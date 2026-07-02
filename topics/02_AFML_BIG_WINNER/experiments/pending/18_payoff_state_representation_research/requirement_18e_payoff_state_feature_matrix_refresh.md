# Requirement: 18E Payoff-state Feature Matrix Refresh

## 0. Non-negotiable Scope

18E is a representation-construction phase after 18D emitted:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
all_hard_gates_pass = true
recommended_refresh_family_ids = M1|M3|M5|M2
deferred_family_ids = M4
```

18E answers one question:

```text
Can the feature-family recommendations from 18D be materialized into a
neutral-preserving, PIT-valid, t0-available, train-only preprocessed refreshed
payoff-state feature matrix, without doing separability testing, model
training, target-aware feature selection, policy work, backtesting, or
deployment?
```

18E's only positive decision is:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
```

The positive 18E handoff does not mean that the original 18C run is now
supported. It means a future 18C-style separability diagnostic may be rerun
against the refreshed 18E matrix. The deferred EP18F oracle-gap bridge remains
blocked until that future separability diagnostic emits:

```text
decision_state = 18C_payoff_state_separability_supported
```

18E must not:

```text
train a payoff separability model
fit or select a predictive model family
compute rank IC as a decision gate
compute binary AUC or precision as a decision gate
select features from robustness target correlation
select features from validation target correlation
select features from OOS separability metrics
start an oracle-gap bridge
define entry policy
define exit policy
define holding policy
define position sizing
construct a portfolio
run a portfolio backtest
deploy a model
emit a production signal
authorize live trading
drop neutral rows
recompute payoff cutoffs on robustness or validation
use delayed t0+k observed-state features in the primary matrix
add M4 regime/context as a primary feature family without a new requirement
```

18E may:

```text
read 18A/18B/18C/18D artifacts and manifests
replay the 18D handoff and recommended feature-family table
materialize predeclared M1/M2/M3/M5 feature formulas
retain the existing 18B F1-F5 feature families as baseline/current features
audit source lineage, PIT validity, t0 availability, and finite coverage
bind refreshed features to the unchanged labelable_full target denominator
fit imputation and scaling parameters on train rows only
emit a refreshed feature matrix, schema, audits, manifest, and report
emit appendix-only excluded/deferred candidate readouts
```

All blocked decisions must emit:

```text
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18E
run_id = 18E_payoff_state_feature_matrix_refresh
requirement_file = requirement_18e_payoff_state_feature_matrix_refresh.md
config_file = configs/config_18e_payoff_state_feature_matrix_refresh.yaml
runner_file = src/run_18e_payoff_state_feature_matrix_refresh.py
test_file = tests/test_18e_payoff_state_feature_matrix_refresh.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

Path aliases:

```text
TOPIC_ROOT = topics/02_AFML_BIG_WINNER
EP18_ROOT = experiments/pending/18_payoff_state_representation_research
```

All paths must be repo-relative or resolver-alias based. Do not hard-code
author-machine absolute paths. Paths beginning with `experiments/...` are
relative to `TOPIC_ROOT`. Paths beginning with `outputs/...` in this requirement
are local aliases relative to `EP18_ROOT`.

### 1.1 Required 18E Config Contract

`configs/config_18e_payoff_state_feature_matrix_refresh.yaml` must make all
source discovery explicit. The runner must not discover candidate sources by
walking arbitrary directories.

Required config keys:

```yaml
run_id: 18E_payoff_state_feature_matrix_refresh
experiment_id: 18_payoff_state_representation_research
phase_id: 18E

paths:
  research_plan: experiments/pending/18_payoff_state_representation_research/research_plan.md
  requirement_18e: experiments/pending/18_payoff_state_representation_research/requirement_18e_payoff_state_feature_matrix_refresh.md
  requirement_18d: experiments/pending/18_payoff_state_representation_research/requirement_18d_payoff_state_feature_representation_diagnostic.md

  eighteen_a_target_definition_registry: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
  eighteen_a_target_denominator_reconciliation: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
  eighteen_a_payoff_cutoff_freeze: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
  eighteen_a_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json

  eighteen_b_matrix: experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
  eighteen_b_matrix_schema: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
  eighteen_b_feature_target_binding_audit: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_target_binding_audit.csv
  eighteen_b_feature_lineage_audit: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
  eighteen_b_feature_family_coverage: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
  eighteen_b_train_only_preprocessing_audit: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv
  eighteen_b_decision: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv
  eighteen_b_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
  eighteen_b_matrix_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_feature_matrix_manifest.json

  eighteen_d_decision: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/representation_refresh_decision.csv
  eighteen_d_family_prioritization: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/feature_family_candidate_prioritization.csv
  eighteen_d_candidate_inventory: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_inventory.csv
  eighteen_d_candidate_lineage: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_lineage_audit.csv
  eighteen_d_candidate_pit_availability: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_pit_availability_audit.csv
  eighteen_d_orthogonal_readout: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/orthogonal_payoff_information_readout.csv
  eighteen_d_search_accounting: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/search_accounting_audit.csv
  eighteen_d_report: experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_feature_representation_diagnostic_report.md
  eighteen_d_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/18D_payoff_state_feature_representation_diagnostic_manifest.json
  eighteen_d_input_artifact_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/input_artifact_manifest_18d.json

  sixteen_b_label_step_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
  sixteen_b_materialized_step_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/materialized_step_panel.parquet
  sixteen_b_label_panel_readout: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
  sixteen_a_episode_interval_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16A_sequential_sampling_geometry_preflight/episode_interval_panel.parquet
  stock_daily_qfq_dir: data/raw/akshare/day/qfq

source_aliases:
  ep18_current_feature_matrix: [eighteen_b_matrix]
  ep18_row_keys: [eighteen_b_matrix]
  ep18_target_contract: [eighteen_a_target_definition_registry, eighteen_a_payoff_cutoff_freeze]
  eighteen_d_handoff: [eighteen_d_decision, eighteen_d_family_prioritization, eighteen_d_candidate_inventory, eighteen_d_candidate_lineage, eighteen_d_candidate_pit_availability, eighteen_d_orthogonal_readout, eighteen_d_search_accounting, eighteen_d_report, eighteen_d_manifest, eighteen_d_input_artifact_manifest]
  pit_price_path_panel: [stock_daily_qfq_dir]
  pit_money_flow_proxy_panel: [stock_daily_qfq_dir]
  episode_geometry_panel: [sixteen_b_label_step_panel, sixteen_b_materialized_step_panel, sixteen_a_episode_interval_panel, stock_daily_qfq_dir]

