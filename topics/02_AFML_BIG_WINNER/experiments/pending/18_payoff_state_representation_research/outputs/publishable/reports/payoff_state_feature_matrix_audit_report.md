# Payoff-state Feature Matrix Audit Report

## Decision

decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md

18B materializes and audits the feature matrix only.
18B does not prove payoff-state separability.
18B does not select features from target outcomes.
18B does not authorize policy, backtest, deployment, or trading.

## 18A Handoff

| contract_check_id                     | observed_value                                       | expected_value                                       | upstream_18a_contract_gate   |
|:--------------------------------------|:-----------------------------------------------------|:-----------------------------------------------------|:-----------------------------|
| decision_state                        | 18A_payoff_state_contract_ready                      | 18A_payoff_state_contract_ready                      | pass                         |
| next_allowed_requirement              | requirement_18b_payoff_state_feature_matrix_audit.md | requirement_18b_payoff_state_feature_matrix_audit.md | pass                         |
| all_hard_gates_pass                   | True                                                 | True                                                 | pass                         |
| input_artifact_gate                   | pass                                                 | pass                                                 | pass                         |
| denominator_reconciliation_gate       | pass                                                 | pass                                                 | pass                         |
| target_lineage_gate                   | pass                                                 | pass                                                 | pass                         |
| o5_incremental_definition_replay_gate | pass                                                 | pass                                                 | pass                         |
| train_frozen_cutoff_gate              | pass                                                 | pass                                                 | pass                         |
| neutral_preservation_gate             | pass                                                 | pass                                                 | pass                         |
| feature_source_pit_gate               | pass                                                 | pass                                                 | pass                         |
| leakage_forbidden_column_gate         | pass                                                 | pass                                                 | pass                         |
| search_accounting_gate                | pass                                                 | pass                                                 | pass                         |
| entry_policy_authorized               | False                                                | False                                                | pass                         |
| exit_policy_authorized                | False                                                | False                                                | pass                         |
| holding_policy_authorized             | False                                                | False                                                | pass                         |
| portfolio_backtest_authorized         | False                                                | False                                                | pass                         |
| model_deployment_authorized           | False                                                | False                                                | pass                         |
| production_signal_authorized          | False                                                | False                                                | pass                         |
| live_trading_authorized               | False                                                | False                                                | pass                         |

## Feature-target Binding

bound_matrix_row_n = 23405
split_mismatch_n = 0
identity_key_join_used = True
split_join_key_used = False

| binding_check_id                    | target_filter_predicate                                                                                                |   target_filter_row_n |   target_filter_identity_key_n | target_filter_split_counts                       | target_label_rule_status_unique   | identity_key_columns                                                                                                  | split_column         |   feature_row_n |   target_row_n |   feature_identity_key_n |   target_identity_key_n |   bound_matrix_row_n | identity_key_join_used   | split_join_key_used   |   feature_duplicate_key_n |   target_duplicate_key_n |   unmatched_feature_key_n |   unmatched_target_key_n |   split_mismatch_n |   feature_missing_split_n |   target_missing_split_n | feature_split_values        | target_split_values         | split_counts_match_18a   | split_allowed_values_gate   |   labelable_step_n_train |   labelable_step_n_robustness |   labelable_step_n_validation |   neutral_step_n_train |   neutral_step_n_robustness |   neutral_step_n_validation | feature_target_binding_gate   | blocking_reason   |
|:------------------------------------|:-----------------------------------------------------------------------------------------------------------------------|----------------------:|-------------------------------:|:-------------------------------------------------|:----------------------------------|:----------------------------------------------------------------------------------------------------------------------|:---------------------|----------------:|---------------:|-------------------------:|------------------------:|---------------------:|:-------------------------|:----------------------|--------------------------:|-------------------------:|--------------------------:|-------------------------:|-------------------:|--------------------------:|-------------------------:|:----------------------------|:----------------------------|:-------------------------|:----------------------------|-------------------------:|------------------------------:|------------------------------:|-----------------------:|----------------------------:|----------------------------:|:------------------------------|:------------------|
| identity_key_target_feature_binding | label_id=continuation_survival_h20_no_deep_drawdown; threshold_id=up50pct; horizon_sessions=20; label_rule_status=pass |                 23405 |                          23405 | train 20,245 / robustness 2,496 / validation 664 | pass                              | step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date | cluster_split_bucket |           23405 |          23405 |                    23405 |                   23405 |                23405 | True                     | False                 |                         0 |                        0 |                         0 |                        0 |                  0 |                         0 |                        0 | robustness|train|validation | robustness|train|validation | True                     | pass                        |                    20245 |                          2496 |                           664 |                   5283 |                         624 |                         159 | pass                          |                   |

## Feature Matrix Schema

