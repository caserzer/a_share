# EP2 Requirement 02: Hazard Timing Model

## 1. Purpose

Requirement 02 implements the first formal EP2-3 model phase: a low-turnover hazard timing model that chooses the episode-level first valid probe day inside the frozen EP2 launch pool.

This phase must answer one question:

> Can a pre-registered discrete-time hazard score choose probe days that beat the frozen no-model `probe_with_simple_stop` baseline without reselecting the pool, label, baseline, threshold target, or robustness years?

Requirement 02 is not a full trading strategy and not a BaseRate bridge. It is a controlled model-vs-baseline timing test.

## 2. Entry Gate

Requirement 02 may start only after Requirement 01 passes:

```bash
uv run python ep2/scripts/validate_requirement_01_label_and_baseline_freeze.py
```

Required Requirement 01 state:

```yaml
validation_status: passed
primary_label_id: confirm_h10_u10_d06_conservative_fail
frozen_baseline_id: probe_with_simple_stop
gate_count: 20
passed_gate_count: 20
failed_gate_count: 0
```

If Requirement 01 fails, stop. Do not patch Requirement 02 to work around a failed freeze contract.

## 3. Frozen Inputs

Requirement 02 can read only the frozen EP2 engineering baseline artifacts and Requirement 01 freeze outputs.

Allowed input roots:

```text
ep2/engineering_baseline/outputs/
ep2/outputs/requirement_01_label_and_baseline_freeze/
```

Minimum required inputs:

```text
ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
ep2/engineering_baseline/outputs/cache/ep2_candidate_probe_grid.parquet
ep2/engineering_baseline/outputs/cache/ep2_path_label_panel.parquet
ep2/engineering_baseline/outputs/cache/ep2_schedule_action_panel.parquet
ep2/engineering_baseline/outputs/cache/ep2_exposure_daily_panel.parquet
ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json
ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv
ep2/engineering_baseline/outputs/reports/ep2_no_model_baseline_results.csv
ep2/engineering_baseline/outputs/reports/ep2_no_model_baseline_gate.csv
ep2/engineering_baseline/outputs/reports/ep2_no_model_baseline_comparison.csv
ep2/outputs/requirement_01_label_and_baseline_freeze/manifests/requirement_01_freeze_manifest.json
ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_freeze_summary.csv
ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_gate_audit.csv
ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_primary_label_audit.csv
ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_baseline_freeze_audit.csv
```

Forbidden inputs:

- Explore9 / Explore10 row-level outputs or caches;
- BaseRate row-level outputs or caches;
- raw full-market daily TopK data;
- any label not marked eligible by Requirement 01, except for audit-only sensitivity reporting;
- robustness years 2024 / 2025 for model training, feature selection, model-config selection, or threshold selection.

If a later implementation needs PIT-derived price / money / industry features outside these frozen artifacts, Requirement 02 must stop and the freeze contract must be explicitly amended before implementation. Do not silently add new row-level data access.

## 4. Non-Goals

This phase does not do:

- full holding / exit research;
- BaseRate overlap bridge;
- portfolio-level annual return / max drawdown comparison;
- path-to-primitive discovery;
- leaf rule extraction;
- industry-specific models;
- Cox / Fine-Gray competing-risk models;
- broad feature search;
- label reselection;
- pool reselection;
- threshold tuning on 2024 / 2025;
- high-frequency daily alpha construction.

## 5. Output Layout

All Requirement 02 outputs must be written under:

```text
ep2/outputs/requirement_02_hazard_timing_model/
```

Required subdirectories:

```text
ep2/outputs/requirement_02_hazard_timing_model/
  cache/
  reports/
  manifests/
```

No Requirement 02 output may overwrite `ep2/engineering_baseline/outputs/` or Requirement 01 outputs.

## 6. Command Surface

Minimum command surface:

```bash
uv run python ep2/scripts/run_requirement_02_hazard_timing_model.py --config ep2/configs/requirement_02_hazard_timing_model.yaml
uv run python ep2/scripts/validate_requirement_02_hazard_timing_model.py --config ep2/configs/requirement_02_hazard_timing_model.yaml
```

The runner must generate all row-level artifacts, reports, and manifests. The validator must fail closed on any missing required artifact, schema violation, leakage violation, freeze violation, split violation, or proceed-gate failure.

## 7. Frozen Config

Requirement 02 config must include these values:

```yaml
phase: requirement_02_hazard_timing_model
output_root: ep2/outputs/requirement_02_hazard_timing_model

frozen_contract:
  requirement_01_summary: ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_freeze_summary.csv
  primary_label_id: confirm_h10_u10_d06_conservative_fail
  frozen_baseline_id: probe_with_simple_stop
  expected_requirement_01_status: passed

model_scope:
  max_probe_window: 10
  primary_horizon: 10
  primary_upside: 0.10
  primary_drawdown: 0.06
  same_day_policy: conservative_fail
  probe_weight: 0.30
  natural_exit: next_open_after_H_trading_days
  fast_fail_drawdown: 0.06

hazard_score:
  lambda_stop: 1.0
  mu_missed_upside: 1.0
  missed_upside_field: missed_gain_to_probe

split:
  train_start: 2017-07-04
  train_end: 2021-12-31
  validation_start: 2022-01-01
  validation_end: 2023-12-31
  robustness_start: 2024-01-01
  robustness_end: 2025-12-31
  split_date_field: launch_effective_date
  embargo_trading_days: 10
  split_unit: launch_episode_id

threshold_selection:
  selection_split: validation
  threshold_grid_source: validation_score_quantiles
  threshold_quantiles: [0.00, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
  primary_objective: mean_after_cost_return_diff_vs_probe_with_simple_stop
  tie_breakers:
    - lower_turnover_proxy
    - lower_missed_gain_to_exposure_median
    - lower_top1_instrument_year_exposure_share

proceed_gate:
  min_mean_after_cost_return_diff_vs_probe_with_simple_stop: 0.0
  max_big_winner_coverage_loss_vs_probe_with_simple_stop: 0.20
  max_missed_gain_to_exposure_median: 0.08
  min_turnover_reduction_vs_daily_baserate: 0.50
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  year_positive_pnl_concentration:
    min_positive_pnl_year_count: 2
    max_two_year_positive_pnl_share: 0.65
    max_three_or_more_year_positive_pnl_share: 0.35
    hard_gate_splits: [validation, robustness]
  max_top1_instrument_year_positive_pnl_share: 0.10
```

## 8. Training Unit and Panel

The training unit is one `(launch_episode_id, probe_signal_date)` candidate day from:

```text
ep2_candidate_probe_grid.parquet
```

Only rows with `is_valid_probe_candidate = true` may enter training, validation, threshold selection, or schedule simulation.

Required training panel output:

```text
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_hazard_training_panel.parquet
```

Minimum schema:

| Column | Rule |
| --- | --- |
| `launch_episode_id` | from candidate grid |
| `instrument` | from candidate grid |
| `probe_signal_date` | close-derived signal date |
| `probe_execution_date` | next-open execution date |
| `launch_effective_date` | first executable launch date |
| `split` | train / validation / robustness |
| `primary_label_id` | constant `confirm_h10_u10_d06_conservative_fail` |
| `hazard_class` | target_first / stop_first / neither |
| `target_first_label` | boolean |
| `stop_first_label` | boolean |
| `neither_label` | boolean |
| `label_path_start_date` | must equal `probe_execution_date` |
| `days_from_launch_execution` | from candidate grid |
| `missed_gain_to_probe` | from candidate grid |
| `is_valid_probe_candidate` | must be true |

Episode-level dedup rule:

```text
The same launch_episode_id must not appear in more than one split.
```

Embargo rule:

```text
No train episode may have launch_effective_date inside 10 trading days before validation_start.
No validation episode may have launch_effective_date inside 10 trading days before robustness_start.
```

## 9. Label Construction

Filter `ep2_path_label_panel.parquet` to:

```text
label_id = confirm_h10_u10_d06_conservative_fail
```

For each candidate row:

```text
target_first_label =
  label_value == 1

stop_first_label =
  first_drawdown_date is not null
  and (
    first_target_date is null
    or first_drawdown_date < first_target_date
    or same_day_ambiguous is true under conservative_fail policy
  )

neither_label =
  not target_first_label
  and not stop_first_label
```

Exactly one of `target_first_label`, `stop_first_label`, `neither_label` must be true for every training row.

Required report:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_class_balance.csv
```

Minimum fields:

```text
split
hazard_class
row_count
episode_count
row_share
episode_share
```

## 10. Feature Contract

Requirement 02 uses a narrow, frozen feature bank. Feature search is not allowed.

Allowed primary feature families:

```text
candidate_timing:
  days_from_launch_execution
  missed_gain_to_probe
  pre_probe_fast_fail_from_launch_reference

launch_context:
  launch_event_rank_within_episode
  executable_event_count
  industry_asof_signal_date

execution_state:
  blocked_buy_reason
  is_buy_executable_next_open
```

The implementation may encode categorical fields by deterministic one-hot encoding, but it must write the resolved feature list and hash.

Required outputs:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_feature_dictionary.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_feature_asof_audit.csv
```

`requirement_02_feature_dictionary.csv` minimum fields:

```text
feature_name
source_artifact
source_field
feature_family
asof_rule
dtype
is_categorical
enabled
```

`requirement_02_feature_asof_audit.csv` minimum fields:

```text
feature_name
source_artifact
max_allowed_date_relation
uses_execution_date_intraday
violation_count
```

