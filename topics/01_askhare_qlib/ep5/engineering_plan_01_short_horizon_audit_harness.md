# EP5 Engineering Plan 01: Short-Horizon Exposure Audit Harness

## 1. Plan Metadata

- Plan id: `ep5_e01_short_horizon_exposure_audit_harness_v1`
- Implements requirement: `ep5_r01_short_horizon_local_feasibility_probe_v1`
- Requirement path: `ep5/requirement_01_short_horizon_local_feasibility_probe_v1.md`
- Upstream discussion: `ep5/discussion.md`
- Status: engineering plan, not research requirement
- Date: 2026-05-21

E01 只负责把 R01 冻结的 short-horizon local feasibility probe 做成可复现、可审计、可验证的本地 harness。

E01 不重新定义：

```text
canonical exposure units
horizon set
execution rule
cost model
split
matched comparator rule
sample / concentration / absolute / relative gates
robustness confirmation
final decision priority
big-winner read-only boundary
```

如果实现发现 R01 某条合同不可执行，必须回到 R01 修改 requirement，不能在 E01 代码或 config 中静默换口径。

## 2. Command Surface

E01 的最小命令面：

```bash
uv run python ep5/scripts/run_r01_short_horizon_local_feasibility_probe.py \
  --config ep5/configs/r01_short_horizon_local_feasibility_probe_v1.yaml

uv run python ep5/scripts/validate_r01_short_horizon_local_feasibility_probe.py \
  --config ep5/configs/r01_short_horizon_local_feasibility_probe_v1.yaml
```

命名原则：

```text
E01 = engineering harness plan
R01 = actual research requirement / output authority
```

因此 runner、config、output root 使用 R01 名称。E01 不创建独立经济结论。

## 3. Required Paths

```text
Config:
  ep5/configs/r01_short_horizon_local_feasibility_probe_v1.yaml

Runner:
  ep5/scripts/run_r01_short_horizon_local_feasibility_probe.py

Validator:
  ep5/scripts/validate_r01_short_horizon_local_feasibility_probe.py

Shared helper module, if needed:
  ep5/scripts/r01_short_horizon_local_feasibility_common.py

Output root:
  ep5/outputs/r01_short_horizon_local_feasibility_probe_v1/
```

Required output layout:

```text
ep5/outputs/r01_short_horizon_local_feasibility_probe_v1/
  cache/
  reports/
  manifests/
```

E01 must not write into `ep2/`, `ep4/`, `BaseRate/`, `Explore*/`, or raw `data/`.

## 4. Non-Goals

E01 must not implement:

- new exposure unit discovery;
- grid search or threshold search;
- model training;
- EP2 hazard model reuse;
- confirm-add;
- holding tuning;
- stop-loss tuning beyond the one R01 fixed fast-fail variant;
- hedged / market-neutral replay;
- portfolio allocator;
- production signal export;
- validation-driven subset selection;
- right-tail pass/fail logic.

E01 can provide clean extension points for future phases only as disabled code paths or schema placeholders. Those placeholders must not affect the R01 run.

## 5. Config Contract

The config must be declarative and narrow. It must not expose a search space.

Minimum config skeleton:

```yaml
phase: ep5_r01_short_horizon_local_feasibility_probe_v1
plan_id: ep5_e01_short_horizon_exposure_audit_harness_v1
requirement_id: ep5_r01_short_horizon_local_feasibility_probe_v1
requirement_path: ep5/requirement_01_short_horizon_local_feasibility_probe_v1.md
output_root: ep5/outputs/r01_short_horizon_local_feasibility_probe_v1

data_sources:
  qlib_provider_uri: data/qlib/cn_data_pit
  pit_universe_path: data/universe/pit_mcap500_mainboard_daily.csv
  pit_qlib_instrument_universe_path: data/universe/pit_qlib_instrument_universe.csv
  pit_industry_path: data/targets/pit_industry_membership.csv
  trading_calendar_path: data/qlib/cn_data_pit/calendars/day.txt
  qlib_instrument_path: data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt
  index_instrument: SH000300

split:
  train_start: "2017-07-04"
  train_end: "2021-12-31"
  validation_start: "2022-01-01"
  validation_end: "2023-12-31"
  robustness_start: "2024-01-01"
  robustness_end: "2025-12-31"

execution:
  signal_date_rule: close_derived_signal_date
  entry_execution_rule: first_executable_next_open
  natural_exit_rule: open_after_h_trading_days
  horizons: [5, 10, 20]
  primary_horizon: 10
  buy_cost_bps: 30
  sell_cost_bps: 80
  round_trip_cost_bps: 110
  max_entry_execution_lag_trading_days: 5
  max_exit_execution_lag_trading_days: 5
  mainboard_limit_inference_pct: 0.095

frozen_formula_constants:
  launch_detector_id: EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20
  launch_history_window_rows: 80
  launch_price_lookback_trading_days: 60
  launch_breakout_min_return: 0.12
  launch_money_ma_window_trading_days: 20
  launch_money_surge_ratio: 2.0
  launch_money_floor_cny: 50000000
  launch_episode_merge_gap_trading_days: 20
  fast_fail_drawdown: -0.06
  vcp_base_length_trading_days: 20
  vcp_base_drawdown_min: -0.12
  vcp_breakout_ret_min: 0.00
  vcp_breakout_ret_max: 0.08
  vcp_vol_contraction_max: 0.80
  vcp_ma20_distance_abs_max: 0.12
  vcp_atr20_pct_max: 0.10
  vcp_money_ratio5_to20_min: 1.10
  vcp_money_ratio5_to20_max: 2.50
  vcp_avg_money20_rank_pct_min: 0.30
  right_tail_horizon_trading_days: 120
  right_tail_plus20_threshold: 0.20
  right_tail_plus50_threshold: 0.50

canonical_units:
  - r01_launch_breakout_money_surge_natural_exit_v0
  - r01_launch_breakout_money_surge_fast_fail_v0
  - r01_base_breakout_vcp_sparse_natural_exit_v0

guardrails:
  allow_extra_units: false
  allow_extra_horizons: false
  allow_threshold_override: false
  allow_validation_subset_selection: false
  allow_model_training: false
  allow_hedged_replay: false
  allow_portfolio_pass_fail: false
```

Validator must fail closed if:

```text
canonical_units is not exactly the three R01 units
horizons is not exactly [5, 10, 20]
primary_horizon is not 10
any cost field differs from R01
any execution lag or limit-inference field differs from R01
any split date differs from R01
any frozen formula constant differs from R01
any guardrail is missing or not false where required
```

## 6. Pipeline Stages

E01 runner should be structured as deterministic stages. Each stage writes explicit audit artifacts.

### 6.1 Stage A: Input Authority and Data Audit

Responsibilities:

- resolve all config paths relative to topic root;
- initialize local Qlib PIT provider;
- verify required fields: open, high, low, close, volume, money, factor;
- verify PIT universe and instrument mapping coverage;
- verify PIT industry membership availability;
- verify SH000300 index data availability;
- verify calendar covers all split dates plus required lookbacks / forward horizons.

Required outputs:

```text
reports/r01_artifact_authority.csv
reports/r01_input_data_audit.csv
reports/r01_provider_field_audit.csv
manifests/r01_run_manifest.json
```

`r01_artifact_authority.csv` minimum schema:

```text
artifact_role
artifact_path
required
exists
sha256
row_count
status
notes
```

### 6.2 Stage B: As-Of Feature Panel

Build one deterministic daily feature panel for all canonical units and comparators.

Required cache:

```text
cache/r01_daily_feature_panel.parquet
```

Minimum row grain:

```text
instrument_id
trade_date
```

Minimum fields:

```text
instrument_id
trade_date
split
open
high
low
close
volume
money
factor
log_return
pit_universe_member
industry_id
avg_money20_asof
liquidity_quintile
avg_money20_rank_pct
close_count_80
history_ok
rolling_min_close_60_prev
rolling_max_close_60_prev
money_ma20_prev
money_ma5
money_ratio5_to20
ma20
atr20_pct
base_high_20_prev
base_low_20_prev
base_drawdown_pct
breakout_ret_pct
pre_base_vol20
recent_vol10
vol_contraction_ratio
index_close
index_ma60
index_ret20
market_state
beta120
beta_bucket
beta_bucket_boundary_version
```

Feature rules:

- all predictive features must be as-of `signal_date = D close`;
- rolling references for event formulas must not use future dates;
- train split terciles define beta buckets;
- liquidity quintiles are cross-sectional by signal date;
- every formula input used by R01 §7.1 and §7.3 must be materialized or reproducibly derived from this panel;
- missing required feature rows are not silently imputed.

Required audit:

```text
reports/r01_feature_asof_audit.csv
reports/r01_formula_input_coverage_audit.csv
reports/r01_market_state_beta_bucket_audit.csv
reports/r01_beta_bucket_boundary_audit.csv
```

### 6.3 Stage C: Canonical Unit Registry

Freeze and emit the implementation interpretation of all three units before generating events.

Required output:

```text
reports/r01_canonical_unit_registry.csv
reports/r01_formula_freeze_audit.csv
```

`r01_canonical_unit_registry.csv` minimum schema:

```text
canonical_unit_id
unit_role
event_source_family
final_decision_authority
horizons
entry_rule
exit_rule
fixed_fast_fail_enabled
formula_hash
formula_text_hash
formula_constants_hash
status
```

`r01_formula_freeze_audit.csv` minimum schema:

```text
canonical_unit_id
source_requirement_section
formula_name
frozen_constant_name
frozen_constant_value
formula_text_hash
formula_constants_hash
implementation_hash
status
```

Validator must fail closed if any unit role differs from R01:

```text
r01_launch_breakout_money_surge_natural_exit_v0 = primary short-horizon exposure unit
r01_launch_breakout_money_surge_fast_fail_v0 = secondary loss-control variant
r01_base_breakout_vcp_sparse_natural_exit_v0 = backup sparse event-source probe
```

### 6.4 Stage D: Event Generation

Generate canonical event rows.

Required cache:

```text
cache/r01_canonical_event_panel.parquet
```

Minimum schema:

```text
canonical_unit_id
instrument_id
signal_date
episode_id
episode_start_signal_date
event_key
split
unit_role
detector_id
detector_formula_hash
formula_hash
formula_input_row_hash
source_requirement_section
event_collapse_window_trading_days
event_status
```

`event_status` is an E01 implementation audit field only. It must not participate in R01 gate, relative-positive logic, final-decision priority, or any validation-time event selection.

For launch units:

```text
episode_id = instrument_id + episode_start_signal_date + detector_id
event_key = canonical_unit_id + instrument_id + episode_start_signal_date
```

For sparse VCP unit:

```text
event_key = canonical_unit_id + instrument_id + signal_date_after_collapse
event_collapse_window_trading_days = 20
```

Required audit:

```text
reports/r01_event_generation_audit.csv
reports/r01_event_overlap_audit.csv
```

Event overlap audit must report overlap among the three units but must not use overlap to select or remove events.
Event generation audit must separately report raw formula hits, post-collapse events, dropped duplicate episode members, and blocked formula rows by canonical unit.

### 6.5 Stage E: Execution Replay

Replay every event for H5, H10, H20 under R01 execution and cost rules.

Required cache:

```text
cache/r01_execution_event_panel.parquet
```

Minimum schema:

```text
canonical_unit_id
unit_role
instrument_id
event_key
signal_date
horizon
split
entry_execution_date
entry_price
natural_exit_target_date
natural_exit_signal_date
natural_exit_execution_date
natural_exit_price
fast_fail_enabled
fast_fail_drawdown
fast_fail_signal_date
exit_execution_date
exit_price
buy_cost_bps
sell_cost_bps
round_trip_cost_bps
gross_return
net_return
execution_status
blocked_reason
entry_lag_trading_days
exit_lag_trading_days
```

