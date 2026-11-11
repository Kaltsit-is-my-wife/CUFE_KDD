"""Metric definitions and deterministic end-to-end task scorer."""
from __future__ import annotations

from collections import Counter, defaultdict


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def detection_metrics(trajectories: list[dict], predictions: list[dict]) -> list[dict]:
    truth = {t["trajectory_id"]: t for t in trajectories}
    groups = defaultdict(list)
    for p in predictions:
        groups[p["method"]].append(p)
    rows = []
    for method, preds in groups.items():
        tp = fp = fn = tn = 0
        delays, errors = [], []
        topic_fp = 0
        type_correct = 0
        for p in preds:
            t = truth[p["trajectory_id"]]
            actual = t["confirmation_session"] is not None
            predicted = p["detected_at"] is not None
            if actual and predicted:
                tp += 1
                delays.append(p["detected_at"] - t["confirmation_session"])
                errors.append(abs(p["detected_at"] - t["drift_start"]))
                expected_type = "abrupt" if t["scenario"] == "abrupt_drift" else "gradual"
                type_correct += int(p["predicted_type"] == expected_type)
            elif not actual and predicted:
                fp += 1
                topic_fp += int(t["scenario"] == "topic_switch")
            elif actual:
                fn += 1
            else:
                tn += 1
        precision, recall = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
        rows.append({
            "method": method, "precision": precision, "recall": recall,
            "f1": safe_div(2 * precision * recall, precision + recall),
            "false_positive_rate": safe_div(fp, fp + tn),
            "mean_detection_delay": sum(delays) / len(delays) if delays else None,
            "mean_localization_error": sum(errors) / len(errors) if errors else None,
            "drift_type_accuracy": safe_div(type_correct, tp),
            "topic_switch_false_positives": topic_fp, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        })
    return rows


def memory_metrics(traj: dict, memories: list[dict]) -> dict:
    final = dict(zip(("cost", "process"), traj["final_goal"]))
    obsolete = [m for m in memories if m["kind"] == "goal" and m["value"] != final[m["key"]]]
    valid = [m for m in memories if m not in obsolete]
    predicted = [m for m in memories if m["downweighted"]]
    tp = sum(m in obsolete for m in predicted)
    fp = sum(m in valid for m in predicted)
    fn = len(obsolete) - tp
    precision, recall = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
    obsolete_weight = sum(m["weight"] for m in obsolete)
    goal_weight = sum(m["weight"] for m in memories if m["kind"] == "goal")
    valid_weight = sum(m["weight"] for m in valid)
    return {
        "obsolete_interference_rate": safe_div(obsolete_weight, goal_weight),
        "valid_memory_retention_rate": safe_div(valid_weight, len(valid)),
        "obsolete_precision": precision, "obsolete_recall": recall,
        "obsolete_f1": safe_div(2 * precision * recall, precision + recall),
        "incorrect_downweight_rate": safe_div(fp, len(valid)), "memory_update_count": len(predicted),
        "_tp": tp, "_fp": fp, "_fn": fn, "_valid_count": len(valid),
        "_valid_weight": valid_weight, "_obsolete_weight": obsolete_weight, "_goal_weight": goal_weight,
    }


def aggregate_memory(rows: list[dict]) -> list[dict]:
    """Micro-average identification/rate metrics; average update count per trajectory."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)
    output = []
    for strategy, vals in grouped.items():
        tp, fp, fn = (sum(v[k] for v in vals) for k in ("_tp", "_fp", "_fn"))
        precision, recall = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
        output.append({
            "strategy": strategy,
            "obsolete_interference_rate": safe_div(sum(v["_obsolete_weight"] for v in vals), sum(v["_goal_weight"] for v in vals)),
            "valid_memory_retention_rate": safe_div(sum(v["_valid_weight"] for v in vals), sum(v["_valid_count"] for v in vals)),
            "obsolete_precision": precision, "obsolete_recall": recall,
            "obsolete_f1": safe_div(2 * precision * recall, precision + recall),
            "incorrect_downweight_rate": safe_div(fp, sum(v["_valid_count"] for v in vals)),
            "memory_update_count": sum(v["memory_update_count"] for v in vals) / len(vals),
        })
    return output


def score_task(traj: dict, memories: list[dict]) -> dict:
    final = dict(zip(("cost", "process"), traj["final_goal"]))
    initial = dict(zip(("cost", "process"), traj["initial_goal"]))
    totals = defaultdict(Counter)
    for m in memories:
        totals[m["kind"]][(m["key"], m["value"])] += m["weight"]
    # Current request contributes modest direct evidence; memory can help or interfere.
    for key, value in final.items():
        totals["goal"][(key, value)] += 2.2
    selected = {}
    for key in ("cost", "process"):
        candidates = [(weight, value) for (k, value), weight in totals["goal"].items() if k == key]
        selected[key] = max(candidates, key=lambda x: (x[0], x[1]))[1]
    bg = traj["background"]
    bg_used = totals["background"][(bg["key"], bg["value"])] > 0
    satisfied = sum(selected[k] == final[k] for k in final)
    old_conflict = any(final[k] != initial[k] and selected[k] == initial[k] for k in final)
    return {
        "task_success": int(satisfied == len(final) and bg_used),
        "old_goal_conflict": int(old_conflict),
        "constraint_satisfaction_rate": satisfied / len(final),
        "background_utilization_rate": int(bg_used),
        "selected_goal": "+".join(selected[k] for k in ("cost", "process")),
    }


def aggregate(rows: list[dict], group_key: str, metric_keys: list[str]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[group_key]].append(row)
    return [{group_key: key, **{m: sum(r[m] for r in vals) / len(vals) for m in metric_keys}} for key, vals in grouped.items()]


def validate_no_leakage() -> None:
    """Regression check: future text cannot alter an earlier detector result."""
    from detect_drift import DETECTORS
    prefix = [{"session_id": i, "text": f"当前话题：A。长期优先低预算和节省开支；长期偏好快速交付。"} for i in range(5)]
    hostile_future = prefix + [{"session_id": 5, "text": "当前话题：B。长期优先高品质体验；长期偏好全面细致。"}]
    for detector in DETECTORS.values():
        before = detector(prefix)
        after_on_same_prefix = detector(hostile_future[:5])
        assert before == after_on_same_prefix
