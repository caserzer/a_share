# EP4 需求 05b: Sleeve Allocator / Exposure Composition Diagnostic V1

## 1. 需求元信息

- 需求 id: `ep4_r05b_sleeve_allocator_exposure_composition_diagnostic_v1`
- 简称: `r05b_sleeve_allocator_exposure_composition_diagnostic_v1`
- 状态: implementation-ready diagnostic requirement
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion5.md`
- 上游 R04e 需求: `ep4/requirement_04e_union_pool_portfolio_level_diagnostic_v1.md`
- 上游 R05 Preflight 需求: `ep4/requirement_05_preflight_alpha_pool_quick_feasibility_v1.md`
- 上游 abandoned R05a 需求: `ep4/requirement_05a_alpha_pool_discovery_protocol_v1.md`
- 必需输出根目录: `ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r05b_sleeve_allocator_exposure_composition_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r05b_sleeve_allocator_exposure_composition_diagnostic.py`
- 日期: 2026-05-19

## 2. 背景与目标

R05b 的前提是：

```text
R04e union pool 没有通过 portfolio-level validation。
R05 Preflight 没有找到可进入 R05a full protocol 的 standalone alpha candidate。
R05a 已被 abandoned / preflight-blocked。
```

因此 R05b 不再寻找新的 entry alpha primitive。R05b 只回答一个组合层问题：

```text
现有 failed / relative-improvement pools 是否还能作为 sleeves，
通过 frozen market-state exposure allocation，
在不制造 mostly-cash illusion、不重命名 alpha 的前提下，
形成 validation portfolio-level diagnostic value？
```

R05b 是 diagnostic，不是 production strategy approval。

R05b 禁止输出：

```text
alpha pool passed
new entry alpha discovered
production allocation rule approved
R04e union pool rescued as alpha
R05 preflight failed primitive rescued as alpha
```

## 3. Mandatory Upstream State

R05b 必须读取并校验以下上游 artifact：

```text
upstream_r04e.validation =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/manifests/r04e_union_pool_portfolio_level_validation.json
upstream_r04e.final_decision =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/reports/r04e_final_decision.csv
upstream_r04e.union_event_panel =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_union_event_panel.parquet
upstream_r04e.portfolio_daily_return_panel =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_portfolio_daily_return_panel.parquet
upstream_r04e.portfolio_policy_summary =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/reports/r04e_portfolio_policy_summary.csv
upstream_r04e.baseline_A_portfolio_daily_return_panel =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_baseline_A_portfolio_daily_return_panel.parquet

upstream_r05_preflight.validation =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json
upstream_r05_preflight.final_decision =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_final_decision.csv
upstream_r05_preflight.candidate_event_panel =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/cache/r05_preflight_candidate_event_panel.parquet
upstream_r05_preflight.forward_return_panel =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/cache/r05_preflight_forward_return_panel.parquet
upstream_r05_preflight.candidate_formula_frozen =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_candidate_formula_frozen.csv
upstream_r05_preflight.gate_audit =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_gate_audit.csv

upstream_r05a.requirement =
  ep4/requirement_05a_alpha_pool_discovery_protocol_v1.md
upstream_r05a.status =
  ep4/outputs/r05a_alpha_pool_discovery_protocol_v1/manifests/r05a_status.json
```

R05b runner 必须 fail closed unless：

```text
r04e.validation_status == passed
r04e.final_decision == r04e_union_not_viable_validation
r05_preflight.validation_status == passed
r05_preflight.final_decision == r05_preflight_stop_no_absolute_floor
r05_preflight.candidate_pass_count == 0
r05_preflight.candidate_formula_frozen contains required candidate_id and round_trip_cost_bp
r05a.status_json.status == abandoned_preflight_blocked
r05a.status_json.active_implementation_allowed == false
r05a.status_json.allowed_next_requirement == sleeve_allocator_direction_requirement
```

R05a requirement markdown 只作为 provenance，不得用 grep / line parser 判定状态。R05b 必须读取 machine-readable `r05a_status.json`；该 JSON 缺失或字段不匹配时，R05b 必须 fail closed 为 `r05b_blocked_upstream_state_changed`。

`r05a_status.json` 必需字段：

```text
requirement_id
status
active_implementation_allowed
allowed_next_requirement
blocked_by_requirement_id
created_at
```

如果上述任一条件不满足，workflow final decision 必须是：

```text
r05b_blocked_upstream_state_changed
```

## 4. Data / Split Contract

R05b 继承 EP4 R04/R05 split：

```text
train_start = 2017-07-04
train_end = 2021-12-31
validation_start = 2022-01-01
validation_end = 2023-12-31
robustness_start = 2024-01-01
robustness_end = 2025-12-31
```

R05b 必须使用以下本地数据源：

```text
price_provider.provider_type = qlib_pit_local
price_provider.price_source_path = data/qlib/cn_data_pit
price_provider.calendar_source_path = data/qlib/cn_data_pit/calendars/day.txt
price_provider.instrument_source_path = data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt
market_state.index_instrument = SH000300
market_state.index_feature_path = data/qlib/cn_data_pit/features/sh000300
```

market state 只能使用 index-level as-of data。不得使用任何 candidate pool 的后验收益、R04e outcome、R05 preflight outcome 反向定义状态。

### 4.1 Market-State Feature Formula Contract

Market-state feature 必须只从 `SH000300` 的 adjusted close 序列构造。允许使用 split 起点之前的历史价格只为了满足 rolling lookback；不得用 validation / robustness 价格反向拟合阈值。

特征公式固定为：

```text
index_close_D = adjusted close of SH000300 at state_signal_date D
index_ma20_D = mean(index_close over last 20 trading days including D), min_periods = 20
index_ma60_D = mean(index_close over last 60 trading days including D), min_periods = 60
index_ret20_D = index_close_D / index_close_{D-20 trading days} - 1
index_realized_vol20_D =
  population standard deviation(ddof=0) of daily close-to-close returns
  over the last 20 one-day returns ending at D
  includes the D close / previous trading day close return
  requires 20 one-day returns and therefore 21 closes
  min_periods = 20 returns