`execution_status` and `blocked_reason` are separate fields. `execution_status` uses the prefixed status enum below; `blocked_reason` must use the unprefixed R01 blocked-reason enum and must be empty for complete rows.

Execution status values:

```text
complete_executable
blocked_missing_open
blocked_missing_exit_open
blocked_zero_volume
blocked_zero_money
blocked_not_universe_member
blocked_limit_up_inferred_on_entry
blocked_limit_down_inferred_on_exit
blocked_missing_calendar_next_day
blocked_insufficient_forward_trading_days
blocked_split_boundary
```

Allowed `blocked_reason` values must exactly match R01 and must be unprefixed:

```text
missing_open
missing_exit_open
zero_volume
zero_money
not_universe_member
limit_up_inferred_on_entry
limit_down_inferred_on_exit
missing_calendar_next_day
insufficient_forward_trading_days
split_boundary
```

Rows with `execution_status = complete_executable` must have empty `blocked_reason`. Blocked rows must keep the R01 blocked reason and must be present in denominator audits.

Required audit:

```text
reports/r01_execution_block_audit.csv
reports/r01_denominator_audit.csv
```

### 6.6 Stage F: Matched Comparator Builder

Build comparator return rows after event replay.

Required cache:

```text
cache/r01_matched_comparator_panel.parquet
```

Minimum schema:

```text
canonical_unit_id
event_key
horizon
split
instrument_id
entry_execution_date
exit_execution_date
candidate_scope_0_count
same_industry_same_liquidity_count
same_industry_only_count
same_liquidity_only_count
same_day_pit_universe_count
primary_comparator_scope
matched_comparator_count
matched_comparator_net_return
matched_comparator_net_return_median
matched_delta_return
matched_delta_return_vs_comparator_median
matched_comparator_status
same_day_universe_delta_return
industry_only_delta_return
liquidity_only_delta_return
SH000300_delta_return
fallback_comparator_used
```

`fallback_comparator_used` is an E01 implementation audit field only. It can feed fallback quality aggregation in Stage G, but it must not directly set `relative_positive` at row level or enter final decision inputs as a selector.

Allowed `primary_comparator_scope` values:

```text
same_industry_same_liquidity
same_industry_only
same_liquidity_only
same_day_pit_universe
```

Allowed `matched_comparator_status` values:

```text
comparable
blocked_insufficient_comparator
blocked_missing_comparator_price
```

The comparator builder must use equal-weight arithmetic mean for primary matched return. Median is audit-only.
If `primary_comparator_scope = same_day_pit_universe` and `matched_comparator_count < 100`, `matched_comparator_status` must be `blocked_insufficient_comparator`.
Stage F must not compute or overwrite `relative_positive`. It only emits row-level comparator scope, count, status, and delta fields; Stage G is the only stage allowed to aggregate fallback share and set `weak_comparator_quality` / `relative_positive`.

Required audits:

```text
reports/r01_comparator_scope_audit.csv
reports/r01_relative_denominator_audit.csv
reports/r01_comparator_fallback_quality_audit.csv
```

### 6.7 Stage G: Gate Summaries

Aggregate R01 event and comparator rows into gate-ready summary tables.

Required reports:

```text
reports/r01_event_summary_by_unit_horizon_split.csv
reports/r01_event_summary_by_unit_horizon_year.csv
reports/r01_regime_beta_decomposition.csv
reports/r01_industry_liquidity_decomposition.csv
reports/r01_sample_gate_audit.csv
reports/r01_concentration_gate_audit.csv
reports/r01_absolute_gate_audit.csv
reports/r01_relative_gate_audit.csv
reports/r01_robustness_confirmation_audit.csv
reports/r01_horizon_shape_audit.csv
```

