# EP2 Requirement 04: Holding / Exit and Winner-Capture Extension

## 1. Purpose

Requirement 04 implements the first formal EP2 holding / exit phase after the passed Requirement 03 schedule bridge.

This phase answers one narrow question:

> Can the frozen Requirement 03 probe / confirm-add exposure process be extended with deterministic, observable holding and exit rules that improve big-winner capture without sacrificing the short-horizon after-cost edge, tail-risk control, turnover discipline, or concentration controls established in Requirements 01-03?

Requirement 04 is a holding / exit and winner-capture extension. It is not a new entry model, not a new label search, not a new hazard threshold search, not a BaseRate integration phase, and not a portfolio-level strategy freeze.

## 2. Entry Gate

Requirement 04 may start only after Requirement 03 passes:

```bash
uv run python ep2/scripts/validate_requirement_03_schedule_bridge.py --config ep2/configs/requirement_03_schedule_bridge.yaml
```

Required Requirement 03 state:

```yaml
phase: requirement_03_schedule_bridge
validation_status: passed
next_phase_proceed_status: passed
primary_label_id: confirm_h10_u10_d06_conservative_fail
frozen_baseline_id: probe_with_simple_stop
hazard_schedule_id: hazard_probe_with_simple_stop
schedule_bridge_id: hazard_probe_confirm_add_fast_fail
selected_threshold: 0.3205667777673395
selected_stop_risk_ceiling: 0.27410397287415667
```

Requirement 03 gate counts are not required to be stored in the manifest. They must be derived from:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_gate_audit.csv
```

Required derived gate state:

```yaml
gate_count: 17
passed_gate_count: 17
failed_gate_count: 0
```

The Requirement 03 evidence that unlocks Requirement 04 is:

| Split | exposed count | probe rate | confirm-add rate | mean after-cost return | p05 after-cost return | strict big-winner capture | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| validation | `104` | `0.195489` | `0.139098` | `0.008592` | `-0.007543` | `0.046512` | passed |
| robustness | `149` | `0.193506` | `0.142857` | `0.005769` | `-0.018225` | `0.023622` | passed |

If Requirement 03 no longer passes, stop. Do not patch Requirement 04 to work around a failed schedule bridge contract.

## 3. Frozen Inputs

Requirement 04 may read only these input roots:

```text
ep2/engineering_baseline/outputs/
ep2/outputs/requirement_01_label_and_baseline_freeze/
ep2/outputs/requirement_02_hazard_timing_model/
ep2/outputs/requirement_03_schedule_bridge/
data/qlib/cn_data_pit/
```

The PIT Qlib root is allowed only for deterministic execution-price, holding-path, and exit-state evaluation. It must not be used for new entry features, model fitting, label reselection, threshold reselection, or schedule-family selection beyond the pre-registered rules in this document.

The PIT price source must be frozen as an input authority. The runner must compute and report:

```text
pit_price_source_hash
pit_calendar_hash
pit_price_field_schema_version
pit_price_hash_scope
```

The minimum hash scope is all instruments referenced by Requirement 03 schedule rows and all trading dates needed to evaluate exits through `confirm_add_execution_date + 120` trading days. The price schema must include `open`, `high`, `low`, and `close`; `volume` and `money` should be hashed when available but are not allowed to become R04 signal features. If any required field or date is missing for an episode, that episode must receive an explicit missing-price status and must not be silently dropped.

Minimum required EP2 inputs:

```text
ep2/outputs/requirement_03_schedule_bridge/manifests/requirement_03_schedule_bridge_manifest.json
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_schedule_action_panel.parquet
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_exposure_daily_panel.parquet
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_episode_schedule_summary.parquet
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_schedule_results.csv
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_schedule_comparison.csv
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_gate_audit.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_episode_primary_probe.csv
ep2/engineering_baseline/outputs/cache/ep2_path_label_panel.parquet
ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv
ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json
```

Forbidden inputs:

- Explore9 / Explore10 row-level outputs or caches;
- BaseRate row-level prediction, order, trade, or portfolio-return panels;
- raw full-market daily TopK data;
- any new provider pull;
- any label not frozen by Requirement 01, except the existing big-winner target fields needed for audit-only capture metrics;
- robustness years for schedule selection, threshold selection, or rule selection;
- future target labels as state-machine inputs;
- BaseRate annual return, drawdown, or turnover as Requirement 04 selection criteria.

## 4. Non-Goals

This phase does not do:

- train or refit a hazard model;
- select a new hazard threshold or stop-risk ceiling;
- change the primary label;
- change the frozen launch pool;
- change the Requirement 03 probe / confirm-add entry process;
- tune confirm-add delay, weight, missed-gain cap, or hazard score threshold;
- build BaseRate integration or attribution;
- compare EP2 and BaseRate annual return / max drawdown as portfolio strategies;
- proceed to P1 strategy validation;
- freeze a production strategy;
- perform path-to-primitive translation, leaf extraction, or industry-specific model work.

## 5. Output Layout

All Requirement 04 outputs must be written under:

```text
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/
```

Required subdirectories:

```text
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/
  cache/
  reports/
  manifests/
