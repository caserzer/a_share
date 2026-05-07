# Explore10D 电子 Launch Risk-Filter Primitive 复核审计报告

## 1. 执行结论
- recommendation = `proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement`。
- Explore10D 只验证 launch-risk-filter primitive。
- Explore10D 不验证 direct launch-winner trigger。
- Explore10D 不证明 primitive 可交易。
- 本阶段不训练新模型、不做新 path extraction、不做策略回测、不选择 score bucket。

## 2. Explore10C 继承与 Seed Freeze
| source_artifact                                                         | source_hash                                                      | source_recommendation                  | width_inheritance_pass   | scope_selection_lineage_pass   | data_discipline_pass   | feature_bank_v2_hygiene_pass   | v2_probe_trainability_pass   | candidate_freeze_pass   | required_artifact_authority_pass   | cache_tracking_pass   |   fold_2024_support_usage_count |   metric_selection_violation_count |   threshold_selection_violation_count |   model_selection_violation_count |   score_bucket_selection_violation_count | inheritance_pass   |   blocked_reason | pass   |
|:------------------------------------------------------------------------|:-----------------------------------------------------------------|:---------------------------------------|:-------------------------|:-------------------------------|:-----------------------|:-------------------------------|:-----------------------------|:------------------------|:-----------------------------------|:----------------------|--------------------------------:|-----------------------------------:|--------------------------------------:|----------------------------------:|-----------------------------------------:|:-------------------|-----------------:|:-------|
| Explore10/outputs/explore10c/reports/explore10c_recommendation_gate.csv | ff144f1419eb1c71f55e67ca47b8cd887d5690d66696153b8378489b03d01a91 | continue_explore10c_path_quality_audit | True                     | True                           | True                   | True                           | True                         | True                    | True                               | True                  |                               0 |                                  0 |                                     0 |                                 0 |                                        0 | True               |              nan | True   |
| freeze_timestamp                 | source_seed_artifact                                                            | source_seed_artifact_hash                                        | source_metric_artifact                                                          | source_metric_artifact_hash                                      | seed_selection_rule                                             | seed_selection_rule_hash   |   input_launch_seed_count |   frozen_launch_seed_count | new_seed_created   | seed_dropped_before_freeze   |   seed_dropped_reason | oof_metric_available_before_freeze   | oof_metric_used_for_display_only   | null_metric_available_before_freeze   | null_metric_read_before_freeze   | family_ablation_metric_available_before_freeze   | family_ablation_metric_read_before_freeze   | freeze_pass   | pass   |
|:---------------------------------|:--------------------------------------------------------------------------------|:-----------------------------------------------------------------|:--------------------------------------------------------------------------------|:-----------------------------------------------------------------|:----------------------------------------------------------------|:---------------------------|--------------------------:|---------------------------:|:-------------------|:-----------------------------|----------------------:|:-------------------------------------|:-----------------------------------|:--------------------------------------|:---------------------------------|:-------------------------------------------------|:--------------------------------------------|:--------------|:-------|
| 2026-05-07T14:15:47.641929+00:00 | Explore10/outputs/explore10c/reports/explore10c_atomic_primitive_seed_table.csv | faf5083b0075ef88ea0d7f75acbb180ca67040a7c7825cc7c30587e5f55a1792 | Explore10/outputs/explore10c/reports/explore10c_primitive_real_metric_audit.csv | 60dc2544807e64835bdaa89b2ff6bd7a220258c33db9c31dd8a39ba72e7fa826 | Explore10C launch_winner v2_hygiene eligible quality seeds only | 2007ba1ae6d771ad           |                        14 |                         14 | False              | False                        |                   nan | True                                 | True                               | True                                  | False                            | False                                            | False                                       | True          | True   |

## 3. Risk-Filter 重标
| primitive_seed_id          | explore10d_interpretation    |   risk_filter_token_count | formula_family_group                                        | relabel_used_metric   | relabel_pass   |
|:---------------------------|:-----------------------------|--------------------------:|:------------------------------------------------------------|:----------------------|:---------------|
| E10C_SEED_40178f7159342c21 | launch_risk_filter_candidate |                         2 | cross_section_rank+industry_market_context+volatility_range | False                 | True           |
| E10C_SEED_c161b734a948d4e1 | launch_risk_filter_candidate |                         2 | kbar_candle_shape+volatility_range                          | False                 | True           |
| E10C_SEED_bdada75fdd341add | launch_risk_filter_candidate |                         3 | industry_market_context+volatility_range                    | False                 | True           |
| E10C_SEED_a802bbc1ee927370 | launch_risk_filter_candidate |                         3 | cross_section_rank+volatility_range                         | False                 | True           |
| E10C_SEED_590e25e49151d6bc | launch_risk_filter_candidate |                         3 | volatility_range                                            | False                 | True           |
| E10C_SEED_7a91a9802f40eb58 | launch_risk_filter_candidate |                         1 | cross_section_rank+kbar_candle_shape+volatility_range       | False                 | True           |
| E10C_SEED_40eb71b01d3d40de | launch_risk_filter_candidate |                         3 | cross_section_rank+volatility_range                         | False                 | True           |
| E10C_SEED_407e18d7d05fdc98 | launch_risk_filter_candidate |                         2 | industry_market_context+price_distance+volatility_range     | False                 | True           |
| E10C_SEED_f41f0c1cf62a7319 | launch_risk_filter_candidate |                         3 | cross_section_rank+volatility_range                         | False                 | True           |
| E10C_SEED_fcda47e3c4b6e009 | launch_risk_filter_candidate |                         3 | industry_market_context+volatility_range                    | False                 | True           |
| E10C_SEED_c8cecb2b23026b7d | launch_risk_filter_candidate |                         2 | kbar_candle_shape+volatility_range+volume_money             | False                 | True           |
| E10C_SEED_c645f9790305e9cb | launch_risk_filter_candidate |                         3 | cross_section_rank+volatility_range                         | False                 | True           |
| E10C_SEED_86d5dde1c52d602c | launch_risk_filter_candidate |                         3 | cross_section_rank+volume_money                             | False                 | True           |
| E10C_SEED_3bd310d43fd4eb55 | launch_risk_filter_candidate |                         3 | industry_market_context+volatility_range                    | False                 | True           |

