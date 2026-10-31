"""Label-side evaluation. This module alone joins predictions to hidden labels."""
from __future__ import annotations

import random
from collections import defaultdict
from itertools import combinations


def div(a: float, b: float) -> float:
    return a / b if b else 0.0


def detection_rows(predictions: list[dict], labels: list[dict], tolerance: int = 2) -> tuple[list[dict], list[dict]]:
    truth = {x["trajectory_id"]: x for x in labels}
    joined = []
    for p in predictions:
        t = truth[p["trajectory_id"]]; alert = p.get("detected_at")
        if not t["has_drift"]:
            error = "false_positive" if alert is not None else "correct_rejection"
            delay = loc_error = None; hit = None
        elif alert is None:
            error = "miss"; delay = loc_error = None; hit = 0
        else:
            delay = alert - t["confirmation_session"]
            estimate = p.get("estimated_onset") if p.get("estimated_onset") is not None else alert
            loc_error = estimate - t["drift_onset"]
            hit = int(abs(loc_error) <= tolerance)
            error = "early" if delay < -tolerance else ("late" if delay > tolerance else "on_time")
        joined.append({**p, "split": t["split"], "scenario": t["scenario"], "has_drift": t["has_drift"],
                       "true_onset": t["drift_onset"], "true_confirmation": t["confirmation_session"],
                       "detection_delay": delay, "localization_error": loc_error,
                       "localization_hit": hit, "error_type": error})
    groups = ["overall", *sorted({x["scenario"] for x in labels}), "all_drift", "no_drift"]
    metrics = []
    for method in sorted({p["method"] for p in joined}):
        method_rows = [x for x in joined if x["method"] == method]
        for group in groups:
            rows = method_rows if group == "overall" else ([x for x in method_rows if x["has_drift"]] if group == "all_drift" else ([x for x in method_rows if not x["has_drift"]] if group == "no_drift" else [x for x in method_rows if x["scenario"] == group]))
            if not rows: continue
            tp = sum(x["has_drift"] and x["detected_at"] is not None for x in rows)
            fp = sum((not x["has_drift"]) and x["detected_at"] is not None for x in rows)
            fn = sum(x["has_drift"] and x["detected_at"] is None for x in rows)
            tn = sum((not x["has_drift"]) and x["detected_at"] is None for x in rows)
            prec, rec = div(tp, tp+fp), div(tp, tp+fn)
            delays = [x["detection_delay"] for x in rows if x["detection_delay"] is not None]
            locs = [abs(x["localization_error"]) for x in rows if x["localization_error"] is not None]
            hits = [x["localization_hit"] for x in rows if x["localization_hit"] is not None and x["detected_at"] is not None]
            metrics.append({"method": method, "group": group, "n_trajectories": len(rows),
                            "precision": prec, "recall": rec, "f1": div(2*prec*rec, prec+rec),
                            "false_positive_rate": div(fp, fp+tn),
                            "localization_hit_rate_tolerance_2": div(sum(hits), len(hits)),
                            "mean_abs_localization_error": div(sum(locs), len(locs)) if locs else None,
                            "mean_detection_delay": div(sum(delays), len(delays)) if delays else None,
                            "tp": tp, "fp": fp, "fn": fn, "tn": tn})
    return metrics, joined


def aggregate_memory(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows: grouped[(row["strategy"], row["category"], row["evaluation_scope"])].append(row)
    out = []
    for (strategy, category, scope), vals in grouped.items():
        sums = {k: sum(v[k] for v in vals) for k in ("tp","fp","fn","obsolete_weight","valid_weight","obsolete_n","valid_n","updates","total_weight")}
        p, r = div(sums["tp"], sums["tp"]+sums["fp"]), div(sums["tp"], sums["tp"]+sums["fn"])
        out.append({"strategy": strategy, "category": category, "evaluation_scope": scope,
                    "obsolete_precision": p, "obsolete_recall": r, "obsolete_f1": div(2*p*r,p+r),
                    "obsolete_interference_rate": div(sums["obsolete_weight"], sums["total_weight"]),
                    "valid_memory_retention_rate": div(sums["valid_weight"], sums["valid_n"]),
                    "incorrect_downweight_rate": div(sums["fp"], sums["valid_n"]),
                    "mean_update_count": div(sums["updates"], len(vals)), "n_trajectories": len(vals)})
    return out


def trajectory_task_rates(rows: list[dict]) -> dict[tuple[str,str], dict[str,float]]:
    grouped = defaultdict(list)
    for r in rows: grouped[(r["trajectory_id"], r["strategy"])].append(r)
    return {k: {m: sum(x[m] for x in v)/len(v) for m in ("task_success","old_goal_conflict","constraint_satisfaction_rate","background_retention_rate")} for k,v in grouped.items()}


def bootstrap_task(rows: list[dict], seed: int, iterations: int = 2000) -> tuple[list[dict], list[dict]]:
    rates = trajectory_task_rates(rows); tids = sorted({k[0] for k in rates}); strategies = sorted({k[1] for k in rates})
    rng = random.Random(seed); metrics = ("task_success","old_goal_conflict","constraint_satisfaction_rate","background_retention_rate")
    summary = []
    for strategy in strategies:
        for metric in metrics:
            point = sum(rates[(t,strategy)][metric] for t in tids)/len(tids)
            samples = []
            for _ in range(iterations):
                draw = [rng.choice(tids) for _ in tids]
                samples.append(sum(rates[(t,strategy)][metric] for t in draw)/len(draw))
            samples.sort(); lo=samples[int(.025*iterations)]; hi=samples[int(.975*iterations)]
            summary.append({"strategy":strategy,"metric":metric,"estimate":point,"ci_low":lo,"ci_high":hi,"bootstrap_unit":"trajectory","n_trajectories":len(tids)})
    pairwise=[]
    for reference,strategy in combinations(strategies,2):
        for metric in ("task_success","old_goal_conflict"):
            diffs=[rates[(t,strategy)][metric]-rates[(t,reference)][metric] for t in tids]
            point=sum(diffs)/len(diffs); samples=[]
            for _ in range(iterations):
                draw=[rng.choice(diffs) for _ in diffs]; samples.append(sum(draw)/len(draw))
            samples.sort()
            pairwise.append({"strategy":strategy,"reference":reference,"metric":metric,"absolute_difference":point,
                             "ci_low":samples[int(.025*iterations)],"ci_high":samples[int(.975*iterations)],
                             "wins":sum(d>0 for d in diffs),"ties":sum(d==0 for d in diffs),"losses":sum(d<0 for d in diffs),"n_trajectories":len(tids)})
    return summary,pairwise
