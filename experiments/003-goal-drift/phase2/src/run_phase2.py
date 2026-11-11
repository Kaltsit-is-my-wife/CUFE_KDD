"""Run phase-2 audit, dev-only tuning, blind test evaluation, and reports."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from detectors import METHODS, predict
from evaluation import aggregate_memory, bootstrap_task, detection_rows
from generate_phase2 import SCENARIOS, SEED, save_data
from memory_and_tasks import apply_strategy, extract_memories, memory_counts, score_task

STRATEGIES = ("no_update", "time_decay", "drift_aware_original", "drift_aware_improved")
BOOTSTRAP_SEED = 20261026


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    view = df[columns].copy()
    for col in view.select_dtypes(include="number"):
        view[col] = view[col].map(lambda x: "NA" if pd.isna(x) else f"{x:.3f}")
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in view.itertuples(index=False, name=None)]
    return "\n".join(lines)


def tune_detector(method: str, observable: list[dict], labels: list[dict]) -> tuple[dict, list[dict]]:
    if method == "baseline_a_topic":
        grids = [{}]
    elif method == "baseline_b_persistence":
        grids = [{"window": w, "persistence": p} for w in (2,3,4) for p in (1,2,3)]
    elif method == "method_c_original":
        grids = [{"threshold": x, "persistence": p} for x in (0.3,0.6,0.9,1.2) for p in (1,2,3)]
    else:
        grids = [{"alpha":a,"margin":m,"confirmations":c,"gap":g}
                 for a,m,c,g in itertools.product((0.45,0.65,0.8),(0.1,0.25,0.45),(1,2,3),(1,2,3))]
    trials=[]; best=None
    for params in grids:
        preds=[]
        for traj in observable:
            result=METHODS[method](traj["sessions"],params)
            preds.append({"trajectory_id":traj["trajectory_id"],"method":method,**result})
        metrics,_=detection_rows(preds,labels)
        overall=next(x for x in metrics if x["group"]=="overall")
        score=overall["f1"]-0.15*overall["false_positive_rate"]+0.05*overall["localization_hit_rate_tolerance_2"]
        trials.append({"method":method,"params":json.dumps(params,sort_keys=True),"objective":score,**overall})
        key=(score,overall["f1"],-overall["false_positive_rate"],-len(json.dumps(params)))
        if best is None or key>best[0]: best=(key,params)
    return best[1],trials


def prediction_map(rows: list[dict]) -> dict[tuple[str,str],dict]:
    return {(x["trajectory_id"],x["method"]):x for x in rows}


def evaluate_strategies(observable: list[dict], labels: list[dict], predictions: list[dict],
                        memory_params: dict[str,dict]) -> tuple[list[dict],list[dict]]:
    obs={x["trajectory_id"]:x for x in observable}; pmap=prediction_map(predictions)
    memory_detail=[]; task_detail=[]
    detector_for={"drift_aware_original":"method_c_original","drift_aware_improved":"method_d_evidence"}
    for label in labels:
        tid=label["trajectory_id"]; sessions=obs[tid]["sessions"]
        final_goal=tuple(label["current_goals"][-1]); bg=label["background"]["value"]
        for strategy in STRATEGIES:
            det=pmap.get((tid,detector_for.get(strategy,"")))
            raw=extract_memories(sessions)
            updated=apply_strategy(raw,sessions,strategy,det,memory_params.get(strategy,{}))
            for counts in memory_counts(updated,final_goal,bg):
                memory_detail.append({"trajectory_id":tid,"scenario":label["scenario"],"strategy":strategy,
                                      "evaluation_scope":"final","task_id":None,**counts})
            for task in label["tasks"]:
                prefix=sessions[:task["session_id"]+1]; raw_prefix=extract_memories(prefix)
                upd_prefix=apply_strategy(raw_prefix,prefix,strategy,det,memory_params.get(strategy,{}))
                for counts in memory_counts(upd_prefix,tuple(task["required_goal"]),bg):
                    memory_detail.append({"trajectory_id":tid,"scenario":label["scenario"],"strategy":strategy,
                                          "evaluation_scope":"online_task","task_id":task["task_id"],**counts})
                task_detail.append({"trajectory_id":tid,"scenario":label["scenario"],"task_id":task["task_id"],
                                    "task_session":task["session_id"],"strategy":strategy,
                                    **score_task(task,upd_prefix,bg,tuple(label["initial_goal"]))})
    return memory_detail,task_detail


def tune_memory(dev_obs: list[dict],dev_labels: list[dict],dev_preds: list[dict]) -> tuple[dict,list[dict]]:
    trials=[]
    # Time decay is selected by paired dev task success, with no test access.
    best_td=None
    for rate in (0.06,0.10,0.14,0.18,0.24,0.30):
        params={"time_decay":{"decay_rate":rate},"drift_aware_original":{},
                "drift_aware_improved":{"lookback":3,"confirm_margin":0.4}}
        mem,tasks=evaluate_strategies(dev_obs,dev_labels,dev_preds,params)
        rows=[x for x in tasks if x["strategy"]=="time_decay"]
        success=sum(x["task_success"] for x in rows)/len(rows)
        retention=next(x for x in aggregate_memory([x for x in mem if x["strategy"]=="time_decay"]) if x["category"]=="overall" and x["evaluation_scope"]=="online_task")["valid_memory_retention_rate"]
        objective=success+0.10*retention
        trials.append({"strategy":"time_decay","params":json.dumps({"decay_rate":rate}),"objective":objective,"task_success":success,"valid_retention":retention})
        if best_td is None or (objective,-rate)>best_td[0]: best_td=((objective,-rate),{"decay_rate":rate})
    best_imp=None
    for lookback,margin in itertools.product((2,3,4,5),(0.15,0.35,0.55,0.8)):
        params={"time_decay":best_td[1],"drift_aware_original":{},
                "drift_aware_improved":{"lookback":lookback,"confirm_margin":margin}}
        mem,tasks=evaluate_strategies(dev_obs,dev_labels,dev_preds,params)
        task_rows=[x for x in tasks if x["strategy"]=="drift_aware_improved"]
        success=sum(x["task_success"] for x in task_rows)/len(task_rows)
        overall=next(x for x in aggregate_memory([x for x in mem if x["strategy"]=="drift_aware_improved"]) if x["category"]=="overall" and x["evaluation_scope"]=="online_task")
        objective=success-0.20*overall["obsolete_interference_rate"]+0.10*overall["valid_memory_retention_rate"]
        trial={"strategy":"drift_aware_improved","params":json.dumps({"lookback":lookback,"confirm_margin":margin}),
               "objective":objective,"task_success":success,"valid_retention":overall["valid_memory_retention_rate"]}
        trials.append(trial)
        if best_imp is None or (objective,-lookback,-margin)>best_imp[0]: best_imp=((objective,-lookback,-margin),{"lookback":lookback,"confirm_margin":margin})
    return {"no_update":{},"time_decay":best_td[1],"drift_aware_original":{},"drift_aware_improved":best_imp[1]},trials


def phase1_snapshot(root: Path) -> dict:
    files=list((root/"src").glob("*.py"))+[root/"data"/"trajectories.json"]+list((root/"results").glob("*.csv"))+list((root/"results").glob("*.png"))+[root/"results"/"experiment_summary.md"]
    return {str(p.relative_to(root)).replace("\\","/"):{"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(files) if p.exists()}


def write_audit(path: Path,snapshot: dict) -> None:
    source_hashes={k:v["sha256"] for k,v in snapshot.items() if k.startswith("src/")}
    text=f"""# Phase 2：第一阶段代码审计

