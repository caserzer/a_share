# EP4 需求 04e: Union Pool Portfolio-Level Diagnostic V1

## 1. 需求元信息

- 需求 id: `ep4_r04e_union_pool_portfolio_level_diagnostic_v1`
- 简称: `r04e_union_pool_portfolio_level_diagnostic_v1`
- 状态: 首版可实现的 union pool / portfolio-level 诊断需求
- 所属 workflow: EP4
- 上游 R04c 需求: `ep4/requirement_04c_candidate_pool_scanner_v1.md`
- 上游 R04c 输出根目录: `ep4/outputs/r04c_candidate_pool_scanner_v1/`
- 上游 R04d 需求: `ep4/requirement_04d_volume_money_relative_improvement_risk_budget_replay_v1.md`
- 上游 R04d 输出根目录: `ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/`
- 上游 R02 family precision 输出根目录: `ep4/outputs/r02_family_precision_forward_return_stats_v1/`
- 必需输出根目录: `ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r04e_union_pool_portfolio_level_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r04e_union_pool_portfolio_level_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r04e_union_pool_portfolio_level_diagnostic.py`
- 日期: 2026-05-19

## 2. 背景与实验目的

R04c v1 的 final decision 是：

```text
r04c_no_candidate_pool_passed_validation
```

R04d v1 的 final decision 是：

```text
r04d_no_policy_passed_validation
```

这两个结论都不能被 R04e 回填或改写。R04e 不是：

```text
R04c passed pool continuation
R04d v2
volume_money retry
exit-policy parameter expansion
production entry rule
```

R04c 和 R04d 共同留下的正向线索是：

1. R02 family pools 在 validation 中没有绝对转正，但相对 matched baseline_A 有稳定左尾改善。
2. `volume_money` 单池 R04d replay 证明 simple risk-budget 能压左尾，但单池不能同时满足正收益和右尾保留。
3. 三个 R02 family pools 与 baseline_A overlap 较低，可能代表不同事件 universe，而不是 baseline_A 的窄子集。

R04e 因此问一个新问题：

```text
把 volume_money / range_breakout / pullback_drawdown 三个 relative-improvement pools
冻结合并为 union pool 后，是否能通过事件分散和组合层聚合，
把 validation 的相对少亏转化为 portfolio-level 正期望或更低左尾？
```

R04e 的关键词是：

```text
frozen union pool + pseudo-diversification audit + portfolio-level diagnostic
```

不是：

```text
single-pool exit tuning
new CTA / trailing search
post-hoc validation gate rewrite
```

## 3. 上游 descriptive leads

R04e 固定使用 R04c v1 中三个 OOS matched delta 正向的 R02 family pools：

| pool_id | validation complete | validation net | validation matched delta | validation p10 delta | validation loss delta | validation +50 rate | overlap with baseline_A |
|---|---:|---:|---:|---:|---:|---:|---:|
| `r02_precision_volume_money` | 1,568 | -2.07% | +4.53% | +3.03% | -10.84% | 5.99% | 21.12% |
| `r02_precision_range_breakout` | 1,332 | -2.19% | +4.40% | +4.07% | -10.77% | 6.38% | 22.02% |
| `r02_precision_pullback_drawdown` | 1,282 | -2.16% | +4.25% | +2.86% | -9.38% | 6.79% | 34.41% |

Robustness descriptive readout:

| pool_id | robustness complete | robustness net | robustness matched delta | robustness loss delta | robustness +50 rate |
|---|---:|---:|---:|---:|---:|
| `r02_precision_pullback_drawdown` | 1,264 | +8.39% | +1.01% | -3.79% | 9.81% |
| `r02_precision_volume_money` | 1,553 | +7.82% | +0.85% | -6.11% | 10.17% |
| `r02_precision_range_breakout` | 1,230 | +8.57% | +0.59% | -5.89% | 10.57% |

这些 leads 不等于 selected pools。R04e 必须在 final report 中写明：

```text
R04e uses R04c failed descriptive leads as a frozen union diagnostic.
R04e does not reinterpret any R04c pool as having passed validation.
R04e does not reinterpret R04d as a policy pass.
```

## 4. R04e 要回答的问题

R04e 必须回答：

