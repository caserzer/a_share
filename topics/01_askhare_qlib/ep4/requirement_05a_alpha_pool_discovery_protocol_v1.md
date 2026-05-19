# EP4 需求 05a: Alpha Pool Discovery Protocol V1

## 1. 需求元信息

- 需求 id: `ep4_r05a_alpha_pool_discovery_protocol_v1`
- 简称: `r05a_alpha_pool_discovery_protocol_v1`
- 状态: abandoned / preflight-blocked，不再作为 active implementation requirement
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion5.md`
- 上游 R04 需求: `ep4/requirement_04_dynamic_momentum_exposure_eligibility_audit_v1.md`
- 上游 R04b 需求: `ep4/requirement_04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.md`
- 上游 R04c 需求: `ep4/requirement_04c_candidate_pool_scanner_v1.md`
- 上游 R04d 需求: `ep4/requirement_04d_volume_money_relative_improvement_risk_budget_replay_v1.md`
- 上游 R04e 需求: `ep4/requirement_04e_union_pool_portfolio_level_diagnostic_v1.md`
- 上游 R05 Preflight 需求: `ep4/requirement_05_preflight_alpha_pool_quick_feasibility_v1.md`
- 必需输出根目录: `ep4/outputs/r05a_alpha_pool_discovery_protocol_v1/`
- 必需 config 路径: `ep4/configs/r05a_alpha_pool_discovery_protocol_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r05a_alpha_pool_discovery_protocol.py`
- 必需 validator 路径: `ep4/scripts/validate_r05a_alpha_pool_discovery_protocol.py`
- 日期: 2026-05-19

### 1.1 Abandonment Note

R05a 已被 R05 Preflight 前置门阻断，不再作为 active implementation requirement。

R05 Preflight 当前结果：

```text
validation_status = passed
final_decision = r05_preflight_stop_no_absolute_floor
candidate_pass_count = 0
allowed_next_requirement = sleeve_allocator_direction_requirement
```

因此本文只作为被否决的 full protocol draft 保留，用于记录当时的 alpha discovery 设计边界。不得在当前证据状态下继续实现 R05a runner / validator，也不得绕过 R05 Preflight gate 重新启用 full protocol。

下一份 active requirement 应转向：

```text
sleeve_allocator_direction_requirement
```

### 1.2 Data / Split / Upstream Artifact Contract

R05a 必须继承 EP4 R04 系列已经使用的 split，不允许 runner 自行改日期：

```text
train_start = 2017-07-04
train_end = 2021-12-31
validation_start = 2022-01-01
validation_end = 2023-12-31
robustness_start = 2024-01-01
robustness_end = 2025-12-31
```

R05a config 必须显式写入同一组日期。validator 必须检查 config 日期与本需求完全一致；任何 drift 都是 fatal。

R05a 必须使用以下本地数据源：

```text
price_provider.provider_type = qlib_pit_local
price_provider.price_source_path = data/qlib/cn_data_pit
price_provider.calendar_source_path = data/qlib/cn_data_pit/calendars/day.txt
price_provider.instrument_source_path = data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt
price_provider.required_qlib_fields = ["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"]
price_provider.adjustment_policy = qlib_adjusted_ohlc_fields

local_inputs.pit_industry_membership = data/targets/pit_industry_membership.csv
```

R05a 必须把以下 upstream artifact 写入 config，并在 validator 中逐项检查存在、schema、manifest validation status：

```text
upstream_r04.validation =
  ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_validation.json
upstream_r04.rps_candidate_pool =
  ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_rps_candidate_action_panel.parquet

upstream_r02_family.validation =
  ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_validation.json
upstream_r02_family.action_time_panel =
  ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet

upstream_r04c.validation =
  ep4/outputs/r04c_candidate_pool_scanner_v1/manifests/r04c_candidate_pool_scanner_validation.json
upstream_r04c.pool_event_panel =
  ep4/outputs/r04c_candidate_pool_scanner_v1/cache/r04c_pool_event_panel.parquet
upstream_r04c.pool_registry_frozen =
  ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_pool_registry_frozen.csv
upstream_r04c.final_decision =
  ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_final_decision.csv

upstream_r04d.validation =
  ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/manifests/r04d_volume_money_relative_improvement_risk_budget_validation.json
