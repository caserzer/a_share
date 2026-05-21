# EP5 Requirement 03: Downside Volatility Shock Rebound Natural Exit V0

## 1. 需求元信息

- 需求 id: `ep5_r03_downside_volatility_shock_rebound_natural_exit_v0`
- 简称: `r03_downside_volatility_shock_rebound_natural_exit_v0`
- 状态: requirement-draft research contract
- 所属 workflow: EP5
- 上游讨论: `ep5/discussion.md`
- 上游 R01 决策: `r01_no_local_feasibility_support`
- 上游 R02 决策: `r02_no_simple_continuation_support`
- 日期: 2026-05-21

R03 不是 R02 的参数扩展，也不是从 R02 descriptive bucket 中抽取局部改善样本来救回 `RS20 continuation`。R02 已经说明 simple RS20 continuation 在 H10 上同时无法通过 absolute、relative、date independence 与 baseline lift。R03 因此必须换一条经济含义不同的 exposure mainline。

R03 的新主线是：

```text
A-share 短周期 continuation 不成立，
但短期下跌波动冲击之后，
可能存在流动性修复 / 卖压衰竭 / 均值回归。
```

R03 只测试一个 frozen primary unit：

```text
r03_downside_volatility_shock_rebound_natural_exit_v0
```

它的核心不是"低波动买强势股"，而是"下跌冲击后的初步稳定修复"。这与 R02 的 RS20 continuation 是相反经济假设，不是 ret20、rank、horizon 或 regime 的修补式搜索。

## 2. 核心问题

R03 只回答一个问题：

```text
在 A-share PIT universe、本地 Qlib 数据、weekly close-observed signal、
next-open execution、扣成本、H5/H10/H20 natural exit 合同下，
短期下跌 + 高波动冲击之后出现初步稳定的股票，
是否在 validation-first 框架下显示出 after-cost、date-independent、
相对 matched comparator 和同周 downside baseline 的短周期修复结构？
```

经济假设拆成四段：

```text
1. 过去 5 个交易日明显下跌，代表近期卖压或恐慌冲击；
2. 过去 10 个交易日 realized volatility 处于横截面高位，代表冲击强度足够；
3. signal date 当天 close 高于前一日 close，代表没有继续破坏，出现初步稳定；
4. 当天成交额不低于前 20 日均额，代表修复不是无流动性死票中的价格噪声。
```

R03 的 positive 结论最多只能说明：

```text
downside-volatility shock rebound exposure 值得进入下一份 controlled discovery / holding diagnostic requirement。
```

它不得直接说明：

```text
可生产、可部署、可进入 allocator、可做 portfolio strategy、或可用 right-tail 管理救回负期望。
```

## 3. Non-Goals

R03 明确不做：

- 不做 R02 的 `ret20`、`rank_pct_ret20`、`ma20`、`money`、`horizon`、`collapse` 参数搜索；
- 不做 `RS20 + low volatility`、`RS20 + ATR filter`、`RS20 + bollinger contraction`；
- 不做 `ret20` 最高组 + 低波动；
- 不做 `mixed market_state`、低 beta、低波动、行业、liquidity bucket 的 validation 后子集选择；
- 不从 R02 的 `mixed market_state`、`rank 0.95-1.00`、`ret20 > 40%` descriptive readout 中抽取新规则；
- 不使用 big-winner / right-tail 标签参与 pass/fail；
- 不加 stop-loss、take-profit、trailing stop、confirm-add、加仓、减仓、再入场；
- 不做 hedged / market-neutral backtest；
- 不做 portfolio allocator、cash allocator 或 sleeve composition；
- 不复活 EP2 / EP4 的 family、fresh、sequence、hazard、volume_money、R05 preflight primitive；
- 不用 train 或 robustness 表现反推公式常量。

允许保留 right-tail / big-winner readout，但只能作为 post-entry diagnostic，不得参与 R03 final decision。

## 4. Phase Boundary

R03 的边界是：

```text
new exposure mainline, not R02 bucket rescue.
shock-rebound probe, not alpha claim.
```

R03 只允许一个 primary canonical unit 进入 pass/fail。任何以下行为都必须先写 R04 或 R03 revision requirement，不得在 E03 实现层暗含：

```text
ret5 threshold search
realized_vol window search
realized_vol rank threshold search
stabilization rule variants
money floor search
weekly cadence variants
horizon search
regime/beta/industry/liquidity subset selection
stop-loss/take-profit overlay
```

R03 的 baseline 只用于回答：

```text
shock-rebound selection 是否跑赢同周类似 downside / liquid 股票？
还是只是市场整体反弹或 downside basket 同期 beta？
```

baseline 不得单独生成 positive decision。

## 5. Data / Split Contract

R03 必须使用本地 PIT 数据，不得在线抓取。数据合同继承 R01 / R02：

| 数据 | 路径 / 口径 |
|:--|:--|
| Qlib PIT provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` |
| PIT industry membership | `data/targets/pit_industry_membership.csv` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` |
| Index state source | `SH000300` under `data/qlib/cn_data_pit` |

Split 固定继承 R01 / R02，不得修改：

```text
train_start      = 2017-07-04
train_end        = 2021-12-31
validation_start = 2022-01-01
validation_end   = 2023-12-31
robustness_start = 2024-01-01
robustness_end   = 2025-12-31
```

Train split 只允许用于：

- 校验 frozen unit 的样本量；
- 输出背景统计；
- E03 sanity check。

Train split 不得用于修改 `ret5`、`realized_vol10`、rank 阈值、stabilization、money floor、collapse、horizon、gate 或 baseline 口径。Validation 是 primary decision split。Robustness 是 read-only holdout，不能救回 validation failure。

## 6. Execution / Cost Contract

R03 继承 R01 / R02 的执行与成本合同：

```text
signal_date = D close 后可观察信号日
entry_execution_date = D 之后第一个可执行交易日
entry_price = adjusted open on entry_execution_date
natural_exit_target_date(H) =
  entry_execution_date 之后第 H 个交易日的 adjusted open
natural_exit_signal_date(H) =
  natural_exit_target_date(H) 之前一个交易日的 close-observed date
natural_exit_execution_date(H) =
  first executable open in exit execution search window

max_entry_execution_lag_trading_days = 5
max_exit_execution_lag_trading_days = 5

mainboard_limit_inference_pct = 0.095

horizon_set = H5, H10, H20
primary_horizon_for_decision = H10

buy_cost_bps  = 30
sell_cost_bps = 80
round_trip_cost_bps = 110

net_return =
  exit_price * (1 - sell_cost_bps / 10000)
  / (entry_price * (1 + buy_cost_bps / 10000))
  - 1
```

