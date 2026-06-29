# 需求：16E Sequential Continuation Utility Diagnostic

## 0. Non-negotiable Scope

16E 是 Episode 16 第五个 phase。它只在 16D 裁决为：

```text
16D_policy_preflight_ready_for_utility_diagnostic
next_allowed_requirement = requirement_16e_sequential_continuation_utility_diagnostic.md
```

时允许运行。

16E 的任务是把 16D 已冻结的 `defend_next_h20` / `continue_next_h20` label-action rule 放到**单步 h20 utility** 口径下诊断。它只回答：

```text
在 16B materialized h20 step universe 中，
16D primary bottom-30% defend action 是否在单个 h20 block 的 return / drawdown / cost / delay diagnostic 中
足以抵消 positive sacrifice、continued negative leakage、neutral uncertainty 和 known-failed context caveat？
```

16E 首次允许计算 utility / return / drawdown / cost / execution-delay diagnostic，但仍然不是：

```text
entry policy
exit policy
holding policy
chained sequential simulation
portfolio construction
position sizing
production signal
deployment authorization
```

16E 中的 `defend_next_h20` 仍是 counterfactual diagnostic action。它可以被赋予**单步诊断语义**以计算 utility，但不得被解释为真实卖出、减仓、避险、止损、择时或交易建议。

若 16E 通过，最多只能授权后续新建：

```text
requirement_16f_chained_action_transition_freeze.md
```

16F 仍需重新冻结 chained transition contract。16E 不得直接授权 16G chained simulation、完整 entry / exit / holding strategy、portfolio backtest 或 deployment。

## 1. Identity

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16E
run_id = 16E_sequential_continuation_utility_diagnostic
requirement_file = requirement_16e_sequential_continuation_utility_diagnostic.md
config_file = configs/config_16e_sequential_continuation_utility_diagnostic.yaml
runner_file = src/run_16e_sequential_continuation_utility_diagnostic.py
test_file = tests/test_16e_sequential_continuation_utility_diagnostic.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths in config should be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths.

## 2. Upstream Authorization Replay

16E 必须复验 16D 的 ready 裁决，不得只读报告文本。

Required 16D values:

```text
decision_state = 16D_policy_preflight_ready_for_utility_diagnostic
next_allowed_requirement = requirement_16e_sequential_continuation_utility_diagnostic.md
primary_label_id = continuation_survival_h20_no_deep_drawdown
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_model_id = ridge_logistic_bar_state_v1
primary_policy_id = defense_bottom_30pct_continuation_score_v1
train_binary_step_n = 14962
train_positive_n = 10078
train_negative_n = 4884
train_defended_binary_step_n = 4489
train_defended_negative_n = 2299
train_defense_negative_capture_rate = 0.470721
train_positive_sacrifice_rate = 0.217305
train_continue_negative_leakage_rate = 0.529279
robustness_binary_step_n = 1872
robustness_positive_n = 1346
robustness_negative_n = 526
robustness_defended_binary_step_n = 397
robustness_defended_negative_n = 196
robustness_defense_negative_capture_rate = 0.372624
robustness_defense_precision_lift_vs_binary_negative_base = 0.212720
robustness_positive_sacrifice_rate = 0.149331
robustness_continue_negative_leakage_rate = 0.627376
non_known_failed_robustness_binary_step_n = 907
non_known_failed_robustness_negative_n = 224
non_known_failed_robustness_defended_negative_n = 83
non_known_failed_robustness_defense_precision_lift = 0.253032
soft_overlap_partial_coverage_caveat = true
known_failed_context_exposure_caveat = true
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
return_backtest_authorized = false
cost_model_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
```

Required 16D hard gates:

```text
input_artifact_gate = pass
upstream_16c_authorization_gate = pass
upstream_16b_label_rebuild_gate = pass
score_rebuild_lineage_gate = pass
feature_contract_replay_gate = pass
score_orientation_gate = pass
threshold_freeze_gate = pass
neutral_handling_gate = pass
policy_action_binding_gate = pass
known_failed_context_rebuild_gate = pass
search_accounting_gate = pass
power_gate = pass
primary_policy_usefulness_gate = pass
context_independence_gate = pass
```

If any required value cannot be proven from publishable 16D tables and manifest, 16E must fail closed:

```text
upstream_16d_authorization_gate = fail
decision_state = 16E_utility_diagnostic_blocked_by_input_or_lineage_failure
next_allowed_requirement = none
```

## 3. Research Questions

16E answers six questions.

```text
Q1. Can the full 16D primary policy action panel be deterministically rebuilt or validated
    without relying on the publishable action sample as row-level truth?

Q2. Can single-step diagnostic action semantics be frozen before any return, cost,
    or execution-delay readout is computed?

Q3. Does the primary defend action produce positive full-denominator h20 net utility
    after positive sacrifice, neutral rows, and primary round-trip cost are included?

Q4. Does defended-negative drawdown/loss avoidance offset defended-positive upside sacrifice,
    and how much negative loss remains in continued negative leakage?

Q5. Does utility support remain present in robustness and outside known-failed context,
    while validation remains stress readout only?

Q6. Was any action semantics, cost tier, threshold, context filter, or utility metric
    selected using validation / robustness / return outcomes?
```

