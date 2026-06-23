# 需求：13A2 Compression Directional Disambiguation Preflight

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
6. 不得从报告文本、图像或人工讨论文本反推出逐行 universe、标签、token、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 13_full_pit_native_event_discovery_v0
phase_id = 13A2
run_id = 13A2_compression_directional_disambiguation_preflight
status = spec_draft_pending_review
expected_entrypoint = src/run_13a2_compression_directional_disambiguation_preflight.py
expected_config = configs/config_13a2_compression_directional_disambiguation_preflight.yaml
expected_test_file = tests/test_13a2_compression_directional_disambiguation_preflight.py
upstream_requirement_13a = EXPERIMENT_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_report_13a = EXPERIMENT_ROOT/outputs/publishable/reports/native_token_cartography_preflight_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13A2 是 13A 的后续预检，不是 13B sequence mining。13A 已证明 full-PIT native universe 上最强 len-1 读数来自：

```text
base_compression_state = volatility_20d__bottom_20pct
```

但 13A 同时证明该 compression state 自身同步放大 lower-first / fast-fail，utility 与 deployability 不过关。13A2 的唯一目标是：

```text
在固定 compression cohort 内，寻找 PIT-safe directional_filter，
判断能否把 upper-first winner 与 lower-first / fast-fail 分开。
```

只有 13A2 通过全部 gate，才允许新建：

```text
requirement_13b_train_frozen_compression_direction_sequence_mining.md
```

## 2. 核心问题

13A2 回答以下问题：

```text
Q1. 13A selected compression state 是否可逐行复现，并能作为固定 base cohort？

Q2. 在 base compression cohort 内，是否存在 train-frozen directional_filter，
    能在 validation / robustness 中相对 compression-only control 保持 winner uplift？

Q3. 该 directional_filter 是否降低或至少不放大 lower-first / fast-fail，
    并使 utility_proxy_per_entry 与 utility_proxy_total_indexed 转正？

Q4. 该 directional_filter 是否只是 broad reversal / low-volatility morphology 的
    再次切片？若是，是否有相对 compression-only baseline 的独立 utility evidence？

Q5. 该 directional_filter 是否具备可部署性，值得进入 13B？
```

Scope boundary：

```text
13A2 只检验 volatility_20d__bottom_20pct 这个 fixed compression base
内部是否存在方向分辨。若 13A2 失败，它只否决
compression-conditional directional disambiguation route；
不证明 full-PIT native universe 中不存在其他可方向分辨的 base state。
是否对 13A 的次强 base state 另开同类 requirement，是独立研究决策，
不得从 13A2 的 next_allowed_requirement = none 自动推断 Episode 13 全局终结。
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. 继承边界

### 3.1 允许继承

13A2 可以继承：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
entry_date = next executable open after reference_date
entry_price = qfq open at entry_date
selected_label_id = vol20d_kup2p0_kdn1p0_H20
native opportunity universe definition from 13A
13A train-frozen native universe floor / cap
13A train-frozen selected compression token threshold
split boundary from 12A7g / 13A
```

13A2 必须读取 13A publishable artifacts 作为 lineage：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_decision.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_readout.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_badside_veto_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/matched_control_design_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_deployability_gate_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_morphology_collinearity_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_label_portability_audit.csv
outputs/manifests/13A_full_pit_native_token_cartography_preflight_manifest.json
```

13A2 可以复用 13A runner 的 deterministic rebuild logic，但不得把 13A 聚合表当成逐行 truth。逐行 base cohort、directional features、label、entry price 必须从 raw PIT universe / qfq bars 或可审计 cache 重新构造。

### 3.2 禁止继承 / 禁止主张

13A2 明确不得：

- 不使用 C0 active band、C0 thresholds、C0 state-change family formula；
- 不修复 C0 selector 或 `volatility_reconciliation_fail`；
- 不重新选择 winner label；
- 不重新搜索 base compression state；
- 不把 `volatility_20d__bottom_20pct` 本身作为 event family 授权 13B；
- 不用 validation / robustness 选择 directional_filter、threshold、orientation、conjunction 或 decision rule；
- 不做 len-2 / len-3 sequence mining；
- 不训练 ML 模型，不做 probability calibration；
- 不做资金曲线、仓位、滑点、容量或交易系统。

13A2 不能主张：

```text
compression state 本身可部署。
```

13A2 只能主张：

```text
在 compression state 内，某个 train-frozen directional_filter
相对 compression-only control 提供了方向分辨、bad-side 控制与 utility 改善。
```

## 4. 必需输入

### 4.1 Full PIT universe 与行情

同 13A：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq daily `reference_pos` 与 next-open executable `entry_pos`。不可证明时 row-level not evaluable；全局 schema / PIT 失败时 fail closed。

### 4.2 Upstream 13A lineage

13A2 要求 13A decision table 满足：

```text
input_gate_status = pass
upstream_lineage_gate_status = pass
native_universe_gate_status = pass
label_portability_gate_status = pass
selected_token_id = volatility_20d__bottom_20pct
selected_token_family_id = volatility_range
sequence_mining_authorized = False
```

13A2 不要求 13A 授权 13B；相反，13A2 的前提正是 13A 因 bad-side / utility / control / morphology caveat 停止。

13A dictionary 中 selected token 行必须满足：

```text
token_id = volatility_20d__bottom_20pct
primitive_id = volatility_20d
threshold_rule = bottom_20pct
threshold_split = train
available_at = reference_date_close
future_data_used = false
comparator = le
```

若 selected token 不存在、阈值不可读取、阈值不是 train-frozen、或 selected token 与 13A decision 不一致，状态为：

```text
13A2_blocked_upstream_13a_lineage_failure
```

### 4.3 12A7g label lineage

13A2 必须沿用 13A/12A7g 的 selected label：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_id = volatility_20d
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
```