执行阻断 reason 集合继承 R01 / R02。blocked rows 必须保留进入 audit。E03 不得重新定义 execution rule、limit inference、cost model 或 split-boundary 处理。

## 7. Frozen Canonical Exposure Units

R03 只允许以下两个 canonical units：

| canonical_unit_id | role | final-decision authority |
|:--|:--|:--|
| `r03_downside_volatility_shock_rebound_natural_exit_v0` | primary shock-rebound exposure unit | 唯一可以单独支持 R03 continue/no-continue 判定的 unit |
| `r03_weekly_downside_nonselected_liquid_baseline_v0` | audit-only downside baseline | 不得单独触发 positive decision；只能作为 primary 的 baseline-lift downgrade guard |

任何新增 unit 必须先修改本 requirement。

### 7.1 `r03_downside_volatility_shock_rebound_natural_exit_v0`

定位：

```text
weekly-observed, downside-volatility shock, initial-stabilization,
short-horizon rebound exposure unit.
```

#### 7.1.1 Weekly observation calendar

R03 的 observation 日固定为：

```text
weekly_observation_date_D =
  每个 ISO calendar week 内、最后一个属于 trading calendar 的交易日。
```

该日 close 后计算信号。周内其他交易日不产生 signal。如果某个自然周没有 trading day，则该周不产生 signal。

#### 7.1.2 Feature definitions

所有特征均为 `signal_date D` close 后可观察，不得使用 D 后数据。

```text
ret5_D =
  close_D / close_{D - 5 trading days} - 1

daily_return_t =
  close_t / close_{t - 1 trading day} - 1

realized_vol10_D =
  population standard deviation of daily_return_t
  over the 10 trading-day returns ending at D
  requiring close_{D - 10 trading days} through close_D to exist

avg_money20_D =
  mean(money over last 20 trading days ending at D)

money_ma20_prev_D =
  mean(money over 20 trading days ending at D - 1 trading day)
```

`realized_vol10_D` 使用 population standard deviation (`ddof = 0`) 作为冻结口径。若任一必要 close 缺失、非正或不可计算，该 instrument 在该 observation date 不进入 rank cross-section。

#### 7.1.3 Volatility rank

`realized_vol10_rank_pct_D` 必须在同一 weekly observation date 的 PIT 高流动性横截面内计算：

```text
rank_cross_section(D) =
  instruments that on D satisfy:
    PIT universe member
    AND avg_money20_D >= 50,000,000 CNY
    AND close_D exists and close_D > 0
    AND close_{D - 1 trading day} exists and close_{D - 1} > 0
    AND close_{D - 5 trading days} exists and close_{D - 5} > 0
    AND close_{D - 10 trading days} through close_D exist and are positive
    AND money_D > 0
    AND volume_D > 0
    AND money_ma20_prev_D is finite and > 0
    AND realized_vol10_D is finite

realized_vol10_rank_pct_D:
  rank realized_vol10_D ascending, so highest realized vol is closest to 1.0
  use average rank for ties
  rank_pct = average_rank / cross_section_count
  require cross_section_count >= 100 for the observation date
```

若 `rank_cross_section_count < 100`，该 observation date 不得产生 7.1 signal，必须进入 rank audit，并标记：

```text
rank_cross_section_status = blocked_insufficient_vol_rank_cross_section
```

#### 7.1.4 Primary eligibility

公式固定为：

```text
eligible(D, instrument) =
  PIT universe member as of D
  AND avg_money20_D >= 50,000,000 CNY
  AND close_D exists and close_D > 0
  AND volume_D > 0
  AND money_D > 0
  AND ret5_D <= -0.0500
  AND realized_vol10_rank_pct_D >= 0.80
  AND close_D > close_{D - 1 trading day}
  AND money_D >= money_ma20_prev_D
```

经济含义：

```text
ret5 <= -5%                         -> 明显短期下跌冲击
realized_vol10_rank_pct >= 80%      -> 冲击强度处于横截面高位
close_D > close_{D-1}               -> 当天没有继续破坏，出现初步稳定
money_D >= money_ma20_prev_D        -> 修复不来自无流动性死票
```

#### 7.1.5 Episode collapse

```text
episode_merge_gap_trading_days = 20
one R03 event per instrument per 20-trading-day window;
within a 20-trading-day window, only the first eligible weekly_observation_date_D
is kept as the R03 signal_date for that instrument.
```

collapse 只在 instrument 维度内运行，不跨 instrument。同一 weekly observation date 内不同 instrument 互不抵消。

#### 7.1.6 Exposure

```text
entry = first executable next-open after weekly_observation_date_D
exit  = natural_exit_execution_date(H5/H10/H20)
no stop-loss
no take-profit
no trailing stop
no confirm-add
no model threshold
no industry filter
no regime filter
no validation-driven subset selection
```

#### 7.1.7 Frozen constants

以下常量在 R03 内不允许修改、不允许搜索、不允许 validation 后调整：

```text
ret5 window length                 = 5 trading days
ret5 downside threshold             = -0.0500
realized_vol window length          = 10 daily returns
realized_vol stdev ddof             = 0
realized_vol rank threshold         = 0.80
vol rank cross-section min count    = 100
avg_money20 window length           = 20 trading days
avg_money20 floor                   = 50,000,000 CNY
money_ma20_prev window length       = 20 trading days ending D - 1
stabilization price rule            = close_D > close_{D-1}
stabilization liquidity rule        = money_D >= money_ma20_prev_D
weekly observation cadence          = ISO-week last trading day
episode collapse gap                = 20 trading days
horizon_set                         = H5, H10, H20
primary_horizon                     = H10
```

### 7.2 `r03_weekly_downside_nonselected_liquid_baseline_v0`

定位：

```text
audit-only, date-aligned downside baseline answering whether primary
shock-rebound selection beats same-week nonselected downside liquid stocks.
```

7.2 不是独立 candidate event source。它必须与 7.1 的 signal dates 对齐：

```text
weekly_observation_date_D = same as 7.1.1

baseline is constructed only for D where
  7.1 has at least one generated primary event before execution blocking.
```

baseline feature scope 与 7.1 使用同一 feature panel 和 same-day rank 结果。Headline baseline 固定为：

