# 需求：16C Sequential Continuation Separability Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0
SOURCE_EP16_ROOT = EXPERIMENT_ROOT
SOURCE_EP15_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP16_ROOT/`、`SOURCE_EP15_ROOT/`、`SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/` 表达的路径必须先解析到对应 root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、16B ready 裁决不可证明、16B label panel lineage 不可证明、step/label join 不可证明、t0 feature as-of 不可证明、split boundary 不可证明、effective-sample discipline 不可证明、search accounting 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来 16D+ 设想反推出逐行 step、label、feature、score、split boundary、entry 价格、exit 价格或收益。

## 1. 实验身份

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16C
run_id = 16C_sequential_continuation_separability_diagnostic
status = draft_ready_for_review
expected_entrypoint = src/run_16c_sequential_continuation_separability_diagnostic.py
expected_config = configs/config_16c_sequential_continuation_separability_diagnostic.yaml
expected_test_file = tests/test_16c_sequential_continuation_separability_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_16a = SOURCE_EP16_ROOT/requirement_16a_sequential_sampling_geometry_preflight.md
upstream_requirement_16b = SOURCE_EP16_ROOT/requirement_16b_sequential_continuation_label_design_diagnostic.md
upstream_report_16a = SOURCE_EP16_ROOT/outputs/publishable/reports/sequential_sampling_geometry_preflight_report.md
upstream_report_16b = SOURCE_EP16_ROOT/outputs/publishable/reports/sequential_continuation_label_design_diagnostic_report.md
```

16C 是 Episode 16 第三个 phase。它只在 16B 裁决为：

```text
16B_continuation_label_ready_for_separability_diagnostic
```

且 16B `next_allowed_requirement` 精确等于：

```text
requirement_16c_sequential_continuation_separability_diagnostic.md
```

时允许启动。

16C 是 Episode 16 中第一次允许引入 t0-observable feature 的阶段。它的使命是检验：

```text
在持有过程中的某个 non-overlap h20 step 起点，
只使用 step_start 当时已经可见的信息，
是否能对下一段 continuation label 形成可审计、跨 split 不崩坏的 separability。
```

16C 仍然不是：

```text
entry policy
exit policy
holding policy
收益 / alpha / cost / portfolio backtest
production model training
probability calibration
bet sizing
thresholded trading signal deployment
label deployment
```

16C 可以训练固定规格、低容量、诊断用途的 separability model，但这些模型只能用于回答本 requirement 的统计问题。任何 model score、probability、feature importance 或 selected threshold 都不得被解释为可交易信号。

若 16C 通过，最多只能授权后续新建：

```text
requirement_16d_sequential_continuation_policy_preflight.md
```

16D 仍需重新冻结 entry / exit / cost / holding / decision policy。本需求不得提前定义 16D 的交易规则。

## 2. 16A/16B 授权与冻结继承

16C 必须继承 16A 的 sampling geometry 与 16B 的 label design，不得重算、重选或调参：

```text
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_label_id = continuation_survival_h20_no_deep_drawdown
sampling_unit = non_overlapping_time_blocked_sampling_geometry_step
primary_split_bucket = train
stability_split_bucket = robustness
stress_test_split_bucket = validation
validation_usage = stress_test_readout_only
neutral_label_usage = excluded_from_primary_binary_target_but_retained_in_denominator_audit
partial_tail_step_usage = excluded_from_labelable_population
```

16B 的关键数值必须在 16C 的 upstream authorization audit 中复验：

```text
decision_state = 16B_continuation_label_ready_for_separability_diagnostic
next_allowed_requirement = requirement_16c_sequential_continuation_separability_diagnostic.md
primary_label_id = continuation_survival_h20_no_deep_drawdown
selected_threshold_id = up50pct
primary_horizon_sessions = 20

labelable_step_n_train = 20245
positive_step_n_train = 10078
negative_step_n_train = 4884
neutral_step_n_train = 5283
positive_rate_train = 0.497802
negative_rate_train = 0.241245

labelable_step_n_robustness = 2496
positive_step_n_robustness = 1346
negative_step_n_robustness = 526
neutral_step_n_robustness = 624
positive_rate_robustness = 0.539263
negative_rate_robustness = 0.210737

labelable_step_n_validation = 664
positive_step_n_validation = 325
negative_step_n_validation = 180
neutral_step_n_validation = 159

base_rate_nontrivial = true
effective_sample_sufficient = true
base_rate_stable_train_robustness = true
step_generation_lineage_sane = true
step_materialization_gate = pass
qfq_price_source_gate = pass
known_failed_overlap_gate = pass
known_failed_overlap_evaluability_gate = pass
soft_overlap_partial_coverage_caveat = true
known_failed_context_exposure_caveat = true
```

16C 必须明确继承 16B 的 caveat：

```text
1. 15B hard taxonomy projection 在 16B 中只是 episode-context exposure，不是 step-local morphology rediscovery。
2. 15C2 soft membership 覆盖不足只产生 soft_overlap_partial_coverage_caveat，不阻断 16C。
3. 16B ready 只授权 16C separability diagnostic，不授权 entry / exit / model / deployment。
```

若上述任一 ready 证据不可证明，`upstream_16b_authorization_gate = fail`，最终裁决必须 fail closed。

## 3. 核心问题

16C 回答以下问题：

```text
Q1. 在 16B materialized h20 labelable step 上，哪些 step_start 当时可见的状态特征
    可以 PIT-safe 地构造？哪些字段只能作为 lineage/audit，不能进入 feature？

Q2. 对 primary binary target：
      continuation_positive vs continuation_negative
    是否存在 train-only 冻结后仍能在 robustness 上保留的 separability？

Q3. 该 separability 是否来自广义 price/volume state，而不是从未来 step_end、
    cluster_end、episode_length、15B path_type、15C2 membership 或 split/date 泄漏出来？

Q4. 该 separability 是否只是 late-rescue / known-failed episode context 的人口结构暴露？
    若是，只能输出 context-concentrated blocked decision，不得授权 16D。

Q5. 若 separability 成立，下一阶段 16D 应继承哪个 label、哪个 sampling unit、
    哪些 feature-family evidence，以及哪些 caveat？
```

