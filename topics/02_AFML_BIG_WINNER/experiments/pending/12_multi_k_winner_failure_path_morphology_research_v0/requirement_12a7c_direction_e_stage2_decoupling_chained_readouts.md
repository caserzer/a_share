# 需求：12A7c Direction E Stage-2 Decoupling and Chained Readouts

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、stage-1 anchor 不可复现、stage-2 path label 不可复现、random replay 不可精确匹配时 fail closed。
6. 不得从报告文本或聚合表反推出事件、标签、特征、stage-1 keep flag、stage-2 score 或 random path label。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7c
direction_id = E
run_id = 12A7c_direction_e_stage2_decoupling_chained_readouts
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7c_direction_e_stage2_decoupling_chained_readouts.py
expected_config = configs/config_12a7c_direction_e_stage2_decoupling_chained_readouts.yaml
expected_test_file = tests/test_12a7c_direction_e_stage2_decoupling_chained_readouts.py
research_plan_source = research_plan_12a6d_rank_based_operating_point_revision.md
upstream_requirement_a = requirement_12a7_direction_a_trailing_rank_operating_point_audit.md
upstream_requirement_c = requirement_12a7b_direction_c_simple_backbone_operating_rule_validation.md
```

本 requirement 实现 `research_plan_12a6d_rank_based_operating_point_revision.md` 中的 Direction E：

```text
E. stage-2 decoupled and chained survivor diagnostics
```

12A7 Direction A 已明确不做 Direction E 的 ground-truth survivor 解耦读数。12A7b Direction C 只在 simple-backbone 报告中给出 stage-2 diagnostic preview；本需求将其正式化为可复现的 stage-2 解耦 / 链式 readout。

本需求回答四个问题：

```text
Q1. 在 ground-truth no-fast-fail survivor denominator 内，stage-2 continuation signal 是否真实存在？
    该 readout 是 diagnostic-only，不可解释为可部署策略。

Q2. 在 12A7b 支持的 stage-1 simple backbone keep 后，
    stage-2 PIT trailing-rank selector 是否仍能提高 continuation rate？

Q3. stage-2 continuation selector 的收益来自复杂 stage-2 score，
    还是可以被 train-frozen single-feature stage-2 backbone 吸收？

Q4. stage-1 fast-fail 防守是否牺牲了 continuation participation；
    如果牺牲，后续应走 stage-2 独立 selector / policy replay，
    而不是继续增加 stage-1 复杂度。
```

必须同时输出：

```text
stage2_decoupled_signal_status
stage2_chained_operating_status
```

## 2. 背景与核心修正

12A7 Direction A 的结论：

```text
12A7 decision_state = 12A7_simple_backbone_supported_complex_model_not_supported
stage-2 robustness AUC = 0.6041
stage-2 robustness rank_IC = 0.1183
stage-2 complex model beats random on the 12A7 chained primary readout,
but does not significantly beat distance_to_120d_low desc single-feature challenger.
```

12A7b Direction C 的结论：

```text
12A7b decision_state = 12A7b_simple_backbone_supported_low_capacity_not_supported
stage-1 anchor = volatility_20d asc, X = 0.30
stage-1 simple backbone passes robustness random and budget gates
low-capacity monotone model does not significantly beat simple backbone
```

12A7b stage-2 diagnostic preview 显示：

```text
robustness ground-truth no-fast-fail survivor continuation rate = 13.45%
robustness stage1-simple-backbone chained survivor continuation rate = 9.33%
robustness distance_to_120d_low desc, X=0.30 continuation rate = 17.57%
robustness matched random p50 for that stage-2 selection = 12.58%
robustness complex matched rate = 18.21%
simple-vs-complex stage-2 paired CI crosses zero
```

这些数值只能作为动机，不能作为本 requirement 的最终证据。Direction E 必须从 row-level artifacts 重新构造 denominators、PIT ranks、random replay、paired comparisons 和 bootstrap CI。

核心修正：

```text
old framing:
  stage-2 was chained into a headline two-stage model before stage-1 operating point was simplified.

new framing:
  stage-1 simple defensive backbone is a fixed anchor;
  stage-2 first gets a decoupled ground-truth survivor diagnostic;
  then stage-2 gets a chained, deployable readout after the fixed stage-1 anchor;
  decoupled signal and chained operating support are separate statuses.
