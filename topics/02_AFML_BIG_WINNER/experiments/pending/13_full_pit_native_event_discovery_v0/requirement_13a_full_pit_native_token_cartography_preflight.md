# 需求：13A Full-PIT Native Token Cartography Preflight

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
6. 不得从报告文本、聚合表、图像或人工讨论文本反推出逐行 universe、标签、token、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 13_full_pit_native_event_discovery_v0
phase_id = 13A
run_id = 13A_full_pit_native_token_cartography_preflight
status = spec_draft_pending_review
expected_entrypoint = src/run_13a_full_pit_native_token_cartography_preflight.py
expected_config = configs/config_13a_full_pit_native_token_cartography_preflight.yaml
expected_test_file = tests/test_13a_full_pit_native_token_cartography_preflight.py
source_discussion = SOURCE_EP12_ROOT/discussion3.md
upstream_requirement = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
upstream_report = SOURCE_EP12_ROOT/outputs/publishable/reports/vol_scaled_label_panel_c0_separability_triage_report.md
```

本需求是 Episode 13 的第一份 requirement。它关闭 Episode 12 的 C0 修补路线，重开一个 C0-free 的 full-PIT native event discovery episode。

核心继承关系：

```text
12A7g full PIT vol-scaled universe
  -> Episode 13 full_pit_native_opportunity_universe
     -> len-1 token cartography preflight
```

13A 只做 preflight / cartography，不做 sequence mining。只有 13A 通过全部 gate，才允许新建：

```text
requirement_13b_train_frozen_event_sequence_mining.md
```

## 2. 核心问题

13A 回答以下问题：

```text
Q1. 能否在不使用 C0 阈值的前提下，从 full PIT executable universe 构造
    可复现、PIT-safe、next-open executable 的 native opportunity universe？

Q2. 12A7g 选出的 vol-scaled winner label
    vol20d_kup2p0_kdn1p0_H20
    在 native opportunity universe 上是否仍具备可接受的 base-rate 稳定性？

Q3. 宽口径 len-1 token family 是否在 train 中产生 winner uplift，
    并在 validation / robustness 中保持方向一致？

Q4. 胜出 token 是否只是 broad reversal / drawdown / C0-like morphology 的重新发现？
    若是，它是否仍通过 bad-side veto 与 utility gate？

Q5. 是否存在足够可部署的 native token，值得进入 13B 的 event sequence mining？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. 继承边界

### 3.1 允许继承自 12A7g

13A 可以继承 12A7g 的以下定义与审计思路：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
reference_pos = qfq daily position for reference_date
entry_date = next executable open after reference_date
entry_pos = qfq daily position for entry_date
entry_price = qfq open at entry_pos
qfq primitive rebuild formula
regime_calendar_available and missing regime date bypass
supported board filter
next-open executable assertion
required pre-vol lookback complete
selected_label_id = vol20d_kup2p0_kdn1p0_H20
```

12A7g 的 publishable tables 只作为 label 选择与最终裁决 lineage：

```text
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_panel_summary.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_separability_decision.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_formula_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_selection_train_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/pre_registered_threshold_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_split_boundary_audit.csv
SOURCE_EP12_ROOT/outputs/manifests/12A7g_vol_scaled_label_panel_c0_separability_triage_manifest.json
```

12A7g 的 local cache 可以作为可选加速输入，但不得作为唯一真相：

```text
SOURCE_EP12_ROOT/outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/full_pit_vol_scaled_label_panel.parquet
SOURCE_EP12_ROOT/outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/c0_vol_scaled_label_matrix.parquet
```

若使用 local cache，runner 必须验证 sha256、schema、row key 唯一性、date range、selected label 一致性，并在 `upstream_12a7g_lineage_audit.csv` 标明 `cache_used = true`。若 cache 不存在或校验失败，runner 必须从 raw PIT universe 与 qfq daily bars 重建，不得 fail open。

### 3.2 禁止继承自 12A7g / C0

13A 明确不得复用以下内容：

```text
full_pit_c0_comparable_active_band
C0-derived active-band thresholds
C0 entry denominator as opportunity universe
C0 event family formula / state-change family formula
C0 survivor / stage-2 decision as event token
raw full-universe separability as event-family evidence
12A6c / C0 feature_matrix volatility as native volatility authority
```

13A 放弃 C0-comparable active band 后，不能主张：

```text
Episode 13 比 C0 更值得做。
```

13A 只能主张：

```text
某些 token 在 full_pit_native_opportunity_universe 上独立可分、
bad-side 未同步放大、且 utility / deployability 过关。
```

## 4. 非目标

本需求明确不做：

- 不继续修复 C0 selector、C0 active band 或 `volatility_reconciliation_fail`；
- 不做 C0-vs-full 的公平 denominator 比较；
- 不新增、修改或重跑 C0 state-change family formula；
- 不做 len-2 / len-3 sequence mining；
- 不训练机器学习模型，不做 probability calibration；
- 不做 policy replay、资金曲线、仓位、滑点、容量或交易系统；
- 不重新挑选 winner label，不根据 native universe retune `k_up`、`k_dn` 或 horizon；
- 不用 validation / robustness 回头选择 token、orientation、threshold、floor / cap 或 decision rule；
- 不把单个高 winner-rate 小样本 token 解释成可部署 edge；
- 不把 morphology 高共线 token 自动否决，也不把它自动命名为新 event family。

## 5. 必需输入

### 5.1 Full PIT universe 与行情

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

PIT universe 必须至少提供：

```text
instrument
date
board_bucket or board_code
is_executable or equivalent executable flag
```

若 membership daily 提供 listed / ST / suspension 状态，native universe 必须使用这些字段；若字段不存在，必须在 `native_universe_definition_audit.csv` 记录 `source_field_available = false`，并只使用 executable daily 的 next-open 可执行证明。

qfq daily bar 必须提供：

```text
date
open
high
low
close
volume or amount or turnover_rate, if available
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq `reference_pos`。qfq 日期重复、缺失、OHLC 非有限、high/low 与 open/close 不一致、entry open 缺失时，该 row 必须标记为 not evaluable 并从 primary scope 剔除。