1. 三个 source pools 两两之间的 event overlap 是否足够低，还是只是同一事件 universe 的重复命名？
2. 即使 event overlap 低，calendar / instrument / industry / market-state overlap 是否仍然高度集中？
3. union 后 validation unique event count 是否接近 baseline_A 量级，还是仍然太小？
4. union hold120 no-exit 的 validation net 是否转正？
5. 如果 union hold120 validation net 没有转正，是否至少达到 conditional_go：相对 matched baseline_A 明显改善，且左尾改善稳定？
6. union 的改善是 event-level mean 改善，还是 portfolio-level 聚合后才出现？
7. portfolio-level equal-weight / family-balanced / active-cap 口径下，validation 是否有正收益或显著低于 baseline_A 的左尾？
8. union 是否只是提高 gross exposure 或 daily candidate count 后得到表面改善？
9. 哪个 source family 贡献了收益、左尾改善、右尾，是否存在单一 family 主导？
10. 如果 union 仍失败，是否说明 EP4 long-only candidate-pool 范式在 validation split 存在结构性天花板？

## 5. Non-Negotiables

### 5.1 R04e 不改变 R04c / R04d 结论

R04e 必须保留上游结论：

```text
R04c final decision remains r04c_no_candidate_pool_passed_validation.
R04d final decision remains r04d_no_policy_passed_validation.
```

禁止写：

```text
R04c selected volume_money
R04c selected union pool
R04d policy passed
R04e production entry rule
```

### 5.2 Union pool 固定，不能再筛

R04e 的唯一主池为：

```text
union_pool_id = r04e_union_r02_volume_money_range_breakout_pullback_drawdown
source_pool_ids:
  - r02_precision_volume_money
  - r02_precision_range_breakout
  - r02_precision_pullback_drawdown
```

每个 source pool 的 membership 权威定义来自 R02 family precision action-time panel：

```text
source_artifact = ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet
family_id in {volume_money, range_breakout, pullback_drawdown}
signal_occurs == true
feature_complete_flag == true
base_action_time_eligible_flag == true
episode_gap_trading_days = 20
anchor_signal_date = first trade_date in collapsed source-family episode
entry = first executable next-open after anchor_signal_date
```

R04c cache 可以用于 reconciliation 和 matched baseline comparator，但不得作为唯一 membership authority。

禁止：

```text
按 validation / robustness outcome 删除 source pool
按 market / industry / RPS 对 union 再筛
只保留 multi-family overlap events
按 R04d replay 结果重排 family 权重
新增 volume / volatility / extension threshold
```

### 5.3 Union event collapse 规则必须冻结

如果同一 instrument 在同一 `entry_execution_date` 命中多个 source family，R04e 必须 collapse 为一条 union event：

```text
union_event_key = instrument + entry_execution_date
source_family_set = sorted list of source families hit on the same union_event_key
source_family_count = len(source_family_set)
anchor_signal_date = min(anchor_signal_date among source hits)
entry_execution_date = same collapsed key date
entry_price = adjusted_open(entry_execution_date)
```

如果同一 instrument 的不同 source families 在不同 entry dates 触发，则保留为不同 union events，但必须输出 `same_instrument_nearby_event_audit`：

```text
nearby_window_trading_days = 20
same_instrument_nearby_source_event_count
same_instrument_nearby_union_event_count
```

不得用 `source_family_count` 作为 selection gate。它只能作为 descriptive diagnostic。

### 5.4 Portfolio diagnostic 不是交易策略批准

R04e 可以输出 portfolio-level daily return diagnostic，但不能输出 production-ready 结论。

允许：

```text
portfolio_level_strong_lead
portfolio_level_conditional_lead
union_not_viable
long_only_validation_ceiling_suspected
```

禁止：

```text
production ready
deployable strategy
entry rule approved
CTA strategy passed
```

### 5.5 Robustness 只读

R04e lifecycle 固定为：

```text
train: no parameter search except validating source definitions and optional train descriptive context
validation: primary diagnostic decision
robustness: final readout only
```

robustness 不得：

```text
改变 union membership
改变 source pool set
改变 policy matrix
改变 active-cap threshold
改变 final validation status
```

