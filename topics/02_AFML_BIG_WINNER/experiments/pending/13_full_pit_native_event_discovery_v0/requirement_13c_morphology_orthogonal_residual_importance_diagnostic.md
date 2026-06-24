# 需求：13C Morphology-Orthogonal Residual Importance Diagnostic

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
phase_id = 13C
run_id = 13C_morphology_orthogonal_residual_importance_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_13c_morphology_orthogonal_residual_importance_diagnostic.py
expected_config = configs/config_13c_morphology_orthogonal_residual_importance_diagnostic.yaml
expected_test_file = tests/test_13c_morphology_orthogonal_residual_importance_diagnostic.py
upstream_requirement_13a = EXPERIMENT_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_13a2 = EXPERIMENT_ROOT/requirement_13a2_compression_directional_disambiguation_preflight.md
upstream_requirement_13a3 = EXPERIMENT_ROOT/requirement_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.md
upstream_report_13a = EXPERIMENT_ROOT/outputs/publishable/reports/native_token_cartography_preflight_report.md
upstream_report_13a2 = EXPERIMENT_ROOT/outputs/publishable/reports/compression_directional_disambiguation_preflight_report.md
upstream_report_13a3 = EXPERIMENT_ROOT/outputs/publishable/reports/compression_repair_state_cost_and_native_feasibility_diagnostic_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13C 是 13A3 之后的新诊断分支，不是 13A4、不是 13B sequence mining，也不是 meta-labeling 训练。13A3 的正式裁决为：

```text
decision_state = 13A3_selected_composite_state_not_supported
next_allowed_requirement = none
sequence_mining_authorized = False
effect_interpretation = total_native_effect_only
distribution_vs_state_edge_disentanglement_required = True
```

13C 必须尊重该裁决。13C 的目标不是救回 13A3 selected state，而是回答一个更窄的问题：

```text
compression-repair composite state 在剥离 broad drawdown / reversal morphology 后，
是否还存在可审计的 residual information？
```

若 residual information 不存在，13C 必须给出 stop 裁决，并阻止基于 compression-repair 的 meta-labeling / bet sizing / sequence mining。若 residual information 存在，13C 最多授权一份独立的 AFML meta-labeling feasibility preflight；不得直接授权 13B。

## 2. 核心问题

13C 回答以下问题：

```text
Q1. 13A3 selected composite state 与全部 required composite states
    在控制 broad morphology anchors 后，是否仍有 winner / utility residual effect？

Q2. compression / position / participation primitives 的信息是否被
    max_drawdown_20d、distance_to_20d_low、ret_20d 等 broad morphology anchors 完全解释？

Q3. 若使用低容量模型或 clustered MDA，compression-repair feature cluster 是否在
    validation / robustness 中提供稳定、非零、方向一致的 out-of-sample residual importance？

Q4. 若 residual importance 存在，它是否也转化为 cost-adjusted utility margin，
    而不是只表现为 AUC 或 winner-rate 的统计读数？

Q5. Episode 13 是否还有资格进入 meta-labeling feasibility；
    或者应将 compression-repair winner branch 永久降级为 defense / participation 特征研究？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

13C 明确不是：

```text
13B sequence mining
13A3 selected state retry
new native token search
new composite state search
barrier / label retuning
meta-labeling model training
probability calibration
bet sizing
portfolio backtest
cost model calibration
```

13C 允许做的只有：

```text
1. 重建 13A3 required composite state membership；
2. 重建 broad morphology anchors；
3. 构造 morphology-balanced / morphology-residual diagnostic panels；
4. 用预注册低容量模型或 grouped residualization 计算 residual effect；
5. 用 clustered MDA / grouped permutation 计算 feature-cluster residual importance；
6. 输出是否允许下一份 meta-labeling feasibility requirement 的 gate。
```

13C 不得产生任何交易、仓位、生产或 alpha 声明。即使 13C positive，也只能授权：

```text
requirement_13d_compression_repair_meta_labeling_feasibility_preflight.md
```

且该授权必须带有：

```text
sequence_mining_authorized = False
meta_labeling_authorized = True
bet_sizing_authorized = False
```

## 4. 继承边界

### 4.1 允许继承

13C 可以继承：

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
split boundary from 12A7g / 13A / 13A2 / 13A3
cost_buffer_grid from 13A3
reference_cost_buffer_return = 0.0100 unless upstream lineage proves otherwise
moderate_cost_buffer_return = 0.0050
```

