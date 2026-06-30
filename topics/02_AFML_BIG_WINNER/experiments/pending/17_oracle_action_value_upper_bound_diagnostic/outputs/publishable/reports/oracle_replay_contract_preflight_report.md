# 17A Oracle Replay Contract Preflight Report

## 1. Decision

```text
decision_state = EP17A_oracle_replay_contract_ready
next_allowed_requirement = requirement_17b_oracle_ladder_replay.md
blocking_reason = none
```

17A 只冻结 denominator / action / replay contract，不解释 oracle value，不授权 entry / exit / holding / sizing / portfolio / deployment / live trading。

## 2. Upstream Closure

| source_phase_id   | decision_state                                   | next_allowed_requirement   | continuation_as_action_mainline_closed   | required_state_status   | blocking_reason   |
|:------------------|:-------------------------------------------------|:---------------------------|:-----------------------------------------|:------------------------|:------------------|
| topic_conclusion  |                                                  |                            | True                                     | pass                    |                   |
| 16E               | 16E_utility_diagnostic_not_supported             | none                       | True                                     | pass                    |                   |
| 16E-postmortem    | 16E_postmortem_mainline_closed_no_path_supported | none                       | True                                     | pass                    |                   |
| 16X               | 16X_payoff_precheck_not_supported                | none                       | True                                     | pass                    |                   |

## 3. Denominator Reconciliation

| split_bucket   |   expected_labelable_step_n |   observed_labelable_step_n |   expected_binary_step_n |   observed_binary_step_n |   expected_neutral_step_n |   observed_neutral_step_n | denominator_reconciliation_gate   |
|:---------------|----------------------------:|----------------------------:|-------------------------:|-------------------------:|--------------------------:|--------------------------:|:----------------------------------|
| train          |                       20245 |                       20245 |                    14962 |                    14962 |                      5283 |                      5283 | pass                              |
| robustness     |                        2496 |                        2496 |                     1872 |                     1872 |                       624 |                       624 | pass                              |
| validation     |                         664 |                         664 |                      505 |                      505 |                       159 |                       159 | pass                              |

## 4. Learned-score Reference Replay

| split_bucket   |   expected_binary_step_n |   observed_binary_step_n |   expected_defended_binary_step_n |   observed_defended_binary_step_n |   expected_defended_negative_n |   observed_defended_negative_n | learned_score_reference_gate   |
|:---------------|-------------------------:|-------------------------:|----------------------------------:|----------------------------------:|-------------------------------:|-------------------------------:|:-------------------------------|
| train          |                    14962 |                    14962 |                              4489 |                              4489 |                           2299 |                           2299 | pass                           |
| robustness     |                     1872 |                     1872 |                               397 |                               397 |                            196 |                            196 | pass                           |
| validation     |                      505 |                      505 |                               158 |                               158 |                             81 |                             81 | pass                           |

## 5. EP16 Replay Sanity

| sanity_check_id                                                | split_bucket   |   cost_bps |   expected_value |   observed_value |    abs_diff |   tolerance | sanity_status   |
|:---------------------------------------------------------------|:---------------|-----------:|-----------------:|-----------------:|------------:|------------:|:----------------|
| 16d_threshold_value                                            | all            |        nan |       0.457071   |      0.457071    | 0           |       1e-12 | pass            |
| 16d_binary_confusion_counts                                    | train          |        nan |       0          |      0           | 0           |       0     | pass            |
| 16e_labelable_denominator_counts                               | train          |         50 |   20245          |  20245           | 0           |       0     | pass            |
| 16d_binary_confusion_counts                                    | robustness     |        nan |       0          |      0           | 0           |       0     | pass            |
| 16e_labelable_denominator_counts                               | robustness     |         50 |    2496          |   2496           | 0           |       0     | pass            |
| 16d_binary_confusion_counts                                    | validation     |        nan |       0          |      0           | 0           |       0     | pass            |
| 16e_labelable_denominator_counts                               | validation     |         50 |     664          |    664           | 0           |       0     | pass            |
| 16e_primary_50bps_robustness_mean_incremental_return           | robustness     |         50 |      -0.00552914 |     -0.00552914  | 6.93889e-17 |       1e-09 | pass            |
| 16e_primary_robustness_defended_negative_drawdown_avoided_mean | robustness     |         50 |       0.164024   |      0.164024    | 0           |       1e-09 | pass            |
| 16e_six_cell_incremental_sum_identity                          | train          |         50 |       0          |      7.10543e-15 | 7.10543e-15 |       1e-09 | pass            |
| 16e_six_cell_incremental_sum_identity                          | robustness     |         50 |       0          |      0           | 0           |       1e-09 | pass            |
| 16e_six_cell_incremental_sum_identity                          | validation     |         50 |       0          |      2.66454e-15 | 2.66454e-15 |       1e-09 | pass            |

## 6. Capacity Status

| capacity_reconstruction_gate   | o6_status_for_17b         | capacity_cap_config_frozen   | turnover_cost_config_frozen   |
|:-------------------------------|:--------------------------|:-----------------------------|:------------------------------|
| appendix_only                  | appendix_only_nonblocking | True                         | True                          |

## 7. Search Accounting

| no_model_training   | no_model_refit   | no_survival_threshold_tuning   | no_validation_selection   | no_payoff_label_redesign   | no_oracle_value_interpretation   | search_accounting_gate   |
|:--------------------|:-----------------|:-------------------------------|:--------------------------|:---------------------------|:---------------------------------|:-------------------------|
| True                | True             | True                           | True                      | True                       | True                             | pass                     |
