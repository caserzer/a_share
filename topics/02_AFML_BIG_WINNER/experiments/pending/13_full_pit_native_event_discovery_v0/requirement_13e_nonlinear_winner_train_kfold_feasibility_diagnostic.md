# 需求：13E Nonlinear Winner Train-KFold Feasibility Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、entry executability 不可证明、label horizon completeness 不可证明、feature availability 不可证明时 fail closed。
6. 不得从报告文本、图像或人工讨论文本反推出逐行 universe、标签、token、split 边界、entry 价格、event membership、decision point 或 path outcome。

## 1. 实验身份

```text
experiment_id = 13_full_pit_native_event_discovery_v0
phase_id = 13E
run_id = 13E_nonlinear_winner_train_kfold_feasibility_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.py
expected_config = configs/config_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.yaml
expected_test_file = tests/test_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.py
upstream_requirement_13a = EXPERIMENT_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_13a2 = EXPERIMENT_ROOT/requirement_13a2_compression_directional_disambiguation_preflight.md
upstream_requirement_13a3 = EXPERIMENT_ROOT/requirement_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.md
upstream_requirement_13c = EXPERIMENT_ROOT/requirement_13c_morphology_orthogonal_residual_importance_diagnostic.md
upstream_report_13a3 = EXPERIMENT_ROOT/outputs/publishable/reports/compression_repair_state_cost_and_native_feasibility_diagnostic_report.md
upstream_report_13c = EXPERIMENT_ROOT/outputs/publishable/reports/morphology_orthogonal_residual_importance_diagnostic_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13E 是 13C 之后的新诊断分支，不是 13B sequence mining，不是 meta-labeling 训练，也不是 13C 报告里假设的 `requirement_13d_compression_repair_meta_labeling_feasibility_preflight`。13C 已明确否决该 13D，本需求不复活它。13C 的正式裁决为：

```text
decision_state = 13C_stop_residual_probability_only_no_utility
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
primary_failure_reason = residual_winner_positive_but_utility_non_positive
```

13E 必须尊重该裁决。13E 不主张 13C 错误，也不试图救回 selected state 的可部署性。13E 只是一个 train-only diagnostic requirement，不作为任何后续推进、meta-labeling、仓位、交易或 requirement 授权依据。13E 只回答一个被 13C 留空、且 13C 从未测试的窄问题：

```text
13C 的 model-level incremental / MDA readout 使用 low_capacity_logistic_l2（线性）模型；
13C 的 selected-state stop 仍来自 residual utility hard gate，不由 13E 重审。
若把模型表达力升级为 repo 当前依赖内可运行的低容量非线性树模型（sklearn HistGradientBoosting），并在 train split 内部用
purged / embargoed k-fold 做诚实评估，selected state 的 winner_positive AUC、winner uplift
与 after-cost utility proxy 是否相对线性 baseline 出现稳定改善？
```

若非线性模型相对线性 baseline 没有稳定的 fold-mean 改善，或改善只停在 AUC 层、不转化为 after-cost utility proxy，13E 必须给出 diagnostic negative readout。若非线性模型在 train k-fold 上同时改善 AUC/uplift 与 after-cost utility proxy，13E 也只能给出 diagnostic positive readout；不得授权任何 OOS confirmatory、meta-labeling feasibility、meta-labeling 训练、sequence mining、bet sizing 或后续 requirement。

## 2. 核心问题

13E 回答以下问题：

```text
Q1. 在 selected composite state repair_range_participation_core_30 的 train events 上，
    低容量非线性树模型（sklearn_hgb_low_capacity）相对线性 baseline（logistic_l2）
    在 winner_positive 的 purged k-fold fold-mean AUC 上是否改善？

Q2. 非线性模型相对线性 baseline 的 fold-mean winner uplift（top-N 富集）是否改善？

Q3. 非线性模型相对线性 baseline 的 fold-mean after-cost utility proxy（0 / 50 / 100bps）
    是否改善，且 50bps 下是否转为非负？

Q4. 上述改善是只出现在 AUC / ranking 层（probability-only），
    还是同时转化为 after-cost utility proxy？

Q5. 在严格 train-only / non-confirmatory 边界下，是否存在一个非线性容量读数，
    可供后续人工讨论，而不是作为推进依据？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

13E 明确不是：

```text
13B sequence mining
13C residual readout retry
13A3 selected state retry
new native token search
new composite state search
barrier / label retuning
meta-labeling model training
probability calibration
bet sizing
portfolio backtest
cost model calibration
regime-conditional policy design
out-of-sample confirmatory test on validation / robustness
```

13E 允许做的只有：