```text
eligible_downside_baseline(D, instrument) =
  PIT universe member as of D
  AND avg_money20_D >= 50,000,000 CNY
  AND close_D exists and close_D > 0
  AND volume_D > 0
  AND money_D > 0
  AND ret5_D <= -0.0500
  AND realized_vol10_rank_pct_D >= 0.80

raw_primary_eligible_pre_collapse(D, instrument) =
  satisfies §7.1.4 primary eligibility on D
  before 20-trading-day episode collapse is applied

paired_nonselected_downside_baseline(D, instrument) =
  eligible_downside_baseline(D, instrument)
  AND NOT raw_primary_eligible_pre_collapse(D, instrument)
```

也就是说，final decision 的 baseline-lift guard 不是 broad market baseline，而是同周、同样 downside shock / high-vol 条件下，未通过 stabilization + liquidity repair 的 nonselected downside basket。

`paired_nonselected_downside_baseline` 必须排除 pre-collapse raw primary eligible names，而不是只排除 episode-collapse 后最终保留的 primary events。被 20 trading-day collapse 压掉的 raw primary eligible instrument 仍然满足 R03 rebound trigger，不得混入 baseline；否则 baseline 会偏离"未通过 stabilization / liquidity repair"的对照含义。

E03 可以额外输出 broad liquid baseline 作为解释字段：

```text
broad_liquid_baseline(D, instrument) =
  PIT universe member as of D
  AND avg_money20_D >= 50,000,000 CNY
  AND close_D exists and close_D > 0
  AND volume_D > 0
  AND money_D > 0
```

但 broad liquid baseline 不得作为 `baseline_lift_gate` authority。

7.2 baseline constants 同样冻结，不得在 E03 中搜索或 validation 后调整：

```text
paired_downside_baseline_min_complete_constituents_per_DH = 30
baseline_lift_min_comparable_observation_date_count       = 40
baseline_lift_min_year_comparable_observation_date_count  = 15
broad_liquid_baseline_role                                = explanatory_only
```

`paired_downside_baseline_min_complete_constituents_per_DH = 30` 是 paired downside / high-vol baseline 的最低可评估性 floor，不是收益调参阈值。它低于 R02 broad weekly liquid baseline 的 100，是因为 R03 baseline 同时要求 downside shock 与 high-vol rank，天然更稀疏；E03 必须在报告中披露每个 `(D,H)` 的 baseline executable constituent count 分布，不能只给 pass/fail。

Headline comparison 必须是 date-level，而不是 instrument-event count comparison：

```text
primary_date_equal_weight_return(D, H) =
  equal-weight net_return of all complete 7.1 primary events on D and H

baseline_date_equal_weight_return(D, H) =
  equal-weight net_return of all complete paired_nonselected_downside_baseline
  constituents on D and H

selection_lift_vs_baseline(D, H) =
  primary_date_equal_weight_return(D, H)
  - baseline_date_equal_weight_return(D, H)
```

baseline constituents 必须使用与 7.1 相同的 entry / exit / cost / blocked_reason 口径。baseline comparison status 必须按 `(D, H)` 穷举：

```text
baseline_executable_constituent_count(D, H) =
  count of paired_nonselected_downside_baseline constituents with complete execution
  on weekly_observation_date_D and horizon H

baseline_comparison_status(D, H) = comparable
  iff primary_decision_observation_date(D, H) = true
  AND baseline_executable_constituent_count(D, H)
      >= paired_downside_baseline_min_complete_constituents_per_DH

baseline_comparison_status(D, H) = blocked_insufficient_baseline_constituents
  iff primary_decision_observation_date(D, H) = true
  AND baseline_executable_constituent_count(D, H)
      < paired_downside_baseline_min_complete_constituents_per_DH

baseline_comparison_status(D, H) = not_applicable_no_primary_complete_event
  iff primary_decision_observation_date(D, H) = false
```

只有 `baseline_comparison_status(D, H) = comparable` 的 date row 才允许进入 `baseline_lift_gate(H)` denominator。baseline 不可评估不得被解释为 positive。

7.2 不使用 7.1 的 20-trading-day episode collapse 作为 headline comparison。它的作用是给每个 7.1 observation date 提供同日 downside baseline，而不是生成一个可交易事件源。

## 8. Forbidden Candidate Sources

R03 不允许使用以下来源生成 candidate 或修改 7.1 公式：

```text
R02 ret20 / rank_pct_ret20 / ma20 / RS20 continuation descriptive buckets
R02 mixed market_state / rank 0.95-1.00 / ret20 > 40% local improvement buckets
RS20 + atr20_pct < threshold
RS20 + realized_vol10_rank < threshold
RS20 + bollinger width contraction
ret20 top bucket + low volatility filter
market_state / beta_bucket / industry / liquidity validation-selected subset
EP5 R01 launch / money_surge / VCP canonical units
EP2 hazard / launch / confirm-add / holding-extension outputs
EP4 family / fresh / sequence / sleeve allocator / volume_money pool
BaseRate / Explore model predictions
```

这些来源可以在 report 中作为 historical context，但不得参与 R03 pass/fail，也不得替换 7.1 / 7.2 frozen formula。

## 9. Matched Comparator Contract

R03 继承 R01 / R02 的 matched comparator 合同：

- comparator candidate universe = `same entry_execution_date + same PIT eligibility + same executability at entry/exit + exclude event instrument`；
- liquidity quintile 在同 `signal_date D` 横截面内计算，口径为 `avg_money20_D`；
- comparator scope 优先级固定为：`same_industry_same_liquidity (>=30) -> same_industry_only (>=30) -> same_liquidity_only (>=30) -> same_day_pit_universe`；
- primary relative gate 使用 matched comparator 的 equal-weight arithmetic mean；
- 必须额外输出 `matched_comparator_net_return_median`、`same_day_universe_delta_return`、`industry_only_delta_return`、`liquidity_only_delta_return`、`SH000300_delta_return`；
- `same_day_pit_universe` 且 `matched_comparator_count < 100` -> `matched_comparator_status = blocked_insufficient_comparator`；
- `fallback_comparator_share > 0.30` -> 该 horizon 降级为 `weak_comparator_quality`，不得输出 `relative_positive = true`。

若 R03 触发 relative-only 后续方向，还必须满足多 comparator 稳定性：

