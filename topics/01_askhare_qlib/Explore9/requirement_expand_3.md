# Explore9 扩展需求 3：P0.7 启动观察池分层、失败过滤与持有/加仓 Gate 探索

版本：review3-fixed / 2026-05-05

本版用于替换上一版 `requirement_expand_3.md`。本版吸收三轮 review，重点修复以下问题：

1. `launch_episode` 合并窗口不得把 later-in-episode 的 post-20 / post-30 / late acceleration 回写到 first launch classification。
2. `launch_stratum_event` 上不得存储 outcome-derived recommendation；event row 只存 T 日可观察的 `declared_stratum_role`。
3. 评估后的 `recommended_action_class_after_evaluation` 只能出现在 leaderboard / report。
4. failure filter denominator 必须显式区分 reject recall、reject precision、scope prevalence、drawdown avoided、false reject。
5. 未触发 filter 的样本也必须有 `filter_opportunity_deadline`、`filter_opportunity_effective_deadline` 与 `filter_decision_reference_date_for_denominator`。
6. false reject 必须排除 target 已经在 filter / gate 生效前达成的样本。
7. failure filter 公式必须声明 `signal_date_definition`，区分 first-hit 与 fixed-window-end。
8. hold / add-on gate 必须有 exposure model，否则不得计算 premature exit、continue hold、unconditional hold 或 add-on success。
9. P0.7 第一实现批次收敛为 P0.7A + P0.7B；P0.7C hold / add-on gate 暂缓。
10. P0.7A family matrix 闭合为 10 个 family、每类至少 2 个 variant。
11. 所有公式字段必须进入 `p0_7_feature_dictionary.csv`；所有阈值必须使用 YAML 中的 `thresholds.*` key。
12. full row-level panels 只要求 parquet cache；报告 CSV 只输出 summary / dictionary / leaderboard / audit。
13. matched-delay baseline 必须声明 `n_jobs` 与 `max_sample_per_variant` 等 runtime controls。
14. 公式 token contract 必须覆盖 raw OHLC、prior_close、qXX_market、first_occurrence_in_60d 等宏 / alias。
15. failure filter 的 R 边界统一为 `<= filter_opportunity_deadline`。
16. launch stratification baseline 必须有显式 schema、分母和 join key。
17. matched-delay pseudo reject set 主榜必须采用 equal-real-reject-count 构造，即每个 repeat 的 pseudo rejected count 等于真实 |R|。
18. opportunity deadline 必须是 trading-day offset，并审计 window / horizon truncation。
19. filter_before_12pct / 20pct drawdown rate 必须明确相对 `stratum_effective_price_reference`。

---

## 1. 背景

Explore9 P0 / P0.5 / P0.6 已形成清晰链路：

- P0 发现大 winner 路径中存在高波动、强趋势、相对强度、成交保持、post-20 / post-30 continuation、late acceleration 等可观察结构。
- P0.5 进一步拆解 early-entry、高波、repair、rank jump、money quality、sparse strong-day，但 qualified early-entry lead 为 0；很多结构在 stock-day 或 dedup event 上好看，切到 instrument-year 后不成立。
- P0.6 测试 launch 后 3/5/10/20 日 delayed first-entry trigger，25 个 entry trigger 没有任何一个可升级为 P1 entry hypothesis；confirmation / pullback / higher-low 更适合 hold、failure filter 或 add-on 观察，而不是 launch-after-confirmation 首入场。

因此 P0.7 不继续扩大 delayed first-entry trigger 网格，而是转成：

```text
P0.7 = launch pool stratification + failure filter discovery + hold/add-on gate contract
```

核心问题从：

```text
launch 后等什么确认再首入场？
```

改成：

```text
1. 哪些 launch stratum 本身值得观察、直接入场研究、或风险降级？
2. 哪些 launch 后失败结构能尽早剔除 false positive，同时不误杀 pending winner？
3. 哪些 confirmation 结构只适合作为 hold / add-on gate，而不是 entry trigger？
```

---

## 2. 阶段定位与实现范围

P0.7 是 Explore9 broad discovery 的第三轮扩展，不是 P1，不是策略回测，不是完整交易系统。

P0.7 不做：

- 最低点预测。
- delayed confirmation first-entry trigger 继续加网格。
- 完整持有策略。
- 完整加仓策略。
- 完整止损策略。
- Explore10 strategy backtest。
- 使用 2025-2026 observed reference 选择阈值。
- 使用 Explore3-Explore8 历史交易结果作为 label、feature、selection input 或排序依据。
- 使用 post-entry / post-filter future outcome 反向筛选 T 日样本。

P0.7 可以做：

- 生成 launch episode。
- 生成 T 日可观察的 launch stratum event。
- 评估 launch stratum 的 direct-launch research baseline。
- 生成 failure filter opportunity panel 与 failure filter event panel。
- 明确 failure filter 的 denominator、precision、recall、false reject 与 matched-delay drawdown audit。
- 定义 hold / add-on gate schema contract。
- 输出 P1 launch stratification / P1 failure filter refine 的候选方向和淘汰方向。

### 2.1 第一实现批次硬切分

P0.7 第一实现批次只做 P0.7A + P0.7B：

```text
P0.7AB first implementation:
  - launch_episode_panel
  - launch_stratum_event_panel
  - launch_stratification_leaderboard
  - failure_filter_opportunity_panel
  - failure_filter_event_panel
  - failure_filter_leaderboard
  - failure_filter_false_reject_audit
  - failure_filter_drawdown_reduction_audit
  - matched-delay filter baseline
  - instrument-year / dedup / regime / industry / coverage audit
```

P0.7C 暂缓：

```text
P0.7C deferred:
  - hold gate leaderboard
  - add-on gate leaderboard
  - exposure-model based hold/add-on success
```

P0.7AB 可以定义 P0.7C schema contract，但不得输出：

```text
recommendation = proceed_to_p1_hold_gate_refine
recommendation = proceed_to_p1_addon_gate_refine
```

---

## 3. 数据边界与纪律

沿用 Explore9 数据边界：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

硬约束：

- 每个 `date + instrument` 样本必须在当日 PIT membership 中。
- 行业归属必须按 PIT industry membership join。
- 成交额字段继续使用 `money`，不得改用 `amount`。
- OHLC 默认已调整，不得再次乘 `factor`。
- P0 / P0.5 / P0.6 输出可以作为 schema reference、candidate family reference 和 audit reference。
- P0 / P0.5 / P0.6 ranked results 不得作为 selection input。
- Explore3-Explore8 的交易结果、signals、daily candidates、model predictions、portfolio daily 不得作为 label、feature、selection input 或排序依据。
- 2025-2026 observed reference 只能观察，不得用于阈值选择。
- 所有新增输出必须落在 `Explore9/outputs/` 下。

允许复用：

```text
Explore9/outputs/cache/stock_day_label_panel.parquet
Explore9/outputs/reports/episode_lifecycle_labels.csv
Explore9/outputs/reports/p0_5_primitive_feature_dictionary.csv
Explore9/outputs/reports/p0_5_pairwise_lift.csv
Explore9/outputs/reports/p0_5_candidate_pattern_audit.csv
Explore9/outputs/cache/p0_6_launch_event_panel.parquet
```

Manifest 必须记录：

```text
p0_label_panel_reused = true / false
p0_5_feature_reference_used = true / false
p0_6_launch_event_panel_reused = true / false
p0_6_entry_results_used_for_selection = false
p0_5_ranked_results_used_for_selection = false
historical_trade_results_used_for_labeling = false
historical_trade_results_used_for_signal = false
historical_trade_results_used_for_selection = false
observed_reference_used_for_selection = false
same_close_proxy_used_in_main_leaderboard = false
later_lifecycle_rewrite_used = false
stratum_declared_role_separated_from_evaluated_recommendation = true
filter_opportunity_panel_required = true
filter_decision_reference_date_defined_for_all_U = true
filter_signal_date_definition_required = true
false_reject_target_timing_audit_passed = true
hold_addon_gate_deferred = true
full_event_csv_reports_disabled_by_default = true
matched_delay_runtime_controls_declared = true
```

---

## 4. 样本单位

### 4.1 Launch Episode

`launch_episode` 是 audit / grouping unit，不是 T 日动作分类单位。

合并规则：

```text
same instrument launch events with gap <= launch_episode_collapse_gap_days collapse into one launch_episode
```