index_drawdown60_D =
  index_close_D / max(index_close over last 60 trading days including D) - 1
```

缺失处理固定为：

```text
feature rows with any required feature missing are not eligible for threshold fitting
within train/validation/robustness output dates, missing required features are fatal
state_count must remain <= 3; no "unknown" state is allowed inside output splits
```

### 4.2 Benchmark Reporting Return Formula Contract

`benchmark_reporting_sleeve` 只用于 reporting baseline，不参与任何 allocation、gate pass 或 weight 计算。

Benchmark daily return 的口径固定为：

```text
benchmark_instrument = SH000300
benchmark_price_source = data/qlib/cn_data_pit/features/sh000300/close.day.bin
benchmark_close_t = adjusted close of SH000300 on trade_date t
benchmark_prev_close_t = adjusted close of SH000300 on the previous trading day before t
benchmark_daily_return_t = benchmark_close_t / benchmark_prev_close_t - 1
```

约束：

```text
benchmark_daily_return is attached to trade_date, not state_signal_date
benchmark_daily_return uses close-to-close adjusted return only
the first output trade_date may use one prior trading day's close before the split start
missing benchmark_close_t or benchmark_prev_close_t inside output rows is fatal
forward-fill, backward-fill, open-to-close return, and raw unadjusted close are forbidden
```

Allocator daily panel 的时间语义固定为：

```text
state_signal_date = D close
exposure_effective_date = next tradable day after D
trade_date in allocator_daily_return_panel = exposure_effective_date
market_state attached to trade_date = state computed from previous state_signal_date
allocator weight applied on trade_date must be fully known at D close
```

## 5. Sleeve Registry

R05b 必须先冻结 sleeve registry，并写入：

```text
reports/r05b_sleeve_registry_frozen.csv
```

允许的 sleeve 只有：

| sleeve_id | role | source | allocation_status |
|---|---|---|---|
| `r04e_union_primary_sleeve` | primary | R04e union portfolio daily return | allocation eligible |
| `base_breakout_vcp_secondary_sleeve` | conditional secondary | R05 preflight `base_breakout_vcp_preflight` | capped secondary only |
| `low_vol_uptrend_diagnostic_sleeve` | diagnostic | R05 preflight `low_vol_uptrend_preflight` | no allocation |
| `low_beta_low_vol_diagnostic_sleeve` | diagnostic | R05 preflight `cross_sectional_low_beta_low_vol_preflight` | no allocation |
| `cash_sleeve` | cash | zero return / zero risk asset assumption | allocation eligible |
| `benchmark_reporting_sleeve` | benchmark | SH000300 reporting baseline | no allocation |

### 5.1 Primary Sleeve

Primary sleeve 必须固定为 R04e union pool 的 full-exposure daily portfolio path：

```text
source_artifact = ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_portfolio_daily_return_panel.parquet
portfolio_id = active_equal_weight_uncapped
policy_id = hold_120d__no_exit__none
return_column = portfolio_daily_net_return
active_count_column = active_count
gross_exposure_before_allocator_column = gross_exposure
```

R05b 不允许从 R04e policy matrix 中重新选择 policy，不允许按 validation outcome 选择 `cap20 / cap40 / cap60`，不允许使用 R04e robustness 反向选择 sleeve path。

R04e primary `active_count` 字段语义必须固定为：

```text
active_count =
  number of positions held on trade_date in the frozen R04e portfolio path
  unique live events still inside the hold_120d holding window
  not the number of newly emitted entry signals on trade_date
```

如果 R04e cache 缺少 `active_count` 或 `gross_exposure`，或 `active_count` 字段语义不能证明为当日持仓总数，R05b 必须 fail closed 为 `r05b_blocked_upstream_state_changed`；不得从 R04e union event panel 重算该语义。

Primary sleeve exposure semantics 固定为：

```text
r04e_union_primary_sleeve_daily_return =
  portfolio_daily_net_return from the frozen R04e row

r04e_union_primary_sleeve_active_count =
  active_count from the frozen R04e row

r04e_union_primary_sleeve_gross_exposure_before_allocator =
  gross_exposure from the frozen R04e row

if gross_exposure column is missing:
  fail closed; do not reconstruct exposure from R04e union_event_panel

if active_count column is missing:
  fail closed; do not reconstruct active_count from R04e union_event_panel

if active_count == 0:
  r04e_union_primary_sleeve_daily_return must be 0
  r04e_union_primary_sleeve_gross_exposure_before_allocator must be 0

0 <= r04e_union_primary_sleeve_gross_exposure_before_allocator <= 1
```

### 5.2 Conditional Secondary Sleeve

`base_breakout_vcp_secondary_sleeve` 只允许从 R05 Preflight frozen outputs 构造：

```text
candidate_id = base_breakout_vcp_preflight
source_event_panel = r05_preflight_candidate_event_panel.parquet
source_forward_return_panel = r05_preflight_forward_return_panel.parquet
```

R05 Preflight 只冻结 event membership / execution dates / hold20 endpoint returns；它没有冻结 daily sleeve return path。因此 R05b 允许使用本需求第 4 节的 qlib PIT price provider 重新构造 daily mark-to-market path，但只能用于已经冻结的 R05 Preflight event set，不得重新定义 candidate rule、threshold、collapse rule 或 entry / exit decision。

所有 R05 Preflight-derived sleeves 的 daily replay 公式固定为：

```text
event_set =
  r05_preflight_candidate_event_panel
  joined with r05_preflight_forward_return_panel by candidate_id + event_key
  filtered to candidate_id of the sleeve
  AND kept_event_flag == true
  AND entry_executable_flag == true
  AND path_complete_flag == true