```

Requirement 04 must not overwrite Requirement 01, Requirement 02, Requirement 03, engineering baseline, or BaseRate outputs.

## 6. Command Surface

Minimum command surface:

```bash
uv run python ep2/scripts/run_requirement_04_holding_exit_winner_capture_extension.py --config ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml
uv run python ep2/scripts/validate_requirement_04_holding_exit_winner_capture_extension.py --config ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml
```

The runner must generate all row-level artifacts, reports, selection outputs, gates, and manifests. The validator must fail closed on missing artifacts, schema violations, frozen-input hash drift, Requirement 03 failure, split leakage, winner-state as-of violations, robustness selection leakage, invalid capture denominators, invalid diagnostic promotion, or any failed hard gate.

## 7. Frozen Config

Requirement 04 config must include these values:

```yaml
phase: requirement_04_holding_exit_winner_capture_extension
output_root: ep2/outputs/requirement_04_holding_exit_winner_capture_extension

frozen_contract:
  requirement_03_manifest: ep2/outputs/requirement_03_schedule_bridge/manifests/requirement_03_schedule_bridge_manifest.json
  expected_requirement_03_status: passed
  expected_requirement_03_next_phase_status: passed
  primary_label_id: confirm_h10_u10_d06_conservative_fail
  frozen_baseline_id: probe_with_simple_stop
  hazard_schedule_id: hazard_probe_with_simple_stop
  schedule_bridge_id: hazard_probe_confirm_add_fast_fail
  selected_threshold: 0.3205667777673395
  selected_stop_risk_ceiling: 0.27410397287415667
  probe_weight: 0.30
  full_weight_after_confirm: 1.00
  confirm_add_window: probe_plus_1_to_probe_plus_3_trading_days
  max_confirm_add_days_from_launch_execution: 10
  base_fast_fail_drawdown: 0.06
  r03_primary_H: 10

pit_price_authority:
  root: data/qlib/cn_data_pit
  required_fields: [open, high, low, close]
  optional_fields: [volume, money]
  hash_scope: r03_instruments_and_dates_through_confirm_add_plus_120_trading_days
  calendar_source: same_as_ep2_common
  price_field_schema_version: pit_qlib_ohlc_v1

schedule_matrix:
  selection_scope: validation_only
  robustness_role: holdout_gate_only
  baseline_schedule_id: R03_original_H10
  baseline_required_for_replay_and_comparison: true
  baseline_promotion_eligible: false
  promotion_eligible_primary_schedule_ids:
    - R03_confirmed_H20
    - R03_confirmed_H60
    - R03_confirmed_H120
    - R03_winner_state_hold_H120
  diagnostic_schedule_ids:
    - R03_all_H20
    - R03_all_H40
    - R03_confirmed_H40
    - R03_no_fast_fail
    - R03_relaxed_fast_fail
    - winner_state_gain_threshold_sensitivity
    - winner_state_trailing_sensitivity

holding_rules:
  unconfirmed_probe_H: 10
  confirmed_H_values: [20, 60, 120]
  winner_state_normal_hold_H: 20
  winner_state_hold_H: 120
  natural_exit: next_open_after_H_trading_days_from_clock_start
  unconfirmed_probe_clock_start: selected_probe_execution_date
  confirmed_position_clock_start: confirm_add_execution_date
  winner_state_max_hold_clock_start: confirm_add_execution_date
  blocked_exit_retry: same_as_requirement_03
  cost_model: same_as_requirement_03

winner_state:
  schedule_id: R03_winner_state_hold_H120
  signal_source: close_derived
  signal_start: confirm_add_execution_date_close
  signal_end: before_normal_hold_natural_exit
  effective_date_rule: next_trading_day_after_signal_date
  transition_price: open_on_effective_date
  min_close_return_from_first_exposure: 0.12
  max_drawdown_since_first_exposure: 0.08
  require_close_above_confirm_add_price: true
  require_no_fast_fail_state: true
  trailing_drawdown_from_post_winner_high_close: 0.15
  profit_floor_from_first_exposure_price: 1.03
  confirm_add_price_floor: true
  max_hold_H_from_confirm_add: 120

diagnostic_sensitivity:
  winner_state_gain_thresholds: [0.10, 0.15, 0.20]
  winner_state_trailing_drawdowns: [0.10, 0.20]
  relaxed_fast_fail_drawdown: 0.10
  fast_fail_saved_loss_threshold: 0.03

selection_objective:
  primary_metric: strict_big_winner_capture_rate_50h120_diff_vs_R03
  require_validation_primary_metric_improvement: true
  materiality_guard:
    strict_capture_count_margin: 1
    exposure_weighted_capture_margin: 0.01
    rule: prefer_simpler_shorter_schedule_unless_longer_schedule_exceeds_both_margins
  tie_breakers:
    - exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03
    - p05_after_cost_return_diff_vs_R03
    - mean_after_cost_return_diff_vs_R03
    - lower_exposure_day_multiple_vs_R03
    - shorter_max_hold_H

