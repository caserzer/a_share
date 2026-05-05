# Explore9 扩展需求 5：P0.9 行业专用 LGBM Launch / Failure Scoring 探索

## 0. 文档状态

```text
requirement_id: Explore9_expand_5_p0_9
phase: P0.9
phase_name: Industry-Specialist LGBM Launch / Failure Scoring Discovery
created_for: Explore9
created_from: P0.8 gate_lgbm_report + user fixed industry list
research_window: 2017-01-01 至 2024-12-31
observed_reference_window: 2025-01-01 至 2026-04-30
artifact_prefix: p0_9_
output_root: Explore9/outputs/
primary_command_profile: profile-p0-9
primary_command_report: report-p0-9
self_check_status: implementation_ready_after_contract_closure
```

P0.9 是 Explore9 broad discovery 的第五轮扩展，接在 P0.8 之后。

P0.8 的主要结果不是“LGBM 无效”，而是：LGBM 对 launch / failure 都有可见预测力，但有效性高度依赖行业和 market regime；因此不能生成跨行业 P1 规则。P0.9 不再强行追求跨行业泛化，而是把研究问题明确改成：

```text
在预先固定的目标行业内部，
行业专用 LGBM 是否能相对行业内 baseline，
稳定提高 launch winner discovery 或 failure reject，
同时控制年份不稳定、个股集中、false reject、winner coverage loss 和 search bias？
```

P0.9 不是策略回测，不是最终买卖模型，不是 clean OOS proof，也不是 Explore10 入口。P0.9 最多输出：

```text
candidate_for_industry_p1_refine
industry_model_predictive_but_not_actionable
industry_specialist_diagnostic_only
```

P0.9 不得输出：

```text
validated_p1_rule
clean_oos_proven_rule
cross_industry_general_rule
ready_for_backtest
freeze_strategy
proceed_to_explore10_backtest
```

### 0.1 自我检查后的核心修订

本版已经完成 implementation-ready 前自查，并补齐以下合同：

```text
1. 正文 gate 使用的 thresholds 必须全部出现在 config sketch。
2. label dictionary 必须定义所有被 P1 / audit 使用的 label。
3. Required outputs 第 17 节是唯一 artifact authority。
4. 行业专用 raw score 不得跨行业比较。
5. P0.8 / P0.7 full-window best 只能 audit，不能做 P0.9 P1 proof。
6. 行业内样本不足、低方差特征、baseline 缺失、label horizon truncation 必须显式降级。
7. failure 多窗口训练样本和 event-level OOF 指标必须分开。
8. launch / failure 均必须使用 event_effective_date 作为 label window 起点。
9. P1 promotion 只来自 core OOF 2020-2023；fold_2024 只做 robustness audit。
```

---

## 1. 固定目标行业

P0.9 只研究以下 9 个预先固定行业：

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

### 1.1 行业固定纪律

这些行业由用户在 P0.9 开始前指定，属于预注册 target industry list。实现不得在运行后根据表现追加、删除或替换行业。

合法：

```text
固定 9 个行业全部跑完；
每个行业单独输出 launch / failure 模型、baseline、OOF、null 和 model card；
按行业独立判断是否存在 candidate_for_industry_p1_refine。
```

不合法：

```text
先跑全部行业，再只汇报表现最好的行业；
用 P0.8 top bucket 中贡献最高的行业自动选择 P0.9 行业；
把非目标行业的表现用于决定目标行业是否进入 P1；
把目标行业合并成一个 pooled model 后宣称行业专用有效。
```

### 1.2 行业选择偏差声明

P0.9 的固定行业清单是在 P0.7AB / P0.8 已经观察到行业条件化线索后提出的。因此：

```text
P0.9 = industry-specific hypothesis-generating robustness validation
not clean industry-selection-independent OOS proof
```

即使某个行业通过 P0.9，也只能进入：

```text
proceed_to_industry_p1_refine
```

不能直接宣称该行业模型已经 clean OOS validated。

### 1.3 行业映射与 PIT 纪律

行业归属必须来自 PIT industry membership：

```text
industry_membership: Explore7/data/targets/pit_industry_membership.csv
join key: date + instrument
```

每条样本的行业必须以 `event_effective_date` 当日或以前可观察的 PIT 行业为准，不得使用未来行业分类修正。

若目标行业名称无法与 PIT 行业完全匹配，必须显式标记：

```text
industry_mapping_status = unresolved
industry_enabled_for_p0_9 = false
```

不得静默把近似行业名、申万一级/二级混用或手工替换为其他行业。

---

## 2. 阶段定位

P0.9 是行业专用 nonlinear discovery，不是策略阶段。

P0.9 研究两个任务：

```text
P0.9A: industry_launch_winner_score_lgbm
P0.9B: industry_failure_reject_score_lgbm
```

P0.9 不研究：

```text
跨行业 general LGBM；
单一全市场 pooled LGBM；
完整 entry / exit / position sizing 策略；
NN / deep learning 主线；
Explore10 backtest；
使用 2025-2026 observed reference 做候选选择或 P1 promotion；
把 P0.8 已看过的 full-window best bucket 当成 clean OOS proof。
```

P0.9 可以研究：

```text
每个固定行业内的 launch winner score；
每个固定行业内的 failure reject score；
行业内 top score bucket 的 winner lift / failure precision；
行业内 feature importance / SHAP / leaf diagnostic；
行业内 false reject 和 winner coverage loss；
行业内 matched-delay baseline；
行业内 LGBM null full-retrain；
行业内 fold stability 和 2021/2022 failure-case review；
行业内 candidate_for_industry_p1_refine。
```

### 2.1 与 P0.8 的关系

P0.8 输出只能作为：

```text
background_reference
schema_reference
audit_anchor
hypothesis_seed_context
```

不得作为：

```text
label
feature
candidate selection target
threshold selection source
P1 proof
strategy source
```

P0.8 score 如需进入 P0.9，只能作为 audit-only comparison，不得作为模型 feature。

---

## 3. 绑定实现规则

本节是强制实现口径。若后文任何表述与本节冲突，以本节为准。

### 3.1 行业内模型，不是行业 feature 模型

P0.9 必须为每个目标行业单独训练模型：

```text
one target_industry × one model_task × one fold = one model training unit
```

单行业模型中，`industry` 本身是常量，不得作为模型输入特征。

禁止输入特征：

```text
industry
industry_code
target_industry_name
is_target_industry
P0.8 score
P0.8 candidate rank
P0.8 leaderboard result
validated / promoted flags from prior phases
```

允许输入特征：

```text
industry_breadth_20d
industry_breadth_change_5d
industry_relative_strength_vs_market
industry_money_breadth
industry_volatility_regime
industry_leader_count
stock_ret20_pctile_within_industry
stock_money_rank_within_industry
stock_vol_rank_within_industry
stock_rank_jump_within_industry
industry_regime
market_regime
```

解释：P0.9 不是让模型学习“这是电子行业所以买”，而是让模型在电子行业内部学习“哪些电子行业内个股状态更像 winner / failure”。

### 3.2 非目标行业用途

非目标行业样本不得进入 P0.9 模型训练、validation、candidate bucket、P1 promotion 或行业内 baseline denominator。

