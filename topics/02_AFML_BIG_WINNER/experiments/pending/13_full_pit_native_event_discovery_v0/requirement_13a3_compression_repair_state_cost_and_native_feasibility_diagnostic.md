# 需求：13A3 Compression Repair-State Cost and Native Feasibility Diagnostic

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
phase_id = 13A3
run_id = 13A3_compression_repair_state_cost_and_native_feasibility_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.py
expected_config = configs/config_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.yaml
expected_test_file = tests/test_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.py
upstream_requirement_13a = EXPERIMENT_ROOT/requirement_13a_full_pit_native_token_cartography_preflight.md
upstream_requirement_13a2 = EXPERIMENT_ROOT/requirement_13a2_compression_directional_disambiguation_preflight.md
upstream_report_13a = EXPERIMENT_ROOT/outputs/publishable/reports/native_token_cartography_preflight_report.md
upstream_report_13a2 = EXPERIMENT_ROOT/outputs/publishable/reports/compression_directional_disambiguation_preflight_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13A3 是 13A2 之后的轻量诊断，不是 13B sequence mining。13A2 给出的关键负面结论不是“compression 内没有方向信号”，而是：

```text
directional signal exists,
but compression-conditional matched-control comparability fails,
and utility may be sensitive to the 100bps cost buffer.
```

13A3 的任务是把这个失败拆成三个可审计问题：

```text
1. cost_buffer 是不是过严到压死了本来接近可用的方向信号？
2. "compression + position_not_weak + participation_recovery"
   如果作为一个单一 native composite event state，而不是 compression 内部 filter，
   是否能在 full-native 框架下通过 bad-side / utility / deployability 诊断？
3. 若 composite state 看起来有效，它是否仍只是 broad morphology / reversal / drawdown 的换皮？
```

13A3 只能授权下一步研究需求，不授权交易、不授权生产、不直接修复 13A2 的 selected filter。

## 2. 核心问题

13A3 回答以下问题：

```text
Q1. 在不改变 13A2 candidate thresholds、orientation、feature formula 的前提下，
    cost_buffer_return ∈ {0, 25bps, 50bps, 75bps, 100bps}
    对现有 diagnostic candidates 的 utility 影响有多大？

Q2. 若 100bps 下 utility 为负，但 25bps / 50bps 下转正，
    这是 cost 口径问题，还是信号幅度仍不足？

Q3. 13A2 发现的 "低波动压缩 + 位置不弱 + 参与度恢复" 是否应被视为
    一个新的 composite native event state，而不是 compression 内部的二级 filter？

Q4. 这些 composite state 在 full-PIT native denominator 下，是否同时满足：
    winner uplift、lower-first / fast-fail 不同步放大、utility 转正、
    denominator drift 可解释、morphology independent evidence 为正？

Q5. Episode 13 应该继续 compression-repair 路线、先做 cost model calibration、
    还是停止 winner discovery branch 并转向 defense / participation 研究？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

13A3 明确不是：

```text
13B sequence mining
compression-conditional matched-control retry
new full-space token search
cost model calibration
trading strategy backtest
```

13A3 是诊断性 requirement。它可以得出：

```text
compression repair state deserves a next feasibility requirement
```

但不得直接主张：

```text
compression repair state is deployable alpha
```

13A3 的正结果最多允许新建以下之一：

```text
requirement_13a4_cost_model_calibration_for_compression_repair_state.md
requirement_13a4_compression_repair_state_confirmatory_preflight.md
```

13A3 使用的是 13A2 报告暴露后的 diagnostic shortlist；该 shortlist 已受到 validation / robustness 读数的人工关注影响。因此 13A3 永远不得直接授权 13B sequence mining，且最终必须满足：

```text
sequence_mining_authorized = False
```

只有当 composite state 在 100bps reference cost 下也通过 full-native bad-side、utility、morphology independent evidence 与 denominator drift gate，13A3 才能授权一份新的 train-frozen confirmatory preflight。若只在 50bps 下通过，必须先进入 13A4 cost model calibration；若只在 25bps 下通过，结果仅为 diagnostic，不得授权下一份 requirement。

## 4. 继承边界

### 4.1 允许继承

13A3 可以继承：

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
13A2 diagnostic candidate dictionary
split boundary from 12A7g / 13A / 13A2
```

13A3 必须读取 13A publishable artifacts 作为 lineage：

