# Explore10 需求说明：Alpha158-like Atomic Feature Bank 与 LGBM Path-to-Audited Primitive Discovery

> 文件名：`requirement_explore10.md`
> 阶段：`Explore10`
> 标题：Alpha158-like Atomic Feature Bank + LGBM Path-to-Audited Primitive Discovery
> 状态：implementation-ready requirement draft
> 生成日期：2026-05-07
> 重要说明：本文中的 Explore10 不是“策略回测 Explore10”。本阶段仍是 discovery / hypothesis generation，不输出可交易策略、不进入回测、不 freeze 规则。

---

## 0. 一句话结论

Explore10 只做一件事：

```text
在 P0.9B 证明“semantic / hand-written primitive 转写失败”之后，
引入更底层、更连续、更中性的 Alpha158-like atomic feature bank，
用 locked LGBM probe 的树路径反向提取稳定 split pattern，
再把这些 pattern 转成 T 日可观察、train-fold 分位化、可人工实现的 audited primitive candidate。
```

Explore10 的主线是：

```text
Alpha158-like atomic feature bank
-> fixed-protocol LGBM probe
-> tree path / split pattern extraction
-> train-fold quantile bucket canonicalization
-> token coverage audit
-> OOF / null / placebo / concentration / slice stability audit
-> audited primitive candidate table
```

Explore10 不是：

```text
策略回测
P1 validation
clean OOS proof
最终模型训练
best LGBM search
score bucket selection
交易规则生成器
自动买卖信号生成器
```

Explore10 可以输出：

```text
atomic_primitive_candidate_for_next_requirement
path_pattern_diagnostic_lead
primitive_rejected_due_to_zero_support
primitive_rejected_due_to_null_or_placebo
primitive_rejected_due_to_concentration
primitive_rejected_due_to_instability
stop_due_to_no_atomic_primitive_signal
```

Explore10 禁止输出：

```text
proceed_to_explore10_backtest = true
validated_model = true
selected_lgbm_model = true
selected_score_bucket = true
actionable_trade_rule = true
freeze_strategy = true
candidate_for_strategy_backtest = true
```

---

## 1. 背景与阶段来源

### 1.1 Explore9 P0 的原始发现

Explore9 P0 的核心结论不是已经找到可交易策略，而是大 winner 在早期到中期修复阶段存在高波扩张、相对强度、修复延展、行业宽度共振等可观察结构；但这些结构更像 winner discovery / continuation confirmation / hold tolerance 线索，不是可冻结的入场规则。

P0 也保留了严格数据纪律：使用 PIT universe、PIT industry membership、target history 和 Qlib PIT provider；Explore8 输出只允许作为背景和 schema/audit reference，不进入 label、signal 或 selection。

### 1.2 P0.8 的启示

P0.8 的 gate + LGBM 探索显示：

```text
LGBM 对 launch / failure 都有可见预测力；
但没有 P1 candidate；
LGBM full-retrain null、leaf rule 稳定性、industry/regime concentration 仍是硬问题。
```

其中 launch LGBM top bucket 是有价值的 discovery lead，但不能作为 P1 规则。P0.8 还显示 failure reject 最大风险不是 precision alone，而是 false reject / missed winner。

### 1.3 P0.9 / P0.9A 的启示

P0.9 证明行业专用 LGBM 的最初严格合同不可训练，因此不是 performance rejection，而是 trainability failure。

P0.9A 证明：

```text
汽车 / 电子 在 T1_fixed_rounds_no_inner_validation 下具备主探针 trainability；
电力设备不具备主合同资格；
T1 是唯一可作为 P0.9B locked probe 的安全合同；
汽车 launch 是最强诊断读数；
汽车 failure 有弱可学习性；
电子 launch / failure 更适合 weak-signal / placebo stress。
```

这些诊断读数不能用于选择模型、调参数、推进 P1 或启动回测，只能用于安排 Explore10 的 primary / secondary / placebo 任务优先级。

### 1.4 P0.9B 的负向结论

P0.9B 的结论是：

```text
stop_due_to_null_or_placebo_collapse
```

8 个预注册 manual primitive candidate 中，允许进入 P0.9C 的数量为 0。最关键的负向证据是：

```text
汽车 launch 模型有最像信号的一组诊断读数，
但转写后的 launch primitive 全部零支持 / one-fold-only / null 下坍缩；
汽车 failure 的 warning primitive 有 core fold 支持，
但 null / placebo 压不过，且 instrument-year concentration 过高；
电子 launch / failure 不构成正向证据。
```

因此 Explore10 不应继续扩写原来的 semantic primitive，例如：

```text
repair_quality + industry_breadth + rank persistence
volatility_expansion_not_destructive
industry_relative_strength_repair
```

而应回到 primitive seed 的表达层，先用更底层、更连续、更中性的 Alpha158-like atomic feature bank 作为新特征空间。

---

## 2. 阶段定位

Explore10 是 `atomic-feature-bank discovery` 与 `path-to-primitive translation` 阶段。

Explore10 是 hypothesis-generating，不是 validation phase。

Explore10 的目标是回答：

```text
当前 semantic primitive 转写失败后，
是否可以用 Alpha158-like atomic feature bank，
在汽车 launch 这个最强诊断任务上，
提取出比原手工 primitive 更宽、更稳定、更可审计的 atomic primitive candidate？
```

Explore10 的成功不代表可交易策略。即使 Explore10 找到 audited primitive candidate，也只能进入下一阶段：

```text
Explore11 manual atomic primitive formula discovery
或
P1 atomic primitive hypothesis refine
```

但不能直接进入：

```text
strategy backtest
Explore10 backtest
production model
freeze strategy
```

---

## 3. 研究问题

Explore10 必须回答以下问题。

### 3.1 Alpha158-like atomic bank 是否覆盖原 primitive 失效区域？

P0.9B 汽车 launch primitive 支持数为 0，说明原 token mask 太窄。Explore10 必须先回答：

```text
新的 atomic tokens 是否在 trainable core OOF 中有足够 support？
是否能覆盖 P0.9B 中 LGBM 认为高分但手工 primitive 抓不到的事件？
```

这一步优先于 lift、AUC、null、path 解读。

### 3.2 LGBM path 是否能稳定复现？

Explore10 不看单棵树、单个 leaf、单个 fold 的故事。它必须回答：

```text
哪些 split features / feature pairs / feature-family combinations
在多个 core fold 中重复出现？
这些 split 的 threshold 是否能转成 train-fold quantile bucket？
这些 pattern 是否能脱离 LGBM score / leaf id 独立实现？
```

### 3.3 Path pattern 是否能转成 audited primitive candidate？

Explore10 必须把 path pattern 翻译成：

```text
observable token list
formula_text_resolved
feature_asof_rule
effective_date_rule
reference_price_rule
denominator_scope
expected direction
```

并证明这个 candidate：

```text
有足够 token support；
跨 core folds 稳定；
不过度集中在单 instrument / instrument-year；
压过 null / placebo；
不依赖 validation-tuned threshold；
不使用 LGBM score / leaf id。
```

### 3.4 Alpha158-like bank 是否只是制造更多 search bias？

因为 Alpha158-like feature bank 增大了表达空间，Explore10 必须特别回答：

```text
real primitive metric 是否超过 path-level null / label permutation null / feature-family placebo？
候选数量、路径数量、抽取预算、null family 是否完整记录？
```

### 3.5 是否存在可进入下一阶段的 atomic primitive seed？

Explore10 不要求一定找出候选，但必须明确：

```text
哪些 atomic primitive candidate 可以进入下一阶段；
哪些因为 zero support / null collapse / concentration / instability 被淘汰；
哪些只保留为 mechanism diagnostic。
```

---

## 4. Scope Lock

### 4.1 主任务

Explore10 主任务固定为：

```text
target_industry = 汽车
model_task = launch_winner
contract = T1_fixed_rounds_no_inner_validation
model_role = locked_lgbm_probe
```

这是唯一可以进入 `atomic_primitive_candidate_for_next_requirement` 的主任务。

### 4.2 次级任务

Explore10 次级任务为：

```text
target_industry = 汽车
model_task = failure_reject
contract = T1_fixed_rounds_no_inner_validation
model_role = secondary_diagnostic_only
```

汽车 failure 可以输出 failure-mechanism diagnostic primitive，但不得进入主 primitive candidate、不得写入
`explore10_next_requirement_candidate_map`、不得触发 Explore11 proceed。若 false-reject gates 全部通过，
只能写入 appendix-only diagnostic map。

### 4.3 Placebo / weak-signal 任务

Explore10 使用电子作为 weak-signal / placebo stress：

```text
target_industry = 电子
model_task = launch_winner
role = weak_signal_sanity_check

target_industry = 电子
model_task = failure_reject
role = negative_control_placebo
```

电子任务不得成为主正向候选来源。若电子 placebo 能生成与汽车 launch 同样“漂亮”的 primitive，则说明 path-to-primitive 流程存在叙事过拟合风险。

### 4.4 排除范围

Explore10 不覆盖：

```text
电力设备主任务
固定 9 行业全量 industry model
跨行业 general model
P0.9C 原 semantic primitive 重跑
LGBM parameter regime comparison
full strategy backtest
entry / exit / position sizing policy
```

---

## 5. 输入边界

### 5.1 允许读取的 Explore9 artifacts

Explore10 可以读取以下内容作为 schema / audit / reference：

```text
Explore9/outputs/p0_9b/reports/p0_9b_report.md
Explore9/outputs/p0_9b/reports/p0_9b_manual_primitive_candidate_table.csv
Explore9/outputs/p0_9b/reports/p0_9b_primitive_to_p0_9c_requirement_map.csv
Explore9/outputs/p0_9b/reports/p0_9b_feature_family_importance.csv
Explore9/outputs/p0_9b/reports/p0_9b_tree_path_split_pattern_audit.csv
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_prediction_panel.parquet

Explore9/outputs/p0_9a/reports/p0_9a_recommendation_summary.csv
Explore9/outputs/p0_9a/reports/p0_9a_trainability_contract_matrix.csv
Explore9/outputs/p0_9a/reports/p0_9a_sample_weight_group_cap_audit.csv

Explore9/outputs/reports/p0_8_lgbm_score_bucket_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_score_bucket_selection_audit.csv
Explore9/outputs/reports/p0_8_search_bias_audit.csv

Explore9/outputs/cache/stock_day_label_panel.parquet
Explore9/outputs/reports/episode_lifecycle_labels.csv
```

All listed artifacts are hard preflight inputs. A missing or renamed artifact must fail preflight with `missing_reference_artifact`, not silently fall back to another file.

### 5.2 用途限制

上述 artifacts 只能用于：

```text
schema reference
task scope lock
sample denominator reference
row identity / label / fold / sample-weight reconciliation for
  p0_9b_locked_t1_train_eval_panel.parquet only
baseline reference
negative-control design
failure-mode explanation
P0.9B high-score coverage audit after candidate-freeze
```

不得用于：

```text
直接选择 primitive winner
直接选择 threshold
直接选择 LGBM hyperparameter
生成交易信号
生成 score bucket
label construction beyond the section 6.6 row/label reconciliation contract
修改 atomic feature bank
修改 candidate extraction / ranking budget
修改 candidate formula / threshold
```

`p0_9b_locked_t1_prediction_panel.parquet` is allowed only for a post-freeze
coverage audit answering whether frozen Explore10 candidates cover P0.9B
diagnostic high-score rows. The high-score definition must be predeclared in
the Explore10 config before any model/path/candidate metric is inspected.
P0.9B score coverage may not change feature definitions, path extraction,
candidate ranking, threshold buckets, primitive formulas, null families, or
recommendation status.

### 5.3 禁止输入

Explore10 禁止读取：

