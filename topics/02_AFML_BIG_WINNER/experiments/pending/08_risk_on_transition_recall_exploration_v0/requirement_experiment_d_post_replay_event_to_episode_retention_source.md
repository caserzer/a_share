# Requirement: Experiment D - Post-Replay Event-to-Episode Retention Source

## 1. Background

Experiments A / B / C all converged on the same source limitation: recall and bridge readouts are currently `pre_replay_capture_only`. They show whether a candidate scope had at least one pre-filter event inside a target episode window, but they do not show whether bridge / winner retention survives after executable replay, 10d horizon completeness, fast-fail filtering, or false-repair filtering.

Experiment C also changed the research priority:

1. `risk_on` is no longer primarily a density-compression problem. R-series bridge signal exists, but fast-fail / false-repair cost remains too high.
2. `transition` is no longer a T4 / T7 or raw R-core repair problem. Current arms do not produce stable robustness bridge retention.
3. Any future risk_on cost rejector, meta-label source, or transition family rediscovery needs a reliable event-to-episode replay source before it can claim post-filter retention.

Experiment D therefore builds and audits the missing source layer:

```text
event-level selected / candidate events -> frozen 06 target episode windows -> replay-policy retention readouts
```

This is a source-building and audit experiment. It must not train a rejector, select a trading union, or claim direct-entry support.

## 2. Primary Question

```text
Can we create a hash-audited post-replay event-to-episode membership source
that supports post-filter retention readouts for E1, 08 family scopes, and
Experiment C arms, without using future episode membership to generate events
or tune selection rules?
```

The required output is a reusable retention source for downstream work:

1. risk_on post-filter cost rejector / meta-label design.
2. transition family rediscovery.
3. A / B / C report refreshes that need post-replay retention instead of `pre_replay_capture_only`.

## 3. Required Upstream Decisions

Experiment D must read the current A / B / C outputs and enforce their source caveats.

Allowed upstream final decisions:

1. Experiment A: `density_fast_fail_audit_complete`
2. Experiment A: `density_fast_fail_audit_partial_source_complete`
3. Experiment B: `regime_family_matrix_complete`
4. Experiment B: `regime_family_matrix_source_caveated_complete`
5. Experiment C: `risk_on_r_series_ranker_complete`
6. Experiment C: `risk_on_r_series_ranker_source_caveated_complete`

If any required upstream manifest is missing or reports an unrecognized decision, return:

```text
post_replay_retention_source_input_blocked
```

The following A / B / C findings are binding:

| finding | binding implication |
| --- | --- |
| A: E1 is sparse and clean enough, with 0.19% rolling 10d duplicate and 14.52% fast-fail | E1 remains baseline; do not treat E1 as a density failure |
| A/B: T4/T7 is low density but weak recall and high fast-fail | T4/T7 remains negative control / quality-filter context |
| A/B: R-core union collision is cross-family, not single-family repetition | replay must preserve family / scope identities; do not collapse R scopes into one raw union |
| C: direct-entry pass 0 and feature-source pass 0 | D must not convert C arms into entry support |
| C: risk_on top arms retain bridge but fail fast-fail / false-repair | D must prioritize post-filter retention by replay policy |
| C: transition robustness bridge is unstable | D must report transition retention, but not use it to select a family |

## 4. Non-Goals

Experiment D must not:

1. train a supervised model.
2. tune thresholds, quotas, cooldowns, or family budgets.
3. create new event candidates from target episode membership.
4. filter events by target episode membership before computing density or failure labels.
5. use `failure_10_label`, `event_false_repair_20d_label`, `event_big_winner_120d_label`, or episode membership as t0 features.
6. claim implementable direct-entry support for an oracle replay policy that uses future labels.
7. overwrite A / B / C outputs.
8. redefine density, fast-fail, false-repair, split/regime sample status, or candidate scope mapping.

## 5. Required Inputs

