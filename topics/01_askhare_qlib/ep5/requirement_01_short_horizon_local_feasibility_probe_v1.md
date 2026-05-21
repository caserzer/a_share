# EP5 Requirement 01: Short-Horizon Local Feasibility Probe V1

## 1. 需求元信息

- 需求 id: `ep5_r01_short_horizon_local_feasibility_probe_v1`
- 简称: `r01_short_horizon_local_feasibility_probe_v1`
- 状态: requirement-ready research contract
- 所属 workflow: EP5
- 上游讨论: `ep5/discussion.md`
- 上游终局证据: `ep4/FINAL_REPORT.md`
- 日期: 2026-05-21

本需求是 EP5 的第一份 requirement。它只冻结研究问题、边界、canonical exposure units 和判定口径；它不是 engineering plan，不规定 runner / config / artifact 目录结构。后续 `E01` 可以把本需求翻译成可复现 harness，但不得在工程实现时自由选择新的 exposure unit、horizon、execution rule 或 pass/fail gate。

## 2. 核心问题

R01 只回答一个问题：

```text
在 A-share PIT universe、本地 Qlib 数据、next-open execution、扣成本、
H5/H10/H20 固定持有合约下，
少数事前冻结的 short-horizon exposure units 是否显示出
action-time、after-cost、validation-first 的本地可交易性？
```

这里的 "本地可交易性" 必须同时拆成两层：

```text
absolute local tradability:
  long-only、扣成本、next-open 条件下是否能赚钱；

relative / residual edge:
  相对同日同宇宙、同业 / 流动性 / beta-state comparator
  是否仍有更干净的收益分布。
```

R01 不是为了证明 short-horizon alpha 普遍存在。它只判断当前冻结的少数 canonical units 是否足以支持 EP5 继续沿 `7.1 short-horizon exposure timing` 推进。

## 3. Non-Goals

R01 明确不做：

- 不做大规模 grid search、pool search、family combination search；
- 不继续 EP4 R05c / R05d，不修补 `fresh` / `family order` / `bad-shape` / `sleeve allocator`；
- 不把 R04d `volume_money` relative improvement 或 R04e union pool 包装成新 alpha；
- 不复活 EP2 的完整 launch / confirm-add / holding-extension 系统；
- 不训练或复用 EP2 hazard model 作为可通过的 R01 candidate；
- 不使用 validation / robustness outcome 反向调整 threshold、bucket、horizon、event collapse 或 sample gate；
- 不做 hedged / market-neutral 回测；
- 不做 holding tuning、stop-loss tuning、profit-taking tuning 或 continuation policy；
- 不输出 production strategy、buy/sell signal、position sizing 或 allocator 结论。

R01 可以保留 big-winner / right-tail readout，但它只能是 post-entry diagnostic，不得参与 R01 pass/fail。

## 4. Phase Boundary

R01 的边界是：

```text
exposure unit first,
right-tail management second.
```

如果 R01 不能证明固定 short-horizon exposure unit 至少存在 validation-first 的正向结构，后续不得启动：

```text
holding-extension requirement
right-tail optionality requirement
allocator / sleeve composition requirement
large-scale alpha discovery requirement
```

如果 R01 只出现 `absolute negative + relative positive`，结论不是 long-only pass，而是：

```text
possible residual edge,
long-only deployability blocked by beta / regime pressure.
```

这种结果只能触发 hedged / relative feasibility audit 的讨论，不能直接启动 market-neutral strategy backtest。

## 5. Data / Split Contract

R01 必须使用本地 PIT 数据，不得在线抓取。

最低数据合同：

| 数据 | 路径 / 口径 | 作用 |
|:--|:--|:--|
| Qlib PIT provider | `data/qlib/cn_data_pit` | adjusted daily OHLCV / money / factor |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` | event eligibility and comparator universe |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` | code / instrument audit |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | matched comparator and concentration audit |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | next tradable date resolution |
| Index state source | `SH000300` under `data/qlib/cn_data_pit` | market / beta-state decomposition |

Split 固定为：

```text
train_start      = 2017-07-04
train_end        = 2021-12-31
validation_start = 2022-01-01
validation_end   = 2023-12-31
robustness_start = 2024-01-01
robustness_end   = 2025-12-31
```

Train split 只允许用于：