```text
Explore3-Explore8 trade_detail / portfolio_daily / signals / model_predictions
任何历史交易结果
任何人工交易记录
任何非 PIT 行业映射
任何 2025-2026 selection signal
任何 validation-tuned threshold file
```

---

## 6. 数据边界与时间纪律

### 6.1 数据链路

默认输入：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri_for_schema_only: Explore1/data/qlib/cn_data
fallback_provider_allowed_for_eligible_rows: false
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

`fallback_provider_uri_for_schema_only` may only be opened for field/calendar schema diagnostics. It may not supply any eligible-row feature, label, baseline, path-support denominator, primitive support row, or null/placebo row. The manifest must record:

```text
fallback_provider_schema_check_only = true
fallback_provider_eligible_row_count = 0
fallback_provider_feature_value_count = 0
```

### 6.2 时间范围

```text
research_start = 2017-01-01
research_end = 2024-12-31
observed_reference_start = 2025-01-01
observed_reference_end = 2026-04-30
```

### 6.3 Fold role

```text
fold_2020: core_oof_trainability_probe / support_eligible_only_if_explore10_trainable
fold_2021: core_oof / explore10_candidate_support_eligible
fold_2022: core_oof / explore10_candidate_support_eligible
fold_2023: core_oof / explore10_candidate_support_eligible
fold_2024: robustness_audit_only
```

`fold_2020` eligibility is conditional. P0.9B showed automotive launch `fold_2020` as no-fit, so Explore10 must not inherit support eligibility by calendar year alone. For each industry/task/fold:

```text
if model_fit_pass = false
or trainability_guardrail_pass = false:
  allowed_for_candidate_extraction = false
  allowed_for_candidate_support_count = false
  allowed_for_null_pass = false
  trainability_rejection_reason must be recorded
```

Promotion metrics use trainable core folds only, but the audit must still report:

```text
core_expected_fold_count = 4
core_trainable_fold_count
core_missing_fold_ids
core_missing_fold_reasons
```

`fold_2024` 不得用于：

```text
candidate support count
candidate extraction
threshold selection
primitive selection
null pass
recommendation upgrade
```

### 6.4 Purged expanding walk-forward

Explore10 必须继续使用 purged expanding walk-forward。

训练样本必须满足：

```text
train_label_window_end_date < validation_start_date
feature_asof_date <= signal_date
event_effective_date = next_trading_day(signal_date)
```

如果 `event_effective_date` 是 next-open 执行日，则：

```text
event_effective_date 当天 high / low / close / volume / money 不得作为 predictive feature；
event_effective_date 当天 open 只能作为 execution reference / label reference，不得作为 ranking feature。
```

### 6.5 Observed-reference 规则

Explore10 必须拆分三类 overlap：

```text
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
```

硬规则：

```text
decision overlap = false for all eligible rows
feature overlap = false for all eligible rows
label measurement overlap rows can only enter robustness audit, not core OOF candidate support
```

### 6.6 Sample panel authority

Explore10 row identity is rebuilt under `Explore10/`, but the canonical row
universe, labels, fold assignment, and pre-existing sample weights must reconcile
to the locked P0.9B train/eval panel.

Authoritative row-identity source:

```text
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet
```

Allowed source roles:

```text
row identity
label value reference
label-window date reference
fold assignment reference
sample-weight reference
lifecycle/context denominator reference
P0.9B row-count reconciliation
```

Forbidden source roles:

```text
Explore10 predictive feature value authority
Explore10 feature-bank formula authority
Explore10 path extraction input feature authority
Explore10 primitive threshold authority
Explore10 candidate ranking metric
Explore10 recommendation input
```

Explore10 must materialize its own event panels:

```text
Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet
```

These panels are built by selecting from the P0.9B train/eval panel by exact
scope, then recomputing all Explore10 predictive features from PIT source data.

Launch row selection:

```text
source panel row where:
  contract_id = T1_fixed_rounds_no_inner_validation
  task = industry_launch_winner_score_lgbm
  industry in {汽车, 电子}
  launch_model_train_eval_eligible = true
  sample_has_required_features = true
```

Failure row selection:

```text
source panel row where:
  contract_id = T1_fixed_rounds_no_inner_validation
  task = industry_failure_reject_score_lgbm
  industry in {汽车, 电子}
  failure_model_train_eval_eligible = true
  sample_has_required_features = true
  failure_decision_window in configured failure_decision_windows
```

No row may be created from P0.9B prediction score, leaf id, primitive output,
feature importance, or high-score bucket.

Required row reconciliation fields:

```text
source_panel_path
source_panel_hash
source_row_count
explore10_row_count
row_identity_match_count
row_identity_missing_from_explore10_count
row_identity_extra_in_explore10_count
label_value_mismatch_count
fold_assignment_mismatch_count
sample_weight_mismatch_count
reconciliation_pass
```

These fields must be included in `explore10_scope_lock.csv` and summarized in
`explore10_required_artifact_authority_audit.csv`.

### 6.7 Sample weight authority

All weighted metrics in Explore10 use:

```text
weight_column = final_sample_weight
```

Required source columns:

```text
base_sample_weight
final_sample_weight
sample_weight
instrument
event_instrument_year
fold_id
split
task
industry
```

Rules:

```text
sample_weight must equal final_sample_weight for every eligible row
final_sample_weight must be finite and > 0
base_sample_weight must be finite and >= 0
weighted rates use sum(final_sample_weight * indicator) / sum(final_sample_weight)
unweighted support counts use row count after candidate mask and eligibility filters
weighted support uses sum(final_sample_weight) after candidate mask and eligibility filters
```

Sample-weight guardrails:

```text
normalize_total_weight_per_industry_task_fold_split = true
max_instrument_year_weight_share = 0.08
max_instrument_year_weight_hhi = 0.08
sample_weight_alias_allowed = sample_weight -> final_sample_weight only
```

`explore10_fold_trainability_audit.csv` and
`explore10_lgbm_diagnostic_metrics.csv` must report both unweighted and weighted
event/positive counts.

Failure multi-window metrics must not sum repeated window weights after event
dedup. After applying `failure_event_level_metric_identity`, the retained row is
the earliest `failure_decision_effective_date`; if tied, the lexicographically
smallest `atomic_failure_event_id`. Its `final_sample_weight` is the only weight
used for event-level failure metrics. The audit must record:

```text
raw_window_row_count
dedup_event_count
duplicate_window_row_count
window_weight_summed_after_dedup = false
retained_weight_source = earliest_failure_decision_effective_date_row
```

### 6.8 Reference price authority

All launch labels use:

```text
event_effective_price_reference =
  adjusted open on event_effective_date from provider_uri
```

All failure labels use:

```text
failure_decision_effective_price_reference =
  adjusted open on failure_decision_effective_date from provider_uri

launch_effective_price_reference =
  adjusted open on launch_effective_date from provider_uri
```

Execution/reference prices follow:

```text
reference_price_rule = next_open
price_adjustment_mode = provider_ohlc_already_adjusted
fallback_provider_allowed_for_reference_price = false
```

If the required open is missing, non-finite, or <= 0:

```text
row_train_eval_eligible = false
reference_price_missing = true
reference_price_missing_reason must be recorded
```

No same-day high / low / close / volume / money on the effective date may be used
as a predictive feature. They may only be used for label measurement after
`event_effective_date` / `failure_decision_effective_date` is fixed.

---

## 7. 样本单位

### 7.1 Launch atomic event row

主样本单位：

```text
atomic_launch_event_row
```

字段至少包括：

```text
atomic_event_id
source_launch_stratum_event_id
launch_episode_id
instrument
target_industry
signal_date
event_effective_date
event_effective_price_reference
feature_asof_date
fold_id
fold_role
model_task
label_version
sample_panel_version
```

主任务只允许：

```text
target_industry = 汽车
model_task = launch_winner
```

### 7.2 Failure atomic event row

次级样本单位：

```text
atomic_failure_decision_row
```

字段至少包括：

```text
atomic_failure_event_id
source_launch_stratum_event_id
failure_decision_window
failure_signal_date
failure_decision_effective_date
failure_decision_effective_price_reference
launch_effective_date
launch_effective_price_reference
target_50h120_not_reached_before_decision_effective_date
feature_asof_date
fold_id
fold_role
model_task
```

Failure 多窗口必须做 event-level dedup 与 weight normalization：

```text
failure_event_dedup_candidate_id =
  hash(
    task,
    target_industry,
    primitive_family,
    normalized_failure_formula_excluding_window_only_tokens,
    ordered_token_id_list_excluding_window_only_tokens,
    failure_direction,
    feature_asof_rule,
    effective_date_rule,
    label_version
  )

failure_event_level_metric_identity =
  failure_event_dedup_candidate_id + source_launch_stratum_event_id
```

主 failure diagnostic metric 必须使用
`failure_event_dedup_candidate_id + source_launch_stratum_event_id` 做去重，
不得直接用 full primitive id，也不得只用 primitive family / direction。
多窗口版本只能通过 earliest `failure_decision_effective_date` 进入主指标。
Window-only tokens must be listed in `failure_window_only_token_list` and
excluded from the dedup candidate hash.

Required artifact:

```text
explore10_failure_event_dedup_audit.csv
```

The audit must prove that coverage, false reject, and drawdown-avoided metrics
are not inflated by repeated failure windows and are not over-merged across
different normalized failure formulas.

### 7.3 Path pattern row

```text
lgbm_path_pattern_row
```

字段至少包括：

```text
path_pattern_raw_id
industry
task
fold_id
tree_id
leaf_id_internal_only
path_depth
split_feature_list
split_operator_list
split_threshold_raw_list
split_threshold_quantile_list
split_feature_family_list
path_train_support_count
path_oof_support_count
path_train_weighted_support
path_oof_weighted_support
path_train_positive_rate
path_oof_positive_rate
path_baseline_rate
```

`leaf_id_internal_only` 不得进入 primitive formula。

### 7.4 Audited primitive candidate row

```text
audited_atomic_primitive_candidate
```

字段至少包括：

```text
primitive_id
primitive_family
industry
task
primitive_text
observable_token_list
formula_text_resolved
source_path_pattern_ids
source_feature_family_set
feature_asof_rule
effective_date_rule
reference_price_rule
denominator_scope
expected_direction
real_metric_name
real_metric_formula_text
null_adjusted_signal_status
manual_primitive_allowed_for_next_requirement
reason_if_not_allowed
```

---

## 8. Label Dictionary

Explore10 不使用 Alpha158 默认 label。所有 label 继续使用 Explore9 / Explore10 自定义 long-horizon labels。

### 8.1 Launch labels

令：

```text
E = event_effective_date
P_E = event_effective_price_reference
```

窗口定义：

```text
label_window_start = E
label_window_N = [E, trading_day_offset(E, N - 1)]
label_window_includes_effective_date_high_low = true
```

必需 label：

```text
launch_winner_50h120 =
  max(high over [E, E+119]) / P_E - 1 >= 0.50

launch_winner_50c120 =
  max(close over [E, E+119]) / P_E - 1 >= 0.50

launch_winner_100h240 =
  max(high over [E, E+239]) / P_E - 1 >= 1.00

launch_future_max_drawdown_60d =
  min(low over [E, E+59]) / P_E - 1

first_20pct_gain_date =
  first date d in [E, E+59] where high_d / P_E - 1 >= 0.20

if first_20pct_gain_date exists:
  launch_drawdown_before_20pct_gain =
    min(low over [E, first_20pct_gain_date]) / P_E - 1
else:
  first_20pct_gain_missing = true
  launch_drawdown_before_20pct_gain =
    min(low over [E, E+59]) / P_E - 1

launch_false_positive_primary =
  launch_winner_50h120 = false
  and launch_future_max_drawdown_60d <= -0.12
```