13C 必须读取 13A3 publishable artifacts 作为 lineage：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/compression_repair_state_feasibility_decision.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_repair_state_dictionary.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_native_readout.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_badside_utility_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_morphology_independent_evidence_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_denominator_drift_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/cost_buffer_sensitivity_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/row_level_cache_audit.csv
outputs/manifests/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic_manifest.json
```

13C 必须读取 13A / 13A2 lineage artifacts，至少包括：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_morphology_collinearity_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_label_portability_audit.csv
outputs/manifests/13A_full_pit_native_token_cartography_preflight_manifest.json
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_dictionary.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_threshold_freeze_audit.csv
outputs/manifests/13A2_compression_directional_disambiguation_preflight_manifest.json
```

可选使用 13A / 13A2 / 13A3 local cache，但必须校验：

```text
row key uniqueness
instrument x reference_date coverage
split boundary equality
selected label equality
base compression membership equality
required composite state membership equality
primitive value equality for audited columns
sha256 / schema hash when manifest provides it
```

Cache 校验失败时必须从 raw PIT universe 和 qfq daily bars 重建；不得 fail open。

### 4.2 禁止继承 / 禁止主张

13C 明确不得：

- 不使用 C0 active band、C0 thresholds、C0 state-change family formula；
- 不修复 C0 selector 或 `volatility_reconciliation_fail`；
- 不重新选择 winner label；
- 不重新搜索 base compression state；
- 不新增 13A3 required composite states；
- 不用 validation / robustness 选择 feature、anchor、cluster、threshold、model family、decision threshold 或 cost tier；
- 不训练高容量模型；
- 不做 hyperparameter search；
- 不做 probability calibration；
- 不做 sequence mining；
- 不做 bet sizing；
- 不做资金曲线、滑点、容量或交易系统；
- 不把 residual AUC positive 解释为可部署 edge。

13C 不能主张：

```text
compression-repair state is deployable alpha
compression-repair state should enter sequence mining
meta-labeling will make the state profitable
```

13C 只能主张：

```text
compression-repair state has / does not have morphology-orthogonal residual information
worth testing in a separate AFML meta-labeling feasibility requirement.
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

同 13A / 13A2 / 13A3：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq daily `reference_pos` 与 next-open executable `entry_pos`。不可证明时 row-level not evaluable；全局 schema / PIT 失败时 fail closed。

### 5.2 Upstream decision requirements

13C 要求 13A3 decision table 满足：

```text
input_gate_status = pass
upstream_13a_lineage_gate_status = pass
upstream_13a2_lineage_gate_status = pass
cost_sensitivity_gate_status = pass
composite_readout_gate_status = pass
badside_gate_status = pass
utility_gate_status = fail
morphology_independent_evidence_gate_status = fail
decision_state = 13A3_selected_composite_state_not_supported
sequence_mining_authorized = False
selected_state_id = repair_range_participation_core_30
```

若 13A3 已经授权 sequence mining，13C 不应运行，状态为：

```text
13C_blocked_upstream_13a3_already_authorized
```

若 13A3 input / lineage / row-level cache audit 未通过，13C 必须 fail closed：

```text
13C_blocked_upstream_13a3_lineage_failure
```

13C 可以在 13A3 failure 基础上运行；13A3 的 utility / morphology failure 是本需求的研究前提，不是 blocker。

### 5.3 Label lineage

13C 必须沿用 12A7g / 13A / 13A2 / 13A3 的 selected label：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_id = volatility_20d
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
```

13C 不得 retune `k_up`、`k_dn`、horizon 或 same-bar priority。若 label formula、vol reference unit、split boundary 或 label eligibility 不可证明，状态为：

```text
13C_blocked_label_lineage_failure
```

## 6. Row-Level Rebuild

13C 必须重建以下 row-level panel：

```text
morphology_residual_panel(row)
  = 13A native PIT executable denominator
  + selected label fields
  + barrier outcome fields
  + utility barrier return fields
  + 13A3 required composite state membership flags
  + 13A2 directional primitive values used by required states
  + broad morphology anchor primitive values
  + denominator control fields
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
horizon_close_return
row_utility_component_0bps
row_utility_component_25bps
row_utility_component_50bps
row_utility_component_75bps
row_utility_component_100bps
utility_positive_50bps
median_upper_barrier_return_source
median_abs_lower_barrier_return_source
```

13C 必须使用与 13A3 一致的 fast-fail 定义：

```text
FAST_FAIL_MAX_SESSIONS = 3
fast_fail(row) =
  lower_first(row) == true
  and time_to_lower(row) <= FAST_FAIL_MAX_SESSIONS
```

13A3 的 primary aggregate utility 使用 state/split 内 median barrier return。13C 因为要做 row-level residualization，必须额外构造逐行 utility component：

```text
row_utility_component(cost_buffer_return) =
  1[upper_first] * upper_barrier
  - 1[lower_first] * abs(lower_barrier)
  - cost_buffer_return

utility_positive_50bps =
  row_utility_component_50bps > 0
```

