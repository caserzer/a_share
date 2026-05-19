# EP4 需求 05 Preflight: Alpha Pool Quick Feasibility V1

## 1. 需求元信息

- 需求 id: `ep4_r05_preflight_alpha_pool_quick_feasibility_v1`
- 简称: `r05_preflight_alpha_pool_quick_feasibility_v1`
- 状态: 实现就绪的 R05a full protocol 低成本方向前置门
- 所属 workflow: EP4
- 上游 R04e 需求: `ep4/requirement_04e_union_pool_portfolio_level_diagnostic_v1.md`
- 下游需求: `ep4/requirement_05a_alpha_pool_discovery_protocol_v1.md`
- 必需输出根目录: `ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/`
- 必需 config 路径: `ep4/configs/r05_preflight_alpha_pool_quick_feasibility_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r05_preflight_alpha_pool_quick_feasibility.py`
- 必需 validator 路径: `ep4/scripts/validate_r05_preflight_alpha_pool_quick_feasibility.py`
- 日期: 2026-05-19

## 2. 实验目的

R05 Preflight 只回答一个方向问题：

```text
新的 low-overlap / non-R02 primitive 是否至少存在 validation absolute positive floor？
```

它不是 alpha pool validation，不允许输出 alpha pass。它的用途是避免在没有正期望迹象的 entry primitive 上投入完整 R05a 工程量。

如果 preflight 都无法在 validation split 上产生正的 hold20 after-cost net mean，完整 R05a 的 matched comparator、block bootstrap、capacity stress、structural risk audit 只会更严格，不应继续执行。

## 3. 必需 Data / Split Contract

R05 Preflight 必须继承 EP4 R04 系列 split：

```text
train_start = 2017-07-04
train_end = 2021-12-31
validation_start = 2022-01-01
validation_end = 2023-12-31
robustness_start = 2024-01-01
robustness_end = 2025-12-31
```

必需数据源：

```text
price_provider.provider_type = qlib_pit_local
price_provider.price_source_path = data/qlib/cn_data_pit
price_provider.calendar_source_path = data/qlib/cn_data_pit/calendars/day.txt
price_provider.instrument_source_path = data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt
price_provider.required_qlib_fields = ["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"]
price_provider.adjustment_policy = qlib_adjusted_ohlc_fields
```

必需 upstream artifact：

```text
upstream_r04e.validation =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/manifests/r04e_union_pool_portfolio_level_validation.json
upstream_r04e.final_decision =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/reports/r04e_final_decision.csv
```

validator 必须检查 R04e validation status 为 `passed`，且 R04e final decision 保持：

```text
r04e_union_not_viable_validation
```

## 4. Preflight Candidate Families

R05 Preflight 只允许三个 canonical candidate：

```text
low_vol_uptrend_preflight
base_breakout_vcp_preflight
cross_sectional_low_beta_low_vol_preflight
```

每个 family 只跑一个固定公式点。不得做 grid search、threshold search、post-hoc filter 或 validation 后重跑。

通用 as-of feature：

```text
decision_date = D after close
entry_execution_date = next tradable open after D
entry_price = adjusted_open(entry_execution_date)
close_D = adjusted_close(D)
ma20_D = mean(close[D-19:D])
ma60_D = mean(close[D-59:D])
ma120_D = mean(close[D-119:D])
ret1_D = close_D / close[D-1] - 1
ret20_D = close_D / close[D-20] - 1
ret60_D = close_D / close[D-60] - 1
log_return_t = ln(close_t / close_{t-1})
realized_vol60_D = std(log_return[D-59:D])
atr20_pct_D = mean(true_range[D-19:D]) / close_D
avg_money20_D = mean(money[D-19:D])
money_ratio5_to20_D = mean(money[D-4:D]) / avg_money20_D
avg_money20_rank_pct_D = same-day cross-sectional pct_rank(avg_money20_D)
realized_vol60_rank_pct_D = same-day cross-sectional pct_rank(realized_vol60_D)
```