```text
1. 复用 13C 已构建的 morphology_residual_panel，仅取 split == train 且 selected state membership 的行；
2. 复用 13C 已冻结的 feature clusters 与 train-frozen buckets；
3. 在 train split 内部构造 purged / embargoed event-span k-fold；
4. 用预注册固定超参的 logistic_l2 与 sklearn_hgb_low_capacity 两个模型族，在同一套 fold 上评估；
5. 比较两个模型族在 winner_positive 上的 fold-mean AUC、winner uplift、after-cost utility proxy；
6. 输出 diagnostic-only readout；所有 decision 都不得允许下一份 requirement 或 meta-labeling。
```

13E 不得产生任何交易、仓位、生产、alpha、meta-labeling 或后续 requirement 授权声明。任何 13E decision 都必须固定：

```text
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
```

## 4. 继承边界

### 4.1 允许继承

13E 可以继承：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
entry_date = next executable open after reference_date
entry_price = qfq open at entry_date
selected_label_id = vol20d_kup2p0_kdn1p0_H20
native opportunity universe definition from 13A
13A train-frozen native universe floor / cap
13A train-frozen compression threshold
13A2 train-frozen directional feature thresholds
13A3 required composite state dictionary
13A3 selected_state_id = repair_range_participation_core_30
split boundary from 12A7g / 13A / 13A2 / 13A3 / 13C
13C feature cluster definitions
13C train-frozen bucket thresholds
13C exact event-span uniqueness reconstruction (event_touch_offsets / exact_uniqueness)
cost_buffer_grid from 13A3 / 13C
reference_cost_buffer_return = 0.0100 unless upstream lineage proves otherwise
moderate_cost_buffer_return = 0.0050
```

13E 必须读取 13C publishable artifacts 与 local cache 作为 lineage：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_orthogonal_residual_importance_decision.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/feature_cluster_dictionary.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/sample_uniqueness_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/incremental_model_comparison.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/clustered_mda_importance.csv
outputs/local_cache/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_residual_panel.parquet
outputs/manifests/13C_morphology_orthogonal_residual_importance_diagnostic_manifest.json
```

可选使用 13A / 13A2 / 13A3 / 13C local cache，但必须校验：

```text
row key uniqueness
instrument x reference_date coverage
split boundary equality
selected label equality
base compression membership equality
selected composite state membership equality
feature cluster column availability and value equality for audited columns
train-frozen bucket threshold equality
sha256 / schema hash when manifest provides it
```

Cache 校验失败时必须从 raw PIT universe 和 qfq daily bars 重建，或重跑 13C runner 重建 panel；不得 fail open。

### 4.2 禁止继承 / 禁止主张

13E 明确不得：

- 不使用 C0 active band、C0 thresholds、C0 state-change family formula；
- 不修复 C0 selector 或 `volatility_reconciliation_fail`；
- 不重新选择 winner label；
- 不重新搜索 base compression state；
- 不新增 13A3 required composite states；
- 不更换 selected_state_id；
- 不重新定义 13C feature clusters 或重新 fit train-frozen buckets（必须沿用 13C 冻结值）；
- 不使用 validation / robustness 任何数据来 fit、选择、调参、early-stopping、阈值选择或读数；
- 不做 hyperparameter search 或 fold-internal 超参调优；
- 不做 probability calibration；
- 不做 sequence mining；
- 不做 bet sizing；
- 不做 regime-conditional policy；
- 不做资金曲线、滑点、容量或交易系统；
- 不把 train k-fold AUC positive 解释为可部署 edge；
- 不把 train k-fold utility proxy positive 解释为 OOS 验证通过。

13E 不能主张：

```text
selected state is deployable alpha
13C decision was wrong
nonlinear model recovers the state for trading
meta-labeling will make the state profitable
out-of-sample edge confirmed
```

13E 只能主张：

```text
nonlinear model capacity does / does not improve selected-state winner AUC and after-cost utility proxy
on train purged k-fold. Any positive result is diagnostic-only and cannot be used to explain away
13C's validation / robustness failure or justify any separate meta-labeling feasibility requirement.
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

同 13A / 13A2 / 13A3 / 13C：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq daily `reference_pos` 与 next-open executable `entry_pos`。不可证明时 row-level not evaluable；全局 schema / PIT 失败时 fail closed。

### 5.2 Upstream decision requirements

13E 要求 13C decision table 满足：

```text
input_gate_status = pass
upstream_lineage_gate_status = pass
row_level_rebuild_gate_status = pass
sample_uniqueness_gate_status in {pass_with_exact_t1, pass_with_downstream_exact_t1_requirement}
decision_state = 13C_stop_residual_probability_only_no_utility
selected_state_id = repair_range_participation_core_30
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
```

若 13C 已经授权 meta-labeling 或 sequence mining，13E 不应运行，状态为：

```text
13E_blocked_upstream_13c_already_authorized
```

若 13C input / lineage / row-level rebuild audit 未通过，13E 必须 fail closed：

```text
13E_blocked_upstream_13c_lineage_failure
```

13E 可以在 13C stop 基础上运行；13C 的 winner-utility failure 是本需求的研究前提，不是 blocker。

### 5.3 Label lineage

13E 必须沿用 12A7g / 13A / 13A2 / 13A3 / 13C 的 selected label：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_id = volatility_20d
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
```