expected:
  upstream_18d_decision_state: 18D_feature_representation_refresh_supported
  upstream_18d_next_allowed_requirement: requirement_18e_payoff_state_feature_matrix_refresh.md
  next_allowed_requirement: requirement_18c_payoff_state_separability_diagnostic.md
  next_allowed_requirement_scope: refreshed_matrix_rerun
  total_labelable_step_n: 23405
  train_labelable_step_n: 20245
  robustness_labelable_step_n: 2496
  validation_labelable_step_n: 664
  existing_primary_raw_feature_n: 23
  refresh_primary_raw_feature_n: 26
  refreshed_primary_raw_feature_n: 49
  refreshed_model_ready_feature_n: 49
  appendix_or_deferred_candidate_feature_n: 15
  candidate_min_finite_rate: 0.80
  qfq_path_min_coverage_rate: 0.95
  recommended_refresh_family_ids: [M1, M3, M5, M2]
  refresh_priority_order: [M1, M3, M5, M2]
  deferred_family_ids: [M4]
  primary_refresh_feature_ids:
    - m1_close_location_episode_range
    - m1_close_location_trailing60_range
    - m1_episode_drawdown_pre_t0
    - m1_failed_repair_count_low_to_t0
    - m1_path_transition_entropy_episode
    - m1_pullback_from_episode_high_t0
    - m1_repair_path_efficiency_episode
    - m1_up_down_run_imbalance_20
    - m3_asymmetric_range_position_t0
    - m3_failed_breakout_count_pre_t0
    - m3_upper_shadow_pressure_share_20
    - m3_upside_downside_room_ratio_t0
    - m3_upside_room_to_episode_high
    - m5_bars_since_episode_high_t0
    - m5_bars_since_episode_low
    - m5_episode_age_to_t0
    - m5_high_to_t0_age_ratio
    - m5_low_to_t0_age_ratio
    - m5_nonoverlap_step_index_to_t0
    - m2_flow_concentration_top3_share_20
    - m2_flow_price_divergence_persistence_20
    - m2_money_flow_persistence_trailing20
    - m2_money_flow_reversal_accel_5v20
    - m2_net_signed_money_flow_trailing20
    - m2_positive_money_flow_share_trailing20
    - m2_turnover_compression_20_vs_60
  appendix_only_candidate_feature_ids:
    - m1_return_sign_entropy_trailing20
    - m1_episode_recovery_ratio_to_high_t0
    - m1_path_linearity_r2_low_to_t0
    - m3_downside_crowding_to_episode_low
    - m3_downside_room_to_episode_low_t0
    - m3_vol_adjusted_repair_strength
    - m5_lifecycle_progress_to_t0
    - m5_bars_since_reclaim
    - m5_low_before_high_t0
    - m2_net_signed_money_flow_accel_5v20
    - m2_positive_money_flow_share_accel_5v20
    - m2_net_signed_money_flow_curvature_5_10_20
    - m2_high_amount_negative_bar_share_20
    - m2_signed_flow_volatility_20
    - m4_regime_context_deferred

identity_key_columns:
  - step_id
  - label_id
  - threshold_id
  - horizon_sessions
  - instrument
  - episode_cluster_id
  - step_index
  - step_start_date
  - step_end_date

lineage_key_columns:
  - step_id
  - label_id
  - threshold_id
  - horizon_sessions
  - instrument
  - episode_cluster_id
  - step_index
  - step_start_pos
  - step_start_date

split_column: cluster_split_bucket
target_column: y_payoff_h20

entropy_params:
  window_ids: [episode_low_to_t0, trailing_20, trailing_60]
  return_state_flat_abs_return_max: 0.001
  close_location_bins: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  probability_epsilon: 1.0e-12
  min_observation_n: 5

money_flow_proxy_params:
  amount_column_priority: [money, amount, turnover_value, volume_times_close]
  close_column_priority: [close, qfq_close]
  zero_return_flow_sign: 0
  denominator_epsilon: 1.0e-12
  min_observation_n: 5
```

Optional config paths may be absent without failing `check-inputs`; however any
candidate feature requiring an absent optional source must be marked `blocked` or
`appendix_only` before matrix materialization.

## 2. Required Upstream State

18E is authorized only by 18D. It is not authorized directly by 18C, 18B, 18A,
EP17, or any manual interpretation of the report.

Required 18D decision row:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
all_hard_gates_pass = true
upstream_18c_contract_gate = pass
input_artifact_gate = pass
capacity_vs_representation_gate = pass
candidate_lineage_gate = pass
pit_t0_availability_gate = pass
orthogonal_payoff_information_gate = pass
feature_family_prioritization_gate = pass
search_accounting_gate = pass
recommended_refresh_family_ids = M1|M3|M5|M2
deferred_family_ids = M4
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required 18D handoff artifacts:

```text
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/representation_refresh_decision.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/feature_family_candidate_prioritization.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_inventory.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_lineage_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_pit_availability_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/orthogonal_payoff_information_readout.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/search_accounting_audit.csv
outputs/publishable/reports/payoff_state_feature_representation_diagnostic_report.md
outputs/manifests/18D_payoff_state_feature_representation_diagnostic_manifest.json
outputs/manifests/input_artifact_manifest_18d.json
```

If 18D artifacts are missing, stale, schema-incompatible, internally
inconsistent, or not hash-aligned with 18D manifests:

```text
decision_state = 18E_upstream_18d_contract_blocked
next_allowed_requirement = none
```

18D handoff authority order:

```text
1. representation_refresh_decision.csv
2. 18D_payoff_state_feature_representation_diagnostic_manifest.json
3. feature_family_candidate_prioritization.csv
4. candidate_feature_lineage_audit.csv
5. candidate_feature_pit_availability_audit.csv
6. orthogonal_payoff_information_readout.csv
7. search_accounting_audit.csv
8. payoff_state_feature_representation_diagnostic_report.md
```

The report is explanatory. It must not override the decision table or manifest.

## 3. Research Questions

18E answers eight matrix-refresh questions.

```text
Q1. Can every existing 18B labelable_full row be bound exactly once to a
    refreshed PIT-valid, t0-available feature row?

Q2. Can the 18D-recommended M1/M3/M5/M2 primary refresh features be
    materialized with deterministic formulas and explicit lineage?