`r01_event_summary_by_unit_horizon_split.csv` must include every field required by R01 §11, including:

```text
canonical_unit_id
unit_role
horizon
split
signal_event_count
entry_executable_count
complete_event_count
blocked_event_count
complete_event_share
mean_gross_return
mean_net_return
median_net_return
p10_net_return
p25_net_return
p75_net_return
p90_net_return
loss_rate
relative_comparable_event_share
blocked_insufficient_comparator_count
fallback_comparator_share
mean_matched_delta_return
median_matched_delta_return
p10_matched_delta_return
matched_loss_rate_delta
matched_comparator_count_mean
matched_comparator_scope_same_industry_same_liquidity_share
matched_comparator_scope_same_industry_only_share
matched_comparator_scope_same_liquidity_only_share
matched_comparator_scope_same_day_pit_universe_share
same_day_universe_delta_mean
industry_only_delta_mean
liquidity_only_delta_mean
SH000300_delta_mean
top1_instrument_event_share
top5_instrument_event_share
top1_industry_event_share
top5_industry_event_share
top1_entry_date_event_share
year_count
min_year_complete_event_count
sample_status
sample_gate_pass
concentration_gate_pass
absolute_positive
relative_positive
weak_comparator_quality
horizon_pass
strongly_negative
adjacent_horizon_shape_status
robustness_confirmed
```

All matched-delta statistics used for relative gates must be computed only on:

```text
matched_comparator_status = comparable
```

Stage G is the only stage that computes `weak_comparator_quality`. If validation `primary_comparator_scope = same_day_pit_universe` share exceeds 30% for the current `canonical_unit_id + horizon`, `weak_comparator_quality` must be true and `relative_positive` must be false.

`r01_event_summary_by_unit_horizon_year.csv` minimum schema:

```text
canonical_unit_id
unit_role
horizon
split
calendar_year
complete_event_count
complete_event_share
mean_net_return
median_net_return
p10_net_return
loss_rate
relative_comparable_event_share
mean_matched_delta_return
median_matched_delta_return
p10_matched_delta_return
matched_loss_rate_delta
fallback_comparator_share
top1_instrument_event_share
top1_industry_event_share
top1_entry_date_event_share
year_gate_status
```

`r01_regime_beta_decomposition.csv` and `r01_industry_liquidity_decomposition.csv` minimum schema:

```text
canonical_unit_id
horizon
split
decomposition_axis
decomposition_value
complete_event_count
mean_net_return
median_net_return
p10_net_return
loss_rate
relative_comparable_event_share
mean_matched_delta_return
median_matched_delta_return
p10_matched_delta_return
matched_loss_rate_delta
event_share
net_return_contribution_share
matched_delta_contribution_share
```

Decomposition outputs are explanatory only. The validator must fail closed if final decision replay uses a decomposition subset as a selection gate.

### 6.8 Stage H: Right-Tail Diagnostic

Build read-only H120 right-tail diagnostic.

Required cache:

```text
cache/r01_right_tail_diagnostic_panel.parquet
```

Minimum schema:

```text
canonical_unit_id
event_key
instrument_id
split
entry_execution_date
entry_price
max_gain_120d
first_plus20_hit_date
first_plus20_hit_offset
first_plus50_hit_date
first_plus50_hit_offset
H5_net_return
H10_net_return
H20_net_return
post_H20_max_gain_to_H120
right_tail_status
right_tail_path_status
```

Allowed `right_tail_path_status` values:

```text
complete_same_split_120d
complete_cross_split_120d_readonly
censored_split_boundary
censored_provider_end
blocked_missing_forward_path
```

Allowed `right_tail_status` values:

```text
hit_plus50
hit_plus20_only
no_hit_complete
censored_not_evaluable
blocked_missing_forward_path
```

Split-level right-tail aggregates may use only `right_tail_path_status = complete_same_split_120d`. Rows with censored path status must have `right_tail_status = censored_not_evaluable`, not `no_hit_complete`.

Required report:

```text
reports/r01_right_tail_readout.csv
reports/r01_right_tail_censoring_audit.csv
```

Right-tail tables must be excluded from final decision computation. The validator must fail closed if final decision logic reads right-tail status as an input.

### 6.9 Stage I: Final Decision Payload

Apply R01 final decision priority exactly.

Required outputs:

```text
reports/r01_final_decision.csv
reports/r01_final_decision_inputs.csv
manifests/r01_artifact_hashes.json
```

`r01_final_decision.csv` schema:

```text
requirement_id
priority_rule_id
final_decision
primary_unit_h10_quadrant
primary_unit_robustness_confirmed
primary_unit_adjacent_horizon_status
sparse_unit_status
fast_fail_unit_status
allowed_next_requirement
blocked_next_requirements
decision_reason
created_at
```

`r01_final_decision_inputs.csv` must contain the exact gate rows and booleans read by the final decision function. It must not contain right-tail fields or decomposition subset filters.

Allowed `final_decision` values must exactly match R01:

```text
r01_short_horizon_local_unit_supported
r01_sparse_event_unit_supported_event_source_followup
r01_fast_fail_only_loss_control_lead
r01_unstable_validation_only_lead
r01_unstable_horizon_shape_no_search_allowed
r01_adjacent_horizon_not_evaluable_validation_lead
r01_relative_edge_only_hedged_or_regime_audit_required
r01_beta_or_market_exposure_only_no_stock_selection_pass
r01_horizon_specific_lead_only_no_search_allowed
r01_sample_limited_primary_lead_only
r01_sample_limited_sparse_event_source_lead_only
r01_no_local_feasibility_support
r01_blocked_data_or_execution_contract
```

Priority order must match R01 §15 exactly:

```text
rule_01_blocked_data_or_execution_contract
rule_02_primary_supported
rule_03_primary_validation_only_lead
rule_04_primary_unstable_horizon_shape
rule_05_primary_adjacent_horizon_not_evaluable
rule_06_sparse_event_source_followup
rule_07_fast_fail_only_loss_control_lead
rule_08_relative_edge_only
rule_09_beta_or_market_exposure_only
rule_10_horizon_specific_lead_only
rule_11_sample_limited_primary_lead_only
rule_12_sample_limited_sparse_lead_only
rule_13_no_local_feasibility_support
```

The validator must replay this order as first-match priority. `rule_06_sparse_event_source_followup` must additionally require the primary natural-exit H10 sample gate and concentration gate to pass, matching R01's sparse-unit boundary. `rule_08_relative_edge_only`, `rule_09_beta_or_market_exposure_only`, and `rule_10_horizon_specific_lead_only` may count the sparse unit only when the same primary H10 sample/concentration precondition is true.

## 7. Validator Contract

The validator must be separate from the runner. It must read outputs and fail closed.

Required validation checks:

```text
1. config exists and matches R01 frozen constants
2. all required outputs exist
3. artifact hashes are recorded
4. canonical unit registry contains exactly three units
5. no extra horizons or extra units exist in outputs
6. daily feature panel contains every materialized formula input field
7. event formulas match frozen R01 definitions and formula hashes
8. formula constants match R01 and are not replaced using train split outcomes
9. no train-driven, validation-driven, or robustness-driven threshold or subset fields exist
10. execution rows have valid date ordering
11. blocked rows are present in denominator audit
12. blocked_reason values match the unprefixed R01 enum
13. comparator status and denominator rules are respected
14. fallback comparator quality downgrade is computed only in Stage G aggregation
15. matched-delta gate statistics use only comparable rows
16. robustness matched-delta statistics use only comparable rows
17. year-level gate inputs are present and reconcile to split summaries
18. required regime / beta / industry / liquidity decomposition outputs exist
19. H5/H20 horizon gates are parameterized, not hard-coded to H10
20. right-tail status enum and censoring aggregation rules are respected
21. right-tail status is absent from final decision inputs
22. decomposition subset filters are absent from final decision inputs
23. final decision is in the R01 enum
24. final decision priority order matches R01 §15 rule 1-13
25. final decision is reproducible from gate audit tables
26. final report contains required boundary language and validator status
```

