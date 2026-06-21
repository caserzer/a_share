# 需求：12A7 Direction A PIT Trailing-rank Operating Point Audit

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
4. 每个被读取的输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失、schema 不匹配、score source 不可用或 fallback 复现越界、PIT 时间戳不可证明、entry executability 不可证明时 fail closed。
6. 不得从报告文本或聚合表反推出事件、标签、特征或逐行 score。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7
direction_id = A
run_id = 12A7_direction_a_trailing_rank_operating_point_audit
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7_direction_a_trailing_rank_operating_point_audit.py
expected_config = configs/config_12a7_direction_a_trailing_rank_operating_point_audit.yaml
expected_test_file = tests/test_12a7_direction_a_trailing_rank_operating_point_audit.py
research_plan_source = research_plan_12a6d_rank_based_operating_point_revision.md
```

12A7 Direction A 只回答 operating-point 问题：

```text
Q1. 12A6c 的 score rank 是否能用 PIT trailing percentile rule 迁移到 OOS，
    而不是依赖 train-frozen absolute probability threshold？

Q2. 在同一实际预算下，trailing-rank rule 是否能在 robustness 中打赢
    matched random 和 train-frozen single-feature challenger？
```

本需求不占用 12A6d 编号。12A6c 的 `next_allowed_requirement` 仍是历史事实，但本需求按已修正研究计划从 12A7 开始。

Lineage note:

```text
This requirement supersedes the previously reserved
requirement_12a7_two_stage_meta_label_oos_validation.md placeholder.
That old 12A7 OOS-validation branch is retired until a deployable rank operating point is supported.
```

## 2. 背景与核心修正

12A6c 的结论：

```text
12A6c decision = 12A6c_stage1_partial
input_gate_status = pass
stage_1_threshold_health = fail
stage_2_threshold_health = fail
```

失败机制不是 score 完全失效，而是 train-frozen absolute probability threshold 无法迁移到 base-rate 非平稳的 OOS 总体：

```text
stage-1:
  OOS fast-fail base rate 更低 -> probability scale 下移
  keep low-risk threshold 放水 -> actual keep budget 膨胀到 78% - 84%

stage-2:
  OOS continuation base rate 更低 -> probability scale 下移
  select high-continuation threshold 收紧 -> actual continue budget 收缩到 31% - 38%
```

12A7 Direction A 的修正是把 deployable operating point 定义为：

```text
headline operating point = PIT trailing-rank / trailing-percentile rule
whole-month or whole-split rank = diagnostic upper bar only
OOS actual budget drift = required readout, not assumed pass by construction
```

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不重新定义 fast-fail / continuation label，不做 vol-scaled barrier；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不训练新高容量模型，不用 OOS 结果回头挑模型、feature、budget、history policy 或 label；
- 不把 whole-month、board-month、whole-split rank 作为 primary gate；
- 不声明可交易 alpha，不做 policy replay、仓位、交易成本或资金曲线；
- 不做 12A7 Direction E 的 ground-truth survivor 解耦读数；
- 不把 random uplift 当作复杂模型成功的充分条件；
- 不把 validation 当作调参集。

## 4. 必需输入

### 4.1 12A6c two-stage 输出

必需输入：

```text
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/input_artifact_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_universe.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_targets.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_dictionary.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_pit_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_1_model_card.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_2_model_card.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_1_rejector_readout.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_2_continuation_readout.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_1_single_feature_frontier.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_2_single_feature_frontier.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_1_score_bucket_readout.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_2_score_bucket_readout.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_1_random_same_budget_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_2_random_same_budget_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage_threshold_health.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_decision.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

Local cache input required for fallback score reproduction:

```text
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_matrix.parquet
```

Primary score source should be a frozen row-level score artifact. If a future 12A6c rerun publishes it, 12A7 must consume it directly instead of refitting. The artifact must include:

```text
meta_event_id
instrument
event_t0_date
event_t0_pos
split
board_bucket
calendar_month
stage_2_decision_pos
stage1_fast_fail_score
stage2_continuation_score
stage_1_fast_fail_target
stage_2_continuation_target
score_source_mode
score_source_caveat
stage_1_model_id
stage_2_model_id
stage_1_feature_order_hash
stage_2_feature_order_hash
stage_1_train_imputation_median_hash
stage_2_train_imputation_median_hash
```

### 4.2 12A6c gate

12A7 Direction A may proceed only if:

```text
two_stage_decision.input_gate_status = pass
two_stage_decision.decision_state in [
  12A6c_stage1_partial,
  12A6c_stage1_supported_stage2_partial,
  12A6c_two_stage_supported
]
two_stage_decision.stage_1_model_id = logistic_regression_l2
two_stage_decision.stage_2_model_id = logistic_regression_l2
```

12A6c threshold health failure is not a blocker; it is the motivation for this requirement.

