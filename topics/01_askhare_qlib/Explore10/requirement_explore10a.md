# Explore10A 需求说明：汽车样本宽度与 Alpha158-like Feature Bank Hygiene 审计

> 文件名：`requirement_explore10a.md`
> 阶段：`Explore10A` / `P0.10A`
> 标题：Automotive Sample-Width and Feature-Bank Hygiene Audit
> 状态：implementation-ready requirement draft
> 生成日期：2026-05-07
> 重要说明：Explore10A 是修复型审计阶段，不是 primitive discovery、不是 P1 validation、不是策略回测。

---

## 0. 一句话结论

Explore10A 只做一件事：

```text
先证明为什么 Explore10 中汽车主任务样本宽度坍缩到 12-13 个 distinct instruments，
并把坍缩归因到可审计的 row / scope / feature / purge / panel contract 阶段。
```

只有在 `sample_width_root_cause_proven_phase_level = true` 后，Explore10A 才允许进入第二层工作：

```text
1. 审计 Alpha158-like feature bank v1 的缺失、重复和覆盖问题；
2. 在根因支持 feature-bank repair 的前提下构造 feature bank v2；
3. 只用 count-only counterfactual 判断汽车 launch 是否恢复原始 trainability guardrail；
4. 再决定是否具备 Explore10B path-to-primitive rerun 的前置条件。
```

Explore10A 不是：

```text
新的 primitive discovery
Explore11
P1 refine
策略回测
LGBM 模型选择
score bucket 选择
path-to-primitive rerun
手工规则生成
买卖信号生成
```

Explore10A 可以输出：

```text
sample_width_root_cause_proven_fold_level
sample_width_root_cause_proven_task_level
sample_width_root_cause_proven_phase_level
sample_width_root_cause_unresolved
sample_width_bottleneck_explained
feature_bank_v2_not_started_due_to_unproven_sample_width_root_cause
feature_bank_v2_hygiene_pass
feature_bank_v2_hygiene_fail
automotive_launch_trainability_restored_for_explore10b
automotive_launch_still_not_trainable
p0_9b_explore10_panel_mismatch_found
p0_9b_explore10_panel_reconciled_no_bug
continue_explore10a_sample_width_root_cause_audit
continue_explore10a_repair_audit
proceed_to_explore10b_atomic_feature_bank_v2_rerun
stop_automotive_single_industry_path_due_to_sample_width
stop_due_to_unresolved_sample_width_root_cause
recommend_broader_cohort_requirement
```

Explore10A 禁止输出：

```text
atomic_primitive_candidate_for_next_requirement = true
manual_primitive_candidate = true
candidate_for_p1_refine = true
validated_model = true
selected_lgbm_model = true
selected_score_bucket = true
actionable_trade_rule = true
proceed_to_explore11 = true
proceed_to_strategy_backtest = true
freeze_strategy = true
```

---

## 1. 背景与阶段来源

### 1.1 Explore10 的直接结论

Explore10 的正式 recommendation 是：

```text
recommendation = stop_due_to_zero_or_insufficient_atomic_support
```

核心解释不是 Alpha158-like atomic bank 已被收益指标否定，而是：

```text
汽车主任务没有形成可训练 locked LGBM probe，
因此没有资格进入 path extraction、candidate support、null pass 或 next requirement。
```

Explore10 生成了 99 个 primitive candidate，但全部来自电子 placebo / weak-signal scope：

```text
电子 failure_reject: 50 candidates, allowed_for_next_requirement = 0
电子 launch_winner: 49 candidates, allowed_for_next_requirement = 0
汽车 launch_winner: 0 candidates
汽车 failure_reject: 0 candidates
```

因此 Explore10 没有任何可进入下一阶段的 atomic primitive seed。

### 1.2 Explore10 的两个阻塞点

Explore10 暴露两个前置阻塞点。

第一，汽车 scope lock 通过了 row reconciliation，但 trainability 失败：

```text
汽车 launch_winner: source rows = 4863, model_fit_pass folds = 0, path eligible folds = 0
汽车 failure_reject: source rows = 17629, model_fit_pass folds = 0, path eligible folds = 0
```

汽车 launch core folds 中，fold_2021 到 fold_2023 虽然有 validation rows 与 positives，但 distinct instruments 只有 12-13，低于配置门槛 20。

第二，Alpha158-like feature bank v1 preflight 失败：

```text
feature_count_total = 164
missing_row_rate = 35.52%
missing_weight_share = 38.57% > 20% threshold
duplicate_or_high_corr_cluster_count = 64 > 50 threshold
feature_bank_preflight_pass = false
```

这说明即使汽车 trainability 不失败，v1 feature bank 也不应直接进入稳定 primitive discovery。

### 1.3 电子 placebo 的警告

Explore10 只在电子 placebo / weak-signal scope 中观察到 path 与 primitive candidate。电子 placebo scope 甚至产生了 stable-looking candidates：

```text
电子 failure_reject stable_atomic_primitive = 12
电子 launch_winner stable_atomic_primitive = 2
explore10_placebo_stress_audit 中 electronics_failure_stable_candidate_count = 14
```

这说明 path-to-primitive translation 在大 feature bank 下存在叙事过拟合风险。Explore10A 必须继续保留 negative-control / placebo stress，不得用电子候选反推正向机制。

### 1.4 P0.9B 与 Explore10 的张力