### 5.2 12A7g lineage 输入

必需输入：

```text
SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
SOURCE_EP12_ROOT/configs/config_12a7g_vol_scaled_label_panel_c0_separability_triage.yaml
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_panel_summary.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_separability_decision.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_formula_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_selection_train_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/pre_registered_threshold_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_split_boundary_audit.csv
SOURCE_EP12_ROOT/outputs/manifests/12A7g_vol_scaled_label_panel_c0_separability_triage_manifest.json
```

`vol_scaled_label_separability_decision.csv` 必须满足：

```text
decision_state = 12A7g_baserate_only_not_separable_stop_winner_selection
selected_label_id = vol20d_kup2p0_kdn1p0_H20
input_gate_status = pass
lineage_gate_status = pass
global_regime_calendar_status in {pass, pass_with_missing_date_bypass}
```

`label_formula_audit.csv` 中 selected label 行必须满足：

```text
label_id = vol20d_kup2p0_kdn1p0_H20
label_type = vol_scaled
vol_reference_id = volatility_20d
vol_reference_unit in {daily_return_std, horizon_return_vol, other_audited_unit}
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
formula_status = pass
```

`label_selection_train_audit.csv` 中 selected label 行必须满足：

```text
selected_label_flag = true
label_eligibility_status = eligible
```

若 12A7g decision table 缺失、selected label 不一致、label formula 不可证明、selected label eligibility 不可证明、lineage gate 不通过，13A 必须 fail closed，状态为：

```text
13A_blocked_upstream_label_lineage_failure
```

### 5.3 Split boundary

13A 必须使用可证明的既有 time split boundary。允许来源按优先级：

```text
1. 12A7g publishable full_universe_split_boundary_audit.csv；
2. 12A7g manifest / config 中记录的 split boundary artifact；
3. 12A7g upstream 12A6c split audit artifact；
4. experiment config 中显式声明且可审计的 split boundary。
```

split 字段必须逐行写入：

```text
split_bucket in {train, validation, robustness}
```

不得从 label 结果、token 结果或报告文本反推 split。若 split boundary 不可证明，input gate fail closed。

## 6. Native Opportunity Universe

### 6.1 Row identity

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
reference_pos = qfq position at reference_date
entry_date = next executable PIT/qfq date after reference_date
entry_pos = qfq position at entry_date
entry_price = qfq open at entry_pos
decision_time = reference_date close
execution_time = entry_date open
```

同一 `(instrument, reference_date)` 只能保留一行。重复 row 必须进入 audit 并 fail closed，除非可由完全相同内容去重且 sha256 lineage 可证明。

### 6.2 Regime calendar bypass

Regime 映射规则继承 12A7g：

```text
regime_join_key = reference_date
market_regime_bucket = daily_regime_bucket
```

若某个 `reference_date` 缺 regime row，不得从 event key、calendar month、报告文本或聚合表反推 regime，也不得 fail open。runner 必须逐行标记：

```text
regime_calendar_available = false
regime_missing_date_bypassed = true
market_regime_bucket = missing_regime_calendar
```

这些行必须从 primary scope、threshold freeze、label portability、token cartography、matched control、decision gates 中剔除，只能进入 audit 计数。

若同 date 多 regime、`daily_regime_conflict_flag == true` 或 `daily_regime_conflict_n > 0`，必须 fail closed。

### 6.3 Primary native universe filter

primary scope：

```text
regime_calendar_available == true
board_bucket in supported_boards
listed_flag != false, if available
st_flag != true, if available
suspended_flag != true, if available
next_open_executable == true
required_pre_vol_lookback_complete == true
native_liquidity_floor_pass == true
native_trading_continuity_floor_pass == true
native_volatility_sanity_pass == true
```

`supported_boards` 必须从 12A7g config 继承，并写入 `native_universe_definition_audit.csv`。不得在 13A 中新增 board bucket 来扩大 denominator。若 12A7g config 不可读取，input gate fail closed。

当前 12A7g lineage 的默认 supported boards：

```text
supported_boards = {main_board, chinext, star}
```

Synthetic tests 可以使用更小的 board set，但 full run 不得把 `sme_board`、unknown board 或缺失 board row 静默纳入 primary scope。

### 6.4 Train-only floor / cap freeze

以下 floor / cap 只能用 train split 计算一次，随后冻结到 validation / robustness：

```text
basic_liquidity_floor
trading_continuity_floor
volatility_sanity_floor
volatility_sanity_cap
```

默认候选规则：

```text
basic_liquidity_floor:
  primary metric = money_median_20d, if amount is available
  fallback metric = turnover_rate_median_20d, if turnover_rate is available
  threshold candidates = train p01, p02, p05, p10
  default selection = p05 unless denominator stability fails

