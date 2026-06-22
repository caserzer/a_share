# 需求：12A7b Direction C Simple-backbone Operating Rule Validation

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、entry executability 不可证明时 fail closed。
6. 不得从报告文本或聚合表反推出事件、标签、特征或逐行 score。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7b
direction_id = C
run_id = 12A7b_direction_c_simple_backbone_operating_rule_validation
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7b_direction_c_simple_backbone_operating_rule_validation.py
expected_config = configs/config_12a7b_direction_c_simple_backbone_operating_rule_validation.yaml
expected_test_file = tests/test_12a7b_direction_c_simple_backbone_operating_rule_validation.py
research_plan_source = research_plan_12a6d_rank_based_operating_point_revision.md
upstream_requirement = requirement_12a7_direction_a_trailing_rank_operating_point_audit.md
upstream_run_id = 12A7_direction_a_trailing_rank_operating_point_audit
```

12A7b Direction C 是 12A7 Direction A 的内部 follow-up。12A7 Direction A 的最终状态为：

```text
decision_state = 12A7_simple_backbone_supported_complex_model_not_supported
recommended_internal_followup = 12A7b_simple_backbone_operating_rule_validation
```

Direction C 的来源是 `research_plan_12a6d_rank_based_operating_point_revision.md` 第 6 节：

```text
C. defensive single-feature / low-capacity monotone challenger gate
```

本 requirement 使用 `12A7b` 编号，是因为 12A7 Direction A 已经完成且把 simple-backbone validation 指向内部 follow-up；`direction_id = C` 保留研究计划中的方向语义。

本需求回答三个问题：

```text
Q1. 如果把 defensive single-feature / simple backbone 设为主规则，
    它是否能在 PIT trailing-rank operating rule 下稳定降低 robustness fast-fail rate？

Q2. Stage-1 的 primary X 是否应从 50% 大比例 gate 改为 train-frozen selective tail keep/reject rule，
    尤其是 X = 30% / 40% / 50% 中的哪个 operating point？

Q3. 在 Q1/Q2 支持 simple backbone 之后，
    低容量、方向受约束的 monotone model 是否能在 robustness 上显著超过 simple backbone；
    如果不能，是否应停止复杂化，把 simple backbone 作为后续主基准？
```

## 2. 背景与核心修正

12A7 Direction A 已证明：

```text
rank-based operating point 比 12A6c train-frozen absolute threshold 更合理；
复杂模型 stage-1 在 robustness 上赢 same-budget random；
但复杂模型显著输给 train-frozen single-feature challenger volatility_60d asc；
stage-1 X=0.30 的 robustness curve 更像 selective tail rejector；
stage-2 有 continuation rank signal，但复杂度收益薄，暂时不应串联进 headline gate。
```

因此 12A7b Direction C 不再把 simple backbone 当作附属 challenger，而是把它提升为 primary candidate operating rule。

核心修正：

```text
old framing:
  complex model is primary; simple feature is challenger.

new framing:
  simple defensive backbone is primary baseline;
  validation phase 1 must first support the single-feature backbone operating rule;
  validation phase 2 may then test whether a low-capacity monotone model adds value;
  the 12A7 complex model is diagnostic comparator, not a support gatekeeper;
  low-capacity monotone model must beat the supported backbone before any higher-complexity model can be justified.
