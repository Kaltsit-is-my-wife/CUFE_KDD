"""Causal detectors. Public APIs accept observable sessions only."""
from __future__ import annotations

import re
from collections import defaultdict, deque

COST = ("economy", "value", "premium")
PACE = ("rapid", "balanced", "thorough")
VALUES = COST + PACE
TOPIC_RE = re.compile(r"Topic: ([^.]+)")

LEXICON = {
    "economy": ("cost as low", "cheapest workable", "minimize spending", "strict budget", "expensive upgrades have stopped", "large price tag"),
    "value": ("value for money", "extra cost when", "price with durability", "bargain-bin and luxury", "cheapest choice caused", "price alone"),
    "premium": ("quality matters more", "premium experience", "pay for the best", "finish and comfort", "sacrificing quality", "comfort now wins"),
    "rapid": ("as quickly", "speed is the main", "short path", "ship early", "wait through another long", "slow option was rejected"),
    "balanced": ("balance speed", "moderate pace", "enough review", "trade off turnaround", "neither rushing nor exhaustive", "either extreme pace"),
    "thorough": ("every important detail", "coverage matters", "comprehensive process", "do not rush", "quick answer without verification", "rushed version was rejected"),
}


def extract(text: str, include_scoped: bool = False) -> dict[str, float]:
    scores = {v: 0.0 for v in VALUES}
    sentences = [s.strip().lower() for s in text.split(".") if s.strip()]
    for sentence in sentences:
        scoped = "this session only" in sentence or "historical context" in sentence or "previous plan" in sentence
        if scoped and not include_scoped:
            continue
        factor = 0.25 if scoped else 1.0
        for value, phrases in LEXICON.items():
            if any(p in sentence for p in phrases):
                scores[value] += factor
    return scores


def dominant(scores: dict[str, float]) -> tuple[str, str] | None:
    c = max(COST, key=lambda x: scores[x]); p = max(PACE, key=lambda x: scores[x])
    if scores[c] <= 0 or scores[p] <= 0:
        return None
    return c, p


def aggregate(texts: list[str], decay: float = 1.0) -> dict[str, float]:
    out = {v: 0.0 for v in VALUES}
    n = len(texts)
    for i, text in enumerate(texts):
        for v, score in extract(text).items():
            out[v] += score * (decay ** (n - i - 1))
    return out


def baseline_a(sessions: list[dict], params: dict | None = None) -> dict:
    previous = None
    for s in sessions:
        m = TOPIC_RE.search(s["text"]); topic = m.group(1) if m else ""
        if previous is not None and topic != previous:
            return {"detected_at": s["session_id"], "predicted_type": "change", "confidence": 1.0}
        previous = topic
    return {"detected_at": None, "predicted_type": None, "confidence": 0.0}


def baseline_b(sessions: list[dict], params: dict) -> dict:
    window, persistence = params["window"], params["persistence"]
    initial = dominant(aggregate([s["text"] for s in sessions[:3]]))
    run = 0
    for i in range(max(3, window - 1), len(sessions)):
        cur = dominant(aggregate([s["text"] for s in sessions[i-window+1:i+1]]))
        run = run + 1 if cur and initial and cur != initial else 0
        if run >= persistence:
            return {"detected_at": sessions[i]["session_id"], "predicted_type": "persistent", "confidence": min(1.0, run/persistence)}
    return {"detected_at": None, "predicted_type": None, "confidence": 0.0}


def method_c(sessions: list[dict], params: dict) -> dict:
    threshold, persistence = params["threshold"], params["persistence"]
    ref = dominant(aggregate([s["text"] for s in sessions[:3]]))
    run = 0; prior_alt = 0.0
    for i in range(3, len(sessions)):
        sc = extract(sessions[i]["text"]); cur = dominant(sc)
        if not ref or not cur:
            run = 0; continue
        margin = sum(sc[v] for v in cur) - sum(sc[v] for v in ref)
        changed = sum(a != b for a, b in zip(ref, cur))
        evidence = max(0.0, margin) * changed
        run = run + 1 if evidence >= threshold else 0
        if evidence >= threshold * 2.2 or run >= persistence:
            typ = "gradual" if prior_alt >= 0.8 else "abrupt"
            return {"detected_at": sessions[i]["session_id"], "predicted_type": typ, "confidence": min(1.0, evidence/(threshold*2.2))}
        prior_alt = prior_alt * 0.75 + sum(sc[v] for v in VALUES if v not in ref)
    return {"detected_at": None, "predicted_type": None, "confidence": 0.0}


def improved_d(sessions: list[dict], params: dict) -> dict:
    """Two-timescale evidence ratio with gaps, reversion guard, and uncertainty."""
    alpha, margin_threshold, confirmations, gap = (params[k] for k in ("alpha", "margin", "confirmations", "gap"))
    ref_scores = aggregate([s["text"] for s in sessions[:3]])
    ref = dominant(ref_scores)
    fast = {v: 0.0 for v in VALUES}; votes: deque[bool] = deque(maxlen=gap + confirmations)
    first_candidate = None
    for i in range(3, len(sessions)):
        sc = extract(sessions[i]["text"])
        for v in VALUES:
            fast[v] = alpha * sc[v] + (1-alpha) * fast[v]
        cur = dominant(fast)
        if not ref or not cur:
            votes.append(False); continue
        ref_mass = sum(fast[v] for v in ref); cur_mass = sum(fast[v] for v in cur)
        changed = sum(a != b for a, b in zip(ref, cur))
        vote = bool(changed and cur_mass - ref_mass >= margin_threshold)
        votes.append(vote)
        if vote and first_candidate is None:
            first_candidate = sessions[i]["session_id"]
        if sum(votes) >= confirmations:
            # Alert at confirmation, but preserve the first supporting evidence as onset estimate.
            return {"detected_at": sessions[i]["session_id"], "estimated_onset": first_candidate,
                    "predicted_type": "gradual" if sessions[i]["session_id"] - first_candidate > 1 else "abrupt",
                    "confidence": min(1.0, (cur_mass-ref_mass)/(margin_threshold+1e-9)/2)}
        if not vote and sum(votes) == 0:
            first_candidate = None
    return {"detected_at": None, "estimated_onset": None, "predicted_type": None, "confidence": 0.0}


METHODS = {"baseline_a_topic": baseline_a, "baseline_b_persistence": baseline_b,
           "method_c_original": method_c, "method_d_evidence": improved_d}


def predict(observable: list[dict], params: dict[str, dict]) -> list[dict]:
    rows = []
    for traj in observable:
        sessions = [{"session_id": s["session_id"], "text": s["text"]} for s in traj["sessions"]]
        for name, method in METHODS.items():
            pred = method(sessions, params.get(name, {}))
            rows.append({"trajectory_id": traj["trajectory_id"], "method": name, **pred})
    return rows
