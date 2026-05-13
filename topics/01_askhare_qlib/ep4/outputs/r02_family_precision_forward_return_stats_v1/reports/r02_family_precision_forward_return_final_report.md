# R02 Family Precision And Forward Return Statistics V1 Final Report

## 结论摘要

- Final decision: `mixed_precision_keep_as_lifecycle_tags`
- frozen family count: 7
- action-time rows per condition: 395386
- headline precision uses post-close close-anchor statistics; next-open precision is audit-only.
- headline lift uses feature-matched background prior, not winner-window recall.

## Headline Precision

| family_id         | condition_group_id                    |   signal_count |   complete_h120_count |   positive_h120_count |   precision_h120_close_anchor |   background_prior_feature_matched_h120_close_anchor |   precision_lift_feature_matched_h120_close_anchor |   endpoint_return_mean |   endpoint_return_median |
|:------------------|:--------------------------------------|---------------:|----------------------:|----------------------:|------------------------------:|-----------------------------------------------------:|---------------------------------------------------:|-----------------------:|-------------------------:|
| momentum_rps      | momentum_rps__and3__68b32373ce93      |          44120 |                 33161 |                  5106 |                      0.153976 |                                             0.106504 |                                            1.44573 |            0.00204373  |              -0.0125945  |
| price_trend       | price_trend__and3__6030760ed19f       |          34592 |                 26293 |                  3999 |                      0.152094 |                                             0.106504 |                                            1.42806 |            0.000743023 |              -0.014549   |
| pullback_drawdown | pullback_drawdown__and3__11795aa42e45 |          56446 |                 43340 |                  6263 |                      0.144509 |                                             0.106504 |                                            1.35684 |            0.00209321  |              -0.0122526  |
| range_breakout    | range_breakout__and3__00e51295d9c3    |          68679 |                 52949 |                  5964 |                      0.112637 |                                             0.106527 |                                            1.05735 |            0.00510888  |              -0.00515809 |
| volatility_band   | volatility_band__and4__ef9c875dde10   |          28211 |                 21594 |                  2427 |                      0.112392 |                                             0.10653  |                                            1.05503 |            0.00285161  |              -0.00872604 |
| oscillator        | oscillator__and4__95dbd99ae828        |          23132 |                 17907 |                  2011 |                      0.112302 |                                             0.106504 |                                            1.05444 |            0.00340634  |              -0.00717423 |
| volume_money      | volume_money__and4__4eb7a99e922f      |          22806 |                 17529 |                  1961 |                      0.111872 |                                             0.106504 |                                            1.0504  |            0.0040251   |              -0.00860812 |

## Validation / Robustness Precision

| family_id         | split      |   signal_count |   precision_h120_close_anchor |   precision_lift_feature_matched_h120_close_anchor |   bootstrap_precision_lift_ci90_lower |
|:------------------|:-----------|---------------:|------------------------------:|---------------------------------------------------:|--------------------------------------:|
| momentum_rps      | robustness |          10929 |                     0.106352  |                                           1.10016  |                              0.96136  |
| momentum_rps      | validation |          10919 |                     0.0629973 |                                           1.23223  |                              1.0723   |
| oscillator        | robustness |           7042 |                     0.0814097 |                                           0.842145 |                              0.763908 |
| oscillator        | validation |           5409 |                     0.0506241 |                                           0.990214 |                              0.868502 |
| price_trend       | robustness |           8370 |                     0.0985395 |                                           1.01934  |                              0.897545 |
| price_trend       | validation |           7628 |                     0.069087  |                                           1.35135  |                              1.14068  |
| pullback_drawdown | robustness |          13646 |                     0.0956735 |                                           0.989697 |                              0.893    |
| pullback_drawdown | validation |          13044 |                     0.064206  |                                           1.25588  |                              1.11545  |
| range_breakout    | robustness |          19795 |                     0.0833875 |                                           0.86257  |                              0.813318 |
| range_breakout    | validation |          16810 |                     0.0558826 |                                           1.09283  |                              0.993259 |
| volatility_band   | robustness |           8668 |                     0.0776783 |                                           0.803513 |                              0.72921  |
| volatility_band   | validation |           6385 |                     0.0576961 |                                           1.12805  |                              0.949113 |
| volume_money      | robustness |           6311 |                     0.104011  |                                           1.07595  |                              0.997091 |
| volume_money      | validation |           5692 |                     0.0568464 |                                           1.11192  |                              0.976206 |