- 计算 as-of quantile bucket；
- 输出背景统计；
- 校验 canonical units 是否样本充足；
- 在后续 E01 中做实现 sanity check。

Train split 不得用于重新选择 R01 canonical units。Validation 是 primary decision split。Robustness 是 read-only holdout：它不能救回 validation failure，但可以把 validation pass 降级为 `r01_unstable_validation_only_lead`。

Train split 的样本量或背景表现只能用于发现本 requirement 本身是否需要回炉修改。E01 实现阶段不得根据 train split 的样本量、收益、relative delta 或 concentration 结果调整 canonical unit 公式常量、event collapse、horizon、execution lag、sample gate 或 comparator 规则。

## 6. Execution / Cost Contract

所有 canonical units 统一使用 close-derived signal、next-open execution。

时间语义：

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
```

执行搜索窗口固定为：

```text
max_entry_execution_lag_trading_days = 5
max_exit_execution_lag_trading_days = 5

entry execution search window:
  signal_date D 之后第 1 到第 5 个交易日

exit execution search window:
  natural_exit_signal_date(H) 之后第 1 到第 5 个交易日
```

如果对应搜索窗口内找不到可执行 open，必须输出阻断行，不能把 event 静默删除或延后到窗口外成交。

涨跌停推断口径固定为：

```text
mainboard_limit_inference_pct = 0.095

limit_up_inferred_on_entry:
  adjusted_open_candidate / adjusted_close_previous_trading_day - 1
    >= mainboard_limit_inference_pct

limit_down_inferred_on_exit:
  adjusted_open_candidate / adjusted_close_previous_trading_day - 1
    <= -mainboard_limit_inference_pct
```

该阈值只服务于当前 PIT mainboard universe 的可执行性阻断推断。E01 不得自行替换为 10%、20%、ST-specific limit 或 provider-specific limit table；若后续发现 PIT universe 中存在无法用该口径解释的 limit regime，必须回到 R01 修改本 contract。

固定 horizon：

```text
horizon_set = H5, H10, H20
primary_horizon_for_decision = H10
H5 and H20 = adjacent sensitivity / shape audit
```

H5 / H10 / H20 都必须输出；不得在 validation 后选择最好 horizon。R01 的主判定优先看 H10。若只有 H5 或 H20 通过而 H10 不通过，结果只能是 `r01_horizon_specific_lead_only_no_search_allowed`，不得升级为 R01 pass。

成本模型固定为 EP2 base cost 口径：

```text
buy_cost_bps  = 30
sell_cost_bps = 80
round_trip_cost_bps = 110

net_return =
  exit_price * (1 - sell_cost_bps / 10000)
  / (entry_price * (1 + buy_cost_bps / 10000))
  - 1
```

阻断执行必须记录，不能静默删除：

```text
missing_open
missing_exit_open
zero_volume
zero_money
not_universe_member
limit_up_inferred_on_entry
limit_down_inferred_on_exit
missing_calendar_next_day
insufficient_forward_trading_days
split_boundary
```

主结果只统计 complete and executable events。所有 blocked rows 必须进入执行阻断审计和 denominator audit。

## 7. Frozen Canonical Exposure Units

R01 只允许以下 3 个 canonical units。任何新增 unit 都必须先修改本 requirement，不能由 E01 config 暗含扩展。

三者角色不同，不能共用同一个 pass 语义：

| canonical_unit_id | role | final-decision authority |
|:--|:--|:--|
| `r01_launch_breakout_money_surge_natural_exit_v0` | primary short-horizon exposure unit | 唯一可以单独支持 `r01_short_horizon_local_unit_supported` 的 unit |
| `r01_launch_breakout_money_surge_fast_fail_v0` | secondary loss-control variant | 只能证明固定 fast-fail 是否改善分布；如果 natural-exit 不成立，不得单独输出 short-horizon exposure pass |
| `r01_base_breakout_vcp_sparse_natural_exit_v0` | backup sparse event-source probe | 仅在 primary H10 sample / concentration 可评估时触发 sparse event-source follow-up；不得被解释为 R05 Preflight primitive 被救回 |

### 7.1 `r01_launch_breakout_money_surge_natural_exit_v0`

定位：

```text
no-model launch / breakout / money-surge short-horizon exposure unit
```

该 unit 使用 EP2 engineering baseline 中已经冻结的 launch detector 作为 event source，但不复用 EP2 label、hazard model、confirm-add 或 holding-extension schedule。

事件公式固定为：

```text
detector_id = EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20

