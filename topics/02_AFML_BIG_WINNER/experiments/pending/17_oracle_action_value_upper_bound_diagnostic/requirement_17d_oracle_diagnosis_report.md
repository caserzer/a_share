# 需求：17D Oracle Diagnosis Report

## 0. Non-negotiable Scope

17D 是 EP17 的解释与裁决 phase。它只能在 17C 已经输出：

```text
decision_state = EP17C_oracle_robustness_ready_for_diagnosis
next_allowed_requirement = requirement_17d_oracle_diagnosis_report.md
```

后运行。

17D 只回答一个问题：

```text
EP17A-17C 证明的 oracle action value 到底指向哪类下一步研究：
payoff-state representation、feature gap、risk-only signal、delayed observed-state diagnostic、
capacity/execution issue，还是当前 action space 无价值？
```

17D 不得做：

```text
new model training
model refit
feature selection
feature engineering
payoff label redesign
survival threshold tuning
oracle threshold tuning
validation-based selection
robustness-based selection
portfolio construction
capacity optimization
entry policy
exit policy
holding policy
position sizing
portfolio backtest
production signal
deployment authorization
live trading authorization
```

17D 是 readout-only decision-tree layer。它可以从 16D/16E/16X 与 17A/17B/17C 的 publishable machine-readable artifacts 计算解释型聚合表，但不得重跑 16-series 或 17A-17C runner，不得修改上游产物，不得重新 materialize row-level oracle panel。

17D 必须把所有结论表达为 diagnostic / research authorization。任何正向结果最多授权下一步 research requirement，不授权策略、交易、回测或部署。

## 1. Identity

```text
experiment_id = 17_oracle_action_value_upper_bound_diagnostic
phase_id = 17D
run_id = 17D_oracle_diagnosis_report
requirement_file = requirement_17d_oracle_diagnosis_report.md
config_file = configs/config_17d_oracle_diagnosis_report.yaml
runner_file = src/run_17d_oracle_diagnosis_report.py
test_file = tests/test_17d_oracle_diagnosis_report.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths. Artifact identity must use content hash, schema, lineage role, row counts, and required gate values.

## 2. 17C Handoff Gate

17D must read 17C artifacts, but must not trust report prose alone.

Required 17C decision:

```text
decision_state = EP17C_oracle_robustness_ready_for_diagnosis
next_allowed_requirement = requirement_17d_oracle_diagnosis_report.md
input_gate = pass
seventeen_b_contract_gate = pass
row_level_panel_gate = pass
topk_gate = pass
bootstrap_gate = pass
matched_base_gate = pass
delayed_curve_gate = pass
search_accounting_gate = pass
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Allowed 17C non-blocking capacity states:

```text
capacity_constraint_gate in {pass, not_evaluable_nonblocking}
capacity_status in {evaluable, appendix_only_nonblocking}
```

If 17C emits `capacity_reconstruction_gate = pass` and `capacity_constraint_gate = fail`, 17D may read the artifacts but the final decision must be `oracle_execution_capacity_blocked`.

If any required 17C machine-readable artifact is missing, stale, schema-incompatible, or internally inconsistent, 17D must fail closed:

```text
final_decision_state = oracle_lineage_or_denominator_blocked
recommended_next_requirement = none
```

## 3. Required Input Artifacts

Required 17C publishable tables:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/17c_input_gate_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/seventeen_b_contract_validation_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_robustness_primary_summary.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_topk_sensitivity.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_bootstrap_ci.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_matched_base.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_delay_curve.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_capacity_constraint.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/oracle_robustness_decision.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress/search_accounting_audit.csv
```

Required 17C report and manifests:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/reports/oracle_robustness_stress_report.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17C_oracle_robustness_stress_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_robustness_engine_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/input_artifact_manifest_17c.json
```

