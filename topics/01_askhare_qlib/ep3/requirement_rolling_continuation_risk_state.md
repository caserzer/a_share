# EP3 Rolling Continuation / Risk-State Audit Requirement

> Requirement id: `ep3_rolling_continuation_risk_state_audit`
> 状态：implementation-ready requirement，尚未实现
> 范围：在 EP2 R05、Explore9 P0.6、EP3 A/C no-go 证据之后，进行 audit-only 的 continuation / risk-state falsification
> 主输出目录：`ep3/outputs/rolling_continuation_risk_state_audit/`

## 1. 背景

本 requirement 从一个负面结论出发：

```text
当前 launch / entry discovery 方向还没有形成稳定 baseline。
```

这不是说所有实验都没有任何结构。更强的解释是：

```text
failure / continuation state recognition 可能存在一定信号；
但 entry / launch timing 还没有足够 specificity，
不能成为 long-horizon winner entry baseline。
```

### 1.1 EP2 R05 证据

EP2 R05-pre 在 R03 exposure 之后测试了三条 deterministic
continuation / profit-protection policy。结果是：

```text
selection_status = failed_no_continuation_policy_edge
next_phase_proceed_status = failed_no_continuation_policy_edge
```

关键点不是 big-winner capture 完全没有提升。validation 中，strict
big-winner capture 从 R03 replay 的 `2` 提高到三条 policy 下的 `5`。
但这个提升伴随更差的 tail risk 和明显更高的 capital occupancy：

| Policy | Strict capture diff | p05 diff vs R03 | Exposure multiple |
| --- | ---: | ---: | ---: |
| `profit_lock_rule_simple` | 3 | -0.016129 | 2.55972 |
| `trailing_stop_rule_simple` | 3 | -0.017497 | 3.31990 |
| `partial_exit_after_profit_rule` | 3 | -0.018656 | 3.24869 |

解释：

```text
R02/R03 entry 能找到 short-horizon executable event timing，
但没有证明被选中的 episode 已经是 long-horizon winner formation entry。
延长 exposure 可以捕获更多 winner，
但也会把更多 bad continuation 带进左尾。
```

因此，本阶段不能继续通过调固定持有天数、固定盈利阈值或固定 trailing-stop
参数来推进。

### 1.2 Explore9 P0.6 证据

Explore9 P0.6 测试了 launch 之后的 delayed / confirmation-style entry
trigger。核心结论是：

```text
25 个 trigger variant 在加入 direct baseline、convertible direct baseline、
instrument-year lift 和 missed-winner 约束后全部失败。
```

报告将几个看起来相对有用的 trigger fragment 重新定位为：

```text
hold_3d_close_above_ema20,
volume_hold_3d,
pullback_3_8_contraction_upper_close
```

这些 fragment 可能是 hold / add-on / failure-filter 观察项，而不是 primary
entry trigger。

解释：

```text
等待 confirmation 可能识别的是“还没有明显失败”的状态，
但它没有证明稳定的 entry lift。
下一步问题应改成 continuation / risk state，
而不是继续扩大 entry-trigger grid。
```

### 1.3 EP3 A/C 与 Deferred-Family 证据

EP3 P0 测试了两个 primary winner-formation anchor family：

```text
A. pullback_hold_restrengthen
C. second_breakout
```

它们在 winner lifecycle profiling 中可见，但作为 executable forward-audit
anchor 失败。P0.5 随后排除了 A/C 只是需要更窄公式、不同 window、或 EP2
reference cleanup 的解释。被支持的解释是：

```text
matched baseline 太强，或者 anchor 没有真实 executable lift；
tail risk 是核心失败，不只是 trigger scarcity。
```

deferred `failed_lookalike_avoidance` audit 改善了 trigger coverage：

```text
validation trigger rate = 18.47%
robustness trigger rate = 19.87%
```

但仍然没有通过关键 matched-delay gate：

| Metric | Value | Gate |
| --- | ---: | --- |
| validation H20 mean diff vs matched-delay | -2.06% | fail |
| validation instrument-year positive-rate diff | -5.81% | fail |
| robustness H20 mean diff vs matched-delay | -1.13% | fail |
| robustness H20 p05 diff vs matched-delay | -2.46% | fail |

解释：

```text
增加 trigger 数量并不足够。
如果 rolling condition 本质上只是 delayed entry，
它大概率不能解决问题；
除非它能在 matched baseline 与 instrument-year stability 下证明
risk-state separation。
```

## 2. 目标

本阶段只问一个更窄的问题：

```text
在 launch / exposure event 已经存在之后，
observable rolling daily state 能否区分
“继续承担持有风险仍然合理”
和
“应该 reduce 或 exit”
并且不破坏 winner capture？
```

这不是 entry discovery 阶段。

本阶段是为未来可能的 continuation / risk-state requirement 做
falsification audit。它只能输出关于 rolling state separation 是否存在的
stop / continue 判断。

## 3. 非目标

本 requirement 不得产生：

- 新的 launch detector；
- 新的 entry trigger；
- delayed-entry rule；
- P1 strategy candidate；
- production signal；
- full portfolio backtest；
- trained model candidate；
- selected trading policy；
- 将 A/C 或 `failed_lookalike_avoidance` 作为 entry family 复活的建议。

任何可以被解读为“因为出现这个 rolling state 所以买入”的输出，都是本阶段
无效输出。

## 4. 研究问题

主问题：

```text
在 already-launched 或 already-exposed episode 中，
rolling as-of daily risk state 能否相对 no-action、matched-random 和
matched-delay baseline
改善 continuation decision，
同时保留足够 future winner upside？
```

必须回答的子问题：

1. rolling risk state 是否能在大部分 drawdown 已经发生之前识别 future
   drawdown / failed continuation？
2. rolling continuation state 是否能保留有意义的 future big-winner upside？
3. 表面收益是否在 validation 和 robustness 中稳定，而不只是 train 有效？
4. 效果是否在 instrument-year 粒度可见，而不只是 event 粒度可见？
5. 效果是否能经受 no-action、matched-random、matched-delay baseline 检验？
6. state 是否只使用 signal date 当时已经可见的数据定义？

## 5. 阶段边界

允许：

