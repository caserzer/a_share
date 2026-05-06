# Explore9 扩展需求 6：P0.9A 行业专用 LGBM Trainability Probe

> 文件名建议：`requirement_expand_6.md`
> 同步短名：`requirement_p0_9a.md`
> 阶段：`P0.9A`
> 标题：电子 / 汽车 / 电力设备行业专用 LGBM 训练可行性探针
> 状态：self-checked implementation-ready requirement
> 生成日期：2026-05-06

---

## 0. 一句话结论

P0.9A 不是 P1，也不是 P0.9 的“放宽阈值重跑”。

P0.9A 只回答一个更窄的问题：

```text
在严格保留 PIT、feature-asof、observed-reference、purged walk-forward 等反泄漏纪律的前提下，
电子、汽车、电力设备这三个行业的行业专用 LGBM，
在什么预注册训练合同下可以合法训练？
```

P0.9A 不回答：

```text
模型是否已经有效；
模型是否可以进 P1；
哪个 score bucket 可以交易；
是否可以进入 Explore10；
是否可以 freeze strategy。
```

本版自我审查后的核心修订：

```text
1. 合同推荐只能基于 trainability，不得基于 outer validation performance。
2. P0.9B 推荐合同使用 deterministic priority，不能事后挑 AUC / logloss 最好者。
3. feature set 不得根据 validation 指标增删。
4. fixed-round alternative 只能 diagnostic，不得参与 P0.9B 合同推荐。
5. model fit success 必须独立于 count gate 审计。
6. 第 17 节是唯一 required artifact authority。
7. 补齐 label-window end-date、failure post-target exclusion、failure window weight normalization 与 model non-degenerate sanity。
8. 补齐 P0.9 结果后验选择三个行业的 selection lineage。
9. 补齐 P0.9B 必须承接 industry/task/contract selection family 的 null / multiplicity 边界。
10. 补齐 T0 strict reproduction 与 P0.9 原始 trainability 输出的 reconciliation。
11. 收紧 T3 grouped temporal inner validation 为完全机械 split。
12. 收紧 fallback provider 只能用于 PIT provider 缺口下的 OHLCV / money 读取，不得替代 PIT membership。
```

---

## 1. 背景

P0.9 的固定 9 个行业全部完成 PIT exact mapping，但 `industry/task/fold` trainability 检查共 90 行，trainable 组合为 0。因此 P0.9 没有实际产生 LGBM bucket、OOF aggregation、candidate-level null、matched-delay candidate audit 或 feature importance 结果。

P0.9 的负向结论不是：

```text
行业专用 LGBM 没有预测力。
```

而是：

```text
当前 P0.9 合同下，行业专用 LGBM 没有合法进入训练阶段。
```

P0.9 报告显示，真正阻塞来自：

```text
strict purged expanding walk-forward
+ industry-local split
+ inner validation gate
+ industry-local distinct instrument / instrument-year gate
```

叠加后，行业内 fold 的训练样本、instrument 覆盖或 inner validation 样本不足。

因此 P0.9A 只做 trainability probe：先回答哪些行业、任务、split 合同可以合法训练，再决定是否另开 P0.9B 行业专用 LGBM discovery rerun。

---

## 2. 阶段定位

P0.9A 是 Explore9 行业专用 LGBM 路线的 trainability probe。

P0.9A 的定位：

```text
trainability feasibility study
pre-registered split contract comparison
anti-leakage implementation audit
industry-specific model training contract selection for future P0.9B
```

P0.9A 不是：

```text
P1 refine
P1 promotion
clean OOS proof
strategy backtest
entry rule discovery
score bucket candidate selection
industry trading rule freeze
```

P0.9A 允许：

```text
1. 对电子、汽车、电力设备分别构造行业内 launch / failure 样本。
2. 对预注册 trainability contract 进行可训练性测试。
3. 训练 LGBM 仅用于确认训练流程是否能合法跑通。
4. 输出 fold-level trainability、sample sufficiency、purge impact、inner validation impact。
5. 输出模型 sanity diagnostics，例如 AUC / logloss / calibration / feature importance。
6. 记录哪些 industry-task-contract 可以进入 P0.9B discovery rerun。
```

P0.9A 禁止：

```text
1. 输出 candidate_for_industry_p1_refine = true。
2. 输出 proceed_to_explore10_backtest。
3. 根据 outer validation 表现选择阈值、bucket、feature、best_iteration 或 trainability gate。
4. 把 2024 robustness 或 observed-reference label measurement 用于 P0.9B/P1 promotion proof。
5. 把 P0.9 本轮失败后的手工阈值调整当作 P1 证据。
6. 根据 P0.9A validation 指标挑选“最佳行业模型”并宣称有效。
```

---

## 3. 固定目标行业与模型任务

P0.9A 只测试以下三个行业：

```text
target_industries:
  - 电子
  - 汽车
  - 电力设备
```

选择理由：

```text
电子：P0.9 中 raw coverage 最好，failure opportunity 最大，failure baseline precision 最高。
汽车：P0.9 中 launch baseline winner rate 最高。
电力设备：P0.9 中 launch baseline winner rate 较高，raw coverage 也较好。
```

### 3.0 Selection lineage 与后验选择边界

上述三个行业不是事前从全市场独立指定，而是基于 P0.9 固定 9 行业诊断结果后验选出的 trainability probe 子集。因此必须显式标记：

```text
industry_selection_source = p0_9_fixed_9_industry_result_review
industry_selection_scope = [电子, 汽车, 电力设备] selected from fixed_9_industries
industry_selection_is_post_p0_9_diagnostic = true
p0_9a_industry_subset_is_clean_oos = false
```

P0.9A 可以使用该后验子集做 trainability probe，但不得把这三个行业在 P0.9A / P0.9B 中的同一 2020-2023 core evidence 解释为 clean independent discovery proof。

若 P0.9B 后续使用 P0.9A 推荐出的行业 / task / contract 继续做 discovery，则 P0.9B 必须满足二选一：

```text
1. null / multiplicity family 覆盖从 P0.9 固定 9 行业到 P0.9A 三行业、再到 P0.9B industry-task-contract 的完整选择路径；
2. 或把 P0.9B 明确标记为 post-selected hypothesis rerun，只能输出 hypothesis-generating 结论，不得输出 clean discovery proof。
```

Required artifact：

```text
p0_9a_selection_lineage_audit.csv
```

P0.9A 对每个目标行业测试两个 task：

```text
model_tasks:
  - industry_launch_winner_score_lgbm
  - industry_failure_reject_score_lgbm
```

### 3.1 `industry_launch_winner_score_lgbm`

样本单位：

```text
one row per target_industry + launch_stratum_event_id
```

目标：

```text
判断行业内 launch / stratum event 是否具备 winner discovery 训练可行性。
```

P0.9A 中只审计 trainability 和 sanity metrics，不生成可执行 entry score。

### 3.2 `industry_failure_reject_score_lgbm`

样本单位：

```text
one row per target_industry + launch_stratum_event_id + failure_decision_window
```

训练可以保留 3d / 5d / 10d 多窗口，但主审计必须同时输出 event-level dedup 后的 sample count。

目标：

```text
判断行业内 failure rejection risk model 是否具备训练可行性。
```

P0.9A 中只审计 trainability 和 sanity metrics，不生成 hard reject 规则。

---

## 4. 数据边界

P0.9A 继承 Explore9 / P0.9 的数据边界：

