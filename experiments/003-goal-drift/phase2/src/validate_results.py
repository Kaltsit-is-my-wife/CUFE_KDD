"""Recompute key aggregates from row-level phase-2 outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.image as mpimg
import pandas as pd


def close(a: float, b: float) -> bool:
    return abs(float(a)-float(b)) < 1e-10


def main() -> None:
    root=Path(__file__).resolve().parents[2]; out=root/"phase2"/"results"
    required=["phase2_audit.md","phase2_trajectory_data.csv","phase2_detection_metrics.csv",
              "phase2_memory_metrics.csv","phase2_task_metrics.csv","phase2_predictions.csv",
              "phase2_failure_cases.csv","phase2_detection_comparison.png","phase2_memory_tradeoff.png",
              "phase2_task_comparison.png","phase2_summary.md","phase2_manifest.json"]
    assert all((out/x).is_file() and (out/x).stat().st_size>0 for x in required)
    pred=pd.read_csv(out/"phase2_predictions.csv"); det=pd.read_csv(out/"phase2_detection_metrics.csv")
    for method,rows in pred.groupby("method"):
        metric=det[(det.method==method)&(det.group=="overall")].iloc[0]
        tp=((rows.has_drift==True)&rows.detected_at.notna()).sum(); fp=((rows.has_drift==False)&rows.detected_at.notna()).sum()
        fn=((rows.has_drift==True)&rows.detected_at.isna()).sum(); tn=((rows.has_drift==False)&rows.detected_at.isna()).sum()
        assert (tp,fp,fn,tn)==tuple(int(metric[x]) for x in ("tp","fp","fn","tn"))
    details=pd.read_csv(out/"phase2_task_details.csv"); task=pd.read_csv(out/"phase2_task_metrics.csv")
    by_traj=details.groupby(["trajectory_id","strategy"]).task_success.mean().reset_index()
    recomputed=by_traj.groupby("strategy").task_success.mean()
    for strategy,value in recomputed.items():
        reported=task[(task.strategy==strategy)&(task.metric=="task_success")].estimate.iloc[0]
        assert close(value,reported)
    mem_detail=pd.read_csv(out/"phase2_memory_details.csv"); mem=pd.read_csv(out/"phase2_memory_metrics.csv")
    for strategy,rows in mem_detail[(mem_detail.category=="overall")&(mem_detail.evaluation_scope=="online_task")].groupby("strategy"):
        recall=rows.tp.sum()/(rows.tp.sum()+rows.fn.sum()) if rows.tp.sum()+rows.fn.sum() else 0
        reported=mem[(mem.strategy==strategy)&(mem.category=="overall")&(mem.evaluation_scope=="online_task")].obsolete_recall.iloc[0]
        assert close(recall,reported)
    snapshot=json.loads((root/"phase2"/"phase1_snapshot.json").read_text(encoding="utf-8"))
    for rel,meta in snapshot.items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==meta["sha256"]
    shapes={p.name:mpimg.imread(p).shape for p in out.glob("*.png")}
    print(f"VALIDATION=PASS predictions={len(pred)} task_rows={len(details)} phase1_files={len(snapshot)} png={shapes}")


if __name__=="__main__": main()
