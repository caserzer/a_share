# Explore9 扩展需求 4：P0.8 Gate 组合与 LGBM 非线性 Launch / Failure Scoring 探索

## 0. 文档状态

```text
requirement_id: Explore9_expand_4_p0_8
phase: P0.8
phase_name: Gate Combination + LGBM Nonlinear Launch / Failure Scoring Discovery
review_fix_version: review15_implementation_ready_final
created_for: Explore9
research_window: 2017-01-01 至 2024-12-31
observed_reference_window: 2025-01-01 至 2026-04-30
artifact_prefix: p0_8_
output_root: Explore9/outputs/
primary_command_profile: profile-p0-8
primary_command_report: report-p0-8
```

P0.8 是 Explore9 broad discovery 的第三轮扩展，接在 P0.7AB 之后。

P0.8 的任务是：在 P0.7AB 已经建立的 `launch_stratum_event` 与 `failure_filter_opportunity` 分母上，用可解释 gate 组合和受审计的 LGBM 非线性打分，研究 launch / failure context 之间是否存在单一公式无法捕捉的交互结构。

P0.8 不是策略建模，不是最终买卖模型，不是 Explore10 回测入口，也不是 clean OOS proof。P0.8 最多输出 `candidate_for_p1_refine`，不能输出 `validated_p1_rule`、`clean_oos_proven_rule`、`ready_for_backtest`、`freeze_strategy` 或 `proceed_to_explore10_backtest`。

---

## 1. Binding review-fix rules

本节是强制实现口径。如果后文任何表述与本节冲突，以本节为准。

### 1.1 P0.8 validation 只能是 robustness validation

P0.8 的 seed context 来自 P0.7AB 已经检查过的 2017-2024 research window。因此 P0.8 的 walk-forward validation 必须被描述为：

```text
robustness validation inside an already-inspected research window
hypothesis-generating evidence
not clean OOS proof
not frozen P1 validation
```

P1 refine 如果要证明候选成立，必须在 P0.8 之后冻结候选定义、冻结 features、冻结 score bucket、冻结阈值，并重新做独立 refine / holdout protocol。

### 1.2 Fold role 与 P1 promotion OOF

P0.8 使用 purged expanding walk-forward：

```text
fold_2020: train 2017-2019, validation 2020
fold_2021: train 2017-2020, validation 2021
fold_2022: train 2017-2021, validation 2022
fold_2023: train 2017-2022, validation 2023
fold_2024: train 2017-2023, validation 2024
```

但 P1 promotion 与 robustness audit 必须分开：

```text
validation_fold_role:
  p1_promotion_eligible
  robustness_audit_only
```

默认 fold role：

```text
fold_2020: p1_promotion_eligible
fold_2021: p1_promotion_eligible
fold_2022: p1_promotion_eligible
fold_2023: p1_promotion_eligible
fold_2024: robustness_audit_only
```

原因：P0.8 允许 2025-2026 只作为 pre-2025 decision 的 forward label measurement，但 observed reference 不得用于 promote P1 candidates。因此 `fold_2024` 可以保留为 robustness audit、stress check、calibration check 和 report context，但不得进入 P1 promotion OOF aggregate。

必须输出两个聚合口径：

```text
p0_8_oof_robustness_all_folds.csv:
  includes fold_2020 ... fold_2024;
  fold_2024 may use 2025-2026 only for pre-2025 decision forward label measurement;
  used for robustness reporting only.

p0_8_p1_promotion_oof_aggregation.csv:
  includes only validation_fold_role = p1_promotion_eligible;
  excludes fold_2024 by default;
  excludes any row / fold where label_measurement_uses_observed_reference = true;
  is the only source for candidate_for_p1_refine eligibility.
```

所有 `min_validation_years`、`min_validation_folds`、`positive_validation_fold_count` 类门槛只能在 `p1_promotion_eligible` folds 上检查。若某候选只靠 `fold_2024` 才过关，必须标记：

```text
p1_rejected_due_to_fold2024_audit_only_dependence = true
```

### 1.3 Observed-reference label-measurement rule

必须拆分三种 overlap：

```text
observed_reference_decision_overlap:
  decision / signal / effective / feature_asof date 落在 observed_reference_start 之后。
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_feature_overlap:
  feature value 需要 observed_reference_start 之后的数据才能计算。
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_label_measurement_overlap:
  decision / feature date 仍在 research_end 之前，
  但 forward label measurement window 跨入 2025-2026 observed reference。
  只允许用于 pre-2025 decision 的 forward outcome measurement。
```

硬规则：

```text
2025-2026 data may be used only to measure forward outcomes for decisions made on or before 2024-12-31.
2025-2026 data may not be used to create features, choose thresholds, choose gates, choose buckets, choose hyperparameters, or promote P1 candidates.
fold_2024_validation_role = robustness_audit_only
fold_2024_included_in_p1_promotion_oof = false
fold_2024_allowed_to_use_observed_reference_for_label_measurement = true
```

原字段 `observed_reference_overlap` 如果继续保留，只能作为兼容字段：

```text
observed_reference_overlap = observed_reference_decision_overlap or observed_reference_feature_overlap
```

不得把 `observed_reference_label_measurement_overlap = true` 误当成样本排除条件；但这些行只能进入 robustness audit，不能进入 P1 promotion aggregate。

### 1.4 Stable candidate identity

Stable candidate identity 必须包含公式语义、token 列表和阈值来源。不得只用 normalized formula 名称聚合，因为同名公式在不同 fold 中可能使用不同 train-optimized threshold 或不同 train-quantile policy。

Gate candidate：

```text
gate_stable_candidate_id = hash(
  model_task,
  decision_context,
  normalized_gate_formula,
  ordered_token_id_list,
  ordered_threshold_config_key_list,
  ordered_threshold_value_policy_list,
  ordered_threshold_source_list,
  ordered_learned_or_fixed_list,
  ordered_threshold_identity_value_list,
  feature_asof_rule,
  effective_date_rule
)
```

LGBM bucket candidate：

```text
lgbm_bucket_stable_candidate_id = hash(
  model_task,
  model_family,
  predeclared_bucket_id,
  train_threshold_policy,
  score_direction,
  feature_set_version,
  label_version
)
```

Leaf-rule candidate：

```text
leaf_rule_stable_candidate_id = hash(
  model_task,
  leaf_rule_canonicalization_mode,
  canonical_train_extracted_leaf_rule,
  threshold_quantile_bucket_list,
  feature_set_version,
  label_version
)
```

`threshold_source` 枚举必须与 token dictionary 完全一致，只允许：

```text
fixed_config
train_quantile
train_optimized
formula_constant
```

不得使用 `train_learned`、`train_learned_threshold` 或其他未列入枚举的别名。

`ordered_threshold_identity_value_list` 的规则：

```text
if threshold_source = fixed_config:
  identity value = exact config key + exact resolved numeric / categorical value

if threshold_source = train_quantile:
  identity value = train quantile bucket policy, e.g. q80 / q90, not validation quantile

if threshold_source = train_optimized:
  identity value = optimization objective + train-only search grid id + resolved train threshold bucket
  fold_resolved_candidate_id must additionally record exact numeric train_threshold_value

if threshold_source = formula_constant:
  identity value = formula constant literal
```

同名公式如果 threshold source、policy、grid id 或 resolved train threshold bucket 不同，不得聚合成同一个 `gate_stable_candidate_id`。如果确实希望按 policy 聚合而不按 exact numeric value 聚合，必须在 report 中额外输出 `threshold_dispersion_audit`，并证明所有 fold 的 resolved threshold bucket 一致；否则只能按 `fold_resolved_candidate_id` 进入 single-fold diagnostic。

单 fold validation 只输出 diagnostic。P1 eligibility 只能由 `p0_8_p1_promotion_oof_aggregation.csv` 判断。

---

## 2. 背景与动机

P0/P0.5 说明，高波动、强趋势、相对强度、强势日、成交保持、post-20/post-30 continuation 都有信息，但多数更像 winner path node、confirmation、continuation 或 hold tolerance，不是可以直接冻结的 early-entry rule。

P0.6 研究 launch 后 delayed first-entry trigger，包括 hold、pullback、higher-low、volume confirmation 等。P0.6 的主要负向结论是：25 个 entry trigger variant 中 P1 candidate = 0；所有 trigger 都没有证明“等确认以后再买”优于“同一 launch 直接买”。