13C report 必须同时输出 utility reconciliation caveat：row-level utility component 用于 residualization / model target；13A3 median-barrier aggregate utility 继续作为 lineage readout，不得混作同一个数。

13C 必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/upstream_lineage_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/row_level_rebuild_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/utility_reconciliation_audit.csv
```

`row_level_rebuild_audit.csv` 字段：

```text
audit_id
row_count
unique_row_id_count
instrument_count
split_bucket
horizon_complete_rate
selected_label_match_rate_vs_cache
composite_membership_match_rate_vs_13a3_cache
required_feature_nonnull_rate
status
```

`utility_reconciliation_audit.csv` 字段：

```text
state_id
split_bucket
cost_buffer_return
cost_tier_label
treated_n
row_component_utility_per_entry
row_component_utility_total_indexed
median_barrier_utility_per_entry_from_13a3
median_barrier_utility_total_indexed_from_13a3
per_entry_delta_row_vs_13a3
total_indexed_delta_row_vs_13a3
reconciliation_status
```

`reconciliation_status` 不参与 13C decision gate；它只防止 residualization 使用的 row-level utility component 与 13A3 aggregate utility 被混作同一读数。

若逐行 membership 无法从 raw inputs 或 verified cache 复现，状态为：

```text
13C_blocked_row_level_rebuild_failure
```

## 7. Morphology Anchors and Feature Clusters

### 7.1 Required morphology anchors

13C 必须预注册以下 broad morphology anchors：

```text
max_drawdown_20d
distance_from_20d_low
close_position_20d
ret_20d
ret_60d
rebound_from_20d_low
volatility_20d
volatility_60d
```

若 `rebound_from_20d_low` 不存在于 upstream feature set，runner 必须用 PIT-safe formula 重建：

```text
rebound_from_20d_low = close[reference_pos] / min(low over last 20 sessions including reference_pos) - 1
```

Broad morphology baseline score 必须至少包含：

```text
broad_drawdown_score = standardized rank of max_drawdown_20d / distance_from_20d_low / ret_20d
broad_reversal_score = standardized rank of rebound_from_20d_low / close_position_20d / ret_60d
broad_morphology_score = equal-weight z-score average of pre-registered anchors
```

Primary broad morphology score 必须使用 equal-weight z-score average，z-score parameters 只能在 train split fit，然后固定到 validation / robustness。PCA 只能作为 secondary diagnostic；若启用 PCA，PCA fit 也只能在 train split 中完成，并固定 loadings 到 validation / robustness。PCA 结果不得改变任何 decision gate。

### 7.2 Required feature clusters

13C 必须使用以下 train-frozen feature clusters，不得用 validation / robustness 重分组：

```text
cluster_compression:
  volatility_20d
  volatility_60d
  range_width_20d if available

cluster_position_strength:
  distance_from_20d_low
  close_vs_sma20
  close_position_20d

cluster_participation:
  turnover_zscore_20d
  amount_ratio_5d_20d
  volume_up_price_not_down_5d

cluster_drawdown_morphology:
  max_drawdown_20d
  ret_20d
  ret_60d
  rebound_from_20d_low

cluster_denominator_controls:
  board_bucket
  calendar_year
  liquidity_bucket
  volatility_bucket
```

Missing optional features must be audited, not silently dropped. Required 13A3 state features must be present or reconstructed; otherwise fail closed.

必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_anchor_dictionary.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/feature_cluster_dictionary.csv
```

## 8. Denominator-Balanced Residualization

13C 的 primary residual effect 不得直接比较 treated vs native raw baseline。必须先按 denominator 与 morphology controls 构造 residual frame。

Primary control denominator:

```text
treated(row, state_id) =
  required_composite_state_membership(state_id) == true

control(row, state_id) =
  native_opportunity_universe(row)
  and required_composite_state_membership(state_id) == false
  and same supported residualization cell as treated rows
```

Secondary comparator:

```text
compression_base_control(row, state_id) =
  compression_base(row)
  and required_composite_state_membership(state_id) == false
  and same supported residualization cell as treated rows
```

`control_n` in 13C tables always means the primary same-cell native complement control unless the column name explicitly starts with `compression_base_`.

### 8.1 Stratification cells

Primary stratification cell:

```text
split_bucket
board_bucket
calendar_year
liquidity_bucket
volatility_bucket
max_drawdown_20d_decile
compression_severity_bucket
```

其中：

```text
liquidity_bucket = train-frozen quantile bucket of money_median_20d
volatility_bucket = train-frozen quantile bucket of volatility_20d
max_drawdown_20d_decile = train-frozen decile bucket
compression_severity_bucket = train-frozen bucket within volatility_20d bottom state
```

Validation / robustness 不得重算 bucket threshold。若某 split 的 cell support 不足，必须合并到预注册 fallback cell：