```

Validation split 在 12A6c / 12A7 中表现为低 base-rate、预算漂移明显的病态区间。因此：

```text
validation = readout-only stress split
robustness = primary OOS gate
train = only place where feature / orientation / X / model capacity can be selected
```

不得用 validation 或 robustness 结果回头选择 feature、orientation、budget X、history policy、model family 或 label。

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不重新定义 fast-fail / continuation label，不做 vol-scaled barrier；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不重新验证 12A7 Direction A 的复杂模型 headline gate；
- 不训练高容量 nonlinear ensemble，不引入 OOS-tuned feature search；
- 不把 validation 当作调参集；
- 不把 whole-month、board-month、whole-split rank 作为 primary gate；
- 不声明可交易 alpha，不做 policy replay、仓位、交易成本或资金曲线；
- 不把 stage-2 diagnostic uplift 当作 stage-1 backbone supported 的条件；
- 不要求 simple backbone 必须显著打赢 12A7 complex model 才能被 supported；
- 不在 simple backbone operating rule 尚未通过 robustness support gate 前，把 low-capacity monotone model 作为 support gate；
- 不让 low-capacity model 在未显著超过 simple backbone 时进入后续 headline gate。

## 4. 必需输入

### 4.1 12A7 Direction A 输出

必需输入：

```text
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/input_artifact_audit.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_decision.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_operating_point_readout.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_budget_curve_readout.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_budget_drift_audit.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_single_feature_challenger.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_random_same_budget_audit.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_score_quality_metrics.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_decile_lift_readout.csv
outputs/publishable/reports/trailing_rank_operating_point_validation_report.md
outputs/manifests/12A7_direction_a_trailing_rank_operating_point_audit_manifest.json
```

Local cache input:

```text
outputs/local_cache/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_score_matrix.parquet
```

### 4.2 12A6c two-stage inputs

Required row-level inputs:

```text
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_universe.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_targets.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_dictionary.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_pit_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_matrix.parquet
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

### 4.3 Random baseline inputs

Required matched random inputs:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
```

Random baseline must be replayed under the same split x board_bucket x calendar_month selected-count profile as the candidate rule. Aggregated random p50 from an unmatched denominator is not acceptable.

## 5. Primary Universe

Primary universe:

```text
source = 12A6c two_stage_event_universe.csv.gz
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage = stage_1
stage_1_evaluable = true
target = stage_1_fast_fail_target
lower target rate is better
```

This is a C0 risk_on event universe, not an all-regime universe.

Required universe audit:

```text
scope_id
raw_event_n
included_event_n
excluded_event_n
source_arm_is_c0_rate
market_regime_risk_on_rate
stage_1_evaluable_rate
split
board_bucket
calendar_year
calendar_month
failure_reason
```

Stage-2 is diagnostic only in this requirement:

```text
stage_2_role = diagnostic_only
stage_2_primary_gate_allowed = false
```

## 6. PIT Trailing-rank Rule

Use the same deployable rank definition as 12A7 Direction A.

Primary policy:

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
stage_1_global_min_history_n = 500
stage_1_board_min_history_n = 150
```

Rank computation frame:

```text
rank_frame = full chronological C0 risk_on stage-1 evaluable universe
rank_history = prior rows in rank_frame before current event_t0_pos
readout_split = assigned only after PIT rank_percentile is computed

validation / robustness ranks must not be computed in split-local frames.
For robustness events, prior train and validation events are allowed in trailing history
only if their event_t0_pos is before the current robustness event.
```

For each current event:

```text
1. Restrict history to prior events only:
     event_t0_pos < current_event_t0_pos
     and event_t0_pos >= current_event_t0_pos - 504
2. Use same-board history if sample_n >= 150.
3. Otherwise use global history if sample_n >= 500.
4. Otherwise rank_status = rank_not_evaluable.
```

Percentile definition:

```text
midrank_percentile =
  (count(H < s) + 0.5 * count(H = s)) / count(H)
```

For a feature with `ascending` orientation:

```text
keep_flag_X = feature_percentile <= X
```

For a feature with `descending` orientation:

```text
keep_flag_X = feature_percentile >= 1 - X
```

Rows with `rank_not_evaluable` are not selectable, but remain in `denominator_n`. Budget must be reported both against total denominator and rank-evaluable denominator.

Diagnostic-only policies:

```text
board_then_global_rolling_252_sessions
board_then_global_rolling_1008_sessions
board_then_global_expanding_from_inception
```

These policies cannot decide supported status.

Forbidden primary ranks:

```text
same_month_full_cohort_rank
board_month_full_cohort_rank
whole_split_rank
```

They may be published only as look-ahead upper bars with:

```text
diagnostic_only_flag = true
lookahead_rank_upper_bar = true
not_allowed_for_decision = true
```

## 7. Candidate Rules

### 7.1 Stage-1 single-feature backbone candidates

Candidate list:

```text
volatility_20d ascending
volatility_60d ascending
max_drawdown_60d ascending
distance_to_60d_low ascending
distance_to_120d_low ascending
rebound_from_60d_low ascending
```

The candidate list is fixed before any 12A7b validation / robustness readout. Feature availability and PIT status must come from `two_stage_feature_dictionary.csv` and `two_stage_feature_pit_audit.csv`.