```

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不重新定义 fast-fail / continuation label，不做 vol-scaled barrier；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不改变 12A7b 的 stage-1 simple backbone decision；
- 不验证 12A7b low-capacity monotone composite backbone；若上游 primary support 转为 composite anchor，必须进入独立 chained-stage-2 requirement；
- 不用 validation 或 robustness 回头选择 stage-1 feature、stage-1 X、history policy、stage-2 feature、stage-2 X、model family 或 label；
- 不把 ground-truth survivor decoupled readout 当作可部署策略；
- 不把 stage-2 diagnostic uplift 反向用于修改 stage-1 fast-fail support status；
- 不训练高容量 ensemble，不引入 OOS-tuned feature search；
- 不声明可交易 alpha，不做仓位、交易成本、slippage、资金曲线或组合回放；
- 不把 whole-month、board-month、whole-split rank 作为 deployable primary gate；
- 不把 complex stage-2 score 打赢 random 当作复杂模型支持的充分条件；必须同时比较 train-frozen single-feature stage-2 challenger。

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
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/split_time_boundary_audit.csv
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/score_reproduction_audit.csv
outputs/publishable/reports/trailing_rank_operating_point_validation_report.md
outputs/manifests/12A7_direction_a_trailing_rank_operating_point_audit_manifest.json
```

Local cache input:

```text
outputs/local_cache/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_score_matrix.parquet
```

`trailing_rank_score_matrix.parquet` 是 imported complex stage-2 score 的权威逐行来源，不得从报告或聚合表反推 score。它必须提供：

```text
meta_event_id
instrument
event_t0_date
event_t0_pos
split
board_bucket
calendar_month
stage_2_decision_pos
stage2_continuation_score
stage_2_continuation_target
score_source_mode
score_source_caveat
stage_2_model_id
```

Stage-2 path / no-fast-fail survivor flags are not required from this artifact. Direction E must source those fields from `simple_backbone_score_matrix.parquet` or from the 12A6c target/path-cache artifacts named below.

### 4.2 12A7b Direction C 输出

必需输入：

```text
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/input_artifact_audit.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_train_selection.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_operating_point_readout.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_budget_drift_audit.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/backbone_stability_slice_audit.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/stage2_diagnostic_backbone_readout.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/direction_c_decision.csv
outputs/publishable/reports/simple_backbone_operating_rule_validation_report.md
outputs/manifests/12A7b_direction_c_simple_backbone_operating_rule_validation_manifest.json
```

Optional local cache inputs for audit / cross-check:

```text
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_score_matrix.parquet
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/bootstrap_replicates.parquet
```

Missing optional 12A7b local-cache inputs must not fail the input gate if canonical anchor reconstruction and publishable count reconciliation from §5.4 pass.

Direction E canonical stage-1 anchor identity is read from `direction_c_decision.csv`:

```text
selected_primary_rule_id
selected_primary_simple_backbone_tuple
selected_primary_X
```

The anchor orientation, feature hash, and history policy must be resolved from the matching selected row in `simple_backbone_train_selection.csv` or `simple_backbone_operating_point_readout.csv`:

```text
rule_id = selected_primary_rule_id
feature_list
feature_orientation_json
feature_list_hash
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_budget_X = selected_primary_X
```

The resolved selected primary backbone must contain exactly one feature and one orientation. Any upstream alias or renamed field must be recorded in `input_artifact_audit.csv` and mapped to the canonical names above before use.

`simple_backbone_score_matrix.parquet` is a preferred cross-check only when its schema status is pass. Its presence must not turn 12A7b's unpublished local-cache schema into a hard cross-requirement contract. Minimal row identity columns for use are:

```text
meta_event_id
instrument
event_t0_pos
split
board_bucket
calendar_month
```

Preferred optional columns, if present, must be consumed for audit and cross-check:

```text
stage_2_decision_pos
no_fast_fail_L10_H20
stage_2_path_evaluable
stage_2_entry_blocked
stage_2_horizon_complete_20d
stage_2_continuation_target
<anchor_stage1_feature>__rank_percentile
<anchor_stage1_feature>__rank_status
selected_primary_simple_backbone_rule_id
```

If any preferred optional path or rank column is missing, Direction E must reconstruct the same field from §4.3 12A6c artifacts instead of failing the input gate. If `selected_primary_simple_backbone_rule_id` is present, it is treated only as an upstream local-cache alias and must equal the canonical `selected_primary_rule_id` from `direction_c_decision.csv`; if it is absent, no fallback is required because the canonical rule id comes from `direction_c_decision.csv`. Direction E outputs must use `stage1_anchor_rule_id`.

The stage-1 anchor for this requirement is the 12A7b train-frozen primary simple backbone:

```text
anchor_stage1_rule_source = direction_c_decision.csv
anchor_stage1_rule_id = selected_primary_rule_id
anchor_stage1_feature = selected_primary_simple_backbone_tuple
anchor_stage1_X = selected_primary_X
anchor_stage1_orientation_source = feature_orientation_json from selected 12A7b rule row
anchor_stage1_family = single_feature_backbone
expected_current_anchor = volatility_20d asc, X = 0.30
```

If 12A7b is rerun and the selected primary simple backbone changes, Direction E must consume the rerun artifact and report the new anchor. It must not hard-code `volatility_20d` unless the artifact says so.

Allowed upstream 12A7b decision states:

```text
12A7b_simple_backbone_supported_low_capacity_not_supported
```

