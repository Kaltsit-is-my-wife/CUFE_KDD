"""Generate the locked independent phase-3 corpus."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SCENARIOS = ("abrupt_drift","gradual_drift","topic_switch","temporary_shift",
             "similar_goal_drift","indirect_drift","stable")
COST=("economy","value","premium"); PACE=("rapid","balanced","thorough")
TOPICS=("travel","shopping","coursework","project","meals","fitness","home","finance","music")
BACKGROUND=(("diet","vegetarian"),("platform","windows"),("schedule","evening"),("access","step_free"))

# Some phrases are recognized by the frozen phase-2 extractor; others are deliberate paraphrase shift.
PHRASES={
 "economy":["keep the overall cost as low as possible","minimize spending over polish","stay on a strict budget","spending less outranks optional features","the leanest acceptable price wins"],
 "value":["optimize value for money","balance price with durability","avoid both bargain-bin and luxury choices","judge total ownership cost, not sticker price","pay only for benefits that last"],
 "premium":["quality matters more than price","choose the premium experience","prioritize finish and comfort over savings","I prefer top-tier materials","best fit outranks the bill"],
 "rapid":["finish as quickly as practical","speed is the main priority","ship early even with fewer extras","shorten the turnaround","act now and refine later"],
 "balanced":["balance speed with adequate checking","use a moderate pace","trade off turnaround and coverage","move steadily with essential checks","neither haste nor exhaustive review"],
 "thorough":["check every important detail","coverage matters more than speed","use a careful comprehensive process","verify the edge cases before finishing","completeness outranks turnaround"],
}
INDIRECT={
 "economy":["premium add-ons no longer justify their price","large price tags now end the discussion"],
 "value":["the cheapest option failed twice, so price alone is out","I stopped buying bargains that need replacement"],
 "premium":["I will not sacrifice quality merely to save","the budget version was rejected for poor comfort"],
 "rapid":["another long review is no longer acceptable","I rejected the slow route before it began"],
 "balanced":["both rushing and endless checking have failed","I no longer accept either pace extreme"],
 "thorough":["quick answers without verification are no longer useful","a rushed result missed too much"],
}
BG={"vegetarian":["I eat vegetarian food","meals must contain no meat"],
    "windows":["my only computer runs Windows","the workflow must work on Windows"],
    "evening":["I can only work in the evening","daytime is unavailable to me"],
    "step_free":["I need step-free access","stairs are not accessible for me"]}


def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def different(rng:random.Random,g:tuple[str,str],similar:bool=False)->tuple[str,str]:
    if similar:
        if rng.random()<.5:
            i=COST.index(g[0]); return (COST[i+1] if i<2 else COST[1],g[1])
        i=PACE.index(g[1]); return (g[0],PACE[i+1] if i<2 else PACE[1])
    return rng.choice([(c,p) for c in COST for p in PACE if c!=g[0] and p!=g[1]])


def generate(config:dict)->tuple[list[dict],list[dict]]:
    rng=random.Random(config["data_seed"]); observable=[]; labels=[]
    total=config["per_scenario_dev"]+config["per_scenario_test"]
    for scenario in SCENARIOS:
      for i in range(total):
        n=rng.randint(*config["session_range"]); initial=(rng.choice(COST),rng.choice(PACE))
        final=different(rng,initial,scenario=="similar_goal_drift"); temporary=different(rng,initial)
        onset=rng.randint(config["drift_onset_range_from_edges"][0],n-config["drift_onset_range_from_edges"][1])
        temp_len=rng.randint(*config["temporary_duration_range"]); temp_end=min(n,onset+temp_len)
        confirm=onset
        if scenario=="gradual_drift": confirm=min(n-3,onset+rng.randint(2,4))
        if scenario=="indirect_drift": confirm=min(n-3,onset+rng.randint(1,3))
        has_drift=scenario in {"abrupt_drift","gradual_drift","similar_goal_drift","indirect_drift"}
        if not has_drift: final=initial; true_onset=true_confirm=None
        else: true_onset=onset; true_confirm=confirm
        bg_key,bg_value=BACKGROUND[(i+SCENARIOS.index(scenario))%len(BACKGROUND)]
        base_topic=rng.choice(TOPICS); sessions=[]; current_goals=[]
        for t in range(n):
            current=initial; evidence=initial; indirect=False
            if scenario in {"abrupt_drift","similar_goal_drift"} and t>=confirm: current=evidence=final
            elif scenario=="gradual_drift":
                if t>=confirm: current=final
                if onset<=t<confirm:
                    progress=(t-onset+1)/(confirm-onset+1)
                    evidence=final if rng.random()<(.18+.58*progress) else initial
                elif t>=confirm: evidence=final
            elif scenario=="indirect_drift" and t>=onset:
                current=final if t>=confirm else initial; evidence=final; indirect=True
            elif scenario=="temporary_shift" and onset<=t<temp_end: current=evidence=temporary
            # Occasional one-session recurrence after real drift, independent of label.
            if has_drift and t>confirm and rng.random()<.12: evidence=initial
            current_goals.append(list(current))
            topic=TOPICS[(i+2*t)%len(TOPICS)] if scenario=="topic_switch" else (base_topic if rng.random()<.76 else rng.choice(TOPICS))
            parts=[f"Topic: {topic}."]
            for value in evidence:
                if rng.random()<.76:
                    pool=INDIRECT[value] if indirect and rng.random()<.72 else PHRASES[value]
                    parts.append(rng.choice(pool)+".")
            if rng.random()<.25:
                value=rng.choice(initial); parts.append(f"The previous plan used to {rng.choice(PHRASES[value])}, but that is historical context.")
            if rng.random()<.28:
                value=rng.choice(COST+PACE); parts.append(f"For this session only, {rng.choice(PHRASES[value])}.")
            if t==0 or rng.random()<.14: parts.append(rng.choice(BG[bg_value])+".")
            if rng.random()<.42: parts.append(f"Unrelated recurring note: {rng.choice(TOPICS)} remains open.")
            sessions.append({"session_id":t,"text":" ".join(parts)})
        split="dev" if i<config["per_scenario_dev"] else "test"; tid=f"p3-{scenario}-{i:02d}"
        # Dense online tasks make time-to-first-correct measurable.
        tasks=[{"task_id":f"{tid}-task-{t}","session_id":t,"required_goal":current_goals[t],
                "signal_strength":rng.choice((.50,.70,.90,1.10))} for t in range(3,n)]
        observable.append({"trajectory_id":tid,"split":split,"sessions":sessions})
        labels.append({"trajectory_id":tid,"split":split,"scenario":scenario,"has_drift":has_drift,
                       "drift_onset":true_onset,"confirmation_session":true_confirm,"temporary_start":onset if scenario=="temporary_shift" else None,
                       "temporary_end":temp_end if scenario=="temporary_shift" else None,
                       "initial_goal":list(initial),"final_goal":list(final),"current_goals":current_goals,
                       "background":{"key":bg_key,"value":bg_value},"tasks":tasks})
    return observable,labels


def save_locked(root:Path,config:dict)->tuple[list[dict],list[dict],dict]:
    data=root/"data"; data.mkdir(parents=True,exist_ok=True)
    observable,labels=generate(config)
    ip=data/"interactions.json"; lp=data/"labels.json"
    ip.write_text(json.dumps(observable,indent=2),encoding="utf-8")
    lp.write_text(json.dumps(labels,indent=2),encoding="utf-8")
    manifest={"seed":config["data_seed"],"trajectory_count":len(labels),"files":{
        "interactions.json":{"bytes":ip.stat().st_size,"sha256":sha(ip)},
        "labels.json":{"bytes":lp.stat().st_size,"sha256":sha(lp)}}}
    (data/"data_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return observable,labels,manifest
