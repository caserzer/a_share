# 需求：17B Oracle Ladder Replay

## 0. Non-negotiable Scope

17B 是 EP17 的第二个可执行 phase。它只能在 17A 的 denominator / action / replay contract 可复验后运行。

17B 只回答一个问题：

```text
在不训练模型、不调阈值、不做 top-k/bootstrap/matched-base robustness 的前提下，
O0-O5 primary oracle ladder 和 partial-defend action variants 是否能在冻结 denominator、
冻结 cost/action semantics、冻结 qfq replay engine 上被完整重放？
```

17B 的正向裁决只能是：

```text
EP17B_oracle_ladder_ready_for_robustness
next_allowed_requirement = requirement_17c_oracle_robustness_stress.md
```

17B 的负向裁决可以是：

```text
oracle_no_action_value_in_current_space
next_allowed_requirement = none
```

如果任何 17A handoff、denominator、qfq replay、row identity、action semantics、search-accounting check 失败，17B 必须 fail closed：

```text
decision_state = oracle_lineage_or_denominator_blocked
next_allowed_requirement = none
```

17B 不得输出：

```text
new model / refit
new feature set
new payoff label
survival score threshold tuning
robustness-based action selection
validation-based action selection
top-k removal conclusion
cluster/bootstrap conclusion
matched-base conclusion
capacity-constrained oracle conclusion
delayed oracle conclusion
entry policy
exit policy
holding policy
position sizing
portfolio backtest
production signal
deployment authorization
live trading authorization
```

17B 可以计算 oracle future-information upper-bound utility，但这些 utility 只能用于决定是否进入 17C robustness stress。17B 不得把任何 positive oracle number 解释为 deployable edge。

## 1. Identity

```text
experiment_id = 17_oracle_action_value_upper_bound_diagnostic
phase_id = 17B
run_id = 17B_oracle_ladder_replay
requirement_file = requirement_17b_oracle_ladder_replay.md
config_file = configs/config_17b_oracle_ladder_replay.yaml
runner_file = src/run_17b_oracle_ladder_replay.py
test_file = tests/test_17b_oracle_ladder_replay.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths. Artifact identity must use content hash, schema, lineage role, and row-key reconciliation as primary identity.

## 2. 17A Handoff Gate

17B must read 17A artifacts, but must not trust the 17A decision row alone.

Required 17A decision:

```text
decision_state = EP17A_oracle_replay_contract_ready
next_allowed_requirement = requirement_17b_oracle_ladder_replay.md
upstream_closure_gate = pass
input_artifact_gate = pass
denominator_reconciliation_gate = pass
oracle_denominator_binding_gate = pass
action_semantics_gate = pass
price_path_replay_gate = pass
learned_score_reference_gate = pass
ep16_utility_replay_gate = pass
six_cell_sanity_gate = pass
search_accounting_gate = pass
```

Allowed non-blocking 17A status:

```text
capacity_reconstruction_gate = appendix_only
o6_status_for_17b = appendix_only_nonblocking
```

17B must independently validate these 17A machine-readable outputs:

```text
oracle_replay_contract_decision.csv
denominator_lineage_audit.csv
oracle_denominator_binding.csv
action_semantics_audit.csv
replay_price_path_audit.csv
delayed_materialization_audit.csv
input_artifact_audit.csv
oracle_denominator_contract.md
oracle_action_contract.md
oracle_replay_engine_manifest.json
input_artifact_manifest.json
```

The 17A publishable report is not a machine gate for 17B. If report prose is incomplete but the machine-readable contract artifacts pass, 17B may run. If any machine-readable contract artifact is missing, stale, or internally inconsistent, 17B must return `oracle_lineage_or_denominator_blocked`.

## 3. Input Artifacts

Required 17A artifacts:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/oracle_replay_contract_decision.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/denominator_lineage_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/oracle_denominator_binding.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/action_semantics_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/replay_price_path_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/delayed_materialization_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/input_artifact_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/oracle_denominator_contract.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/oracle_action_contract.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_replay_engine_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/input_artifact_manifest.json
```

This list is intentionally the same machine-gate scope as §2. If future edits add a required 17A machine-readable gate in §2, §3 must be updated in the same patch.

Required replay data source:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16E_sequential_continuation_utility_diagnostic/utility_panel.parquet
```

The 16E utility panel is an optional upstream local cache in EP16, but it is a required materialization source for 17B unless the 17B runner can rebuild the required row-level replay panel under:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/local_cache/17B_oracle_ladder_replay/oracle_ladder_panel.parquet
```

