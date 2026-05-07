# Explore10C 电子行业 Path Quality 与 Primitive Quality 审计报告

## 1. 执行结论
- recommendation = `continue_explore10c_path_quality_audit`。
- Explore10C 可以证明电子 path / primitive seed 是否有探索性质量证据；Explore10C 不能证明电子 primitive 可交易。
- 本阶段不输出 P1 candidate，不做策略回测，不选择 score bucket，不形成交易规则。

### 1.1 研究结论摘要

Explore10C 的主要结论不是“电子 launch primitive 已经失败”，而是更窄、更具体：

- 工程与数据纪律已经不是当前瓶颈：Explore10B width inheritance、post-selection lineage、data discipline、v2 hygiene、fixed probe、candidate freeze、artifact authority、cache tracking 全部通过。
- 电子 scope 的 v2 feature bank 可构造：v1 的 164 个 path-eligible features 在 fold-local train-scope unsupervised hygiene 后，global intersection 留下 81 个 v2 features；missingness 与重复簇问题显著降低，并保留全部 feature-family coverage。
- 固定 probe 具备 trainability：launch/failure 的 v1 与 v2 probes 在 `fold_2021/fold_2022/fold_2023` 均训练成功，且没有 hyperparameter search、early stopping、metric model selection 或 fold_2024 support usage。
- 真正的研究阻断发生在 primitive-quality 层：launch side 14 个 seed 都有 OOF support 和 fold presence，但没有任何 launch seed 通过 null/FDR family；failure secondary 侧有 24 个 FDR pass rows，触发 `placebo_or_secondary_dominates_primary = true`。
- 因此最合理解释是：电子宽行业标签确实解决了样本宽度问题，也能产生可解释 path forms；但当前 path evidence 更像 failure/avoidance diagnostic，而不是 launch-winner primitive seed。继续推进到 Explore10D manual formula review 会过早。

当前 recommendation 保持为：

```text
continue_explore10c_path_quality_audit
```

它的含义是：继续审计或重构 path-quality 设计，而不是进入 P1、策略回测、score bucket 或交易规则。

## 2. Explore10B 宽度继承与后验选择
| source_artifact                                                         | source_hash                                                      | width_problem_solved_phase_level   | electronics_launch_width_solved_excluding_expected_fold_2020_boundary   | secondary_failure_diagnostic_status   |   fold_2024_support_usage_count |   row_identity_mismatch_count |   feature_asof_leakage_violation_count |   observed_reference_decision_feature_overlap_eligible_rows | explore10b_recommendation                                  | inheritance_pass   |   blocked_reason | pass   |
|:------------------------------------------------------------------------|:-----------------------------------------------------------------|:-----------------------------------|:------------------------------------------------------------------------|:--------------------------------------|--------------------------------:|------------------------------:|---------------------------------------:|------------------------------------------------------------:|:-----------------------------------------------------------|:-------------------|-----------------:|:-------|
| Explore10/outputs/explore10b/reports/explore10b_recommendation_gate.csv | 628516c5c601f5d8ba244dc8cfa751f426a74c9fe136e21edc8d5f3f73a85d96 | True                               | True                                                                    | pass                                  |                               0 |                             0 |                                      0 |                                                           0 | proceed_to_explore10c_electronics_path_quality_requirement | True               |              nan | True   |
| selected_industry   | selected_primary_task   | selection_source_phase              | selection_source_artifact                                                                              | selection_reason                                                                               | was_selected_after_observing_trainability   | was_selected_after_observing_candidate_count   | was_selected_after_automotive_width_failure   | selection_metric_used_for_scope                                                   | selection_metric_allowed_for_10c   | post_selection_family_id             | selection_family_null_required   | allowed_conclusion                                   | forbidden_conclusion                              | scope_selection_lineage_pass   | pass   |
|:--------------------|:------------------------|:------------------------------------|:-------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------|:--------------------------------------------|:-----------------------------------------------|:----------------------------------------------|:----------------------------------------------------------------------------------|:-----------------------------------|:-------------------------------------|:---------------------------------|:-----------------------------------------------------|:--------------------------------------------------|:-------------------------------|:-------|
| 电子                | launch_winner           | Explore10 / Explore10A / Explore10B | explore10_atomic_primitive_candidate_table.csv;explore10a_report.md;explore10b_recommendation_gate.csv | electronics_width_solved_after_automotive_width_failure_and_reference_candidate_count_observed | True                                        | True                                           | True                                          | trainability_denominator;reference_candidate_count;automotive_scope_width_failure | True                               | post_selected_electronics_explore10c | True                             | post_selected_electronics_manual_review_seed_allowed | electronics_alpha_validated_or_tradable_primitive | True                           | True   |

