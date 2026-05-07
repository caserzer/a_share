# Explore10C 需求说明：电子行业 Path Quality 与 Primitive Quality 审计

> 文件名：`requirement_explore10c.md`
> 阶段：`Explore10C` / `P0.10C`
> 标题：Electronics Path-Quality and Primitive-Quality Audit
> 状态：implementation-ready requirement
> 生成日期：2026-05-07
> 重要说明：Explore10C 只验证电子行业在样本宽度足够后，path records / primitive seeds 是否具备稳定、可解释、非后验污染的质量证据；不做策略回测，不输出 P1 candidate，不选择 score bucket。

---

## 0. 一句话结论

Explore10A 已证明汽车单行业的主瓶颈是：

```text
phase_level_primary_bottleneck = automotive_scope_width
```

Explore10B 已证明切换到电子后，样本宽度瓶颈被解决：

```text
recommendation = proceed_to_explore10c_electronics_path_quality_requirement
width_problem_solved_phase_level = true
electronics_launch_width_solved_excluding_expected_fold_2020_boundary = true
secondary_failure_diagnostic_status = pass
```

Explore10C 只做下一件事：

```text
在电子行业样本宽度已足够的前提下，
先补做 feature bank v2 hygiene，
再验证电子 path records / primitive seeds 是否有足够的质量证据。
```

Explore10C 的唯一核心问题是：

```text
电子行业在样本宽度足够的前提下，Explore10 产生的 path records
是否有稳定、可解释、非后验污染的 primitive-quality evidence？
```

---

## 1. 背景

### 1.1 Explore10A 已完成但没有做 v2

Explore10A 的 Phase-0 root-cause proof 已完成。结论是汽车 scope 本身过窄：

```text
recommendation = stop_automotive_single_industry_path_due_to_sample_width
sample_width_root_cause_proven_phase_level = true
phase_level_primary_bottleneck = automotive_scope_width
```

因此 Explore10A 中以下 v2 模块只输出了 status-only artifact：

```text
explore10a_feature_bank_v1_to_v2_hygiene_audit.csv
explore10a_feature_bank_v2_dictionary.csv
explore10a_feature_bank_v2_feature_drop_log.csv
explore10a_feature_bank_v2_duplicate_cluster_audit.csv
explore10a_feature_bank_v2_missingness_by_fold.csv
explore10a_feature_bank_v2_missingness_by_instrument.csv
explore10a_feature_bank_v2_family_coverage_audit.csv
explore10a_trainability_counterfactual_audit.csv
explore10a_electronics_placebo_guardrail_audit.csv
```

Required interpretation:

```text
这些 artifact 的 not_started 状态不是实现遗漏；
它们是被 automotive_scope_width hard gate 正确阻断。
```

Explore10C 不得把 10A 的 status-only v2 artifact 当作 v2 已完成证据。Explore10C 必须在电子 scope 下重新构造和审计 v2。

### 1.2 Explore10B 已完成宽度验证

Explore10B 的研究数据：

```text
电子 launch required core folds trainability denominator = 24 / 24 / 25
电子 launch required core folds feature-available instruments = 26 / 25 / 27
电子 failure core folds trainability denominator = 21 / 24 / 24 / 25
fold_2024 support usage = 0
row identity mismatch = 0
feature_asof_leakage_violation_count = 0
observed_reference_decision_feature_overlap_eligible_rows = 0
```

Explore10B 只证明：

```text
电子解决了样本宽度问题。
```

Explore10B 没有证明：

```text
电子 path 有 alpha；
电子 primitive 有效；
电子可进入 P1；
电子可回测；
电子可形成交易规则。
```

### 1.3 为什么需要 Explore10C

Explore10 原始报告显示电子 reference scope 产生了 99 条 candidate-like path records：

```text
电子 launch_winner reference candidate count = 49
电子 failure_reject reference candidate count = 50
```

但 10B 对 candidate table 的使用边界很窄：只读取 `industry/task` 并按行计数。Explore10C 才允许在严格门禁下审计这些 path / primitive 是否有质量。

Explore10C 必须避免一个常见错误：

```text
因为电子样本更宽，所以把电子 path 直接当成有效 primitive。
```

正确目标是：

```text
电子样本更宽以后，是否仍然能在 OOF、null、placebo、concentration、
slice stability、manualizability 约束下留下可进入下一份人工公式复核 requirement 的 primitive seed？
```

---

## 2. 阶段定位

Explore10C 是 `path-quality / primitive-quality audit`。

Explore10C 只回答 9 个问题：

```text
1. 10B 的电子样本宽度 pass 是否可继承，且没有 fold_2024 support usage？
2. Alpha158-like feature bank v1 在电子 scope 下是否仍有 missing / duplicate / family imbalance 问题？
3. 能否用 train-scope unsupervised 规则构造 feature bank v2？
4. v2 是否降低 missingness 和重复簇，同时保留 feature-family coverage？
5. 在固定 probe contract 下，电子 launch 是否能产生可冻结的 path patterns？
6. 冻结后的 path / primitive seed 是否在 core OOF folds 上有稳定支持？
7. 这些 seed 是否压过 label-permutation null、instrument-year block null、path-structure null 和 placebo guardrail？
8. 这些 seed 是否存在 instrument / instrument-year concentration 或 slice instability？
9. 是否可以进入下一份 manual primitive formula review requirement？
```

Explore10C 不回答：

```text
哪个 score bucket 可交易？
哪个 LightGBM model 最好？
电子行业是否有可直接回测策略？
电子是否进入 P1？
电子是否能替代真实上下游产业链 cohort？
```

---

## 3. Scope

### 3.1 Primary scope

```text
target_industry = 电子
primary_task = launch_winner
scope_role = primary_path_quality_audit
```

Primary scope 是唯一可以产生 `manual_review_seed` 的 scope。

### 3.2 Secondary diagnostic scope

```text
target_industry = 电子
secondary_task = failure_reject
scope_role = secondary_failure_diagnostic
```

Failure task 可以作为：

```text
false-positive / false-reject diagnostic
placebo-dominance guardrail
mechanism contrast evidence
```

