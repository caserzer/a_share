# EP2 Requirement 05: Daily Continuation Value and Profit-Protection Policy

> 文件名：`requirement_05_daily_continuation_profit_protection_policy.md`
> 阶段：`EP2 Requirement 05`
> 标题：Daily Continuation Value and Profit-Protection Policy
> 状态：staged requirement draft; first implementation is deterministic-prephase-only; full model stage is a later gated run
> 生成日期：2026-05-09
> 重要说明：R05 是 R04 固定持有期失败后的 post-exposure continuation / risk-budget 阶段，不是新的 entry、不是新的 label search、不是完整组合回测、不是策略冻结。

---

## 0. 一句话结论

Requirement 05 只做一件事，但必须分阶段执行：

```text
在冻结 R01 / R02 / R03 的 probe / confirm-add / fast-fail exposure 合同后，
构造 post-exposure daily state panel，
先用 deterministic-only profit-protection policy 做低自由度验证，
再用 R04 regime audit 判断 R04 失败是否主要来自 regime mismatch，
只有在样本量、deterministic edge、regime audit 都通过后，
才允许启动每日 continuation model / policy grid。
```

R05 的核心转向是：

```text
不再问：应该固定持有 H20 / H60 / H120 吗？
而是问：每一个可观察交易日，继续持有是否仍然有正边际价值？
```

时间在 R05 中只是：

```text
max_holding_days safety cap
```

不是 selection target。

当前 R03/R04 已知样本规模较小：

```text
validation exposed episodes = 104
validation 50h120 big-winner episodes = 43
robustness exposed episodes = 149
robustness 50h120 big-winner episodes = 127
```

因此本 requirement 明确禁止在第一版直接展开 3 个模型 + 大 policy grid 的 full R05。第一版默认执行模式是：

```text
implementation_mode = deterministic_prephase_only
full_model_stage_allowed = evaluated
full_model_stage_executed = false
```

第一版必须只跑：

```text
Run 1:
  R05-pre deterministic-only mini-phase
  R04 regime audit
  sample-power audit
```

只有 Run 1 明确输出 `full_model_stage_allowed = true` 后，后续才允许用独立
Run 2 启动 full model stage：

```text
Run 2:
  implementation_mode = full_model_stage
  full_model_stage_allowed = true
  full_model_stage_executed = true
```

`run_R05_full_model_stage` 不是 R05 的最终研究结论，只是 R05 内部 stage
transition 建议。它不能被解释为 R05 已经通过，也不能替代 R06 go/no-go。

---

## 1. 背景与阶段来源

### 1.1 R01-R03 已经证明的事实

R01 / R02 / R03 已经完成并通过：

```text
Requirement 01: passed, 20/20 gates
Requirement 02: passed, 27/27 gates
Requirement 03: passed, 17/17 gates
```

R01 冻结：

```text
primary_label_id = confirm_h10_u10_d06_conservative_fail
frozen_baseline_id = probe_with_simple_stop
```

R02 冻结：

```text
hazard_schedule_id = hazard_probe_with_simple_stop
selected_threshold = 0.3205667777673395
selected_stop_risk_ceiling = 0.27410397287415667
```

R03 冻结：

```text
schedule_bridge_id = hazard_probe_confirm_add_fast_fail
probe_weight = 0.30
confirm_add_weight = 0.70
full_weight_after_confirm = 1.00
confirm_add window = probe + 1 to probe + 3 trading days
fast_fail_drawdown = -0.06
natural_exit H = 10
```

R03 的阶段性含义：

```text
低频 hazard probe + deterministic confirm_add 可以在 validation / robustness 上提高短周期 after-cost return，
且 EP2 exposure 大部分不是 BaseRate primary TopK 的简单复刻。
```

但 R03 不是完整策略，最大未解决问题是：

```text
big-winner strict capture 很低，holding / exit 未解决。
```

### 1.2 R04 的负向结论

R04 已经完成，但没有任何 promoted schedule。

R04 结论：

```text
validation_status = failed_tail_risk
next_phase_proceed_status = failed_tail_risk
recommendation = reframe_EP2_as_risk_filter_overlay
selected_requirement_04_schedule_id = null
```

R04 验证了两件事：

```text
1. 固定延长持有 H20 / H60 / H120 可以提高部分 validation strict big-winner capture；
2. 但所有 promotion-eligible schedule 都在 validation tail-risk / capital occupancy / mean return gate 上失败。
```

R04 的关键解释：

```text
固定 H 持有期把所有 confirmed episode 一视同仁；
真实问题不是 H 取值不够好，
而是每个 episode 的 continuation value 会随着价格、利润垫、回撤、成交和市场状态每日变化。
```

R04 后的正确研究方向不是继续扩 H matrix，而是：

```text
post-exposure daily continuation value
profit protection
giveback risk
partial exit / full exit / tighten stop policy
```

---

## 2. 阶段定位与执行顺序

R05 是 R04 之后的 post-exposure continuation / profit-protection 阶段。

R05 分为三个执行层级。

### 2.1 R05-pre: deterministic-only mini-phase

R05-pre 是强制第一阶段。它只跑 deterministic profit-protection baselines，不训练模型，不展开 model policy grid。

R05-pre 可以做：

```text
1. replay R03_original_H10；
2. replay only the two cheap R04 diagnostic references explicitly listed in Section 11；
3. build post-exposure state panel；
4. evaluate exactly three deterministic profit-protection rules；
5. compare deterministic rules against R03 and matched exposure-days random exit；
6. emit deterministic-only proceed / stop status。
```

R05-pre 不得重新 replay R04 的完整 H matrix。`R04_confirmed_H60` 和
`R04_confirmed_H120` 只能从 R04 frozen report 中作为 read-only comparison rows
读取，不得成为 R05-pre simulator 的执行范围。

R05-pre 的目的不是证明最终策略，而是用最小工程量回答：

```text
post-exposure profit-protection policy 这个方向是否有足够 edge，
值得继续启动模型化 continuation policy。
```

### 2.2 R04-regime audit: mandatory pre-model audit

R05-pre 之后必须做 R04-regime audit。原因是 R04 中 H20 / winner-state 在 robustness 上明显好于 validation，但 validation 失败。

R04-regime audit 只能 replay / attribution，不允许调参。它要回答：

```text
R04 失败是因为 fixed-H / winner-state 规则本身错误，
还是因为 validation split 对 holding extension 是不利 regime？
```

如果 audit 显示 regime effect 是主因，R05 full model 不得直接启动；下一阶段应改写为 regime-conditional holding / regime holdout requirement。

### 2.3 Conditional full model stage

只有以下条件全部满足，Run 1 才能把 `full_model_stage_allowed` 置为 true：

```text
1. deterministic-only mini-phase 至少有一个 deterministic policy 通过 validation Track A 或 Track B；
2. deterministic policy 在 robustness 上没有 material reversal；
3. R04-regime audit 没有输出 `regime_mismatch_status = blocking`；
4. sample-power audit 通过 full-model minimum-sample gate；
5. policy-grid candidate count 不超过预注册上限。
```

Full R05 model stage 必须在后续独立 Run 2 中执行。Run 2 可以做：

```text
1. 构造 R03 exposure 之后的每日持仓状态面板；
2. 定义 continuation reward / giveback risk / hold-vs-exit delta labels；
3. 训练小型 continuation / risk 模型；
4. 用预注册 policy 将模型输出映射为 hold_full / partial_exit / full_exit / tighten_stop；
5. 与 R03、R04 diagnostic baselines、matched exposure-days random exit 做对照；
6. 判断 EP2 是否更适合作为 profit-protection / risk-filter overlay 或 short-horizon event sleeve。
```

如果 R05-pre 或 sample-power audit 不通过，full model stage artifacts 可以省略或以
`not_run` stub 形式生成；validator 必须接受 deterministic-only terminal status，
但必须确认没有偷偷训练模型、展开 model grid 或使用 model prediction 做 selection。

R05 不做：

```text
1. 不重新选择 primary label；
2. 不修改 R02 hazard threshold；
3. 不修改 R02 stop-risk ceiling；
4. 不修改 R03 probe / confirm_add rule；
5. 不新增 entry signal；
6. 不新增 launch detector；
7. 不训练新的 entry model；
8. 不做 Alpha158 path-to-primitive；
9. 不回到行业 LGBM；
10. 不用 BaseRate row-level 数据做 selection；
11. 不做完整组合年化收益比较；
12. 不输出 P1 strategy；
13. 不 freeze strategy。
```

