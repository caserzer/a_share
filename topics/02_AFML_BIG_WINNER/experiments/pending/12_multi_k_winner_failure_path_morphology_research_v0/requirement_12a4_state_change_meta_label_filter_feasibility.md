# 需求：12A4 Risk-on State-change Freshness / Meta-label Filter Feasibility

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明时 fail closed；不得从报告文本或聚合表反推出事件、标签或特征。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A4
run_id = 12A4_state_change_meta_label_filter_feasibility
status = spec_draft_pending_review
expected_entrypoint = src/run_12a4_state_change_meta_label_filter_feasibility.py
expected_config = configs/config_12a4_state_change_meta_label_filter_feasibility.yaml
expected_test_file = tests/test_12a4_state_change_meta_label_filter_feasibility.py
```

本需求是对 `research_plan.md` 中旧版 “12A4 Optional Filter Layer Feasibility” 的收敛修订。12A3 没有支持 C0 union 成为 primary event backbone，因此 12A4 不再继续寻找新的硬事件定义；12A4 的 primary scope 限定在 `market_regime_bucket = risk_on`，只检验：

```text
state-change 事件作为低密度、早触发、低重复、PIT 可执行的 feature source，
能否通过 freshness / context / interaction / path features 形成有用的 meta-label score。
```

## 2. 上游冻结事实

12A4 承接以下已发布事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
12A3 decision = 12A3_state_change_backbone_partial_feature_source
```

12A3 关键读数：

```text
C0 low_to_high recall = 98.60%
R-core low_to_high recall = 97.43%
C0 low_to_high event precision = 5.32%
R-core low_to_high event precision = 6.39%
12A3 supported precision gate threshold = 8.39%
C0 event_n = 28,691
R-core event_n = 47,914
C0 density ratio vs R-core = 0.599
C0 same-instrument 10d duplicate = 7.25%
R-core same-instrument 10d duplicate = 57.83%
C0 first event minus low median = 9 sessions
R-core first event minus low median = 14 sessions
```

12A3 risk_on slice 已知读数：

```text
C0 risk_on low_to_high train event_n = 8,303
C0 risk_on low_to_high train positive_n = 602
C0 risk_on low_to_high train precision = 7.25%
C0 risk_on low_to_high validation event_n = 2,151
C0 risk_on low_to_high validation positive_n = 43
C0 risk_on low_to_high validation precision = 2.00%
C0 risk_on low_to_high robustness event_n = 4,659
C0 risk_on low_to_high robustness positive_n = 370
C0 risk_on low_to_high robustness precision = 7.94%
```

解释：

```text
validation risk_on 是低 base-rate 薄片，不能因为 event_n 足够就自动用于 threshold selection。
12A4 必须显式检查 validation base-rate health。
```

12A3 的含义：

```text
C0 union 的优势是 clean event source，不是 raw timing precision。
继续调整 priority / family / density hard rule 不应被当作主研究方向。
12A4 必须先补充 R-core 同口径 risk_on baseline，再测试 freshness / decay 与 meta-label scoring。
```

## 2.1 Primary regime scope

12A4 的 primary decision population 必须限定为：

```text
market_regime_bucket = risk_on
```

Scope rules：

1. `transition` 和 `risk_off` 事件不得进入 primary feature matrix、model fit、threshold selection 或 final decision gate。
2. 非 risk_on 事件只能进入 `regime_scope_exclusion_audit.csv`，用于 row count / exclusion reason 审计。
3. 12A4 不搜索 regime filter，也不比较 `risk_on` / `transition` / `risk_off` 哪个更好。
4. 12A4 的核心问题是：在 risk_on 内，C0 state-change 是否相对 R-core risk_on baseline 还有增量。

## 3. 核心研究问题

12A4 回答四个问题：

1. 在 `risk_on` scope 内，C0 读数是否优于 R-core risk_on baseline，还是只复述 risk_on base rate？
2. 12A3 missed episode 中暴露出的 `low 前 11-44 sessions 有 state-change 但未进入 low_to_high`，是否可以用 state freshness / decay / carry-forward 解释？
3. 在 C0 risk_on primary population 上，结合 R-core prior interaction feature 后，PIT meta-label score 是否能把事件分层到明显高于 base rate 的 top bucket？
4. 如果 top bucket precision 提高，是否同时保留足够 episode recall、降低 density / duplicate，并且不恶化 fast-fail / false-repair？

## 4. 非目标

12A4 明确不做：

- 不修改 12A2 family formula、threshold、canonicalization priority 或 C0 primary union；
- 不把 B7 diagnostic-only family 或 blocked industry / sector family 提升为候选；
- 不搜索或优化 `risk_on` / `transition` / `risk_off` regime filter；
- 不让 `transition` 或 `risk_off` 事件进入 primary scoring；
- 不用 robustness 结果回头挑选更好看的 feature、threshold、model；
- 不做 policy replay、仓位、entry / exit、交易成本或资金曲线；
- 不声明最终可交易 alpha；
- 不训练高容量黑箱模型；
- 不使用 episode low / high / first_50pct / MFE / future return 生成特征；
- 不把 event 是否落入 episode window 的 future label 混入 t0 feature；
- 不用事后 board/regime 修订值替代 t0 PIT context；
- 不把 8.39% precision 当成最终成功目标。

## 5. 必需输入

### 5.1 12A3 frontier 输出

必需输入：

```text
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_frontier_decision.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_episode_recall_precision_frontier.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_event_timing_distribution.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_captured_episode_density.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_missed_episode_diagnostics.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_b8_incremental_episode_recall.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_frontier_slice_readout.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/backbone_event_label_exposure.csv
outputs/publishable/tables/12A3_episode_precision_recall_frontier/state_change_label_recompute_parity_audit.csv
outputs/manifests/12A3_episode_precision_recall_frontier_manifest.json
```

12A3 gate：

```text
backbone_frontier_decision.decision_state =
  12A3_state_change_backbone_partial_feature_source
partial_feature_source_gate_pass = true
label_recompute_gate_pass = true
min_label_recompute_parity_match_rate >= 0.995
```

若 12A3 为 `12A3_no_backbone_improvement_over_r_core` 或 label parity 未通过，12A4 必须 fail closed。

### 5.2 12A2 state-change 事件输入

必需输入：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_canonical.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_instances.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_family_formula_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_canonicalization_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_density_audit.csv
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

Primary state-change population：