proceed_gate:
  min_validation_strict_big_winner_capture_diff_vs_R03: 0.0
  min_validation_captured_big_winner_count_delta_vs_R03: 1
  min_validation_exposure_weighted_capture_diff_vs_R03: 0.0
  min_robustness_strict_big_winner_capture_diff_vs_R03: 0.0
  min_robustness_exposure_weighted_capture_diff_vs_R03: 0.0
  min_validation_mean_after_cost_return_diff_vs_R03: -0.001
  min_robustness_mean_after_cost_return_diff_vs_R03: -0.002
  max_validation_p05_after_cost_return_deterioration_vs_R03: 0.005
  max_robustness_p05_after_cost_return_deterioration_vs_R03: 0.005
  max_validation_max_adverse_excursion_deterioration_vs_R03: 0.020
  max_robustness_max_adverse_excursion_deterioration_vs_R03: 0.020
  max_blocked_exit_retry_rate: 0.05
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  max_turnover_proxy_multiple_vs_R03: 1.25
  max_exposure_day_multiple_vs_R03: 3.0
  min_winner_state_entry_count_validation: 5
  min_winner_state_entry_count_robustness: 3
```

## 8. Schedule Rules

Requirement 04 schedule IDs are deterministic. No schedule family or parameter may be added after looking at validation or robustness results.

### 8.1 Baseline Replay

`R03_original_H10` must reproduce Requirement 03 `hazard_probe_confirm_add_fast_fail` action and exposure semantics:

```yaml
R03_original_H10:
  probe: same_as_requirement_03
  confirm_add: same_as_requirement_03
  fast_fail: same_as_requirement_03
  natural_exit_H: 10
  role: baseline_and_comparison
```

The implementation may read Requirement 03 row-level artifacts or replay the schedule, but replayed outputs must be schema-compatible and metric-compatible with Requirement 03.

Requirement 04 must write a baseline reconciliation audit row for `R03_original_H10`. Validation and robustness must satisfy:

```text
episode_count exactly equals Requirement 03
episode_with_any_exposure_count exactly equals Requirement 03
probe_rate exactly equals Requirement 03 within 1e-12
confirm_add_rate exactly equals Requirement 03 within 1e-12
mean_after_cost_return equals Requirement 03 within 1e-10
p05_after_cost_return equals Requirement 03 within 1e-10
strict_big_winner_capture_rate_50h120 equals Requirement 03 within 1e-12
```

If the reconciliation fails, Requirement 04 status is `failed_contract_or_leakage`; no holding variant may be selected.

### 8.2 Confirmed Holding Extension

Confirmed schedules extend only full confirmed exposure:

```yaml
R03_confirmed_H20:
  if confirm_add_executed: natural_exit_H = 20 from confirm_add_execution_date
  else: natural_exit_H = 10 from selected_probe_execution_date

R03_confirmed_H60:
  if confirm_add_executed: natural_exit_H = 60 from confirm_add_execution_date
  else: natural_exit_H = 10 from selected_probe_execution_date

R03_confirmed_H120:
  if confirm_add_executed: natural_exit_H = 120 from confirm_add_execution_date
  else: natural_exit_H = 10 from selected_probe_execution_date
```

Rules:

- probe entry date, probe weight, confirm-add date, confirm-add weight, and first exposure price are inherited from Requirement 03;
- no new probe or confirm-add candidate may be selected;
- unconfirmed probe episodes must not be extended beyond H10;
- confirmed holding clocks start from `confirm_add_execution_date`, not from the initial probe;
- unconfirmed probe holding clocks start from `selected_probe_execution_date`;
- base fast-fail remains active until the episode exits;
- blocked-exit retry and cost accounting are identical to Requirement 03;
- natural exit is evaluated as next open after `H` trading days from the schedule-specific clock start.

### 8.3 Winner-State Hold

`R03_winner_state_hold_H120` separates normal confirmed holding from observable winner holding:

```yaml
normal_hold:
  applies_to: confirm_add_executed episodes
  natural_exit_H: 20 from confirm_add_execution_date

winner_state_entry:
  signal_date: close-derived date
  effective_date: next_trading_day(signal_date)
  transition_price: open[effective_date]
  conditions:
    - confirm_add_executed = true
    - close_return_from_first_exposure >= 0.12
    - max_drawdown_since_first_exposure <= 0.08
    - close[signal_date] > confirm_add_price
    - fast_fail_state_has_occurred = false

winner_state_exit:
  max_hold_H_from_confirm_add: 120
  exit_next_open_if_any:
    - drawdown_from_post_winner_high_close >= 0.15
    - close < first_exposure_price * 1.03
    - close < confirm_add_price
    - H120 natural exit reached
```

Winner-state is a position-state transition, not a new buy signal. It cannot increase target weight above `1.00`.

### 8.4 Winner-State As-Of Contract

For every winner-state transition, the runner must materialize:

```text
winner_state_signal_date
winner_state_effective_date
winner_state_transition_price
winner_state_feature_max_date
winner_state_signal_source
winner_state_no_lookahead_passed
```

The following are forbidden:

- same-close transition;
- using `winner_state_effective_date` high, low, close, volume, money, or return as a signal feature;
- using any date after `winner_state_signal_date` as a state feature;
- using future target labels, first +50% target date, first +100% target date, or post-exit returns as state inputs;
- using robustness rows to modify winner-state thresholds.

## 9. Diagnostic-Only Counterfactuals

Diagnostic schedules explain mechanisms. They cannot become the promoted schedule and cannot set `next_phase_proceed_status = passed`.

Required diagnostic schedules:

```yaml
R03_all_H20:
  for any episode with executed R03 exposure, set natural_exit_H = 20 from first_exposure_date
  probe and confirm_add dates unchanged
  fast-fail unchanged