### 4.3 Matched random source

12A7 must reuse the same random source lineage as 12A6c. If 12A6c aggregate random audit is insufficient to recompute a same-budget trailing-rank baseline, the implementation must read:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
```

Random rows must preserve sampled-draw / `sample_weight` semantics. Unique-path de-duplication is forbidden.

Random path labels must be generated by merging `matched_random_sampled_entries.csv.gz` with the two path caches on:

```text
path_key
instrument
entry_pos
entry_price
```

Required derived random columns:

```text
random_stage_1_evaluable
random_stage_1_fast_fail_target
random_no_fast_fail_L10_H20
random_stage_2_entry_blocked
random_stage_2_horizon_complete_20d
random_stage_2_continuation_target
random_path_label_status
```

If either path cache is unavailable or the merge key is not unique on the cache side, the random baseline must fail closed with `decision_state = 12A7_blocked_input_or_pit_failure`.

## 5. Universe And Time Discipline

Primary universe:

```text
source = 12A6c two_stage_event_universe.csv.gz
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage_1_evaluable = true
entry_blocked = false
expected_primary_event_n = 15113 unless upstream hash drift is explicitly reported
```

Stage-1 decision time:

```text
decision_time = event_t0_close
sort_key = event_t0_pos, event_t0_date, instrument, meta_event_id
allowed history =
  prior events with event_t0_pos < current event_t0_pos
  AND event_t0_pos >= current event_t0_pos - trailing_history_window_sessions
```

Stage-2 decision time:

```text
decision_time = close at stage_2_decision_pos
sort_key = stage_2_decision_pos, instrument, meta_event_id
deployable denominator =
  stage-1 trailing-rank keep under the same stage1_history_policy_id and stage1_budget_X
  AND stage1_gate_source = primary_model_trailing_rank_keep
  AND no_fast_fail_L10_H20 = true
  AND stage_2_path_evaluable = true
  AND stage_2_entry_blocked = false
  AND stage_2_horizon_complete_20d = true
allowed history =
  prior deployable stage-2 candidates with stage_2_decision_pos < current stage_2_decision_pos
  AND stage_2_decision_pos >= current stage_2_decision_pos - trailing_history_window_sessions
  computed under the same stage1_history_policy_id and stage1_budget_X
```

Tie ordering must be deterministic:

```text
tie_break_key = instrument ASC, event_t0_date ASC, meta_event_id ASC
```

Stage-1 selection must be computed end-to-end for every row before any stage-2 deployable denominator or stage-2 history is constructed. No label from the current or future row may enter any trailing history statistic used to score or select the current row.

## 6. Score Source And Reproduction

Primary model scores:

```text
stage_1_score_id = logistic_regression_l2.stage1_fast_fail_score
stage_1_direction = lower score is better
stage_1_target_id = stage_1_fast_fail_target

stage_2_score_id = logistic_regression_l2.stage2_continuation_score
stage_2_direction = higher score is better
stage_2_target_id = stage_2_continuation_target
```

Score-source priority:

```text
primary:
  consume frozen row-level scores if present
  score_source_mode = frozen_12A6c_row_level_scores
  no model refit

fallback:
  reproduce scores from 12A6c feature matrix and model card
  score_source_mode = reproduce_12A6c_v1
  refit diagnostics required
```

If row-level scores are not already available, implementation may reproduce them from 12A6c:

```text
score_source_mode = reproduce_12A6c_v1
fit_split = train only
model_family = logistic_regression_l2
hyperparameter_json = stage_1_model_card.csv / stage_2_model_card.csv
feature_list_hash must match 12A6c model_card
feature_order must reproduce the 12A6c feature_list_hash
feature preprocessing =
  train_median_imputation fit on train split only
  no standardization
  no class weights
  no post-fit calibration
runtime metadata =
  sklearn_version
  numpy_version
  pandas_version
  train_imputation_median_hash
  feature_order_hash
```

Required reproduction audit:

```text
score_reproduction_audit.csv
```

Allowed `score_reproduction_status` values:

```text
frozen_row_level_scores
pass_exact
pass_near_miss
fail
```

The audit must compare reproduced aggregate readouts against 12A6c:

```text
pass_exact:
  stage_1 train score_threshold abs diff <= 1e-9
  stage_2 train score_threshold abs diff <= 1e-9
  stage_1 split keep_n abs diff <= 0
  stage_2 split continue_n abs diff <= 0
  stage_1 split target_rate abs diff <= 1e-9
  stage_2 split target_rate abs diff <= 1e-9

pass_near_miss:
  feature_order_hash and hyperparameter_json match
  stage_1 split keep_n abs diff <= max(50, 0.05 * reference_selected_n)
  stage_2 split continue_n abs diff <= max(50, 0.05 * reference_selected_n)
  stage_1 split target_rate abs diff <= 0.001
  stage_2 split target_rate abs diff <= 0.001
  stage_1 / stage_2 score_threshold abs diff <= 0.001
