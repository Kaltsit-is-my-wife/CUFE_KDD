"""Causal early-candidate state machine and reversible memory projection."""
from __future__ import annotations

from collections import deque


def build_trace(sessions:list[dict],params:dict,detectors_module)->list[dict]:
    aggregate=detectors_module.aggregate; dominant=detectors_module.dominant; extract=detectors_module.extract
    values=detectors_module.VALUES
    ref=dominant(aggregate([s["text"] for s in sessions[:3]]))
    fast={v:0.0 for v in values}; votes=deque(maxlen=params["window"])
    state="neutral"; target=None; candidate_start=None; no_vote=0; recovery_run=0; trace=[]
    for i,s in enumerate(sessions):
        event="none"
        if i<3 or not ref:
            trace.append({"session_id":s["session_id"],"state":state,"target":target,"event":event,"candidate_vote":False}); continue
        sc=extract(s["text"])
        for v in values: fast[v]=params["alpha"]*sc[v]+(1-params["alpha"])*fast[v]
        cur=dominant(fast)
        ref_mass=sum(fast[v] for v in ref)
        cur_mass=sum(fast[v] for v in cur) if cur else 0.0
        vote=bool(cur and cur!=ref and cur_mass-ref_mass>=params["candidate_margin"])
        votes.append(vote)
        if vote:
            no_vote=0; recovery_run=0
            if state=="neutral": state="pending"; candidate_start=s["session_id"]; event="candidate"; target=cur
            elif cur!=target: target=cur; event="retarget"
            if sum(votes)>=params["confirmations"] and state!="confirmed": state="confirmed"; event="confirm"
        else:
            no_vote+=1
            is_reference=bool(cur==ref and ref_mass>0)
            recovery_run=recovery_run+1 if is_reference else 0
            if state=="pending" and no_vote>=params["timeout"]:
                state="neutral"; target=None; candidate_start=None; event="timeout_restore"; votes.clear()
            elif state=="confirmed" and recovery_run>=params["recovery_votes"]:
                state="neutral"; target=None; candidate_start=None; event="recovered"; votes.clear(); no_vote=0
        trace.append({"session_id":s["session_id"],"state":state,"target":target,"event":event,
                      "candidate_vote":vote,"candidate_start":candidate_start})
    return trace


def project_memory(memories:list[dict],state:dict,weights:dict)->list[dict]:
    out=[dict(m) for m in memories]
    for m in out:
        if m["kind"] in {"temporary","history_plan"}:
            m["weight"]*=weights["temporary_scope_weight"]; m["state"]="downweighted"
    if state["state"] not in {"pending","confirmed"} or not state.get("target"):
        return out
    target=dict(zip(("cost","pace"),state["target"]))
    factor=weights["pending_weight"] if state["state"]=="pending" else weights["confirmed_weight"]
    for m in out:
        if m["kind"]=="long_term_goal" and m["value"]!=target[m["key"]]:
            m["weight"]*=factor; m["state"]="pending" if state["state"]=="pending" else "downweighted"
    return out


def oracle_project(memories:list[dict],task_session:int,label:dict,weights:dict)->list[dict]:
    out=[dict(m) for m in memories]
    for m in out:
        if m["kind"] in {"temporary","history_plan"}: m["weight"]*=weights["temporary_scope_weight"]; m["state"]="downweighted"
    if not label["has_drift"] or task_session<label["drift_onset"]: return out
    target=dict(zip(("cost","pace"),label["current_goals"][task_session]))
    for m in out:
        if m["kind"]=="long_term_goal" and m["value"]!=target[m["key"]]:
            m["weight"]*=weights["confirmed_weight"]; m["state"]="downweighted"
    return out
