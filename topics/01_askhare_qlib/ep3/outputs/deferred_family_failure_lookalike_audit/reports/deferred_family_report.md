# EP3 Deferred-Family Failure-Lookalike Audit

## Final Decision

`stop_deferred_family`

## Upstream Problem Chain

EP3 P0 stopped A/C after trigger, lift, robustness, and tail failures. P0.5 confirmed A/C should stop and authorized this deferred-family requirement.

## Trigger Summary

| split      |   event_count |   canonical_launch_episode_count |   trigger_rate_per_launch_episode |
|:-----------|--------------:|---------------------------------:|----------------------------------:|
| train      |           253 |                             1153 |                          0.219428 |
| validation |            99 |                              536 |                          0.184701 |
| robustness |           154 |                              775 |                          0.19871  |

## Matched Lift Summary

| split      |   anchor_event_count |   baseline_event_count |   mean_diff_vs_baseline |   p05_diff_vs_baseline |   mae_worsening_vs_baseline |
|:-----------|---------------------:|-----------------------:|------------------------:|-----------------------:|----------------------------:|
| train      |                  253 |                    250 |              0.00476689 |             0.0107754  |                 0.000962113 |
| validation |                   99 |                     98 |             -0.020626   |            -0.00200166 |                -0.00681459  |
| robustness |                  154 |                    154 |             -0.0113042  |            -0.0246307  |                -0.00631879  |

## Gate Summary

| gate_name                                     |   gate_value |   threshold | comparison   | gate_passed   | failure_status_if_failed       |
|:----------------------------------------------|-------------:|------------:|:-------------|:--------------|:-------------------------------|
| validation_trigger_rate                       |   0.184701   |   0.1       | >=           | True          |                                |
| validation_unique_instrument_year_count       |  86          |  25         | >=           | True          |                                |
| validation_h20_mean_diff_vs_matched_delay     |  -0.020626   |   0         | >            | False         | failed_gate                    |
| validation_h20_p05_diff_vs_matched_delay      |  -0.00200166 |  -0.003     | >=           | True          |                                |
| validation_h20_mae_worsening_vs_matched_delay |  -0.00681459 |   0.005     | <=           | True          |                                |
| validation_instrument_year_positive_rate_diff |  -0.0581395  |   0         | >=           | False         | failed_gate                    |
| robustness_h20_mean_diff_vs_matched_delay     |  -0.0113042  |  -0.001     | >=           | False         | failed_gate                    |
| robustness_h20_p05_diff_vs_matched_delay      |  -0.0246307  |  -0.005     | >=           | False         | failed_gate                    |
| robustness_trigger_not_collapsed              |   0.19871    |   0.0923507 | >=           | True          |                                |
| persistent_failure_validation_tail_share      |   0.0277778  |   0.5       | >=           | False         | failed_formula_refinement_gate |
| persistent_failure_robustness_tail_share      |   0.0243902  |   0.3       | >=           | False         | failed_formula_refinement_gate |

## Validator Status

`validation_status = passed`

`validation_failures = []`
