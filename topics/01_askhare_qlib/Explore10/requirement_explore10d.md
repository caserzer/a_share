# Explore10D 需求说明：电子行业 Launch Risk-Filter Primitive 复核审计

> 文件名：`requirement_explore10d.md`
> 阶段：`Explore10D` / `P0.10D`
> 标题：Electronics Launch Risk-Filter Primitive Matched-Null and Family-Ablation Audit
> 状态：implementation-ready requirement
> 生成日期：2026-05-07
> 重要说明：Explore10D 继续主线 `launch_winner`，但不再把当前 top launch paths 当作直接 winner trigger；本阶段只验证它们是否更合理地解释为 `avoid-overheated / launch-risk-filter primitive`。Explore10D 不做策略回测，不输出 P1 candidate，不选择 score bucket，不产生交易规则。

---

## 0. 一句话结论

Explore10C 已证明：

```text
电子 broad-industry scope 解决了 denominator；
feature bank v2 解决了 hygiene；
fixed probe 解决了 trainability；
但 primitive-quality evidence 没有解决 launch-winner validity。
```

Explore10C 的阻断点是：

```text
launch side 14 个 seed 全部有 OOF support / fold presence / manualizability，
但 0 个 launch seed 通过 null/FDR family；
failure secondary stronger，触发 placebo_or_secondary_dominates_primary = true。
```

Explore10D 只继续主线 launch，执行三件事：

```text
A. 将 launch primitive 目标从 direct winner trigger 收紧为 avoid-overheated / launch-risk-filter primitive；
C. 对 Explore10C top launch seeds 做 stricter support-matched null；
D. 对 launch top seeds 做 family-level ablation。
```

Explore10D 的核心问题是：

```text
Explore10C 的 launch top seeds 是否只是 weak winner trigger，
还是可以被重新解释为可复核的 launch-risk-filter primitive？
```

---

## 1. 背景与当前证据

### 1.1 Explore10C 已通过的部分

Explore10C 已经排除了以下实现层问题：

```text
width_inheritance_pass = true
scope_selection_lineage_pass = true
data_discipline_pass = true
feature_bank_v2_hygiene_pass = true
v2_probe_trainability_pass = true
candidate_freeze_pass = true
primitive_token_coverage_pass = true
fold_2024_support_usage_count = 0
metric_selection_violation_count = 0
threshold_selection_violation_count = 0
model_selection_violation_count = 0
score_bucket_selection_violation_count = 0
required_artifact_authority_pass = true
cache_tracking_pass = true
```

因此 Explore10D 不应重新证明这些工程事实，只能继承并审计其输入 authority。

### 1.2 Explore10C 的 launch evidence

Explore10C 的 launch side：

```text
launch frozen primitive seeds = 14
launch seeds with OOF support / fold presence = 14
launch seeds with manualizability pass = 14
launch seeds passing all null/FDR families = 0
launch max OOF lift = 1.283
launch median OOF lift = 1.007
```

top launch formulas 主要集中在：

```text
ATR / volatility / range / money coherence / volume-price divergence
```

这更像：

```text
avoid overheated launch
avoid excessive volatility
avoid unstable money-price state
```

而不是：

```text
direct winner trigger
```

### 1.3 Explore10C 的 failure warning

Explore10C 的 failure side：

```text
failure frozen primitive seeds = 106
failure OOF quality pass seeds = 95
failure FDR pass rows = 24
failure stronger than primary launch side
placebo_or_secondary_dominates_primary = true
```

Required interpretation:

```text
failure stronger 不能支持 launch primary；
它只能说明当前 path extraction 更容易找到 bad-launch / failure-risk structure。
```

Explore10D 不把 failure side 扩展成主任务。Failure side 只作为 guardrail/reference，不能产生 launch recommendation。

---

## 2. 阶段定位

Explore10D 是：

```text
launch-risk-filter primitive audit
```

Explore10D 不是：

```text
manual formula review phase
P1 candidate selection
strategy backtest
score bucket selection
new path search
failure/reject standalone requirement
```

Explore10D 只回答 7 个问题：

```text
1. Explore10C 的 engineering gates 是否可继承？
2. 10C top launch seeds 是否可被预注册地重标为 risk-filter primitive，而不是 post-hoc winner trigger？
3. top launch seeds 在 support-matched null 下是否仍有非随机 lift？
4. top launch seeds 在 same-family / same-token / same-fold-presence null 下是否仍有非随机 lift？
5. volatility/range/money-coherence family 是否是 launch top seed 的必要成分？
6. 去掉或只保留这些 family 后，launch evidence 是增强、消失还是不变？
7. 是否值得进入下一份人工公式复核 requirement？
```

