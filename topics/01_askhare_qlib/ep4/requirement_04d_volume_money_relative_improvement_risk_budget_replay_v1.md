# EP4 需求 04d: Volume Money Relative-Improvement Pool Risk-Budget Replay V1

## 1. 需求元信息

- 需求 id: `ep4_r04d_volume_money_relative_improvement_risk_budget_replay_v1`
- 简称: `r04d_volume_money_relative_improvement_risk_budget_replay_v1`
- 状态: 首版可实现的单池 risk-budget replay 诊断需求
- 所属 workflow: EP4
- 上游 R04c 需求: `ep4/requirement_04c_candidate_pool_scanner_v1.md`
- 上游 R04c 输出根目录: `ep4/outputs/r04c_candidate_pool_scanner_v1/`
- 上游 R04b 需求: `ep4/requirement_04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.md`
- 上游 R04b 输出根目录: `ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/`
- 上游 R02 family precision 输出根目录: `ep4/outputs/r02_family_precision_forward_return_stats_v1/`
- 必需输出根目录: `ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/`
- 必需 config 路径: `ep4/configs/r04d_volume_money_relative_improvement_risk_budget_replay_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r04d_volume_money_relative_improvement_risk_budget_replay.py`
- 必需 validator 路径: `ep4/scripts/validate_r04d_volume_money_relative_improvement_risk_budget_replay.py`
- 日期: 2026-05-18

## 2. 背景与实验目的

R04c v1 的 final decision 是：

```text
r04c_no_candidate_pool_passed_validation
```

R04c v1 没有发现可以直接升级为 R04b-style replay 主池的 candidate pool。这个结论不能被回填或改写。

但 R04c 同时暴露了一个强 descriptive lead：`r02_precision_volume_money`。

它在 validation split 的 hold120 no-exit profile 是：

| 指标 | 数值 |
|---|---:|
| replay_complete_count | 1,568 |
| censored_share | 24.40% |
| net_return_mean | -2.07% |
| net_return_mean_delta_vs_matched_baseline_A | +4.53% |
| p10_delta_vs_matched_baseline_A | +3.03% |
| loss_le_minus5_delta_vs_matched_baseline_A | -10.84% |
| max_gain50_count | 94 |
| max_gain50_rate | 5.99% |
| matched_baseline_max_gain50_rate | 5.84% |
| matched_comparator_effective_sample_size | 2,999.5 |
| overlap_with_baseline_A_share | 21.12% |
| pool_unique_event_share | 78.88% |

它在 robustness split 的 descriptive readout 是：

| 指标 | 数值 |
|---|---:|
| replay_complete_count | 1,553 |
| censored_share | 29.31% |
| net_return_mean | +7.82% |
| net_return_mean_delta_vs_matched_baseline_A | +0.85% |
| p10_delta_vs_matched_baseline_A | +2.24% |
| loss_le_minus5_delta_vs_matched_baseline_A | -6.11% |
| max_gain50_rate | 10.17% |
| matched_baseline_max_gain50_rate | 11.46% |
| matched_comparator_effective_sample_size | 2,423.2 |

因此 R04d 不问：

```text
volume_money 是否已经通过 R04c？
```

答案是否定的。

R04d 只问一个新问题：

```text
一个 validation 中相对少亏、左尾改善、且主要由新事件构成的 fixed pool，
能否通过简单的 risk-budget / shorter-hold / break-even replay，
把相对改善转化为 OOS 正期望？
```

R04d 的关键词是：

```text
relative-improvement pool + risk-budget replay diagnostic
```

不是：

```text
R04c passed pool
R04b continuation
CTA strategy
production entry rule
```

## 3. R04d 要回答的问题

R04d 必须回答：

1. 固定 `r02_precision_volume_money` pool 后，shorter hold / break-even / time-stop 是否能把 validation net mean 从 `-2.07%` 推到 `> 0`？
2. 改善是否来自左尾压缩，而不是只来自减少 holding days 后丢掉亏损样本？
3. 改善是否同时出现在 validation 与 robustness，而不是只修复 validation？
4. selected policy 在 robustness 中是否至少保持高于 R04c baseline_A robustness net mean `6.12%`？
5. selected policy 相对 volume_money hold120 no-exit 的 robustness net delta 是否为正？如果不是，是否仍可作为 validation-only insurance lead？
6. shorter hold / break-even 是否过度牺牲 `max_gain50` 右尾？
7. censored_share 是否从 volume_money hold120 的 validation `24.40%` 和 robustness `29.31%` 得到改善？
8. 是否存在简单 policy family 足够解释改善，还是需要复杂 CTA/trailing？
9. 是否值得后续进入 portfolio-level union pool 或 volume_money v2 anchor 研究？