审计先于第二阶段算法修改完成。第一阶段 `src/`、`data/`、`results/` 未被第二阶段程序写入；完整 SHA-256 快照见 `phase1_snapshot.json`。

## 结论

1. **没有发现检测器直接标签泄漏。** `src/detect_drift.py:128-131` 显式构造仅含 `session_id/text` 的输入；三个检测函数按会话顺序运行。真实标签只在 `src/evaluate.py:11-48` 合并评估。前缀测试较弱但方向正确。
2. **存在显著的数据—规则同源。** `generate_data.py` 只使用三组固定目标对，突变固定在 session 5，渐进固定在 4--7；生成器直接插入英文目标 token。`detect_drift.py` 使用同一组 token/中文短语以及与生成模式一致的持续阈值，因此 Baseline B 和 Method C 的 F1=1.0 不能视为跨分布证据。
3. **Method C 的漂移类型识别也依赖生成痕迹。** 渐进轨迹提前插入英文新目标 token，`prior_alternative_evidence` 正是累计这些 token；类型准确率 1.0 高度受模板结构影响。
4. **未发现时间衰减读取标签。** 其权重只依赖年龄；但第一阶段每个会话都重复背景约束，任务又给真实当前目标固定 `+2.2` 分，恰好让近期目标占优且背景永不丢失。这解释了 100% Task Success，属于评估偏向/难度不足，不是标签泄漏。
5. **在线任务没有未来会话更新。** `run_experiment.py:99-108` 使用任务时点前缀。不过任务时点由真实 `confirmation_session` 选择，这是评估调度信息；它没有传给策略，但会让漂移任务集中在预设位置。
6. **任务实例存在轨迹内相关性。** 144 个任务来自 48 条轨迹，第一阶段只报任务级均值，没有轨迹级置信区间，不能把 144 个任务当成独立样本。
7. **原始漂移感知召回低的机制原因。** 它只降权报警时点之前、与最近两会话主导目标冲突的长期目标记忆；报警后抽取到的冲突/历史记忆不会处理，低置信证据也没有待确认状态。

