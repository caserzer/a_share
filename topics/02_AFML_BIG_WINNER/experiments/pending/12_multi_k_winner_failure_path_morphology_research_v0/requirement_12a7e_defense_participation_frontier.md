# 需求：12A7e Defense-Participation Frontier

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、stage-1 rank reconstruction 不可证明、stage-2 candidate selection 不可复现、label 不可复现时 fail closed。
6. 不得从报告文本、聚合表或人工总结反推出事件级特征、标签、stage-1 keep flag、stage-2 score 或 frontier 指标。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7e
run_id = 12A7e_defense_participation_frontier
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7e_defense_participation_frontier.py
expected_config = configs/config_12a7e_defense_participation_frontier.yaml
expected_test_file = tests/test_12a7e_defense_participation_frontier.py
research_plan_source = research_plan_2_stage2_random_baseline_and_defense_participation.md
upstream_requirement = requirement_12a7d_stage2_random_baseline_support_triage.md
```

本需求实现 `research_plan_2_stage2_random_baseline_and_defense_participation.md` 第 5 节：

```text
12A7e: Defense-Participation Frontier
```

12A7e 回答：

```text
How aggressive should stage-1 defense be if the final objective is big-winner capture?
```

它不是 policy replay，也不是重新训练模型；它是一个 train-frozen frontier audit，用同一个 stage-1 simple backbone 特征和同一个 stage-2 deployable candidate，系统比较不同 stage-1 X 对 downside defense、winner participation、stage-2 survivor support 和固定 barrier expectancy proxy 的影响。

## 2. 背景与核心问题

上游已知事实：

```text
12A7b selected stage-1 simple backbone:
  feature = volatility_20d
  orientation = asc
  X = 0.30
  history_policy = board_then_global_rolling_504_sessions

12A7c selected deployable chained stage-2 candidate:
  candidate_id = complex_stage2_score
  stage2_X = 0.30

12A7d final decision:
  decision_state = 12A7d_stage2_signal_diagnostic_only
  recommended_internal_followup = test_whether_stage1_X030_denominator_is_too_narrow
```

12A7d 的关键 insight 是：当前 stage-1 X=0.30 可能过窄，导致 chained survivor denominator 变薄，strict / near-strict random baseline 难以稳定构造。12A7e 因此必须把 X=0.30 从“固定前提”降级为“frontier 上的一个点”，并衡量更宽 stage-1 defense 是否更适合 big-winner capture。

核心解释边界：

```text
If wider X improves winner participation and stage-2 evidence while preserving acceptable fast-fail defense,
then the two-stage architecture is not necessarily failing;
the X=0.30 defense setting may be too aggressive for the right-tail objective.

If no wider X can recover winner participation or stage-2 evidence,
then the current fixed-barrier stage-2 signal may be structurally weak
or the fixed -10% / +20% label design may be insufficient.
```

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不改变 fast-fail / continuation label，不做 vol-scaled barrier；
- 不重新训练 stage-1 或 stage-2 模型；
- 不重新选择 stage-1 feature、orientation 或 history policy；
- 不重新选择 stage-2 candidate family、feature set、model family 或 stage2_X；
- 不用 validation 或 robustness 选择 preferred X；
- 不声明 X=1.00 是可部署策略，只把它作为 no-stage-1-defense anchor；
- 不把 decoupled ground-truth survivor 当作可部署策略；
- 不把 nominal barrier expectancy proxy 解释成交易 PnL；
- 不做 position sizing、holding period、transaction cost、slippage、资金曲线或 policy replay；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不声明可交易 alpha。

## 4. 必需输入

### 4.1 上游 decision 和 report artifacts

必需输入：

```text
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/direction_c_decision.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_train_selection.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_operating_point_readout.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_random_same_budget_audit.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/direction_e_decision.csv
outputs/publishable/tables/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_train_selection.csv
outputs/publishable/tables/12A7d_stage2_random_baseline_support_triage/stage2_chained_sensitivity_decision.csv
outputs/publishable/tables/12A7d_stage2_random_baseline_support_triage/frozen_candidate_reconciliation.csv
outputs/publishable/tables/12A7d_stage2_random_baseline_support_triage/random_replay_variant_readout.csv
outputs/publishable/reports/stage2_random_baseline_triage_report.md
outputs/manifests/12A7d_stage2_random_baseline_support_triage_manifest.json
```

Required `direction_c_decision.csv` fields:

```text
decision_state
input_gate_status
pit_gate_status
phase_1_simple_backbone_gate_status
selected_primary_rule_id
selected_primary_simple_backbone_tuple
selected_primary_X
robustness_fast_fail_rate
robustness_delta_vs_random_p50
robustness_delta_vs_random_p50_ci95_high
gate_failure_reasons
```

Required `direction_e_decision.csv` fields:

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
selected_chained_candidate_id
selected_chained_candidate_family
selected_chained_X
selected_chained_deployable_at_stage_2_decision_time
gate_failure_reasons
next_allowed_requirement
recommended_internal_followup
```