Explicitly unsupported upstream 12A7b state in this requirement:

```text
12A7b_low_capacity_monotone_supported_over_backbone
```

If upstream 12A7b selects `12A7b_low_capacity_monotone_supported_over_backbone`, the fixed anchor is no longer a single-feature simple backbone. Direction E must not approximate a monotone composite anchor with `<feature>__rank_percentile`. It must fail closed for this requirement and route to:

```text
decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
next_allowed_requirement = none
recommended_internal_followup = low_capacity_backbone_chained_stage2_validation
```

If 12A7b does not have a supported phase-1 simple backbone:

```text
decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
```

### 4.3 12A6c row-level inputs

Required row-level inputs:

```text
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_universe.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_targets.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_dictionary.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_pit_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_matrix.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

Optional fallback / cross-check input:

```text
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_row_level_scores.parquet
```

This fallback may be used only if it exists and its schema is explicitly audited. Missing `two_stage_row_level_scores.parquet` must not fail the input gate because the current row-level score and path fields are available from 12A7 / 12A7b local-cache artifacts and 12A6c target/path-cache artifacts.

`stage2_path_cache.parquet` must contain the row-level continuation path labels required to recompute `stage_2_continuation_target`, including:

```text
path_key
instrument
entry_pos
entry_price
stage_2_entry_blocked
stage_2_horizon_complete_20d
continuation_U20_L10_H2_20
```

### 4.4 Matched random inputs

Required random inputs:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
```

Random path labels must be generated by merging random entries with both path caches on:

```text
path_key
instrument
entry_pos
entry_price
```

Cache-side uniqueness:

```text
entry_forward_path_cache.parquet unique on the join key
stage2_path_cache.parquet unique on the join key
```

If either cache has duplicate join keys or a sampled random row has no required cache match:

```text
random_replay_status = fail
input_gate_status = fail
decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
```

## 5. Universe and Denominators

### 5.1 Primary scope

Primary universe:

```text
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage_1_evaluable = true
```

Rows outside this scope must be excluded and counted in `scope_universe_audit.csv`.

### 5.2 Stage-2 path-evaluable survivor denominator

Common stage-2 path-evaluable survivor condition:

```text
no_fast_fail_L10_H20 = true
stage_2_path_evaluable = true
stage_2_entry_blocked = false
stage_2_horizon_complete_20d = true
stage2_label_read_status = pass
stage_2_decision_pos is finite
```

Stage-2 target:

```text
target = stage_2_continuation_target
higher continuation_rate is better
```

`stage2_label_read_status` is a derived status, not an assumed source column. It must be generated by joining the event row to `stage2_path_cache.parquet` on `path_key / instrument / entry_pos / entry_price` or by consuming equivalent audited row-level fields from `simple_backbone_score_matrix.parquet`. It is `pass` only when the row has a unique cache match, is not entry-blocked, has complete 20-day stage-2 horizon, and has a finite/readable `continuation_U20_L10_H2_20` or equivalent `stage_2_continuation_target`.

### 5.3 Decoupled ground-truth survivor denominator

Decoupled denominator:

```text
denominator_type = ground_truth_no_fast_fail_survivor
denominator = primary scope AND common stage-2 path-evaluable survivor condition
stage1_anchor_selected_flag is not used
deployable_at_stage_2_decision_time = false
```

Purpose:

```text
isolate whether stage-2 signal exists after removing stage-1 fast-fail label pollution.
```

This readout is diagnostic-only because it conditions on ground-truth no-fast-fail survival. It must not be interpreted as a deployable entry strategy and must not set `stage2_chained_operating_status`.

### 5.4 Chained stage-1-anchor survivor denominator

Chained denominator:

```text
denominator_type = stage1_anchor_chained_survivor
denominator = primary scope
              AND stage1_anchor_selected_flag = true
              AND common stage-2 path-evaluable survivor condition
deployable_at_stage_2_decision_time = true if all PIT / timing / random replay gates pass
```

`stage1_anchor_selected_flag` must be reconstructed without relying on unpublished 12A7b local-cache columns:

```text
canonical reconstruction source:
  direction_c_decision.csv
  using selected_primary_rule_id / selected_primary_simple_backbone_tuple / selected_primary_X
  plus feature_orientation_json and history policy from the matching selected 12A7b rule row
  plus two_stage_feature_matrix.parquet
  recompute the selected primary simple-backbone PIT trailing rank
  with exactly the same history policy and min-history thresholds recorded by 12A7b

optional cross-check source:
  simple_backbone_score_matrix.parquet
  if stored <anchor_stage1_feature>__rank_percentile / __rank_status exist
  and schema status is pass
```

The implementation must record:

```text
stage1_anchor_reconstruction_status
stage1_anchor_rule_id
stage1_anchor_feature
stage1_anchor_orientation
stage1_anchor_X
stage1_anchor_selected_n_by_split
recomputed_anchor_selected_id_hash
local_cache_anchor_selected_id_hash
publishable_count_reconciliation_status
```

