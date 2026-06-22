# 需求：12A7d Stage-2 Random Baseline Support Triage

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
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、stage-1 anchor 不可证明、stage-2 candidate selection 不可复现、random path label 不可复现时 fail closed。
6. 本需求唯一允许承接的上游失败类型是 12A7c 的 random replay construction failure。其他上游失败不得被 12A7d “放宽修复”。
7. 不得从报告文本或聚合表反推出事件、标签、特征、stage-1 keep flag、stage-2 score 或 random path label。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7d
run_id = 12A7d_stage2_random_baseline_support_triage
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7d_stage2_random_baseline_support_triage.py
expected_config = configs/config_12a7d_stage2_random_baseline_support_triage.yaml
expected_test_file = tests/test_12a7d_stage2_random_baseline_support_triage.py
research_plan_source = research_plan_2_stage2_random_baseline_and_defense_participation.md
upstream_requirement = requirement_12a7c_direction_e_stage2_decoupling_chained_readouts.md
```

本需求实现 `research_plan_2_stage2_random_baseline_and_defense_participation.md` 第 4 节：

```text
12A7d: Random Baseline Support Triage
```

12A7d 的目标不是重新选择 stage-2 模型，而是回答：

```text
Q1. 12A7c 的 chained stage-2 fail 是 continuation signal failure，
    还是 strict exact matched random baseline construction failure？

Q2. 在预注册 random baseline variants 下，哪些 null 能被构造，
    它们各自允许多强的解释？

Q3. 如果 strict null 不可构造，近严格或诊断 null 是否只支持
    directional sensitivity，而不是 deployable support？
```

## 2. 背景与核心修正

12A7c 已完成的实跑结论：

```text
stage-1 anchor = volatility_20d asc, X = 0.30
selected_chained_candidate_id = complex_stage2_score
selected_chained_X = 0.30
stage1_anchor_reconstruction_status = pass
gate_failure_reasons = decoupled_random_replay_failed;chained_random_replay_failed
```

12A7c 的 random replay 失败机制是 strict exact cell replay 过脆：

```text
for each seed:
  every split x board_bucket x calendar_month cell must have enough random rows
  otherwise the entire seed is invalid
```

已知表现：

```text
decoupled valid_seed_n = 29 / 100
chained valid_seed_n = 0 / 100
robustness chained selected_n ~= 279
robustness chained selected_positive_n ~= 36
```

这些数字只能作为本需求的动机。12A7d 必须从 row-level artifacts 重新构造 candidate rows、random rows、cell support、variant random rates 和 bootstrap CI。

核心修正：

```text
old framing:
  strict exact random replay failure blocks every stage-2 conclusion.

new framing:
  strict exact replay remains the strongest fail-closed benchmark;
  additional pre-registered variants diagnose whether the block is a
  baseline support problem or a true signal problem;
  weaker random nulls never become equivalent to the strict null.
```

Hard interpretation rule:

```text
Evidence strength strictly decreases as the random null becomes coarser:

strict_exact_cell_replay
  > hierarchical_month_quarter_replay
  > hierarchical_split_board_fallback_replay
  > pooled_cell_weighted_replay
  > with_replacement_replay

