# 需求：13F Early-Path Confirmation Delayed-Entry Train Diagnostic

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、entry executability 不可证明、early-path window 不可证明、label horizon completeness 不可证明、feature availability 不可证明时 fail closed。
6. 不得从报告文本、图像或人工讨论文本反推出逐行 universe、标签、token、split 边界、entry 价格、early-path、event membership、decision point 或 path outcome。

## 1. 实验身份

```text
experiment_id = 13_full_pit_native_event_discovery_v0
phase_id = 13F
run_id = 13F_early_path_confirmation_delayed_entry_train_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_13f_early_path_confirmation_delayed_entry_train_diagnostic.py
expected_config = configs/config_13f_early_path_confirmation_delayed_entry_train_diagnostic.yaml
expected_test_file = tests/test_13f_early_path_confirmation_delayed_entry_train_diagnostic.py
upstream_requirement_13a = EXPERIMENT_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_13a3 = EXPERIMENT_ROOT/requirement_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.md
upstream_requirement_13c = EXPERIMENT_ROOT/requirement_13c_morphology_orthogonal_residual_importance_diagnostic.md
upstream_requirement_13e = EXPERIMENT_ROOT/requirement_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.md
upstream_report_13c = EXPERIMENT_ROOT/outputs/publishable/reports/morphology_orthogonal_residual_importance_diagnostic_report.md
upstream_report_13e = EXPERIMENT_ROOT/outputs/publishable/reports/nonlinear_winner_train_kfold_feasibility_diagnostic_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13F 是 13E 之后的新 train-only diagnostic 分支。它不推翻 13C / 13E，也不复活 t0-entry winner search。13C / 13E 的相关裁决为：

```text
13C: decision_state = 13C_stop_residual_probability_only_no_utility
13E: decision_state = 13E_stop_no_nonlinear_auc_improvement
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
```

上游链条（09 / 11 / 12 / 13）已反复证明：在 **t0 截面**（event 触发当日的下一可执行 open）进场时，selected event / state 有 winner lift，但 after-cost utility ≈ 0 或为负，且 failure-side 信号是 auc-only、不转化为 OOS utility。13F 不再在 t0 截面找 entry edge。13F 回答一个 lifecycle 上游被跳过的 Confirmation 环节问题：

```text
若 event 触发后不在 t0 立即进场，而是先观察 early_path_k 个 session 的已实现路径，
再决定是否进场，则“event + early-path-confirmed delayed entry”的 train-fold after-cost utility
是否优于“t0 直接进场”（13C 已证明 t0 entry utility ≈ 0）？
```

13F 是 train-only diagnostic：它不碰 validation / robustness，不授权任何下游 requirement、meta-labeling、bet sizing 或 sequence mining。它只判断“是否存在值得人工讨论的 delayed-entry confirmatory 线索”。任何 13F decision 都必须固定：

```text
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
```

## 2. 核心问题

13F 回答以下问题：

```text
Q1. 在 selected event repair_range_participation_core_30 触发后，
    把进场时点从 t0 推迟到 t0 + early_path_k，是否提高 train-fold after-cost utility？

Q2. 提高（若有）主要来自“延迟本身剔除了早期失败样本”（纯门控），
    还是来自“early-path realized features 能区分后续 continuation”（realized-path 模型）？

Q3. 延迟进场是否同时损失 winner（早期就涨上去、延迟后错过的样本），
    即 delayed entry 的 utility 改善是否被 missed-winner 抵消？

Q4. 上述结论对 early_path_k 与 label horizon 口径是否稳健，
    还是只在个别 k 或个别 horizon 口径下成立？

Q5. 在严格 train-only / non-confirmatory 边界下，是否存在一个延迟进场 utility 读数，
    值得开一份独立 confirmatory requirement，而不是作为推进或部署依据？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

13F 明确不是：

```text
13B sequence mining
t0 winner entry retry
new native token / state search
barrier / label k_up / k_dn retuning
meta-labeling model training for deployment
probability calibration for sizing
bet sizing
holding / exit / profit-protection policy
portfolio backtest
cost model calibration
out-of-sample confirmatory test on validation / robustness
```

13F 允许做的只有：

```text
1. 复用 13C 已构建的 morphology_residual_panel，仅取 split == train 且 selected event membership 的行；
2. 对每个 train event，从 qfq daily bars 重建 t0 .. t0 + early_path_k 的已实现 early path；
3. 构造 delayed-entry execution（t0 + early_path_k 的 next executable open）与 delayed-entry label / utility；
4. 构造 early-path realized features（只用 t0+1 .. t0+early_path_k 的已实现数据）；
5. 在 train split 内用 purged / embargoed event-span k-fold，比较：
   (a) t0 baseline entry，(b) 纯门控 delayed entry，(c) realized-path 模型 delayed entry；
6. 输出 diagnostic-only readout；所有 decision 都不得授权下一份 requirement 或 meta-labeling。
```