```text
fallback_cell = split_bucket + board_bucket + calendar_year + max_drawdown_20d_quintile
```

Cell support threshold：

```text
min_treated_per_cell = 20
min_control_per_cell = 50
min_positive_per_split = 50
```

### 8.2 Residual labels

13C 必须构造以下 residual targets：

```text
residual_winner =
  winner_positive - E[winner_positive | morphology_controls, denominator_controls]

residual_lower_first =
  lower_first - E[lower_first | morphology_controls, denominator_controls]

residual_fast_fail =
  fast_fail - E[fast_fail | morphology_controls, denominator_controls]

residual_utility =
  row_utility_component_50bps - E[row_utility_component_50bps | morphology_controls, denominator_controls]
```

Primary implementation 可以使用任一预注册低容量方法：

```text
method_a = cell_mean_residualization
method_b = train-frozen logistic / ridge residual model with morphology + denominator controls only
```

若使用 `method_b`：

- 模型 family 必须预注册为 logistic/ridge 或 linear/ridge；
- regularization grid 不得用 validation / robustness 选择；
- primary regularization 使用 config 固定值；
- 模型只用于 residualization，不得解释为可部署 classifier。

All residual expectation objects must be fit on train split only:

```text
fit_scope = train
apply_scope = train / validation / robustness
validation_labels_used_to_fit_expectation = false
robustness_labels_used_to_fit_expectation = false
```

For `method_a`, cell means for `E[y | controls]` must be computed from train rows only. Validation / robustness rows are assigned expected values using train-fitted cell rates. If a validation / robustness cell is unseen in train, runner must use the pre-registered backoff hierarchy:

```text
1. board_bucket + calendar_year + max_drawdown_20d_quintile
2. board_bucket + max_drawdown_20d_quintile
3. max_drawdown_20d_quintile
4. train global mean
```

The selected backoff level must be recorded per cell in `residualization_design_audit.csv`.

Because 13A3 already identified calendar / liquidity denominator drift, 13C must audit residual expectation calibration before interpreting residual winner as morphology-orthogonal information.

Residual calibration is not a hard pass/fail gate, but it must produce a caveat that is carried into the final decision and any downstream 13D requirement.

必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/residualization_design_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/residual_calibration_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/residual_state_effect_readout.csv
```

`residual_calibration_audit.csv` 字段：

```text
target_id                         # winner_positive / lower_first / fast_fail / row_utility_component_50bps
split_bucket                      # validation / robustness
residualization_method
cell_scope                        # primary_cell / fallback_level_1 / fallback_level_2 / fallback_level_3 / global
cell_count
row_count
predicted_mean_from_train
realized_mean_in_split
calibration_error
abs_calibration_error
weighted_abs_calibration_error
max_abs_cell_calibration_error
calibration_status
```

Calibration status:

```text
calibration_pass:
  weighted_abs_calibration_error <= 0.02 for binary targets
  and weighted_abs_calibration_error <= 0.0025 for row_utility_component_50bps

residual_drift_caveat:
  threshold exceeded in validation or robustness

insufficient_calibration_support:
  supported cell_count or row_count is insufficient for stable readout
```

`residual_drift_caveat` does not automatically fail `residual_winner_gate_status`, but it changes final interpretation:

```text
effect_interpretation =
  morphology_orthogonal_residual_diagnostic_only_with_residual_drift_caveat
```

and downstream 13D must include:

```text
residual_drift_caveat_from_13c = true
calibration_recheck_required = true
```

`residual_state_effect_readout.csv` 字段：

```text
state_id
split_bucket
residualization_method
treated_n
control_n
cell_count
supported_cell_count
raw_winner_diff
residual_winner_diff
raw_lower_first_diff
residual_lower_first_diff
raw_fast_fail_diff
residual_fast_fail_diff
raw_utility_per_entry
residual_utility_per_entry
raw_utility_total_indexed
residual_utility_total_indexed
residual_utility_margin_vs_broad
compression_base_residual_utility_per_entry
residual_control_definition
residual_winner_gate_status
residual_badside_readout_status
```

Residual readout formulas:

```text
raw_winner_diff =
  mean(winner_positive | treated) - mean(winner_positive | primary_same_cell_control)

residual_winner_diff =
  mean(residual_winner | treated) - mean(residual_winner | primary_same_cell_control)

raw_lower_first_diff / residual_lower_first_diff:
  same formula using lower_first / residual_lower_first

raw_fast_fail_diff / residual_fast_fail_diff:
  same formula using fast_fail / residual_fast_fail

raw_utility_per_entry =
  mean(row_utility_component_50bps | treated)

residual_utility_per_entry =
  mean(residual_utility | treated)

residual_utility_total_indexed =
  residual_utility_per_entry * treated_n / native_denominator_n

