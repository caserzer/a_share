# 需求：14C Cohort Rank Monotonicity Stress Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP13_ROOT/`、`SOURCE_EP12_ROOT/` 表达的路径必须先解析到对应 episode root。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、14A lineage 不可证明、14A row-level cache 不可证明、rank cutoff duplicate consistency 不可证明、split boundary 不可证明、rank finite coverage 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本或聚合 readout 反推出逐行 event membership、cohort rank、label、split 边界、entry 价格或 path outcome。

## 1. 实验身份

```text
experiment_id = 14_full_native_sparse_state_change_event_utility_preflight_v0
phase_id = 14C
run_id = 14C_cohort_rank_monotonicity_stress_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_14c_cohort_rank_monotonicity_stress_diagnostic.py
expected_config = configs/config_14c_cohort_rank_monotonicity_stress_diagnostic.yaml
expected_test_file = tests/test_14c_cohort_rank_monotonicity_stress_diagnostic.py
upstream_requirement_14a = EXPERIMENT_ROOT/requirement_14a_full_native_sparse_state_change_event_utility_preflight.md
upstream_requirement_13a = SOURCE_EP13_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

14C 是 14A 失败之后的轻量诊断 requirement。它不继续 winner-entry search，不修复 F5/F2/F6，不新增 event family，不训练模型，也不选择新的 trading rule。14C 只回答一个问题：

```text
14A 的 cohort normalization / event_intensity_score 在 validation stress 区间是否仍然
对 winner、fast_fail、lower_first、after-cost utility 保留单调信息？
```

14C 的输出用于决定后续研究路线：

```text
1. 若 stress 下只保留 bad-side 单调性，则优先进入 defense / participation overlay requirement；
2. 若 stress 下 winner / utility 单调性也存在，才允许讨论 event uniqueness redesign preflight；
3. 若 stress 下连 bad-side 单调性也消失，则 cohort-rank thesis 被证伪，不得继续围绕 intensity-rank 调参。
```

14C 永远不得产生以下授权：

```text
active_winner_entry_search_authorized = true
confirmatory_entry_authorized = true
meta_labeling_authorized = true
bet_sizing_authorized = true
production_strategy_authorized = true
```

## 2. 核心问题

14C 回答以下问题：

```text
Q1. 对 14A train-frozen selected arm F4_board_relative_strength_rank_jump__ret60_jump3，
    C3 cohort_percentile_rank 在 validation stress split 中是否仍与 fast_fail / lower_first
    呈稳定负相关？

Q2. C3 cohort_percentile_rank 在 validation stress split 中是否与 winner / 50bps utility
    呈稳定正相关，还是只保留 bad-side suppression 信息？

Q3. C1-C6 cohort dimensions 的单调性是否一致，还是 C3 只是局部偶然改善？

Q4. 单调性是否在 regime、board、volatility、liquidity 分层中坍塌？

Q5. 14C 应把后续路线导向 defense overlay、event uniqueness redesign diagnostic，
    还是完全关闭 cohort-rank winner-entry thesis？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

14C 允许做：

```text
1. 读取 14A publishable decision / audit / readout 作为 lineage；
2. 读取 14A local row-level caches 作为主数据源；
3. 对 14A 已生成的 cohort_percentile_rank 做 rank-IC、top-bottom spread、bucket slope；
4. 对 validation stress split 单独输出 stress monotonicity readout；
5. 对 board / regime / volatility / liquidity 做 readout-only 分层诊断；
6. 对 all-family sparse_event_panel 做 secondary raw-intensity monotonicity readout；
7. 输出确定性 next-research decision map。
```

14C 明确不是：

```text
confirmatory entry requirement
defense overlay implementation
event uniqueness redesign
new sparse event family search
new cohort arm search
threshold tuning
portfolio backtest
meta-labeling
nonlinear model retry
probability calibration
bet sizing
exit / holding policy
cost model calibration
```

14C 不得用 validation / robustness 选择新的 cohort arm、rank cutoff、event family、threshold 或 operating rule。14C 的 primary arm 必须固定为 14A decision 中的：

```text
selected_raw_event_arm_id
selected_cohort_arm_id
selected_rank_cutoff_id
```

当前 14A 产物中该 primary arm 是：

```text
raw_event_arm_id = F4_board_relative_strength_rank_jump__ret60_jump3
cohort_arm_id = C3
rank_cutoff_id = top20pct
```

C1-C6 的读数只能作为 diagnostic readout。若 C3 失败但其他 cohort arm 通过，14C 不得把其他 arm 事后提升为 primary support，只能输出 `alternate_cohort_readout_present = true` 并要求另开 requirement。

## 4. 继承边界

### 4.1 允许继承

14C 可以继承 14A 的以下定义：

```text
record_unit = instrument x reference_date x raw_event_arm_id x cohort_arm_id
reference_date = PIT executable row date
entry_date = next executable open after reference_date
entry_price = qfq open at entry_date
split_bucket in {train, validation, robustness}
selected_label_id = vol20d_kup2p0_kdn1p0_H20
winner = 14A selected label winner_positive
fast_fail := lower_first OR same_bar_conflict
primary_cost_tier_bps = 50
path_utility_component_0bps = same-event path utility at 0bps
path_utility_component_50bps = same-event path utility at 50bps
path_utility_component_100bps = same-event path utility at 100bps
event_intensity_score = 14A frozen sparse-event family intensity score
cohort_percentile_rank = 14A PIT cohort percentile rank
rank_direction = high_is_stronger
```

