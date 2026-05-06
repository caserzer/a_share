# Explore9 扩展需求 5：P0.9 行业专用 LGBM 非线性模型探索

> 文件状态：implementation-ready contract draft
> 阶段：P0.9 / Expand 5
> 核心方向：Industry-Specialist LGBM Launch / Failure Scoring Discovery
> 结论权限：hypothesis-generating only；不得进入 Explore10；不得 freeze strategy。

---

## 0. 一句话结论

P0.9 不再追求跨行业 general LGBM，而是在 **预先固定的 9 个行业内部** 分别训练行业专用 LGBM，回答：

```text
在单一行业内部，
行业内相对强度、行业宽度、波动扩张、修复质量、成交质量、market regime 与失败路径，
是否能相对 industry-local baseline，
稳定提高 launch winner discovery 或 failure rejection，
同时控制 false reject、winner coverage loss、个股集中、instrument-year 集中、regime 集中、search bias 与 label leakage？
```

P0.9 可以输出：

```text
candidate_for_industry_p1_refine
industry_model_predictive_but_not_actionable
continue_p0_9_industry_lgbm_discovery
```

P0.9 不得输出：

```text
cross_industry_general_rule
clean_oos_proven_rule
proceed_to_explore10_backtest
freeze_strategy
deploy_model
```

---

## 1. 背景与阶段定位

P0.8 已经证明两个事实：

```text
1. LGBM 在 launch / failure 两侧都有可见预测力；
2. 这些预测力高度依赖 industry / regime，不能作为跨行业 general model 直接晋级 P1。
```

因此 P0.9 的目标不是放宽 P0.8 的行业集中门槛，而是把行业集中重新定义成一个独立研究问题：

```text
如果研究者明确只关注某个行业，
能否在该行业内部训练出稳定、可审计、不过拟合的 LGBM？
```

P0.9 是 discovery / robustness validation，不是 clean OOS proof。即使某行业候选通过 P0.9，也只能进入 industry-specific P1 refine。

---

## 2. 固定行业清单

P0.9 的 target industries 必须在 requirement 和 config 中固定，不得由 P0.8 leaderboard 事后选择。

固定行业：

```text
国防军工
基础化工
汽车
交通运输
机械设备
建筑材料
传媒
电力设备
电子
```

硬规则：

```text
fixed_target_industry_list = exactly the 9 industries above
industry_selection_from_validation_performance = false
industry_selection_from_p0_8_best_bucket = false
```

非目标行业不得进入：

```text
industry-specific model training
industry-specific validation
candidate bucket denominator
industry-local baseline denominator
industry P1 promotion
```

非目标行业只允许用于 T 日可观察的 market-wide context，例如 market breadth、market regime、market percentile alias。

### 2.1 Target industry mapping audit

固定行业必须逐一映射到 PIT industry membership。不得静默使用近似行业名、混用申万一级/二级、或在运行后替换行业。

必须输出：

```text
p0_9_target_industry_mapping_audit.csv
```

字段至少包括：

```text
configured_industry_name
matched_pit_industry_name
industry_code_if_available
match_status
industry_enabled_for_p0_9
sample_event_count
sample_instrument_count
sample_instrument_year_count
missing_or_unknown_industry_count
mapping_exclusion_reason
```

P1 gate 前置要求：

```text
all fixed_target_industries appear in mapping audit;
unresolved industry rows are not silently dropped from the report;
if match_status != exact_match:
  industry_enabled_for_p0_9 = false
  candidate_for_industry_p1_refine = false for that industry
```

---

## 3. 数据边界与禁止项

P0.9 沿用 Explore9 / Explore7 PIT 数据链路：

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

硬约束：

```text
每个 date + instrument 样本必须在当日 PIT membership 中；
行业归属必须按 date + instrument 的 PIT industry membership join；
成交额字段必须使用 money，不得改用 amount；
OHLC 默认已复权，不得再次乘 factor；
Explore3-Explore8 trade results / signals / daily candidates / model predictions 不得作为 feature、label、selection input 或排序依据；
2025-2026 observed reference 不得用于 feature、threshold、bucket、model、candidate 或 P1 promotion。
```

---

## 4. 时间范围、fold role 与 purge

### 4.1 时间范围

```text
data_start: 2017-01-01
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30
```

### 4.2 Fold 定义

```text
fold_2020: train 2017-2019, validation 2020, role = p1_promotion_eligible
fold_2021: train 2017-2020, validation 2021, role = p1_promotion_eligible
fold_2022: train 2017-2021, validation 2022, role = p1_promotion_eligible
fold_2023: train 2017-2022, validation 2023, role = p1_promotion_eligible
fold_2024: train 2017-2023, validation 2024, role = robustness_audit_only
```

P0.9 必须输出两个 OOF scope：

```text
oof_core_2020_2023:
  includes fold_2020, fold_2021, fold_2022, fold_2023 only;
  excludes fold_2024;
  excludes observed-reference label measurement rows;
  is the only source for candidate_for_industry_p1_refine.

oof_with_2024_label_measurement:
  includes fold_2020 ... fold_2024;
  fold_2024 may use 2025-2026 only for forward label measurement of pre-2025 decisions;
  audit / robustness only;
  cannot promote P1 candidates.
```

### 4.3 Purged expanding walk-forward

P0.9 的 walk-forward 必须是真正的 purged walk-forward。对任一 outer fold：

```text
validation_start_date = first trading day of validation year
validation_end_date = last trading day of validation year
```

任何 train row 必须满足：

```text
train_feature_asof_date < validation_start_date
train_event_effective_date < validation_start_date
train_label_window_end_date < validation_start_date
```

其中：

```text
train_label_window_end_date = max label horizon end date used by the task / training loss / validation metric.
```

如果 launch task 同时训练或审计 50h120 与 100h240，则 train purge 必须使用更长的 240d end date；如果某一模型只训练 50h120，但 P1 gate 仍审计 100h240 false reject，则对应 P1 promotion 样本也必须满足其 P1 gate 所需 label window 不跨入 validation_start。

被 purge 的 train rows 不得进入：

```text
training loss
inner validation split
feature selection
threshold selection
bucket threshold fitting
null full-retrain training set
trainability positive / negative count
```

### 4.4 Inner validation purge

如果 LGBM early stopping 使用 train fold 内部的 inner validation，则 inner split 也必须 purge：

```text
inner_validation_start_date = first trading day of inner validation period
inner_train_feature_asof_date < inner_validation_start_date
inner_train_event_effective_date < inner_validation_start_date
inner_train_label_window_end_date < inner_validation_start_date
```

Outer validation fold 不得用于 early stopping、best iteration、hyperparameter、feature selection、bucket selection、leaf rule selection 或 threshold optimization。

### 4.5 Purge audit

必须输出：

```text
p0_9_walk_forward_purge_audit.csv
p0_9_inner_validation_purge_audit.csv
```

字段至少包括：

```text
target_industry
model_task
fold_id
split_name
validation_start_date
validation_end_date
max_label_horizon_days_used_for_purge
raw_train_event_count
purged_due_to_label_window_cross_validation_count
purged_due_to_event_effective_date_count
purged_due_to_feature_asof_date_count
train_event_count_after_purge
train_positive_count_after_purge
train_negative_count_after_purge
inner_validation_event_count_after_purge
outer_validation_event_count_eligible
purge_rule_pass
```

P1 gate 必须要求：

```text
walk_forward_purge_rule_pass = true
inner_validation_purge_rule_pass = true
```

---

## 5. Signal date、feature-asof 与 next-open 执行

P0.9 默认信号来自 close-derived formula，因此必须区分：

```text
signal_date = formula observed close date
feature_asof_date = signal_date
event_effective_date = next_trading_day(signal_date)
effective_price_reference = open on event_effective_date
```

Launch：

```text
stratum_date = launch close-derived signal date
stratum_effective_date = next_trading_day(stratum_date)
event_effective_date = stratum_effective_date
feature_asof_date = stratum_date
```

Failure：

```text
failure_signal_date = close-derived failure signal date
failure_decision_effective_date = next_trading_day(failure_signal_date)
event_effective_date = failure_decision_effective_date
feature_asof_date = failure_signal_date
```

禁止：

```text
using event_effective_date high / low / close as model feature;
using event_effective_date volume / money as model feature;
using next_open as predictive feature;
using any feature with feature_asof_date > signal_date for close-derived formulas.
```

`next_open` 只允许作为：

```text
execution price reference
label reference price
execution feasibility audit
```

必须输出：

```text
p0_9_feature_asof_leakage_audit.csv
```

P1 gate 必须要求：

```text
feature_asof_leakage_violation_count = 0
```