### 8.2 Failure labels

令：

```text
D = failure_decision_effective_date
P_D = failure_decision_effective_price_reference
L = launch_effective_date
P_L = launch_effective_price_reference
```

必需 label：

```text
target_50h120_not_reached_before_decision_effective_date =
  max(high over [L, previous_trading_day(D)]) / P_L - 1 < 0.50

failure_drawdown_from_decision_60d =
  min(low over [D, D+59]) / P_D - 1

failure_reject_positive_primary =
  target_50h120_not_reached_before_decision_effective_date = true
  and failure_drawdown_from_decision_60d <= -0.12

false_reject_vs_launch_target_50h120 =
  target_50h120_not_reached_before_decision_effective_date = true
  and max(high over [D, L+119]) / P_L - 1 >= 0.50

false_reject_vs_decision_target_50h120 =
  max(high over [D, D+119]) / P_D - 1 >= 0.50
```

P1 / main candidate false-reject audit must use `false_reject_vs_launch_target_50h120` if failure primitives are ever promoted. `false_reject_vs_decision_target_50h120` is diagnostic only.

### 8.3 Required label dictionary output

`explore10_label_dictionary.csv` 必须记录：

```text
label_name
model_task
label_type
reference_date_field
reference_price_field
horizon_trading_days
label_window_start_rule
label_window_end_rule
positive_condition
negative_condition
missing_condition
eligibility_field
used_for_training
used_for_path_metric
used_for_null
used_for_next_requirement_gate
```

---

## 9. Alpha158-like Atomic Feature Bank

### 9.1 总原则

Explore10 使用 `Alpha158-like`，不是直接复用 Alpha158 默认任务、默认 label 或默认 workflow。

Explore10 只借鉴 Alpha158 的低层表达思想：

```text
用 OHLCV / rolling / normalized / rank / distance / volatility / volume-price relations
构造中性、连续、低层 atomic features。
```

Explore10 不得使用：

```text
Qlib Alpha158 default label
Qlib default train/test split
非 PIT universe
非 PIT industry
future return label from Ref(close, -2) / Ref(close, -1)
```

### 9.2 Feature families

Atomic feature bank 至少包含以下 family。

Before any model fitting or path extraction, implementation must materialize a pre-run source dictionary:

```text
Explore10/configs/atomic_feature_bank_v1.yaml
```

The run then writes the resolved audit dictionary:

```text
Explore10/outputs/explore10/reports/explore10_atomic_feature_dictionary.csv
```

The manifest must record:

```text
atomic_feature_bank_source_path
atomic_feature_bank_source_hash
resolved_feature_dictionary_hash
feature_added_after_metric_inspection_count = 0
feature_removed_after_metric_inspection_count = 0
```

#### A. kbar / candle shape

```text
open_close_ratio
high_close_ratio
low_close_ratio
close_open_return
intraday_range_pct
body_pct
upper_shadow_pct
lower_shadow_pct
close_location
gap_open_pct
gap_close_pct
```

#### B. rolling return

窗口：

```text
1d, 2d, 3d, 5d, 10d, 20d, 40d, 60d, 120d
```

特征：

```text
ret_Nd
close_over_close_Nd
return_slope_Nd
return_acceleration_5_20
return_acceleration_20_60
```

#### C. rolling price distance

```text
close_over_ma_N
close_over_median_N
close_over_max_high_N
close_over_min_low_N
distance_to_high_N
distance_to_low_N
launch_gain_from_recent_low_N
drawdown_from_recent_high_N
```

N:

```text
5, 10, 20, 40, 60, 120
```

#### D. volatility / range

```text
atr_like_10
atr_like_20
atr20_pct
volatility_return_std_N
amplitude_N
range_expansion_ratio_5_20
range_expansion_ratio_20_60
high_vol_constructive_ratio
high_vol_destructive_ratio
```

#### E. volume / money

```text
volume_over_mean_N
money_over_mean_N
volume_zscore_N
money_zscore_N
turnover_proxy_ratio_N
money_price_coherence_N
volume_price_divergence_N
```

N:

```text
5, 10, 20, 60
```

#### F. cross-sectional rank

```text
ret_Nd_market_rank
ret_Nd_industry_rank
money_Nd_market_rank
money_Nd_industry_rank
atr20_pct_market_rank
atr20_pct_industry_rank
rank_jump_5d
rank_persistence_3d
rank_persistence_5d
rank_evaporation_2d
rank_evaporation_3d
rank_evaporation_5d
```

#### G. industry / market context

```text
industry_breadth_20d
industry_breadth_change_5d
industry_money_breadth_20d
industry_relative_strength_vs_market_20d
industry_relative_strength_vs_market_60d
market_regime
market_breadth_20d
market_volatility_regime
risk_on_off_bucket
```

#### H. launch lifecycle context

```text
launch_family
launch_lifecycle_pool
prelaunch_drawdown_60d
prelaunch_drawdown_120d
prelaunch_repair_age
post_20_state
post_30_state
late_acceleration_flag
sparse_strong_day_flag
```

Lifecycle context can be used only if it is observable as of `signal_date`.

Lifecycle context is split into two roles:

```text
context_slice_only:
  launch_family
  launch_lifecycle_pool
  post_20_state
  post_30_state
  late_acceleration_flag

atomic_lifecycle_numeric_or_flag:
  prelaunch_drawdown_60d
  prelaunch_drawdown_120d
  prelaunch_repair_age
  sparse_strong_day_flag
```

`context_slice_only` fields may be used for denominator construction, baseline
cells, and slice stability audits only. They must be recorded with:

```text
allowed_for_path_extraction = false
allowed_for_primitive_formula = false
```

If a lifecycle concept is needed as a model/path/formula token, it must be
re-expressed as an atomic OHLCV-derived feature under a separate feature name
with explicit `formula_text`, `formula_hash`, `feature_asof_rule`, and PIT
denominator. Semantic lifecycle labels may not be smuggled into primitive
formulas through the atomic bank.

### 9.2.1 Formula template authority

`Explore10/configs/atomic_feature_bank_v1.yaml` is not allowed to be a name-only
feature list. It must materialize every expanded feature row before model fitting.

The source YAML must include:

```text
feature_name
feature_family
feature_role
formula_template_id
formula_text
raw_inputs
window
cross_section_scope
normalization_scope
feature_asof_rule
missing_value_policy
allowed_for_path_extraction
allowed_for_primitive_formula
```

Formula DSL definitions:

```text
t = signal_date
ref(x, n) = value of x n trading days before t
roll_mean(x, N) = mean over [t-N+1, t]
roll_median(x, N) = median over [t-N+1, t]
roll_std(x, N) = sample std over [t-N+1, t]
roll_max(x, N) = max over [t-N+1, t]
roll_min(x, N) = min over [t-N+1, t]
logret_1d = log(close_t / ref(close, 1))
pct_rank(x, denominator) = average-tie percentile rank in [0, 1]
feature_ref(feature_name, n) = already-computed feature value n trading days before t
safe_div(a, b) = null if b is missing, non-finite, or 0
```

Allowed canonical formula templates:

```text
open_close_ratio =
  safe_div(open_t, ref(close, 1)) - 1
high_close_ratio =
  safe_div(high_t, close_t) - 1
low_close_ratio =
  safe_div(low_t, close_t) - 1
close_open_return =
  safe_div(close_t, open_t) - 1
intraday_range_pct =
  safe_div(high_t - low_t, ref(close, 1))
body_pct =
  abs(close_t - open_t) / ref(close, 1)
upper_shadow_pct =
  (high_t - max(open_t, close_t)) / ref(close, 1)
lower_shadow_pct =
  (min(open_t, close_t) - low_t) / ref(close, 1)
close_location =
  safe_div(close_t - low_t, high_t - low_t)
gap_open_pct =
  safe_div(open_t, ref(close, 1)) - 1
gap_close_pct =
  safe_div(close_t, ref(close, 1)) - 1

ret_Nd =
  safe_div(close_t, ref(close, N)) - 1
close_over_close_Nd =
  safe_div(close_t, ref(close, N))
return_slope_Nd =
  slope of linear regression of log(close) on trading-day index over [t-N+1, t]
return_acceleration_5_20 =
  ret_5d - ret_20d * 5 / 20
return_acceleration_20_60 =
  ret_20d - ret_60d * 20 / 60

close_over_ma_N =
  safe_div(close_t, roll_mean(close, N)) - 1
close_over_median_N =
  safe_div(close_t, roll_median(close, N)) - 1
close_over_max_high_N =
  safe_div(close_t, roll_max(high, N)) - 1
close_over_min_low_N =
  safe_div(close_t, roll_min(low, N)) - 1
distance_to_high_N =
  safe_div(roll_max(high, N), close_t) - 1
distance_to_low_N =
  safe_div(close_t, roll_min(low, N)) - 1
launch_gain_from_recent_low_N =
  safe_div(close_t, roll_min(low, N)) - 1
drawdown_from_recent_high_N =
  safe_div(close_t, roll_max(high, N)) - 1

true_range =
  max(high_t - low_t, abs(high_t - ref(close, 1)), abs(low_t - ref(close, 1)))
atr_like_N =
  roll_mean(true_range, N)
atr20_pct =
  safe_div(atr_like_20, close_t)
volatility_return_std_N =
  roll_std(logret_1d, N)
amplitude_N =
  safe_div(roll_max(high, N), roll_min(low, N)) - 1
range_expansion_ratio_5_20 =
  safe_div(atr_like_5, atr_like_20)
range_expansion_ratio_20_60 =
  safe_div(atr_like_20, atr_like_60)
high_vol_constructive_ratio =
  mean((logret_1d > 0) and (true_range / close_t >= atr20_pct) over [t-19, t])
high_vol_destructive_ratio =
  mean((logret_1d < 0) and (true_range / close_t >= atr20_pct) over [t-19, t])

volume_over_mean_N =
  safe_div(volume_t, roll_mean(volume, N))
money_over_mean_N =
  safe_div(money_t, roll_mean(money, N))
volume_zscore_N =
  safe_div(volume_t - roll_mean(volume, N), roll_std(volume, N))
money_zscore_N =
  safe_div(money_t - roll_mean(money, N), roll_std(money, N))
turnover_proxy_ratio_N =
  safe_div(money_t, roll_median(money, N))
money_price_coherence_N =
  rolling corr(logret_1d, money_t / ref(money, 1) - 1, N)
volume_price_divergence_N =
  pct_rank(volume_over_mean_N, market) - pct_rank(ret_Nd, market)

ret_Nd_market_rank =
  pct_rank(ret_Nd, PIT market denominator on t)
ret_Nd_industry_rank =
  pct_rank(ret_Nd, PIT same-industry denominator on t)
money_Nd_market_rank =
  pct_rank(money_over_mean_N, PIT market denominator on t)
money_Nd_industry_rank =
  pct_rank(money_over_mean_N, PIT same-industry denominator on t)
atr20_pct_market_rank =
  pct_rank(atr20_pct, PIT market denominator on t)
atr20_pct_industry_rank =
  pct_rank(atr20_pct, PIT same-industry denominator on t)
rank_jump_5d =
  ret_5d_market_rank_t - feature_ref(ret_5d_market_rank, 5)
rank_persistence_3d =
  roll_mean(ret_5d_market_rank, 3)
rank_persistence_5d =
  roll_mean(ret_5d_market_rank, 5)
rank_evaporation_2d =
  feature_ref(ret_5d_market_rank, 2) - ret_5d_market_rank_t
rank_evaporation_3d =
  feature_ref(ret_5d_market_rank, 3) - ret_5d_market_rank_t
rank_evaporation_5d =
  feature_ref(ret_5d_market_rank, 5) - ret_5d_market_rank_t

industry_breadth_20d =
  mean(ret_20d > 0 over PIT same-industry denominator on t)
industry_breadth_change_5d =
  industry_breadth_20d_t - feature_ref(industry_breadth_20d, 5)
industry_money_breadth_20d =
  mean(money_over_mean_20 > 1 over PIT same-industry denominator on t)
industry_relative_strength_vs_market_Nd =
  mean(ret_Nd over PIT same-industry denominator on t)
  - mean(ret_Nd over PIT market denominator on t)
market_breadth_20d =
  mean(ret_20d > 0 over PIT market denominator on t)
market_volatility_regime =
  predeclared quantile bucket of benchmark volatility_return_std_20 on train fold
market_regime =
  predeclared bucket from benchmark ret_20d and market_volatility_regime
risk_on_off_bucket =
  predeclared bucket from market_breadth_20d and market_regime

prelaunch_drawdown_Nd =
  safe_div(close_t, roll_max(high, N)) - 1
prelaunch_repair_age =
  trading days since most recent roll_min(low, 120)
sparse_strong_day_flag =
  ret_1d_market_rank >= train_q95 and money_over_mean_20 >= train_q80
```

