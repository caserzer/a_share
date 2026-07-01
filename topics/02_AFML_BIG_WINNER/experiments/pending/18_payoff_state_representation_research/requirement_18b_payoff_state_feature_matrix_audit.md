# Requirement: 18B Payoff-state Feature Matrix and Representation Audit

## 0. Non-negotiable Scope

18B is the second executable phase of EP18. It may start only after 18A
emits:

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
all_hard_gates_pass = true
```

18B answers one question:

```text
Can the EP18 payoff-state targets frozen by 18A be bound to a PIT-valid,
t0-available feature matrix with complete row keys, neutral-preserving
denominators, train-only preprocessing, feature-family coverage, and leakage
controls, without doing model training, separability testing, feature selection,
threshold tuning, or policy/backtest/deployment work?
```

18B's only positive decision is:

```text
decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
```

18B must not output:

```text
model training
model refit
payoff-state separability result
rank IC
binary AUC
precision / recall as a primary gate
feature selection from target correlation
feature selection from robustness or validation
score threshold
entry policy
exit policy
holding policy
position sizing
portfolio construction
portfolio backtest
deployment authorization
production signal
live trading authorization
```

18B may compute feature missingness, feature lineage, train-only preprocessing
parameters, split drift, family coverage, and feature-target binding audits.
18B may compute appendix-only target distribution by predeclared feature-family
buckets, but those readouts must not be used for feature selection, threshold
selection, or any 18B pass/fail gate.

If any upstream 18A handoff, input artifact, target binding, feature lineage,
coverage, preprocessing, forbidden feature, split binding, or search-accounting
check fails, 18B must fail closed with the most specific blocked decision in
section 13.

```text
decision_state = one of the blocked decisions listed in section 13
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18B
run_id = 18B_payoff_state_feature_matrix_audit
requirement_file = requirement_18b_payoff_state_feature_matrix_audit.md
config_file = configs/config_18b_payoff_state_feature_matrix_audit.yaml
runner_file = src/run_18b_payoff_state_feature_matrix_audit.py
test_file = tests/test_18b_payoff_state_feature_matrix_audit.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code
author-machine absolute paths. Artifact identity must use content hash, schema,
lineage role, row counts, and row-key reconciliation as primary identity.

## 2. Required Upstream Handoff Gate

18B is authorized only by 18A, not directly by EP17D or the umbrella EP18 file.

Required 18A decision row:

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
all_hard_gates_pass = true

upstream_authorization_gate = pass
input_artifact_gate = pass
denominator_reconciliation_gate = pass
target_lineage_gate = pass
oracle_reference_denominator_gate = pass
o5_incremental_definition_replay_gate = pass
train_frozen_cutoff_gate = pass
neutral_preservation_gate = pass
path_risk_sign_convention_gate = pass
feature_source_pit_gate = pass
leakage_forbidden_column_gate = pass
search_accounting_gate = pass

entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required 18A handoff artifacts:

```text
outputs/publishable/payoff_state_target_contract.md
outputs/publishable/payoff_state_feature_contract.md
outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/oracle_reference_denominator_map.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_distribution_readout.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/path_risk_target_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/feature_source_inventory.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/leakage_forbidden_column_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/search_accounting_audit.csv
outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
outputs/manifests/input_artifact_manifest_18a.json
outputs/manifests/payoff_state_target_contract_manifest.json
```

If 18A artifacts are missing, stale, schema-incompatible, internally
inconsistent, or not hash-aligned with 18A manifests:

```text
decision_state = 18B_upstream_18a_contract_blocked
next_allowed_requirement = none
```

## 3. Research Questions

18B answers seven matrix-contract questions.

```text
Q1. Can every labelable_full row from 18A be bound exactly once to a PIT-valid
    t0 feature row, preserving train / robustness / validation denominators?

Q2. Can the 18A target definitions be materialized as row-level target columns
    with identical lineage hash and train-frozen payoff cutoff semantics?

Q3. Can the feature matrix include only primary-allowed F1-F5 features from the
    18A feature source inventory, while keeping row identities and split labels
    out of model-feature columns?

Q4. Can feature missingness and family coverage pass with no hidden row drops,
    no neutral-row exclusion, and no split-local imputation?

Q5. Can preprocessing parameters be fit on train rows only and replayed to
    robustness / validation without using target values or split-local stats?

Q6. Can split drift be reported as an audit readout without changing feature
    families, thresholds, or target definitions?

Q7. Can search accounting prove that 18B did no model training, no separability,
    no target-aware feature selection, no policy, no backtest, and no deployment?
```