trading_continuity_floor:
  metric = tradable_bar_count_20d / 20
  threshold candidates = 0.80, 0.90, 0.95, 1.00
  default selection = 0.95

volatility_sanity_floor / cap:
  metric = volatility_20d
  floor candidates = train p01, p02, p05
  cap candidates = train p95, p98, p99
  default selection = [p01, p99]
```

Tie-breaking：

```text
1. choose the candidate pair with largest retained train denominator
   subject to denominator stability tolerance;
2. if tied, choose the pair with lowest universe_balance_score,
   where universe_balance_score is computed only from denominator mix
   drift by year / board / regime and never from label outcome;
3. if tied, choose the least restrictive floor / cap;
4. if still tied, choose lexicographically by metric_id / threshold_id.
```

Universe floor / cap freeze 不得使用 winner label、fast-fail label、future return 或任何 outcome-derived statistic。`label_base_rate_dispersion` 只能在 §7 label portability 中作为 freeze 后的复核结果，不能反向参与 §6.4 的 universe threshold 选择。

冻结后的阈值必须写入：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
```

### 6.5 Native volatility self-consistency

13A 不要求 native volatility 与 12A6c / C0 feature_matrix reconciliation。它只要求 native full-PIT volatility 自身可复现、PIT-safe。

冻结公式：

```text
daily_return[t] = close[t] / close[t - 1] - 1
volatility_Nd = std(daily_return over reference_pos - N + 1 ... reference_pos, ddof=0)
required_pre_vol_lookback_complete = all N daily_return observations finite
```

若 native volatility 自身不可复现、lookback 不完整、qfq row 不唯一或 OHLCV 非有限，input gate fail closed 或 row-level not evaluable，具体由错误是否全局性决定。

### 6.6 Universe stability audit

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_definition_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_threshold_sensitivity_audit.csv
```

审计维度：

```text
split_bucket
calendar_year
board_bucket
market_regime_bucket
instrument_count
row_count
instrument_month_count
winner_base_rate
missing_regime_bypassed_row_n
not_evaluable_row_n
```

阈值邻域敏感性必须报告：

```text
threshold_variant_id
retained_row_n
retained_row_share_delta
winner_base_rate_delta
board_mix_max_abs_delta
year_mix_max_abs_delta
status in {pass, warn, fail}
```

默认容差：

```text
max_retained_row_share_delta = 0.10
max_winner_base_rate_delta = 0.02
max_board_mix_abs_delta = 0.08
max_year_mix_abs_delta = 0.08
```

## 7. Label Portability

### 7.1 Frozen selected label

13A 必须只使用 12A7g 选出的 label：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_id = volatility_20d
vol_reference_unit = read from 12A7g label_formula_audit.csv
horizon_sessions = 20
k_up = 2.0
k_dn = 1.0
entry_anchor = next executable open
```

Label 计算：

```text
if vol_reference_unit == daily_return_std:
  vol_horizon_scale = volatility_20d_at_reference * sqrt(horizon_sessions)
elif vol_reference_unit == horizon_return_vol:
  vol_horizon_scale = volatility_20d_at_reference
else:
  vol_horizon_scale = audited_transform_recorded_in_12A7g_label_formula_audit

upper_barrier_return = k_up * vol_horizon_scale
lower_barrier_return = -1 * k_dn * vol_horizon_scale
upper_barrier_price = entry_price * (1 + upper_barrier_return)
lower_barrier_price = entry_price * (1 + lower_barrier_return)

horizon_complete =
  entry_pos is finite
  and entry_pos + horizon_sessions < instrument_qfq_row_n

horizon_window = qfq rows from entry_pos through entry_pos + horizon_sessions, inclusive
upper_touch at offset s = high[entry_pos + s] / entry_price - 1 >= upper_barrier_return
lower_touch at offset s = low[entry_pos + s] / entry_price - 1 <= lower_barrier_return
winner = first upper_touch before first lower_touch
fast_fail = first lower_touch before first upper_touch
same_bar_conflict = upper_touch and lower_touch at the same first offset
```

这必须复刻 12A7g `label_formula_audit.csv` 的 `path_window = reference_pos_through_reference_pos_plus_horizon_inclusive` 与 `same_bar_priority = lower_first`。若 13A 重算 label 与可选 12A7g local cache 在相同 row key 上不一致，必须输出 mismatch audit；若 mismatch 超过预注册容差，input gate fail closed。

同一 bar 同时触及上下 barrier 时，必须使用 lower-first conservative rule：

```text
same_bar_conflict -> winner = false, fast_fail = true, lower_first_conflict = true
```

若 horizon 不完整，该 row 不得进入 primary label panel。

### 7.2 Native denominator label portability