## 4. Support-Matched Null
| primitive_seed_id          | null_family                               |   core_fold_count |   real_metric |   null_mean |   null_p95 |   real_minus_null_p95 |   empirical_p_value | support_match_status     | included_in_fdr_family   | null_pass   | pass   |
|:---------------------------|:------------------------------------------|------------------:|--------------:|------------:|-----------:|----------------------:|--------------------:|:-------------------------|:-------------------------|:------------|:-------|
| E10C_SEED_3bd310d43fd4eb55 | support_matched_random_row_null           |                 3 |      0.798763 |    0.888145 |    1.51802 |            -0.71926   |          0.576846   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_fold_presence_null   |                 3 |      0.798763 |    0.867535 |    1.38578 |            -0.587013  |          0.580838   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_instrument_year_null |                 3 |      0.798763 |    0.92057  |    1.40934 |            -0.610576  |          0.606786   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_token_count_null     |                 3 |      0.798763 |    0.884043 |    1.39485 |            -0.596087  |          0.586826   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40178f7159342c21 | support_matched_random_row_null           |                 3 |      1.06444  |    0.858981 |    1.21015 |            -0.145709  |          0.161677   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40178f7159342c21 | support_matched_same_fold_presence_null   |                 3 |      1.06444  |    0.851925 |    1.21015 |            -0.145709  |          0.171657   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40178f7159342c21 | support_matched_same_instrument_year_null |                 3 |      1.06444  |    0.847115 |    1.0929  |            -0.0284638 |          0.155689   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40178f7159342c21 | support_matched_same_token_count_null     |                 3 |      1.06444  |    0.850299 |    1.0929  |            -0.0284638 |          0.137725   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_407e18d7d05fdc98 | support_matched_random_row_null           |                 3 |      0.903345 |    0.859336 |    1.0929  |            -0.18956   |          0.439122   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_fold_presence_null   |                 3 |      0.903345 |    0.851202 |    1.21015 |            -0.306805  |          0.421158   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_instrument_year_null |                 3 |      0.903345 |    0.87287  |    1.21015 |            -0.306805  |          0.483034   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_token_count_null     |                 3 |      0.903345 |    0.859127 |    1.0929  |            -0.18956   |          0.42515    | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40eb71b01d3d40de | support_matched_random_row_null           |                 3 |      1.19533  |    0.995693 |    1.32107 |            -0.125743  |          0.257485   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_fold_presence_null   |                 3 |      1.19533  |    1.00032  |    1.32555 |            -0.130222  |          0.269461   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_instrument_year_null |                 3 |      1.19533  |    0.999344 |    1.32555 |            -0.130222  |          0.267465   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_token_count_null     |                 3 |      1.19533  |    0.99471  |    1.32555 |            -0.130222  |          0.279441   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_590e25e49151d6bc | support_matched_random_row_null           |                 3 |      1.0414   |    0.994713 |    1.23941 |            -0.198009  |          0.393214   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_590e25e49151d6bc | support_matched_same_fold_presence_null   |                 3 |      1.0414   |    1.01589  |    1.23941 |            -0.198009  |          0.449102   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_590e25e49151d6bc | support_matched_same_instrument_year_null |                 3 |      1.0414   |    0.974362 |    1.23941 |            -0.198009  |          0.351297   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_590e25e49151d6bc | support_matched_same_token_count_null     |                 3 |      1.0414   |    0.974098 |    1.23941 |            -0.198009  |          0.345309   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_7a91a9802f40eb58 | support_matched_random_row_null           |                 3 |      0.837133 |    0.997341 |    1.32555 |            -0.488415  |          0.728543   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_fold_presence_null   |                 3 |      0.837133 |    1.01145  |    1.32107 |            -0.483935  |          0.782435   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_instrument_year_null |                 3 |      0.837133 |    1.02662  |    1.32555 |            -0.488415  |          0.782435   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_token_count_null     |                 3 |      0.837133 |    0.992112 |    1.32555 |            -0.488415  |          0.728543   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_86d5dde1c52d602c | support_matched_random_row_null           |                 3 |      1.18031  |    1.00014  |    1.32107 |            -0.140763  |          0.319361   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_fold_presence_null   |                 3 |      1.18031  |    1.00067  |    1.32555 |            -0.145243  |          0.323353   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_instrument_year_null |                 3 |      1.18031  |    0.998724 |    1.32555 |            -0.145243  |          0.297405   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_token_count_null     |                 3 |      1.18031  |    1.00651  |    1.32129 |            -0.140987  |          0.329341   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_a802bbc1ee927370 | support_matched_random_row_null           |                 3 |      1.23622  |    0.854088 |    1.0929  |             0.143315  |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_fold_presence_null   |                 3 |      1.23622  |    0.856831 |    1.0929  |             0.143315  |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_instrument_year_null |                 3 |      1.23622  |    0.848307 |    1.0929  |             0.143315  |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_token_count_null     |                 3 |      1.23622  |    0.845624 |    1.0929  |             0.143315  |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_bdada75fdd341add | support_matched_random_row_null           |                 3 |      0.973418 |    0.915541 |    1.51802 |            -0.544606  |          0.383234   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_bdada75fdd341add | support_matched_same_fold_presence_null   |                 3 |      0.973418 |    0.883442 |    1.40362 |            -0.430201  |          0.381238   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_bdada75fdd341add | support_matched_same_instrument_year_null |                 3 |      0.973418 |    0.911329 |    1.40934 |            -0.435922  |          0.39521    | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_bdada75fdd341add | support_matched_same_token_count_null     |                 3 |      0.973418 |    0.877762 |    1.38621 |            -0.412789  |          0.371257   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c161b734a948d4e1 | support_matched_random_row_null           |                 3 |      0.964919 |    0.86777  |    1.21015 |            -0.245231  |          0.351297   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_fold_presence_null   |                 3 |      0.964919 |    0.848083 |    1.0929  |            -0.127986  |          0.289421   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_instrument_year_null |                 3 |      0.964919 |    0.855728 |    1.0929  |            -0.127986  |          0.309381   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_token_count_null     |                 3 |      0.964919 |    0.857954 |    1.21015 |            -0.245231  |          0.331337   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c645f9790305e9cb | support_matched_random_row_null           |                 3 |      1.2825   |    0.85678  |    1.21015 |             0.0723516 |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_c645f9790305e9cb | support_matched_same_fold_presence_null   |                 3 |      1.2825   |    0.853409 |    1.21015 |             0.0723516 |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_c645f9790305e9cb | support_matched_same_instrument_year_null |                 3 |      1.2825   |    0.87035  |    1.0929  |             0.189596  |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_c645f9790305e9cb | support_matched_same_token_count_null     |                 3 |      1.2825   |    0.868615 |    1.21015 |             0.0723516 |          0.00199601 | exact_or_nearest_allowed | True                     | True        | True   |
| E10C_SEED_c8cecb2b23026b7d | support_matched_random_row_null           |                 3 |      0.501348 |    0.891843 |    1.37243 |            -0.871084  |          0.888224   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_fold_presence_null   |                 3 |      0.501348 |    0.896436 |    1.39485 |            -0.893502  |          0.902196   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_instrument_year_null |                 3 |      0.501348 |    0.910367 |    1.39485 |            -0.893502  |          0.9002     | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_token_count_null     |                 3 |      0.501348 |    0.898364 |    1.39439 |            -0.89304   |          0.9002     | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_random_row_null           |                 3 |      1.07234  |    0.897162 |    1.40362 |            -0.331275  |          0.257485   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_fold_presence_null   |                 3 |      1.07234  |    0.89067  |    1.38621 |            -0.313863  |          0.261477   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_instrument_year_null |                 3 |      1.07234  |    0.899756 |    1.51802 |            -0.44568   |          0.247505   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_token_count_null     |                 3 |      1.07234  |    0.914732 |    1.39439 |            -0.322045  |          0.263473   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_random_row_null           |                 3 |      0.742892 |    0.852771 |    1.0929  |            -0.350013  |          0.590818   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_fold_presence_null   |                 3 |      0.742892 |    0.854536 |    1.0929  |            -0.350013  |          0.610778   | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_instrument_year_null |                 3 |      0.742892 |    0.852206 |    1.21015 |            -0.467258  |          0.57485    | exact_or_nearest_allowed | True                     | False       | False  |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_token_count_null     |                 3 |      0.742892 |    0.868423 |    1.21015 |            -0.467258  |          0.638723   | exact_or_nearest_allowed | True                     | False       | False  |