```text
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_decision.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_dictionary.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_cartography_readout.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_badside_veto_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_deployability_gate_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_token_morphology_collinearity_audit.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_label_portability_audit.csv
outputs/manifests/13A_full_pit_native_token_cartography_preflight_manifest.json
```

13A3 必须读取 13A2 publishable artifacts 作为 lineage：

```text
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/base_compression_cohort_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_dictionary.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_threshold_freeze_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_readout.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_badside_utility_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/directional_filter_matched_control_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_search_multiplicity_audit.csv
outputs/publishable/tables/13A2_compression_directional_disambiguation_preflight/compression_directional_disambiguation_decision.csv
outputs/manifests/13A2_compression_directional_disambiguation_preflight_manifest.json
```

13A3 可以复用 13A / 13A2 runner 的 deterministic rebuild logic，但不得把聚合表当成逐行 truth。逐行 native universe、label、event state membership、barrier outcome、entry price、cost-adjusted utility 必须从 raw PIT universe / qfq bars 或可审计 row-level cache 重建。

### 4.2 禁止继承 / 禁止主张

13A3 明确不得：

- 不使用 C0 active band、C0 thresholds、C0 state-change family formula；
- 不修复 C0 selector 或 `volatility_reconciliation_fail`；
- 不重新选择 winner label；
- 不重新搜索 base compression state；
- 不在 full native space 搜索任意新 primitive；
- 不用 validation / robustness 选择 cost tier、composite state、threshold、orientation 或 decision rule；
- 不把 13A2 的 `insufficient_control` filter 直接改名为 supported event；
- 不做 len-2 / len-3 sequence mining；
- 不训练 ML 模型，不做 probability calibration；
- 不做资金曲线、仓位、滑点、容量或交易系统。

13A3 不能主张：

```text
降低 cost_buffer 后的正 utility = 可部署。
```

13A3 只能主张：

```text
在给定 cost tier 下，某些 pre-frozen composite repair state
值得或不值得进入下一份 requirement。
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

同 13A / 13A2：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到 qfq daily `reference_pos` 与 next-open executable `entry_pos`。不可证明时 row-level not evaluable；全局 schema / PIT 失败时 fail closed。

### 5.2 Upstream 13A lineage

13A3 要求 13A decision table 满足：

```text
input_gate_status = pass
upstream_lineage_gate_status = pass
native_universe_gate_status = pass
label_portability_gate_status = pass
selected_token_id = volatility_20d__bottom_20pct
selected_token_family_id = volatility_range
sequence_mining_authorized = False
```

13A selected token dictionary 必须提供 train-frozen compression threshold：

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
13A3_blocked_upstream_13a_lineage_failure
```

### 5.3 Upstream 13A2 lineage

13A3 要求 13A2 decision table 满足：

```text
input_gate_status = pass
upstream_13a_lineage_gate_status = pass
label_lineage_gate_status = pass
cost_buffer_lineage_gate_status = pass
base_compression_gate_status = pass
candidate_grid_gate_status = pass
decision_state = 13A2_no_directional_filter_survives_stop_event_mining
sequence_mining_authorized = False
```

13A3 必须读取并记录但不得要求通过以下 13A2 gate，因为 13A3 的前提正是这些 gate 未能授权 selected filter：

```text
winner_uplift_gate_status
direction_readout_gate_status
control_quality_gate_status
badside_utility_gate_status
morphology_gate_status
morphology_independent_evidence_gate_status
stability_gate_status
search_control_gate_status
deployability_gate_status
decision_reason
```

13A2 不需要有 selected filter；13A3 的前提正是 13A2 没有 selected filter。若 13A2 已经授权 13B，则 13A3 不应运行，状态为：

```text
13A3_blocked_upstream_13a2_already_authorized
```

13A3 必须用 13A2 `directional_filter_dictionary.csv` 解析每个 required `source_13a2_filter_id` 到：

```text
primitive_id_1
primitive_id_2
threshold_rule_1
threshold_rule_2
threshold_value_1
threshold_value_2
```

然后用 13A2 `directional_filter_threshold_freeze_audit.csv` 验证每个 `(primitive_id, threshold_rule)` 的 primitive-level threshold 存在且数值一致。注意：`directional_filter_threshold_freeze_audit.csv` 不要求包含 `filter_id`；`filter_id` 的权威来源是 `directional_filter_dictionary.csv`。缺任一 required filter、primitive threshold、或两表 threshold value 不一致时状态为：

```text
13A3_blocked_required_composite_threshold_missing
```

### 5.4 12A7g label lineage