但 failure task 不得直接产生 primary recommendation，也不得单独触发下一阶段。

### 3.3 Reference-only scope

```text
reference_phase = Explore10A / Explore10B
reference_industry = 汽车
role = failed_width_reference_only
```

汽车只用于解释为什么切换到电子，不参与 Explore10C candidate support、null pass 或 recommendation。

### 3.4 Fold roles

```text
fold_2020 = launch_expected_event_history_boundary / failure_core_diagnostic
fold_2021 = core_oof
fold_2022 = core_oof
fold_2023 = core_oof
fold_2024 = robustness_only
```

Hard rule:

```text
fold_2024 不得用于 feature-bank v2 selection、probe selection、path selection、
threshold selection、metric selection、candidate pass、recommendation support。
```

### 3.5 行业标签边界

Explore10C 继续把 `电子` 视为：

```text
broad denominator handle
```

而不是：

```text
真实上下游产业链定义
真实业务同质 cohort
可解释 supply-chain membership
```

因此即使 Explore10C 找到 path-quality evidence，结论仍然只属于：

```text
post-selected electronics broad-industry exploratory evidence
```

---

## 4. Hard Phase Gates

Explore10C 必须按顺序执行以下 gate。后面的 gate 不能反向修改前面的 artifact、feature definition、candidate extraction budget 或 threshold rule。

```text
Gate 0: 10B width inheritance gate
Gate 0B: post-selection lineage gate
Gate 0C: cross-cutting data discipline gate
Gate 1: feature bank v2 hygiene gate
Gate 2: fixed probe trainability and contract gate
Gate 3: path extraction and freeze gate
Gate 4: primitive translation and token coverage gate
Gate 5: OOF / baseline / null / placebo gate
Gate 6: concentration / slice stability / manualizability gate
Gate 7: recommendation gate
```

If an upstream gate fails, downstream artifacts must still exist but must be status-only with:

```text
execution_status
not_started_reason
upstream_gate
upstream_gate_pass
```

---

## 5. Gate 0: 10B Width Inheritance

Explore10C may start only if Explore10B proves:

```text
width_problem_solved_phase_level = true
electronics_launch_width_solved_excluding_expected_fold_2020_boundary = true
secondary_failure_diagnostic_status in [pass, secondary_only_width_fail_nonblocking]
recommendation = proceed_to_explore10c_electronics_path_quality_requirement
```

Required artifact:

```text
explore10c_explore10b_width_inheritance_gate.csv
```

Minimum fields:

```text
source_artifact
source_hash
width_problem_solved_phase_level
electronics_launch_width_solved_excluding_expected_fold_2020_boundary
secondary_failure_diagnostic_status
fold_2024_support_usage_count
row_identity_mismatch_count
feature_asof_leakage_violation_count
observed_reference_decision_feature_overlap_eligible_rows
explore10b_recommendation
inheritance_pass
blocked_reason
pass
```

Pass condition:

```text
inheritance_pass = true
fold_2024_support_usage_count = 0
row_identity_mismatch_count = 0
feature_asof_leakage_violation_count = 0
observed_reference_decision_feature_overlap_eligible_rows = 0
```

### 5.1 Gate 0B: Post-Selection Lineage

Explore10C inherits a post-selected electronics scope. It must not treat electronics as an originally preregistered primary industry.

Required artifact:

```text
explore10c_scope_selection_lineage_audit.csv
```

Minimum fields:

```text
selected_industry
selected_primary_task
selection_source_phase
selection_source_artifact
selection_reason
was_selected_after_observing_trainability
was_selected_after_observing_candidate_count
was_selected_after_automotive_width_failure
selection_metric_used_for_scope
selection_metric_allowed_for_10c
post_selection_family_id
selection_family_null_required
allowed_conclusion
forbidden_conclusion
scope_selection_lineage_pass
pass
```

Required values:

```text
selected_industry = 电子
selected_primary_task = launch_winner
selection_source_phase = Explore10 / Explore10A / Explore10B
was_selected_after_observing_trainability = true
was_selected_after_observing_candidate_count = true
was_selected_after_automotive_width_failure = true
selection_metric_allowed_for_10c = true
selection_family_null_required = true
allowed_conclusion = post_selected_electronics_manual_review_seed_allowed
forbidden_conclusion = electronics_alpha_validated_or_tradable_primitive
```

Pass condition:

```text
scope_selection_lineage_pass = true
```

This pass does not remove post-selection risk. It only proves the risk was recorded and carried into null / placebo interpretation.

### 5.2 Gate 0C: Cross-Cutting Data Discipline

Explore10C must not rely only on Explore10B discipline audits. Explore10C creates new v2 panels, fixed-probe predictions, path-support panels, primitive OOF panels, and null/placebo panels; each new row surface must have its own discipline audit.

Required artifact:

```text
explore10c_data_discipline_audit.csv
```

Minimum fields:

```text
row_surface_name
row_surface_path
target_industry
task
fold_id
feature_bank_version
probe_contract_id
row_count
distinct_instruments
row_identity_key_set
row_identity_key_status
schema_key_missing_keys
schema_key_missing_count
row_identity_duplicate_count
row_identity_mismatch_count
feature_asof_date_column
label_measurement_date_column
event_effective_date_column
decision_reference_date_column
feature_asof_leakage_violation_count
observed_reference_decision_overlap_count
observed_reference_feature_overlap_count
observed_reference_label_measurement_overlap_count
walk_forward_purge_violation_count
fold_2024_used_for_support
data_discipline_pass
pass
```

Required row surfaces:

```text
v1_reference_train_eval_panel
v2_hygiene_train_eval_panel
v2_feature_availability_panel
fixed_probe_prediction_panel
path_support_panel
primitive_seed_oof_panel
null_placebo_panel
```

Pass condition:

```text
row_identity_duplicate_count = 0
row_identity_mismatch_count = 0
feature_asof_leakage_violation_count = 0
observed_reference_decision_overlap_count = 0
observed_reference_feature_overlap_count = 0
observed_reference_label_measurement_overlap_count = 0
walk_forward_purge_violation_count = 0
fold_2024_used_for_support = false
data_discipline_pass = true
```

