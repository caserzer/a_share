# 需求：17A Oracle Replay Contract Preflight

## 0. Non-negotiable Scope

17A 是 EP17 的第一个可执行 phase。EP17 是 topic-level diagnostic restart，不是 EP16 的后续 continuation phase，也不是 16B2 payoff-aligned label redesign。

17A 只回答一个前置问题：

```text
在不训练模型、不调阈值、不解释 oracle value 的前提下，
能否把 EP16 失败现场的 decision-state denominator、action semantics、qfq replay、
cost assumptions、delay materialization、lineage identity 全部冻结成可复验的 oracle replay contract？
```

17A 的唯一正向裁决是：

```text
EP17A_oracle_replay_contract_ready
next_allowed_requirement = requirement_17b_oracle_ladder_replay.md
```

17A 不得输出：

```text
new model / refit
new feature set
new payoff label
survival score threshold tuning
oracle value interpretation
oracle ladder decision
entry policy
exit policy
holding policy
position sizing
portfolio backtest
production signal
deployment authorization
live trading authorization
```

17A 可以重新计算或重放 forward return / drawdown / cost fields，但仅限于 lineage and sanity replay：这些数值用于证明 EP16 16E utility panel、qfq path、16D action binding 可复验。17A 不得把任何 oracle result 解释为 "有价值" 或 "无价值"。

If any denominator, lineage, qfq replay, action contract, or search-accounting check fails, 17A must fail closed:

```text
decision_state = oracle_lineage_or_denominator_blocked
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 17_oracle_action_value_upper_bound_diagnostic
phase_id = 17A
run_id = 17A_oracle_replay_contract_preflight
requirement_file = requirement_17a_oracle_replay_contract_preflight.md
config_file = configs/config_17a_oracle_replay_contract_preflight.yaml
runner_file = src/run_17a_oracle_replay_contract_preflight.py
test_file = tests/test_17a_oracle_replay_contract_preflight.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All config paths must be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths. Input artifact identity must use content hash, schema, lineage role, and row-key reconciliation as primary identity. An older manifest absolute path such as `/home/...` is never sufficient reason to fail if the content hash, schema, relative role, and row keys reconcile.

## 2. Upstream Closure Replay

17A is authorized only as a diagnostic restart after EP16 closure. It must prove that no continuation policy, payoff-label redesign, or deployment authorization remains open.

Required topic-level closure state:

```text
deployable_strategy_found = false
production_signal_authorized = false
live_trading_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
continuation_as_action_mainline_closed = true
```

Required topic-level narrative readout, non-hard-gate:

```text
main_unsolved_problem = OOS payoff/utility ranking, not recall
```

`main_unsolved_problem` may be proven from `research_plan.md` or from `research_conclusions.md` prose. It is not required to exist as a machine-readable key in `research_conclusions.md`. If the exact key is absent from `research_conclusions.md` but the OOS payoff / utility-ranking problem is present in prose or research plan, set:

```text
main_unsolved_problem_readout_status = prose_or_research_plan_only
```

This narrative readout must not fail `upstream_closure_gate`.

Required 16E utility decision:

```text
decision_state = 16E_utility_diagnostic_not_supported
next_allowed_requirement = none
primary_label_id = continuation_survival_h20_no_deep_drawdown
primary_model_id = ridge_logistic_bar_state_v1
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
primary_round_trip_defense_cost_bps = 50
primary_return_utility_gate = fail
drawdown_avoidance_gate = pass
delay_stress_gate = fail
context_power_gate = pass
context_utility_gate = fail
six_cell_reconciliation_gate = pass
utility_interpretation = drawdown_reduction_only_return_not_supported
```

Required 16E-postmortem closure:

```text
decision_state = 16E_postmortem_mainline_closed_no_path_supported
next_allowed_requirement = none
selected_path_id = none
continuation_as_action_mainline_closed = true
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Required 16X payoff precheck closure:

```text
decision_state = 16X_payoff_precheck_not_supported
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
payoff_aligned_label_redo_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

If any required closure authorization input cannot be proven from publishable decision tables and manifests:

```text
upstream_closure_gate = fail
decision_state = oracle_lineage_or_denominator_blocked
next_allowed_requirement = none
```

## 3. Research Questions

17A answers seven contract questions.

```text
Q1. Can the EP16 labelable, binary, and neutral denominators be reconciled by split
    without confusing full-labelable utility denominator with binary policy denominator?

