# 需求：14A Full-Native Sparse State-Change Event Utility Preflight

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP13_ROOT/`、`SOURCE_EP12_ROOT/` 表达的路径必须先解析到对应 episode root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、entry executability 不可证明、label horizon completeness 不可证明、feature availability 不可证明、cohort availability 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、event membership、cohort rank、label、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 14_full_native_sparse_state_change_event_utility_preflight_v0
phase_id = 14A
run_id = 14A_full_native_sparse_state_change_event_utility_preflight
status = spec_draft_pending_review
expected_entrypoint = src/run_14a_full_native_sparse_state_change_event_utility_preflight.py
expected_config = configs/config_14a_full_native_sparse_state_change_event_utility_preflight.yaml
expected_test_file = tests/test_14a_full_native_sparse_state_change_event_utility_preflight.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_13a = SOURCE_EP13_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

14A 是 Episode 14 的第一份执行 requirement。它不继续 13B sequence mining，也不复活 13A / 13A3 / 13C 的 compression-repair state。14A 检验一个新的、极窄的 thesis：

```text
full-native sparse state-change event
  + strict PIT cohort relative position
  -> ranking-to-utility transport
```

14A 的 negative lineage 是 Episodes 01-13 已经反复暴露的 blocker：

```text
ranking / recall / probability readout repeatedly exists,
but it does not reliably transport into after-cost full-denominator entry utility.
```

因此 14A 的正向证据必须同时满足：

```text
1. sparse first-trigger event 不是 pure noise，至少有 opportunity / ranking 表面；
2. PIT cohort relative position 能把该表面转成 50bps same-event full-denominator utility。
```

14A 失败时，不得继续主动 winner-entry event family search。后续只能把 topic 降级到 defense / participation overlay，或正式更换 thesis。

## 2. 核心问题

14A 回答以下问题：

```text
Q1. 能否在 13A full-PIT native opportunity universe 上构造 sparse、first-trigger、
    de-duplicated、next-open executable 的 state-change events？

Q2. Raw sparse events 是否相对 native baseline 有 winner / opportunity / ranking 表面，
    并且是否已经改善 bad-side 与 after-cost utility？

Q3. 在不引入未来信息、不使用 validation / robustness 调参的前提下，
    PIT cohort relative position 是否能在保留 winner opportunity 的同时，
    改善 50bps same-event full-denominator utility？

Q4. 正向读数是否只是 13A volatility compression、13A3 / 13C compression-repair
    morphology 或 broad drawdown / reversal 的重新发现？

Q5. validation split 作为长下跌 / risk-off 压力区间时，是否仍允许 active winner-entry
    thesis 继续进入 14B confirmatory requirement？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

14A 允许做：

```text
1. 复用 13A native opportunity universe 与 12A7g / 13A selected vol-scaled label lineage；
2. 从 raw PIT universe、qfq bars、benchmark / board context 中重建 t0 close 可观测 state-change features；
3. 预注册小规模 sparse event family 与参数网格；
4. 生成 false-to-true / first-trigger / cooldown 后的 sparse event panel；
5. 评估 raw event 的 opportunity、bad-side、utility、density、uniqueness；
6. 对有最低 raw opportunity 表面的 event family 加入 strict PIT cohort-relative rank arms；
7. 使用 same-event denominator 评估 cohort-normalized selection utility；
8. 输出 morphology rediscovery、validation stress、search accounting 与 decision mapping。
```

14A 明确不是：

```text
sequence mining
meta-labeling
nonlinear model capacity retry
probability calibration
bet sizing
portfolio backtest
exit / holding policy
cost model calibration
defense overlay
post-hoc replacement of selected event family
```

14A 不得产生任何生产、交易、仓位、alpha 或 meta-labeling 授权声明。即使 14A 通过，也只允许新建：

```text
requirement_14b_confirmatory_sparse_event_requirement.md
```

14B 必须重新冻结 confirmatory contract，不得把 14A exploratory readout 直接当作部署证据。

## 4. 继承边界

### 4.1 允许继承

14A 可以继承：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
reference_pos = qfq daily position at reference_date
decision_time = reference_date close
entry_date = next executable open after reference_date
entry_pos = qfq daily position at entry_date
entry_price = qfq open at entry_pos
selected_label_id = vol20d_kup2p0_kdn1p0_H20
selected_label same_bar_priority = lower_first
native opportunity universe definition from 13A
13A train-frozen native universe floor / cap
split boundary from 12A7g / 13A
cost_tier_bps = {0, 50, 100}
primary_cost_tier_bps = 50
```

14A 必须读取 13A publishable artifacts 作为 lineage：

```text
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/input_artifact_audit.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/upstream_12a7g_lineage_audit.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_decision.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_definition_audit.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_label_portability_audit.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_readout.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_morphology_collinearity_audit.csv
SOURCE_EP13_ROOT/outputs/manifests/13A_full_pit_native_token_cartography_preflight_manifest.json
```

14A 可以使用 13A local cache 作为加速输入：

```text
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_label_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_token_matrix.parquet
```

These three 13A local cache files are optional accelerator artifacts at input-audit time. Missing cache files must be recorded with `required_flag = false`, then full mode must attempt the 13A rebuild path before making a final input / lineage decision.

若使用 local cache，runner 必须验证：

```text
row key uniqueness
instrument x reference_date coverage
split boundary equality
selected_label_id equality
entry_date / entry_price rebuild equality for audited rows
native universe floor / cap equality
schema adapter mapping equality
sha256 / schema hash when manifest provides it
```

Cache 缺失或校验失败时，runner 必须从 raw PIT universe 与 qfq bars 重建，不得 fail open。

If the rebuild succeeds, the runner must re-run the same schema adapter and cache audit against the rebuilt 13A outputs. If the rebuild fails, final decision must be `14A_input_blocked` through the upstream lineage / adapter gate, not through a stale pre-rebuild input audit result.

13A primary cache schema adapter is frozen against `native_universe_panel.parquet`, because it is the only 13A cache that contains entry fields, barrier fields, labels, and terminal path return in one row-level artifact:

```text
native_universe_panel.split -> split_bucket
native_universe_panel.upper_barrier -> upper_barrier_return
native_universe_panel.lower_barrier -> lower_barrier_return
native_universe_panel.winner_positive -> winner
native_universe_panel.upper_first -> upper_first
native_universe_panel.lower_first -> lower_first
native_universe_panel.same_bar_conflict -> same_bar_conflict
native_universe_panel.native_scope -> native_scope
native_universe_panel.horizon_close_return -> terminal_return_20d
native_universe_panel.entry_date -> entry_date
native_universe_panel.entry_pos -> entry_pos
native_universe_panel.entry_price -> entry_price