14C 不得重新计算 14A labels、entry price、barrier touch、path utility、event membership 或 cohort rank，除非作为 audited equality check。若 14A row-level cache 缺失，14C 必须 `input_blocked`，不得静默重跑或局部重建 14A。

### 4.2 必需输入 artifacts

14C 必须读取以下 14A artifacts：

```text
EXPERIMENT_ROOT/requirement_14a_full_native_sparse_state_change_event_utility_preflight.md
EXPERIMENT_ROOT/outputs/manifests/14A_full_native_sparse_state_change_event_utility_preflight_manifest.json
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/full_native_sparse_state_change_event_utility_decision.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/search_multiplicity_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/pit_cohort_normalization_dictionary.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/pit_cohort_rank_availability_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/pit_cohort_normalized_utility_readout.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/validation_stress_interpretation_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/sparse_event_raw_readout.csv
EXPERIMENT_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/pit_cohort_normalized_event_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/sparse_event_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/state_change_feature_panel.parquet
```

The 14A manifest is publishable lineage only. It is not sufficient proof of 14A local-cache integrity because 14A local caches may be intentionally absent from manifest `output_hashes`. For each required 14A local-cache parquet, 14C must perform direct filesystem validation and write the following fields to `row_level_cohort_rank_source_audit.csv`:

```text
artifact_role
artifact_path
direct_read_status
row_count
column_count
sha256
schema_status
required_column_missing_list
local_cache_lineage_status
```

`local_cache_lineage_status` may be `pass` only when direct read, sha256 calculation, row count, and schema validation all pass. Missing or unreadable required local caches must produce `decision_state = 14C_input_blocked`; 14C must not infer local-cache validity from the 14A manifest.

The 14A report is optional narrative lineage only:

```text
EXPERIMENT_ROOT/outputs/publishable/reports/full_native_sparse_state_change_event_utility_preflight_report.md
```

14C 不得从该 report 读取任何用于计算的 metric、row membership、rank 或 label。

### 4.3 14A decision prerequisite

14C 只能在 14A 已完成且未授权 confirmatory entry 时运行。允许的 14A decision states：

```text
14A_diagnostic_cohort_signal_only_no_utility
14A_diagnostic_raw_event_signal_but_no_cohort_transport
14A_stop_no_cohort_utility_transport
14A_stop_validation_stress_failure_no_active_entry_authorization
14A_stop_density_duplicate_or_morphology_rediscovery
14A_stop_no_sparse_event_utility
```

若 14A decision 为：

```text
14A_supported_open_14B_confirmatory_sparse_event_requirement
```

14C 必须输出：

```text
decision_state = 14C_not_applicable_14A_already_supported_confirmatory_path
```

若 14A input blocked 或 decision artifact 不可读，14C 必须输出：

```text
decision_state = 14C_input_blocked
```

## 5. Row-Level Source Contract

### 5.1 Primary panel

Primary row-level source:

```text
pit_cohort_normalized_event_panel.parquet
```

Required columns：

```text
family_id
parameter_set_id
raw_event_arm_id
event_id
row_id
instrument
reference_date
split_bucket
board_bucket
calendar_year
instrument_year
reference_date_rank
event_intensity_score
entry_date
entry_price
upper_first
lower_first
same_bar_conflict
winner
fast_fail
upper_barrier_return
lower_barrier_return
terminal_return_20d
max_high_return
min_low_return
path_utility_component_0bps
path_utility_component_50bps
path_utility_component_100bps
cohort_finite_n
cohort_percentile_rank
cohort_rank_status
cohort_arm_id
rank_cutoff_id
selected_event_flag
skipped_event_flag
```

Required domain checks：

```text
split_bucket in {train, validation, robustness}
cohort_percentile_rank in [0, 1] when cohort_rank_status = pass
cohort_finite_n >= pit_cohort_normalization_dictionary.minimum_cohort_finite_n when cohort_rank_status = pass
winner, fast_fail, lower_first, same_bar_conflict are boolean-like
path_utility_component_0bps / 50bps / 100bps are finite for all primary panel rows
rank_direction for all C1-C6 = high_is_stronger
```

### 5.2 Rank cutoff duplicate canonicalization

14A stores one row per `(event_id, cohort_arm_id, rank_cutoff_id)` because top10pct and top20pct are both evaluated. 14C rank-IC / bucket monotonicity must not double count the same event.

Before analysis, 14C must audit duplicates over this key:

```text
duplicate_key = (raw_event_arm_id, event_id, cohort_arm_id)
```

For each duplicate group, the following fields must be identical across `rank_cutoff_id`:

```text
row_id
instrument
reference_date
split_bucket
event_intensity_score
winner
fast_fail
lower_first
same_bar_conflict
path_utility_component_0bps
path_utility_component_50bps
path_utility_component_100bps
cohort_finite_n
cohort_percentile_rank
cohort_rank_status
```

If any invariant field differs, output:

```text
duplicate_consistency_status = fail
decision_state = 14C_input_blocked
```

