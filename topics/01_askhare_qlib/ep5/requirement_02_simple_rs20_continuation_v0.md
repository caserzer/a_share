# EP5 Requirement 02: Simple RS20 Continuation V0

## 1. 需求元信息

- 需求 id: `ep5_r02_simple_rs20_continuation_v0`
- 简称: `r02_simple_rs20_continuation_v0`
- 状态: requirement-ready research contract
- 所属 workflow: EP5
- 上游讨论: `ep5/discussion.md`
- 上游决策: `ep5/outputs/r01_short_horizon_local_feasibility_probe_v1/reports/r01_final_report.md`（final_decision = `r01_no_local_feasibility_support`）
- 上游 harness: `ep5/engineering_plan_01_short_horizon_audit_harness.md`
- 日期: 2026-05-21

R02 不是 R01 的 grid expansion。R01 已经输出 `r01_no_local_feasibility_support`，并明确禁止在 launch / breakout / money_surge / VCP 公式上做阈值搜索、horizon 网格、stop-loss / take-profit、行业内分别调参或 regime-switching 之类的修补式实验。R02 是 EP5 的 **renormalized simple exposure baseline**：换一条机制更简单、自由度更低、可解释性更强的 short-horizon exposure 路径，让 EP5 实验链路继续跑，并回答一个最小但独立的经济问题。

R02 不宣布找到 alpha。它的目的不是 production，也不是 pass。它的目的只有一个：让 EP5 在不滑入 grid expansion 的前提下，知道 short-horizon exposure timing 这条主线**是否还值得继续研究**。

R02 的 continue 结论必须同时避免两类假阳性：

```text
1. event-row 样本很多，但其实只是少数 weekly observation dates 的同期市场暴露；
2. 7.1 RS20 selection 看起来赚钱，但同周高流动性 PIT universe baseline 同样或更强。
```

因此 7.2 baseline 不能单独输出 pass，但可以作为 7.1 的 downgrade guard：如果 7.1 无法稳定跑赢同周、高流动性、可执行的 non-selected baseline，R02 不得输出 `r02_simple_continuation_supported_continue_research`。

## 2. 核心问题

R02 只回答一个问题：

```text
在 A-share PIT universe、本地 Qlib 数据、next-open execution、扣成本、
H5/H10/H20 固定持有合约下，
一个低自由度、横截面相对强度、固定每周一次观察的 simple continuation exposure
是否在 validation-first、after-cost、matched-comparator 框架下显示出
可继续研究 (continue-research-worthy) 的初步结构？
```

继续研究只意味着 R03 可以被讨论；不意味着该 exposure 是 alpha、可部署、或可进入 portfolio allocator。

经济假设只有一条：

```text
在 PIT 高流动性宇宙内，
最近 20 个交易日横截面相对强、且仍处于短期上行趋势的股票，
是否在接下来的 H5/H10/H20 内显示出
扣成本、相对同日同宇宙 comparator 的 continuation 收益结构？
```

R02 不研究 launch、breakout、money_surge、VCP、base、family、fresh、sequence、hazard、confirm-add、holding-extension、stop-loss、take-profit、big-winner entry 或 right-tail optionality。

## 3. Non-Goals

R02 明确不做：

- 不做 R01 canonical units 的阈值放宽或参数变体；不重写 launch / money_surge / VCP；
- 不做 ret20 窗口搜索、rank_pct 阈值搜索、money 阈值搜索、horizon 搜索；
- 不加 stop-loss、take-profit、trailing stop、confirm-add、再入场、加仓、减仓；
- 不做行业内分别选最优阈值；不做 regime-on/off 后再买；不做 beta-bucket subset selection；
- 不在 validation 后修改任何 R02 公式常量、event collapse、horizon、execution lag、sample gate、concentration gate 或 comparator 规则；
- 不做 big-winner entry，不使用 +20% / +50% 标签作为 pass/fail；
- 不做 hedged / market-neutral 回测，不写 portfolio allocator；
- 不复活 EP2 launch / confirm-add / holding-extension 系统；
- 不复用 EP4 family / fresh / sequence / sleeve allocator / volume_money pool；
- 不重新定义 R01 的 PIT universe、execution rule、cost model、horizon、split 或 matched comparator 公式。

R02 可以保留 big-winner / right-tail readout，但只能是 post-entry diagnostic，不得参与 R02 continue/no-continue 判定。

## 4. Phase Boundary

R02 的边界是：

```text
renormalize, not search.
continue-research probe, not alpha claim.
```

R02 只允许一个新的 canonical unit 进入 pass/fail。任何"换一种 RS 公式"、"换一种 rank 阈值"、"换一种持有周期" 的尝试都属于 R02 grid expansion，必须先回到 R03 重新定义 requirement。

R02 的 positive / continue 结论必须是 stock-selection lift，不得只是 weekly liquid universe beta。7.2 baseline 不是第二个 candidate，也不能单独产生 pass；但如果 7.2 baseline 解释掉 7.1 的收益，R02 必须降级为 beta / market exposure only。

R02 的输出**不允许**直接触发：

```text
holding-extension requirement
right-tail optionality requirement
stop-loss / take-profit requirement
allocator / sleeve composition requirement
hedged / market-neutral strategy backtest
large-scale alpha discovery requirement
```

R02 的输出可以触发的最远 next requirement 是：

```text
R03 controlled discovery under strict low-dimensional search,
或
R02-followup hedged / relative feasibility audit (audit only, not backtest),
或
EP5 phase pause / 重新选 exposure 主线。
```

