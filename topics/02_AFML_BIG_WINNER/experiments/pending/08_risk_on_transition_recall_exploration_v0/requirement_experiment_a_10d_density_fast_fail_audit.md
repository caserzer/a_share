# Requirement: Experiment A - 10d Density / Fast-Fail Audit Replay

## 1. Background

07 / 08 reports contain several valid but different density readings:

1. formal full-denominator density: events per instrument-year and p95.
2. concentration diagnostics: family share / mechanism share.
3. episode-window diagnostics: event count inside a target episode or before-first-50pct window.

These readings must not be collapsed into one `density` concept. In particular, high whole-episode event count does not automatically mean high-frequency 10d executable event congestion. Experiment A freezes a single density / fast-fail caliber and replays 07 / 08 candidate pools under that caliber.

Experiment A is an audit / caliber-freezing experiment. It does not create a trading signal, does not train a model, and does not select a final entry union.

## 2. Primary Objectives

Experiment A must answer:

```text
Do the 07 / 08 candidate families remain too dense when density is evaluated
at executable event-day / rolling 10d fast-fail caliber, rather than only
by episode-window accumulation or 120d winner labels?
```

It must also produce the cross-experiment contract:

```text
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
```

Experiments B / C / D / E must reference this contract rather than redefining 10d density.

## 3. Non-Goals

Experiment A must not:

1. fit a ranker or rejector.
2. use validation / robustness to tune thresholds.
3. change 06 denominator, 07 artifacts, or 08 artifacts.
4. use target episode membership to generate events.
5. convert episode-window diagnostic thresholds into hard admission gates.
6. claim direct-entry support for any family or union.

## 4. Required Inputs

Read-only source artifacts:

1. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json`
2. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv`
3. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_instances.csv`
4. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_event_precision_label_readout.csv`
5. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_false_repair_diagnostic.csv`
6. `outputs/manifests/run_manifest.json`
7. `outputs/publishable/tables/candidate_family_canonical_events.csv.gz`
8. `outputs/publishable/tables/candidate_family_event_instances.csv.gz`
9. `outputs/publishable/tables/candidate_family_label_quality_readout.csv`
10. `outputs/publishable/tables/candidate_family_false_repair_diagnostic.csv`
11. `outputs/publishable/tables/candidate_family_density_summary.csv`
12. `outputs/publishable/tables/candidate_family_bridge_positive_recall.csv`
13. `outputs/publishable/tables/candidate_family_incremental_recall_over_e1.csv`
14. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_compression_frontier.csv`
15. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_threshold_sensitivity.csv`
16. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_recall_bridge_density_by_split.csv`
17. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_score_spec.csv`
18. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_source_pool_summary.csv`
19. `outputs/publishable/reports/discussion.md`
20. this requirement file.

Optional local-cache inputs may be used only if present and hash-auditable. If local cache is absent, Experiment A must still complete using publishable tables and mark any unavailable fields as `not_available_publishable_source`.

Event-level label inputs are optional but semantically important:

1. `outputs/local_cache/candidate_family_event_labels.parquet`
2. `../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_event_labels.parquet`, or an equivalent hash-audited 07 event-label artifact, if present.

Publishable aggregate label readouts may populate aggregate fast-fail rates by split / regime / scope. They must not be used to simulate event-level filtering or event-level retention. If event-level labels are unavailable, event-level oracle replay fields must be marked `not_available_publishable_source`.

Optional R-series membership inputs may be used only if present, non-empty, and schema-auditable:

1. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_selected_compressed_variants.csv`
2. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_compressed_canonical_events.csv`

Empty optional membership artifacts must be treated as absent, not as valid empty selections.

Retention and episode-window outputs require one of the following event-to-episode denominator sources:

1. frozen 06 episode reference with event-window boundaries, e.g. `topn_big_winner_episode_reference.parquet`, if available on the machine running the experiment.
2. 08 `candidate_family_capture.parquet`, if available on the machine running the experiment.
3. an equivalent hash-audited artifact that maps frozen 06 target episodes to split / regime / before-first-50pct windows.

These sources are hard dependencies for `candidate_10d_retention_by_split_regime.csv` and episode-window fields in `candidate_density_caliber_crosswalk.csv`. If they are unavailable, the run may still produce publishable-source density / fast-fail audit tables, but retention and episode-window fields must be marked:

```text
not_available_publishable_source
```

and the final decision must be `density_fast_fail_audit_partial_source_complete`, not `density_fast_fail_audit_complete`.