upstream_r04d.final_decision =
  ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/reports/r04d_final_decision.csv

upstream_r04e.validation =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/manifests/r04e_union_pool_portfolio_level_validation.json
upstream_r04e.union_event_panel =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_union_event_panel.parquet
upstream_r04e.final_decision =
  ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/reports/r04e_final_decision.csv

upstream_r05_preflight.validation =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json
upstream_r05_preflight.final_decision =
  ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_final_decision.csv
```

R04e is mandatory for R05a. 如果 R04e validation artifact 不存在或不是 `passed`，R05a runner 必须停止，validator 必须输出 fatal failure；不能降级为 `if available`。

R05 Preflight is mandatory for R05a. 如果 R05 Preflight validation status 不是 `passed`，或 R05 Preflight final decision 不是：

```text
r05_preflight_go_r05a_full_protocol
```

R05a runner 必须停止，validator 必须 fail closed。R05a 不允许在 preflight stop / insufficient sample / execution blocked 状态下继续执行 full protocol。

如果 R05 Preflight final decision 是 `r05_preflight_go_r05a_full_protocol`，R05a 只能启用 `reports/r05_preflight_final_decision.csv` 中的 `passed_candidate_families`。未通过 preflight 的 candidate family 可以保留在 formula grid 中用于审计，但必须标记为：

```text
preflight_blocked_not_allowed_in_r05a
```

且不得进入 train selection 或 validation。

R05a 必须输出标准 manifest / validation artifacts：

```text
manifests/r05a_alpha_pool_discovery_protocol_manifest.json
manifests/r05a_alpha_pool_discovery_protocol_validation.json
reports/r05a_alpha_pool_discovery_protocol_validation_audit.csv
```

`r05a_alpha_pool_discovery_protocol_manifest.json` 必需字段：

```text
requirement_id
requirement_path
config_path
output_root
created_at
split_definition_hash
price_provider_hash
upstream_artifact_hashes_json
frozen_formula_grid_hash
frozen_rule_registry_hash
frozen_candidate_registry_hash
final_decision
artifact_hashes_json
```

`r05a_alpha_pool_discovery_protocol_validation.json` 必需字段：

```text
validation_status
failed_checks
warning_checks
final_decision
selected_pool_ids
created_at
audit_path
manifest_path
```

`r05a_alpha_pool_discovery_protocol_validation_audit.csv` 必需字段：

```text
check_id
check_name
severity
status
details
artifact_path
```

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
  enumerate the pre-registered finite formula grid only
  compute train-only metrics
  select at most one validation candidate per candidate_family

validation:
  confirm train-selected frozen candidates only
  no threshold adjustment
  no new bucket merge
  no reverse selection

robustness:
  read-only final readout
```

R05a v1 不允许 free-form primitive search。所有公式、阈值、搜索空间、selection score、tie-breaker 必须在 `reports/r05a_candidate_formula_grid_frozen.csv` 中先于任何 train outcome 写死。

如果 train 阶段没有任何 candidate 满足 train eligibility，runner 仍必须输出 registry、train audit、空 validation audit 和 final report。workflow-level final decision 必须是：

```text
r05a_no_alpha_pool_passed_validation
```

不能因为 train 阶段无候选而临时扩大 grid。

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

R05a v1 只允许三个 primary candidate universes：

```text
low_vol_uptrend
base_breakout_vcp
cross_sectional_low_beta_low_vol
```

上述列表是 R05a 的 maximum allowed candidate universe。实际进入 train selection 的 candidate families 必须是该列表与 R05 Preflight `passed_candidate_families` 的交集。

每个 candidate universe 只能展开为预注册公式 grid 中的有限 variants：

```text
max_variants_per_candidate_family = 8
max_validation_selected_pools_per_candidate_family = 1
max_total_validation_selected_pools = 3
default_n_jobs = 12
random_seed = 20260519
```

train selection 必须使用固定排序：

```text
eligible first:
  train_complete_event_count >= 500
  train_matched_event_share >= 95%
  train_capacity_adjusted_net_mean_t20 > 0
  train_p10_delta_t20 >= 0
  train_loss_le_5_delta_t20 < 0

sort descending:
  train_capacity_adjusted_net_mean_t20
  train_p10_delta_t20
  train_right_tail_retention_ratio_120

sort ascending:
  train_daily_candidate_count_p99
  pool_id
```

