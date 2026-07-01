# Requirement: 18C Low-capacity Payoff-state Separability Diagnostic

## 0. Non-negotiable Scope

18C is the third executable phase of EP18. It may start only after 18B emits:

```text
decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
all_hard_gates_pass = true
```

18C answers one question:

```text
Can the PIT-valid, t0-available 18B feature matrix rank broad h20 payoff state
out-of-sample with low-capacity, predeclared models, enough to clear strict
labelable_full materiality gates and support an 18D oracle-gap bridge?
```

18C's only positive decision is:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18d_payoff_state_oracle_gap_bridge.md
```

18C must not output or authorize:

```text
entry policy
exit policy
holding policy
position sizing
portfolio construction
portfolio backtest
model deployment
production signal
live trading
score threshold for trading
robustness-tuned threshold
validation-tuned threshold
feature selection from robustness or validation
model family selection from robustness or validation
```

18C is the first EP18 phase allowed to train and evaluate low-capacity
payoff-state models. 18C still remains a diagnostic phase. It may produce
scores, coefficients, rank metrics, bucket readouts, bootstrap confidence
intervals, and appendix binary sanity metrics. It may not convert any score or
bucket into an entry, exit, holding, sizing, or portfolio policy.

If any upstream handoff, input artifact, matrix replay, train-only fitting,
model-registry, metric, baseline, search-accounting, or authorization-boundary
check fails, 18C must fail closed with the most specific blocked decision in
section 14.

```text
decision_state = one of the blocked decisions listed in section 14
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18C
run_id = 18C_payoff_state_separability_diagnostic
requirement_file = requirement_18c_payoff_state_separability_diagnostic.md
config_file = configs/config_18c_payoff_state_separability_diagnostic.yaml
runner_file = src/run_18c_payoff_state_separability_diagnostic.py
test_file = tests/test_18c_payoff_state_separability_diagnostic.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code
author-machine absolute paths. Artifact identity must use content hash, schema,
lineage role, row counts, and row-key reconciliation as primary identity.

## 2. Required Upstream Handoff Gate

18C is authorized only by 18B, not directly by 18A, EP17D, 16X, or 16C.

Required 18B decision row:

```text
decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
all_hard_gates_pass = true

upstream_18a_contract_gate = pass
input_artifact_gate = pass
feature_target_binding_gate = pass
feature_matrix_schema_gate = pass
feature_complete_rate_gate = pass
feature_lineage_gate = pass
feature_family_coverage_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
split_binding_gate = pass
split_drift_readout_gate = pass
search_accounting_gate = pass

entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required 18B handoff artifacts:

```text
outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_target_binding_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_missingness_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/matrix_row_completeness_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/forbidden_feature_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/search_accounting_audit.csv
outputs/publishable/reports/payoff_state_feature_matrix_audit_report.md
outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
outputs/manifests/payoff_state_feature_matrix_manifest.json
outputs/manifests/input_artifact_manifest_18b.json
```

If 18B artifacts are missing, stale, schema-incompatible, internally
inconsistent, or not hash-aligned with 18B manifests:

```text
decision_state = 18C_upstream_18b_contract_blocked
next_allowed_requirement = none
```

## 3. Research Questions

18C answers nine separability questions.

```text
Q1. Can the fixed 18B model-ready F1-F5 feature matrix rank y_payoff_h20 on the
    labelable_full denominator out-of-sample?

Q2. Does the primary low-capacity payoff score clear a predeclared strict
    labelable_full robustness materiality floor without split-local threshold
    recomputation?

Q3. Is the robustness payoff decile curve monotone enough to support a broad
    payoff-state representation rather than a narrow winner target?

Q4. Does the cluster bootstrap lower confidence bound for robustness payoff
    rank IC exclude zero under episode_cluster_id resampling?

Q5. Do top-score buckets lift train-frozen top30 and top20 payoff-state rates
    without treating binary metrics as primary gates?

Q6. Is continue_advantage ranking a lineage replay of y_payoff_h20 ranking, not
    a separate source of evidence?

Q7. Is any apparent support merely a volatility or path-risk defense score
    rather than payoff-state separability?

Q8. Are 16C binary continuation metrics and 18C top30/top20 logistic metrics
    kept as appendix-only sanity readouts?

Q9. Can search accounting prove there was no robustness/validation feature
    selection, model-family selection, threshold tuning, policy, backtest, or
    deployment authorization?