If any downstream module executes, the corresponding row surface must appear in `explore10c_data_discipline_audit.csv`. Status-only downstream artifacts must record the upstream gate that blocked execution.

---

## 6. Gate 1: Feature Bank v2 Hygiene

### 6.1 Purpose

Explore10C must complete the v2 series that Explore10A did not run. It must do this under electronic scope, not under automotive scope.

Feature bank v2 is:

```text
a hygiene version of Alpha158-like v1
```

Feature bank v2 is not:

```text
a new alpha search
a validation-metric-selected feature set
a candidate-table-selected feature set
a feature importance-selected model surface
```

### 6.2 Allowed construction sources

Feature bank v2 may use only:

```text
predeclared v1 formulas
train-scope unsupervised missingness
train-scope unsupervised correlation / duplicate clustering
formula complexity
feature-family coverage constraints
feature-asof rule authority
```

Feature bank v2 may not use:

```text
labels
validation AUC / logloss / lift
OOF primitive support
candidate table ranking
path support
null outcome
placebo outcome
fold_2024
P0.9B high-score coverage
feature importance
score bucket
strategy return
```

### 6.3 Train-scope definition

For v2 construction:

```text
construction_target_folds = fold_2021, fold_2022, fold_2023
target_industry = 电子
primary_task = launch_winner
sample rows = fold-local training rows eligible for primary train/eval panel before label/metric use
```

`fold_2024` is excluded.

Failure task may be used only for robustness diagnostics after v2 is frozen. It cannot select v2 features.

Feature-bank v2 construction must be fold-local for leakage control:

```text
feature_bank_v2_scope_id = v2_hygiene_fold_<fold_id>
rows_used_for_missingness = rows in that fold's training split only
rows_used_for_correlation = rows in that fold's training split only
rows_from_that_fold_validation_period = 0
labels_read_for_v2 = false
oof_metric_read_for_v2 = false
```

A global reporting dictionary may be emitted only after all fold-local v2 dictionaries are frozen. It must be derived mechanically from fold-local dictionaries:

```text
global_v2_dictionary_rule = intersection_of_core_fold_v2_features
```

or, if the implementation uses a union for diagnostics:

```text
global_v2_dictionary_rule = union_reference_only_not_recommendation_eligible
```

Only `intersection_of_core_fold_v2_features` can support `feature_bank_v2_hygiene_pass` for recommendation.

### 6.4 Duplicate representative rule

For each duplicate or high-correlation cluster, representative selection must be deterministic:

```text
1. lower train-scope missing_weight_share
2. higher fold availability count
3. lower formula complexity
4. lower feature family overrepresentation penalty
5. simpler as-of rule
6. lexicographic feature_name tie-breaker
```

No validation label or validation metric may be used.

Cluster construction must be deterministic:

```text
correlation_method = spearman_on_train_scope_rank_values
missing_pair_policy = pairwise_non_null
duplicate_corr_abs_threshold = thresholds.duplicate_corr_abs_threshold
duplicate_min_pairwise_non_null_count = thresholds.duplicate_min_pairwise_non_null_count
cluster_algorithm = connected_components_on_abs_corr_graph
```

Near-constant feature definition:

```text
constant_or_near_constant = true
if non_null_unique_value_count <= 1
or top_value_weight_share >= thresholds.max_top_value_share_for_nonconstant
```

Formula complexity score must be computed before any metric is read:

```text
formula_complexity_score =
  operator_count
  + window_token_count
  + 2 * nested_operator_count
  + 5 * unmapped_formula_token_count
```

Feature-family overrepresentation penalty:

```text
feature_family_overrepresentation_penalty =
  max(0, family_share_if_selected - thresholds.max_feature_family_share)
```