history_ok:
  valid close count over prior / current 80-row window >= 80

price_breakout:
  close_D / rolling_min_close_60_prev_D - 1 >= 0.12
  AND close_D >= rolling_max_close_60_prev_D

money_surge:
  money_D >= 2.0 * money_ma20_prev_D
  AND money_D >= 50,000,000 CNY

basic_launch_signal:
  PIT universe member as of D
  AND history_ok
  AND price_breakout
  AND money_surge
  AND close_D exists
  AND money_D > 0
  AND volume_D > 0
```

Episode collapse 固定为：

```text
episode_merge_gap_trading_days = 20
episode_start_signal_date = first signal_date in collapsed launch episode
one R01 event per instrument + launch episode
```

Exposure:

```text
entry = first executable next-open after episode_start_signal_date
exit = natural_exit_execution_date(H5/H10/H20)
no stop
no confirm-add
no model threshold
```

### 7.2 `r01_launch_breakout_money_surge_fast_fail_v0`

定位：

```text
same event source as 7.1, with one fixed risk-control contract.
```

该 unit 不是 stop-loss tuning。它只测试一个事前冻结的最小 fast-fail 保护是否改变 short-horizon tradability。

事件来源、entry 和 collapse 完全继承 7.1。

Fast-fail 只能在 §15 rule 7 的完整条件下触发最终结论：primary natural-exit 未满足 `h10_validated_pass`，而 fast-fail unit 同时满足 `h10_validated_pass`、`robustness_confirmed` 和 `adjacent_horizon_clean`。满足该条件时，最终结论只能是：

```text
r01_fast_fail_only_loss_control_lead
```

该结论表示 fixed fast-fail 可能有 loss-control 价值，不表示底层 exposure unit 已经是正期望，也不得直接进入 controlled discovery / holding tuning。

Fast-fail 规则固定为：

```text
fast_fail_drawdown = -0.06
fast_fail_signal_date =
  first close-observed date t where
  entry_execution_date <= t <= natural_exit_signal_date(H)
  AND
  adjusted_close / entry_price - 1 <= -0.06

if fast_fail_signal_date exists:
  exit_execution_date = first executable open after fast_fail_signal_date
else:
  exit_execution_date = natural_exit_execution_date(H)
```

禁止：

```text
validation 后修改 -6% threshold
新增 take-profit
新增 trailing stop
新增 confirm-add
把 H20 / H120 winner readout 用作 exit trigger
```

### 7.3 `r01_base_breakout_vcp_sparse_natural_exit_v0`

定位：

```text
low-overlap sparse event source sanity check.
```

该 unit 继承 EP4 R05 Preflight 中 `base_breakout_vcp_preflight` 的 frozen formula，只作为 sparse event source 备选。它不能被解释为 R05 Preflight 失败 primitive 的救回；如果样本量不足，只能输出 `r01_sample_limited_sparse_event_source_lead_only`。

Sparse unit 不得独立升级为 R01 主线，也不得在 primary unit 本身样本严重不足或 concentration 不可用时单独触发 supported 标签。只有当 7.1 primary natural-exit unit 在 H10 已满足 sample gate 和 concentration gate、但未满足完整 long-only support，同时 sparse unit 满足 §15 rule 6 的完整条件时，最终结论才可以是：

```text
r01_sparse_event_unit_supported_event_source_followup
```

该结论只允许下一份 requirement 讨论 low-overlap sparse event-source feasibility，不允许把 EP4 R05 Preflight 的 failed primitive 改写为已通过 alpha。


公式固定为：

```text
base_length = 20
base_high_D = max(high[D-20:D-1])
base_low_D = min(low[D-20:D-1])
base_drawdown_pct_D = base_low_D / base_high_D - 1
breakout_ret_pct_D = close_D / base_high_D - 1
pre_base_vol20_D = std(log_return[D-20:D-1])
recent_vol10_D = std(log_return[D-9:D])
vol_contraction_ratio_D = recent_vol10_D / pre_base_vol20_D