若 label formula、vol reference unit、split boundary 或 label eligibility 不可证明，状态为：

```text
13A2_blocked_label_lineage_failure
```

## 5. Base Compression Cohort

13A2 必须先重建 13A native opportunity universe，再冻结 base compression cohort：

```text
base_compression_state(row) =
  native_universe(row)
  and volatility_20d(row) <= threshold_value_from_13A_dictionary
```

默认阈值来源：

```text
13A native_token_dictionary.csv
token_id = volatility_20d__bottom_20pct
threshold_value = 0.016023...  # exact value must be read from table, not hard-coded
```

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/base_compression_cohort_audit.csv
```

字段：

```text
split_bucket
native_denominator_n
base_compression_n
base_coverage_share
base_positive_n
base_winner_rate
base_lower_first_rate
base_fast_fail_rate
base_utility_proxy_per_entry
base_utility_proxy_total_indexed
base_board_mix_main_board_share
base_board_mix_chinext_share
threshold_value
threshold_source_token_id
threshold_reproduction_status
cost_buffer_return
cost_buffer_source
```

Base cohort 必须满足：

```text
train base_compression_n >= 5000
validation base_compression_n >= 1000
robustness base_compression_n >= 1000
threshold_reproduction_status = pass
```

否则状态为：

```text
13A2_base_compression_not_reproducible_stop
```

## 6. Directional Filter Families

13A2 的 filter 只能使用 `reference_date_close` 及以前可得的 PIT-safe 特征。所有 threshold 必须在 train split 的 base compression cohort 内冻结，不能用 validation / robustness。

### 6.0 Canonical bullish score

所有 directional primitive 必须先转成统一方向的：

```text
bullish_score
```

之后所有 threshold 都只使用同一组 train-only quantile rules：

```text
top_50pct
top_40pct
top_30pct
top_20pct
```

Filter 公式统一为：

```text
directional_filter(row) = bullish_score(row) >= train_base_compression_quantile(threshold_rule)
```

不得在不同 family 中混用 `top` / `bottom` / 手写常数阈值。若某 primitive 的自然方向是 lower-is-bullish，必须先通过 `bullish_score = -raw_value` 转向后再应用 top quantile。

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_threshold_freeze_audit.csv
```

字段：

```text
primitive_id
filter_family_id
raw_feature_formula
bullish_score_formula
threshold_rule
threshold_value
threshold_source_split
threshold_source_scope
available_at
future_data_used
feature_availability_status
threshold_freeze_status
```

### 6.1 Relative Strength Filters

目标：压缩但相对自身历史或板块不弱。

Primitive：

```text
ret_5d
ret_20d
stock_vs_board_5d
stock_vs_board_20d
close_vs_sma20 = close / sma20 - 1
```

Bullish score：

```text
ret_5d_bullish_score = ret_5d
ret_20d_bullish_score = ret_20d
stock_vs_board_5d_bullish_score = stock_vs_board_5d
stock_vs_board_20d_bullish_score = stock_vs_board_20d
close_vs_sma20_bullish_score = close_vs_sma20
```

若 board return 需要现场构造，必须只使用 same board native executable rows 在 `reference_date` 及以前的 close-to-close equal-weight return，并在 feature availability audit 中记录构造状态。

