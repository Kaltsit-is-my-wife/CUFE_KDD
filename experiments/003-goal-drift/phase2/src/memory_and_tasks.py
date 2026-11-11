"""Memory extraction, four update strategies, and strategy-neutral task scoring."""
from __future__ import annotations

import math
from collections import defaultdict

from detectors import COST, PACE, aggregate, dominant, extract

BG_LEXICON = {
    "vegetarian": ("vegetarian", "no meat"), "windows": ("runs windows", "work on windows"),
    "evening": ("only work in the evening", "daytime is unavailable"),
    "step_free": ("step-free", "stairs are not accessible"),
}


def value_key(value: str) -> str:
    return "cost" if value in COST else "pace"


def extract_memories(sessions: list[dict]) -> list[dict]:
    memories = []
    for session in sessions:
        for raw_sentence in session["text"].split("."):
            sentence = raw_sentence.strip()
            if not sentence:
                continue
            lower = sentence.lower()
            kind = "temporary" if "this session only" in lower else ("history_plan" if "historical context" in lower or "previous plan" in lower else "long_term_goal")
            scores = extract(sentence, include_scoped=True)
            for value, score in scores.items():
                if score > 0:
                    memories.append({"session_id": session["session_id"], "kind": kind,
                                     "key": value_key(value), "value": value, "weight": 1.0,
                                     "state": "active", "source": sentence})
            for bg_value, phrases in BG_LEXICON.items():
                if any(p in lower for p in phrases):
                    memories.append({"session_id": session["session_id"], "kind": "stable_background",
                                     "key": "background", "value": bg_value, "weight": 1.0,
                                     "state": "active", "source": sentence})
    return memories


def infer_goal(sessions: list[dict], lookback: int) -> tuple[tuple[str, str] | None, dict[str, float]]:
    scores = aggregate([s["text"] for s in sessions[-lookback:]], decay=0.82)
    return dominant(scores), scores


def apply_strategy(memories: list[dict], sessions: list[dict], strategy: str,
                   detection: dict | None, params: dict) -> list[dict]:
    now = sessions[-1]["session_id"]
    out = [dict(m) for m in memories]
    if strategy == "no_update":
        return out
    if strategy == "time_decay":
        rate = params["decay_rate"]
        for m in out:
            m["weight"] *= math.exp(-rate * (now - m["session_id"]))
            if m["weight"] < 0.5:
                m["state"] = "downweighted"
        return out
    if strategy == "drift_aware_original":
        if not detection or detection.get("detected_at") is None or detection["detected_at"] > now:
            return out
        goal, _ = infer_goal(sessions, 2)
        if goal:
            target = dict(zip(("cost", "pace"), goal))
            for m in out:
                if (m["kind"] == "long_term_goal" and m["session_id"] < detection["detected_at"]
                        and m["value"] != target[m["key"]]):
                    m["weight"] *= 0.12; m["state"] = "downweighted"
        return out
    if strategy != "drift_aware_improved":
        raise ValueError(strategy)
    # Type-aware base policy is observable from linguistic scope, not ground truth.
    for m in out:
        if m["kind"] in {"temporary", "history_plan"}:
            m["weight"] *= 0.25; m["state"] = "downweighted"
    if not detection or detection.get("detected_at") is None or detection["detected_at"] > now:
        return out
    goal, scores = infer_goal(sessions, params["lookback"])
    if not goal:
        return out
    target = dict(zip(("cost", "pace"), goal))
    for key, domain in (("cost", COST), ("pace", PACE)):
        ordered = sorted((scores[v], v) for v in domain)
        margin = ordered[-1][0] - ordered[-2][0]
        for m in out:
            if m["kind"] == "long_term_goal" and m["key"] == key and m["value"] != target[key]:
                if margin >= params["confirm_margin"]:
                    m["weight"] *= 0.10; m["state"] = "downweighted"
                else:
                    m["weight"] *= 0.55; m["state"] = "pending"
    return out


def memory_truth(memory: dict, current_goal: tuple[str, str], background_value: str) -> str:
    if memory["kind"] in {"temporary", "history_plan"}:
        return "obsolete"
    if memory["kind"] == "stable_background":
        return "valid" if memory["value"] == background_value else "obsolete"
    target = dict(zip(("cost", "pace"), current_goal))
    return "valid" if memory["value"] == target[memory["key"]] else "obsolete"


def memory_counts(memories: list[dict], current_goal: tuple[str, str], background_value: str) -> list[dict]:
    rows = []
    categories = ["overall", "long_term_goal", "stable_background", "temporary", "history_plan"]
    for category in categories:
        subset = memories if category == "overall" else [m for m in memories if m["kind"] == category]
        tp = fp = fn = 0; obsolete_weight = valid_weight = 0.0; obsolete_n = valid_n = updates = 0
        for m in subset:
            truth = memory_truth(m, current_goal, background_value)
            predicted = m["weight"] < 0.5
            updates += int(m["state"] != "active")
            if truth == "obsolete":
                obsolete_n += 1; obsolete_weight += m["weight"]
                tp += int(predicted); fn += int(not predicted)
            else:
                valid_n += 1; valid_weight += m["weight"]
                fp += int(predicted)
        rows.append({"category": category, "tp": tp, "fp": fp, "fn": fn,
                     "obsolete_weight": obsolete_weight, "valid_weight": valid_weight,
                     "obsolete_n": obsolete_n, "valid_n": valid_n, "updates": updates,
                     "total_weight": obsolete_weight + valid_weight})
    return rows


def score_task(task: dict, memories: list[dict], background_value: str, initial_goal: tuple[str, str]) -> dict:
    required = dict(zip(("cost", "pace"), task["required_goal"]))
    totals = defaultdict(float)
    for m in memories:
        if m["kind"] in {"long_term_goal", "temporary", "history_plan"}:
            totals[(m["key"], m["value"])] += m["weight"]
    for key, value in required.items():
        totals[(key, value)] += task["signal_strength"]
    selected = {}
    for key, domain in (("cost", COST), ("pace", PACE)):
        selected[key] = max(domain, key=lambda v: (totals[(key, v)], v))
    bg_strength = sum(m["weight"] for m in memories if m["kind"] == "stable_background" and m["value"] == background_value)
    background_used = bg_strength >= 0.70
    satisfied = sum(selected[k] == required[k] for k in required)
    initial = dict(zip(("cost", "pace"), initial_goal))
    old_conflict = any(required[k] != initial[k] and selected[k] == initial[k] for k in required)
    reasons = []
    if selected["cost"] != required["cost"]: reasons.append("cost_goal_conflict")
    if selected["pace"] != required["pace"]: reasons.append("pace_goal_conflict")
    if not background_used: reasons.append("background_below_threshold")
    return {"task_success": int(satisfied == 2 and background_used),
            "old_goal_conflict": int(old_conflict), "constraint_satisfaction_rate": satisfied / 2,
            "background_retention_rate": int(background_used),
            "selected_goal": f"{selected['cost']}+{selected['pace']}",
            "failure_reason": ";".join(reasons) if reasons else "success"}
