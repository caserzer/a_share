# Explore10B 需求说明：电子行业样本宽度可行性验证

> 文件名：`requirement_explore10b.md`
> 阶段：`Explore10B` / `P0.10B`
> 标题：Electronics Sample-Width Feasibility Probe
> 状态：implementation-ready requirement
> 生成日期：2026-05-07
> 重要说明：Explore10B 只验证电子行业是否解决 Explore10/10A 暴露的样本宽度问题；不做 primitive discovery、不做策略验证、不输出交易候选。

---

## 0. 一句话结论

Explore10A 已证明汽车单行业 path-to-primitive 的第一瓶颈是：

```text
phase_level_primary_bottleneck = automotive_scope_width
```

Explore10B 只做下一件最小工作：

```text
把 primary scope 从汽车切到电子，
验证电子行业是否在 PIT row identity、feature availability、trainability denominator、
core fold distinct instruments 上解决样本宽度问题。
```

Explore10B 不是电子行业 path-to-primitive rerun，也不是电子 primitive discovery。它只回答：

```text
电子行业是否具备进入下一阶段 path-quality / primitive-quality requirement 的样本宽度前置条件？
```

---

## 1. 背景

### 1.1 Explore10A 的直接结论

Explore10A 的报告结论为：

```text
recommendation = stop_automotive_single_industry_path_due_to_sample_width
sample_width_root_cause_proven_phase_level = true
phase_level_primary_bottleneck = automotive_scope_width
Explore10B readiness = false
```

核心证据：

```text
汽车 launch core folds scope_locked_distinct_instruments = 0 / 15 / 15 / 15
汽车 launch core folds feature_bank_v1_available_distinct_instruments = 0 / 12 / 13 / 13
min_distinct_instruments_original = 20
```

这说明汽车单行业不是因为 P0.9B -> Explore10 行构造错误失败，也不是因为 asof / purge / observed-reference violation 失败，而是 denominator 本身太窄。

### 1.2 为什么选择电子

Explore10 已经观察到电子比汽车有更宽的 denominator：

```text
电子 launch core trainable folds = 3
电子 failure core trainable folds = 4
电子 launch / failure distinct instruments 约 24-25
Explore10 reference 中电子产生 99 个 candidate-like path records
```

这并不证明电子有 alpha，也不证明电子 path 有效。它只说明电子比汽车更适合用于验证：

```text
当样本宽度足够时，Explore10 的 atomic path discovery infrastructure 是否至少具备前置可运行条件？
```

### 1.2.1 Selection Lineage 与后验选择边界

电子不是 Explore10 原始 primary scope。Explore10B 选择电子，是因为 Explore10 / Explore10A 后验观察到：

```text
汽车 primary 因 automotive_scope_width 失败；
电子 reference scope 有足够 distinct instruments；
电子 reference scope 产生了 candidate-like path records。
```

因此 Explore10B 必须把电子选择本身视为实验族的一部分，而不是预注册 primary industry。

必须输出：

```text
explore10b_scope_selection_lineage_audit.csv
```

Minimum fields:

```text
selected_industry
selected_task
selection_source_phase
selection_source_artifact
selection_reason
was_selected_after_observing_trainability
was_selected_after_observing_candidate_count
selection_metric_used
selection_metric_allowed_for_width_probe
post_selection_boundary
allowed_conclusion
forbidden_conclusion
pass
```

Required values:

```text
selected_industry = 电子
selection_source_phase = Explore10 / Explore10A
was_selected_after_observing_trainability = true
was_selected_after_observing_candidate_count = true
selection_metric_allowed_for_width_probe = true
allowed_conclusion = electronics_sample_width_solved_for_next_requirement
forbidden_conclusion = electronics_alpha_or_primitive_validated
```

### 1.3 行业分类边界

Explore10B 允许使用 PIT `电子` 行业 membership，但它的含义必须降级为：

```text
broad denominator handle
```

而不是：

```text
真实上下游产业链定义
真实业务同质 cohort
可解释 supply-chain membership
```

原因是申万行业、东财主题、概念标签都不能可靠表达 A 股公司的真实上下游关系。Explore10B 不解决产业链 membership 问题；它只验证“电子这个宽行业标签是否足以解决数据宽度”。

---

## 2. 阶段定位