13F 不得产生任何交易、仓位、生产、alpha、meta-labeling 或后续 requirement 授权声明。即使 diagnostic positive，也只能作为人工讨论线索。

## 4. 继承边界

### 4.1 允许继承

13F 可以继承：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date (t0 reference)
t0_entry_date = next executable open after reference_date
t0_entry_price = qfq open at t0_entry_date
selected_label_id = vol20d_kup2p0_kdn1p0_H20
selected_event / selected_state = repair_range_participation_core_30
native opportunity universe definition from 13A
13A / 13A2 / 13A3 train-frozen thresholds and required state dictionary
split boundary from 12A7g / 13A / 13C
13C feature cluster definitions and train-frozen buckets (only for t0-level context features)
13C exact event-span uniqueness reconstruction (event_touch_offsets / exact_uniqueness)
cost_buffer_grid from 13A3 / 13C
reference_cost_buffer_return = 0.0100 unless upstream lineage proves otherwise
```

13F 必须读取 13C / 13E lineage：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_orthogonal_residual_importance_decision.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/feature_cluster_dictionary.csv
outputs/local_cache/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_residual_panel.parquet
outputs/manifests/13C_morphology_orthogonal_residual_importance_diagnostic_manifest.json
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/nonlinear_winner_train_kfold_feasibility_decision.csv
```

Cache 校验项与 13E 同（row key uniqueness、coverage、split boundary equality、selected event membership equality、frozen bucket equality、schema hash）。校验失败时必须从 raw PIT universe 与 qfq daily bars 重建；不得 fail open。

### 4.2 禁止继承 / 禁止主张

13F 明确不得：

- 不在 t0 截面重新搜索 winner / failure entry edge；
- 不更换 selected event / state；
- 不 retune k_up / k_dn / horizon_sessions / same_bar_priority；
- 不使用 validation / robustness 任何数据来 fit、选择、调参、阈值选择或读数；
- 不做 hyperparameter search 或 fold-internal 超参调优；
- 不用 t0 之后、但晚于 t0 + early_path_k 的任何数据构造 early-path features（禁止 look-ahead）；
- 不让 early-path window 与 label horizon window 重叠（见 §6）；
- 不做 probability calibration、bet sizing、holding / exit policy；
- 不把 train-fold utility positive 解释为 OOS edge 或可部署 edge；
- 不在看到结果后更换预注册主对照 k / horizon 口径。

13F 不能主张：

```text
delayed entry is deployable alpha
13C / 13E decision was wrong
out-of-sample edge confirmed
holding / sizing policy validated
```

13F 只能主张：

```text
event + early-path-confirmed delayed entry does / does not improve train-fold after-cost utility
over t0 direct entry on the selected event, under a strictly PIT early-path window. Any positive
result is train-only diagnostic and only justifies considering a separate confirmatory requirement.
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

同 13A / 13C / 13E：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq daily `reference_pos`、`t0_entry_pos`，以及每个 `early_path_k` 的 `delayed_entry_pos`。任一 delayed entry 的 executable open 或 label horizon bars 不可证明时该 (row, k) not evaluable；全局 schema / PIT 失败时 fail closed。

### 5.2 Upstream decision requirements

13F 要求 13C 与 13E decision table 满足：

```text
13C: input_gate_status = pass, row_level_rebuild_gate_status = pass,
     decision_state = 13C_stop_residual_probability_only_no_utility,
     selected_state_id = repair_range_participation_core_30,
     meta_labeling_authorized = False, bet_sizing_authorized = False
13E: purged_cv_integrity_gate_status = pass,
     row_level_rebuild_gate_status = pass,
     decision_state = 13E_stop_no_nonlinear_auc_improvement,
     selected_state_id = repair_range_participation_core_30,
     validation_used_in_13e = false, robustness_used_in_13e = false,
     meta_labeling_authorized = False, bet_sizing_authorized = False
```

若任一上游 lineage / row-level audit 未通过，13F 必须 fail closed：

```text
13F_blocked_upstream_lineage_failure
```

### 5.3 Label lineage

13F 必须沿用 selected label 公式，但允许把 entry anchor 从 t0 平移到 delayed entry（见 §7）：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_id = volatility_20d
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
```

13F 不得 retune `k_up`、`k_dn`、`horizon_sessions` 或 same-bar priority。barrier 阈值仍由 t0-reference 的 `volatility_20d` 决定（与 13C 一致），不得用 delayed-entry 当日的 vol 重算 barrier（避免引入 t0 之后的信息进入 barrier 定义）。若 label formula / vol reference / split boundary 不可证明，状态为：

```text
13F_blocked_label_lineage_failure
```

## 6. PIT Early-Path / Delayed-Entry 构造（核心防泄漏约束）

### 6.1 时间轴定义

