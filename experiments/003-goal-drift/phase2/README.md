# Phase 2 experiment

Phase 1 is preserved in the project-level `src/`, `data/`, and `results/` directories. Phase 2 reads those files only to build a SHA-256 audit snapshot; all new writes stay under `phase2/`.

```powershell
cd D:\数据挖掘KDD\验证实验\goal-drift-poc
python phase2/src/run_phase2.py
python phase2/src/run_phase2.py --check-determinism
```

The generator writes observable interactions and hidden labels to separate files. Detector tuning uses only complete development trajectories. Test predictions are generated from interactions before labels are joined by `evaluation.py`. Bootstrap sampling uses complete test trajectories.