必须输出单一裁决：

```text
decision_state
```

## 4. Scope Boundary

16C 允许做：

```text
1. 读取 16B 的 step-level continuation label panel。
2. 基于 step_start_pos / step_start_date 构造 PIT-safe t0 feature panel。
3. 冻结 feature contract、as-of policy、missing policy、leakage audit。
4. 在 train 上 fit 固定规格低容量 diagnostic models。
5. 用 train-only preprocessing / folds / model spec 输出 separability readout。
6. 在 robustness 上做 OOS readout；validation 只做 stress-test readout。
7. 用 episode_cluster_id / instrument / time block 做 grouped 和 purged stability。
8. 输出 known-failed episode-context stratified separability readout。
9. 输出确定性 next-research decision map。
```

16C 明确不得做：

```text
1. 不新增、删除或重调 continuation label。
2. 不改变 selected threshold、primary horizon 或 sampling unit。
3. 不使用 validation / robustness 选择 feature、model family、hyperparameter、threshold 或 decision rule。
4. 不使用 step_end_pos、step_end_date、step_end_qfq_close、max_drawdown_from_step_start、
   step_end_price_ratio_minus_one_for_label_rule、continuation_positive、
   continuation_negative、continuation_neutral 作为 feature。
5. 不使用 cluster_end_pos、episode_length_sessions、future remaining sessions、
   full cluster duration、future overlap、future labelable step count 作为 feature。
6. 不使用 15B path_type、15C/15C2 phase/membership、known_failed_family、
   soft membership 或 any outcome-relative taxonomy 作为 model feature。
7. 不把 instrument id、calendar date ordinal、split bucket、episode_cluster_id 作为 model feature。
8. 不训练高容量模型，不做 grid search，不做 AutoML，不做 probability calibration。
9. 不计算交易收益、cost、slippage、capacity、portfolio、entry/exit PnL。
10. 不输出可部署 signal 或 production model artifact。
```

## 5. Required Inputs

### 5.1 16B artifacts

16C 必须读取以下 16B artifacts：

```text
SOURCE_EP16_ROOT/requirement_16b_sequential_continuation_label_design_diagnostic.md
SOURCE_EP16_ROOT/outputs/publishable/reports/sequential_continuation_label_design_diagnostic_report.md
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/input_artifact_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/upstream_16a_authorization_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/step_lineage_adapter_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/step_materialization_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/label_rule_definition_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_by_split_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_by_horizon_sensitivity_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_by_threshold_sensitivity_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/effective_sample_label_support_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/price_path_completeness_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/qfq_price_source_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/search_accounting_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/sequential_continuation_label_decision.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/validation_stress_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
SOURCE_EP16_ROOT/outputs/manifests/16B_sequential_continuation_label_design_diagnostic_manifest.json
```

`continuation_label_panel_readout.csv` 是 authoritative label source。16B local parquet caches 只能作为 optional cache：

```text
SOURCE_EP16_ROOT/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/materialized_step_panel.parquet
SOURCE_EP16_ROOT/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
SOURCE_EP16_ROOT/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_panel.parquet
```

这些 cache 在 Git 中可能不存在，不得作为 required input。若 cache 存在，runner 必须校验其 row count / key hash / schema 与 publishable artifacts 一致；若 cache 缺失，必须从 `continuation_label_panel_readout.csv` 与本节 required publishable inputs 重建所需 panel。若 cache 与 publishable CSV 不一致，以 publishable CSV 为准并 fail closed，不得静默用 cache 覆盖。

### 5.2 16A artifacts

16C 必须读取以下 16A artifacts 作为 sampling geometry lineage：

```text
SOURCE_EP16_ROOT/requirement_16a_sequential_sampling_geometry_preflight.md
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/sampling_geometry_decision.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/effective_sample_size_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/horizon_grid_step_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/episode_cluster_non_overlap_audit.csv
SOURCE_EP16_ROOT/outputs/manifests/16A_sequential_sampling_geometry_preflight_manifest.json
```

16A local cache 只能作为 optional lineage acceleration：

```text
SOURCE_EP16_ROOT/outputs/local_cache/16A_sequential_sampling_geometry_preflight/episode_interval_panel.parquet
SOURCE_EP16_ROOT/outputs/local_cache/16A_sequential_sampling_geometry_preflight/step_geometry_panel.parquet
```

这些 cache 不得作为 fresh-checkout reproducibility 的 required input。16C 所需 step/label row-level source 必须来自 16B publishable label panel；16A cache 只可用于复核 sampling geometry lineage。

### 5.3 PIT universe and qfq price source

16C 必须使用 PIT-safe step_start features，所需源数据为：

```text
TOPIC_ROOT/data/raw/akshare/day/qfq/{instrument}.csv
TOPIC_ROOT/data/processed/universe/pit_topn_400_100_executable_daily.csv
TOPIC_ROOT/data/processed/universe/pit_topn_400_100_membership_daily.csv
```

qfq price source 必须至少提供：

```text
date
open
high
low
close
volume
money
turnover_rate
instrument
```

PIT universe source 必须至少提供：

```text
usable_trade_date
instrument
membership_date
available_time
board_bucket
is_listed
is_st
is_suspended
total_market_cap_cny
board_rank_by_market_cap
board_quota
history_ready_240d_flag
history_observed_sessions_before_usable_date
```

对每个 step，feature as-of date 定义为：

```text
feature_as_of_date = step_start_date
feature_as_of_pos = step_start_pos
```

qfq rolling features 只能使用：

