# Requirement: Experiment B - Regime x Event-Family Performance Matrix

## 1. Background

07 / 08 reports show materially different behavior by market regime. Experiment A then showed that the main 10d executable-density issue is not E1 sparsity and not single-family R repetition. The real issue is cross-family collision after R1 / R2 / R6 / R7 / R8 are unioned into R-core.

Experiment A also showed that T4 / T7 is not a strong recall indicator in its current selected form. `08_selected_T4_T7_union` is low density, but all/all pre-replay any recall is only 17.61%, pre-replay bridge recall is only 5.09%, and 10d fast-fail is 35.19%. Transition-specific readouts are still weak enough to challenge the T4 / T7 hypothesis. Therefore Experiment B must not treat T4 / T7 as the default transition-regime answer. It must reselect transition event families from the eligible family pool.

Retention is currently only available as pre-replay capture. Experiment B must consume Experiment A as a frozen evidence contract, expose its 10d / 20d failure readouts as diagnostic labels, and avoid using those labels as t0 entry features.

Experiment B is a diagnostic / design experiment. It does not select a final entry union, does not train a model, and does not emit direct-entry support.

## 2. Primary Question

```text
Which event families provide recall, bridge quality, acceptable 10d fast-fail
cost, and acceptable executable-density behavior in risk_off, risk_on, and
transition regimes, after applying Experiment A's density, uniqueness,
collision, source-status, and failure-label findings?

For transition specifically, which event family or family set should replace
or compete with the old T4 / T7 hypothesis after Experiment A showed weak
recall and high fast-fail?
```

## 3. Required Dependency

Experiment B must read and reference:

```text
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_audit_report.md
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
```

If the density contract is missing, the final decision must be:

```text
regime_family_matrix_contract_blocked
```

If the Experiment A manifest / report is missing, or if its final decision is not one of the allowed source-complete states below, the final decision must be:

```text
regime_family_matrix_input_blocked
```

Allowed Experiment A source-complete states:

1. `density_fast_fail_audit_complete`
2. `density_fast_fail_audit_partial_source_complete`

Experiment B must not redefine 10d density, adjacent gap, uniqueness, fast-fail, retention source status, or episode-window diagnostic rules. It must consume Experiment A's output tables and manifest as read-only evidence.

## 4. Experiment A Result Constraints

The following Experiment A facts are binding inputs to Experiment B:

| scope | event_n | pre_replay_any_recall | pre_replay_bridge_recall | rolling_10d_duplicate_rate | uniqueness_10d_p10 | fast_fail_10d_rate | false_repair_20d_rate | B interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `07_E1_only` | 6820 | 71.12% | 32.56% | 0.19% | 1.000 | 14.52% | 20.62% | sparse baseline; not a density problem |
| `07_full_union` | 15161 | 72.04% | 34.75% | 29.60% | 0.727 | 16.33% | 23.13% | 07 union density alert; context only |
| `08_selected_T4_T7_union` | 2063 | 17.61% | 5.09% | 3.73% | 1.000 | 35.19% | 39.07% | low recall, low density, high fast-fail; challenged incumbent |
| `08_R_core_event_regime_gated` | 47914 | n/a | n/a | 57.83% | 0.364 | 24.20% | 31.11% | cross-family collision diagnostic only |
| `08_R1_event_regime_gated` | 14363 | 85.28% | 33.84% | 0.00% | 1.000 | 26.61% | 33.49% | individual R family; evaluate by regime |
| `08_R2_event_regime_gated` | 9537 | 76.25% | 27.13% | 0.00% | 1.000 | 23.75% | 29.16% | individual R family; evaluate by regime |
| `08_R6_event_regime_gated` | 16204 | 88.25% | 38.99% | 0.00% | 1.000 | 23.19% | 30.30% | individual R family; evaluate by regime |
| `08_R7_event_regime_gated` | 9786 | 78.86% | 33.29% | 0.00% | 1.000 | 23.30% | 29.62% | individual R family; evaluate by regime |
| `08_R8_event_regime_gated` | 12896 | 74.85% | 28.04% | 0.00% | 1.000 | 26.33% | 33.70% | individual R family; evaluate by regime |

