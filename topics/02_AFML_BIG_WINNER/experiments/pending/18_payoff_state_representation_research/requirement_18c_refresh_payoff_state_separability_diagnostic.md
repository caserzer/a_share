# Requirement: 18C Refresh Payoff-state Separability Diagnostic

## 0. Scope

This is a supplement to `requirement_18c_payoff_state_separability_diagnostic.md`.
It does not replace the original 18C requirement or reinterpret the original
18C run. It defines the only authorized refreshed 18C-style separability rerun
after 18E emitted:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
all_hard_gates_pass = true
```

The refreshed 18C rerun answers one question:

```text
Can the PIT-valid, t0-available 18E refreshed 49-feature matrix rank broad h20
payoff state out-of-sample with the same strict low-capacity separability gates
used by initial 18C?
```

The only positive refreshed 18C decision is:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
```

All blocked or diagnostic decisions must emit:

```text
next_allowed_requirement = none
```

The refreshed 18C rerun must not authorize entry policy, exit policy, holding
policy, portfolio backtest, model deployment, production signal, or live
trading. It must not tune features, model families, score thresholds, payoff
cutoffs, or support gates on robustness or validation rows.

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18C
run_id = 18C_refresh_payoff_state_separability_diagnostic
requirement_file = requirement_18c_refresh_payoff_state_separability_diagnostic.md
base_requirement_file = requirement_18c_payoff_state_separability_diagnostic.md
config_file = configs/config_18c_refresh_payoff_state_separability_diagnostic.yaml
runner_file = src/run_18c_refresh_payoff_state_separability_diagnostic.py
test_file = tests/test_18c_refresh_payoff_state_separability_diagnostic.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All output paths for this refreshed run must use `18C_refresh_payoff_state_separability_diagnostic`
as the run namespace. The refreshed rerun must not overwrite the original
`18C_payoff_state_separability_diagnostic` tables, figures, local cache,
manifests, or report.

## 2. Required Upstream Handoff Gate

The refreshed 18C rerun is authorized only by 18E. It is not authorized directly
by 18B, original 18C, 18D, EP17, 16X, or manual interpretation of a report.

Required 18E decision row:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
all_hard_gates_pass = true

upstream_18d_contract_gate = pass
input_artifact_gate = pass
feature_family_recommendation_replay_gate = pass
refreshed_feature_source_gate = pass
refreshed_feature_formula_gate = pass
refreshed_feature_lineage_gate = pass
pit_t0_availability_gate = pass
target_binding_gate = pass
feature_matrix_schema_gate = pass
feature_complete_rate_gate = pass
feature_family_coverage_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
search_accounting_gate = pass

entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required 18E handoff artifacts:

```text
experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_family_coverage.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_lineage_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_target_binding_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_missingness_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_pit_availability_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/train_only_preprocessing_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/forbidden_feature_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/search_accounting_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_feature_matrix_refresh_report.md
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18E_payoff_state_feature_matrix_refresh_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/input_artifact_manifest_18e.json
```

Required 18E handoff schema compatibility:

```text
refreshed_feature_matrix_schema.csv required columns =
  column_name
  column_role
  feature_family_id
  raw_feature_name
  model_ready_feature_name
  source_artifact_alias
  dtype
  primary_raw_feature
  primary_model_feature
  appendix_only
  target_column
  metadata_column
  forbidden_as_model_feature
  preprocessing_fit_split
  preprocessing_param_id
  blocking_reason

refreshed_feature_family_coverage.csv required columns =
  feature_family_id
  family_role
  expected_primary_feature_n
  observed_primary_feature_n
  observed_model_ready_feature_n
  finite_train_rate_min
  finite_all_rate_min
  family_coverage_status
  blocking_reason

refreshed_feature_lineage_audit.csv required columns =
  candidate_family_id
  feature_id
  candidate_feature_id
  source_artifact_alias
  lineage_scope
  row_n
  finite_candidate_value_row_n
  uses_full_episode_boundary_after_t0
  uses_future_h20_path
  uses_step_end_outcome
  uses_oracle_label
  uses_payoff_target
  uses_binary_target
  pit_valid_status
  t0_available_status
  candidate_primary_allowed_after_lineage
  candidate_appendix_only
  lineage_before_correlation_gate
  blocking_reason

refreshed_feature_target_binding_audit.csv required columns =
  binding_check_id
  existing_18b_row_n
  refreshed_matrix_row_n
  existing_identity_key_n
  refreshed_identity_key_n
  identity_key_join_used
  split_join_key_used
  existing_duplicate_key_n
  refreshed_duplicate_key_n
  unmatched_existing_key_n
  unmatched_refreshed_key_n
  split_mismatch_n
  neutral_row_n
  neutral_rows_dropped
  target_binding_gate
  blocking_reason

refreshed_feature_missingness_audit.csv required columns =
  feature_name
  feature_family_id
  split_bucket
  row_n
  finite_n
  missing_n
  finite_rate
  expected_min_finite_rate
  feature_complete_rate_gate
  blocking_reason

refreshed_feature_pit_availability_audit.csv required columns =
  candidate_family_id
  feature_id
  candidate_feature_id
  source_artifact_alias
  pit_valid_status
  t0_available_status
  uses_future_h20_path
  uses_step_end_outcome
  uses_oracle_label
  uses_payoff_target
  uses_binary_target
  candidate_primary_allowed_after_lineage
  candidate_appendix_only
  blocking_reason

train_only_preprocessing_audit.csv required columns =
  feature_name
  model_ready_feature_name
  feature_family_id
  preprocessing_kind
  fit_split
  fit_row_n
  preprocessing_uses_target_columns
  preprocessing_uses_robustness_rows
  preprocessing_uses_validation_rows
  split_local_imputation_used
  split_local_scaling_used
  status
  blocking_reason

forbidden_feature_audit.csv required columns =
  forbidden_column_family
  forbidden_column_pattern
  column_name
  present_in_matrix
  column_role
  marked_model_ready_feature
  forbidden_feature_gate
  blocking_reason

search_accounting_audit.csv required columns =
  search_family
  phase_id
  no_model_training
  no_model_refit
  no_scoring
  no_rank_ic_computed_as_gate
  no_auc_computed_as_gate
  no_precision_recall_computed_as_gate
  no_feature_selection_from_target_correlation
  no_feature_selection_from_robustness
  no_feature_selection_from_validation
  no_threshold_tuning_on_robustness
  no_threshold_tuning_on_validation
  binary_metric_not_primary_gate
  neutral_rows_not_dropped
  delayed_features_not_primary
  m4_not_primary
  oracle_gap_bridge_not_started
  no_entry_policy_authorized
  no_exit_policy_authorized
  no_holding_policy_authorized
  no_portfolio_backtest_authorized
  no_model_deployment_authorized
  no_production_signal_authorized
  no_live_trading_authorized
  search_accounting_gate
  blocking_reason
```

For 18E lineage and PIT handoff tables, feature identity must use
`feature_id`/`candidate_feature_id` and must be reconciled to
`raw_feature_name`/`model_ready_feature_name` through
`refreshed_feature_matrix_schema.csv`. The refreshed 18C runner must not require
non-18E aliases such as `feature_name`, `feature_lineage_gate`,
`pit_t0_availability_gate`, or `bound_matrix_row_n` in those 18E handoff tables.
The aggregate 18E decision-row gates remain authoritative for aggregate handoff
status, while row-level lineage and PIT status must be read from
`lineage_before_correlation_gate`, `pit_valid_status`, and
`t0_available_status`.

If any required 18E artifact is missing, stale, schema-incompatible, internally
inconsistent, or not hash-aligned with the 18E manifests:

```text
decision_state = 18C_refresh_upstream_18e_contract_blocked
next_allowed_requirement = none
```

If the only missing required artifact is the untracked local-cache parquet
`outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet`,
the refreshed 18C runner must still fail closed with the same decision and must
write an input audit row with:

```text
artifact_key = eighteen_e_refreshed_matrix
read_status = missing
blocking_reason = missing_local_cache_refreshed_matrix;rerun_18e_full_to_regenerate
```

Regeneration path:

```bash
cd topics/02_AFML_BIG_WINNER
python experiments/pending/18_payoff_state_representation_research/src/run_18e_payoff_state_feature_matrix_refresh.py --mode full
```

## 3. Required Local and Context Inputs