## 5. Data / Split Contract

R02 必须使用本地 PIT 数据，不得在线抓取。数据合同与 R01 §5 完全一致：

| 数据 | 路径 / 口径 |
|:--|:--|
| Qlib PIT provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` |
| PIT industry membership | `data/targets/pit_industry_membership.csv` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` |
| Index state source | `SH000300` under `data/qlib/cn_data_pit` |

Split 与 R01 完全一致，不得修改：

```text
train_start      = 2017-07-04
train_end        = 2021-12-31
validation_start = 2022-01-01
validation_end   = 2023-12-31
robustness_start = 2024-01-01
robustness_end   = 2025-12-31
```

Train split 只允许用于：

- 校验 canonical unit 是否样本充足；
- 输出背景统计；
- 在 E02 实现阶段做 sanity check。

Train split 不得用于重新选择 R02 公式常量、rank_pct 阈值、ret 窗口、horizon、event collapse 或 sample gate。Validation 是 primary decision split。Robustness 是 read-only holdout：不能救回 validation failure。

## 6. Execution / Cost Contract

R02 完全继承 R01 §6 的执行 / 成本合同。E02 不得替换。最低复述：

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

执行阻断 reason 集合、blocked rows 必须保留进入 audit 的口径，全部继承 R01 §6。

如果 E02 在实现时发现某条执行 / 成本 / 阻断口径与 R01 harness 不一致，必须先回到 R01 / E01 修订，不得在 R02 工程层重新定义。

## 7. Frozen Canonical Exposure Units

R02 只允许以下两个 canonical units，且角色严格区分：

| canonical_unit_id | role | final-decision authority |
|:--|:--|:--|
| `r02_simple_rs20_continuation_natural_exit_v0` | primary simple continuation exposure unit | 唯一可以单独支持 R02 continue/no-continue 判定的 unit |
| `r02_weekly_liquid_universe_baseline_v0` | audit-only baseline | 不得单独触发任何 positive decision；但必须作为 7.1 的 baseline-lift downgrade guard |

任何新增 unit 必须先修改本 requirement，不得在 E02 config 中暗含扩展。

### 7.1 `r02_simple_rs20_continuation_natural_exit_v0`

定位：

```text
weekly-observed, low-degree-of-freedom, cross-sectional relative-strength
short-horizon continuation exposure unit.
```

#### 7.1.1 Weekly observation calendar

R02 不允许逐日扫描，也不允许月末 / 半月末 / 任意自定义节奏。observation 日固定为：

```text
weekly_observation_date_D =
  每个 ISO calendar week 内、最后一个属于 trading calendar 的交易日。
```

也就是说：

- 该自然周内，trading calendar 中最后一个 trading day 即为该周的 `signal_date D`；
- 如果整个自然周没有 trading day（连续假期周），该周不产生 R02 signal；
- 周内其他交易日不产生 signal，也不进入 R02 evaluation。

不允许使用 calendar 自定义周期（每 5 个交易日、每 7 个自然日）替换 ISO-week-end-of-trading-week 口径。

#### 7.1.2 Eligibility rule

公式固定为：

```text
ret20_D = close_D / close_{D - 20 trading days} - 1
ret5_D  = close_D / close_{D - 5 trading days}  - 1
ma20_D  = mean(close over last 20 trading days ending at D)
avg_money20_D = mean(money over last 20 trading days ending at D)

rank_pct_ret20_D =
  cross-sectional percentile rank of ret20_D
  computed within
    instruments that on weekly_observation_date_D satisfy:
      PIT universe member
      AND avg_money20_D >= 50,000,000 CNY
      AND close_D exists
      AND ret20_D is finite
      AND ma20_D is finite
      AND ret5_D is finite

rank_pct_ret20_D implementation:
  rank ret20_D ascending, so the strongest ret20 is closest to 1.0
  use average rank for ties
  rank_pct = average_rank / cross_section_count
  require cross_section_count >= 100 for the observation date

eligible(D, instrument) =
  PIT universe member as of D
  AND avg_money20_D >= 50,000,000 CNY
  AND close_D > ma20_D
  AND ret5_D > 0
  AND rank_pct_ret20_D >= 0.80
  AND money_D > 0
  AND volume_D > 0
```

`cross_section_count` 作为 denominator 是冻结口径。使用 average-rank 的目的，是避免同分簇把一批 instrument 同时放大到唯一最高 rank；若若干 instrument 并列最高，它们共享 average rank，`rank_pct_ret20_D` 可以小于 1.0。

`rank_pct_ret20_D` 必须在该 weekly observation date 的高流动性、PIT-eligible、特征齐全集合内做横截面 rank；不得使用 train split 全期 rank、行业内 rank 或 beta-bucket 内 rank。

若某个 weekly observation date 的 `rank_cross_section_count < 100`，该 observation date 不得产生 7.1 signal，必须进入 `r02_rank_cross_section_audit.csv`，并标记：

```text
rank_cross_section_status = blocked_insufficient_rank_cross_section
```

#### 7.1.3 Episode collapse

```text
episode_merge_gap_trading_days = 20
one R02 event per instrument per 20-trading-day window;
within a 20-trading-day window, only the first eligible weekly_observation_date_D
is kept as the R02 signal_date for that instrument.
```

20 个交易日窗口从该 instrument 的上一次 R02 signal_date（如果有）开始向前数。collapse 只在 instrument 维度内运行，不跨 instrument；同一 weekly observation date 内不同 instrument 互不抵消。

