# EP4 需求 05a: Alpha Pool Discovery Protocol V1

## 1. 需求元信息

- 需求 id: `ep4_r05a_alpha_pool_discovery_protocol_v1`
- 简称: `r05a_alpha_pool_discovery_protocol_v1`
- 状态: 首版可实现的 alpha pool discovery protocol / matched comparator 需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion5.md`
- 上游 R04 需求: `ep4/requirement_04_dynamic_momentum_exposure_eligibility_audit_v1.md`
- 上游 R04b 需求: `ep4/requirement_04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.md`
- 上游 R04c 需求: `ep4/requirement_04c_candidate_pool_scanner_v1.md`
- 上游 R04d 需求: `ep4/requirement_04d_volume_money_relative_improvement_risk_budget_replay_v1.md`
- 上游 R04e 需求: `ep4/requirement_04e_union_pool_portfolio_level_diagnostic_v1.md`
- 必需输出根目录: `ep4/outputs/r05a_alpha_pool_discovery_protocol_v1/`
- 必需 config 路径: `ep4/configs/r05a_alpha_pool_discovery_protocol_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r05a_alpha_pool_discovery_protocol.py`
- 必需 validator 路径: `ep4/scripts/validate_r05a_alpha_pool_discovery_protocol.py`
- 日期: 2026-05-19

## 2. 背景与实验目的

R04/R04b/R04c/R04d 的共同结论是：

```text
已有 stock-level signals 有信息，
但主要表现为：
  right-tail enrichment
  path-state confirmation
  relative left-tail improvement

它们尚未稳定证明：
  action-time after-cost positive expectancy alpha pool
```

R04c/R04d 中大量结果属于：

```text
matched delta > 0
AND validation net < 0
= relative improvement pool
!= alpha pool
```

R05a 的目的不是继续在 RPS / momentum / family universe 上切 gate，也不是把 R04c/R04d 的 failed leads 改写成 selected pools。

R05a 只做一件事：

```text
冻结下一阶段 alpha pool discovery 的研究协议，
并以低 overlap candidate universe 做首版 action-time audit。
```

核心问题是：

```text
是否存在一个与现有 RPS / family pools 低重叠的新事件 universe，
其 entry-time after-cost return distribution 本身足够干净，
可以在 validation 上形成 absolute positive expectancy？
```

## 3. 研究原假设

R05a 必须把怀疑写成正式 null hypothesis，而不是默认 alpha pool 存在。

```text
H0:
  在当前 A-share long-only universe、日频 next-open execution、
  成本、容量、停牌/跌停约束下，
  不存在可复用的 low-left-tail positive-expectancy alpha pool。
```

R05a 的任务是尝试拒绝该原假设。

如果 validation 无法拒绝 H0，则后续不应继续扩大 primitive search。现有信号应降级为：

```text
lifecycle tags
relative-improvement sleeves
risk overlays
explanatory diagnostics
```

## 4. R05a 要回答的问题

R05a 必须回答：

1. 新 candidate universe 与 RPS / R02 family / R04c descriptive leads 的 event overlap 是否足够低？
2. 新 candidate universe 的 action-time after-cost validation net 是否大于 0？
3. 右尾是否仍然存在，而不是被低波 / base filter 完全消灭？
4. 左尾是否相对 matched comparator 有统计意义上的改善？
5. 改善是否通过 block bootstrap / leave-one-out / concentration stress，而不是 event-level noise？
6. matched comparator 是否控制 split、calendar、industry、liquidity、volatility、market regime、momentum context？
7. 结果是否在 capacity-adjusted after-cost 口径下仍然通过？
8. 是否存在 top1 year / top1 industry / top1 instrument 主导？
9. 是否存在 look-ahead、same-day close、future high/low、survivorship、停牌/跌停执行等数据泄漏？
10. 如果不能通过 validation，失败原因是 no alpha、统计功效不足、容量失败、执行失败，还是结构性左尾不可控？

## 5. Non-Negotiables

### 5.1 Alpha Pool 与 Relative Improvement Pool 必须分开

R05a 必须使用以下术语：

```text
relative_improvement_pool:
  matched net delta > 0
  but validation net <= 0