P0.9B 中汽车 launch 是最强 diagnostic signal，但 Explore10 的汽车主任务却没有任何 path eligible fold。Explore10A 必须解释：

```text
为什么 P0.9B 中汽车 launch 可诊断，
但 Explore10 中汽车 launch 在 atomic bank / path probe 下变成 0 eligible folds？
```

这一步优先于任何新 primitive、新模型、新回测。

---

## 2. 阶段定位

Explore10A 是 `repair audit phase`。

Explore10A 的目标是回答：

```text
1. 汽车样本宽度为什么收缩到 12-13 个 distinct instruments？
2. 这种收缩是数据构造 / scope lock / feature missing / label purge / asof rule 的问题，还是汽车单行业天然样本宽度不足？
3. 只有在样本宽度坍缩根因已被证明后，Alpha158-like feature bank v1 的 missing / duplicate 问题是否需要修复为 v2？
4. 只有在 v2 被允许构造后，汽车 launch 是否至少有足够 core folds 恢复原始 trainability guardrail？
5. 如果样本宽度根因证明汽车单行业天然过窄，是否应停止汽车单行业 path-to-primitive 路线，改成更宽 cohort 或 event-regime cohort？
```

### 2.1 Hard Phase-0 Gate

Explore10A 的第一验收口径只有一个：

```text
sample_width_root_cause_proven_phase_level
```

在该 gate 通过之前，以下动作一律不得作为已完成结论：

```text
feature_bank_v2_hygiene_pass
automotive_launch_trainability_restored_for_explore10b
proceed_to_explore10b_atomic_feature_bank_v2_rerun
stop_due_to_feature_bank_hygiene_failure
stop_due_to_placebo_dominates_primary_risk
```

如果 root cause 不能被证明，Explore10A 的最强 recommendation 只能是：

```text
continue_explore10a_sample_width_root_cause_audit
```

或者在数据证据明确不可修复时输出：

```text
stop_due_to_unresolved_sample_width_root_cause
```

Explore10A 不回答：

```text
哪个 primitive 有效？
哪个 LGBM path 有 alpha？
哪个 feature 重要？
哪个 score bucket 可交易？
是否进入 P1？
是否进入回测？
```

---

## 3. Scope Lock

### 3.1 Primary audit scope

```text
target_industry = 汽车
primary_task = launch_winner
secondary_task = failure_reject
```

Primary audit 重点是汽车 launch，因为 Explore10 的 proceed condition 只允许汽车 launch primitive 成为下一阶段主候选。

汽车 failure 只能作为 secondary diagnostic，用于确认汽车样本宽度问题是否也发生在 failure task。

### 3.2 Placebo / negative-control scope

```text
placebo_industry = 电子
placebo_tasks = launch_winner, failure_reject
```

电子只用于：

```text
feature bank hygiene 对照
placebo candidate risk 对照
negative-control search-bias 压力测试
```

电子不得产生任何 candidate_for_next_requirement。

### 3.3 Explicitly excluded scope

Explore10A 不覆盖：

```text
电力设备主任务
固定 9 行业重跑
跨行业 general model
Explore10B path-to-primitive rerun
manual primitive discovery
strategy backtest
```

---

## 4. 数据纪律

### 4.1 Time and PIT discipline

Explore10A 沿用 Explore10 的数据纪律：

```text
research_start = 2017-01-01
research_end = 2024-12-31
observed_reference_start = 2025-01-01
observed_reference_end = 2026-04-30
fold_2020 至 fold_2023 = core audit folds
fold_2024 = robustness audit only
```

PIT discipline：

```text
PIT universe required
PIT industry membership required
PIT provider required
fallback provider may be used for schema diagnostics only
```

### 4.2 Feature-asof discipline

For all close-derived launch / failure signals:

```text
signal_date = close-derived signal day
event_effective_date = next_trading_day(signal_date)
feature_asof_date = signal_date
```

Forbidden predictive features:

```text
event_effective_date high
event_effective_date low
event_effective_date close
event_effective_date volume
event_effective_date money
```

`event_effective_date open` may be used only as execution / label reference, not as predictive feature.

### 4.3 Purged walk-forward discipline

Train eligibility must satisfy:

```text
train_label_window_end_date < validation_start_date
```

No train row may have 50h120 / 100h240 / failure label window spilling into the validation year.

Explore10A may audit counterfactual row counts with relaxed purge only as diagnostic, but such rows cannot support Explore10B recommendation.

### 4.4 Observed-reference discipline

Explore10A must split observed-reference overlap into:

```text
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
```

Rules:

```text
decision overlap -> ineligible
feature overlap -> ineligible
label measurement overlap -> robustness / audit only; not eligible for core support
```

---

## 5. Allowed Input Artifacts

Explore10A may read these artifacts as schema / audit / reconciliation reference:

```text
Explore10/outputs/explore10/reports/explore10_report.md
Explore10/outputs/explore10/reports/explore10_run_manifest.json
Explore10/outputs/explore10/reports/explore10_feature_bank_preflight_audit.csv
Explore10/outputs/explore10/reports/explore10_scope_lock_audit.csv
Explore10/outputs/explore10/reports/explore10_fold_trainability_audit.csv
Explore10/outputs/explore10/reports/explore10_feature_asof_leakage_audit.csv
Explore10/outputs/explore10/reports/explore10_observed_reference_overlap_audit.csv
Explore10/outputs/explore10/reports/explore10_required_artifact_authority_audit.csv
Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet
Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet

Explore9/outputs/p0_9b/reports/p0_9b_report.md
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_prediction_panel.parquet

Explore9/outputs/p0_9a/reports/p0_9a_recommendation_summary.csv
Explore9/outputs/p0_9a/reports/p0_9a_trainability_contract_matrix.csv
Explore9/outputs/p0_9a/reports/p0_9a_sample_weight_group_cap_audit.csv

Explore7/data/universe/pit_mcap500_mainboard_daily.csv
Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
Explore7/data/targets/pit_industry_membership.csv
Explore7/data/targets/market_targets.csv
Explore7/data/targets/industry_targets.csv
Explore7/data/targets/target_history.csv
Explore7/data/qlib/cn_data_pit
```

Allowed uses:

```text
schema reference
row attrition audit
panel reconciliation
feature availability audit
feature bank v2 hygiene construction only after sample_width_root_cause_proven_phase_level = true
trainability counterfactual counts
negative-control design
```

Forbidden uses:

```text
select primitive winner
select LGBM hyperparameters
select score bucket
select validation threshold
generate trading signals
change labels based on results
use 2025-2026 for selection
use historical trading results
```

---

## 6. Core Research Questions

Explore10A must answer these questions.

### 6.0 Question ordering

Research questions are ordered gates, not a parallel checklist.

```text
Gate 0: Prove why automotive sample width collapsed.
Gate 1: Attribute the collapse to one primary bottleneck enum.
Gate 2: Only if Gate 0/1 justify feature repair, run feature bank v2 hygiene.
Gate 3: Only if v2 is allowed and passes, run trainability counterfactual.
Gate 4: Only if all prior gates pass, evaluate Explore10B readiness.
```

Any artifact for a later gate may be emitted as a status-only artifact with:

```text
execution_status = not_started_due_to_unproven_sample_width_root_cause
```

Such status-only artifacts satisfy artifact authority but cannot support Explore10B.

### 6.1 Automotive sample-width question

```text
Why did automotive launch/failure collapse to 12-13 distinct instruments in Explore10?
```

Required sub-questions:

```text
1. How many PIT automotive instruments exist per fold?
2. How many have raw launch/failure source rows?
3. How many survive label horizon, purge, feature-asof, observed-reference, scope lock, feature availability, and trainability denominator?
4. Which step removes each missing instrument?
5. Is the loss due to legitimate PIT/event eligibility or implementation / scope mismatch?
```

`sample_width_root_cause_proven_fold_level = true` requires all of the following for one task/fold:

```text
1. every PIT automotive instrument/fold/task has a first_failure_stage or reaches trainability denominator;
2. row_count, weighted_row_count, positive_count, and distinct_instruments reconcile across all stages;
3. p0_9b vs Explore10 row identity/schema differences are either matched or classified;
4. unknown_or_unclassified_loss_weight_share <= thresholds.max_unknown_loss_weight_share;
5. primary_bottleneck is exactly one of the allowed enums in Section 10;
6. the report gives instrument/fold evidence for the chosen bottleneck.
```

`sample_width_root_cause_proven_task_level = true` if and only if:

```text
1. all core folds for that task have sample_width_root_cause_proven_fold_level = true;
2. all core folds have unknown_or_unclassified_loss_weight_share <= thresholds.max_unknown_loss_weight_share;
3. all core folds have a non-unresolved primary_bottleneck;
4. no core fold has feature-asof, purge, observed-reference decision/feature overlap, or panel reconciliation discipline violation.
```

`sample_width_root_cause_proven_phase_level = true` if and only if:

```text
1. automotive launch_winner primary task has sample_width_root_cause_proven_task_level = true across all core folds;
2. automotive failure_reject secondary task has secondary_failure_discipline_violation_count = 0;
3. phase-level primary_bottleneck is assigned from the automotive launch_winner task, not from a single fold;
4. no unresolved loss remains above threshold in any primary launch core fold.
```

Fold-level proof cannot be promoted to task-level or phase-level proof without these aggregations.

Required gate artifact:

```text
explore10a_sample_width_root_cause_gate.csv
```

Minimum fields:

```text
target_industry
task
fold_id
sample_width_root_cause_proven_fold_level
sample_width_root_cause_proven_task_level
sample_width_root_cause_proven_phase_level
primary_bottleneck
phase_level_primary_bottleneck
root_cause_evidence_level
unknown_or_unclassified_loss_weight_share
secondary_failure_discipline_violation_count
p0_9b_explore10_reconciliation_status
phase0_pass
allowed_next_gate
blocked_next_gate_reason
```

### 6.2 P0.9B vs Explore10 reconciliation question

```text
Why did P0.9B automotive launch show diagnostic trainability, while Explore10 automotive launch had zero path-eligible folds?
```

Required comparison:

```text
p0_9b_locked_t1_train_eval_panel
vs
explore10_lgbm_train_eval_panel
```

The comparison must be row-level where keys are available, otherwise instrument/date/fold aggregate fallback must be used.

### 6.3 Feature bank v1 hygiene question

```text
Can Alpha158-like feature bank v1 be reduced to a v2 that passes missingness and duplicate gates without collapsing feature-family coverage?
```

This question is conditional. It may only be answered as `feature_bank_v2_hygiene_pass/fail` after:

```text
sample_width_root_cause_proven_phase_level = true
```

Before that, Explore10A may report v1 missingness diagnostics, but must not claim v2 readiness.