A win under a coarser null is not equivalent to a win under the strict null.
Coarser variants can show directional sensitivity, but cannot by themselves
prove deployable support.
```

Variant results must not be aggregated by taking the best result. Each variant is interpreted independently, and the final decision must report the strongest accepted null and the weakest accepted null that still supports the stated claim.

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不重新定义 fast-fail / continuation label，不做 vol-scaled barrier；
- 不重新训练 stage-1 或 stage-2 模型；
- 不重新选择 stage-1 anchor feature、orientation、X 或 history policy；
- 不用 validation 或 robustness 回头选择 stage-2 feature、candidate family、X、baseline variant 或 cell fallback；
- 不把 baseline variant 跑出来的最好结果当作最终结论；
- 不把 pooled 或 replacement random null 的胜出解释为 deployable support；
- 不把 decoupled ground-truth survivor readout 当作可部署策略；
- 不做 12A7e defense-participation frontier；
- 不做 policy replay、仓位、交易成本、slippage、资金曲线或组合回放；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不声明可交易 alpha。

## 4. 必需输入

### 4.1 12A7c frozen outputs

必需输入：

```text
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/input_artifact_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/scope_universe_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage1_anchor_rule_card.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_candidate_card.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_train_selection.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_ground_truth_survivor_readout.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_chained_trailing_rank_readout.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_random_same_budget_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_single_feature_challenger.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_complex_model_matched_comparator.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_budget_drift_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_opportunity_cost_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/direction_e_decision.csv
outputs/publishable/reports/stage2_decoupling_chained_readouts_report.md
outputs/manifests/12A7c_direction_e_stage2_decoupling_chained_readouts_manifest.json
```

12A7c row-level local cache:

```text
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_decoupling_score_matrix.parquet
```

Optional diagnostic input:

```text
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/random_stage2_selected.parquet
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/bootstrap_replicates.parquet
```

`random_stage2_selected.parquet` may be used to reconcile the original strict 12A7c failure, but it must not be the source for coarser variants because it is already a selected replay artifact. Coarser variants must read the canonical random source in §4.3.

### 4.2 Required 12A7c gate

12A7d may proceed only when 12A7c failed for random replay construction and not for lineage, PIT, split, label, or anchor reasons.

Allowed upstream state:

```text
direction_e_decision.stage1_anchor_reconstruction_status = pass
direction_e_decision.selected_chained_deployable_at_stage_2_decision_time = true
direction_e_decision.selected_chained_candidate_id is not null
direction_e_decision.selected_chained_X is not null
direction_e_decision.gate_failure_reasons subset of [
  decoupled_random_replay_failed,
  chained_random_replay_failed
]
```

`gate_failure_reasons` is now a required 12A7c `direction_e_decision.csv` field. If a legacy 12A7c artifact predates that schema freeze and lacks the column, 12A7d may use the following fallback only after recording `gate_failure_reasons_source = inferred_legacy_12A7c_artifact` in `input_artifact_audit.csv` and `stage2_chained_sensitivity_decision.csv`:

```text
legacy fallback allowed only if all are true:
  direction_e_decision.decision_state = 12A7c_blocked_input_or_stage1_anchor_failure
  direction_e_decision.stage1_anchor_reconstruction_status = pass
  direction_e_decision.stage2_decoupled_signal_status = blocked
  direction_e_decision.stage2_chained_operating_status = blocked
  direction_e_decision.selected_chained_deployable_at_stage_2_decision_time = true
  selected decoupled and chained rows exist in the 12A7c readout tables
  selected decoupled/chained readout_status values are random_replay_failed

legacy fallback forbidden if any available 12A7c artifact reports:
  stage1_anchor_reconstruction_status != pass
  PIT / split-boundary / label / score reconstruction failure
  missing selected candidate identity
  missing selected candidate selected_n or selected_positive_n
```

`direction_e_decision.input_gate_status = fail` is allowed only under the subset rule or the legacy fallback above. Any additional failure reason must fail closed:

```text
decision_state = 12A7d_blocked_input_or_lineage_failure
```

### 4.3 Canonical random source inputs

Required random source:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
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

Required cache schema checks:

```text
entry_forward_path_cache.parquet must contain:
  path_key
  instrument
  entry_pos
  entry_price
  entry_blocked
  horizon_complete_20d
  time_to_lower_minus_10_20d

stage2_path_cache.parquet must contain:
  path_key
  instrument
  entry_pos
  entry_price
  stage_2_entry_blocked
  stage_2_horizon_complete_20d
  continuation_U20_L10_H2_20
```

These columns must be proven by the corresponding 12A6b / 12A6c manifest schema when available, and the direct file schema must always be checked in `input_artifact_audit.csv`. Missing, renamed, or type-incompatible cache columns are `random_source_status = fail`.

If either cache has duplicate join keys, or if a sampled random row has no required cache match:

```text
random_source_status = fail
input_gate_status = fail
decision_state = 12A7d_blocked_input_or_lineage_failure
```

Required random derived fields:

```text
random_stage_1_evaluable
random_no_fast_fail_L10_H20
random_stage_2_entry_blocked
random_stage_2_horizon_complete_20d
random_stage_2_continuation_target
random_stage_2_evaluable
random_stage2_label_read_status
```

Definitions:

```text
random_stage1_label_join_status = pass
  iff the random row has a unique `entry_forward_path_cache.parquet` match
  on path_key / instrument / entry_pos / entry_price.

random_stage_1_evaluable =
  random_stage1_label_join_status = pass
  AND entry_blocked = false
  AND horizon_complete_20d = true

random_no_fast_fail_L10_H20 =
  random_stage_1_evaluable = true
  AND time_to_lower_minus_10_20d is null

random_stage2_label_join_status = pass
  iff the random row has a unique `stage2_path_cache.parquet` match
  on path_key / instrument / entry_pos / entry_price.

random_stage_2_evaluable =
  random_stage2_label_join_status = pass
  AND random_stage_2_entry_blocked = false
  AND random_stage_2_horizon_complete_20d = true

random_stage2_label_read_status = pass
  iff random_stage2_label_join_status = pass,
  random_stage_2_entry_blocked = false,
  random_stage_2_horizon_complete_20d = true,
  and continuation_U20_L10_H2_20 is finite/readable.

random_stage_2_continuation_target =
  bool(continuation_U20_L10_H2_20)