```text
candidate_generation_status = supported_canonical_event
non_executable_next_open = false
event_t0_pit_status = pass
trade_open_pit_status = pass
```

`state_change_candidate_event_instances.csv.gz` 只能用于 same-day family trigger count、secondary family flags、freshness / overlap features；不得重新生成 primary event。

### 5.3 R-core benchmark 输入

必需输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/episode_target_registry_06_risk_on_428.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_arm_event_registry.csv.gz
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_demote_or_keep_decision.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_density_badside_tradeoff.csv
outputs/manifests/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json
```

R-core gate：

```text
r_core_demote_or_keep_decision.decision = 12A1_r_core_recall_benchmark_only
primary_benchmark_arm_id = 08_R_core_event_regime_gated_raw
```

12A4 必须为 R-core 事件补同口径 risk_on baseline / board / density / interaction readout。不得仅用 C0 risk_on slice 判断 state-change 是否有效。

### 5.4 PIT 市场、价格、执行和 label 输入

必需输入：

```text
topics/02_AFML_BIG_WINNER/configs/labels.yaml
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/index/benchmark_indices_daily.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
```

所有 path / return / volatility / turnover / rank feature 必须在 `event_t0_date` 收盘后可得；若 feature 需要 next-open execution，必须明确标记：

```text
feature_availability_time = event_t0_close
or
feature_availability_time = trade_open_pre_execution
```

Primary scoring feature 只能使用 `event_t0_close` 可得特征。`trade_open_pre_execution` 特征只能进入 secondary tradability readout。

## 6. Scoring population

12A4 必须物化统一 risk_on 事件池：

```text
meta_label_event_universe.csv.gz
```

Row contract：

```text
one row = one source event after risk_on scope filter
meta_event_id is unique
same source_event_id cannot appear in multiple rows
interaction / residual concepts are flags or readout slices, not extra rows
```

必需 source population：

| source_arm_id | 来源 | 用途 |
| --- | --- | --- |
| `C0_state_change` | 12A2 C0 canonical supported risk_on events | primary decision population |
| `R_core` | 12A1 R-core raw risk_on benchmark events | benchmark baseline population |

Primary decision population：

```text
source_arm_id = C0_state_change
market_regime_bucket = risk_on
```

Benchmark population：

```text
source_arm_id = R_core
market_regime_bucket = risk_on
```

Model fit / threshold / final decision 只能使用 primary decision population。R-core rows 只用于 baseline、prior interaction feature 和 report readout；不得把 `source_arm_is_r_core` 当作 primary model 的分类特征来训练 pooled C0/R-core 模型。

必需 readout slice flags：

```text
readout_c0_intersect_r_core_same_day
readout_c0_without_prior_r_core_5_sessions
readout_r_core_without_prior_c0_5_sessions
readout_c0_after_prior_r_core_5_sessions
readout_r_core_after_prior_c0_5_sessions
```

这些 readout flags 只能用于 slice readout / feature，不得生成额外事件行。

Nearby 定义必须可配置，默认：

```text
nearby_window_sessions = 5
```

统一事件主键：

```text
meta_event_id
source_event_id
source_arm_id
instrument
event_t0_date
event_t0_pos
trade_open_date
trade_open_pos
event_split
board_bucket
market_regime_bucket
```

Risk-on scope filter：

```text
if market_regime_bucket is missing:
  reconstruct from PIT index / benchmark context at event_t0_date
if reconstructed market_regime_bucket != risk_on:
  exclude from meta_label_event_universe
  write to regime_scope_exclusion_audit.csv
if market_regime_bucket cannot be reconstructed:
  exclude from meta_label_event_universe
  write exclusion_reason = missing_regime_scope
```

必需输出 `market_regime_reconstruction_status` 和 `regime_scope_status`。

## 7. PIT Feature Contract

12A4 必须输出：

```text
meta_label_event_feature_matrix.parquet
meta_label_feature_dictionary.csv
meta_label_feature_pit_audit.csv
```

每个 feature 必须在 dictionary 中记录：

```text
feature_name
feature_group
source_artifact
calculation_rule
availability_time
lookback_window
missing_policy
pit_status
allowed_for_primary_model
```

### 7.1 Event-native features

必需 feature：

```text
source_arm_is_c0
source_arm_is_r_core
primary_family_id
primary_family_is_B1
primary_family_is_B2
primary_family_is_B3
primary_family_is_B4
primary_family_is_B5
primary_family_is_B6
primary_family_is_B8
triggered_family_count
triggered_family_ge2
has_B1_trigger
has_B3_trigger
has_B5_trigger
has_B8_trigger
canonical_priority
raw_instance_count_collapsed
event_split
board_bucket
```

R-core 不存在的 family fields 必须置 null / false，并在 feature matrix 中保留 `source_arm_is_r_core = true`。

`source_arm_is_c0`、`source_arm_is_r_core` 只能用于 population audit / benchmark readout，`allowed_for_primary_model = false`。Primary model 的训练行均来自 C0 risk_on population，不得依赖 source-arm identity 产生 uplift。

### 7.2 Freshness / decay features

这是 12A4 的第一优先 feature group。必需 feature：

```text
sessions_since_last_c0_event_same_instrument
days_since_last_c0_event_same_instrument
sessions_since_last_same_family_event
days_since_last_same_family_event
sessions_since_last_B1_event
sessions_since_last_B5_event
sessions_since_last_B8_event
c0_event_count_last_5_sessions
c0_event_count_last_10_sessions
c0_event_count_last_20_sessions
c0_event_count_last_40_sessions
c0_event_count_last_60_sessions
same_family_event_count_last_20_sessions
is_first_c0_after_20_session_silence
is_first_c0_after_40_session_silence
freshness_decay_tau_5
freshness_decay_tau_10
freshness_decay_tau_20
freshness_decay_tau_40
```

Decay formula：

```text
freshness_decay_tau_N = exp(-sessions_since_last_c0_event_same_instrument / N)
```

如果没有历史事件：

```text
sessions_since_last_* = null
is_first_* = true
freshness_decay_tau_* = 0
```

### 7.3 Active-state carry-forward features

12A4 必须单独输出 active-state decay frontier：

```text
state_change_active_state_decay_frontier.csv
```

定义：

```text
An event creates an active state from event_t0_pos to event_t0_pos + horizon_sessions.
horizon_sessions in [5, 10, 20, 40, 60]
The active state is PIT-valid because it is a predeclared holding validity window.
It is not a new event and must not increase event_n.
```

Denominator rule：

```text
active_state_event_n = original risk_on C0 event_n
active_state_interval_n = count(unique instrument x active_state_start x horizon_sessions)
diagnostic_carry_inside_event_n =
  count(original events whose declared active interval overlaps a same-instrument low_to_high episode)