P0.7AB 已经把 launch pool 分层和 failure filter 分母做干净，工程与审计链路可用。P0.7AB 显示：launch 侧有局部 precision 和 lift，但 P1 candidate = 0；failure 侧有部分 destructive / high-vol / gap-fade 风险信号，但 P1 candidate = 0。

因此 P0.8 的正确任务不是放宽 P1 gate，而是研究：

```text
high-vol × repair quality × money quality × rank persistence × industry/regime × failure path
```

这些非线性交互是否能提供比单公式更稳定的 launch / failure score。

---

## 3. 数据边界与输入

默认输入：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

允许复用 P0.7AB 输出作为 denominator / schema / feature reference：

```text
Explore9/outputs/cache/p0_7_launch_episode_panel.parquet
Explore9/outputs/cache/p0_7_launch_stratum_event_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_opportunity_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_event_panel.parquet
Explore9/outputs/reports/p0_7_feature_dictionary.csv
Explore9/outputs/cache/stock_day_label_panel.parquet
```

禁止作为 feature：

```text
recommended_action_class_after_evaluation
p1_launch_stratification_candidate
p1_failure_filter_candidate
leaderboard_rank
leaderboard_score
eval_action
future outcome metrics
fold validation metrics
observed reference metrics
```

P0.8 必须自行生成 `p0_8_gate_token_dictionary.csv`，不得依赖不存在或历史遗留的 `p0_7_gate_token_dictionary.csv`。

---

## 4. Sample panels and eligibility

### 4.0 Unified event effective date

P0.8 所有 sample、sample-weight、instrument-year、fold audit 和 concentration audit 必须使用统一字段 `event_effective_date`。

```text
for launch task:
  event_effective_date = stratum_effective_date
  event_effective_price_reference = stratum_effective_price_reference

for failure task:
  event_effective_date = failure_decision_effective_date
  event_effective_price_reference = failure_decision_effective_price_reference
```

任何 group key、calendar year、instrument-year、sample-weight cap、purge audit、trainability audit 不得直接引用 task-specific `decision_effective_date`。必须引用：

```text
event_year = calendar_year(event_effective_date)
event_instrument_year = instrument + event_year
```

### 4.1 Launch model sample panel

必须输出：

```text
Explore9/outputs/cache/p0_8_launch_model_sample_panel.parquet
```

单位：

```text
one row per launch_stratum_event_id + model_task + fold_id
```

字段至少包括：

```text
launch_stratum_event_id
launch_episode_id
instrument
date
stratum_date
stratum_signal_date
stratum_effective_date
event_effective_date
stratum_effective_price_reference
event_effective_price_reference
feature_asof_date
fold_id
validation_fold_role
p1_promotion_eligible_fold
launch_family
launch_variant
lifecycle_pool
declared_stratum_role
industry
market_regime
label_horizon_truncated
label_measurement_available
label_measurement_uses_observed_reference
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
launch_model_train_eval_eligible
launch_p1_promotion_eligible
base_sample_weight
final_sample_weight
sample_weight
```

Train/eval eligibility：

```text
launch_model_train_eval_eligible =
  feature_asof_date <= research_end
  and stratum_effective_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_horizon_truncated = false
  and label_measurement_available = true
  and sample_has_required_features = true
```

P1 promotion eligibility：

```text
launch_p1_promotion_eligible =
  launch_model_train_eval_eligible
  and validation_fold_role = p1_promotion_eligible
  and label_measurement_uses_observed_reference = false
  and observed_reference_label_measurement_overlap = false
```

### 4.2 Failure model sample panel

必须输出：

```text
Explore9/outputs/cache/p0_8_failure_model_sample_panel.parquet
```

单位：

```text
one row per launch_stratum_event_id + failure_decision_window + model_task + fold_id
```

默认 windows：

```text
failure_decision_windows: 3d / 5d / 10d
```

默认 timing：

```text
failure_decision_signal_date = trading_day_offset(stratum_date, failure_decision_window)
failure_decision_effective_date = next_trading_day(failure_decision_signal_date)
event_effective_date = failure_decision_effective_date
event_effective_price_reference = failure_decision_effective_price_reference
feature_asof_date = failure_decision_signal_date
```

Failure panel 字段至少必须包含：

```text
launch_stratum_event_id
launch_episode_id
instrument
stratum_date
stratum_effective_date
failure_decision_window
failure_decision_signal_date
failure_decision_effective_date
event_effective_date
failure_decision_effective_price_reference
event_effective_price_reference
feature_asof_date
fold_id
validation_fold_role
model_task
industry
market_regime
label_horizon_truncated
label_measurement_available
label_measurement_uses_observed_reference
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
failure_model_train_eval_eligible
failure_p1_promotion_eligible
base_sample_weight
final_sample_weight
sample_weight
```

Failure model eligibility：

```text
failure_model_train_eval_eligible =
  target_50h120_not_reached_before_decision_effective_date
  and label_horizon_truncated = false
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_measurement_available = true
  and sample_has_required_features = true
```

Failure P1 promotion eligibility：

```text
failure_p1_promotion_eligible =
  failure_model_train_eval_eligible
  and validation_fold_role = p1_promotion_eligible
  and label_measurement_uses_observed_reference = false
  and observed_reference_label_measurement_overlap = false
```

Post-target rows：

```text
if target already reached before failure_decision_effective_date:
  post_target_risk_audit_only = true
  exclude_from_failure_training_loss = true
  exclude_from_failure_validation_metrics = true
  exclude_from_failure_bucket_selection = true
  exclude_from_failure_p1_candidate_selection = true
```

这些 row 不得作为 negative training example，也不得进入 false-reject denominator。

### 4.3 Failure multi-window event-level dedup

窗口可以作为模型输入或 full candidate identity 的一部分，但 P1 / OOF / coverage / false-reject / recall 主指标不得直接使用 full `stable_candidate_id` 做 event-level dedup。原因是 full `stable_candidate_id` 可能包含 `failure_decision_window`，这会导致同一 `launch_stratum_event_id` 的 3d / 5d / 10d 命中被重复计入。

必须新增并输出两个 id：

```text
failure_full_stable_candidate_id = stable_candidate_id
failure_window_group_policy = config.failure_dedup.failure_window_group_policy

failure_event_dedup_candidate_id = hash(
  model_task,
  decision_context,
  candidate_family_or_model_family,
  normalized_failure_formula_windowless,
  ordered_token_id_list_excluding_window_only_tokens,
  ordered_threshold_identity_value_list_excluding_window_only_tokens,
  feature_asof_rule,
  effective_date_rule,
  feature_set_version,
  label_version,
  failure_window_group_policy
)
```

默认：

```text
failure_window_group_policy = merge_3d_5d_10d_for_main_p1_metrics
window_specific_candidate_protocol = false
```

主指标使用：

```text
failure_event_level_dedup_key = failure_event_dedup_candidate_id + launch_stratum_event_id
```

`failure_decision_window` 可以保留在 `failure_full_stable_candidate_id` 中，用于 fold-local candidate、window-specific diagnostic、模型输入或 leaf-rule 解释；但主 OOF P1 指标、coverage、false reject、reject recall、winner coverage loss、matched-delay reject count 和 search-bias candidate count 必须使用 `failure_event_dedup_candidate_id`。

若同一 `failure_event_dedup_candidate_id + launch_stratum_event_id` 被多个 window 命中，主指标只保留：

```text
earliest failure_decision_effective_date
earliest failure_decision_window
source_failure_full_stable_candidate_id_at_earliest_hit
```

后续 window 只能进入 `p0_8_failure_multi_window_dedup_audit.csv`。不得在主 coverage、false reject、reject recall、winner coverage loss、matched-delay reject count 中重复计数同一个 launch event。

如果实现希望把 3d / 5d / 10d window 作为完全独立 P1 candidate，必须另开 `window_specific_candidate_protocol = true`，并在 report 中单独标记为 `window_specific_diagnostic_only`；默认 P0.8 主 P1 gate 不允许用 window-specific full id 绕过 event-level dedup。

---

## 5. Label dictionary and label definitions

### 5.1 Required label dictionary schema

必须输出：

```text
Explore9/outputs/reports/p0_8_label_dictionary.csv
```

每个 label 至少包含：