```

All failures are fail-closed and must map to a specific 18C blocking decision.

## 4. Allowed and Forbidden Work

18C may:

1. Read 18B feature matrix, schema, audits, reports, and manifests.
2. Read 18A target and cutoff contracts needed to replay denominator and target
   lineage constraints.
3. Read 16X payoff probe tables as external coarse context only.
4. Read 16C binary separability tables as appendix-only binary continuation
   comparators.
5. Fit predeclared low-capacity models on train rows only.
6. Score train, robustness, and validation rows using train-fitted parameters.
7. Compute rank IC, decile monotonicity, bucket lift, cluster bootstrap CIs,
   coefficient tables, sensitivity readouts, binary sanity metrics, and figures.
8. Emit a diagnostic report and manifests.

18C must not:

1. Add, drop, transform, or select features based on target correlation,
   robustness metrics, validation metrics, or binary sanity metrics.
2. Recompute 18A payoff cutoffs on robustness or validation.
3. Recompute score operating thresholds on robustness or validation for any
   decision gate.
4. Use 16C binary continuation performance as a primary payoff-state gate.
5. Treat top30/top20 binary AUC, average precision, or precision lift as a
   primary support gate.
6. Treat top10 or any narrower winner label as the primary target.
7. Use delayed F6 or unavailable F7 features in a primary model.
8. Use instrument, episode_cluster_id, split labels, row keys, target columns,
   oracle labels, or future h20 outcome fields as model features.
9. Rewrite upstream EP16, EP17, 18A, or 18B publishable artifacts.

## 5. Required Input Artifacts

All inputs must be recorded in `input_artifact_audit.csv` and
`input_artifact_manifest_18c.json` with:

```text
artifact_key
artifact_role
required_flag
resolver_alias
resolved_path
relative_path
source_experiment_id
source_phase_id
row_count
sha256
source_kind
schema_status
read_status
expected_row_n
observed_row_n
expected_identity_key_n
observed_identity_key_n
cache_hash_validated
cache_schema_validated
cache_key_reconciliation_gate
absolute_path_mismatch_ignored
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 5.1 EP18 local planning inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18_payoff_state_representation_research.md
experiments/pending/18_payoff_state_representation_research/requirement_18a_payoff_state_contract_preflight.md
experiments/pending/18_payoff_state_representation_research/requirement_18b_payoff_state_feature_matrix_audit.md
experiments/pending/18_payoff_state_representation_research/requirement_18c_payoff_state_separability_diagnostic.md
```

### 5.2 18B handoff inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_target_binding_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_missingness_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/matrix_row_completeness_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/forbidden_feature_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/search_accounting_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_feature_matrix_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/input_artifact_manifest_18b.json
```

### 5.3 18A target contract inputs

Required for target lineage and cutoff replay:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/payoff_state_target_contract.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_target_contract_manifest.json
```

### 5.4 16X external coarse payoff baseline inputs

16X is an external coarse payoff baseline, not a same-denominator primary
support gate. 16X used a winner-episode probe denominator with robustness row
count 1,872, while 18C primary metrics use the 18B `labelable_full` robustness
row count 2,496. The 16X target column and score construction are also not
identical to 18C. Therefore 16X comparisons are required for context and
continuity with EP16, but they must not pass or fail `baseline_improvement_gate`
or `next_allowed_requirement`.

Required:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/survival_vs_payoff_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_decile_monotonicity_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/cluster_bootstrap_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_aligned_label_power_precheck_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16X_payoff_aligned_continuation_label_power_precheck_manifest.json
```

Required 16X reference values for source-integrity and context only:

```text
16x_payoff_probe_id = payoff_rank_probe_v1
16x_robustness_payoff_rank_ic = 0.05187674283077765
16x_robustness_decile_monotonicity_spearman = 0.16363636363636364
16x_robustness_cluster_bootstrap_rank_ic_ci_low = 0.007705547248002782
```

If observed 16X values differ from these references beyond `1e-12`, 18C must
record the mismatch as source drift and fail closed with
`18C_input_artifact_blocked`. The `1e-12` tolerance is an artifact-integrity
check only; it is not an improvement threshold.

### 5.5 16C appendix-only binary baseline inputs

16C is a binary continuation baseline, not a primary payoff-state baseline.
Required for appendix comparison only:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/grouped_cv_separability_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/oos_separability_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_model_registry.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/sequential_continuation_separability_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_contract.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16C_sequential_continuation_separability_diagnostic_manifest.json
```

16C readouts must never appear in the primary 18C support gate.

## 6. Denominator and Target Contract

18C primary metrics use the full labelable denominator materialized by 18B:

```text
train labelable_full row_n = 20,245
robustness labelable_full row_n = 2,496
validation labelable_full row_n = 664
total labelable_full row_n = 23,405

