# Explore9 扩展需求 7：P0.9B 行业 LGBM 机制解释与手工 Primitive 转写 Probe

> 文件名：`requirement_p0_9b.md`
> 阶段：`P0.9B`
> 标题：Industry LGBM-to-Primitive Translation Probe
> 状态：implementation-ready requirement draft
> 生成日期：2026-05-06

---

## 0. 一句话结论

P0.9B 不训练一个可部署的行业 LGBM，也不比较哪个 LGBM 参数更好。

P0.9B 只做一件事：

```text
在 P0.9A 已经确认可训练的 汽车 / 电子 + T1 合同下，
把 locked T1 LGBM 当成 diagnostic probe，
反向提取稳定、可解释、可审计、可转写的行业内 primitive，
为下一阶段 P0.9C 手工 industry gate / formula discovery 提供候选结构。
```

P0.9B 的主线不是：

```text
parameter-regime model comparison
best LGBM search
score bucket selection
P1 candidate promotion
Explore10 backtest
strategy freeze
```

P0.9B 的主线是：

```text
sample-weight guardrail resolution
-> locked T1 model mechanism extraction
-> feature-family / slice / null / placebo audit
-> manual primitive translation
-> P0.9C requirement map
```

P0.9B 可以输出：

```text
diagnostic_probe_signal_present
diagnostic_probe_signal_absent
diagnostic_probe_signal_uninterpretable
manual_primitive_candidate_for_p0_9c
primitive_rejected_due_to_null_or_placebo
primitive_rejected_due_to_concentration
blocked_by_weight_guardrail
```

P0.9B 禁止输出：

```text
candidate_for_industry_p1_refine = true
validated_model = true
clean_oos_proven_rule = true
selected_lgbm_params
selected_score_bucket
actionable_trade_rule
proceed_to_explore10_backtest = true
freeze_strategy = true
```

---

## 1. 背景与阶段来源

### 1.1 P0.9 的结论

P0.9 证明：原始行业专用 LGBM 合同在固定 9 行业、2 个任务、purged expanding walk-forward 与严格 inner-validation gate 下不可训练。所有 industry / task / fold trainability 组合均失败。因此 P0.9 不是 performance rejection，而是 trainability failure。

P0.9 的正确解释是：

```text
行业专用 LGBM 方向没有被收益指标否定；
当前严格合同把模型训练挡在门外。
```

### 1.2 P0.9A 的结论

P0.9A 专门回答 trainability，目标行业为：

```text
电子
汽车
电力设备
```

P0.9A 的有效结论：

```text
1. 汽车 / 电子 在 T1_fixed_rounds_no_inner_validation 下具备主探针 trainability；
2. 电力设备在主合同下不具备 P0.9B 主执行资格，只能保留 diagnostic appendix；
3. T2 / T3 inner-validation 合同对当前行业专用样本过重；
4. T1 是唯一可作为 P0.9B locked probe 的安全合同；
5. sample-weight group cap 存在失败，但必须按 P0.9B 主执行范围和 appendix 范围拆开判定，不能用电力设备或非主合同失败错误阻塞汽车 / 电子 T1 主探针。
```

P0.9A 的 T1 诊断读数只能作为描述优先级，不得作为合同选择或模型选择依据：

```text
汽车 launch：AUC 0.7348，OOF events 701，本轮最强诊断信号；
汽车 failure：AUC 0.5749，OOF events 2750，有弱可学习性；
电子 launch：AUC 0.5201，OOF events 1212，轻微信号；
电子 failure：AUC 0.4866，OOF events 4586，接近或低于随机，用于 null / placebo stress。
```

这些读数不能推出：

```text
汽车 launch 已经有效；
电子 failure 已经无效；
任何任务可以进入 P1；
任何模型可以进入策略回测。
```

它们只决定 P0.9B 的报告阅读顺序。四个主 task 必须生成同等深度的 required artifacts，不得因为 P0.9A AUC 高低改变分析覆盖。

### 1.3 为什么 P0.9B 不是 Parameter-Regime 主线

上一版 P0.9B 把主线写成 `Parameter-Regime Explanation Probe`：预注册多组 LGBM 参数族，用不同参数代表不同结构假设。

这条方向是安全的，但不是最高效的下一步。原因：

```text
1. P0.9A 已经说明当前数据不适合传统 supervised-learning 调参流程；
2. T1 是唯一可训练主合同，继续比较参数族容易变成隐性调参；
3. 当前真正需要的不是“哪个参数表现好”，而是“模型暗示了哪些可手工审计结构”；
4. LGBM 的价值应转化为 future manual primitive，而不是停留在 feature importance story。
```

因此 P0.9B 改为：

```text
Industry LGBM-to-Primitive Translation Probe
```

Parameter regimes 可以作为 secondary diagnostic appendix，但不得作为主线、不得用于选择 primitive、不得用于选择模型或参数。

---

## 2. 阶段定位

P0.9B 是 `post-selected diagnostic primitive-translation phase`。

P0.9B 是 hypothesis-generating，不是 validation phase。

P0.9B 的任务是把 LGBM 中可解释的行业内结构转写成下一阶段人工 gate / formula 的候选 primitive。

P0.9B 不得被解释为：

```text
P1 validation
clean OOS proof
industry model refinement
hyperparameter tuning
score bucket selection
trading strategy construction
```

报告必须固定使用以下边界措辞：

```text
LGBM score is diagnostic only.
Locked T1 model is a probe instrument, not a deployable model.
Feature importance is explanation evidence, not feature selection evidence.
Validation metrics are descriptive, not selection metrics.
Manual primitives are future research hypotheses, not trading rules.
No P1 / Explore10 / freeze eligibility is produced by P0.9B.
```

---

## 3. 输入边界

### 3.1 允许读取的 P0.9A artifacts