#### 7.1.4 Exposure

```text
entry = first executable next-open after weekly_observation_date_D
       (subject to R01 §6 entry execution search window)
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

#### 7.1.5 Frozen constants — not tunable

以下常量在 R02 内一律不允许修改、不允许搜索、不允许 validation 后调整：

```text
ret20 window length        = 20 trading days
ret5 window length         = 5 trading days
ma20 window length         = 20 trading days
avg_money20 window length  = 20 trading days
avg_money20 floor          = 50,000,000 CNY
rank_pct_ret20 threshold   = 0.80
ret5 sign rule             = strictly > 0
close vs ma20 rule         = strictly >
weekly observation cadence = ISO-week last trading day
episode collapse gap       = 20 trading days
horizon_set                = H5, H10, H20
primary_horizon            = H10
```

如果 E02 实现时怀疑某个常量需要改动，必须回到 R02 修订，不得在工程层换值。

### 7.2 `r02_weekly_liquid_universe_baseline_v0`

定位：

```text
audit-only, date-aligned baseline answering whether RS20 selection contributes
stock-selection lift over the same weekly liquid universe itself.
```

7.2 不是独立 candidate event source。它必须与 7.1 的 signal dates 对齐：

```text
weekly_observation_date_D = same as 7.1.1

baseline is constructed only for weekly_observation_date_D where
  7.1 has at least one generated primary event before execution blocking.

eligible_baseline(D, instrument) =
  PIT universe member as of D
  AND avg_money20_D >= 50,000,000 CNY
  AND close_D exists
  AND money_D > 0
  AND volume_D > 0

paired_nonselected_baseline(D, instrument) =
  eligible_baseline(D, instrument)
  AND instrument is not selected by 7.1 on the same D
```

7.2 必须输出两个 baseline readouts：

```text
full_liquid_baseline:
  equal-weight all eligible_baseline(D, instrument)

nonselected_liquid_baseline:
  equal-weight paired_nonselected_baseline(D, instrument)
```

R02 final decision 的 baseline-lift guard 必须使用 `nonselected_liquid_baseline`。`full_liquid_baseline` 只用于解释。

7.2 的 headline comparison 必须是 date-level，而不是独立 instrument-event count comparison：

```text
primary_date_equal_weight_return(D, H) =
  equal-weight net_return of all complete 7.1 primary events on D and H

baseline_date_equal_weight_return(D, H) =
  equal-weight net_return of all complete nonselected_liquid_baseline constituents on D and H

selection_lift_vs_baseline(D, H) =
  primary_date_equal_weight_return(D, H)
  - baseline_date_equal_weight_return(D, H)
```

baseline constituents 必须使用与 7.1 相同的 entry / exit / cost / blocked_reason 口径。baseline comparison status 必须按 `(D, H)` 穷举，不得让 E02 推断 "非 blocked 即 comparable"：

```text
baseline_executable_constituent_count(D, H) =
  count of nonselected_liquid_baseline constituents with complete execution
  on weekly_observation_date_D and horizon H

baseline_comparison_status(D, H) = comparable
  iff primary_decision_observation_date(D, H) = true
  AND baseline_executable_constituent_count(D, H) >= 100

baseline_comparison_status(D, H) = blocked_insufficient_baseline_constituents
  iff primary_decision_observation_date(D, H) = true
  AND baseline_executable_constituent_count(D, H) < 100

baseline_comparison_status(D, H) = not_applicable_no_primary_complete_event
  iff primary_decision_observation_date(D, H) = false
