"""Independent latent-state generator for the harder phase-2 corpus."""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20261025
SCENARIOS = (
    "abrupt_drift", "gradual_drift", "topic_switch", "temporary_shift",
    "similar_goal_drift", "indirect_drift", "stable",
)
COST = ("economy", "value", "premium")
PACE = ("rapid", "balanced", "thorough")
TOPICS = ("travel", "shopping", "coursework", "project", "meals", "fitness", "home")
BACKGROUND = (
    ("diet", "vegetarian"), ("platform", "windows"),
    ("schedule", "evening"), ("access", "step_free"),
)

PHRASES = {
    "economy": ["keep the overall cost as low as possible", "the cheapest workable route matters most", "minimize spending over polish", "stay on a strict budget"],
    "value": ["optimize value for money", "accept a little extra cost when it clearly pays off", "balance price with durability", "avoid both bargain-bin and luxury choices"],
    "premium": ["quality matters more than price", "choose the premium experience", "I am willing to pay for the best fit", "prioritize finish and comfort over savings"],
    "rapid": ["finish as quickly as practical", "speed is the main priority", "prefer a short path to delivery", "ship early even with fewer extras"],
    "balanced": ["balance speed with adequate checking", "use a moderate pace", "do enough review without overdoing it", "trade off turnaround and coverage"],
    "thorough": ["check every important detail", "coverage matters more than speed", "use a careful comprehensive process", "do not rush the review"],
}
INDIRECT = {
    "economy": ["expensive upgrades have stopped making sense", "I rejected every option with a large price tag"],
    "value": ["the absolute cheapest choice caused too many repairs", "I no longer want price alone to decide"],
    "premium": ["I am done sacrificing quality just to save a little", "the budget option was rejected because comfort now wins"],
    "rapid": ["I cannot wait through another long review", "the slow option was rejected before purchase"],
    "balanced": ["neither rushing nor exhaustive checking worked", "I stopped choosing either extreme pace"],
    "thorough": ["I no longer accept a quick answer without verification", "the rushed version was rejected after missing details"],
}
BG_PHRASES = {
    "vegetarian": ["I eat vegetarian food", "meals must contain no meat"],
    "windows": ["my only computer runs Windows", "the workflow must work on Windows"],
    "evening": ["I can only work in the evening", "daytime is unavailable to me"],
    "step_free": ["I need step-free access", "stairs are not accessible for me"],
}


def other_goal(rng: random.Random, goal: tuple[str, str], similar: bool = False) -> tuple[str, str]:
    if similar:
        if rng.random() < 0.5:
            idx = COST.index(goal[0]); return COST[min(2, idx + 1) if idx < 2 else 1], goal[1]
        idx = PACE.index(goal[1]); return goal[0], PACE[min(2, idx + 1) if idx < 2 else 1]
    choices = [(c, p) for c in COST for p in PACE if c != goal[0] and p != goal[1]]
    return rng.choice(choices)


def phrase(rng: random.Random, value: str) -> str:
    return rng.choice(PHRASES[value])