Publishable count reconciliation must compare recomputed `selected_n` by split against `simple_backbone_operating_point_readout.csv` filtered to:

```text
stage = stage_1
rule_id = selected_primary_rule_id
stage1_budget_X = selected_primary_X
split in [train, validation, robustness]
```

If `simple_backbone_operating_point_readout.csv` also provides `split = all`, Direction E should reconcile it as an additional aggregate check. Missing `all` must not fail reconciliation.

If the optional local-cache cross-check is available, it must produce the same selected `meta_event_id` set as canonical reconstruction. If publishable 12A7b selected counts disagree with canonical reconstruction, or if the optional local-cache row-id hash disagrees:

```text
stage1_anchor_reconstruction_status = fail
decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
```

## 6. Stage-2 Candidate Families

### 6.1 Complex stage-2 score

Complex candidate:

```text
candidate_id = complex_stage2_score
score_col = stage2_continuation_score
orientation = desc
source = trailing_rank_score_matrix.parquet primary; optional two_stage_row_level_scores.parquet cross-check only
model_id = imported from upstream artifact
```

No refit is allowed for the canonical complex comparator. If `trailing_rank_score_matrix.parquet` is unavailable, the run must fail closed for complex support unless an explicitly diagnostic-only fallback reproduction is requested and records:

```text
score_reproduction_status
score_source_caveat
score_reproduction_delta
diagnostic_only_if_unbounded_reproduction_error = true
```

### 6.2 Train-frozen single-feature stage-2 challenger

Candidate feature list and orientation:

```text
realized_path_volatility_0_20d descending
realized_max_high_return_0_20d descending
realized_early_window_ret_0_10d descending
realized_ma_5_20_spread_at_day20 descending
distance_to_120d_low descending
```

Feature eligibility:

```text
feature exists in two_stage_feature_matrix.parquet
feature_dictionary.pit_status = pass
feature_pit_audit.pit_status = pass
feature allowed_for_stage_2 = true or stage-specific allowed flag is present and true
feature timestamp <= stage_2_decision_pos information set
```

If a candidate feature lacks a stage-2 PIT proof, it must be excluded with reason:

```text
excluded_stage2_pit_unproven
```

### 6.3 Optional low-capacity stage-2 model

Low-capacity stage-2 models are diagnostic-only in this requirement unless explicitly pre-registered in config:

```text
few-feature logistic regression
low-capacity logistic regression
monotone additive rank score
shallow decision tree diagnostic-only
```

Any model beyond single-feature or imported complex stage-2 score must satisfy:

```text
feature_count <= 3
feature list selected on train only
orientation selected on train only or supplied by pre-registered monotonicity map
no validation / robustness feature selection
model_card records feature_list_hash and train-only selection path
```

## 7. PIT Trailing-rank Rule

Primary history policy:

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
stage_2_global_min_history_n = 250
stage_2_board_min_history_n = 75
```

For each current stage-2 decision row:

```text
rank_frame = denominator-specific full chronological stage-2 frame
rank_history = rows in rank_frame with stage_2_decision_pos < current_stage_2_decision_pos
rank_history must not be split-local
validation / robustness ranks may use prior train / validation rows only if their stage_2_decision_pos is earlier
```

History fallback:

```text
1. Use same-board history if sample_n >= 75.
2. Otherwise use global history if sample_n >= 250.
3. Otherwise rank_status = rank_not_evaluable.
```

Percentile:

```text
midrank_percentile =
  (count(H < s) + 0.5 * count(H = s)) / count(H)
```

For continuation candidates where higher score is better:

```text
keep_flag_X = rank_percentile >= 1 - X
```

Rows with `rank_not_evaluable` are not selectable but remain in `denominator_n`.

Budget grid:

```text
stage2_X_grid = [0.30, 0.50, 0.70]
```

Train-only selection:

```text
For each denominator_type separately:
  select feature / candidate family / X on train only.
  validation and robustness are readout-only.
  selection tie-break:
    highest_train_continuation_rate
    larger_selected_n
    simpler_candidate_family
    feature_name_ASC
    X_ASC
```

`ground_truth_no_fast_fail_survivor` and `stage1_anchor_chained_survivor` may select different stage-2 candidates, but the report must make this explicit. Only the chained selection can contribute to a deployable operating status.

## 8. Random Replay

### 8.1 Decoupled random replay

For `ground_truth_no_fast_fail_survivor`:

```text
random denominator = random_no_fast_fail_L10_H20 = true
                    AND random_stage_2_evaluable = true
                    AND random_stage2_label_read_status = pass
```

Random stage-2 derived fields:

```text
random_stage_2_evaluable =
  random_stage_2_entry_blocked = false
  AND random_stage_2_horizon_complete_20d = true