R03_all_H40:
  for any episode with executed R03 exposure, set natural_exit_H = 40 from first_exposure_date
  probe and confirm_add dates unchanged
  fast-fail unchanged

R03_confirmed_H40:
  if confirm_add_executed, set natural_exit_H = 40 from confirm_add_execution_date
  else keep natural_exit_H = 10 from selected_probe_execution_date
  probe and confirm_add dates unchanged
  fast-fail unchanged

R03_no_fast_fail:
  disable base fast-fail

R03_relaxed_fast_fail:
  use fast_fail_drawdown = 0.10

winner_state_gain_threshold_sensitivity:
  run winner-state with gain thresholds [0.10, 0.15, 0.20]
  emit one diagnostic variant per threshold

winner_state_trailing_sensitivity:
  run winner-state with trailing drawdowns [0.10, 0.20]
  emit one diagnostic variant per trailing drawdown
```

Diagnostic outputs must be reported separately. A diagnostic schedule may inform later research, but it must not be selected as the Requirement 04 promoted schedule.

Partial-exit schedules such as `half_exit_at_10d_keep_half_to_H40` and `half_exit_after_15pct_gain_keep_half_trailing` are explicitly deferred to a later requirement. They are not required Requirement 04 diagnostics because their weight-transition, trailing, floor, and blocked-exit rules are not part of this frozen contract.

## 10. Big-Winner Capture Definitions

Requirement 04 must report strict, exposure-weighted, and partial capture. The target source and first target date logic must match the existing EP2 big-winner capture logic used by Requirements 02 and 03.

For each big-winner episode:

```text
first_50pct_target_date =
  first date where the frozen 50h120 big-winner target is reached

exposure_weight_at_first_50pct_target_date =
  target-day open-effective schedule exposure weight on first_50pct_target_date
```

Target-day open-effective exposure is defined as the position weight after all open-executed actions scheduled before the first target observation on `first_50pct_target_date`. Exits or entries whose signal is generated from the same day's high, low, close, return, volume, or money cannot change the target-day capture state. If a natural exit was already scheduled for the target-date open, the target-day exposure after that open exit is the capture weight. This prevents same-day target information from creating optimistic capture.

Definitions:

```text
strict_capture =
  exposure_weight_at_first_50pct_target_date > 0

exposure_weighted_capture =
  sum(exposure_weight_at_first_50pct_target_date for big-winner episodes)
  / big_winner_episode_count

partial_capture =
  had positive exposure before first_50pct_target_date
  even if fully exited before first_50pct_target_date
```

Required metrics:

```text
strict_big_winner_capture_rate_50h120
exposure_weighted_big_winner_capture_rate_50h120
partial_capture_rate_50h120
captured_big_winner_count_50h120
partial_captured_big_winner_count_50h120
big_winner_episode_count_50h120
strict_big_winner_capture_rate_100h240_sensitivity
```

`strict_big_winner_capture_rate_100h240_sensitivity` must use first target dates from the frozen EP2 path label panel. If an implementation recomputes 100h240 target dates from PIT prices instead of reading the frozen target fields, the PIT hash scope must extend through `launch_effective_date + 240` trading days and the manifest must record that expanded scope. The default Requirement 04 implementation should not recompute 100h240 targets.

`partial_capture` is diagnostic. It must not replace strict capture as the primary proceed gate.

These metrics separate:

- big winners never entered by EP2;
- big winners entered but exited before target;
- big winners held through target with small or full weight.

## 11. Required Outputs

Required row-level outputs:

```text
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/cache/requirement_04_schedule_action_panel.parquet
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/cache/requirement_04_exposure_daily_panel.parquet
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/cache/requirement_04_episode_schedule_summary.parquet
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/cache/requirement_04_winner_state_event_panel.parquet
```

Action and exposure schemas must be compatible with Requirement 03. Any added columns must be optional extensions, not incompatible replacements.

`requirement_04_episode_schedule_summary.parquet` minimum fields:

```text
schedule_id
variant_id
schedule_role
split
launch_episode_id
instrument
launch_effective_date
selected_probe_signal_date
selected_probe_execution_date
confirm_add_signal_date
confirm_add_execution_date
probe_executed
confirm_add_executed
winner_state_entered
winner_state_signal_date
winner_state_effective_date
winner_state_transition_price
first_exposure_date
first_exposure_price
confirm_add_price
exit_date
exit_reason
exit_target_weight_after
natural_exit_clock_start_date
natural_exit_H
fast_fail_exit
trailing_exit
profit_floor_exit
blocked_exit_retry_count
after_cost_return
max_adverse_excursion
max_favorable_excursion
missed_gain_to_exposure
turnover
strict_capture_50h120
partial_capture_50h120
exposure_weight_at_first_50pct_target_date
selection_eligible
selection_status
price_data_status
```

`requirement_04_winner_state_event_panel.parquet` minimum fields:

```text
schedule_id
variant_id
split
launch_episode_id
instrument
signal_date
effective_date
transition_price
close_return_from_first_exposure
max_drawdown_since_first_exposure
close_above_confirm_add_price
fast_fail_state_has_occurred
winner_state_signal_passed
winner_state_entered
feature_max_date
asof_passed
no_same_close_transition_passed
```

Required reports:

```text
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_schedule_results.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_schedule_comparison.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_selected_schedule.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_big_winner_capture_audit.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_fast_fail_value_audit.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_winner_state_asof_audit.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_diagnostic_counterfactuals.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_gate_audit.csv
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_artifact_authority.csv
```

## 12. Report Schemas

`requirement_04_schedule_results.csv` minimum fields:

```text
schedule_id
variant_id
schedule_role
split
episode_count
episode_with_any_exposure_count
probe_rate
confirm_add_rate
winner_hold_mode_entry_rate
winner_hold_mode_entry_count
fast_fail_exit_rate
trailing_exit_rate
profit_floor_exit_rate
natural_exit_rate
blocked_exit_retry_rate
mean_after_cost_return
median_after_cost_return
p05_after_cost_return
p95_after_cost_return
max_adverse_excursion_mean
max_adverse_excursion_p95
max_favorable_excursion_mean
mean_holding_days
median_holding_days
mean_exposure_days
median_exposure_days
capital_occupancy_proxy
turnover_proxy
strict_big_winner_capture_rate_50h120
exposure_weighted_big_winner_capture_rate_50h120
partial_capture_rate_50h120
captured_big_winner_count_50h120
big_winner_episode_count_50h120
strict_big_winner_capture_rate_100h240_sensitivity
top1_instrument_year_exposure_share
top5_instrument_exposure_share
```

Exposure-day and capital-occupancy definitions:

```text
daily_exposure_weight =
  end-of-day target exposure weight after all valid open-executed actions for the date