If Q1 fails, it is lineage failure. If Q2 fails, it is action-semantics failure. If Q3/Q4 fail, utility is not supported. If Q5 lacks enough non-known-failed context power, 16E is low-power; if powered non-known-failed utility fails while known-failed utility passes, 16E is context-concentrated only. If Q6 fails, it is search/leakage failure.

## 4. Allowed And Forbidden Work

16E may:

1. Rebuild or validate the full 16D primary policy action panel.
2. Freeze a single-step diagnostic action semantics before computing utility.
3. Rebuild close-to-close h20 return and h20 max drawdown from qfq daily prices.
4. Compute gross and cost-stressed single-step utility for `defend_next_h20` vs blind `continue_next_h20`.
5. Compute one-session delayed defense execution stress.
6. Report positive sacrifice, avoided negative loss/drawdown, continued negative leakage, and neutral utility.
7. Report all / late-rescue / non-late-rescue / known-failed / non-known-failed context utility.
8. Define a next-phase question for chained transition freeze if all gates pass.

16E must not:

1. Treat `defend_next_h20` as a real exit, sell, hedge, stop, or position-size instruction.
2. Chain multiple h20 decisions into a strategy simulation.
3. Define or evaluate a new entry rule.
4. Change 16D primary policy id, score threshold, score model, horizon, label id, or threshold id.
5. Optimize action semantics using train, validation, robustness, return, cost, or context outcomes.
6. Select cost tier, delay rule, context filter, or utility scalar after seeing OOS results.
7. Drop neutral rows from full-denominator utility.
8. Map neutral rows to positive or negative.
9. Use validation or robustness for model, threshold, policy, action semantics, cost, or utility-metric selection.
10. Claim live, simulated, or deployable trading performance.

## 5. Required Inputs

All required inputs must enter `input_artifact_audit.csv` with:

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
```

Missing or schema-failing required inputs fail closed.

### 5.1 16D Publishable Inputs

16E must read the following publishable 16D artifacts:

```text
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/sequential_continuation_policy_preflight_decision.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/upstream_16c_authorization_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/score_rebuild_lineage_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/feature_contract_replay_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_candidate_registry.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_threshold_freeze_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_action_binding_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_confusion_readout.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_tradeoff_frontier_readout.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/known_failed_context_rebuild_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_context_stratified_readout.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/neutral_policy_handling_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_stability_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/search_accounting_audit.csv
outputs/manifests/16D_sequential_continuation_policy_preflight_manifest.json
```

`policy_action_sample.csv.gz` is publishable sample only. It must never be used as the full row-level source for utility.

### 5.2 Full Row-level Policy Action Panel

16E requires full row-level action data for the primary policy:

```text
outputs/local_cache/16D_sequential_continuation_policy_preflight/policy_action_panel.parquet
```

This local parquet is an optional acceleration cache. If missing, 16E must rebuild the action panel by importing/replaying the 16D runner and config:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/configs/config_16d_sequential_continuation_policy_preflight.yaml
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16d_sequential_continuation_policy_preflight.py
```

The rebuild path must be side-effect isolated:

```text
16E may import 16D helper functions and rebuild the panel in memory.
16E may write the rebuilt primary action panel only under
  outputs/local_cache/16E_sequential_continuation_utility_diagnostic/
16E must not invoke 16D full mode in a way that rewrites 16D publishable tables,
  reports, local caches, or manifests.
If the only available replay path would mutate 16D artifacts, 16E must fail closed.
```

If cache exists, it may be used only after proving:

```text
row keys are unique
policy_id includes defense_bottom_30pct_continuation_score_v1
primary policy row count equals 23405
binary step count equals 17339
neutral step count equals 6066
split label counts replay 16D decision and confusion readouts
threshold_value for primary policy equals 0.457071 within tolerance
candidate_action is never missing
known_failed context flags are present and replay aggregate 16D context readouts
```

If validation fails, implementation must discard/rebuild or fail closed. It must not compute utility from a stale or partial action panel.

### 5.3 Price Path Inputs

16E utility must be recomputed from qfq price paths, not inferred from aggregate tables.

Required raw price source:

```text
stock_daily_qfq_dir = data/raw/akshare/day/qfq
```

For every primary policy row, qfq data must prove:

```text
instrument exists
step_start_pos and step_end_pos are in bounds
step_start_date and step_end_date match qfq dates at those positions
step_start_qfq_close and step_end_qfq_close match qfq close within tolerance
all close values in step_start_pos ... step_end_pos are finite and positive
one-session delay row step_start_pos + 1 exists for h20 rows
```

If qfq path validation fails:

```text
utility_price_path_gate = fail
decision_state = 16E_utility_diagnostic_blocked_by_input_or_lineage_failure
```

### 5.4 16B / 16C Lineage Inputs

16E must inherit the 16B label and 16C score/feature caveats via 16D, and may read upstream artifacts when needed for independent checks:

```text
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/sequential_continuation_label_decision.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/qfq_price_source_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/sequential_continuation_separability_decision.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/oos_separability_readout.csv
```

These are lineage checks. 16E must not refit the 16C model or change 16D policy thresholds.

## 6. Single-step Diagnostic Action Semantics

16E must freeze single-step semantics before utility computation.

Primary semantics:

```text
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
decision_time = step_start_date close
baseline_action = blind_continue_next_h20
baseline_exposure = 1.0 from step_start_qfq_close to step_end_qfq_close
continue_next_h20 exposure = 1.0 from step_start_qfq_close to step_end_qfq_close
defend_next_h20 exposure = 0.0 from step_start_qfq_close to step_end_qfq_close
defend_cash_return_h20 = 0.0
continue_trade_cost = 0.0
defend_trade_cost = round_trip_defense_cost_bps / 10000
```

