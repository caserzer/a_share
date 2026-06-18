# Requirement: 12A0 + 12A1 Winner Registry Lineage and R-core Backbone Demotion Audit

## 0. Path Baseline

This requirement uses the following path aliases:

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

Path resolution rules:

1. Paths beginning with `topics/` are repo-root-relative.
2. Paths beginning with `../` are relative to `EXPERIMENT_ROOT`.
3. Every consumed input artifact must be recorded in `input_artifact_audit.csv` with resolved absolute path, row count where applicable, sha256, and read status.
4. Local-cache parquet inputs are allowed. If a required local-cache parquet is missing, the run must fail closed instead of backfilling from aggregate tables.

## 1. Experiment Identity

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
run_id = 12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit
status = spec_frozen_pending_run
expected_entrypoint = src/run_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.py
expected_config = configs/config_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.yaml
expected_test_file = tests/test_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.py
```

This requirement combines the first two phases from `research_plan.md`:

```text
12A0: Winner Registry and Lineage Audit
12A1: R-core Backbone Demotion Audit
```

The combined run is intentional. 12A1 cannot be interpreted until 12A0 freezes the target population and proves that 06 episode targets and 11A2 PIT candidate rows are not being silently mixed.

## 2. Purpose

The run answers two questions:

```text
12A0:
  What are the frozen target populations for 12, and how do the
  06 risk_on episode registry and 11A2 PIT-valid winner rows align?

12A1:
  Given the 06 risk_on 428 episode target, is R-core a valid event
  backbone, or should it be demoted to feature source / recall benchmark?
```

The run is diagnostic-only. It does not create new state-change event families, does not train a model, does not tune `keep_0800`, does not change 10A/10B/10C/11 outputs, and does not authorize any trading policy.

## 3. Non-Goals

This requirement explicitly does not:

- generate B1/B2/B3 state-change candidate events;
- run multi-K winner/failure morphology;
- train winner/failure or fast-fail classifiers;
- run policy replay;
- select a buy/sell threshold;
- use future MFE, future return, or label-derived touch coordinates as features;
- treat 11A2 446 candidate rows as the full winner-episode target;
- treat raw R-core as the default modeling denominator.

## 4. Required Inputs

### 4.1 06 Episode Target Source

Primary source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/publishable/tables/topn_big_winner_episode_reference_summary.csv
```

Optional stronger source, if present:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/local_cache/topn_big_winner_episode_reference.parquet
```

Manifest source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/manifests/run_manifest.json
```

Required columns in the publishable CSV:

```text
episode_id
instrument
episode_low_date
episode_high_date
mfe_120
market_regime_bucket
split
duration_bucket
earliest_qualifying_low_date
earliest_qualifying_high_date
cluster_union_start_date
cluster_union_end_date
board_bucket
liquidity_money_20d
total_market_cap_cny
```

Frozen 12A0 episode target:

```text
selection_rule = market_regime_bucket == risk_on
expected_row_n = 428
record_unit = deduped_big_winner_episode
primary_key = episode_id
fallback_unique_key = instrument + episode_low_date + episode_high_date
```

If `episode_id` is not unique, or the filtered count is not 428, the run must stop with:

```text
decision = 12A0_input_blocked
block_reason = 06_risk_on_episode_registry_count_or_key_mismatch
```

### 4.2 11A2 PIT Candidate Winner Readout Source

Primary source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/mfe_basis_reconciliation.csv
```

Audit sources:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/denominator_contract_audit.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/outcome_class_count_audit.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/manifest_11A2_post_t0_archetype_path_divergence_diagnostic.json
```

Required `mfe_basis_reconciliation.csv` columns:

```text
row_id
instrument
event_t0_date
mfe_120d_frozen
mfe_120_recomputed
mfe_120_rel_diff
basis_status
```

Frozen 12A0 PIT candidate winner readout:

```text
selection_rule =
  numeric(mfe_120d_frozen) >= 0.5

expected_evaluated_denominator_row_n = 4665
expected_big_winner_row_n = 446
record_unit = risk_on_pit_valid_candidate_row
primary_key = row_id
```

This population intentionally follows the frozen 11A2 outcome label basis. Rows with `basis_status != ok` remain in the 446-row PIT candidate winner registry and must carry `lineage_status = basis_mismatch_kept_for_frozen_label_consistency`.

The `outcome_class_count_audit.csv` must contain:

```text
split = all
class_id = class_big_winner
row_n = 446
```

If the 4665 evaluated denominator or 446 frozen-label big-winner count cannot be reproduced, the run must stop with:

```text
decision = 12A0_input_blocked
block_reason = 11a2_pit_candidate_winner_count_mismatch
```

### 4.3 Current 12 Diagnostic Baseline Inputs

The current diagnostics are not the authoritative source for recomputation, but they are baseline fixtures. A valid run must recompute the same headline lineage numbers unless an explicit upstream artifact hash changed.

```text
outputs/diagnostics/winner_428_vs_446_alignment_summary.csv
outputs/diagnostics/06_topn_risk_on_big_winner_episodes_428.csv
outputs/diagnostics/11a2_risk_on_pit_valid_big_winner_rows_446.csv
outputs/diagnostics/06_428_episodes_to_11a2_446_rows_alignment.csv
outputs/diagnostics/11a2_446_rows_to_nearest_06_episode_alignment.csv
outputs/diagnostics/winner_episode_registry_divergence_lineage.csv
outputs/diagnostics/winner_428_vs_446_detail_manifest.csv
```

Required baseline headline values:

```text
06_risk_on_episodes = 428
11a2_446_rows = 446
11a2_rows_with_same_instrument_any_06_episode = 428
11a2_rows_with_same_instrument_risk_on_06_episode = 353
11a2_rows_exact_same_date_as_nearest_any_06_low = 0
11a2_rows_exact_same_date_as_nearest_risk_on_06_low = 0
11a2_rows_nearest_any_before_episode_low = 210
11a2_rows_nearest_any_inside_low_to_high_window = 167
11a2_rows_nearest_any_after_episode_high = 51
06_risk_on_episodes_with_any_11_row_pre120_to_high = 120
06_risk_on_episodes_without_11_row_pre120_to_high = 308
```

If recomputed values differ from these diagnostics while all upstream hashes are unchanged, final status must be no higher than:

```text
decision = 12A0_population_lineage_incomplete
```

Hash comparison policy:

```text
upstream_hash_reference = source manifest hash when manifest is present
upstream_hash_reference = direct artifact sha256 when manifest is absent
diagnostic_hash_reference = outputs/diagnostics/winner_428_vs_446_detail_manifest.csv
```

The runner must write one `input_artifact_audit.csv` row for each authoritative upstream source and one row for each diagnostic baseline artifact. If a baseline headline value changes and the relevant authoritative source hash also changed, the report must use:

```text
diagnostic_reconciliation_status = changed_with_upstream_hash_change
```

If the headline changes while the relevant authoritative source hash is unchanged, use:

```text
diagnostic_reconciliation_status = unexplained_diagnostic_drift
decision = 12A0_population_lineage_incomplete
```

### 4.4 08 R-core and Event Source Inputs

Primary R-family event source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
```

Scope contract:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
```

Optional bridge-ranker event arms:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_selected_events.csv.gz
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_density_fast_fail_readout.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
```

Event-label source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
```

Post-replay episode membership source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
```

`post_replay_event_episode_membership.parquet` is audit/readout-only in this requirement. It must not replace the 06 episode registry as the primary target.

### 4.5 10A / 10B Benchmark Inputs

10A:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/post_dedup_density_audit.csv
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/manifests/10A_density_rule_system_manifest.json
```

10B:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_threshold_frontier.csv
topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/outputs/manifests/10B_fast_fail_structural_gate_manifest.json
```

Frozen 10B benchmark operating point:

```text
model_id = regularized_logistic_fast_fail_10d_l2_v1
ablation_id = full
threshold_id = keep_9400
capacity_id = keep_9400
candidate_rejected_flag = true means filtered out by 10B
candidate_rejected_flag = false means retained after 10B safety gate
```

If 10B `keep_9400` cannot be reconstructed exactly from the score parquet and threshold frontier, A1 may still run raw R-core and 10A audits, but the 10B comparison must be marked:

```text
tenb_benchmark_status = not_available
```

### 4.6 09 Risk-on R-core Bridge and Label Completeness Inputs

09 source-pool bridge:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/input_audit/source_pool_reconstruction_audit.csv
```

09A label binding source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
```

09A label binding summary, if present:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
```

Required `source_pool_reconstruction_audit.csv` rows:

```text
source_pool_id = 08_R_core_event_regime_gated
source_row_count = 47914
selected_event_count = 30790
accepted_difference_reason = 08_A_H_accepted_r_core_minus_15
status = pass

source_pool_id = 08_R6_event_regime_gated
source_row_count = 16204
selected_event_count = 9260
status = pass
```

Required `selected_label_event_bindings.parquet` columns:

```text
sample_id
canonical_event_id
instrument
event_t0_date
event_split
source_pool_id
event_regime_bucket
denominator_id
horizon_complete_10d
horizon_complete_20d
horizon_complete_120d
selected_fast_fail_10_label
frozen_false_repair_20d_label
event_big_winner_120d_label
winner_censoring_status
censoring_status
```

Frozen risk-on R-core label binding counts:

```text
denominator_id = risk_on_r_core_horizon_complete
all = 30790
train = 16603
validation = 4457
robustness = 9730
horizon_complete_10d_all = 30737
horizon_complete_20d_all = 30737
horizon_complete_120d_all = 30731
```

This 09A binding is the authoritative horizon-completeness source for 10A/10B comparison arms. It must be joined by:

```text
canonical_event_id
input_denominator_id from 10A/10B == selected_label_event_bindings.denominator_id
```

If 09A binding is unavailable, 10A/10B bad-side readouts must be marked `bad_side_label_status = not_available`. Raw 08 R-core evaluation may still use the 08 candidate label source.

### 4.7 07 E1 Bad-Side Baseline Input

E1 bad-side baseline source:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/regime_family_matrix/regime_family_fast_fail_diagnostic_matrix.csv
```

Required baseline row filter for A1 gates:

```text
candidate_scope_id = 07_E1_only
family_id = E1_early_ema60_repair
event_split = same split as the evaluated arm, or all for split = all
market_regime_bucket = risk_on
```

Required fields:

```text
event_count
fast_fail_10d_count
fast_fail_10d_rate
false_repair_20d_count
false_repair_20d_rate
horizon_incomplete_10d_count
label_mapping_status
event_level_label_source_status
```

`market_regime_bucket = all` may be reported as context, but it must not be used for `*_excess_vs_07_E1_only` gates.

## 5. Core Keys and Time Fields

### 5.1 Episode Key

```text
episode_key = episode_id
fallback_episode_key = instrument + "|" + episode_low_date + "|" + episode_high_date
```

`episode_id` must be non-null and unique after the 06 risk_on filter.

### 5.2 11A2 PIT Candidate Row Key

```text
pit_candidate_row_key = row_id
fallback_pit_candidate_row_key = instrument + "|" + event_t0_date + "|" + row_id
```

`row_id` must be non-null and unique in `mfe_basis_reconciliation.csv`.

### 5.3 Event Key

For 08 candidate-family events:

```text
event_key = canonical_event_id
event_signal_date = event_t0_date
event_execution_date = trade_open_date when non_executable_next_open == false else event_t0_date
event_execution_pos = trade_open_pos when non_executable_next_open == false else event_t0_pos
```

For 10A events:

```text
event_key = input_event_key
canonical_event_id =
  parse fourth "|" component from input_event_key
  else sample_id only if sample_id matches one 08 canonical_event_id
  else null