## 3. Data Discipline
| row_surface_name              | task                               | fold_id   |   row_count |   row_identity_duplicate_count |   feature_asof_leakage_violation_count | fold_2024_used_for_support   | data_discipline_pass   |
|:------------------------------|:-----------------------------------|:----------|------------:|-------------------------------:|---------------------------------------:|:-----------------------------|:-----------------------|
| v1_reference_train_eval_panel | industry_failure_reject_score_lgbm | fold_2021 |        3636 |                              0 |                                      0 | False                        | True                   |
| v1_reference_train_eval_panel | industry_failure_reject_score_lgbm | fold_2022 |        4861 |                              0 |                                      0 | False                        | True                   |
| v1_reference_train_eval_panel | industry_failure_reject_score_lgbm | fold_2023 |        6107 |                              0 |                                      0 | False                        | True                   |
| v1_reference_train_eval_panel | industry_launch_winner_score_lgbm  | fold_2021 |        1104 |                              0 |                                      0 | False                        | True                   |
| v1_reference_train_eval_panel | industry_launch_winner_score_lgbm  | fold_2022 |        1472 |                              0 |                                      0 | False                        | True                   |
| v1_reference_train_eval_panel | industry_launch_winner_score_lgbm  | fold_2023 |        1913 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_failure_reject_score_lgbm | fold_2021 |        3636 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_failure_reject_score_lgbm | fold_2022 |        4861 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_failure_reject_score_lgbm | fold_2023 |        6107 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_launch_winner_score_lgbm  | fold_2021 |        1104 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_launch_winner_score_lgbm  | fold_2022 |        1472 |                              0 |                                      0 | False                        | True                   |
| v2_hygiene_train_eval_panel   | industry_launch_winner_score_lgbm  | fold_2023 |        1913 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_failure_reject_score_lgbm | fold_2021 |        3636 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_failure_reject_score_lgbm | fold_2022 |        4861 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_failure_reject_score_lgbm | fold_2023 |        6107 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_launch_winner_score_lgbm  | fold_2021 |        1104 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_launch_winner_score_lgbm  | fold_2022 |        1472 |                              0 |                                      0 | False                        | True                   |
| v2_feature_availability_panel | industry_launch_winner_score_lgbm  | fold_2023 |        1913 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | failure_reject                     | fold_2021 |        2400 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | failure_reject                     | fold_2022 |        2078 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | failure_reject                     | fold_2023 |        2086 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | launch_winner                      | fold_2021 |         824 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | launch_winner                      | fold_2022 |         712 |                              0 |                                      0 | False                        | True                   |
| fixed_probe_prediction_panel  | launch_winner                      | fold_2023 |         744 |                              0 |                                      0 | False                        | True                   |
| path_support_panel            | failure_reject                     | pooled    |         721 |                              0 |                                      0 | False                        | True                   |
| path_support_panel            | launch_winner                      | pooled    |        1258 |                              0 |                                      0 | False                        | True                   |
| primitive_seed_oof_panel      | industry_failure_reject_score_lgbm | fold_2021 |       37121 |                              0 |                                      0 | False                        | True                   |
| primitive_seed_oof_panel      | industry_failure_reject_score_lgbm | fold_2022 |       35005 |                              0 |                                      0 | False                        | True                   |
| primitive_seed_oof_panel      | industry_failure_reject_score_lgbm | fold_2023 |       46958 |                              0 |                                      0 | False                        | True                   |
| primitive_seed_oof_panel      | industry_launch_winner_score_lgbm  | fold_2021 |        2991 |                              0 |                                      0 | False                        | True                   |

## 4. Feature Bank v2 Hygiene
| feature_bank_v2_scope_id       |   v1_feature_count |   v2_feature_count |   missing_weight_share_before |   missing_weight_share_after |   duplicate_or_high_corr_cluster_count_before |   max_feature_family_share_after |   feature_family_coverage_after_hygiene | labels_read_for_v2   | oof_metric_read_for_v2   | fold_2024_used_for_v2   | feature_bank_v2_hygiene_pass   |
|:-------------------------------|-------------------:|-------------------:|------------------------------:|-----------------------------:|----------------------------------------------:|---------------------------------:|----------------------------------------:|:---------------------|:-------------------------|:------------------------|:-------------------------------|
| v2_hygiene_fold_fold_2021      |                164 |                 83 |                     0.128524  |                   0.00139554 |                                            16 |                         0.228916 |                                       1 | False                | False                    | False                   | True                           |
| v2_hygiene_fold_fold_2022      |                164 |                 87 |                     0.094345  |                   0.00991351 |                                            20 |                         0.206897 |                                       1 | False                | False                    | False                   | True                           |
| v2_hygiene_fold_fold_2023      |                164 |                105 |                     0.0775431 |                   0.0376102  |                                            23 |                         0.247619 |                                       1 | False                | False                    | False                   | True                           |
| v2_hygiene_global_intersection |                164 |                 81 |                     0.0775431 |                   0.0376102  |                                            23 |                         0.247619 |                                       1 | False                | False                    | False                   | True                           |