必须在 native universe 上复核 selected label 的可移植性：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_label_portability_audit.csv
```

字段必须至少包括：

```text
split_bucket
denominator_n
horizon_complete_n
horizon_complete_rate
winner_positive_n
winner_base_rate
fast_fail_rate
same_bar_conflict_rate
label_base_rate_dispersion
label_stability_status
source_12a7g_formula_status
source_12a7g_vol_reference_unit
source_12a7g_train_base_rate
source_12a7g_label_stability_score
source_12a7g_max_label_base_rate_dispersion
source_12a7g_max_same_bar_conflict_rate
```

默认可移植性 gate：

```text
horizon_complete_rate >= 0.98
train winner_positive_n >= source_12a7g_min_train_positive_n
label_base_rate_dispersion <= source_12a7g_max_label_base_rate_dispersion
same_bar_conflict_rate <= source_12a7g_max_same_bar_conflict_rate
```

默认从 12A7g config / `pre_registered_threshold_audit.csv` 继承：

```text
source_12a7g_min_train_positive_n = 200
source_12a7g_max_label_base_rate_dispersion = 0.10
source_12a7g_max_same_bar_conflict_rate = 0.03
```

若 label 在 native universe 上漂移超阈，不允许 retune label；decision_state 必须为：

```text
13A_label_not_portable_stop_or_revisit_label
```

## 8. Token Dictionary

### 8.1 Token availability

所有 token primitive 必须在 `decision_time = reference_date close` 可用，不得使用 entry date 之后的信息。

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_availability_audit.csv
```

每个 token 必须记录：

```text
token_id
family_id
primitive_id
lookback_sessions
orientation
threshold_rule
threshold_value
threshold_split = train
available_at = reference_date_close
future_data_used = false
```

### 8.2 Primitive family

13A 必须覆盖以下 len-1 primitive family：

```text
reversal_drawdown:
  max_drawdown_20d
  distance_to_20d_low
  rebound_from_20d_low

breakout_trend:
  distance_to_20d_high
  ret_5d
  ret_20d
  trend_ma_5_20_spread
  trend_ma_20_60_spread

volatility_range:
  volatility_20d
  volatility_60d
  vol_ratio_20d_60d
  vol_compression_20d_60d
  vol_expansion_20d_60d
  recent_range_activity_20d
  intraday_range_mean_20d

liquidity_attention:
  turnover_rate_median_20d
  turnover_zscore_20d
  money_median_20d

relative_strength:
  stock_vs_board_20d
  board_return_20d
```

若某 primitive 因输入字段缺失不可计算，不能 fail open；必须在 availability audit 中记录：

```text
primitive_status = unavailable_missing_source_field
token_status = excluded_before_grid
```

若整个 family 不可用，必须保留 family-level audit row。

### 8.3 Primitive formula freeze

```text
price_reference = qfq close at reference_pos
ret_Nd = close[reference_pos] / close[reference_pos - N] - 1
daily_return = close[t] / close[t - 1] - 1
volatility_Nd = std(daily_return over reference_pos - N + 1 ... reference_pos, ddof=0)
distance_to_Nd_high = close[reference_pos] / max(high over last N sessions including reference_pos) - 1
distance_to_Nd_low = close[reference_pos] / min(low over last N sessions including reference_pos) - 1
rebound_from_Nd_low = close[reference_pos] / min(low over last N sessions including reference_pos) - 1
trend_ma_5_20_spread = mean(close last 5 sessions) / mean(close last 20 sessions) - 1
trend_ma_20_60_spread = mean(close last 20 sessions) / mean(close last 60 sessions) - 1
max_drawdown_Nd = min(close[t] / max(close up to t within last N sessions) - 1)
vol_ratio_20d_60d = volatility_20d / volatility_60d - 1
vol_compression_20d_60d = -1 * vol_ratio_20d_60d
vol_expansion_20d_60d = vol_ratio_20d_60d
recent_range_activity_20d = mean((high - low) / close over last 20 sessions)
intraday_range_mean_20d = mean((high - low) / open over last 20 sessions)
turnover_zscore_20d = (current turnover_rate - mean(turnover_rate last 20 sessions)) / std(turnover_rate last 20 sessions, ddof=0)
stock_vs_board_20d = ret_20d - board_return_20d
```

若 `board_return_20d` 无现成 PIT board return 输入，runner 可以用 same board native executable rows 的 equal-weight close-to-close return 构造，但必须只使用 reference_date 及以前数据，并在 audit 中记录构造方法。

### 8.4 Len-1 token grid

每个 numeric primitive 默认生成以下 train-frozen candidate token：

```text
bottom_10pct
bottom_20pct
top_20pct
top_10pct
```

阈值只在 train split 计算。validation / robustness 只能 apply frozen threshold。

Token grid 上限：

```text
max_token_candidate_n = 120
```

若候选数超过上限，必须先按 family priority 与 primitive priority 截断，截断规则写入 config 和 token dictionary。不得用 label outcome 截断 token grid。

## 9. Matched Control 与 Metrics

### 9.1 Matched control design

每个 token 的 control 必须从同一 native opportunity universe 中抽取，且不能满足该 token。基础匹配字段：