Read-only upstream manifests and reports:

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_audit_report.md
outputs/publishable/reports/regime_family_matrix/regime_family_matrix_report.md
outputs/publishable/reports/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_report.md
discussion.md
```

Frozen target episode denominator:

```text
../06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/local_cache/topn_big_winner_episode_reference.parquet
../06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/manifests/run_manifest.json
../06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/publishable/tables/topn_big_winner_episode_reference_summary.csv
```

08 required local cache sources:

```text
outputs/local_cache/candidate_family_capture.parquet
outputs/local_cache/candidate_family_event_labels.parquet
```

08 optional local cache source, for future downstream context only:

```text
outputs/local_cache/cross_section_feature_panel.parquet
```

`cross_section_feature_panel.parquet` must not be required to build event-to-episode membership, replay retention, or final completeness. Its absence must be reported as optional context missing, not as an input block.

08 publishable event sources:

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_10d_retention_by_split_regime.csv
outputs/publishable/tables/regime_family_matrix/regime_family_performance_matrix.csv
outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_selected_events.csv.gz
outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_rejected_events.csv.gz
outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_bridge_recall_readout.csv
outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_decision_tiers.csv
```

07 baseline sources:

```text
../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json
../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_canonical_event_labels.parquet
```

The 07 sources are hard requirements for `07_E1_only`, because E1 is the baseline and all E1-missed diagnostics depend on it. If D cannot reconstruct `07_E1_only`, the final decision must be `post_replay_retention_source_input_blocked`.

`07_full_union` is a backfill / context scope. If `07_E1_only` is complete but only `07_full_union` cannot be reconstructed, D may return `post_replay_retention_source_source_caveated_complete`.

If any required local-cache source above is absent, D may still produce a source audit, but it must not claim post-replay completeness. The final decision must be source-caveated or input-blocked according to Section 15.

## 6. Episode Window Contract

The source of truth for target episode identity is the frozen 06 Top-N episode reference. It must provide exactly 2,493 target episodes unless the upstream 06 manifest explicitly changes the denominator.

The source of truth for replay window boundaries is `candidate_family_capture.parquet`, because the 06 episode reference provides the frozen episode denominator but not all replay window fields required by D.

06-to-D field crosswalk:

| 06 episode reference field | D canonical field | notes |
| --- | --- | --- |
| `episode_id` | `target_episode_id` | primary denominator key |
| `instrument` | `instrument` | must match exactly |
| `split` | `episode_split` | D output must use `episode_split` |
| `episode_low_date` | `episode_low_date` | denominator identity / audit |
| `episode_high_date` | `episode_high_date` | denominator identity / audit |
| `first_ema60_reclaim_date` | audit-only 06 reference date | must not be substituted for `first_50pct_touch_date` |

`first_50pct_touch_date`, `window_start_pos`, `window_end_pos`, `board_bucket`, and `market_regime_bucket` must come from `candidate_family_capture.parquet` after joining to the canonicalized 06 keys. If either source already uses the D canonical field names, the implementation must still emit the crosswalk audit so denominator reconciliation is explicit.

Experiment D must build a distinct episode-window table from `candidate_family_capture.parquet` and cross-check it against the 06 episode reference. `candidate_family_capture.parquet` is scope-expanded: a valid upstream file can contain one row per scope for the same `target_episode_id` / `window`. D must therefore:

1. de-duplicate episode windows by `target_episode_id` and `window`.
2. assert that all duplicate source rows agree on required episode-window keys and boundaries.
3. record the duplicate source row count in the episode-window audit.
4. keep only one denominator row per `target_episode_id` / `window` after validation.

If duplicated source rows disagree on any required episode-window key or boundary, the affected row must be marked:

```text
episode_window_conflict_blocked
```

and retained in denominator audits.

Required episode-window keys:

1. `target_episode_id`
2. `instrument`
3. `episode_low_date`
4. `episode_high_date`
5. `first_50pct_touch_date`
6. `episode_split`
7. `market_regime_bucket`
8. `board_bucket`
9. `window`
10. `window_start_pos`
11. `window_end_pos`

Before a full run, D must preflight `candidate_family_capture.parquet` and assert that all required episode-window keys above are present as columns after any documented alias normalization. Missing columns are contract failures. Missing values in present columns are row-level `episode_window_source_blocked` conditions.

Required windows:

1. `low_to_first_50pct`: main bridge-positive recall window.
2. `low_to_high`: full episode capture context.

Window-bound inclusiveness:

1. `low_to_first_50pct` is inclusive of `window_start_pos` and exclusive of the first 50% touch boundary unless the upstream capture source explicitly encodes `window_end_pos` as the last pre-touch trading position.
2. The implementation must honor the already-materialized `window_start_pos` / `window_end_pos` from `candidate_family_capture.parquet` and report `window_end_inclusive_flag`.
3. `low_to_high` is inclusive of both `episode_low_date` and `episode_high_date` when the materialized positions are available.
4. The reconciliation audit must include the chosen inclusiveness flags because 0.01 percentage point tolerance is not meaningful if D changes boundary semantics.

If `first_50pct_touch_date`, `window_start_pos`, or `window_end_pos` is missing for a target episode, the affected episode-window row must be marked:

```text
episode_window_source_blocked
```

The row must remain in denominator audits. It must not be silently dropped.

## 7. Event Anchor Contract

Event replay must use the same executable anchor policy as Experiment A:

1. Primary anchor: `trade_open_pos` / `trade_open_date`.
2. Fallback anchor: `event_t0_pos` / `event_t0_date` only when the row is non-executable or next-open is unavailable.
3. Every fallback row must carry `event_anchor_source = event_t0_fallback_non_executable_audit`.
4. Executable rows must carry `event_anchor_source = trade_open_executable`.

The post-replay membership source must store both raw t0 fields and replay anchor fields:

1. `event_t0_date`
2. `event_t0_pos`
3. `trade_open_date`
4. `trade_open_pos`
5. `replay_anchor_date`
6. `replay_anchor_pos`
7. `event_anchor_source`

No membership calculation may use information after `replay_anchor_date` except in explicitly labeled audit-only replay policies.

Before applying the anchor policy, every event source must be normalized into an enriched event envelope with:

1. `source_kind`
2. `source_id`
3. `canonical_event_id`
4. source-native event identifier when available
5. all raw t0 fields
6. all executable trade-open fields
7. all replay-policy label fields required by Section 10

For C arms, `risk_on_r_series_ranker_selected_events.csv.gz` and `risk_on_r_series_ranker_rejected_events.csv.gz` are selection readouts, not complete replay event tables. D must enrich these rows by joining back to the 08 canonical event / event-label sources using `canonical_event_id`. If a selected or rejected C row cannot be enriched to the replay anchor and required label fields, the row must be retained in source coverage audit with:

```text
c_arm_event_enrichment_blocked
```

The affected arm / split / regime cell must be marked `source_blocked` or more conservative. Implementation must not crash or silently drop unmatched selected C rows.

If a C arm resolves only to an aggregate frontier / compression pool that is marked `aggregate_frontier_only_no_event_membership` in `candidate_scope_mapping_contract.csv`, D must not reconstruct its membership from the aggregate rule. The arm must be retained with `c_arm_event_enrichment_blocked` and a source coverage row explaining that no event-membership source exists.

For 07 baseline rows, D must enrich through the 07 canonical event and label sources listed in Section 5. Cross-source joins between 07 and 08 are forbidden unless explicitly used as reconciliation diagnostics.

## 8. Event-to-Episode Membership Definition

For each candidate event and target episode-window row, membership is true only when all conditions hold:

1. same `instrument`.
2. event `replay_anchor_pos` is not null.
3. `replay_anchor_pos` falls inside the materialized replay window using the Section 6 boundary-inclusiveness contract.
4. the candidate event belongs to a reconstructable candidate scope, C arm, or baseline event source.

The comparison in rule 3 must use the `window_end_inclusive_flag` from Section 6. If `window_end_inclusive_flag = false`, the implementation must use `window_start_pos <= replay_anchor_pos < window_end_pos`.

The membership table must not use `captured_target_episode_id_first` from event labels as the primary join key. That field can be used only as a reconciliation audit because it is a label artifact, not the canonical replay join.

Events may map to more than one episode only if the frozen 06 denominator contains overlapping target episode windows for the same instrument. Such rows must be flagged:

```text
multi_episode_membership_overlap
```

and summarized in the source coverage audit.

Episode-level metrics and event-level metrics intentionally have different counting units. If one event maps to two valid episode windows, captured episode counts may increase by 2 while `selected_event_n` increases by 1. This is expected behavior and must not be treated as a reconciliation failure.

## 9. Candidate Scope and Arm Coverage