position_active(t) =
  actual_entry_execution_date <= t <= actual_exit_date

position_known_by_previous_close(t) =
  decision_date <= previous_trading_day(t) on the shared R05b trading calendar

position_daily_gross_return(t) =
  if t == actual_entry_execution_date:
    adjusted_close_t / actual_entry_price - 1
  elif actual_entry_execution_date < t < actual_exit_date:
    adjusted_close_t / adjusted_close_previous_trading_day - 1
  elif t == actual_exit_date:
    actual_exit_price / adjusted_close_previous_trading_day - 1

round_trip_cost_bp =
  round_trip_cost_bp from r05_preflight_candidate_formula_frozen.csv
  for the sleeve candidate_id
entry_cost_decimal = round_trip_cost_bp / 20000
exit_cost_decimal = round_trip_cost_bp / 20000
position_daily_net_return(t) =
  position_daily_gross_return(t)
  - entry_cost_decimal if t == actual_entry_execution_date
  - exit_cost_decimal if t == actual_exit_date

sleeve_daily_return(t) =
  equal-weight average of position_daily_net_return(t)
  over positions where position_active(t) == true
  AND position_known_by_previous_close(t) == true
  0.0 if active_count == 0

sleeve_active_count(t) =
  count of active complete executable positions on t
  where position_known_by_previous_close(t) == true

sleeve_gross_exposure_before_allocator(t) =
  1.0 if sleeve_active_count(t) > 0
  0.0 if sleeve_active_count(t) == 0

0 <= sleeve_gross_exposure_before_allocator(t) <= 1
```

R05b v1 不支持 partial-gross secondary sleeves。`sleeve_daily_return` already represents a fully-invested sleeve return when active and zero return when inactive; allocator return must use `sleeve_weight * sleeve_daily_return` without multiplying by `sleeve_gross_exposure_before_allocator` again.

Secondary sleeve active_count 的时序必须可审计：每个计入 trade_date `t` 的 event 必须满足 `decision_date <= previous_trading_day(t)`，且 `actual_entry_execution_date <= t <= actual_exit_date`。如果 R05 Preflight frozen panel 缺少 `decision_date`、`actual_entry_execution_date` 或 `actual_exit_date`，或任何计入 active_count 的 event 在 `t` 当日开盘后才可知，R05b 必须 fail closed；不得默认信任 frozen event set 避免 lookahead。

R05b 必须输出 R05 Preflight replay censor audit。完整性阈值固定为：

```text
preflight_replay_complete_share_min = 0.95

source_event_count =
  count of frozen source events for sleeve candidate_id
kept_event_count =
  count where kept_event_flag == true
entry_executable_event_count =
  count where kept_event_flag == true AND entry_executable_flag == true
complete_replay_event_count =
  count where kept_event_flag == true
  AND entry_executable_flag == true
  AND path_complete_flag == true
complete_replay_event_share =
  complete_replay_event_count / kept_event_count if kept_event_count > 0
  else 0

lookahead_safe_event_count =
  count of complete executable events whose decision_date is strictly before
  every trade_date on which the event contributes to sleeve_active_count
lookahead_censored_event_count =
  complete_replay_event_count - lookahead_safe_event_count
lookahead_audit_status =
  pass if lookahead_censored_event_count == 0
  else fail
```

如果 allocation-eligible 或 capped secondary sleeve 的 `complete_replay_event_share < 0.95`，对应 allocator policy 必须被阻断，`blocking_reason = preflight_replay_complete_share_below_min`。Diagnostic sleeve 的 complete share 不足只能阻断 decomposition 解释，不得触发 allocation pass。

R05b 禁止把 `hold20_net_return` 直接摊销成 daily return，禁止使用 validation outcome 过滤 event，禁止为了提高 secondary sleeve activation 而放宽 `base_breakout_vcp_preflight` 的 frozen event set。

它的角色固定为：

```text
secondary only
max_weight = 0.20
may activate only when market_state == risk_on
may activate only when r04e_union_primary_sleeve active_count < 20
must not be evaluated as standalone alpha gate
must not be threshold-tuned
```

如果该 sleeve 在 validation 中没有足够 active days，结论只能写为 `secondary_sleeve_insufficient_activation`，不得扩大触发条件。

Secondary activation threshold 固定为：

```text
secondary_activation_min_validation_active_days = 20
secondary_activation_min_validation_active_share = 0.02
secondary_activation_min_robustness_active_days = 20
secondary_activation_min_robustness_active_share = 0.02

secondary_activation_eligible_day =
  split in {validation, robustness}
  AND market_state == risk_on
  AND r04e_union_primary_sleeve_active_count < 20
  AND base_breakout_vcp_secondary_sleeve_active_count > 0

secondary_activation_day_count =
  count(split days where secondary_activation_eligible_day)

secondary_activation_day_share =
  secondary_activation_day_count / split_trading_day_count

if split == validation
AND (secondary_activation_day_count < 20
     OR secondary_activation_day_share < 0.02):
  secondary_activation_status = secondary_sleeve_insufficient_activation

if split == robustness
AND (secondary_activation_day_count < 20
     OR secondary_activation_day_share < 0.02):
  secondary_activation_status = robustness_secondary_sleeve_insufficient_activation