```text
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
industry_membership: Explore7/data/targets/pit_industry_membership.csv
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

硬约束：

```text
1. 每个 date + instrument 必须 PIT membership = true。
2. 行业归属必须按 date + instrument 的 PIT industry membership join。
3. 非目标行业不得进入 P0.9A train / validation / diagnostic denominator。
4. 2025-2026 不得用于特征选择、阈值选择、模型选择、trainability gate 选择或 candidate selection。
5. Explore3-Explore8 的历史交易结果不得作为 label / feature / selection input。
6. P0.9 输出只能作为 failure diagnosis / schema reference / audit reference，不得作为训练标签或 feature。
7. `fallback_provider_uri` 只能在 PIT provider 缺少基础 OHLCV / money 字段时用于读取价格与成交字段，不得替代 PIT industry membership、PIT universe membership、feature_asof_date 或 label source。
8. 所有成交额字段必须使用 `money`；不得用 `amount` 静默替代 `money`。
```

---

## 5. 时间切分与 fold role

P0.9A 继续使用 expanding walk-forward，但结论权限不同。

```text
fold_2020:
  validation_year = 2020
  role = core_trainability_probe

fold_2021:
  validation_year = 2021
  role = core_trainability_probe

fold_2022:
  validation_year = 2022
  role = core_trainability_probe

fold_2023:
  validation_year = 2023
  role = core_trainability_probe

fold_2024:
  validation_year = 2024
  role = robustness_trainability_audit_only
```

P0.9A 没有 P1 promotion，因此不存在 `p1_promotion_eligible = true` 的候选输出。但报告仍必须把 2020-2023 与 2024 分开：

```text
core_probe_oof = fold_2020 + fold_2021 + fold_2022 + fold_2023
robustness_audit = fold_2024
```

`fold_2024` 可以用于 trainability robustness audit，但不得作为未来 P0.9B 或 P1 的 promotion proof。


每个 fold 必须生成机械 fold calendar，不得只用年份隐式推断：

```text
fold_id
validation_year
validation_start_date
validation_end_date
train_raw_start_date = research_start
train_raw_end_date = trading_day_before(validation_start_date)
fold_role
is_core_probe_fold
is_robustness_audit_fold
observed_reference_label_measurement_allowed
```

Required artifact:

```text
p0_9a_fold_role_calendar.csv
```

---

## 6. Purged walk-forward 硬约束

P0.9A 不能为了训练成功而取消 purge。

主规则：

```text
train_label_window_end_date < validation_start_date
```

所有 train row 必须满足：

```text
label_window_end_date < validation_start_date
feature_asof_date <= signal_date
observed_reference_decision_overlap = false
observed_reference_feature_overlap = false
label_horizon_truncated = false
sample_has_required_features = true
```

对于 inner validation，如果使用 inner validation：

```text
inner_train_label_window_end_date < inner_validation_start_date
inner_validation_label_window_end_date < validation_start_date
outer_validation_used_for_inner_validation = false
```

Inner validation rows 必须先通过 outer train purge，只能从 `label_window_end_date < validation_start_date` 的 outer-purged train rows 中切出。Inner validation labels 可以用于 early stopping，但不得跨入 outer validation year；否则 best_iteration 会间接使用 outer validation period 的 forward outcome。

Required artifact:

```text
p0_9a_inner_validation_split_audit.csv
```

P0.9A 必须输出：

```text
p0_9a_walk_forward_purge_audit.csv
p0_9a_inner_validation_purge_audit.csv
```

审计字段至少包括：

```text
target_industry
model_task
fold_id
contract_id
raw_train_rows
rows_removed_by_label_window_purge
rows_removed_by_event_date_purge
rows_removed_by_feature_asof_purge
rows_removed_by_observed_reference_decision_overlap
rows_removed_by_observed_reference_feature_overlap
rows_removed_by_label_truncation
train_rows_after_purge
train_positive_after_purge
train_negative_after_purge
train_distinct_instruments_after_purge
train_distinct_instrument_years_after_purge
inner_validation_rows_before_outer_purge
inner_validation_rows_removed_by_outer_label_window_purge
inner_validation_label_window_end_max
validation_start_date
inner_validation_label_window_crosses_outer_validation_count
purge_pass
```

### 6.1 Label-window end-date 合同

P0.9A 的 purge 不能使用模糊的 `label_window_end_date`。实现必须为每个 row 明确输出：

```text
training_label_window_end_date
metric_label_window_end_date_max
label_window_end_date_used_for_train_purge
label_window_end_date_used_for_inner_purge
```

Launch task 默认训练标签为：

```text
launch_winner_50h120
launch_false_positive_primary
launch_future_max_drawdown_60d
```

因此 launch 训练 purge 使用：

```text
training_label_window_end_date = max(
  trading_day_offset(stratum_effective_date, 119),
  trading_day_offset(stratum_effective_date, 59)
)
```

Failure task 默认训练标签为：

```text
failure_reject_positive_primary
failure_drawdown_from_decision_60d
```

因此 failure 训练 purge 使用：

```text
training_label_window_end_date = trading_day_offset(failure_decision_effective_date, 59)
```

Failure false-reject / residual-upside 标签属于 sanity diagnostic，不得默认扩大 training purge；若未来某个合同把它们纳入训练 loss，必须在 config 中显式声明，并重新计算 `training_label_window_end_date`。

Required artifact：

```text
p0_9a_label_window_end_date_audit.csv
```

---

## 7. Feature-asof 与 feature set 合同

P0.9A 必须保留 P0.9 的 close-derived next-open 纪律。

定义：

```text
launch close-derived signal:
  signal_date = stratum_date
  event_effective_date = next_trading_day(stratum_date)
  feature_asof_date = signal_date

failure close-derived signal:
  signal_date = failure_signal_date
  event_effective_date = next_trading_day(failure_signal_date)
  feature_asof_date = signal_date
```

禁止：

```text
1. 使用 event_effective_date 当天 high / low / close / volume / money 作为预测特征。
2. 使用 next_open 作为预测特征。
3. 使用 observed-reference date 的任何 feature。
4. 使用未来 label、future return、future drawdown 作为特征。
5. 使用 P0.9 validation 结果、bucket rank、candidate rank、trainability pass/fail 作为特征。
```

允许：

```text
next_open on event_effective_date 可作为 execution price reference 或 execution audit，不能作为 predictive model feature。
```

### 7.1 Feature set contract

P0.9A 不做 feature selection。所有模型只能使用预注册 feature allowlist。

合法特征来源：

```text
1. P0.9 / P0.8 已定义的 PIT observable primitive features。
2. P0.7 / P0.8 / P0.9 面板中的 T 日可观察字段。
3. 行业内相对排名、行业宽度、market regime 等 feature，只要 feature_asof_date <= signal_date。
```

缺失处理：

```text
feature availability threshold 和 imputation policy 必须在 config 中预注册。
若某 feature 因 train-only availability audit 被排除，必须在所有 folds 和 contracts 中按同一 policy 处理。
不得根据 outer validation performance 增删 feature。
```

Required artifacts：

```text
p0_9a_feature_asof_leakage_audit.csv
p0_9a_feature_contract_audit.csv
p0_9a_feature_dictionary.csv
p0_9a_feature_availability_audit.csv
```

P0.9A 成功前置条件：

```text
feature_asof_leakage_violation_count = 0
```

---

## 8. Observed-reference 纪律

P0.9A 继续拆分三类 overlap：

```text
observed_reference_decision_overlap
observed_reference_feature_overlap
observed_reference_label_measurement_overlap
```

规则：

```text
observed_reference_decision_overlap = true 的 row 不得进入 train / validation / trainability pass。
observed_reference_feature_overlap = true 的 row 不得进入 train / validation / trainability pass。
observed_reference_label_measurement_overlap = true 的 row 只可进入 fold_2024 robustness audit，不得进入 core_probe_oof。
```

Required artifact：

```text
p0_9a_observed_reference_overlap_audit.csv
```

---

## 8.1 Train / evaluation eligibility 与 post-target failure 排除

P0.9A 必须显式输出 train/eval eligibility，不能只靠代码过滤。

### 8.1.1 Launch eligibility

```text
launch_model_train_eval_eligible =
  target_industry in [电子, 汽车, 电力设备]
  and PIT_membership = true
  and feature_asof_date = signal_date
  and event_effective_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_horizon_truncated = false
  and label_measurement_available = true
  and sample_has_required_features = true
