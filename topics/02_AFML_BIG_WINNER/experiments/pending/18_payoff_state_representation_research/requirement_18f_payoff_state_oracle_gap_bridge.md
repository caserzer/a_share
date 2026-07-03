# Requirement: 18F Payoff-state Oracle Gap Bridge

## 0. Scope

18F is the learned payoff-state utility bridge after refreshed 18C emitted:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
all_hard_gates_pass = true
```

18F answers one question:

```text
Does the train-frozen 18C refresh payoff-state score reduce the aligned
labelable_full oracle action-value gap enough to justify a later policy
preflight requirement?
```

18F is not a trading strategy, not a portfolio backtest, and not an entry, exit,
or holding policy. It is a single-step utility bridge diagnostic against frozen
EP17/18A oracle references. It must not authorize entry policy, exit policy,
holding policy, portfolio backtest, model deployment, production signal, or live
trading.

The only positive 18F decision is:

```text
decision_state = 18F_payoff_state_policy_preflight_allowed
next_allowed_requirement = requirement_19_payoff_state_policy_preflight.md
next_allowed_requirement_scope = payoff_state_policy_preflight
```

All blocked or diagnostic decisions must emit:

```text
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18F
run_id = 18F_payoff_state_oracle_gap_bridge
requirement_file = requirement_18f_payoff_state_oracle_gap_bridge.md
config_file = configs/config_18f_payoff_state_oracle_gap_bridge.yaml
runner_file = src/run_18f_payoff_state_oracle_gap_bridge.py
test_file = tests/test_18f_payoff_state_oracle_gap_bridge.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All outputs must use `18F_payoff_state_oracle_gap_bridge` as the run namespace.
18F must not overwrite 18A, 18B, original 18C, 18C refresh, 18D, or 18E
artifacts.

## 2. Required Upstream Authorization

18F is authorized only by the refreshed 18C run. It is not authorized directly
by 18E, original 18C, 18D, EP17, 16X, or manual report interpretation.

Required refreshed 18C decision row:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
all_hard_gates_pass = true

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

entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required refreshed 18C metrics:

```text
primary_model_id = ridge_payoff_rank_h20_v1
primary_feature_n = 49
primary_split = robustness
primary_target_id = y_payoff_h20
robustness_payoff_rank_ic = 0.1253619565871872
robustness_decile_payoff_monotonicity_spearman = 0.7333333333333332
robustness_cluster_bootstrap_rank_ic_ci_low = 0.08822122710318461
rank_ic_vs_volatility20d_delta = 0.06059040668108248
```

Required refreshed 18C source hashes:

```text
score_panel_sha256 = a3f431c8b634dcb9d24b31a5ed38574b94e7332672d4861470037837492cfc2c
source_18e_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
source_18e_schema_sha256 = 56429807004c0d3ad69101c87d1f125b4c8e33713d702f53f251002fea235a26
```

If any refreshed 18C handoff check fails, 18F must fail closed:

```text
decision_state = 18F_upstream_18c_refresh_contract_blocked
next_allowed_requirement = none
```

## 3. Required Input Artifacts

### 3.1 Local planning and requirements

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18_payoff_state_representation_research.md
experiments/pending/18_payoff_state_representation_research/requirement_18a_payoff_state_contract_preflight.md
experiments/pending/18_payoff_state_representation_research/requirement_18c_refresh_payoff_state_separability_diagnostic.md
experiments/pending/18_payoff_state_representation_research/requirement_18f_payoff_state_oracle_gap_bridge.md
```

### 3.2 Refreshed 18C score and decision handoff

```text
experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18C_refresh_payoff_state_separability_diagnostic/refreshed_payoff_state_score_panel.parquet
experiments/pending/18_payoff_state_representation_research/outputs/manifests/refreshed_payoff_state_score_panel_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_oos_rank_readout.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_decile_monotonicity.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bucket_lift.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_bootstrap_ci.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/payoff_state_model_coefficients.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/topk_removal_sensitivity.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/family_removal_sensitivity.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/baseline_comparison_readout.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/search_accounting_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_separability_refresh_report.md
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18C_refresh_payoff_state_separability_diagnostic_manifest.json
```

The model registry, coefficient table, and top-k sensitivity table are required
because 18F must recompute learned utility under frozen 18C feature-removal
score definitions. Aggregate family rank-IC sensitivity alone is not sufficient
to rebuild action masks.

### 3.3 18E matrix target source

The 18C refresh score panel does not carry all utility target columns required
for 18F. 18F must join the score panel to the exact 18E refreshed matrix used by
18C refresh.

```text
experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
experiments/pending/18_payoff_state_representation_research/outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
```

The 18E matrix hash must equal the hash recorded by 18C refresh:

```text
refreshed_payoff_state_feature_matrix.parquet sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
```

### 3.4 18A target and oracle denominator contract

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/payoff_state_target_contract.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/oracle_reference_denominator_map.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/o5_incremental_definition_replay.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_target_contract_manifest.json
```