fast_fail := lower_first OR same_bar_conflict
```

`native_label_panel.parquet` is cross-check only for:

```text
native_label_panel.split
native_label_panel.upper_barrier
native_label_panel.lower_barrier
native_label_panel.winner_positive
native_label_panel.upper_first
native_label_panel.lower_first
native_label_panel.same_bar_conflict
native_label_panel.horizon_complete
```

The cross-check key is `(instrument, reference_date, row_id)`. If `native_label_panel` disagrees with `native_universe_panel` on any overlapping selected-label field, cache invalid and rebuild required. `native_label_panel` must never be used as the source for `terminal_return_20d`, because it does not contain `horizon_close_return`.

Adapter 只能改列名、派生 `fast_fail` 和单位标签，不得改 row set、barrier value、label value、entry price 或 split boundary。若 cache 中既存在 source field 又存在 target field，二者必须逐行一致；否则 cache invalid and rebuild required。

### 4.2 12A7g label lineage

14A 必须沿用 12A7g 选出的 label identity 与 barrier formula：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
label_type = vol_scaled
vol_reference_id = volatility_20d
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
entry_anchor = next executable open
same_bar_priority = lower_first
```

Primary path-window convention 必须显式写入 lineage：

```text
selected_label_identity_source = 12A7g label_formula_audit
primary_label_path_window_source = 13A implemented native label panel
implemented_path_window = entry_pos_through_entry_pos_plus_horizon_inclusive
entry_anchor = next executable open
```

12A7g `label_formula_audit.path_window` 当前记录为 `reference_pos_through_reference_pos_plus_horizon_inclusive`。14A 不得静默混用两套 path window。Primary decision 使用 13A 已发布 native universe / native label lineage 的 next-open entry implementation；同时必须在 `upstream_lineage_audit.csv` 记录：

```text
upstream_formula_path_window
implemented_path_window
path_window_reconciliation_status
path_window_reconciliation_reason
```

Allowed status values:

```text
pass_same_as_upstream_formula
pass_with_documented_13a_entry_anchor
fail_13a_entry_anchor_not_reproducible
fail_unexpected_path_window_conflict
```

若 13A native label panel 不能用 raw qfq bars 复现 entry-anchored labels，14A 必须 fail closed；不得退回 reference_pos-window 重算后继续 primary decision。Reference_pos-window 只能作为 diagnostic mismatch audit，不得进入 utility gate。

Entry-anchor label reproducibility audit defaults:

```text
minimum_audited_rows = min(500, all cache rows with horizon_complete)
sample_method = deterministic hash sample by row_id
allowed_label_mismatch_rate = 0.0000
allowed_barrier_abs_tolerance = 1e-10
allowed_terminal_return_abs_tolerance = 1e-10
```

必需 lineage artifacts：

```text
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_separability_decision.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_formula_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_selection_train_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_split_boundary_audit.csv
SOURCE_EP12_ROOT/outputs/manifests/12A7g_vol_scaled_label_panel_c0_separability_triage_manifest.json
```

`vol_scaled_label_separability_decision.csv` 必须满足：

```text
input_gate_status = pass
lineage_gate_status = pass
selected_label_id = vol20d_kup2p0_kdn1p0_H20
```

12A7g 的 `decision_state = 12A7g_baserate_only_not_separable_stop_winner_selection` 不是 blocker。它只说明 C0 separability 路线失败，不否定 14A 重新检验 sparse state-change event。

### 4.3 禁止继承 / 禁止主张

14A 明确不得继承：

```text
C0 active band
C0 thresholds
C0 event family formula
C0 survivor / stage-2 decision
13A selected dense token as event membership
13A volatility_20d__bottom_20pct dense state as event family
13A2 directional filter shortlist as event family
13A3 / 13C repair_range_participation_core_30 as event membership
13E nonlinear model scores
13F delayed-entry folds or delayed-entry panels
13G rule overlay actions or overlay utility
```

14A 可以读取 13C / 13E / 13F / 13G decision artifacts 作为 negative context lineage，但不得把这些 artifact 的逐行 outputs 当作 14A event truth。

14A 不能主张：

```text
13A dense token was almost deployable.
compression repair state is revived.
defense overlay can rescue failed winner-entry utility.
cohort rank AUC improvement equals deployable utility.
```

14A 只能主张：

```text
full-native sparse first-trigger state-change event, optionally cohort-normalized with strict PIT rank,
does / does not transport opportunity into same-event after-cost utility.
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/data/processed/index/benchmark_indices_daily.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

PIT universe 必须至少提供：

```text
instrument
date or usable_trade_date
board_bucket or board_code
is_executable or equivalent executable flag
listed / ST / suspension fields when available
```

qfq daily bar 必须至少提供：

```text
date
open
high
low
close
volume or amount or money or turnover_rate, if available
```

benchmark 必需提供：

```text
index_alias = all_a
date or trade_date
open
high
low
close
```

若 `all_a` 不存在，F1 residual family 必须 disabled 并记录 `family_input_status = blocked_missing_benchmark`。若 remaining family count 低于 4，14A input gate fail closed。

The files in §5.1 are local data artifacts and may be outside VCS. Their existence cannot be inferred from git or file-search indexes. The runner must verify each required input by direct filesystem read, sha256, row count, and schema audit. Missing required local data must map to:

```text
decision_state = 14A_input_blocked
gate_failure = required_local_data_artifact_missing
```

`regime_daily_series_audit.csv` is used only to preserve 13A / 12A7g lineage and to reproduce `native_scope` exclusions when rebuilding 13A native universe. It must not be used to select event family, threshold, cohort arm, rank cutoff, or validation interpretation beyond the already frozen split labels.

### 5.2 Row identity and split

逐行身份：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
reference_pos = qfq position at reference_date
entry_date = immediate next executable open after reference_date
entry_pos = qfq position at entry_date
entry_price = qfq open at entry_pos
decision_time = reference_date close
execution_time = entry_date open
split_bucket in {train, validation, robustness}
```