## 4. Non-Negotiables

### 4.1 R04d 不改变 R04c v1 结论

R04d 必须在 final report 中写明：

```text
R04d does not reinterpret R04c v1 as passed.
volume_money is a descriptive relative-improvement lead, not an R04c selected pool.
```

禁止写：

```text
volume_money passed R04c
R04c selected volume_money
R04d is R04c robustness continuation
```

### 4.2 Pool 固定，不允许重选

R04d 的唯一主池固定为：

```text
pool_id = r02_precision_volume_money
adapter_id = r02_family_precision_frozen_family_occurrence
```

pool membership 权威定义来自 R02 family precision action-time panel：

```text
source_artifact = ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet
family_id == volume_money
signal_occurs == true
feature_complete_flag == true
base_action_time_eligible_flag == true
episode_gap_trading_days = 20
anchor_signal_date = first trade_date in collapsed episode
entry = first executable next-open after anchor_signal_date
```

R04c cache 可以用于 reconciliation，但不得作为唯一 membership authority。

禁止：

```text
把 range_breakout / pullback_drawdown 加入主池
用 validation 或 robustness 表现改 pool threshold
按 market / industry / RPS 再筛 volume_money pool
用 R04d replay 结果反向删除 volume_money 子样本
```

### 4.3 Policy 搜索必须简化

R04d v1 只允许 primary selection 使用：

```text
no_exit
time_stop
break_even_after_gain
fixed_stop
fixed_size
volatility_scaled
```

其中重点 family 是：

```text
time_stop
break_even_after_gain
```

R04d v1 禁止 primary selection 使用：

```text
ATR trailing
EMA trailing
CTA / trend-following trailing
profit_lock_after_gain
market_state_scaled entry/block gate
industry_state_scaled entry/block gate
```

如需输出 ATR/EMA/CTA，只能作为 future-work placeholder，不得运行、不得 selected、不得进入 final decision。

### 4.4 Validation 选 policy，robustness 只读

R04d lifecycle 固定为：

```text
train: policy parameter selection only
validation: policy family / selected_policy_id freeze
robustness: final readout only
```

robustness 不得：

```text
更换 selected_policy_id
更换 pool
更换参数
决定是否加入新 policy family
```

### 4.5 Baseline comparator 必须分层

所有 policy 必须同时比较：

```text
volume_money_hold120_no_exit_fixed_size
baseline_A_r04c_hold120_no_exit_fixed_size
matched_baseline_A
```

主 gate 使用 `volume_money_hold120_no_exit_fixed_size` 作为直接 policy baseline，同时报告相对 `baseline_A` 和 `matched_baseline_A` 的改善。

三层 comparator 口径必须冻结为：

```text
volume_money_hold120_no_exit_fixed_size:
  same reconstructed volume_money pool
  hold_120d + no_exit + fixed_size
  replayed by R04d price / cost / sizing semantics
  used by primary gates

baseline_A_r04c_hold120_no_exit_fixed_size:
  R04c baseline_A hold120 no-exit fixed-size profile
  used as absolute context and robustness floor
  not a same-policy comparator

matched_baseline_A:
  R04c matched baseline event panel replayed under the same R04d policy_id
  used for same-policy matched deltas
  not used for train / validation / robustness selection gates
```

`net_return_mean_delta_vs_matched_baseline_A`、`p10_delta_vs_matched_baseline_A`、`loss_le_minus5_delta_vs_matched_baseline_A` 必须来自同一 `policy_id` 在 volume_money pool 与 matched baseline_A panel 上的 replay 差值。R04c report 中的 hold120 matched delta 只能作为 upstream context，不得直接套用到 non-hold120 policy。

## 5. 必需输入

R04d 必须加载并校验：

```text
ep4/outputs/r04c_candidate_pool_scanner_v1/manifests/r04c_candidate_pool_scanner_validation.json
ep4/outputs/r04c_candidate_pool_scanner_v1/manifests/r04c_candidate_pool_scanner_manifest.json
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_final_decision.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_validation_gate_audit.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_hold120_pool_profile.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_matched_baseline_delta_summary.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_overlap_uniqueness_audit.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_pool_registry_frozen.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/cache/r04c_pool_event_panel.parquet
ep4/outputs/r04c_candidate_pool_scanner_v1/cache/r04c_matched_baseline_panel.parquet

ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet

ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json

data/qlib/cn_data_pit/calendars/day.txt
data/qlib/cn_data_pit/features/*/{open,high,low,close,volume,money,factor}.day.bin
data/qlib/cn_data_pit/instruments/*.txt
```