random_stage2_label_read_status = pass
  iff the random row has a unique cache match,
  random_stage_2_entry_blocked = false,
  random_stage_2_horizon_complete_20d = true,
  and random_stage_2_continuation_target is finite/readable.
```

For each candidate and split:

```text
1. Build candidate selected-count cells by split x board_bucket x calendar_month.
2. For each random seed, draw exactly the same selected_n per cell
   from random denominator rows.
3. Compute random_stage_2_continuation_target rate per seed.
4. Report random_p05 / random_p50 / random_p95 from valid seeds.
```

Within each random selected-count cell, sampling must be reproducible after a stable ordering by:

```text
replacement_draw_index
sample_draw_id
instrument
random_trade_open_date
path_key
```

`random_stage2_selected.parquet` must record these ordering columns plus `retention_rank_rule`. If a legacy random input lacks `replacement_draw_index` or `sample_draw_id`, Direction E must derive deterministic equivalents from the audited input row order and record `retention_rank_rule = derived_from_input_row_order`.

### 8.2 Chained two-step random replay

For `stage1_anchor_chained_survivor`, random replay must preserve the two-stage path:

```text
Step 1. Stage-1 anchor random keep:
  For each split x board_bucket x calendar_month,
  draw exactly the same stage1_anchor_selected_n as the real stage-1 anchor
  from random_stage_1_evaluable rows.

Step 2. Random survivor denominator:
  Restrict step-1 random keep rows to:
    random_no_fast_fail_L10_H20 = true
    random_stage_2_evaluable = true
    random_stage2_label_read_status = pass

Step 3. Stage-2 candidate random selected count:
  For each split x board_bucket x calendar_month,
  draw exactly the same stage2 selected_n as the candidate
  from the step-2 random survivor denominator.
  Use the same stable retention ordering columns defined in 8.1.

Step 4. Compute random_stage_2_continuation_target rate per seed.
```

Required seed validity:

```text
valid_seed_n >= 100
every candidate selected-count cell has sampled_random_n = requested_selected_n
stage1 random keep counts match exactly
stage2 random selected counts match exactly
random_stage2_label_read_status = pass
```

If any selected-count cell cannot be replayed exactly for enough seeds:

```text
random_replay_status = fail
decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
```

## 9. Metrics

Required readout for every candidate, denominator_type, X, and split:

```text
denominator_type
deployable_at_stage_2_decision_time
stage
split
candidate_id
candidate_family
single_feature_comparison_role
complex_comparison_role
feature_list
feature_orientation_json
feature_list_hash
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_anchor_rule_id
stage1_anchor_selected_n
stage2_budget_X
denominator_n
rank_evaluable_n
rank_not_evaluable_n
denominator_positive_n
rank_evaluable_positive_n
selected_n
selected_positive_n
selected_budget_total
selected_budget_rank_evaluable
selected_continuation_rate
base_continuation_rate
delta_vs_base
random_p05
random_p50
random_p95
delta_vs_random_p50
delta_vs_random_p50_ci95_low
delta_vs_random_p50_ci95_high
single_feature_matched_rate
delta_vs_single_feature
delta_vs_single_feature_ci95_low
delta_vs_single_feature_ci95_high
complex_model_matched_rate
delta_vs_complex_model
delta_vs_complex_model_ci95_low
delta_vs_complex_model_ci95_high
bootstrap_denominator_positive_n
bootstrap_replicate_valid_n
rank_not_evaluable_rate
budget_abs_delta_total_vs_X
budget_abs_delta_rank_evaluable_vs_X
readout_status
diagnostic_only_flag
```

Direction:

```text
selected_continuation_rate higher is better
delta_vs_random_p50 > 0 is better
delta_vs_single_feature > 0 means candidate beats train-frozen single-feature
delta_vs_complex_model > 0 means candidate beats imported complex stage-2 score
```

Comparator role semantics:

```text
For candidate_family = single_feature_stage2:
  single_feature_comparison_role = self
  single_feature_matched_rate = NA
  delta_vs_single_feature = NA
  delta_vs_single_feature_ci95_low / high = NA

For candidate_family = complex_stage2_score:
  single_feature_comparison_role = matched_challenger
  single_feature_matched_rate = continuation rate of the train-frozen single-feature challenger
  computed on the same denominator, split, X, and selected_n cells.

For any single-feature row that also reports complex comparator diagnostics:
  complex_comparison_role = matched_complex
  complex_model_matched_rate is the imported complex score selected at the same selected_n cells.

For rows without a meaningful paired comparator:
  *_comparison_role = not_applicable
  corresponding matched-rate and delta fields = NA
```

Base-rate definition:

```text
base_continuation_rate = denominator_positive_n / denominator_n
delta_vs_base = selected_continuation_rate - base_continuation_rate

For paired/common-denominator comparator readouts:
  base_continuation_rate must be recomputed on the same common denominator used by that row.
