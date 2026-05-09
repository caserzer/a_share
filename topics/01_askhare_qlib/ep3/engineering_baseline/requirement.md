# EP3 Engineering Baseline Requirement

> Requirement id: `ep3_engineering_baseline`
> Status: implementation-ready requirement
> Scope: EP3-P0 audit-only winner formation anchor discovery
> Authoritative context: `ep3/discussion.md`

## 1. Purpose

EP3 的研究对象是 **winner formation anchor discovery**，不是 EP2 R05/R06 continuation filter，也不是策略开发。

本工程基座只回答一个问题：

```text
在不继承 R02 threshold、R03 confirmed pool、R05 holding policy 的前提下，
是否存在可观察、next-open 可执行、能被 matched baseline 反证的
winner formation anchor idea？
```

本阶段是 EP3-P0。它是 audit-first discovery，不是 P1 validation。

完成本 requirement 以前，不允许：

```text
训练 entry / ranking / continuation 模型；
输出策略候选；
做 full portfolio backtest；
把任何 anchor 标记为可交易系统；
进入 EP3-P1 / EP3-P2。
```

## 2. Research Positioning

EP2 R01-R05 的阶段性结论是：

```text
EP2/R03 的 entry 更像短周期 launch event timing；
它没有证明 R03 confirm-add 后的 episode 已经进入 long-horizon winner formation。
```

因此 EP3 不继续在 R03 confirmed pool 中做 filter。EP3 改问：

```text
真正的大 winner 在启动前、启动初期、加速前，
是否存在稳定、可观察、可执行的 lifecycle anchor？
```

EP3-P0 的成功不是形成策略，而是形成一组经过反证的 preliminary anchor lead。

## 3. Non-Goals

本阶段明确不做：

- 不训练任何模型；
- 不做 R02 threshold search；
- 不读取 R03 confirmed pool 作为主研究母体；
- 不继承 R05 deterministic holding policies 作为 selection input；
- 不把 120d big-winner label 作为训练目标；
- 不在 H10/H20/H60 中选择最优 horizon；
- 不实现 deferred anchor families；
- 不用 robustness 或 future split 选择 anchor、窗口、baseline、threshold；
- 不输出 P1 candidate、frozen strategy、portfolio candidate 或 production signal；
- 不做 BaseRate row-level overlap 或组合层收益宣称。

## 4. Canonical Inputs

所有基础输入必须来自项目 canonical `data/` 目录和已冻结 EP2 artifacts。禁止从 Explore9 / Explore10 / BaseRate row-level cache 读取基础数据。

| Input | Required path | Role |
| --- | --- | --- |
| Qlib PIT provider | `data/qlib/cn_data_pit` | daily OHLCV / money / calendar |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` | universe eligibility |
| PIT qlib instrument map | `data/universe/pit_qlib_instrument_universe.csv` | code / instrument audit |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | industry / concentration audit |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | next trading day resolution |
| EP2 launch pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | reference launch episodes |
| EP2 candidate probe grid | `ep2/engineering_baseline/outputs/cache/ep2_candidate_probe_grid.parquet` | reference as-of / execution discipline only |
| EP2 engineering manifest | `ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json` | frozen input authority |

EP2 launch detector may be used as a reference anchor and as part of the bounded forward-audit universe. It must not be treated as the winner formation source of truth.

## 5. Required Config

The implementation must add:

```text
ep3/engineering_baseline/config.yaml
```

Minimum required config:

```yaml
phase: ep3_engineering_baseline
output_root: ep3/engineering_baseline/outputs

data_sources:
  qlib_provider_uri: data/qlib/cn_data_pit
  pit_universe_path: data/universe/pit_mcap500_mainboard_daily.csv
  pit_qlib_instrument_universe_path: data/universe/pit_qlib_instrument_universe.csv
  pit_industry_path: data/targets/pit_industry_membership.csv
  trading_calendar_path: data/qlib/cn_data_pit/calendars/day.txt

frozen_ep2_inputs:
  ep2_engineering_manifest: ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json
  ep2_launch_pool: ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
  ep2_candidate_probe_grid: ep2/engineering_baseline/outputs/cache/ep2_candidate_probe_grid.parquet

split:
  train_start: "2017-07-04"
  train_end: "2021-12-31"
  validation_start: "2022-01-01"
  validation_end: "2023-12-31"
  robustness_start: "2024-01-01"
  robustness_end: "2025-12-31"
  split_date_field: signal_date
  horizon_contained_within_split_for_primary_gates: true
  max_label_horizon_trading_days: 240