---

## 6. Observed-reference overlap

必须拆分三类 overlap：

```text
observed_reference_decision_overlap:
  signal / decision / effective / feature_asof date >= observed_reference_start.
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_feature_overlap:
  feature value 需要 observed_reference_start 之后的数据才能计算。
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_label_measurement_overlap:
  decision / feature 仍在 research_end 之前，
  但 forward label measurement window 跨入 observed reference。
  只允许用于 pre-2025 decision 的 forward outcome measurement；
  只能进入 robustness / audit，不得进入 P1 promotion。
```

必须输出：

```text
p0_9_observed_reference_overlap_audit.csv
p0_9_observed_reference_row_audit.parquet
```

`p0_9_observed_reference_overlap_audit.csv` 字段至少包括：

```text
panel_name
target_industry
model_task
fold_id
raw_rows
decision_overlap_rows
feature_overlap_rows
label_measurement_overlap_rows
rows_entered_train
rows_entered_outer_validation
rows_entered_p1_promotion
eligible_overlap_rows
pass
```

`p0_9_observed_reference_row_audit.parquet` 字段至少包括：

```text
panel_name
sample_id
target_industry
model_task
fold_id
instrument
signal_date
event_effective_date
feature_asof_date
label_window_start_date
label_window_end_date
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
label_measurement_uses_observed_reference
row_used_for_training
row_used_for_outer_validation
row_used_for_p1_promotion
row_used_for_robustness_audit_only
overlap_exclusion_reason
```

P1 gate 必须要求：

```text
observed_reference_decision_overlap_rows_entered_p1 = 0
observed_reference_feature_overlap_rows_entered_p1 = 0
observed_reference_label_measurement_rows_used_for_p1_promotion = false
```

---

## 7. 样本单位与 train/eval eligibility

### 7.1 Launch sample

样本单位：

```text
one row per target_industry + launch_stratum_event_id
```

主字段：

```text
target_industry
instrument
launch_stratum_event_id
launch_episode_id
launch_family
launch_variant
launch_declared_role
signal_date
stratum_date
stratum_effective_date
event_effective_date
stratum_effective_price_reference
feature_asof_date
fold_id
validation_fold_role
sample_weight
final_sample_weight
event_instrument_year
train_label_window_end_date
label_horizon_truncated
```

Eligibility：

```text
industry_launch_model_train_eval_eligible =
  target_industry in fixed_target_industry_list
  and pit_industry_on_event_effective_date = target_industry
  and event_effective_date <= research_end
  and feature_asof_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_measurement_available = true
  and sample_has_required_features = true
  and feature_asof_leakage_violation = false
  and purge_eligible_for_current_fold = true
```

For P1 promotion rows additionally：

```text
label_horizon_truncated = false
label_measurement_uses_observed_reference = false
```

### 7.2 Failure sample

训练样本单位：

```text
one row per target_industry + launch_stratum_event_id + failure_decision_window
```

主 OOF / P1 指标必须 event-level dedup：

```text
failure_event_level_dedup_key =
  target_industry + failure_event_dedup_candidate_id + launch_stratum_event_id
```

`failure_decision_window` 可以作为模型输入或 full stable candidate identity 的一部分，但主指标 dedup id 必须可排除 window-only tokens。

主字段：

```text
target_industry
instrument
launch_stratum_event_id
failure_decision_window
failure_signal_date
failure_decision_effective_date
event_effective_date
failure_decision_effective_price_reference
failure_full_stable_candidate_id
failure_event_dedup_candidate_id
feature_asof_date
fold_id
validation_fold_role
sample_weight
final_sample_weight
event_instrument_year
train_label_window_end_date
label_horizon_truncated
```

Eligibility：

```text
industry_failure_model_train_eval_eligible =
  target_industry in fixed_target_industry_list
  and pit_industry_on_event_effective_date = target_industry
  and event_effective_date <= research_end
  and feature_asof_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_measurement_available = true
  and sample_has_required_features = true
  and feature_asof_leakage_violation = false
  and purge_eligible_for_current_fold = true
  and target_50h120_not_reached_before_decision_effective_date = true for failure primary training/eval
```

Already-achieved target rows：

```text
if target_50h120_reached_before_decision_effective_date = true:
  exclude_from_failure_primary_training_loss = true
  exclude_from_failure_primary_precision_metrics = true
  include_in_post_target_risk_audit_only = true
  if target_100h240_not_reached_before_decision_effective_date = true:
    include_in_big_winner_100h240_false_reject_audit = true
    include_in_post_50_pre_100_big_winner_audit = true
```

For P1 promotion rows additionally：

```text
label_horizon_truncated = false
label_measurement_uses_observed_reference = false
```

---

## 8. Label / metric dictionary

必须输出：

```text
p0_9_label_dictionary.csv
```

schema 至少包括：

```text
label_name
model_task
label_type
label_definition_formula
reference_date_field
reference_price_field
horizon_trading_days
label_window_start_rule
label_window_end_rule
label_window_includes_effective_date_high_low
positive_condition
negative_condition
label_end_date_field
eligibility_field
observed_reference_label_measurement_allowed
post_target_handling
used_for_training
used_for_validation
used_for_industry_p1_gate
sign_convention
denominator_unit
```

### 8.1 Label window convention

所有 forward label 的 window 起点都是 `event_effective_date` 当天，不是 signal date，也不是 t+1：

```text
label_window_start = event_effective_date
label_window_N = [event_effective_date, trading_day_offset(event_effective_date, N - 1)]
label_window_includes_effective_date_high_low = true
```

### 8.2 Launch labels

令：

```text
E = stratum_effective_date
P = stratum_effective_price_reference
```

Launch primary：

```text
launch_winner_50h120 =
  max(high over [E, trading_day_offset(E, 119)]) / P - 1 >= 0.50
```

Launch secondary：

```text
launch_winner_50c120 =
  max(close over [E, trading_day_offset(E, 119)]) / P - 1 >= 0.50

launch_winner_100h240 =
  max(high over [E, trading_day_offset(E, 239)]) / P - 1 >= 1.00

launch_winner_100c240 =
  max(close over [E, trading_day_offset(E, 239)]) / P - 1 >= 1.00

launch_future_20pct_high_60d =
  max(high over [E, trading_day_offset(E, 59)]) / P - 1 >= 0.20
```

Drawdown labels：

```text
launch_future_max_drawdown_60d =
  min(low over [E, trading_day_offset(E, 59)]) / P - 1
```

Sign convention：drawdown 为负数，`-0.12` 表示 12% 回撤。

```text
first_20pct_gain_date =
  first date d in [E, trading_day_offset(E, 59)] where high_d / P - 1 >= 0.20

if first_20pct_gain_date exists:
  launch_drawdown_before_20pct_gain_end_date = first_20pct_gain_date
  first_20pct_gain_missing = false
else:
  launch_drawdown_before_20pct_gain_end_date = trading_day_offset(E, 59)
  first_20pct_gain_missing = true

launch_drawdown_before_20pct_gain =
  min(low over [E, launch_drawdown_before_20pct_gain_end_date]) / P - 1

launch_drawdown_before_20pct_gain_le_10pct =
  launch_drawdown_before_20pct_gain >= -0.10
```

False positive：

```text
launch_false_positive_primary =
  launch_winner_50h120 = false
  and launch_future_max_drawdown_60d <= -0.12
```

Launch P1 aggregation metrics：

```text
launch_winner_rate =
  weighted count(candidate rows where launch_winner_50h120 = true)
  / weighted count(candidate rows)

winner_episode_coverage =
  unique launch_episode_id in candidate rows where launch_winner_50h120 = true
  / unique launch_episode_id in candidate opportunity scope where launch_winner_50h120 = true

median_future_max_drawdown_60d =
  weighted median of launch_future_max_drawdown_60d over candidate rows

fold_median_drawdown_not_worse_than_baseline =
  fold_median_future_max_drawdown_60d >= fold_candidate_scope_baseline_median_drawdown_60d - thresholds.max_drawdown_worsening
```

Launch baseline join for `winner_episode_coverage` and `median_future_max_drawdown_60d` must use the same candidate-scope weighted baseline composition rules in section 9.4.

### 8.3 Failure labels

令：

```text
D = failure_decision_effective_date
Q = failure_decision_effective_price_reference
E = stratum_effective_date
P = stratum_effective_price_reference
```

Failure drawdown from decision：

```text
failure_drawdown_from_decision_60d =
  min(low over [D, trading_day_offset(D, 59)]) / Q - 1
```

Failure primary positive：

```text
failure_reject_positive_primary =
  launch_winner_50h120_from_launch_reference = false
  and failure_drawdown_from_decision_60d <= -0.12
```