Explore10D 不回答：

```text
电子 launch primitive 是否可交易；
哪个 score bucket 可交易；
是否进入 P1；
是否应该回测；
failure side 是否可以作为独立 bad-launch strategy；
电子 broad industry 是否可替代真实产业链 cohort。
```

---

## 3. Scope

### 3.1 Primary scope

```text
target_industry = 电子
primary_task = launch_winner
scope_role = primary_launch_risk_filter_audit
```

Primary scope 只使用 Explore10C 已冻结的 launch seeds。

### 3.2 Seed universe

Allowed seed universe:

```text
source_phase = Explore10C
source_artifact = explore10c_atomic_primitive_seed_table.csv
task = launch_winner
feature_bank_version = v2_hygiene
eligible_for_quality_audit = true
fold_2024_support_used = false
raw_numeric_threshold_in_formula = false
leaf_id_in_formula = false
score_bucket_in_formula = false
```

Required seed count:

```text
expected_launch_seed_count = 14
```

Explore10D may rank seeds for diagnostic display only by fixed predeclared fields:

```text
oof_lift_vs_scope_baseline
oof_support_count
core_fold_presence_count
formula_family_group
```

No new seed may be created in Explore10D.

### 3.3 Secondary guardrail scope

```text
source_phase = Explore10C
secondary_task = failure_reject
role = inherited_placebo_guardrail_only
```

Failure side may be used only to report:

```text
placebo_or_secondary_dominates_primary
failure side stronger than launch side
```

Failure side may not:

```text
select launch seeds
define launch formula
set launch thresholds
become primary recommendation
trigger Explore10D success
```

### 3.4 Fold roles

```text
core_oof = fold_2021, fold_2022, fold_2023
robustness_only = fold_2024
```

Hard rule:

```text
fold_2024 不得用于 seed selection、null matching、family ablation pass、
threshold selection、recommendation support。
```

---

## 4. Hard Phase Gates

Explore10D must run gates in this order:

```text
Gate 0: Explore10C inheritance and artifact authority gate
Gate 1: launch seed freeze and relabel gate
Gate 2: support-matched null gate
Gate 3: same-family / same-token / same-fold-presence null gate
Gate 4: family-level ablation gate
Gate 5: concentration / slice / manualizability carry-forward gate
Gate 6: recommendation gate
```

If any upstream gate fails, downstream artifacts must still exist as status-only files with:

```text
execution_status
not_started_reason
upstream_gate
upstream_gate_pass
```

---

## 5. Gate 0: Explore10C Inheritance

Explore10D may start only if Explore10C proves:

```text
width_inheritance_pass = true
scope_selection_lineage_pass = true
data_discipline_pass = true
feature_bank_v2_hygiene_pass = true
v2_probe_trainability_pass = true
candidate_freeze_pass = true
required_artifact_authority_pass = true
cache_tracking_pass = true
fold_2024_support_usage_count = 0
metric_selection_violation_count = 0
threshold_selection_violation_count = 0
model_selection_violation_count = 0
score_bucket_selection_violation_count = 0
```

Required artifact:

```text
explore10d_explore10c_inheritance_gate.csv
```

Minimum fields:

```text
source_artifact
source_hash
source_recommendation
width_inheritance_pass
scope_selection_lineage_pass
data_discipline_pass
feature_bank_v2_hygiene_pass
v2_probe_trainability_pass
candidate_freeze_pass
required_artifact_authority_pass
cache_tracking_pass
fold_2024_support_usage_count
metric_selection_violation_count
threshold_selection_violation_count
model_selection_violation_count
score_bucket_selection_violation_count
inheritance_pass
blocked_reason
pass
```

Important:

```text
Explore10C recommendation = continue_explore10c_path_quality_audit
```

is acceptable for Explore10D, because Explore10D is the continuation audit. It is not a success inheritance.

---

## 6. Gate 1: Launch Seed Freeze and Relabel

### 6.1 Freeze rule

Explore10D must freeze the input seed universe before any new null or ablation metric is computed.

Required artifact:

```text
explore10d_launch_seed_freeze_audit.csv
```

Minimum fields:

```text
freeze_timestamp
source_seed_artifact
source_seed_artifact_hash
source_metric_artifact
source_metric_artifact_hash
seed_selection_rule
seed_selection_rule_hash
input_launch_seed_count
frozen_launch_seed_count
new_seed_created
seed_dropped_before_freeze
seed_dropped_reason
oof_metric_available_before_freeze
oof_metric_used_for_display_only
null_metric_available_before_freeze
null_metric_read_before_freeze
family_ablation_metric_available_before_freeze
family_ablation_metric_read_before_freeze
freeze_pass
pass
```

