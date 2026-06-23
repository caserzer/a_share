# 需求：12A7g Vol-scaled Label Panel and C0 Separability Triage

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
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、regime bucket PIT 可证明性失败、entry executability 不可证明、label horizon completeness 不可证明、feature availability 不可证明时 fail closed。
6. 不得从报告文本或聚合表反推出事件、标签、特征、score、逐行 path 结果或 split 边界。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7g
run_id = 12A7g_vol_scaled_label_panel_c0_separability_triage
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7g_vol_scaled_label_panel_c0_separability_triage.py
expected_config = configs/config_12a7g_vol_scaled_label_panel_c0_separability_triage.yaml
expected_test_file = tests/test_12a7g_vol_scaled_label_panel_c0_separability_triage.py
discussion_source = discussion2.md
research_plan_source = research_plan_3_winner_label_form_and_decoupled_selector.md
upstream_requirement_a = requirement_12a7f_c0_winner_baserate_enrichment_control_diagnostic.md
upstream_requirement_b = requirement_12a7e_defense_participation_frontier.md
upstream_requirement_c = requirement_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.md
```

本需求落地 `discussion2.md` 第 15 节的最低成本验证序列。它不是 event-family 重做，也不是 selector 训练，而是一个 triage gate：

```text
先定义 event-agnostic 的 vol-scaled winner label panel；
再把同一 label panel 贴到现有 C0 entry / survivor / deployable continuation 分母；
最后用 train-frozen separability + recall-accounted utility proxy 判断：
  A. research_plan_3 的 C0 + label 修正路线是否还值得继续；
  B. 是否需要付出更高成本启动 full-universe event-family cartography；
  C. 或者 winner-selection 路线本身应降级为 defense overlay + rule-based participation。
```

## 2. 核心问题

本需求回答五个问题，对应 discussion2 的 Step 1-5：

```text
Q1. 在全 PIT executable universe 上，是否能构造 PIT-safe 的 vol-scaled winner label panel，
    并得到不同 label 的 base-rate / horizon-completeness / regime drift 读数？

Q2. 不重做 event family 时，把新 label panel 贴到现有 C0 entry、post-hoc survivor、
    deployable chained continuation 三个分母后，右尾 winner 是否单特征可分？

Q3. fast-fail defense 对新 label 的 continuation recall 成本是多少？
    survivor-conditional rate 提升是否只是 precision 换 recall？

Q4. 在 C0 不可分时，全 PIT universe 的 primitive feature 是否显示更强的 label separability，
    足以支持启动 event-family cartography？

Q5. 基于 train-frozen label / feature / orientation，robustness readout 是否支持：
    继续 C0 label-revision 路线、启动 full-universe event mining、或停止 winner-selection？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. 背景与核心修正

12A7f 的关键事实：

```text
C0 direct-entry +20%/20d robustness:
  C0 winner rate      = 0.1552
  control winner rate = 0.1236
  diff                = +0.0316, CI95 [+0.0109, +0.0522]

C0 fast-fail robustness:
  C0 fast-fail        = 0.3059
  control fast-fail   = 0.2466
  diff                = +0.0592
```

这说明 C0 有弱右尾富集，但不是干净的 winner event。12A7f survivor-conditional 的 `+20%/20d` diff 提升到 `+5.67pp`，但这不是免费净化；它是 precision / recall tradeoff，必须把被 fast-fail defense 过滤掉的真实 continuation positive 记账。

本需求的核心修正：

```text
1. label 定义先 event-agnostic：
   vol-scaled label panel 在全 PIT executable universe 上重算，
   不把 C0 或 survivor selection 烤进 label 定义。

2. label 选择 train-frozen：
   可以全量计算 label panel，但 primary label / k / horizon / feature orientation
   只能由 train split 预注册规则选择；validation 和 robustness 只读。

3. denominator 分层：
   post-hoc no-fast-fail survivor 只能是 diagnostic；
   可部署 readout 必须使用 entry-time t0 或逐行 `stage_2_reference_pos` continuation decision point。

4. recall 成本必须同锚点记账：
   defense / survivor 对 entry opportunity 的误杀，只能用同一个 entry-anchored label 计算；
   post-survivor continuation label 不能与 direct-entry label 混作 recall 分子分母。

5. base-rate 不是 go/no-go：
   go/no-go 由 separability + recall-accounted utility proxy 决定，
   不由 base-rate enrichment 单独决定。

6. full-universe base rate 不能替代 matched control：
   全 PIT label panel 给干净 base rate；
   任何 event-family enrichment 比较仍必须 matched control。
```

## 4. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、threshold grid、canonicalization priority、cooldown 或 risk_on scope；
- 不运行 full event-family grid search，不做 new CUSUM / vol event mining；
- 不训练高容量模型，不做 probability calibration、Platt、isotonic、budget calibration；
- 不做 policy replay、仓位、交易成本、slippage、资金曲线或可交易 alpha 声明；
- 不把全样本最优 label / k / horizon 回头解释为发现过程；
- 不把 full-universe label base rate 当作 event matched-control enrichment；
- 不把 post-hoc ground-truth survivor readout 当作可部署策略；
- 不用 validation 或 robustness 回头选择 label、feature、orientation、denominator、utility weights 或 decision threshold；
- 不把 `12A7g_full_universe_more_separable_start_event_cartography` 解释成 event-family 已支持；它只授权下一份 event cartography requirement。

## 5. 必需输入

### 5.1 全 PIT executable universe 与行情

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

`regime_daily_series_audit.csv` 必须提供：

```text
date
daily_regime_bucket
daily_regime_conflict_n
daily_regime_conflict_flag
```

Regime 映射规则：

```text
regime_join_key = reference_date
market_regime_bucket = daily_regime_bucket
required_status =
  every retained primary-scope reference_date has exactly one regime row
  and daily_regime_conflict_flag == false
  and daily_regime_conflict_n == 0
```

Regime calendar 允许因前后窗口计算约束而覆盖范围短于 PIT universe。若某个 `reference_date` 缺 regime row，不得从 event key、calendar month、报告文本或 C0 聚合表反推 regime，也不得 fail open；runner 必须逐行标记：

```text
regime_calendar_available = false
regime_missing_date_bypassed = true
market_regime_bucket = missing_regime_calendar
```

这些行必须从 `primary_scope`、train label selection、validation / robustness readout、C0-comparable active-band full-universe denominator、full-vs-C0 deltas 和所有 decision gates 中剔除，只能进入 audit 计数。仅因为缺 regime row 而剔除数据时：

```text
global_regime_calendar_status = pass_with_missing_date_bypass
global_regime_calendar_reason = missing_regime_date_bypassed
```

若所有可用 regime row 均被剔除后 primary retained universe 为空，必须 fail closed。若同 date 多 regime、`daily_regime_conflict_flag == true` 或 `daily_regime_conflict_n > 0`，仍必须 `global_regime_calendar_status = fail` 并 fail closed。

全 PIT universe label panel 的 primary scope：

```text
record_unit = instrument x reference_date
reference_date = PIT executable daily row date
reference_pos = qfq daily position for reference_date
entry_date = next executable open after reference_date
entry_pos = qfq daily position for entry_date
entry_price = qfq open at entry_pos
primary_scope =
  regime_calendar_available == true
  and market_regime_bucket == risk_on
  and board_bucket in supported boards
  and next-open entry executable
  and required pre-vol lookback complete
```

All-regime label panel 可作为 secondary diagnostic，但 primary comparison 必须保持和 C0 risk_on 口径一致。