R04c validation status 必须为 `passed`，且 R04c final decision 必须保持：

```text
r04c_no_candidate_pool_passed_validation
```

这不是为了要求失败，而是为了防止 R04d 被误写成 R04c passed continuation。

如果 R04c final decision 已经不同，R04d 必须 fail closed：

```text
blocked_upstream_r04c_state_changed
```

## 6. Pool Reconstruction

R04d 必须重建 `r02_precision_volume_money` pool，并与 R04c 输出 reconciliation。

必需 reconciliation 字段：

```text
r04d_reconstructed_event_count
r04c_volume_money_event_count
overlap_event_count
overlap_share_vs_r04d
overlap_share_vs_r04c
anchor_date_mismatch_count
entry_date_mismatch_count
entry_price_rel_diff_p95
entry_price_rel_diff_max
reconciliation_status
```

通过条件：

```text
overlap_share_vs_r04d >= 0.99
overlap_share_vs_r04c >= 0.99
entry_price_rel_diff_p95 <= 0.0001
```

R04c cache 是 reconciliation 与 same-policy matched comparator 的必需输入。如果 `r04c_pool_event_panel.parquet` 或 `r04c_matched_baseline_panel.parquet` 缺失，R04d 必须 fail closed：

```text
blocked_missing_required_input
```

R04d 仍必须以 R02 panel 作为 volume_money membership authority；R04c cache 只用于 reconciliation 和 matched baseline comparator，不得反过来定义主池 membership。

## 7. Policy Matrix

### 7.1 Entry

Entry 固定为：

```text
entry_execution_date = first executable next-open after anchor_signal_date
entry_price = adjusted_open(entry_execution_date)
```

不得在 entry 上加入额外 allow/block。

### 7.2 Hold rules

R04d v1 policy matrix 必须包含：

```text
hold_20d
hold_40d
hold_60d
hold_120d
```

`hold_120d + no_exit + fixed_size` 是 volume_money policy baseline。

### 7.3 Exit rules

Primary selectable exit families：

```text
no_exit
time_stop
break_even_after_gain
fixed_stop
```

默认参数：

```yaml
time_stop_days: [10, 20, 40, 60]
break_even_after_gain:
  activation_gain_pct: [0.08, 0.10, 0.15]
fixed_stop:
  stop_loss_pct: [-0.05, -0.08, -0.10]
```

约束：

```text
time_stop_days < hold_rule_max_days
break_even exit only after activation_gain_pct is reached
fixed_stop uses close-based signal, next-open execution
```

Exit execution 必须沿用 R04b offset 语义：

```text
entry_execution_date open = offset 0 entry execution
day N close = trading-day offset N close after entry execution
exit_signal_date = first close-based date whose policy condition is true
exit_execution_date = first executable open after exit_signal_date
```

各 exit rule 的冻结语义：

```text
no_exit:
  exit_signal_date = close at hold_rule_max_days

time_stop:
  exit_signal_date = close at time_stop_days
  invalid if time_stop_days >= hold_rule_max_days

fixed_stop:
  exit if close_return_from_entry <= stop_loss_pct
  else exit at hold_rule_max_days

break_even_after_gain:
  inactive before close_return_from_entry >= activation_gain_pct
  after activation, exit if close_return_from_entry <= 0
  else exit at hold_rule_max_days
```

Invalid `time_stop_days >= hold_rule_max_days` 组合不得 selectable。若两个 policy 行为完全等价，runner 必须保留一个 canonical selectable row，并在 `duplicate_policy_group_id` 中标记重复行；重复行不得参与 train / validation selection。

### 7.4 Sizing rules

Primary selectable sizing：

```text
fixed_size
volatility_scaled
```

默认 volatility_scaled：

```yaml
target_vol: 0.02
min_weight: 0.25
max_weight: 1.00
```

`volatility_scaled` 是 risk-budget 维度，不是 entry gate。它不得把任何 event 从 pool 中删除。

`volatility_scaled` 单点冻结为：

```text
stock_realized_vol_20d_asof_entry =
  standard deviation of simple adjusted close returns over the 20 complete
  trading days before entry_execution_date, not annualized

position_weight =
  clip(target_vol / stock_realized_vol_20d_asof_entry, min_weight, max_weight)
```

