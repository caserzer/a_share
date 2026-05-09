# EP2 Requirement 03: Schedule Bridge and BaseRate-Overlap Audit

## 1. Purpose

Requirement 03 implements the EP2-4 bridge after the passed Requirement 02 hazard timing model.

This phase answers one narrow question:

> Can the frozen Requirement 02 hazard probe be assembled into a deterministic low-turnover probe / confirm-add / fast-fail exposure schedule, and does that schedule expose a differentiated event opportunity set relative to the BaseRate daily TopK anchor?

Requirement 03 is a schedule-and-overlap bridge. It is not a full EP2 strategy, not a new label search, and not a portfolio-level claim that EP2 beats BaseRate annual return or drawdown.

## 2. Entry Gate

Requirement 03 may start only after Requirement 02 passes:

```bash
uv run python ep2/scripts/validate_requirement_02_hazard_timing_model.py --config ep2/configs/requirement_02_hazard_timing_model.yaml
```

Required Requirement 02 state:

```yaml
phase: requirement_02_hazard_timing_model
validation_status: passed
requirement_03_proceed_status: passed
primary_label_id: confirm_h10_u10_d06_conservative_fail
frozen_baseline_id: probe_with_simple_stop
selected_threshold: 0.3205667777673395
selected_stop_risk_ceiling: 0.27410397287415667
```

Requirement 02 gate counts are not required to be stored in the manifest. They must be derived from:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_gate_audit.csv
```

Required derived gate state:

```yaml
gate_count: 27
passed_gate_count: 27
failed_gate_count: 0
```

The Requirement 02 evidence that unlocks Requirement 03 is:

| Split | mean after-cost diff vs `probe_with_simple_stop` | turnover reduction vs daily BaseRate | probe rate | big-winner coverage loss | status |
| --- | ---: | ---: | ---: | ---: | --- |
| validation | `0.005353` | `0.940514` | `0.195489` | `0.000000` | passed |
| robustness | `0.005210` | `0.941117` | `0.193506` | `0.000000` | passed |

If Requirement 02 no longer passes, stop. Do not patch Requirement 03 to work around a failed hazard timing contract.

## 3. Frozen Inputs

Requirement 03 may read only these input roots:

```text
ep2/engineering_baseline/outputs/
ep2/outputs/requirement_01_label_and_baseline_freeze/
ep2/outputs/requirement_02_hazard_timing_model/
BaseRate/outputs/alpha158_lgbm_oos/
```

Minimum required EP2 inputs:

```text
ep2/outputs/requirement_02_hazard_timing_model/manifests/requirement_02_hazard_manifest.json
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_hazard_training_panel.parquet
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_hazard_prediction_panel.parquet
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_episode_primary_probe.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_schedule_results.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_baseline_comparison.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_gate_audit.csv
ep2/engineering_baseline/outputs/cache/ep2_candidate_probe_grid.parquet
ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv
ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json
```

Minimum required BaseRate audit inputs:

```text
BaseRate/outputs/alpha158_lgbm_oos/reports/base_rate_run_manifest.json
BaseRate/outputs/alpha158_lgbm_oos/cache/prediction_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/order_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/trade_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/reports/base_rate_topk_sensitivity.csv
BaseRate/outputs/alpha158_lgbm_oos/reports/base_rate_trade_summary_by_fold.csv
```

BaseRate row-level inputs are audit-only in Requirement 03. They must not affect EP2 launch pool selection, label selection, hazard feature construction, selected threshold, stop-risk ceiling, probe date selection, confirm-add rule, or any schedule choice.

Forbidden inputs:

- Explore9 / Explore10 row-level outputs or caches;
- raw full-market daily TopK data outside the frozen BaseRate output root;
- any new provider pull to create features, labels, or schedules;
- any new model training, feature search, or threshold search;
- Requirement 02 robustness rows for changing the selected hazard threshold;
- BaseRate portfolio returns as a direct pass/fail comparison against EP2 schedule-only returns.

## 4. Non-Goals

This phase does not do:

- train or refit a hazard model;
- select a new hazard threshold;
- change the primary label;
- change the frozen launch pool;
- tune confirm-add delay or weight from validation / robustness outcomes;
- build a complete holding / exit system;
- compare EP2 and BaseRate annual return / max drawdown as portfolio strategies;
- explain BaseRate losses with EP2 fast-fail exits;
- decide whether BaseRate and EP2 should be combined in one portfolio;
- perform leaf rule extraction or path-to-primitive translation.

The two deferred BaseRate attribution questions are explicitly out of scope:

1. whether EP2 fast-fail explains BaseRate losing trades;
2. whether EP2 duplicates, conflicts with, or should add to BaseRate existing positions.

## 5. Output Layout

All Requirement 03 outputs must be written under:

```text
ep2/outputs/requirement_03_schedule_bridge/
```

Required subdirectories:

```text
ep2/outputs/requirement_03_schedule_bridge/
  cache/
  reports/
  manifests/