Q3. Can 18E retain the existing 18B F1-F5 features without mutating their
    target binding, denominator, or train-only preprocessing semantics?

Q4. Can appendix-only or deferred 18D candidates be kept out of the primary
    model-ready matrix?

Q5. Can refreshed feature missingness and finite coverage pass without hidden
    row drops, neutral-row exclusion, or split-local imputation?

Q6. Can preprocessing parameters for old and new primary features be fit on
    train rows only and replayed unchanged to robustness and validation?

Q7. Can the refreshed matrix carry target columns for downstream diagnostics
    while proving target columns, split labels, and row IDs are not model
    features?

Q8. Can search accounting prove 18E did no model training, no separability
    testing, no target-aware feature selection, no policy, no backtest, and no
    deployment authorization?
```

All failures are fail-closed and must map to a specific 18E blocking decision.

## 4. Allowed and Forbidden Work

18E may:

1. Read 18D decision, prioritization, candidate inventory, lineage, PIT/t0, and
   report artifacts.
2. Read the existing 18B feature matrix and matrix-contract artifacts.
3. Read 18A target/cutoff contracts needed to preserve denominator and target
   lineage.
4. Read 16B/16A episode geometry sources and qfq daily price/amount sources
   explicitly configured for M1/M2/M3/M5 feature construction.
5. Materialize the refreshed row-level feature matrix under 18E local cache.
6. Add the 26 primary refresh features listed in section 8.2.
7. Retain the existing 23 F1-F5 primary raw features from 18B.
8. Fit imputation and scaling parameters on train rows only.
9. Emit source, formula, lineage, PIT/t0, missingness, coverage, preprocessing,
   schema, forbidden-feature, search-accounting, decision, report, and manifest
   artifacts.

18E must not:

1. Train, refit, score, calibrate, or evaluate any payoff-state model.
2. Compute payoff-state rank IC, separability, AUC, precision, recall, policy
   utility, or oracle gap reduction as a decision gate.
3. Add, drop, or transform primary features using target correlation,
   robustness outcomes, validation outcomes, OOS metrics, or model metrics.
4. Recompute payoff cutoffs on robustness or validation.
5. Reclassify neutral rows as positive or negative.
6. Use delayed t0+k features in the primary matrix.
7. Promote `m5_lifecycle_progress_to_t0`, `m5_bars_since_reclaim`, M4 regime
   context, non-representative dedup aliases, or failed train-prior 18D
   candidates into primary model-ready features.
8. Treat O4/O5 oracle information as a deployable signal.
9. Rewrite upstream EP16, EP17, 18A, 18B, 18C, or 18D publishable artifacts.

## 5. Required Input Artifacts

All inputs must be recorded in `input_artifact_audit.csv` and
`input_artifact_manifest_18e.json` with:

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
column_count
sha256
source_kind
cache_sha256
cache_hash_validated
cache_hash_manifest_status
schema_status
read_status
key_reconciliation_status
expected_row_n
observed_row_n
absolute_path_mismatch_ignored
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 5.1 EP18 Local Planning Inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18d_payoff_state_feature_representation_diagnostic.md
experiments/pending/18_payoff_state_representation_research/requirement_18e_payoff_state_feature_matrix_refresh.md
```

### 5.2 18D Handoff Inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/representation_refresh_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/feature_family_candidate_prioritization.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_inventory.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_lineage_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_pit_availability_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/orthogonal_payoff_information_readout.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/search_accounting_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_feature_representation_diagnostic_report.md
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18D_payoff_state_feature_representation_diagnostic_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/input_artifact_manifest_18d.json
```

### 5.3 Existing Matrix and Target Inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_decision.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_target_binding_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/manifests/payoff_state_feature_matrix_manifest.json
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
experiments/pending/18_payoff_state_representation_research/outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
```

### 5.4 Feature Construction Inputs

Required:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/materialized_step_panel.parquet
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16A_sequential_sampling_geometry_preflight/episode_interval_panel.parquet
data/raw/akshare/day/qfq
```

The qfq directory must be audited at instrument level. A missing qfq path for an
instrument may set candidate refresh features to missing for that instrument's
rows, but the total qfq path coverage must satisfy:

```text
qfq_path_coverage_rate >= 0.95
```

Otherwise:

```text
decision_state = 18E_refresh_source_lineage_blocked
next_allowed_requirement = none
```

## 6. Fixed Constants and Expected Values

18E must preserve the 18A/18B target and denominator contract.

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

Expected feature counts:

```text
existing_primary_raw_feature_n = 23
refresh_primary_raw_feature_n = 26
refreshed_primary_raw_feature_n = 49
refreshed_model_ready_feature_n = 49
appendix_or_deferred_candidate_feature_n = 15
```

## 7. Row Keys and Matrix Grain

The 18E refreshed feature matrix grain is one row per 18A/18B labelable_full
non-overlap step.

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

Required row checks:

```text
existing_18b_row_n = 23,405
refreshed_matrix_row_n = 23,405
existing_identity_key_n = 23,405
refreshed_identity_key_n = 23,405
identity_key_join_used = true
split_join_key_used = false
existing_duplicate_key_n = 0
refreshed_duplicate_key_n = 0
unmatched_existing_key_n = 0
unmatched_refreshed_key_n = 0
split_mismatch_n = 0
neutral_row_n = 6,066
neutral_rows_dropped = false
```

18E must join source-derived feature rows to existing 18B rows on the matrix
identity key only. `cluster_split_bucket` must be compared after the identity
join and must not be part of the join key.

## 8. Primary Feature Universe

### 8.1 Existing F1-F5 Features Retained From 18B

18E must retain all 23 existing primary raw F1-F5 features from 18B and carry
their original family identifiers:

```text
F1: ret_5d, ret_10d, ret_20d, ma_5_20_spread, ma_20_60_spread,
    distance_to_20d_high, distance_to_60d_high
F2: turnover_rate_20d_mean, turnover_rate_60d_mean,
    turnover_rate_20d_zscore, volume_20d_zscore, money_20d_zscore
F3: board_rank_pct, board_rank_by_market_cap
F4: volatility_20d, volatility_60d, max_drawdown_20d,
    max_drawdown_60d, intraday_range_20d_mean
F5: board_bucket_chinext, board_bucket_main_board,
    log_total_market_cap_cny, tradability_status_ok