Transition-specific T4 / T7 constraints:

| scope | split | transition_episode_n | transition_event_n | pre_replay_any_recall | pre_replay_bridge_recall | fast_fail_10d_rate | false_repair_20d_rate | cell_sample_status | B interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `08_selected_T4_T7_union` | train | 304 | 249 | 23.03% | 8.55% | 28.74% | 30.52% | `sufficient_for_cell_readout` | weak recall / bridge with high failure |
| `08_selected_T4_T7_union` | robustness | 100 | 61 | 12.00% | 2.00% | 16.67% | 24.59% | `sufficient_for_cell_readout` | weak recall / bridge; lower but still non-baseline failure |
| `08_selected_T4_T7_union` | validation | 81 | 157 | 8.64% | 3.70% | 25.48% | 29.94% | `low_power_caution` | diagnostic only |
| `08_selected_T4_T7_union` | all | n/a | 467 | n/a | n/a | 26.08% | 29.55% | context | transition fast-fail context only |

Additional binding constraints:

1. E1 is the low-congestion baseline. B must not describe E1 as a density failure; the E1 problem is coverage / recall.
2. T4 / T7 cannot be promoted because it is sparse. Its all/all recall / bridge readout is weak, its transition split readouts remain weak, and its 10d fast-fail is above the E1 baseline in the relevant readouts. B must mark it as a challenged incumbent and `quality_filter_required` unless regime-specific evidence proves otherwise.
3. Transition-specific findings must use exact Experiment A transition split rows. B must not substitute all/all T4 / T7 metrics for train / robustness / validation transition cells.
4. Transition-regime analysis must not assume T4 / T7 is the correct transition family. B must reselect transition event families from the full eligible pool using recall, bridge, density, collision, and fast-fail diagnostics.
5. R-core union cannot be classified as a family support candidate. It is a cross-family collision stress scope used to explain why de-overlap, cooldown, top-k, or ranker design is required.
6. R1 / R2 / R6 / R7 / R8 must be evaluated separately. Their individual 10d duplicate rates are 0.00%, but their combined R-core union creates severe same-instrument 10d collision.
7. Retention evidence from Experiment A is `pre_replay_capture_only`. It must not be treated as post-fast-fail retention, oracle replay retention, or tradeable support.
8. `08_R_core_event_regime_gated` has no capture scope in Experiment A and must carry `scope_capture_not_available` for retention fields.
9. R-series compression arms are `aggregate_frontier_only_no_event_membership`. They may appear only as hypotheses / recommended reconstruction targets, not as event-level family decisions.
10. Experiment A's 10d and 20d failure readouts must appear in B as diagnostic labels / label-derived metrics. They may be used for audit, rejector targets, and quality-filter analysis, but must never be used as t0 entry features.

## 5. Required Inputs

Read-only inputs:

1. `outputs/manifests/run_manifest.json`
2. `outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json`
3. `outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md`
4. `outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_audit_report.md`
5. `outputs/publishable/tables/density_fast_fail_audit/density_fast_fail_audit_gate_summary.csv`
6. `outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv`
7. `outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv`
8. `outputs/publishable/tables/density_fast_fail_audit/candidate_density_caliber_crosswalk.csv`
9. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_summary.csv`
10. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_uniqueness_diagnostic.csv`
11. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_fast_fail_readout.csv`
12. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_retention_by_split_regime.csv`
13. `outputs/publishable/tables/density_fast_fail_audit/candidate_adjacent_event_gap_diagnostic.csv`
14. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_vs_episode_density_comparison.csv`
15. `outputs/publishable/tables/candidate_family_event_instances.csv` or `outputs/publishable/tables/candidate_family_event_instances.csv.gz`
16. `outputs/publishable/tables/candidate_family_canonical_events.csv` or `outputs/publishable/tables/candidate_family_canonical_events.csv.gz`
17. `outputs/publishable/tables/candidate_family_incremental_recall_over_e1.csv`
18. `outputs/publishable/tables/candidate_family_bridge_positive_recall.csv`
19. `outputs/publishable/tables/candidate_family_recall_by_split_regime.csv`
20. `outputs/publishable/tables/candidate_family_density_summary.csv`
21. `outputs/publishable/tables/candidate_family_label_quality_readout.csv`
22. `outputs/publishable/tables/candidate_family_false_repair_diagnostic.csv`
23. `outputs/publishable/tables/candidate_family_overlap_matrix.csv`
24. `outputs/publishable/tables/candidate_family_mechanism_cluster_summary.csv`
25. `outputs/publishable/tables/regime_recall_baseline_07_e1_only.csv`
26. 07 tables needed for E1 / E2 / E3 / E6 context:
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_channel_recall_contribution.csv`
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_channel_density_summary.csv`
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_false_repair_diagnostic.csv`
27. this requirement file.