## 5. Matched Null FDR
| primitive_seed_id          | null_family                               |   real_metric |   empirical_p_value |   bh_q_value | fdr_pass   |
|:---------------------------|:------------------------------------------|--------------:|--------------------:|-------------:|:-----------|
| E10C_SEED_3bd310d43fd4eb55 | support_matched_random_row_null           |      0.798763 |          0.576846   |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_fold_presence_null   |      0.798763 |          0.580838   |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_instrument_year_null |      0.798763 |          0.606786   |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | support_matched_same_token_count_null     |      0.798763 |          0.586826   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | support_matched_random_row_null           |      1.06444  |          0.161677   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | support_matched_same_fold_presence_null   |      1.06444  |          0.171657   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | support_matched_same_instrument_year_null |      1.06444  |          0.155689   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | support_matched_same_token_count_null     |      1.06444  |          0.137725   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | support_matched_random_row_null           |      0.903345 |          0.439122   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_fold_presence_null   |      0.903345 |          0.421158   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_instrument_year_null |      0.903345 |          0.483034   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | support_matched_same_token_count_null     |      0.903345 |          0.42515    |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | support_matched_random_row_null           |      1.19533  |          0.257485   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_fold_presence_null   |      1.19533  |          0.269461   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_instrument_year_null |      1.19533  |          0.267465   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | support_matched_same_token_count_null     |      1.19533  |          0.279441   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | support_matched_random_row_null           |      1.0414   |          0.393214   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | support_matched_same_fold_presence_null   |      1.0414   |          0.449102   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | support_matched_same_instrument_year_null |      1.0414   |          0.351297   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | support_matched_same_token_count_null     |      1.0414   |          0.345309   |    0.705229  | False      |
| E10C_SEED_7a91a9802f40eb58 | support_matched_random_row_null           |      0.837133 |          0.728543   |    0.807889  | False      |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_fold_presence_null   |      0.837133 |          0.782435   |    0.842622  | False      |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_instrument_year_null |      0.837133 |          0.782435   |    0.842622  | False      |
| E10C_SEED_7a91a9802f40eb58 | support_matched_same_token_count_null     |      0.837133 |          0.728543   |    0.807889  | False      |
| E10C_SEED_86d5dde1c52d602c | support_matched_random_row_null           |      1.18031  |          0.319361   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_fold_presence_null   |      1.18031  |          0.323353   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_instrument_year_null |      1.18031  |          0.297405   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | support_matched_same_token_count_null     |      1.18031  |          0.329341   |    0.705229  | False      |
| E10C_SEED_a802bbc1ee927370 | support_matched_random_row_null           |      1.23622  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_fold_presence_null   |      1.23622  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_instrument_year_null |      1.23622  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_a802bbc1ee927370 | support_matched_same_token_count_null     |      1.23622  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_bdada75fdd341add | support_matched_random_row_null           |      0.973418 |          0.383234   |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | support_matched_same_fold_presence_null   |      0.973418 |          0.381238   |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | support_matched_same_instrument_year_null |      0.973418 |          0.39521    |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | support_matched_same_token_count_null     |      0.973418 |          0.371257   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | support_matched_random_row_null           |      0.964919 |          0.351297   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_fold_presence_null   |      0.964919 |          0.289421   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_instrument_year_null |      0.964919 |          0.309381   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | support_matched_same_token_count_null     |      0.964919 |          0.331337   |    0.705229  | False      |
| E10C_SEED_c645f9790305e9cb | support_matched_random_row_null           |      1.2825   |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c645f9790305e9cb | support_matched_same_fold_presence_null   |      1.2825   |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c645f9790305e9cb | support_matched_same_instrument_year_null |      1.2825   |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c645f9790305e9cb | support_matched_same_token_count_null     |      1.2825   |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c8cecb2b23026b7d | support_matched_random_row_null           |      0.501348 |          0.888224   |    0.922664  | False      |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_fold_presence_null   |      0.501348 |          0.902196   |    0.922664  | False      |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_instrument_year_null |      0.501348 |          0.9002     |    0.922664  | False      |
| E10C_SEED_c8cecb2b23026b7d | support_matched_same_token_count_null     |      0.501348 |          0.9002     |    0.922664  | False      |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_random_row_null           |      1.07234  |          0.257485   |    0.705229  | False      |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_fold_presence_null   |      1.07234  |          0.261477   |    0.705229  | False      |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_instrument_year_null |      1.07234  |          0.247505   |    0.705229  | False      |
| E10C_SEED_f41f0c1cf62a7319 | support_matched_same_token_count_null     |      1.07234  |          0.263473   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_random_row_null           |      0.742892 |          0.590818   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_fold_presence_null   |      0.742892 |          0.610778   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_instrument_year_null |      0.742892 |          0.57485    |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | support_matched_same_token_count_null     |      0.742892 |          0.638723   |    0.729969  | False      |
| E10C_SEED_3bd310d43fd4eb55 | same_feature_family_set_null              |      0.798763 |          0.499002   |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | same_fold_presence_null                   |      0.798763 |          0.54491    |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | same_quantile_direction_mix_null          |      0.798763 |          0.528942   |    0.705229  | False      |
| E10C_SEED_3bd310d43fd4eb55 | same_token_count_null                     |      0.798763 |          0.566866   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | same_feature_family_set_null              |      1.06444  |          0.431138   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | same_fold_presence_null                   |      1.06444  |          0.399202   |    0.705229  | False      |
| E10C_SEED_40178f7159342c21 | same_quantile_direction_mix_null          |      1.06444  |          1          |    1         | False      |
| E10C_SEED_40178f7159342c21 | same_token_count_null                     |      1.06444  |          0.391218   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | same_feature_family_set_null              |      0.903345 |          0.610778   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | same_fold_presence_null                   |      0.903345 |          0.447106   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | same_quantile_direction_mix_null          |      0.903345 |          0.556886   |    0.705229  | False      |
| E10C_SEED_407e18d7d05fdc98 | same_token_count_null                     |      0.903345 |          0.556886   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | same_feature_family_set_null              |      1.19533  |          0.295409   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | same_fold_presence_null                   |      1.19533  |          0.305389   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | same_quantile_direction_mix_null          |      1.19533  |          0.305389   |    0.705229  | False      |
| E10C_SEED_40eb71b01d3d40de | same_token_count_null                     |      1.19533  |          0.347305   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | same_feature_family_set_null              |      1.0414   |          0.431138   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | same_fold_presence_null                   |      1.0414   |          0.391218   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | same_quantile_direction_mix_null          |      1.0414   |          0.377246   |    0.705229  | False      |
| E10C_SEED_590e25e49151d6bc | same_token_count_null                     |      1.0414   |          0.411178   |    0.705229  | False      |
| E10C_SEED_7a91a9802f40eb58 | same_feature_family_set_null              |      0.837133 |          0.528942   |    0.705229  | False      |
| E10C_SEED_7a91a9802f40eb58 | same_fold_presence_null                   |      0.837133 |          0.50499    |    0.705229  | False      |
| E10C_SEED_7a91a9802f40eb58 | same_quantile_direction_mix_null          |      0.837133 |          0.54491    |    0.705229  | False      |
| E10C_SEED_7a91a9802f40eb58 | same_token_count_null                     |      0.837133 |          0.546906   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | same_feature_family_set_null              |      1.18031  |          0.387226   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | same_fold_presence_null                   |      1.18031  |          0.279441   |    0.705229  | False      |
| E10C_SEED_86d5dde1c52d602c | same_quantile_direction_mix_null          |      1.18031  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_86d5dde1c52d602c | same_token_count_null                     |      1.18031  |          0.341317   |    0.705229  | False      |
| E10C_SEED_a802bbc1ee927370 | same_feature_family_set_null              |      1.23622  |          0.311377   |    0.705229  | False      |
| E10C_SEED_a802bbc1ee927370 | same_fold_presence_null                   |      1.23622  |          0.269461   |    0.705229  | False      |
| E10C_SEED_a802bbc1ee927370 | same_quantile_direction_mix_null          |      1.23622  |          0.325349   |    0.705229  | False      |
| E10C_SEED_a802bbc1ee927370 | same_token_count_null                     |      1.23622  |          0.289421   |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | same_feature_family_set_null              |      0.973418 |          0.423154   |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | same_fold_presence_null                   |      0.973418 |          0.44511    |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | same_quantile_direction_mix_null          |      0.973418 |          0.45509    |    0.705229  | False      |
| E10C_SEED_bdada75fdd341add | same_token_count_null                     |      0.973418 |          0.447106   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | same_feature_family_set_null              |      0.964919 |          0.512974   |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | same_fold_presence_null                   |      0.964919 |          0.46507    |    0.705229  | False      |
| E10C_SEED_c161b734a948d4e1 | same_quantile_direction_mix_null          |      0.964919 |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c161b734a948d4e1 | same_token_count_null                     |      0.964919 |          0.47505    |    0.705229  | False      |
| E10C_SEED_c645f9790305e9cb | same_feature_family_set_null              |      1.2825   |          0.275449   |    0.705229  | False      |
| E10C_SEED_c645f9790305e9cb | same_fold_presence_null                   |      1.2825   |          0.223553   |    0.705229  | False      |
| E10C_SEED_c645f9790305e9cb | same_quantile_direction_mix_null          |      1.2825   |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_c645f9790305e9cb | same_token_count_null                     |      1.2825   |          0.303393   |    0.705229  | False      |
| E10C_SEED_c8cecb2b23026b7d | same_feature_family_set_null              |      0.501348 |          0.906188   |    0.922664  | False      |
| E10C_SEED_c8cecb2b23026b7d | same_fold_presence_null                   |      0.501348 |          0.802395   |    0.855888  | False      |
| E10C_SEED_c8cecb2b23026b7d | same_quantile_direction_mix_null          |      0.501348 |          0.728543   |    0.807889  | False      |
| E10C_SEED_c8cecb2b23026b7d | same_token_count_null                     |      0.501348 |          0.742515   |    0.815311  | False      |
| E10C_SEED_f41f0c1cf62a7319 | same_feature_family_set_null              |      1.07234  |          0.437126   |    0.705229  | False      |
| E10C_SEED_f41f0c1cf62a7319 | same_fold_presence_null                   |      1.07234  |          0.373253   |    0.705229  | False      |
| E10C_SEED_f41f0c1cf62a7319 | same_quantile_direction_mix_null          |      1.07234  |          0.00199601 |    0.0186294 | True       |
| E10C_SEED_f41f0c1cf62a7319 | same_token_count_null                     |      1.07234  |          0.431138   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | same_feature_family_set_null              |      0.742892 |          0.560878   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | same_fold_presence_null                   |      0.742892 |          0.598802   |    0.705229  | False      |
| E10C_SEED_fcda47e3c4b6e009 | same_quantile_direction_mix_null          |      0.742892 |          1          |    1         | False      |
| E10C_SEED_fcda47e3c4b6e009 | same_token_count_null                     |      0.742892 |          0.588822   |    0.705229  | False      |