Required 18A decision:

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
all_hard_gates_pass = true
denominator_reconciliation_gate = pass
target_lineage_gate = pass
oracle_reference_denominator_gate = pass
o5_incremental_definition_replay_gate = pass
train_frozen_cutoff_gate = pass
neutral_preservation_gate = pass
path_risk_sign_convention_gate = pass
search_accounting_gate = pass
```

### 3.5 EP17 oracle references

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_diagnosis_decision.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_value_source_attribution.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_learned_model_gap_bridge.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/search_accounting_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17D_oracle_diagnosis_report_manifest.json

experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_ladder_summary.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o5_action_selection_proof.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o2_drawdown_threshold_replay.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_high_upside_threshold_freeze.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17B_oracle_ladder_replay_manifest.json
```

## 4. Required Input Schemas

### 4.1 Score panel

`refreshed_payoff_state_score_panel.parquet` must include at least:

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
ridge_payoff_rank_h20_v1_train_score_decile
ridge_payoff_rank_h20_v1_train_score_top30_bucket
ridge_payoff_rank_h20_v1_train_score_top20_bucket
score_cutoff_source
split_local_score_cutoff_recompute_used
source_18e_matrix_sha256
score_panel_status
blocking_reason
```

Required score panel contract:

```text
score_panel_status = scored for all 23405 rows
row_count = 23405
split_counts = train 20245; robustness 2496; validation 664
source_18e_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
split_local_score_cutoff_recompute_used = false for all rows
```

### 4.2 18E matrix target columns

The exact 18E matrix must include:

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
label_class
continuation_positive
continuation_negative
continuation_neutral
y_payoff_h20
y_signed_max_drawdown_h20
continue_value
defend_value
continue_advantage
defend_advantage
o5_incremental
payoff_ordinal_state
top30_yes_no
top20_yes_no
binary_positive_negative
```

The exact 18E matrix must also include every `feature_name` used by
`ridge_payoff_rank_h20_v1` in
`payoff_state_model_coefficients.csv`. Missing model-ready feature columns fail
the `input_artifact_gate`.

Required join contract:

```text
primary_identity_key_columns = step_id|label_id
full_lineage_key_columns = step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date
score_panel_to_18e_matrix_join_type = one_to_one
joined_row_n = 23405
unmatched_score_panel_row_n = 0
unmatched_matrix_row_n = 0
target_value_mismatch_n for shared target columns = 0
model_ready_feature_mismatch_n for coefficient feature columns = 0
```

### 4.3 18C model and sensitivity artifacts

`payoff_state_model_registry.csv` must include the primary model row:

```text
model_id = ridge_payoff_rank_h20_v1
model_family = ridge_regression
model_role = primary_support
target_column = y_payoff_h20
feature_column_n = 49
fit_split = train
used_for_primary_decision = true
training_uses_robustness_rows = false
training_uses_validation_rows = false
model_registry_gate = pass
```

`payoff_state_model_coefficients.csv` must include all 49 primary model feature
rows with:

```text
model_id
feature_name
feature_family_id
coefficient
feature_train_std
standardized_coefficient
abs_coefficient_rank
standardized_abs_coefficient_rank
train_fit_row_n
coefficient_source
```

`topk_removal_sensitivity.csv` must include robustness and validation rows for
the top-k coefficient removals only:

```text
top1_abs_coefficient_removed
top3_abs_coefficient_removed
top5_abs_coefficient_removed
```

`family_removal_sensitivity.csv` must include robustness and validation rows for
the family removals:

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

18F must replay the removed feature sets from these two 18C sensitivity tables.
It must not select a different feature set from 18F utility results.

Sensitivity scores must use the frozen 18C zero-contribution convention:

```text
sensitivity_score =
  ridge_payoff_rank_h20_v1_score
  - sum(feature_value * coefficient for removed features)
```