对每个 train event 与每个 `early_path_k`：

```text
reference_pos        = t0 reference row position (PIT)
t0_entry_pos         = reference_pos + 1 (next executable open) = t0 baseline entry
early_path_window    = bars at positions [t0_entry_pos .. t0_entry_pos + early_path_k - 1]
delayed_entry_target_pos = t0_entry_pos + early_path_k
delayed_entry_pos    = next executable open at or after delayed_entry_target_pos
delayed_label_window_from_entry =
  bars at positions [delayed_entry_pos .. delayed_entry_pos + horizon_sessions - 1]
  # delayed entry is executed at delayed_entry_pos open; the same session high/low/close
  # is post-entry path and belongs to the delayed label window.
```

硬约束（任一违反则该 (row, k) not evaluable，且若系统性违反则 fail closed）：

```text
1. early-path features 只能用 early_path_window 内（含端点）的已实现 bars；
2. delayed_label_window 必须严格晚于 early_path_window，二者不得重叠；允许 delayed_label_window
   从 delayed_entry_pos 当日开始，因为成交发生在 open，之后的 high/low/close 属于入场后路径；
3. delayed_entry_pos 必须是真实可执行 open（停牌 / 涨跌停一字不可成交时顺延或标记 not_executable）；
4. barrier 阈值用 t0-reference volatility_20d，不得用 early-path 或 delayed-entry 当日 vol；
5. 全部 position 映射必须来自 qfq daily bars 与 PIT executable membership，不得来自报告文本。
```

### 6.2 Early-path realized features（只允许已实现数据）

预注册 early-path 特征集（全部由 early_path_window 内已实现 bars 计算，train-frozen 标准化）：

```text
early_path_cum_return            # delayed_entry vs t0_entry 的累计收益
early_path_max_favorable_excursion
early_path_max_adverse_excursion
early_path_realized_volatility
early_path_up_day_fraction
early_path_close_position_in_range
early_path_volume_trend
early_path_touched_lower_barrier_flag   # 早期是否已触及/接近下轨（fast-fail 早兆）
early_path_touched_upper_barrier_flag   # 早期是否已触及上轨（早涨）
```

不得引入 early_path_window 之外的数据；不得引入 13C 未冻结的 t0 截面新特征。`early_path_cum_return` 是 realized-path 特征和 missed-winner / opportunity-cost audit 字段，不得被直接加进 delayed-entry strategy utility。t0-level context 可复用 13C feature clusters，但仅作为 realized-path 模型的可选辅助列，且必须标注为 t0-only、不含未来信息。

### 6.3 Missed-winner / early-exit 会计

延迟进场会丢失“在 early_path_window 内就已触及上轨”的样本。13F 必须显式记录这部分，以免高估延迟收益：

```text
missed_upper_in_window_n   = 早期窗口内已触及上轨、被延迟规则排除的 events
early_lower_in_window_n    = 早期窗口内已触及下轨的 events
delayed_evaluable_n        = 仍可在 delayed_entry 进场并有完整 label horizon 的 events
missed_upper_opportunity_cost_50bps =
  t0 baseline 在 missed_upper events 上的 realized utility contribution
  - delayed arm 在同一 events 上的 utility contribution（通常为 0 持仓）
```

Delayed-entry strategy utility 必须遵守“延迟后才持仓”的资金口径：early_path_window 内尚未进场，持仓收益为 0；窗口内价格变化只能作为 feature / missed-winner opportunity cost audit，不得并入 delayed strategy utility。t0 baseline 与 delayed arm 必须在“同一批 events、同一分母”下比较：未进场、not-executable、missed-upper、early-lower 样本均保留在分母内；delayed arm 对未持仓样本记 0 持仓收益，并在 missed-winner audit 中单独说明机会成本。

## 7. Entry Variants 与 Label / Utility

### 7.1 三个对照臂

```text
arm_t0_baseline          # 所有 event 在 t0_entry 等权进场（13C 已证 utility ≈ 0）
arm_gate_delayed         # 纯门控：early_path_window 内未触发 fast-fail-early 才在 delayed_entry 进场
arm_model_delayed        # realized-path 模型：用 early-path features 打分，top 分位才在 delayed_entry 进场
```

`arm_gate_delayed` 的门控规则预注册为：

```text
进场条件 = NOT early_path_touched_lower_barrier_flag
（即早期窗口内未触及下轨；可在 config 增加 early_path_cum_return >= 0 作为 sensitivity，但主对照只用 lower-barrier 门控）
```

`arm_model_delayed` 模型预注册：

```text
model = logistic_l2 (沿用 13C/13E 超参) 主对照
optional secondary = sklearn_hgb_low_capacity (沿用 13E 超参，仅 sensitivity)
target = delayed_winner_positive
top_fraction = 0.50 (config; 与门控臂的保留比例量级可比，sensitivity 可加 0.30)
禁止 hyperparameter search / fold-internal tuning / early stopping
```