## 第二阶段修复

- 168 条变长轨迹、随机漂移时点、七类场景（含单独稳定场景）、表达缺失/反复/临时意图/历史提及/稀疏背景。
- 按完整轨迹分为 56 条开发集和 112 条测试集；所有阈值只用开发集。
- 交互与标签分文件；检测进程接口只读交互，评估模块随后独立合并标签。
- 新任务减少当前目标直接信号，背景只稀疏出现；四策略共享完全相同的任务实例。
- 统计以完整轨迹为 Bootstrap 单位，避免伪重复。

第一阶段源码哈希：

```json
{json.dumps(source_hashes,indent=2)}
```
"""
    path.write_text(text,encoding="utf-8")


def plot_results(det: pd.DataFrame,mem: pd.DataFrame,task: pd.DataFrame,out: Path) -> None:
    overall=det[det.group=="overall"].set_index("method")
    overall[["precision","recall","f1","false_positive_rate","localization_hit_rate_tolerance_2"]].plot(kind="bar",figsize=(10,5),ylim=(0,1.05),rot=15,title="Phase 2 blind-test drift detection")
    plt.tight_layout(); plt.savefig(out/"phase2_detection_comparison.png",dpi=160); plt.close()
    m=mem[(mem.category=="overall") & (mem.evaluation_scope=="online_task")].set_index("strategy")
    m[["obsolete_interference_rate","valid_memory_retention_rate","obsolete_f1"]].plot(kind="bar",figsize=(10,5),ylim=(0,1.05),rot=15,title="Memory interference-retention trade-off")
    plt.tight_layout(); plt.savefig(out/"phase2_memory_tradeoff.png",dpi=160); plt.close()
    t=task[task.metric.isin(["task_success","old_goal_conflict","background_retention_rate"])].pivot(index="strategy",columns="metric",values="estimate")
    t.plot(kind="bar",figsize=(10,5),ylim=(0,1.05),rot=15,title="Paired end-to-end tasks (trajectory bootstrap)")
    plt.tight_layout(); plt.savefig(out/"phase2_task_comparison.png",dpi=160); plt.close()


def run(root: Path) -> dict:
    phase=root/"phase2"; out=phase/"results"; out.mkdir(parents=True,exist_ok=True)
    snapshot=phase1_snapshot(root)
    (phase/"phase1_snapshot.json").write_text(json.dumps(snapshot,indent=2),encoding="utf-8")
    write_audit(out/"phase2_audit.md",snapshot)
    observable,labels=save_data(phase)
    # Reload separately to enforce the blind module boundary.
    interactions=json.loads((phase/"data"/"interactions.json").read_text(encoding="utf-8"))
    all_labels=json.loads((phase/"data"/"labels.json").read_text(encoding="utf-8"))
    dev_obs=[x for x in interactions if x["split"]=="dev"]; test_obs=[x for x in interactions if x["split"]=="test"]
    dev_labels=[x for x in all_labels if x["split"]=="dev"]; test_labels=[x for x in all_labels if x["split"]=="test"]

    params={}; tuning=[]
    for method in METHODS:
        params[method],trials=tune_detector(method,dev_obs,dev_labels); tuning.extend(trials)
    dev_preds=predict(dev_obs,params)
    memory_params,memory_tuning=tune_memory(dev_obs,dev_labels,dev_preds)
    test_preds=predict(test_obs,params)  # one final test pass
    det_metrics,joined=detection_rows(test_preds,test_labels)
    mem_detail,task_detail=evaluate_strategies(test_obs,test_labels,test_preds,memory_params)
    mem_metrics=aggregate_memory(mem_detail)
    task_metrics,pairwise=bootstrap_task(task_detail,BOOTSTRAP_SEED)

    label_map={x["trajectory_id"]:x for x in all_labels}
    flat=[]
    for traj in interactions:
        lab=label_map[traj["trajectory_id"]]
        for s in traj["sessions"]:
            flat.append({"trajectory_id":traj["trajectory_id"],"split":traj["split"],"scenario":lab["scenario"],
                         "session_id":s["session_id"],"text":s["text"],"current_goal":"+".join(lab["current_goals"][s["session_id"]]),
                         "has_drift":lab["has_drift"],"drift_onset":lab["drift_onset"],"confirmation_session":lab["confirmation_session"]})
    pd.DataFrame(flat).to_csv(out/"phase2_trajectory_data.csv",index=False,encoding="utf-8-sig")
    det_df=pd.DataFrame(det_metrics); pred_df=pd.DataFrame(joined); mem_df=pd.DataFrame(mem_metrics)
    task_df=pd.DataFrame(task_metrics); pair_df=pd.DataFrame(pairwise)
    det_df.to_csv(out/"phase2_detection_metrics.csv",index=False,encoding="utf-8-sig")
    pred_df.to_csv(out/"phase2_predictions.csv",index=False,encoding="utf-8-sig")
    mem_df.to_csv(out/"phase2_memory_metrics.csv",index=False,encoding="utf-8-sig")
    task_df.to_csv(out/"phase2_task_metrics.csv",index=False,encoding="utf-8-sig")
    pair_df.to_csv(out/"phase2_task_pairwise.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(task_detail).to_csv(out/"phase2_task_details.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(mem_detail).to_csv(out/"phase2_memory_details.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(tuning).to_csv(out/"phase2_detection_dev_tuning.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(memory_tuning).to_csv(out/"phase2_memory_dev_tuning.csv",index=False,encoding="utf-8-sig")

    failures=[]
    for x in joined:
        if x["error_type"] not in {"correct_rejection","on_time"}:
            failures.append({"record_type":"detection","trajectory_id":x["trajectory_id"],"scenario":x["scenario"],"method_or_strategy":x["method"],"error_type":x["error_type"],"location":x["detected_at"],"details":f"true_onset={x['true_onset']}; delay={x['detection_delay']}"})
    for x in task_detail:
        if not x["task_success"]:
            failures.append({"record_type":"task","trajectory_id":x["trajectory_id"],"scenario":x["scenario"],"method_or_strategy":x["strategy"],"error_type":"task_failure","location":x["task_session"],"details":x["failure_reason"]})
    fail_df=pd.DataFrame(failures); fail_df.to_csv(out/"phase2_failure_cases.csv",index=False,encoding="utf-8-sig")
    plot_results(det_df,mem_df,task_df,out)

    counts=Counter((x["split"],x["scenario"]) for x in all_labels)
    overall_det=det_df[det_df.group=="overall"]
    overall_mem=mem_df[(mem_df.category=="overall") & (mem_df.evaluation_scope=="online_task")]
    success=task_df[task_df.metric=="task_success"]
    conflict=task_df[task_df.metric=="old_goal_conflict"]
    det_view=overall_det.set_index("method"); mem_view=overall_mem.set_index("strategy"); task_view=success.set_index("strategy")
    stable_view=det_df[det_df.group=="stable"].set_index("method")
    temporary_view=det_df[det_df.group=="temporary_shift"].set_index("method")
    imp_vs_orig=pair_df[(pair_df.strategy=="drift_aware_original") & (pair_df.reference=="drift_aware_improved") & (pair_df.metric=="task_success")].iloc[0]
    d_false=pred_df[(pred_df.method=="method_d_evidence") & (pred_df.error_type=="false_positive")].iloc[0]
    c_miss=pred_df[(pred_df.method=="method_c_original") & (pred_df.error_type=="miss")].iloc[0]
    imp_task_fail=next(x for x in task_detail if x["strategy"]=="drift_aware_improved" and not x["task_success"])
    summary=f"""# Phase 2 Goal Drift PoC 实验总结