13E 不得 retune `k_up`、`k_dn`、horizon 或 same-bar priority。若 label formula、vol reference unit、split boundary 或 label eligibility 不可证明，状态为：

```text
13E_blocked_label_lineage_failure
```

## 6. Row-Level Rebuild

13E 必须复用或重建以下 row-level panel，并只保留 train 子集：

```text
train_event_panel(row)
  = 13C morphology_residual_panel
  filtered to split_bucket == train AND native_scope == true AND membership(selected_state_id) == true
  + selected label fields
  + barrier outcome fields
  + utility barrier return fields
  + 13C feature cluster columns
  + 13C train-frozen bucket columns
  + market_regime_bucket (carried for provenance only, not used as a split/gate axis in 13E)
```

必需 row key：

```text
row_id
instrument
reference_date
split_bucket
board_bucket
calendar_year
calendar_month
market_regime_bucket
entry_date
entry_price
entry_pos
```

必需 label / utility fields：

```text
winner_positive
upper_first
lower_first
fast_fail
neutral
censored
same_bar_conflict
horizon_complete
upper_barrier
lower_barrier
time_to_upper
time_to_lower
horizon_sessions
row_utility_component_0bps
row_utility_component_50bps
row_utility_component_100bps
utility_positive_50bps
```

必需 feature columns（沿用 13C cluster 定义，不得新增、不得重 fit bucket）：

```text
cluster_drawdown_morphology: max_drawdown_20d, ret_20d, ret_60d, rebound_from_20d_low
cluster_denominator_controls: board_bucket, calendar_year, liquidity_bucket, volatility_bucket
cluster_compression: volatility_20d, volatility_60d, range_width_20d
cluster_position_strength: distance_from_20d_low, close_vs_sma20, close_position_20d
cluster_participation: turnover_zscore_20d, amount_ratio_5d_20d, volume_up_price_not_down_5d
```

若 selected state 的 train event 数低于 `min_train_event_n`（config，默认 1000），或任一 required feature 全空，状态为：

```text
13E_blocked_row_level_rebuild_failure
```

## 7. Feature Sets and Model Families

### 7.1 Feature sets

13E 不重新设计 feature，只沿用 13C 的两个 feature set，使非线性消融与 13C 严格可比：

```text
baseline_feature_set =
  cluster_drawdown_morphology
  + cluster_denominator_controls

augmented_feature_set =
  baseline_feature_set
  + cluster_compression
  + cluster_position_strength
  + cluster_participation
```

13E 的主要对照变量是 model family（线性 vs 非线性），次要对照变量是 feature set（baseline vs augmented）。不得引入任何 13C 未冻结的新特征、交互项或变换。若 config 显式开启 `explicit_interaction_probe = false`（默认 false），则不构造任何手工交互项；显式交互探查留给后续独立需求，不在 13E 内做。

### 7.2 Model families

允许且必须运行的模型族（全部预注册固定超参，禁止 search）：

```text
logistic_l2          # 线性 baseline，沿用 13C 超参
sklearn_hgb_low_capacity # scikit-learn HistGradientBoosting 低容量非线性树模型，本需求的核心对照
```

`logistic_l2` 超参（沿用 13C，不得变更）：

```text
penalty = l2
solver = liblinear
C = 0.50
max_iter = 200
standardize_features = true (train-fold-frozen scaler)
```

`sklearn_hgb_low_capacity` 超参（预注册固定，不得 search、不得 fold-internal 调优、不得 OOS 调优）：

```text
model_class = sklearn.ensemble.HistGradientBoostingClassifier
loss = log_loss
max_iter = 200
learning_rate = 0.03
max_leaf_nodes = 15
max_depth = 4
min_samples_leaf = 100
l2_regularization = 1.0
random_state = 13050
early_stopping = False
```

模型只做 diagnostic，不得用于交易信号、阈值选择、probability calibration、meta-labeling 或 bet sizing。`sklearn.ensemble.HistGradientBoostingClassifier` 不可用时（import 失败或当前 scikit-learn 版本不支持该类），状态为：