Required 12A7d `stage2_chained_sensitivity_decision.csv` fields:

```text
decision_state
input_gate_status
candidate_reconciliation_status
random_source_status
selected_chained_candidate_id
selected_chained_candidate_family
selected_chained_X
stage1_anchor_rule_id
stage1_anchor_feature
stage1_anchor_orientation
stage1_anchor_X
allowed_interpretation
next_allowed_requirement
recommended_internal_followup
```

Required 12A7d `frozen_candidate_reconciliation.csv` fields:

```text
denominator_type
candidate_id
candidate_family
stage2_budget_X
split
recomputed_selected_n
upstream_selected_n
recomputed_selected_positive_n
upstream_selected_positive_n
recomputed_selected_budget_rank_evaluable
upstream_selected_budget_rank_evaluable
candidate_reconciliation_status
```

### 4.2 Row-level candidate source

Canonical row-level source:

```text
outputs/local_cache/12A7c_direction_e_stage2_decoupling_chained_readouts/stage2_decoupling_score_matrix.parquet
```

Fallback row-level sources, used only when `stage2_decoupling_score_matrix.parquet`
is missing a required row-level column:

```text
outputs/local_cache/12A7_direction_a_trailing_rank_operating_point_audit/trailing_rank_score_matrix.parquet
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_score_matrix.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_matrix.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
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
calendar_quarter
path_key
source_arm_is_c0
market_regime_bucket
stage_1_evaluable
stage_1_fast_fail_target
no_fast_fail_L10_H20
stage_2_path_evaluable
stage_2_entry_blocked
stage_2_horizon_complete_20d
stage_2_decision_pos
stage_2_continuation_target
stage2_label_read_status
stage2_continuation_score
stage1_anchor_rank_percentile
stage1_anchor_rank_status
stage1_anchor_selected_flag
volatility_20d
```

Primary scope:

```text
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage_1_evaluable = true
```

The implementation must treat `stage2_decoupling_score_matrix.parquet` as
row-level evidence, not as a decision summary. It may use the 12A7c
`stage1_anchor_rank_percentile` only after proving that it reconstructs the
12A7b/12A7c X=0.30 selected counts by split.

Fallback rules:

```text
stage2_continuation_score may be rebuilt only from
  trailing_rank_score_matrix.parquet keyed by meta_event_id / instrument /
  event_t0_pos / stage_2_decision_pos;

stage-1 anchor rank inputs may be rebuilt only from
  simple_backbone_score_matrix.parquet using volatility_20d__rank_percentile
  and volatility_20d__rank_status;

stage-1 feature inputs may be rebuilt only from
  simple_backbone_score_matrix.parquet or two_stage_feature_matrix.parquet;

stage-2 path / label fields may be rebuilt only from stage2_path_cache.parquet
  joined on path_key / instrument / entry_pos / entry_price.
```

If any required score-matrix column is absent and cannot be rebuilt from the
explicit fallback sources above with audited one-to-one keys:

```text
candidate_reconstruction_status = fail
decision_state = 12A7e_blocked_input_or_lineage_failure
```

### 4.3 Random baseline source

Required random source for stage-1 fast-fail and stage-2 continuation random baselines:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/entry_forward_path_cache.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

Required random input columns:

```text
seed
sample_draw_id
path_key
split
board_bucket
calendar_month
calendar_quarter
random_trade_open_date
instrument
entry_pos
entry_price
replacement_draw_index
```

Required `entry_forward_path_cache.parquet` columns:

```text
path_key
instrument
entry_pos
entry_price
entry_blocked
horizon_complete_20d
time_to_lower_minus_10_20d
```

Required `stage2_path_cache.parquet` columns:

```text
path_key
instrument
entry_pos
entry_price
stage_2_entry_blocked
stage_2_horizon_complete_20d
continuation_U20_L10_H2_20
```

Cache join key for both caches:

```text
path_key
instrument
entry_pos
entry_price
```

Both cache files must be unique on the join key. These columns must be proven
by the corresponding 12A6b / 12A6c manifest schema when available, and the
direct file schema must always be checked in `input_artifact_audit.csv`.

Derived random stage-1 fields:

```text
random_stage_1_fast_fail_read_status = pass iff
  entry_blocked = false
  AND horizon_complete_20d = true

random_stage_1_fast_fail_target =
  time_to_lower_minus_10_20d is not null

random_stage_1_evaluable =
  random_stage_1_fast_fail_read_status = pass

random_no_fast_fail_L10_H20 =
  random_stage_1_evaluable = true
  AND time_to_lower_minus_10_20d is null
```

This must match the 12A7b random replay semantics exactly: `entry_blocked`
and `horizon_complete_20d` determine whether the random path label is readable;
`time_to_lower_minus_10_20d.notna()` determines the fast-fail positive target
for readable rows.

Derived random stage-2 fields:

```text
random_stage2_label_join_status = pass iff
  the random row has a unique `stage2_path_cache.parquet` match
  on path_key / instrument / entry_pos / entry_price

random_stage_2_evaluable =
  random_stage2_label_join_status = pass
  AND stage_2_entry_blocked = false
  AND stage_2_horizon_complete_20d = true

random_stage2_label_read_status = pass iff
  random_stage_2_evaluable = true
  AND continuation_U20_L10_H2_20 is finite/readable

random_stage_2_continuation_target =
  continuation_U20_L10_H2_20
```

If any required random source column is missing, a random row has no required
cache match, a cache join key is duplicated, or any sampled row has
`random_stage_1_fast_fail_read_status != pass` for stage-1 replay or
`random_stage2_label_read_status != pass` for stage-2 replay, 12A7e must fail
closed:

```text
decision_state = 12A7e_blocked_input_or_lineage_failure
```

## 5. Input Gates

12A7e may proceed only if all are true:

```text
12A7b direction_c_decision.input_gate_status = pass
12A7b direction_c_decision.pit_gate_status = pass
12A7b direction_c_decision.phase_1_simple_backbone_gate_status = pass
12A7b selected_primary_simple_backbone_tuple = volatility_20d
12A7b selected_primary_X = 0.30

12A7c direction_e_decision.stage1_anchor_reconstruction_status = pass
12A7c selected_chained_deployable_at_stage_2_decision_time = true
12A7c selected_chained_candidate_id is not null
12A7c selected_chained_X is not null

12A7d input_gate_status = pass
12A7d candidate_reconciliation_status = pass
12A7d random_source_status = pass
12A7d next_allowed_requirement = requirement_12a7e_defense_participation_frontier.md
```

Allowed 12A7d upstream states:

```text
12A7d_stage2_signal_diagnostic_only
12A7d_random_baseline_support_insufficient
12A7d_stage2_not_supported
12A7d_strict_chained_stage2_supported
12A7d_chained_stage2_supported_with_baseline_caveat
```

Blocked 12A7d upstream state:

```text
12A7d_blocked_input_or_lineage_failure
```

If any input gate fails:

```text
decision_state = 12A7e_blocked_input_or_lineage_failure
next_allowed_requirement = none
```

## 6. Frozen Frontier Contract

### 6.1 Stage-1 backbone

Stage-1 backbone is frozen to:

```text
stage1_feature = volatility_20d
stage1_orientation = asc
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
```

Only X varies:

```text
stage1_X_grid = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00]
```

The selected flag for each X is:

```text
if X < 1.00:
  stage1_selected_flag_X =
    stage1_anchor_rank_status = rank_evaluable
    AND stage1_anchor_rank_percentile <= X

if X = 1.00:
  stage1_selected_flag_X =
    stage_1_evaluable = true
```

`X = 1.00` is the no-stage-1-defense anchor. It is not allowed to claim downside defense. It exists to measure how much winner participation is lost by stage-1 filtering.

### 6.2 Frozen stage-2 candidate

Stage-2 candidate is frozen from 12A7c / 12A7d:

```text
stage2_candidate_id = selected_chained_candidate_id
stage2_candidate_family = selected_chained_candidate_family
stage2_feature = stage2_continuation_score
stage2_orientation = desc
stage2_X = selected_chained_X
```

Stage-2 PIT rank policy is also frozen to 12A7c:

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
stage_2_global_min_history_n = 250
stage_2_board_min_history_n = 75
```

For each current stage-2 decision row:

```text
rank_frame = denominator-X-specific full chronological stage-2 frame
rank_frame for X contains only rows satisfying stage2_denominator_X
rank_history_X = rows in the same rank_frame for the same X
  with stage_2_decision_pos < current_stage_2_decision_pos
rank_history_X must be a subset of denominator_X for the same stage1_X
rank_history must not be split-local
validation / robustness ranks may use prior train / validation rows only if
  their stage_2_decision_pos is earlier than the current row