All failures are fail-closed and must map to a specific 18B blocking decision.

## 4. Allowed and Forbidden Work

18B may:

1. Read 18A target and feature contracts, 18A tables, 18A manifests, and 18A
   report.
2. Read 16C `t0_feature_panel.parquet` as the primary row-level feature source
   after hash/schema/key validation.
3. Read 16C feature contract, lineage, leakage, and coverage audits.
4. Read the 16B row-level label panel used by 18A as the primary target source.
5. Materialize a row-level payoff-state feature matrix under 18B local cache.
6. Add target columns frozen by 18A and feature columns permitted by 18A.
7. Fit imputation and scaling parameters on train rows only.
8. Emit schema, missingness, lineage, coverage, preprocessing, split drift,
   binding, search accounting, decision, manifest, and report artifacts.

18B must not:

1. Train, refit, score, calibrate, or evaluate any model.
2. Compute payoff-state rank IC, separability, AUC, precision, recall, policy
   utility, or oracle gap reduction.
3. Select or remove features using target distribution, target correlation,
   robustness outcomes, validation outcomes, OOS performance, or model metrics.
4. Recompute payoff cutoffs on robustness or validation.
5. Reclassify neutral rows as positive or negative.
6. Use delayed t0+k features in the primary matrix.
7. Use unavailable external feature families as if they existed.
8. Treat O4/O5 oracle information as a deployable signal.
9. Rewrite upstream EP16, EP17, or 18A publishable artifacts.

## 5. Required Input Artifacts

All inputs must be recorded in `input_artifact_audit.csv` and
`input_artifact_manifest_18b.json` with:

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
cache_sha256
cache_hash_validated
cache_hash_manifest_status
cache_schema_validated
cache_key_reconciliation_gate
expected_feature_row_n
observed_feature_row_n
expected_matrix_identity_key_n
observed_matrix_identity_key_n
schema_status
read_status
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
```

### 5.2 18A handoff inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/payoff_state_target_contract.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/payoff_state_feature_contract.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_contract_preflight_report.md
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/oracle_reference_denominator_map.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/o5_incremental_definition_replay.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_distribution_readout.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/path_risk_target_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/feature_source_inventory.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/leakage_forbidden_column_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/search_accounting_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/input_artifact_manifest_18a.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_target_contract_manifest.json
```

### 5.3 Row-level feature and target sources

Required primary feature source:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16C_sequential_continuation_separability_diagnostic/t0_feature_panel.parquet
```

Primary feature-source provenance requirements:

```text
artifact_role = primary_row_level_feature_source
source_kind = validated_local_cache
cache_sha256 = observed sha256 of t0_feature_panel.parquet at 18B runtime
cache_hash_validated = true if source manifest exposes an exact matching hash
cache_hash_manifest_status in {exact_match, not_available_nonblocking}
cache_hash_manifest_status = not_available_nonblocking only when schema/key/row-count checks pass
cache_schema_validated = true
cache_key_reconciliation_gate = pass
expected_feature_row_n = 23,405
observed_feature_row_n = 23,405
expected_matrix_identity_key_n = 23,405
observed_matrix_identity_key_n = 23,405
```

If the 16C manifest does not expose an exact hash for this local-cache parquet,
18B must record `cache_hash_manifest_status = not_available_nonblocking`, record
the observed `cache_sha256`, and fail closed unless schema, row-count, and
identity-key reconciliation pass.

Required feature-source contracts:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_contract.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_lineage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_leakage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_coverage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16C_sequential_continuation_separability_diagnostic_manifest.json
```