同一 `(instrument, reference_date)` 只能保留一行。重复 row 必须进入 audit 并 fail closed，除非可由完全相同内容去重且 sha256 lineage 可证明。

Split boundary 必须从 12A7g / 13A 可审计 artifact 读取。不得从 label 结果、event 结果或报告文本反推 split。若 split boundary 不可证明，状态为：

```text
14A_input_blocked
gate_failure = split_boundary_unavailable
```

### 5.3 Label rebuild

14A 必须重建或校验 selected label，而不是直接相信聚合表。

Label 计算：

```text
daily_return[t] = close[t] / close[t - 1] - 1
volatility_20d = std(daily_return over reference_pos - 19 ... reference_pos, ddof=0)

if vol_reference_unit == daily_return_std:
  vol_horizon_scale = volatility_20d_at_reference * sqrt(20)
elif vol_reference_unit == horizon_return_vol:
  vol_horizon_scale = volatility_20d_at_reference
else:
  vol_horizon_scale = audited_transform_recorded_in_12A7g_label_formula_audit

upper_barrier_return = 2.0 * vol_horizon_scale
lower_barrier_return = -1.0 * vol_horizon_scale
horizon_window = qfq rows from entry_pos through entry_pos + 20, inclusive
upper_touch at offset s = high[entry_pos + s] / entry_price - 1 >= upper_barrier_return
lower_touch at offset s = low[entry_pos + s] / entry_price - 1 <= lower_barrier_return
winner = first upper_touch before first lower_touch
fast_fail = first lower_touch before first upper_touch
same_bar_conflict = upper_touch and lower_touch at the same first offset
same_bar_conflict -> winner = false, fast_fail = true
```

`entry_pos` is the immediate next executable open after `reference_date`. This path-window convention is intentionally the 13A implemented native-label convention. It differs from the 12A7g formula-audit text field and must be audited as described in §4.2.

Horizon 不完整的 row 不得进入 primary label panel。Label cache mismatch 超过预注册容差时，input gate fail closed。

## 6. Sparse Event Family Formula Freeze

14A 只允许以下 6 个 event families。每个 family 必须输出：

```text
family_id
parameter_set_id
event_id
instrument
reference_date
event_t0_pos
event_signal_time = t0_close
entry_date
entry_price
event_intensity_score
reset_state_id
cooldown_sessions
first_trigger_flag
duplicate_within_cooldown_flag
family_input_status
```

`event_intensity_score` 必须在 t0 close 后、next-open 前可知，且方向固定为 higher is stronger。若某 family 无法定义 monotonic intensity，该 family 不得进入 cohort normalization，只能做 raw event audit。

### 6.1 Frozen family grid

默认 family 与参数网格：

```text
F1 residual_cusum_break
  feature: one-sided positive CUSUM of stock residual return vs all_a benchmark
  lookback_sessions: {60, 120}
  beta_min_observations: 40
  residual_vol_window: same as lookback_sessions
  trigger_threshold_z: {2.5, 3.0}
  reset_condition: cusum_z <= 0.5 or residual return <= 0
  cooldown_sessions: 20
  event_intensity_score: cusum_z

F2 compression_to_directional_expansion
  feature: train-frozen low volatility / narrow range compression followed by positive range expansion
  compression_window: 20
  compression_threshold_rule: train bottom 20pct
  expansion_ratio_threshold: {1.5, 2.0}
  direction_condition: close_to_close_return_1d > 0
  reset_condition: compression_state = false for 5 consecutive sessions
  cooldown_sessions: 20
  event_intensity_score: range_expansion_ratio

F3 controlled_damage_first_reclaim
  feature: first reclaim after controlled drawdown
  damage_lookback_sessions: {20, 60}
  max_drawdown_band: [-0.35, -0.10]
  reclaim_rule: close >= moving_average_20d and close_to_close_return_1d > 0
  reset_condition: new 20d high or drawdown_band exits for 5 consecutive sessions
  cooldown_sessions: 20
  event_intensity_score: reclaim_distance_to_ma20

F4 board_relative_strength_rank_jump
  feature: board-relative return percentile jump
  relative_return_window: {20, 60}
  rank_jump_decile_threshold: {2, 3}
  board_cohort: same board_bucket, same reference_date, primary native universe rows only
  intensity_observable_at: t0_close_after_full_board_close
  reset_condition: percentile_rank falls below prior rank for 5 consecutive sessions
  cooldown_sessions: 15
  event_intensity_score: percentile_rank_delta

F5 participation_ignition_with_price_control
  feature: participation spike with controlled positive price action
  participation_metric_priority: money, amount, turnover_rate, volume
  participation_window: {20, 60}
  participation_ratio_threshold: {1.5, 2.0}
  price_control_band: close_to_close_return_1d in [0.00, 0.06]
  disallow_limit_like_bar: true when limit flag or close_to_close_return_1d >= 0.095
  reset_condition: participation_ratio < 1.0 for 5 consecutive sessions
  cooldown_sessions: 15
  event_intensity_score: participation_ratio

F6 low_volatility_range_expansion_first_trigger
  feature: first upside range expansion after low realized volatility
  volatility_window: 20
  low_vol_threshold_rule: train bottom 20pct
  range_expansion_ratio_threshold: {1.5, 2.0}
  direction_condition: close > open and close_to_close_return_1d > 0
  reset_condition: low_vol_state = false for 5 consecutive sessions
  cooldown_sessions: 20
  event_intensity_score: range_expansion_ratio
```