Candidate availability rule:

```text
For each named candidate:
  if feature missing from feature dictionary -> candidate_status = excluded_missing_feature
  if pit_status != pass -> candidate_status = excluded_pit_failure
  otherwise candidate_status = candidate_available

If no candidate has candidate_status = candidate_available:
  decision_state = 12A7b_blocked_input_or_pit_failure
  failure_reason = no_pit_valid_stage1_backbone_candidate

If candidates are PIT-valid but no candidate tuple passes train sample / budget eligibility:
  decision_state = 12A7b_backbone_diagnostic_only
  failure_reason = no_train_eligible_backbone_tuple
```

### 7.2 Primary budget grid

Stage-1 budget grid:

```text
stage1_X_grid = [0.30, 0.40, 0.50]
```

Rationale:

```text
12A7 Direction A showed that X = 0.50 pulls too much middle mass into stage-1,
while X = 0.30 behaves more like a selective tail rejector.
12A7b must test this as a train-frozen operating rule, not as a robustness-picked rule.
```

`X = 0.40` is new relative to the 12A7 Direction A published budget curve. It must be generated by row-level PIT percentile replay. Linear interpolation or inference from aggregate `0.30 / 0.50 / 0.70` tables is forbidden.

### 7.3 Train-only selection rule

For every candidate feature and every `stage1_X_grid` value, first compute row-level PIT trailing percentile on the full chronological C0 risk_on rank frame defined in Section 6. Then select the primary tuple using train split rows only.

Allowed for selection:

```text
train rows
train labels
train selected_n / positive_n / rate / random readout
train rank-evaluable coverage
```

Forbidden for selection:

```text
validation labels / rates / budgets / random readout
robustness labels / rates / budgets / random readout
aggregate OOS curve behavior
```

Eligibility:

```text
train_selected_n >= 300
train_rank_evaluable_n >= 1000
train_denominator_positive_n >= 30
```

Primary simple backbone selection:

```text
1. Keep only eligible train candidate tuples.
2. Compute train_fast_fail_rate and train_delta_vs_random_p50.
3. Prefer tuples with train_delta_vs_random_p50 <= -0.02.
4. Choose the tuple with the lowest train_fast_fail_rate.
5. If absolute train_fast_fail_rate difference <= 0.002, choose the larger selected_n.
6. If still tied, choose lower complexity:
     single feature before two-feature model before three-feature model.
7. If still tied, choose feature_name ASC and X ASC.
```

The selected feature, orientation, X, history policy, and tie-break path must be written to `simple_backbone_train_selection.csv` and then applied unchanged to validation and robustness.

The train objective can naturally prefer the smallest X in the grid because lower X is more selective. This is acceptable only if the tuple passes the train eligibility gates and later robustness support gates. The selected tuple's X-driven capacity tradeoff must be reported explicitly in `simple_backbone_train_selection.csv`.

### 7.4 Sequential monotone-model validation

Direction C is a two-phase validation:

```text
phase_1 = single_feature_backbone_operating_rule_validation
phase_2 = low_capacity_monotone_incremental_value_validation
```

Phase 2 is enabled only if phase 1 supports the simple backbone on robustness:

```text
phase_2_enabled =
  phase_1_simple_backbone_gate_status = pass
  and phase_1_selected_tuple_frozen = true
```

If phase 1 does not support the simple backbone, monotone output must be:

```text
low_capacity_status = skipped_backbone_not_supported
diagnostic_only_flag = true
not_allowed_for_decision = true
```

Allowed phase-2 families:

```text
two_feature_monotone_additive_rank_score
three_feature_monotone_additive_rank_score
monotone_constrained_logistic_diagnostic_only_if_dependency_available
```

Primary phase-2 support family:

```text
monotone_additive_rank_score
```

For each feature, compute a risk-increasing percentile:

```text
if orientation = ascending:
  risk_percentile = feature_midrank_percentile

if orientation = descending:
  risk_percentile = 1 - feature_midrank_percentile
```

The monotone additive score is:

```text
monotone_risk_score = sum_j(weight_j * risk_percentile_j)
constraints:
  weight_j >= 0
  sum_j(weight_j) = 1
  feature_count <= 3
```