```text
label_name
model_task
label_type: primary / secondary / audit / eligibility
label_family
label_definition_formula
reference_date_field
reference_price_field
horizon_trading_days
future_price_field_used: high / close / low / mixed
target_return_threshold
drawdown_threshold
comparison_operator
positive_condition
negative_condition
label_start_date_field
label_end_date_field
label_window_includes_effective_date_high_low
eligibility_field
validity_rule
observed_reference_label_measurement_allowed
observed_reference_overlap_handling
label_horizon_truncated_handling
post_target_handling
uses_high
uses_close
uses_low
label_direction
null_value_rule
used_for_training
used_for_validation
used_for_p1_gate
```

未在 label dictionary 中定义的 label，不得进入训练、验证、ranking 或 P1 gate。

### 5.2 Effective-date label window convention

P0.8 默认 close-derived signal 的执行规则是 next trading day open：

```text
stratum_effective_date = next_trading_day(stratum_signal_date)
stratum_effective_price_reference = open on stratum_effective_date
failure_decision_effective_date = next_trading_day(failure_decision_signal_date)
failure_decision_effective_price_reference = open on failure_decision_effective_date
```

如果 reference price 是 next-open，则 label window 必须从 effective date 当天开始，而不是从 effective date 后一天开始：

```text
label_window_start_date = effective_date
label_window_end_date_N = trading_day_offset(effective_date, N - 1)
label_window_includes_effective_date_high_low = true
```

因此 `N=120` 表示包括 effective date 当天在内的 120 个交易日。Daily high / low / close 是 future outcome，不是 T 日 feature。

### 5.3 Launch labels

令：

```text
E = stratum_effective_date
P_E = stratum_effective_price_reference
H_N(E) = max(high over E ... trading_day_offset(E, N-1))
C_N(E) = max(close over E ... trading_day_offset(E, N-1))
L_N(E) = min(low over E ... trading_day_offset(E, N-1))
```

Launch labels：

```text
launch_winner_50h120 = H_120(E) / P_E - 1 >= 0.50
launch_winner_50c120 = C_120(E) / P_E - 1 >= 0.50
launch_winner_100h240 = H_240(E) / P_E - 1 >= 1.00
launch_future_20pct_high_60d = H_60(E) / P_E - 1 >= 0.20
launch_future_max_drawdown_60d = L_60(E) / P_E - 1

launch_false_positive_primary =
  not launch_winner_50h120
  and launch_future_max_drawdown_60d <= -0.12

first_20pct_gain_date = first trading day d in [E, trading_day_offset(E, 59)] where
  high[d] / P_E - 1 >= 0.20

if first_20pct_gain_date exists:
  first_20pct_gain_missing = false
  launch_drawdown_before_20pct_gain_end_date = first_20pct_gain_date
else:
  first_20pct_gain_missing = true
  launch_drawdown_before_20pct_gain_end_date = trading_day_offset(E, 59)

launch_drawdown_before_20pct_gain =
  min(low over E ... launch_drawdown_before_20pct_gain_end_date) / P_E - 1

launch_drawdown_before_20pct_gain_le_10pct =
  launch_drawdown_before_20pct_gain >= -0.10
```

Drawdown 用负数表示；`le_10pct` 指回撤幅度不超过 10%，公式必须是 `>= -0.10`。如果 60 个交易日内未达到 20% high，`first_20pct_gain_missing = true`，drawdown 计算窗口固定到 `trading_day_offset(E, 59)`，不得输出 null 或改用其他窗口。

### 5.4 Failure labels: decision reference and launch reference

Failure model 必须同时保留两套 false-reject 口径。

Decision reference 用于回答：

```text
如果在 reject decision effective date 重新评估，未来风险/收益是否不值得继续暴露？
```

Launch reference 用于回答：

```text
这个 reject 是否错杀了原 launch opportunity 中本来会成为 winner 的样本？
```

令：

```text
D = failure_decision_effective_date
P_D = failure_decision_effective_price_reference
E = stratum_effective_date
P_E = stratum_effective_price_reference
```

Pending target 必须按 label 分开，不得把 50% 与 100% 口径混成一个字段：

```text
pre_decision_window_for_launch_reference = [E, previous_trading_day(D)]

launch_target_50h120_reached_before_decision =
  exists trading day d in pre_decision_window_for_launch_reference where high[d] / P_E - 1 >= 0.50

launch_target_100h240_reached_before_decision =
  exists trading day d in pre_decision_window_for_launch_reference where high[d] / P_E - 1 >= 1.00

target_50h120_not_reached_before_decision_effective_date =
  not launch_target_50h120_reached_before_decision

target_100h240_not_reached_before_decision_effective_date =
  not launch_target_100h240_reached_before_decision
```

Failure primary target 固定为 `50h120`。`100h240` 只用于 big-winner false-reject audit / secondary veto，不得替代 primary denominator。

Decision-reference labels：

```text
future_50pct_high_120d_from_decision_reference =
  max(high over D ... trading_day_offset(D, 119)) / P_D - 1 >= 0.50

future_100pct_high_240d_from_decision_reference =
  max(high over D ... trading_day_offset(D, 239)) / P_D - 1 >= 1.00

future_max_drawdown_60d_from_decision_reference =
  min(low over D ... trading_day_offset(D, 59)) / P_D - 1

failure_reject_positive_primary =
  target_50h120_not_reached_before_decision_effective_date
  and not future_50pct_high_120d_from_decision_reference
  and future_max_drawdown_60d_from_decision_reference <= -0.12

failure_false_reject_winner_from_decision_50h120 =
  target_50h120_not_reached_before_decision_effective_date
  and future_50pct_high_120d_from_decision_reference

failure_false_reject_big_winner_from_decision_100h240 =
  target_100h240_not_reached_before_decision_effective_date
  and future_100pct_high_240d_from_decision_reference
```

Launch-reference coverage labels：

```text
launch_target_reached_after_decision_within_original_horizon_50h120 =
  target_50h120_not_reached_before_decision_effective_date
  and exists trading day d in [D, trading_day_offset(E, 119)] where high[d] / P_E - 1 >= 0.50

launch_target_reached_after_decision_within_original_horizon_100h240 =
  target_100h240_not_reached_before_decision_effective_date
  and exists trading day d in [D, trading_day_offset(E, 239)] where high[d] / P_E - 1 >= 1.00

failure_false_reject_winner_from_launch_50h120 =
  launch_target_reached_after_decision_within_original_horizon_50h120

failure_false_reject_big_winner_from_launch_100h240 =
  launch_target_reached_after_decision_within_original_horizon_100h240
```

Interpretation：

```text
winner coverage loss / missed launch winner / false reject coverage metrics 必须使用 from_launch_reference。
residual reward-risk / reject precision / decision-date opportunity metrics 使用 from_decision_reference。
from_decision_reference false reject 只能作为 secondary_veto_gate / diagnostic downgrade，不得替代 from_launch_reference 的 P1 winner coverage gate。若二者冲突，P1 主解释以 from_launch_reference 为准；decision-reference 风险只决定是否触发 secondary veto 或降级说明。
```

---

## 6. Sample weights

主榜默认：

```text
sample_weight_mode = episode_balanced_with_group_cap
base_sample_weight = 1 / number_of_model_rows_in_same_launch_episode_and_task
final_sample_weight = base_sample_weight after group aggregate cap and split-level renormalization
sample_weight = final_sample_weight  # backward-compatible alias only
```

Instrument-year cap 必须是 group-level aggregate cap，不得写成单行 `min(row_weight, cap)`。

```text
instrument_year_group_key = fold_id + split + model_task + instrument + calendar_year(event_effective_date)
base_group_weight_sum = sum(base_sample_weight over instrument_year_group_key)
max_group_weight_share = config.sample_weight.max_instrument_year_weight_share

Iteratively scale groups where group_weight_sum / total_weight_sum > max_group_weight_share
until no group breaches the cap or max iterations reached.

Then renormalize final weights so sum(final_sample_weight) = number of rows in the split.
```

必须输出：

```text
Explore9/outputs/reports/p0_8_sample_weight_audit.csv
Explore9/outputs/reports/p0_8_sample_weight_group_cap_audit.csv
```

字段至少包括：

```text
fold_id
model_task
split
instrument_year
event_effective_year
raw_group_weight_sum
raw_group_weight_share
final_group_weight_sum
final_group_weight_share
top_instrument_year_weight_share
instrument_year_weight_hhi
group_cap_applied
max_instrument_year_weight_share
row_count
positive_count
```

样本面板、LGBM prediction panel、baseline audit 与 concentration audit 必须同时保留：

```text
base_sample_weight
final_sample_weight
sample_weight = final_sample_weight
```