train neutral row_n = 5,283
robustness neutral row_n = 624
validation neutral row_n = 159
```

Neutral rows must remain in the primary continuous payoff denominator. They
must not be dropped, relabeled, or hidden in a binary-only denominator.

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

Because `continue_advantage` is an affine transform of `y_payoff_h20`, its rank
metrics must be identical to payoff rank metrics up to floating precision.
18C must not count continue-advantage rank IC as independent confirmation.

Ordinal target:

```text
target_id = payoff_ordinal_h20_train_frozen
target_column = payoff_ordinal_state
source_string_to_int_mapping:
  state_0_below_top30_payoff -> 0
  state_1_top30_to_top20_payoff -> 1
  state_2_top20_to_top10_payoff -> 2
  state_3_top10_extreme_payoff -> 3
derived_numeric_column = payoff_ordinal_state_int
state_0 meaning = below train-frozen top30 cutoff
state_1 meaning = train-frozen top30 to top20
state_2 meaning = train-frozen top20 to top10
state_3 meaning = train-frozen top10 extreme
role = ordinal_payoff_state_diagnostic
```

The ordinal diagnostic model must use `payoff_ordinal_state_int`, not raw string
ordering. Any unknown string, missing mapping, or non-deterministic categorical
encoding fails `matrix_contract_replay_gate`.

Train-frozen payoff cutoffs:

```text
top30 cutoff = 0.0596330275229357
top20 cutoff = 0.1012285086722715
top10 cutoff = 0.1721071844362347
split_local_quantile_recompute = false
```

Binary sanity targets:

```text
top30_yes_no = y_payoff_h20 >= train-frozen top30 cutoff
top20_yes_no = y_payoff_h20 >= train-frozen top20 cutoff
binary_positive_negative = 16B positive / negative rows only
```

Binary sanity targets may be used only in appendix readouts. They must not
authorize 18D unless the continuous payoff rank and monotonicity gates also
pass.

## 7. Feature Contract

18C may use only the 23 18B model-ready primary features:

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

Feature-family roles:

```text
F1 continuation strength / repair persistence: primary allowed
F2 participation / sponsorship: primary allowed
F3 cross-sectional leadership: primary allowed
F4 path-risk decoupling: primary allowed but risk-only diagnostic required
F5 regime / board / market context: primary allowed
F6 delayed observed-state appendix: forbidden in primary model
F7 external feature families: unavailable and forbidden
```

18C must not add new engineered features. It may compute model scores and
diagnostic score contributions from train-fitted coefficients. Those scores and
contributions are outputs, not new input features.

## 8. Model Registry and Training Protocol

The model registry is predeclared. 18C must not choose the positive decision by
selecting the best model family on robustness or validation.

Primary support model:

```text
model_id = ridge_payoff_rank_h20_v1
model_family = ridge_regression
target_column = y_payoff_h20
feature_columns = 23 18B model-ready primary features
fit_split = train
fit_row_n = 20,245
hyperparameters = alpha=10.0; fit_intercept=true; solver=auto
used_for_primary_decision = true
```

Auxiliary continuous model:

```text
model_id = elastic_net_payoff_rank_h20_v1
model_family = elastic_net_regression
target_column = y_payoff_h20
feature_columns = 23 18B model-ready primary features
fit_split = train
hyperparameters = alpha=0.0005; l1_ratio=0.10; fit_intercept=true; max_iter=10000; random_state=1818
used_for_primary_decision = false
```

Ordinal diagnostic model:

```text
model_id = ridge_ordinal_payoff_state_v1
model_family = ridge_regression_on_ordinal_state
target_column = payoff_ordinal_state_int
feature_columns = 23 18B model-ready primary features
fit_split = train
hyperparameters = alpha=10.0; fit_intercept=true; solver=auto
used_for_primary_decision = false
```

Binary sanity models:

```text
model_id = ridge_logistic_top30_sanity_v1
model_family = logistic_regression_l2
target_column = top30_yes_no
feature_columns = 23 18B model-ready primary features
fit_split = train
hyperparameters = penalty=l2; C=1.0; class_weight=balanced; solver=liblinear; max_iter=1000; random_state=1818
used_for_primary_decision = false