If the rebuild path would mutate any EP16 output, 17B must fail closed instead of rebuilding.

Required qfq source:

```text
data/raw/akshare/day/qfq
```

17B must validate qfq materialization for every row used by O0/O2/O5 full-labelable replay and O1/O4 binary replay. A position-only check such as `step_start_pos + k <= step_end_pos` is not sufficient for 17B row admission.

## 4. Denominator Contract

Primary denominator identity:

```text
label_id = continuation_survival_h20_no_deep_drawdown
threshold_id = up50pct
horizon_sessions = 20
primary_model_id = ridge_logistic_bar_state_v1
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_round_trip_defense_cost_bps = 50
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
```

Expected denominator counts:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n | positive_n | negative_n
train        | 20245            | 14962         | 5283           | 10078      | 4884
robustness   | 2496             | 1872          | 624            | 1346       | 526
validation   | 664              | 505           | 159            | 325        | 180
```

Denominator binding:

```text
O0 No Oracle Baseline           -> labelable_full
O1 Perfect Negative Oracle      -> binary_primary; labelable_neutral_stress required
O2 Perfect Deep Drawdown Oracle -> labelable_full
O3 Perfect False-repair Oracle  -> appendix_only_or_skipped_nonblocking unless pre-existing label join is complete
O4 Positive Preservation Oracle -> binary_primary; labelable_neutral_stress required
O5 Perfect Utility Oracle       -> labelable_full
L0 16D Learned-score Reference  -> reference only; not an oracle and not used for oracle selection
```

Fail-closed rules:

```text
O0/O2/O5 observed rows must equal labelable_step_n for every split.
O1/O4 primary rows must equal binary_step_n for every split.
O1/O4 neutral stress rows must reconcile neutral_step_n for every split.
duplicate primary row key count must be 0.
missing primary row key field count must be 0.
missing qfq close or nonfinite qfq close count must be 0.
```

When using the 16E utility panel as an input source, 17B must treat it as a cost-expanded utility table:

```text
expected_raw_16e_utility_panel_rows = 23405 labelable rows * 4 cost tiers = 93620
denominator extraction must use either:
    fixed source cost tier = primary_round_trip_defense_cost_bps
or:
    primary row-key de-duplication before denominator counting