### 6.2 Range Position Filters

目标：压缩位于区间上沿，而不是下跌后贴近低位横盘。

Primitive：

```text
close_position_20d = (close - low_20d) / max(high_20d - low_20d, epsilon)
distance_to_20d_high = high_20d / close - 1
distance_from_20d_low = close / low_20d - 1
higher_low_slope_10d
```

Bullish score：

```text
close_position_20d_bullish_score = close_position_20d
distance_to_20d_high_bullish_score = -distance_to_20d_high
distance_from_20d_low_bullish_score = distance_from_20d_low
higher_low_slope_10d_bullish_score = higher_low_slope_10d
```

`epsilon` 必须固定为 `1e-12`。若 `high_20d - low_20d <= epsilon`，该 row 的 range-position primitives 标记为 not evaluable，不得填 0 或使用未来 fallback。

### 6.3 Drawdown Exclusion Filters

目标：排除“低波动只是下跌后弱反弹/弱横盘”的样本。

Primitive：

```text
max_drawdown_20d
max_drawdown_60d
ret_60d
distance_to_60d_low
```

Bullish score：

```text
max_drawdown_Nd = min(close[tau] / max_close_so_far_within_Nd[tau] - 1), tau in lookback window
max_drawdown_20d_bullish_score = max_drawdown_20d   # value closer to 0 is more bullish
max_drawdown_60d_bullish_score = max_drawdown_60d
ret_60d_bullish_score = ret_60d
distance_to_60d_low_bullish_score = distance_to_60d_low
```

注意：drawdown exclusion 容易重新发现 broad reversal morphology。所有此 family 胜出 token 必须进入 morphology independent evidence gate。

本 family 预期更容易触发：

```text
morphology_rediscovery_suspect
```

这不是 gate 冲突，而是有意设计：drawdown_exclusion 若胜出，实质通过标准由 §9.4 的 morphology independent evidence gate 决定。若它不能在 compression-only baseline 之外提供正 utility margin 与 non-increasing lower-first evidence，最多 diagnostic，不得授权 13B。

### 6.4 Constructive Participation Filters

目标：压缩状态中存在参与度改善，而不是流动性死水。

Primitive：

```text
turnover_zscore_20d
amount_ratio_5d_20d
money_median_5d_vs_20d
up_day_volume_share_20d
volume_up_price_not_down_5d
```

Bullish score：

```text
turnover_zscore_20d_bullish_score = turnover_zscore_20d
amount_ratio_5d_20d_bullish_score = amount_ratio_5d_20d
money_median_5d_vs_20d_bullish_score = money_median_5d_vs_20d
up_day_volume_share_20d_bullish_score = up_day_volume_share_20d
volume_up_price_not_down_5d_bullish_score = volume_up_price_not_down_5d
```

`volume_up_price_not_down_5d` 定义为过去 5 个 reference-date 可见交易日中：

```text
sum(volume[t] where close[t] >= close[t - 1]) / sum(volume[t])
```

若 volume / amount / turnover 字段不可用，相关 primitive 标记为 `not_available`，不得用 fallback future proxy。

13A2 默认不允许在 participation primitive 内嵌 `ret_5d >= 0` 或 `close_position_20d >= train_median` 这类 guard。若需要 guard，必须作为显式 two-filter conjunction 进入 §6.5，并计入 search space。

### 6.5 Allowed Conjunctions

13A2 允许单 filter 与最多二元 conjunction：

```text
single_filter = base_state AND filter_A
two_filter_conjunction = base_state AND filter_A AND filter_B
```

二元 conjunction 只允许跨 family：

```text
relative_strength + range_position
relative_strength + drawdown_exclusion
relative_strength + participation
range_position + participation
drawdown_exclusion + participation
```

禁止同 family 内多阈值堆叠，禁止三元及以上 conjunction，禁止 validation / robustness 反向选择 conjunction。

Candidate grid 必须 deterministic，且默认不会触发 outcome-based truncation：

```text
single_filter_candidates:
  all available primitives
  x {top_50pct, top_40pct, top_30pct, top_20pct}

two_filter_conjunction_candidates:
  allowed family pairs listed above
  x first 3 available primitives per family by fixed primitive_priority
  x matched threshold tiers {top_40pct, top_30pct}
```

Primitive priority is fixed before reading outcome:

```text
relative_strength:
  1. stock_vs_board_20d
  2. ret_20d
  3. close_vs_sma20
  4. stock_vs_board_5d
  5. ret_5d

range_position:
  1. close_position_20d
  2. distance_to_20d_high
  3. distance_from_20d_low
  4. higher_low_slope_10d

drawdown_exclusion:
  1. max_drawdown_20d
  2. ret_60d
  3. distance_to_60d_low
  4. max_drawdown_60d

participation:
  1. turnover_zscore_20d
  2. volume_up_price_not_down_5d
  3. amount_ratio_5d_20d
  4. up_day_volume_share_20d
  5. money_median_5d_vs_20d
```

Default candidate upper bound:

```text
max_directional_candidate_n = 240
expected_max_candidate_n = 72 single + 90 pair = 162
```

If unavailable primitives reduce the grid, candidate count decreases. If an implementation change would exceed `max_directional_candidate_n`, runner must fail closed with:

```text
13A2_blocked_candidate_grid_not_preregistered
```

It must not truncate after seeing outcome.

`directional_filter_dictionary.csv` 必须包含：

```text
filter_id
candidate_ordinal
candidate_type in {single_filter, two_filter_conjunction}
filter_family_id
family_pair_id
primitive_id_1
primitive_id_2
threshold_rule_1
threshold_rule_2
filter_formula
bullish_score_formula_1
bullish_score_formula_2
candidate_grid_status
```

## 7. Directional Denominator 与 Control

对每个 directional candidate：

```text
treated = base_compression_state AND directional_filter
compression_control = base_compression_state AND NOT directional_filter
```

主 readout 只比较 treated vs compression_control。Full native universe 只作为背景 baseline，不作为主要 control。

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_matched_control_audit.csv
```

Match key 默认：

```text
level_0 = month + board + regime + compression_severity_decile + liquidity_decile + allowed non-self directional deciles
level_1 = quarter + board + regime + compression_severity_decile + liquidity_decile
level_2 = quarter + board + regime + compression_severity_decile
level_3 = year + board + regime + compression_severity_decile
```

Token-aware control 规则：

1. directional_filter 所属 primitive / family 的 decile 不得作为 match key，否则会把 signal 匹配掉。
2. compression severity 必须保留在 match key，防止 filter 只是选择更深或更浅的 low-vol cohort。
3. board mix 使用 relative drift audit，不使用单一 board 60% 绝对上限。

`allowed non-self directional deciles` 必须 deterministic：

```text
directional_decile_feature_id = decile(bullish_score) computed on train base compression cohort

For a single_filter candidate:
  excluded_match_decile_ids =
    all primitives in the candidate filter family

For a two_filter_conjunction candidate:
  excluded_match_decile_ids =
    all primitives in both candidate filter families

included_match_decile_ids =
  for every non-candidate family, take the first available primitive by §6.5 primitive_priority
  and include its directional_decile_feature_id
```

Example：

```text
candidate = stock_vs_board_20d_top_40pct AND close_position_20d_top_40pct
excluded families = {relative_strength, range_position}
included match deciles = first available primitive from drawdown_exclusion and participation
```

必须在 `directional_filter_matched_control_audit.csv` 记录：

```text
excluded_match_decile_ids
included_match_decile_ids
compression_severity_decile_used
liquidity_decile_used
```

Control quality：

```text
primary_comparable:
  effective_control_ratio >= 3
  coarsening_level in {level_0, level_1}
  max_standardized_diff_after_match <= 0.25

coarsened_caveat:
  effective_control_ratio >= 2
  coarsening_level = level_2
  max_standardized_diff_after_match <= 0.50

insufficient_control:
  otherwise
```

`insufficient_control` 的 candidate 可以报告 diagnostic readout，但不得通过 winner uplift gate 或授权 13B。

Control audit 还必须输出：

```text
filter_id
split_bucket
treated_n
control_n
coarsening_level
effective_control_ratio
matched_block_n
unmatched_treated_n
max_standardized_diff_after_match
control_match_quality
match_status
```

## 8. Metrics

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_readout.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_badside_utility_audit.csv
```

Readout 字段：

```text
filter_id
filter_family_id
filter_formula
split_bucket
treated_n
treated_positive_n
treated_winner_rate
control_n
control_positive_n
control_winner_rate
compression_baseline_winner_rate
native_baseline_winner_rate
winner_rate_diff_vs_compression_control
winner_rate_diff_ci_low
winner_rate_diff_ci_high
auc_one_vs_compression_control
rank_ic_within_base_compression
top_decile_lift_within_base_compression
control_match_quality
readout_status
```

Bad-side / utility 字段：