### 7.2 Delayed label / utility

```text
delayed_winner_positive / delayed_lower_first / delayed_fast_fail
  = triple-barrier outcome computed on delayed_label_window
delayed_row_utility_component_{0,50,100}bps
  = 1[delayed_upper_first]*upper_barrier
    - 1[delayed_lower_first]*abs(lower_barrier)
    - cost_buffer_return

delayed_arm_per_event_utility_{0,50,100}bps
  = 1[selected_for_delayed_entry AND delayed_entry_executable]
    * delayed_row_utility_component_{0,50,100}bps
  + 1[not selected_for_delayed_entry OR not executable] * 0

t0_baseline_per_event_utility_{0,50,100}bps
  = original t0 row_utility_component_{0,50,100}bps from the same event denominator
```

### 7.3 Horizon 口径（两种，均输出）

```text
horizon_mode_from_entry   # 主对照：delayed entry 后重新计满 horizon_sessions = 20
horizon_mode_calendar_t0  # sensitivity：固定日历终点 = t0_entry_pos + 20，delayed 后 horizon 被压缩
```

主对照固定 `horizon_mode_from_entry`；`horizon_mode_calendar_t0` 仅作 sensitivity，不得单独触发 positive。

```text
from_entry label positions:
  [delayed_entry_pos .. delayed_entry_pos + horizon_sessions - 1]

calendar_t0 label positions:
  [delayed_entry_pos .. t0_entry_pos + horizon_sessions - 1]
  若 delayed_entry_pos > t0_entry_pos + horizon_sessions - 1，则该 (row, k, horizon_mode)
  不可评价，不得静默丢弃。
```

## 8. Purged / Embargoed Train K-Fold Protocol

13F 的全部评估都在 train split 内部进行，validation / robustness 不参与。Fold 构造沿用 13E 协议：

```text
fold_n = 5 (config)
fold_assignment = chronological contiguous blocks by reference_date within train
event_span_i =
  [t0_entry_pos_i, max_observable_event_end_pos_i]
max_observable_event_end_pos_i =
  max(
    t0_entry_pos_i + original_t0_touch_or_vertical_offset_i,
    max delayed_label_end_pos_i across all pre-registered early_path_k and horizon modes
  )
purge_window_sessions = 20
embargo_sessions = 20
purge_group_unit = instrument
embargo_scope = global_calendar_session
min_effective_train_event_n_per_fold = 300
min_effective_test_event_n_per_fold = 50
```

Fold 规则与 13E 同（purge 同 instrument 重叠 span；global-session embargo；scaler 只在 train_k fit；bucket 沿用 13C frozen；sample weight 用 purged/embargoed train_k 内重算的 exact event-span average uniqueness；test_k uniqueness 只作 audit）。但 13F 的 exact event-span 必须使用上面的 `max_observable_event_end_pos_i`，不得只使用 t0 baseline 的 first-touch / vertical span；否则 k=5/8/13 的 delayed label future path 会被低估。purge / embargo / fold-local uniqueness / minimum support 缺失任一项时：

```text
13F_blocked_purged_cv_integrity_failure
```

注意：event-span 与 fold 划分仍以 t0 为锚（同一 event 的 t0 / delayed 必须落在同一 fold，不得因延迟跨 fold），避免同一 event 的 t0 与 delayed 版本分属 train/test 造成泄漏。

## 9. Fold-level 指标与对照

### 9.1 每臂 fold 指标

每个 `(arm, early_path_k, horizon_mode, fold)` 在 test_k 上计算：

```text
evaluable_n
selected_n                         # 该臂实际进场的 events 数（t0 臂 = 全部）
winner_rate                        # delayed_winner_positive 均值（t0 臂用 t0 label）
fast_fail_rate
utility_per_event_mean_0bps / 50bps / 100bps
  # 全部 events 等权；未进场 / not-executable 样本计 0 持仓收益
utility_per_selected_entry_mean_50bps
  # 仅实际进场样本的诊断指标，不得用于主 gate
utility_per_event_median_50bps     # robust audit，不得替代主 gate
missed_upper_in_window_n
```

注意 utility 必须在“同一批 events、同口径”下计算：延迟臂未进场的 events 计入 0 持仓收益，不得只在进场子集上平均，也不得把 early_path_window 的未持仓价格变化并入 delayed arm strategy utility。

### 9.2 主对照与 deltas

必须输出：

```text
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/delayed_vs_t0_entry_comparison.csv
```

字段：