different stage1_X values must not share or borrow stage-2 rank histories
if board-specific history has at least stage_2_board_min_history_n rows:
  rank within board-specific trailing history
else if global history has at least stage_2_global_min_history_n rows:
  rank within global trailing history
else:
  stage2_rank_status = rank_not_evaluable
```

Rows with `stage2_rank_status != rank_evaluable` must not be stage-2 selected.

For every stage1_X:

```text
stage2_denominator_X =
  stage1_selected_flag_X = true
  AND no_fast_fail_L10_H20 = true
  AND stage_2_path_evaluable = true
  AND stage_2_entry_blocked = false
  AND stage_2_horizon_complete_20d = true
  AND stage2_label_read_status = pass
  AND stage_2_decision_pos is finite
```

Stage-2 selected rows are the top `stage2_X` fraction by PIT trailing rank of
`stage2_continuation_score` within the deployable stage-2 denominator. The
implementation must use the frozen rank policy above and must not recompute
stage-2 rank using future rows.

### 6.3 X=0.30 reconstruction gate

Before evaluating the frontier, the implementation must reconstruct the frozen X=0.30 counts:

```text
stage1 selected_n by split must match 12A7b / 12A7c within integer equality
stage2 selected_n by split must match 12A7c / 12A7d chained selected counts
stage2 selected_positive_n by split must match 12A7c / 12A7d chained positives
stage2 selected_budget_rank_evaluable must match within 1e-12
```

If reconstruction fails:

```text
candidate_reconstruction_status = fail
decision_state = 12A7e_blocked_input_or_lineage_failure
```

## 7. Metrics

For each `stage1_X`, `split`, and optional slice, compute:

```text
stage1_entry_n
stage1_anchor_role
stage1_rank_evaluable_n
stage1_selected_n
stage1_selected_budget_total
stage1_selected_budget_rank_evaluable
stage1_rank_not_evaluable_rate
stage1_fast_fail_positive_n
stage1_fast_fail_rate
stage1_base_fast_fail_rate
stage1_delta_vs_base_fast_fail
stage1_random_p05
stage1_random_p50
stage1_random_p95
stage1_delta_vs_random_p50
stage1_delta_vs_random_p50_ci95_low
stage1_delta_vs_random_p50_ci95_high
stage1_random_valid_seed_n
stage1_random_support_status

ground_truth_survivor_n
ground_truth_survivor_continuation_positive_n
ground_truth_survivor_continuation_rate
chained_survivor_n
chained_survivor_positive_n
chained_survivor_share_of_ground_truth
chained_survivor_continuation_rate
continuation_positive_capture_rate

stage2_selected_n
stage2_selected_continuation_positive_n
stage2_selected_continuation_rate
stage2_selected_positive_capture_rate
stage2_selected_budget_rank_evaluable
stage2_random_support_status
stage2_random_p50
stage2_delta_vs_random_p50
stage2_delta_vs_random_p50_ci95_low
stage2_random_valid_seed_n

nominal_barrier_expectancy_proxy
frontier_dominance_status
frontier_readout_status
diagnostic_only_flag
```

Definitions:

```text
stage1_entry_n =
  count of primary scope rows in the split

stage1_anchor_role =
  x030_reference if stage1_X = 0.30;
  no_stage1_defense_anchor if stage1_X = 1.00;
  frontier_candidate otherwise

stage1_fast_fail_rate =
  stage1_fast_fail_positive_n / stage1_selected_n

stage1_base_fast_fail_rate =
  fast-fail rate across all primary scope rows in the split before X filtering

stage1_delta_vs_base_fast_fail =
  stage1_fast_fail_rate - stage1_base_fast_fail_rate

train_x100_unfiltered_fast_fail_rate =
  stage1_fast_fail_rate from the train row where stage1_X = 1.00

frontier_readout_status enum =
  ok
  stage1_random_support_insufficient
  stage2_random_support_insufficient_with_stage1_supported
  stage1_and_stage2_random_support_insufficient
  reconstruction_failed
  blocked_input_or_lineage_failure

frontier_readout_status =
  ok iff candidate reconstruction passes, stage1_random_support_status = pass,
  and stage2_random_support_status = pass;
  stage1_random_support_insufficient iff stage1_random_support_status = insufficient
  and stage2_random_support_status = pass;
  stage2_random_support_insufficient_with_stage1_supported iff
  stage1_random_support_status = pass and stage2_random_support_status = insufficient;
  stage1_and_stage2_random_support_insufficient iff both are insufficient