Any feature in section 9.2 not expressible by one of the templates above must be
removed from the source dictionary before the first run and recorded in:

```text
explore10_feature_bank_preflight_audit.csv
```

with `removed_before_metric_inspection = true`. No new formula template may be
introduced after any model, path, candidate, null, placebo, slice, or
concentration metric is inspected.

### 9.3 Feature dictionary contract

`explore10_atomic_feature_dictionary.csv` must include:

```text
feature_name
feature_family
feature_role
formula_text
formula_hash
raw_inputs
raw_required_field_exempt
window
feature_asof_rule
pit_required
normalization_scope
transform_type
cross_section_scope
frozen_train_transform_required
train_fold_quantile_required
eligible_denominator_field
missing_value_policy
allowed_for_launch
allowed_for_failure
allowed_for_path_extraction
allowed_for_primitive_formula
leakage_risk_level
```

Any feature used in a formula, split pattern, primitive, or path identity must appear in this dictionary.

The dictionary is a pre-model contract. No feature, raw alias, quantile alias, rolling reference, or lifecycle/context field may be introduced after validation metrics, path metrics, null metrics, or candidate metrics are inspected.

### 9.4 Feature bank preflight audit

Before model fitting or path extraction, the resolved feature bank must pass a
feature-count, missingness, constant-feature, duplication, and family-dominance
preflight.

`explore10_feature_bank_preflight_audit.csv` must include:

```text
feature_bank_source_dictionary_hash
resolved_feature_dictionary_hash
feature_generation_code_hash
feature_count_total
feature_count_by_family
feature_count_removed_before_run
removed_feature_list_hash
removed_before_metric_inspection
allowed_for_path_extraction_count
allowed_for_primitive_formula_count
missing_row_rate
missing_weight_share
constant_or_near_constant_rate
duplicate_or_high_corr_cluster_count
duplicate_or_high_corr_abs_threshold
max_feature_family_share
feature_family_missing_weight_share
feature_family_missing_weight_share_max
feature_family_dominance_pass
missingness_pass
constant_feature_pass
duplicate_cluster_pass
feature_bank_preflight_pass
```

Hard gates:

```text
missing_weight_share <= thresholds.max_feature_missing_weight_share
feature_family_missing_weight_share_max <= thresholds.max_feature_family_missing_weight_share
constant_or_near_constant_rate <= thresholds.max_constant_feature_rate
max_feature_family_share <= thresholds.max_feature_family_share
duplicate_or_high_corr_cluster_count <= thresholds.max_duplicate_feature_cluster_count
```

Near-constant features are features whose train-fold weighted standard
deviation is below `thresholds.min_feature_weighted_std` or whose distinct
finite value count is below `thresholds.min_feature_distinct_value_count`.
Duplicate / high-correlation clusters use train-fold eligible rows only and the
absolute correlation threshold from the config.

If `feature_bank_preflight_pass = false`, the run may write diagnostics and a
report, but no path extraction, primitive candidate, null pass, or proceed
recommendation is allowed.

### 9.5 Raw input exemptions

Raw provider fields:

```text
open, high, low, close, volume, money, factor
```

must appear in dictionary with:

```text
feature_role = raw_input
raw_required_field_exempt = true
```

But raw inputs cannot be used directly as unnormalized predictive features except where explicitly allowed, such as `open` as event execution reference.

---

## 10. Feature As-Of and Leakage Contract

### 10.1 Close-derived signal rule

For all close-derived launch and failure formulas:

```text
signal_date = date where close-derived condition is known
event_effective_date = next_trading_day(signal_date)
feature_asof_date = signal_date
```

Forbidden:

```text
feature computed from event_effective_date close
feature computed from event_effective_date high
feature computed from event_effective_date low
feature computed from event_effective_date volume
feature computed from event_effective_date money
```

Allowed only for execution / label reference:

```text
event_effective_date open
```

### 10.2 Feature normalization

Explore10 separates daily PIT cross-sectional features from train-fold-fitted transforms.

Daily PIT cross-sectional features include:

```text
market_rank
industry_rank
market_breadth
industry_breadth
market_regime
industry_relative_strength
```

These are computed on each `signal_date` using only the PIT eligible universe and PIT industry membership known as of `signal_date`. They are not fitted on the validation fold, but their same-date denominator must be recorded.

Train-fold-fitted transforms include:

```text
split-threshold quantile buckets
winsorization cutoffs
z-score mean/std
scaling parameters
clipping thresholds
primitive threshold bucket boundaries
```

These must be computed:

```text
within train fold only
using PIT eligible universe
using signal_date or earlier information
```

Validation fold must use frozen train-fold transform.

The audit must distinguish:

```text
cross_section_scope = market | industry | none
cross_section_denominator_count
train_fitted_parameter_source_fold
frozen_train_transform_used
validation_refit_violation_count
```

### 10.3 Required audit

`explore10_feature_asof_leakage_audit.csv` must include:

```text
feature_name
feature_asof_date
signal_date
event_effective_date
uses_event_effective_date_ohlc
uses_future_field
uses_observed_reference
cross_section_scope
cross_section_denominator_count
train_fitted_parameter_source_fold
frozen_train_transform_used
validation_refit_violation_count
fallback_provider_used_for_feature
eligible_row_count
violation_count
pass
```

Explore10 main candidate requires:

```text
feature_asof_leakage_violation_count = 0
```

---

## 11. LGBM Probe Contract

### 11.1 Model role

LGBM in Explore10 is:

```text
diagnostic path extraction probe
```

It is not:

```text
deployable model
selected model
strategy score
P1 validator
```

### 11.2 Fixed model configuration

Primary task:

```yaml
automotive_launch_lgbm_probe:
  contract: T1_fixed_rounds_no_inner_validation
  num_boost_round: 64
  early_stopping: false
  objective: binary
  metric: [auc, binary_logloss]
  max_depth: 3
  num_leaves: 8
  min_data_in_leaf: 30
  learning_rate: 0.05
  feature_fraction: 0.80
  bagging_fraction: 0.80
  bagging_freq: 1
  lambda_l1: 0.0
  lambda_l2: 1.0
  random_seed: 20260507
```

Secondary failure task:

```yaml
automotive_failure_lgbm_probe:
  contract: T1_fixed_rounds_no_inner_validation
  num_boost_round: 32
  early_stopping: false
  objective: binary
  metric: [auc, binary_logloss]
  max_depth: 3
  num_leaves: 8
  min_data_in_leaf: 30
  learning_rate: 0.05
  feature_fraction: 0.80
  bagging_fraction: 0.80
  bagging_freq: 1
  lambda_l1: 0.0
  lambda_l2: 1.0
  random_seed: 20260507
```

Explore10 may not search hyperparameters.

### 11.3 Trainability

Explore10 must report per fold:

```text
train_event_count_after_purge
train_positive_count_after_purge
validation_event_count
validation_positive_count
distinct_instruments
distinct_instrument_years
feature_available_count
model_fit_pass
prediction_uniqueness
prediction_std
tree_count
used_feature_count
```

Mechanical pass definition:

```text
model_fit_pass = true
  iff model training completes without exception
  and prediction rows are written for the validation fold
  and prediction values are finite
  and tree_count = configured_num_boost_round

trainability_guardrail_pass = true
  iff train_event_count_after_purge >= thresholds.min_train_event_count
  and train_positive_count_after_purge >= thresholds.min_train_positive_count
  and validation_event_count >= thresholds.min_validation_event_count
  and validation_positive_count >= thresholds.min_validation_positive_count
  and distinct_instruments >= thresholds.min_distinct_instruments
  and distinct_instrument_years >= thresholds.min_distinct_instrument_years
  and feature_available_count >= thresholds.min_feature_available_count
  and prediction_uniqueness >= thresholds.min_prediction_uniqueness
  and prediction_std >= thresholds.min_prediction_std
  and tree_count = configured_num_boost_round
  and used_feature_count >= thresholds.min_used_feature_count

explore10_fold_trainability_pass = true
  iff model_fit_pass = true
  and trainability_guardrail_pass = true
```

`prediction_uniqueness` must be computed as the count of distinct finite
validation predictions after rounding to 12 decimal places. `prediction_std`
must be computed on finite validation predictions only.

Required artifact:

```text
explore10_fold_trainability_audit.csv
```

If `explore10_fold_trainability_pass = false`, the fold cannot contribute path
extraction, candidate support, token coverage, null pass, slice pass, or
promotion. The audit must record the exact failed predicate.

### 11.4 Model output limitations

Explore10 may output:

```text
OOF diagnostic metrics
feature family importance
tree path dumps
split pattern statistics
```

Explore10 may not output:

```text
selected_score_bucket
top_decile_trade_list
buy/sell signal
portfolio return
strategy backtest
```

---

## 12. LGBM Path Extraction

### 12.1 Raw path extraction

For each trainable core fold and each locked LGBM model:

```text
for each tree:
  for each leaf:
    extract root-to-leaf path
```

Each raw path row must include:

```text
industry
task
fold_id
tree_id
leaf_id_internal_only
path_depth
leaf_value
path_split_count
split_feature_ordered_list
split_operator_ordered_list
split_threshold_raw_ordered_list
split_gain_ordered_list
split_cover_ordered_list
path_train_support_count
path_oof_support_count
path_train_weighted_support
path_oof_weighted_support
```

### 12.2 Raw path exclusions

Exclude path from primitive extraction if:

```text
path_depth = 0
path_train_support_count < path_extraction.min_path_train_support_count
path_contains_forbidden_feature = true
path_feature_asof_violation = true
```

`path_oof_support_count` and `path_oof_weighted_support` are raw-path audit
fields only at this stage. They must not be used to exclude, rank, canonicalize,
or translate paths before the primitive candidate formula is frozen. OOF support
can only reject an already frozen primitive through the token coverage audit and
must be reported as a post-freeze reason, not as a pre-freeze extraction filter.

Excluded paths still appear in audit.

### 12.3 Required artifact

`explore10_lgbm_raw_path_dump.csv`

---

## 13. Threshold Quantile Canonicalization

### 13.1 Why

Raw split thresholds are fold-specific and cannot be used directly as primitive thresholds.

Forbidden primitive threshold:

```text
atr20_pct > 0.04317
```

Allowed primitive threshold:

```text
atr20_pct >= train_fold_q80
```

### 13.2 Quantile buckets

Allowed threshold buckets:

```text
q05, q10, q20, q30, q40, q50, q60, q70, q80, q90, q95
```

For each split threshold:

```text
threshold_quantile_bucket =
  nearest allowed quantile bucket computed on train fold eligible denominator
```

### 13.3 Directional bucket rules

For feature direction:

```text
greater_than:
  feature >= train_qXX

less_than:
  feature <= train_qXX

range:
  train_qXX <= feature <= train_qYY
```

### 13.4 Required artifact

`explore10_path_threshold_quantile_audit.csv`

Fields:

```text
feature_name
fold_id
raw_threshold
train_quantile_value
assigned_quantile_bucket
quantile_error
denominator_count
quantile_missing
pass
```

---

## 14. Path Pattern Canonicalization

### 14.1 Two identities

Explore10 must generate two path identities:

```text
strict_path_pattern_id:
  preserves ordered tree path structure

relaxed_feature_set_pattern_id:
  ignores tree order and uses feature + direction + quantile bucket set
```

### 14.2 Primitive aggregation identity

Primitive candidate extraction uses:

```text
relaxed_feature_set_pattern_id
```

not raw leaf id.

### 14.3 Candidate identity fields

```text
industry
task
feature_family_set
feature_name_set
operator_direction_set
quantile_bucket_set
feature_asof_rule
effective_date_rule
label_version
feature_bank_version
lgbm_config_hash
sample_panel_version
training_code_version
```

### 14.4 Merge tolerance

Continuous threshold bucket can be merged across folds if:

```text
same feature
same operator direction
quantile bucket distance <= 1 allowed bucket step
same feature family
same task
same industry
```

No merge across industries or tasks.

### 14.5 Required artifacts

```text
explore10_path_pattern_canonicalization.csv
explore10_path_pattern_fold_presence.csv
```

---

## 15. Primitive Candidate Generation

### 15.1 Candidate extraction source

Primitive candidates may only be generated from:

```text
train-fold path structure
predeclared feature-family mapping
predeclared canonicalization rules
```

Validation OOF metrics or validation support counts may not be used to choose
which path becomes candidate. Candidate identity must be frozen before any OOF
support, OOF label, OOF lift, P0.9B high-score coverage, null, placebo, slice,
or concentration result is inspected.

### 15.2 Candidate extraction budget

Per industry/task/fold:

```text
max_raw_paths_considered = 2000
max_patterns_after_canonicalization = 300
max_primitive_candidates_per_task = 50
```

Candidate ranking for extraction must use train-only information:

```text
path_train_support_count
path_train_weighted_support
split_gain_train
path_depth_penalty
feature_family_diversity
```

Forbidden ranking criteria:

```text
validation support count
validation lift
validation AUC contribution
validation positive rate
validation top event story
P0.9B high-score coverage
fold_2024 performance
```

### 15.3 Candidate freeze audit

Before any OOF support, OOF label, real metric, null, placebo, concentration,
slice, dropout, or P0.9B high-score coverage result is computed, the run must
write a frozen candidate inventory hash.

`explore10_candidate_freeze_audit.csv` must include:

```text
primitive_id
industry
task
candidate_generation_stage
feature_bank_source_hash
resolved_feature_dictionary_hash
candidate_extraction_config_hash
canonicalization_config_hash
candidate_formula_hash
candidate_frozen_before_oof_support
candidate_frozen_before_oof_metric
candidate_frozen_before_p0_9b_score_coverage
oof_support_used_for_candidate_filter
p0_9b_score_used_for_candidate_filter
validation_metric_used_for_candidate_filter
fold_2024_used_for_candidate_filter
pass
```

### 15.4 Primitive translation rules

A path pattern can become primitive candidate only if:

```text
uses 2 to 6 observable tokens
does not contain leaf id
does not contain LGBM score
does not contain raw numeric threshold
uses train-fold quantile threshold or config threshold
has feature_asof_rule
has effective_date_rule
has denominator_scope
has expected_direction
```

### 15.5 Candidate types

```text
atomic_single_family_context
atomic_cross_family_context
repair_volatility_rank_context
breadth_rank_volatility_context
failure_destructive_path_context
negative_control_placebo_context
```

### 15.6 Required artifact

`explore10_atomic_primitive_candidate_table.csv`

---

## 16. Token Coverage Audit

### 16.1 Motivation

P0.9B failed partly because automotive launch primitive masks had zero support. Therefore token coverage is the first hard gate.

### 16.2 Required metrics

For each primitive candidate and core fold:

```text
denominator_event_count
token_1_support_count
token_2_support_count
token_3_support_count
all_token_support_count
all_token_weighted_support
support_rate
positive_count
weighted_positive_count
support_missing_reason
```

### 16.3 Coverage gates

Primary automotive launch primitive candidate requires:

```text
all_token_support_count >= thresholds.min_primitive_oof_support_count
all_token_weighted_support >= thresholds.min_primitive_weighted_support
supporting_core_fold_count >= thresholds.min_supporting_core_folds
supporting_validation_year_count >= thresholds.min_supporting_validation_years
```

If coverage fails:

```text
manual_primitive_allowed_for_next_requirement = false
reason_if_not_allowed = zero_or_insufficient_support
```

No null / lift conclusion may be reported as positive for zero-support primitives.

### 16.4 Required artifact

`explore10_primitive_token_coverage_audit.csv`

### 16.5 P0.9B high-score coverage audit

P0.9B high-score coverage is audit-only. It answers whether frozen Explore10
atomic candidates cover the P0.9B diagnostic high-score rows that the old
semantic primitives missed. It may not select, rank, rescue, or reject a
candidate by itself.

`explore10_p0_9b_high_score_coverage_audit.csv` must include:

```text
p0_9b_prediction_panel_path
p0_9b_prediction_panel_hash
high_score_definition_config_hash
high_score_scope
high_score_threshold_rule
high_score_row_count
primitive_id
candidate_formula_hash
candidate_frozen_before_score_coverage
covered_high_score_row_count
covered_high_score_weight_share
covered_high_score_positive_rate
coverage_used_for_feature_selection
coverage_used_for_candidate_selection
coverage_used_for_threshold_selection
coverage_used_for_recommendation
audit_only_pass
```

Required pass conditions:

```text
candidate_frozen_before_score_coverage = true
coverage_used_for_feature_selection = false
coverage_used_for_candidate_selection = false
coverage_used_for_threshold_selection = false
coverage_used_for_recommendation = false
```

---

## 17. Primitive Evaluation Metrics

### 17.1 Launch primitive real metric

Primary real metric:

```text
launch_primitive_oof_lift_vs_industry_task_fold_baseline =
  weighted_positive_rate(primitive rows in core OOF)
  / weighted_positive_rate(all eligible industry/task rows in same core fold)
```

Aggregation:

```text
fold_equal_weighted_mean_lift =
  mean(lift_fold over eligible core folds)
```

Secondary metrics:

```text
positive_rate
baseline_positive_rate
winner_coverage
false_positive_rate
future_max_drawdown_60d_median
drawdown_before_20pct_gain_median
high_only_50h120_rate
```

### 17.2 Failure primitive real metric

Primary failure diagnostic metric:

```text
failure_lift_minus_false_reject_penalty =
  failure_positive_rate_lift
  - max(0, false_reject_vs_launch_target_rate - baseline_false_reject_vs_launch_target_rate)
```

Secondary:

```text
failure_positive_rate
failure_precision_lift
false_reject_vs_launch_target_rate
false_reject_vs_decision_target_rate
drawdown_avoided_vs_matched_delay
filter_before_12pct_drawdown_rate
```

Failure primitives are secondary by default and cannot override automotive launch primary result.

### 17.3 Required artifact

`explore10_primitive_real_metric_audit.csv`

---

## 18. Baseline Contract

### 18.1 Launch baseline

For automotive launch:

```text
industry_task_fold_baseline =
  all eligible 汽车 launch rows in same fold and task
```

Additional baselines:

```text
same_launch_family_baseline
same_lifecycle_pool_baseline
candidate_scope_weighted_baseline
P0.9B semantic_primitive_baseline_audit
```

### 18.2 Candidate-scope weighted baseline

For mixed-family primitive:

```text
candidate_scope_weighted_baseline =
  weighted average of baseline cells by candidate row family/lifecycle/regime composition
```

Baseline cells must meet:

```text
baseline_cell_event_count >= thresholds.min_baseline_cell_event_count
baseline_cell_positive_count >= thresholds.min_baseline_cell_positive_count
```

Sparse fallback hierarchy:

```text
exact cell
drop variant
drop lifecycle_pool
drop regime bucket
industry + task all eligible rows
```

### 18.3 Baseline missing gates

```text
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share <= thresholds.max_candidate_baseline_sparse_cell_weight_share
```

### 18.4 Required artifacts

```text
explore10_industry_task_fold_baseline.csv
explore10_candidate_scope_weighted_baseline.csv
explore10_baseline_sparsity_audit.csv
```

---

## 19. Null / Placebo / Search Bias Audit

### 19.1 Null families

Explore10 must run at least:

```text
label_permutation_within_industry_fold
instrument_year_block_shuffle
year_block_shuffle_within_industry
path_structure_null_from_permuted_lgbm
feature_family_placebo_dropout
electronics_failure_negative_control_placebo
```

Shared null execution rules:

```text
null_repeats_screening = config.null.repeats_screening
null_repeats_promotion = config.null.repeats_promotion
random_seed_root = config.null.random_seed
fold_roles_used = trainable core folds only
fold_2024_used_in_null = false
candidate_generation_budget = same as real run
candidate_freeze_required_before_real_oof_metric = true
candidate_freeze_required_before_null_metric = true
```

Every null row must preserve:

```text
industry
task
fold_id
train/validation split
row eligibility
final_sample_weight
instrument
event_instrument_year
failure_event_level_metric_identity after failure dedup
```

Null families are defined as follows:

```text
label_permutation_within_industry_fold:
  permute validation labels within industry + task + fold_id;
  evaluate already-frozen real candidates on permuted validation labels;
  do not retrain LGBM;
  used as frozen-candidate label-noise null.

instrument_year_block_shuffle:
  shuffle label blocks keyed by event_instrument_year within industry + task + fold_id;
  preserve within-block label sequence, row weights, and candidate masks;
  evaluate already-frozen real candidates;
  used to test instrument-year concentration sensitivity.

year_block_shuffle_within_industry:
  shuffle validation-year label blocks within industry + task across trainable core folds;
  preserve per-year positive counts and row weights;
  evaluate already-frozen real candidates;
  used to test year/regime dependence.

path_structure_null_from_permuted_lgbm:
  permute train labels within industry + task + train fold;
  retrain the fixed LGBM with the same feature bank and config;
  extract paths and generate null candidates using the same train-only budget;
  evaluate frozen null candidates on real validation labels;
  used as the main path-to-primitive search-bias null.

feature_family_placebo_dropout:
  remove one feature family from the fixed feature bank before LGBM fit;
  rerun fixed LGBM/path extraction for diagnostic deltas only;
  cannot create, rank, rescue, or reject a real primitive candidate.

electronics_failure_negative_control_placebo:
  run the same path-to-primitive pipeline on 电子 + failure_reject;
  any stable candidate is treated as narrative-overfit evidence, not positive evidence.
```

`placebo_stress_pass` for a primary automotive launch candidate requires:

```text
electronics_failure_stable_candidate_count <= thresholds.max_placebo_stable_candidate_count
electronics_failure_equal_or_stronger_candidate_count <= thresholds.max_placebo_equal_or_stronger_candidate_count
feature_family_placebo_creates_equal_or_stronger_candidate = false
candidate_formula_not_recreated_by_placebo = true
```

Equal-or-stronger means:

```text
placebo candidate has same or lower empirical_p_value
and same or higher real_oof_metric
and same or higher supporting_core_fold_count
```

All four placebo pass predicates must be written to
`explore10_placebo_stress_audit.csv`.

### 19.2 Main null: path-structure null

For each null repeat:

```text
1. permute train labels within industry + fold, preserving class balance;
2. retrain fixed LGBM with same feature bank and same config;
3. extract paths with same extraction budget and canonicalization;
4. generate primitive candidates with same train-only policy;
5. evaluate frozen null candidates on real validation labels;
6. aggregate candidate-level OOF null metric.
```

This is the main test for path-to-primitive search bias.

### 19.3 Candidate-level p-value

For each real candidate C:

```text
real_metric(C)
null_metric_distribution(C_or_matched_pattern_family)
empirical_p_value =
  (1 + count(null_metric >= real_metric)) / (1 + null_repeats)
```

If exact candidate identity is not present in null repeats, use matched null by:

```text
same task
same token count
same feature-family count
same support bucket
same path depth bucket
```

Matched-null fallback must be machine-audited. For every candidate:

```text
exact_null_identity_available
null_match_level
matched_null_repeat_count
matched_null_candidate_count
matched_null_metric_count
matched_null_support_bucket
matched_null_sparse
null_uninterpretable_due_to_sparse_match
```

Promotion cannot use a sparse matched null. If:

```text
matched_null_metric_count < thresholds.min_null_metric_count_for_candidate_p_value
or matched_null_repeat_count < thresholds.min_null_repeat_count_for_promotion
```

then:

```text
null_adjusted_signal_status = null_uninterpretable_due_to_sparse_match
atomic_primitive_candidate_for_next_requirement = false
```

`repeats_screening` is diagnostic only. Any candidate marked
`stable_atomic_primitive` must use the promotion-repeat null distribution.

### 19.4 Candidate-level null aggregation

Candidate-level null aggregation must be materialized separately so the run
cannot silently average fold p-values or treat one fold as the candidate result.

`explore10_candidate_level_null_aggregation.csv` must include:

```text
primitive_id
real_oof_metric
null_repeat_id
null_candidate_id_or_match_family
null_oof_metric
exact_null_identity_available
null_match_level
matched_null_repeat_count
matched_null_metric_count
empirical_p_value
null_p95
fdr_q_value
candidate_level_null_pass
```

Candidate-level null pass must be computed from the pooled candidate-level OOF
metric distribution after the candidate formula is frozen. It may not be derived
from:

```text
average(per_fold_p_value)
best_fold_only_null
per_fold_null_pass_count_as_candidate_pass
```

The null aggregation audit must record:

```text
per_fold_p_value_average_used = false
best_fold_only_null_used = false
per_fold_null_pass_count_used_as_candidate_pass = false
```

### 19.5 FDR

Explore10 must compute:

```text
fdr_q_value
```

FDR is computed across all frozen `汽车 + launch_winner` primitive candidates
generated within the predeclared extraction budget before coverage, null,
placebo, concentration, slice, or manualizability rejection. Secondary failure
and electronics placebo candidates must use separate diagnostic FDR families and
cannot reduce or improve the primary automotive launch FDR.

### 19.6 Status

```text
stable_atomic_primitive:
  real_metric > null_p95
  empirical_p_value <= thresholds.max_empirical_p_value
  fdr_q_value <= thresholds.max_fdr_q_value
  placebo_stress_pass = true

weak_but_not_collapsed:
  real_metric > null_mean
  empirical_p_value <= thresholds.max_weak_empirical_p_value
  but not stable

collapsed_under_null:
  real_metric <= null_mean
  or empirical_p_value > thresholds.max_weak_empirical_p_value

null_uninterpretable_due_to_sparse_match:
  matched_null_metric_count < thresholds.min_null_metric_count_for_candidate_p_value
  or matched_null_repeat_count < thresholds.min_null_repeat_count_for_promotion
```

### 19.7 Required artifacts

```text
explore10_path_structure_null_audit.csv
explore10_label_permutation_null_audit.csv
explore10_instrument_year_block_null_audit.csv
explore10_placebo_stress_audit.csv
explore10_search_bias_summary.csv
explore10_null_match_sparsity_audit.csv
explore10_candidate_level_null_aggregation.csv
```

All null-family audit files must include the shared fields:

```text
null_family
null_repeat_id
industry
task
fold_id
fold_role
primitive_id
shuffle_unit
labels_permuted_or_shuffled
train_labels_permuted
validation_labels_permuted
lgbm_retrained
candidate_generation_replayed
candidate_formula_frozen_before_null
row_count
weighted_row_count
positive_count
weighted_positive_count
real_metric_reference
null_metric
random_seed
fold_2024_used
pass
```

`explore10_path_structure_null_audit.csv` additionally must include:

```text
null_model_id
null_model_config_hash
null_feature_bank_hash
null_raw_path_count
null_canonical_pattern_count
null_candidate_count
same_extraction_budget_as_real
same_canonicalization_as_real
same_train_only_policy_as_real
```

`explore10_placebo_stress_audit.csv` additionally must include:

```text
placebo_scope
placebo_candidate_id
matched_primary_primitive_id
electronics_failure_stable_candidate_count
electronics_failure_equal_or_stronger_candidate_count
feature_family_placebo_creates_equal_or_stronger_candidate
candidate_formula_not_recreated_by_placebo
placebo_stress_pass
```

---

## 20. Slice Stability Audit

### 20.1 Required slices

For each candidate:

```text
fold_id
validation_year
market_regime
launch_family
launch_lifecycle_pool
volatility_bucket
liquidity_bucket
instrument_year
```

Failure candidates additionally:

```text
failure_decision_window
failure_delay_bucket
```

### 20.2 Gates

Primary automotive launch candidate requires:

```text
supporting_core_fold_count >= thresholds.min_supporting_core_folds
supporting_validation_year_count >= thresholds.min_supporting_validation_years
supporting_primary_slice_count >= thresholds.min_supporting_primary_slices
fold_2024_used_for_support = false
```

### 20.3 Required artifact

`explore10_slice_stability_audit.csv`

---

## 21. Concentration Audit

### 21.1 Instrument concentration

Metrics:

```text
top1_instrument_contribution
top5_instrument_contribution
top_instrument_year_contribution
instrument_year_hhi
weight_share_top_instrument_year
```

Gates:

```text
top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
top_instrument_year_contribution <= thresholds.max_top_instrument_year_contribution
instrument_year_hhi <= thresholds.max_instrument_year_hhi
```

### 21.2 Regime concentration

Metrics:

```text
regime_hhi
top1_regime_contribution
```

Gates:

```text
regime_hhi <= thresholds.max_regime_hhi
top1_regime_contribution <= thresholds.max_top1_regime_contribution
```

### 21.3 Required artifact

`explore10_concentration_audit.csv`

---

## 22. Feature-Family Dropout Audit

### 22.1 Purpose

Dropout verifies whether the primitive interpretation matches the model mechanism.

### 22.2 Required dropout families

```text
price_distance
rolling_return
volatility_range
volume_money
cross_section_rank
industry_market_context
launch_lifecycle_context
```

### 22.3 Rules

Feature-family dropout is diagnostic only.

It may not be used to:

```text
select primitive by validation performance
change feature bank after validation
change LGBM config
change threshold bucket
change candidate formula
```

### 22.4 Required artifact

`explore10_feature_family_dropout_audit.csv`

---

## 23. Atomic Primitive Manualizability

A primitive is manualizable only if:

```text
uses no LGBM score
uses no leaf id
uses no model probability
uses no validation-tuned threshold
uses no raw numeric threshold
uses only train-fold quantile bucket or fixed config threshold
has formula_text_resolved
has feature_asof_rule
has effective_date_rule
has reference_price_rule
can be recomputed from PIT OHLCV + PIT industry membership
```

Required artifact:

```text
explore10_manualizability_audit.csv
```

---

## 24. Nonselection And Forbidden Output Audits

Explore10 must prove that metrics and thresholds are used only for audit gates
after candidates are frozen.

### 24.1 Metric nonselection audit

`explore10_metric_nonselection_audit.csv` must include:

```text
selection_surface
candidate_stage
metric_name
metric_available_before_candidate_freeze
metric_used_for_feature_bank_edit
metric_used_for_path_filter
metric_used_for_candidate_ranking
metric_used_for_threshold_choice
metric_used_for_recommendation
allowed_gate_only_usage
violation_count
pass
```

Required pass:

```text
metric_used_for_feature_bank_edit = false
metric_used_for_path_filter = false
metric_used_for_candidate_ranking = false
metric_used_for_threshold_choice = false
```

### 24.2 Threshold nonselection audit

`explore10_threshold_nonselection_audit.csv` must include:

```text
primitive_id
feature_name
threshold_source
threshold_bucket
raw_threshold_used_in_formula
validation_metric_used_to_choose_threshold
p0_9b_score_coverage_used_to_choose_threshold
threshold_declared_before_oof_metric
train_fold_quantile_used
violation_count
pass
```

Required pass:

```text
raw_threshold_used_in_formula = false
validation_metric_used_to_choose_threshold = false
p0_9b_score_coverage_used_to_choose_threshold = false
threshold_declared_before_oof_metric = true
```

### 24.3 Forbidden recommendation self-check

`explore10_forbidden_recommendation_self_check.csv` must include every forbidden
recommendation/output enum in this requirement and record:

```text
forbidden_output
present_in_manifest
present_in_report
present_in_candidate_table
present_in_next_requirement_map
violation_count
pass
```

Required pass:

```text
violation_count = 0
```

---

## 25. Promotion / Rejection Gates

### 25.1 Audit pass taxonomy

Explore10 separates run-discipline audits from candidate-quality audits.

```text
discipline_audit_pass:
  artifact completeness
  required artifact authority
  threshold config consistency
  feature-asof
  observed-reference decision / feature overlap
  walk-forward purge
  fallback provider zero eligible rows
  feature bank preflight
  candidate freeze
  P0.9B high-score coverage audit-only usage
  metric / threshold nonselection
  forbidden recommendation self-check
  cache tracking

primary_candidate_quality_pass:
  token coverage
  baseline missing / sparsity
  candidate-level null
  FDR
  placebo stress
  concentration
  slice stability
  manualizability

diagnostic_quality_pass:
  secondary failure quality diagnostics
  electronics weak-signal / placebo diagnostics
```

`explore10_audit_pass_taxonomy.csv` must include:

```text
audit_name
artifact_name
audit_class
scope
discipline_audit_pass
primary_candidate_quality_pass
diagnostic_quality_pass
blocks_entire_run
blocks_primary_candidate
blocks_secondary_or_placebo_only
pass
```

Hard rule:

```text
secondary failure / electronics placebo quality failure does not block
  proceed_to_explore11_manual_atomic_primitive_formula_discovery

secondary failure / electronics placebo discipline failure blocks the whole run
```

### 25.2 Primary automotive launch candidate gate

A candidate can be marked:

```text
atomic_primitive_candidate_for_next_requirement = true
```

only if all are true:

```text
scope = 汽车 + launch_winner
discipline_audit_pass = true
primary_candidate_quality_pass = true
candidate_freeze_pass = true
feature_asof_leakage_violation_count = 0
observed_reference_decision_overlap_count = 0
observed_reference_feature_overlap_count = 0
token_coverage_pass = true
baseline_missing_pass = true
baseline_sparsity_pass = true
slice_stability_pass = true
concentration_pass = true
manualizability_pass = true
null_adjusted_signal_status = stable_atomic_primitive
null_match_sparsity_pass = true
placebo_stress_pass = true
p0_9b_high_score_coverage_audit_only_pass = true
fold_2024_used_for_support = false
no_metric_selection_violation = true
no_threshold_selection_violation = true
```

### 25.3 Secondary failure candidate gate

Failure output can only be:

```text
secondary_atomic_failure_primitive_for_diagnostic = true
```

It is never eligible for:

```text
atomic_primitive_candidate_for_next_requirement = true
explore10_next_requirement_candidate_map
proceed_to_explore11_manual_atomic_primitive_formula_discovery
```