```text
qfq position <= step_start_pos
```

PIT universe features 只能使用：

```text
usable_trade_date == step_start_date
or latest usable_trade_date <= step_start_date with available_time <= step_start_date close
```

若 PIT universe 在 step_start_date 缺失，可以 row-level 标记 `pit_context_missing = true`，但不得未来填充。若 train 或 robustness required PIT context missing rate > 5%，`pit_context_feature_gate = fail`。

### 5.4 Required known-failed context lineage

16C 的 known-failed context independence gate 需要 row-level cluster context。该 context 不得依赖 16B local cache；必须从 15B publishable membership source 和 15B 冻结 taxonomy rule deterministic rebuild，并用 15B/16B publishable aggregates 校验：

```text
SOURCE_EP15_ROOT/requirement_15b_winner_path_shape_taxonomy_diagnostic.md
SOURCE_EP15_ROOT/src/run_15b_winner_path_shape_taxonomy_diagnostic.py
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/input_artifact_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_feature_definition_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_readout.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/representative_anchor_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/split_overlap_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
SOURCE_EP15_ROOT/outputs/manifests/15B_winner_path_shape_taxonomy_diagnostic_manifest.json
SOURCE_EP16_ROOT/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_readout.csv
```

`winner_episode_cluster_membership_audit.csv` 是 Git LFS publishable input，但它不包含 `path_type`。16C 必须用 15B frozen rule code / audited rule tables 对该 membership source deterministic rebuild row-level taxonomy assignment。15B local cache can be used only as optional acceleration:

```text
SOURCE_EP15_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet
SOURCE_EP15_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/anchor_path_shape_feature_panel.parquet
```

若 local cache 缺失，runner 必须重建；不得因 cache 缺失 fail closed。若 cache 存在，必须校验 rebuilt row key / path_type aggregate 与 cache 一致。

若 required 15B artifact 缺失、schema 不完整、row key duplicate、15B path_type enum 不可证明、或不能重建 16B `known_failed_overlap_readout.csv` 的 h20/up50 hard taxonomy aggregate within tolerance，`known_failed_context_rebuild_gate = fail`。

在执行 row-level taxonomy rebuild 之前，必须先校验 15B rule audit 与 feature definition audit 足以无歧义复算 path_type：

```text
required_rule_closure_status = pass iff
  path_shape_taxonomy_rule_audit.csv contains every train-frozen quantile / scaler needed by 15B predicates
  and path_shape_feature_definition_audit.csv defines every taxonomy_rule_input feature
  and run_15b_winner_path_shape_taxonomy_diagnostic.py exposes deterministic predicate order
  and all predicate / fallback branches are covered, including:
    data_quality_blocked
    unclassified_short_path
    jump_repricing_winner
    late_rescue_winner
    smooth_trend_winner
    slow_grind_winner
    stair_step_winner
    choppy_reversal_winner
    unclassified_mixed_path
```

若 rule / feature / predicate order 不足以闭合重建，不得硬算一个近似 taxonomy；必须设置：

```text
known_failed_context_rebuild_gate = fail_rule_underspecified
```

Cluster context 重建规则必须与 16B 保持一致：

```text
required_known_failed_path_types = {
  choppy_reversal_winner,
  late_rescue_winner,
  jump_repricing_winner,
  unclassified_mixed_path
}

cluster_failed_anchor_share =
  count rebuilt 15B taxonomy assignment rows in cluster with path_type == known_failed_family
  / count rebuilt 15B taxonomy assignment rows joined to cluster

known_failed_context_flag = cluster_failed_anchor_share >= 0.50
late_rescue_context_flag = known_failed_context_flag for known_failed_family == late_rescue_winner
known_failed_context_any = any known_failed_context_flag across required_known_failed_path_types
```

15B path_type enum 必须先校验包含 `required_known_failed_path_types`。不得把 join miss 解释成 `known_failed_context_any = false`。`representative_anchor_audit.csv` 可用于 sanity check dominant path type，但不得作为 row-level context source，因为它不能精确还原 every-family anchor share。

### 5.5 Optional appendix inputs

以下 artifacts 只能作为 appendix/readout，不得进入 model feature：

```text
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/known_failed_morphology_overlap_readout.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/anchor_soft_membership_panel.csv
```

它们必须在 `input_artifact_audit.csv.required_flag` 标为 `optional_appendix` 或 `optional_context_audit`。缺失不得导致 feature leakage fail，但若 requirement 声明的 known-failed context stratified readout 无法评估，必须输出 caveat，不得假设 context exposure 为 0。

## 6. Primary Step Universe

16C primary universe 由 16B label panel 派生：

```text
primary_step_universe =
  label_id == continuation_survival_h20_no_deep_drawdown
  and threshold_id == up50pct
  and horizon_sessions == 20
  and cluster_split_bucket in {train, robustness, validation}
  and label_rule_status == pass
  and step_start_pos is finite
  and step_end_pos == step_start_pos + horizon_sessions - 1
```

Primary binary target：

```text
target_binary_population =
  primary_step_universe
  and (continuation_positive == true or continuation_negative == true)

y = 1 if continuation_positive == true
y = 0 if continuation_negative == true
```

Neutral rows：

```text
continuation_neutral == true
```

不得进入 primary binary model fit、AUC、PR-AUC 或 threshold-free separability metric。但 neutral rows 必须保留在：

```text
neutral_population_audit.csv
feature_coverage_audit.csv
denominator_accounting fields
report denominator caveat
```

禁止静默删除 neutral rows 后声称 coverage 为 100%。

Required key uniqueness：

```text
step_id unique within label_id / threshold_id / horizon_sessions
instrument + episode_cluster_id + horizon_sessions + step_index unique
```

若 step_id duplicate、positive/negative 同时为 true、positive/negative/neutral 全 false、或 row key 无法 join 到 16A/16B lineage，`step_label_binding_gate = fail`。