每个 episode 至少包含：

```text
launch_episode_id
instrument
launch_episode_first_date
launch_episode_last_date
launch_episode_first_observable_family
launch_episode_first_observable_role
launch_episode_family_set_asof_first_date
launch_episode_family_set_full_episode_audit
launch_episode_contains_post20_later
launch_episode_contains_post30_later
launch_episode_contains_late_acceleration_later
launch_episode_contains_sparse_strong_day_later
launch_episode_summary_primary_family_audit_only
launch_episode_summary_primary_family_used_for_first_stratum = false
```

关键纪律：

```text
launch_episode_summary_primary_family_audit_only 只能用于报告和审计。
first launch classification 只能使用 launch_episode_first_date 当天及以前可观察字段。
later lifecycle states create later launch_stratum_events rather than rewriting the first one.
```

例子：

```text
Day 1: primary_pre_20 launch appears
Day 8: post_20 state appears
Day 15: late_acceleration state appears
```

则：

```text
Day 1 创建 first launch_stratum_event，只能按 Day 1 字段分类。
Day 8 创建新的 post_20 launch_stratum_event。
Day 15 创建新的 late_acceleration launch_stratum_event。
不得把 Day 15 的 late_acceleration 回写成 Day 1 的 primary family。
```

### 4.2 Launch Stratum Event

`launch_stratum_event` 是 P0.7A 的主研究单位，表示在某个 `stratum_date` 上可观察到的 launch / lifecycle stratum。

核心纪律：event row 只能记录 `stratum_date` 当天可观察的角色声明，不得记录评估后才知道的推荐动作。

每个 stratum event 至少包含：

```text
launch_stratum_event_id
launch_episode_id
instrument
stratum_date
stratum_effective_date
stratum_effective_price_reference
stratum_family
stratum_variant
stratum_formula
stratum_formula_version
declared_stratum_role
declared_lifecycle_stage
role_declaration_rule_id
stratum_source_event_date
stratum_observation_cutoff_date
stratum_observable_fields_asof_date
stratum_family_set_asof_date
stratum_lifecycle_transition_from_previous_stratum
created_by_later_lifecycle_state
later_episode_lifecycle_state_used = false
stratum_market_regime
stratum_industry_regime
stratum_prelaunch_path_bucket
stratum_volatility_quality_bucket
stratum_money_quality_bucket
label_horizon_truncated
observed_reference_overlap
```

T 日可观察性：

```text
stratum_observation_cutoff_date = stratum_date
stratum_family / declared_stratum_role / declared_lifecycle_stage
  only use stratum_date or earlier observable fields
```

禁止：

```text
use episode_audit_contains_*_ever in stratum classification
rewrite first stratum using later lifecycle fields
collapse later lifecycle state into first launch action
store direct_entry_watchable / failure_prone_no_trade as event-row fields
```

`declared_stratum_role` 枚举：

```text
launch_observation_context
watchlist_observation_context
risk_warning_context
hold_continuation_context
addon_context_deferred
diagnostic_context
rejected_or_uncertain_context
```

说明：

- `declared_stratum_role` 是 T 日可观察角色，只能由 `stratum_date` 当天或以前字段决定。
- `declared_stratum_role` 不得包含收益、lift、baseline、coverage、instrument-year 等评估后信息。
- `recommended_action_class_after_evaluation` 只能出现在 leaderboard / report，由 baseline、lift、coverage、drawdown、false-reject、instrument-year 审计后生成。

评估后推荐动作枚举：

```text
direct_entry_watchable
watchlist_only
failure_prone_no_trade
hold_continuation_only
add_on_context_only
diagnostic_only
rejected_or_uncertain
```

约束：

```text
stratum event row stores declared_stratum_role only
leaderboard/report stores recommended_action_class_after_evaluation only
recommended_action_class_after_evaluation can use baseline / lift / coverage / IY audit
declared_stratum_role cannot use baseline / lift / coverage / IY audit
```

### 4.3 Failure Filter Opportunity 与 Failure Filter Event

P0.7B 必须先生成 `failure_filter_opportunity_panel`，再从中派生 `failure_filter_event_panel`。

```text
failure_filter_opportunity_panel:
  one row per launch_stratum_event_id + filter_variant
  includes rows with and without filter signal
  used as denominator U

failure_filter_event_panel:
  subset of opportunity rows where filter_signal_occurs = true
  used as rejected set R
```

每个 opportunity row 至少包含：

```text
failure_filter_opportunity_id
launch_stratum_event_id
launch_episode_id
instrument
stratum_date
filter_family
filter_variant
filter_formula_version
filter_search_start_date
filter_opportunity_deadline
filter_opportunity_effective_start_date
filter_opportunity_effective_deadline
filter_window_truncated
filter_horizon_truncated
filter_window_missing_reason
filter_signal_occurs
filter_signal_date
filter_effective_date
filter_effective_price_reference
filter_decision_reference_date_for_denominator
signal_date_definition
formula_window_trading_days
filter_formula_observation_timing
```

每个 failure filter event 至少包含：

```text
failure_filter_event_id
failure_filter_opportunity_id
launch_episode_id
launch_stratum_event_id
instrument
stratum_date
filter_signal_date
filter_effective_date
filter_effective_price_reference
filter_delay_trading_days
filter_family
filter_variant
filter_formula
filter_formula_version
filter_observable_fields
signal_date_definition
filter_formula_observation_timing
filter_action
filter_severity
filter_reason_code
filter_reference_price
filter_reference_rule
filter_price_at_signal
filter_price_at_effective_date
target_reached_before_filter_effective_date_20pct_high_60d
target_reached_before_filter_effective_date_50pct_high_120d
target_reached_before_filter_effective_date_50pct_close_120d
target_reached_before_filter_effective_date_100pct_high_240d
target_not_reached_before_filter_effective_date_50pct_high_120d
target_not_reached_before_filter_decision_reference_date_50pct_high_120d
post_target_filter_signal
filter_max_adverse_excursion_before_signal
filter_max_favorable_excursion_before_signal
filter_rank_within_launch_stratum
is_first_filter_for_launch_stratum
is_primary_counted_filter
```

Filter action 枚举：

```text
remove_from_watchlist
no_new_entry
reduce_risk
no_add_on
hold_review_only
diagnostic_only
```

Timing 硬约束：

```text
filter_search_start_date = next_trading_day(stratum_date)
filter_signal_date > stratum_date
filter_signal_date <= filter_opportunity_deadline
filter condition uses only filter_signal_date and earlier observable data
filter_effective_date sample is PIT member

if filter_formula_observation_timing = close_derived:
    filter_effective_date = next_trading_day(filter_signal_date)
    filter_effective_price_reference = next_open
elif filter_formula_observation_timing = intraday_observable:
    filter_effective_date >= filter_signal_date
    intraday_observable_fields_must_be_declared = true
else:
    filter_formula_observation_timing defaults to close_derived
```

Signal-date definition 必须逐公式声明：

```text
signal_date_definition = first_hit_within_window / fixed_window_end / instantaneous_day / rolling_window_first_hit
```

默认规则：

```text
first_hit_within_window:
  filter_signal_date = first date in search window where formula becomes true

fixed_window_end:
  filter_signal_date = configured window end date; formula can use the full window but cannot act earlier

instantaneous_day:
  filter_signal_date = the same date as the single-day observable condition

rolling_window_first_hit:
  filter_signal_date = first date where rolling-window condition becomes true
```

没有 `signal_date_definition` 的 filter formula 不得进入主榜。

### 4.4 Hold Gate / Add-on Gate Event（P0.7C deferred contract）

P0.7C 第一批不运行，但 schema contract 必须明确 exposure model，防止 hold/add-on gate 变成隐藏 entry filter。

Exposure model 枚举：

```text
watchlist_observation_only
direct_launch_research_exposure
post_20_30_existing_winner_context
sparse_strong_day_existing_context
manual_or_external_exposure_forbidden
```

每个 hold / add-on event 必须包含：

```text
exposure_model
exposure_start_date
exposure_reference_price
exposure_source_rule
exposure_start_is_T_day_observable
exposure_assumption_declared = true
hidden_entry_filter_used = false
```

没有 `exposure_start_date` 和 `exposure_reference_price`，不得计算：

```text
premature_exit
continue_hold
unconditional_hold_baseline
hold_gate_success_lift
add_on_success_lift
```