```

`secondary_sleeve_insufficient_activation` and `robustness_secondary_sleeve_insufficient_activation` 只阻断 `market_state_cash_plus_basebreakout_secondary_v1`，不得阻断 `market_state_cash_allocator_v1` 或 `full_exposure_primary_baseline` 的诊断。如果 secondary policy 在 validation 通过但 robustness secondary activation 不足，该 secondary policy 不得输出 pass；报告必须说明 robustness 中该 policy 退化为 cash allocator 等价暴露，不能证明 secondary sleeve 可复用。

### 5.3 Diagnostic Sleeves

`low_vol_uptrend_diagnostic_sleeve` 和 `low_beta_low_vol_diagnostic_sleeve` 只用于 return decomposition：

```text
allocation_weight = 0 for all dates
allowed output = decomposition / state interaction / explanatory diagnostic
forbidden output = allocation pass / alpha pass / secondary sleeve promotion
```

## 6. Market State Classifier

R05b 必须在 train split 冻结 market state classifier，并输出：

```text
reports/r05b_market_state_classifier_frozen.csv
reports/r05b_market_state_panel.csv
```

classifier 只允许使用 SH000300 的 D close 已知特征：

```text
index_close_D
index_ma20_D
index_ma60_D
index_ret20_D
index_realized_vol20_D
index_drawdown60_D
```

train-only frozen thresholds：

```text
vol20_high_threshold = train quantile 70% of index_realized_vol20_D
drawdown60_hard_threshold = -10%
trend_positive = index_close_D > index_ma60_D AND index_ret20_D > 0
trend_negative = index_close_D < index_ma60_D OR index_ret20_D < 0
```

state rule：

```text
if index_drawdown60_D <= -10%:
  market_state = risk_off
elif trend_negative AND index_realized_vol20_D >= vol20_high_threshold:
  market_state = risk_off
elif trend_positive AND index_realized_vol20_D < vol20_high_threshold:
  market_state = risk_on
else:
  market_state = risk_neutral
```

execution timing：

```text
state_signal_date = D close
exposure_effective_date = next tradable open after D
```

Forbidden:

```text
validation threshold adjustment
state count > 3
candidate outcome driven state labels
pool-specific state classifier
industry-specific market state grid
robustness-based state relabeling
```

## 7. Allocator Policy Registry

R05b 必须冻结 allocator policy registry，并输出：

```text
reports/r05b_allocator_policy_registry_frozen.csv
```

R05b v1 只允许以下 policies：

### 7.1 `full_exposure_primary_baseline`

```text
policy_role = baseline_reference
is_selectable = false
r04e_union_primary_sleeve_weight = 1.0
base_breakout_vcp_secondary_sleeve_weight = 0.0
cash_sleeve_weight = 0.0
```

`full_exposure_primary_baseline` 始终输出 return / exposure / cash_only diagnostics，但不参与 validation pass/fail、mostly-cash gate 或 final allocator selection。

### 7.2 `market_state_cash_allocator_v1`

```text
if market_state == risk_on:
  r04e_union_primary_sleeve_weight = 1.0
  cash_sleeve_weight = 0.0

if market_state == risk_neutral:
  r04e_union_primary_sleeve_weight = 0.5
  cash_sleeve_weight = 0.5

if market_state == risk_off:
  r04e_union_primary_sleeve_weight = 0.0
  cash_sleeve_weight = 1.0
```

### 7.3 `market_state_cash_plus_basebreakout_secondary_v1`

Start with `market_state_cash_allocator_v1`, then apply:

```text
if market_state == risk_on
AND r04e_union_primary_sleeve_active_count < 20
AND base_breakout_vcp_secondary_sleeve_active_count > 0:
  primary_weight_before_secondary_clip = r04e_union_primary_sleeve_weight
  assert primary_weight_before_secondary_clip >= 0.20
  base_breakout_vcp_secondary_sleeve_weight = 0.20
  r04e_union_primary_sleeve_weight = max(0, primary_weight_before_secondary_clip - 0.20)
else:
  base_breakout_vcp_secondary_sleeve_weight = 0.0
```

In v1 the secondary branch is risk_on only, therefore `primary_weight_before_secondary_clip` must be 1.0. The `max(0, ...)` guard must not hide a negative or underfunded primary-weight configuration; a failed assertion is a validation error.

Total gross exposure must satisfy:

```text
r04e_union_primary_effective_gross_exposure =
  r04e_union_primary_sleeve_weight
  * r04e_union_primary_sleeve_gross_exposure_before_allocator

base_breakout_vcp_secondary_effective_gross_exposure =
  base_breakout_vcp_secondary_sleeve_weight
  * base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator

total_gross_exposure =
  r04e_union_primary_effective_gross_exposure
  + base_breakout_vcp_secondary_effective_gross_exposure

cash_sleeve_weight is excluded from total_gross_exposure
0 <= total_gross_exposure <= 1.0
0 <= r04e_union_primary_sleeve_gross_exposure_before_allocator <= 1.0
0 <= base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator <= 1.0

cash_only_flag =
  total_gross_exposure == 0

allocator_daily_return =
  r04e_union_primary_sleeve_weight
  * r04e_union_primary_sleeve_daily_return
  + base_breakout_vcp_secondary_sleeve_weight
  * base_breakout_vcp_secondary_sleeve_daily_return
```

`total_gross_exposure` and `allocator_daily_return` intentionally use different units:

```text
total_gross_exposure uses sleeve_weight * sleeve_gross_exposure_before_allocator
allocator_daily_return uses sleeve_weight * sleeve_daily_return
```

因为 `sleeve_daily_return` 已经是 sleeve 内部按其 own active exposure 计算后的 return；不得在 return formula 中再次乘以 `sleeve_gross_exposure_before_allocator`。

Mostly-cash guard 必须使用 risk-asset gross exposure，不得把 cash weight 计入 gross exposure：

```text
average_gross_exposure = mean(total_gross_exposure)
cash_only_day_share = mean(cash_only_flag)

all_day_period_return =
  product(1 + sleeve_daily_return over every split trading day) - 1

active_only_period_return =
  product(1 + sleeve_daily_return over days with sleeve_active_count > 0) - 1
  null if sleeve_active_count > 0 never occurs

sleeve_period_return =
  all_day_period_return