From-launch false reject / winner coverage loss：

```text
target_50h120_not_reached_before_decision_effective_date =
  max(high over [E, previous_trading_day(D)]) / P - 1 < 0.50

target_100h240_not_reached_before_decision_effective_date =
  max(high over [E, previous_trading_day(D)]) / P - 1 < 1.00

target_50h120_reached_before_decision_effective_date =
  not target_50h120_not_reached_before_decision_effective_date

target_100h240_reached_before_decision_effective_date =
  not target_100h240_not_reached_before_decision_effective_date

post_50_pre_100_pending_big_winner_state =
  target_50h120_reached_before_decision_effective_date = true
  and target_100h240_not_reached_before_decision_effective_date = true

failure_false_reject_vs_launch_target_50h120 =
  target_50h120_not_reached_before_decision_effective_date = true
  and launch_winner_50h120_from_launch_reference = true

failure_false_reject_vs_launch_target_100h240 =
  target_100h240_not_reached_before_decision_effective_date = true
  and launch_winner_100h240_from_launch_reference = true
```

P1 failure gate 使用 from-launch 作为主口径：

```text
winner_false_reject_from_launch_rate =
  event-level dedup rejected rows with failure_false_reject_vs_launch_target_50h120 = true
  / event-level dedup rejected rows where target_50h120_not_reached_before_decision_effective_date = true

big_winner_false_reject_from_launch_rate =
  event-level dedup rejected rows with failure_false_reject_vs_launch_target_100h240 = true
  / event-level dedup rejected rows where target_100h240_not_reached_before_decision_effective_date = true

pending_winner_coverage_loss_from_launch =
  unique pending launch winners rejected by candidate
  / unique pending launch winners in candidate opportunity scope

total_winner_coverage_loss_from_launch =
  unique launch winners rejected by candidate before achieving target
  / unique launch winners in candidate opportunity scope

post_50_pre_100_big_winner_false_reject_rate =
  event-level dedup rejected rows with post_50_pre_100_pending_big_winner_state = true
  and launch_winner_100h240_from_launch_reference = true
  / event-level dedup opportunity rows with post_50_pre_100_pending_big_winner_state = true
  and launch_winner_100h240_from_launch_reference = true
```

Primary failure training may exclude rows that already achieved `50h120`, but big-winner protection must not drop `post_50_pre_100_pending_big_winner_state` rows from 100h240 false-reject / coverage-loss audits. These rows must be marked:

```text
exclude_from_failure_primary_training_loss = true
exclude_from_failure_primary_precision_metrics = true
include_in_big_winner_100h240_false_reject_audit = true
include_in_post_50_pre_100_big_winner_audit = true
```

From-decision residual upside 只作为 secondary veto / diagnostic downgrade：

```text
failure_false_reject_vs_decision_target_50h120 =
  max(high over [D, trading_day_offset(D, 119)]) / Q - 1 >= 0.50

failure_false_reject_vs_decision_target_100h240 =
  max(high over [D, trading_day_offset(D, 239)]) / Q - 1 >= 1.00
```

Decision-reference secondary veto：

```text
decision_reference_residual_50h120_rate =
  event-level dedup rejected rows with failure_false_reject_vs_decision_target_50h120 = true
  / event-level dedup rejected rows

decision_reference_residual_100h240_rate =
  event-level dedup rejected rows with failure_false_reject_vs_decision_target_100h240 = true
  / event-level dedup rejected rows

decision_reference_secondary_veto_pass =
  decision_reference_residual_50h120_rate <= thresholds.max_decision_reference_residual_50h120_rate
  and decision_reference_residual_100h240_rate <= thresholds.max_decision_reference_residual_100h240_rate
```

该 veto 只使用 from-decision residual upside，不替代 from-launch false-reject 主口径。若 veto 不通过，`candidate_for_industry_p1_refine = false`，但仍可在报告中标记为 `industry_failure_direction_valid_but_false_reject_too_high`。

Failure primary precision / lift 主口径：

```text
failure_primary_eval_row =
  event-level dedup rejected row
  where exclude_from_failure_primary_precision_metrics != true

failure_primary_eval_denominator =
  count(failure_primary_eval_row)

failure_precision =
  count(failure_primary_eval_row where failure_reject_positive_primary = true)
  / failure_primary_eval_denominator

nonwinner_precision =
  count(failure_primary_eval_row where launch_winner_50h120_from_launch_reference = false)
  / failure_primary_eval_denominator

failure_precision_lift_vs_candidate_scope_weighted_baseline =
  failure_precision / candidate_scope_weighted_failure_baseline_precision

nonwinner_precision_lift =
  nonwinner_precision / candidate_scope_weighted_baseline_nonwinner_precision

failure_precision_lift_vs_matched_delay =
  failure_precision / matched_delay_failure_precision
```

`post_50_pre_100_pending_big_winner_state` 行不得进入 `failure_primary_eval_row`，但必须进入 false-reject / coverage-loss audit。所有 precision / lift 的分母必须是 event-level dedup 后的 rejected row，不得使用 raw multi-window row。

### 8.4 Drawdown timing / matched-delay metrics

```text
first_12pct_drawdown_date_from_launch_reference =
  first date d in [E, trading_day_offset(E, 59)] where low_d / P - 1 <= -0.12

filter_before_12pct_drawdown =
  first_12pct_drawdown_date_from_launch_reference exists
  and D < first_12pct_drawdown_date_from_launch_reference

filter_same_day_as_12pct_drawdown_ambiguous =
  first_12pct_drawdown_date_from_launch_reference exists
  and D = first_12pct_drawdown_date_from_launch_reference

filter_before_12pct_drawdown_rate =
  count(event-level dedup rejected rows where filter_before_12pct_drawdown = true)
  / count(event-level dedup rejected rows where first_12pct_drawdown_date_from_launch_reference exists)

filter_before_12pct_drawdown_rate_including_same_day_sensitivity =
  count(event-level dedup rejected rows where filter_before_12pct_drawdown = true or filter_same_day_as_12pct_drawdown_ambiguous = true)
  / count(event-level dedup rejected rows where first_12pct_drawdown_date_from_launch_reference exists)

same_day_12pct_drawdown_ambiguous_share =
  count(event-level dedup rejected rows where filter_same_day_as_12pct_drawdown_ambiguous = true)
  / count(event-level dedup rejected rows where first_12pct_drawdown_date_from_launch_reference exists)
```

P1 主口径必须使用严格的 `D < first_12pct_drawdown_date_from_launch_reference`。同日 `D = drawdown_date` 因日线无法判断 open 后先 reject 还是先触及 low，只能进入 sensitivity / audit，不得支撑 P1 gate。

`drawdown_avoided_vs_matched_delay`：

```text
real_adverse_drawdown_after_reject_60d =
  median(abs(min(0, failure_drawdown_from_decision_60d)))
  over event-level dedup rejected rows

matched_delay_adverse_drawdown_after_pseudo_reject_60d =
  median(abs(min(0, matched_delay_drawdown_from_pseudo_reject_60d)))
  over matched-delay pseudo reject rows with exact real reject count

drawdown_avoided_vs_matched_delay =
  real_adverse_drawdown_after_reject_60d
  - matched_delay_adverse_drawdown_after_pseudo_reject_60d
```

因此正值表示真实 failure gate 拒绝的样本后续 adverse drawdown 大于 matched-delay pseudo reject，说明 gate 比同数量随机延迟拒绝多避开了下跌；负值表示该 gate 反而不如 matched-delay。

Denominator unit：

```text
event-level dedup rejected row = target_industry + failure_event_dedup_candidate_id + launch_stratum_event_id
```

---

## 9. Industry-local baseline 与 baseline sparsity

### 9.1 Required baseline artifacts

必须输出：

```text
p0_9_industry_local_baseline.csv
p0_9_industry_failure_opportunity_baseline.csv
p0_9_industry_candidate_scope_weighted_baseline.csv
p0_9_industry_baseline_sparsity_audit.csv
p0_9_fold_local_p0_8_baseline_audit.csv
```

`p0_9_industry_local_baseline.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
validation_fold_role
baseline_scope_type
baseline_scope_key
baseline_denominator_unit
baseline_join_key
eligible_event_count
positive_count
positive_rate
industry_local_all_launch_baseline_rate
industry_local_same_family_baseline_rate
false_positive_rate
median_drawdown_60d
winner_episode_coverage
failure_precision
nonwinner_precision
label_horizon_truncated_rate
observed_reference_label_measurement_rate
```