```

## 10. Statistical Gates

Bootstrap settings:

```text
seed = 120712
n_resamples >= 2000
ci_low_q = 0.025
ci_high_q = 0.975
bootstrap_min_denominator_positive_n = 30
bootstrap_min_valid_replicates = 1500
```

Random CI:

```text
Use nested random-seed bootstrap.
Each replicate must resample candidate events and valid random seeds,
then recompute random p50 from the resampled seed distribution.

Canonical fields:
  delta_vs_random_p50_ci95_low / high =
    bootstrap CI of candidate_continuation_rate - random_p50
```

Paired comparator CI:

```text
Use paired event bootstrap on the common denominator.

Canonical fields:
  delta_vs_single_feature_ci95_low / high =
    bootstrap CI of candidate_continuation_rate - single_feature_matched_rate

  delta_vs_complex_model_ci95_low / high =
    bootstrap CI of candidate_continuation_rate - complex_model_matched_rate
```

Decoupled signal is positive if robustness satisfies all:

```text
denominator_type = ground_truth_no_fast_fail_survivor
selected_n >= 150
denominator_positive_n >= 30
bootstrap_replicate_valid_n >= 1500
delta_vs_random_p50 >= +0.02
delta_vs_random_p50_ci95_low > 0
rank_not_evaluable_rate <= 0.05
```

Chained single-feature selector is supported if robustness satisfies all:

```text
denominator_type = stage1_anchor_chained_survivor
candidate_family = single_feature_stage2
selected_n >= 150
denominator_positive_n >= 30
bootstrap_replicate_valid_n >= 1500
delta_vs_random_p50 >= +0.02
delta_vs_random_p50_ci95_low > 0
rank_not_evaluable_rate <= 0.05
budget_abs_delta_rank_evaluable_vs_X <= 0.10
```

Chained complex stage-2 selector is supported only if robustness satisfies all:

```text
denominator_type = stage1_anchor_chained_survivor
candidate_family = complex_stage2_score
selected_n >= 150
denominator_positive_n >= 30
bootstrap_replicate_valid_n >= 1500
delta_vs_random_p50 >= +0.02
delta_vs_random_p50_ci95_low > 0
delta_vs_single_feature >= +0.01
delta_vs_single_feature_ci95_low > 0
rank_not_evaluable_rate <= 0.05
budget_abs_delta_rank_evaluable_vs_X <= 0.10
```

If complex stage-2 beats random but not single-feature, the status is simple-selector supported or partial, not complex supported.

Status fields:

```text
stage2_decoupled_signal_status values:
  positive
  partial
  not_supported
  blocked

stage2_chained_operating_status values:
  complex_supported
  simple_selector_supported
  decoupled_only_chained_not_supported
  partial
  not_supported
  blocked
```

Status derivation:

```text
stage2_decoupled_signal_status = blocked
  if input / PIT / leakage / random / split-boundary / stage1-anchor gate fails.

stage2_decoupled_signal_status = positive
  if the robustness row for ground_truth_no_fast_fail_survivor passes all decoupled signal gates.

stage2_decoupled_signal_status = partial
  if point estimates beat random but sample, CI, rank-evaluable, or budget-quality gates fail.

stage2_decoupled_signal_status = not_supported
  otherwise.

stage2_chained_operating_status = blocked
  if any mandatory gate fails before chained evaluation.

stage2_chained_operating_status = complex_supported
  only if stage2_decoupled_signal_status = positive
  and chained complex stage-2 support gates pass.

stage2_chained_operating_status = simple_selector_supported
  only if stage2_decoupled_signal_status = positive
  and chained single-feature support gates pass
  while complex-vs-single-feature support does not pass.

stage2_chained_operating_status = decoupled_only_chained_not_supported
  if stage2_decoupled_signal_status = positive
  but no chained selector passes support gates.

stage2_chained_operating_status = partial
  if chained point estimates are favorable but support gates fail,
  or if chained robustness support gates pass while stage2_decoupled_signal_status = partial.

stage2_chained_operating_status = not_supported
  otherwise.
```

The dependency on `stage2_decoupled_signal_status = positive` is intentional. Decoupled positive is the requirement's guard that stage-2 continuation signal exists among true no-fast-fail survivors independent of the stage-1 anchor. If decoupled is only `partial` while chained robustness appears strong, Direction E must report this as diagnostic-only / partial rather than supported, because the deployable chained result may be driven by anchor-induced denominator composition rather than a stable stage-2 continuation signal.

## 11. Opportunity-cost Audit

Direction E must quantify whether the stage-1 defensive anchor sacrifices continuation:

```text
ground_truth_survivor_n
ground_truth_survivor_continuation_rate
stage1_anchor_chained_survivor_n
stage1_anchor_chained_survivor_continuation_rate
chained_survivor_share_of_ground_truth_survivors
continuation_rate_delta_chained_vs_ground_truth
continuation_positive_capture_rate
fast_fail_reduction_from_stage1_anchor
```

Required interpretation fields:

```text
stage1_defense_opportunity_cost_status