### 5.6 禁止复杂 exit 扩展

R04e v1 只允许 simple hold / simple risk-budget / portfolio cap：

```text
hold_20d
hold_40d
hold_60d
hold_120d
no_exit
break_even_after_gain
fixed_stop
active_equal_weight
family_balanced_active_equal_weight
daily_entry_cap sensitivity
```

R04e v1 禁止：

```text
ATR trailing
EMA trailing
CTA / trend-following trailing
profit_lock_after_gain
market_state entry/block gate
industry_state entry/block gate
validation-tuned family weights
```

## 6. 必需输入

R04e 必须加载并校验：

```text
ep4/outputs/r04c_candidate_pool_scanner_v1/manifests/r04c_candidate_pool_scanner_validation.json
ep4/outputs/r04c_candidate_pool_scanner_v1/manifests/r04c_candidate_pool_scanner_manifest.json
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_final_decision.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_hold120_pool_profile.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_matched_baseline_delta_summary.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_overlap_uniqueness_audit.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_concentration_audit.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_pool_registry_frozen.csv
ep4/outputs/r04c_candidate_pool_scanner_v1/cache/r04c_pool_event_panel.parquet
ep4/outputs/r04c_candidate_pool_scanner_v1/cache/r04c_matched_baseline_panel.parquet

ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/manifests/r04d_volume_money_relative_improvement_risk_budget_validation.json
ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/reports/r04d_final_decision.csv

ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet

ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json

data/qlib/cn_data_pit/calendars/day.txt
data/qlib/cn_data_pit/features/*/{open,high,low,close,volume,money,factor}.day.bin
data/qlib/cn_data_pit/instruments/*.txt
```

Upstream validation gates：

```text
R04c validation_status == passed
R04c final_decision == r04c_no_candidate_pool_passed_validation
R04d validation_status == passed
R04d final_decision == r04d_no_policy_passed_validation
R04b validation_status == passed
```

若任一条件不满足，R04e 必须 fail closed：

```text
blocked_upstream_validation_failed
blocked_upstream_state_changed
blocked_missing_required_input
```

## 7. Split 与 baseline

R04e 必须沿用 R04/R04b/R04c 的 split 定义，不得重切：

```text
train
validation
robustness
```

R04e 必须同时输出以下 comparators：

```text
union_pool:
  r04e_union_r02_volume_money_range_breakout_pullback_drawdown

source_pools:
  r02_precision_volume_money
  r02_precision_range_breakout
  r02_precision_pullback_drawdown

global_baseline_A:
  baseline_A_r04_included_rps_episode_first_trigger

matched_baseline_A:
  R04c matched baseline panel, replayed under the same R04e policy when possible
```

Comparator 角色：

```text
global_baseline_A:
  absolute context and EP4 long-only baseline

matched_baseline_A:
  same split / calendar / market / industry matched comparator
  used for event-level matched deltas

source_pools:
  family contribution and union decomposition
```

`matched_baseline_A` 不得用于重新选择 union membership。

## 8. Gate 0: Union Readiness / P0.5

R04e 必须先生成 Gate 0 readiness 表。Gate 0 不是 final strategy gate，而是判断 union 是否值得解读的前置诊断。

### 8.1 Event overlap audit

必需字段：

```text
source_pool_id_a
source_pool_id_b
split
event_count_a
event_count_b
intersection_event_count
union_event_count
jaccard
overlap_share_vs_a
overlap_share_vs_b
same_instrument_overlap_count
same_instrument_overlap_share_vs_a
same_entry_date_overlap_count
same_entry_date_overlap_share_vs_a
overlap_status
```

Gate 0 event-overlap 解释口径：

```text
low_overlap: max pairwise jaccard <= 0.25
moderate_overlap: 0.25 < max pairwise jaccard <= 0.45
high_overlap: max pairwise jaccard > 0.45
```

`high_overlap` 不自动 fail，但 final report 只能说 union 是 correlated source blend，不能说 diversified union。

### 8.2 Pseudo-diversification audit

R04e 必须检查低 event overlap 是否只是伪分散。必需字段：