```

Directly counting all cost-expanded rows as denominator rows is a fail-closed implementation bug, not evidence of denominator mismatch.

Canonical 17B field mapping:

```text
17B canonical field        | 16E source field                  | source rule
forward_return_h20         | continue_return_h20               | recompute from qfq close-to-close, then reconcile to source
realized_h20_payoff        | continue_return_h20               | alias of forward_return_h20 for O4 payoff thresholding
signed_max_drawdown_h20    | continue_max_drawdown_h20         | recompute as signed negative drawdown, then reconcile to source
max_drawdown_h20           | signed_max_drawdown_h20           | deprecated alias; implementation should emit signed_max_drawdown_h20
qfq_path_status            | utility_price_status              | canonical status for 17B qfq replay
drawdown_abs_for_reporting | drawdown_avoided_abs              | positive abs reporting field, reconciled to abs(signed_max_drawdown_h20), never used for O2 threshold comparison
drawdown_avoided_abs       | drawdown_abs_for_reporting        | deprecated alias; implementation should emit drawdown_abs_for_reporting
```

If source and canonical names differ, the 17B manifest must record the mapping, the source column, the recomputation formula, and the maximum reconciliation error.

## 5. Oracle Definitions

### O0. No Oracle Baseline

```text
oracle_id = O0
oracle_name = No Oracle Baseline
denominator = labelable_full
policy = blind_continue_all
```

Every labelable row continues through h20. Incremental return versus blind continue must be exactly 0 within numerical tolerance.

O0 variants must be machine-readable:

```text
oracle_variant_id = O0_blind_continue_primary
primary_variant = true
```

### O1. Perfect Negative Oracle

```text
oracle_id = O1
oracle_name = Perfect Negative Oracle
denominator = binary_primary
knows = label_class == negative
negative -> defend
positive -> continue
```

Neutral stress readout:

```text
denominator = labelable_full
neutral -> continue
neutral rows are excluded from O1 primary gate
```

O1 tests whether perfect knowledge of EP16 negative labels has action value.

O1 variants must be machine-readable:

```text
oracle_variant_id = O1_negative_primary
primary_variant = true
```

### O2. Perfect Deep Drawdown Oracle

```text
oracle_id = O2
oracle_name = Perfect Deep Drawdown Oracle
denominator = labelable_full
primary_drawdown_threshold = -0.10
stress_drawdown_thresholds = [-0.08, -0.12, -0.15, -0.20]
deep_drawdown = signed_max_drawdown_h20 <= drawdown_threshold
deep_drawdown -> defend
otherwise -> continue
```

O2 must compute drawdown from the same qfq path lineage as 17A sanity replay. It may use 16E `continue_max_drawdown_h20` only after reconciling that field to qfq for the admitted rows.

Drawdown sign convention is hard-gated:

```text
signed_max_drawdown_h20 <= 0
primary deep drawdown condition = signed_max_drawdown_h20 <= -0.10
stress deep drawdown conditions = signed_max_drawdown_h20 <= {-0.08, -0.12, -0.15, -0.20}
```

Positive absolute fields such as `drawdown_avoided_abs` must never be compared to negative drawdown thresholds. The manifest must record the conversion relationship between the signed negative drawdown used by O2 and any positive absolute drawdown reporting field used for EP16/17A sanity, including the 17A robustness defended-negative absolute drawdown readout `0.164024392171124`.

O2 variants must be machine-readable:

```text
oracle_variant_id        | drawdown_threshold | primary_variant
O2_dd_10pct_primary      | -0.10              | true
O2_dd_08pct_stress       | -0.08              | false
O2_dd_12pct_stress       | -0.12              | false
O2_dd_15pct_stress       | -0.15              | false
O2_dd_20pct_stress       | -0.20              | false
```

Only `O2_dd_10pct_primary` may enter the 17B ready/no-action decision. Stress variants are readouts for the ladder report and for later 17C design only.

### O3. Perfect False-repair Oracle

```text
oracle_id = O3
oracle_name = Perfect False-repair / Ineffective-exposure Oracle
status = appendix_only_or_skipped_nonblocking unless a pre-existing false-repair label joins without ambiguity
```

17B must not create a new false-repair label. If no pre-existing label source is configured and reconciled, emit:

```text
o3_status = skipped_nonblocking
```

O3 must not block O0/O1/O2/O4/O5 ladder readiness.

### O4. Positive Preservation Oracle

```text
oracle_id = O4
oracle_name = Positive Preservation Oracle
denominator = binary_primary
knows = label_class == positive
positive -> continue
negative -> defend
```

Neutral stress readout:

```text
denominator = labelable_full
neutral -> defend
neutral rows are excluded from O4 primary gate
```

High-upside stress:

```text
high_upside_positive thresholds = train-frozen top 30%, top 20%, top 10% realized h20 payoff cutoffs
```

The absolute cutoff values must be learned from train only and written to `oracle_high_upside_threshold_freeze.csv` and the 17B manifest. Robustness and validation must apply the train-frozen absolute cutoffs. Split-local percentile recomputation is forbidden.

O4 variants must be machine-readable:

```text
oracle_variant_id             | variant_rule                                      | primary_variant
O4_label_positive_primary     | label_class == positive                           | true
O4_high_upside_top30_stress   | realized_h20_payoff >= train top-30% cutoff       | false
O4_high_upside_top20_stress   | realized_h20_payoff >= train top-20% cutoff       | false
O4_high_upside_top10_stress   | realized_h20_payoff >= train top-10% cutoff       | false
```

Only `O4_label_positive_primary` may enter the 17B ready/no-action decision. High-upside variants are stress readouts and must not be used to rescue the primary O4 gate.

### O5. Perfect Utility Oracle

```text
oracle_id = O5
oracle_name = Perfect Utility Oracle
denominator = labelable_full
knows = realized net utility of continue vs defend under frozen action semantics and cost
```

Action rule:

```text
if defend_net_return > continue_net_return:
    defend
else:
    continue