For sensitivity utility, the operating-point quantile remains
`defend_bottom30_continue_rest`; only the sensitivity score replaces the base
score. The cutoff may be recomputed from train rows for the sensitivity score
only. Robustness or validation rows must never set the sensitivity cutoff.

### 4.4 Oracle denominator map

`oracle_reference_denominator_map.csv` must include:

```text
oracle_reference_id
source_artifact
source_denominator_type
split_bucket
observed_step_n
mean_incremental_return
source_value
source_formula
allowed_bridge_denominator
direct_comparison_allowed
oracle_reference_denominator_gate
notes
blocking_reason
```

Required robustness oracle references:

```text
O5_perfect_utility_primary:
  source_denominator_type = labelable_full
  observed_step_n = 2496
  mean_incremental_return = 0.0294674283651707
  allowed_bridge_denominator = labelable_full
  direct_comparison_allowed = true

O2_dd_10pct_primary:
  source_denominator_type = labelable_full
  observed_step_n = 2496
  mean_incremental_return = 0.0185108290944368
  allowed_bridge_denominator = labelable_full
  direct_comparison_allowed = true

O4_label_positive_primary:
  source_denominator_type = binary_primary
  observed_step_n = 1872
  mean_incremental_return = 0.0246811054592491
  allowed_bridge_denominator = binary_primary
  direct_comparison_allowed = false for labelable_full bridge

17D_mixed_o5_vs_best_label_path_gap:
  source_denominator_type = mixed_diagnostic_only
  source_value = 0.004786322905921601
  allowed_bridge_denominator = none
  direct_comparison_allowed = false
```

The following operation is forbidden:

```text
learned_labelable_full_mean - O4_binary_primary_mean
```

Any O4 comparison must be restricted to the `binary_primary` denominator and
must be labeled appendix/sanity unless explicitly stated otherwise.

## 5. Learned Utility Definition

18F must use frozen 18A action semantics:

```text
q_continue = 1.0
q_defend = 0.0
cost_bps = 50
cash_return = 0.0
blind_continue_base = continue_value
```

For any learned operating point:

```text
learned_defend_flag in {true,false}
learned_continue_flag = not learned_defend_flag

row_incremental_return =
  if learned_defend_flag then defend_value - continue_value
  else 0

row_incremental_return = learned_defend_flag * defend_advantage
learned_mean_incremental_return = mean(row_incremental_return over denominator rows)
```

This is the only learned utility formula allowed in 18F. It is aligned to O5's
blind-continue baseline. Non-defended rows contribute zero. Neutral rows remain
in `labelable_full` and must not be dropped.

The O5 identity must be replayed:

```text
o5_policy_value = max(continue_value, defend_value)
o5_incremental = o5_policy_value - blind_continue_base
               = max(0, defend_value - continue_value)
               = max(0, defend_advantage)
```

Required replay tolerances:

```text
joined_o5_incremental_max_abs_diff <= 1e-9
joined_o5_incremental_formula_mismatch_n = 0
```

If utility formula replay fails:

```text
decision_state = 18F_oracle_gap_contract_blocked
next_allowed_requirement = none
```

## 6. Train-frozen Operating Points

18F must not tune thresholds on robustness or validation. All learned operating
points are derived from train score ranks and then replayed unchanged.

Primary operating point:

```text
primary_operating_point_id = defend_bottom30_continue_rest
score_source_column = ridge_payoff_rank_h20_v1_score
cutoff_source_split = train
cutoff_quantile = 0.30
learned_defend_flag = score <= train_score_q30_cutoff
learned_continue_flag = score > train_score_q30_cutoff
decision_role = primary
```

Required diagnostic operating points:

```text
defend_bottom10_continue_rest:
  cutoff_quantile = 0.10
  decision_role = diagnostic_conservative

defend_bottom20_continue_rest:
  cutoff_quantile = 0.20
  decision_role = diagnostic_conservative

defend_bottom40_continue_rest:
  cutoff_quantile = 0.40
  decision_role = diagnostic_aggressive

defend_bottom50_continue_rest:
  cutoff_quantile = 0.50
  decision_role = diagnostic_aggressive

continue_top30_defend_rest:
  cutoff_quantile = 0.70
  learned_continue_flag = score >= train_score_q70_cutoff
  decision_role = over_narrow_stress

continue_top20_defend_rest:
  cutoff_quantile = 0.80
  learned_continue_flag = score >= train_score_q80_cutoff
  decision_role = over_narrow_stress

continue_top10_defend_rest:
  cutoff_quantile = 0.90
  learned_continue_flag = score >= train_score_q90_cutoff
  decision_role = top10_over_narrow_stress_only
```