R05 的有效结论只能是：

```text
run_R05_full_model_stage
proceed_to_regime_conditional_requirement
proceed_to_R06_baserate_integration_as_event_sleeve
proceed_to_R06_baserate_integration_as_risk_filter_overlay
keep_EP2_as_short_horizon_event_sleeve
reframe_EP2_as_profit_protection_overlay
stop_big_winner_holding_research
stop_due_to_no_continuation_policy_edge
stop_due_to_insufficient_selection_power
```

R05 禁止输出：

```text
candidate_for_P1_strategy = true
validated_strategy = true
clean_oos_proven_rule = true
freeze_strategy = true
selected_final_model = true
portfolio_level_outperformance_claim = true
```

---

## 3. Entry Gate

R05 可以开始，当且仅当：

```text
1. R01 passed；
2. R02 passed；
3. R03 passed；
4. R04 completed with failed_tail_risk or equivalent no-promoted-holding-schedule status；
5. R04 did not promote any fixed-H or winner-state holding schedule；
6. R05 runner can replay R03 action / exposure panel exactly on validation and robustness.
```

最低 R03 frozen state：

```yaml
requirement_03:
  validation_status: passed
  next_phase_proceed_status: passed
  primary_label_id: confirm_h10_u10_d06_conservative_fail
  frozen_baseline_id: probe_with_simple_stop
  hazard_schedule_id: hazard_probe_with_simple_stop
  schedule_bridge_id: hazard_probe_confirm_add_fast_fail
  selected_threshold: 0.3205667777673395
  selected_stop_risk_ceiling: 0.27410397287415667
```

最低 R04 state：

```yaml
requirement_04:
  validation_status: failed_tail_risk
  next_phase_proceed_status: failed_tail_risk
  recommendation: reframe_EP2_as_risk_filter_overlay
  selected_requirement_04_schedule_id: null
```

如果 R03 不再通过，停止。
如果 R04 出现 promoted schedule，R05 必须重新写 requirement，不能直接沿用本文件。

### 3.1 Sample-Power Entry Gate

R05 必须先生成：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_sample_power_audit.csv
```

最低字段：

```text
split
exposed_episode_count
big_winner_episode_count_50h120
actionable_big_winner_episode_count_50h120
baseline_strict_captured_big_winner_count_50h120
actionable_uncaptured_big_winner_count_50h120
state_row_count
confirmed_exposed_episode_count
deterministic_candidate_count
model_candidate_count
estimated_free_parameter_count
events_per_candidate
events_per_free_parameter
deterministic_stage_allowed
full_model_stage_allowed
full_model_stage_executed
failure_reason
```

Sample-power gates：

```yaml
sample_power:
  deterministic_stage_min_validation_exposed_episodes: 80
  deterministic_stage_min_validation_big_winner_50h120: 30
  deterministic_stage_min_validation_actionable_big_winner_50h120: 10
  full_model_min_validation_exposed_episodes: 180
  full_model_min_validation_big_winner_50h120: 80
  full_model_min_validation_actionable_big_winner_50h120: 40
  full_model_min_events_per_free_parameter: 10
  max_full_model_policy_candidates: 32
  max_deterministic_policy_candidates: 3
```

`deterministic_candidate_count` 的分母写死为三条 deterministic
profit-protection rules：

```text
profit_lock_rule_simple
trailing_stop_rule_simple
partial_exit_after_profit_rule
```

以下对象不计入 `deterministic_candidate_count`：

```text
R03_original_H10_replay
R04 diagnostic replays
matched_exposure_days_random_exit
read-only R04 comparison rows
```

Actionable big-winner 定义：

```text
big-winner episode with positive R03 exposure before first_50pct_target_date
```

Actionable uncaptured big-winner 定义：

```text
actionable_big_winner_episode_count_50h120
- baseline_strict_captured_big_winner_count_50h120
```

Track A 的 winner-capture improvement 仍使用 total 50h120 big-winner count
计算门槛，但 gate audit 必须同时报告 actionable 分母。若
`actionable_uncaptured_big_winner_count_50h120` 小于 Track A 所需最小新增 capture
数量，则 Track A fail closed，避免在理论上无法改善的样本上做 selection。

当前已知 R03 validation exposure / winner 数量可以允许 R05-pre deterministic-only mini-phase，但不足以默认允许 full model stage。除非 sample-power audit 用当前 artifacts 证明上述 full-model gates 通过，否则：

```text
full_model_stage_allowed = false
full_model_stage_executed = false
model training = forbidden
model policy grid expansion = forbidden
terminal status may be stop_due_to_insufficient_selection_power or proceed_to_regime_conditional_requirement
```

---

## 4. Frozen Inputs

R05 只允许读取以下输入根：

```text
ep2/engineering_baseline/outputs/
ep2/outputs/requirement_01_label_and_baseline_freeze/
ep2/outputs/requirement_02_hazard_timing_model/
ep2/outputs/requirement_03_schedule_bridge/
ep2/outputs/requirement_04_holding_exit_winner_capture_extension/  # diagnostic reference only
data/qlib/cn_data_pit/  # holding path / exit execution only
```

R04 artifacts 的权限：

```text
R04 artifacts may be used as diagnostic background and baseline comparison only.
R04 variants must not be used to choose R05 model features, R05 labels, R05 thresholds, or R05 policy candidates.
```

BaseRate 权限：

```text
BaseRate row-level prediction / order / trade / portfolio-return panels are forbidden in R05 selection.
BaseRate may be mentioned only as future R06 integration target.
```

禁止输入：

```text
1. Explore9 / Explore10 row-level caches；
2. new provider pull；
3. BaseRate row-level panels；
4. unregistered Alpha158 feature bank；
5. robustness rows for selecting R05 model / threshold / policy；
6. future target labels as predictive features；
7. R04 diagnostic counterfactual as promoted policy.
```

---

## 5. Output Layout

所有 R05 输出必须写入：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/
```

目录结构：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/
  cache/
  reports/
  manifests/
```

R05 不得覆盖 R01 / R02 / R03 / R04 / engineering baseline / BaseRate 输出。

---

## 6. Command Surface

最低命令面：

```bash
uv run python ep2/scripts/run_requirement_05_continuation_policy.py \
  --config ep2/configs/requirement_05_daily_continuation_profit_protection_policy.yaml

uv run python ep2/scripts/validate_requirement_05_continuation_policy.py \
  --config ep2/configs/requirement_05_daily_continuation_profit_protection_policy.yaml
```

Runner 必须生成当前执行阶段对应的 row-level cache、reports 和 manifest。Full model
stage 未获准启动时，runner 不得生成 trained prediction panel；model 相关 report 必须
缺席并在 artifact authority 中标为 `not_required_stage_disabled`，或生成
`not_run` stub。
Validator 必须 fail closed on missing artifacts、schema violations、frozen-input hash drift、feature-asof violation、R03 replay mismatch、robustness leakage、policy selection drift、BaseRate leakage、gate contradiction。

---

## 7. Sample Unit and Split Discipline

### 7.1 Primary row unit

R05 的 primary row unit 是：

```text
one row per launch_episode_id + state_signal_date + active_position_state
```

即：

```text
R03 first exposure 或 confirm_add 后，每一个仍有正 exposure 的可观察交易日。
```

R05 不允许对没有 R03 exposure 的 episode 创建 continuation state row。

### 7.2 State dates

定义：

```text
state_signal_date = close-derived state observation date
action_effective_date = next_trading_day(state_signal_date)
action_execution_price = open[action_effective_date]
```

所有 predictive features 必须满足：

```text
feature_asof_date <= state_signal_date
```

禁止：

```text
1. 使用 action_effective_date high / low / close / volume / money 作为 feature；
2. 使用 action_effective_date intraday path 作为 action decision input；
3. 使用 future target / post-exit outcome 作为 feature；
4. same-close exit / partial-exit / tighten-stop transition。
```

### 7.3 Label window

Continuation labels 从 `action_effective_date` 开始计算：

```text
label_window_start = action_effective_date
label_window_K = [action_effective_date, trading_day_offset(action_effective_date, K-1)]
label_window_includes_action_effective_date_high_low = true
```

因为 action_effective_date next-open 后，后续 high / low / close 已经属于持仓路径。

### 7.4 Split discipline

R05 使用 R03 split：

```text
train
validation
robustness
```

规则：

```text
train: train model and fit calibration only
validation: select model threshold / policy candidate only
robustness: holdout only, no selection
```

Robustness 不得用于：

```text
1. model family selection；
2. feature selection；
3. threshold selection；
4. policy selection；
5. action-space expansion；
6. fallback rule changes。
```

---

## 8. Post-Exposure Daily State Panel

R05 必须先生成：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_post_exposure_state_panel.parquet
```