- 在上游 launch / exposure event 之后构建 daily rolling state panel；
- 使用 train-frozen threshold 评估预注册 rolling state family；
- 比较 `continue`、`reduce`、`exit`、`no_action` 这些 state interpretation；
- 报告 drawdown avoided、future winner retained、false reject 和 tail-risk
  metrics；
- 执行 deterministic audit 和 matched baseline；
- 为后续 formal refinement phase 输出 go/no-go recommendation。

禁止：

- 从 validation 或 robustness 选择 threshold；
- 从 validation 或 robustness 选择 rolling window length；
- 训练 entry、continuation、ranking、exit 或 risk model；
- 用 future max return / future drawdown 构造 state；
- 使用 EP2 R02 score threshold 作为 feature；
- 使用 EP2 R03 confirmed-pool membership 作为 selection rule；
- 使用 EP2 R05 policy outcome 作为 label 或 threshold selector；
- 修改 EP2、Explore9 或 EP3 frozen upstream artifact；
- 运行 portfolio backtest；
- 将任何 state promotion 到 P1。

validation 和 robustness 只能评估 train-derived 或 config-static definition。

## 6. Canonical Inputs

本阶段只能读取以下输入。

| Input | Path | Role |
| --- | --- | --- |
| EP2 launch pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | canonical launch episode universe |
| EP2 R04 manifest | `ep2/outputs/requirement_04_holding_exit_winner_capture_extension/manifests/requirement_04_holding_exit_manifest.json` | R04 authority |
| EP2 R04 exposure daily panel | `ep2/outputs/requirement_04_holding_exit_winner_capture_extension/cache/requirement_04_exposure_daily_panel.parquet` | exposure-day base |
| EP2 R04 big-winner audit | `ep2/outputs/requirement_04_holding_exit_winner_capture_extension/reports/requirement_04_big_winner_capture_audit.csv` | winner labels and capture reference |
| EP2 R05 manifest | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/manifests/requirement_05_continuation_policy_manifest.json` | R05 authority |
| EP2 R05 post-exposure state panel | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_post_exposure_state_panel.parquet` | post-exposure observable states |
| EP2 R05 continuation training panel | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_continuation_training_panel.parquet` | deterministic audit base only |
| EP2 R05 policy exposure daily panel | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_policy_exposure_daily_panel.parquet` | primary exposure process authority |
| EP2 R05 matched random exit panel | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_matched_random_exit_panel.parquet` | matched-random reference |
| EP2 R05 report | `ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_report.md` | background evidence only |
| Explore9 P0.6 entry trigger report | `Explore9/outputs/reports/explore9_p0_6_entry_trigger_report.md` | background evidence only |
| EP3 P0.5/deferred joint report | `ep3/p0_5_deferred_family_joint_report.md` | background evidence only |
| PIT Qlib provider | `data/qlib/cn_data_pit` | OHLCV features visible as of state date |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | trading-day windows |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | industry/regime decomposition |
| PIT universe membership | `data/universe/pit_qlib_instrument_universe.csv` | point-in-time membership check |

禁止输入：

- 任何 BaseRate row-level cache；
- Explore9 或 Explore10 model score；
- Explore9 / Explore10 row-level candidate panel；
- EP2 R02 learned threshold 或 score output；
- 将 EP2 R03 selected confirmed-pool output 作为 filter；
- validation-selected 或 robustness-selected parameter file；
- 新拉取的 Tushare / AkShare 数据。

### 6.1 R05 Panel 字段隔离

R05 post-exposure state panel 可以读取，但只能使用下列字段族：

- key / split 字段：`launch_episode_id`、`instrument`、`split`；
- date 字段：`state_signal_date`、`action_effective_date`、`feature_asof_date`；
- R03 exposure date/price 字段：`r03_first_exposure_signal_date`、
  `r03_first_exposure_execution_date`、`r03_first_exposure_price`、
  `r03_confirm_add_signal_date`、`r03_confirm_add_execution_date`、
  `r03_confirm_add_price`；
- current state 字段：`current_exposure_weight_before_action`、
  `active_position_state`、`days_since_first_exposure`、`days_since_confirm_add`、
  `current_close`、`current_return_from_first_exposure`、
  `current_return_from_confirm_add`、`max_favorable_excursion_since_first_exposure`、
  `max_adverse_excursion_since_first_exposure`、`post_confirm_high_to_date`、
  `drawdown_from_post_confirm_high`、`giveback_from_peak_profit`、
  `current_profit_cushion`、`distance_to_first_exposure_price`、
  `distance_to_confirm_add_price`；
- execution 字段：`sell_executable_next_open`、`blocked_sell_reason_next_open`；
- as-of audit 字段：`feature_asof_violation_flag`。

以下字段不得进入 feature dictionary、state panel、variant formula、threshold
freeze、gate 或任何 promotion evidence：

```text
r02_P_target_first_at_probe
r02_P_stop_first_at_probe
r02_P_neither_at_probe
r02_score_probe_day_at_probe
r02_selected_threshold
r02_selected_stop_risk_ceiling
any column matching r02_*
any column matching *_score*
any column matching *_threshold*
```

validator 必须检查 forbidden R02 / score / threshold 字段没有进入任何输出。

## 7. Episode Universe

primary universe 定义为：

```text
所有至少有一个 primary exposure process exposure day，
并且有足够 post-state horizon 可以评估 H5、H10、H20、H60 action outcome
的 EP2 launch episode。
```

H120 只用于 `future_big_winner_retained_50h120`、false reject 和 partial
haircut 支持证据。H120 不足的 row 可以进入 H5/H10/H20/H60 action lift，但不得
进入 retention / false reject / partial haircut denominator。

### 7.1 Primary Exposure Process Freeze

本阶段必须冻结唯一 primary exposure process：

```text
primary_exposure_process_id = R03_original_H10_replay
source_panel = requirement_05_policy_exposure_daily_panel.parquet
required_filter:
  policy_id = R03_original_H10_replay
  schedule_id = R03_original_H10_replay