Minimum hard-required scope coverage:

1. `07_E1_only`
2. `08_selected_T4_T7_union`
3. `08_T4_gated`
4. `08_T7_gated`
5. `08_R1_event_regime_gated`
6. `08_R2_event_regime_gated`
7. `08_R6_event_regime_gated`
8. `08_R7_event_regime_gated`
9. `08_R8_event_regime_gated`
10. `08_R_core_event_regime_gated`

Required caveated / context scope coverage:

1. `07_full_union`

If `07_full_union` is missing while `07_E1_only` and all hard-required 08 scopes are complete, D may return source-caveated complete. If `07_E1_only` is missing, D must return input-blocked because E1-missed retention cannot be constructed.

Minimum required C arm coverage:

1. every `arm_id` in `risk_on_r_series_ranker_decision_tiers.csv`.
2. `risk_on` and `transition` target regimes.
3. `risk_off` rows as diagnostic-only if they exist in C output.

For C arms, selected membership must come from `risk_on_r_series_ranker_selected_events.csv.gz`, not from reconstructing the arm rules ad hoc. Rejected rows may be used only for false-negative / suppression diagnostics.

All required `candidate_scope_id` event sets must be reconstructed from `candidate_scope_mapping_contract.csv`, using its declared source path and row-filter contract. D must not hand-code scope membership rules for E1, T4/T7, R-series, or R-core if the mapping contract already defines them.

If a required scope has `scope_mapping_status` or reconstructability status other than `reconstructable_event_membership`, D must not approximate the scope. The affected scope must be retained in output tables with:

```text
scope_mapping_source_blocked
```

The source coverage audit must report the mapping-contract row used for every required scope.

## 10. Replay Policies

Experiment D must implement and report these replay policies:

| replay_policy_id | description | uses future labels | admission use |
| --- | --- | --- | --- |
| `pre_replay_capture_only` | D recomputes pre-replay membership from its own event envelope and replay-window basis, then reconciles against A / C upstream artifacts | no | no |
| `post_replay_executable_horizon_complete` | retains events with executable replay anchor and complete label horizons required by the specific readout | no future outcome labels, but uses label completeness | source audit only |
| `post_replay_non_fast_fail_10d_oracle` | removes events where `failure_10_label == true` | yes | audit-only |
| `post_replay_non_false_repair_20d_oracle` | removes events where `event_false_repair_20d_label == true` | yes | audit-only |
| `post_replay_non_fast_fail_and_non_false_repair_oracle` | removes both fast-fail 10d and false-repair 20d events | yes | audit-only |

All oracle policies must carry:

```text
oracle_future_label_used = true
entry_support_allowed = false
```

If downstream uses any oracle replay as direct-entry support, the consuming experiment must fail its leakage audit.

All policies in D, including non-oracle policies, must emit `entry_support_allowed = false`. D is a source-building experiment only.

Required label completeness is policy-specific:

1. 10d fast-fail readouts require non-null `failure_10_label`.
2. 20d false-repair readouts require non-null `event_false_repair_20d_label`.
3. 120d big-winner readouts require non-null `event_big_winner_120d_label`.
4. bridge / any-capture retention based only on replay-window membership must not be blocked by a 120d label that is irrelevant to the requested readout.

For reconciliation:

1. scope-level `pre_replay_capture_only` metrics must be recomputed by D using the same source event set, split / regime cell, instrument match, canonicalized episode window, and pre-filter event anchor basis used to build D membership. Upstream A artifacts supply `upstream_value`, not the D output value.
2. C-arm `pre_replay_capture_only` metrics must be recomputed by D from C selected events after enrichment, then reconciled against Experiment C `risk_on_r_series_ranker_bridge_recall_readout.csv`. D must not try to infer C-arm pre-replay recall directly from A scope-level capture unless it is explicitly labeled as a diagnostic approximation.
3. If A or C marks a source as partial and the relevant cell is not comparable under the same membership basis, D must emit `reconciliation_status = not_comparable_source_partial` rather than failing the run.

## 11. Retention Metrics

For each `candidate_scope_id` / `arm_id`, split, regime, window, and replay policy, report:

1. `target_episode_denominator_n`
2. `bridge_episode_denominator_n`
3. `pre_replay_any_captured_episode_n`
4. `post_replay_any_captured_episode_n`
5. `pre_replay_any_recall`
6. `post_replay_any_recall`
7. `any_recall_retention`
8. `pre_replay_bridge_captured_episode_n`
9. `post_replay_bridge_captured_episode_n`
10. `pre_replay_bridge_recall`
11. `post_replay_bridge_recall`
12. `bridge_recall_retention`
13. `e1_missed_pre_replay_capture_n`
14. `e1_missed_post_replay_capture_n`
15. `e1_missed_capture_retention`
16. `selected_event_n`
17. `post_replay_event_n`
18. `filtered_event_n`
19. `filter_drop_rate`
20. `cell_sample_status`
21. `retention_source_status`

Retention ratios must be null when the denominator is zero. They must not be filled with 0.

For multi-episode membership overlaps, episode-level capture metrics count distinct captured episodes, while event-level metrics count distinct events. These counts are not expected to sum to the same value.

## 12. Sample Status

Use the same conservative status rules as Experiment B / C:

1. `sufficient_for_cell_readout`: all denominators required by the specific window / metric are at least 100.
2. `low_power_caution`: any required denominator is at least 30 and below 100.
3. `diagnostic_only`: any required denominator is below 30, or source completeness is insufficient.
4. `source_blocked`: required event membership, episode-window, or label source is unavailable.

Window-specific denominator rules:

1. `low_to_first_50pct` bridge readouts require both `target_episode_denominator_n` and `bridge_episode_denominator_n`.
2. `low_to_high` any-capture readouts require `target_episode_denominator_n`; `bridge_episode_denominator_n` may be null when no bridge-specific denominator is defined for that full-window context.
3. E1-missed readouts require `e1_missed_episode_n` in addition to the relevant target / bridge denominator.

When upstream A / B / C marks a split / regime cell as more conservative than the D denominator rule, D must use the more conservative status.

## 13. Required Outputs

Report outputs:

```text
outputs/publishable/reports/post_replay_event_to_episode_retention_source/post_replay_retention_source_contract.md
outputs/publishable/reports/post_replay_event_to_episode_retention_source/post_replay_retention_source_report.md
```

Manifest:

```text
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
```

Publishable tables:

```text
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_episode_window_audit.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_source_coverage_audit.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_scope_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_arm_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_policy_effect_summary.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_e1_missed_retention_summary.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_reconciliation_against_a_b_c.csv
```

Local-only raw membership output:

```text
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
```

If the raw membership file is too large for normal local handling, it may be partitioned by `split` / `market_regime_bucket` / `source_kind`. It must remain under `outputs/local_cache/**` and must not be committed.

## 14. Required Output Schemas

`post_replay_episode_window_audit.csv` must include:

1. `target_episode_id`
2. `instrument`
3. `episode_split`
4. `market_regime_bucket`
5. `window`
6. `window_start_pos`
7. `window_end_pos`
8. `episode_low_date`
9. `first_50pct_touch_date`
10. `episode_high_date`
11. `episode_window_source_status`
12. `denominator_included_flag`
13. `window_end_inclusive_flag`
14. `source_path`
15. `source_hash`
16. `source_row_count_before_dedup`
17. `dedup_conflict_flag`
18. `dedup_conflict_fields`

`post_replay_source_coverage_audit.csv` must include:

1. `source_kind`
2. `source_id`
3. `required_flag`
4. `source_path`
5. `source_hash`
6. `row_count`
7. `expected_key_count`
8. `matched_key_count`
9. `unmatched_key_count`
10. `source_status`
11. `blocking_flag`

`post_replay_scope_retention_by_split_regime.csv` must include all Section 11 retention metrics plus:

1. `candidate_scope_id`
2. `window`
3. `replay_policy_id`
4. `oracle_future_label_used`
5. `entry_support_allowed`
6. `pre_replay_source_reference`
7. `post_replay_membership_source_hash`
8. `membership_basis`

`post_replay_arm_retention_by_split_regime.csv` must include all Section 11 retention metrics plus:

1. `arm_id`
2. `target_regime`
3. `arm_family_set`
4. `window`
5. `replay_policy_id`
6. `oracle_future_label_used`
7. `entry_support_allowed`
8. `c_arm_tier`
9. `c_arm_final_decision_copy`
10. `membership_basis`