Full-universe primitive features 必须从 PIT universe row 和 qfq daily bar 逐行重建，不能复用 C0 event feature matrix，也不能把 C0 membership / event family 信息带入 full universe。qfq daily bar 必须按 `date` 稳定排序并建立 `date_pos`，每个 `(instrument, reference_date)` 必须能唯一映射到 qfq `reference_pos`；若 qfq row 缺失、重复或 OHLC 非有限值，该行 feature / label 状态为 not evaluable。

Full-universe primitive formula freeze：

```text
price_reference = qfq close at reference_pos
ret_Nd = close[reference_pos] / close[reference_pos - N] - 1
daily_return = close[t] / close[t - 1] - 1
volatility_Nd = std(daily_return over reference_pos - N + 1 ... reference_pos, ddof=0)
distance_to_Nd_high = close[reference_pos] / max(high over last N sessions including reference_pos) - 1
distance_to_Nd_low = close[reference_pos] / min(low over last N sessions including reference_pos) - 1
trend_ma_5_20_spread = mean(close last 5 sessions) / mean(close last 20 sessions) - 1
trend_ma_20_60_spread = mean(close last 20 sessions) / mean(close last 60 sessions) - 1
max_drawdown_Nd = min(close[t] / max(close up to t within last N sessions) - 1)
turnover_zscore_20d = (turnover_rate[reference_pos] - mean(turnover_rate last 20 sessions)) / std(turnover_rate last 20 sessions, ddof=0)
turnover_rate_median_20d = median(turnover_rate last 20 sessions)
money_median_20d = median(money last 20 sessions)
trading_continuity_20d = qfq bar count in last 20 exchange sessions / 20
recent_range_activity_20d = max(high last 20 sessions) / min(low last 20 sessions) - 1
intraday_range_mean_20d = mean(high / low - 1 over last 20 sessions)
board_return_20d = equal-weight mean ret_20d by board_bucket x reference_date over PIT executable rows with finite ret_20d
stock_vs_board_20d = ret_20d - board_return_20d
```

`required pre-vol lookback complete` means `volatility_20d` and `volatility_60d` both have complete close-return lookbacks, qfq OHLC is finite through `reference_pos`, and `reference_pos + max(horizon_sessions)` can be checked for horizon completeness without inferring label values. Any deviation must be recorded in `full_universe_primitive_feature_audit.csv`.

Full-universe raw pool 不能直接和 C0 denominator 比 separability。C0 已经过 state-change / risk / evaluability 过滤，raw full universe 里会包含大量明显 inactive / low-liquidity / no-motion hard negatives，直接比较会把 `full_vs_c0_auc_delta` 灌水。用于 §12 / §13.4 cartography gate 的 primary full-universe denominator 必须先构造 C0-comparable active opportunity band：

```text
active_band_id = full_pit_c0_comparable_active_band
active_band_threshold_source = train split C0 entry denominator
threshold_freeze_rule = compute on train only, apply unchanged to validation / robustness
required_band_dimensions =
  market_regime_bucket
  board_bucket
  entry_executability
  liquidity_or_turnover_activity
  recent_trading_continuity
  pre_event_volatility_range
  recent_motion_or_range_activity
```

推荐初始 band 口径：

```text
market_regime_bucket == risk_on
board_bucket in supported boards
next-open entry executable
required pre-vol lookback complete
liquidity_or_turnover_activity = turnover_rate_median_20d, fallback money_median_20d
recent_trading_continuity = trading_continuity_20d
pre_event_volatility_range = volatility_20d
recent_motion_or_range_activity = recent_range_activity_20d, fallback intraday_range_mean_20d

liquidity_or_turnover_activity >= train_c0_entry_p05
recent_trading_continuity >= train_c0_entry_p05
pre_event_volatility_range between train_c0_entry_p01 and train_c0_entry_p99
recent_motion_or_range_activity >= train_c0_entry_p05
```

Active-band threshold source rows are:

```text
source = c0_entry_t0 train split rows
reference_date = event_t0_date
feature_source =
  recompute the same qfq primitive formulas at event_t0_date close
  and reconcile volatility_20d / volatility_60d against two_stage_feature_matrix
threshold_quantile_source =
  train_c0_entry_p05 for lower activity / continuity / motion thresholds
  train_c0_entry_p01 and train_c0_entry_p99 for volatility range
```

If recomputed C0 primitive values and `two_stage_feature_matrix` values disagree for `volatility_20d` or `volatility_60d` beyond `1e-12` absolute tolerance on any row with finite values, `full_universe_active_band_audit.csv` must record `fallback_status = volatility_reconciliation_fail` and `active_band_cartography_gate_eligible = false`.

若某个维度没有 PIT-safe primitive，runner 必须在 audit 中记录 fallback；若无法构造至少 liquidity/activity + volatility + trading-continuity 三类约束，`full_pit_risk_on_universe_raw_diagnostic` 只能作为 diagnostic，不得触发 `12A7g_full_universe_more_separable_start_event_cartography`。

Runner 必须输出 `full_universe_active_band_audit.csv`，至少包含：

```text
band_id
threshold_source_split
dimension
feature_id
threshold_low
threshold_high
threshold_quantile_source
pit_status
raw_full_universe_row_n
active_band_row_n
active_band_share
c0_entry_row_n
c0_coverage_rate
fallback_status
active_band_cartography_gate_eligible
```

Active band 必须按 split 报告覆盖稳定性。若 robustness / validation 的 C0 coverage 明显偏离 train，full-universe active-band 比较降级为 diagnostic，不得触发 cartography gate：

```text
split
c0_coverage_rate_by_split
active_band_share_by_split
c0_coverage_rate_delta_vs_train
active_band_share_delta_vs_train
active_band_coverage_stability_status
```

Full PIT universe split assignment:

```text
split_source = outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
split_assignment_rule = assign by reference_date using frozen split boundaries
boundary_policy = reference_date, not label horizon end date
```

`split_time_boundary_audit.csv` is expected to contain train / evaluation boundary rows:

```text
train_end = validation.train_max_event_t0_date
validation_start = validation.eval_min_event_t0_date
robustness_start = robustness.eval_min_event_t0_date

assigned split:
  train if reference_date <= train_end
  validation if validation_start <= reference_date < robustness_start
  robustness if reference_date >= robustness_start
  boundary_gap_excluded otherwise
```

`boundary_gap_excluded` rows must be counted in `full_universe_split_boundary_audit.csv` and excluded from train selection, validation readout, robustness gates, and full-vs-C0 deltas. They do not by themselves fail the run unless their row count is nonzero on an exchange session with a missing upstream boundary explanation.

Runner 必须输出 `full_universe_split_boundary_audit.csv`，至少包含：

```text
split
start_date
end_date
reference_row_n
entry_executable_row_n
horizon_complete_row_n_by_horizon
boundary_assignment_status
```

Full PIT universe 的 `instrument x reference_date` 日频 label 会产生严重 overlapping horizon correlation。所有 full-universe primitive separability 的 primary CI 必须使用 block 方法：

```text
primary_ci_method = instrument_month_block_bootstrap
block_key = instrument x calendar_month(reference_date)
secondary_ci_method = optional purged_subsample_sensitivity
purge_gap_sessions >= max(horizon_sessions)
```

必须输出 `label_overlap_effective_n_audit.csv`：

```text
denominator_id
label_id
horizon_sessions
raw_row_n
instrument_n
instrument_month_block_n
mean_rows_per_block
p95_rows_per_block
effective_block_n
overlap_control_status
```

### 5.2 C0 event 与 path artifacts

必需输入：

