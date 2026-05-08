# BaseRate Alpha158 + LightGBM OOS Report

## Executive conclusion

recommendation = `stop_primitive_discovery_until_positive_base_rate`.

baseline_positive_after_cost = `False`.
baseline_negative_after_cost = `True`.
baseline_inconclusive_due_to_data_or_execution = `False`.

This stage establishes a PIT broad-universe Alpha158 + LightGBM after-cost OOS base rate. It does not discover primitives, validate a final strategy, or freeze a model.

## Scope and data

- provider: `data/qlib/cn_data_pit`
- universe: `data/universe/pit_mcap500_mainboard_daily.csv`
- decision label: `LABEL_1D_Q`
- decision portfolio: `topk_50_dropout_5_daily`
- execution: `next_open`, sell-first, no same-close execution.

## Data source and PIT universe audit

| data_source | path | exists | min_date | max_date | row_count | file_count | pass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pit_universe | data/universe/pit_mcap500_mainboard_daily.csv | True | 2017-07-04 | 2026-04-30 | 439140 | 0 | True |
| qlib_instruments | data/universe/qlib_pit_mcap500_mainboard.txt | True |  |  |  | 0 | True |
| qlib_provider | data/qlib/cn_data_pit | True | 2017-01-03 | 2026-04-30 |  | 3783 | True |
| pit_industry_membership | data/targets/pit_industry_membership.csv | True | 2017-07-04 | 2026-04-30 | 439140 | 0 | True |

PIT universe coverage sample:

| date | pit_member_count | provider_member_count | intersection_count | coverage_rate | pass |
| --- | --- | --- | --- | --- | --- |
| 2017-07-04 | 138 | 458 | 138 | 1 | True |
| 2017-07-05 | 140 | 458 | 140 | 1 | True |
| 2017-07-06 | 138 | 458 | 138 | 1 | True |
| 2017-07-07 | 142 | 458 | 142 | 1 | True |
| 2017-07-10 | 140 | 458 | 140 | 1 | True |
| 2017-07-11 | 140 | 458 | 140 | 1 | True |
| 2017-07-12 | 140 | 458 | 140 | 1 | True |
| 2017-07-13 | 140 | 458 | 140 | 1 | True |
| 2017-07-14 | 139 | 458 | 139 | 1 | True |
| 2017-07-17 | 135 | 458 | 135 | 1 | True |

## Prediction coverage and anti-leakage checks

Prediction coverage counts only PIT-member predictions, not raw model predictions outside the daily PIT universe.

| fold_id | date | pit_member_count | raw_prediction_count | prediction_count | extra_prediction_count | missing_prediction_count | prediction_coverage | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fold_2021 | 2021-01-04 | 231 | 296 | 231 | 65 | 0 | 1 | True |
| fold_2021 | 2021-01-05 | 233 | 297 | 233 | 64 | 0 | 1 | True |
| fold_2021 | 2021-01-06 | 233 | 297 | 233 | 64 | 0 | 1 | True |
| fold_2021 | 2021-01-07 | 238 | 299 | 238 | 61 | 0 | 1 | True |
| fold_2021 | 2021-01-08 | 238 | 300 | 238 | 62 | 0 | 1 | True |
| fold_2021 | 2021-01-11 | 237 | 302 | 237 | 65 | 0 | 1 | True |
| fold_2021 | 2021-01-12 | 240 | 302 | 240 | 62 | 0 | 1 | True |
| fold_2021 | 2021-01-13 | 240 | 302 | 240 | 62 | 0 | 1 | True |
| fold_2021 | 2021-01-14 | 236 | 301 | 236 | 65 | 0 | 1 | True |
| fold_2021 | 2021-01-15 | 237 | 301 | 237 | 64 | 0 | 1 | True |

## Model training summary