```text
split
pool_id
event_count
replay_complete_count
top1_calendar_year_share
top1_calendar_month_share
top1_instrument_share
top5_instrument_share
top1_industry_share
top3_industry_share
top1_market_state_share
top1_industry_state_share
daily_candidate_count_mean
daily_candidate_count_p50
daily_candidate_count_p90
daily_candidate_count_p95
daily_candidate_count_p99
same_instrument_20d_cluster_share
pseudo_diversification_status
```

Pseudo-diversification status：

```text
sufficient:
  top1_instrument_share <= 0.03
  top5_instrument_share <= 0.12
  top1_industry_share <= 0.25
  same_instrument_20d_cluster_share <= 0.35
  daily_candidate_count_p99 <= 80

watch:
  any sufficient threshold breached, but no severe threshold breached

concentrated:
  top1_instrument_share > 0.05
  OR top5_instrument_share > 0.20
  OR top1_industry_share > 0.35
  OR same_instrument_20d_cluster_share > 0.50
  OR daily_candidate_count_p99 > 120
```

Calendar concentration must be reported but must not hard-fail validation by itself, because validation split is already short and structurally year-concentrated.

### 8.3 Union hold120 no-exit readiness

R04e 必须先在 union pool 上跑 event-level hold120 no-exit fixed-size replay。

必需字段：

```text
split
pool_id
event_count
replay_complete_count
censored_share
net_return_mean
net_return_median
net_return_p10
net_return_p25
net_return_p75
net_return_p90
loss_le_minus5_rate
loss_le_minus10_rate
max_gain50_rate
matched_baseline_net_return_mean
net_return_mean_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
max_gain50_rate_delta_vs_matched_baseline_A
top1_calendar_year_share
top1_instrument_share
top1_industry_share
readiness_status
```

Validation readiness status：

```text
strong_go:
  validation replay_complete_count >= 2500
  validation net_return_mean > 0
  validation net_return_mean_delta_vs_matched_baseline_A >= 0.02
  validation p10_delta_vs_matched_baseline_A >= 0
  validation loss_le_minus5_delta_vs_matched_baseline_A < 0
  validation matched_comparator_status == sufficient
  pseudo_diversification_status != concentrated

conditional_go:
  validation replay_complete_count >= 2000
  validation net_return_mean >= -0.015
  validation net_return_mean_delta_vs_matched_baseline_A >= 0.02
  validation p10_delta_vs_matched_baseline_A >= 0
  validation loss_le_minus5_delta_vs_matched_baseline_A < 0
  validation matched_comparator_status == sufficient
  pseudo_diversification_status != concentrated

stop:
  otherwise
```

`strong_go` 可以进入 portfolio-level replay 的 positive-readout interpretation。

`conditional_go` 可以进入 portfolio-level replay，但 final report 必须写明：

```text
Union hold120 is still not an absolute positive pool; R04e only tests portfolio-level loss reduction.
```

`stop` 时仍可输出 fixed matrix replay as audit，但 final decision 不得升级。

## 9. Union Portfolio Replay

### 9.1 Entry semantics

Entry 固定为：

```text
entry_execution_date = first executable next-open after anchor_signal_date
entry_price = adjusted_open(entry_execution_date)
```

不得在 entry 加入 dynamic allow/block。

### 9.2 Event-level policy matrix

R04e v1 的 event-level policy matrix 固定为：

```yaml
hold_rules:
  - hold_20d
  - hold_40d
  - hold_60d
  - hold_120d

exit_rules:
  no_exit:
    params: [none]
  break_even_after_gain:
    activation_gain_pct: [0.08, 0.10, 0.15]
  fixed_stop:
    stop_loss_pct: [-0.05, -0.08, -0.10]
```

不运行 `time_stop` 作为独立 exit family，因为 `hold_20d/40d/60d` 已经覆盖主要 shorter-hold 问题。若实现中保留 `time_stop`，必须标记为 sensitivity-only，不得进入 primary gates。

Exit execution 沿用 R04b/R04d 语义：

```text
execution_policy = close_signal_next_open
entry_execution_date open = offset 0 entry execution
day N close = trading-day offset N close after entry execution
exit_signal_date = first close-based date whose policy condition is true
exit_execution_date = first executable open after exit_signal_date
```

Policy semantics：