Search accounting defaults：

```text
family_count = 6
parameter_grid_count = 16
family_parameter_grid_count:
  F1 = 4
  F2 = 2
  F3 = 2
  F4 = 4
  F5 = 2
  F6 = 2
cohort_arm_family_count = 6
rank_cutoff_grid = {top20pct, top10pct}
maximum_train_selected_raw_arms_into_cohort = 6
maximum_operating_arms_allowed_into_validation = 3
validation_used_for_family_selection = false
robustness_used_for_family_selection = false
```

Synthetic tests 可以使用更小 grid，但 full run 必须输出完整 grid accounting。新增 family、阈值、feature、rank cutoff 或 cohort arm 必须另开 requirement。

F4 raw intensity depends on same-date board cross-section. It is allowed only under the same PIT premise as C1 / C2: all same-date board membership, executable flags, and t0 close features must be observable after full board close and before next-open entry. If this cannot be proven, F4 must be disabled with `family_input_status = blocked_pit_availability`.

### 6.2 First-trigger, reset, cooldown

所有 family 必须遵守：

```text
raw_state_true[t] computed only from data <= t0 close
transition_event[t] = raw_state_true[t] and not raw_state_true[t - 1]
eligible_event[t] = transition_event[t] and cooldown since previous accepted event for same instrument-family-parameter
accepted_event[t] = eligible_event[t] and reset condition satisfied since previous event
```

同一 `(instrument, family_id, parameter_set_id)` 在 cooldown 内重复触发时，只保留第一条，并记录：

```text
duplicate_within_cooldown_flag = true for suppressed rows
duplicate_suppressed_n
```

被 suppressed 的 duplicate 不得进入 event denominator，但必须进入 density audit。

### 6.3 Density and duplicate controls

默认 event density gate：

```text
min_train_event_n_per_parameter = 100
min_validation_event_n_per_operating_arm = 30
min_robustness_event_n_per_operating_arm = 30
target_max_event_density_per_instrument_year = 3.0
hard_max_event_density_per_instrument_year = 6.0
max_duplicate_episode_fraction = 0.35
min_average_uniqueness = 0.50
```

`hard_max_event_density_per_instrument_year` 任何 split 失败时，该 parameter arm 不得进入 cohort normalization。若所有 arms 因 density / duplicate 失败，decision 为：

```text
14A_stop_density_duplicate_or_morphology_rediscovery
gate_failure = density_duplicate_gate_failed
```

## 7. Raw Event Utility Preflight

Raw event preflight 在 cohort normalization 之前运行。每个 `(family_id, parameter_set_id, split_bucket)` 必须输出：

```text
event_n
instrument_n
instrument_year_n
event_density_per_instrument_year
winner_positive_n
winner_rate
native_baseline_winner_rate
winner_rate_lift
fast_fail_rate
native_baseline_fast_fail_rate
fast_fail_uplift
lower_first_rate
native_baseline_lower_first_rate
lower_first_uplift
same_bar_conflict_rate
median_upper_barrier_return
median_abs_lower_barrier_return
terminal_return_20d_mean
terminal_return_60d_mean
terminal_return_120d_mean
mfe_return_20d_median
mfe_return_60d_median
mfe_return_120d_median
native_baseline_mfe_return_20d_median
native_baseline_mfe_return_60d_median
native_baseline_mfe_return_120d_median
mae_return_20d_median
mae_return_60d_median
mae_return_120d_median
native_baseline_mae_return_20d_median
native_baseline_mae_return_60d_median
native_baseline_mae_return_120d_median
utility_per_event_mean_0bps
utility_per_event_mean_50bps
utility_per_event_mean_100bps
utility_total_indexed_50bps
badside_gate_status
raw_opportunity_surface_status
```

Raw path utility uses selected label barriers:

```text
path_utility_component(cost_tier_bps) =
  if upper_first: upper_barrier_return - cost_buffer_return
  elif lower_first or same_bar_conflict: lower_barrier_return - cost_buffer_return
  else: terminal_return_20d - cost_buffer_return

cost_buffer_return:
  0bps = 0.0000
  50bps = 0.0050
  100bps = 0.0100

utility_per_event_mean_{tier} = mean(path_utility_component(tier) over raw event denominator)
utility_total_indexed_{tier} = sum(path_utility_component(tier)) / native_split_denominator_n
```

Native baseline for raw opportunity surface is frozen as:

```text
native_baseline_denominator = all 13A native_scope rows in same split_bucket
native_baseline_winner_rate = mean(winner over native_baseline_denominator)
native_baseline_fast_fail_rate = mean(fast_fail over native_baseline_denominator)
native_baseline_lower_first_rate = mean(lower_first OR same_bar_conflict over native_baseline_denominator)
native_baseline_mfe_return_{H}d_median =
  median(max high return over entry_pos ... entry_pos + H among native_baseline_denominator)
native_baseline_mae_return_{H}d_median =
  median(min low return over entry_pos ... entry_pos + H among native_baseline_denominator)
H in {20, 60, 120}
```

Rows without complete path for H must be excluded from that H-specific baseline and event metric, with denominator counts reported separately.

Raw opportunity surface gate uses train split only for admission into 14A3:

```text
raw_opportunity_surface_status = pass if any:
  train winner_rate_lift >= 0.02
  train utility_per_event_mean_0bps > 0
  train mfe_return_20d_median > native_baseline_mfe_return_20d_median
  train event_intensity_score top20pct winner_rate - bottom20pct winner_rate >= 0.03
```

The raw intensity top/bottom readout is computed only within each `(family_id, parameter_set_id)` train event denominator:

```text
raw_intensity_top20pct = train events with event_intensity_score >= train p80
raw_intensity_bottom20pct = train events with event_intensity_score <= train p20
raw_intensity_top_bottom_winner_rate_delta =
  mean(winner in raw_intensity_top20pct) - mean(winner in raw_intensity_bottom20pct)

minimum top side event_n = 30
minimum bottom side event_n = 30
tie handling = include all tied rows at p20 / p80 boundary
if either side event_n < 30, this admission clause is not met
```