## 5. Input Gate

If a required source artifact is missing, unreadable, or schema-incompatible, the final decision must be:

```text
density_fast_fail_audit_input_blocked
```

The manifest must report:

1. missing path.
2. expected columns.
3. actual columns if available.
4. source artifact hash status.

Missing optional local cache must not block the audit. It only blocks fields that require unavailable event-level labels.

Missing frozen episode / capture source must not be silently ignored. It blocks retention replay and episode-window crosswalk fields, and must be reflected in:

1. `candidate_scope_reconstructability_audit.csv`
2. `density_fast_fail_audit_gate_summary.csv`
3. `density_fast_fail_audit_manifest.json`
4. final decision `density_fast_fail_audit_partial_source_complete`

## 6. Caliber Contract

Experiment A must write `density_fast_fail_caliber_contract.md` before any metric table. The contract is the only authoritative definition for downstream experiments.

The contract must freeze:

1. `event_key`: canonical event id if available; otherwise deterministic hash of `source_scope_id, instrument, event_t0_date, event_t0_pos`. `source_scope_id` must be derived explicitly as:
   - `candidate_scope_id` if present.
   - else `canonical_event_scope` if present.
   - else deterministic join of `source_experiment, candidate_scope_type, family_id, variant_id`.
2. `event_t0`: observable event date / position.
3. `event_execution_key`: next-open executable event row, with non-executable rows retained in audit denominators.
4. `event_window_anchor_pos` and `event_window_anchor_date`: the timing anchor for rolling density, adjacent gap, and uniqueness. Executable rows must use `trade_open_pos` / `trade_open_date`. Non-executable audit-only rows must remain in denominators and use `event_t0_pos` / `event_t0_date` with `event_window_anchor_status = non_executable_t0_fallback`.
5. `failure_10_complete`: horizon complete flag for 10-trading-day path after execution.
6. `failure_10_label`: fast-fail diagnostic label. If source only provides `false_repair_10d`, map it explicitly and preserve source column name.
7. `fast_fail_definition_id`: semantic source of the 10d failure readout. Allowed values include:
   - `failure_10_path`: forward 10d path failure label.
   - `false_repair_10d_derived`: repair-signal invalidation within 10d, not guaranteed semantically equivalent to `failure_10_path`.
   - `not_available_publishable_source`.
   The same output table may contain multiple definition ids only if every row records `fast_fail_definition_id` and `label_source_column`.
8. `failure_10_forward_label_only`: failure_10 / false_repair_10d are forward diagnostic labels used for audit / rejector training targets only. Experiment A replays existing events and must not alter event trigger time. Downstream B / C / D must not use these labels as entry-trigger features.
9. `formal_full_denominator_density`: events per instrument-year over the full evaluated source denominator, not a regime-only denominator.
10. `denominator_source_id`: the evaluated universe / instrument-year source used by each candidate scope.
11. `instrument_years`: the exact denominator used in density calculations. Minimum definition: `instrument_years = evaluated_instrument_days / 252`, aligned with 06 / 07 universe-years-252 convention. If a source uses a different trading-day convention, it must be recorded in `denominator_source_id` and marked ratio-incompatible unless reconciled.
12. `denominator_compatibility_flag`: whether two candidate scopes can be ratio-compared for gate purposes. Cross-source ratios such as 07 vs 08 may be reported only as diagnostic when this flag is false.
13. `rolling_10d_window_count_self_included`: same-instrument / same-candidate-scope event count in `[event_window_anchor_pos, event_window_anchor_pos + 10 trading days]`, including the anchor event, calculated after canonicalization and before target-episode filtering.
14. `rolling_10d_neighbor_count_ex_self`: `rolling_10d_window_count_self_included - 1`; duplicate flags and duplicate rates must use this ex-self count.
15. `rolling_20d_window_count_self_included` and `rolling_20d_neighbor_count_ex_self` with the same event-window anchor convention.
16. `event_uniqueness_10d`: AFML-style event uniqueness over the 10-trading-day label horizon. For each event, define its active interval as `[event_window_anchor_pos, event_window_anchor_pos + 10]`. At each trading position, compute concurrency only among active events with the same instrument and same candidate scope. Event uniqueness is the mean of `1 / concurrency_t` over the event's active interval. Report mean, median, p10, and low-uniqueness share by candidate scope. E1 uniqueness is expected to be very high because E1 is sparse; it is a reference anchor, not the alert baseline for expanded candidate families.
17. `adjacent_gap`: `event_window_anchor_pos` difference to previous kept event for the same instrument and same candidate scope.
18. `episode_window_density`: diagnostic only; never an admission hard fail gate.
19. train-only threshold freeze rules.
20. validation / robustness read-only rules.
21. treatment of censored, horizon-incomplete, and non-executable rows.