P0.9B 可以读取：

```text
Explore9/outputs/p0_9a/reports/p0_9a_recommendation_summary.csv
Explore9/outputs/p0_9a/reports/p0_9a_trainability_contract_matrix.csv
Explore9/outputs/p0_9a/reports/p0_9a_lgbm_fold_trainability_audit.csv
Explore9/outputs/p0_9a/reports/p0_9a_model_sanity_metrics_oof.csv
Explore9/outputs/p0_9a/reports/p0_9a_feature_importance_diagnostic_only.csv
Explore9/outputs/p0_9a/reports/p0_9a_sample_weight_group_cap_audit.csv
Explore9/outputs/p0_9a/reports/p0_9a_p0_9b_null_family_recommendation.csv
Explore9/outputs/p0_9a/reports/p0_9a_failure_event_level_trainability_audit.csv
Explore9/outputs/p0_9a/reports/p0_9a_feature_asof_leakage_audit.csv
Explore9/outputs/p0_9a/reports/p0_9a_observed_reference_overlap_audit.csv
Explore9/outputs/p0_9a/reports/p0_9a_walk_forward_purge_audit.csv
```

这些 artifacts 只能用于：

```text
1. 锁定 P0.9B 执行范围；
2. 锁定 T1 fixed rounds 合同；
3. 继承 sample-weight guardrail；
4. 继承 null / multiplicity family；
5. 写明为什么 P0.9B 是 post-selected diagnostic phase；
6. 复用 anti-leakage / purge / feature-asof 审计口径。
```

不得用于：

```text
label construction
feature selection
parameter selection
threshold selection
score calibration
bucket selection
candidate ranking
P1 promotion
Explore10 decision
```

### 3.2 允许读取的 P0.9 / P0.8 / P0.7 artifacts

P0.9B 可以读取 P0.9 / P0.8 / P0.7 报告作为背景，但只能写入 narrative background 或 audit reference。

禁止将 P0.7 / P0.8 / P0.9 的 best candidate、leaderboard rank、feature importance、score bucket、gate formula 作为 P0.9B 的 selection input。

---

## 4. 执行范围

### 4.1 主执行 industry-task

P0.9B 主执行范围只包括 P0.9A 中具备 T1 trainability 的 industry-task：

| industry | task | execution contract | role |
|---|---|---|---|
| 汽车 | industry_launch_winner_score_lgbm | T1 fixed rounds | primary_mechanism_extraction |
| 汽车 | industry_failure_reject_score_lgbm | T1 fixed rounds | secondary_failure_extraction |
| 电子 | industry_launch_winner_score_lgbm | T1 fixed rounds | weak_signal_diagnostic |
| 电子 | industry_failure_reject_score_lgbm | T1 fixed rounds | null_placebo_stress |

### 4.2 电力设备处理

`电力设备` 不进入 P0.9B 主执行范围。

```text
industry = 电力设备
allowed_role = diagnostic_trainability_reference_only
eligible_for_locked_t1_main_probe = false
eligible_for_manual_primitive_candidate = false
eligible_for_p0_9c_map = false
eligible_for_p1_or_explore10 = false
```

电力设备可以进入 appendix，用于说明 raw sample 充足但主合同 trainability 不足的情形。不得用电力设备的结果补强汽车 / 电子 primitive。

### 4.3 任务优先级

P0.9B 报告解释顺序：

```text
Priority 1: 汽车 launch
  本轮最强诊断信号；优先做 mechanism extraction 与 primitive translation。

Priority 2: 汽车 failure
  弱可学习性；重点看是否存在 failure-risk primitive，必须特别控制 from-launch false reject。

Priority 3: 电子 launch
  轻微信号；重点测试解释流程是否能避免过度叙事。

Priority 4: 电子 failure
  接近随机或弱于随机；主要作为 null/placebo stress test。
```

注意：该优先级仅决定报告解释顺序，不决定合同选择、模型选择、threshold 选择或 primitive promotion。四个主 task 必须生成同等深度的 artifact；不得因为 `汽车 launch` AUC 较高而多做解释，也不得因为 `电子 failure` AUC 较弱而少做 null / placebo / slice / concentration 审计。

---

## 5. Locked T1 合同

P0.9B 必须继承 P0.9A 的 T1 合同。

```text
contract_id = T1_fixed_rounds_no_inner_validation
inner_validation = false
early_stopping = false
outer_validation_used_for_iteration_selection = false
```

固定轮数：

```text
launch num_boost_round = 64
failure num_boost_round = 32
```

禁止：

```text
grid search
random search
Bayesian optimization
validation AUC 选参
validation logloss 选参
validation Brier 选参
2024 robustness 选参
post-hoc 修改 rounds
post-hoc 修改 feature set
post-hoc 添加 parameter regimes
```

如果实现运行 secondary parameter regimes，它们只能进入 appendix：

```text
secondary_parameter_regime_role = diagnostic_only
allowed_to_select_model = false
allowed_to_select_primitive = false
allowed_to_override_locked_t1 = false
```

---

## 6. Sample-Weight Guardrail

P0.9A 的 sample-weight group cap 在全合同矩阵上存在失败项：

```text
failed_rows = 72
max_top_instrument_year_weight_share = 9.42%
configured_cap = 8.00%
```

但 P0.9B 主执行范围只包括：

```text
汽车 / 电子 + T1_fixed_rounds_no_inner_validation
```

因此 sample-weight guardrail 必须拆成两层：

```text
main_scope_cap_pass:
  只统计 汽车 / 电子 + T1 + main industry-task-fold。
  若 false，则阻塞 main probe signal interpretation。

appendix_scope_cap_pass:
  统计 电力设备 appendix、T0/T2/T3/T4 或其他非主范围。
  若 false，只能阻塞对应 appendix interpretation；
  不得阻塞 汽车 / 电子 + T1 主探针。
```