若 no family / parameter passes `raw_opportunity_surface_status`, decision 为：

```text
14A_stop_no_sparse_event_utility
gate_failure = no_raw_sparse_event_surface
```

Raw utility pass is not required for 14A3 admission. A raw event may enter cohort transport if it has opportunity / ranking surface but no raw 50bps utility.

## 8. Strict PIT Cohort Normalization

Cohort normalization 是 14A 的主实验臂。它只能运行在 train-selected raw event arms 上，且不得使用 validation / robustness 选择 cohort family、rank cutoff、threshold 或 operating arm。

### 8.1 Allowed cohort arms

允许的 cohort arms：

```text
C1 same_date_full_cross_section
C2 same_date_same_board_cross_section
C3 rolling_prior_event_family_252d
C4 rolling_prior_board_event_family_252d
C5 month_to_date_partial_event_cohort
C6 week_to_date_partial_event_cohort
```

每个 cohort arm 必须证明：

```text
decision_time = t0 close
entry_time = next executable open
cohort membership observable before entry
board / executable flags observable before entry
event_intensity_score observable before entry
rank computed only from rows with date <= t0 for rolling / partial cohorts
```

Same-date cross-section arms 是最大 PIT 风险源。若不能证明 same-date membership / board / executable flags / t0 features 在 next-open 前可知，该 arm 必须：

```text
cohort_arm_status = blocked_pit_availability
used_in_primary_decision = false
```

不得降级为可用诊断。

禁止的 normalization：

```text
whole-month full cohort rank
whole-split rank
future event count
post-entry cohort statistic
validation-selected rank cutoff
robustness-selected rank cutoff
report-derived cohort membership
```

### 8.2 Rank cutoff and selected-entry accounting

Rank cutoff grid：

```text
rank_cutoff_id in {top20pct, top10pct}
top20pct: cohort_percentile_rank >= 0.80
top10pct: cohort_percentile_rank >= 0.90
rank_direction = high_is_stronger
```

Percentile rank formula and cohort denominator are frozen:

```text
cohort_percentile_rank =
  (count(cohort rows with finite event_intensity_score <= current event_intensity_score)
   - 0.5 * count(cohort rows with event_intensity_score == current event_intensity_score))
  / cohort_finite_n

missing or non-finite event_intensity_score -> cohort_rank_status = missing_intensity
cohort_finite_n below arm minimum -> cohort_rank_status = insufficient_cohort
partial cohort with no prior peer besides current event -> cohort_rank_status = degenerate_partial_cohort
ties are handled by midpoint rank
rank is computed separately for each family_id / parameter_set_id
```

Cohort denominator by arm:

```text
C1 same_date_full_cross_section:
  cohort rows = all 13A native_scope rows on reference_date with finite intensity
  minimum cohort_finite_n = 100

C2 same_date_same_board_cross_section:
  cohort rows = all 13A native_scope rows on reference_date and same board_bucket with finite intensity
  minimum cohort_finite_n = 30

C3 rolling_prior_event_family_252d:
  cohort rows = accepted events from the same family_id / parameter_set_id
                with reference_date in [t0 - 252 trading sessions, t0 - 1]
  current event is not included in the reference distribution
  percentile = share of prior accepted event scores <= current event score
  minimum cohort_finite_n = 50

C4 rolling_prior_board_event_family_252d:
  cohort rows = accepted events from the same family_id / parameter_set_id and same board_bucket
                with reference_date in [t0 - 252 trading sessions, t0 - 1]
  current event is not included in the reference distribution
  minimum cohort_finite_n = 30

C5 month_to_date_partial_event_cohort:
  cohort rows = accepted events from same family_id / parameter_set_id
                with calendar month equal to current event month and reference_date <= t0
  current event may be included because all rows are observable at t0 close
  minimum cohort_finite_n = 20

C6 week_to_date_partial_event_cohort:
  cohort rows = accepted events from same family_id / parameter_set_id
                with ISO week equal to current event week and reference_date <= t0
  current event may be included because all rows are observable at t0 close
  minimum cohort_finite_n = 10
```

For C1 / C2, intensity must be computed for all native-scope rows, not only accepted events. For C3-C6, intensity must be computed for accepted event rows only. If an arm cannot meet this denominator contract, it is `blocked_cohort_denominator_contract` and cannot enter primary decision.

For C5 / C6, the current event may be included in the partial cohort, but a partial cohort is primary-eligible only when at least one other accepted event exists in the same partial period. Otherwise `cohort_rank_status = degenerate_partial_cohort` and the row cannot be selected by primary rank cutoff.

For each `(raw_event_arm_id, cohort_arm_id, rank_cutoff_id)`, utility accounting must keep the raw event denominator fixed:

```text
same_event_denominator_n = raw_event_n for the same family / parameter / split
selected_event_n = events passing cohort rank cutoff
skipped_event_n = same_event_denominator_n - selected_event_n

selected event utility = path_utility_component(cost_tier_bps)
skipped event utility = 0

same_event_utility_mean_{tier} =
  sum(selected event utility at tier) / same_event_denominator_n

selected_entry_diagnostic_utility_mean_{tier} =
  mean(selected event utility at tier over selected_event_n)
```

`selected_entry_diagnostic_utility_mean` 只能作为诊断字段，不得用于 primary decision。任何把 skipped events 从 denominator 删除后才为正的读数，必须标记为：

```text
utility_transport_status = selected_entry_only_not_full_denominator
```

### 8.3 Train-only operating arm selection

Operating arm selection uses train split only:

```text
candidate_raw_arms = raw event arms with:
  density_gate_status = pass
  raw_opportunity_surface_status = pass
  family_input_status = pass

candidate_cohort_arms = cohort arms with:
  cohort_availability_gate_status = pass
  train same_event_utility_mean_50bps > 0
  train selected_event_n >= 50
  train selected_event_fraction between 0.03 and 0.50
```

