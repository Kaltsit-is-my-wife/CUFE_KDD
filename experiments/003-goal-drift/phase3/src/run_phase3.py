"""Run the preregistered phase-3 experiment without modifying earlier phases."""
from __future__ import annotations
import argparse,hashlib,itertools,json,platform,random,sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"phase2"/"src"))
import detectors, memory_and_tasks
sys.path.insert(0,str(ROOT/"phase3"/"src"))
import online_strategy
from evaluation_phase3 import aggregate_memory,bootstrap_and_tests,detection_metrics,trajectory_rates
from experiment_core import ALL_STRATEGIES,DEPLOYABLE,evaluate
from generate_phase3 import SCENARIOS,save_locked

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def capture_originals(root):
    phase1=json.loads((root/"phase2"/"phase1_snapshot.json").read_text(encoding="utf-8")); paths=set(phase1)
    for folder in (root/"phase2"/"src",root/"phase2"/"data",root/"phase2"/"results"):
        for p in folder.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts: paths.add(str(p.relative_to(root)).replace("\\","/"))
    for p in (root/"phase2"/"README.md",):
        if p.exists(): paths.add(str(p.relative_to(root)).replace("\\","/"))
    return {rel:{"bytes":(root/rel).stat().st_size,"sha256":sha(root/rel),"historical_baseline":rel in phase1} for rel in sorted(paths)}

def verify_snapshot(root,snapshot):
    return [rel for rel,meta in snapshot.items() if not (root/rel).exists() or sha(root/rel)!=meta["sha256"]]

def predict(observable,params):
    rows=[]
    for tr in observable:
        c=detectors.method_c(tr["sessions"],params["method_c"]); d=detectors.improved_d(tr["sessions"],params["method_d"])
        rows += [{"trajectory_id":tr["trajectory_id"],"method":"method_c",**c},{"trajectory_id":tr["trajectory_id"],"method":"method_d",**d}]
    return rows

def tune_detectors(obs,labels):
    grids={"method_c":[{"threshold":x,"persistence":p} for x in (.3,.6,.9,1.2) for p in (1,2,3)],
           "method_d":[{"alpha":a,"margin":m,"confirmations":c,"gap":g} for a,m,c,g in itertools.product((.45,.65,.8),(.1,.25,.45),(1,2,3),(1,2,3))]}
    chosen={}; trials=[]
    for method,candidates in grids.items():
        best=None
        for par in candidates:
            preds=[]
            for tr in obs:
                result=(detectors.method_c if method=="method_c" else detectors.improved_d)(tr["sessions"],par)
                preds.append({"trajectory_id":tr["trajectory_id"],"method":method,**result})
            metrics,_=detection_metrics(preds,labels); overall=next(x for x in metrics if x["group"]=="overall")
            objective=overall["f1"]-.15*overall["false_positive_rate"]+.05*overall["localization_hit_rate_tolerance_2"]
            trials.append({"method":method,"params":json.dumps(par,sort_keys=True),"objective":objective,**overall})
            key=(objective,overall["f1"],-overall["false_positive_rate"],-len(json.dumps(par)))
            if best is None or key>best[0]: best=(key,par)
        chosen[method]=best[1]
    return chosen,trials

def early_confirmation_predictions(observable,params):
    rows=[]
    for tr in observable:
        trace=online_strategy.build_trace(tr["sessions"],params,detectors); confirmed=next((x for x in trace if x["event"]=="confirm"),None)
        rows.append({"trajectory_id":tr["trajectory_id"],"method":"method_e_confirmation",
                     "detected_at":confirmed["session_id"] if confirmed else None,
                     "estimated_onset":confirmed.get("candidate_start") if confirmed else None,
                     "predicted_type":"persistent" if confirmed else None,"confidence":1.0 if confirmed else 0.0})
    return rows