Hard rules:

```text
new_seed_created = false
seed_dropped_before_freeze = false
null_metric_read_before_freeze = false
family_ablation_metric_read_before_freeze = false
```

### 6.2 Relabel rule

Explore10D must relabel current launch seeds from:

```text
direct_launch_winner_trigger
```

to:

```text
launch_risk_filter_candidate
```

only if the formula contains at least one of:

```text
volatility_range token
volume_money token
money_price_coherence token
market_volatility_regime token
ATR/range/amplitude token
```

This relabel is interpretive, not performance-based.

Required artifact:

```text
explore10d_launch_seed_relabel_audit.csv
```

Minimum fields:

```text
primitive_seed_id
source_formula_text_resolved
source_oof_lift_vs_scope_baseline
source_best_fdr_q
source_null_pass
original_interpretation
explore10d_interpretation
risk_filter_token_count
winner_trigger_token_count
formula_family_group
relabel_reason
relabel_used_metric
relabel_pass
pass
```

Hard rule:

```text
relabel_used_metric = false
```

OOF lift may be displayed, but it cannot decide whether a seed is relabeled.

### 6.3 Risk-filter metric contract

Explore10D does not create a new label and does not redefine `launch_winner`.
The risk-filter interpretation is tested through a pre-registered metric
contract:

```text
primary_label = launch_winner
primary_real_metric_name = oof_lift_vs_scope_weighted_baseline
risk_filter_interpretation_metric = launch_risk_filter_retained_lift
```

Definitions:

```text
included_rows = electronics launch OOF rows satisfying the frozen formula
scope_rows = all eligible electronics launch OOF rows in fold_2021/fold_2022/fold_2023
included_positive_rate = weighted_mean(primary_label, included_rows, final_sample_weight)
scope_positive_rate = weighted_mean(primary_label, scope_rows, final_sample_weight)
oof_lift_vs_scope_weighted_baseline = included_positive_rate / scope_positive_rate
```

Diagnostic-only risk-filter context:

```text
excluded_rows = scope_rows not satisfying the frozen formula
excluded_positive_rate = weighted_mean(primary_label, excluded_rows, final_sample_weight)
included_minus_excluded_positive_rate = included_positive_rate - excluded_positive_rate
excluded_state_failure_rate = weighted_mean(failure_diagnostic_label, excluded_rows, final_sample_weight)
included_state_failure_rate = weighted_mean(failure_diagnostic_label, included_rows, final_sample_weight)
failure_rate_reduction_diagnostic = excluded_state_failure_rate - included_state_failure_rate
```

Hard interpretation rule:

```text
success evidence = primary_real_metric passing matched-null/FDR and ablation gates
failure_rate_reduction_diagnostic may be reported but cannot unlock success
```

Required artifact:

```text
explore10d_launch_risk_filter_metric_contract.csv
```

Minimum fields:

```text
primary_label
primary_real_metric_name
risk_filter_interpretation_metric
weight_column
included_rows_definition
scope_rows_definition
included_positive_rate_formula
scope_positive_rate_formula
real_metric_formula_text
failure_diagnostic_label_available
failure_diagnostic_used_for_success
metric_contract_pass
pass
```

---

## 7. Gate 2: Support-Matched Null

### 7.1 Purpose

Explore10C showed that launch top seeds do not survive the broad post-selected null/FDR family. Explore10D must test whether this is because the null was too broad or because the seed has no real structure.

Support-matched nulls must match each frozen seed on:

```text
task = launch_winner
target_industry = 电子
fold_id
OOF support bucket
weighted support bucket
core_fold_presence_count
instrument_count_bucket
instrument_year_count_bucket
token_count
feature_family_count
```

### 7.2 Matching mechanics

Support buckets are fixed before any null metric is computed:

```text
support_count_bucket_edges = [0, 50, 100, 250, 500, 1000, 2000, inf]
weighted_support_bucket_edges = [0, 50, 100, 250, 500, 1000, 2000, inf]
instrument_count_bucket_edges = [0, 3, 5, 10, 20, 50, 100, inf]
instrument_year_count_bucket_edges = [0, 3, 5, 10, 20, 50, 100, inf]
```

Matching rules:

```text
task and target_industry must match exactly
fold_id must match exactly
token_count must match exactly for same-token nulls
core_fold_presence_count must match exactly for same-fold-presence nulls
feature_family_count may use nearest bucket only if exact match is empty
support / weighted_support / instrument / instrument_year buckets may use nearest bucket only within max_nearest_bucket_distance = 1
```

Sampling rules:

```text
sampling_with_replacement = true
random_seed = hash(config.nulls.random_seed, primitive_seed_id, null_family, null_iteration_id)
empirical_p_value = (1 + count(null_metric >= real_metric)) / (1 + null_iteration_count)
p_value_side = one_sided_upper_tail
```

Failure rules:

```text
if no exact_or_nearest_allowed match exists:
  support_match_status = no_match_blocked
  null_metric = null
  empirical_p_value = 1.0
  null_pass = false
  pass = false
```

### 7.3 Required null families

Required support-matched null families:

```text
support_matched_random_row_null
support_matched_same_token_count_null
support_matched_same_fold_presence_null
support_matched_same_instrument_year_null
```

Each null family must include all frozen launch seeds, including weak and zero-pass seeds.

Required artifact:

```text
explore10d_support_matched_null_audit.csv
```

Minimum fields:

```text
primitive_seed_id
null_family
null_iteration_id
fold_id
matched_support_bucket
matched_weighted_support_bucket
matched_instrument_count_bucket
matched_instrument_year_count_bucket
matched_token_count
matched_feature_family_count
real_metric
null_metric
real_minus_null_p95
empirical_p_value
null_iteration_count
support_match_status
support_match_gap
fold_2024_used
null_pass
pass
```

Pass condition per seed/family:

```text
real_metric = oof_lift_vs_scope_weighted_baseline
real_metric >= thresholds.min_risk_filter_oof_lift_vs_baseline
real_minus_null_p95 >= thresholds.min_real_minus_support_matched_null_p95
empirical_p_value <= thresholds.max_support_matched_empirical_p_value
null_iteration_count >= config.nulls.support_matched_iterations
support_match_status = exact_or_nearest_allowed
fold_2024_used = false
```

Required summary artifact:

```text
explore10d_support_matched_null_summary.csv
```

Minimum fields:

```text
primitive_seed_id
null_family
core_fold_count
real_metric
null_mean
null_p95
real_minus_null_p95
empirical_p_value
support_match_status
included_in_fdr_family
null_pass
pass
```

---

## 8. Gate 3: Same-Family / Same-Token / Same-Fold-Presence Null

### 8.1 Purpose

Explore10D must test whether the top launch seed signal is stronger than other formulas with the same broad structure.

### 8.2 Structural candidate pool

Structural nulls may only draw from Explore10C artifacts that were frozen before
Explore10C primitive-quality metrics:

```text
primary_pool_artifact = explore10c_path_pattern_canonicalization.csv
fold_presence_artifact = explore10c_path_pattern_fold_presence.csv
seed_oof_panel_artifact = explore10c_electronics_primitive_seed_oof_panel.parquet
```

Eligible structural null candidates:

```text
task = launch_winner
target_industry = 电子
feature_bank_version = v2_hygiene
fold_2024_support_used = false
raw_numeric_threshold_in_formula = false
leaf_id_in_formula = false
score_bucket_in_formula = false
metric_selected = false
path_frozen_before_oof_null = true
```

Forbidden candidate sources:

```text
new LGBM paths
fold_2024-only paths
validation-selected formulas
failure_reject formulas
manual edits after Explore10C freeze
```

Required null families:

```text
same_feature_family_set_null
same_token_count_null
same_fold_presence_null
same_quantile_direction_mix_null
```

Required artifact:

```text
explore10d_structural_matched_null_audit.csv
```

Minimum fields:

```text
primitive_seed_id
null_family
null_iteration_id
formula_family_group
feature_family_set
token_count
fold_presence_count
quantile_direction_mix
real_metric
null_metric
null_mean
null_p95
real_minus_null_p95
empirical_p_value
null_iteration_count
structural_match_status
candidate_dropped_before_null
candidate_dropped_before_null_reason
null_pass
pass
```

Pass condition per seed/family:

```text
real_metric = oof_lift_vs_scope_weighted_baseline
real_minus_null_p95 >= thresholds.min_real_minus_structural_matched_null_p95
empirical_p_value <= thresholds.max_structural_matched_empirical_p_value
null_iteration_count >= config.nulls.structural_matched_iterations
structural_match_status = exact_or_nearest_allowed
candidate_dropped_before_null = false
```

All frozen seeds must be included in FDR correction.

Required artifact:

```text
explore10d_matched_null_fdr_audit.csv
```

Minimum fields:

```text
selection_family_id
primitive_seed_id
null_family
frozen_seed_count_in_family
real_metric
empirical_p_value
bh_rank
bh_q_value
included_in_fdr_family
candidate_dropped_before_fdr
fdr_pass
pass
```

FDR rule:

```text
selection_family_id = post_selected_electronics_explore10d_launch_risk_filter
FDR method = Benjamini-Hochberg
FDR family includes every frozen launch seed and every required matched-null family
candidate_dropped_before_fdr = false for all frozen seeds
fdr_pass = bh_q_value <= thresholds.max_fdr_q
```

---

## 9. Gate 4: Family-Level Ablation

### 9.1 Purpose

Explore10C top launch formulas concentrate in volatility/range/money-coherence filters. Explore10D must test whether these families are necessary and whether the apparent signal disappears when they are removed.

Required ablation suites:

```text
remove_volatility_range_family
remove_volume_money_family
remove_cross_section_rank_family
remove_industry_market_context_family
keep_only_volatility_range_family
keep_only_volume_money_family
keep_only_volatility_range_plus_volume_money
keep_only_non_risk_filter_families
```

### 9.2 Rules

Ablation may not create new formula thresholds from validation data.

Allowed:

```text
remove existing tokens by family
keep existing tokens by family
recompute OOF support and lift using existing train-fold quantile buckets
compare against support-matched baseline
```

Forbidden:

```text
new LGBM training
new path extraction
new raw split threshold
validation-tuned threshold
score bucket
strategy return
fold_2024 support
```

Invalid ablation handling:

```text
if ablated_token_count < thresholds.min_ablated_token_count:
  ablation_status = invalid_empty_or_too_short_formula
  ablation_pass = false

if ablated_oof_support_count < thresholds.min_ablated_oof_support_count:
  ablation_status = invalid_insufficient_support
  ablation_pass = false

if support_retention_rate > thresholds.max_ablation_support_expansion_rate:
  ablation_status = invalid_support_explosion
  ablation_pass = false

invalid ablation rows must still be emitted
invalid ablation rows cannot support risk_filter_interpretation_supported
```

Required artifact:

```text
explore10d_family_ablation_audit.csv
```

Minimum fields:

```text
primitive_seed_id
ablation_suite
ablation_rule
removed_family_set
kept_family_set
original_formula_text
ablated_formula_text
original_token_count
ablated_token_count
original_oof_support_count
ablated_oof_support_count
original_oof_lift
ablated_oof_lift
delta_lift
support_retention_rate
direction_preserved
ablation_status
ablation_interpretation
fold_2024_used
ablation_pass
pass
```

Interpretation rules:

```text
if remove_volatility_range_family collapses lift and keep_only_volatility_range_family preserves lift:
  volatility_range_is_necessary = true

if remove_volume_money_family collapses lift and keep_only_volume_money_family preserves lift:
  volume_money_is_necessary = true

if keep_only_non_risk_filter_families preserves lift:
  risk_filter_interpretation_weakens = true

if all keep_only suites collapse:
  formula_requires_cross_family_interaction = true
```

Machine-readable support rule:

```text
risk_filter_interpretation_supported = true only if:
  matched_null_fdr_pass = true
  and risk_filter_interpretation_weakens = false
  and at least one of:
    volatility_range_is_necessary = true
    volume_money_is_necessary = true
    industry_market_context_is_necessary = true
    formula_requires_cross_family_interaction = true
```

Required summary artifact:

```text
explore10d_family_ablation_summary.csv
```

Minimum fields:

```text
primitive_seed_id
formula_family_group
volatility_range_is_necessary
volume_money_is_necessary
cross_section_rank_is_necessary
industry_market_context_is_necessary
formula_requires_cross_family_interaction
risk_filter_interpretation_supported
risk_filter_interpretation_weakens
matched_null_fdr_pass
valid_ablation_suite_count
ablation_summary_pass
pass
```

---

## 10. Gate 5: Carry-Forward Sanity

Explore10D must carry forward Explore10C sanity gates:

```text
token coverage
concentration
slice stability
manualizability
forbidden recommendation self-check
cache tracking
artifact authority
```

Required artifacts:

```text
explore10d_token_coverage_carry_forward_audit.csv
explore10d_concentration_carry_forward_audit.csv
explore10d_slice_stability_carry_forward_audit.csv
explore10d_manualizability_carry_forward_audit.csv
explore10d_metric_nonselection_audit.csv
explore10d_threshold_nonselection_audit.csv
explore10d_model_nonselection_audit.csv
explore10d_score_bucket_nonselection_audit.csv
explore10d_fold_2024_nonselection_audit.csv
```

Carry-forward does not mean automatic pass. The artifact must record source values and whether Explore10D still allows the seed to support recommendation.

### 10.2 Governance artifact schemas

Required preflight artifact:

```text
explore10d_preflight_reference_artifact_audit.csv
```

Minimum fields:

```text
artifact_name
artifact_path
artifact_role
exists
content_hash
required_for_gate
source_phase
read_before_freeze_allowed
preflight_pass
pass
```

Required forbidden-recommendation artifact:

```text
explore10d_forbidden_recommendation_self_check.csv
```

Minimum fields:

```text
forbidden_token
searched_artifact
occurrence_count
allowed_context
violation_count
pass
```

Required cache tracking artifact:

```text
explore10d_cache_tracking_audit.csv
```

Minimum fields:

```text
cache_artifact
cache_path
exists
file_format
row_level_cache
csv_row_level_export
gitignore_rule_present
content_hash
cache_tracking_pass
pass
```

Required artifact authority artifact:

```text
explore10d_required_artifact_authority_audit.csv
```

Minimum fields:

```text
required_artifact
artifact_type
required_by_section
exists
has_required_columns
row_count
status_only_allowed
status_only_emitted
authority_pass
pass
```

---

## 11. Recommendation Gate

Explore10D can recommend a manual formula review requirement only if:

```text
1. Explore10C inheritance pass = true
2. frozen_launch_seed_count = 14
3. no new seed was created
4. relabel_used_metric = false
5. at least thresholds.min_risk_filter_seed_count seeds pass support-matched null after FDR
6. at least thresholds.min_risk_filter_seed_count seeds pass structural matched null after FDR
7. at least thresholds.min_risk_filter_seed_count seeds have risk_filter_interpretation_supported = true
8. failure secondary does not become primary evidence
9. concentration carry-forward pass = true
10. slice stability carry-forward pass = true
11. manualizability carry-forward pass = true
12. fold_2024_support_usage_count = 0
13. metric / threshold / model / score-bucket selection violation count = 0
14. required artifact authority pass = true
15. cache tracking pass = true
16. forbidden output self-check pass = true
```

Required artifact:

```text
explore10d_recommendation_gate.csv
```

Minimum fields:

```text
inheritance_pass
launch_seed_freeze_pass
launch_seed_relabel_pass
metric_contract_pass
support_matched_null_pass_seed_count
structural_matched_null_pass_seed_count
matched_null_fdr_pass_seed_count
family_ablation_supported_seed_count
risk_filter_interpretation_supported_seed_count
failure_secondary_used_as_primary_evidence
concentration_carry_forward_pass_seed_count
slice_stability_carry_forward_pass_seed_count
manualizability_carry_forward_pass_seed_count
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

## 12. Allowed and Forbidden Recommendations

Allowed recommendations:

```text
proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement
continue_explore10d_launch_risk_filter_audit
stop_due_to_no_support_matched_launch_risk_filter_evidence
stop_due_to_structural_matched_null_collapse
stop_due_to_family_ablation_not_supporting_risk_filter_interpretation
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
direct_launch_winner_trigger_validated
failure_reject_primitive_validated
```

Important boundary:

```text
proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement
```

means only:

```text
有足够证据写下一份人工公式复核 requirement，复核 launch-risk-filter primitive。
```

It does not mean:

```text
primitive is tradable
primitive is P1-ready
primitive is a winner trigger
strategy can be backtested
```

---

## 13. Required Outputs

All reports must be written to:

```text
Explore10/outputs/explore10d/reports/
```

All row-level parquet caches must be written to:

```text
Explore10/outputs/explore10d/cache/
```

Parquet caches must be gitignored.

### 13.1 Required report artifacts

```text
explore10d_run_manifest.json
explore10d_preflight_reference_artifact_audit.csv
explore10d_explore10c_inheritance_gate.csv
explore10d_launch_seed_freeze_audit.csv
explore10d_launch_seed_relabel_audit.csv
explore10d_launch_risk_filter_metric_contract.csv
explore10d_support_matched_null_audit.csv
explore10d_support_matched_null_summary.csv
explore10d_structural_matched_null_audit.csv
explore10d_matched_null_fdr_audit.csv
explore10d_family_ablation_audit.csv
explore10d_family_ablation_summary.csv
explore10d_token_coverage_carry_forward_audit.csv
explore10d_concentration_carry_forward_audit.csv
explore10d_slice_stability_carry_forward_audit.csv
explore10d_manualizability_carry_forward_audit.csv
explore10d_metric_nonselection_audit.csv
explore10d_threshold_nonselection_audit.csv
explore10d_model_nonselection_audit.csv
explore10d_score_bucket_nonselection_audit.csv
explore10d_fold_2024_nonselection_audit.csv
explore10d_forbidden_recommendation_self_check.csv
explore10d_cache_tracking_audit.csv
explore10d_required_artifact_authority_audit.csv
explore10d_recommendation_gate.csv
explore10d_report.md
```

### 13.2 Required cache artifacts

```text
explore10d_frozen_launch_seed_panel.parquet
explore10d_support_matched_null_panel.parquet
explore10d_structural_matched_null_panel.parquet
explore10d_family_ablation_panel.parquet
explore10d_launch_risk_filter_oof_panel.parquet
```

No row-level CSV export is allowed by default.

---

## 14. Report Requirements

`explore10d_report.md` must be in Chinese and must answer:

```text
1. Explore10D 是否正确继承 Explore10C 的 engineering pass？
2. Explore10D 是否没有创建新 seed？
3. launch seeds 是否被非性能规则重标为 risk-filter candidates？
4. support-matched null 是否改变 Explore10C 的 launch null 结论？
5. structural matched null 是否显示 top launch seeds 有真实结构？
6. family ablation 是否支持 volatility/range/money-coherence risk-filter interpretation？
7. 哪些 seeds 只是 support artifact 或 family artifact？
8. failure secondary 是否仍然 dominance primary？
9. 是否存在 concentration / slice / manualizability carry-forward blocker？
10. 是否可以进入 Explore10E manual formula review requirement？
11. 本阶段没有回答哪些交易或策略问题？
```

The report must include:

```text
Explore10D 只验证 launch-risk-filter primitive；
Explore10D 不验证 direct launch-winner trigger；
Explore10D 不证明 primitive 可交易。
```

---

## 15. Config Sketch

```yaml
phase: explore10d
title: electronics_launch_risk_filter_matched_null_and_family_ablation_audit
output_root: Explore10/outputs/explore10d
requirement_path: Explore10/requirement_explore10d.md