## 7. Feature Contract

### 7.1 Primary feature families

16C primary feature set 只允许使用 step_start 当时可见的 rolling market state 与 PIT membership context。

Required qfq rolling features：

```text
ret_5d
ret_10d
ret_20d
ret_60d
volatility_20d
volatility_60d
distance_to_20d_high
distance_to_60d_high
distance_to_20d_low
distance_to_60d_low
max_drawdown_20d
max_drawdown_60d
ma_5_20_spread
ma_20_60_spread
turnover_rate_20d_mean
turnover_rate_60d_mean
turnover_rate_20d_zscore
volume_20d_zscore
money_20d_zscore
intraday_range_20d_mean
```

Formula freeze：

```text
ret_Nd = close[step_start_pos] / close[step_start_pos - N] - 1
daily_return[t] = close[t] / close[t - 1] - 1
volatility_Nd = std(daily_return over step_start_pos - N + 1 ... step_start_pos, ddof=0)
distance_to_Nd_high = close[step_start_pos] / max(high over last N sessions ending step_start_pos) - 1
distance_to_Nd_low = close[step_start_pos] / min(low over last N sessions ending step_start_pos) - 1
max_drawdown_Nd = min(close[t] / max(close over window up to t) - 1 over last N sessions ending step_start_pos)
ma_5_20_spread = mean(close last 5 sessions ending step_start_pos) / mean(close last 20 sessions ending step_start_pos) - 1
ma_20_60_spread = mean(close last 20 sessions ending step_start_pos) / mean(close last 60 sessions ending step_start_pos) - 1
turnover_rate_20d_mean = mean(turnover_rate last 20 sessions ending step_start_pos)
turnover_rate_60d_mean = mean(turnover_rate last 60 sessions ending step_start_pos)
turnover_rate_20d_zscore = (turnover_rate[step_start_pos] - mean(turnover_rate last 20)) / std(turnover_rate last 20, ddof=0)
volume_20d_zscore = (volume[step_start_pos] - mean(volume last 20)) / std(volume last 20, ddof=0)
money_20d_zscore = (money[step_start_pos] - mean(money last 20)) / std(money last 20, ddof=0)
intraday_range_20d_mean = mean(high / low - 1 over last 20 sessions ending step_start_pos)
```

If denominator std == 0：

```text
zscore feature = 0
zero_std_flag = true
```

Rows with insufficient rolling lookback must be retained in feature coverage audit and excluded from model fit only if required feature missing cannot be imputed by train median. If required feature missing rate > 5% in train or robustness after train-median imputation policy, `feature_coverage_gate = fail`。

Required PIT context features：

```text
log_total_market_cap_cny
board_rank_pct = board_rank_by_market_cap / board_quota
history_observed_sessions_before_usable_date
board_bucket_onehot
history_ready_240d_flag
```

`board_bucket_onehot` 的合法枚举冻结为：

```text
board_bucket_allowed_values = {chinext, main_board}
```

Validation / robustness 若出现 train 未见但属于合法枚举的 bucket，仍映射到 `unknown_train_unseen` 并进入 feature coverage audit；若出现不在合法枚举中的 bucket，`pit_context_feature_gate = fail_unknown_board_bucket_enum`。

`history_observed_sessions_before_usable_date` 与 `history_ready_240d_flag` 可同时作为 PIT context feature，但必须在 `feature_importance_stability_readout.csv` 标记：

```text
collinearity_caveat = history_depth_feature_pair
```

PIT status features:

```text
is_listed
is_st
is_suspended
```

必须进入 audit，但不得作为 model feature。若 primary universe 中出现 `is_listed != true`、`is_st == true` 或 `is_suspended == true`，该 row feature status = not_evaluable，且进入 `pit_context_feature_gate` 统计。

### 7.2 Secondary audit-only features

以下字段只允许用于 readout、stratification 或 leakage audit，不得进入 model feature：

```text
step_index
episode_cluster_id
instrument
cluster_split_bucket
threshold_id
horizon_sessions
known_failed_family
hard_projection_coverage
soft_overlap_coverage
15B path_type
15C2 soft membership
```

以下 cluster-relative realized-so-far features 可作为 appendix diagnostic，但不得进入 primary decision：

```text
sessions_since_cluster_start = step_start_pos - cluster_start_pos
cluster_start_to_step_start_return = close[step_start_pos] / close[cluster_start_pos] - 1
cluster_start_to_step_start_max_drawdown
cluster_start_to_step_start_realized_volatility
```

原因：16D 尚未定义 entry/holding start。任何使用 cluster_start 的特征都可能把 ex-post episode interval 结构误当成可部署 holding context。16C primary separability gate 只能使用 §7.1 primary features。

### 7.3 Forbidden feature fields

若任何 forbidden 字段进入 feature matrix、preprocessing、model fit、feature selection、threshold selection 或 score calculation，必须：

```text
feature_leakage_gate = fail
decision_state = 16C_sequential_continuation_separability_blocked_by_feature_leakage
```

Forbidden fields:

```text
step_end_pos
step_end_date
step_end_qfq_close
max_drawdown_from_step_start
step_end_price_ratio_minus_one_for_label_rule
continuation_positive
continuation_negative
continuation_neutral
label_rule_status
cluster_end_pos
episode_length_sessions
remaining_sessions_to_cluster_end
available_forward_sessions
full_horizon_nonoverlap_step_n
partial_tail_step_n
step_n_nonoverlap
anchor_n
source_anchor_row_n
path_winner_uncensored_anchor_n
15B path_type
15C entry_phase
15C2 soft membership scores
known_failed_step_flag
known_failed_family
validation / robustness labels used for any fit or threshold freeze
```

`label_rule_status` 可用于 filtering and audit only，不得作为 model feature。