P0.9B 启动 main-scope signal interpretation 前必须二选一：

```text
A. 修复 sample-weight group cap：
   主执行范围所有 industry-task-fold 的 main_scope_cap_pass = true；

B. 未修复：
   phase_status = blocked_by_main_scope_weight_guardrail；
   可以生成数据诊断报告；
   禁止输出 diagnostic_probe_signal_present；
   禁止输出 manual_primitive_candidate_for_p0_9c。
```

不得在 main-scope sample-weight cap 未处理时，把任何 main-scope feature importance、validation lift、slice stability、null-adjusted score 解释为支持 future primitive。

如果只有 appendix scope cap 失败，则报告必须写明：

```text
main_scope_signal_interpretation_allowed = true
appendix_signal_interpretation_allowed = false for failed appendix rows
```

Required artifact：

```text
p0_9b_sample_weight_guardrail_resolution.csv
```

字段：

```text
industry
task
fold_id
contract_id
scope_role
max_top_instrument_year_weight_share
instrument_year_weight_hhi
configured_top_share_cap
configured_hhi_cap
cap_pass
main_scope_cap_pass
appendix_scope_cap_pass
resolution_method
resolution_status
allowed_for_signal_interpretation
blocked_reason
```

P0.9B manifest 必须写入：

```text
sample_weight_guardrail_resolved = true / false
main_scope_sample_weight_guardrail_resolved = true / false
appendix_scope_sample_weight_guardrail_resolved = true / false
sample_weight_guardrail_resolution_method = cap_recomputed / cap_threshold_formally_waived / blocked
sample_weight_guardrail_used_for_primitive = false if unresolved
```

---

## 7. 数据纪律与反泄漏

P0.9B 必须沿用 Explore9 / P0.9A 的 PIT 数据边界。

默认输入：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

### 7.1 Feature as-of rule

P0.9B 必须继承 P0.9A 的 anti-leakage rule。

对于 close-derived launch / failure signals：

```text
signal_date = close-derived signal date
event_effective_date = next_trading_day(signal_date)
execution_price_reference = next_open on event_effective_date
feature_asof_date = signal_date
```

禁止作为 model feature：

```text
event_effective_date high
event_effective_date low
event_effective_date close
event_effective_date volume
event_effective_date money
any feature computed after signal_date close
```

允许：

```text
event_effective_date next_open as execution price reference / audit only
```

Required artifact：

```text
p0_9b_feature_asof_leakage_audit.csv
```

所有主执行行必须满足：

```text
feature_asof_leakage_violation_count = 0
```

### 7.2 Walk-forward purge

P0.9B 必须继承 purged walk-forward。

训练样本 eligibility 必须满足：

```text
train_label_window_end_date < validation_start_date
```

P0.9B 不做 early stopping，但仍必须审计 train labels 是否跨入 validation year。

Required artifact：

```text
p0_9b_walk_forward_purge_audit.csv
```

### 7.3 Fold role

P0.9B 的 core OOF 只包括：

```text
fold_2020
fold_2021
fold_2022
fold_2023
```

`fold_2024` 只能是：

```text
robustness_audit_only
allowed_label_measurement_overlap = true for pre-2025 decisions
allowed_for_primitive_selection = false
allowed_for_manual_primitive_candidate = false
allowed_for_p0_9c_map = false
```

### 7.4 Observed reference

P0.9B 必须继续拆分三类 overlap：

```text
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
```

硬规则：

```text
decision_overlap rows cannot enter train / validation / interpretation
feature_overlap rows cannot enter train / validation / interpretation
label_measurement_overlap rows cannot enter core OOF primitive evidence
label_measurement_overlap rows can enter 2024 robustness appendix only
```

Required artifact：

```text
p0_9b_observed_reference_overlap_audit.csv
```

---

## 8. 样本单位与标签

### 8.1 Launch task 样本单位

```text
sample_unit = launch_stratum_event
industry = target_industry PIT as of signal_date
event_effective_date = stratum_effective_date
reference_price = launch_effective_price_reference
```

主标签仅用于诊断，不用于 P1：

```text
launch_winner_50h120 = max(high over [E, trading_day_offset(E,119)]) / P_E - 1 >= 0.50
launch_winner_50c120 = max(close over [E, trading_day_offset(E,119)]) / P_E - 1 >= 0.50
launch_winner_100h240 = max(high over [E, trading_day_offset(E,239)]) / P_E - 1 >= 1.00
launch_future_max_drawdown_60d = min(low over [E, trading_day_offset(E,59)]) / P_E - 1
```

其中：

```text
E = stratum_effective_date
P_E = stratum_effective_price_reference
label_window_includes_effective_date_high_low = true
drawdown sign convention: -0.12 means 12% drawdown
```

### 8.2 Failure task 样本单位

Failure task 可以保留多窗口训练，但解释与主审计必须 event-level dedup。

窗口：

```text
failure_decision_window in {3d, 5d, 10d}
```

样本：

```text
window_sample_unit = launch_stratum_event_id + failure_decision_window
event_dedup_unit = launch_stratum_event_id
D = failure_decision_effective_date
P_D = failure_decision_effective_price_reference
L = launch_effective_date
P_L = launch_effective_price_reference
```

Failure 主诊断标签：

```text
failure_drawdown_from_decision_60d = min(low over [D, trading_day_offset(D,59)]) / P_D - 1
failure_reject_positive_primary =
  target_50h120_not_reached_before_decision_effective_date
  and failure_drawdown_from_decision_60d <= -0.12
```

False reject 拆成两套：

```text
from-launch target:
  failure_false_reject_vs_launch_target_50h120
  failure_false_reject_vs_launch_target_100h240
  用于 winner coverage / missed original launch winner 解释

from-decision target:
  failure_false_reject_vs_decision_target_50h120
  failure_false_reject_vs_decision_target_100h240
  用于 residual reward-risk diagnostic
```