```

Requirement 03 must not overwrite Requirement 01, Requirement 02, engineering baseline, or BaseRate outputs.

## 6. Command Surface

Minimum command surface:

```bash
uv run python ep2/scripts/run_requirement_03_schedule_bridge.py --config ep2/configs/requirement_03_schedule_bridge.yaml
uv run python ep2/scripts/validate_requirement_03_schedule_bridge.py --config ep2/configs/requirement_03_schedule_bridge.yaml
```

The runner must generate all row-level artifacts, reports, and manifests. The validator must fail closed on missing artifacts, schema violations, frozen-input hash drift, Requirement 02 failure, BaseRate audit leakage, schedule incompatibility, or proceed-gate failure.

## 7. Frozen Config

Requirement 03 config must include these values:

```yaml
phase: requirement_03_schedule_bridge
output_root: ep2/outputs/requirement_03_schedule_bridge

frozen_contract:
  requirement_02_manifest: ep2/outputs/requirement_02_hazard_timing_model/manifests/requirement_02_hazard_manifest.json
  expected_requirement_02_status: passed
  primary_label_id: confirm_h10_u10_d06_conservative_fail
  frozen_baseline_id: probe_with_simple_stop
  hazard_schedule_id: hazard_probe_with_simple_stop
  selected_threshold: 0.3205667777673395
  selected_stop_risk_ceiling: 0.27410397287415667

schedule_bridge:
  schedule_id: hazard_probe_confirm_add_fast_fail
  probe_weight: 0.30
  confirm_add_weight: 0.70
  full_weight_after_confirm: 1.00
  confirm_add_enabled: true
  confirm_add_rule: first_valid_confirm_candidate_in_window_after_probe
  confirm_add_search_start_offset_trading_days: 1
  confirm_add_search_end_offset_trading_days: 3
  max_confirm_add_days_from_launch_execution: 10
  max_missed_gain_to_confirm: 0.08
  fast_fail_drawdown: 0.06
  natural_exit: next_open_after_H_trading_days
  primary_H: 10
  blocked_exit_retry: same_as_engineering_baseline
  cost_model: same_as_engineering_baseline
  counterfactual_schedules:
    - hazard_probe_with_simple_stop_replay
    - hazard_probe_confirm_add_no_fast_fail

baserate_bridge:
  base_rate_root: BaseRate/outputs/alpha158_lgbm_oos
  primary_portfolio_id: topk_50_dropout_5_daily
  primary_label_name: LABEL_1D_Q
  primary_cost_scenario: base
  topk_hit_k: 50
  high_score_quantile: 0.80
  same_day_match_policy: signal_date_to_base_rate_signal_date
  next_open_match_policy: ep2_execution_date_to_base_rate_trade_date
  order_filter:
    side: buy
    blocked: false
  trade_filter:
    side: buy
    filled: true