Pre-registered weight grid:

```text
two_feature_weights:
  [0.50, 0.50]
  [0.67, 0.33]
  [0.33, 0.67]

three_feature_weights:
  [0.34, 0.33, 0.33]
  [0.50, 0.25, 0.25]
  [0.25, 0.50, 0.25]
  [0.25, 0.25, 0.50]
```

Operating rule for phase 2:

```text
composite_history =
  prior monotone_risk_score values in the same PIT 504-session board/global history window

monotone_risk_score_percentile =
  midrank_percentile(monotone_risk_score, composite_history)

keep_flag_X = monotone_risk_score_percentile <= phase_1_selected_X
```

Composite score percentile uses the same rank frame and fallback discipline as Section 6:

```text
rank_frame = full chronological C0 risk_on stage-1 evaluable universe
board_min_history_n = 150
global_min_history_n = 500
rank_not_evaluable rows cannot be selected and remain in denominator_n
validation / robustness composite ranks must not be computed in split-local frames
```

Phase-2 feature subset and weights are selected on train only:

```text
candidate_pool = stage-1 single-feature backbone candidates
must_include = phase_1_selected_single_feature
max_features = 3
selection_objective = train fast-fail rate at phase_1_selected_X
tie_break = fewer features, then lower train selected_n drift, then feature_name ASC, then weight_json ASC
```

Disallowed for support gates:

```text
high_capacity_gradient_boosting
random_forest
deep_model
oos_selected_feature_subset
unconstrained model whose monotonicity cannot be proven from the risk_percentile transform and nonnegative weights
```

Constrained logistic models may be published only as diagnostics. If included, the optimizer, standardization, imputation, regularization grid, coefficient constraints, and dependency versions must be fully recorded in `low_capacity_monotone_model_card.csv`. Constrained logistic output cannot satisfy the primary support gate in this requirement; only the monotone additive rank score can.

### 7.5 Complex model comparator

The 12A7 Direction A complex model must remain a comparator, not a new primary:

```text
complex_model_source = 12A7_direction_a_trailing_rank_operating_point_audit
stage1_score_id = stage1_fast_fail_score
history_policy_id = board_then_global_rolling_504_sessions
score_reproduction_status = imported from trailing_rank_decision.csv
score_source_caveat = imported from trailing_rank_decision.csv
```

Complex model comparison must be matched by split x board_bucket x calendar_month selected_n on the common denominator. Raw unmatched budget differences cannot drive support status.

The complex comparator is diagnostic-only for phase-1 backbone support:

```text
complex_comparator_allowed_for_support_gate = false
complex_delta_near_miss_guard = 0.005 absolute fast-fail-rate difference
```

Comparator caveat rule:

```text
if score_source_caveat != "":
  complex_comparator_status = numerical_near_miss_diagnostic

if abs(delta_vs_complex_model) <= complex_delta_near_miss_guard:
  complex_comparator_status = complex_parity_or_near_miss

if bootstrap_ci95(candidate_minus_complex_model) crosses 0:
  complex_comparator_status = complex_parity_or_uncertain
```

These statuses must be reported, but they cannot downgrade `phase_1_simple_backbone_gate_status` if the backbone passes random, stability, budget, PIT, and coverage gates.

Common denominator definition:

```text
common_denominator_n =
  count rows in the target split that are label-evaluable and rank-evaluable
  for both candidate rule and comparator rule.

common_denominator_coverage_vs_complex_model =
  common_denominator_n / candidate_rank_evaluable_n

common_denominator_coverage_vs_simple_backbone =
  common_denominator_n / low_capacity_rank_evaluable_n
```

This is denominator overlap, not selected-set overlap. Selected-count replay must then be done inside this common denominator by split x board_bucket x calendar_month.

For phase-2, `common_denominator_coverage_vs_simple_backbone` is a paired-comparison completeness readout, not a warm-up protection gate. Because low-capacity composite rank-evaluable rows may be a subset of the single-feature backbone rank-evaluable rows, this ratio can be near 1.0 even when composite warm-up loses material rows. Phase-2 warm-up / abstention risk is controlled by `rank_not_evaluable_rate <= 0.05` and must be reported against the full phase-2 denominator.

## 8. Metrics