If consistency passes, build canonical panel by keeping exactly one row per duplicate key. The canonical selection rule is:

```text
1. sort rank_cutoff_id by priority: top20pct, top10pct, all other values lexicographically;
2. keep first row;
3. preserve original rank_cutoff_id in canonical_rank_cutoff_source.
```

`selected_event_flag` and `skipped_event_flag` are not used for monotonicity scoring because 14C evaluates continuous rank information, not a thresholded operating rule.

### 5.3 Feature enrichment

14C must join `state_change_feature_panel.parquet` to the canonical panel using:

```text
join_key = (row_id, instrument, reference_date)
```

Required enrichment columns：

```text
market_regime_bucket
volatility_20d_decile
liquidity_metric_decile
board_bucket
calendar_year
calendar_month
```

If feature enrichment is missing for more than 0.1% of canonical rows, output:

```text
feature_enrichment_status = fail
decision_state = 14C_input_blocked
```

Overlapping lineage columns must be checked before enrichment values are used:

```text
canonical.board_bucket == feature.board_bucket
canonical.calendar_year == feature.calendar_year
canonical.reference_date == feature.reference_date
canonical.split_bucket == feature.split_bucket, if feature.split_bucket exists
```

If the feature panel contains both `split_bucket` and `split`, overlap validation must use `split_bucket` as the authoritative comparable field. `split` is legacy lineage only and must not be compared to canonical `split_bucket` unless an explicit adapter first proves equality between `feature.split` and `feature.split_bucket`.

Any non-null mismatch in an overlapping lineage column must fail closed:

```text
feature_conflict_n > 0
feature_enrichment_status = fail
decision_state = 14C_input_blocked
```

`feature_enrichment_audit.csv` must record missing and conflict counts by overlap field so implementation cannot silently prefer one source over the other.

Volatility / liquidity strata are frozen as:

```text
low = decile <= 3
mid = 4 <= decile <= 6
high = decile >= 7
missing = null / non-finite
```

Derived stress fields are frozen as:

```text
volatility_bucket = bucket(volatility_20d_decile) using the low/mid/high/missing map above
liquidity_bucket = bucket(liquidity_metric_decile) using the low/mid/high/missing map above
```

14C must not require upstream `volatility_tertile` or `liquidity_tertile` columns; those names are not authoritative 14A cache fields.

If the upstream decile encoding is 0-9 rather than 1-10, runner must shift it to 1-10 after recording `decile_encoding_adapter_status = shifted_0_9_to_1_10`.

## 6. Primary Analysis Universe

Primary canonical event panel:

```text
raw_event_arm_id = selected_raw_event_arm_id from 14A decision
primary_cohort_arm_id = selected_cohort_arm_id from 14A decision
one canonical row per (raw_event_arm_id, event_id, cohort_arm_id)
include both cohort_rank_status = pass and non-pass rows
```

Current expected primary universe:

```text
raw_event_arm_id = F4_board_relative_strength_rank_jump__ret60_jump3
primary_cohort_arm_id = C3
primary_rank_cutoff_id = top20pct
```

For rank-IC and bucket monotonicity, `primary_rank_cutoff_id` is lineage only; canonical row-level rank analysis uses every event once regardless of top10/top20 threshold.

Primary finite-rank analysis panel:

```text
primary canonical event panel
where cohort_rank_status = pass
and cohort_percentile_rank is finite
```

Denominators must be reported separately:

```text
same_event_denominator_n = primary canonical event rows
finite_rank_n = primary finite-rank analysis rows
finite_rank_coverage = finite_rank_n / same_event_denominator_n
dropped_total_n = same_event_denominator_n - finite_rank_n
dropped_insufficient_cohort_n = count(cohort_rank_status = insufficient_cohort)
dropped_degenerate_partial_cohort_n = count(cohort_rank_status = degenerate_partial_cohort)
dropped_nonfinite_rank_n = count(cohort_rank_status = pass and cohort_percentile_rank is non-finite)
```

Because C3 uses `rolling_prior_252d`, insufficient-cohort drops may concentrate in early train history. 14C must therefore write `primary_finite_rank_coverage_audit.csv` by split and `calendar_year`, including dropped counts and rates, so reviewers can see whether rank-IC is biased toward events with longer prior history. This audit is interpretive; it does not change the §8.2 power gate.

Coverage audit status is deterministic:

```text
split_dropped_total_n = sum(dropped_total_n) within split_bucket
earliest_train_year = min(calendar_year where split_bucket = train)
earliest_train_year_drop_share =
  dropped_total_n for (split_bucket = train, calendar_year = earliest_train_year)
  / split_dropped_total_n for train

coverage_audit_status = no_drops
  if split_dropped_total_n = 0

coverage_audit_status = train_early_history_concentration
  if split_bucket = train
  and calendar_year = earliest_train_year
  and earliest_train_year_drop_share >= 0.80

coverage_audit_status = pass
  otherwise
```

Secondary universe：

```text
all C1-C6 cohort arms for selected_raw_event_arm_id
```

Secondary all-family raw-intensity universe:

```text
sparse_event_panel.parquet all raw_event_arm_id
```

The all-family raw-intensity universe may only evaluate `event_intensity_score` within each `raw_event_arm_id` and split. It must not invent C1-C6 cohort ranks for families that 14A did not cohort-normalize.