The primary decision must not select a better operating point after observing
robustness or validation utility. Diagnostic operating points may explain why
the primary bridge fails, but they must not replace the primary operating point
unless a future requirement explicitly authorizes a new freeze.

## 7. Utility Decomposition

For every split, denominator, and operating point, 18F must compute:

```text
defended_positive_incremental_return =
  mean(denominator rows,
       I(learned_defend_flag and label_class = positive) * defend_advantage)

defended_negative_incremental_return =
  mean(denominator rows,
       I(learned_defend_flag and label_class = negative) * defend_advantage)

defended_neutral_incremental_return =
  mean(denominator rows,
       I(learned_defend_flag and label_class = neutral) * defend_advantage)

continued_negative_leakage =
  mean(denominator rows,
       I(learned_continue_flag and label_class = negative) * max(0, defend_advantage))

continued_positive_retained =
  mean(denominator rows,
       I(learned_continue_flag and label_class = positive) * max(0, continue_advantage))
```

Required identity:

```text
learned_mean_incremental_return =
  defended_positive_incremental_return
  + defended_negative_incremental_return
  + defended_neutral_incremental_return
  + residual_reconciliation_term
```

`residual_reconciliation_term` must be reported. Its absolute value must be
less than or equal to `1e-12`.

The explanatory sacrifice and avoidance metrics are separate from the identity:

```text
defended_positive_opportunity_cost =
  mean(denominator rows,
       I(learned_defend_flag and label_class = positive) * max(0, continue_advantage))

defended_negative_avoidance_gain =
  mean(denominator rows,
       I(learned_defend_flag and label_class = negative) * max(0, defend_advantage))

defended_neutral_contribution =
  defended_neutral_incremental_return
```

These explanatory metrics must never replace the direct incremental-return
identity above.

Top payoff retention metrics:

```text
top30_payoff_retention_rate =
  count(top30_yes_no = true and learned_continue_flag = true)
  / count(top30_yes_no = true)

top20_payoff_retention_rate =
  count(top20_yes_no = true and learned_continue_flag = true)
  / count(top20_yes_no = true)

top30_payoff_sacrifice_rate = 1 - top30_payoff_retention_rate
top20_payoff_sacrifice_rate = 1 - top20_payoff_retention_rate
```

## 8. Oracle Gap Metrics

For labelable_full robustness:

```text
o5_mean_incremental_return = 0.0294674283651707
o2_mean_incremental_return = 0.0185108290944368

o5_gap_remaining = o5_mean_incremental_return - learned_mean_incremental_return
o2_gap_remaining = o2_mean_incremental_return - learned_mean_incremental_return

o5_approximation_ratio = learned_mean_incremental_return / o5_mean_incremental_return
o2_approximation_ratio = learned_mean_incremental_return / o2_mean_incremental_return
o5_gap_reduction_flag = learned_mean_incremental_return > 0
o5_upper_bound_violation = learned_mean_incremental_return > o5_mean_incremental_return + 1e-12
```

For aligned labelable_full comparisons, O5 is a same-denominator upper bound
under the frozen defend/continue action set. A learned action mask exceeding O5
is therefore a contract violation, not a stronger policy.

For binary_primary robustness:

```text
binary_primary_rows = label_class in {positive, negative}
o4_mean_incremental_return = 0.0246811054592491
learned_binary_primary_mean_incremental_return =
  mean(binary_primary rows, learned_defend_flag * defend_advantage)
o4_binary_approximation_ratio =
  learned_binary_primary_mean_incremental_return / o4_mean_incremental_return
```

The binary bridge must be labeled:

```text
denominator_type = binary_primary
binary_bridge_role = appendix_sanity_only
binary_bridge_used_as_primary_gate = false
```

## 9. Hard Gates

Positive 18F support requires all gates below to pass:

```text
upstream_18c_refresh_contract_gate = pass
input_artifact_gate = pass
score_matrix_join_gate = pass
oracle_denominator_contract_gate = pass
o5_identity_replay_gate = pass
o5_upper_bound_contract_gate = pass
operating_point_freeze_gate = pass
learned_utility_support_gate = pass
oracle_gap_reduction_gate = pass
positive_sacrifice_gate = pass
payoff_retention_gate = pass
neutral_reconciliation_gate = pass
cluster_bootstrap_utility_gate = pass
topk_sensitivity_gate = pass
validation_stress_gate = pass
binary_boundary_gate = pass
search_accounting_gate = pass
```