Required checks:

```text
missing_weight_share
duplicate_or_high_corr_cluster_count
constant_or_near_constant_rate
max_feature_family_share
feature_family_missing_weight_share
feature_family_coverage_after_hygiene
per-fold feature availability
per-instrument feature availability
```

### 6.4 Trainability counterfactual question

```text
If feature bank v2 is used, does automotive launch regain enough trainable core folds under the existing trainability guardrail?
```

Counterfactual variants may be computed only after sample-width root cause is proven and v2 construction is allowed. They are diagnostics only and cannot produce primitive candidates.

### 6.5 Placebo risk question

```text
Does electronics placebo still generate stable-looking candidates under v2-like feature hygiene?
```

Explore10A does not run full path-to-primitive. It only checks whether the data / feature bank setup would continue to make electronics unusually easy to generate narratives.

If v2 is not started because sample-width root cause remains unproven, placebo output must be limited to Explore10 reference evidence and v1/v2-not-started status.

---

## 7. Automotive Row Attrition Waterfall

### 7.1 Unit of analysis

The waterfall must be produced at three granularities:

```text
instrument-level
instrument + fold-level
instrument + fold + task-level
```

Tasks:

```text
launch_winner
failure_reject
```

### 7.2 Required attrition stages

For each instrument / fold / task, Phase-0 root-cause proof must cover:

```text
pit_automotive_member
has_qlib_pit_calendar
has_required_ohlcv
has_raw_source_event
has_launch_or_failure_scope_row
label_window_available
passes_label_truncation
passes_label_window_purge
passes_observed_reference_decision_feature
passes_feature_asof
passes_scope_lock
passes_feature_bank_v1_required_availability
eligible_for_trainability_denominator
eligible_for_model_fit
eligible_for_path_extraction
```

Conditional stages after `sample_width_root_cause_proven_phase_level = true`:

```text
passes_feature_bank_v2_required_availability
```

`passes_sample_weight_group_cap` is not a Phase-0 row-removal stage unless the implementation actually removes rows. If it only changes weights, it must be reported in Section 13, not used as the first failure reason for sample-width collapse.

### 7.3 Required loss reason

If an instrument disappears at any stage, record:

```text
first_failure_stage
first_failure_reason
last_stage_passed
raw_row_count_before_failure
weighted_row_count_before_failure
positive_count_before_failure
unknown_or_unclassified_loss_weight_share
```

### 7.4 Required artifact

```text
explore10a_automotive_row_attrition_waterfall.csv
```

Minimum fields:

```text
target_industry
instrument
fold_id
task
stage_name
stage_order
row_count
weighted_row_count
positive_count
distinct_signal_dates
distinct_event_effective_dates
pass
first_failure_stage
first_failure_reason
unknown_or_unclassified_loss_weight_share
```

---

## 8. P0.9B vs Explore10 Panel Reconciliation

### 8.1 Join keys

Preferred join key must be schema-aware. Required fields are:

```text
instrument
fold_id
signal_date
event_effective_date
launch_stratum_event_id
```

Task fields must be canonicalized before comparison:

```text
p0_9b model_task = industry_launch_winner_score_lgbm -> launch_winner
p0_9b model_task = industry_failure_reject_score_lgbm -> failure_reject
Explore10 model_task = launch_winner / failure_reject
```

Optional join keys may be used only if they exist in both panels:

```text
source_event_id
label_version
model_task_canonical
target_industry
```

Fallback join key if event IDs are absent or differ:

```text
instrument
model_task_canonical
fold_id
signal_date
event_effective_date
```

Fallback join must be audited and cannot silently collapse duplicate rows. Missing schema fields must be recorded as `schema_key_missing`, not treated as row mismatches.

### 8.2 Row classifications

Every candidate row must be classified as:

```text
present_in_both
present_in_both_but_task_alias_changed
present_in_both_but_feature_ineligible
present_in_both_but_probe_contract_ineligible
p0_9b_only
explore10_only
matched_by_fallback_key
schema_key_missing
unmatched_due_to_event_id_change
unmatched_due_to_signal_date_shift
unmatched_due_to_feature_asof_rule
unmatched_due_to_label_version
unmatched_due_to_feature_bank_missing
unmatched_due_to_scope_lock_change
unmatched_due_to_purge_or_label_horizon
```

### 8.3 Required reconciliation metrics

```text
matched_row_count
p0_9b_only_row_count
explore10_only_row_count
matched_weight_share
p0_9b_only_weight_share
explore10_only_weight_share
instrument_count_p0_9b
instrument_count_explore10
instrument_count_common
instrument_count_p0_9b_only
instrument_count_explore10_only
positive_count_delta
weight_sum_delta
schema_key_missing_count
task_alias_changed_row_count
present_in_both_but_ineligible_row_count
```

### 8.4 Required artifact

```text
explore10a_p0_9b_explore10_panel_reconciliation.csv
```

---

## 9. Feature Bank v2 Hygiene Contract

Feature bank v2 is a conditional module. It must not be constructed until:

```text
sample_width_root_cause_proven_phase_level = true
```

If root cause is unresolved, all v2 artifacts must be status-only with:

```text
execution_status = not_started_due_to_unproven_sample_width_root_cause
```

If the proven root cause is `automotive_scope_width`, v2 construction is optional only for future hygiene documentation and cannot support Explore10B readiness in this requirement.

### 9.1 Goal