validation 只能使用上述排序选出的 frozen pools。robustness 不能改变 selected pool。

原因：

```text
1. 与现有 RPS / family universe overlap 预期较低。
2. primitive 容易做严格 as-of 冻结。
3. 文献先验支持 low-vol / structured momentum / low-beta 方向。
4. 不直接依赖 post-event survival 或 winner label。
5. `cross_sectional_low_beta_low_vol` 在机制上不同于 continuation momentum，用于避免 R05a v1 只测试同一 long-only momentum 范式。
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

## 7. Candidate Formula Grid 与 Pool Registry

R05a runner 必须在任何 train outcome 计算前冻结完整 candidate formula grid，并写入：

```text
reports/r05a_candidate_formula_grid_frozen.csv
reports/r05a_rule_registry_frozen.csv
```

`r05a_candidate_formula_grid_frozen.csv` 必需字段：

```text
pool_id
pool_name
candidate_family
variant_id
formula_text
formula_hash
parameter_json
grid_rank_order
train_selection_allowed
validation_selection_allowed_before_train
status_before_train
```

train selection 完成后、validation 开始前，runner 必须冻结 selected candidate pool registry，并写入：

```text
reports/r05a_candidate_pool_registry_frozen.csv
reports/r05a_rule_registry_frozen.csv
reports/r05a_train_selection_trace.csv
```

`r05a_candidate_pool_registry_frozen.csv` 必须包含所有 grid variants。每个 candidate pool 必须带固定八元组：

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

`status` 只允许：

```text
grid_candidate
train_selected_validation_frozen
train_rejected_sample
train_rejected_metric
train_rejected_capacity
train_rejected_comparator
preflight_blocked_not_allowed_in_r05a
```

`r05a_train_selection_trace.csv` 必需字段：

```text
pool_id
candidate_family
split
train_complete_event_count
train_matched_event_share
train_capacity_adjusted_net_mean_t20
train_p10_delta_t20
train_loss_le_5_delta_t20
train_right_tail_retention_ratio_120
train_daily_candidate_count_p99
train_eligibility_status
selection_rank
selected_for_validation_flag
rejection_reason
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
- candidate formula grid 缺失；
- train selection trace 缺失；
- rule registry 缺失；
- 公式没有 hash；
- registry 中没有八元组任一元素；
- grid 中出现未注册 candidate family；
- grid 中每个 candidate family 超过 8 个 variants；
- validation selected pool 超过每个 family 1 个或总数 2 个；
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

通用 price-derived feature 公式必须固定：

```text
log_return_t = ln(close_t / close_{t-1})
true_range_t =
  max(
    high_t - low_t,
    abs(high_t - close_{t-1}),
    abs(low_t - close_{t-1})
  )
pct_rank values use deterministic average-rank tie handling
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

cross-sectional beta:
  market return must be computed from the same tradable instrument universe as of D
  beta window must end at D close
  beta rank must be same-day cross-sectional rank, no future benchmark composition
```

## 9. Candidate Universe Definition Requirements

### 9.1 Low-Vol Uptrend

`low_vol_uptrend` 的 as-of features 必须全部由 `decision_date = D` 收盘及以前的数据计算：

```text
close_D
ma20_D = mean(close[D-19:D])
ma60_D = mean(close[D-59:D])
ma120_D = mean(close[D-119:D])
ret1_D = close_D / close[D-1] - 1
ret20_D = close_D / close[D-20] - 1
ret60_D = close_D / close[D-60] - 1
realized_vol60_D = std(log_return[D-59:D])
atr20_pct_D = mean(true_range[D-19:D]) / close_D
avg_money20_D = mean(money[D-19:D])
money_ratio5_to20_D = mean(money[D-4:D]) / avg_money20_D
avg_money20_rank_pct_D = same-day cross-sectional pct_rank(avg_money20_D)
realized_vol60_rank_pct_D = same-day cross-sectional pct_rank(realized_vol60_D)
```

`low_vol_uptrend` 的 pre-registered grid 固定为：

