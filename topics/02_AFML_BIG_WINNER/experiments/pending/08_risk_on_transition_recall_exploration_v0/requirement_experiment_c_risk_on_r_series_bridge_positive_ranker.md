# Requirement: Experiment C - Risk-on / Transition R-series Bridge-Positive Ranker

## 1. Background

Experiment A showed that `07_E1_only` is not a 10d density failure case. E1 is sparse enough and reasonably clean, but misses a large share of bridge-positive recall in `risk_on` and `transition` regimes.

Experiment B changed the prior for Experiment C:

1. T4 / T7 are not a strong transition recall backbone. `08_selected_T4_T7_union` has low density, but its all/all recall is only 17.61%, bridge recall is 5.09%, and fast-fail is 35.19%. In transition train it reaches only 23.03% recall and 8.55% bridge with 28.74% fast-fail.
2. R-family single scopes are strong, but the raw R-core union is not directly usable. R1 / R2 / R6 / R7 / R8 each have 0.00% rolling 10d duplicate, while `08_R_core_event_regime_gated` has 57.83% rolling duplicate, 0.364 uniqueness p10, and 38.12 p95 density.
3. R6 is the current transition primary candidate. In transition train, R6 has 96.05% recall, 49.34% bridge recall, and 20.86% fast-fail. In transition robustness, R6 has 43.00% recall, 27.00% bridge recall, and 14.42% fast-fail.
4. R6 is also the strongest risk_on positive candidate. In risk_on train, R6 has 96.44% recall, 43.30% bridge recall, and 30.52% fast-fail. In risk_on robustness, R6 has 90.06% recall, 56.91% bridge recall, and 22.70% fast-fail.
5. The binding problem is no longer "find any recall family". The problem is selecting / ranking / de-overlapping R-series events so that bridge-positive coverage survives while fast-fail, density, cross-family collision, and family concentration are controlled.

Experiment C therefore tests whether a train-only event selector can turn the R-family evidence from Experiment B into either:

1. a source-caveated direct-entry candidate, or
2. a meta-label / rejector feature-source candidate.

A no-direct-entry result is valid and must still produce reusable diagnostics for future label-source and replay work.

## 2. Required Dependencies

Experiment C must read and reference Experiment A and Experiment B outputs.

Required Experiment A contract:

```text
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
```