---

## 5. Effective-date 与执行口径

默认执行口径：

```text
formula_observation_timing = close_derived
effective_date = next_trading_day(signal_date)
effective_price_reference = next_open
```

同日生效只允许：

```text
formula_observation_timing = intraday_observable
intraday_observable_fields_must_be_declared = true
same_day_effective_allowed_by_formula = true
```

禁止：

```text
close-derived signal same-day close execution in main leaderboard
same_close_proxy in main leaderboard
future invalidation as sample selection
post-filter future outcome as formula input
```

---

## 6. Label 与 target timing

P0.7 label 从 `stratum_effective_price_reference` 或 `filter_effective_price_reference` 重算，不得直接复用 launch 日 label。

Launch stratum labels：

```text
stratum_future_20pct_high_60d
stratum_future_50pct_high_120d
stratum_future_50pct_close_120d
stratum_future_100pct_high_240d
stratum_future_100pct_close_240d
stratum_future_max_drawdown_60d
stratum_drawdown_before_50pct_gain
stratum_time_to_20pct_high_days
stratum_time_to_50pct_high_days
```

Failure labels：

```text
launch_nonwinner_primary = not stratum_future_50pct_high_120d
launch_failure_primary =
  not stratum_future_20pct_high_60d
  and stratum_future_max_drawdown_60d <= -thresholds.failure_drawdown_threshold
```

False reject target timing：

```text
target_not_reached_before_filter_effective_date_50pct_high_120d =
  stratum_future_50pct_high_120d
  and target_50pct_high_date > filter_effective_date

failure_filter_false_reject_winner =
  filter_signal_occurs
  and stratum_future_50pct_high_120d
  and target_not_reached_before_filter_effective_date_50pct_high_120d
```

如果 target 已在 filter 生效前达成：

```text
post_target_filter_signal = true
false_reject = false
```

这些样本只能进入：

```text
post_target_risk_reduction_audit
post_target_hold_review_audit
```

P0.7C deferred 也必须使用同样规则：

```text
target_not_reached_before_gate_effective_date
target_not_reached_before_addon_effective_date
```

---

## 7. 特征、派生字段与配置命名

### 7.1 Feature dictionary

必须生成并写入 `p0_7_feature_dictionary.csv` 的字段包括：

```text
ret_1d
ret_3d
ret_5d
ret_20d
body_ret
day_range
close_location
upper_shadow_pct
lower_shadow_pct
atr20_pct
volatility20
volatility60
money_ratio_20
money_ratio_60
ret_rank_20d_market
ret_rank_20d_market_5d_ago
ret_rank_20d_market_5d_median
ret_rank_20d_market_at_stratum
ret_rank_20d_industry
ret_rank_20d_industry_5d_median
relative_ret20_vs_benchmark
relative_ret20_vs_industry
industry_breadth_20d
industry_breadth_20d_at_stratum
market_regime
ema20
ema20_5d_ago
median20
low20
low60
low90
low120
stratum_low_at_signal
stratum_close_at_signal
invalidation_reference_price
launch_gain_from_recent_low_60d
launch_gain_from_recent_low_90d
launch_gain_from_recent_low_120d
prelaunch_drawdown_120d
max_drawdown_20d
close_location_5d_median
rolling_range_20d
higher_low_count_20d
late_acceleration_flag
post_20pct_relative_strength
post_30pct_relative_strength
prior_close
first_occurrence_in_60d
q40_market
q50_market
q60_market
q70_market
q80_market
q90_market
```

每个字段至少包含：

```text
feature_name
feature_family
feature_role = raw_input / derived_feature / quantile_alias / formula_macro / label_only / audit_only
lookback_days
min_history_trading_days
observable_date
uses_future_data
required_fields
raw_required_field_exempt
feature_eligible_rule
formula_text
formula_text_resolved
thresholds
used_in_launch_stratification
used_in_failure_filter
used_in_hold_gate
used_in_add_on_gate
```

任何 `uses_future_data = true` 的字段只能进入 label / audit，不得进入 formula。

机械定义补充：

```text
ret_rank_20d_market_5d_ago = ret_rank_20d_market shifted by 5 trading days per instrument
ret_rank_20d_market_at_stratum = ret_rank_20d_market observed on stratum_date
market_regime = PIT market regime bucket joined by date from market_targets / target_history
stratum_low_at_signal = stratum low reference available at filter_signal_date; default = low on stratum_date
stratum_close_at_signal = stratum close reference available at filter_signal_date; default = close on stratum_date
invalidation_reference_price = configured observable invalidation price; must specify reference_rule
prior_close = close shifted by 1 trading day per instrument
first_occurrence_in_60d = true if the same formula family has not been true for the same instrument in the prior 60 trading days
qXX_market(feature, date) = PIT-universe cross-sectional quantile of feature on date; XX in {40, 50, 60, 70, 80, 90}
```

Raw field exemption contract：

```text
raw_required_field_exempt = true is allowed only for raw provider fields:
  open, high, low, close, volume, money, factor, instrument, date

raw_required_field_exempt = false for all derived features, formula macros and quantile aliases.
All raw provider fields must still appear in p0_7_feature_dictionary.csv with feature_role = raw_input and min_history_trading_days = 0.
```

Quantile alias contract：

```text
q40_market / q50_market / q60_market / q70_market / q80_market / q90_market are formula macros, not fixed global columns.
A formula like atr20_pct >= q80_market must be resolved in p0_7_launch_formula_matrix.csv as:
  atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe)
A formula like day_range >= q70_market must be resolved as:
  day_range >= cross_section_quantile(day_range, 0.70, date, PIT universe)
Every formula row using qXX_market must populate:
  uses_quantile_alias = true
  quantile_alias_resolved_text
  formula_text_resolved
```

Formula token coverage audit：

```text
p0_7_formula_token_coverage_audit.csv must list every token appearing in formula_text.
Each token must map to exactly one of:
  raw_input_field
  derived_feature
  quantile_alias_macro
  threshold_key
  enum_literal
  operator_or_function
Unmapped token count must be 0 for the run to pass.
```

字段命名规则：

```text
any field, raw input, macro or alias used in a formula must appear in p0_7_feature_dictionary.csv or p0_7_formula_token_coverage_audit.csv
any raw input token must have raw_required_field_exempt = true and feature_role = raw_input
any qXX_market token must have feature_role = quantile_alias and must be resolved in formula_text_resolved
any field ending with _at_stratum must be frozen as of stratum_date
any field ending with _at_signal must be observable as of signal_date, not effective_date
```

### 7.2 Config threshold reference convention

公式和 gate 中必须直接使用 YAML key：

```text
thresholds.<key>
```

例如：

```text
thresholds.min_launch_lift_vs_all
thresholds.rank_drop
thresholds.max_stop_distance_for_new_risk
```

禁止在实现中使用未映射的同义名：

```text
configured_min_launch_lift_vs_all
configured_rank_drop
configured_max_stop_distance_for_new_risk
```

如果报告中为了中文可读性使用 `configured_*` 作为说明别名，manifest 必须输出：

```text
configured_to_yaml_key_mapping
```

---

## 8. P0.7A：Launch Pool Stratification

### 8.1 研究目标

P0.7A 输出 launch pool 分层，而不是 entry trigger leaderboard。

目标：

```text
在 stratum_date 当天或以前可观察的信息下，
先声明不同 launch stratum 的 declared_stratum_role，
再在 leaderboard/report 中基于 baseline / lift / coverage / instrument-year 审计，
输出 recommended_action_class_after_evaluation。
```

### 8.2 Bounded Stratification Family Matrix

P0.7A 第一实现批次必须使用闭合 matrix：10 个 family，每个至少 2 个 variant，总 variant 不少于 20 个。

Family：

```text
1. high_vol_quality_permit
2. high_vol_destructive_warning
3. rank_jump_persistence_watchlist
4. repair_quality_watchlist
5. money_price_keep_context
6. industry_breadth_coherence
7. relative_strength_persistence
8. prelaunch_path_quality
9. sparse_strong_day_lifecycle_node
10. post_20_30_or_late_continuation_context
```

每个 formula row 必须包含：

```text
stratum_family
stratum_variant
formula_text
required_features
required_thresholds
declared_stratum_role
formula_observation_cutoff = stratum_date
formula_uses_future_data = false
```

