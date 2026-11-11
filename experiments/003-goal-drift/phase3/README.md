# Phase 3: timing and reversible memory updates

All writes are isolated under `phase3/`. Phase 1 and phase 2 are read only and checked against a pre-run SHA-256 snapshot.

```powershell
cd D:\数据挖掘KDD\验证实验\goal-drift-poc
python -m unittest discover -s phase3\tests -v
python phase3\src\run_phase3.py
python phase3\src\run_phase3.py --check-determinism
python phase3\src\validate_results.py
```

`config/preregistered_config.json` and `results/phase3_design.md` were written before strategy implementation and formal testing. `oracle_timing` is a diagnostic upper bound and is excluded from deployable comparisons and the continue/stop decision.