### 6.5 Required v2 gates

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
feature_count_after_hygiene >= thresholds.min_feature_count_after_hygiene
rows_from_validation_period_for_v2 = 0
labels_read_for_v2 = false
oof_metric_read_for_v2 = false
global_v2_dictionary_rule = intersection_of_core_fold_v2_features
```

### 6.6 Required artifacts

```text
explore10c_feature_bank_v1_profile_audit.csv
explore10c_feature_bank_v1_to_v2_hygiene_audit.csv
explore10c_feature_bank_v2_dictionary.csv
explore10c_feature_bank_v2_feature_drop_log.csv
explore10c_feature_bank_v2_duplicate_cluster_audit.csv
explore10c_feature_bank_v2_missingness_by_fold.csv
explore10c_feature_bank_v2_missingness_by_instrument.csv
explore10c_feature_bank_v2_family_coverage_audit.csv
```

Minimum fields for `explore10c_feature_bank_v1_to_v2_hygiene_audit.csv`:

```text
feature_bank_version_from
feature_bank_version_to
target_industry
task
train_scope_folds
feature_bank_v2_scope_id
global_v2_dictionary_rule
rows_used_for_missingness_count
rows_used_for_correlation_count
rows_from_validation_period_for_v2
labels_read_for_v2
oof_metric_read_for_v2
v1_feature_count
v2_feature_count
dropped_feature_count
missing_weight_share_before
missing_weight_share_after
missing_row_rate_before
missing_row_rate_after
duplicate_or_high_corr_cluster_count_before
duplicate_or_high_corr_cluster_count_after
constant_or_near_constant_rate_before
constant_or_near_constant_rate_after
max_feature_family_share_before
max_feature_family_share_after
feature_family_coverage_after_hygiene
feature_asof_leakage_violation_count
unmapped_formula_token_count
label_or_metric_used_for_v2
fold_2024_used_for_v2
feature_bank_v2_hygiene_pass
pass
```

---

## 7. Gate 2: Fixed Probe Contract

### 7.1 Probe policy

Explore10C may train fixed LightGBM probes only after v2 is frozen.

Allowed:

```text
fixed LightGBM parameters
fixed rounds
no inner validation
no hyperparameter search
no early stopping
no metric-based model selection
same probe contract across core folds
```

Forbidden:

```text
model selection by AUC / logloss / lift
score bucket selection
threshold tuning
feature importance selection
fold_2024 model selection
choosing v1 vs v2 by OOF metric
```

### 7.2 Probe variants

Required variants:

```text
v1_reference_probe
v2_hygiene_probe
```

Interpretation:

```text
v1_reference_probe = reference-only baseline for comparison
v2_hygiene_probe = only variant eligible for path-quality recommendation
```

If v2 fails hygiene, `v2_hygiene_probe` must be status-only and no path-quality recommendation is allowed.

### 7.3 Required artifacts

```text
explore10c_probe_contract_audit.csv
explore10c_lgbm_fixed_probe_audit.csv
explore10c_trainability_counterfactual_audit.csv
```

Minimum fields:

```text
target_industry
task
fold_id
feature_bank_version
probe_contract_id
fixed_params_hash
hyperparameter_search_used
early_stopping_used
metric_selection_used
fold_2024_used_for_probe_selection
train_rows
train_positive_count
validation_rows
validation_positive_count
distinct_instruments
distinct_instrument_years
feature_count
model_fit_sanity_pass
prediction_std_sanity_pass
trainability_guardrail_pass
failed_predicate
path_extraction_allowed
pass
```

No AUC, logloss, Brier, lift, score bucket, or return metric may be used for model selection.

---

## 8. Gate 3: Path Extraction and Candidate Freeze

### 8.1 Freeze-before-metrics rule

Path candidates must be frozen before any OOF, null, placebo, concentration, or slice stability metric is computed.

Required artifact:

```text
explore10c_path_candidate_freeze_audit.csv
```

Minimum fields:

```text
freeze_timestamp
feature_bank_version
probe_contract_id
candidate_extraction_budget
candidate_extraction_budget_hash
candidate_extraction_inputs_hash
max_path_depth
min_train_path_support_count
min_train_path_weighted_support
max_paths_per_fold_task
max_paths_total
path_dedup_identity
path_sort_key
candidate_metric_columns_available_before_freeze
candidate_metric_columns_read_before_freeze
oof_metric_computed_before_freeze
null_metric_computed_before_freeze
placebo_metric_computed_before_freeze
manual_formula_modified_after_freeze
freeze_pass
pass
```

Hard rule:

```text
candidate_metric_columns_read_before_freeze = false
oof_metric_computed_before_freeze = false
null_metric_computed_before_freeze = false
placebo_metric_computed_before_freeze = false
manual_formula_modified_after_freeze = false
```

### 8.2 Candidate extraction inputs

Path extraction may use:

```text
tree structure
train-fold path support count
train-fold path weighted support
path depth
feature family diversity
predeclared max candidate budget
```

Path extraction may not use:

```text
validation label outcome
OOF lift
null pass
placebo pass
candidate ranking metric from Explore10
feature importance
fold_2024
P0.9B score bucket
strategy return
```

Required extraction budget:

```text
max_path_depth = config.candidate_extraction.max_path_depth
min_train_path_support_count = config.candidate_extraction.min_train_path_support_count
min_train_path_weighted_support = config.candidate_extraction.min_train_path_weighted_support
max_paths_per_fold_task = config.candidate_extraction.max_paths_per_fold_task
max_paths_total = config.candidate_extraction.max_paths_total
max_paths_per_feature_family = config.candidate_extraction.max_paths_per_feature_family
path_dedup_identity = normalized_feature_direction_quantile_sequence
path_sort_key = train_weighted_support_desc_then_path_depth_asc_then_feature_family_diversity_desc_then_path_pattern_id_asc
```

The extraction budget must be loaded from config before model fitting starts. It cannot be changed after seeing path, OOF, null, placebo, or manualizability results.

### 8.3 Threshold canonicalization

Raw numeric split thresholds must never be used directly in primitive formulas.

Each split threshold must be canonicalized into train-fold quantile buckets:

```text
feature_name
raw_threshold_internal
quantile_bucket_count
train_fold_quantile_bucket
threshold_direction
threshold_source_fold
threshold_asof_rule
missing_branch_token
tie_policy
```

Primitive formulas may use only:

```text
feature_quantile_bucket_condition
rank / quantile comparison
directional predicate
predeclared window token
```

Forbidden in formula text:

```text
raw float threshold
leaf_id
tree_id
model score
validation metric
```

Canonicalization details:

```text
quantile_bucket_count = config.threshold_canonicalization.quantile_bucket_count
quantile_source_rows = source fold training rows only
quantile_source_excludes_validation_rows = true
quantile_source_excludes_fold_2024 = true
tie_policy = average_rank_then_lower_bucket
missing_value_policy = explicit_missing_branch_token
out_of_range_policy = clamp_to_edge_bucket
bucket_label_format = q<lower_pct>_<upper_pct>
```

Raw thresholds may be stored only in internal audit columns. Any primitive formula that contains a raw float threshold must fail.

### 8.4 Required artifacts

```text
explore10c_lgbm_raw_path_dump.csv
explore10c_path_pattern_canonicalization.csv
explore10c_path_threshold_quantile_audit.csv
explore10c_path_pattern_fold_presence.csv
```

Minimum fields for `explore10c_path_pattern_canonicalization.csv`:

```text
path_pattern_id
feature_bank_version
source_fold_id
source_tree_id_internal_only
source_leaf_id_internal_only
path_depth
feature_name_list
feature_family_list
split_direction_list
raw_threshold_internal_list
split_threshold_quantile_list
quantile_bucket_count
quantile_source_row_count
quantile_source_excludes_validation_rows
missing_branch_token_list
tie_policy
formula_tokens
raw_numeric_threshold_in_formula
leaf_id_in_formula
tree_id_in_formula
canonicalization_pass
pass
```

---

## 9. Gate 4: Primitive Translation and Token Coverage

### 9.1 Primitive seed definition

Explore10C may create:

```text
audited_electronics_primitive_seed
```

It may not create:

```text
P1 candidate
strategy rule
trade rule
selected score bucket
freeze strategy
```

### 9.2 Primitive row fields

Required artifact:

```text
explore10c_atomic_primitive_seed_table.csv
```

Minimum fields:

```text
primitive_seed_id
target_industry
task
feature_bank_version
probe_contract_id
source_path_pattern_ids
primitive_family
primitive_text
formula_text_resolved
formula_token_list
asof_rule
threshold_bucket_rule
train_support_count
oof_support_count
train_weighted_support
oof_weighted_support
core_fold_presence_count
fold_2024_support_used
raw_numeric_threshold_in_formula
leaf_id_in_formula
score_bucket_in_formula
primitive_freeze_timestamp
eligible_for_quality_audit
manual_review_seed_allowed
pass
```

### 9.3 Token coverage

Required artifact:

```text
explore10c_primitive_token_coverage_audit.csv
```

Minimum fields:

```text
primitive_seed_id
token
token_type
token_source
mapped_formula_component
asof_rule
coverage_status
unmapped_token_count
context_slice_only_token_count
raw_numeric_threshold_token_count
leaf_or_tree_token_count
token_coverage_pass
pass
```

Pass condition:

```text
unmapped_token_count = 0
context_slice_only_token_count = 0
raw_numeric_threshold_token_count = 0
leaf_or_tree_token_count = 0
```

---

## 10. Gate 5: OOF, Baseline, Null, and Placebo

### 10.1 OOF metric boundary

OOF metrics may be computed only after candidate freeze.

Allowed quality metrics:

```text
oof_support_count
oof_weighted_support
oof_positive_rate
baseline_positive_rate
oof_lift_vs_scope_baseline
fold_presence_count
null_adjusted_signal_status
```

Primary quality metric is fixed before candidate freeze:

```text
primary_quality_metric = oof_lift_vs_scope_weighted_baseline
secondary_quality_metrics = report_only
```

No implementation may choose between lift, positive-rate difference, AUC, or any other metric after seeing OOF or null results.

Forbidden selection surfaces:

```text
score bucket
portfolio return
drawdown
Sharpe
turnover
strategy hit rate
P1 backtest metric
```

### 10.2 Baseline requirement

Each primitive seed must be compared against scope-consistent baselines:

```text
industry_task_fold_baseline
candidate_scope_weighted_baseline
label_rate_baseline
support_matched_baseline
```

Sparse baselines must be flagged. A candidate cannot pass by beating an invalid sparse baseline only.

### 10.3 Null families

Required null families:

```text
label_permutation_null
instrument_year_block_null
path_structure_null
feature_family_dropout_null
```

Each primitive seed must record:

```text
selection_family_id
null_family
null_iteration_count
matched_support_bucket
real_metric
null_mean
null_p95
null_p99
real_minus_null_p95
empirical_p_value
bh_q_value
null_pass
```

Null pass condition:

```text
real_metric = oof_lift_vs_scope_weighted_baseline
real_metric >= thresholds.min_oof_lift_vs_baseline
real_minus_null_p95 >= thresholds.min_real_minus_null_p95
empirical_p_value <= thresholds.max_empirical_p_value
bh_q_value <= thresholds.max_fdr_q
null_iteration_count >= config.nulls.min_iterations
```

FDR correction scope:

```text
selection_family_id =
  target_industry
  + task
  + feature_bank_version
  + probe_contract_id
  + post_selection_family_id