### 8.3 Launch stratification formulas

#### 8.3.1 high_vol_quality_permit

```text
expansion_high_vol_upper_close =
  atr20_pct >= q80_market
  and day_range >= q80_market
  and close_location >= 0.65
  and ret_rank_20d_market >= 0.70
  and launch_gain_from_recent_low_60d < 0.30
```

```text
high_vol_controlled_drawdown =
  atr20_pct >= q80_market
  and close_location >= 0.60
  and low >= median20 * 0.95
  and ret_rank_20d_market >= 0.65
  and industry_breadth_20d >= q50_market
```

Declared role: `launch_observation_context`.

#### 8.3.2 high_vol_destructive_warning

```text
destructive_high_vol_upper_shadow =
  atr20_pct >= q80_market
  and close_location <= 0.40
  and upper_shadow_pct >= 0.45
```

```text
high_vol_break_median_warning =
  atr20_pct >= q80_market
  and close < median20
  and money_ratio_20 >= 1.30
```

Declared role: `risk_warning_context`.

#### 8.3.3 rank_jump_persistence_watchlist

```text
rank_jump_5d_persist_3d =
  ret_rank_20d_market - ret_rank_20d_market_5d_ago >= 0.25
  and ret_rank_20d_market_5d_median >= 0.60
```

```text
industry_rank_jump_leader =
  ret_rank_20d_industry >= 0.80
  and ret_rank_20d_market >= 0.60
  and relative_ret20_vs_industry >= 0
```

Declared role: `watchlist_observation_context`.

#### 8.3.4 repair_quality_watchlist

```text
repair_reclaim_ema20_quality =
  close >= ema20
  and ema20 >= ema20_5d_ago
  and prelaunch_drawdown_120d <= -0.20
  and close_location >= 0.60
```

```text
repair_higher_low_reclaim =
  higher_low_count_20d >= 1
  and close >= median20
  and max_drawdown_20d >= -0.12
```

Declared role: `watchlist_observation_context`.

#### 8.3.5 money_price_keep_context

```text
money_price_upper_keep =
  money_ratio_20 >= 1.20
  and close_location >= 0.65
  and close >= median20
```

```text
money_expansion_no_distribution =
  money_ratio_20 >= 1.20
  and upper_shadow_pct <= 0.35
  and close >= open
```

Declared role: `watchlist_observation_context`.

#### 8.3.6 industry_breadth_coherence

```text
industry_breadth_confirmed_launch =
  industry_breadth_20d >= q60_market
  and relative_ret20_vs_industry >= 0
  and ret_rank_20d_market >= 0.60
```

```text
weak_market_industry_leader =
  market_regime in [weak, neutral]
  and ret_rank_20d_industry >= 0.80
  and relative_ret20_vs_benchmark >= 0
```

Declared role: `launch_observation_context`.

#### 8.3.7 relative_strength_persistence

```text
relative_strength_10d_persistence =
  ret_rank_20d_market >= 0.70
  and ret_rank_20d_market_5d_median >= 0.65
  and relative_ret20_vs_benchmark >= 0
  and close >= median20
```

```text
industry_relative_strength_persistence =
  ret_rank_20d_industry >= 0.75
  and relative_ret20_vs_industry >= 0
  and close_location_5d_median >= 0.55
```

Declared role: `launch_observation_context`.

#### 8.3.8 prelaunch_path_quality

```text
controlled_repair_from_deep_drawdown =
  prelaunch_drawdown_120d <= -0.25
  and max_drawdown_20d >= -0.12
  and close >= median20
```

```text
range_tightening_then_expand =
  rolling_range_20d <= q40_market
  and day_range >= q70_market
  and close_location >= 0.65
```

Declared role: `watchlist_observation_context`.

#### 8.3.9 sparse_strong_day_lifecycle_node

```text
first_near_limit_upper_close =
  ret_1d >= thresholds.near_limit_threshold
  and close_location >= 0.75
  and first_occurrence_in_60d = true
```

```text
strong_body_day_node =
  body_ret >= q90_market
  and close_location >= 0.75
  and money_ratio_20 >= 1.20
```

Declared role: `diagnostic_context` or `addon_context_deferred`.

#### 8.3.10 post_20_30_or_late_continuation_context

```text
post_20_relative_strength_context =
  launch_gain_from_recent_low_90d >= 0.20
  and launch_gain_from_recent_low_90d < 0.30
  and ret_rank_20d_market >= 0.70
```

```text
late_acceleration_context =
  launch_gain_from_recent_low_120d >= 0.50
  or late_acceleration_flag = true
```

Declared role: `hold_continuation_context` or `addon_context_deferred`.

### 8.4 Direct Launch Baseline Schema Contract

`p0_7_direct_launch_baseline_by_stratum.csv` 是 launch stratification leaderboard 的唯一 baseline source。实现不得在 leaderboard 里临时重算未记录的 baseline。

每个 baseline row 至少包含：

```text
baseline_id
baseline_scope_type
baseline_scope_key
baseline_denominator_unit
baseline_denominator_definition
baseline_join_key
research_start
research_end
target_definition_version
label_reference_date_rule
stratum_family
stratum_variant
candidate_declared_stratum_role
candidate_declared_lifecycle_stage
candidate_market_regime
candidate_industry_regime
eligible_launch_stratum_event_count
eligible_launch_episode_count
distinct_instrument_count
distinct_year_count
future_20pct_high_60d_rate
future_50pct_high_120d_rate
future_50pct_close_120d_rate
future_100pct_high_240d_rate
future_100pct_close_240d_rate
launch_big_winner_primary_rate
launch_false_positive_primary_rate
median_future_max_high_gain_120d
median_future_max_drawdown_60d
median_drawdown_before_50pct_gain
winner_episode_coverage
label_horizon_truncated_rate
observed_reference_overlap_rate
```

`baseline_scope_type` 枚举：

```text
all_launch_episode_baseline
same_launch_family_baseline
same_lifecycle_pool_baseline
same_market_regime_baseline
same_industry_regime_baseline
```

分母定义：

```text
baseline_denominator_unit = launch_stratum_event_id
all_launch_episode_baseline:
  all eligible launch_stratum_event rows in research period with valid label horizon

same_launch_family_baseline:
  eligible launch_stratum_event rows where stratum_family = candidate.stratum_family

same_lifecycle_pool_baseline:
  eligible launch_stratum_event rows where declared_lifecycle_stage = candidate.declared_lifecycle_stage

same_market_regime_baseline:
  eligible launch_stratum_event rows where market_regime = candidate.market_regime

same_industry_regime_baseline:
  eligible launch_stratum_event rows where industry_regime = candidate.industry_regime
```

Baseline join key：

```text
baseline_join_key = (
  baseline_scope_type,
  stratum_family when scope is same_launch_family_baseline else null,
  candidate_declared_lifecycle_stage when scope is same_lifecycle_pool_baseline else null,
  candidate_market_regime when scope is same_market_regime_baseline else null,
  candidate_industry_regime when scope is same_industry_regime_baseline else null,
  target_definition_version,
  label_reference_date_rule,
  research_start,
  research_end
)
```

Leaderboard 中的字段必须从 baseline table join 得到：

```text
lift_vs_same_family_baseline = launch_big_winner_primary_rate / same_family_baseline_launch_big_winner_primary_rate
lift_vs_same_lifecycle_baseline = launch_big_winner_primary_rate / same_lifecycle_baseline_launch_big_winner_primary_rate
same_family_baseline_false_positive_rate = launch_false_positive_primary_rate from same_launch_family_baseline
same_family_baseline_median_drawdown_60d = median_future_max_drawdown_60d from same_launch_family_baseline
```

如果某个 baseline 分母不足：

```text
baseline_insufficient_count = true
corresponding lift field = null
p1_launch_stratification_candidate = false
rejection_reason includes insufficient_baseline_denominator
```

### 8.5 Launch Stratification Leaderboard

`p0_7_launch_stratification_leaderboard.csv` 至少包含：