winner_labels:
  primary:
    label_id: winner_50h120
    horizon_trading_days: 120
    upside_target: 0.50
    target_price_reference: intraday_high
  sensitivity:
    label_id: winner_100h240
    horizon_trading_days: 240
    upside_target: 1.00
    target_price_reference: intraday_high

anchor_scope:
  lifecycle_profiling_universe: all_pit_50h120_and_100h240_winners
  forward_audit_universe: ep2_launch_pool_plus_winner_start_matched_controls
  anchor_window_source: train_lifecycle_profile_only
  anchor_window_status: derived_then_frozen_before_validation
  anchor_window_quantile_low: 0.10
  anchor_window_quantile_high: 0.90
  anchor_window_min_trading_days: 1
  anchor_window_max_trading_days: 60

observable_reference_rules:
  atr_lookback_days: 20
  acceleration_lookback_days: 60
  acceleration_min_return: 0.12
  money_ma_lookback_days: 20
  money_multiple_min: 2.0
  money_min_cny: 50000000
  restrengthen_high_lookback_days: 5
  pullback_min_drawdown_from_acceleration_close: 0.04
  pullback_max_drawdown_from_acceleration_close: 0.18
  pullback_hold_atr_multiple: 2.0
  second_breakout_min_gap_days: 3
  second_breakout_max_gap_days: 60
  second_breakout_min_return_from_first_close: 0.06
  consolidation_max_drawdown_from_first_close: 0.15

primary_anchor_families:
  - pullback_hold_restrengthen
  - second_breakout

deferred_anchor_families:
  - post_breakout_contraction
  - industry_sync_expansion
  - market_regime_reacceleration
  - turnover_volatility_contraction
  - failed_lookalike_avoidance

primary_horizon:
  horizon_id: H20
  holding_trading_days: 20
  natural_exit: next_open_after_H_trading_days

sensitivity_horizons:
  - H10
  - H60

execution:
  signal_date_rule: close_derived_signal_date
  decision_date_rule: same_as_signal_date_after_close
  execution_date_rule: next_trading_day(signal_date)
  entry_price_reference: open[execution_date]
  blocked_execution_reasons:
    - missing_open
    - zero_volume
    - zero_money
    - limit_up_inferred
    - limit_down_inferred
    - not_universe_member
    - missing_calendar_next_day
    - missing_price_row

cost_model:
  same_as_ep2_engineering_baseline: true
  cost_profile: base

trigger_budget:
  min_anchor_trigger_rate_per_launch_episode: 0.20
  max_anchor_trigger_rate_per_launch_episode: 1.50

matched_controls:
  random_seed: 20260509
  controls_per_anchor: 5
  sample_with_replacement_if_insufficient: false
  bucket_quantile_source: train_split_only
  money_bucket_quantiles: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  realized_volatility_bucket_quantiles: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  return_60d_bucket_quantiles: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  max_calendar_day_distance: 20
  max_controls_per_instrument_month: 3

gates:
  min_lifecycle_anchor_recall: 0.30
  min_validation_unique_instrument_year_count: 25
  min_validation_h20_mean_diff_vs_matched_delay: 0.0
  min_validation_h20_p05_diff_vs_matched_delay: -0.003
  max_validation_h20_mae_worsening_vs_matched_delay: 0.005
  min_validation_instrument_year_positive_rate_diff: 0.0
  max_top1_instrument_year_pnl_share: 0.20
  max_top5_instrument_exposure_share: 0.50
```

Any implementation may add fields, but it must not weaken the constraints above without updating this requirement.

## 5.1 Formula Dictionary

All formula fields in this section must appear in `ep3_observable_anchor_dictionary.csv` with `formula_text`, `lookback_days`, `asof_rule`, and `parameter_hash`.

Base references:

```text
t = signal_date
execution_date = next_trading_day(t)
all rolling windows are inclusive of the stated end date
all signal formulas use data <= t
execution_date open/high/low/close/volume/money are forbidden as signal inputs
```

Daily derived fields:

```text
prev_close[t] = close[t - 1 trading day]

true_range[t] =
  max(
    high[t] - low[t],
    abs(high[t] - prev_close[t]),
    abs(low[t] - prev_close[t])
  )

atr20[t] =
  mean(true_range, 20 trading days ending t - 1)

atr20_pct[t] =
  atr20[t] / close[t - 1]

money_ma20[t] =
  mean(money, 20 trading days ending t - 1)

ret_60d[t] =
  close[t] / close[t - 60 trading days] - 1

vol20[t] =
  std(daily close-to-close return, 20 trading days ending t - 1)