```text
13E_blocked_nonlinear_model_unavailable
```

不得用 logistic-only fallback 冒充非线性对照后给出 diagnostic positive readout。

## 8. Purged / Embargoed Train K-Fold Protocol

### 8.1 Fold 构造

13E 的全部评估都在 train split 内部进行，validation / robustness 不参与。Fold 必须按 event-span purge + embargo 构造：

```text
fold_n = 5 (config, default 5)
fold_assignment = chronological contiguous blocks by reference_date within train
t0 = entry_date
t1 = first touch date of upper/lower barrier, else vertical barrier date (horizon_sessions)
event_span_i = [entry_pos_i, entry_pos_i + offset_i]   # offset from 13C event_touch_offsets
purge_window_sessions = 20
embargo_sessions = 20
purge_group_unit = instrument
embargo_scope = global_calendar_session
min_effective_train_event_n_per_fold = 300
min_effective_test_event_n_per_fold = 50
```

Fold 规则：

```text
1. 对每个 fold k：test_k = fold k 的 events；train_k = 其余 folds 的 events。
2. 从 train_k 中 purge 掉 event_span 与 test_k 任一 event_span 在同一 instrument 上重叠的行。
3. 在 test_k 的全局 calendar-session 时间边界两侧各 embargo embargo_sessions 个 session，任何 instrument 上落入 embargo 窗口的 train_k 行都剔除。
4. scaler / bucket 不得重 fit（bucket 沿用 13C train-frozen），scaler 只在 train_k 上 fit 后应用到 test_k。
5. fold 内训练 sample weight 必须在 purge / embargo 之后的 train_k 事件集合内，用 13C exact t1 重建逻辑重新计算 event-span average_uniqueness；不得使用 full-train 或包含 test_k 的全局 uniqueness 权重。
6. test_k 的 uniqueness 只能作为 audit readout，不得影响 train_k sample weight、scaler、模型拟合或任何 threshold。
```

`time_order_preserved = true`，fold 之间不得 shuffle 跨时间。purge / embargo / fold-local uniqueness weighting / minimum effective fold support 缺失任一项时不得评估，状态为：

```text
13E_blocked_purged_cv_integrity_failure
```

### 8.2 Fold-level 评估指标

每个 `(model_family, feature_set, fold)` 必须在 test_k 上计算：

```text
auc = winner_positive AUC on test_k
logloss = winner_positive log loss on test_k
winner_uplift_topN =
  mean(winner_positive | top_N rows by model score in test_k)
  - mean(winner_positive | all rows in test_k)
N = round(top_fraction * test_k_n)   # top_fraction config, default 0.20
utility_proxy_0bps  = mean(row_utility_component_0bps  | top_N rows by model score in test_k)
utility_proxy_50bps = mean(row_utility_component_50bps | top_N rows by model score in test_k)
utility_proxy_100bps= mean(row_utility_component_100bps| top_N rows by model score in test_k)
```

`utility_proxy` 是 test fold 内 top-N 排序的乐观上界（每个模型在 test fold 内自选 top-N）。decision 只能使用 fold-mean 指标在两个模型族之间的相对差与符号，不得把 absolute `utility_proxy` 水平当作可部署 utility 或仓位输入。

### 8.3 Fold 聚合

必须输出每个 `(model_family, feature_set)` 的 fold-mean 与 fold-std：

```text
fold_mean_auc, fold_std_auc
fold_mean_logloss, fold_std_logloss
fold_mean_winner_uplift_topN, fold_std_winner_uplift_topN
fold_mean_utility_proxy_0bps, fold_std_utility_proxy_0bps
fold_mean_utility_proxy_50bps, fold_std_utility_proxy_50bps
fold_mean_utility_proxy_100bps, fold_std_utility_proxy_100bps
```

## 9. Nonlinear vs Linear Comparison

### 9.1 Comparison readout

13E 必须输出 logistic vs sklearn_hgb 在 augmented_feature_set 上的对照（主对照），以及各自 baseline vs augmented 的对照（辅对照）。

必须输出：

```text
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/nonlinear_vs_linear_comparison.csv
```

字段：

```text
feature_set
metric_id                         # auc / logloss / winner_uplift_topN / utility_proxy_0bps / utility_proxy_50bps / utility_proxy_100bps
logistic_fold_mean
logistic_fold_std
sklearn_hgb_fold_mean
sklearn_hgb_fold_std
nonlinear_minus_linear_delta
delta_fold_std
delta_sign
comparison_status
```

### 9.2 Improvement formulas