```text
multi_comparator_relative_stable(H) =
  relative_positive(H)
  AND at least 3 of the following 4 validation mean deltas are > 0:
      mean_matched_delta_return
      same_day_universe_delta_return
      industry_only_delta_return
      liquidity_only_delta_return
  AND each validation calendar year has at least 2 of the 4 deltas >= -0.0025
  AND SH000300_delta_return is not the only positive relative readout
```

`SH000300_delta_return` 只能作为 beta / market context，不得单独支撑 relative lead。

## 10. Regime / Beta / Shock-State Decomposition

R03 继承 R01 / R02 的 regime / beta-state 分解口径，包括 SH000300 market_state、stock_beta120、beta_bucket 的 train-split-only tercile 阈值。

这些维度只用于解释，不得作为 selection gate：

```text
split
calendar_year
market_state
beta_bucket
industry
liquidity_quintile
canonical_unit_id
horizon
```

R03 额外输出 shock-state decomposition：

```text
ret5_bucket_at_D:
  ret5 <= -0.15
  -0.15 < ret5 <= -0.10
  -0.10 < ret5 <= -0.05

realized_vol10_rank_bucket_at_D:
  bucket_080_085
  bucket_085_090
  bucket_090_095
  bucket_095_100

stabilization_return_at_D =
  close_D / close_{D-1} - 1

stabilization_return_bucket_at_D:
  stabilization_return_at_D <= 0.00
  0.00 < stabilization_return_at_D <= 0.01
  0.01 < stabilization_return_at_D <= 0.03
  stabilization_return_at_D > 0.03

money_repair_ratio_at_D =
  money_D / money_ma20_prev_D

money_repair_ratio_bucket_at_D:
  money_repair_ratio_at_D < 0.50
  0.50 <= money_repair_ratio_at_D < 1.00
  1.00 <= money_repair_ratio_at_D < 1.50
  1.50 <= money_repair_ratio_at_D < 3.00
  money_repair_ratio_at_D >= 3.00
```

这些 bucket 都是 descriptive readout，不允许 validation 后选 bucket 升级为 pass。Primary unit 理论上只会落在 `stabilization_return_at_D > 0.00` 与 `money_repair_ratio_at_D >= 1.00` 的 bucket；baseline unit 可能落在非稳定或低 money repair bucket，因此 bucket 必须覆盖完整 signed / sub-1.0 区间，不能把 baseline failure state 静默混入 primary repair state。

## 11. Required Metrics

每个 `canonical_unit_id + horizon + split` 至少输出 R01 / R02 的 event-level 指标，并额外输出：

```text
weekly_observation_date_count
decision_observation_date_count
min_year_decision_observation_date_count
signal_event_count
entry_executable_count
complete_event_count
blocked_event_count
complete_event_share
unique_instrument_count
mean_ret5_at_D
median_ret5_at_D
mean_realized_vol10_at_D
mean_realized_vol10_rank_pct_at_D
mean_stabilization_return_at_D
mean_money_repair_ratio_at_D
mean_avg_money20_at_D
date_weighted_mean_net_return
date_weighted_median_net_return
date_weighted_mean_matched_delta_return
positive_observation_date_share_net
positive_observation_date_share_matched_delta
top1_observation_date_event_share
top5_observation_date_event_share
top1_observation_date_profit_contribution_share
vol_rank_cross_section_count_min
vol_rank_cross_section_count_median
baseline_comparable_observation_date_count
min_year_baseline_comparable_observation_date_count
baseline_lift_evaluable
baseline_executable_constituent_count_min
baseline_executable_constituent_count_p10
baseline_executable_constituent_count_median
baseline_executable_constituent_count_mean
selection_lift_vs_baseline_mean
selection_lift_vs_baseline_median
selection_lift_vs_baseline_p10
selection_lift_loss_rate_delta
broad_liquid_baseline_date_weighted_mean_net_return
```

必须输出 execution audit：

```text
blocked_reason
blocked_count
blocked_share
canonical_unit_id
horizon
split
```

必须输出 concentration audit：

```text
instrument_id
industry_id
entry_year
entry_date
observation_date
event_count
event_share
net_return_contribution_share
matched_delta_contribution_share
```

## 12. Gate Definitions

R03 判定口径继承 R01 / R02 的结构：

```text
sample gate
concentration gate
absolute_positive
relative_positive
baseline_lift_gate
robustness_confirmed
adjacent_horizon_clean
```

R03 的 date-level denominator 固定为：

```text
primary_decision_observation_date(D, H) =
  D has at least one complete 7.1 primary event for horizon H

decision_observation_date_count(H) =
  count of primary_decision_observation_date(D, H)

baseline_comparable_observation_date(D, H) =
  primary_decision_observation_date(D, H)
  AND baseline_comparison_status(D, H) = comparable

baseline_comparable_observation_date_count(H) =
  count of baseline_comparable_observation_date(D, H)
```

所有年度 gate 的 yearly rows 只允许包含有 qualifying observation 的 calendar year。empty calendar-year rows 必须排除在 year-level mean / all / any 计算之外，并单独审计；但如果 required year count 或 minimum yearly count 因某年为空而不足，gate 必须失败。

### 12.1 Sample Gate

R03 primary unit 的 validation sample gate 固定为：

```text
complete_event_count >= 300
complete_event_share >= 0.95
year_count = 2
min_year_complete_event_count >= 75
decision_observation_date_count >= 40
min_year_decision_observation_date_count >= 15
```

```text
sample_status = sample_pass
  iff all validation sample gate conditions above are true

sample_status = blocked_insufficient_date_independence_sample
  iff complete_event_count >= 300
  AND complete_event_share >= 0.95
  AND year_count = 2
  AND min_year_complete_event_count >= 75
  AND (
    decision_observation_date_count < 40
    OR min_year_decision_observation_date_count < 15
  )
```

若 validation `complete_event_count` 在 `[150, 299]`：

```text
sample_status = sample_limited_lead
```

若 validation `complete_event_count < 150`：

```text
sample_status = blocked_insufficient_sample
```

`sample_limited_lead`、`blocked_insufficient_sample` 和 `blocked_insufficient_date_independence_sample` 都不得输出 R03 continue。若 event count 过关但 date-level gate 不过关，必须输出 `blocked_insufficient_date_independence_sample`，不得用 event-row 密度掩盖 observation-date 集中。

新增 date independence gate：