alpha_pool:
  validation net mean > 0
  validation median > -0.50% at T+20 net return
  validation p10 >= matched baseline p10
  validation loss<=-5% < matched baseline
  after-cost and capacity-adjusted result still passes
  bootstrap / block-bootstrap evidence passes
```

R05a v1 的默认主判定口径为：

```text
primary_decision_horizon = T+20 net return
secondary_tail_horizons = T+60 / T+120
pre_registered_median_floor = -0.50% at T+20 net return
```

所有未显式带 horizon 后缀的 `net / median / p10 / loss<=-5%` gate，默认均指 `primary_decision_horizon = T+20 net return`。

如果 runner 需要改变主判定 horizon，必须在 R05a 跑前通过 config 和 frozen rule registry 明确写死，不能在 outcome 后调整。

禁止把以下结果写成 alpha：

```text
matched delta > 0 but validation net <= 0
robustness positive after validation failure
right-tail coverage improved but p10 / loss worsened
raw return positive but capacity-adjusted return failed
```

### 5.2 不允许继续 RPS / Family Slicing

R05a 不是：

```text
R04c retry
R04d v2
R04e follow-up selector
more RPS threshold search
more family ordering search
fresh-count / same-day bundle retry
market-state stock-level entry gate
```

禁止在 validation 后新增：

```text
RPS threshold
industry gate
market gate
family count gate
bad-shape filter
post-hoc liquidity filter
post-hoc volatility filter
```

### 5.3 Train-Only Discovery + Validation Freeze

R05a 必须固定生命周期：

```text
train:
  primitive / threshold / pool search
  select small fixed candidate set

validation:
  confirm train-selected frozen candidates only
  no threshold adjustment
  no new bucket merge
  no reverse selection

robustness:
  read-only final readout