| fold_id | label_name | model_id | train_row_count | valid_row_count | best_iteration | valid_metric | rank_ic_mean_valid | fit_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fold_2021 | LABEL_1D_Q | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 116360 | 63366 | 46 | 0.00212446 | 0.0396464 | fit_success |
| fold_2022 | LABEL_1D_Q | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 179726 | 77139 | 32 | 0.00187446 | 0.0214568 | fit_success |
| fold_2023 | LABEL_1D_Q | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 256865 | 78126 | 14 | 0.000893865 | 0.0206295 | fit_success |
| fold_2024 | LABEL_1D_Q | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 334991 | 73850 | 7 | 0.000441506 | 0.00794367 | fit_success |
| fold_2025 | LABEL_1D_Q | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 408841 | 73446 | 35 | 0.00106623 | 0.0203702 | fit_success |
| fold_2021 | LABEL_5D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 116360 | 63366 | 51 | 0.0092146 | 0.0766751 | fit_success |
| fold_2022 | LABEL_5D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 179726 | 77139 | 15 | 0.00545733 | 0.0245337 | fit_success |
| fold_2023 | LABEL_5D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 256865 | 78126 | 56 | 0.00710841 | 0.0551452 | fit_success |
| fold_2024 | LABEL_5D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 334991 | 73850 | 7 | 0.00216164 | 0.0100493 | fit_success |
| fold_2025 | LABEL_5D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 408841 | 73446 | 96 | 0.00762296 | 0.0495043 | fit_success |
| fold_2021 | LABEL_10D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 116360 | 63366 | 51 | 0.0157938 | 0.0960031 | fit_success |
| fold_2022 | LABEL_10D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 179726 | 77139 | 1 | 0.0082888 | 0.015785 | fit_success |
| fold_2023 | LABEL_10D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 256865 | 78126 | 32 | 0.0093235 | 0.0621415 | fit_success |
| fold_2024 | LABEL_10D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 334991 | 73850 | 1 | 0.00409764 | 0.00412875 | fit_success |
| fold_2025 | LABEL_10D | LGBM_REGRESSION_ALPHA158_FIXED_V1 | 408841 | 73446 | 69 | 0.0116516 | 0.0582282 | fit_success |

## OOS net performance and benchmark comparison

