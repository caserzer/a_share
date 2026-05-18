# EP4 需求 04b: Fixed-Entry Hold / Exit / Risk-Budget CTA Diagnostic V1

## 1. 需求元信息

- 需求 id: `ep4_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1`
- 简称: `r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1`
- 状态: 首版可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion4.md`
- 上游 R04 需求: `ep4/requirement_04_dynamic_momentum_exposure_eligibility_audit_v1.md`
- 上游 R04 输出根目录: `ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/`
- 必需输出根目录: `ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic.py`
- 日期: 2026-05-18

## 2. 背景与实验目的

R04 v1 的结论是：

```text
RPS / momentum 更像右尾候选池生成器，不是 action-time entry trigger。
RPS + market + industry 没有形成稳定的 OOS exposure eligibility gate。
baseline_A RPS pool 仍保留右尾，但 bad path / early failure 很重。
```

因此 R04b 不再继续寻找新的 entry filter，也不继续叠加：

```text
volume_money gate
stock volatility / ATR entry gate
price extension entry gate
market + industry selected entry pool
```

R04b 只回答一个收窄后的问题：

```text
在固定 RPS episode-first-trigger entry pool 上，
预注册的 hold / exit / sizing policy 是否能压缩坏路径，
同时保留 RPS pool 的 max_gain50 右尾？
```

CTA / trailing exit 在本需求中不是独立策略方向，也不是新 entry 方法，而只是：

```text
exit_rule family 中的一类实现。
```

R04b 的实验单元固定为：

```text
policy_id = hold_rule_id x exit_rule_id x sizing_rule_id
```

其中：

- `hold_rule` 定义最长持有窗口或自然到期窗口；
- `exit_rule` 定义提前退出逻辑，CTA / trailing 是其中一类；
- `sizing_rule` 定义入场后的风险预算或头寸缩放逻辑。

本需求的核心目标不是让胜率更漂亮，而是验证：

```text
bad-path loss compression
WITHOUT destroying max_gain50 winner retention
```

## 3. Non-Negotiables

### 3.1 固定 entry pool

R04b 的 primary candidate pool 必须是 R04 v1 的 baseline_A：

```text
R04 included single_momentum_rps episode-first-trigger rows
```

主池不得使用：

```text
mask_B_market_non_missing
mask_B_market_constructive_no_default_rebound_penalty
mask_C_industry_leadership
any market x industry selected pool
```

原因：

```text
R04 v1 未证明 market + industry exposure eligibility 有稳定 OOS 增量。
如果 R04b 在 mask_C pool 上测试 CTA，将无法区分收益来自 CTA 还是来自上游 entry filter。
```

允许 market / industry state 进入：

```text
interaction audit
subgroup report
risk-budget descriptive analysis
```

但不允许进入：

```text
entry selection
entry allow/block rule
policy promotion denominator restriction
```

例如允许的问题是：

```text
CTA-A 在 downtrend_low_breadth subgroup 下是否比 normal_uptrend subgroup 更有效？
```

禁止的问题是：

```text
只在 downtrend_low_breadth 上应用 CTA-A 后是否通过？
```

后者是变相 entry gate。

### 3.2 固定 entry anchor

每个 candidate 的 entry 必须继承 R04 action-time anchor：

```text
anchor_signal_date = R04 baseline_A episode-first-trigger signal date
entry_execution_date = first executable next-open after anchor_signal_date
entry_price = executable next-open price
```

不得重新搜索 entry day，不得等待更多 family signal，不得使用：

```text
fresh-anchor
seed-anchor
family-order anchor
bad-shape T+10 anchor
market regime transition anchor
```

### 3.3 CTA 不能被特殊照顾

CTA / trailing 必须和以下 baseline 在同一张 policy comparison table 中比较：

```text
no_exit
fixed_stop
time_stop
break_even_after_gain
profit_lock_after_gain
ATR trailing
EMA trailing
```

不能只证明：

```text
CTA 比 no management 好。
```

必须证明：

```text
CTA / trailing family 在同一 train-selected / validation-selected 纪律下，
相对 fixed_stop / time_stop / profit_lock 等对照仍有可解释增量。
```

### 3.4 不允许把 exit improvement 写成 exposure eligibility improvement

R04b 的所有结论只能写成：

```text
fixed-entry hold / exit / sizing diagnostic
```

不得写成：

```text
RPS entry gate passed
market exposure eligibility passed
industry leadership gate passed
production CTA strategy ready
position sizing rule ready
```

## 4. Gate 0: Replay 与 Metric 语义冻结

R04b 在任何 policy replay 前，必须先通过 Gate 0。

Gate 0 是 R04b 的前置依赖，不是后续优化项。runner 必须把 Gate 0 spec 原样写出到：

```text
reports/r04b_gate0_metric_replay_spec_frozen.csv
```

Gate 0 必须冻结以下口径。

### 4.1 Return 口径

默认主口径：

```text
return_type = simple_return
entry_price = adjusted next-open executable price
exit_price = adjusted next-open executable price after exit signal
gross_return = exit_price / entry_price - 1
net_return = gross_return - entry_cost - exit_cost - slippage_cost
```

`log_return` 只能作为 secondary audit，不得驱动 policy selection。

成本项必须在 config 中冻结：

```yaml
cost_model:
  entry_slippage_bps: <frozen>
  exit_slippage_bps: <frozen>
  commission_bps: <frozen>
  stamp_tax_bps: <frozen>
  min_fee_policy: <frozen_or_none>