Q2. Can the 16D learned-score reference replay reproduce the frozen threshold,
    primary policy id, split counts, and binary confusion counts?

Q3. Can qfq close-to-close utility replay reproduce 16E primary 50bps robustness
    full-denominator mean incremental return and defended-negative drawdown sanity values?

Q4. Can every oracle in O0-O7 be bound to an explicit denominator type,
    information set, action family, cost grid, and neutral-handling rule before
    any oracle ladder value is computed?

Q5. Can delayed-decision semantics be materialized against the original t0-h20
    endpoint without restarting a fresh h20 horizon at t0+k?

Q6. Can capacity-constrained replay be marked primary only when calendar and
    exposure reconstruction are auditable, and appendix-only otherwise?

Q7. Can search accounting prove that no model training, threshold tuning,
    feature selection, validation selection, payoff-label redesign, or deployment
    claim has entered 17A?
```

If Q1-Q3 fail, it is lineage or denominator failure. If Q4-Q6 fail, it is replay-contract failure. If Q7 fails, it is search/leakage failure. All failures map to `oracle_lineage_or_denominator_blocked`.

## 4. Allowed And Forbidden Work

17A may:

1. Read EP16 publishable decision, audit, manifest, and local cache artifacts.
2. Validate optional local parquet caches before use.
3. Rebuild the 16D primary action panel or 16E utility panel under 17A local cache if upstream local caches are absent or stale.
4. Recompute qfq close-to-close h20 return, max drawdown, first-session return, and cost-stressed diagnostic utility strictly for sanity replay.
5. Freeze oracle denominator types, action definitions, cost grid, delay semantics, and neutral handling before 17B.
6. Emit denominator, action, replay, and search-accounting audits.
7. Write root-level contract docs `oracle_denominator_contract.md` and `oracle_action_contract.md`.

17A must not:

1. Train, refit, or recalibrate any model.
2. Change `threshold_value = 0.4570714890970447` or any 16D candidate policy.
3. Tune a survival score, payoff threshold, action intensity, cost tier, delay k, context filter, or oracle gate using robustness or validation outcomes.
4. Compute O1-O7 oracle ladder value beyond minimal schema and materialization dry-run checks.
5. Interpret any oracle upper bound as support or failure.
6. Define or evaluate an entry, exit, holding, sizing, or portfolio rule.
7. Treat oracle future information as deployable signal.
8. Rewrite EP16 publishable tables, manifests, reports, or local caches.

## 5. Required Inputs

All inputs must enter `input_artifact_manifest.json` and `input_artifact_audit.csv` with:

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
schema_status
read_status
absolute_path_mismatch_ignored
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 5.1 Topic and Closure Inputs

Required:

```text
research_conclusions.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/research_plan.md
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/sequential_continuation_utility_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/continuation_utility_failure_postmortem_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_aligned_label_power_precheck_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16E_sequential_continuation_utility_diagnostic_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16E_postmortem_continuation_utility_failure_decomposition_manifest.json
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16X_payoff_aligned_continuation_label_power_precheck_manifest.json
```

### 5.2 16B Denominator and qfq Lineage Inputs

Required publishable lineage:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/sequential_continuation_label_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/step_materialization_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/qfq_price_source_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16B_sequential_continuation_label_design_diagnostic_manifest.json
```

Optional cache, usable only after validation:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
```

### 5.3 16D Learned-score Reference Inputs

Required publishable inputs:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/sequential_continuation_policy_preflight_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_threshold_freeze_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_action_binding_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_confusion_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_context_stratified_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/known_failed_context_rebuild_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16D_sequential_continuation_policy_preflight/search_accounting_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16D_sequential_continuation_policy_preflight_manifest.json
```

Optional cache, usable only after validation:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16D_sequential_continuation_policy_preflight/policy_action_panel.parquet
```

If the cache is absent, 17A may rebuild the primary policy action panel using 16D config/runner helpers, but the rebuilt panel must be written only under:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/local_cache/17A_oracle_replay_contract_preflight/
```

### 5.4 16E Utility Replay Inputs

Required publishable inputs:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/sequential_continuation_utility_decision.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/single_step_action_semantics_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/utility_price_path_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/policy_utility_binding_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/six_cell_utility_reconciliation.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/utility_by_split_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/negative_avoidance_utility_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/search_accounting_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/manifests/16E_sequential_continuation_utility_diagnostic_manifest.json
```

Optional cache, usable only after validation:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16E_sequential_continuation_utility_diagnostic/utility_panel.parquet
```