Required target source:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
```

Target source filter:

```text
label_id = continuation_survival_h20_no_deep_drawdown
threshold_id = up50pct
horizon_sessions = 20
label_rule_status = pass
target_filter_row_n = 23,405
target_filter_identity_key_n = 23,405
target_filter_split_counts = train 20,245 / robustness 2,496 / validation 664
```

The target source must reconcile to the 18A `full_row_level_target_source`.
No target row outside this filtered, pass-status, identity-key-reconciled
labelable_full panel may enter the 18B matrix.

## 6. Fixed Constants and Expected Values

18B must freeze the following constants before matrix materialization:

```text
primary_threshold_id = up50pct
primary_horizon_sessions = 20
primary_sampling_unit = full_horizon_nonoverlap_step
primary_denominator = labelable_full
primary_cost_bps = 50
primary_q_defend = 0.0
validation_role = stress_readout_only
```

Expected denominator reconciliation:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n
train        | 20,245           | 14,962        | 5,283
robustness   | 2,496            | 1,872         | 624
validation   | 664              | 505           | 159
total        | 23,405           | 17,339        | 6,066
```

Required train-frozen payoff cutoffs:

```text
top30_cutoff = 0.0596330275229357
top20_cutoff = 0.1012285086722715
top10_cutoff = 0.1721071844362347
split_local_recompute_used = false
```

Required 18A target lineage:

```text
y_payoff_h20_lineage_hash = payoff_state_target_contract_manifest.y_payoff_h20_lineage_hash
payoff_cutoff_freeze.y_payoff_lineage_hash == y_payoff_h20_lineage_hash
target_definition_registry.y_payoff_h20.lineage_hash == y_payoff_h20_lineage_hash
```

## 7. Row Keys and Matrix Grain

The 18B feature matrix grain is one row per 18A labelable_full non-overlap step.