## 8. Preprocessing And Model Arms

### 8.1 Train-only preprocessing

All preprocessing must be fit on train only：

```text
numeric_imputer = train median
numeric_scaler = train median/IQR robust scaler
categorical_encoder = train frozen one-hot categories
winsorization = train 1st/99th percentile caps
```

Validation and robustness must use train-frozen preprocessing parameters. Unknown categorical levels in validation / robustness must map to `unknown_train_unseen` and be counted in `feature_coverage_audit.csv`。

### 8.2 Fixed diagnostic model arms

16C may evaluate only the following fixed low-capacity arms：

```text
intercept_only_baseline
ridge_logistic_bar_state_v1
single_depth2_tree_bar_state_v1
univariate_feature_rank_readout
```

Model spec freeze：

```text
ridge_logistic_bar_state_v1:
  model_family = logistic_regression
  penalty = l2
  C = 1.0
  class_weight = balanced
  solver = liblinear
  max_iter = 1000
  random_state = 1616

single_depth2_tree_bar_state_v1:
  model_family = decision_tree_classifier
  max_depth = 2
  min_samples_leaf = max(50, ceil(0.02 * train_binary_n))
  class_weight = balanced
  random_state = 1616

univariate_feature_rank_readout:
  binning = train deciles
  metric = train_frozen_bin_positive_minus_negative_rate_spread
  no model fit
```

No hyperparameter search is allowed. The runner must fail if config contains any grid, random search, AutoML flag, or user-supplied alternative model family.

### 8.3 Fold discipline

Train separability must be audited using both:

```text
episode_cluster_grouped_cv:
  n_splits = 5
  group_key = episode_cluster_id
  same episode_cluster_id never split across folds

instrument_purged_chronological_cv:
  n_splits = 5
  fold_unit = chronological_time_block
  order_key = step_start_date
  test_fold = one contiguous time block
  train_candidate = all other time blocks
  purge_sessions = primary_horizon_sessions
  purge_key = instrument
  purge_rule =
    remove any train_candidate row where the same instrument has
    abs(train_step_start_pos - any_test_step_start_pos) < purge_sessions
    or train label window [train_step_start_pos, train_step_end_pos]
       overlaps any test label window [test_step_start_pos, test_step_end_pos]
```

该 CV 不是 instrument-grouped split；同一 instrument 可以出现在多个 chronological folds，但同 instrument 的近邻/重叠 label windows 必须被 purged。若实现把整个 instrument 作为不可跨 fold 的 group，则不符合本 requirement。

If a fold has fewer than:

```text
positive_n >= 50
negative_n >= 50
episode_cluster_n >= 20
```

the fold is invalid. If valid_fold_n < 4 for either CV scheme, `cv_power_gate = fail`。

若 `instrument_purged_chronological_cv` 因 purge 掉太多同 instrument 近邻窗口而导致 fold invalid，应归因于 `cv_power_gate = fail` 并进入 low-power decision branch，不得归因为 `train_cv_separability_gate = fail` 或 `separability_not_supported`。

Validation split remains stress readout only. It must never be used for model selection, threshold selection, feature selection, preprocessing, or decision upgrade.

## 9. Metrics

Primary target metrics are threshold-free:

```text
roc_auc
average_precision
binary_positive_rate = positive_n / (positive_n + negative_n)
pr_auc_lift_vs_binary_base = average_precision - binary_positive_rate
rank_ic_spearman
cluster_bootstrap_auc_ci_low
cluster_bootstrap_auc_ci_high
```

`binary_positive_rate` 与 16B labelable positive rate 不同。16B train labelable positive rate 为 `10078 / 20245 = 0.497802`；16C primary binary target 排除 neutral 后，train binary positive rate 为 `10078 / (10078 + 4884) = 0.673573`。所有 PR-AUC lift、top-decile lift 和 model-vs-baseline lift 必须使用 binary target denominator，不得使用 labelable denominator。

Thresholded readouts may be reported only as secondary diagnostics:

```text
top_decile_positive_rate
bottom_decile_negative_rate
top_decile_positive_minus_binary_base_rate
selected_train_quantile_readout_only
```

No thresholded readout may authorize 16D by itself.

Cluster bootstrap rules：

```text
bootstrap_unit = episode_cluster_id
bootstrap_replicates = 500
random_state = 1616
confidence_level = 0.95
```

Any confidence interval, p-value, or effective power statement must use cluster bootstrap or grouped CV, not raw row iid assumptions.

Robustness split 的 episode_cluster_n 约为 204，cluster bootstrap CI 只能作为 directional uncertainty readout。Primary go/no-go 仍由 grouped/purged fold-level stability、robustness OOS metric 和 context independence gate 共同决定；不得只凭 bootstrap CI 下界升级 decision。

## 10. Known-failed Context Independence

16C must rebuild row-level known-failed episode context from §5.4 required 15B publishable membership source, then validate the aggregate against 16B `known_failed_overlap_readout.csv`. 16B `known_failed_overlap_panel.parquet` may be used only as optional cache. These fields are never model features.

Required strata:

```text
all_steps
late_rescue_context
non_late_rescue_context
known_failed_context_any
non_known_failed_context
```

For each stratum and split, output:

```text
binary_step_n
positive_n
negative_n
episode_cluster_n
roc_auc
average_precision
binary_positive_rate
pr_auc_lift_vs_binary_base
valid_stratum_power
```

Context independence gate：

```text
known_failed_context_independence_gate = pass iff
  non_known_failed_context train binary_step_n >= 1000
  and non_known_failed_context train positive_n >= 200
  and non_known_failed_context train negative_n >= 100
  and non_known_failed_context robustness binary_step_n >= 200
  and non_known_failed_context robustness positive_n >= 50
  and non_known_failed_context robustness negative_n >= 30
  and robustness non_known_failed_context roc_auc >= 0.52
```