```

`launch_like_acceleration` is true on date `t` if all conditions are true:

```text
close[t] / close[t - 60 trading days] - 1 >= 0.12
close[t] >= max(close, 60 trading days ending t - 1)
money[t] >= 2.0 * money_ma20[t]
money[t] >= 50,000,000
PIT universe member on t
not blocked for next-open buy on execution_date
```

`winner_start_anchor` for lifecycle profiling is:

```text
the first launch_like_acceleration date in the 120 trading days before first_50pct_target_date
```

If no such date exists, set `winner_start_anchor_status = no_observable_launch_like_acceleration`.

If multiple launch-like acceleration dates occur within 20 trading days, merge them into one lifecycle episode and keep the earliest date as `winner_start_anchor`.

## 6. Stage Order

The runner must execute stages in this order and write `ep3_stage_order_audit.csv`:

1. input authority and PIT audit;
2. winner label panel construction;
3. lifecycle profiling universe construction;
4. train-only anchor window derivation;
5. observable anchor dictionary freeze;
6. bounded forward-audit universe construction;
7. primary anchor detection;
8. matched baseline construction;
9. H20 primary forward audit and H10/H60 sensitivity;
10. gate audit and manifest.

The winner label panel may be materialized at stage 2, but validation / robustness outcome values must not be consumed by stages 1-5 for deriving windows, formula parameters, matched-control buckets, baseline construction, thresholds, ranking, or gates. In stage-order audit terms, "used" is stricter than "materialized".

`ep3_stage_order_audit.csv` must include:

| Field | Description |
| --- | --- |
| `stage_order` | integer 1-10 |
| `stage_name` | required stage name |
| `completed_at` | ISO timestamp |
| `validation_outcomes_materialized` | may become true after stage 2 |
| `robustness_outcomes_materialized` | may become true after stage 2 |
| `validation_outcomes_used_by_stage` | must be false for stages 1-5 |
| `robustness_outcomes_used_by_stage` | must be false for stages 1-5 |
| `frozen_artifact_written` | artifact written at stage |
| `artifact_hash_after_stage` | hash after stage completion |

## 7. Universe Contract

EP3 has two separate universes.

### 7.1 Lifecycle Profiling Universe

This universe includes all PIT-eligible 50h120 and 100h240 winners.

Allowed use:

```text
retrospective lifecycle profiling；
winner-stage occurrence rate；
days-to / days-from anchor distributions；
observable-stage translation audit；
failure-lookalike existence audit。
```

Forbidden use:

```text
matched baseline lift；
promotion；
strategy selection；
validation gate selection；
training target for a predictive model。
```

### 7.2 Forward Audit Universe

This universe includes:

```text
EP2 launch pool
+ matched control stock-days around train-derived winner_start windows
```

The control construction must be mechanical and auditable. Minimum matching dimensions:

```text
split
calendar month
industry
market universe membership
money bucket
20d realized volatility bucket
60d return bucket
```

Matched controls may not use future winner status, future returns, or validation/robustness outcomes for selection.

Forward audit row grain:

```text
one row per executable candidate signal date and instrument
primary_key = source_universe + anchor_family_id + instrument + signal_date
```

The forward audit universe is built as:

```text
1. all executable EP2 launch pool rows;
2. plus matched control stock-days sampled around train-derived anchor windows;
3. plus same-instrument nonanchor candidates needed for required baselines.
```

Matched control stock-days are selected mechanically:

```text
candidate control date must be in same split as anchor signal_date;
calendar date distance <= 20 calendar days;
same industry as anchor instrument on control date;
same PIT universe membership;
same train-frozen money bucket;
same train-frozen 20d realized volatility bucket;
same train-frozen 60d return bucket;
exclude dates where the same instrument has a primary anchor within +/- 5 trading days;
sample up to 5 controls per anchor using random_seed = 20260509;
tie-break by smaller calendar date distance, then higher money, then instrument lexicographic order;
if fewer than 5 controls exist, use all available controls and set control_shortfall_flag = true;
no replacement unless config explicitly changes and requirement is updated.
```

Bucket boundaries must be derived from train split only and written to:

```text
reports/ep3_matched_control_bucket_freeze.csv
```

The same frozen bucket boundaries must be used for validation and robustness.

## 8. Winner Label Panel

The runner must build:

```text
ep3_winner_label_panel.parquet
```

Required fields:

| Field | Description |
| --- | --- |
| `date` | candidate signal date |
| `instrument` | Qlib instrument |
| `split` | train / validation / robustness |
| `winner_50h120` | true if target +50% reached within 120 trading days |
| `first_50pct_target_date` | first target date if any |
| `winner_100h240` | sensitivity label |
| `first_100pct_target_date` | first sensitivity target date if any |
| `max_forward_return_120` | max forward return in H120 |
| `max_forward_return_240` | max forward return in H240 |
| `label_horizon_complete` | enough future data exists |
| `label_price_adjustment_mode` | PIT adjusted OHLC mode |
| `label_input_hash` | PIT input hash scope |
| `horizon_contained_in_split` | target horizon end date <= split end |
| `eligible_for_primary_gate` | horizon complete and contained in split |

Rows with incomplete horizon may be retained for coverage audit but must be excluded from primary lift calculations.

Row grain:

```text
one row per PIT-eligible stock-day
primary_key = date + instrument
required_min_date =
  first trading day >= train_start with at least 60 prior trading days of OHLCV history