Cost grid:

```text
round_trip_defense_cost_bps in {0, 25, 50, 100}
primary_round_trip_defense_cost_bps = 50
```

Interpretation:

```text
50 bps is a diagnostic round-trip defense cost buffer for leaving and restoring h20 exposure.
It is not a calibrated live transaction-cost model.
```

One-session delay stress:

```text
delay_stress_id = one_session_delay_close_to_close_v1
delayed_defend_exposure = 1.0 from step_start_qfq_close to qfq_close[step_start_pos + 1]
delayed_defend_exposure = 0.0 from qfq_close[step_start_pos + 1] to step_end_qfq_close
delayed_defend_cash_return_after_delay = 0.0
delayed_defend_trade_cost = round_trip_defense_cost_bps / 10000
```

Alternative semantics may be reported only as appendix if pre-registered in config before any utility computation:

```text
partial_de_risk_50pct_h20_close_to_close_v1
no_additional_continuation_sleeve_h20_v1
cash_or_benchmark_substitution_h20_v1
```

Alternative semantics cannot change the primary decision, and cannot be promoted to primary based on train, robustness, validation, context, or cost results.

Action semantics audit must prove:

```text
primary_action_semantics_id is config-frozen
primary_round_trip_defense_cost_bps is config-frozen
delay_stress_id is config-frozen
validation_used_for_action_semantics_selection = false
robustness_used_for_action_semantics_selection = false
return_metric_used_for_action_semantics_selection = false
cost_metric_used_for_action_semantics_selection = false
```

If this cannot be proven:

```text
action_semantics_gate = fail
decision_state = 16E_utility_diagnostic_blocked_by_action_semantics_failure
next_allowed_requirement = none
```

## 7. Utility Formulae

All utility metrics are single-step h20 diagnostics.

For each row:

```text
continue_return_h20 =
  step_end_qfq_close / step_start_qfq_close - 1

continue_max_drawdown_h20 =
  min(close[t] / step_start_qfq_close - 1 for t in step_start_pos ... step_end_pos)

continue_max_drawdown_h20 must replay max_drawdown_from_step_start within tolerance.
```

Under primary semantics:

```text
if candidate_action == continue_next_h20:
  policy_gross_return_h20 = continue_return_h20
  policy_max_drawdown_h20 = continue_max_drawdown_h20
  policy_net_return_h20_{cost_bps} = continue_return_h20
  incremental_net_return_h20_{cost_bps} = 0.0
  drawdown_avoided_abs = 0.0

if candidate_action == defend_next_h20:
  policy_gross_return_h20 = 0.0
  policy_max_drawdown_h20 = 0.0
  policy_net_return_h20_{cost_bps} = -cost_bps / 10000
  incremental_net_return_h20_{cost_bps} =
    policy_net_return_h20_{cost_bps} - continue_return_h20
  drawdown_avoided_abs = max(0.0, -continue_max_drawdown_h20)
```

Under one-session delay stress, continued rows remain the baseline continue action and
therefore still contribute zero incremental utility. Defended rows receive one session
of unavoidable exposure before cash defense starts.

```text
if candidate_action == continue_next_h20:
  delayed_policy_net_return_h20_{cost_bps} = continue_return_h20
  delayed_incremental_net_return_h20_{cost_bps} = 0.0

if candidate_action == defend_next_h20:
  first_session_return =
    qfq_close[step_start_pos + 1] / step_start_qfq_close - 1

  delayed_policy_net_return_h20_{cost_bps} =
    first_session_return - cost_bps / 10000

  delayed_incremental_net_return_h20_{cost_bps} =
    delayed_policy_net_return_h20_{cost_bps} - continue_return_h20
```

Full-denominator means use all labelable rows:

```text
labelable_denominator = positive_n + negative_n + neutral_n

full_denominator_mean_incremental_return_{cost_bps} =
  sum(incremental_net_return_h20_{cost_bps}) / labelable_denominator

full_denominator_sum_incremental_return_{cost_bps} =
  sum(incremental_net_return_h20_{cost_bps})

full_denominator_mean_drawdown_avoided_abs =
  sum(drawdown_avoided_abs) / labelable_denominator

delay_stress_mean_incremental_return_{cost_bps} =
  sum(delayed_incremental_net_return_h20_{cost_bps}) / labelable_denominator
```

Do not use selected-entry-only, defended-only, or delay-defended-only denominators for primary decision. Defended-only means are diagnostic.

## 8. Required Reconciliation

16E must reconcile utility over six action-label cells:

```text
defended_positive
defended_negative
defended_neutral
continued_positive
continued_negative
continued_neutral
```

For each split and context stratum, output per cell:

```text
split_bucket
context_stratum
cost_bps
cell_id
candidate_action
label_class
cell_step_n
continue_return_sum
continue_return_mean
continue_max_drawdown_mean
policy_net_return_sum
policy_net_return_mean
incremental_return_sum
incremental_return_mean
drawdown_avoided_abs_sum
drawdown_avoided_abs_mean
```

`six_cell_utility_reconciliation.csv` must use this long schema, with one row
per `(split_bucket, context_stratum, cost_bps, cell_id)`. Do not emit separate
`_0bps`, `_25bps`, `_50bps`, or `_100bps` metric columns in this table; the
`cost_bps` column is the sole cost dimension.

