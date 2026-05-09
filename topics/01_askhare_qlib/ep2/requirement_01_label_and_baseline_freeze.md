# EP2 Requirement 01: Label and Baseline Freeze

## 1. Purpose

本 requirement 的目的不是重新做 EP2-0 工程基座，而是把已经完成的 `ep2/engineering_baseline` 结果冻结为后续 EP2-3 / EP2-4 的唯一输入合同。

完成本文件以前，不允许开始 hazard timing model、feature search、模型阈值选择、portfolio selection 或 BaseRate bridge。

## 2. Frozen Authority

权威输入来自：

```text
ep2/engineering_baseline/requirement.md
ep2/engineering_baseline/config.yaml
ep2/engineering_baseline/outputs/
```

当前 engineering baseline manifest:

```yaml
validation_status: passed
required_artifact_count: 20
existing_required_artifact_count: 20
config_hash: 02c64d1c90fb2344247f732e7935738bae17542f67442db3758ddcc0f4c6f492
launch_detector_config_hash: ecf4d97efb4239181765a50b1fd161af4b93d7f5e298cbce5bb276aeda4e10d0
```

Requirement 02 的 hazard timing model 只能读取这些 frozen artifacts，不得从 Explore9 / Explore10 / BaseRate cache 读取 row-level 输入。

Requirement 03 的 BaseRate-overlap bridge 可以读取后续 requirement 明确定义的 BaseRate bridge inputs，但这些 inputs 只能用于 overlap / coverage audit，不得反向影响 launch pool、primary label、hazard features、model threshold 或 schedule selection。

## 3. Frozen Launch Pool

Frozen pool 已完成，后续不得为了改善模型或 schedule 结果重定义 pool。

```yaml
launch_detector_version: EP2_LAUNCH_DETECTOR_V0
detector_id: EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20
detector_family: price_breakout_money_surge
pool_rows: 5605
episode_count: 2464
source_pool: ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
episode_dictionary: ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv
pool_freeze_manifest: ep2/engineering_baseline/outputs/manifests/ep2_pool_freeze_manifest.json
```

冻结内容包括：

- universe definition；
- PIT universe / industry as-of rule；
- price adjustment rule；
- launch detector version / thresholds / lookback windows；
- episode start / reset / end / merge rule；
- next-open execution rule；
- buy / sell direction-specific block fields；
- cost model components。

Hard rule:

```text
If the launch detector, universe, PIT rule, price adjustment, episode rule, or execution rule changes,
EP2 must be treated as a full restart.
```

## 4. Frozen Primary Label

Primary label 冻结为：

```yaml
primary_label_id: confirm_h10_u10_d06_conservative_fail
horizon: 10
upside: 0.10
drawdown: 0.06
same_day_policy: conservative_fail
selection_scope: 2017_2023_core_research_years
robustness_only_years: [2024, 2025]
```

选择理由：

- 与 `schedule_defaults.primary_H = 10` 对齐；
- 与 `canonical_fast_fail_drawdown = 0.06` 对齐；
- 使用保守 ambiguity policy；
- 通过 candidate base-rate、episode base-rate、ambiguity、concentration gates。

Primary label tie-breaker is frozen as:

```text
1. keep only rows with frozen_for_ep2_2 = true;
2. keep only same_day_policy = conservative_fail;
3. keep only horizon = schedule_defaults.primary_H = 10;
4. keep only drawdown = canonical_fast_fail_drawdown = 0.06;
5. choose the smallest upside target whose candidate_positive_rate remains >= 0.20 and whose episode_any_positive_rate <= 0.50.
```

Under this rule, `confirm_h10_u10_d06_conservative_fail` is selected. `confirm_h10_u08_d06_conservative_fail` is a valid sensitivity, but it is not primary because its `episode_any_positive_rate = 0.534636` is above the frozen primary tie-breaker ceiling. Higher upside labels under the same H/drawdown either fail the candidate base-rate gate or are outside the frozen primary tie-breaker.

Primary label audit:

```yaml
candidate_positive_rate: 0.224157
episode_any_positive_rate: 0.431616
episode_first_valid_positive_rate: 0.267022
episode_weighted_positive_rate: 0.243188
event_count: 12692
episode_count: 1689
year_count: 7
top1_instrument_year_positive_share: 0.009139
same_day_ambiguity_rate: 0.0
median_after_cost_return: -0.026881
```