model_id = ridge_logistic_top20_sanity_v1
model_family = logistic_regression_l2
target_column = top20_yes_no
feature_columns = 23 18B model-ready primary features
fit_split = train
hyperparameters = penalty=l2; C=1.0; class_weight=balanced; solver=liblinear; max_iter=1000; random_state=1818
used_for_primary_decision = false
```

Shallow tree diagnostic:

```text
model_id = shallow_tree_payoff_depth2_v1
model_family = decision_tree_regressor
target_column = y_payoff_h20
feature_columns = 23 18B model-ready primary features
fit_split = train
hyperparameters = max_depth=2; min_samples_leaf=max(50,ceil(0.02*train_row_n)); random_state=1818
used_for_primary_decision = false
```

Baselines:

```text
model_id = intercept_unconditional_payoff_baseline
score = train mean y_payoff_h20
used_for_primary_decision = baseline_only

model_id = volatility20d_defense_baseline
score = -1 * mr_volatility_20d
used_for_primary_decision = risk_only_baseline

model_id = 16x_payoff_rank_probe_v1
score = external 16X payoff probe readout only
denominator = winner_episode_probe_rows_only
robustness_row_n = 1872
comparison_role = external_coarse_context_only
used_for_primary_decision = external_baseline_only

model_id = 16c_ridge_logistic_bar_state_v1
score = external 16C binary continuation readout only
used_for_primary_decision = appendix_only
```

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

The final model for OOS scoring must be fit once on all train rows, then replayed
unchanged to robustness and validation.

## 9. Metric Definitions

Rank IC:

```text
payoff_rank_ic = SpearmanCorr(score, y_payoff_h20)
continue_advantage_rank_ic = SpearmanCorr(score, continue_advantage)
split_scope = train / robustness / validation
primary_support_split = robustness
validation_role = stress_readout_only
```

Continue-advantage rank IC replay must satisfy:

```text
abs(continue_advantage_rank_ic - payoff_rank_ic) <= 1e-12
```

Decile monotonicity:

```text
score_decile_cutoffs = train score quantiles at 0.1, 0.2, ..., 0.9
split_local_score_quantile_recompute = false
decile_index = 1 lowest score bucket through 10 highest score bucket
decile_payoff_monotonicity_spearman = SpearmanCorr(decile_index, mean_y_payoff_h20_by_decile)
```

Top-minus-bottom payoff gap:

```text
top3_deciles = decile_index in {8, 9, 10}
bottom3_deciles = decile_index in {1, 2, 3}
top3_minus_bottom3_payoff_gap = mean_y_payoff_top3_deciles - mean_y_payoff_bottom3_deciles
```

Bucket lift:

```text
score_top30_cutoff = train score 70th percentile
score_top20_cutoff = train score 80th percentile
split_local_score_cutoff_recompute = false
top30_payoff_state_lift = top30_yes_no rate in score_top30 bucket / split unconditional top30_yes_no rate
top20_payoff_state_lift = top20_yes_no rate in score_top20 bucket / split unconditional top20_yes_no rate
```

Cluster bootstrap:

```text
metric = payoff_rank_ic
split_bucket = robustness
cluster_key = episode_cluster_id
resample_unit = episode_cluster_id
bootstrap_resample_n = 2000
bootstrap_ci_level = 0.95
bootstrap_random_seed = 20260629
ci_method = percentile
cluster_bootstrap_rank_ic_ci_low = lower 2.5 percentile
cluster_bootstrap_rank_ic_ci_high = upper 97.5 percentile
```

Top-k removal sensitivity:

```text
base_model = ridge_payoff_rank_h20_v1
coefficient_rank = standardized_abs_coefficient_rank
standardized_coefficient = coefficient * train_std(model_ready_feature)
k_values = 1, 3, 5
operation = zero out selected coefficient contributions without refitting
splits = robustness and validation
role = diagnostic_readout
```

Family-removal sensitivity:

```text
families = F1, F2, F3, F4, F5
operation = zero out all coefficient contributions from the family without refitting
risk_only_focus_family = F4
role = diagnostic_readout and risk-only classification aid
```

Binary sanity metrics:

```text
binary_auc = ROC AUC
average_precision = average precision
precision_lift = average_precision - split unconditional positive rate
targets = top30_yes_no, top20_yes_no, binary_positive_negative
role = appendix_sanity_only
binary_sanity_positive_for_blocked_classification =
  robustness non-16C row with roc_auc >= 0.550000
  or robustness non-16C row with precision_lift > 0.020000