## 6. Family Ablation
| primitive_seed_id          | formula_family_group                       | volatility_range_is_necessary   | volume_money_is_necessary   | cross_section_rank_is_necessary   | industry_market_context_is_necessary   | formula_requires_cross_family_interaction   | risk_filter_interpretation_supported   | risk_filter_interpretation_weakens   | matched_null_fdr_pass   |   valid_ablation_suite_count | ablation_summary_pass   | pass   |
|:---------------------------|:-------------------------------------------|:--------------------------------|:----------------------------|:----------------------------------|:---------------------------------------|:--------------------------------------------|:---------------------------------------|:-------------------------------------|:------------------------|-----------------------------:|:------------------------|:-------|
| E10C_SEED_3bd310d43fd4eb55 | industry_market_context                    | False                           | False                       | True                              | True                                   | True                                        | False                                  | False                                | False                   |                            6 | False                   | False  |
| E10C_SEED_40178f7159342c21 | cross_section_rank;industry_market_context | False                           | False                       | True                              | True                                   | True                                        | False                                  | False                                | False                   |                            7 | False                   | False  |
| E10C_SEED_407e18d7d05fdc98 | industry_market_context;price_distance     | True                            | False                       | True                              | False                                  | False                                       | False                                  | True                                 | False                   |                            7 | False                   | False  |
| E10C_SEED_40eb71b01d3d40de | cross_section_rank                         | True                            | False                       | False                             | False                                  | False                                       | False                                  | False                                | False                   |                            7 | False                   | False  |
| E10C_SEED_590e25e49151d6bc | nan                                        | False                           | False                       | True                              | True                                   | True                                        | False                                  | False                                | False                   |                            5 | False                   | False  |
| E10C_SEED_7a91a9802f40eb58 | cross_section_rank;kbar_candle_shape       | True                            | False                       | True                              | True                                   | False                                       | False                                  | False                                | False                   |                            7 | False                   | False  |
| E10C_SEED_86d5dde1c52d602c | cross_section_rank;volume_money            | False                           | True                        | False                             | False                                  | False                                       | True                                   | False                                | True                    |                            7 | True                    | True   |
| E10C_SEED_a802bbc1ee927370 | cross_section_rank                         | False                           | False                       | False                             | False                                  | False                                       | False                                  | False                                | True                    |                            7 | False                   | False  |
| E10C_SEED_bdada75fdd341add | industry_market_context                    | False                           | False                       | True                              | True                                   | True                                        | False                                  | False                                | False                   |                            6 | False                   | False  |
| E10C_SEED_c161b734a948d4e1 | kbar_candle_shape                          | False                           | False                       | True                              | True                                   | True                                        | True                                   | False                                | True                    |                            7 | True                    | True   |
| E10C_SEED_c645f9790305e9cb | cross_section_rank                         | False                           | False                       | False                             | False                                  | False                                       | False                                  | False                                | True                    |                            7 | False                   | False  |
| E10C_SEED_c8cecb2b23026b7d | kbar_candle_shape;volume_money             | False                           | False                       | True                              | True                                   | True                                        | False                                  | True                                 | False                   |                            8 | False                   | False  |
| E10C_SEED_f41f0c1cf62a7319 | cross_section_rank                         | False                           | False                       | True                              | False                                  | False                                       | False                                  | True                                 | True                    |                            7 | False                   | False  |
| E10C_SEED_fcda47e3c4b6e009 | industry_market_context                    | False                           | False                       | True                              | True                                   | True                                        | False                                  | False                                | False                   |                            6 | False                   | False  |