## 5. Fixed Probe 与 Candidate Freeze
| task           | fold_id   | feature_bank_version   |   train_rows |   validation_rows |   feature_count | model_fit_sanity_pass   | trainability_guardrail_pass   | path_extraction_allowed   |
|:---------------|:----------|:-----------------------|-------------:|------------------:|----------------:|:------------------------|:------------------------------|:--------------------------|
| launch_winner  | fold_2021 | v1_reference           |          643 |               412 |             160 | True                    | True                          | False                     |
| launch_winner  | fold_2022 | v1_reference           |         1033 |               356 |             160 | True                    | True                          | False                     |
| launch_winner  | fold_2023 | v1_reference           |         1425 |               372 |             160 | True                    | True                          | False                     |
| launch_winner  | fold_2021 | v2_hygiene             |          643 |               412 |              81 | True                    | True                          | True                      |
| launch_winner  | fold_2022 | v2_hygiene             |         1033 |               356 |              81 | True                    | True                          | True                      |
| launch_winner  | fold_2023 | v2_hygiene             |         1425 |               372 |              81 | True                    | True                          | True                      |
| failure_reject | fold_2021 | v1_reference           |         2175 |              1200 |             163 | True                    | True                          | False                     |
| failure_reject | fold_2022 | v1_reference           |         3349 |              1039 |             163 | True                    | True                          | False                     |
| failure_reject | fold_2023 | v1_reference           |         4459 |              1043 |             163 | True                    | True                          | False                     |
| failure_reject | fold_2021 | v2_hygiene             |         2175 |              1200 |              81 | True                    | True                          | True                      |
| failure_reject | fold_2022 | v2_hygiene             |         3349 |              1039 |              81 | True                    | True                          | True                      |
| failure_reject | fold_2023 | v2_hygiene             |         4459 |              1043 |              81 | True                    | True                          | True                      |
| freeze_timestamp                 | feature_bank_version   | probe_contract_id                             | candidate_extraction_budget                                                                                                                                                                                                                                                                                                                                                                                                              | candidate_extraction_budget_hash   | candidate_extraction_inputs_hash   |   max_path_depth |   min_train_path_support_count |   min_train_path_weighted_support |   max_paths_per_fold_task |   max_paths_total | path_dedup_identity                            | path_sort_key                                                                                               | candidate_metric_columns_available_before_freeze   | candidate_metric_columns_read_before_freeze   | oof_metric_computed_before_freeze   | null_metric_computed_before_freeze   | placebo_metric_computed_before_freeze   | manual_formula_modified_after_freeze   | freeze_pass   | pass   |
|:---------------------------------|:-----------------------|:----------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------|:-----------------------------------|-----------------:|-------------------------------:|----------------------------------:|--------------------------:|------------------:|:-----------------------------------------------|:------------------------------------------------------------------------------------------------------------|:---------------------------------------------------|:----------------------------------------------|:------------------------------------|:-------------------------------------|:----------------------------------------|:---------------------------------------|:--------------|:-------|
| 2026-05-07T11:19:11.205754+00:00 | v2_hygiene             | explore10c_fixed_lightgbm_no_inner_validation | {"max_path_depth": 4, "max_paths_per_feature_family": 20, "max_paths_per_fold_task": 40, "max_paths_total": 120, "max_raw_paths_considered": 2000, "min_train_path_support_count": 30, "min_train_path_weighted_support": 30.0, "path_dedup_identity": "normalized_feature_direction_quantile_sequence", "path_sort_key": "train_weighted_support_desc_then_path_depth_asc_then_feature_family_diversity_desc_then_path_pattern_id_asc"} | c8d4a5d50ab63097                   | cee186a5b2f3e772                   |                4 |                             30 |                                30 |                        40 |               120 | normalized_feature_direction_quantile_sequence | train_weighted_support_desc_then_path_depth_asc_then_feature_family_diversity_desc_then_path_pattern_id_asc | False                                              | False                                         | False                               | False                                | False                                   | False                                  | True          | True   |