13A3 必须沿用 13A / 13A2 / 12A7g 的 selected label：

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
13A3_blocked_label_lineage_failure
```

## 6. Row-Level Rebuild

13A3 必须重建以下 row-level panel：

```text
native_opportunity_panel(row)
  = 13A native PIT executable denominator
  + selected label fields
  + barrier outcome fields
  + utility barrier return fields
  + 13A2 required directional primitive values
  + 13A2 train-frozen threshold membership flags
```

可选使用 13A / 13A2 local cache，但必须验证：

```text
row key uniqueness
instrument x reference_date coverage
split boundary equality
selected label equality
base compression membership equality
threshold value equality
sha256 / schema hash when manifest provides it
```

Cache 校验失败时必须从 raw PIT universe 和 qfq daily bars 重建；不得 fail open。

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/upstream_13a_lineage_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/upstream_13a2_lineage_audit.csv
```

## 7. Diagnostic 1: Cost-Buffer Sensitivity

### 7.1 Cost grid

Cost sensitivity 必须只改变 `cost_buffer_return`，不得改变 label、barrier、entry price、state membership、threshold、orientation、candidate grid 或 split。

预注册 cost grid：

```text
cost_buffer_grid = [0.0000, 0.0025, 0.0050, 0.0075, 0.0100]
cost_tier_label = [0bps, 25bps, 50bps, 75bps, 100bps]
reference_cost_buffer_return = 0.0100
moderate_cost_buffer_return = 0.0050
```

Utility 公式必须与 13A / 13A2 一致，仅替换 cost 项。若 13A / 13A2 的 manifest 或 config 中存在 cost buffer lineage，则 13A3 必须读取并记录：

```text
upstream_cost_buffer_return
upstream_cost_buffer_source
```

若 upstream cost 与 `reference_cost_buffer_return = 0.0100` 不一致，13A3 不得硬编码 100bps，必须以 upstream lineage 为 reference，并在 report 中显式说明。

### 7.2 Sensitivity universe

Cost sensitivity 分两层输出：

1. 全 13A2 candidate grid：

```text
all_13a2_candidate_cost_scan
```

用于判断 13A2 的 utility-negative 结论是否主要由 cost buffer 造成。

2. 13A3 required composite shortlist：

```text
required_repair_state_cost_scan
```

用于决定是否进入 composite native feasibility。

不得根据 validation / robustness 的 cost scan 反向新增 composite state。

### 7.3 Output

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/cost_buffer_sensitivity_audit.csv
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/cost_buffer_turning_point_summary.csv
```

`cost_buffer_sensitivity_audit.csv` 字段：

```text
scope_id                         # all_13a2_candidate_grid / required_repair_state_shortlist
filter_id_or_state_id
source_phase                     # 13A2_filter / 13A3_composite_state
split_bucket
cost_buffer_return
cost_tier_label
treated_n
treated_positive_n
winner_rate
lower_first_rate
fast_fail_rate
self_utility_proxy_per_entry
self_utility_proxy_total_indexed
self_utility_margin_vs_100bps
self_utility_positive
lower_first_uplift_vs_native
fast_fail_uplift_vs_native
bootstrap_ci_low
bootstrap_ci_high
ci_status
```

这里的 `self_utility_*` 只表示该 candidate / state 自身在指定 cost tier 下的 utility，不是相对 native baseline 或 compression base 的 margin。不得把 §7 的 `self_utility_positive` 当成 §9 的 `utility_margin_vs_native > 0` 或 `utility_margin_vs_compression_base > 0`。

`cost_buffer_turning_point_summary.csv` 字段：

```text
filter_id_or_state_id
source_phase
first_cost_tier_with_validation_self_utility_positive
first_cost_tier_with_robustness_self_utility_positive
first_cost_tier_with_both_validation_and_robustness_self_utility_positive
self_utility_positive_at_0bps
self_utility_positive_at_25bps
self_utility_positive_at_50bps
self_utility_positive_at_75bps
self_utility_positive_at_100bps
cost_sensitivity_status
```

### 7.4 Cost sensitivity status

每个 candidate / state 的 `cost_sensitivity_status`：

```text
no_economic_amplitude:
  validation self_utility_proxy_per_entry <= 0 and robustness self_utility_proxy_per_entry <= 0
  even at cost_buffer_return = 0

cost_fragile_25bps_only:
  validation and robustness self_utility_proxy_per_entry > 0 at 25bps
  but not at 50bps

