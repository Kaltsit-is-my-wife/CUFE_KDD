"""Causal rule detectors. Ground-truth fields are never accepted by these functions."""
from __future__ import annotations

import re
from collections import Counter, deque

GOAL_WORDS = ("frugal", "premium", "fast", "thorough")
ZH_TO_GOAL = {
    "低预算": "frugal", "节省": "frugal", "经济": "frugal", "成本控制": "frugal",
    "高品质": "premium", "高端": "premium", "品质优先": "premium",
    "快速": "fast", "速度": "fast", "尽快": "fast",
    "全面细致": "thorough", "完整性": "thorough", "充分核查": "thorough",
}
TOPIC_RE = re.compile(r"当前话题：([^。]+)")


def goal_scores(text: str) -> dict[str, float]:
    scores = {g: 0.0 for g in GOAL_WORDS}
    for phrase, goal in ZH_TO_GOAL.items():
        if phrase in text:
            scores[goal] += 1.0
    # Weak transition mentions are intentionally weaker than explicit preference phrases.
    for goal in GOAL_WORDS:
        if goal in text:
            scores[goal] += 0.35
    return scores


def dominant_goal(texts: list[str]) -> tuple[str, str] | None:
    total = Counter()
    for text in texts:
        total.update(goal_scores(text))
    cost = max(("frugal", "premium"), key=lambda x: total[x])
    process = max(("fast", "thorough"), key=lambda x: total[x])
    if total[cost] == 0 or total[process] == 0:
        return None
    return cost, process


def baseline_a(sessions: list[dict]) -> dict:
    """Adjacent-session topic change; intentionally confounds topic and goal."""
    previous = None
    for s in sessions:  # strictly chronological; no future access
        match = TOPIC_RE.search(s["text"])
        topic = match.group(1) if match else ""
        if previous is not None and topic != previous:
            return {"detected_at": s["session_id"], "predicted_type": "change"}
        previous = topic
    return {"detected_at": None, "predicted_type": None}


def baseline_b(sessions: list[dict]) -> dict:
    """Short-window persistence: two consecutive windows must differ from initial goal."""
    initial_texts: list[str] = []
    recent: deque[str] = deque(maxlen=3)
    candidate_count = 0
    for s in sessions:
        if len(initial_texts) < 3:
            initial_texts.append(s["text"])
        recent.append(s["text"])
        if len(initial_texts) < 3 or len(recent) < 3:
            continue
        initial = dominant_goal(initial_texts)
        current = dominant_goal(list(recent))
        candidate_count = candidate_count + 1 if current and current != initial else 0
        if candidate_count >= 2:
            return {"detected_at": s["session_id"], "predicted_type": "persistent"}
    return {"detected_at": None, "predicted_type": None}


def method_c(sessions: list[dict]) -> dict:
    """Dual-timescale causal detector for abrupt jumps and accumulating gradual change."""
    long = {g: 0.0 for g in GOAL_WORDS}
    deviation_run = 0
    gradual_mass = 0.0
    prior_alternative_evidence = 0.0
    for idx, s in enumerate(sessions):
        score = goal_scores(s["text"])
        if idx < 3:
            for g in GOAL_WORDS:
                long[g] += score[g]
            continue
        reference = (max(("frugal", "premium"), key=lambda g: long[g]),
                     max(("fast", "thorough"), key=lambda g: long[g]))
        current = (max(("frugal", "premium"), key=lambda g: score[g]),
                   max(("fast", "thorough"), key=lambda g: score[g]))
        old_strength = score[reference[0]] + score[reference[1]]
        new_strength = score[current[0]] + score[current[1]]
        changed_dims = sum(a != b for a, b in zip(reference, current))
        deviation = max(0.0, new_strength - old_strength) * changed_dims
        deviation_run = deviation_run + 1 if changed_dims and deviation >= 1.2 else 0
        gradual_mass = max(0.0, gradual_mass * 0.72 + deviation)
        if changed_dims == 2 and deviation >= 3.0:
            kind = "gradual" if prior_alternative_evidence >= 1.0 else "abrupt"
            return {"detected_at": s["session_id"], "predicted_type": kind}
        if deviation_run >= 2 and gradual_mass >= 3.0:
            return {"detected_at": s["session_id"], "predicted_type": "gradual"}
        alternatives = [g for g in GOAL_WORDS if g not in reference]
        prior_alternative_evidence = prior_alternative_evidence * 0.8 + sum(score[g] for g in alternatives)
        # Conservative adaptation prevents one-session topic/noise from changing reference.
        for g in GOAL_WORDS:
            long[g] = 0.94 * long[g] + 0.06 * score[g]
    return {"detected_at": None, "predicted_type": None}


DETECTORS = {"baseline_a_topic": baseline_a, "baseline_b_persistence": baseline_b, "method_c_sustained": method_c}


def run_detectors(trajectories: list[dict]) -> list[dict]:
    predictions = []
    for traj in trajectories:
        # Explicit sanitization is the leakage boundary.
        observable = [{"session_id": s["session_id"], "text": s["text"]} for s in traj["sessions"]]
        for name, detector in DETECTORS.items():
            pred = detector(observable)
            predictions.append({"trajectory_id": traj["trajectory_id"], "method": name, **pred})
    return predictions