```text
nonlinear_auc_delta(feature_set) =
  sklearn_hgb_fold_mean_auc(feature_set) - logistic_fold_mean_auc(feature_set)

nonlinear_uplift_delta(feature_set) =
  sklearn_hgb_fold_mean_winner_uplift_topN(feature_set) - logistic_fold_mean_winner_uplift_topN(feature_set)

nonlinear_utility_delta_50bps(feature_set) =
  sklearn_hgb_fold_mean_utility_proxy_50bps(feature_set) - logistic_fold_mean_utility_proxy_50bps(feature_set)
```

主对照固定使用 `feature_set = augmented_feature_set`。

## 10. Sample Uniqueness / Overlap Audit

13E 必须复用 13C 的 exact event-span uniqueness 重建逻辑，并在每个 fold 的 purged / embargoed train_k 事件集合内重新计算 fold-local overlap readout 与 sample weight。13E 不得把 daily H20 events 当作独立样本，也不得把 full-train overlap、test_k overlap 或跨 fold overlap 信息注入当前 fold 的训练 sample weight。

必须输出：

```text
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/train_kfold_uniqueness_audit.csv
```

字段：

```text
state_id
fold_id
event_n
t1_reconstruction_status
purged_rows_n
embargoed_rows_n
effective_train_event_n
effective_test_event_n
train_mean_average_uniqueness
train_median_average_uniqueness
train_p10_average_uniqueness
train_mean_concurrency
train_p95_concurrency
test_mean_average_uniqueness
test_mean_concurrency
sample_uniqueness_gate_status
```

`sample_uniqueness_gate_status` 取值：

```text
pass_with_exact_t1                 # 全 fold 都用 fold-local exact t1 重建且 purge/embargo/min effective support 生效
purged_cv_integrity_caveat         # exact t1 可用但某 fold purge/embargo 后 effective_train_event_n 或 effective_test_event_n 过低
exact_uniqueness_unavailable       # exact t1 不可重建
```

任一 fold 为 `exact_uniqueness_unavailable` 时，13E 不得给出 diagnostic positive readout，状态为：

```text
13E_stop_uniqueness_unavailable_for_downstream
```

任一 fold 为 `purged_cv_integrity_caveat` 时，13E 不得给出 diagnostic positive readout；该状态说明 train-only CV 支撑不足，不允许把后续 AUC / uplift / utility readout 解释为稳定非线性容量信号，最终状态必须为：

```text
13E_blocked_purged_cv_integrity_failure
```

## 11. Decision Gates

13E gate statuses:

```text
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
nonlinear_model_availability_gate_status
purged_cv_integrity_gate_status
nonlinear_auc_improvement_gate_status
nonlinear_uplift_improvement_gate_status
nonlinear_utility_proxy_gate_status
sample_uniqueness_gate_status
search_accounting_status
```

### 11.1 Gate pass requirements

`purged_cv_integrity_gate_status = pass` requires：

```text
所有 fold 都记录 purge_window_sessions = 20、embargo_sessions = 20、purge_group_unit = instrument、embargo_scope = global_calendar_session；
所有 fold 都在 purged/embargoed train_k 内重新计算 exact event-span uniqueness sample weight；
所有 fold 都满足 effective_train_event_n >= min_effective_train_event_n_per_fold；
所有 fold 都满足 effective_test_event_n >= min_effective_test_event_n_per_fold；
sample_uniqueness_gate_status = pass_with_exact_t1；
没有任何 fold 使用 validation / robustness 数据。
```

`nonlinear_auc_improvement_gate_status = pass` requires（augmented_feature_set 上）：

```text
nonlinear_auc_delta > auc_improvement_min      # config, default 0.005
fold-mean sklearn_hgb AUC 改善方向在多数 fold（>= 3/5）一致
```

`nonlinear_uplift_improvement_gate_status = pass` requires：

```text
nonlinear_uplift_delta > 0
fold-mean sklearn_hgb winner_uplift_topN 改善方向在多数 fold（>= 3/5）一致
```

`nonlinear_utility_proxy_gate_status = pass` requires（这是本需求的硬经济 gate）：

```text
sklearn_hgb fold_mean_utility_proxy_50bps(augmented) > 0
AND nonlinear_utility_delta_50bps(augmented) > 0
AND sklearn_hgb fold_mean_utility_proxy_50bps(augmented) - fold_std_utility_proxy_50bps(augmented) > 0
```

最后一条要求 fold-mean 减一个 fold-std 仍为正，避免单 fold 主导的伪正向 utility。

`nonlinear_utility_proxy_gate_status = probability_only_no_utility` if：

```text
nonlinear_auc_improvement_gate_status = pass
AND nonlinear_uplift_improvement_gate_status = pass
AND nonlinear_utility_proxy_gate_status hard condition fails
```