The following identity must hold within tolerance independently for each
`(split_bucket, context_stratum, cost_bps)`:

```text
sum six-cell incremental_return_sum
  == full_denominator_sum_incremental_return for the same split/context/cost key
```

For split-level primary decision, use only `context_stratum = all_steps`.
Context strata are overlapping diagnostic views and must not be summed across
`all_steps`, `known_failed`, `non_known_failed`, `episode_start`, or any other
context readout.

If implementation reports only defended-positive and defended-negative without neutral and continued cells:

```text
six_cell_reconciliation_gate = fail
decision_state = 16E_utility_diagnostic_blocked_by_input_or_lineage_failure
```

## 9. Neutral Handling

Neutral rows must remain in the full utility denominator:

```text
neutral rows are not positive
neutral rows are not negative
neutral rows contribute realized return, drawdown, policy return, and incremental return
neutral rows enter six-cell reconciliation as defended_neutral or continued_neutral
```

Required neutral readouts:

```text
split_bucket
cost_bps
neutral_step_n
neutral_defended_n
neutral_continued_n
neutral_continue_return_mean
neutral_policy_net_return_mean
neutral_incremental_return_sum
neutral_incremental_return_mean
neutral_drawdown_avoided_abs_mean
neutral_utility_gate
neutral_utility_caveat
```

`neutral_utility_readout.csv` must also use a long `cost_bps` schema. The
report may highlight the primary 50 bps row, but the table schema must not mix
primary-cost suffix columns with cost-grid rows.

If neutral rows are dropped from primary full-denominator utility or mapped to binary labels:

```text
neutral_utility_gate = fail
decision_state = 16E_utility_diagnostic_blocked_by_input_or_lineage_failure
```

## 10. Context Stratification

16E must reuse 16D context flags:

```text
all_steps
late_rescue_context
non_late_rescue_context
known_failed_context_any
non_known_failed_context
```

Primary context independence is evaluated on:

```text
non_known_failed_context
```

Reason:

```text
16E must prove utility is not merely a utility expression of 15B known-failed morphology.
```

Validation split context rows with low power remain stress readout only. They cannot block primary decision unless lineage failure is discovered.

## 11. Support Gates

### 11.1 Hard Lineage Gates

All must pass:

```text
input_artifact_gate = pass
upstream_16d_authorization_gate = pass
full_action_panel_rebuild_gate = pass
utility_price_path_gate = pass
action_semantics_gate = pass
policy_utility_binding_gate = pass
six_cell_reconciliation_gate = pass
neutral_utility_gate = pass
context_utility_rebuild_gate = pass
search_accounting_gate = pass
```

Any hard lineage fail maps to:

```text
16E_utility_diagnostic_blocked_by_input_or_lineage_failure
```

except action semantics failure, which maps to:

```text
16E_utility_diagnostic_blocked_by_action_semantics_failure
```

### 11.2 Power Gates

Power gates use labelable denominators unless specified.

```text
train_labelable_step_n >= 10000
train_defended_labelable_step_n >= 3000
train_defended_positive_n >= 1000
train_defended_negative_n >= 1000
train_defended_neutral_n >= 300
train_episode_cluster_n >= 200

robustness_labelable_step_n >= 1000
robustness_defended_labelable_step_n >= 250
robustness_defended_positive_n >= 100
robustness_defended_negative_n >= 100
robustness_defended_neutral_n >= 30
robustness_episode_cluster_n >= 100
```

Validation:

```text
validation_labelable_step_n >= 300
validation_defended_labelable_step_n >= 30
```

Validation power is stress-readout only. If validation is below this floor, set:

```text
validation_stress_low_power_caveat = true
```

but do not block primary decision.

Validation power columns are excluded from `primary_power_gate`,
`context_power_gate`, and the final blocking decision. They may only set
`validation_stress_low_power_caveat = true` unless a separate lineage failure is
discovered.

### 11.3 Primary Return Utility Gates

For primary semantics and `primary_round_trip_defense_cost_bps = 50`:

```text
train_full_denominator_mean_incremental_return_50bps > 0
robustness_full_denominator_mean_incremental_return_50bps > 0
robustness_full_denominator_sum_incremental_return_50bps > 0
```

The 0 bps readout must also be positive in train and robustness:

```text
train_full_denominator_mean_incremental_return_0bps > 0
robustness_full_denominator_mean_incremental_return_0bps > 0
```

If 0 bps passes but 50 bps fails:

```text
decision_state = 16E_utility_diagnostic_cost_or_execution_fragile
next_allowed_requirement = none
```

If both 0 bps and 50 bps fail:

```text
decision_state = 16E_utility_diagnostic_not_supported
next_allowed_requirement = none
```

### 11.4 Drawdown Avoidance Gates

For primary semantics:

```text
train_defended_negative_drawdown_avoided_abs_mean >= 0.08
robustness_defended_negative_drawdown_avoided_abs_mean >= 0.08
train_full_denominator_mean_drawdown_avoided_abs > 0
robustness_full_denominator_mean_drawdown_avoided_abs > 0
```

If return utility fails but drawdown avoidance passes, 16E may report:

```text
utility_interpretation = drawdown_reduction_only_return_not_supported
```

but it must not authorize 16F.

### 11.5 Delay Stress Gates

