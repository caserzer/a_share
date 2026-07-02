# Payoff-state Feature Matrix Refresh Report

## Decision

decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun

18E is matrix construction only. 18E does not train a payoff separability model.
18E does not compute OOS payoff separability support. 18E does not authorize
EP18F oracle-gap bridge, policy, backtest, deployment, production signal, or
trading. Only a future refreshed separability diagnostic can decide whether the
new matrix clears rank IC, monotonicity, baseline, bootstrap, and
search-accounting gates.

## 18D Handoff Replay

| source_artifact                                                  | field_name                         | observed_value                                         | expected_value                                         | status   | blocking_reason   |
|:-----------------------------------------------------------------|:-----------------------------------|:-------------------------------------------------------|:-------------------------------------------------------|:---------|:------------------|
| representation_refresh_decision.csv                              | decision_state                     | 18D_feature_representation_refresh_supported           | 18D_feature_representation_refresh_supported           | pass     |                   |
| representation_refresh_decision.csv                              | next_allowed_requirement           | requirement_18e_payoff_state_feature_matrix_refresh.md | requirement_18e_payoff_state_feature_matrix_refresh.md | pass     |                   |
| representation_refresh_decision.csv                              | all_hard_gates_pass                | True                                                   | True                                                   | pass     |                   |
| representation_refresh_decision.csv                              | upstream_18c_contract_gate         | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | input_artifact_gate                | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | capacity_vs_representation_gate    | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | candidate_lineage_gate             | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | pit_t0_availability_gate           | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | orthogonal_payoff_information_gate | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | feature_family_prioritization_gate | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | search_accounting_gate             | pass                                                   | pass                                                   | pass     |                   |
| representation_refresh_decision.csv                              | recommended_refresh_family_ids     | M1|M3|M5|M2                                            | M1|M3|M5|M2                                            | pass     |                   |
| representation_refresh_decision.csv                              | deferred_family_ids                | M4                                                     | M4                                                     | pass     |                   |
| 18D_payoff_state_feature_representation_diagnostic_manifest.json | decision_state                     | 18D_feature_representation_refresh_supported           | 18D_feature_representation_refresh_supported           | pass     |                   |
| 18D_payoff_state_feature_representation_diagnostic_manifest.json | next_allowed_requirement           | requirement_18e_payoff_state_feature_matrix_refresh.md | requirement_18e_payoff_state_feature_matrix_refresh.md | pass     |                   |
| 18D_payoff_state_feature_representation_diagnostic_manifest.json | all_hard_gates_pass                | True                                                   | True                                                   | pass     |                   |
| 18D_payoff_state_feature_representation_diagnostic_manifest.json | recommended_refresh_family_ids     | M1|M3|M5|M2                                            | M1|M3|M5|M2                                            | pass     |                   |
| 18D_payoff_state_feature_representation_diagnostic_manifest.json | deferred_family_ids                | M4                                                     | M4                                                     | pass     |                   |
| representation_refresh_decision.csv                              | entry_policy_authorized            | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | exit_policy_authorized             | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | holding_policy_authorized          | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | portfolio_backtest_authorized      | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | model_deployment_authorized        | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | production_signal_authorized       | False                                                  | False                                                  | pass     |                   |
| representation_refresh_decision.csv                              | live_trading_authorized            | False                                                  | False                                                  | pass     |                   |

Candidate replay summary:

| expected_18e_role   |   candidate_n |
|:--------------------|--------------:|
| appendix_only       |            14 |
| deferred            |             1 |
| primary_refresh     |            26 |

## Denominator And Neutral Preservation

refreshed_matrix_row_n = 23405
neutral_row_n = 6066
neutral_rows_dropped = False
identity_key_join_used = True
split_join_key_used = False
split_mismatch_n = 0

## Source Audit

|   qfq_instrument_path_coverage_rate |   qfq_matrix_row_path_coverage_rate | amount_proxy_source   |
|------------------------------------:|------------------------------------:|:----------------------|
|                                   1 |                                   1 | money                 |