## 7. Carry-Forward Sanity
| primitive_seed_id          |   top_instrument_weight_share |   top_instrument_year_weight_share |   top5_instrument_weight_share |   instrument_hhi |   instrument_year_hhi |   max_single_event_weight_share |   support_count |   weighted_support | concentration_pass   | pass   | concentration_carry_forward_pass   |
|:---------------------------|------------------------------:|-----------------------------------:|-------------------------------:|-----------------:|----------------------:|--------------------------------:|----------------:|-------------------:|:---------------------|:-------|:-----------------------------------|
| E10C_SEED_40178f7159342c21 |                      0.128015 |                          0.0537042 |                       0.566395 |        0.0846449 |             0.0341093 |                       0.0184725 |             582 |            646.814 | False                | False  | False                              |
| E10C_SEED_c161b734a948d4e1 |                      0.136001 |                          0.0654428 |                       0.532732 |        0.0781508 |             0.0344677 |                       0.0238846 |             531 |            500.249 | True                 | True   | True                               |
| E10C_SEED_bdada75fdd341add |                      0.133376 |                          0.0696912 |                       0.569775 |        0.0888194 |             0.038297  |                       0.0197915 |             420 |            423.619 | False                | False  | False                              |
| E10C_SEED_a802bbc1ee927370 |                      0.136996 |                          0.0627881 |                       0.544488 |        0.0821558 |             0.0368899 |                       0.0191289 |             614 |            624.62  | True                 | True   | True                               |
| E10C_SEED_590e25e49151d6bc |                      0.139147 |                          0.0523879 |                       0.484409 |        0.0729463 |             0.0328197 |                       0.0178648 |             528 |            439.062 | True                 | True   | True                               |
| E10C_SEED_7a91a9802f40eb58 |                      0.120601 |                          0.0477333 |                       0.47696  |        0.0717262 |             0.0278198 |                       0.0181779 |             679 |            657.298 | True                 | True   | True                               |
| E10C_SEED_40eb71b01d3d40de |                      0.110226 |                          0.0474654 |                       0.429287 |        0.0651554 |             0.0268286 |                       0.0118664 |             717 |            661.008 | True                 | True   | True                               |
| E10C_SEED_407e18d7d05fdc98 |                      0.10942  |                          0.0604252 |                       0.482955 |        0.0739257 |             0.0320853 |                       0.0129175 |             656 |            649.046 | True                 | True   | True                               |
| E10C_SEED_f41f0c1cf62a7319 |                      0.190672 |                          0.0826662 |                       0.626564 |        0.104164  |             0.0520928 |                       0.0325525 |             428 |            367.046 | False                | False  | False                              |
| E10C_SEED_fcda47e3c4b6e009 |                      0.128344 |                          0.073224  |                       0.578107 |        0.0894205 |             0.0439543 |                       0.0146448 |             508 |            535.6   | False                | False  | False                              |
| E10C_SEED_c8cecb2b23026b7d |                      0.158152 |                          0.0712233 |                       0.553228 |        0.0857989 |             0.0374277 |                       0.0253152 |             431 |            471.981 | False                | False  | False                              |
| E10C_SEED_c645f9790305e9cb |                      0.140824 |                          0.065033  |                       0.536912 |        0.0827435 |             0.0378324 |                       0.0198128 |             591 |            603.059 | True                 | True   | True                               |
| E10C_SEED_86d5dde1c52d602c |                      0.125403 |                          0.0518611 |                       0.451599 |        0.0691062 |             0.0295509 |                       0.0195431 |             568 |            611.382 | True                 | True   | True                               |
| E10C_SEED_3bd310d43fd4eb55 |                      0.14408  |                          0.080471  |                       0.604579 |        0.0959575 |             0.0427404 |                       0.0172028 |             441 |            487.365 | False                | False  | False                              |
| primitive_seed_id          |   source_slice_row_count | slice_stability_carry_forward_pass   | pass   |
|:---------------------------|-------------------------:|:-------------------------------------|:-------|
| E10C_SEED_3bd310d43fd4eb55 |                       73 | True                                 | True   |
| E10C_SEED_40178f7159342c21 |                       78 | True                                 | True   |
| E10C_SEED_407e18d7d05fdc98 |                       84 | True                                 | True   |
| E10C_SEED_40eb71b01d3d40de |                       94 | True                                 | True   |
| E10C_SEED_590e25e49151d6bc |                       80 | True                                 | True   |
| E10C_SEED_7a91a9802f40eb58 |                       94 | True                                 | True   |
| E10C_SEED_86d5dde1c52d602c |                       91 | True                                 | True   |
| E10C_SEED_a802bbc1ee927370 |                       77 | True                                 | True   |
| E10C_SEED_bdada75fdd341add |                       73 | True                                 | True   |
| E10C_SEED_c161b734a948d4e1 |                       77 | True                                 | True   |
| E10C_SEED_c645f9790305e9cb |                       76 | True                                 | True   |
| E10C_SEED_c8cecb2b23026b7d |                       78 | True                                 | True   |
| E10C_SEED_f41f0c1cf62a7319 |                       66 | True                                 | True   |
| E10C_SEED_fcda47e3c4b6e009 |                       72 | True                                 | True   |
| primitive_seed_id          | formula_text_resolved                                                                                                                 |   operator_count |   feature_count |   window_count |   threshold_bucket_count | uses_only_asof_observable_inputs   | raw_threshold_free   | leaf_id_free   | score_free   |   manual_formula_complexity_score | manualizability_pass   | manual_review_notes                    | pass   | manualizability_carry_forward_pass   |
|:---------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|-----------------:|----------------:|---------------:|-------------------------:|:-----------------------------------|:---------------------|:---------------|:-------------|----------------------------------:|:-----------------------|:---------------------------------------|:-------|:-------------------------------------|
| E10C_SEED_40178f7159342c21 | atr_like_10 <= train_q80_85 and money_20d_market_rank <= train_q75_80 and industry_relative_strength_vs_market_60d >= train_q00_05    |                2 |               3 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_c161b734a948d4e1 | atr_like_10 <= train_q80_85 and gap_open_pct >= train_q25_30 and atr20_pct >= train_q00_05                                            |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_bdada75fdd341add | atr_like_10 <= train_q80_85 and market_volatility_regime >= train_q15_20 and market_volatility_regime <= train_q80_85                 |                2 |               2 |              1 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_a802bbc1ee927370 | atr20_pct_market_rank <= train_q60_65 and atr_like_10 >= train_q00_05 and atr_like_10 <= train_q80_85                                 |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_590e25e49151d6bc | atr20_pct <= train_q75_80 and volatility_return_std_20 >= train_q05_10 and volatility_return_std_20 >= train_q20_25                   |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_7a91a9802f40eb58 | high_vol_destructive_ratio <= train_q80_85 and gap_open_pct >= train_q25_30 and ret_20d_market_rank <= train_q85_90                   |                2 |               3 |              1 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_40eb71b01d3d40de | atr20_pct_market_rank <= train_q70_75 and volatility_return_std_5 >= train_q10_15 and volatility_return_std_5 <= train_q85_90         |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_407e18d7d05fdc98 | atr20_pct <= train_q70_75 and market_volatility_regime >= train_q15_20 and close_over_median_10 <= train_q85_90                       |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_f41f0c1cf62a7319 | atr_like_10 <= train_q80_85 and atr_like_10 >= train_q05_10 and atr20_pct_industry_rank >= train_q30_35                               |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_fcda47e3c4b6e009 | atr_like_10 <= train_q80_85 and market_volatility_regime >= train_q25_30 and industry_relative_strength_vs_market_60d >= train_q00_05 |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_c8cecb2b23026b7d | atr_like_10 <= train_q80_85 and gap_open_pct >= train_q25_30 and money_over_mean_5 <= train_q75_80                                    |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_c645f9790305e9cb | atr_like_10 <= train_q80_85 and atr_like_10 >= train_q00_05 and atr20_pct_market_rank <= train_q55_60                                 |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_86d5dde1c52d602c | money_price_coherence_20 <= train_q65_70 and volume_price_divergence_20 <= train_q90_95 and atr20_pct_market_rank <= train_q70_75     |                2 |               3 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |
| E10C_SEED_3bd310d43fd4eb55 | atr_like_10 <= train_q80_85 and market_volatility_regime >= train_q15_20 and volatility_return_std_10 <= train_q60_65                 |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   | True                                 |