```text
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_universe.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_targets.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_dictionary.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_pit_audit.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_feature_matrix.parquet
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

`two_stage_event_universe.csv.gz` 必须提供：

```text
meta_event_id
instrument
entry_date
entry_pos
entry_price
path_key
split
board_bucket
calendar_month
calendar_year
market_regime_bucket
source_arm_is_c0
stage_1_evaluable
stage_1_fast_fail_target
no_fast_fail_L10_H20
stage_2_decision_pos
stage_2_reference_pos
stage_2_reference_price
stage_2_path_evaluable
stage_2_entry_blocked
stage_2_horizon_complete_20d
stage_2_horizon_complete_40d
```

### 5.3 12A7b / 12A7e defense artifacts

必需输入：

```text
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_train_selection.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_operating_point_readout.csv
outputs/publishable/tables/12A7b_direction_c_simple_backbone_operating_rule_validation/direction_c_decision.csv
outputs/publishable/tables/12A7e_defense_participation_frontier/defense_participation_decision.csv
outputs/publishable/tables/12A7e_defense_participation_frontier/stage1_frontier_readout.csv
outputs/publishable/tables/12A7e_defense_participation_frontier/defense_participation_frontier.csv
outputs/local_cache/12A7b_direction_c_simple_backbone_operating_rule_validation/simple_backbone_score_matrix.parquet
outputs/manifests/12A7b_direction_c_simple_backbone_operating_rule_validation_manifest.json
outputs/manifests/12A7e_defense_participation_frontier_manifest.json
```

Required upstream state:

```text
12A7b decision_state = 12A7b_simple_backbone_supported_low_capacity_not_supported
12A7b selected_primary_simple_backbone_tuple = volatility_20d
12A7b selected_primary_X = 0.30
12A7e decision_state = 12A7e_x030_defense_optimal_for_downside_not_winner
```

若上述状态不成立，本需求必须 fail closed 或输出：

```text
decision_state = 12A7g_blocked_input_or_lineage_failure
```

12A7g 必须 row-level 重建 12A7b / 12A7e 的 X=0.30 stage-1 keep，不能从 aggregate selected_n 反推。重建规则：

```text
stage1_anchor_source = simple_backbone_score_matrix.parquet
required_columns =
  meta_event_id
  volatility_20d
  volatility_20d__rank_percentile
  volatility_20d__rank_status

stage1_anchor_feature = volatility_20d
stage1_anchor_orientation = asc
stage1_anchor_X = 0.30
stage1_anchor_selected_flag =
  volatility_20d__rank_status == rank_evaluable
  and volatility_20d__rank_percentile <= 0.30
```

The rank source must be auditable as:

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
stage_1_global_min_history_n = 500
stage_1_board_min_history_n = 150
percentile_formula =
  (count(history_value < current_value) + 0.5 * count(history_value == current_value)) / history_n
history_window =
  prior rows with event_t0_pos < current event_t0_pos
  and event_t0_pos >= current event_t0_pos - 504
history_scope =
  board history if board history_n >= 150
  else global history if global history_n >= 500
  else rank_not_evaluable
```

Runner 必须输出 `stage1_anchor_x030_reconstruction_audit.csv`，至少包含：

```text
split
recomputed_selected_n
upstream_selected_n
recomputed_rank_evaluable_n
upstream_rank_evaluable_n
recomputed_selected_budget_rank_evaluable
upstream_selected_budget_rank_evaluable
selected_n_match_status
rank_evaluable_match_status
budget_match_status
stage1_anchor_reconstruction_status
```

`upstream_selected_n / upstream_rank_evaluable_n / upstream_selected_budget_rank_evaluable` 来自 12A7e `stage1_frontier_readout.csv` 的 `stage1_X = 0.30` 行。任一 split 的 selected_n 或 rank_evaluable_n 不一致，或 budget 差异超过 `1e-12`，必须 fail closed。`c0_deployable_stage2_reference` 只能使用通过该重建的 `stage1_anchor_selected_flag`。

### 5.4 12A7f enrichment artifacts

必需输入：

```text
outputs/publishable/tables/12A7f_c0_winner_baserate_enrichment_control_diagnostic/c0_winner_enrichment_decision.csv
outputs/publishable/tables/12A7f_c0_winner_baserate_enrichment_control_diagnostic/c0_vs_control_winner_baserate_readout.csv
outputs/publishable/tables/12A7f_c0_winner_baserate_enrichment_control_diagnostic/winner_label_source_audit.csv
outputs/publishable/tables/12A7f_c0_winner_baserate_enrichment_control_diagnostic/enrichment_stability_slice_audit.csv
outputs/manifests/12A7f_c0_winner_baserate_enrichment_control_diagnostic_manifest.json
```

12A7f 只作 upstream context 和 anchor reconciliation；12A7g 必须重新计算 vol-scaled labels，不得从 12A7f 的 fixed-barrier aggregate tables 反推逐行 label。

## 6. Vol-scaled label panel

### 6.1 Label reference point

全 PIT universe label：

```text
feature_reference_pos = qfq close position at reference_date
label_reference_pos = entry_pos
entry_pos = next executable open position after reference_date
label_reference_price = entry_price = qfq open at entry_pos
```

C0 entry-anchored label：

```text
reference_pos = entry_pos
entry_price = entry_price
allowed_usage =
  c0_entry_t0 separability readout
  recall-cost accounting for defense / survivor filters
```

C0 post-survivor continuation label：

```text
reference_pos = stage_2_reference_pos
reference_price = stage_2_reference_price
allowed_usage =
  c0_deployable_stage2_reference continuation separability readout only
```

同一个 selected label 必须能生成两个 reference view：

```text
entry_anchor_view:
  reference_pos = original entry_pos
  reference_price = original entry_price
  used_for = direct-entry readout and retained-positive recall accounting

continuation_view:
  reference_pos = stage_2_reference_pos
  reference_price = stage_2_reference_price
  used_for = survivor-stage continuation readout only
```

不得混用 entry-anchored label 与 post-survivor continuation label。所有 readout 必须标注：

```text
label_reference_view in {
  full_universe_next_open,
  c0_entry_anchor,
  c0_post_survivor_continuation
}
```

### 6.2 Vol reference

Primary vol reference：

```text
vol_reference_id in {
  volatility_20d,
  volatility_60d
}
vol_reference_availability = reference_date close or earlier
vol_reference_unit in {
  daily_return_std,
  horizon_return_vol,
  other_audited_unit
}
vol_horizon_scale =
  if daily_return_std: vol_reference * sqrt(horizon_sessions)
  if horizon_return_vol: vol_reference
  if other_audited_unit: audited_transform_recorded_in_label_formula_audit
```

若现有 `volatility_20d / volatility_60d` 的单位不是 daily return volatility，runner 必须在 `label_formula_audit.csv` 中记录实际单位和缩放公式；无法证明单位时 fail closed。

### 6.3 Label grid

Primary vol-scaled grid：

```text
horizon_sessions in {20, 40, 60}
k_up in {1.0, 1.5, 2.0, 2.5}
k_dn in {0.75, 1.0, 1.25}
upper_barrier = k_up * vol_horizon_scale
lower_barrier = -1 * k_dn * vol_horizon_scale
same_bar_priority = lower_first
```

Anchor fixed labels：

```text
fixed_U15_L10_H20
fixed_U20_L10_H20
fixed_U20_L10_H40
```

Barrier traversal is frozen for both vol-scaled and fixed anchor labels:

```text
horizon_complete =
  reference_pos is finite
  and reference_pos + horizon_sessions < instrument_qfq_row_n

path_window =
  qfq rows from reference_pos through reference_pos + horizon_sessions, inclusive

upper_touch at offset s =
  high[reference_pos + s] / reference_price - 1 >= upper_barrier

lower_touch at offset s =
  low[reference_pos + s] / reference_price - 1 <= lower_barrier

time_to_upper = first offset s with upper_touch, else NA
time_to_lower = first offset s with lower_touch, else NA
same_bar_conflict =
  time_to_upper is finite
  and time_to_lower is finite
  and time_to_upper == time_to_lower

upper_first =
  horizon_complete
  and time_to_upper is finite
  and (time_to_lower is NA or time_to_upper < time_to_lower)

lower_first =
  horizon_complete
  and time_to_lower is finite
  and (time_to_upper is NA or time_to_lower <= time_to_upper)

neutral =
  horizon_complete
  and time_to_upper is NA
  and time_to_lower is NA

censored = not horizon_complete
```

This implements `same_bar_priority = lower_first`: same-offset high/low touches are `same_bar_conflict = true`, `lower_first = true`, and `upper_first = false`. Offset 0 is included because the reference price is the executable open for entry / continuation views and the same session's high / low is not known at decision time but is the realized path being labeled.

Fixed anchor labels use the same traversal with:

```text
fixed_U15_L10_H20: upper_barrier = 0.15, lower_barrier = -0.10, horizon_sessions = 20
fixed_U20_L10_H20: upper_barrier = 0.20, lower_barrier = -0.10, horizon_sessions = 20
fixed_U20_L10_H40: upper_barrier = 0.20, lower_barrier = -0.10, horizon_sessions = 40
```

所有 label 都必须输出以下状态：

```text
upper_first
lower_first
neutral
censored
same_bar_conflict
entry_blocked
horizon_complete
```

Primary positive definition：

```text
winner_positive = upper_first == true
```

Secondary diagnostics：

```text
upper_touch_anytime
lower_touch_anytime
max_high_return
min_low_return
time_to_upper
time_to_lower
pre_success_MAE_for_upper_touch
```

`pre_success_MAE_for_upper_touch` is `min(low / reference_price - 1)` over offsets `0 ... time_to_upper`, inclusive, when `time_to_upper` is finite; otherwise it is NA. `max_high_return` and `min_low_return` use the complete `path_window` and are NA when `horizon_complete = false`.

## 7. Denominator contracts

12A7g 必须同时输出三个 C0 denominator readouts，且不得混淆解释等级。

### 7.1 C0 entry denominator

```text
denominator_id = c0_entry_t0
scope =
  source_arm_is_c0 == true
  and market_regime_bucket == risk_on
  and stage_1_evaluable == true
  and entry executable
decision_time = entry_pos / t0 next open
feature_set_allowed = t0 PIT features only
interpretation = deployable entry-time diagnostic
```

### 7.2 C0 post-hoc ground-truth survivor denominator

```text
denominator_id = c0_posthoc_no_fast_fail_survivor
scope =
  c0_entry_t0
  and no_fast_fail_L10_H20 == true
  and path evaluable
decision_time = post-hoc known survivor
feature_set_allowed = diagnostic only
interpretation = post_hoc_diagnostic_only
```

该分母不能设置 deployable support decision。它只能回答：

```text
如果事后知道已经活过 fast-fail，label 是否更可分？
```

### 7.3 C0 deployable continuation denominator

```text
denominator_id = c0_deployable_stage2_reference
scope =
  c0_entry_t0
  and train-frozen stage-1 simple backbone keep under volatility_20d asc X=0.30
  and no_fast_fail_L10_H20 == true
  and stage_2_path_evaluable == true
decision_time = stage_2_reference_pos
feature_set_allowed =
  t0 PIT features
  plus realized_path features with row-level availability_time <= close at stage_2_reference_pos
interpretation = deployable stage2_reference continuation diagnostic
```

该分母是 12A7g 中唯一允许支持 `continue_C0_label_revision` 的 survivor-stage denominator。若它不可分，而 post-hoc survivor 可分，结论必须降级为 diagnostic-only。

### 7.4 Full PIT universe denominator

```text
denominator_id = full_pit_risk_on_universe_raw_diagnostic
scope = 5.1 primary_scope
decision_time = reference_date close / next executable open
feature_set_allowed = event-agnostic PIT primitives only
interpretation = raw full-universe diagnostic only, not cartography gate

denominator_id = full_pit_c0_comparable_active_band
scope =
  5.1 primary_scope
  and full_universe_active_band_audit.active_band_cartography_gate_eligible == true
decision_time = reference_date close / next executable open
feature_set_allowed = event-agnostic PIT primitives only
interpretation = primary full-universe comparator for event-mining triage
```

只有 `full_pit_c0_comparable_active_band` 可以用于 §12 / §13.4 的 `full_vs_c0_*` delta gate。`full_pit_risk_on_universe_raw_diagnostic` 只能报告背景读数，不能启动 event cartography。Full universe readout 只用于判断是否存在比 C0 更有希望的 primitive separability；它不能直接支持任何具体 event family。

## 8. Feature contracts

### 8.1 C0 t0 PIT feature set

来自 `two_stage_feature_dictionary.csv`：

```text
allowed_for_stage_1 = true
pit_status = pass
availability_time <= event_t0_close
```

Population/audit columns such as `source_arm_is_c0`、`source_arm_is_r_core` 不得作为 separability feature。

### 8.2 C0 stage-2 feature set

来自 `two_stage_feature_dictionary.csv`：

```text
allowed_for_stage_2 = true
pit_status = pass
row_level_availability_assertion:
  feature.availability_time <= close at stage_2_reference_pos
```

必须拆分输出：

```text
feature_time_bucket = t0_pit
feature_time_bucket = realized_0_20d
```

若 `stage_2_reference_pos` 不等于 `entry_pos + 20`，不得用固定 +20 偏移替代逐行 availability assertion。若 realized-path feature 在 `c0_entry_t0` 或 `c0_posthoc_no_fast_fail_survivor` 的 entry-time readout 中出现，或任一 stage-2 row 的 `feature.availability_time > stage_2_reference_pos close`，必须 fail closed。

Realized-path feature availability must be audited row by row:

```text
realized_0_20d feature source =
  two_stage_event_universe.csv.gz columns with prefix realized_
  or stage2_path_cache.parquet columns with prefix realized_

realized_0_20d availability_time =
  close at stage_2_reference_pos - 1 if feature was computed through day-20 close
  else close at stage_2_reference_pos when the feature explicitly uses stage_2_reference_pos row

stage2_feature_availability_status =
  pass only if availability_time <= close at stage_2_reference_pos for every selected stage-2 row
```

Runner must record the resolved source and availability convention in `denominator_contract_audit.csv`. `c0_entry_t0` and `c0_posthoc_no_fast_fail_survivor` may report realized-path features only as excluded candidates with `exclusion_reason = realized_path_not_entry_time_pit`; they cannot enter rank, AUC, rank-IC, decile lift, utility support, or decision flags.

### 8.3 Full universe primitive feature set

Full universe primitive scan 只允许 event-agnostic PIT primitives：

```text
ret_5d / ret_10d / ret_20d / ret_60d
volatility_20d / volatility_60d
distance_to_20d_high / low
distance_to_60d_high / low
trend_ma_5_20_spread
trend_ma_20_60_spread
max_drawdown_20d / 60d
turnover_zscore_20d
board_relative_return / stock_vs_board_return primitives if PIT-safe
```