broad_morphology_baseline_threshold(state_id) =
  train-frozen threshold at quantile
  1 - train_treated_n(state_id) / train_native_denominator_n
  of broad_morphology_score in train native denominator

broad_morphology_baseline_rows(state_id, split) =
  native rows in split where
  broad_morphology_score >= broad_morphology_baseline_threshold(state_id)
  and, when enough support remains, not treated(state_id)

if treated exclusion causes insufficient support:
  include treated rows and flag comparator_overlap_caveat

No split-local top-N ranking is allowed for this baseline. Validation / robustness baseline membership must be determined only by the train-frozen broad morphology score transform and train-frozen threshold.

residual_utility_margin_vs_broad =
  residual_utility_per_entry
  - mean(residual_utility | broad_morphology_baseline_rows)
```

Primary residual winner gate pass requires all of:

```text
validation residual_winner_diff > 0
robustness residual_winner_diff > 0
validation residual_utility_per_entry > 0 at 50bps
robustness residual_utility_per_entry > 0 at 50bps
```

Residual bad-side is a required readout but not a hard authorization gate:

```text
residual_badside_readout_status =
  caveat_left_tail_residual_positive
  if validation or robustness residual_lower_first_diff > 0

residual_badside_readout_status =
  caveat_fast_fail_residual_positive
  if validation or robustness residual_fast_fail_diff > 0.01

residual_badside_readout_status =
  no_badside_residual_caveat
  otherwise
```

Rationale: 13A3 already proves this family is a high-event-intensity / double-tail state. 13C's primary question is whether morphology-orthogonal winner / utility residual information exists. A positive residual lower-first readout must be reported as a caveat and carried into any downstream meta-labeling feasibility requirement, but it must not by itself stop 13C from answering the residual winner question.

If only winner residual is positive but utility residual is non-positive, status must be:

```text
residual_readout_probability_only_no_utility
```

## 9. Clustered MDA / Residual Importance Diagnostic

13C must measure whether compression-repair feature clusters add information beyond morphology anchors.

### 9.1 Model families

Allowed diagnostic model families:

```text
low_capacity_logistic_l2
monotone_optional_tree_stump_ensemble
```

Default primary model:

```text
low_capacity_logistic_l2
```

The model is diagnostic only. It may not be used for trading signals, threshold selection, probability calibration, meta-labeling, or bet sizing.

Target:

```text
primary_target = winner_positive
secondary_targets = lower_first, fast_fail, utility_positive_50bps
```

Feature sets:

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

### 9.2 Purged / embargoed evaluation

Because the selected label has `horizon_sessions = 20`, any fold-based evaluation must use:

```text
purge_window_sessions = 20
embargo_sessions = 20
group_unit = instrument
time_order_preserved = true
```

Validation protocol:

```text
train split: fit model / fit scaler / fit buckets only
validation split: evaluate first out-of-sample
robustness split: final holdout readout
```

Optional internal CV inside train split must be purged and embargoed. No validation / robustness feedback may change model family, features, cluster definition, regularization, bucket thresholds, or decision rules.

### 9.3 Clustered MDA

Permutation importance must be grouped by feature cluster. A cluster permutation shuffles all features in that cluster together within split and denominator bucket, preserving broad time distribution.

Required clustered MDA output:

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/clustered_mda_importance.csv
```

字段：

```text
model_id
target_id
split_bucket
metric_id                    # auc / logloss / utility_proxy
cluster_id
baseline_metric
permuted_metric_mean
permuted_metric_std
mda_importance
mda_importance_ci_low
mda_importance_ci_high
permutation_n
importance_status
```

Primary cluster importance pass:

```text
cluster_position_strength or cluster_participation has:
  validation mda_importance_ci_low > 0
  robustness mda_importance_ci_low > 0
  and same sign for row_utility_component_50bps / utility_positive_50bps importance

cluster_compression alone cannot pass this gate,
because compression is the inherited base state and already suspected to be broad morphology.
```

If only `cluster_drawdown_morphology` is important, status must be:

```text
morphology_only_importance
```

If compression / position / participation clusters improve AUC but not cost-adjusted utility, status must be:

```text
residual_importance_no_utility_translation
```

### 9.4 Incremental model comparison

