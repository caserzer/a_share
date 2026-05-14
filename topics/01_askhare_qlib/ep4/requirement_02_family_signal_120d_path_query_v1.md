# EP4 Requirement 02 Follow-up: Family Signal 120D Path Analysis For R03 Support V1

## 1. Requirement Metadata

- Requirement id: `ep4_r02_family_signal_120d_path_query_v1`
- Short name: `r02_family_signal_120d_path_query_v1`
- Status: implementation-ready path-analysis requirement
- Owner workflow: EP4
- Upstream requirement: `ep4/requirement_02_big_winner_coverage_ratio_search_v1.md`
- Upstream statistics requirement: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- Required output root: `ep4/outputs/r02_family_signal_120d_path_query_v1/`
- Required config path: `ep4/configs/r02_family_signal_120d_path_query_v1.yaml`
- Required runner path: `ep4/scripts/run_r02_family_signal_120d_path_query.py`
- Required validator path: `ep4/scripts/validate_r02_family_signal_120d_path_query.py`
- Date: 2026-05-14

## 2. Purpose

本需求做固定信号触发后的 120 个交易日路径分析，用于支持 R03 设计前的证据整理。

它不是 R03 promotion gate，也不直接产出交易策略；它必须把每个冻结信号触发后的真实可执行路径拆成：

- 早期不利波动是否过大；
- 上涨是否发生在止损式下跌之前；
- 最大涨幅是否只是窗口内不可持续的瞬时高点；
- 如果 R03 要继续，应该优先研究 entry delay、stop、take-profit、hold-window 还是信号本身。

它回答：

```text
给定 R02 已冻结的单 family 高覆盖条件，以及若干指定的 4-family 复核组合，
当信号在 action-time stock-day 触发后，
若下一交易日开盘建仓，
未来 120 个交易日内的固定截面收益、早期 MAE/MFE、先涨先跌 race、
水下时间、收益保持、最大回撤路径和每 10 日 ATR 是什么？
```

本需求不重新搜索条件，不估计 big-winner precision，不做交易策略、不做仓位分配，也不把结果解释为 R03 promotion。
它必须输出 R03 handoff diagnostics，明确哪些信号/组合值得进入 R03 设计假设，哪些应停止或仅保留为背景证据。

## 3. Hard Scope

允许：

- 使用 Section 4 固定的 7 个单 family 条件；
- 使用 Section 5 固定的 4 个复核组合；
- 在 R01 / R02 PIT-executable eligible stock-day 分母上重放信号；
- 对每个触发事件输出 120 个交易日路径指标；
- 每个信号输出一个独立 CSV；
- 输出 raw trigger 口径和 episode 审计口径；
- 输出非逐笔的跨信号聚合摘要、R03 handoff diagnostics 和 markdown 分析报告；
- 输出 manifest、validation audit 和必要的 signal dictionary。

禁止：

- 重新搜索阈值、窗口、family 或组合；
- 用本需求结果反向修改 Section 4 / Section 5 的信号定义；
- 生成合并所有信号的 row-level 主结果 CSV；每个信号的 raw trigger row-level 输出必须仍是独立 CSV；
- 在聚合摘要中隐藏 raw trigger 和 episode 口径的差异；
- 用 known big winner window 作为触发分母；
- 引入新的在线数据抓取；
- 把任一输出标记为 production entry、R03-ready、validated strategy 或可交易信号。

## 4. Frozen Single-Family Signals

以下 7 个单 family 信号必须逐字冻结。实现必须校验它们与上游 R02 coverage-search artifact 中的 condition group 一致。

| family | signal_id | condition | coverage | density | mean first hit | median first hit | split stability |
|:--|:--|:--|--:|--:|:--|:--|:--|
| `momentum_rps` | `single_momentum_rps` | `roc5_r02 >= 0.05 AND rps5_r02 >= 0.8 AND rps10_r02 >= 0.5` | 85.09% | 11.16% | T+9.2 | T+8 | robustness 83.82% below 85% |
| `oscillator` | `single_oscillator` | `kdj_k5_r02 >= 60 AND cci5_r02 >= 100 AND kdj_k10_r02 >= 55 AND cci10_r02 >= 150` | 85.09% | 5.85% | T+11.3 | T+11 | validation 82.91% below 85% |
| `price_trend` | `single_price_trend` | `close_over_ma5_r02 >= 0.03 AND ema_slope5_r02 >= 0.0 AND close_over_ma10_r02 >= 0.03` | 86.15% | 8.75% | T+9.3 | T+7 | validation 82.28% below 85% |
| `pullback_drawdown` | `single_pullback_drawdown` | `pullback_depth5_r02 >= -0.05 AND rebound_from_low5_r02 >= 0.05 AND days_since_high10_r02 <= 5` | 90.30% | 14.28% | T+8.8 | T+7 | all splits above 88% |
| `range_breakout` | `single_range_breakout` | `range_position5_r02 >= 0.9 AND new_high_flag10_r02 == 1.0 AND range_position10_r02 >= 0.7` | 96.80% | 17.37% | T+8.0 | T+7 | all splits above 95% |
| `volatility_band` | `single_volatility_band` | `boll_pct_b5_r02 >= 0.8 AND boll_width5_r02 >= 1.0 AND boll_width10_r02 >= 1.0 AND price_channel_position10_r02 >= 0.8` | 85.21% | 7.14% | T+10.1 | T+8 | train 83.41% below 85% |
| `volume_money` | `single_volume_money` | `volume_ratio5_r02 >= 1.5 AND money_zscore5_r02 >= 2.0 AND money_price_coherence5_r02 == 1.0 AND money_price_coherence10_r02 == 1.0` | 88.17% | 5.77% | T+11.8 | T+11 | all splits above 86% |

The `coverage`, `density`, `mean first hit`, `median first hit`, and `split stability` columns are source descriptors only. They must be copied to the signal dictionary for traceability, but must not be recomputed as new metrics or used to filter triggers in this query.

Validator must still read the upstream R02 coverage-search artifacts and verify:

- each `signal_id` maps to the intended upstream `condition_group_id`;
- each frozen condition text matches the upstream condition text after deterministic normalization;
- each source descriptor copied into the signal dictionary matches the upstream artifact value within explicit rounding tolerance.

This validation is identity / lineage checking, not a new coverage or density calculation.

## 5. Frozen Review Composite Signals

复核组合只允许以下 4 个。每个组合在同一 `instrument_id, trade_date` 上必须要求所有列出的 single-family signal 同日触发。

| signal_id | signal_type | required single-family signals |
|:--|:--|:--|
| `review_momentum_oscillator_pullback_volume` | `same_day_family_and4` | `momentum_rps, oscillator, pullback_drawdown, volume_money` |
| `review_oscillator_pullback_volatility_volume` | `same_day_family_and4` | `oscillator, pullback_drawdown, volatility_band, volume_money` |
| `review_momentum_oscillator_range_volume` | `same_day_family_and4` | `momentum_rps, oscillator, range_breakout, volume_money` |
| `review_momentum_pullback_volatility_volume` | `same_day_family_and4` | `momentum_rps, pullback_drawdown, volatility_band, volume_money` |

Composite signals are query objects only. They are not new searched conditions and must not be described as selected, validated, or production-ready.

## 6. Required Inputs

主输入必须来自本地已有 EP4 / R02 artifacts 和 PIT 行情数据：

- R02 eligible-day density panel: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_eligible_day_density_panel.parquet`
- R02 atomic condition dictionary: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/reports/r02_big_winner_coverage_atomic_condition_dictionary.csv`
- R02 candidate dictionary / all-results artifacts needed to validate the frozen conditions
- Local PIT daily OHLCV / amount data sufficient for:
  - signal recomputation or signal replay;
  - next-trading-day open price;
  - high / low / close path over 120 trading days after entry;
  - ATR calculation.
- EP4 split calendar and R01 / R02 PIT-executable eligible stock-day conventions.

No new online fetch is allowed.

## 7. Trigger And Entry Anchor

Primary trigger grain:

```text
instrument_id
signal_date
signal_id
```

`signal_date` is the trading day on which the single or composite signal is true using only data observable as of that day's close.

Primary entry anchor:

```text
entry_date = first R01 / EP4 executable trading date after signal_date for the same instrument
entry_price = open(instrument_id, entry_date)
```

Rationale: the frozen signals use same-day close-derived fields, so they are only fully known after `signal_date` close. All path returns in this requirement are therefore relative to `entry_price`, not `signal_date` close.

The entry date must pass the same local executable next-open filters used by EP4 where available, including at minimum:

- instrument is tradable and not suspended on `entry_date`;
- open price is present, finite, and positive;
- the daily bar is not marked dirty by the local EP4 data-quality rules;
- the row is not excluded by the existing R01 / R02 PIT-executable denominator;
- if local limit-up / limit-down executable flags exist, next-open buy feasibility must pass the existing EP4 rule.

If no executable `entry_date` is found, or if `entry_price` is unavailable / invalid, the trigger row must still be written with:

```text
entry_valid = false
entry_invalid_reason populated
all 120d path metrics null
```

## 8. Signal Deduplication

Default output grain is raw trigger stock-day. Consecutive signal days must not be collapsed in the primary per-signal CSV.

For this V1 requirement:

```yaml
primary_grain: raw_signal_stock_day
episode_collapse_enabled: true
episode_collapse_scope: audit_only
```

If the same signal triggers on the same instrument for consecutive days, every trigger gets its own CSV row and its own next-open entry anchor. This preserves the user's requested query semantics.

For interpretation and R03 support, the implementation must also produce an audit-only episode view:

```text
episode_id = deterministic hash(signal_id, instrument_id, split, episode_start_signal_date, episode_end_signal_date)
episode_start_signal_date = first consecutive signal_date in the episode
episode_end_signal_date = last consecutive signal_date in the episode
episode_trigger_count = number of raw trigger rows in the episode
episode_entry_date = entry_date of the first valid raw trigger in the episode
episode_entry_price = entry_price of the first valid raw trigger in the episode
```

Episode construction is per `signal_id, instrument_id, split`. A new episode starts when at least one instrument trading day exists between two trigger dates without the same signal firing, or when the split changes. Episode outputs are diagnostic only and must not replace the raw trigger stock-day CSVs.

Raw trigger CSVs must not expose post-hoc episode fields such as `episode_id`, `episode_end_signal_date`, or `episode_trigger_count`. These fields are future-derived because they depend on knowing when a run of consecutive triggers ends. They are allowed only in `reports/episode_signals/` and in aggregate summaries. R03 implementations must not use episode-audit fields as candidate inputs unless a later R03 requirement explicitly defines an online-safe episode state.

## 9. 120D Path Window

Primary path window:

```text
path_start = entry_date
path_end = entry_date + 120 trading days
path_dates = tradable instrument dates from path_start through path_end
path_offset(entry_date) = 0
path_offset(entry_date + N trading days) = N
```

This means a complete 120D path contains offsets `0, 1, ..., 120`, or `121` daily bars including the entry day. The user's requested 120-day forward metrics are evaluated through offset `120`; offset `0` is included only to anchor entry-day high / low / close, drawdown, and ATR.

The path is complete only when all trading days needed for T+120 metrics exist inside the same split boundary. Incomplete rows must remain in the per-signal CSV and must report:

- `path_complete_120d = false`
- `available_forward_trading_days`
- `path_incomplete_reason`

Metric-specific completeness is allowed. For example, a row with only 60 forward days can have ATR fields through T+60 populated while T+70 through T+120 remain null.

## 10. Required Path Metrics

All return fields are relative to `entry_price` unless the field name explicitly says otherwise.

### 10.1 First -5% Trigger

Primary -5% trigger uses intraday low:

```text
first_minus5_date =
  first date d in path_dates such that low(d) / entry_price - 1 <= -0.05
```

Required fields:

- `first_minus5_date`
- `first_minus5_offset`
- `first_minus5_low_return`
- `first_minus5_hit_flag`

Audit close-based fields must also be included:

- `first_close_minus5_date`
- `first_close_minus5_offset`
- `first_close_minus5_return`
- `first_close_minus5_hit_flag`

### 10.2 Maximum Gain And Maximum Loss

Maximum gain uses intraday high:

```text
max_gain_120d = max(high(d) / entry_price - 1 for d in path_dates)
max_gain_date = earliest date achieving max_gain_120d
max_gain_offset = trading-day offset from entry_date
```

Maximum loss uses intraday low:

```text
max_loss_120d = min(low(d) / entry_price - 1 for d in path_dates)
max_loss_date = earliest date achieving max_loss_120d
max_loss_offset = trading-day offset from entry_date
```

Required fields:

- `max_gain_120d`
- `max_gain_date`
- `max_gain_offset`
- `max_loss_120d`
- `max_loss_date`
- `max_loss_offset`

### 10.3 Maximum Drawdown Path

Maximum drawdown is the worst peak-to-trough decline inside the post-entry path. Because daily OHLC does not reveal intraday high / low ordering, the primary drawdown must not assume that a same-day high occurred before the same-day low.

The primary drawdown uses the best peak observable before the trough day, with `entry_price` as the initial peak candidate:

```text
running_peak_price_before_d(d) =
  max(entry_price, high(path_start), ..., high(previous trading day before d))

drawdown_at_d =
  low(d) / running_peak_price_before_d(d) - 1

max_drawdown_120d =
  min(drawdown_at_d for d in path_dates)
```

For `d = entry_date`, `running_peak_price_before_d = entry_price`.

Required fields:

- `max_drawdown_120d`
- `max_drawdown_start_date`
- `max_drawdown_end_date`
- `max_drawdown_start_offset`
- `max_drawdown_end_offset`
- `max_drawdown_peak_price`
- `max_drawdown_trough_price`
- `max_drawdown_trough_return_from_entry`
- `max_drawdown_ohlc_order_policy`: fixed value `prior_peak_only`

Tie-break rule:

```text
If multiple paths have the same max_drawdown_120d, choose:
  earliest max_drawdown_end_date,
  then earliest max_drawdown_start_date,
  then lowest signal_id lexical order for deterministic sorting only.
```

An implementation may output an audit-only same-day high-to-low drawdown diagnostic, but it must use a clearly named field such as `max_drawdown_same_day_hilo_diagnostic` and must not replace the primary `max_drawdown_120d`.

### 10.4 ATR Every 10 Trading Days

ATR must be computed from PIT daily OHLC using Wilder ATR with default period 14:

```yaml
atr_period: 14
atr_offsets: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
```

For every offset, output both raw ATR and ATR normalized by close:

```text
atr14_t{offset}
atr14_pct_t{offset} = atr14_t{offset} / close_t{offset}
```

If ATR cannot be computed at an offset because lookback is incomplete or the forward date is missing, the corresponding fields must be null and `atr_missing_offsets` must list the missing offsets.

### 10.5 Fixed-Horizon Close Returns

The implementation must output close-to-entry returns at fixed horizons:

```yaml
fixed_return_offsets: [1, 3, 5, 10, 20, 40, 60, 120]
```

For each offset `N`:

```text
close_return_t{N} = close(entry_date + N trading days) / entry_price - 1
```

Required fields:

- `close_return_t1`
- `close_return_t3`
- `close_return_t5`
- `close_return_t10`
- `close_return_t20`
- `close_return_t40`
- `close_return_t60`
- `close_return_t120`

If the offset is unavailable, the field must be null and the row must remain present.

### 10.6 Staged MAE / MFE

The implementation must measure adverse and favorable excursion at multiple windows, not only at T+120:

```yaml
excursion_offsets: [5, 10, 20, 40, 60, 120]
```

For each offset `N`:

```text
mae_low_t{N} = min(low(d) / entry_price - 1 for d in path_offsets 0..N)
mfe_high_t{N} = max(high(d) / entry_price - 1 for d in path_offsets 0..N)
```

Required fields:

- `mae_low_t5`, `mae_low_t10`, `mae_low_t20`, `mae_low_t40`, `mae_low_t60`, `mae_low_t120`
- `mfe_high_t5`, `mfe_high_t10`, `mfe_high_t20`, `mfe_high_t40`, `mfe_high_t60`, `mfe_high_t120`

ATR-normalized audit fields must also be produced when `atr14_pct_t0` is available:

```text
mae_atr_t{N} = mae_low_t{N} / atr14_pct_t0
mfe_atr_t{N} = mfe_high_t{N} / atr14_pct_t0
```

Required fields:

- `mae_atr_t5`, `mae_atr_t10`, `mae_atr_t20`, `mae_atr_t40`, `mae_atr_t60`, `mae_atr_t120`
- `mfe_atr_t5`, `mfe_atr_t10`, `mfe_atr_t20`, `mfe_atr_t40`, `mfe_atr_t60`, `mfe_atr_t120`

If `atr14_pct_t0` is null, zero, or invalid, ATR-normalized excursion fields must be null and `atr_missing_offsets` / validation audit must make the missingness visible.

All aggregate summaries using ATR-normalized fields must include explicit denominators:

```text
atr_t0_usable_count = count(rows where atr14_pct_t0 is finite and > 0)
atr_t0_usable_rate = atr_t0_usable_count / entry_valid_count when entry_valid_count > 0
```

If `entry_valid_count = 0`, `atr_t0_usable_rate` must be null and `atr_evidence_status` must be `low_coverage_audit_only`.

If `atr_t0_usable_rate < 0.80` for any `signal_id, grain`, the markdown report and R03 handoff diagnostics must mark ATR-derived evidence as `low_coverage_audit_only` for that row. ATR-derived metrics must not drive `recommended_r03_status` when `atr_t0_usable_rate < 0.80`.

### 10.7 Upside Thresholds And Race Metrics

The implementation must measure whether upside occurs before adverse drawdown. Upside threshold hits use intraday high:

```yaml
upside_thresholds: [0.05, 0.10, 0.20]
downside_race_thresholds: [-0.05, -0.10]
```

