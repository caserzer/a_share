# EP3 Engineering Baseline Report

Generated at: 2026-05-10T02:07:45.237808+00:00

## EP3-P1 Decision

- `pullback_hold_restrengthen`: `no-go` / `failed_trigger_budget`
- `second_breakout`: `no-go` / `failed_trigger_budget`

## Gate Summary

- `pullback_hold_restrengthen`: 7/15 gates passed
- `second_breakout`: 9/15 gates passed

## Validation H20 Metrics

| anchor_family_id           | baseline_id                        |   event_count |   mean_after_cost_return_H20 |   p05_after_cost_return_H20 |   instrument_year_positive_rate |
|:---------------------------|:-----------------------------------|--------------:|-----------------------------:|----------------------------:|--------------------------------:|
| pullback_hold_restrengthen | anchor                             |            77 |                  -0.0587021  |                   -0.204964 |                        0.214286 |
| pullback_hold_restrengthen | all_launch_direct_baseline         |           941 |                  -0.0188492  |                   -0.177242 |                        0.254777 |
| pullback_hold_restrengthen | matched_delay_baseline             |            73 |                  -0.0365174  |                   -0.189718 |                        0.348485 |
| pullback_hold_restrengthen | same_instrument_nonanchor_baseline |            66 |                  -0.0429104  |                   -0.171896 |                        0.258065 |
| pullback_hold_restrengthen | industry_matched_baseline          |            50 |                  -0.0339273  |                   -0.17584  |                        0.318182 |
| pullback_hold_restrengthen | failed_lookalike_baseline          |           235 |                  -0.0350699  |                   -0.191127 |                        0.270408 |
| second_breakout            | anchor                             |            64 |                  -0.0209044  |                   -0.176741 |                        0.354839 |
| second_breakout            | all_launch_direct_baseline         |           941 |                  -0.0188492  |                   -0.177242 |                        0.254777 |
| second_breakout            | matched_delay_baseline             |            63 |                  -0.0121524  |                   -0.135981 |                        0.327869 |
| second_breakout            | same_instrument_nonanchor_baseline |            44 |                   0.00579863 |                   -0.177219 |                        0.44186  |
| second_breakout            | industry_matched_baseline          |            43 |                  -0.0337465  |                   -0.171671 |                        0.27027  |
| second_breakout            | failed_lookalike_baseline          |           171 |                  -0.0382168  |                   -0.190405 |                        0.280822 |

## Boundary

This EP3-P0 run is audit-only. A `go` requires `passed_to_ep3_p1_anchor_validation`; all `failed_*` statuses are no-go.