P0.9B 不做 P1，但如果要判断 future primitive 是否允许进入 P0.9C，failure primitive 必须优先检查 from-launch false reject。

### 8.3 Failure 多窗口权重归一化

P0.9B 必须继承 P0.9A 的 failure window normalization：

```text
base_event_weight = event_balanced_weight
valid_window_count_for_event = count(valid windows for launch_stratum_event_id within target_industry + fold_id + task)
failure_window_normalized_weight = base_event_weight / valid_window_count_for_event
```

顺序：

```text
1. window normalization
2. instrument-year group cap
3. final sample weight
```

Required artifacts：

```text
p0_9b_failure_window_weight_normalization_audit.csv
p0_9b_failure_event_level_dedup_audit.csv
```

---

## 9. Feature Family Dictionary

P0.9B 不得把 feature importance 用于选择特征。Feature family 只用于解释和 primitive 转写。

必须固定 feature family：

```text
industry_relative_strength
industry_breadth
stock_within_industry_rank
volatility_expansion
repair_quality
turnover_liquidity_money
launch_family_lifecycle
failure_path
market_regime
price_location_gap
calendar_context
execution_feasibility
```

每个 feature 必须进入：

```text
p0_9b_feature_family_dictionary.csv
```

字段至少包括：

```text
feature_name
feature_family
raw_or_derived
formula_text_resolved
feature_asof_rule
allowed_for_launch
allowed_for_failure
used_in_locked_t1_model
used_in_secondary_parameter_regime
leakage_risk_class
```

禁止：

```text
feature selected because validation importance was high
feature dropped because validation importance was low
feature threshold tuned on validation
feature family added after reading P0.9B validation results
```

---

## 10. P0.9B 三段式执行

### 10.1 P0.9B0：Guardrail Resolution

执行前先确认：

```text
main_scope_sample_weight_guardrail_resolved = true
feature_asof_leakage_violation_count = 0
observed_reference_decision_feature_overlap_eligible_count = 0
walk_forward_purge_pass = true
required_inputs_available = true
```

如果 main-scope sample-weight guardrail 未解决：

```text
phase_status = blocked_by_weight_guardrail
report_allowed = true
primitive_candidate_output_allowed = false
```

### 10.2 P0.9B1：Locked T1 Mechanism Extraction

在主执行 scope 内，按 T1 合同训练 / 重跑 locked model。

必须输出：

```text
core OOF diagnostic metrics
prediction dispersion
feature family importance
feature family dropout delta
slice stability
instrument-year concentration
tree split / path pattern
null / placebo adjusted diagnostics
```

不得输出：

```text
selected model
selected params
selected bucket
P1 candidate
```

### 10.3 P0.9B2：Manual Primitive Translation

把稳定诊断结构转写成手工 primitive。

Primitive 的形式必须是：

```text
industry
 task
 primitive_family
 primitive_text
 observable_tokens
 expected_direction
 relation_type
 effective_date_rule
 feature_asof_rule
 reference_price_rule
 null_status
 stability_status
 allowed_for_p0_9c
 reason_if_not_allowed
```

Primitive 不能是：

```text
use LGBM score > x
use leaf id == y
buy top decile
reject bottom decile
use feature importance top feature as rule
```

Primitive 应该类似：

```text
汽车 launch:
  行业内相对强度改善 + 修复质量较高 + 波动扩张但非破坏性 + 行业宽度未恶化

汽车 failure:
  高波破坏 + 行业宽度转弱 + 个股行业内 rank 蒸发 + failure path 出现

电子 launch:
  行业内宽度改善 + rank persistence + 非 late acceleration

电子 failure:
  若 LGBM signal 不能通过 null/placebo，则输出 negative-control lesson，而不是 primitive
```

---

## 11. 诊断分析要求

### 11.1 Core OOF diagnostic metrics

必须按 industry-task 输出：

```text
AUC
logloss
Brier
calibration slope
prediction std
unique prediction count
OOF event count
positive count
base rate
rank correlation
```

这些指标只用于 sanity 和 narrative 描述，不得用于选择模型、参数、阈值、bucket、primitive。

Required artifact：

```text
p0_9b_core_oof_diagnostic_metrics.csv
```

### 11.2 Feature-family importance

必须输出：

```text
feature_gain_share
feature_split_share
permutation_importance_delta
family_total_gain_share
top_feature_dominance_share
single_family_dominance_flag
```

Required artifact：

```text
p0_9b_feature_family_importance.csv
```

### 11.3 Feature-family dropout

对每个主 task 至少测试：

```text
drop industry_relative_strength
drop industry_breadth
drop stock_within_industry_rank
drop volatility_expansion
drop repair_quality
drop turnover_liquidity_money
drop market_regime
drop failure_path for failure task
drop launch_family_lifecycle for launch task
```

输出：

```text
metric_delta_after_dropout
prediction_correlation_after_dropout
primitive_signal_survives_dropout
family_is_essential
family_is_artifact_risk
```

Required artifact：

```text
p0_9b_feature_family_dropout_audit.csv
```

### 11.4 Slice stability

至少按以下 slice 输出：

```text
validation_year
fold_id
industry
task
market_regime
launch_family
failure_decision_window
liquidity_bucket
volatility_bucket
instrument_year
```

Primitive 不得来自单一 slice。

Slice stability 状态必须机械判定：

```text
slice_stability_status = pass only if:
  core_fold_support_count >= 2
  and supporting_validation_year_count >= 2
  and supporting_slice_count >= 2 for the primary claimed slice dimension
  and fold_2024_used_for_support = false

slice_stability_status = one_fold_only if:
  core_fold_support_count < 2

slice_stability_status = one_year_only if:
  supporting_validation_year_count < 2

slice_stability_status = one_slice_only if:
  supporting_slice_count < 2

slice_stability_status = uninterpretable if:
  required slice denominator is missing
  or slice denominator < configured minimum
```