```

`pass_near_miss` may proceed but must set `score_source_caveat = numerical_near_miss`. The selected-count tolerance is deliberately wider than the target-rate tolerance because a tiny logistic threshold change can flip many rows when OOS scores are dense at the train boundary. If reproduction exceeds near-miss bounds, 12A7 must stop.

If row-level scores are absent and fallback reproduction fails, 12A7 must stop with:

```text
decision_state = 12A7_blocked_score_source_failure
```

## 7. PIT Trailing-rank Operating Rule

### 7.1 Primary history policy

Primary deployable history policy:

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
```

For each current row:

```text
1. Restrict history to prior rows inside the rolling window:
     decision_pos < current_decision_pos
     AND decision_pos >= current_decision_pos - trailing_history_window_sessions.
2. Use prior rows in the same board_bucket inside that window if sample_n >= board_min_history_n.
3. Otherwise fall back to prior global rows inside that window if sample_n >= global_min_history_n.
4. Otherwise mark rank_status = rank_not_evaluable.
```

The 504-session primary window is pre-registered for 12A7 and is not selected on validation / robustness. It is long enough to keep stage-2 survivor history evaluable while still adapting to recent score-regime shifts.

Diagnostic-only history policies:

```text
board_then_global_rolling_252_sessions
board_then_global_rolling_1008_sessions
board_then_global_expanding_from_inception

diagnostic_only_flag = true
not_allowed_for_decision = true
```

Expanding-from-inception is explicitly not the headline rule because it ranks current OOS scores against stale early-regime distributions.

Minimum history:

```text
stage_1_global_min_history_n = 500
stage_1_board_min_history_n = 150
stage_2_global_min_history_n = 250
stage_2_board_min_history_n = 75
```

Rows with `rank_not_evaluable` are not selectable, but they remain in `denominator_n` and must be counted in both `trailing_rank_operating_point_readout.csv` and `trailing_rank_budget_drift_audit.csv`. `selected_budget_total` uses `denominator_n`; `selected_budget_rank_evaluable` uses `rank_evaluable_n`.

### 7.2 Percentile definition

For score `s` and trailing history score array `H`:

```text
midrank_percentile =
  (count(H < s) + 0.5 * count(H = s)) / count(H)
```

Stage-1:

```text
stage1_score_percentile = midrank_percentile(stage1_fast_fail_score, H)
keep_flag_X = stage1_score_percentile <= X
```

Stage-2:

```text
stage2_score_percentile = midrank_percentile(stage2_continuation_score, H)
continue_flag_X = stage2_score_percentile >= 1 - X
```

Percentile ties are not broken to force an exact budget. The observed selected budget is a result, not a constraint.

### 7.3 Budget grid

Required grid:

```text
budget_grid = [0.30, 0.50, 0.70]
primary_X_stage_1 = 0.50
primary_X_stage_2 = 0.50
primary_tuple = stage1_budget_X = 0.50, stage2_budget_X = 0.50

stage_1_curve:
  stage1_budget_X in budget_grid
  stage2_budget_X = null

stage_2_chained_curve:
  stage1_budget_X fixed at primary_X_stage_1
  stage2_budget_X in budget_grid

paired_grid:
  stage1_budget_X in budget_grid
  stage2_budget_X in budget_grid
  diagnostic_only_flag = true unless equal to primary_tuple
```

The implementation must publish stage-1 curve and stage-2 chained curve rows. Decision support uses `primary_tuple` only. If `primary_tuple` fails, the run may report diagnostic curves for other budgets but must not switch the headline budget after seeing OOS.

### 7.4 Diagnostic upper bars

The following ranks are allowed only as diagnostic upper bars:

```text
same_month_full_cohort_rank
board_month_full_cohort_rank
whole_split_rank
```

Every such row must carry:

```text
diagnostic_only_flag = true
lookahead_rank_upper_bar = true
not_allowed_for_decision = true
```

They cannot enter `trailing_rank_decision.csv` support gates or `next_allowed_requirement`.

## 8. Baselines

### 8.1 Same-budget matched random

For each stage, split, budget tuple, and primary history policy:

```text
stage-1 random:
  model_denominator_n_cell =
    count(C0 deployable rows in split x board_bucket x calendar_month)
  model_selected_n_cell =
    count(stage-1 selected rows in the same cell)
  random_denominator_n_cell =
    count(matched random deployable rows in the same cell)
  random_selected_n_cell =
    floor(model_selected_n_cell / model_denominator_n_cell * random_denominator_n_cell)

stage-2 random:
  random_stage1_denominator_n_cell =
    count(matched random deployable rows in split x board_bucket x calendar_month)
  random_stage1_keep_n_cell =
    floor(model_stage1_selected_n_cell / model_stage1_denominator_n_cell * random_stage1_denominator_n_cell)
  random_stage1_keep_rows =
    first random_stage1_keep_n_cell rows by random_retention_rank

  model_denominator_n_cell =
    count(model stage-2 deployable rows in split x board_bucket x calendar_month
          under stage1_budget_X and stage2_budget_X)
  model_selected_n_cell =
    count(model stage-2 continue rows in the same cell)
  random_denominator_n_cell =
    count(random_stage1_keep_rows in the same cell where
          random_no_fast_fail_L10_H20 = true
          AND random_stage_2_entry_blocked = false
          AND random_stage_2_horizon_complete_20d = true)
  random_selected_n_cell =
    floor(model_selected_n_cell / model_denominator_n_cell * random_denominator_n_cell)
```

`model_denominator_n_cell` is the full deployable cell denominator before trailing-history exclusion. This makes random match the realized deployed budget, including abstention caused by insufficient history. Stage-2 random must first apply an analogous random stage-1 keep budget; otherwise the stage-2 random denominator would mix all random survivors against model-kept survivors and create a composition confound.

If `model_selected_n_cell > 0` and random denominator exists, minimum selected random count is 1. If random denominator is missing, the cell is excluded and logged with `random_cell_status = missing_random_denominator`.

Random selection must be deterministic and label-free:

```text
random_seed_n >= 100
base_seed = 120700
random_retention_rank =
  hash(base_seed, seed, random_instrument, random_trade_open_date, random_row_id)
```

Stage-1 random baseline target:

```text
random_keep_fast_fail_rate_p05 / p50 / p95
```

Stage-2 random baseline target:

```text
random_continue_continuation_rate_p05 / p50 / p95
```

### 8.2 Train-frozen single-feature challenger

Formal challenger must be selected on train only, then applied unchanged to validation / robustness.

Stage-1 candidate list:

```text
volatility_20d ascending
volatility_60d ascending
max_drawdown_60d ascending
distance_to_60d_low ascending
distance_to_120d_low ascending
rebound_from_60d_low ascending
```

Stage-2 candidate list:

```text
realized_path_volatility_0_20d descending
realized_max_high_return_0_20d descending
realized_early_window_ret_0_10d descending
realized_ma_5_20_spread_at_day20 descending
distance_to_120d_low descending
```

Selection rule:

```text
stage-1:
  choose the candidate with the lowest train fast_fail_rate at X = 0.50
  under the same board_then_global_rolling_504_sessions history policy

stage-2:
  choose the candidate with the highest train continuation_rate at X = 0.50
  under the same board_then_global_rolling_504_sessions history policy
  and stage1_budget_X fixed at primary_X_stage_1
  and stage1_gate_source = primary_model_trailing_rank_keep

tie_break = feature_name ASC
```

Primary model-vs-single-feature deltas must be budget- and denominator-matched:

```text
common_evaluable_denominator =
  rows evaluable for both primary model score and the train-frozen single-feature challenger
  under the same stage, split, history_policy_id, history_window, stage1_budget_X, stage2_budget_X

model_selected_n_cell =
  count(primary model selected rows within common_evaluable_denominator
        by split x board_bucket x calendar_month)

single_feature_selected_n_cell =
  model_selected_n_cell

single_feature_selected_rows =
  best rows by the frozen feature orientation within the same common_evaluable_denominator cell
```

The raw trailing-percentile challenger readout may also be published, but `delta_vs_single_feature` used in support gates must come from this common-denominator matched-selected-n replay. If common denominator coverage is below 95% of the model rank-evaluable denominator, support status must be downgraded to diagnostic or partial.

OOS best-single may be published as diagnostic only:

```text
oos_best_single_diagnostic_only = true
not_allowed_for_decision = true
```

## 9. Metrics

### 9.1 Score quality

Required per split:

```text
auc
spearman_rank_ic
rank_ic_pvalue
decile_lift
quintile_lift
tail_bucket_rate
base_rate
event_n
positive_n
```

Stage-1 direction:

```text
auc_target = stage_1_fast_fail_target
auc_score = stage1_fast_fail_score
higher score should imply higher fast_fail_rate
operating rule still keeps lower-score rows because lower fast-fail risk is better
rank_ic is computed between stage1_fast_fail_score and stage_1_fast_fail_target
rank_ic expected sign = positive
```

Stage-2 direction:

```text
higher score should imply higher continuation_rate
```

### 9.2 Operating readout

Required for every `stage x split x history_policy_id x stage1_budget_X x stage2_budget_X x model_or_baseline`:

```text
denominator_n
rank_evaluable_n
rank_not_evaluable_n
denominator_positive_n
rank_evaluable_positive_n
selected_n
selected_positive_n
selected_budget_total
selected_budget_rank_evaluable
selected_rate
base_rate
delta_vs_base
random_p05
random_p50
random_p95
delta_vs_random_p50
single_feature_selected_rate
delta_vs_single_feature
bootstrap_ci95_low
bootstrap_ci95_high
bootstrap_random_ci95_low
bootstrap_random_ci95_high
bootstrap_single_feature_ci95_low
bootstrap_single_feature_ci95_high
bootstrap_positive_n
```

Stage-1 `selected_rate` is fast-fail rate; lower is better.

Stage-2 `selected_rate` is continuation rate; higher is better.

`base_rate` is computed on `rank_evaluable_n` unless explicitly suffixed with `_total`. The budget fields must always show both total-denominator and rank-evaluable-denominator versions.

### 9.3 Budget drift

Required budget drift readout:

```text
stage1_budget_X
stage2_budget_X
budget_tuple_role
actual_budget_total
actual_budget_rank_evaluable
budget_abs_delta_total_vs_X
budget_abs_delta_rank_evaluable_vs_X
rank_not_evaluable_rate
board_history_used_rate
global_fallback_rate
history_n_p05
history_n_p50
history_n_p95
```

Budget drift is never a pass-by-construction condition. It is a required diagnostic.

### 9.4 Bootstrap

Bootstrap confidence intervals:

```text
bootstrap_unit = meta_event_id
random_bootstrap_unit = random_seed
bootstrap_seed = 120701
bootstrap_n = 2000
strata = split x board_bucket x calendar_month where sample size permits
nested_random_seed_resampling = true
```

Headline deltas:

```text
stage1_model_minus_random_p50_fast_fail_rate
stage1_model_minus_single_feature_fast_fail_rate
stage2_model_minus_random_p50_continuation_rate
stage2_model_minus_single_feature_continuation_rate
```

If a bootstrap cell is too small, fall back to split-level bootstrap and mark `bootstrap_status = fallback_split_level`.

For model-vs-random deltas, each bootstrap replicate must resample both model events and random seeds, then recompute the random p50 from the resampled seed distribution. For model-vs-single-feature deltas, use paired event bootstrap on the same split and target denominator. If nested random resampling is not possible, `bootstrap_status = random_ci_diagnostic_only` and random CI cannot satisfy a hard support gate.

## 10. Gates

### 10.1 Input and PIT gate

Required:

```text
input_artifact_audit_status = pass
score_reproduction_status in [
  frozen_row_level_scores,
  pass_exact,
  pass_near_miss
]
split_time_boundary_audit_status = pass
no_future_feature_status = pass
diagnostic_lookahead_rank_excluded_from_primary_gate = pass
```

Any failure yields:

```text
decision_state = 12A7_blocked_input_or_pit_failure
```

Except score-source failure yields:

```text
decision_state = 12A7_blocked_score_source_failure
```

### 10.2 Sample-size gate

Minimum headline sample sizes:

```text
headline_split_min_selected_n = 300
stage2_headline_min_selected_n = 150
bootstrap_min_positive_n = 30
slice_min_selected_n = 100
```

Sub-threshold split / board / family / year cells are diagnostic-only.

### 10.3 Rank-quality gate

Suggested support floors:

```text
stage1_fast_fail_auc_robustness >= 0.55
stage2_continuation_auc_robustness >= 0.55
rank_ic sign consistent with each stage's declared expected sign across train / robustness
robustness decile lift direction correct
```

Validation is readout-only. Robustness is the primary OOS gate.

For selective future budgets below 30%, this AUC floor must not be reused blindly; any later decile/tail policy should add precision@k, tail lift, or partial-AUC style gates.

### 10.4 Stage-1 support gate

At `history_policy_id = board_then_global_rolling_504_sessions`, `history_window_mode = rolling_sessions`, `trailing_history_window_sessions = 504`, and `stage1_budget_X = 0.50, stage2_budget_X = null`, stage-1 is supported if robustness satisfies all:

```text
selected_n >= headline_split_min_selected_n
model_fast_fail_rate <= random_fast_fail_rate_p50 - 0.02
model_fast_fail_rate <= train_frozen_single_feature_fast_fail_rate - 0.01
bootstrap_ci95(model_minus_random_p50) entirely below 0
bootstrap_ci95(model_minus_single_feature) entirely below 0
rank_quality_gate = pass
```

If model beats random but not train-frozen single feature:

```text
stage_1_status = simple_backbone_supported_complex_model_not_supported
```

### 10.5 Stage-2 support gate

At `history_policy_id = board_then_global_rolling_504_sessions`, `history_window_mode = rolling_sessions`, `trailing_history_window_sessions = 504`, and `primary_tuple = (stage1_budget_X = 0.50, stage2_budget_X = 0.50)`, stage-2 is supported if robustness satisfies all:

```text
selected_n >= stage2_headline_min_selected_n
model_continuation_rate >= random_continuation_rate_p50 + 0.02
model_continuation_rate >= train_frozen_single_feature_continuation_rate + 0.01
bootstrap_ci95(model_minus_random_p50) entirely above 0
bootstrap_ci95(model_minus_single_feature) entirely above 0
rank_quality_gate = pass
```

If stage-2 selected denominator is too small or CI too wide, stage-2 is diagnostic / partial, not supported.

CI exclusion in the correct direction is the primary statistical condition. The absolute margins above are secondary practical-effect floors and must be reported alongside base-rate-scaled relative lift.

### 10.6 Decision map

```text
12A7_trailing_rank_supported:
  stage-1 and stage-2 both pass support gates.

12A7_stage1_trailing_rank_supported_stage2_partial:
  stage-1 passes; stage-2 fails single-feature, sample-size, or CI gate but does not collapse vs random.

12A7_simple_backbone_supported_complex_model_not_supported:
  train-frozen single-feature challenger beats complex model on robustness.

12A7_rank_signal_diagnostic_only:
  AUC / lift exists, but sample-size or bootstrap gate blocks supported status.

12A7_no_rank_transport:
  rank-quality gate fails or model fails random baseline on robustness.

12A7_blocked_score_source_failure:
  frozen row-level scores are unavailable and fallback reproduction exceeds near-miss tolerance.

12A7_blocked_input_or_pit_failure:
  required input, PIT, leakage, random, or split-boundary gate fails.
```

`next_allowed_requirement` mapping:

```text
if decision_state = 12A7_trailing_rank_supported:
  next_allowed_requirement = requirement_12a8_probability_calibration_prior_shift_audit.md
  rationale =
    rank operating point is supported, but 12A6c threshold transport failed;
    12A8 is a calibration / prior-shift diagnostic before any later OOS policy validation.

if decision_state = 12A7_stage1_trailing_rank_supported_stage2_partial:
  next_allowed_requirement = none
  recommended_internal_followup = 12A7b_stage2_trailing_rank_or_backbone_revision

if decision_state = 12A7_simple_backbone_supported_complex_model_not_supported:
  next_allowed_requirement = none
  recommended_internal_followup = 12A7b_simple_backbone_operating_rule_validation

if decision_state in [12A7_no_rank_transport, 12A7_rank_signal_diagnostic_only]:
  next_allowed_requirement = requirement_12a9_vol_scaled_label_stability_and_separability_audit.md

if decision_state starts with 12A7_blocked:
  next_allowed_requirement = none
```

## 11. Required Outputs

All publishable tables go under:

```text
outputs/publishable/tables/12A7_direction_a_trailing_rank_operating_point_audit/
```

Required tables:

```text
input_artifact_audit.csv
score_reproduction_audit.csv
random_path_label_audit.csv
trailing_rank_score_quality_metrics.csv
trailing_rank_operating_point_readout.csv
trailing_rank_budget_drift_audit.csv
trailing_rank_random_same_budget_audit.csv
trailing_rank_single_feature_challenger.csv
trailing_rank_decile_lift_readout.csv
trailing_rank_budget_curve_readout.csv
diagnostic_lookahead_rank_upper_bar.csv
trailing_rank_decision.csv
split_time_boundary_audit.csv
```

Required local cache:

```text
outputs/local_cache/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_score_matrix.parquet
```

`trailing_rank_score_matrix.parquet` required columns:

```text
meta_event_id
instrument
event_t0_date
event_t0_pos
split
board_bucket
calendar_month
stage_2_decision_pos
stage1_fast_fail_score
stage2_continuation_score
stage_1_fast_fail_target
stage_2_continuation_target
score_source_mode
score_source_caveat
stage_1_model_id
stage_2_model_id
stage_1_feature_order_hash
stage_2_feature_order_hash
stage_1_train_imputation_median_hash
stage_2_train_imputation_median_hash
```

### 11.1 `score_reproduction_audit.csv`

Required columns:

```text
stage
model_id
score_source_mode
fit_split
feature_order_hash
feature_list_hash_expected
feature_list_hash_reproduced
train_imputation_median_hash
sklearn_version
numpy_version
pandas_version
split
reference_selected_n
reproduced_selected_n
selected_n_abs_diff
reference_target_rate
reproduced_target_rate
target_rate_abs_diff
reference_score_threshold
reproduced_score_threshold
score_threshold_abs_diff
score_reproduction_status
score_source_caveat
failure_reason
```

### 11.2 `random_path_label_audit.csv`

Required columns:

```text
seed
split
board_bucket
calendar_month
random_sampled_n
path_cache_matched_n
stage2_cache_matched_n
random_stage_1_evaluable_n
random_no_fast_fail_n
random_stage_2_path_evaluable_n
random_stage_2_positive_n
sample_weight_sum
merge_key_unique_status
random_path_label_status
failure_reason
```