```text
stratum_family
stratum_variant
declared_stratum_role
recommended_action_class_after_evaluation
launch_episode_count
distinct_instrument_count
distinct_year_count
distinct_industry_count
top1_instrument_contribution
top5_instrument_contribution
future_20pct_high_60d_rate
future_50pct_high_120d_rate
future_50pct_close_120d_rate
future_100pct_high_240d_rate
future_100pct_close_240d_rate
launch_big_winner_primary_rate
launch_false_positive_primary_rate
median_future_max_high_gain_120d
median_future_max_drawdown_60d
median_drawdown_before_50pct_gain
median_time_to_20pct_high_days
median_time_to_50pct_high_days
winner_episode_coverage
winner_episode_coverage_loss_vs_all_launch
lift_vs_all_launch_baseline
lift_vs_same_family_baseline
lift_vs_same_lifecycle_baseline
instrument_year_lift_vs_all_launch
instrument_year_lift_vs_same_family
positive_unique_instrument_year_count
year_by_year_min_precision
year_by_year_precision_std
observability_leak_check_passed
later_lifecycle_rewrite_count
p1_launch_stratification_candidate
rejection_reason
```

P1 launch stratification gate：

```text
launch_episode_count >= thresholds.min_launch_stratum_event_count
distinct_year_count >= thresholds.min_distinct_year_count_launch
distinct_instrument_count >= thresholds.min_distinct_instrument_count_launch
top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
lift_vs_all_launch_baseline >= thresholds.min_launch_lift_vs_all
lift_vs_same_family_baseline >= thresholds.min_launch_lift_vs_same_family
instrument_year_lift_vs_all_launch >= thresholds.min_instrument_year_lift
positive_unique_instrument_year_count >= thresholds.min_positive_unique_instrument_year_count
winner_episode_coverage >= thresholds.min_winner_episode_coverage
launch_false_positive_primary_rate <= same_family_baseline_false_positive_rate + thresholds.max_false_positive_rate_tolerance
median_future_max_drawdown_60d >= same_family_baseline_median_drawdown_60d - thresholds.max_drawdown_worsening_tolerance
observability_leak_check_passed = true
later_lifecycle_rewrite_count = 0
```

---

## 9. P0.7B：Failure Filter Discovery

### 9.1 研究目标

P0.7B 研究：

```text
哪些 launch 后短窗口内的 T 日可观察失败结构，
可以减少 false positive 和 nonwinner drawdown，
同时不显著牺牲 pending winner coverage？
```

Failure filter 不得解释为“通过 filter 才能首入场”。它只能解释为：

```text
risk downgrade / watchlist removal / no-new-entry / no-add-on / hold review
```

### 9.2 Failure Filter Family Matrix

至少 10 类 family，每类至少 2 个 variant，总 variant 不少于 20 个。每个 variant 必须声明：

```text
signal_date_definition
formula_window_trading_days
filter_formula_observation_timing
effective_date_rule
filter_action
```

Family：

```text
1. break_launch_low_filter
2. break_median20_or_ema20_filter
3. gap_fade_filter
4. upper_shadow_volume_failure_filter
5. rank_evaporation_filter
6. money_distribution_filter
7. industry_breadth_evaporation_filter
8. no_followthrough_filter
9. destructive_high_vol_filter
10. wide_stop_or_unexecutable_filter
```

示例公式：

```text
break_launch_low_3d:
  signal_date_definition = first_hit_within_window
  formula_window_trading_days = 3
  filter_signal_date = first trading day in [stratum_date+1, stratum_date+3]
                       where low < stratum_low_at_signal
  condition = low < stratum_low_at_signal
```

```text
break_ema20_after_launch_5d:
  signal_date_definition = first_hit_within_window
  formula_window_trading_days = 5
  filter_signal_date = first trading day in [stratum_date+1, stratum_date+5]
                       where close <= ema20
  condition = close <= ema20
```

```text
gap_fade_after_launch:
  signal_date_definition = instantaneous_day
  formula_window_trading_days = 5
  condition =
    open >= prior_close * (1 + thresholds.gap_up_min_ret)
    and close_location <= 0.35
    and close <= open
```

```text
upper_shadow_volume_failure:
  signal_date_definition = instantaneous_day
  formula_window_trading_days = 5
  condition =
    upper_shadow_pct >= 0.45
    and close_location <= 0.40
    and money_ratio_20 >= 1.50
```

```text
rank_evaporation_5d:
  signal_date_definition = first_hit_within_window
  formula_window_trading_days = 5
  filter_signal_date = first trading day in [stratum_date+1, stratum_date+5]
                       where rank evaporation condition is true
  condition =
    ret_rank_20d_market <= ret_rank_20d_market_at_stratum - thresholds.rank_drop
    and ret_rank_20d_market <= thresholds.rank_evaporation_floor
```

```text
industry_breadth_evaporation_5d:
  signal_date_definition = first_hit_within_window
  formula_window_trading_days = 5
  condition = industry_breadth_20d <= industry_breadth_20d_at_stratum - thresholds.industry_breadth_drop
```

```text
no_followthrough_5d:
  signal_date_definition = fixed_window_end
  formula_window_trading_days = 5
  filter_signal_date = stratum_date + 5 trading days
  condition =
    max(high over stratum_date+1 to stratum_date+5) <= stratum_close_at_signal * (1 + thresholds.min_followthrough_gain)
    and min(close over stratum_date+1 to stratum_date+5) < stratum_close_at_signal
```

```text
destructive_high_vol_3d:
  signal_date_definition = first_hit_within_window
  formula_window_trading_days = 3
  condition =
    atr20_pct >= q80_market
    and close_location <= 0.40
    and close < median20
```

```text
wide_stop_risk_no_add:
  signal_date_definition = instantaneous_day
  formula_window_trading_days = 5
  condition = close / invalidation_reference_price - 1 >= thresholds.max_stop_distance_for_new_risk
```

### 9.3 Failure Filter Denominator Contract

对每个 `(launch_stratum_scope, filter_variant)`，必须显式定义分母、机会窗口和 decision reference date。

#### 9.3.1 Opportunity window for all rows

每一条 `U` 中的 launch stratum row，无论是否触发 filter，都必须先生成同一套 opportunity 字段：

```text
filter_opportunity_start_date = next_trading_day(stratum_date)
filter_opportunity_deadline = trading_day_offset(stratum_date, formula_window_trading_days)

if filter_formula_observation_timing = close_derived:
    filter_opportunity_effective_deadline = next_trading_day(filter_opportunity_deadline)
else if filter_formula_observation_timing = intraday_observable:
    filter_opportunity_effective_deadline = filter_opportunity_deadline

filter_opportunity_deadline uses trading-day offset, not calendar-day offset.
```

Filter signal row：

```text
R = subset of U where filter_signal_occurs = true
    and filter_signal_date >= filter_opportunity_start_date
    and filter_signal_date <= filter_opportunity_deadline
```

Denominator decision reference date：

```text
if row in R:
    filter_decision_reference_date_for_denominator = filter_effective_date
else:
    filter_decision_reference_date_for_denominator = filter_opportunity_effective_deadline
```

这条规则解决未触发 filter 的样本没有 `filter_effective_date` 的问题。

Window / horizon truncation：

```text
if filter_opportunity_deadline is outside available trading calendar
   or filter_opportunity_effective_deadline is outside available PIT membership
   or target horizon required for denominator is unavailable:
      filter_window_truncated = true or filter_horizon_truncated = true
      row excluded from U for the affected metric
      row counted in p0_7_scope_completion_audit.csv
else:
      filter_window_truncated = false
      filter_horizon_truncated = false
```

Truncated rows must not be silently dropped; every exclusion needs `filter_window_missing_reason`.

#### 9.3.2 Eligible universe and labels

```text
U = launch_stratum_events in scope
    with valid signal search window
    with valid target horizon
    with PIT membership on filter_opportunity_effective_deadline

R = subset of U where filter_signal_occurs = true
    and filter_signal_date >= filter_opportunity_start_date
    and filter_signal_date <= filter_opportunity_deadline
N = subset of U where launch_nonwinner_primary = true
F = subset of U where launch_failure_primary = true
W50 = subset of U where stratum_future_50pct_high_120d = true
BW = subset of U where stratum_future_50pct_close_120d = true or stratum_future_100pct_high_240d = true
```

Pending-winner sets：

```text
W50_pending_for_denominator =
  W50 where target_not_reached_before_filter_decision_reference_date_for_denominator = true

BW_pending_for_denominator =
  BW where corresponding big-winner target not reached before filter_decision_reference_date_for_denominator

R_W50_false_reject =
  R ∩ W50 where target_not_reached_before_filter_effective_date_50pct_high_120d = true

R_BW_false_reject =
  R ∩ BW where corresponding big-winner target not reached before filter_effective_date
```