required_max_date =
  robustness_end
price_hash_scope_end =
  robustness_end + 240 trading days, or provider max date if earlier with label_horizon_complete=false
```

Primary gate eligibility:

```text
eligible_for_primary_gate =
  label_horizon_complete
  and horizon_contained_in_split
  and PIT universe member on date
```

Lifecycle profiling may use only train rows where:

```text
split = train
eligible_for_primary_gate = true
```

Validation and robustness gates may use only rows in their respective split with `eligible_for_primary_gate = true`.

## 9. Lifecycle Profile

The runner must write:

```text
ep3_winner_lifecycle_profile.csv
```

Schema:

```text
one row per winner-stage
primary_key = winner_episode_id + lifecycle_stage_id
```

Required fields:

| Field | Description |
| --- | --- |
| `winner_episode_id` | deterministic winner episode id |
| `instrument` | instrument |
| `winner_label_id` | winner_50h120 / winner_100h240 |
| `split` | split by stage signal date |
| `lifecycle_stage_id` | pre_breakout_base / first_acceleration / confirmation_anchor / late_acceleration / failure_lookalike |
| `retrospective_stage_date` | date known retrospectively |
| `observable_signal_date` | close-derived date if stage can be observed |
| `observable_anchor_candidate` | boolean |
| `days_to_first_50pct_target` | stage date to first target |
| `days_from_observable_start` | observable start to stage |
| `stage_extraction_rule_id` | deterministic rule id |
| `stage_extraction_rule_hash` | hash of stage rule |
| `winner_start_anchor_status` | found / no_observable_launch_like_acceleration |
| `anchor_family_id` | mapped primary/deferred family if any |
| `anchor_window_measure` | distance measure used for train quantile freeze |
| `eligible_for_primary_gate` | copied from winner label panel for the stage date |

This table is explanatory. It cannot be used directly as a tradable signal table.

## 10. Anchor Window Freeze

The implementation must derive anchor windows from train split lifecycle profiling only:

```text
anchor_window_low = clipped train quantile 0.10
anchor_window_high = clipped train quantile 0.90
clip range = [1, 60] trading days
```

The derived window must be written to:

```text
ep3_anchor_window_freeze.csv
```

After this file is written, validation / robustness must use the same window with no changes.

If lifecycle profiling cannot derive a valid window for an anchor family, that family is marked `failed_lifecycle_window_derivation` and is not forward-audited.

Window measures are fixed by family:

```text
pullback_hold_restrengthen:
  anchor_window_measure =
    trading_days_between(winner_start_anchor, first_observable_pullback_low_date)

second_breakout:
  anchor_window_measure =
    trading_days_between(winner_start_anchor, second_breakout_signal_date)
```

Quantiles are computed only from train split winner-stage rows with:

```text
winner_label_id = winner_50h120
observable_anchor_candidate = true
winner_start_anchor_status = found
anchor_family_id in primary_anchor_families
eligible_for_primary_gate = true
```

`ep3_anchor_window_freeze.csv` required fields:

| Field | Description |
| --- | --- |
| `anchor_family_id` | primary family |
| `anchor_window_measure` | fixed measure name |
| `train_observation_count` | count used for quantile |
| `raw_quantile_low` | train q10 |
| `raw_quantile_high` | train q90 |
| `train_median_anchor_window_days` | train median used by `matched_delay_baseline` |
| `frozen_window_low` | clipped lower bound |
| `frozen_window_high` | clipped upper bound |
| `window_derivation_status` | derived / failed_lifecycle_window_derivation |
| `window_hash` | hash of frozen window row |

`median_train_anchor_window_days` in later sections means the `train_median_anchor_window_days` value for the same `anchor_family_id` in this file. It must be computed from the same train rows as the q10/q90 window and frozen before validation / robustness audit.

## 11. Primary Anchor Families

P0 may implement only these two anchor families.

### 11.1 `pullback_hold_restrengthen`

Concept:

```text
After a launch-like acceleration, price pulls back but holds above a reference floor,
then re-strengthens on a close-derived signal.
```

Minimum mechanical fields required in `ep3_observable_anchor_dictionary.csv`:

| Field | Required |
| --- | --- |
| `anchor_family_id` | `pullback_hold_restrengthen` |
| `reference_event_rule` | launch-like acceleration source |
| `pullback_window` | train-derived frozen window |
| `hold_floor_rule` | explicit price / ATR floor |
| `restrengthen_rule` | explicit close-derived rule |
| `entry_execution_rule` | next open |
| `parameter_hash` | canonical hash |

P0 formula:

```text
reference acceleration date a:
  launch_like_acceleration[a] = true