最低 schema：

```text
launch_episode_id
instrument
split
state_signal_date
action_effective_date
action_execution_price
state_row_id

r03_first_exposure_signal_date
r03_first_exposure_execution_date
r03_first_exposure_price
r03_confirm_add_signal_date
r03_confirm_add_execution_date
r03_confirm_add_price
current_exposure_weight_before_action
active_position_state

has_probe_entry_executed
has_confirm_add_executed
days_since_first_exposure
days_since_confirm_add
remaining_days_to_R03_H10_natural_exit

current_close
current_return_from_first_exposure
current_return_from_confirm_add
current_unrealized_return_weighted
max_favorable_excursion_since_first_exposure
max_adverse_excursion_since_first_exposure
post_confirm_high_to_date
drawdown_from_post_confirm_high
giveback_from_peak_profit
current_profit_cushion
distance_to_first_exposure_price
distance_to_confirm_add_price

active_stop_floor
active_stop_source
sell_executable_next_open
blocked_sell_reason_next_open
buy_or_add_executable_next_open
blocked_buy_reason_next_open

r02_P_target_first_at_probe
r02_P_stop_first_at_probe
r02_P_neither_at_probe
r02_score_probe_day_at_probe
r02_selected_threshold
r02_selected_stop_risk_ceiling

feature_asof_date
feature_asof_violation_flag
```

State panel 不得包含：

```text
future_label
future_return
future_drawdown
first_50pct_target_date
first_100pct_target_date
post_action_effective_intraday_feature
```

这些只允许出现在 label / evaluation panel。

---

## 9. Label and Metric Dictionary

R05 必须生成：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_label_metric_dictionary.csv
```

最低字段：

```text
label_or_metric_name
label_or_metric_type
reference_date_field
reference_price_field
horizon_trading_days
formula_text
sign_convention
used_for_training
used_for_validation_selection
used_for_robustness_gate
used_for_diagnostic_only
```

### 9.1 Continuation reward labels

定义：

```text
D = action_effective_date
P_D = action_execution_price
K ∈ {5, 10, 20}
```

```text
future_high_return_Kd_from_action =
  max(high over [D, D+K-1]) / P_D - 1

future_close_return_Kd_from_action =
  close[D+K-1] / P_D - 1

profit_extension_Kd =
  future_high_return_Kd_from_action >= thresholds.profit_extension_target_Kd
```

默认 targets：

```yaml
profit_extension_target:
  K5: 0.04
  K10: 0.06
  K20: 0.10
```

### 9.2 Giveback / adverse-risk labels

```text
future_low_return_Kd_from_action =
  min(low over [D, D+K-1]) / P_D - 1

adverse_drawdown_Kd =
  future_low_return_Kd_from_action <= -thresholds.adverse_drawdown_Kd
```

默认 drawdown thresholds：

```yaml
adverse_drawdown:
  K5: 0.04
  K10: 0.06
  K20: 0.08
```

Profit giveback：

```text
peak_profit_reference_price = max(high observed from first exposure through state_signal_date)
future_min_low_Kd = min(low over [D, D+K-1])

giveback_from_peak_Kd =
  future_min_low_Kd / peak_profit_reference_price - 1

giveback_event_Kd =
  giveback_from_peak_Kd <= -thresholds.giveback_from_peak_Kd
```

### 9.3 Hold-vs-exit delta

Exit-now reference：

```text
exit_now_after_cost_return = realized return if current exposure is liquidated at action_execution_price
```

Hold-K reference：

```text
hold_K_after_cost_return = realized return if current exposure is held to close or next-open exit at D+K-1,
using the same cost model and no additional policy action.
```

Incremental delta：

```text
hold_vs_exit_delta_Kd = hold_K_after_cost_return - exit_now_after_cost_return
```

Primary training targets：

```text
continuation_reward_label = profit_extension_10d
continuation_risk_label = adverse_drawdown_10d or giveback_event_10d
hold_vs_exit_delta_label = hold_vs_exit_delta_10d
```

### 9.4 Big-winner capture metrics

R05 must preserve R04 definitions for strict / exposure-weighted / partial capture.

Strict capture：

```text
strict_capture_50h120 =
  episode is frozen 50h120 big winner
  and schedule exposure weight at first_50pct_target_date open-effective state > 0
```

Exposure-weighted capture：

```text
exposure_weighted_capture_50h120 =
  sum(exposure_weight_at_first_50pct_target_date for frozen 50h120 big-winner episodes)
  / frozen_50h120_big_winner_episode_count
```

Partial capture：

```text
partial_capture_50h120 =
  episode is frozen 50h120 big winner
  and schedule had positive exposure before first_50pct_target_date
```

Big-winner target dates must come from the same frozen target authority used in R04, including PIT hash scope through launch + 240 trading days if recomputation is required.

---

## 10. Feature Dictionary and As-Of Discipline

R05 必须生成：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_feature_dictionary.csv
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_feature_asof_audit.csv
```

### 10.1 Allowed feature families

R05 allowed feature families：

```text
1. position_state
2. path_state
3. R02_frozen_probe_scores
4. recent_price_volume_state
5. market_context_light
6. industry_context_light
7. execution_availability
```

Allowed examples：

```text
position_state:
  days_since_first_exposure
  days_since_confirm_add
  current_exposure_weight
  current_return_from_first_exposure
  current_return_from_confirm_add
  current_profit_cushion

path_state:
  max_favorable_excursion_since_first_exposure
  max_adverse_excursion_since_first_exposure
  drawdown_from_post_confirm_high
  giveback_from_peak_profit
  distance_to_first_exposure_price
  distance_to_confirm_add_price

R02_frozen_probe_scores:
  r02_P_target_first_at_probe
  r02_P_stop_first_at_probe
  r02_P_neither_at_probe
  r02_score_probe_day_at_probe

recent_price_volume_state:
  ret_1d / ret_3d / ret_5d as of state_signal_date
  close_location_5d
  volume_ratio_5d
  money_ratio_5d
  atr_pct_10d

market_context_light:
  market_ret_5d
  market_volatility_20d
  market_breadth_20d

industry_context_light:
  industry_ret_5d
  industry_breadth_20d
  stock_rank_within_industry_20d

execution_availability:
  sell_executable_next_open
  blocked_sell_reason_next_open
```

Forbidden features：

```text
1. action_effective_date high / low / close / volume / money；
2. future target dates；
3. future capture labels；
4. BaseRate scores / orders / trades；
5. R04 selected schedule outcome；
6. R04 promotion gate result；
7. label outcomes from D onward；
8. new Alpha158 feature bank；
9. same-day close after action execution.
```

### 10.2 As-of rule

All predictive features：

```text
feature_asof_date <= state_signal_date
```

If any predictive feature violates as-of：

```text
validation_status = failed_contract_or_leakage
next_phase_proceed_status = failed_contract_or_leakage
```

---

## 11. Baselines and Counterfactuals

R05 primary comparisons must include：

```text
R03_original_H10_replay
R04_R03_confirmed_H20_replay_diagnostic
R04_R03_winner_state_hold_H120_replay_diagnostic
profit_lock_rule_simple
trailing_stop_rule_simple
partial_exit_after_profit_rule
matched_exposure_days_random_exit
```

R05-pre must run only:

```text
R03_original_H10_replay
R04_R03_confirmed_H20_replay_diagnostic
R04_R03_winner_state_hold_H120_replay_diagnostic
profit_lock_rule_simple
trailing_stop_rule_simple
partial_exit_after_profit_rule
matched_exposure_days_random_exit
```

R05-pre must not train any model and must not generate model policy candidates.

### 11.1 R03 baseline

`R03_original_H10_replay` is baseline authority.

Required：

```text
validation / robustness replay must match R03 action / exposure semantics.
```

### 11.2 R04 diagnostic baselines

R04 variants are diagnostic-only：