```

The retained F1-F5 features must not be recomputed from scratch unless the
existing 18B matrix is missing or fails schema/key reconciliation. If recomputed
for audit, the 18E report must disclose drift versus 18B and fail closed unless
the recomputation is numerically reconciled.

### 8.2 Primary Refresh Features From 18D

18E must materialize these 26 primary refresh raw features. This list is fixed
from the new 18D report's train-prior, lineage-valid, t0-available,
dedup-representative evidence. 18E must not rerank or shrink it using any
target readout, robustness result, validation result, or model metric.

```text
M1:
  m1_close_location_episode_range
  m1_close_location_trailing60_range
  m1_episode_drawdown_pre_t0
  m1_failed_repair_count_low_to_t0
  m1_path_transition_entropy_episode
  m1_pullback_from_episode_high_t0
  m1_repair_path_efficiency_episode
  m1_up_down_run_imbalance_20

M3:
  m3_asymmetric_range_position_t0
  m3_failed_breakout_count_pre_t0
  m3_upper_shadow_pressure_share_20
  m3_upside_downside_room_ratio_t0
  m3_upside_room_to_episode_high

M5:
  m5_bars_since_episode_high_t0
  m5_bars_since_episode_low
  m5_episode_age_to_t0
  m5_high_to_t0_age_ratio
  m5_low_to_t0_age_ratio
  m5_nonoverlap_step_index_to_t0

M2:
  m2_flow_concentration_top3_share_20
  m2_flow_price_divergence_persistence_20
  m2_money_flow_persistence_trailing20
  m2_money_flow_reversal_accel_5v20
  m2_net_signed_money_flow_trailing20
  m2_positive_money_flow_share_trailing20
  m2_turnover_compression_20_vs_60
```

These features are authorized by the 18D train-prior lineage and orthogonality
handoff. 18E must not recompute target correlation to decide whether to include
or exclude them.

Expected primary refresh family coverage:

```text
M1 primary_refresh_feature_n = 8
M3 primary_refresh_feature_n = 5
M5 primary_refresh_feature_n = 6
M2 primary_refresh_feature_n = 7
M4 primary_refresh_feature_n = 0
```

### 8.3 Appendix-only or Deferred Candidate Features

The following 18D candidates must not be marked as primary model-ready features
in 18E:

```text
m1_return_sign_entropy_trailing20
m1_episode_recovery_ratio_to_high_t0
m1_path_linearity_r2_low_to_t0
m3_downside_crowding_to_episode_low
m3_downside_room_to_episode_low_t0
m3_vol_adjusted_repair_strength
m5_lifecycle_progress_to_t0
m5_bars_since_reclaim
m5_low_before_high_t0
m2_net_signed_money_flow_accel_5v20
m2_positive_money_flow_share_accel_5v20
m2_net_signed_money_flow_curvature_5_10_20
m2_high_amount_negative_bar_share_20
m2_signed_flow_volatility_20
m4_regime_context_deferred
```

Reasons inherited from 18D:

```text
m1_return_sign_entropy_trailing20 = failed volatility/participation orthogonality
m1_episode_recovery_ratio_to_high_t0 = dedup alias of m1_close_location_episode_range
m1_path_linearity_r2_low_to_t0 = failed train-prior orthogonality
m3_downside_crowding_to_episode_low = failed train-prior orthogonality
m3_downside_room_to_episode_low_t0 = dedup alias / failed train-prior orthogonality
m3_vol_adjusted_repair_strength = failed train-prior orthogonality
m5_lifecycle_progress_to_t0 = full_episode_boundary_after_t0 look-ahead block
m5_bars_since_reclaim = finite_rate 0.795386 below 0.80 floor
m5_low_before_high_t0 = failed train-prior orthogonality
m2_net_signed_money_flow_accel_5v20 = failed f2_extended_participation_money orthogonality
m2_positive_money_flow_share_accel_5v20 = failed f2_extended_participation_money orthogonality
m2_net_signed_money_flow_curvature_5_10_20 = failed f2_extended_participation_money orthogonality
m2_high_amount_negative_bar_share_20 = failed f2_extended_participation_money orthogonality
m2_signed_flow_volatility_20 = failed f2_extended_participation_money orthogonality
m4_regime_context_deferred = no new PIT context and family deferred
```

If emitted, these columns must be marked:

```text
appendix_only = true
primary_model_feature = false
used_for_gate = false
used_for_downstream_separability = false
```

### 8.4 18D Candidate Replay Gate

18E must emit `refresh_candidate_replay_audit.csv` with one row per 18D
candidate feature. This audit is the hard evidence behind
`feature_family_recommendation_replay_gate`.

The replay audit must classify every candidate into exactly one expected 18E
role:

```text
primary_refresh
appendix_only
deferred
```

Primary refresh candidates must satisfy all inherited 18D conditions:

```text
candidate_feature_id in expected.primary_refresh_feature_ids
candidate_family_id in expected.recommended_refresh_family_ids
candidate_primary_allowed_after_lineage = true
pit_primary_allowed = true
candidate_appendix_only = false
train_prior_row_found = true
recommendation_eligible_residualization = true
dedup_group_representative = true
orthogonal_payoff_candidate = true
```

Expected residualization control sets:

```text
M1 = base_vol_participation
M3 = base_vol_participation
M5 = base_vol_participation
M2 = f2_extended_participation_money
```

M2 must fail replay if the only qualifying row is from
`base_vol_participation`; 18D made that control set diagnostic-only for M2.

Appendix/deferred candidates must satisfy:

```text
candidate_feature_id in expected.appendix_only_candidate_feature_ids
primary_model_feature = false
used_for_downstream_separability = false
```

Specific inherited blocks must be replayed exactly:

```text
m5_lifecycle_progress_to_t0 -> full_episode_boundary_after_t0
m5_bars_since_reclaim -> candidate_finite_rate_below_floor
m4_regime_context_deferred -> m4_deferred_by_default or family deferred
```

If any 18D candidate is missing, duplicated, classified into multiple roles,
or mismatches the inherited lineage/PIT/orthogonality state:

```text
feature_family_recommendation_replay_gate = fail
decision_state = 18E_refresh_candidate_replay_blocked
next_allowed_requirement = none
```

## 9. Refresh Feature Formula Contract

All refresh features must be deterministic, PIT-valid, t0-available, and
computed before any target readout.

### 9.1 Shared Price Path Rules

```text
price_source = qfq daily path
required_qfq_columns = date|open|high|low|close|money|turnover_rate|instrument
optional_qfq_fallback_columns = amount|turnover_value|volume
feature_window_end_pos <= step_start_pos
feature_window_end_date <= step_start_date
minimum_observation_count = 5
uses_step_end_outcome = false
uses_future_h20_path = false
uses_oracle_label = false
uses_payoff_target = false
uses_binary_target = false
```

QFQ source resolution:

```text
qfq path must be sorted by instrument,date
qfq position index is zero-based within each instrument after date sort
qfq_close_t0 = close at step_start_pos
amount_proxy priority = money, amount, turnover_value, volume * close
amount_proxy selected source must be recorded per instrument in source audit
volume * close may be used only if volume exists and close is finite
turnover_rate source = turnover_rate
```

Shared t0-frozen episode geometry:

```text
episode_segment_t0 = qfq rows [cluster_start_pos, step_start_pos]
episode_low_pos_t0 = first argmin(qfq low over episode_segment_t0)
episode_high_pos_t0 = first argmax(qfq high over episode_segment_t0)
episode_low_price_t0 = qfq low at episode_low_pos_t0
episode_high_price_t0 = qfq high at episode_high_pos_t0
qfq_close_episode_low_t0 = qfq close at episode_low_pos_t0
qfq_close_episode_high_t0 = qfq close at episode_high_pos_t0
```

The low/high positions must be derived only from bars with
`source_pos <= step_start_pos`. If `cluster_start_pos > step_start_pos`, if the
qfq path is not reconciled to `step_start_date`, or if the segment has fewer
than `minimum_observation_count` valid rows, all dependent refresh features are
missing and the row-level lineage must record the reason.

Episode-local windows:

```text
episode_low_to_t0 = [episode_low_pos_t0, step_start_pos]
trailing_5 = [max(first_valid_qfq_pos, step_start_pos - 4), step_start_pos]
trailing_10 = [max(first_valid_qfq_pos, step_start_pos - 9), step_start_pos]
trailing_20 = [max(first_valid_qfq_pos, step_start_pos - 19), step_start_pos]
trailing_60 = [max(first_valid_qfq_pos, step_start_pos - 59), step_start_pos]
```

### 9.2 M5 Episode Position and Maturity

```text
m5_bars_since_episode_low = step_start_pos - episode_low_pos_t0