For each `(raw_event_arm_id, split_bucket)`, raw-intensity ranking must be:

```text
secondary_raw_intensity_percentile_rank =
  midpoint percentile rank of event_intensity_score within the raw arm and split
rank_direction = high_is_stronger
ties = midpoint rank
top20pct = secondary_raw_intensity_percentile_rank >= 0.80
bottom20pct = secondary_raw_intensity_percentile_rank <= 0.20
```

The all-family readout role is diagnostic only:

```text
readout_role = diagnostic_secondary_not_for_selection
```

Families that failed 14A raw-arm admission because of density, duplicate fraction, or morphology gates remain excluded from next-requirement authorization. A monotonic all-family raw-intensity readout may motivate discussion, but it must not set `next_allowed_requirement`.

## 7. Metrics

### 7.1 Rank-IC

For each group:

```text
group_key = (raw_event_arm_id, cohort_arm_id, split_bucket)
```

and for stress strata:

```text
group_key = (raw_event_arm_id, cohort_arm_id, split_bucket, stress_dimension, stress_bucket)
```

compute Spearman rank correlation using average tie ranks:

```text
rank_ic_winner = spearman(cohort_percentile_rank, winner)
rank_ic_fast_fail = spearman(cohort_percentile_rank, fast_fail)
rank_ic_lower_first = spearman(cohort_percentile_rank, lower_first)
rank_ic_utility_0bps = spearman(cohort_percentile_rank, path_utility_component_0bps)
rank_ic_utility_50bps = spearman(cohort_percentile_rank, path_utility_component_50bps)
rank_ic_utility_100bps = spearman(cohort_percentile_rank, path_utility_component_100bps)
rank_ic_terminal_return_20d = spearman(cohort_percentile_rank, terminal_return_20d)
```

Expected sign:

```text
rank_ic_winner > 0
rank_ic_fast_fail < 0
rank_ic_lower_first < 0
rank_ic_utility_50bps > 0
```

For binary targets (`winner`, `fast_fail`, `lower_first`), Spearman rank-IC uses average ranks over many tied 0/1 outcomes. Its sign and uncertainty are decision-relevant, but its absolute magnitude must not be compared directly with continuous utility rank-IC.

A group is `insufficient_n` if finite pair count is below:

```text
minimum_rank_ic_n = 100
minimum_stress_stratum_rank_ic_n = 50
```

### 7.2 Bucket monotonicity

Primary bucket readout uses quintiles:

```text
Q1 = [0.00, 0.20)
Q2 = [0.20, 0.40)
Q3 = [0.40, 0.60)
Q4 = [0.60, 0.80)
Q5 = [0.80, 1.00]
```

For each bucket compute:

```text
event_n
winner_rate
fast_fail_rate
lower_first_rate
utility_mean_0bps
utility_mean_50bps
utility_mean_100bps
terminal_return_20d_mean
```

Top-bottom spreads:

```text
top_bottom_winner_delta = Q5.winner_rate - Q1.winner_rate
top_bottom_fast_fail_delta = Q5.fast_fail_rate - Q1.fast_fail_rate
top_bottom_lower_first_delta = Q5.lower_first_rate - Q1.lower_first_rate
top_bottom_utility_delta_50bps = Q5.utility_mean_50bps - Q1.utility_mean_50bps
```

Expected signs:

```text
top_bottom_winner_delta > 0
top_bottom_fast_fail_delta < 0
top_bottom_lower_first_delta < 0
top_bottom_utility_delta_50bps > 0
```

Secondary decile readout is allowed only when:

```text
split_group_event_n >= 300
all_decile_event_n >= 20
```

Decile readout must be marked `readout_only`, and primary decision must use quintiles.

### 7.3 Stress dimensions

Stress dimensions must be readout-only:

```text
split_bucket = validation
market_regime_bucket
board_bucket
volatility_bucket
liquidity_bucket
calendar_year
```

For each stress dimension bucket, compute rank-IC and quintile spreads if `event_n >= 50`. If insufficient, output `stress_bucket_status = insufficient_n` and do not impute.

### 7.4 Bootstrap uncertainty

14C must provide deterministic bootstrap intervals for primary C3 readouts:

```text
bootstrap_seed = 1403001
bootstrap_n = 500
bootstrap_cluster = instrument_year
ci_level = 90%
```

Required bootstrap metrics:

```text
rank_ic_fast_fail_ci_low
rank_ic_fast_fail_ci_high
rank_ic_utility_50bps_ci_low
rank_ic_utility_50bps_ci_high
top_bottom_fast_fail_delta_ci_low
top_bottom_fast_fail_delta_ci_high
top_bottom_utility_delta_50bps_ci_low
top_bottom_utility_delta_50bps_ci_high
```

If a split has fewer than 30 bootstrap clusters, output `bootstrap_status = insufficient_clusters` and leave CI fields null. Point estimates still must be reported.

## 8. Gate Definitions

### 8.1 Input gate

Pass only if:

```text
all required artifacts read_status = pass
14A decision prerequisite satisfied
14A manifest exists for publishable lineage
required 14A local caches have direct filesystem row_count / sha256 / schema audit status = pass
primary row-level cache schema matches required columns
feature enrichment join status = pass
duplicate consistency status = pass
```