Full universe primitive scan 不得使用 C0 family trigger flags、future returns、label-derived fields、episode identifiers 或 post-entry realized-path features。

若 primary label 使用 `vol_reference_id = volatility_20d`，则 `volatility_20d` 及其同源直接变换不得作为该 label 的 primary separability feature；`volatility_60d` 同理。此类 readout 只能标为 `construction_coupled_diagnostic_only`。若要把同源 volatility feature 放回 primary，必须先输出 orthogonalized feature 和 `label_feature_construction_coupling_audit.csv`，证明它不是 barrier 尺度定义的机械反射。

`same_bar_priority = lower_first` 也可能和 volatility 产生机械耦合：低 vol 名义 barrier 更窄，same-bar conflict 更容易出现，进而被系统性判为 lower-first。`label_feature_construction_coupling_audit.csv` 必须按 vol bucket 输出 same-bar conflict 分层：

```text
label_id
vol_reference_id
vol_bucket
denominator_id
same_bar_conflict_rate
lower_first_rate
upper_first_rate
winner_positive_rate
construction_coupled_status
```

## 9. Train-frozen selection discipline

12A7g 可以计算完整 label panel 和完整 readout matrix，但选择必须 train-only。

### 9.1 Label selection

Train split 选择 primary label，规则必须预注册在 config 中：

```text
eligible label if:
  train horizon_complete_rate >= 0.98
  train winner_positive_n >= min_train_positive_n
  train winner_base_rate between min_label_base_rate and max_label_base_rate
  train same_bar_conflict_rate <= max_same_bar_conflict_rate
  train label_base_rate_dispersion <= max_label_base_rate_dispersion

selection order:
  1. prefer best_vol_scaled_label over best_fixed_anchor_label if vol_scaled_not_worse_than_fixed == true
  2. higher train label_stability_score
  3. lower regime/year base-rate dispersion
  4. lower train same_bar_conflict_rate
  5. base-rate closer to target_label_base_rate
  6. shorter horizon
  7. deterministic label_id lexical tie-break
```

Label stability metrics are train-only and computed on `full_pit_c0_comparable_active_band` when eligible; if active band is not eligible, compute on `full_pit_risk_on_universe_raw_diagnostic` and mark `label_selection_active_band_status = diagnostic_source`. They must not use any C0 separability, survivor readout, full-universe feature separability, or utility proxy.

```text
eligible stability slices =
  calendar_year
  board_bucket
  market_regime_bucket

slice included if:
  slice_denominator_n >= min_label_stability_slice_n
  and slice_positive_n >= min_label_stability_slice_positive_n

label_base_rate_dispersion =
  max(abs(slice_winner_base_rate - train_winner_base_rate)) over included slices

label_stability_score =
  train_horizon_complete_rate
  - train_same_bar_conflict_rate
  - label_base_rate_dispersion
  - abs(train_winner_base_rate - target_label_base_rate)

vol_scaled_not_worse_than_fixed =
  best_vol_scaled_label.label_stability_score >= best_fixed_anchor_label.label_stability_score - max_label_stability_score_tolerance
  and best_vol_scaled_label.label_base_rate_dispersion <= best_fixed_anchor_label.label_base_rate_dispersion + max_label_base_rate_dispersion_tolerance
  and best_vol_scaled_label.same_bar_conflict_rate <= best_fixed_anchor_label.same_bar_conflict_rate + max_same_bar_conflict_rate_tolerance
```

Label selection 不得使用 C0-entry separability、post-survivor separability、full-universe primitive separability 或 utility proxy。Validation 和 robustness 不能改变 selected label。

### 9.2 Feature / orientation selection

For each denominator and selected label:

```text
train:
  select feature_id and orientation by separability_score

validation:
  readout-only stress split

robustness:
  final readout-only gate
```

Feature orientation and score are deterministic:

```text
auc_desc = AUC(feature_value, winner_positive)
auc_asc = 1 - auc_desc
rank_ic_desc = Spearman(feature_value, winner_positive)
rank_ic_asc = -1 * rank_ic_desc

top_decile for desc = highest 10% finite feature values within split / denominator
top_decile for asc = lowest 10% finite feature values within split / denominator

top_decile_lift_abs = top_decile_winner_rate - base_winner_rate
top_decile_lift_ratio = top_decile_winner_rate / base_winner_rate
top_decile_lift_abs_desc = desc_top_decile_winner_rate - base_winner_rate
top_decile_lift_abs_asc = asc_top_decile_winner_rate - base_winner_rate

orientation chosen on train =
  desc if separability_score_desc > separability_score_asc
  asc if separability_score_asc > separability_score_desc
  lexical tie-break asc

separability_score_desc =
  auc_desc
  + 0.50 * max(0, top_decile_lift_abs_desc)
  + 0.10 * max(0, rank_ic_desc)

separability_score_asc =
  auc_asc
  + 0.50 * max(0, top_decile_lift_abs_asc)
  + 0.10 * max(0, rank_ic_asc)

separability_score_orientation =
  oriented_auc
  + 0.50 * max(0, top_decile_lift_abs)
  + 0.10 * max(0, oriented_rank_ic)
```

Feature tie-break order after `separability_score_orientation`:

```text
1. raw train separability pass before non-pass
2. higher oriented_auc
3. higher top_decile_lift_abs
4. higher top_decile_positive_n
5. lower rank_not_evaluable_rate
6. feature_time_bucket order t0_pit before realized_0_20d
7. feature_id lexical order
8. orientation lexical order asc before desc
```

Feature selection must write:

```text
selected_feature_id
selected_orientation
feature_time_bucket
label_reference_view
construction_coupled_status
train_auc
train_rank_ic
train_top_decile_lift_abs
train_top_decile_lift_ratio
selection_rank
tie_break_reason
```

### 9.3 Pre-registered config defaults

以下常数直接影响 go/no-go，必须写入 config；runner 不得在读完 validation / robustness 后修改。若 config 缺失，使用以下默认值并在 `pre_registered_threshold_audit.csv` 记录：

```text
# label eligibility
min_label_base_rate = 0.05
max_label_base_rate = 0.35
target_label_base_rate = 0.15
min_train_positive_n = 200
max_same_bar_conflict_rate = 0.03
max_label_base_rate_dispersion = 0.10
min_label_stability_slice_n = 200
min_label_stability_slice_positive_n = 20
max_label_stability_score_tolerance = 0.02
max_label_base_rate_dispersion_tolerance = 0.02
max_same_bar_conflict_rate_tolerance = 0.005

# separability pass
min_auc = 0.55
min_top_decile_lift_abs = 0.03
min_top_decile_lift_ratio = 1.20
min_top_decile_positive_n = 30
max_rank_not_evaluable_rate = 0.05
search_adjustment_method = bonferroni_bootstrap_ci
search_adjustment_alpha = 0.05

# recall / utility gate
cost_buffer_bps = 100
min_recall_vs_entry = 0.70
max_recall_adjusted_utility_deterioration = 0.10
recall_floor_feasibility_warning_margin = 0.05

# full-universe vs C0 gate
min_full_universe_auc_delta = 0.02
min_full_universe_effective_block_n = 200
min_full_vs_c0_top_decile_lift_delta_abs = 0.02
max_active_band_c0_coverage_rate_split_delta = 0.15
max_active_band_share_split_delta = 0.20
min_full_universe_stability_slice_n = 500
min_full_universe_stability_slice_positive_n = 30
max_full_vs_c0_stability_dispersion_delta = 0.02

# C0 denominator diversity
min_c0_instrument_n = 30
min_c0_instrument_month_block_n = 30
```