```text
filter_id
split_bucket
treated_lower_first_rate
control_lower_first_rate
lower_first_uplift_vs_compression_control
treated_fast_fail_rate
control_fast_fail_rate
fast_fail_uplift_vs_compression_control
treated_same_bar_conflict_rate
median_upper_barrier_return
median_abs_lower_barrier_return
utility_proxy_per_entry
utility_proxy_total_indexed
utility_proxy_total_indexed_ci_low
compression_baseline_utility_total_indexed
utility_margin_vs_compression_baseline
utility_margin_vs_compression_baseline_ci_low
cost_buffer_return
cost_buffer_source
badside_status
utility_status
```

Utility proxy 默认：

```text
utility_proxy_per_entry =
  treated_winner_rate * median_upper_barrier_return
  - treated_lower_first_rate * median_abs_lower_barrier_return
  - cost_buffer_return
```

Cost buffer 必须与 13A / 12A7g lineage 使用同一口径：

```text
default_cost_buffer_return = 0.01
cost_buffer_source_priority:
  1. 13A config / manifest lineage, if available
  2. 12A7g config / label lineage, if available
  3. default_cost_buffer_return = 0.01
```

若 lineage 中存在非默认 cost buffer，13A2 必须以 lineage 值为准，并在 base cohort、bad-side / utility、deployability audit 中记录 `cost_buffer_return` 与 `cost_buffer_source`。Base compression utility 与 directional filter utility 必须使用同一 `cost_buffer_return`；否则 utility margin 不可比，状态为：

```text
13A2_blocked_cost_buffer_lineage_mismatch
```

### 8.1 CI / Bootstrap

所有 CI 字段必须使用同一套 block bootstrap，不得由各表自行实现不同口径。

Bootstrap config：

```text
bootstrap_seed = 13202
bootstrap_resample_n = 500
bootstrap_min_valid_replicates = 250
bootstrap_ci_low_quantile = 0.05
bootstrap_unit = instrument_month_block
```

Bootstrap rules：

```text
1. 在每个 split 内按 instrument_month_block 抽样，有放回抽取 block。
2. 每个 replicate 内重算 winner_rate_diff、lower_first_uplift、utility_proxy_per_entry、
   utility_proxy_total_indexed、utility_margin_vs_compression_baseline。
3. CI low 取 replicate 分布的 5% 分位数。
4. 若 valid replicates < bootstrap_min_valid_replicates，相关 gate 标记为 insufficient_ci_fail。
5. synthetic tests 可以把 bootstrap_resample_n 降低，但 full run 不得低于默认值。
```

必须输出 bootstrap provenance：

```text
bootstrap_seed
bootstrap_resample_n
bootstrap_valid_replicates
bootstrap_ci_low_quantile
bootstrap_unit
ci_status
```

## 9. Gate

### 9.1 Train Selection Gate

Train 只用于选择 candidate，不用于最终授权。

Candidate 必须满足：

```text
train treated_n >= 1000
train treated_positive_n >= 100
train control_match_quality != insufficient_control
train winner_rate_diff_vs_compression_control > 0
train auc_one_vs_compression_control >= 0.55
train lower_first_uplift_vs_compression_control <= 0.02
train utility_proxy_per_entry > 0
```

Train score：

```text
train_score =
  winner_rate_diff_vs_compression_control
  - max(lower_first_uplift_vs_compression_control, 0)
  + 0.5 * utility_proxy_per_entry
```

Tie-breaking：

```text
1. higher train_score
2. lower lower_first_uplift_vs_compression_control
3. higher treated_positive_n
4. simpler filter: single_filter before two_filter_conjunction
5. lexicographic filter_id
```

必须分别输出：

```text
selected_filter_candidate_ordinal
selected_filter_train_score_rank
```

避免重复 13A 中 `selected_token_rank_train` 语义不清的问题。

### 9.2 Validation / Robustness Direction Gate

最终授权要求 validation 与 robustness 同时满足：

```text
treated_n >= 500
treated_positive_n >= 50
control_match_quality in {primary_comparable, coarsened_caveat}
winner_rate_diff_vs_compression_control > 0
winner_rate_diff_ci_low >= -0.01
auc_one_vs_compression_control >= 0.55
top_decile_lift_within_base_compression >= 0.02
```

`coarsened_caveat` 不能单独授权 13B；若 selected filter 在 validation 或 robustness 为 `coarsened_caveat`，必须同时通过 stricter utility 与 stability caveat gate，才能升级为：

```text
coarsened_caveat_pass_strict
```