```text
base_conditions:
  close_D > ma120_D
  ma60_D > ma120_D
  ret60_D >= 0
  close_D >= ma60_D * 0.98
  avg_money20_rank_pct_D >= min_avg_money20_rank_pct
  realized_vol60_rank_pct_D <= max_realized_vol60_rank_pct
  abs(close_D / ma20_D - 1) <= max_abs_close_to_ma20_pct
  atr20_pct_D <= 0.08
  money_ratio5_to20_D <= max_money_ratio5_to20
  abs(ret1_D) <= max_abs_ret1

grid:
  max_realized_vol60_rank_pct in [0.40, 0.50]
  max_abs_close_to_ma20_pct in [0.10, 0.12]
  min_avg_money20_rank_pct in [0.30]
  max_money_ratio5_to20 in [2.50]
  max_abs_ret1 in [0.08]

variant_count = 4
```

每个 grid combination 生成一个 `pool_id`：

```text
low_vol_uptrend__vol{max_realized_vol60_rank_pct}__ext{max_abs_close_to_ma20_pct}
```

该 pool 的目标不是最高 big-winner rate，而是：

```text
right-tail remains
left-tail naturally lighter
after-cost validation net positive
```

### 9.2 Base Breakout / VCP

`base_breakout_vcp` 的 as-of features 必须全部由 `decision_date = D` 收盘及以前的数据计算：

```text
base_length in [20, 40]
base_high_D = max(high[D-base_length:D-1])
base_low_D = min(low[D-base_length:D-1])
base_drawdown_pct_D = base_low_D / base_high_D - 1
breakout_ret_pct_D = close_D / base_high_D - 1
pre_base_vol20_D = std(log_return[D-base_length:D-1])
recent_vol10_D = std(log_return[D-9:D])
vol_contraction_ratio_D = recent_vol10_D / pre_base_vol20_D
ma20_D = mean(close[D-19:D])
atr20_pct_D = mean(true_range[D-19:D]) / close_D
avg_money20_D = mean(money[D-19:D])
money_ratio5_to20_D = mean(money[D-4:D]) / avg_money20_D
avg_money20_rank_pct_D = same-day cross-sectional pct_rank(avg_money20_D)
```

`base_breakout_vcp` 的 pre-registered grid 固定为：

```text
base_conditions:
  base_drawdown_pct_D >= -max_base_drawdown_pct
  breakout_ret_pct_D >= min_breakout_buffer_pct
  breakout_ret_pct_D <= 0.08
  vol_contraction_ratio_D <= 0.80
  abs(close_D / ma20_D - 1) <= 0.12
  atr20_pct_D <= 0.10
  money_ratio5_to20_D >= 1.10
  money_ratio5_to20_D <= 2.50
  avg_money20_rank_pct_D >= 0.30

grid:
  base_length in [20, 40]
  max_base_drawdown_pct in [0.12, 0.15]
  min_breakout_buffer_pct in [0.00, 0.02]

variant_count = 8
breakout_confirmed_by = D close
earliest_entry = D+1 tradable open
```

每个 grid combination 生成一个 `pool_id`：

```text
base_breakout_vcp__len{base_length}__dd{max_base_drawdown_pct}__buf{min_breakout_buffer_pct}
```

禁止：

```text
using post-entry high to define breakout
using future base boundary
using future max gain to confirm VCP
using entry-day volume for D+1 open decision
```

### 9.3 Cross-Sectional Low Beta / Low Vol

`cross_sectional_low_beta_low_vol` 的 as-of features 必须全部由 `decision_date = D` 收盘及以前的数据计算：

```text
market_log_return_t =
  equal-weight mean of log_return_t across tradable instrument universe

beta120_D =
  cov(stock_log_return[D-119:D], market_log_return[D-119:D])
  / var(market_log_return[D-119:D])

beta120_rank_pct_D =
  same-day cross-sectional pct_rank(beta120_D)

realized_vol60_D = std(log_return[D-59:D])
realized_vol60_rank_pct_D = same-day cross-sectional pct_rank(realized_vol60_D)
avg_money20_D = mean(money[D-19:D])
avg_money20_rank_pct_D = same-day cross-sectional pct_rank(avg_money20_D)
money_ratio5_to20_D = mean(money[D-4:D]) / avg_money20_D
ma120_D = mean(close[D-119:D])
ret1_D = close_D / close[D-1] - 1
ret20_D = close_D / close[D-20] - 1
atr20_pct_D = mean(true_range[D-19:D]) / close_D
```