```

这个 process 是本阶段的 `no_action_replay`。它只用于定义“已经存在的
exposure”和 no-action baseline，不代表本阶段认可 R03 是 long-horizon
winner entry。

Allowed use:

- `actual_weight`、`cash_weight` 用于构造 no-action exposure path；
- `daily_return_net`、`cum_return_net` 只用于 reconciliation audit，不得作为主收益；
- `date` 用于 exposure day calendar；
- `launch_episode_id` 和 `instrument` 用于和 rolling state row 对齐。

Forbidden use:

- 不得混入 `profit_lock_rule_simple`、`trailing_stop_rule_simple`、
  `partial_exit_after_profit_rule`；
- 不得混入 R04 diagnostic schedule；
- 不得从多个 schedule / policy 中挑选表现最好的 exposure process；
- R05 policy outcome 不得作为 label、threshold selector 或 promotion evidence。

如果 source panel 中同一个 `launch_episode_id + date` 在该 filter 下出现多行，
validator 必须 fail。

实现必须区分两种 row scope：

| Scope | Description | Promotion role |
| --- | --- | --- |
| `primary_exposure_day_scope` | `R03_original_H10_replay` 中 `actual_weight > 0` 的 exposure day | primary audit scope |
| `launch_observation_only_scope` | 没有 exposure day 或缺少 exposure replay 的 launch episode | denominator and miss audit only |

`launch_observation_only_scope` 的 row 不能支持 continuation state，因为没有假定已经
持仓。

## 8. State Date 与 Action Date

每个 rolling state row 必须使用：

```text
state_signal_date:
  close-derived date，即 rolling condition 被观察到的日期。

state_effective_date:
  state_signal_date 之后的下一个交易日。

state_effective_price_reference:
  open[state_effective_date]，即 state_signal_date 之后第一个可执行交易日的开盘价。
```

规则：

- `state_signal_date` 的 feature 必须只使用该日期或该日期之前可见的数据；
- future return、future high、future low、future drawdown 不得进入 state formula；
- 如果 next open 不可用，或因为涨跌停执行逻辑无法成交，该 row 不是 action-eligible，
  且必须报告 blocked reason；
- 所有 metric 必须从 `state_effective_price_reference` 计算，不能使用 same-day close
  作为主执行价格。

### 8.1 Price Return Basis

所有 action return 必须从 PIT OHLCV 重新计算，不得混用 R05 panel 中的
`daily_return_net` 作为主收益口径。

统一价格路径：

```text
action_start_date = state_effective_date
entry_price_for_action = open[action_start_date]

Hk horizon:
  starts at open[action_start_date]
  first day return uses open[action_start_date] -> close[action_start_date]
  later daily returns use close[d-1] -> close[d]
  horizon end is the kth trading day after action_start_date, inclusive
```

`daily_return_net`、`cum_return_net` 只能用于 reconciliation audit，不得用于
`mean_after_cost_return`、`p05_after_cost_return`、`mae_mean` 或 gate 主指标。

## 9. 预注册 Rolling State Family

本阶段只测试 deterministic family。window length 和 threshold edge 必须在评估
validation 之前被定义为 config-static 或 train-derived。

### 9.1 Continuation State Family

| State family | Intent | Allowed examples |
| --- | --- | --- |
| `trend_hold_state` | 价格仍在 rolling trend support 之上 | close above EMA20/EMA30, EMA slope positive |
| `volume_support_state` | 持有期间 volume/money 没有 collapse | money above rolling median/MA20 floor |
| `range_compression_hold_state` | 波动收缩但价格没有 breakdown | rolling range contraction with close above support |
| `relative_strength_hold_state` | 相对 market/industry 仍有强度 | ret20 relative rank, industry-relative ret |
| `profit_buffer_state` | reduce risk 前已经有 open profit buffer | current return from entry above train-frozen floor |

### 9.2 Risk State Family

| State family | Intent | Allowed examples |
| --- | --- | --- |
| `support_break_state` | 价格跌破 rolling support | close below EMA20/EMA30 or rolling low break |
| `volume_failure_state` | continuation 失败且 money 走弱 | money collapse after launch while price weakens |
| `range_expansion_down_state` | 下行波动扩张 | high-low range expansion with negative close location |
| `relative_strength_failure_state` | 个股相对 market/industry 走弱 | relative ret20 deterioration |
| `profit_giveback_state` | open profit 明显回撤 | drawdown from post-entry peak using as-of peak only |

第一版实现不得新增其他 state family，除非另一个 requirement revision 预先注册。

### 9.3 第一版 State Variant Matrix

第一版只能实现下表中的 variant。所有公式字段必须写入
`rolling_state_feature_dictionary.csv`，所有 train-derived threshold 必须写入
`rolling_state_threshold_freeze.csv`。

| state_variant_id | state_family_id | state_direction | Formula | Threshold source |
| --- | --- | --- | --- | --- |
| `trend_hold_ema20_3d` | `trend_hold_state` | continuation | `close >= ema20 and close_1d_ago >= ema20_1d_ago and close_2d_ago >= ema20_2d_ago and ema20_slope_5d > 0` | config-static |
| `volume_support_money20_floor` | `volume_support_state` | continuation | `money_ma3 >= 0.80 * money_ma20 and close >= ema20` | config-static |
| `range_compression_above_support` | `range_compression_hold_state` | continuation | `rolling_range_5d / atr20 <= train_q50 and close >= ema20` | train-only q50 |
| `relative_strength_hold_20d` | `relative_strength_hold_state` | continuation | `relative_ret20_vs_market >= 0 and relative_ret20_vs_industry >= 0` | config-static |
| `profit_buffer_6pct` | `profit_buffer_state` | continuation | `current_return_from_entry >= 0.06 and drawdown_from_profit_peak_asof_state <= 0.04` | config-static |
| `support_break_ema20_2d` | `support_break_state` | risk | `close < ema20 and close_1d_ago < ema20_1d_ago and ret3 < 0` | config-static |
| `volume_failure_money20_break` | `volume_failure_state` | risk | `money_ma3 < 0.60 * money_ma20 and close < ema20` | config-static |
| `range_expansion_downside` | `range_expansion_down_state` | risk | `true_range / atr20 >= 1.50 and close_location_in_day <= 0.30 and ret1 < 0` | config-static |
| `relative_strength_failure_20d` | `relative_strength_failure_state` | risk | `relative_ret20_vs_market <= train_q30_market_rel20 and relative_ret20_vs_industry <= train_q30_industry_rel20` | train-only q30 |
| `profit_giveback_10_6` | `profit_giveback_state` | risk | `open_profit_peak_asof_state >= 0.10 and drawdown_from_profit_peak_asof_state >= 0.06` | config-static |

计算约束：

- EMA、ATR、money MA、rolling range、relative return 的 rolling window 必须只用
  `state_signal_date` 及以前数据；
- `train_q50` 和 `train_q30` 只能从 train split 的 eligible state rows 计算；
- validation / robustness 不得改变 threshold、window、variant id 或公式；
- 如果任一 required feature 缺失，row 必须标记为 feature-ineligible，不得静默填充。

### 9.3.1 Feature Formula Freeze

第一版 feature 必须按以下公式计算：

```text
ema20:
  per-instrument EMA(close, span=20, adjust=false), ending at state_signal_date