```text
no_exit:
  exit_signal_date = close at hold_rule_max_days

fixed_stop:
  exit if close_return_from_entry <= stop_loss_pct
  else exit at hold_rule_max_days

break_even_after_gain:
  inactive before close_return_from_entry >= activation_gain_pct
  after activation, exit if close_return_from_entry <= 0
  else exit at hold_rule_max_days
```

### 9.3 Portfolio weighting matrix

R04e 必须在 event-level replay 之上构造 portfolio-level daily return。

Primary portfolio weighting：

```text
active_equal_weight:
  each active union event has equal weight each day
  total gross exposure normalized to 1.0 when active_count > 0

family_balanced_active_equal_weight:
  each source family sleeve receives equal gross sleeve weight among families with active positions
  events inside each active source family sleeve are equal-weighted
  multi-family collapsed event receives fractional membership in each source family in source_family_set
  total gross exposure normalized to 1.0 when active_count > 0
```

Active-cap sensitivity：

```yaml
daily_active_cap:
  primary: none
  sensitivity: [20, 40, 60]
```

If `active_count > daily_active_cap`, cap selection must use a deterministic pre-outcome key:

```text
cap_rank_key =
  sha256(instrument + entry_execution_date + union_event_key)
```

Cap sensitivity is not a train/validation-selected parameter. It is reported as capacity / concentration sensitivity only. Primary final decision uses uncapped active portfolios.

### 9.4 Daily portfolio return construction

Runner must build a daily path panel for each event-policy pair:

```text
event_id
policy_id
trade_date
entry_execution_date
exit_execution_date
active_flag
daily_gross_return
daily_cost_return
daily_net_return
source_family_set
source_family_count
```

Daily return semantics：

```text
entry day:
  from entry open to same-day close, net of entry cost

intermediate active days:
  close-to-close adjusted return

exit day:
  from prior close to exit open, net of exit cost
  active_flag = true only until exit execution

non-active days:
  excluded from active basket; portfolio return is 0 when no active events
```

Portfolio daily return:

```text
portfolio_daily_net_return =
  sum(event_daily_net_return * portfolio_event_weight_on_date)
```

The portfolio is long-only and cash earns zero return. Total gross exposure must not exceed 1.0 in primary portfolios.

### 9.5 Cost model

R04e must reuse R04b/R04d cost model:

```yaml
cost_model:
  cost_model_id: a_share_daily_replay_default_v1
  entry_slippage_bps: 5.0
  exit_slippage_bps: 5.0
  commission_bps_per_side: 3.0
  stamp_tax_bps_on_exit: 5.0
  min_fee_policy: none
```

Event-level and portfolio-level net returns must both be net of the above costs.

## 10. Metrics

### 10.1 Event-level metrics

