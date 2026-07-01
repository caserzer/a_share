# Payoff-state Contract Preflight Report

## Decision

decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md

18A freezes targets and contracts only.
18A does not prove payoff-state separability.
18A does not authorize policy, backtest, deployment, or trading.

## Upstream Authorization

EP17D authorization replay passed with final decision `oracle_payoff_state_research_allowed`.

## Denominator Reconciliation

| split_bucket   |   labelable_step_n |   binary_step_n |   neutral_step_n |   expected_labelable_step_n |   expected_binary_step_n |   expected_neutral_step_n | denominator_reconciliation_gate   | blocking_reason   |
|:---------------|-------------------:|----------------:|-----------------:|----------------------------:|-------------------------:|--------------------------:|:----------------------------------|:------------------|
| train          |              20245 |           14962 |             5283 |                       20245 |                    14962 |                      5283 | pass                              |                   |
| robustness     |               2496 |            1872 |              624 |                        2496 |                     1872 |                       624 | pass                              |                   |
| validation     |                664 |             505 |              159 |                         664 |                      505 |                       159 | pass                              |                   |

## Oracle Reference Denominators

| oracle_reference_id                 | source_denominator_type   |   observed_step_n |   mean_incremental_return | allowed_bridge_denominator   | direct_comparison_allowed   |
|:------------------------------------|:--------------------------|------------------:|--------------------------:|:-----------------------------|:----------------------------|
| O5_perfect_utility_primary          | labelable_full            |              2496 |                 0.0294674 | labelable_full               | True                        |
| O2_dd_10pct_primary                 | labelable_full            |              2496 |                 0.0185108 | labelable_full               | True                        |
| O4_label_positive_primary           | binary_primary            |              1872 |                 0.0246811 | binary_primary               | False                       |
| 17D_mixed_o5_vs_best_label_path_gap | mixed_diagnostic_only     |               nan |               nan         | none                         | False                       |

The 17D mixed O5-vs-O4 gap is diagnostic-only and must not be used as a learned-score bridge target.

## O5 Incremental Identity

o5_incremental = max(0, defend_value - continue_value)

| split_bucket   |   cost_bps |   q_defend |   observed_step_n |   defended_step_n |   aggregate_o5_incremental_replay |   source_mean_incremental_return |   max_abs_diff |   formula_mismatch_n | o5_incremental_definition_replay_gate   | blocking_reason   |
|:---------------|-----------:|-----------:|------------------:|------------------:|----------------------------------:|---------------------------------:|---------------:|---------------------:|:----------------------------------------|:------------------|
| train          |         50 |          0 |             20245 |              9409 |                         0.0355625 |                        0.0355625 |    4.16334e-17 |                    0 | pass                                    |                   |
| robustness     |         50 |          0 |              2496 |              1056 |                         0.0294674 |                        0.0294674 |    5.55112e-17 |                    0 | pass                                    |                   |
| validation     |         50 |          0 |               664 |               319 |                         0.0391385 |                        0.0391385 |    4.85723e-17 |                    0 | pass                                    |                   |

## Payoff Cutoff Freeze

| threshold_id             |   train_absolute_payoff_cutoff |   train_row_count | split_local_recompute_used   | train_frozen_cutoff_gate   |
|:-------------------------|-------------------------------:|------------------:|:-----------------------------|:---------------------------|
| high_upside_top30_stress |                       0.059633 |             20245 | False                        | pass                       |
| high_upside_top20_stress |                       0.101229 |             20245 | False                        | pass                       |
| high_upside_top10_stress |                       0.172107 |             20245 | False                        | pass                       |

## Neutral Preservation

| split_bucket   |   labelable_step_n |   neutral_step_n | neutral_preserved_in_labelable_full   | neutral_reclassified_as_positive_or_negative   | neutral_preservation_gate   | blocking_reason   |
|:---------------|-------------------:|-----------------:|:--------------------------------------|:-----------------------------------------------|:----------------------------|:------------------|
| train          |              20245 |             5283 | True                                  | False                                          | pass                        |                   |
| robustness     |               2496 |              624 | True                                  | False                                          | pass                        |                   |
| validation     |                664 |              159 | True                                  | False                                          | pass                        |                   |

## Feature Source Inventory

| feature_family_id   | feature_family_name                        | pit_available_status   | t0_available_status   | primary_allowed   | appendix_only   |
|:--------------------|:-------------------------------------------|:-----------------------|:----------------------|:------------------|:----------------|
| F1                  | continuation strength / repair persistence | pass                   | pass                  | True              | False           |
| F2                  | participation / sponsorship                | pass                   | pass                  | True              | False           |
| F3                  | cross-sectional leadership                 | pass                   | pass                  | True              | False           |
| F4                  | path-risk decoupling                       | pass                   | pass                  | True              | False           |
| F5                  | regime / board / market context            | pass                   | pass                  | True              | False           |
| F6                  | delayed observed-state appendix            | appendix_only          | not_t0_available      | False             | True            |
| F7                  | external feature families                  | unavailable            | unavailable           | False             | False           |

## Search Accounting

No model training, refit, feature selection, target selection from robustness/validation, separability metric, policy, backtest, deployment, production signal, or live trading authorization was performed.