Feature bank v2 is not a new alpha search. It is a hygiene version of Alpha158-like v1.

Its goal is:

```text
reduce missingness
reduce duplicate / high-correlation clusters
retain feature-family coverage
preserve feature-asof discipline
restore automotive sample width if missingness was the cause
```

### 9.2 Feature selection source

Feature bank v2 may be derived only from:

```text
predeclared feature formulas
train-scope unsupervised missingness
train-scope unsupervised correlation / duplicate clustering
feature formula complexity
feature-family coverage constraints
sample-width root-cause attribution that explicitly justifies feature repair
```

Feature bank v2 may not use:

```text
labels
validation lift
validation AUC
validation primitive support
path support
null outcome
P0.9B high-score coverage
fold_2024 performance
sample-width unknown-loss rows
```

### 9.3 Candidate removal reasons

Each dropped feature must have exactly one primary drop reason:

```text
missing_weight_share_too_high
missing_row_rate_too_high
feature_family_missing_weight_share_too_high
constant_or_near_constant
high_corr_duplicate_cluster_representative_not_selected
asof_rule_violation
raw_unscaled_ohlcv_not_allowed
formula_unmapped
insufficient_fold_availability
complexity_exceeds_limit
context_slice_only_not_atomic_feature
```

### 9.4 Duplicate cluster representative rule

For high-correlation or duplicate clusters, representative selection must be deterministic:

Priority order:

```text
1. lower train-scope missing_weight_share
2. higher fold availability count
3. lower formula complexity
4. lower feature family overrepresentation penalty
5. simpler asof rule
6. lexicographic feature_name tie-breaker
```

No validation label or validation metric may be used.

### 9.5 Required v2 gates

Feature bank v2 passes only if:

```text
missing_weight_share <= thresholds.max_feature_missing_weight_share
missing_row_rate <= thresholds.max_feature_missing_row_rate
duplicate_or_high_corr_cluster_count <= thresholds.max_duplicate_feature_cluster_count
constant_or_near_constant_rate <= thresholds.max_constant_feature_rate
max_feature_family_share <= thresholds.max_feature_family_share
feature_family_coverage_after_hygiene >= thresholds.min_feature_family_coverage_after_hygiene
feature_asof_leakage_violation_count = 0
unmapped_formula_token_count = 0
```

### 9.6 Required artifacts

```text
explore10a_feature_bank_v1_to_v2_hygiene_audit.csv
explore10a_feature_bank_v2_dictionary.csv
explore10a_feature_bank_v2_feature_drop_log.csv
explore10a_feature_bank_v2_duplicate_cluster_audit.csv
explore10a_feature_bank_v2_missingness_by_fold.csv
explore10a_feature_bank_v2_missingness_by_instrument.csv
explore10a_feature_bank_v2_family_coverage_audit.csv
```

---

## 10. Feature Availability vs Sample Width Attribution

Explore10A must explicitly separate sample-width causes before any v2 repair conclusion:

```text
A. automotive event scope is inherently too narrow;
B. feature bank missingness makes otherwise valid automotive rows ineligible.
C. P0.9B and Explore10 have equivalent row identity but different task alias / probe eligibility contract.
D. P0.9B and Explore10 have a real panel construction or scope mismatch.
E. root cause remains unresolved.
```

### 10.1 Required metrics

For each automotive task and fold:

```text
raw_distinct_instruments
scope_locked_distinct_instruments
feature_bank_v1_available_distinct_instruments
feature_bank_v2_available_distinct_instruments
trainability_denominator_distinct_instruments
path_eligible_distinct_instruments
p0_9b_distinct_instruments
explore10_distinct_instruments
present_in_both_distinct_instruments
unknown_or_unclassified_loss_weight_share
```

### 10.2 Interpretation rule

Primary bottleneck must be assigned before v2 repair is used as evidence.

If `scope_locked_distinct_instruments` is already 12-13 before feature filtering:

```text
primary_bottleneck = automotive_scope_width
```

If `scope_locked_distinct_instruments >= 20` but `feature_bank_v1_available_distinct_instruments` collapses to 12-13:

```text
primary_bottleneck = feature_bank_v1_missingness
```

If P0.9B has much larger instrument width than Explore10 before feature filtering:

```text
primary_bottleneck = panel_construction_or_scope_mismatch
```

If P0.9B and Explore10 rows match but Explore10 fails only after task alias / feature eligibility / model probe guardrails:

```text
primary_bottleneck = probe_contract_or_feature_eligibility
```

If unknown/unclassified loss exceeds threshold:

```text
primary_bottleneck = unresolved
sample_width_root_cause_proven_fold_level = false
sample_width_root_cause_proven_task_level = false
sample_width_root_cause_proven_phase_level = false
```

Only after a non-`unresolved` primary bottleneck is proven may v2 restoration be used as second-order evidence:

```text
v2_restores_distinct_instruments = true/false
```

### 10.3 Required artifact

```text
explore10a_sample_width_attribution.csv
```

---

## 11. Trainability Counterfactual Audit

### 11.1 Purpose

Trainability counterfactual is diagnostic only. It cannot produce primitive candidates or model candidates.

It is also conditional. It must not run beyond v1/count-only reference diagnostics until:

```text
sample_width_root_cause_proven_phase_level = true
```

If root cause is unresolved, `explore10a_trainability_counterfactual_audit.csv` must exist but contain only the not-started status and the Phase-0 row/count evidence.