缺少 20 个有效 pre-entry close return 时，`volatility_scaled` policy 必须标记为 `censored_by_missing_required_indicator`；`fixed_size` policy 不得因此被 censored。

### 7.5 禁止的 v1 policy

R04d v1 不运行：

```text
ATR_trailing
EMA_trailing
CTA
profit_lock_after_gain
market_state_scaled
industry_state_scaled
```

原因：本实验先检验最简单的 shorter hold / break-even 能否解决 `-2.07%` validation net，而不是扩大自由度。

## 8. Replay 口径

Replay 必须复用 R04b/R04c price-provider 语义：

```text
provider_uri = data/qlib/cn_data_pit
feature expressions = $open/$high/$low/$close/$volume/$money/$factor
output schema = adjusted_open/adjusted_high/adjusted_low/adjusted_close/volume/money/factor
dirty bar logic = R04b suspended_or_dirty_bar 判定
execution_policy = close_signal_next_open
```

成本模型沿用 R04b：

```yaml
cost_model:
  cost_model_id: a_share_daily_replay_default_v1
  entry_slippage_bps: 5.0
  exit_slippage_bps: 5.0
  commission_bps_per_side: 3.0
  stamp_tax_bps_on_exit: 5.0
  min_fee_policy: none
```

主收益：

```text
gross_return = exit_price / entry_price - 1
unweighted_net_return = gross_return - entry_cost - exit_cost
weighted_net_return = position_weight * unweighted_net_return
net_return = weighted_net_return
```

`net_return_*`、`loss_le_minus5_rate`、`loss_le_minus10_rate` 和所有 selection / gate 默认使用 `weighted_net_return` 聚合。runner 必须同时保留 `unweighted_net_return`，用于解释 sizing 是否只是通过降仓位改善 headline 指标。

`max_gain50`、`max_gain50_retention` 和 path quality 使用 gross adjusted close path，不扣成本、不乘 `position_weight`。

### 8.1 max_gain50 retention 口径

R04d 的右尾保护约束以 `volume_money_hold120_no_exit_fixed_size` 为对照。

先在 volume_money hold120 no-exit fixed-size baseline 上定义：

```text
volume_money_hold120_max_gain50_flag =
  gross_max_adjusted_close_return_from_entry_to_day120 >= 0.50
```

其中 day120 窗口固定为：

```text
gross adjusted close return from offset 0 close through offset 120 close,
measured against adjusted entry open price
```

对每个 policy 定义：

```text
policy_retained_max_gain50_flag =
  volume_money_hold120_max_gain50_flag == true
  AND policy_exit_execution_date > volume_money_hold120_first_plus50_hit_date
```

`volume_money_hold120_first_plus50_hit_date` 必须由同一条 gross adjusted close path 计算。这里必须使用 `>`，不能使用 `>=`；如果 policy 在首次 +50% 命中日的 open 已经离场，则不能视为保留了当天 close 才出现的 +50% winner。

主保留率定义为：

```text
max_gain50_retention_vs_volume_money_hold120 =
  sum(policy_retained_max_gain50_flag)
  / sum(volume_money_hold120_max_gain50_flag)
```

该指标必须按 split 单独计算。`net_return`、成本、slippage、`position_weight` 均不得进入 retention 判定。

## 9. Metrics

每个 `policy_id x split` 必须输出：

```text
event_count
replay_complete_count
censored_count
censored_share
net_return_mean
net_return_median
net_return_p10
net_return_p25
net_return_p75
net_return_p90
unweighted_net_return_mean
unweighted_net_return_p10
weighted_net_return_mean
weighted_net_return_p10
loss_le_minus5_rate
loss_le_minus10_rate
max_drawdown_p50
max_drawdown_p90
max_gain50_count
max_gain50_rate
max_gain50_retention_vs_volume_money_hold120
avg_holding_days
position_weight_mean
position_weight_p10
turnover_proxy
cost_bps_mean
net_return_metric_basis
```

同时输出 deltas：

```text
net_return_mean_delta_vs_volume_money_hold120
p10_delta_vs_volume_money_hold120
loss_le_minus5_delta_vs_volume_money_hold120
max_gain50_rate_delta_vs_volume_money_hold120

net_return_mean_delta_vs_baseline_A
net_return_mean_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
matched_comparator_status
matched_comparator_effective_sample_size
```

## 10. Gate 与阈值

### 10.1 Minimum denominator

默认：

```yaml
minimum_train_replay_complete_count: 1000
minimum_validation_replay_complete_count: 1000
minimum_robustness_replay_complete_count: 1000
max_validation_censored_share: 0.25
max_robustness_censored_share: 0.25
minimum_validation_max_gain50_count: 50
minimum_robustness_max_gain50_count: 50
```

