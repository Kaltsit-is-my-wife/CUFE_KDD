# InflMem sandbox demo summary

> Pipeline sanity check only; synthetic data, no LLM, not a scientific result.

- users: 20
- sessions: 3
- events: 60
- seed: 0

| metric | naive | provenance |
|---|---:|---:|
| cmr | 1.000 | 0.000 |
| cmr_cond | 1.000 | 0.000 |
| coverage | 1.000 | 1.000 |
| idr | 1.000 | 0.000 |
| sfb_beta | 0.112 | 0.009 |

## What this shows

- naive writer overclaims: all compliance events become durable preference; CMR = 1.0.
- provenance writer hedges recommendation-accepted mismatches: CMR = 0.0.
- provenance is too conservative in this demo: IDR = 0.0; it misses real internalization.
- SFB drops from 0.112 (naive) to 0.009 (provenance).

## What this does not show

- This is not a scientific result: 20 synthetic users, 60 events, no LLM, rule-based writers.
- It does not validate the real CMR threshold or Gate 1; that needs P2–P5's pipeline.
- The provenance writer needs persistence / negative controls / exploration to recover IDR.