```

如果 discovery 使用了 all-splits，只能输出：

```text
oos_retest_required
```

不能进入 alpha promotion。

### 5.4 Market-State Exposure Overlay 不能创造 Alpha

R05a 可以输出 market-state return decomposition，但不得把 cash / exposure sleeve 写成 alpha source。

任何 exposure overlay 如果要进入后续 requirement，必须先满足：

```text
risk_on_full_exposure_validation_net > 0
```

否则只允许输出：

```text
market_state_risk_control_lead
not_alpha_pool
```

## 6. 候选 Universe Scope

### 6.1 R05a V1 Primary Candidate Universes

R05a v1 只允许两个 primary candidate universes：

```text
low_vol_uptrend
base_breakout_vcp
```

原因：

```text
1. 与现有 RPS / family universe overlap 预期较低。
2. primitive 容易做严格 as-of 冻结。
3. 文献先验支持 low-vol / structured momentum 方向。
4. 不直接依赖 post-event survival 或 winner label。
```

### 6.2 Excluded From R05a V1

以下方向不进入 R05a v1 primary gate：

```text
post_capitulation_recovery
leader_not_extended
liquidity_dry_to_active
raw RPS95 extension
R02 family union with new thresholds
market-state cash sleeve
```

其中 `post_capitulation_recovery` 必须延后，因为 A 股下该方向存在结构性左尾：

```text
停牌
连续跌停不可退出
ST / 退市路径
监管处罚
流动性塌陷
```

如果后续单独研究该方向，必须先实现 suspension-aware / limit-down-aware / delisting-aware return model。

## 7. Candidate Pool Registry

R05a runner 必须在任何 outcome 计算前冻结 candidate pool registry，并写入：

```text
reports/r05a_candidate_pool_registry_frozen.csv
reports/r05a_rule_registry_frozen.csv
```

每个 candidate pool 必须带固定八元组：

```text
1. source rule
2. as-of rule
3. entry rule
4. event collapse rule
5. cost / capacity rule
6. matched comparator rule
7. statistical evidence rule
8. kill criteria
```

必需字段：

```text
pool_id
pool_name
candidate_family
source_rule_text
feature_formula_text
feature_formula_hash
asof_rule_text
entry_rule_text
event_collapse_rule_text
cost_rule_id
capacity_rule_id
matched_comparator_rule_id
statistical_evidence_rule_id
kill_criteria_id
train_selection_allowed
validation_selection_allowed
robustness_selection_allowed
status
```

`r05a_rule_registry_frozen.csv` 必须注册所有被 candidate pool 引用的 rule id。

必需字段：

```text
rule_id
rule_type
rule_name
rule_text
default_value_json
formula_hash
applies_to_pool_id
active_flag
```

其中 `rule_type` 只允许：

```text
source_rule
asof_rule
entry_rule
event_collapse_rule
cost_capacity_rule
matched_comparator_rule
statistical_evidence_rule
kill_criteria_rule
```

validator 必须 fail closed：

- registry 缺失；
- rule registry 缺失；
- 公式没有 hash；
- registry 中没有八元组任一元素；
- pool 引用的 rule_id 不存在于 `r05a_rule_registry_frozen.csv`；
- 同一 `rule_type + applies_to_pool_id` 下 active rule 不唯一；
- validation 出现 registry 未声明 pool；
- validation 后 registry 被修改；
- validation 后 rule registry 被修改；
- 实际 membership 与 frozen registry 公式不一致；
- pool 在 validation 后新增、合并、重命名、删除阈值。

## 8. Action-Time Anchor 与 As-Of 规则

R05a 必须固定 action-time grain：

```text
decision_date = D after close
entry_execution_date = next tradable open after D
entry_price = adjusted_open(entry_execution_date)
event_key = pool_id + instrument_id + entry_execution_date
```

所有 entry features 必须满足：

```text
all entry features known no later than D close
if entry_date = E open:
  feature_asof_date <= previous tradable close before E
```

禁止：

```text
same-day close feature for same-day open execution
future high/low window in base / VCP definition
post-entry volume / turnover in liquidity confirmation
future industry membership
future universe membership
future ST / delisting status
future suspension status
```

行业分类必须使用 as-of 信息。如果 instrument 在 `decision_date` 前 60 个交易日内发生行业重分类，matched bucket v1 使用重分类前的稳定 industry，并在 audit 中标记：

```text
industry_reclassification_lookback_days = 60
industry_reclassification_audit_flag = 1
matched_industry_bucket = prior_stable_industry
```

该规则只使用 `decision_date` 时已经可知的行业历史，不得使用未来重分类。

具体 primitive 的 as-of 要求：

```text
volatility contraction:
  contraction window must end before breakout confirmation, or be known by D close

base breakout:
  base high / base low cannot use post-entry bars
  if breakout is confirmed by D close, earliest entry is D+1 open

industry relative strength:
  industry return / ranking must use asof industry membership and D-close-known prices

market breadth:
  breadth must be computed from securities tradable and observable as of D

liquidity:
  money / volume expansion cannot use entry-day turnover
```

## 9. Candidate Universe Definition Requirements

### 9.1 Low-Vol Uptrend

`low_vol_uptrend` 的 source rule 必须表达以下结构：

```text
longer-term trend up
medium-term trend non-negative
realized_volatility_60d <= same-day matched universe median
price not extremely extended from MA / ATR
liquidity sufficient for execution
no blowoff volume / high-vol lottery state
```

R05a v1 不允许在 low-vol 定义里同时保留多个可选口径。默认冻结为：

```text
realized_volatility_window = 60 trading days
matched_universe_for_vol_median =
  same decision_date
  same split
  same industry bucket
  same liquidity quartile
low_vol_condition =
  realized_volatility_60d <= matched_universe_median_realized_volatility_60d