```

`cash_only_flag` means no risk-asset exposure, not merely explicit allocation to the cash sleeve. If allocator weight points to a sleeve that is internally inactive, `total_gross_exposure == 0` and `cash_only_flag == true` even when `cash_sleeve_weight == 0`.

No other allocator policy is allowed in v1.

## 8. Mostly-Cash Illusion Guards

R05b pass 必须同时满足：

```text
validation_average_gross_exposure >= 0.35
validation_cash_only_day_share <= 0.65
validation_risk_on_full_exposure_daily_mean > 0
validation_risk_on_full_exposure_period_return > 0
overall_allocator_validation_period_return > 0
overall_allocator_validation_daily_mean > 0
```

Hard kill：

```text
if risk_on_full_exposure_validation_net <= 0:
  market_state_cash_sleeve_cannot_pass
```

如果 allocator 只靠降低 exposure 避开亏损，而 risk-on full-exposure sleeve 本身不赚钱，final decision 不得为 pass。

### 8.1 Metric Formula and Delta Sign Contract

所有 gate metric 必须使用同一套公式：

```text
daily_return = allocator_daily_return or full_exposure_primary_daily_return
period_return = product(1 + daily_return) - 1
daily_mean = mean(daily_return)
monthly_return = product(1 + daily_return within calendar month) - 1
monthly_p10 = quantile(monthly_return, 0.10)
equity_curve = cumulative product(1 + daily_return)
max_drawdown = max(1 - equity_curve / running_max(equity_curve))
rolling_20d_return = product(1 + daily_return over 20 trading days) - 1
worst_20d_return = min(rolling_20d_return)
average_gross_exposure = mean(total_gross_exposure)
cash_only_day_share = mean(cash_only_flag)
```

Delta sign convention 固定为“正数表示 allocator 更好”：

```text
monthly_p10_delta_vs_full_exposure =
  allocator_monthly_p10 - full_exposure_primary_monthly_p10

max_drawdown_delta_vs_full_exposure =
  full_exposure_primary_max_drawdown - allocator_max_drawdown
  positive means allocator has a smaller drawdown loss magnitude

worst_20d_delta_vs_full_exposure =
  allocator_worst_20d_return - full_exposure_primary_worst_20d_return
  positive means allocator has a less negative worst 20d return
```

Right-tail gate 固定为：

```text
allocator_monthly_p90 = quantile(allocator monthly_return, 0.90)
full_exposure_primary_monthly_p90 = quantile(full-exposure primary monthly_return, 0.90)

right_tail_gate_mode allowed values:
  retention_vs_full_exposure
  absolute_p90_floor

right_tail_gate_status allowed values:
  right_tail_pass
  right_tail_fail

right_tail_retention_min =
  0.60 for validation
  0.50 for robustness

absolute_p90_floor_min =
  0.02 for validation
  0.01 for robustness

if full_exposure_primary_monthly_p90 <= 0:
  right_tail_gate_mode = absolute_p90_floor
  right_tail_retention_vs_full_exposure = null
  right_tail_gate_status =
    right_tail_pass if allocator_monthly_p90 >= absolute_p90_floor_min
    else right_tail_fail
else:
  right_tail_gate_mode = retention_vs_full_exposure
  right_tail_retention_vs_full_exposure =
    allocator_monthly_p90 / full_exposure_primary_monthly_p90
  right_tail_gate_status =
    right_tail_pass if right_tail_retention_vs_full_exposure >= right_tail_retention_min
    else right_tail_fail
```

Mode and threshold selection are computed independently per split. Robustness must use robustness `full_exposure_primary_monthly_p90` to choose `robustness_right_tail_gate_mode`; it must not reuse validation mode, validation p90, or validation threshold.

`right_tail_retention_vs_full_exposure` must be null only when `right_tail_gate_mode == absolute_p90_floor`. It must be non-null when `right_tail_gate_mode == retention_vs_full_exposure`. Validator must reject `0` as a placeholder for absolute-p90 mode retention.

Risk-on full-exposure metric 固定为：

```text
risk_on_full_exposure_validation_period_return =
  period_return of full_exposure_primary_daily_return
  on validation trade_dates whose effective market_state == risk_on

risk_on_full_exposure_validation_daily_mean =
  daily_mean of full_exposure_primary_daily_return
  on validation trade_dates whose effective market_state == risk_on

risk_on_full_exposure_validation_net =
  risk_on_full_exposure_validation_period_return
```

## 9. Validation Gates

R05b validation gate 必须比较 allocator 与 full-exposure primary baseline。

Gate 只适用于 selectable allocator policies：

```text
market_state_cash_allocator_v1
market_state_cash_plus_basebreakout_secondary_v1
```

`full_exposure_primary_baseline` 只作为 baseline reference：必须输出 `average_gross_exposure`、`cash_only_day_share`、monthly / drawdown / right-tail 指标，但不得因为 baseline 自身 cash_only_day_share 超过阈值而触发 `r05b_mostly_cash_illusion`，也不得被选为 passing allocator。

Primary validation requirements：

```text
overall_allocator_validation_period_return > 0
overall_allocator_validation_daily_mean > 0
monthly_p10_delta_vs_full_exposure > 0
max_drawdown_delta_vs_full_exposure > 0
worst_20d_delta_vs_full_exposure > 0
validation_average_gross_exposure >= 0.35
validation_cash_only_day_share <= 0.65
risk_on_full_exposure_validation_period_return > 0
risk_on_full_exposure_validation_daily_mean > 0
right_tail_gate_status == right_tail_pass
```

Robustness read-only guardrails：

```text
robustness_period_return >= -5%
robustness_right_tail_gate_status == right_tail_pass
robustness_average_gross_exposure >= 0.35
```

Robustness guardrails are pass-blocking but not selectable:

```text
runner may not choose a policy because robustness looks better
runner may not tune thresholds or weights from robustness
if validation passes but robustness guardrail fails:
  robustness_readonly_status = robustness_readonly_failed
  final_decision cannot be r05b_sleeve_allocator_passed_diagnostic_only