diagnostic_carry_precision =
  diagnostic_carry_inside_event_n / active_state_event_n
```

不得把 active interval 内的每一天当成新 event；不得用 active-state overlap 提高原事件的 `event_inside_window_n` 而不单独标记 denominator。

Interpretation rule：

```text
diagnostic_carry_precision is forward-looking diagnostic readout.
It answers whether missed episodes fall inside a predeclared freshness radius.
It is not t0 event precision and cannot be compared against §11 supported / partial gates.
forward_looking_caveat = true
```

Active-state readout 必须回答：

```text
active_state_horizon_sessions
active_state_event_n
active_state_interval_n
active_state_episode_recall
diagnostic_carry_inside_event_n
diagnostic_carry_precision
active_state_incremental_episode_n_vs_event_t0_low_to_high
diagnostic_carry_incremental_precision
active_state_bad_side_10_20_rate
missed_episode_recovered_n
active_state_denominator_type
forward_looking_caveat
```

该 readout 用于验证 missed episodes 是否来自 state freshness horizon；不得直接作为交易 holding rule。

### 7.4 Density / crowding features

必需 feature：

```text
same_instrument_duplicate_count_last_10_sessions
same_instrument_duplicate_count_last_20_sessions
same_instrument_duplicate_count_last_60_sessions
events_per_instrument_last_60_sessions
events_per_instrument_last_120_sessions
same_family_events_per_instrument_last_60_sessions
market_wide_c0_event_count_same_date
market_wide_same_family_event_count_same_date
board_wide_c0_event_count_same_date
board_wide_same_family_event_count_same_date
event_date_cross_sectional_density_percentile
```

Cross-sectional density percentile 必须只使用 `event_t0_date` 当日及之前可得事件。

### 7.5 Risk-on market context features

必需 feature：

```text
market_regime_bucket
is_risk_on
regime_age_sessions
benchmark_return_5d
benchmark_return_20d
benchmark_return_60d
benchmark_volatility_20d
benchmark_drawdown_from_60d_high
market_breadth_proxy_20d
```

若 `market_breadth_proxy_20d` 无法从现有 PIT 输入稳定构造，必须置 null 并记录 `feature_status = unavailable_existing_data`；不得临时引入新外部数据。

Primary feature matrix 中：

```text
market_regime_bucket must equal risk_on
is_risk_on must equal true
```

`is_transition`、`is_risk_off` 不得进入 primary feature matrix；非 risk_on 的行已在 scope filter 阶段排除。

12A4 必须输出 R-core 同口径 risk_on baseline：

```text
risk_on_r_core_baseline.csv
```

字段：

```text
source_arm_id
split
regime_scope
event_n
low_to_high_event_inside_n
low_to_high_event_precision
pre120_event_precision
episode_recall_low_to_high
event_density_mean
same_instrument_10d_duplicate_rate
bad_side_10_20_rate
winner_120d_rate
```

Split requirement：

```text
split in [all, train, validation, robustness]
all = all risk_on rows after scope filter
train / validation / robustness = event_split-specific risk_on rows
```

所有 `precision_lift_vs_R_core_risk_on_baseline` 必须使用同 split baseline；不得用 all-split R-core baseline 评价 validation 或 robustness。

Interpretation rule：

```text
If C0 risk_on precision <= R-core risk_on precision,
then state-change does not add timing precision inside risk_on.
```

### 7.6 Instrument pre-event path features

所有 pre-event path feature 只能使用 `event_t0_pos` 及之前的 qfq OHLCV。

必需 feature：

```text
ret_5d
ret_10d
ret_20d
ret_60d
volatility_20d
volatility_60d
max_drawdown_20d
max_drawdown_60d
distance_to_20d_high
distance_to_60d_high
distance_to_120d_high
distance_to_20d_low
distance_to_60d_low
distance_to_120d_low
rebound_from_20d_low
rebound_from_60d_low
turnover_zscore_20d
volume_zscore_20d
gap_open_prev_day
trend_ma_5_20_spread
trend_ma_20_60_spread
```

若 turnover 字段在 qfq 文件中不可得，必须记录缺失状态；不得用未来或非 PIT 数据补齐。

### 7.7 Entropy / path disorder features

Entropy features 用于刻画 risk_on 内 event 前路径的有序程度 / 混乱程度。它们不是新事件定义，也不得使用 event 后路径。

Primary entropy feature 必须只使用 `event_t0_pos` 及之前的 qfq OHLCV：

```text
return_sign_entropy_20d
return_sign_entropy_60d
binned_return_entropy_20d
binned_return_entropy_60d
up_down_transition_entropy_20d
up_down_transition_entropy_60d
intraday_range_bin_entropy_20d
volume_direction_entropy_20d
```

Diagnostic-only entropy feature：

```text
gaussian_return_entropy_20d
gaussian_return_entropy_60d
```

解释：

```text
gaussian_return_entropy_N is a monotonic transform of trailing return variance.
It is useful as an audit bridge, but by default allowed_for_primary_model = false
unless a later requirement explicitly proves non-redundant value.
```

Entropy formula：

```text
entropy = -sum(p_i * log(p_i))
normalized_entropy = entropy / log(number_of_declared_possible_states)
```

Normalization denominator must be fixed by the declared state space, not by the nonempty states observed in each event window. This keeps entropy comparable across events.

Declared state counts：

```text
return_sign_state = 3
binned_return_state = 5
up_down_transition_state = 9
intraday_range_bin_state = number_of_train_frozen_bins
volume_direction_state = 3
```

If the observed distribution is degenerate, entropy is 0 and normalized entropy is 0. Implementation must never divide by `log(1)`.

State construction rules：

```text
return_sign_state:
  log_return > 0 -> up
  log_return < 0 -> down
  log_return = 0 -> flat

binned_return_state:
  use predeclared volatility-scaled bins:
    (-inf, -1.5 sigma], (-1.5, -0.5 sigma], (-0.5, 0.5 sigma],
    (0.5, 1.5 sigma], (1.5 sigma, inf)
  sigma must be computed from prior window data only