ema20_slope_5d:
  ema20[state_signal_date] / ema20[state_signal_date - 5 trading days] - 1

close_1d_ago:
  close[state_signal_date - 1 trading day]

close_2d_ago:
  close[state_signal_date - 2 trading days]

ema20_1d_ago:
  ema20[state_signal_date - 1 trading day]

ema20_2d_ago:
  ema20[state_signal_date - 2 trading days]

money_ma3:
  rolling mean(money, 3 trading days), ending at state_signal_date

money_ma20:
  rolling mean(money, 20 trading days), ending at state_signal_date

true_range:
  max(high - low, abs(high - prev_close), abs(low - prev_close))

atr20:
  rolling mean(true_range, 20 trading days), ending at state_signal_date

rolling_range_5d:
  (max(high, last 5 trading days) - min(low, last 5 trading days))
  / close[state_signal_date]

close_location_in_day:
  if high > low:
    (close - low) / (high - low)
  else:
    0.5

ret1:
  close[state_signal_date] / close[state_signal_date - 1 trading day] - 1

ret3:
  close[state_signal_date] / close[state_signal_date - 3 trading days] - 1

ret20:
  close[state_signal_date] / close[state_signal_date - 20 trading days] - 1
```

Entry / profit-state definitions：

```text
entry_effective_date:
  r03_first_exposure_execution_date from the allowed R05 post-exposure fields.

entry_price_reference:
  r03_first_exposure_price from the allowed R05 post-exposure fields.

current_return_from_entry:
  close[state_signal_date] / entry_price_reference - 1

open_profit_peak_asof_state:
  max(close from entry_effective_date through state_signal_date)
  / entry_price_reference - 1

drawdown_from_profit_peak_asof_state:
  open_profit_peak_asof_state - current_return_from_entry
```

第一版不使用 confirm-add blended cost basis。`r03_confirm_add_*` 只能用于审计和
report 分解，不得改变 `current_return_from_entry` 的主口径。

Market / industry return definitions:

```text
market_ret20:
  equal-weight close-to-close 20 trading day return of PIT universe members.

industry_ret20:
  equal-weight close-to-close 20 trading day return of PIT same-industry
  members from `data/targets/pit_industry_membership.csv`.

relative_ret20_vs_market:
  ret20 - market_ret20

relative_ret20_vs_industry:
  ret20 - industry_ret20
```

If the PIT same-industry member count is `< 10` on `state_signal_date`,
`industry_ret20` and `relative_ret20_vs_industry` must be null, and any variant
requiring industry-relative return must mark the row feature-ineligible.

Train-derived thresholds:

```text
train_q50_range_atr:
  q50 of rolling_range_5d / atr20 over train eligible state rows.

train_q30_market_rel20:
  q30 of relative_ret20_vs_market over train eligible state rows.

train_q30_industry_rel20:
  q30 of relative_ret20_vs_industry over train eligible state rows.
```

All threshold rows must include:

```text
threshold_id
source_split = train
source_row_count
source_min_date
source_max_date
value
```

### 9.4 预注册 Regime Cells

regime-conditional decision 只能使用以下预注册 support cell：

```text
market_trend_state in {market_trend_on, market_trend_off}
industry_sync_state in {industry_sync_on, industry_sync_off}
regime_cell_id = market_trend_state + "__" + industry_sync_state
```

另有一个 audit-only cell：

```text
regime_cell_id = insufficient_industry_members
```

该 cell 只能用于覆盖率和不可判定原因报告，不能作为 regime-conditional support
或 promotion evidence。

定义：

```text
market_trend_on:
  market_close >= market_ema60 and market_ema60_slope_20d > 0

market_trend_off:
  not market_trend_on

industry_sync_on:
  industry_close_gt_ema60_ratio >= train_median_industry_close_gt_ema60_ratio

industry_sync_off:
  not industry_sync_on
```

`train_median_industry_close_gt_ema60_ratio` 必须只用 train split 计算并写入
`rolling_state_threshold_freeze.csv`。不得在看到 validation outcome 后新增
regime cell。

regime 数据源和公式：

```text
market_close:
  equal-weight synthetic close index of PIT universe members.
  Initial index value = 1.0 on the first available calendar date.

market_ema60:
  EMA(market_close, span=60, adjust=false), ending at state_signal_date.

market_ema60_slope_20d:
  market_ema60[state_signal_date]
  / market_ema60[state_signal_date - 20 trading days] - 1

industry_close_gt_ema60_ratio:
  for the instrument's PIT industry on state_signal_date,
  share of PIT same-industry members where close >= ema60.
