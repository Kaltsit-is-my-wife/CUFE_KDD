"""Memory extraction and three deterministic update strategies."""
from __future__ import annotations

import math
import re

from detect_drift import dominant_goal

BG_VALUES = ("vegetarian", "windows", "evening", "low_mobility")
BG_PHRASES = {"vegetarian": "素食", "windows": "Windows", "evening": "晚间", "low_mobility": "无障碍"}


def extract_memories(traj: dict) -> list[dict]:
    memories = []
    for s in traj["sessions"]:
        goal = dominant_goal([s["text"]])
        if goal:
            for dim, value in zip(("cost", "process"), goal):
                memories.append({"session_id": s["session_id"], "kind": "goal", "key": dim, "value": value, "weight": 1.0})
        for value, phrase in BG_PHRASES.items():
            if phrase in s["text"]:
                memories.append({"session_id": s["session_id"], "kind": "background", "key": traj["background"]["key"], "value": value, "weight": 1.0})
    return memories


def apply_strategy(memories: list[dict], strategy: str, detected_at: int | None, sessions: list[dict]) -> list[dict]:
    final_t = sessions[-1]["session_id"]
    result = [dict(m, downweighted=False) for m in memories]
    if strategy == "no_update":
        return result
    if strategy == "time_decay":
        for m in result:
            m["weight"] = math.exp(-0.18 * (final_t - m["session_id"]))
            m["downweighted"] = m["weight"] < 0.5
        return result
    if strategy != "drift_aware":
        raise ValueError(strategy)
    if detected_at is None:
        return result
    observed = [s["text"] for s in sessions if s["session_id"] <= detected_at][-2:]
    detected_goal = dominant_goal(observed)
    if detected_goal:
        target = dict(zip(("cost", "process"), detected_goal))
        for m in result:
            if m["kind"] == "goal" and m["session_id"] < detected_at and m["value"] != target[m["key"]]:
                m["weight"] *= 0.12
                m["downweighted"] = True
    return result