cost_viable_50bps:
  validation and robustness self_utility_proxy_per_entry > 0 at 50bps
  but not at 100bps

cost_robust_100bps:
  validation and robustness self_utility_proxy_per_entry > 0 at 100bps
```

若 required composite shortlist 中没有任何 state 达到 `cost_fragile_25bps_only` 或更高，最终状态优先为：

```text
13A3_stop_cost_sensitivity_no_economic_amplitude
```

若只有 `cost_fragile_25bps_only`，可以继续输出 composite readout，但不得授权 cost calibration、confirmatory preflight 或 13B；最终最多为：

```text
13A3_diagnostic_only_cost_too_fragile
```

## 8. Composite Repair-State Shortlist

13A3 不重新搜索 arbitrary conjunction。Composite states 必须来自 13A2 报告中已经暴露的 diagnostic slices，并在本 requirement 中预注册。

重要边界：

```text
shortlist_source = post_13A2_diagnostic_report
confirmatory_status = false
```

这意味着 13A3 的 shortlist 不是一组完全 train-only 发现的候选。13A2 报告中的 train / validation / robustness diagnostic readout 已经影响了本需求选择哪些 slice 进入 13A3。因此 13A3 可以判断这些 slice 是否值得下一份 train-frozen confirmatory preflight，但不得直接把 13A3 的 positive 结果升级为 13B sequence mining 授权。

Base compression condition 固定为：

```text
compression_base(row) =
  native_universe(row)
  and volatility_20d(row) <= 13A train-frozen volatility_20d__bottom_20pct threshold
```

Composite event state 统一格式：

```text
composite_state(row) =
  compression_base(row)
  and pre_frozen_directional_component(row)
  and pre_frozen_participation_filter(row)
```

`pre_frozen_directional_component` 分两类：

```text
position_strength_component:
  range position / relative strength, morphology risk normal

drawdown_momentum_suspect_component:
  drawdown / ret_60d repair state, morphology risk suspect
```

### 8.1 Required composite states

必须实现以下 state。`source_13a2_filter_id` 必须来自 13A2 `directional_filter_dictionary.csv`，component thresholds 必须再由 13A2 `directional_filter_threshold_freeze_audit.csv` 验证：

| state_id | source_13a2_filter_id | component_family | directional_component_class | morphology_risk |
|---|---|---|---|---|
| repair_range_participation_core_30 | `distance_from_20d_low__top_30pct__AND__turnover_zscore_20d__top_30pct` | range + participation | position_strength_component | normal |
| repair_sma_participation_core_30 | `close_vs_sma20__top_30pct__AND__turnover_zscore_20d__top_30pct` | relative + participation | position_strength_component | normal |
| repair_close_position_participation_core_30 | `close_position_20d__top_30pct__AND__turnover_zscore_20d__top_30pct` | range + participation | position_strength_component | normal |
| repair_range_participation_broad_40 | `distance_from_20d_low__top_40pct__AND__turnover_zscore_20d__top_40pct` | range + participation | position_strength_component | normal |
| repair_ret60_volume_suspect_30 | `ret_60d__top_30pct__AND__volume_up_price_not_down_5d__top_30pct` | drawdown / momentum + participation | drawdown_momentum_suspect_component | morphology_suspect |
| repair_drawdown_amount_suspect_30 | `max_drawdown_20d__top_30pct__AND__amount_ratio_5d_20d__top_30pct` | drawdown + participation | drawdown_momentum_suspect_component | morphology_suspect |

State priority is fixed before 13A3 readout:

```text
1. repair_range_participation_core_30
2. repair_sma_participation_core_30
3. repair_close_position_participation_core_30
4. repair_range_participation_broad_40
5. repair_ret60_volume_suspect_30
6. repair_drawdown_amount_suspect_30
```

Tie-break:

```text
1. stronger cost tier first: 100bps > 75bps > 50bps > 25bps > 0bps
2. higher train utility_proxy_per_entry at the same cost tier
3. lower train lower_first_rate
4. lower state_priority
```

### 8.2 Composite state dictionary

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_repair_state_dictionary.csv
```

字段：

```text
state_id
state_priority
source_13a2_filter_id
base_token_id
base_threshold_value
component_1_primitive_id
component_1_threshold_rule
component_1_threshold_value
component_2_primitive_id
component_2_threshold_rule
component_2_threshold_value
component_family
directional_component_class
morphology_risk
shortlist_source
confirmatory_status
threshold_source_split
future_data_used
state_reproduction_status
```