```

## 5. Frozen Candidate and Denominator Contract

### 5.1 Candidate identity

12A7d must freeze stage-2 candidates from 12A7c. It must not perform new train selection.

Primary chained candidate:

```text
source = direction_e_decision.csv
denominator_type = stage1_anchor_chained_survivor
candidate_id = selected_chained_candidate_id
candidate_family = selected_chained_candidate_family
stage2_budget_X = selected_chained_X
stage1_anchor_rule_id = stage1_anchor_rule_id
stage1_anchor_feature = stage1_anchor_feature
stage1_anchor_orientation = stage1_anchor_orientation
stage1_anchor_X = stage1_anchor_X
```

Optional decoupled diagnostic candidate:

```text
source = direction_e_decision.csv
denominator_type = ground_truth_no_fast_fail_survivor
candidate_id = selected_decoupled_candidate_id
candidate_family = selected_decoupled_candidate_family
stage2_budget_X = selected_decoupled_X
diagnostic_only_flag = true
```

Decoupled rows are diagnostic-only in every output. They may explain whether continuation ranking signal exists among true no-fast-fail survivors, but they must not enter `decision_state`, `strongest_accepted_null`, `weakest_accepted_null_that_supports_claim`, or `next_allowed_requirement`.

If `stage2_train_selection.csv` contains additional `selection_status = selected_train_frozen` rows for these denominator types, 12A7d may include them as secondary readouts. They must be labeled:

```text
selection_role = secondary_frozen_12A7c_readout
```

Secondary rows cannot override the primary chained decision.

### 5.2 Candidate row reconstruction

Canonical candidate row source:

```text
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_decoupling_score_matrix.parquet
```

Required columns:

```text
meta_event_id
instrument
event_t0_date
event_t0_pos
split
board_bucket
calendar_month
stage_2_decision_pos
path_key
stage_2_continuation_target
stage2_label_read_status
no_fast_fail_L10_H20
stage_2_path_evaluable
stage_2_entry_blocked
stage_2_horizon_complete_20d
stage1_anchor_selected_flag
stage1_anchor_rank_status
stage2_continuation_score
<selected single-feature columns if selected by 12A7c>
```

Optional candidate survivor-label fallback:

```text
If stage2_decoupling_score_matrix.parquet lacks any of:
  no_fast_fail_L10_H20
  stage_2_path_evaluable
  stage_2_entry_blocked
  stage_2_horizon_complete_20d

then 12A7d may reconstruct only those survivor-condition fields from the
canonical path caches using this source map:

  no_fast_fail_L10_H20:
    outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
    source fields = entry_blocked, horizon_complete_20d, time_to_lower_minus_10_20d

  stage_2_path_evaluable:
    outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
    source fields = stage_2_entry_blocked, stage_2_horizon_complete_20d

  stage_2_entry_blocked:
    outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
    source field = stage_2_entry_blocked

  stage_2_horizon_complete_20d:
    outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
    source field = stage_2_horizon_complete_20d

Fallback is allowed only if stage2_decoupling_score_matrix.parquet contains
an audited join key sufficient to join the path caches without ambiguity:
  path_key
  instrument
  entry_pos
  entry_price

If the score matrix lacks the survivor columns and lacks the full audited
path-cache join key, `candidate_reconciliation_status = fail` and the run
must fail closed.

Fallback may not be used to reconstruct stage-2 score, candidate identity,
rank, selected flag, or target values that are already frozen by 12A7c.
```

Primary scope:

```text
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage_1_evaluable = true
```

Common stage-2 path-evaluable survivor condition:

```text
no_fast_fail_L10_H20 = true
stage_2_path_evaluable = true
stage_2_entry_blocked = false
stage_2_horizon_complete_20d = true
stage2_label_read_status = pass
stage_2_decision_pos is finite
```

Denominators:

```text
ground_truth_no_fast_fail_survivor =
  primary scope
  AND common stage-2 path-evaluable survivor condition

stage1_anchor_chained_survivor =
  primary scope
  AND stage1_anchor_selected_flag = true
  AND common stage-2 path-evaluable survivor condition
