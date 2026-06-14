# 09B Clustered Importance Report

本报告使用 config-frozen train-only diagnostic model，按 feature family 做 group permutation MDA / family ablation，并补充 single-feature importance。它不是 09C 最终模型，只用于冻结 feature foundation 的读数。

## Group MDA Top Rows

| target | split | family | auc_drop | baseline_auc |
| --- | --- | --- | ---: | ---: |
| fast_fail_only_10d | train | FS2_basis_path_quality | 0.265357 | 0.805228 |
| fast_fail_only_10d | robustness | FS2_basis_path_quality | 0.237637 | 0.744471 |
| fast_fail_only_10d | validation | FS2_basis_path_quality | 0.229910 | 0.755579 |
| false_repair_20d_component | robustness | FS0_baseline_h_features | 0.178866 | 0.704150 |
| hybrid_cost_bad_10_20 | robustness | FS0_baseline_h_features | 0.177962 | 0.666408 |
| false_repair_20d_component | validation | FS3_vol_range_stop_distance | 0.170798 | 0.707565 |
| hybrid_cost_bad_10_20 | train | FS0_baseline_h_features | 0.160124 | 0.687364 |
| false_repair_20d_component | train | FS0_baseline_h_features | 0.159806 | 0.699951 |
| hybrid_cost_bad_10_20 | validation | FS0_baseline_h_features | 0.134467 | 0.680330 |
| false_repair_20d_component | robustness | FS3_vol_range_stop_distance | 0.132222 | 0.704150 |
| hybrid_cost_bad_10_20 | validation | FS3_vol_range_stop_distance | 0.129602 | 0.680330 |
| fast_fail_only_10d | train | FS1_event_intrinsic | 0.127569 | 0.805228 |

## Single Feature Importance Top Rows

| target | split | feature | family | single_feature_auc |
| --- | --- | --- | --- | ---: |
| fast_fail_only_10d | robustness | return_20d | FS2_basis_path_quality | 0.759483 |
| fast_fail_only_10d | robustness | close_to_ema20 | FS2_basis_path_quality | 0.749334 |
| fast_fail_only_10d | robustness | return_20d_sigma_norm | FS3_vol_range_stop_distance | 0.743132 |
| fast_fail_only_10d | validation | close_to_ema20 | FS2_basis_path_quality | 0.736826 |
| fast_fail_only_10d | robustness | range_width_ratio_20d_60d | FS3_vol_range_stop_distance | 0.735238 |
| fast_fail_only_10d | validation | range_width_ratio_20d_60d | FS3_vol_range_stop_distance | 0.726480 |
| fast_fail_only_10d | train | close_to_ema20 | FS2_basis_path_quality | 0.725044 |
| false_repair_20d_component | robustness | atr_20_pct | FS3_vol_range_stop_distance | 0.722692 |
| fast_fail_only_10d | validation | panel_return_20d_rolling_z_60d | FS0_baseline_h_features | 0.717988 |
| false_repair_20d_component | validation | atr_20_pct | FS3_vol_range_stop_distance | 0.715768 |
| fast_fail_only_10d | validation | return_20d | FS2_basis_path_quality | 0.715397 |
| fast_fail_only_10d | train | return_10d | FS0_baseline_h_features | 0.713443 |

## Split Stability

| target | spearman | top3_overlap | status |
| --- | ---: | ---: | --- |
| false_repair_20d_component | 0.964286 | 2 | pass |
| fast_fail_only_10d | 0.821429 | 2 | pass |
| hybrid_cost_bad_10_20 | 1.000000 | 3 | pass |

## Caveat

validation / robustness importance 只读；feature selection、scaling 与 diagnostic fit 均只使用 R-core train scope。