`post_replay_policy_effect_summary.csv` must include:

1. `source_kind`
2. `source_id`
3. `split`
4. `market_regime_bucket`
5. `window`
6. `base_policy_id`
7. `replay_policy_id`
8. `event_drop_n`
9. `event_drop_rate`
10. `any_recall_delta_pp`
11. `bridge_recall_delta_pp`
12. `e1_missed_capture_delta_n`
13. `policy_effect_interpretation`

`post_replay_e1_missed_retention_summary.csv` must include:

1. `source_kind`
2. `source_id`
3. `split`
4. `market_regime_bucket`
5. `window`
6. `replay_policy_id`
7. `e1_episode_denominator_n`
8. `e1_pre_replay_captured_episode_n`
9. `e1_post_replay_captured_episode_n`
10. `e1_missed_episode_n`
11. `source_pre_replay_captures_e1_missed_n`
12. `source_post_replay_captures_e1_missed_n`
13. `e1_missed_capture_retention`
14. `incremental_post_replay_capture_over_e1_n`
15. `incremental_post_replay_capture_over_e1_rate`
16. `cell_sample_status`
17. `retention_source_status`

`post_replay_label_leakage_audit.csv` must include:

1. `field_name`
2. `field_source`
3. `allowed_for_membership_join`
4. `allowed_for_replay_filter`
5. `allowed_as_t0_feature`
6. `uses_future_information`
7. `allowed_downstream_use`
8. `leakage_status`

`post_replay_reconciliation_against_a_b_c.csv` must include:

1. `source_experiment`
2. `source_artifact`
3. `source_metric`
4. `scope_or_arm_id`
5. `split`
6. `market_regime_bucket`
7. `upstream_value`
8. `d_recomputed_pre_replay_value`
9. `absolute_diff`
10. `tolerance`
11. `reconciliation_status`
12. `membership_basis`
13. `source_partial_flag`

Allowed `reconciliation_status` values:

1. `pass`
2. `within_tolerance_with_rounding`
3. `not_comparable_source_partial`
4. `not_comparable_membership_basis`
5. `missing_upstream_value`
6. `fail`

## 15. Final Decisions

Allowed final decisions:

```text
post_replay_retention_source_complete
post_replay_retention_source_source_caveated_complete
post_replay_retention_source_input_blocked
post_replay_retention_source_contract_blocked
post_replay_retention_source_leakage_blocked
```

Return `post_replay_retention_source_complete` only when:

1. all required input sources are present and hash-audited.
2. the frozen target episode denominator reconciles to A / B / C denominators.
3. event-to-episode membership is materialized locally.
4. scope and C arm post-replay retention tables are complete for required rows.
5. pre-replay reconciliation against A / B / C passes tolerance.
6. leakage audit passes.

Local raw membership is intentionally local-only. It may remain uncommitted under `outputs/local_cache/**` without forcing `source_caveated_complete`, provided the manifest records its path, partition layout if any, row count, schema fingerprint, and content hash or deterministic partition hashes.

Return `post_replay_retention_source_source_caveated_complete` when:

1. core scope retention is complete but some optional C arms, rejected-event diagnostics, or the `07_full_union` backfill scope is missing.
2. local raw membership is materialized but its hash / schema / partition metadata is incomplete.
3. post-replay retention is complete for risk_on but transition remains diagnostic due to sample / source status.

Return `post_replay_retention_source_input_blocked` when a hard dependency required to create membership is missing, including:

1. frozen 06 target episode reference.
2. distinct episode-window source.
3. candidate event labels required for replay policies.
4. candidate event sources required for minimum scope coverage.
5. 07 sources required to reconstruct `07_E1_only`.

Missing `07_full_union` alone must not trigger input-blocked if `07_E1_only` is complete.

Return `post_replay_retention_source_contract_blocked` when the required upstream source exists but violates D's contract, including:

1. episode-window duplicate rows disagree after de-duplication.
2. `candidate_scope_mapping_contract.csv` cannot reconstruct a required scope and no explicit source-blocked row is emitted.
3. a required publishable output is missing required schema columns.
4. manifest hashes or row counts cannot be reconciled to the produced outputs.