if selected policy is market_state_cash_plus_basebreakout_secondary_v1
AND robustness secondary activation is insufficient:
  robustness_readonly_status = robustness_secondary_sleeve_insufficient_activation
  final_decision cannot be r05b_sleeve_allocator_passed_diagnostic_only
```

Robustness 不能救回 validation failure。

## 10. Required Outputs

R05b 必须输出：

```text
cache/r05b_sleeve_daily_return_panel.parquet
cache/r05b_allocator_daily_return_panel.parquet
reports/r05b_sleeve_registry_frozen.csv
reports/r05b_market_state_classifier_frozen.csv
reports/r05b_market_state_panel.csv
reports/r05b_allocator_policy_registry_frozen.csv
reports/r05b_preflight_replay_censor_audit.csv
reports/r05b_secondary_sleeve_activation_audit.csv
reports/r05b_sleeve_return_decomposition.csv
reports/r05b_risk_on_full_exposure_audit.csv
reports/r05b_mostly_cash_illusion_audit.csv
reports/r05b_allocator_policy_summary.csv
reports/r05b_allocator_monthly_summary.csv
reports/r05b_validation_gate_audit.csv
reports/r05b_terminal_decision_audit.csv
reports/r05b_final_decision.csv
reports/r05b_sleeve_allocator_exposure_composition_final_report.md
manifests/r05b_sleeve_allocator_exposure_composition_manifest.json
manifests/r05b_sleeve_allocator_exposure_composition_validation.json
reports/r05b_sleeve_allocator_exposure_composition_validation_audit.csv
```

### 10.1 `r05b_sleeve_registry_frozen.csv`

Required fields:

```text
sleeve_id
sleeve_role
source_artifact
source_filter
allocation_status
max_weight
formula_hash
blocking_reason
```

### 10.1.1 `r05b_allocator_policy_registry_frozen.csv`

Required fields:

```text
allocator_policy_id
policy_role
allowed_sleeve_ids_json
state_weight_rule_text
secondary_activation_rule_text
gross_exposure_formula_text
cash_excluded_from_gross_exposure_flag
is_selectable
formula_hash
blocking_reason
```

### 10.2 `r05b_market_state_classifier_frozen.csv`

Required fields:

```text
classifier_id
fit_split
index_instrument
feature_set_json
thresholds_json
state_rule_text
state_rule_hash
state_count
signal_timing
execution_timing
active_flag
```

### 10.3 `r05b_market_state_panel.csv`

Required fields:

```text
trade_date
split
state_signal_date
exposure_effective_date
market_state
index_close
index_ma20
index_ma60
index_ret20
index_realized_vol20
index_drawdown60
classifier_id
```

### 10.4 `r05b_sleeve_daily_return_panel.parquet`

Required fields:

```text
trade_date
split
sleeve_id
sleeve_role
sleeve_daily_return
sleeve_active_count
sleeve_gross_exposure_before_allocator
source_artifact
source_candidate_id
source_policy_id
source_portfolio_id
position_replay_method
```

### 10.5 `r05b_allocator_daily_return_panel.parquet`

Required fields:

```text
trade_date
split
allocator_policy_id
state_signal_date
exposure_effective_date
market_state
r04e_union_primary_sleeve_active_count
base_breakout_vcp_secondary_sleeve_active_count
r04e_union_primary_sleeve_gross_exposure_before_allocator
base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator
r04e_union_primary_effective_gross_exposure
base_breakout_vcp_secondary_effective_gross_exposure
r04e_union_primary_sleeve_weight
base_breakout_vcp_secondary_sleeve_weight
cash_sleeve_weight
total_gross_exposure
allocator_daily_return
full_exposure_primary_daily_return
benchmark_daily_return
cash_only_flag
```

`benchmark_daily_return` 必须严格使用 §4.2 的 `SH000300` close-to-close adjusted return 公式；不得由 sleeve return、market-state feature return 或 allocator return 反推。

### 10.6 Replay / Activation Audit Reports

`r05b_preflight_replay_censor_audit.csv` 必需字段：

```text
sleeve_id
candidate_id
split
source_event_count
kept_event_count
entry_executable_event_count
complete_replay_event_count
complete_replay_event_share
complete_share_min
lookahead_safe_event_count
lookahead_censored_event_count
lookahead_audit_status
replay_censor_status
blocking_reason
```

`r05b_secondary_sleeve_activation_audit.csv` 必需字段：

```text
allocator_policy_id
split
validation_trading_day_count
risk_on_day_count
primary_active_lt20_day_count
secondary_active_day_count
secondary_activation_day_count
secondary_activation_day_share
activation_day_count_min
activation_day_share_min
secondary_activation_status
robustness_secondary_activation_status
policy_blocking_reason
```

### 10.7 Decomposition / Risk Audit Reports

`r05b_sleeve_return_decomposition.csv` 必需字段：

```text
sleeve_id
split
market_state
active_day_count
active_day_share
sleeve_period_return
all_day_period_return
active_only_period_return
sleeve_daily_mean
sleeve_monthly_p10
sleeve_monthly_p90
sleeve_max_drawdown
sleeve_return_contribution
allocation_status
decomposition_status
blocking_reason
```

`r05b_risk_on_full_exposure_audit.csv` 必需字段：

```text
split
risk_on_day_count
risk_on_day_share
full_exposure_primary_period_return
full_exposure_primary_daily_mean
full_exposure_primary_monthly_p10
full_exposure_primary_max_drawdown
risk_on_full_exposure_period_return
risk_on_full_exposure_daily_mean
risk_on_full_exposure_gate_status
blocking_reason
```

`r05b_mostly_cash_illusion_audit.csv` 必需字段：

```text
allocator_policy_id
split
average_gross_exposure
average_gross_exposure_min
cash_only_day_share
cash_only_day_share_max
risk_on_full_exposure_period_return
risk_on_full_exposure_daily_mean
overall_allocator_period_return
overall_allocator_daily_mean
mostly_cash_illusion_status
blocking_reason
```

### 10.8 Policy Summary / Monthly Reports

`r05b_allocator_policy_summary.csv` 必需字段：

```text
allocator_policy_id
split
period_return
daily_mean
monthly_p10
monthly_p90
right_tail_gate_mode
right_tail_gate_status
absolute_p90_floor_min
max_drawdown
worst_20d_return
average_gross_exposure
cash_only_day_share
right_tail_retention_vs_full_exposure
secondary_activation_status
robustness_secondary_activation_status
validation_gate_status
robustness_readonly_status
blocking_reason
```

`r05b_allocator_monthly_summary.csv` 必需字段：

```text
allocator_policy_id
month
split
monthly_return
full_exposure_primary_monthly_return
monthly_return_delta_vs_full_exposure
average_gross_exposure
cash_only_day_share
risk_on_day_count
risk_neutral_day_count
risk_off_day_count
```

### 10.9 Gate / Decision Reports

`r05b_validation_gate_audit.csv` 必需字段：

This audit is required for selectable allocator policies. `full_exposure_primary_baseline` may appear only with `validation_gate_status = baseline_reference_only`; it must not be counted as a pass or fail candidate.

```text
allocator_policy_id
split
validation_gate_status
period_return
daily_mean
monthly_p10
monthly_p10_delta_vs_full_exposure
max_drawdown
max_drawdown_delta_vs_full_exposure
worst_20d_delta_vs_full_exposure
average_gross_exposure
cash_only_day_share
risk_on_full_exposure_period_return
risk_on_full_exposure_daily_mean
right_tail_retention_vs_full_exposure
absolute_p90_floor_min
allocator_monthly_p90
full_exposure_primary_monthly_p90
right_tail_gate_mode
right_tail_gate_status
robustness_readonly_status
robustness_period_return
robustness_allocator_monthly_p90
robustness_full_exposure_primary_monthly_p90
robustness_right_tail_gate_mode
robustness_right_tail_gate_status
robustness_right_tail_retention_vs_full_exposure
robustness_absolute_p90_floor_min
robustness_average_gross_exposure
blocking_reason
```

Allowed `validation_gate_status` values:

```text
validation_pass
validation_fail
baseline_reference_only
blocked_secondary_sleeve_insufficient_activation
robustness_secondary_sleeve_insufficient_activation
blocked_preflight_replay_complete_share
robustness_readonly_failed
```

`r05b_final_decision.csv` 必需字段：

```text
requirement_id
final_decision
selected_allocator_policy_id
validation_gate_status
terminal_stop_flag
allowed_next_requirement
blocking_reason
created_at
```

`r05b_terminal_decision_audit.csv` 必需字段：

```text
decision_priority
condition_name
condition_met
candidate_final_decision
selected_final_decision
terminal_stop_flag
allowed_next_requirement
blocking_reason
```

## 11. Final Decision

Allowed workflow-level decisions:

```text
r05b_sleeve_allocator_passed_diagnostic_only
r05b_mostly_cash_illusion
r05b_risk_on_full_exposure_failed
r05b_allocator_not_viable_validation
r05b_blocked_upstream_state_changed
r05b_blocked_validation_failed
```

Decision field contract:

| final_decision | terminal_stop_flag | allowed_next_requirement |
|---|---:|---|
| `r05b_sleeve_allocator_passed_diagnostic_only` | false | `oos_roll_forward_retest_only` |
| `r05b_mostly_cash_illusion` | true | `ep5_escape_hatch_only` |
| `r05b_risk_on_full_exposure_failed` | true | `ep5_escape_hatch_only` |
| `r05b_allocator_not_viable_validation` | true | `ep5_escape_hatch_only` |
| `r05b_blocked_upstream_state_changed` | false | `rerun_upstream_or_refresh_requirement` |
| `r05b_blocked_validation_failed` | false | `fix_validation_failure_only` |

Decision precedence:

```text
1. If required upstream state changed:
     r05b_blocked_upstream_state_changed
     terminal_stop_flag = false
     allowed_next_requirement = rerun_upstream_or_refresh_requirement