Required readout for every candidate tuple and split:

```text
stage
split
rule_id
rule_family
validation_phase
phase_1_simple_backbone_gate_status
phase_2_enabled
complex_score_reproduction_status
complex_score_source_caveat
complex_comparator_status
feature_list
feature_orientation_json
feature_list_hash
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_budget_X
denominator_n
rank_evaluable_n
rank_not_evaluable_n
denominator_positive_n
rank_evaluable_positive_n
selected_n
selected_positive_n
selected_budget_total
selected_budget_rank_evaluable
common_denominator_n
common_denominator_coverage_vs_complex_model
common_denominator_coverage_vs_simple_backbone
selected_fast_fail_rate
base_fast_fail_rate
delta_vs_base
random_p05
random_p50
random_p95
delta_vs_random_p50
complex_model_matched_rate
delta_vs_complex_model
simple_backbone_matched_rate
delta_vs_simple_backbone
bootstrap_random_ci95_low
bootstrap_random_ci95_high
bootstrap_complex_ci95_low
bootstrap_complex_ci95_high
bootstrap_backbone_ci95_low
bootstrap_backbone_ci95_high
bootstrap_denominator_positive_n
bootstrap_replicate_valid_n
readout_status
diagnostic_only_flag
```

Stage-1 target:

```text
selected_fast_fail_rate lower is better
delta_vs_random_p50 < 0 is better
delta_vs_complex_model < 0 means candidate beats complex model
delta_vs_simple_backbone < 0 means low-capacity model beats simple backbone
```

Budget drift readout:

```text
selected_budget_total
selected_budget_rank_evaluable
budget_abs_delta_total_vs_X
budget_abs_delta_rank_evaluable_vs_X
rank_not_evaluable_rate
board_history_used_rate
global_fallback_rate
history_n_p05
history_n_p50
history_n_p95
```

Validation must be included in all tables but marked:

```text
validation_gate_role = readout_only_stress_split
not_allowed_for_selection = true
```

## 9. Statistical Gates

Bootstrap settings:

```text
seed = 120711
n_resamples >= 2000
ci_low_q = 0.025
ci_high_q = 0.975
bootstrap_min_denominator_positive_n = 30
bootstrap_min_valid_replicates = 1500
```

Random CI:

```text
Use nested random-seed bootstrap.
Each bootstrap replicate must resample model events and random seeds,
then recompute random p50 from the resampled seed distribution.
```

Comparator CI:

```text
Use paired event bootstrap on the common denominator.
```

Stage-1 simple backbone is supported if robustness satisfies all:

```text
input_gate_status = pass
pit_gate_status = pass
selected_n >= 300
denominator_positive_n >= 30
bootstrap_replicate_valid_n >= 1500
selected_fast_fail_rate <= random_p50 - 0.02
bootstrap_ci95(candidate_minus_random_p50) entirely below 0
selected_budget_total <= 0.60
rank_not_evaluable_rate <= 0.05
```

Complex-model matched comparison is required as a diagnostic readout, but it is not a phase-1 support gate.

Low-capacity monotone model is supported over simple backbone only if robustness satisfies all:

```text
phase_1_simple_backbone_gate_status = pass
phase_2_enabled = true
selected_n >= 300
denominator_positive_n >= 30
bootstrap_replicate_valid_n >= 1500
low_capacity_fast_fail_rate <= simple_backbone_matched_rate - 0.01
bootstrap_ci95(low_capacity_minus_simple_backbone) entirely below 0
all monotone additive score constraints satisfied
feature_count <= 3
rank_not_evaluable_rate <= 0.05
```

If simple backbone is supported but low-capacity model does not beat it, complexity is not supported.

## 10. Stability Diagnostics

Required stability slices:

```text
split
calendar_year
board_bucket
primary_family_id
calendar_month
```

For each slice with `selected_n >= 100`, report:

```text
selected_n
selected_fast_fail_rate
base_fast_fail_rate
delta_vs_base
random_p50
delta_vs_random_p50
budget_total
budget_rank_evaluable
rank_not_evaluable_rate
direction_status
```

Direction status:

```text
pass = selected_fast_fail_rate < base_fast_fail_rate and selected_fast_fail_rate < random_p50
weak = selected_fast_fail_rate < base_fast_fail_rate but not < random_p50
fail = selected_fast_fail_rate >= base_fast_fail_rate
insufficient_n = selected_n < 100
```

