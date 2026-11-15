# EP34 v3 archive — 2026-11-15

This publication records the existing v3 research and user-selected early-model observation pool. See [the primary handoff](../handoff/v3_primary_20261113/START_HERE.md). The early model is primary; momentum remains the control. Archived intermediate reports retain their original pending-choice and unsuccessful-branch statements; the primary handoff and current_goal.json record the later decision.

No new training, collection, deployment or trading is performed by this publication. These are local historical research results, not independently validated forward predictions or investment recommendations. Latest complete observation week is 2026-10-16, on data through 2026-10-21.

## Published and local-only artifacts

Code, protocols, reports, compact evaluation tables, handoff material and all 686 weekly candidate-directory CSVs are published. The weekly CSVs are stored in early_model_periods.tar.gz and momentum_periods.tar.gz. Extract each archive into handoff/v3_candidates_20261016/<method>/periods/ to restore the original file paths. All 343 members per archive were compared byte-for-byte with their source CSVs. Existing local CSVs are left untouched.

New bulk Parquet training/prediction/replay tables, joblib models and runtime caches remain local. Their hashes and exclusion reasons are in manifest.json. This does not remove previously tracked artifacts. A fresh clone alone is not sufficient to reproduce every data-dependent command; historical references to local-only inputs are retained rather than silently substituted. No EP35 changes are included.

## Validation

EP34 test suite: 114 passed. Selected text and compressed source CSVs passed credential-pattern scanning (not exhaustive secret certification). Publication scope and hashes are checked before commit. All original failed experiments and dated limitations remain unchanged.