m5_bars_since_episode_high_t0 = step_start_pos - episode_high_pos_t0

m5_episode_age_to_t0 = step_start_pos - cluster_start_pos

m5_nonoverlap_step_index_to_t0 =
    floor((step_start_pos - cluster_start_pos) / horizon_sessions)

m5_low_to_t0_age_ratio =
    (step_start_pos - episode_low_pos_t0) /
    max(step_start_pos - cluster_start_pos, 1)

m5_high_to_t0_age_ratio =
    (step_start_pos - episode_high_pos_t0) /
    max(step_start_pos - cluster_start_pos, 1)
```

`m5_lifecycle_progress_to_t0` is explicitly blocked from the primary matrix.
The new 18D report proved it depends on a full episode boundary after t0:

```text
m5_lifecycle_progress_to_t0 blocking_reason = full_episode_boundary_after_t0
future_source_dependency_row_n = 23405
future_normalizer_dependency_row_n = 23405
finite_candidate_value_row_n = 0
```

18E may emit it only in appendix audit tables with:

```text
appendix_only = true
primary_model_feature = false
used_for_downstream_separability = false
```

If any primary M5 feature requires `cluster_end_pos`, full episode completion,
future h20 payoff path, or current row step_end outcome:

```text
decision_state = 18E_pit_t0_availability_blocked
next_allowed_requirement = none
```

### 9.3 M3 Payoff Asymmetry Context

```text
m3_upside_room_to_episode_high =
    (episode_high_price_t0 - qfq_close_t0) / qfq_close_t0

m3_upside_downside_room_ratio_t0 =
    (episode_high_price_t0 - qfq_close_t0) /
    (qfq_close_t0 - episode_low_price_t0)

m3_asymmetric_range_position_t0 =
    2 * (qfq_close_t0 - episode_low_price_t0) /
    (episode_high_price_t0 - episode_low_price_t0) - 1

m3_failed_breakout_count_pre_t0 =
    count candidate pos where:
      pos in [cluster_start_pos + 1, step_start_pos - 5]
      qfq_high[pos] >= max(qfq_high over [cluster_start_pos, pos - 1])
      min(qfq_close over [pos + 1, pos + 5]) < qfq_low[pos]

m3_upper_shadow_pressure_share_20 =
    mean((qfq_high - max(qfq_open, qfq_close)) / (qfq_high - qfq_low))
    over valid trailing_20 candles
```

Where:

```text
episode_high_price_t0 = max(qfq_high over [cluster_start_pos, step_start_pos])
qfq_close_t0 = qfq close at step_start_pos
episode_price_range_t0 = episode_high_price_t0 - episode_low_price_t0
downside_room_t0 = qfq_close_t0 - episode_low_price_t0
```

The feature must not use any high after `step_start_pos`.

M3 denominator guards:

```text
if qfq_close_t0 <= denominator_epsilon:
    m3_upside_room_to_episode_high = missing
    blocking_reason = nonpositive_qfq_close_t0

if downside_room_t0 <= denominator_epsilon:
    m3_upside_downside_room_ratio_t0 = missing
    blocking_reason = zero_downside_room

if episode_price_range_t0 <= denominator_epsilon:
    m3_asymmetric_range_position_t0 = missing
    blocking_reason = zero_price_range
```

For `m3_failed_breakout_count_pre_t0`, a failed breakout attempt may only use
bars inside `[cluster_start_pos, step_start_pos]`. Any follow-through check must
be truncated at `step_start_pos`; no bar after t0 may be inspected.

For `m3_upper_shadow_pressure_share_20`, a valid candle must satisfy:

```text
qfq_open, qfq_high, qfq_low, qfq_close are finite
candle_range = qfq_high - qfq_low
candle_range > denominator_epsilon
```

If fewer than 5 valid trailing-20 candles remain, the feature is missing with
`blocking_reason = insufficient_valid_candles_or_zero_range`.

### 9.4 M1 Episode-local Morphology

```text
m1_close_location_episode_range =
    (qfq_close_t0 - episode_low_price_t0) /
    (episode_high_price_t0 - episode_low_price_t0)

m1_episode_drawdown_pre_t0 =
    min(qfq_low_t / running_max(qfq_close up to t) - 1)
    for t in [cluster_start_pos, step_start_pos]