`cross_sectional_low_beta_low_vol` 的 pre-registered grid 固定为：

```text
base_conditions:
  beta120_rank_pct_D <= max_beta120_rank_pct
  realized_vol60_rank_pct_D <= max_realized_vol60_rank_pct
  avg_money20_rank_pct_D >= 0.30
  close_D >= ma120_D * 0.95
  ret20_D >= min_ret20
  money_ratio5_to20_D <= 2.00
  abs(ret1_D) <= 0.08
  atr20_pct_D <= 0.08

grid:
  max_beta120_rank_pct in [0.35, 0.45]
  max_realized_vol60_rank_pct in [0.40, 0.50]
  min_ret20 in [-0.03, 0.00]

variant_count = 8
```

每个 grid combination 生成一个 `pool_id`：

```text
cross_sectional_low_beta_low_vol__beta{max_beta120_rank_pct}__vol{max_realized_vol60_rank_pct}__ret20{min_ret20}
```

该 pool 的目标是测试机制上不同于 RPS / continuation momentum 的 low-beta / low-vol cross-sectional risk-premium candidate。它不得使用 market-state exposure overlay 作为 entry filter，也不得把低 beta 暴露解释为 standalone alpha；是否 alpha 仍由 validation net、matched comparator、capacity-adjusted、bootstrap 和 structural-risk gate 决定。

## 10. Event Collapse 与 Sample Construction

同一 `pool_id + instrument_id` 在短窗口内重复触发，必须按 frozen collapse rule 处理。

默认 collapse rule：

```text
collapse_window_trading_days:
  low_vol_uptrend = 20
  base_breakout_vcp = 10
  cross_sectional_low_beta_low_vol = 20
keep first event within collapse window
next eligible event must be after prior entry_execution_date + collapse_window
```

这是 R05a v1 的保守取舍，不代表最优事件间隔。`low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` 用 20 天近似月度状态再入场，`base_breakout_vcp` 用 10 天允许较快的二次 breakout 事件。任何 universe-specific collapse window search 都必须进入 R05a v2，不能在 R05a validation 后调整。

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

### 11.1 Bucket Formula Contract

R05a v1 的 matched bucket formulas 必须固定如下，不能由 runner 自行解释：

```text
calendar_year_quarter =
  year(entry_execution_date) + "Q" + quarter(entry_execution_date)

industry_bucket =
  asof industry_target_key from data/targets/pit_industry_membership.csv
  using latest membership date <= decision_date
  if missing: "UNKNOWN"

sector_bucket =
  first-level industry / sector field if available
  otherwise industry_bucket

liquidity_quartile =
  same decision_date cross-sectional quartile of avg_money20_D
  within tradable instrument universe

volatility_quartile =
  same decision_date cross-sectional quartile of realized_vol60_D
  within tradable instrument universe

momentum_rps_context_quartile =
  same decision_date cross-sectional quartile of ret20_D
  within tradable instrument universe

market_regime_bucket =
  market_ret60_bucket + "__" + market_vol20_bucket

market_ret60 =
  equal-weight mean of close_D / close[D-60] - 1
  across tradable instrument universe on D

market_vol20 =
  std of daily equal-weight market log return over D-19:D
```

`market_ret60_bucket` 和 `market_vol20_bucket` 的 bucket edges 必须只用 train split 计算，然后冻结到：

```text
reports/r05a_bucket_edge_registry_frozen.csv
```

`r05a_bucket_edge_registry_frozen.csv` 必需字段：

```text
bucket_id
bucket_dimension
edge_source_split
edge_formula
edge_formula_hash
lower_bound
upper_bound
bucket_label
```

默认 bucket edge：

```text
market_ret60_bucket:
  train terciles of market_ret60

market_vol20_bucket:
  train terciles of market_vol20
```

所有 same-day cross-sectional quartiles 只使用 `decision_date` 当日可交易且特征完整的股票，不得跨 split 学习边界。

### 11.2 Default Matched Comparator Fallback Ladder

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
reports/r05a_bucket_edge_registry_frozen.csv
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