注意：volume_money hold120 validation `censored_share = 24.40%`，robustness `29.31%`。R04d v1 的 selected policy 必须在 validation 和 robustness 都满足 `censored_share <= 25%`。这是一条绝对可交易完整性门槛，对 robustness 明确要求相对 hold120 得到改善；不得解释成“只要不恶化即可”。

### 10.2 Train selection score

Train 只用于参数选择。默认：

```text
train_policy_score =
  z(net_return_mean_delta_vs_volume_money_hold120)
  + z(p10_delta_vs_volume_money_hold120)
  - z(loss_le_minus5_delta_vs_volume_money_hold120)
  - 0.5 * z(avg_holding_days)
  - winner_retention_penalty
```

其中：

```text
winner_retention_penalty =
  max(0, 0.50 - max_gain50_retention_vs_volume_money_hold120)
```

z-score reference set 必须在同一 `policy_family_id` 内计算。

z-score reference set 只包含同一 `policy_family_id` 内 `is_train_selectable == true` 且 train denominator sufficient 的 rows。若某一项在 reference set 内标准差为 0，则该项 z-score 固定为 0，不得动态换 reference set。

### 10.3 Validation hard gates

Train-selected policy 必须在 validation 同时满足：

```text
replay_complete_count >= minimum_validation_replay_complete_count
censored_share <= max_validation_censored_share
net_return_mean > 0
net_return_mean_delta_vs_volume_money_hold120 >= 0.02
p10_delta_vs_volume_money_hold120 >= 0
loss_le_minus5_delta_vs_volume_money_hold120 < 0
max_gain50_count >= minimum_validation_max_gain50_count
max_gain50_retention_vs_volume_money_hold120 >= 0.50
```

解释：

```text
validation net > 0 是 R04d 的核心问题：risk-budget 是否能把 volume_money 从 -2.07% 推到正收益。
delta_vs_volume_money_hold120 >= 2pct 确保不是微小噪声。
retention >= 50% 是候选门槛，不是 production 门槛。
```

### 10.4 Robustness final readout gates

Validation-selected policy 在 robustness 必须满足：

```text
replay_complete_count >= minimum_robustness_replay_complete_count
censored_share <= max_robustness_censored_share
net_return_mean > baseline_A_robustness_net_return_mean
net_return_mean_delta_vs_volume_money_hold120 >= -0.01
p10_delta_vs_volume_money_hold120 >= 0
loss_le_minus5_delta_vs_volume_money_hold120 <= 0
max_gain50_count >= minimum_robustness_max_gain50_count
max_gain50_retention_vs_volume_money_hold120 >= 0.50
```

其中：

```text
baseline_A_robustness_net_return_mean = R04c baseline_A robustness net_return_mean
```

当前参考值是：

```text
baseline_A_robustness_net_return_mean = 6.12%
```

如果 robustness 同时满足：

```text
net_return_mean_delta_vs_volume_money_hold120 > 0
```

则标记：

```text
robustness_relative_improvement_status = strong_pass
```

如果 robustness 只满足：

```text
net_return_mean > baseline_A_robustness_net_return_mean
net_return_mean_delta_vs_volume_money_hold120 >= -0.01
```

则标记：

```text
robustness_relative_improvement_status = insurance_pass_not_pool_improving
```

这种结果只能说明 risk-budget 没有明显破坏 robustness，不代表 policy 优于 volume_money no-exit。

## 11. Selection Lifecycle

### 11.1 Stage 0: Upstream validation

检查：

```text
R04c validation_status == passed
R04b validation_status == passed
R04c final_decision == r04c_no_candidate_pool_passed_validation
R04c volume_money validation row exists
```

### 11.2 Stage 1: Pool reconstruction

重建 volume_money pool，输出：

```text
r04d_volume_money_pool_reconstruction_audit.csv
r04d_volume_money_pool_event_panel.parquet
```

### 11.3 Stage 2: Policy matrix freeze

输出：

```text
r04d_policy_matrix_frozen.csv
```

所有 policy 必须在 replay 前冻结。

### 11.4 Stage 3: Train parameter selection

输出：

```text
r04d_train_policy_selection_trace.csv
```

Train 只能选择同 family 内参数，不得选择 pool。

### 11.5 Stage 4: Validation policy selection

输出：

```text
r04d_validation_gate_audit.csv
```

Validation 冻结唯一：