Required fields:

- `first_plus5_date`, `first_plus5_offset`, `first_plus5_high_return`, `first_plus5_hit_flag`
- `first_plus10_date`, `first_plus10_offset`, `first_plus10_high_return`, `first_plus10_hit_flag`
- `first_plus20_date`, `first_plus20_offset`, `first_plus20_high_return`, `first_plus20_hit_flag`
- `first_minus10_date`, `first_minus10_offset`, `first_minus10_low_return`, `first_minus10_hit_flag`
- `hit_plus5_before_minus5`
- `hit_plus10_before_minus5`
- `hit_plus20_before_minus10`
- `minus5_before_plus10`
- `race_plus5_minus5_status`
- `race_plus10_minus5_status`
- `race_plus20_minus10_status`

Race boolean fields must be paired with status fields so censoring is not confused with failure. Allowed race status values:

- `upside_first`: upside threshold was hit before the paired downside threshold;
- `downside_first`: downside threshold was hit before the paired upside threshold;
- `same_offset`: both thresholds were hit on the same trading-day offset and daily OHLC cannot determine intraday ordering;
- `upside_only_complete`: upside threshold was hit, downside threshold was not hit, and path is complete for the comparison horizon;
- `downside_only_complete`: downside threshold was hit, upside threshold was not hit, and path is complete for the comparison horizon;
- `neither_hit_complete`: neither threshold was hit and path is complete for the comparison horizon;
- `censored_incomplete`: ordering is unresolved because the available path is incomplete.

The default comparison horizon for every race pair is T+120. If both sides are hit inside the available path, status must be decided by offsets even when `path_complete_120d = false`. If one or both sides are not hit and `path_complete_120d = false`, status must be `censored_incomplete`. If neither side is hit and `path_complete_120d = true`, status must be `neither_hit_complete`.

The boolean race fields are interpreted as:

```text
true  when status in {upside_first, upside_only_complete}
false when status in {downside_first, downside_only_complete, neither_hit_complete}
null  when status in {same_offset, censored_incomplete}
```

`minus5_before_plus10` must be mechanically derived from `race_plus10_minus5_status` and must not be independently computed:

```text
true  when race_plus10_minus5_status in {downside_first, downside_only_complete}
false when race_plus10_minus5_status in {upside_first, upside_only_complete, neither_hit_complete}
null  when race_plus10_minus5_status in {same_offset, censored_incomplete}
```

This prevents incomplete paths and same-day OHLC ambiguity from being counted as clean failures or successes.

### 10.8 Pain Before Profit

For R03 entry/stop design, the implementation must show how much adverse movement occurs before the first meaningful upside event:

```text
max_loss_before_first_plus10 =
  min(low(d) / entry_price - 1 for d in path_start through first_plus10_date)

max_loss_before_first_plus10_offset =
  earliest trading-day offset achieving max_loss_before_first_plus10
```

If `first_plus10_hit_flag = false`, compute the field through the available path window and set `max_loss_before_first_plus10_censored = true`.

The drawdown-before-profit field must use the same prior-peak drawdown convention as Section 10.3:

```text
max_drawdown_before_first_plus20_end_date =
  first_plus20_date if first_plus20_hit_flag = true
  else last available path date

max_drawdown_before_first_plus20_eval_end_offset =
  trading-day offset of max_drawdown_before_first_plus20_end_date from entry_date

max_drawdown_before_first_plus20 =
  min(drawdown_at_d for d in path_start through max_drawdown_before_first_plus20_end_date)

max_drawdown_before_first_plus20_end_offset =
  earliest trading-day offset of the trough date achieving max_drawdown_before_first_plus20
```

If `first_plus20_hit_flag = false`, compute `max_drawdown_before_first_plus20` through the available path window and set `max_drawdown_before_first_plus20_censored = true`. If `first_plus20_hit_flag = true`, set `max_drawdown_before_first_plus20_censored = false`. If no valid path date is available, all drawdown-before-first-plus20 fields must be null and the censored flag must be true.

Required fields:

- `max_loss_before_first_plus10`
- `max_loss_before_first_plus10_offset`
- `max_loss_before_first_plus10_censored`
- `max_drawdown_before_first_plus20`
- `max_drawdown_before_first_plus20_end_offset`
- `max_drawdown_before_first_plus20_eval_end_offset`
- `max_drawdown_before_first_plus20_censored`

These fields must use the same entry-price and prior-peak drawdown conventions as Sections 10.2 and 10.3.

### 10.9 Underwater Time And Gain Retention

The implementation must distinguish sustained paths from paths that only make a transient high:

Required fields:

- `days_close_below_entry_120d`
- `share_days_close_below_entry_120d`
- `max_consecutive_days_close_below_entry_120d`
- `first_recover_entry_date`
- `first_recover_entry_offset`
- `close_t120_above_entry_flag`
- `peak_to_t120_giveback`
- `close_return_20d_after_max_gain`

Definitions:

```text
days_close_below_entry_120d =
  count(path_dates where close(d) < entry_price)

share_days_close_below_entry_120d =
  days_close_below_entry_120d / number of available path dates

first_recover_entry_date =
  first date after the first close below entry_price where close(d) >= entry_price

peak_to_t120_giveback =
  close_t120 / max_high_price_120d - 1

close_return_20d_after_max_gain =
  close(max_gain_date + 20 trading days) / close(max_gain_date) - 1
```

If T+120 or T+20 after max gain is unavailable, the corresponding field must be null and completeness audit must record it.

### 10.10 Path Quality Classification

Each row must receive deterministic descriptive flags. These are not promotion labels and must not be used to refit Section 4 / Section 5 signals inside this requirement.

Required fields:

- `path_quality_flag`
- `early_failure_flag`
- `tradable_continuation_flag`
- `transient_spike_flag`
- `severe_drawdown_flag`
- `whipsaw_after_profit_flag`
- `clean_continuation_flag`
- `late_drawdown_flag`
- `incomplete_flag`

Default definitions:

```text
early_failure_flag =
  first_minus5_hit_flag == true AND first_minus5_offset <= 10

incomplete_flag =
  path_complete_120d == false
  OR any required input for path_quality_flag is null

tradable_continuation_flag =
  hit_plus10_before_minus5 == true AND close_return_t20 >= 0

transient_spike_flag =
  max_gain_120d >= 0.20 AND close_return_t120 < 0

severe_drawdown_flag =
  max_drawdown_120d <= -0.20

whipsaw_after_profit_flag =
  first_plus10_hit_flag == true
  AND first_minus5_hit_flag == true
  AND first_plus10_offset < first_minus5_offset
  AND first_minus5_offset <= first_plus10_offset + 20

clean_continuation_flag =
  hit_plus10_before_minus5 == true
  AND close_return_t20 >= 0
  AND max_drawdown_before_first_plus20 > -0.10

late_drawdown_flag =
  first_plus10_hit_flag == true
  AND max_drawdown_120d <= -0.20
  AND max_drawdown_end_offset > first_plus10_offset
```

For `incomplete_flag`, the required input set is exactly:

- `path_complete_120d`
- `first_minus5_hit_flag`
- `first_minus5_offset` when `first_minus5_hit_flag = true`
- `hit_plus10_before_minus5`
- `close_return_t20`
- `max_gain_120d`
- `close_return_t120`
- `max_drawdown_120d`
- `first_plus10_hit_flag`
- `first_plus10_offset` when `first_plus10_hit_flag = true`
- `max_drawdown_before_first_plus20`
- `max_drawdown_end_offset`

`path_quality_flag` must be one of:

- `early_failure`
- `clean_continuation`
- `whipsaw_after_profit`
- `tradable_continuation`
- `transient_spike`
- `late_drawdown`
- `severe_drawdown`
- `mixed`
- `incomplete`

Tie-break order:

```text
incomplete > early_failure > clean_continuation > whipsaw_after_profit > tradable_continuation > transient_spike > late_drawdown > severe_drawdown > mixed
```

## 11. Required Per-Signal CSV Schema

Each signal must produce exactly one path CSV under:

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/signals/{signal_id}_120d_path.csv
```

Required row fields:

- `signal_id`
- `signal_type`: `single_family` or `same_day_family_and4`
- `family_id`: populated for single-family signals, null for composite signals
- `required_family_set`: pipe-delimited for composite signals
- `instrument_id`
- `signal_date`
- `split`
- `entry_date`
- `entry_price`
- `entry_valid`
- `entry_invalid_reason`
- `path_complete_120d`
- `available_forward_trading_days`
- `path_incomplete_reason`
- `first_minus5_date`
- `first_minus5_offset`
- `first_minus5_low_return`
- `first_minus5_hit_flag`
- `first_close_minus5_date`
- `first_close_minus5_offset`
- `first_close_minus5_return`
- `first_close_minus5_hit_flag`
- `max_gain_120d`
- `max_gain_date`
- `max_gain_offset`
- `max_loss_120d`
- `max_loss_date`
- `max_loss_offset`
- `max_drawdown_120d`
- `max_drawdown_start_date`
- `max_drawdown_end_date`
- `max_drawdown_start_offset`
- `max_drawdown_end_offset`
- `max_drawdown_peak_price`
- `max_drawdown_trough_price`
- `max_drawdown_trough_return_from_entry`
- `max_drawdown_ohlc_order_policy`
- `atr_missing_offsets`
- `atr14_t0`
- `atr14_pct_t0`
- `atr14_t10`
- `atr14_pct_t10`
- `atr14_t20`
- `atr14_pct_t20`
- `atr14_t30`
- `atr14_pct_t30`
- `atr14_t40`
- `atr14_pct_t40`
- `atr14_t50`
- `atr14_pct_t50`
- `atr14_t60`
- `atr14_pct_t60`
- `atr14_t70`
- `atr14_pct_t70`
- `atr14_t80`
- `atr14_pct_t80`
- `atr14_t90`
- `atr14_pct_t90`
- `atr14_t100`
- `atr14_pct_t100`
- `atr14_t110`
- `atr14_pct_t110`
- `atr14_t120`
- `atr14_pct_t120`
- `close_return_t1`
- `close_return_t3`
- `close_return_t5`
- `close_return_t10`
- `close_return_t20`
- `close_return_t40`
- `close_return_t60`
- `close_return_t120`
- `mae_low_t5`
- `mae_low_t10`
- `mae_low_t20`
- `mae_low_t40`
- `mae_low_t60`
- `mae_low_t120`
- `mfe_high_t5`
- `mfe_high_t10`
- `mfe_high_t20`
- `mfe_high_t40`
- `mfe_high_t60`
- `mfe_high_t120`
- `mae_atr_t5`
- `mae_atr_t10`
- `mae_atr_t20`
- `mae_atr_t40`
- `mae_atr_t60`
- `mae_atr_t120`
- `mfe_atr_t5`
- `mfe_atr_t10`
- `mfe_atr_t20`
- `mfe_atr_t40`
- `mfe_atr_t60`
- `mfe_atr_t120`
- `first_plus5_date`
- `first_plus5_offset`
- `first_plus5_high_return`
- `first_plus5_hit_flag`
- `first_plus10_date`
- `first_plus10_offset`
- `first_plus10_high_return`
- `first_plus10_hit_flag`
- `first_plus20_date`
- `first_plus20_offset`
- `first_plus20_high_return`
- `first_plus20_hit_flag`
- `first_minus10_date`
- `first_minus10_offset`
- `first_minus10_low_return`
- `first_minus10_hit_flag`
- `hit_plus5_before_minus5`
- `hit_plus10_before_minus5`
- `hit_plus20_before_minus10`
- `minus5_before_plus10`
- `race_plus5_minus5_status`
- `race_plus10_minus5_status`
- `race_plus20_minus10_status`
- `max_loss_before_first_plus10`
- `max_loss_before_first_plus10_offset`
- `max_loss_before_first_plus10_censored`
- `max_drawdown_before_first_plus20`
- `max_drawdown_before_first_plus20_end_offset`
- `max_drawdown_before_first_plus20_eval_end_offset`
- `max_drawdown_before_first_plus20_censored`
- `days_close_below_entry_120d`
- `share_days_close_below_entry_120d`
- `max_consecutive_days_close_below_entry_120d`
- `first_recover_entry_date`
- `first_recover_entry_offset`
- `close_t120_above_entry_flag`
- `peak_to_t120_giveback`
- `close_return_20d_after_max_gain`
- `path_quality_flag`
- `early_failure_flag`
- `tradable_continuation_flag`
- `transient_spike_flag`
- `severe_drawdown_flag`
- `whipsaw_after_profit_flag`
- `clean_continuation_flag`
- `late_drawdown_flag`
- `incomplete_flag`

Required episode-audit CSV row fields under `reports/episode_signals/{signal_id}_120d_episode_audit.csv`:

- `signal_id`
- `signal_type`
- `family_id`
- `required_family_set`
- `instrument_id`
- `split`
- `episode_id`
- `episode_start_signal_date`
- `episode_end_signal_date`
- `episode_trigger_count`
- `first_raw_signal_date`
- `last_raw_signal_date`
- `episode_entry_date`
- `episode_entry_price`
- `episode_entry_valid`
- `episode_entry_invalid_reason`
- all path metric fields from the first valid raw trigger row in the episode, using the same field names as the per-signal CSV
- `episode_path_quality_flag`

If an episode has no valid raw trigger entry, `episode_entry_valid = false`, `episode_entry_invalid_reason` must be populated, and path metric fields must be null.

Raw trigger rows must be sorted by:

```text
instrument_id asc,
signal_date asc,
signal_id asc
```

Episode audit rows must be sorted by:

```text
instrument_id asc,
episode_start_signal_date asc,
signal_id asc
```

No merged all-signal row-level result CSV is allowed. The per-signal CSV is the only raw trigger row-level path output format for this requirement. Non-row-level aggregate summary CSVs required in Section 12 are allowed and required.

## 12. Required Artifacts

The output bundle must contain:

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/
  manifests/
    r02_family_signal_120d_path_query_manifest.json
    r02_family_signal_120d_path_query_validation.json
  reports/
    r02_family_signal_120d_signal_dictionary.csv
    r02_family_signal_120d_validation_audit.csv
    r02_family_signal_120d_path_quality_summary.csv
    r02_family_signal_120d_episode_summary.csv
    r02_family_signal_120d_r03_handoff_diagnostics.csv
    r02_family_signal_120d_path_analysis_report.md
    signals/
      single_momentum_rps_120d_path.csv
      single_oscillator_120d_path.csv
      single_price_trend_120d_path.csv
      single_pullback_drawdown_120d_path.csv
      single_range_breakout_120d_path.csv
      single_volatility_band_120d_path.csv
      single_volume_money_120d_path.csv
      review_momentum_oscillator_pullback_volume_120d_path.csv
      review_oscillator_pullback_volatility_volume_120d_path.csv
      review_momentum_oscillator_range_volume_120d_path.csv
      review_momentum_pullback_volatility_volume_120d_path.csv
    episode_signals/
      single_momentum_rps_120d_episode_audit.csv
      single_oscillator_120d_episode_audit.csv
      single_price_trend_120d_episode_audit.csv
      single_pullback_drawdown_120d_episode_audit.csv
      single_range_breakout_120d_episode_audit.csv
      single_volatility_band_120d_episode_audit.csv
      single_volume_money_120d_episode_audit.csv
      review_momentum_oscillator_pullback_volume_120d_episode_audit.csv
      review_oscillator_pullback_volatility_volume_120d_episode_audit.csv
      review_momentum_oscillator_range_volume_120d_episode_audit.csv
      review_momentum_pullback_volatility_volume_120d_episode_audit.csv
```