```text
R04_R03_confirmed_H20_replay_diagnostic
R04_R03_winner_state_hold_H120_replay_diagnostic
```

They cannot be promoted in R05, but R05 must compare against them to show whether continuation policy adds value beyond simple fixed-H / winner-state extensions.

R05-pre simulator 只允许 replay 上述两个 R04 diagnostic references。R04 的
`R03_confirmed_H60` 和 `R03_confirmed_H120` 只能在
`requirement_05_R04_comparison_audit.csv` 中从 R04 frozen schedule metrics 读取，
字段必须标记：

```text
source = r04_frozen_report_read_only
replayed_by_r05 = false
promotion_eligible = false
```

### 11.3 Deterministic profit-protection baselines

These three deterministic rules are not optional diagnostics in R05-pre. They are the primary first-stage experiment. If all three fail both Track A and Track B on validation, full model stage must not start unless a later requirement explicitly overrides this requirement.

All deterministic rules share the same timing contract:

```text
1. signal features are computed from close[state_signal_date] and earlier only;
2. action executes at open[action_effective_date];
3. no same-close exit, partial-exit, or stop transition is allowed;
4. sell blocks use the same blocked-exit retry as R03;
5. action priority is full_exit > partial_exit > tighten_stop > hold_full;
6. if an exit is blocked, the intended target weight remains pending until retry succeeds or terminal blocked-exit is reached;
7. safety-cap natural exit executes at the next open after max_holding_days_safety_cap from first exposure.
```

`profit_lock_rule_simple`：

```yaml
activate_if:
  current_return_from_first_exposure >= 0.10
action:
  partial_exit_to_weight: 0.30
  partial_exit_once_per_episode: true
exit_remaining_if:
  giveback_from_peak_profit <= -0.06
max_holding_days_safety_cap: 120
```

Mechanics:

```text
activation_signal_date = first state_signal_date satisfying activate_if
partial_exit_effective_date = next_trading_day(activation_signal_date)
target_weight_after_partial = min(current_exposure_weight_before_action, 0.30)
profit_peak_reference updates from close only while exposure_weight > 0
giveback_from_peak_profit = current_return_from_first_exposure - max_return_from_first_exposure_to_date
exit_remaining_signal_date = first later state_signal_date with giveback_from_peak_profit <= -0.06
exit_remaining_effective_date = next_trading_day(exit_remaining_signal_date)
```

`trailing_stop_rule_simple`：

```yaml
activate_if:
  current_return_from_first_exposure >= 0.10
stop_floor:
  max(previous_stop_floor, peak_profit_reference_price * (1 - 0.08))
exit_if_close_below_stop_floor:
  full_exit_next_open
max_holding_days_safety_cap: 120
```

Mechanics:

```text
stop floor is inactive before activation_signal_date
after activation, active_stop_floor is persistent and monotonic non-decreasing
peak_profit_reference_price uses max close observed through state_signal_date
if close[state_signal_date] <= active_stop_floor, full_exit executes at next open
stop_floor cannot use action_effective_date high / low / close
```

`partial_exit_after_profit_rule`：

```yaml
activate_if:
  current_return_from_first_exposure >= 0.12
action:
  partial_exit_fraction: 0.50
  partial_exit_once_per_episode: true
remaining_position_exit:
  trailing_stop_rule_simple
max_holding_days_safety_cap: 120
```

Mechanics:

```text
partial exit sells current_exposure_weight_before_action * 0.50 at next open
remaining target weight is current_exposure_weight_before_action * 0.50
after partial exit, remaining exposure uses trailing_stop_rule_simple with activation already true
no second partial exit is allowed for the same episode
```

### 11.4 Matched exposure-days random exit

`matched_exposure_days_random_exit` must match：

```text
1. episode set；
2. first exposure date；
3. exposure-day distribution；
4. split；
5. confirm-add status distribution；
6. executable exit constraints.
```

Matched random is candidate-specific. For every promotion-eligible deterministic or
model policy, R05 must generate a matching random reference after that candidate's
action / exposure panel is finalized and before validation selection is evaluated.
R03 baseline gets its own baseline-matched random reference.

Required identifiers:

```text
policy_id
random_reference_policy_id
random_repeat_id
matched_to_policy_id
generated_after_policy_action_hash
generated_before_selection = true
matched_random_generated_before_selection = true
candidate_policy_hash
random_baseline_hash
```

Matched random must be generated after candidate policy action schedule is frozen
but before validation metric ranking / selected-policy freeze. It cannot be
generated only for the eventual selected policy after selection.

Matched random cannot use robustness outcomes to alter its matching buckets or seed.

Random config：

```yaml
matched_exposure_days_random_exit:
  n_repeats: 100
  random_seed: 20260509
  sample_unit: launch_episode_id
  match_by:
    - split
    - confirm_add_executed
    - exposure_day_bucket
    - executable_exit_count_bucket
```

Output must include：

```text
random_mean
random_std
random_p05
random_p50
random_p95
real_minus_random_p50
real_minus_random_p95
```

### 11.5 R04 regime audit

R05 must generate:

```text
reports/requirement_05_R04_regime_audit.csv
```

Minimum fields:

```text
split
regime_bucket
schedule_id
episode_count
exposed_episode_count
big_winner_episode_count_50h120
mean_after_cost_return_diff_vs_R03
p05_after_cost_return_diff_vs_R03
strict_capture_diff_vs_R03
exposure_day_multiple_vs_R03
validation_to_robustness_direction_match
regime_mismatch_flag
regime_mismatch_status
regime_mismatch_confidence
condition_A_triggered
condition_B_triggered
audit_interpretation
```

Allowed regime buckets must be observable from `state_signal_date` or earlier:

```text
market_ret_20d_bucket
market_volatility_20d_bucket
market_breadth_20d_bucket
industry_ret_20d_bucket
calendar_year
```

R04-regime audit is diagnostic-only. It cannot select an R05 policy. It can only
block the full model stage when the mechanical status is
`regime_mismatch_status = blocking`.

Regime mismatch status:

```text
condition A:
  at least two R04 holding-extension schedules among
  {R04_confirmed_H20, R04_winner_state_hold_H120, R04_confirmed_H60, R04_confirmed_H120}
  have validation Track A/B failure but robustness Track A/B pass or non-material reversal.

condition B:
  for any allowed regime dimension, at least one validation bucket and one robustness bucket
  each have exposed_episode_count >= 25 and big_winner_episode_count_50h120 >= 8,
  and the sign of mean_after_cost_return_diff_vs_R03 or p05_after_cost_return_diff_vs_R03
  reverses between validation and robustness for at least two R04 holding-extension schedules.

regime_mismatch_status = none if neither condition holds
regime_mismatch_status = weak_diagnostic if exactly one condition holds
regime_mismatch_status = blocking if both condition A and condition B hold

regime_mismatch_confidence = high only when regime_mismatch_status = blocking
regime_mismatch_flag = regime_mismatch_status in {weak_diagnostic, blocking}
```

Only `regime_mismatch_status = blocking` may block full model stage:

```text
full_model_stage_allowed = false
recommended_next_step = proceed_to_regime_conditional_requirement
```

If `regime_mismatch_status = weak_diagnostic`, R05 must report the diagnostic but
must not automatically block full model stage. Weak diagnostic status can only
affect recommendation language and cannot select a policy, feature, threshold, or
action rule.

The regime audit may block full model stage, but it must not choose a policy,
feature, threshold, or action rule.

---

## 12. Model Family

R05 full model stage 可以训练小模型，但只有在 deterministic pre-phase、R04-regime audit 和 sample-power audit 全部通过后才允许。模型只预测 continuation / risk，不直接输出交易策略。

If `full_model_stage_allowed = false`:

```text
model training is forbidden
continuation_prediction_panel may be omitted
model_calibration_audit may be omitted or emitted as not_run
model policy candidates must be empty
selected_policy must come from deterministic-only candidates or be null
```

Allowed first implementation：

```yaml
model_family:
  reward_model:
    model_type: lightgbm_binary
    target: continuation_reward_label
  risk_model:
    model_type: lightgbm_binary
    target: continuation_risk_label
  delta_model:
    model_type: lightgbm_regression
    target: hold_vs_exit_delta_10d
    optional: true
```

Simpler fallback allowed：

```yaml
reward_model: logistic_regression
risk_model: logistic_regression
delta_model: ridge_regression
```