非目标行业数据只允许用于 T 日可观察的横截面市场统计，例如：

```text
ret_rank_20d_market
market_regime
market_breadth
market_quantile_alias
benchmark relative return
```

这些字段必须在 feature dictionary 中标记：

```text
feature_scope = market_context
computed_from_all_pit_universe = true
used_for_training_sample = false
```

### 3.3 Fold role 与 P1 promotion OOF

P0.9 沿用 P0.8 的 purged expanding walk-forward：

```text
fold_2020: train 2017-2019, validation 2020
fold_2021: train 2017-2020, validation 2021
fold_2022: train 2017-2021, validation 2022
fold_2023: train 2017-2022, validation 2023
fold_2024: train 2017-2023, validation 2024
```

默认 fold role：

```text
fold_2020: p1_promotion_eligible
fold_2021: p1_promotion_eligible
fold_2022: p1_promotion_eligible
fold_2023: p1_promotion_eligible
fold_2024: robustness_audit_only
```

P0.9 必须输出两个 OOF scope：

```text
oof_core_2020_2023:
  includes only fold_2020 ... fold_2023;
  excludes fold_2024;
  excludes observed-reference label measurement rows;
  is the only source for candidate_for_industry_p1_refine.

oof_with_2024_label_measurement:
  includes fold_2020 ... fold_2024;
  fold_2024 may use 2025-2026 only for pre-2025 decision forward label measurement;
  used for robustness / audit only.
```

若某个行业模型只靠 `fold_2024` 才显著改善，必须输出：

```text
industry_candidate_rejected_due_to_fold2024_audit_only_dependence = true
candidate_for_industry_p1_refine = false
```

### 3.4 Observed reference 规则

必须拆分三类 observed reference overlap：

```text
observed_reference_decision_overlap:
  decision / signal / effective / feature_asof date 落在 observed_reference_start 之后。
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_feature_overlap:
  feature value 需要 observed_reference_start 之后的数据才能计算。
  永远禁止进入 train、validation、selection、P1 eligibility。

observed_reference_label_measurement_overlap:
  decision / feature date 仍在 research_end 之前，
  但 forward label measurement window 跨入 observed reference。
  只允许用于 pre-2025 decision 的 forward outcome measurement。
```

硬规则：

```text
2025-2026 data may be used only to measure forward outcomes for decisions made on or before 2024-12-31.
2025-2026 data may not be used to create features, choose thresholds, choose buckets, choose hyperparameters, choose industries, or promote P1 candidates.
fold_2024_validation_role = robustness_audit_only
fold_2024_included_in_industry_p1_promotion_oof = false
```

### 3.5 Event effective date

P0.9 使用统一字段：

```text
event_effective_date
```

定义：

```text
launch task:
  event_effective_date = stratum_effective_date

failure task:
  event_effective_date = failure_decision_effective_date
```

所有以下口径统一使用 `event_effective_date`：

```text
calendar_year(event_effective_date)
event_instrument_year
sample weight group cap
fold assignment
instrument-year concentration
label window start
baseline join
OOF aggregation
```

### 3.6 Label window 起点

所有 forward label 的 `t` 必须是 `event_effective_date`，不是原始 signal date。

如果信号来自 close-derived formula，执行假设默认是 next trading day open：

```text
signal_date = formula observed close date
effective_date = next_trading_day(signal_date)
effective_price_reference = open on effective_date
```

label window 必须包含 effective date 当天 high / low / close：

```text
label_window_start = event_effective_date
label_window_N = [event_effective_date, trading_day_offset(event_effective_date, N - 1)]
label_window_includes_effective_date_high_low = true
```

禁止把主实现写成：

```text
max(high over t+1 ... t+120)
min(low over t+1 ... t+60)
```

### 3.7 行业间分数不可直接比较

P0.9 每个行业单独训练模型，score calibration 和 train bucket threshold 都是行业内定义。

硬规则：

```text
raw industry_launch_winner_score 不得跨行业排序；
raw industry_failure_reject_score 不得跨行业排序；
不同 target_industry 的 top 5% bucket 只代表各自行业内 top 5%，不是全市场同一风险/收益分位；
industry specialist summary 只能比较 OOF lift、coverage、false reject、null p/q、fold stability 等标准化指标。
```

如果报告按 raw score 横向排序行业，必须标记：

```text
cross_industry_score_comparison_invalid = true
all_candidate_for_industry_p1_refine = false until report corrected
```

### 3.8 行业内 P1 promotion 权限

P0.9 的候选权限只到行业内 P1 refine：

```text
candidate_for_industry_p1_refine = true / false
```

如果候选只在单一年份、单一 instrument、单一 instrument-year 或单一 regime 中成立，必须降级为：

```text
industry_single_year_diagnostic_only
industry_single_instrument_diagnostic_only
industry_regime_specialist_diagnostic_only
```

---

## 4. 数据输入与允许复用

### 4.1 继承数据边界

P0.9 沿用 Explore9 数据边界：

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
成交额字段继续使用 money，不得改用 amount；
OHLC 默认已复权，不得再次乘 factor；
所有特征只能使用 event_effective_date 或以前可观察信息；
所有 label 只能用于训练 / 验证 / 报告，不得作为 T 日特征。
```

### 4.2 允许复用 P0.7 / P0.8 输出

允许作为 schema / sample panel reference：

```text
Explore9/outputs/cache/p0_7_launch_episode_panel.parquet
Explore9/outputs/cache/p0_7_launch_stratum_event_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_opportunity_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_event_panel.parquet
Explore9/outputs/reports/p0_7_feature_dictionary.csv
Explore9/outputs/reports/p0_8_feature_dictionary.csv
Explore9/outputs/reports/p0_8_label_dictionary.csv
Explore9/outputs/reports/p0_8_lgbm_model_card.csv
Explore9/outputs/reports/p0_8_lgbm_feature_importance.csv
```

允许作为 audit anchor：

```text
Explore9/outputs/reports/p0_8_p1_promotion_oof_aggregation.csv
Explore9/outputs/reports/p0_8_oof_robustness_all_folds.csv
Explore9/outputs/reports/p0_8_fold_local_p0_7_baseline_audit.csv
Explore9/outputs/reports/p0_8_search_bias_audit.csv
Explore9/outputs/reports/p0_8_null_permutation_baseline.csv
```

禁止：

```text
用 P0.8 full-window best bucket 作为 P0.9 候选选择；
用 P0.8 validation 表现选择只跑哪个行业；
用 P0.8 leaf rule 作为 P0.9 hard-coded feature；
用 P0.8 score 作为 P0.9 模型输入 feature；
用 P0.8 candidate_for_p1_refine / rank / leaderboard score 作为训练标签或排序目标。
```

### 4.3 P0.9 自建 feature / label dictionary

P0.9 必须输出自己的：

```text
p0_9_feature_dictionary.csv
p0_9_label_dictionary.csv
p0_9_model_feature_set_manifest.csv
```

P0.9 不依赖 P0.8 token dictionary 作为唯一来源。所有实际使用字段必须在 P0.9 feature dictionary 中定义。

---

## 5. 样本单位

### 5.1 Launch model sample

Launch task 样本单位：

```text
one row per target_industry + launch_stratum_event_id
```

过滤条件：

```text
pit_industry_on_stratum_effective_date in fixed_target_industry_list
industry_launch_model_train_eval_eligible = true
```

主字段：

```text
target_industry
instrument
event_effective_date
launch_stratum_event_id
launch_episode_id
launch_family
launch_variant
launch_declared_role
stratum_date
stratum_effective_date
stratum_effective_price_reference
feature_asof_date
fold_id
validation_fold_role
sample_weight
final_sample_weight
event_instrument_year
```

Launch event 去重：

```text
primary launch OOF metrics must use one row per target_industry + launch_stratum_event_id.
If multiple raw launch hits map to the same launch_stratum_event_id, use the P0.7 deduped stratum event row.
```

### 5.2 Failure model sample

Failure task 样本单位：

```text
one row per target_industry + launch_stratum_event_id + failure_decision_window
```

但主 OOF 指标必须按 event-level dedup：

```text
failure_event_level_dedup_key =
  target_industry + failure_event_dedup_candidate_id + launch_stratum_event_id
