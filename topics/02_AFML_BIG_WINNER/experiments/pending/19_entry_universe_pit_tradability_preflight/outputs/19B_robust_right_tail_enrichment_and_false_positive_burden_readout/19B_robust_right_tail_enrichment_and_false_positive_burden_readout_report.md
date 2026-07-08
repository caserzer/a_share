# 19B 稳健右尾富集与假阳性负担读出报告

## 决策摘要

- decision_state: `19B_false_positive_burden_blocked`
- next_allowed_requirement: `none`
- validation outcome read: `false`
- model / policy / backtest / production / live trading authorization: `false`
- 19C replay remains forbidden unless a later validation-stress requirement authorizes it.

## Cell Readout

| family | grid_cell | p_candidate_50 | p_eligible_50 | positive_score | positive_pass | residual_pass | cell_decision_state |
|---|---:|---:|---:|---:|---|---|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | 0.2803 | 0.2104 | 0.0278 | True | False | false_positive_burden_blocked |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | 0.2270 | 0.2104 | -0.0256 | False | False | robustness_not_supported |

## Baseline Quality

| family | grid_cell | variant | quality_gate | unmatched_rate | max_smd | diagnostic_only |
|---|---|---|---|---:|---:|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | original_calendar_time_random_same_budget | fail | 0.0947 | 1.1168 | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | original_instrument_matched_random_same_budget | fail | 0.1424 | 1.0583 | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | original_liquidity_size_volatility_matched_same_budget | fail | 0.4588 | 0.7781 | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | repaired_lsv_return_cem_v1 | fail | 0.4588 | 0.7847 | True |
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | repaired_lsv_return_nn_caliper_v1 | fail | 0.0947 | 1.1048 | True |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | original_calendar_time_random_same_budget | fail | 0.0922 | 0.8955 | False |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | original_instrument_matched_random_same_budget | fail | 0.0721 | 0.8297 | False |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | original_liquidity_size_volatility_matched_same_budget | fail | 0.3557 | 0.5351 | False |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | repaired_lsv_return_cem_v1 | fail | 0.3557 | 0.5236 | True |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | repaired_lsv_return_nn_caliper_v1 | fail | 0.0922 | 0.8878 | True |

## False-Positive Burden

| family | grid_cell | candidate_per_winner | fast_fail_rate | false_repair_rate | mae_abs_worsening | gate |
|---|---|---:|---:|---:|---:|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | 3.568 | 0.489 | 0.489 | 0.0927 | fail |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | 4.406 | 0.465 | 0.465 | 0.0702 | fail |

## Required Figures

- `figures/tail_lift_curve.png`
- `figures/ccdf_survival_curve.png`
- `figures/capture_vs_burden.png`
- `figures/mfe_mae_joint_scatter.png`

## Boundary

- 19B 不读取 validation outcome。
- positive exposure persistence 不是 independent alpha。
- matched-baseline quality failure blocks residual-alpha support only.
- positive exposure persistence without matched-baseline residual pass can only support 19_entry_universe_enrichment_only_diagnostic.
- 19B 不授权 19C replay、EP20 policy preflight、entry policy、组合回测、production signal 或 live trading。
