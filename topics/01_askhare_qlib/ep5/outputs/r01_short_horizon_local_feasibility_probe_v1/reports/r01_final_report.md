# EP5 R01 Final Report

## 1. Boundary and non-goals

R01 did not perform alpha search.
R01 did not use big-winner labels for pass/fail.
R01 did not tune thresholds after validation.
R01 does not approve a production strategy.

## 2. Input and data audit

- Output root: `ep5/outputs/r01_short_horizon_local_feasibility_probe_v1`
- Validation status: `passed`

## 3. Canonical unit registry

- `r01_launch_breakout_money_surge_natural_exit_v0`: primary short-horizon exposure unit.
- `r01_launch_breakout_money_surge_fast_fail_v0`: secondary loss-control variant.
- `r01_base_breakout_vcp_sparse_natural_exit_v0`: backup sparse event-source probe.

## 4. Execution denominator and blocking

See `reports/r01_execution_block_audit.csv` and `reports/r01_denominator_audit.csv`.

## 5. H10 four-quadrant result

- Primary H10 quadrant: `absolute_false__relative_false`
- Primary H10 complete events: `592`
- Primary H10 mean net return: `-0.008268`
- Primary H10 mean matched delta: `0.007421`

## 6. H5/H20 horizon shape

See `reports/r01_horizon_shape_audit.csv`.

## 7. Matched comparator and relative edge

Matched-delta gate statistics use only `matched_comparator_status = comparable` rows.

## 8. Year / regime / beta-state decomposition

See `reports/r01_event_summary_by_unit_horizon_year.csv`, `reports/r01_regime_beta_decomposition.csv`, and `reports/r01_industry_liquidity_decomposition.csv`.

## 9. Robustness confirmation

- Primary robustness confirmed: `False`

## 10. Right-tail diagnostic, read-only

Right-tail outputs are post-entry diagnostics and are excluded from final decision computation.

## 11. Final decision and allowed next requirement

- Final decision: `r01_no_local_feasibility_support`
- Priority rule: `rule_13_no_local_feasibility_support`
- Allowed next requirement: `pause / renormalize`
- Blocked next requirements: `grid expansion`
- Reason: No canonical unit supplied local feasibility support.

## 12. Validator status

- `validation_status = passed`
- Passed gates: `28` / `28`