```

`failure_decision_window` 可以作为模型输入或 diagnostic identity，但主指标 dedup 不得让同一 launch event 的 3d / 5d / 10d 重复计算 coverage / false reject / recall。

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
failure_event_dedup_candidate_id
feature_asof_date
fold_id
validation_fold_role
sample_weight
final_sample_weight
event_instrument_year
```

### 5.3 Failure 多窗口训练权重与 OOF 去重

训练时可以保留 3d / 5d / 10d 多窗口行，但必须避免同一 launch event 因窗口数量多而主导训练。

默认训练权重：

```text
window_count_for_event = count(failure_decision_window rows for target_industry + launch_stratum_event_id)
failure_window_normalized_weight = base_sample_weight / window_count_for_event
```

OOF / P1 主指标：

```text
same target_industry + launch_stratum_event_id 被多个 failure window 命中时，
只保留 earliest failure_decision_effective_date。
```

必须输出 multi-window dedup 和 window-weight audit。

### 5.4 行业内 train/eval eligibility

Launch：

```text
industry_launch_model_train_eval_eligible =
  target_industry in fixed_target_industry_list
  and pit_industry_on_event_effective_date = target_industry
  and event_effective_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_measurement_available = true
  and sample_has_required_features = true
```

Failure：

```text
industry_failure_model_train_eval_eligible =
  target_industry in fixed_target_industry_list
  and pit_industry_on_event_effective_date = target_industry
  and event_effective_date <= research_end
  and observed_reference_decision_overlap = false
  and observed_reference_feature_overlap = false
  and label_measurement_available = true
  and sample_has_required_features = true
  and target_50h120_not_reached_before_decision_effective_date = true for failure primary training/eval
```

P1 promotion rows additionally require：

```text
label_horizon_truncated = false
label_measurement_uses_observed_reference = false
validation_fold_role = p1_promotion_eligible
```

Already-achieved target rows：

```text
if target_50h120_reached_before_failure_decision_effective_date = true:
  exclude_from_failure_training_loss = true
  exclude_from_failure_validation_metrics = true
  include_in_post_target_risk_audit_only = true
```

### 5.5 行业内样本充足性审计

每个 `target_industry + model_task + fold_id` 必须输出样本充足性审计。

如果某行业在 core OOF 的至少 `thresholds.min_positive_validation_folds` 个 fold 中不满足样本充足性，只能输出：

```text
industry_model_sample_insufficient_diagnostic_only
candidate_for_industry_p1_refine = false
```

---

## 6. Label dictionary

P0.9 必须输出 `p0_9_label_dictionary.csv`。字段至少包括：

```text
label_name
model_task
label_type
label_definition_formula
reference_date_field
reference_price_field
horizon_trading_days
label_window_start_rule
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
```

### 6.1 Launch labels

Let：

```text
E = stratum_effective_date
P = stratum_effective_price_reference
```

Launch primary label：

```text
launch_winner_50h120 =
  max(high over [E, trading_day_offset(E, 119)]) / P - 1 >= 0.50
```

Launch secondary labels：

```text
launch_winner_50c120 =
  max(close over [E, trading_day_offset(E, 119)]) / P - 1 >= 0.50

launch_winner_100h240 =
  max(high over [E, trading_day_offset(E, 239)]) / P - 1 >= 1.00

launch_winner_100c240 =
  max(close over [E, trading_day_offset(E, 239)]) / P - 1 >= 1.00

launch_future_20pct_high_60d =
  max(high over [E, trading_day_offset(E, 59)]) / P - 1 >= 0.20

launch_future_max_drawdown_60d =
  min(low over [E, trading_day_offset(E, 59)]) / P - 1
```

Drawdown before 20% gain：

```text
first_20pct_gain_date =
  first date d in [E, trading_day_offset(E, 59)] where
  high_d / P - 1 >= 0.20

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

High-only audit：

```text
launch_high_only_50h120 = launch_winner_50h120 = true and launch_winner_50c120 = false
launch_high_only_winner_share = count(launch_high_only_50h120) / count(launch_winner_50h120)
```

### 6.2 Failure labels

Let：

```text
D = failure_decision_effective_date
Q = failure_decision_effective_price_reference
E = stratum_effective_date
P = stratum_effective_price_reference
```

Failure primary positive：

```text
failure_drawdown_from_decision_60d =
  min(low over [D, trading_day_offset(D, 59)]) / Q - 1

failure_reject_positive_primary =
  launch_winner_50h120_from_launch_reference = false
  and failure_drawdown_from_decision_60d <= -0.12
```

From-launch false reject：

```text
target_50h120_not_reached_before_decision_effective_date =
  max(high over [E, previous_trading_day(D)]) / P - 1 < 0.50

target_100h240_not_reached_before_decision_effective_date =
  max(high over [E, previous_trading_day(D)]) / P - 1 < 1.00

failure_false_reject_vs_launch_target_50h120 =
  target_50h120_not_reached_before_decision_effective_date = true
  and launch_winner_50h120_from_launch_reference = true

failure_false_reject_vs_launch_target_100h240 =
  target_100h240_not_reached_before_decision_effective_date = true
  and launch_winner_100h240_from_launch_reference = true
```

From-decision residual upside：

```text
failure_false_reject_vs_decision_target_50h120 =
  max(high over [D, trading_day_offset(D, 119)]) / Q - 1 >= 0.50

failure_false_reject_vs_decision_target_100h240 =
  max(high over [D, trading_day_offset(D, 239)]) / Q - 1 >= 1.00
```

P1 failure gate 固定使用 from-launch 作为主 false-reject / coverage-loss 口径：

```text
winner_false_reject_rate_for_industry_p1 = winner_false_reject_from_launch_rate
big_winner_false_reject_rate_for_industry_p1 = big_winner_false_reject_from_launch_rate
pending_winner_coverage_loss_for_industry_p1 = pending_winner_coverage_loss_from_launch
```

From-decision 只作为 secondary veto / diagnostic downgrade：

```text
decision_reference_secondary_veto_pass =
  failure_false_reject_vs_decision_target_50h120_rate <= thresholds.max_decision_reference_residual_50h120_rate
  and failure_false_reject_vs_decision_target_100h240_rate <= thresholds.max_decision_reference_residual_100h240_rate