注意：

```text
target_not_reached_before_filter_effective_date_* only applies to R rows
target_not_reached_before_filter_decision_reference_date_for_denominator applies to every U row
```

#### 9.3.3 Metric definitions

```text
nonwinner_reject_recall = |R ∩ N| / |N|
failure_reject_recall = |R ∩ F| / |F|
reject_precision_nonwinner = |R ∩ N| / |R|
reject_precision_failure = |R ∩ F| / |R|

same_launch_stratum_nonwinner_prevalence = |N| / |U|
same_launch_stratum_failure_prevalence = |F| / |U|

reject_precision_nonwinner_lift_vs_scope_prevalence =
  reject_precision_nonwinner / same_launch_stratum_nonwinner_prevalence

reject_precision_failure_lift_vs_scope_prevalence =
  reject_precision_failure / same_launch_stratum_failure_prevalence

winner_false_reject_rate_among_eligible_winners =
  |R_W50_false_reject| / |W50_pending_for_denominator|

big_winner_false_reject_rate_among_eligible_winners =
  |R_BW_false_reject| / |BW_pending_for_denominator|

winner_coverage_loss_pending = |R_W50_false_reject| / |W50_pending_for_denominator|
winner_coverage_loss_total = |R_W50_false_reject| / |W50|
```

Sensitivity audit 必须额外报告：

```text
W50_pending_at_opportunity_deadline =
  W50 where target_not_reached_before_filter_opportunity_effective_deadline = true

winner_false_reject_rate_at_opportunity_deadline =
  |R_W50_false_reject| / |W50_pending_at_opportunity_deadline|
```

Unfiltered baseline 不存在 reject rate。禁止：

```text
nonwinner_reject_rate >= same_launch_stratum_baseline + x
```

正确比较：

```text
reject_precision_nonwinner_lift_vs_scope_prevalence
reject_precision_failure_lift_vs_scope_prevalence
nonwinner_reject_recall against thresholds.min_nonwinner_reject_recall
failure_reject_recall against thresholds.min_failure_reject_recall
winner_false_reject_rate against thresholds.max_winner_false_reject_rate
```

### 9.4 Drawdown Avoided 与 Matched-delay Baseline

Drawdown avoided 定义：

```text
future_drawdown_if_not_filtered =
  min return from filter_effective_price_reference to future low within thresholds.drawdown_audit_window

potential_drawdown_avoided_if_filter_effective =
  max(0, -future_drawdown_if_not_filtered)

median_drawdown_avoided_on_rejected_nonwinners =
  median(potential_drawdown_avoided_if_filter_effective for R ∩ N)
```

Filter-before-drawdown 定义：

```text
stratum_reference_price_for_drawdown_threshold = stratum_effective_price_reference

first_12pct_drawdown_date_from_stratum =
  first trading day after stratum_effective_date where
  low / stratum_reference_price_for_drawdown_threshold - 1 <= -0.12

first_20pct_drawdown_date_from_stratum =
  first trading day after stratum_effective_date where
  low / stratum_reference_price_for_drawdown_threshold - 1 <= -0.20

F12 = subset of U where first_12pct_drawdown_date_from_stratum exists within thresholds.drawdown_audit_window
F20 = subset of U where first_20pct_drawdown_date_from_stratum exists within thresholds.drawdown_audit_window

filter_before_12pct_drawdown_rate =
  |R ∩ F12 where filter_effective_date <= first_12pct_drawdown_date_from_stratum| / |R ∩ F12|

filter_before_20pct_drawdown_rate =
  |R ∩ F20 where filter_effective_date <= first_20pct_drawdown_date_from_stratum| / |R ∩ F20|
```

说明：

```text
filter_before_*_drawdown_rate is measured relative to stratum_effective_price_reference, not filter_effective_price_reference.
filter_effective_price_reference is used for drawdown_avoided audit after the filter becomes actionable.
If |R ∩ F12| or |R ∩ F20| is below threshold, the corresponding rate is null and the candidate cannot pass P1 gate using that metric.
```

Matched-delay：

```text
matched_delay_pseudo_reject_set_mode = exact_real_reject_count

For each (launch_stratum_scope, filter_variant) and each repeat:
  empirical_delay_distribution = distribution of filter_delay_trading_days among R
  pseudo_rejected_count_target = |R|
  sample pseudo_rejected_count_target rows from U using matched_delay.sample_with_replacement
  max_sample_per_variant controls runtime chunking / batching, not the statistical target count
  for each sampled row:
      sampled_delay = sample from empirical_delay_distribution with replacement
      pseudo_filter_signal_date = trading_day_offset(stratum_date, sampled_delay)
      pseudo_filter_effective_date follows the same observation_timing rule as the real filter
      if pseudo_filter_signal_date > filter_opportunity_deadline or horizon/PIT membership invalid:
          resample up to matched_delay.max_resample_attempts
      if still invalid:
          mark matched_delay_invalid_due_to_horizon_count += 1
  PR = valid pseudo-rejected rows for that repeat

matched_delay_filter_baseline computes reject precision, false reject and drawdown avoided on PR.

median_drawdown_avoided_vs_matched_delay =
  median_drawdown_avoided_on_rejected_nonwinners
  - matched_delay_median_drawdown_avoided_on_pseudo_rejected_nonwinners
```

Forbidden matched-delay modes unless explicitly enabled for sensitivity only：

```text
every_U_gets_pseudo_filter_date
pseudo_rejected_count_independent_of_conversion_rate
pseudo_dates_sampled_from_calendar_days
```

Default pseudo set size must match real filter conversion pressure exactly (`|PR_target| = |R|`); otherwise precision / false-reject comparisons are not comparable.

If implementation uses `max_sample_per_variant` as an approximation cap rather than a chunk size, it must set:

```text
matched_delay_approximation_used = true
matched_delay_exact_real_reject_count_used = false
```

and the matched-delay result is diagnostic-only; it cannot support P1 gating.

Matched-delay 必须记录：

```text
matched_delay_mode
matched_delay_pseudo_reject_set_mode
matched_delay_exact_real_reject_count_used
matched_delay_approximation_used
matched_delay_random_seed
matched_delay_n_repeats
matched_delay_sample_with_replacement
matched_delay_n_jobs
matched_delay_max_sample_per_variant
matched_delay_max_resample_attempts
matched_delay_pseudo_rejected_count_target
matched_delay_sample_count
matched_delay_valid_sample_count
matched_delay_invalid_due_to_horizon_count
matched_delay_bootstrap_mean
matched_delay_bootstrap_std
```

### 9.5 Failure Filter Leaderboard

`p0_7_failure_filter_leaderboard.csv` 至少包含：

```text
filter_family
filter_variant
filter_action
launch_stratum_scope
filter_event_count
filter_eligible_launch_count
filtered_launch_count
distinct_launch_episode_count
distinct_instrument_count
distinct_year_count
filter_conversion_rate
median_filter_delay_days
eligible_nonwinner_count
eligible_failure_count
eligible_pending_winner_count
eligible_pending_big_winner_count
filtered_nonwinner_count
filtered_failure_count
filtered_pending_winner_count
filtered_pending_big_winner_count
nonwinner_reject_recall
failure_reject_recall
reject_precision_nonwinner
reject_precision_failure
same_launch_stratum_nonwinner_prevalence
same_launch_stratum_failure_prevalence
reject_precision_nonwinner_lift_vs_scope_prevalence
reject_precision_failure_lift_vs_scope_prevalence
winner_false_reject_rate_among_pending_winners
big_winner_false_reject_rate_among_pending_winners
winner_coverage_loss_pending
winner_coverage_loss_total
median_drawdown_avoided_on_rejected_nonwinners
mean_drawdown_avoided_on_rejected_nonwinners
median_drawdown_avoided_vs_matched_delay
mean_drawdown_avoided_vs_matched_delay
filter_before_12pct_drawdown_rate
filter_before_20pct_drawdown_rate
matched_delay_reject_precision_nonwinner
matched_delay_winner_false_reject_rate
matched_delay_drawdown_avoided
instrument_year_filter_effect_lift
positive_unique_instrument_year_count
top1_instrument_contribution
top5_instrument_contribution
filter_observable_delay_days
filter_after_target_achieved_count
observability_leak_check_passed
p1_failure_filter_candidate
rejection_reason
```