若任一 state 无法复现，必须保留该 state 行并标记：

```text
state_reproduction_status = fail
```

若全部 required states 无法复现，状态为：

```text
13A3_blocked_composite_state_reproduction_failure
```

## 9. Composite Full-Native Feasibility

### 9.1 Full-native frame

13A3 的 composite readout 不再使用 compression-only matched control 作为 primary gate。每个 composite state 作为一个 native event state，与 full-PIT native denominator 比较：

```text
treated(row) = composite_state(row)
native_baseline(row) = native_opportunity_universe(row)
complement(row) = native_opportunity_universe(row) and not composite_state(row)
```

Primary readout 相对 `native_baseline`；`complement` 只作为辅助解释，不作为 matched-control fail gate。

这样做的原因：

```text
13A2 已证明 directional filter 改变 compression denominator，
compression-only matched-control 框架无法容纳该状态。
13A3 要检验的是：它作为一个完整 native event state 是否有经济意义。
```

Interpretation boundary:

```text
13A3 full-native readout estimates total_native_effect.
It does not identify pure_conditional_state_edge.
```

若 composite state 在 full-native frame 中表现为正，报告必须明确说明这可能来自：

```text
1. state edge 本身；
2. board / liquidity / compression severity / calendar / regime 分布迁移；
3. 二者混合。
```

Denominator drift audit 只能暴露分布迁移，不能证明已经剥离分布效应。因此任何 positive 13A3 结果都必须把以下任务交给 confirmatory preflight，而不得在 13A3 中宣称完成：

```text
distribution_vs_state_edge_disentanglement_required = true
```

### 9.2 Readout output

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_native_readout.csv
```

字段：

```text
state_id
split_bucket
treated_n
treated_positive_n
native_denominator_n
native_positive_n
coverage_share
captured_positive_share
treated_winner_rate
native_winner_rate
winner_rate_diff_vs_native
winner_rate_diff_ci_low
winner_rate_diff_ci_high
treated_lower_first_rate
native_lower_first_rate
lower_first_uplift_vs_native
treated_fast_fail_rate
native_fast_fail_rate
fast_fail_uplift_vs_native
binary_state_auc
top_lift_proxy
readout_status
```

Minimum support:

```text
train treated_n >= 1000
train treated_positive_n >= 100
validation treated_n >= 500
validation treated_positive_n >= 50
robustness treated_n >= 500
robustness treated_positive_n >= 50
```

Support failure does not delete the state; it marks:

```text
readout_status = insufficient_support
```

### 9.3 Bad-side and utility

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_badside_utility_audit.csv
```

字段：

```text
state_id
split_bucket
cost_buffer_return
cost_tier_label
treated_n
upper_first_rate
lower_first_rate
fast_fail_rate
native_upper_first_rate
native_lower_first_rate
native_fast_fail_rate
compression_base_lower_first_rate
compression_base_fast_fail_rate
lower_first_uplift_vs_native
fast_fail_uplift_vs_native
lower_first_uplift_vs_compression_base
fast_fail_uplift_vs_compression_base
median_upper_barrier_return
median_abs_lower_barrier_return
utility_proxy_per_entry
utility_proxy_total_indexed
utility_margin_vs_native
utility_margin_vs_compression_base
utility_status
badside_status
```

Bad-side primary pass:

```text
validation lower_first_uplift_vs_compression_base <= 0.00
robustness lower_first_uplift_vs_compression_base <= 0.00
validation fast_fail_uplift_vs_compression_base <= 0.01
robustness fast_fail_uplift_vs_compression_base <= 0.01
```

Rationale: 13A3 的 composite state 继承了 compression base。Bad-side primary gate 要回答的是“repair state 是否降低或至少不放大 compression base 的左尾风险”，而不是要求它立刻优于 full-native baseline。`lower_first_uplift_vs_native` 与 `fast_fail_uplift_vs_native` 必须继续报告，但只作为 total-effect caveat，不作为 primary bad-side fail 条件。

Cost-tier pass labels:

```text
utility_pass_100bps:
  validation and robustness utility_proxy_per_entry > 0 at 100bps
  and validation and robustness utility_margin_vs_native > 0 at 100bps

utility_pass_50bps_cost_caveat:
  validation and robustness utility_proxy_per_entry > 0 at 50bps
  and validation and robustness utility_margin_vs_native > 0 at 50bps
  but utility_pass_100bps is false

utility_pass_25bps_diagnostic_only:
  validation and robustness utility_proxy_per_entry > 0 at 25bps
  but utility_pass_50bps_cost_caveat is false

utility_fail:
  none of the above
```