canonical_event_id_source =
  input_event_key_component_4
  or sample_id_verified_against_08_canonical
  or unresolved
event_signal_date = event_t0_date
event_execution_date = event_window_anchor_date
event_execution_pos = event_window_anchor_pos
```

`sample_id` alone is not a stable cross-experiment canonical key. A 10A row may use `sample_id` as `canonical_event_id` only after a deterministic join to 08 `candidate_family_canonical_events.csv.gz` proves:

```text
sample_id == canonical_event_id
instrument matches
event_t0_date matches
```

If this proof fails, the 10A event remains valid for within-10A density and label readouts, but cross-experiment episode alignment must set:

```text
canonical_event_id_source = unresolved
alignment_status = canonical_event_unresolved
```

For 10B events:

```text
event_key = input_event_key
canonical_event_id = binding_canonical_event_id
event_signal_date = event_t0_date
```

All A1 episode-alignment metrics use `event_signal_date`. Execution fields are separate audit fields and must not shift episode timing unless a metric name explicitly contains `execution_anchor`.

### 5.4 Split Semantics

Two split fields must be kept separate:

```text
episode_split = split from the 06 episode registry
event_split = event_split from 08 events or split from 10A/10B rows
```

For split-specific episode recall, the denominator is filtered by `episode_split`. A capture event counts only when:

```text
event_split == episode_split
```

For split-specific event precision, the denominator is filtered by `event_split`. A matched episode counts only when:

```text
episode_split == event_split
```

For `split = all`, no split equality constraint is applied. Every split-specific output row must include:

```text
split_basis = episode_split for episode recall
split_basis = event_split for event precision and density
split_mismatch_candidate_n
```

## 6. A0 Winner Registry Lineage Contract

### 6.1 Episode Target Registry

Output:

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/episode_target_registry_06_risk_on_428.csv
```

Required columns:

```text
record_source
record_unit
selection_rule
source_relative_path
episode_id
instrument
episode_low_date
episode_high_date
first_50pct_date
pre120_calendar_start_date
low_to_high_sessions
low_to_high_calendar_days
mfe_120
split
duration_bucket
board_bucket
liquidity_money_20d
total_market_cap_cny
cluster_union_start_date
cluster_union_end_date
lineage_status
```

`first_50pct_date` policy:

```text
first_50pct_date =
  earliest_qualifying_high_date if present
  else episode_high_date
```

`pre120_calendar_start_date` policy:

```text
pre120_calendar_start_date = episode_low_date - 120 calendar days
```

This requirement intentionally uses 120 calendar days for the primary `pre120_to_high` audit because the current lineage diagnostics expose `within_120_calendar_days_before_low_to_high`. A later state-change generator may add a trading-day equivalent, but it must not replace this primary A0/A1 metric.

### 6.2 PIT Candidate Winner Registry

Output:

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/pit_candidate_winner_registry_11a2_446.csv
```

Required columns:

```text
record_source
record_unit
selection_rule
source_relative_path
row_id
instrument
event_t0_date
mfe_120d_frozen
mfe_120_recomputed
mfe_120_rel_diff
basis_status
analysis_regime_scope
pit_scope
lineage_status
```

Required count:

```text
row_n = 446
```

### 6.3 Population Bridge Audit

Output:

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/population_bridge_audit.csv
```

The audit must be produced in both directions:

1. 11A2 row -> nearest 06 episode.
2. 06 episode -> all matching 11A2 rows in `pre120_calendar_start_date` to `episode_high_date`.

Required 11A2-row-level columns:

```text
bridge_direction = 11a2_row_to_06_episode
row_id
instrument
event_t0_date
nearest_any_06_episode_id
nearest_any_06_episode_low_date
nearest_any_06_episode_high_date
nearest_any_market_regime_bucket
nearest_any_event_minus_episode_low_days
nearest_any_abs_event_minus_episode_low_days
nearest_any_event_vs_episode_window
nearest_risk_on_06_episode_id
nearest_risk_on_event_minus_episode_low_days
nearest_risk_on_abs_event_minus_episode_low_days
nearest_risk_on_event_vs_episode_window
inside_any_pre120_calendar_to_high_flag
inside_risk_on_pre120_calendar_to_high_flag
```

Nearest-episode tie break:

```text
1. smallest absolute event_t0_date - episode_low_date in calendar days
2. risk_on episode before non-risk_on episode for nearest_risk_on fields only
3. earliest episode_low_date
4. lexicographically smallest episode_id
```

Required 06-episode-level columns:

```text
bridge_direction = 06_episode_to_11a2_rows
episode_id
instrument
episode_low_date
episode_high_date
matching_11a2_winner_row_n_pre120_to_high
matching_11a2_row_ids
matching_11a2_event_t0_dates
matching_11a2_event_minus_low_days
episode_has_any_11a2_row_pre120_to_high_flag
```

Window category for `event_vs_episode_window`:

```text
before_pre120_calendar_start
pre120_before_episode_low
inside_low_to_high
after_episode_high
no_same_instrument_episode
```

### 6.4 Winner Registry Lineage Summary