```text
split_bucket
calendar_month or reference_month
board_bucket
market_regime_bucket
volatility_20d_decile
liquidity_metric_decile
```

匹配必须 token-aware。若当前 token 的 primitive / family 本身来自匹配字段，必须从该 token 的 match key 中移除对应 decile，防止把 signal 匹配掉或造成 control 不可得：

```text
if token family == volatility_range:
  exclude volatility_20d_decile from match key

if token family == liquidity_attention:
  exclude liquidity_metric_decile from match key

if token primitive_id in {volatility_20d, volatility_60d, vol_ratio_20d_60d,
                         vol_compression_20d_60d, vol_expansion_20d_60d}:
  exclude all volatility-derived match keys

if token primitive_id in {turnover_rate_median_20d, turnover_zscore_20d, money_median_20d}:
  exclude all liquidity-derived match keys
```

若严格匹配导致 control 不足，runner 允许按预注册顺序 coarsen match key：

```text
level_0 = month + board + regime + allowed deciles
level_1 = quarter + board + regime + allowed deciles
level_2 = quarter + board + regime
level_3 = year + board + regime
```

coarsening 只能为补足 control 使用，不得根据 outcome 选择。

不得使用 future label、future return、winner outcome 或 bad-side outcome 做匹配。

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/matched_control_design_audit.csv
```

字段至少包括：

```text
token_id
split_bucket
treated_n
control_n
matched_block_n
unmatched_treated_n
effective_control_ratio
max_standardized_diff_after_match
excluded_match_keys
coarsening_level
control_match_quality
match_status
```

默认 gate：

```text
effective_control_ratio >= 3
unmatched_treated_share <= 0.05
max_standardized_diff_after_match <= 0.10
```

`control_match_quality` 规则：

```text
coarsening_level in {level_0, level_1} and max_standardized_diff_after_match <= 0.10:
  control_match_quality = primary_comparable

coarsening_level in {level_2, level_3} or max_standardized_diff_after_match > 0.10:
  control_match_quality = coarsened_caveat

coarsening_level in {level_2, level_3}
and max_standardized_diff_after_match <= 0.05
and effective_control_ratio >= 5
and unmatched_treated_share <= 0.02
and validation winner_rate_diff_vs_control_ci_low > 0
and robustness winner_rate_diff_vs_control_ci_low > 0
and validation captured_positive_n >= 100
and robustness captured_positive_n >= 100
and validation coverage_share >= 0.01
and robustness coverage_share >= 0.01
and utility_gate_status = utility_pass_per_entry
and stability_gate_status = pass:
  control_match_quality = coarsened_caveat_pass_strict

effective_control_ratio < 3 or unmatched_treated_share > 0.05:
  control_match_quality = insufficient_control
```

`control_match_quality = coarsened_caveat` 的 token 可以进入 diagnostic readout，但不能仅凭 matched-control winner diff 授权 13B；它必须在 deployability 与 stability 中通过 stricter caveat gate 后升级为 `coarsened_caveat_pass_strict`。`control_match_quality = insufficient_control` 的 token 不得通过 winner uplift gate。

### 9.2 Winner uplift metrics

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_readout.csv
```

字段至少包括：

```text
token_id
family_id
primitive_id
split_bucket
treated_n
treated_positive_n
treated_winner_rate
control_n
control_positive_n
control_winner_rate
native_baseline_winner_rate
winner_rate_diff_vs_control
winner_rate_diff_vs_control_ci_low
winner_rate_diff_vs_control_ci_high
winner_rate_ratio_vs_control
odds_ratio_vs_control
auc_one_vs_rest
broad_morphology_baseline_auc
auc_margin_vs_broad_morphology_baseline
rank_ic
top_decile_lift
control_match_quality
metric_status
```

默认 winner uplift gate：

```text
train treated_n >= 500
train treated_positive_n >= 50
validation treated_n >= 200
robustness treated_n >= 200
validation winner_rate_diff_vs_control > 0
robustness winner_rate_diff_vs_control > 0
validation auc_one_vs_rest >= 0.55
robustness auc_one_vs_rest >= 0.55
validation top_decile_lift >= 0.02
control_match_quality != insufficient_control
```

若 train 选出候选 token，但 validation / robustness 的方向不一致、AUC 不达标、top-decile lift 不达标或 control 不足，该 token 视为没有通过 winner uplift gate。它可以留在 readout 中，但不得进入 bad-side / deployability 授权链。

### 9.3 Bad-side veto

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_badside_veto_audit.csv
```

字段至少包括：

```text
token_id
split_bucket
upper_first_rate
treated_fast_fail_rate
control_fast_fail_rate
fast_fail_uplift
treated_same_bar_conflict_rate
treated_lower_first_rate
control_lower_first_rate
lower_first_uplift
median_upper_barrier_return
median_abs_lower_barrier_return
utility_proxy_per_entry
utility_proxy_unit
utility_proxy_total_indexed
utility_proxy_total_indexed_ci_low
native_baseline_utility_total_indexed
native_baseline_utility_total_indexed_ci_high
cost_buffer_return
utility_gate_status
badside_status
```

默认 utility proxy：

```text
utility_proxy_unit = return
cost_buffer_return = source_cost_buffer_bps / 10000