```

If an industry has fewer than 10 PIT members on `state_signal_date`, the row
must be marked `regime_cell_id = insufficient_industry_members` and cannot
support a regime-conditional decision.

## 10. Candidate Actions

本 audit 不执行策略，只为每个 eligible state row 模拟 counterfactual action
interpretation：

| Action | Meaning | Allowed promotion role |
| --- | --- | --- |
| `no_action` | 保持 `R03_original_H10_replay` 不变 | baseline only |
| `continue` | state 表示当前风险仍可继续承担 | diagnostic |
| `reduce` | state 表示将 exposure 降低到固定 fraction | diagnostic |
| `exit` | state 表示停止继续承担 exposure | diagnostic |

任何 action 都不得开新仓。

`reduce` 第一版只能使用固定 fraction：

```text
reduce_to_weight in {0.50, 0.30}
```

fraction set 是 config-static，不得从 validation 或 robustness 中选择。

### 10.1 Action-Adjusted Return Formula

所有 action-level metric 必须从同一套 no-action replay 派生：

```text
primary_exposure_process_id = R03_original_H10_replay
source_panel = requirement_05_policy_exposure_daily_panel.parquet
filter = policy_id == schedule_id == R03_original_H10_replay
cost_model = same_as_EP2_R05
cost_authority_chain:
  ep2/configs/requirement_05_daily_continuation_profit_protection_policy.yaml
    -> baseline.config_path = ep2/engineering_baseline/config.yaml
  ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml
    -> holding_rules.cost_model = same_as_requirement_03
  ep2/configs/requirement_03_schedule_bridge.yaml
    -> schedule_bridge.cost_model = same_as_engineering_baseline
  ep2/engineering_baseline/config.yaml
    -> cost_model
```

定义：

```text
state_effective_date = next_trading_day(state_signal_date)
state_effective_price_reference = open[state_effective_date]
action_start_date = state_effective_date
```

`no_action`：

```text
使用 primary exposure process 中 action_start_date 及之后的 actual_weight。
收益使用 8.1 的 PIT OHLCV price return basis 重新计算。
不改变任何 exposure。
```

`continue`：

```text
收益计算与 no_action 完全相同。
它只用于衡量 continuation state row 这个子集是否优于 no_action reference universe，
不得解释为新增交易动作。
```

因此，`continue` 的 lift 不能使用 same-row no-action diff。same-row 中
`continue` 和 `no_action` 的 action-adjusted return 必须完全相等。continuation
state 的 support 只能来自：

```text
continue state subset
vs
full primary exposure no-action reference universe
或 matched_random / matched_delay baseline
```

而不是来自 same-row `continue - no_action`。

`exit`：

```text
从 action_start_date 起，将 actual_weight 设置为 0，cash_weight 设置为 1。
action_start_date 当日使用 state_effective_price_reference 作为退出价格。
退出后 horizon 内剩余 daily return = 0。
必须扣除一次 sell cost，cost model 与 EP2/R05 保持一致。
```

`reduce`：

```text
从 action_start_date 起，将 actual_weight 设置为
min(no_action_actual_weight, reduce_to_weight)。
cash_weight = 1 - adjusted_actual_weight。
不延长原 no-action replay 的持有结束日。
必须对被卖出的权重扣除一次 sell cost，cost model 与 EP2/R05 保持一致。
```

Cost model 要求：

- 必须读取上述 cost authority chain，并把最终使用的
  `ep2/engineering_baseline/config.yaml::cost_model` 写入
  `rolling_state_action_formula_audit.csv`；
- 如果无法确认 `same_as_EP2_R05`，validator 必须 fail；
- 不得在本阶段引入新的 commission、stamp tax、slippage 或冲击成本假设。

`mean_after_cost_return`、`p05_after_cost_return`、`mae_mean`、
`drawdown_avoided_mean` 和 `capital_occupancy_multiple` 都必须基于上述
action-adjusted exposure path 计算。

Action-adjusted daily net return:

```text
daily_net_return =
  adjusted_actual_weight * instrument_price_return
  - transaction_cost_on_weight_change