## 6. Primitive Seeds 与 Null/FDR
| primitive_seed_id          | task           | primitive_family                              |   core_fold_presence_count | raw_numeric_threshold_in_formula   | leaf_id_in_formula   | score_bucket_in_formula   | manual_review_seed_allowed   |
|:---------------------------|:---------------|:----------------------------------------------|---------------------------:|:-----------------------------------|:---------------------|:--------------------------|:-----------------------------|
| E10C_SEED_cbf63de235d8a660 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_fd035923866fd1e4 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_2576d8f88654df29 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_10252ec52570449e | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_cb5fb1523206af15 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_348502511b66a9da | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_ae3b660a4862e871 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_dc129ba4bf693d78 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_27fd3e12ebde8180 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_453d5ee94b815758 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_7400f6587f37602f | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_5875a30005613d2d | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_a36ac1afd51d2500 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_01206ced30a80685 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_d2a2c0fa932a97f4 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_15a26f9130d9661c | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_47053ca671186ab9 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_b357ba4f2a3ccb27 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_6000a5438303e374 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| E10C_SEED_7782697252cebc56 | failure_reject | electronics_failure_secondary_diagnostic_seed |                          1 | False                              | False                | False                     | False                        |
| primitive_seed_id          | task           |   oof_support_count |   oof_lift_vs_scope_baseline |   fold_presence_count | null_adjusted_signal_status      | oof_quality_pass   |
|:---------------------------|:---------------|--------------------:|-----------------------------:|----------------------:|:---------------------------------|:-------------------|
| E10C_SEED_cbf63de235d8a660 | failure_reject |                1358 |                     1.04161  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_fd035923866fd1e4 | failure_reject |                1337 |                     1.04692  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_2576d8f88654df29 | failure_reject |                1340 |                     1.04445  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_10252ec52570449e | failure_reject |                1128 |                     1.16692  |                     3 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_cb5fb1523206af15 | failure_reject |                1036 |                     0.932919 |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_348502511b66a9da | failure_reject |                1111 |                     1.10016  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_ae3b660a4862e871 | failure_reject |                1048 |                     1.15239  |                     3 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_dc129ba4bf693d78 | failure_reject |                1127 |                     1.15928  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_27fd3e12ebde8180 | failure_reject |                1037 |                     0.856875 |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_453d5ee94b815758 | failure_reject |                1086 |                     1.16515  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_7400f6587f37602f | failure_reject |                1508 |                     0.979561 |                     3 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_5875a30005613d2d | failure_reject |                1203 |                     1.07847  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_a36ac1afd51d2500 | failure_reject |                 848 |                     0.937447 |                     3 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_01206ced30a80685 | failure_reject |                1084 |                     1.04333  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_d2a2c0fa932a97f4 | failure_reject |                1078 |                     1.04158  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_15a26f9130d9661c | failure_reject |                1020 |                     1.11378  |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_47053ca671186ab9 | failure_reject |                 850 |                     0.804974 |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_b357ba4f2a3ccb27 | failure_reject |                 920 |                     1.01335  |                     3 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_6000a5438303e374 | failure_reject |                 769 |                     0.962014 |                     2 | collapsed_or_unproven_under_null | True               |
| E10C_SEED_7782697252cebc56 | failure_reject |                 868 |                     0.734236 |                     3 | collapsed_or_unproven_under_null | True               |
| primitive_seed_id          | null_family                 |   real_metric |   empirical_p_value |   bh_q_value | fdr_pass   |
|:---------------------------|:----------------------------|--------------:|--------------------:|-------------:|:-----------|
| E10C_SEED_cbf63de235d8a660 | feature_family_dropout_null |      1.04161  |          0.0746269  |    0.223881  | False      |
| E10C_SEED_fd035923866fd1e4 | feature_family_dropout_null |      1.04692  |          0.0696517  |    0.219953  | False      |
| E10C_SEED_2576d8f88654df29 | feature_family_dropout_null |      1.04445  |          0.0597015  |    0.193626  | False      |
| E10C_SEED_10252ec52570449e | feature_family_dropout_null |      1.16692  |          0.0265781  |    0.118125  | False      |
| E10C_SEED_cb5fb1523206af15 | feature_family_dropout_null |      0.932919 |          0.965174   |    0.991567  | False      |
| E10C_SEED_348502511b66a9da | feature_family_dropout_null |      1.10016  |          0.0149254  |    0.0852878 | True       |
| E10C_SEED_ae3b660a4862e871 | feature_family_dropout_null |      1.15239  |          0.0232558  |    0.111628  | False      |
| E10C_SEED_dc129ba4bf693d78 | feature_family_dropout_null |      1.15928  |          0.00497512 |    0.0629481 | True       |
| E10C_SEED_27fd3e12ebde8180 | feature_family_dropout_null |      0.856875 |          1          |    1         | False      |
| E10C_SEED_453d5ee94b815758 | feature_family_dropout_null |      1.16515  |          0.00497512 |    0.0629481 | True       |
| E10C_SEED_7400f6587f37602f | feature_family_dropout_null |      0.979561 |          0.694352   |    0.991567  | False      |
| E10C_SEED_5875a30005613d2d | feature_family_dropout_null |      1.07847  |          0.00497512 |    0.0629481 | True       |
| E10C_SEED_a36ac1afd51d2500 | feature_family_dropout_null |      0.937447 |          0.774086   |    0.991567  | False      |
| E10C_SEED_01206ced30a80685 | feature_family_dropout_null |      1.04333  |          0.124378   |    0.297049  | False      |
| E10C_SEED_d2a2c0fa932a97f4 | feature_family_dropout_null |      1.04158  |          0.154229   |    0.324692  | False      |
| E10C_SEED_15a26f9130d9661c | feature_family_dropout_null |      1.11378  |          0.00995025 |    0.0629481 | True       |
| E10C_SEED_47053ca671186ab9 | feature_family_dropout_null |      0.804974 |          1          |    1         | False      |
| E10C_SEED_b357ba4f2a3ccb27 | feature_family_dropout_null |      1.01335  |          0.44186    |    0.803383  | False      |
| E10C_SEED_6000a5438303e374 | feature_family_dropout_null |      0.962014 |          0.766169   |    0.991567  | False      |
| E10C_SEED_7782697252cebc56 | feature_family_dropout_null |      0.734236 |          0.956811   |    0.991567  | False      |
| E10C_SEED_0272cec80954552f | feature_family_dropout_null |      0.966635 |          0.766169   |    0.991567  | False      |
| E10C_SEED_30f829b6b83e52c5 | feature_family_dropout_null |      1.09555  |          0.13289    |    0.30667   | False      |
| E10C_SEED_fecfc3193f49e499 | feature_family_dropout_null |      0.880125 |          0.887043   |    0.991567  | False      |
| E10C_SEED_4a9044adbaa2f918 | feature_family_dropout_null |      1.30578  |          0.00996678 |    0.0629481 | True       |
| E10C_SEED_970a764a07cfc2cb | feature_family_dropout_null |      1.06168  |          0.112957   |    0.297049  | False      |
| E10C_SEED_e7d3ad15ee2dc1db | feature_family_dropout_null |      1.00711  |          0.491694   |    0.880647  | False      |
| E10C_SEED_2ed424dc8a601fc6 | feature_family_dropout_null |      1.12322  |          0.0730897  |    0.223881  | False      |
| E10C_SEED_12c326ae4b214b07 | feature_family_dropout_null |      0.763458 |          0.906977   |    0.991567  | False      |
| E10C_SEED_722d9681c64453db | feature_family_dropout_null |      0.972508 |          0.684385   |    0.991567  | False      |
| E10C_SEED_4d73c55103327fa7 | feature_family_dropout_null |      0.981048 |          0.634551   |    0.991567  | False      |