The markdown report is required, but it must be descriptive and data-backed. It must include:

- raw trigger vs episode口径差异；
- 每个信号的 early failure、tradable continuation、transient spike、severe drawdown 比例；
- 固定截面收益分布；
- MAE/MFE 分布；
- race metric 分布和 censored / same-offset 比例；
- ATR 缺失率、usable rate 和 low-coverage audit-only 标记；
- R03 handoff conclusion: `continue_to_r03_design`, `needs_entry_delay_or_stop_design`, `background_only`, or `stop_candidate`.
- R03 handoff status basis metrics and blocker / opportunity explanation.

The report must not call any signal `production-ready`, `R03-ready`, `validated strategy`, `buy signal`, `可交易信号`, or `已验证策略`.

### 12.1 Aggregate Summary Schemas

`r02_family_signal_120d_path_quality_summary.csv` must contain one row per `signal_id, signal_type, grain`, where `grain` is `raw_trigger` or `episode_first_trigger`.

Required fields:

- `signal_id`
- `signal_type`
- `grain`
- `row_count`
- `episode_count`
- `entry_valid_count`
- `path_complete_120d_count`
- `entry_invalid_rate`
- `path_incomplete_rate`
- `atr_t0_missing_rate`
- `atr_t0_usable_count`
- `atr_t0_usable_rate`
- `atr_evidence_status`
- `first_minus5_hit_rate`
- `first_minus5_t10_rate`
- `first_plus10_hit_rate`
- `hit_plus10_before_minus5_rate`
- `hit_plus20_before_minus10_rate`
- `race_plus10_minus5_censored_rate`
- `race_plus20_minus10_censored_rate`
- `early_failure_rate`
- `clean_continuation_rate`
- `whipsaw_after_profit_rate`
- `tradable_continuation_rate`
- `transient_spike_rate`
- `late_drawdown_rate`
- `severe_drawdown_rate`
- `close_return_t20_p25`, `close_return_t20_p50`, `close_return_t20_p75`
- `close_return_t60_p25`, `close_return_t60_p50`, `close_return_t60_p75`
- `close_return_t120_p25`, `close_return_t120_p50`, `close_return_t120_p75`
- `mae_low_t10_p50`, `mae_low_t20_p50`, `mae_low_t120_p50`
- `mfe_high_t10_p50`, `mfe_high_t20_p50`, `mfe_high_t120_p50`
- `max_drawdown_120d_p50`
- `peak_to_t120_giveback_p50`