The `o5_upper_bound_contract_gate` is evaluated before learned utility support.
It passes only when:

```text
o5_upper_bound_violation = false
```

If `o5_upper_bound_violation = true`:

```text
decision_state = 18F_oracle_gap_contract_blocked
```

### 9.1 Learned utility support gate

Primary gate uses only:

```text
split_bucket = robustness
denominator_type = labelable_full
operating_point_id = defend_bottom30_continue_rest
```

Required:

```text
learned_mean_incremental_return > 0
```

If `learned_mean_incremental_return <= 0`:

```text
decision_state = 18F_utility_bridge_not_supported
```

### 9.2 Oracle gap reduction gate

Required:

```text
o5_gap_remaining < o5_mean_incremental_return
o2_gap_remaining < o2_mean_incremental_return
o5_gap_reduction_flag = true
o5_approximation_ratio >= 0.25
o2_approximation_ratio >= 0.25
```

This gate proves that the learned diagnostic action mask reduces some aligned
oracle headroom. It does not prove that a policy should be deployed.
Because `O2 < O5`, the O5 approximation ratio is the binding materiality floor;
the O2 ratio is retained as a same-denominator sanity readout.

If learned utility is positive but approximation ratios fail:

```text
decision_state = 18F_oracle_gap_not_reduced
```

### 9.3 Positive sacrifice gate

Required for the primary operating point:

```text
positive_sacrifice_to_avoidance_ratio =
  defended_positive_opportunity_cost
  / max(defended_negative_avoidance_gain + max(defended_neutral_contribution, 0), 1e-12)

positive_sacrifice_to_avoidance_ratio < 1.00
defended_positive_opportunity_cost < defended_negative_avoidance_gain + max(defended_neutral_contribution, 0)
```

If an over-narrow top10-like operating point is the only readout with positive
utility, or if the primary bridge creates large positive sacrifice:

```text
decision_state = 18F_over_narrow_winner_bridge_blocked
```

### 9.4 Payoff retention gate

Required for the primary operating point:

```text
top30_payoff_retention_rate >= 0.70
top20_payoff_retention_rate >= 0.80
```

This gate ensures the score bridge does not improve utility merely by defending
too many high-upside rows.

### 9.5 Neutral reconciliation gate

Required:

```text
neutral_rows_included = true
neutral_row_n = train 5283; robustness 624; validation 159
neutral_rows_dropped = false
neutral_contribution_reported = true
```

Neutral contribution may be positive or negative. It must be explicit and must
not be hidden by switching to binary_primary.

### 9.6 Cluster bootstrap utility gate

Primary bootstrap:

```text
split_bucket = robustness
cluster_key = episode_cluster_id
bootstrap_resample_n = 2000
bootstrap_random_seed = 20260629
metric_id = learned_mean_incremental_return
ci_level = 0.95
```

Required:

```text
valid_bootstrap_resample_n = 2000
cluster_bootstrap_utility_ci_low > 0
```

### 9.7 Top-k sensitivity gate

18F must evaluate learned utility after removing score contributions from the
same primary-score sensitivity definitions produced by 18C refresh. Top-k
removed feature sets come from `topk_removal_sensitivity.csv`; family removed
feature sets come from `family_removal_sensitivity.csv`.

Required top-k robustness rows:

```text
top1_abs_coefficient_removed
top3_abs_coefficient_removed
top5_abs_coefficient_removed
```

Required family robustness rows:

```text
family_F4_removed
family_M1_removed
family_M2_removed
family_M3_removed
family_M5_removed
```

Required:

```text
primary_learned_utility_retention_rate_after_top5_removed >= 0.25
family_F4_removed_learned_utility_retention_rate >= 0.25
```

If the primary base learned utility is non-positive, sensitivity retention is not
economically evaluable: `learned_utility_retention_rate` may be blank/NaN,
`topk_bootstrap_status = not_evaluable`, `blocking_reason =
base_learned_utility_nonpositive`, and `topk_sensitivity_gate = fail`. This
cannot improve the decision because `learned_utility_support_gate` has higher
precedence and must fail first.

If removing one top feature erases utility but other bridge gates pass, 18F may
still emit `18F_payoff_state_representation_diagnostic_only` rather than policy
preflight, because the result is too concentrated for a policy handoff.

### 9.8 Validation stress gate