### 11.2 Fail statuses

Use specific fail statuses:

```text
13E_blocked_input_or_lineage_failure
13E_blocked_upstream_13c_lineage_failure
13E_blocked_upstream_13c_already_authorized
13E_blocked_label_lineage_failure
13E_blocked_row_level_rebuild_failure
13E_blocked_nonlinear_model_unavailable
13E_blocked_purged_cv_integrity_failure
13E_stop_no_nonlinear_auc_improvement
13E_stop_no_nonlinear_uplift_improvement
13E_stop_nonlinear_auc_improvement_no_utility
13E_stop_uniqueness_unavailable_for_downstream
13E_diagnostic_nonlinear_train_utility_signal_present
```

## 12. Search / Multiplicity Accounting

13E 是 13C stop 之后的 train-only diagnostic。它必须被显式标记为 non-confirmatory，且明确 validation / robustness 从未在本需求中被读取。

必须输出：

```text
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/search_multiplicity_audit.csv
```

字段：

```text
selected_state_id
posthoc_after_13c_report
validation_used_in_13e
robustness_used_in_13e
feature_set_n
model_family_n
target_n
fold_n
effective_search_space_n
hyperparameter_search_used
fold_internal_tuning_used
early_stopping_used
oos_used_for_selection
confirmatory_status
search_accounting_status
```

Default:

```text
selected_state_id = repair_range_participation_core_30
posthoc_after_13c_report = true
validation_used_in_13e = false
robustness_used_in_13e = false
feature_set_n = 2
model_family_n = 2
target_n = 1
fold_n = 5
hyperparameter_search_used = false
fold_internal_tuning_used = false
early_stopping_used = false
oos_used_for_selection = false
confirmatory_status = false
search_accounting_status = diagnostic_train_only_not_confirmatory
```

13E positive result 只能报告为 train-only diagnostic signal。它不能授权 regime-aware meta-labeling feasibility requirement；不能触碰 validation / robustness；不能被报告为可部署 edge、OOS edge、后续推进依据或训练依据。

## 13. Decision Precedence

Decision precedence is strict:

1. Input / PIT / schema / lineage failure:

```text
13E_blocked_input_or_lineage_failure
```

2. Upstream 13C lineage failure 或 13C 已授权下游:

```text
13E_blocked_upstream_13c_lineage_failure
13E_blocked_upstream_13c_already_authorized
```

3. Label lineage failure:

```text
13E_blocked_label_lineage_failure
```

4. Row-level rebuild failure（含 train event 不足）:

```text
13E_blocked_row_level_rebuild_failure
```

5. 非线性模型不可用:

```text
13E_blocked_nonlinear_model_unavailable
```

6. Purged CV integrity failure:

```text
13E_blocked_purged_cv_integrity_failure
```

7. 非线性模型相对线性 baseline 没有 AUC 改善:

```text
13E_stop_no_nonlinear_auc_improvement
```

8. 非线性模型有 AUC 改善但没有 winner uplift 改善:

```text
13E_stop_no_nonlinear_uplift_improvement
```

9. 非线性模型有 AUC / uplift 改善但不转化为 after-cost utility proxy:

```text
13E_stop_nonlinear_auc_improvement_no_utility
```

10. Exact uniqueness 不可用且下游无法要求 exact t1 rebuild:

```text
13E_stop_uniqueness_unavailable_for_downstream
```

11. 全部主 diagnostic gate 通过:

```text
13E_diagnostic_nonlinear_train_utility_signal_present
```

No decision may be upgraded by a prettier non-selected state. 13E 固定只测预注册 selected state；不得在看到结果后更换 state 或 feature set。13E 也不得因 sklearn_hgb 在 baseline_feature_set 上的偶发改善而产生任何授权。Diagnostic positive readout 必须基于 augmented_feature_set 上的主对照，但仍然 `next_allowed_requirement = none`。

## 14. Final Decision Output

必须输出：

```text
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/nonlinear_winner_train_kfold_feasibility_decision.csv
```

字段：

```text
decision_state
next_allowed_requirement
sequence_mining_authorized
meta_labeling_authorized
bet_sizing_authorized
selected_state_id
effect_interpretation
confirmatory_status
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
nonlinear_model_availability_gate_status
purged_cv_integrity_gate_status
nonlinear_auc_improvement_gate_status
nonlinear_uplift_improvement_gate_status
nonlinear_utility_proxy_gate_status
sample_uniqueness_gate_status
validation_used_in_13e
robustness_used_in_13e
search_accounting_status
primary_failure_reason
train_kfold_capacity_readout
```

`train_kfold_capacity_readout` 取值：