| fold_id | portfolio_id | benchmark_id | cost_scenario | net_annual_return | benchmark_annual_return | excess_return | tracking_error | max_drawdown | benchmark_max_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | monthly_rebalance_topk_50 | pit_universe_equal_weight | base | -0.00128339 | 0.170878 | -0.172162 | 0.129923 | -0.123949 | -0.203583 |
| all_oos | monthly_rebalance_topk_50 | pit_universe_equal_weight | high | -0.00310534 | 0.170878 | -0.173984 | 0.129956 | -0.125877 | -0.203583 |
| all_oos | monthly_rebalance_topk_50 | pit_universe_equal_weight | low | 0.000671734 | 0.170878 | -0.170206 | 0.129889 | -0.121866 | -0.203583 |
| all_oos | topk_100_dropout_10 | pit_universe_equal_weight | base | 0.069406 | 0.170878 | -0.101472 | 0.0514372 | -0.23708 | -0.203583 |
| all_oos | topk_100_dropout_10 | pit_universe_equal_weight | high | 0.0300531 | 0.170878 | -0.140825 | 0.0514968 | -0.294083 | -0.203583 |
| all_oos | topk_100_dropout_10 | pit_universe_equal_weight | low | 0.112999 | 0.170878 | -0.0578788 | 0.0513718 | -0.22087 | -0.203583 |
| all_oos | topk_100_full_rebalance | pit_universe_equal_weight | base | -0.0452208 | 0.170878 | -0.216099 | 0.0480624 | -0.434039 | -0.203583 |
| all_oos | topk_100_full_rebalance | pit_universe_equal_weight | high | -0.152445 | 0.170878 | -0.323323 | 0.0483167 | -0.626013 | -0.203583 |
| all_oos | topk_100_full_rebalance | pit_universe_equal_weight | low | 0.0832201 | 0.170878 | -0.0876581 | 0.04783 | -0.225447 | -0.203583 |
| all_oos | topk_20_dropout_2 | pit_universe_equal_weight | base | 0.0499698 | 0.170878 | -0.120908 | 0.127388 | -0.400373 | -0.203583 |
| all_oos | topk_20_dropout_2 | pit_universe_equal_weight | high | 0.0115247 | 0.170878 | -0.159353 | 0.127554 | -0.446555 | -0.203583 |
| all_oos | topk_20_dropout_2 | pit_universe_equal_weight | low | 0.0924632 | 0.170878 | -0.078415 | 0.127228 | -0.361384 | -0.203583 |
| all_oos | topk_50_dropout_5 | pit_universe_equal_weight | base | 0.0916916 | 0.170878 | -0.0791866 | 0.081917 | -0.312438 | -0.203583 |
| all_oos | topk_50_dropout_5 | pit_universe_equal_weight | high | 0.0517019 | 0.170878 | -0.119176 | 0.0820133 | -0.351166 | -0.203583 |
| all_oos | topk_50_dropout_5 | pit_universe_equal_weight | low | 0.135921 | 0.170878 | -0.0349575 | 0.081808 | -0.268874 | -0.203583 |
| all_oos | topk_50_dropout_5_daily | pit_universe_equal_weight | base | 0.0916916 | 0.170878 | -0.0791866 | 0.081917 | -0.312438 | -0.203583 |
| all_oos | topk_50_dropout_5_daily | pit_universe_equal_weight | high | 0.0517019 | 0.170878 | -0.119176 | 0.0820133 | -0.351166 | -0.203583 |
| all_oos | topk_50_dropout_5_daily | pit_universe_equal_weight | low | 0.135921 | 0.170878 | -0.0349575 | 0.081808 | -0.268874 | -0.203583 |
| all_oos | topk_50_dropout_5_daily_label_10d | pit_universe_equal_weight | base | 0.0624881 | 0.170878 | -0.10839 | 0.0783379 | -0.298775 | -0.203583 |
| all_oos | topk_50_dropout_5_daily_label_10d | pit_universe_equal_weight | high | 0.0235912 | 0.170878 | -0.147287 | 0.0784242 | -0.351291 | -0.203583 |

Primary decision metrics:

```json
{
  "fold_id": "all_oos",
  "portfolio_id": "topk_50_dropout_5_daily",
  "benchmark_id": "pit_universe_equal_weight",
  "cost_scenario": "base",
  "net_annual_return": 0.09169162118114893,
  "benchmark_annual_return": 0.17087820239668683,
  "excess_return": -0.0791865812155379,
  "information_ratio": -0.8096617916888216,
  "max_drawdown": -0.3124380451462241,
  "benchmark_max_drawdown": -0.20358258485794067,
  "tracking_error": 0.08191699228615239
}
```

## Execution, turnover, and cost