The contract must explicitly reject direct adoption of the episode-interval diagnostic's suggested hard gates:

```text
risk_on episode event_count_median <= 2
risk_on episode event_count_top10 <= 4
episode adjacent_gap_median >= 10 trading days
```

These thresholds are allowed only as `diagnostic_alert` because they depend on target episode / before-first-50pct windows and can conflate long-spaced stage events with 10d event congestion.

## 7. Candidate Scopes

Experiment A must replay at least:

1. `07_E1_only`
2. `07_E1_plus_E3`
3. `07_full_union`
4. `08_selected_T4_T7_union`
5. `08_T4_gated`
6. `08_T7_gated`
7. `08_R_core_event_regime_gated`
8. `08_R1_event_regime_gated`
9. `08_R2_event_regime_gated`
10. `08_R6_event_regime_gated`
11. `08_R7_event_regime_gated`
12. `08_R8_event_regime_gated`
13. R-series compression frontier arms listed in `risk_on_r_series_compression_frontier.csv`.

Experiment A must materialize the exact source mapping in `candidate_scope_mapping_contract.csv` before computing metrics. Minimum required mappings:

| output `candidate_scope_id` | source artifact | source row filter | canonicalization rule |
| --- | --- | --- | --- |
| `07_E1_only` | 07 canonical events | `triggered_channels` contains `E1_early_ema60_repair` | canonical rows by `canonical_event_id` / `event_id` |
| `07_E1_plus_E3` | 07 canonical events | `triggered_channels` contains `E1_early_ema60_repair` or `E3_rank_persistence` | canonical rows by `canonical_event_id` / `event_id` |
| `07_full_union` | 07 canonical events | recommended union rows; if no explicit flag exists, all rows in the 07 canonical publishable table | canonical rows by `canonical_event_id` / `event_id` |
| `08_selected_T4_T7_union` | 08 canonical events | `triggered_family_variants` contains the train-selected T4 / T7 `event_regime_gated` variants materialized in 08 `selected_candidate_union` | canonical rows by `canonical_event_id` / `event_id` |
| `08_T4_gated` | 08 canonical events | `family_id == T4_entropy_compression_then_directional_expansion` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_T7_gated` | 08 canonical events | `family_id == T7_board_relative_strength_break` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R_core_event_regime_gated` | 08 canonical events | `family_id` in R1 / R2 / R6 / R7 / R8 and `variant_id == event_regime_gated` | canonical union by instrument / event anchor |
| `08_R1_event_regime_gated` | 08 canonical events | `family_id == R1_relative_strength_breakout` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R2_event_regime_gated` | 08 canonical events | `family_id == R2_near_high_volume_expansion` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R6_event_regime_gated` | 08 canonical events | `family_id == R6_market_breadth_thrust` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R7_event_regime_gated` | 08 canonical events | `family_id == R7_cross_sectional_momentum_rank_jump` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R8_event_regime_gated` | 08 canonical events | `family_id == R8_persistent_distance_above_ema` and `variant_id == event_regime_gated` | canonical rows by `canonical_event_id` / `event_id` |
| `08_R_compression_arm::<compression_arm_id>` | R-series frontier plus score spec / source pool | deterministic arm policy when membership is reconstructable | arm-selected canonical rows; otherwise aggregate-only crosswalk |

If a listed source row filter produces zero rows, the scope must be marked `empty_scope_from_source_filter` and audited separately from missing / unreconstructable inputs.

If a scope cannot be reconstructed from publishable tables, output a row with:

```text
scope_status = not_reconstructable_from_publishable_source
```

and do not silently drop it.

R-series compression frontier arms require special handling. `risk_on_r_series_compression_frontier.csv` is an arm-level frontier table and may not contain selected event membership. Deterministic reconstruction is allowed only when all of the following hold:

1. the arm's `threshold_policy` and `score_spec_id` are available.
2. `risk_on_r_series_score_spec.csv` identifies every score field and threshold needed by the arm.
3. the source event table contains every required t0-visible score field.
4. `risk_on_r_series_source_pool_summary.csv` identifies the source family / variant policy.
5. the implementation can reproduce the arm's published `canonical_event_count` within an explicitly reported tolerance.