utility_proxy_per_entry =
  upper_first_rate * median_upper_barrier_return
  - treated_lower_first_rate * median_abs_lower_barrier_return
  - cost_buffer_return

utility_proxy_total_indexed =
  utility_proxy_per_entry * treated_n / native_split_denominator_n

source_cost_buffer_bps = inherited from 12A7g config, default 100
```

`treated_lower_first_rate` 已包含 same-bar lower-first conflict，不得再额外重复扣一次 same-bar。same-bar conflict 必须单独报告，用于判断 label 机械冲突是否恶化。

默认 bad-side / utility gate：

```text
validation fast_fail_uplift <= 0.02
robustness fast_fail_uplift <= 0.02
validation lower_first_uplift <= 0.01
robustness lower_first_uplift <= 0.01

utility pass if and only if:
  validation utility_proxy_per_entry > 0
  and robustness utility_proxy_per_entry > 0
  and utility_gate_status = utility_pass_per_entry

or:
  validation utility_proxy_per_entry >= 0
  and robustness utility_proxy_per_entry >= 0
  and validation utility_proxy_total_indexed_ci_low
      > validation native_baseline_utility_total_indexed_ci_high
  and robustness utility_proxy_total_indexed_ci_low
      > robustness native_baseline_utility_total_indexed_ci_high
  and utility_gate_status = utility_pass_total_indexed
```

`utility_proxy_per_entry < 0` 不得由 total indexed utility 补救。`utility_pass_total_indexed` 只能用于 per-entry 非负但接近零、且 total indexed utility 在预注册置信区间下显著优于 native baseline 的 token；这类 token 必须在 deployability gate 中显式暴露 precision / recall / coverage tradeoff。

### 9.4 Morphology collinearity check

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_morphology_collinearity_audit.csv
```

字段至少包括：

```text
token_id
split_bucket
morphology_anchor_id
rank_corr_with_anchor
max_abs_rank_corr_with_reversal_anchor
morphology_flag
broad_morphology_baseline_auc
auc_margin_vs_broad_morphology_baseline
broad_morphology_baseline_utility_total_indexed
utility_total_margin_vs_broad_morphology_baseline
utility_total_margin_vs_broad_morphology_baseline_ci_low
morphology_suspect_independent_evidence_status
morphology_collinearity_status
```

每个胜出 token 必须与以下 anchors 计算 train / validation / robustness rank correlation：

```text
max_drawdown_20d
distance_to_20d_low
rebound_from_20d_low
ret_20d
volatility_20d
```

同一 anchor set 还必须在 native universe 上按 13A 的同一 matched-control / bad-side / deployability pipeline 计算 broad morphology baseline：

```text
broad_morphology_baseline_auc =
  max auc_one_vs_rest among the pre-registered anchor tokens

broad_morphology_baseline_utility_total_indexed =
  max utility_proxy_total_indexed among the pre-registered anchor tokens
  subject to bad-side status not worse than native baseline

auc_margin_vs_broad_morphology_baseline =
  token_auc - broad_morphology_baseline_auc

utility_total_margin_vs_broad_morphology_baseline =
  token_utility_proxy_total_indexed - broad_morphology_baseline_utility_total_indexed
```

这一步不是把 reversal / drawdown token 否决掉，而是防止一个与 broad morphology 高度共线、且没有更强独立证据的 token 换名授权 13B。

默认标记规则：

```text
if max_abs_rank_corr_with_reversal_anchor >= 0.70:
  morphology_flag = morphology_rediscovery_suspect
else:
  morphology_flag = morphology_distinct_or_low_collinearity
```

高共线本身不构成 veto。只有当高共线 token 同时出现以下情况，才降级为：

```text
C0_like_two_tailed_rediscovery_diagnostic_only
```

降级条件：

```text
fast_fail_uplift > threshold
or lower_first_uplift > threshold
or utility_proxy_per_entry <= 0 and utility_proxy_total_indexed not significantly better than native baseline
```

若高共线 token 仍通过 bad-side veto 与 deployability gate，可以标记为：

```text
native_morphology_event_supported_no_c0_claim
```

但它还必须通过 `morphology_suspect_independent_evidence_gate`：

```text
pass if:
  validation auc_margin_vs_broad_morphology_baseline >= 0.02
  and robustness auc_margin_vs_broad_morphology_baseline >= 0.02

or:
  validation utility_total_margin_vs_broad_morphology_baseline_ci_low > 0
  and robustness utility_total_margin_vs_broad_morphology_baseline_ci_low > 0
  and validation fast_fail_uplift <= 0
  and robustness fast_fail_uplift <= 0
  and validation lower_first_uplift <= 0
  and robustness lower_first_uplift <= 0
  and control_match_quality = primary_comparable
```

若 `morphology_rediscovery_suspect` 未通过该独立证据 gate，即使 ordinary winner uplift / bad-side / deployability 达标，也只能标记为 diagnostic，不得设置 `sequence_mining_authorized = true`。

但报告中不得声称它证明 C0 体系正确。

## 10. Stability, Search Control, Deployability