where:

```text
selected_event_fraction = selected_event_n / same_event_denominator_n
```

Train ranking score:

```text
train_selection_score =
  2.0 * same_event_utility_mean_50bps
  + 1.0 * winner_rate_lift
  - 1.0 * max(fast_fail_uplift, 0)
  - 0.5 * duplicate_episode_fraction
```

Tie-breaking:

```text
1. higher train same_event_utility_mean_50bps
2. lower train fast_fail_uplift
3. lower event_density_per_instrument_year
4. lower morphology_rediscovery_score
5. lexicographic raw_event_arm_id / cohort_arm_id / rank_cutoff_id
```

Only the top `maximum_operating_arms_allowed_into_validation = 3` train-selected arms may be read as operating arms in validation / robustness decision. All other arms remain diagnostic and must be excluded from positive decision evidence.

## 9. Morphology Rediscovery Gate

14A must test whether positive arms are merely rediscovering previously failed morphology.

Required comparisons:

```text
13A volatility_20d__bottom_20pct overlap
13A volatility / range compression token family overlap
13A3 / 13C repair_range_participation_core_30 overlap when row-level lineage is available
broad drawdown / reversal proxy overlap
F2 / F6 compression / low-vol overlap
```

Required row-level sources for 13A overlap:

```text
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_token_matrix.parquet
```

Optional row-level sources for 13A3 / 13C repair overlap:

```text
SOURCE_EP13_ROOT/outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_repair_state_dictionary.csv
SOURCE_EP13_ROOT/outputs/local_cache/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_state_matrix.parquet
SOURCE_EP13_ROOT/outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_orthogonal_residual_importance_decision.csv
SOURCE_EP13_ROOT/outputs/local_cache/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_residual_panel.parquet
```

If optional repair-state caches are missing or fail schema validation, 14A may continue only if it records:

```text
repair_state_overlap_status = unavailable_optional_cache
repair_state_overlap_used_in_primary_gate = false
```

13A volatility / compression overlap remains required. If 13A native token matrix is missing and cannot be rebuilt from `native_token_dictionary.csv`, morphology gate must fail closed.

For each operating arm, output:

```text
arm_id
split_bucket
overlap_source_id
event_overlap_rate
selected_event_overlap_rate
utility_from_overlap_rows_50bps
utility_from_non_overlap_rows_50bps
winner_rate_lift_non_overlap
morphology_rediscovery_score
morphology_independent_evidence_status
```

`morphology_rediscovery_score` is frozen as:

```text
morphology_rediscovery_score =
  max(selected_event_overlap_rate over required overlap_source_id values)
```

If a required overlap source is unavailable, `morphology_rediscovery_score = 1.0` and `morphology_independent_evidence_status = fail_missing_required_overlap`. Optional 13A3 / 13C overlap sources do not force score to 1.0 when unavailable, but their missing status must be visible in the audit.

Default morphology fail conditions:

```text
selected_event_overlap_rate >= 0.70
and utility_from_non_overlap_rows_50bps <= 0
and winner_rate_lift_non_overlap < 0.02
```

F2 / F6 require stricter evidence:

```text
selected_event_overlap_rate with 13A compression / low-vol tokens < 0.50
or utility_from_non_overlap_rows_50bps > 0 in validation and robustness
```

F3 requires stricter drawdown / reversal evidence:

```text
selected_event_overlap_rate with broad drawdown / reversal proxy < 0.50
or utility_from_non_overlap_rows_50bps > 0 in validation and robustness
```

For F3, `morphology_rediscovery_audit.csv` must include:

```text
broad_drawdown_overlap_rate
broad_reversal_overlap_rate
f3_drawdown_reversal_independent_evidence_status
```

If the best operating arm fails morphology independent evidence, decision为：

```text
14A_stop_density_duplicate_or_morphology_rediscovery
gate_failure = morphology_rediscovery_gate_failed
```

## 10. Primary Gates

### 10.1 Gate list

14A 必须输出以下 gate：

```text
input_gate_status
upstream_lineage_gate_status
native_universe_gate_status
native_label_portability_gate_status
sparse_event_construction_gate_status
density_duplicate_gate_status
raw_opportunity_surface_gate_status
cohort_availability_gate_status
cohort_transport_gate_status
badside_veto_gate_status
same_event_utility_50bps_gate_status
morphology_rediscovery_gate_status
validation_stress_gate_status
search_accounting_gate_status
```

### 10.2 50bps same-event utility gate

Primary utility gate:

```text
same_event_utility_50bps_gate_status = pass if:
  selected train-frozen operating arm has
  validation same_event_utility_mean_50bps > 0
  and robustness same_event_utility_mean_50bps > 0
  and validation selected_event_n >= 30
  and robustness selected_event_n >= 30
```

If raw event arm is selected without cohort normalization, the same formula applies with:

```text
cohort_arm_id = raw_all_events
selected_event_n = same_event_denominator_n
skipped_event_n = 0
```

### 10.3 Cohort incremental utility gate

Cohort transport gate:

```text
cohort_transport_gate_status = pass if:
  selected cohort operating arm same_event_utility_mean_50bps
    > its raw_all_events same_event_utility_mean_50bps
  in train, validation, and robustness
  and validation / robustness improvement is not explained only by selected-entry denominator shrinkage
```

The denominator-shrinkage check is deterministic:

```text
same_event_utility_delta_50bps =
  cohort_arm_same_event_utility_mean_50bps
  - raw_all_events_same_event_utility_mean_50bps

selected_entry_utility_delta_50bps =
  cohort_arm_selected_entry_diagnostic_utility_mean_50bps
  - raw_all_events_utility_per_event_mean_50bps

cohort_transport_gate_status = pass only if:
  train same_event_utility_delta_50bps > 0
  and validation same_event_utility_delta_50bps > 0
  and robustness same_event_utility_delta_50bps > 0
  and validation same_event_utility_delta_50bps >= 0.0010
  and robustness same_event_utility_delta_50bps >= 0.0010

If selected_entry_utility_delta_50bps > 0 but same_event_utility_delta_50bps <= 0,
utility_transport_status = selected_entry_only_not_full_denominator.
```