If all false-reject gates pass:

```text
false_reject_vs_launch_target_rate <= thresholds.max_false_reject_vs_launch_target_rate
pending_winner_coverage_loss <= thresholds.max_pending_winner_coverage_loss
drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_matched_delay
```

then it may be marked:

```text
secondary_failure_mechanism_diagnostic_for_appendix = true
```

Even then, failure output remains appendix-only and does not become a trading
reject rule, primary candidate, or next-requirement seed.

### 25.4 Rejection reasons

Allowed rejection reasons:

```text
zero_or_insufficient_support
one_fold_only
one_slice_only
collapsed_under_null
placebo_only
instrument_concentration_too_high
instrument_year_concentration_too_high
regime_concentration_too_high
baseline_missing_or_sparse
feature_asof_leakage
observed_reference_overlap
not_manualizable
candidate_freeze_violation
metric_selection_violation
threshold_selection_violation
p0_9b_score_selection_violation
null_uninterpretable_due_to_sparse_match
```

---

## 26. Required Outputs

All full row-level panels must be parquet cache only.

### 26.1 Required report artifacts

```text
explore10_run_manifest.json
explore10_scope_lock.csv
explore10_label_dictionary.csv
explore10_atomic_feature_dictionary.csv
explore10_feature_bank_preflight_audit.csv
explore10_feature_asof_leakage_audit.csv
explore10_observed_reference_overlap_audit.csv
explore10_walk_forward_purge_audit.csv
explore10_fold_trainability_audit.csv
explore10_lgbm_diagnostic_metrics.csv
explore10_lgbm_feature_importance.csv
explore10_lgbm_raw_path_dump.csv
explore10_path_threshold_quantile_audit.csv
explore10_path_pattern_canonicalization.csv
explore10_path_pattern_fold_presence.csv
explore10_candidate_freeze_audit.csv
explore10_atomic_primitive_candidate_table.csv
explore10_p0_9b_high_score_coverage_audit.csv
explore10_primitive_token_coverage_audit.csv
explore10_primitive_real_metric_audit.csv
explore10_industry_task_fold_baseline.csv
explore10_candidate_scope_weighted_baseline.csv
explore10_baseline_sparsity_audit.csv
explore10_path_structure_null_audit.csv
explore10_label_permutation_null_audit.csv
explore10_instrument_year_block_null_audit.csv
explore10_placebo_stress_audit.csv
explore10_search_bias_summary.csv
explore10_null_match_sparsity_audit.csv
explore10_candidate_level_null_aggregation.csv
explore10_slice_stability_audit.csv
explore10_concentration_audit.csv
explore10_failure_event_dedup_audit.csv
explore10_feature_family_dropout_audit.csv
explore10_manualizability_audit.csv
explore10_audit_pass_taxonomy.csv
explore10_metric_nonselection_audit.csv
explore10_threshold_nonselection_audit.csv
explore10_forbidden_recommendation_self_check.csv
explore10_required_artifact_authority_audit.csv
explore10_threshold_config_consistency_audit.csv
explore10_atomic_primitive_rejection_summary.csv
explore10_secondary_failure_diagnostic_map.csv
explore10_next_requirement_candidate_map.csv
explore10_report.md
```

### 26.2 Required cache artifacts

```text
Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet
Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
Explore10/outputs/explore10/cache/explore10_lgbm_model_dump.parquet
Explore10/outputs/explore10/cache/explore10_full_path_candidate_panel.parquet
```

Cache tracking rule:

```text
git check-ignore Explore10/outputs/explore10/cache/*.parquet must pass
full row-level panels cannot be tracked CSV
report CSV/JSON/markdown artifacts live under Explore10/outputs/explore10/reports/
```

### 26.3 Mechanical authority self-checks

`explore10_required_artifact_authority_audit.csv` must check:

```text
artifact_name
referenced_section
listed_in_section_26
exists_at_manifest_path
manifest_row_count
manifest_col_count
manifest_file_size
is_cache_artifact
is_report_artifact
cache_parquet_ignored_by_git
row_level_csv_generated_by_default
row_level_csv_tracked_by_git
pass
```

Required pass:

```text
all artifacts referenced in sections 6-25 appear in section 26
all section 26 artifacts exist at manifest paths
manifest row_count / col_count / file_size are recorded where applicable
all cache parquet files are ignored by git
row_level_csv_generated_by_default = false
row_level_csv_tracked_by_git = false
```

`explore10_threshold_config_consistency_audit.csv` must check:

```text
threshold_name
referenced_in_requirement
present_in_config
config_value
used_by_runtime
marked_unused_diagnostic
alias_of
alias_target_present
threshold_alias_mismatch
pass
```

Required pass:

```text
all thresholds.* used in text appear in config
all config thresholds are used or marked unused_diagnostic
threshold_alias_mismatch = false
```

### 26.4 Name-only artifact schema closure

The following artifacts are not allowed to be free-form outputs. They must use
the schemas below in addition to any fields required earlier.

`explore10_run_manifest.json` must include:

```text
phase
command
config_path
config_hash
requirement_path
requirement_hash
atomic_feature_bank_source_path
atomic_feature_bank_source_hash
resolved_feature_dictionary_hash
source_panel_path
source_panel_hash
sample_panel_version
sample_weight_policy_hash
reference_price_rule
output_root
recommendation
discipline_audit_pass
primary_candidate_count
accepted_primary_candidate_count
secondary_diagnostic_count
forbidden_output_flags
fallback_provider_schema_check_only
fallback_provider_eligible_row_count
fallback_provider_feature_value_count
artifact_manifest
```

Each `artifact_manifest` entry must include:

```text
artifact_name
path
artifact_class
row_count
col_count
file_size_bytes
content_hash
tracked_by_git
git_check_ignore_pass
required_by_section
```

`explore10_scope_lock.csv` must include:

```text
industry
task
role
fold_id
fold_role
contract_id
source_panel_path
source_panel_hash
source_row_count
explore10_row_count
row_identity_match_count
row_identity_missing_from_explore10_count
row_identity_extra_in_explore10_count
label_value_mismatch_count
fold_assignment_mismatch_count
sample_weight_mismatch_count
model_fit_pass
trainability_guardrail_pass
explore10_fold_trainability_pass
allowed_for_path_extraction
allowed_for_candidate_support_count
allowed_for_null_pass
allowed_for_recommendation_upgrade
fold_2024_used_for_support
scope_lock_pass
```

`explore10_observed_reference_overlap_audit.csv` must include:

```text
industry
task
fold_id
fold_role
eligible_row_count
observed_reference_decision_overlap_count
observed_reference_feature_overlap_count
observed_reference_label_measurement_overlap_count
label_measurement_overlap_core_support_count
decision_overlap_used_for_candidate_support
feature_overlap_used_for_candidate_support
label_measurement_overlap_used_for_candidate_support
observed_reference_overlap_pass
```

`explore10_walk_forward_purge_audit.csv` must include:

```text
industry
task
fold_id
raw_train_rows
train_rows_after_purge
validation_rows
train_label_window_end_date_max
validation_start_date
rows_with_train_label_window_end_crossing_validation
rows_with_event_effective_date_crossing_validation
rows_with_feature_asof_crossing_validation
event_effective_date_open_used_as_feature_count
walk_forward_purge_pass
```

`explore10_lgbm_diagnostic_metrics.csv` must include:

```text
industry
task
fold_id
fold_role
model_role
contract_id
num_boost_round
tree_count
train_event_count_after_purge
train_positive_count_after_purge
train_weighted_event_count_after_purge
train_weighted_positive_count_after_purge
validation_event_count
validation_positive_count
validation_weighted_event_count
validation_weighted_positive_count
auc
binary_logloss
brier_score
prediction_std
prediction_uniqueness
used_feature_count
model_fit_pass
trainability_guardrail_pass
```

`explore10_lgbm_feature_importance.csv` must include:

```text
industry
task
fold_id
feature_name
feature_family
importance_gain
importance_split
gain_share_within_fold
split_share_within_fold
allowed_for_path_extraction
allowed_for_primitive_formula
used_for_feature_selection
used_for_candidate_ranking
diagnostic_only
```

`explore10_atomic_primitive_rejection_summary.csv` must include:

```text
primitive_id
industry
task
primitive_family
token_coverage_pass
baseline_missing_pass
baseline_sparsity_pass
candidate_level_null_pass
fdr_pass
placebo_stress_pass
slice_stability_pass
concentration_pass
manualizability_pass
candidate_freeze_pass
metric_nonselection_pass
threshold_nonselection_pass
atomic_primitive_candidate_for_next_requirement
reason_if_not_allowed
blocking_audit_name
```

`explore10_next_requirement_candidate_map.csv` must include:

```text
primitive_id
industry
task
primitive_family
formula_text_resolved
observable_token_list
feature_asof_rule
effective_date_rule
reference_price_rule
denominator_scope
real_metric_name
real_metric_value
null_adjusted_signal_status
required_next_phase_validation
why_this_is_not_a_strategy
allowed_for_next_requirement
```

It must contain only:

```text
industry = 汽车
task = launch_winner
allowed_for_next_requirement = true
```

`explore10_secondary_failure_diagnostic_map.csv` must include:

```text
primitive_id
industry
task
formula_text_resolved
false_reject_vs_launch_target_rate
pending_winner_coverage_loss
drawdown_avoided_vs_matched_delay
secondary_failure_mechanism_diagnostic_for_appendix
appendix_only
allowed_for_next_requirement
reason_not_primary
```

Required values:

```text
appendix_only = true
allowed_for_next_requirement = false
```

---

## 27. Report Structure

`explore10_report.md` 至少包含：

```text
1. 执行结论
2. Explore10 定位与禁止结论
3. Why semantic primitive failed and why atomic feature bank is tested
4. Scope lock: 汽车 launch primary, 汽车 failure secondary, 电子 placebo
5. Data discipline: PIT, feature-asof, observed-reference, purge
6. Alpha158-like feature bank preflight and coverage
7. Fold trainability audit
8. LGBM diagnostic metrics
9. Path extraction and quantile canonicalization
10. Path pattern fold presence
11. Candidate freeze audit
12. Primitive token coverage
13. P0.9B high-score coverage audit-only
14. Primitive real metrics
15. Candidate-level null aggregation / placebo / search-bias audit
16. Slice stability and concentration
17. Failure event dedup appendix audit
18. Feature-family dropout
19. Manualizability audit
20. Discipline vs quality audit taxonomy
21. Metric / threshold nonselection self-check
22. Required artifact authority and threshold config consistency
23. Accepted atomic primitive candidates
24. Rejected primitive candidates and reasons
25. Secondary failure appendix diagnostics
26. Next requirement map
27. Recommendation
28. Self-check: no model selection, no score bucket, no backtest, no strategy
```

---

## 28. Recommendation Enum

Explore10 recommendation must be one of:

```text
proceed_to_explore11_manual_atomic_primitive_formula_discovery
continue_explore10_atomic_feature_bank_discovery
stop_due_to_zero_or_insufficient_atomic_support
stop_due_to_null_or_placebo_collapse
stop_due_to_concentration_or_instability
stop_due_to_feature_asof_or_data_discipline_violation
```

Forbidden recommendations:

```text
proceed_to_explore10_backtest
proceed_to_strategy_backtest
candidate_for_p1_strategy
validated_model
selected_lgbm_model
selected_score_bucket
freeze_strategy
```

### 28.1 Proceed condition

`proceed_to_explore11_manual_atomic_primitive_formula_discovery` is allowed only if:

```text
at least one atomic_primitive_candidate_for_next_requirement = true
discipline_audit_pass = true for the whole run
primary_candidate_quality_pass = true for at least one 汽车 + launch_winner candidate
explore10_next_requirement_candidate_map has at least one row
explore10_next_requirement_candidate_map contains only 汽车 + launch_winner rows
explore10_secondary_failure_diagnostic_map rows, if any, are appendix-only
secondary failure / electronics placebo quality failure is not counted as primary failure
secondary failure / electronics placebo discipline failure blocks proceed
no metric / threshold / candidate-freeze violation
no forbidden recommendation self-check violation
```

---

## 29. Config Sketch

```yaml
phase: explore10
title: alpha158_like_atomic_feature_bank_path_to_primitive
output_root: Explore10/outputs/explore10

scope:
  primary:
    industry: 汽车
    task: launch_winner
    role: primary_candidate_source
  secondary:
    industry: 汽车
    task: failure_reject
    role: secondary_diagnostic
  placebo:
    - industry: 电子
      task: launch_winner
      role: weak_signal_sanity
    - industry: 电子
      task: failure_reject
      role: negative_control_placebo

folds:
  core_expected: [2020, 2021, 2022, 2023]
  support_eligible_if_trainable: [2020, 2021, 2022, 2023]
  robustness_only: [2024]
  fold_2024_used_for_support: false

data:
  provider_uri: Explore7/data/qlib/cn_data_pit
  fallback_provider_uri_for_schema_only: Explore1/data/qlib/cn_data
  fallback_provider_allowed_for_eligible_rows: false
  universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
  industry_membership: Explore7/data/targets/pit_industry_membership.csv
  price_adjustment_mode: provider_ohlc_already_adjusted
  required_fields: [open, high, low, close, volume, money, factor]
  source_train_eval_panel: Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet
  row_identity_source_role: labels_folds_weights_only

reference_price:
  rule: next_open
  event_effective_price_reference: adjusted_open_on_event_effective_date
  failure_decision_effective_price_reference: adjusted_open_on_failure_decision_effective_date
  fallback_provider_allowed_for_reference_price: false
  missing_or_nonpositive_reference_price_blocks_row: true

sample_weight:
  source_weight_column: final_sample_weight
  required_columns: [base_sample_weight, final_sample_weight, sample_weight]
  sample_weight_alias: sample_weight -> final_sample_weight
  weighted_metric_weight_column: final_sample_weight
  normalize_total_weight_per_industry_task_fold_split: true
  max_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.08
  failure_event_level_weight_policy: earliest_failure_decision_effective_date_row
  failure_window_weight_summed_after_dedup: false

p0_9b_reference:
  prediction_panel: Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_prediction_panel.parquet
  usage: audit_only_after_candidate_freeze
  high_score_scope: same_industry_task_fold_core_oof
  high_score_threshold_rule: prediction_score_top_decile_within_industry_task_fold
  can_change_feature_bank: false
  can_change_candidate_formula: false
  can_change_threshold: false
  can_change_recommendation: false

feature_bank:
  version: alpha158_like_v1_plus_explore9_domain
  source_dictionary: Explore10/configs/atomic_feature_bank_v1.yaml
  source_dictionary_is_expanded_feature_row_contract: true
  formula_template_set: requirement_section_9_2_1
  formulas_may_be_added_after_metric_inspection: false
  name_only_features_allowed: false
  use_qlib_alpha158_default_label: false
  feature_asof_date_rule: signal_date
  cross_section_features_use_pit_signal_date_denominator: true
  train_fitted_transform_scope: train_fold_only
  quantile_buckets: [q05, q10, q20, q30, q40, q50, q60, q70, q80, q90, q95]
  context_slice_only_features: [launch_family, launch_lifecycle_pool, post_20_state, post_30_state, late_acceleration_flag]
  context_slice_only_allowed_for_path_extraction: false
  context_slice_only_allowed_for_primitive_formula: false

feature_bank_preflight:
  duplicate_high_corr_abs_threshold: 0.995
  near_constant_uses_train_fold_only: true
  fail_run_before_path_extraction_if_preflight_fails: true

candidate_freeze:
  required_before_oof_support: true
  required_before_oof_metric: true
  required_before_p0_9b_score_coverage: true
  oof_support_can_filter_raw_paths: false

failure_dedup:
  use_failure_event_dedup_candidate_id: true
  metric_identity: failure_event_dedup_candidate_id + source_launch_stratum_event_id
  exclude_window_only_tokens_from_dedup_hash: true
  primary_metric_uses_earliest_failure_decision_effective_date: true

audit_pass_taxonomy:
  secondary_failure_quality_failure_blocks_primary_proceed: false
  electronics_placebo_quality_failure_blocks_primary_proceed: false
  secondary_or_placebo_discipline_failure_blocks_run: true

lgbm_probe:
  early_stopping: false
  hyperparameter_search: false
  launch:
    num_boost_round: 64
    objective: binary
    max_depth: 3
    num_leaves: 8
    min_data_in_leaf: 30
    learning_rate: 0.05
    feature_fraction: 0.80
    bagging_fraction: 0.80
    lambda_l2: 1.0
  failure:
    num_boost_round: 32
    objective: binary
    max_depth: 3
    num_leaves: 8
    min_data_in_leaf: 30
    learning_rate: 0.05
    feature_fraction: 0.80
    bagging_fraction: 0.80
    lambda_l2: 1.0

path_extraction:
  max_raw_paths_considered: 2000
  max_patterns_after_canonicalization: 300
  max_primitive_candidates_per_task: 50
  min_path_train_support_count: 30
  min_path_oof_support_count_for_audit_only: 10
  allowed_quantile_buckets: [q05, q10, q20, q30, q40, q50, q60, q70, q80, q90, q95]

thresholds:
  min_train_event_count: 200
  min_train_positive_count: 20
  min_validation_event_count: 30
  min_validation_positive_count: 5
  min_distinct_instruments: 20
  min_distinct_instrument_years: 20
  min_feature_available_count: 50
  min_prediction_uniqueness: 10
  min_prediction_std: 0.000001
  min_used_feature_count: 2

  max_feature_missing_weight_share: 0.20
  max_feature_family_missing_weight_share: 0.35
  max_constant_feature_rate: 0.25
  max_feature_family_share: 0.45
  max_duplicate_feature_cluster_count: 50
  min_feature_weighted_std: 0.000000000001
  min_feature_distinct_value_count: 3

  min_primitive_oof_support_count: 30
  min_primitive_weighted_support: 30
  min_supporting_core_folds: 2
  min_supporting_validation_years: 2
  min_supporting_primary_slices: 2

  min_baseline_cell_event_count: 50
  min_baseline_cell_positive_count: 5
  max_candidate_baseline_missing_row_rate: 0.05
  max_candidate_baseline_missing_weight_share: 0.05
  max_candidate_baseline_sparse_cell_weight_share: 0.20

  max_top1_instrument_contribution: 0.20
  max_top5_instrument_contribution: 0.50
  max_top_instrument_year_contribution: 0.12
  max_instrument_year_hhi: 0.08
  max_regime_hhi: 0.60
  max_top1_regime_contribution: 0.75

  max_empirical_p_value: 0.10
  max_fdr_q_value: 0.20
  max_weak_empirical_p_value: 0.25
  min_null_metric_count_for_candidate_p_value: 30
  min_null_repeat_count_for_promotion: 100
  max_placebo_stable_candidate_count: 0
  max_placebo_equal_or_stronger_candidate_count: 0

  max_false_reject_vs_launch_target_rate: 0.20
  max_pending_winner_coverage_loss: 0.25
  min_drawdown_avoided_vs_matched_delay: 0.00

null:
  enabled: true
  repeats_screening: 50
  repeats_promotion: 100
  random_seed: 20260507
  n_jobs: 24
  families:
    - label_permutation_within_industry_fold
    - instrument_year_block_shuffle
    - year_block_shuffle_within_industry
    - path_structure_null_from_permuted_lgbm
    - feature_family_placebo_dropout
    - electronics_failure_negative_control_placebo

artifact_authority:
  all_referenced_artifacts_must_appear_in_section_26: true
  all_section_26_artifacts_must_exist: true
  cache_parquet_must_be_ignored_by_git: true
  row_level_csv_generated_by_default_allowed: false

threshold_config_consistency:
  all_text_thresholds_must_exist_in_config: true
  unused_config_thresholds_require_unused_diagnostic_marker: true
  threshold_alias_mismatch_allowed: false

forbidden_outputs:
  enforce_ban: true
  values:
    - proceed_to_explore10_backtest
    - selected_score_bucket
    - actionable_trade_rule
    - freeze_strategy
```

---

## 30. Implementation Commands

Required commands:

```bash
uv run python Explore10/scripts/run_explore10.py profile-explore10 \
  --config Explore10/configs/atomic_feature_bank_explore10.yaml

uv run python Explore10/scripts/run_explore10.py report-explore10 \
  --config Explore10/configs/atomic_feature_bank_explore10.yaml
```

Explore9 code may be imported or reused as shared implementation, but Explore10 command entrypoints, configs, reports, and cache outputs must live under `Explore10/`. No temporary `Explore9/outputs/explore10/` compatibility output path is allowed for accepted implementation.

---

## 31. Preflight Checklist

Before running Explore10, implementation must verify:

```text
[ ] target industry 汽车 exact PIT mapping exists
[ ] all Explore9 reference artifacts listed in section 5.1 exist at exact paths
[ ] primary task launch_winner event panel exists
[ ] core folds 2020-2023 trainability audited under fixed probe contract
[ ] untrainable core folds excluded from extraction/support/null pass with recorded reason
[ ] fold_2024 is robustness only
[ ] feature_asof_date = signal_date
[ ] event_effective_date high/low/close/volume/money not used as feature
[ ] fallback provider used only for schema diagnostics and contributes zero eligible rows
[ ] atomic feature bank source dictionary exists and source hash is recorded
[ ] Alpha158-like feature dictionary complete
[ ] feature bank preflight passes feature-count / missingness / constant / duplicate / family-dominance gates
[ ] feature dictionary includes raw_required_field_exempt and formula_hash for every required row
[ ] context_slice_only lifecycle fields are not allowed for path extraction or primitive formula
[ ] cross-sectional rank/breadth features use PIT signal-date denominator, not validation-fitted transforms
[ ] no Qlib Alpha158 default label used
[ ] no Explore3-Explore8 trading result used
[ ] observed-reference decision/feature overlap excluded
[ ] label measurement overlap excluded from support
[ ] candidate inventory is frozen before OOF support / OOF metric / P0.9B score coverage inspection
[ ] raw path extraction does not filter or rank by OOF support
[ ] P0.9B prediction panel is audit-only and cannot alter features, candidates, thresholds, or recommendation
[ ] full row-level outputs go to ignored parquet cache
[ ] null family configured before validation metrics inspected
[ ] null matched-fallback sparsity gates are configured before validation metrics inspected
[ ] candidate-level null aggregation is used; fold-level p-value averaging is forbidden
[ ] failure appendix uses failure_event_dedup_candidate_id + source_launch_stratum_event_id
[ ] discipline audit pass is separated from primary and diagnostic quality pass
[ ] candidate extraction budget fixed before run
[ ] metric / threshold / candidate-freeze / artifact-authority audits are required outputs
[ ] all thresholds referenced in text appear in config or fail threshold consistency audit
[ ] recommendation enum cannot output backtest/freeze/strategy
```

---

## 32. Final Boundary Statement

Explore10 的研究边界必须在报告中重复：

```text
This is an atomic primitive discovery phase.
Alpha158-like features are used as a low-level expression bank, not as a trading strategy.
LGBM is used only as a path-extraction probe.
Tree leaves and model scores are not trading rules.
Only train-fold quantile-bucketed, T-day observable, audited primitive candidates may enter the next requirement.
No P1 validation, no Explore10 strategy backtest, no model deployment, and no frozen rule is produced.
```