market beta feature：

```text
market_log_return_t =
  equal-weight mean of log_return_t across tradable instrument universe

beta120_D =
  cov(stock_log_return[D-119:D], market_log_return[D-119:D])
  / var(market_log_return[D-119:D])

beta120_rank_pct_D =
  same-day cross-sectional pct_rank(beta120_D)
```

所有 rank 使用 deterministic average-rank tie handling。

基础 price-derived feature 必须固定为：

```text
true_range_t =
  max(
    high_t - low_t,
    abs(high_t - close_{t-1}),
    abs(low_t - close_{t-1})
  )

tradable_instrument_universe_D =
  instrument is in price_provider.instrument_source_path
  AND open_D / high_D / low_D / close_D / money_D / volume_D are finite
  AND money_D > 0
  AND volume_D > 0
  AND close_{D-1} is finite

same-day cross-sectional pct_rank universe =
  tradable_instrument_universe_D with required feature complete
```

缺失处理必须固定：

```text
if any feature required by a canonical formula is missing:
  candidate membership = false
  missing_feature_flag = 1 in candidate_event_panel for diagnostic rows if emitted

if beta120 denominator var(market_log_return[D-119:D]) <= 0 or missing:
  beta120_D = null
  cross_sectional_low_beta_low_vol_preflight membership = false
```

## 5. Canonical Formulas

### 5.1 low_vol_uptrend_preflight

```text
close_D > ma120_D
ma60_D > ma120_D
ret60_D >= 0
close_D >= ma60_D * 0.98
avg_money20_rank_pct_D >= 0.30
realized_vol60_rank_pct_D <= 0.40
abs(close_D / ma20_D - 1) <= 0.10
atr20_pct_D <= 0.08
money_ratio5_to20_D <= 2.50
abs(ret1_D) <= 0.08
```

### 5.2 base_breakout_vcp_preflight

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

### 5.3 cross_sectional_low_beta_low_vol_preflight

```text
beta120_rank_pct_D <= 0.40
realized_vol60_rank_pct_D <= 0.40
avg_money20_rank_pct_D >= 0.30
close_D >= ma120_D * 0.95
ret20_D >= -0.03
money_ratio5_to20_D <= 2.00
abs(ret1_D) <= 0.08
atr20_pct_D <= 0.08
```

## 6. Execution / Return Scope

Preflight 只跑最小 after-cost hold20：

```text
entry = next tradable open after D
exit = close after 20 trading days
round_trip_cost_bp = 50
return_type = simple_return
event_collapse_window_trading_days = 20
max_entry_execution_lag_trading_days = 5
max_exit_execution_lag_trading_days = 5
```

不做：

```text
matched comparator
bootstrap
capacity-adjusted pass
structural-risk full audit
portfolio construction
market-state overlay
```

runner 必须按固定顺序处理：

```text
raw trigger construction
deterministic event collapse
entry execution lag
split attribution
exit execution lag within same split
return moment aggregation
```

event collapse 必须是 deterministic：

```text
collapse_grain = candidate_id + instrument_id
collapse_order = decision_date asc, entry_target_date asc, event_key asc
collapse_anchor_date = decision_date
collapse_window_trading_days = 20

keep first raw trigger for each collapse_grain
for later raw triggers in same collapse_grain:
  if decision_date <= 20th tradable date after prior kept collapse_anchor_date:
    suppress trigger
    suppression_reason = suppressed_by_event_collapse
  else:
    keep trigger
```

`r05_preflight_candidate_event_panel.parquet` 只能包含 collapse 后保留的事件。
所有 split summary / gate / return moment 的 `event_count` 都必须等于 collapse 后保留事件数，不得使用 raw trigger 数。
每个保留事件必须写入该 collapse window 内被合并的 raw trigger 数，便于复核连续触发信号是否被重复计数。
被 suppress 的 raw trigger 在 split-level raw/suppressed 统计中必须继承其对应保留事件的 `split`。