base_drawdown_pct_D >= -0.12
breakout_ret_pct_D >= 0.00
breakout_ret_pct_D <= 0.08
vol_contraction_ratio_D <= 0.80
abs(close_D / ma20_D - 1) <= 0.12
atr20_pct_D <= 0.10
money_ratio5_to20_D >= 1.10
money_ratio5_to20_D <= 2.50
avg_money20_rank_pct_D >= 0.30
```

Exposure:

```text
event_collapse_window_trading_days = 20
entry = first executable next-open after D
exit = natural_exit_execution_date(H5/H10/H20)
no stop
no continuation
no threshold expansion
```

## 8. Forbidden Candidate Sources

R01 不允许使用以下来源生成可通过 candidate：

```text
EP2 hazard model selected probes
EP2 confirm-add schedule
EP2 R04/R05 holding-extension or continuation policies
EP4 R02/R03 family / fresh / sequence pools
EP4 R04c/R04d/R04e candidate pools
EP4 R05b sleeve allocator or market-state policy
BaseRate TopK predictions
Explore9 / Explore10 primitive outputs
```

这些来源可以在报告中作为背景或 negative / historical comparison，但不得参与 R01 pass/fail。

## 9. Matched Comparator Contract

R01 必须同时输出 absolute return 和 matched relative return。

每条 event 的 comparator candidate universe 先固定为：

```text
same entry_execution_date
same PIT universe eligibility
same executability at entry and horizon exit
exclude the event instrument itself
```

Liquidity quintile:

```text
avg_money20_asof_D = mean(money over last 20 trading days ending at D)
quintile thresholds are computed cross-sectionally within the same signal_date D
```

Primary matched comparator 必须按以下固定顺序选择，不能由实现自由决定：

```text
candidate_scope_0 = comparator candidate universe

candidate_scope_1 =
  same SW2021 industry as event instrument
  AND same liquidity quintile as event instrument

if count(candidate_scope_1) >= 30:
  primary_comparator_scope = same_industry_same_liquidity
else if count(same SW2021 industry within candidate_scope_0) >= 30:
  primary_comparator_scope = same_industry_only
else if count(same liquidity quintile within candidate_scope_0) >= 30:
  primary_comparator_scope = same_liquidity_only
else:
  primary_comparator_scope = same_day_pit_universe
```

Comparator return 使用与 event 相同的 entry / exit / cost 口径。Primary comparator return 固定为 equal-weight arithmetic mean：

```text
matched_comparator_net_return =
  mean(net_return of all rows in primary_comparator_scope)

matched_comparator_count =
  row count of primary_comparator_scope

matched_delta_return =
  event_net_return - matched_comparator_net_return
```

必须额外输出 primary comparator 的 median 版本用于审计，但不得替代 primary gate：

```text
matched_comparator_net_return_median
matched_delta_return_vs_comparator_median
```

如果 `primary_comparator_scope = same_day_pit_universe` 且 `matched_comparator_count < 100`，该 event 的 relative comparison 状态必须是：

```text
matched_comparator_status = blocked_insufficient_comparator
```

该 event 可以保留在 absolute return denominator 中，但不得进入 `relative_positive` 的 primary denominator；必须进入 comparator fallback audit。

必须额外输出：

```text
same_day_universe_delta_return
industry_only_delta_return
liquidity_only_delta_return
SH000300_delta_return
```

但 R01 primary relative 判定只使用 primary matched comparator 的 equal-weight mean。Fallback 使用率必须报告；fallback 质量的 pass/fail 判定以 §12.4 的 `fallback_comparator_share <= 0.30` 为唯一 authority，超过该阈值时 relative conclusion 必须降级为 `weak_comparator_quality`，不得输出 `relative_positive = true`。

## 10. Regime / Beta-State Decomposition

R01 不允许用 outcome 反向定义 regime。Regime / beta-state 只用于解释，不得作为 selection gate。

固定 market state：

```text
index = SH000300
index_close_D = adjusted close at signal_date D
index_ma60_D = mean(index close over last 60 trading days including D)
index_ret20_D = index_close_D / index_close_{D-20 trading days} - 1

market_state_D =
  risk_on  if index_close_D >= index_ma60_D AND index_ret20_D >= 0
  risk_off if index_close_D <  index_ma60_D AND index_ret20_D <  0
  mixed    otherwise
```

固定 beta bucket：

```text
stock_beta120_D =
  rolling beta of stock daily close-to-close return vs SH000300
  over the last 120 trading days ending at D

beta_bucket thresholds:
  train split terciles only

beta_bucket_D:
  low_beta / mid_beta / high_beta