升级条件必须在 validation 与 robustness 同时满足：

```text
raw control_match_quality = coarsened_caveat
effective_control_ratio >= 2.5
coarsening_level = level_2
max_standardized_diff_after_match <= 0.35
winner_rate_diff_ci_low >= 0
lower_first_uplift_vs_compression_control <= -0.005
fast_fail_uplift_vs_compression_control <= 0
utility_proxy_per_entry > 0
utility_proxy_total_indexed_ci_low > 0
utility_margin_vs_compression_baseline_ci_low > 0
max_abs(treated_board_share - base_compression_board_share) <= 0.10
max_abs(treated_board_share - matched_control_board_share) <= 0.10
at least 5 calendar_year slices with utility_proxy_per_entry > 0
```

若任一条件不满足，保留 `coarsened_caveat`，candidate 最多 diagnostic，不得授权 13B。

### 9.3 Bad-side / Utility Gate

13A2 的 primary gate 是 bad-side / utility，不是 AUC。

Validation 与 robustness 必须同时满足：

```text
lower_first_uplift_vs_compression_control <= 0
fast_fail_uplift_vs_compression_control <= 0.01
utility_proxy_per_entry > 0
utility_margin_vs_compression_baseline_ci_low > 0
```

若 per-entry utility 为正但 total indexed utility 为负，只能 diagnostic，不得授权 13B。

若 total indexed utility 为正但 per-entry utility 不为正，也只能 diagnostic，除非 requirement 另行预注册 coverage/recall tradeoff；13A2 默认不允许该逃生通道。

`lower_first_uplift_vs_compression_control <= 0` 是有意严格条件。13A2 的目标不是只找净 utility 为正的更活跃突破样本，而是验证 compression 内部是否能被 PIT-safe 方向信号“掰单尾”：保留或提升 upper-first，同时不增加 lower-first。若某 filter 的 upper-first uplift 足以让 utility 转正，但 lower-first uplift 仍为小正数，该 filter 只能标记：

```text
net_utility_positive_but_left_tail_not_disambiguated
```

该状态可以作为研究 insight 报告，但不得授权 13B。

### 9.4 Morphology Independent Evidence Gate

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_morphology_audit.csv
```

Anchor：

```text
volatility_20d
max_drawdown_20d
distance_to_20d_low
distance_to_20d_high
close_position_20d
ret_20d
```

若任一 split 中：

```text
max_abs_rank_corr_with_morphology_anchor >= 0.70
```

则标记：

```text
morphology_rediscovery_suspect
```

Suspect candidate 必须额外满足：

```text
validation utility_margin_vs_compression_baseline_ci_low > 0
robustness utility_margin_vs_compression_baseline_ci_low > 0
validation lower_first_uplift_vs_compression_control <= 0
robustness lower_first_uplift_vs_compression_control <= 0
validation control_match_quality = primary_comparable
robustness control_match_quality = primary_comparable
```

否则只能 diagnostic，不得授权 13B。

### 9.5 Stability Gate

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_stability_audit.csv
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
at least 3 calendar_year slices with winner_rate_diff_vs_compression_control > 0
at least 3 calendar_year slices with utility_proxy_per_entry > 0
max_abs(treated_board_share - base_compression_board_share) <= 0.15
max_abs(treated_board_share - matched_control_board_share) <= 0.15
instrument_month_block_bootstrap_ci_low > -0.01
```

若只有单一 market regime 可用，标记：

```text
regime_single_bucket_caveat
```

该 caveat 不单独 fail closed，但 report 必须说明不能主张跨 regime 稳定性。

### 9.6 Search Control Gate

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_search_multiplicity_audit.csv
```

Effective search space 至少包括：

```text
available_primitive_n
single_filter_candidate_n
two_filter_conjunction_candidate_n
candidate_grid_n = single_filter_candidate_n + two_filter_conjunction_candidate_n
threshold_candidate_n = 4 for single filters, 2 matched tiers for pair filters
bullish_score_orientation_candidate_n = 1
family_pair_candidate_n = 5
match_coarsening_policy_n
base_state_candidate_n = 1  # fixed from 13A, still recorded
effective_search_space_n
effective_search_space_n_outcome_free_adjusted
```

默认 gate：

```text
fdr_q_value <= 0.10
deflated_auc_validation >= 0.55
deflated_utility_margin_validation_ci_low > 0
deflated_utility_margin_robustness_ci_low > 0
```

Search-control pass 不得覆盖 bad-side、control quality、morphology 或 deployability failure。

### 9.7 Deployability Gate

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_deployability_gate_audit.csv
```