Required 17B supporting tables for decomposition and oracle semantics:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_ladder_summary.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_six_cell_decomposition.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_action_intensity_frontier.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_neutral_stress.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o2_drawdown_threshold_replay.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o5_action_selection_proof.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_high_upside_threshold_freeze.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17B_oracle_ladder_replay_manifest.json
```

Required Episode 16 reference artifacts for learned-model / current-feature gap:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/sequential_continuation_policy_preflight_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_confusion_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/sequential_continuation_utility_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/six_cell_utility_reconciliation.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/continuation_utility_failure_postmortem_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/failure_arithmetic_attribution.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_aligned_label_power_precheck_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/survival_vs_payoff_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/episode_16_final_report.md
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16D_sequential_continuation_policy_preflight_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16E_sequential_continuation_utility_diagnostic_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16E_postmortem_continuation_utility_failure_decomposition_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16X_payoff_aligned_continuation_label_power_precheck_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/episode_16_final_report_manifest.json
```

17D may read the 16-series reports for narrative consistency, but all gates must be computed from the listed CSV/JSON artifacts. If Episode 16 reference artifacts are unavailable but 17C artifacts pass, 17D must not claim `oracle_value_exists_feature_gap` or `oracle_payoff_state_research_allowed`; it must emit `oracle_lineage_or_denominator_blocked` with `blocking_reason = missing_16_reference_for_feature_gap`.

Every required upstream artifact must be validated against its authoritative phase manifest when that manifest is listed above. Hash, row-count, schema, handoff, and authorization checks must be written to `17d_contract_validation_audit.csv`; stale or unverifiable upstream artifacts are fail-closed contract failures, not report-only warnings.

## 4. Frozen Interpretation Constants

17D must use the following constants. They are interpretation thresholds, not tuned parameters.

```text
primary_split = robustness
primary_cost_bps = 50
primary_q_defend = 0.0
materiality_mean_floor = 0.0025
positive_ci_floor = 0.0
topk_positive_floor = 0.0
matched_min_pass_share = 0.75
delayed_dominance_gap_floor = 0.0025
delayed_retention_floor = 1.0
timing_decay_warn_retention_floor = 0.80
o4_top10_failure_required_for_overdefense_flag = true
```

No validation or robustness outcome may change these constants.

Primary 17D readouts must use the frozen primary observation slice unless a metric is explicitly marked train, validation, delayed, or appendix-only:

```text
primary_filter:
  split_bucket = robustness
  cost_bps = 50
  q_defend = 0.0
```

For 17B/17C tables, every final-decision mean, top-k, bootstrap, matched-base, and support gate must apply `primary_filter` before aggregation. Bootstrap gate minima must include only rows where `bootstrap_primary_role = primary_required`; `calendar_quarter` bootstrap rows are readout-only and cannot block final decision. Top-k gate minima must include all frozen removal families within `primary_filter`. Matched-base pass share must include hard-required matched-base families only. Train rows may be used only for frozen O4 high-upside threshold cutoffs; validation rows may be used only for validation-specific delayed support and report diagnostics.

## 5. Diagnostic Question Families

17D must compute a decision tree with exactly these primary question families:

```text
Q0_lineage_and_contract
Q1_action_space_upper_bound
Q2_label_path_oracle_support
Q3_payoff_preservation_support
Q4_path_risk_support
Q5_current_feature_gap
Q6_delayed_timing_support
Q7_capacity_execution_support
Q8_final_decision
```

Each question must emit:

```text
question_id
question_text
evidence_artifact
evidence_metric
observed_value
threshold_or_expected_value
question_status in {pass, fail, blocked, not_evaluable_nonblocking}
diagnostic_interpretation
```

## 6. Metric Definitions

### 6.1 Action-space upper bound

Use `oracle_robustness_primary_summary.csv`, `oracle_bootstrap_ci.csv`, and `oracle_topk_sensitivity.csv` after `primary_filter`.

O5 is strong if:

```text
O5_perfect_utility_primary.primary_support_gate = pass
O5_perfect_utility_primary.mean_incremental_return >= materiality_mean_floor
O5_perfect_utility_primary.bootstrap_ci_low_min > positive_ci_floor
O5_perfect_utility_primary.topk_removed_mean_min > topk_positive_floor
```

Emit:

```text
o5_upper_bound_mean
o5_upper_bound_trimmed_mean
o5_upper_bound_ci_low_min
o5_upper_bound_topk_min
o5_defended_rate
```

### 6.2 Label/path oracle support

Use primary variants from `oracle_robustness_primary_summary.csv` after `primary_filter`. Variant support gates must reconcile to the corresponding primary rows, bootstrap minima, top-k minima, and matched-base hard-required rows.