eligible pullback low date p:
  p is after a
  trading_days_between(a, p) in frozen pullback window
  drawdown_from_acceleration_close =
    low[p] / close[a] - 1
  drawdown_from_acceleration_close <= -0.04
  drawdown_from_acceleration_close >= -0.18
  low[p] >= close[a] - 2.0 * atr20[a]

restrengthen signal date t:
  t is after p
  t is within 5 trading days after p
  close[t] >= max(high, 5 trading days ending p)
  close[t] > close[t - 1 trading day]
  money[t] >= money_ma20[t]
  next-open buy is executable

anchor signal:
  earliest t satisfying all conditions for each reference acceleration episode
```

If multiple pullback lows satisfy the rule before a restrengthen signal, use the lowest `low[p]`; tie-break by earliest `p`.

P0 failed-lookalike rule for this family:

```text
reference acceleration date a is valid;
candidate date t is executable next open;
there is at least one candidate pullback low p after a and before t;
the row fails exactly one of:
  pullback_window_pass:
    trading_days_between(a, p) in frozen pullback window
  drawdown_band_pass:
    -0.18 <= low[p] / close[a] - 1 <= -0.04
  atr_floor_pass:
    low[p] >= close[a] - 2.0 * atr20[a]
  restrengthen_pass:
    t after p, t within 5 trading days after p,
    close[t] >= max(high, 5 trading days ending p),
    close[t] > close[t - 1 trading day],
    money[t] >= money_ma20[t]
```

### 11.2 `second_breakout`

Concept:

```text
The first launch-like acceleration is not the entry.
A second close-derived breakout / re-acceleration becomes the candidate anchor.
```

Minimum mechanical fields required in `ep3_observable_anchor_dictionary.csv`:

| Field | Required |
| --- | --- |
| `anchor_family_id` | `second_breakout` |
| `first_breakout_rule` | initial launch-like acceleration |
| `reset_or_consolidation_rule` | required separation before second breakout |
| `second_breakout_rule` | explicit close-derived rule |
| `entry_execution_rule` | next open |
| `parameter_hash` | canonical hash |

P0 formula:

```text
first acceleration date a:
  launch_like_acceleration[a] = true

eligible consolidation interval [a+1, t-1]:
  trading_days_between(a, t) in frozen second_breakout window
  trading_days_between(a, t) >= 3
  min(low, interval [a+1, t-1]) >= close[a] * (1 - 0.15)

second breakout signal date t:
  close[t] >= max(high, interval [a+1, t-1])
  close[t] / close[a] - 1 >= 0.06
  money[t] >= 2.0 * money_ma20[t]
  money[t] >= 50,000,000
  next-open buy is executable

anchor signal:
  earliest t satisfying all conditions for each first acceleration episode
```

If a `pullback_hold_restrengthen` anchor and `second_breakout` anchor occur on the same instrument and signal date, keep both rows with distinct `anchor_event_id`; downstream metrics must de-duplicate only when computing instrument-year concentration.

P0 failed-lookalike rule for this family:

```text
first acceleration date a is valid;
candidate date t is executable next open;
t is after a;
the row fails exactly one of:
  window_and_gap_pass:
    trading_days_between(a, t) in frozen second_breakout window
    and trading_days_between(a, t) >= 3
  consolidation_pass:
    min(low, interval [a+1, t-1]) >= close[a] * (1 - 0.15)
  breakout_price_pass:
    close[t] >= max(high, interval [a+1, t-1])
    and close[t] / close[a] - 1 >= 0.06
  breakout_liquidity_pass:
    money[t] >= 2.0 * money_ma20[t]
    and money[t] >= 50,000,000