### 11.2 Counterfactual grid

Explore10A may evaluate the following count-only grid:

```text
feature_bank_version:
  v1_original
  v2_hygiene

feature_missing_policy:
  strict_original
  v2_drop_high_missing_features
  lgbm_native_missing_diagnostic_only

min_distinct_instruments:
  20_original
  15_diagnostic
  12_diagnostic
```

`v2_hygiene` is materialized only after `sample_width_root_cause_proven_phase_level = true`; otherwise v2 rows are status-only.

Only `feature_bank_version = v2_hygiene` and `min_distinct_instruments = 20_original` can support Explore10B recommendation.

`15_diagnostic` and `12_diagnostic` can only support:

```text
recommend_broader_cohort_requirement
or
continue_explore10a_repair_audit
```

They cannot support Explore10B path-to-primitive rerun.

### 11.3 No model performance selection

Trainability counterfactual may report:

```text
train rows
train positives
validation rows
validation positives
distinct instruments
distinct instrument-years
feature availability
model_fit_sanity_pass
prediction_std_sanity
```

But it may not use or report as selection criteria:

```text
AUC
logloss
Brier
lift
path count
primitive count
score bucket
feature importance
```

If model_fit_sanity is run, it is only to confirm implementation viability; no tree path may be extracted and no score bucket may be formed.

### 11.4 Required artifact

```text
explore10a_trainability_counterfactual_audit.csv
```

---

## 12. Electronics Placebo Guardrail

### 12.1 Purpose

Electronics remains a negative-control / weak-signal scope because Explore10 generated stable-looking candidates in electronics placebo. Explore10A must not remove this guardrail.

### 12.2 Required checks

Explore10A must report:

```text
electronics_v1_path_candidate_count_reference
electronics_v2_feature_bank_available_rows_or_not_started_status
electronics_v2_missing_weight_share_or_not_started_status
electronics_v2_duplicate_cluster_count_or_not_started_status
electronics_placebo_risk_flag
```

Explore10A does not run full path-to-primitive on electronics by default. If a lightweight placebo path sanity run is enabled, it must be report-only and cannot create candidate maps.

### 12.3 Stop condition

If electronics placebo becomes easier to satisfy than automotive primary under v2, record:

```text
placebo_dominates_primary_risk = true
```

This does not automatically block feature bank v2, but it blocks any recommendation stronger than:

```text
continue_explore10a_repair_audit
```

### 12.4 Required artifact

```text
explore10a_electronics_placebo_guardrail_audit.csv
```

---

## 13. Sample Weight and Concentration Audit

Explore10A must inherit P0.9A / P0.9B sample-weight concentration concerns.

### 13.1 Required metrics

For each target industry / task / fold / feature_bank_version:

```text
top_instrument_year_weight_share
instrument_year_weight_hhi
top1_instrument_contribution
top5_instrument_contribution
weight_cap_violation_count
weight_cap_violation_weight_share
```

### 13.2 Required gates for Explore10B eligibility

```text
top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
weight_cap_violation_count = 0
```

If gate fails, Explore10A may still recommend more repair, but not Explore10B.

### 13.3 Required artifact

```text
explore10a_sample_weight_and_concentration_audit.csv
```

---

## 14. Explore10B Readiness Gate

Explore10A may recommend `proceed_to_explore10b_atomic_feature_bank_v2_rerun` only if all conditions hold:

```text
1. sample_width_root_cause_proven_phase_level = true
2. phase_level_primary_bottleneck is one of:
   - feature_bank_v1_missingness
   - panel_construction_or_scope_mismatch
   - probe_contract_or_feature_eligibility
3. unknown_or_unclassified_loss_weight_share <= thresholds.max_unknown_loss_weight_share
4. feature_bank_v2_hygiene_pass = true
5. feature_asof_leakage_violation_count = 0
6. observed_reference_decision_feature_overlap_eligible_rows = 0
7. automotive_panel_reconciliation_status is one of:
   - reconciled_no_bug
   - mismatch_explained_and_fixed_by_v2
   - present_in_both_but_probe_contract_explained
8. automotive launch has at least thresholds.min_trainable_core_folds_for_explore10b core folds trainable under:
   - feature_bank_version = v2_hygiene
   - min_distinct_instruments = thresholds.min_distinct_instruments_original
   - original purge and observed-reference rules
9. each Explore10B-eligible core fold has path_eligible_distinct_instruments >= thresholds.min_distinct_instruments_original
10. sample_weight_and_concentration_pass = true
11. electronics placebo guardrail does not dominate primary
12. no metric-selection or threshold-selection violation
13. required artifact authority pass = true
```

If `phase_level_primary_bottleneck = automotive_scope_width`, Explore10A must not recommend:

```text
proceed_to_explore10b_atomic_feature_bank_v2_rerun
```

Allowed recommendations in that case are limited to:

```text
stop_automotive_single_industry_path_due_to_sample_width
recommend_broader_cohort_requirement
```

Default:

```text
thresholds.min_trainable_core_folds_for_explore10b = 2
thresholds.min_distinct_instruments_original = 20
thresholds.max_unknown_loss_weight_share = 0.01
```

If only diagnostic thresholds 15 or 12 pass, Explore10A must not recommend Explore10B. It may recommend:

```text
recommend_broader_cohort_requirement
```

or:

```text
continue_explore10a_repair_audit
```

---

## 15. Recommendation Enum

Explore10A recommendation must be one of:

```text
proceed_to_explore10b_atomic_feature_bank_v2_rerun
continue_explore10a_sample_width_root_cause_audit
continue_explore10a_repair_audit
stop_automotive_single_industry_path_due_to_sample_width
recommend_broader_cohort_requirement
stop_due_to_feature_bank_hygiene_failure
stop_due_to_feature_asof_or_data_discipline_violation
stop_due_to_placebo_dominates_primary_risk
stop_due_to_unresolved_sample_width_root_cause
```

Forbidden recommendations:

```text
proceed_to_explore11_manual_atomic_primitive_formula_discovery
proceed_to_strategy_backtest
candidate_for_p1_strategy
validated_model
selected_lgbm_model
selected_score_bucket
atomic_primitive_candidate_for_next_requirement
freeze_strategy
```

---

## 16. Required Report Artifacts

Section 16 is the single required report artifact authority.

```text
explore10a_run_manifest.json
explore10a_preflight_reference_artifact_audit.csv
explore10a_feature_asof_leakage_audit.csv
explore10a_observed_reference_overlap_audit.csv
explore10a_purge_audit.csv
explore10a_sample_width_root_cause_gate.csv
explore10a_automotive_row_attrition_waterfall.csv
explore10a_p0_9b_explore10_panel_reconciliation.csv
explore10a_feature_bank_v1_to_v2_hygiene_audit.csv
explore10a_feature_bank_v2_dictionary.csv
explore10a_feature_bank_v2_feature_drop_log.csv
explore10a_feature_bank_v2_duplicate_cluster_audit.csv
explore10a_feature_bank_v2_missingness_by_fold.csv
explore10a_feature_bank_v2_missingness_by_instrument.csv
explore10a_feature_bank_v2_family_coverage_audit.csv
explore10a_sample_width_attribution.csv
explore10a_trainability_counterfactual_audit.csv
explore10a_electronics_placebo_guardrail_audit.csv
explore10a_sample_weight_and_concentration_audit.csv
explore10a_explore10b_readiness_gate.csv
explore10a_metric_nonselection_audit.csv
explore10a_threshold_nonselection_audit.csv
explore10a_forbidden_recommendation_self_check.csv
explore10a_required_artifact_authority_audit.csv
explore10a_threshold_config_consistency_audit.csv
explore10a_report.md
```

Conditional artifacts are still required for authority, but when their gate has not started they must be status-only artifacts with:

```text
execution_status
not_started_reason
upstream_gate
upstream_gate_pass
```

Allowed `not_started_reason` values:

```text
unproven_sample_width_root_cause
root_cause_is_automotive_scope_width
feature_bank_v2_not_allowed
explore10b_readiness_not_allowed
```

---

## 17. Required Cache Artifacts

Full row-level outputs must be parquet cache only.

```text
Explore10/outputs/explore10a/cache/explore10a_automotive_launch_attrition_panel.parquet
Explore10/outputs/explore10a/cache/explore10a_automotive_failure_attrition_panel.parquet
Explore10/outputs/explore10a/cache/explore10a_p0_9b_explore10_row_reconciliation_panel.parquet
Explore10/outputs/explore10a/cache/explore10a_feature_availability_panel.parquet
Explore10/outputs/explore10a/cache/explore10a_trainability_counterfactual_panel.parquet
```

Cache tracking rule:

```text
git check-ignore Explore10/outputs/explore10a/cache/*.parquet must pass
full row-level panels cannot be tracked CSV
report CSV/JSON/markdown artifacts live under Explore10/outputs/explore10a/reports/
```

---

## 18. Report Structure

`explore10a_report.md` must contain:

```text
1. Executive conclusion
2. Explore10A scope and forbidden conclusions
3. Phase-0 sample-width root-cause gate
4. Why Explore10 stopped and what Explore10A tests
5. Automotive sample-width attrition waterfall
6. P0.9B vs Explore10 panel reconciliation
7. Feature availability vs sample width attribution
8. Feature bank v1 failure explanation
9. Conditional feature bank v2 hygiene result or not-started status
10. Conditional trainability counterfactual audit or not-started status
11. Electronics placebo guardrail
12. Sample weight and concentration audit
13. Explore10B readiness gate or not-allowed status
14. Recommendation
15. Required artifact self-check
16. Threshold / metric nonselection self-check
17. Final boundary statement
```

---

## 19. Config Sketch