Label/path support passes if at least one of:

```text
O1_negative_primary.primary_support_gate = pass
O2_dd_10pct_primary.primary_support_gate = pass
O4_label_positive_primary.primary_support_gate = pass
```

Emit per variant:

```text
mean_incremental_return
trimmed_mean_incremental_return
bootstrap_ci_low_min
topk_removed_mean_min
matched_base_pass_share_min
defended_rate
support_gate
```

### 6.3 O5 headroom gap

Compute:

```text
best_label_path_mean = max(mean_incremental_return of O1/O2/O4 primary variants)
o5_vs_best_label_path_gap = O5_mean - best_label_path_mean
o5_vs_o4_gap = O5_mean - O4_label_positive_primary_mean
o5_vs_o2_gap = O5_mean - O2_dd_10pct_primary_mean
```

These are diagnostic gaps only. They must not be used as tuning criteria.

### 6.4 Path-risk support

Use `oracle_o2_drawdown_threshold_replay.csv`, `oracle_topk_sensitivity.csv`, and `oracle_bootstrap_ci.csv` after `primary_filter`.

For O2 variants:

```text
O2_dd_08pct_stress
O2_dd_10pct_primary
O2_dd_12pct_stress
O2_dd_15pct_stress
O2_dd_20pct_stress
```

Emit:

```text
signed_drawdown_threshold
defended_step_n
defended_rate
mean_incremental_return
trimmed_mean_incremental_return
topk_removed_mean_min
bootstrap_ci_low_min
threshold_support_gate
threshold_value_decay_vs_08pct
```

`threshold_support_gate = pass` for an O2 threshold variant only if the primary-filtered row has positive `topk_removed_mean_min` and positive `bootstrap_ci_low_min`, with bootstrap minima computed from rows where `bootstrap_primary_role = primary_required`.

`path_risk_support_gate = pass` if O2 primary passes and at least three O2 threshold variants have `threshold_support_gate = pass`.

### 6.5 Payoff/upside preservation support

Use O4 primary and high-upside stress variants after `primary_filter`:

```text
O4_label_positive_primary
O4_high_upside_top30_stress
O4_high_upside_top20_stress
O4_high_upside_top10_stress
```

Emit:

```text
defended_step_n
defended_rate
mean_incremental_return
topk_removed_mean_min
bootstrap_ci_low_min
topk_gate
bootstrap_gate
overdefense_flag
```

For `O4_label_positive_primary`, emit `threshold_id = label_positive_primary`, `train_quantile = NA`, and `train_absolute_payoff_cutoff = NA`. For high-upside variants, `threshold_id`, `train_quantile`, and `train_absolute_payoff_cutoff` must come from `oracle_high_upside_threshold_freeze.csv`; train split is allowed only for these frozen cutoff fields, not for primary utility gates.

For `O4_high_upside_top30_stress`, `O4_high_upside_top20_stress`, and `O4_high_upside_top10_stress`, 17D must consume readout-level `topk_gate`, `bootstrap_gate`, `topk_removed_mean_min`, and `bootstrap_ci_low_min` from 17C tables. These values must be variant-specific rows, not copied from `O4_label_positive_primary`.

`payoff_preservation_support_gate = pass` if O4 primary passes and either O4 top30 or O4 top20 passes both top-k and bootstrap gates.

`overdefense_flag = true` if O4 top10 fails top-k or bootstrap while top30/top20 pass. This flag indicates that overly narrow upside preservation destroys continuation value; it does not block payoff-state research.

### 6.6 Current-feature gap

Use Episode 16 artifacts.

17D must map current-feature-gap evidence from the following source fields:

```text
survival_policy_negative_capture = 16D sequential_continuation_policy_preflight_decision.robustness_defense_negative_capture_rate
survival_policy_precision_lift = 16D sequential_continuation_policy_preflight_decision.robustness_defense_precision_lift_vs_binary_negative_base
sixteen_e_utility_interpretation = 16E sequential_continuation_utility_decision.utility_interpretation
sixteen_e_robustness_net_utility = 16E-postmortem failure_arithmetic_attribution.full_denominator_net_utility_total where split_bucket = robustness and cost_bps = 50
sixteen_e_postmortem_directionality_gate = 16E-postmortem continuation_utility_failure_postmortem_decision.directionality_gate
sixteen_x_payoff_rank_ic = 16X payoff_aligned_label_power_precheck_decision.robustness_payoff_probe_rank_ic_spearman
sixteen_x_payoff_minus_survival_margin = 16X payoff_aligned_label_power_precheck_decision.payoff_minus_survival_rank_ic_margin
sixteen_x_payoff_monotone_flag = 16X payoff_aligned_label_power_precheck_decision.payoff_monotone_flag
```