Explore10B 是 `sample-width feasibility probe`。

Explore10B 只回答 5 个问题：

```text
1. 电子 launch_winner 是否在 core folds 中有足够 distinct instruments？
2. 电子 failure_reject 是否作为 secondary diagnostic 也有足够 distinct instruments？
3. 电子的宽度优势是否在 feature availability 后仍然存在？
4. 电子的宽度优势是否来自正常 PIT row identity / feature eligibility，而不是数据泄漏或构造错误？
5. 如果电子宽度可行，是否可以进入下一份 path-quality requirement？
```

Explore10B 不回答：

```text
哪个电子 primitive 有效？
哪个电子 LGBM path 有 alpha？
电子是否有可交易 score bucket？
电子是否进入 P1？
电子是否可以回测？
电子是否形成 freeze strategy？
```

---

## 3. Scope

### 3.1 Primary scope

```text
target_industry = 电子
primary_task = launch_winner
scope_role = primary_sample_width_probe
```

### 3.2 Secondary diagnostic scope

```text
target_industry = 电子
secondary_task = failure_reject
scope_role = secondary_width_diagnostic
```

### 3.3 Reference-only scope

```text
reference_industry = 汽车
reference_task = launch_winner / failure_reject
source = Explore10A outputs
role = failed_width_reference_only
```

汽车不得重新进入 primary scope。汽车只用于对比：

```text
为什么电子解决了样本宽度，而汽车没有解决样本宽度？
```

### 3.4 Out-of-scope

Explore10B 不做以下 scope：

```text
broader manufacturing cohort
汽车产业链人工 cohort
东财主题 membership cohort
申万多行业拼接 cohort
event-regime cohort
```

这些可以作为后续 requirement，但不属于 Explore10B。

### 3.5 Explore10 Reference Role Relabel

Explore10 artifacts 中电子的角色不是 Explore10B primary：

```text
Explore10 电子 launch_winner role = weak_signal_sanity_check
Explore10 电子 failure_reject role = negative_control_placebo
Explore10B 电子 launch_winner role = primary_sample_width_probe
Explore10B 电子 failure_reject role = secondary_width_diagnostic
```

实现必须显式记录 role relabel，不得直接继承 Explore10 的 placebo / weak-signal 语义。

Required artifact:

```text
explore10b_scope_role_relabel_audit.csv
```

Minimum fields:

```text
industry
task
fold_id
explore10_reference_role
explore10b_scope_role
role_relabel_reason
role_relabel_allowed
role_relabel_used_for_alpha_claim
pass
```

Required:

```text
role_relabel_used_for_alpha_claim = false
```

---

## 4. Fold Policy

沿用 Explore10 / Explore10A 的 fold 命名：

```text
core folds:
  fold_2020
  fold_2021
  fold_2022
  fold_2023

robustness-only fold:
  fold_2024
```

`fold_2024` 不得用于 readiness support、阈值选择、feature selection、candidate selection。

Explore10 reference 中 `fold_2020` 对 launch 可能为 0 rows。Explore10B 必须单独分类：

```text
fold_2020_zero_launch_row_status
```

允许状态：

```text
expected_event_history_boundary
panel_construction_mismatch
feature_availability_mismatch
unresolved
```

如果 `fold_2020` 是 expected event-history boundary，则电子 launch width pass 不要求 fold_2020 本身有 >=20 instruments，但必须要求：

```text
fold_2021 / fold_2022 / fold_2023 均满足 width guardrail
```

---

## 5. Research Questions

### 5.1 Primary question

```text
Does electronics solve the sample-width problem observed in automotive?
```

机器可判定版本：

```text
electronics_launch_width_solved_excluding_expected_fold_2020_boundary = true
```

当且仅当：

```text
1. fold_2021 / fold_2022 / fold_2023 launch_winner scope_locked_distinct_instruments >= min_distinct_instruments_original;
2. fold_2021 / fold_2022 / fold_2023 launch_winner feature_bank_v1_available_distinct_instruments >= min_distinct_instruments_original;
3. fold_2021 / fold_2022 / fold_2023 launch_winner trainability_denominator_distinct_instruments >= min_distinct_instruments_original;
4. fold_2020 launch_winner zero row status is classified and not unresolved;
5. no feature-asof, observed-reference, purge, or row-reconciliation discipline violation exists in primary launch rows;
6. width pass is not created by relaxing min_distinct_instruments_original.
```