```text
nonlinear_capacity_signal_absent               # 非线性无 AUC 改善或无 winner uplift 改善
nonlinear_auc_only_signal                       # 非线性改善 AUC / uplift，但不改善 utility
nonlinear_train_utility_proxy_signal_present    # 非线性同时改善 AUC / uplift / train k-fold utility proxy
```

Allowed diagnostic positive readout:

```text
decision_state = 13E_diagnostic_nonlinear_train_utility_signal_present
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
effect_interpretation = train_kfold_nonlinear_diagnostic_only
train_kfold_capacity_readout = nonlinear_train_utility_proxy_signal_present
```

All decisions, including diagnostic positive and negative decisions:

```text
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
```

Report 输出：

```text
outputs/publishable/reports/nonlinear_winner_train_kfold_feasibility_diagnostic_report.md
```

Manifest 输出：

```text
outputs/manifests/13E_nonlinear_winner_train_kfold_feasibility_diagnostic_manifest.json
```

## 15. Report Requirements

报告必须用中文写，并包含：

1. 单行裁决：非线性模型表达力是否改善 selected-state winner 的 train k-fold AUC / uplift / after-cost utility proxy，以及该读数为何只是 diagnostic-only。
2. 为什么 13E 不推翻 13C：13C 否决的是 selected-state residual utility hard gate；13E 只检查“换成非线性树模型 + train purged k-fold 是否改善”，且全程不碰 validation / robustness。
3. Train-only 边界声明：明确 validation / robustness 在本需求中从未被读取，本结论不是 OOS 验证。
4. Purged k-fold 设计：fold 划分、purge_window_sessions、embargo_sessions、event-span uniqueness sample weight、每 fold 的 purged/embargoed 行数。
5. Logistic vs sklearn_hgb 主对照（augmented_feature_set）：fold-mean AUC、winner uplift、utility proxy（0 / 50 / 100bps）及其 delta 与 fold-std。
6. Baseline vs augmented 辅对照：在两个模型族下，加入 compression / position / participation 是否改善。
7. Utility proxy caveat：`utility_proxy` 是 test fold 内 top-N 排序的乐观上界，decision 只用 fold-mean delta 的符号与 fold-mean 减一 fold-std 的稳健性，不用 absolute 水平。
8. AUC/uplift vs utility 区分：若非线性改善 AUC / uplift 但不改善 after-cost utility proxy，必须明确这是 `probability_only_no_utility`，并据此给出 `13E_stop_nonlinear_auc_improvement_no_utility`；若 AUC 通过但 uplift 不通过，必须给出 `13E_stop_no_nonlinear_uplift_improvement`。
9. Sample uniqueness / overlap audit：每 fold 的 exact t1 状态、train/test 平均 uniqueness、concurrency、effective_train_event_n、effective_test_event_n。
10. 若 diagnostic positive，明确它仍不授权 regime-aware meta-labeling feasibility、不授权 13B、不授权 bet sizing、不产生任何 next requirement；它只能作为人工讨论线索。
11. 若 negative，明确是以下哪类失败：
   - no nonlinear AUC improvement；
   - nonlinear AUC improvement without winner uplift improvement；
   - nonlinear AUC / uplift improvement without after-cost utility translation；
   - purged CV integrity failure；
   - uniqueness / event-span 不可审计。
12. Diagnostic readout：把 `train_kfold_capacity_readout` 写清楚，作为人工讨论线索；不得把它写成 13C OOS failure 的归因结论或后续推进依据。

报告必须避免以下措辞：

```text
alpha discovered
deployable strategy
confirmed edge
out-of-sample validated
sequence mining ready
bet sizing ready
```

## 16. Test Requirements

必须实现 synthetic tests，不依赖大文件：

1. `test_path_resolution_contract`
   确认 `topics/`、`data/`、`experiments/`、`outputs/` 路径解析规则。

2. `test_upstream_13c_stop_decision_required`
   若 13C 已授权 meta-labeling / sequence mining，13E 必须 blocked。

3. `test_train_only_no_oos_access`
   runner 在任何阶段都不得读取 split_bucket in {validation, robustness} 的行；decision table 必须 `validation_used_in_13e = false`、`robustness_used_in_13e = false`。

4. `test_no_report_text_reconstruction`
   runner 不得从 report markdown 解析逐行 event membership。

5. `test_selected_state_membership_reproduction`
   selected state membership 必须来自 verified cache 或 raw rebuild；聚合 readout 不可作为 row truth。

6. `test_frozen_buckets_not_refit`
   bucket thresholds 必须沿用 13C train-frozen 值，不得在 13E 重 fit。