up_down_transition_state:
  ordered pair of consecutive return_sign_state values inside the lookback window

intraday_range_bin_state:
  (high - low) / previous_close, binned by predeclared train-frozen quantiles

volume_direction_state:
  sign(volume - rolling_median_volume_20d)
```

PIT rules：

1. Entropy windows are trailing windows ending at `event_t0_pos`.
2. No episode low / high / winner label / future return can be used in state construction.
3. Any train-frozen quantile cutoffs must be fit on train only and then applied unchanged to validation / robustness.
4. If the lookback window has fewer than 0.8 * N valid observations, feature value must be null and `feature_status = insufficient_history`.

12A4 必须输出 entropy redundancy audit：

```text
entropy_feature_redundancy_audit.csv
```

字段：

```text
feature_name
split
coverage_rate
pearson_corr_vs_matching_volatility
spearman_corr_vs_matching_volatility
pearson_corr_vs_abs_return_lookback
spearman_corr_vs_abs_return_lookback
max_abs_redundancy_corr
redundancy_status
allowed_for_primary_model_after_audit
```

Redundancy rule：

```text
if max_abs_redundancy_corr >= 0.95:
  allowed_for_primary_model_after_audit = false
  redundancy_status = diagnostic_only_redundant_with_volatility
```

Entropy features 必须进入 `entropy_path_disorder_only_frontier` non-model baseline，用于判断 uplift 是否只是 path disorder 单特征排序带来的。

### 7.8 Volume acceleration / decay features

Volume acceleration / decay features 用于刻画 event 前成交量状态是否仍在加速、已经衰减，或只是一次性 liquidity spike。它们是 freshness / pre-event path 的二级候选特征，不是新的 event 定义，也不得作为单独 decision gate。

不得直接使用裸二阶差分作为 primary feature。必须使用稳健版本，并在 `event_t0_pos` 及之前的 qfq OHLCV / turnover 数据上计算：

```text
log_volume_accel_5d
log_volume_accel_10d
volume_z_accel_5d
volume_z_accel_10d
recent_log_volume_slope_5d
prior_log_volume_slope_15d
volume_slope_accel_5_15d
volume_slope_decay_ratio_5_15d
turnover_z_accel_5d
turnover_z_accel_10d
```

Definitions：

```text
log_volume = log1p(volume)

log_volume_accel_5d =
  (log_volume_t0 - log_volume_t0_minus_5)
  - (log_volume_t0_minus_5 - log_volume_t0_minus_10)

log_volume_accel_10d =
  (log_volume_t0 - log_volume_t0_minus_10)
  - (log_volume_t0_minus_10 - log_volume_t0_minus_20)

volume_z_accel_N =
  volume_zscore_N_at_t0 - volume_zscore_N_at_t0_minus_N

volume_zscore_N_at_t =
  (mean(log_volume over [t - N + 1, t]) - trailing_60d_mean_log_volume_at_t)
  / trailing_60d_std_log_volume_at_t

turnover_z_accel_N =
  turnover_zscore_N_at_t0 - turnover_zscore_N_at_t0_minus_N

turnover_zscore_N_at_t =
  (mean(turnover over [t - N + 1, t]) - trailing_60d_mean_turnover_at_t)
  / trailing_60d_std_turnover_at_t

recent_log_volume_slope_5d =
  OLS slope of log_volume over [event_t0_pos - 4, event_t0_pos]

prior_log_volume_slope_15d =
  OLS slope of log_volume over [event_t0_pos - 19, event_t0_pos - 5]

volume_slope_accel_5_15d =
  recent_log_volume_slope_5d - prior_log_volume_slope_15d

volume_slope_decay_ratio_5_15d =
  recent_log_volume_slope_5d / (abs(prior_log_volume_slope_15d) + 1e-6)
```

Construction rules：

1. `volume <= 0` 或缺失时，该 session 不得参与 slope / acceleration 计算。
2. 若 lookback 中有效 session 少于 required window 的 0.8，feature 必须置 null，并记录 `feature_status = insufficient_history`.
3. 所有 ratio / acceleration feature 必须用 train-frozen p1 / p99 winsorization cutoffs；validation / robustness 只能复用 train cutoffs。
4. Turnover 不可得时，`turnover_z_accel_*` 必须置 null，并记录 `feature_status = unavailable_existing_data`；不得用非 PIT 外部数据补齐。
5. Volume acceleration features 不得使用 event 后成交量，也不得使用 low/high/episode label。

12A4 必须输出 volume acceleration audit：

```text
volume_acceleration_feature_audit.csv
```

字段：

```text
feature_name
split
coverage_rate
invalid_volume_rate
winsorization_lower_cutoff
winsorization_upper_cutoff
pearson_corr_vs_turnover_zscore_20d
spearman_corr_vs_turnover_zscore_20d
pearson_corr_vs_volatility_20d
spearman_corr_vs_volatility_20d
pearson_corr_vs_abs_return_20d
spearman_corr_vs_abs_return_20d
max_abs_redundancy_corr
redundancy_status
allowed_for_primary_model_after_audit
```

Redundancy / anomaly rule：

```text
if max_abs_redundancy_corr >= 0.95:
  allowed_for_primary_model_after_audit = false
  redundancy_status = diagnostic_only_redundant_with_turnover_or_volatility

if coverage_rate < 0.80:
  allowed_for_primary_model_after_audit = false
  redundancy_status = diagnostic_only_sparse_coverage
```

Volume acceleration features 必须进入 `volume_acceleration_decay_only_frontier` non-model baseline，用于判断 uplift 是否只是成交量加速 / 衰减单特征排序带来的。

### 7.9 Cross-sectional rank features

按 `event_t0_date` 当日、board 内和全 universe 计算 rank / percentile：

```text
ret_20d_cs_rank_all
ret_60d_cs_rank_all
volatility_20d_cs_rank_all
turnover_20d_cs_rank_all
drawdown_60d_cs_rank_all
ret_20d_cs_rank_board
ret_60d_cs_rank_board
volatility_20d_cs_rank_board
turnover_20d_cs_rank_board
drawdown_60d_cs_rank_board
```

Universe denominator 必须来自 PIT executable universe；不得使用事后全市场 survivorship universe。

### 7.10 Failure / false-repair risk features

这些 feature 必须只由历史事件和历史价格构造，不得使用当前事件未来标签。

```text
instrument_prior_252d_ff10_event_count
instrument_prior_252d_fr20_event_count
family_prior_train_ff10_rate
family_prior_train_fr20_rate
family_prior_train_badside_rate
recent_lower_low_count_60d
recent_failed_rebound_count_60d
high_drawdown_weak_rebound_flag
```

`family_prior_train_*` 在 train 以外 split 中只能使用 train 统计；不得用 validation / robustness 的标签更新。`ff10`、`fr20`、`badside` 是历史聚合特征名，不得携带当前事件标签。

Temporal audit：

```text
split_time_boundary_audit.csv must record min/max event_t0_date by split.
If max(train.event_t0_date) > min(evaluation_split.event_t0_date),
  family_prior_train_* cannot be allowed_for_primary_model for that evaluation split.
  It may remain diagnostic-only, or be replaced by expanding prior-by-date statistics.