Required artifact：

```text
p0_9b_slice_stability_audit.csv
```

### 11.5 Instrument-year concentration

必须输出：

```text
top1_instrument_contribution
top5_instrument_contribution
top_instrument_year_contribution
instrument_year_hhi
weight_share_top_instrument_year
```

如果解释主要来自一个 instrument-year，primitive 必须标记：

```text
primitive_rejected_due_to_instrument_year_concentration = true
```

Concentration 状态必须机械判定：

```text
instrument_year_concentration_status = pass only if:
  top1_instrument_contribution <= 0.20
  and top5_instrument_contribution <= 0.60
  and top_instrument_year_contribution <= 0.12
  and instrument_year_hhi <= 0.08
  and weight_share_top_instrument_year <= 0.08

instrument_year_concentration_status = fail_top1 if:
  top1_instrument_contribution > 0.20

instrument_year_concentration_status = fail_top_instrument_year if:
  top_instrument_year_contribution > 0.12
  or weight_share_top_instrument_year > 0.08

instrument_year_concentration_status = fail_hhi if:
  instrument_year_hhi > 0.08
```

Required artifact：

```text
p0_9b_instrument_year_concentration_audit.csv
```

### 11.6 Tree path / split pattern extraction

P0.9B 可以解析 LGBM split pattern，但不得把 leaf rule 当作交易规则。

必须输出：

```text
top_split_features
common_feature_pairs
feature_family_pair_frequency
approximate_threshold_quantile_bucket
path_support_count
path_fold_presence
path_interpretation_text
```

Threshold 必须转成 train-fold quantile bucket，不得使用 validation-tuned numeric threshold。

Required artifact：

```text
p0_9b_tree_path_split_pattern_audit.csv
```

---

## 12. Null / Placebo / Search-bias 约束

P0.9B 是 post-selected diagnostic phase，因此必须做 null / placebo，防止解释叙事过拟合。

### 12.1 Null families

至少执行：

```text
label_permutation_within_industry_fold
instrument_year_block_shuffle
year_shuffle_within_industry
feature_family_dropout_placebo
weak_signal_task_placebo using 电子 failure
```

对于每个 primitive candidate 必须输出：

```text
real_metric
null_mean
null_p95
empirical_p_value
null_adjusted_signal_status
```

### 12.1.1 Null / placebo 状态硬阈值

`null_adjusted_signal_status` 必须按预注册阈值机械判定，不得由报告作者事后解释。

默认阈值：

```text
null_empirical_p_pass_threshold = 0.10
null_percentile_pass = real_metric > null_p95
min_null_repeats = 100
weak_signal_placebo_max_supported_primitive_count = 0
```

状态枚举：

```text
stable:
  real_metric > null_p95
  and empirical_p_value <= 0.10
  and not placebo_only
  and not one_fold_only
  and not one_instrument_year_only

weak_but_not_collapsed:
  real_metric > null_mean
  and real_metric <= null_p95
  and empirical_p_value <= 0.25
  and not placebo_only

collapsed_under_null:
  real_metric <= null_mean
  or empirical_p_value > 0.25

placebo_only:
  same or stronger primitive story appears in weak_signal_task_placebo
  or feature_family_dropout_placebo produces comparable signal

uninterpretable:
  null repeats < min_null_repeats
  or required null family missing
  or null metric cannot be computed
```

只有 `stable` 可以支持 `manual_primitive_allowed_for_p0_9c = true`。`weak_but_not_collapsed` 只能进入 narrative / negative-control lesson，不得进入 P0.9C map。

Required artifact：

```text
p0_9b_null_placebo_audit.csv
```

### 12.2 电子 failure 作为压力测试

`电子 failure` 不得因为可训练而被自动解释为有效方向。

P0.9B 必须使用电子 failure 检查解释流程本身：

```text
if weak_signal_task produces too many plausible primitive stories:
    interpretation_pipeline_overfits_narrative = true
```

Required artifact：

```text
p0_9b_weak_signal_placebo_stress_audit.csv
```

### 12.3 Metric non-selection

P0.9B 可以读取 metrics，但不得让 metrics 参与排序型选择：

```text
contract selection
parameter selection
feature selection
bucket selection
industry selection
task selection
```

允许使用预注册 pass/fail metric gates 判断 primitive eligibility。也就是说，metrics 不得用于“谁表现最好就选谁”，但可以用于机械判定：

```text
null_adjusted_signal_status == stable
slice_stability_status == pass
instrument_year_concentration_status == pass
feature_family_dropout_status in {pass, expected_dependency}
```

Primitive eligibility 只能基于预注册的解释合同：

```text
sample-weight pass
anti-leakage pass
null/placebo not collapsed
slice stability
instrument-year concentration pass
feature-family dropout consistency
manualizability
```

`p0_9b_metric_nonselection_audit.csv` 必须区分：

```text
metric_used_for_ranking_selection
metric_used_for_pre_registered_pass_fail_gate
```

前者必须恒为 false；后者允许为 true，但必须能追溯到本 requirement 的硬阈值。

Required artifact：

```text
p0_9b_metric_nonselection_audit.csv
```

所有 `selection_violation` 必须为 false。

---

## 13. Manual Primitive Candidate Gate

P0.9B 不是 P1，但它需要判断哪些 primitive 可以进入 P0.9C。

### 13.1 Primitive allowed for P0.9C 的必要条件

```text
manual_primitive_allowed_for_p0_9c = true
```

当且仅当：