这些值是 pre-registered default，不是结论阈值调参空间。任何 override 必须在 run start 前写入 config，并输出 override reason；不得基于本次结果调整。

## 10. Separability metrics

For every denominator x label x feature:

```text
auc
rank_ic
rank_ic_ci95_low
rank_ic_ci95_high
top_decile_winner_rate
base_winner_rate
top_decile_lift_abs
top_decile_lift_ratio
top_decile_lift_ci95_low
top_decile_lift_ci95_high
bottom_decile_winner_rate
top_minus_bottom_spread
positive_n
denominator_n
horizon_complete_n
horizon_complete_rate
censored_n
censored_rate
rank_evaluable_n
rank_not_evaluable_rate
instrument_n
instrument_month_block_n
effective_block_n
```

Primary separability 必须只在 `horizon_complete == true` 的行上计算；`censored` 行不得进入 AUC / rank-IC / decile-lift 的分母。Robustness split 因近期端点导致的 censoring 必须通过 `horizon_complete_rate` 显式报告，不能把 calendar endpoint censoring 混入 negative label。

Primary robustness separability pass:

```text
auc >= min_auc
rank_ic same sign as train and validation
top_decile_lift_ci95_low > 0
top_decile_lift_abs >= min_top_decile_lift_abs
top_decile_lift_ratio >= min_top_decile_lift_ratio
top_decile_positive_n >= min_top_decile_positive_n
rank_not_evaluable_rate <= max_rank_not_evaluable_rate
```

C0 denominator 的 separability pass 还必须满足多样性下限：

```text
instrument_n >= min_c0_instrument_n
instrument_month_block_n >= min_c0_instrument_month_block_n
```

If multiple labels or features are evaluated, report both raw and search-adjusted status:

```text
raw_separability_status
search_adjusted_status
label_grid_size
feature_grid_size
effective_search_size
```

Search-adjusted status is fixed to `bonferroni_bootstrap_ci`:

```text
effective_search_size =
  max(1, label_grid_size * feature_grid_size * orientation_count_for_feature)

adjusted_alpha =
  search_adjustment_alpha / effective_search_size

adjusted_ci_low_quantile = adjusted_alpha / 2
adjusted_ci_high_quantile = 1 - adjusted_alpha / 2

search_adjusted_status = pass only if:
  raw_separability_status == pass
  and adjusted top_decile_lift_ci_low > 0
  and adjusted rank_ic_ci excludes 0 in the train-selected direction
```

For full-vs-C0 deltas, the same adjusted quantiles must be used for `full_vs_c0_auc_delta_ci95_low` and `full_vs_c0_top_decile_lift_delta_abs_ci95_low`; column names may keep `ci95` for compatibility, but `search_multiplicity_audit.csv` must record the adjusted quantiles actually used. Runner may additionally report unadjusted CI columns, but decision flags must use adjusted status.

## 11. Recall-accounted utility proxy

12A7g 不输出真实净值，不做交易 replay。它输出 conservative utility proxy。

For each selected label and denominator:

```text
gross_upper_component = upper_first_rate * median_upper_barrier
gross_lower_component = lower_first_rate * abs(median_lower_barrier)
neutral_component = neutral_rate * min(0, median_horizon_close_return_for_neutral)
cost_component = cost_buffer_bps / 10000
utility_proxy =
  gross_upper_component
  - gross_lower_component
  + neutral_component
  - cost_component
utility_proxy_per_20d =
  utility_proxy * (20 / horizon_sessions)
```

`neutral_component` 是保守项：neutral path 不能默认为 0 收益；若 neutral close-return 的中位数为正，primary proxy 仍按 0 处理。所有 upper / lower / neutral 统计必须使用同一个 `label_reference_view`。跨 horizon 比较只能使用 `utility_proxy_per_20d` 或同 horizon raw proxy；不得用 raw `utility_proxy` 比较 H20 / H40 / H60。`utility_proxy_per_20d` 只是线性归一的 conservative proxy，不是精确年化收益或真实净值。

For defense / survivor comparisons:

```text
recall_label_reference_view = c0_entry_anchor
continuation_label_reference_view = c0_post_survivor_continuation

entry_anchor_positive_n =
  count entry-anchor winner_positive in c0_entry_t0

posthoc_retained_entry_anchor_positive_n =
  count entry-anchor winner_positive among c0_posthoc_no_fast_fail_survivor rows

deployable_retained_entry_anchor_positive_n =
  count entry-anchor winner_positive among c0_deployable_stage2_reference rows

posthoc_continuation_positive_n =
  count continuation-view winner_positive in c0_posthoc_no_fast_fail_survivor rows

deployable_continuation_positive_n =
  count continuation-view winner_positive in c0_deployable_stage2_reference rows

posthoc_survivor_recall_vs_entry =
  posthoc_retained_entry_anchor_positive_n / entry_anchor_positive_n

deployable_stage2_recall_vs_entry =
  deployable_retained_entry_anchor_positive_n / entry_anchor_positive_n

posthoc_recall_cost = 1 - posthoc_survivor_recall_vs_entry
deployable_recall_cost = 1 - deployable_stage2_recall_vs_entry

entry_utility_total_indexed_to_entry_n =
  c0_entry_t0.utility_proxy_per_entry * c0_entry_t0.denominator_n

deployable_stage2_utility_total_indexed_to_entry_n =
  c0_deployable_stage2_reference.utility_proxy_per_entry * c0_entry_t0.denominator_n

recall_adjusted_utility_deterioration_vs_entry =
  if entry_utility_total_indexed_to_entry_n > 0:
    max(0, entry_utility_total_indexed_to_entry_n - deployable_stage2_utility_total_indexed_to_entry_n)
    / abs(entry_utility_total_indexed_to_entry_n)
  else:
    0 if deployable_stage2_utility_total_indexed_to_entry_n >= entry_utility_total_indexed_to_entry_n
    else 1
```

Utility proxy must be reported with count-based recall:

```text
precision_rate
captured_positive_n
recall_vs_entry
utility_proxy_per_entry
utility_proxy_per_20d
utility_proxy_total_indexed_to_entry_n
recall_adjusted_utility_deterioration_vs_entry
```

Any claim that survivor-conditional is better must show both:

```text
conditional precision improves
captured_positive_n / recall-adjusted utility does not deteriorate beyond pre-registered tolerance
```

`min_recall_vs_entry = 0.70` 是严格默认值，可能在 fast-fail 结构下变成近似“保证失败”的阈值。Runner 必须在 final decision 前输出 `recall_floor_feasibility_audit.csv`，用 12A6c / 12A7f 已知 fast-fail 率和 train-only selected-label entry-anchor retained positives 粗估该阈值是否结构性绑定：

```text
min_recall_vs_entry
recall_floor_feasibility_warning_margin
c0_entry_fast_fail_rate
c0_entry_no_fast_fail_rate
train_selected_label_entry_anchor_positive_n
train_selected_label_retained_entry_anchor_positive_n
train_selected_label_retained_recall_vs_entry
fixed_anchor_retained_recall_vs_entry_if_available
recall_floor_structurally_binding =
  train_selected_label_retained_recall_vs_entry + recall_floor_feasibility_warning_margin
  < min_recall_vs_entry
```

若 `recall_floor_structurally_binding == true`，runner 不得自动放宽阈值，但 report 必须明确说明 continue 分支受到预注册 recall floor 的强约束；若需要调整，只能在新的 requirement 或重新冻结的 config 中完成。

## 12. Full-universe primitive triage

This is not event-family cartography. It is a cheap direction test.