```

### 11.3 Deferred Families

The following are dictionary-only in P0:

```text
post_breakout_contraction
industry_sync_expansion
market_regime_reacceleration
turnover_volatility_contraction
failed_lookalike_avoidance
```

They must not produce rows in the primary forward audit, must not be ranked, and must not affect gates.

## 12. Candidate Anchor Panel

The runner must write:

```text
ep3_candidate_anchor_panel.parquet
```

Required fields:

| Field | Description |
| --- | --- |
| `anchor_event_id` | deterministic id |
| `anchor_family_id` | primary family |
| `instrument` | instrument |
| `signal_date` | close-derived signal date |
| `execution_date` | next trading day |
| `entry_price_reference` | next open |
| `split` | split by signal date |
| `is_primary_anchor_family` | true only for A/C |
| `is_deferred_anchor_family` | false for P0 rows |
| `is_executable_next_open` | execution status |
| `blocked_buy_reason` | if any |
| `anchor_window_id` | frozen window id |
| `feature_asof_date` | must be <= signal_date |
| `anchor_trigger_rate_denominator_id` | launch_episode / control_bucket |
| `winner_label_available_for_audit` | boolean |
| `eligible_for_primary_gate` | joined from winner label panel by `(signal_date, instrument)` |
| `label_join_status` | matched / missing_label / incomplete_horizon / split_horizon_crossing |
| `source_universe` | ep2_launch_pool / matched_control |
| `reference_acceleration_date` | launch-like acceleration date `a` used by formula |
| `reference_acceleration_event_id` | deterministic id for merged launch-like acceleration episode |
| `anchor_formula_version` | immutable formula version, `ep3_p0_v1` |
| `anchor_parameter_hash` | hash of formula parameters and frozen window |
| `dedupe_rank_within_reference_event` | rank after family-specific tie-breaks |

Only rows with `dedupe_rank_within_reference_event = 1` may enter forward-audit metrics. Non-first rows may be retained for diagnostics but must be marked `excluded_by_reference_event_dedupe = true`.

## 13. Matched Baselines

The runner must write:

```text
ep3_matched_baseline_panel.parquet
```

Required baseline ids:

```text
all_launch_direct_baseline
matched_delay_baseline
same_instrument_nonanchor_baseline
industry_matched_baseline
failed_lookalike_baseline
```

Matched baselines are only valid in the forward audit universe. They are forbidden in winner-only lifecycle profiling.

All baselines must use the same next-open execution, blocked buy, cost, and horizon mechanics as the anchor events.

Baseline construction is fixed as follows:

| Baseline id | Construction |
| --- | --- |
| `all_launch_direct_baseline` | All executable EP2 launch pool rows, independent of whether a primary anchor fired. |
| `matched_delay_baseline` | For each anchor row, same instrument, delayed signal date equal to `signal_date + median_train_anchor_window_days` clipped to the same split and executable next-open; if unavailable, use the nearest later executable date within 20 calendar days and set `delay_repair_flag = true`. |
| `same_instrument_nonanchor_baseline` | Same instrument and same split, executable non-anchor date within +/-20 calendar days, matched to the same train-frozen money / vol20 / ret60 buckets; exclude dates within +/-5 trading days of any primary anchor. |
| `industry_matched_baseline` | Different instrument, same industry, same split, executable date within +/-20 calendar days, same train-frozen money / vol20 / ret60 buckets. |
| `failed_lookalike_baseline` | Rows satisfying all reference acceleration and liquidity conditions but failing exactly one family-specific confirmation condition. This is a baseline / false-positive audit only, not a deferred family implementation. |

`failed_lookalike_avoidance` remains a deferred family. P0 may measure `failed_lookalike_baseline`; it must not train or select a separate avoidance rule.

For pairwise baselines, construct baselines only from anchor rows with `dedupe_rank_within_reference_event = 1`. A baseline row linked to an excluded anchor must either not be emitted or must be marked `match_status = unavailable` and excluded from primary metrics.

`ep3_matched_baseline_panel.parquet` required fields:

| Field | Description |
| --- | --- |
| `baseline_event_id` | deterministic id |
| `anchor_event_id` | linked anchor id when pairwise baseline |
| `baseline_id` | one of required baseline ids |
| `instrument` | baseline instrument |
| `signal_date` | baseline signal date |
| `execution_date` | next trading day |
| `split` | split by baseline signal date |
| `match_status` | matched / repaired / shortfall / unavailable |
| `match_reason` | mechanical explanation |
| `matched_control_bucket_id` | frozen bucket id |
| `delay_repair_flag` | boolean for matched delay repair |
| `control_shortfall_flag` | boolean |
| `is_executable_next_open` | execution status |
| `blocked_buy_reason` | if any |
| `eligible_for_primary_gate` | joined from winner label panel by `(signal_date, instrument)` |
| `label_join_status` | matched / missing_label / incomplete_horizon / split_horizon_crossing |
| `baseline_input_hash` | hash of matched-control inputs |

## 14. Forward Audit Metrics

The primary horizon is fixed:

```text
primary_horizon = H20
```

The runner must also compute H10 and H60 sensitivity, but sensitivity metrics cannot be used for P0 proceed selection.

Required primary metrics by split / anchor_family / baseline:

| Metric | Role |
| --- | --- |
| `event_count` | sample size |
| `anchor_trigger_count` | trigger count |
| `anchor_trigger_rate_per_launch_episode` | trigger budget |
| `unique_instrument_count` | breadth |
| `unique_instrument_year_count` | breadth |
| `mean_after_cost_return_H20` | primary return |
| `median_after_cost_return_H20` | robustness |
| `p05_after_cost_return_H20` | tail risk |
| `max_adverse_excursion_mean_H20` | tail risk |
| `winner_capture_rate_50h120` | outcome audit |
| `winner_capture_rate_100h240` | sensitivity audit |
| `instrument_year_positive_rate` | stability |
| `top1_instrument_year_pnl_share` | concentration |
| `top5_instrument_exposure_share` | concentration |
| `failure_lookalike_rate` | false-positive audit |

Metric formulas:

```text
lifecycle_anchor_recall =
  count(train winner_50h120 episodes with at least one observable primary anchor candidate)
  / count(train winner_50h120 episodes with eligible_for_primary_gate = true)