## 8. 11 个问题的直接回答
1. 问题：Explore10D 是否正确继承 Explore10C 的 engineering pass？
   回答：是。Explore10D 正确继承了 Explore10C 的工程与数据纪律通过事实；但没有继承“launch primitive 已成功”的结论。
2. 问题：Explore10D 是否没有创建新 seed？
   回答：是。输入 launch seed = 14，冻结后 launch seed = 14，`new_seed_created = False`，`seed_dropped_before_freeze = False`。
3. 问题：launch seeds 是否被非性能规则重标为 risk-filter candidates？
   回答：是。14 个 launch seeds 都被重标为 `launch_risk_filter_candidate`；重标只看公式 token / family，未使用收益、null、FDR 或 ablation 指标，`relabel_used_metric = False`。
4. 问题：support-matched null 是否改变 Explore10C 的 launch null 结论？
   回答：有改变，但不是全面翻盘。10C 中 launch side 没有 seed 通过原 null/FDR；10D 的 support-matched null 下有 2 个 seed 通过 FDR，但其余 12 个仍未通过。
5. 问题：structural matched null 是否显示 top launch seeds 有真实结构？
   回答：有结构证据，但证据很窄。structural matched null 下有 4 个 seed 通过 FDR，且 pass 都来自 `same_quantile_direction_mix_null`，不能解读为所有同 family / 同 token 近邻都稳健胜出。
6. 问题：family ablation 是否支持 volatility/range/money-coherence risk-filter interpretation？
   回答：部分支持。family ablation 只支持 2 个 seed：`E10C_SEED_86d5dde1c52d602c` 和 `E10C_SEED_c161b734a948d4e1`；其余 12 个不能用 ablation 支持 risk-filter 解释。
7. 问题：哪些 seeds 只是 support artifact 或 family artifact？
   回答：不能把所有 seed 都当成候选公式。`E10C_SEED_a802bbc1ee927370` 更像 support artifact；`E10C_SEED_86d5dde1c52d602c` 和 `E10C_SEED_c161b734a948d4e1` 更像 ablation-supported artifact；只有 `E10C_SEED_c645f9790305e9cb` 同时有 support + structural evidence，但 ablation 未支持。
8. 问题：failure secondary 是否仍然 dominance primary？
   回答：failure secondary 仍然只是 guardrail，不是 primary evidence。Explore10D 没有用 failure side 选择 launch seed、设定公式、设定阈值或支持 recommendation。
9. 问题：是否存在 concentration / slice / manualizability carry-forward blocker？
   回答：有 concentration blocker。14 个 seed 中 6 个 concentration carry-forward 失败；slice stability 和 manualizability 均为 14 / 14 通过。
10. 问题：是否可以进入 Explore10E manual formula review requirement？
    回答：是。可以进入 Explore10E，但含义仅是“值得人工复核 launch-risk-filter primitive”；不是 P1、不是回测、不是交易规则。
11. 问题：本阶段没有回答哪些交易或策略问题？
    回答：本阶段没有证明 primitive 可交易，没有验证 direct launch-winner trigger，没有选择 score bucket / threshold / trade rule，也没有进入 P1。

## 9. Recommendation Gate
| inheritance_pass   | launch_seed_freeze_pass   | launch_seed_relabel_pass   | metric_contract_pass   |   support_matched_null_pass_seed_count |   structural_matched_null_pass_seed_count |   matched_null_fdr_pass_seed_count |   family_ablation_supported_seed_count |   risk_filter_interpretation_supported_seed_count | failure_secondary_used_as_primary_evidence   |   concentration_carry_forward_pass_seed_count |   slice_stability_carry_forward_pass_seed_count |   manualizability_carry_forward_pass_seed_count |   fold_2024_support_usage_count |   metric_selection_violation_count |   threshold_selection_violation_count |   model_selection_violation_count |   score_bucket_selection_violation_count | required_artifact_authority_pass   | cache_tracking_pass   |   forbidden_output_violation_count | recommendation                                                             | recommendation_allowed   | recommendation_reason            | pass   |
|:-------------------|:--------------------------|:---------------------------|:-----------------------|---------------------------------------:|------------------------------------------:|-----------------------------------:|---------------------------------------:|--------------------------------------------------:|:---------------------------------------------|----------------------------------------------:|------------------------------------------------:|------------------------------------------------:|--------------------------------:|-----------------------------------:|--------------------------------------:|----------------------------------:|-----------------------------------------:|:-----------------------------------|:----------------------|-----------------------------------:|:---------------------------------------------------------------------------|:-------------------------|:---------------------------------|:-------|
| True               | True                      | True                       | True                   |                                      2 |                                         4 |                                  1 |                                      2 |                                                 2 | False                                        |                                             8 |                                              14 |                                              14 |                               0 |                                  0 |                                     0 |                                 0 |                                        0 | True                               | True                  |                                  0 | proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement | True                     | all_risk_filter_audit_gates_pass | True   |