If Experiment A tables are missing but the user intentionally runs B as a pre-A planning pass, B may output only a schema / plan report with:

```text
regime_family_matrix_waiting_for_density_contract
```

It must not output family support claims.

## 6. Candidate Families and Diagnostic Scopes

Experiment B must include at least the following family-level candidates:

1. `E1_early_ema60_repair`
2. `E2_same_day_confirmation_tag`
3. `E3_persistence_quality`
4. `E6_continuation_tag`
5. `T4_entropy_compression_then_directional_expansion`
6. `T7_board_relative_strength_break`
7. `R1_relative_strength_breakout`
8. `R2_near_high_volume_expansion`
9. `R6_market_breadth_thrust`
10. `R7_cross_sectional_momentum_rank_jump`
11. `R8_persistent_distance_above_ema`

Experiment B must also include these A-aligned diagnostic scopes:

1. `07_E1_only` as sparse baseline.
2. `07_full_union` as 07 density-alert context.
3. `08_selected_T4_T7_union` as low-recall / low-density / high-fast-fail context.
4. `08_T4_gated` and `08_T7_gated` as individual T4 / T7 challenged-incumbent scopes.
5. `08_R_core_event_regime_gated` as cross-family collision stress diagnostic.
6. `08_R1_event_regime_gated`, `08_R2_event_regime_gated`, `08_R6_event_regime_gated`, `08_R7_event_regime_gated`, `08_R8_event_regime_gated` as individual R-family evidence.

Optional diagnostic families may include R3, T3, T5, T6, T8, and R5, but optional families must never replace the required list.

For transition reselection, the eligible pool must include the required E / R / T families plus any optional transition-relevant families with reconstructable event membership. T4 / T7 must remain in the pool as challenged incumbents / negative controls, not as the default transition answer. The individual T4 / T7 readout must use `08_T4_gated` and `08_T7_gated`; `08_selected_T4_T7_union` is union context only and must not be used as the sole evidence for an individual T4 or T7 role. If event instances or canonical events are unavailable, transition family-combination scoring and cross-family collision scoring must be `source_blocked`, not approximated from aggregate recall tables.

R-series compression arms may be listed only in `regime_family_compression_arm_hypothesis.csv` and the report's recommendation section until selected-event membership is reconstructed.

## 7. Regime and Split Grid

Required regimes:

1. `risk_off`
2. `risk_on`
3. `transition`

Required splits:

1. `train`
2. `validation`
3. `robustness`
4. `all`

Headline conclusions may use `all` only as context. Support / block conclusions must be split-aware and must respect sample-size guardrails.

## 8. Transition Regime Family Reselection

Experiment B must run a transition-specific family reselection pass. The pass must answer:

```text
Among reconstructable families, which family or family combination best explains
transition-regime recall and bridge capture without inheriting T4 / T7's high
fast-fail profile or R-core's cross-family collision?
```

Required transition reselection rules:

1. Candidate screening must be run on `market_regime_bucket = transition` separately from risk_on and risk_off.
2. Screening metrics must include pre-replay any recall, pre-replay bridge recall, incremental recall over E1, 10d fast-fail label-derived rate, 20d false-repair label-derived rate, rolling 10d duplicate rate, 10d uniqueness p10, and cross-family collision.
3. T4 / T7 must be evaluated as challenged incumbents. Individual T4 / T7 scoring must use `08_T4_gated` and `08_T7_gated`; `08_selected_T4_T7_union` is union context only. For those two A-aligned scopes, `pre_replay_any_recall` and `pre_replay_bridge_recall` must come from `candidate_10d_retention_by_split_regime.csv`; B must not expect `08_T4_gated` or `08_T7_gated` scope ids to appear in `candidate_family_recall_by_split_regime.csv` or `candidate_family_bridge_positive_recall.csv`. Those 08 family tables are variant-keyed and may be used only as supplemental variant context. T4 / T7 may be retained only as `quality_filter_required`, `context_tag_only`, or `negative_control` unless the individual scope beats the new candidate pool on transition recall / bridge while also reducing fast-fail.
4. A transition candidate cannot be selected solely because it is sparse. It must clear minimum recall / bridge evidence and must not be worse than the E1 fast-fail baseline without an explicit quality-filter rationale.
5. Train and robustness splits must be shown separately. Validation transition can be diagnostic only if sample-size guardrails fail.
6. If no family clears the transition screen, B must report `transition_family_reselection_inconclusive` in the recommendation table instead of falling back to T4 / T7.

Required transition roles:

1. `transition_primary_candidate`
2. `transition_support_feature`
3. `transition_quality_filter_candidate`
4. `transition_context_only`
5. `transition_negative_control`
6. `transition_source_blocked`
7. `transition_inconclusive`

## 9. Fast-Fail Diagnostic Labels

Experiment B must expose Experiment A's failure diagnostics as labels and label-derived rates.

Required aggregate diagnostic fields:

1. `candidate_scope_id`
2. `event_split`
3. `market_regime_bucket`
4. `event_count`
5. `failure_10_complete_event_count`
6. `fast_fail_10d_count`
7. `fast_fail_10d_rate`
8. `false_repair_20d_count`
9. `false_repair_20d_rate`
10. `non_executable_event_count`
11. `horizon_incomplete_10d_count`
12. `label_source_column`
13. `fast_fail_definition_id`
14. `label_mapping_status`
15. `event_level_label_source_status`
16. `fast_fail_diagnostic_label_usage`

`fast_fail_diagnostic_label_usage` must be:

```text
diagnostic_only_not_t0_feature
```

Aggregate outputs must not contain boolean diagnostic-label columns. Aggregate failure diagnostics are represented by counts, rates, source columns, and source-status fields.

If B materializes event-level diagnostic rows, the event-level artifact must include at least:

1. `event_id`
2. `instrument`
3. `candidate_scope_id`
4. `event_split`
5. `market_regime_bucket`
6. `event_window_anchor_pos`
7. `fast_fail_10d_diagnostic_label`
8. `false_repair_20d_diagnostic_label`
9. `label_source_column`
10. `fast_fail_definition_id`
11. `event_level_label_source_status`

The event-level artifact may be local-only if too large for publishable output. If materialized locally, write it under:

```text
outputs/local_cache/regime_family_matrix/regime_family_fast_fail_event_diagnostics.parquet
```

The report may describe these as 10d / 20d fast-fail diagnostics, but the physical 20d column name must stay aligned with Experiment A's `false_repair_20d_*` naming unless an implementation source provides a separate true `fast_fail_20d_*` label.

## 10. Required Outputs

Write outputs under:

```text
outputs/publishable/tables/regime_family_matrix/
outputs/publishable/reports/regime_family_matrix/
outputs/manifests/regime_family_matrix/
```

Required tables:

1. `regime_family_experiment_a_alignment.csv`
2. `regime_family_performance_matrix.csv`
3. `regime_family_sample_guardrail.csv`
4. `regime_family_density_fast_fail_matrix.csv`
5. `regime_family_fast_fail_diagnostic_matrix.csv`
6. `regime_family_bridge_recall_matrix.csv`
7. `regime_family_overlap_concentration_matrix.csv`
8. `regime_family_cross_family_collision_matrix.csv`
9. `regime_family_retention_source_status.csv`
10. `transition_event_family_reselection_matrix.csv`
11. `regime_family_compression_arm_hypothesis.csv`
12. `regime_family_design_recommendations.csv`

Required report:

1. `regime_family_matrix_report.md`

Required manifest:

1. `regime_family_matrix_manifest.json`

## 11. Required Metrics

For each split / regime / family cell, report:

1. `source_scope_id`
2. `source_scope_status`
3. `retention_source_status`
4. `episode_denominator_n`
5. `bridge_denominator_n`
6. `event_n`
7. `candidate_captured_episode_n`
8. `before_first_50pct_any_recall`
9. `bridge_positive_recall`
10. `pre_replay_any_recall`
11. `pre_replay_bridge_recall`
12. `post_replay_any_recall`
13. `post_replay_bridge_recall`
14. `incremental_recall_over_e1`
15. `incremental_captures_over_e1`
16. `incremental_recall_source_status`
17. `e1_missed_capture_n`
18. `failure_10_complete_event_count`
19. `fast_fail_10d_count`
20. `fast_fail_10d_rate`
21. `fast_fail_excess_vs_e1_pp`
22. `false_repair_20d_count`
23. `false_repair_20d_rate`
24. `non_executable_event_count`
25. `horizon_incomplete_10d_count`
26. `label_source_column`
27. `fast_fail_definition_id`
28. `label_mapping_status`
29. `event_level_label_source_status`
30. `fast_fail_diagnostic_label_usage`
31. `events_per_instrument_year_mean`
32. `events_per_instrument_year_p95`
33. `rolling_10d_duplicate_rate`
34. `density_granularity`
35. `density_source_split`
36. `density_source_regime`
37. `density_cell_recomputed_flag`
38. `event_uniqueness_10d_p10`
39. `event_uniqueness_10d_low_share`
40. `concurrency_p95`
41. `adjacent_gap_median`
42. `adjacent_gap_lt_10d_share`
43. `cross_family_collision_10d_rate`
44. `single_family_density_share`
45. `mechanism_cluster_share`
46. `label_completeness_rate`
47. `next_open_executable_rate`
48. `experiment_a_density_alert_status`
49. `experiment_a_source_caveat`
50. `transition_reselection_role`
51. `experiment_a_cell_sample_status`
52. `computed_cell_sample_status`
53. `cell_sample_status`
54. `cell_sample_status_resolution`
55. `family_regime_role_recommendation`

If Experiment A marks retention as `pre_replay_capture_only`, `post_replay_any_recall` and `post_replay_bridge_recall` must be empty / null, and the report must explicitly state that no post-fast-fail retention support is available.

Individual T4 / T7 source rule:

1. For `08_T4_gated` and `08_T7_gated`, `pre_replay_any_recall` and `pre_replay_bridge_recall` must be read from `candidate_10d_retention_by_split_regime.csv`.
2. `candidate_family_recall_by_split_regime.csv`, `candidate_family_bridge_positive_recall.csv`, and `candidate_family_incremental_recall_over_e1.csv` may contain T4 / T7 variant rows, but they are not keyed by the A scope ids `08_T4_gated` and `08_T7_gated`.
3. For `08_T4_gated` and `08_T7_gated`, `incremental_recall_over_e1` and `incremental_captures_over_e1` may be null with:

```text
incremental_recall_source_status = not_available_publishable_source
```

4. Missing incremental recall for `08_T4_gated` / `08_T7_gated` must not source-block the cell if pre-replay recall / bridge, fast-fail, density, uniqueness, and gap diagnostics are available from Experiment A.

Density granularity contract:

1. `candidate_10d_density_summary.csv` is scope-level only. It has no `event_split` or `market_regime_bucket` columns.
2. `events_per_instrument_year_mean`, `events_per_instrument_year_p95`, and `rolling_10d_duplicate_rate` must be joined into split / regime / family cells by `source_scope_id` only.
3. For those scope-level density fields, set:

```text
density_granularity = scope_level_only
density_source_split = all
density_source_regime = all
density_cell_recomputed_flag = False
```

4. B must not recompute scope-level density fields at split / regime granularity. Recomputing them would violate the Experiment A contract and the no-redefinition rule in section 3.
5. Split / regime cell-level values are allowed only for A tables that already provide split / regime columns: uniqueness / concurrency from `candidate_10d_uniqueness_diagnostic.csv`, adjacent gap from `candidate_adjacent_event_gap_diagnostic.csv`, fast-fail diagnostics from `candidate_10d_fast_fail_readout.csv`, and retention from `candidate_10d_retention_by_split_regime.csv`.
6. If a cell requires split / regime density but A provides only scope-level density, keep the scope-level value, mark `density_granularity = scope_level_only`, and explain the limitation in the report.

## 12. Sample-Size and Source Guardrails

Every split / regime / family cell must report `episode_denominator_n` and `bridge_denominator_n`.

Cell status rules:

1. If `episode_denominator_n < 30` or `bridge_denominator_n < 30`, set:

```text
computed_cell_sample_status = diagnostic_only
```

The cell must not be used for support / block decisions, threshold tuning, or family selection.

2. If `30 <= episode_denominator_n < 100` or `30 <= bridge_denominator_n < 100`, set:

```text
computed_cell_sample_status = low_power_caution
```

The cell may be discussed only with train / robustness consistency and must not be a sole support claim.

3. If both denominators are >= 100, set:

```text
computed_cell_sample_status = sufficient_for_cell_readout
```

4. Known small cells, including validation risk_on with denominator around 22, must be explicitly marked `diagnostic_only`.

5. If Experiment A already provides `cell_sample_status`, B must preserve it in `experiment_a_cell_sample_status` and compute `computed_cell_sample_status` independently from the denominators available in B.

6. Final `cell_sample_status` must be the more conservative of `experiment_a_cell_sample_status` and `computed_cell_sample_status`.

Conservative ordering:

```text
diagnostic_only > low_power_caution > sufficient_for_cell_readout
```

If the two statuses differ, set:

```text
cell_sample_status_resolution = conservative_override
```

7. If `retention_source_status` is `pre_replay_capture_only`, the cell may support "candidate generation has recall" but may not support "post-filter retention survives".

8. If `source_scope_status` is `scope_capture_not_available`, recall / bridge recall fields must be null and the cell can only be used for density / fast-fail / collision diagnostics.

9. If a compression arm is `aggregate_frontier_only_no_event_membership`, it must be excluded from event-level metrics and family role classification.

10. Fast-fail diagnostic labels must be excluded from feature inputs and entry-rule definitions. They can appear only in diagnostic tables, quality-filter readouts, rejector-target design notes, or post-hoc report sections.

11. Scope-level density limitations do not change `cell_sample_status`. They must be represented through `density_granularity = scope_level_only` and `experiment_a_source_caveat`.

## 13. Family Role Classification

Experiment B must classify each family / regime pair into one of:

1. `backbone_candidate`
2. `support_feature_candidate`
3. `quality_filter_required`
4. `collision_deoverlap_required`
5. `union_collision_diagnostic_only`
6. `context_tag_only`
7. `density_or_fast_fail_blocked`
8. `bridge_quality_blocked`
9. `sample_blocked`
10. `source_blocked`
11. `negative_control`

Classification rules:

1. `backbone_candidate` is a design role only, not direct-entry support. It requires sufficient sample cells, positive incremental recall over E1, bridge-positive recall not worse than E1, acceptable 10d fast-fail cost, no Experiment A density alert, and no cross-family collision block.
2. `support_feature_candidate` allows direct-entry density or concentration to be imperfect, but requires positive bridge readout, acceptable fast-fail cost, and no source caveat that invalidates the evidence.
3. `quality_filter_required` applies when density is acceptable but fast-fail is materially worse than E1. `08_selected_T4_T7_union`, T4, and T7 must default to this role unless split / regime evidence proves a materially lower fast-fail profile.
4. `collision_deoverlap_required` applies when individual family evidence is usable but the corresponding union shows severe cross-family 10d collision. R1 / R2 / R6 / R7 / R8 in risk_on must be evaluated for this role.
5. `union_collision_diagnostic_only` is forced for `08_R_core_event_regime_gated`.
6. `context_tag_only` applies when overlap is high or incremental recall is near zero but the family may help as a feature.
7. `density_or_fast_fail_blocked` applies when Experiment A marks a density alert that cannot be separated from the family or when fast-fail is too high for any design role other than rejector / quality-filter research.
8. `sample_blocked` overrides all positive claims when sample guardrails fail.
9. `source_blocked` overrides all positive claims when event membership, capture scope, or retention source status is unavailable for the claimed metric.
10. `negative_control` applies to families such as R5 if low density comes with poor recall / bridge quality.

## 14. Regime Design Hypotheses

The report must evaluate, but not assume as true:

1. `risk_off`: E1 repair may remain the cleanest sparse baseline; R/T families may be context only unless they add bridge recall without fast-fail or collision cost.
2. `risk_on`: R1 / R6 / R7 / R8 may provide high pre-replay recall and bridge capture, but raw R-core union is collision blocked. The question is whether individual R families can become features or de-overlapped candidates.
3. `transition`: T4 / volatility-compression families are no longer the default transition answer. B must reselect transition event families from the eligible pool and use T4 / T7 mainly as challenged incumbents, quality-filter candidates, or negative controls unless the data disproves Experiment A's weak-recall / high-fast-fail warning.

## 15. Decisions

Allowed final decisions:

1. `regime_family_matrix_complete`
2. `regime_family_matrix_contract_blocked`
3. `regime_family_matrix_input_blocked`
4. `regime_family_matrix_waiting_for_density_contract`
5. `regime_family_matrix_source_caveated_complete`
6. `regime_family_matrix_transition_reselection_inconclusive`

Decision priority:

1. If the density contract is missing, return `regime_family_matrix_contract_blocked`.
2. If required non-optional inputs are missing and this is not an intentional pre-A planning pass, return `regime_family_matrix_input_blocked`.
3. If running as an intentional pre-A planning pass, return `regime_family_matrix_waiting_for_density_contract`.
4. If Experiment A final decision is `density_fast_fail_audit_partial_source_complete`, or any retention row used by B has `retention_source_status = pre_replay_capture_only`, or any required role claim depends on source-caveated evidence, return `regime_family_matrix_source_caveated_complete` when the run otherwise completes.
5. `regime_family_matrix_complete` is allowed only when Experiment A final decision is `density_fast_fail_audit_complete`, no required retention evidence is `pre_replay_capture_only`, and all required role claims have event membership / capture / post-replay source support.
6. If no transition family clears the transition screen but there are no source caveats requiring `regime_family_matrix_source_caveated_complete`, return `regime_family_matrix_transition_reselection_inconclusive`.
7. If source caveats and transition reselection inconclusiveness both occur, the top-level final decision must be `regime_family_matrix_source_caveated_complete`, and `transition_family_reselection_inconclusive` must appear in `regime_family_design_recommendations.csv`.

This experiment must not emit direct-entry support. It only emits design recommendations for Experiment C / later decomposition work.

## 16. Report Requirements

`regime_family_matrix_report.md` must contain:

1. one-page conclusion.
2. Experiment A alignment summary, including final decision and source caveats.
3. sample-size and source-status guardrail summary.
4. family role matrix by regime.
5. risk_off findings.
6. risk_on findings, including R1 / R6 recall value and R-core collision caveat.
7. transition reselection findings, including why T4 / T7 is retained, demoted, or rejected.
8. T4 / T7 individual-vs-union caveat: `08_T4_gated` and `08_T7_gated` drive individual roles; `08_selected_T4_T7_union` is context only.
9. T4 / T7 source caveat: `08_T4_gated` / `08_T7_gated` recall and bridge come from Experiment A retention, while 08 family recall / bridge tables are variant-keyed supplemental context.
10. density / fast-fail / uniqueness summary using Experiment A contract.
11. density granularity caveat: scope-level density values are joined into cells and are not split / regime recomputations.
12. fast-fail diagnostic section covering `fast_fail_10d_*`, `false_repair_20d_*`, `label_source_column`, and source-status fields.
13. R-core cross-family collision decomposition.
14. retention source caveat: pre-replay capture is not post-fast-fail retention.
15. compression-arm hypothesis section marked aggregate-only.
16. small-cell caveats, including validation risk_on.
17. recommendations for Experiment C, including R-family de-overlap / ranker design and the newly selected transition-family direction.

## 17. Tests

At minimum, tests must verify:

1. cells with denominator < 30 are forced to `diagnostic_only`.
2. cells with denominator 30-99 are marked `low_power_caution`.
3. Experiment B fails closed if the density contract is absent.
4. Experiment B fails closed if the Experiment A manifest / report is missing.
5. no metric redefines 10d density, uniqueness, adjacent gap, or fast-fail outside the Experiment A contract.
6. `all` split cannot override split-level sample-blocked cells.
7. high-overlap families can be classified only as `context_tag_only` unless non-overlap bucket evidence is available.
8. `08_R_core_event_regime_gated` is always `union_collision_diagnostic_only` and never `backbone_candidate` or `support_feature_candidate`.
9. `pre_replay_capture_only` retention cannot populate post-replay retention fields or support post-filter claims.
10. T4 / T7 high fast-fail prevents `backbone_candidate` unless regime-specific evidence shows a materially different fast-fail profile.
11. Experiment A density-alert status propagates into B's density / collision columns.
12. aggregate-only compression arms cannot feed event-level decisions, role classification, or hard gates.
13. `scope_capture_not_available` forces recall and bridge recall fields to null for that scope.
14. transition reselection does not default to T4 / T7 when its recall / bridge metrics remain weak.
15. `transition_family_reselection_inconclusive` is emitted when no transition family clears sample, recall, bridge, density, and fast-fail diagnostics.
16. aggregate fast-fail diagnostic outputs contain count / rate / source fields and do not contain boolean `*_diagnostic_label` columns.
17. event-level fast-fail diagnostic labels are present only if an event-level diagnostic artifact is materialized, and remain absent from t0 feature inputs and entry rules.
18. the 20d diagnostic uses Experiment A's `false_repair_20d_*` naming unless a distinct `fast_fail_20d_*` source is explicitly available.
19. transition family-combination scoring and cross-family collision scoring are `source_blocked` if event instances or canonical events are unavailable.
20. the required T4 family id is exactly `T4_entropy_compression_then_directional_expansion`.
21. transition-specific T4 / T7 findings use transition split metrics, not only all/all metrics.
22. scope-level density fields copied into split / regime cells carry `density_granularity = scope_level_only`, `density_source_split = all`, `density_source_regime = all`, and `density_cell_recomputed_flag = False`.
23. B does not recompute `events_per_instrument_year_mean`, `events_per_instrument_year_p95`, or `rolling_10d_duplicate_rate` at split / regime level.
24. final `cell_sample_status` is the more conservative of `experiment_a_cell_sample_status` and `computed_cell_sample_status`.
25. current Experiment A `density_fast_fail_audit_partial_source_complete` or any `pre_replay_capture_only` retention source forces top-level `regime_family_matrix_source_caveated_complete`.
26. T4 / T7 individual roles are evaluated from `08_T4_gated` and `08_T7_gated`; `08_selected_T4_T7_union` is accepted only as context.
27. `08_T4_gated` and `08_T7_gated` pre-replay recall / bridge are read from `candidate_10d_retention_by_split_regime.csv`, not joined by those scope ids against 08 family recall / bridge tables.
28. Missing `incremental_recall_over_e1` for `08_T4_gated` / `08_T7_gated` sets `incremental_recall_source_status = not_available_publishable_source` and does not source-block the cell by itself.