`known_failed_context` / `late_rescue_context` strata 若在 robustness 上样本稀疏，只设置：

```text
valid_stratum_power = false
known_failed_context_sparse_caveat = true
```

这不单独阻断 `known_failed_context_independence_gate`。该 gate 的本意是检验 `non_known_failed_context` 中是否仍有 separability；只要 non-known-failed side 满足样本量与 robustness AUC 门，known-failed side 稀疏只能进入 caveat 和 report，不得被解释成 context independence fail。

If all-segment separability passes but context independence fails, decision must be:

```text
16C_sequential_continuation_separability_context_concentrated_only
```

This outcome means t0 features may be proxying known failed episode context. It does not authorize 16D.

## 11. Required Outputs

All publishable tables must be written under:

```text
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/
```

Required tables：

```text
input_artifact_audit.csv
upstream_16b_authorization_audit.csv
step_label_binding_audit.csv
t0_feature_contract.csv
t0_feature_lineage_audit.csv
t0_feature_coverage_audit.csv
t0_feature_leakage_audit.csv
separability_training_universe_audit.csv
separability_fold_assignment_audit.csv
separability_model_registry.csv
univariate_feature_separability_readout.csv
grouped_cv_separability_readout.csv
oos_separability_readout.csv
feature_importance_stability_readout.csv
known_failed_context_rebuild_audit.csv
known_failed_context_stratified_separability_readout.csv
neutral_population_audit.csv
search_accounting_audit.csv
sequential_continuation_separability_decision.csv
```

Local cache outputs：

```text
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/t0_feature_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/separability_score_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/fold_assignment_panel.parquet
```

Optional publishable compressed score export：

```text
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_score_sample.csv.gz
```

If full score export would exceed 50MB uncompressed, do not publish the full score CSV. Keep full scores in local parquet cache and publish only aggregate readouts plus sample manifest.

Report：

```text
outputs/publishable/reports/sequential_continuation_separability_diagnostic_report.md
```

Manifest：

```text
outputs/manifests/16C_sequential_continuation_separability_diagnostic_manifest.json
```

## 12. Table Schemas

`upstream_16b_authorization_audit.csv` 至少包含：

```text
upstream_decision_state
upstream_next_allowed_requirement
primary_label_id
selected_threshold_id
primary_horizon_sessions
labelable_step_n_train
positive_step_n_train
negative_step_n_train
neutral_step_n_train
labelable_step_n_robustness
positive_step_n_robustness
negative_step_n_robustness
neutral_step_n_robustness
step_materialization_gate
qfq_price_source_gate
known_failed_overlap_gate
known_failed_overlap_evaluability_gate
soft_overlap_partial_coverage_caveat
known_failed_context_exposure_caveat
authorization_status
blocking_reason
```

`t0_feature_contract.csv` 至少包含：

```text
feature_name
feature_family
source_artifact
source_columns
formula_id
lookback_sessions
as_of_policy
allowed_primary_model_feature
allowed_secondary_readout
forbidden_as_model_feature
forbidden_reason
missing_policy
train_fit_only_preprocessing
```

`t0_feature_leakage_audit.csv` 至少包含：

```text
feature_name
max_source_pos_minus_step_start_pos
max_source_date_minus_step_start_date
uses_step_end_field
uses_cluster_end_field
uses_label_field
uses_path_taxonomy_field
uses_split_or_identity_field
uses_validation_or_robustness_fit
leakage_status
blocking_reason
```

`separability_training_universe_audit.csv` 至少包含：

```text
split_bucket
labelable_step_n
binary_step_n
positive_n
negative_n
neutral_n
episode_cluster_n
instrument_n
feature_complete_binary_step_n
feature_complete_rate
effective_sample_policy
universe_status
```

`grouped_cv_separability_readout.csv` 至少包含：

```text
cv_scheme
model_id
fold_id
train_binary_step_n
test_binary_step_n
train_episode_cluster_n
test_episode_cluster_n
test_positive_n
test_negative_n
purged_train_row_n
purge_rule_status
roc_auc
average_precision
binary_positive_rate
pr_auc_lift_vs_binary_base
rank_ic_spearman
fold_status
```

`oos_separability_readout.csv` 至少包含：

```text
split_bucket
model_id
binary_step_n
positive_n
negative_n
episode_cluster_n
roc_auc
average_precision
binary_positive_rate
pr_auc_lift_vs_binary_base
rank_ic_spearman
cluster_bootstrap_auc_ci_low
cluster_bootstrap_auc_ci_high
oos_status
```

`known_failed_context_stratified_separability_readout.csv` 至少包含：

```text
split_bucket
context_stratum
model_id
binary_step_n
positive_n
negative_n
episode_cluster_n
roc_auc
average_precision
binary_positive_rate
pr_auc_lift_vs_binary_base
valid_stratum_power
context_independence_status
```

`feature_importance_stability_readout.csv` 至少包含：

```text
feature_name
feature_family
model_id
cv_scheme
fold_n
mean_abs_coef_or_importance
median_rank
rank_iqr
sign_consistency_fold_share
selected_in_top_decile_fold_share
collinearity_caveat
rank_stability_status
```

`known_failed_context_rebuild_audit.csv` 至少包含：

```text
threshold_id
horizon_sessions
cluster_split_bucket
known_failed_family
rule_closure_status
source_15b_anchor_n
joined_cluster_n
joined_anchor_n
missing_cluster_n
path_type_enum_status
recomputed_positive_step_n
recomputed_failed_family_positive_step_n
source_16b_positive_step_n
source_16b_failed_family_positive_step_n
count_delta_vs_16b
aggregate_rebuild_status
known_failed_context_rebuild_gate
blocking_reason
```

`sequential_continuation_separability_decision.csv` 至少包含：