Validation is stress readout only. It must not tune operating points or gates.

Required:

```text
validation_primary_learned_mean_incremental_return >= 0
validation_top30_payoff_retention_rate >= 0.50
validation_top20_payoff_retention_rate >= 0.50
validation_utility_sign_reversal = false
```

If validation hard reverses:

```text
decision_state = 18F_payoff_state_representation_diagnostic_only
```

### 9.9 Binary boundary gate

Required:

```text
binary_bridge_used_as_primary_gate = false for every binary bridge row
O4 binary_primary is never subtracted from learned labelable_full
binary_primary success cannot override labelable_full utility failure
```

## 10. Required Outputs

Required publishable tables:

```text
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/input_artifact_audit.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/upstream_18c_refresh_handoff_audit.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/score_matrix_join_audit.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/oracle_reference_replay_audit.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/score_operating_point_freeze.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/learned_payoff_state_utility_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/oracle_gap_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/payoff_state_six_cell_decomposition.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/binary_denominator_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/cluster_bootstrap_utility_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/topk_bootstrap_utility_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/validation_stress_utility_bridge.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/search_accounting_audit.csv
outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/payoff_state_oracle_gap_bridge_decision.csv
```

Required figures:

```text
outputs/publishable/figures/18F_payoff_state_oracle_gap_bridge/oracle_gap_bridge_curve.png
outputs/publishable/figures/18F_payoff_state_oracle_gap_bridge/positive_sacrifice_vs_payoff_preservation.png
```

Required report:

```text
outputs/publishable/reports/payoff_state_oracle_gap_bridge_report.md
```

Required manifests:

```text
outputs/manifests/18F_payoff_state_oracle_gap_bridge_manifest.json
outputs/manifests/input_artifact_manifest_18f.json
```

## 11. Output Schemas

### 11.1 `score_operating_point_freeze.csv`

Required columns:

```text
operating_point_id
score_source_column
cutoff_source_split
cutoff_quantile
train_score_cutoff_value
learned_defend_rule
learned_continue_rule
decision_role
train_defended_n
train_defended_rate
robustness_defended_n
robustness_defended_rate
validation_defended_n
validation_defended_rate
split_local_threshold_recompute_used
operating_point_freeze_gate
blocking_reason
```

### 11.2 `learned_payoff_state_utility_bridge.csv`

Required columns:

```text
split_bucket
denominator_type
operating_point_id
decision_role
row_n
episode_cluster_n
defended_n
continued_n
defended_rate
learned_mean_incremental_return
learned_sum_incremental_return
mean_continue_value
mean_defend_value_on_defended_rows
mean_defend_advantage_on_defended_rows
defended_positive_incremental_return
defended_negative_incremental_return
defended_neutral_incremental_return
residual_reconciliation_term
positive_sacrifice_to_avoidance_ratio
top30_payoff_retention_rate
top20_payoff_retention_rate
neutral_row_n
neutral_contribution_mean
utility_bridge_status
blocking_reason
```

### 11.3 `oracle_gap_bridge.csv`

Required columns:

```text
split_bucket
denominator_type
operating_point_id
oracle_reference_id
oracle_reference_denominator_type
oracle_mean_incremental_return
learned_mean_incremental_return
oracle_gap_remaining
oracle_approximation_ratio
oracle_upper_bound_violation
direct_comparison_allowed
hard_gate_used
oracle_gap_bridge_status
blocking_reason
```

### 11.4 `payoff_state_six_cell_decomposition.csv`

Required columns:

```text
split_bucket
denominator_type
operating_point_id
score_action_bucket
label_class
row_n
row_share
mean_y_payoff_h20
mean_continue_value
mean_defend_value
mean_defend_advantage
sum_incremental_return
mean_incremental_return_on_full_denominator
positive_opportunity_cost
negative_avoidance_gain
neutral_contribution
continued_positive_retained
continued_negative_leakage
decomposition_status
blocking_reason
```

### 11.5 `binary_denominator_bridge.csv`

Required columns:

```text
split_bucket
operating_point_id
binary_denominator_row_n
learned_binary_primary_mean_incremental_return
o4_binary_primary_mean_incremental_return
o4_binary_gap_remaining
o4_binary_approximation_ratio
binary_bridge_used_as_primary_gate
binary_bridge_role
binary_bridge_status
blocking_reason
```

### 11.6 `cluster_bootstrap_utility_bridge.csv`

Required columns:

```text
split_bucket
denominator_type
operating_point_id
cluster_key
metric_id
row_n
episode_cluster_n
learned_mean_incremental_return
cluster_bootstrap_utility_ci_low
cluster_bootstrap_utility_ci_high
bootstrap_resample_n
valid_bootstrap_resample_n
bootstrap_random_seed
ci_level
cluster_bootstrap_utility_status
blocking_reason
```

### 11.7 `topk_bootstrap_utility_bridge.csv`

Required columns:

```text
sensitivity_id
split_bucket
denominator_type
operating_point_id
removed_feature_n
removed_feature_names
removed_feature_family_id
base_learned_mean_incremental_return
sensitivity_learned_mean_incremental_return
learned_utility_retention_rate
cluster_bootstrap_utility_ci_low
cluster_bootstrap_utility_ci_high
bootstrap_resample_n
valid_bootstrap_resample_n
topk_bootstrap_status
blocking_reason
```

### 11.8 `validation_stress_utility_bridge.csv`

Required columns:

```text
operating_point_id
validation_row_n
validation_episode_cluster_n
validation_learned_mean_incremental_return
validation_o5_approximation_ratio
validation_top30_payoff_retention_rate
validation_top20_payoff_retention_rate
validation_utility_sign_reversal
validation_stress_role
validation_stress_status
blocking_reason
```

### 11.9 `search_accounting_audit.csv`

Required columns:

```text
search_family
phase_id
run_id
scope_id
primary_operating_point_predeclared
no_model_training
no_model_refit
no_feature_selection_from_utility
no_feature_selection_from_robustness
no_feature_selection_from_validation
no_threshold_tuning_on_robustness
no_threshold_tuning_on_validation
no_oracle_reference_selection_from_results
no_binary_metric_primary_gate
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

### 11.10 `payoff_state_oracle_gap_bridge_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
upstream_18c_refresh_contract_gate
input_artifact_gate
score_matrix_join_gate
oracle_denominator_contract_gate
o5_identity_replay_gate
o5_upper_bound_contract_gate
operating_point_freeze_gate
learned_utility_support_gate
oracle_gap_reduction_gate
positive_sacrifice_gate
payoff_retention_gate
neutral_reconciliation_gate
cluster_bootstrap_utility_gate
topk_sensitivity_gate
validation_stress_gate
binary_boundary_gate
search_accounting_gate
primary_operating_point_id
primary_labelable_full_learned_mean_incremental_return
primary_o5_approximation_ratio
primary_o2_approximation_ratio
primary_o5_gap_remaining
primary_o5_upper_bound_violation
primary_positive_sacrifice_to_avoidance_ratio
primary_top30_payoff_retention_rate
primary_top20_payoff_retention_rate
primary_cluster_bootstrap_utility_ci_low
primary_cluster_bootstrap_utility_ci_high
primary_cluster_bootstrap_valid_resample_n
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

## 12. Decision States and Precedence

Allowed decisions:

```text
18F_payoff_state_policy_preflight_allowed
18F_payoff_state_representation_diagnostic_only
18F_utility_bridge_not_supported
18F_upstream_18c_refresh_contract_blocked
18F_input_artifact_blocked
18F_score_matrix_join_blocked
18F_oracle_gap_contract_blocked
18F_oracle_gap_not_reduced
18F_over_narrow_winner_bridge_blocked
18F_search_accounting_blocked
18F_unclassified_oracle_gap_bridge_blocked
```

Decision precedence:

```text
1. upstream_18c_refresh_contract_gate fail -> 18F_upstream_18c_refresh_contract_blocked
2. input_artifact_gate fail -> 18F_input_artifact_blocked
3. score_matrix_join_gate fail -> 18F_score_matrix_join_blocked
4. oracle_denominator_contract_gate fail or o5_identity_replay_gate fail or o5_upper_bound_contract_gate fail or binary_boundary_gate fail -> 18F_oracle_gap_contract_blocked
5. operating_point_freeze_gate fail -> 18F_oracle_gap_contract_blocked
6. search_accounting_gate fail -> 18F_search_accounting_blocked
7. learned_utility_support_gate fail -> 18F_utility_bridge_not_supported
8. oracle_gap_reduction_gate fail -> 18F_oracle_gap_not_reduced
9. positive_sacrifice_gate fail or payoff_retention_gate fail -> 18F_over_narrow_winner_bridge_blocked
10. cluster_bootstrap_utility_gate fail or topk_sensitivity_gate fail or validation_stress_gate fail -> 18F_payoff_state_representation_diagnostic_only
11. all gates pass -> 18F_payoff_state_policy_preflight_allowed
12. otherwise -> 18F_unclassified_oracle_gap_bridge_blocked
```