def generate(seed: int = SEED, per_scenario: int = 24) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    observable, labels = [], []
    for scenario in SCENARIOS:
        for i in range(per_scenario):
            n_sessions = rng.randint(11, 15)
            initial = (rng.choice(COST), rng.choice(PACE))
            final = other_goal(rng, initial, similar=scenario == "similar_goal_drift")
            temporary = other_goal(rng, initial)
            onset = rng.randint(4, n_sessions - 5)
            temporary_length = rng.choice((1, 2, 3))
            confirm = onset
            if scenario == "gradual_drift":
                confirm = min(n_sessions - 3, onset + rng.choice((2, 3, 4)))
            elif scenario == "indirect_drift":
                confirm = min(n_sessions - 3, onset + rng.choice((1, 2)))
            has_drift = scenario in {"abrupt_drift", "gradual_drift", "similar_goal_drift", "indirect_drift"}
            if not has_drift:
                final = initial
                true_onset = true_confirm = None
            else:
                true_onset, true_confirm = onset, confirm
            bg_key, bg_value = BACKGROUND[(i + SCENARIOS.index(scenario)) % len(BACKGROUND)]
            recurring_topic = rng.choice(TOPICS)
            current_goals, sessions = [], []
            for t in range(n_sessions):
                current = initial
                evidence_goal = initial
                indirect = False
                if scenario in {"abrupt_drift", "similar_goal_drift"} and t >= confirm:
                    current = evidence_goal = final
                elif scenario == "gradual_drift":
                    if t >= confirm:
                        current = final
                    if onset <= t < confirm:
                        # Non-monotone and sometimes missing transition evidence.
                        evidence_goal = final if rng.random() < (0.30 + 0.16 * (t - onset)) else initial
                    elif t >= confirm:
                        evidence_goal = final
                elif scenario == "indirect_drift" and t >= onset:
                    current = final if t >= confirm else initial
                    evidence_goal, indirect = final, True
                elif scenario == "temporary_shift" and onset <= t < min(n_sessions, onset + temporary_length):
                    current = evidence_goal = temporary

                current_goals.append(list(current))
                if scenario == "topic_switch":
                    topic = TOPICS[(t * 3 + i) % len(TOPICS)]
                else:
                    topic = recurring_topic if rng.random() < 0.72 else rng.choice(TOPICS)
                parts = [f"Topic: {topic}."]
                # Evidence omissions and paraphrases are independent of the latent label.
                for value in evidence_goal:
                    if rng.random() < 0.82:
                        parts.append((rng.choice(INDIRECT[value]) if indirect and rng.random() < 0.78 else phrase(rng, value)) + ".")
                # Historical goal mention shares vocabulary but is explicitly scoped as history.
                if t > onset and rng.random() < 0.28:
                    old_value = rng.choice(initial)
                    parts.append(f"The previous plan used to {phrase(rng, old_value)}, but that is historical context.")
                # A temporary request can conflict with the long-term goal.
                if rng.random() < 0.30:
                    temp_value = rng.choice(COST + PACE)
                    parts.append(f"For this session only, {phrase(rng, temp_value)}.")
                # Background is stable but sparse, unlike phase 1 where it appeared every session.
                if t == 0 or rng.random() < 0.18:
                    parts.append(rng.choice(BG_PHRASES[bg_value]) + ".")
                if rng.random() < 0.35:
                    parts.append(f"Unrelated recurring note: {rng.choice(TOPICS)} remains on my checklist.")
                sessions.append({"session_id": t, "text": " ".join(parts)})

            split = "dev" if i < 8 else "test"
            tid = f"p2-{scenario}-{i:02d}"
            if has_drift:
                raw_task_times = [true_confirm, min(n_sessions - 1, true_confirm + 2), n_sessions - 1]
            elif scenario == "temporary_shift":
                recovered = min(n_sessions - 1, onset + temporary_length)
                raw_task_times = [recovered, min(n_sessions - 1, recovered + 2), n_sessions - 1]
            else:
                raw_task_times = [min(7, n_sessions - 1), min(9, n_sessions - 1), n_sessions - 1]
            task_times = sorted(set(raw_task_times))
            tasks = [{"task_id": f"{tid}-task-{j}", "session_id": tt,
                      "required_goal": current_goals[tt], "signal_strength": rng.choice((0.65, 0.9, 1.2))}
                     for j, tt in enumerate(task_times)]
            observable.append({"trajectory_id": tid, "split": split, "sessions": sessions})
            labels.append({
                "trajectory_id": tid, "split": split, "scenario": scenario,
                "has_drift": has_drift, "drift_onset": true_onset, "confirmation_session": true_confirm,
                "initial_goal": list(initial), "final_goal": list(final), "current_goals": current_goals,
                "background": {"key": bg_key, "value": bg_value}, "tasks": tasks,
            })
    return observable, labels


def save_data(root: Path) -> tuple[list[dict], list[dict]]:
    observable, labels = generate()
    data = root / "data"; data.mkdir(parents=True, exist_ok=True)
    (data / "interactions.json").write_text(json.dumps(observable, indent=2), encoding="utf-8")
    (data / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    return observable, labels
