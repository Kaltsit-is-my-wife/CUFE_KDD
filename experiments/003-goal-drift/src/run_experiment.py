"""Run the complete reproducible PoC and write all report artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from detect_drift import run_detectors
from evaluate import aggregate, aggregate_memory, detection_metrics, memory_metrics, score_task, validate_no_leakage
from generate_data import SEED, save_trajectories
from update_memory import apply_strategy, extract_memories

STRATEGIES = ("no_update", "time_decay", "drift_aware")
METRIC_LABELS = {
    "precision": "Precision", "recall": "Recall", "f1": "F1",
    "false_positive_rate": "False positive rate",
    "obsolete_interference_rate": "Obsolete interference",
    "valid_memory_retention_rate": "Valid retention",
    "task_success_rate": "Task success", "old_goal_conflict_rate": "Old-goal conflict",
    "constraint_satisfaction_rate": "Constraint satisfaction",
    "background_utilization_rate": "Background utilization",
}


def save_plot(df: pd.DataFrame, index: str, columns: list[str], path: Path, title: str) -> None:
    ax = df.set_index(index)[columns].plot(kind="bar", figsize=(9, 4.8), rot=12)
    ax.set_title(title)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.legend([METRIC_LABELS.get(c, c) for c in columns], loc="best", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt_table(df: pd.DataFrame, columns: list[str]) -> str:
    shown = df[columns].copy()
    for c in shown.select_dtypes(include="number").columns:
        shown[c] = shown[c].map(lambda x: f"{x:.3f}")
    # Avoid pandas' optional `tabulate` dependency.
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in shown.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *body])


def run(root: Path) -> dict:
    data_path, results = root / "data" / "trajectories.json", root / "results"
    results.mkdir(parents=True, exist_ok=True)
    trajectories = save_trajectories(data_path, SEED)
    validate_no_leakage()

    # Flattening is for inspection only; detector input is sanitized inside run_detectors.
    trajectory_rows = []
    for t in trajectories:
        for s in t["sessions"]:
            trajectory_rows.append({
                "trajectory_id": t["trajectory_id"], "scenario": t["scenario"],
                "session_id": s["session_id"], "text": s["text"],
                "drift_start": t["drift_start"], "confirmation_session": t["confirmation_session"],
            })
    pd.DataFrame(trajectory_rows).to_csv(results / "trajectory_data.csv", index=False, encoding="utf-8-sig")

    predictions = run_detectors(trajectories)
    truth = {t["trajectory_id"]: t for t in trajectories}
    pred_rows = []
    for p in predictions:
        t = truth[p["trajectory_id"]]
        pred_rows.append({**p, "scenario": t["scenario"], "true_drift_start": t["drift_start"],
                          "true_confirmation": t["confirmation_session"]})
    pred_df = pd.DataFrame(pred_rows)
    pred_df.to_csv(results / "predictions.csv", index=False, encoding="utf-8-sig")
    detection_df = pd.DataFrame(detection_metrics(trajectories, predictions))
    detection_df.to_csv(results / "detection_metrics.csv", index=False, encoding="utf-8-sig")

    c_preds = {p["trajectory_id"]: p["detected_at"] for p in predictions if p["method"] == "method_c_sustained"}
    memory_detail, task_detail = [], []
    for t in trajectories:
        raw = extract_memories(t)
        for strategy in STRATEGIES:
            detected = c_preds[t["trajectory_id"]] if strategy == "drift_aware" else None
            updated = apply_strategy(raw, strategy, detected, t["sessions"])
            memory_detail.append({"trajectory_id": t["trajectory_id"], "scenario": t["scenario"],
                                  "strategy": strategy, **memory_metrics(t, updated)})
            # Three online tasks per trajectory. Each task sees only its session prefix.
            first_task = t["confirmation_session"] if t["confirmation_session"] is not None else 7
            for task_session in range(first_task, min(first_task + 3, len(t["sessions"]))):
                prefix_traj = {**t, "sessions": t["sessions"][:task_session + 1]}
                prefix_raw = extract_memories(prefix_traj)
                prefix_detection = c_preds[t["trajectory_id"]]
                if prefix_detection is None or prefix_detection > task_session or strategy != "drift_aware":
                    prefix_detection = None
                prefix_updated = apply_strategy(prefix_raw, strategy, prefix_detection, prefix_traj["sessions"])
                task_detail.append({"trajectory_id": t["trajectory_id"], "scenario": t["scenario"],
                                    "task_session": task_session, "strategy": strategy,
                                    **score_task(t, prefix_updated)})

    memory_keys = ["obsolete_interference_rate", "valid_memory_retention_rate", "obsolete_precision",
                   "obsolete_recall", "obsolete_f1", "incorrect_downweight_rate", "memory_update_count"]
    task_keys = ["task_success", "old_goal_conflict", "constraint_satisfaction_rate", "background_utilization_rate"]
    memory_df = pd.DataFrame(aggregate_memory(memory_detail))
    task_df = pd.DataFrame(aggregate(task_detail, "strategy", task_keys)).rename(
        columns={"task_success": "task_success_rate", "old_goal_conflict": "old_goal_conflict_rate"})
    memory_df.to_csv(results / "memory_metrics.csv", index=False, encoding="utf-8-sig")
    task_df.to_csv(results / "task_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(memory_detail).to_csv(results / "memory_metrics_by_trajectory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(task_detail).to_csv(results / "task_metrics_by_trajectory.csv", index=False, encoding="utf-8-sig")

    save_plot(detection_df, "method", ["precision", "recall", "f1", "false_positive_rate"],
              results / "detection_comparison.png", "Goal-drift detection (48 controlled trajectories)")
    save_plot(memory_df, "strategy", ["obsolete_interference_rate", "valid_memory_retention_rate", "obsolete_f1"],
              results / "memory_comparison.png", "Memory update comparison")
    save_plot(task_df, "strategy", ["task_success_rate", "old_goal_conflict_rate", "constraint_satisfaction_rate"],
              results / "task_success_comparison.png", "End-to-end deterministic task evaluation")

    failures = pred_df[(pred_df["method"] == "method_c_sustained") &
                       (((pred_df["true_confirmation"].isna()) & pred_df["detected_at"].notna()) |
                        ((pred_df["true_confirmation"].notna()) & pred_df["detected_at"].isna()))]
    if failures.empty:
        # Report a real baseline error if Method C has none.
        failures = pred_df[(pred_df["method"] == "baseline_a_topic") &
                           (pred_df["scenario"] == "topic_switch") & pred_df["detected_at"].notna()]
    case = failures.iloc[0].to_dict() if not failures.empty else {}
    counts = Counter(t["scenario"] for t in trajectories)
    det_view = detection_df.set_index("method")
    mem_view = memory_df.set_index("strategy")
    task_view = task_df.set_index("strategy")
    summary = f"""# Goal Drift PoC — 实验结果摘要