```

Neutral rows must remain neutral rows. They cannot be rewritten to positive or negative before O5 action selection. O5 six-cell decomposition must separately report:

```text
defended_neutral
continued_neutral
```

O5 is the core current-action-space upper bound for 17B.

O5 variants must be machine-readable:

```text
oracle_variant_id = O5_perfect_utility_primary
primary_variant = true
```

## 6. Action Intensity and Cost Contract

Action families inherited from 17A:

```text
blind_continue
full_defend_exit_cash
partial_defend_50pct
partial_defend_25pct
learned_score_reference
```

Primary action-intensity grid:

```text
q_continue = 1.00
q_defend in [0.00, 0.25, 0.50]
primary_q_defend = 0.00
```

Cost grid:

```text
round_trip_defense_cost_bps = [0, 25, 50, 100]
primary_round_trip_defense_cost_bps = 50
cash_return = 0
holding_cost = 0
```

Per-row replay formula:

```text
blind_continue_pnl = forward_return_h20
continue_net_return = q_continue * forward_return_h20 - holding_cost
defend_net_return = q_defend * forward_return_h20 - round_trip_defense_cost_bps / 10000
oracle_policy_net_return = selected action net return
incremental_net_return = oracle_policy_net_return - blind_continue_pnl
```

For every `q_defend` and `cost_bps` variant, O5 must independently recompute:

```text
defend_net_return(q_defend, cost_bps)
continue_net_return(q_continue)

if defend_net_return(q_defend, cost_bps) > continue_net_return(q_continue):
    oracle_action = defend
else:
    oracle_action = continue
```

The full-defend O5 action set must not be reused as the partial-defend O5 action set. For O1/O2/O4 deterministic future-condition oracles, the known future condition can be identical across `q_defend`, but the payoff must still use the configured `q_defend` and `cost_bps`. 17B must not choose `q_defend` using robustness or validation results.

## 7. Replay Engine Requirements

17B must create a row-level local replay panel:

```text
outputs/local_cache/17B_oracle_ladder_replay/oracle_ladder_panel.parquet
```

Required row-level fields:

```text
primary row key fields
cluster_split_bucket
label_class
forward_return_h20
realized_h20_payoff
signed_max_drawdown_h20
drawdown_abs_for_reporting
step_start_qfq_close
step_end_qfq_close
qfq_path_status
oracle_id
oracle_variant_id
oracle_variant_name
primary_variant
drawdown_threshold
high_upside_threshold_id
action_intensity_id
cost_bps
q_continue
q_defend
oracle_action
baseline_net_return
oracle_policy_net_return
incremental_net_return
cell_id
```

qfq replay validation must prove for every admitted row:

```text
instrument exists
step_start_pos and step_end_pos are in bounds
step_start_date and step_end_date match qfq dates at those positions
step_start_qfq_close and step_end_qfq_close match qfq close within tolerance
all close values from step_start_pos through step_end_pos are finite and positive
forward_return_h20 reconciles to qfq close-to-close return
realized_h20_payoff equals forward_return_h20 unless explicitly overridden by a frozen payoff formula
signed_max_drawdown_h20 reconciles to qfq path drawdown as a signed nonpositive value
drawdown_abs_for_reporting reconciles to abs(signed_max_drawdown_h20)
```

If qfq replay cannot be proven for a row required by a primary oracle, the whole phase must return `oracle_lineage_or_denominator_blocked`. 17B may not silently drop rows from a primary denominator.

## 8. Main Metrics

Each oracle/oracle-variant/action-intensity/cost/split row must report:

```text
labelable_step_n or binary_step_n according to denominator
defended_step_n
continued_step_n
defended_rate
mean_incremental_return
median_incremental_return
trimmed_mean_incremental_return
winsorized_mean_incremental_return
sum_incremental_return
ev_per_exposure_day
transaction_cost_sum
exposure_days_removed
defended_positive_opportunity_cost
defended_negative_gain
defended_neutral_gain
continued_negative_leakage
continued_positive_retained
net_full_denominator_utility
```

Trimmed and winsorized definitions must be config-frozen before replay:

```text
trim_fraction_each_tail = 0.01
winsor_fraction_each_tail = 0.01
```

These definitions must not vary by split or oracle.

## 9. Six-cell Decomposition

17B must inherit EP16 six-cell attribution:

```text
defended_positive
defended_negative
defended_neutral
continued_positive
continued_negative
continued_neutral
```

Every positive-looking oracle result must be explainable by the six-cell table:

```text
positive sacrifice
negative avoided
neutral contribution / drag
continued negative leakage
continued positive retained
```

For O1/O4 binary-primary rows, six-cell output must include both:

```text
primary_binary denominator decomposition
labelable_neutral_stress decomposition
```

The primary binary gate must not use neutral stress rows.

## 10. Search Accounting

17B search accounting must prove:

```text
no_model_training = true
no_model_refit = true
no_survival_threshold_tuning = true
no_validation_selection = true
no_robustness_tuning = true
no_feature_selection = true
no_payoff_label_redesign = true
no_split_local_payoff_quantile_recompute = true
no_oracle_value_interpretation_beyond_17b = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