Output:

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/winner_registry_lineage_summary.csv
```

Required rows:

```text
metric,value
06_risk_on_episodes,428
11a2_pit_valid_big_winner_rows,446
11a2_rows_with_same_instrument_any_06_episode,428
11a2_rows_with_same_instrument_risk_on_06_episode,353
11a2_rows_exact_same_date_as_nearest_any_06_low,0
11a2_rows_exact_same_date_as_nearest_risk_on_06_low,0
11a2_rows_nearest_any_before_episode_low,210
11a2_rows_nearest_any_inside_low_to_high_window,167
11a2_rows_nearest_any_after_episode_high,51
06_risk_on_episodes_with_any_11_row_pre120_to_high,120
06_risk_on_episodes_without_11_row_pre120_to_high,308
```

These values are a frozen baseline. The report must interpret them as population divergence, not as an implementation failure.

## 7. A1 R-core Backbone Demotion Contract

### 7.1 Required Arms

A1 must evaluate the following arms when inputs are available:

| arm_id | source | decision_role | event source rule |
| --- | --- | --- | --- |
| `08_R_core_event_regime_gated_raw` | 08 candidate canonical | `raw_backbone_decision_required` | `candidate_scope_id = 08_R_core_event_regime_gated` mapping rule |
| `08_R6_event_regime_gated_raw` | 08 candidate canonical | `comparison_non_blocking` | `candidate_scope_id = 08_R6_event_regime_gated` mapping rule |
| `10A_same_instrument_cooldown_10d_r_core` | 10A post-dedup bindings | `compression_comparison_non_blocking` | `population_id = 10A__same_instrument_cooldown_10d`, `denominator_id = post_dedup_risk_on_r_core`, `admission_status = admitted`, `readout_only_flag = false` |
| `10B_keep_9400_retained_after_fast_fail_gate` | 10B scores | `optional_compression_comparison` | 10A arm minus rows where 10B `candidate_rejected_flag = true` at frozen keep_9400 |
| `10B_keep_9400_rejected_fast_fail_bucket` | 10B scores | `optional_compression_comparison` | rows where 10B `candidate_rejected_flag = true` at frozen keep_9400 |
| `08C_baseline_r_core_no_ranker_diagnostic` | 08C selected events | `optional_historical_comparison` | `arm_id = baseline_r_core_no_ranker_diagnostic`, `target_regime = risk_on` |
| `08C_top_k_per_instrument_month_family_aware` | 08C selected events | `optional_historical_comparison` | `arm_id = top_k_per_instrument_month_family_aware`, `target_regime = risk_on` |
| `08C_cooldown_20d_ranked_within_bucket` | 08C selected events | `optional_historical_comparison` | `arm_id = cooldown_20d_ranked_within_bucket`, `target_regime = risk_on` |

Only `raw_backbone_decision_required` can block the final raw R-core demotion decision. Non-blocking comparison arms must still appear in `r_core_arm_input_status.csv`; if unavailable, use:

```text
arm_status = not_available
```

The report must then say which comparison is unavailable, but the raw R-core decision must still be computed if `08_R_core_event_regime_gated_raw` is valid.

### 7.2 Reconstructing 08 R-core Scope

For `08_R_core_event_regime_gated_raw`, the preferred reconstruction path is the 08 `candidate_scope_mapping_contract.csv` rule:

```text
triggered_family_variants contains any R1/R2/R6/R7/R8 event_regime_gated variant
```

The runner must not hand-code a different R-core definition if the mapping contract is present. It may implement the mapping rule only after verifying the contract row:

```text
candidate_scope_id = 08_R_core_event_regime_gated
scope_mapping_status = reconstructable_event_membership
```

Expected event count from reconstructability audit:

```text
08_R_core_event_regime_gated source_row_count = 47914
```

If the reconstructed count differs from the contract by more than 0 rows while hashes are unchanged, required-arm evaluation must fail with:

```text
decision = 12A1_r_core_population_blocked
block_reason = r_core_scope_reconstruction_mismatch
```

### 7.3 R-core Population Bridge

A1 must explicitly bridge the raw R-core source pool into later risk-on and compressed populations. The bridge is diagnostic and prevents denominator mixing.

Required bridge stages:

| bridge_stage_id | source population | target population | expected all count | authoritative source |
| --- | --- | --- | ---: | --- |
| `raw_08_r_core_contract` | 08 canonical events | `08_R_core_event_regime_gated` | `47914` | 08 reconstructability audit |
| `risk_on_horizon_complete_09a` | `08_R_core_event_regime_gated` | `risk_on_r_core_horizon_complete` | `30790` | 09 source-pool + 09A selected label binding |
| `post_dedup_10a_same_instrument` | `risk_on_r_core_horizon_complete` | `post_dedup_risk_on_r_core` at `10A__same_instrument_cooldown_10d` | `15802` | 10A population contract |

Required split counts:

| bridge_stage_id | train | validation | robustness |
| --- | ---: | ---: | ---: |
| `risk_on_horizon_complete_09a` | `16603` | `4457` | `9730` |
| `post_dedup_10a_same_instrument` | `8318` | `2514` | `4970` |

The raw R-core demotion decision is computed only on `08_R_core_event_regime_gated_raw`. 09A and 10A/10B populations are comparison / compression readouts and cannot replace the raw R-core denominator.

If any bridge count differs while source hashes are unchanged, output:

```text
population_bridge_status = denominator_bridge_mismatch
```

and prevent 10A/10B comparison from being interpreted as an upgrade to raw R-core support.

### 7.4 Episode Alignment Windows

For every arm event, match only same-instrument 06 risk_on episodes.

Primary windows:

```text
pre120_calendar_to_high:
  episode_low_date - 120 calendar days <= event_signal_date <= episode_high_date

low_to_high:
  episode_low_date <= event_signal_date <= episode_high_date

low_to_first_50pct:
  episode_low_date <= event_signal_date <= first_50pct_date