```

其中 `instrument_price_return` 必须来自 8.1 的统一价格路径。

`capital_occupancy_multiple` 定义为：

```text
sum(action_adjusted_actual_weight exposure days)
/
sum(no_action_actual_weight exposure days)
```

如果分母为 0，该 row 不得进入 action lift 主榜，必须单独报告。

### 10.2 Comparison Reference Scope

不同 action 的 no-action comparison 必须使用不同 reference scope：

| Action direction | Valid no-action reference | Reason |
| --- | --- | --- |
| `risk` + `reduce` / `exit` | same state row 的 `no_action` counterfactual | 衡量同一状态日上减仓/退出是否降低风险 |
| `continuation` + `continue` | full primary exposure no-action reference universe | same-row `continue` 等于 `no_action`，只能衡量 state subset selection |

`rolling_state_action_lift.csv` 必须写入：

```text
comparison_reference_scope in {
  same_row_no_action,
  full_primary_exposure_no_action_universe
}
```

`full_primary_exposure_no_action_universe` 定义为：

```text
same split
same horizon_id
primary_exposure_day_scope
is_action_eligible = true
sufficient horizon for that horizon_id
action-adjusted path = no_action replay
```

该 reference universe 不得按当前 `state_variant_id` 是否触发过滤；它是衡量
continuation state subset 是否优于普通已持仓日的背景基准。

validator 必须 fail 如果：

- `continue` 使用 same-row no-action diff 作为 support gate；
- `risk` action 使用 full-universe no-action diff 代替 same-row counterfactual；
- report 没有说明每个 action row 的 comparison reference scope。

## 11. Required Outputs

所有输出必须位于：

```text
ep3/outputs/rolling_continuation_risk_state_audit/
```

Required cache outputs：

| Output | Row grain |
| --- | --- |
| `cache/rolling_state_daily_panel.parquet` | one row per `launch_episode_id + state_signal_date + state_family_id + state_variant_id` |
| `cache/rolling_state_action_panel.parquet` | one row per state row + candidate action |
| `cache/rolling_state_matched_baseline_panel.parquet` | one row per state row + baseline id |

Required report outputs：

| Output | Purpose |
| --- | --- |
| `reports/rolling_state_feature_dictionary.csv` | formula and as-of feature contract |
| `reports/rolling_state_variant_matrix.csv` | pre-registered state variants |
| `reports/rolling_state_threshold_freeze.csv` | config-static and train-derived thresholds |
| `reports/rolling_state_primary_exposure_authority.csv` | primary exposure process audit |
| `reports/rolling_state_trigger_decomposition.csv` | state frequency and breadth |
| `reports/rolling_state_action_lift.csv` | action-level outcome metrics |
| `reports/rolling_state_action_formula_audit.csv` | action-adjusted return formula audit |
| `reports/rolling_state_false_reject_audit.csv` | winners rejected or reduced too early |
| `reports/rolling_state_drawdown_avoidance_audit.csv` | drawdown avoided before H5/H10/H20/H60 |
| `reports/rolling_state_instrument_year_stability.csv` | instrument-year lift and concentration |
| `reports/rolling_state_regime_audit.csv` | market / industry regime decomposition |
| `reports/rolling_state_matched_random_audit.csv` | matched-random comparison |
| `reports/rolling_state_matched_baseline_audit.csv` | all matched baseline coverage and lift comparison |
| `reports/rolling_state_gate_audit.csv` | machine-readable gate result |
| `reports/rolling_state_decision.csv` | final phase decision |
| `reports/rolling_state_report.md` | Chinese summary report |
| `manifests/rolling_state_manifest.json` | validation manifest |

## 12. Core Schema

### 12.1 `rolling_state_daily_panel.parquet`

必需字段：

| Field | Description |
| --- | --- |
| `rolling_state_event_id` | stable id |
| `launch_episode_id` | upstream launch episode |
| `instrument` | instrument code |
| `split` | train / validation / robustness |
| `instrument_year` | instrument + state year |
| `primary_exposure_process_id` | must equal `R03_original_H10_replay` |
| `source_policy_id` | source policy id from exposure panel |
| `source_schedule_id` | source schedule id from exposure panel |
| `state_signal_date` | observable close-derived state date |
| `state_effective_date` | next trading day |
| `state_effective_price_reference` | next open |
| `state_family_id` | registered state family |
| `state_variant_id` | registered deterministic variant |
| `state_direction` | continuation / risk |
| `state_formula_version` | formula version |
| `state_formula_hash` | hash of formula dictionary row |
| `feature_asof_date` | latest feature date used |
| `feature_lookback_window_days` | maximum rolling lookback |
| `is_action_eligible` | executable next-open flag |
| `blocked_action_reason` | reason when not eligible |
| `entry_effective_date` | upstream entry / exposure effective date |
| `entry_price_reference` | upstream entry price |
| `current_return_from_entry` | as-of return at state signal date |
| `open_profit_peak_asof_state` | as-of max close return since entry |
| `drawdown_from_profit_peak_asof_state` | as-of giveback |
| `future_return_H5` | raw instrument future return from effective price, action-independent |
| `future_return_H10` | raw instrument future return from effective price, action-independent |
| `future_return_H20` | raw instrument future return from effective price, action-independent |
| `future_return_H60` | raw instrument future return from effective price, action-independent |
| `future_mae_H20` | positive max adverse excursion loss after effective date |
| `future_mfe_H60` | positive max favorable excursion gain after effective date |
| `future_big_winner_retained_50h120` | true if future 50h120 target remains reachable after effective date |
| `target_reached_before_state_effective_date` | target already reached before action could occur |
| `retention_denominator_eligible` | eligible for winner retention denominator |
| `false_reject_denominator_eligible` | eligible for false reject denominator |
| `partial_haircut_denominator_eligible` | eligible for partial winner haircut denominator |
| `market_trend_state` | pre-registered market regime state |
| `industry_sync_state` | pre-registered industry regime state |
| `regime_cell_id` | pre-registered regime cell |
| `label_horizon_truncated` | insufficient future data |

### 12.2 Winner Retention And False Reject Definition

本阶段必须从 `state_effective_price_reference` 重新计算 future winner
retention，不得直接复用 launch day 或 entry day 的 winner label。

定义：

```text
future_big_winner_retained_50h120 =
  max(high over 120 trading days from state_effective_date, inclusive)
  / state_effective_price_reference - 1 >= 0.50
```

MAE / MFE 符号约定：

```text
future_mae_H20 =
  max(0, 1 - min(low over H20 from state_effective_date, inclusive)
  / state_effective_price_reference)

future_mfe_H60 =
  max(0, max(high over H60 from state_effective_date, inclusive)
  / state_effective_price_reference - 1)

mae_mean:
  mean of positive loss; lower is better.

mae_improvement_vs_no_action:
  no_action_mae_mean - action_mae_mean; positive is better.

drawdown_avoided_mean:
  no_action_mae_mean - action_mae_mean; positive is better.
```

如果目标在 `state_effective_date` 之前已经达成：

```text
target_reached_before_state_effective_date = true
retention_denominator_eligible = false
false_reject_denominator_eligible = false
partial_haircut_denominator_eligible = false
```

这类 row 必须进入 report-only 的 already-hit audit，但不得作为
future winner retention 或 false reject 的支持证据。

如果 horizon 不足 120 个交易日：

```text
label_horizon_truncated = true
retention_denominator_eligible = false
false_reject_denominator_eligible = false
partial_haircut_denominator_eligible = false
```

其他 row 的 denominator eligibility：

```text
retention_denominator_eligible = true
false_reject_denominator_eligible = true
partial_haircut_denominator_eligible = true
```

false reject 定义：

```text
full_false_reject_winner =
  action in {reduce, exit}
  and false_reject_denominator_eligible
  and future_big_winner_retained_50h120
  and retained_weight_after_action < 0.50
```

partial haircut 定义：

```text
partial_winner_haircut =
  action = reduce
  and partial_haircut_denominator_eligible
  and future_big_winner_retained_50h120
  and 0 < retained_weight_after_action < no_action_actual_weight
```

future winner retention rate 定义：

```text
future_winner_retention_rate =
  retained future winner count after action
  /
  retention_denominator_eligible future winner count under no_action
```

其中：

- `exit` 的 retained future winner count = 0；
- `reduce` 的 retained future winner count 只在剩余权重 `>= 0.50` 时计为 retained；
- `continue` 与 `no_action` 的 retained future winner count 相同；
- `false_reject_winner_rate` 使用 `full_false_reject_winner` 作为 numerator；
- `partial_winner_haircut_rate` 单独报告，不得和 full false reject 混在一起；
- already-hit target 不得提高 retention rate。

rate denominator 定义：

```text
future_winner_denominator_count =
  count rows where retention_denominator_eligible
  and future_big_winner_retained_50h120

false_reject_winner_rate =
  sum(full_false_reject_winner) / future_winner_denominator_count

partial_winner_haircut_rate =
  sum(partial_winner_haircut) / future_winner_denominator_count