`not_comparable_source_partial` reconciliation rows must not trigger contract-blocked by themselves. They are allowed only when the relevant upstream source explicitly reports a partial source status.

Return `post_replay_retention_source_leakage_blocked` when:

1. episode membership is used to create, select, or rank candidate events.
2. oracle future labels are marked as implementable entry filters.
3. leakage audit finds any future label in t0 feature fields.

## 16. Report Requirements

The report must be written in Chinese and include:

1. final decision and source caveats.
2. exact input source table with path, row count, hash, required/optional status.
3. denominator reconciliation against 06 / A / B / C.
4. scope-level post-replay retention table.
5. C arm post-replay retention table, especially risk_on top arms and transition diagnostics.
6. policy effect summary: how much recall / bridge survives each replay policy.
7. explicit statement that oracle future-label replay is audit-only.
8. risk_on implication: whether post-filter retention is sufficient to justify a future cost rejector.
9. transition implication: whether post-filter retention changes or confirms the need for family rediscovery.
10. list of blocked or caveated cells.

The report must not describe any oracle policy as deployable.

## 17. Tests / Acceptance Checks

Minimum required checks:

1. required upstream manifests exist and decisions are in the allowed set.
2. 06 target episode denominator row count reconciles to 2,493 or reports an explicit upstream denominator drift.
3. 06 field crosswalk canonicalizes `episode_id -> target_episode_id` and `split -> episode_split`.
4. `candidate_family_capture.parquet` contains every required episode-window key after documented alias normalization.
5. distinct episode-window table has no duplicate `target_episode_id` / `window` rows after de-duplication.
6. duplicated `candidate_family_capture.parquet` source rows agree on every required episode-window key before de-duplication.
7. every denominator row has split and market regime.
8. window boundary inclusiveness is materialized as `window_end_inclusive_flag` and used in membership joins.
9. replay anchor policy matches Experiment A.
10. C selected and rejected rows are enriched through canonical / label sources by `canonical_event_id`; unmatched rows are audited and block only the affected cells.
11. C arms mapped only to `aggregate_frontier_only_no_event_membership` are marked `c_arm_event_enrichment_blocked` without reconstructing membership from aggregate rules.
12. raw event-to-episode membership uses instrument plus replay window bounds, not `captured_target_episode_id_first` as primary key.
13. no event candidate is generated from episode membership.
14. hard-required scopes are reconstructed from `candidate_scope_mapping_contract.csv` or explicitly source-blocked.
15. missing `07_E1_only` triggers input-blocked; missing `07_full_union` alone can only trigger source-caveated.
16. C arm selected events are sourced from C selected-events output, not rebuilt ad hoc.
17. C-arm pre-replay reconciliation uses Experiment C readout artifacts, not A scope-level capture as an arm proxy.
18. D recomputes pre-replay membership and uses A / C artifacts only as upstream comparison values.
19. `not_comparable_source_partial` reconciliation rows do not trigger contract-blocked when upstream A / C explicitly reports partial source status.
20. pre-replay scope recall reconciles against Experiment A within 0.01 percentage point where comparable.
21. pre-replay arm recall reconciles against Experiment C within 0.01 percentage point where comparable.
22. required label completeness is enforced per requested readout horizon, not globally across 10d / 20d / 120d.
23. all replay policies have `entry_support_allowed = false`.
24. oracle replay policies have `oracle_future_label_used = true`.
25. `failure_10_label`, false-repair labels, winner labels, and episode membership are absent from any t0 feature export.
26. retention ratios are null, not zero, when denominators are zero.
27. sample status uses the conservative A/B/C-compatible rule with window-specific denominator relevance.
28. multi-episode membership overlaps are counted and reported with distinct event-level and episode-level counting.
29. absence of optional `cross_section_feature_panel.parquet` does not trigger input-blocked or source-caveated by itself.
30. local raw membership output is under `outputs/local_cache/**`.
31. publishable tables contain no oversized uncompressed raw membership dump.
32. output manifest hashes every publishable artifact and local raw membership metadata.
33. report states that post-replay source unblocks future rejector design but does not itself train a rejector.
34. `git diff --check` passes for the requirement and generated publishable markdown.