```

All frozen candidate seeds in the same `selection_family_id` must be included in FDR correction, including rejected and zero-support seeds. Passing only after dropping failed candidates is a metric-selection violation.

Required FDR artifact:

```text
explore10c_candidate_family_fdr_audit.csv
```

Minimum fields:

```text
selection_family_id
primitive_seed_id
target_industry
task
feature_bank_version
probe_contract_id
frozen_candidate_count_in_family
null_family
real_metric
empirical_p_value
bh_rank
bh_q_value
included_in_fdr_family
candidate_dropped_before_fdr
candidate_dropped_before_fdr_reason
fdr_pass
metric_selection_violation_count
pass
```

### 10.4 Placebo guardrail

Required placebo/negative-control checks:

```text
electronics_failure_secondary_diagnostic
automotive_failed_width_reference_only
feature_family_dropout_placebo
label_permutation_placebo
```

Failure task cannot become the primary winner. If failure task produces stronger, more stable seeds than launch primary, record:

```text
placebo_or_secondary_dominates_primary = true
```

and block any recommendation stronger than:

```text
continue_explore10c_path_quality_audit
```

### 10.5 Required artifacts

```text
explore10c_candidate_scope_weighted_baseline.csv
explore10c_baseline_sparsity_audit.csv
explore10c_primitive_real_metric_audit.csv
explore10c_label_permutation_null_audit.csv
explore10c_instrument_year_block_null_audit.csv
explore10c_path_structure_null_audit.csv
explore10c_feature_family_dropout_audit.csv
explore10c_candidate_level_null_aggregation.csv
explore10c_candidate_family_fdr_audit.csv
explore10c_placebo_guardrail_audit.csv
```

---

## 11. Gate 6: Concentration, Slice Stability, and Manualizability

### 11.1 Concentration

Required artifact:

```text
explore10c_concentration_audit.csv
```

Minimum fields:

```text
primitive_seed_id
top_instrument_weight_share
top_instrument_year_weight_share
top5_instrument_weight_share
instrument_hhi
instrument_year_hhi
max_single_event_weight_share
support_count
weighted_support
concentration_pass
pass
```

### 11.2 Slice stability

Required artifact:

```text
explore10c_slice_stability_audit.csv
```

Required slices:

```text
fold
calendar_year
instrument
instrument_year
feature_family
event_quarter
market_regime_reference_only
```

Minimum fields:

```text
primitive_seed_id
slice_type
slice_value
support_count
weighted_support
positive_rate
baseline_rate
lift
slice_pass
instability_reason
```

### 11.3 Manualizability

Required artifact:

```text
explore10c_manualizability_audit.csv
```

Minimum fields:

```text
primitive_seed_id
formula_text_resolved
operator_count
feature_count
window_count
threshold_bucket_count
uses_only_asof_observable_inputs
raw_threshold_free
leaf_id_free
score_free
manual_formula_complexity_score
manualizability_pass
manual_review_notes
pass
```

Manualizability pass does not mean the primitive is a trade rule. It only means the formula is simple enough for a future manual formula review requirement.

---

## 12. Recommendation Gate

Explore10C may recommend a next requirement only if:

```text
1. Explore10B width inheritance pass = true
2. scope_selection_lineage_pass = true
3. data_discipline_pass = true
4. feature_bank_v2_hygiene_pass = true
5. v2_hygiene_probe trainability pass in all required launch core folds
6. candidate freeze pass = true
7. no raw numeric threshold / leaf id / score token in primitive formula
8. at least thresholds.min_quality_seed_count seeds pass OOF support and fold presence
9. each passing seed beats required null families after FDR correction
10. placebo_or_secondary_dominates_primary = false
11. concentration pass = true
12. slice stability pass = true
13. manualizability pass = true
14. no fold_2024 support usage
15. no metric / threshold / model / score-bucket selection violation
16. required artifact authority pass = true
17. cache tracking pass = true
18. forbidden output self-check pass = true
```

Required artifact:

```text
explore10c_recommendation_gate.csv
```

Minimum fields:

```text
width_inheritance_pass
scope_selection_lineage_pass
data_discipline_pass
feature_bank_v2_hygiene_pass
v2_probe_trainability_pass
candidate_freeze_pass
primitive_token_coverage_pass
oof_quality_seed_count
null_pass_seed_count
fdr_pass_seed_count
candidate_family_fdr_pass
placebo_or_secondary_dominates_primary
concentration_pass_seed_count
slice_stability_pass_seed_count
manualizability_pass_seed_count
fold_2024_support_usage_count
metric_selection_violation_count
threshold_selection_violation_count
model_selection_violation_count
score_bucket_selection_violation_count
required_artifact_authority_pass
cache_tracking_pass
forbidden_output_violation_count
recommendation
recommendation_allowed
recommendation_reason
pass
```

---

## 13. Allowed and Forbidden Recommendations

Allowed recommendations:

```text
proceed_to_explore10d_electronics_manual_primitive_formula_review_requirement
continue_explore10c_path_quality_audit
stop_due_to_feature_bank_v2_hygiene_failure
stop_due_to_no_electronics_path_quality_evidence
stop_due_to_null_or_placebo_collapse
stop_due_to_concentration_or_slice_instability
stop_due_to_data_discipline_violation
```

Forbidden recommendations:

```text
candidate_for_p1_strategy
proceed_to_strategy_backtest
validated_model
selected_lgbm_model
selected_score_bucket
selected_threshold
selected_trade_rule
freeze_strategy
electronics_alpha_validated
electronics_primitive_validated_for_trading
broader_cohort_replaces_supply_chain_definition
```

Important boundary:

```text
proceed_to_explore10d_electronics_manual_primitive_formula_review_requirement
```

means only:

```text
there is enough post-selected exploratory primitive-quality evidence to write a manual review requirement.
```

It does not mean:

```text
primitive is valid for P1
primitive is tradable
strategy can be backtested
```

---

## 14. Required Outputs

All reports must be written to:

```text
Explore10/outputs/explore10c/reports/
```

All row-level parquet caches must be written to:

```text
Explore10/outputs/explore10c/cache/
```

Parquet caches must be gitignored.

### 14.1 Required report artifacts

```text
explore10c_run_manifest.json
explore10c_preflight_reference_artifact_audit.csv
explore10c_scope_selection_lineage_audit.csv
explore10c_explore10b_width_inheritance_gate.csv
explore10c_data_discipline_audit.csv
explore10c_feature_bank_v1_profile_audit.csv
explore10c_feature_bank_v1_to_v2_hygiene_audit.csv
explore10c_feature_bank_v2_dictionary.csv
explore10c_feature_bank_v2_feature_drop_log.csv
explore10c_feature_bank_v2_duplicate_cluster_audit.csv
explore10c_feature_bank_v2_missingness_by_fold.csv
explore10c_feature_bank_v2_missingness_by_instrument.csv
explore10c_feature_bank_v2_family_coverage_audit.csv
explore10c_probe_contract_audit.csv
explore10c_lgbm_fixed_probe_audit.csv
explore10c_trainability_counterfactual_audit.csv
explore10c_path_candidate_freeze_audit.csv
explore10c_lgbm_raw_path_dump.csv
explore10c_path_pattern_canonicalization.csv
explore10c_path_threshold_quantile_audit.csv
explore10c_path_pattern_fold_presence.csv
explore10c_atomic_primitive_seed_table.csv
explore10c_primitive_token_coverage_audit.csv
explore10c_candidate_scope_weighted_baseline.csv
explore10c_baseline_sparsity_audit.csv
explore10c_primitive_real_metric_audit.csv
explore10c_label_permutation_null_audit.csv
explore10c_instrument_year_block_null_audit.csv
explore10c_path_structure_null_audit.csv
explore10c_feature_family_dropout_audit.csv
explore10c_candidate_level_null_aggregation.csv
explore10c_candidate_family_fdr_audit.csv
explore10c_placebo_guardrail_audit.csv
explore10c_concentration_audit.csv
explore10c_slice_stability_audit.csv
explore10c_manualizability_audit.csv
explore10c_metric_nonselection_audit.csv
explore10c_threshold_nonselection_audit.csv
explore10c_model_nonselection_audit.csv
explore10c_score_bucket_nonselection_audit.csv
explore10c_fold_2024_nonselection_audit.csv
explore10c_forbidden_recommendation_self_check.csv
explore10c_cache_tracking_audit.csv
explore10c_required_artifact_authority_audit.csv
explore10c_recommendation_gate.csv
explore10c_report.md
```

### 14.2 Required cache artifacts

```text
explore10c_electronics_v1_reference_train_eval_panel.parquet
explore10c_electronics_v2_hygiene_train_eval_panel.parquet
explore10c_electronics_v2_feature_availability_panel.parquet
explore10c_electronics_fixed_probe_prediction_panel.parquet
explore10c_electronics_path_support_panel.parquet
explore10c_electronics_primitive_seed_oof_panel.parquet
explore10c_electronics_null_placebo_panel.parquet
```

No row-level CSV export is allowed by default.

### 14.3 Manifest minimum keys

`explore10c_run_manifest.json` must include:

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
width_inheritance_pass
scope_selection_lineage_pass
data_discipline_pass
feature_bank_v2_hygiene_pass
quality_seed_count
candidate_family_fdr_pass
recommendation
recommendation_allowed
forbidden_output_violation_count
pass
```