anchor_trigger_rate_per_launch_episode =
  anchor_trigger_count
  / count(distinct EP2 launch_episode_id in the same split)

mean_after_cost_return_H20_diff_vs_matched_delay =
  anchor mean_after_cost_return_H20
  - matched_delay_baseline mean_after_cost_return_H20

p05_after_cost_return_H20_diff_vs_matched_delay =
  anchor p05_after_cost_return_H20
  - matched_delay_baseline p05_after_cost_return_H20

max_adverse_excursion_mean_H20_worsening_vs_matched_delay =
  max(
    0,
    matched_delay_baseline max_adverse_excursion_mean_H20
      - anchor max_adverse_excursion_mean_H20
  )

instrument_year_positive_rate =
  count(instrument-year groups with total after-cost H20 PnL > 0)
  / count(instrument-year groups with at least one event)

instrument_year_positive_rate_diff_vs_matched_delay =
  anchor instrument_year_positive_rate
  - matched_delay_baseline instrument_year_positive_rate

top1_instrument_year_pnl_share =
  max(positive instrument-year PnL)
  / sum(positive instrument-year PnL)

top5_instrument_exposure_share =
  sum(events in top 5 instruments by event_count)
  / total event_count

failure_lookalike_rate =
  failed_lookalike_baseline event_count
  / (primary_anchor_event_count + failed_lookalike_baseline event_count)

matched_delay_failure_rate =
  count(matched_delay_baseline rows satisfying failed_lookalike_baseline rule)
  / count(executable matched_delay_baseline rows)
```

`max_adverse_excursion_mean_H20` must be a negative return number. The worsening formula above is positive only when the anchor has a more negative mean MAE than the matched delay baseline.

Primary metric denominator rules:

```text
anchor-side rows:
  eligible_for_primary_gate = true
  is_executable_next_open = true
  dedupe_rank_within_reference_event = 1

pairwise baseline rows:
  linked anchor row satisfies all anchor-side rules
  baseline eligible_for_primary_gate = true
  baseline is_executable_next_open = true
  match_status in {matched, repaired}

non-pairwise baseline rows:
  eligible_for_primary_gate = true
  is_executable_next_open = true
  match_status != unavailable