Sign inversion or slope collapse in robustness must be called out in the report. Validation instability is a stress warning, not a hard blocker unless it reveals PIT leakage or input corruption.

## 11. Stage-2 Diagnostic Arm

Stage-2 remains diagnostic-only in this requirement.

Candidate:

```text
distance_to_120d_low descending
stage2_X_grid = [0.30, 0.50]
```

Orientation is stage-specific and train-frozen within each stage:

```text
stage-1 distance_to_120d_low ascending means lower pre-event distance is defensive for fast-fail avoidance.
stage-2 distance_to_120d_low descending means higher post-survival distance is diagnostic for continuation.
These orientations must not be shared or inferred across stages.
```

Diagnostic readouts:

```text
ground_truth_no_fast_fail_survivor_readout
stage1_simple_backbone_chained_survivor_readout
matched_random_same_budget_readout
simple_stage2_backbone_vs_complex_stage2_readout
```

Required warning:

```text
stage_2_diagnostic_only = true
not_allowed_for_12A7b_decision_state = true
```

Stage-2 may recommend a future requirement only if robustness selected_n, positive_n, and paired CI are sufficient. It cannot upgrade 12A7b support status.

## 12. Required Outputs

All publishable tables go under:

```text
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/
```

Required tables:

```text
input_artifact_audit.csv
scope_universe_audit.csv
simple_backbone_train_selection.csv
simple_backbone_candidate_curve.csv
simple_backbone_operating_point_readout.csv
simple_backbone_budget_drift_audit.csv
simple_backbone_random_same_budget_audit.csv
complex_model_matched_comparator.csv
low_capacity_monotone_model_card.csv
low_capacity_monotone_readout.csv
backbone_stability_slice_audit.csv
stage2_diagnostic_backbone_readout.csv
direction_c_decision.csv
```

Report:

```text
outputs/publishable/reports/simple_backbone_operating_rule_validation_report.md
```

Manifest:

```text
outputs/manifests/12A7b_direction_c_simple_backbone_operating_rule_validation_manifest.json
```

Local cache:

```text
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_score_matrix.parquet
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/bootstrap_replicates.parquet
```

## 13. Decision Map

```text
12A7b_simple_backbone_supported:
  phase-1 train-frozen simple backbone passes robustness support gates and beats random;
  complex model comparison is diagnostic-only;
  phase-2 was not run or was explicitly skipped by config.

12A7b_simple_backbone_supported_low_capacity_not_supported:
  phase-1 simple backbone passes;
  phase-2 runs but low-capacity monotone model does not significantly beat the supported backbone.

12A7b_low_capacity_monotone_supported_over_backbone:
  phase-1 simple backbone passes;
  phase-2 low-capacity monotone model beats the supported backbone with robustness CI support.

12A7b_backbone_diagnostic_only:
  phase-1 simple backbone point estimate is promising but sample size, CI width,
  budget drift or rank-evaluable coverage blocks support.

12A7b_no_simple_backbone_transport:
  phase-1 train-frozen simple backbone fails random baseline or direction stability on robustness.

12A7b_blocked_input_or_pit_failure:
  required input, PIT, leakage, random, or split-boundary gate fails.
```

Decision precedence must be exclusive:

```text
1. If input / PIT / leakage / random / split-boundary gate fails:
     decision_state = 12A7b_blocked_input_or_pit_failure

2. Else evaluate phase-1 simple backbone support gate.

3. If phase-1 fails random baseline or direction stability:
     decision_state = 12A7b_no_simple_backbone_transport

4. If phase-1 has favorable point estimate but fails sample-size, CI, budget-drift,
   or rank-evaluable coverage:
     decision_state = 12A7b_backbone_diagnostic_only

4b. If phase-1 beats random and is directionally stable but complex comparison is
    parity / uncertain / numerical near-miss:
      keep evaluating phase-1 support without using complex as a blocker;
      write complex_comparator_status to the report.

5. If phase-1 passes and phase_2_enabled = false:
     decision_state = 12A7b_simple_backbone_supported

6. If phase-1 passes and phase_2_enabled = true, evaluate phase-2.

7. If phase-2 passes monotone-over-backbone support gate:
     decision_state = 12A7b_low_capacity_monotone_supported_over_backbone

8. If phase-2 runs but does not pass monotone-over-backbone support gate:
     decision_state = 12A7b_simple_backbone_supported_low_capacity_not_supported
```