```text
date_independence_gate(H) =
  decision_observation_date_count >= 40
  AND min_year_decision_observation_date_count >= 15
  AND top1_observation_date_event_share <= 0.08
  AND top5_observation_date_event_share <= 0.30
  AND date_weighted_mean_net_return > 0.0000
  AND date_weighted_mean_matched_delta_return > 0.0000
  AND each validation calendar year date_weighted_mean_net_return >= -0.0025
  AND each validation calendar year date_weighted_mean_matched_delta_return >= -0.0025
  AND positive_observation_date_share_net >= 0.50
  AND positive_observation_date_share_matched_delta >= 0.50
```

### 12.2 Concentration Gate

R03 concentration gate 固定为：

```text
top1_instrument_event_share <= 0.05
top5_instrument_event_share <= 0.20
top1_industry_event_share <= 0.35
top1_entry_date_event_share <= 0.08
top1_observation_date_event_share <= 0.08
top5_observation_date_event_share <= 0.30
top1_observation_date_profit_contribution_share <= 0.20
fallback_comparator_share <= 0.30
```

任一失败时，unit 可保留描述性 readout，但不得输出 R03 continue。

### 12.3 Absolute Positive

`absolute_positive(H) = true` 当且仅当 validation split 的当前 horizon summary row 同时满足：

```text
mean_net_return > 0.0000
median_net_return >= -0.0025
p10_net_return >= -0.0800
loss_rate <= 0.55
each validation calendar year mean_net_return >= -0.0025
```

### 12.4 Relative Positive

`relative_positive(H) = true` 当且仅当 validation split 的当前 horizon summary row 同时满足：

```text
relative_comparable_event_share >= 0.95
blocked_insufficient_comparator_count / complete_event_count <= 0.05
fallback_comparator_share <= 0.30
mean_matched_delta_return > 0.0000
each validation calendar year mean_matched_delta_return >= -0.0025
```

并且以下三项至少两项成立：

```text
median_matched_delta_return >= 0.0000
p10_matched_delta_return >= 0.0000
matched_loss_rate_delta <= 0.0000
```

matched delta statistics 仅在 `matched_comparator_status = comparable` 上计算。

### 12.5 Baseline Lift Gate

`baseline_lift_gate(H)` 用于防止把同周 downside basket 的市场反弹误判为 primary shock-rebound selection edge。

```text
baseline_lift_evaluable(H) =
  baseline_comparable_observation_date_count >= 40
  AND min_year_baseline_comparable_observation_date_count >= 15

baseline_lift_gate(H) =
  baseline_lift_evaluable(H)
  AND selection_lift_vs_baseline_mean > 0.0000
  AND each validation calendar year selection_lift_vs_baseline_mean >= -0.0025
  AND at least 2 of the following 3 are true:
      selection_lift_vs_baseline_median >= 0.0000
      selection_lift_vs_baseline_p10 >= 0.0000
      selection_lift_loss_rate_delta <= 0.0000
```

若 H10 满足 `h10_validated_pass`，但 `baseline_lift_evaluable(H10) = false`，不得解释为 beta exposure，必须输出 baseline not evaluable 类结论。只有当 `baseline_lift_evaluable(H10) = true` 且 `baseline_lift_gate(H10) = false` 时，才允许降级为 `r03_downside_beta_or_market_rebound_only_no_selection_pass`。

对于 `absolute_positive(H10) = true`、`relative_positive(H10) = false` 的 abs-only 状态，baseline guard 同样必须先判定：

```text
abs-only + baseline_lift_evaluable(H10) = false
  -> baseline not evaluable, not beta-only

abs-only + baseline_lift_evaluable(H10) = true
  AND baseline_lift_gate(H10) = false
  -> downside beta / market rebound only

abs-only + baseline_lift_gate(H10) = true
  -> absolute rebound with baseline lift but no matched-relative support;
     report as conflict lead, not beta-only and not continue
```

### 12.6 Robustness Confirmation

Robustness 不允许救回 validation failure。若 validation H10 已通过，robustness 只用于确认稳定性：

```text
robustness_baseline_lift_evaluable(H10) =
  robustness_baseline_comparable_observation_date_count >= 40
  AND min_robustness_year_baseline_comparable_observation_date_count >= 15

robustness_confirmed(H10) =
  robustness_complete_event_count >= 300
  AND robustness_complete_event_share >= 0.95
  AND robustness_year_count = 2
  AND min_robustness_year_complete_event_count >= 75
  AND robustness_decision_observation_date_count >= 40
  AND min_robustness_year_decision_observation_date_count >= 15
  AND robustness_relative_comparable_event_share >= 0.95
  AND robustness_blocked_insufficient_comparator_count / robustness_complete_event_count <= 0.05
  AND robustness_mean_net_return >= -0.0025
  AND robustness_median_net_return >= -0.0050
  AND robustness_p10_net_return >= -0.0900
  AND robustness_loss_rate <= 0.58
  AND robustness_mean_matched_delta_return >= -0.0025
  AND each robustness calendar year mean_net_return >= -0.0050
  AND each robustness calendar year mean_matched_delta_return >= -0.0050
  AND robustness_top1_instrument_event_share <= 0.05
  AND robustness_top5_instrument_event_share <= 0.20
  AND robustness_top1_industry_event_share <= 0.35
  AND robustness_top1_observation_date_event_share <= 0.08
  AND robustness_top5_observation_date_event_share <= 0.30
  AND robustness_fallback_comparator_share <= 0.30
  AND robustness_baseline_lift_evaluable(H10)
  AND robustness_selection_lift_vs_baseline_mean >= -0.0025
```

若 robustness 不满足，上述 validation pass 必须降级为：

```text
r03_unstable_validation_only_lead
```

### 12.7 H10 Validated Pass And Stock Selection Supported

```text
h10_validated_pass(unit) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10)

stock_selection_supported(unit, H10) =
  h10_validated_pass(unit)
  AND baseline_lift_gate(H10)
```

## 13. Four-Quadrant Interpretation

R03 必须对 primary H10 unit 输出以下四象限：