classification_role = blocked-decision precedence aid only, not support gate
```

## 10. Required Outputs

All publishable tables must be CSV with LF line endings and deterministic row
ordering.

Required local-cache artifact:

```text
outputs/local_cache/18C_payoff_state_separability_diagnostic/payoff_state_score_panel.parquet
```

Required publishable tables:

```text
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/upstream_18b_handoff_audit.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/matrix_contract_replay_audit.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_registry.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_cv_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_coefficients.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_oos_rank_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_decile_monotonicity.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_bucket_lift.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_bootstrap_ci.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/topk_removal_sensitivity.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/baseline_comparison_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/binary_sanity_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/search_accounting_audit.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
```

Required figures:

```text
outputs/publishable/figures/18C_payoff_state_separability_diagnostic/payoff_state_decile_curve.png
outputs/publishable/figures/18C_payoff_state_separability_diagnostic/score_vs_payoff_rank_surface.png
```

Required report:

```text
outputs/publishable/reports/payoff_state_separability_diagnostic_report.md
```

Required manifests:

```text
outputs/manifests/18C_payoff_state_separability_diagnostic_manifest.json
outputs/manifests/input_artifact_manifest_18c.json
outputs/manifests/payoff_state_score_panel_manifest.json
```

## 11. Required Table Schemas

### 11.1 `matrix_contract_replay_audit.csv`

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
matrix_row_n = 23405
train_row_n = 20245
robustness_row_n = 2496
validation_row_n = 664
model_ready_feature_n = 23
target_column_n = 19
identity_key_columns = step_id|label_id
identity_key_duplicate_n = 0
full_lineage_key_columns = step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date
full_lineage_key_duplicate_n = 0
target_lineage_hash_y_payoff_h20 = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
target_lineage_hash_continue_advantage = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
target_lineage_hash_payoff_ordinal_state = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
target_lineage_gate_y_payoff_h20 = pass
target_denominator_reconciliation_gate = pass
target_denominator_labelable_replay = 18A_equals_18B_matrix
target_denominator_neutral_replay = 18A_equals_18B_matrix
neutral_preservation_gate = pass
neutral_reclassified_as_positive_or_negative = false
neutral_rows_preserved = true
payoff_ordinal_state_string_mapping_complete = true
continue_advantage_affine_replay_max_abs_diff <= 1e-12
train_frozen_payoff_cutoff_value_replay = pass for top30/top20/top10 values
train_frozen_payoff_cutoff_lineage_hash = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3
split_local_payoff_cutoff_recompute_used = false
train_frozen_payoff_cutoff_gate = pass
```

The primary 18C row identity key is `step_id|label_id`. In the current 18B
matrix, `step_id` is already unique, but `label_id` remains part of the identity
contract so that future multi-target matrices cannot collide silently. The full
lineage key must also be checked as a diagnostic replay of the 18B binding key.

### 11.2 `payoff_state_model_registry.csv`

Required columns:

```text
model_id
model_family
model_role
target_column
feature_column_n
fit_split
hyperparameters
used_for_primary_decision
binary_metric_used_as_primary_gate
training_uses_robustness_rows
training_uses_validation_rows
model_registry_gate
blocking_reason
```

### 11.3 `payoff_state_model_cv_readout.csv`

Required columns:

```text
cv_scheme
model_id
fold_id
train_row_n
test_row_n
train_episode_cluster_n
test_episode_cluster_n
payoff_rank_ic
decile_payoff_monotonicity_spearman
top3_minus_bottom3_payoff_gap
fold_status
```

CV readouts are diagnostics only. They must not select model family, feature
set, score threshold, payoff cutoff, or any OOS gate.

### 11.4 `payoff_state_model_coefficients.csv`

Required columns:

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

Tree diagnostics may report feature importance in the same table with
`coefficient_source = tree_importance`.

For linear models, `standardized_coefficient` must be computed as:

```text
standardized_coefficient = coefficient * train_std(model_ready_feature)
standardized_abs_coefficient_rank = rank(descending abs(standardized_coefficient))
```

Top-k coefficient removal must use `standardized_abs_coefficient_rank`, not raw
`abs(coefficient)`. This is required because 18B model-ready features mix
robust-scaled continuous features with binary F5 features that are mode-imputed
without scaling.

### 11.5 `payoff_state_oos_rank_readout.csv`

Required columns:

```text
split_bucket
model_id
target_id
row_n
episode_cluster_n
rank_ic_spearman
continue_advantage_rank_ic_spearman
continue_advantage_replay_abs_diff
coarse_rank_ic_vs_16x_external_delta
rank_ic_status
```

Primary support row:

```text
split_bucket = robustness
model_id = ridge_payoff_rank_h20_v1
target_id = y_payoff_h20
row_n = 2496
rank_ic_spearman >= 0.080000
coarse_rank_ic_vs_16x_external_delta reported but not a hard gate
```

### 11.6 `payoff_state_decile_monotonicity.csv`

Required columns:

```text
split_bucket
model_id
decile_index
row_n
mean_payoff
mean_continue_advantage
mean_score
score_cutoff_source
decile_payoff_monotonicity_spearman
top3_minus_bottom3_payoff_gap
split_local_score_cutoff_recompute_used
monotonicity_status
```

Primary support requirements:

```text
split_bucket = robustness
model_id = ridge_payoff_rank_h20_v1
score_cutoff_source = train_frozen_score_deciles
split_local_score_cutoff_recompute_used = false
decile_payoff_monotonicity_spearman >= 0.600000
top3_minus_bottom3_payoff_gap > 0
```

### 11.7 `payoff_state_bucket_lift.csv`

Required columns:

```text
split_bucket
model_id
bucket_id
score_cutoff_source
score_cutoff_value
row_n
split_unconditional_event_rate
bucket_event_rate
bucket_lift
target_column
split_local_score_cutoff_recompute_used
bucket_lift_status
```

Required buckets:

```text
score_top30_bucket against top30_yes_no
score_top20_bucket against top20_yes_no
```

Primary support requirements:

```text
robustness top30_payoff_state_lift > 1.0
robustness top20_payoff_state_lift > 1.0
split_local_score_cutoff_recompute_used = false
```

### 11.8 `payoff_state_bootstrap_ci.csv`

Required columns:

```text
split_bucket
model_id
metric_id
point_estimate
cluster_bootstrap_rank_ic_ci_low
cluster_bootstrap_rank_ic_ci_high
bootstrap_ci_level
ci_excludes_zero_flag
bootstrap_resample_n
valid_bootstrap_resample_n
invalid_bootstrap_resample_n
bootstrap_cluster_key
bootstrap_random_seed
bootstrap_status
```

Primary support requirements:

```text
split_bucket = robustness
model_id = ridge_payoff_rank_h20_v1
metric_id = payoff_rank_ic
cluster_bootstrap_rank_ic_ci_low > 0
bootstrap_resample_n = 2000
valid_bootstrap_resample_n = 2000
bootstrap_cluster_key = episode_cluster_id
bootstrap_random_seed = 20260629
```

### 11.9 `topk_removal_sensitivity.csv`

Required columns:

```text
sensitivity_id
split_bucket
model_id
removal_type
removed_feature_n
removed_feature_names
removed_feature_family_id
base_rank_ic_spearman
sensitivity_rank_ic_spearman
rank_ic_retention_rate
sensitivity_status
```

Required sensitivity rows:

```text
top1_abs_coefficient_removed
top3_abs_coefficient_removed
top5_abs_coefficient_removed
family_F1_removed
family_F2_removed
family_F3_removed
family_F4_removed
family_F5_removed
```

### 11.10 `baseline_comparison_readout.csv`

Required columns:

```text
comparison_id
split_bucket
model_id
baseline_id
metric_id
model_denominator_type
baseline_denominator_type
baseline_role
model_value
baseline_value
delta_vs_baseline
required_delta
hard_gate_used
comparison_status
```

Required comparisons:

```text
ridge_payoff_rank_h20_v1 robustness payoff_rank_ic vs volatility20d_defense_baseline, hard_gate_used=true
ridge_payoff_rank_h20_v1 robustness decile_monotonicity vs volatility20d_defense_baseline, hard_gate_used=false
ridge_payoff_rank_h20_v1 robustness payoff_rank_ic vs intercept_unconditional_payoff_baseline, hard_gate_used=false
ridge_payoff_rank_h20_v1 robustness payoff_rank_ic vs 16x_payoff_rank_probe_v1, hard_gate_used=false
ridge_payoff_rank_h20_v1 robustness decile_monotonicity vs 16x_payoff_rank_probe_v1, hard_gate_used=false
ridge_payoff_rank_h20_v1 robustness bootstrap_ci_low vs 16x_payoff_rank_probe_v1, hard_gate_used=false
```

All rows against `16x_payoff_rank_probe_v1` must set:

```text
baseline_role = external_coarse_context_only
model_denominator_type = labelable_full
baseline_denominator_type = winner_episode_probe_rows_only
comparison_status in {external_context_only, source_mismatch_blocked}
hard_gate_used = false
```