exposure_days =
  count trading days where daily_exposure_weight > 0

weighted_exposure_days =
  sum daily_exposure_weight over the episode schedule path

mean_exposure_days =
  mean exposure_days across episodes in the split

median_exposure_days =
  median exposure_days across episodes in the split

capital_occupancy_proxy =
  mean weighted_exposure_days across episodes in the split

exposure_day_multiple_vs_R03 =
  capital_occupancy_proxy(schedule) / capital_occupancy_proxy(R03_original_H10)
```

If `capital_occupancy_proxy(R03_original_H10) = 0`, the split is invalid and Requirement 04 must fail with `failed_contract_or_leakage`.

`requirement_04_schedule_comparison.csv` minimum fields:

```text
split
schedule_id
variant_id
comparison_schedule_id
schedule_role
mean_after_cost_return_diff
median_after_cost_return_diff
p05_after_cost_return_diff
max_adverse_excursion_mean_diff
turnover_proxy_diff
turnover_proxy_multiple
exposure_day_multiple_vs_R03
capital_occupancy_proxy_diff
strict_big_winner_capture_rate_50h120_diff
exposure_weighted_big_winner_capture_rate_50h120_diff
partial_capture_rate_50h120_diff
captured_big_winner_count_50h120_diff
winner_hold_mode_entry_rate_diff
fast_fail_exit_rate_diff
blocked_exit_retry_rate_diff
```

`requirement_04_selected_schedule.csv` minimum fields:

```text
selected_schedule_id
selected_variant_id
selection_split
selection_status
selected_from_primary_matrix
validation_objective_rank
validation_strict_big_winner_capture_rate_50h120_diff_vs_R03
validation_exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03
validation_p05_after_cost_return_diff_vs_R03
validation_mean_after_cost_return_diff_vs_R03
validation_exposure_day_multiple_vs_R03
materiality_guard_applied
winner_state_min_support_pass
robustness_gate_status
next_phase_proceed_status
recommendation
```

`requirement_04_big_winner_capture_audit.csv` minimum fields:

```text
schedule_id
variant_id
split
launch_episode_id
instrument
first_50pct_target_date
first_100pct_target_date
big_winner_50h120
big_winner_100h240
had_positive_exposure_before_first_50pct_target_date
exposure_weight_at_first_50pct_target_date
target_day_open_exit_applied
target_day_capture_timing_status
strict_capture_50h120
partial_capture_50h120
exit_date
exit_before_first_50pct_target
exit_reason
```

`requirement_04_fast_fail_value_audit.csv` minimum fields:

```text
schedule_id
variant_id
counterfactual_id
counterfactual_variant_id
split
big_winner_capture_delta
exposure_weighted_capture_delta
partial_capture_delta
mean_return_delta
p05_return_delta
max_adverse_excursion_delta
fast_fail_saved_loss_count
fast_fail_false_exit_winner_count
fast_fail_false_exit_big_winner_count
fast_fail_false_exit_partial_capture_count
```

`fast_fail_false_exit_big_winner_count` and `fast_fail_false_exit_partial_capture_count` are hindsight diagnostics only. They must not be used as schedule features, winner-state inputs, threshold-selection inputs, or promoted-schedule selection criteria.

Fast-fail audit definitions:

```text
base_schedule =
  the same schedule with Requirement 03 base fast-fail enabled