validator hard fail：

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

`r05a_candidate_event_panel.parquet` 必需字段：

```text
pool_id
candidate_family
variant_id
instrument_id
decision_date
entry_execution_date
entry_price
split
event_key
kept_event_flag
formula_hash
```

`r05a_forward_path_panel.parquet` 必需字段：

```text
pool_id
split
event_key
instrument_id
entry_execution_date
horizon
exit_date
exit_price
gross_return
net_return
capacity_adjusted_net_return
max_drawdown
max_gain
path_complete_flag
path_censor_reason
```

`r05a_pool_forward_return_summary.csv` 必需字段：

```text
pool_id
candidate_family
split
horizon
event_count
complete_event_count
net_return_mean
capacity_adjusted_net_return_mean
net_return_median
net_return_p10
net_return_p25
net_return_p75
net_return_p90
loss_le_5_rate
loss_le_10_rate
max_gain50_rate
```

`r05a_pool_distribution_summary.csv` 必需字段：

```text
pool_id
split
horizon
metric_name
pool_value
matched_baseline_value
delta_vs_matched
sample_count
```

`r05a_right_tail_left_tail_tradeoff.csv` 必需字段：

```text
pool_id
split
right_tail_retention_ratio_120
pool_max_gain50_rate_120
matched_baseline_max_gain50_rate_120
p10_delta_t20
loss_le_5_delta_t20
classification
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

`r05a_cost_capacity_spec_frozen.csv` 必需字段：

```text
cost_rule_id
capacity_rule_id
base_round_trip_cost_bp
capacity_slippage_stress_round_trip_bp
capacity_adjusted_round_trip_cost_bp
daily_candidate_count_p99_cap
active_count_p95_cap
per_name_participation_cap
turnover_event_count_20d_cap_per_instrument
minimum_median_holding_days
spec_hash
```

`r05a_cost_capacity_audit.csv` 必需字段：

```text
pool_id
split
horizon
raw_after_cost_net_mean
capacity_adjusted_net_mean
capacity_adjusted_delta
daily_candidate_count_p99
active_count_p95
active_count_p99
per_name_participation_p95
capacity_gate_status
blocking_reason
```

`r05a_turnover_capacity_gate_audit.csv` 必需字段：

```text
pool_id
split
instrument_id
event_count_20d_max
median_holding_days
turnover_event_count_20d_cap_per_instrument
turnover_gate_status
capacity_gate_status
```

每个 validation result 必须同时报告：

```text
raw after-cost result
capacity-adjusted after-cost result
```

只要 capacity-adjusted 版本失败，就不能用 raw 版本 claim alpha。

validator hard fail：

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

`r05a_bootstrap_ci_summary.csv` 必需字段：

```text
pool_id
split
horizon
bootstrap_unit
metric_name
point_estimate
ci_level
ci_lower
ci_upper
resamples
random_seed
```

`r05a_block_bootstrap_ci_summary.csv` 必需字段：

```text
pool_id
split
horizon
block_unit
metric_name
point_estimate
ci_level
ci_lower
ci_upper
resamples
random_seed
primary_evidence_flag
gate_status
```

`r05a_leave_one_out_summary.csv` 必需字段：

```text
pool_id
split
leave_one_out_dimension
left_out_key
remaining_event_count
capacity_adjusted_net_mean_t20
p10_delta_t20
loss_le_5_delta_t20
positive_flag
```

`r05a_concentration_stress_audit.csv` 必需字段：

```text
pool_id
split
top1_year_share
top1_industry_share
top1_instrument_share
year_leave_one_out_positive_share
industry_leave_one_out_positive_share
instrument_concentration_gate_status
blocking_reason
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

R05a config 必须显式声明 structural-risk data source：

```text
structural_risk_sources.asof_stock_status_path
structural_risk_sources.asof_st_flag_path
structural_risk_sources.asof_delisting_path
structural_risk_sources.asof_suspension_path
structural_risk_sources.asof_regulatory_event_path
```

如果上述 source 任一缺失，runner 仍可执行 price-inferred audit，但 final decision 不得为 `r05a_alpha_pool_passed`。workflow-level final decision 最高只能是：

```text
r05a_execution_model_incomplete
```

price-inferred fallback 必须固定为：