Risk-only classification aid:

```text
if primary_rank_ic - volatility20d_defense_rank_ic <= 0.005000
and family_F4_removed_rank_ic_retention_rate < 0.500000
then risk_only_gate = fail
```

### 11.11 `binary_sanity_readout.csv`

Required columns:

```text
split_bucket
model_id
target_column
denominator_type
row_n
positive_n
negative_n
neutral_n
roc_auc
average_precision
split_unconditional_positive_rate
precision_lift
binary_metric_used_as_primary_gate
binary_sanity_status
```

Required:

```text
binary_metric_used_as_primary_gate = false for every row
16C comparisons appear only in appendix rows
```

### 11.12 `search_accounting_audit.csv`

Required columns:

```text
search_family
phase_id
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

### 11.13 `payoff_state_separability_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
all_hard_gates_pass
upstream_18b_contract_gate
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

## 12. Required Figures

`payoff_state_decile_curve.png` must show train, robustness, and validation
mean `y_payoff_h20` by train-frozen score decile for
`ridge_payoff_rank_h20_v1`. It must label robustness as the primary support
split and validation as stress readout only.

`score_vs_payoff_rank_surface.png` must show a deterministic, publishable
relationship between train-fitted score rank and realized payoff rank. It may be
a hexbin, binned surface, or two-dimensional rank heatmap. It must use only
computed score and realized target columns from 18C outputs.

Figures must be regenerated from publishable tables or the local score panel,
and their source hashes must appear in the 18C manifest.

## 13. Required Gates

Positive 18C support requires all hard gates below to pass:

```text
upstream_18b_contract_gate = pass
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

The `0.080000` floor is an intentionally strict go/no-go materiality threshold
for deciding whether the current F1-F5 t0 representation deserves an 18D
oracle-gap bridge. It is not a calibrated probability of success and is not a
same-denominator 16X improvement claim.

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
primary_rank_ic - volatility20d_defense_rank_ic > 0.005000
or family_F4_removed_rank_ic_retention_rate >= 0.500000
```

Binary sanity boundary gate:

```text
binary_metric_used_as_primary_gate = false for every binary sanity row
binary metrics do not determine next_allowed_requirement
16C metrics do not determine next_allowed_requirement
```

Validation readouts:

```text
validation_role = stress_readout_only
validation_stress_evaluable = true if validation row_n = 664 and episode_cluster_n >= 30
validation metrics must be reported
validation metrics must not tune model, feature set, payoff cutoff, score threshold, or support gate
```

## 14. Required Decisions

Allowed decisions:

```text
18C_payoff_state_separability_supported
18C_upstream_18b_contract_blocked
18C_input_artifact_blocked
18C_matrix_contract_replay_blocked
18C_model_registry_blocked
18C_train_only_fit_blocked
18C_oos_tuning_blocked
18C_payoff_state_signal_weak_or_nonmonotone
18C_current_features_reconfirmed_insufficient
18C_binary_only_not_supported
18C_over_narrow_winner_target_blocked
18C_risk_only_no_payoff_state
18C_search_accounting_blocked
18C_separability_contract_blocked
```

Decision mapping:

When multiple blocked interpretations are true, 18C must emit the first
matching decision in this precedence order:

```text
1. upstream_18b_contract_gate fail -> 18C_upstream_18b_contract_blocked
2. input_artifact_gate fail -> 18C_input_artifact_blocked
3. matrix_contract_replay_gate fail -> 18C_matrix_contract_replay_blocked
4. model_registry_gate fail -> 18C_model_registry_blocked
5. train_only_fit_gate fail -> 18C_train_only_fit_blocked
6. oos_no_tuning_gate fail -> 18C_oos_tuning_blocked
7. search_accounting_gate fail -> 18C_search_accounting_blocked
8. risk_only_gate fail -> 18C_risk_only_no_payoff_state
9. all primary, bucket-lift, and binary sanity readouts weak -> 18C_current_features_reconfirmed_insufficient
10. top30/top20 bucket lift passes but continuous rank/monotonicity gates fail -> 18C_over_narrow_winner_target_blocked
11. binary sanity metrics pass but primary rank/monotonicity gates fail -> 18C_binary_only_not_supported
12. rank_ic_support_gate fail or monotonicity_support_gate fail or bootstrap_ci_gate fail or baseline_improvement_gate fail -> 18C_payoff_state_signal_weak_or_nonmonotone
13. otherwise unclassified separability contract failure -> 18C_separability_contract_blocked
```