proceed_gate:
  min_validation_mean_after_cost_return_diff_vs_requirement_02: 0.0
  min_robustness_mean_after_cost_return_diff_vs_requirement_02: -0.001
  max_big_winner_coverage_loss_vs_requirement_02: 0.10
  max_missed_gain_to_exposure_median: 0.08
  min_turnover_reduction_vs_daily_baserate: 0.50
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  min_baserate_overlap_report_coverage: 0.95
  min_uncovered_ep2_exposure_share: 0.20
  baserate_overlap_coverage_scope: validation_and_robustness_only
  baserate_overlap_coverage_unit: action_level_ep2_exposure_event
```

## 8. Schedule Bridge Rule

Requirement 03 schedule id:

```text
hazard_probe_confirm_add_fast_fail
```

The schedule starts from the frozen Requirement 02 selected probe:

```text
selected_probe_signal_date
selected_probe_execution_date
selected_threshold
selected_stop_risk_ceiling
```

Probe entry rule:

```yaml
probe_entry:
  execution_date: selected_probe_execution_date
  target_weight_after: 0.30
  if_no_requirement_02_probe: no_exposure
```

Confirm-add rule:

```yaml
confirm_add:
  candidate_search_start: selected_probe_execution_date + 1 trading day
  candidate_search_end: min(selected_probe_execution_date + 3 trading days, launch_effective_date + 10 trading days)
  select: earliest candidate row satisfying all valid_if conditions
  valid_if:
    - candidate belongs to the same launch_episode_id
    - is_valid_probe_candidate = true
    - score_probe_day >= selected_threshold
    - P_stop_first <= selected_stop_risk_ceiling
    - pre_probe_fast_fail_from_launch_reference = false
    - missed_gain_to_probe <= 0.08
    - buy is executable next open
    - no fast_fail_exit has already occurred
  action:
    action_type: confirm_add
    target_weight_after: 1.00
  if_none: keep_probe_weight_until_fast_fail_or_natural_exit
```

The confirm-add rule is a bounded search window, not an exact-day rule. `confirm_add_search_start_offset_trading_days = 1` and `confirm_add_search_end_offset_trading_days = 3` mean the implementation must examine candidate rows from `probe + 1` through `probe + 3` trading days, then choose the earliest valid row. It must not skip an earlier valid row to wait for the third day.

Fast-fail and natural exit inherit the engineering baseline mechanics:

```yaml
fast_fail_exit:
  enabled: true
  drawdown_from_first_exposure_price: -0.06
  target_weight_after: 0.00

natural_exit:
  date_rule: next_open_after_H_trading_days
  H: 10
  target_weight_after: 0.00

blocked_exit_retry:
  same_as_engineering_baseline: true
```

This phase must also preserve a Requirement 02 comparable schedule:

```text
hazard_probe_with_simple_stop
```

The comparable schedule can be read from Requirement 02 reports or replayed, but any replay must be byte/schema-compatible with Requirement 02 action and exposure semantics.

## 9. Schedule Outputs

Required row-level outputs:

```text
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_schedule_action_panel.parquet
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_exposure_daily_panel.parquet
ep2/outputs/requirement_03_schedule_bridge/cache/requirement_03_episode_schedule_summary.parquet
```

Action and exposure schemas must be compatible with:

```text
ep2/engineering_baseline/outputs/cache/ep2_schedule_action_panel.parquet
ep2/engineering_baseline/outputs/cache/ep2_exposure_daily_panel.parquet
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_schedule_action_panel.parquet
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_exposure_daily_panel.parquet
```

`requirement_03_episode_schedule_summary.parquet` minimum fields:

```text
schedule_id
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
fast_fail_exit
natural_exit
after_cost_return
missed_gain_to_exposure
turnover
first_exposure_date
exit_date
selection_status
no_probe_reason
no_confirm_add_reason
```

Required reports:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_schedule_results.csv
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_schedule_comparison.csv
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_confirm_add_audit.csv
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_gate_audit.csv
```