## T+1 / T+3 / T+5 / T+10 / T+20 Endpoint Return

| family_id         |   horizon |   complete_horizon_count |   endpoint_return_max |   endpoint_return_min |   endpoint_return_mean |   endpoint_return_median |   endpoint_return_positive_rate |
|:------------------|----------:|-------------------------:|----------------------:|----------------------:|-----------------------:|-------------------------:|--------------------------------:|
| momentum_rps      |         1 |                    44016 |              0.14386  |             -0.132203 |            0.000183285 |             -0.00197821  |                        0.454517 |
| momentum_rps      |         3 |                    43818 |              0.405138 |             -0.297124 |           -0.000435363 |             -0.00427648  |                        0.454676 |
| momentum_rps      |         5 |                    43584 |              0.584627 |             -0.390943 |           -0.000379038 |             -0.00544322  |                        0.458907 |
| momentum_rps      |        10 |                    43238 |              1.08424  |             -0.444796 |            0.000667161 |             -0.00702695  |                        0.460382 |
| momentum_rps      |        20 |                    42445 |              1.30831  |             -0.511312 |            0.00204373  |             -0.0125945   |                        0.454683 |
| oscillator        |         1 |                    23050 |              0.118717 |             -0.117143 |            0.00145816  |             -0.000764218 |                        0.460781 |
| oscillator        |         3 |                    22925 |              0.346021 |             -0.297124 |            0.00297163  |             -0.00113082  |                        0.477208 |
| oscillator        |         5 |                    22820 |              0.538043 |             -0.375706 |            0.00187709  |             -0.00216138  |                        0.47362  |
| oscillator        |        10 |                    22649 |              1.08424  |             -0.411974 |            0.00199399  |             -0.00329542  |                        0.472339 |
| oscillator        |        20 |                    22270 |              1.15145  |             -0.443743 |            0.00340634  |             -0.00717423  |                        0.464571 |
| price_trend       |         1 |                    34513 |              0.14386  |             -0.118624 |            0.000952905 |             -0.00172286  |                        0.460493 |
| price_trend       |         3 |                    34389 |              0.405138 |             -0.297124 |            0.00118395  |             -0.00363204  |                        0.463433 |
| price_trend       |         5 |                    34249 |              0.584627 |             -0.390943 |            0.000325194 |             -0.00512163  |                        0.462057 |
| price_trend       |        10 |                    33989 |              1.08424  |             -0.457995 |            0.000157629 |             -0.00779219  |                        0.455706 |
| price_trend       |        20 |                    33435 |              1.32829  |             -0.542909 |            0.000743023 |             -0.014549    |                        0.447705 |
| pullback_drawdown |         1 |                    56323 |              0.14386  |             -0.118624 |            0.000508196 |             -0.00180119  |                        0.456741 |
| pullback_drawdown |         3 |                    56099 |              0.405138 |             -0.297124 |            0.000679943 |             -0.0036563   |                        0.459063 |
| pullback_drawdown |         5 |                    55865 |              0.584627 |             -0.390943 |            0.000336618 |             -0.00514382  |                        0.459483 |
| pullback_drawdown |        10 |                    55486 |              1.08424  |             -0.444796 |            0.000485049 |             -0.00725003  |                        0.45862  |
| pullback_drawdown |        20 |                    54473 |              1.4043   |             -0.511312 |            0.00209321  |             -0.0122526   |                        0.453472 |
| range_breakout    |         1 |                    68496 |              0.14386  |             -0.118624 |            0.000510894 |             -0.00142669  |                        0.444756 |
| range_breakout    |         3 |                    68163 |              0.405138 |             -0.297124 |            0.0014017   |             -0.00206616  |                        0.464269 |
| range_breakout    |         5 |                    67847 |              0.578071 |             -0.390943 |            0.00137021  |             -0.00255754  |                        0.466284 |
| range_breakout    |        10 |                    67334 |              1.08424  |             -0.457995 |            0.00240908  |             -0.00297619  |                        0.473476 |
| range_breakout    |        20 |                    66118 |              1.30831  |             -0.542909 |            0.00510888  |             -0.00515809  |                        0.470946 |
| volatility_band   |         1 |                    28125 |              0.14386  |             -0.117143 |            0.00107339  |             -0.00145776  |                        0.451556 |
| volatility_band   |         3 |                    27992 |              0.405138 |             -0.291128 |            0.00235798  |             -0.0025413   |                        0.463168 |
| volatility_band   |         5 |                    27878 |              0.570542 |             -0.390943 |            0.00180758  |             -0.0036569   |                        0.461439 |
| volatility_band   |        10 |                    27698 |              1.08424  |             -0.439926 |            0.00228812  |             -0.00449993  |                        0.465557 |
| volatility_band   |        20 |                    27331 |              1.23325  |             -0.485213 |            0.00285161  |             -0.00872604  |                        0.45849  |
| volume_money      |         1 |                    22775 |              0.14386  |             -0.1376   |            0.000953065 |             -0.000960231 |                        0.459056 |
| volume_money      |         3 |                    22609 |              0.385991 |             -0.297124 |            0.0028763   |             -0.00134586  |                        0.474811 |
| volume_money      |         5 |                    22519 |              0.538043 |             -0.375706 |            0.00325882  |             -0.00226205  |                        0.471824 |
| volume_money      |        10 |                    22385 |              1.08424  |             -0.457995 |            0.00336318  |             -0.00355192  |                        0.470896 |
| volume_money      |        20 |                    21926 |              1.31328  |             -0.542909 |            0.0040251   |             -0.00860812  |                        0.453617 |