split 归属必须绑定到实际入场可执行性：

```text
split_assignment_date =
  actual_entry_execution_date if actual_entry_execution_date is not null
  else entry_target_date

split = assign_split(split_assignment_date)
```

若 `split_assignment_date` 不落在 train / validation / robustness 任一 split 内，该事件必须被剔除出 headline summary，
并在 validation audit 中记录为 `split_assignment_out_of_scope`。

但 runner 必须保留 basic execution flags：

```text
entry_open_available_flag
entry_limit_up_inferred_flag
entry_execution_lag_trading_days
actual_entry_execution_date
exit_available_flag
exit_limit_down_inferred_flag
exit_execution_lag_trading_days
actual_exit_date
path_complete_flag
path_censor_reason
```

entry / exit lag 规则必须固定：

```text
entry_target_date =
  first tradable calendar date after decision_date D

entry_open_available_flag =
  adjusted_open(entry_candidate_date) is finite
  AND adjusted_open(entry_candidate_date) > 0
  AND money(entry_candidate_date) > 0
  AND volume(entry_candidate_date) > 0

entry_limit_up_inferred_flag =
  adjusted_open(entry_candidate_date) >= adjusted_close(previous_tradable_date) * 1.095

entry_executable_flag =
  entry_open_available_flag == 1
  AND entry_limit_up_inferred_flag == 0

actual_entry_execution_date =
  first date from entry_target_date through entry_target_date + 5 tradable days
  where entry_executable_flag == 1

if no executable entry within lag window:
  path_complete_flag = 0
  path_censor_reason = entry_unavailable_after_lag
  event remains in event_count denominator
  event is excluded from complete_event_count and return moments

exit_target_date =
  20th tradable date after actual_entry_execution_date

exit_available_flag =
  adjusted_close(exit_candidate_date) is finite
  AND adjusted_close(exit_candidate_date) > 0
  AND money(exit_candidate_date) > 0
  AND volume(exit_candidate_date) > 0

exit_limit_down_inferred_flag =
  adjusted_close(exit_candidate_date) <= adjusted_close(previous_tradable_date) * 0.905

exit_executable_flag =
  exit_available_flag == 1
  AND exit_limit_down_inferred_flag == 0

actual_exit_date =
  first date from exit_target_date through exit_target_date + 5 tradable days
  where exit_executable_flag == 1
  AND exit_candidate_date <= split_end_date

exit censor precedence =
  1. split_boundary_exit_out_of_split
  2. exit_unavailable_after_lag

if exit_target_date > split_end_date
or exit_target_date + 5 tradable days > split_end_date and no executable exit exists on or before split_end_date:
  path_complete_flag = 0
  path_censor_reason = split_boundary_exit_out_of_split
  event remains in event_count denominator
  event is excluded from complete_event_count and return moments
  runner must not use any exit price after split_end_date

if full exit lag window is inside split and no executable exit exists within lag window:
  path_complete_flag = 0
  path_censor_reason = exit_unavailable_after_lag
  event remains in event_count denominator
  event is excluded from complete_event_count and return moments

hold20_net_return =
  actual_exit_price / actual_entry_price - 1 - round_trip_cost_bp / 10000
```

## 7. 必需输出

```text
cache/r05_preflight_candidate_event_panel.parquet
cache/r05_preflight_forward_return_panel.parquet
reports/r05_preflight_candidate_formula_frozen.csv
reports/r05_preflight_split_return_summary.csv
reports/r05_preflight_execution_audit.csv
reports/r05_preflight_event_collapse_audit.csv
reports/r05_preflight_gate_audit.csv
reports/r05_preflight_final_decision.csv
reports/r05_preflight_alpha_pool_quick_feasibility_final_report.md
manifests/r05_preflight_alpha_pool_quick_feasibility_manifest.json
manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json
reports/r05_preflight_alpha_pool_quick_feasibility_validation_audit.csv
```