7. `test_purged_kfold_removes_overlap`
   synthetic 中若 test fold 与 train fold 在同一 instrument 上有重叠 event_span，purge 后这些 train 行必须被剔除。

8. `test_embargo_applied`
   synthetic 中落入 test fold 全局 calendar-session 时间边界 embargo 窗口的 train 行必须被剔除，即使 instrument 不同也必须剔除。

9. `test_fold_local_uniqueness_sample_weight_applied`
   fold 内训练必须在 purged/embargoed train_k 内重新计算 exact event-span average_uniqueness 作为 sample weight；若 sample weight 来自 full-train、包含 test_k 或缺失，必须 fail。

10. `test_sklearn_hgb_required_no_logistic_fallback`
    `sklearn.ensemble.HistGradientBoostingClassifier` 不可用时必须 `13E_blocked_nonlinear_model_unavailable`，不得用 logistic 冒充非线性对照后给出 diagnostic positive readout。

11. `test_no_hyperparameter_search`
    两个模型族必须使用预注册固定超参；`hyperparameter_search_used = false`、`fold_internal_tuning_used = false`、`early_stopping_used = false`。

12. `test_auc_only_improvement_cannot_emit_positive_readout`
    sklearn_hgb AUC / uplift 改善但 utility proxy gate 不通过时，必须 `13E_stop_nonlinear_auc_improvement_no_utility`，不得给出 diagnostic positive readout。

13. `test_utility_gate_requires_mean_minus_std_positive`
    若 sklearn_hgb fold_mean_utility_proxy_50bps 为正但 fold_mean 减一 fold_std 为负，utility gate 不得 pass。

14. `test_no_nonlinear_improvement_stop`
    sklearn_hgb 相对 logistic 无 AUC 改善时，必须 `13E_stop_no_nonlinear_auc_improvement`，且 `train_kfold_capacity_readout = nonlinear_capacity_signal_absent`。

15. `test_no_uplift_improvement_stop`
    sklearn_hgb 相对 logistic 有 AUC 改善但无 winner_uplift_topN 改善时，必须 `13E_stop_no_nonlinear_uplift_improvement`，且不得给出 `probability_only_no_utility` 或 diagnostic positive readout。

16. `test_effective_fold_support_blocks_positive`
    任一 fold 的 `effective_train_event_n < min_effective_train_event_n_per_fold` 或 `effective_test_event_n < min_effective_test_event_n_per_fold` 时，必须 `13E_blocked_purged_cv_integrity_failure`，不得输出 diagnostic positive readout。

17. `test_decision_precedence`
    上游 failure 优先于所有 fold-level positive readout。

18. `test_no_bet_sizing_authorization`
    任何 13E decision 都必须 `bet_sizing_authorized = False`。

19. `test_no_sequence_mining_authorization`
    任何 13E decision 都必须 `sequence_mining_authorized = False`。

20. `test_no_state_or_feature_swap`
    runner 不得在看到 fold 结果后更换 selected state 或 feature set；diagnostic positive readout 必须基于 augmented_feature_set 主对照。

21. `test_diagnostic_positive_readout`
    augmented 主对照同时通过 AUC / uplift / utility gate 时，必须 `13E_diagnostic_nonlinear_train_utility_signal_present` 且 `train_kfold_capacity_readout = nonlinear_train_utility_proxy_signal_present`，同时 `next_allowed_requirement = none`、`meta_labeling_authorized = False`。

22. `test_search_accounting_non_confirmatory`
    `search_accounting_status = diagnostic_train_only_not_confirmatory`、`confirmatory_status = false`。

## 17. Implementation Order

建议实现顺序：

1. Parse config and resolve paths.
2. Load upstream 13C decision, manifest, and lineage tables; assert 13C stop state.
3. Reuse or rebuild row-level native panel; filter to train + selected-state membership.
4. Verify 13C feature clusters and train-frozen buckets (no refit).
5. Reconstruct exact event-span offsets and per-event average uniqueness on train events.
6. Build chronological purged + embargoed k-fold assignment within train.
7. For each (model_family, feature_set, fold): fit on purged/embargoed train_k with uniqueness sample weight, score test_k, compute AUC / logloss / winner uplift / utility proxy.
8. Aggregate fold-mean and fold-std per (model_family, feature_set).
9. Compute nonlinear vs linear deltas on augmented_feature_set (main) and baseline (aux).
10. Compute train k-fold uniqueness audit per fold.
11. Apply decision gates and decision precedence.
12. Write publishable tables, report, manifest, and tests.

No step may read validation / robustness rows, refit 13C frozen buckets, search hyperparameters, use early stopping, or swap the selected state / feature set after seeing fold results.