13C must output:

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/incremental_model_comparison.csv
```

字段：

```text
model_family
target_id
split_bucket
baseline_feature_set_metric_auc
augmented_feature_set_metric_auc
auc_delta
baseline_feature_set_utility_proxy
augmented_feature_set_utility_proxy
utility_delta
baseline_logloss
augmented_logloss
logloss_delta
incremental_status
```

Incremental pass requires:

```text
validation auc_delta > 0
robustness auc_delta > 0
validation utility_delta > 0
robustness utility_delta > 0
```

No AUC-only result can authorize meta-labeling.

## 10. Sample Uniqueness / Overlap Audit

13C must not treat daily H20 events as independent. Even though 13C is diagnostic, it must report overlap risk before any downstream meta-labeling authorization.

If row-level `t1` is available or can be reconstructed:

```text
t0 = entry_date
t1 = first touch date of upper/lower barrier, else vertical barrier date
event_span = [t0, t1]
concurrency_t = number of active events for same instrument at date t
average_uniqueness_i = mean_t(1 / concurrency_t) over event_span_i
```

If `t1` cannot be reconstructed from available inputs, 13C must output `t1_unavailable` and fall back to instrument-month block overlap proxy inherited from 12A7g / 13A, but meta-labeling authorization must require future 13D to reconstruct exact `t1`.

必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/sample_uniqueness_audit.csv
```

字段：

```text
state_id
split_bucket
event_n
t1_reconstruction_status
mean_average_uniqueness
median_average_uniqueness
p25_average_uniqueness
p10_average_uniqueness
mean_concurrency
p95_concurrency
instrument_month_block_n
mean_rows_per_block
p95_rows_per_block
effective_block_n
overlap_status
sample_uniqueness_gate_status
downstream_requirement_requires_exact_t1_rebuild
```

Meta-labeling authorization requires:

```text
sample_uniqueness_gate_status != exact_uniqueness_unavailable
or downstream_requirement_requires_exact_t1_rebuild = true
```

## 11. Decision Gates

13C gate statuses:

```text
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
morphology_anchor_gate_status
residualization_gate_status
residual_winner_gate_status
residual_badside_readout_status
residual_calibration_status
clustered_mda_gate_status
incremental_utility_gate_status
sample_uniqueness_gate_status
search_accounting_status
```

### 11.1 Gate pass requirements

`residual_winner_gate_status = pass` requires primary residual winner gate pass from §8.2.

`residual_badside_readout_status` is a caveat field. It must be populated before any positive decision, but it cannot hard-block `13C_authorize_meta_labeling_feasibility_preflight`.

`residual_calibration_status` is a caveat field. If any primary target in validation or robustness is `residual_drift_caveat`, 13C may still authorize 13D only with downgraded `effect_interpretation` and explicit downstream calibration recheck requirement.

`clustered_mda_gate_status = pass` requires at least one non-drawdown, non-compression cluster:

```text
cluster_position_strength
cluster_participation
```

to have positive validation and robustness clustered MDA with positive utility translation.

`incremental_utility_gate_status = pass` requires augmented feature set to beat baseline feature set in both validation and robustness on utility proxy. The primary utility proxy for model comparison is:

```text
model_utility_proxy(model, state_id, split) =
  mean(row_utility_component_50bps for top_N rows by model score)

N =
  treated_n(state_id, split)
```

The same utility proxy formula must be used for baseline and augmented models. `model_utility_proxy` is an optimistic out-of-sample ranking upper bound because each model selects top-N rows inside the evaluation split. The decision may use only the sign consistency of `utility_delta` across validation and robustness; it may not use the absolute `model_utility_proxy` level as evidence of deployable utility or as a sizing input.

`sample_uniqueness_gate_status = pass_with_exact_t1` if exact `t1` uniqueness is computed. If exact `t1` unavailable but all other gates pass:

```text
sample_uniqueness_gate_status = pass_with_downstream_exact_t1_requirement
```

and 13D must be required to rebuild exact event spans before any model training.

If exact `t1` is unavailable and downstream exact rebuild is not explicitly required:

```text
sample_uniqueness_gate_status = exact_uniqueness_unavailable
```

### 11.2 Fail statuses

Use specific fail statuses:

```text
13C_blocked_input_or_lineage_failure
13C_blocked_row_level_rebuild_failure
13C_stop_morphology_anchor_unavailable
13C_stop_no_morphology_orthogonal_residual_effect
13C_stop_residual_probability_only_no_utility
13C_stop_morphology_only_importance
13C_stop_residual_importance_no_utility_translation
13C_stop_uniqueness_unavailable_for_downstream
13C_authorize_meta_labeling_feasibility_preflight
```

## 12. Search / Multiplicity Accounting

13C is a diagnostic after 13A3 has already looked at validation / robustness readouts. It must be explicitly marked non-confirmatory.