values:
  no_material_continuation_cost
  continuation_cost_but_stage2_recoverable
  continuation_cost_not_recovered_by_stage2
  insufficient_stage2_sample
```

This audit is not a support gate by itself, but it must be called out in the report and in `direction_e_decision.csv`.

## 12. Stability Diagnostics

Required slices:

```text
split
calendar_year
board_bucket
primary_family_id
calendar_month
stage1_anchor_selected_flag
```

For each slice with `selected_n >= 100`, report:

```text
selected_n
selected_continuation_rate
base_continuation_rate
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
pass = selected_continuation_rate > base_continuation_rate and selected_continuation_rate > random_p50
weak = selected_continuation_rate > base_continuation_rate but not > random_p50
fail = selected_continuation_rate <= base_continuation_rate
insufficient_n = selected_n < 100
```

Sign inversion or slope collapse in robustness must be called out in the report. Validation instability is a stress warning, not a hard blocker unless it reveals PIT leakage, stage-1 anchor reconstruction failure, or input corruption.

## 13. Required Outputs

All publishable tables go under:

```text
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/
```

Required tables:

```text
input_artifact_audit.csv
scope_universe_audit.csv
stage1_anchor_rule_card.csv
stage2_candidate_card.csv
stage2_train_selection.csv
stage2_ground_truth_survivor_readout.csv
stage2_chained_trailing_rank_readout.csv
stage2_random_same_budget_audit.csv
stage2_single_feature_challenger.csv
stage2_complex_model_matched_comparator.csv
stage2_budget_drift_audit.csv
stage2_opportunity_cost_audit.csv
stage2_stability_slice_audit.csv
direction_e_decision.csv
```

`direction_e_decision.csv` required fields:

```text
decision_state
input_gate_status
stage1_anchor_reconstruction_status
stage2_decoupled_signal_status
stage2_chained_operating_status
stage1_anchor_rule_id
stage1_anchor_feature
stage1_anchor_orientation
stage1_anchor_X
selected_decoupled_candidate_id
selected_decoupled_candidate_family
selected_decoupled_X
selected_chained_candidate_id
selected_chained_candidate_family
selected_chained_X
selected_chained_deployable_at_stage_2_decision_time
stage1_defense_opportunity_cost_status
gate_failure_reasons
next_allowed_requirement
recommended_internal_followup
```

Report:

```text
outputs/publishable/reports/stage2_decoupling_chained_readouts_report.md
```

Manifest:

```text
outputs/manifests/12A7c_direction_e_stage2_decoupling_chained_readouts_manifest.json
```

Local cache:

```text
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_decoupling_score_matrix.parquet
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/bootstrap_replicates.parquet
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/random_stage2_selected.parquet
```

## 14. Decision Map

Decision states:

```text
12A7c_stage2_chained_complex_supported:
  decoupled signal is positive;
  chained complex stage-2 selector beats random and train-frozen single-feature
  on robustness with CI support.

12A7c_stage2_chained_simple_selector_supported:
  decoupled signal is positive;
  chained train-frozen single-feature stage-2 selector beats random on robustness;
  complex stage-2 selector does not significantly beat that single-feature selector.

12A7c_stage2_decoupled_only_chained_not_supported:
  ground-truth survivor denominator shows stage-2 signal;
  chained denominator after stage-1 anchor fails random / sample / CI / budget gates.

12A7c_stage2_diagnostic_only:
  stage-2 point estimates are promising but sample size, positive_n, CI width,
  rank-evaluable coverage, random replay quality, or the decoupled-positive
  guard blocks support.

12A7c_no_stage2_signal:
  neither decoupled nor chained robustness readout beats matched random with the required margin.
  This state must not be used when chained support gates pass but decoupled signal is not positive;
  that boundary state is diagnostic-only.

12A7c_blocked_input_or_stage1_anchor_failure:
  required input, PIT, leakage, random, split-boundary, or stage-1 anchor reconstruction gate fails.
```

Decision precedence:

```text
1. If input / PIT / leakage / random / split-boundary / stage1-anchor gate fails:
     decision_state = 12A7c_blocked_input_or_stage1_anchor_failure

2. Else evaluate decoupled ground-truth survivor signal.

3. Else evaluate chained deployable stage-2 readout after the fixed stage-1 anchor.

4. If stage2_decoupled_signal_status = positive
   and chained complex stage-2 selector beats random and single-feature:
     decision_state = 12A7c_stage2_chained_complex_supported

5. Else if stage2_decoupled_signal_status = positive
   and chained single-feature selector beats random:
     decision_state = 12A7c_stage2_chained_simple_selector_supported

6. Else if stage2_decoupled_signal_status = positive but chained readout fails:
     decision_state = 12A7c_stage2_decoupled_only_chained_not_supported