if decision_reference_secondary_veto_pass = false:
  diagnostic_only_due_to_decision_reference_residual_reward_risk = true
  candidate_for_industry_p1_refine = false
```

Failure timing：

```text
first_12pct_drawdown_date_from_launch_reference =
  first date d in [E, trading_day_offset(E, 59)] where
  low_d / P - 1 <= -0.12

filter_before_12pct_drawdown =
  first_12pct_drawdown_date_from_launch_reference exists
  and D <= first_12pct_drawdown_date_from_launch_reference

filter_before_12pct_drawdown_rate =
  count(rejected event-level dedup rows where filter_before_12pct_drawdown = true)
  / count(rejected event-level dedup rows where first_12pct_drawdown_date_from_launch_reference exists)
```

### 6.3 Label horizon truncation audit

必须审计：

```text
label_horizon_truncated
label_measurement_uses_observed_reference
rows_eligible_for_p1_promotion
```

任何 P1 promotion row 必须满足：

```text
label_horizon_truncated = false
label_measurement_uses_observed_reference = false
```

---

## 7. 行业内 baseline

P0.9 的所有 lift 必须相对行业内 baseline。不得用全市场 baseline 替代行业内 baseline。

必须输出行业内 baseline 和 candidate-scope weighted baseline。

### 7.1 Industry-local baseline schema

字段至少包括：

```text
target_industry
model_task
fold_id
validation_fold_role
baseline_id
baseline_scope_type
baseline_scope_key
baseline_denominator_unit
baseline_denominator_definition
baseline_join_key
research_start
research_end
label_definition_version
feature_set_version
eligible_event_count
positive_count
positive_rate
false_positive_rate
median_future_max_drawdown_60d
winner_episode_coverage
failure_precision
nonwinner_precision
drawdown_avoided_reference
label_horizon_truncated_rate
observed_reference_label_measurement_rate
```

baseline scope 至少包括：

```text
industry_local_all_launch_baseline
industry_local_same_family_baseline
industry_local_same_lifecycle_baseline
industry_local_same_regime_baseline
industry_local_fold_local_p0_7_baseline
industry_local_fold_local_p0_8_bucket_baseline_audit_only
```

### 7.2 Candidate-scope weighted baseline

LGBM score bucket 可以跨 launch family / failure family，因此不能假设存在单一 same-family baseline。

必须定义：

```text
candidate_scope_weighted_baseline
```

计算：

```text
for each candidate bucket:
  compute candidate row composition by target_industry + family + variant + lifecycle_pool + regime bucket;
  join corresponding industry-local baseline for each scope cell;
  weighted average baseline metrics using final_sample_weight;
```

对 LGBM mixed-family bucket，正文中的 `industry_local_same_family_baseline` 统一解释为：

```text
candidate_scope_weighted_same_family_baseline =
  weighted average of industry_local_same_family_baseline cells
  using candidate final_sample_weight composition

launch_lift_vs_industry_local_same_family_baseline =
  launch_winner_rate / candidate_scope_weighted_same_family_baseline_winner_rate

failure_precision_lift_vs_candidate_scope_weighted_baseline =
  failure_precision / candidate_scope_weighted_baseline_failure_precision
```

不得对 mixed-family bucket 使用单一 family baseline，也不得退回全行业 baseline 冒充 same-family baseline。

必须输出：

```text
candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share
```

P1 gate 必须要求：

```text
candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share
```

缺失 baseline 的行不得静默删除后再计算 lift。

### 7.3 Fold-local P0.8 baseline contract

P0.8 / P0.7 full-window best 只能 audit，不能作为 P1 gate 对照。

若要比较上一阶段最佳单公式或 bucket，必须用：

```text
fold-local train-selected baseline
```

规则：

```text
for each target_industry + task + outer fold:
  choose baseline only from train years;
  freeze chosen baseline;
  evaluate once on outer validation fold;
```

---

## 8. Feature set

P0.9 的特征按行业内模型重新定义。`industry` 本身禁止作为模型输入，但行业动态状态和行业内 rank 必须重点保留。

### 8.1 Feature family

必须至少覆盖以下 family：

```text
price_return_features
volatility_features
prelaunch_path_features
repair_quality_features
money_quality_features
relative_strength_market_features
relative_strength_within_industry_features
industry_dynamic_context_features
market_regime_features
launch_family_context_features
failure_path_context_features
execution_feasibility_features
```

### 8.2 推荐核心特征

Launch / failure 共享核心特征：

```text
atr20_pct
rolling_range_20d
volatility60
amplitude20
prelaunch_drawdown_120d
launch_gain_from_recent_low_60d
launch_gain_from_recent_low_120d
ret_5d
ret_20d
ret_rank_20d_market
ret_rank_20d_industry
ret_rank_20d_industry_5d_ago
ret_rank_jump_5d_industry
money_ratio_20
money_ratio_60
money_rank_20d_market
money_rank_20d_industry
industry_breadth_20d
industry_breadth_change_5d
industry_relative_strength_vs_market_20d
industry_relative_strength_vs_market_60d
industry_money_breadth_20d
market_regime
industry_regime
higher_low_count_20d
ema20_distance
median20_distance
close_location
upper_shadow_ratio
body_ret
```

Execution audit-only features：

```text
next_open_gap_if_available_for_effective_date_audit_only
```

Failure-specific features：

```text
destructive_high_vol_3d_flag
destructive_high_vol_5d_flag
gap_fade_break_prior_close_5d_flag
rank_evaporation_2d_industry
rank_evaporation_3d_industry
rank_evaporation_5d_industry
money_price_keep_context_flag
repair_higher_low_reclaim_flag
break_launch_low_flag
break_ema20_flag
wide_stop_risk_pct
```

### 8.3 Feature dictionary contract

任何被 LGBM 使用的字段必须出现在 `p0_9_feature_dictionary.csv`。字段至少包括：

```text
feature_name
feature_family
feature_role
raw_or_derived
formula_text
formula_text_resolved
feature_asof_rule
required_raw_fields
computed_from_target_industry_only
computed_from_all_pit_universe
uses_future_data
uses_observed_reference_data
allowed_for_launch_model
allowed_for_failure_model
threshold_config_key
threshold_source
learned_or_fixed
validation_threshold_used
```

`threshold_source` 只允许：

```text
fixed_config
train_quantile
train_optimized
formula_constant
```

### 8.4 Feature availability audit

每个行业 / fold / task 必须审计特征覆盖、低方差和移除原因。

字段至少包括：

```text
target_industry
model_task
fold_id
feature_name
non_null_rate_train
non_null_rate_validation
unique_value_count_train
unique_value_count_validation
feature_removed_due_to_constant_or_low_coverage
feature_removed_reason
```

低覆盖或单行业内常量特征不得静默进入 LGBM。被移除特征必须写入 model feature set manifest。

---

## 9. Model tasks

### 9.1 Industry launch winner LGBM

模型名：

```text
industry_launch_winner_score_lgbm
```

训练单位：

```text
target_industry + fold_id
```

训练目标：

```text
primary label: launch_winner_50h120
secondary labels for audit: launch_winner_50c120, launch_winner_100h240, launch_false_positive_primary, launch_drawdown_before_20pct_gain
```

输出 score：

```text
industry_launch_winner_score
```

预声明 bucket：

```text
launch_top_10pct_by_train_threshold
launch_top_5pct_by_train_threshold
launch_top_2pct_by_train_threshold
```

### 9.2 Industry failure reject LGBM

模型名：

```text
industry_failure_reject_score_lgbm
```

训练单位：

```text
target_industry + fold_id
```

训练目标：

```text
primary label: failure_reject_positive_primary
secondary labels for audit: failure_false_reject_vs_launch_target_50h120, failure_false_reject_vs_launch_target_100h240, failure_false_reject_vs_decision_target_50h120, drawdown_avoided_vs_matched_delay
```

输出 score：

```text
industry_failure_reject_score
```

预声明 bucket：

```text
failure_top_risk_10pct_by_train_threshold
failure_top_risk_5pct_by_train_threshold
failure_top_risk_2pct_by_train_threshold
```

主指标必须 event-level dedup：

```text
same target_industry + launch_stratum_event_id 被多个 failure window 命中时，
只保留 earliest failure_decision_effective_date。
```

---

## 10. LGBM training contract

### 10.1 禁止 outer validation 泄漏

Outer validation fold 不得用于：

```text
early stopping
best iteration selection
hyperparameter selection
feature selection
bucket selection
leaf-rule selection
threshold optimization
candidate selection
```

如果使用 early stopping，只能使用 train fold 内部切分出的 inner validation：

```text
early_stopping_uses_outer_validation_fold = false
early_stopping_uses_inner_train_split_only = true
```

如果实现无法做到，则必须：

```text
early_stopping_rounds = null
n_estimators_fixed = true
```

### 10.2 Inner validation split rule

Inner validation 必须从 train fold 内部切分，不得使用 outer validation 年份。

默认：

```text
inner_validation = latest train year after purge
```

如果 latest train year positive count 不足，可以使用：

```text
inner_validation = last two train years after purge
```

但必须记录：

```text
inner_validation_split_rule
inner_validation_event_count
inner_validation_positive_count
inner_validation_years
```

### 10.3 Per-industry trainability gate

每个 `target_industry + model_task + fold_id` 训练前必须检查：

```text
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