`electronics_launch_width_solved` may exist as a backward-compatible alias, but the authoritative phase-level pass field is:

```text
electronics_launch_width_solved_excluding_expected_fold_2020_boundary
```

Default:

```text
min_distinct_instruments_original = 20
```

### 5.2 Secondary question

```text
Does electronics failure_reject also show enough sample width?
```

机器可判定版本：

```text
electronics_failure_width_diagnostic_pass = true
```

当且仅当：

```text
fold_2020 / fold_2021 / fold_2022 / fold_2023 failure_reject
trainability_denominator_distinct_instruments >= min_distinct_instruments_original
```

Failure task 只能作为 secondary diagnostic，不能替代 launch primary task。

Secondary failure status must be represented separately:

```text
secondary_failure_diagnostic_status in [
  pass,
  secondary_only_width_fail_nonblocking,
  secondary_data_discipline_violation_blocking,
  unresolved_blocking
]
secondary_failure_blocking = true only for data-discipline violation or unresolved status
```

If failure width is weak but launch discipline is clean, Explore10B may still pass with:

```text
electronics_failure_width_diagnostic_pass = false
secondary_failure_diagnostic_status = secondary_only_width_fail_nonblocking
secondary_failure_blocking = false
```

### 5.3 Comparison question

```text
Is the electronics width advantage real relative to automotive?
```

必须输出电子 vs 汽车对比：

```text
scope_locked_distinct_instruments
feature_bank_v1_available_distinct_instruments
trainability_denominator_distinct_instruments
trainable_core_fold_count
failed_predicate
```

### 5.4 Data discipline question

```text
Is electronics width solved without creating new data-discipline risk?
```

必须验证：

```text
feature_asof_leakage_violation_count = 0
observed_reference_decision_feature_overlap_eligible_rows = 0
walk_forward_purge_pass = true
row_identity_missing_from_explore10_count = 0
row_identity_extra_in_explore10_count = 0
fold_2024_used_for_support = false
```

### 5.5 Next-phase question

如果电子样本宽度可行，Explore10B 只能推荐：

```text
proceed_to_explore10c_electronics_path_quality_requirement
```

它不得推荐：

```text
proceed_to_explore11_manual_atomic_primitive_formula_discovery
candidate_for_p1_strategy
proceed_to_strategy_backtest
```

---

## 6. Data Sources

Explore10B 必须优先使用已有 Explore10 / Explore10A artifacts，不得重跑 path-to-primitive。

Required inputs:

```text
Explore10/outputs/explore10/reports/explore10_scope_lock.csv
Explore10/outputs/explore10/reports/explore10_fold_trainability_audit.csv
Explore10/outputs/explore10/reports/explore10_feature_asof_leakage_audit.csv
Explore10/outputs/explore10/reports/explore10_observed_reference_overlap_audit.csv
Explore10/outputs/explore10/reports/explore10_walk_forward_purge_audit.csv
Explore10/outputs/explore10/reports/explore10_feature_bank_preflight_audit.csv
Explore10/outputs/explore10/reports/explore10_atomic_primitive_candidate_table.csv
Explore10/outputs/explore10a/reports/explore10a_sample_width_attribution.csv
Explore10/outputs/explore10a/reports/explore10a_sample_width_root_cause_gate.csv
Explore10/outputs/explore10a/reports/explore10a_report.md
Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet
Explore7/data/targets/pit_industry_membership.csv
```

Required row-level cache inputs:

```text
Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet
```

These cache inputs may be used only for row-level width attribution, feature availability width calculation, and row identity reconciliation. They must not be used for candidate generation.

If these cache inputs are missing, Explore10B must fail preflight with:

```text
missing_required_row_level_cache
```

It must not substitute `feature_available_count` from `explore10_fold_trainability_audit.csv` for feature-bank-v1 available distinct instrument width.

### 6.1 Row Identity Reconciliation Authority

Explore10B 必须把 row identity reconciliation 写成 task-aware 规则，不能只按 `instrument / fold_id` 粗 join。

Canonical launch identity keys:

```text
instrument
fold_id
signal_date
event_effective_date
launch_stratum_event_id
```

Canonical failure identity keys:

```text
instrument
fold_id
failure_signal_date as signal_date
failure_decision_effective_date as event_effective_date
launch_stratum_event_id
atomic_failure_event_id
```

If a source artifact lacks a task-specific optional key, implementation must record:

```text
row_identity_key_status = schema_key_missing
schema_key_missing_keys = <semicolon-separated missing keys>
```

Missing optional keys are preflight/schema findings, not row mismatches. A row mismatch may be counted only after joining on the available canonical key set documented in the output artifact.

Required row-identity audit fields must appear in either `explore10b_electronics_data_discipline_audit.csv` or `explore10b_preflight_reference_artifact_audit.csv`:

```text
target_industry
task
fold_id
row_identity_join_key_set
row_identity_key_status
schema_key_missing_keys
schema_key_missing_count
row_identity_match_count
row_identity_missing_from_reference_count
row_identity_extra_in_reference_count
row_identity_mismatch_count
row_identity_join_status
pass
```

### 6.2 Feature Availability Source Authority

`feature_bank_v1_available_distinct_instruments` must be computed from row-level Explore10 cache, not inferred from report-only columns.

Allowed source:

```text
Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
```

Allowed feature availability calculation:

```text
For each industry/task/fold:
  count distinct instruments among rows where
  target_industry_name = 电子 or industry = 电子,
  task/source_task = launch_winner or failure_reject,
  fold_id = current fold,
  sample_has_required_features = true,
  feature_asof_leakage_violation = false if present.
```

Task-specific trainability denominator predicates:

```text
launch_winner trainability denominator:
  industry_launch_model_train_eval_eligible = true

failure_reject trainability denominator:
  industry_failure_model_train_eval_eligible = true
```

These trainability predicates may be used for `trainability_denominator_distinct_instruments`, but they must not be used to inflate `feature_bank_v1_available_distinct_instruments`. The feature-availability denominator is the v1 feature-available row scope; trainability is a later, narrower gate.

Required predicate fields:

```text
feature_availability_predicate_name
feature_availability_predicate_columns
feature_availability_source_panel
feature_availability_source_hash
feature_availability_fallback_used
feature_availability_fallback_reason
```

If the exact feature availability predicate is not present in the cache, implementation must emit:

```text
feature_availability_width_status = not_directly_available_from_source_cache
```

and Explore10B cannot pass the width gate unless `trainability_denominator_distinct_instruments` already demonstrates the same or narrower v1-eligible denominator with documented source fields.

---

## 7. Hard Gates

### 7.1 Width gate

Required artifact:

```text
explore10b_electronics_sample_width_gate.csv
```

Minimum fields:

```text
target_industry
task
fold_id
fold_role
scope_locked_distinct_instruments
feature_bank_v1_available_distinct_instruments
trainability_denominator_distinct_instruments
min_distinct_instruments_original
width_guardrail_pass
fold_2020_zero_launch_row_status
electronics_launch_width_solved_excluding_expected_fold_2020_boundary
electronics_launch_width_solved
electronics_failure_width_diagnostic_pass
width_problem_solved_phase_level
failed_width_reason
feature_availability_width_source
feature_availability_width_status
pass
```

### 7.2 Trainability denominator gate

Required artifact:

```text
explore10b_electronics_trainability_denominator_audit.csv
```

Minimum fields:

```text
target_industry
task
fold_id
train_event_count_after_purge
train_positive_count_after_purge
validation_event_count
validation_positive_count
feature_available_count
distinct_instruments
distinct_instrument_years
trainability_denominator_source
model_fit_pass_reference
trainability_guardrail_pass_reference
explore10_fold_trainability_pass_reference
failed_predicate_reference
sample_width_failure_only
pass
```

`model_fit_pass_reference` 可以来自 Explore10 已有结果，但 Explore10B 不得重新训练模型来选择版本。

### 7.3 Data discipline gate

Required artifact:

```text
explore10b_electronics_data_discipline_audit.csv
```

Minimum fields:

```text
target_industry
task
fold_id
feature_asof_leakage_violation_count
observed_reference_decision_overlap_count
observed_reference_feature_overlap_count
observed_reference_decision_feature_overlap_eligible_rows
walk_forward_purge_pass
row_identity_mismatch_count
row_identity_join_key_set
row_identity_key_status
schema_key_missing_keys
schema_key_missing_count
row_identity_match_count
row_identity_missing_from_reference_count
row_identity_extra_in_reference_count
row_identity_join_status
fold_2024_used_for_support
feature_asof_audit_scope
feature_asof_source_artifact
observed_reference_source_artifact
purge_source_artifact
scope_lock_source_artifact
discipline_pass
```