```

如果 row 用于 `core_probe_oof`，还必须满足：

```text
observed_reference_label_measurement_overlap = false
```

### 8.1.2 Failure eligibility

```text
failure_model_train_eval_eligible =
  target_industry in [电子, 汽车, 电力设备]
  and PIT_membership = true
  and feature_asof_date = signal_date
  and failure_decision_effective_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_horizon_truncated = false
  and label_measurement_available = true
  and sample_has_required_features = true
  and target_50h120_not_reached_before_decision_effective_date = true
```

如果 `target_50h120_not_reached_before_decision_effective_date = false`，该 row 必须标记：

```text
post_target_risk_audit_only = true
exclude_from_failure_training_loss = true
exclude_from_failure_validation_metrics = true
exclude_from_failure_trainability_positive_negative_count = true
```

原因：

```text
failure reject 模型只研究“还没有达成 launch winner target 时是否应该识别失败风险”。
已经达成 50h120 target 的 row 不再是 reject opportunity，不能作为 negative example 训练。
```

Required artifacts：

```text
p0_9a_train_eval_eligibility_audit.csv
p0_9a_failure_post_target_exclusion_audit.csv
```

---

## 9. Label 体系

P0.9A 沿用 P0.9 label dictionary，但必须重新输出简化版 label audit。

### 9.1 Launch primary label

```text
launch_winner_50h120:
  reference_date = stratum_effective_date
  reference_price = stratum_effective_price_reference
  horizon = 120 trading days
  window = [stratum_effective_date, trading_day_offset(stratum_effective_date, 119)]
  positive = max(high over window) / reference_price - 1 >= 0.50
```

### 9.2 Launch risk labels

```text
launch_future_max_drawdown_60d:
  min(low over [E, trading_day_offset(E, 59)]) / reference_price - 1
  negative drawdown convention: -0.12 = 12% drawdown

launch_false_positive_primary:
  launch_winner_50h120 = false
  and launch_future_max_drawdown_60d <= -0.12
```

### 9.3 Failure primary label

定义：

```text
D = failure_decision_effective_date
P_D = failure_decision_effective_price_reference
L = launch_effective_date
P_L = launch_effective_price_reference
failure_label_window_60d = [D, trading_day_offset(D, 59)]
failure_label_window_120d = [D, trading_day_offset(D, 119)]
```

`failure_decision_effective_date` 当天 open 之后的 high / low / close 属于 forward path，不能被跳过。

```text
failure_drawdown_from_decision_60d =
  min(low over failure_label_window_60d) / P_D - 1

failure_reject_positive_primary =
  target_50h120_not_reached_before_decision_effective_date = true
  and failure_drawdown_from_decision_60d <= -0.12
```

Drawdown 使用负数口径：

```text
-0.12 = 12% drawdown
```

### 9.4 Target-not-reached fields

P0.9A 必须拆出两套 pending target 字段，不能用一个 ambiguous target 字段混合 50% 与 100%。

```text
target_50h120_not_reached_before_decision_effective_date =
  max(high from L to trading_day_before(D)) / P_L - 1 < 0.50

target_100h240_not_reached_before_decision_effective_date =
  max(high from L to trading_day_before(D)) / P_L - 1 < 1.00
```

若 `D = L`，则 before-decision path 为空，两个 pending 字段默认为 true。

`target_50h120_not_reached_before_decision_effective_date` 是 failure primary trainability / sanity 的主 pending 口径；`target_100h240_not_reached_before_decision_effective_date` 只用于 big-winner false-reject audit。

### 9.5 Failure false reject labels

两套 reference 必须同时输出：

```text
failure_false_reject_vs_launch_target_50h120 =
  filter/reject decision occurs while target_50h120_not_reached_before_decision_effective_date = true
  and launch_winner_50h120 = true

failure_false_reject_vs_decision_target_50h120 =
  max(high over failure_label_window_120d) / P_D - 1 >= 0.50
```

P0.9A 不做 P1 gate，但 sanity report 必须明确：

```text
from_launch_target 用于判断是否错杀原 launch winner。
from_decision_target 只用于 residual reward-risk diagnostic。
```

### 9.6 Failure post-target exclusion

Failure task 必须把已经达到 launch target 的样本排除出训练和 trainability 分母，避免模型把“目标已完成后的风险信号”当成拒绝机会。

```text
eligible_failure_training_row =
  target_50h120_not_reached_before_decision_effective_date = true
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_horizon_truncated = false
```

若：

```text
target_50h120_not_reached_before_decision_effective_date = false
```

则该 row 必须标记：

```text
post_target_audit_only = true
exclude_from_failure_training_loss = true
exclude_from_failure_trainability_count = true
exclude_from_failure_outer_validation_sanity_metric = true
```

Required artifacts：

```text
p0_9a_label_dictionary.csv
p0_9a_label_horizon_truncation_audit.csv
p0_9a_label_window_definition_audit.csv
p0_9a_label_window_end_date_audit.csv
p0_9a_failure_post_target_exclusion_audit.csv
```

---

## 10. Trainability probe matrix

P0.9A 的核心是预注册训练合同矩阵。所有合同必须在 config 中固定，不能在查看 validation 指标后修改。

### 10.1 Contract T0: strict P0.9 reproduction control

目的：复现 P0.9 的严格合同，确认代码和样本口径一致。

```text
contract_id = T0_strict_p0_9_reproduction
inner_validation_mode = latest_train_year
lgbm_training_mode = early_stopping_inner_validation
instrument_gate_profile = strict_p0_9
count_profile = strict
```

预期：可能仍然失败。T0 是 control，不是主要希望通过的合同。

T0 必须与 P0.9 已生成的 strict trainability 输出做 reconciliation。对三个目标行业、两个 task、五个 fold，至少比较：

```text
target_industry
model_task
fold_id
p0_9_train_rows_after_purge
p0_9a_t0_train_rows_after_purge
p0_9_train_positive_after_purge
p0_9a_t0_train_positive_after_purge
p0_9_train_distinct_instruments_after_purge
p0_9a_t0_train_distinct_instruments_after_purge
p0_9_inner_validation_rows
p0_9a_t0_inner_validation_rows
p0_9_fail_reasons
p0_9a_t0_fail_reasons
reconciliation_pass
reconciliation_diff_reason
```

允许差异只包括：

```text
1. P0.9A 明确新增的 failure post-target exclusion；
2. P0.9A 明确修正的 label-window end-date 口径；
3. P0.9A 明确修正的 feature availability / missing-field audit。
```

任何其它差异必须标记：

```text
t0_reconciliation_unexplained_diff = true
eligible_for_p0_9b_discovery_rerun = false
```

Required artifact:

```text
p0_9a_t0_vs_p0_9_reconciliation_audit.csv
```

### 10.2 Contract T1: fixed rounds, no inner validation

目的：检验当前瓶颈是否主要来自 inner validation 过薄。

```text
contract_id = T1_fixed_rounds_no_inner_validation
inner_validation_mode = none
lgbm_training_mode = fixed_n_estimators
outer_validation_used_for_early_stopping = false
fixed_n_estimators_launch = 64
fixed_n_estimators_failure = 32
instrument_gate_profile = safe_relative
count_profile = safe_probe
```

T1 禁止 early stopping，也禁止用 outer validation 选择 best iteration。

T1 只能回答：

```text
在不需要 inner validation 的情况下，该 industry-task-fold 是否可以训练一个合法 LGBM。
```

### 10.3 Contract T2: pooled inner validation

目的：保留 inner validation，但避免最新单一年份过薄。

```text
contract_id = T2_pooled_inner_validation
inner_validation_mode = pooled_tail_train_years
inner_validation_tail_years = 2
lgbm_training_mode = early_stopping_inner_validation
outer_validation_used_for_early_stopping = false
instrument_gate_profile = safe_relative
count_profile = safe_probe
```

要求：

```text
1. inner validation 必须来自 outer train period 内。
2. inner validation 不得使用 outer validation year。
3. inner validation years = latest N train years before outer validation year。
4. inner validation rows must satisfy label_window_end_date < outer_validation_start_date。
5. inner train rows must satisfy label_window_end_date < inner_validation_start_date。
6. inner validation 不得使用 fold_2024 为 core folds 选择 best_iteration。
```

Required artifact:

```text
p0_9a_inner_validation_split_audit.csv
```

### 10.4 Contract T3: grouped temporal inner validation

目的：在 train years 内构造更稳定的 inner validation group，不随机切 stock-day row。

```text
contract_id = T3_grouped_temporal_inner_validation
inner_validation_mode = grouped_temporal_blocks
inner_group_unit = instrument_year
inner_validation_block_selection = latest_non_overlapping_blocks
inner_validation_block_count = 2
inner_validation_min_distinct_calendar_years = 2
inner_validation_block_tie_break = calendar_year_desc_then_instrument_asc
lgbm_training_mode = early_stopping_inner_validation
outer_validation_used_for_early_stopping = false
instrument_gate_profile = safe_relative
count_profile = safe_probe
```

T3 的 inner validation 必须完全机械生成：

```text
1. 先在 outer-purged train rows 中生成 instrument-year blocks。
2. 按 calendar_year descending、instrument ascending 排序。
3. 选择最近的 `inner_validation_block_count` 个 calendar years 中的全部 eligible instrument-year blocks。
4. 若最近两年 block 通过 label-window purge 后不足 `safe_probe` inner validation count gate，则状态为 `not_trainable_under_inner_validation`，不得回溯寻找表现更好的年份组合。
5. 同一个 launch_stratum_event_id 不得同时出现在 inner train 与 inner validation。
6. 对 failure 多窗口，同一个 launch_stratum_event_id 的不同 failure_decision_window 不得跨 inner train / inner validation。
```

禁止：

```text
random row split
same launch episode in inner train and inner validation
same instrument adjacent window leakage
inner_validation_label_window_end_date crossing outer validation_start_date
```

### 10.5 Contract T4: diagnostic minimal instrument gate

目的：判断特定行业是否只是因为 strict / safe instrument gate 而不可训练。

```text
contract_id = T4_diagnostic_minimal_instrument_gate
inner_validation_mode = none
lgbm_training_mode = fixed_n_estimators
instrument_gate_profile = diagnostic_minimal
count_profile = diagnostic_minimal
```

T4 只能生成 diagnostic-only 结果，不得成为 P0.9B 主合同。

---

## 11. Contract selection anti-selection rule

P0.9A 可以比较多个 trainability contract，但不得根据 outer validation performance 选择合同。

合法的 P0.9B 推荐合同只能来自以下 deterministic priority：

```text
contract_selection_priority_for_p0_9b:
  1. T0_strict_p0_9_reproduction
  2. T2_pooled_inner_validation
  3. T3_grouped_temporal_inner_validation
  4. T1_fixed_rounds_no_inner_validation
  5. T4_diagnostic_minimal_instrument_gate = never eligible