ground_truth_survivor_n =
  count of primary scope rows satisfying no_fast_fail_L10_H20,
  stage_2_path_evaluable, stage_2_entry_blocked = false,
  stage_2_horizon_complete_20d, stage2_label_read_status = pass,
  and finite stage_2_decision_pos before stage-1 X filtering

chained_survivor_n =
  count of rows satisfying stage1_selected_flag_X and stage-2 denominator_X

chained_survivor_share_of_ground_truth =
  chained_survivor_n / ground_truth_survivor_n

continuation_positive_capture_rate =
  chained_survivor_positive_n / ground_truth_survivor_continuation_positive_n

stage2_selected_continuation_rate =
  stage2_selected_continuation_positive_n / stage2_selected_n

stage2_selected_positive_capture_rate =
  stage2_selected_continuation_positive_n / stage1_entry_n

nominal_barrier_expectancy_proxy =
  0.20 * stage2_selected_positive_capture_rate
  - 0.10 * stage1_fast_fail_rate
```

The proxy must not use survivor-conditional `stage2_selected_continuation_rate`. It is an entry-level fixed-barrier comparison proxy, not trading PnL.

## 8. Stage-1 Random Same-Budget Baseline

For every `stage1_X`, construct a stage-1 random same-budget baseline on the canonical random source.

Requested counts:

```text
for each split x board_bucket x calendar_month:
  requested_selected_n = count(stage1_selected_flag_X = true)
```

For each random seed:

```text
sample requested_selected_n rows without replacement from the same
split x board_bucket x calendar_month random pool;
compute random_stage_1_fast_fail_target;
compute random_fast_fail_rate by split.
```

Required pass condition:

```text
stage1_random_valid_seed_n >= 100
```

If strict exact stage-1 random replay is insufficient for any X, the frontier row may still be emitted as diagnostic, but:

```text
stage1_random_support_status = insufficient
frontier_readout_status = stage1_random_support_insufficient
```

No coarser random fallback is allowed for selecting preferred X in 12A7e. Coarser random fallback belongs to a later explicitly named diagnostic if needed.

## 9. Stage-2 Random Readout

Stage-2 random readout is diagnostic in 12A7e and must not reuse 12A7d's coarser baseline variants as if they were strict support.

Minimum required stage-2 random readout:

```text
for each stage1_X and split:
  strict exact random support status if constructible
  stage2_random_valid_seed_n
  stage2_random_p50
  stage2_delta_vs_random_p50
  stage2_delta_vs_random_p50_ci95_low
```

The implementation may use the 12A7d strict exact replay logic generalized to each `stage1_X`, but it must record `stage2_random_support_status`. If strict support is insufficient, stage2 random fields may be `NA`, and `frontier_readout_status` must explain the insufficiency.

The frontier decision must not select X solely because weak stage-2 random variants look favorable.

## 10. Train-Only Preferred X Selection

12A7e is a frontier audit, not an OOS X re-selection exercise. If a preferred X is emitted, it must be selected using train split rows only.

Forbidden:

```text
choose preferred X using validation continuation outcomes
choose preferred X using robustness continuation outcomes
choose preferred X using report text or visual inspection
choose preferred X using any metric not written in train frontier rows
```

Train eligibility for preferred X:

```text
frontier_readout_status = ok or stage2_random_support_insufficient_with_stage1_supported
stage1_random_valid_seed_n >= 100
stage1_delta_vs_random_p50_ci95_high < 0
stage1_fast_fail_rate <= train_x100_unfiltered_fast_fail_rate - 0.02
stage2_selected_n >= 150
stage2_selected_continuation_positive_n >= 30
nominal_barrier_expectancy_proxy is finite
```

Diagnostic participation guard, not a train eligibility gate:

```text
chained_survivor_share_guard_threshold = 0.50
chained_survivor_share_guard_status =
  pass if chained_survivor_share_of_ground_truth >= 0.50
  else below_diagnostic_threshold