`p0_9_industry_failure_opportunity_baseline.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
failure_decision_window
reject_delay_bucket
failure_opportunity_family
failure_opportunity_variant
lifecycle_pool
regime_bucket
eligible_failure_opportunity_count
failure_positive_count
industry_local_failure_baseline_precision
nonwinner_precision
winner_false_reject_from_launch_rate
big_winner_false_reject_from_launch_rate
pending_winner_coverage_loss_from_launch
median_failure_drawdown_from_decision_60d
```

`p0_9_industry_candidate_scope_weighted_baseline.csv` 字段至少包括：

```text
target_industry
model_task
stable_candidate_id
predeclared_bucket_id
candidate_row_count
candidate_weight
candidate_scope_weighted_baseline_positive_rate
candidate_scope_weighted_baseline_false_positive_rate
candidate_scope_weighted_baseline_median_drawdown_60d
candidate_scope_weighted_failure_baseline_precision
candidate_scope_weighted_baseline_nonwinner_precision
candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share
candidate_baseline_fallback_level
```

`p0_9_industry_baseline_sparsity_audit.csv` 字段至少包括：

```text
target_industry
model_task
baseline_scope_type
baseline_composition_key
baseline_cell_event_count
baseline_cell_positive_count
baseline_cell_sparse
baseline_fallback_level
baseline_fallback_reason
candidate_baseline_sparse_cell_weight_share
baseline_sparsity_audit_pass
```

### 9.2 Launch baseline scopes

Launch baseline 至少包括：

```text
industry_local_all_launch_baseline
industry_local_same_family_baseline
industry_local_same_lifecycle_baseline
industry_local_same_regime_baseline
industry_local_fold_local_p0_8_bucket_baseline_audit_only
```

所有 lift 必须相对行业内 baseline，不得用全市场 baseline 替代。

### 9.3 Failure opportunity baseline

Failure P1 gate 中的：

```text
industry_local_failure_baseline_precision
```

必须来自显式的 failure opportunity baseline：

```text
industry_local_failure_opportunity_baseline_by_window_delay
```

baseline denominator 至少按以下字段分层：

```text
target_industry
model_task
fold_id
failure_decision_window
reject_delay_bucket
failure_opportunity_family
failure_opportunity_variant
lifecycle_pool
regime_bucket
```

这样可以防止 failure model 通过集中在更容易的 window / delay bucket 抬高 precision。

### 9.4 Candidate-scope weighted baseline

对于 LGBM bucket / leaf bucket / mixed-family gate，baseline 必须按 candidate 覆盖样本的 composition 加权。

Launch composition key：

```text
target_industry
model_task
launch_family
launch_variant
lifecycle_pool
regime_bucket
```

Failure composition key：

```text
target_industry
model_task
failure_opportunity_family
failure_opportunity_variant
lifecycle_pool
regime_bucket
failure_decision_window
reject_delay_bucket
```

计算：

```text
for each candidate bucket:
  compute candidate row composition using final_sample_weight;
  join corresponding industry-local baseline cell;
  compute weighted average baseline metrics;
```

### 9.5 Baseline missing 与 sparse denominator

必须同时输出：

```text
candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share
candidate_baseline_shrinkage_used
candidate_baseline_fallback_level
```

P1 gate 必须约束：

```text
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share <= thresholds.max_candidate_baseline_sparse_cell_weight_share
```

Baseline cell minimum：

```text
baseline_cell_event_count >= thresholds.min_baseline_cell_event_count
baseline_cell_positive_count >= thresholds.min_baseline_cell_positive_count for positive-rate baseline
```

如果 cell 太小，必须使用预注册 fallback hierarchy，不得临时发明：

```text
level_0: exact industry + task + family/variant + lifecycle + regime + window + delay
level_1: drop variant, keep family + lifecycle + regime + window + delay
level_2: drop delay bucket, keep family + lifecycle + regime + window
level_3: drop window, keep family + lifecycle + regime
level_4: industry + task + lifecycle + regime
level_5: industry + task all eligible opportunities
```

Fallback 后仍不满足 minimum 的 row 计入 baseline missing。

---

## 10. Feature dictionary 与行业专用特征

必须输出：

```text
p0_9_feature_dictionary.csv
p0_9_model_feature_set_manifest.csv
```

`industry`、`industry_code`、`target_industry_name` 本身不得作为模型 feature。允许使用行业动态状态和行业内 rank：

```text
industry_breadth_20d
industry_breadth_change_5d
industry_relative_strength_vs_market_20d
industry_relative_strength_vs_market_60d
industry_money_breadth_20d
industry_volatility_regime
industry_leader_count
stock_ret20_pctile_within_industry
stock_money_rank_within_industry
stock_vol_rank_within_industry
stock_rank_jump_within_industry
industry_regime
market_regime
```

所有实际输入 LGBM 的 feature 必须有：

```text
feature_name
feature_family
feature_asof_rule
raw_or_derived
raw_required_field_exempt
formula_text_resolved
uses_event_effective_date_ohlc
allowed_for_launch_model
allowed_for_failure_model
observed_reference_feature_overlap_possible
```

P1 gate 必须要求：

```text
uses_event_effective_date_ohlc = false for all model features
feature_asof_leakage_violation_count = 0
```

---

## 11. LGBM training contract

### 11.1 Model tasks

Launch model：

```text
model_name: industry_launch_winner_score_lgbm
sample_unit: target_industry + launch_stratum_event_id
primary_label: launch_winner_50h120
predeclared_buckets:
  - launch_top_10pct_by_train_threshold
  - launch_top_5pct_by_train_threshold
  - launch_top_2pct_by_train_threshold
```

Failure model：

```text
model_name: industry_failure_reject_score_lgbm
sample_unit: target_industry + launch_stratum_event_id + failure_decision_window
primary_label: failure_reject_positive_primary
predeclared_buckets:
  - failure_top_risk_10pct_by_train_threshold
  - failure_top_risk_5pct_by_train_threshold
  - failure_top_risk_2pct_by_train_threshold
```

Raw scores 不得跨行业排序。不同 target_industry 的 top 5% 只代表该行业内 top 5%。

### 11.2 Early stopping

Outer validation fold 不得用于：

```text
early stopping
best iteration selection
hyperparameter selection
feature selection
bucket selection
threshold selection
leaf-rule selection
candidate selection
```

如果使用 early stopping，只能使用 train fold 内部 purged inner validation：

```text
early_stopping_uses_outer_validation_fold = false
early_stopping_uses_inner_train_split_only = true
```

如果实现无法做到，则：

```text
early_stopping_rounds = null
n_estimators_fixed = true
```

### 11.3 Fold trainability

必须输出：

```text
p0_9_industry_lgbm_fold_trainability_audit.csv
```

每个 `target_industry + model_task + fold_id` 必须训练前检查：

```text
walk_forward_purge_rule_pass = true
inner_validation_purge_rule_pass = true
train_event_count_after_purge >= thresholds.min_industry_lgbm_train_event_count
train_positive_count_after_purge >= thresholds.min_industry_lgbm_train_positive_count
train_negative_count_after_purge >= thresholds.min_industry_lgbm_train_negative_count
train_distinct_instruments >= thresholds.min_industry_lgbm_train_distinct_instruments
train_distinct_instrument_years >= thresholds.min_industry_lgbm_train_distinct_instrument_years
inner_validation_event_count >= thresholds.min_industry_lgbm_inner_validation_event_count
inner_validation_positive_count >= thresholds.min_industry_lgbm_inner_validation_positive_count
outer_validation_event_count_eligible >= thresholds.min_industry_lgbm_outer_validation_event_count
outer_validation_positive_count_eligible >= thresholds.min_industry_lgbm_outer_validation_positive_count
outer_validation_distinct_instruments >= thresholds.min_industry_lgbm_outer_validation_distinct_instruments
outer_validation_distinct_instrument_years >= thresholds.min_industry_lgbm_outer_validation_distinct_instrument_years
```

不满足则：

```text
lgbm_training_enabled_for_industry_fold = false
fold_excluded_from_industry_lgbm_oof_aggregation = true
fold_status = disabled_due_to_insufficient_industry_sample_or_purge
```

禁止用 SMOTE、重复采样或 class-weight trick 强行让薄样本 fold 进入主 OOF。

### 11.4 Aggregate trainability pass

P1 gate 中的：

```text
industry_launch_trainability_pass
industry_failure_trainability_pass
```

定义为：

```text
For the given target_industry + model_task + candidate:
  all p1_promotion_eligible core folds included in oof_core_2020_2023 are trainable;
  core_trainable_fold_count >= thresholds.min_core_trainable_folds_for_industry_p1;
  candidate has predictions in all trainable core folds;
  no candidate-included fold has fold_status disabled.
```

默认：