```text
early_path_k
horizon_mode
arm
fold_mean_utility_per_event_mean_50bps
fold_std_utility_per_event_mean_50bps
fold_mean_utility_per_selected_entry_mean_50bps
fold_mean_utility_per_event_median_50bps
fold_mean_winner_rate
fold_mean_fast_fail_rate
fold_mean_selected_fraction
fold_mean_missed_upper_fraction
delta_utility_per_event_mean_50bps_vs_t0
delta_utility_per_event_mean_50bps_vs_gate
missed_upper_opportunity_cost_50bps
delta_sign_consistency_folds          # 多数 fold 同号计数
comparison_status
```

Improvement formulas（主对照固定 `early_path_k = 3`、`horizon_mode = horizon_mode_from_entry`、`arm = arm_model_delayed`，对照 `arm_t0_baseline`）：

```text
delayed_utility_mean_delta(k, mode, arm) =
  fold_mean_utility_per_event_mean_50bps(arm, k, mode)
  - fold_mean_utility_per_event_mean_50bps(arm_t0_baseline)

model_vs_gate_utility_mean_delta(k, mode) =
  fold_mean_utility_per_event_mean_50bps(arm_model_delayed, k, mode)
  - fold_mean_utility_per_event_mean_50bps(arm_gate_delayed, k, mode)
```

### 9.3 必需审计表

13F 的时间轴和会计不能只写入报告，必须输出可复核的机器表：

```text
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/row_level_rebuild_audit.csv
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/early_path_rebuild_audit.csv
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/delayed_entry_executability_audit.csv
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/missed_winner_accounting.csv
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/fold_arm_metrics.csv
```

`row_level_rebuild_audit.csv` 最少字段：

```text
selected_state_id
row_count
unique_row_id_count
non_train_row_count
selected_event_membership_mismatch_n
required_column_missing_count
instrument_reference_date_duplicate_n
reference_pos_missing_n
t0_entry_pos_missing_n
report_text_used_as_row_truth
validation_rows_used
robustness_rows_used
row_level_rebuild_gate_status
```

`early_path_rebuild_audit.csv` 最少字段：

```text
early_path_k
row_count
early_path_evaluable_n
early_path_window_start_min_pos
early_path_window_end_max_pos
delayed_entry_target_pos_check_status
label_window_disjoint_status
barrier_uses_t0_volatility_status
lookahead_column_count
early_path_pit_gate_status
```

`delayed_entry_executability_audit.csv` 最少字段：

```text
early_path_k
horizon_mode
evaluable_n
not_executable_n
forward_shifted_entry_n
missing_label_horizon_n
not_executable_fraction
delayed_entry_executability_gate_status
```

`missed_winner_accounting.csv` 最少字段：

```text
early_path_k
horizon_mode
arm
fold_id
event_n
missed_upper_in_window_n
early_lower_in_window_n
missed_upper_fraction
missed_upper_opportunity_cost_50bps
same_event_delta_utility_50bps_vs_t0
selected_entry_only_delta_utility_50bps_vs_t0
missed_winner_offset_gate_status
```

`fold_arm_metrics.csv` 最少字段：

```text
fold_id
early_path_k
horizon_mode
arm
evaluable_n
selected_n
selected_fraction
winner_rate
fast_fail_rate
utility_per_event_mean_0bps
utility_per_event_mean_50bps
utility_per_event_mean_100bps
utility_per_selected_entry_mean_50bps
utility_per_event_median_50bps
missed_upper_in_window_n
early_lower_in_window_n
```

## 10. Sample Uniqueness / Overlap Audit

沿用 13E：每 fold 在 purged/embargoed train_k 内重算 exact event-span uniqueness，但 event span 必须使用 13F 的 `max_observable_event_end_pos_i`。必须输出：

```text
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/train_kfold_uniqueness_audit.csv
```

字段同 13E（state_id、fold_id、event_n、t1_reconstruction_status、purged_rows_n、embargoed_rows_n、effective_train_event_n、effective_test_event_n、train/test uniqueness 与 concurrency、sample_uniqueness_gate_status）。

`sample_uniqueness_gate_status` 取值与 13E 同；任一 fold `exact_uniqueness_unavailable` → `13F_stop_uniqueness_unavailable_for_downstream`；任一 fold `purged_cv_integrity_caveat` → `13F_blocked_purged_cv_integrity_failure`。

## 11. Decision Gates

13F gate statuses:

```text
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
early_path_pit_gate_status
delayed_entry_executability_gate_status
purged_cv_integrity_gate_status
delayed_utility_improvement_gate_status
missed_winner_offset_gate_status
sample_uniqueness_gate_status
search_accounting_status
```

### 11.1 Gate pass requirements

`early_path_pit_gate_status = pass` requires：

```text
所有 (row, k) 的 early-path features 只用 early_path_window 内 bars；
delayed_label_window 与 early_path_window 不重叠；
barrier 阈值用 t0-reference volatility_20d；
没有任何 look-ahead 列。
```

`delayed_entry_executability_gate_status = pass` requires：