For each `split x pool_id x policy_id`:

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
loss_le_minus5_rate
loss_le_minus10_rate
max_drawdown_p50
max_drawdown_p90
max_gain50_count
max_gain50_rate
max_gain120d_p90
avg_holding_days
matched_baseline_status
net_return_mean_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
```

### 10.2 Portfolio daily metrics

For each `split x portfolio_id x policy_id`:

```text
trading_day_count
active_day_count
active_day_share
daily_return_mean
daily_return_median
daily_return_p10
daily_return_p25
daily_return_p75
daily_return_p90
period_compounded_return
annualized_return
annualized_vol
sharpe_like
max_drawdown
worst_20d_return
best_20d_return
active_count_mean
active_count_p50
active_count_p90
active_count_p95
active_count_p99
turnover_event_count
avg_holding_days
portfolio_denominator_status
```

`annualized_return` and `sharpe_like` are descriptive only. Final gates must primarily use:

```text
period_compounded_return
daily_return_mean
max_drawdown
worst_20d_return
monthly_return_p10
```

### 10.3 Monthly portfolio metrics

For each `split x portfolio_id x policy_id x calendar_month`:

```text
month
monthly_compounded_return
active_day_share
active_count_mean
turnover_event_count
source_family_volume_money_weight_share
source_family_range_breakout_weight_share
source_family_pullback_drawdown_weight_share
```

Monthly summary:

```text
monthly_count
monthly_return_mean
monthly_return_median
monthly_return_p10
monthly_return_min
positive_month_rate
worst_month
worst_month_return
```

### 10.4 Family contribution decomposition

R04e must decompose union portfolio performance:

```text
split
portfolio_id
policy_id
source_family_id
active_weight_share_mean
event_count
daily_return_contribution_sum
daily_return_contribution_mean
monthly_return_contribution_mean
loss_day_contribution_share
positive_day_contribution_share
max_gain50_event_count
source_family_status
```

Required source family ids:

```text
volume_money
range_breakout
pullback_drawdown
multi_family_collapsed
```

### 10.5 Baseline comparison metrics

R04e must compare union portfolios against baseline_A under the same portfolio construction:

```text
portfolio_period_return_delta_vs_baseline_A
portfolio_daily_mean_delta_vs_baseline_A
portfolio_monthly_p10_delta_vs_baseline_A
portfolio_max_drawdown_delta_vs_baseline_A
portfolio_worst_20d_delta_vs_baseline_A
active_count_p95_delta_vs_baseline_A
```

Baseline_A portfolio replay must use the same policy matrix and active portfolio construction, not copied summary rows from R04/R04c.

## 11. Decision Gates

R04e is diagnostic-only. Final decision statuses are descriptive, not production approvals.

### 11.1 Gate 0 status

Gate 0 status must be one of:

```text
gate0_strong_go
gate0_conditional_go
gate0_stop_low_quality_union
gate0_blocked_insufficient_inputs
```

Mapping:

```text
gate0_strong_go:
  readiness_status == strong_go

gate0_conditional_go:
  readiness_status == conditional_go

gate0_stop_low_quality_union:
  readiness_status == stop

gate0_blocked_insufficient_inputs:
  required inputs / matched baseline / denominator missing
```

### 11.2 Portfolio validation gate

Primary validation portfolio candidates are:

```text
portfolio_id in {
  active_equal_weight_uncapped,
  family_balanced_active_equal_weight_uncapped
}
policy_id in fixed event-level matrix
```

A policy is `validation_portfolio_strong_pass` only if all conditions hold:

```text
Gate 0 status in {gate0_strong_go, gate0_conditional_go}
validation portfolio period_compounded_return > 0
validation portfolio daily_return_mean > 0
validation portfolio monthly_return_p10 >= -0.05
validation portfolio max_drawdown <= baseline_A same-policy max_drawdown
validation portfolio monthly_return_p10_delta_vs_baseline_A >= 0
validation event-level max_gain50_rate >= 0.80 * union_hold120_no_exit_max_gain50_rate
validation active_day_share >= 0.50
validation active_count_p95 <= 80 for uncapped portfolio, or cap sensitivity confirms no single date dominates
```

A policy is `validation_portfolio_conditional_pass` if:

```text
Gate 0 status in {gate0_strong_go, gate0_conditional_go}
validation portfolio period_compounded_return > 0
validation portfolio daily_return_mean > 0
validation portfolio monthly_return_p10_delta_vs_baseline_A >= 0
validation portfolio max_drawdown_delta_vs_baseline_A <= 0
validation event-level max_gain50_rate >= 0.60 * union_hold120_no_exit_max_gain50_rate
```

Otherwise:

```text
validation_portfolio_failed
```

### 11.3 Validation selection rule

R04e does not do train parameter search. If multiple policies pass validation:

1. prefer `family_balanced_active_equal_weight_uncapped` over `active_equal_weight_uncapped` if both pass with similar return, because family balancing better tests union diversification;
2. prefer policy with higher validation `monthly_return_p10`;
3. then lower validation `max_drawdown`;
4. then higher validation `period_compounded_return`;
5. then shorter average holding days only if the first four are tied.

This ranking must be frozen in code before robustness readout.

### 11.4 Robustness readout

Robustness can only classify the validation-selected policy:

```text
robustness_confirmed:
  robustness period_compounded_return > 0
  robustness daily_return_mean > 0
  robustness monthly_return_p10_delta_vs_baseline_A >= 0
  robustness max_drawdown_delta_vs_baseline_A <= 0

robustness_mixed:
  robustness period_compounded_return > 0
  but one of left-tail deltas fails