P1 failure filter gate：

```text
filter_event_count >= thresholds.min_failure_filter_event_count
distinct_year_count >= thresholds.min_distinct_year_count_failure
distinct_instrument_count >= thresholds.min_distinct_instrument_count_failure
top1_instrument_contribution <= thresholds.max_top1_instrument_contribution
top5_instrument_contribution <= thresholds.max_top5_instrument_contribution
nonwinner_reject_recall >= thresholds.min_nonwinner_reject_recall
failure_reject_recall >= thresholds.min_failure_reject_recall
reject_precision_nonwinner_lift_vs_scope_prevalence >= thresholds.min_reject_precision_lift
reject_precision_failure_lift_vs_scope_prevalence >= thresholds.min_failure_precision_lift
winner_false_reject_rate_among_pending_winners <= thresholds.max_winner_false_reject_rate
big_winner_false_reject_rate_among_pending_winners <= thresholds.max_big_winner_false_reject_rate
winner_coverage_loss_pending <= thresholds.max_winner_coverage_loss_pending
winner_coverage_loss_total <= thresholds.max_winner_coverage_loss_total
median_drawdown_avoided_vs_matched_delay >= thresholds.min_drawdown_avoided_vs_matched_delay_pct
filter_before_12pct_drawdown_rate >= thresholds.min_before_12pct_drawdown_rate
filter_before_20pct_drawdown_rate >= thresholds.min_before_20pct_drawdown_rate
instrument_year_filter_effect_lift >= thresholds.min_instrument_year_lift
positive_unique_instrument_year_count >= thresholds.min_positive_unique_instrument_year_count
observability_leak_check_passed = true
```

---

## 10. P0.7C：Hold / Add-on Gate Discovery（deferred）

P0.7C 在第一实现批次不运行。本节作为第二实现批次 contract。

Hold gate 研究对象：

```text
在明确 exposure_model 的前提下，
哪些 T 日可观察状态说明 launch / continuation context 仍可继续持有或继续观察？
```

Add-on gate 研究对象：

```text
在已经存在 exposure 的前提下，
哪些 T 日可观察状态允许研究加仓，而不是作为首入场 trigger？
```

Hold / add-on baseline 必须绑定同一个 exposure model：

```text
same_launch_stratum_unconditional_hold_baseline
same_launch_family_unconditional_hold_baseline
same_lifecycle_context_unconditional_hold_baseline
matched_delay_hold_baseline
hold_gate_convertible_baseline
same_context_addon_baseline
matched_delay_addon_baseline
```

Add-on success label 不得包含 stop risk：

```text
add_on_success_primary =
  addon_future_20pct_high_60d
  and addon_drawdown_before_20pct_gain >= -0.10
```

`addon_to_stop_risk_pct` 只能作为 feasibility / eligibility / audit gate：

```text
addon_feasible_for_primary =
  addon_to_stop_risk_pct <= thresholds.max_addon_to_stop_risk_pct
  and addon_limit_like_open_flag = false
```

---

## 11. 去重、instrument-year 与 coverage

主榜去重：

```text
launch stratification primary unit = launch_episode_id + stratum_family + stratum_variant
failure filter primary unit = launch_stratum_event_id + filter_family + filter_variant
hold gate primary unit = launch_stratum_event_id + hold_gate_family + hold_gate_variant   # deferred
add-on gate primary unit = launch_stratum_event_id + addon_family + addon_variant         # deferred
```

同一 `(launch_stratum_event_id, family, variant)` 只能取 first valid event。

Instrument-year 必须报告：

```text
instrument_year_key = instrument + calendar_year(stratum_date)
positive_unique_instrument_year_count
instrument_year_lift_vs_all_launch
instrument_year_lift_vs_same_family
instrument_year_filter_effect_lift
```

任何只在 pooled event 上好看，但 instrument-year 不成立的方向，只能是 diagnostic。

Coverage 必须报告：

```text
winner_episode_coverage
winner_coverage_loss
pending_winner_coverage_loss
big_winner_coverage_loss
top1_instrument_contribution
top5_instrument_contribution
year_by_year_precision
industry_by_industry_precision
```

---

## 12. 输出文件

### 12.1 Required parquet cache

Full row-level panels 只要求 parquet cache：

```text
Explore9/outputs/cache/p0_7_launch_episode_panel.parquet
Explore9/outputs/cache/p0_7_launch_stratum_event_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_opportunity_panel.parquet
Explore9/outputs/cache/p0_7_failure_filter_event_panel.parquet
```

### 12.2 Required CSV / JSON reports

报告 CSV 只输出 summary、dictionary、formula matrix、leaderboard、audit 与 schema：

```text
Explore9/outputs/reports/p0_7_feature_dictionary.csv
Explore9/outputs/reports/p0_7_formula_token_coverage_audit.csv
Explore9/outputs/reports/p0_7_launch_formula_matrix.csv
Explore9/outputs/reports/p0_7_launch_episode_summary.csv
Explore9/outputs/reports/p0_7_launch_stratum_event_summary.csv
Explore9/outputs/reports/p0_7_launch_stratification_leaderboard.csv
Explore9/outputs/reports/p0_7_launch_stratification_rejected.csv
Explore9/outputs/reports/p0_7_direct_launch_baseline_by_stratum.csv
Explore9/outputs/reports/p0_7_failure_filter_formula_matrix.csv
Explore9/outputs/reports/p0_7_failure_filter_opportunity_summary.csv
Explore9/outputs/reports/p0_7_failure_filter_event_summary.csv
Explore9/outputs/reports/p0_7_failure_filter_leaderboard.csv
Explore9/outputs/reports/p0_7_failure_filter_rejected.csv
Explore9/outputs/reports/p0_7_failure_filter_false_reject_audit.csv
Explore9/outputs/reports/p0_7_failure_filter_drawdown_reduction_audit.csv
Explore9/outputs/reports/p0_7_matched_delay_filter_baseline.csv
Explore9/outputs/reports/p0_7_lifecycle_transition_audit.csv
Explore9/outputs/reports/p0_7_stratum_observability_audit.csv
Explore9/outputs/reports/p0_7_regime_breakdown.csv
Explore9/outputs/reports/p0_7_industry_breakdown.csv
Explore9/outputs/reports/p0_7_instrument_year_breakdown.csv
Explore9/outputs/reports/p0_7_dedup_audit.csv
Explore9/outputs/reports/p0_7_scope_completion_audit.csv
Explore9/outputs/reports/p0_7_row_panel_schema.csv
Explore9/outputs/reports/p0_7_run_manifest.json
Explore9/outputs/reports/explore9_p0_7ab_launch_failure_report.md
```

输出纪律：

```text
full row-level panels are required as parquet cache only
full row-level CSV reports are not required and should not be generated by default
CSV reports should be summaries, dictionaries, formula matrices, leaderboards, audits, and schema files
optional debug row CSV may be generated only when config.output.debug_export_row_csv = true and capped by output.debug_max_rows_per_panel
```

### 12.3 P0.7C deferred outputs

P0.7C 第二实现批次新增：

```text
Explore9/outputs/cache/p0_7_hold_gate_event_panel.parquet
Explore9/outputs/cache/p0_7_addon_gate_event_panel.parquet
Explore9/outputs/reports/p0_7_exposure_model_audit.csv
Explore9/outputs/reports/p0_7_hold_gate_formula_matrix.csv
Explore9/outputs/reports/p0_7_hold_gate_leaderboard.csv
Explore9/outputs/reports/p0_7_hold_gate_rejected.csv
Explore9/outputs/reports/p0_7_hold_gate_winner_coverage_audit.csv
Explore9/outputs/reports/p0_7_addon_gate_formula_matrix.csv
Explore9/outputs/reports/p0_7_addon_gate_leaderboard.csv
Explore9/outputs/reports/p0_7_addon_gate_rejected.csv
Explore9/outputs/reports/p0_7_addon_execution_feasibility_audit.csv
```

---

## 13. 报告要求

`explore9_p0_7ab_launch_failure_report.md` 必须用中文撰写，并包含：