If the utility cache is absent or stale, 17A may rebuild the utility sanity panel under the 17A local cache. It must not rewrite 16E outputs.

### 5.5 Price Path Inputs

Required qfq source:

```text
stock_daily_qfq_dir = data/raw/akshare/day/qfq
```

For every denominator row used by O0/O2/O5/O6/O7 full-labelable replay, qfq lineage must prove:

```text
instrument exists
step_start_pos and step_end_pos are in bounds
step_start_date and step_end_date match qfq dates at those positions
step_start_qfq_close and step_end_qfq_close match qfq close within tolerance
all close values from step_start_pos through step_end_pos are finite and positive
step_start_pos + 1 exists for first-session delay sanity
t0+k positions for k in {3, 5, 10} exist within the original h20 interval
```

## 6. Denominator Contract

17A must emit `oracle_denominator_contract.md` and `denominator_lineage_audit.csv`. The primary denominator is:

```text
EP16 up50pct / h20 / full-horizon / non-overlap continuation decision states
```

Required split reconciliation:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n
train        | 20245            | 14962         | 5283
robustness   | 2496             | 1872          | 624
validation   | 664              | 505           | 159
```

Definitions:

```text
labelable_step_n = positive + negative + neutral
binary_step_n = positive + negative
neutral_step_n = neutral
primary_split_for_confirmatory_gates = robustness
train_usage = lineage, calibration, threshold-freeze, and explanatory readout only
validation_usage = stress readout only
```

Primary row key:

```text
step_id
label_id
threshold_id
instrument
episode_cluster_id
horizon_sessions
step_index
step_start_date
step_end_date
cluster_split_bucket
```

The implementation must reject duplicate primary row keys within each source panel. If any row lacks `episode_cluster_id`, `instrument`, split, step start/end dates, or label class, the denominator contract fails.

### 6.1 Oracle Denominator Binding

17A must freeze this table before 17B:

```text
oracle_id | oracle_name                              | primary_denominator_type
O0        | No Oracle Baseline                       | labelable_full
O1        | Perfect Negative Oracle                  | binary_primary
O2        | Perfect Deep Drawdown Oracle             | labelable_full
O3        | Perfect False-repair Oracle              | appendix_only_if_join_incomplete
O4        | Positive Preservation Oracle             | binary_primary
O5        | Perfect Utility Oracle                   | labelable_full
O6        | Capacity-constrained Utility Oracle      | labelable_full_if_capacity_gate_passes
O7        | Delayed Utility Oracle                   | labelable_full
L0        | 16D Learned-score Reference              | binary_fit_labelable_replay
```

Rules:

```text
O0/O2/O5/O6/O7 full-labelable replay must match labelable_step_n.
O1/O4 primary binary readout and L0 binary confusion must match binary_step_n.
O1/O4 must also emit labelable_neutral_stress, but neutral stress is not the primary binary gate.
O3 cannot block O1/O2/O4/O5 if skipped for incomplete false-repair lineage.
Any neutral count mismatch fails before full-denominator utility can be interpreted.
```

## 7. Action and Cost Contract

17A must emit `oracle_action_contract.md` and `action_semantics_audit.csv`.

Baseline:

```text
baseline_action = blind_continue_h20
baseline_exposure = 1.0 from step_start_qfq_close to step_end_qfq_close
cash_return = 0.0
holding_cost = 0.0 unless explicitly configured
```

Allowed action families:

```text
full_defend_exit_cash
partial_defend_50pct
partial_defend_25pct
blind_continue
delayed_decision_k
learned_score_reference
```

Primary cost grid:

```text
round_trip_defense_cost_bps in {0, 25, 50, 100}
primary_round_trip_defense_cost_bps = 50
cost_selected_by_oos_result = false
```

Per-row formulas:

```text
blind_continue_pnl = forward_return_h20
continue_pnl = q_continue * forward_return_remaining - holding_cost
defend_pnl = q_defend * forward_return_remaining - transaction_cost
incremental_pnl = oracle_policy_pnl - blind_continue_pnl
```

Exposure settings:

```text
q_continue = 1.0
q_full_defend = 0.0
q_partial_defend_50pct = 0.50
q_partial_defend_25pct = 0.25
```

### 7.1 Delayed Decision Semantics

Delayed semantics must be frozen before 17B:

```text
delayed_k_sessions in {3, 5, 10}
delayed_decision_time = t0 + k close
t0 -> t0+k: blind continue exposure = 1.0
t0+k -> original h20 end: oracle chooses continue or defend
incremental utility is compared to original t0 blind continue over the full h20 block
```

Forbidden delayed semantics:

```text
restart_h20_at_t0_plus_k = false
partial_tail_fill = false
new endpoint selected after seeing outcome = false
```

If any t0+k price or remaining original h20 interval cannot be materialized, O7 must fail closed for 17B readiness:

```text
delayed_materialization_gate = fail
decision_state = oracle_lineage_or_denominator_blocked
```

### 7.2 Capacity Contract

O6 may be primary in later phases only if 17A proves:

```text
calendar_day can be reconstructed
active exposure count can be reconstructed
same-day concurrent candidate count can be reconstructed
capacity cap is config-frozen before oracle replay
turnover/cost assumptions are config-frozen before oracle replay
```

If this cannot be proven:

```text
capacity_reconstruction_gate = appendix_only
O6_status_for_17B = appendix_only_nonblocking
```

O6 appendix-only status must not block O0-O5 replay readiness.

## 8. Replay Sanity Checks

17A must emit `ep16_replay_sanity_check.csv` and `replay_price_path_audit.csv`.

### 8.1 Learned-score Reference

Required 16D reference values:

```text
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_model_id = ridge_logistic_bar_state_v1
threshold_value = 0.4570714890970447
threshold_abs_tolerance <= 1e-12
```

Required split counts:

```text
train_binary_step_n = 14962
train_positive_n = 10078
train_negative_n = 4884
train_defended_binary_step_n = 4489
train_defended_negative_n = 2299
train_defense_negative_capture_rate = 0.47072072072072074
train_positive_sacrifice_rate = 0.21730502083746775
train_continue_negative_leakage_rate = 0.5292792792792793