```

只有 `baseline_comparison_status(D, H) = comparable` 的 date row 才允许进入 `baseline_lift_gate(H)` denominator；`blocked_insufficient_baseline_constituents` 与 `not_applicable_no_primary_complete_event` 必须单独审计，不得混入 baseline lift 统计。

7.2 不使用 7.1 的 20-trading-day episode collapse 作为 headline comparison。原因是 7.2 的作用不是生成一个可交易事件源，而是给每个 7.1 observation date 提供同日 baseline。E02 可以输出 baseline constituent panel，但 final report 的 7.1 vs 7.2 comparison 必须以 date-level equal-weight row 为 authority。

该 unit **不参与 R02 final decision authority**。它的作用是：

- 给 7.1 提供一个 "同周可执行高流动性宇宙" 的 absolute / relative readout；
- 解释 7.1 的 absolute / relative delta 是 stock-selection edge，还是 market beta / 高流动性宇宙的同期 beta 暴露。
- 作为 7.1 的 downgrade guard：若 7.1 不能稳定跑赢 `nonselected_liquid_baseline`，不得输出 `r02_simple_continuation_supported_continue_research`。

不允许在 7.2 上做任何 pass / fail 判定，不允许在 7.2 上做任何 subset、任何阈值搜索；不允许把 7.1 - 7.2 差额包装成 alpha。7.2 只能防止 false positive，不能创造 positive decision。

## 8. Forbidden Candidate Sources

R02 不允许使用以下来源生成 candidate 或修改 7.1 公式：

```text
EP2 hazard model selected probes
EP2 launch / confirm-add / holding-extension schedule
EP4 R02 / R03 family / fresh / sequence pools
EP4 R04c / R04d / R04e candidate pools
EP4 R05 base_breakout_vcp / launch / money_surge primitives
EP4 R05b sleeve allocator or market-state policy
EP5 R01 launch / money_surge / VCP canonical units
BaseRate TopK predictions
Explore9 / Explore10 primitive outputs
任何"在 7.1 公式上调阈值、加 stop / take-profit、加行业 / regime 筛选"的变体
```

这些来源可以在报告中作为背景或 historical comparison，但不得参与 R02 pass/fail，也不得替换 7.1 / 7.2 frozen formula。

## 9. Matched Comparator Contract

R02 完全继承 R01 §9 的 matched comparator 合同。最低复述：

- comparator candidate universe = `same entry_execution_date + same PIT eligibility + same executability at entry/exit + exclude event instrument`；
- liquidity quintile 在同 `signal_date D` 横截面内计算（口径与 R01 一致：`avg_money20_asof_D`）；
- comparator scope 优先级固定为：`same_industry_same_liquidity (≥30) → same_industry_only (≥30) → same_liquidity_only (≥30) → same_day_pit_universe`；
- 主 relative gate 使用 primary matched comparator 的 equal-weight arithmetic mean；
- 必须额外输出 `matched_comparator_net_return_median`、`same_day_universe_delta_return`、`industry_only_delta_return`、`liquidity_only_delta_return`、`SH000300_delta_return` 用于审计；
- `same_day_pit_universe` 且 `matched_comparator_count < 100` → `matched_comparator_status = blocked_insufficient_comparator`；不得进入 relative_positive denominator，但保留在 absolute denominator 与 fallback audit；
- `fallback_comparator_share > 0.30` → 该 horizon 必须降级为 `weak_comparator_quality`，不得输出 `relative_positive = true`。

R02 不允许重新定义 comparator 公式。如果 E02 发现 R01 §9 的 comparator 在 R02 weekly cadence 下有口径冲突，必须回到 R01 / E01 修订；R02 工程层不得静默替换。

若 R02 触发 relative-only 后续方向，还必须满足多 comparator 稳定性：

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

`SH000300_delta_return` 只能作为 beta / market context 解释，不得单独支撑 `multi_comparator_relative_stable`。若 `relative_positive(H10) = true` 但 `multi_comparator_relative_stable(H10) = false`，不得输出 `r02_relative_edge_only_hedged_or_regime_audit_required`。

## 10. Regime / Beta-State Decomposition

R02 完全继承 R01 §10 的 regime / beta-state 分解口径，包括 SH000300 market_state、stock_beta120、beta_bucket 的 train-split-only tercile 阈值。

regime / beta-state 只用于解释，不得作为 selection gate。R02 不允许 "regime-on 才买" 或 "high-beta bucket 才买" 这类 subset 操作。

必须按以下维度输出分解：

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

并必须额外输出 R02 特有的解释维度（与 7.1 经济假设直接相关）：

```text
rank_pct_ret20_bucket_at_D:
  bucket_080_085, bucket_085_090, bucket_090_095, bucket_095_100
ret20_value_bucket_at_D:
  ret20 <= 0.10
  0.10 < ret20 <= 0.20
  0.20 < ret20 <= 0.40
  ret20 > 0.40
```

这两个 bucket 只是描述性 readout，不允许做 bucket-level subset selection 或 validation 后挑 bucket 升级为 pass。

## 11. Required Metrics

每个 `canonical_unit_id + horizon + split` 至少输出 R01 §11 的全部指标。R02 在此基础上额外强制输出：

```text
weekly_observation_date_count
decision_observation_date_count
min_year_decision_observation_date_count
events_per_observation_date_mean
events_per_observation_date_median
events_per_observation_date_p95
unique_instrument_count
mean_avg_money20_at_D
mean_ret20_at_D
mean_rank_pct_ret20_at_D
share_of_event_dates_with_zero_eligible_instruments
date_weighted_mean_net_return
date_weighted_median_net_return
date_weighted_mean_matched_delta_return
positive_observation_date_share_net
positive_observation_date_share_matched_delta
top1_observation_date_event_share
top5_observation_date_event_share
top1_observation_date_profit_contribution_share
rank_cross_section_count_min
rank_cross_section_count_median
```

同时必须输出 7.1 与 7.2 的并列对照表，至少包含：

```text
canonical_unit_id
horizon
split
complete_event_count
mean_net_return
median_net_return
loss_rate
mean_matched_delta_return
median_matched_delta_return
matched_loss_rate_delta
date_weighted_mean_net_return
date_weighted_mean_matched_delta_return
baseline_date_weighted_mean_net_return
baseline_comparable_observation_date_count
min_year_baseline_comparable_observation_date_count
baseline_lift_evaluable
selection_lift_vs_baseline_mean
selection_lift_vs_baseline_median
selection_lift_vs_baseline_p10
selection_lift_loss_rate_delta
```

以上 baseline comparison 字段全部按 `canonical_unit_id + horizon + split` 输出；若 E02 采用 wide-format 报告，H10 主判定字段必须明确带出 `_H10` 后缀或等价 horizon 标识，不得把 H5 / H10 / H20 的 baseline comparability 混成一个 split-level 值。

7.2 baseline 不单独进入 pass/fail，但必须出现在 explanatory comparison，并且必须为 `baseline_lift_gate` 提供 authority。

execution audit、concentration audit 字段集合与 R01 §11 一致。

## 12. Gate Definitions

R02 的判定口径**整体保持 R01 §12 的结构**（sample / concentration / absolute / relative / robustness），但允许在 sample 量级做出符合 weekly cadence 的轻度调整。其余 gate 一律继承 R01 数值，不得放宽。

R02 的 date-level denominator 固定如下：

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

`date_independence_gate` 使用 `primary_decision_observation_date` 作为 denominator。`baseline_lift_gate` 只使用 `baseline_comparable_observation_date` 作为 denominator。E02 不得混用这两个 denominator。

所有年度 gate 的 yearly rows 只允许包含有 qualifying observation 的 calendar year。empty calendar-year rows 必须排除在 year-level mean / all / any 计算之外，并单独审计；但如果 required `year_count`、`min_year_complete_event_count`、`min_year_decision_observation_date_count` 或 `min_year_baseline_comparable_observation_date_count` 因某年为空而不足，gate 必须失败，不能用排除空行制造通过。

### 12.1 Sample Gate

`canonical_unit_id + horizon H + split` summary row 须满足：

```text
split = validation
complete_event_count >= 600
complete_event_share >= 0.95
year_count = 2
min_year_complete_event_count >= 200
decision_observation_date_count >= 70
min_year_decision_observation_date_count >= 30
```

若 validation `complete_event_count` 在 `[300, 599]`：

```text
sample_status = sample_limited_lead
```

若 validation `complete_event_count < 300`：

```text
sample_status = blocked_insufficient_sample
```

`sample_limited_lead` 与 `blocked_insufficient_sample` 都不得输出 R02 continue。

7.1 的 weekly cadence 下，2022-2023 validation 期内每周都会产生若干 RS20 eligible signals，预期 `complete_event_count` 远大于 600；因此 R02 必须同时检查 date-level 样本。若 event count 过关但 `decision_observation_date_count` 或 `min_year_decision_observation_date_count` 不过关，仍视为 sample gate 失败。

`sample_limited_lead` 只表示 event-row count limited；它不允许绕过 date-level gate。若 date-level count 不足，不能输出 sample-limited lead，必须进入 no-support 或 not-evaluable 类结论。

新增 date-level 独立性 gate：

```text
date_independence_gate(H) =
  decision_observation_date_count >= 70
  AND min_year_decision_observation_date_count >= 30
  AND top1_observation_date_event_share <= 0.05
  AND top5_observation_date_event_share <= 0.20
  AND date_weighted_mean_net_return > 0.0000
  AND date_weighted_mean_matched_delta_return > 0.0000
  AND each validation calendar year date_weighted_mean_net_return >= -0.0025
  AND each validation calendar year date_weighted_mean_matched_delta_return >= -0.0025
  AND positive_observation_date_share_net >= 0.50
  AND positive_observation_date_share_matched_delta >= 0.50