For `delay_stress_id = one_session_delay_close_to_close_v1` and 50 bps:

```text
train_delay_stress_mean_incremental_return_50bps > 0
robustness_delay_stress_mean_incremental_return_50bps > 0
```

If primary close-to-close utility passes but delay stress fails:

```text
decision_state = 16E_utility_diagnostic_cost_or_execution_fragile
next_allowed_requirement = none
```

### 11.6 Context Utility Gates

For `non_known_failed_context`, power gates are evaluated before utility gates:

```text
non_known_failed_train_labelable_step_n >= 1000
non_known_failed_train_defended_labelable_step_n >= 200
non_known_failed_robustness_labelable_step_n >= 300
non_known_failed_robustness_defended_labelable_step_n >= 50
```

If any non-known-failed context power gate fails:

```text
decision_state = 16E_utility_diagnostic_low_power
context_utility_status = context_power_inconclusive
next_allowed_requirement = none
```

After context power gates pass, utility gates are:

```text
non_known_failed_train_full_denominator_mean_incremental_return_50bps > 0
non_known_failed_train_full_denominator_mean_drawdown_avoided_abs > 0
non_known_failed_robustness_full_denominator_mean_incremental_return_50bps > 0
non_known_failed_robustness_full_denominator_mean_drawdown_avoided_abs > 0
```

Known-failed context utility must be reported with the same readout columns, but it
is diagnostic only. It can explain context concentration; it cannot rescue a
failed non-known-failed utility gate.

If all utility support exists only inside known-failed context after
non-known-failed context power gates pass:

```text
decision_state = 16E_utility_diagnostic_context_concentrated_only
next_allowed_requirement = none
```

### 11.7 Continued Negative Leakage Caveat

Continued negative leakage is not allowed to disappear inside an aggregate utility
pass. Report:

```text
continued_negative_residual_loss_abs =
  sum(max(0.0, -continue_return_h20) for continued_negative rows)

defended_negative_avoided_loss_abs =
  sum(max(0.0, -continue_return_h20) for defended_negative rows)

continued_negative_residual_loss_share =
  continued_negative_residual_loss_abs / max(defended_negative_avoided_loss_abs, epsilon)
```

If primary utility gates pass but `continued_negative_residual_loss_share > 1.0`:

```text
continued_negative_leakage_caveat = utility_positive_but_leaky
```

This caveat does not by itself authorize entry, chained holding, or deployment
logic, and it must appear in the report summary and decision CSV.

### 11.8 Search Accounting Gates

16E must prove:

```text
primary_policy_id inherited from 16D, unchanged
primary_action_semantics_id config-frozen before utility computation
primary_round_trip_defense_cost_bps config-frozen before utility computation
delay_stress_id config-frozen before utility computation
validation_used_for_selection = false
robustness_used_for_selection = false
return_metric_used_for_selection = false
cost_metric_used_for_selection = false
context_filter_used_for_selection = false
threshold_changed_after_16d = false
model_refit_after_16d = false
```

Any violation maps to:

```text
16E_utility_diagnostic_blocked_by_utility_search_or_leakage
```

## 12. Outputs

All publishable tables must be written under:

```text
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_16d_authorization_audit.csv
full_action_panel_rebuild_audit.csv
single_step_action_semantics_audit.csv
utility_price_path_audit.csv
policy_utility_binding_audit.csv
six_cell_utility_reconciliation.csv
utility_by_split_readout.csv
utility_by_context_readout.csv
positive_sacrifice_utility_readout.csv
negative_avoidance_utility_readout.csv
continued_negative_leakage_utility_readout.csv
neutral_utility_readout.csv
cost_delay_stress_readout.csv
validation_stress_utility_readout.csv
search_accounting_audit.csv
sequential_continuation_utility_decision.csv
utility_panel_sample.csv.gz
```

Local cache outputs:

```text
outputs/local_cache/16E_sequential_continuation_utility_diagnostic/utility_panel.parquet
```

Report:

```text
outputs/publishable/reports/sequential_continuation_utility_diagnostic_report.md
```

Manifest:

```text
outputs/manifests/16E_sequential_continuation_utility_diagnostic_manifest.json
```

## 13. Required Table Schemas

### 13.1 `input_artifact_audit.csv`