robustness_binary_step_n = 1872
robustness_positive_n = 1346
robustness_negative_n = 526
robustness_defended_binary_step_n = 397
robustness_defended_negative_n = 196
robustness_defense_negative_capture_rate = 0.3726235741444867
robustness_defense_precision_lift_vs_binary_negative_base = 0.21271986479795046
robustness_positive_sacrifice_rate = 0.14933135215453194
robustness_continue_negative_leakage_rate = 0.6273764258555133

validation_binary_step_n = 505
validation_positive_n = 325
validation_negative_n = 180
validation_defended_binary_step_n = 158
validation_defended_negative_n = 81
validation_defense_negative_capture_rate = 0.45
validation_defense_precision_lift_vs_binary_negative_base = 0.1562225842837448
validation_positive_sacrifice_rate = 0.23692307692307693
validation_continue_negative_leakage_rate = 0.55
```

Validation is a stress replay only. These values must be reconciled for lineage completeness, but validation must not be used for threshold, action, cost, oracle, or gate selection.

### 8.2 Utility and Drawdown Replay

Required 16E sanity values:

```text
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
primary_round_trip_defense_cost_bps = 50

train_labelable_step_n = 20245
train_defended_labelable_step_n = 5584
train_defended_positive_n = 2190
train_defended_negative_n = 2299
train_defended_neutral_n = 1095

robustness_labelable_step_n = 2496
robustness_defended_labelable_step_n = 486
robustness_defended_positive_n = 201
robustness_defended_negative_n = 196
robustness_defended_neutral_n = 89

validation_labelable_step_n = 664
validation_defended_labelable_step_n = 183
validation_defended_positive_n = 77
validation_defended_negative_n = 81
validation_defended_neutral_n = 25
```

Primary 50bps replay targets:

```text
robustness_full_denominator_mean_incremental_return_50bps = -0.005529136777913869
robustness_defended_negative_drawdown_avoided_abs_mean = 0.164024392171124
utility_mean_abs_tolerance <= 1e-9
drawdown_abs_tolerance <= 1e-9
```

The drawdown target applies to the 16D primary defended-negative set. O2 in later phases may defend a different row set, so O2's defended-negative mean need not equal `0.164024392171124`; however, O2 must use the same qfq max-drawdown field proven here.

### 8.3 Six-cell Sanity

17A must prove that six cells exist for each split and primary cost tier:

```text
defended_positive
defended_negative
defended_neutral
continued_positive
continued_negative
continued_neutral
```

For each `(split_bucket, cost_bps = 50)`:

```text
sum(incremental_return_sum over six cells)
  == utility_by_split_readout.full_denominator_sum_incremental_return