```

选择规则：

```text
for each target_industry + model_task:
  select the first contract_id in contract_selection_priority_for_p0_9b
  where core_folds_trainable_count >= configured_min_core_folds_trainable_for_p0_9b
  and model_fit_success_core_fold_count >= configured_min_core_folds_trainable_for_p0_9b
  and all anti-leakage audits pass
  and contract_id != T4_diagnostic_minimal_instrument_gate
```

禁止：

```text
1. 用 outer validation AUC / logloss / calibration / score bucket lift 选择合同。
2. 用 fold_2024 robustness 表现选择合同。
3. 在看过 P0.9A 指标后调整 contract priority。
4. 将 T4 diagnostic_minimal 的通过结果升级为 P0.9B 主合同。
```

如果多个合同都可训练，报告必须同时列出全部通过合同，但 `recommended_p0_9b_contract_id` 只能按 deterministic priority 给出。

### 11.1 Selection family carry-forward to P0.9B

P0.9A 的合同选择虽然不能使用 outer validation performance，但仍然使用了 label-derived trainability counts，例如 positive count、negative count、failure event-level positive count。因此 P0.9B 不得只把最终推荐的单一 contract 当成唯一已测试假设。

P0.9B 的 null / multiplicity 必须至少覆盖：

```text
fixed_9_industries_from_p0_9
selected_3_industries_for_p0_9a
2 model_tasks
all preregistered P0.9A contracts T0 / T1 / T2 / T3
T4 diagnostic_minimal as non-eligible diagnostic family member
deterministic contract selection rule
configured_min_core_folds_trainable_for_p0_9b
```

合法的 P0.9B 设计只能使用以下两种之一：

```text
full_selection_replay_null:
  每次 null permutation / bootstrap / label shuffle 都重新执行 P0.9A 的 industry-task-contract trainability selection，再评价 P0.9B candidate。

family_adjusted_post_selected_null:
  不重放 selection，但把所有 P0.9A 测试过的 industry-task-contract 纳入 family，且报告明确为 post-selected hypothesis。
```

若 P0.9B requirement 没有承接上述 selection family，则 P0.9A 即使找到可训练合同，也只能输出：

```text
eligible_for_p0_9b_discovery_rerun = false
not_eligible_reason = p0_9b_selection_family_not_specified
```

Required artifact：

```text
p0_9a_p0_9b_null_family_recommendation.csv
```

Required artifact：

```text
p0_9a_contract_selection_audit.csv
```

---

### 11.2 Post-validation adjustment rule

如果在查看任意以下结果后调整 threshold / gate / feature allowlist / fixed_n_estimators / contract priority：

```text
outer validation AUC / logloss
outer validation score bucket lift
feature importance
calibration
fold_2024 robustness
trainability pass/fail summary
```

则当前 run 必须标记：

```text
post_validation_adjustment_detected = true
eligible_for_p0_9b_discovery_rerun = false
requires_fresh_preregistered_rerun = true
```

允许做的事情：

```text
把调整建议写进报告的 next requirement suggestion。
```

不允许做的事情：

```text
在同一个 run 中调整后重新解释为合法 probe 结果。
```

Required artifact：

```text
p0_9a_post_validation_adjustment_audit.csv
```

---

## 12. Instrument gate 与 count profiles

P0.9A 不直接放宽 P1 gate，而是预注册不同 trainability gate profile。

### 12.1 Instrument gate profiles

`strict_p0_9`：

```text
min_train_distinct_instruments = 20
min_train_distinct_instrument_years = 40
min_outer_validation_distinct_instruments = 8
min_outer_validation_distinct_instrument_years = 8
```

`safe_relative`：

为避免 relative gate 使用未来 fold 信息，`safe_relative` 必须使用 fold-local、pre-label-outcome inventory，而不是全研究期整体行业股票数。

```text
fold_train_available_instruments =
  distinct instruments in target_industry
  with PIT membership and required feature availability
  in outer train period before validation_start
  before label-outcome filtering

fold_train_available_instrument_years =
  distinct instrument + calendar_year(event_effective_date)
  in outer train period before validation_start
  before label-outcome filtering

fold_outer_validation_available_instruments =
  distinct instruments in target_industry
  with PIT membership and required feature availability
  in validation_year
  before label-outcome filtering

fold_outer_validation_available_instrument_years =
  distinct instrument + validation_year
  in validation_year
  before label-outcome filtering

min_train_distinct_instruments = max(8, ceil(0.50 * fold_train_available_instruments))
min_train_distinct_instrument_years = max(25, ceil(0.45 * fold_train_available_instrument_years))
min_outer_validation_distinct_instruments = max(5, ceil(0.25 * fold_outer_validation_available_instruments))
min_outer_validation_distinct_instrument_years = max(5, ceil(0.20 * fold_outer_validation_available_instrument_years))