`requirement_03_schedule_results.csv` minimum fields:

```text
schedule_id
split
episode_count
episode_with_any_exposure_count
probe_rate
confirm_add_rate
fast_fail_exit_rate
natural_exit_rate
mean_after_cost_return
median_after_cost_return
p05_after_cost_return
p95_after_cost_return
big_winner_capture_rate
missed_gain_to_exposure_median
turnover_proxy
top1_instrument_year_exposure_share
top5_instrument_exposure_share
positive_pnl_year_count
top_year_positive_pnl_share
top_instrument_year_positive_pnl_share
```

`requirement_03_schedule_comparison.csv` minimum fields:

```text
split
schedule_id
comparison_schedule_id
mean_after_cost_return_diff
median_after_cost_return_diff
big_winner_coverage_loss
turnover_reduction
missed_gain_to_exposure_diff
confirm_add_return_contribution
fast_fail_return_contribution
```

Contribution fields must use deterministic counterfactual schedules:

```text
confirm_add_return_contribution =
  mean_after_cost_return(hazard_probe_confirm_add_fast_fail)
  - mean_after_cost_return(hazard_probe_with_simple_stop_replay)

fast_fail_return_contribution =
  mean_after_cost_return(hazard_probe_confirm_add_fast_fail)
  - mean_after_cost_return(hazard_probe_confirm_add_no_fast_fail)
```

`hazard_probe_with_simple_stop_replay` uses the frozen Requirement 02 selected probe dates, `probe_weight = 0.30`, no confirm-add, and the same fast-fail / natural-exit mechanics. `hazard_probe_confirm_add_no_fast_fail` uses the Requirement 03 probe and confirm-add rule but disables fast-fail exits; it is diagnostic-only and cannot become the promoted schedule.

## 10. BaseRate-Overlap Bridge

Requirement 03 answers only the first three BaseRate bridge questions.

All BaseRate joins must use these canonical filters:

```yaml
prediction_panel:
  label_name: LABEL_1D_Q

order_panel:
  portfolio_id: topk_50_dropout_5_daily
  label_name: LABEL_1D_Q
  cost_scenario: base
  side: buy
  blocked: false

trade_panel:
  portfolio_id: topk_50_dropout_5_daily
  label_name: LABEL_1D_Q
  cost_scenario: base
  side: buy
  filled: true
```

Rows outside these filters are excluded from overlap counts. Sell rows, blocked orders, unfilled trades, non-primary portfolios, non-primary labels, and non-base cost scenarios must not count as BaseRate coverage or hits.

### 10.1 Launch Pool TopK Hit

Question:

> How many EP2 launch events / episodes are also hit by BaseRate TopK?

Definition:

```text
base_rate_topk_hit =
  base_rate_prediction_top50_hit
  or base_rate_order_hit
  or base_rate_trade_hit

base_rate_prediction_top50_hit =
  instrument is in the same-date top 50 BaseRate prediction score set

base_rate_order_hit =
  instrument appears in the filtered BaseRate primary buy order rows
  on the matched BaseRate execution date

base_rate_trade_hit =
  instrument appears in the filtered BaseRate primary buy trade rows
  on the matched BaseRate execution date
```

Primary matching:

```text
EP2 probe_signal_date -> BaseRate prediction_panel.date
EP2 probe_execution_date -> BaseRate order_panel.date / trade_panel.date
```