| fold_id | portfolio_id | cost_scenario | order_count | trade_count | fill_rate | turnover_annualized | cost_drag_annualized |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | monthly_rebalance_topk_50 | base | 590 | 585 | 0.999587 | 2.43765 | 0.00425996 |
| all_oos | monthly_rebalance_topk_50 | high | 590 | 585 | 0.999587 | 2.438 | 0.00608183 |
| all_oos | monthly_rebalance_topk_50 | low | 590 | 585 | 0.999587 | 2.43728 | 0.00230822 |
| all_oos | topk_100_dropout_10 | base | 24078 | 23954 | 0.994772 | 49.8928 | 0.0872552 |
| all_oos | topk_100_dropout_10 | high | 24078 | 23954 | 0.994772 | 49.9196 | 0.124717 |
| all_oos | topk_100_dropout_10 | low | 24078 | 23954 | 0.994772 | 49.8624 | 0.0473153 |
| all_oos | topk_100_full_rebalance | base | 76338 | 76112 | 0.996997 | 158.221 | 0.276769 |
| all_oos | topk_100_full_rebalance | high | 76340 | 76106 | 0.996882 | 158.168 | 0.395321 |
| all_oos | topk_100_full_rebalance | low | 76339 | 76116 | 0.997049 | 158.257 | 0.150258 |
| all_oos | topk_20_dropout_2 | base | 4816 | 4779 | 0.991123 | 49.696 | 0.0869004 |
| all_oos | topk_20_dropout_2 | high | 4816 | 4779 | 0.991123 | 49.7094 | 0.124179 |
| all_oos | topk_20_dropout_2 | low | 4816 | 4779 | 0.991123 | 49.6775 | 0.047136 |
| all_oos | topk_50_dropout_5 | base | 12027 | 11932 | 0.991696 | 49.6887 | 0.0868986 |
| all_oos | topk_50_dropout_5 | high | 12027 | 11932 | 0.991696 | 49.7115 | 0.124199 |
| all_oos | topk_50_dropout_5 | low | 12027 | 11932 | 0.991696 | 49.6635 | 0.0471273 |
| all_oos | topk_50_dropout_5_daily | base | 12027 | 11932 | 0.991696 | 49.6887 | 0.0868986 |
| all_oos | topk_50_dropout_5_daily | high | 12027 | 11932 | 0.991696 | 49.7115 | 0.124199 |
| all_oos | topk_50_dropout_5_daily | low | 12027 | 11932 | 0.991696 | 49.6635 | 0.0471273 |
| all_oos | topk_50_dropout_5_daily_label_10d | base | 12011 | 11923 | 0.992236 | 49.5971 | 0.0867287 |
| all_oos | topk_50_dropout_5_daily_label_10d | high | 12011 | 11923 | 0.992236 | 49.6078 | 0.123925 |

Blocked-order summary:

| date | side | block_reason | order_count | blocked_order_count | blocked_notional | block_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2021-01-05 | buy | filled | 576 | 0 | 8.4e+06 | 0 |
| 2021-01-06 | buy | filled | 309 | 0 | 5.01058e+06 | 0 |
| 2021-01-06 | sell | filled | 228 | 0 | 3.53536e+06 | 0 |
| 2021-01-07 | buy | filled | 309 | 0 | 4.91139e+06 | 0 |
| 2021-01-07 | sell | filled | 267 | 0 | 4.20051e+06 | 0 |
| 2021-01-08 | buy | filled | 279 | 0 | 4.54904e+06 | 0 |
| 2021-01-08 | sell | filled | 240 | 0 | 4.00949e+06 | 0 |
| 2021-01-11 | buy | filled | 315 | 0 | 5.14471e+06 | 0 |
| 2021-01-11 | sell | filled | 297 | 0 | 4.81276e+06 | 0 |
| 2021-01-12 | buy | filled | 273 | 0 | 4.31131e+06 | 0 |
| 2021-01-12 | sell | filled | 246 | 0 | 3.83659e+06 | 0 |
| 2021-01-13 | buy | filled | 297 | 0 | 4.72915e+06 | 0 |
| 2021-01-13 | sell | filled | 279 | 0 | 4.30141e+06 | 0 |
| 2021-01-14 | buy | filled | 294 | 0 | 4.71614e+06 | 0 |
| 2021-01-14 | sell | filled | 243 | 0 | 3.70303e+06 | 0 |

## Random same-turnover baseline

random_same_turnover_p_value = `0.0`.