scope:
  primary:
    industry: 电子
    task: launch_winner
    role: primary_launch_risk_filter_audit
  secondary_guardrail:
    industry: 电子
    task: failure_reject
    role: inherited_placebo_guardrail_only

folds:
  core_oof: [fold_2021, fold_2022, fold_2023]
  robustness_only: [fold_2024]
  fold_2024_used_for_support: false

paths:
  explore10c_manifest: Explore10/outputs/explore10c/reports/explore10c_run_manifest.json
  explore10c_recommendation_gate: Explore10/outputs/explore10c/reports/explore10c_recommendation_gate.csv
  explore10c_seed_table: Explore10/outputs/explore10c/reports/explore10c_atomic_primitive_seed_table.csv
  explore10c_real_metric: Explore10/outputs/explore10c/reports/explore10c_primitive_real_metric_audit.csv
  explore10c_fdr: Explore10/outputs/explore10c/reports/explore10c_candidate_family_fdr_audit.csv
  explore10c_placebo_guardrail: Explore10/outputs/explore10c/reports/explore10c_placebo_guardrail_audit.csv
  explore10c_concentration: Explore10/outputs/explore10c/reports/explore10c_concentration_audit.csv
  explore10c_slice_stability: Explore10/outputs/explore10c/reports/explore10c_slice_stability_audit.csv
  explore10c_manualizability: Explore10/outputs/explore10c/reports/explore10c_manualizability_audit.csv
  explore10c_path_pattern_canonicalization: Explore10/outputs/explore10c/reports/explore10c_path_pattern_canonicalization.csv
  explore10c_path_pattern_fold_presence: Explore10/outputs/explore10c/reports/explore10c_path_pattern_fold_presence.csv
  explore10c_v2_panel: Explore10/outputs/explore10c/cache/explore10c_electronics_v2_hygiene_train_eval_panel.parquet
  explore10c_primitive_seed_oof_panel: Explore10/outputs/explore10c/cache/explore10c_electronics_primitive_seed_oof_panel.parquet

seed_policy:
  source_task: launch_winner
  source_feature_bank_version: v2_hygiene
  expected_launch_seed_count: 14
  new_seed_creation_allowed: false
  seed_drop_before_freeze_allowed: false
  interpretation: launch_risk_filter_candidate

risk_filter_tokens:
  feature_families:
    - volatility_range
    - volume_money
    - industry_market_context
  token_patterns:
    - atr
    - volatility
    - range
    - amplitude
    - money_price_coherence
    - volume_price_divergence
    - market_volatility_regime

nulls:
  support_matched_iterations: 500
  structural_matched_iterations: 500
  random_seed: 20260507
  sampling_with_replacement: true
  p_value_side: one_sided_upper_tail
  max_nearest_bucket_distance: 1
  support_count_bucket_edges: [0, 50, 100, 250, 500, 1000, 2000, .inf]
  weighted_support_bucket_edges: [0, 50, 100, 250, 500, 1000, 2000, .inf]
  instrument_count_bucket_edges: [0, 3, 5, 10, 20, 50, 100, .inf]
  instrument_year_count_bucket_edges: [0, 3, 5, 10, 20, 50, 100, .inf]
  families:
    - support_matched_random_row_null
    - support_matched_same_token_count_null
    - support_matched_same_fold_presence_null
    - support_matched_same_instrument_year_null
    - same_feature_family_set_null
    - same_token_count_null
    - same_fold_presence_null
    - same_quantile_direction_mix_null