## 7. Placebo / Concentration / Slice / Manualizability
| placebo_guardrail                        |   primary_pass_seed_count |   secondary_failure_pass_seed_count | placebo_or_secondary_dominates_primary   | recommendation_blocked_above_continue   | pass   |
|:-----------------------------------------|--------------------------:|------------------------------------:|:-----------------------------------------|:----------------------------------------|:-------|
| electronics_failure_secondary_diagnostic |                         0 |                                  24 | True                                     | True                                    | False  |
| automotive_failed_width_reference_only   |                         0 |                                  24 | False                                    | False                                   | True   |
| feature_family_dropout_placebo           |                         0 |                                  24 | False                                    | False                                   | True   |
| label_permutation_placebo                |                         0 |                                  24 | False                                    | False                                   | True   |
| primitive_seed_id          |   top_instrument_weight_share |   top_instrument_year_weight_share |   top5_instrument_weight_share |   instrument_hhi |   instrument_year_hhi |   max_single_event_weight_share |   support_count |   weighted_support | concentration_pass   | pass   |
|:---------------------------|------------------------------:|-----------------------------------:|-------------------------------:|-----------------:|----------------------:|--------------------------------:|----------------:|-------------------:|:---------------------|:-------|
| E10C_SEED_cbf63de235d8a660 |                     0.0972192 |                          0.0684031 |                       0.474964 |        0.0777922 |             0.0450824 |                       0.0123828 |            1358 |           1344.29  | True                 | True   |
| E10C_SEED_fd035923866fd1e4 |                     0.0986102 |                          0.0672573 |                       0.474295 |        0.0778368 |             0.0450493 |                       0.01256   |            1337 |           1325.33  | True                 | True   |
| E10C_SEED_2576d8f88654df29 |                     0.0982738 |                          0.0670279 |                       0.474723 |        0.0778527 |             0.0451099 |                       0.0125172 |            1340 |           1329.87  | True                 | True   |
| E10C_SEED_10252ec52570449e |                     0.16602   |                          0.0788831 |                       0.582276 |        0.0916145 |             0.0424902 |                       0.0135537 |            1128 |           1228.16  | False                | False  |
| E10C_SEED_cb5fb1523206af15 |                     0.158971  |                          0.0907141 |                       0.610397 |        0.102718  |             0.0604632 |                       0.0155866 |            1036 |           1067.98  | False                | False  |
| E10C_SEED_348502511b66a9da |                     0.113022  |                          0.0759544 |                       0.476737 |        0.0823502 |             0.0490197 |                       0.0148792 |            1111 |           1256.98  | True                 | True   |
| E10C_SEED_ae3b660a4862e871 |                     0.178026  |                          0.0845878 |                       0.618749 |        0.0997069 |             0.0456847 |                       0.0145339 |            1048 |           1145.33  | False                | False  |
| E10C_SEED_dc129ba4bf693d78 |                     0.115541  |                          0.0822679 |                       0.499879 |        0.0821719 |             0.0510004 |                       0.0141353 |            1127 |           1177.63  | True                 | True   |
| E10C_SEED_27fd3e12ebde8180 |                     0.150649  |                          0.0859655 |                       0.663398 |        0.116976  |             0.0650807 |                       0.0147706 |            1037 |           1126.98  | False                | False  |
| E10C_SEED_453d5ee94b815758 |                     0.108578  |                          0.0839026 |                       0.47582  |        0.0801543 |             0.0488322 |                       0.0166342 |            1086 |           1124.36  | True                 | True   |
| E10C_SEED_7400f6587f37602f |                     0.120015  |                          0.0497205 |                       0.484058 |        0.0733122 |             0.0289694 |                       0.0189623 |            1508 |           1531.88  | True                 | True   |
| E10C_SEED_5875a30005613d2d |                     0.110617  |                          0.0791858 |                       0.478688 |        0.0792257 |             0.0472262 |                       0.0144454 |            1203 |           1152.35  | True                 | True   |
| E10C_SEED_a36ac1afd51d2500 |                     0.196433  |                          0.103945  |                       0.608205 |        0.104114  |             0.0651928 |                       0.0223248 |             848 |            745.638 | False                | False  |
| E10C_SEED_01206ced30a80685 |                     0.104429  |                          0.0764709 |                       0.473817 |        0.0797125 |             0.0447109 |                       0.0152248 |            1084 |           1093.36  | True                 | True   |
| E10C_SEED_d2a2c0fa932a97f4 |                     0.110854  |                          0.0824142 |                       0.483344 |        0.0796362 |             0.0451356 |                       0.0156283 |            1078 |           1065.13  | True                 | True   |
| E10C_SEED_15a26f9130d9661c |                     0.129482  |                          0.0846613 |                       0.540216 |        0.0863645 |             0.0529203 |                       0.0154008 |            1020 |           1080.87  | True                 | True   |
| E10C_SEED_47053ca671186ab9 |                     0.185775  |                          0.10601   |                       0.765832 |        0.140853  |             0.086702  |                       0.0155971 |             850 |            913.889 | False                | False  |
| E10C_SEED_b357ba4f2a3ccb27 |                     0.150863  |                          0.102459  |                       0.599797 |        0.097081  |             0.0581843 |                       0.0248726 |             920 |            751.947 | False                | False  |
| E10C_SEED_6000a5438303e374 |                     0.166397  |                          0.10817   |                       0.68291  |        0.122481  |             0.0722595 |                       0.0185858 |             769 |            895.639 | False                | False  |
| E10C_SEED_7782697252cebc56 |                     0.121017  |                          0.0960935 |                       0.536175 |        0.085702  |             0.0557985 |                       0.0226619 |             868 |            734.544 | True                 | True   |
| primitive_seed_id          | formula_text_resolved                                                                                                                                |   operator_count |   feature_count |   window_count |   threshold_bucket_count | uses_only_asof_observable_inputs   | raw_threshold_free   | leaf_id_free   | score_free   |   manual_formula_complexity_score | manualizability_pass   | manual_review_notes                    | pass   |
|:---------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|-----------------:|----------------:|---------------:|-------------------------:|:-----------------------------------|:---------------------|:---------------|:-------------|----------------------------------:|:-----------------------|:---------------------------------------|:-------|
| E10C_SEED_cbf63de235d8a660 | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and close_over_max_high_20 <= train_q95_100                  |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_fd035923866fd1e4 | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and close_over_median_20 >= train_q00_05                     |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_2576d8f88654df29 | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and close_over_ma_20 >= train_q00_05                         |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_10252ec52570449e | atr_like_10 <= train_q80_85 and atr_like_10 >= train_q00_05 and industry_relative_strength_vs_market_60d >= train_q30_35                             |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_cb5fb1523206af15 | atr_like_10 <= train_q75_80 and atr_like_10 >= train_q00_05 and market_volatility_regime <= train_q60_65                                             |                2 |               2 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_348502511b66a9da | industry_relative_strength_vs_market_60d >= train_q30_35 and market_volatility_regime <= train_q55_60 and close_over_min_low_5 >= train_q00_05       |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_ae3b660a4862e871 | atr_like_10 <= train_q75_80 and atr_like_10 >= train_q00_05 and industry_relative_strength_vs_market_60d >= train_q30_35                             |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_dc129ba4bf693d78 | market_volatility_regime <= train_q60_65 and industry_relative_strength_vs_market_60d >= train_q30_35 and volume_price_divergence_20 <= train_q90_95 |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_27fd3e12ebde8180 | atr_like_10 <= train_q75_80 and market_volatility_regime <= train_q60_65 and atr_like_10 <= train_q65_70                                             |                2 |               2 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_453d5ee94b815758 | market_volatility_regime <= train_q60_65 and industry_relative_strength_vs_market_60d >= train_q30_35 and amplitude_10 >= train_q00_05               |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_7400f6587f37602f | high_vol_constructive_ratio <= train_q40_45 and money_5d_market_rank <= train_q85_90 and high_vol_destructive_ratio <= train_q80_85                  |                2 |               3 |              1 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_5875a30005613d2d | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and body_pct >= train_q05_10                                 |                2 |               3 |              1 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_a36ac1afd51d2500 | atr_like_10 <= train_q80_85 and atr_like_10 >= train_q00_05 and atr20_pct_market_rank >= train_q35_40                                                |                2 |               2 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_01206ced30a80685 | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and close_over_max_high_20 <= train_q80_85                   |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_d2a2c0fa932a97f4 | market_volatility_regime <= train_q60_65 and volume_price_divergence_10 <= train_q80_85 and close_over_max_high_10 <= train_q80_85                   |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_15a26f9130d9661c | market_volatility_regime <= train_q60_65 and industry_relative_strength_vs_market_60d >= train_q30_35 and gap_open_pct >= train_q15_20               |                2 |               3 |              1 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_47053ca671186ab9 | atr_like_10 <= train_q80_85 and market_volatility_regime <= train_q60_65 and atr_like_10 <= train_q50_55                                             |                2 |               2 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_b357ba4f2a3ccb27 | atr20_pct_market_rank >= train_q45_50 and close_over_max_high_20 >= train_q05_10 and close_over_close_20d <= train_q90_95                            |                2 |               3 |              3 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_6000a5438303e374 | market_volatility_regime <= train_q60_65 and industry_relative_strength_vs_market_60d >= train_q30_35 and atr_like_10 <= train_q65_70                |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |
| E10C_SEED_7782697252cebc56 | atr20_pct_market_rank >= train_q45_50 and low_close_ratio >= train_q05_10 and close_over_max_high_20 >= train_q05_10                                 |                2 |               3 |              2 |                        3 | True                               | True                 | True           | True         |                                 6 | True                   | manual_review_seed_only_not_trade_rule | True   |