| column_role         |   column_n |
|:--------------------|-----------:|
| model_ready_feature |         23 |
| raw_feature         |         23 |
| row_key             |          9 |
| split_metadata      |          1 |
| target              |         19 |

Primary raw feature count = 23
Primary model-ready feature count = 23

## Missingness and Completeness

Worst finite-rate rows:

| feature_name             | feature_family_id   | split_bucket   |   row_n |   finite_n |   missing_n |   finite_rate |   expected_min_finite_rate | feature_complete_rate_gate   | blocking_reason   |
|:-------------------------|:--------------------|:---------------|--------:|-----------:|------------:|--------------:|---------------------------:|:-----------------------------|:------------------|
| intraday_range_20d_mean  | F4                  | validation     |     664 |        664 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_chinext     | F5                  | train          |   20245 |      20245 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_chinext     | F5                  | robustness     |    2496 |       2496 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_chinext     | F5                  | validation     |     664 |        664 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_main_board  | F5                  | train          |   20245 |      20245 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_main_board  | F5                  | robustness     |    2496 |       2496 |           0 |             1 |                       0.99 | pass                         |                   |
| board_bucket_main_board  | F5                  | validation     |     664 |        664 |           0 |             1 |                       0.99 | pass                         |                   |
| log_total_market_cap_cny | F5                  | train          |   20245 |      20245 |           0 |             1 |                       0.99 | pass                         |                   |
| log_total_market_cap_cny | F5                  | robustness     |    2496 |       2496 |           0 |             1 |                       0.99 | pass                         |                   |
| ret_5d                   | F1                  | robustness     |    2496 |       2496 |           0 |             1 |                       0.99 | pass                         |                   |

Row completeness:

| split_bucket   |   row_n |   primary_raw_feature_n |   primary_model_ready_feature_n |   row_complete_n |   matrix_row_complete_rate |   expected_min_matrix_row_complete_rate | row_drop_used_to_improve_complete_rate   | feature_complete_rate_gate   | blocking_reason   |
|:---------------|--------:|------------------------:|--------------------------------:|-----------------:|---------------------------:|----------------------------------------:|:-----------------------------------------|:-----------------------------|:------------------|
| train          |   20245 |                      23 |                              23 |            20245 |                          1 |                                    0.99 | False                                    | pass                         |                   |
| robustness     |    2496 |                      23 |                              23 |             2496 |                          1 |                                    0.99 | False                                    | pass                         |                   |
| validation     |     664 |                      23 |                              23 |              664 |                          1 |                                    0.99 | False                                    | pass                         |                   |
| total          |   23405 |                      23 |                              23 |            23405 |                          1 |                                    0.99 | False                                    | pass                         |                   |

## Feature Family Coverage

| feature_family_id   | feature_family_name                        |   expected_feature_n |   observed_raw_feature_n |   observed_model_ready_feature_n | pit_available_status   | t0_available_status   |   raw_feature_missing_n |   model_ready_feature_missing_n | primary_allowed   | appendix_only   | feature_family_coverage_gate   | blocking_reason   |
|:--------------------|:-------------------------------------------|---------------------:|-------------------------:|---------------------------------:|:-----------------------|:----------------------|------------------------:|--------------------------------:|:------------------|:----------------|:-------------------------------|:------------------|
| F1                  | continuation strength / repair persistence |                    7 |                        7 |                                7 | pass                   | pass                  |                       0 |                               0 | True              | False           | pass                           |                   |
| F2                  | participation / sponsorship                |                    5 |                        5 |                                5 | pass                   | pass                  |                       0 |                               0 | True              | False           | pass                           |                   |
| F3                  | cross-sectional leadership                 |                    2 |                        2 |                                2 | pass                   | pass                  |                       0 |                               0 | True              | False           | pass                           |                   |
| F4                  | path-risk decoupling                       |                    5 |                        5 |                                5 | pass                   | pass                  |                       0 |                               0 | True              | False           | pass                           |                   |
| F5                  | regime / board / market context            |                    4 |                        4 |                                4 | pass                   | pass                  |                       0 |                               0 | True              | False           | pass                           |                   |
| F6                  | delayed observed-state appendix            |                    0 |                        0 |                                0 | appendix_only          | not_t0_available      |                       0 |                               0 | False             | True            | pass                           |                   |
| F7                  | external feature families                  |                    0 |                        0 |                                0 | unavailable            | unavailable           |                       0 |                               0 | False             | False           | pass                           |                   |

## Split Drift Readout

Split drift is diagnostic-only and did not remove features.

| split_comparison    |   feature_readout_n |
|:--------------------|--------------------:|
| train_vs_robustness |                  23 |
| train_vs_validation |                  23 |

## Search Accounting

No model training, refit, feature selection, target selection from robustness/validation, separability metric, policy utility, backtest, deployment, production signal, or live trading authorization was performed.