| fold_id | portfolio_id | repeat_id | same_turnover | same_turnover_or_n_drop | turnover_match_ratio | model_turnover_annualized | random_turnover_annualized | used_for_p_value | same_execution_constraints | same_cost_model | net_annual_return | empirical_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | topk_50_dropout_5_daily | 0 | True | True | 1.01191 | 49.6887 | 50.2807 | True | True | True | -0.0425559 | 0 |
| all_oos | topk_50_dropout_5_daily | 1 | True | True | 1.0118 | 49.6887 | 50.2751 | True | True | True | -0.0400996 | 0 |
| all_oos | topk_50_dropout_5_daily | 2 | True | True | 1.01128 | 49.6887 | 50.249 | True | True | True | -0.0426213 | 0 |
| all_oos | topk_50_dropout_5_daily | 3 | True | True | 0.994646 | 49.6887 | 49.4226 | True | True | True | -0.027892 | 0 |
| all_oos | topk_50_dropout_5_daily | 4 | True | True | 1.01096 | 49.6887 | 50.2335 | True | True | True | -0.0307139 | 0 |
| all_oos | topk_50_dropout_5_daily | 5 | True | True | 1.0108 | 49.6887 | 50.2253 | True | True | True | -0.0560168 | 0 |
| all_oos | topk_50_dropout_5_daily | 6 | True | True | 1.00559 | 49.6887 | 49.9666 | True | True | True | -0.0274457 | 0 |
| all_oos | topk_50_dropout_5_daily | 7 | True | True | 1.01235 | 49.6887 | 50.3023 | True | True | True | -0.0623986 | 0 |
| all_oos | topk_50_dropout_5_daily | 8 | True | True | 1.0124 | 49.6887 | 50.3046 | True | True | True | -0.0542179 | 0 |
| all_oos | topk_50_dropout_5_daily | 9 | True | True | 1.01223 | 49.6887 | 50.2964 | True | True | True | -0.0587431 | 0 |

## Cost sensitivity

| fold_id | portfolio_id | cost_scenario | net_annual_return | cost_drag_annualized | collapse_vs_base | pass |
| --- | --- | --- | --- | --- | --- | --- |
| all_oos | monthly_rebalance_topk_50 | base | -0.00128339 | 0.00425996 | True | False |
| all_oos | monthly_rebalance_topk_50 | high | -0.00310534 | 0.00608183 | True | False |
| all_oos | monthly_rebalance_topk_50 | low | 0.000671734 | 0.00230822 | False | True |
| all_oos | topk_100_dropout_10 | base | 0.069406 | 0.0872552 | False | True |
| all_oos | topk_100_dropout_10 | high | 0.0300531 | 0.124717 | False | True |
| all_oos | topk_100_dropout_10 | low | 0.112999 | 0.0473153 | False | True |
| all_oos | topk_100_full_rebalance | base | -0.0452208 | 0.276769 | True | False |
| all_oos | topk_100_full_rebalance | high | -0.152445 | 0.395321 | True | False |
| all_oos | topk_100_full_rebalance | low | 0.0832201 | 0.150258 | False | True |
| all_oos | topk_20_dropout_2 | base | 0.0499698 | 0.0869004 | False | True |
| all_oos | topk_20_dropout_2 | high | 0.0115247 | 0.124179 | True | False |
| all_oos | topk_20_dropout_2 | low | 0.0924632 | 0.047136 | False | True |
| all_oos | topk_50_dropout_5 | base | 0.0916916 | 0.0868986 | False | True |
| all_oos | topk_50_dropout_5 | high | 0.0517019 | 0.124199 | False | True |
| all_oos | topk_50_dropout_5 | low | 0.135921 | 0.0471273 | False | True |
| all_oos | topk_50_dropout_5_daily | base | 0.0916916 | 0.0868986 | False | True |
| all_oos | topk_50_dropout_5_daily | high | 0.0517019 | 0.124199 | False | True |
| all_oos | topk_50_dropout_5_daily | low | 0.135921 | 0.0471273 | False | True |
| all_oos | topk_50_dropout_5_daily_label_10d | base | 0.0624881 | 0.0867287 | False | True |
| all_oos | topk_50_dropout_5_daily_label_10d | high | 0.0235912 | 0.123925 | False | True |

## TopK / rebalance sensitivity