Schema alignment rule:

```text
feature_asof_leakage_audit is feature-bank/global or fold-source scoped;
observed_reference_overlap_audit is industry/task/fold scoped;
walk_forward_purge_audit is industry/task/fold scoped;
scope_lock is industry/task/fold scoped.
```

If an input artifact is not naturally task/fold scoped, implementation must not fabricate per-task row support. It must record:

```text
feature_asof_audit_scope = global_feature_bank_audit
```

and combine it with task/fold scoped observed-reference, purge, and scope-lock checks.

### 7.4 Automotive comparison gate

Required artifact:

```text
explore10b_electronics_vs_automotive_width_comparison.csv
```

Minimum fields:

```text
comparison_scope
target_industry
task
fold_id
scope_locked_distinct_instruments
feature_bank_v1_available_distinct_instruments
trainability_denominator_distinct_instruments
trainable_core_fold_count
primary_bottleneck
failed_predicate
width_delta_vs_automotive
comparison_pass
```

This comparison is diagnostic only. Automotive cannot become primary in Explore10B.

### 7.5 Candidate reference count audit

Required artifact:

```text
explore10b_candidate_reference_count_audit.csv
```

Minimum fields:

```text
industry
task
reference_candidate_count
source_artifact
source_column_allowlist
candidate_count_calculation
formula_columns_read
primitive_text_read
threshold_columns_read
metric_value_columns_read
candidate_count_used_for_width_probe_only
pass
```

Required:

```text
source_column_allowlist = industry;task
candidate_count_calculation = grouped_row_count_from_industry_task_only
formula_columns_read = false
primitive_text_read = false
threshold_columns_read = false
metric_value_columns_read = false
candidate_count_used_for_width_probe_only = true
```

### 7.6 Cache tracking audit

Required artifact:

```text
explore10b_cache_tracking_audit.csv
```

Minimum fields:

```text
artifact_name
artifact_path
is_parquet_cache
exists
git_check_ignore_pass
tracked_by_git
row_level_csv_generated_by_default
pass
```

All `Explore10/outputs/explore10b/cache/*.parquet` files must be ignored by git and must not be tracked.

---

### 7.7 Recommendation gate

Required artifact:

```text
explore10b_recommendation_gate.csv
```

Minimum fields:

```text
electronics_launch_width_solved_excluding_expected_fold_2020_boundary
width_problem_solved_phase_level
electronics_failure_width_diagnostic_pass
secondary_failure_diagnostic_status
secondary_failure_blocking
data_discipline_pass
scope_selection_lineage_pass
scope_role_relabel_pass
candidate_reference_count_audit_pass
cache_tracking_pass
required_artifact_authority_pass
forbidden_recommendation_violation_count
fold_2024_support_usage_count
threshold_selection_violation_count
metric_selection_violation_count
recommendation
recommendation_allowed
recommendation_reason
pass
```

---

## 8. Feature Bank Boundary

Explore10B does not repair feature bank v1.

Explore10B may report v1 availability width, but it must not output:

```text
feature_bank_v2_hygiene_pass
feature_bank_v2_dictionary
feature_bank_v2_rerun
feature_bank_v2_selected_features
```

Reason:

```text
Explore10B 的唯一目标是判断电子行业是否解决样本宽度问题。
如果电子在 v1 下已经通过 width gate，下一阶段再单独决定是否需要 v2 hygiene。
如果电子在 v1 下仍不通过 width gate，v2 也不应被用来掩盖 denominator 不足。
```

Allowed feature-bank status:

```text
feature_bank_v1_width_availability_profile_only
```

---

## 9. Candidate / Metric Boundary

Explore10B may read Explore10 candidate reference counts only as evidence that electronics was trainable enough to produce path records.

Explore10B must not evaluate:

```text
primitive lift
candidate-level null
FDR
manualizability
score bucket
strategy backtest
P1 readiness
```

If the implementation reads `explore10_atomic_primitive_candidate_table.csv`, it may use only:

```text
industry
task
```