```

An event can match multiple episodes if episode windows overlap. The event-level precision numerator counts the event once if it matches at least one episode in the window. Multi-match rows must be counted in `multi_episode_event_overlap_n`.

### 7.5 Episode Recall Metrics

For each `arm_id`, `split`, and `window_id`:

```text
episode_recall = captured_episode_n / eligible_episode_n
eligible_episode_n = count distinct 06 episode_id in that split
captured_episode_n = eligible episodes with >= 1 arm event in the same-instrument window
split_basis = episode_split
```

Required window ids:

```text
pre120_calendar_to_high
low_to_high
low_to_first_50pct
```

Required split values:

```text
all
train
validation
robustness
```

### 7.6 Event Precision Metrics

For each `arm_id`, `split`, and `window_id`:

```text
event_precision = event_inside_window_n / event_n
outside_event_rate = 1 - event_precision
split_basis = event_split
```

`event_n` is distinct `event_key` in the arm and split. If the same canonical event appears multiple times due to source rows, collapse before computing precision and record the collapse in `r_core_event_key_uniqueness_audit.csv`.

Required extra timing metrics:

```text
event_before_pre120_calendar_start_rate
event_pre120_before_episode_low_rate
event_inside_low_to_high_rate
event_after_episode_high_rate
median_event_minus_low_days_for_matched_events
p25_event_minus_low_days_for_matched_events
p75_event_minus_low_days_for_matched_events
```

### 7.7 Density Metrics

Density must follow the 08 density caliber contract:

```text
event_window_anchor_pos = trade_open_pos for executable rows
event_window_anchor_pos = event_t0_pos only for non-executable audit rows
rolling_10d duplicate uses ex-self neighbor count
rolling_20d uses the same convention
```

Required density metrics:

```text
events_per_instrument_year_mean
events_per_instrument_year_p95
density_vs_e1_full_denominator
rolling_10d_duplicate_rate
rolling_20d_duplicate_rate
adjacent_gap_median
unique_instrument_n
unique_event_day_n
top_instrument_event_share
top_board_event_share
```

Formal density formulas:

```text
event_window_anchor_pos =
  trade_open_pos for executable rows
  else event_t0_pos for non-executable audit rows

density_basis_id = 08_full_evaluated_universe_years_252
denominator_source_id = 08_full_evaluated_universe_years_252
denominator_compatibility_group = 07_08_topn_proxy_universe_years_252

denominator_instrument_years =
  candidate_10d_density_summary.07_E1_only.instrument_years

events_per_instrument_year_mean =
  event_n / denominator_instrument_years

events_per_instrument_year_p95 =
  p95 over instruments using the same full-universe denominator basis when
  published exposure is available;
  otherwise p95 over active instruments using
  denominator_instrument_years / active_instrument_n as an approximation

density_vs_e1_full_denominator =
  events_per_instrument_year_mean / 07_E1_only.events_per_instrument_year_mean
```

The `07_E1_only` denominator must be read from 08 `candidate_10d_density_summary.csv` using the same `event_window_anchor_policy_id`, `denominator_source_id`, and `denominator_compatibility_group`. Do not recompute the primary density denominator from each arm's own min/max event span. Per-arm event-span density may be emitted only as an audit column and must not feed gates.

For 08 arms, `events_per_instrument_year_p95` must be read from the matching 08 density summary row when that row exists. For split-level rows without a published 08 p95, the runner may recompute an active-instrument approximation, but it must set:

```text
events_per_instrument_year_p95_basis_status =
  recomputed_split_active_instrument_year_approximation
density_denominator_status = compatible
```

If neither published p95 nor the active-instrument approximation can be reconstructed, set:

```text
events_per_instrument_year_p95_basis_status = not_reconstructable
density_denominator_status = incompatible
```

For 10A/10B comparison arms, 10A density tables are cross-check inputs. A1 must still emit the primary `density_vs_e1_full_denominator` on the 08 full-denominator basis so raw R-core, 09A, 10A, and 10B rows remain comparable.

If the denominator compatibility group differs, set:

```text
density_denominator_status = incompatible
density_status = denominator_incompatible
```

and the arm is not eligible for `12A1_r_core_backbone_supported`.

Otherwise set:

```text
density_denominator_status = compatible
```

If an arm already has a published density table using the 08/10A caliber, the runner may read it for cross-check, but it must still output a unified A1 density table using the same column names for every arm.

### 7.8 Bad-Side and Winner Readouts

For each arm and split, output:

```text
fast_fail_10d_count
fast_fail_10d_rate
fast_fail_10d_evaluable_event_n
fast_fail_10d_baseline_rate_07_E1_only
fast_fail_10d_excess_vs_07_E1_only
false_repair_20d_count
false_repair_20d_rate
false_repair_20d_evaluable_event_n
false_repair_20d_baseline_rate_07_E1_only
false_repair_20d_excess_vs_07_E1_only
winner_120_count
winner_120_rate
winner_120_evaluable_event_n
winner_retention_vs_raw_r_core
```

E1 baseline formulas:

```text
baseline row =
  regime_family_fast_fail_diagnostic_matrix
  where candidate_scope_id = 07_E1_only
    and family_id = E1_early_ema60_repair
    and event_split = arm split
    and market_regime_bucket = risk_on

fast_fail_10d_baseline_rate_07_E1_only = baseline.fast_fail_10d_rate
false_repair_20d_baseline_rate_07_E1_only = baseline.false_repair_20d_rate

fast_fail_10d_excess_vs_07_E1_only =
  fast_fail_10d_rate - fast_fail_10d_baseline_rate_07_E1_only

false_repair_20d_excess_vs_07_E1_only =
  false_repair_20d_rate - false_repair_20d_baseline_rate_07_E1_only