本实验是规则方法和合成数据的受控验证，不是真实 LLM Agent 实测。生成种子 `{SEED}`，轨迹级 Bootstrap 种子 `{BOOTSTRAP_SEED}`。

## 数据与盲测边界

- 共 {len(all_labels)} 条轨迹；开发集 {len(dev_labels)}，测试集 {len(test_labels)}。按完整轨迹划分，无会话跨组。
- 测试集每场景 16 条；检测器只读 `data/interactions.json`，预测完成后评估器才读取 `data/labels.json`。
- 检测、记忆阈值只通过开发集选择；测试集只运行一次最终配置。选定参数见 manifest。

## 测试集检测

{markdown_table(overall_det,['method','precision','recall','f1','false_positive_rate','localization_hit_rate_tolerance_2','mean_abs_localization_error','mean_detection_delay','tp','fp','fn','tn'])}

无漂移轨迹的 Detection Delay 保持 NA，只单独计误报。分场景结果见 `phase2_detection_metrics.csv`。

## 测试集记忆（在线任务时点 overall）

{markdown_table(overall_mem,['strategy','obsolete_precision','obsolete_recall','obsolete_f1','obsolete_interference_rate','valid_memory_retention_rate','incorrect_downweight_rate','mean_update_count'])}

分类别与轨迹末端结果也在同一 CSV 中，以 `evaluation_scope` 区分。低干扰不能脱离有效记忆保留率解读。