Required report:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_baserate_launch_overlap.csv
```

Minimum fields:

```text
split
schedule_id
episode_count
episode_with_probe_count
base_rate_prediction_covered_count
base_rate_prediction_coverage_rate
base_rate_prediction_top50_hit_count
base_rate_prediction_top50_hit_rate
base_rate_order_hit_count
base_rate_order_hit_rate
base_rate_trade_hit_count
base_rate_trade_hit_rate
base_rate_any_hit_count
base_rate_any_hit_rate
```

### 10.2 Exposure Signal in BaseRate Score Region

Question:

> Does the EP2 exposure signal appear in a high BaseRate score region?

Definition:

For each EP2 selected probe and confirm-add event, join BaseRate `prediction_panel.parquet` by `(date, instrument)`, then compute same-date cross-sectional rank. Higher BaseRate `score` is better:

```text
base_rate_score_rank_pct =
  descending_rank_percentile(score)
  where the highest score on the date has percentile 1.0
  and the lowest score has percentile 1 / same_day_prediction_count

base_rate_high_score_region = base_rate_score_rank_pct >= 0.80
base_rate_topk_prediction_hit = descending_rank(score) <= 50
```

Required report:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_baserate_score_overlap.csv
```

Minimum fields:

```text
split
action_type
event_count
base_rate_prediction_covered_count
base_rate_prediction_coverage_rate
mean_base_rate_score_rank_pct
median_base_rate_score_rank_pct
high_score_region_count
high_score_region_rate
base_rate_prediction_top50_hit_count
base_rate_prediction_top50_hit_rate
```

### 10.3 Uncovered Low-Frequency Opportunity

Question:

> Does the EP2 exposure schedule provide low-frequency opportunities that BaseRate did not cover?

Definition:

```text
ep2_uncovered_exposure =
  EP2 probe or confirm_add executed
  and filtered BaseRate primary buy order/trade rows did not include the same instrument on the matched execution date
```

Coverage is counted at action level. Return and big-winner metrics are counted at episode level using `launch_episode_id` dedupe:

```text
uncovered_episode =
  the first executed EP2 exposure action for the episode is ep2_uncovered_exposure

uncovered_mean_after_cost_return =
  mean episode after_cost_return over uncovered_episode rows

uncovered_big_winner_capture_rate =
  big-winner capture rate over uncovered_episode rows using the same capture logic as Requirement 02

uncovered_turnover_proxy =
  turnover proxy computed on action-level ep2_uncovered_exposure rows only,
  using the same turnover denominator and cost-model convention as the Requirement 02 schedule reports
```

If probe is covered but confirm-add is uncovered, the action contributes to action-level coverage counts, but the episode is not counted as an uncovered episode for return and big-winner metrics. This prevents double-counting one episode's return across multiple exposure actions.

Required report:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_baserate_uncovered_opportunity.csv
```

Minimum fields:

```text
split
schedule_id
executed_ep2_exposure_count
base_rate_trade_overlap_count
base_rate_trade_overlap_rate
uncovered_ep2_exposure_count
uncovered_ep2_exposure_share
uncovered_episode_count
uncovered_episode_share
uncovered_mean_after_cost_return
uncovered_big_winner_capture_rate
uncovered_turnover_proxy
```

### 10.4 BaseRate Coverage Gate Definition

BaseRate overlap coverage is a validation / robustness hard gate only. Train split coverage may be reported, but it cannot pass or fail Requirement 03.

Coverage unit:

```text
eligible_ep2_action =
  split in {validation, robustness}
  and action_type in {probe, confirm_add}
  and EP2 action is executed
```

Coverage components:

```text
prediction_coverage_rate =
  count(eligible_ep2_action with same-date BaseRate prediction row)
  / count(eligible_ep2_action)

order_coverage_rate =
  count(eligible_ep2_action with same-date filtered BaseRate order panel date coverage)
  / count(eligible_ep2_action)

trade_coverage_rate =
  count(eligible_ep2_action with same-date filtered BaseRate trade panel date coverage)
  / count(eligible_ep2_action)

baserate_overlap_report_coverage =
  min(prediction_coverage_rate, order_coverage_rate, trade_coverage_rate)