```text
selected_policy_id
```

如果没有 policy 通过 validation hard gates：

```text
final_decision = r04d_no_policy_passed_validation
```

### 11.6 Stage 5: Robustness readout

输出：

```text
r04d_robustness_readout.csv
```

Robustness 只能评估 validation-frozen `selected_policy_id`。

## 12. Final Decision

允许的 final decision：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_upstream_r04c_state_changed
blocked_pool_reconstruction_failed
blocked_gate0_metric_replay_spec_failed
blocked_policy_matrix_invalid
blocked_selection_leakage_detected
r04d_no_policy_passed_validation
r04d_policy_validation_only_not_robust
r04d_policy_passed_relative_improvement_diagnostic_only
r04d_policy_strong_pass_diagnostic_only
```

决策优先级：

1. 必需输入缺失 -> `blocked_missing_required_input`
2. R04c / R04b validation 未通过 -> `blocked_upstream_validation_failed`
3. R04c final decision 不再是 `r04c_no_candidate_pool_passed_validation` -> `blocked_upstream_r04c_state_changed`
4. volume_money pool 无法重建或 reconciliation 失败 -> `blocked_pool_reconstruction_failed`
5. Gate0 formula / replay spec 未冻结或 hash 不一致 -> `blocked_gate0_metric_replay_spec_failed`
6. policy matrix 无法冻结或包含 forbidden family -> `blocked_policy_matrix_invalid`
7. 发现 train/validation/robustness selection leakage -> `blocked_selection_leakage_detected`
8. 无 policy 通过 validation -> `r04d_no_policy_passed_validation`
9. validation-selected policy robustness gate 失败 -> `r04d_policy_validation_only_not_robust`
10. robustness 通过但 `net_return_mean_delta_vs_volume_money_hold120 <= 0` -> `r04d_policy_passed_relative_improvement_diagnostic_only`
11. robustness 通过且 `net_return_mean_delta_vs_volume_money_hold120 > 0` -> `r04d_policy_strong_pass_diagnostic_only`

即使 strong pass，也只能写：

```text
volume_money relative-improvement risk-budget diagnostic passed;
eligible for future portfolio-level confirmation.
```

不得写：

```text
production ready
R04c passed
entry rule approved
CTA strategy passed
```

## 13. 必需输出

runner 必须写出：

```text
ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/
  cache/
    r04d_volume_money_pool_event_panel.parquet
    r04d_daily_policy_path_panel.parquet
    r04d_policy_replay_panel.parquet
    r04d_policy_selection_panel.parquet
  reports/
    r04d_upstream_state_audit.csv
    r04d_gate0_metric_replay_spec_frozen.csv
    r04d_volume_money_pool_reconstruction_audit.csv
    r04d_policy_matrix_frozen.csv
    r04d_policy_duplicate_audit.csv
    r04d_policy_replay_summary.csv
    r04d_matched_baseline_policy_replay_summary.csv
    r04d_policy_vs_volume_money_hold120_summary.csv
    r04d_train_policy_selection_trace.csv
    r04d_validation_gate_audit.csv
    r04d_robustness_readout.csv
    r04d_winner_retention_audit.csv
    r04d_censored_replay_audit.csv
    r04d_cost_turnover_audit.csv
    r04d_final_decision.csv
    r04d_volume_money_relative_improvement_risk_budget_final_report.md
    r04d_volume_money_relative_improvement_risk_budget_validation_audit.csv
  manifests/
    r04d_volume_money_relative_improvement_risk_budget_manifest.json
    r04d_volume_money_relative_improvement_risk_budget_validation.json