| fold_id | portfolio_id | label_name | topk | n_drop | rebalance | net_annual_return | turnover_annualized | decision_primary | selection_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | monthly_rebalance_topk_50 | LABEL_1D_Q | 50 | 5 | monthly | -0.00128339 | 2.43765 | False | False |
| all_oos | topk_100_dropout_10 | LABEL_1D_Q | 100 | 10 | daily | 0.069406 | 49.8928 | False | False |
| all_oos | topk_100_full_rebalance | LABEL_1D_Q | 100 | 100 | daily_full | -0.0452208 | 158.221 | False | False |
| all_oos | topk_20_dropout_2 | LABEL_1D_Q | 20 | 2 | daily | 0.0499698 | 49.696 | False | False |
| all_oos | topk_50_dropout_5 | LABEL_1D_Q | 50 | 5 | daily | 0.0916916 | 49.6887 | False | False |
| all_oos | topk_50_dropout_5_daily | LABEL_1D_Q | 50 | 5 | daily | 0.0916916 | 49.6887 | True | False |
| all_oos | topk_50_dropout_5_daily_label_10d | LABEL_10D | 50 | 5 | daily | 0.0624881 | 49.5971 | False | False |
| all_oos | topk_50_dropout_5_daily_label_5d | LABEL_5D | 50 | 5 | daily | 0.0778721 | 49.7185 | False | False |
| all_oos | topk_50_full_rebalance | LABEL_1D_Q | 50 | 50 | daily_full | -0.126037 | 237.175 | False | False |
| all_oos | weekly_rebalance_topk_50 | LABEL_1D_Q | 50 | 5 | weekly | 0.00216165 | 10.502 | False | False |

## Year-by-year results

| year | portfolio_id | cost_scenario | return | max_drawdown | turnover | cost_drag | benchmark_excess | fill_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | monthly_rebalance_topk_50 | base | 0.0221145 | -0.0389216 | 2.33184 | 0.00403761 | -0.292159 | 0.999587 |
| 2021 | monthly_rebalance_topk_50 | high | 0.0204445 | -0.0390716 | 2.33208 | 0.00574481 | -0.293899 | 0.999587 |
| 2021 | monthly_rebalance_topk_50 | low | 0.0239418 | -0.0387605 | 2.33158 | 0.0021724 | -0.290254 | 0.999587 |
| 2021 | topk_100_dropout_10 | base | 0.144715 | -0.121084 | 48.9594 | 0.0854248 | -0.164072 | 0.99067 |
| 2021 | topk_100_dropout_10 | high | 0.105382 | -0.123969 | 48.9895 | 0.121991 | -0.205229 | 0.99067 |
| 2021 | topk_100_dropout_10 | low | 0.188428 | -0.117947 | 48.9274 | 0.0462274 | -0.118262 | 0.99067 |
| 2021 | topk_100_full_rebalance | base | 0.0519107 | -0.165365 | 166.856 | 0.29169 | -0.261085 | 0.996642 |
| 2021 | topk_100_full_rebalance | high | -0.0670965 | -0.173227 | 166.963 | 0.416922 | -0.384968 | 0.996642 |
| 2021 | topk_100_full_rebalance | low | 0.195565 | -0.156924 | 166.736 | 0.158116 | -0.110776 | 0.996642 |
| 2021 | topk_20_dropout_2 | base | 0.0848762 | -0.115616 | 48.6243 | 0.0848424 | -0.226663 | 0.976584 |
| 2021 | topk_20_dropout_2 | high | 0.0477892 | -0.117312 | 48.652 | 0.121152 | -0.265385 | 0.976584 |
| 2021 | topk_20_dropout_2 | low | 0.126089 | -0.113811 | 48.5948 | 0.0459143 | -0.183569 | 0.976584 |
| 2021 | topk_50_dropout_5 | base | 0.230418 | -0.119487 | 48.9687 | 0.0854455 | -0.0741922 | 0.985399 |
| 2021 | topk_50_dropout_5 | high | 0.188237 | -0.122498 | 48.9968 | 0.122017 | -0.118462 | 0.985399 |
| 2021 | topk_50_dropout_5 | low | 0.277292 | -0.116245 | 48.9386 | 0.0462423 | -0.0249221 | 0.985399 |
| 2021 | topk_50_dropout_5_daily | base | 0.230418 | -0.119487 | 48.9687 | 0.0854455 | -0.0741922 | 0.985399 |
| 2021 | topk_50_dropout_5_daily | high | 0.188237 | -0.122498 | 48.9968 | 0.122017 | -0.118462 | 0.985399 |
| 2021 | topk_50_dropout_5_daily | low | 0.277292 | -0.116245 | 48.9386 | 0.0462423 | -0.0249221 | 0.985399 |
| 2021 | topk_50_dropout_5_daily_label_10d | base | 0.245752 | -0.187289 | 48.2649 | 0.0841792 | -0.0580825 | 0.983414 |
| 2021 | topk_50_dropout_5_daily_label_10d | high | 0.203285 | -0.190506 | 48.2847 | 0.120186 | -0.102676 | 0.983414 |