```

### 4.2 Exit execution 口径

R04b v1 的主 replay 使用 close-based signal / next-open execution：

```text
exit_signal_date = first date whose close-based policy condition is true
exit_execution_date = first executable next-open after exit_signal_date
```

禁止在 primary replay 中用当日 low / high 触发后假设同日成交，因为日线 OHLC 无法确定真实盘中顺序。

允许输出 secondary intraday_stop_sensitivity：

```text
if low <= stop_threshold then exit at stop price
```

但该 sensitivity 不得用于 policy selection 或 final decision。

### 4.3 Censored path 口径

候选样本如果无法形成完整 policy replay，必须保留在 audit 中，并标记：

```text
replay_status in {
  replay_complete,
  censored_by_split_boundary,
  censored_by_missing_price,
  censored_by_suspension_or_dirty_bar,
  censored_by_no_exit_execution,
  invalid_entry
}
```

主 headline 默认只使用：

```text
replay_status == replay_complete
```

但必须同时输出 censored audit，量化每个 split / policy 的 excluded share。

如果某 policy 的 validation 或 robustness replay_complete denominator 低于阈值，该 policy 只能进入 descriptive table，不得成为 selected policy。

### 4.4 Bad path 重新定义

R04 的 legacy primary metric：

```text
+10 before -5
```

在 R04b 中只能作为 legacy diagnostic，不得作为 primary metric。

原因：

```text
在 CTA / stop policy 下，-5 可能是 policy 主动截断之前或之后的事件，
继续使用 +10 before -5 会把 exit policy 的主动行为误算成自然路径优势。
```

R04b primary bad-path 指标必须使用 policy replay 后的结果：

```text
policy_realized_loss_le_minus5_rate
policy_realized_loss_le_minus10_rate
policy_max_adverse_excursion_p50 / p75 / p90
left_tail_net_return_p10
bad_path_loss_compression_vs_hold120
```

### 4.5 max_gain50 retention 定义

R04b 的右尾保护约束以 hold_120d baseline 为对照。

先在无退出 baseline 上定义：

```text
hold120_max_gain50_flag =
  gross_max_adjusted_close_return_from_entry_to_day120 >= 0.50
```

`hold120_max_gain50_flag` 是潜在右尾 winner 标识，必须使用 gross adjusted close path return，不扣成本、不乘 sizing weight。

对每个 policy 定义：

```text
policy_retained_max_gain50_flag =
  hold120_max_gain50_flag == true
  AND policy_exit_execution_date >= hold120_first_plus50_hit_date
```

其中 `hold120_first_plus50_hit_date` 也必须由同一条 gross adjusted close path 计算。policy retention 只判断是否在首次 +50% gross path hit 之前提前离场；不得用 net return、position weight 或成本修正该 retention 判定。

如果 policy 从未提前退出，且 hold120 达到 +50%，则视为保留。

如果 policy 在首次 +50% 命中前退出，即使退出时已经盈利，也视为未保留 max_gain50。

`net_return` 只用于 payoff aggregation，不得用于定义 `hold120_max_gain50_flag`、`hold120_first_plus50_hit_date` 或 `policy_retained_max_gain50_flag`。

主保留率定义：

```text
max_gain50_retention_vs_hold120 =
  sum(policy_retained_max_gain50_flag)
  / sum(hold120_max_gain50_flag)