```

within `1e-9`.

## 9. Search Accounting

17A must emit `search_accounting_audit.csv` with:

```text
search_family = oracle_action_value_upper_bound_diagnostic
phase_id = 17A
no_model_training = true
no_model_refit = true
no_survival_threshold_tuning = true
no_validation_selection = true
no_robustness_tuning = true
no_feature_selection = true
no_payoff_label_redesign = true
no_oracle_value_interpretation = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
search_accounting_gate
blocking_reason
```

Any false value in the no-search/no-authorization fields fails closed.

## 10. Outputs

All publishable tables must be written under:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_closure_audit.csv
denominator_lineage_audit.csv
oracle_denominator_binding.csv
action_semantics_audit.csv
delayed_materialization_audit.csv
capacity_reconstruction_audit.csv
replay_price_path_audit.csv
learned_score_reference_replay_audit.csv
ep16_replay_sanity_check.csv
six_cell_sanity_reconciliation.csv
search_accounting_audit.csv
oracle_replay_contract_decision.csv
```

Required root-level docs:

```text
oracle_denominator_contract.md
oracle_action_contract.md
```

Local cache outputs:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/local_cache/17A_oracle_replay_contract_preflight/replay_contract_panel.parquet
```

Report:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/reports/oracle_replay_contract_preflight_report.md
```

Required manifest outputs:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17A_oracle_replay_contract_preflight_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_replay_engine_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/input_artifact_manifest.json
```

## 11. Required Table Schemas

### 11.1 `upstream_closure_audit.csv`

Minimum columns:

```text
source_document
source_phase_id
deployable_strategy_found
decision_state
next_allowed_requirement
continuation_as_action_mainline_closed
main_unsolved_problem_readout
main_unsolved_problem_readout_status
payoff_aligned_label_redo_authorized
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
chained_simulation_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
required_state_status
blocking_reason
```

### 11.2 `denominator_lineage_audit.csv`

Minimum columns:

```text
split_bucket
expected_labelable_step_n
observed_labelable_step_n
expected_binary_step_n
observed_binary_step_n
expected_neutral_step_n
observed_neutral_step_n
positive_n
negative_n
neutral_n
duplicate_primary_row_key_n
missing_primary_row_key_field_n
missing_episode_cluster_id_n
missing_instrument_n
source_16b_status
source_16d_status
source_16e_status
denominator_reconciliation_gate
blocking_reason
```

### 11.3 `oracle_denominator_binding.csv`

Minimum columns:

```text
oracle_id
oracle_name
primary_denominator_type
expected_primary_row_count_train
expected_primary_row_count_robustness
expected_primary_row_count_validation
neutral_stress_required
appendix_only_allowed
skip_is_blocking
binding_status
blocking_reason
```

### 11.4 `action_semantics_audit.csv`

Minimum columns:

```text
action_family_id
baseline_action
q_continue
q_defend
round_trip_defense_cost_bps_grid
primary_round_trip_defense_cost_bps
cost_selected_by_oos_result
cash_return
holding_cost
validation_used_for_action_selection
robustness_used_for_action_selection
return_metric_used_for_action_selection
action_semantics_gate
blocking_reason
```

### 11.5 `delayed_materialization_audit.csv`

Minimum columns:

```text
split_bucket
labelable_step_n
delay_k_sessions
materialized_step_n
missing_t0_plus_k_price_n
missing_original_h20_endpoint_n
restart_h20_at_t0_plus_k
partial_tail_fill_used
delayed_materialization_gate
blocking_reason
```

### 11.6 `capacity_reconstruction_audit.csv`

Minimum columns:

```text
calendar_reconstruction_status
active_exposure_reconstruction_status
same_day_concurrent_candidate_status
capacity_cap_config_frozen
turnover_cost_config_frozen
o6_primary_allowed
o6_status_for_17b
capacity_reconstruction_gate
blocking_reason
```

### 11.7 `replay_price_path_audit.csv`

Minimum columns:

```text
split_bucket
labelable_step_n
price_path_valid_step_n
missing_qfq_instrument_n
bad_step_bounds_n
nonfinite_close_n
nonpositive_close_n
step_start_close_mismatch_n
step_end_close_mismatch_n
first_session_missing_n
delay_k_missing_n
max_drawdown_replay_abs_diff_max
price_path_replay_gate
blocking_reason
```

### 11.8 `learned_score_reference_replay_audit.csv`

Minimum columns:

```text
primary_policy_id
primary_model_id
threshold_value_expected
threshold_value_observed
threshold_value_abs_diff
split_bucket
expected_binary_step_n
observed_binary_step_n
expected_positive_n
observed_positive_n
expected_negative_n
observed_negative_n
expected_defended_binary_step_n
observed_defended_binary_step_n
expected_defended_negative_n
observed_defended_negative_n
defense_negative_capture_rate_abs_diff
positive_sacrifice_rate_abs_diff
continue_negative_leakage_rate_abs_diff
learned_score_reference_gate
blocking_reason
```

### 11.9 `ep16_replay_sanity_check.csv`

Minimum columns:

```text
sanity_check_id
split_bucket
cost_bps
expected_value
observed_value
abs_diff
tolerance
source_table
sanity_status
blocking_reason
```

Required `sanity_check_id` values:

```text
16d_threshold_value
16d_binary_confusion_counts
16e_labelable_denominator_counts
16e_primary_50bps_robustness_mean_incremental_return
16e_primary_robustness_defended_negative_drawdown_avoided_mean
16e_six_cell_incremental_sum_identity
```

### 11.10 `oracle_replay_contract_decision.csv`

Minimum columns:

```text
decision_state
next_allowed_requirement
upstream_closure_gate
input_artifact_gate
denominator_reconciliation_gate
oracle_denominator_binding_gate
action_semantics_gate
delayed_materialization_gate
capacity_reconstruction_gate
price_path_replay_gate
learned_score_reference_gate
ep16_utility_replay_gate
six_cell_sanity_gate
search_accounting_gate
o6_status_for_17b
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
chained_simulation_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