## Matrix Schema

| column_role         |   column_n |
|:--------------------|-----------:|
| model_ready_feature |         49 |
| raw_feature         |         49 |
| row_key             |          9 |
| split_metadata      |          1 |
| target              |         19 |

Primary raw feature count = 49
Primary model-ready feature count = 49

## Missingness

Worst total finite-rate rows:

| feature_name                       | feature_family_id   |   finite_rate | feature_complete_rate_gate   |
|:-----------------------------------|:--------------------|--------------:|:-----------------------------|
| m1_path_transition_entropy_episode | M1                  |      0.906174 | pass                         |
| m1_failed_repair_count_low_to_t0   | M1                  |      0.906174 | pass                         |
| m3_failed_breakout_count_pre_t0    | M3                  |      0.906174 | pass                         |
| m1_repair_path_efficiency_episode  | M1                  |      0.937877 | pass                         |
| m3_upside_downside_room_ratio_t0   | M3                  |      0.960094 | pass                         |
| m3_upper_shadow_pressure_share_20  | M3                  |      0.961632 | pass                         |
| m1_close_location_episode_range    | M1                  |      0.961675 | pass                         |
| m1_close_location_trailing60_range | M1                  |      0.961675 | pass                         |
| m3_asymmetric_range_position_t0    | M3                  |      0.961675 | pass                         |
| m5_episode_age_to_t0               | M5                  |      0.961675 | pass                         |
| m5_bars_since_episode_low          | M5                  |      0.961675 | pass                         |
| m5_bars_since_episode_high_t0      | M5                  |      0.961675 | pass                         |

## Feature Family Coverage

| feature_family_id   | family_role           |   expected_primary_feature_n |   observed_primary_feature_n |   observed_model_ready_feature_n |   finite_train_rate_min |   finite_all_rate_min | family_coverage_status   | blocking_reason        |
|:--------------------|:----------------------|-----------------------------:|-----------------------------:|---------------------------------:|------------------------:|----------------------:|:-------------------------|:-----------------------|
| F1                  | existing_18b_retained |                            7 |                            7 |                                7 |                1        |              1        | pass                     |                        |
| F2                  | existing_18b_retained |                            5 |                            5 |                                5 |                1        |              1        | pass                     |                        |
| F3                  | existing_18b_retained |                            2 |                            2 |                                2 |                1        |              1        | pass                     |                        |
| F4                  | existing_18b_retained |                            5 |                            5 |                                5 |                1        |              1        | pass                     |                        |
| F5                  | existing_18b_retained |                            4 |                            4 |                                4 |                1        |              1        | pass                     |                        |
| M1                  | primary_refresh       |                            8 |                            8 |                                8 |                0.916572 |              0.906174 | pass                     |                        |
| M3                  | primary_refresh       |                            5 |                            5 |                                5 |                0.916572 |              0.906174 | pass                     |                        |
| M5                  | primary_refresh       |                            6 |                            6 |                                6 |                0.967795 |              0.961675 | pass                     |                        |
| M2                  | primary_refresh       |                            7 |                            7 |                                7 |                0.967795 |              0.961675 | pass                     |                        |
| M4                  | deferred              |                            0 |                            0 |                                0 |              nan        |            nan        | pass                     | m4_deferred_by_default |

## Train-only Preprocessing

preprocessing_feature_n = 49
fit_split_values = train
preprocessing_uses_target_columns = False
split_local_imputation_used = False
split_local_scaling_used = False

## Forbidden Feature And Search Accounting

forbidden_gate_fail_n = 0
search_accounting_gate = pass

## Handoff

If and only if this decision remains
18E_payoff_state_feature_matrix_refresh_supported, a refreshed 18C-style
separability diagnostic may use:

outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_decision.csv
outputs/manifests/18E_payoff_state_feature_matrix_refresh_manifest.json
outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