## 配对任务与轨迹级 95% Bootstrap CI

{markdown_table(success,['strategy','estimate','ci_low','ci_high','n_trajectories'])}

旧目标冲突率：

{markdown_table(conflict,['strategy','estimate','ci_low','ci_high','n_trajectories'])}

所有策略共享同一批轨迹、任务、当前要求。CI 以完整测试轨迹重采样，而非把同轨迹的多个任务当独立样本。配对差异见 `phase2_task_pairwise.csv`；CI 覆盖 0 时不宣称可靠优势。

## 失败与解释

- Method D 相对 Method C：F1 从 {det_view.loc['method_c_original','f1']:.3f} 提升到 {det_view.loc['method_d_evidence','f1']:.3f}，FPR 从 {det_view.loc['method_c_original','false_positive_rate']:.3f} 降到 {det_view.loc['method_d_evidence','false_positive_rate']:.3f}；代价是平均延迟从 {det_view.loc['method_c_original','mean_detection_delay']:.3f} 增至 {det_view.loc['method_d_evidence','mean_detection_delay']:.3f}。
- 稳定场景四个方法的 FPR 分别为：A={stable_view.loc['baseline_a_topic','false_positive_rate']:.3f}、B={stable_view.loc['baseline_b_persistence','false_positive_rate']:.3f}、C={stable_view.loc['method_c_original','false_positive_rate']:.3f}、D={stable_view.loc['method_d_evidence','false_positive_rate']:.3f}。Method D 的误报全部来自更难的短暂变化场景（该场景 FPR={temporary_view.loc['method_d_evidence','false_positive_rate']:.3f}）。
- 改进记忆的在线过时召回从原始策略 {mem_view.loc['drift_aware_original','obsolete_recall']:.3f} 提升至 {mem_view.loc['drift_aware_improved','obsolete_recall']:.3f}，但任务成功率从 {task_view.loc['drift_aware_original','estimate']:.3f} 降至 {task_view.loc['drift_aware_improved','estimate']:.3f}。原始减改进的配对差为 {imp_vs_orig['absolute_difference']:.3f}，95% CI [{imp_vs_orig['ci_low']:.3f}, {imp_vs_orig['ci_high']:.3f}]；主要机制是 Method D 更晚报警，确认点附近任务尚未完成旧目标降权。
- 时间衰减任务成功率为 {task_view.loc['time_decay','estimate']:.3f}，不再是 1.0；与不更新的差为 {pair_df[(pair_df.strategy=='time_decay') & (pair_df.reference=='no_update') & (pair_df.metric=='task_success')].iloc[0]['absolute_difference']:.3f}，其区间覆盖 0，且背景会随年龄丢失。
- 代表性案例：Method D 在 `{d_false['trajectory_id']}`（短暂变化）于 session {d_false['detected_at']} 误报；Method C 漏掉 `{c_miss['trajectory_id']}`；改进记忆在 `{imp_task_fail['trajectory_id']}` 的 session {imp_task_fail['task_session']} 因 `{imp_task_fail['failure_reason']}` 任务失败。
- 全部误报、漏报、提前/延迟报警及任务失败保存在 `phase2_failure_cases.csv`，没有删除不利样本。