```text
mainboard_limit_pct = 9.5%
entry_open_unavailable_flag =
  next_open is null OR next_open <= 0 OR next_volume is null OR next_money is null

entry_limit_up_block_flag =
  next_open >= close_D * (1 + mainboard_limit_pct)

exit_limit_down_block_flag on exit_date X =
  open_X <= close_prev_tradable * (1 - mainboard_limit_pct)

suspension_inferred_flag =
  open/high/low/close/money/volume missing OR money <= 0 OR volume <= 0
```

当 exit date 不可执行时，runner 必须使用保守 lag policy：

```text
max_exit_execution_lag_trading_days = 5
if exit still unavailable after lag:
  mark path as structurally_blocked
  include event in denominator
  do not impute a favorable exit
```

必需产物：

```text
reports/r05a_tradability_asof_audit.csv
reports/r05a_suspension_limit_down_audit.csv
reports/r05a_survivorship_structural_risk_audit.csv
```

`r05a_tradability_asof_audit.csv` 必需字段：

```text
pool_id
split
event_key
instrument_id
decision_date
entry_execution_date
entry_open_unavailable_flag
entry_limit_up_block_flag
tradability_source_status
tradability_audit_pass
failure_reason
```

`r05a_suspension_limit_down_audit.csv` 必需字段：

```text
pool_id
split
event_key
instrument_id
planned_exit_date
actual_exit_date
exit_execution_lag_trading_days
suspension_inferred_flag
exit_limit_down_block_flag
structurally_blocked_flag
denominator_retained_flag
```

`r05a_survivorship_structural_risk_audit.csv` 必需字段：

```text
source_name
source_path
source_available_flag
asof_coverage_start
asof_coverage_end
missing_instrument_share
missing_event_share
alpha_pass_allowed_flag
forced_final_decision_if_missing
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
R04e union pool
```

R04e union pool 是 mandatory comparator。validator 必须检查 `upstream_r04e.union_event_panel` 存在，且 R04e final decision 保持：

```text
r04e_union_not_viable_validation
```

R05a 的 low-overlap pass gate 固定为：

```text
validation_exact_event_overlap_rate_vs_each_prior_pool <= 20%
validation_nearby_5d_event_overlap_rate_vs_each_prior_pool <= 35%
validation_calendar_day_overlap_rate_vs_each_prior_pool <= 60%
validation_instrument_overlap_rate_vs_each_prior_pool <= 70%
validation_nonoverlap_event_share >= 65%
validation_nonoverlap_net_mean_t20 > 0, if claiming alpha
validation_nonoverlap_p10_delta_t20 >= 0, if claiming alpha
```

事件 overlap 定义：

```text
exact_event_overlap:
  same instrument_id
  same entry_execution_date

nearby_5d_event_overlap:
  same instrument_id
  abs(candidate_entry_execution_date - prior_entry_execution_date) <= 5 trading days
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
exact_event_overlap_rate
nearby_5d_event_overlap_rate
instrument_overlap_rate
nonoverlap_event_share
overlap_net_mean
nonoverlap_net_mean
overlap_p10
nonoverlap_p10
```

如果 alpha evidence 主要来自与旧 pool 的 overlap 子集，不能 claim low-overlap alpha pool。

如果任一 prior pool 的 low-overlap pass gate 失败，pool-level status 必须是：

```text
overlap_blocked_existing_route
```

该 pool 不得支持 `r05a_alpha_pool_passed`。

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
entry_execution_unavailable_share_cap = 5%
exit_structurally_blocked_share_cap = 2%
exact_event_overlap_rate_vs_each_prior_pool_cap = 20%
nearby_5d_event_overlap_rate_vs_each_prior_pool_cap = 35%
nonoverlap_event_share_floor = 65%
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
entry execution unavailable share > 5%
exit structurally blocked share > 2%
structural risk source missing, if claiming alpha
exact event overlap vs any prior pool > 20%
nearby 5d event overlap vs any prior pool > 35%
instrument overlap vs any prior pool > 70%
nonoverlap event share < 65%
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

runner 必须同时写出：

```text
reports/r05a_final_decision.csv
reports/r05a_pool_decision_audit.csv
```

`r05a_final_decision.csv` 必需字段：