```

The implementation must recompute the frozen candidate stage-2 PIT trailing-rank selection using the same 12A7c rank rule, then reconcile by split against 12A7c publishable readouts. If recomputed `selected_n`, `selected_positive_n`, or `selected_budget_rank_evaluable` differs from the corresponding 12A7c row beyond exact integer equality for counts or `1e-12` for rates:

```text
candidate_reconciliation_status = fail
decision_state = 12A7d_blocked_input_or_lineage_failure
```

### 5.3 PIT rank rule

The PIT rank rule is inherited from 12A7c:

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
validation / robustness ranks may use prior train / validation rows only if earlier in time
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

## 6. Random Baseline Variants

Every baseline variant must be pre-registered in config and emitted independently.

| baseline_id | baseline_family_id | null_strength_rank | definition | allowed conclusion |
|---|---|---:|---|---|
| `strict_exact_cell_replay` | `strict_exact_cell_replay` | 1 | exact split x board_bucket x calendar_month replay, no replacement, every requested cell must pass for a seed to be valid | original fail-closed benchmark; can support deployable claim if robustness gates pass |
| `hierarchical_month_quarter_replay` | `hierarchical_cell_replay` | 2 | month cell first, then same split x board_bucket x calendar_quarter if month is short | primary sensitivity with baseline caveat if no split x board fallback is used |
| `hierarchical_split_board_fallback_replay` | `hierarchical_cell_replay` | 3 | split x board_bucket fallback after month and quarter are short | diagnostic only |
| `pooled_cell_weighted_replay` | `pooled_cell_weighted_replay` | 4 | exact-cell weighted replay using requested cell weights, without invalidating the whole seed when some cells are short | sensitivity / diagnostic only |
| `with_replacement_replay` | `with_replacement_replay` | 5 | exact-cell replay allowing replacement inside sparse cells and reporting duplicate / effective-n diagnostics | diagnostic only unless a later requirement adds variance correction |

### 6.1 Strict exact cell replay

Cell key:

```text
split
board_bucket
calendar_month
```

For each candidate, denominator type, split, and seed:

```text
1. Build candidate selected-count cells by split x board_bucket x calendar_month.
2. Draw exactly requested_selected_n random rows in every cell.
3. Do not draw with replacement.
4. A seed is valid only if every requested cell has sampled_random_n = requested_selected_n.
5. Compute random_stage_2_continuation_target rate per valid seed.
```

Required pass condition:

```text
valid_seed_n >= min_random_seed_n
all requested cells pass
baseline_construction_status = pass
```

### 6.2 Hierarchical cell replay

Fallback order:

```text
level_1 = split x board_bucket x calendar_month
level_2 = split x board_bucket x calendar_quarter
level_3 = split x board_bucket
```

Two hierarchical variants must be emitted separately:

```text
baseline_id = hierarchical_month_quarter_replay
  allowed fallback levels = [level_1, level_2]
  if level_2 is short, the requested cell fails for that seed.

baseline_id = hierarchical_split_board_fallback_replay
  allowed fallback levels = [level_1, level_2, level_3]
  if level_3 is used anywhere, the row is diagnostic-only.
```

For each requested candidate cell:

```text
1. Process requested cells in deterministic order:
     split ASC,
     board_bucket ASC,
     calendar_month ASC,
     replay_step ASC,
     candidate_id ASC,
     stage2_budget_X ASC.
2. Try level_1 for the same seed after excluding rows already sampled
   in the same seed x replay_step x baseline_id.
3. If available_random_n < requested_selected_n, try level_2 after the
   same exclusion.
4. If the active baseline_id permits level_3 and level_2 is still short,
   try level_3 after the same exclusion.
5. If the active baseline_id does not permit the needed fallback level,
   or if the final allowed level is short, the cell fails for that seed.
6. Record realized_cell_grain for every sampled cell.
```

Interpretation:

```text
if baseline_id = hierarchical_month_quarter_replay
and every sampled cell uses level_1 or level_2:
  allowed_interpretation = sensitivity_with_baseline_caveat
  calendar_dimension_preserved_flag = true

if baseline_id = hierarchical_split_board_fallback_replay
or any sampled cell uses level_3:
  allowed_interpretation = diagnostic_only
  calendar_dimension_preserved_flag = false
```

The board dimension must always be preserved. Any fallback that drops `board_bucket` is forbidden in this requirement.

No-replacement rule:

```text
For strict_exact_cell_replay, hierarchical_month_quarter_replay,
hierarchical_split_board_fallback_replay, and pooled_cell_weighted_replay,
the same random_row_uid must not be sampled twice within the same:

seed x replay_step x denominator_type x candidate_id x stage2_budget_X x baseline_id

Using a row in `stage_1_keep` and then again in `stage_2_select` is allowed
only because stage-2 selection is a subset of the already kept stage-1 rows;
it must be recorded with stage1_keep_selected_flag = true and does not count
as a duplicate within a replay step.
```

### 6.3 Pooled cell weighted replay

Pooled weighted replay keeps the candidate cell composition as weights instead of requiring every seed to satisfy every cell.

For each seed:

```text
1. Use exact split x board_bucket x calendar_month cells.
2. For every requested cell with available_random_n > 0,
   draw min(requested_selected_n, available_random_n) rows without replacement.