```

This guard must be reported, but it must not exclude a narrow X from train
selection by itself. The frontier is explicitly testing whether narrow X harms
winner participation; using a monotone survivor-share field as a hard gate would
prejudge that question.

Primary train objective:

```text
maximize nominal_barrier_expectancy_proxy
```

Tie-breaks:

```text
1. larger continuation_positive_capture_rate
2. lower stage1_fast_fail_rate
3. larger stage2_selected_n
4. smaller stage1_X
```

The selected row must be written as:

```text
selection_split = train
preferred_X_if_train_selected
train_selection_status
tie_break_path
```

Validation and robustness may only report where the train-selected X ranks on their own frontiers:

```text
validation_frontier_rank_for_preferred_X
robustness_frontier_rank_for_preferred_X
lookahead_selection_guard_status = pass
```

If no train row passes eligibility:

```text
preferred_X_if_train_selected = NA
train_selection_status = no_train_frontier_candidate
```

## 11. Pareto Frontier

A row is Pareto dominated within a split if another X satisfies all:

```text
other.stage1_fast_fail_rate <= current.stage1_fast_fail_rate
other.continuation_positive_capture_rate >= current.continuation_positive_capture_rate
other.stage2_selected_positive_capture_rate >= current.stage2_selected_positive_capture_rate
other.nominal_barrier_expectancy_proxy >= current.nominal_barrier_expectancy_proxy
other.stage1_selected_budget_rank_evaluable within budget_drift tolerance
at least one comparison is strict
```

Budget drift tolerance:

```text
budget_abs_delta_rank_evaluable_vs_X <= 0.02
```

Required Pareto fields:

```text
pareto_frontier_flag
dominates_x_list
dominated_by_x_list
frontier_rank_by_proxy
frontier_rank_by_capture
frontier_rank_by_fast_fail
```

The report must show train, validation, and robustness Pareto frontiers separately.

## 12. Decision Map

Decision states:

```text
12A7e_wider_stage1_frontier_preferred_for_winner_capture:
  train selects preferred_X_if_train_selected > 0.30;
  preferred X is Pareto-efficient on train;
  validation and robustness do not show severe downside-defense collapse;
  robustness chained_survivor_share_of_ground_truth improves vs X=0.30.

12A7e_no_stage1_width_recovers_winner_participation:
  X=1.00 or widest X has materially higher participation,
  but fast-fail defense collapses or nominal proxy does not improve,
  so a no-defense architecture is not supported.

12A7e_x030_defense_optimal_for_downside_not_winner:
  train-selected preferred_X_if_train_selected = 0.30,
  or train-selected preferred_X_if_train_selected < 0.30 and the report
  explicitly labels the result as tighter-than-X030 defense;
  X=0.30 or tighter remains best for the train objective,
  but wider X dominates winner participation metrics,
  implying objective conflict between downside defense and right-tail capture.

12A7e_x030_frontier_preferred_confirmed:
  train-selected preferred_X_if_train_selected = 0.30;
  no wider X has material participation improvement after defense/proxy checks.

12A7e_tighter_stage1_frontier_preferred_for_downside_defense:
  train-selected preferred_X_if_train_selected < 0.30;
  report must state that the train objective preferred a more aggressive
  defense than the upstream X=0.30 anchor.

12A7e_policy_objective_split_required:
  train frontier has no single X that jointly preserves downside defense
  and improves winner capture; report recommends separating defense overlay
  from winner-capture policy objective.

12A7e_blocked_input_or_lineage_failure:
  required input, schema, PIT, split, reconstruction, label, or upstream gate fails.
```

Decision precedence:

```text
1. If input / lineage / PIT / label / reconstruction gate fails:
     decision_state = 12A7e_blocked_input_or_lineage_failure

2. Else if a train row is selected and preferred_X_if_train_selected > 0.30
   and robustness participation improves vs X=0.30 without severe fast-fail collapse:
     decision_state = 12A7e_wider_stage1_frontier_preferred_for_winner_capture

3. Else if a train row is selected and preferred_X_if_train_selected > 0.30
   and (
     robustness participation does not improve vs X=0.30
     OR severe fast-fail collapse is observed
   ):
     decision_state = 12A7e_policy_objective_split_required

4. Else if a train row is selected and preferred_X_if_train_selected = 0.30
   and no wider X has material participation improvement:
     decision_state = 12A7e_x030_frontier_preferred_confirmed

5. Else if a train row is selected and preferred_X_if_train_selected = 0.30
   and at least one wider X has material participation improvement:
     decision_state = 12A7e_x030_defense_optimal_for_downside_not_winner

6. Else if a train row is selected and preferred_X_if_train_selected < 0.30
   and no wider X has material participation improvement:
     decision_state = 12A7e_tighter_stage1_frontier_preferred_for_downside_defense

7. Else if a train row is selected and preferred_X_if_train_selected < 0.30
   and at least one wider X has material participation improvement:
     decision_state = 12A7e_x030_defense_optimal_for_downside_not_winner

8. Else if no train row passes eligibility
   and the X=1.00 row or widest available X row has material participation recovery
   but severe fast-fail collapse or train nominal proxy does not improve vs X=0.30:
     decision_state = 12A7e_no_stage1_width_recovers_winner_participation

9. Else if no train row passes eligibility:
     decision_state = 12A7e_policy_objective_split_required

10. Else:
     decision_state = 12A7e_policy_objective_split_required
