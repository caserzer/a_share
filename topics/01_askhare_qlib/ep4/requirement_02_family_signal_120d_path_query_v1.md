# EP4 Requirement 02 Follow-up: Family Signal 120D Path Query V1

## 1. Requirement Metadata

- Requirement id: `ep4_r02_family_signal_120d_path_query_v1`
- Short name: `r02_family_signal_120d_path_query_v1`
- Status: implementation-ready query requirement
- Owner workflow: EP4
- Upstream requirement: `ep4/requirement_02_big_winner_coverage_ratio_search_v1.md`
- Upstream statistics requirement: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- Required output root: `ep4/outputs/r02_family_signal_120d_path_query_v1/`
- Required config path: `ep4/configs/r02_family_signal_120d_path_query_v1.yaml`
- Required runner path: `ep4/scripts/run_r02_family_signal_120d_path_query.py`
- Required validator path: `ep4/scripts/validate_r02_family_signal_120d_path_query.py`
- Date: 2026-05-13

## 2. Purpose

本需求只做固定信号触发后的 120 个交易日路径查询。

它回答：

```text
给定 R02 已冻结的单 family 高覆盖条件，以及若干指定的 4-family 复核组合，
当信号在 action-time stock-day 触发后，
若下一交易日开盘建仓，
未来 120 个交易日内第一次触及 -5%、最大涨幅、最大跌幅、最大回撤路径和每 10 日 ATR 是什么？
```

本需求不重新搜索条件，不估计 precision，不生成 markdown report，不做交易策略、不做仓位分配，也不把结果解释为 R03 promotion。

## 3. Hard Scope

允许：

- 使用 Section 4 固定的 7 个单 family 条件；
- 使用 Section 5 固定的 4 个复核组合；
- 在 R01 / R02 PIT-executable eligible stock-day 分母上重放信号；
- 对每个触发事件输出 120 个交易日路径指标；
- 每个信号输出一个独立 CSV；
- 输出 manifest、validation audit 和必要的 signal dictionary。

禁止：

- 重新搜索阈值、窗口、family 或组合；
- 用本需求结果反向修改 Section 4 / Section 5 的信号定义；
- 输出 markdown final report；
- 生成合并所有信号的主结果 CSV；每个信号必须是一个独立 CSV；
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

Default output grain is raw trigger stock-day. Do not collapse consecutive signal days unless config explicitly enables an audit-only episode mode.

For this V1 requirement:

```yaml
primary_grain: raw_signal_stock_day
episode_collapse_enabled: false
```

If the same signal triggers on the same instrument for consecutive days, every trigger gets its own CSV row and its own next-open entry anchor. This preserves the user's requested query semantics.

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

Rows must be sorted by:

```text
instrument_id asc,
signal_date asc,
signal_id asc
```

No merged all-signal result CSV is allowed. The per-signal CSV is the only row-level path output format for this requirement.

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
```

No markdown report is allowed for this requirement.

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
- `per_signal_row_counts`
- `per_signal_entry_invalid_counts`
- `per_signal_incomplete_120d_counts`
- `validation_status`

## 14. Validation Gates

Validator must fail closed if:

- any required signal from Section 4 or Section 5 is missing;
- any extra signal is produced;
- any single-family condition text differs from Section 4;
- any composite signal uses OR, lagged family confirmation, non-same-day matching, or a family outside Section 5;
- any per-signal CSV is missing;
- any per-signal CSV lacks required columns;
- any merged row-level all-signal CSV is generated, including files matching `reports/*all*signal*.csv`, `reports/*merged*.csv`, or any CSV outside `reports/signals/` that contains `instrument_id`, `signal_date`, and path metric columns;
- a markdown report is generated under the output root;
- `entry_valid = true` but `entry_date` is not strictly after `signal_date`;
- `entry_date` does not pass the required executable next-open filters when those local filter fields are available;
- `entry_valid = false` but path metric fields are populated;
- path return fields are computed relative to `signal_date` close instead of `entry_price`;
- `first_minus5_date` uses close rather than low for the primary field;
- max gain uses close rather than high;
- max loss uses close rather than low;
- max drawdown omits `entry_price` as the initial peak candidate or assumes same-day high-before-low ordering for the primary field;
- ATR uses a non-Wilder method or non-14 period without explicit config and manifest disclosure;
- rows are filtered by future 120d path availability instead of retained with completeness flags;
- outputs depend on known big winner membership, reference-date windows, or future labels.

## 15. Interpretation Boundary

This query is descriptive path evidence only. It may be used to inspect whether the existing high-coverage family states tend to incur early adverse excursion, delayed continuation, or excessive post-entry drawdown. It must not be used as a standalone strategy validation or as a promotion gate without a separate requirement that defines executable entry, exit, risk budget, and out-of-sample decision rules.