```

`date_independence_gate` 是 R02 对 weekly cross-section correlation 的额外防线。它不替代 R01 gate，只能更严格；不允许 E02 删除或放宽。

### 12.2 Concentration Gate

数值与 R01 §12.2 完全一致：

```text
top1_instrument_event_share <= 0.05
top5_instrument_event_share <= 0.20
top1_industry_event_share <= 0.35
top1_entry_date_event_share <= 0.05
fallback_comparator_share <= 0.30
top1_observation_date_event_share <= 0.05
top5_observation_date_event_share <= 0.20
top1_observation_date_profit_contribution_share <= 0.20
```

任一失败 → unit 可保留描述性 readout，但不得输出 R02 continue。

### 12.3 Absolute Positive

`absolute_positive(H)` 定义与 R01 §12.3 完全一致，不得放宽：

```text
mean_net_return > 0.0000
median_net_return >= -0.0025
p10_net_return >= -0.0800
loss_rate <= 0.55
each validation calendar year mean_net_return >= -0.0025
```

### 12.4 Relative Positive

`relative_positive(H)` 定义与 R01 §12.4 完全一致，不得放宽：

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

matched delta statistics 仅在 `matched_comparator_status = comparable` 上计算；其余口径与 R01 §12.4 一致。

### 12.5 Baseline Lift Gate

`baseline_lift_gate(H)` 是 R02 新增 false-positive guard，只用于防止 7.1 把 weekly liquid universe beta 误判为 RS20 selection edge。

`baseline_lift_gate` 的 denominator 只允许使用：

```text
baseline_comparison_status(D, H) = comparable
```

baseline 可评估性与 baseline lift 失败必须分开：

```text
baseline_lift_evaluable(H) =
  baseline_comparable_observation_date_count >= 70
  AND min_year_baseline_comparable_observation_date_count >= 30

baseline_lift_gate(H) =
  baseline_lift_evaluable(H)
  AND selection_lift_vs_baseline_mean > 0.0000
  AND each validation calendar year selection_lift_vs_baseline_mean >= -0.0025
  AND at least 2 of the following 3 are true:
      selection_lift_vs_baseline_median >= 0.0000
      selection_lift_vs_baseline_p10 >= 0.0000
      selection_lift_loss_rate_delta <= 0.0000
```

若 7.1 H10 满足 `h10_validated_pass`，但 `baseline_lift_evaluable(H10) = false`，不得解释为 beta exposure；必须输出 baseline not evaluable 类结论。只有当 `baseline_lift_evaluable(H10) = true` 且 `baseline_lift_gate(H10) = false` 时，才允许降级为 `r02_beta_or_market_exposure_only_no_stock_selection_pass`。

### 12.6 Robustness Confirmation

数值与 R01 §12.5 完全一致；唯一差异是 sample 量级随 §12.1 调整：

```text
robustness_complete_event_count >= 600
robustness_complete_event_share >= 0.95
robustness_year_count = 2
min_robustness_year_complete_event_count >= 200
robustness_decision_observation_date_count >= 70
min_robustness_year_decision_observation_date_count >= 30
```

其余 robustness 阈值（mean / median / p10 / loss_rate / matched delta / 年度 floor / concentration / fallback）全部沿用 R01 §12.5。R02 还要求 robustness split 上 baseline comparison 可评估，且 `baseline_lift_gate(H10)` 不得显著失效：

```text
robustness_baseline_lift_evaluable(H10) =
  robustness_baseline_comparable_observation_date_count(H10) >= 70
  AND min_robustness_year_baseline_comparable_observation_date_count(H10) >= 30