```

For `split = all`, use the E1 baseline row with `event_split = all` and `market_regime_bucket = risk_on`.

Labels must come from event-level frozen upstream labels:

| arm family | join key | required label fields | dedup policy |
| --- | --- | --- | --- |
| 08 arms | `canonical_event_id -> candidate_family_event_labels.event_id` | `failure_10_label`, `event_false_repair_20d_label`, `event_big_winner_120d_label` | prefer `label_scope = selected_candidate_union`, else `all_new_candidate_union`, else `event_instance`; fail if duplicate rows at the chosen priority disagree |
| 10A arms | `input_event_key` within `post_dedup_event_bindings.parquet`, plus `canonical_event_id + input_denominator_id` to 09A selected label binding | `selected_fast_fail_10_label`, `frozen_false_repair_20d_label`, `winner_120`; completeness from 09A `horizon_complete_*` | one admitted row per `input_event_key`; duplicates must collapse through `admitted_event_id` |
| 10B arms | `input_event_key` to 10B score parquet, plus 10A binding join for missing false-repair label, plus 09A completeness join | `selected_fast_fail_10_label`, `winner_120`, `frozen_false_repair_20d_label` from 10A if absent in 10B; completeness from 09A `horizon_complete_*` | filter exact frozen keep_9400 operating point before joining labels |

Label polarity:

```text
fast_fail_10d_positive = selected_fast_fail_10_label in {1, true} or failure_10_label in {1, true}
false_repair_20d_positive = frozen_false_repair_20d_label in {1, true} or event_false_repair_20d_label in {1, true}
winner_120_positive = winner_120 in {1, true} or event_big_winner_120d_label in {1, true}
```

Label completeness:

```text
fast_fail_complete =
  failure_10_complete == true
  or 09A.horizon_complete_10d == true

false_repair_20d_complete =
  event_false_repair_20d_complete == true
  or 09A.horizon_complete_20d == true

winner_120_complete =
  (horizon_complete_120d == true and main_barrier_label_complete == true)
  or 09A.horizon_complete_120d == true
```

Bad-side and winner rates must use complete/evaluable denominators:

```text
fast_fail_10d_rate = fast_fail_10d_count / fast_fail_10d_evaluable_event_n
false_repair_20d_rate = false_repair_20d_count / false_repair_20d_evaluable_event_n
winner_120_rate = winner_120_count / winner_120_evaluable_event_n
```

For 10A/10B arms, `fast_fail_10d_evaluable_event_n`, `false_repair_20d_evaluable_event_n`, and `winner_120_evaluable_event_n` must come from the 09A selected label binding completeness flags after joining by `canonical_event_id + input_denominator_id`. A missing completeness join is not a negative label.

Winner retention denominator:

```text
winner_retention_vs_raw_r_core =
  arm.winner_120_count / 08_R_core_event_regime_gated_raw.winner_120_count
  for the same split

winner_retention_vs_raw_r_core = 1.0 for 08_R_core_event_regime_gated_raw
winner_retention_vs_raw_r_core = null if either label source is unavailable
```

The runner must output label join coverage and completeness coverage by arm. If coverage is below `0.995` for any required label field or required completeness field, set:

```text
bad_side_label_status = incomplete
```

and the arm is not eligible for `12A1_r_core_backbone_supported`.

If a label source is missing for an arm, the arm may still report episode alignment and density, but bad-side status must be:

```text
bad_side_label_status = not_available
```

The arm is then not eligible for `12A1_r_core_backbone_supported`.

## 8. A1 Decision Gates

### 8.1 Backbone-Supported Gate

R-core can be retained as a supported backbone only if `08_R_core_event_regime_gated_raw` passes all of the following on both `train` and `robustness`:

| metric | threshold |
| --- | ---: |
| `episode_recall_pre120_calendar_to_high` | `>= 0.70` |
| `episode_recall_low_to_high` | `>= 0.45` |
| `event_precision_pre120_calendar_to_high` | `>= 0.25` |
| `event_precision_low_to_high` | `>= 0.15` |
| `outside_event_rate_low_to_high` | `<= 0.85` |
| `density_vs_e1_full_denominator` | `<= 2.50` |
| `events_per_instrument_year_p95` | `<= 10.00` |
| `rolling_10d_duplicate_rate` | `<= 0.20` |
| `fast_fail_10d_excess_vs_07_E1_only` | `<= 0.05` |
| `false_repair_20d_excess_vs_07_E1_only` | `<= 0.05` |
| `label_completeness_coverage` | `>= 0.995` |
| `density_denominator_status` | `compatible` |
| `event_after_episode_high_rate` | `<= 0.20` |

Validation is readout-only because 11/12 lineage evidence shows validation is underpowered for winner rows. However, if validation has enough rows and contradicts train/robustness by more than 15pp on episode recall or event precision, report `validation_conflict_flag = true`.

Validation has enough rows only when both are true for the relevant metric:

```text
validation_event_n >= 100
validation_eligible_episode_n >= 30
```

### 8.2 Feature-Source Minimum Gate

R-core can be demoted to `12A1_r_core_feature_source_only` only if it still passes the following minimum usability checks on both `train` and `robustness`:

| metric | threshold |
| --- | ---: |
| `episode_recall_pre120_calendar_to_high` | `>= 0.70` |
| `event_precision_pre120_calendar_to_high` | `>= 0.15` |
| `event_precision_low_to_high` | `>= 0.08` |
| `density_vs_e1_full_denominator` | `<= 4.00` |
| `events_per_instrument_year_p95` | `<= 20.00` |
| `rolling_10d_duplicate_rate` | `<= 0.35` |
| `bad_side_label_status` | `available` |
| `label_completeness_coverage` | `>= 0.995` |
| `density_denominator_status` | `compatible` |

If raw R-core has high recall but fails any Feature-Source Minimum Gate, it is a recall benchmark / stress pool, not a feature-source denominator.

### 8.3 Demotion States

The final A1 decision must be one of:

```text
12A1_r_core_backbone_supported
12A1_r_core_feature_source_only
12A1_r_core_recall_benchmark_only
12A1_r_core_population_blocked
```

Decision rules:

```text
if any raw_backbone_decision_required input for raw R-core reconstruction is blocked:
    decision = 12A1_r_core_population_blocked