```

该 pool 的目标不是最高 big-winner rate，而是：

```text
right-tail remains
left-tail naturally lighter
after-cost validation net positive
```

### 9.2 Base Breakout / VCP

`base_breakout_vcp` 的 source rule 必须表达以下结构：

```text
pre-breakout volatility contraction
base drawdown controlled
breakout confirmed no later than D close
breakout day not extremely extended by ATR / MA distance
volume expansion mild to moderate, not blowoff
entry at next tradable open after breakout confirmation
```

R05a v1 的 base / VCP 默认冻结值：

```text
minimum_base_length_trading_days = 20
maximum_base_drawdown_pct = 15%
breakout_confirmed_by = D close
earliest_entry = D+1 tradable open
```

禁止：

```text
using post-entry high to define breakout
using future base boundary
using future max gain to confirm VCP
using entry-day volume for D+1 open decision
```

## 10. Event Collapse 与 Sample Construction

同一 `pool_id + instrument_id` 在短窗口内重复触发，必须按 frozen collapse rule 处理。

默认 collapse rule：

```text
collapse_window_trading_days:
  low_vol_uptrend = 20
  base_breakout_vcp = 10
keep first event within collapse window
next eligible event must be after prior entry_execution_date + collapse_window
```

这是 R05a v1 的保守取舍，不代表最优事件间隔。`low_vol_uptrend` 用 20 天近似月度状态再入场，`base_breakout_vcp` 用 10 天允许较快的二次 breakout 事件。任何 universe-specific collapse window search 都必须进入 R05a v2，不能在 R05a validation 后调整。

runner 必须输出：

```text
reports/r05a_event_collapse_audit.csv
```

必需字段：

```text
pool_id
split
instrument_id
raw_signal_date
decision_date
entry_execution_date
event_key
collapse_window_trading_days
raw_trigger_count_in_window
kept_event_flag
collapse_reason
```

不得用 validation outcome 修改 collapse window。

## 11. Matched Comparator Spec

R05a 必须使用 matched comparator，而不是全市场平均。

每个 candidate event 的 comparator 必须在同一 split 内匹配：

```text
calendar year / quarter
market regime
industry
liquidity bucket
volatility bucket
momentum / RPS context bucket
tradability status
```

### 11.1 Default Matched Comparator Fallback Ladder

R05a v1 必须使用统一 fallback ladder，避免不同 runner 自行决定匹配松绑顺序。

默认冻结值：

```text
target_matched_candidates_per_event = 50
minimum_matched_candidates_per_event = 20
matched_sampling_with_replacement = false
matched_random_seed = 20260519
validation_unmatched_event_share_cap = 5%
validation_fallback_level_ge_3_share_cap = 30%
```

fallback ladder：

```text
L0:
  split
  calendar year-quarter
  market regime
  industry bucket
  liquidity quartile
  volatility quartile
  momentum / RPS context quartile
  tradability status

L1:
  drop momentum / RPS context quartile

L2:
  drop volatility quartile

L3:
  drop liquidity quartile

L4:
  coarsen industry bucket to sector / level-1 industry

L5:
  coarsen calendar year-quarter to calendar year
