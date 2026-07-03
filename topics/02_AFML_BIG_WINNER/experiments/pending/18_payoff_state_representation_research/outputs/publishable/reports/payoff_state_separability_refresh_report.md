# Refreshed 18C Payoff-state Separability Diagnostic Report

## Decision

decision_state = 18C_refresh_upstream_18e_contract_blocked
next_allowed_requirement = none
next_allowed_requirement_scope = none

This refreshed 18C runner is fail-closed. It does not authorize policy,
backtest, deployment, production signal, or live trading.

## Missing Inputs

| artifact_key                | blocking_reason                                                           |
|:----------------------------|:--------------------------------------------------------------------------|
| eighteen_e_refreshed_matrix | missing;missing_local_cache_refreshed_matrix;rerun_18e_full_to_regenerate |

## 18E Handoff

| contract_check_id                         | observed_value                                          | expected_value                                          | upstream_18e_contract_gate   | blocking_reason               |
|:------------------------------------------|:--------------------------------------------------------|:--------------------------------------------------------|:-----------------------------|:------------------------------|
| decision_state                            | 18E_payoff_state_feature_matrix_refresh_supported       | 18E_payoff_state_feature_matrix_refresh_supported       | pass                         |                               |
| next_allowed_requirement                  | requirement_18c_payoff_state_separability_diagnostic.md | requirement_18c_payoff_state_separability_diagnostic.md | pass                         |                               |
| next_allowed_requirement_scope            | refreshed_matrix_rerun                                  | refreshed_matrix_rerun                                  | pass                         |                               |
| all_hard_gates_pass                       | True                                                    | True                                                    | pass                         |                               |
| upstream_18d_contract_gate                | pass                                                    | pass                                                    | pass                         |                               |
| input_artifact_gate                       | pass                                                    | pass                                                    | pass                         |                               |
| feature_family_recommendation_replay_gate | pass                                                    | pass                                                    | pass                         |                               |
| refreshed_feature_source_gate             | pass                                                    | pass                                                    | pass                         |                               |
| refreshed_feature_formula_gate            | pass                                                    | pass                                                    | pass                         |                               |
| refreshed_feature_lineage_gate            | pass                                                    | pass                                                    | pass                         |                               |
| pit_t0_availability_gate                  | pass                                                    | pass                                                    | pass                         |                               |
| target_binding_gate                       | pass                                                    | pass                                                    | pass                         |                               |
| feature_matrix_schema_gate                | pass                                                    | pass                                                    | pass                         |                               |
| feature_complete_rate_gate                | pass                                                    | pass                                                    | pass                         |                               |
| feature_family_coverage_gate              | pass                                                    | pass                                                    | pass                         |                               |
| train_only_preprocessing_gate             | pass                                                    | pass                                                    | pass                         |                               |
| forbidden_feature_gate                    | pass                                                    | pass                                                    | pass                         |                               |
| search_accounting_gate                    | pass                                                    | pass                                                    | pass                         |                               |
| entry_policy_authorized                   | False                                                   | False                                                   | pass                         |                               |
| exit_policy_authorized                    | False                                                   | False                                                   | pass                         |                               |
| holding_policy_authorized                 | False                                                   | False                                                   | pass                         |                               |
| portfolio_backtest_authorized             | False                                                   | False                                                   | pass                         |                               |
| model_deployment_authorized               | False                                                   | False                                                   | pass                         |                               |
| production_signal_authorized              | False                                                   | False                                                   | pass                         |                               |
| live_trading_authorized                   | False                                                   | False                                                   | pass                         |                               |
| all_required_18e_artifacts_present        | 1                                                       | 0                                                       | fail                         | missing_required_18e_artifact |

## Matrix Contract Replay

| check_id                      | expected_value   | observed_value   | matrix_contract_replay_gate   | blocking_reason                                                   |
|:------------------------------|:-----------------|:-----------------|:------------------------------|:------------------------------------------------------------------|
| matrix_file_exists            | present          | missing          | fail                          | missing_local_cache_refreshed_matrix;rerun_18e_full_to_regenerate |
| primary_model_ready_feature_n | 49               | 49               | pass                          |                                                                   |
| target_column_n               | 19               | 19               | pass                          |                                                                   |
| manifest_matrix_row_n         | 23405            | 23405            | pass                          |                                                                   |