```

如果 `future_winner_denominator_count = 0`，对应 rate 必须为 null，gate 不得通过。

### 12.3 `rolling_state_action_lift.csv`

必需 row grain：

```text
split + state_family_id + state_variant_id + action + horizon_id
```

必需 metrics：

| Field | Description |
| --- | --- |
| `event_count` | eligible state rows |
| `unique_launch_episode_count` | unique launch episodes |
| `unique_instrument_year_count` | breadth |
| `mean_after_cost_return` | action-adjusted mean |
| `p05_after_cost_return` | action-adjusted p05 |
| `mae_mean` | action-adjusted MAE |
| `mae_improvement_vs_no_action` | no-action MAE minus action MAE, positive is better |
| `drawdown_avoided_mean` | avoided drawdown vs no-action |
| `future_winner_retention_rate` | retained future winner share |
| `false_reject_winner_rate` | full false reject before future winner realization |
| `partial_winner_haircut_rate` | partial reduction of future winner exposure |
| `already_hit_target_row_count` | target already reached before state effective date |
| `horizon_truncated_row_count` | rows excluded due to insufficient horizon |
| `capital_occupancy_multiple` | exposure days vs no-action |
| `comparison_reference_scope` | same-row or full-universe no-action reference |
| `mean_diff_vs_no_action_reference` | action mean minus no-action reference mean |
| `p05_diff_vs_no_action_reference` | action p05 minus no-action reference p05 |
| `matched_random_p95_diff` | real minus matched-random p95 |
| `matched_delay_mean_diff` | real minus matched-delay mean |
| `matched_delay_p05_diff` | real minus matched-delay p05 |
| `instrument_year_positive_rate_diff` | action vs no-action at instrument-year grain |
| `interpretation_status` | interpretable / too_sparse |

## 13. Baselines

必需 baseline：

| Baseline id | Description |
| --- | --- |
| `no_action_replay` | `R03_original_H10_replay` exposure path unchanged |
| `matched_random_state_date` | same episode, random eligible state date with same exposure age bucket |
| `matched_delay_state_date` | same episode, train-frozen delay after first eligible state |
| `same_instrument_nonstate_day` | same instrument, exposure day without this state |
| `industry_year_matched_state` | different instrument, same industry/year and similar exposure age |

matched baseline 必须报告 unmatched row。除非 config 明确声明允许 replacement，且
manifest 记录了 replacement，否则禁止 replacement。

`matched_random_state_date` 和 `matched_delay_state_date` 必须使用同一个
primary exposure process，且 donor day 必须满足：

- same `launch_episode_id`；
- same `split`；
- same exposure age bucket；
- `actual_weight > 0`；
- action-eligible；
- not selected using future outcome。

exposure age bucket 冻结为 config-static：

```text
days_since_first_exposure_bucket:
  0_2:   0 <= days_since_first_exposure <= 2
  3_5:   3 <= days_since_first_exposure <= 5
  6_10:  6 <= days_since_first_exposure <= 10
  gt_10: days_since_first_exposure > 10
```

matched baseline 不得从 validation 或 robustness 调整 bucket 边界。

### 13.1 Matched-Delay Freeze

`matched_delay_state_date` 不能在 validation 或 robustness 中重新选择 delay。第一版
delay 必须按以下顺序冻结：

```text
1. 如果 config 明确给出 matched_delay_days，则使用 config-static value。
2. 否则只在 train split 中计算：
   median(state_signal_date - first_exposure_execution_date)
   over eligible rolling state rows for the same state_variant_id.
3. 将结果按 trading-day integer 取整，并写入 rolling_state_threshold_freeze.csv。
```

每个 matched-delay donor 必须满足：

```text
donor_state_signal_date =
  first_exposure_execution_date + frozen matched_delay_days in trading days