Required local planning inputs:

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18_payoff_state_representation_research.md
experiments/pending/18_payoff_state_representation_research/requirement_18c_payoff_state_separability_diagnostic.md
experiments/pending/18_payoff_state_representation_research/requirement_18c_refresh_payoff_state_separability_diagnostic.md
experiments/pending/18_payoff_state_representation_research/requirement_18e_payoff_state_feature_matrix_refresh.md
```

Required target contract inputs:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/payoff_state_target_contract.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_target_contract_manifest.json
```

Required external context inputs, appendix or context only:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/survival_vs_payoff_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_decile_monotonicity_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/cluster_bootstrap_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_aligned_label_power_precheck_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16X_payoff_aligned_continuation_label_power_precheck_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/oos_separability_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_model_registry.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/sequential_continuation_separability_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16C_sequential_continuation_separability_diagnostic_manifest.json
```

16X remains external coarse context only. 16C remains binary continuation
appendix only. Neither may pass or fail the refreshed 18C primary support gate.

## 4. Denominator and Target Contract

The refreshed 18C rerun keeps the original EP18 labelable full denominator:

```text
total labelable_full row_n = 23405
train labelable_full row_n = 20245
robustness labelable_full row_n = 2496
validation labelable_full row_n = 664

total neutral row_n = 6066
train neutral row_n = 5283
robustness neutral row_n = 624
validation neutral row_n = 159
neutral_rows_dropped = false
```

Primary target:

```text
target_id = y_payoff_h20
target_column = y_payoff_h20
denominator_type = labelable_full
lineage_hash = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
sign_convention = higher is better h20 payoff
```

Continue-advantage replay target:

```text
target_id = continue_advantage
target_column = continue_advantage
definition = continue_value - defend_value under q_defend=0.0 and cost_bps=50
observed_relationship = continue_advantage = y_payoff_h20 + 0.005
role = lineage_replay_sanity
```

Continue-advantage rank IC must match payoff rank IC up to floating precision:

```text
abs(continue_advantage_rank_ic - payoff_rank_ic) <= 1e-12
```

Train-frozen payoff cutoffs:

```text
top30 cutoff = 0.0596330275229357
top20 cutoff = 0.1012285086722715
top10 cutoff = 0.1721071844362347
split_local_quantile_recompute = false
```

Binary top30/top20 targets are sanity readouts only. Binary AUC, average
precision, and precision lift must not become primary support gates.

## 5. Refreshed Feature Contract

The refreshed 18C rerun may use only the 49 18E primary model-ready features
listed in `refreshed_payoff_state_feature_matrix_manifest.json`.

Existing 18B retained features:

```text
mr_ret_5d
mr_ret_10d
mr_ret_20d
mr_ma_5_20_spread
mr_ma_20_60_spread
mr_distance_to_20d_high
mr_distance_to_60d_high
mr_turnover_rate_20d_mean
mr_turnover_rate_60d_mean
mr_turnover_rate_20d_zscore
mr_volume_20d_zscore
mr_money_20d_zscore
mr_board_rank_pct
mr_board_rank_by_market_cap
mr_volatility_20d
mr_volatility_60d
mr_max_drawdown_20d
mr_max_drawdown_60d
mr_intraday_range_20d_mean
mr_board_bucket_chinext
mr_board_bucket_main_board
mr_log_total_market_cap_cny
mr_tradability_status_ok
```

18E primary refresh features:

```text
mr_m1_close_location_episode_range
mr_m1_close_location_trailing60_range
mr_m1_episode_drawdown_pre_t0
mr_m1_failed_repair_count_low_to_t0
mr_m1_path_transition_entropy_episode
mr_m1_pullback_from_episode_high_t0
mr_m1_repair_path_efficiency_episode
mr_m1_up_down_run_imbalance_20
mr_m3_asymmetric_range_position_t0
mr_m3_failed_breakout_count_pre_t0
mr_m3_upper_shadow_pressure_share_20
mr_m3_upside_downside_room_ratio_t0
mr_m3_upside_room_to_episode_high
mr_m5_bars_since_episode_high_t0
mr_m5_bars_since_episode_low
mr_m5_episode_age_to_t0
mr_m5_high_to_t0_age_ratio
mr_m5_low_to_t0_age_ratio
mr_m5_nonoverlap_step_index_to_t0
mr_m2_flow_concentration_top3_share_20
mr_m2_flow_price_divergence_persistence_20
mr_m2_money_flow_persistence_trailing20
mr_m2_money_flow_reversal_accel_5v20
mr_m2_net_signed_money_flow_trailing20
mr_m2_positive_money_flow_share_trailing20
mr_m2_turnover_compression_20_vs_60
```

Expected family coverage:

```text
F1 existing_18b_retained = 7
F2 existing_18b_retained = 5
F3 existing_18b_retained = 2
F4 existing_18b_retained = 5
F5 existing_18b_retained = 4
M1 primary_refresh = 8
M3 primary_refresh = 5
M5 primary_refresh = 6
M2 primary_refresh = 7
M4 deferred = 0
```

The refreshed 18C rerun must not add appendix-only or deferred candidates to
the primary model. In particular, it must not use `m5_lifecycle_progress_to_t0`,
`m5_bars_since_reclaim`, or `m4_regime_context_deferred` as model features.

## 6. Matrix Contract Replay

Required matrix replay checks:

```text
matrix_source_run_id = 18E_payoff_state_feature_matrix_refresh
matrix_row_n = 23405
train_row_n = 20245
robustness_row_n = 2496
validation_row_n = 664
primary_model_ready_feature_n = 49
existing_18B_model_ready_feature_n = 23
refresh_model_ready_feature_n = 26
target_column_n = 19
primary_identity_key_columns = step_id|label_id
primary_identity_key_duplicate_n = 0
full_lineage_key_columns = step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date
full_lineage_key_duplicate_n = 0
matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
schema_sha256 = 56429807004c0d3ad69101c87d1f125b4c8e33713d702f53f251002fea235a26
neutral_preservation_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
split_local_payoff_cutoff_recompute_used = false
```

The primary refreshed 18C row identity key remains `step_id|label_id` to preserve
the 18A/18B target-denominator contract. The full lineage key must also be
checked as a diagnostic replay of the 18E matrix binding. A duplicate under
either key fails `matrix_contract_replay_gate`.

If the matrix hash in `refreshed_payoff_state_feature_matrix_manifest.json`
differs from the actual parquet content hash, the run must fail closed with:

```text
decision_state = 18C_refresh_matrix_contract_replay_blocked
next_allowed_requirement = none
```

## 7. Model Registry and Training Protocol

The refreshed rerun inherits the original 18C model registry, but every primary
and auxiliary model must use the refreshed 49-feature list.

Primary support model:

```text
model_id = ridge_payoff_rank_h20_v1
model_family = ridge_regression
target_column = y_payoff_h20
feature_columns = 49 18E refreshed model-ready primary features
fit_split = train
fit_row_n = 20245
hyperparameters = alpha=10.0; fit_intercept=true; solver=auto
used_for_primary_decision = true
```

Auxiliary models:

```text
elastic_net_payoff_rank_h20_v1
ridge_ordinal_payoff_state_v1
ridge_logistic_top30_sanity_v1
ridge_logistic_top20_sanity_v1
shallow_tree_payoff_depth2_v1
```

All auxiliary models must use train rows only for fitting. They may produce
diagnostics, but they must not select features, model families, or thresholds.

Train-only cross-validation:

```text
cv_scheme = episode_cluster_grouped_cv
cv_scope = train rows only
fold_n = 5
fold_key = episode_cluster_id
fold_seed = 1818
cv_role = diagnostic_readout_only
cv_must_not_select_primary_model_family = true
cv_must_not_use_robustness_rows = true
cv_must_not_use_validation_rows = true
```

The final model for out-of-sample scoring must be fit once on all train rows
and replayed unchanged to robustness and validation.

## 8. Metrics and Gates

The refreshed rerun preserves the original 18C primary support gates.

Positive refreshed 18C support requires all hard gates below to pass:

```text
upstream_18e_contract_gate = pass
input_artifact_gate = pass
matrix_contract_replay_gate = pass
model_registry_gate = pass
train_only_fit_gate = pass
oos_no_tuning_gate = pass
rank_ic_support_gate = pass
monotonicity_support_gate = pass
bucket_lift_gate = pass
bootstrap_ci_gate = pass
baseline_improvement_gate = pass
risk_only_gate = pass
binary_sanity_boundary_gate = pass
search_accounting_gate = pass
```

Rank IC support gate:

```text
primary_model = ridge_payoff_rank_h20_v1
primary_split = robustness
primary_target = y_payoff_h20
rank_ic_materiality_floor = 0.080000
robustness_payoff_rank_ic >= 0.080000
continue_advantage_replay_abs_diff <= 1e-12
```

Monotonicity support gate:

```text
robustness_decile_payoff_monotonicity_spearman >= 0.600000
robustness_top3_minus_bottom3_payoff_gap > 0
split_local_score_cutoff_recompute_used = false
```

Bucket lift gate:

```text
robustness_top30_payoff_state_lift > 1.0
robustness_top20_payoff_state_lift > 1.0
split_local_score_cutoff_recompute_used = false
```

Bootstrap CI gate:

```text
robustness_cluster_bootstrap_rank_ic_ci_low > 0
bootstrap_resample_n = 2000
valid_bootstrap_resample_n = 2000
bootstrap_cluster_key = episode_cluster_id
bootstrap_random_seed = 20260629
```

Baseline improvement gate:

```text
same_denominator_baseline = volatility20d_defense_baseline
primary_rank_ic - volatility20d_defense_rank_ic > 0.005000
external_16x_comparison_role = external_coarse_context_only
external_16x_comparison_hard_gate_used = false
```

Risk-only gate:

```text
risk_only_gate_evaluation_precondition =
  rank_ic_support_gate = pass
  and monotonicity_support_gate = pass
  and bootstrap_ci_gate = pass
  and baseline_improvement_gate = pass