```

该指标必须按 split 单独计算，并输出 Wilson interval。

### 4.6 门槛候选

R04b v1 的主门槛候选冻结为：

```text
min_max_gain50_retention_vs_hold120 = 0.60
```

解释：

```text
如果一个 policy 压缩了 bad path，但保留的 hold120 max_gain50 winner 少于 60%，
则它破坏了 RPS pool 的核心右尾价值，不得通过 final gate。
```

可输出 report-only sensitivity：

```text
max_gain50_retention_threshold_sensitivity in {0.50, 0.60, 0.70}
```

但 pass/fail 只能使用冻结的 `0.60`。

## 5. 必需输入

### 5.1 R04 validation 与 manifest

必须读取并校验：

```text
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_validation.json
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_manifest.json
```

必须满足：

```text
validation_status == passed
final_decision in {
  r04_v1_exposure_eligibility_audit_complete_descriptive_only,
  proceed_to_r04b_hold_exit_only,
  stop_exposure_eligibility_route_no_oos_lift
}
```

如果 R04 validation 未通过，R04b 必须 fail closed：

```text
blocked_upstream_r04_validation_failed
```

### 5.2 Candidate pool

主 candidate pool 固定来自：

```text
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_rps_candidate_action_panel.parquet
```

必须使用：

```text
r04_inclusion_status == included
split in {train, validation, robustness}
episode_entry_valid == true
entry_execution_date not null
entry_price > 0
```

不得从 raw repeated-trigger panel 重构主分母。

必须输出 input reconciliation：

```text
reports/r04b_input_reconciliation_audit.csv
```

字段至少包含：

```text
split
r04_candidate_rows
included_rows
valid_entry_rows
policy_replay_eligible_rows
excluded_invalid_entry
excluded_missing_price_path
excluded_split_boundary
source_manifest_hash
source_candidate_panel_hash
```

### 5.3 Market / industry interaction fields

为了 subgroup / interaction audit，可以读取：

```text
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_candidate_regime_join_panel.parquet
```

只允许使用以下字段作为 interaction labels：

```text
market_regime_bucket
industry_regime_bucket
industry_target_key
stock_rps_60d
stock_rps_minus_industry_rps_60d
```

这些字段不得改变主 pool，也不得参与 train policy selection，除非作为明确的 report-only subgroup。

### 5.4 Price path

R04b 必须使用本地 PIT price data，不得在线抓取。

price path 必须至少覆盖：

```text
entry_execution_date through entry_execution_date + 120 trading days
```

必需字段：

```text
instrument_id
trade_date
open
close
high
low
volume
money
factor_or_adjusted_price_flag
suspended_or_dirty_bar
```

如果价格来自 Qlib / PIT parquet / cached panel，runner 必须在 manifest 中记录：

```text
price_source_path
price_source_hash
calendar_source_path
calendar_source_hash
adjustment_policy
```

### 5.5 Optional volatility / ATR fields

ATR / volatility 只能用于 exit distance 或 sizing，不得用于 entry allow/block。

ATR 必须使用 entry 后每个 exit_signal_date 当天可知的数据：

```text
TR_t = max(
  high_t - low_t,
  abs(high_t - close_{t-1}),
  abs(low_t - close_{t-1})
)
ATR_14_asof_t = mean(TR_{t-13}, ..., TR_t)
```

不得使用 future high / low 计算当日以前的 ATR。

## 6. Split 与选择纪律

R04b 必须继承 R04 split：

```text
train
validation
robustness
```

### 6.1 Train selection

Train 只能用于：

```text
select parameters within each pre-registered policy family
```

例如：

```text
ATR trailing family: choose k from {2.5, 3.0, 3.5}
fixed stop family: choose stop from {-5%, -8%, -10%}
profit lock family: choose activation from {+10%, +15%, +20%}
ATR trailing canonical family: choose k from {2.5, 3.0, 3.5} with min_activation_gain_pct = 0.00
```

Train 不得用于新增 policy family、删除失败 family、修改 metric formula。

Activated ATR trailing variants with `min_activation_gain_pct > 0` are sensitivity-only in R04b v1. They must not enter train parameter selection, validation family selection, or final decision.

### 6.2 Validation selection

Validation 只能用于：

```text
select policy family among train-selected family representatives
```

例如：

```text
fixed_stop vs time_stop vs ATR_trailing vs EMA_trailing
```

Validation 不得用于调 family 内参数。

### 6.3 Robustness read-only

Robustness 只能用于 final readout：

```text
no parameter tuning
no policy family replacement
no threshold changes
no subgroup promotion
```

任何使用 robustness 结果改变 policy 的行为都必须进入下一版 requirement，不能回填当前 R04b。

### 6.4 Selection audit

必须输出：

```text
reports/r04b_policy_selection_trace.csv
```

字段至少包含：

```text
selection_stage
split_used
policy_family_id
candidate_policy_id
parameter_set_id
selection_metric_name
selection_metric_value
selection_rank
z_reference_set_id
z_reference_set_size
selected_flag
rejection_reason
```

Validator 必须检查：

```text
parameter_set selected only from train
policy_family selected only from validation
robustness never appears in selection_stage
```

## 7. Policy Matrix

R04b v1 必须使用有限矩阵，不允许全参数大网格。

Runner 必须写出 frozen policy spec：

```text
reports/r04b_policy_matrix_frozen.csv
```

字段至少包含：

```text
policy_id
hold_rule_id
exit_rule_id
sizing_rule_id
policy_family_id
parameter_set_id
is_baseline_policy
is_train_selectable
is_validation_selectable
is_sensitivity_policy
parameter_reference_group_id
validation_family_reference_set_id
invalid_policy_reason
entry_rule_text
hold_rule_formula
exit_rule_formula
sizing_rule_formula
cost_model_id
formula_hash
```

### 7.1 Hold rule candidates

R04b v1 允许：

```text
hold_20d:
  max_holding_days = 20