`six_cell_utility_reconciliation.csv` is required as a 16E arithmetic consistency source, not as the primary net-utility source. 17D must use it to verify that all required `split_bucket`, `cost_bps`, `candidate_action`, and `label_class` six-cell rows have `six_cell_reconciliation_status = pass` before trusting the 16E utility decision and the postmortem arithmetic attribution. If this reconciliation fails or required primary cells are missing, `current_feature_gap_gate = blocked` and final decision must fall back according to Section 7 priority, normally `oracle_lineage_or_denominator_blocked` when the failure is a required input/contract issue.

Current-feature gap passes if all are true:

```text
16D decision_state = 16D_policy_preflight_ready_for_utility_diagnostic
16E decision_state = 16E_utility_diagnostic_not_supported
16E primary_return_utility_gate = fail
16E drawdown_avoidance_gate = pass
16E six_cell_utility_reconciliation required primary cells have six_cell_reconciliation_status = pass
16E-postmortem continuation_as_action_mainline_closed = true
16X payoff_separability_gate = fail
16X payoff_aligned_label_redo_authorized = false
```

Emit:

```text
survival_policy_negative_capture
survival_policy_precision_lift
sixteen_e_utility_interpretation
sixteen_e_robustness_net_utility
sixteen_e_postmortem_directionality_gate
sixteen_x_payoff_rank_ic
sixteen_x_payoff_minus_survival_margin
sixteen_x_payoff_monotone_flag
current_feature_gap_gate
```

This gate is what distinguishes `oracle_payoff_state_research_allowed` from a generic oracle upper-bound result.

### 6.7 Delayed timing support

Use `oracle_delay_curve.csv`. Delayed rows are split-specific; each delayed comparison must use `cost_bps = 50` and `q_defend = 0.0` within the row's own `split_bucket`.

For each split:

```text
best_delayed_k = k with max(delayed_mean_incremental_return)
best_delayed_mean
best_delayed_gap_vs_o5_t0
best_delayed_retention_ratio_vs_o5_t0
k10_retention_ratio_vs_o5_t0
```

For each split, choose `best_delayed_k` only from rows with `delayed_curve_gate = pass`. If no delayed row passes for a split, emit `best_delayed_k = NA`, `delayed_decision_supported_gate = fail`, and the split-specific blocking reason.

`delayed_decision_supported_gate = pass` only if:

```text
delayed_curve_gate = pass for all rows
topk_gate = pass for best delayed k in robustness and validation
bootstrap_gate = pass for best delayed k in robustness and validation
matched_base_gate = pass for best delayed k in robustness and validation
best_delayed_gap_vs_o5_t0 >= delayed_dominance_gap_floor in robustness
best_delayed_gap_vs_o5_t0 >= delayed_dominance_gap_floor in validation
best_delayed_retention_ratio_vs_o5_t0 >= delayed_retention_floor in robustness
best_delayed_retention_ratio_vs_o5_t0 >= delayed_retention_floor in validation
```

If delayed means are positive but this gate fails, emit:

```text
timing_sensitivity_candidate = true
oracle_delayed_decision_supported = false
```

This prevents a single robustness split timing artifact from becoming the final decision.

### 6.8 Capacity support

Use `oracle_capacity_constraint.csv`.

```text
capacity_execution_block_gate = fail if
    capacity_reconstruction_gate = pass
    and capacity_constraint_gate = fail

capacity_execution_block_gate = not_evaluable_nonblocking if
    capacity_status = appendix_only_nonblocking
```

If capacity is not evaluable, 17D must state that no execution-capacity conclusion is authorized.

## 7. Final Decision Priority

17D final decision must be exactly one of the EP17 decision labels from the research plan:

```text
oracle_no_action_value_in_current_space
oracle_value_exists_feature_gap
oracle_risk_signal_only_no_payoff_value
oracle_delayed_decision_supported
oracle_execution_capacity_blocked
oracle_payoff_state_research_allowed
oracle_lineage_or_denominator_blocked
```

Priority order is binding:

1. If any required input, schema, manifest hash, contract validation, authorization, or handoff gate fails:

```text
final_decision_state = oracle_lineage_or_denominator_blocked
recommended_next_requirement = none
```

2. Else if O5 upper-bound support fails or 17C decision is not ready:

```text
final_decision_state = oracle_no_action_value_in_current_space
recommended_next_requirement = none
```

3. Else if capacity reconstruction is evaluable and capacity constraint fails:

```text
final_decision_state = oracle_execution_capacity_blocked
recommended_next_requirement = requirement_18_capacity_execution_reconstruction.md
```

4. Else if delayed decision support passes and payoff preservation support does not pass:

```text
final_decision_state = oracle_delayed_decision_supported
recommended_next_requirement = requirement_18_delayed_observed_state_diagnostic.md
```

This rule intentionally precedes the risk-only branch. A validated delayed decision means the action space may still preserve payoff if the observed state is allowed to mature for a frozen delay; in that case the next research question is timing/state observability, not a risk-budget-only overlay.

5. Else if path-risk support passes but payoff preservation support fails:

```text
final_decision_state = oracle_risk_signal_only_no_payoff_value
recommended_next_requirement = requirement_18_risk_budget_overlay_research.md
```

6. Else if payoff preservation support passes and current-feature gap passes:

```text
final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
```

7. Else if O5 upper-bound support passes but none of the more specific positive labels above are selected:

```text
final_decision_state = oracle_value_exists_feature_gap
recommended_next_requirement = requirement_18_feature_gap_source_diagnostic.md
blocking_reason = perfect_utility_only_or_explanatory_support_inconclusive
```

This fallback is mandatory. It covers cases where O5 proves action-space headroom but O1/O2/O4, delayed, capacity, or Episode 16 explanatory support is incomplete, inconclusive, or below the priority thresholds.

The decision table must emit every intermediate gate and the selected priority rank so that the final priority path is auditable.

For the current 17C evidence, the expected non-binding diagnostic orientation is:

```text
payoff_preservation_support_gate = pass
path_risk_support_gate = pass
current_feature_gap_gate = pass
delayed_decision_supported_gate = fail
timing_sensitivity_candidate = true
capacity_execution_block_gate = not_evaluable_nonblocking
expected_final_decision_state = oracle_payoff_state_research_allowed
```

This expected orientation is not a hard-coded output. The implementation must recompute it from artifacts.

## 8. Required Outputs

Publishable tables under:

```text
outputs/publishable/tables/17D_oracle_diagnosis_report/
```

Required tables:

```text
17d_input_gate_audit.csv
17d_contract_validation_audit.csv
oracle_diagnosis_decision_tree.csv
oracle_value_source_attribution.csv
oracle_path_risk_threshold_diagnosis.csv
oracle_upside_preservation_diagnosis.csv
oracle_timing_sensitivity_diagnosis.csv
oracle_learned_model_gap_bridge.csv
oracle_diagnosis_decision.csv
search_accounting_audit.csv
```

Required report:

```text
outputs/publishable/reports/ep17_oracle_action_value_diagnostic_report.md
```

Required manifests:

```text
outputs/manifests/17D_oracle_diagnosis_report_manifest.json
outputs/manifests/oracle_diagnosis_engine_manifest.json
outputs/manifests/input_artifact_manifest_17d.json
```

17D should not emit new figures unless needed for report readability. If figures are emitted, they must be derived only from required input tables and must be listed in the manifest.

## 9. Required Table Schemas

### 9.1 `17d_input_gate_audit.csv`

Required columns:

```text
artifact_key
artifact_role
required_flag
resolved_path
relative_path
source_phase_id
row_count
sha256
schema_status
lineage_status
gate_status
blocking_reason
```

Must include all required 17C, 17B, and 16 reference artifacts. This table checks path resolution, basic schema presence, row counts, and artifact availability. Manifest-expected values and cross-phase handoff checks are authoritative in `17d_contract_validation_audit.csv`.