```

The gate `min_baserate_overlap_report_coverage >= 0.95` is evaluated separately on validation and robustness. Both splits must pass.

## 11. BaseRate Audit Boundaries

BaseRate overlap reports are diagnostic and cannot be used to choose the EP2 schedule. The runner and validator must enforce:

```text
BaseRate prediction/order/trade rows are read only after:
  - Requirement 02 selected_threshold is loaded;
  - schedule bridge rule is fixed from config;
  - EP2 schedule action/exposure panels are generated.
```

This ordering must be machine-verifiable. The runner must write:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_stage_order_audit.csv
```

Minimum fields:

```text
stage_name
stage_order
started_at
completed_at
input_artifact_name
input_artifact_hash
output_artifact_name
output_artifact_hash
base_rate_rows_available
```

Required stage order:

```text
1 load_requirement_02_selected_contract
2 build_fixed_schedule_bridge_rule
3 generate_ep2_schedule_action_panel
4 generate_ep2_exposure_daily_panel
5 load_filtered_baserate_prediction_panel
6 load_filtered_baserate_order_panel
7 load_filtered_baserate_trade_panel
8 generate_baserate_overlap_reports
9 evaluate_requirement_03_gates
```

For stages 1-4, `base_rate_rows_available` must be `false`. For stages 5-9, BaseRate rows may be available, but they must not alter any EP2 schedule action or exposure artifact hash.

Required audit report:

```text
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_baserate_leakage_audit.csv
```

Minimum fields:

```text
audit_name
passed
observed_value
expected_value
detail
```

Required audit rows:

```text
requirement_02_threshold_unchanged
requirement_02_stop_risk_ceiling_unchanged
base_rate_not_used_for_probe_selection
base_rate_not_used_for_confirm_add_selection
base_rate_not_used_for_feature_construction
base_rate_not_used_for_label_selection
base_rate_not_used_for_schedule_selection
base_rate_portfolio_return_not_used_as_gate
stage_order_prevents_baserate_pre_schedule_access
schedule_action_panel_hash_unchanged_after_baserate_load
exposure_daily_panel_hash_unchanged_after_baserate_load
```

## 12. Proceed Gate to Next Phase

Requirement 03 passes only if validation and robustness both satisfy:

1. schedule bridge is generated from frozen Requirement 02 threshold and stop-risk ceiling;
2. `mean_after_cost_return_diff` vs `hazard_probe_with_simple_stop` is `> 0` on validation;
3. `mean_after_cost_return_diff` vs `hazard_probe_with_simple_stop` is `>= -0.001` on robustness;
4. `big_winner_coverage_loss` vs `hazard_probe_with_simple_stop` is `<= 0.10`;
5. `missed_gain_to_exposure_median <= 0.08`;
6. `turnover_reduction_vs_daily_baserate >= 0.50`;
7. `top1_instrument_year_exposure_share <= 0.10`;
8. `top5_instrument_exposure_share <= 0.35`;
9. BaseRate overlap report coverage, computed with the action-level validation / robustness denominator in section 10.4, is `>= 0.95` on both validation and robustness;
10. action-level uncovered EP2 exposure share is `>= 0.20`;
11. all BaseRate leakage audit rows pass.

Failure precedence is fixed:

1. frozen-contract or leakage failure returns `failed_contract_or_leakage`;
2. schedule gate failure returns `failed_schedule_bridge`;
3. BaseRate report coverage or uncovered-opportunity failure returns `failed_baserate_bridge_coverage`;
4. only if all hard gates pass may status be `passed`.

If frozen-contract or leakage gates fail, Requirement 03 status is:

```text
failed_contract_or_leakage
```

If schedule gates fail, Requirement 03 status is:

```text
failed_schedule_bridge
```

If schedule gates pass but BaseRate audit coverage or uncovered-opportunity gates fail, Requirement 03 status is:

```text
failed_baserate_bridge_coverage
```

If all gates pass, Requirement 03 status is:

```text
passed
```

Passing Requirement 03 does not mean EP2 is a complete strategy. It only permits a later holding / exit phase to study whether the low-frequency EP2 event exposure can be assembled into a portfolio-level process.