hold_60d:
  max_holding_days = 60

hold_120d:
  max_holding_days = 120
```

`hold_120d + no_exit + fixed_size` 是主对照 baseline：

```text
baseline_hold120_no_exit_fixed_size
```

所有 max_gain50 retention 必须以该 baseline 的 `hold120_max_gain50_flag` 为分母。

### 7.2 Exit rule families

R04b v1 允许以下 exit families。

#### no_exit

```text
exit_signal_date = entry_execution_date + max_holding_days
```

#### fixed_stop

Close-based fixed stop：

```text
exit if close_return_from_entry <= stop_loss_pct
else exit at max_holding_days
```

候选参数：

```yaml
stop_loss_pct: [-0.05, -0.08, -0.10]
```

#### time_stop

```text
exit at fixed holding day N
```

候选参数：

```yaml
time_stop_days: [10, 20, 40, 60]
```

#### break_even_after_gain

```text
if close_return_from_entry >= activation_gain_pct:
  stop_floor = 0
exit if close_return_from_entry <= stop_floor after activation
else exit at max_holding_days
```

候选参数：

```yaml
activation_gain_pct: [0.10, 0.15, 0.20]
```

#### profit_lock_after_gain

```text
if close_return_from_entry >= activation_gain_pct:
  stop_floor = locked_gain_pct