### 9.2 `17d_contract_validation_audit.csv`

Required columns:

```text
artifact_key
source_phase_id
source_manifest_key
manifest_output_key
validation_check_id
observed_value
expected_value
validation_status
blocking_reason
```

Required validation checks:

```text
17c_decision_handoff_values
17c_required_artifact_sha256
17c_required_artifact_row_count
17c_required_artifact_schema
17b_supporting_artifact_sha256
17b_supporting_artifact_row_count
17b_supporting_artifact_schema
16d_reference_artifact_sha256
16d_reference_artifact_row_count
16d_reference_artifact_schema
16e_reference_artifact_sha256
16e_reference_artifact_row_count
16e_reference_artifact_schema
16e_postmortem_reference_artifact_sha256
16e_postmortem_reference_artifact_row_count
16e_postmortem_reference_artifact_schema
16x_reference_artifact_sha256
16x_reference_artifact_row_count
16x_reference_artifact_schema
required_report_hash_if_manifested
authorization_flags_false
search_accounting_flags_true
```

`validation_status` must be one of:

```text
pass
fail
not_manifested_nonblocking
```

Any `fail` row makes `contract_validation_gate = fail` and final decision must be `oracle_lineage_or_denominator_blocked`. `not_manifested_nonblocking` is allowed only for report hashes that are absent from the authoritative upstream manifest; it is not allowed for required CSV/JSON artifacts.

### 9.3 `oracle_diagnosis_decision_tree.csv`

Required columns:

```text
question_id
question_family
question_text
evidence_artifact
evidence_metric
observed_value
threshold_or_expected_value
question_status
diagnostic_interpretation
final_decision_priority_rank
blocking_reason
```

`question_family` must be one of the families in Section 5.

### 9.4 `oracle_value_source_attribution.csv`

Required columns:

```text
oracle_variant_id
oracle_family
split_bucket
cost_bps
q_defend
observed_step_n
defended_rate
mean_incremental_return
trimmed_mean_incremental_return
bootstrap_ci_low_min
topk_removed_mean_min
matched_base_pass_share_min
o5_gap_vs_variant_mean
support_gate
interpretation_tag
```

`interpretation_tag` allowed values:

```text
perfect_utility_upper_bound
label_negative_support
drawdown_path_risk_support
payoff_preservation_support
weak_or_failed_support
```

### 9.5 `oracle_path_risk_threshold_diagnosis.csv`

Required columns:

```text
oracle_variant_id
signed_drawdown_threshold
defended_step_n
defended_rate
mean_incremental_return
trimmed_mean_incremental_return
topk_removed_mean_min
bootstrap_ci_low_min
threshold_value_decay_vs_08pct
threshold_support_gate
path_risk_support_gate
interpretation
```

### 9.6 `oracle_upside_preservation_diagnosis.csv`

Required columns:

```text
oracle_variant_id
threshold_id
train_quantile
train_absolute_payoff_cutoff
defended_step_n
defended_rate
mean_incremental_return
topk_removed_mean_min
bootstrap_ci_low_min
topk_gate
bootstrap_gate
overdefense_flag
payoff_preservation_support_gate
interpretation
```

### 9.7 `oracle_timing_sensitivity_diagnosis.csv`

Required columns:

```text
split_bucket
best_delayed_k
best_delayed_mean_incremental_return
best_delayed_trimmed_mean_incremental_return
o5_t0_mean_incremental_return
best_delayed_gap_vs_o5_t0
best_delayed_retention_ratio_vs_o5_t0
k10_delayed_retention_ratio_vs_o5_t0
delayed_decision_supported_gate
timing_sensitivity_candidate
interpretation
```

### 9.8 `oracle_learned_model_gap_bridge.csv`

Required columns:

```text
source_phase_id
artifact_key
evidence_metric
observed_value
expected_value
gate_status
feature_gap_component
interpretation
```

Required components:

```text
16d_survival_policy_has_negative_risk_power
16e_return_utility_not_supported
16e_six_cell_reconciliation_consistent
16e_drawdown_reduction_only
16e_postmortem_mainline_closed
16x_payoff_feature_contract_not_supported
17c_oracle_action_value_positive
```