Required matrix identity key columns:

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
```

Required split metadata column:

```text
cluster_split_bucket
```

Required key checks:

```text
feature_row_n = 23,405
target_row_n = 23,405
feature_identity_key_n = 23,405
target_identity_key_n = 23,405
bound_matrix_row_n = 23,405
identity_key_join_used = true
split_join_key_used = false
feature_duplicate_key_n = 0
target_duplicate_key_n = 0
unmatched_feature_key_n = 0
unmatched_target_key_n = 0
split_mismatch_n = 0
```

18B must join feature rows to target rows on the matrix identity key only.
`cluster_split_bucket` must be compared after the identity join and must not be
part of the join key. The matrix may keep row keys and split labels as metadata
columns. They must not be marked as model features.

## 8. Target Columns to Bind

18B must bind the following target columns from the 18A target contract.

### 8.1 Continuous payoff target

```text
y_payoff_h20 = step_end_price_ratio_minus_one_for_label_rule
```

Sign convention:

```text
positive y_payoff_h20 = positive continuation payoff
negative y_payoff_h20 = loss over h20
```

### 8.2 Action-value targets

Frozen action semantics:

```text
q_continue = 1.0
q_defend = 0.0
cost_bps = 50
cash_return = 0.0
continue_value = continue_net_return_h20
continue_net_return_h20 = y_payoff_h20 under the 18A O5 replay contract
defend_value = defend_net_return_h20
defend_net_return_h20 = -0.005 under q_defend=0.0 and cost_bps=50
continue_advantage = continue_value - defend_value
defend_advantage = defend_value - continue_value
o5_incremental = max(0, defend_advantage)
```

`o5_incremental` must replay the 18A O5 identity over the full labelable_full
denominator. Non-defended rows contribute zero. 18B must not introduce a second
continue-value convention; if an upstream artifact exposes
`continue_net_return_h20`, it must be numerically reconciled to `y_payoff_h20`
before binding.

### 8.3 Ordinal payoff-state target

Use train-frozen absolute cutoffs from 18A:

```text
state_0 = below_top30_payoff        if y_payoff_h20 < top30_cutoff
state_1 = top30_to_top20_payoff     if top30_cutoff <= y_payoff_h20 < top20_cutoff
state_2 = top20_to_top10_payoff     if top20_cutoff <= y_payoff_h20 < top10_cutoff
state_3 = top10_extreme_payoff      if y_payoff_h20 >= top10_cutoff
```

`state_3` is an over-narrow stress state only. It must not become the primary
18C target unless a later requirement explicitly authorizes that change.

### 8.4 Path-risk auxiliary target

```text
y_signed_max_drawdown_h20 = max_drawdown_from_step_start
risk_state_dd08 = y_signed_max_drawdown_h20 <= -0.08
risk_state_dd10 = y_signed_max_drawdown_h20 <= -0.10
risk_state_dd12 = y_signed_max_drawdown_h20 <= -0.12
```

Drawdown uses signed negative values. Positive absolute drawdown is forbidden
for threshold comparison.

### 8.5 Binary sanity targets

Allowed only as sanity metadata:

```text
label_class in {positive, negative, neutral}
binary_positive_negative
top30_yes_no
top20_yes_no
drawdown_dd10_yes_no
```

Binary sanity targets must be marked:

```text
binary_metric_used_as_primary_gate = false
```

## 9. Primary Feature Columns

18B may materialize only F1-F5 primary-allowed feature families from the 18A
feature source inventory.

### F1 continuation strength / repair persistence

```text
ret_5d
ret_10d
ret_20d
ma_5_20_spread
ma_20_60_spread
distance_to_20d_high
distance_to_60d_high
```

### F2 participation / sponsorship

```text
turnover_rate_20d_mean
turnover_rate_60d_mean
turnover_rate_20d_zscore
volume_20d_zscore
money_20d_zscore
```

### F3 cross-sectional leadership

```text
board_rank_pct
board_rank_by_market_cap
```

### F4 path-risk decoupling

```text
volatility_20d
volatility_60d
max_drawdown_20d
max_drawdown_60d
intraday_range_20d_mean
```

### F5 regime / board / market context

```text
board_bucket_chinext
board_bucket_main_board
log_total_market_cap_cny
tradability_status_ok
```

Expected primary raw feature count:

```text
F1 feature_n = 7
F2 feature_n = 5
F3 feature_n = 2
F4 feature_n = 5
F5 feature_n = 4
primary_raw_feature_n = 23
```

18B must create model-ready columns for these features using train-only
preprocessing. Model-ready columns must be explicitly identified in
`payoff_state_feature_matrix_schema.csv`.

Non-primary families inherited from the 18A feature source inventory:

```text
F6 delayed observed-state appendix = appendix_only, primary_allowed = false
F7 external feature families = unavailable, primary_allowed = false
```

F6/F7 may appear only in coverage and forbidden-family audit readouts. They must
not be materialized as primary raw or model-ready features.

## 10. Forbidden Feature Columns

The following may exist only as row metadata, target columns, or forbidden audit
matches. They must not be marked as model-ready features:

```text
future payoff
step_end price
step_end return
future drawdown
oracle action
O1/O2/O4/O5 future labels
label_class if used as model feature
split id
instrument id as raw model feature
episode cluster id as raw model feature
validation / robustness outcome-derived columns
```

Explicit forbidden model-feature columns include:

```text
step_id
instrument
episode_cluster_id
cluster_split_bucket
step_start_date
step_end_date
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
risk_state_dd08
risk_state_dd10
risk_state_dd12
binary_positive_negative
top30_yes_no
top20_yes_no
drawdown_dd10_yes_no
oracle_reference_id
oracle_action
```

If any forbidden column is marked as a model feature:

```text
decision_state = 18B_forbidden_feature_blocked
next_allowed_requirement = none
```

## 11. Train-only Preprocessing Contract

18B must produce train-only preprocessing parameters for all primary raw
features.

Numeric feature preprocessing:

```text
imputer = train median
center = train median
scale = train interquartile range
if train_iqr == 0 then scale = 1.0 and zero_iqr_flag = true
```

Binary / one-hot feature preprocessing:

```text
cast to 0/1 numeric
imputer = train mode or 0 if missing
center = 0
scale = 1
```

Required checks:

```text
fit_split = train
fit_row_n = 20,245
preprocessing_uses_target_columns = false
preprocessing_uses_robustness_rows = false
preprocessing_uses_validation_rows = false
split_local_imputation_used = false
split_local_scaling_used = false
```

18B may materialize both raw features and model-ready features in the local
matrix. Model-ready features must be derived only from train-frozen parameters.

## 12. Required Outputs

18B must write publishable outputs under:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/
```