```text
thresholds.min_core_trainable_folds_for_industry_p1 = 4
```

因此若某行业在 fold_2020-2023 任一核心 fold 样本不足，默认只能 diagnostic-only，除非 config 预先降低该阈值并且报告降级结论权限。

### 11.5 Feasibility / sample sufficiency audits

正式训练前必须先输出固定行业 feasibility count，不得因样本不足从固定清单中删除行业。

必须输出：

```text
p0_9_industry_feasibility_count_audit.csv
p0_9_industry_sample_sufficiency_audit.csv
```

`p0_9_industry_feasibility_count_audit.csv` 字段至少包括：

```text
target_industry
pit_mapping_status
industry_enabled_for_p0_9
overall_distinct_instruments
overall_distinct_instrument_years
overall_launch_events
overall_launch_50h120_positive_count
overall_failure_opportunities
overall_failure_positive_count
fold_id
train_event_count_after_purge
train_positive_count_after_purge
outer_validation_event_count_eligible
outer_validation_positive_count_eligible
expected_promotion_feasibility
non_promotable_reason
```

`p0_9_industry_sample_sufficiency_audit.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
fold_trainability_pass
aggregate_trainability_pass
sample_sufficiency_pass
sample_sufficiency_fail_reason
diagnostic_only_due_to_insufficient_sample
candidate_for_industry_p1_refine_allowed
```

若任一固定行业样本不足：

```text
diagnostic_only_due_to_insufficient_sample = true
candidate_for_industry_p1_refine = false for that industry
industry still appears in report and candidate summary
```

### 11.6 Sample weight group cap

Sample weight cap 必须是 group aggregate cap，不是单行 `min(weight, cap)`。

Group key：

```text
fold_id + split + model_task + target_industry + instrument + calendar_year(event_effective_date)
```

必须输出：

```text
p0_9_sample_weight_group_cap_audit.csv
```

P1 gate 必须约束：

```text
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
```

---

## 12. Null full-retrain 与 candidate-level aggregation

### 12.1 Runtime scope

Null full-retrain 分两级：

```text
screening_null:
  run for all trainable industry + task + fold + predeclared bucket;
  n_repeats >= thresholds.min_lgbm_null_screening_repeats;
  discovery warning only.

promotion_null:
  run only for candidates that pass all non-null P1 gates;
  n_repeats >= thresholds.min_lgbm_null_promotion_repeats;
  required for candidate_for_industry_p1_refine = true.
```

必须输出：

```text
p0_9_lgbm_null_runtime_plan.csv
p0_9_lgbm_null_permutation_baseline.csv
p0_9_candidate_level_null_aggregation.csv
```

### 12.2 Fold-level null process

For each null repeat `r` and each `target_industry + model_task + fold_id`：

```text
1. permute train labels within target_industry + model_task + fold train set;
2. retrain full LGBM using the same feature set, config, sample weighting and inner-validation rule;
3. derive bucket thresholds using the same predeclared train-bucket policy;
4. apply frozen null model and frozen null thresholds to real outer validation features;
5. evaluate with real outer validation labels.
```

禁止：

```text
permuting validation labels as primary null;
reusing real model scores for null;
selecting null buckets by validation performance;
averaging fold p-values as candidate p-value.
```

### 12.3 Candidate-level OOF null aggregation

P1 gate 是 candidate-level，因此 null 也必须 candidate-level。对每个真实 candidate `C`：

Primary null metric 必须预注册，不能在看完 null / validation 后选择：

```text
if model_task = industry_launch_winner_score_lgbm:
  primary_null_metric_name = launch_lift_vs_candidate_scope_weighted_baseline
  primary_null_metric_direction = higher_is_better

if model_task = industry_failure_reject_score_lgbm:
  primary_null_metric_name = failure_precision_lift_vs_candidate_scope_weighted_baseline
  primary_null_metric_direction = higher_is_better
```

Matched-delay lift、drawdown avoided、false reject、coverage loss 和 decision-reference residual upside 是 failure P1 gate 的额外 veto / robustness 条件，不得替代 primary null metric，也不得事后选择最有利指标作为 null metric。

```text
real_oof_metric(C) = aggregate the preregistered primary_null_metric over oof_core_2020_2023 using the same event-level dedup, sample weight and denominator rules as P1 gate.
```

For each null repeat `r`：

```text
null_oof_metric_r(C) = aggregate the same preregistered primary_null_metric on null validation rows over the same oof_core_2020_2023 folds, using the same stable candidate identity, bucket policy, event-level dedup, sample weight and denominator rules.
```

Candidate p-value：

```text
empirical_p_value(C) =
  (1 + count_r(null_oof_metric_r(C) >= real_oof_metric(C))) / (1 + n_repeats)
```

Null P95：

```text
candidate_lift_exceeds_null_p95 =
  real_oof_metric(C) > percentile_95({null_oof_metric_r(C)})
```

FDR：

```text
fdr_q_value_within_industry_task =
  Benjamini-Hochberg q-value computed within target_industry + model_task + candidate_type family.

fdr_q_value_across_fixed_industries =
  Benjamini-Hochberg q-value computed across all fixed_target_industries + model_task + candidate_type family.
```

P1 promotion 必须使用 `fdr_q_value_across_fixed_industries`。`fdr_q_value_within_industry_task` 只能作为诊断字段，防止在 9 个固定行业中事后挑出最好行业时低估 search bias。

`p0_9_candidate_level_null_aggregation.csv` 字段至少包括：

```text
target_industry
model_task
candidate_type
stable_candidate_id
primary_null_metric_name
primary_null_metric_direction
real_oof_metric
null_repeat_count
null_p95
empirical_p_value
fdr_q_value_within_industry_task
fdr_q_value_across_fixed_industries
candidate_lift_exceeds_null_p95
promotion_null_executed
```

不得只测试最好 folds；不得以 per-fold null pass count 替代 candidate-level p-value / q-value。

---

## 13. Candidate identity

### 13.1 LGBM bucket identity

`stable_candidate_id` 必须包含足够的模型 / 数据 / 配置 identity，避免不同模型共用同一候选 ID。

字段：

```text
target_industry
model_task
candidate_type
predeclared_bucket_id
bucket_policy
feature_set_version
label_version
sample_panel_version
industry_mapping_version
lgbm_config_hash
sample_weight_policy_hash
trainability_policy_hash
random_seed
training_code_version
null_policy_version
```

### 13.2 Failure dedup identity

Failure 需要两个 ID：

```text
failure_full_stable_candidate_id:
  may include failure_decision_window and window-specific policy.

failure_event_dedup_candidate_id:
  excludes window-only tokens and is used for OOF / P1 event-level dedup.
```

主指标固定使用：

```text
failure_event_level_dedup_key =
  target_industry + failure_event_dedup_candidate_id + launch_stratum_event_id
```

### 13.3 Threshold identity

若存在 train_quantile / train_optimized threshold，则 candidate identity 必须记录：

```text
ordered_token_id_list
ordered_threshold_config_key_list
ordered_threshold_value_policy_list
ordered_threshold_source_list
ordered_learned_or_fixed_list
ordered_threshold_identity_value_list
train_threshold_value_bucket_or_hash
```

同名公式在不同 fold 中若 numeric threshold 语义不同，不得被错误聚合成同一 stable candidate，除非已通过预注册 threshold canonicalization。

---

## 14. Matched-delay for failure

Failure model 必须继续保留 matched-delay baseline。

默认：

```text
matched_delay_mode = exact_real_reject_count
matched_delay_unit = event-level dedup rejected row
matched_delay_random_seed = 20260505
matched_delay_n_repeats >= 100
```

Pseudo reject set：

```text
pseudo_rejected_count_target = real event-level dedup reject count
pseudo reject dates sampled from eligible same-industry opportunity pool
matched by failure_decision_window / reject_delay_bucket distribution where applicable
```

Matched-delay metrics：

```text
D_pseudo = matched_delay_pseudo_reject_effective_date
Q_pseudo = matched_delay_pseudo_reject_effective_price_reference

matched_delay_drawdown_from_pseudo_reject_60d =
  min(low over [D_pseudo, trading_day_offset(D_pseudo, 59)]) / Q_pseudo - 1

matched_delay_failure_positive_primary =
  launch_winner_50h120_from_launch_reference = false
  and matched_delay_drawdown_from_pseudo_reject_60d <= -0.12

matched_delay_failure_precision =
  count(matched-delay pseudo reject rows where matched_delay_failure_positive_primary = true)
  / count(matched-delay pseudo reject rows)
```

必须输出：

```text
p0_9_industry_failure_matched_delay_baseline.csv
```