## Episode De-dup Audit

| family_id         |   signal_count |   complete_h120_count |   precision_h120_close_anchor |   precision_lift_feature_matched_h120_close_anchor |
|:------------------|---------------:|----------------------:|------------------------------:|---------------------------------------------------:|
| momentum_rps      |          11879 |                  9138 |                      0.140184 |                                            1.31623 |
| oscillator        |          13515 |                 10392 |                      0.115377 |                                            1.08331 |
| price_trend       |          12573 |                  9705 |                      0.138897 |                                            1.30416 |
| pullback_drawdown |          12889 |                  9961 |                      0.128702 |                                            1.20843 |
| range_breakout    |          18249 |                 13935 |                      0.114388 |                                            1.07379 |
| volatility_band   |          12756 |                  9756 |                      0.112956 |                                            1.06033 |
| volume_money      |          15975 |                 12196 |                      0.113562 |                                            1.06627 |

## Signal Redundancy Diagnostics

下表为 action-time stock-day 上的 family 信号冗余诊断。Phi / Jaccard 越高，越说明两个 family 可能在描述相近状态。

| family_a          | family_b          |   pair_denominator_count |   joint_signal_count |   p_b_given_a |   phi_correlation |   jaccard_overlap |   joint_precision_h120_close_anchor |
|:------------------|:------------------|-------------------------:|---------------------:|--------------:|------------------:|------------------:|------------------------------------:|
| momentum_rps      | pullback_drawdown |                   395386 |                38507 |      0.872779 |          0.739564 |          0.62049  |                            0.152284 |
| pullback_drawdown | momentum_rps      |                   395386 |                38507 |      0.682192 |          0.739564 |          0.62049  |                            0.152284 |
| momentum_rps      | price_trend       |                   395386 |                25197 |      0.571102 |          0.606598 |          0.47084  |                            0.162553 |
| price_trend       | momentum_rps      |                   395386 |                25197 |      0.728405 |          0.606598 |          0.47084  |                            0.162553 |
| price_trend       | pullback_drawdown |                   395386 |                28160 |      0.814061 |          0.59418  |          0.447851 |                            0.151539 |
| pullback_drawdown | price_trend       |                   395386 |                28160 |      0.498884 |          0.59418  |          0.447851 |                            0.151539 |
| price_trend       | volatility_band   |                   395272 |                19054 |      0.550821 |          0.57675  |          0.43553  |                            0.134456 |
| volatility_band   | price_trend       |                   395272 |                19054 |      0.67541  |          0.57675  |          0.43553  |                            0.134456 |
| range_breakout    | volatility_band   |                   395206 |                26652 |      0.388117 |          0.564153 |          0.379501 |                            0.112664 |
| volatility_band   | range_breakout    |                   395206 |                26652 |      0.944738 |          0.564153 |          0.379501 |                            0.112664 |
| price_trend       | range_breakout    |                   395273 |                28700 |      0.829672 |          0.536116 |          0.384868 |                            0.148702 |
| range_breakout    | price_trend       |                   395273 |                28700 |      0.417886 |          0.536116 |          0.384868 |                            0.148702 |