## 10. 详细研究数据与结论解读

### 10.1 本阶段数据量与审计面

Explore10D 的实际审计面如下：

| 审计面 | 数据量 | 解释 |
|:--|--:|:--|
| frozen launch seeds | 14 | 全部来自 Explore10C `launch_winner` / `v2_hygiene` / `eligible_for_quality_audit = true`，没有新 seed。 |
| relabel pass seeds | 14 | 全部按 token / family 规则重标为 `launch_risk_filter_candidate`，`relabel_used_metric = False`。 |
| support-matched null summary rows | 56 | 14 seeds * 4 support-matched null families。 |
| support-matched null iteration rows | 28000 | 14 seeds * 4 families * 500 iterations。 |
| structural matched null iteration rows | 28000 | 14 seeds * 4 structural families * 500 iterations。 |
| matched-null FDR rows | 112 | 14 seeds * 8 matched-null families，所有 frozen seeds 均进入 FDR family。 |
| family ablation rows | 112 | 14 seeds * 8 ablation suites，invalid ablation row 也保留。 |
| carry-forward concentration pass seeds | 8 / 14 | 6 个 seed 仍有 top5 instrument concentration blocker。 |
| slice stability pass seeds | 14 / 14 | 当前 14 个 seed 都没有 slice carry-forward blocker。 |
| manualizability pass seeds | 14 / 14 | 当前公式都仍是人工可复核 seed，不含 raw threshold / leaf id / score。 |

这说明 Explore10D 的主要变化不是扩大搜索，而是把 Explore10C 的 14 个 launch seeds 放进更严格的 matched-null / family-ablation 审计框架。工程纪律是干净的；研究解释仍然需要谨慎。

### 10.2 Formula family 分布

14 个 launch-risk-filter seeds 的 formula family 仍高度集中：

| family | 出现次数 |
|:--|--:|
| volatility_range | 13 |
| cross_section_rank | 7 |
| industry_market_context | 5 |
| kbar_candle_shape | 3 |
| volume_money | 2 |
| price_distance | 1 |

我的判断：Explore10D 进一步确认，当前电子 launch seed 的核心不是“强趋势触发器”，而是“波动状态过滤器”。`volatility_range` 几乎覆盖全体 seeds，说明模型反复捕捉的是 launch 发生时的温度、波动和拥挤程度；`volume_money` 只出现在 2 个 seeds，但其中 1 个成为 ablation-supported seed，说明 money/volume coherence 的边际信息可能比出现频率更重要。

### 10.3 Seed-level evidence 汇总

| seed | real_lift | support FDR pass families | best support q | structural FDR pass families | best structural q | ablation supported | concentration pass | 主要 family |
|:--|--:|--:|--:|--:|--:|:--|:--|:--|
| E10C_SEED_c645f9790305e9cb | 1.2825 | 4 | 0.0186 | 1 | 0.0186 | False | True | cross_section_rank + volatility_range |
| E10C_SEED_a802bbc1ee927370 | 1.2362 | 4 | 0.0186 | 0 | 0.7052 | False | True | cross_section_rank + volatility_range |
| E10C_SEED_86d5dde1c52d602c | 1.1803 | 0 | 0.7052 | 1 | 0.0186 | True | True | cross_section_rank + volume_money |
| E10C_SEED_c161b734a948d4e1 | 0.9649 | 0 | 0.7052 | 1 | 0.0186 | True | True | kbar_candle_shape + volatility_range |
| E10C_SEED_f41f0c1cf62a7319 | 1.0723 | 0 | 0.7052 | 1 | 0.0186 | False | False | cross_section_rank + volatility_range |
| E10C_SEED_40eb71b01d3d40de | 1.1953 | 0 | 0.7052 | 0 | 0.7052 | False | True | cross_section_rank + volatility_range |
| E10C_SEED_40178f7159342c21 | 1.0644 | 0 | 0.7052 | 0 | 0.7052 | False | False | cross_section_rank + industry_market_context + volatility_range |
| E10C_SEED_590e25e49151d6bc | 1.0414 | 0 | 0.7052 | 0 | 0.7052 | False | True | volatility_range |
| E10C_SEED_bdada75fdd341add | 0.9734 | 0 | 0.7052 | 0 | 0.7052 | False | False | industry_market_context + volatility_range |
| E10C_SEED_407e18d7d05fdc98 | 0.9033 | 0 | 0.7052 | 0 | 0.7052 | False | True | industry_market_context + price_distance + volatility_range |
| E10C_SEED_7a91a9802f40eb58 | 0.8371 | 0 | 0.8079 | 0 | 0.7052 | False | True | cross_section_rank + kbar_candle_shape + volatility_range |
| E10C_SEED_3bd310d43fd4eb55 | 0.7988 | 0 | 0.7052 | 0 | 0.7052 | False | False | industry_market_context + volatility_range |
| E10C_SEED_fcda47e3c4b6e009 | 0.7429 | 0 | 0.7052 | 0 | 0.7052 | False | False | industry_market_context + volatility_range |
| E10C_SEED_c8cecb2b23026b7d | 0.5013 | 0 | 0.9227 | 0 | 0.8079 | False | False | kbar_candle_shape + volatility_range + volume_money |

最重要的研究现象是：三类证据没有完全落在同一批 seeds 上。

- support-matched FDR 通过的是 `E10C_SEED_c645f9790305e9cb` 和 `E10C_SEED_a802bbc1ee927370`。
- structural matched FDR 通过的是 `E10C_SEED_86d5dde1c52d602c`、`E10C_SEED_c161b734a948d4e1`、`E10C_SEED_c645f9790305e9cb`、`E10C_SEED_f41f0c1cf62a7319`。
- 同时通过 support + structural matched-null 的只有 `E10C_SEED_c645f9790305e9cb`。
- family ablation 支持 risk-filter interpretation 的是 `E10C_SEED_86d5dde1c52d602c` 和 `E10C_SEED_c161b734a948d4e1`。
- 没有任何一个 seed 同时满足 support + structural + ablation 三类最强证据。

我的判断：Explore10D 的通过结论应该被理解为“足够进入 Explore10E 人工公式复核”，不是“已有单一公式可以被提升”。下一阶段必须把 seed-level evidence overlap 作为第一优先级，否则容易把 support artifact、structural artifact、ablation artifact 混成一个不存在的统一结论。

### 10.4 Support-matched null 的含义

Support-matched null 下真正强的只有两个 volatility/rank 结构：

| seed | formula | real_lift | support matched FDR 结果 |
|:--|:--|--:|:--|
| E10C_SEED_c645f9790305e9cb | `atr_like_10 <= train_q80_85 and atr_like_10 >= train_q00_05 and atr20_pct_market_rank <= train_q55_60` | 1.2825 | 4 / 4 support families pass，q = 0.0186 |
| E10C_SEED_a802bbc1ee927370 | `atr20_pct_market_rank <= train_q60_65 and atr_like_10 >= train_q00_05 and atr_like_10 <= train_q80_85` | 1.2362 | 4 / 4 support families pass，q = 0.0186 |