Forbidden：

```text
1. direct action classifier trained on realized best action；
2. model that predicts holding days directly；
3. model that predicts continuous stop price directly；
4. reinforcement learning；
5. Cox / Fine-Gray survival model in first implementation；
6. feature search from robustness；
7. model chosen by BaseRate performance；
8. model chosen by big-winner target hindsight alone。
```

Model config must be fixed before validation scoring and written to：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_model_config_audit.csv
```

Model config audit must explicitly include:

```text
full_model_stage_allowed
full_model_stage_executed
sample_power_gate_passed
deterministic_prephase_gate_passed
regime_audit_blocked_full_model
regime_mismatch_status
regime_mismatch_confidence
model_training_executed
model_policy_candidate_count
```

---

## 13. Continuation Score

For full model stage, produce for every state row：

```text
P_profit_extension_10d
P_giveback_or_adverse_drawdown_10d
E_hold_vs_exit_delta_10d
continuation_score
```

For deterministic-only stage, these model-score fields are not used for action
selection. They must be null in action outputs or absent from stage-disabled
prediction artifacts. Deterministic rules must rely only on explicit state-panel
fields such as return, peak, drawdown, exposure weight, and executable exit state.

Default score：

```text
continuation_score =
    1.0 * P_profit_extension_10d
  - 1.0 * P_giveback_or_adverse_drawdown_10d
  + 0.5 * clip(E_hold_vs_exit_delta_10d, -0.05, 0.05)
  - 0.05 * capital_occupancy_penalty
```

Where：

```text
capital_occupancy_penalty = min(days_since_first_exposure / 120, 1.0)
```

Required output：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_continuation_prediction_panel.parquet
```

This output is required only when `full_model_stage_allowed = true` and
`model_training_executed = true`. When full model stage is disabled, the file must
not contain trained predictions; artifact authority must mark it as either:

```text
artifact_status = not_required_stage_disabled
```

or, if a stub is emitted:

```text
artifact_status = not_run_stub
row_count = 0
model_training_executed = false
```

Minimum schema：

```text
state_row_id
launch_episode_id
instrument
split
state_signal_date
action_effective_date
P_profit_extension_10d
P_giveback_or_adverse_drawdown_10d
E_hold_vs_exit_delta_10d
continuation_score
score_rank_within_episode
feature_asof_violation_flag
```

---

## 14. Action Space and Policy Mapping

R05 action space is fixed：

```text
hold_full
partial_exit
full_exit
tighten_stop
```

No new entry / add action is allowed.

### 14.1 Action definitions

`hold_full`：

```text
no trade, maintain current exposure weight
```

`partial_exit`：

```text
sell down to target weight = max(0.30, current_exposure_weight * 0.50)
execute next open if sell executable
```

`full_exit`：

```text
sell to zero exposure
execute next open if sell executable
```

`tighten_stop`：

```text
no immediate trade unless close-derived stop condition already breached;
update active_stop_floor by pre-registered formula;
future exit still executes next open after close-derived stop signal.
```

### 14.2 Stop floor formula

Default tightened stop：

```text
profit_floor_candidate = first_exposure_price * (1 + max(current_return_from_first_exposure - 0.08, 0))
trailing_candidate = post_confirm_high_to_date * (1 - thresholds.tightened_trailing_giveback)
active_stop_floor_new = max(active_stop_floor_previous, profit_floor_candidate, trailing_candidate)
```

Default：

```yaml
tightened_trailing_giveback: 0.08
```

Stop signal：

```text
if close[state_signal_date] <= active_stop_floor:
  action = forced_full_exit at next open
```

No intraday stop execution is allowed in R05.

Forced stop priority:

```text
close_breaches_active_stop_floor -> forced_full_exit
forced_full_exit priority > model_score_full_exit > partial_exit > tighten_stop > hold_full
```

Once active stop floor is breached, policy mapping cannot override the exit with
`hold_full`, `partial_exit`, or `tighten_stop`.

### 14.3 Policy mapping

Model policy thresholds are selected on validation only and only when full model
stage is allowed. If `full_model_stage_allowed = false`, model policy grid
expansion is forbidden and `model_policy_candidate_count` must be zero.

Candidate policy grid：

```yaml
policy_grid:
  full_exit_score_threshold: [-0.10, 0.00]
  partial_exit_score_threshold: [0.05]
  risk_full_exit_threshold: [0.60, 0.70]
  risk_partial_exit_threshold: [0.45, 0.55]
  tighten_stop_profit_threshold: [0.08, 0.12]
  tighten_stop_risk_threshold: [0.40]
  max_policy_candidates: 32
```

When full model stage is allowed, the candidate grid must be expanded before
validation scoring and written to artifact authority. If the expanded model
policy grid exceeds `max_policy_candidates`, full model stage must fail closed
with:

```text
next_phase_proceed_status = failed_contract_or_leakage
failure_reason = model_policy_grid_too_large
```

Mapping order：

```text
1. If current exposure = 0: no action.
2. If pending_exit_action_type is active: retry pending exit before reading new policy scores.
3. If close[state_signal_date] <= active_stop_floor: forced_full_exit.
4. If P_giveback_or_adverse_drawdown_10d >= risk_full_exit_threshold: full_exit.
5. Else if continuation_score <= full_exit_score_threshold: full_exit.
6. Else if current_profit_cushion > 0 and P_giveback_or_adverse_drawdown_10d >= risk_partial_exit_threshold: partial_exit.
7. Else if current_profit_cushion > 0 and continuation_score <= partial_exit_score_threshold: partial_exit.
8. Else if current_return_from_first_exposure >= tighten_stop_profit_threshold and P_giveback_or_adverse_drawdown_10d >= tighten_stop_risk_threshold: tighten_stop.
9. Else hold_full.
```

If multiple action conditions apply, priority：

```text
pending_exit_retry > forced_full_exit > model_score_full_exit > partial_exit > tighten_stop > hold_full
```

### 14.4 Safety cap

All policies must have safety cap：

```yaml
max_holding_days_safety_cap: 120
```

If no full exit occurs before cap：

```text
natural_exit at next open after max_holding_days_safety_cap
```

The safety cap is not a selection target.

---

## 15. Schedule Simulation

R05 policy simulation must use the same state machine and execution rules as EP2 engineering baseline / R03.

Required row-level outputs：

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_policy_action_panel.parquet
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/cache/requirement_05_policy_exposure_daily_panel.parquet
```

Minimum action schema：

```text
policy_id
launch_episode_id
instrument
split
state_signal_date
action_effective_date
action_type
target_weight_before
target_weight_after
action_execution_price
blocked_action
blocked_action_reason
pending_exit_action_type
pending_exit_reason
pending_exit_signal_date
pending_exit_retry_day_count
active_stop_floor_before
active_stop_floor_after
continuation_score
P_profit_extension_10d
P_giveback_or_adverse_drawdown_10d
E_hold_vs_exit_delta_10d
```

For deterministic-only policies, the model-score columns in the action schema must
be present but null. Validator must fail if deterministic action decisions depend
on non-null model scores while `full_model_stage_allowed = false`.

Blocked sell retry：

```yaml
blocked_exit_retry:
  same_as_engineering_baseline: true
  retry_until_executed: true
  max_retry_trading_days: 5
  if_still_blocked: mark_terminal_blocked_exit