`p0_9_industry_failure_matched_delay_baseline.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
stable_candidate_id
predeclared_bucket_id
matched_delay_repeat_id
matched_delay_mode
matched_delay_unit
matched_delay_random_seed
real_reject_event_count
pseudo_reject_event_count
exact_real_reject_count_pass
matched_delay_failure_precision
matched_delay_nonwinner_precision
matched_delay_drawdown_from_pseudo_reject_60d_median
matched_delay_winner_false_reject_from_launch_rate
matched_delay_big_winner_false_reject_from_launch_rate
```

### 14.1 Failure multi-window / weight audits

Failure training may use multiple `failure_decision_window` rows, but OOF / P1 metrics must be event-level dedup and window weighting must not let one launch event dominate.

`p0_9_industry_failure_multi_window_dedup_audit.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
stable_candidate_id
failure_event_dedup_candidate_id
launch_stratum_event_id
raw_window_hit_count
kept_failure_decision_window
kept_failure_decision_effective_date
duplicate_window_hit_count
dedup_policy
dedup_pass
```

`p0_9_failure_window_weight_normalization_audit.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
launch_stratum_event_id
failure_decision_window
raw_sample_weight
window_normalized_sample_weight
sum_window_weight_per_launch_event
window_weight_normalization_pass
```

P1 gate 前置要求：

```text
failure_multi_window_dedup_pass = true
failure_window_weight_normalization_pass = true
```

---

## 15. P1 gate：industry launch candidate

Launch P1 gate 必须全部满足：

```text
validation_scope = oof_core_2020_2023
fold_2024_used_for_p1_promotion = false
observed_reference_label_measurement_rows_used_for_p1_promotion = false
walk_forward_purge_rule_pass = true
inner_validation_purge_rule_pass = true
feature_asof_leakage_violation_count = 0
early_stopping_audit_pass = true
bucket_selection_audit_pass = true
threshold_learned_on_validation = false

industry_launch_trainability_pass = true
positive_validation_fold_count >= thresholds.min_positive_validation_folds
validation_distinct_years >= thresholds.min_validation_years
validation_event_count >= thresholds.min_launch_validation_event_count
validation_positive_count >= thresholds.min_launch_validation_positive_count
validation_distinct_instruments >= thresholds.min_validation_distinct_instruments
validation_distinct_instrument_years >= thresholds.min_validation_distinct_instrument_years

launch_winner_rate >= industry_local_all_launch_baseline_rate * thresholds.min_launch_lift_vs_industry_all
launch_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_launch_lift_vs_candidate_scope_weighted_baseline
launch_lift_vs_industry_local_same_family_baseline >= thresholds.min_launch_lift_vs_same_family
winner_episode_coverage >= thresholds.min_launch_winner_episode_coverage
false_positive_rate <= candidate_scope_weighted_baseline_false_positive_rate + thresholds.max_false_positive_worsening
median_future_max_drawdown_60d >= candidate_scope_weighted_baseline_median_drawdown_60d - thresholds.max_drawdown_worsening

candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share <= thresholds.max_candidate_baseline_sparse_cell_weight_share

top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
oof_regime_hhi <= thresholds.max_regime_hhi
oof_top1_regime_contribution <= thresholds.max_top1_regime_contribution

null_full_retrain_executed = true
completed_null_repeats >= thresholds.min_lgbm_null_promotion_repeats
candidate_lift_exceeds_null_p95 = true
empirical_p_value <= thresholds.max_lgbm_null_empirical_p
fdr_q_value_across_fixed_industries <= thresholds.max_lgbm_null_fdr_q
```

Launch positive validation fold：

```text
fold_event_count >= thresholds.min_launch_fold_event_count
fold_positive_count >= thresholds.min_launch_fold_positive_count
fold_lift_vs_industry_all >= thresholds.min_launch_fold_lift_vs_industry_all
fold_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_launch_fold_lift_vs_candidate_scope_weighted_baseline
fold_winner_coverage >= thresholds.min_launch_fold_winner_coverage
fold_false_positive_rate <= fold_candidate_scope_baseline_false_positive_rate + thresholds.max_fold_false_positive_worsening
fold_median_drawdown_not_worse_than_baseline = true
fold_trainability_pass = true
```

---

## 16. P1 gate：industry failure candidate

Failure P1 gate 必须全部满足：

```text
validation_scope = oof_core_2020_2023
fold_2024_used_for_p1_promotion = false
observed_reference_label_measurement_rows_used_for_p1_promotion = false
walk_forward_purge_rule_pass = true
inner_validation_purge_rule_pass = true
feature_asof_leakage_violation_count = 0
early_stopping_audit_pass = true
bucket_selection_audit_pass = true
threshold_learned_on_validation = false
failure_multi_window_dedup_pass = true
failure_window_weight_normalization_pass = true

industry_failure_trainability_pass = true
positive_validation_fold_count >= thresholds.min_positive_validation_folds
validation_distinct_years >= thresholds.min_validation_years
validation_reject_event_count_event_dedup >= thresholds.min_failure_validation_reject_event_count
validation_failure_positive_count >= thresholds.min_failure_validation_positive_count
validation_distinct_instruments >= thresholds.min_validation_distinct_instruments
validation_distinct_instrument_years >= thresholds.min_validation_distinct_instrument_years

failure_precision >= industry_local_failure_baseline_precision * thresholds.min_failure_precision_lift_vs_industry_baseline
nonwinner_precision_lift >= thresholds.min_nonwinner_precision_lift
failure_precision_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_failure_precision_lift_vs_candidate_scope_weighted_baseline
failure_precision_lift_vs_matched_delay >= thresholds.min_failure_precision_lift_vs_matched_delay

drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_matched_delay
filter_before_12pct_drawdown_rate >= thresholds.min_filter_before_12pct_drawdown_rate
same_day_12pct_drawdown_ambiguous_share <= thresholds.max_same_day_12pct_drawdown_ambiguous_share

winner_false_reject_from_launch_rate <= thresholds.max_winner_false_reject_from_launch_rate
big_winner_false_reject_from_launch_rate <= thresholds.max_big_winner_false_reject_from_launch_rate
post_50_pre_100_big_winner_false_reject_rate <= thresholds.max_post_50_pre_100_big_winner_false_reject_rate
pending_winner_coverage_loss_from_launch <= thresholds.max_pending_winner_coverage_loss_from_launch
total_winner_coverage_loss_from_launch <= thresholds.max_total_winner_coverage_loss_from_launch

decision_reference_secondary_veto_pass = true

candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
candidate_baseline_sparse_cell_weight_share <= thresholds.max_candidate_baseline_sparse_cell_weight_share

top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
oof_regime_hhi <= thresholds.max_regime_hhi
oof_top1_regime_contribution <= thresholds.max_top1_regime_contribution

null_full_retrain_executed = true
completed_null_repeats >= thresholds.min_lgbm_null_promotion_repeats
candidate_lift_exceeds_null_p95 = true
empirical_p_value <= thresholds.max_lgbm_null_empirical_p
fdr_q_value_across_fixed_industries <= thresholds.max_lgbm_null_fdr_q
```

Failure positive validation fold：

```text
fold_reject_event_count_event_dedup >= thresholds.min_failure_fold_reject_event_count
fold_failure_positive_count >= thresholds.min_failure_fold_positive_count
fold_failure_precision_lift_vs_industry_baseline >= thresholds.min_failure_fold_precision_lift_vs_industry_baseline
fold_failure_precision_lift_vs_matched_delay >= thresholds.min_failure_fold_precision_lift_vs_matched_delay
fold_winner_false_reject_from_launch_rate <= thresholds.max_fold_winner_false_reject_from_launch_rate
fold_big_winner_false_reject_from_launch_rate <= thresholds.max_fold_big_winner_false_reject_from_launch_rate
fold_pending_winner_coverage_loss_from_launch <= thresholds.max_fold_pending_winner_coverage_loss_from_launch
fold_drawdown_avoided_vs_matched_delay >= thresholds.min_fold_drawdown_avoided_vs_matched_delay
fold_trainability_pass = true
```

---

## 17. Required outputs

第 17 节是唯一 required artifact authority。未列入本节的 artifact 默认为 optional。

### 17.1 Manifest / dictionaries / config

```text
p0_9_run_manifest.json
p0_9_config_resolved.yaml
p0_9_target_industry_mapping_audit.csv
p0_9_industry_feasibility_count_audit.csv
p0_9_feature_dictionary.csv
p0_9_label_dictionary.csv
p0_9_model_feature_set_manifest.csv
```

### 17.2 Leakage / observed reference / purge