counterfactual_schedule =
  matching diagnostic schedule with fast-fail disabled or relaxed

fast_fail_saved_loss =
  base_schedule exits through fast-fail
  and counterfactual_schedule after_cost_return - base_schedule after_cost_return <= -0.03

fast_fail_false_exit_winner =
  base_schedule exits through fast-fail
  and counterfactual_schedule strict_capture_50h120 = true

fast_fail_false_exit_big_winner =
  base_schedule exits through fast-fail before first_50pct_target_date
  and the episode is a frozen 50h120 big-winner episode
  and counterfactual_schedule strict_capture_50h120 = true

fast_fail_false_exit_partial_capture =
  base_schedule exits through fast-fail
  and counterfactual_schedule partial_capture_50h120 = true
```

The saved-loss threshold `0.03` must come from config as `fast_fail_saved_loss_threshold`. These counts are episode-deduped by `launch_episode_id` and computed separately for train, validation, and robustness.

`requirement_04_winner_state_asof_audit.csv` minimum fields:

```text
schedule_id
variant_id
split
launch_episode_id
instrument
winner_state_signal_date
winner_state_effective_date
winner_state_feature_max_date
winner_state_transition_price_date
same_close_transition_used
effective_date_high_low_close_used_as_signal
future_target_label_used_as_signal
asof_passed
detail
```

`requirement_04_diagnostic_counterfactuals.csv` minimum fields:

```text
schedule_id
variant_id
diagnostic_family
parameter_name
parameter_value
split
metric_name
metric_value
diff_vs_R03
eligible_for_selection
diagnostic_interpretation
```

For every row in this report, `eligible_for_selection` must be `false`.

`requirement_04_gate_audit.csv` must include explicit rows for baseline replay reconciliation:

```text
r03_replay_episode_count_match
r03_replay_exposed_count_match
r03_replay_probe_rate_match
r03_replay_confirm_add_rate_match
r03_replay_mean_after_cost_return_match
r03_replay_p05_after_cost_return_match
r03_replay_strict_big_winner_capture_match
baseline_schedule_not_promotion_eligible
exposure_weighted_capture_non_deterioration
exposure_day_multiple_gate
winner_state_min_support_pass
selection_materiality_guard_applied
```

## 13. Selection Rule

Promoted schedule selection is validation-only and may select only from:

```text
R03_confirmed_H20
R03_confirmed_H60
R03_confirmed_H120
R03_winner_state_hold_H120
```

`R03_original_H10` is baseline-only. It is required for replay and comparison, but `promotion_eligible = false` and it must not be selected as the promoted schedule. Diagnostics must not be selected.

A schedule is validation-passing only if it satisfies all validation gates in section 14. Among validation-passing schedules, select the schedule with the best:

```text
strict_big_winner_capture_rate_50h120_diff_vs_R03
```

Before tie breakers are applied, the complexity materiality guard must be enforced:

```text
For each candidate schedule, compare it against the best validation-passing simpler schedule
according to the same selection objective.

If the longer or more complex candidate beats that simpler schedule by
  <= 1 captured big-winner episode
and
  <= 0.01 exposure-weighted capture rate,