If raw event utility already passes and no cohort arm improves it, decision may be:

```text
14A_diagnostic_raw_event_signal_but_no_cohort_transport
```

It must not authorize 14B. A raw-event-only follow-up requires a separate research-plan update and a new requirement with its own deterministic gates; it cannot be authorized through 14A's cohort-transport decision map.

### 10.4 Bad-side veto

Bad-side gate:

```text
badside_veto_gate_status = pass if:
  validation fast_fail_uplift <= 0.02
  and robustness fast_fail_uplift <= 0.02
  and validation lower_first_uplift <= 0.01
  and robustness lower_first_uplift <= 0.01
```

Same-bar lower-first conflict is included in lower-first and fast-fail. It must also be reported separately.

### 10.5 Validation stress interpretation

Validation split is a known stress interval:

```text
validation split = long drawdown / risk-off pressure interval
```

This caveat cannot lower any gate and cannot select thresholds. It only changes interpretation.

Required fields:

```text
validation_stress_status
stress_split_utility_50bps
stress_split_winner_opportunity_retained
stress_split_badside_exposure
stress_failure_type in {none, no_signal_failure, stress_regime_utility_transport_failure}
```

If robustness passes but validation 50bps same-event utility fails, the primary decision remains the same-event full-denominator failure state. Validation stress must be reported as an interpretation gate, not used as a weaker alternate threshold:

```text
decision_state = 14A_diagnostic_cohort_signal_only_no_utility
gate_failure = same_event_utility_50bps_failed
validation_stress_gate_status = fail
stress_failure_type = stress_regime_utility_transport_failure
```

## 11. Decision State Mapping

14A decision table must contain:

```text
decision_state
next_allowed_requirement
active_winner_entry_search_authorized
confirmatory_status
selected_raw_event_arm_id
selected_family_id
selected_parameter_set_id
selected_cohort_arm_id
selected_rank_cutoff_id
primary_cost_tier_bps
primary_failure_reason
gate_failure
input_gate_status
upstream_lineage_gate_status
native_universe_gate_status
native_label_portability_gate_status
sparse_event_construction_gate_status
density_duplicate_gate_status
raw_opportunity_surface_gate_status
cohort_availability_gate_status
cohort_transport_gate_status
badside_veto_gate_status
same_event_utility_50bps_gate_status
morphology_rediscovery_gate_status
validation_stress_gate_status
search_accounting_gate_status
```

Deterministic decision precedence：

```text
1. Any required input / lineage / label / split / PIT availability failure:
   decision_state = 14A_input_blocked
   next_allowed_requirement = none

2. Sparse event construction fails for all families:
   decision_state = 14A_stop_no_sparse_event_utility
   gate_failure = sparse_event_construction_gate_failed
   next_allowed_requirement = none

3. Density / duplicate gate fails for all candidate arms:
   decision_state = 14A_stop_density_duplicate_or_morphology_rediscovery
   gate_failure = density_duplicate_gate_failed
   next_allowed_requirement = none

4. No raw event arm has train opportunity / ranking surface:
   decision_state = 14A_stop_no_sparse_event_utility
   gate_failure = no_raw_sparse_event_surface
   next_allowed_requirement = none

5. Raw opportunity exists, but all PIT cohort arms are unavailable or PIT-unsafe:
   decision_state = 14A_stop_no_cohort_utility_transport
   gate_failure = cohort_availability_gate_failed
   next_allowed_requirement = none

6. Cohort rank improves winner / ranking readout but same-event 50bps utility fails:
   decision_state = 14A_diagnostic_cohort_signal_only_no_utility
   gate_failure = same_event_utility_50bps_failed
   next_allowed_requirement = none

7. Raw event has signal or raw utility, but cohort transport does not improve same-event utility:
   decision_state = 14A_diagnostic_raw_event_signal_but_no_cohort_transport
   gate_failure = cohort_transport_gate_failed
   next_allowed_requirement = none

8. A distinct pre-registered validation stress audit fails after same-event utility would otherwise pass:
   decision_state = 14A_stop_validation_stress_failure_no_active_entry_authorization
   gate_failure = validation_stress_utility_failed
   next_allowed_requirement = none

9. Best arm fails morphology independent evidence:
   decision_state = 14A_stop_density_duplicate_or_morphology_rediscovery
   gate_failure = morphology_rediscovery_gate_failed
   next_allowed_requirement = none

10. A train-frozen sparse event + PIT cohort arm passes all primary gates:
    decision_state = 14A_supported_open_14B_confirmatory_sparse_event_requirement
    next_allowed_requirement = requirement_14b_confirmatory_sparse_event_requirement.md
```

All non-supported states must set:

```text
active_winner_entry_search_authorized = false
confirmatory_status = false
```

Supported state may set:

```text
active_winner_entry_search_authorized = true
confirmatory_status = false
```

14A support authorizes only the writing of 14B confirmatory requirement, not trading, deployment, sizing, or model training.

## 12. Required Outputs

### 12.1 Publishable tables

Required table directory:

```text
outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/
```