`r02_family_signal_120d_episode_summary.csv` must contain one row per `signal_id` and include:

- `signal_id`
- `signal_type`
- `raw_trigger_row_count`
- `episode_count`
- `episode_compression_ratio = episode_count / raw_trigger_row_count`
- `episode_trigger_count_p50`
- `episode_trigger_count_p90`
- `episode_entry_valid_count`
- `episode_path_complete_120d_count`
- `episode_atr_t0_usable_count`
- `episode_atr_t0_usable_rate`
- `episode_early_failure_rate`
- `episode_clean_continuation_rate`
- `episode_whipsaw_after_profit_rate`
- `episode_tradable_continuation_rate`
- `episode_transient_spike_rate`
- `episode_late_drawdown_rate`
- `episode_severe_drawdown_rate`
- `episode_hit_plus10_before_minus5_rate`
- `episode_close_return_t20_p50`
- `episode_close_return_t60_p50`
- `episode_close_return_t120_p50`
- `episode_mae_low_t20_p50`
- `episode_mfe_high_t20_p50`
- `episode_max_drawdown_120d_p50`

`r02_family_signal_120d_r03_handoff_diagnostics.csv` must contain one row per `signal_id` and include:

- `signal_id`
- `raw_trigger_row_count`
- `episode_count`
- `episode_compression_ratio`
- `recommended_r03_status`
- `primary_blocker`
- `primary_opportunity`
- `status_basis_metrics`
- `atr_evidence_status`
- `needs_entry_delay_test`
- `needs_stop_loss_test`
- `needs_take_profit_test`
- `needs_hold_window_test`
- `notes`

Allowed `recommended_r03_status` values:

- `continue_to_r03_design`
- `needs_entry_delay_or_stop_design`
- `background_only`
- `stop_candidate`

These statuses are analysis handoff labels only. They must not be interpreted as final promotion decisions.

`primary_blocker` and `primary_opportunity` are mandatory string fields. When a branch does not set one of them, the unset field must be the literal value `none`.

### 12.2 R03 Handoff Policy

`recommended_r03_status` must be computed deterministically from the `episode_first_trigger` grain in `r02_family_signal_120d_path_quality_summary.csv`, not from raw trigger rows. Raw trigger metrics may be shown as supporting evidence only. In `path_quality_summary.csv`, `episode_count` must equal `row_count` when `grain = episode_first_trigger`; for `grain = raw_trigger`, `episode_count` must be null.

Default handoff thresholds:

```yaml
min_episode_count_for_handoff: 200
min_path_complete_rate: 0.70
min_atr_usable_rate_for_atr_evidence: 0.80
continue_min_hit_plus10_before_minus5_rate: 0.45
continue_max_early_failure_rate: 0.35
continue_max_severe_drawdown_rate: 0.55
continue_min_close_return_t20_p50: 0.00
stop_min_early_failure_rate: 0.55
stop_max_hit_plus10_before_minus5_rate: 0.30
background_max_episode_count: 199
```

Status assignment order:

```text
if episode_count <= background_max_episode_count:
  recommended_r03_status = background_only
  primary_blocker = insufficient_episode_sample

else if entry_valid_count == 0:
  recommended_r03_status = background_only
  primary_blocker = no_valid_executable_entries

else if path_complete_120d_count / entry_valid_count < min_path_complete_rate:
  recommended_r03_status = background_only
  primary_blocker = insufficient_complete_path_sample

else if early_failure_rate >= stop_min_early_failure_rate
        AND hit_plus10_before_minus5_rate <= stop_max_hit_plus10_before_minus5_rate:
  recommended_r03_status = stop_candidate
  primary_blocker = early_failure_without_enough_prior_upside

else if hit_plus10_before_minus5_rate >= continue_min_hit_plus10_before_minus5_rate
        AND early_failure_rate <= continue_max_early_failure_rate
        AND severe_drawdown_rate <= continue_max_severe_drawdown_rate
        AND close_return_t20_p50 >= continue_min_close_return_t20_p50:
  recommended_r03_status = continue_to_r03_design
  primary_opportunity = clean_continuation_candidate

else if first_plus10_hit_rate >= 0.40
        OR mfe_high_t20_p50 >= 0.10
        OR transient_spike_rate >= 0.25:
  recommended_r03_status = needs_entry_delay_or_stop_design
  primary_opportunity = upside_exists_but_path_needs_risk_design

else:
  recommended_r03_status = background_only
  primary_blocker = no_clear_path_edge
```

When any metric in a comparison is null, that comparison must evaluate to `false`, except for the explicit `entry_valid_count == 0` branch. This makes the handoff policy deterministic for sparse or incomplete outputs.

`needs_entry_delay_test`, `needs_stop_loss_test`, `needs_take_profit_test`, and `needs_hold_window_test` must also be deterministic:

```text
needs_entry_delay_test = early_failure_rate >= 0.35 OR first_minus5_t10_rate >= 0.35
needs_stop_loss_test = severe_drawdown_rate >= 0.45 OR max_drawdown_120d_p50 <= -0.15
needs_take_profit_test = transient_spike_rate >= 0.25 OR peak_to_t120_giveback_p50 <= -0.20
needs_hold_window_test = close_return_t20_p50 >= 0 AND close_return_t120_p50 < close_return_t20_p50
```

`status_basis_metrics` must list the exact metric values and thresholds that determined the status in a deterministic semicolon-delimited form, for example:

```text
episode_count=421>=200; hit_plus10_before_minus5_rate=0.48>=0.45; early_failure_rate=0.31<=0.35
```

If `atr_t0_usable_rate < min_atr_usable_rate_for_atr_evidence`, set `atr_evidence_status = low_coverage_audit_only`; otherwise set `atr_evidence_status = usable`. ATR-derived metrics must not appear in `status_basis_metrics` when `atr_evidence_status = low_coverage_audit_only`.

## 13. Manifest Requirements

Manifest must include:

- `phase`
- `generated_at`
- `requirement_path`
- `config_path`
- `config_hash`
- `output_root`
- `upstream_r02_output_root`
- `upstream_r02_manifest_path`
- `upstream_r02_manifest_hash`
- `single_signal_count = 7`
- `review_composite_signal_count = 4`
- `total_signal_count = 11`
- `primary_grain = raw_signal_stock_day`
- `entry_anchor = first_executable_next_open_after_signal_date`
- `entry_executable_filter_policy`
- `path_horizon_trading_days = 120`
- `minus5_trigger_price = low`
- `atr_method = wilder`
- `atr_period = 14`
- `atr_offsets`
- `per_signal_csv_paths`
- `per_signal_episode_audit_paths`
- `per_signal_row_counts`
- `per_signal_episode_counts`
- `per_signal_entry_invalid_counts`
- `per_signal_incomplete_120d_counts`
- `path_quality_summary_path`
- `episode_summary_path`
- `r03_handoff_diagnostics_path`
- `path_analysis_report_path`
- `fixed_return_offsets`
- `excursion_offsets`
- `upside_thresholds`
- `downside_race_thresholds`
- `path_quality_classification_policy`
- `race_status_policy`
- `atr_evidence_policy`
- `r03_handoff_policy`
- `r03_handoff_thresholds`
- `r03_handoff_boundary = descriptive_analysis_only`
- `validation_status`

## 14. Validation Gates

Validator must fail closed if:

- any required signal from Section 4 or Section 5 is missing;
- any extra signal is produced;
- any single-family condition text differs from Section 4;
- any composite signal uses OR, lagged family confirmation, non-same-day matching, or a family outside Section 5;
- any per-signal CSV is missing;
- any per-signal CSV lacks required columns;
- any per-signal raw trigger CSV contains post-hoc episode fields such as `episode_id`, `episode_end_signal_date`, or `episode_trigger_count`;
- any required episode-audit CSV is missing;
- any required episode-audit CSV lacks required columns;
- any episode is constructed across split boundaries;
- any required aggregate summary CSV is missing;
- any required aggregate summary CSV lacks required columns;
- any merged row-level all-signal CSV is generated, including files matching `reports/*all*signal*.csv`, `reports/*merged*.csv`, or any CSV outside `reports/signals/` / `reports/episode_signals/` that contains `instrument_id`, `signal_date`, and row-level path metric columns;
- the markdown analysis report is missing;
- the markdown analysis report uses forbidden promotion language;
- `entry_valid = true` but `entry_date` is not strictly after `signal_date`;
- `entry_date` does not pass the required executable next-open filters when those local filter fields are available;
- `entry_valid = false` but path metric fields are populated;
- path return fields are computed relative to `signal_date` close instead of `entry_price`;
- `first_minus5_date` uses close rather than low for the primary field;
- max gain uses close rather than high;
- max loss uses close rather than low;
- max drawdown omits `entry_price` as the initial peak candidate or assumes same-day high-before-low ordering for the primary field;
- fixed-horizon returns use high/low instead of close;
- MAE uses close instead of low, or MFE uses close instead of high;
- race metrics use close for primary plus/minus threshold hits;
- race boolean fields are not consistent with their paired race status fields;
- `minus5_before_plus10` is not mechanically derived from `race_plus10_minus5_status`;
- race status fields contain values outside Section 10.7;
- race status fields do not use T+120 as the comparison horizon or fail to mark unresolved incomplete-path comparisons as `censored_incomplete`;
- `max_drawdown_before_first_plus20` does not use the Section 10.3 prior-peak drawdown convention, or its censored fields are inconsistent with Section 10.8;
- `max_loss_before_first_plus10_offset` is not the earliest offset achieving `max_loss_before_first_plus10`;
- `max_drawdown_before_first_plus20_end_offset` is not the earliest trough offset achieving `max_drawdown_before_first_plus20`, or `max_drawdown_before_first_plus20_eval_end_offset` is not the evaluation window end offset;
- path quality flags are computed with a different policy than Section 10.10 without manifest disclosure;
- `incomplete_flag` is inconsistent with Section 10.10 or `path_quality_flag = incomplete` is missing when `incomplete_flag = true`;
- episode audit rows replace or filter the required raw trigger rows;
- aggregate summary files mix raw trigger and episode grains without an explicit `grain` field;
- `path_quality_summary.csv` has `grain = episode_first_trigger` rows where `episode_count != row_count`, or raw-trigger rows where `episode_count` is non-null;
- ATR-derived aggregate metrics omit usable denominators or drive handoff status when `atr_evidence_status = low_coverage_audit_only`;
- `entry_valid_count = 0` but `atr_t0_usable_rate` is non-null or `atr_evidence_status` is not `low_coverage_audit_only`;
- `recommended_r03_status`, `needs_*_test`, `primary_blocker`, or `primary_opportunity` violate the deterministic Section 12.2 handoff policy;
- `primary_blocker` or `primary_opportunity` is empty instead of a policy value or `none`;
- `status_basis_metrics` is missing for any handoff row or includes ATR-derived metrics when ATR evidence is low coverage;
- ATR uses a non-Wilder method or non-14 period without explicit config and manifest disclosure;
- rows are filtered by future 120d path availability instead of retained with completeness flags;
- outputs depend on known big winner membership, reference-date windows, or future labels.

## 15. Interpretation Boundary

This analysis is descriptive path evidence only. It may be used to inspect whether the existing high-coverage family states tend to incur early adverse excursion, delayed continuation, transient spikes, recoverable pullbacks, or excessive post-entry drawdown.

It may support R03 by producing explicit handoff hypotheses such as:

- the signal is too failure-prone and should stop;
- the signal may require delayed entry;
- the signal may require early stop / risk-budget design;
- the signal may require take-profit or trailing-stop design because upside is transient;
- the signal has enough path quality to justify a formal R03 executable strategy requirement.

It must not be used as a standalone strategy validation or as a promotion gate without a separate R03 requirement that defines executable entry, exit, risk budget, portfolio construction, out-of-sample decision rules, and final go/no-go metrics.