```text
decision_state
next_allowed_requirement
primary_label_id
selected_threshold_id
primary_horizon_sessions
primary_model_id
train_binary_step_n
train_positive_n
train_negative_n
train_episode_cluster_n
robustness_binary_step_n
robustness_positive_n
robustness_negative_n
robustness_episode_cluster_n
primary_model_feature_n
train_feature_complete_rate
robustness_feature_complete_rate
binary_sample_power
feature_power
input_artifact_gate
upstream_16b_authorization_gate
feature_contract_gate
feature_lineage_gate
feature_coverage_gate
feature_leakage_gate
step_label_binding_gate
pit_context_feature_gate
qfq_feature_source_gate
preprocessing_train_only_gate
cv_fold_assignment_gate
cv_power_gate
search_accounting_gate
train_cv_separability_gate
robustness_separability_gate
episode_cluster_grouped_cv_valid_fold_n
episode_cluster_grouped_cv_median_roc_auc
episode_cluster_grouped_cv_median_pr_auc_lift_vs_binary_base
episode_cluster_grouped_cv_positive_auc_fold_share
instrument_purged_chronological_cv_valid_fold_n
instrument_purged_chronological_cv_median_roc_auc
instrument_purged_chronological_cv_positive_auc_fold_share
robustness_roc_auc
robustness_pr_auc_lift_vs_binary_base
robustness_cluster_bootstrap_auc_ci_low
known_failed_context_rebuild_gate
known_failed_context_independence_gate
validation_stress_evaluable
neutral_population_caveat
known_failed_context_sparse_caveat
soft_overlap_partial_coverage_caveat
known_failed_context_exposure_caveat
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
model_deployment_authorized
production_signal_authorized
separability_diagnostic_complete
```

## 13. Decision Gates

Hard fail gates：

```text
input_artifact_gate
upstream_16b_authorization_gate
step_label_binding_gate
feature_contract_gate
feature_lineage_gate
feature_coverage_gate
feature_leakage_gate
pit_context_feature_gate
qfq_feature_source_gate
preprocessing_train_only_gate
cv_fold_assignment_gate
known_failed_context_rebuild_gate
search_accounting_gate
```

`cv_fold_assignment_gate` checks fold construction, purge rule application, and no same-cluster leakage. `cv_power_gate` is not a hard fail gate; it is a statistical power gate that maps to `16C_sequential_continuation_separability_low_power`.

Power gates：

```text
binary_sample_power:
  train_binary_step_n >= 5000
  and train_positive_n >= 500
  and train_negative_n >= 500
  and train_episode_cluster_n >= 200
  and robustness_binary_step_n >= 500
  and robustness_positive_n >= 100
  and robustness_negative_n >= 100
  and robustness_episode_cluster_n >= 100

feature_power:
  primary_model_feature_n >= 12
  and train_feature_complete_rate >= 0.95
  and robustness_feature_complete_rate >= 0.95
```

`binary_sample_power` 使用 16C binary target denominator：

```text
binary_step_n = positive_n + negative_n
neutral_n is excluded from binary_step_n
primary train binary_step_n = 10078 + 4884 = 14962
primary robustness binary_step_n = 1346 + 526 = 1872
```

不得把 16B labelable step count `20245` 当作 train binary denominator。

Separability gates：

```text
train_cv_separability_gate pass iff
  ridge_logistic_bar_state_v1 episode_cluster_grouped_cv valid_fold_n >= 4
  and ridge_logistic_bar_state_v1 episode_cluster_grouped_cv median_roc_auc >= 0.55
  and ridge_logistic_bar_state_v1 episode_cluster_grouped_cv median_pr_auc_lift_vs_binary_base >= 0.02
  and ridge_logistic_bar_state_v1 episode_cluster_grouped_cv positive_auc_fold_share >= 0.60
  and ridge_logistic_bar_state_v1 instrument_purged_chronological_cv valid_fold_n >= 4
  and ridge_logistic_bar_state_v1 instrument_purged_chronological_cv median_roc_auc >= 0.53
  and ridge_logistic_bar_state_v1 instrument_purged_chronological_cv positive_auc_fold_share >= 0.60

robustness_separability_gate pass iff
  ridge_logistic_bar_state_v1 robustness roc_auc >= 0.55
  and ridge_logistic_bar_state_v1 robustness pr_auc_lift_vs_binary_base >= 0.02
  and ridge_logistic_bar_state_v1 robustness cluster_bootstrap_auc_ci_low >= 0.50
```

Validation stress：

```text
validation_stress_evaluable:
  validation binary_step_n >= 100
  and validation_positive_n >= 30
  and validation_negative_n >= 30
```

`validation_stress_evaluable` 不参与 primary decision branch，只写入 decision row 和 report caveat。

## 14. Decision Map

最终裁决只能取以下枚举之一：

```text
16C_sequential_continuation_separability_ready_for_policy_preflight
16C_sequential_continuation_separability_blocked_by_input_or_lineage_failure
16C_sequential_continuation_separability_blocked_by_feature_leakage
16C_sequential_continuation_separability_low_power
16C_sequential_continuation_separability_not_supported
16C_sequential_continuation_separability_context_concentrated_only
```

Decision map：

```text
if feature_leakage_gate == fail:
  decision_state = 16C_sequential_continuation_separability_blocked_by_feature_leakage
  next_allowed_requirement = none

elif any hard fail:
  decision_state = 16C_sequential_continuation_separability_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif not binary_sample_power or not feature_power or cv_power_gate != pass:
  decision_state = 16C_sequential_continuation_separability_low_power
  next_allowed_requirement = none

elif not train_cv_separability_gate or not robustness_separability_gate:
  decision_state = 16C_sequential_continuation_separability_not_supported
  next_allowed_requirement = none

elif known_failed_context_independence_gate != pass:
  decision_state = 16C_sequential_continuation_separability_context_concentrated_only
  next_allowed_requirement = none

else:
  decision_state = 16C_sequential_continuation_separability_ready_for_policy_preflight
  next_allowed_requirement = requirement_16d_sequential_continuation_policy_preflight.md
```