robustness_failed:
  robustness period_compounded_return <= 0
  OR daily_return_mean <= 0
```

Robustness cannot turn a validation fail into pass.

### 11.5 Final decision

Final decision must be one of:

```text
r04e_union_portfolio_strong_lead
r04e_union_portfolio_conditional_lead
r04e_union_validation_positive_but_robustness_mixed
r04e_union_validation_positive_but_robustness_failed
r04e_union_not_viable_validation
r04e_long_only_validation_ceiling_suspected
r04e_blocked_upstream_validation_failed
r04e_blocked_missing_required_input
r04e_blocked_validation_failed
```

Decision precedence:

1. If required input or upstream validation missing: `r04e_blocked_missing_required_input` or `r04e_blocked_upstream_validation_failed`.
2. If validator checks fail: `r04e_blocked_validation_failed`.
3. If Gate 0 stop because denominator, matched comparator, or pseudo-diversification is insufficient: `r04e_union_not_viable_validation`.
4. If Gate 0 stop because absolute validation net is still weak, but baseline_A validation is also very negative and union still improves matched left-tail: `r04e_long_only_validation_ceiling_suspected`.
5. If validation has no strong or conditional portfolio pass: `r04e_union_not_viable_validation`.
6. If validation conditional pass and robustness confirmed or mixed: `r04e_union_portfolio_conditional_lead`.
7. If validation strong pass and robustness confirmed: `r04e_union_portfolio_strong_lead`.
8. If validation strong pass but robustness mixed: `r04e_union_validation_positive_but_robustness_mixed`.
9. If validation pass but robustness failed: `r04e_union_validation_positive_but_robustness_failed`.

Even for `strong_lead`, report must state:

```text
diagnostic only; no production entry rule is emitted; upstream pools were selected after prior OOS descriptive review.
```

## 12. 必需输出

R04e must write:

```text
ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/
  cache/
    r04e_source_pool_event_panel.parquet
    r04e_union_event_panel.parquet
    r04e_event_policy_path_panel.parquet
    r04e_portfolio_daily_return_panel.parquet
    r04e_baseline_A_portfolio_daily_return_panel.parquet
    r04e_matched_baseline_event_replay_panel.parquet
  reports/
    r04e_source_pool_reconciliation.csv
    r04e_union_event_overlap_audit.csv
    r04e_pseudo_diversification_audit.csv
    r04e_daily_candidate_count_audit.csv
    r04e_union_hold120_readiness.csv
    r04e_policy_matrix_frozen.csv
    r04e_event_policy_replay_summary.csv
    r04e_portfolio_policy_summary.csv
    r04e_portfolio_monthly_summary.csv
    r04e_family_contribution_decomposition.csv
    r04e_baseline_A_portfolio_comparison.csv
    r04e_gate_audit.csv
    r04e_final_decision.csv
    r04e_union_pool_portfolio_level_final_report.md
  manifests/
    r04e_union_pool_portfolio_level_manifest.json
    r04e_union_pool_portfolio_level_validation.json