Minimum columns:

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
blocking_reason
```

### 13.2 `full_action_panel_rebuild_audit.csv`

Minimum columns:

```text
action_panel_source
cache_path
rebuild_config_path
rebuild_runner_path
primary_policy_id
primary_policy_row_count
binary_step_count
neutral_step_count
unique_policy_key_status
candidate_action_missing_n
threshold_value_replayed
threshold_value_expected
threshold_value_abs_diff
split_label_count_replay_status
known_failed_context_replay_status
cache_validation_status
full_action_panel_rebuild_status
blocking_reason
```

### 13.3 `upstream_16d_authorization_audit.csv`

Minimum columns:

```text
upstream_decision_state
upstream_next_allowed_requirement
primary_label_id
selected_threshold_id
primary_horizon_sessions
primary_model_id
primary_policy_id
train_binary_step_n
train_positive_n
train_negative_n
train_defended_binary_step_n
train_defended_negative_n
train_defense_negative_capture_rate
train_positive_sacrifice_rate
train_continue_negative_leakage_rate
robustness_binary_step_n
robustness_positive_n
robustness_negative_n
robustness_defended_binary_step_n
robustness_defended_negative_n
robustness_defense_negative_capture_rate
robustness_defense_precision_lift_vs_binary_negative_base
robustness_positive_sacrifice_rate
robustness_continue_negative_leakage_rate
non_known_failed_robustness_binary_step_n
non_known_failed_robustness_negative_n
non_known_failed_robustness_defended_negative_n
non_known_failed_robustness_defense_precision_lift
soft_overlap_partial_coverage_caveat
known_failed_context_exposure_caveat
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
return_backtest_authorized
cost_model_authorized
model_deployment_authorized
production_signal_authorized
input_artifact_gate
upstream_16c_authorization_gate
upstream_16b_label_rebuild_gate
score_rebuild_lineage_gate
feature_contract_replay_gate
score_orientation_gate
threshold_freeze_gate
neutral_handling_gate
policy_action_binding_gate
known_failed_context_rebuild_gate
search_accounting_gate
power_gate
primary_policy_usefulness_gate
context_independence_gate
authorization_status
blocking_reason
```

### 13.4 `single_step_action_semantics_audit.csv`

Minimum columns:

```text
primary_action_semantics_id
decision_time
baseline_action
continue_exposure
defend_exposure
defend_cash_return_h20
round_trip_defense_cost_bps_grid
primary_round_trip_defense_cost_bps
delay_stress_id
validation_used_for_action_semantics_selection
robustness_used_for_action_semantics_selection
return_metric_used_for_action_semantics_selection
cost_metric_used_for_action_semantics_selection
action_semantics_gate
blocking_reason
```

### 13.5 `utility_price_path_audit.csv`

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
max_drawdown_replay_abs_diff_max
delay_row_missing_n
utility_price_path_gate
blocking_reason
```

### 13.6 `policy_utility_binding_audit.csv`

Minimum columns:

```text
primary_policy_id
primary_action_semantics_id
label_id
threshold_id
horizon_sessions
labelable_step_n
binary_step_n
neutral_step_n
defended_labelable_step_n
continued_labelable_step_n
duplicate_step_policy_key_n
missing_candidate_action_n
missing_utility_price_n
neutral_dropped_from_denominator_n
policy_utility_binding_gate
blocking_reason
```

### 13.7 `six_cell_utility_reconciliation.csv`

One row per split, context stratum, cost tier, and six-cell id:

```text
split_bucket
context_stratum
cost_bps
cell_id
candidate_action
label_class
cell_step_n
continue_return_sum
continue_return_mean
continue_max_drawdown_mean
policy_net_return_sum
policy_net_return_mean
incremental_return_sum
incremental_return_mean
drawdown_avoided_abs_sum
drawdown_avoided_abs_mean
six_cell_reconciliation_status
```

### 13.8 `utility_by_split_readout.csv`

Minimum columns:

```text
split_bucket
cost_bps
labelable_step_n
positive_n
negative_n
neutral_n
defended_labelable_step_n
continued_labelable_step_n
full_denominator_sum_incremental_return
full_denominator_mean_incremental_return
full_denominator_mean_drawdown_avoided_abs
defended_positive_incremental_return_sum
defended_negative_incremental_return_sum
defended_neutral_incremental_return_sum
continued_negative_return_sum
continued_negative_max_drawdown_mean
primary_return_utility_gate
drawdown_avoidance_gate
```

### 13.9 `utility_by_context_readout.csv`

Same core utility columns as `utility_by_split_readout.csv`, plus:

```text
context_stratum
valid_context_power
context_utility_rebuild_gate
context_utility_status
context_caveat
```

### 13.10 `cost_delay_stress_readout.csv`

Minimum columns:

```text
split_bucket
cost_bps
delay_stress_id
labelable_step_n
defended_labelable_step_n
delay_stress_denominator_type
delay_stress_labelable_denominator
delay_stress_continued_zero_incremental_n
primary_close_to_close_mean_incremental_return
delay_stress_mean_incremental_return
primary_minus_delay_delta
cost_delay_stress_status
```

### 13.11 `neutral_utility_readout.csv`

Minimum columns:

```text
split_bucket
cost_bps
neutral_step_n
neutral_defended_n
neutral_continued_n
neutral_continue_return_mean
neutral_policy_net_return_mean
neutral_incremental_return_sum
neutral_incremental_return_mean
neutral_drawdown_avoided_abs_mean
neutral_utility_gate
neutral_utility_caveat
```

### 13.12 `positive_sacrifice_utility_readout.csv`

Minimum columns:

```text
split_bucket
context_stratum
cost_bps
defended_positive_n
defended_positive_continue_return_sum
defended_positive_continue_return_mean
defended_positive_policy_net_return_sum
defended_positive_policy_net_return_mean
defended_positive_incremental_return_sum
defended_positive_incremental_return_mean
positive_upside_sacrificed_abs_sum
positive_upside_sacrificed_abs_mean
positive_sacrifice_status
positive_sacrifice_caveat
```

### 13.13 `negative_avoidance_utility_readout.csv`

Minimum columns:

```text
split_bucket
context_stratum
cost_bps
defended_negative_n
defended_negative_continue_return_sum
defended_negative_continue_return_mean
defended_negative_policy_net_return_sum
defended_negative_policy_net_return_mean
defended_negative_incremental_return_sum
defended_negative_incremental_return_mean
defended_negative_drawdown_avoided_abs_sum
defended_negative_drawdown_avoided_abs_mean
defended_negative_avoided_loss_abs_sum
negative_avoidance_status
negative_avoidance_caveat
```