For each frontier arm:

1. If event membership can be reconstructed from source events plus the arm's deterministic threshold policy, output full 10d density / gap / fast-fail metrics.
2. If an explicit selected-event membership artifact exists, use it and record its path / hash.
3. If only aggregate frontier metrics are available, output aggregate crosswalk fields only and set:

```text
scope_status = aggregate_frontier_only_no_event_membership
```

4. Aggregate-only frontier arms must not be included in rolling 10d density, adjacent gap, fast-fail event-level readout, or hard-gate comparisons.
5. If deterministic reconstruction count does not reconcile to the published arm count, set `scope_status = reconstructed_membership_count_mismatch` and exclude the arm from hard-gate comparisons.

## 8. Required Outputs

Write all Experiment A outputs under:

```text
outputs/publishable/tables/density_fast_fail_audit/
outputs/publishable/reports/density_fast_fail_audit/
outputs/manifests/density_fast_fail_audit/
```

Required tables:

1. `candidate_10d_density_summary.csv`
2. `candidate_10d_fast_fail_readout.csv`
3. `candidate_10d_retention_by_split_regime.csv`
4. `candidate_10d_density_vs_episode_density_comparison.csv`
5. `candidate_adjacent_event_gap_diagnostic.csv`
6. `candidate_10d_uniqueness_diagnostic.csv`
7. `candidate_density_caliber_crosswalk.csv`
8. `candidate_scope_reconstructability_audit.csv`
9. `density_fast_fail_audit_gate_summary.csv`
10. `candidate_scope_mapping_contract.csv`

Required reports:

1. `density_fast_fail_caliber_contract.md`
2. `density_fast_fail_audit_report.md`

Required manifest:

1. `density_fast_fail_audit_manifest.json`

## 9. Table Schemas

`candidate_10d_density_summary.csv` must include:

1. `candidate_scope_id`
2. `candidate_scope_type`
3. `source_experiment`
4. `event_count`
5. `executable_event_count`
6. `failure_10_complete_event_count`
7. `event_window_anchor_policy_id`
8. `non_executable_t0_fallback_event_count`
9. `denominator_source_id`
10. `instrument_years`
11. `denominator_compatibility_group`
12. `events_per_instrument_year_mean`
13. `events_per_instrument_year_p95`
14. `rolling_10d_window_count_self_included_mean`
15. `rolling_10d_neighbor_count_ex_self_mean`
16. `rolling_10d_duplicate_event_count`
17. `rolling_10d_duplicate_rate`
18. `rolling_20d_window_count_self_included_mean`
19. `rolling_20d_neighbor_count_ex_self_mean`
20. `rolling_20d_duplicate_event_count`
21. `rolling_20d_duplicate_rate`
22. `event_uniqueness_concurrency_scope`
23. `event_uniqueness_10d_mean`
24. `event_uniqueness_10d_median`
25. `event_uniqueness_10d_p10`
26. `event_uniqueness_10d_low_share`
27. `same_day_duplicate_rate`
28. `density_vs_07_E1_only`
29. `density_vs_07_E1_only_compatibility_flag`
30. `density_vs_08_E1_recomputed`
31. `density_vs_08_E1_recomputed_compatibility_flag`
32. `scope_status`

`candidate_10d_fast_fail_readout.csv` must include:

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
14. `fast_fail_definition_comparable_to_failure_10_path`
15. `label_mapping_status`
16. `event_level_label_source_status`

`candidate_10d_retention_by_split_regime.csv` must include:

1. `candidate_scope_id`
2. `retention_replay_id`
3. `retention_replay_definition`
4. `replay_uses_future_label`
5. `episode_split`
6. `market_regime_bucket`
7. `target_episode_denominator`
8. `pre_replay_any_recall`
9. `post_replay_any_recall`
10. `any_recall_retention`
11. `pre_replay_bridge_recall`
12. `post_replay_bridge_recall`
13. `bridge_recall_retention`
14. `e1_missed_capture_retention`
15. `event_level_label_source_status`
16. `cell_sample_status`
17. `retention_source_status`
18. `episode_capture_source_path`
19. `episode_capture_source_hash`

Allowed `retention_replay_id` values:

1. `execution_horizon_complete_only`: retains executable rows with auditable 10d horizon completeness. This replay does not use future failure labels.
2. `audit_oracle_non_fast_fail_only`: removes events whose auditable `failure_10_label` / mapped `false_repair_10d` is true. This replay uses future labels and is audit-only; it must not be described as an implementable entry filter or direct-entry support.
3. `pre_replay_capture_only`: reports the existing pre-replay episode capture cells when episode capture exists but event-to-episode replay membership is unavailable. Post-replay fields must remain null and this row must not be described as a filter replay.
4. `not_available_publishable_source`: required event-level label, episode-capture source, or scope capture source is unavailable.

`candidate_adjacent_event_gap_diagnostic.csv` must include:

1. `candidate_scope_id`
2. `event_split`
3. `market_regime_bucket`
4. `instrument_count`
5. `gap_sample_count`
6. `gap_anchor_policy_id`
7. `adjacent_gap_p10`
8. `adjacent_gap_median`
9. `adjacent_gap_p90`
10. `gap_lt_5d_rate`
11. `gap_lt_10d_rate`
12. `gap_ge_20d_rate`
13. `diagnostic_alert_flag`

`candidate_10d_uniqueness_diagnostic.csv` must include:

1. `candidate_scope_id`
2. `event_split`
3. `market_regime_bucket`
4. `event_count`
5. `executable_event_count`
6. `active_interval_definition`
7. `active_interval_horizon_trading_days`
8. `concurrency_scope`
9. `concurrency_mean`
10. `concurrency_p95`
11. `event_uniqueness_10d_mean`
12. `event_uniqueness_10d_median`
13. `event_uniqueness_10d_p10`
14. `event_uniqueness_10d_low_share`
15. `low_uniqueness_threshold`
16. `uniqueness_diagnostic_alert_flag`

`candidate_density_caliber_crosswalk.csv` must include one row per candidate scope and compare:

1. formal full-denominator density.
2. denominator source id and compatibility group.
3. whether cross-source ratios are gate-eligible or diagnostic-only.
4. family / mechanism concentration.
5. episode-window event count median / top10.
6. rolling 10d executable density with self-included and ex-self counts separated.
7. 10d event uniqueness and concurrency.
8. adjacent gap distribution.
9. final hard-gate status.
10. final diagnostic-alert status.

`candidate_10d_density_vs_episode_density_comparison.csv` must include:

1. `candidate_scope_id`
2. `episode_split`
3. `market_regime_bucket`
4. `episode_window_metric_status`
5. `episode_event_count_mean`
6. `episode_event_count_median`
7. `episode_event_count_top10`
8. `episode_adjacent_gap_median`
9. `rolling_10d_duplicate_rate`
10. `event_uniqueness_10d_p10`
11. `executable_timing_alert_flag`
12. `episode_window_alert_flag`
13. `episode_window_used_as_hard_gate_flag`
14. `density_concept_mismatch_note`

`candidate_scope_mapping_contract.csv` must include one row per required scope / arm:

1. `candidate_scope_id`
2. `source_experiment`
3. `source_artifact_path`
4. `source_artifact_hash`
5. `source_row_filter`
6. `canonicalization_rule`
7. `expected_source_columns`
8. `actual_source_columns_hash`
9. `reconstructability_requirement`
10. `scope_mapping_status`

`candidate_scope_reconstructability_audit.csv` must include:

1. `candidate_scope_id`
2. `scope_status`
3. `source_artifact_path`
4. `source_artifact_hash_status`
5. `source_row_count`
6. `selected_event_count`
7. `published_reference_event_count`
8. `reconstructed_vs_published_count_difference`
9. `missing_required_columns`
10. `aggregate_only_reason`
11. `event_level_label_source_status`
12. `episode_capture_source_status`
13. `hard_gate_eligible_flag`
14. `notes`

`density_fast_fail_audit_gate_summary.csv` must include:

1. `gate_id`
2. `gate_type`
3. `candidate_scope_id`
4. `gate_status`
5. `metric_value`
6. `threshold_value`
7. `threshold_source`
8. `train_only_threshold_flag`
9. `denominator_compatibility_flag`
10. `uses_episode_window_density_flag`
11. `uses_future_label_flag`
12. `failure_reason`

`density_fast_fail_audit_manifest.json` must include:

1. run id, timestamp, code / config hash if available.
2. input path / hash / schema status for every required and optional artifact inspected.
3. `density_fast_fail_caliber_contract.md` hash.
4. output path / hash for every required table and report.
5. final decision and blocking / partial-completion reason.
6. explicit booleans for `event_level_labels_available`, `episode_capture_available`, and `r_series_membership_reconstructable`.