### 10.1 Stability gate

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_stability_slice_audit.csv
```

切片：

```text
calendar_year
board_bucket
market_regime_bucket
instrument_month_block
```

默认 gate：

```text
at least 3 calendar_year slices with positive winner_rate_diff_vs_control
no single board contributes > 60% treated_n for supported token
instrument_month_block_bootstrap_ci_low > -0.01
```

若 token 只在单一切片有效，最多标记为 diagnostic，不得进入 sequence authorization。

### 10.2 Search-control gate

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_search_multiplicity_audit.csv
```

字段至少包括：

```text
token_grid_size
family_grid_size
token_threshold_candidate_n
orientation_candidate_n
universe_floor_cap_candidate_n
match_coarsening_policy_n
effective_search_space_n
selected_token_rank_train
raw_p_value
fdr_q_value
deflated_auc
selection_split = train
readout_only_splits = validation,robustness
```

默认 gate：

```text
effective_search_space_n >= token_grid_size
fdr_q_value <= 0.10
deflated_auc_validation >= 0.53
```

`effective_search_space_n` 必须覆盖所有会影响 token selection 或 selected-token readout 的预注册自由度：

```text
effective_search_space_n =
  token_grid_size
  * max(1, orientation_candidate_n)
  * max(1, token_threshold_candidate_n)
  * max(1, universe_floor_cap_candidate_n)
  * max(1, match_coarsening_policy_n)
```

若某个自由度被证明完全 outcome-free 且 deterministic，例如 §6.4 的 universe floor / cap 使用 label-free denominator tie-break，runner 可以在 audit 中同时输出：

```text
effective_search_space_n_conservative
effective_search_space_n_outcome_free_adjusted
```

但 primary FDR / deflated metric 必须使用 conservative `effective_search_space_n`。Validation / robustness 只能 readout，不得参与 token 选择、orientation 选择、threshold 选择、floor / cap 选择或 coarsening policy 选择。

### 10.3 Deployability gate

13A 的 deployability gate 不使用单一 recall floor 否决 token，因为 native event discovery 允许低 coverage、高质量的 niche event。但它必须报告捕获正例数、coverage 和 utility total。

必须输出：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_deployability_gate_audit.csv
```

字段至少包括：

```text
token_id
split_bucket
decision_point = reference_date_close
execution_point = next_open
coverage_share
captured_positive_n
captured_positive_share
winner_rate
lift_vs_native_baseline
utility_proxy_per_entry
utility_proxy_total_indexed
utility_proxy_total_indexed_ci_low
native_baseline_utility_total_indexed
native_baseline_utility_total_indexed_ci_high
cost_buffer_return
precision_recall_frontier_status
deployability_status
```

默认 gate：

```text
validation captured_positive_n >= 50
robustness captured_positive_n >= 50
validation coverage_share >= 0.005
robustness coverage_share >= 0.005
utility pass according to §9.3 bad-side / utility gate
```

deployability gate 不过时，token 只能作为 diagnostic，不能授权 13B sequence mining。

## 11. 输出

### 11.1 Publishable tables

必须输出到：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/
```

必需文件：

```text
input_artifact_audit.csv
upstream_12a7g_lineage_audit.csv
native_universe_frozen_thresholds.csv
native_universe_definition_audit.csv
native_universe_threshold_sensitivity_audit.csv
native_label_portability_audit.csv
native_token_dictionary.csv
native_token_availability_audit.csv
matched_control_design_audit.csv
native_token_cartography_readout.csv
native_token_badside_veto_audit.csv
native_token_morphology_collinearity_audit.csv
native_token_stability_slice_audit.csv
native_token_search_multiplicity_audit.csv
native_token_deployability_gate_audit.csv
native_token_cartography_decision.csv
```

### 11.2 Local cache

允许输出到：

```text
outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_label_panel.parquet
outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_token_matrix.parquet
```

local cache 不进入 publishable claim。所有 publishable claim 必须能由 publishable tables、manifest 和可重建输入证明。

### 11.3 Report and manifest

必须输出：

```text
outputs/publishable/reports/native_token_cartography_preflight_report.md
outputs/manifests/13A_full_pit_native_token_cartography_preflight_manifest.json
```

报告必须使用中文，至少包含：

```text
1. 13A 的问题边界：不是 C0 修复，不是 sequence mining；
2. native opportunity universe 的 denominator 审计；
3. selected label 在 native universe 上的 portability；
4. len-1 token family 总览；
5. 胜出 token 的 winner uplift、bad-side、utility、stability；
6. morphology_collinearity_check 的结论；
7. deployability gate 与 precision / recall / coverage tradeoff；
8. 是否授权 13B sequence mining。
```

## 12. Decision State

`native_token_cartography_decision.csv` 必须只有一行，字段至少包括：

```text
decision_state
next_allowed_requirement
input_gate_status
upstream_lineage_gate_status
native_universe_gate_status
label_portability_gate_status
winner_uplift_gate_status
badside_gate_status
stability_gate_status
search_control_gate_status
deployability_gate_status
selected_token_id
selected_token_family_id
selected_token_morphology_flag
selected_token_control_match_quality
selected_token_morphology_suspect_independent_evidence_status
sequence_mining_authorized
decision_reason
```

决策优先级：