| absolute_positive | relative_positive | 解释 | 允许后续 |
|:--|:--|:--|:--|
| true | true | downside shock rebound 可能同时具备 long-only tradability 与 residual edge。 | 还必须通过 baseline_lift_gate、robustness_confirmed(unit)、adjacent_horizon_clean，才允许写 R04 controlled discovery 或 holding diagnostic。 |
| false | true | 可能存在 residual rebound edge，但 long-only deployability 被 beta / regime pressure 阻断。 | 只有 multi_comparator_relative_stable 与 baseline_lift_gate 同时通过时，才能写 hedged / relative feasibility audit；不得写 long-only pass。 |
| true | false | 可能只是市场整体反弹、downside basket beta 或流动性修复 beta；也可能是有 baseline lift 但 matched-relative 不成立的冲突 lead。 | 必须先看 7.2 baseline lift；baseline 不可评估不能解释为 beta，baseline lift 通过也不得直接 continue。 |
| false | false | downside volatility shock rebound 在当前 PIT、成本、horizon 下不成立。 | 不得扩阈值 grid；R03 主线暂停或重新定义 exposure mainline。 |

H5 / H20 只作为形状审计：

```text
horizon_pass(H) =
  sample gate for horizon H
  AND concentration gate for horizon H
  AND date_independence_gate(H)
  AND absolute_positive(H)
  AND relative_positive(H)

strongly_negative(H) =
  complete_event_count >= 150
  AND mean_net_return < -0.0025
  AND mean_matched_delta_return < -0.0025
```

Adjacent horizon 可评估性只用于判断 H10 pass 是否被 H5 / H20 形状破坏，不等同于 H5 / H20 pass：

```text
adjacent_horizon_shape_status(H) = evaluable
  iff complete_event_count >= 150
  AND complete_event_share >= 0.90
  AND mean_net_return is finite
  AND mean_matched_delta_return is finite

adjacent_horizon_shape_status(H) = adjacent_horizon_not_evaluable
  otherwise
```

H10 pass 后，如果 H5 或 H20 strongly negative，则不得输出 supported continue。

## 14. Big-Winner / Right-Tail Diagnostic

R03 必须保留 right-tail readout，但不得参与 pass/fail：

```text
big_winner_horizon = H120
big_winner_threshold = +50% gross max close return from entry_price
right_tail_thresholds = +20%, +50%
```

split / censoring 规则继承 R01 / R02：

```text
right_tail_path_status =
  complete_same_split_120d
  complete_cross_split_120d_readonly
  censored_split_boundary
  censored_provider_end
  blocked_missing_forward_path

right_tail_status =
  hit_plus50
  hit_plus20_only
  no_hit_complete
  censored_not_evaluable
  blocked_missing_forward_path
```

官方 split-level right-tail aggregate 只能使用 `complete_same_split_120d`。right-tail readout 只能回答：

```text
若短周期 exposure 本身成立，是否值得另写 holding-extension diagnostic。
```

禁止回答：

```text
短周期 exposure 失败，但 +20% / +50% 命中率看起来高，所以 R03 passed。
```

## 15. Final Decision Contract

R03 final decision 只能是以下之一：

```text
r03_downside_volatility_shock_rebound_supported_continue_research
r03_unstable_validation_only_lead
r03_unstable_horizon_shape_no_search_allowed
r03_adjacent_horizon_not_evaluable_validation_lead
r03_relative_rebound_edge_only_hedged_or_regime_audit_required
r03_downside_beta_or_market_rebound_only_no_selection_pass
r03_absolute_rebound_only_baseline_lift_no_relative_pass
r03_baseline_not_evaluable_validation_lead
r03_horizon_specific_lead_only_no_search_allowed
r03_sample_limited_primary_lead_only
r03_no_downside_rebound_support
r03_blocked_data_or_execution_contract
```

辅助定义：

```text
adjacent_horizon_clean(unit) =
  NOT strongly_negative(H5)
  AND NOT strongly_negative(H20)
  AND H5 adjacent_horizon_shape_status != adjacent_horizon_not_evaluable
  AND H20 adjacent_horizon_shape_status != adjacent_horizon_not_evaluable

adjacent_horizon_not_evaluable(unit) =
  H5 adjacent_horizon_shape_status = adjacent_horizon_not_evaluable
  OR H20 adjacent_horizon_shape_status = adjacent_horizon_not_evaluable

sample_limited_return_lead(unit, H10) =
  sample_status = sample_limited_lead
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10)

baseline_not_evaluable_validation_lead(unit, H10) =
  h10_validated_pass(unit)
  AND baseline_lift_evaluable(H10) = false

robustness_confirmed(unit) :=
  robustness_confirmed(H10)

relative_only_audit_supported(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND relative_positive(H10)
  AND multi_comparator_relative_stable(H10)
  AND baseline_lift_gate(H10)
  AND absolute_positive(H10) = false

relative_only_baseline_not_evaluable(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND relative_positive(H10)
  AND multi_comparator_relative_stable(H10)
  AND baseline_lift_evaluable(H10) = false
  AND absolute_positive(H10) = false

absolute_only_baseline_not_evaluable(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10) = false
  AND baseline_lift_evaluable(H10) = false

absolute_only_beta_or_market_rebound(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10) = false
  AND baseline_lift_evaluable(H10)
  AND baseline_lift_gate(H10) = false

absolute_only_baseline_lift_no_relative_pass(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10) = false
  AND baseline_lift_gate(H10)
```

决策优先级（first-match priority）：