## 12. Decision Map

Final decision enum:

```text
EP17A_oracle_replay_contract_ready
oracle_lineage_or_denominator_blocked
```

Decision logic:

```text
if any required upstream closure authorization value cannot be proven:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif any required input artifact is missing or schema-failing:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif denominator_reconciliation_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif oracle_denominator_binding_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif action_semantics_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif delayed_materialization_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif price_path_replay_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif learned_score_reference_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif ep16_utility_replay_gate fails or six_cell_sanity_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

elif search_accounting_gate fails:
  decision_state = oracle_lineage_or_denominator_blocked
  next_allowed_requirement = none

else:
  decision_state = EP17A_oracle_replay_contract_ready
  next_allowed_requirement = requirement_17b_oracle_ladder_replay.md
```

Capacity reconstruction failure alone does not block readiness if it is safely downgraded:

```text
capacity_reconstruction_gate = appendix_only
o6_status_for_17b = appendix_only_nonblocking
```

Regardless of decision:

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

## 13. Report Requirements

The Chinese report must include:

1. 单行 decision and next allowed requirement.
2. Why EP17 is a topic-level diagnostic restart, not a continuation-policy continuation.
3. Upstream 16E / postmortem / 16X closure replay.
4. Denominator reconciliation with labelable, binary, and neutral counts by split.
5. Oracle denominator binding table for O0-O7 and L0.
6. Learned-score reference replay with threshold and 16D confusion counts.
7. qfq replay sanity and exact 16E 50bps robustness utility/drawdown checks.
8. Six-cell sanity identity.
9. Delayed decision semantics and no-restart-h20 rule.
10. Capacity reconstruction status and whether O6 is primary or appendix-only for 17B.
11. Search accounting: no model/refit/threshold/validation/robustness/payoff-label search.
12. Explicit statement that 17A does not interpret oracle value and does not authorize entry, exit, holding, sizing, portfolio, deployment, or live trading.

## 14. Manifest Requirements