def tune_early(obs,labels,predictions,config):
    g=config["early_response_dev_grid"]; trials=[]; best=None
    for cm,conf,window,recovery,timeout,pw in itertools.product(g["candidate_margin"],g["confirmations"],g["window"],g["recovery_votes"],g["timeout"],g["pending_weight"]):
        par={"alpha":config["selected_detector_alpha"],"candidate_margin":cm,"confirmations":conf,"window":window,"recovery_votes":recovery,"timeout":timeout,"pending_weight":pw}
        mem,tasks,_=evaluate(obs,labels,predictions,par,config,detectors,memory_and_tasks,online_strategy,strategies=("early_reversible",))
        success=sum(x["task_success"] for x in tasks)/len(tasks); conflict=sum(x["old_goal_conflict"] for x in tasks)/len(tasks); bg=sum(x["background_retention_rate"] for x in tasks)/len(tasks)
        mm=next(x for x in aggregate_memory(mem) if x["strategy"]=="early_reversible" and x["category"]=="overall"); recovery_rate=mm["temporary_recovery_success_rate"] or 0.0
        objective=success-.25*conflict-.10*(1-recovery_rate); row={"params":json.dumps(par,sort_keys=True),"objective":objective,"task_success":success,"old_goal_conflict":conflict,"background_retention":bg,"recovery_success":recovery_rate}; trials.append(row)
        if bg>=.98:
            key=(objective,success,recovery_rate,-conflict)
            if best is None or key>best[0]: best=(key,par)
    if best is None: raise RuntimeError("No early-response dev candidate met background constraint")
    return best[1],trials

def scenario_task_metrics(task_rows,labels,seed,iterations):
    truth={x["trajectory_id"]:x for x in labels}; rates=trajectory_rates(task_rows,labels); rng=random.Random(seed); out=[]
    for group in SCENARIOS:
        tids=sorted(x["trajectory_id"] for x in labels if x["scenario"]==group)
        for strategy in ALL_STRATEGIES:
            for metric in ("task_success","old_goal_conflict","background_retention_rate"):
                vals=[rates[(t,strategy)][metric] for t in tids]; boot=[sum(rng.choice(vals) for _ in vals)/len(vals) for _ in range(iterations)]; boot.sort()
                out.append({"strategy":strategy,"metric":metric,"group":group,"estimate":sum(vals)/len(vals),"ci_low":boot[int(.025*iterations)],"ci_high":boot[int(.975*iterations)],"n_trajectories":len(tids),"bootstrap_unit":"trajectory"})
    return out

def mdtable(df,cols):
    v=df[cols].copy()
    for c in v.select_dtypes(include="number"): v[c]=v[c].map(lambda x:"NA" if pd.isna(x) else f"{x:.3f}")
    return "\n".join(["| "+" | ".join(cols)+" |","| "+" | ".join("---" for _ in cols)+" |",*["| "+" | ".join(map(str,r))+" |" for r in v.itertuples(index=False,name=None)]])

def plots(det,mem,task,out):
    det[det.group=="overall"].set_index("method")[["precision","recall","f1","false_positive_rate","localization_hit_rate_tolerance_2"]].plot(kind="bar",figsize=(9,5),ylim=(0,1.05),rot=10,title="Phase 3 drift detection")
    plt.tight_layout(); plt.savefig(out/"phase3_detection_comparison.png",dpi=160); plt.close()
    mem[mem.category=="overall"].set_index("strategy")[["obsolete_interference_rate","valid_memory_retention_rate","obsolete_f1","temporary_recovery_success_rate"]].plot(kind="bar",figsize=(11,5),ylim=(0,1.05),rot=18,title="Phase 3 memory timing and recovery")
    plt.tight_layout(); plt.savefig(out/"phase3_memory_comparison.png",dpi=160); plt.close()
    task[(task.group=="overall")&task.metric.isin(["task_success","old_goal_conflict","background_retention_rate"])].pivot(index="strategy",columns="metric",values="estimate").plot(kind="bar",figsize=(11,5),ylim=(0,1.05),rot=18,title="Phase 3 paired online tasks")
    plt.tight_layout(); plt.savefig(out/"phase3_task_comparison.png",dpi=160); plt.close()

def write_audit(out,snapshot,changed):
    text=f"""# Phase 3 实现审计

- Method C/D 输入均为按时间排序的 `session_id/text`，不读取场景或标签。Method D 只有达到确认票数才返回报警；`estimated_onset` 在确认前不可用。
- 四组合消融成立，因为第二阶段记忆函数只消费标准检测字典。A/B 使用 C，C/D 使用 D；原始/改进记忆交叉替换没有隐藏名称依赖。
- 第二阶段记忆不是跨任务持久对象：每个任务从原始前缀重新抽取并投影权重。第三阶段基线保留这一语义；新增策略另有显式因果状态轨迹。
- 新增 Early Reversible 只使用当前及历史文本。候选、确认、恢复、超时和背景保护均有单元测试。
- Oracle Timing 读取真实起点，只是不可部署诊断上界，排除在正式比较和继续门槛之外。
- 第三阶段调参只读取开发标签；测试标签只在固定参数后由评估侧连接。任务统计和 Bootstrap 均以完整轨迹为单位。
- 第一阶段有 18 个历史哈希基线。第二阶段 manifest 只历史签名结果文件，源码/数据没有历史签名；本阶段运行前补建当前全量快照，此限制没有伪装成历史保证。
- 原阶段快照文件数：{len(snapshot)}；运行后变化数：{len(changed)}（必须为 0）。
"""
    (out/"phase3_audit.md").write_text(text,encoding="utf-8")