`sample_weight` 只能作为兼容别名，不得与 `final_sample_weight` 不一致。`equal_row` 只能作为 sensitivity audit。P1 gate 必须同时检查 OOF candidate 的 instrument-year 权重集中度：

```text
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
```

---

## 7. Feature dictionary and leakage discipline

必须输出：

```text
Explore9/outputs/reports/p0_8_feature_dictionary.csv
Explore9/outputs/reports/p0_8_formula_token_coverage_audit.csv
Explore9/outputs/reports/p0_8_feature_asof_leakage_audit.csv
Explore9/outputs/reports/p0_8_gate_token_dictionary.csv
```

任何 LGBM feature、gate token、formula token 必须进入 dictionary 或属于允许的 operator / literal / function。

`p0_8_gate_token_dictionary.csv` 必须至少包含：

```text
token_id
token_name
token_family
source_family
source_variant
model_task
decision_context
feature_asof_rule
formula_text_raw
formula_text_resolved
threshold_config_key
threshold_value_policy
threshold_source: fixed_config / train_quantile / train_optimized / formula_constant
learned_or_fixed: learned / fixed
learned_fold_id
train_threshold_value
train_threshold_quantile
train_threshold_value_identity
train_threshold_value_bucket_hash
threshold_canonicalization_rule
validation_threshold_used = false
allowed_for_gate_search
allowed_for_lgbm_feature
allowed_in_launch_task
allowed_in_failure_task
observed_reference_used_for_threshold = false
leakage_audit_pass
```

其中 `rank_evaporation_2d / rank_evaporation_3d / rank_evaporation_5d` 等新 token 必须显式记录 `formula_text_resolved`、`threshold_config_key`、`threshold_value_policy`、`learned_or_fixed`、`threshold_source`、`train_threshold_value_identity`、`train_threshold_value_bucket_hash`。禁止在代码中隐式生成同名 token，也禁止用 outer validation 学阈值。任何 `validation_threshold_used = true` 的 token 不得进入 train search、validation metrics 或 P1 promotion。

禁止 feature：

```text
future labels
entry_success_primary
failure_primary
recommended_action_class_after_evaluation
eval_action
p1_candidate
leaderboard_rank
leaderboard_score
validation_precision
validation_lift
observed_reference_result
post_target_signal_flag as feature
label_horizon_truncated as feature
observed_reference_overlap as feature
```

允许 feature family：

```text
price_path_features
volatility_features
money_quality_features
relative_strength_features
rank_persistence_features
rank_deterioration_features
repair_quality_features
prelaunch_path_features
industry_context_features
market_regime_features
lifecycle_context_features
launch_formula_flags
failure_opportunity_context_flags
execution_feasibility_features
```

Industry / regime feature 可以用，但必须经过 industry/regime ablation 和 concentration gate。

---

## 8. P0.8A Gate Combination Discovery

### 8.1 Seed gate combinations

优先测试：

```text
repair_higher_low_reclaim AND destructive_high_vol_3d
repair_higher_low_reclaim AND destructive_high_vol_5d
money_price_upper_keep AND destructive_high_vol_3d
money_price_upper_keep AND destructive_high_vol_5d
money_expansion_no_distribution AND destructive_high_vol_3d
money_expansion_no_distribution AND destructive_high_vol_5d
first_near_limit_upper_close AND rank_evaporation_2d
first_near_limit_upper_close AND rank_evaporation_3d
first_near_limit_upper_close AND rank_evaporation_5d
high_vol_quality_permit AND industry_breadth_coherence
high_vol_quality_permit AND market_regime_risk_on
high_vol_destructive_warning AND market_regime_risk_off
gap_fade_break_prior_close_5d AND high_vol_destructive_warning
gap_fade_break_prior_close_5d AND money_distribution_5d
```

### 8.2 Beam search contract

Beam search 只能在 train fold 内执行。

```text
beam_width = 50
max_candidates_per_depth = 200
max_final_gate_candidates_per_fold = 300
min_train_event_count = 100
min_train_distinct_instrument_year = 25
min_train_distinct_years = 3
max_tokens_per_gate = 4
max_industry_or_regime_tokens_per_gate = 1
```

禁止在 validation fold 上选择 gate。Validation 只评估 train-selected / predeclared gate。

### 8.3 Gate outputs

```text
Explore9/outputs/reports/p0_8_gate_candidate_train_search.csv
Explore9/outputs/reports/p0_8_gate_candidate_validation_metrics.csv
Explore9/outputs/reports/p0_8_gate_candidate_oof_aggregation.csv
Explore9/outputs/reports/p0_8_gate_complexity_audit.csv
```

---

## 9. P0.8B LGBM Nonlinear Scoring Discovery

### 9.1 Tasks

至少训练两个模型：

```text
launch_winner_score_lgbm
failure_reject_score_lgbm
```

可选 shadow：

```text
small_mlp_shadow_benchmark = optional, not main line
```

### 9.2 Early stopping anti-leakage

Outer validation fold 不得用于 early stopping、best iteration、hyperparameter search、feature selection、bucket selection 或 leaf-rule selection。

默认允许 early stopping，但只能使用 train fold 内部切出的 inner validation：

```text
early_stopping_uses_outer_validation_fold = false
early_stopping_uses_inner_train_split_only = true
inner_validation_mode = latest fully eligible train year after purge
inner_validation_fallback_to_outer_allowed = false
```

如果找不到满足 trainability gate 的 inner validation year，或 latest eligible train year 在 purge 后样本不足，则：

```text
lgbm_training_enabled_for_fold = false
fold_excluded_from_lgbm_oof_aggregation = true
fold_status = disabled_due_to_no_valid_inner_validation
```

禁止 fallback 到 outer validation fold、observed-reference label-measurement rows 或随机切分来完成 early stopping。

如果实现无法保证，必须关闭 early stopping：

```text
early_stopping_rounds = null
n_estimators_fixed = true
```

### 9.3 Trainability / sample sufficiency gate

每个 LGBM task / fold 在训练前必须通过 trainability gate。必须输出：

```text
Explore9/outputs/reports/p0_8_lgbm_fold_trainability_audit.csv
```

字段至少包括：

```text
fold_id
model_task
train_event_count_after_purge
train_positive_count_after_purge
train_negative_count_after_purge
train_distinct_instrument_year
inner_validation_event_count
inner_validation_positive_count
outer_validation_event_count_eligible
outer_validation_positive_count_eligible
outer_validation_distinct_instrument_year
purge_rate
label_horizon_truncated_rate
observed_reference_label_measurement_overlap_rate
trainability_status
trainability_rejection_reason
```

默认 gate：

```text
train_event_count_after_purge >= thresholds.min_lgbm_train_event_count
train_positive_count_after_purge >= thresholds.min_lgbm_train_positive_count
train_negative_count_after_purge >= thresholds.min_lgbm_train_negative_count
train_distinct_instrument_year >= thresholds.min_lgbm_train_distinct_instrument_year
inner_validation_event_count >= thresholds.min_lgbm_inner_validation_event_count
inner_validation_positive_count >= thresholds.min_lgbm_inner_validation_positive_count
outer_validation_event_count_eligible >= thresholds.min_lgbm_outer_validation_event_count
outer_validation_positive_count_eligible >= thresholds.min_lgbm_outer_validation_positive_count
outer_validation_distinct_instrument_year >= thresholds.min_lgbm_validation_distinct_instrument_year
```

不满足的 fold：

```text
lgbm_training_enabled_for_fold = false
fold_excluded_from_lgbm_oof_aggregation = true
fold_status = disabled_due_to_insufficient_sample
```

不得用降采样、重复采样、SMOTE 或 class-weight trick 强行让薄样本 fold 进入主验证。Class weight 只能作为 sensitivity audit。

### 9.4 Score bucket predeclaration

Validation fold 不得用于选择最好看的 score bucket。

Launch 默认 bucket：

```text
launch_top_10pct_by_train_threshold
launch_top_5pct_by_train_threshold
launch_top_2pct_by_train_threshold
```

Failure 默认 bucket：

```text
failure_top_risk_10pct_by_train_threshold
failure_top_risk_5pct_by_train_threshold
failure_top_risk_2pct_by_train_threshold
```

`predeclared_bucket_id` 是 stable candidate identity 的一部分。

### 9.5 Leaf-rule extraction

Leaf rule / path 只能使用 train fold 数据抽取和排序，然后在 validation fold 上评估一次。禁止使用 validation performance 选择 top leaves / paths。