`17A_oracle_replay_contract_preflight_manifest.json` must include:

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
research_plan_path
research_plan_sha256
decision_state
next_allowed_requirement
upstream_closure_states
primary_denominator_counts
primary_policy_id
primary_model_id
threshold_value
primary_action_semantics_id
primary_round_trip_defense_cost_bps
oracle_denominator_binding_hash
oracle_action_contract_hash
input_artifact_hashes
output_hashes
row_counts
authorization_booleans
large_artifact_policy
```

`oracle_replay_engine_manifest.json` must include:

```text
replay_engine_id
replay_engine_version
denominator_contract_path
denominator_contract_sha256
action_contract_path
action_contract_sha256
primary_denominator_counts
oracle_denominator_binding_hash
primary_action_semantics_id
primary_round_trip_defense_cost_bps
cost_grid_bps
delayed_action_semantics
delayed_k_sessions
capacity_reconstruction_gate
o6_status_for_17b
qfq_price_source
qfq_price_source_hash_or_snapshot_id
price_path_replay_gate
learned_score_reference_gate
ep16_utility_replay_gate
six_cell_sanity_gate
search_accounting_gate
```

`input_artifact_manifest.json` must include one entry per input artifact with:

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
schema_status
read_status
absolute_path_mismatch_ignored
blocking_reason
```

## 15. Implementation Pattern

Implementation should remain experiment-local under:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/
```

It may reuse 16B / 16D / 16E helpers through importlib. No shared-package refactor is required.

Local caches are optional accelerators only. Before use, the runner must validate:

```text
schema
row count
primary row-key uniqueness
split counts
label counts
threshold id
horizon_sessions = 20
policy_id where applicable
source artifact hash if available
```

If a rebuild path would mutate EP16 outputs, 17A must fail closed instead of rebuilding.

Large row-level replay panels must remain local parquet. Publishable row-level samples are not required for 17A.

## 16. Test Plan

Implement focused tests covering:

```text
test_17a_requires_ep16_closure_and_no_authorizations
test_17a_rejects_open_16e_next_allowed_requirement
test_denominator_reconciles_labelable_binary_neutral_counts
test_binary_denominator_not_confused_with_labelable_denominator
test_neutral_count_mismatch_fails_before_utility_interpretation
test_oracle_denominator_binding_o1_o4_binary_primary_with_neutral_stress
test_oracle_denominator_binding_o0_o2_o5_o7_labelable_full
test_o3_incomplete_lineage_is_appendix_only_nonblocking
test_16d_threshold_replays_exact_value
test_16d_primary_policy_confusion_replays_train_and_robustness
test_policy_action_cache_optional_and_validated_before_use
test_policy_action_sample_cannot_be_full_row_source
test_qfq_replay_validates_step_start_and_step_end_close
test_qfq_replay_recomputes_h20_return_and_max_drawdown
test_16e_robustness_50bps_mean_incremental_return_replays
test_16e_robustness_defended_negative_drawdown_mean_replays
test_16d_primary_policy_validation_stress_replays_without_selection
test_six_cell_incremental_sum_identity_replays
test_action_contract_freezes_cost_grid_before_replay
test_action_contract_rejects_oos_selected_cost_or_action
test_delayed_semantics_use_original_h20_endpoint
test_delayed_semantics_reject_restart_h20_at_t0_plus_k
test_missing_delay_price_fails_delayed_materialization_gate
test_capacity_reconstruction_can_downgrade_o6_to_appendix_only
test_capacity_reconstruction_failure_does_not_block_o0_to_o5
test_search_accounting_rejects_model_refit_or_threshold_tuning
test_search_accounting_rejects_oracle_value_interpretation_in_17a
test_decision_ready_only_when_all_hard_gates_pass
test_decision_blocked_on_any_lineage_denominator_or_replay_failure
test_all_trading_deployment_authorizations_false
test_manifests_include_run_replay_engine_and_input_artifact_hashes
```

## 17. Validation Commands

From `topics/02_AFML_BIG_WINNER`:

```bash
python -m py_compile experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17a_oracle_replay_contract_preflight.py
python -m pytest experiments/pending/17_oracle_action_value_upper_bound_diagnostic/tests/test_17a_oracle_replay_contract_preflight.py -q
python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17a_oracle_replay_contract_preflight.py --mode check-inputs
python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17a_oracle_replay_contract_preflight.py --mode full
git diff --check
```

## 18. Caveats To Carry Forward

17A must carry these inherited caveats into the report and manifest:

```text
16B soft_overlap_partial_coverage_caveat = true
16B known_failed_context_exposure_caveat = true
16C neutral_population_caveat = true
16D soft_overlap_partial_coverage_caveat = true
16D known_failed_context_exposure_caveat = true
16E utility_interpretation = drawdown_reduction_only_return_not_supported
16E_postmortem selected_path_id = none
16X payoff_aligned_label_redo_authorized = false
EP17 oracle outputs use future information and are not deployable signals
```