3. Compute cell_rate from sampled rows.
4. Restrict candidate rows to the same supported requested cells and compute:
     candidate_supported_cell_selected_n
     candidate_supported_cell_positive_n
     candidate_supported_cell_continuation_rate
5. Compute weighted_random_rate =
     sum(requested_selected_n * cell_rate for supported cells)
     / sum(requested_selected_n for supported cells)
6. Compute pooled delta fields against `candidate_supported_cell_continuation_rate`,
   not against the full frozen candidate continuation rate.
7. Report supported_requested_n and unsupported_requested_n.
```

Seed validity:

```text
supported_requested_n / total_requested_n >= pooled_min_supported_weight_share
effective_seed_n >= pooled_min_effective_seed_n
```

Pooled replay must report shortfall explicitly and is diagnostic-only unless it confirms a stricter accepted null. The full frozen candidate continuation rate must still be reported as `full_candidate_continuation_rate`, but it must not feed pooled delta or CI fields.

### 6.4 With-replacement replay

For each exact split x board_bucket x calendar_month cell:

```text
if available_random_n >= requested_selected_n:
  draw without replacement
elif 0 < available_random_n < requested_selected_n:
  draw with replacement until requested_selected_n is reached
else:
  cell fails for that seed
```

Required diagnostics:

```text
replacement_draw_n
duplicate_random_row_n
duplicate_rate
unique_random_n
effective_n
seed_effective_n
median_seed_effective_n
max_row_reuse_n
cell_zero_support_n
```

Effective-n definition:

```text
For each seed x split x replay_step x denominator_type x candidate_id x stage2_budget_X:
  reuse_count_i = number of draws for unique random_row_uid i
  seed_effective_n = (sum_i reuse_count_i)^2 / sum_i(reuse_count_i^2)

For readout rows:
  effective_n = median(seed_effective_n) across valid seeds
  median_seed_effective_n = effective_n
  effective_seed_n = count of seeds with:
    seed_effective_n >= replacement_effective_n_floor
    AND cell_zero_support_n = 0
```

`with_replacement_replay` is diagnostic-only in 12A7d. A positive result under this null may motivate a later variance-corrected random replay requirement, but it must not set a supported deployable state here.

## 7. Chained Random Replay Contract

For `stage1_anchor_chained_survivor`, every variant must preserve the two-stage path.

Step 1. Stage-1 anchor random keep:

```text
For each seed and baseline_id,
draw the same stage1_anchor_selected_n profile as the real stage-1 anchor
from random_stage_1_evaluable rows using the same baseline-specific cell
fallback rule as stage-2 selection.

stage1 requested-count source:
  12A7c stage1 anchor reconstructed selected rows

stage1 requested cell key:
  split x board_bucket x calendar_month

stage1 replay behavior:
  strict_exact_cell_replay uses exact month cells.
  hierarchical_month_quarter_replay uses month then quarter fallback.
  hierarchical_split_board_fallback_replay uses month, quarter, then split x board fallback.
  pooled_cell_weighted_replay uses exact month cells with requested-cell weights.
  with_replacement_replay uses exact month cells and may replace only inside sparse cells.
```

Step 2. Random survivor denominator:

```text
Restrict step-1 random keep rows to:
  random_no_fast_fail_L10_H20 = true
  random_stage_2_evaluable = true
  random_stage2_label_read_status = pass
```

Step 3. Stage-2 candidate random selected count:

```text
Draw the same stage2 selected-count profile as the frozen 12A7c candidate
from the step-2 random survivor denominator,
using the active baseline variant.

stage2 requested cell key:
  split x board_bucket x calendar_month

Stage-2 selected random rows must be a subset of the stage-1 kept random rows
for the same seed and baseline_id.
```

Step 4. Random target:

```text
random_rate = mean(random_stage_2_continuation_target)
```

The same `baseline_id` must be applied consistently to stage-1 keep and stage-2 select within a chained seed. Mixing strict stage-1 with coarser stage-2, or coarser stage-1 with strict stage-2, is forbidden unless it is emitted as an explicitly named diagnostic ablation and excluded from the decision map.

For `ground_truth_no_fast_fail_survivor`, Step 1 is skipped and the random denominator is:

```text
random_no_fast_fail_L10_H20 = true
AND random_stage_2_evaluable = true
AND random_stage2_label_read_status = pass
```

Decoupled replay is always diagnostic-only and cannot change 12A7d decision state.

## 8. Sampling Reproducibility

Random row identity:

```text
random_row_uid =
  seed
  sample_draw_id
  path_key
  instrument
  entry_pos
  entry_price
  replacement_draw_index