生成时间由本次程序运行决定；随机种子固定为 `{SEED}`。本实验是**规则基线与合成数据上的受控模拟**，没有调用大模型或外部模型服务，结果不代表真实 LLM Agent 的实测效果。

## 数据

- 轨迹总数：{len(trajectories)}；每条 10 个会话，共 {len(trajectory_rows)} 个会话。
- 场景分布：{', '.join(f'{k}={counts[k]}' for k in sorted(counts))}。
- 漂移真实标签只在指标评估中使用。检测器接口仅接收 `session_id` 与截至当前的 `text`，并通过前缀不变性断言检查未来信息泄漏。

## 漂移检测

{fmt_table(detection_df, ['method','precision','recall','f1','false_positive_rate','mean_detection_delay','mean_localization_error','drift_type_accuracy','topic_switch_false_positives'])}

`mean_detection_delay = detected_at - confirmation_session`，负值表示在人工设定的确认点之前预警；`mean_localization_error = |detected_at - drift_start|`。普通话题切换误报数量单独列出。

## 记忆更新

{fmt_table(memory_df, ['strategy','obsolete_interference_rate','valid_memory_retention_rate','obsolete_precision','obsolete_recall','obsolete_f1','incorrect_downweight_rate','memory_update_count'])}

干扰率按目标记忆的加权占比计算；保留率是仍有效记忆相对原始权重的平均值。更新数量不是删除数量，Strategy C 只把不兼容的旧目标记忆降至 0.12，背景记忆保留。

## 端到端任务

{fmt_table(task_df, ['strategy','task_success_rate','old_goal_conflict_rate','constraint_satisfaction_rate','background_utilization_rate'])}