## 10. Gate Rules

Experiment A has no direct-entry support decision. It can only return audit status.

Hard fail gates:

1. required input missing or schema-incompatible.
2. failure_10 / false_repair_10d mapping cannot be audited for any scope required to produce event-level fast-fail readout. Aggregate-only frontier arms with `scope_status = aggregate_frontier_only_no_event_membership` are excluded from this hard fail.
3. contract not written before metric outputs.
4. metrics use episode-window density as hard fail.
5. validation / robustness used to tune thresholds.
6. cross-source density ratio used as a hard gate when `denominator_compatibility_flag == false`.
7. rolling duplicate metrics use self-included window counts without also providing ex-self duplicate counts.
8. mixed fast-fail definitions appear in the same readout table without row-level `fast_fail_definition_id` and `label_source_column`.
9. rolling density, adjacent gap, or uniqueness are computed from `event_t0_pos` for executable rows instead of `event_window_anchor_pos`.
10. uniqueness concurrency is computed across instruments instead of same-instrument / same-candidate-scope active intervals.
11. `audit_oracle_non_fast_fail_only` retention is used as an entry-support gate or described as an implementable t0 filter.

Diagnostic alerts:

1. episode-window event count median / top10 are report-only diagnostics and must not trigger an alert by themselves.
2. episode-window congestion alert may trigger only when episode-window count is high and at least one executable-timing diagnostic also fires: adjacent gap median < 10 trading days, rolling_10d_duplicate_rate materially high, or event_uniqueness_10d low.
3. adjacent gap median < 10 trading days.
4. rolling_10d_duplicate_rate materially above a predeclared same-source baseline.
5. fast_fail_10d_rate materially above a predeclared same-source baseline.
6. event_uniqueness_10d_p10 below a predeclared absolute low-uniqueness threshold.
7. event_uniqueness_10d_low_share above a predeclared absolute low-uniqueness-share threshold.
8. compression arm uniqueness fails to improve versus its own same-source uncompressed pool, when such a source-pool comparison is available.

Diagnostic alerts must be reported but must not by themselves set `density_blocked`.

## 11. Decisions

Allowed final decisions:

1. `density_fast_fail_audit_complete`
2. `density_fast_fail_audit_input_blocked`
3. `density_fast_fail_audit_contract_blocked`
4. `density_fast_fail_audit_partial_source_complete`

`partial_source_complete` is allowed only when publishable-source density / fast-fail metrics are complete but optional local-cache fields, frozen episode reference, or capture parquet required for retention / episode-window replay are unavailable.

## 12. Report Requirements

`density_fast_fail_audit_report.md` must contain:

1. one-page conclusion.
2. explicit explanation of why episode-level gates from the interval diagnostic are not adopted as hard gates.
3. crosswalk of density concepts.
4. scope reconstructability summary.
5. 07 E1 / E1+E3 / full-union comparison.
6. 08 selected T4/T7 comparison.
7. R-series family and compression-arm comparison.
8. adjacent gap findings by family / arm.
9. 10d event uniqueness findings by family / arm.
10. fast-fail 10d findings.
11. recommended inputs for Experiments B and C.
12. explicit warning when any retention replay uses future labels and is audit-only.

## 13. Tests

At minimum, tests must verify:

1. contract is generated before dependent tables.
2. episode-window diagnostic flags cannot set hard fail status.
3. rolling 10d duplicate count is per instrument and uses `event_window_anchor_pos` ordering.
4. non-executable rows are retained in audit denominators.
5. validation / robustness threshold values are read-only.
6. missing optional local cache does not block publishable-source audit.
7. 10d event uniqueness is computed from active horizon concurrency and is not replaced by rolling event count.
8. executable rolling density and adjacent gap use `event_window_anchor_pos`, not raw `event_t0_pos`.
9. uniqueness concurrency is same-instrument / same-candidate-scope only.
10. oracle non-fast-fail retention rows carry `replay_uses_future_label = true` and cannot set hard-gate pass.
11. every required candidate scope has a row in `candidate_scope_mapping_contract.csv` and `candidate_scope_reconstructability_audit.csv`.
12. aggregate-only R-series frontier arms are excluded from rolling 10d, adjacent-gap, uniqueness, and event-level fast-fail hard-gate comparisons.