`r05_preflight_candidate_formula_frozen.csv` 必需字段：

```text
candidate_id
candidate_family
formula_text
formula_hash
parameter_json
decision_date_policy
entry_policy
exit_policy
round_trip_cost_bp
active_flag
```

`r05_preflight_candidate_event_panel.parquet` 必需字段：

```text
candidate_id
candidate_family
instrument_id
decision_date
entry_target_date
event_key
split
split_assignment_date
formula_hash
membership_flag
missing_feature_flag
raw_trigger_date
collapse_anchor_date
collapse_window_trading_days
raw_trigger_count_in_window
suppressed_trigger_count_in_window
kept_event_flag
entry_open_available_flag
entry_limit_up_inferred_flag
entry_executable_flag
actual_entry_execution_date
entry_execution_lag_trading_days
path_censor_reason
```

`r05_preflight_forward_return_panel.parquet` 必需字段：

```text
candidate_id
candidate_family
instrument_id
event_key
split
decision_date
actual_entry_execution_date
actual_entry_price
exit_target_date
actual_exit_date
actual_exit_price
split_assignment_date
split_end_date
exit_available_flag
exit_limit_down_inferred_flag
exit_executable_flag
exit_execution_lag_trading_days
hold20_gross_return
hold20_net_return
path_complete_flag
path_censor_reason
```

`r05_preflight_execution_audit.csv` 必需字段：

```text
candidate_id
candidate_family
split
event_count
entry_unavailable_after_lag_count
entry_limit_up_block_count
exit_unavailable_after_lag_count
exit_limit_down_block_count
split_boundary_exit_out_of_split_count
complete_event_count
complete_event_share
execution_audit_status
blocking_reason
```

`r05_preflight_event_collapse_audit.csv` 必需字段：

```text
candidate_id
candidate_family
instrument_id
raw_trigger_count
kept_event_count
suppressed_by_collapse_count
collapse_window_trading_days
first_raw_trigger_date
last_raw_trigger_date
collapse_audit_status
blocking_reason
```

`r05_preflight_split_return_summary.csv` 必需字段：

```text
candidate_id
candidate_family
split
event_count
raw_trigger_count
suppressed_by_collapse_count
complete_event_count
complete_event_share
hold20_net_mean
hold20_net_median
hold20_net_p10
loss_le_5_rate
```

`r05_preflight_gate_audit.csv` 必需字段：

```text
candidate_id
candidate_family
validation_event_count
validation_complete_event_share
validation_hold20_net_mean
validation_hold20_net_median
validation_hold20_net_p10
validation_loss_le_5_rate
preflight_gate_status
blocking_reason
```

`r05_preflight_final_decision.csv` 必需字段：

```text
requirement_id
final_decision
candidate_pass_count
passed_candidate_ids
passed_candidate_families
blocking_reason
allowed_next_requirement
created_at
```

`r05_preflight_alpha_pool_quick_feasibility_manifest.json` 必需字段：

```text
requirement_id
requirement_path
config_path
output_root
created_at
split_definition_hash
price_provider_hash
upstream_artifact_hashes_json
formula_hashes_json
final_decision
artifact_hashes_json
```

`r05_preflight_alpha_pool_quick_feasibility_validation.json` 必需字段：

```text
validation_status
failed_checks
warning_checks
final_decision
candidate_pass_count
created_at
audit_path
manifest_path
```

`r05_preflight_alpha_pool_quick_feasibility_validation_audit.csv` 必需字段：

```text
check_id
check_name
severity
status
details
artifact_path
```

validator 必须 fail closed：