Must include:

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
cache_schema_adapter_audit.csv
native_label_portability_audit.csv
row_level_rebuild_audit.csv
sparse_event_family_formula_spec.csv
sparse_event_parameter_grid_audit.csv
sparse_event_generation_audit.csv
sparse_event_density_audit.csv
sparse_event_raw_readout.csv
sparse_event_badside_utility_audit.csv
sparse_event_uniqueness_density_audit.csv
pit_cohort_normalization_dictionary.csv
pit_cohort_rank_availability_audit.csv
pit_cohort_normalized_utility_readout.csv
cohort_normalization_transport_audit.csv
morphology_rediscovery_audit.csv
validation_stress_interpretation_audit.csv
search_multiplicity_audit.csv
full_native_sparse_state_change_event_utility_decision.csv
```

### 12.2 Local cache

Optional cache directory:

```text
outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/
```

Allowed cache files:

```text
native_rebuild_panel.parquet
state_change_feature_panel.parquet
sparse_event_panel.parquet
pit_cohort_normalized_event_panel.parquet
```

Cache files are implementation accelerators only. They must not replace publishable audits.

### 12.3 Manifest and report

Required manifest:

```text
outputs/manifests/14A_full_native_sparse_state_change_event_utility_preflight_manifest.json
```

Required report:

```text
outputs/publishable/reports/full_native_sparse_state_change_event_utility_preflight_report.md
```

Report must include:

1. 单行裁决与 `decision_state`。
2. 14A 是否支持打开 14B，以及原因。
3. Input / lineage / label / split / PIT availability audit summary。
4. Sparse event family construction、density、duplicate、uniqueness summary。
5. Raw event opportunity / bad-side / utility readout。
6. PIT cohort normalization availability 与 same-event utility transport readout。
7. Validation stress interval interpretation，不降低 gate。
8. Morphology rediscovery audit，尤其 F2 / F6 是否只是 compression / low-vol 换名。
9. Search accounting：family count、parameter grid count、cohort-arm count、rank cutoff count、validation / robustness 未参与 selection。
10. Failure state 的含义区分：`no_sparse_event_surface`、`ranking_to_utility_transport_failed`、`stress_validation_failure`。

## 13. Implementation Notes

Implementation should prefer deterministic rebuilds and explicit joins:

```text
1. Load and audit required inputs.
2. Rebuild or validate 13A native universe panel and selected label panel.
3. Compute t0-close observable feature panel for all families.
4. Generate raw state, transition event, reset, cooldown, and accepted sparse event panel.
5. Compute selected label, path utility, raw readouts, density, duplicate, uniqueness.
6. Select raw arms for cohort normalization using train-only criteria.
7. Compute PIT cohort ranks and availability audit for allowed arms.
8. Select at most 3 operating arms using train-only score.
9. Read validation / robustness only after operating arm freeze.
10. Run morphology rediscovery, validation stress, and search accounting audits.
11. Emit deterministic decision table, report, cache, and manifest.
```

Implementation must keep these columns stable across row-level cache and publishable outputs:

```text
instrument
reference_date
split_bucket
family_id
parameter_set_id
event_id
raw_event_arm_id
cohort_arm_id
rank_cutoff_id
same_event_denominator_flag
selected_event_flag
skipped_event_flag
winner
fast_fail
same_bar_conflict
upper_barrier_return
lower_barrier_return
terminal_return_20d
path_utility_component_0bps
path_utility_component_50bps
path_utility_component_100bps
```

For reused 13A cache fields, the implementation must also preserve these adapter audit columns:

```text
source_artifact_id
source_column
target_column
adapter_rule
row_count_checked
value_match_status
unit_match_status
required_for_primary
adapter_status
```

The following adapter rows are required at minimum:

```text
native_universe_panel.split -> split_bucket
native_universe_panel.upper_barrier -> upper_barrier_return
native_universe_panel.lower_barrier -> lower_barrier_return
native_universe_panel.winner_positive -> winner
native_universe_panel.lower_first + native_universe_panel.same_bar_conflict -> fast_fail
native_universe_panel.horizon_close_return -> terminal_return_20d
native_label_panel.instrument + native_label_panel.reference_date + native_label_panel.row_id -> native_universe_panel cross_check key coverage
native_label_panel.split -> native_universe_panel.split cross_check
native_label_panel.upper_barrier -> native_universe_panel.upper_barrier cross_check
native_label_panel.lower_barrier -> native_universe_panel.lower_barrier cross_check
native_label_panel.winner_positive -> native_universe_panel.winner_positive cross_check
native_label_panel.upper_first -> native_universe_panel.upper_first cross_check
native_label_panel.lower_first -> native_universe_panel.lower_first cross_check
native_label_panel.same_bar_conflict -> native_universe_panel.same_bar_conflict cross_check
native_label_panel.horizon_complete -> native_universe_panel.horizon_complete cross_check
```

## 14. Test Expectations

Minimum tests:

```text
test_input_artifact_audit_fail_closed
test_13a_cache_mismatch_forces_rebuild_or_blocks
test_13a_cache_schema_adapter_audit_required
test_13a_adapter_primary_source_is_native_universe_panel
test_fast_fail_derived_from_lower_first_or_same_bar_conflict
test_label_path_window_reconciliation_uses_13a_entry_anchor
test_selected_label_lower_first_same_bar_rule
test_sparse_event_first_trigger_reset_cooldown
test_duplicate_within_cooldown_suppressed_from_event_denominator
test_family_grid_search_accounting_counts
test_f4_same_date_board_rank_requires_pit_availability
test_raw_opportunity_native_baseline_mfe_defined
test_raw_intensity_top_bottom_percentile_train_only
test_raw_opportunity_surface_train_only_admission
test_same_date_cohort_pit_availability_required
test_cohort_rank_excludes_future_rows
test_cohort_rank_denominator_contract_by_arm
test_partial_cohort_degenerate_status_excluded_from_primary
test_same_event_denominator_keeps_skipped_events_as_zero
test_selected_entry_utility_not_allowed_for_primary_decision
test_cohort_transport_requires_same_event_delta_threshold
test_validation_not_used_for_operating_arm_selection
test_badside_veto_includes_same_bar_lower_first
test_morphology_rediscovery_blocks_compression_rename
test_f3_drawdown_reversal_overlap_uses_stricter_gate
test_required_13a_token_overlap_missing_fails_morphology_gate
test_raw_only_signal_does_not_authorize_14b
test_same_event_failure_takes_precedence_over_stress_stop
test_supported_state_requires_validation_and_robustness_50bps_positive
test_decision_precedence_input_blocked_before_diagnostic_states
test_manifest_contains_report_and_all_publishable_tables
```

Synthetic fixtures may use a reduced universe, family grid, and cohort arms, but must preserve:

```text
train-only freeze
PIT cohort availability checks
same-event denominator accounting
lower-first same-bar rule
decision precedence
```