7. Else if stage2_decoupled_signal_status in [partial, not_supported]
   and chained support gates pass:
     decision_state = 12A7c_stage2_diagnostic_only

8. Else if point estimates are favorable but gates fail:
     decision_state = 12A7c_stage2_diagnostic_only

9. Else:
     decision_state = 12A7c_no_stage2_signal
```

`next_allowed_requirement` mapping:

```text
if decision_state = 12A7c_stage2_chained_complex_supported:
  next_allowed_requirement = requirement_12a8_probability_calibration_prior_shift_audit.md
  recommended_internal_followup = two_stage_rank_policy_replay_after_calibration

if decision_state = 12A7c_stage2_chained_simple_selector_supported:
  next_allowed_requirement = none
  recommended_internal_followup = simple_stage2_backbone_policy_replay

if decision_state = 12A7c_stage2_decoupled_only_chained_not_supported:
  next_allowed_requirement = none
  recommended_internal_followup = stage1_stage2_objective_tradeoff_review

if decision_state in [
  12A7c_stage2_diagnostic_only,
  12A7c_no_stage2_signal
]:
  next_allowed_requirement = requirement_12a9_vol_scaled_label_stability_and_separability_audit.md
  recommended_internal_followup = label_or_denominator_revision_before_stage2_policy

if decision_state starts with 12A7c_blocked:
  next_allowed_requirement = none
  recommended_internal_followup = gate_specific_failure_triage
```

## 15. Report Requirements

The report must lead with:

```text
final decision
stage2_decoupled_signal_status
stage2_chained_operating_status
stage1 anchor tuple and X
decoupled robustness selected_n / continuation_rate / random_p50 / CI
chained robustness selected_n / continuation_rate / random_p50 / CI
single-feature challenger result
complex-vs-single-feature paired result
opportunity-cost audit summary
validation stress warning
recommended next step
```

The report must explicitly state:

```text
Ground-truth survivor decoupled readout is diagnostic-only and not deployable.
Chained readout is deployable at stage-2 decision time only after the fixed stage-1 anchor has selected the row and no-fast-fail survival is observable; it is not a t0-entry deployable strategy.
No stage-2 feature, orientation, X, or model capacity was chosen using validation or robustness.
The conclusion applies only to C0 risk_on events and the current continuation target.
```

Required findings:

```text
1. Whether stage-2 signal exists after removing stage-1 denominator pollution.
2. Whether stage-1 simple backbone suppresses continuation opportunity.
3. Whether a stage-2 selector can recover continuation on the chained denominator.
4. Whether complex stage-2 score beats a train-frozen single-feature stage-2 backbone.
5. Whether the next research step is calibration, policy replay, or label/denominator revision.
```

## 16. Implementation Checklist

Implementation must include tests for:

1. Input artifact audit records every required input with sha256 and schema status.
2. 12A7b stage-1 anchor reconstruction matches publishable selected counts and, when optional local-cache row ids are available, exactly matches those selected ids.
3. Decoupled denominator ignores `stage1_anchor_selected_flag`.
4. Chained denominator requires both `stage1_anchor_selected_flag = true` and observable no-fast-fail survivor status.
5. Stage-2 PIT ranks use only prior `stage_2_decision_pos` rows and are not split-local.
6. Stage-2 feature candidates without PIT proof are excluded fail-closed.
7. Random decoupled replay exactly matches selected_n by split x board_bucket x calendar_month.
8. Random chained replay performs exact two-step stage-1 keep then stage-2 select matching.
9. Validation and robustness never influence feature, X, candidate family, history policy, or label choice.
10. Bootstrap CI fields are present and use canonical direction where continuation higher is better.
11. Decision map precedence is exclusive.
12. Chained support gates enforce `budget_abs_delta_rank_evaluable_vs_X <= 0.10`.
13. Random chained replay verifies both stage-1 random keep counts and stage-2 random selected counts exactly by split x board_bucket x calendar_month.
14. Complex-vs-single-feature paired CI uses `candidate_continuation_rate - single_feature_matched_rate`; sign reversal must fail tests.
15. Decoupled rows ignore `stage1_anchor_selected_flag`, while chained rows require both `stage1_anchor_selected_flag = true` and observable survivor status.
16. `simple_backbone_score_matrix.parquet` missing optional columns triggers 12A6c reconstruction fallback, not input-gate failure.
17. Upstream `12A7b_low_capacity_monotone_supported_over_backbone` routes to `low_capacity_backbone_chained_stage2_validation` and does not approximate composite scores with a single-feature percentile.
18. Report and manifest hashes are synchronized.

## 17. One-line Thesis

12A7c Direction E separates the question "does continuation signal exist among true survivors?" from the deployable question "does a stage-2 selector still work after the fixed stage-1 defensive backbone?", so that the project can stop confusing downside rejection with right-tail continuation selection.