### 9.9 `oracle_diagnosis_decision.csv`

Required columns:

```text
final_decision_state
recommended_next_requirement
lineage_gate
contract_validation_gate
o5_upper_bound_gate
label_path_support_gate
path_risk_support_gate
payoff_preservation_support_gate
current_feature_gap_gate
delayed_decision_supported_gate
timing_sensitivity_candidate
capacity_execution_block_gate
primary_o5_mean_incremental_return
best_label_path_mean_incremental_return
o5_vs_best_label_path_gap
best_delayed_retention_ratio_validation
capacity_status
selected_priority_rank
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

### 9.10 `search_accounting_audit.csv`

Required columns:

```text
search_family
phase_id
no_model_training
no_model_refit
no_survival_threshold_tuning
no_validation_selection
no_robustness_tuning
no_feature_selection
no_payoff_label_redesign
no_oracle_threshold_tuning
no_decision_threshold_tuning
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

## 10. Required Report

`ep17_oracle_action_value_diagnostic_report.md` must be written in Chinese and must include:

1. Final decision state and recommended next requirement.
2. Clear statement that no trading, entry, exit, holding, portfolio backtest, deployment, production signal, or live trading is authorized.
3. 17C handoff and machine-readable artifact validation summary.
4. O5 upper-bound summary and why O5 alone is not a deployable policy.
5. O1/O2/O4 label/path support summary.
6. O5-vs-label/path headroom gap.
7. O2 drawdown threshold curve and interpretation of path-risk value decay.
8. O4 high-upside threshold stress and overdefense interpretation.
9. Episode 16 bridge: why current survival/payoff feature contract failed despite oracle action value.
10. Delayed timing sensitivity and why delayed support is or is not a final decision.
11. Capacity status and execution boundary.
12. Search accounting and authorization flags.
13. Recommended next research direction and explicit non-recommendations.

The report must not claim that oracle results are tradable. It must distinguish:

```text
oracle action-space value
current learned model value
future research authorization
deployment authorization
```

## 11. Manifest Requirements

`17D_oracle_diagnosis_report_manifest.json` must include:

```text
run_id
experiment_id
phase_id
created_at_utc
config_file
config_sha256
requirement_file
requirement_sha256
runner_file
test_file
input_artifact_hashes
output_hashes
row_counts
contract_validation_gate
final_decision_state
recommended_next_requirement
decision_priority_order
materiality_constants
authorization_flags
python_version
```

`oracle_diagnosis_engine_manifest.json` must include formulas for:

```text
contract validation gate
O5 upper-bound gate
label/path support gate
O5 headroom gaps
O2 threshold value decay
O4 overdefense flag
current-feature gap gate
delayed support gate
capacity execution block gate
final decision priority
```

`input_artifact_manifest_17d.json` must list every input path with:

```text
artifact_key
artifact_role
required_flag
source_manifest_key
manifest_output_key
resolved_path
relative_path
source_phase_id
row_count
expected_sha256
observed_sha256
expected_row_count
observed_row_count
schema_status
gate_status
blocking_reason
```

## 12. Search Accounting

17D must emit:

```text
no_model_training = true
no_model_refit = true
no_survival_threshold_tuning = true
no_validation_selection = true
no_robustness_tuning = true
no_feature_selection = true
no_payoff_label_redesign = true
no_oracle_threshold_tuning = true
no_decision_threshold_tuning = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

If any `no_*` field is false, `search_accounting_gate = fail` and final decision must be `oracle_lineage_or_denominator_blocked`.

## 13. Validation Commands

Required commands:

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17d_oracle_diagnosis_report.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/configs/config_17d_oracle_diagnosis_report.yaml

python -m pytest topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/tests -q

git diff --check -- topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic
```

The runner may support `--check-inputs-only`; if present, it must not overwrite full-run reports or manifests except `input_artifact_manifest_17d.json`.

## 14. Required Post-run Assertions