## Capacity and failure cases

| date | portfolio_id | estimated_trade_notional | money_available | participation_rate_proxy | capacity_warning | pass |
| --- | --- | --- | --- | --- | --- | --- |
| 2021-01-05 | topk_50_dropout_5_daily | 100000 | 4.85781e+09 | 2.05854e-05 | False | True |
| 2021-01-06 | topk_50_dropout_5_daily | 100435 | 1.20051e+10 | 8.36608e-06 | False | True |
| 2021-01-07 | topk_50_dropout_5_daily | 203793 | 8.67844e+09 | 2.34827e-05 | False | True |
| 2021-01-08 | topk_50_dropout_5_daily | 184406 | 1.64672e+10 | 1.11984e-05 | False | True |
| 2021-01-11 | topk_50_dropout_5_daily | 201963 | 7.26064e+09 | 2.78161e-05 | False | True |
| 2021-01-12 | topk_50_dropout_5_daily | 182849 | 1.59103e+10 | 1.14925e-05 | False | True |
| 2021-01-13 | topk_50_dropout_5_daily | 203896 | 1.35722e+10 | 1.50231e-05 | False | True |
| 2021-01-14 | topk_50_dropout_5_daily | 141018 | 7.27871e+09 | 1.9374e-05 | False | True |
| 2021-01-15 | topk_50_dropout_5_daily | 139777 | 4.50041e+09 | 3.10588e-05 | False | True |
| 2021-01-18 | topk_50_dropout_5_daily | 199041 | 1.35025e+10 | 1.4741e-05 | False | True |
| 2021-01-19 | topk_50_dropout_5_daily | 201549 | 1.77865e+10 | 1.13316e-05 | False | True |
| 2021-01-20 | topk_50_dropout_5_daily | 161253 | 2.00309e+10 | 8.05022e-06 | False | True |
| 2021-01-21 | topk_50_dropout_5_daily | 205010 | 2.83802e+10 | 7.22371e-06 | False | True |
| 2021-01-22 | topk_50_dropout_5_daily | 205328 | 2.26754e+10 | 9.05509e-06 | False | True |
| 2021-01-25 | topk_50_dropout_5_daily | 210391 | 4.19937e+10 | 5.01007e-06 | False | True |

| case_id | portfolio_id | failure_type | metric_impact | root_cause | action_required |
| --- | --- | --- | --- | --- | --- |
| no_positive_base_rate | topk_50_dropout_5_daily | negative_after_cost | 0.0916916 | see benchmark/cost/random baseline tables | stop_primitive_discovery_until_positive_base_rate |

## Forbidden conclusion self-check

| forbidden_output | observed_count | pass | evidence_path |
| --- | --- | --- | --- |
| primitive_candidate | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| candidate_for_p1_strategy | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| validated_model | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| production_model | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| selected_final_strategy | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| freeze_strategy | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| proceed_to_primitive_discovery | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| proceed_to_explore11 | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| candidate_for_p1_strategy | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| validated_strategy | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| selected_final_model | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
| selected_score_bucket | 0 | True | BaseRate/outputs/alpha158_lgbm_oos/reports/BaseRate-Alpha158-LGBM-OOS-report.md |