```text
1. input / PIT / split / upstream lineage 失败:
   decision_state = 13A_blocked_input_or_lineage_failure
   next_allowed_requirement = fix_input_lineage_then_rerun_13A

2. selected label 在 native universe 上不可移植:
   decision_state = 13A_label_not_portable_stop_or_revisit_label
   next_allowed_requirement = revisit_label_portability_requirement

3. 无 len-1 token 通过 winner uplift / search-control:
   decision_state = 13A_no_native_token_survives_stop_event_mining
   next_allowed_requirement = none

   This includes cases where train selected at least one candidate token,
   but validation / robustness direction is inconsistent, AUC / lift falls
   below threshold, FDR / deflated metric fails, or control_match_quality
   is insufficient_control.

4. 有 token 可分但 bad-side / utility / deployability 不过:
   decision_state = 13A_native_token_diagnostic_only_badside_or_utility_fail
   next_allowed_requirement = none_or_diagnostic_report_only

   This also includes tokens whose ordinary readout passes but whose
   control_match_quality = coarsened_caveat and stricter caveat gate does
   not pass.

5. 高 morphology 共线 token 通过全部 gate:
   decision_state = 13A_native_morphology_event_supported_no_c0_claim
   next_allowed_requirement = requirement_13b_train_frozen_event_sequence_mining.md

   Requires:
     selected_token_morphology_flag = morphology_rediscovery_suspect
     selected_token_morphology_suspect_independent_evidence_status = pass

6. morphology 低共线或多 family token 通过全部 gate:
   decision_state = 13A_native_len1_token_supported_authorize_sequence_mining
   next_allowed_requirement = requirement_13b_train_frozen_event_sequence_mining.md
```

任何授权 13B 的决策都必须满足：

```text
sequence_mining_authorized = true
deployability_gate_status = pass
search_control_gate_status = pass
badside_gate_status = pass
selected_token_control_match_quality in {primary_comparable, coarsened_caveat_pass_strict}
```

## 13. Validation Commands

实现完成后，至少需要支持以下命令：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER

python -m py_compile experiments/pending/13_full_pit_native_event_discovery_v0/src/run_13a_full_pit_native_token_cartography_preflight.py
python -m pytest experiments/pending/13_full_pit_native_event_discovery_v0/tests/test_13a_full_pit_native_token_cartography_preflight.py

python experiments/pending/13_full_pit_native_event_discovery_v0/src/run_13a_full_pit_native_token_cartography_preflight.py \
  --config experiments/pending/13_full_pit_native_event_discovery_v0/configs/config_13a_full_pit_native_token_cartography_preflight.yaml \
  --check-inputs-only

python experiments/pending/13_full_pit_native_event_discovery_v0/src/run_13a_full_pit_native_token_cartography_preflight.py \
  --config experiments/pending/13_full_pit_native_event_discovery_v0/configs/config_13a_full_pit_native_token_cartography_preflight.yaml
```

Runner 必须支持 deterministic rerun。同一输入、同一 config、同一 code version 下，publishable table hash 必须一致。

## 14. 最低测试要求

测试至少覆盖：

```text
path resolution and input audit
duplicate qfq date detection
missing qfq reference_date row exclusion
next-open entry executability
regime missing date bypass
regime conflict fail closed
train-only threshold freeze
universe floor / cap tie-break does not use label outcome
validation / robustness threshold replay
native volatility self-consistency
selected label formula reads vol_reference_unit and horizon scale from 12A7g lineage
selected label lower-first conflict handling
horizon incompleteness exclusion
token availability no future data
token grid size and FDR accounting
effective_search_space includes threshold / orientation / floor / coarsening freedom
matched control does not use outcome
token-aware matched control excludes current token family match keys
control coarsening caveat cannot authorize sequence without strict pass
utility proxy uses return units and cost_buffer_return
utility gate distinguishes utility_pass_per_entry and utility_pass_total_indexed
morphology collinearity flag but not veto
morphology_rediscovery_suspect requires independent evidence before 13B authorization
bad-side veto downgrade
deployability gate captured_positive_n / coverage handling
decision_state precedence
manifest hash stability
```

测试不能依赖本地大文件才能通过；必须包含 small synthetic fixtures。Full run 可以依赖真实数据。

## 15. Implementation Notes

实现时建议分层：

```text
1. load_and_audit_inputs()
2. rebuild_full_pit_base_panel()
3. freeze_native_universe_thresholds_on_train()
4. apply_native_universe_filters()
5. compute_selected_vol_scaled_label()
6. build_token_primitives_and_grid()
7. evaluate_tokens_with_matched_controls()
8. run_badside_morphology_stability_search_deployability_gates()
9. write_publishable_outputs_and_manifest()
```

任何 row-level exclusion 都必须保留原因码：

```text
missing_regime_calendar
regime_conflict
unsupported_board
not_listed_or_st_or_suspended
missing_qfq_reference_row
duplicate_qfq_reference_row
missing_entry_open
pre_vol_lookback_incomplete
label_horizon_incomplete
token_primitive_unavailable
native_floor_fail
native_cap_fail
```

13A 的关键工程判断是：universe definition、label portability、token selection、deployability 是四个独立 gate。任何一个 gate 不过，都不能用另一个 gate 的漂亮读数覆盖。