## Pairwise Incremental Precision Diagnostics

下表为 ordered pair 的诊断性 AND / only 统计。它只用于判断 added family 是否可能提供额外确认，不构成新信号。

| base_family     | added_family      |   base_signal_count |   base_and_added_signal_count |   base_precision_h120_close_anchor |   base_and_added_precision_h120_close_anchor |   delta_precision_base_and_added_minus_base |   signal_retention_base_and_added_vs_base |   complete_h120_count_base_and_added |
|:----------------|:------------------|--------------------:|------------------------------:|-----------------------------------:|---------------------------------------------:|--------------------------------------------:|------------------------------------------:|-------------------------------------:|
| range_breakout  | momentum_rps      |               68679 |                         27795 |                           0.112637 |                                     0.152845 |                                   0.040208  |                                  0.404709 |                                20969 |
| volume_money    | momentum_rps      |               22806 |                          8785 |                           0.111872 |                                     0.147964 |                                   0.036092  |                                  0.385206 |                                 6630 |
| range_breakout  | price_trend       |               68679 |                         28700 |                           0.112637 |                                     0.148702 |                                   0.0360651 |                                  0.417886 |                                21876 |
| oscillator      | momentum_rps      |               23132 |                         12397 |                           0.112302 |                                     0.148097 |                                   0.0357942 |                                  0.535924 |                                 9352 |
| range_breakout  | pullback_drawdown |               68679 |                         34407 |                           0.112637 |                                     0.141752 |                                   0.0291158 |                                  0.500983 |                                26511 |
| volatility_band | momentum_rps      |               28211 |                         16382 |                           0.112392 |                                     0.140371 |                                   0.0279785 |                                  0.580695 |                                12296 |
| oscillator      | price_trend       |               23132 |                         15000 |                           0.112302 |                                     0.139136 |                                   0.026834  |                                  0.648452 |                                11557 |
| volume_money    | price_trend       |               22806 |                         11565 |                           0.111872 |                                     0.134525 |                                   0.0226529 |                                  0.507103 |                                 8898 |
| volatility_band | price_trend       |               28211 |                         19054 |                           0.112392 |                                     0.134456 |                                   0.0220632 |                                  0.67541  |                                14555 |
| oscillator      | pullback_drawdown |               23132 |                         15071 |                           0.112302 |                                     0.132714 |                                   0.0204112 |                                  0.651522 |                                11619 |
| volume_money    | pullback_drawdown |               22806 |                          9694 |                           0.111872 |                                     0.12886  |                                   0.016988  |                                  0.425064 |                                 7481 |
| volatility_band | pullback_drawdown |               28211 |                         19098 |                           0.112392 |                                     0.128484 |                                   0.016092  |                                  0.67697  |                                14601 |

## Top-4 Independent Combined Precision

top-4 independent family set 只按信号独立性排序选择，不使用 precision、future return 或 big winner label。