For the selected label, compute univariate separability over `full_pit_c0_comparable_active_band` for the allowed primitive features. `full_pit_risk_on_universe_raw_diagnostic` 可同步输出，但不得进入 pass/fail gate：

```text
full_universe_auc
full_universe_rank_ic
full_universe_top_decile_lift_abs
full_universe_top_decile_lift_ratio
year_stability
board_stability
instrument_month_block_bootstrap_ci
best_c0_auc_for_same_label
best_c0_top_decile_lift_abs_for_same_label
best_c0_top_decile_lift_ratio_for_same_label
full_vs_c0_auc_delta
full_vs_c0_auc_delta_ci95_low
full_vs_c0_top_decile_lift_delta_abs
full_vs_c0_top_decile_lift_delta_abs_ci95_low
active_band_id
active_band_cartography_gate_eligible
```

Year / board stability is measured on the train-selected feature / orientation and selected label:

```text
stability_slice included if:
  slice_denominator_n >= min_full_universe_stability_slice_n
  and slice_positive_n >= min_full_universe_stability_slice_positive_n

year_stability_dispersion =
  max(abs(slice_top_decile_lift_abs - overall_top_decile_lift_abs)) over calendar_year slices

board_stability_dispersion =
  max(abs(slice_top_decile_lift_abs - overall_top_decile_lift_abs)) over board_bucket slices

full_universe_stability_not_worse_than_c0 =
  full_universe_year_stability_dispersion <= best_c0_year_stability_dispersion + max_full_vs_c0_stability_dispersion_delta
  and full_universe_board_stability_dispersion <= best_c0_board_stability_dispersion + max_full_vs_c0_stability_dispersion_delta
```

If C0 lacks enough included year / board slices to compute a comparator dispersion, `full_universe_stability_not_worse_than_c0 = false` for the cartography gate and the full-universe readout is diagnostic-only.

Full-universe primitive pass:

```text
full_universe robustness separability pass
and search_adjusted_status = pass
and full_universe_stability_not_worse_than_c0 = true
and full_vs_c0_auc_delta >= min_full_universe_auc_delta
and full_vs_c0_auc_delta_ci95_low > 0
and full_vs_c0_top_decile_lift_delta_abs >= min_full_vs_c0_top_decile_lift_delta_abs
and full_vs_c0_top_decile_lift_delta_abs_ci95_low > 0
and effective_block_n >= min_full_universe_effective_block_n
and abs(c0_coverage_rate_delta_vs_train) <= max_active_band_c0_coverage_rate_split_delta
and abs(active_band_share_delta_vs_train) <= max_active_band_share_split_delta
and active_band_cartography_gate_eligible == true
```

这些 delta threshold 必须使用 §9.3 的 pre-registered config defaults，不能在 runner 中隐式硬编码或跑后调整。

This pass only authorizes:

```text
next_allowed_requirement = requirement_12a7h_event_family_enrichment_cartography.md
```

It does not support any event family by itself.

## 13. Decision logic

Runner 必须先计算所有 candidate decision flags，再按以下固定优先级输出唯一 `decision_state`。若多个条件同时成立，选择优先级最高者，并在 `decision_precedence_audit.csv` 记录被压制的 lower-priority candidate states。

```text
decision_precedence:
  1. 12A7g_blocked_input_or_lineage_failure
  2. 12A7g_vol_scaled_label_drift_unresolved
  3. 12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild
  4. 12A7g_c0_posthoc_survivor_signal_diagnostic_only
  5. 12A7g_full_universe_more_separable_start_event_cartography
  6. 12A7g_baserate_only_not_separable_stop_winner_selection
```

### 13.1 Input failure

```text
12A7g_blocked_input_or_lineage_failure:
  any required input missing, schema mismatch, upstream decision mismatch,
  PIT failure, regime PIT failure, split boundary failure, feature availability failure,
  label reproduction failure, or horizon completeness failure.
```

若 `full_pit_c0_comparable_active_band` 无法构造，不得 fail-open；必须设置 `active_band_cartography_gate_eligible = false`，并禁止 §13.4，但不阻断 C0 entry / survivor / deployable denominator readouts。

### 13.2 Continue C0 label-revision route

```text
12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild:
  selected label passes train-frozen eligibility and stability;
  if selected label is fixed anchor, it was selected by §9.1 without validation / robustness feedback;
  c0_deployable_stage2_reference robustness separability pass on continuation_view;
  c0_entry_t0 or c0_deployable_stage2_reference utility_proxy_total_indexed_to_entry_n is positive after cost buffer;
  cross-horizon comparison uses utility_proxy_per_20d, not raw utility_proxy;
  deployable_stage2_recall_vs_entry >= min_recall_vs_entry;
  recall_adjusted_utility_deterioration_vs_entry <= max_recall_adjusted_utility_deterioration;
  posthoc-only evidence is not the sole support source;
  validation and robustness directions agree.

next_allowed_requirement =
  requirement_12a7h_decoupled_defense_overlay_survivor_stage_winner_selector.md
```

### 13.3 Diagnostic-only C0 survivor signal

```text
12A7g_c0_posthoc_survivor_signal_diagnostic_only:
  c0_posthoc_no_fast_fail_survivor separability pass;
  but c0_deployable_stage2_reference does not pass;
  or recall-adjusted utility proxy fails;
  or support is only visible after post-hoc survivor conditioning.

next_allowed_requirement =
  requirement_12a7g2_stage2_decision_time_repair_or_event_cartography_triage.md
```

### 13.4 Start event-family cartography

```text
12A7g_full_universe_more_separable_start_event_cartography:
  C0 entry and C0 deployable stage2 denominators do not pass separability;
  full_pit_c0_comparable_active_band primitive scan passes separability on the same selected label;
  full-universe pass is search-adjusted and stable by year / board;
  full_universe is better than best C0 readout by pre-registered delta thresholds;
  full_universe effective_block_n passes overlap-correlation control;
  active_band_cartography_gate_eligible == true;
  full_pit_c0_comparable_active_band utility_proxy_per_20d > 0 after cost buffer.

next_allowed_requirement =
  requirement_12a7h_event_family_enrichment_cartography.md
```

### 13.5 Stop winner-selection route

```text
12A7g_baserate_only_not_separable_stop_winner_selection:
  selected label may show base-rate enrichment,
  but neither C0 denominators nor full-universe primitive scan show robust separability;
  or utility proxy is non-positive after recall cost and cost buffer.

next_allowed_requirement =
  defense_overlay_plus_rule_based_participation_summary
```

### 13.6 Label drift unresolved

```text
12A7g_vol_scaled_label_drift_unresolved:
  vol-scaled label panel does not reduce year / board / regime drift vs fixed anchors;
  or selected label is too unstable for separability interpretation.

next_allowed_requirement =
  requirement_12a7g_label_form_stability_revision.md
```

This state is triggered mechanically before separability decisions if any of the following train-frozen label conditions is true:

```text
no label passes eligibility
selected_label.label_base_rate_dispersion > max_label_base_rate_dispersion
selected_label.same_bar_conflict_rate > max_same_bar_conflict_rate
selected_label.horizon_complete_rate < 0.98
selected_label.winner_positive_n < min_train_positive_n
best_vol_scaled_label exists
  and best_fixed_anchor_label exists
  and vol_scaled_not_worse_than_fixed == false
  and selected_label.label_type == vol_scaled
label_selection_active_band_status == diagnostic_source
  and full_universe_active_band_audit.active_band_cartography_gate_eligible == false
  and active-band ineligibility reason prevents stable label drift interpretation
```

