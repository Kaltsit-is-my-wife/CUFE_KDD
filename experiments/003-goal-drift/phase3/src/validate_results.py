"""Validate phase-3 row-level recomputation, locks, hashes, and figures."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import matplotlib.image as mpimg
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"phase3"/"results"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b): return abs(float(a)-float(b))<1e-10

def main():
    required=["phase3_design.md","phase3_summary.md","phase3_audit.md","phase3_detection_metrics.csv","phase3_memory_metrics.csv","phase3_task_metrics.csv","phase3_predictions.csv","phase3_failure_cases.csv","phase3_manifest.json","phase3_detection_comparison.png","phase3_memory_comparison.png","phase3_task_comparison.png"]
    assert all((OUT/x).is_file() and (OUT/x).stat().st_size>0 for x in required)
    manifest=json.loads((OUT/"phase3_manifest.json").read_text(encoding="utf-8")); assert manifest["determinism_check"]["status"]=="PASS"; assert manifest["original_changed_files"]==[]
    for name,meta in manifest["files"].items(): assert sha(OUT/name)==meta["sha256"]
    data_manifest=json.loads((ROOT/"phase3"/"data"/"data_manifest.json").read_text(encoding="utf-8"))
    for name,meta in data_manifest["files"].items(): assert sha(ROOT/"phase3"/"data"/name)==meta["sha256"]
    snapshot=json.loads((ROOT/"phase3"/"original_baseline_snapshot.json").read_text(encoding="utf-8"))
    for rel,meta in snapshot.items(): assert (ROOT/rel).exists() and sha(ROOT/rel)==meta["sha256"]
    pred=pd.read_csv(OUT/"phase3_predictions.csv"); det=pd.read_csv(OUT/"phase3_detection_metrics.csv")
    for method,rows in pred.groupby("method"):
        reported=det[(det.method==method)&(det.group=="overall")].iloc[0]; tp=((rows.has_drift==True)&rows.detected_at.notna()).sum(); fp=((rows.has_drift==False)&rows.detected_at.notna()).sum(); fn=((rows.has_drift==True)&rows.detected_at.isna()).sum(); tn=((rows.has_drift==False)&rows.detected_at.isna()).sum(); assert (tp,fp,fn,tn)==tuple(int(reported[x]) for x in ("tp","fp","fn","tn"))
    details=pd.read_csv(OUT/"phase3_task_details.csv"); task=pd.read_csv(OUT/"phase3_task_metrics.csv"); per=details.groupby(["trajectory_id","strategy"]).task_success.mean().groupby("strategy").mean()
    for strategy,value in per.items(): assert close(value,task[(task.strategy==strategy)&(task.metric=="task_success")&(task.group=="overall")].estimate.iloc[0])
    md=pd.read_csv(OUT/"phase3_memory_details.csv"); mm=pd.read_csv(OUT/"phase3_memory_metrics.csv")
    for strategy,rows in md[md.category=="overall"].groupby("strategy"):
        rec=rows.tp.sum()/(rows.tp.sum()+rows.fn.sum()) if rows.tp.sum()+rows.fn.sum() else 0; assert close(rec,mm[(mm.strategy==strategy)&(mm.category=="overall")].obsolete_recall.iloc[0])
    states=pd.read_csv(OUT/"phase3_state_log.csv"); assert len(states)>0 and states.trajectory_id.nunique()==224
    assert set(states.state).issubset({"neutral","pending","confirmed"}) and {"candidate","confirm","recovered","timeout_restore"}.intersection(set(states.event))
    shapes={p.name:mpimg.imread(p).shape for p in OUT.glob("*.png")}; assert len(shapes)==3
    print(f"VALIDATION=PASS predictions={len(pred)} task_rows={len(details)} state_rows={len(states)} original_files={len(snapshot)} data_files={len(data_manifest['files'])} png={shapes}")
if __name__=="__main__": main()