Any violation must block 17B.

## 11. Decision Logic

17B decision split discipline:

```text
primary_decision_split = robustness
train = lineage / calibration / explanatory readout only
validation = stress readout only; never rescues or blocks a 17B decision
```

17B primary ladder gate constants:

```text
primary_ladder_metric = trimmed_mean_incremental_return
primary_ladder_metric_floor = 0.0000
primary_ladder_materiality_metric = mean_incremental_return
primary_ladder_materiality_floor = 0.0025
primary_ladder_cost_bps = 50
primary_ladder_q_defend = 0.00
primary_ladder_variants_only = true
primary_ladder_candidate_variants = {
    O1_negative_primary,
    O2_dd_10pct_primary,
    O4_label_positive_primary,
    O5_perfect_utility_primary
}
```

O5 remains in the primary candidate set intentionally because research plan §5 defines O5 as the current action-space theoretical upper bound. To avoid deterministic ready from infinitesimal hindsight gains, 17B ready requires both support and economic materiality:

```text
support_metric: trimmed_mean_incremental_return > 0
materiality_metric: mean_incremental_return >= 0.0025
```

Raw mean alone, median, winsorized mean, non-primary cost grid rows, partial-defend rows, drawdown stress variants, and high-upside stress variants are required readouts, but they must not trigger `EP17B_oracle_ladder_ready_for_robustness` or rescue `oracle_no_action_value_in_current_space`.

Lineage block:

```text
if any input / denominator / qfq / action / search gate fails:
    decision_state = oracle_lineage_or_denominator_blocked
    next_allowed_requirement = none
```

No-action value:

```text
if all primary_ladder_candidate_variants have
       trimmed_mean_incremental_return <= primary_ladder_metric_floor
       or mean_incremental_return < primary_ladder_materiality_floor
   on split_bucket = robustness,
   cost_bps = primary_ladder_cost_bps,
   q_defend = primary_ladder_q_defend:
       decision_state = oracle_no_action_value_in_current_space
       next_allowed_requirement = none
```

Ready for robustness:

```text
if O0-O5 primary ladder materializes,
   O3 is either materialized or explicitly skipped_nonblocking,
   all required figures/tables/manifests are emitted,
   and at least one primary_ladder_candidate_variant has
       trimmed_mean_incremental_return > primary_ladder_metric_floor
       and mean_incremental_return >= primary_ladder_materiality_floor
       on split_bucket = robustness,
       cost_bps = primary_ladder_cost_bps,
       q_defend = primary_ladder_q_defend:
       decision_state = EP17B_oracle_ladder_ready_for_robustness
       next_allowed_requirement = requirement_17c_oracle_robustness_stress.md
```

17B must not emit `oracle_payoff_state_research_allowed`, `oracle_value_exists_feature_gap`, `oracle_delayed_decision_supported`, or `oracle_execution_capacity_blocked`. Those labels require later EP17C/EP17D evidence.

## 12. Required Outputs

Publishable tables under:

```text
outputs/publishable/tables/17B_oracle_ladder_replay/
```

Required tables:

```text
17b_input_gate_audit.csv
17a_contract_validation_audit.csv
oracle_row_replay_audit.csv
oracle_ladder_summary.csv
oracle_six_cell_decomposition.csv
oracle_action_intensity_frontier.csv
oracle_neutral_stress.csv
oracle_o2_drawdown_threshold_replay.csv
oracle_o5_action_selection_proof.csv
oracle_high_upside_threshold_freeze.csv
oracle_ladder_decision.csv
search_accounting_audit.csv
```

`oracle_o2_drawdown_threshold_replay.csv` and `oracle_o5_action_selection_proof.csv` are not optional appendix tables. They are downstream contract artifacts required by 17C contract validation and 17D diagnosis. If either table is missing, omitted from the manifest, or schema-incompatible, 17C/17D must fail closed with `oracle_lineage_or_denominator_blocked`.

Required figures under:

```text
outputs/publishable/figures/17B_oracle_ladder_replay/
```

Required figures:

```text
oracle_ladder_net_utility.png
positive_sacrifice_vs_negative_avoidance.png
```

Required report:

```text
outputs/publishable/reports/oracle_ladder_replay_report.md
```

Required manifests:

```text
outputs/manifests/17B_oracle_ladder_replay_manifest.json
outputs/manifests/oracle_ladder_replay_engine_manifest.json
outputs/manifests/input_artifact_manifest_17b.json
```

Local cache:

```text
outputs/local_cache/17B_oracle_ladder_replay/oracle_ladder_panel.parquet
```

## 13. Required Table Schemas

### 13.1 `17b_input_gate_audit.csv`

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
row_key_status
gate_status
blocking_reason
```

Additional required validation/proof table schemas:

`17a_contract_validation_audit.csv` required columns:

```text
artifact_key
validation_check_id
observed_value
expected_value
validation_status
blocking_reason
```

`oracle_o2_drawdown_threshold_replay.csv` required columns:

```text
oracle_id
oracle_variant_id
primary_variant
split_bucket
cost_bps
q_defend
signed_drawdown_threshold
drawdown_predicate
expected_step_n
observed_step_n
defended_step_n
mean_incremental_return
trimmed_mean_incremental_return
forward_return_replay_abs_diff_max
signed_max_drawdown_replay_abs_diff_max
positive_abs_drawdown_used_for_o2_threshold
drawdown_sign_convention_gate
qfq_lineage_reconciliation_gate
o2_drawdown_replay_gate
blocking_reason
```

This table must contain one row for every O2 threshold variant in Section 5, for every split, `cost_bps`, and `q_defend` readout required by 17B. It must expose `signed_drawdown_threshold`, `defended_step_n`, `mean_incremental_return`, and `trimmed_mean_incremental_return` because 17C and 17D consume these fields directly for O2 threshold robustness and path-risk diagnosis.

`oracle_o5_action_selection_proof.csv` required columns:

```text
split_bucket
cost_bps
q_defend
observed_step_n
defended_step_n
formula
formula_recomputed_mismatch_n
formula_recompute_gate
full_defend_reference_q_defend
full_defend_reference_defended_step_n
action_set_sha256
full_defend_reference_action_set_sha256
action_set_equal_to_full_defend_reference
zero_cost_formula_equivalence_expected
nonreference_full_defend_reuse_gate
o5_action_selection_proof_gate
blocking_reason
```

This table must prove O5 action selection from the frozen action semantics without reusing any non-equivalent full-defend action set. It is a required source for downstream proof that O5 is a perfect-utility upper bound, not a deployable policy.

### 13.2 `oracle_row_replay_audit.csv`

Required columns:

```text
split_bucket
denominator_type
expected_step_n
observed_step_n
duplicate_primary_row_key_n
missing_primary_row_key_field_n
missing_qfq_instrument_n
bad_step_bounds_n
nonfinite_close_n
nonpositive_close_n
forward_return_replay_abs_diff_max
signed_max_drawdown_replay_abs_diff_max
drawdown_abs_replay_abs_diff_max
positive_abs_drawdown_used_for_o2_threshold
drawdown_sign_convention_gate
row_replay_gate
blocking_reason
```

### 13.3 `oracle_ladder_summary.csv`

Required columns:

```text
oracle_id
oracle_name
oracle_variant_id
oracle_variant_name
primary_variant
oracle_status
split_bucket
denominator_type
action_intensity_id
q_defend
cost_bps
expected_step_n
observed_step_n
defended_step_n
continued_step_n
defended_rate
mean_incremental_return
median_incremental_return
trimmed_mean_incremental_return
winsorized_mean_incremental_return
sum_incremental_return
ev_per_exposure_day
transaction_cost_sum
exposure_days_removed
defended_positive_opportunity_cost
defended_negative_gain
defended_neutral_gain
continued_negative_leakage
continued_positive_retained
net_full_denominator_utility
ladder_metric_gate
blocking_reason
```

### 13.4 `oracle_six_cell_decomposition.csv`

Required columns:

```text
oracle_id
oracle_name
oracle_variant_id
oracle_variant_name
primary_variant
split_bucket
denominator_scope
action_intensity_id
q_defend
cost_bps
cell_id
label_class
oracle_action
step_n
mean_baseline_net_return
mean_oracle_policy_net_return
mean_incremental_return
sum_incremental_return
cell_contribution_to_total
six_cell_gate
blocking_reason
```

### 13.5 `oracle_action_intensity_frontier.csv`

Required columns:

```text
oracle_id
oracle_variant_id
oracle_variant_name
primary_variant
split_bucket
cost_bps
q_defend
q_removed
defended_step_n
continued_step_n
mean_incremental_return
trimmed_mean_incremental_return
winsorized_mean_incremental_return
positive_sacrifice
negative_avoidance
neutral_drag
frontier_gate
blocking_reason
```

### 13.6 `oracle_neutral_stress.csv`

Required columns:

```text
oracle_id
oracle_variant_id
oracle_variant_name
primary_variant
split_bucket
cost_bps
q_defend
neutral_action_rule
labelable_step_n
neutral_step_n
primary_binary_step_n
neutral_mean_incremental_return
neutral_sum_incremental_return
primary_binary_mean_incremental_return
labelable_stress_mean_incremental_return
neutral_stress_gate
blocking_reason
```

### 13.7 `oracle_high_upside_threshold_freeze.csv`

Required columns:

```text
threshold_id
oracle_variant_id
train_quantile
train_absolute_payoff_cutoff
train_row_count
robustness_applied_cutoff
validation_applied_cutoff
split_local_recompute_used
threshold_freeze_gate
blocking_reason
```

### 13.8 `oracle_ladder_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
input_gate
row_replay_gate
denominator_gate
oracle_ladder_gate
six_cell_gate
action_intensity_gate
neutral_stress_gate
high_upside_threshold_gate
search_accounting_gate
primary_ladder_metric
primary_ladder_metric_floor
primary_ladder_materiality_metric
primary_ladder_materiality_floor
primary_ladder_cost_bps
primary_ladder_q_defend
primary_positive_oracle_id
primary_positive_oracle_variant_id
o3_status
o6_status_inherited
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