`next_allowed_requirement` mapping:

```text
if decision_state in [
  12A7b_simple_backbone_supported,
  12A7b_simple_backbone_supported_low_capacity_not_supported
]:
  next_allowed_requirement = none
  recommended_internal_followup = simple_backbone_policy_replay_or_12A8_calibration_scope_review

if decision_state = 12A7b_low_capacity_monotone_supported_over_backbone:
  next_allowed_requirement = none
  recommended_internal_followup = low_capacity_backbone_chained_stage2_validation

if decision_state in [
  12A7b_backbone_diagnostic_only,
  12A7b_no_simple_backbone_transport
]:
  next_allowed_requirement = requirement_12a9_vol_scaled_label_stability_and_separability_audit.md

if decision_state starts with 12A7b_blocked:
  next_allowed_requirement = none
```

## 14. Test Checklist

Required tests:

1. Input artifact audit includes every required artifact and fails closed on missing required files.
2. Primary universe is restricted to `source_arm_is_c0 = true`, `market_regime_bucket = risk_on`, `stage_1_evaluable = true`.
3. Split boundaries match 12A6c / 12A7 Direction A boundaries.
4. Feature PIT status is pass for every selected candidate.
5. Train-only selection does not read validation or robustness labels, rates, budgets, or bootstrap results.
6. Validation rows are never used for feature, orientation, X, history policy, or model-family selection.
7. Rolling history uses only prior `event_t0_pos` rows and never same-month full-cohort membership.
8. Validation / robustness PIT ranks are computed on the full chronological C0 risk_on rank frame, not split-local frames.
9. Board history falls back to global only when board history is below min history.
10. `rank_not_evaluable` rows cannot be selected but remain in total denominator.
11. Budget fields distinguish total denominator and rank-evaluable denominator.
12. Random baseline selected counts are matched by split x board_bucket x calendar_month.
13. Complex-model comparator uses common denominator and matched selected_n, not raw unmatched budgets.
14. Bootstrap CI direction is lower-is-better for stage-1 fast-fail rate.
15. Support gates use `selected_budget_total`, not an alias such as `budget_total`.
16. Complex comparator is diagnostic-only and cannot block phase-1 simple-backbone support.
17. Phase-2 reports common-denominator coverage vs simple backbone as paired-comparison completeness, not as a warm-up support gate.
18. Low-capacity model cannot be supported if monotone additive score constraints are violated.
19. Phase-2 composite `monotone_risk_score_percentile` is computed from prior composite scores under the same PIT history policy.
20. Phase-2 support gate enforces `rank_not_evaluable_rate <= 0.05`.
21. Stage-2 outputs are marked diagnostic-only and cannot alter `direction_c_decision.csv`.
22. Diagnostic look-ahead ranks, if produced, are marked `not_allowed_for_decision = true`.
23. Report reproduces `direction_c_decision.csv` headline numbers exactly.
24. Manifest records code path, config path, input sha256, output sha256, git revision, and run timestamp.

## 15. Report Requirements

The report must lead with:

```text
final decision
selected primary simple backbone tuple
robustness selected_n
robustness budget_total
robustness fast_fail_rate
delta_vs_random_p50 with CI
delta_vs_complex_model with CI
complex_score_source_caveat
complex_comparator_status
low_capacity_vs_simple_backbone result
validation stress warning
recommended next step
```

The report must explicitly state:

```text
Validation is readout-only because prior 12A6c / 12A7 evidence shows a pathological low-base-rate budget-drift interval.
No feature, orientation, X, or model capacity was chosen using validation or robustness.
The conclusion applies only to C0 risk_on events, not all regimes.
```

## 16. One-line Thesis

12A7b Direction C turns the 12A7 finding into a stricter operating-rule validation: low-volatility defensive simple backbone must be tested as the primary PIT trailing-rank rule, and any added model complexity must prove robustness value over that backbone before the research can move back toward calibration, labels, or chained stage-2 policy.