```text
1. main_scope_sample_weight_guardrail_resolved = true
2. feature_asof_leakage_violation_count = 0
3. observed_reference_decision_feature_overlap_eligible_count = 0
4. primitive uses only T-day observable tokens
5. primitive does not depend on LGBM raw score / leaf id / score bucket
6. primitive has support in core OOF folds, not fold_2024 only
7. primitive is not one-instrument-year dominated
8. primitive is not one-year-only
9. primitive is not one-feature-only unless explicitly labeled threshold_primitive_diagnostic
10. null_adjusted_signal_status = stable
11. slice_stability_status = pass
12. instrument_year_concentration_status = pass
13. feature-family dropout does not fully collapse the claimed mechanism unexpectedly
14. feature_family_dropout_status in {pass, expected_dependency}
15. weak_signal_placebo_status != narrative_overfit
16. metric_used_for_ranking_selection = false
17. metric_used_for_pre_registered_pass_fail_gate is allowed only if threshold is declared in this requirement
18. manual_hypothesis_text is precise enough to implement as future formula
19. no metric-based ranking selection violation
20. task-specific role permits translation
```

### 13.2 任务角色限制

汽车 launch：

```text
allowed_to_emit_manual_primitive = true
priority = primary
```

汽车 failure：

```text
allowed_to_emit_manual_primitive = true
must_include_false_reject_caution = true
from_launch_false_reject_audit_required = true
```

电子 launch：

```text
allowed_to_emit_manual_primitive = true only if null/placebo and slice stability pass
otherwise weak_signal_lesson_only
```

电子 failure：

```text
allowed_to_emit_manual_primitive = false by default
allowed_only_if extraordinarily stable under null/placebo and not narrative-overfit
primary role = negative control / weak-signal stress
```

电力设备：

```text
allowed_to_emit_manual_primitive = false
role = diagnostic_trainability_reference_only
```

### 13.3 Forbidden primitive forms

禁止输出：

```text
LGBM_score_top_5pct
leaf_rule_123
predicted_probability_above_x
feature_importance_top_feature_buy
best_validation_slice_rule
2024_robustness_rule
post_target_rule
same-day close execution rule
```

---

## 14. Primitive Families to Extract

P0.9B 应优先尝试把 LGBM 解释转写成以下 primitive family。

### 14.1 汽车 launch primitive seed families

```text
auto_industry_relative_strength_repair
  行业内相对强度改善 + 修复质量提高

auto_volatility_expansion_not_destructive
  波动扩张但未出现破坏性高波

auto_industry_breadth_support
  行业宽度改善或未恶化，个股 rank persistence

auto_money_quality_launch
  成交金额/换手改善且价格保持

auto_market_regime_compatibility
  非极端 risk-off 或市场状态未明显压制行业扩张
```

### 14.2 汽车 failure primitive seed families

```text
auto_destructive_high_vol_rank_evaporation
  高波破坏 + 行业内 rank 快速蒸发

auto_industry_breadth_failure
  行业宽度转弱 + 个股不能跟随

auto_gap_fade_or_price_location_failure
  gap/fade/跌破关键参考价 + 失败路径

auto_turnover_distribution_warning
  放量但价格不能保持 / 成交质量转坏
```

### 14.3 电子 launch primitive seed families

```text
electronics_breadth_rank_persistence
  行业宽度改善 + 个股 rank persistence

electronics_non_late_acceleration_strength
  强势但非 late acceleration / 非 post-target state

electronics_liquidity_quality_confirmation
  成交质量确认但不作为首入场规则
```

### 14.4 电子 failure primitive seed families

默认作为 stress / placebo：

```text
electronics_failure_null_stress
  如果模型解释出漂亮故事但 null/placebo 不支持，记录为 negative lesson
```

只有在极少数情况下允许转写 primitive：

```text
null_adjusted_signal_status = stable
slice_stability_pass = true
false_reject_caution_pass = true
feature_family_dropout_pass = true
```

---

## 15. Primitive 输出表

Required artifact：

```text
p0_9b_manual_primitive_candidate_table.csv
```

字段至少包括：

```text
primitive_id
industry
task
task_role
primitive_family
primitive_text
primitive_type
source_model_contract
source_evidence_type
feature_family_set
observable_token_list
forbidden_token_check_pass
feature_asof_rule
effective_date_rule
reference_price_rule
relation_type
expected_direction
core_fold_support_count
fold_2024_used_for_support
null_adjusted_signal_status
placebo_stress_status
feature_family_dropout_status
slice_stability_status
instrument_year_concentration_status
manualizability_status
manual_primitive_allowed_for_p0_9c
reason_if_not_allowed
required_future_test
```

Primitive type 枚举：

```text
threshold_primitive
pairwise_interaction_primitive
three_way_context_primitive
sequence_context_primitive
failure_warning_primitive
negative_control_lesson
reject_due_to_artifact
```

---

## 16. P0.9C Requirement Map

P0.9B 最重要的输出是把 primitive 转成下一阶段 P0.9C 的研究任务。

Required artifact：

```text
p0_9b_primitive_to_p0_9c_requirement_map.csv
```

字段：

```text
primitive_id
industry
task
recommended_p0_9c_module
manual_formula_family_to_create
expected_denominator
expected_event_unit
required_baseline
required_false_reject_audit
required_matched_delay_audit
required_instrument_year_audit
required_null_or_placebo_audit
why_this_is_not_p1_yet
recommended_priority
```

P0.9C 只能接收：

```text
manual_primitive_allowed_for_p0_9c = true
```

不得接收：

```text
raw LGBM score bucket
leaf rule
validation best slice
secondary parameter regime result
fold_2024-only observation
```

---

## 17. Parameter Regime Appendix

Parameter regimes 从主线降级为 appendix。

如果实现仍运行 parameter regimes，只允许以下用途：