```

Cache parquet 可被 `.gitignore` 忽略；reports 和 manifests 是可追踪审计产物。

## 14. Schema 要求

### 14.1 `r04d_policy_replay_summary.csv`

字段至少包含：

```text
policy_id
policy_family_id
hold_rule_id
exit_rule_family_id
sizing_rule_id
parameter_set_id
parameter_values_json
split
event_count
replay_complete_count
censored_share
net_return_mean
net_return_p10
unweighted_net_return_mean
unweighted_net_return_p10
weighted_net_return_mean
weighted_net_return_p10
position_weight_mean
position_weight_p10
loss_le_minus5_rate
loss_le_minus10_rate
max_gain50_count
max_gain50_rate
max_gain50_retention_vs_volume_money_hold120
avg_holding_days
net_return_mean_delta_vs_volume_money_hold120
p10_delta_vs_volume_money_hold120
loss_le_minus5_delta_vs_volume_money_hold120
net_return_mean_delta_vs_baseline_A
net_return_mean_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
matched_comparator_status
matched_comparator_effective_sample_size
net_return_metric_basis
winner_retention_status
denominator_status
```

### 14.2 `r04d_validation_gate_audit.csv`

字段至少包含：

```text
policy_id
policy_family_id
split
validation_gate_pass
validation_selection_score
validation_selected_rank
replay_complete_count
censored_share
max_allowed_censored_share
net_return_mean
net_return_metric_basis
net_return_mean_delta_vs_volume_money_hold120
p10_delta_vs_volume_money_hold120
loss_le_minus5_delta_vs_volume_money_hold120
max_gain50_count
max_gain50_retention_vs_volume_money_hold120
failed_gate_list
selected_policy_id
selected_flag
```

### 14.3 `r04d_final_decision.csv`

字段至少包含：

```text
final_decision
selected_policy_id
selected_policy_family_id
selected_hold_rule_id
selected_exit_rule_family_id
selected_sizing_rule_id
validation_gate_pass
robustness_gate_pass
robustness_relative_improvement_status
net_return_metric_basis
validation_net_return_mean
robustness_net_return_mean
validation_censored_share
robustness_censored_share
validation_net_return_mean_delta_vs_volume_money_hold120
robustness_net_return_mean_delta_vs_volume_money_hold120
validation_p10_delta_vs_volume_money_hold120
robustness_p10_delta_vs_volume_money_hold120
validation_loss_le_minus5_delta_vs_volume_money_hold120
robustness_loss_le_minus5_delta_vs_volume_money_hold120
validation_max_gain50_retention_vs_volume_money_hold120
robustness_max_gain50_retention_vs_volume_money_hold120
decision_reason
```

### 14.4 `r04d_policy_matrix_frozen.csv`

字段至少包含：

```text
policy_id
policy_family_id
hold_rule_id
hold_rule_max_days
exit_rule_family_id
sizing_rule_id
parameter_set_id
parameter_values_json
is_train_selectable
is_validation_selectable
invalid_policy_reason
duplicate_policy_group_id
canonical_policy_id
formula_hash
```

`is_train_selectable == true` 的 row 不得有 `invalid_policy_reason`，也不得是非 canonical duplicate row。

### 14.5 `r04d_matched_baseline_policy_replay_summary.csv`

字段至少包含：

```text
policy_id
split
volume_money_replay_complete_count
matched_baseline_replay_complete_count
matched_comparator_effective_sample_size
volume_money_net_return_mean
matched_baseline_net_return_mean
net_return_mean_delta_vs_matched_baseline_A
volume_money_net_return_p10
matched_baseline_net_return_p10
p10_delta_vs_matched_baseline_A
volume_money_loss_le_minus5_rate
matched_baseline_loss_le_minus5_rate
loss_le_minus5_delta_vs_matched_baseline_A
matched_comparator_status
```

该表必须由同一 `policy_id` 的 volume_money replay 与 matched baseline_A replay 生成，不得使用 R04c hold120 summary 直接填充。

### 14.6 `r04d_gate0_metric_replay_spec_frozen.csv`

字段至少包含：

```text
spec_section
spec_item
frozen_value_json
formula_text
source_config_key
formula_hash
```

该表必须覆盖 return、cost、sizing、execution offset、censored status、matched comparator、max_gain50 retention、baseline delta、gate threshold 与 selection score。

## 15. Validator Requirements

Validator 必须检查：

1. R04c validation status 为 `passed`。
2. R04b validation status 为 `passed`。
3. R04c final decision 仍为 `r04c_no_candidate_pool_passed_validation`。
4. 所有必需 cache / reports / manifests 存在。
5. 所有 cache/reports/manifests 路径写入 manifest。
6. volume_money pool reconstruction audit 通过。
7. policy matrix 在 replay 前冻结，且 `formula_hash` 完整。
8. policy matrix 不包含 forbidden families: `ATR_trailing`, `EMA_trailing`, `CTA`, `profit_lock_after_gain`, `market_state_scaled`, `industry_state_scaled`。
9. `r04d_gate0_metric_replay_spec_frozen.csv` 必须写出 return / cost / sizing / matched comparator / retention / censored / gate threshold 的 formula hash。
10. `net_return_metric_basis == weighted_net_return`，且 replay panel 同时保留 `unweighted_net_return` 与 `weighted_net_return`。
11. `volatility_scaled` 不得删除 event，只能改变 `position_weight`；缺少 20 日 as-of vol 的样本只能进入 `censored_by_missing_required_indicator`。
12. `matched_baseline_A` delta 必须来自同一 `policy_id` 在 matched baseline panel 上的 replay，不得复用 R04c hold120 matched delta。
13. `max_gain50_retention_vs_volume_money_hold120` 必须使用 gross adjusted close path 和 volume_money hold120 denominator，不得使用 net return 或 position weight。
14. invalid `time_stop_days >= hold_rule_max_days` 不得 train / validation selectable。
15. duplicate equivalent policy rows 不得同时 train / validation selectable。
16. train selection trace 的 `split_used` 只能是 `train`。
17. validation gate audit 的 input policy 必须来自 train-selected parameter set。
18. validation gate audit 必须冻结唯一 `selected_policy_id`，且 selected rank == 1 among validation-passed policies。
19. robustness 不得出现在 selection trace 的 `split_used` 中。
20. robustness readout 不得改变 validation-frozen `selected_policy_id`。
21. validation gate failed 的 policy 不得 selected。
22. robustness gate failed 时 final decision 不得为 passed。
23. selected policy 必须满足 split-specific censored gate: validation <= 25%，robustness <= 25%。
24. z-score zero-std 项必须按 0 处理，reference set 不得动态切换。
25. report 必须包含 mandatory boundary strings。

Mandatory boundary strings：

```text
R04d does not reinterpret R04c v1 as passed.
volume_money is a descriptive relative-improvement lead, not an R04c selected pool.
R04d uses a fixed r02_precision_volume_money pool.
R04d primary policies are shorter hold, time_stop, break_even, fixed_stop, and sizing only.
Robustness is final readout only.
Headline net_return metrics use weighted_net_return; unweighted returns are audit only.
No production entry rule is emitted by this diagnostic.
```

## 16. Final Report Requirements

Final report 必须用中文写出，并至少回答：

1. R04d 为什么不是 R04c passed continuation？
2. volume_money hold120 no-exit 在 train / validation / robustness 的 profile 是什么？
3. pool reconstruction 是否和 R04c volume_money 一致？
4. policy matrix 包含哪些 hold / exit / sizing families？
5. train 选出了哪些 parameter set？
6. validation 是否有 policy 把 net mean 从 `-2.07%` 推到 `> 0`？
7. selected policy 的 headline 改善有多少来自 `weighted_net_return`，unweighted audit 是否同向？
8. selected policy 的 left-tail improvement 是否来自 p10 上移和 loss<=-5 降低？
9. selected policy 的 same-policy matched baseline delta 是否仍为正？
10. selected policy 是否过度牺牲 +50 winner retention？
11. robustness 是否高于 baseline_A robustness `6.12%`？
12. robustness 是否也优于 volume_money hold120 no-exit？
13. time_stop / break_even 哪类 family 更有解释力？
14. 是否值得进入 portfolio-level union pool 或 R04e？

Final report 必须单独列出：

```text
validation net > 0 policies
validation passed but robustness failed policies
robustness strong_pass policies
winner retention < 50% policies
censored_share > 25% policies
weighted-pass but unweighted-fail policies
matched_baseline_A same-policy delta <= 0 policies
```

## 17. Implementation Checklist

- [ ] R04c validation passed.
- [ ] R04b validation passed.
- [ ] R04c final decision 未被改写。
- [ ] volume_money pool reconstruction 完成。
- [ ] R04c cache 必需输入存在，reconciliation 完成。
- [ ] Gate0 formula / replay spec 已冻结并 hash 校验通过。
- [ ] policy matrix 在 replay 前冻结。
- [ ] invalid / duplicate policy row 不参与 train / validation selection。
- [ ] primary policy family 只包含 no_exit / time_stop / break_even / fixed_stop。
- [ ] sizing 只包含 fixed_size / volatility_scaled。
- [ ] headline net_return 使用 weighted_net_return，并输出 unweighted audit。
- [ ] matched_baseline_A 使用 same-policy replay delta。
- [ ] Train 只做参数选择。
- [ ] Validation 冻结唯一 selected_policy_id。
- [ ] Robustness 只读，不参与选择。
- [ ] selected policy 的 validation net > 0。
- [ ] selected policy 的 validation delta vs volume_money hold120 >= 2pct。
- [ ] selected policy 的 robustness net > baseline_A robustness net。
- [ ] max_gain50 retention guardrail 输出。
- [ ] censored replay audit 输出。
- [ ] final report 用中文回答 Section 16 的问题。
- [ ] validator 输出 `validation_status: passed` 后，才可讨论是否进入后续研究。