```

可选替代特征：

```text
family_expanding_prior_ff10_rate_asof_t0
family_expanding_prior_fr20_rate_asof_t0
family_expanding_prior_badside_rate_asof_t0
```

这些 expanding prior 特征必须只使用 `event_t0_date` 之前 horizon-complete 的历史事件标签。

### 7.11 R-core interaction features

必需 feature：

```text
has_r_core_same_day_at_t0_close
has_prior_r_core_within_5_sessions
sessions_since_nearest_prior_r_core_event
has_future_r_core_within_5_sessions
c0_before_future_r_core_within_5_sessions
c0_after_prior_r_core_within_5_sessions
r_core_active_same_risk_on_scope
source_interaction_bucket
```

`has_future_r_core_within_5_sessions` 和 `c0_before_future_r_core_within_5_sessions` 是诊断 feature，只能进入 report，不得进入 primary model，因为它们在 event_t0 不可知。

Primary R-core interaction features 只允许使用 risk_on scope 内的 R-core prior events：

```text
prior_r_core_event.market_regime_bucket = risk_on
prior_r_core_event.event_t0_date <= current_event.event_t0_date
```

若需要检查所有 regime 的 prior R-core 事件，只能输出 diagnostic-only readout：

```text
diagnostic_has_prior_any_regime_r_core_within_5_sessions
allowed_for_primary_model = false
```

Primary model allowed interaction features：

```text
has_r_core_same_day_at_t0_close
has_prior_r_core_within_5_sessions
sessions_since_nearest_prior_r_core_event
c0_after_prior_r_core_within_5_sessions
r_core_active_same_risk_on_scope
```

## 8. Meta-label targets

12A4 必须输出：

```text
meta_label_event_targets.csv.gz
```

Primary target：

```text
target_low_to_high_inside =
  event_t0_date inside same-instrument 06 risk_on episode low_to_high window