Each artifact item must include:

```text
artifact_name
artifact_path
exists
file_size_bytes
sha256
row_count
column_count
artifact_authority
tracked_by_git
git_check_ignore_pass
```

---

## 15. Report Requirements

`explore10c_report.md` must be in Chinese and must answer:

```text
1. Explore10C 是否正确继承了 Explore10B 的电子样本宽度 pass？
2. 电子 scope 的后验选择 lineage 是否被记录，并进入 selection-family null 解释？
3. Explore10C 新生成的 v2/probe/path/primitive/null row surfaces 是否通过 data discipline？
4. 10A 中未执行的 feature bank v2 是否已在电子 scope 下完成？
5. v2 相比 v1 是否降低 missingness / duplicate cluster，并保留 feature-family coverage？
6. v2 是否通过 feature-asof / formula-token / unmapped-token gate，且没有使用 validation rows / labels / OOF metrics？
7. 固定 probe 是否没有 hyperparameter search、early stopping、metric selection？
8. path candidates 是否在任何 OOF/null/placebo metric 前冻结？
9. path thresholds 是否全部转为 train-fold quantile buckets？
10. primitive formula 是否没有 raw numeric threshold、leaf id、score bucket 或 model id？
11. 有多少电子 launch primitive seeds 通过 OOF support、baseline、null、FDR 和 placebo？
12. failure secondary 是否 domination primary？若是，如何阻断 recommendation？
13. 是否存在 instrument / instrument-year concentration 或 slice instability？
14. 哪些 seed 只适合 manual review，不能进入 P1？
15. 是否触发 fold_2024、metric、threshold、model、score-bucket selection violation？
16. 是否可以进入 Explore10D manual primitive formula review requirement？
17. 本阶段没有回答哪些策略或交易问题？
```