All predictive features must be available no later than `probe_signal_date` close. `probe_execution_date` open may be used as execution price only, not as a predictive feature.

## 11. Model Family

The primary model is a discrete-time three-class softmax model:

```text
classes:
  0 = target_first
  1 = stop_first
  2 = neither
```

Allowed first implementation:

```yaml
model_type: lightgbm_multiclass_softmax
objective: multiclass
num_class: 3
random_state: 20260509
```

The model config must be fixed before validation scoring. A small implementation sanity grid is allowed only if every candidate model is selected by validation split only and the grid is written to `requirement_02_model_config_audit.csv`.

Forbidden:

- binary label model;
- model chosen by 2024 / 2025 robustness results;
- model chosen by BaseRate overlap;
- separate industry models;
- leaf extraction as a decision rule.

## 12. Hazard Score

For every candidate probe day, produce:

```text
P_target_first
P_stop_first
P_neither
score_probe_day =
    P_target_first
  - 1.0 * P_stop_first
  - 1.0 * max(missed_gain_to_probe, 0)
```

Required prediction panel:

```text
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_hazard_prediction_panel.parquet
```

Minimum schema:

```text
launch_episode_id
instrument
probe_signal_date
probe_execution_date
split
P_target_first
P_stop_first
P_neither
score_probe_day
score_rank_within_episode
is_valid_probe_candidate
```

Probability rows must satisfy:

```text
abs(P_target_first + P_stop_first + P_neither - 1.0) <= 1e-6
```

## 13. Episode Primary Probe Rule

Requirement 02 selects at most one model probe per launch episode.

```yaml
episode_primary_probe_day:
  search_window:
    start: launch_effective_date
    end: launch_effective_date + max_probe_window
  valid_if:
    - is_valid_probe_candidate = true
    - score_probe_day >= selected_threshold
    - P_stop_first <= selected_stop_risk_ceiling
    - pre_probe_fast_fail_from_launch_reference = false
    - missed_gain_to_probe <= 0.08
  if_multiple: earliest_valid_day_only
  if_none: no_probe
```

Primary stop-risk ceiling:

```yaml
selected_stop_risk_ceiling: validation_median_P_stop_first_among_target_first_positive_rows
```

If no threshold satisfies the proceed gates on the validation split, Requirement 02 must output `validation_status = failed` and must not proceed to Requirement 03.

Required output:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_episode_primary_probe.csv
```

Minimum fields:

```text
launch_episode_id
instrument
split
selected_probe_signal_date
selected_probe_execution_date
selected_threshold
selected_stop_risk_ceiling
score_probe_day
P_target_first
P_stop_first
P_neither
missed_gain_to_probe
selection_status
no_probe_reason
```

## 14. Threshold Selection

Threshold selection uses validation split only.

For each candidate threshold:

1. apply the episode primary probe rule;
2. simulate the same exposure state machine as `probe_with_simple_stop`;
3. compare against frozen `probe_with_simple_stop`;
4. write threshold-level metrics;
5. choose the threshold with the best validation objective among thresholds that pass all hard gates.

Required report:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_threshold_sweep.csv
```

Minimum fields:

```text
threshold
split
episode_count
episode_with_probe_count
probe_rate
mean_after_cost_return
mean_after_cost_return_diff_vs_probe_with_simple_stop
big_winner_coverage_loss_vs_probe_with_simple_stop
missed_gain_to_exposure_median
turnover_proxy
turnover_reduction_vs_daily_baserate
top1_instrument_year_exposure_share
top5_instrument_exposure_share
positive_pnl_year_count
top_year_positive_pnl_share
top_instrument_year_positive_pnl_share
passed_all_gates
```