|   selection_rank | selected_family_set                                              |   combo_mean_abs_phi |   combo_max_abs_phi |   combo_mean_jaccard |   combo_max_jaccard |
|-----------------:|:-----------------------------------------------------------------|---------------------:|--------------------:|---------------------:|--------------------:|
|                1 | momentum_rps, oscillator, pullback_drawdown, volume_money        |             0.378217 |            0.739564 |             0.276884 |            0.62049  |
|                2 | momentum_rps, oscillator, volatility_band, volume_money          |             0.378306 |            0.513275 |             0.265492 |            0.371634 |
|                3 | oscillator, pullback_drawdown, volatility_band, volume_money     |             0.381891 |            0.513275 |             0.264561 |            0.371634 |
|                4 | momentum_rps, oscillator, range_breakout, volume_money           |             0.388932 |            0.506765 |             0.261658 |            0.326985 |
|                5 | momentum_rps, pullback_drawdown, volatility_band, volume_money   |             0.394413 |            0.739564 |             0.292628 |            0.62049  |
|                6 | oscillator, pullback_drawdown, range_breakout, volume_money      |             0.39791  |            0.506765 |             0.26969  |            0.379274 |
|                7 | momentum_rps, range_breakout, volatility_band, volume_money      |             0.404571 |            0.564153 |             0.279041 |            0.379501 |
|                8 | oscillator, price_trend, pullback_drawdown, volume_money         |             0.405882 |            0.59418  |             0.285832 |            0.447851 |
|                9 | momentum_rps, oscillator, price_trend, volume_money              |             0.406082 |            0.606598 |             0.290346 |            0.47084  |
|               10 | pullback_drawdown, range_breakout, volatility_band, volume_money |             0.410836 |            0.564153 |             0.285552 |            0.379501 |

| split      | selected_family_set                                       |   top4_combined_signal_count |   top4_combined_complete_h120_count |   top4_combined_positive_h120_count |   top4_combined_precision_h120_close_anchor |   top4_background_prior_common_denominator_h120_close_anchor |   top4_precision_lift_vs_common_denominator |   top4_signal_retention_vs_min_single_family | sample_sufficiency_status   |
|:-----------|:----------------------------------------------------------|-----------------------------:|------------------------------------:|------------------------------------:|--------------------------------------------:|-------------------------------------------------------------:|--------------------------------------------:|---------------------------------------------:|:----------------------------|
| all        | momentum_rps, oscillator, pullback_drawdown, volume_money |                         5229 |                                3952 |                                 554 |                                   0.140182  |                                                    0.106504  |                                     1.31621 |                                     0.229282 | sufficient_for_diagnostic   |
| robustness | momentum_rps, oscillator, pullback_drawdown, volume_money |                         1473 |                                 926 |                                 117 |                                   0.12635   |                                                    0.0966695 |                                     1.30703 |                                     0.233402 | sufficient_for_diagnostic   |
| train      | momentum_rps, oscillator, pullback_drawdown, volume_money |                         2507 |                                1985 |                                 382 |                                   0.192443  |                                                    0.142722  |                                     1.34838 |                                     0.234716 | sufficient_for_diagnostic   |
| validation | momentum_rps, oscillator, pullback_drawdown, volume_money |                         1249 |                                1041 |                                  55 |                                   0.0528338 |                                                    0.0511244 |                                     1.03344 |                                     0.230911 | sufficient_for_diagnostic   |

## Decision Gate Audit