cap:
  min_train_distinct_instruments <= 18
  min_train_distinct_instrument_years <= 50
```

禁止使用以下信息来计算 relative gate：

```text
winner label
failure label
future return / drawdown
outer validation score
fold_2024 robustness score
P0.9A model metric
```

Required artifact:

```text
p0_9a_fold_inventory_audit.csv
```

`diagnostic_minimal`，只用于 T4：

```text
min_train_distinct_instruments = max(6, ceil(0.35 * fold_train_available_instruments))
min_train_distinct_instrument_years = max(15, ceil(0.30 * fold_train_available_instrument_years))
min_outer_validation_distinct_instruments = 4
min_outer_validation_distinct_instrument_years = 4
```

### 12.2 Count profiles

`strict`，用于 T0：

```text
min_train_event_count_after_purge = 500
min_train_positive_count_after_purge = 30
min_train_negative_count_after_purge = 100
min_inner_validation_event_count = 100
min_inner_validation_positive_count = 8
min_outer_validation_event_count = 80
min_outer_validation_positive_count = 5
```

`safe_probe`，用于 T1 / T2 / T3：

```text
min_train_event_count_after_purge = 400
min_train_positive_count_after_purge = 25
min_train_negative_count_after_purge = 80
min_inner_validation_event_count = 60
min_inner_validation_positive_count = 5
min_outer_validation_event_count = 60
min_outer_validation_positive_count = 5
```

若 `inner_validation_mode = none`，inner validation count gate 不适用，但必须记录：

```text
inner_validation_disabled_by_contract = true
fixed_n_estimators_used = true
```

`diagnostic_minimal`，只用于 T4：

```text
min_train_event_count_after_purge = 250
min_train_positive_count_after_purge = 15
min_train_negative_count_after_purge = 50
min_outer_validation_event_count = 40
min_outer_validation_positive_count = 3
```

T4 输出必须标记：

```text
diagnostic_only_due_to_minimal_gate = true
```

---

## 13. LGBM training contract

### 13.1 通用参数

P0.9A 不是 hyperparameter search。所有参数必须预注册在 config 中。

默认参数：

```yaml
lgbm_common:
  objective: binary
  boosting_type: gbdt
  learning_rate: 0.05
  num_leaves: 31
  max_depth: 5
  min_data_in_leaf: 50
  feature_fraction: 0.8
  bagging_fraction: 0.8
  bagging_freq: 1
  lambda_l1: 0.0
  lambda_l2: 1.0
  seed: 20260506
```

### 13.2 Early stopping 规则

若合同使用 early stopping：

```text
early_stopping_uses_inner_validation_only = true
outer_validation_used_for_early_stopping = false
outer_validation_used_for_best_iteration = false
```

若 inner validation 不足：

```text
contract_status = not_trainable_under_inner_validation
```

不得临时改用 outer validation early stopping。

### 13.3 Fixed rounds 规则

若合同使用 fixed rounds：

```text
best_iteration_selection = disabled
fixed_n_estimators configured before run
outer_validation_used_for_iteration_selection = false
```

默认：

```yaml
fixed_n_estimators:
  launch: 64
  failure: 32
```

P0.9A 可以同时报告 alternative fixed-round sanity：

```text
launch: 32 / 64
failure: 32 / 64
```

但 alternative fixed-round sanity 只能进入 diagnostic 输出，不得参与 `eligible_for_p0_9b_discovery_rerun`。若 T1 要进入 P0.9B，P0.9B requirement 必须重新预注册唯一 fixed-round policy。

### 13.4 Model fit success definition

`trainability_count_gate_pass = true` 不等于模型已经成功训练。

`lgbm_training_success = true` 当且仅当：

```text
1. trainability count gate pass。
2. anti-leakage gates pass。
3. LGBM fit completed without exception。
4. model produced finite probabilities for outer validation rows。
5. prediction row count equals eligible outer validation row count。
6. no NaN / inf score。
7. class distribution in train set contains both positive and negative class。
```

若 count gate 通过但 LGBM fit 失败，状态必须为：

```text
count_trainable_but_model_fit_failed
```

Required artifact：

```text
p0_9a_model_fit_failure_audit.csv
```

### 13.5 Model non-degenerate sanity

模型训练成功不要求 AUC 达标，但不能是退化输出。每个已训练 fold 必须输出：

```text
prediction_nan_rate
prediction_unique_value_count
prediction_std
trained_tree_count
feature_used_count
all_positive_or_all_negative_training_label_flag
model_training_error_flag
```

默认 non-degenerate pass：

```text
prediction_nan_rate = 0
prediction_unique_value_count >= 10
prediction_std > 0
trained_tree_count > 0
feature_used_count >= 5
all_positive_or_all_negative_training_label_flag = false
model_training_error_flag = false
```

该 pass 只用于说明训练合同技术上可运行，不得解释为模型有效。

Required artifact：

```text
p0_9a_model_non_degenerate_sanity_audit.csv
```

---

## 14. 样本权重与 failure 多窗口去重

P0.9A 沿用 P0.9 的 sample-weight group cap 和 failure multi-window 纪律。

### 14.1 `event_effective_date`

统一字段：

```text
launch task:
  event_effective_date = stratum_effective_date

failure task:
  event_effective_date = failure_decision_effective_date
```

sample weight group key：

```text
target_industry + model_task + fold_id + contract_id + instrument + calendar_year(event_effective_date)
```

Group-level cap 必须作用于同一 instrument-year group 的总权重，而不是仅限制单行权重：

```text
group_weight_sum_before_cap = sum(raw_sample_weight within group)
if group_weight_sum_before_cap > max_group_weight:
    final_sample_weight = raw_sample_weight * max_group_weight / group_weight_sum_before_cap
else:
    final_sample_weight = raw_sample_weight
```

`p0_9a_sample_weight_group_cap_audit.csv` 至少包含：

```text
group_key
group_weight_sum_before_cap
group_weight_sum_after_cap
cap_scale
top_instrument_year_weight_share
instrument_year_weight_hhi
group_cap_pass
```

### 14.2 Failure 多窗口

训练样本可保留：

```text
failure_decision_window in [3d, 5d, 10d]
```

但不得让 3d / 5d / 10d 重复窗口虚增训练有效样本。Failure task 必须同时满足：

```text
window_level_count_profile_pass = true
event_level_dedup_count_profile_pass = true
```

Window-normalized weight：

```text
base_event_weight = episode / event balanced weight
valid_window_count_for_event = count(valid failure_decision_window for launch_stratum_event_id within target_industry + fold_id + contract_id)
failure_window_normalized_weight = base_event_weight / valid_window_count_for_event
```

随后再应用 instrument-year group cap。不得先 cap 后再除 window 数。

必须输出：

```text
p0_9a_failure_window_weight_normalization_audit.csv
p0_9a_failure_multi_window_dedup_audit.csv
p0_9a_failure_event_level_trainability_audit.csv
```

主 sanity metrics 必须同时给出：

```text
window-level metrics
and event-level-dedup metrics
```

如果一个 launch event 被多个 window 命中，event-level dedup 保留：

```text
earliest failure_decision_effective_date
then earliest failure_decision_window
```

Failure event-level trainability dedup key：

```text
target_industry + model_task + fold_id + contract_id + launch_stratum_event_id
```

Event-level count profile：

```text
strict:
  min_train_dedup_event_count_after_purge = 250
  min_train_dedup_positive_event_count_after_purge = 20
  min_outer_validation_dedup_event_count = 60
  min_outer_validation_dedup_positive_event_count = 5

safe_probe:
  min_train_dedup_event_count_after_purge = 200
  min_train_dedup_positive_event_count_after_purge = 15
  min_outer_validation_dedup_event_count = 45
  min_outer_validation_dedup_positive_event_count = 4