```text
主对照 k=3 下，delayed_entry not-executable 比例低于 config 上限（默认 0.10）；
not-executable / 顺延样本被显式记录，不静默丢弃。
```

`purged_cv_integrity_gate_status = pass` requires：与 13E 同（含 min effective fold support、同 event 同 fold）。

`delayed_utility_improvement_gate_status = pass` requires（主对照，这是本需求硬经济 gate）：

```text
arm_model_delayed (k=3, from_entry) fold_mean_utility_per_event_mean_50bps > 0
AND delayed_utility_mean_delta(k=3, from_entry, arm_model_delayed) > 0
AND fold_mean_utility_per_event_mean_50bps
    - fold_std_utility_per_event_mean_50bps > 0
AND delta_sign_consistency_folds >= 3/5
```

`delayed_utility_improvement_gate_status = gate_effect_only_no_model_edge` requires：

```text
arm_gate_delayed 在同一 k=3/from_entry 口径下满足上述硬经济 gate；
AND arm_model_delayed 未满足上述硬经济 gate，或
    model_vs_gate_utility_mean_delta(k=3, from_entry) <= 0
（说明改善来自“延迟剔除早期失败”本身，而非 early-path 模型）。
```

`missed_winner_offset_gate_status = pass` requires：

```text
delayed_utility_mean_delta 使用同一批 events 的全分母 utility；
delayed arm 对 missed_upper / not selected / not executable 样本计 0 持仓收益；
same_event_delta_utility_50bps_vs_t0 > 0；
missed_upper_opportunity_cost_50bps 已单独输出且没有被排除出分母。
```

### 11.2 Fail statuses

```text
13F_blocked_input_or_lineage_failure
13F_blocked_upstream_lineage_failure
13F_blocked_label_lineage_failure
13F_blocked_row_level_rebuild_failure
13F_blocked_early_path_pit_failure
13F_blocked_delayed_entry_not_executable
13F_blocked_purged_cv_integrity_failure
13F_stop_no_delayed_utility_improvement
13F_stop_delayed_improvement_offset_by_missed_winners
13F_stop_uniqueness_unavailable_for_downstream
13F_diagnostic_delayed_entry_utility_signal_present
13F_diagnostic_delayed_gate_effect_only
```

## 12. Search / Multiplicity Accounting

13F 同时扫描 5 个 k × 2 个 horizon × 3 个 arm，必须显式记账并预注册主对照。

必须输出：

```text
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/search_multiplicity_audit.csv
```

字段与默认：

```text
selected_state_id = repair_range_participation_core_30
posthoc_after_13e_report = true
validation_used_in_13f = false
robustness_used_in_13f = false
early_path_k_grid = [2, 3, 5, 8, 13]
horizon_mode_n = 2
arm_n = 3
primary_k = 3
primary_horizon_mode = horizon_mode_from_entry
primary_arm = arm_model_delayed
effective_search_space_n = 30
hyperparameter_search_used = false
oos_used_for_selection = false
confirmatory_status = false
search_accounting_status = diagnostic_train_only_not_confirmatory
```

授权（diagnostic positive）只能基于预注册主对照（k=3, from_entry, model_delayed）。其余 29 个组合仅作 sensitivity readout，不得单独触发 positive，也不得在看到结果后被提升为主对照。

## 13. Decision Precedence

严格优先级：

```text
1. 13F_blocked_input_or_lineage_failure
2. 13F_blocked_upstream_lineage_failure
3. 13F_blocked_label_lineage_failure
4. 13F_blocked_row_level_rebuild_failure
5. 13F_blocked_early_path_pit_failure
6. 13F_blocked_delayed_entry_not_executable
7. 13F_blocked_purged_cv_integrity_failure
8. 13F_stop_uniqueness_unavailable_for_downstream
9. 主 k=3/from_entry 下 arm_gate_delayed 与 arm_model_delayed 均未满足
   same-event utility improvement gate -> 13F_stop_no_delayed_utility_improvement
10. 任一 raw selected-entry improvement 在 same-event denominator / missed-winner
    accounting 后转为非正 -> 13F_stop_delayed_improvement_offset_by_missed_winners
11. arm_gate_delayed 满足 same-event utility improvement gate，但
    arm_model_delayed 无额外改善 -> 13F_diagnostic_delayed_gate_effect_only
12. arm_model_delayed 满足 same-event utility improvement gate，且
    model_vs_gate_utility_mean_delta > 0 -> 13F_diagnostic_delayed_entry_utility_signal_present
```

No decision may be upgraded by a prettier non-primary k / horizon / arm。13F 固定预注册主对照；不得事后换 k、换 horizon 口径或换 arm。

## 14. Final Decision Output

必须输出：

```text
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/early_path_confirmation_delayed_entry_decision.csv
```

字段：