| condition_group_id                    | family_id         | split      | decision_grain   |   signal_count |   complete_h120_count |   positive_h120_count |   precision_lift_feature_matched_h120_close_anchor |   bootstrap_precision_lift_ci90_lower |   endpoint_return_median_t20 | signal_count_gate_pass   | complete_h120_gate_pass   | positive_h120_gate_pass   | lift_gate_pass   | bootstrap_gate_pass   | t20_median_gate_pass   | split_gate_pass   |
|:--------------------------------------|:------------------|:-----------|:-----------------|---------------:|----------------------:|----------------------:|---------------------------------------------------:|--------------------------------------:|-----------------------------:|:-------------------------|:--------------------------|:--------------------------|:-----------------|:----------------------|:-----------------------|:------------------|
| momentum_rps__and3__68b32373ce93      | momentum_rps      | robustness | stock_day        |          10929 |                  6864 |                   730 |                                           1.10016  |                              0.96136  |                  -0.00531683 | True                     | True                      | True                      | False            | False                 | False                  | False             |
| momentum_rps__and3__68b32373ce93      | momentum_rps      | validation | stock_day        |          10919 |                  9175 |                   578 |                                           1.23223  |                              1.0723   |                  -0.0283101  | True                     | True                      | True                      | False            | True                  | False                  | False             |
| oscillator__and4__95dbd99ae828        | oscillator        | robustness | stock_day        |           7042 |                  4852 |                   395 |                                           0.842145 |                              0.763908 |                   0.00157353 | True                     | True                      | True                      | False            | False                 | True                   | False             |
| oscillator__and4__95dbd99ae828        | oscillator        | validation | stock_day        |           5409 |                  4326 |                   219 |                                           0.990214 |                              0.868502 |                  -0.016899   | True                     | True                      | True                      | False            | False                 | False                  | False             |
| price_trend__and3__6030760ed19f       | price_trend       | robustness | stock_day        |           8370 |                  5409 |                   533 |                                           1.01934  |                              0.897545 |                  -0.00560051 | True                     | True                      | True                      | False            | False                 | False                  | False             |
| price_trend__and3__6030760ed19f       | price_trend       | validation | stock_day        |           7628 |                  6528 |                   451 |                                           1.35135  |                              1.14068  |                  -0.0284705  | True                     | True                      | True                      | False            | True                  | False                  | False             |
| pullback_drawdown__and3__11795aa42e45 | pullback_drawdown | robustness | stock_day        |          13646 |                  8968 |                   858 |                                           0.989697 |                              0.893    |                  -0.00432669 | True                     | True                      | True                      | False            | False                 | False                  | False             |
| pullback_drawdown__and3__11795aa42e45 | pullback_drawdown | validation | stock_day        |          13044 |                 11027 |                   708 |                                           1.25588  |                              1.11545  |                  -0.0258791  | True                     | True                      | True                      | False            | True                  | False                  | False             |
| range_breakout__and3__00e51295d9c3    | range_breakout    | robustness | stock_day        |          19795 |                 13851 |                  1155 |                                           0.86257  |                              0.813318 |                   0.0019355  | True                     | True                      | True                      | False            | False                 | True                   | False             |
| range_breakout__and3__00e51295d9c3    | range_breakout    | validation | stock_day        |          16810 |                 13081 |                   731 |                                           1.09283  |                              0.993259 |                  -0.0118319  | True                     | True                      | True                      | False            | False                 | False                  | False             |
| volatility_band__and4__ef9c875dde10   | volatility_band   | robustness | stock_day        |           8668 |                  5806 |                   451 |                                           0.803513 |                              0.72921  |                   0.00291545 | True                     | True                      | True                      | False            | False                 | True                   | False             |
| volatility_band__and4__ef9c875dde10   | volatility_band   | validation | stock_day        |           6385 |                  5113 |                   295 |                                           1.12805  |                              0.949113 |                  -0.0197487  | True                     | True                      | True                      | False            | False                 | False                  | False             |
| volume_money__and4__4eb7a99e922f      | volume_money      | robustness | stock_day        |           6311 |                  4288 |                   446 |                                           1.07595  |                              0.997091 |                  -0.00188381 | True                     | True                      | True                      | False            | False                 | False                  | False             |
| volume_money__and4__4eb7a99e922f      | volume_money      | validation | stock_day        |           5692 |                  4433 |                   252 |                                           1.11192  |                              0.976206 |                  -0.0154852  | True                     | True                      | True                      | False            | False                 | False                  | False             |

## Interpretation

这些统计只说明 frozen family 在 action-time 分母上的 posterior / forward-return 行为。pairwise AND / only 和 top-4 combined-AND 都是诊断性压力测试，不是当日可执行入场信号，也不直接生成 R03 promotion gate。