## 8. 详细研究数据与初步洞察

### 8.1 Gate 结果拆解

Explore10C 的 gate 结果可以拆成两类：

| gate group | result | 解释 |
|---|---:|---|
| width / lineage / discipline | pass | 电子宽度继承成立，后验选择被显式记录，新 row surfaces 无 row identity duplicate、feature-asof leakage、fold_2024 support usage |
| feature bank v2 | pass | v2 在电子 launch train-scope 下独立构造，不复用 10A status-only artifact |
| fixed probe / candidate freeze | pass | v1/v2 probes 均可训练，v2 path candidates 在 OOF/null/placebo 前冻结 |
| token / manualizability / slice | pass | launch seeds 均为 train-fold quantile bucket formula，无 raw threshold、leaf id、score bucket |
| null / FDR / placebo | fail | launch seeds 不通过 null/FDR；failure secondary stronger，触发 placebo dominance |

这说明本阶段不是 implementation failure，而是 research signal gate failure。换句话说，10C 已经把“是否因为样本太窄、v2 未完成、probe 不可训练、artifact 不完整”这些可能性排除掉，剩下的问题集中在 primitive signal quality 本身。

### 8.2 Feature Bank v2 结果

v2 hygiene 的关键数据：

| fold scope | train rows | v1 features | v2 features | dropped | missing weight before | missing weight after | duplicate clusters before | max family share after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fold_2021 | 643 | 164 | 83 | 81 | 12.85% | 0.14% | 16 | 22.89% |
| fold_2022 | 1033 | 164 | 87 | 77 | 9.43% | 0.99% | 20 | 20.69% |
| fold_2023 | 1425 | 164 | 105 | 59 | 7.75% | 3.76% | 23 | 24.76% |
| global intersection | 1425 reference row | 164 | 81 | 59 | 7.75% | 3.76% | 23 | 24.76% |

drop reason 分布：