所有 utility margin 必须在同一 cost tier 下比较：

```text
utility_margin_vs_native(cost_tier) =
  state_utility_total_indexed(cost_tier)
  - native_baseline_utility_total_indexed(cost_tier)

utility_margin_vs_compression_base(cost_tier) =
  state_utility_total_indexed(cost_tier)
  - compression_base_utility_total_indexed(cost_tier)
```

`utility_pass_100bps` can only authorize a new train-frozen confirmatory preflight requirement. `utility_pass_50bps_cost_caveat` can only authorize 13A4 cost model calibration. 13A3 itself never authorizes 13B sequence mining.

## 10. Denominator Drift Audit

13A3 must not reuse 13A's invalid absolute board concentration rule. Board stability must be relative to the native denominator and complement.

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_denominator_drift_audit.csv
```

字段：

```text
state_id
split_bucket
drift_axis                       # board / year / regime / liquidity / compression_severity
bucket_id
treated_n
treated_share
native_share
complement_share
treated_minus_native_share
treated_minus_complement_share
drift_status
```

Primary drift thresholds:

```text
board max_abs(treated_share - native_share) <= 0.20
board max_abs(treated_share - complement_share) <= 0.25
year max_abs(treated_share - native_share) <= 0.15
regime requires at least 2 non-empty regime buckets for independent evidence;
  if only one regime bucket exists, status = regime_single_bucket_caveat, not automatic fail
liquidity median money_median_20d treated/native ratio in [0.50, 2.00]
compression_severity treated/native volatility_20d median ratio in [0.50, 1.50]
```

Drift status:

```text
primary_pass
caveat_relative_drift
fail_extreme_drift
regime_single_bucket_caveat
```

Extreme drift fail:

```text
board max_abs(treated_share - native_share) > 0.35
or year max_abs(treated_share - native_share) > 0.30
or liquidity median ratio outside [0.25, 4.00]
```

Denominator drift caveat does not automatically fail a diagnostic state, but `fail_extreme_drift` prevents confirmatory preflight authorization.

## 11. Morphology Independent Evidence

Composite states with `morphology_risk = morphology_suspect` must pass this gate. Composite states with `morphology_risk = normal` must still be audited.

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_morphology_independent_evidence_audit.csv
```

Anchors inherited from 13A:

```text
broad_reversal_baseline
broad_drawdown_baseline
volatility_20d__bottom_20pct compression_base
max_drawdown_20d
distance_to_20d_low
rebound_from_20d_low
ret_20d
```

字段：

```text
state_id
split_bucket
cost_buffer_return
cost_tier_label
morphology_risk
max_abs_rank_corr_with_anchor
top_anchor_id
state_auc
broad_morphology_baseline_auc
auc_margin_vs_broad
state_utility_total_indexed
broad_morphology_utility_total_indexed
utility_margin_vs_broad
compression_base_utility_total_indexed
utility_margin_vs_compression_base
independent_evidence_status
```

Morphology independent evidence must be computed for every cost tier in `cost_buffer_grid`. Pass rule is evaluated at the same cost tier used by the decision route:

```text
50bps cost-calibration route:
  evaluate utility margins at cost_buffer_return = 0.0050

100bps confirmatory-preflight route:
  evaluate utility margins at reference_cost_buffer_return
```

Cost-tier-specific pass rule:

```text
validation utility_margin_vs_broad > 0
robustness utility_margin_vs_broad > 0
validation utility_margin_vs_compression_base > 0
robustness utility_margin_vs_compression_base > 0
```

AUC margin alone cannot pass this gate. If utility margin is negative at the selected route's cost tier, status must be:

```text
morphology_rediscovery_without_independent_utility
```

## 12. Search / Multiplicity Accounting

13A3 is a diagnostic shortlist, but it still has researcher degrees of freedom. 必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/composite_search_multiplicity_audit.csv
```

字段：

```text
composite_state_n
cost_grid_n
effective_search_space_n
posthoc_shortlist_from_13a2_report
validation_used_for_shortlist
robustness_used_for_shortlist
state_priority_policy
cost_tier_policy
train_selection_rule
validation_used_for_final_selection
robustness_used_for_final_selection
fdr_or_deflation_method
search_accounting_status
```

Default:

```text
composite_state_n = 6
cost_grid_n = 5
effective_search_space_n = 30
posthoc_shortlist_from_13a2_report = true
validation_used_for_shortlist = true
robustness_used_for_shortlist = true
validation_used_for_final_selection = false
robustness_used_for_final_selection = false
search_accounting_status = diagnostic_posthoc_not_confirmatory
```

13A3 final selected diagnostic state must be selected using train only:

```text
eligible_train_state =
  train support pass
  and train winner_rate_diff_vs_native > 0
  and train lower_first_uplift_vs_compression_base <= 0
  and train utility_proxy_per_entry > 0 at strongest available cost tier