必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/search_multiplicity_audit.csv
```

字段：

```text
required_state_n
selected_state_id
posthoc_after_13a3_report
validation_seen_before_requirement
robustness_seen_before_requirement
feature_cluster_n
anchor_n
model_family_n
target_n
effective_search_space_n
hyperparameter_search_used
validation_used_for_selection
robustness_used_for_selection
confirmatory_status
search_accounting_status
```

Default:

```text
required_state_n = 6
selected_state_id = repair_range_participation_core_30
posthoc_after_13a3_report = true
validation_seen_before_requirement = true
robustness_seen_before_requirement = true
model_family_n = 1 unless optional family is enabled in config
hyperparameter_search_used = false
validation_used_for_selection = false
robustness_used_for_selection = false
confirmatory_status = false
search_accounting_status = diagnostic_posthoc_not_confirmatory
```

13C positive result may only authorize confirmatory-style downstream feasibility. It cannot be reported as final evidence of deployable edge.

## 13. Decision Precedence

Decision precedence is strict:

1. Input / PIT / schema / lineage failure:

```text
13C_blocked_input_or_lineage_failure
```

2. Row-level rebuild failure:

```text
13C_blocked_row_level_rebuild_failure
```

3. Morphology anchors unavailable:

```text
13C_stop_morphology_anchor_unavailable
```

4. Residual winner gate fails:

```text
13C_stop_no_morphology_orthogonal_residual_effect
```

5. Residual winner probability positive but utility non-positive:

```text
13C_stop_residual_probability_only_no_utility
```

6. Clustered MDA shows only drawdown morphology importance:

```text
13C_stop_morphology_only_importance
```

7. Non-morphology residual importance exists but does not translate to utility:

```text
13C_stop_residual_importance_no_utility_translation
```

8. Exact uniqueness unavailable and downstream cannot require exact t1 rebuild:

```text
13C_stop_uniqueness_unavailable_for_downstream
```

9. All primary gates pass:

```text
13C_authorize_meta_labeling_feasibility_preflight
```

No decision may be upgraded by a prettier non-selected state in validation / robustness. 13C may report all states, but authorization must be based on predeclared selected state plus required residual gates. If non-selected states look better, report them as hypothesis-generating only.

## 14. Final Decision Output

必须输出：

```text
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_orthogonal_residual_importance_decision.csv
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
morphology_anchor_gate_status
residualization_gate_status
residual_winner_gate_status
residual_badside_readout_status
residual_calibration_status
clustered_mda_gate_status
incremental_utility_gate_status
sample_uniqueness_gate_status
downstream_requirement_requires_exact_t1_rebuild
residual_drift_caveat_from_13c
calibration_recheck_required
search_accounting_status
primary_failure_reason
```

Allowed positive decision:

```text
decision_state = 13C_authorize_meta_labeling_feasibility_preflight
next_allowed_requirement = requirement_13d_compression_repair_meta_labeling_feasibility_preflight.md
sequence_mining_authorized = False
meta_labeling_authorized = True
bet_sizing_authorized = False
downstream_requirement_requires_exact_t1_rebuild = true if sample_uniqueness_gate_status == pass_with_downstream_exact_t1_requirement else false
residual_drift_caveat_from_13c = true if residual_calibration_status == residual_drift_caveat else false
calibration_recheck_required = residual_drift_caveat_from_13c
effect_interpretation =
  morphology_orthogonal_residual_diagnostic_only_with_residual_drift_caveat
  if residual_drift_caveat_from_13c
  else morphology_orthogonal_residual_diagnostic_only
