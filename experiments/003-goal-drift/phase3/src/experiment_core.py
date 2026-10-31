"""Factorial strategy evaluation on identical online task prefixes."""
from __future__ import annotations
DEPLOYABLE=("A_C_original","B_C_improved","C_D_original","D_D_improved","early_reversible","no_update")
ALL_STRATEGIES=DEPLOYABLE+("oracle_timing",)
def maps(predictions): return {(p["trajectory_id"],p["method"]):p for p in predictions}

def evaluate(observable,labels,predictions,early_params,config,detectors,memory,online,strategies=ALL_STRATEGIES):
    obs={x["trajectory_id"]:x for x in observable}; pmap=maps(predictions); mem_rows=[]; task_rows=[]; state_rows=[]
    for lab in labels:
      tid=lab["trajectory_id"]; sessions=obs[tid]["sessions"]; trace=online.build_trace(sessions,early_params,detectors); c=pmap.get((tid,"method_c")); d=pmap.get((tid,"method_d")); weights={**config["fixed_memory_weights"],"pending_weight":early_params["pending_weight"]}
      state_rows.extend({"trajectory_id":tid,"scenario":lab["scenario"],**x} for x in trace)
      for strategy in strategies:
       for task in lab["tasks"]:
        t=task["session_id"]; prefix=sessions[:t+1]; raw=memory.extract_memories(prefix); det=None
        if strategy=="A_C_original": updated=memory.apply_strategy(raw,prefix,"drift_aware_original",c,{}); det=c
        elif strategy=="B_C_improved": updated=memory.apply_strategy(raw,prefix,"drift_aware_improved",c,config["inherited_memory_params"]); det=c
        elif strategy=="C_D_original": updated=memory.apply_strategy(raw,prefix,"drift_aware_original",d,{}); det=d
        elif strategy=="D_D_improved": updated=memory.apply_strategy(raw,prefix,"drift_aware_improved",d,config["inherited_memory_params"]); det=d
        elif strategy=="early_reversible": updated=online.project_memory(raw,trace[t],weights); det={"detected_at":trace[t].get("candidate_start")}
        elif strategy=="oracle_timing": updated=online.oracle_project(raw,t,lab,weights)
        elif strategy=="no_update": updated=[dict(m) for m in raw]
        else: raise ValueError(strategy)
        counts_list=memory.memory_counts(updated,tuple(task["required_goal"]),lab["background"]["value"]); recovery=None
        if lab["scenario"]=="temporary_shift" and t==lab["temporary_end"]:
            goal_counts=next(x for x in counts_list if x["category"]=="long_term_goal")
            recovery=int(goal_counts["fp"]==0 and goal_counts["fn"]==0 and (trace[t]["state"]=="neutral" if strategy=="early_reversible" else True))
        for counts in counts_list: mem_rows.append({"trajectory_id":tid,"scenario":lab["scenario"],"task_id":task["task_id"],"task_session":t,"strategy":strategy,"recovery_success":recovery,**counts})
        scored=memory.score_task(task,updated,lab["background"]["value"],tuple(lab["initial_goal"])); incorrect=counts_list[0]["fp"]
        if scored["task_success"]: attribution="success"
        elif not scored["background_retention_rate"]: attribution="background_loss"
        elif lab["scenario"]=="temporary_shift" and t>=lab["temporary_end"] and strategy=="early_reversible" and trace[t]["state"]!="neutral": attribution="recovery_failure"
        elif det and det.get("detected_at") is not None and not lab["has_drift"]: attribution="false_alarm_update"
        elif strategy=="no_update": attribution="no_update_interference"
        elif strategy=="oracle_timing": attribution="oracle_residual_conflict"
        elif lab["has_drift"] and (not det or det.get("detected_at") is None or det["detected_at"]>t): attribution="detection_delay"
        elif incorrect: attribution="erroneous_downweight"
        else: attribution="goal_evidence_conflict"
        task_rows.append({"trajectory_id":tid,"scenario":lab["scenario"],"task_id":task["task_id"],"task_session":t,"strategy":strategy,"detection_at":det.get("detected_at") if det else None,"online_state":trace[t]["state"] if strategy=="early_reversible" else "na","failure_attribution":attribution,**scored})
    return mem_rows,task_rows,state_rows