`reference_candidate_count` must be calculated as:

```text
count rows grouped by industry/task after reading only industry and task columns
```

If a `candidate_count` column exists in any future source artifact, Explore10B must ignore it unless a later requirement explicitly changes this boundary.

It must not use:

```text
primitive_text
formula_text_resolved
feature thresholds
real_metric_value
candidate ranking
```

---

## 10. Acceptance Criteria

### 10.1 Pass condition

Explore10B passes if:

```text
1. electronics_launch_width_solved_excluding_expected_fold_2020_boundary = true;
2. width_problem_solved_phase_level = true;
3. secondary_failure_blocking = false;
4. data_discipline_pass = true;
5. required_artifact_authority_pass = true;
6. no forbidden output violation;
7. no fold_2024 support usage;
8. no threshold or metric selection violation;
9. scope_selection_lineage_pass = true;
10. scope_role_relabel_pass = true;
11. candidate_reference_count_audit_pass = true;
12. cache_tracking_pass = true.
```

### 10.2 Fail condition

Explore10B fails if:

```text
1. electronics launch has fewer than 3 core folds with trainability_denominator_distinct_instruments >= 20;
2. fold_2020 launch zero rows remain unresolved;
3. feature availability collapses electronic launch below 20 in fold_2021/fold_2022/fold_2023;
4. row identity mismatch explains the apparent width;
5. feature-asof / observed-reference / purge discipline fails;
6. implementation uses fold_2024 for support;
7. implementation outputs primitive or strategy recommendation;
8. secondary_failure_blocking = true.
```

### 10.3 Recommendation enum

Allowed recommendations:

```text
proceed_to_explore10c_electronics_path_quality_requirement
continue_explore10b_electronics_width_audit
stop_electronics_probe_due_to_sample_width
stop_due_to_electronics_data_discipline_violation
```

Forbidden recommendations:

```text
proceed_to_explore10b_atomic_feature_bank_v2_rerun
proceed_to_explore11_manual_atomic_primitive_formula_discovery
candidate_for_p1_strategy
proceed_to_strategy_backtest
validated_model
selected_lgbm_model
selected_score_bucket
atomic_primitive_candidate_for_next_requirement
freeze_strategy
```

---

## 11. Required Outputs

All reports must be written to:

```text
Explore10/outputs/explore10b/reports/
```

All row-level parquet caches must be written to:

```text
Explore10/outputs/explore10b/cache/
```

Parquet caches must be gitignored.

### 11.1 Required report artifacts

```text
explore10b_run_manifest.json
explore10b_preflight_reference_artifact_audit.csv
explore10b_scope_selection_lineage_audit.csv
explore10b_scope_role_relabel_audit.csv
explore10b_electronics_sample_width_gate.csv
explore10b_electronics_row_attrition_waterfall.csv
explore10b_electronics_trainability_denominator_audit.csv
explore10b_electronics_feature_availability_width_audit.csv
explore10b_electronics_data_discipline_audit.csv
explore10b_electronics_vs_automotive_width_comparison.csv
explore10b_candidate_reference_count_audit.csv
explore10b_fold_2024_nonselection_audit.csv
explore10b_metric_nonselection_audit.csv
explore10b_threshold_nonselection_audit.csv
explore10b_forbidden_recommendation_self_check.csv
explore10b_required_artifact_authority_audit.csv
explore10b_cache_tracking_audit.csv
explore10b_recommendation_gate.csv
explore10b_report.md
```

### 11.2 Required cache artifacts

```text
explore10b_electronics_launch_width_panel.parquet
explore10b_electronics_failure_width_panel.parquet
explore10b_electronics_feature_availability_panel.parquet
```

No row-level CSV export is allowed by default.

### 11.3 Required artifact schemas not defined above

`explore10b_run_manifest.json` minimum keys:

```text
phase
requirement_path
config_path
output_root
command
run_started_at
run_completed_at
input_artifacts
output_artifacts
artifact_count_expected
artifact_count_produced
required_artifact_authority_pass
electronics_launch_width_solved_excluding_expected_fold_2020_boundary
width_problem_solved_phase_level
secondary_failure_diagnostic_status
recommendation
recommendation_allowed
pass
```

Each `input_artifacts` and `output_artifacts` item must include:

```text
artifact_name
artifact_path
exists
file_size_bytes
sha256
row_count
column_count
artifact_authority
```

`explore10b_preflight_reference_artifact_audit.csv` minimum fields:

```text
artifact_name
artifact_path
required
exists
readable
file_size_bytes
sha256
row_count
column_count
required_columns_present
missing_required_columns
authority_role
preflight_status
pass
```

`explore10b_electronics_row_attrition_waterfall.csv` minimum fields:

```text
target_industry
task
fold_id
stage_order
stage_name
source_artifact
row_count
distinct_instruments
loss_from_previous_stage
loss_reason
unknown_loss_count
unknown_loss_weight_share
pass
```

Required waterfall stages:

```text
pit_industry_membership
event_source_rows
scope_locked_rows
feature_bank_v1_available_rows
trainability_denominator_rows
model_fit_reference_rows
path_record_reference_rows
```

`explore10b_electronics_feature_availability_width_audit.csv` minimum fields:

```text
target_industry
task
fold_id
source_panel_path
source_panel_hash
source_filter_expression
feature_availability_predicate_name
feature_availability_predicate_columns
feature_available_row_count
feature_bank_v1_available_distinct_instruments
trainability_denominator_distinct_instruments
fallback_used
fallback_reason
feature_availability_width_status
pass
```

`explore10b_fold_2024_nonselection_audit.csv` minimum fields:

```text
artifact_name
fold_id
fold_role
fold_2024_rows_observed
used_for_width_support
used_for_threshold_selection
used_for_metric_selection
used_for_candidate_selection
fold_2024_support_usage_count
pass
```

`explore10b_metric_nonselection_audit.csv` minimum fields:

```text
source_artifact
metric_columns_present
metric_columns_read
metric_values_used_for_selection
selected_metric_name
metric_selection_violation_count
pass
```

`explore10b_threshold_nonselection_audit.csv` minimum fields:

```text
source_artifact
threshold_columns_present
threshold_columns_read
raw_threshold_values_used
quantile_threshold_values_used
threshold_selection_violation_count
pass
```

`explore10b_forbidden_recommendation_self_check.csv` minimum fields:

```text
output_artifact
forbidden_token
token_found
recommendation_value
forbidden_recommendation_violation_count
forbidden_output_violation_count
pass
```

`explore10b_required_artifact_authority_audit.csv` minimum fields:

```text
artifact_name
artifact_path
required_by_section
produced
schema_pass
row_count
column_count
sha256
source_authority
authority_pass
pass
```

---

## 12. Report Requirements

`explore10b_report.md` must be in Chinese and must answer:

```text
1. 电子是否解决了汽车暴露的样本宽度问题？
2. 电子 launch 的 fold_2021/fold_2022/fold_2023 是否都 >=20 distinct instruments？
3. fold_2020 launch zero rows 是否已分类？
4. 电子 failure 的 `secondary_failure_diagnostic_status` 是 pass、nonblocking fail，还是 blocking fail？
5. feature availability 后电子宽度是否仍然足够？
6. 电子宽度优势是否来自真实 row scope，而不是 leakage / mismatch？
7. 与汽车相比，宽度差异是多少？
8. 电子作为 Explore10B primary 是否属于后验选择，边界如何处理？
9. Explore10 reference role 如何被重标为 Explore10B role？
10. candidate reference count 是否只按 industry/task 分组行数计算，并且只作为宽度证据使用？
11. 是否可以进入下一份 path-quality requirement？
12. 本阶段没有回答哪些问题？
13. 是否触发任何 forbidden output？
```

The report must include an explicit sentence:

```text
Explore10B 只证明电子是否解决样本宽度问题，不证明电子 primitive 有效。
```

---

## 13. Config Sketch