```python
from pathlib import Path
import pandas as pd

base = Path("topics/02_AFML_BIG_WINNER/experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report")
decision = pd.read_csv(base / "oracle_diagnosis_decision.csv").iloc[0]
contract = pd.read_csv(base / "17d_contract_validation_audit.csv")

assert decision["final_decision_state"] in {
    "oracle_no_action_value_in_current_space",
    "oracle_value_exists_feature_gap",
    "oracle_risk_signal_only_no_payoff_value",
    "oracle_delayed_decision_supported",
    "oracle_execution_capacity_blocked",
    "oracle_payoff_state_research_allowed",
    "oracle_lineage_or_denominator_blocked",
}
assert decision["contract_validation_gate"] in {"pass", "fail"}
assert pd.notna(decision["selected_priority_rank"])
assert decision["entry_policy_authorized"] == False
assert decision["exit_policy_authorized"] == False
assert decision["holding_policy_authorized"] == False
assert decision["portfolio_backtest_authorized"] == False
assert decision["model_deployment_authorized"] == False
assert decision["production_signal_authorized"] == False
assert decision["live_trading_authorized"] == False
assert set(contract["validation_status"]).issubset({"pass", "fail", "not_manifested_nonblocking"})
if decision["final_decision_state"] != "oracle_lineage_or_denominator_blocked":
    assert decision["contract_validation_gate"] == "pass"
    assert not (contract["validation_status"] == "fail").any()

tree = pd.read_csv(base / "oracle_diagnosis_decision_tree.csv")
assert {"Q0_lineage_and_contract", "Q1_action_space_upper_bound", "Q8_final_decision"}.issubset(set(tree["question_family"]))
assert not tree["question_status"].isna().any()

source = pd.read_csv(base / "oracle_value_source_attribution.csv")
assert {"O5_perfect_utility_primary", "O1_negative_primary", "O2_dd_10pct_primary", "O4_label_positive_primary"}.issubset(set(source["oracle_variant_id"]))

timing = pd.read_csv(base / "oracle_timing_sensitivity_diagnosis.csv")
assert {"train", "robustness", "validation"}.issubset(set(timing["split_bucket"]))
assert "timing_sensitivity_candidate" in timing.columns

bridge = pd.read_csv(base / "oracle_learned_model_gap_bridge.csv")
assert {
    "16d_survival_policy_has_negative_risk_power",
    "16e_return_utility_not_supported",
    "16e_six_cell_reconciliation_consistent",
    "16x_payoff_feature_contract_not_supported",
    "17c_oracle_action_value_positive",
}.issubset(set(bridge["feature_gap_component"]))
```

## 15. Required Tests

The implementation must include focused tests for:

```text
test_17d_requires_17c_ready_handoff
test_17d_contract_validation_audit_blocks_on_stale_hash
test_17d_blocks_on_missing_16_reference_for_feature_gap
test_17d_decision_priority_prefers_lineage_block_over_positive_readouts
test_17d_decision_priority_falls_back_to_feature_gap_when_o5_only_positive
test_17d_o5_upper_bound_gate_uses_topk_bootstrap_and_materiality
test_17d_payoff_preservation_allows_top30_top20_but_flags_top10_overdefense
test_17d_payoff_preservation_requires_variant_specific_high_upside_topk_bootstrap
test_17d_o4_label_positive_uses_explicit_threshold_id_convention
test_17d_o2_threshold_decay_is_readout_not_tuning
test_17d_primary_filter_excludes_calendar_quarter_bootstrap_from_hard_gate
test_17d_delayed_support_requires_validation_dominance_not_robustness_only
test_17d_capacity_appendix_only_is_nonblocking_but_not_execution_authorization
test_17d_current_feature_gap_uses_16d_16e_16x_machine_tables
test_17d_current_feature_gap_requires_16e_six_cell_reconciliation_pass
test_17d_final_decision_emits_single_label
test_17d_no_policy_authorization_flags_are_true
test_17d_report_hash_is_synced_in_manifest
```

## 16. Implementation Notes

17D should be implemented as a deterministic aggregation/report runner:

```text
read inputs
validate schemas and hashes
compute diagnostic gates
apply final decision priority
write tables
write Chinese report
write manifests
```

It should not require row-level 17B parquet. All required 17D diagnostics must be computable from publishable 17B/17C and 16 reference tables. If an implementation needs row-level data, the requirement must be revised before implementation.

The output report is the final EP17 diagnostic report, not a new experiment proposal. It may recommend a next requirement by name, but it must not create that next requirement.