```

Pending exit semantics:

```text
1. A blocked full_exit, forced_full_exit, or partial_exit creates pending_exit intent.
2. pending_exit_action_type records the original intended action.
3. pending_exit_reason records the original action reason.
4. pending_exit_signal_date records the original close-derived signal date.
5. pending_exit_retry_day_count starts at 1 on the first blocked effective date.
6. While pending_exit_action_type is active, retry has priority over new hold/tighten/model decisions.
7. If the retry executes, clear pending_exit_action_type after execution.
8. If max_retry_trading_days is exceeded, mark terminal_blocked_exit and clear active exposure according to the frozen baseline terminal-blocked semantics.
```

R05 must not allow a blocked exit intent to disappear because a later state row
would have produced `hold_full`.

---

## 16. Selection Protocol

### 16.1 Candidate generation

Candidate policies include：

```text
1. deterministic baselines;
2. model policy grid candidates;
3. matched exposure-days random exit;
4. R03 / R04 diagnostic replays.
```

Only model policy grid candidates and deterministic profit-protection baselines can be considered for R05 promoted policy.

Promotion-ineligible：

```text
R03_original_H10_replay
R04 fixed-H replays
R04 winner-state replay
matched_exposure_days_random_exit
no-fast-fail diagnostics
BaseRate-derived variants
```

### 16.2 Validation selection

Selection uses validation split only.

Primary objective must be multi-gate, not a single metric.

A policy is eligible if it passes either Track A or Track B.

#### Track A: winner-capture improvement

```text
strict_big_winner_capture_count_diff_vs_R03_validation >= max(2, ceil(0.05 * validation_big_winner_episode_count_50h120))
actionable_uncaptured_big_winner_count_50h120_validation >= strict_big_winner_capture_count_diff_required_validation
exposure_weighted_capture_diff_vs_R03_validation >= 0
mean_after_cost_return_diff_vs_R03_validation >= thresholds.max_mean_drop_vs_R03_negative_bound
p05_after_cost_return_diff_vs_R03_validation >= thresholds.max_p05_drop_vs_R03_negative_bound
max_adverse_excursion_worsening_vs_R03_validation <= thresholds.max_mae_worsening_vs_R03
exposure_day_multiple_vs_R03_validation <= thresholds.max_exposure_day_multiple_vs_R03
```

#### Track B: profit-protection / risk-filter improvement

```text
strict_big_winner_capture_count_loss_vs_R03_validation <= thresholds.track_B_max_strict_capture_count_loss
strict_big_winner_capture_rate_loss_vs_R03_validation <= thresholds.max_strict_capture_rate_loss_vs_R03
exposure_weighted_capture_loss_vs_R03_validation <= thresholds.max_exposure_weighted_capture_loss_vs_R03
mean_after_cost_return_diff_vs_R03_validation >= thresholds.min_mean_improvement_vs_R03_for_profit_protection
p05_after_cost_return_diff_vs_R03_validation >= thresholds.min_p05_improvement_vs_R03_for_profit_protection
max_adverse_excursion_improvement_vs_R03_validation >= thresholds.min_mae_improvement_vs_R03_for_profit_protection
```

Default Track B strict-capture count loss is zero because R03 validation baseline
strict capture count is very small. A one-count strict-capture loss is allowed
only if all of the following stronger risk-filter gates pass:

```text
strict_big_winner_capture_count_loss_vs_R03_validation == 1
p05_after_cost_return_diff_vs_R03_validation >= thresholds.track_B_one_capture_loss_min_p05_improvement
mean_after_cost_return_diff_vs_R03_validation >= thresholds.track_B_one_capture_loss_min_mean_improvement
exposure_weighted_capture_loss_vs_R03_validation <= thresholds.track_B_one_capture_loss_max_exposure_weighted_loss
```

A policy must also beat matched exposure-days random exit：

```text
real_metric_vs_matched_random_p50 > 0
real_metric_vs_matched_random_p95 >= -thresholds.max_random_p95_shortfall
```

Track B recommendation downgrade:

```text
if selected policy passes Track B only through the one-count strict-capture-loss exception:
  recommendation cannot be proceed_to_R06_baserate_integration_as_event_sleeve
  recommendation can only be one of:
    proceed_to_R06_baserate_integration_as_risk_filter_overlay
    keep_EP2_as_short_horizon_event_sleeve
    reframe_EP2_as_profit_protection_overlay
```

Such a policy may be useful as a risk filter, but it must not be described as a
winner-capture extension.

### 16.3 Tie-breakers

If multiple candidates pass：

```text
1. Prefer candidate passing both Track A and Track B.
2. Prefer lower p05 deterioration.
3. Prefer lower exposure-day multiple.
4. Prefer simpler policy with fewer action transitions.
5. Prefer deterministic baseline over model policy if performance difference is not material.
6. Prefer policy with lower blocked-exit rate.
7. Lexicographic policy_id as final deterministic tie-breaker.
```

Materiality rule：

```text
If model policy improves objective by less than thresholds.model_over_deterministic_materiality_margin,
then deterministic policy is selected or result downgraded to diagnostic_only.
```

Selection-power rule:

```text
If validation_big_winner_episode_count_50h120 < full_model_min_validation_big_winner_50h120
or validation_exposed_episode_count < full_model_min_validation_exposed_episodes,
then model policies are promotion-ineligible even if their validation metrics are numerically better.
```

### 16.4 Robustness holdout

Robustness is evaluated only after validation-selected policy is frozen.

Robustness cannot change：

```text
1. selected model family；
2. selected thresholds；
3. selected action mapping；
4. policy_id；
5. features；
6. label definitions。
```

If validation passes but robustness fails：

```text
next_phase_proceed_status = failed_robustness_holdout
```

---

## 17. Metrics and Gates

R05 must output schedule-level metrics for train / validation / robustness.

Required metrics：

```text
policy_id
split
episode_count
exposed_episode_count
action_count
partial_exit_count
full_exit_count
tighten_stop_count
blocked_exit_count
blocked_exit_retry_count
terminal_blocked_exit_count
mean_after_cost_return
median_after_cost_return
p05_after_cost_return
p95_after_cost_return
max_adverse_excursion_mean
max_adverse_excursion_p95
strict_big_winner_capture_rate_50h120
strict_big_winner_capture_count_50h120
exposure_weighted_big_winner_capture_rate_50h120
partial_capture_rate_50h120
actionable_big_winner_episode_count_50h120
baseline_strict_captured_big_winner_count_50h120
actionable_uncaptured_big_winner_count_50h120
mean_exposure_days
median_exposure_days
exposure_day_multiple_vs_R03
capital_occupancy_proxy
turnover_proxy
turnover_ratio_vs_R03
top1_instrument_year_exposure_share
top5_instrument_exposure_share
matched_random_real_minus_p50
matched_random_real_minus_p95
track_B_one_capture_loss_exception_used
sample_power_stage
promotion_eligible_stage
```

Default gates：

```yaml
r05_gates:
  deterministic_stage_min_validation_exposed_episodes: 80
  deterministic_stage_min_validation_big_winner_50h120: 30
  deterministic_stage_min_validation_actionable_big_winner_50h120: 10
  full_model_min_validation_exposed_episodes: 180
  full_model_min_validation_big_winner_50h120: 80
  full_model_min_validation_actionable_big_winner_50h120: 40
  full_model_min_events_per_free_parameter: 10
  max_full_model_policy_candidates: 32
  max_deterministic_policy_candidates: 3

  track_A_min_strict_capture_count_diff_floor: 2
  track_A_min_strict_capture_count_diff_rate: 0.05

  max_mean_drop_vs_R03_negative_bound: -0.0010
  max_p05_drop_vs_R03_negative_bound: -0.0030
  max_mae_worsening_vs_R03: 0.0050
  max_exposure_day_multiple_vs_R03: 3.0

  track_B_max_strict_capture_count_loss: 0
  max_strict_capture_rate_loss_vs_R03: 0.10
  max_exposure_weighted_capture_loss_vs_R03: 0.10
  min_mean_improvement_vs_R03_for_profit_protection: 0.0010
  min_p05_improvement_vs_R03_for_profit_protection: 0.0020
  min_mae_improvement_vs_R03_for_profit_protection: 0.0020
  track_B_one_capture_loss_min_p05_improvement: 0.0100
  track_B_one_capture_loss_min_mean_improvement: 0.0030
  track_B_one_capture_loss_max_exposure_weighted_loss: 0.0200

  max_random_p95_shortfall: 0.0010
  max_blocked_exit_retry_rate: 0.05
  max_terminal_blocked_exit_rate: 0.01
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  model_over_deterministic_materiality_margin: 0.0010
```

Proceed condition：

```text
deterministic pre-phase passes sample-power gate;
if full model stage is attempted, full-model sample-power gate passes;
validation selected policy passes Track A or Track B;
robustness selected policy passes the same track or does not materially reverse;
matched exposure-days random exit comparison passes;
concentration gates pass;
blocked-exit gates pass;
feature-asof and frozen-contract audits pass.
```

---

## 18. Diagnostic Audits

R05 must output the following diagnostic reports.

### 18.0 Sample-power and stage-order audit

```text
requirement_05_sample_power_audit.csv
requirement_05_stage_order_audit.csv
```

`requirement_05_stage_order_audit.csv` must prove:

```text
1. deterministic-only policies are evaluated before any model training;
2. R04-regime audit is evaluated before full model stage;
3. sample-power audit is evaluated before full model stage;
4. if full_model_stage_allowed = false, no model artifacts contain trained predictions;
5. robustness rows are not read for deterministic/model selection.
```

### 18.1 Profit-protection attribution

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/reports/requirement_05_profit_protection_attribution.csv
```

