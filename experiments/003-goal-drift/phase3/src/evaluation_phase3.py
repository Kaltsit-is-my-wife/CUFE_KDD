"""Phase-3 metrics, trajectory bootstrap, paired randomization, and Holm correction."""
from __future__ import annotations
import random
from collections import defaultdict
from itertools import combinations

def div(a,b): return a/b if b else 0.0

def detection_metrics(predictions,labels,tolerance=2):
    truth={x["trajectory_id"]:x for x in labels}; joined=[]
    for p in predictions:
        t=truth[p["trajectory_id"]]; alert=p.get("detected_at")
        if not t["has_drift"]: error="false_positive" if alert is not None else "correct_rejection"; delay=loc=None; hit=None
        elif alert is None: error="miss"; delay=loc=None; hit=0
        else:
            delay=alert-t["confirmation_session"]; estimate=p.get("estimated_onset") if p.get("estimated_onset") is not None else alert
            loc=estimate-t["drift_onset"]; hit=int(abs(loc)<=tolerance); error="early" if delay < -tolerance else ("late" if delay>tolerance else "on_time")
        joined.append({**p,"scenario":t["scenario"],"has_drift":t["has_drift"],"true_onset":t["drift_onset"],"true_confirmation":t["confirmation_session"],"detection_delay":delay,"localization_error":loc,"localization_hit":hit,"error_type":error})
    groups=["overall",*sorted({x["scenario"] for x in labels}),"all_drift","no_drift"]; out=[]
    for method in sorted({x["method"] for x in joined}):
      mr=[x for x in joined if x["method"]==method]
      for group in groups:
        rows=mr if group=="overall" else ([x for x in mr if x["has_drift"]] if group=="all_drift" else ([x for x in mr if not x["has_drift"]] if group=="no_drift" else [x for x in mr if x["scenario"]==group]))
        if not rows: continue
        tp=sum(x["has_drift"] and x["detected_at"] is not None for x in rows); fp=sum(not x["has_drift"] and x["detected_at"] is not None for x in rows); fn=sum(x["has_drift"] and x["detected_at"] is None for x in rows); tn=sum(not x["has_drift"] and x["detected_at"] is None for x in rows)
        pr,re=div(tp,tp+fp),div(tp,tp+fn); delays=[x["detection_delay"] for x in rows if x["detection_delay"] is not None]; locs=[abs(x["localization_error"]) for x in rows if x["localization_error"] is not None]; hits=[x["localization_hit"] for x in rows if x["localization_hit"] is not None and x["detected_at"] is not None]
        out.append({"method":method,"group":group,"n_trajectories":len(rows),"precision":pr,"recall":re,"f1":div(2*pr*re,pr+re),"false_positive_rate":div(fp,fp+tn),"localization_hit_rate_tolerance_2":div(sum(hits),len(hits)),"mean_abs_localization_error":div(sum(locs),len(locs)) if locs else None,"mean_detection_delay":div(sum(delays),len(delays)) if delays else None,"tp":tp,"fp":fp,"fn":fn,"tn":tn})
    return out,joined

def aggregate_memory(rows):
    grouped=defaultdict(list)
    for r in rows: grouped[(r["strategy"],r["category"])].append(r)
    out=[]
    for (strategy,category),vals in grouped.items():
        sums={k:sum(v[k] for v in vals) for k in ("tp","fp","fn","obsolete_weight","valid_weight","obsolete_n","valid_n","updates","total_weight")}; p=div(sums["tp"],sums["tp"]+sums["fp"]); rec=div(sums["tp"],sums["tp"]+sums["fn"]); recovery=[v["recovery_success"] for v in vals if v.get("recovery_success") is not None]
        out.append({"strategy":strategy,"category":category,"obsolete_precision":p,"obsolete_recall":rec,"obsolete_f1":div(2*p*rec,p+rec),"obsolete_interference_rate":div(sums["obsolete_weight"],sums["total_weight"]),"valid_memory_retention_rate":div(sums["valid_weight"],sums["valid_n"]),"incorrect_downweight_rate":div(sums["fp"],sums["valid_n"]),"mean_update_count":div(sums["updates"],len(vals)),"temporary_recovery_success_rate":div(sum(recovery),len(recovery)) if recovery else None,"n_states":len(vals)})
    return out