这两个公式的共同点非常清楚：它们不是追逐极端高波动，而是在 ATR / volatility rank 上限制 launch 状态不能过热。研究含义更接近：

```text
avoid excessive launch volatility
keep launch volatility in a controlled range
avoid overheated launch state
```

我的判断：如果 Explore10E 要人工复核“风险过滤”公式，`E10C_SEED_c645f9790305e9cb` 应该排在第一优先级，因为它是唯一同时有 support-matched 和 structural matched 证据的 seed；`E10C_SEED_a802bbc1ee927370` 排第二，但它缺少 structural FDR 支持，必须防止被解释为更一般的 structural primitive。

### 10.5 Structural matched null 的含义

Structural matched null 的 pass 全部来自 `same_quantile_direction_mix_null`：

| seed | real_lift | structural pass family | q |
|:--|--:|:--|--:|
| E10C_SEED_86d5dde1c52d602c | 1.1803 | same_quantile_direction_mix_null | 0.0186 |
| E10C_SEED_c161b734a948d4e1 | 0.9649 | same_quantile_direction_mix_null | 0.0186 |
| E10C_SEED_c645f9790305e9cb | 1.2825 | same_quantile_direction_mix_null | 0.0186 |
| E10C_SEED_f41f0c1cf62a7319 | 1.0723 | same_quantile_direction_mix_null | 0.0186 |

这说明 seed 不是完全随机，但结构证据很窄：它主要证明特定 direction / quantile mix 有区分度，而不是证明同 family set、同 token count、同 fold presence 的所有近邻比较都稳定胜出。

我的判断：structural evidence 是“有结构”的证据，不是“结构稳健”的证据。Explore10E 不应该只沿用 `same_quantile_direction_mix_null` 的结果，而应该人工检查这些 formulas 是否能被压缩成可解释的少数规则，并要求规则在 same-family / same-token 近邻中仍有合理优势。

### 10.6 Family ablation 的含义

Family ablation 支持的两个 seed 是：

| seed | family group | 必要成分 | interpretation |
|:--|:--|:--|:--|
| E10C_SEED_86d5dde1c52d602c | cross_section_rank + volume_money | volume_money_is_necessary = True | money-price coherence / volume-price divergence 是核心；这是更像 risk-filter 的 seed。 |
| E10C_SEED_c161b734a948d4e1 | kbar_candle_shape + volatility_range | industry_market_context_is_necessary = True；formula_requires_cross_family_interaction = True | 单独 volatility 不够，可能依赖 gap / candle / volatility 的交互状态。 |

其中 `E10C_SEED_86d5dde1c52d602c` 的公式是：

```text
money_price_coherence_20 <= train_q65_70
and volume_price_divergence_20 <= train_q90_95
and atr20_pct_market_rank <= train_q70_75
```

这个 seed 的研究价值最高的地方不是 real_lift 最大，而是它把 `volume_money` 与 `ATR market rank` 组合在一起，并且 ablation 显示 volume_money 是必要项。它更符合“过滤不稳定资金价格状态”的直觉。

`E10C_SEED_c161b734a948d4e1` 的 real_lift 只有 0.9649，却在 structural null 和 ablation 上通过。这说明它不是 winner trigger；更合理的解释是它可能定义了一个 launch 状态边界，人工复核时应检查它是否用于排除局部过热或 gap 异常，而不是用于筛选上涨。

### 10.7 Concentration blocker

14 个 seeds 中，8 个通过 concentration carry-forward，6 个失败。失败主要由 top5 instrument weight share 超过阈值驱动：

| seed | top instrument weight share | top5 instrument weight share | support count | concentration pass |
|:--|--:|--:|--:|:--|
| E10C_SEED_f41f0c1cf62a7319 | 0.1907 | 0.6266 | 428 | False |
| E10C_SEED_3bd310d43fd4eb55 | 0.1441 | 0.6046 | 441 | False |
| E10C_SEED_fcda47e3c4b6e009 | 0.1283 | 0.5781 | 508 | False |
| E10C_SEED_bdada75fdd341add | 0.1334 | 0.5698 | 420 | False |
| E10C_SEED_40178f7159342c21 | 0.1280 | 0.5664 | 582 | False |
| E10C_SEED_c8cecb2b23026b7d | 0.1582 | 0.5532 | 431 | False |

我的判断：concentration 是 Explore10E 的硬风险点。尤其 `E10C_SEED_f41f0c1cf62a7319` 虽然 structural matched null 通过，但 concentration 失败且 ablation weakens = True，不应作为优先人工公式。相反，`E10C_SEED_c645f9790305e9cb`、`E10C_SEED_a802bbc1ee927370`、`E10C_SEED_86d5dde1c52d602c` 的 concentration pass 更适合进入人工复核短名单。

### 10.8 我的最终研究判断

Explore10D 支持进入 Explore10E，但理由应该写得很窄：

```text
当前电子 launch seeds 不支持 direct winner trigger；
当前证据支持继续复核 avoid-overheated / launch-risk-filter primitive；
最强候选方向是 controlled volatility range + money/volume coherence；
下一阶段必须做人工公式压缩、seed-level evidence overlap 检查、concentration 复核；
不能进入 P1、不能回测、不能选择 score bucket。
```

建议 Explore10E 的人工复核优先级：

| 优先级 | seed | 原因 | 注意事项 |
|:--|:--|:--|:--|
| 1 | E10C_SEED_c645f9790305e9cb | 唯一 support + structural matched-null overlap；real_lift 最高；concentration pass。 | Ablation 未支持 risk-filter interpretation，需要人工判断是否只是 volatility support artifact。 |
| 2 | E10C_SEED_86d5dde1c52d602c | structural pass + ablation supported；volume_money necessary；concentration pass。 | Support-matched FDR 未通过，不应单独作为强证据。 |
| 3 | E10C_SEED_c161b734a948d4e1 | structural pass + ablation supported；concentration pass。 | real_lift < 1，不能解释为 winner trigger，只能复核状态过滤边界。 |
| 4 | E10C_SEED_a802bbc1ee927370 | support-matched 4 / 4 pass；real_lift 高；concentration pass。 | structural FDR 未通过，可能是 support artifact。 |

停止或降级方向：

- `E10C_SEED_f41f0c1cf62a7319`：structural pass，但 concentration fail 且 ablation weakens，优先级应降低。
- `E10C_SEED_c8cecb2b23026b7d`：real_lift 低、support/structural 均不通过、concentration fail，不应进入 Explore10E 主复核。
- 单纯 `industry_market_context + volatility_range` 组合：多数组合没有 matched-null/FDR 支撑，不能泛化成行业 regime 规则。

因此，Explore10D 的研究结论应保持为：

```text
proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement
```

但 Explore10E 的 requirement 应显式要求：

```text
1. 不允许把 10D 结果写成 validated primitive；
2. 不允许把 support-pass seed 和 ablation-pass seed 合并成同一个结论；
3. 人工复核必须逐 seed 说明证据来源、缺口、concentration 风险；
4. 只有同时具备可解释公式、非过度集中、matched-null 支持的 seed 才能进入下一轮规则化讨论。
```