Fields：

```text
policy_id
split
profit_lock_action_count
partial_exit_action_count
tighten_stop_action_count
full_exit_action_count
mean_return_saved_by_partial_exit
mean_return_saved_by_full_exit
p05_return_saved_by_policy
winner_capture_lost_due_to_exit_count
partial_capture_lost_due_to_exit_count
```

### 18.2 Action reason audit

```text
requirement_05_action_reason_audit.csv
```

Fields：

```text
policy_id
action_type
action_reason
count
weighted_count
mean_pre_action_unrealized_return
mean_post_action_return_10d
mean_saved_loss
mean_missed_upside
```

### 18.3 Model calibration audit

```text
requirement_05_model_calibration_audit.csv
```

Required only when `full_model_stage_allowed = true`. If full model stage is
disabled, this report may be omitted if artifact authority marks it
`not_required_stage_disabled`, or emitted as a `not_run` stub with:

```text
model_training_executed = false
row_count = 0
```

Fields：

```text
model_name
split
auc
logloss
brier
calibration_slope
calibration_intercept
score_decile
observed_rate
predicted_rate
```

Calibration is diagnostic. A calibrated model does not imply promoted policy.

### 18.4 Robustness no-selection audit

```text
requirement_05_robustness_nonselection_audit.csv
```

Must prove robustness data was not used before selected policy freeze.

### 18.5 R04 comparison audit

```text
requirement_05_R04_comparison_audit.csv
```

Must compare selected policy to：

```text
R03_original_H10
R04_confirmed_H20
R04_winner_state_hold_H120
R04_confirmed_H60
R04_confirmed_H120
```

But R04 schedules remain promotion-ineligible.

---

## 19. Required Artifact Authority

R05 must output artifact authority for every artifact below. Artifact authority
must classify each artifact as one of:

```text
required_always
required_deterministic_stage
required_full_model_stage
not_required_stage_disabled
not_run_stub
```

Validator must fail closed if an artifact is missing while classified as
`required_always`, `required_deterministic_stage`, or `required_full_model_stage`.
Validator must also fail if a `not_required_stage_disabled` or `not_run_stub`
model artifact contains trained predictions, non-empty model candidates, or model
selection evidence.

### 19.1 Manifest

```text
ep2/outputs/requirement_05_daily_continuation_profit_protection_policy/manifests/requirement_05_continuation_policy_manifest.json
```

Minimum fields：

```text
phase
validation_status
next_phase_proceed_status
recommendation
generated_at
engineering_baseline_manifest_hash
requirement_01_manifest_hash
requirement_02_manifest_hash
requirement_03_manifest_hash
requirement_04_manifest_hash
primary_label_id
frozen_baseline_id
hazard_schedule_id
schedule_bridge_id
selected_threshold
selected_stop_risk_ceiling
post_exposure_state_panel_hash
feature_dictionary_hash
label_metric_dictionary_hash
model_config_audit_hash
prediction_panel_hash
policy_action_panel_hash
policy_exposure_daily_panel_hash
policy_results_hash
gate_audit_hash
robustness_nonselection_audit_hash
full_model_stage_allowed
full_model_stage_executed
model_training_executed
deterministic_prephase_status
regime_audit_blocked_full_model
regime_mismatch_status
regime_mismatch_confidence
sample_power_status
```

When an artifact is not required due to stage disablement, its manifest hash must
be null and its authority row must include:

```text
artifact_status = not_required_stage_disabled
hash = null
reason = full_model_stage_not_allowed
```

### 19.2 Always-required cache artifacts

```text
cache/requirement_05_post_exposure_state_panel.parquet
cache/requirement_05_continuation_training_panel.parquet
cache/requirement_05_policy_action_panel.parquet
cache/requirement_05_policy_exposure_daily_panel.parquet
cache/requirement_05_matched_random_exit_panel.parquet
```

`requirement_05_continuation_training_panel.parquet` is required because labels
and sample-power must be audited even when model training is disabled. It must
not be used to train a model unless `full_model_stage_allowed = true`.

### 19.3 Full-model-stage cache artifacts

Required only when `full_model_stage_allowed = true`:

```text
cache/requirement_05_continuation_prediction_panel.parquet
```

If full model stage is disabled, this artifact must be absent or a zero-row
`not_run_stub`.

### 19.4 Always-required report artifacts

```text
reports/requirement_05_artifact_authority.csv
reports/requirement_05_sample_power_audit.csv
reports/requirement_05_stage_order_audit.csv
reports/requirement_05_feature_dictionary.csv
reports/requirement_05_feature_asof_audit.csv
reports/requirement_05_label_metric_dictionary.csv
reports/requirement_05_model_config_audit.csv
reports/requirement_05_deterministic_prephase_results.csv
reports/requirement_05_policy_grid_results.csv
reports/requirement_05_selected_policy.csv
reports/requirement_05_schedule_metrics.csv
reports/requirement_05_gate_audit.csv
reports/requirement_05_profit_protection_attribution.csv
reports/requirement_05_action_reason_audit.csv
reports/requirement_05_R03_replay_audit.csv
reports/requirement_05_R04_comparison_audit.csv
reports/requirement_05_R04_regime_audit.csv
reports/requirement_05_matched_random_exit_audit.csv
reports/requirement_05_concentration_audit.csv
reports/requirement_05_blocked_exit_audit.csv
reports/requirement_05_robustness_nonselection_audit.csv
reports/requirement_05_forbidden_recommendation_audit.csv
reports/requirement_05_report.md
```

### 19.5 Full-model-stage report artifacts

Required only when `full_model_stage_allowed = true`:

```text
reports/requirement_05_model_calibration_audit.csv
```

If full model stage is disabled, this report must be absent with artifact
authority status `not_required_stage_disabled` or emitted as a `not_run_stub`.

Full row-level CSV outputs are not required and must not be generated by default. Row-level panels must be parquet cache only.

---

## 20. Config Sketch