exit if close_return_from_entry <= stop_floor after activation
else exit at max_holding_days
```

候选参数：

```yaml
activation_gain_pct: [0.15, 0.20, 0.30]
locked_gain_pct: [0.05, 0.10]
```

Invalid combination:

```text
locked_gain_pct >= activation_gain_pct
```

Invalid combinations must be rejected before replay and must not appear as selectable rows in `r04b_policy_matrix_frozen.csv`. They may appear only as audit rows with `invalid_policy_reason = locked_gain_pct_ge_activation_gain_pct` and both `is_train_selectable = false` and `is_validation_selectable = false`.

#### ATR trailing

Close-based ATR trailing:

```text
trail_stop_t = max(previous_trail_stop, highest_close_since_entry - k_atr * ATR_14_asof_t)
exit if close_t <= trail_stop_t
else exit at max_holding_days
```

候选参数：

```yaml
k_atr: [2.5, 3.0, 3.5]
min_activation_gain_pct_for_selection: [0.00]
min_activation_gain_pct_sensitivity_only: [0.10]
```

If `min_activation_gain_pct > 0`, trailing stop is inactive until close return first reaches the activation threshold.

R04b v1 treats `min_activation_gain_pct = 0.00` as the canonical ATR trailing family for train / validation selection. `min_activation_gain_pct = 0.10` is allowed only as report-only sensitivity because its behavior overlaps with break-even / profit-lock families. Sensitivity-only ATR variants must have:

```text
is_sensitivity_policy = true
is_train_selectable = false
is_validation_selectable = false
```

#### EMA trailing

Close-based EMA trailing:

```text
exit if close_t < EMA_N_t for confirm_days consecutive days
else exit at max_holding_days
```

候选参数：

```yaml
ema_window: [10, 20]
confirm_days: [1, 2, 3]
```

### 7.3 Sizing rule families

Sizing 只影响 payoff aggregation，不影响 entry eligibility。

R04b v1 允许：

#### fixed_size

```text
position_weight = 1.0
```

#### volatility_scaled

```text
position_weight = clip(target_vol / stock_realized_vol_20d_asof_entry, min_weight, max_weight)
```

候选参数：

```yaml
target_vol: [0.02]
min_weight: [0.25]
max_weight: [1.00]
```

R04b v1 freezes `volatility_scaled` as a single-point sizing candidate. It is not a train-searchable volatility target family. Any target-volatility sensitivity belongs to a later R04c requirement.

#### market_state_scaled

Market state 只能缩放，不得 block：

```text
position_weight =
  1.00 if market_regime_bucket in {downtrend_low_breadth, normal_range}
  0.75 if market_regime_bucket == normal_uptrend
  0.50 if market_regime_bucket == missing_market_regime
```

该规则是 pre-registered descriptive sizing candidate。它不得被解释为 market entry gate。

If market regime is missing due to upstream data gap, weight must follow the frozen missing policy; runner must not infer a better state after outcome inspection.

## 8. Required Metrics

所有 metrics 必须按以下 grain 输出：

```text
policy_id
split
```

并在需要时补充：

```text
market_regime_bucket
industry_regime_bucket
calendar_year
instrument_id
```

### 8.1 Primary policy metrics

主表必须包含：

```text
event_count
replay_complete_count
replay_complete_rate
weighted_event_count
net_return_mean
net_return_median
net_return_p10
net_return_p25
net_return_p75
net_return_p90
realized_loss_le_minus5_rate
realized_loss_le_minus10_rate
max_adverse_excursion_p50
max_adverse_excursion_p75
max_adverse_excursion_p90
bad_path_loss_compression_vs_hold120
max_gain50_retention_vs_hold120
max_gain50_retention_wilson_lower
max_gain50_retention_wilson_upper
winner_exit_efficiency
avg_holding_days
turnover_proxy
cost_bps_mean
```

### 8.2 Bad-path compression

定义：

```text
bad_path_loss_compression_vs_hold120 =
  hold120_realized_loss_le_minus5_rate
  - policy_realized_loss_le_minus5_rate
```

如果该值为正，说明 policy 降低了 -5% realized loss 频率。

必须同时输出 left-tail return，不得只看 loss frequency：

```text
left_tail_net_return_p10_delta_vs_hold120 =
  policy_net_return_p10 - hold120_net_return_p10
```

### 8.3 Winner exit efficiency

对 hold120 max_gain50 winners：

```text
winner_exit_efficiency =
  policy_net_return_mean among hold120_max_gain50_flag
  / hold120_net_return_mean among hold120_max_gain50_flag
```

如果 denominator 不足，标记：

```text
winner_efficiency_status = insufficient_winner_denominator
```

### 8.4 Legacy diagnostics

R04 legacy fields 必须保留但不得驱动 final decision：

```text
legacy_plus10_before_minus5_rate
legacy_bad_path_rate
legacy_early_failure_rate
legacy_race_ambiguous_rate
```

Final report 必须明确说明：

```text
+10 before -5 is not the R04b primary metric.
```

## 9. Hard Gates 与 Final Decision

### 9.1 Minimum denominators

默认门槛：

```yaml
minimum_train_replay_complete_count: 500
minimum_validation_replay_complete_count: 300
minimum_robustness_replay_complete_count: 300
minimum_validation_hold120_max_gain50_count: 30
minimum_robustness_hold120_max_gain50_count: 30
max_censored_share: 0.25
```

低于门槛的 policy 只能 descriptive，不得 selected。

### 9.2 Train selection score

Train 内 family 参数选择使用：

```text
train_selection_score =
  z(net_return_mean_delta_vs_hold120)
  + z(left_tail_net_return_p10_delta_vs_hold120)
  + z(bad_path_loss_compression_vs_hold120)
  - z(avg_holding_days_increase_penalty)