### 13.14 `continued_negative_leakage_utility_readout.csv`

Minimum columns:

```text
split_bucket
context_stratum
cost_bps
continued_negative_n
continued_negative_continue_return_sum
continued_negative_continue_return_mean
continued_negative_max_drawdown_mean
continued_negative_max_drawdown_worst
continued_negative_residual_loss_abs
defended_negative_avoided_loss_abs
continued_negative_residual_loss_share
continued_negative_leakage_status
continued_negative_leakage_caveat
```

### 13.15 `validation_stress_utility_readout.csv`

Minimum columns:

```text
stress_split_id
cost_bps
labelable_step_n
defended_labelable_step_n
continued_labelable_step_n
positive_n
negative_n
neutral_n
full_denominator_sum_incremental_return
full_denominator_mean_incremental_return
full_denominator_mean_drawdown_avoided_abs
delay_stress_mean_incremental_return
validation_used_for_selection
validation_blocks_decision
validation_stress_status
validation_stress_caveat
```

### 13.16 `search_accounting_audit.csv`

Must declare:

```text
search_family = sequential_continuation_utility_diagnostic
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
primary_round_trip_defense_cost_bps = 50
primary_horizon_sessions = 20
selected_threshold_id = up50pct
primary_label_id = continuation_survival_h20_no_deep_drawdown
validation_used_for_selection = false
robustness_used_for_selection = false
return_metric_used_for_selection = false
cost_metric_used_for_selection = false
context_filter_used_for_selection = false
threshold_changed_after_16d = false
model_refit_after_16d = false
entry_rule_defined = false
chained_policy_simulated = false
portfolio_metric_computed = false
deployment_metric_computed = false
search_accounting_gate
blocking_reason
```

### 13.17 `sequential_continuation_utility_decision.csv`

Minimum columns:

```text
decision_state
next_allowed_requirement
primary_label_id
primary_model_id
primary_policy_id
primary_action_semantics_id
primary_round_trip_defense_cost_bps
primary_return_utility_gate
drawdown_avoidance_gate
delay_stress_gate
context_power_gate
context_utility_gate
six_cell_reconciliation_gate
continued_negative_leakage_caveat
utility_interpretation
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

## 14. Decision Map

Final decision enum:

```text
16E_utility_diagnostic_ready_for_chained_action_transition_freeze
16E_utility_diagnostic_blocked_by_input_or_lineage_failure
16E_utility_diagnostic_blocked_by_action_semantics_failure
16E_utility_diagnostic_blocked_by_utility_search_or_leakage
16E_utility_diagnostic_low_power
16E_utility_diagnostic_not_supported
16E_utility_diagnostic_cost_or_execution_fragile
16E_utility_diagnostic_context_concentrated_only
```

Decision logic:

```text
if any forbidden search / data leakage / chained simulation / entry / deployment contamination:
  decision_state = 16E_utility_diagnostic_blocked_by_utility_search_or_leakage
  next_allowed_requirement = none

elif action_semantics_gate fails:
  decision_state = 16E_utility_diagnostic_blocked_by_action_semantics_failure
  next_allowed_requirement = none

elif any hard lineage gate fails:
  decision_state = 16E_utility_diagnostic_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif any train/robustness primary power gate fails
     or any non-known-failed context power gate fails:
  decision_state = 16E_utility_diagnostic_low_power
  next_allowed_requirement = none

elif primary close-to-close 0bps utility gates pass
     and primary close-to-close 50bps utility gates fail:
  decision_state = 16E_utility_diagnostic_cost_or_execution_fragile
  next_allowed_requirement = none

elif primary close-to-close 50bps utility gates pass
     and delay stress gates fail:
  decision_state = 16E_utility_diagnostic_cost_or_execution_fragile
  next_allowed_requirement = none

elif primary return utility gates fail and drawdown avoidance gates pass:
  decision_state = 16E_utility_diagnostic_not_supported
  next_allowed_requirement = none
  utility_interpretation = drawdown_reduction_only_return_not_supported

elif primary return utility gates fail:
  decision_state = 16E_utility_diagnostic_not_supported
  next_allowed_requirement = none

elif non-known-failed context power gates pass
     and non-known-failed context utility gates fail
     and known-failed context utility readout passes:
  decision_state = 16E_utility_diagnostic_context_concentrated_only
  next_allowed_requirement = none

else:
  decision_state = 16E_utility_diagnostic_ready_for_chained_action_transition_freeze
  next_allowed_requirement = requirement_16f_chained_action_transition_freeze.md
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

If ready, 16E authorizes only writing the 16F chained action transition freeze requirement. It does not authorize any live or simulated trading policy.

## 15. Report Requirements

The Chinese report must include:

1. 单行 decision and next allowed requirement.
2. 16D authorization replay with exact policy and confusion numbers.
3. Explanation that 16E is single-step utility diagnostic, not exit/holding/deployment authorization.
4. Primary single-step action semantics and cost/delay assumptions.
5. Price path rebuild and utility binding lineage.
6. Six-cell utility reconciliation.
7. Positive sacrifice opportunity cost.
8. Avoided negative loss/drawdown and continued negative leakage.
9. Neutral utility handling.
10. Cost grid and one-session delay stress.
11. Known-failed and non-known-failed context utility.
12. Continued negative leakage caveat, if any.
13. Validation stress caveat.
14. Search accounting: no OOS selection, no chained simulation, no entry rule.
15. Findings and insight: whether 16F chained transition freeze is justified.