```

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

这些分解不得用于 validation 后选择 subset。它们只回答结果来自 stock-level edge、market beta、regime pressure、行业集中，还是 liquidity / inventory concentration。

## 11. Required Metrics

每个 `canonical_unit_id + horizon + split` 至少输出：

```text
signal_event_count
entry_executable_count
complete_event_count
blocked_event_count
complete_event_share
mean_gross_return
mean_net_return
median_net_return
p10_net_return
p25_net_return
p75_net_return
p90_net_return
loss_rate
mean_matched_delta_return
median_matched_delta_return
p10_matched_delta_return
matched_loss_rate_delta
matched_comparator_count_mean
matched_comparator_scope_same_industry_same_liquidity_share
matched_comparator_scope_same_industry_only_share
matched_comparator_scope_same_liquidity_only_share
matched_comparator_scope_same_day_pit_universe_share
blocked_insufficient_comparator_count
relative_comparable_event_share
same_day_universe_delta_mean
industry_only_delta_mean
liquidity_only_delta_mean
SH000300_delta_mean
top1_instrument_event_share
top5_instrument_event_share
top1_industry_event_share
top5_industry_event_share
top1_entry_date_event_share
fallback_comparator_share
```

必须额外输出 execution audit：

```text
blocked_reason
blocked_count
blocked_share
canonical_unit_id
horizon
split
```

以及 concentration audit：

```text
instrument_id
industry_id
entry_year
entry_date
event_count
event_share
net_return_contribution_share
matched_delta_contribution_share
```

R01 不要求组合级回测，但如果 E01 输出 portfolio daily diagnostic，该 diagnostic 只能作为附录，不能替代 event-level pass/fail。

## 12. Gate Definitions

### 12.1 Sample Gate

本节所有 gate 都按 `canonical_unit_id + horizon H + split` 的 summary row 计算。`H` 只能是 `H5`、`H10`、`H20`。字段名不带 horizon 前缀时，表示当前 summary row 的 horizon 字段。

一个 `canonical_unit_id + horizon H` 要进入该 horizon 的 quadrant 判定，必须满足：

```text
split = validation
complete_event_count >= 300
complete_event_share >= 0.95
year_count = 2
min_year_complete_event_count >= 75
```

若 validation `complete_event_count` 在 `[150, 299]`：

```text
sample_status = sample_limited_lead
```

若 validation `complete_event_count < 150`：

```text
sample_status = blocked_insufficient_sample
```

`sample_limited_lead` 和 `blocked_insufficient_sample` 都不得输出 R01 pass。

### 12.2 Concentration Gate

该 horizon 的 primary 判定必须满足：

```text
top1_instrument_event_share <= 0.05
top5_instrument_event_share <= 0.20
top1_industry_event_share <= 0.35
top1_entry_date_event_share <= 0.05
fallback_comparator_share <= 0.30
```

任一失败时，unit 可以保留描述性结论，但不得输出 R01 pass。

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

所有用于 `relative_positive(H)` 的 matched delta statistics 必须只基于：

```text
matched_comparator_status = comparable
```

`blocked_insufficient_comparator` rows 必须保留在 absolute return denominator 和 comparator audit 中，但不得进入 `mean_matched_delta_return`、`median_matched_delta_return`、`p10_matched_delta_return`、`matched_loss_rate_delta` 或 year-level matched delta gate 的计算。

并且以下三项至少两项成立：

```text
median_matched_delta_return >= 0.0000
p10_matched_delta_return >= 0.0000
matched_loss_rate_delta <= 0.0000
```

### 12.5 Robustness Confirmation

Robustness 不允许救回 validation failure。

若 validation H10 已同时满足 sample、concentration、`absolute_positive(H10)`、`relative_positive(H10)`，robustness 只用于确认稳定性：

```text
robustness_confirmed = true if:
  robustness_complete_event_count >= 300
  robustness_complete_event_share >= 0.95
  robustness_year_count = 2
  min_robustness_year_complete_event_count >= 75
  robustness_relative_comparable_event_share >= 0.95
  robustness_blocked_insufficient_comparator_count / robustness_complete_event_count <= 0.05
  robustness_mean_net_return >= -0.0025
  robustness_median_net_return >= -0.0050
  robustness_p10_net_return >= -0.0900
  robustness_loss_rate <= 0.58
  robustness_mean_matched_delta_return >= -0.0025
  each robustness calendar year mean_net_return >= -0.0050
  each robustness calendar year mean_matched_delta_return >= -0.0050
  robustness_top1_instrument_event_share <= 0.05
  robustness_top5_instrument_event_share <= 0.20
  robustness_top1_industry_event_share <= 0.35
  robustness_top1_entry_date_event_share <= 0.05
  robustness_fallback_comparator_share <= 0.30