Validation 与 robustness 必须同时满足：

```text
coverage_share_within_native >= 0.005
coverage_share_within_base_compression >= 0.02
captured_positive_n >= 50
captured_positive_share_within_base_compression >= 0.05
utility_proxy_per_entry > 0
utility_proxy_total_indexed_ci_low > 0
precision_recall_frontier_status = pass
```

13A2 默认不允许 niche 逃生通道。若 filter utility 明显为正但 coverage 未达到上述阈值，标记为：

```text
niche_directional_filter_diagnostic_only
```

该状态不得授权 13B。若后续要研究 niche filter，必须另开 requirement 并预注册 niche coverage / recall / capacity 口径。

## 10. Decision States

必须输出：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_disambiguation_decision.csv
```

Decision precedence：

```text
1. input / raw PIT / qfq / split / entry / label lineage fail
   -> 13A2_blocked_input_or_label_lineage_failure
   next_allowed_requirement = fix_input_lineage_then_rerun_13A2

1b. cost buffer lineage 与 utility audit 口径不可对齐
   -> 13A2_blocked_cost_buffer_lineage_mismatch
   next_allowed_requirement = fix_lineage_cost_buffer_then_rerun_13A2

2. 13A lineage 或 selected compression token 不可证明
   -> 13A2_blocked_upstream_13a_lineage_failure
   next_allowed_requirement = fix_or_rerun_13A

3. base compression cohort 不可复现或样本不足
   -> 13A2_base_compression_not_reproducible_stop
   next_allowed_requirement = revisit_13A_base_state

4. 无 train candidate 通过 direction selection gate
   -> 13A2_no_directional_filter_survives_stop_event_mining
   next_allowed_requirement = none

5. train 有 candidate，但 validation / robustness direction 或 search-control 不过
   -> 13A2_no_directional_filter_survives_stop_event_mining
   next_allowed_requirement = none

6. direction readout 过线，但 bad-side / utility / deployability / control quality 不过
   -> 13A2_directional_filter_diagnostic_only_badside_or_utility_fail
   next_allowed_requirement = none

7. coverage 未达 deployability 阈值，即使 utility 为正
   -> 13A2_directional_filter_diagnostic_only_niche_coverage
   next_allowed_requirement = none

8. morphology_rediscovery_suspect 且 independent evidence 不过
   -> 13A2_directional_filter_diagnostic_only_morphology_rediscovery
   next_allowed_requirement = none

9. selected filter 通过全部 gate
   -> 13A2_compression_direction_supported_authorize_13B
   next_allowed_requirement = requirement_13b_train_frozen_compression_direction_sequence_mining.md
```

`next_allowed_requirement = none` 在本 requirement 中只表示：

```text
do not proceed to 13B from this fixed compression base.
```

它不表示 Episode 13 全局终结，也不否决对其他 fixed base state 另开同类 directional-disambiguation requirement。

输出字段：

```text
decision_state
next_allowed_requirement
input_gate_status
upstream_13a_lineage_gate_status
cost_buffer_lineage_gate_status
base_compression_gate_status
direction_readout_gate_status
badside_utility_gate_status
control_quality_gate_status
morphology_independent_evidence_gate_status
stability_gate_status
search_control_gate_status
deployability_gate_status
selected_filter_id
selected_filter_family_id
selected_filter_formula
selected_filter_candidate_ordinal
selected_filter_train_score_rank
selected_filter_control_match_quality
selected_filter_morphology_flag
sequence_mining_authorized
decision_reason
```

## 11. Required Outputs

Publishable tables：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/input_artifact_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/upstream_13a_lineage_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/base_compression_cohort_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_feature_availability_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_dictionary.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_threshold_freeze_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_matched_control_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_readout.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_badside_utility_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_morphology_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_stability_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_search_multiplicity_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_deployability_gate_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_disambiguation_decision.csv
```

Report：

```text
outputs/publishable/reports/compression_directional_disambiguation_preflight_report.md
```

Manifest：

```text
outputs/manifests/13A2_compression_directional_disambiguation_preflight_manifest.json
```

Local cache optional：

```text
outputs/local_cache/13A2_compression_directional_disambiguation_preflight/base_compression_directional_panel.parquet
```

Local cache 不得进入 publishable scope；manifest 必须记录 cache path、existence、row count、schema hash 与 whether cache was used。

## 12. Report Requirements

Report 必须用中文写清楚：