```text
decision_state
next_allowed_requirement
sequence_mining_authorized
meta_labeling_authorized
bet_sizing_authorized
selected_state_id
primary_k
primary_horizon_mode
primary_arm
effect_interpretation
confirmatory_status
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
early_path_pit_gate_status
delayed_entry_executability_gate_status
purged_cv_integrity_gate_status
delayed_utility_improvement_gate_status
missed_winner_offset_gate_status
sample_uniqueness_gate_status
validation_used_in_13f
robustness_used_in_13f
search_accounting_status
primary_failure_reason
delayed_entry_capacity_readout
```

`delayed_entry_capacity_readout` 取值：

```text
delayed_entry_no_utility_signal             # 主对照延迟进场未改善 utility
delayed_entry_offset_by_missed_winners      # 有 raw 改善但被错过早涨抵消
delayed_entry_gate_effect_only              # 仅“延迟剔除早期失败”有用，early-path 模型无额外 edge
delayed_entry_model_utility_signal_present  # 延迟 + early-path 模型同时改善 train-fold utility
```

Allowed diagnostic positive readouts:

```text
decision_state = 13F_diagnostic_delayed_entry_utility_signal_present
  -> delayed_entry_capacity_readout = delayed_entry_model_utility_signal_present
decision_state = 13F_diagnostic_delayed_gate_effect_only
  -> delayed_entry_capacity_readout = delayed_entry_gate_effect_only
```

All decisions（含 diagnostic positive 与 negative）固定：

```text
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
effect_interpretation = train_only_delayed_entry_diagnostic
```

Report 输出：

```text
outputs/publishable/reports/early_path_confirmation_delayed_entry_train_diagnostic_report.md
```

Manifest 输出：

```text
outputs/manifests/13F_early_path_confirmation_delayed_entry_train_diagnostic_manifest.json
```

## 15. Report Requirements

报告必须用中文写，并包含：

1. 单行裁决：event 触发后延迟进场是否改善 train-fold after-cost utility，以及该读数为何只是 diagnostic-only。
2. 为什么 13F 不推翻 13C / 13E：13C/13E 否决的是 t0 winner entry；13F 只检查“延迟到 early-path 确认后进场是否更好”，且全程不碰 validation / robustness。
3. Train-only / PIT 边界声明：明确 validation / robustness 从未读取；明确 early-path window 与 label window 不重叠、barrier 用 t0 vol、无 look-ahead。
4. 时间轴与延迟构造：t0_entry、early_path_window、delayed_entry、delayed_label_window 的定义与每个 k 的 not-executable 比例。
5. 三臂主对照（k=3, from_entry）：arm_t0_baseline vs arm_gate_delayed vs arm_model_delayed 的 same-event fold-mean utility、selected-entry diagnostic utility、median robust audit、winner_rate、fast_fail_rate、selected_fraction、missed_upper_fraction。
6. Missed-winner 会计：延迟错过的早涨 winner 数、opportunity cost、same-event denominator 下的 utility delta，明确改善是否在 missed_upper/not-selected/not-executable 样本保留在分母后仍为正。
7. 门控 vs 模型区分：改善是来自“延迟剔除早期失败”（gate_effect_only）还是“early-path 模型有额外 edge”。
8. Sensitivity：k ∈ {2,3,5,8,13} 与两种 horizon 口径下结论是否稳健，明确哪些组合为正、哪些为负；强调非主对照只作线索。
9. Utility 口径 caveat：主 gate 使用“同一批 events、未进场计 0 持仓”的 fold-mean utility；selected-entry utility 与 median utility 只作诊断，不得替代主 gate。
10. Sample uniqueness：每 fold exact-t1 状态、train/test uniqueness、concurrency、effective support。
11. 若 diagnostic positive，明确它仍不授权任何 requirement、meta-labeling、bet sizing 或 holding policy，只能作为人工讨论线索；下一步若要推进必须另开独立 confirmatory requirement 并在未触碰的 OOS 上验证。
12. 若 negative，明确是以下哪类：无 utility 改善 / 改善被 missed-winner 抵消 / PIT 或 executability 失败 / CV integrity 失败 / uniqueness 不可审计。

报告必须避免以下措辞：

```text
alpha discovered
deployable strategy
confirmed edge
out-of-sample validated
holding policy validated
bet sizing ready
```

## 16. Test Requirements

必须实现 synthetic tests，不依赖大文件：

1. `test_path_resolution_contract`
   确认路径解析规则。

2. `test_upstream_13c_13e_stop_required`
   13C/13E 未处于预期 stop 且 meta_labeling/bet_sizing=false 时，13F 必须 blocked。

3. `test_train_only_no_oos_access`
   runner 不得读取 validation / robustness 行；decision 必须 `validation_used_in_13f=false`、`robustness_used_in_13f=false`。

4. `test_early_path_no_lookahead`
   early-path features 只能用 early_path_window 内 bars；若任何特征引用 window 之外的 bar，必须 fail / `13F_blocked_early_path_pit_failure`。