Threshold finalization report:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_selected_threshold.csv
```

Minimum fields:

```text
selected_threshold
selected_stop_risk_ceiling
selection_split
selection_reason
validation_objective_value
validation_passed_all_gates
```

## 15. Schedule Simulation

Requirement 02 schedule id:

```text
hazard_probe_with_simple_stop
```

This schedule uses the model-selected probe date but otherwise inherits the frozen baseline mechanics:

```yaml
probe_weight: 0.30
confirm_add_enabled: false
fast_fail_drawdown: 0.06
natural_exit: next_open_after_H_trading_days
primary_H: 10
cost_model: same as engineering baseline
blocked_exit_retry: same as engineering baseline
```

Required row-level outputs:

```text
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_schedule_action_panel.parquet
ep2/outputs/requirement_02_hazard_timing_model/cache/requirement_02_exposure_daily_panel.parquet
```

The action and exposure schemas must be compatible with:

```text
ep2_schedule_action_panel.parquet
ep2_exposure_daily_panel.parquet
```

## 16. Model Evaluation

Required reports:

```text
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_model_metrics.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_schedule_results.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_baseline_comparison.csv
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_gate_audit.csv
```

`requirement_02_model_metrics.csv` minimum fields:

```text
split
row_count
episode_count
multiclass_logloss
target_first_auc_ovr
stop_first_auc_ovr
neither_auc_ovr
top_decile_target_first_rate
top_decile_stop_first_rate
```

`requirement_02_schedule_results.csv` minimum fields:

```text
schedule_id
split
episode_count
episode_with_any_exposure_count
probe_rate
no_probe_rate
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
```

`requirement_02_baseline_comparison.csv` minimum fields:

```text
split
comparison_id
comparison_schedule_id
mean_after_cost_return_diff
median_after_cost_return_diff
big_winner_coverage_loss
turnover_reduction
missed_gain_to_exposure_diff
```

## 17. Proceed Gate to Requirement 03

Requirement 02 passes only if validation split and robustness split both satisfy:

1. `mean_after_cost_return_diff_vs_probe_with_simple_stop > 0`;
2. `big_winner_coverage_loss_vs_probe_with_simple_stop <= 0.20`;
3. `missed_gain_to_exposure_median <= 0.08`;
4. `turnover_reduction_vs_daily_baserate >= 0.50`;
5. `top1_instrument_year_exposure_share <= 0.10`;
6. `top5_instrument_exposure_share <= 0.35`;
7. year-level positive-PnL concentration passes the split-aware hard gate:
   - validation / robustness must each have positive model-selected exposure PnL in at least 2 years;
   - when a hard-gate split has exactly 2 positive-PnL years, no year may contribute more than 65% of positive model-selected exposure PnL;
   - when a hard-gate split has 3 or more positive-PnL years, no year may contribute more than 35% of positive model-selected exposure PnL;
   - train split year concentration is diagnostic-only and cannot block or unlock Requirement 03;
8. no instrument-year contributes more than 10% of positive model-selected exposure PnL.

Rationale: validation and robustness are each 2-year holdouts. A fixed 35% top-year positive-PnL cap is mathematically impossible in a 2-year split because the largest year must contribute at least 50% of positive PnL. Requirement 02 therefore uses a 2-year concentration cap for holdout splits and retains the stricter 35% rule only when at least 3 positive-PnL years are present.

The validation split selects the model threshold. The robustness split can only confirm or reject the selected threshold; it cannot change the threshold.

If validation passes but robustness fails, Requirement 02 status is:

```text
failed_robustness_holdout
```

and Requirement 03 must not start.

## 18. Stop Rules

Stop and do not proceed to Requirement 03 if any of the following happens:

1. Requirement 01 no longer passes;
2. primary label changes;
3. frozen baseline changes;
4. model uses 2024 / 2025 for training, model selection, threshold selection, or feature selection;
5. model uses BaseRate / Explore row-level inputs;
6. episode appears in more than one split;
7. predictive features use execution-date intraday data;
8. selected threshold only beats random but not `probe_with_simple_stop`;
9. model signal frequency becomes daily-alpha-like and fails turnover reduction;
10. big-winner coverage falls more than allowed;
11. results require relabeling or threshold reselection to pass.

## 19. Required Artifact Authority

Requirement 02 must output:

```text
ep2/outputs/requirement_02_hazard_timing_model/manifests/requirement_02_hazard_manifest.json
ep2/outputs/requirement_02_hazard_timing_model/reports/requirement_02_artifact_authority.csv
```

`requirement_02_hazard_manifest.json` minimum fields:

```text
phase
validation_status
requirement_03_proceed_status
generated_at
requirement_01_manifest_hash
engineering_baseline_manifest_hash
primary_label_id
frozen_baseline_id
selected_threshold
selected_stop_risk_ceiling
model_type
feature_dictionary_hash
training_panel_hash
prediction_panel_hash
schedule_action_panel_hash
gate_audit_hash
```

`requirement_02_artifact_authority.csv` minimum fields:

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

## 20. Validation Checklist

`validate_requirement_02_hazard_timing_model.py` must verify:

- Requirement 01 passed and hashes match recorded inputs;
- all required artifacts exist;
- primary label is `confirm_h10_u10_d06_conservative_fail`;
- frozen baseline is `probe_with_simple_stop`;
- training panel uses only valid probe candidates;
- exactly one hazard class is true per training row;
- no episode crosses split boundaries;
- embargo is respected;
- 2024 / 2025 are not used for model or threshold selection;
- feature dictionary contains only enabled allowed features;
- feature as-of audit has zero violations;
- probability rows sum to one;
- episode primary probe uses earliest valid day only;
- threshold is selected from validation split only;
- schedule state machine is compatible with the frozen baseline;
- validation and robustness gates are both reported;
- Requirement 03 proceed status is explicitly `passed`, `failed_validation`, or `failed_robustness_holdout`.