```

Robustness 中所有 matched delta statistics 同样只能基于：

```text
matched_comparator_status = comparable
```

若 robustness 不满足，上述 validation pass 必须降级为：

```text
r01_unstable_validation_only_lead
```

不得输出 `r01_short_horizon_local_unit_supported`。

## 13. Four-Quadrant Interpretation

R01 必须对每个 primary H10 unit 输出以下四象限之一：

| absolute_positive | relative_positive | 解释 | 允许后续 |
|:--|:--|:--|:--|
| true | true | short-horizon unit 可能有本地可交易性和 residual edge。 | 若 robustness confirmed，可进入 controlled discovery / holding diagnostic 的下一份 requirement。 |
| false | true | 可能有 residual edge，但 long-only deployability 被 beta / regime pressure 阻断。 | 只能讨论 hedged / relative feasibility audit，不得输出 long-only pass。 |
| true | false | 可能只是 market beta / same-day inventory exposure。 | 先做 beta / regime attribution，不得当作 stock-selection edge。 |
| false | false | 当前 canonical unit 没有给出继续 7.1 的初步支持。 | 不得扩大 grid；7.1 暂停或重新定义 event source。 |

H5 / H20 只作为形状和相邻 horizon sensitivity：

```text
horizon_pass(H) =
  sample gate for horizon H
  AND concentration gate for horizon H
  AND absolute_positive(H)
  AND relative_positive(H)

H10 pass + neither H5 nor H20 strongly_negative = primary support
H5 or H20 horizon_pass but H10 not horizon_pass = horizon_specific_lead_only
H10 pass but H5 strongly_negative OR H20 strongly_negative = unstable_horizon_shape
```

`sample gate`、`concentration gate`、`absolute_positive(H)`、`relative_positive(H)` 在 H5 / H20 上完全复用 §12.1-§12.4 的公式，只把当前 summary row 的 `horizon` 换成 H5 或 H20。H5 / H20 不允许使用更宽松门槛。

`strongly_negative(H)` 固定为：

```text
complete_event_count >= 150
AND mean_net_return < -0.0025
AND mean_matched_delta_return < -0.0025
```

如果 H5 或 H20 因样本不足无法判断 `strongly_negative`，必须输出：

```text
adjacent_horizon_shape_status = adjacent_horizon_not_evaluable
```

但不得把不可评估的 adjacent horizon 当成正向确认。若 H10 pass 且任一 adjacent horizon `strongly_negative = true`，final decision 必须降级为：

```text
r01_unstable_horizon_shape_no_search_allowed
```

若 H10 pass 且任一 adjacent horizon 是 `adjacent_horizon_not_evaluable`，同时没有 adjacent horizon `strongly_negative = true`，final decision 必须降级为：

```text
r01_adjacent_horizon_not_evaluable_validation_lead
```

## 14. Big-Winner / Right-Tail Diagnostic

R01 必须保留 big-winner readout，但它不能参与 pass/fail。

Read-only diagnostic 固定为：

```text
big_winner_horizon = H120
big_winner_threshold = +50% gross max close return from entry_price
right_tail_thresholds = +20%, +50%
```

H120 readout 的 split / censoring 规则固定为：

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

官方 split-level right-tail aggregate 只能使用：

```text
right_tail_path_status = complete_same_split_120d
```

如果 120D path 跨越 validation -> robustness 或 robustness -> provider end，该 event 的 row-level diagnostic 可以保留，但必须标记为 `complete_cross_split_120d_readonly` 或 censoring status；不得进入 split-level right-tail rate，也不得参与任何 R01 pass/fail。Provider 尾部不足必须标记为 `censored_provider_end`，不能当作未命中 +20% / +50%。

`right_tail_status` 只能在 `right_tail_path_status in {complete_same_split_120d, complete_cross_split_120d_readonly}` 时输出 `hit_plus50`、`hit_plus20_only` 或 `no_hit_complete`。所有 censored rows 的 `right_tail_status` 必须是 `censored_not_evaluable`，不能当作 `no_hit_complete`。

每个 complete event 必须输出：

```text
max_gain_120d
first_plus20_hit_date
first_plus20_hit_offset
first_plus50_hit_date
first_plus50_hit_offset
H5_net_return
H10_net_return
H20_net_return
post_H20_max_gain_to_H120
right_tail_status
right_tail_path_status
```

允许的解释：

```text
short-horizon unit passed; some post-entry states may deserve later holding-extension diagnostic.
```

禁止的解释：

```text
short-horizon unit failed, but big-winner rate looks high, so R01 passed.
```

如果 R01 pass 后要研究 holding extension，必须另写 requirement；R01 不允许在当前文档内定义 holding tuning。

## 15. Final Decision Contract

R01 final decision 只能是以下之一：

```text
r01_short_horizon_local_unit_supported
r01_sparse_event_unit_supported_event_source_followup
r01_fast_fail_only_loss_control_lead
r01_unstable_validation_only_lead
r01_unstable_horizon_shape_no_search_allowed
r01_adjacent_horizon_not_evaluable_validation_lead
r01_relative_edge_only_hedged_or_regime_audit_required
r01_beta_or_market_exposure_only_no_stock_selection_pass
r01_horizon_specific_lead_only_no_search_allowed
r01_sample_limited_primary_lead_only
r01_sample_limited_sparse_event_source_lead_only
r01_no_local_feasibility_support
r01_blocked_data_or_execution_contract
```

决策优先级：

辅助定义：

```text
h10_validated_pass(unit) =
  sample gate for H10
  AND concentration gate for H10
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
  AND absolute_positive(H10)
  AND relative_positive(H10)