```

Train z-score reference set 必须冻结：

```text
train_z_reference_set =
  rows in r04b_policy_matrix_frozen.csv
  where parameter_reference_group_id == current.parameter_reference_group_id
    and policy_family_id == current.policy_family_id
    and is_train_selectable == true
    and is_sensitivity_policy == false
    and invalid_policy_reason is null
```

`parameter_reference_group_id` 必须在 policy matrix 写出时冻结。runner 不得在看到 train metric 后动态改变 reference set，也不得把不同 `policy_family_id` 的参数混在同一个 train z-score reference set 中。若某个 metric 在 reference set 内标准差为 0，则该 metric 的 z-score 固定为 0。若某 parameter set 因 replay 不完整导致 selection metric 缺失，则该 parameter set 不得被 train 选中。

但如果：

```text
max_gain50_retention_vs_hold120 < 0.60
```

则该 parameter set 必须直接标记：

```text
failed_winner_retention_gate
```

不得被 train 选中。

### 9.3 Validation family selection

Validation family selection 必须满足所有 hard gates：

```text
validation_replay_complete_count >= minimum_validation_replay_complete_count
validation_hold120_max_gain50_count >= minimum_validation_hold120_max_gain50_count
validation_max_gain50_retention_vs_hold120 >= 0.60
validation_bad_path_loss_compression_vs_hold120 > 0
validation_left_tail_net_return_p10_delta_vs_hold120 >= 0
validation_net_return_mean_delta_vs_hold120 > 0
validation_censored_share <= max_censored_share
```

如果多个 family 通过，选择 validation score 最高者：

```text
validation_selection_score =
  z(net_return_mean_delta_vs_hold120)
  + z(left_tail_net_return_p10_delta_vs_hold120)
  + z(bad_path_loss_compression_vs_hold120)
  + z(max_gain50_retention_vs_hold120)
```

Validation z-score reference set 也必须冻结：

```text
validation_z_reference_set =
  one train-selected representative per policy_family_id
  where validation_family_reference_set_id == current.validation_family_reference_set_id
    and is_validation_selectable == true
    and is_sensitivity_policy == false
    and invalid_policy_reason is null
```

Validation 不得把未通过 train 参数选择的同 family 变体重新放回 reference set。

### 9.4 Robustness final readout

最终通过必须满足：

```text
robustness_replay_complete_count >= minimum_robustness_replay_complete_count
robustness_hold120_max_gain50_count >= minimum_robustness_hold120_max_gain50_count
robustness_max_gain50_retention_vs_hold120 >= 0.60
robustness_bad_path_loss_compression_vs_hold120 > 0
robustness_left_tail_net_return_p10_delta_vs_hold120 >= 0
robustness_net_return_mean_delta_vs_hold120 > 0
robustness_censored_share <= max_censored_share
```

如果 validation 通过但 robustness 失败，final decision 必须是：

```text
r04b_policy_not_robust_hold_exit_diagnostic_complete
```

不得用 pooled OOS 掩盖 robustness 失败。

### 9.5 Final decision precedence

Final decision 固定为：

```text
1. blocked_upstream_r04_validation_failed
2. blocked_missing_required_input
3. blocked_gate0_metric_replay_spec_failed
4. blocked_policy_matrix_invalid
5. blocked_selection_leakage_detected
6. r04b_no_policy_family_passed_validation
7. r04b_policy_not_robust_hold_exit_diagnostic_complete
8. r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only
```

即使 final decision 为：

```text
r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only
```

也只表示：

```text
fixed-entry policy replay diagnostic passed.
```

不得表示 production strategy ready。

## 10. Required Outputs

runner 必须写出：

```text
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/
  cache/
    r04b_candidate_replay_base_panel.parquet
    r04b_daily_policy_path_panel.parquet
    r04b_policy_replay_panel.parquet
    r04b_policy_selection_panel.parquet
    r04b_subgroup_interaction_panel.parquet
  reports/
    r04b_gate0_metric_replay_spec_frozen.csv
    r04b_input_reconciliation_audit.csv
    r04b_policy_matrix_frozen.csv
    r04b_policy_replay_summary.csv
    r04b_policy_vs_hold120_summary.csv
    r04b_policy_selection_trace.csv
    r04b_winner_retention_audit.csv
    r04b_bad_path_compression_audit.csv
    r04b_censored_replay_audit.csv
    r04b_market_industry_interaction_audit.csv
    r04b_year_instrument_concentration_audit.csv
    r04b_cost_turnover_audit.csv
    r04b_legacy_metric_audit.csv
    r04b_final_decision.csv
    r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md
  manifests/
    r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json
    r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json