The original candidate `confirm_success_10d_12pct_before_6pct_drawdown` maps to `confirm_h10_u12_d06_conservative_fail` under the conservative ambiguity policy. It is not frozen as primary because `ep2_label_freeze_candidate.csv` marks it as `candidate_base_rate_out_of_range` with `frozen_for_ep2_2 = false`.

## 5. Allowed Label Sensitivities

Only labels with `frozen_for_ep2_2 = true` in:

```text
ep2/engineering_baseline/outputs/reports/ep2_label_freeze_candidate.csv
```

may be used as sensitivity labels.

Current count:

```yaml
label_sweep_rows: 108
frozen_for_ep2_2_count: 30
```

Sensitivity labels are audit-only. They must not be used to re-select the primary model, model threshold, or schedule rule after looking at EP2-3 / EP2-4 outcomes.

## 6. Frozen Baseline

The only no-model schedule that passed all hard gates is:

```yaml
baseline_schedule_id: probe_with_simple_stop
probe_weight: 0.30
probe_date_rule: launch_effective_date
confirm_add_enabled: false
fast_fail_drawdown: 0.06
natural_exit: next_open_after_H_trading_days
primary_H: 10
```

Baseline result:

```yaml
episode_with_any_exposure_count: 2447
probe_rate: 0.993101
fast_fail_exit_rate: 0.404221
mean_after_cost_return: -0.001409
median_after_cost_return: -0.006526
big_winner_capture_rate: 0.039660
missed_gain_to_exposure_median: 0.0
turnover_proxy: 15.006477
top1_instrument_year_exposure_share: 0.002043
top5_instrument_exposure_share: 0.009399
```

Passed hard gates:

```yaml
mean_after_cost_diff_vs_random: 0.004060
big_winner_coverage_loss_vs_buy_all: -0.011331
median_missed_gain_to_exposure: 0.0
top1_instrument_year_exposure_share: 0.002043
top5_instrument_exposure_share: 0.009399
turnover_reduction_vs_daily_baserate: 0.697990
mean_after_cost_diff_vs_buy_all_hold_to_H: 0.003095
mean_after_cost_diff_vs_buy_all_same_fast_fail: 0.003706
```

`ep2_no_model_baseline_gate.csv` uses the legacy gate name `after_cost_lift_vs_random`; because random mean return is negative, the recorded value is interpreted here as a mean after-cost return difference, not a multiplicative ratio.

This baseline is the minimum comparison target for EP2-3. A hazard timing model that cannot beat `probe_with_simple_stop` is not a valid improvement.

For Requirement 02, "beat `probe_with_simple_stop`" means OOS results must satisfy all of the following under the same frozen pool, primary label, execution state machine, cost model, and natural-exit rule:

1. `mean_after_cost_return - probe_with_simple_stop.mean_after_cost_return > 0`;
2. `big_winner_coverage_loss_vs_probe_with_simple_stop <= 0.20`;
3. `missed_gain_to_exposure_median <= 0.08`;
4. `turnover_reduction_vs_daily_baserate >= 0.50`;
5. `top1_instrument_year_exposure_share <= 0.10`;
6. `top5_instrument_exposure_share <= 0.35`;
7. no robustness year or sensitivity label may be used to choose the model threshold.

## 7. Failed Baselines

The following schedules are retained only as negative controls or fairness baselines:

```text
buy_all_on_launch_hold_to_H
buy_all_on_launch_with_same_fast_fail
fixed_delay_1d
fixed_delay_3d
fixed_delay_5d
fixed_delay_10d
random_probe_within_launch_window
staged_buy_all
probe_then_naive_add
```

They must not be promoted into EP2-3 candidates unless EP2 is explicitly restarted with a new requirement.

## 8. Proceed Gate to Requirement 02

Requirement 02 may start only if all statements below remain true:

1. `ep2_engineering_baseline_manifest.json` has `validation_status = passed`;
2. all required artifacts in `ep2_required_artifact_authority.csv` still exist;
3. pool / PIT / feature-asof / execution audits still pass;
4. primary label remains `confirm_h10_u10_d06_conservative_fail`;
5. `probe_with_simple_stop` remains the frozen benchmark to beat;
6. no launch detector, pool, label threshold, or baseline rule is modified to improve downstream results.

If any item fails, stop and update this requirement before continuing.