1. P0.7 为什么不是 P0.6 重跑。
2. 为什么第一实现批次只做 P0.7A + P0.7B。
3. Launch episode 与 stratum event 覆盖。
4. Later-in-episode lifecycle state 是否被禁止回写 first stratum。
5. Launch stratification leaderboard。
6. Launch stratum 的 `declared_stratum_role` 与 `recommended_action_class_after_evaluation` 分离审计。
7. Failure filter family matrix。
8. Failure filter denominator audit。
9. Failure filter false reject audit，并排除 target 已经达成样本。
10. 无 filter signal 样本的 denominator reference date 审计。
11. first-hit vs fixed-window signal date contract 审计。
12. Drawdown avoided vs matched-delay audit。
13. Instrument-year / year-by-year / industry stability。
14. 哪些方向进入 P1 launch stratification / P1 failure filter refine。
15. 哪些方向只能保留 diagnostic。
16. 是否仍不得进入 Explore10。

报告结论枚举：

```text
recommendation = proceed_to_p1_launch_stratification_refine
recommendation = proceed_to_p1_failure_filter_refine
recommendation = continue_p0_7ab_discovery
recommendation = entry_not_solved_but_launch_failure_direction_valid
recommendation = stop_due_to_no_stable_launch_failure_structure
```

不得输出：

```text
recommendation = proceed_to_explore10_backtest
recommendation = proceed_to_frozen_strategy
recommendation = p1_entry_trigger_from_p0_7_hold_gate
recommendation = proceed_to_p1_hold_gate_refine       # unless P0.7C has run
recommendation = proceed_to_p1_addon_gate_refine      # unless P0.7C has run
```

---

## 14. 成功标准

### 14.1 P0.7AB 最低成功标准

- 生成 `launch_episode_panel`。
- 生成 `launch_stratum_event_panel`。
- 生成 `failure_filter_opportunity_panel`。
- 生成 `failure_filter_event_panel`。
- 测试 10 类 launch stratum family，总 variant 不少于 20。
- 测试 10 类 failure filter family，总 variant 不少于 20。
- 每个 family 都有公式、阈值、declared role、recommended action evaluation rule、eligibility。
- 所有 `declared_stratum_role` 都通过 `stratum_date` T 日可观察性审计。
- `recommended_action_class_after_evaluation` 只能在 leaderboard / report 中生成。
- Later lifecycle state 不得重写 first launch stratum。
- Failure filter denominator 显式区分 recall、precision、prevalence、false reject、drawdown avoided。
- 未触发 filter 的样本也有 `filter_decision_reference_date_for_denominator`。
- False reject 必须排除 target already reached before effective date。
- 每个 failure filter formula 都声明 `signal_date_definition`。
- Matched-delay baseline 必须可复现，并有 runtime controls。
- 所有主榜报告 instrument-year lift。
- 所有主榜报告 winner coverage / coverage loss。
- Full row-level panels 只作为 parquet cache。
- 不输出 Explore10 backtest 建议。
- 不输出 P1 hold/add-on gate 结论。

### 14.2 P0.7C 最低成功标准（deferred）

- 生成 `hold_gate_event_panel` 和 `add_on_gate_event_panel`。
- 所有 hold/add-on event 都有 exposure model。
- `hidden_entry_filter_used_count = 0`。
- hold gate 报告 pending winner false reject。
- add-on gate 报告 stop distance / wide stop / late acceleration overlap。
- `addon_to_stop_risk_pct` 不进入 success label。

---

## 15. 配置建议

建议新增第一实现批次配置：

```text
Explore9/configs/launch_failure_p0_7ab.yaml
```

配置 sketch：

```yaml
profile_name: p0_7ab_launch_failure
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30

scope:
  run_p0_7a_launch_stratification: true
  run_p0_7b_failure_filter: true
  run_p0_7c_hold_gate: false
  run_p0_7c_addon_gate: false

reuse:
  p0_label_panel: true
  p0_5_feature_reference: true
  p0_6_launch_event_panel: true
  p0_6_entry_results_for_selection: false

windows:
  launch_episode_collapse_gap_days: 20
  failure_filter_windows: [1, 3, 5, 10, 20]
  max_filter_signal_wait_trading_days: 20
  hold_gate_windows: [3, 5, 10, 20, 40]
  addon_gate_windows: [5, 10, 20, 40, 60]

thresholds:
  # common stability
  min_distinct_year_count_launch: 5
  min_distinct_year_count_failure: 5
  min_distinct_instrument_count_launch: 50
  min_distinct_instrument_count_failure: 50
  min_positive_unique_instrument_year_count: 20
  min_winner_episode_coverage: 0.05
  max_top1_instrument_contribution: 0.15
  max_top5_instrument_contribution: 0.35
  min_instrument_year_lift: 1.00

  # launch stratification
  min_launch_stratum_event_count: 200
  min_launch_lift_vs_all: 1.10
  min_launch_lift_vs_same_family: 1.05
  max_false_positive_rate_tolerance: 0.00
  max_drawdown_worsening_tolerance: 0.02

  # failure filter denominator / precision / recall
  min_failure_filter_event_count: 200
  min_nonwinner_reject_recall: 0.20
  min_failure_reject_recall: 0.20
  min_reject_precision_lift: 1.05
  min_failure_precision_lift: 1.05
  max_winner_false_reject_rate: 0.25
  max_big_winner_false_reject_rate: 0.15
  max_winner_coverage_loss_pending: 0.30
  max_winner_coverage_loss_total: 0.20
  min_drawdown_avoided_vs_matched_delay_pct: 0.00
  min_before_12pct_drawdown_rate: 0.50
  min_before_20pct_drawdown_rate: 0.50
  failure_drawdown_threshold: 0.12
  drawdown_audit_window: 60

  # formula thresholds
  near_limit_threshold: 0.085
  gap_up_min_ret: 0.03
  rank_drop: 0.25
  rank_evaporation_floor: 0.50
  industry_breadth_drop: 0.15
  min_followthrough_gain: 0.05
  max_stop_distance_for_new_risk: 0.15

  # P0.7C deferred thresholds
  min_hold_gate_event_count: 200
  min_addon_event_count: 100
  min_distinct_year_count_hold: 5
  min_distinct_year_count_addon: 4
  min_distinct_instrument_count_hold: 50
  min_distinct_instrument_count_addon: 40
  max_hold_gate_winner_coverage_loss: 0.35
  max_hold_gate_false_reject_winner_rate: 0.30
  max_addon_to_stop_risk_pct: 0.15
  max_addon_wide_stop_rate: 0.40
  max_late_acceleration_overlap_rate: 0.50
  min_addon_success_lift_vs_same_context: 1.05

matched_delay:
  enabled: true
  random_seed: 20260505
  n_repeats: 100
  sample_with_replacement: false
  n_jobs: 24
  max_sample_per_variant: 20000   # runtime chunk / batching control; does not change pseudo_rejected_count_target by default
  max_resample_attempts: 10
  pseudo_reject_set_mode: exact_real_reject_count
  exact_real_reject_count_required_for_p1: true

output:
  full_row_panels_as_parquet_cache: true
  full_row_panels_as_csv_reports: false
  debug_export_row_csv: false
  debug_max_rows_per_panel: 5000

execution:
  default_formula_observation_timing: close_derived
  default_effective_date_execution: next_trading_day_open
  default_effective_price_reference: next_open
  intraday_same_day_effective_allowed_only_if_declared: true
  same_close_proxy_used_in_main_leaderboard: false
  next_open_used_for_filter_execution_audit: true
  next_open_used_for_hold_gate_execution_audit: true
  next_open_used_for_addon_execution_audit: true

ranking:
  instrument_year_required: true
  dedup_event_required: true
  winner_coverage_required: true
  false_reject_audit_required: true
  observability_leak_check_required: true
  failure_filter_denominator_audit_required: true
  declared_role_vs_recommended_action_split_required: true
  formula_token_coverage_audit_required: true
  launch_baseline_schema_contract_required: true
  matched_delay_conversion_rate_matched_required: true
```

---

## 16. 建议命令

```bash
uv run python Explore9/scripts/run_explore9.py profile-p0-7ab --config Explore9/configs/launch_failure_p0_7ab.yaml
uv run python Explore9/scripts/run_explore9.py report-p0-7ab --config Explore9/configs/launch_failure_p0_7ab.yaml
```

不得从 P0.7AB 直接进入 Explore10。只有当 P0.7AB 的 launch stratification 或 failure filter 通过对应 P1 gate，才允许进入：

```text
P1 launch stratification refine
P1 failure filter refine
```