### 11.3 `trailing_rank_score_quality_metrics.csv`

Required columns:

```text
stage
split
model_id
score_id
target_id
history_policy_id
history_window_mode
trailing_history_window_sessions
auc_target_id
auc_score_direction
rank_ic_expected_sign
event_n
positive_n
base_rate
auc
spearman_rank_ic
rank_ic_pvalue
decile_lift
quintile_lift
tail_bucket_rate
direction_check_status
rank_quality_status
```

### 11.4 `trailing_rank_operating_point_readout.csv`

Required columns:

```text
stage
split
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_gate_source
stage1_budget_X
stage2_budget_X
budget_tuple_role
model_id
score_id
target_id
denominator_n
rank_evaluable_n
rank_not_evaluable_n
denominator_positive_n
rank_evaluable_positive_n
selected_n
selected_positive_n
selected_budget_total
selected_budget_rank_evaluable
selected_rate
base_rate
delta_vs_base
random_p05
random_p50
random_p95
delta_vs_random_p50
single_feature_name
single_feature_common_denominator_n
single_feature_matched_selected_n
single_feature_actual_budget_common
single_feature_selected_rate
delta_vs_single_feature
relative_lift_vs_random_p50
relative_lift_vs_single_feature
bootstrap_ci95_low
bootstrap_ci95_high
bootstrap_random_ci95_low
bootstrap_random_ci95_high
bootstrap_single_feature_ci95_low
bootstrap_single_feature_ci95_high
bootstrap_positive_n
bootstrap_status
readout_status
diagnostic_only_flag
```

### 11.5 `trailing_rank_budget_drift_audit.csv`

Required columns:

```text
stage
split
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_gate_source
stage1_budget_X
stage2_budget_X
budget_tuple_role
denominator_n
rank_evaluable_n
rank_not_evaluable_n
rank_not_evaluable_rate
selected_n
actual_budget_total
actual_budget_rank_evaluable
budget_abs_delta_total_vs_X
budget_abs_delta_rank_evaluable_vs_X
board_history_used_rate
global_fallback_rate
history_n_p05
history_n_p50
history_n_p95
budget_drift_status
```

### 11.6 `trailing_rank_random_same_budget_audit.csv`

Required columns:

```text
stage
seed
split
board_bucket
calendar_month
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_gate_source
stage1_budget_X
stage2_budget_X
budget_tuple_role
model_denominator_n
model_rank_evaluable_n
model_selected_n
random_stage1_denominator_n
random_stage1_keep_n
random_denominator_n
random_selected_n
random_positive_n
sample_weight_sum
random_rate
random_target_id
random_cell_status
retention_rank_rule
```

### 11.7 `trailing_rank_single_feature_challenger.csv`

Required columns:

```text
stage
feature_name
orientation_selected_on_train
selection_split
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_gate_source
stage1_budget_X
stage2_budget_X
budget_tuple_role
split
denominator_n
rank_evaluable_n
common_denominator_n
common_denominator_coverage
denominator_positive_n
rank_evaluable_positive_n
selected_n
selected_positive_n
matched_selected_n
matched_selected_rate
selected_budget_total
selected_budget_rank_evaluable
selected_rate
base_rate
challenger_status
denominator_match_status
diagnostic_only_flag
```

### 11.8 `diagnostic_lookahead_rank_upper_bar.csv`

Required columns:

```text
stage
split
rank_method_id
history_policy_id
history_window_mode
trailing_history_window_sessions
stage1_gate_source
stage1_budget_X
stage2_budget_X
budget_tuple_role
selected_n
selected_positive_n
selected_budget_total
selected_budget_rank_evaluable
selected_rate
base_rate
delta_vs_base
lookahead_rank_upper_bar
not_allowed_for_decision
diagnostic_only_flag
```

### 11.9 `trailing_rank_decision.csv`

Required columns:

```text
decision_state
input_gate_status
score_reproduction_status
pit_gate_status
stage_1_status
stage_2_status
primary_history_policy_id
primary_history_window_mode
primary_trailing_history_window_sessions
primary_budget_X_stage_1
primary_budget_X_stage_2
stage_1_model_id
stage_1_score_id
stage_1_gate_source
score_source_mode
score_source_caveat
stage_1_robustness_selected_n
stage_1_robustness_selected_positive_n
stage_1_robustness_fast_fail_rate
stage_1_robustness_random_p50
stage_1_robustness_single_feature_rate
stage_1_robustness_budget
stage_1_robustness_budget_rank_evaluable
stage_2_model_id
stage_2_score_id
stage_2_stage1_gate_source
stage_2_robustness_selected_n
stage_2_robustness_selected_positive_n
stage_2_robustness_continuation_rate
stage_2_robustness_random_p50
stage_2_robustness_single_feature_rate
stage_2_robustness_budget
stage_2_robustness_budget_rank_evaluable
gate_failure_reasons
next_allowed_requirement
recommended_internal_followup
```