The report must include explicit boundary statements:

```text
Explore10C 可以证明电子 path / primitive seed 是否有探索性质量证据；
Explore10C 不能证明电子 primitive 可交易。
```

```text
Explore10C 的成功 recommendation 只能进入 Explore10D manual formula review；
不能进入 P1、不能回测、不能形成 score bucket 或交易规则。
```

---

## 16. Config Sketch

```yaml
phase: explore10c
title: electronics_path_quality_and_primitive_quality_audit
output_root: Explore10/outputs/explore10c
requirement_path: Explore10/requirement_explore10c.md

scope:
  primary:
    industry: 电子
    task: launch_winner
    role: primary_path_quality_audit
  secondary:
    industry: 电子
    task: failure_reject
    role: secondary_failure_diagnostic
  reference_only:
    industry: 汽车
    role: failed_width_reference_only

folds:
  core_oof: [fold_2021, fold_2022, fold_2023]
  launch_expected_event_history_boundary: [fold_2020]
  robustness_only: [fold_2024]
  fold_2024_used_for_support: false

paths:
  explore10b_manifest: Explore10/outputs/explore10b/reports/explore10b_run_manifest.json
  explore10b_width_gate: Explore10/outputs/explore10b/reports/explore10b_electronics_sample_width_gate.csv
  explore10b_recommendation_gate: Explore10/outputs/explore10b/reports/explore10b_recommendation_gate.csv
  explore10_train_eval_panel: Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
  explore10_launch_event_panel: Explore10/outputs/explore10/cache/explore10_atomic_launch_event_panel.parquet
  explore10_failure_decision_panel: Explore10/outputs/explore10/cache/explore10_atomic_failure_decision_panel.parquet
  explore10_model_dump: Explore10/outputs/explore10/cache/explore10_lgbm_model_dump.parquet
  explore10_full_path_candidate_panel: Explore10/outputs/explore10/cache/explore10_full_path_candidate_panel.parquet
  feature_bank_v1_config: Explore10/configs/atomic_feature_bank_v1.yaml
  explore10_feature_dictionary: Explore10/outputs/explore10/reports/explore10_atomic_feature_dictionary.csv
  explore10_feature_bank_preflight: Explore10/outputs/explore10/reports/explore10_feature_bank_preflight_audit.csv
  explore10_feature_asof_leakage: Explore10/outputs/explore10/reports/explore10_feature_asof_leakage_audit.csv
  explore10_observed_reference_overlap: Explore10/outputs/explore10/reports/explore10_observed_reference_overlap_audit.csv
  explore10_walk_forward_purge: Explore10/outputs/explore10/reports/explore10_walk_forward_purge_audit.csv

scope_selection_lineage:
  selected_after_observing_trainability: true
  selected_after_observing_candidate_count: true
  selected_after_automotive_width_failure: true
  selection_family_null_required: true

data_discipline:
  required_row_surfaces:
    - v1_reference_train_eval_panel
    - v2_hygiene_train_eval_panel
    - v2_feature_availability_panel
    - fixed_probe_prediction_panel
    - path_support_panel
    - primitive_seed_oof_panel
    - null_placebo_panel
  max_row_identity_duplicate_count: 0
  max_row_identity_mismatch_count: 0
  max_feature_asof_leakage_violation_count: 0
  max_observed_reference_overlap_count: 0
  max_walk_forward_purge_violation_count: 0

feature_bank_hygiene:
  source_version: alpha158_like_v1
  target_version: alpha158_like_v2_hygiene
  selection_scope: fold_local_train_scope_unsupervised_only
  recommendation_dictionary_rule: intersection_of_core_fold_v2_features
  labels_allowed: false
  validation_metrics_allowed: false
  validation_rows_allowed: false
  fold_2024_allowed: false
  duplicate_representative_rule:
    - lower_train_scope_missing_weight_share
    - higher_fold_availability_count
    - lower_formula_complexity
    - lower_feature_family_overrepresentation_penalty
    - simpler_asof_rule
    - lexicographic_feature_name

probe_contract:
  fixed_lgbm_only: true
  hyperparameter_search_allowed: false
  early_stopping_allowed: false
  metric_model_selection_allowed: false
  feature_bank_versions: [v1_reference, v2_hygiene]
  recommendation_eligible_feature_bank_version: v2_hygiene

candidate_extraction:
  max_path_depth: 4
  min_train_path_support_count: 30
  min_train_path_weighted_support: 30.0
  max_paths_per_fold_task: 40
  max_paths_total: 120
  max_paths_per_feature_family: 20
  path_dedup_identity: normalized_feature_direction_quantile_sequence
  path_sort_key: train_weighted_support_desc_then_path_depth_asc_then_feature_family_diversity_desc_then_path_pattern_id_asc

candidate_freeze:
  freeze_before_oof_metrics: true
  freeze_before_null_metrics: true
  freeze_before_placebo_metrics: true
  freeze_before_manual_formula_edits: true
  raw_numeric_threshold_in_formula_allowed: false
  threshold_representation: train_fold_quantile_bucket

threshold_canonicalization:
  quantile_bucket_count: 20
  quantile_source_rows: source_fold_training_rows_only
  tie_policy: average_rank_then_lower_bucket
  missing_value_policy: explicit_missing_branch_token
  out_of_range_policy: clamp_to_edge_bucket
  bucket_label_format: q_lower_pct_upper_pct

thresholds:
  min_distinct_instruments_original: 20
  min_quality_seed_count: 1
  min_core_fold_presence_count: 2
  min_oof_support_count: 20
  min_oof_weighted_support: 20.0
  max_feature_missing_weight_share: 0.20
  max_feature_missing_row_rate: 0.20
  max_duplicate_feature_cluster_count: 25
  duplicate_corr_abs_threshold: 0.995
  duplicate_min_pairwise_non_null_count: 100
  max_constant_feature_rate: 0.02
  max_top_value_share_for_nonconstant: 0.995
  max_feature_family_share: 0.35
  min_feature_family_coverage_after_hygiene: 0.80
  min_feature_count_after_hygiene: 60
  min_oof_lift_vs_baseline: 1.05
  min_real_minus_null_p95: 0.0
  max_empirical_p_value: 0.05
  max_fdr_q: 0.10
  max_top_instrument_weight_share: 0.25
  max_top_instrument_year_weight_share: 0.20
  max_instrument_year_hhi: 0.15

nulls:
  families:
    - label_permutation_null
    - instrument_year_block_null
    - path_structure_null
    - feature_family_dropout_null
  min_iterations: 100
  pass_rule: real_metric_above_null_p95_with_fdr_and_not_placebo_dominated

allowed_recommendations:
  - proceed_to_explore10d_electronics_manual_primitive_formula_review_requirement
  - continue_explore10c_path_quality_audit
  - stop_due_to_feature_bank_v2_hygiene_failure
  - stop_due_to_no_electronics_path_quality_evidence
  - stop_due_to_null_or_placebo_collapse
  - stop_due_to_concentration_or_slice_instability
  - stop_due_to_data_discipline_violation

forbidden_outputs:
  - candidate_for_p1_strategy
  - proceed_to_strategy_backtest
  - validated_model
  - selected_lgbm_model
  - selected_score_bucket
  - selected_threshold
  - selected_trade_rule
  - freeze_strategy
  - electronics_alpha_validated
  - electronics_primitive_validated_for_trading
```