```yaml
phase: explore10b
title: electronics_sample_width_feasibility_probe
output_root: Explore10/outputs/explore10b
requirement_path: Explore10/requirement_explore10b.md

scope:
  primary:
    industry: 电子
    task: launch_winner
    role: primary_sample_width_probe
  secondary:
    industry: 电子
    task: failure_reject
    role: secondary_width_diagnostic
  reference_only:
    industry: 汽车
    tasks: [launch_winner, failure_reject]
    role: failed_width_reference_only

folds:
  core: [fold_2020, fold_2021, fold_2022, fold_2023]
  launch_width_required_core: [fold_2021, fold_2022, fold_2023]
  robustness_only: [fold_2024]
  fold_2024_used_for_support: false
  fold_2020_launch_zero_row_allowed_status: expected_event_history_boundary

thresholds:
  min_distinct_instruments_original: 20
  min_launch_width_pass_core_folds: 3
  max_unknown_width_loss_weight_share: 0.01
  max_feature_asof_leakage_violation_count: 0
  max_observed_reference_decision_feature_overlap_eligible_rows: 0

paths:
  explore10_scope_lock: Explore10/outputs/explore10/reports/explore10_scope_lock.csv
  explore10_trainability: Explore10/outputs/explore10/reports/explore10_fold_trainability_audit.csv
  explore10_feature_asof_leakage: Explore10/outputs/explore10/reports/explore10_feature_asof_leakage_audit.csv
  explore10_observed_reference_overlap: Explore10/outputs/explore10/reports/explore10_observed_reference_overlap_audit.csv
  explore10_purge: Explore10/outputs/explore10/reports/explore10_walk_forward_purge_audit.csv
  explore10_candidate_table: Explore10/outputs/explore10/reports/explore10_atomic_primitive_candidate_table.csv
  explore10a_width_attribution: Explore10/outputs/explore10a/reports/explore10a_sample_width_attribution.csv
  explore10_lgbm_train_eval_panel: Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
  explore10_atomic_launch_event_panel: Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
  explore10_atomic_failure_decision_panel: Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet

source_authority:
  feature_bank_v1_available_distinct_instruments: row_level_explore10_cache_only
  trainability_denominator_distinct_instruments: explore10_fold_trainability_audit.distinct_instruments
  reference_candidate_count: grouped_row_count_from_industry_task_only

row_identity_keys:
  launch_winner: [instrument, fold_id, signal_date, event_effective_date, launch_stratum_event_id]
  failure_reject: [instrument, fold_id, failure_signal_date, failure_decision_effective_date, launch_stratum_event_id, atomic_failure_event_id]
  missing_optional_key_status: schema_key_missing

feature_availability_predicates:
  common: [target_industry_name_or_industry_equals_scope, task_or_source_task_equals_scope, fold_id_equals_scope, sample_has_required_features_true]
  launch_trainability_denominator: industry_launch_model_train_eval_eligible_true
  failure_trainability_denominator: industry_failure_model_train_eval_eligible_true

secondary_failure:
  blocking_statuses: [secondary_data_discipline_violation_blocking, unresolved_blocking]
  nonblocking_statuses: [pass, secondary_only_width_fail_nonblocking]

allowed_recommendations:
  - proceed_to_explore10c_electronics_path_quality_requirement
  - continue_explore10b_electronics_width_audit
  - stop_electronics_probe_due_to_sample_width
  - stop_due_to_electronics_data_discipline_violation

forbidden_outputs:
  - proceed_to_explore10b_atomic_feature_bank_v2_rerun
  - proceed_to_explore11_manual_atomic_primitive_formula_discovery
  - candidate_for_p1_strategy
  - proceed_to_strategy_backtest
  - validated_model
  - selected_lgbm_model
  - selected_score_bucket
  - atomic_primitive_candidate_for_next_requirement
  - freeze_strategy
```

---

## 14. Implementation Notes

Expected future commands:

```bash
uv run python Explore10/scripts/run_explore10.py profile-explore10b --config Explore10/configs/electronics_sample_width_feasibility_explore10b.yaml
uv run python Explore10/scripts/run_explore10.py report-explore10b --config Explore10/configs/electronics_sample_width_feasibility_explore10b.yaml
```

These commands are not implemented by this requirement document.

Implementation must preserve existing Explore10 and Explore10A commands.

---

## 15. Final Boundary Statement

Explore10B is a narrow feasibility phase.

It may conclude:

```text
电子解决了样本宽度问题，可以写 Explore10C 来验证 path quality。
```

It may also conclude:

```text
电子没有解决样本宽度问题，继续用行业标签做 path-to-primitive 没有意义。
```

It must not conclude:

```text
电子 primitive 有效。
电子可以进入 P1。
电子可以回测。
电子可以替代汽车产业链问题。
```

The only valid success meaning is:

```text
electronics_sample_width_solved_for_next_requirement = true
```