If `18F_payoff_state_policy_preflight_allowed`, all policy/backtest/deployment
authorization columns must still be false. The positive decision authorizes only
the next requirement spec for a policy preflight.

## 13. Report Requirements

`payoff_state_oracle_gap_bridge_report.md` must include:

1. One-line decision, next allowed requirement, and no-policy authorization flags.
2. Refreshed 18C handoff replay and score panel hash.
3. Score-to-matrix join proof and utility target replay.
4. Oracle denominator map with explicit O5/O2 labelable_full and O4 binary_primary boundaries.
5. Train-frozen operating points and the primary `defend_bottom30_continue_rest` rule.
6. Learned labelable_full utility by train, robustness, and validation.
7. O5 and O2 gap remaining, approximation ratios, and O5 upper-bound audit.
8. Binary-primary O4 bridge as appendix only.
9. Direct incremental-return decomposition plus positive sacrifice, negative avoidance, neutral contribution, and leakage.
10. Cluster bootstrap CI for learned utility.
11. Top-k and family removal utility sensitivity.
12. Validation stress readout and any sign reversal.
13. Final AFML interpretation: whether payoff-state separability became action-value utility evidence, or remains representation-only.

The report must clearly state:

```text
18F is not a policy, not a backtest, and not a production signal.
```

## 14. Manifest Requirements

`18F_payoff_state_oracle_gap_bridge_manifest.json` must include:

```text
run_id
phase_id
requirement_file_sha256
config_file_sha256
runner_file_sha256
input_artifact_manifest_sha256
source_18c_refresh_manifest_sha256
source_18c_score_panel_sha256
source_18e_matrix_sha256
source_18a_target_contract_manifest_sha256
publishable_table_sha256_by_name
publishable_figure_sha256_by_name
report_sha256
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
o5_upper_bound_contract_gate
primary_operating_point_id
primary_labelable_full_learned_mean_incremental_return
primary_o5_approximation_ratio
primary_o2_approximation_ratio
primary_o5_gap_remaining
primary_o5_upper_bound_violation
primary_positive_sacrifice_to_avoidance_ratio
primary_top30_payoff_retention_rate
primary_top20_payoff_retention_rate
validation_role
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

## 15. Test Requirements

The 18F test suite must include:

```text
test_18f_requires_supported_18c_refresh_handoff
test_18f_rejects_mixed_o4_o5_denominator_subtraction
test_18f_score_panel_joins_exactly_to_18e_matrix
test_18f_replays_o5_incremental_identity
test_18f_blocks_learned_utility_above_o5_upper_bound
test_18f_operating_points_are_train_frozen
test_18f_primary_utility_uses_labelable_full_denominator
test_18f_utility_decomposition_residual_is_exact
test_18f_replays_18c_topk_removed_feature_sets
test_18f_replays_18c_family_removed_feature_sets_from_family_table
test_18f_binary_bridge_is_appendix_only
test_18f_positive_sacrifice_and_retention_gates_block_over_narrow_bridge
test_18f_bootstrap_uses_episode_cluster_id_and_2000_resamples
test_18f_validation_stress_cannot_tune_thresholds
test_18f_search_accounting_blocks_policy_backtest_deployment_signal_and_trading
test_18f_positive_decision_only_allows_requirement_19_policy_preflight
```

At least one controlled positive-path fixture or monkeypatch test must prove:

```text
all hard gates pass -> decision_state = 18F_payoff_state_policy_preflight_allowed
positive decision -> next_allowed_requirement = requirement_19_payoff_state_policy_preflight.md
positive decision -> all policy/backtest/deployment/signal/trading authorization flags remain false
```

At least one controlled denominator-failure fixture must prove:

```text
learned_labelable_full_mean - O4_binary_primary_mean attempted
-> decision_state = 18F_oracle_gap_contract_blocked
```

## 16. Validation Commands

Minimum validation commands:

```bash
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18f_payoff_state_oracle_gap_bridge.py
python experiments/pending/18_payoff_state_representation_research/src/run_18f_payoff_state_oracle_gap_bridge.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18f_payoff_state_oracle_gap_bridge.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18f_payoff_state_oracle_gap_bridge.py -q
```

Before publication:

```bash
git diff --check
git diff --cached --check
```