Regardless of decision：

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
```

若 decision ready，只授权 16D 写一份 policy preflight requirement。16C 不授权实际交易、部署或持仓规则。

## 15. Search Accounting

`search_accounting_audit.csv` 必须声明：

```text
search_family = sequential_continuation_separability_diagnostic
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_label_id = continuation_survival_h20_no_deep_drawdown
model_family_grid_searched = false
hyperparameter_grid_searched = false
feature_selection_grid_searched = false
validation_used_for_selection = false
robustness_used_for_selection = false
primary_model_id = ridge_logistic_bar_state_v1
primary_model_spec_frozen = true
feature_contract_frozen_before_fit = true
forbidden_feature_audit_passed = true/false
```

No implementation may add feature/model variants after seeing train, validation, or robustness performance. Any extra exploratory readout must be marked `appendix_only` and excluded from decision.

## 16. Report Requirements

Report must be written in Chinese and include:

1. 最终裁决与 next allowed requirement。
2. 16B 授权复验与继承 caveat。
3. Primary target denominator：按 split 展示 positive / negative / neutral 计数。
4. 为什么 neutral rows 排除出 binary separability，但仍保留在 denominator audit。
5. Feature contract 与 feature leakage audit 摘要。
6. Train-only preprocessing 与 fold discipline。
7. Episode-cluster grouped CV 与 instrument-purged chronological CV 结果。
8. Robustness OOS separability 结果。
9. Validation stress readout 与 caveat。
10. Known-failed context stratified separability，以及证据是否 context-concentrated。
11. Feature importance stability，并强调其只用于诊断。
12. 显式 non-claims：无 entry、无 exit、无 PnL、无 cost、无 deployment、无 production model。
13. Findings and insight：16D 是否值得定义，以及 16D 必须继承哪些 caveat。

## 17. Manifest Requirements

Manifest must include:

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
input_artifact_hashes
upstream_16a_decision
upstream_16b_decision
primary_label_id
selected_threshold_id
primary_horizon_sessions
feature_contract_sha256
preprocessing_spec_sha256
model_registry_sha256
primary_model_id
train_cv_summary
robustness_oos_summary
known_failed_context_independence_summary
decision_state
next_allowed_requirement
authorization_booleans
output_hashes
row_counts
large_artifact_policy
```

If any output table exceeds 50MB, manifest must identify it and state whether it is local cache, LFS-published, gzip-published, or intentionally not published.

## 18. Test Plan

Implement the following named tests:

```text
test_16b_ready_authorization_required_for_16c
test_16b_next_allowed_requirement_must_match_16c
test_primary_step_universe_filters_up50_h20_primary_label_only
test_step_label_binding_rejects_duplicate_step_ids
test_binary_target_positive_vs_negative_excludes_neutral
test_neutral_rows_retained_in_denominator_audit
test_feature_contract_forbids_step_end_and_label_fields
test_feature_contract_forbids_cluster_end_and_episode_length_fields
test_feature_contract_forbids_15b_15c2_taxonomy_as_model_features
test_qfq_rolling_features_use_only_positions_le_step_start_pos
test_pit_context_join_uses_asof_not_future_fill
test_train_only_imputer_scaler_and_winsorization
test_validation_and_robustness_not_used_for_selection
test_no_hyperparameter_grid_or_model_family_search
test_episode_cluster_grouped_cv_keeps_cluster_in_one_fold
test_instrument_purged_cv_removes_same_instrument_label_window_overlap
test_cv_power_gate_requires_valid_fold_counts
test_cv_power_gate_low_power_not_input_lineage_failure
test_binary_sample_power_uses_effective_nonoverlap_and_cluster_counts
test_local_cache_inputs_are_optional_and_rebuildable_from_publishable_artifacts
test_feature_coverage_gate_fails_missing_rate_above_threshold
test_leakage_gate_precedes_other_decision_branches
test_known_failed_context_fields_are_readout_only_not_features
test_known_failed_context_rebuilt_from_15b_publishable_membership
test_known_failed_context_rebuild_must_match_16b_aggregate
test_known_failed_context_rebuild_fails_when_15b_rule_audit_underspecified
test_sparse_known_failed_context_stratum_is_caveat_not_gate_failure
test_context_concentrated_only_blocks_16d_authorization
test_pr_auc_lift_uses_binary_positive_rate_not_labelable_positive_rate
test_board_bucket_enum_frozen_and_unknown_bucket_fails
test_feature_importance_stability_schema_includes_collinearity_caveat
test_ready_decision_only_authorizes_named_16d_requirement
test_all_policy_and_deployment_authorizations_remain_false
test_search_accounting_rejects_posthoc_feature_or_model_variants
test_large_score_export_policy_keeps_full_scores_local_when_needed
```

Validation commands from `topics/02_AFML_BIG_WINNER`:

```text
python -m py_compile experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16c_sequential_continuation_separability_diagnostic.py
python -m pytest experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/tests/test_16c_sequential_continuation_separability_diagnostic.py -q
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16c_sequential_continuation_separability_diagnostic.py --mode check-inputs
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16c_sequential_continuation_separability_diagnostic.py --mode full
git diff --check
```

## 19. Implementation Notes

1. Keep implementation experiment-local. Reuse 16A/16B helper patterns via `importlib` where useful.
2. Prefer parquet local cache for row-level feature and score panels.
3. Do not publish full row-level score CSV if it creates avoidable large artifact risk.
4. All numeric comparisons in authorization audits should allow exact integer equality for counts and tolerance `1e-6` for rates.
5. Any generated report rewrite must update manifest report hash.
6. Any failure must fail closed with explicit blocking reason, not empty output tables.