```

Secondary targets：

```text
target_pre120_to_high_inside
target_low_to_first_50pct_inside
target_winner_120d
target_fast_fail_10d
target_false_repair_20d
target_bad_side_10_20
```

Target rules：

1. Targets can use future labels and episode windows because they are labels, not features.
2. Any target-derived field must be excluded from `meta_label_event_feature_matrix.parquet`.
3. If an event matches multiple same-instrument episode windows, `target_*_inside` counts once and `multi_episode_target_overlap_n` records overlap.
4. Label completeness must be explicit:

```text
label_10d_complete
label_20d_complete
label_120d_complete
target_status
```

## 9. Model / scoring contract

12A4 必须先输出 non-model baselines，再训练 low-capacity meta-label score。

### 9.1 Non-model baselines

必需 baselines：

```text
family_only_frontier
risk_on_r_core_baseline_frontier
freshness_decay_only_frontier
density_only_frontier
entropy_path_disorder_only_frontier
volume_acceleration_decay_only_frontier
r_core_interaction_only_frontier
pre_event_path_rank_only_frontier
```

每个 baseline 必须输出 top bucket frontier，用于判断模型是否只是复述一个简单条件。

### 9.2 Allowed primary models

允许模型：

```text
logistic_regression_l2
logistic_regression_l1
shallow_decision_tree_max_depth_3
scorecard_quantile_binning
```

可选模型：

```text
gradient_boosting_depth_2_diagnostic_only
lightgbm_challenger_diagnostic_only
```

如果使用可选模型，它只能作为 diagnostic，不得单独决定 `12A4_meta_label_supported`。

禁止模型：

```text
deep learning
large unrestricted random forest
high-depth gradient boosting
post-hoc manually selected threshold from robustness
model ensemble selected by best robustness performance
```

### 9.3 LightGBM challenger benchmark

LightGBM 必须作为 challenger benchmark 输出，用于检验 low-capacity primary models 是否遗漏明显 nonlinear interaction。LightGBM 不是 primary decision model；若只有 LightGBM 达到 uplift，而 allowed primary models 未达到 supported gate，最终状态不得为 `12A4_meta_label_supported`。

Challenger purpose：

```text
question = did low-capacity primary models miss nonlinear feature interaction?
not_question = can LightGBM alone justify state-change timing selector?
```

LightGBM feature rules：

1. 只能使用 `allowed_for_primary_model = true` 的 feature。
2. 不得使用 active-state carry-forward diagnostic feature、future R-core diagnostic feature、target-derived field、forbidden future-name pattern field。
3. 不得使用 `gaussian_return_entropy_*`，除非 `entropy_feature_redundancy_audit.csv` 明确证明其非 volatility proxy 且 `allowed_for_primary_model_after_audit = true`。
4. 不得使用被 `entropy_feature_redundancy_audit.csv` 或 `volume_acceleration_feature_audit.csv` 标记为 diagnostic-only / redundant / sparse 的 feature。
5. 不得用 LightGBM feature importance 反向选择一组更好看的 low-capacity features 后重跑 supported gate；若需要这么做，必须进入下一阶段 12A5。

Required LightGBM constraints：

```text
objective = binary
boosting_type = gbdt
num_leaves <= 7
max_depth <= 3
min_data_in_leaf >= 100
learning_rate <= 0.05
feature_fraction <= 0.80
bagging_fraction <= 0.80
lambda_l1 >= 0
lambda_l2 >= 0
n_estimators selected by train internal CV only
early_stopping_source = train_internal_cv_only
class_weight_policy in (none, train_prevalence_balanced_fixed)
class_weight_policy_source = fixed_before_robustness_train_cv_only
```

`class_weight_policy` 必须写入 `lightgbm_challenger_model_card.csv`。不得在 validation / robustness 上根据 top bucket precision 事后选择 class weight。

Threshold / evaluation policy：

```text
fit population = C0_state_change risk_on train
hyperparameter selection = train internal CV fixed small grid only
threshold selection = same policy as §9.4
final evaluation = robustness with thresholds frozen before robustness
```

LightGBM outputs must be comparable with primary models:

```text
top10_low_to_high_precision
top20_low_to_high_precision
top10_episode_recall_low_to_high
top20_episode_recall_low_to_high
top20_bad_side_10_20_rate
top20_event_n
precision_lift_vs_C0_risk_on_baseline
precision_lift_vs_R_core_risk_on_baseline
precision_lift_vs_best_non_model_baseline
monotonic_bucket_status
rank_monotonicity_status
feature_group_importance
```

LightGBM 必须按与 primary models 相同的 split 维度（all / train / validation / robustness）输出上述字段，使 §11.4 challenger gate 可以逐条引用 `lightgbm_robustness_top*` 值。

If LightGBM dependency is unavailable in the execution environment, implementation must output:

```text
lightgbm_challenger_status = skipped_dependency_unavailable
```

and the missing challenger result must not be used to support or reject the primary 12A4 decision.

即使 LightGBM skipped，required output 也必须存在 stub CSV，避免 manifest / validator 歧义：

```text
lightgbm_challenger_score_bucket_frontier.csv
lightgbm_challenger_model_card.csv
```

Stub fields must include：

```text
lightgbm_challenger_status
skip_reason
dependency_name
dependency_version
split
row_status
```

### 9.4 Split / threshold policy

训练和选择：

```text
fit population = source_arm_id = C0_state_change and market_regime_bucket = risk_on and split = train
hyperparameter selection = train internal CV or fixed small grid
threshold selection = validation only if validation threshold health passes, otherwise train internal CV
final evaluation = robustness, with thresholds frozen before robustness
```

Validation threshold health：

```text
validation_event_n >= 500
and validation_positive_n >= 50
and validation_base_precision >= 0.5 * train_base_precision
```

如果任一条件不满足：

```text
threshold_selection_source = train_internal_cv
validation_threshold_selection_status = unhealthy_readout_only
```

若 validation threshold health 不通过，必须使用 train internal CV 并把 validation 作为 readout，不得用 validation 或 robustness 调 threshold。当前 12A3 risk_on validation positive_n = 43 且 base precision = 2.00%，预期会触发 train-CV fallback；实现不得按旧的 event_n-only sufficiency 走 validation threshold selection。

必须输出：

```text
validation_threshold_health.csv
```

字段：

```text
train_event_n
train_positive_n
train_base_precision
validation_event_n
validation_positive_n
validation_base_precision
validation_event_n_gate_pass
validation_positive_n_gate_pass
validation_base_precision_health_gate_pass
validation_threshold_health_pass
threshold_selection_source
validation_threshold_selection_status
```

### 9.5 Score buckets

所有 scoring method 必须输出：

```text
score
score_percentile_train_reference
score_bucket_decile
score_bucket_quintile
top_5pct_flag
top_10pct_flag
top_20pct_flag
top_30pct_flag
```

Percentile cutoffs 必须从 train 分布冻结，并应用到 validation / robustness。

## 10. Evaluation metrics

12A4 必须按以下维度输出 all / train / validation / robustness；其中 `all` 表示 risk_on scope 内所有事件，不包含 transition / risk_off：

### 10.1 Precision / recall / density

```text
event_n
target_low_to_high_inside_n
low_to_high_event_precision
episode_captured_n
episode_recall_low_to_high
episode_recall_pre120
events_per_captured_episode_median
events_per_captured_episode_p95
events_per_instrument_year_mean
events_per_instrument_year_p95
same_instrument_10d_duplicate_rate
outside_event_rate
```

### 10.2 Lift vs baselines

必需比较：

```text
precision_lift_vs_C0_risk_on_baseline
precision_lift_vs_R_core_risk_on_baseline
precision_lift_vs_best_non_model_baseline
recall_retention_vs_C0_risk_on_baseline
event_density_ratio_vs_C0_risk_on_baseline
event_density_ratio_vs_R_core_risk_on_baseline
```

### 10.3 Bad-side / payoff readout

```text
fast_fail_10d_rate
false_repair_20d_rate
bad_side_10_20_rate
winner_120d_rate
bad_side_delta_vs_C0_risk_on_baseline
winner_lift_vs_C0_risk_on_baseline
```

### 10.4 Calibration / rank monotonicity

```text
decile_low_to_high_precision
decile_bad_side_10_20_rate
decile_winner_120d_rate
spearman_score_vs_target_low_to_high
top_decile_vs_bottom_decile_precision_lift
monotonic_bucket_status
```

若只有 top bucket 高、其余 bucket 无序，必须标记：

```text
rank_monotonicity_status = weak
```

## 11. Decision gates

8.39% 是最低可研究门槛，不是成功目标。12A4 success 必须高于 12A3 supported gate。

Decision precedence：

```text
1. blocked_input_or_pit_failure
2. meta_label_supported
3. nonlinear_candidate_requires_12A5_validation
4. meta_label_partial_feature_source
5. meta_label_diagnostic_only
6. no_meta_label_uplift
```

### 11.0 Blocked input / PIT gate

输出状态为 `12A4_blocked_input_or_pit_failure` 的条件：

```text
required_input_artifact_missing = true
or input_artifact_read_status != pass
or input_schema_gate_pass = false
or r_core_risk_on_baseline_gate_pass = false
or r_core_risk_on_baseline_missing = true
or label_completeness_gate_pass = false
or feature_pit_gate_pass = false
or primary_population_event_n = 0
```

该状态优先级最高。若进入 blocked，任何 primary model、non-model baseline 或 LightGBM challenger readout 都不得改变 final decision；报告只能说明阻断原因和可修复输入。

### 11.1 Supported gate

输出状态为 `12A4_meta_label_supported` 需要同时满足：

```text
supporting_model_family in (
  logistic_regression_l2,
  logistic_regression_l1,
  shallow_decision_tree_max_depth_3,
  scorecard_quantile_binning
)
robustness_top20_low_to_high_precision >= 0.10
robustness_top10_low_to_high_precision >= 0.12
robustness_top20_precision_lift_vs_R_core_risk_on_baseline >= 1.50
robustness_top20_precision_lift_vs_C0_risk_on_baseline >= 1.75
robustness_top20_precision_lift_vs_best_non_model_baseline >= 1.20
robustness_top20_episode_recall_low_to_high >= 0.35
robustness_top20_bad_side_10_20_rate <= C0_risk_on_bad_side_10_20_rate
robustness_top20_event_n >= 500
monotonic_bucket_status in (pass, weak_with_top_bucket_consistent)
feature_pit_gate_pass = true
label_completeness_gate_pass = true
threshold_freeze_gate_pass = true
```

### 11.1a Supported gate feasibility self-check

supported gate 的多条 precision / lift 阈值会相互叠加，真正卡住的约束往往不是绝对 precision，而是某一条相对 lift。为避免实现者事后才发现“哪条 gate 才是 binding 约束”，12A4 必须输出 `supported_gate_feasibility_selfcheck.csv`，把 §11.1 每条数值门槛都展开成可对照行。

字段：

```text
gate_name
gate_kind
required_threshold
realized_value
binding_implied_precision
gate_pass
is_binding_constraint
notes
```

规则：

```text
gate_kind in (absolute_precision, relative_lift, recall, bad_side, event_n, monotonicity, pit, label, threshold_freeze)