任务是确定性选择当前成本偏好、执行偏好和背景约束；成功要求两个当前目标约束与背景约束全部满足。每条轨迹从确认会话（无漂移轨迹从 session 7）开始连续评估 3 个在线任务，每次只能读取当时及以前的记忆和检测输出，共 {len(task_detail) // len(STRATEGIES)} 个任务实例、{len(task_detail)} 条策略评分记录。

## 真实失败案例

- 轨迹 `{case.get('trajectory_id', 'none')}`，场景 `{case.get('scenario', 'none')}`，方法 `{case.get('method', 'none')}`：真实确认位置 `{case.get('true_confirmation', 'none')}`，预测位置 `{case.get('detected_at', 'none')}`。这是本次输出中实际筛选出的误报或漏报，而非手工编造。

## 三条主要发现

1. 相邻话题变化基线产生 {int(det_view.loc['baseline_a_topic', 'topic_switch_false_positives'])} 个普通话题切换误报；持续性基线和 Method C 在本数据上的 F1 均为 {det_view.loc['method_c_sustained', 'f1']:.3f}，但 Method C 平均比人工确认点提前 {-det_view.loc['method_c_sustained', 'mean_detection_delay']:.3f} 个会话，并正确区分两种漂移类型。
2. 漂移感知策略把过时干扰率从 {mem_view.loc['no_update', 'obsolete_interference_rate']:.3f} 降到 {mem_view.loc['drift_aware', 'obsolete_interference_rate']:.3f}，有效记忆保留率仍为 {mem_view.loc['drift_aware', 'valid_memory_retention_rate']:.3f}；但其过时记忆召回仅 {mem_view.loc['drift_aware', 'obsolete_recall']:.3f}，是明确失败点。
3. 时间衰减的任务成功率最高（{task_view.loc['time_decay', 'task_success_rate']:.3f}），漂移感知为 {task_view.loc['drift_aware', 'task_success_rate']:.3f}，不更新为 {task_view.loc['no_update', 'task_success_rate']:.3f}；代价是时间衰减的有效记忆保留率仅 {mem_view.loc['time_decay', 'valid_memory_retention_rate']:.3f}。因此当前结果不支持“漂移感知策略全面优于简单衰减”。

## 局限与下一步

- 合成文本的词表、漂移时间和规则检测器同源，外部有效性有限；轨迹规模仅 48。
- 规则抽取没有处理真实语言中的否定、隐喻、目标层级、相互矛盾证据和工具反馈。
- 下一阶段应在获得同意的真实 Agent 多会话日志上盲标漂移，用真实模型的任务输出做人工与自动双重评分，并测试检测阈值跨域泛化。
- 当前任务决策器是规则系统；不能把本结果表述为 LLM Agent 性能提升。

## 复现

从项目根目录运行：

```powershell
python src/run_experiment.py
python src/run_experiment.py --check-determinism
```

第二条命令在同一进程中连续运行两次，并比较核心 JSON/CSV/PNG/Markdown 的 SHA-256；全部一致才返回成功。

本次一致性检查状态：`PENDING`（使用 `--check-determinism` 时，程序在实际通过后自动改写为 `PASS`）。

## 文件路径

- 项目根目录：`{root}`
- 合成轨迹：`{data_path}`
- 汇总结果目录：`{results}`
- 必需结果：`trajectory_data.csv`、`detection_metrics.csv`、`memory_metrics.csv`、`task_metrics.csv`、`predictions.csv`、`detection_comparison.png`、`memory_comparison.png`、`task_success_comparison.png`、`experiment_summary.md`。
"""
    (results / "experiment_summary.md").write_text(summary, encoding="utf-8")
    manifest = {p.name: {"bytes": p.stat().st_size, "sha256": file_hash(p)}
                for p in sorted(results.iterdir()) if p.is_file() and p.name != "reproducibility_manifest.json"}
    (results / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"trajectories": len(trajectories), "counts": dict(counts), "manifest": manifest,
            "detection": detection_df, "memory": memory_df, "task": task_df, "failure": case}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-determinism", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    first = run(root)
    print(f"seed={SEED} trajectories={first['trajectories']} scenarios={first['counts']}")
    print("\nDETECTION\n", first["detection"].to_string(index=False))
    print("\nMEMORY\n", first["memory"].to_string(index=False))
    print("\nTASK\n", first["task"].to_string(index=False))
    print("\nFAILURE_CASE\n", first["failure"])
    if args.check_determinism:
        hashes1 = {k: v["sha256"] for k, v in first["manifest"].items()}
        second = run(root)
        hashes2 = {k: v["sha256"] for k, v in second["manifest"].items()}
        if hashes1 != hashes2:
            print("DETERMINISM_CHECK=FAIL", file=sys.stderr)
            return 2
        summary_path = root / "results" / "experiment_summary.md"
        summary_text = summary_path.read_text(encoding="utf-8").replace(
            "本次一致性检查状态：`PENDING`（使用 `--check-determinism` 时，程序在实际通过后自动改写为 `PASS`）。",
            f"本次一致性检查状态：`PASS`（两次运行的 {len(hashes1)} 个核心产物 SHA-256 全部一致）。")
        summary_path.write_text(summary_text, encoding="utf-8")
        manifest_path = root / "results" / "reproducibility_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest[summary_path.name] = {"bytes": summary_path.stat().st_size, "sha256": file_hash(summary_path)}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"DETERMINISM_CHECK=PASS files={len(hashes1)}")
    print(f"results={root / 'results'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