family_ablation:
  suites:
    - remove_volatility_range_family
    - remove_volume_money_family
    - remove_cross_section_rank_family
    - remove_industry_market_context_family
    - keep_only_volatility_range_family
    - keep_only_volume_money_family
    - keep_only_volatility_range_plus_volume_money
    - keep_only_non_risk_filter_families

thresholds:
  min_risk_filter_seed_count: 1
  min_risk_filter_oof_lift_vs_baseline: 1.05
  min_real_minus_support_matched_null_p95: 0.0
  min_real_minus_structural_matched_null_p95: 0.0
  max_support_matched_empirical_p_value: 0.05
  max_structural_matched_empirical_p_value: 0.05
  max_fdr_q: 0.10
  min_ablation_support_retention_rate: 0.50
  min_ablated_token_count: 1
  min_ablated_oof_support_count: 50
  max_ablation_support_expansion_rate: 3.0
  max_fold_2024_support_usage_count: 0

allowed_recommendations:
  - proceed_to_explore10e_launch_risk_filter_manual_formula_review_requirement
  - continue_explore10d_launch_risk_filter_audit
  - stop_due_to_no_support_matched_launch_risk_filter_evidence
  - stop_due_to_structural_matched_null_collapse
  - stop_due_to_family_ablation_not_supporting_risk_filter_interpretation
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
  - direct_launch_winner_trigger_validated
  - failure_reject_primitive_validated
```

---

## 16. Expected Commands

Future implementation should add commands without breaking existing Explore10 / 10A / 10B / 10C commands:

```bash
uv run python Explore10/scripts/run_explore10.py profile-explore10d --config Explore10/configs/electronics_launch_risk_filter_explore10d.yaml
uv run python Explore10/scripts/run_explore10.py report-explore10d --config Explore10/configs/electronics_launch_risk_filter_explore10d.yaml
```

Required new config:

```text
Explore10/configs/electronics_launch_risk_filter_explore10d.yaml
```

Required `.gitignore` coverage:

```text
Explore10/outputs/explore10d/cache/
```

---

## 17. Acceptance Checklist

```text
[ ] Explore10C inheritance pass is audited from source artifacts
[ ] only Explore10C launch_winner seeds are frozen
[ ] no new seed is created
[ ] no seed is dropped before matched null / FDR
[ ] seed relabel to risk-filter is rule-based, not metric-based
[ ] risk-filter metric contract is pre-registered and machine-auditable
[ ] support-matched null bucket edges and nearest fallback rules are fixed before metrics
[ ] support-matched null includes all frozen launch seeds
[ ] structural matched null draws only from frozen Explore10C launch artifacts
[ ] structural matched null includes all frozen launch seeds
[ ] FDR family includes rejected and weak seeds
[ ] family ablation uses existing formula tokens and train-fold quantile buckets only
[ ] invalid ablation formulas are emitted as failed rows, not silently dropped
[ ] risk_filter_interpretation_supported has a deterministic boolean rule
[ ] no new LGBM model is trained
[ ] no new path extraction is run
[ ] no raw numeric threshold enters formula text
[ ] fold_2024 is not used for support or recommendation
[ ] failure side remains guardrail-only
[ ] recommendation cannot mention P1, backtest, score bucket, selected threshold, trade rule, or validated primitive
[ ] all required report artifacts exist
[ ] all required cache artifacts exist and are gitignored
[ ] Chinese report answers all Section 14 questions
```

---

## 18. Final Boundary Statement

Explore10D may conclude:

```text
电子 launch top seeds 不是 direct winner trigger，
但其中部分 formula 可能是 launch-risk-filter primitive，
值得进入 Explore10E manual formula review requirement。
```

Explore10D may also conclude:

```text
电子 launch top seeds 在 support-matched / structural-matched null 下仍然坍缩，
应停止 launch primitive 主线。
```

Explore10D must not conclude:

```text
电子 primitive 已验证有效。
电子可以进入 P1。
电子可以回测。
电子可以形成 score bucket。
电子可以形成交易规则。
failure diagnostic 可以替代 launch primary。
```

The strongest valid success meaning is:

```text
post_selected_electronics_launch_risk_filter_manual_review_seed_allowed = true
```