```

## 15. Reports and Artifacts

All outputs must live under:

```text
ep3/engineering_baseline/outputs/
```

Required cache:

```text
cache/ep3_winner_label_panel.parquet
cache/ep3_candidate_anchor_panel.parquet
cache/ep3_matched_baseline_panel.parquet
```

Required reports:

```text
reports/ep3_input_authority.csv
reports/ep3_pit_coverage_audit.csv
reports/ep3_winner_lifecycle_profile.csv
reports/ep3_winner_cross_year_audit.csv
reports/ep3_anchor_window_freeze.csv
reports/ep3_observable_anchor_dictionary.csv
reports/ep3_matched_control_bucket_freeze.csv
reports/ep3_anchor_trigger_budget_audit.csv
reports/ep3_anchor_vs_matched_baseline.csv
reports/ep3_failure_lookalike_audit.csv
reports/ep3_instrument_year_lift_audit.csv
reports/ep3_regime_stability_audit.csv
reports/ep3_sensitivity_horizon_audit.csv
reports/ep3_preliminary_anchor_leads.csv
reports/ep3_gate_audit.csv
reports/ep3_discussion_report.md
reports/ep3_stage_order_audit.csv
```

Required manifest:

```text
manifests/ep3_engineering_baseline_manifest.json
```

## 16. Gate Semantics

Implementation success means artifacts and validator obey this requirement. Research success means an anchor family passes validation gates and remains acceptable on robustness without changing parameters.

Allowed statuses:

```text
passed_to_ep3_p1_anchor_validation
failed_no_clean_lifecycle_anchor
failed_trigger_budget
failed_forward_lift
failed_tail_risk
failed_concentration
failed_robustness
failed_contract_or_leakage
```

Precedence:

```text
failed_contract_or_leakage
failed_no_clean_lifecycle_anchor
failed_trigger_budget
failed_forward_lift
failed_tail_risk
failed_concentration
failed_robustness
passed_to_ep3_p1_anchor_validation
```

## 17. Proceed Gates

For an anchor family to enter `ep3_preliminary_anchor_leads.csv` as `lead_status = validation_passed`, it must pass all validation gates:

```text
lifecycle_anchor_recall >= 0.30
anchor_trigger_rate_per_launch_episode in [0.20, 1.50]
validation_unique_instrument_year_count >= 25
mean_after_cost_return_H20_diff_vs_matched_delay > 0
p05_after_cost_return_H20_diff_vs_matched_delay >= -0.003
max_adverse_excursion_mean_H20_worsening_vs_matched_delay <= 0.005
instrument_year_positive_rate_diff_vs_matched_delay >= 0
top1_instrument_year_pnl_share <= 0.20
top5_instrument_exposure_share <= 0.50
failure_lookalike_rate <= matched_delay_failure_rate
```

Robustness gates use the same frozen anchor definitions, windows, and baseline construction:

```text
robustness_mean_after_cost_return_H20_diff_vs_matched_delay >= -0.001
robustness_p05_after_cost_return_H20_diff_vs_matched_delay >= -0.005
robustness_anchor_trigger_rate_per_launch_episode in [0.20, 1.50]
robustness_top1_instrument_year_pnl_share <= 0.25
robustness_top5_instrument_exposure_share <= 0.55
```

If validation passes but robustness fails, status is `failed_robustness`.

## 18. Validator Requirements

The implementation must add a fail-closed validator:

```text
ep3/engineering_baseline/scripts/validate_ep3_engineering_baseline.py
```

The validator must fail on:

- missing required artifacts;
- schema mismatch;
- output written outside `ep3/engineering_baseline/outputs/`;
- use of R02 threshold / R03 confirmed pool / R05 policies as primary input;
- deferred anchor family producing P0 forward-audit rows;
- validation / robustness data used for train-only anchor window derivation;
- validation / robustness data used to derive matched-control bucket boundaries;
- validation / robustness outcomes consumed by any stage 1-5 derivation even if the label panel was already materialized;
- matched baseline lift computed inside winner-only lifecycle profiling;
- matched baseline panel row grain or baseline id construction not matching this requirement;
- primary gate metrics including rows with incomplete label horizon or horizon crossing split boundaries;
- label panel date range not matching required min/max and price hash scope;
- signal feature with `feature_asof_date > signal_date`;
- execution using same-close or execution-date high/low/close as signal;
- H10/H60 sensitivity used for primary selection;
- anchor candidate panel missing reference acceleration ids, formula version, parameter hash, or dedupe rank;
- anchor or baseline panel missing `eligible_for_primary_gate` / `label_join_status`;
- `matched_delay_baseline` not using `train_median_anchor_window_days` from `ep3_anchor_window_freeze.csv`;
- failed-lookalike rows not matching the exact family-specific one-failed-condition rules;
- deferred anchor families contributing rows or metrics in P0;
- trigger budget not enforced;
- trigger-rate denominator not based on distinct EP2 launch episodes in the same split;
- gate formulas using denominators different from Section 14;
- manifest hash mismatch;
- any failed hard gate incorrectly marked as passed.

## 19. Test Plan

Required commands:

```bash
uv run python ep3/engineering_baseline/scripts/run_ep3_engineering_baseline.py \
  --config ep3/engineering_baseline/config.yaml

uv run python ep3/engineering_baseline/scripts/validate_ep3_engineering_baseline.py \
  --config ep3/engineering_baseline/config.yaml

uv run python -m py_compile \
  ep3/engineering_baseline/scripts/run_ep3_engineering_baseline.py \
  ep3/engineering_baseline/scripts/validate_ep3_engineering_baseline.py
```

The final report must give a direct go/no-go judgment for EP3-P1:

```text
go: passed_to_ep3_p1_anchor_validation
no-go: any failed_* status
```

## 20. Implementation Notes

This requirement is ready for implementation as an EP3-P0 engineering baseline. Any later change to anchor families, primary horizon, trigger budget, matched-control construction, or proceed gates must update this requirement before rerunning artifacts.