binding_implied_precision:
  for absolute_precision gates = required_threshold
  for relative_lift gates = required_threshold * reference_baseline_precision
  for non-precision gates = null

is_binding_constraint = true for the single gate whose binding_implied_precision
  is the maximum among all precision-equivalent gates (absolute_precision + relative_lift);
  ties broken by larger required_threshold then by gate_name.
```

该 self-check 只用于解释 supported gate 的可达性结构，不改变 §11.1 的判定逻辑；任何 gate 仍以 §11.1 为准。`is_binding_constraint = true` 的那条必须在 §13 报告中被显式引用。

### 11.2 Partial feature gate

输出状态为 `12A4_meta_label_partial_feature_source` 的条件：

```text
allowed_primary_best_model_family in (
  logistic_regression_l2,
  logistic_regression_l1,
  shallow_decision_tree_max_depth_3,
  scorecard_quantile_binning
)
and
(
  (
    allowed_primary_best_robustness_top20_low_to_high_precision >= 0.0839
    and allowed_primary_best_robustness_top20_low_to_high_precision < 0.10
  )
  or
  (
    allowed_primary_best_robustness_top20_low_to_high_precision >= 0.10
    and one or more of episode recall / bad-side / baseline-lift gates fails
  )
)
```

该状态表示 allowed primary model 证明 state-change features 可以进入后续 morphology model，但不能作为 entry/timing selector。LightGBM-only uplift 不得触发该状态；若只有 LightGBM 满足 uplift 条件，只能进入 §11.4 nonlinear challenger candidate 或 diagnostic readout。

### 11.3 Diagnostic-only gate

输出状态为 `12A4_meta_label_diagnostic_only` 的条件：

```text
feature coverage too sparse
or usable_primary_feature_n = 0
or validation/robustness denominator too small
or model uplift only appears in train
or best result only comes from diagnostic-only future feature
```

### 11.4 Nonlinear challenger candidate

输出状态为 `12A4_nonlinear_candidate_requires_12A5_validation` 的条件：

```text
allowed_primary_models_do_not_pass_supported_gate = true
and lightgbm_challenger_status = evaluated
and lightgbm_robustness_top20_low_to_high_precision >= 0.10
and lightgbm_robustness_top10_low_to_high_precision >= 0.12
and lightgbm_robustness_top20_precision_lift_vs_R_core_risk_on_baseline >= 1.50
and lightgbm_robustness_top20_precision_lift_vs_C0_risk_on_baseline >= 1.75
and lightgbm_robustness_top20_precision_lift_vs_best_non_model_baseline >= 1.20
and lightgbm_robustness_top20_episode_recall_low_to_high >= 0.35
and lightgbm_top20_bad_side_10_20_rate <= C0_risk_on_bad_side_10_20_rate
and lightgbm_robustness_top20_event_n >= 500
and lightgbm_monotonic_bucket_status in (pass, weak_with_top_bucket_consistent)
and lightgbm_feature_pit_gate_pass = true
and lightgbm_threshold_freeze_gate_pass = true
```

该状态表示 nonlinear interaction 值得进入 12A5 复核，但 12A4 不得把 LightGBM-only uplift 宣告为 timing selector supported。

challenger 候选门槛除“只能来自 nonlinear 模型”这一点外，不得低于 §11.1 supported gate 的核心 precision / lift / recall / bad-side / monotonicity / event_n 条件；唯一允许放宽的是 `supporting_model_family`。这样可以避免高方差黑箱凭单一 top20 噪声 precision 被误升级为 12A5 复核候选。

### 11.5 No useful uplift

输出状态为 `12A4_no_meta_label_uplift` 的条件：

```text
nonlinear_candidate_requires_12A5_validation = false
and blocked_input_or_pit_failure = false
and (
  allowed_primary_best_robustness_top20_low_to_high_precision < 0.0839
  or allowed_primary_best_precision_lift_vs_R_core_risk_on_baseline <= 1.0
  or allowed_primary_best_top_bucket_bad_side_materially_worsens = true
  or threshold_freeze_gate_pass = false
)
```

## 12. Required outputs

12A4 必须输出以下 publishable tables：

```text
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/input_artifact_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/regime_scope_exclusion_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/split_time_boundary_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_event_universe.csv.gz
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_event_targets.csv.gz
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_feature_dictionary.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_feature_pit_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/entropy_feature_redundancy_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/volume_acceleration_feature_audit.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/risk_on_r_core_baseline.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/state_change_active_state_decay_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/non_model_filter_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/validation_threshold_health.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_score_bucket_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/supported_gate_feasibility_selfcheck.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_model_card.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/lightgbm_challenger_score_bucket_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/lightgbm_challenger_model_card.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_decision.csv
```

Local-cache only, unless size is small enough for publishable:

```text
outputs/local_cache/12A4_state_change_meta_label_filter_feasibility/meta_label_event_feature_matrix.parquet
outputs/local_cache/12A4_state_change_meta_label_filter_feasibility/model_artifacts/
```

Required report：

```text
outputs/publishable/reports/state_change_meta_label_filter_decision_report.md
```

Required manifest：

```text
outputs/manifests/12A4_state_change_meta_label_filter_feasibility_manifest.json
```

## 13. Report requirements

`state_change_meta_label_filter_decision_report.md` 必须用中文写清：

1. 在 risk_on scope 内，C0 是否相对 R-core risk_on baseline 有增量。
2. Validation threshold health 是否通过；如果不通过，必须说明 threshold selection 已 fallback 到 train internal CV，validation 仅作 readout。
3. Freshness / decay 是否解释 12A3 missed episodes；active-state carry readout 必须标注 `forward_looking_caveat = true`，不得解释为 t0 precision uplift。
4. 最强 non-model baseline 是什么，是否已经足够解释 uplift。
5. Meta-label model 的 top 10% / top 20% precision、episode recall、bad-side。
6. 为什么 8.39% 不是最终成功目标。
7. 哪些 feature group 真正有贡献，哪些只是诊断噪声。
8. Entropy / path disorder features 是否提供非 volatility 冗余信息；若 entropy uplift 被 `entropy_feature_redundancy_audit.csv` 判为 volatility proxy，必须降级为 diagnostic-only。
9. Volume acceleration / decay features 是否提供 freshness 增量；若 uplift 被 `volume_acceleration_feature_audit.csv` 判为 turnover / volatility proxy，必须降级为 diagnostic-only。
10. LightGBM challenger 是否发现 low-capacity primary models 漏掉的 nonlinear interaction；若 LightGBM-only 通过，必须标记为 `12A4_nonlinear_candidate_requires_12A5_validation`，不得写成 12A4 supported。
11. 若 final decision 为 partial / no-uplift / nonlinear-candidate，必须量化 top20 precision 距离 supported gate 的缺口，并拆解缺口来自 base-rate 限制、模型 lift 不足、best non-model baseline 已解释 uplift、bad-side gate 约束，还是只有 high-capacity challenger 可见。必须引用 `supported_gate_feasibility_selfcheck.csv` 中 `is_binding_constraint = true` 的那一条，明确指出真正卡住 supported gate 的是哪条阈值及其 binding-implied precision。
12. 必须专门分析 precision uplift 是否以 bad-side 上升为代价，至少报告 top10/top20 相对 C0 risk_on baseline 的 bad-side delta。
13. 若 final decision 为 blocked，必须列出触发 §11.0 的具体 gate、输入 artifact、schema / PIT / label / R-core baseline 状态，并禁止给出 timing selector 结论。
14. 是否建议进入下一阶段：

```text
12A5_morphology_feature_modeling
or
stop_state_change_as_timing_signal_keep_feature_source
```

报告不得只给 model AUC；必须以 precision / recall / density / bad-side / PIT coverage 为主。

## 14. Test requirements

测试至少覆盖：

```text
test_required_inputs_exist_and_schema
test_12a3_decision_gate_required
test_blocked_gate_triggers_on_missing_r_core_risk_on_baseline
test_blocked_gate_triggers_on_failed_feature_pit_or_label_completeness
test_primary_universe_contains_only_risk_on_events
test_meta_event_id_unique_no_interaction_duplicate_rows
test_feature_dictionary_has_pit_status_for_every_feature
test_forbidden_future_columns_absent_from_primary_feature_matrix
test_r_core_risk_on_baseline_exists_by_split
test_validation_threshold_health_forces_train_cv_when_unhealthy
test_freshness_features_use_only_prior_events
test_entropy_features_use_only_prior_window_and_train_frozen_bins
test_entropy_normalization_uses_declared_state_count_not_nonempty_states
test_entropy_redundancy_audit_blocks_volatility_proxy_features
test_volume_acceleration_features_use_only_prior_window_and_train_frozen_winsorization
test_volume_acceleration_audit_blocks_turnover_or_volatility_proxy_features
test_lightgbm_challenger_uses_only_allowed_primary_features
test_lightgbm_challenger_cannot_set_supported_decision_state
test_lightgbm_challenger_gate_not_weaker_than_primary_core_gates
test_lightgbm_skipped_dependency_outputs_required_stub_csvs
test_lightgbm_class_weight_policy_is_enumerated_and_recorded
test_lightgbm_challenger_thresholds_are_train_cv_only_when_validation_unhealthy
test_lightgbm_challenger_outputs_comparable_bucket_frontier
test_partial_gate_uses_allowed_primary_models_only
test_supported_gate_feasibility_selfcheck_marks_single_binding_constraint
test_r_core_interaction_primary_features_are_prior_only
test_family_prior_train_features_respect_split_time_boundary
test_active_state_decay_is_diagnostic_only_with_forward_looking_caveat
test_active_state_decay_does_not_increase_event_n_or_reuse_denominator_silently
test_train_thresholds_are_frozen_before_robustness
test_score_buckets_use_train_reference_percentiles
test_required_outputs_and_manifest_hashes
```

Forbidden feature name patterns：

```text
episode_low
episode_high
first_50pct
mfe
future
target_
label_
winner_
fast_fail_
false_repair_
bad_side_
event_minus_low
inside_window
```

这些字段可以出现在 target / report / evaluation outputs，但不得出现在 primary feature matrix 的 `allowed_for_primary_model = true` feature 列中。

## 15. Final decision states

12A4 最终只允许以下状态：

```text
12A4_meta_label_supported
12A4_meta_label_partial_feature_source
12A4_meta_label_diagnostic_only
12A4_nonlinear_candidate_requires_12A5_validation
12A4_no_meta_label_uplift
12A4_blocked_input_or_pit_failure
```

解释：

- `12A4_meta_label_supported`：state-change feature source 经 PIT meta-label score 后形成稳定、高于 base-rate 的 top bucket，可进入后续 morphology feature modeling。
- `12A4_meta_label_partial_feature_source`：有弱 uplift，但不足以承担 timing / entry selector。
- `12A4_meta_label_diagnostic_only`：诊断有信息，但缺少稳定 denominator、R-core baseline 或 PIT feature coverage。
- `12A4_nonlinear_candidate_requires_12A5_validation`：只有 LightGBM challenger 显示稳定 uplift，说明可能存在 nonlinear interaction，但不能在 12A4 直接宣告 supported。
- `12A4_no_meta_label_uplift`：meta-labeling 未能突破 precision base rate。
- `12A4_blocked_input_or_pit_failure`：输入、schema、PIT 或 label completeness 阻断。
