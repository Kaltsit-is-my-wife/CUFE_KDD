"""Generate deterministic, controlled multi-session trajectories."""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20251025
SCENARIOS = ("abrupt_drift", "gradual_drift", "topic_switch", "stable")
GOAL_PAIRS = [
    (("frugal", "fast"), ("premium", "thorough")),
    (("premium", "fast"), ("frugal", "thorough")),
    (("frugal", "thorough"), ("premium", "fast")),
]
TOPICS = ["旅行路线", "采购清单", "学习安排", "项目排期", "餐饮选择", "周末活动"]
BACKGROUND = [
    ("diet", "vegetarian"), ("platform", "windows"),
    ("schedule", "evening"), ("accessibility", "low_mobility"),
]

GOAL_TEXT = {
    "frugal": ["长期优先低预算和节省开支", "持续偏好经济方案", "成本控制仍是长期目标"],
    "premium": ["长期优先高品质体验", "持续偏好高端方案", "品质优先是长期目标"],
    "fast": ["长期偏好快速交付", "持续重视速度", "尽快完成是长期目标"],
    "thorough": ["长期偏好全面细致", "持续重视完整性", "充分核查是长期目标"],
}
BG_TEXT = {
    "vegetarian": "背景约束：只选择素食",
    "windows": "背景约束：使用 Windows",
    "evening": "背景约束：只能晚间处理",
    "low_mobility": "背景约束：行动不便，需要无障碍",
}


def _goal_phrase(goal: tuple[str, str], variant: int) -> str:
    return "；".join(GOAL_TEXT[v][variant % 3] for v in goal)


def generate_trajectories(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    trajectories: list[dict] = []
    for scenario in SCENARIOS:
        for i in range(12):
            old_goal, new_goal = GOAL_PAIRS[i % len(GOAL_PAIRS)]
            bg_key, bg_value = BACKGROUND[i % len(BACKGROUND)]
            base_topic = TOPICS[i % len(TOPICS)]
            sessions = []
            for t in range(10):
                topic = base_topic
                evidence: list[str] = []
                current_goal = old_goal
                if scenario == "abrupt_drift" and t >= 5:
                    current_goal = new_goal
                elif scenario == "gradual_drift":
                    # New-goal evidence rises causally; the committed goal changes at session 7.
                    if t < 4:
                        evidence = [_goal_phrase(old_goal, t)]
                    elif t == 4:
                        evidence = [_goal_phrase(old_goal, t), f"开始考虑{new_goal[0]}和{new_goal[1]}"]
                    elif t == 5:
                        evidence = [f"更多考虑{new_goal[0]}和{new_goal[1]}", _goal_phrase(old_goal, t)]
                    elif t == 6:
                        evidence = [_goal_phrase(new_goal, t), f"但尚未完全放弃{old_goal[0]}"]
                    else:
                        current_goal = new_goal
                        evidence = [_goal_phrase(new_goal, t)]
                elif scenario == "topic_switch":
                    # Deliberately large lexical topic changes while explicit long-term goals stay fixed.
                    topic = TOPICS[(i + t * 2) % len(TOPICS)]

                if not evidence:
                    evidence = [_goal_phrase(current_goal, t)]
                noise = rng.choice(["请给出三个选项", "今天只讨论当前事项", "需要可执行步骤", "请保持简洁"])
                text = f"当前话题：{topic}。{'；'.join(evidence)}。{BG_TEXT[bg_value]}。{noise}。"
                sessions.append({"session_id": t, "text": text})

            drift_start = 5 if scenario == "abrupt_drift" else (4 if scenario == "gradual_drift" else None)
            confirmation = 5 if scenario == "abrupt_drift" else (7 if scenario == "gradual_drift" else None)
            trajectories.append({
                "trajectory_id": f"{scenario}-{i:02d}",
                "scenario": scenario,
                "initial_goal": list(old_goal),
                "final_goal": list(new_goal if "drift" in scenario else old_goal),
                "background": {"key": bg_key, "value": bg_value},
                "drift_start": drift_start,
                "confirmation_session": confirmation,
                "sessions": sessions,
            })
    return trajectories


def save_trajectories(path: Path, seed: int = SEED) -> list[dict]:
    data = generate_trajectories(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    rows = save_trajectories(root / "data" / "trajectories.json")
    print(f"generated={len(rows)} seed={SEED}")