diagnostic_minimal:
  min_train_dedup_event_count_after_purge = 120
  min_train_dedup_positive_event_count_after_purge = 8
  min_outer_validation_dedup_event_count = 30
  min_outer_validation_dedup_positive_event_count = 3
```

---

## 15. 允许输出的模型诊断

P0.9A 可以输出以下 model sanity diagnostics：

```text
AUC
logloss
Brier score
calibration by decile
feature importance gain
feature importance split
score distribution by fold
score bucket diagnostic by predeclared top 10% / 5% / 2%
```

但这些字段必须标记为：

```text
sanity_diagnostic_only = true
```

Score bucket diagnostic 规则：

```text
1. Bucket thresholds must be derived on train fold scores only。
2. Frozen train thresholds are then applied once to outer validation scores。
3. Validation score quantiles may be reported only as distribution audit, not as bucket-definition source。
4. No bucket may be promoted, selected, or recommended in P0.9A。
```

Required artifact：

```text
p0_9a_score_bucket_threshold_audit.csv
```

禁止：

```text
candidate_for_industry_p1_refine = true
validated_score_bucket = true
score_bucket_used_for_strategy = true
```

### 15.1 Diagnostic metrics cannot drive contract selection

以下字段全部是 `diagnostic_only`，不得参与 P0.9B 合同推荐：

```text
AUC
logloss
Brier score
calibration by decile
feature importance
score bucket diagnostic
fold_2024 robustness performance
```

P0.9A 的推荐只能由以下字段决定：

```text
core_folds_trainable_count
anti_leakage_pass
purge_pass
observed_reference_overlap_pass
model_fit_success
contract_selection_priority_for_p0_9b
```

若报告中出现基于 validation performance 的合同推荐，必须标记：

```text
p0_9a_contract_selection_violation = true
recommended_p0_9b_contract_id = null
```

Required artifact：

```text
p0_9a_outer_validation_metric_nonselection_audit.csv
```

---

## 16. Trainability statuses 与 P0.9B 进入条件

每个 `target_industry + model_task + fold_id + contract_id` 必须输出一个状态：

```text
trainable_under_strict_p0_9
trainable_under_safe_probe
trainable_under_diagnostic_minimal
not_trainable_due_to_purge
not_trainable_due_to_inner_validation
not_trainable_due_to_cross_section
not_trainable_due_to_positive_count
not_trainable_due_to_outer_validation
not_trainable_due_to_feature_asof_violation
not_trainable_due_to_observed_reference_overlap
not_trainable_due_to_label_truncation
not_trainable_due_to_failure_event_level_count
count_trainable_but_model_fit_failed
```

每个 `target_industry + model_task + contract_id` 必须输出 aggregate status：

```text
core_folds_trainable_count
core_folds_total = 4
model_fit_success_core_fold_count
robustness_2024_trainable
eligible_for_p0_9b_discovery_rerun
not_eligible_reason
recommended_p0_9b_contract_id
```

进入 P0.9B discovery rerun 的最低条件：

```text
1. core_folds_trainable_count >= configured_min_core_folds_trainable_for_p0_9b under the same contract_id
2. model_fit_success_core_fold_count >= configured_min_core_folds_trainable_for_p0_9b
3. feature_asof_leakage_violation_count = 0
4. observed_reference_decision_overlap_eligible_count = 0
5. observed_reference_feature_overlap_eligible_count = 0
6. train_label_window_purge_pass = true
7. model trained without outer validation early stopping
8. event-level dedup audit pass for failure task
9. failure task post-target exclusion audit pass
10. model non-degenerate sanity pass
11. contract_id selected by deterministic priority, not validation performance
12. selection_lineage_audit_pass = true
13. t0_vs_p0_9_reconciliation_pass = true or explained_diff_only = true
14. p0_9b_null_family_recommendation_specified = true
```

T4 不能使 `eligible_for_p0_9b_discovery_rerun = true`，即使它训练成功。

---

## 17. Required artifacts

第 17 节是 P0.9A 唯一 required artifact authority。除非显式标记 optional，否则实现必须输出。

### 17.1 Core panels / cache

```text
p0_9a_industry_launch_sample_panel.parquet
p0_9a_industry_failure_sample_panel.parquet
p0_9a_industry_trainability_probe_panel.parquet
p0_9a_industry_model_prediction_panel.parquet
```

### 17.2 Required CSV / JSON audits

```text
p0_9a_run_manifest.json
p0_9a_selection_lineage_audit.csv
p0_9a_industry_mapping_audit.csv
p0_9a_industry_feasibility_count_audit.csv
p0_9a_fold_inventory_audit.csv
p0_9a_fold_role_calendar.csv
p0_9a_t0_vs_p0_9_reconciliation_audit.csv
p0_9a_walk_forward_purge_audit.csv
p0_9a_inner_validation_purge_audit.csv
p0_9a_inner_validation_split_audit.csv
p0_9a_feature_asof_leakage_audit.csv
p0_9a_feature_contract_audit.csv
p0_9a_train_eval_eligibility_audit.csv
p0_9a_failure_post_target_exclusion_audit.csv
p0_9a_observed_reference_overlap_audit.csv
p0_9a_label_dictionary.csv
p0_9a_label_horizon_truncation_audit.csv
p0_9a_label_window_definition_audit.csv
p0_9a_label_window_end_date_audit.csv
p0_9a_feature_dictionary.csv
p0_9a_feature_availability_audit.csv
p0_9a_trainability_contract_matrix.csv
p0_9a_lgbm_fold_trainability_audit.csv
p0_9a_lgbm_training_status.csv
p0_9a_model_fit_failure_audit.csv
p0_9a_model_non_degenerate_sanity_audit.csv
p0_9a_lgbm_fixed_rounds_audit.csv
p0_9a_lgbm_early_stopping_audit.csv
p0_9a_sample_weight_group_cap_audit.csv
p0_9a_failure_window_weight_normalization_audit.csv
p0_9a_failure_multi_window_dedup_audit.csv
p0_9a_failure_event_level_trainability_audit.csv
p0_9a_model_sanity_metrics_by_fold.csv
p0_9a_model_sanity_metrics_oof.csv
p0_9a_score_bucket_threshold_audit.csv
p0_9a_score_bucket_diagnostic_only.csv
p0_9a_feature_importance_diagnostic_only.csv
p0_9a_industry_task_contract_summary.csv
p0_9a_contract_selection_audit.csv
p0_9a_p0_9b_null_family_recommendation.csv
p0_9a_outer_validation_metric_nonselection_audit.csv
p0_9a_bottleneck_decomposition_audit.csv
p0_9a_lgbm_model_identity_audit.csv
p0_9a_model_metric_selection_guard_audit.csv
p0_9a_schema_contract_audit.csv
p0_9a_post_validation_adjustment_audit.csv
p0_9a_recommendation_summary.csv
```

### 17.3 Markdown report

```text
explore9_p0_9a_industry_trainability_probe_report.md
```

---

## 18. Config sketch

```yaml
phase: p0_9a_industry_trainability_probe

paths:
  provider_uri: Explore7/data/qlib/cn_data_pit
  fallback_provider_uri: Explore1/data/qlib/cn_data
  fallback_provider_allowed_fields: [open, high, low, close, volume, money, factor]
  fallback_provider_forbidden_roles:
    - industry_membership
    - universe_membership
    - feature_asof_date
    - label_source
  universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
  industry_membership: Explore7/data/targets/pit_industry_membership.csv
  output_dir: Explore9/outputs/p0_9a

calendar:
  research_start: '2017-01-01'
  research_end: '2024-12-31'
  observed_reference_start: '2025-01-01'
  observed_reference_end: '2026-04-30'

target_industries:
  - 电子
  - 汽车
  - 电力设备

target_industry_selection:
  source: p0_9_fixed_9_industry_result_review
  selected_from_fixed_9: true
  post_p0_9_diagnostic_selection: true
  clean_oos_industry_selection: false
  require_selection_lineage_audit: true