def trajectory_rates(task_rows,labels):
    grouped=defaultdict(list)
    for r in task_rows: grouped[(r["trajectory_id"],r["strategy"])].append(r)
    truth={x["trajectory_id"]:x for x in labels}; out={}
    for key,vals in grouped.items():
        tid,strategy=key; lab=truth[tid]; row={m:sum(v[m] for v in vals)/len(vals) for m in ("task_success","old_goal_conflict","background_retention_rate")}; post=[v for v in vals if lab["has_drift"] and v["task_session"]>=lab["confirmation_session"]]; correct=[v["task_session"]-lab["confirmation_session"] for v in post if v["task_success"]]; row["first_correct_delay"]=min(correct) if correct else None; row["first_correct_achieved"]=int(bool(correct)) if lab["has_drift"] else None; out[key]=row
    return out

def bootstrap_and_tests(task_rows,labels,seed,iterations,permutation_iterations,deployable):
    rates=trajectory_rates(task_rows,labels); tids=sorted({k[0] for k in rates}); rng=random.Random(seed); summary=[]
    for strategy in sorted({k[1] for k in rates}):
      for metric in ("task_success","old_goal_conflict","background_retention_rate"):
        vals=[rates[(t,strategy)][metric] for t in tids]; point=sum(vals)/len(vals); boot=[sum(rng.choice(vals) for _ in vals)/len(vals) for _ in range(iterations)]; boot.sort(); summary.append({"strategy":strategy,"metric":metric,"estimate":point,"ci_low":boot[int(.025*iterations)],"ci_high":boot[int(.975*iterations)],"n_trajectories":len(tids),"bootstrap_unit":"trajectory"})
      delays=[rates[(t,strategy)]["first_correct_delay"] for t in tids if rates[(t,strategy)]["first_correct_delay"] is not None]; achieved=[rates[(t,strategy)]["first_correct_achieved"] for t in tids if rates[(t,strategy)]["first_correct_achieved"] is not None]
      summary += [{"strategy":strategy,"metric":"first_correct_delay","estimate":div(sum(delays),len(delays)) if delays else None,"ci_low":None,"ci_high":None,"n_trajectories":len(delays),"bootstrap_unit":"trajectory"},{"strategy":strategy,"metric":"first_correct_achievement_rate","estimate":div(sum(achieved),len(achieved)),"ci_low":None,"ci_high":None,"n_trajectories":len(achieved),"bootstrap_unit":"trajectory"}]
    pair=[]
    for reference,strategy in combinations(sorted(deployable),2):
      for metric in ("task_success","old_goal_conflict"):
        diffs=[rates[(t,strategy)][metric]-rates[(t,reference)][metric] for t in tids]; obs=sum(diffs)/len(diffs); boot=[sum(rng.choice(diffs) for _ in diffs)/len(diffs) for _ in range(iterations)]; boot.sort(); extreme=0
        for _ in range(permutation_iterations): extreme+=abs(sum(d if rng.random()<.5 else -d for d in diffs)/len(diffs))>=abs(obs)-1e-15
        pair.append({"strategy":strategy,"reference":reference,"metric":metric,"absolute_difference":obs,"ci_low":boot[int(.025*iterations)],"ci_high":boot[int(.975*iterations)],"p_value":(extreme+1)/(permutation_iterations+1),"wins":sum(d>0 for d in diffs),"ties":sum(d==0 for d in diffs),"losses":sum(d<0 for d in diffs),"n_trajectories":len(tids)})
    order=sorted(range(len(pair)),key=lambda i:pair[i]["p_value"]); running=0.0; m=len(pair)
    for rank,idx in enumerate(order): adjusted=min(1.0,(m-rank)*pair[idx]["p_value"]); running=max(running,adjusted); pair[idx]["holm_p_value"]=running
    return summary,pair,rates