1. 13A2 不是重找 compression，而是在 13A compression cohort 内做方向分辨；
2. base compression cohort 的 winner / lower-first / utility baseline；
3. selected directional filter 的公式、阈值来源与 PIT availability；
4. treated vs compression_control 的 winner uplift、lower-first uplift、utility；
5. 相对 compression-only baseline 的增量，而不是只相对 full native baseline；
6. matched-control quality、included/excluded match deciles 与 coarsening caveat；
7. morphology independent evidence；
8. board mix 使用 relative drift，不使用 60% absolute board gate；
9. 若 stop，必须说明 stop 的主因，不得用漂亮 AUC 覆盖 bad-side / utility failure；
10. 若 13A2 stop，明确它只否决 fixed compression base 的方向分辨，不是 Episode 13 全局否定；
11. 是否授权 13B。

## 13. Tests

必须包含 synthetic tests，不依赖大文件。

测试清单：

1. 缺 13A decision / dictionary / manifest 时 fail closed；
2. 13A selected token 不是 `volatility_20d__bottom_20pct` 时 fail closed；
3. base compression threshold 从 13A dictionary 读取，不 hard-code；
4. base compression cohort denominator 与 split boundary 可复现；
5. cost_buffer_return 从 13A / 12A7g lineage 继承，base 与 treated utility 不一致时 fail closed；
6. 每个 primitive 先转成 canonical bullish_score，再统一使用 top quantile；
7. directional thresholds 只从 train base cohort 冻结；
8. validation / robustness 不参与 threshold、orientation、conjunction selection；
9. candidate grid 固定为 single 全量 + 预注册 first-3 primitive pair grid，超过 240 fail closed，不 outcome truncation；
10. participation guard 不得隐式内嵌，必须作为显式 conjunction；
11. treated / compression_control 分母互斥且并集等于 base cohort 可评估行；
12. token-aware match 排除 candidate family 全部 decile；conjunction 排除两侧 family；
13. compression_severity_decile 保留在 match key；
14. `insufficient_control` candidate 不得通过 winner gate；
15. `coarsened_caveat` 只有满足 strict upgrade 条件才可授权；
16. lower-first uplift > 0 时 badside gate fail，即使 winner AUC 与 net utility 很高；
17. `net_utility_positive_but_left_tail_not_disambiguated` 不得授权 13B；
18. utility per entry <= 0 时 deployability fail；
19. niche coverage 未达阈值时只能 diagnostic-only；
20. morphology suspect 且 independent evidence fail 时不得授权；
21. drawdown_exclusion 胜出时预期触发 morphology suspect，并按 §9.4 判定；
22. board stability 使用 relative drift，不使用 60% absolute board share；
23. bootstrap CI 使用统一 seed / block unit / resample count；
24. search multiplicity 计入 threshold / orientation / conjunction / match policy；
25. selected filter candidate ordinal 与 train score rank 分开输出；
26. manifest hash 覆盖所有 publishable outputs；
27. rerun deterministic：相同输入、config、seed 下 output hash 一致。

## 14. Implementation Order

推荐实现顺序：

```text
1. parse config and path aliases
2. input artifact audit
3. load and verify 13A lineage
4. rebuild native universe and selected label using 13A/12A7g lineage
5. rebuild base compression cohort from 13A selected token threshold
6. compute directional primitives PIT-safely
7. freeze directional thresholds on train base cohort
8. build single and allowed two-filter candidates
9. construct treated vs compression_control matched controls
10. compute readout, bad-side, utility, morphology, stability, search, deployability audits
11. apply decision precedence
12. write publishable tables, report, manifest
13. run synthetic tests and py_compile
```

## 15. Acceptance Criteria

Requirement is implementation-ready only if:

```text
base_compression_state is fixed from 13A
directional_filter is evaluated only inside base compression cohort
primary control is compression_control, not full native universe
bad-side / utility gate is stricter than winner uplift gate
board stability uses relative drift
cost_buffer_return is lineage-consistent across base and treated utility
candidate grid has deterministic non-outcome construction
coarsened_caveat and niche coverage paths are diagnostic unless explicit strict gates pass
search-control cannot override bad-side / utility / control failure
decision_state is single and fail-closed
all outputs are pre-named
synthetic tests cover all fail-closed paths
```

13A2 成功的最低标准不是找到更高 AUC，而是找到：

```text
compression + directional_filter
  relative to compression-only control:
    winner uplift > 0
    lower-first uplift <= 0
    utility > 0
    deployability pass
    morphology independent evidence pass when suspect
```

否则 Episode 13 不得进入 sequence mining。