```

如果该 donor day 不存在、不可执行、或不满足同一 exposure age bucket，则该 row
必须记为 unmatched，不得向前或向后搜索 replacement，除非 config 明确允许且
manifest 记录 replacement rule。

`rolling_state_matched_baseline_audit.csv` 必须至少包含：

```text
split
state_variant_id
baseline_id
candidate_row_count
matched_row_count
unmatched_row_count
replacement_used
matched_delay_days
mean_diff_vs_state_action
p05_diff_vs_state_action
instrument_year_positive_rate_diff
```

### 13.2 Other Matched Baseline Donor Rules

`same_instrument_nonstate_day` donor 必须满足：

- same `instrument`；
- same `split`；
- same primary exposure process；
- exposure day 且 `actual_weight > 0`；
- action-eligible；
- same `days_since_first_exposure_bucket`；
- 该 donor day 对当前 `state_variant_id` 为 false；
- not selected using future outcome。

`industry_year_matched_state` donor 必须满足：

- different `instrument`；
- same `split`；
- same PIT industry on donor `state_signal_date`；
- same calendar year；
- same primary exposure process；
- same `days_since_first_exposure_bucket`；
- same `state_variant_id` is true on donor day；
- action-eligible；
- exposure age difference <= 2 trading days within the same bucket；
- not selected using future outcome。

如果多个 donor 满足条件，必须使用 deterministic seed 从 eligible donor set 中抽取，
seed 写入 manifest。不得按 future return、future drawdown 或 winner outcome 排序。
如果没有 donor，该 row 必须记为 unmatched。

## 14. Gates

本阶段 final decision 只能是以下之一：

```text
stop_rolling_continuation_risk_state
write_rolling_continuation_risk_state_refinement_requirement
write_regime_conditional_risk_state_requirement
```

不得返回：

```text
write_entry_requirement
write_launch_trigger_requirement
write_p1_validation_requirement
strategy_candidate
production_signal
```

### 14.1 Minimum Interpretability Gates

一个 state variant 只有在 validation 中同时满足以下条件，才是 interpretable：

- `event_count >= 50`;
- `unique_launch_episode_count >= 30`;
- `unique_instrument_year_count >= 25`;
- top1 instrument-year PnL contribution <= `0.20`;
- top5 instrument exposure share <= `0.50`.

### 14.2 Risk-State Support Gates

risk-state variant 必须满足以下条件，才能支持后续 refinement requirement：

- validation `drawdown_avoided_mean > 0`;
- validation `p05_diff_vs_no_action_reference >= 0.005`;
- validation `mae_improvement_vs_no_action >= 0.005`;
- validation `false_reject_winner_rate <= 0.20`;
- validation `partial_winner_haircut_rate <= 0.35`;
- validation `future_winner_retention_rate >= 0.70`;
- validation `matched_random_p95_diff >= -0.001`;
- validation `matched_delay_mean_diff >= -0.001`;
- validation `matched_delay_p05_diff >= -0.001`;
- validation `instrument_year_positive_rate_diff >= 0`;
- robustness `p05_diff_vs_no_action_reference >= 0`;
- robustness `mae_improvement_vs_no_action >= 0`;
- robustness `matched_delay_mean_diff >= -0.003`;
- robustness `matched_delay_p05_diff >= -0.003`;
- robustness false reject winner rate <= validation false reject rate + `0.10`;
- robustness partial winner haircut rate <= validation partial haircut rate + `0.10`;
- already-hit target rows do not count toward future winner retention or false
  reject support.

### 14.3 Continuation-State Support Gates

continuation-state variant 必须满足以下条件，才能支持后续 refinement
requirement：

- validation `mean_diff_vs_no_action_reference > 0`;
- validation `p05_diff_vs_no_action_reference >= -0.003`;
- validation future winner retention rate >= `0.80`;
- validation capital occupancy multiple <= `1.50`;
- validation `matched_random_p95_diff >= -0.001`;
- validation `matched_delay_mean_diff >= -0.001`;
- validation `matched_delay_p05_diff >= -0.003`;
- validation instrument-year positive-rate diff >= `0`;
- robustness `mean_diff_vs_no_action_reference >= -0.001`;
- robustness `p05_diff_vs_no_action_reference >= -0.005`;
- robustness `matched_delay_mean_diff >= -0.003`;
- robustness `matched_delay_p05_diff >= -0.005`;
- already-hit target rows do not count toward future winner retention support.

### 14.4 Regime-Conditional Gate

只有同时满足以下条件，decision 才可以是
`write_regime_conditional_risk_state_requirement`：

- 没有 global state variant 通过全部 support gate；
- 至少一个预注册 market / industry regime cell 是 interpretable；
- 该 cell 通过所有 validation risk-state 或 continuation-state gate；
- robustness 没有超过允许 tolerance 的反转；
- regime split 在查看 validation outcome 之前已经定义。

否则 final decision 必须是：

```text
stop_rolling_continuation_risk_state
```

## 15. Validator Requirements

validator 必须在以下情况 fail：

- 缺少 canonical input file；
- upstream R04 或 R05 manifest 不存在；
- primary exposure process 不唯一；
- source exposure row 不满足 `policy_id = schedule_id = R03_original_H10_replay`；
- 使用 forbidden input；
- 输出位于声明 output root 之外；
- 任一 required panel 出现 duplicate primary key；
- 缺少 formula dictionary 或 formula hash mismatch；
- feature as-of date 晚于 `state_signal_date`；
- action effective date 没有严格晚于 close-derived `state_signal_date`；
- 使用 same-day close 作为 primary execution price；
- 使用 future outcome 构造 state；
- forbidden R02 / score / threshold 字段进入任何输出或公式；
- 直接复用 launch day / entry day winner label 作为 state-date retention；
- already-hit target row 被计入 retention 或 false reject denominator；
- `false_reject_winner_rate` 或 `partial_winner_haircut_rate` 使用了非 future-winner
  denominator；
- partial winner haircut 被混入 full false reject numerator；
- MAE / drawdown avoided 使用了未声明符号方向或方向与 gate 相反；
- action-adjusted return 未按本 requirement 的公式计算；
- `daily_return_net` 或 `cum_return_net` 被用作 gate 主收益口径；
- `continue` 使用 same-row no-action diff 作为 support evidence；
- cost model 无法证明与 EP2/R05 一致；
- industry member count `< 10` 的 row 仍被用于 industry-relative variant 或
  regime-conditional support；
- H120 不足或 already-hit target row 被计入 retention、false reject 或 partial
  haircut denominator；
- 使用 validation 或 robustness 选择 threshold、window、variant 或 regime；
- `matched_delay_state_date` 未通过 config-static 或 train-only 方式冻结；
- matched baseline audit 缺少 unmatched row 或 replacement 记录；
- `same_instrument_nonstate_day` 或 `industry_year_matched_state` donor 不满足
  预注册 donor rule；
- 生成未预注册的 state variant 或 regime cell；
- 产生 model training artifact；
- 产生 portfolio backtest artifact；
- 产生 entry 或 launch trigger output；
- report row 在声明 row grain 下重复；
- non-executable row 缺少 blocked-action reason；
- replacement 被禁止时仍使用 matched baseline donor replacement；
- final decision 不在允许 decision set 中。

## 16. Required Report Narrative

中文报告必须按以下顺序回答：

1. 为什么 EP2 R05、Explore9 P0.6、EP3 A/C/deferred 证据说明本阶段应是
   continuation / risk-state audit，而不是另一个 entry audit。
2. 本阶段为什么冻结 `R03_original_H10_replay` 作为唯一 primary exposure
   process。
3. rolling state 是否能在大部分损失发生前降低 tail risk。
4. rolling state 是否能保留足够 future winner upside，且不把 already-hit
   target 计入支持证据。
5. 效果是否经受 no-action、matched-random 和 matched-delay baseline 检验。
6. 证据是否在 instrument-year 粒度稳定。
7. 下一步应 stop、refinement，还是 regime-conditional audit。

报告必须明确写出：

```text
This phase does not prove a new entry or launch baseline.
```

## 17. Implementation Command Contract

预期命令形态：

```bash
uv run python ep3/scripts/run_rolling_continuation_risk_state.py build \
  --config ep3/configs/rolling_continuation_risk_state.yaml

uv run python ep3/scripts/run_rolling_continuation_risk_state.py validate \
  --config ep3/configs/rolling_continuation_risk_state.yaml

uv run python ep3/scripts/run_rolling_continuation_risk_state.py report \
  --config ep3/configs/rolling_continuation_risk_state.yaml
```

这些 scripts 和 configs 不属于本次 requirement-writing step。
