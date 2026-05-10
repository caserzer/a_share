# EP3 P0.5 Anchor Failure Diagnostic Report

## Upstream Authority And Reproduction Status

- Authority failures: 0
- Upstream reproduction rows: 2; failed rows: 0

## Trigger Denominator Reconciliation

- Denominator reconciliation failures: 0

## Trigger-Budget Decomposition

| split      | anchor_family_id           |   anchor_trigger_count |   ep2_launch_episode_count |   trigger_rate_per_launch_episode | trigger_count_reproduction_status   |
|:-----------|:---------------------------|-----------------------:|---------------------------:|----------------------------------:|:------------------------------------|
| train      | pullback_hold_restrengthen |                    181 |                       1153 |                         0.156982  | passed                              |
| train      | second_breakout            |                    184 |                       1153 |                         0.159584  | passed                              |
| validation | pullback_hold_restrengthen |                     77 |                        536 |                         0.143657  | passed                              |
| validation | second_breakout            |                     64 |                        536 |                         0.119403  | passed                              |
| robustness | pullback_hold_restrengthen |                     57 |                        775 |                         0.0735484 | passed                              |
| robustness | second_breakout            |                     58 |                        775 |                         0.0748387 | passed                              |

## Matched-Lift Decomposition

| split      | anchor_family_id           |   anchor_event_count |   baseline_event_count |   mean_diff_vs_baseline |   p05_diff_vs_baseline | interpretation_status   |
|:-----------|:---------------------------|---------------------:|-----------------------:|------------------------:|-----------------------:|:------------------------|
| train      | pullback_hold_restrengthen |                  179 |                    179 |              0.00193843 |             0.00646109 | interpretable           |
| train      | second_breakout            |                  181 |                    181 |             -0.00155391 |            -0.0392998  | interpretable           |
| validation | pullback_hold_restrengthen |                   73 |                     73 |             -0.0208543  |            -0.0157375  | interpretable           |
| validation | second_breakout            |                   63 |                     63 |             -0.00765649 |            -0.0409269  | interpretable           |
| robustness | pullback_hold_restrengthen |                   57 |                     57 |              0.016085   |            -0.00522826 | interpretable           |
| robustness | second_breakout            |                   57 |                     57 |             -0.0100071  |            -0.0436761  | interpretable           |

## H10/H60 Sensitivity Audit

Sensitivity rows are report-only and are not used in hypothesis or stop/continue decisions.

## Tail And Concentration Findings

Tail and concentration findings are material only through the H20 tail report and hypothesis audit.

## Hypothesis Audit

| anchor_family_id           | hypothesis_id                                    | support_status   | support_rule_status   | primary_evidence_report                     |
|:---------------------------|:-------------------------------------------------|:-----------------|:----------------------|:--------------------------------------------|
| pullback_hold_restrengthen | h1_formula_too_narrow                            | rejected         | failed                | reports/p0_5_matched_lift_decomposition.csv |
| pullback_hold_restrengthen | h2_window_position_problem                       | rejected         | failed                | reports/p0_5_matched_lift_decomposition.csv |
| pullback_hold_restrengthen | h3_ep2_reference_pollution                       | rejected         | failed                | reports/p0_5_trigger_decomposition.csv      |
| pullback_hold_restrengthen | h4_matched_baseline_too_strong_or_anchor_no_lift | supported        | passed                | reports/p0_5_matched_lift_decomposition.csv |
| pullback_hold_restrengthen | h5_tail_risk_not_trigger_rate_is_core_failure    | supported        | passed                | reports/p0_5_tail_failure_decomposition.csv |
| second_breakout            | h1_formula_too_narrow                            | rejected         | failed                | reports/p0_5_matched_lift_decomposition.csv |
| second_breakout            | h2_window_position_problem                       | rejected         | failed                | reports/p0_5_matched_lift_decomposition.csv |
| second_breakout            | h3_ep2_reference_pollution                       | rejected         | failed                | reports/p0_5_trigger_decomposition.csv      |
| second_breakout            | h4_matched_baseline_too_strong_or_anchor_no_lift | supported        | passed                | reports/p0_5_matched_lift_decomposition.csv |
| second_breakout            | h5_tail_risk_not_trigger_rate_is_core_failure    | supported        | passed                | reports/p0_5_tail_failure_decomposition.csv |

## Stop / Continue Decision

| decision_scope   | anchor_family_id           | recommended_decision              |   decision_precedence_rank | decision_rationale                                                                           |
|:-----------------|:---------------------------|:----------------------------------|---------------------------:|:---------------------------------------------------------------------------------------------|
| family           | pullback_hold_restrengthen | stop_current_family               |                          1 | Stop required by sparse partitions, matched-baseline failure, or tail/concentration failure. |
| family           | second_breakout            | stop_current_family               |                          1 | Stop required by sparse partitions, matched-baseline failure, or tail/concentration failure. |
| overall          | all                        | write_deferred_family_requirement |                          2 | Overall decision follows family precedence unless deferred-family rule passes.               |

Overall P0.5 decision: `write_deferred_family_requirement`.