elif raw R-core passes every Backbone-Supported Gate on train and robustness:
    decision = 12A1_r_core_backbone_supported

elif raw R-core passes every Feature-Source Minimum Gate on train and robustness
     but fails at least one Backbone-Supported Gate:
    decision = 12A1_r_core_feature_source_only

elif raw R-core episode_recall_pre120_calendar_to_high >= 0.50
     on train and robustness
     and (
       event_precision_low_to_high < 0.15
       or density_vs_e1_full_denominator > 2.50
       or rolling_10d_duplicate_rate > 0.20
       or bad_side_label_status != available
       or label_completeness_coverage < 0.995
       or density_denominator_status != compatible
     ):
    decision = 12A1_r_core_recall_benchmark_only

else:
    decision = 12A1_r_core_recall_benchmark_only
```

The decision text must explicitly state whether 10A/10B compression improves the operating point enough for feature-source use. 10A/10B cannot upgrade raw R-core to `r_core_backbone_supported`; they can only support a later compressed-population branch.

## 9. Required Outputs

All outputs must live under:

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/
outputs/publishable/reports/
outputs/manifests/
```

### 9.1 Tables

Required tables:

```text
input_artifact_audit.csv
episode_target_registry_06_risk_on_428.csv
pit_candidate_winner_registry_11a2_446.csv
population_bridge_audit.csv
winner_registry_lineage_summary.csv
r_core_population_bridge_summary.csv
r_core_arm_input_status.csv
r_core_arm_event_registry.csv.gz
r_core_episode_alignment_by_window.csv
r_core_event_precision_by_window.csv
r_core_density_badside_tradeoff.csv
r_core_event_key_uniqueness_audit.csv
r_core_demote_or_keep_decision.csv
```

### 9.2 `input_artifact_audit.csv`

Required columns:

```text
artifact_id
artifact_role
required_for_final_decision_flag
required_for_comparison_flag
relative_path
resolved_absolute_path
exists_flag
read_status
row_count
column_count
sha256
source_manifest_path
source_manifest_hash
expected_columns
actual_columns_hash
diagnostic_hash_reference_status
diagnostic_reconciliation_status
block_reason
```

Allowed `read_status` values:

```text
readable_tabular
readable_manifest
readable_binary
missing
schema_mismatch
read_error
```

### 9.3 `r_core_arm_input_status.csv`

Required columns:

```text
arm_id
decision_role
arm_status
event_source_path
label_source_path
event_source_row_n
reconstructed_event_n
expected_event_n
event_key_field
canonical_event_id_source_rule
reconstruction_status
event_key_uniqueness_status
label_join_status
label_join_coverage
label_completeness_join_status
label_completeness_coverage
tenb_benchmark_status
block_reason
```

Allowed `arm_status` values:

```text
available
not_available
blocked
available_with_label_gap
available_with_canonical_gap
```

### 9.4 `r_core_arm_event_registry.csv.gz`

Required columns:

```text
arm_id
decision_role
event_key
canonical_event_id
canonical_event_id_source
input_event_key
sample_id
source_event_id
instrument
event_signal_date
event_signal_pos
event_execution_date
event_execution_pos
event_execution_status
event_split
population_id
input_denominator_id
denominator_id
raw_event_status
admission_status
readout_only_flag
label_join_key
label_join_status
label_completeness_join_status
horizon_complete_10d
horizon_complete_20d
horizon_complete_120d
fast_fail_10d_label
false_repair_20d_label
winner_120_label
source_row_count_collapsed
event_registry_status
```

### 9.5 `r_core_population_bridge_summary.csv`

Required columns:

```text
bridge_stage_id
source_population_id
target_population_id
split
source_event_n
target_event_n
expected_target_event_n
retained_rate
authoritative_source_path
selection_rule
population_bridge_status
allowed_interpretation
block_reason
```

Required rows:

```text
raw_08_r_core_contract / all / expected_target_event_n = 47914
risk_on_horizon_complete_09a / all / expected_target_event_n = 30790
risk_on_horizon_complete_09a / train / expected_target_event_n = 16603
risk_on_horizon_complete_09a / validation / expected_target_event_n = 4457
risk_on_horizon_complete_09a / robustness / expected_target_event_n = 9730
post_dedup_10a_same_instrument / all / expected_target_event_n = 15802
post_dedup_10a_same_instrument / train / expected_target_event_n = 8318
post_dedup_10a_same_instrument / validation / expected_target_event_n = 2514
post_dedup_10a_same_instrument / robustness / expected_target_event_n = 4970
```

### 9.6 `r_core_event_key_uniqueness_audit.csv`

Required columns:

```text
arm_id
event_key
source_row_n
canonical_event_id_n
input_event_key_n
sample_id_n
representative_event_key
collapse_status
duplicate_reason
uniqueness_status
```

### 9.7 `r_core_episode_alignment_by_window.csv`

Required columns:

```text
arm_id
split
split_basis
window_id
eligible_episode_n
captured_episode_n
missed_episode_n
episode_recall
captured_episode_event_count_median
captured_episode_event_count_p95
first_event_minus_low_median
first_event_minus_low_p25
first_event_minus_low_p75
multi_episode_event_overlap_n
split_mismatch_candidate_n
alignment_status
```

### 9.8 `r_core_event_precision_by_window.csv`

Required columns:

```text
arm_id
split
split_basis
window_id
event_n
event_inside_window_n
event_precision
outside_event_rate
event_before_pre120_calendar_start_n
event_pre120_before_episode_low_n
event_inside_low_to_high_n
event_after_episode_high_n
event_before_pre120_calendar_start_rate
event_pre120_before_episode_low_rate
event_inside_low_to_high_rate
event_after_episode_high_rate
median_event_minus_low_days_for_matched_events
split_mismatch_candidate_n
precision_status
```