```yaml
phase: explore10a
title: automotive_sample_width_and_feature_bank_hygiene_audit
output_root: Explore10/outputs/explore10a

scope:
  primary:
    industry: 汽车
    task: launch_winner
    role: primary_trainability_repair_audit
  secondary:
    industry: 汽车
    task: failure_reject
    role: secondary_sample_width_audit
  placebo:
    industry: 电子
    tasks: [launch_winner, failure_reject]
    role: negative_control_guardrail

folds:
  core: [2020, 2021, 2022, 2023]
  robustness_only: [2024]
  fold_2024_used_for_readiness: false

data_discipline:
  feature_asof_date_rule: signal_date
  event_effective_date_rule: next_trading_day_after_signal_date
  event_effective_ohlcvm_as_feature_allowed: false
  train_label_window_end_before_validation_start: true
  observed_reference_decision_feature_overlap_allowed: false
  observed_reference_label_measurement_core_support_allowed: false

phase_gates:
  sample_width_root_cause_first: true
  feature_bank_v2_allowed_before_sample_width_root_cause_proven_phase_level: false
  trainability_counterfactual_allowed_before_sample_width_root_cause_proven_phase_level: false
  explore10b_readiness_allowed_before_sample_width_root_cause_proven_phase_level: false
  sample_width_root_cause_levels:
    - fold_level
    - task_level
    - phase_level
  explore10b_allowed_primary_bottleneck:
    - feature_bank_v1_missingness
    - panel_construction_or_scope_mismatch
    - probe_contract_or_feature_eligibility
  explore10b_forbidden_primary_bottleneck:
    - automotive_scope_width
    - unresolved
  primary_bottleneck_allowed:
    - automotive_scope_width
    - feature_bank_v1_missingness
    - panel_construction_or_scope_mismatch
    - probe_contract_or_feature_eligibility
    - unresolved

feature_bank_hygiene:
  source_version: alpha158_like_v1_from_explore10
  target_version: alpha158_like_v2_hygiene
  enabled_after_sample_width_root_cause_proven_phase_level: true
  status_only_when_root_cause_unproven: true
  selection_uses_labels: false
  selection_uses_validation_metrics: false
  duplicate_cluster_method: train_scope_correlation_and_formula_identity
  duplicate_cluster_threshold_abs_corr: 0.98
  representative_policy:
    - lower_missing_weight_share
    - higher_fold_availability_count
    - lower_formula_complexity
    - lower_family_overrepresentation_penalty
    - simpler_asof_rule
    - lexicographic_feature_name

trainability_counterfactual:
  enabled: true
  enabled_after_sample_width_root_cause_proven_phase_level: true
  model_fit_sanity_allowed: true
  path_extraction_allowed: false
  primitive_candidate_generation_allowed: false
  feature_bank_versions: [v1_original, v2_hygiene]
  min_distinct_instruments_grid: [20, 15, 12]
  explore10b_eligible_min_distinct_instruments: 20

thresholds:
  max_feature_missing_weight_share: 0.20
  max_feature_missing_row_rate: 0.30
  max_duplicate_feature_cluster_count: 50
  max_constant_feature_rate: 0.05
  max_feature_family_share: 0.35
  min_feature_family_coverage_after_hygiene: 0.80
  min_trainable_core_folds_for_explore10b: 2
  min_distinct_instruments_original: 20
  max_unknown_loss_weight_share: 0.01
  max_top_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.08

recommendation_allowed:
  - proceed_to_explore10b_atomic_feature_bank_v2_rerun
  - continue_explore10a_sample_width_root_cause_audit
  - continue_explore10a_repair_audit
  - stop_automotive_single_industry_path_due_to_sample_width
  - recommend_broader_cohort_requirement
  - stop_due_to_feature_bank_hygiene_failure
  - stop_due_to_feature_asof_or_data_discipline_violation
  - stop_due_to_placebo_dominates_primary_risk
  - stop_due_to_unresolved_sample_width_root_cause
```

---

## 20. Implementation Commands

Required commands:

```bash
uv run python Explore10/scripts/run_explore10.py profile-explore10a \
  --config Explore10/configs/automotive_sample_width_feature_bank_hygiene_explore10a.yaml

uv run python Explore10/scripts/run_explore10.py report-explore10a \
  --config Explore10/configs/automotive_sample_width_feature_bank_hygiene_explore10a.yaml
```

No temporary `Explore9/outputs/explore10a/` output path is allowed for accepted implementation.

---

## 21. Preflight Checklist

Before running Explore10A, implementation must verify:

```text
[ ] Explore10 report artifacts exist
[ ] Explore10 cache panels exist
[ ] P0.9B locked T1 train/eval and prediction panels exist
[ ] P0.9A recommendation and sample-weight audits exist
[ ] 汽车 PIT industry exact mapping exists
[ ] 电子 PIT industry exact mapping exists
[ ] sample-width root-cause gate runs before feature bank v2 construction
[ ] sample-width root-cause gate separates fold-level, task-level, and phase-level proof
[ ] Explore10B readiness excludes phase_level_primary_bottleneck = automotive_scope_width
[ ] v2 / counterfactual / Explore10B readiness artifacts can be status-only if Phase-0 fails
[ ] fallback provider contributes zero eligible rows
[ ] feature_asof_date = signal_date
[ ] event_effective_date high/low/close/volume/money not used as feature
[ ] train_label_window_end_date < validation_start_date for core train rows
[ ] observed-reference decision / feature overlap excluded
[ ] fold_2024 robustness-only
[ ] feature bank v2 selection does not use labels or validation metrics
[ ] trainability counterfactual does not extract paths or primitive candidates
[ ] electronics placebo remains negative-control only
[ ] no score bucket, model selection, backtest, or P1 recommendation possible
```

---

## 22. Final Boundary Statement

Explore10A report must repeat:

```text
Explore10A is a repair audit phase.
Its first and binding task is to prove why automotive sample width collapsed.
Only after sample_width_root_cause_proven_phase_level = true may it diagnose feature-bank v2 repair, trainability counterfactuals, or Explore10B readiness.
If phase_level_primary_bottleneck = automotive_scope_width, Explore10A cannot proceed to Explore10B and must stop the automotive single-industry path or recommend a broader cohort.
It does not create primitive candidates, does not validate a model, and does not run backtests.
Only if automotive launch regains enough trainable core folds under a clean feature bank v2 and original sample-width guardrails may the project proceed to Explore10B.
```