```

If `replacement_draw_index` is missing and deterministically derived, the derived value must be used in `random_row_uid`. For no-replacement variants, duplicate `random_row_uid` within a replay step is a hard failure.

Within each random candidate pool, stable ordering must use:

```text
replacement_draw_index
sample_draw_id
instrument
random_trade_open_date
path_key
```

If a legacy random input lacks `replacement_draw_index` or `sample_draw_id`, the implementation may derive deterministic equivalents from audited input row order and must record:

```text
retention_rank_rule = derived_from_input_row_order
```

Default config constants:

```text
min_random_seed_n = 100
bootstrap_seed = 120712
n_resamples >= 2000
ci_low_q = 0.025
ci_high_q = 0.975
bootstrap_min_valid_replicates = 1500
pooled_min_supported_weight_share = 0.80
pooled_min_effective_seed_n = 30
replacement_effective_n_floor = 0.50 * requested_selected_n per seed x split x replay_step
```

## 9. Metrics and Required Fields

Required readout for every `baseline_id`, `denominator_type`, `candidate_id`, `stage2_budget_X`, and `split`:

```text
baseline_id
baseline_family_id
denominator_type
candidate_id
candidate_family
stage2_budget_X
split
cell_grain
null_strength_rank
board_dimension_preserved_flag
calendar_dimension_preserved_flag
allowed_interpretation
stage1_anchor_rule_id
stage1_anchor_X
candidate_selected_n
candidate_selected_positive_n
candidate_continuation_rate
candidate_base_continuation_rate
full_candidate_selected_n
full_candidate_positive_n
full_candidate_continuation_rate
candidate_supported_cell_selected_n
candidate_supported_cell_positive_n
candidate_supported_cell_continuation_rate
requested_selected_n
requested_cell_n
supported_cell_n
unsupported_cell_n
available_random_n
sampled_random_n
shortfall_n
shortfall_rate
supported_requested_n
unsupported_requested_n
supported_weight_share
valid_seed_n
effective_seed_n
random_p05
random_p50
random_p95
delta_vs_random_p50
delta_vs_random_p50_ci95_low
delta_vs_random_p50_ci95_high
bootstrap_replicate_valid_n
replacement_draw_n
duplicate_rate
effective_n
median_seed_effective_n
cell_zero_support_n
baseline_construction_status
readout_status
diagnostic_only_flag
```

Direction:

```text
candidate_continuation_rate higher is better
delta_vs_random_p50 = candidate_continuation_rate - random_p50
delta_vs_random_p50_ci95_low > 0 supports positive separation

For pooled_cell_weighted_replay only:
  delta_vs_random_p50 =
    candidate_supported_cell_continuation_rate - random_p50
  delta_vs_random_p50_ci95_low / high use the same supported-cell
  candidate denominator.
```

Cell audit must include one row per seed x requested cell x replay step:

```text
baseline_id
baseline_family_id
seed
replay_step
denominator_type
candidate_id
stage2_budget_X
split
board_bucket
calendar_month
calendar_quarter
requested_selected_n
realized_cell_grain
available_random_n
sampled_random_n
shortfall_n
fallback_used_flag
replacement_used_flag
duplicate_rate
random_row_uid_duplicate_n
seed_effective_n
cell_support_status
```

## 10. Statistical Gates

Bootstrap method:

```text
Use nested random-seed bootstrap.
Each replicate resamples candidate selected events and valid random seeds,
then recomputes random p50 from the resampled seed distribution.
```

Canonical CI fields:

```text
delta_vs_random_p50_ci95_low / high =
  bootstrap CI of candidate_continuation_rate - random_p50
```

Primary chained support gate:

```text
denominator_type = stage1_anchor_chained_survivor
split = robustness
candidate_selected_n >= 150
candidate_selected_positive_n >= 30
valid_seed_n >= min_random_seed_n for strict or hierarchical variants
bootstrap_replicate_valid_n >= 1500
delta_vs_random_p50 >= +0.02
delta_vs_random_p50_ci95_low > 0
baseline_construction_status = pass
```

For pooled weighted replay:

```text
supported_weight_share >= pooled_min_supported_weight_share
effective_seed_n >= pooled_min_effective_seed_n
delta_vs_random_p50_ci95_low > 0
diagnostic_only_flag = true
```

For with-replacement replay:

```text
cell_zero_support_n = 0
effective_n >= replacement_effective_n_floor
effective_seed_n >= min_random_seed_n
delta_vs_random_p50_ci95_low > 0
diagnostic_only_flag = true
```

Validation remains readout-only. No decision state may be selected because validation alone passes or fails.

## 11. Decision Map

Only chained robustness rows can set the 12A7d decision:

```text
decision_denominator_type = stage1_anchor_chained_survivor
decision_split = robustness

Rows with denominator_type = ground_truth_no_fast_fail_survivor are report-only
diagnostics. They must not set, upgrade, or downgrade `decision_state`.
```

Decision states:

```text
12A7d_strict_chained_stage2_supported:
  strict_exact_cell_replay is constructible on robustness;
  chained robustness delta_vs_random_p50_ci95_low > 0;
  all primary chained support gates pass.