### 9.9 `r_core_density_badside_tradeoff.csv`

Required columns:

```text
arm_id
split
split_basis
event_n
unique_instrument_n
unique_event_day_n
density_basis_id
denominator_source_id
denominator_instrument_years
denominator_compatibility_group
events_per_instrument_year_mean
events_per_instrument_year_p95
events_per_instrument_year_p95_basis_status
density_vs_e1_full_denominator
density_vs_07_E1_only_compatibility_flag
density_denominator_status
rolling_10d_duplicate_rate
rolling_20d_duplicate_rate
adjacent_gap_median
fast_fail_10d_count
fast_fail_10d_rate
fast_fail_10d_evaluable_event_n
fast_fail_10d_baseline_rate_07_E1_only
fast_fail_10d_excess_vs_07_E1_only
false_repair_20d_count
false_repair_20d_rate
false_repair_20d_evaluable_event_n
false_repair_20d_baseline_rate_07_E1_only
false_repair_20d_excess_vs_07_E1_only
winner_120_count
winner_120_rate
winner_120_evaluable_event_n
winner_retention_vs_raw_r_core
bad_side_label_status
label_join_coverage
label_completeness_coverage
density_status
```

### 9.10 `r_core_demote_or_keep_decision.csv`

Required columns:

```text
decision
decision_reason
raw_r_core_train_gate_pass
raw_r_core_robustness_gate_pass
raw_r_core_validation_conflict_flag
population_bridge_status
episode_recall_gate_pass
event_precision_gate_pass
density_gate_pass
density_denominator_status
duplicate_gate_pass
bad_side_gate_pass
label_completeness_gate_pass
timing_gate_pass
feature_source_minimum_gate_pass
tena_compression_interpretation
tenb_safety_gate_interpretation
next_allowed_requirement
```

Allowed `next_allowed_requirement` values:

```text
requirement_12a2_state_change_backbone_candidate_generator.md
requirement_12a4_backbone_filter_layer_feasibility.md
stop_no_valid_backbone_for_morphology
```

### 9.11 Report

Required report:

```text
outputs/publishable/reports/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_report.md
```

The report must contain:

1. final decision;
2. A0 target registry counts;
3. 06 vs 11A2 lineage mismatch interpretation;
4. raw 47914 -> 09A 30790 -> 10A 15802 population bridge;
5. raw R-core episode recall and event precision;
6. 08-caliber density denominator status;
7. E1 risk_on bad-side baseline and label completeness coverage;
8. density / duplicate / bad-side tradeoff;
9. 10A/10B benchmark comparison;
10. explicit statement whether R-core remains backbone, feature source, or recall benchmark;
11. next allowed requirement.

### 9.12 Manifest

Required manifest:

```text
outputs/manifests/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json
```

Required top-level fields:

```text
run_id
experiment_id
legacy_directory_id
created_at
git_commit
input_artifacts
output_artifacts
decision
decision_reason
source_caveat_status
output_hashes
```

## 10. Validation

The run must fail closed on:

- missing source artifact where `required_for_final_decision_flag = true`;
- wrong 06 risk_on count;
- wrong 11A2 evaluated denominator count;
- wrong 11A2 winner count;
- non-unique episode key;
- non-unique 11A2 row key;
- raw R-core scope reconstruction mismatch;
- 09A risk_on R-core bridge count mismatch;
- 10A post-dedup same-instrument bridge count mismatch when the 10A comparison arm is available;
- unresolved raw R-core event key;
- raw R-core label join coverage below `0.995`;
- raw R-core label completeness coverage below `0.995`;
- missing E1 risk_on bad-side baseline row for train or robustness;
- incompatible density denominator for raw R-core;
- missing required output columns;
- decision not in the allowed state set.

Non-blocking comparison arms must not fail the run solely because their source is unavailable. They must instead produce an `r_core_arm_input_status.csv` row with `arm_status = not_available` or `blocked`.

Minimum tests:

1. path resolution and artifact audit test;
2. 06 episode target count/key test;
3. 11A2 winner row count/key test;
4. population bridge summary reproduction test;
5. R-core reconstruction count test;
6. 09A `risk_on_r_core_horizon_complete` bridge count and split-count test;
7. 10A post-dedup same-instrument bridge count and split-count test;
8. 10A canonical id resolution test;
9. 10B keep_9400 optional reconstruction status test;
10. episode recall denominator and `episode_split` test;
11. event precision denominator and `event_split` test;
12. label join coverage, completeness coverage, and polarity test;
13. E1 risk_on bad-side baseline selection test;
14. density denominator compatibility test;
15. decision state machine test;
16. output schema test.

## 11. Expected Prior

The expected prior, based on 08/09/10/11 evidence, is:

```text
R-core will not pass as raw backbone.
It will likely be demoted to feature source or recall benchmark.
```

This prior must not be hard-coded into the decision. The decision must be computed from the gates in §8.

## 12. Follow-up Boundary

If final decision is:

```text
12A1_r_core_backbone_supported
```

then a later requirement may evaluate compressed-population multi-K morphology, but it still must not use raw R-core without the accepted arm id.

If final decision is:

```text
12A1_r_core_feature_source_only
```

then the next allowed requirement is:

```text
requirement_12a2_state_change_backbone_candidate_generator.md
```

If final decision is:

```text
12A1_r_core_recall_benchmark_only
```

then R-core may only be used as recall benchmark / stress pool in 12A2. It must not be the denominator for winner/failure training.

If final decision is:

```text
12A1_r_core_population_blocked
```

then no downstream 12 requirement may proceed until the lineage or source reconstruction blocker is resolved.