family_F4_removed_rank_ic_retention_rate >= 0.500000
and family_F4_removed_rank_ic_spearman > 0
```

The risk-only gate is a payoff-directionality guard, not a second copy of the
volatility baseline comparison. If the score clears headline rank IC only because
F4 path-risk features dominate, the refreshed 18C rerun must emit
`18C_risk_only_no_payoff_state` even when binary or bucket readouts look useful.
If any risk-only evaluation precondition fails, `risk_only_gate` must be
`not_evaluable_primary_signal_weak` and must not determine the blocked decision;
the earlier failing rank, monotonicity, bootstrap, or baseline gate determines
the decision instead.

Binary sanity boundary gate:

```text
binary_metric_used_as_primary_gate = false for every binary sanity row
binary metrics do not determine next_allowed_requirement
16C metrics do not determine next_allowed_requirement
```

Validation remains a stress readout only. Validation metrics must be reported
but must not tune model, feature set, payoff cutoff, score threshold, or support
gate.

## 9. Required Outputs

Required local-cache artifact:

```text
outputs/local_cache/18C_refresh_payoff_state_separability_diagnostic/refreshed_payoff_state_score_panel.parquet
```

Required publishable tables:

```text
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/upstream_18e_handoff_audit.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/refreshed_matrix_contract_replay_audit.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_registry.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_cv_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_coefficients.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_oos_rank_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_decile_monotonicity.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bucket_lift.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bootstrap_ci.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/topk_removal_sensitivity.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/family_removal_sensitivity.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/baseline_comparison_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/binary_sanity_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/search_accounting_audit.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
```

All publishable tables must be CSV with LF line endings and deterministic row
ordering. Required schema changes from the base 18C requirement are additive
unless explicitly replaced below.

Required figures:

```text
outputs/publishable/figures/18C_refresh_payoff_state_separability_diagnostic/payoff_state_decile_curve.png
outputs/publishable/figures/18C_refresh_payoff_state_separability_diagnostic/score_vs_payoff_rank_surface.png
```

Required report:

```text
outputs/publishable/reports/payoff_state_separability_refresh_report.md
```

Required manifests:

```text
outputs/manifests/18C_refresh_payoff_state_separability_diagnostic_manifest.json
outputs/manifests/input_artifact_manifest_18c_refresh.json
outputs/manifests/refreshed_payoff_state_score_panel_manifest.json
```

### 9.1 `refreshed_payoff_state_score_panel.parquet`

Required columns:

```text
step_id
label_id
threshold_id
horizon_sessions
instrument
episode_cluster_id
step_index
step_start_date
step_end_date
cluster_split_bucket
y_payoff_h20
continue_advantage
payoff_ordinal_state
top30_yes_no
top20_yes_no
binary_positive_negative
ridge_payoff_rank_h20_v1_score
elastic_net_payoff_rank_h20_v1_score
ridge_ordinal_payoff_state_v1_score
ridge_logistic_top30_sanity_v1_score
ridge_logistic_top20_sanity_v1_score
shallow_tree_payoff_depth2_v1_score
ridge_payoff_rank_h20_v1_train_score_decile
ridge_payoff_rank_h20_v1_train_score_top30_bucket
ridge_payoff_rank_h20_v1_train_score_top20_bucket
score_cutoff_source
split_local_score_cutoff_recompute_used
source_18e_matrix_sha256
score_panel_status
blocking_reason
```

Required score-panel semantics:

```text
primary_identity_key_columns = step_id|label_id
full_lineage_key_columns = step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date
target_columns copied unchanged from 18E matrix where present
score columns produced by train-fitted models only
train score decile and top-score bucket assignments use train-frozen score cutoffs
split_local_score_cutoff_recompute_used = false for every scored row
source_18e_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
score_panel_status in {scored, not_scored_fail_closed}
if score_panel_status = scored then row_n = 23405
if score_panel_status = scored then split_counts = train 20245; robustness 2496; validation 664
if score_panel_status = scored then primary_identity_key_duplicate_n = 0
if score_panel_status = scored then full_lineage_key_duplicate_n = 0
if score_panel_status = not_scored_fail_closed then row_n may be 0
```

If the run fails before model scoring, the score panel may be emitted with
`score_panel_status = not_scored_fail_closed`, but it must still include the
required columns and an explicit `blocking_reason`; identity-key uniqueness is
not evaluated for an empty fail-closed score panel. A positive
`18C_payoff_state_separability_supported` decision requires
`score_panel_status = scored` for all 23,405 rows.

### 9.2 `family_removal_sensitivity.csv`

Required columns:

```text
sensitivity_id
split_bucket
model_id
removal_type
removed_feature_family_id
removed_feature_n
removed_feature_names
base_rank_ic_spearman
sensitivity_rank_ic_spearman
rank_ic_retention_rate
family_role
refresh_family_flag
risk_only_focus_flag
sensitivity_status
blocking_reason
```

Required family rows for each of `robustness` and `validation`:

```text
family_F1_removed
family_F2_removed
family_F3_removed
family_F4_removed
family_F5_removed
family_M1_removed
family_M2_removed
family_M3_removed
family_M5_removed
```

Required semantics:

```text
operation = zero out all coefficient contributions from the family without refitting
base_model = ridge_payoff_rank_h20_v1
base_rank_ic_spearman = ridge_payoff_rank_h20_v1 robustness payoff_rank_ic before removal
sensitivity_rank_ic_spearman = payoff_rank_ic after zeroing the family contribution without refitting
rank_ic_retention_rate = sensitivity_rank_ic_spearman / base_rank_ic_spearman
if base_rank_ic_spearman <= 0 or missing then sensitivity_status = invalid_base_rank_ic and risk_only_gate = not_evaluable_primary_signal_weak
refresh_family_flag = true only for M1/M2/M3/M5 rows
risk_only_focus_flag = true only for F4 rows
family_F4_removed robustness retention and sensitivity_rank_ic_spearman feed risk_only_gate
M1/M2/M3/M5 rows are diagnostic readouts only and must not tune feature selection
```

### 9.3 `upstream_18e_handoff_audit.csv`

Required columns:

```text
contract_check_id
expected_value
observed_value
upstream_18e_contract_gate
blocking_reason
```

Required checks:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
all_hard_gates_pass = true
upstream_18d_contract_gate = pass
input_artifact_gate = pass
feature_family_recommendation_replay_gate = pass
refreshed_feature_source_gate = pass
refreshed_feature_formula_gate = pass
refreshed_feature_lineage_gate = pass
pit_t0_availability_gate = pass
target_binding_gate = pass
feature_matrix_schema_gate = pass
feature_complete_rate_gate = pass
feature_family_coverage_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
search_accounting_gate = pass
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

### 9.4 `refreshed_matrix_contract_replay_audit.csv`

Required columns:

```text
check_id
expected_value
observed_value
matrix_contract_replay_gate
blocking_reason
```

Required checks:

```text
matrix_source_run_id = 18E_payoff_state_feature_matrix_refresh
matrix_row_n = 23405
train_row_n = 20245
robustness_row_n = 2496
validation_row_n = 664
primary_model_ready_feature_n = 49
existing_18B_model_ready_feature_n = 23
refresh_model_ready_feature_n = 26
target_column_n = 19
primary_identity_key_columns = step_id|label_id
primary_identity_key_duplicate_n = 0
full_lineage_key_columns = step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date
full_lineage_key_duplicate_n = 0
source_18e_manifest_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
actual_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
schema_sha256 = 56429807004c0d3ad69101c87d1f125b4c8e33713d702f53f251002fea235a26
target_lineage_hash_y_payoff_h20 = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
target_lineage_hash_continue_advantage = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
neutral_preservation_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
continue_advantage_affine_replay_max_abs_diff <= 1e-12
train_frozen_payoff_cutoff_value_replay = pass for top30/top20/top10 values
split_local_payoff_cutoff_recompute_used = false
```

### 9.5 `search_accounting_audit.csv`

Required columns:

```text
search_family
run_id
phase_id
scope_id
model_family_registry_predeclared
primary_model_predeclared
no_feature_selection_from_target_correlation
no_feature_selection_from_robustness
no_feature_selection_from_validation
no_model_family_selection_from_robustness
no_model_family_selection_from_validation
no_threshold_tuning_on_robustness
no_threshold_tuning_on_validation
no_split_local_payoff_cutoff_recompute
no_split_local_score_threshold_recompute_for_gate
binary_metric_not_primary_gate
validation_stress_readout_only
no_entry_policy_authorized
no_exit_policy_authorized
no_holding_policy_authorized
no_portfolio_backtest_authorized
no_model_deployment_authorized
no_production_signal_authorized
no_live_trading_authorized
search_accounting_gate
blocking_reason
```

This table audits the refreshed 18C separability rerun itself, not the upstream
18E matrix-construction search accounting. A positive decision requires all
boolean no-search/no-policy fields above to be true and
`search_accounting_gate = pass`.

### 9.6 Positive-path Test Requirements

The refreshed 18C test suite must include at least one controlled positive-path
fixture or monkeypatch test that proves:

```text
all hard gates pass -> decision_state = 18C_payoff_state_separability_supported
positive decision -> next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
positive decision -> next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
rank_ic_support_gate, monotonicity_support_gate, bucket_lift_gate, bootstrap_ci_gate, baseline_improvement_gate, risk_only_gate, and search_accounting_gate all feed the positive decision
each primary gate failure maps to the required blocked decision precedence
validation_stress_evaluable is reported but cannot select model, features, thresholds, or support gates
```

## 10. Decision Table Contract

`payoff_state_separability_decision.csv` must include:

```text
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
upstream_18e_contract_gate
input_artifact_gate
matrix_contract_replay_gate
model_registry_gate
train_only_fit_gate
oos_no_tuning_gate
rank_ic_support_gate
monotonicity_support_gate
bucket_lift_gate
bootstrap_ci_gate
baseline_improvement_gate
risk_only_gate
binary_sanity_boundary_gate
search_accounting_gate
validation_stress_evaluable
validation_stress_caveat
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