1. 若任一 required artifact 缺失、schema 不合法、split 泄漏、formula hash 不匹配、execution/cost/comparator 被 E03 修改，输出 `r03_blocked_data_or_execution_contract`。
2. 若 primary unit 满足 `stock_selection_supported(unit, H10)`、`robustness_confirmed(unit)` 和 `adjacent_horizon_clean`，输出 `r03_downside_volatility_shock_rebound_supported_continue_research`。
3. 若 primary unit 满足 `baseline_not_evaluable_validation_lead(unit, H10)`，输出 `r03_baseline_not_evaluable_validation_lead`。
4. 若 primary unit 满足 `h10_validated_pass`、`baseline_lift_evaluable(H10) = true`，但 `baseline_lift_gate(H10) = false`，输出 `r03_downside_beta_or_market_rebound_only_no_selection_pass`。
5. 若 primary unit 满足 `stock_selection_supported(unit, H10)`，但 `robustness_confirmed(unit) = false`，输出 `r03_unstable_validation_only_lead`。
6. 若 primary unit 满足 `stock_selection_supported(unit, H10)` 和 `robustness_confirmed(unit)`，且任一 adjacent horizon `strongly_negative = true`，输出 `r03_unstable_horizon_shape_no_search_allowed`。
7. 若 primary unit 满足 `stock_selection_supported(unit, H10)` 和 `robustness_confirmed(unit)`，没有 adjacent horizon `strongly_negative = true`，但 `adjacent_horizon_not_evaluable = true`，输出 `r03_adjacent_horizon_not_evaluable_validation_lead`。
8. 若 primary unit 满足 `relative_only_audit_supported(unit, H10)`，输出 `r03_relative_rebound_edge_only_hedged_or_regime_audit_required`。
9. 若 primary unit 满足 `relative_only_baseline_not_evaluable(unit, H10)`，输出 `r03_baseline_not_evaluable_validation_lead`。
10. 若 primary unit 满足 `absolute_only_baseline_not_evaluable(unit, H10)`，输出 `r03_baseline_not_evaluable_validation_lead`。
11. 若 primary unit 满足 `absolute_only_beta_or_market_rebound(unit, H10)`，输出 `r03_downside_beta_or_market_rebound_only_no_selection_pass`。
12. 若 primary unit 满足 `absolute_only_baseline_lift_no_relative_pass(unit, H10)`，输出 `r03_absolute_rebound_only_baseline_lift_no_relative_pass`。
13. 若 primary unit 只有 H5 或 H20 满足 `horizon_pass(H)` 和 `baseline_lift_gate(H)`、H10 不满足 `horizon_pass(H10)`，输出 `r03_horizon_specific_lead_only_no_search_allowed`。
14. 若 primary unit 满足 `sample_limited_return_lead(unit, H10)` 和 `baseline_lift_gate(H10)`，输出 `r03_sample_limited_primary_lead_only`。
15. 其他所有情况输出 `r03_no_downside_rebound_support`。

当多个规则同时可命中时，以 first-match priority 为唯一 authority；final report 必须并列披露所有 would-have-matched rules。

若 `final_decision = r03_baseline_not_evaluable_validation_lead`，`r03_final_decision_inputs.csv` 必须额外输出：

```text
matched_rule_id in {rule_3, rule_9, rule_10}
baseline_not_evaluable_origin in {
  h10_validated_pass,
  rel_only,
  abs_only
}
```

其中：

```text
rule_3  -> baseline_not_evaluable_origin = h10_validated_pass
rule_9  -> baseline_not_evaluable_origin = rel_only
rule_10 -> baseline_not_evaluable_origin = abs_only
```

| final_decision | 允许后续 |
|:--|:--|
| `r03_downside_volatility_shock_rebound_supported_continue_research` | 只能写 controlled discovery / holding diagnostic requirement；不得直接 production。 |
| `r03_relative_rebound_edge_only_hedged_or_regime_audit_required` | 只能写 hedged / relative feasibility audit；不得写 long-only deployment。 |
| `r03_downside_beta_or_market_rebound_only_no_selection_pass` | 只能做 beta / market rebound attribution；不得当 stock-selection edge。 |
| `r03_absolute_rebound_only_baseline_lift_no_relative_pass` | 只能作为 abs-only conflict lead 披露；不得写 continue，不得当 matched-relative edge。 |
| `r03_unstable_validation_only_lead` | 只能记录为 unstable lead；robustness 不允许救回 validation。 |
| `r03_unstable_horizon_shape_no_search_allowed` | 不得通过 horizon search 修复。 |
| `r03_adjacent_horizon_not_evaluable_validation_lead` | 只能先补充 adjacent horizon 可评估性审计。 |
| `r03_baseline_not_evaluable_validation_lead` | 只能先复核 baseline coverage；不得解释为 positive。 |
| `r03_horizon_specific_lead_only_no_search_allowed` | 不得把 H5/H20 局部 lead 升级为 H10 pass。 |
| `r03_sample_limited_primary_lead_only` | 只能先做样本来源和执行阻断复核，不得放宽阈值堆样本。 |
| `r03_no_downside_rebound_support` | R03 主线暂停；不得扩 grid 救回。 |
| `r03_blocked_data_or_execution_contract` | 必须先修数据 / 工程合同，不得解释经济结论。 |

## 16. Reporting Requirements

最终报告必须用中文回答以下问题：

1. R03 final decision 是什么？命中了哪条 priority rule？哪些 would-have-matched rules 被披露？
2. H10 primary quadrant 是哪一象限？absolute / relative 各自失败或通过的根因是什么？
3. H10 validation 的 event count、complete share、decision observation date count、yearly count 是否达标？
4. 主要 execution blocking reason 是什么？是否存在 PIT universe、limit、split boundary 或 missing open 的结构性问题？
5. H10 absolute gate 的 mean、median、p10、loss rate、年度 mean 分别是多少？
6. H10 relative gate 的 matched delta、median delta、p10 delta、matched loss-rate delta、fallback share、年度 delta 分别是多少？
7. date independence 是否通过？date-weighted return / delta 和 positive date share 是否支持结论？
8. downside baseline 是否可评估？primary 是否跑赢同周 nonselected downside high-vol basket？
   必须披露 `baseline_executable_constituent_count(D,H)` 的 min / p10 / median / mean。
9. broad liquid baseline 是否显示只是市场整体反弹？
10. H5 / H20 是否提供相邻 horizon 形状确认，还是只有 horizon-specific lead？
11. robustness 2024-2025 是确认、翻转，还是只读改善？
12. 失败是否来自样本不足、execution completeness、baseline 不可评估、baseline lift 失败、relative comparator 弱，还是 exposure 本身无效？
13. regime / beta / industry / liquidity decomposition 是否说明结果只是 market / beta / liquidity state？
14. shock-state decomposition 是否显示 ret5 跌幅、vol rank、stabilization strength、money repair ratio 的描述性差异？这些差异不得升级为新规则。
15. right-tail / +20% / +50% readout 是否仅作为 post-entry diagnostic 披露？
16. 根据 R03 结果，下一步允许写什么 requirement？哪些方向被禁止？

报告必须显式写出以下边界句：

```text
R03 did not tune ret5, realized_vol10, volatility rank, stabilization, money floor, horizon, or collapse.
R03 did not reuse R02 descriptive buckets as candidate rules.
R03 did not use big-winner labels for pass/fail.
R03 did not tune thresholds after validation.
R03 did not approve a production strategy.
R03 did not run a hedged or market-neutral backtest.
R03 did not let the audit-only downside baseline create a positive decision.
```

## 17. Required Artifacts / Validator Contract

E03 至少必须输出：