```

### 10.1 `r04b_policy_replay_summary.csv`

必须包含每个 policy / split 的 headline metrics。

必需字段：

```text
policy_id
policy_family_id
hold_rule_id
exit_rule_id
sizing_rule_id
split
event_count
replay_complete_count
censored_count
replay_complete_rate
weighted_event_count
net_return_mean
net_return_median
net_return_p10
net_return_p90
net_return_mean_delta_vs_hold120
left_tail_net_return_p10_delta_vs_hold120
realized_loss_le_minus5_rate
realized_loss_le_minus10_rate
bad_path_loss_compression_vs_hold120
max_gain50_retention_vs_hold120
winner_exit_efficiency
avg_holding_days
turnover_proxy
denominator_status
winner_retention_status
```

### 10.2 `r04b_winner_retention_audit.csv`

必须包含：

```text
policy_id
split
hold120_max_gain50_count
policy_retained_max_gain50_count
max_gain50_retention_vs_hold120
wilson_lower
wilson_upper
first_plus50_hit_before_exit_count
exit_before_first_plus50_count
winner_exit_efficiency
retention_gate_threshold
retention_gate_pass
```

其中：

```text
retention_gate_threshold = 0.60
```

### 10.3 `r04b_market_industry_interaction_audit.csv`

必须按 policy / split / subgroup 输出：

```text
policy_id
split
interaction_dimension
interaction_value
event_count
replay_complete_count
net_return_mean_delta_vs_hold120
bad_path_loss_compression_vs_hold120
max_gain50_retention_vs_hold120
subgroup_denominator_status
top1_calendar_year_share
top1_instrument_share
research_lead_eligible_flag
research_lead_ineligible_reason
```

Interaction dimensions 至少包括：

```text
market_regime_bucket
industry_regime_bucket
market_regime_bucket x industry_regime_bucket
```

Report 必须明确：

```text
interaction audit is not entry selection.
```

Interaction subgroup 只有同时满足以下条件，才允许在 final report 中作为单独的后续研究线索点名：

```text
replay_complete_count >= 100
top1_calendar_year_share <= 0.50
subgroup_denominator_status == sufficient
```

否则只能保留在 audit CSV 中，不得在 final report 中写成 `promising lead`、`保留线索` 或类似表述。

### 10.4 `r04b_final_decision.csv`

必须包含：

```text
final_decision
selected_policy_id
selected_policy_family_id
validation_gate_pass
robustness_gate_pass
validation_max_gain50_retention_vs_hold120
robustness_max_gain50_retention_vs_hold120
validation_bad_path_loss_compression_vs_hold120
robustness_bad_path_loss_compression_vs_hold120
validation_net_return_mean_delta_vs_hold120
robustness_net_return_mean_delta_vs_hold120
decision_reason
```

## 11. Validator Requirements

Validator 必须输出：

```text
reports/r04b_fixed_entry_hold_exit_risk_budget_cta_validation_audit.csv
manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json
```

至少检查：

1. R04 upstream validation passed；
2. R04 candidate source hash 与 manifest 一致；
3. primary candidate pool 只来自 baseline_A included RPS episode-first-trigger rows；
4. mask_B / mask_C 没有进入主 pool；
5. Gate 0 spec 存在且 formula_hash 完整；
6. return / cost / censored / bad-path / retention 口径冻结；
7. `min_max_gain50_retention_vs_hold120 == 0.60`；
8. policy matrix 中每个 policy 有 formula_hash；
9. policy matrix 只包含 config 预注册 rule family；
10. CTA / trailing policy 被标为 exit_rule，不是独立 strategy track；
11. profit-lock invalid combination 不得作为 selectable policy；
12. activated ATR trailing (`min_activation_gain_pct > 0`) 只能是 sensitivity policy；
13. train z-score reference set 只在同一 `policy_family_id` / `parameter_reference_group_id` 内计算；
14. validation z-score reference set 只包含 train-selected family representatives；
15. max_gain50 flag / first hit / retention 使用 gross adjusted close path，不使用 net return；
16. train 只用于 family 内参数选择；
17. validation 只用于 family 选择；
18. robustness 未参与任何选择；
19. final selected policy 在 validation 和 robustness 均满足 retention gate；
20. final selected policy 在 validation 和 robustness 均满足 bad-path compression gate；
21. `+10 before -5` 未作为 primary metric 或 selection_metric；
22. market / industry fields 只出现在 interaction audit 或 sizing formula，不出现在 entry filter；
23. interaction research lead 必须满足 replay denominator 与 year concentration 门槛；
24. censored share 未超过 threshold；
25. winner denominator 足够；
26. output manifest 包含所有 required outputs 和 sha256；
27. final report 包含 mandatory boundary strings。

Mandatory boundary strings：

```text
R04b is fixed-entry policy replay, not entry eligibility.
CTA/trailing is an exit_rule family, not a separate strategy track.
Market and industry states are interaction diagnostics only, not selection gates.
+10 before -5 is legacy diagnostic only for R04b.
max_gain50_retention_vs_hold120 gate threshold = 0.60.
No production entry gate, sizing rule, or CTA strategy is emitted by this diagnostic.
```

## 12. Final Report Requirements

Final report 必须用中文写出，并至少回答：

1. 在 hold120 baseline 下，RPS pool 的 net return / bad path / max_gain50 右尾是什么？
2. 哪些 exit_rule family 在 train 中胜出，参数是什么？
3. 哪些 policy family 在 validation 中通过 hard gates？
4. final selected policy 在 robustness 中是否保持 bad-path compression？
5. final selected policy 是否满足 `max_gain50_retention_vs_hold120 >= 60%`？
6. CTA / trailing 是否真的优于 fixed_stop / time_stop / profit_lock 对照？
7. 改善是否主要来自降低左尾，而不是砍掉右尾？
8. market / industry subgroup 是否只影响 policy effectiveness，而没有变成 entry gate？
9. `downtrend_low_breadth` 与 `industry_lagging` 是否只是 interaction lead，还是出现了不应推广的小样本异常？
10. 是否值得进入下一版 R04c / production-like replay？

Final report 必须单独列出：

```text
winner_efficiency_status == insufficient_winner_denominator 的 policy / subgroup cell 占比
research_lead_eligible_flag == false 的 interaction cell 占比
```

不得只展示 denominator sufficient 的少数 cell 后宣称 subgroup 有稳定线索。

Report 不能出现：

```text
production ready
entry gate passed
market gate passed
industry gate passed
CTA strategy passed
```

除非明确否定这些说法。

## 13. Implementation Checklist

- [ ] R04 upstream validation passed.
- [ ] R04b uses baseline_A full RPS included pool as primary candidate pool.
- [ ] No mask_B / mask_C selected pool is used for primary replay.
- [ ] Gate 0 metric and replay semantics are frozen before policy replay.
- [ ] `+10 before -5` is legacy diagnostic only.
- [ ] `max_gain50_retention_vs_hold120 >= 0.60` is the v1 pass/fail threshold candidate.
- [ ] CTA / trailing is modeled as `exit_rule`, not as a separate strategy track.
- [ ] Policy matrix is finite and pre-registered.
- [ ] Train selects parameters only.
- [ ] Validation selects policy family only.
- [ ] Robustness is read-only.
- [ ] Market / industry states are interaction diagnostics only.
- [ ] Final report is Chinese and includes all mandatory boundary strings.

## 14. Out Of Scope

以下内容不属于 R04b v1：

```text
new entry anchor search
new RPS threshold search
market / industry entry gate promotion
volume_money entry gate
price extension entry gate
stock volatility entry gate
online data fetch
intraday stop primary execution
portfolio construction across simultaneous candidates
capital allocation optimization
production strategy emission
```

如果 R04b 通过，只允许进入下一版 requirement drafting，例如：

```text
R04c portfolio-level fixed-entry policy replay
R04c regime-aware risk-budget validation
R04c production-like cost / capacity / turnover audit
```

不得直接上线。