```text
requirement_id
final_decision
selected_pool_ids
blocking_reason
validation_alpha_pool_count
created_at
```

`r05a_pool_decision_audit.csv` 必需字段：

```text
pool_id
candidate_family
train_selection_status
validation_gate_status
capacity_gate_status
matched_comparator_gate_status
low_overlap_gate_status
structural_risk_gate_status
bootstrap_gate_status
concentration_gate_status
pool_final_status
blocking_reason
```

`r05a_alpha_pool_passed` 需要同时满足：

```text
at least one candidate pool passes validation hard gates
capacity-adjusted after-cost net mean > 0
block-bootstrap evidence passes
matched comparator evidence passes
low-overlap evidence passes against R04 / R02 / R04c / R04e
right-tail retention floor passes
left-tail improvement passes
concentration stress passes
structural risk audit passes
all structural-risk asof sources available
no post-validation threshold tuning
```

如果 validation 失败但 robustness 转正，final decision 仍必须以 validation 为准：

```text
r05a_no_alpha_pool_passed_validation
```

robustness 只能作为 read-only evidence。

如果 no candidate 在 train 阶段入选 validation，final decision 必须是：

```text
r05a_no_alpha_pool_passed_validation
```

如果 validation hard gates 全部通过，但 low-overlap gate 或 structural-risk source gate 失败，final decision 不得是 `r05a_alpha_pool_passed`，并且 final report 必须在 decision 章节写出 blocking reason。

## 20. 必需报告结构

final report 路径：

```text
reports/r05a_alpha_pool_discovery_protocol_final_report.md
```

final report 必须包含：

1. Executive decision
2. R05 Preflight gate result
3. R04/R04b/R04c/R04d/R04e upstream conclusion preservation
4. Data / split / upstream artifact contract
5. Candidate formula grid and train selection trace
6. Candidate registry and frozen eight-tuple summary
7. Alpha pool vs relative improvement pool classification
8. Low-overlap audit
9. Matched comparator audit
10. Forward return distribution summary
11. Right-tail / left-tail tradeoff
12. Cost / capacity / turnover audit
13. Bootstrap / block-bootstrap evidence
14. Concentration and leave-one-out stress
15. As-of / look-ahead / structural risk audit
16. Market-state return decomposition, diagnostic only
17. Mechanical kill criteria audit
18. Final decision and allowed next steps

`Market-state return decomposition` 章节中的任何正向叙述都必须显式带 `not_alpha` 标签，不能在 Findings 或 Decision 中被写成 alpha evidence。

The report must explicitly write:

```text
R05a does not reinterpret R04c failed pools as alpha pools.
R05a does not reinterpret R04d failed policy as a policy pass.
R05a treats market-state exposure overlay as risk control, not alpha creation.
R05a only runs after R05 Preflight permits the full protocol.
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

如果 R05 Preflight validation status 不是 `passed`，或没有给出 `r05_preflight_go_r05a_full_protocol`：

```text
不得执行 R05a full protocol。
不得通过换另一组 primitive 绕过 preflight。
下一份 requirement 只能转向 sleeve_allocator_direction_requirement、sample_extension_only 或 execution_model_repair_only。
```

如果 R05a 没有 alpha pass：

```text
停止扩大 RPS / family / momentum threshold search。
将现有 signals 降级为 lifecycle tags / relative-improvement sleeves / risk overlays。
不再用 cash sleeve 或 exit insurance 解释为主 alpha。
下一步默认转向 sleeve allocator / exposure / inventory 方向，而不是 R05b 换 primitive。
```

如果 R05a 有 alpha pass：

```text
新开 R05b portfolio construction / risk overlay requirement。
R05b 只能使用 R05a passed frozen pool。
R05b 不能重新选择 R05a thresholds。
R05b 入口前必须执行 OOS roll-forward retest，标准与 R05a validation gate 相同。
如果多个 pool pass，必须先做 pair-overlap / return-correlation / joint-capacity audit。
如果只有 `cross_sectional_low_beta_low_vol` pass，R05b 必须把 low-beta exposure decomposition 与 alpha evidence 分开报告。
```

如果 R05a 是 `insufficient_statistical_power`：

```text
只能扩大样本或延长 OOS，
不能调参重跑 validation。
```