### 13.9 `search_accounting_audit.csv`

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
no_split_local_payoff_quantile_recompute
no_oracle_value_interpretation_beyond_17b
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

## 14. Figure Requirements

`oracle_ladder_net_utility.png` must show:

```text
facets or grouped panels for train / robustness / validation
O0-O5 primary cost = 50bps
primary q_defend = 0.00
mean and trimmed mean incremental return
O3 explicitly marked skipped or appendix-only if not materialized
```

`positive_sacrifice_vs_negative_avoidance.png` must show:

```text
train / robustness / validation facets
O1 / O2 / O4 / O5 points
x-axis = defended_positive_opportunity_cost or positive sacrifice
y-axis = defended_negative_gain or negative avoidance
neutral contribution shown separately, not hidden inside the point label
```

Figures must be generated from the publishable tables, not from a separate hidden computation path.

## 15. Report Requirements

The Chinese report must include:

1. Single-line decision and next allowed requirement.
2. 17A handoff status and any inherited non-blocking appendix status.
3. Denominator counts by split for labelable, binary, and neutral rows.
4. O0-O5 oracle definitions and which denominator each oracle uses.
5. Primary 50bps full-defend ladder summary for train / robustness / validation, limited to `primary_variant = true`.
6. Partial-defend action-intensity frontier for q_defend 0.25 and 0.50.
7. Six-cell decomposition explaining positive sacrifice, negative avoidance, neutral drag, continued negative leakage, and continued positive retained.
8. O1/O4 neutral stress readout and why neutral stress is not used in the binary primary gate.
9. O2 drawdown-threshold replay, including primary `O2_dd_10pct_primary`, stress variants, and qfq lineage reconciliation.
10. O4 high-upside threshold freeze, including primary `O4_label_positive_primary`, stress variants, train absolute cutoffs, and no split-local recomputation.
11. O3 status: materialized, appendix-only, or skipped_nonblocking.
12. O5 action selection proof that each `q_defend/cost_bps` variant recomputes `defend_net_return` and does not reuse the full-defend action set.
13. Primary decision gate constants: robustness split, `trimmed_mean_incremental_return > 0`, `mean_incremental_return >= 0.0025`, 50bps, `q_defend = 0.00`, and primary variants only.
14. Search accounting: no model/refit/threshold/validation/robustness/payoff-label search.
15. Explicit statement that 17B does not authorize entry, exit, holding, sizing, portfolio, deployment, production signal, or live trading.
16. Explicit statement that positive 17B ladder numbers only authorize EP17C robustness stress, not payoff-state research.

## 16. Manifest Requirements

`17B_oracle_ladder_replay_manifest.json` must include:

```text
run_id
experiment_id
phase_id
requirement_file
config_file
runner_file
test_file
created_at_utc
git_commit_if_available
input_artifact_hashes
output_hashes
decision_state
next_allowed_requirement
primary_cost_bps
primary_ladder_metric
primary_ladder_metric_floor
primary_ladder_materiality_metric
primary_ladder_materiality_floor
primary_ladder_cost_bps
cost_grid
q_defend_grid
primary_q_defend
primary_ladder_candidate_variants
trim_fraction_each_tail
winsor_fraction_each_tail
oracle_variant_definitions
o2_drawdown_variant_grid
o4_high_upside_variant_grid
o5_action_recomputed_per_cost_intensity
drawdown_sign_convention
canonical_field_mapping
o3_status
o6_status_inherited
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

`oracle_ladder_replay_engine_manifest.json` must include:

```text
row_key
denominator_binding
oracle_definitions
oracle_variant_definitions
action_intensity_grid
cost_grid
return_formula
o5_action_selection_formula_by_cost_intensity
drawdown_formula
drawdown_sign_convention
qfq_replay_tolerance
trim_winsor_definitions
primary_ladder_gate_constants
high_upside_threshold_source = train_only
```

`input_artifact_manifest_17b.json` must include:

```text
artifact_key
artifact_role
relative_path
sha256
schema_columns
row_count
source_phase_id
lineage_status
```

## 17. Tests

Minimum required tests:

```text
test_17a_ready_decision_is_required_but_not_sufficient
test_denominator_counts_match_17a_binding_for_labelable_and_binary_oracles
test_o0_incremental_return_is_zero
test_o1_o4_neutral_rows_do_not_enter_primary_binary_gate
test_o2_drawdown_threshold_uses_qfq_reconciled_drawdown
test_o2_drawdown_threshold_uses_signed_negative_drawdown_not_abs_field
test_o2_drawdown_threshold_replay_table_is_required_downstream_contract
test_o3_skipped_nonblocking_does_not_block_o0_o5
test_o4_high_upside_thresholds_are_train_frozen_absolute_cutoffs
test_o5_uses_strict_defend_greater_than_continue_rule
test_o5_partial_defend_recomputes_action_by_variant_not_full_defend_set
test_o5_action_selection_proof_table_is_required_downstream_contract
test_partial_defend_grid_is_config_frozen_before_replay
test_oracle_variant_ids_are_unique_and_manifested
test_17b_ready_gate_uses_primary_trimmed_metric_primary_cost_primary_q_only
test_17b_ready_gate_requires_25bps_mean_materiality_floor
test_nonprimary_cost_or_stress_variant_cannot_rescue_ready_decision
test_16e_cost_expanded_panel_is_deduped_before_denominator_count
test_canonical_field_mapping_reconciles_continue_return_and_qfq_return
test_17b_emits_17a_contract_validation_o2_replay_and_o5_proof_tables
test_no_validation_or_robustness_selection_flags_are_true
test_decision_blocks_on_missing_required_qfq_row
test_report_contains_no_deployment_authorization
```

## 18. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER

python -m py_compile experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17b_oracle_ladder_replay.py

python -m pytest experiments/pending/17_oracle_action_value_upper_bound_diagnostic/tests/test_17b_oracle_ladder_replay.py -q

python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17b_oracle_ladder_replay.py --mode check-inputs

python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17b_oracle_ladder_replay.py --mode full

python - <<'PY'
from pathlib import Path
import pandas as pd
base = Path("experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay")
decision = pd.read_csv(base / "oracle_ladder_decision.csv").iloc[0]
assert decision["decision_state"] in {
    "EP17B_oracle_ladder_ready_for_robustness",
    "oracle_no_action_value_in_current_space",
    "oracle_lineage_or_denominator_blocked",
}
assert decision["primary_ladder_metric"] == "trimmed_mean_incremental_return"
assert decision["primary_ladder_materiality_metric"] == "mean_incremental_return"
assert float(decision["primary_ladder_materiality_floor"]) == 0.0025
assert int(decision["primary_ladder_cost_bps"]) == 50
assert float(decision["primary_ladder_q_defend"]) == 0.0
assert str(decision["entry_policy_authorized"]).lower() == "false"
assert str(decision["live_trading_authorized"]).lower() == "false"
print(decision["decision_state"])
PY

git diff --check
```

## 19. Implementation Notes

Implementation should remain experiment-local under:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/
```

The runner may reuse 17A helpers through importlib, but it must not weaken this 17B contract if 17A helper behavior is incomplete. In particular, 17B must perform its own row-level qfq replay validation for admitted oracle rows.

Large row-level replay panels must remain local parquet. Publishable row-level samples are not required for 17B.