```text
1. 判断某种解释是否依赖 tree depth / min_child / feature_fraction；
2. 识别 class-weight artifact；
3. 辅助解释 locked T1 机制是否稳健；
4. 作为 negative evidence。
```

禁止用途：

```text
select best regime
replace locked T1
select primitive because regime metric best
select parameter for P0.9C
```

Optional artifact：

```text
p0_9b_secondary_parameter_regime_appendix.csv
```

如果该 artifact 生成，report 必须显式写明：

```text
Secondary parameter regimes are diagnostic-only and were not used to select primitives.
```

---

## 18. Required Outputs

第 18 节是 P0.9B 的唯一 required artifact authority。

### 18.1 Manifest / report

```text
p0_9b_run_manifest.json
p0_9b_report.md
p0_9b_forbidden_recommendation_self_check.csv
p0_9b_cache_tracking_audit.csv
```

### 18.2 Scope / guardrail / anti-leakage

```text
p0_9b_scope_lock.csv
p0_9b_sample_weight_guardrail_resolution.csv
p0_9b_feature_asof_leakage_audit.csv
p0_9b_observed_reference_overlap_audit.csv
p0_9b_walk_forward_purge_audit.csv
p0_9b_metric_nonselection_audit.csv
```

### 18.3 Model diagnostics

```text
p0_9b_locked_t1_model_inventory.csv
p0_9b_core_oof_diagnostic_metrics.csv
p0_9b_prediction_dispersion_audit.csv
p0_9b_model_sanity_audit.csv
```

### 18.4 Failure-specific audits

```text
p0_9b_failure_window_weight_normalization_audit.csv
p0_9b_failure_event_level_dedup_audit.csv
p0_9b_failure_false_reject_reference_audit.csv
```

### 18.5 Explanation audits

```text
p0_9b_feature_family_dictionary.csv
p0_9b_feature_family_importance.csv
p0_9b_feature_family_dropout_audit.csv
p0_9b_slice_stability_audit.csv
p0_9b_instrument_year_concentration_audit.csv
p0_9b_tree_path_split_pattern_audit.csv
```

### 18.6 Null / placebo / stress

```text
p0_9b_null_placebo_audit.csv
p0_9b_weak_signal_placebo_stress_audit.csv
```

### 18.7 Primitive translation

```text
p0_9b_manual_primitive_candidate_table.csv
p0_9b_primitive_stability_audit.csv
p0_9b_primitive_null_adjusted_audit.csv
p0_9b_primitive_to_p0_9c_requirement_map.csv
```

### 18.8 Optional appendix

```text
p0_9b_secondary_parameter_regime_appendix.csv
p0_9b_diagnostic_electric_equipment_appendix.csv
```

Optional artifacts must be clearly marked optional in manifest. Required artifacts must exist even if empty, with schema and explanatory row count.

Row-level or model-prediction panels must be parquet cache only:

```text
Explore9/outputs/p0_9b/cache/
```

Required cache tracking rule:

```text
git check-ignore Explore9/outputs/p0_9b/cache/*.parquet must pass
full row-level panels cannot be tracked CSV
report CSV/JSON/markdown artifacts live under Explore9/outputs/p0_9b/reports/
```

---

## 19. Report Structure

`p0_9b_report.md` 至少包含：

```text
1. 执行结论
2. P0.9B 定位与禁止结论
3. P0.9A 输入边界与 sample-weight guardrail
4. Scope lock: 汽车 / 电子 + T1，电力设备 appendix only
5. Anti-leakage / purge / observed-reference audit
6. Locked T1 diagnostic metrics
7. Feature-family mechanism extraction
8. Null / placebo / weak-signal stress
9. Slice stability and instrument-year concentration
10. Primitive candidate table summary
11. Primitive rejected reasons
12. P0.9C requirement map
13. Stop conditions and recommendation
14. Self-check: no P1 / no Explore10 / no score bucket selection
```

报告中必须显式写：

```text
No validated model is produced.
No best LGBM parameter is selected.
No score bucket is selected.
No P1 / Explore10 / freeze recommendation is produced.
Manual primitives are future hypotheses only.
```

---

## 20. Recommendation 枚举

P0.9B 最终 recommendation 只能是以下之一：

```text
proceed_to_p0_9c_manual_industry_gate_discovery
continue_p0_9b_primitive_translation_probe
blocked_by_weight_guardrail
stop_due_to_no_interpretable_primitive
stop_due_to_null_or_placebo_collapse
stop_due_to_concentration_or_instability
```

禁止 recommendation：

```text
proceed_to_industry_p1_refine
candidate_for_industry_p1_refine
proceed_to_explore10_backtest
validated_industry_model
freeze_strategy
selected_lgbm_model
selected_score_bucket
```

### 20.1 proceed_to_p0_9c 的条件

```text
proceed_to_p0_9c_manual_industry_gate_discovery
```

仅当：

```text
1. main_scope_sample_weight_guardrail_resolved = true
2. anti-leakage audits pass
3. at least one manual_primitive_allowed_for_p0_9c = true
4. primitive_to_p0_9c_requirement_map has at least one valid row
5. no metric selection violation
6. no forbidden recommendation self-check violation
```

注意：这不是 P1，也不是策略回测入口。

---

## 21. Config Sketch

建议配置文件：

```text
Explore9/configs/industry_lgbm_to_primitive_p0_9b.yaml
```

配置草案：