```

Severe fast-fail collapse definition:

```text
stage1_fast_fail_rate >= x030_stage1_fast_fail_rate + 0.05
AND stage1_delta_vs_random_p50_ci95_high >= 0
```

Material participation improvement definition:

```text
survivor_share_material_lift_min = 0.10
positive_capture_material_lift_min = 0.05

chained_survivor_share_of_ground_truth >=
  x030_share + survivor_share_material_lift_min
OR continuation_positive_capture_rate >=
  x030_capture_rate + positive_capture_material_lift_min
```

The two thresholds are intentionally separate because survivor share and
positive capture rate have different bases and variance profiles.

Nominal proxy does not improve definition:

```text
train_nominal_barrier_expectancy_proxy <= x030_train_proxy
```

## 13. Required Outputs

Output directory:

```text
outputs/publishable/tables/12A7e_defense_participation_frontier/
```

Required tables:

```text
input_artifact_audit.csv
stage1_x_grid_card.csv
frontier_candidate_reconstruction.csv
stage1_frontier_readout.csv
stage2_frontier_readout.csv
defense_participation_frontier.csv
pareto_frontier_audit.csv
stage1_random_same_budget_audit.csv
stage2_random_support_audit.csv
frontier_selection_audit.csv
defense_participation_decision.csv
```

Report:

```text
outputs/publishable/reports/defense_participation_frontier_report.md
```

Manifest:

```text
outputs/manifests/12A7e_defense_participation_frontier_manifest.json
```

Local cache:

```text
outputs/local_cache/12A7e_defense_participation_frontier/frontier_selection_matrix.parquet
outputs/local_cache/12A7e_defense_participation_frontier/stage2_rank_matrix_by_x.parquet
outputs/local_cache/12A7e_defense_participation_frontier/bootstrap_replicates.parquet
```

The manifest must include sha256 for every publishable table, report, config, requirement, and local-cache artifact. Report and manifest hashes must be synchronized after report generation.

## 14. Required Schemas

### 14.1 `defense_participation_frontier.csv`

Required fields:

```text
stage1_X
split
stage1_entry_n
stage1_anchor_role
stage1_rank_evaluable_n
stage1_selected_n
stage1_selected_budget_total
stage1_selected_budget_rank_evaluable
stage1_budget_abs_delta_rank_evaluable_vs_X
stage1_rank_not_evaluable_rate
stage1_fast_fail_positive_n
stage1_fast_fail_rate
stage1_base_fast_fail_rate
stage1_delta_vs_base_fast_fail
stage1_random_p05
stage1_random_p50
stage1_random_p95
stage1_delta_vs_random_p50
stage1_delta_vs_random_p50_ci95_low
stage1_delta_vs_random_p50_ci95_high
stage1_random_valid_seed_n
stage1_random_support_status
ground_truth_survivor_n
ground_truth_survivor_continuation_positive_n
ground_truth_survivor_continuation_rate
chained_survivor_n
chained_survivor_positive_n
chained_survivor_share_of_ground_truth
chained_survivor_continuation_rate
continuation_positive_capture_rate
stage2_selected_n
stage2_selected_continuation_positive_n
stage2_selected_continuation_rate
stage2_selected_positive_capture_rate
stage2_selected_budget_rank_evaluable
stage2_random_support_status
stage2_random_valid_seed_n
stage2_random_p50
stage2_delta_vs_random_p50
stage2_delta_vs_random_p50_ci95_low
nominal_barrier_expectancy_proxy
pareto_frontier_flag
frontier_rank_by_proxy
frontier_readout_status
diagnostic_only_flag
```

### 14.2 `frontier_selection_audit.csv`

Required fields:

```text
selection_split
stage1_X
train_eligible_flag
eligibility_failure_reasons
nominal_barrier_expectancy_proxy
continuation_positive_capture_rate
chained_survivor_share_of_ground_truth
chained_survivor_share_guard_status
stage1_fast_fail_rate
stage2_selected_n
stage2_selected_continuation_positive_n
frontier_rank_by_proxy
tie_break_rank
tie_break_path
selected_flag
lookahead_selection_guard_status
validation_frontier_rank_for_selected_X
robustness_frontier_rank_for_selected_X
```

### 14.3 `defense_participation_decision.csv`

Required fields:

```text
decision_state
input_gate_status
candidate_reconstruction_status
stage1_random_source_status
stage2_random_source_status
selection_split
preferred_X_if_train_selected
x030_train_proxy
x030_validation_proxy
x030_robustness_proxy
preferred_train_proxy
preferred_validation_proxy
preferred_robustness_proxy
x030_robustness_chained_survivor_share
preferred_robustness_chained_survivor_share
x030_robustness_fast_fail_rate
preferred_robustness_fast_fail_rate
robustness_frontier_rank_for_preferred_X
lookahead_selection_guard_status
next_allowed_requirement
recommended_internal_followup
```

## 15. Report Requirements

The report must be written in Chinese and include:

```text
final decision_state
stage-1 X grid and train-selected preferred X if any
X=0.30 baseline row
X=1.00 no-defense anchor row
train / validation / robustness Pareto frontier tables
fast-fail defense vs winner participation tradeoff plot-ready table
stage2 survivor denominator expansion by X
stage2 selected continuation rate and positive capture by X
nominal_barrier_expectancy_proxy by X
strict random support status by X
why preferred X was or was not selected
lookahead guard statement
recommended next requirement
```

The report must explicitly answer:

```text
Is the two-stage architecture failing because stage-2 has no deployable signal,
or because stage-1 X=0.30 removes too much of the right-tail opportunity set?
```

Required interpretation:

```text
If wider X improves participation but weakens fast-fail defense:
  explain the objective conflict.