then prefer the simpler shorter schedule.
```

If there is no validation-passing simpler schedule, the candidate is not blocked by the materiality guard. The guard is evaluated before the ordinary tie breakers and must be recorded in `requirement_04_selected_schedule.csv`.

Complexity order, from simplest to most complex:

```text
R03_confirmed_H20
R03_confirmed_H60
R03_confirmed_H120
R03_winner_state_hold_H120
```

Tie breakers, after applying the materiality guard, in order:

1. higher `exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03`;
2. higher `p05_after_cost_return_diff_vs_R03`;
3. higher `mean_after_cost_return_diff_vs_R03`;
4. lower `exposure_day_multiple_vs_R03`;
5. shorter `max_hold_H`;
6. deterministic lexicographic `schedule_id`.

Robustness rows must not affect schedule selection. Robustness is evaluated only after a validation-selected schedule is fixed.

If no validation schedule passes all validation gates, write complete diagnostic artifacts and set:

```text
validation_status: failed_schedule_extension
next_phase_proceed_status: failed_schedule_extension
recommendation: keep_EP2_as_short_horizon_event_sleeve
```

## 14. Proceed Gates

Requirement 04 passes only if the selected primary schedule satisfies all contract, validation, and robustness gates.

Validation gates:

1. selected schedule comes from `promotion_eligible_primary_schedule_ids`;
2. `strict_big_winner_capture_rate_50h120_diff_vs_R03 > 0`;
3. `captured_big_winner_count_50h120_diff_vs_R03 >= 1`;
4. `exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03 >= 0`;
5. `mean_after_cost_return_diff_vs_R03 >= -0.001`;
6. `p05_after_cost_return` deteriorates by no more than `0.005` vs R03;
7. `max_adverse_excursion_mean` deteriorates by no more than `0.020` vs R03;
8. `blocked_exit_retry_rate <= 0.05`;
9. `turnover_proxy_multiple_vs_R03 <= 1.25`;
10. `exposure_day_multiple_vs_R03 <= 3.0`;
11. `top1_instrument_year_exposure_share <= 0.10`;
12. `top5_instrument_exposure_share <= 0.35`;
13. all winner-state as-of audit rows pass for any schedule using winner-state;
14. if selected schedule is `R03_winner_state_hold_H120`, `winner_hold_mode_entry_count >= 5` and `winner_hold_mode_entry_rate > 0`.

Robustness holdout gates:

1. selected schedule is evaluated without changing any parameter;
2. `strict_big_winner_capture_rate_50h120_diff_vs_R03 >= 0`;
3. `exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03 >= 0`;
4. `mean_after_cost_return_diff_vs_R03 >= -0.002`;
5. `p05_after_cost_return` deteriorates by no more than `0.005` vs R03;
6. `max_adverse_excursion_mean` deteriorates by no more than `0.020` vs R03;
7. `blocked_exit_retry_rate <= 0.05`;
8. `turnover_proxy_multiple_vs_R03 <= 1.25`;
9. `exposure_day_multiple_vs_R03 <= 3.0`;
10. concentration gates pass;
11. all winner-state as-of audit rows pass for any schedule using winner-state;
12. if selected schedule is `R03_winner_state_hold_H120`, `winner_hold_mode_entry_count >= 3` and `winner_hold_mode_entry_rate > 0`.

Failure precedence is fixed:

1. frozen-contract, input, schema, split, or as-of violation returns `failed_contract_or_leakage`;
2. if no promotion-eligible schedule improves validation strict capture and captured big-winner count, return `failed_winner_capture`;
3. if at least one promotion-eligible schedule improves validation strict capture and captured big-winner count, but all such schedules fail validation tail-risk, turnover, occupancy, blocked-exit, concentration, exposure-weighted-capture, or winner-state-support gates, return `failed_tail_risk`;
4. if at least one schedule passes validation gates but no schedule remains after applying the materiality guard, return `failed_schedule_extension`;
5. selected schedule passes validation but fails robustness holdout returns `failed_robustness_holdout`;
6. only if all gates pass may status be `passed`.

Passing Requirement 04 permits Requirement 05 BaseRate integration / attribution. It does not permit P1 strategy validation or strategy freeze.

## 15. Recommendation Enum

The manifest must include both gate status and recommendation. Recommendation is interpretive and must not replace hard gate status.

Allowed recommendations:

```text
proceed_to_R05_baserate_integration
keep_EP2_as_short_horizon_event_sleeve
reframe_EP2_as_risk_filter_overlay
stop_big_winner_holding_extension
```

Recommended mapping:

```text
passed:
  recommendation = proceed_to_R05_baserate_integration

failed_schedule_extension:
  recommendation = keep_EP2_as_short_horizon_event_sleeve

failed_winner_capture:
  recommendation = stop_big_winner_holding_extension

failed_tail_risk:
  recommendation = reframe_EP2_as_risk_filter_overlay

failed_robustness_holdout:
  recommendation = keep_EP2_as_short_horizon_event_sleeve