```yaml
phase: requirement_05_daily_continuation_profit_protection_policy
output_root: ep2/outputs/requirement_05_daily_continuation_profit_protection_policy

frozen_contract:
  requirement_01_status: passed
  requirement_02_status: passed
  requirement_03_status: passed
  requirement_04_status: failed_tail_risk
  primary_label_id: confirm_h10_u10_d06_conservative_fail
  frozen_baseline_id: probe_with_simple_stop
  hazard_schedule_id: hazard_probe_with_simple_stop
  schedule_bridge_id: hazard_probe_confirm_add_fast_fail
  selected_threshold: 0.3205667777673395
  selected_stop_risk_ceiling: 0.27410397287415667

state_panel:
  start_after: first_positive_exposure
  include_probe_only_states: true
  include_confirmed_states: true
  state_signal_date_rule: close_derived
  action_effective_date_rule: next_trading_day_open
  max_holding_days_safety_cap: 120

stage_control:
  implementation_mode: deterministic_prephase_only
  run_deterministic_prephase_first: true
  run_R04_regime_audit_before_full_model: true
  full_model_stage_default_enabled: false
  full_model_stage_executed_default: false
  full_model_requires_sample_power_pass: true
  full_model_requires_deterministic_prephase_pass: true
  full_model_requires_regime_mismatch_status_not_blocking: true

labels:
  primary_K: 10
  additional_K: [5, 20]
  profit_extension_target:
    K5: 0.04
    K10: 0.06
    K20: 0.10
  adverse_drawdown:
    K5: 0.04
    K10: 0.06
    K20: 0.08
  giveback_from_peak:
    K5: 0.04
    K10: 0.06
    K20: 0.08

model:
  reward_model:
    model_type: lightgbm_binary
    random_state: 20260509
    num_boost_round: 64
  risk_model:
    model_type: lightgbm_binary
    random_state: 20260509
    num_boost_round: 64
  delta_model:
    enabled: true
    model_type: lightgbm_regression
    random_state: 20260509
    num_boost_round: 64
  early_stopping: false
  robustness_used_for_model_selection: false

policy_grid:
  full_exit_score_threshold: [-0.10, 0.00]
  partial_exit_score_threshold: [0.05]
  risk_full_exit_threshold: [0.60, 0.70]
  risk_partial_exit_threshold: [0.45, 0.55]
  tighten_stop_profit_threshold: [0.08, 0.12]
  tighten_stop_risk_threshold: [0.40]
  tightened_trailing_giveback: 0.08
  max_policy_candidates: 32

matched_random_exit:
  n_repeats: 100
  random_seed: 20260509
  sample_unit: launch_episode_id
  candidate_specific: true
  generated_after_candidate_action_schedule_frozen: true
  generated_before_validation_ranking: true

r05_gates:
  deterministic_stage_min_validation_exposed_episodes: 80
  deterministic_stage_min_validation_big_winner_50h120: 30
  deterministic_stage_min_validation_actionable_big_winner_50h120: 10
  full_model_min_validation_exposed_episodes: 180
  full_model_min_validation_big_winner_50h120: 80
  full_model_min_validation_actionable_big_winner_50h120: 40
  full_model_min_events_per_free_parameter: 10
  max_full_model_policy_candidates: 32
  max_deterministic_policy_candidates: 3
  track_A_min_strict_capture_count_diff_floor: 2
  track_A_min_strict_capture_count_diff_rate: 0.05
  max_mean_drop_vs_R03_negative_bound: -0.0010
  max_p05_drop_vs_R03_negative_bound: -0.0030
  max_mae_worsening_vs_R03: 0.0050
  max_exposure_day_multiple_vs_R03: 3.0
  track_B_max_strict_capture_count_loss: 0
  max_strict_capture_rate_loss_vs_R03: 0.10
  max_exposure_weighted_capture_loss_vs_R03: 0.10
  min_mean_improvement_vs_R03_for_profit_protection: 0.0010
  min_p05_improvement_vs_R03_for_profit_protection: 0.0020
  min_mae_improvement_vs_R03_for_profit_protection: 0.0020
  track_B_one_capture_loss_min_p05_improvement: 0.0100
  track_B_one_capture_loss_min_mean_improvement: 0.0030
  track_B_one_capture_loss_max_exposure_weighted_loss: 0.0200
  max_random_p95_shortfall: 0.0010
  max_blocked_exit_retry_rate: 0.05
  max_terminal_blocked_exit_rate: 0.01
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  model_over_deterministic_materiality_margin: 0.0010

regime_audit:
  allowed_dimensions:
    - market_ret_20d_bucket
    - market_volatility_20d_bucket
    - market_breadth_20d_bucket
    - industry_ret_20d_bucket
    - calendar_year
  min_bucket_exposed_episodes: 25
  min_bucket_big_winner_50h120: 8
  min_reversing_r04_schedule_count_to_block: 2
  status_enum:
    - none
    - weak_diagnostic
    - blocking
  blocking_requires_condition_A_and_B: true
```

---

## 21. Validation Checklist

`validate_requirement_05_continuation_policy.py` must verify：

```text
1. R01 / R02 / R03 frozen statuses pass；
2. R04 completed with no promoted schedule；
3. R03 replay metrics match validation / robustness baselines；
4. all stage-required artifacts exist and stage-disabled model artifacts are absent or not_run stubs；
5. sample-power audit exists and controls deterministic vs full model stage；
6. sample-power audit includes actionable big-winner and baseline strict-capture counts；
7. deterministic_candidate_count equals exactly the three deterministic profit-protection rules；
8. deterministic prephase runs before any model training；
9. R04-regime audit runs before full model stage and applies none / weak_diagnostic / blocking status mechanically；
10. if full_model_stage_allowed = false, full_model_stage_executed = false, no model policy is promoted, and no trained model artifact is used；
11. model policy grid candidate count <= max_full_model_policy_candidates；
12. Track A strict-capture minimum uses max(2, ceil(5% * validation big-winner count)) and actionable-uncaptured support is sufficient；
13. Track B strict-capture count loss obeys zero-loss default or the stronger one-count-loss exception；
14. Track B one-count-loss exception cannot produce event-sleeve winner-capture recommendation；
15. post-exposure state panel contains only rows after R03 exposure；
16. no row without R03 positive exposure is used for continuation training；
17. feature-asof audit has zero violations；
18. action_effective_date high/low/close/volume/money are not predictive features；
19. labels start at action_effective_date and include action-effective high/low；
20. robustness rows are unavailable during model / policy selection；
21. selected policy comes from validation only；
22. matched exposure-days random exit is candidate-specific, generated with fixed seed and repeat count, generated after candidate policy hash is frozen, and generated before selection；
23. BaseRate row-level data is not read；
24. R04 variants are diagnostic-only and not promoted；
25. R04 H60/H120 comparison rows are read-only from frozen R04 reports, not R05 replay outputs；
26. policy action panel and exposure panel obey state-machine priority；
27. forced stop breach has priority over model-score full exit, partial exit, tighten stop, and hold；
28. deterministic partial exits are once-per-episode and close-derived / next-open only；
29. blocked exit retry preserves pending_exit intent and cannot be overridden by later hold decisions；
30. all gates are reported for validation and robustness；
31. next_phase_proceed_status is consistent with gate audit；
32. forbidden recommendation audit passes；
33. manifest hashes match current artifacts。
```

---

## 22. Recommendation Logic

R05 may output an internal stage-transition recommendation：

```text
recommendation = run_R05_full_model_stage
```

when：

```text
R05-pre deterministic-only policy passes validation and robustness gates,
sample-power full-model gate passes,
regime_mismatch_status != blocking,
full_model_stage_allowed = true,
and full_model_stage_executed = false.
```

`run_R05_full_model_stage` is not a final research proceed status. It only means
that a later independent R05 full-model run is allowed. It must not be reported
as R05 passing, R06 readiness, strategy readiness, or portfolio validation.

R05 may output：

```text
recommendation = proceed_to_regime_conditional_requirement
```

when：

```text
R04-regime audit suggests validation failure is primarily regime-specific,
regime_mismatch_status = blocking,
or deterministic rules show materially different validation / robustness direction
that cannot be resolved by a pooled continuation policy.
```

R05 may output：

```text
recommendation = proceed_to_R06_baserate_integration_as_event_sleeve
```

when：

```text
Track A passes validation and robustness,
and policy improves or preserves big-winner capture without tail-risk deterioration.
```

Forbidden for this recommendation:

```text
track_B_one_capture_loss_exception_used = true
```

R05 may output：

```text
recommendation = proceed_to_R06_baserate_integration_as_risk_filter_overlay
```

when：

```text
Track B passes validation and robustness,
and policy primarily improves mean / p05 / MAE / capital occupancy rather than capture.
```

If `track_B_one_capture_loss_exception_used = true`, this is the strongest allowed
R06 recommendation. The policy must be described as risk-filter / profit-protection
overlay only, not winner-capture extension.

R05 may output：

```text
recommendation = keep_EP2_as_short_horizon_event_sleeve
```

when：

```text
R05 does not improve continuation enough for R06,
but R03 short-horizon edge remains intact.
```

R05 may output：

```text
recommendation = stop_big_winner_holding_research
```

when：

```text
no continuation / profit-protection policy improves capture or risk without degrading R03.
```

R05 may output：

```text
recommendation = stop_due_to_insufficient_selection_power
```

when：

```text
deterministic prephase has enough support to run,
but full model sample-power gates fail and deterministic policies do not produce enough evidence to justify R06.
```

R05 may output：

```text
recommendation = stop_due_to_no_continuation_policy_edge
```

when：

```text
model and deterministic baselines both fail matched exposure-days random exit or robustness gates.
```

R05 must not output：

```text
proceed_to_P1_strategy
proceed_to_strategy_backtest
freeze_strategy
validated_strategy
selected_final_model
```

---

## 23. Source Artifacts

This requirement is based on the current EP2 artifact sequence：

```text
EP2 Engineering Baseline Requirement
Requirement 01: Label and Baseline Freeze
Requirement 02: Hazard Timing Model
Requirement 03: Schedule Bridge and BaseRate-Overlap Audit
Requirement 04: Holding / Exit Winner-Capture Extension Report
```

Key interpretation：

```text
R01-R03 passed and established a low-frequency launch exposure timing signal.
R04 failed because fixed holding-time extensions increased winner capture only at unacceptable tail-risk / capital-occupancy cost.
R05 therefore reframes holding as daily continuation value and profit-protection policy.
```