```text
upstream_18b_contract_gate fail -> 18C_upstream_18b_contract_blocked
input_artifact_gate fail -> 18C_input_artifact_blocked
matrix_contract_replay_gate fail -> 18C_matrix_contract_replay_blocked
model_registry_gate fail -> 18C_model_registry_blocked
train_only_fit_gate fail -> 18C_train_only_fit_blocked
oos_no_tuning_gate fail -> 18C_oos_tuning_blocked
search_accounting_gate fail -> 18C_search_accounting_blocked
risk_only_gate fail -> 18C_risk_only_no_payoff_state
all primary, bucket-lift, and binary sanity readouts weak -> 18C_current_features_reconfirmed_insufficient
top30/top20 bucket lift passes but continuous rank/monotonicity gates fail -> 18C_over_narrow_winner_target_blocked
binary sanity metrics pass but primary rank/monotonicity gates fail -> 18C_binary_only_not_supported
rank_ic_support_gate fail or monotonicity_support_gate fail or bootstrap_ci_gate fail or baseline_improvement_gate fail -> 18C_payoff_state_signal_weak_or_nonmonotone
otherwise unclassified separability contract failure -> 18C_separability_contract_blocked
```

Positive decision:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18d_payoff_state_oracle_gap_bridge.md
```

All blocked decisions:

```text
next_allowed_requirement = none
```

No 18C decision may authorize entry, exit, holding, portfolio backtest, model
deployment, production signal, or live trading.

## 15. Report Requirements

`payoff_state_separability_diagnostic_report.md` must include:

1. One-line decision and next allowed requirement.
2. 18B handoff replay and matrix contract replay.
3. Input artifact audit summary.
4. Model registry and train-only fitting summary.
5. Primary OOS rank readout with robustness as support split and validation as
   stress readout.
6. Decile monotonicity and top3-minus-bottom3 payoff gap.
7. Bucket lift for top30/top20 train-frozen payoff states.
8. Cluster bootstrap CI.
9. Baseline comparison against same-denominator volatility20d and intercept
   baselines, with 16X payoff probe clearly marked as external coarse context.
10. Top-k and family removal sensitivity.
11. Binary sanity appendix, including 16C appendix-only comparison.
12. Search accounting and authorization boundary.

The report must state clearly:

```text
18C evaluates low-capacity payoff-state separability only.
18C does not authorize policy, backtest, deployment, production signal, or trading.
16C binary continuation results are appendix-only and are not primary payoff-state gates.
continue_advantage is an affine replay of y_payoff_h20 and is not independent evidence.
Only 18C_payoff_state_separability_supported may authorize 18D.
```

## 16. Manifest Requirements

`18C_payoff_state_separability_diagnostic_manifest.json` must include:

```text
run_id
phase_id
requirement_file_sha256
config_file_sha256
runner_file_sha256
input_artifact_manifest_sha256
score_panel_sha256
publishable_table_sha256_by_name
publishable_figure_sha256_by_name
report_sha256
decision_state
next_allowed_requirement
all_hard_gates_pass
primary_model_id
primary_split
primary_target_id
robustness_payoff_rank_ic
robustness_decile_payoff_monotonicity_spearman
robustness_cluster_bootstrap_rank_ic_ci_low
coarse_rank_ic_vs_16x_external_delta
validation_role
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

`payoff_state_score_panel_manifest.json` must include row count, split counts,
identity-key columns, score columns, target columns, model ids, and source 18B
matrix hash.

## 17. Handoff to 18D

18D may begin only if:

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18d_payoff_state_oracle_gap_bridge.md
all hard gates = pass
```

18D may consume:

```text
payoff_state_score_panel.parquet
payoff_state_model_registry.csv
payoff_state_model_coefficients.csv
payoff_state_oos_rank_readout.csv
payoff_state_decile_monotonicity.csv
payoff_state_bucket_lift.csv
payoff_state_bootstrap_ci.csv
baseline_comparison_readout.csv
payoff_state_separability_decision.csv
18C manifest files
```

18D may compare the learned payoff-state score to EP17 O4/O5 oracle headroom
only on aligned denominators. 18D still must not define or evaluate a trading
policy unless a later requirement explicitly authorizes a separate policy
preflight.

## 18. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18c_payoff_state_separability_diagnostic.py
python experiments/pending/18_payoff_state_representation_research/src/run_18c_payoff_state_separability_diagnostic.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18c_payoff_state_separability_diagnostic.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18c_payoff_state_separability_diagnostic.py -q
```

Before publish:

```bash
git diff --check
```