12A7d_chained_stage2_supported_with_baseline_caveat:
  strict_exact_cell_replay is not constructible;
  hierarchical_month_quarter_replay passes robustness;
  pooled_cell_weighted_replay direction agrees;
  chained robustness delta_vs_random_p50_ci95_low > 0;
  interpretation explicitly records baseline caveat.

12A7d_stage2_signal_diagnostic_only:
  positive chained evidence appears only under hierarchical_split_board_fallback_replay,
  pooled weighted replay, or with-replacement replay;
  or candidate-side sample / positive_n / CI quality blocks support.

12A7d_random_baseline_support_insufficient:
  no pre-registered variant can construct enough valid or effective random support
  to evaluate the frozen chained candidate.

12A7d_stage2_not_supported:
  at least one strict or near-strict baseline with null_strength_rank <= 3
  is constructible,
  but the frozen chained candidate does not beat random on robustness.

12A7d_blocked_input_or_lineage_failure:
  required input, upstream lineage, PIT, label, split-boundary, candidate
  reconciliation, or random path-source gate fails before variant evaluation.
```

Decision precedence:

```text
1. If input / lineage / PIT / label / split / candidate reconciliation gate fails:
     decision_state = 12A7d_blocked_input_or_lineage_failure

2. Else evaluate strict_exact_cell_replay.

3. If strict chained robustness support gates pass:
     decision_state = 12A7d_strict_chained_stage2_supported

4. Else evaluate hierarchical_month_quarter_replay.

5. If hierarchical_month_quarter_replay passes
   and pooled weighted replay has the same positive sign:
     decision_state = 12A7d_chained_stage2_supported_with_baseline_caveat

6. Else if chained point estimates are favorable only under
   diagnostic variants:
     decision_state = 12A7d_stage2_signal_diagnostic_only

7. Else if all variants have baseline_construction_status in [fail, insufficient]:
     decision_state = 12A7d_random_baseline_support_insufficient

8. Else if strongest_accepted_null_strength_rank <= 3:
     decision_state = 12A7d_stage2_not_supported

9. Else:
     decision_state = 12A7d_random_baseline_support_insufficient
```

`stage2_chained_sensitivity_decision.csv` must include:

```text
decision_state
input_gate_status
candidate_reconciliation_status
random_source_status
gate_failure_reasons_source
selected_chained_candidate_id
selected_chained_candidate_family
selected_chained_X
stage1_anchor_rule_id
stage1_anchor_feature
stage1_anchor_orientation
stage1_anchor_X
strict_baseline_status
hierarchical_month_quarter_baseline_status
hierarchical_split_board_fallback_baseline_status
pooled_weighted_baseline_status
with_replacement_baseline_status
strongest_accepted_null
weakest_accepted_null_that_supports_claim
weakest_accepted_null_strength_rank
robustness_candidate_selected_n
robustness_candidate_positive_n
robustness_candidate_continuation_rate
robustness_random_p50
robustness_delta_vs_random_p50
robustness_delta_vs_random_p50_ci95_low
robustness_delta_vs_random_p50_ci95_high
baseline_caveat
allowed_interpretation
next_allowed_requirement
recommended_internal_followup
```

`next_allowed_requirement` mapping:

```text
if decision_state in [
  12A7d_strict_chained_stage2_supported,
  12A7d_chained_stage2_supported_with_baseline_caveat
]:
  next_allowed_requirement = requirement_12a7e_defense_participation_frontier.md
  recommended_internal_followup = quantify_stage1_defense_opportunity_cost_before_policy_replay

if decision_state in [
  12A7d_stage2_signal_diagnostic_only,
  12A7d_random_baseline_support_insufficient,
  12A7d_stage2_not_supported
]:
  next_allowed_requirement = requirement_12a7e_defense_participation_frontier.md
  recommended_internal_followup = test_whether_stage1_X030_denominator_is_too_narrow

if decision_state = 12A7d_blocked_input_or_lineage_failure:
  next_allowed_requirement = none
  recommended_internal_followup = gate_specific_failure_triage