## 限制

- 仍是合成英文表达和人工词典；生成器与抽取器虽分离潜变量/标签，但仍共享有限语义域。
- 当前测试轨迹足以给出轨迹级不确定区间，但不足以证明跨领域或真实 Agent 泛化。
- Bootstrap CI 是描述性非参数区间，没有进行多重比较校正；不应过度解释边界结果。
- 实施中发现并修复了临时区间抽样和在线记忆指标口径错误，因此测试流程在修复后重跑。检测与记忆阈值始终由开发集自动选择、没有按测试指标手工调节，但本测试仍不等同于从未暴露的一次性外部盲测。

本次重复性检查：`PENDING`。
"""
    (out/"phase2_summary.md").write_text(summary,encoding="utf-8")
    manifest={"seeds":{"data":SEED,"bootstrap":BOOTSTRAP_SEED},"python":platform.python_version(),
              "pandas":pd.__version__,"trajectory_counts":{f"{k[0]}:{k[1]}":v for k,v in sorted(counts.items())},
              "detector_params":params,"memory_params":memory_params,"bootstrap_iterations":2000,
              "phase1_snapshot_sha256":sha(phase/"phase1_snapshot.json")}
    files={p.name:{"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!="phase2_manifest.json"}
    manifest["files"]=files
    (out/"phase2_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return {"counts":counts,"params":params,"memory_params":memory_params,"detection":overall_det,"memory":overall_mem,"task":success,"pairwise":pair_df,"failures":fail_df,"hashes":{k:v["sha256"] for k,v in files.items()}}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--check-determinism",action="store_true"); args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    first=run(root)
    print("COMMAND=python phase2/src/run_phase2.py" + (" --check-determinism" if args.check_determinism else ""))
    print("SCENARIOS",dict(first["counts"])); print("DETECTOR_PARAMS",first["params"]); print("MEMORY_PARAMS",first["memory_params"])
    print("\nDETECTION TEST\n",first["detection"].to_string(index=False)); print("\nMEMORY TEST\n",first["memory"].to_string(index=False))
    print("\nTASK SUCCESS WITH CI\n",first["task"].to_string(index=False)); print("\nPAIRED DIFFERENCES\n",first["pairwise"].to_string(index=False))
    print("FAILURE_CASES",len(first["failures"]),"results=",root/"phase2"/"results")
    if args.check_determinism:
        second=run(root)
        if first["hashes"]!=second["hashes"]:
            print("DETERMINISM_CHECK=FAIL",file=sys.stderr); return 2
        out=root/"phase2"/"results"; report=out/"phase2_summary.md"
        report.write_text(report.read_text(encoding="utf-8").replace("本次重复性检查：`PENDING`。",f"本次重复性检查：`PASS`（{len(first['hashes'])} 个产物两次运行 SHA-256 一致）。"),encoding="utf-8")
        manifest_path=out/"phase2_manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["determinism_check"]={"status":"PASS","compared_files":len(first["hashes"])}
        manifest["files"][report.name]={"bytes":report.stat().st_size,"sha256":sha(report)}
        manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        print(f"DETERMINISM_CHECK=PASS files={len(first['hashes'])}")
    return 0


if __name__=="__main__": raise SystemExit(main())