Allowed decisions:

```text
18C_payoff_state_separability_supported
18C_refresh_upstream_18e_contract_blocked
18C_refresh_input_artifact_blocked
18C_refresh_matrix_contract_replay_blocked
18C_model_registry_blocked
18C_train_only_fit_blocked
18C_oos_tuning_blocked
18C_payoff_state_signal_weak_or_nonmonotone
18C_current_features_reconfirmed_insufficient
18C_binary_only_not_supported
18C_over_narrow_winner_target_blocked
18C_risk_only_no_payoff_state
18C_search_accounting_blocked
18C_refresh_separability_contract_blocked
```

Decision precedence:

```text
1. upstream_18e_contract_gate fail -> 18C_refresh_upstream_18e_contract_blocked
2. input_artifact_gate fail -> 18C_refresh_input_artifact_blocked
3. matrix_contract_replay_gate fail -> 18C_refresh_matrix_contract_replay_blocked
4. model_registry_gate fail -> 18C_model_registry_blocked
5. train_only_fit_gate fail -> 18C_train_only_fit_blocked
6. oos_no_tuning_gate fail -> 18C_oos_tuning_blocked
7. search_accounting_gate fail -> 18C_search_accounting_blocked
8. all primary, bucket-lift, and binary sanity readouts weak -> 18C_current_features_reconfirmed_insufficient
9. top30/top20 bucket lift passes but continuous rank/monotonicity gates fail -> 18C_over_narrow_winner_target_blocked
10. binary sanity metrics pass but primary rank/monotonicity gates fail -> 18C_binary_only_not_supported
11. rank_ic_support_gate fail or monotonicity_support_gate fail or bootstrap_ci_gate fail or baseline_improvement_gate fail -> 18C_payoff_state_signal_weak_or_nonmonotone
12. risk_only_gate fail after all risk-only evaluation preconditions pass -> 18C_risk_only_no_payoff_state
13. otherwise unclassified refresh contract failure -> 18C_refresh_separability_contract_blocked
```