不满足时：

```text
lgbm_training_enabled_for_industry_fold = false
fold_excluded_from_industry_lgbm_oof_aggregation = true
fold_status = disabled_due_to_insufficient_industry_sample
```

禁止用以下方法强行让薄样本 fold 进入主 OOF：

```text
SMOTE
复制正样本
validation oversampling
用 class_weight 掩盖 positive count 不足
合并 fold_2024 作为 P1 promotion fold
合并相邻行业样本
```

### 10.4 Sample weight 与 instrument-year cap

Sample weight group key：

```text
target_industry + fold_id + split + model_task + instrument + calendar_year(event_effective_date)
```

不得只做 row-level `min(weight, cap)`。必须做 group-level aggregate cap：

```text
sum(final_sample_weight within group) <= thresholds.max_instrument_year_group_weight_share * total_fold_task_weight
```

审计字段：

```text
target_industry
fold_id
split
model_task
instrument
event_effective_year
raw_group_weight
capped_group_weight
cap_applied
top_instrument_year_weight_share
instrument_year_weight_hhi
```

P1 gate 必须限制：

```text
oof_top_instrument_year_weight_share <= thresholds.max_top_instrument_year_weight_share
oof_instrument_year_weight_hhi <= thresholds.max_instrument_year_weight_hhi
```

### 10.5 LGBM config default

默认参数仅作为初始建议，P0.9 不得用 outer validation 搜索参数：

```yaml
objective: binary
metric: binary_logloss
boosting_type: gbdt
learning_rate: 0.03
num_leaves: 31
max_depth: 5
min_data_in_leaf: 80
feature_fraction: 0.80
bagging_fraction: 0.80
bagging_freq: 1
lambda_l1: 0.0
lambda_l2: 1.0
n_estimators: 500
early_stopping_rounds: 100
early_stopping_uses_inner_train_split_only: true
random_seed: 20260505
```

---

## 11. LGBM null full-retrain

P0.9 必须执行 LGBM bucket null full-retrain。没有执行 promotion-level null full-retrain 的 LGBM bucket 不得进入 industry P1 refine。

### 11.1 Primary null mode

主 null 模式：

```text
train_label_permutation_full_retrain_then_real_validation_eval
```

流程：

```text
for each target_industry + model_task + fold_id + predeclared_bucket_id:
  1. 在 train fold 内 permutation label；
  2. 保留 train feature、sample weight、fold split、bucket policy；
  3. 重新训练完整 LGBM；
  4. 在 permuted-train 模型上导出 train bucket threshold；
  5. 冻结 null model 和 null bucket threshold；
  6. 应用到真实 outer validation features；
  7. 用真实 outer validation labels 评估；
  8. 重复 N 次形成 best-null / bucket-null distribution。
```

禁止：

```text
只 permutation validation labels；
复用真实模型 score；
只重排 validation score；
用真实模型 feature importance 选择 null feature；
用 validation null 反向选择 bucket。
```

### 11.2 Null runtime staging

为控制 runtime，P0.9 允许两级 null：

```text
screening_null:
  n_repeats >= thresholds.min_lgbm_null_screening_repeats
  用于初筛和报告 search-bias warning。

promotion_null:
  n_repeats >= thresholds.min_lgbm_null_promotion_repeats
  只有 promotion_null 完成后，候选才允许 candidate_for_industry_p1_refine = true。
```

如果只完成 screening null：

```text
candidate_lift_exceeds_null_p95_screening = true / false
candidate_for_industry_p1_refine = false
candidate_status = null_screening_only_not_promotion_eligible
```

### 11.3 Permutation scope

默认：

```text
permutation_scope = target_industry + train_fold + model_task
```

可选更严格：

```text
permutation_stratified_by = event_effective_year + launch_family
```

如果某行业 fold 内 positive 太少导致 stratified permutation 不可行，必须标记：

```text
null_permutation_stratification_degraded = true
```

### 11.4 Null gate

每个 P1 candidate 必须满足：

```text
null_full_retrain_executed = true
completed_null_repeats >= thresholds.min_lgbm_null_promotion_repeats
candidate_lift_exceeds_null_p95 = true
empirical_p_value <= thresholds.max_lgbm_null_empirical_p
fdr_q_value <= thresholds.max_lgbm_null_fdr_q
```

---

## 12. Matched-delay baseline for failure model

Failure reject 仍必须比较 matched-delay baseline，防止模型只是学会“等几天失败自然暴露”。

默认模式：

```text
matched_delay_pseudo_reject_set_mode = exact_real_reject_count
```

规则：

```text
For each target_industry + fold + failure candidate bucket:
  pseudo_rejected_count_target = real event-level dedup reject count |R|
  pseudo reject dates sampled from eligible same-industry opportunity pool
  pseudo delay distribution matched to real reject delay distribution
  evaluate precision / false reject / drawdown avoided using same labels
```

禁止：

```text
every_U_gets_pseudo_filter_date
pseudo_rejected_count independent of real conversion rate
calendar-day delay sampling
sampling from non-target industries
```

Real reject drawdown avoided 定义：