Leaf-rule canonicalization：

```text
leaf_rule_canonicalization_mode = exact_feature_quantile_bucketed
numeric_threshold_quantile_bins = q05/q10/q20/q30/q40/q50/q60/q70/q80/q90/q95
threshold_quantile_tolerance = 0.05
allow_feature_family_only_merge = false
validation_informed_canonicalization_allowed = false
```

如果 leaf rule 不能形成 canonical match across folds，只能作为 single-fold diagnostic，不得进入 stable candidate OOF aggregation。

### 9.6 LGBM outputs

```text
Explore9/outputs/cache/p0_8_lgbm_launch_predictions_walkforward.parquet
Explore9/outputs/cache/p0_8_lgbm_failure_predictions_walkforward.parquet
Explore9/outputs/reports/p0_8_lgbm_fold_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_score_bucket_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_instrument_year_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_industry_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_feature_importance.csv
Explore9/outputs/reports/p0_8_lgbm_leaf_rule_candidates.csv
Explore9/outputs/reports/p0_8_lgbm_leaf_rule_canonicalization_audit.csv
Explore9/outputs/reports/p0_8_lgbm_model_card.csv
Explore9/outputs/reports/p0_8_lgbm_early_stopping_audit.csv
Explore9/outputs/reports/p0_8_lgbm_score_bucket_selection_audit.csv
```

---

## 10. Baselines and search-bias audit

### 10.1 Launch baselines

Launch gate / model 至少比较：

```text
all_launch_episode_baseline
same_launch_family_baseline
same_lifecycle_pool_baseline
same_market_regime_baseline
same_industry_regime_baseline
industry_only_baseline
P0.7AB full-window best single formula baseline audit-only
P0.7AB fold-local train-selected single formula baseline
P0.8 train-best gate baseline
null / permutation search baseline
```

`P0.7AB best single formula baseline` 如果来自 P0.7AB 全 research-window leaderboard，只能作为 audit baseline，不得参与 P1 gate。若要参与 P1 gate 比较，必须是 fold-local train-selected P0.7-style baseline：每个 outer fold 只能在 train years 内选择 best single formula，然后冻结该 baseline 并在同一 outer validation fold 上评估。

必须在 baseline audit 中记录：

```text
baseline_source_scope: full_window_audit_only / fold_local_train_selected
baseline_selected_on_validation = false
baseline_used_for_p1_gate = true / false
```

LGBM score bucket 通常会跨多个 launch family / variant，因此 same-family baseline 必须定义为 candidate-composition-weighted baseline，而不是单一 family baseline。

```text
For candidate C with event-level rows r:
  family_key_r = launch_family or launch_family + launch_variant, per config
  weight_r = final sample_weight or event-level unit weight, per metric

candidate_weighted_same_family_winner_rate =
  weighted_average(same_family_baseline_winner_rate[family_key_r], weights = weight_r over r in C)

candidate_weighted_same_family_false_positive_rate =
  weighted_average(same_family_baseline_false_positive_rate[family_key_r], weights = weight_r over r in C)

candidate_weighted_same_family_median_drawdown_60d =
  weighted median / weighted quantile of same-family baseline drawdown references using candidate composition weights

oof_validation_lift_vs_candidate_weighted_same_family_baseline =
  candidate_oof_winner_rate / candidate_weighted_same_family_winner_rate
```

Gate candidate 如果本身是 single-family，则 weighted baseline 退化为该 family baseline。Mixed-family LGBM bucket 不得使用全局 baseline 冒充 same-family baseline。

所有候选必须输出两套 baseline missing 口径：

```text
candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share
```

`candidate_weighted_baseline_missing_rate` 只允许作为兼容别名，且必须等于 `candidate_baseline_missing_weight_share`，不得再用 row-count 公式填充 weighted 字段。

missing baseline row 不得静默丢弃。Launch / failure P1 gate 必须要求：

```text
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
```

必须输出：

```text
Explore9/outputs/reports/p0_8_candidate_baseline_composition_audit.csv
Explore9/outputs/reports/p0_8_candidate_baseline_missing_audit.csv
```

Baseline missing rate 必须显式计算，不得静默丢弃缺 baseline 的 row：

```text
candidate_baseline_missing_row_rate =
  rows_with_missing_required_family_or_scope_baseline / candidate_rows_before_baseline_join_filtering

candidate_baseline_missing_weight_share =
  sum(final_sample_weight for rows_with_missing_required_family_or_scope_baseline)
  / sum(final_sample_weight for all candidate_rows_before_baseline_join_filtering)

candidate_weighted_baseline_missing_rate = candidate_baseline_missing_weight_share  # backward-compatible alias only

candidate rows with missing baseline must remain in the audit denominator;
P1 gate must fail if either row-rate or weight-share exceeds its threshold.
```

### 10.2 Failure baselines

Failure score / gate 至少比较：

```text
same_opportunity_scope_unfiltered_baseline
same_launch_family_failure_baseline
same_lifecycle_failure_baseline
matched_delay_exact_reject_count_baseline
industry_only_baseline
P0.7AB full-window best single filter baseline audit-only
P0.7AB fold-local train-selected single filter baseline
P0.8 train-best gate baseline
null / permutation search baseline
```

`P0.7AB best single filter baseline` 如果来自 P0.7AB 全 research-window leaderboard，只能作为 audit baseline，不得参与 P1 gate。若要参与 P1 gate 比较，必须是 fold-local train-selected P0.7-style filter baseline：每个 outer fold 只能在 train years 内选择 best single filter，然后冻结该 baseline 并在同一 outer validation fold 上评估。

Matched-delay 对 model score bucket 的规则：

```text
pseudo_reject_count_target = actual_event_level_dedup_rejected_count_in_score_bucket
pseudo_delay_distribution = actual_score_bucket_decision_delay_distribution
pseudo_sample_scope = same validation fold + same opportunity scope
n_repeats = config.matched_delay.n_repeats
random_seed = config.matched_delay.random_seed
```

禁止：

```text
every_U_gets_pseudo_filter_date
pseudo_count_independent_of_score_bucket_reject_count
pseudo_dates_sampled_from calendar days
using validation outcome to choose pseudo reject rows
```

### 10.3 Search-bias null generation

P0.8 的 primary search-bias null 必须使用 train-permutation full-search protocol，不得和 validation permutation 混用。

Primary null：

```text
primary_null_mode = train_label_permutation_search_then_real_validation_eval
```

Gate-search null：

```text
1. 在 train fold 内按 year + industry + episode / instrument-year 分组 permutation label。
2. 在 permuted train 上用与真实 gate 搜索完全相同的 search budget、beam width、filters、complexity penalty 搜索候选。
3. 用 permuted train 选出的 null gate candidate，冻结 token / threshold。
4. 在真实 outer validation labels 上评估该 null candidate。
```

LGBM-bucket null：

```text
1. 在 train fold 内 permutation label，保留相同 group structure。
2. 用 permuted train labels 重新训练完整 LGBM，包括 inner validation / early stopping / sample weights / trainability gate。
3. 使用同一套 predeclared bucket policy，并在 permuted train 上确定 bucket thresholds。
4. 在真实 outer validation labels 上评估 null LGBM buckets。
5. 对 leaf rule，必须从 permuted train model 中抽取 train-selected leaf rules，再应用到真实 outer validation。
```

共同输出：

```text
p0_8_search_bias_audit.csv
p0_8_null_permutation_baseline.csv
p0_8_lgbm_null_bucket_baseline.csv
p0_8_lgbm_null_leaf_rule_baseline.csv
```

每个 candidate type 的 p-value 必须分开计算，禁止将 gate-combination null、LGBM bucket null、LGBM leaf-rule null 混成同一个 p-value。

P1 candidate 必须满足：

```text
search_bias_pass = true
candidate_lift_exceeds_null_p95 = true
selection_bias_warning = false
empirical_p_value <= thresholds.max_search_bias_empirical_p
fdr_q_value <= thresholds.max_search_bias_fdr_q
```

---

## 11. Industry / regime anti-sector-model audit

P0.8 允许 industry / regime 作为 T 日可观察 context，但不得让 P1 candidate 退化为隐性行业模型。所有 gate、LGBM bucket、leaf rule 的 OOF 聚合必须输出：