## 11. Report Requirements

`payoff_state_separability_refresh_report.md` must include:

1. One-line decision, next allowed requirement, and refresh scope.
2. 18E handoff replay and refreshed matrix contract replay.
3. Input artifact and manifest hash audit.
4. Refreshed 49-feature family coverage and train-only preprocessing summary.
5. Model registry and train-only fitting summary.
6. Primary OOS rank readout with robustness as support split and validation as
   stress readout.
7. Decile monotonicity and top3-minus-bottom3 payoff gap.
8. Bucket lift for top30/top20 train-frozen payoff states.
9. Cluster bootstrap CI.
10. Baseline comparison against same-denominator volatility20d and intercept
    baselines, with 16X clearly marked as external coarse context.
11. Top-k and family removal sensitivity, including M1/M2/M3/M5 refresh-family
    sensitivity.
12. Binary sanity appendix, including 16C appendix-only comparison.
13. Search accounting and authorization boundary.

The report must state clearly:

```text
This is the refreshed 18C rerun on the 18E matrix.
It does not overwrite or reinterpret the original 18C diagnostic.
18E provided matrix construction support only, not separability support.
Only this refreshed rerun can decide whether the future EP18F oracle-gap
requirement may be created and executed.
No policy, backtest, deployment, production signal, or live trading is authorized.
```