confirmatory_status = False
```

All negative decisions:

```text
next_allowed_requirement = none
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
```

Report 输出：

```text
outputs/publishable/reports/morphology_orthogonal_residual_importance_diagnostic_report.md
```

Manifest 输出：

```text
outputs/manifests/13C_morphology_orthogonal_residual_importance_diagnostic_manifest.json
```

## 15. Report Requirements

报告必须用中文写，并包含：

1. 单行裁决：是否存在 morphology-orthogonal residual information。
2. 为什么 13C 不推翻 13A3：13A3 否决的是 direct winner-buy / sequence mining，13C 只检查 residual information。
3. Residualization 设计：stratification cells、fallback cell、support loss。
4. Selected state 的 raw vs residual readout：winner、lower-first、fast-fail、utility。
5. Baseline morphology-only model vs augmented model 的 validation / robustness 对比。
6. Clustered MDA：drawdown morphology、compression、position、participation 各 cluster 的 importance。
7. Sample uniqueness / overlap audit：是否 exact t1、平均 uniqueness、concurrency 或 block proxy。
8. Model utility proxy caveat：`model_utility_proxy` 是 evaluation split 内 top-N 排序的乐观上界，decision 只依赖 `utility_delta` 在 validation / robustness 的符号一致性，不依赖绝对 utility 水平。
9. Residual bad-side caveat：若 residual lower-first / fast-fail 仍为正，必须说明它不 hard-block 13C，但必须进入 13D 的 meta-labeling risk controls。
10. Residual calibration caveat：报告 train-fitted residual expectation 在 validation / robustness 上的 predicted vs realized calibration error；若触发 `residual_drift_caveat`，必须说明 residual winner 可能吸收了 calendar / regime drift，且 13D 必须重检 calibration。
11. 若 positive，明确下一步仍只是 meta-labeling feasibility，不是 bet sizing、不授权 13B。
12. 若 negative，明确是以下哪类失败：
   - no residual effect；
   - probability-only residual without utility；
   - morphology-only importance；
   - residual importance no utility translation；
   - uniqueness / event-span 不可审计。

报告必须避免以下措辞：

```text
alpha discovered
deployable strategy
confirmed edge
sequence mining ready
bet sizing ready
```

## 16. Test Requirements

必须实现 synthetic tests，不依赖大文件：

1. `test_path_resolution_contract`
   确认 `topics/`、`data/`、`experiments/`、`outputs/` 路径解析规则。

2. `test_upstream_13a3_negative_decision_required`
   若 13A3 已授权 sequence mining，13C 必须 blocked。

3. `test_no_report_text_reconstruction`
   runner 不得从 report markdown 解析逐行 event membership。

4. `test_required_composite_state_membership_reproduction`
   required state membership 必须来自 verified cache 或 raw rebuild；聚合 readout 不可作为 row truth。

5. `test_train_frozen_bucket_thresholds`
   liquidity / volatility / max_drawdown bucket thresholds 只能用 train split fit。

6. `test_residualization_controls_remove_morphology`
   synthetic 中若 treated effect 完全由 max_drawdown cell mix 造成，residual effect 必须接近 0。

7. `test_probability_only_no_utility_fails`
   residual winner positive 但 residual utility non-positive 时，不能 pass。

8. `test_clustered_mda_group_permutation`
   cluster permutation 必须一起 shuffle cluster 内所有 features，不能单列 permutation 后相加。

9. `test_morphology_only_importance_fails`
   只有 drawdown cluster 重要时，decision 必须为 morphology-only stop。

10. `test_auc_only_incremental_gain_cannot_authorize`
    augmented model AUC 提升但 utility_delta <= 0 时不得授权 13D。

11. `test_purged_embargo_config_required`
    model diagnostic 必须记录 purge_window_sessions = 20 和 embargo_sessions = 20。

12. `test_uniqueness_exact_or_downstream_requirement`
    exact t1 不可用时，positive decision 必须要求 downstream exact t1 rebuild；否则 fail。

13. `test_decision_precedence`
    上游 failure 优先于所有 residual / MDA positive readout。

14. `test_no_bet_sizing_authorization`
    任何 13C decision 都必须 `bet_sizing_authorized = False`。

15. `test_no_sequence_mining_authorization`
    任何 13C decision 都必须 `sequence_mining_authorized = False`。

16. `test_residual_lower_first_does_not_hard_block_winner`
    residual winner / utility gate 通过但 residual lower-first > 0 时，13C 不得因 bad-side caveat alone stop；必须输出 `residual_badside_readout_status` caveat。

17. `test_broad_morphology_baseline_uses_train_frozen_threshold`
    validation / robustness 的 broad morphology baseline rows 必须来自 train-frozen quantile threshold，不得使用 evaluation split top-N 排序。

18. `test_model_utility_proxy_delta_only`
    positive decision 只能使用 validation / robustness `utility_delta > 0` 的符号一致性，不得用 absolute `model_utility_proxy` 水平授权。

19. `test_residual_calibration_caveat_does_not_hard_fail`
    residual winner gate 通过但 calibration error 超阈值时，13C 不得直接 stop；必须输出 `residual_calibration_status = residual_drift_caveat`、降级 `effect_interpretation`，并要求 13D calibration recheck。

20. `test_residual_calibration_audit_uses_oos_realized_rates`
    `residual_calibration_audit.csv` 必须比较 train-fitted predicted cell rates 与 validation / robustness realized rates，不得用 validation / robustness label refit expectation。

## 17. Implementation Order

建议实现顺序：

1. Parse config and resolve paths.
2. Load upstream decisions, manifests, and lineage tables.
3. Rebuild or verify row-level native panel, label fields, and composite membership.
4. Reconstruct morphology anchors and feature clusters.
5. Fit train-frozen buckets and morphology residualization design.
6. Compute raw vs residual state effects for all required states.
7. Compute residual calibration audit against validation / robustness realized rates.
8. Fit morphology-only baseline diagnostic model on train.
9. Fit augmented diagnostic model on train.
10. Evaluate validation / robustness with purge / embargo provenance.
11. Compute clustered MDA / grouped permutation importance.
12. Compute sample uniqueness or exact-t1 availability audit.
13. Apply decision precedence.
14. Write publishable tables, report, manifest, and tests.

No step may use validation / robustness to define thresholds, anchors, clusters, model family, regularization, state selection, or decision rules.