### 8.2 Primary C3 power gate

Pass only if the primary canonical event panel and finite-rank analysis panel have:

```text
train same_event_denominator_n >= 300
validation same_event_denominator_n >= 300
robustness same_event_denominator_n >= 300
train finite_rank_n >= 300
validation finite_rank_n >= 300
robustness finite_rank_n >= 300
train finite_rank_coverage >= 0.90
validation finite_rank_coverage >= 0.90
robustness finite_rank_coverage >= 0.90
```

Current 14A expected canonical denominator counts are:

```text
train = 1061
validation = 553
robustness = 534
```

Current 14A expected finite-rank counts are:

```text
train = 1004
validation = 553
robustness = 534
```

These expected counts are audit hints, not hard-coded values. The runner must read actual counts from row-level cache.

### 8.3 Stress bad-side monotonicity gate

Pass if primary C3 satisfies all:

```text
validation.rank_ic_fast_fail <= -0.03
validation.bootstrap_status = pass
validation.rank_ic_fast_fail_ci_high < 0
validation.top_bottom_fast_fail_delta <= -0.03
train.rank_ic_fast_fail <= 0
robustness.rank_ic_fast_fail <= 0
validation.top_bottom_lower_first_delta <= 0
```

This gate supports only defense / participation interpretation. It does not authorize entry. If validation bootstrap status is `insufficient_clusters`, the bad-side gate must fail even when the point estimate is negative.

### 8.4 Stress utility monotonicity gate

Pass if primary C3 satisfies all:

```text
validation.rank_ic_utility_50bps >= 0.03
validation.top_bottom_utility_delta_50bps > 0
train.rank_ic_utility_50bps >= 0
robustness.rank_ic_utility_50bps >= 0
```

This gate says the cohort-rank thesis is not fully dead. It does not override 14A same-event utility failure.

### 8.5 Stress winner monotonicity gate

Pass if primary C3 satisfies all:

```text
validation.rank_ic_winner >= 0.03
validation.top_bottom_winner_delta > 0
train.rank_ic_winner >= 0
robustness.rank_ic_winner >= 0
```

Winner monotonicity without utility monotonicity must be reported as probability-only / diagnostic-only.

### 8.6 Cohort dimension consistency gate

For C1-C6 readout, compute per-cohort stress signs:

```text
badside_sign_good = validation.rank_ic_fast_fail < 0
utility_sign_good = validation.rank_ic_utility_50bps > 0
winner_sign_good = validation.rank_ic_winner > 0
```

Status:

```text
cohort_dimension_consistency_status = broad_support
  if at least 3 of 6 cohort arms have badside_sign_good and at least 2 of 6 have utility_sign_good.

cohort_dimension_consistency_status = badside_only_broad_support
  if at least 3 of 6 cohort arms have badside_sign_good and fewer than 2 have utility_sign_good.

cohort_dimension_consistency_status = localized_or_weak
  if primary C3 passes one monotonicity gate but fewer than 3 of 6 cohort arms share the sign.

cohort_dimension_consistency_status = no_support
  otherwise.
```

This gate is readout-only for next-thesis routing. It cannot promote a non-primary cohort arm into primary support.

### 8.7 Search accounting gate

Pass only if:

```text
primary_raw_event_arm_id is copied from 14A decision
primary_cohort_arm_id is copied from 14A decision
no validation / robustness selected new arm
all C1-C6 readouts marked diagnostic_secondary
all-family sparse_event_panel readout marked diagnostic_secondary
no threshold is selected from validation or robustness
```

## 9. Decision Map

Decision precedence is deterministic:

```text
if input_gate_status != pass:
  decision_state = 14C_input_blocked
  next_allowed_requirement = none
  secondary_allowed_discussion = none

elif 14A decision already supports confirmatory sparse event:
  decision_state = 14C_not_applicable_14A_already_supported_confirmatory_path
  next_allowed_requirement = none
  secondary_allowed_discussion = none

elif primary_c3_power_gate_status != pass:
  decision_state = 14C_insufficient_primary_power
  next_allowed_requirement = none
  secondary_allowed_discussion = none

elif stress_badside_monotonicity_gate_status == pass
   and stress_utility_monotonicity_gate_status == pass
   and stress_winner_monotonicity_gate_status == pass:
  decision_state = 14C_stress_rank_monotonic_supported_diagnostic_only
  next_allowed_requirement = requirement_14d_defense_overlay_confirmatory.md
  secondary_allowed_discussion = requirement_14e_event_uniqueness_redesign_preflight.md

elif stress_badside_monotonicity_gate_status == pass:
  decision_state = 14C_stress_badside_monotonic_supported_defense_only
  next_allowed_requirement = requirement_14d_defense_overlay_confirmatory.md
  secondary_allowed_discussion = none

elif stress_utility_monotonicity_gate_status == pass
     or stress_winner_monotonicity_gate_status == pass:
  decision_state = 14C_probability_or_utility_monotonic_partial_no_defense_support
  next_allowed_requirement = none
  secondary_allowed_discussion = requirement_14e_event_uniqueness_redesign_preflight.md

else:
  decision_state = 14C_stress_cohort_rank_monotonicity_not_supported
  next_allowed_requirement = none
  secondary_allowed_discussion = none
```