m1_pullback_from_episode_high_t0 =
    qfq_close_t0 / episode_high_price_t0 - 1

m1_close_location_trailing60_range =
    (qfq_close_t0 - min(qfq_low over trailing_60)) /
    (max(qfq_high over trailing_60) - min(qfq_low over trailing_60))

m1_up_down_run_imbalance_20 =
    longest_positive_close_diff_run(trailing_20) -
    longest_negative_close_diff_run(trailing_20)

m1_failed_repair_count_low_to_t0 =
    count candidate pos where:
      pos in [episode_low_pos_t0 + 3, step_start_pos - 5]
      qfq_close[pos] > max(qfq_close over [pos - 3, pos - 1])
      min(qfq_close over [pos + 1, pos + 5]) / qfq_close[pos] - 1 <= -0.05
      max(qfq_close over [pos + 1, pos + 5]) <= qfq_close[pos]
```

`m1_close_location_episode_range` must be clipped to `[0, 1]` only after
recording an audit flag if raw value is outside `[0, 1]`. If
`episode_high_price_t0 == episode_low_price_t0`, the feature is missing with
`blocking_reason = zero_price_range`.

`m1_close_location_trailing60_range` must use the same range guard. If
`max(qfq_high over trailing_60) - min(qfq_low over trailing_60) <=
denominator_epsilon`, the feature is missing with
`blocking_reason = zero_trailing60_price_range`.

`m1_episode_drawdown_pre_t0` intentionally uses qfq low divided by running max
qfq close as a drawdown proxy; this mixed low/close definition is inherited from
18D and must be recorded in the formula registry.

Return-state binning:

```text
ret_t = qfq_close[t] / qfq_close[t - 1] - 1
state_t = down if ret_t < -0.001
state_t = flat if abs(ret_t) <= 0.001
state_t = up if ret_t > 0.001
transition_state_t = state_{t-1} -> state_t across episode_low_to_t0
```

Path transition entropy:

```text
p_ij = (transition_count_ij + probability_epsilon) /
       (sum(transition_count_ij) + 9 * probability_epsilon)

m1_path_transition_entropy_episode =
    -sum_{i,j in {down,flat,up}} p_ij * ln(p_ij) / ln(9)
```

Repair path efficiency:

```text
m1_repair_path_efficiency_episode =
    abs(qfq_close_t0 - qfq_close_episode_low_t0) /
    sum(abs(diff(qfq_close over [episode_low_pos_t0, step_start_pos])))
```

If the denominator is zero or nonfinite, the feature is missing with
`blocking_reason = zero_repair_path_distance`.

For `m1_failed_repair_count_low_to_t0`, repair-attempt and follow-through
checks must stop at `step_start_pos`. No repair success/failure condition may
use the future h20 path or the current row `step_end_date`.

Both count features must use inclusive 5-bar post-attempt windows ending no
later than `step_start_pos`. If the required future-within-pre-t0 window is not
fully available, that candidate attempt is skipped; the feature itself remains
defined as the count of complete pre-t0 attempts.

### 9.5 M2 Supply and Pressure Dynamics

Money-flow proxy source resolution:

```text
amount_t source priority = money, amount, turnover_value, volume * close
close_t source priority = close, qfq_close
zero close-to-close return -> signed_money_proxy_t sign = 0
nonpositive or nonfinite amount_t is excluded from the window denominator
minimum observation count for any money-flow window = 5
```

Daily signed-flow proxy:

```text
signed_money_proxy_t = amount_t * sign(close_t - close_{t-1})
```

Valid signed-flow sequence and reversal rate:

```text
valid_signed_flow_row_t =
    isfinite(amount_t) and amount_t > denominator_epsilon and
    isfinite(sign(close_t - close_{t-1}))

The first row in a window is invalid for signed-flow statistics because it has
no prior close inside that window.

signed_flow_sign_sequence(window) =
    sign(signed_money_proxy_t) for valid signed-flow rows in date order

reversal_rate(window) =
    mean(signed_flow_sign_sequence[i] != signed_flow_sign_sequence[i - 1])
    for i = 1..len(sequence)-1
```

If `len(signed_flow_sign_sequence) < 2`, `reversal_rate(window)` is missing
with `blocking_reason = insufficient_signed_flow_sign_pairs`.

Primary M2 formulas:

```text
m2_net_signed_money_flow_trailing20 =
    sum(signed_money_proxy_t) /
    (sum(abs(amount_t)) + denominator_epsilon)

m2_positive_money_flow_share_trailing20 =
    sum(amount_t where close_t > close_{t-1}) /
    (sum(amount_t) + denominator_epsilon)

m2_money_flow_persistence_trailing20 =
    mean(sign(signed_money_proxy_t) == sign(signed_money_proxy_{t-1}))

m2_turnover_compression_20_vs_60 =
    mean(turnover_rate over trailing_20) /
    mean(turnover_rate over trailing_60)

m2_money_flow_reversal_accel_5v20 =
    reversal_rate(signed_money_proxy over trailing_5) -
    reversal_rate(signed_money_proxy over trailing_20)

m2_flow_price_divergence_persistence_20 =
    mean(divergence_flag_j) over valid 5-row subwindows j inside trailing_20

m2_flow_concentration_top3_share_20 =
    sum(top 3 abs(signed_money_proxy_t) over trailing_20) /
    (sum(abs(signed_money_proxy_t) over trailing_20) + denominator_epsilon)
```

`m2_flow_price_divergence_persistence_20` subwindow contract:

```text
trailing_20 must contain 20 ordered rows indexed 0..19
subwindow_j = rows [j - 4, j] for j = 4..19
expected_subwindow_n = 16

subwindow_return_j =
    close[j] / close[j - 4] - 1
    if close[j - 4] > denominator_epsilon else missing

subwindow_flow_j =
    m2_net_signed_money_flow_trailing20 formula applied to subwindow_j
    with required_n = 5

divergence_flag_j =
    sign(subwindow_return_j) != sign(subwindow_flow_j)