---

## 17. Expected Commands

Future implementation should add commands without breaking existing Explore10 / 10A / 10B commands:

```bash
uv run python Explore10/scripts/run_explore10.py profile-explore10c --config Explore10/configs/electronics_path_quality_explore10c.yaml
uv run python Explore10/scripts/run_explore10.py report-explore10c --config Explore10/configs/electronics_path_quality_explore10c.yaml
```

Required new config:

```text
Explore10/configs/electronics_path_quality_explore10c.yaml
```

Required `.gitignore` coverage:

```text
Explore10/outputs/explore10c/cache/
```

---

## 18. Acceptance Checklist

```text
[ ] 10B width inheritance gate passes before any v2 or path work
[ ] post-selection lineage is recorded and carried into selection-family null interpretation
[ ] Explore10C row surfaces pass feature-asof, observed-reference, purge, and row-identity discipline
[ ] 10A status-only v2 artifacts are not reused as v2 proof
[ ] electronic feature bank v2 is constructed from fold-local train-scope unsupervised evidence only
[ ] v2 construction uses zero validation rows, labels, OOF metrics, fold_2024 rows, or feature importance
[ ] v2 duplicate representative rule is deterministic
[ ] fold_2024 is robustness-only and never support
[ ] fixed LGBM probe has no hyperparameter search and no early stopping
[ ] path extraction budget is loaded from config before model fitting and is not changed after metrics
[ ] candidate freeze happens before OOF/null/placebo metrics
[ ] raw numeric thresholds do not enter primitive formulas
[ ] threshold quantile buckets have deterministic bucket count, tie policy, missing branch, and source rows
[ ] primitive formulas contain no leaf id, tree id, model score, or score bucket
[ ] null, FDR, and placebo families are computed after candidate freeze over all frozen seeds
[ ] concentration and slice stability gates are enforced
[ ] manualizability audit separates manual-review seed from trade rule
[ ] no selected model, selected score bucket, strategy backtest, P1 candidate, or freeze strategy
[ ] all required report artifacts exist
[ ] all required cache parquet artifacts exist and are gitignored
[ ] Chinese report answers all Section 15 questions
```

---

## 19. Final Boundary Statement

Explore10C is not a strategy phase.

Explore10C may conclude:

```text
电子行业有足够的探索性 path / primitive seed 质量证据，
可以进入 Explore10D manual primitive formula review requirement。
```

Explore10C may also conclude:

```text
电子虽然解决了样本宽度，但 path / primitive quality 不足，
应停止或继续修 feature bank / path audit。
```

Explore10C must not conclude:

```text
电子 primitive 已验证有效。
电子可以进入 P1。
电子可以回测。
电子可以形成 score bucket。
电子可以形成交易规则。
电子行业标签可以替代真实上下游产业链定义。
```

The strongest valid success meaning is:

```text
post_selected_electronics_manual_review_seed_allowed = true
```