```text
real_rejected_median_drawdown_from_decision_60d =
  median(failure_drawdown_from_decision_60d for real rejected event-level dedup rows)

pseudo_rejected_median_drawdown_from_decision_60d =
  median(failure_drawdown_from_decision_60d for matched-delay pseudo rejected rows)

drawdown_avoided_vs_matched_delay =
  pseudo_rejected_median_drawdown_from_decision_60d - real_rejected_median_drawdown_from_decision_60d
```

由于 drawdown 是负数，`drawdown_avoided_vs_matched_delay > 0` 表示真实 reject 相对 matched-delay 识别出更深或更应避免的回撤。

P1 failure gate 必须要求：

```text
drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_matched_delay
failure_precision_lift_vs_matched_delay >= thresholds.min_failure_precision_lift_vs_matched_delay
```

---

## 13. Score bucket 与 candidate identity

### 13.1 Candidate identity

LGBM bucket stable id：

```text
industry_lgbm_bucket_stable_candidate_id = hash(
  target_industry,
  model_task,
  model_family,
  predeclared_bucket_id,
  train_threshold_policy,
  score_direction,
  feature_set_version,
  label_version,
  fold_role_policy,
  observed_reference_policy
)
```

同一 bucket 在不同 fold 的 numeric threshold 可以不同，但必须来自同一 train-threshold policy，且 validation 不得参与 threshold 学习。

必须输出 threshold dispersion audit。

字段至少包括：

```text
target_industry
model_task
fold_id
predeclared_bucket_id
train_score_threshold
validation_score_threshold_used
threshold_source
threshold_policy
threshold_learned_on_validation
bucket_event_count
bucket_positive_count
```

### 13.2 Failure full id vs dedup id

Failure window 可以作为模型输入或 full candidate identity，但主指标使用 windowless dedup identity。

```text
failure_full_stable_candidate_id = industry_lgbm_bucket_stable_candidate_id + failure_decision_window

failure_event_dedup_candidate_id = hash(
  target_industry,
  model_task,
  model_family,
  predeclared_bucket_id,
  train_threshold_policy,
  score_direction,
  feature_set_version,
  label_version,
  fold_role_policy,
  observed_reference_policy,
  failure_window_group_policy = windowless_event_dedup
)
```

主指标固定使用：

```text
failure_event_level_dedup_key = failure_event_dedup_candidate_id + launch_stratum_event_id
```

### 13.3 Bucket selection

P0.9 只允许预声明 bucket：

```text
launch_top_10pct_by_train_threshold
launch_top_5pct_by_train_threshold
launch_top_2pct_by_train_threshold
failure_top_risk_10pct_by_train_threshold
failure_top_risk_5pct_by_train_threshold
failure_top_risk_2pct_by_train_threshold
```

不得在报告阶段查看 validation metrics 后选择“最好看的 bucket”。

---

## 14. P1 gate：industry launch candidate

P0.9 launch candidate 只能在行业内进入 P1 refine。

字段：

```text
candidate_for_industry_p1_refine
```

Launch P1 gate 必须全部满足：

```text
validation_scope = oof_core_2020_2023
fold_2024_used_for_p1_promotion = false
observed_reference_label_measurement_rows_used_for_p1_promotion = false

industry_launch_trainability_pass = true
positive_validation_fold_count >= thresholds.min_positive_validation_folds
validation_distinct_years >= thresholds.min_validation_years
validation_event_count >= thresholds.min_launch_validation_event_count
validation_positive_count >= thresholds.min_launch_validation_positive_count
validation_distinct_instruments >= thresholds.min_validation_distinct_instruments
validation_distinct_instrument_years >= thresholds.min_validation_distinct_instrument_years
core_p1_eligible_fold_count >= thresholds.min_core_eligible_folds_for_industry_p1

launch_winner_rate >= industry_local_all_launch_baseline_rate * thresholds.min_launch_lift_vs_industry_all
launch_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_launch_lift_vs_candidate_scope_weighted_baseline
launch_lift_vs_industry_local_same_family_baseline >= thresholds.min_launch_lift_vs_same_family
launch_50c120_rate >= candidate_scope_weighted_baseline_50c120_rate * thresholds.min_launch_50c120_lift_vs_candidate_scope_weighted_baseline
launch_high_only_winner_share <= thresholds.max_launch_high_only_winner_share
winner_episode_coverage >= thresholds.min_launch_winner_episode_coverage
false_positive_rate <= candidate_scope_weighted_baseline_false_positive_rate + thresholds.max_false_positive_worsening
median_future_max_drawdown_60d >= candidate_scope_weighted_baseline_median_drawdown_60d - thresholds.max_drawdown_worsening

candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share

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
fdr_q_value <= thresholds.max_lgbm_null_fdr_q
```

### 14.1 Launch positive validation fold definition

A launch fold is positive only if all are true：

```text
fold_event_count >= thresholds.min_launch_fold_event_count
fold_positive_count >= thresholds.min_launch_fold_positive_count
fold_lift_vs_industry_all >= thresholds.min_launch_fold_lift_vs_industry_all
fold_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_launch_fold_lift_vs_candidate_scope_weighted_baseline
fold_winner_coverage >= thresholds.min_launch_fold_winner_coverage
fold_false_positive_rate <= fold_candidate_scope_baseline_false_positive_rate + thresholds.max_fold_false_positive_worsening
fold_median_drawdown_not_worse_than_baseline = true
```

---

## 15. P1 gate：industry failure candidate

Failure P1 gate 必须全部满足：

```text
validation_scope = oof_core_2020_2023
fold_2024_used_for_p1_promotion = false
observed_reference_label_measurement_rows_used_for_p1_promotion = false

industry_failure_trainability_pass = true
positive_validation_fold_count >= thresholds.min_positive_validation_folds
validation_distinct_years >= thresholds.min_validation_years
validation_reject_event_count_event_dedup >= thresholds.min_failure_validation_reject_event_count
validation_failure_positive_count >= thresholds.min_failure_validation_positive_count
validation_distinct_instruments >= thresholds.min_validation_distinct_instruments
validation_distinct_instrument_years >= thresholds.min_validation_distinct_instrument_years
core_p1_eligible_fold_count >= thresholds.min_core_eligible_folds_for_industry_p1

failure_precision >= industry_local_failure_baseline_precision * thresholds.min_failure_precision_lift_vs_industry_baseline
nonwinner_precision_lift >= thresholds.min_nonwinner_precision_lift
failure_precision_lift_vs_candidate_scope_weighted_baseline >= thresholds.min_failure_precision_lift_vs_candidate_scope_weighted_baseline
failure_precision_lift_vs_matched_delay >= thresholds.min_failure_precision_lift_vs_matched_delay

drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_matched_delay
filter_before_12pct_drawdown_rate >= thresholds.min_filter_before_12pct_drawdown_rate

winner_false_reject_from_launch_rate <= thresholds.max_winner_false_reject_from_launch_rate
big_winner_false_reject_from_launch_rate <= thresholds.max_big_winner_false_reject_from_launch_rate
pending_winner_coverage_loss_from_launch <= thresholds.max_pending_winner_coverage_loss_from_launch
total_winner_coverage_loss_from_launch <= thresholds.max_total_winner_coverage_loss_from_launch

decision_reference_secondary_veto_pass = true

candidate_baseline_missing_row_rate <= thresholds.max_candidate_baseline_missing_row_rate
candidate_baseline_missing_weight_share <= thresholds.max_candidate_baseline_missing_weight_share

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
fdr_q_value <= thresholds.max_lgbm_null_fdr_q
```