```text
industry_hhi
top1_industry_contribution
top3_industry_contribution
industry_count_with_min_events
regime_hhi
top1_regime_contribution
with_industry_regime_features_metric
without_industry_regime_features_metric
industry_regime_ablation_lift_ratio
lift_vs_industry_only_baseline
without_industry_regime_ablation_lift
industry_regime_dependency_warning
```

默认 P1 gate：

```text
industry_hhi <= thresholds.max_industry_hhi
top1_industry_contribution <= thresholds.max_top1_industry_contribution
top3_industry_contribution <= thresholds.max_top3_industry_contribution
industry_count_with_min_events >= thresholds.min_industry_count_with_min_events
regime_hhi <= thresholds.max_regime_hhi
top1_regime_contribution <= thresholds.max_top1_regime_contribution
industry_regime_ablation_lift_ratio >= thresholds.min_industry_regime_ablation_lift_ratio
lift_vs_industry_only_baseline >= thresholds.min_lift_vs_industry_only_baseline
without_industry_regime_ablation_lift >= thresholds.min_without_industry_regime_ablation_lift
```

`regime_hhi` 与 `top1_regime_contribution` 默认是 hard gate，不只是 audit。若某候选只在单一 market regime 成立，必须降级为 `regime_specialist_diagnostic_only`，不得进入主 P1 refine gate，除非另开预声明 regime-specific research protocol。

如果候选只在单一行业成立，只能标记：

```text
industry_specialist_diagnostic_only
not_p1_candidate_due_to_industry_regime_dependence
```

不得进入主 P1 refine gate，除非另开预声明 sector-specific research protocol。

---

## 12. Metrics and P1 refine gates

### 12.1 Positive validation fold definition

`positive_validation_fold_count` 必须在 `validation_fold_role = p1_promotion_eligible` 的 fold 上计算。`fold_2024` audit-only fold 不得计入。

Launch positive fold：

```text
launch_positive_validation_fold =
  fold_event_count >= thresholds.min_fold_launch_event_count
  and fold_positive_winner_count >= thresholds.min_fold_launch_winner_count
  and fold_lift_vs_all_launch_baseline >= thresholds.min_fold_launch_positive_lift_vs_all
  and fold_lift_vs_candidate_weighted_same_family_baseline >= thresholds.min_fold_launch_positive_lift_vs_family
  and fold_winner_episode_coverage >= thresholds.min_fold_winner_episode_coverage
  and fold_false_positive_rate <= fold_candidate_weighted_same_family_false_positive_rate * thresholds.max_fold_false_positive_ratio_vs_family
  and fold_median_drawdown_60d >= fold_candidate_weighted_same_family_median_drawdown_60d - thresholds.max_fold_drawdown_degradation
```

Failure positive fold：

```text
failure_positive_validation_fold =
  fold_event_level_dedup_reject_count >= thresholds.min_fold_failure_reject_count
  and fold_failure_positive_count >= thresholds.min_fold_failure_positive_count
  and fold_nonwinner_precision_lift >= thresholds.min_fold_nonwinner_precision_lift
  and fold_failure_precision_lift >= thresholds.min_fold_failure_precision_lift
  and fold_winner_false_reject_from_launch_rate <= thresholds.max_fold_winner_false_reject_rate
  and fold_pending_winner_coverage_loss_from_launch <= thresholds.max_fold_pending_winner_coverage_loss
  and fold_median_drawdown_avoided_vs_matched_delay >= thresholds.min_fold_drawdown_avoided_vs_delay
```

```text
positive_validation_fold_count = count(fold where *_positive_validation_fold = true among p1_promotion_eligible folds only)
```

### 12.2 Baseline completeness and instrument-year concentration

Baseline missing 必须同时按 row-count 与 sample-weight 计算：

```text
candidate_baseline_missing_row_rate =
  rows_without_candidate_scope_weighted_baseline / candidate_oof_rows_before_baseline_join_filtering

candidate_baseline_missing_weight_share =
  sum(final_sample_weight for rows_without_candidate_scope_weighted_baseline)
  / sum(final_sample_weight for candidate_oof_rows_before_baseline_join_filtering)

candidate_weighted_baseline_missing_rate = candidate_baseline_missing_weight_share  # backward-compatible alias only
```

缺失 baseline 行不得静默丢弃，也不得从 denominator 删除。Launch / failure P1 gate 都必须要求：

```text
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
```

Instrument-year concentration 必须按最终 OOF event weight 或 event unit weight 输出：

```text
oof_top_instrument_year_weight_share = max(weight_share by event_instrument_year)
oof_instrument_year_weight_hhi = sum(weight_share_by_event_instrument_year^2)
```

Launch / failure P1 gate 都必须要求：

```text
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
```

### 12.3 Launch P1 refine gate

Launch gate / model score bucket 可进入 P1 refine，当且仅当 P1-promotion-eligible OOF aggregate 满足：

```text
p1_promotion_eligible_oof_validation_fold_count >= thresholds.min_validation_folds
p1_promotion_eligible_oof_validation_distinct_years >= thresholds.min_validation_years
positive_validation_fold_count >= thresholds.min_positive_validation_folds
p1_promotion_eligible_oof_event_count >= thresholds.min_launch_gate_event_count
p1_promotion_eligible_oof_distinct_instrument_year >= thresholds.min_distinct_instrument_year
p1_promotion_eligible_oof_lift_vs_all_launch_baseline >= thresholds.min_launch_lift_vs_all
p1_promotion_eligible_oof_lift_vs_candidate_weighted_same_family_baseline >= thresholds.min_launch_lift_vs_same_family
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
p1_promotion_eligible_oof_instrument_year_lift >= thresholds.min_instrument_year_lift
p1_promotion_eligible_oof_winner_episode_coverage >= thresholds.min_winner_episode_coverage
p1_promotion_eligible_oof_false_positive_rate <= candidate_weighted_same_family_false_positive_rate * thresholds.max_false_positive_ratio_vs_family
p1_promotion_eligible_oof_median_drawdown_60d >= candidate_weighted_same_family_median_drawdown_60d - thresholds.max_drawdown_degradation
oof_top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
oof_top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
oof_top1_industry_contribution <= thresholds.max_top1_industry_contribution
oof_top3_industry_contribution <= thresholds.max_top3_industry_contribution
oof_industry_hhi <= thresholds.max_industry_hhi
oof_regime_hhi <= thresholds.max_regime_hhi
oof_top1_regime_contribution <= thresholds.max_top1_regime_contribution
industry_count_with_min_events >= thresholds.min_industry_count_with_min_events
industry_regime_ablation_lift_ratio >= thresholds.min_industry_regime_ablation_lift_ratio
lift_vs_industry_only_baseline >= thresholds.min_lift_vs_industry_only_baseline
without_industry_regime_ablation_lift >= thresholds.min_without_industry_regime_ablation_lift
search_bias_pass = true
fold_2024_used_for_p1_promotion = false
```

### 12.4 Failure P1 refine gate

Failure gate / model score bucket 可进入 P1 refine，当且仅当 P1-promotion-eligible OOF aggregate 满足：

```text
p1_promotion_eligible_oof_validation_fold_count >= thresholds.min_validation_folds
p1_promotion_eligible_oof_validation_distinct_years >= thresholds.min_validation_years
positive_validation_fold_count >= thresholds.min_positive_validation_folds
p1_promotion_eligible_oof_event_level_dedup_reject_count >= thresholds.min_failure_gate_event_count
p1_promotion_eligible_oof_nonwinner_precision_lift >= thresholds.min_nonwinner_precision_lift
p1_promotion_eligible_oof_failure_precision_lift >= thresholds.min_failure_precision_lift
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
p1_promotion_eligible_oof_winner_false_reject_from_launch_rate <= thresholds.max_winner_false_reject_rate
p1_promotion_eligible_oof_big_winner_false_reject_from_launch_rate <= thresholds.max_big_winner_false_reject_rate
secondary_decision_reference_veto_pass = true
p1_promotion_eligible_oof_pending_winner_coverage_loss_from_launch <= thresholds.max_pending_winner_coverage_loss
p1_promotion_eligible_oof_total_winner_coverage_loss_from_launch <= thresholds.max_total_winner_coverage_loss
p1_promotion_eligible_oof_median_drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_delay
p1_promotion_eligible_oof_before_12pct_drawdown_rate >= thresholds.min_before_12pct_drawdown_rate
p1_promotion_eligible_oof_instrument_year_filter_effect_lift >= thresholds.min_instrument_year_filter_effect_lift
oof_top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
oof_top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
oof_top1_industry_contribution <= thresholds.max_top1_industry_contribution
oof_top3_industry_contribution <= thresholds.max_top3_industry_contribution
oof_industry_hhi <= thresholds.max_industry_hhi
oof_regime_hhi <= thresholds.max_regime_hhi
oof_top1_regime_contribution <= thresholds.max_top1_regime_contribution
industry_count_with_min_events >= thresholds.min_industry_count_with_min_events
industry_regime_ablation_lift_ratio >= thresholds.min_industry_regime_ablation_lift_ratio
lift_vs_industry_only_baseline >= thresholds.min_lift_vs_industry_only_baseline
without_industry_regime_ablation_lift >= thresholds.min_without_industry_regime_ablation_lift
search_bias_pass = true
fold_2024_used_for_p1_promotion = false
```