```

Requirement 04 must explicitly forbid these recommendations or actions:

```text
proceed_to_P1_strategy
freeze_strategy
full_portfolio_backtest
change_R02_threshold
change_primary_label
```

## 16. Stop Rules

Stop and do not proceed if any of the following happens:

1. Requirement 03 no longer passes;
2. Requirement 03 selected threshold differs from `0.3205667777673395`;
3. Requirement 03 selected stop-risk ceiling differs from `0.27410397287415667`;
4. primary label changes from `confirm_h10_u10_d06_conservative_fail`;
5. Requirement 03 probe or confirm-add entry rules are changed;
6. BaseRate row-level data is used for Requirement 04 schedule selection;
7. winner-state uses same-close transition;
8. winner-state uses effective-date high, low, close, or future data as a signal feature;
9. future target labels are used as state inputs;
10. robustness rows are used for schedule or parameter selection;
11. diagnostic-only schedules are promoted;
12. the result requires relabeling, threshold reselection, feature expansion, or launch-pool changes to pass.

## 17. Required Artifact Authority

Requirement 04 must output:

```text
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/manifests/requirement_04_holding_exit_manifest.json
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_artifact_authority.csv
```

`requirement_04_holding_exit_manifest.json` minimum fields:

```text
phase
validation_status
next_phase_proceed_status
recommendation
generated_at
requirement_03_manifest_hash
requirement_02_manifest_hash
engineering_baseline_manifest_hash
pit_price_source_hash
pit_calendar_hash
pit_price_field_schema_version
pit_price_hash_scope
primary_label_id
frozen_baseline_id
hazard_schedule_id
schedule_bridge_id
selected_threshold
selected_stop_risk_ceiling
selected_requirement_04_schedule_id
selected_schedule_role
winner_state_enabled
schedule_action_panel_hash
exposure_daily_panel_hash
episode_schedule_summary_hash
winner_state_event_panel_hash
schedule_results_hash
schedule_comparison_hash
selected_schedule_hash
big_winner_capture_audit_hash
fast_fail_value_audit_hash
winner_state_asof_audit_hash
diagnostic_counterfactuals_hash
gate_audit_hash
artifact_authority_hash
```

`requirement_04_artifact_authority.csv` minimum fields:

```text
artifact_name
artifact_path
authority_role
producer_command
schema_version
required_for_requirement
row_count
content_hash
```

## 18. Validation Checklist

`validate_requirement_04_holding_exit_winner_capture_extension.py` must verify:

- Requirement 03 manifest exists and has `next_phase_proceed_status = passed`;
- Requirement 03 selected threshold and stop-risk ceiling match the frozen config;
- Requirement 03 gate counts are derived from `requirement_03_gate_audit.csv` and equal `gate_count = 17`, `passed_gate_count = 17`, `failed_gate_count = 0`;
- all required artifacts exist;
- PIT price source hash, calendar hash, field schema version, and hash scope are present and match the generated artifacts;
- row-level action and exposure schemas are compatible with Requirement 03;
- no Requirement 01 / 02 / 03 / engineering baseline / BaseRate artifacts are overwritten;
- no episode crosses split boundaries;
- validation-only selection is enforced;
- robustness is not used for schedule selection or tie-breaking;
- primary matrix schedules and diagnostic schedules match config exactly;
- diagnostic sensitivity family rows have unique `variant_id`, `parameter_name`, and `parameter_value`;
- `R03_original_H10` is baseline-only and never promotion-eligible;
- diagnostic schedules are never promoted;
- selection materiality guard is applied before tie breakers;
- R03 probe and confirm-add dates are unchanged;
- `R03_original_H10` replay reconciliation gates all pass against Requirement 03 validation and robustness reports;
- unconfirmed probe episodes remain H10 in confirmed-extension schedules;
- confirmed-extension natural-exit clocks start from `confirm_add_execution_date`;
- unconfirmed probe natural-exit clocks start from `selected_probe_execution_date`;
- winner-state signal features use only data `<= winner_state_signal_date`;
- winner-state effective date is the next trading day after signal date;
- same-close transition is absent;
- effective-date high, low, close, return, volume, or money is not used as a signal feature;
- future target labels are not used as winner-state inputs;
- strict, exposure-weighted, and partial big-winner capture use the correct big-winner episode denominator;
- 100h240 sensitivity target dates come from the frozen EP2 path label panel unless PIT hash scope is expanded through launch + 240 trading days;
- exposure-weighted big-winner capture does not deteriorate on validation or robustness;
- exposure-day multiple and capital occupancy fields are present and use the R03 baseline denominator;
- exposure-day and capital-occupancy metrics follow the section 12 mechanical definitions;
- `partial_capture` does not replace strict capture in hard gates;
- winner-state selected schedules satisfy the configured minimum validation and robustness support counts;
- `fast_fail_false_exit_big_winner_count` and `fast_fail_false_exit_partial_capture_count` are reported only as hindsight diagnostics;
- `fast_fail_saved_loss_count`, `fast_fail_false_exit_winner_count`, `fast_fail_false_exit_big_winner_count`, and `fast_fail_false_exit_partial_capture_count` follow the mechanical definitions in section 12;
- fast-fail diagnostic counterfactuals cannot become selected schedules;
- selected schedule satisfies all validation gates;
- selected schedule satisfies all robustness gates without parameter changes;
- failure status precedence is enforced;
- recommendation enum is valid and does not imply P1 strategy, strategy freeze, full portfolio backtest, R02 threshold change, or primary-label change;
- manifest hashes match current artifacts.

## 19. Test Plan

Run prerequisite validation:

```bash
uv run python ep2/scripts/validate_requirement_01_label_and_baseline_freeze.py
uv run python ep2/scripts/validate_requirement_02_hazard_timing_model.py --config ep2/configs/requirement_02_hazard_timing_model.yaml
uv run python ep2/scripts/validate_requirement_03_schedule_bridge.py --config ep2/configs/requirement_03_schedule_bridge.yaml
```

Run Requirement 04:

```bash
uv run python ep2/scripts/run_requirement_04_holding_exit_winner_capture_extension.py --config ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml
uv run python ep2/scripts/validate_requirement_04_holding_exit_winner_capture_extension.py --config ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml
```

Compile checks:

```bash
uv run python -m py_compile \
  ep2/scripts/requirement_04_holding_exit_winner_capture_extension_common.py \
  ep2/scripts/run_requirement_04_holding_exit_winner_capture_extension.py \
  ep2/scripts/validate_requirement_04_holding_exit_winner_capture_extension.py
```

Inspect final artifacts:

- manifest status and recommendation;
- selected schedule and validation-only selection audit;
- strict / exposure-weighted / partial big-winner capture;
- p05 and max adverse excursion deterioration;
- fast-fail value audit;
- winner-state as-of audit;
- diagnostic-only counterfactuals;
- gate audit failure precedence.

Give a final Requirement 05 go/no-go judgment from `next_phase_proceed_status` and `recommendation`.