model_tasks:
  - industry_launch_winner_score_lgbm
  - industry_failure_reject_score_lgbm

folds:
  core_probe_years: [2020, 2021, 2022, 2023]
  robustness_years: [2024]
  train_mode: expanding
  purge_train_label_window_end_before_validation_start: true
  inner_validation_purge_required: true
  fold_2024_counted_for_core_folds_trainable_count: false
  fold_2024_allowed_for_contract_selection: false
  inner_validation_label_window_end_before_outer_validation_start: true
  fold_role_calendar_required: true

contract_selection_priority_for_p0_9b:
  - T0_strict_p0_9_reproduction
  - T2_pooled_inner_validation
  - T3_grouped_temporal_inner_validation
  - T1_fixed_rounds_no_inner_validation

contracts:
  - contract_id: T0_strict_p0_9_reproduction
    inner_validation_mode: latest_train_year
    lgbm_training_mode: early_stopping_inner_validation
    instrument_gate_profile: strict_p0_9
    count_profile: strict

  - contract_id: T1_fixed_rounds_no_inner_validation
    inner_validation_mode: none
    lgbm_training_mode: fixed_n_estimators
    instrument_gate_profile: safe_relative
    count_profile: safe_probe

  - contract_id: T2_pooled_inner_validation
    inner_validation_mode: pooled_tail_train_years
    inner_validation_tail_years: 2
    lgbm_training_mode: early_stopping_inner_validation
    instrument_gate_profile: safe_relative
    count_profile: safe_probe

  - contract_id: T3_grouped_temporal_inner_validation
    inner_validation_mode: grouped_temporal_blocks
    inner_group_unit: instrument_year
    inner_validation_block_selection: latest_non_overlapping_blocks
    inner_validation_block_count: 2
    inner_validation_min_distinct_calendar_years: 2
    inner_validation_block_tie_break: calendar_year_desc_then_instrument_asc
    inner_validation_insufficient_blocks_status: not_trainable_under_inner_validation
    lgbm_training_mode: early_stopping_inner_validation
    instrument_gate_profile: safe_relative
    count_profile: safe_probe

  - contract_id: T4_diagnostic_minimal_instrument_gate
    inner_validation_mode: none
    lgbm_training_mode: fixed_n_estimators
    instrument_gate_profile: diagnostic_minimal
    count_profile: diagnostic_minimal
    diagnostic_only: true

lgbm_common:
  objective: binary
  boosting_type: gbdt
  learning_rate: 0.05
  num_leaves: 31
  max_depth: 5
  min_data_in_leaf: 50
  feature_fraction: 0.8
  bagging_fraction: 0.8
  bagging_freq: 1
  lambda_l1: 0.0
  lambda_l2: 1.0
  seed: 20260506

fixed_n_estimators:
  launch: 64
  failure: 32

feature_policy:
  feature_selection_enabled: false
  feature_availability_audit_train_only: true
  validation_based_feature_drop_enabled: false

eligibility:
  exclude_failure_post_target_rows: true
  failure_primary_pending_target: 50h120
  observed_reference_label_measurement_allowed_only_in_2024_robustness: true

score_bucket_diagnostic:
  buckets: [top_10pct, top_5pct, top_2pct]
  threshold_source: train_fold_scores_only
  validation_quantiles_allowed_for_definition: false
  diagnostic_only: true

post_validation_adjustment:
  if_any_threshold_gate_feature_contract_changed_after_validation: diagnostic_only
  requires_fresh_preregistered_rerun: true

instrument_gate_profiles:
  strict_p0_9:
    min_train_distinct_instruments: 20
    min_train_distinct_instrument_years: 40
    min_outer_validation_distinct_instruments: 8
    min_outer_validation_distinct_instrument_years: 8

  safe_relative:
    inventory_basis: fold_local_pre_label_outcome
    min_train_distinct_instruments_min: 8
    min_train_distinct_instruments_ratio: 0.50
    min_train_distinct_instruments_cap: 18
    min_train_distinct_instrument_years_min: 25
    min_train_distinct_instrument_years_ratio: 0.45
    min_train_distinct_instrument_years_cap: 50
    min_outer_validation_distinct_instruments_min: 5
    min_outer_validation_distinct_instruments_ratio: 0.25
    min_outer_validation_distinct_instrument_years_min: 5
    min_outer_validation_distinct_instrument_years_ratio: 0.20

  diagnostic_minimal:
    inventory_basis: fold_local_pre_label_outcome
    min_train_distinct_instruments_min: 6
    min_train_distinct_instruments_ratio: 0.35
    min_train_distinct_instrument_years_min: 15
    min_train_distinct_instrument_years_ratio: 0.30
    min_outer_validation_distinct_instruments: 4
    min_outer_validation_distinct_instrument_years: 4

count_profiles:
  strict:
    min_train_event_count_after_purge: 500
    min_train_positive_count_after_purge: 30
    min_train_negative_count_after_purge: 100
    min_inner_validation_event_count: 100
    min_inner_validation_positive_count: 8
    min_outer_validation_event_count: 80
    min_outer_validation_positive_count: 5

  safe_probe:
    min_train_event_count_after_purge: 400
    min_train_positive_count_after_purge: 25
    min_train_negative_count_after_purge: 80
    min_inner_validation_event_count: 60
    min_inner_validation_positive_count: 5
    min_outer_validation_event_count: 60
    min_outer_validation_positive_count: 5

  diagnostic_minimal:
    min_train_event_count_after_purge: 250
    min_train_positive_count_after_purge: 15
    min_train_negative_count_after_purge: 50
    min_outer_validation_event_count: 40
    min_outer_validation_positive_count: 3

failure_event_level_count_profiles:
  strict:
    min_train_dedup_event_count_after_purge: 250
    min_train_dedup_positive_event_count_after_purge: 20
    min_outer_validation_dedup_event_count: 60
    min_outer_validation_dedup_positive_event_count: 5
  safe_probe:
    min_train_dedup_event_count_after_purge: 200
    min_train_dedup_positive_event_count_after_purge: 15
    min_outer_validation_dedup_event_count: 45
    min_outer_validation_dedup_positive_event_count: 4
  diagnostic_minimal:
    min_train_dedup_event_count_after_purge: 120
    min_train_dedup_positive_event_count_after_purge: 8
    min_outer_validation_dedup_event_count: 30
    min_outer_validation_dedup_positive_event_count: 3

failure_window_weighting:
  normalize_by_valid_window_count: true
  apply_instrument_year_cap_after_window_normalization: true

model_non_degenerate_sanity:
  max_prediction_nan_rate: 0.0
  min_prediction_unique_value_count: 10
  min_feature_used_count: 5
  require_prediction_std_gt_zero: true
  require_trained_tree_count_gt_zero: true

success_rules:
  configured_min_core_folds_trainable_for_p0_9b: 3
  require_selection_lineage_audit: true
  require_t0_vs_p0_9_reconciliation: true
  require_p0_9b_null_family_recommendation: true
  require_no_feature_asof_leakage: true
  require_no_observed_reference_decision_feature_overlap: true
  require_train_label_window_purge_pass: true
  require_inner_validation_label_window_purge_pass: true
  require_no_outer_validation_early_stopping: true
  require_failure_post_target_exclusion: true
  require_score_bucket_train_thresholds_only: true
  require_model_fit_success: true
  require_model_non_degenerate_sanity: true
  require_failure_event_level_trainability_pass: true
  require_deterministic_contract_selection: true
  t4_can_enter_p0_9b: false

p0_9b_selection_family_policy:
  allowed_modes:
    - full_selection_replay_null
    - family_adjusted_post_selected_null
  must_cover_p0_9_fixed_9_industries: true
  must_cover_p0_9a_selected_3_industries: true
  must_cover_all_model_tasks: true
  must_cover_contracts: [T0_strict_p0_9_reproduction, T1_fixed_rounds_no_inner_validation, T2_pooled_inner_validation, T3_grouped_temporal_inner_validation]
  include_t4_as_diagnostic_family_member: true