Validator output:

```text
manifests/r01_validation.json
reports/r01_validation_gate_audit.csv
reports/r01_schema_validation_audit.csv
reports/r01_final_decision_replay_audit.csv
reports/r01_final_report.md
```

`r01_validation.json` minimum fields:

```text
validation_status
requirement_id
plan_id
config_path
output_root
gate_count
passed_gate_count
failed_gate_count
final_decision
created_at
```

`validation_status` values:

```text
passed
failed
blocked_missing_required_artifact
blocked_schema_mismatch
blocked_contract_drift
```

## 8. Report Contract

`reports/r01_final_report.md` must be generated after validation from structured runner outputs plus validator outputs. Manual edits are not the authority.

The validator may own report rendering, or it may call a pure report renderer after producing `manifests/r01_validation.json`. In either case, the renderer must not mutate runner artifacts, recompute final decision with different logic, or inspect validation results to change any event, gate, comparator, or final-decision row.

Required sections:

```text
1. Boundary and non-goals
2. Input and data audit
3. Canonical unit registry
4. Execution denominator and blocking
5. H10 four-quadrant result
6. H5/H20 horizon shape
7. Matched comparator and relative edge
8. Year / regime / beta-state decomposition
9. Robustness confirmation
10. Right-tail diagnostic, read-only
11. Final decision and allowed next requirement
12. Validator status
```

The report must contain these literal boundary statements:

```text
R01 did not perform alpha search.
R01 did not use big-winner labels for pass/fail.
R01 did not tune thresholds after validation.
R01 does not approve a production strategy.
```

The report must not contain:

```text
production approved
alpha pool passed
live trading signal
portfolio allocator approved
hedged strategy passed
```

## 9. Implementation Order

Recommended implementation sequence:

1. Create config and path helpers.
2. Implement local provider loading and input audits.
3. Build daily feature panel.
4. Implement canonical unit registry and formula audits.
5. Implement event generation for the primary launch unit.
6. Add fast-fail variant from the same event source.
7. Add sparse VCP event source.
8. Implement execution replay for H5/H10/H20.
9. Implement matched comparator builder.
10. Implement gate summaries and final decision replay.
11. Implement right-tail diagnostic as read-only.
12. Implement validator, including final-decision replay.
13. Implement validation-backed final report renderer.
14. Run runner and validator/report rendering from topic root with `uv run`.

No stage should inspect validation results to mutate earlier runner artifacts.

## 10. Implementation Guardrails

E01 must fail closed if any of the following happen:

```text
config contains more than the three R01 canonical units
config contains more than H5/H10/H20
runner accepts threshold lists or grids for event formulas
runner reads EP2 hazard predictions
runner reads EP4 R02/R03/R04/R05 candidate pools as event sources
runner uses right-tail fields in final decision logic
runner creates a hedged return as primary metric
runner suppresses blocked executions from denominator audits
runner drops events after seeing validation returns
validator and runner compute different final decisions
final report is generated from manual edits or from a pre-validation report stub
```

## 11. Completion Criteria

E01 is complete only when:

```text
uv run python ep5/scripts/run_r01_short_horizon_local_feasibility_probe.py --config ep5/configs/r01_short_horizon_local_feasibility_probe_v1.yaml
```

generates all required runner artifacts, and:

```text
uv run python ep5/scripts/validate_r01_short_horizon_local_feasibility_probe.py --config ep5/configs/r01_short_horizon_local_feasibility_probe_v1.yaml
```

ends with:

```text
validation_status = passed
```

and writes both:

```text
manifests/r01_validation.json
reports/r01_final_report.md
```

`validation_status = passed` means the harness respected the R01 contract. It does not mean the exposure unit passed economically. The economic outcome is only the `final_decision` in `reports/r01_final_decision.csv`.