If fixed anchors are selected because `vol_scaled_not_worse_than_fixed == false`, the decision is not automatically `label_drift_unresolved`; the runner must continue with the fixed anchor only when the fixed anchor itself passes all label eligibility and stability thresholds. Otherwise it must set `12A7g_vol_scaled_label_drift_unresolved`. This case must be explicit in `label_selection_train_audit.csv`.

## 14. Required outputs

Publishable tables:

```text
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/input_artifact_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_split_boundary_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_primitive_feature_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_active_band_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/stage1_anchor_x030_reconstruction_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_overlap_effective_n_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_formula_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_panel_summary.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/horizon_completeness_by_split_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_selection_train_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/pre_registered_threshold_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/denominator_contract_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/c0_denominator_diversity_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_feature_construction_coupling_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/c0_label_base_rate_readout.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/c0_separability_readout.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_primitive_separability_readout.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/common_entry_anchor_recall_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/continuation_recall_cost_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/recall_floor_feasibility_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/utility_proxy_readout.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/search_multiplicity_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/stability_slice_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/decision_precedence_audit.csv
outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/vol_scaled_label_separability_decision.csv
```

Local cache:

```text
outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/full_pit_vol_scaled_label_panel.parquet
outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/c0_vol_scaled_label_matrix.parquet
outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_primitive_feature_panel.parquet
outputs/local_cache/12A7g_vol_scaled_label_panel_c0_separability_triage/bootstrap_replicates.parquet
```

Report and manifest:

```text
outputs/publishable/reports/vol_scaled_label_panel_c0_separability_triage_report.md
outputs/manifests/12A7g_vol_scaled_label_panel_c0_separability_triage_manifest.json
```

## 15. Report requirements

Report must include:

1. Final `decision_state` and next allowed requirement.
2. Explicit statement that full-universe label panel is event-agnostic and not event support.
3. Decision precedence audit if multiple candidate states are true.
4. Pre-registered threshold audit with defaults / overrides.
5. Global regime calendar audit, full-universe split boundary audit, primitive feature audit, active-band audit, active-band coverage drift, and overlap-correlation effective-N audit.
6. Horizon completeness by split / horizon, proving separability excludes censored endpoint rows.
7. Label selection audit showing train-only choice, stability score, drift status, vol-scaled-vs-fixed comparison, and validation / robustness readout-only status.
8. Label-feature construction coupling audit, especially volatility label vs volatility feature and same-bar conflict by vol bucket.
9. C0 entry, post-hoc survivor, and deployable stage2 denominators in separate tables, including diversity counts and X=0.30 row-level reconstruction.
10. A warning if post-hoc survivor passes but deployable stage2 denominator fails.
11. Recall cost table using common entry-anchor positives, with continuation positives reported separately.
12. Recall floor feasibility audit showing whether `min_recall_vs_entry` is structurally binding.
13. Utility proxy table including neutral component, recall-adjusted utility deterioration, and per-20d normalized proxy, explicitly not called NAV or policy replay.
14. Full-universe primitive readout and whether the C0-comparable active band justifies event-family cartography under relative-vs-C0 thresholds.
15. Search multiplicity audit and adjusted status.
16. Stability slices by split, calendar_year, board_bucket, market_regime_bucket, and primary C0 family where applicable.
17. Missing regime calendar dates, if any, are reported as bypassed row / unique-date counts, excluded from primary-scope denominators, and do not by themselves set `input_gate_status = fail`.

## 16. Validation commands

Expected validation commands:

```bash
python -m py_compile experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a7g_vol_scaled_label_panel_c0_separability_triage.py
pytest -q experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/tests/test_12a7g_vol_scaled_label_panel_c0_separability_triage.py
python experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a7g_vol_scaled_label_panel_c0_separability_triage.py --mode check-inputs
python experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a7g_vol_scaled_label_panel_c0_separability_triage.py --mode full
```

## 17. Acceptance checklist

1. `input_artifact_audit.csv` includes every required artifact and all required rows have `read_status = pass`, `schema_status = pass`.
2. Global regime calendar is an explicit required input, every primary reference_date maps to one non-conflicted regime row, and `risk_on` is joined from `daily_regime_bucket`.
3. `full_universe_split_boundary_audit.csv` proves reference-date split assignment with frozen upstream boundaries and counts any `boundary_gap_excluded` rows.
4. `full_universe_primitive_feature_audit.csv` records qfq-derived primitive formulas, lookbacks, PIT availability, missing / duplicate qfq status, and C0 volatility reconciliation.
5. `full_universe_active_band_audit.csv` proves the cartography gate uses C0-comparable active opportunity band, not raw full universe, and passes active-band coverage drift thresholds.
6. `stage1_anchor_x030_reconstruction_audit.csv` proves row-level X=0.30 keep reconstruction against upstream 12A7e selected_n / rank_evaluable_n / budget.
7. `label_overlap_effective_n_audit.csv` proves full-universe primitive CI uses block/effective-N controls.
8. `horizon_completeness_by_split_audit.csv` proves separability excludes censored endpoint rows.
9. `pre_registered_threshold_audit.csv` records all default / overridden go/no-go constants before run execution.
10. `label_formula_audit.csv` records every label formula, vol reference unit, k grid value, horizon, same-bar priority, path-window inclusivity, and horizon completeness.
11. Full PIT label panel is computed without using C0 membership, event family, future returns, or episode labels as features.
12. Primary label selection is train-only, deterministic, uses the registered stability score, and does not use any separability readout.
13. Feature / orientation selection uses the registered separability score and deterministic tie-breaks.
14. C0 post-hoc survivor readout is marked `diagnostic_only` and cannot set deployable support.
15. C0 deployable stage2 readout uses only features whose row-level `availability_time <= stage_2_reference_pos`.
16. C0 denominator diversity passes `min_c0_instrument_n` and `min_c0_instrument_month_block_n`.
17. Label-feature construction coupling is audited; same-source volatility features are not primary unless orthogonalized, and same-bar conflict is stratified by vol bucket.
18. Recall cost uses common entry-anchor positives; continuation positives are reported separately.
19. `recall_floor_feasibility_audit.csv` reports whether `min_recall_vs_entry` is structurally binding before final decision.
20. Continue-C0 decision requires `recall_adjusted_utility_deterioration_vs_entry <= max_recall_adjusted_utility_deterioration`.
21. Full-universe primitive readout cannot directly support an event family and must beat C0 inside the active band by pre-registered delta thresholds to authorize cartography.
22. Search multiplicity is recorded with `bonferroni_bootstrap_ci`, and final status reports adjusted support.
23. Label drift unresolved is triggered only by the mechanical conditions in §13.6.
24. Utility proxy includes neutral component and per-20d normalized proxy; it is not described as NAV, alpha, policy replay, or deployable return.
25. `decision_precedence_audit.csv` records candidate states and precedence if more than one condition is true.
26. `vol_scaled_label_separability_decision.csv` has exactly one row and one allowed decision state.

Allowed decision states:

```text
12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild
12A7g_c0_posthoc_survivor_signal_diagnostic_only
12A7g_full_universe_more_separable_start_event_cartography
12A7g_baserate_only_not_separable_stop_winner_selection
12A7g_vol_scaled_label_drift_unresolved
12A7g_blocked_input_or_lineage_failure
```

## 18. One-line summary

12A7g is the cheapest fork-resolution gate: define the vol-scaled winner label on the full PIT universe, test C0 separability without rebuilding events, account for survivor recall cost, and only start event-family cartography if full-universe primitives are clearly more separable than C0.