Required local cache:

```text
outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
```

Required report:

```text
outputs/publishable/reports/payoff_state_feature_matrix_audit_report.md
```

Required tables:

```text
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/input_artifact_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/upstream_18a_contract_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_target_binding_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_missingness_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/matrix_row_completeness_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/split_drift_feature_readout.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/forbidden_feature_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/search_accounting_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv
```

Optional appendix table:

```text
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/appendix_feature_family_bucket_target_distribution.csv
```

If the optional appendix table is emitted, it must be marked:

```text
appendix_only = true
used_for_feature_selection = false
used_for_gate = false
```

Required manifests:

```text
outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
outputs/manifests/input_artifact_manifest_18b.json
outputs/manifests/payoff_state_feature_matrix_manifest.json
```

### 12.1 Minimum table schemas

`feature_target_binding_audit.csv`:

```text
binding_check_id
target_filter_predicate
target_filter_row_n
target_filter_identity_key_n
target_filter_split_counts
target_label_rule_status_unique
identity_key_columns
split_column
feature_row_n
target_row_n
feature_identity_key_n
target_identity_key_n
bound_matrix_row_n
identity_key_join_used
split_join_key_used
feature_duplicate_key_n
target_duplicate_key_n
unmatched_feature_key_n
unmatched_target_key_n
split_mismatch_n
labelable_step_n_train
labelable_step_n_robustness
labelable_step_n_validation
neutral_step_n_train
neutral_step_n_robustness
neutral_step_n_validation
feature_target_binding_gate
blocking_reason
```

`payoff_state_feature_matrix_schema.csv`:

```text
column_name
column_role
feature_family_id
source_artifact
source_column
dtype
model_ready_feature
raw_feature
target_column
metadata_column
forbidden_as_model_feature
preprocessing_id
lineage_status
blocking_reason
```

Allowed `column_role` values:

```text
row_key
split_metadata
target
raw_feature
model_ready_feature
diagnostic_metadata
```

`feature_missingness_audit.csv`:

```text
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
```

`matrix_row_completeness_audit.csv`:

```text
split_bucket
row_n
primary_raw_feature_n
primary_model_ready_feature_n
row_complete_n
matrix_row_complete_rate
expected_min_matrix_row_complete_rate
row_drop_used_to_improve_complete_rate
feature_complete_rate_gate
blocking_reason
```

`feature_lineage_audit.csv`:

```text
feature_name
feature_family_id
source_artifact
as_of_policy
max_source_pos_minus_step_start_pos
max_source_date_minus_step_start_date
source_lineage_status_16c
source_leakage_status_16c
feature_lineage_gate
blocking_reason
```

`feature_family_coverage.csv`:

```text
feature_family_id
feature_family_name
expected_feature_n
observed_raw_feature_n
observed_model_ready_feature_n
pit_available_status
t0_available_status
primary_allowed
feature_family_coverage_gate
blocking_reason
```

`train_only_preprocessing_audit.csv`:

```text
feature_name
feature_family_id
preprocessing_id
fit_split
fit_row_n
imputer
train_median
train_iqr
scale_value
zero_iqr_flag
preprocessing_uses_target_columns
preprocessing_uses_robustness_rows
preprocessing_uses_validation_rows
split_local_imputation_used
split_local_scaling_used
train_only_preprocessing_gate
blocking_reason
```

`split_drift_feature_readout.csv`:

```text
feature_name
feature_family_id
comparison_split
train_mean
comparison_mean
standardized_mean_diff
train_missing_rate
comparison_missing_rate
missing_rate_diff
split_drift_flag
split_drift_readout_gate
notes
```

`forbidden_feature_audit.csv`:

```text
forbidden_column_family
forbidden_column_pattern
column_name
present_in_matrix
marked_model_ready_feature
forbidden_feature_gate
blocking_reason
```

`search_accounting_audit.csv`:

```text
search_family
phase_id
no_model_training
no_model_refit
no_feature_selection
no_target_correlation_feature_selection
no_robustness_feature_selection
no_validation_feature_selection
no_separability_metric_computed
no_rank_ic_computed
no_binary_metric_used_as_primary_gate
no_entry_policy_authorized
no_exit_policy_authorized
no_holding_policy_authorized
no_portfolio_backtest_authorized
no_model_deployment_authorized
no_production_signal_authorized
no_live_trading_authorized
delayed_features_used_in_primary_model
search_accounting_gate
blocking_reason
```

`payoff_state_feature_matrix_decision.csv`:

```text
decision_state
next_allowed_requirement
all_hard_gates_pass
upstream_18a_contract_gate
input_artifact_gate
feature_target_binding_gate
feature_matrix_schema_gate
feature_complete_rate_gate
feature_lineage_gate
feature_family_coverage_gate
train_only_preprocessing_gate
forbidden_feature_gate
split_binding_gate
split_drift_readout_gate
search_accounting_gate
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

## 13. Required Gates and Decisions

18B pass requires all hard gates to pass:

```text
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
```

If any gate fails:

```text
next_allowed_requirement = none
```

Allowed decisions:

```text
18B_payoff_state_feature_matrix_ready
18B_upstream_18a_contract_blocked
18B_input_artifact_blocked
18B_target_binding_blocked
18B_feature_matrix_schema_blocked
18B_feature_lineage_blocked
18B_feature_matrix_low_coverage
18B_train_only_preprocessing_blocked
18B_forbidden_feature_blocked
18B_split_binding_blocked
18B_search_accounting_blocked
18B_feature_matrix_contract_blocked
```

Decision mapping:

```text
upstream_18a_contract_gate fail -> 18B_upstream_18a_contract_blocked
input_artifact_gate fail -> 18B_input_artifact_blocked
feature_target_binding_gate fail -> 18B_target_binding_blocked
feature_matrix_schema_gate fail -> 18B_feature_matrix_schema_blocked
feature_lineage_gate fail -> 18B_feature_lineage_blocked
feature_complete_rate_gate fail -> 18B_feature_matrix_low_coverage
feature_family_coverage_gate fail -> 18B_feature_matrix_low_coverage
train_only_preprocessing_gate fail -> 18B_train_only_preprocessing_blocked
forbidden_feature_gate fail -> 18B_forbidden_feature_blocked
split_binding_gate fail -> 18B_split_binding_blocked
split_drift_readout_gate fail -> 18B_feature_matrix_contract_blocked
search_accounting_gate fail -> 18B_search_accounting_blocked
otherwise unclassified matrix contract failure -> 18B_feature_matrix_contract_blocked
```

Positive decision:

```text
decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
```

All blocked decisions:

```text
next_allowed_requirement = none
```

No 18B decision may authorize entry, exit, holding, portfolio backtest, model
deployment, production signal, or live trading.

## 14. Gate Details

### 14.1 Feature target binding gate

Required:

```text
bound_matrix_row_n = 23,405
target_filter_row_n = 23,405
target_filter_identity_key_n = 23,405
target_filter_split_counts = train 20,245 / robustness 2,496 / validation 664
target_label_rule_status_unique = pass
identity_key_join_used = true
split_join_key_used = false
feature_duplicate_key_n = 0
target_duplicate_key_n = 0
unmatched_feature_key_n = 0
unmatched_target_key_n = 0
split_mismatch_n = 0
train / robustness / validation labelable counts match 18A
neutral rows remain present in the matrix
```

### 14.2 Feature matrix schema gate

Required:

```text
schema_row_n >= metadata columns + target columns + 23 raw primary features + 23 model-ready primary features
raw_primary_feature_n = 23
model_ready_primary_feature_n = 23
raw_primary_feature_list_exact_match = true
model_ready_primary_feature_list_exact_match = true
extra_model_ready_feature_n = 0
every model-ready primary feature has preprocessing_id
no row key, split metadata, target, diagnostic metadata, or forbidden column is marked model_ready_feature = true
every local matrix column has a matching schema row
feature_matrix_schema_gate = pass
```

If the schema gate fails, 18B must fail closed with
`decision_state = 18B_feature_matrix_schema_blocked`.

### 14.3 Feature complete rate gate

Required:

```text
matrix_overall_primary_feature_finite_rate >= 0.99
each primary feature finite_rate by split >= 0.99
matrix_row_complete_rate >= 0.99
matrix_row_completeness_audit.csv contains split-level row-complete proof
no row may be dropped to improve complete rate
```

If a feature fails finite-rate requirements, 18B must fail closed. It must not
silently remove that feature or select an alternative family.

### 14.4 Feature lineage gate

Required:

```text
all primary features have source_lineage_status_16c = pass
all primary features have source_leakage_status_16c = pass
max_source_pos_minus_step_start_pos <= 0
max_source_date_minus_step_start_date <= 0
```

### 14.5 Feature family coverage gate

Required:

```text
F1 observed_model_ready_feature_n = 7
F2 observed_model_ready_feature_n = 5
F3 observed_model_ready_feature_n = 2
F4 observed_model_ready_feature_n = 5
F5 observed_model_ready_feature_n = 4
F6 primary_allowed = false
F7 primary_allowed = false
F6/F7 status is inherited from 18A feature_source_inventory.csv
```

### 14.6 Train-only preprocessing gate

Required:

```text
fit_split = train
fit_row_n = 20,245
preprocessing_uses_target_columns = false
preprocessing_uses_robustness_rows = false
preprocessing_uses_validation_rows = false
split_local_imputation_used = false
split_local_scaling_used = false
```

### 14.7 Forbidden feature gate

Required:

```text
marked_model_ready_feature = false for every forbidden column match
instrument and episode_cluster_id may appear only as metadata keys
cluster_split_bucket may appear only as split metadata
target columns may not appear as model-ready features
```

### 14.8 Split binding gate

Required:

```text
cluster_split_bucket in {train, robustness, validation}
split counts match 18A target_denominator_reconciliation
no row has missing split
no row has split changed during target-feature binding
```

### 14.9 Split drift readout gate

Split drift is a required diagnostic readout, not a support gate for 18C.

Required:

```text
split_drift_feature_readout.csv exists
all primary features have train-vs-robustness drift rows
all primary features have train-vs-validation drift rows
split_drift_flag is diagnostic-only
split_drift_flag does not remove features
split_drift_flag does not block 18B handoff by itself
```

## 15. Report Requirements

`payoff_state_feature_matrix_audit_report.md` must include:

1. One-line decision and next allowed requirement.
2. 18A handoff replay.
3. Input artifact audit summary.
4. Feature-target binding summary and denominator reconciliation.
5. Feature matrix schema summary.
6. Feature family coverage table.
7. Missingness and complete-rate audit.
8. Feature lineage and leakage audit.
9. Train-only preprocessing summary.
10. Split drift readout summary.
11. Forbidden feature audit.
12. Search accounting and authorization boundary.

The report must state clearly:

```text
18B materializes and audits the feature matrix only.
18B does not prove payoff-state separability.
18B does not select features from target outcomes.
18B does not authorize policy, backtest, deployment, or trading.
```

## 16. Handoff to 18C

18C may begin only if:

```text
decision_state = 18B_payoff_state_feature_matrix_ready
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
all hard gates = pass
```

18C must consume:

```text
payoff_state_feature_matrix.parquet
payoff_state_feature_matrix_schema.csv
feature_target_binding_audit.csv
feature_missingness_audit.csv
matrix_row_completeness_audit.csv
feature_lineage_audit.csv
feature_family_coverage.csv
train_only_preprocessing_audit.csv
forbidden_feature_audit.csv
payoff_state_feature_matrix_decision.csv
18B manifest files
```

18C is the first phase that may evaluate low-capacity payoff-state
separability. 18C still must not authorize policy, portfolio backtest,
deployment, production signal, or live trading unless a later requirement
explicitly authorizes a separate policy preflight.

## 17. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18b_payoff_state_feature_matrix_audit.py
python experiments/pending/18_payoff_state_representation_research/src/run_18b_payoff_state_feature_matrix_audit.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18b_payoff_state_feature_matrix_audit.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18b_payoff_state_feature_matrix_audit.py -q
```

Before publish:

```bash
git diff --check
```