```

Only subwindows with finite `subwindow_return_j` and finite `subwindow_flow_j`
enter the mean. If no valid subwindow remains, the feature is missing with
`blocking_reason = insufficient_valid_divergence_subwindows`.

M2 features must be described as daily signed-flow proxies, not true order flow,
unless a future requirement introduces PIT-valid true buy/sell direction fields.
The M2 primary gate inherited from 18D is the
`f2_extended_participation_money` residualization set; `base_vol_participation`
rows are diagnostic-only and must not authorize M2 primary inclusion.
Turnover-rate-only fields may support turnover compression but must not be
labeled as money-flow proxies.

## 10. Lineage, PIT, and Availability Gates

Every primary refresh feature must have a row in
`refreshed_feature_lineage_audit.csv` and
`refreshed_feature_pit_availability_audit.csv` with:

```text
pit_valid_status = pass
t0_available_status = pass
source_pos_max_minus_step_start_pos <= 0
source_date_max_minus_step_start_date <= 0
uses_future_h20_path = false
uses_step_end_outcome = false
uses_oracle_label = false
uses_payoff_target = false
uses_binary_target = false
candidate_primary_allowed_after_lineage = true
candidate_appendix_only = false
```

If any primary refresh feature fails lineage or t0 availability:

```text
decision_state = 18E_pit_t0_availability_blocked
next_allowed_requirement = none
```

## 11. Target Binding and Forbidden Columns

18E must preserve target columns inherited from the 18B matrix:

```text
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
label_class
```

These columns may appear in the refreshed matrix as target or metadata columns.
They must not be marked as primary raw features or model-ready features.
It is intentional that a retained target/metadata column such as `label_class`
also appears in the forbidden model-feature list; retention and model-feature eligibility are separate schema roles.

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
decision_state = 18E_forbidden_feature_blocked
next_allowed_requirement = none
```

## 12. Train-only Preprocessing Contract

18E must produce train-only preprocessing parameters for all 49 primary raw
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

Model-ready feature naming:

```text
existing F1-F5 model-ready names remain as in 18B, e.g. mr_ret_5d
refresh model-ready names = mr_<raw_refresh_feature_id>
```

Examples:

```text
mr_m5_episode_age_to_t0
mr_m5_bars_since_episode_high_t0
mr_m3_upside_room_to_episode_high
mr_m1_close_location_episode_range
mr_m2_money_flow_reversal_accel_5v20
mr_m2_money_flow_persistence_trailing20
```

## 13. Required Outputs

18E must write publishable outputs under:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/
```

Required local cache:

```text
outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
```

Required report:

```text
outputs/publishable/reports/payoff_state_feature_matrix_refresh_report.md
```

Required tables:

```text
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/input_artifact_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/upstream_18d_handoff_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refresh_candidate_replay_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_source_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_formula_registry.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_lineage_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_pit_availability_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_target_binding_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_missingness_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_family_coverage.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/matrix_row_completeness_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/train_only_preprocessing_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/split_drift_feature_readout.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/forbidden_feature_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/search_accounting_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_decision.csv
```

Optional appendix tables:

```text
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/appendix_excluded_candidate_feature_audit.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/appendix_feature_family_bucket_target_distribution.csv
```

If optional appendix tables are emitted, they must be marked:

```text
appendix_only = true
used_for_feature_selection = false
used_for_gate = false
used_for_downstream_separability = false
```

Required manifests:

```text
outputs/manifests/18E_payoff_state_feature_matrix_refresh_manifest.json
outputs/manifests/input_artifact_manifest_18e.json
outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
```

## 14. Minimum Table Schemas

### 14.1 `upstream_18d_handoff_audit.csv`

```text
source_artifact
field_name
observed_value
expected_value
status
blocking_reason
```

### 14.2 `refresh_candidate_replay_audit.csv`

```text
candidate_family_id
candidate_feature_id
expected_18e_role
expected_primary_model_feature
expected_appendix_only
expected_residualization_control_set_id
observed_18d_candidate_inventory_row_found
observed_18d_lineage_row_found
observed_18d_pit_row_found
observed_18d_train_prior_row_found
observed_18d_recommended_family
observed_candidate_primary_allowed_after_lineage
observed_pit_primary_allowed
observed_candidate_appendix_only
observed_recommendation_eligible_residualization
observed_dedup_group_representative
observed_orthogonal_payoff_candidate
observed_residualization_control_set_id
observed_blocking_reason
replay_status
blocking_reason
```

### 14.3 `refreshed_feature_formula_registry.csv`

```text
candidate_family_id
feature_id
feature_name
feature_role
formula_id
formula_text
source_artifact_alias
source_columns
window_id
minimum_observation_count
primary_model_feature
appendix_only
inherited_from_18d_candidate
lineage_before_target_evidence
blocking_reason
```

### 14.4 `refreshed_feature_matrix_schema.csv`

```text
column_name
column_role
feature_family_id
raw_feature_name
model_ready_feature_name
source_artifact_alias
dtype
nullable
primary_raw_feature
primary_model_feature
appendix_only
target_column
metadata_column
forbidden_as_model_feature
preprocessing_fit_split
preprocessing_param_id
blocking_reason
```

### 14.5 `refreshed_feature_family_coverage.csv`

```text
feature_family_id
family_role
expected_primary_feature_n
observed_primary_feature_n
finite_train_rate_min
finite_all_rate_min
family_coverage_status
blocking_reason
```

### 14.6 `train_only_preprocessing_audit.csv`

```text
feature_name
model_ready_feature_name
feature_family_id
raw_dtype
preprocessing_kind
fit_split
fit_row_n
imputer_value
center_value
scale_value
train_iqr
zero_iqr_flag
preprocessing_uses_target_columns
preprocessing_uses_robustness_rows
preprocessing_uses_validation_rows
split_local_imputation_used
split_local_scaling_used
status
blocking_reason
```

### 14.7 `refreshed_feature_matrix_decision.csv`

```text
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
upstream_18d_contract_gate
input_artifact_gate
feature_family_recommendation_replay_gate
refreshed_feature_source_gate
refreshed_feature_formula_gate
refreshed_feature_lineage_gate
pit_t0_availability_gate
target_binding_gate
feature_matrix_schema_gate
feature_complete_rate_gate
feature_family_coverage_gate
train_only_preprocessing_gate
forbidden_feature_gate
search_accounting_gate
blocking_reason
existing_primary_raw_feature_n
refresh_primary_raw_feature_n
refreshed_primary_raw_feature_n
refreshed_model_ready_feature_n
appendix_or_deferred_candidate_feature_n
qfq_path_coverage_rate
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

## 15. Required Gates and Decisions

All hard gates must pass for the positive 18E decision:

```text
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
```

Allowed positive decision:

```text
18E_payoff_state_feature_matrix_refresh_supported
```

Allowed blocked or diagnostic decisions:

```text
18E_upstream_18d_contract_blocked
18E_input_artifact_blocked
18E_refresh_candidate_replay_blocked
18E_refresh_source_lineage_blocked
18E_pit_t0_availability_blocked
18E_refreshed_feature_formula_blocked
18E_target_binding_blocked
18E_refreshed_feature_matrix_schema_blocked
18E_refreshed_feature_matrix_low_coverage
18E_train_only_preprocessing_blocked
18E_forbidden_feature_blocked
18E_search_accounting_blocked
18E_no_refresh_candidate_family_supported
18E_feature_matrix_refresh_contract_blocked
18E_feature_matrix_refresh_diagnostic_only
```

Decision mapping:

```text
upstream_18d_contract_gate fail -> 18E_upstream_18d_contract_blocked
input_artifact_gate fail -> 18E_input_artifact_blocked
feature_family_recommendation_replay_gate fail -> 18E_refresh_candidate_replay_blocked
refreshed_feature_source_gate fail -> 18E_refresh_source_lineage_blocked
refreshed_feature_formula_gate fail -> 18E_refreshed_feature_formula_blocked
refreshed_feature_lineage_gate fail -> 18E_refresh_source_lineage_blocked
pit_t0_availability_gate fail -> 18E_pit_t0_availability_blocked
target_binding_gate fail -> 18E_target_binding_blocked
feature_matrix_schema_gate fail -> 18E_refreshed_feature_matrix_schema_blocked
feature_complete_rate_gate fail -> 18E_refreshed_feature_matrix_low_coverage
feature_family_coverage_gate fail -> 18E_refreshed_feature_matrix_low_coverage
train_only_preprocessing_gate fail -> 18E_train_only_preprocessing_blocked
forbidden_feature_gate fail -> 18E_forbidden_feature_blocked
search_accounting_gate fail -> 18E_search_accounting_blocked
no recommended refresh family can be materialized -> 18E_no_refresh_candidate_family_supported
otherwise unclassified matrix-refresh failure -> 18E_feature_matrix_refresh_contract_blocked
```

Positive decision requirements:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
```

Blocked decision requirements:

```text
next_allowed_requirement = none
```

## 16. Search Accounting

18E must emit `search_accounting_audit.csv` proving:

```text
no_model_training = true
no_model_refit = true
no_scoring = true
no_rank_ic_computed_as_gate = true
no_auc_computed_as_gate = true
no_precision_recall_computed_as_gate = true
no_feature_selection_from_target_correlation = true
no_feature_selection_from_robustness = true
no_feature_selection_from_validation = true
no_threshold_tuning_on_robustness = true
no_threshold_tuning_on_validation = true
binary_metric_not_primary_gate = true
neutral_rows_not_dropped = true
delayed_features_not_primary = true
m4_not_primary = true
oracle_gap_bridge_not_started = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

## 17. Report Requirements

`payoff_state_feature_matrix_refresh_report.md` must include:

1. One-line decision and next allowed requirement.
2. 18D handoff replay, candidate replay audit, and recommended family summary.
3. Explicit statement that 18E is matrix construction only, not separability.
4. Row denominator and neutral preservation summary.
5. Source audit summary for 18B matrix, 16B/16A geometry, qfq path data, and
   18D handoff artifacts.
6. Formula registry summary for all 26 primary refresh features.
7. Appendix/deferred feature list and reasons for exclusion from the primary
   model-ready matrix.
8. PIT/t0 lineage and availability summary.
9. Feature missingness and finite-rate summary by split and family.
10. Train-only preprocessing summary.
11. Forbidden-feature and search-accounting summary.
12. Handoff instructions for a refreshed 18C-style separability rerun.

The report must state clearly:

```text
18E does not train a payoff separability model.
18E does not compute OOS payoff separability support.
18E does not authorize EP18F oracle-gap bridge.
18E does not authorize policy, backtest, deployment, production signal, or trading.
Only a future refreshed separability diagnostic can decide whether the new
matrix clears rank IC, monotonicity, baseline, bootstrap, and search-accounting
gates.
```

## 18. Manifest Requirements

`18E_payoff_state_feature_matrix_refresh_manifest.json` must include:

```text
run_id
phase_id
requirement_file_sha256
config_file_sha256
runner_file_sha256
input_artifact_manifest_sha256
refreshed_feature_matrix_sha256
publishable_table_sha256_by_name
report_sha256
decision_state
next_allowed_requirement
next_allowed_requirement_scope
all_hard_gates_pass
upstream_18d_decision_state
recommended_refresh_family_ids
deferred_family_ids
primary_refresh_feature_ids
appendix_only_candidate_feature_ids
existing_primary_raw_feature_n
refresh_primary_raw_feature_n
refreshed_primary_raw_feature_n
refreshed_model_ready_feature_n
appendix_or_deferred_candidate_feature_n
qfq_path_coverage_rate
neutral_rows_dropped
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

## 19. Handoff to Refreshed Separability Diagnostic

If and only if 18E emits:

```text
decision_state = 18E_payoff_state_feature_matrix_refresh_supported
next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md
next_allowed_requirement_scope = refreshed_matrix_rerun
```

then the next allowed work is a refreshed 18C-style separability diagnostic using:

```text
outputs/local_cache/18E_payoff_state_feature_matrix_refresh/refreshed_payoff_state_feature_matrix.parquet
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_schema.csv
outputs/publishable/tables/18E_payoff_state_feature_matrix_refresh/refreshed_feature_matrix_decision.csv
outputs/manifests/18E_payoff_state_feature_matrix_refresh_manifest.json
outputs/manifests/refreshed_payoff_state_feature_matrix_manifest.json
```

The refreshed separability diagnostic must not reuse stale 18C results from the
old 18B matrix. It must train and evaluate only on the 18E refreshed matrix
under a new or explicitly refreshed 18C config. EP18F oracle-gap work remains
blocked unless that future diagnostic emits:

```text
decision_state = 18C_payoff_state_separability_supported
```

## 20. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18e_payoff_state_feature_matrix_refresh.py
python experiments/pending/18_payoff_state_representation_research/src/run_18e_payoff_state_feature_matrix_refresh.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18e_payoff_state_feature_matrix_refresh.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18e_payoff_state_feature_matrix_refresh.py -q
```

Before publish:

```bash
git diff -- experiments/pending/18_payoff_state_representation_research/requirement_18e_payoff_state_feature_matrix_refresh.md
```