### 15.1 Failure positive validation fold definition

A failure fold is positive only if all are true：

```text
fold_reject_event_count_event_dedup >= thresholds.min_failure_fold_reject_event_count
fold_failure_positive_count >= thresholds.min_failure_fold_positive_count
fold_failure_precision_lift_vs_industry_baseline >= thresholds.min_failure_fold_precision_lift_vs_industry_baseline
fold_failure_precision_lift_vs_matched_delay >= thresholds.min_failure_fold_precision_lift_vs_matched_delay
fold_winner_false_reject_from_launch_rate <= thresholds.max_fold_winner_false_reject_from_launch_rate
fold_big_winner_false_reject_from_launch_rate <= thresholds.max_fold_big_winner_false_reject_from_launch_rate
fold_pending_winner_coverage_loss_from_launch <= thresholds.max_fold_pending_winner_coverage_loss_from_launch
fold_drawdown_avoided_vs_matched_delay >= thresholds.min_fold_drawdown_avoided_vs_matched_delay
```

---

## 16. Interpretation and diagnostics

P0.9 必须输出解释性材料，但解释性材料不能代替 P1 gate。

### 16.1 Feature importance

每个行业 / task 必须报告：

```text
top gain features
top split features
per-fold feature stability
feature family contribution
industry_dynamic_feature_share
market_regime_feature_share
within_industry_rank_feature_share
```

### 16.2 2021 / 2022 stress review

P0.8 显示 2021 / 2022 是 launch / failure LGBM 的压力年份。因此 P0.9 必须对每个行业输出 stress review。

字段至少包括：

```text
target_industry
model_task
fold_id
validation_year
auc
logloss
bucket_lift
bucket_event_count
bucket_positive_count
baseline_positive_rate
market_regime_distribution
industry_regime_distribution
major_failure_reason
candidate_degraded_due_to_2021_2022_instability
```

### 16.3 Leaf rule

Leaf rules 只能作为 diagnostic，除非通过稳定性和 null：

```text
leaf_rule_single_fold_diagnostic_only by default
```

如果要提取 leaf rule，必须：

```text
train fold only extraction;
canonicalization by feature + quantile bucket;
outer validation one-time evaluation;
no validation-driven leaf selection;
```

---

## 17. Required outputs

第 17 节是 P0.9 required artifact 的唯一 authority。若前文声明了输出，必须在本节列出；未列入本节的 artifact 默认为 optional。

### 17.1 Manifest / dictionaries

```text
p0_9_run_manifest.json
p0_9_target_industry_mapping_audit.csv
p0_9_feature_dictionary.csv
p0_9_label_dictionary.csv
p0_9_model_feature_set_manifest.csv
p0_9_config_resolved.yaml
```

### 17.2 Cache parquet

Full row-level panels 默认只输出 parquet cache，不默认输出大 CSV：

```text
p0_9_industry_launch_sample_panel.parquet
p0_9_industry_failure_sample_panel.parquet
p0_9_industry_launch_oof_prediction_panel.parquet
p0_9_industry_failure_oof_prediction_panel.parquet
p0_9_industry_failure_event_dedup_panel.parquet
p0_9_industry_launch_episode_dedup_panel.parquet
```

### 17.3 Baseline / eligibility / trainability

```text
p0_9_industry_local_baseline.csv
p0_9_industry_candidate_scope_weighted_baseline.csv
p0_9_fold_local_p0_8_baseline_audit.csv
p0_9_industry_lgbm_fold_trainability_audit.csv
p0_9_sample_weight_group_cap_audit.csv
p0_9_failure_window_weight_normalization_audit.csv
p0_9_observed_reference_label_measurement_audit.csv
p0_9_industry_sample_sufficiency_audit.csv
p0_9_industry_feature_availability_audit.csv
p0_9_label_horizon_truncation_audit.csv
```

### 17.4 Model output

```text
p0_9_industry_lgbm_fold_metrics.csv
p0_9_industry_lgbm_score_bucket_leaderboard.csv
p0_9_industry_launch_lgbm_bucket_leaderboard.csv
p0_9_industry_failure_lgbm_bucket_leaderboard.csv
p0_9_industry_p1_promotion_oof_aggregation.csv
p0_9_oof_robustness_all_folds.csv
p0_9_lgbm_score_bucket_selection_audit.csv
p0_9_threshold_dispersion_audit.csv
p0_9_lgbm_calibration_drift_audit.csv
```

### 17.5 Null / matched-delay / search bias

```text
p0_9_lgbm_null_runtime_plan.csv
p0_9_lgbm_null_full_retrain_audit.csv
p0_9_lgbm_null_full_retrain_distribution.csv
p0_9_multiple_testing_fdr_audit.csv
p0_9_industry_failure_matched_delay_baseline.csv
p0_9_industry_failure_multi_window_dedup_audit.csv
```

### 17.6 Interpretation / report

```text
p0_9_industry_lgbm_feature_importance.csv
p0_9_industry_lgbm_shap_summary.csv
p0_9_industry_lgbm_leaf_rule_diagnostic.csv
p0_9_industry_model_card.csv
p0_9_industry_2021_2022_stress_review.csv
p0_9_industry_fold_failure_case_review.csv
p0_9_industry_specialist_summary.csv
explore9_p0_9_industry_lgbm_report.md
```

---

## 18. Report structure

`explore9_p0_9_industry_lgbm_report.md` 必须包含：

```text
1. Summary recommendation
2. Fixed target industry list and mapping audit
3. Data discipline and observed-reference audit
4. Per-industry sample sufficiency
5. Per-industry launch LGBM results
6. Per-industry failure LGBM results
7. Industry-local baseline comparison
8. LGBM null full-retrain result
9. Failure matched-delay and false-reject audit
10. Instrument / instrument-year concentration
11. Regime concentration and stress years
12. Feature availability / feature importance / SHAP / model interpretation
13. 2021/2022 failure-case review
14. Industry candidate decision table
15. What can and cannot be promoted to P1
16. Required next action
```

Report recommendation 只能取：

```text
continue_p0_9_industry_lgbm_discovery
proceed_to_industry_p1_refine
industry_model_predictive_but_not_actionable
industry_failure_direction_valid_but_false_reject_too_high
industry_launch_direction_valid_but_sample_or_year_unstable
stop_due_to_no_stable_industry_lgbm_structure
```

不得输出：

```text
proceed_to_explore10_backtest
ready_for_backtest
clean_oos_rule_validated
cross_industry_rule_validated
freeze_strategy
```

---

## 19. Config sketch