```text
p0_9_feature_asof_leakage_audit.csv
p0_9_observed_reference_overlap_audit.csv
p0_9_observed_reference_row_audit.parquet
p0_9_walk_forward_purge_audit.csv
p0_9_inner_validation_purge_audit.csv
p0_9_label_horizon_truncation_audit.csv
```

### 17.3 Cache parquet

```text
p0_9_industry_launch_sample_panel.parquet
p0_9_industry_failure_sample_panel.parquet
p0_9_industry_launch_oof_prediction_panel.parquet
p0_9_industry_failure_oof_prediction_panel.parquet
p0_9_industry_failure_event_dedup_panel.parquet
```

### 17.4 Baseline / trainability / weights

```text
p0_9_industry_local_baseline.csv
p0_9_industry_failure_opportunity_baseline.csv
p0_9_industry_candidate_scope_weighted_baseline.csv
p0_9_industry_baseline_sparsity_audit.csv
p0_9_fold_local_p0_8_baseline_audit.csv
p0_9_industry_lgbm_fold_trainability_audit.csv
p0_9_sample_weight_group_cap_audit.csv
p0_9_industry_sample_sufficiency_audit.csv
```

### 17.5 LGBM / null / matched-delay

```text
p0_9_lgbm_null_runtime_plan.csv
p0_9_lgbm_null_permutation_baseline.csv
p0_9_candidate_level_null_aggregation.csv
p0_9_industry_failure_matched_delay_baseline.csv
p0_9_industry_failure_multi_window_dedup_audit.csv
p0_9_failure_window_weight_normalization_audit.csv
p0_9_industry_lgbm_early_stopping_audit.csv
p0_9_industry_lgbm_score_bucket_selection_audit.csv
```

`p0_9_industry_lgbm_early_stopping_audit.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
early_stopping_rounds
early_stopping_uses_outer_validation_fold
early_stopping_uses_inner_train_split_only
inner_validation_purge_rule_pass
best_iteration_source
early_stopping_audit_pass
```

`p0_9_industry_lgbm_score_bucket_selection_audit.csv` 字段至少包括：

```text
target_industry
model_task
fold_id
predeclared_bucket_id
train_score_threshold
validation_score_threshold_used
threshold_policy
threshold_source
threshold_learned_on_validation
bucket_selection_audit_pass
```

P1 gate 前置要求：

```text
early_stopping_audit_pass = true
bucket_selection_audit_pass = true
threshold_learned_on_validation = false
```

### 17.6 Leaderboards / OOF / robustness

```text
p0_9_industry_launch_lgbm_bucket_leaderboard.csv
p0_9_industry_failure_lgbm_bucket_leaderboard.csv
p0_9_industry_p1_candidate_summary.csv
p0_9_industry_oof_core_2020_2023_aggregation.csv
p0_9_industry_oof_with_2024_robustness_audit.csv
p0_9_industry_model_robustness_audit.csv
```

`p0_9_industry_p1_candidate_summary.csv` 字段至少包括：

```text
target_industry
model_task
stable_candidate_id
predeclared_bucket_id
candidate_for_industry_p1_refine
recommendation
failed_gate_reasons
validation_scope
launch_lift_vs_candidate_scope_weighted_baseline
failure_precision_lift_vs_candidate_scope_weighted_baseline
fdr_q_value_across_fixed_industries
decision_reference_secondary_veto_pass
diagnostic_only_due_to_insufficient_sample
required_next_action
```

`p0_9_industry_model_robustness_audit.csv` 字段至少包括：

```text
target_industry
model_task
stable_candidate_id
fold_2024_used_for_p1_promotion
fold_2024_robustness_metric
year_2021_stress_pass
year_2022_stress_pass
regime_concentration_pass
instrument_concentration_pass
robustness_audit_pass
```

### 17.7 Interpretation

```text
p0_9_industry_lgbm_feature_importance.csv
p0_9_industry_lgbm_shap_summary.csv
p0_9_industry_lgbm_leaf_rule_diagnostic.csv
p0_9_industry_model_card.csv
p0_9_industry_2021_2022_stress_review.csv
p0_9_industry_fold_failure_case_review.csv
```

### 17.8 Report

```text
explore9_p0_9_industry_lgbm_report.md
```

Report 必须包含：

```text
1. Summary recommendation
2. Fixed target industry list and PIT mapping audit
3. Feasibility and sample sufficiency by industry
4. Purge / feature-asof / observed-reference audit
5. Launch LGBM per-industry results
6. Failure LGBM per-industry results
7. Industry-local baseline and sparse-cell fallback audit
8. Candidate-level null and cross-industry FDR audit
9. Failure matched-delay, false-reject, and post-50/pre-100 big-winner audit
10. Instrument / instrument-year / regime concentration
11. 2021/2022 stress review
12. Feature importance / SHAP / leaf diagnostics
13. Industry candidate decision table
14. What can and cannot be promoted to industry P1 refine
15. Required next action
```

Report recommendation 只能取：

```text
continue_p0_9_industry_lgbm_discovery
proceed_to_industry_p1_refine
industry_model_predictive_but_not_actionable
industry_failure_direction_valid_but_false_reject_too_high
industry_launch_direction_valid_but_sample_or_year_unstable
industry_diagnostic_only_due_to_insufficient_sample
stop_due_to_no_stable_industry_lgbm_structure
```

Report 不得输出：

```text
proceed_to_explore10_backtest
ready_for_backtest
clean_oos_rule_validated
cross_industry_rule_validated
freeze_strategy
```

---

## 18. Config sketch