```yaml
phase: P0.9B
mode: industry_lgbm_to_primitive_translation_probe

scope:
  main_industry_tasks:
    - industry: 汽车
      task: industry_launch_winner_score_lgbm
      role: primary_mechanism_extraction
      contract_id: T1_fixed_rounds_no_inner_validation
    - industry: 汽车
      task: industry_failure_reject_score_lgbm
      role: secondary_failure_extraction
      contract_id: T1_fixed_rounds_no_inner_validation
    - industry: 电子
      task: industry_launch_winner_score_lgbm
      role: weak_signal_diagnostic
      contract_id: T1_fixed_rounds_no_inner_validation
    - industry: 电子
      task: industry_failure_reject_score_lgbm
      role: null_placebo_stress
      contract_id: T1_fixed_rounds_no_inner_validation
  diagnostic_appendix_industries:
    - 电力设备

locked_t1:
  launch_num_boost_round: 64
  failure_num_boost_round: 32
  early_stopping: false
  inner_validation: false
  outer_validation_used_for_iteration_selection: false

folds:
  core_oof_folds: [fold_2020, fold_2021, fold_2022, fold_2023]
  robustness_folds: [fold_2024]
  fold_2024_allowed_for_primitive: false

sample_weight_guardrail:
  require_resolution_before_interpretation: true
  block_main_probe_only_if_main_scope_fails: true
  appendix_failure_does_not_block_main_scope: true
  max_top_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.08

anti_leakage:
  feature_asof_date_equals_signal_date: true
  forbid_event_effective_date_ohlcv_as_feature: true
  require_train_label_window_end_before_validation_start: true
  observed_reference_decision_feature_overlap_allowed: false
  observed_reference_label_measurement_allowed_for_core_oof: false

feature_families:
  - industry_relative_strength
  - industry_breadth
  - stock_within_industry_rank
  - volatility_expansion
  - repair_quality
  - turnover_liquidity_money
  - launch_family_lifecycle
  - failure_path
  - market_regime
  - price_location_gap
  - calendar_context
  - execution_feasibility

null_placebo:
  enabled: true
  n_repeats: 100
  random_seed: 20260506
  empirical_p_pass_threshold: 0.10
  weak_empirical_p_max: 0.25
  require_real_metric_gt_null_p95_for_stable: true
  families:
    - label_permutation_within_industry_fold
    - instrument_year_block_shuffle
    - year_shuffle_within_industry
    - feature_family_dropout_placebo
    - weak_signal_task_placebo

primitive_gate:
  min_core_fold_support_count_primary: 2
  min_supporting_validation_year_count: 2
  min_supporting_slice_count: 2
  max_top1_instrument_contribution: 0.20
  max_top5_instrument_contribution: 0.60
  max_top_instrument_year_contribution: 0.12
  max_instrument_year_hhi: 0.08
  max_weight_share_top_instrument_year: 0.08
  require_null_not_collapsed: true
  require_metric_nonselection_pass: true
  require_manualizable_text: true
  forbid_lgbm_score_or_leaf_rule: true

secondary_parameter_regime_appendix:
  enabled: false
  allowed_for_selection: false
```

---

## 22. Implementation Commands

建议在 `Explore9/scripts/run_explore9.py` 中新增：

```text
profile-p0-9b
report-p0-9b
```

执行命令：

```bash
uv run python Explore9/scripts/run_explore9.py profile-p0-9b \
  --config Explore9/configs/industry_lgbm_to_primitive_p0_9b.yaml

uv run python Explore9/scripts/run_explore9.py report-p0-9b \
  --config Explore9/configs/industry_lgbm_to_primitive_p0_9b.yaml
```

输出根目录：

```text
Explore9/outputs/p0_9b/
```

输出边界：

```text
Explore9/outputs/p0_9b/reports/  # tracked CSV / JSON / markdown reports
Explore9/outputs/p0_9b/cache/    # ignored parquet cache only
```

---

## 23. Self-Check

P0.9B 完成前必须自检：

```text
1. 第 18 节所有 required artifacts 存在；
2. manifest 记录每个 artifact 的 row count / column count / file size；
3. sample-weight guardrail resolution 已输出；
4. 如果 main-scope sample-weight 未解决，primitive candidate 输出为空；
5. feature-asof leakage audit violation 为 0；
6. observed-reference decision / feature overlap eligible count 为 0；
7. fold_2024 没有支持任何 primitive candidate；
8. metric_nonselection_audit 无 violation；
9. 电子 failure 没有被强行解释成有效模型；
10. report 没有使用 best / selected / final model 语言；
11. report 没有把 feature importance 写成 feature selection；
12. report 没有输出 P1 / Explore10 / freeze；
13. 每个 allowed primitive 都有 P0.9C requirement map；
14. 每个 rejected primitive 都有 reason_if_not_allowed；
15. full row-level panels 只作为 parquet cache，不默认输出巨大 CSV；
16. `git check-ignore Explore9/outputs/p0_9b/cache/*.parquet` 通过；
17. `p0_9b_cache_tracking_audit.csv` 证明 cache parquet 未被 git 跟踪。
```

---

## 24. Stop Conditions

任一条件触发时，P0.9B 必须停止在 diagnostic 报告，不得输出 future manual primitive：

```text
main-scope sample-weight cap unresolved
feature-asof leakage detected
observed-reference decision/feature overlap entered eligible rows
required artifact missing
metric selection violation
null/placebo collapse
signal one-fold-only
signal fold_2024-only
signal one-instrument-year-only
signal dominated by one feature with no dropout support
manual primitive cannot be expressed without LGBM score or leaf id
```

这些停止条件不代表行业方向失败。它们只说明 locked T1 LGBM 没有给出足够可解释、可转写、可审计的下一阶段 primitive。

---

## 25. 最终边界

P0.9B 的有效产物只有：

```text
manual primitive candidate for P0.9C
negative-control lesson
artifact / null / concentration rejection reason
```

P0.9B 不能把 LGBM 模型本身往前推进。

P0.9B 的最好结果也只是：

```text
proceed_to_p0_9c_manual_industry_gate_discovery
```

不是：

```text
proceed_to_industry_p1_refine
proceed_to_explore10_backtest
freeze_strategy
```