| fold | missingness | duplicate/high-corr representative drop | constant/near-constant |
|---|---:|---:|---:|
| fold_2021 | 51 | 29 | 1 |
| fold_2022 | 40 | 36 | 1 |
| fold_2023 | 15 | 43 | 1 |

初步洞察：

- v1 的主要 hygiene 问题不是 family collapse，而是 missingness 与 high-corr redundancy。
- v2 后全部 folds 的 max family share 都低于 25%，明显低于 35% 上限；因此 v2 没有退化成单一 feature family。
- global intersection 留下 81 个 features，仍覆盖 8 个 families；这足够支撑 probe，但也说明后续 formula review 应优先关注“跨 family 但高度相关”的 path 是否只是同一状态的不同表达。

### 8.3 Probe / Path / Seed 宽度

固定 probe 的样本规模：

| task | feature bank | folds | train rows | validation rows | feature count | all pass |
|---|---|---:|---:|---:|---:|---|
| launch_winner | v1_reference | 3 | 3101 | 1140 | 160 | true |
| launch_winner | v2_hygiene | 3 | 3101 | 1140 | 81 | true |
| failure_reject | v1_reference | 3 | 9983 | 3282 | 163 | true |
| failure_reject | v2_hygiene | 3 | 9983 | 3282 | 81 | true |

path / seed 产出：

| surface | launch_winner | failure_reject |
|---|---:|---:|
| raw v2 paths | 1258 | 721 |
| frozen primitive seeds | 14 | 106 |
| OOF support/fold presence pass seeds | 14 | 95 |

初步洞察：

- launch 的 raw paths 更多，但冻结后只剩 14 个 seeds；failure raw paths 更少，却冻结出 106 个 seeds。这说明 candidate budget 与 dedup 后，failure path structure 更分散、更容易形成不同 seed。
- launch seeds 全部通过 support/fold presence，说明“没有足够 OOF support”不是失败原因。
- failure 的 train/validation denominator 显著更大，且 seed 数量远高于 launch；failure dominance 可能部分来自任务定义和样本结构，而不一定是更好的可交易信号。

### 8.4 Launch Seed 的 OOF 表现

launch side 14 个 seeds 的 OOF lift 分布：

| metric | value |
|---|---:|
| seed count | 14 |
| mean lift | 0.985 |
| median lift | 1.007 |
| max lift | 1.283 |
| seeds with lift >= 1.05 | 6 |
| seeds with OOF support/fold presence pass | 14 |
| seeds passing all null/FDR families | 0 |

top launch seeds：

| seed | OOF support | lift | best FDR q | formula |
|---|---:|---:|---:|---|
| E10C_SEED_c645f9790305e9cb | 591 | 1.283 | 0.297 | `atr_like_10 <= train_q80_85 and atr_like_10 >= train_q00_05 and atr20_pct_market_rank <= train_q55_60` |
| E10C_SEED_a802bbc1ee927370 | 614 | 1.236 | 0.297 | `atr20_pct_market_rank <= train_q60_65 and atr_like_10 >= train_q00_05 and atr_like_10 <= train_q80_85` |
| E10C_SEED_40eb71b01d3d40de | 717 | 1.195 | 0.297 | `atr20_pct_market_rank <= train_q70_75 and volatility_return_std_5 between train_q10_15 and train_q85_90` |
| E10C_SEED_86d5dde1c52d602c | 568 | 1.180 | 0.385 | `money_price_coherence_20 <= train_q65_70 and volume_price_divergence_20 <= train_q90_95 and atr20_pct_market_rank <= train_q70_75` |

初步洞察：

- launch top seeds 的形态集中在 volatility/range 不极端、ATR rank 不高、量价背离不过强。这更像“避免过热/过波动的 launch 条件”，而不是强 winner trigger。
- best FDR q 最低也只有 0.297，远高于 0.10 门槛；即使 top lift 看起来有方向，也无法证明它压过 post-selected family 下的 null。
- launch median lift 接近 1.0，说明整体 seed pool 没有稳定上移；少数 high-lift seeds 可能是局部 path artifact 或 support composition，而不是可冻结 primitive。

### 8.5 Failure Diagnostic 与 Placebo Dominance

failure side 的 OOF lift 分布：

| metric | value |
|---|---:|
| seed count | 106 |
| mean lift | 1.043 |
| median lift | 1.042 |
| max lift | 1.414 |
| seeds with lift >= 1.05 | 50 |
| OOF support/fold presence pass seeds | 95 |

FDR / placebo 结果：

| task | null family | FDR pass rows |
|---|---|---:|
| launch_winner | label_permutation_null | 0 |
| launch_winner | instrument_year_block_null | 0 |
| launch_winner | path_structure_null | 0 |
| launch_winner | feature_family_dropout_null | 0 |
| failure_reject | path_structure_null | 24 |
| failure_reject | feature_family_dropout_null | 24 |
| failure_reject | label_permutation_null | 0 |
| failure_reject | instrument_year_block_null | 0 |

placebo guardrail：

```text
primary_pass_seed_count = 0
secondary_failure_pass_seed_count = 24
placebo_or_secondary_dominates_primary = true
```

初步洞察：

- failure side 明显比 launch side 强，但并没有通过全部 null families；它主要压过 path-structure / feature-family-dropout null，没有压过 label permutation 和 instrument-year block null。
- 这意味着 failure path 捕捉到的可能是可解释的状态结构，但这种结构仍可能被 label distribution 或 instrument-year block effects 解释。
- 对 Explore10C 来说，这是一个强阻断：secondary diagnostic 不能反向证明 primary launch seed 成立；相反，它说明当前 path extraction 更容易找到“失败/回避状态”，不是“winner launch primitive”。