| artifact | 内容 |
|:--|:--|
| `r03_run_manifest.json` | run metadata、git sha、config hash、input path、split、formula constants。 |
| `r03_artifact_hashes.json` | 所有输出文件 hash。 |
| `r03_validation.json` | validator status 与每条 check。 |
| `r03_canonical_unit_registry.csv` | canonical units、role、formula hash、final-decision authority。 |
| `r03_formula_freeze_audit.csv` | frozen constants 与 requirement 对齐审计。 |
| `r03_input_data_audit.csv` | provider、calendar、PIT universe、industry、index source coverage。 |
| `r03_event_generation_audit.csv` | signal generation、weekly observation、collapse、rank cross-section 状态。 |
| `r03_vol_rank_cross_section_audit.csv` | realized_vol10 rank cross-section count 与 blocked dates。 |
| `r03_execution_block_audit.csv` | blocked reason by split / horizon / unit。 |
| `r03_event_summary_by_unit_horizon_split.csv` | split-level event summary。 |
| `r03_event_summary_by_unit_horizon_year.csv` | yearly event summary。 |
| `r03_absolute_gate_audit.csv` | absolute_positive authority。 |
| `r03_relative_gate_audit.csv` | relative_positive authority。 |
| `r03_date_independence_audit.csv` | date-level denominator 与 date-weighted metrics。 |
| `r03_baseline_date_comparison.csv` | primary vs paired nonselected downside baseline date-level comparison。 |
| `r03_baseline_lift_audit.csv` | baseline_lift_gate authority。 |
| `r03_multi_comparator_relative_audit.csv` | matched / same-day / industry / liquidity / index comparator readout。 |
| `r03_regime_beta_decomposition.csv` | regime / beta / industry / liquidity decomposition。 |
| `r03_shock_state_decomposition.csv` | ret5 / vol rank / stabilization / money repair bucket readout。 |
| `r03_concentration_gate_audit.csv` | instrument / industry / date / observation-date concentration。 |
| `r03_horizon_shape_audit.csv` | H5 / H10 / H20 shape 与 strongly_negative。 |
| `r03_right_tail_readout.csv` | +20% / +50% post-entry diagnostic。 |
| `r03_right_tail_censoring_audit.csv` | right-tail split/censoring status。 |
| `r03_final_decision_inputs.csv` | final decision 所有 rule input，含 would-have-matched rules；当 final decision 是 `r03_baseline_not_evaluable_validation_lead` 时，必须含 `matched_rule_id` 与 `baseline_not_evaluable_origin`。 |
| `r03_final_decision_replay_audit.csv` | 按 §15 first-match priority replay 的唯一 authority。 |
| `r03_final_decision.csv` | 单行最终结论。 |
| `r03_final_report.md` | 中文最终报告。 |

Validator 必须检查：

1. No online fetch; all input paths are local PIT paths.
2. Split ranges exactly match §5.
3. Formula constants and baseline constants exactly match §7.1.7 and §7.2.
4. Weekly observation calendar is ISO-week last trading day.
5. Realized volatility uses 10 daily returns ending D and `ddof = 0`.
6. Volatility rank uses same-day PIT high-liquidity cross-section and average rank tie handling.
7. Primary eligibility exactly matches §7.1.4.
8. Episode collapse is per instrument, 20 trading days, first signal kept.
9. Execution / cost contract matches §6.
10. Paired nonselected downside baseline excludes `raw_primary_eligible_pre_collapse`, not only post-collapse kept primary events.
11. Baseline comparison status is exhaustive and only comparable rows enter baseline_lift_gate.
12. Baseline_lift_gate uses paired nonselected downside baseline, not broad liquid baseline.
13. Baseline executable constituent count distribution is reported and the frozen per-(D,H) threshold is 30.
14. Sample status includes `blocked_insufficient_date_independence_sample` for event-count-sufficient but date-level-insufficient cases.
15. Relative-only final decision rule 8 requires both `baseline_lift_gate(H10) = true` and `multi_comparator_relative_stable(H10) = true`; matched-comparator stability alone is insufficient.
16. Relative-only baseline-not-evaluable state maps to `r03_baseline_not_evaluable_validation_lead`, not `r03_no_downside_rebound_support`.
17. Abs+/rel- final decision follows the three-way baseline guard: not evaluable / beta-only / abs-only conflict lead.
18. `r03_baseline_not_evaluable_validation_lead` requires `matched_rule_id` and `baseline_not_evaluable_origin in {h10_validated_pass, rel_only, abs_only}` in `r03_final_decision_inputs.csv`.
19. Matched comparator scope and fallback rules match §9.
20. Empty year rows are excluded from year-level metrics but cannot manufacture a pass.
21. Robustness cannot rescue validation failure.
22. Right-tail readout does not enter pass/fail.
23. R02 descriptive bucket fields do not appear as selection gates.
24. Final decision priority matches §15 rules 1-15.
25. Final report includes the boundary statements in §16.

## 18. Relationship to E01 / E02 / E03

E01 / E02 已经把 EP5 R01 / R02 的 harness 落到执行、成本、split、comparator、regime、right-tail、gate、validator 的冻结口径。R03 不得在工程层重新定义这些口径。

E03 只允许：

```text
注册新 canonical_unit_id (r03_downside_volatility_shock_rebound_natural_exit_v0)
注册新 baseline_unit_id (r03_weekly_downside_nonselected_liquid_baseline_v0)
扩展 realized_vol10 / stabilization / money_repair feature builder
扩展 ret5 / vol_rank / stabilization / money_repair shock-state decomposition
扩展 paired_nonselected_downside baseline 与 date-level lift
扩展 §15 final decision rules 1-15
扩展 §17 validator checks 1-25
```

E03 不得改变：

```text
canonical_unit_id 角色 / final-decision authority
horizon_set / cost / split / weekly cadence / episode collapse
matched comparator / fallback / multi_comparator_relative_stable
date_independence_gate / baseline_lift_gate / concentration gate 数值
big-winner read-only boundary
```

## 19. Implementation Boundary

This requirement is ready for engineering planning only after review. E03 implementation must be config-driven and replayable, but must not change the research contract.

If E03 finds any of the following, it must stop and return to R03 requirement review:

```text
feature cannot be computed as-of D without leakage
baseline is systematically not evaluable under paired downside threshold
sample is blocked_insufficient_sample or blocked_insufficient_date_independence_sample in train and validation
execution contract conflicts with R01/R02 harness
formula constants need modification
new candidate source seems necessary
```

R03 is allowed to fail. A clean `r03_no_downside_rebound_support` is a valid research outcome and must not be patched through threshold search.