## 13. Stop Rules

Stop and do not proceed if any of the following happens:

1. Requirement 02 no longer passes;
2. selected threshold differs from `0.3205667777673395`;
3. selected stop-risk ceiling differs from `0.27410397287415667`;
4. primary label changes from `confirm_h10_u10_d06_conservative_fail`;
5. confirm-add rule is tuned using validation / robustness outcomes;
6. BaseRate rows are used before schedule action/exposure generation;
7. BaseRate overlap changes EP2 schedule selection;
8. direct EP2-vs-BaseRate annual return or max-drawdown comparison is used as a hard gate;
9. EP2 schedule turnover becomes daily-alpha-like and fails the turnover reduction gate;
10. confirm-add materially improves mean return only by sacrificing big-winner coverage beyond the allowed cap;
11. uncovered EP2 exposure is too small to justify a separate low-frequency bridge;
12. results require relabeling, threshold reselection, or BaseRate-informed schedule edits to pass.

## 14. Required Artifact Authority

Requirement 03 must output:

```text
ep2/outputs/requirement_03_schedule_bridge/manifests/requirement_03_schedule_bridge_manifest.json
ep2/outputs/requirement_03_schedule_bridge/reports/requirement_03_artifact_authority.csv
```

`requirement_03_schedule_bridge_manifest.json` minimum fields:

```text
phase
validation_status
next_phase_proceed_status
generated_at
requirement_02_manifest_hash
engineering_baseline_manifest_hash
base_rate_manifest_hash
primary_label_id
frozen_baseline_id
hazard_schedule_id
schedule_bridge_id
selected_threshold
selected_stop_risk_ceiling
schedule_action_panel_hash
exposure_daily_panel_hash
schedule_results_hash
schedule_comparison_hash
baserate_launch_overlap_hash
baserate_score_overlap_hash
baserate_uncovered_opportunity_hash
baserate_leakage_audit_hash
stage_order_audit_hash
gate_audit_hash
```

`requirement_03_artifact_authority.csv` minimum fields:

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

## 15. Validation Checklist

`validate_requirement_03_schedule_bridge.py` must verify:

- Requirement 02 manifest exists and has `requirement_03_proceed_status = passed`;
- Requirement 02 selected threshold and stop-risk ceiling match the frozen config;
- Requirement 02 gate counts are derived from `requirement_02_gate_audit.csv` and equal `gate_count = 27`, `passed_gate_count = 27`, `failed_gate_count = 0`;
- all required artifacts exist;
- schedule action and exposure schemas are compatible with EP2 baseline and Requirement 02;
- no episode crosses split boundaries;
- confirm-add uses only the deterministic frozen rule;
- contribution fields are computed from the named deterministic counterfactual schedules;
- BaseRate joins apply the canonical `portfolio_id`, `label_name`, `cost_scenario`, `side`, `blocked`, and `filled` filters;
- BaseRate score rank uses descending score direction with highest score percentile equal to `1.0`;
- no BaseRate row-level data is used for EP2 schedule selection;
- BaseRate prediction/order/trade joins have explicit coverage rates;
- BaseRate overlap report coverage uses the section 10.4 action-level validation / robustness denominator;
- BaseRate overlap questions 1-3 are all reported;
- uncovered opportunity return and big-winner metrics use episode-level first-uncovered-exposure dedupe;
- uncovered turnover proxy uses action-level uncovered exposure rows;
- stage-order audit proves BaseRate rows are unavailable before EP2 schedule action and exposure artifacts are generated;
- schedule action and exposure artifact hashes are unchanged after BaseRate rows are loaded;
- failure status precedence is contract/leakage, then schedule, then BaseRate coverage;
- deferred BaseRate attribution questions are not reported as conclusions;
- validation and robustness gates are both reported;
- all hard gates pass before `next_phase_proceed_status = passed`;
- manifest hashes match current artifacts.