```

If multiple states pass train, select by §8.1 tie-break. Validation / robustness may only accept or reject the train-selected state; they may not choose a different state.

All non-selected states remain in readout tables for interpretation, but cannot drive `decision_state`. Because the shortlist itself is post-hoc diagnostic, even the train-selected state can only drive a next-requirement recommendation, not direct 13B authorization.

## 13. Decision Precedence

Decision precedence is strict:

1. Input / PIT / schema / lineage failure:

```text
13A3_blocked_input_or_lineage_failure
```

2. 13A selected compression token cannot be reproduced:

```text
13A3_blocked_upstream_13a_lineage_failure
```

3. 13A2 required threshold / candidate lineage cannot be reproduced:

```text
13A3_blocked_upstream_13a2_lineage_failure
```

4. Required composite state shortlist cannot be constructed:

```text
13A3_blocked_composite_state_reproduction_failure
```

5. Cost sensitivity shows no economic amplitude even at zero cost:

```text
13A3_stop_cost_sensitivity_no_economic_amplitude
```

6. No state passes train-only eligibility:

```text
13A3_no_train_composite_state_survives
```

7. Train-selected state fails validation / robustness readout, bad-side, or utility at all actionable cost tiers:

```text
13A3_selected_composite_state_not_supported
```

8. Train-selected state passes only 25bps diagnostic utility:

```text
13A3_diagnostic_only_cost_too_fragile
```

9. Train-selected state passes 50bps but not 100bps, with bad-side and morphology independent evidence pass:

```text
13A3_cost_caveat_repair_state_supported_requires_cost_model_calibration
next_allowed_requirement = requirement_13a4_cost_model_calibration_for_compression_repair_state.md
sequence_mining_authorized = False
effect_interpretation = total_native_effect_only
distribution_vs_state_edge_disentanglement_required = true
```

10. Train-selected state passes 100bps, bad-side, morphology independent evidence, and no extreme denominator drift:

```text
13A3_reference_cost_repair_state_diagnostic_supported_requires_confirmatory_preflight
next_allowed_requirement = requirement_13a4_compression_repair_state_confirmatory_preflight.md
sequence_mining_authorized = False
effect_interpretation = total_native_effect_only
distribution_vs_state_edge_disentanglement_required = true
```

The confirmatory preflight must rerun the selected state as a train-frozen confirmatory contract. It must explicitly separate distribution effect from conditional state edge, for example by pre-registered stratification, weighting, or matched-denominator diagnostics over board, liquidity, compression severity, calendar, and regime axes. Only that later requirement may decide whether to create 13B sequence mining.

11. Train-selected state passes utility but fails morphology independent evidence:

```text
13A3_stop_morphology_rediscovery_without_independent_utility
```

12. Train-selected state passes utility but has extreme denominator drift:

```text
13A3_stop_extreme_denominator_drift
```

No decision may be upgraded by a prettier non-selected state in validation / robustness.

## 14. Final Decision Output

必须输出：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/compression_repair_state_feasibility_decision.csv
```

字段：

```text
decision_state
next_allowed_requirement
sequence_mining_authorized
selected_state_id
selected_state_cost_status
selected_state_reference_cost_pass
selected_state_50bps_cost_pass
confirmatory_status
shortlist_source
effect_interpretation
distribution_vs_state_edge_disentanglement_required
badside_primary_baseline
input_gate_status
upstream_13a_lineage_gate_status
upstream_13a2_lineage_gate_status
cost_sensitivity_gate_status
composite_readout_gate_status
badside_gate_status
utility_gate_status
denominator_drift_gate_status
morphology_independent_evidence_gate_status
search_accounting_status
primary_failure_reason
```

Report 输出：

```text
outputs/publishable/reports/compression_repair_state_cost_and_native_feasibility_diagnostic_report.md
```

Manifest 输出：

```text
outputs/manifests/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic_manifest.json
```

## 15. Report Requirements