primary_h10_evaluable_for_sparse_followup =
  r01_launch_breakout_money_surge_natural_exit_v0 sample gate for H10
  AND r01_launch_breakout_money_surge_natural_exit_v0 concentration gate for H10

non_fast_fail_unit_for_quadrant =
  r01_launch_breakout_money_surge_natural_exit_v0
  OR (
    r01_base_breakout_vcp_sparse_natural_exit_v0
    AND primary_h10_evaluable_for_sparse_followup
  )
```

1. 若任何必需数据、split、execution、cost 或 canonical unit authority 缺失，输出 `r01_blocked_data_or_execution_contract`。
2. 若 `r01_launch_breakout_money_surge_natural_exit_v0` 满足 `h10_validated_pass`、`robustness_confirmed` 和 `adjacent_horizon_clean`，输出 `r01_short_horizon_local_unit_supported`。
3. 若 `r01_launch_breakout_money_surge_natural_exit_v0` 满足 `h10_validated_pass`，但 `robustness_confirmed = false`，输出 `r01_unstable_validation_only_lead`。
4. 若 `r01_launch_breakout_money_surge_natural_exit_v0` 满足 `h10_validated_pass` 和 `robustness_confirmed`，且任一 adjacent horizon `strongly_negative = true`，输出 `r01_unstable_horizon_shape_no_search_allowed`。
5. 若 `r01_launch_breakout_money_surge_natural_exit_v0` 满足 `h10_validated_pass` 和 `robustness_confirmed`，没有 adjacent horizon `strongly_negative = true`，但 `adjacent_horizon_not_evaluable = true`，输出 `r01_adjacent_horizon_not_evaluable_validation_lead`。
6. 若 primary natural-exit 不满足上述 long-only support，但满足 `primary_h10_evaluable_for_sparse_followup`，且 `r01_base_breakout_vcp_sparse_natural_exit_v0` 满足 `h10_validated_pass`、`robustness_confirmed` 和 `adjacent_horizon_clean`，输出 `r01_sparse_event_unit_supported_event_source_followup`。
7. 若 primary natural-exit 不满足 `h10_validated_pass`，但 `r01_launch_breakout_money_surge_fast_fail_v0` 满足 `h10_validated_pass`、`robustness_confirmed` 和 `adjacent_horizon_clean`，输出 `r01_fast_fail_only_loss_control_lead`。
8. 若没有 long-only support，但至少一个 `non_fast_fail_unit_for_quadrant` 满足 sample、concentration、relative_positive 且 `absolute_positive = false`，输出 `r01_relative_edge_only_hedged_or_regime_audit_required`。
9. 若至少一个 `non_fast_fail_unit_for_quadrant` 满足 sample、concentration、absolute_positive 且 `relative_positive = false`，输出 `r01_beta_or_market_exposure_only_no_stock_selection_pass`。
10. 若任一 `non_fast_fail_unit_for_quadrant` 只有 H5 或 H20 满足 `horizon_pass`、H10 不满足 `horizon_pass`，输出 `r01_horizon_specific_lead_only_no_search_allowed`。
11. 若 `r01_launch_breakout_money_surge_natural_exit_v0` 满足 `sample_limited_return_lead(unit, H10)`，输出 `r01_sample_limited_primary_lead_only`。
12. 若 `r01_base_breakout_vcp_sparse_natural_exit_v0` 满足 `sample_limited_return_lead(unit, H10)`，输出 `r01_sample_limited_sparse_event_source_lead_only`。
13. 其余情况输出 `r01_no_local_feasibility_support`。

上述 final decision 使用 first-match priority：从 rule 1 到 rule 13 依次判断，首个命中规则决定唯一 `final_decision`。如果多个 unit 同时具有描述性 lead，报告必须并列披露所有 unit 的 H10 quadrant、sample status、robustness status 和 adjacent horizon status；不得因为 higher-priority final decision 隐藏 lower-priority unit 的 sample-limited、sparse 或 fast-fail readout。

`r01_short_horizon_local_unit_supported` 也不是 production approval。它只允许下一份 requirement 讨论：

```text
controlled discovery under strict low-dimensional search,
or post-entry holding-extension diagnostic,
or E01-backed reproducible harness expansion.
```

它不允许直接进入 portfolio allocator、hedged strategy、right-tail management 或 live trading。

其他非终止性 final decision 的允许后续固定为：

| final_decision | 允许后续 |
|:--|:--|
| `r01_sparse_event_unit_supported_event_source_followup` | 只能写 low-overlap sparse event-source requirement，不得直接扩成 broad pool search。 |
| `r01_fast_fail_only_loss_control_lead` | 只能写 loss-control / risk-state diagnostic，不得当作底层 exposure pass。 |
| `r01_unstable_validation_only_lead` | 先做 validation / robustness drift explanation，不得进入 search。 |
| `r01_unstable_horizon_shape_no_search_allowed` | 先解释 horizon instability，不得挑选单个 horizon 推进。 |
| `r01_adjacent_horizon_not_evaluable_validation_lead` | 先补足 adjacent horizon 可评估性或解释样本缺口，不得把 H10 单点通过升级为 search。 |
| `r01_sample_limited_primary_lead_only` | 只能先做 primary 事件样本来源和执行阻断复核，不得通过放宽阈值强行堆样本。 |
| `r01_sample_limited_sparse_event_source_lead_only` | 只能先做 sparse event-source 样本可行性复核，不得把稀疏样本包装成 alpha pass。 |

## 16. Reporting Requirements

R01 最终报告必须直接回答：

1. 哪个 canonical unit 在 H10 进入哪个四象限？
2. 结果是 absolute edge、relative edge、beta exposure，还是没有 edge？
3. Validation 2022 / 2023 是否方向一致，还是集中在单一年份？
4. Robustness 2024 / 2025 是否确认，还是把结果降级为 validation-only lead？
5. Matched comparator fallback 是否过高？
6. 收益是否由少数 instrument、industry、entry date 贡献？
7. H5 / H20 是否支持 H10，还是只出现 horizon-specific lead？
8. Big-winner readout 是否只是 post-entry diagnostic，是否被错误用于 pass/fail？
9. 下一份 requirement 被允许启动哪条方向，哪条方向被禁止？

报告必须显式写出：

```text
R01 did not perform alpha search.
R01 did not use big-winner labels for pass/fail.
R01 did not tune thresholds after validation.
R01 does not approve a production strategy.
```

## 17. Relationship to E01

E01 的职责是实现可复现 harness。E01 可以定义：

```text
runner path
config path
output directory
artifact schema
manifest hash
validator checks
```

但 E01 不得改变：

```text
canonical_unit_id
canonical unit role / final-decision authority
horizon_set
execution rule
cost model
split
sample gate
concentration gate
absolute / relative positive definitions
final decision priority
big-winner read-only boundary
```

如果 E01 发现本 requirement 中某个字段无法实现，应回到 R01 修改 requirement，而不是在代码中静默换口径。