```

不得 drop：

```text
split
tradability status
entry-date asof feasibility
```

如果 L5 后仍不足 `minimum_matched_candidates_per_event`，该 event 必须标记为 unmatched，不得继续任意放宽到全市场 comparator。

runner 必须写出：

```text
reports/r05a_matched_comparator_spec_frozen.csv
reports/r05a_matched_comparator_audit.csv
```

`r05a_matched_comparator_spec_frozen.csv` 必需字段：

```text
comparator_rule_id
match_dimension
bucket_formula
bucket_formula_hash
fallback_order
minimum_candidates_per_event
with_replacement_flag
random_seed
asof_rule
```

`r05a_matched_comparator_audit.csv` 必需字段：

```text
pool_id
split
event_key
instrument_id
entry_execution_date
match_bucket_id
match_level_used
matched_candidate_count
matched_sample_count
fallback_used_flag
fallback_reason
matched_baseline_net_mean
matched_baseline_p10
matched_baseline_loss_le_5_rate
```

如果 fallback 过多，validator 不得允许 alpha pass。

建议 hard fail：

```text
validation_unmatched_event_share > 5%
validation_fallback_level_ge_3_share > 30%
```

## 12. Forward Return 与 Risk Metrics

每个 pool 必须输出 action-time forward path：

```text
T+1 / T+5 / T+20 / T+60 / T+120 net return
net_return_mean
net_return_median
net_return_p10 / p25 / p75 / p90
loss <= -5%
loss <= -10%
max_drawdown_20 / 60 / 120
max_gain_20 / 60 / 120
max_gain50_rate
right-tail retention
turnover
calendar / industry / instrument concentration
```

R05a v1 的 right-tail retention 公式固定为：

```text
right_tail_retention_ratio_120 =
  pool_max_gain50_rate_120 / matched_baseline_max_gain50_rate_120

if matched_baseline_max_gain50_rate_120 < 2%:
  use pool_max_gain50_rate_120 >= 1% as fallback right-tail floor
```

必需产物：

```text
cache/r05a_candidate_event_panel.parquet
cache/r05a_forward_path_panel.parquet
reports/r05a_pool_forward_return_summary.csv
reports/r05a_pool_distribution_summary.csv
reports/r05a_right_tail_left_tail_tradeoff.csv
reports/r05a_pool_pair_correlation_audit.csv
```

`r05a_pool_pair_correlation_audit.csv` 必需字段：

```text
pool_id_a
pool_id_b
split
event_overlap_rate
instrument_overlap_rate
calendar_day_overlap_rate
daily_return_correlation
matched_delta_correlation
joint_capacity_active_count_p95
joint_capacity_active_count_p99
```

如果一个 pool 只有 p90 或 `+50 rate` 好，但 median、p10、loss rate 差，它必须被标记为：

```text
right_tail_lottery_not_alpha
```

## 13. Cost / Capacity / Turnover

成本、turnover、capacity 必须在 discovery 阶段 binding。

### 13.1 Default Frozen Cost / Capacity Values

R05a v1 默认冻结值：

```text
base_round_trip_cost_bp = 50
capacity_slippage_stress_round_trip_bp = 25
capacity_adjusted_round_trip_cost_bp = 75
daily_candidate_count_p99_cap = 100
active_count_p95_cap = 500
per_name_participation_cap = 2% of prior 20d average daily money
turnover_event_count_20d_cap_per_instrument = 1
minimum_median_holding_days = 10
```

如果项目级 cost model 已经存在，runner 可以使用项目级 cost model，但必须在 `r05a_cost_capacity_spec_frozen.csv` 中记录，并同时输出上述 fallback cost 口径的 stress result。alpha pass 必须在 active cost model 与 fallback stress cost 两个口径下都不失败。

每个 pool 必须输出：

```text
daily candidate count
active count p95 / p99
turnover event count
median holding days
position notional vs money percentile
max participation rate assumption
capacity-adjusted slippage stress
```

必需产物：

```text
reports/r05a_cost_capacity_spec_frozen.csv
reports/r05a_cost_capacity_audit.csv
reports/r05a_turnover_capacity_gate_audit.csv
```

每个 validation result 必须同时报告：

```text
raw after-cost result
capacity-adjusted after-cost result
```

只要 capacity-adjusted 版本失败，就不能用 raw 版本 claim alpha。

建议 hard fail：

```text
daily_candidate_count_p99 > 100
active_count_p95 > 500
per_name_participation > 2% of prior 20d average daily money
turnover_event_count_20d_per_instrument > 1
median_holding_days < 10
capacity_adjusted_net_mean <= 0
```

## 14. Statistical Evidence Rule

点估计不能作为 pass 依据。R05a 必须输出：

```text
event bootstrap CI
calendar-week block bootstrap CI
calendar-month block bootstrap CI
year leave-one-out
industry leave-one-out
instrument concentration stress
```

### 14.1 Default Frozen Bootstrap Protocol

R05a v1 的 primary statistical evidence 必须使用 calendar-week block bootstrap。

默认冻结值：

```text
bootstrap_random_seed = 20260519
bootstrap_resamples = 5000
ci_level = 90%
ci_lower_quantile = 5%
ci_upper_quantile = 95%
primary_block_unit = calendar_week
primary_block_size = all events whose entry_execution_date falls in the same calendar week
secondary_block_unit = calendar_month
event_bootstrap_unit = event_key
```

证据优先级：

```text
primary:
  calendar-week block bootstrap