`next_allowed_requirement = requirement_14d_defense_overlay_confirmatory.md` is permitted only when `stress_badside_monotonicity_gate_status = pass`. Utility-only or winner-only monotonicity is not sufficient evidence for defense overlay and never authorizes entry, meta-labeling, bet sizing, or production use.

14B remains reserved for the 14A confirmatory sparse-event entry path (`requirement_14b_confirmatory_sparse_event_requirement.md`). 14C must not emit a new 14B-named requirement. If defense overlay is supported, the next requirement is 14D; if event uniqueness redesign is only a secondary discussion path, it is 14E.

Every decision must also output:

```text
active_winner_entry_search_authorized = false
confirmatory_entry_authorized = false
meta_labeling_authorized = false
bet_sizing_authorized = false
production_strategy_authorized = false
```

## 10. Required Outputs

Publishable table root:

```text
outputs/publishable/tables/14C_cohort_rank_monotonicity_stress_diagnostic/
```

Local cache root:

```text
outputs/local_cache/14C_cohort_rank_monotonicity_stress_diagnostic/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_14a_lineage_audit.csv
row_level_cohort_rank_source_audit.csv
rank_cutoff_duplicate_consistency_audit.csv
feature_enrichment_audit.csv
primary_finite_rank_coverage_audit.csv
primary_cohort_rank_ic_by_split.csv
primary_cohort_rank_bucket_monotonicity_readout.csv
primary_cohort_rank_bootstrap_interval.csv
cohort_dimension_rank_ic_by_split.csv
cohort_dimension_bucket_monotonicity_readout.csv
stress_regime_rank_monotonicity_readout.csv
stress_dimension_failure_mode_audit.csv
all_family_raw_intensity_monotonicity_readout.csv
search_accounting_audit.csv
cohort_rank_monotonicity_stress_decision.csv
```

Required local caches:

```text
cohort_rank_monotonicity_panel.parquet
primary_c3_rank_bucket_panel.parquet
stress_dimension_rank_panel.parquet
```

Required report:

```text
outputs/publishable/reports/cohort_rank_monotonicity_stress_diagnostic_report.md
```

Required manifest:

```text
outputs/manifests/14C_cohort_rank_monotonicity_stress_diagnostic_manifest.json
```

Manifest must include:

```text
run_id
phase_id
git_revision
config_hash
input_artifacts with sha256
output_hashes for every publishable table and report
decision_state
next_allowed_requirement
created_at_utc
```

## 11. Output Schema Requirements