2. If validator fails:
     r05b_blocked_validation_failed
     terminal_stop_flag = false
     allowed_next_requirement = fix_validation_failure_only

3. If risk_on_full_exposure_validation_net <= 0:
     r05b_risk_on_full_exposure_failed
     terminal_stop_flag = true
     allowed_next_requirement = ep5_escape_hatch_only

4. If every selectable allocator policy has average gross exposure < 0.35 or cash-only day share > 0.65:
     r05b_mostly_cash_illusion
     terminal_stop_flag = true
     allowed_next_requirement = ep5_escape_hatch_only

5. If no allocator policy passes all validation gates and robustness guardrails:
     r05b_allocator_not_viable_validation
     terminal_stop_flag = true
     allowed_next_requirement = ep5_escape_hatch_only

6. If one fixed allocator policy passes all validation gates and robustness guardrails:
     r05b_sleeve_allocator_passed_diagnostic_only
     terminal_stop_flag = false
     allowed_next_requirement = oos_roll_forward_retest_only
```

If `terminal_stop_flag = true`, R05b final report must explicitly state:

```text
EP4 terminated.
Do not create R05c/R05d sleeve variants.
Further work requires EP5 with a changed universe, horizon, hedge leg, execution model, or problem framing.
```

## 12. Validator Fail-Closed Rules

Validator 必须 fail closed if：

- 任一 required upstream artifact 缺失；
- R04e validation status 不是 `passed`；
- R04e final decision 不是 `r04e_union_not_viable_validation`；
- R05 Preflight validation status 不是 `passed`；
- R05 Preflight final decision 不是 `r05_preflight_stop_no_absolute_floor`；
- R05 Preflight candidate pass count 不是 0；
- R05 Preflight candidate formula frozen artifact 缺失，或缺少 `candidate_id` / `round_trip_cost_bp` 字段；
- R05 Preflight-derived sleeve 的 `round_trip_cost_bp` 不是从 candidate-specific frozen formula row 读取；
- R05a status JSON 缺失，或未标记 `abandoned_preflight_blocked` / `active_implementation_allowed=false` / `allowed_next_requirement=sleeve_allocator_direction_requirement`；
- split 日期与本需求不一致；
- benchmark price file 缺失，或 output split 内 `benchmark_close_t` / `benchmark_prev_close_t` 出现空值；
- sleeve registry 出现未注册 sleeve；
- R05 Preflight-derived sleeve daily return 不是从 frozen event set 加 qlib PIT daily replay 构造；
- R05 Preflight replay censor audit 缺失；
- R05 Preflight-derived sleeve 缺少 `decision_date` / `actual_entry_execution_date` / `actual_exit_date`，或 active_count 包含前一交易日收盘不可知的 event；
- allocation-eligible 或 capped secondary sleeve 的 complete replay event share < 0.95 但仍参与 allocation pass；
- diagnostic sleeve 的 complete replay event share < 0.95 被用于触发 allocation pass 或 workflow-level fail closed；
- `hold20_net_return` 被直接摊销或替代为 daily sleeve return；
- diagnostic sleeve 出现非 0 allocation weight；
- secondary activation audit 缺失；
- `market_state_cash_plus_basebreakout_secondary_v1` 在 `secondary_sleeve_insufficient_activation` 时仍通过 validation gate；
- `market_state_cash_plus_basebreakout_secondary_v1` 在 `robustness_secondary_sleeve_insufficient_activation` 时仍输出 pass；
- `secondary_sleeve_insufficient_activation` 阻断了 `market_state_cash_allocator_v1` 或 `full_exposure_primary_baseline`；
- base breakout secondary sleeve weight > 0.20；
- base breakout secondary sleeve 在非 risk_on 日期激活；
- base breakout secondary sleeve 在 primary active_count >= 20 日期激活；
- secondary branch 下 `primary_weight_before_secondary_clip < 0.20`，或 `max(0, ...)` 掩盖负权重配置；
- R04e primary `active_count` 或 `gross_exposure` column 缺失，或 runner 从 union_event_panel 重算 primary exposure / active_count；
- R04e primary `active_count` 字段语义不是当日持仓总数；
- R04e primary `gross_exposure` 字段值超出 [0, 1]；
- 任一 sleeve_gross_exposure_before_allocator < 0 或 > 1；
- active_count == 0 但 sleeve_gross_exposure_before_allocator != 0；
- market state classifier 使用 validation / robustness fit；
- market state feature 公式、rolling window、ddof、缺失处理与本需求不一致；
- `benchmark_daily_return` 缺失，或未按 §4.2 使用 `SH000300` trade_date close-to-close adjusted return 计算；
- right_tail_gate_mode / right_tail_gate_status 不在 allowed values 中；
- absolute_p90_floor_min 缺失，或 validation / robustness 阈值与 §8.1 不一致；
- right_tail_retention_vs_full_exposure 在 `absolute_p90_floor` mode 下非 null，或在 `retention_vs_full_exposure` mode 下为 null；
- robustness right-tail gate 未按 robustness 自身 p90 重新选择 mode；
- market state 数量超过 3；
- market state 使用 candidate outcome 定义；
- exposure_effective_date 不是 state_signal_date 后下一交易日；
- allocator_daily_return_panel.trade_date 不是 exposure_effective_date；
- metric delta sign convention 与本需求不一致；
- allocator policy registry 出现未注册 policy；
- total_gross_exposure 把 cash_sleeve_weight 计入 gross exposure；
- cash_only_flag 不是按 `total_gross_exposure == 0` 计算；
- `full_exposure_primary_baseline` 被用于 validation pass/fail、mostly-cash gate 或 final allocator selection；
- allocator_daily_return 又额外乘以 sleeve_gross_exposure_before_allocator 导致 double scaling；
- right-tail gate 在 full_exposure_primary_monthly_p90 <= 0 时按 retention=0 自动失败，而不是切换到 absolute p90 floor；
- total gross exposure < 0 或 > 1；
- average gross exposure / cash-only day share 缺失；
- risk-on full-exposure audit 缺失；
- robustness read-only guardrail 缺失，或 robustness guardrail failed 仍输出 pass；
- final decision 与 gate precedence 不一致；
- terminal stop flag 与 allowed next requirement 不一致；
- final report 出现 alpha pass / production allocation approval / R04e rescued as alpha 语言。

## 13. Final Report Requirements

Final report 必须包含：

```text
1. Upstream R04e / R05 Preflight / R05a abandoned state
2. Frozen sleeve registry
3. Frozen market state classifier
4. Market state distribution by split
5. Full-exposure primary baseline performance
6. Risk-on full-exposure audit
7. Allocator policy comparison
8. Mostly-cash illusion audit
9. R05 Preflight replay censor audit
10. Secondary base_breakout activation audit
11. Diagnostic sleeve decomposition
12. Validation gate result
13. Robustness read-only result
14. Terminal stop / allowed next requirement
```

The report must state:

```text
R05b does not discover alpha.
R05b does not reinterpret R04e union as alpha.
R05b does not rescue R05 Preflight failed primitives.
R05b only tests whether failed / relative-improvement pools have limited sleeve value.
```