Secondary decision-reference veto：

```text
secondary_decision_reference_veto_pass =
  p1_promotion_eligible_oof_winner_false_reject_from_decision_rate <= thresholds.max_secondary_decision_false_reject_rate
  and p1_promotion_eligible_oof_big_winner_false_reject_from_decision_rate <= thresholds.max_secondary_decision_big_winner_false_reject_rate
```

该 veto 的语义是：候选虽然不能用 decision-reference 解释 winner coverage loss，但如果 decision-reference 也显示严重错杀后续 winner，则不得进入 P1 refine，只能输出 `diagnostic_only_due_to_secondary_decision_reference_veto`。

### 12.5 Failure interpretations

```text
if LGBM meets AUC / logloss but fails coverage / false reject:
  model_predictive_but_not_actionable = true

if LGBM meets pooled metrics but fails instrument-year:
  diagnostic_only_due_to_instrument_year_failure

if model passes only with industry / regime features:
  not_p1_candidate_due_to_industry_regime_dependence
```

---

## 13. Required outputs

本节是 P0.8 artifact 的唯一 required artifact authority。凡在前文声明为“必须输出”的文件，必须在本节列出；未列入本节的文件只能视为 optional / debug artifact，不能被 report generator 或 P1 gate 硬依赖。

Full row-level panels must be parquet cache only; full CSV panels are not generated by default.

Cache：

```text
Explore9/outputs/cache/p0_8_launch_model_sample_panel.parquet
Explore9/outputs/cache/p0_8_failure_model_sample_panel.parquet
Explore9/outputs/cache/p0_8_failure_multi_window_event_level_dedup_panel.parquet
Explore9/outputs/cache/p0_8_lgbm_launch_predictions_walkforward.parquet
Explore9/outputs/cache/p0_8_lgbm_failure_predictions_walkforward.parquet
```

Required report CSV / JSON / Markdown：

```text
Explore9/outputs/reports/p0_8_run_manifest.json
Explore9/outputs/reports/p0_8_label_dictionary.csv
Explore9/outputs/reports/p0_8_feature_dictionary.csv
Explore9/outputs/reports/p0_8_gate_token_dictionary.csv
Explore9/outputs/reports/p0_8_formula_token_coverage_audit.csv
Explore9/outputs/reports/p0_8_feature_asof_leakage_audit.csv
Explore9/outputs/reports/p0_8_observed_reference_label_measurement_audit.csv
Explore9/outputs/reports/p0_8_fold_role_audit.csv
Explore9/outputs/reports/p0_8_sample_weight_audit.csv
Explore9/outputs/reports/p0_8_sample_weight_group_cap_audit.csv
Explore9/outputs/reports/p0_8_failure_multi_window_dedup_audit.csv
Explore9/outputs/reports/p0_8_candidate_baseline_composition_audit.csv
Explore9/outputs/reports/p0_8_candidate_baseline_missing_audit.csv
Explore9/outputs/reports/p0_8_gate_candidate_train_search.csv
Explore9/outputs/reports/p0_8_gate_candidate_validation_metrics.csv
Explore9/outputs/reports/p0_8_gate_candidate_oof_aggregation.csv
Explore9/outputs/reports/p0_8_gate_complexity_audit.csv
Explore9/outputs/reports/p0_8_lgbm_fold_trainability_audit.csv
Explore9/outputs/reports/p0_8_lgbm_fold_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_score_bucket_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_instrument_year_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_industry_metrics.csv
Explore9/outputs/reports/p0_8_lgbm_feature_importance.csv
Explore9/outputs/reports/p0_8_lgbm_leaf_rule_candidates.csv
Explore9/outputs/reports/p0_8_lgbm_leaf_rule_canonicalization_audit.csv
Explore9/outputs/reports/p0_8_lgbm_model_card.csv
Explore9/outputs/reports/p0_8_lgbm_early_stopping_audit.csv
Explore9/outputs/reports/p0_8_lgbm_score_bucket_selection_audit.csv
Explore9/outputs/reports/p0_8_threshold_dispersion_audit.csv
Explore9/outputs/reports/p0_8_stable_candidate_oof_aggregation.csv
Explore9/outputs/reports/p0_8_p1_promotion_oof_aggregation.csv
Explore9/outputs/reports/p0_8_oof_robustness_all_folds.csv
Explore9/outputs/reports/p0_8_search_bias_audit.csv
Explore9/outputs/reports/p0_8_null_permutation_baseline.csv
Explore9/outputs/reports/p0_8_lgbm_null_bucket_baseline.csv
Explore9/outputs/reports/p0_8_lgbm_null_leaf_rule_baseline.csv
Explore9/outputs/reports/p0_8_fold_local_p0_7_baseline_audit.csv
Explore9/outputs/reports/p0_8_industry_regime_concentration_audit.csv
Explore9/outputs/reports/p0_8_industry_regime_ablation_audit.csv
Explore9/outputs/reports/explore9_p0_8_gate_lgbm_report.md
```

Optional debug artifacts must be written under `Explore9/outputs/debug/` and must not be consumed by P1 gates unless promoted into the required list above by a future requirement revision.

---

## 14. Config sketch