If wider X improves both proxy and participation:
  recommend using 12A7e frontier result as the next denominator for
  a follow-up stage-2 random-baseline support test.

If no X improves participation and proxy:
  recommend 12A8 calibration or 12A9 label revision only after explaining
  why denominator widening failed.
```

## 16. Required Tests

1. Path resolver handles `topics/`, `experiments/`, `outputs/`, `configs/`, `src/`, and `tests/` prefixes.
2. Input gate fails closed when 12A7d is `12A7d_blocked_input_or_lineage_failure`.
3. `stage1_X_grid` equals `[0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00]`; no hidden X values are allowed.
4. X=1.00 keeps all `stage_1_evaluable` rows and is marked `no_stage1_defense_anchor`.
5. X=0.30 reconstruction exactly matches 12A7b / 12A7c / 12A7d selected counts and positives by split.
6. Stage-1 selected rows use `stage1_anchor_rank_percentile <= X` for `asc` orientation and never use future rows.
7. Stage-2 denominator for each X is a subset of the stage-1 selected rows for that X.
8. Stage-2 candidate remains `complex_stage2_score` with `stage2_X = 0.30` for all stage1_X values.
9. `stage2_selected_positive_capture_rate` uses `stage1_entry_n` as denominator, not `stage2_selected_n`.
10. `nominal_barrier_expectancy_proxy` uses `stage2_selected_positive_capture_rate`, not survivor-conditional continuation rate.
11. Train preferred X selection reads only train frontier rows.
12. Validation and robustness cannot change `preferred_X_if_train_selected`.
13. Pareto dominance uses the four required objectives and requires at least one strict improvement.
14. `stage1_random_valid_seed_n < 100` marks the row as random-support insufficient.
15. If no train row is eligible, decision is not a hidden robustness-picked X.
16. `defense_participation_decision.csv` contains `lookahead_selection_guard_status`.
17. Report includes X=0.30 and X=1.00 rows explicitly.
18. Manifest includes report hash and local-cache hashes.
19. `frozen_candidate_reconciliation.csv` is required and X=0.30 reconstruction reads it for split-level selected count, positive count, and budget equality.
20. Stage-2 random replay requires `stage2_path_cache.parquet`, validates cache-key uniqueness, and derives `random_stage2_label_read_status` and `random_stage_2_continuation_target`.
21. Stage-2 PIT rank recomputation uses the frozen 12A7c rank policy, including stage-2 min-history thresholds and non-split-local chronological history.
22. Different `stage1_X` values do not share stage-2 rank histories; each `rank_history_X` is a subset of its own `denominator_X`.
23. Missing `stage2_decoupling_score_matrix.parquet` columns are rebuilt only from explicit fallback sources with audited one-to-one keys, otherwise the run fails closed.
24. `chained_survivor_share_guard_status` is reported but does not exclude a train row from eligibility by itself.
25. Decision-state tests cover mutually exclusive train outcomes: `preferred_X > 0.30`, `preferred_X = 0.30`, `preferred_X < 0.30`, and no eligible train row.
26. `12A7e_no_stage1_width_recovers_winner_participation` is reachable before the generic no-train-candidate fallback when only X=1.00 or the widest X recovers participation but fails defense/proxy checks.

## 17. One-line Thesis

12A7e turns the 12A7d diagnostic into a frontier problem: if stage-1 X=0.30 is too defensive for right-tail participation, the next credible stage-2 experiment must first widen the deployable chained denominator under train-only selection discipline, rather than forcing policy replay on a denominator whose strict random baseline cannot support it.