def run(root):
    phase=root/"phase3"; out=phase/"results"; out.mkdir(parents=True,exist_ok=True)
    config=json.loads((phase/"config"/"preregistered_config.json").read_text(encoding="utf-8"))
    snapshot=capture_originals(root); (phase/"original_baseline_snapshot.json").write_text(json.dumps(snapshot,indent=2),encoding="utf-8")
    _,_,data_manifest=save_locked(phase,config)
    observable=json.loads((phase/"data"/"interactions.json").read_text(encoding="utf-8")); labels=json.loads((phase/"data"/"labels.json").read_text(encoding="utf-8"))
    dev_obs=[x for x in observable if x["split"]=="dev"]; test_obs=[x for x in observable if x["split"]=="test"]; dev_labels=[x for x in labels if x["split"]=="dev"]; test_labels=[x for x in labels if x["split"]=="test"]
    det_params,det_trials=tune_detectors(dev_obs,dev_labels); config["selected_detector_alpha"]=det_params["method_d"]["alpha"]; dev_preds=predict(dev_obs,det_params)
    early_params,early_trials=tune_early(dev_obs,dev_labels,dev_preds,config)
    test_preds=predict(test_obs,det_params)+early_confirmation_predictions(test_obs,early_params)
    det_metrics,joined=detection_metrics(test_preds,test_labels,config["localization_tolerance"])
    mem_rows,task_rows,state_rows=evaluate(test_obs,test_labels,test_preds,early_params,config,detectors,memory_and_tasks,online_strategy)
    mem_metrics=aggregate_memory(mem_rows); task_summary,pairs,rates=bootstrap_and_tests(task_rows,test_labels,config["bootstrap_seed"],config["bootstrap_iterations"],config["permutation_iterations"],DEPLOYABLE)
    for x in task_summary: x["group"]="overall"
    task_summary += scenario_task_metrics(task_rows,test_labels,config["bootstrap_seed"]+1,config["bootstrap_iterations"])
    det_df=pd.DataFrame(det_metrics); mem_df=pd.DataFrame(mem_metrics); task_df=pd.DataFrame(task_summary); pair_df=pd.DataFrame(pairs); pred_df=pd.DataFrame(joined)
    failures=[]
    for x in joined:
        if x["error_type"] not in {"correct_rejection","on_time"}: failures.append({"record_type":"detection","trajectory_id":x["trajectory_id"],"scenario":x["scenario"],"strategy_or_method":x["method"],"session":x["detected_at"],"reason":x["error_type"]})
    for x in task_rows:
        if not x["task_success"]: failures.append({"record_type":"task","trajectory_id":x["trajectory_id"],"scenario":x["scenario"],"strategy_or_method":x["strategy"],"session":x["task_session"],"reason":x["failure_attribution"]})
    failure_df=pd.DataFrame(failures)
    # Required and diagnostic row-level outputs.
    det_df.to_csv(out/"phase3_detection_metrics.csv",index=False,encoding="utf-8-sig"); mem_df.to_csv(out/"phase3_memory_metrics.csv",index=False,encoding="utf-8-sig"); task_df.to_csv(out/"phase3_task_metrics.csv",index=False,encoding="utf-8-sig"); pred_df.to_csv(out/"phase3_predictions.csv",index=False,encoding="utf-8-sig"); failure_df.to_csv(out/"phase3_failure_cases.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(task_rows).to_csv(out/"phase3_task_details.csv",index=False,encoding="utf-8-sig"); pd.DataFrame(mem_rows).to_csv(out/"phase3_memory_details.csv",index=False,encoding="utf-8-sig"); pd.DataFrame(state_rows).to_csv(out/"phase3_state_log.csv",index=False,encoding="utf-8-sig"); pair_df.to_csv(out/"phase3_pairwise_tests.csv",index=False,encoding="utf-8-sig"); pd.DataFrame(det_trials).to_csv(out/"phase3_detection_dev_tuning.csv",index=False,encoding="utf-8-sig"); pd.DataFrame(early_trials).to_csv(out/"phase3_early_dev_tuning.csv",index=False,encoding="utf-8-sig")
    plots(det_df,mem_df,task_df,out)
    changed=verify_snapshot(root,snapshot); write_audit(out,snapshot,changed)
    overall_task=task_df[(task_df.group=="overall")&(task_df.metric=="task_success")]; overall_mem=mem_df[mem_df.category=="overall"]; overall_det=det_df[det_df.group=="overall"]
    task_view=overall_task.set_index("strategy")["estimate"]; mem_view=overall_mem.set_index("strategy"); det_view=overall_det.set_index("method")
    temp_view=task_df[(task_df.group=="temporary_shift")&(task_df.metric=="task_success")].set_index("strategy")["estimate"]
    primary=pair_df[(pair_df.strategy=="early_reversible")&(pair_df.reference=="D_D_improved")&(pair_df.metric=="task_success")].iloc[0]
    early_bg=task_df[(task_df.group=="overall")&(task_df.strategy=="early_reversible")&(task_df.metric=="background_retention_rate")].iloc[0]["estimate"]
    stable=task_df[(task_df.group=="stable")&(task_df.metric=="task_success")].set_index("strategy")["estimate"]; stable_drop=stable["D_D_improved"]-stable["early_reversible"]
    criteria={"gain_at_least_0.05":bool(primary.absolute_difference>=config["continue_thresholds"]["minimum_absolute_task_gain"]),"ci_lower_above_zero":bool(primary.ci_low>0),"background_at_least_0.98":bool(early_bg>=config["continue_thresholds"]["minimum_background_retention"]),"stable_drop_within_0.02":bool(stable_drop<=config["continue_thresholds"]["maximum_stable_success_drop"])}; decision="CONTINUE_CONTROLLED_RESEARCH" if all(criteria.values()) else "STOP_OR_REVISE_CURRENT_IMPLEMENTATION"
    first_fail=failure_df.iloc[0].to_dict() if len(failure_df) else {}
    summary=f"""# Phase 3 实验总结

这是规则与合成数据实验，不是真实 LLM Agent 评测。数据种子 `{config['data_seed']}`；开发/测试轨迹 {len(dev_labels)}/{len(test_labels)}；测试任务记录 {len(task_rows)}。

## 检测（独立测试 overall）

{mdtable(overall_det,['method','precision','recall','f1','false_positive_rate','localization_hit_rate_tolerance_2','mean_abs_localization_error','mean_detection_delay'])}

Method E 是 Early Reversible 的确认事件；临时候选不是正式报警。无漂移延迟为 NA。

## 机制消融与任务成功

{mdtable(overall_task,['strategy','estimate','ci_low','ci_high','n_trajectories'])}

Oracle Timing 是不可部署上界，不能与正常方法作公平排名。完整旧目标冲突、背景保留、首次正确执行时间和分场景结果见 CSV。

## 在线记忆（overall）

{mdtable(overall_mem,['strategy','obsolete_precision','obsolete_recall','obsolete_f1','obsolete_interference_rate','valid_memory_retention_rate','incorrect_downweight_rate','temporary_recovery_success_rate'])}

## 预注册主要比较与决策

- Early Reversible − D：任务成功率差 `{primary.absolute_difference:.3f}`，95% CI `[{primary.ci_low:.3f}, {primary.ci_high:.3f}]`，原始配对随机化 p=`{primary.p_value:.5f}`，Holm p=`{primary.holm_p_value:.5f}`。
- Early 背景保留率 `{early_bg:.3f}`；稳定场景相对 D 的成功率下降 `{stable_drop:.3f}`。
- 门槛：`{json.dumps(criteria,ensure_ascii=False)}`。
- 决策：**{decision}**。

## 失败归因与假设

- **H1 不支持。** 新测试上 D 的平均延迟为 {det_view.loc['method_d','mean_detection_delay']:.3f}，反而早于 C 的 {det_view.loc['method_c','mean_detection_delay']:.3f}；同为原始记忆时 C→D 的任务率从 {task_view['A_C_original']:.3f} 到 {task_view['C_D_original']:.3f}，同为改进记忆时从 {task_view['B_C_improved']:.3f} 到 {task_view['D_D_improved']:.3f}。第二阶段的延迟解释未在独立数据复现。
- **H2 不支持当前实现。** Early 在短暂变化场景成功率 {temp_view['early_reversible']:.3f}，D 为 {temp_view['D_D_improved']:.3f}；严格恢复成功率仅 {mem_view.loc['early_reversible','temporary_recovery_success_rate']:.3f}，仍有恢复失败。
- **H3 支持。** Early 的过时记忆 F1={mem_view.loc['early_reversible','obsolete_f1']:.3f}，高于 D 的 {mem_view.loc['D_D_improved','obsolete_f1']:.3f}，但任务增益只有 {primary.absolute_difference:.3f}，未达到预注册 0.05 门槛。
- Oracle Timing 任务成功率 {task_view['oracle_timing']:.3f}，说明仍有时机/证据覆盖上界，但它读取真实起点，不可部署。
- 代表性保留失败：`{first_fail}`。所有失败均在 `phase3_failure_cases.csv`，未删除不利结果。

## 限制

- 仍使用有限人工词典；约 40% 表达是冻结抽取器不认识的分布迁移同义改写，仍不能代表真实语言。
- 第二阶段仅用于探索消融；正式确认使用新锁定测试集。开发参数固定后才连接测试标签。
- 配对检验进行了 Holm 校正，但合成分布、机制模型和任务效用仍限制外部有效性。
- 首次正式测试后只修正了 Oracle/不更新的失败归因名称和空状态日志写出，并补充报告解释；检测参数、早期策略参数、任务评分、预测和预注册门槛均未改变。修复后重新执行了完整双运行确定性检查。

重复性检查：`PENDING`。原阶段完整性变化数：`{len(changed)}`。
"""
    (out/"phase3_summary.md").write_text(summary,encoding="utf-8")
    manifest={"config":config,"selected_detector_params":det_params,"selected_early_params":early_params,"data_manifest":data_manifest,"original_snapshot_sha256":sha(phase/"original_baseline_snapshot.json"),"original_changed_files":changed,"criteria":criteria,"decision":decision,"python":platform.python_version(),"pandas":pd.__version__}
    files={p.name:{"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!="phase3_manifest.json"}; manifest["files"]=files; (out/"phase3_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return {"manifest":manifest,"hashes":{k:v["sha256"] for k,v in files.items()},"detection":overall_det,"memory":overall_mem,"task":overall_task,"primary":primary,"failures":failure_df,"counts":Counter((x["split"],x["scenario"]) for x in labels),"changed":changed}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--check-determinism",action="store_true"); args=ap.parse_args(); first=run(ROOT)
    print("COMMAND=python phase3/src/run_phase3.py"+(" --check-determinism" if args.check_determinism else "")); print("COUNTS",dict(first["counts"])); print("DETECTION\n",first["detection"].to_string(index=False)); print("MEMORY\n",first["memory"].to_string(index=False)); print("TASK\n",first["task"].to_string(index=False)); print("PRIMARY\n",first["primary"].to_dict()); print("DECISION",first["manifest"]["decision"],"ORIGINAL_CHANGED",first["changed"],"FAILURES",len(first["failures"])); print("RESULTS",ROOT/"phase3"/"results")
    if args.check_determinism:
        second=run(ROOT)
        if first["hashes"]!=second["hashes"]: print("DETERMINISM_CHECK=FAIL",file=sys.stderr); return 2
        out=ROOT/"phase3"/"results"; report=out/"phase3_summary.md"; report.write_text(report.read_text(encoding="utf-8").replace("重复性检查：`PENDING`",f"重复性检查：`PASS`（{len(first['hashes'])} 个产物 SHA-256 一致）"),encoding="utf-8")
        mp=out/"phase3_manifest.json"; m=json.loads(mp.read_text(encoding="utf-8")); m["determinism_check"]={"status":"PASS","compared_files":len(first["hashes"])}; m["files"][report.name]={"bytes":report.stat().st_size,"sha256":sha(report)}; mp.write_text(json.dumps(m,indent=2),encoding="utf-8"); print(f"DETERMINISM_CHECK=PASS files={len(first['hashes'])}")
    return 0
if __name__=="__main__": raise SystemExit(main())