- 任一必需 artifact 缺失；
- 任一必需字段缺失；
- R04e validation status 不是 `passed`；
- R04e final decision 不是 `r04e_union_not_viable_validation`；
- split 日期与本需求不一致；
- 任一 headline summary / gate 使用 raw trigger count 代替 collapse 后保留事件数；
- `r05_preflight_candidate_event_panel.parquet.kept_event_flag` 存在非 1 值；
- 任一同一 `candidate_id + instrument_id` 的保留事件违反 20 trading-day collapse window；
- `raw_trigger_count` 不等于 `kept_event_count + suppressed_by_collapse_count`；
- split-level raw/suppressed 统计未按对应保留事件的 `split` 归属；
- `split_assignment_date` 未按 `actual_entry_execution_date else entry_target_date` 生成；
- 任一 `path_complete_flag == 1` 的记录出现 `actual_exit_date > split_end_date`；
- 任一跨 split exit path 未标记为 `split_boundary_exit_out_of_split`；
- `split_assignment_out_of_scope` 事件进入 headline summary / gate；
- formula hash 缺失或公式文本与 hash 不一致；
- canonical candidate 数量不是 3；
- 出现非 canonical candidate；
- `r05_preflight_gate_audit.csv.preflight_gate_status` 出现未注册状态；
- `r05_preflight_final_decision.csv.final_decision` 出现未注册状态；
- final decision 与 candidate-level gate 逻辑不一致；
- `r05_preflight_go_r05a_full_protocol` 下 `passed_candidate_ids` 或 `passed_candidate_families` 为空；
- preflight final report 出现 alpha pass / production entry rule 语言。

## 8. Gate 与 Final Decision

candidate-level preflight pass 需要同时满足：

```text
validation_event_count >= 300
validation_complete_event_share >= 95%
validation_hold20_net_mean > 0
validation_hold20_net_median > -0.50%
validation_hold20_net_p10 > -8.00%
```

candidate-level status 只允许：

```text
preflight_pass
preflight_fail_no_absolute_floor
preflight_fail_insufficient_sample
preflight_fail_execution_blocked
```

`r05_preflight_gate_audit.csv.preflight_gate_status` 必须逐 candidate 写入上述状态。只有 `preflight_pass` candidate 可以进入 R05a full protocol。

workflow-level final decision 只允许：

```text
r05_preflight_go_r05a_full_protocol
r05_preflight_stop_no_absolute_floor
r05_preflight_insufficient_sample
r05_preflight_execution_blocked
```

决策规则：

```text
if any candidate-level preflight pass:
  final_decision = r05_preflight_go_r05a_full_protocol
  allowed_next_requirement = ep4/requirement_05a_alpha_pool_discovery_protocol_v1.md
  passed_candidate_ids = only candidate_id with preflight_gate_status == preflight_pass
  passed_candidate_families = only candidate_family with preflight_gate_status == preflight_pass

elif all candidates have validation_event_count < 300:
  final_decision = r05_preflight_insufficient_sample
  allowed_next_requirement = sample_extension_only

elif any candidate has validation_complete_event_share < 95%:
  final_decision = r05_preflight_execution_blocked
  allowed_next_requirement = execution_model_repair_only

else:
  final_decision = r05_preflight_stop_no_absolute_floor
  allowed_next_requirement = sleeve_allocator_direction_requirement
```

R05 Preflight 不允许 claim alpha。即使 final decision 是 `r05_preflight_go_r05a_full_protocol`，也只能说明 full R05a protocol 值得执行。

如果 workflow final decision 是 `r05_preflight_go_r05a_full_protocol`，R05a 也只能启用 `passed_candidate_families`。未通过 preflight 的 family 必须在 R05a formula grid 中标记为：

```text
preflight_blocked_not_allowed_in_r05a
```

不得通过 R05a full protocol 重新启用。

## 9. R05a Blocking Contract

R05a full protocol 必须把 R05 Preflight 作为 mandatory upstream：

```text
upstream_r05_preflight.validation =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json
upstream_r05_preflight.final_decision =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_final_decision.csv
```

如果 R05 Preflight validation status 不是 `passed`，或 R05 Preflight final decision 不是 `r05_preflight_go_r05a_full_protocol`，R05a runner 必须停止，validator 必须 fail closed。