### 8.6 Concentration、Slice 与 Manualizability

concentration / manualizability 汇总：

| task | seeds | concentration pass | slice nonzero | manualizability pass |
|---|---:|---:|---:|---:|
| launch_winner | 14 | 8 | all checked slices nonzero | 14 |
| failure_reject | 106 | 81 | all checked slices nonzero | 106 |

launch concentration 的最大值：

| metric | max |
|---|---:|
| top instrument weight share | 0.191 |
| top5 instrument weight share | 0.627 |
| instrument-year HHI | 0.052 |

初步洞察：

- launch 的 concentration 不是主要阻断，但 14 个 seeds 中只有 8 个通过 concentration，说明部分 formula 仍有 top5 instrument concentration 偏高的问题。
- 所有 launch seeds 都 manualizable，且 formula complexity score 均为 6；这支持“可以人工阅读”，但不支持“可以进入 manual review requirement”，因为 null/FDR 和 placebo gate 未过。
- slice 没有 zero-support 问题，说明 seed 不是单一 fold 或单一时间切片伪影；真正问题仍是 null-adjusted signal strength。

### 8.7 方向性判断

本阶段最重要的研究判断：

```text
电子 broad-industry scope 解决了 denominator；
feature bank v2 解决了 hygiene；
fixed probe 解决了 trainability；
但 primitive-quality evidence 没有解决 launch-winner validity。
```

下一步如果继续 Explore10C，而不是进入 Explore10D，应优先考虑：

- 将 launch primitive 的目标从“直接 winner trigger”收紧为“winner 前置风险状态 / avoid-overheated-launch state”，因为 top launch formulas 多是 volatility/range/money coherence 过滤器。
- 分离 failure diagnostic 与 launch primary 的 candidate budget，避免 failure 更宽 denominator 和更多 seed 数量压倒 primary interpretation。
- 对 launch top seeds 做 family-level ablation 或 stricter support-matched null，而不是增加更多 path 搜索；当前失败不是 search space 太小，而是 post-selected null 下不够强。
- 如果要保留 failure side，应把它写成独立的 bad-launch / reject-risk requirement，而不是作为 launch-winner primitive 的支持证据。

## 9. Section 15 直接回答
- 1. Explore10C 通过 `explore10c_explore10b_width_inheritance_gate.csv` 继承 Explore10B 宽度 pass。
- 2. 电子 scope 的后验选择 lineage 已记录，并用 `post_selected_electronics_explore10c` 进入 null/FDR family。
- 3. 新 row surfaces 通过 `explore10c_data_discipline_audit.csv` 审计。
- 4. 10A 的 status-only v2 artifact 没有被当作完成证据；10C 在电子 scope 重新构造 v2。
- 5. v2 相比 v1 的 missingness、duplicate cluster、family coverage 见第 4 节。
- 6. v2 不读取 validation rows、labels、OOF metric 或 fold_2024。
- 7. fixed probe 没有 hyperparameter search、early stopping 或 metric model selection。
- 8. candidate freeze 在 OOF/null/placebo metric 前完成。
- 9. path thresholds 只用 train-fold quantile buckets。
- 10. primitive formula 不含 raw numeric threshold、leaf id、tree id、score bucket 或 model score。
- 11. 通过 OOF/null/FDR 的 seed 数见 recommendation gate。
- 12. failure secondary 若 domination primary，会阻断强于 continue 的 recommendation。
- 13. concentration 与 slice stability 见对应 audit。
- 14. seed 只允许进入 manual review，不是 P1 或交易规则。
- 15. fold_2024、metric、threshold、model、score-bucket selection violation 均由 nonselection audit 检查。
- 16. 是否进入 Explore10D：`False`。
- 17. 本阶段没有回答策略回测、交易可执行性、score bucket 或 P1 有效性问题。

## 10. Recommendation Gate
| width_inheritance_pass   | scope_selection_lineage_pass   | data_discipline_pass   | feature_bank_v2_hygiene_pass   | v2_probe_trainability_pass   | candidate_freeze_pass   | primitive_token_coverage_pass   |   oof_quality_seed_count |   null_pass_seed_count |   fdr_pass_seed_count | candidate_family_fdr_pass   | placebo_or_secondary_dominates_primary   |   concentration_pass_seed_count |   slice_stability_pass_seed_count |   manualizability_pass_seed_count |   fold_2024_support_usage_count |   metric_selection_violation_count |   threshold_selection_violation_count |   model_selection_violation_count |   score_bucket_selection_violation_count | required_artifact_authority_pass   | cache_tracking_pass   |   forbidden_output_violation_count | recommendation                         | recommendation_allowed   | recommendation_reason    | pass   |
|:-------------------------|:-------------------------------|:-----------------------|:-------------------------------|:-----------------------------|:------------------------|:--------------------------------|-------------------------:|-----------------------:|----------------------:|:----------------------------|:-----------------------------------------|--------------------------------:|----------------------------------:|----------------------------------:|--------------------------------:|-----------------------------------:|--------------------------------------:|----------------------------------:|-----------------------------------------:|:-----------------------------------|:----------------------|-----------------------------------:|:---------------------------------------|:-------------------------|:-------------------------|:-------|
| True                     | True                           | True                   | True                           | True                         | True                    | True                            |                       14 |                      0 |                     0 | False                       | True                                     |                               8 |                                14 |                                14 |                               0 |                                  0 |                                     0 |                                 0 |                                        0 | True                               | True                  |                                  0 | continue_explore10c_path_quality_audit | True                     | blocked_by_required_gate | False  |