### 11.1 `cohort_rank_monotonicity_stress_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
secondary_allowed_discussion
active_winner_entry_search_authorized
confirmatory_entry_authorized
meta_labeling_authorized
bet_sizing_authorized
production_strategy_authorized
selected_raw_event_arm_id
selected_cohort_arm_id
selected_rank_cutoff_id
primary_cost_tier_bps
input_gate_status
primary_c3_power_gate_status
stress_badside_monotonicity_gate_status
stress_utility_monotonicity_gate_status
stress_winner_monotonicity_gate_status
cohort_dimension_consistency_status
search_accounting_gate_status
primary_failure_reason
```

### 11.2 `input_artifact_audit.csv`

Required columns:

```text
artifact_role
artifact_path
resolved_path
required_flag
lineage_role
read_status
row_count
column_count
sha256
schema_status
required_column_missing_list
```

### 11.3 `upstream_14a_lineage_audit.csv`

Required columns:

```text
upstream_requirement_path
upstream_requirement_sha256
upstream_manifest_path
upstream_manifest_sha256
upstream_decision_path
upstream_decision_sha256
upstream_decision_state
upstream_next_allowed_requirement
upstream_selected_raw_event_arm_id
upstream_selected_cohort_arm_id
upstream_selected_rank_cutoff_id
upstream_primary_cost_tier_bps
decision_prerequisite_status
lineage_status
```

### 11.4 `row_level_cohort_rank_source_audit.csv`

Required columns:

```text
artifact_role
artifact_path
direct_read_status
row_count
column_count
sha256
schema_status
required_column_missing_list
local_cache_lineage_status
```

### 11.5 `rank_cutoff_duplicate_consistency_audit.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
duplicate_key_name
duplicate_group_n
duplicate_row_n
rank_cutoff_values
canonical_rank_cutoff_priority
canonical_row_n
invariant_field
mismatch_group_n
mismatch_row_n
duplicate_consistency_status
```

`duplicate_consistency_status` may be `pass` only when every invariant field in §5.2 has zero mismatch groups.

### 11.6 `feature_enrichment_audit.csv`

Required columns:

```text
join_key_name
canonical_row_n
matched_row_n
missing_n
missing_rate
overlap_field
feature_conflict_n
feature_conflict_rate
split_field_source
split_adapter_status
decile_encoding_adapter_status
feature_enrichment_status
```

### 11.7 `primary_cohort_rank_ic_by_split.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
same_event_denominator_n
finite_rank_n
finite_rank_coverage
dropped_total_n
dropped_insufficient_cohort_n
dropped_insufficient_cohort_rate
dropped_degenerate_partial_cohort_n
dropped_nonfinite_rank_n
rank_ic_winner
rank_ic_fast_fail
rank_ic_lower_first
rank_ic_utility_0bps
rank_ic_utility_50bps
rank_ic_utility_100bps
rank_ic_terminal_return_20d
expected_sign_winner_status
expected_sign_fast_fail_status
expected_sign_lower_first_status
expected_sign_utility_50bps_status
rank_ic_status
```

All rank-IC values in this table must use only the primary finite-rank analysis panel. `same_event_denominator_n` is carried for denominator visibility and must not be used as the Spearman sample count. All dropped-rate fields use `same_event_denominator_n` as denominator.

### 11.8 `primary_finite_rank_coverage_audit.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
calendar_year
same_event_denominator_n
finite_rank_n
dropped_total_n
dropped_insufficient_cohort_n
dropped_insufficient_cohort_rate
dropped_degenerate_partial_cohort_n
dropped_degenerate_partial_cohort_rate
dropped_nonfinite_rank_n
dropped_nonfinite_rank_rate
split_dropped_total_n
earliest_train_year
earliest_train_year_drop_share
dominant_dropped_cohort_rank_status
coverage_audit_status
```

`coverage_audit_status` is readout-only and must use the deterministic rules in §6. This status is report interpretation evidence, not an additional power gate.

### 11.9 `primary_cohort_rank_bootstrap_interval.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
bootstrap_seed
bootstrap_n
bootstrap_cluster
bootstrap_status
rank_ic_fast_fail_ci_low
rank_ic_fast_fail_ci_high
rank_ic_utility_50bps_ci_low
rank_ic_utility_50bps_ci_high
top_bottom_fast_fail_delta_ci_low
top_bottom_fast_fail_delta_ci_high
top_bottom_utility_delta_50bps_ci_low
top_bottom_utility_delta_50bps_ci_high
```

Validation bad-side defense authorization must read `bootstrap_status` and `rank_ic_fast_fail_ci_high` from this table.

### 11.10 `primary_cohort_rank_bucket_monotonicity_readout.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
bucket_scheme
rank_bucket_id
rank_bucket_low
rank_bucket_high
event_n
winner_rate
fast_fail_rate
lower_first_rate
utility_mean_0bps
utility_mean_50bps
utility_mean_100bps
terminal_return_20d_mean
top_bottom_winner_delta
top_bottom_fast_fail_delta
top_bottom_lower_first_delta
top_bottom_utility_delta_50bps
bucket_monotonicity_status
```

### 11.11 `cohort_dimension_rank_ic_by_split.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
event_n
finite_rank_n
rank_ic_winner
rank_ic_fast_fail
rank_ic_lower_first
rank_ic_utility_50bps
expected_sign_winner_status
expected_sign_fast_fail_status
expected_sign_lower_first_status
expected_sign_utility_50bps_status
rank_ic_status
readout_role
```

`readout_role` must be `diagnostic_secondary_not_for_selection` for every C1-C6 row.

### 11.12 `cohort_dimension_bucket_monotonicity_readout.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
split_bucket
bucket_scheme
rank_bucket_id
rank_bucket_low
rank_bucket_high
event_n
winner_rate
fast_fail_rate
lower_first_rate
utility_mean_50bps
top_bottom_winner_delta
top_bottom_fast_fail_delta
top_bottom_lower_first_delta
top_bottom_utility_delta_50bps
bucket_monotonicity_status
readout_role
```

`readout_role` must be `diagnostic_secondary_not_for_selection`; this table cannot promote a non-primary cohort arm into primary support.

### 11.13 `stress_regime_rank_monotonicity_readout.csv`

Required columns:

```text
raw_event_arm_id
cohort_arm_id
stress_dimension
stress_bucket
split_bucket
event_n
finite_rank_n
rank_ic_winner
rank_ic_fast_fail
rank_ic_lower_first
rank_ic_utility_50bps
top_bottom_winner_delta
top_bottom_fast_fail_delta
top_bottom_lower_first_delta
top_bottom_utility_delta_50bps
stress_bucket_status
readout_role
```

Allowed `stress_dimension` values:

```text
market_regime_bucket
board_bucket
volatility_bucket
liquidity_bucket
calendar_year
```

`readout_role` must be `diagnostic_secondary_not_for_selection`.

### 11.14 `stress_dimension_failure_mode_audit.csv`

Required columns:

```text
stress_dimension
stress_bucket
split_bucket
event_n
rank_ic_fast_fail
rank_ic_utility_50bps
top_bottom_fast_fail_delta
top_bottom_utility_delta_50bps
stress_bucket_status
failure_mode
```

Allowed `failure_mode` values:

```text
badside_monotonic_utility_not_monotonic
utility_monotonic_badside_not_monotonic
both_monotonic
neither_monotonic
insufficient_n
```

### 11.15 `search_accounting_audit.csv`

Required columns:

```text
primary_raw_event_arm_id
primary_cohort_arm_id
primary_rank_cutoff_id
validation_selected_new_arm
robustness_selected_new_arm
c1_c6_readout_role
all_family_readout_role
threshold_selected_from_validation
threshold_selected_from_robustness
search_accounting_gate_status
```

Pass only if validation / robustness did not select any new arm or threshold and all secondary readouts are marked diagnostic.

### 11.16 `all_family_raw_intensity_monotonicity_readout.csv`

Required columns:

```text
raw_event_arm_id
family_id
parameter_set_id
split_bucket
event_n
rank_source
top20_event_n
bottom20_event_n
rank_ic_winner
rank_ic_fast_fail
rank_ic_utility_50bps
top_bottom_winner_delta
top_bottom_fast_fail_delta
top_bottom_utility_delta_50bps
readout_role
```

`rank_source` must be `secondary_raw_intensity_percentile_rank`. Top/bottom deltas must use the fixed top20pct / bottom20pct rules in §6, never validation-optimized cutoffs.

`readout_role` must always be:

```text
diagnostic_secondary_not_for_selection
```

Even if F2 / F5 / F6 or any other 14A density-excluded family shows monotonic raw-intensity readout, this table must not trigger `next_allowed_requirement`. It is evidence for human discussion only.

## 12. Report Requirements

Report must be written in Chinese and include:

```text
1. 14A failure recap and why 14C exists;
2. primary C3 stress monotonicity result;
3. bad-side vs winner / utility 单调性的分离解释；
4. C1-C6 cohort dimensions 是否一致；
5. stress regime / board / vol / liquidity failure mode；
6. finite-rank coverage and insufficient-cohort drop distribution, especially train early-history concentration；
7. explicit note that binary-target rank-IC magnitudes are not directly comparable with continuous utility rank-IC；
8. all-family raw-intensity readout as secondary evidence only, and density-excluded families cannot trigger next_allowed_requirement；
9. deterministic decision and next_allowed_requirement；
10. explicit statement that 14C does not authorize winner-entry, meta-labeling, bet sizing, or production strategy.
```

Report 不得把 selected-entry utility、bucket top utility 或 diagnostic rank-IC 解释成 deployable alpha。

## 13. Test Plan

必须新增 focused synthetic tests：

```text
1. rank_cutoff duplicate rows are deduplicated exactly once and invariant-field mismatch fails closed;
2. primary arm is copied from 14A decision and cannot be replaced by validation-best C1-C6 arm;
3. Spearman rank-IC sign handling is correct for winner positive, fast_fail negative, utility positive;
4. quintile bucket boundaries include rank = 1.0 in Q5 and rank = 0.0 in Q1;
5. selected_event_flag / skipped_event_flag are ignored for continuous monotonicity scoring;
6. validation stress gate uses validation readout only, not robustness substitution;
7. feature enrichment join by (row_id, instrument, reference_date) fails closed above missing threshold;
8. feature enrichment overlap mismatch on board_bucket / calendar_year / split_bucket fails closed even when join coverage passes;
9. required 14A local caches are direct-read and sha256-audited; manifest presence alone cannot pass input gate;
10. primary power gate separates same_event_denominator_n, finite_rank_n, finite_rank_coverage, and dropped_insufficient_cohort_n;
11. primary_finite_rank_coverage_audit reports insufficient / degenerate / nonfinite rank drops separately by split and calendar_year;
12. coverage_audit_status is deterministic and flags train_early_history_concentration only when earliest_train_year_drop_share >= 0.80;
13. volatility_bucket and liquidity_bucket are derived from 14A decile columns; missing upstream tertile columns do not block implementation;
14. validation bad-side gate fails when rank_ic_fast_fail_ci_high crosses 0 or bootstrap_status is insufficient_clusters;
15. insufficient stress strata produce insufficient_n and do not impute rank-IC;
16. all required publishable tables have explicit schema and stable required columns;
17. all-family raw-intensity readout uses midpoint percentile rank and fixed top20pct / bottom20pct definitions;
18. all-family raw-intensity readout is marked diagnostic_secondary_not_for_selection;
19. density-excluded families with monotonic raw-intensity readout cannot trigger next_allowed_requirement;
20. decision precedence maps badside-only support to defense overlay, never entry authorization;
21. utility-only or winner-only support maps to no defense overlay and next_allowed_requirement = none;
22. 14C never emits a 14B-named next requirement; defense overlay is 14D and event uniqueness discussion is 14E;
23. manifest output hash coverage includes every publishable table and report.
```

Validation commands:

```text
python -m py_compile experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0/src/run_14c_cohort_rank_monotonicity_stress_diagnostic.py
python -m pytest experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0/tests -q
python src/run_14c_cohort_rank_monotonicity_stress_diagnostic.py --mode check-inputs
python src/run_14c_cohort_rank_monotonicity_stress_diagnostic.py --mode full
git diff --check
```

## 14. Implementation Notes

CLI must support:

```text
--mode {check-inputs,full}
--check-inputs-only
--config configs/config_14c_cohort_rank_monotonicity_stress_diagnostic.yaml
```

`check-inputs` must:

```text
1. resolve all required artifacts;
2. validate 14A decision prerequisite;
3. validate row-level cache schemas;
4. validate duplicate canonicalization;
5. validate feature enrichment joinability;
6. write input and source audits;
7. exit before computing rank-IC / bucket readouts.
```

`full` must run the complete diagnostic and emit all required outputs.

Implementation must prefer structured dataframe operations. It must not parse markdown reports for data, must not use validation / robustness to select a new primary arm, and must not mutate any 14A artifact.