5. `test_early_path_label_window_disjoint`
   delayed_label_window 与 early_path_window 重叠时必须 fail。

6. `test_barrier_uses_t0_volatility`
   barrier 阈值必须用 t0-reference volatility_20d，不得用 delayed-entry 当日 vol。

7. `test_delayed_entry_executability`
   delayed_entry 落在停牌/一字时必须顺延或标记 not_executable，不得静默用不可成交价。

8. `test_missed_winner_accounting`
   early_path_window 内已触上轨的 events 必须计入 missed_upper_in_window 与 opportunity-cost audit；delayed arm 对这些未持仓样本计 0，但不得从 same-event 分母悄悄移除。

9. `test_utility_same_event_basis`
   延迟臂未进场 events 必须计 0 持仓收益并入同一分母；若只在进场子集平均，或把 early_path_window 未持仓价格变化并入 delayed strategy utility，必须 fail。

10. `test_same_event_same_fold`
    同一 event 的 t0 与 delayed 版本必须落在同一 fold；跨 fold 时必须 fail（防泄漏）。

11. `test_purged_embargo_and_min_support`
    purge/embargo/fold-local uniqueness/min effective support 任一缺失 → `13F_blocked_purged_cv_integrity_failure`；event span 必须覆盖所有预注册 delayed label 的 `max_observable_event_end_pos_i`，不得只用 t0 baseline span。

12. `test_no_hyperparameter_search`
    两个模型臂用预注册固定超参；`hyperparameter_search_used=false`。

13. `test_primary_comparison_fixed`
    主对照固定 k=3 / from_entry / model_delayed；runner 不得事后换主对照。

14. `test_no_delayed_improvement_stop`
    主对照 utility 未改善时 → `13F_stop_no_delayed_utility_improvement`、`delayed_entry_capacity_readout=delayed_entry_no_utility_signal`。

15. `test_missed_winner_offset_stop`
    raw 改善但计入 missed-winner 后转非正时 → `13F_stop_delayed_improvement_offset_by_missed_winners`。

16. `test_gate_effect_only_readout`
    gate_delayed 改善但 model_delayed 无额外 edge 时 → `13F_diagnostic_delayed_gate_effect_only`、`delayed_entry_gate_effect_only`。

17. `test_utility_gate_requires_mean_minus_std_positive`
    fold_mean 减一 fold_std 非正时 utility gate 不得 pass。

18. `test_decision_precedence`
    上游/PIT/executability/CV failure 优先于任何 fold-level positive。

19. `test_no_authorization_invariants`
    任何 13F decision 都必须 `next_allowed_requirement=none`、`meta_labeling_authorized=False`、`bet_sizing_authorized=False`、`sequence_mining_authorized=False`。

20. `test_sensitivity_cannot_override_primary`
    非主对照 k / horizon / arm 看起来更好时，不得改变 decision_state；只能作为 sensitivity readout。

21. `test_diagnostic_positive_readout`
    主对照三 gate（utility improvement + missed-winner offset + model>gate）全过时 → `13F_diagnostic_delayed_entry_utility_signal_present`、`delayed_entry_model_utility_signal_present`，同时 `next_allowed_requirement=none`。

22. `test_search_accounting_non_confirmatory`
    `search_accounting_status=diagnostic_train_only_not_confirmatory`、`confirmatory_status=false`、`effective_search_space_n=30`。

## 17. Implementation Order

建议实现顺序：

1. Parse config and resolve paths.
2. Load upstream 13C / 13E decisions, manifest, lineage; assert stop states.
3. Reuse or rebuild row-level native panel; filter to train + selected event membership.
4. For each event and each early_path_k: reconstruct t0_entry / early_path_window / delayed_entry / delayed_label_window from qfq bars under PIT constraints.
5. Build early-path realized features (window-only) and missed-winner / early-lower accounting.
6. Build delayed label / utility (both horizon modes) with same-event-basis accounting.
7. Build chronological purged + embargoed k-fold (same event same fold) within train.
8. For each (arm, k, horizon_mode, fold): compute selected_n, winner_rate, fast_fail_rate, same-event utility mean, selected-entry diagnostic utility, and median robust audit.
9. Aggregate fold-mean / fold-std; compute delayed-vs-t0 deltas; isolate gate-effect vs model-edge.
10. Compute uniqueness audit per fold using 13F max observable event span, not only t0 baseline span.
11. Apply gates and decision precedence (primary comparison only authorizes readout).
12. Write publishable tables, report, manifest, and tests.

No step may read validation / robustness rows, use look-ahead in early-path features, overlap early-path and label windows, add pre-entry early_path price movement to delayed strategy utility, drop missed-winner events from the utility denominator, split a single event's t0/delayed versions across folds, search hyperparameters, or swap the pre-registered primary comparison after seeing results.