robustness_selection_lift_vs_baseline_mean >= -0.0025

robustness_confirmed(H10) =
  all inherited R01 robustness thresholds pass
  AND robustness_decision_observation_date_count >= 70
  AND min_robustness_year_decision_observation_date_count >= 30
  AND robustness_baseline_lift_evaluable(H10)
  AND robustness_selection_lift_vs_baseline_mean >= -0.0025
```

robustness 不能救回 validation failure；validation pass + robustness fail → 必须降级为 `r02_unstable_validation_only_lead`。

## 13. Four-Quadrant Interpretation

R02 必须对 7.1 primary unit 在 H10 输出以下四象限之一。语义与 R01 §13 一致，但 **行动结论降级为 continue / no-continue 而非 alpha pass**：

| absolute_positive | relative_positive | 解释 | 允许后续 |
|:--|:--|:--|:--|
| true | true | preliminary quadrant 显示 7.1 同时有 absolute / relative structure，但这还不是 continue decision。 | 在 `h10_validated_pass` 之外，还必须同时满足 baseline_lift_gate、robustness_confirmed、adjacent_horizon_clean，才允许写 R03 controlled discovery；不得直接进 production 或 allocator。 |
| false | true | 可能存在 residual edge，但 long-only deployability 被 beta / regime pressure 阻断。 | 只有 multi_comparator_relative_stable 通过时，才能写 hedged / relative feasibility audit (audit only)；不得写 long-only pass，不得写 market-neutral backtest。 |
| true | false | 可能只是 weekly liquid universe 的 market beta / 同期 inventory exposure。 | 必须先做 7.1 vs 7.2 baseline 的 beta / regime attribution；不得当 stock-selection edge 推进。若 baseline 不可评估，不能解释为 beta。 |
| false | false | simple continuation exposure 在当前 PIT、成本、horizon 下不成立。 | EP5 7.1 short-horizon exposure timing 主线暂停；不得扩 grid，不得改 ret 窗口、rank_pct、horizon。 |

H5 / H20 仅作为形状审计：

```text
horizon_pass(H) =
  sample gate for horizon H
  AND concentration gate for horizon H
  AND date_independence_gate(H)
  AND absolute_positive(H)
  AND relative_positive(H)
```

`strongly_negative(H)` 与 R01 §13 完全一致：

```text
complete_event_count >= 150
AND mean_net_return < -0.0025
AND mean_matched_delta_return < -0.0025
```

不可评估的 adjacent horizon 不得当成正向确认；horizon shape 降级 / 不可评估降级的命名与 R01 §13 对齐（见 §15）。

## 14. Big-Winner / Right-Tail Diagnostic

R02 必须保留 big-winner readout，但不得参与 pass/fail。

口径与 R01 §14 完全一致：

```text
big_winner_horizon = H120
big_winner_threshold = +50% gross max close return from entry_price
right_tail_thresholds = +20%, +50%
```

`right_tail_path_status` / `right_tail_status` / split-level aggregate 规则、censoring 规则、跨 split 处理 全部继承 R01 §14。

允许的解释：

```text
simple continuation unit passed; some post-entry states may deserve later
holding-extension diagnostic (only after R03 is written).
```

禁止的解释：

```text
simple continuation unit failed, but big-winner rate looks high, so R02 continued.
```

R02 不允许在当前文档内定义任何 holding tuning、stop-loss tuning、take-profit tuning 或 right-tail entry rule。

## 15. Final Decision Contract

R02 final decision 只能是以下之一：

```text
r02_simple_continuation_supported_continue_research
r02_relative_edge_only_hedged_or_regime_audit_required
r02_beta_or_market_exposure_only_no_stock_selection_pass
r02_baseline_not_evaluable_validation_lead
r02_unstable_validation_only_lead
r02_unstable_horizon_shape_no_search_allowed
r02_adjacent_horizon_not_evaluable_validation_lead
r02_horizon_specific_lead_only_no_search_allowed
r02_sample_limited_primary_lead_only
r02_no_simple_continuation_support
r02_blocked_data_or_execution_contract
```

辅助定义：

```text
h10_validated_pass(unit) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND absolute_positive(H10)
  AND relative_positive(H10)

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

stock_selection_supported(unit, H10) =
  h10_validated_pass(unit)
  AND baseline_lift_gate(H10)

baseline_not_evaluable_validation_lead(unit, H10) =
  h10_validated_pass(unit)
  AND baseline_lift_evaluable(H10) = false

relative_only_audit_supported(unit, H10) =
  sample gate for H10
  AND concentration gate for H10
  AND date_independence_gate(H10)
  AND relative_positive(H10)
  AND multi_comparator_relative_stable(H10)
  AND absolute_positive(H10) = false