Report must explicitly state:

```text
16E does not authorize entry, exit, holding, chained simulation, deployment, or live trading.
```

## 16. Manifest Requirements

Manifest must include:

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
upstream_16d_decision
primary_label_id
selected_threshold_id
primary_horizon_sessions
primary_model_id
primary_policy_id
primary_action_semantics_id
primary_round_trip_defense_cost_bps
decision_state
next_allowed_requirement
continued_negative_leakage_caveat
authorization_booleans
input_artifact_hashes
output_hashes
row_counts
large_artifact_policy
```

## 17. Implementation Pattern

Implementation should remain experiment-local and may reuse existing runners via importlib:

```text
16B runner helpers for label and qfq step lineage
16C runner helpers for path resolution, hashing, table writing, and metrics
16D runner helpers for policy score/action rebuild
```

No shared-package refactor is required.

Use local caches only after lineage validation. Required publishable audits remain mandatory even when caches exist. Even if the current workspace contains local parquet caches, implementation must still run the row-count, key, schema, and metric replay checks before trusting them.

Large full row-level panels should be stored as local parquet. Publishable row-level utility output should be sampled/compressed:

```text
utility_panel_sample.csv.gz
max_publishable_utility_panel_sample_rows = 5000
```

## 18. Test Plan

Implement focused synthetic tests covering:

```text
test_16d_ready_authorization_required_for_16e
test_16d_next_allowed_requirement_must_match_16e
test_16d_policy_counts_and_primary_policy_replayed
test_policy_action_sample_cannot_be_used_as_full_source
test_full_action_panel_cache_is_optional_and_must_validate
test_missing_action_panel_rebuilds_via_16d_runner_contract
test_action_semantics_pre_gate_required_before_utility
test_action_semantics_cannot_be_selected_on_robustness_or_validation
test_primary_action_semantics_full_avoidance_cash_h20_formula
test_cost_grid_and_primary_50bps_are_config_frozen
test_qfq_price_path_replays_step_start_end_and_drawdown
test_utility_formula_continue_rows_have_zero_incremental_return
test_utility_formula_defend_rows_subtract_continue_return_and_cost
test_one_session_delay_stress_formula
test_delay_stress_uses_full_labelable_denominator
test_six_cell_reconciliation_exact
test_six_cell_reconciliation_does_not_sum_over_overlapping_contexts
test_neutral_rows_remain_in_full_denominator
test_positive_sacrifice_uses_realized_return_not_counts_only
test_negative_avoidance_uses_return_and_drawdown
test_continued_negative_leakage_reported_even_when_policy_passes
test_continued_negative_leakage_caveat_when_residual_loss_exceeds_avoided_loss
test_full_denominator_utility_not_defended_only_denominator
test_context_utility_non_known_failed_gate
test_context_power_failure_maps_to_low_power_not_context_concentrated
test_validation_stress_readout_does_not_select_or_block_except_lineage
test_all_required_publishable_outputs_have_declared_schema
test_cost_fragility_decision_when_0bps_passes_50bps_fails
test_delay_fragility_decision_when_primary_passes_delay_fails
test_search_accounting_rejects_threshold_semantics_cost_or_context_selection
test_decision_map_action_semantics_failure
test_decision_map_lineage_failure
test_decision_map_low_power
test_decision_map_not_supported
test_decision_map_cost_or_execution_fragile
test_decision_map_context_concentrated_only
test_ready_decision_only_allows_16f_requirement
test_all_trading_deployment_and_chained_sim_authorizations_false
test_manifest_contains_input_artifact_hashes_and_report_hash
test_large_utility_panel_is_local_cache_with_publishable_sample_only
```

## 19. Validation Commands

From `topics/02_AFML_BIG_WINNER`:

```bash
python -m py_compile experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_sequential_continuation_utility_diagnostic.py
python -m pytest experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/tests/test_16e_sequential_continuation_utility_diagnostic.py -q
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_sequential_continuation_utility_diagnostic.py --mode check-inputs
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_sequential_continuation_utility_diagnostic.py --mode full
git diff --check
```

After full run, inspect generated artifact sizes before publish. Full utility panels should remain local parquet unless deliberately compressed and sampled.

## 20. Expected Caveats To Carry Forward

16E must carry these inherited caveats:

```text
16B soft_overlap_partial_coverage_caveat = true
16B known_failed_context_exposure_caveat = true
16C neutral_population_caveat = true
16C validation_stress_evaluable = true but validation is not a selection split
16C history_depth_feature_pair collinearity caveat
16C score separability is diagnostic, not utility
16D defend_next_h20 is label-action preflight, not exit policy
16D robustness defense rate is lower than train threshold quantile
16D continued negative leakage remains high
```

If 16E is ready, 16F must inherit:

```text
up50pct threshold
h20 continuation horizon
non-overlap h20 sampling unit
train-only preprocessing and score threshold freeze
primary policy id defense_bottom_30pct_continuation_score_v1
primary action semantics full_avoidance_cash_h20_close_to_close_v1
primary round-trip defense cost 50bps
neutral handling rules
six-cell utility reconciliation
known-failed context caveat
no entry authorization from 16E
no exit/holding authorization from 16E
no chained simulation authorization from 16E
no deployment authorization from 16E
```