### 11.10 Report / Manifest

Required report:

```text
outputs/publishable/reports/trailing_rank_operating_point_validation_report.md
```

Report 必须用中文，并包含：

1. 为什么 12A6c 的失败是 threshold transport failure，而不是直接判定 no signal；
2. trailing-rank rule 如何满足 PIT，以及为什么 whole-month / whole-split rank 只能做 diagnostic upper bar；
3. stage-1 / stage-2 的 AUC、rank-IC、decile lift；
4. primary tuple `(stage1_budget_X = 0.50, stage2_budget_X = 0.50)` 的 OOS actual budget drift；
5. model vs matched random same-budget 的 robustness 读数；
6. model vs train-frozen single-feature challenger 的 robustness 读数；
7. diagnostic look-ahead upper bar 与 deployable trailing-rank 的差距；
8. 是否进入 12A8 calibration / 12A9 vol-scaled label 后续。

Required manifest:

```text
outputs/manifests/12A7_direction_a_trailing_rank_operating_point_audit_manifest.json
```

Manifest 必须包含：

```text
requirement_hash
config_hash
entrypoint_hash
input_hashes
output_hashes
local_cache_hashes
decision_state
git_revision
created_at_utc
```

## 12. Tests

Required tests:

1. Required 12A6c inputs exist and schemas match this requirement.
2. `two_stage_decision.input_gate_status = pass` and decision state is an allowed upstream state.
3. Score source is either `frozen_row_level_scores`, `pass_exact`, or `pass_near_miss`; fallback reproduction outside near-miss bounds blocks the run.
4. Random path labels are generated by merging sampled random rows with both required path caches on the declared key, and cache-side merge keys are unique.
5. `random_path_label_audit.csv` contains non-null stage-1 / stage-2 random label counts for every non-empty random cell.
6. Primary history policy is `board_then_global_rolling_504_sessions`; expanding-from-inception appears only in diagnostic rows.
7. Stage-1 trailing history uses only rows with `event_t0_pos < current event_t0_pos` and `event_t0_pos >= current event_t0_pos - 504`.
8. Stage-2 trailing history uses only rows with `stage_2_decision_pos < current stage_2_decision_pos` and `stage_2_decision_pos >= current stage_2_decision_pos - 504`.
9. Stage-1 decisions are fully computed before stage-2 denominators and stage-2 history are built.
10. Current-row and future-row labels are never used to compute current percentile.
11. `same_month_full_cohort_rank`, `board_month_full_cohort_rank`, and `whole_split_rank` never appear in primary decision rows.
12. Rows with insufficient history are marked `rank_not_evaluable`, remain in `denominator_n`, are not selectable, and are counted in budget drift audit.
13. `primary_tuple = (stage1_budget_X = 0.50, stage2_budget_X = 0.50)` is the only primary decision budget tuple.
14. Stage-2 chained curve rows use `stage1_budget_X = 0.50`; paired-grid rows with other stage-1 budgets are diagnostic-only.
15. Same-budget random baseline selected counts match model selected budget by split x board_bucket x calendar_month under the correct stage-specific denominator.
16. Stage-2 random applies an analogous random stage-1 keep before forming random no-fast-fail survivor denominator.
17. Stage-2 random denominator includes only random no-fast-fail survivors with stage-2 executable and horizon-complete status.
18. Random baseline preserves sampled-draw / `sample_weight` semantics and does not unique-path de-duplicate.
19. Stage-2 single-feature challenger rows use `stage1_gate_source = primary_model_trailing_rank_keep`.
20. Single-feature challenger feature and orientation are selected on train only and applied unchanged to validation / robustness.
21. Primary model-vs-single-feature deltas use common-denominator matched-selected-n replay; raw trailing challenger rows are diagnostic.
22. OOS best-single rows, if present, carry `diagnostic_only_flag = true`.
23. Stage-1 AUC uses `stage_1_fast_fail_target` and raw `stage1_fast_fail_score`; operating keep still selects lower scores.
24. Stage-1 support gate uses lower fast-fail rate as better.
25. Stage-2 support gate uses higher continuation rate as better.
26. Bootstrap CI direction is correct for each stage; model-vs-random CI resamples both model events and random seeds or is diagnostic-only.
27. Minimum selected-n and positive-n gates block supported status when unmet; every headline readout row includes denominator, rank-evaluable, selected, and bootstrap positive counts.
28. Budget drift audit never reports `pass_by_construction`.
29. Required output schema test passes for every publishable table.
30. Manifest hash sync test passes for report, tables, and local score matrix.