```

### 12.1 Manifest requirements

Manifest must include:

```text
requirement_id
config_hash
runner_hash
validator_hash
upstream_r04c_manifest_hash
upstream_r04d_manifest_hash
upstream_r04b_manifest_hash
r02_family_action_time_panel_hash
price_provider_hash
cost_model_id
source_pool_ids
union_pool_id
policy_matrix_hash
portfolio_weighting_matrix_hash
split_definition_hash
artifact_hashes
created_at
```

## 13. Validator Requirements

Validator must fail closed if any required check fails.

Required checks:

1. All required inputs exist.
2. R04c validation status is `passed`.
3. R04c final decision is exactly `r04c_no_candidate_pool_passed_validation`.
4. R04d validation status is `passed`.
5. R04d final decision is exactly `r04d_no_policy_passed_validation`.
6. R04b validation status is `passed`.
7. Source family set is exactly `{volume_money, range_breakout, pullback_drawdown}`.
8. Union membership is deterministic and reproducible from R02 family action-time panel.
9. R04c source pool reconciliation overlap share for each source pool is >= 0.99.
10. Same instrument + same entry date collapse has no duplicate `union_event_key`.
11. `source_family_count` appears only as diagnostic; it is not used as selection filter.
12. No market / industry / RPS gate is applied to union membership.
13. Policy matrix contains only allowed v1 policies.
14. Policy matrix contains no `ATR`, `EMA`, `CTA`, `profit_lock`, `market_state_gate`, or `industry_state_gate` primary rows.
15. Event-level replay uses close-signal-next-open execution.
16. Cost model matches R04b/R04d default.
17. Matched baseline deltas are computed from same-policy replay, not copied from R04c hold120 rows.
18. Baseline_A portfolio comparison uses same portfolio construction as union.
19. Portfolio total gross exposure never exceeds 1.0 in primary portfolios.
20. Active-cap sensitivity is not used for primary validation selection.
21. Robustness metrics are not used to select policy or change final validation status.
22. Final decision is one of the allowed status values.
23. Final report includes the mandatory non-reinterpretation statements.
24. Final report does not contain forbidden production language.
25. Manifest contains hashes for all required artifacts.

Validator output schema:

```text
check_id
check_name
status
severity
details
```

Validation manifest:

```json
{
  "validation_status": "passed|failed",
  "failed_checks": [],
  "warning_checks": [],
  "final_decision": "...",
  "selected_portfolio_policy_id": "...|null",
  "gate0_status": "...",
  "created_at": "..."
}
```

## 14. Final Report 必答问题

Final report 必须用中文回答：

1. R04e 是否改变 R04c/R04d 的失败结论？答案必须是否定。
2. 三个 source pools 的 pairwise event overlap 是多少？
3. union 是否真的分散，还是 calendar / instrument / industry / market-state 伪分散？
4. union hold120 no-exit validation net 是否转正？
5. Gate 0 是 strong_go、conditional_go 还是 stop？
6. portfolio-level active_equal_weight 与 family_balanced 哪个更好？
7. 改善主要来自 event-level alpha，还是组合层分散？
8. union 相对 baseline_A 的 monthly p10、max drawdown、worst 20d 是否改善？
9. 哪个 source family 贡献了收益，哪个贡献了左尾风险？
10. daily candidate count 是否过高，active cap 是否改变结论？
11. 如果 validation 仍失败，是否支持 `long_only_validation_ceiling_suspected`？
12. 后续应进入 R04f portfolio sleeve / market-state cash sleeve，还是停止 EP4 long-only pool 线？

## 15. Implementation Notes

### 15.1 Suggested execution phases

Runner should be structured as:

```text
phase_0_load_and_validate_inputs
phase_1_reconstruct_source_pools
phase_2_build_union_event_panel
phase_3_gate0_overlap_and_readiness
phase_4_event_level_policy_replay
phase_5_portfolio_daily_return_construction
phase_6_portfolio_summary_and_baseline_comparison
phase_7_gate_audit_and_final_decision
phase_8_manifest_and_report_stub
```

### 15.2 Fail-closed behavior

If Gate 0 fails, runner may still complete phases 4-8 for audit, but final decision cannot exceed:

```text
r04e_union_not_viable_validation
r04e_long_only_validation_ceiling_suspected
```

If a portfolio policy looks good only under active-cap sensitivity but not under uncapped primary portfolios, it must be reported as:

```text
capacity_sensitivity_only
```

not selected.

### 15.3 Why R04e does not add CTA

R04d already showed single-pool simple risk-budget has limited upside:

```text
best validation net: -0.58%
best validation delta_vs_hold120: +1.49%
short-hold retention: 0.88% to 6.19%
```

Adding CTA / trailing at R04e would mix two questions:

```text
Does union diversify candidate pools?
Does a complex exit fit these paths?
```

R04e v1 must answer the first question first.

## 16. Non-goals

R04e does not:

```text
promote any R04c failed pool to passed
retry volume_money alone
search new family thresholds
build production strategy
optimize portfolio weights on validation or robustness
add shorting
add cash timing based on market state
alter split definitions
alter R04c/R04d final decisions
```

If R04e concludes that union still fails validation, the recommended next research question is not R04d v2. It is:

```text
Does EP4 long-only candidate-pool research require market-state cash sleeve,
short sleeve, or a different split design because validation years are structurally adverse?
```