secondary:
  calendar-month block bootstrap
  event bootstrap sanity check
```

event bootstrap 只能作为 sanity check，不能单独支持 alpha pass，因为它会低估同日 / 同周横截面冲击相关性。

必需产物：

```text
reports/r05a_bootstrap_ci_summary.csv
reports/r05a_block_bootstrap_ci_summary.csv
reports/r05a_leave_one_out_summary.csv
reports/r05a_concentration_stress_audit.csv
```

validation pass 至少需要：

```text
validation net mean > 0
after-cost net mean block-bootstrap lower bound > 0
median > -0.50% at T+20 net return
p10 delta point estimate >= 0
p10 delta calendar-week block-bootstrap lower bound >= -1.00 percentage point
loss<=-5 delta point estimate < 0
loss<=-5 delta calendar-week block-bootstrap upper bound <= +2.00 percentage points
year_leave_one_out_positive_share >= 80%
industry_leave_one_out_positive_share >= 80%
```

如果样本太薄，导致 CI 无法稳定支持判断，结论必须是：

```text
insufficient_statistical_power
descriptive_lead_only
oos_retest_required
```

不能放宽门槛 claim alpha。

## 15. Structural Risk Audit

R05a 必须显式处理 A 股结构风险：

```text
survivorship bias
suspension path
limit-down buy/sell feasibility
ST / delisting status asof
regulatory event status asof
liquidity collapse
```

必需产物：

```text
reports/r05a_tradability_asof_audit.csv
reports/r05a_suspension_limit_down_audit.csv
reports/r05a_survivorship_structural_risk_audit.csv
```

禁止：

```text
exclude an event because later path became untradable
assume exit at unavailable limit-down / suspended price
use future ST / delisting status to filter entry
drop delisted instruments without explicit asof-executable rule
```

如果 implementation 暂时无法处理这些路径，final decision 不得为 alpha pass。

允许的最高结论是：

```text
execution_model_incomplete
descriptive_lead_only
```

## 16. Overlap 与 Low-Overlap Audit

R05a 必须证明新 pool 不是旧 RPS / family route 的窄子集。

对照对象：

```text
RPS candidate pool from R04
R04c selected descriptive leads
R02 family precision pools
R04e union pool, if available
```

必需产物：

```text
reports/r05a_overlap_with_prior_pools_audit.csv
reports/r05a_low_overlap_uniqueness_summary.csv
```

必需字段：

```text
pool_id
prior_pool_id
split
event_overlap_rate
instrument_overlap_rate
calendar_day_overlap_rate
industry_overlap_rate
overlap_net_mean
nonoverlap_net_mean
overlap_p10
nonoverlap_p10
```

如果 alpha evidence 主要来自与旧 pool 的 overlap 子集，不能 claim low-overlap alpha pool。

## 17. Market-State Return Decomposition

R05a 可以输出 market-state decomposition，但它不是 primary alpha gate。

必需产物：

```text
reports/r05a_market_state_return_decomposition.csv
```

必需字段：

```text
pool_id
split
market_state
active_days_share
event_count
gross_exposure_share
net_return_contribution
left_tail_contribution
right_tail_contribution
drawdown_contribution
risk_on_full_exposure_net
risk_on_full_exposure_validation_net
```

如果出现：

```text
risk_on_full_exposure_net <= 0
```

则任何 market-state exposure overlay 都不能进入 pass language。

如果 final report 对 market-state decomposition 有任何正向描述，必须以 `not_alpha` 标签结尾，例如：

```text
market_state_risk_control_lead_not_alpha
```

## 18. Mechanical Kill Criteria

每个 candidate pool 在 train 阶段冻结后，validation 只能跑一次。

kill criteria 必须在 validation 前写死：

```text
net mean floor
median floor
p10 delta floor
loss-rate delta ceiling
bootstrap CI rule
top1 year / industry / instrument concentration cap
daily candidate / active count cap
participation / capacity cap
turnover cap
fallback comparator cap
asof / tradability failure cap
```

### 18.1 Default Frozen Kill Values

R05a v1 默认 hard gate 数值：

```text
primary_decision_horizon = T+20 net return
validation_net_mean_floor = 0.00%
validation_median_floor = -0.50%
p10_delta_point_floor = 0.00 percentage point
p10_delta_week_block_lower_floor = -1.00 percentage point
loss_le_5_delta_point_ceiling = 0.00 percentage point
loss_le_5_delta_week_block_upper_ceiling = +2.00 percentage points
right_tail_retention_ratio_120_floor = 50%
right_tail_fallback_abs_max_gain50_rate_120_floor = 1%, if matched baseline max_gain50 rate < 2%
year_leave_one_out_positive_share_floor = 80%
industry_leave_one_out_positive_share_floor = 80%
top1_year_share_cap = 35%
top1_industry_share_cap = 35%
top1_instrument_share_cap = 10%
daily_candidate_count_p99_cap = 100
active_count_p95_cap = 500
per_name_participation_cap = 2% of prior 20d average daily money
turnover_event_count_20d_cap_per_instrument = 1
validation_unmatched_event_share_cap = 5%
validation_fallback_level_ge_3_share_cap = 30%
asof_tradability_hard_fail_count_cap = 0
bootstrap_resamples = 5000
bootstrap_ci_level = 90%
bootstrap_primary_block_unit = calendar_week
```

validation hard fail 条件：

```text
validation net mean <= 0
validation median < -0.50%
validation p10 < matched baseline p10
validation loss<=-5% >= matched baseline
after-cost net mean block-bootstrap lower bound <= 0
p10 delta calendar-week block-bootstrap lower bound < -1.00 percentage point
loss<=-5 delta point estimate >= 0
loss<=-5 delta calendar-week block-bootstrap upper bound > +2.00 percentage points
right_tail_retention_ratio_120 < 50%, if matched baseline max_gain50 rate >= 2%
pool_max_gain50_rate_120 < 1%, if matched baseline max_gain50 rate < 2%
year_leave_one_out_positive_share < 80%
industry_leave_one_out_positive_share < 80%
top1 year share > 35%
top1 industry share > 35%
top1 instrument share > 10%
daily candidate p99 > 100
active count p95 > 500
per-name participation > 2% of prior 20d average daily money
capacity-adjusted net mean <= 0
turnover_event_count_20d_per_instrument > 1
fallback level >= 3 event share > 30%
unmatched event share > 5%
asof / tradability audit fail
risk_on_full_exposure_validation_net <= 0, if market-state exposure overlay is claimed
```

如果失败：

```text
archive_candidate_pool
no threshold tuning
no validation bucket merge
no robustness rescue
no promote as alpha
no second validation pass with adjusted thresholds
```

允许的输出只有：

```text
alpha_pool_pass
relative_improvement_lead
descriptive_lead
archive_no_alpha
insufficient_statistical_power
execution_model_incomplete
oos_retest_required
```

## 19. Final Decision Rules

R05a final report 必须输出一个 workflow-level decision：

```text
r05a_alpha_pool_passed
r05a_relative_improvement_only
r05a_no_alpha_pool_passed_validation
r05a_insufficient_statistical_power
r05a_execution_model_incomplete
r05a_oos_retest_required
```

`r05a_alpha_pool_passed` 需要同时满足：

```text
at least one candidate pool passes validation hard gates
capacity-adjusted after-cost net mean > 0
block-bootstrap evidence passes
matched comparator evidence passes
right-tail retention floor passes
left-tail improvement passes
concentration stress passes
structural risk audit passes
no post-validation threshold tuning
```

如果 validation 失败但 robustness 转正，final decision 仍必须以 validation 为准：

```text
r05a_no_alpha_pool_passed_validation
```

robustness 只能作为 read-only evidence。

## 20. 必需报告结构

final report 路径：

```text
reports/r05a_alpha_pool_discovery_protocol_final_report.md
```

final report 必须包含：

1. Executive decision
2. R04/R04b/R04c/R04d/R04e upstream conclusion preservation
3. Candidate registry and frozen eight-tuple summary
4. Alpha pool vs relative improvement pool classification
5. Low-overlap audit
6. Matched comparator audit
7. Forward return distribution summary
8. Right-tail / left-tail tradeoff
9. Cost / capacity / turnover audit
10. Bootstrap / block-bootstrap evidence
11. Concentration and leave-one-out stress
12. As-of / look-ahead / structural risk audit
13. Market-state return decomposition, diagnostic only
14. Mechanical kill criteria audit
15. Final decision and allowed next steps

`Market-state return decomposition` 章节中的任何正向叙述都必须显式带 `not_alpha` 标签，不能在 Findings 或 Decision 中被写成 alpha evidence。

The report must explicitly write:

```text
R05a does not reinterpret R04c failed pools as alpha pools.
R05a does not reinterpret R04d failed policy as a policy pass.
R05a treats market-state exposure overlay as risk control, not alpha creation.
```

## 21. Literature Priors

R05a may cite literature only as research priors, not as pass evidence.

文献引用只能出现在 final report 的 `Research priors` 章节，不得出现在 `Findings`、`Decision` 或 `Passed evidence` 章节。

Allowed literature prior categories:

```text
low-vol / low-risk anomaly
momentum crash and market-state dependence
volatility-managed portfolios
residual momentum
52-week high
factor zoo / trading cost / overfitting controls
```

Examples:

- [The Volatility Effect in China](https://link.springer.com/article/10.1057/s41260-021-00218-0)
- [Betting Against Beta](https://www.nber.org/papers/w16601)
- [Momentum Crashes](https://www.nber.org/papers/w20439.pdf)
- [The 52-Week High and Momentum Investing](https://www.bauer.uh.edu/TGeorge/papers/gh4-paper.pdf)
- [Residual Momentum](https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf)
- [A Taxonomy of Anomalies and their Trading Costs](https://www.nber.org/papers/w20721)
- [Taming the Factor Zoo](https://www.nber.org/papers/w25481)

Final report 不得写：

```text
literature supports alpha pass
published anomaly proves this pool works
```

只能写：

```text
literature prior motivates this test
local validation evidence determines pass/fail
```

## 22. 后续路线

如果 R05a 没有 alpha pass：

```text
停止扩大 RPS / family / momentum threshold search。
将现有 signals 降级为 lifecycle tags / relative-improvement sleeves / risk overlays。
不再用 cash sleeve 或 exit insurance 解释为主 alpha。
```

如果 R05a 有 alpha pass：

```text
新开 R05b portfolio construction / risk overlay requirement。
R05b 只能使用 R05a passed frozen pool。
R05b 不能重新选择 R05a thresholds。
R05b 入口前必须执行 OOS roll-forward retest，标准与 R05a validation gate 相同。
如果多个 pool pass，必须先做 pair-overlap / return-correlation / joint-capacity audit。
```

如果 R05a 是 `insufficient_statistical_power`：

```text
只能扩大样本或延长 OOS，
不能调参重跑 validation。
```