## 12. Manifest Requirements

`18C_refresh_payoff_state_separability_diagnostic_manifest.json` must include:

```text
run_id
phase_id
requirement_file_sha256
base_requirement_file_sha256
config_file_sha256
runner_file_sha256
input_artifact_manifest_sha256
source_18e_matrix_sha256
source_18e_schema_sha256
score_panel_sha256
publishable_table_sha256_by_name
publishable_figure_sha256_by_name
report_sha256
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
primary_model_id
primary_feature_n
primary_split
primary_target_id
robustness_payoff_rank_ic
robustness_decile_payoff_monotonicity_spearman
robustness_cluster_bootstrap_rank_ic_ci_low
rank_ic_vs_volatility20d_delta
validation_role
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

`refreshed_payoff_state_score_panel_manifest.json` must include row count, split
counts, identity-key columns, target columns, score columns, model ids, the 49
feature names, and the source 18E matrix hash.

## 13. Handoff to EP18F

EP18F may begin only if refreshed 18C emits:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
all_hard_gates_pass = true
```

`requirement_18f_payoff_state_oracle_gap_bridge.md` is a future requirement and
is not part of this refreshed 18C deliverable. If the file is absent at refreshed
18C runtime, that absence must not block the refreshed 18C separability decision;
the positive decision authorizes creating and implementing that next requirement,
not executing EP18F inside the 18C runner.

EP18F may consume:

```text
outputs/local_cache/18C_refresh_payoff_state_separability_diagnostic/refreshed_payoff_state_score_panel.parquet
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_registry.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_coefficients.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_oos_rank_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_decile_monotonicity.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bucket_lift.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bootstrap_ci.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/baseline_comparison_readout.csv
outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
outputs/manifests/18C_refresh_payoff_state_separability_diagnostic_manifest.json
outputs/manifests/refreshed_payoff_state_score_panel_manifest.json
```

EP18F must compare learned payoff-state scores to EP17 O4/O5 oracle headroom
only on aligned denominators. A positive refreshed 18C decision still does not
authorize entry, exit, holding, portfolio backtest, deployment, production
signal, or live trading.

## 14. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18c_refresh_payoff_state_separability_diagnostic.py
python experiments/pending/18_payoff_state_representation_research/src/run_18c_refresh_payoff_state_separability_diagnostic.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18c_refresh_payoff_state_separability_diagnostic.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18c_refresh_payoff_state_separability_diagnostic.py -q
```

Before publish:

```bash
git diff --check
```