```yaml
phase: p0_8
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30

label_boundary:
  observed_reference_decision_overlap_allowed_in_main_oof: false
  observed_reference_feature_overlap_allowed_in_main_oof: false
  observed_reference_label_measurement_overlap_allowed_for_pre_2025_decisions: true
  fold_2024_allowed_to_use_2025_2026_for_forward_label_measurement: true
  fold_2024_included_in_p1_promotion_oof: false
  observed_reference_label_measurement_audit_enabled: true

walk_forward:
  split_mode: purged_expanding_walk_forward
  validation_years: [2020, 2021, 2022, 2023, 2024]
  p1_promotion_validation_years: [2020, 2021, 2022, 2023]
  robustness_audit_only_years: [2024]
  fold_2024_role: robustness_audit_only_not_p1_promotion
  purge_by_label_end_date: true
  random_split_used: false
  validation_role: robustness_validation_not_clean_oos_proof
  p1_check_unit: stable_candidate_aggregated_out_of_fold
  p1_aggregation_excludes_robustness_audit_only_folds: true

sample_weight:
  mode: episode_balanced_with_group_cap
  group_key_date_field: event_effective_date
  max_instrument_year_weight_share: 0.08
  max_group_cap_iterations: 20
  normalize_total_weight_per_split: true
  output_base_sample_weight: true
  output_final_sample_weight: true
  sample_weight_alias: final_sample_weight
  equal_row_sensitivity: true

failure_dedup:
  failure_window_group_policy: merge_3d_5d_10d_for_main_p1_metrics
  window_specific_candidate_protocol: false
  main_metric_dedup_key: failure_event_dedup_candidate_id_plus_launch_stratum_event_id

gate_search:
  enabled: true
  modes: [manual_seeded_combo, beam_search_combo]
  min_tokens_per_gate: 2
  max_tokens_per_gate: 4
  max_negated_tokens_per_gate: 1
  max_industry_or_regime_tokens_per_gate: 1
  beam_width: 50
  max_candidates_per_depth: 200
  max_final_gate_candidates_per_fold: 300
  min_train_event_count: 100
  min_train_distinct_instrument_year: 25
  min_train_distinct_years: 3
  random_seed: 20260505

lgbm:
  enabled: true
  tasks: [launch_winner_score_lgbm, failure_reject_score_lgbm]
  trainability_gate_enabled: true
  skip_untrainable_fold: true
  objective: binary
  boosting_type: gbdt
  learning_rate: 0.03
  num_leaves: 31
  max_depth: 5
  min_data_in_leaf: 80
  feature_fraction: 0.75
  bagging_fraction: 0.75
  bagging_freq: 1
  lambda_l1: 0.1
  lambda_l2: 1.0
  n_estimators: 2000
  early_stopping_rounds: 100
  inner_validation_mode: latest_fully_eligible_train_year_after_purge
  early_stopping_uses_outer_validation_fold: false
  early_stopping_uses_inner_train_split_only: true
  inner_validation_fallback_to_outer_allowed: false
  disable_fold_when_inner_validation_unavailable: true
  metric: [binary_logloss, auc]
  n_jobs: 24
  random_seed: 20260505
  hyperparameter_search_enabled: false
  validation_bucket_selection_allowed: false
  predeclared_launch_score_buckets:
    - launch_top_10pct_by_train_threshold
    - launch_top_5pct_by_train_threshold
    - launch_top_2pct_by_train_threshold
  predeclared_failure_score_buckets:
    - failure_top_risk_10pct_by_train_threshold
    - failure_top_risk_5pct_by_train_threshold
    - failure_top_risk_2pct_by_train_threshold

search_bias_audit:
  enabled: true
  primary_null_mode: train_label_permutation_search_then_real_validation_eval
  validation_label_permutation_for_primary_null: false
  permutation_group_preserve: instrument_year_or_episode
  permutation_n_repeats: 100
  same_search_budget_as_real: true
  lgbm_null_full_retrain_required: true
  candidate_count_reporting: true
  empirical_p_value_enabled: true
  fdr_q_value_enabled: true

industry_regime_ablation:
  enabled: true
  train_without_industry_regime_features: true
  industry_regime_only_model_enabled: true

matched_delay:
  enabled: true
  mode: exact_real_reject_count
  n_repeats: 50
  n_jobs: 24
  max_sample_per_variant: 20000
  random_seed: 20260505

thresholds:
  min_validation_years: 3
  min_validation_folds: 3
  min_positive_validation_folds: 2
  min_fold_launch_event_count: 30
  min_fold_launch_winner_count: 3
  min_fold_launch_positive_lift_vs_all: 1.00
  min_fold_launch_positive_lift_vs_family: 1.00
  min_fold_winner_episode_coverage: 0.02
  max_fold_drawdown_degradation: 0.02
  min_fold_failure_reject_count: 30
  min_fold_failure_positive_count: 3
  min_fold_nonwinner_precision_lift: 1.00
  min_fold_failure_precision_lift: 1.00
  max_fold_false_positive_ratio_vs_family: 1.05
  max_fold_winner_false_reject_rate: 0.25
  max_fold_pending_winner_coverage_loss: 0.20
  min_fold_drawdown_avoided_vs_delay: 0.00
  min_launch_gate_event_count: 100
  min_failure_gate_event_count: 200
  min_distinct_instrument_year: 25
  min_launch_lift_vs_all: 1.10
  min_launch_lift_vs_same_family: 1.05
  min_instrument_year_lift: 1.00
  min_winner_episode_coverage: 0.05
  max_false_positive_ratio_vs_family: 1.00
  max_drawdown_degradation: 0.02
  min_nonwinner_precision_lift: 1.05
  min_failure_precision_lift: 1.05
  max_winner_false_reject_rate: 0.25
  max_big_winner_false_reject_rate: 0.15
  max_secondary_decision_false_reject_rate: 0.30
  max_secondary_decision_big_winner_false_reject_rate: 0.20
  max_pending_winner_coverage_loss: 0.30
  max_total_winner_coverage_loss: 0.20
  min_drawdown_avoided_vs_delay: 0.00
  min_before_12pct_drawdown_rate: 0.50
  min_instrument_year_filter_effect_lift: 1.00
  max_top1_instrument_contribution: 0.10
  max_top5_instrument_contribution: 0.35
  max_top_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.05
  max_industry_hhi: 0.18
  max_top1_industry_contribution: 0.35
  max_top3_industry_contribution: 0.65
  max_regime_hhi: 0.50
  max_top1_regime_contribution: 0.70
  min_industry_count_with_min_events: 3
  min_lift_vs_industry_only_baseline: 1.02
  min_without_industry_regime_ablation_lift: 1.00
  min_industry_regime_ablation_lift_ratio: 0.85
  max_candidate_baseline_missing_row_rate: 0.05
  max_candidate_baseline_missing_weight_share: 0.05
  max_train_optimized_threshold_dispersion: 0.05
  min_lgbm_train_event_count: 1000
  min_lgbm_train_positive_count: 50
  min_lgbm_train_negative_count: 200
  min_lgbm_inner_validation_event_count: 200
  min_lgbm_inner_validation_positive_count: 10
  min_lgbm_outer_validation_event_count: 200
  min_lgbm_outer_validation_positive_count: 10
  min_lgbm_train_distinct_instrument_year: 25
  min_lgbm_validation_distinct_instrument_year: 10
  max_search_bias_empirical_p: 0.10
  max_search_bias_fdr_q: 0.20
  require_search_bias_audit: true
  require_candidate_lift_exceeds_null_p95: true

runtime:
  n_jobs: 24
  max_memory_gb: 64
  parquet_compression: zstd
```

---

## 15. Report conclusion permissions

允许输出：

```text
continue_p0_8_discovery
candidate_for_p1_gate_combination_refine
candidate_for_p1_lgbm_score_refine
candidate_for_p1_extracted_gate_refine
model_predictive_but_not_actionable
nonlinear_structure_detected_but_unstable
stop_due_to_no_stable_nonlinear_structure
```

禁止输出：

```text
proceed_to_explore10_backtest
freeze_strategy
validated_p1_rule
clean_oos_rule_validated
deploy_model
```

如果 LGBM AUC / logloss 明显优于 baseline，但 P1 promotion OOF 的 instrument-year、winner coverage、false reject、matched-delay 或 search-bias 不过关，必须输出：

```text
model_predictive_but_not_actionable = true
recommendation = continue_p0_8_discovery
```

---

## 16. Implementation preflight contract checklist

实现验收必须逐项检查以下合同：

```text
1. Required artifact authority：
   第 13 节是唯一 required artifact authority。前文所有 must-output audit 必须列入第 13 节；未列入者只能是 optional/debug。

2. Candidate baseline missing：
   launch / failure P1 gate 都必须同时包含 candidate_baseline_missing_row_rate 与 candidate_baseline_missing_weight_share；candidate_weighted_baseline_missing_rate 只能作为 weight_share 的兼容别名。

3. Instrument-year weight concentration：
   sample-weight audit 必须输出 top_instrument_year_weight_share 与 instrument_year_weight_hhi；launch / failure P1 gate 必须包含 oof_top_instrument_year_weight_share 和 oof_instrument_year_weight_hhi。

3.1 Regime concentration：
   industry/regime audit 必须输出 regime_hhi 与 top1_regime_contribution；默认作为 P1 hard gate，而不是只做 audit。

3.2 Failure multi-window dedup：
   failure 主指标必须使用 failure_event_dedup_candidate_id + launch_stratum_event_id；full stable_candidate_id 可包含 window，但不得用于主 event-level dedup。failure_window_group_policy 必须来自 config，默认 merge_3d_5d_10d_for_main_p1_metrics。

3.3 Sample weight identity：
   sample panel、prediction panel、baseline audit 和 concentration audit 必须保留 base_sample_weight 与 final_sample_weight；sample_weight 只能作为 final_sample_weight 的兼容别名。

3.4 LGBM inner validation fallback：
   inner_validation_mode = latest_fully_eligible_train_year_after_purge。若找不到合格 inner validation year，则该 fold disabled_due_to_no_valid_inner_validation；不得 fallback 到 outer validation。

4. Threshold source and stable id：
   threshold_source 只允许 fixed_config / train_quantile / train_optimized / formula_constant。stable_candidate_id 必须包含 token_id、threshold_config_key、value_policy、threshold_source、learned_or_fixed、threshold_identity_value。train_optimized 必须另有 fold_resolved_candidate_id 与 train_threshold_value 审计。

5. Launch drawdown before gain：
   若 first_20pct_gain_date 缺失，launch_drawdown_before_20pct_gain_end_date = trading_day_offset(E, 59)，first_20pct_gain_missing = true；不得产生 null label。

6. Failure pending target：
   target_50h120_not_reached_before_decision_effective_date 是 failure primary target；target_100h240_not_reached_before_decision_effective_date 只用于 big-winner false-reject audit / secondary veto。
```