Required Experiment A manifest / source tables:

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_summary.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_10d_fast_fail_readout.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_10d_retention_by_split_regime.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_adjacent_event_gap_diagnostic.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_10d_uniqueness_diagnostic.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
```

Required Experiment B manifest / source tables:

```text
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/publishable/reports/regime_family_matrix/regime_family_matrix_report.md
outputs/publishable/tables/regime_family_matrix/regime_family_performance_matrix.csv
outputs/publishable/tables/regime_family_matrix/transition_event_family_reselection_matrix.csv
outputs/publishable/tables/regime_family_matrix/regime_family_density_fast_fail_matrix.csv
outputs/publishable/tables/regime_family_matrix/regime_family_fast_fail_diagnostic_matrix.csv
outputs/publishable/tables/regime_family_matrix/regime_family_cross_family_collision_matrix.csv
outputs/publishable/tables/regime_family_matrix/regime_family_bridge_recall_matrix.csv
outputs/publishable/tables/regime_family_matrix/regime_family_retention_source_status.csv
outputs/publishable/tables/regime_family_matrix/regime_family_compression_arm_hypothesis.csv
outputs/publishable/tables/regime_family_matrix/regime_family_design_recommendations.csv
```

Required 08 candidate-family event sources:

```text
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_incremental_recall_over_e1.csv
outputs/publishable/tables/candidate_family_bridge_positive_recall.csv
outputs/publishable/tables/candidate_family_density_summary.csv
outputs/publishable/tables/candidate_family_label_quality_readout.csv
outputs/publishable/tables/candidate_family_false_repair_diagnostic.csv
outputs/publishable/tables/candidate_family_overlap_matrix.csv
outputs/publishable/tables/candidate_family_feature_snapshot_summary.csv
outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_compression_frontier.csv
outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_score_spec.csv
outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_source_pool_summary.csv
```

Optional supervised-ranker inputs:

```text
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/candidate_family_capture.parquet
outputs/local_cache/cross_section_feature_panel.parquet
```

If the Experiment A contract is missing, return:

```text
risk_on_r_series_ranker_contract_blocked
```

If any required Experiment A / B manifest or required source table is missing, return:

```text
risk_on_r_series_ranker_input_blocked
```

If optional local cache is absent, supervised arms must fail closed with:

```text
ranker_arm_status = supervised_ranker_input_blocked_missing_local_cache
```

but deterministic budget / cooldown / de-overlap arms must still run if publishable tables are sufficient.

Allowed upstream final decisions:

1. Experiment A: `density_fast_fail_audit_complete`
2. Experiment A: `density_fast_fail_audit_partial_source_complete`
3. Experiment B: `regime_family_matrix_complete`
4. Experiment B: `regime_family_matrix_source_caveated_complete`

If Experiment A is `density_fast_fail_audit_partial_source_complete`, Experiment B is `regime_family_matrix_source_caveated_complete`, or any retention source is `pre_replay_capture_only`, Experiment C may still complete but the final decision must be source-caveated.

Experiment C must not redefine density, rolling duplicate, adjacent gap, uniqueness, fast-fail, false-repair, retention, or split/regime sample-status rules. It may compute those metrics only for newly selected event sets by applying the Experiment A contract verbatim.

### 2.1 Scope Reconstruction Contract

Experiment C must reconstruct every `candidate_scope_id` through Experiment A's published mapping contract.

Required rules:

1. `candidate_scope_mapping_contract.csv` is the source of truth for `source_artifact_path`, `source_row_filter`, `canonicalization_rule`, and `reconstructability_requirement`.
2. `candidate_scope_reconstructability_audit.csv` is the source of truth for whether event membership is reconstructable.
3. Any selected or rejected event row for `08_R6_event_regime_gated`, `08_R_core_event_regime_gated`, `08_T4_gated`, `08_T7_gated`, or `08_selected_T4_T7_union` must be produced from the mapping contract, not from ad hoc string matching.
4. If a required scope has `scope_mapping_status != reconstructable_event_membership`, deterministic event-level arms depending on that scope must return `ranker_arm_status = event_membership_source_blocked`.
5. B compression-arm rows are aggregate hypotheses only. If `event_membership_status != event_membership_available`, they may seed arm design but cannot pass direct-entry or feature-source gates.
6. `candidate_family_event_instances.csv.gz` and `candidate_family_canonical_events.csv.gz` are raw event sources; they do not by themselves define `candidate_scope_id` membership.

## 3. A/B Result Bindings

The implementation must encode these A/B bindings before any model or selector is run.

### 3.1 Baselines

| scope | event_n | recall | bridge | mean_density | p95_density | rolling_10d_duplicate | uniqueness_p10 | fast_fail_10d | false_repair_20d | role |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `07_E1_only` | 6,820 | 71.12% | 32.56% | 1.88 | 4.70 | 0.19% | 1.000 | 14.52% | 20.62% | clean baseline |
| `07_full_union` | 15,161 | 72.04% | 34.75% | 4.19 | 10.85 | 29.60% | 0.727 | 16.33% | 23.13% | density / duplicate blocked |
| `08_selected_T4_T7_union` | 2,063 | 17.61% | 5.09% | 0.57 | 1.53 | 3.73% | 1.000 | 35.19% | 39.07% | challenged incumbent / negative control |
| `08_R_core_event_regime_gated` | 47,914 | NA | NA | 13.23 | 38.12 | 57.83% | 0.364 | 24.20% | 31.11% | collision stress pool only |
| `08_R6_event_regime_gated` | 16,204 | 88.25% | 38.99% | 4.47 | 12.23 | 0.00% | 1.000 | 23.19% | 30.30% | primary positive family |

### 3.2 Transition Binding

R6 must enter Experiment C as the transition primary candidate.

| split | scope | recall | bridge | fast_fail_10d | false_repair_20d | cell_status | required C role |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| train | `08_R6_event_regime_gated` | 96.05% | 49.34% | 20.86% | 25.55% | sufficient | primary candidate |
| train | `08_R1_event_regime_gated` | 97.04% | 46.71% | 25.21% | 29.25% | sufficient | support feature |
| train | `08_R7_event_regime_gated` | 93.75% | 46.05% | 22.18% | 26.17% | sufficient | support feature |
| train | `07_E1_only` | 62.17% | 32.01% | 17.15% | 21.00% | sufficient | baseline |
| train | `08_selected_T4_T7_union` | 23.03% | 8.55% | 28.74% | 30.52% | sufficient | quality filter / negative control |
| robustness | `08_R6_event_regime_gated` | 43.00% | 27.00% | 14.42% | 20.89% | sufficient | primary candidate |
| robustness | `08_R2_event_regime_gated` | 45.00% | 21.00% | 11.64% | 17.10% | sufficient | support feature |
| robustness | `07_E1_only` | 40.00% | 24.00% | 7.63% | 13.49% | sufficient | baseline |
| validation | `08_R6_event_regime_gated` | 95.06% | 37.04% | 20.17% | 28.79% | low_power_caution | read-only diagnostic |

### 3.3 Risk-on Binding

R6 must enter Experiment C as the risk_on positive candidate, with explicit fast-fail cost controls.

| split | scope | recall | bridge | fast_fail_10d | rolling_10d_duplicate | required C role |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| train | `08_R6_event_regime_gated` | 96.44% | 43.30% | 30.52% | 0.00% | positive candidate with rejector |
| train | `07_E1_only` | 63.11% | 28.89% | 13.90% | 0.19% | baseline |
| train | `08_selected_T4_T7_union` | 21.78% | 6.22% | 40.31% | 3.73% | negative control |
| robustness | `08_R6_event_regime_gated` | 90.06% | 56.91% | 22.70% | 0.00% | positive candidate with rejector |
| robustness | `07_E1_only` | 49.17% | 34.81% | 13.47% | 0.19% | baseline |
| robustness | `08_selected_T4_T7_union` | 19.89% | 7.18% | 36.12% | 3.73% | negative control |

### 3.4 Source Caveats

Experiment C must carry these upstream limitations into every report and final decision:

1. Experiment A final state is allowed to be `density_fast_fail_audit_partial_source_complete`.
2. Experiment B final state is allowed to be `regime_family_matrix_source_caveated_complete`.
3. Retention is `pre_replay_capture_only`; recall / bridge claims are pre-replay candidate-generation claims.
4. `fast_fail_10d_*` and `false_repair_20d_*` are diagnostic labels, not t0 entry features.
5. 137 B cells have event-level fast-fail source and 49 do not. Missing event-level fast-fail source must block supervised rejector arms for those cells, but must not block deterministic readouts.
6. Validation risk_on is diagnostic only. Validation transition is `low_power_caution` and cannot drive threshold selection.

### 3.5 Binding Drift Guard

The numeric values in §3 are load-time bindings to Experiment A / B outputs, not informal documentation.

Implementation must verify the §3 binding values against the current A/B source tables before running selectors:

1. `event_n` must match exactly.
2. rates reported as percentages in §3 must match source tables within 0.01 percentage point after percentage conversion.
3. density / p95 / uniqueness values reported to two or three decimals must match source tables within the displayed rounding tolerance.
4. upstream decisions must match the manifest decisions in §2.

If any required binding value drifts outside tolerance, the run must stop with:

```text
risk_on_r_series_ranker_binding_drift_blocked
```

The report must identify the stale field, expected value, source value, and source artifact.

## 4. Primary Questions

Experiment C must answer:

```text
Can a train-only R-series ranker / budgeted selector preserve risk_on and transition
bridge-positive recall while reducing the density, duplicate, fast-fail, and
cross-family collision cost seen in the raw R-core pool?
```

It must also answer:

```text
Is the best supported output a source-caveated direct-entry candidate, a
meta-label / rejector feature-source, or diagnostic-only evidence?
```

Transition is not secondary. Risk_on and transition are both primary target regimes.

## 5. Non-Goals

Experiment C must not:

1. run a trading strategy or portfolio backtest.
2. tune thresholds, family budgets, feature selection, or cooldown parameters on validation or robustness.
3. use target episode membership to generate event candidates.
4. use future 120d returns as event features.
5. use `fast_fail_10d`, `failure_10_label`, `false_repair_20d`, or bridge outcome labels as t0 features.
6. silently drop R2 because it is unscored.
7. promote T4 / T7 as transition recall families only because they are sparse.
8. report raw `08_R_core_event_regime_gated` as a direct-entry candidate.
9. report a direct-entry candidate if only the feature-source gate passes.
10. claim post-replay recall / bridge retention unless a replay stage is explicitly implemented and audited.
11. overwrite Experiment A, Experiment B, full 08 run, or R-series compression patch artifacts.

## 6. Target Regimes and Split Discipline

Primary target regimes:

1. `risk_on`
2. `transition`

Diagnostic-only regime:

1. `risk_off`

Risk-off rules:

1. `risk_off` must consume Experiment B readouts for diagnostic context only.
2. `risk_off` must not be used for fitting, threshold selection, cooldown selection, family-budget selection, or final candidate support.
3. `risk_off` rows may appear in readout tables only with `target_regime_decision_tier = risk_off_diagnostic_only`.
4. Missing risk_off fast-fail / retention source must not block `risk_on` or `transition`, but must be reported in `risk_on_r_series_ranker_source_caveat_audit.csv`.

Split discipline:

1. Train may be used for fitting, scoring, thresholds, cooldowns, family budgets, and calibration.
2. Robustness is support / block readout only.
3. Validation is read-only diagnostic only.
4. Validation risk_on cannot support any candidate.
5. Validation transition is `low_power_caution` and can only sanity-check direction.

If any code path uses validation or robustness for threshold selection, final decision must be:

```text
risk_on_r_series_ranker_leakage_blocked
```

## 7. Source Families and Roles

Default R-series source families:

1. `R1_relative_strength_breakout`
2. `R2_near_high_volume_expansion`
3. `R6_market_breadth_thrust`
4. `R7_cross_sectional_momentum_rank_jump`
5. `R8_persistent_distance_above_ema`

Optional support family:

1. `R3_vcp_breakout`

Negative-control family:

1. `R5_growth_or_small_style_confirmation`

Context families:

1. `E1`
2. `E2`
3. `E3`
4. `E6`
5. `T4`
6. `T7`

Required family roles:

1. R6 is the required primary candidate for both `risk_on` and `transition`.
2. R1 and R7 are required transition support candidates.
3. R2 must be explicitly handled because transition robustness shows lower fast-fail but weaker bridge than R6.
4. R8 remains a support / context candidate unless train evidence promotes it.
5. Raw R-core union is collision stress input only and must not be selected directly.
6. T4 / T7 are challenged incumbents, quality-filter candidates, or negative controls only.
7. E1 is the baseline and comparison denominator.
8. R5 may be included only in diagnostics and must not contribute to selected pools.

## 8. R2 Handling

R2 is a core semantic family but may be unscored if amount / volume expansion fields are unavailable.

Experiment C must choose one explicit R2 policy:

1. `r2_recomputed_volume_score`: amount / volume fields are available, point-in-time safe, and hash-audited; R2 enters the score ranker.
2. `r2_family_budget_only`: R2 remains unscored but receives an explicit family budget / cooldown.
3. `r2_diagnostic_only`: R2 is excluded from selected pools but retained in diagnostics.

Silent R2 dropping is forbidden.

If R2 enters selected pools without a score, the selected event table must expose `rank_score_available = false` and the selection reason must be budget / cooldown based, not score based.

## 9. Feature Rules

Allowed feature classes:

1. t0-visible R1 / R6 / R7 / R8 score fields.
2. audited R2 amount / volume expansion fields if available.
3. family id and mechanism cluster id.
4. same-day overlap tags.
5. same-instrument prior-window event counts computed at t0 without future labels.
6. same-instrument family collision tags available at event t0.
7. event-regime / board / market context available at t0.
8. E1 / E2 / E3 / E6 / T4 / T7 same-day tags as context features only.

Forbidden features:

1. future return.
2. future high / low.
3. first +50% touch date.
4. target episode membership.
5. post-event volume.
6. validation / robustness labels.
7. `failure_10_label`
8. `failure_10_path`
9. `false_repair_20d`
10. bridge-positive outcome labels.
11. any field that is label-derived before event t0.

Experiment A fast-fail and Experiment B fast-fail / false-repair fields may be used as labels, cost readouts, or rejector targets only. They must not enter the t0 feature matrix.

## 10. Labels and Objectives

Training labels may use future outcomes only as labels, never as event-generation features.

Primary positive label:

```text
bridge_positive_event_or_episode_capture
```

This label is a pre-replay capture label.

Required label-source rules:

1. Supervised arms must source `bridge_positive_event_or_episode_capture` from `outputs/local_cache/candidate_family_capture.parquet` when that optional cache is available.
2. Deterministic readouts must source bridge / recall metrics from the pre-replay fields in Experiment A / B publishable tables.
3. The positive label must not require post-replay episode membership.
4. Missing post-replay episode membership must not be reported as `event_membership_source_blocked`.
5. Any post-filter retention claim is forbidden unless Experiment C implements and audits an explicit replay stage.

Primary cost labels:

```text
fast_fail_10d
false_repair_20d
```

Primary selection objectives:

1. preserve or improve bridge-positive recall vs E1.
2. capture E1-missed bridge-positive cases.
3. reduce R-core density and cross-family collision.
4. limit fast-fail and false-repair cost vs E1.
5. prevent single-family concentration from dominating selected events.

Secondary evaluation label:

```text
winner_120
```

`winner_120` must remain a staged downstream label and must not be the sole ranker objective.

## 11. Candidate Arms

Experiment C must evaluate at least these arms.

Baseline / stress arms:

1. `baseline_r_core_no_ranker_diagnostic`
2. `baseline_r6_only_transition_primary`
3. `baseline_r6_only_risk_on_positive`
4. `baseline_t4_t7_negative_control`

Family-pool arms:

1. `r6_r1_r7_bridge_pool`
2. `r6_r2_low_fast_fail_support`
3. `r6_r1_r2_r7_bridge_pool`
4. `family_budget_equal_weight`
5. `family_budget_bridge_weighted_train_only`

De-overlap / density-control arms:

1. `cooldown_20d_ranked_within_bucket`
2. `cooldown_40d_ranked_within_bucket`
3. `top_k_per_instrument_month_family_aware`
4. `top_k_per_instrument_20d_family_aware`
5. `market_day_family_quota`
6. `cross_family_collision_suppression`

Rejector / meta-label arms:

1. `fast_fail_rejector_overlay_train_only`
2. `false_repair_rejector_overlay_train_only`
3. `bridge_positive_ranker_with_fast_fail_penalty`
4. `supervised_bridge_ranker` if optional local-cache inputs are available.

R2 policy arms:

1. `r2_budget_only_arm` if R2 is unscored.
2. `r2_diagnostic_only_arm` if R2 cannot be selected.

Each arm must output selected canonical events, rejected events, rank scores if available, and failure reasons.

Deterministic arms must run even when supervised arms are blocked.

## 12. Gate Rules

Gate rules must be evaluated separately for `risk_on` and `transition`, then summarized jointly.

### 12.0 Decision Granularity and Fixed Density Thresholds

Experiment C has two decision layers:

1. `target_regime_decision_tier`: computed separately for `risk_on` and `transition`.
2. `final_decision`: computed once for the manifest and report after all required outputs are written.

Target-regime tiers may differ. For example, an arm may be `source_caveated_direct_entry_candidate_supported` for `transition` and `diagnostic_only_or_no_candidate` for `risk_on`.

The manifest-level `final_decision` must be one of:

1. `risk_on_r_series_ranker_complete`
2. `risk_on_r_series_ranker_source_caveated_complete`
3. `risk_on_r_series_ranker_input_blocked`
4. `risk_on_r_series_ranker_contract_blocked`
5. `risk_on_r_series_ranker_leakage_blocked`
6. `risk_on_r_series_ranker_source_blocked`
7. `risk_on_r_series_ranker_binding_drift_blocked`

If all required outputs are produced and any upstream source caveat from §3.4 is active, the manifest-level decision must be:

```text
risk_on_r_series_ranker_source_caveated_complete
```

This holds even if every target-regime tier is diagnostic-only.

When `final_decision` appears in row-level output tables, it must be a constant copy of the manifest-level decision. Row-level differences must be represented only by `target_regime_decision_tier`, gate columns, and failure columns.

Density admission thresholds are Experiment C thresholds, not Experiment A contract thresholds. Experiment A supplies the computation formula only.

Frozen E1 density reference:

```text
density_reference_scope_id = 07_E1_only
density_reference_granularity = all/all scope-level executable event-day density
density_reference_mean = 1.882717
density_reference_p95 = 4.704032
density_reference_rolling_10d_duplicate_rate = 0.0019
```

Direct-entry density admission is not strict E1 parity. E1 parity remains a diagnostic reference only.

Frozen direct-entry density budget:

```text
direct_entry_density_vs_e1_full_denominator_max = 1.50
direct_entry_events_per_instrument_year_mean_max = 2.824076
direct_entry_events_per_instrument_year_p95_max = 7.056048
direct_entry_rolling_10d_duplicate_rate_max = 15.00%
```

Allowed `density_granularity` values:

1. `selected_arm_recomputed`: selected-arm density recomputed from event membership using the Experiment A contract.
2. `scope_level_reference`: value inherited from an upstream A/B scope for baseline comparison only.
3. `scope_level_only`: upstream A/B cell carries only scope-level density and must not be treated as split/regime density.
4. `aggregate_only_reference`: compression-arm or summary-only value with no event membership; cannot pass direct-entry or feature-source gates.
5. `not_available_source_blocked`: required density source is missing.

Only `selected_arm_recomputed` may pass direct-entry or feature-source density gates.

Borderline pass rule:

1. Any recall / bridge / fast-fail / false-repair delta within plus or minus 1.00 percentage point of its threshold must set `borderline_pass_flag = true`.
2. `borderline_metric_names` must list the metrics that are within the borderline band.
3. Borderline status does not change pass/fail by itself, but must be visible in `risk_on_r_series_ranker_decision_tiers.csv` and the report.
4. The R6 robustness transition bridge delta is expected to be near the +3 percentage point threshold; it must not silently flip tiers without a borderline note.

### 12.1 Direct-entry candidate

Decision:

```text
direct_entry_candidate_supported
```

Required for a target-regime direct-entry decision:

1. train incremental recall vs E1 >= +8 percentage points.
2. train bridge delta vs E1 >= +5 percentage points.
3. robustness incremental recall vs E1 >= +3 percentage points.
4. robustness bridge delta vs E1 >= +3 percentage points.
5. train and robustness selected-arm cells for the target regime both have `cell_sample_status = sufficient_for_cell_readout`.
6. `density_granularity = selected_arm_recomputed`.
7. `density_vs_e1_full_denominator <= 1.50`.
8. selected `events_per_instrument_year_mean <= 2.824076`.
9. selected `events_per_instrument_year_p95 <= 7.056048`.
10. selected rolling 10d duplicate rate <= 15.00%.
11. single-family selected-event share <= 35%.
12. fast-fail 10d rate <= E1 same split/regime rate + 2 percentage points.
13. false-repair 20d rate <= E1 same split/regime rate + 3 percentage points.
14. OOS separability does not reverse on robustness.
15. selected event source is auditable.
16. the arm is not aggregate-only and has event-level selected/rejected membership.

If either required train or robustness cell is `low_power_caution`, `diagnostic_only`, or any status other than `sufficient_for_cell_readout`, `direct_entry_gate_pass` must be false. The arm may still be evaluated for feature-source or diagnostic tiers.

If upstream source caveats are present, this tier must be reported as:

```text
source_caveated_direct_entry_candidate_supported
```

unless a post-filter replay stage is implemented and audited inside Experiment C.

### 12.2 Meta-label / rejector feature source

Decision:

```text
meta_label_feature_source_supported
```

Allowed when direct-entry fails but:

1. single-family selected-event share <= 65%.
2. train bridge delta is positive in at least one primary target regime.
3. robustness bridge delta is non-negative or only mildly degraded with explanation.
4. `density_granularity = selected_arm_recomputed`.
5. `density_vs_e1_full_denominator <= 2.50`.
6. selected `events_per_instrument_year_p95 <= 12.226065`, using R6 all/all p95 as the maximum feature-source reference.
7. selected rolling 10d duplicate rate <= 15.00%.
8. fast-fail 10d cost is auditable.
9. fast-fail 10d rate <= E1 same split/regime rate + 10 percentage points, or a rejector-specific rationale is reported.
10. at least one OOS separability readout remains positive.
11. selected events are clearly marked as feature-source only.
12. the arm is not aggregate-only and has event-level selected/rejected membership.

If upstream source caveats are present, this tier must be reported as:

```text
source_caveated_meta_label_feature_source_supported
```

### 12.3 Diagnostic only / no candidate

Decision:

```text
diagnostic_only_or_no_candidate
```

Required when neither direct-entry nor feature-source gates pass.

This is a valid result. It must still output:

1. arm frontier.
2. ranker scores if available.
3. rejected-arm frontier.
4. family budget audit.
5. failure distribution.
6. explanation of whether the blocker is bridge, density, p95, duplicate, fast-fail, false-repair, concentration, OOS separability, missing feature source, or source caveat.

Other blocking decisions:

1. `risk_on_r_series_ranker_input_blocked`
2. `risk_on_r_series_ranker_contract_blocked`
3. `risk_on_r_series_ranker_leakage_blocked`
4. `risk_on_r_series_ranker_source_blocked`
5. `risk_on_r_series_ranker_binding_drift_blocked`

## 13. OOS Separability

Report OOS separability for:

1. bridge-positive vs bridge-negative.
2. non-fast-fail vs fast-fail 10d.
3. non-false-repair vs false-repair 20d.
4. 120d winner vs non-winner as secondary.
5. E1-missed captured vs still missed.

Metrics:

1. AUC.
2. PR-AUC.
3. top-decile lift.
4. calibration by score decile.
5. sample count by split / regime / family.

Cells with event_n < 30 must be `diagnostic_only`.

Cells with 30 <= event_n < 100 must be `low_power_caution`.

Experiment C must inherit the more conservative status between upstream Experiment B cell status and its own selected-arm sample status.

## 14. Required Outputs

Write outputs under:

```text
outputs/publishable/tables/risk_on_r_series_bridge_ranker/
outputs/publishable/reports/risk_on_r_series_bridge_ranker/
outputs/manifests/risk_on_r_series_bridge_ranker/
outputs/local_cache/risk_on_r_series_bridge_ranker/
```

Required tables:

1. `risk_on_r_series_ranker_arm_frontier.csv`
2. `risk_on_r_series_ranker_selected_events.csv`
3. `risk_on_r_series_ranker_rejected_events.csv`
4. `risk_on_r_series_ranker_feature_spec.csv`
5. `risk_on_r_series_ranker_family_budget_audit.csv`
6. `risk_on_r_series_ranker_density_fast_fail_readout.csv`
7. `risk_on_r_series_ranker_bridge_recall_readout.csv`
8. `risk_on_r_series_ranker_transition_reselection_readout.csv`
9. `risk_on_r_series_ranker_deoverlap_audit.csv`
10. `risk_on_r_series_ranker_oos_separability.csv`
11. `risk_on_r_series_ranker_decision_tiers.csv`
12. `risk_on_r_series_ranker_failure_distribution.csv`
13. `risk_on_r_series_ranker_source_caveat_audit.csv`
14. `risk_on_r_series_ranker_label_policy_audit.csv`

Required report:

1. `risk_on_r_series_bridge_ranker_report.md`

Required manifest:

1. `risk_on_r_series_bridge_ranker_manifest.json`

## 15. Output Schemas

`risk_on_r_series_ranker_arm_frontier.csv` must include:

1. `arm_id`
2. `arm_type`
3. `target_regime`
4. `source_family_ids`
5. `r2_policy`
6. `upstream_a_decision`
7. `upstream_b_decision`
8. `source_caveat_status`
9. `train_selected_event_count`
10. `validation_selected_event_count`
11. `robustness_selected_event_count`
12. `density_vs_e1_full_denominator`
13. `events_per_instrument_year_mean`
14. `events_per_instrument_year_p95`
15. `density_granularity`
16. `rolling_10d_duplicate_rate`
17. `adjacent_gap_median`
18. `cross_family_collision_rate`
19. `single_family_selected_share_max`
20. `train_incremental_recall_over_e1`
21. `train_bridge_delta_vs_e1`
22. `robustness_incremental_recall_over_e1`
23. `robustness_bridge_delta_vs_e1`
24. `fast_fail_10d_rate`
25. `fast_fail_10d_excess_vs_e1`
26. `false_repair_20d_rate`
27. `false_repair_20d_excess_vs_e1`
28. `direct_entry_gate_pass`
29. `feature_source_gate_pass`
30. `target_regime_decision_tier`
31. `final_decision`
32. `ranker_arm_status`
33. `train_cell_sample_status`
34. `robustness_cell_sample_status`
35. `sample_status_gate_pass`
36. `borderline_pass_flag`
37. `borderline_metric_names`
38. `failure_reason`

`final_decision` in this table must be the manifest-level decision copied unchanged to every row.

`risk_on_r_series_ranker_selected_events.csv` must include:

1. `arm_id`
2. `candidate_scope_id`
3. `canonical_event_id`
4. `instrument`
5. `event_t0_date`
6. `event_split`
7. `market_regime_bucket`
8. `family_id`
9. `mechanism_cluster_id`
10. `rank_score`
11. `rank_score_available`
12. `selected_rank`
13. `selected_reason`
14. `r2_policy`
15. `cooldown_rule`
16. `family_budget_rule`
17. `feature_source_only`
18. `source_caveat_status`

`risk_on_r_series_ranker_rejected_events.csv` must include:

1. `arm_id`
2. `candidate_scope_id`
3. `canonical_event_id`
4. `instrument`
5. `event_t0_date`
6. `event_split`
7. `market_regime_bucket`
8. `family_id`
9. `rank_score`
10. `rank_score_available`
11. `rejection_reason`
12. `blocked_by_cooldown`
13. `blocked_by_family_budget`
14. `blocked_by_collision`
15. `blocked_by_fast_fail_rejector`

The selected / rejected event tables must not expose future label columns as features. If labels are joined for audit, they must be in readout-only tables and marked with `label_only = true`.

`risk_on_r_series_ranker_feature_spec.csv` must include:

1. `feature_name`
2. `feature_family`
3. `source_column`
4. `source_artifact`
5. `asof_policy`
6. `allowed_as_feature`
7. `blocked_reason`
8. `missing_policy`
9. `point_in_time_safe`
10. `label_leakage_check_status`

`risk_on_r_series_ranker_family_budget_audit.csv` must include:

1. `arm_id`
2. `target_regime`
3. `family_id`
4. `budget_rule`
5. `budget_cap`
6. `candidate_event_count`
7. `selected_event_count`
8. `selected_share`
9. `single_family_share_gate_pass`
10. `r2_policy`

`risk_on_r_series_ranker_density_fast_fail_readout.csv` must include:

1. `arm_id`
2. `target_regime`
3. `split`
4. `market_regime_bucket`
5. `selected_event_count`
6. `density_granularity`
7. `density_reference_scope_id`
8. `events_per_instrument_year_mean`
9. `events_per_instrument_year_p95`
10. `density_vs_e1_full_denominator`
11. `rolling_10d_duplicate_rate`
12. `adjacent_gap_median`
13. `fast_fail_10d_count`
14. `fast_fail_10d_rate`
15. `fast_fail_10d_excess_vs_e1`
16. `false_repair_20d_count`
17. `false_repair_20d_rate`
18. `false_repair_20d_excess_vs_e1`
19. `event_level_label_source_status`
20. `direct_entry_density_gate_pass`
21. `feature_source_density_gate_pass`

`risk_on_r_series_ranker_bridge_recall_readout.csv` must include:

1. `arm_id`
2. `target_regime`
3. `split`
4. `market_regime_bucket`
5. `episode_denominator_n`
6. `bridge_denominator_n`
7. `selected_event_count`
8. `pre_replay_any_recall`
9. `pre_replay_bridge_recall`
10. `incremental_recall_over_e1`
11. `incremental_captures_over_e1`
12. `e1_missed_capture_n`
13. `retention_source_status`
14. `cell_sample_status`

`risk_on_r_series_ranker_transition_reselection_readout.csv` must include:

1. `arm_id`
2. `split`
3. `candidate_scope_id`
4. `family_id`
5. `transition_role`
6. `pre_replay_any_recall`
7. `pre_replay_bridge_recall`
8. `fast_fail_10d_rate`
9. `false_repair_20d_rate`
10. `target_regime_decision_tier`
11. `t4_t7_negative_control_status`

`risk_on_r_series_ranker_deoverlap_audit.csv` must include:

1. `arm_id`
2. `target_regime`
3. `instrument`
4. `event_t0_date`
5. `pre_deoverlap_event_count`
6. `post_deoverlap_selected_count`
7. `suppressed_event_count`
8. `suppression_rule`
9. `cross_family_collision_count`
10. `cooldown_rule`
11. `family_budget_rule`

`risk_on_r_series_ranker_oos_separability.csv` must include:

1. `arm_id`
2. `target_regime`
3. `split`
4. `label_name`
5. `sample_count`
6. `positive_count`
7. `auc`
8. `pr_auc`
9. `top_decile_lift`
10. `calibration_status`
11. `oos_separability_status`

`risk_on_r_series_ranker_decision_tiers.csv` must include:

1. `arm_id`
2. `target_regime`
3. `target_regime_decision_tier`
4. `final_decision`
5. `direct_entry_gate_pass`
6. `feature_source_gate_pass`
7. `density_gate_pass`
8. `p95_gate_pass`
9. `duplicate_gate_pass`
10. `bridge_gate_pass`
11. `recall_gate_pass`
12. `fast_fail_gate_pass`
13. `false_repair_gate_pass`
14. `selected_share_gate_pass`
15. `sample_status_gate_pass`
16. `oos_separability_status`
17. `borderline_pass_flag`
18. `borderline_metric_names`
19. `supported_usage`
20. `failure_reason`

`final_decision` in this table must be the manifest-level decision copied unchanged to every row.

`risk_on_r_series_ranker_failure_distribution.csv` must include:

1. `arm_id`
2. `target_regime`
3. `failure_reason`
4. `failure_count`
5. `failure_share`
6. `blocking_level`
7. `example_scope_ids`

`risk_on_r_series_ranker_label_policy_audit.csv` must include:

1. `field_name`
2. `field_source`
3. `allowed_as_feature`
4. `allowed_as_label`
5. `allowed_as_readout`
6. `reason`

`risk_on_r_series_ranker_source_caveat_audit.csv` must include:

1. `source_artifact`
2. `source_decision`
3. `source_status`
4. `affects_direct_entry`
5. `affects_feature_source`
6. `required_report_caveat`

## 16. Report Requirements

`risk_on_r_series_bridge_ranker_report.md` must include:

1. one-page conclusion with manifest-level final decision and per-regime decision tiers.
2. A/B input and manifest audit.
3. explicit source-caveat statement.
4. Experiment A density / fast-fail contract inheritance.
5. scope reconstruction audit from `candidate_scope_mapping_contract.csv`.
6. Experiment B result alignment, including R6 transition evidence, risk_on R6 evidence, T4/T7 demotion, and R-core collision.
7. fixed C density gate thresholds and whether each selected arm used `selected_arm_recomputed`.
8. per-regime decision tiers and manifest-level final decision.
9. R2 policy.
10. source family summary.
11. arm frontier.
12. selected arm explanation.
13. direct-entry gate replay by `risk_on` and `transition`.
14. feature-source gate replay by `risk_on` and `transition`.
15. density / p95 / duplicate / collision readout.
16. fast-fail 10d and false-repair 20d diagnostic readout.
17. bridge / recall readout.
18. OOS separability readout.
19. T4/T7 negative-control readout.
20. risk_off diagnostic-only readout.
21. negative-result explanation if no tier passes.
22. downstream recommendation for replay, meta-label, or no-candidate.
23. binding drift audit comparing §3 values to loaded A/B source values.
24. pre-replay label policy for `bridge_positive_event_or_episode_capture`.
25. borderline pass metrics, especially any robustness bridge / recall deltas within 1 percentage point of thresholds.

The report must not describe pre-replay recall / bridge as post-filter trading signal retention.

## 17. Tests

At minimum, tests must verify:

1. missing Experiment A contract blocks the run.
2. missing required A/B manifest or table blocks the run.
3. missing `candidate_scope_mapping_contract.csv` or `candidate_scope_reconstructability_audit.csv` blocks event-level deterministic arms.
4. event-level selected/rejected rows are reconstructed only through the scope mapping contract.
5. aggregate-only compression arms cannot pass direct-entry or feature-source gates.
6. allowed source-caveated upstream decisions do not block deterministic arms.
7. source-caveated upstream decisions force manifest-level `risk_on_r_series_ranker_source_caveated_complete`.
8. target-regime tiers can differ between `risk_on` and `transition`.
9. validation / robustness are never used for threshold tuning.
10. missing optional local cache blocks only supervised arms.
11. R2 policy is explicit.
12. raw R-core can appear only as diagnostic / stress arm and cannot be selected directly.
13. T4/T7 cannot become default transition recall families without passing explicit gate rules.
14. direct-entry tier requires the 35% selected-share gate.
15. feature-source tier uses the 65% selected-share gate and cannot be labeled entry.
16. direct-entry density gate uses `density_vs_e1_full_denominator <= 1.50`, mean <= 2.824076, p95 <= 7.056048, and rolling 10d duplicate <= 15.00%.
17. feature-source density gate uses `density_vs_e1_full_denominator <= 2.50` and p95 <= 12.226065.
18. no future return, episode membership, fast-fail label, false-repair label, or bridge label enters the t0 feature matrix.
19. fast-fail 10d and false-repair 20d are present as diagnostic labels / readouts.
20. selected and rejected event tables do not expose future labels as features.
21. deterministic arms run when supervised arms are blocked.
22. no-candidate still writes frontier, scores if available, and failure distribution.
23. cell sample status inherits the more conservative status between B and C.
24. validation risk_on is diagnostic-only.
25. validation transition is low-power diagnostic-only.
26. risk_off rows are diagnostic-only and never enter final candidate support.
27. density calculations for selected arms use the Experiment A contract verbatim.
28. `density_granularity` is populated from the allowed enum and no B scope-level density is misrepresented as split/regime density.
29. every required output table in §14 has the schema columns specified in §15.
30. report explicitly states that recall / bridge conclusions are pre-replay unless C implements replay.
31. direct-entry gate fails when required train or robustness cell status is not `sufficient_for_cell_readout`.
32. `bridge_positive_event_or_episode_capture` is sourced only from pre-replay capture sources and never requires post-replay episode membership.
33. metrics within 1 percentage point of gate thresholds set `borderline_pass_flag` and list `borderline_metric_names`.
34. load-time binding checks verify §3 hardcoded values against current A/B source tables and return `risk_on_r_series_ranker_binding_drift_blocked` on drift.
35. `final_decision` values in row-level tables are constant copies of the manifest-level decision.