Report 必须用中文写明：

1. 13A3 是否验证了“13A2 主要死于 100bps cost buffer”。
2. cost=0 / 25bps / 50bps / 75bps / 100bps 下 utility 的转折点。
3. composite state 相对 full-native baseline 的 winner、lower-first、fast-fail、utility。
4. 为什么 full-native frame 与 13A2 compression-control frame 回答的是不同问题。
5. 为什么 13A3 的 positive readout 只能解释为 `total_native_effect`，不能解释为已经证明 `pure_conditional_state_edge`。
6. bad-side primary gate 为什么使用 `vs_compression_base`，并同时报告 `vs_native` caveat。
7. 是否存在 morphology rediscovery；若存在，utility margin 是否为正。
8. 若最终停止，必须区分：
   - signal amplitude too weak；
   - cost assumption too harsh but uncalibrated；
   - morphology rediscovery；
   - denominator drift；
   - bad-side still amplified。
9. 若允许下一步，必须明确下一步是 13A4 cost model calibration 还是 13A4 confirmatory preflight；并明确 confirmatory preflight 必须分离 distribution effect 与 state edge。13A3 不得直接授权 13B sequence mining。

## 16. Test Requirements

必须实现 synthetic tests，不依赖大文件：

1. `test_cost_sensitivity_changes_only_cost_term`
   同一 row-level outcome 在不同 cost tier 下，state membership、label、barrier return 不变，utility 只随 cost 项变化。

2. `test_composite_state_thresholds_loaded_from_13a2_freeze`
   Composite state 阈值必须来自 13A2 threshold freeze table；缺失阈值 fail closed。

3. `test_validation_not_used_for_state_selection`
   构造 validation 最强但 train 不合格的 state，最终不得被选中。

4. `test_full_native_frame_does_not_apply_compression_control_smd_fail`
   Composite full-native readout 不因 compression-control SMD fail 自动失败，但 denominator drift audit 必须记录漂移。

5. `test_relative_board_drift_not_absolute_60pct_rule`
   主板 share 超过 60% 不自动 fail；只有相对 native / complement drift 超阈值才 fail。

6. `test_utility_50bps_cannot_authorize_13b`
   50bps pass、100bps fail 时，next requirement 必须是 13A4 cost model calibration，sequence_mining_authorized 必须为 false。

7. `test_utility_100bps_requires_confirmatory_preflight_not_13b`
   100bps pass 时，next requirement 必须是 13A4 confirmatory preflight，sequence_mining_authorized 仍必须为 false。

8. `test_morphology_auc_margin_without_utility_margin_fails`
   AUC margin 为正但 utility margin 为负时，morphology independent evidence 必须 fail。

9. `test_morphology_margin_uses_route_cost_tier`
   50bps route 必须用 50bps morphology utility margin，100bps route 必须用 reference-cost morphology utility margin。

10. `test_badside_primary_uses_compression_base`
   lower_first / fast_fail primary bad-side gate 必须使用 `*_uplift_vs_compression_base`；`*_uplift_vs_native` 只作为 caveat 输出。

11. `test_cost_scan_self_utility_not_margin`
   §7 cost sensitivity 的 `self_utility_*` 字段不得被用于替代 §9 的 `utility_margin_vs_native` 或 `utility_margin_vs_compression_base`。

12. `test_positive_decision_requires_distribution_edge_handoff`
   50bps 或 100bps positive decision 必须输出 `effect_interpretation = total_native_effect_only` 且 `distribution_vs_state_edge_disentanglement_required = true`。

13. `test_decision_precedence`
   input failure、cost no-amplitude、bad-side fail、morphology fail、extreme drift fail 必须按 §13 顺序裁决。

## 17. Implementation Order

实现顺序必须是：

1. Read config and resolve all paths.
2. Audit inputs and upstream 13A / 13A2 / 12A7g lineage.
3. Rebuild native opportunity panel and label / barrier outcomes.
4. Load 13A compression threshold and 13A2 directional thresholds.
5. Reconstruct required composite state membership.
6. Run cost-buffer sensitivity across all 13A2 candidates and required states.
7. Run full-native composite readout.
8. Run bad-side / utility audit across cost tiers.
9. Run denominator drift audit.
10. Run morphology independent evidence audit.
11. Apply train-only selection and decision precedence.
12. Write publishable tables, report, manifest, and tests.

No step may use validation / robustness to define a threshold, choose a state, change cost tier policy, or alter decision precedence.