```yaml
phase: P0.9
profile_name: industry_specialist_lgbm_p0_9
artifact_prefix: p0_9_
output_root: Explore9/outputs/

research_window:
  research_start: 2017-01-01
  research_end: 2024-12-31
  observed_reference_start: 2025-01-01
  observed_reference_end: 2026-04-30

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
  fold_2020:
    train_start: 2017-01-01
    train_end: 2019-12-31
    validation_year: 2020
    validation_fold_role: p1_promotion_eligible
  fold_2021:
    train_start: 2017-01-01
    train_end: 2020-12-31
    validation_year: 2021
    validation_fold_role: p1_promotion_eligible
  fold_2022:
    train_start: 2017-01-01
    train_end: 2021-12-31
    validation_year: 2022
    validation_fold_role: p1_promotion_eligible
  fold_2023:
    train_start: 2017-01-01
    train_end: 2022-12-31
    validation_year: 2023
    validation_fold_role: p1_promotion_eligible
  fold_2024:
    train_start: 2017-01-01
    train_end: 2023-12-31
    validation_year: 2024
    validation_fold_role: robustness_audit_only

model_tasks:
  launch:
    enabled: true
    model_name: industry_launch_winner_score_lgbm
    primary_label: launch_winner_50h120
    predeclared_buckets:
      - launch_top_10pct_by_train_threshold
      - launch_top_5pct_by_train_threshold
      - launch_top_2pct_by_train_threshold
  failure:
    enabled: true
    model_name: industry_failure_reject_score_lgbm
    primary_label: failure_reject_positive_primary
    predeclared_buckets:
      - failure_top_risk_10pct_by_train_threshold
      - failure_top_risk_5pct_by_train_threshold
      - failure_top_risk_2pct_by_train_threshold

lgbm:
  objective: binary
  metric: binary_logloss
  learning_rate: 0.03
  num_leaves: 31
  max_depth: 5
  min_data_in_leaf: 80
  feature_fraction: 0.80
  bagging_fraction: 0.80
  bagging_freq: 1
  lambda_l2: 1.0
  n_estimators: 500
  early_stopping_rounds: 100
  early_stopping_uses_inner_train_split_only: true
  random_seed: 20260505

null_full_retrain:
  enabled: true
  n_repeats_screening: 20
  n_repeats_promotion: 100
  n_jobs: 24
  primary_null_mode: train_label_permutation_full_retrain_then_real_validation_eval
  permutation_scope: target_industry_train_fold_model_task
  max_runtime_guard_minutes_per_industry_task: 240

matched_delay:
  enabled_for_failure: true
  mode: exact_real_reject_count
  random_seed: 20260505
  n_repeats: 100
  n_jobs: 24
  max_sample_per_variant: 20000

thresholds:
  min_positive_validation_folds: 3
  min_validation_years: 3
  min_validation_distinct_instruments: 12
  min_validation_distinct_instrument_years: 20
  min_core_eligible_folds_for_industry_p1: 3

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
  min_launch_50c120_lift_vs_candidate_scope_weighted_baseline: 1.00
  max_launch_high_only_winner_share: 0.35
  min_launch_winner_episode_coverage: 0.05
  max_false_positive_worsening: 0.03
  max_drawdown_worsening: 0.02

  min_launch_fold_event_count: 50
  min_launch_fold_positive_count: 5
  min_launch_fold_lift_vs_industry_all: 1.05
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
  max_winner_false_reject_from_launch_rate: 0.20
  max_big_winner_false_reject_from_launch_rate: 0.15
  max_pending_winner_coverage_loss_from_launch: 0.35
  max_total_winner_coverage_loss_from_launch: 0.35
  max_decision_reference_residual_50h120_rate: 0.25
  max_decision_reference_residual_100h240_rate: 0.15

  min_failure_fold_reject_event_count: 25
  min_failure_fold_positive_count: 8
  min_failure_fold_precision_lift_vs_industry_baseline: 1.03
  min_failure_fold_precision_lift_vs_matched_delay: 1.00
  max_fold_winner_false_reject_from_launch_rate: 0.30
  max_fold_big_winner_false_reject_from_launch_rate: 0.25
  max_fold_pending_winner_coverage_loss_from_launch: 0.45
  min_fold_drawdown_avoided_vs_matched_delay: 0.00

  max_candidate_baseline_missing_row_rate: 0.05
  max_candidate_baseline_missing_weight_share: 0.05
  max_top1_instrument_contribution: 0.10
  max_top5_instrument_contribution: 0.35
  max_instrument_year_group_weight_share: 0.08
  max_top_instrument_year_weight_share: 0.08
  max_instrument_year_weight_hhi: 0.08
  max_regime_hhi: 0.55
  max_top1_regime_contribution: 0.70

  min_lgbm_null_screening_repeats: 20
  min_lgbm_null_promotion_repeats: 100
  max_lgbm_null_empirical_p: 0.10
  max_lgbm_null_fdr_q: 0.20
```

Thresholds 是初始建议，不代表策略参数。若实现需要调整，必须记录在 manifest，并说明调整是否发生在 validation 之前、是否使用 validation 表现。

---

## 20. Commands

建议新增命令：

```bash
uv run python Explore9/scripts/run_explore9.py profile-p0-9 --config Explore9/configs/industry_lgbm_p0_9.yaml
uv run python Explore9/scripts/run_explore9.py report-p0-9 --config Explore9/configs/industry_lgbm_p0_9.yaml
```

---

## 21. Implementation preflight checklist

实现前必须逐项检查：

```text
1. 固定 9 个行业是否全部映射到 PIT industry membership。
2. industry 本身、industry_code、target_industry_name 是否被排除出 LGBM feature。
3. fold_2024 是否只进入 robustness audit。
4. observed-reference label measurement rows 是否全部排除出 P1 promotion。
5. label window 是否从 event_effective_date 当天开始。
6. launch / failure label dictionary 是否覆盖所有训练、验证、P1 gate 字段。
7. 每个行业 / task / fold 是否通过 trainability gate。
8. Failure 多窗口训练是否做 window weight normalization。
9. Failure OOF / P1 是否做 event-level dedup。
10. candidate-scope weighted baseline 是否按 final_sample_weight 计算。
11. baseline missing row rate 和 weight share 是否同时进入 P1 gate。
12. instrument-year group cap 是否是 group aggregate cap，不是 row cap。
13. LGBM early stopping 是否只用 inner train split。
14. bucket threshold 是否只从 train fold 学出。
15. LGBM null full-retrain 是否达到 promotion repeats。
16. matched-delay 是否 exact_real_reject_count。
17. raw score 是否没有跨行业排序。
18. full-window P0.8 best 是否只作为 audit。
19. Required outputs 第 17 节列出的 artifact 是否全部生成。
20. 报告是否没有输出 Explore10 / clean OOS / frozen strategy。
```

---

## 22. 最终阶段结论口径

P0.9 可能结论：

```text
continue_p0_9_industry_lgbm_discovery
proceed_to_industry_p1_refine
industry_model_predictive_but_not_actionable
industry_failure_direction_valid_but_false_reject_too_high
industry_launch_direction_valid_but_sample_or_year_unstable
stop_due_to_no_stable_industry_lgbm_structure
```

P0.9 成功不要求找到最终交易策略。即使某行业没有 candidate，也可以是有效结论，因为它回答了行业专用 nonlinear model 是否具备进一步 refine 价值。

如果某行业 candidate 通过 P0.9，只能进入：

```text
industry-specific P1 refine
```

不得直接进入：

```text
Explore10 strategy backtest
cross-industry deployment
clean OOS validation claim
frozen strategy
```