```

---

## 19. Report requirements

`explore9_p0_9a_industry_trainability_probe_report.md` 必须至少回答：

```text
1. 三个行业是否 PIT exact match。
2. 每个行业 raw launch / failure 样本是否足够。
3. 每个 industry-task-fold-contract 在 T0 严格合同下为什么失败或通过。
4. T1 fixed rounds 是否能解决 inner validation 过薄。
5. T2 pooled inner validation 是否能解决 latest-year inner validation 过薄。
6. T3 grouped temporal inner validation 是否能保留 early stopping 且合法训练。
7. T4 minimal gate 是否只是说明小样本 diagnostic feasibility。
8. 哪些 industry-task-contract 满足 core_folds_trainable_count >= 3。
9. 哪些行业仍因 cross-section 不足只能 diagnostic-only。
10. 是否存在 feature-asof、observed-reference、label truncation 或 purge 违规。
11. 是否存在 count gate 通过但 LGBM fit 失败。
12. 若进入 P0.9B，推荐唯一 contract_id，且必须证明推荐不是基于 outer validation performance。
13. 如果合同因 AUC / logloss / score bucket 表现被选择，必须标记 selection violation 并取消 P0.9B 推荐。
14. failure task 是否同时通过 window-level count 与 event-level dedup count。
15. failure window-normalized weight 是否在 instrument-year cap 之前应用。
16. failure pending target、decision drawdown、false reject from-launch / from-decision 是否按 label dictionary 输出。
17. inner validation label window 是否跨入 outer validation year；若跨入，该 fold-contract 必须失败。
18. failure task 是否正确排除了 post-target rows。
19. label-window purge 使用 training label window 还是 metric label window，并解释二者分母差异。
20. 已训练模型是否通过 non-degenerate sanity，但不得把该 sanity pass 解读成有效性证明。
21. 三个目标行业是如何从 P0.9 固定 9 行业中后验选出的，且该选择为何不能被解释成 clean OOS。
22. T0 strict reproduction 与 P0.9 原始 trainability 输出是否一致；若不一致，差异是否只来自预注册修正。
23. T3 grouped temporal inner validation 是否按机械 block 规则生成，是否存在回溯挑选 block。
24. P0.9B 若继续推进，null / multiplicity 是否覆盖 fixed 9 industries、selected 3 industries、2 tasks、全部合同与 deterministic selection rule。
25. fallback provider 是否只用于基础 OHLCV / money 字段，且没有替代 PIT membership / universe / label source。
```

报告必须明确：

```text
P0.9A 没有 P1 candidate。
P0.9A 没有 validated score bucket。
P0.9A 没有 Explore10 建议。
```

---

## 20. 成功标准

P0.9A 成功不是模型赚钱，也不是 AUC 高。

P0.9A 成功标准是：

```text
至少一个 target_industry + model_task + contract_id
在 core_probe_oof 的 4 个 folds 中至少 3 个 fold 可合法训练，
且 model_fit_success，
且 model_non_degenerate_sanity_pass，
且没有 feature-asof / observed-reference / purge / label truncation / post-target exclusion 违规，
且 selection_lineage_audit_pass，
且 T0 与 P0.9 reconciliation 无 unexplained diff，
且 P0.9B selection family / null carry-forward recommendation 已输出，
且不是 T4 diagnostic_minimal contract，
且 recommended_p0_9b_contract_id 由 deterministic priority 给出。
```

如果满足，允许输出：

```text
recommendation = proceed_to_p0_9b_industry_lgbm_discovery_rerun
```

P0.9B 才能重新预注册：

```text
1. 唯一行业或多个行业；
2. 唯一 model task；
3. 唯一 trainability contract；
4. null full-retrain；
5. selection-family replay null 或 family-adjusted post-selected null；
6. score bucket candidate gate；
7. matched-delay failure baseline；
8. P1 refine eligibility。
```

---

## 21. 自我审查与实现前检查清单

实现前必须确认：

```text
1. 第 17 节列出的 required artifacts 全部存在，且第 17 节是唯一 required artifact authority。
2. p0_9a_fold_inventory_audit.csv 证明 safe_relative / diagnostic_minimal 使用 fold-local pre-label-outcome inventory。
3. p0_9a_inner_validation_split_audit.csv 证明 inner validation 没有使用 outer validation year 或 fold_2024 为 core fold 选 best_iteration。
4. p0_9a_contract_selection_audit.csv 输出 deterministic priority 选择过程。
5. p0_9a_outer_validation_metric_nonselection_audit.csv 证明 AUC / logloss / lift / score bucket 没有用于合同推荐。
6. p0_9a_feature_contract_audit.csv 证明 feature allowlist 未按 validation 指标调整。
7. p0_9a_model_fit_failure_audit.csv 区分 count trainable 与 model fit success。
8. p0_9a_lgbm_model_identity_audit.csv 记录 lgbm_config_hash / feature_set_version / label_version / sample_panel_version / random_seed / training_code_version。
9. T4 通过不会触发 eligible_for_p0_9b_discovery_rerun。
10. fold_2024 只进入 robustness audit，不影响 P0.9B 推荐。
11. fixed-round alternative 只进入 diagnostic，不影响合同推荐。
12. failure task 同时通过 window-level 与 event-level dedup trainability。
13. failure_window_normalized_weight 在 instrument-year cap 之前应用。
14. failure_drawdown_from_decision_60d 与 target_50h120_not_reached_before_decision_effective_date 已在 label dictionary 中完整定义。
15. failure post-target rows 没有进入 failure training / validation / count gate。
16. score bucket diagnostic 使用 train-fold threshold，而不是 validation quantile。
17. post-validation adjustment audit 没有发现事后调阈值 / 调合同。
18. p0_9a_bottleneck_decomposition_audit.csv 能按 purge / cross-section / inner-validation / positive-count / model-fit 归因失败。
19. p0_9a_selection_lineage_audit.csv 说明三个行业来自 P0.9 固定 9 行业的后验诊断选择。
20. p0_9a_t0_vs_p0_9_reconciliation_audit.csv 证明 T0 与 P0.9 strict trainability 输出一致，或只存在预注册允许差异。
21. T3 inner validation split 按固定 block count / tie-break 机械生成，没有回溯挑选。
22. p0_9a_p0_9b_null_family_recommendation.csv 说明 P0.9B 必须如何承接 selection family。
23. fallback provider 没有替代 PIT industry / universe / label source，且没有用 amount 替代 money。
```

若上述任一检查失败，本阶段不得输出：

```text
recommendation = proceed_to_p0_9b_industry_lgbm_discovery_rerun
```

---

## 22. 实现命令建议

```bash
uv run python Explore9/scripts/run_explore9.py profile-p0-9a \
  --config Explore9/configs/industry_trainability_probe_p0_9a.yaml

uv run python Explore9/scripts/run_explore9.py report-p0-9a \
  --config Explore9/configs/industry_trainability_probe_p0_9a.yaml
```

---

## 23. 最终结论权限

P0.9A 最终报告只能输出以下 recommendation 之一：

```text
recommendation = proceed_to_p0_9b_industry_lgbm_discovery_rerun
recommendation = continue_p0_9a_trainability_probe
recommendation = industry_task_diagnostic_only_due_to_cross_section
recommendation = stop_industry_lgbm_due_to_no_safe_trainable_contract
```

不得输出：

```text
recommendation = proceed_to_industry_p1_refine
recommendation = proceed_to_explore10_backtest
recommendation = freeze_strategy
recommendation = validated_industry_model
```

P0.9A 的正确定位始终是：

```text
训练可行性探针，不是模型有效性证明。
```