```

`r02_weekly_liquid_universe_baseline_v0` 不能作为 final decision authority，也不能单独触发任何 positive decision。但 `baseline_lift_gate` 必须作为 7.1 positive decision 的 downgrade guard；若 baseline 解释掉 7.1，R02 必须降级。

决策优先级（first-match priority，从 rule 1 到 rule 12 依次判断，首个命中规则决定唯一 `final_decision`）：

1. 若任何必需数据、split、execution、cost 或 canonical unit authority 缺失，输出 `r02_blocked_data_or_execution_contract`。
2. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `stock_selection_supported(unit, H10)`、`robustness_confirmed` 和 `adjacent_horizon_clean`，输出 `r02_simple_continuation_supported_continue_research`。
3. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `baseline_not_evaluable_validation_lead(unit, H10)`，输出 `r02_baseline_not_evaluable_validation_lead`。
4. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `h10_validated_pass`、`baseline_lift_evaluable(H10) = true`，但 `baseline_lift_gate(H10) = false`，输出 `r02_beta_or_market_exposure_only_no_stock_selection_pass`。
5. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `stock_selection_supported(unit, H10)`，但 `robustness_confirmed = false`，输出 `r02_unstable_validation_only_lead`。
6. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `stock_selection_supported(unit, H10)` 和 `robustness_confirmed`，且任一 adjacent horizon `strongly_negative = true`，输出 `r02_unstable_horizon_shape_no_search_allowed`。
7. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `stock_selection_supported(unit, H10)` 和 `robustness_confirmed`，没有 adjacent horizon `strongly_negative = true`，但 `adjacent_horizon_not_evaluable = true`，输出 `r02_adjacent_horizon_not_evaluable_validation_lead`。
8. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `relative_only_audit_supported(unit, H10)`，输出 `r02_relative_edge_only_hedged_or_regime_audit_required`。
9. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 sample gate、concentration gate、`date_independence_gate(H10)`、`absolute_positive(H10) = true`、`relative_positive(H10) = false`，输出 `r02_beta_or_market_exposure_only_no_stock_selection_pass`。
10. 若 `r02_simple_rs20_continuation_natural_exit_v0` 只有 H5 或 H20 满足 `horizon_pass` 和 `baseline_lift_gate(H)`、H10 不满足 `horizon_pass`，输出 `r02_horizon_specific_lead_only_no_search_allowed`。
11. 若 `r02_simple_rs20_continuation_natural_exit_v0` 满足 `sample_limited_return_lead(unit, H10)` 和 `baseline_lift_gate(H10)`，输出 `r02_sample_limited_primary_lead_only`。
12. 其余情况输出 `r02_no_simple_continuation_support`。

当多个规则同时可命中时，以上 first-match priority 是唯一 authority；但 final report 必须并列披露所有 would-have-matched rules，避免 baseline downgrade、relative-only、horizon-specific 或 sample-limited 信息被较早规则遮蔽。

非终止性 final decision 的允许后续固定为：

| final_decision | 允许后续 |
|:--|:--|
| `r02_simple_continuation_supported_continue_research` | 只能写 R03 controlled discovery under strict low-dimensional search，或 post-entry holding-extension diagnostic（必须另写 requirement）；不得直接进 portfolio allocator、hedged strategy、live trading。 |
| `r02_relative_edge_only_hedged_or_regime_audit_required` | 只能写 hedged / relative feasibility audit（audit only：融券可得性、容量、对冲成本、industry-neutral 实操、beta 估计精度），不得直接做 market-neutral backtest。 |
| `r02_beta_or_market_exposure_only_no_stock_selection_pass` | 必须先做 7.1 vs 7.2 baseline 的 beta / regime / 流动性 attribution，不得当 stock-selection edge 推进。该 decision 只覆盖 baseline 可评估但 7.1 没有稳定跑赢 baseline 的情况。 |
| `r02_baseline_not_evaluable_validation_lead` | 先修复或解释 baseline comparison 可评估性，不得把 baseline 缺失解释成 beta，也不得进入 search。 |
| `r02_unstable_validation_only_lead` | 先做 validation / robustness drift explanation，不得进入 search。 |
| `r02_unstable_horizon_shape_no_search_allowed` | 先解释 horizon instability，不得挑选单个 horizon 推进。 |
| `r02_adjacent_horizon_not_evaluable_validation_lead` | 先补足 adjacent horizon 可评估性，不得把 H10 单点通过升级为 search。 |
| `r02_horizon_specific_lead_only_no_search_allowed` | 不得把单 horizon lead 升级为 search 或 production。 |
| `r02_sample_limited_primary_lead_only` | 先做事件来源 / 执行阻断 / weekly cadence 复核，不得通过放宽阈值堆样本。 |
| `r02_no_simple_continuation_support` | EP5 7.1 short-horizon exposure timing 主线暂停或重新选 exposure 主线；不得扩 grid，不得改 ret 窗口、rank_pct、horizon。 |
| `r02_blocked_data_or_execution_contract` | 先回到 R01 / E01 修订执行 / 数据合同，再决定是否继续 R02。 |

`r02_simple_continuation_supported_continue_research` 不是 production approval。它只表示 simple short-horizon continuation exposure 在当前 PIT 数据、成本、H10 主判定下显示出**值得继续研究**的结构。

## 16. Reporting Requirements

R02 最终报告必须直接回答：

1. `r02_simple_rs20_continuation_natural_exit_v0` 在 H10 进入哪个四象限？
2. 结果是 absolute edge、relative edge、beta exposure，还是没有 edge？
3. Validation 2022 / 2023 是否方向一致，还是集中在单一年份？
4. Robustness 2024 / 2025 是否确认，还是把结果降级为 validation-only lead？
5. Matched comparator fallback 是否过高？
6. 收益是否由少数 instrument、industry、entry date 贡献？
7. event-row 结论是否由少数 weekly observation dates 驱动？date-weighted return 是否同向？
8. H5 / H20 是否支持 H10，还是只出现 horizon-specific lead？
9. Big-winner readout 是否只是 post-entry diagnostic，是否被错误用于 pass/fail？
10. 7.1 vs 7.2 baseline 是否可评估？若可评估，差额是否解释为 stock-selection edge，还是 weekly liquid universe 同期 beta 暴露？若 §15 rule 9 触发，必须额外披露 `baseline_lift_gate(H10)`，说明 abs+/rel- 是普遍 beta 还是 matched-comparator 失败。
11. 若触发 relative-only，是否通过多 comparator 稳定性，而不是只相对 SH000300 或单一 comparator 为正？
12. 下一份 requirement 被允许启动哪条方向，哪条方向被禁止？

报告必须显式写出：

```text
R02 did not perform alpha search.
R02 did not tune ret20, ret5, rank_pct, ma20, money floor, horizon, or collapse.
R02 did not use big-winner labels for pass/fail.
R02 did not tune thresholds after validation.
R02 did not approve a production strategy.
R02 did not run a hedged or market-neutral backtest.
R02 did not let the audit-only weekly liquid universe baseline create a positive decision.
```

## 17. Required Artifacts / Validator Contract

E02 最小 artifact authority 必须包括：

| artifact | authority |
|:--|:--|
| `r02_formula_freeze_audit.csv` | 证明 7.1 / 7.2 公式常量、rank 口径、weekly cadence、collapse gap 与本 requirement 完全一致。 |
| `r02_rank_cross_section_audit.csv` | 每个 weekly observation date 的 rank universe size、blocked_insufficient_rank_cross_section 状态。 |
| `r02_primary_event_panel.parquet` | 7.1 generated events，含 signal_date、rank_pct、ret20、ret5、ma20、avg_money20、episode id。 |
| `r02_execution_event_panel.parquet` | 7.1 execution rows，继承 R01 execution schema。 |
| `r02_baseline_constituent_panel.parquet` | 7.2 date-aligned baseline constituents，含 full / nonselected baseline 标记与 execution status。 |
| `r02_baseline_date_comparison.csv` | date-level 7.1 vs 7.2 equal-weight comparison，含 `baseline_executable_constituent_count(D,H)` 与 `baseline_comparison_status(D,H)`，作为 `baseline_lift_gate` authority。 |
| `r02_event_summary_by_unit_horizon_split.csv` | R01-compatible split summary 加 R02 date-weighted fields。 |
| `r02_event_summary_by_unit_horizon_year.csv` | 年度 summary，必须排除 empty calendar-year rows 进入 gate。 |
| `r02_date_independence_audit.csv` | date count、top observation-date concentration、date-weighted mean、positive date share。 |
| `r02_multi_comparator_relative_audit.csv` | matched / same-day universe / industry / liquidity / SH000300 relative readouts。 |
| `r02_final_decision_inputs.csv` | final decision 所有 rule input，含 would-have-matched rules。 |
| `r02_final_decision_replay_audit.csv` | 按 §15 first-match priority replay 的唯一 authority。 |
| `r02_final_report.md` | 中文最终报告，回答 §16 的全部问题。 |

Validator 至少必须检查：

```text
1. formula_hash / constants exactly match §7.1 and §7.2.
2. only one primary decision unit exists.
3. 7.2 baseline is date-aligned to 7.1 and cannot create positive decision.
4. baseline_comparison_status(D,H) is exhaustive and only comparable rows enter baseline_lift_gate.
5. cache / parquet authority files do not enter report-only hand edits.
6. sample gate includes both event-level and date-level counts.
7. date_independence_gate is applied before any continue decision.
8. baseline_lift_gate is applied before r02_simple_continuation_supported_continue_research.
9. baseline_lift_evaluable=false maps to r02_baseline_not_evaluable_validation_lead, not beta exposure.
10. robustness_confirmed requires robustness_baseline_lift_evaluable=true and robustness_selection_lift_vs_baseline_mean >= -0.0025.
11. relative-only decision requires multi_comparator_relative_stable.
12. empty calendar-year rows are excluded from year-level gates and separately audited.
13. final decision priority matches §15 rules 1-12.
14. would-have-matched rules are reported even when not selected.
15. big-winner / right-tail fields do not feed any final decision rule.
```

## 18. Relationship to E01 / E02

E01 已经把 EP5 R01 的 harness 落到执行、成本、split、horizon、comparator、gate、validator 等冻结口径上。R02 不得在工程层重新定义这些东西；E02（如有必要）只允许：

```text
注册新 canonical_unit_id 与对应 event-source builder
扩展 weekly observation date 调度
扩展 R02-specific metrics 与 7.1 vs 7.2 对照
扩展 final decision rules 至 §15 列表
扩展 validator 检查 7.1 / 7.2 公式常量是否被静默改动
扩展 date-level baseline lift / multi-comparator relative audit
```

E02 不得改变：

```text
canonical_unit_id 的角色或 final-decision authority
horizon_set
execution rule / cost model / split
sample / concentration / absolute / relative gate 数值
weekly cadence 定义
7.1 公式常量
7.2 date-aligned baseline 定义
date_independence_gate / baseline_lift_gate / multi_comparator_relative_stable
big-winner read-only boundary
```

如果 E02 在实现时发现本 requirement 中某个字段无法实现，应回到 R02 修改 requirement，而不是在代码中静默换口径。