```yaml
phase: p0_9_industry_lgbm

fixed_target_industries:
  - 国防军工
  - 基础化工
  - 汽车
  - 交通运输
  - 机械设备
  - 建筑材料
  - 传媒
  - 电力设备
  - 电子

folds:
  fold_2020: {train_start: 2017-01-01, train_end: 2019-12-31, validation_year: 2020, validation_fold_role: p1_promotion_eligible}
  fold_2021: {train_start: 2017-01-01, train_end: 2020-12-31, validation_year: 2021, validation_fold_role: p1_promotion_eligible}
  fold_2022: {train_start: 2017-01-01, train_end: 2021-12-31, validation_year: 2022, validation_fold_role: p1_promotion_eligible}
  fold_2023: {train_start: 2017-01-01, train_end: 2022-12-31, validation_year: 2023, validation_fold_role: p1_promotion_eligible}
  fold_2024: {train_start: 2017-01-01, train_end: 2023-12-31, validation_year: 2024, validation_fold_role: robustness_audit_only}

purge:
  require_train_label_window_end_before_validation_start: true
  require_inner_train_label_window_end_before_inner_validation_start: true
  max_label_horizon_days_used_for_purge: task_max_required_label_horizon

feature_asof:
  close_derived_signal_feature_asof_date: signal_date
  event_effective_date_ohlc_features_allowed: false

model_tasks:
  launch:
    enabled: true
    model_name: industry_launch_winner_score_lgbm
    primary_label: launch_winner_50h120
    predeclared_buckets: [launch_top_10pct_by_train_threshold, launch_top_5pct_by_train_threshold, launch_top_2pct_by_train_threshold]
  failure:
    enabled: true
    model_name: industry_failure_reject_score_lgbm
    primary_label: failure_reject_positive_primary
    predeclared_buckets: [failure_top_risk_10pct_by_train_threshold, failure_top_risk_5pct_by_train_threshold, failure_top_risk_2pct_by_train_threshold]

lgbm:
  objective: binary
  metric: auc
  learning_rate: 0.03
  num_leaves: 31
  max_depth: 5
  min_data_in_leaf: 100
  feature_fraction: 0.8
  bagging_fraction: 0.8
  bagging_freq: 1
  lambda_l1: 0.0
  lambda_l2: 1.0
  early_stopping_rounds: 100
  early_stopping_uses_outer_validation_fold: false
  early_stopping_uses_inner_train_split_only: true
  random_seed: 20260505

null_full_retrain:
  enabled: true
  screening_repeats: 20
  promotion_repeats: 100
  n_jobs: 24
  primary_null_mode: train_label_permutation_full_retrain_then_real_validation_eval
  candidate_level_aggregation: true
  permutation_scope: target_industry_train_fold_model_task

matched_delay:
  enabled_for_failure: true
  mode: exact_real_reject_count
  random_seed: 20260505
  n_repeats: 100
  n_jobs: 24

baseline:
  min_baseline_cell_event_count: 50
  min_baseline_cell_positive_count: 5
  fallback_hierarchy_pre_registered: true

thresholds:
  min_positive_validation_folds: 3
  min_validation_years: 3
  min_validation_distinct_instruments: 8
  min_validation_distinct_instrument_years: 8
  min_core_trainable_folds_for_industry_p1: 4
  min_baseline_cell_event_count: 50
  min_baseline_cell_positive_count: 5

  min_industry_lgbm_train_event_count: 500
  min_industry_lgbm_train_positive_count: 30
  min_industry_lgbm_train_negative_count: 100
  min_industry_lgbm_train_distinct_instruments: 20
  min_industry_lgbm_train_distinct_instrument_years: 40
  min_industry_lgbm_inner_validation_event_count: 100
  min_industry_lgbm_inner_validation_positive_count: 8
  min_industry_lgbm_outer_validation_event_count: 80
  min_industry_lgbm_outer_validation_positive_count: 5
  min_industry_lgbm_outer_validation_distinct_instruments: 8
  min_industry_lgbm_outer_validation_distinct_instrument_years: 8

  min_launch_validation_event_count: 200
  min_launch_validation_positive_count: 20
  min_launch_lift_vs_industry_all: 1.25
  min_launch_lift_vs_candidate_scope_weighted_baseline: 1.10
  min_launch_lift_vs_same_family: 1.05
  min_launch_winner_episode_coverage: 0.05
  max_false_positive_worsening: 0.03
  max_drawdown_worsening: 0.02
  min_launch_fold_event_count: 50
  min_launch_fold_positive_count: 5
  min_launch_fold_lift_vs_industry_all: 1.00
  min_launch_fold_lift_vs_candidate_scope_weighted_baseline: 1.00
  min_launch_fold_winner_coverage: 0.01
  max_fold_false_positive_worsening: 0.05

  min_failure_validation_reject_event_count: 100
  min_failure_validation_positive_count: 30
  min_failure_precision_lift_vs_industry_baseline: 1.10
  min_nonwinner_precision_lift: 1.05
  min_failure_precision_lift_vs_candidate_scope_weighted_baseline: 1.05
  min_failure_precision_lift_vs_matched_delay: 1.03
  min_drawdown_avoided_vs_matched_delay: 0.01
  min_filter_before_12pct_drawdown_rate: 0.50
  max_same_day_12pct_drawdown_ambiguous_share: 0.20
  max_winner_false_reject_from_launch_rate: 0.20
  max_big_winner_false_reject_from_launch_rate: 0.15
  max_post_50_pre_100_big_winner_false_reject_rate: 0.20
  max_decision_reference_residual_50h120_rate: 0.25
  max_decision_reference_residual_100h240_rate: 0.15
  max_pending_winner_coverage_loss_from_launch: 0.35
  max_total_winner_coverage_loss_from_launch: 0.35
  min_failure_fold_reject_event_count: 30
  min_failure_fold_positive_count: 10
  min_failure_fold_precision_lift_vs_industry_baseline: 1.00
  min_failure_fold_precision_lift_vs_matched_delay: 1.00
  max_fold_winner_false_reject_from_launch_rate: 0.25
  max_fold_big_winner_false_reject_from_launch_rate: 0.25
  max_fold_pending_winner_coverage_loss_from_launch: 0.45
  min_fold_drawdown_avoided_vs_matched_delay: 0.00

  max_candidate_baseline_missing_row_rate: 0.05
  max_candidate_baseline_missing_weight_share: 0.05
  max_candidate_baseline_sparse_cell_weight_share: 0.20
  max_top1_instrument_contribution: 0.10
  max_top5_instrument_contribution: 0.35
  max_top_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.08
  max_regime_hhi: 0.55
  max_top1_regime_contribution: 0.70

  min_lgbm_null_screening_repeats: 20
  min_lgbm_null_promotion_repeats: 100
  max_lgbm_null_empirical_p: 0.10
  max_lgbm_null_fdr_q: 0.20
```

任何 threshold / feature allowlist / bucket policy / trainability gate / P1 gate 若在查看 validation、robustness 或 report 指标后调整，则：

```text
threshold_adjusted_after_validation = true
candidate_for_industry_p1_refine = false
requires_fresh_preregistered_rerun = true
```

---

## 19. Commands

建议新增命令：

```bash
uv run python Explore9/scripts/run_explore9.py profile-p0-9 --config Explore9/configs/industry_lgbm_p0_9.yaml
uv run python Explore9/scripts/run_explore9.py report-p0-9 --config Explore9/configs/industry_lgbm_p0_9.yaml
```

命令不得生成 Explore10 backtest，不得读取 Explore3-Explore8 trade results，不得输出可交易策略配置。

---

## 20. Implementation preflight checklist

实现前必须逐项通过：

```text
[ ] 固定 9 个行业全部写入 config / manifest。
[ ] 每个行业输出 feasibility count table；样本不足行业标记 diagnostic-only，不得静默删除。
[ ] industry 本身、industry_code、target_industry_name 被排除出 LGBM feature。
[ ] close-derived feature_asof_date = signal_date，event_effective_date 当天 OHLCV 不进 feature。
[ ] walk-forward purge 使用 train_label_window_end_date < validation_start_date。
[ ] inner validation purge 使用 inner_train_label_window_end_date < inner_validation_start_date。
[ ] fold_2024 只进入 robustness audit，不进入 P1 promotion。
[ ] observed-reference decision / feature overlap 不进入 train / validation / P1。
[ ] observed-reference label measurement overlap 不进入 P1 promotion。
[ ] label window 从 effective date 当天开始，包含 effective date high / low。
[ ] launch / failure label dictionary 覆盖所有训练、验证、P1 gate 字段。
[ ] failure already-achieved 50h120 target rows 不进入 primary failure training/eval，但 post-50/pre-100 行保留在 100h240 false-reject audit。
[ ] failure false reject P1 主口径使用 from-launch target。
[ ] failure precision / lift 使用 event-level dedup 后的 failure_primary_eval_row 分母。
[ ] filter_before_12pct_drawdown P1 主口径使用严格 D < drawdown_date，同日 ambiguous 只做 sensitivity。
[ ] drawdown_avoided_vs_matched_delay 使用真实 reject adverse drawdown 减 matched-delay adverse drawdown。
[ ] industry-local baseline 和 failure opportunity baseline 已定义。
[ ] baseline artifact schema 覆盖 P1 gate 所需的 candidate-scope weighted baseline 字段。
[ ] baseline sparse cell 使用预注册 fallback hierarchy。
[ ] candidate-scope weighted baseline missing row / weight / sparse share 已审计。
[ ] LGBM outer validation 不用于 early stopping / threshold / bucket / feature selection。
[ ] early stopping audit 和 score bucket selection audit 通过。
[ ] 每个行业 task fold 通过 trainability gate；aggregate trainability pass 已定义。
[ ] sample weight 做 group-level instrument-year cap。
[ ] failure 多窗口主指标做 event-level dedup，window weight normalization audit 通过。
[ ] null full-retrain 使用 candidate-level OOF aggregation，不平均 per-fold p-value。
[ ] null primary metric 已按 model_task 预注册，不使用事后挑选指标。
[ ] P1 promotion 使用 across fixed industries 的 FDR q-value，不使用 within-industry q-value。
[ ] promotion null repeats 达到阈值，否则不得 candidate_for_industry_p1_refine。
[ ] matched-delay baseline 使用 exact_real_reject_count。
[ ] raw score 不跨行业排序。
[ ] Required outputs 第 17 节列出的 artifact 全部生成。
[ ] 报告不输出 Explore10 / clean OOS / frozen strategy。
```

---

## 21. 最终阶段结论口径

若没有行业通过：

```text
recommendation = continue_p0_9_industry_lgbm_discovery
candidate_for_industry_p1_refine_count = 0
```

若模型有预测力但未通过 P1 gate：

```text
recommendation = industry_model_predictive_but_not_actionable
candidate_for_industry_p1_refine = false
required_next_action = tighten_or_stop_before_industry_p1_refine
```

若行业因 mapping 或样本不足不可推广：

```text
recommendation = industry_diagnostic_only_due_to_insufficient_sample
candidate_for_industry_p1_refine = false
industry remains in report
```

若某行业 launch model 通过：

```text
recommendation = proceed_to_industry_p1_refine
industry = <target_industry>
model_task = industry_launch_winner_score_lgbm
candidate_scope = industry_specific_only
cross_industry_claim_allowed = false
```

若某行业 failure model 通过：

```text
recommendation = proceed_to_industry_p1_refine
industry = <target_industry>
model_task = industry_failure_reject_score_lgbm
candidate_scope = industry_specific_only
cross_industry_claim_allowed = false
```

即使某行业候选通过，也必须明确：

```text
P0.9 is not clean OOS proof.
P0.9 does not authorize Explore10.
P0.9 candidate must be frozen and re-tested in industry P1 refine.
```
