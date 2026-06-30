# Oracle Denominator Contract

run_id = 17A_oracle_replay_contract_preflight

Primary denominator:

```text
EP16 up50pct / h20 / full-horizon / non-overlap continuation decision states
```

| oracle_id   | oracle_name                         | primary_denominator_type               |   expected_primary_row_count_train |   expected_primary_row_count_robustness |   expected_primary_row_count_validation | neutral_stress_required   | appendix_only_allowed   |
|:------------|:------------------------------------|:---------------------------------------|-----------------------------------:|----------------------------------------:|----------------------------------------:|:--------------------------|:------------------------|
| O0          | No Oracle Baseline                  | labelable_full                         |                              20245 |                                    2496 |                                     664 | False                     | False                   |
| O1          | Perfect Negative Oracle             | binary_primary                         |                              14962 |                                    1872 |                                     505 | True                      | False                   |
| O2          | Perfect Deep Drawdown Oracle        | labelable_full                         |                              20245 |                                    2496 |                                     664 | False                     | False                   |
| O3          | Perfect False-repair Oracle         | appendix_only_if_join_incomplete       |                              20245 |                                    2496 |                                     664 | False                     | True                    |
| O4          | Positive Preservation Oracle        | binary_primary                         |                              14962 |                                    1872 |                                     505 | True                      | False                   |
| O5          | Perfect Utility Oracle              | labelable_full                         |                              20245 |                                    2496 |                                     664 | False                     | False                   |
| O6          | Capacity-constrained Utility Oracle | labelable_full_if_capacity_gate_passes |                              20245 |                                    2496 |                                     664 | False                     | True                    |
| O7          | Delayed Utility Oracle              | labelable_full                         |                              20245 |                                    2496 |                                     664 | False                     | False                   |
| L0          | 16D Learned-score Reference         | binary_fit_labelable_replay            |                              14962 |                                    1872 |                                     505 | False                     | False                   |