```

## 12. Required Outputs

All publishable tables go under:

```text
outputs/publishable/tables/12A7d_stage2_random_baseline_support_triage/
```

Required tables:

```text
input_artifact_audit.csv
frozen_candidate_reconciliation.csv
random_support_cell_audit.csv
random_replay_variant_readout.csv
random_replay_variant_bootstrap_ci.csv
random_replay_seed_distribution.csv
stage2_chained_sensitivity_decision.csv
```

Report:

```text
outputs/publishable/reports/stage2_random_baseline_triage_report.md
```

Manifest:

```text
outputs/manifests/12A7d_stage2_random_baseline_support_triage_manifest.json
```

Local cache:

```text
outputs/local_cache/12A7d_stage2_random_baseline_support_triage/frozen_candidate_selection_matrix.parquet
outputs/local_cache/12A7d_stage2_random_baseline_support_triage/variant_random_selected.parquet
outputs/local_cache/12A7d_stage2_random_baseline_support_triage/variant_bootstrap_replicates.parquet
```

The manifest must include sha256 for every publishable table, report, config, requirement, and local-cache artifact. Report and manifest hashes must be synchronized after report generation.

## 13. Report Requirements

The report must lead with:

```text
final decision_state
selected chained candidate and X frozen from 12A7c
stage-1 anchor tuple and X
strict replay construction status
hierarchical replay construction status
pooled weighted replay construction status
with-replacement replay construction status
robustness candidate selected_n / positive_n / continuation_rate
best strict-or-near-strict random_p50 and CI
weakest accepted null that supports the claim
allowed interpretation
recommended next step
```

The report must explicitly state:

```text
12A7d did not select a new stage-2 candidate, feature, X, or model family.
12A7d did not change the stage-1 simple backbone anchor.
A coarser random null is weaker evidence than strict exact replay.
Pooled and with-replacement variants are diagnostic-only unless they merely confirm a stricter accepted null.
Decoupled survivor readout is not deployable.
The conclusion applies only to C0 risk_on events and the current fixed -10% / +20% labels.
```

Required findings:

```text
1. Whether strict exact replay is structurally impossible or merely under-seeded.
2. Which cells cause the random support shortfall.
3. Whether hierarchical replay repairs support while preserving board and useful calendar controls.
4. Whether pooled / replacement variants agree directionally with stricter variants.
5. Whether the evidence supports stage-2 chained continuation or only diagnoses a baseline construction problem.
6. Whether 12A7e should widen the stage-1 defense denominator before any policy replay.
7. Decoupled readout, if emitted, as diagnostic context only.
```

## 14. Implementation Checklist

Implementation must include tests for:

1. `direction_e_decision.csv` allows 12A7c random replay failure but rejects unrelated upstream failures.
2. Input artifact audit records every required input with sha256, row count, schema status, and read status.
3. Candidate reconstruction from `stage2_decoupling_score_matrix.parquet` exactly reconciles selected counts and positives against 12A7c publishable readouts.
4. 12A7d never uses report text to derive candidate identity, labels, or scores.
5. Strict replay invalidates a seed when any split x board_bucket x calendar_month requested cell is short.
6. `random_stage_1_evaluable` and `random_no_fast_fail_L10_H20` are derived from `entry_forward_path_cache.parquet` using the explicit field mapping in §4.3.
7. `hierarchical_month_quarter_replay` tries month then quarter and fails the cell if quarter is short.
8. `hierarchical_split_board_fallback_replay` tries month, quarter, then split x board, never drops board_bucket, and is marked diagnostic-only when fallback is used.
9. No-replacement variants prevent duplicate `random_row_uid` within a replay step even when hierarchical fallback pools overlap.
10. Pooled weighted replay uses requested cell counts as weights, reports unsupported requested weight, and computes pooled delta against candidate rows restricted to supported cells.
11. With-replacement replay reports duplicate rate, Kish effective_n, seed_effective_n, and zero-support cells.
12. Chained replay applies the same baseline variant to both stage-1 random keep and stage-2 random select.
13. Stage-1 random keep uses the same hierarchical fallback rule as stage-2 random select for the active `baseline_id`.
14. Stage-2 selected random rows are a subset of stage-1 kept rows for the same seed and baseline_id.
15. Decoupled replay skips stage-1 random keep, remains diagnostic-only, and cannot affect decision_state.
16. Random path labels are joined from cache by `path_key / instrument / entry_pos / entry_price` with uniqueness checks.
17. Bootstrap CI computes `candidate_continuation_rate - random_p50` for strict and hierarchical rows, and `candidate_supported_cell_continuation_rate - random_p50` for pooled rows; sign reversal fails tests.
18. Decision precedence is exclusive and does not choose the best-looking variant.
19. Pooled and with-replacement variants cannot produce `12A7d_strict_chained_stage2_supported` or `12A7d_chained_stage2_supported_with_baseline_caveat` by themselves.
20. Validation and robustness do not influence candidate, X, feature, model family, or baseline variant selection.
21. Required output schemas contain all fields named in §9 and §11.
22. Report and manifest hashes are synchronized.

## 15. One-line Thesis

12A7d isolates whether 12A7c failed because the chained continuation signal is absent or because the strict random null cannot support the narrow stage-1 X=0.30 survivor denominator, while preserving the rule that weaker random baselines only earn weaker conclusions.
