# discussion3：R05 之后对 entry 结构与 R06 方向的讨论

> 生成日期：2026-05-09
> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 P1 validation。
> 适用范围：基于当前 EP2 Requirement 01-05 的实验结果，讨论为什么 R04/R05 暴露出 entry specificity 问题，以及下一阶段如何约束“反过来修 entry”。

---

## 0. TL;DR

R04 / R05 的失败不应简单理解为 “holding / exit 规则写得不好”。更准确的解释是：

```text
当前 R03 entry 能找到短周期、可执行、低换手的 probe / confirm-add 机会；
但它没有证明这些 confirm-add episode 本身已经属于长期 winner-holding pool。
```

R05-pre 的三条 deterministic policy 都把 validation strict big-winner capture 从 `2` 提到 `5`，但代价是：

```text
p05 return 恶化约 1.6-1.9pct；
capital occupancy 上升到 2.56-3.32 倍；
trailing / partial exit 的 exposure-day multiple 超过 3.0；
Track A / Track B / matched-random p95 全部失败。
```

这个形态说明：在 R03 confirm-add 后的 episode pool 中，可能混有两类样本：

```text
1. 延长持有后确实能贡献 big-winner capture 的 episode；
2. 延长持有后会被尾部回撤吞掉收益的 episode。
```

当前 entry 没有把这两类分开。因此，下一步如果继续研究，重点不应是继续调固定 H、固定 profit lock 或 trailing stop，而应验证：

```text
在 R03 已 confirm-add 的 episode 上，
是否存在 confirm-add 时点 as-of 可观测的信息，
能判断该 episode 是否值得进入 extended holding / continuation policy。
```

这更像 R06：`confirm_add_continuation_eligibility_filter`，而不是 R05 full-model。

---

## 1. 当前 entry 的实际结构

当前 EP2 entry 不是一个单点信号，而是一个四层漏斗。

### 1.1 Launch episode

来源是 `EP2_LAUNCH_DETECTOR_V0`：

```text
detector_family = price_breakout_money_surge
price_breakout_lookback_days = 60
price_breakout_min_return = 0.12
money_ma_lookback_days = 20
money_multiple_min = 2.0
money_min_cny = 50,000,000
```

含义：

```text
过去 60 个交易日内价格出现突破；
当日成交额显著放大；
信号只使用 signal_date 收盘时可见信息；
执行在下一交易日开盘。
```

这一层的作用是发现异常启动事件，不是精细筛选长期 winner。

### 1.2 Valid probe candidate

在 launch 后最多 10 个交易日内生成候选 probe day。候选必须满足：

```text
is_within_allowed_probe_window = true
buy next open executable
no terminal state before probe
no pre-probe fast-fail from launch reference
missed_gain_to_probe <= 0.08
```

这一层控制的是：

```text
这个 launch 后是否还有可执行、未追太高、路径未失效的 probe 机会。
```

### 1.3 R02 hazard-selected probe

R02 只在 valid probe candidates 上训练 / 选择。目标是短周期 path label：

```text
primary_label_id = confirm_h10_u10_d06_conservative_fail
classes = target_first / stop_first / neither
```

冻结阈值：

```text
selected_threshold = 0.3205667777673395
selected_stop_risk_ceiling = 0.27410397287415667
```

probe 规则：

```text
score_probe_day >= selected_threshold
P_stop_first <= selected_stop_risk_ceiling
is_valid_probe_candidate = true
pre_probe_fast_fail_from_launch_reference = false
```

执行后只上 `0.30` probe weight。R02 / R03 validation 中：

```text
episode_count = 532
episode_with_any_exposure_count = 104
probe_rate = 0.195489
```

也就是说，R02 已经把大部分 launch episode 过滤掉了。

### 1.4 R03 confirm-add

R03 在 R02 selected probe 后增加 deterministic confirm-add：

```text
confirm_add_search_window = probe + 1 到 probe + 3 trading days
max_confirm_add_days_from_launch_execution = 10
confirm_add_weight = 0.70
full_weight_after_confirm = 1.00
fast_fail_drawdown = 0.06
```

confirm-add 仍要求：

```text
same episode
valid candidate
score_probe_day >= selected_threshold
P_stop_first <= selected_stop_risk_ceiling
pre_probe_fast_fail_from_launch_reference = false
missed_gain_to_probe <= 0.08
buy executable
no prior fast-fail
```

R03 validation 中：

```text
probe_rate = 0.195489
confirm_add_rate = 0.139098
mean_after_cost_return = 0.008592
p05_after_cost_return = -0.007543
big_winner_capture_rate = 0.046512
turnover_proxy = 7.92
```

这说明 R03 的 entry 是一个短周期的 exposure timing structure：

```text
broad launch detector
  -> valid probe window filter
    -> short-horizon hazard probe selector
      -> bounded confirm-add continuation check
        -> H10 natural exit / 6% fast-fail
```

---

## 2. R04 / R05 暴露出的结构问题

R04 测试的是：

```text
如果把 R03 confirm-add 后的持有期拉长到 H20 / H60 / H120，
或者加入 winner-state hold，
能否提高 big-winner capture 且不破坏 tail risk。
```

R05-pre 测试的是：

```text
如果不直接固定 H，
而用简单 profit lock / trailing stop / partial exit，
能否保护利润并保留 winner 上行。
```

R05 validation 的关键结果：

| policy_id | strict capture count | mean diff vs R03 | p05 diff vs R03 | exposure multiple | matched p95 diff |
|:--|--:|--:|--:|--:|--:|
| R03_original_H10_replay | 2 | 0.000000 | 0.000000 | 1.000000 | |
| profit_lock_rule_simple | 5 | 0.000801 | -0.016129 | 2.559721 | -0.002617 |
| trailing_stop_rule_simple | 5 | 0.000862 | -0.017497 | 3.319898 | -0.001501 |
| partial_exit_after_profit_rule | 5 | 0.001218 | -0.018656 | 3.248690 | -0.001504 |

这个结果很关键：

```text
winner capture 是可以提高的；
但提高 capture 的同时，p05 和资金占用同步变差。
```

因此，问题不只是 exit 规则太简单。更深层的问题是：

```text
当前 confirm-add episode pool 中，
值得继续持有的样本和延长后会带来尾部损失的样本没有被分开。
```

---

## 3. 为什么不应该直接做 R05 full-model

R05 full-model 的自然想法是：

```text
每天根据 continuation / risk / delta score 决定 hold、tighten stop、partial exit 或 full exit。
```

但当前不适合直接做，原因有三点。

### 3.1 样本量与自由度不匹配

R05-pre validation 样本：

```text
exposed_episode_count = 104
big_winner_episode_count_50h120 = 43
actionable_big_winner_episode_count_50h120 = 16
baseline_strict_captured_big_winner_count_50h120 = 2
```

这个规模可以跑三条 deterministic policy，但不适合承载多模型、多 grid、多 track 的 full-model selection。

### 3.2 Daily panel 会放大样本量错觉

R05 daily state panel 看起来有更多 rows，但真正独立的信息单位仍然是 episode。若直接训练 daily continuation model，容易把同一个 episode 的多天状态当成很多独立样本，实际 selection noise 不会因此消失。

### 3.3 当前失败更像 entry pool 混合问题

如果 entry pool 内部不能区分 “可长持” 与 “不可长持”，更复杂的 daily policy 只会更精细地调退出路径，但无法从根上解决：

```text
该不该让这个 episode 进入 extended holding policy。
```

---

## 4. “反过来修 entry” 是正确方向吗

是，但必须限定含义。

这里的 “修 entry” 不应该是：

```text
重新预测 120d big-winner；
重新搜索 R02 hazard threshold；
重新扩大 R02 features；
重新改变 launch detector；
回到 Explore primitive / path extraction。
```

这些都会破坏 R01-R03 已经冻结的阶段边界，也可能重新引入 horizon mismatch 或 threshold search。

更准确的方向是：

```text
不动 R01 / R02 / R03；
只在 R03 confirm-add 之后，
加一层 confirm-add continuation eligibility filter。
```

也就是：

```text
R03 confirm-add passed
  -> continuation eligibility filter
    -> allowed to use extended holding / profit protection / trailing policy
```

这个 filter 才是当前结构中缺失的一层。

---

## 5. 建议的 R06 问题表述

R06 不应被写成 “R05 full-model continuation policy”。更好的问题是：

```text
在 R03 已 confirm-add 的 exposure 上，
能否用 confirm-add 时点 as-of 的信息，
预测该 episode 是否值得延长持有，
从而让 extended holding 的 capture 提升不再被 p05 恶化抵消？
```

一个更机械的名称：

```text
Requirement 06: Confirm-Add Continuation Eligibility Filter
```

它的研究对象是 episode-level，不是 daily-level：

```text
sample_unit = launch_episode_id
trigger = first R03 confirm_add_execution_date
decision_date = confirm_add_signal_date
execution_scope = confirm_add already happened; decide whether future extended policy is allowed
```

---

## 6. R06 的最小可验证声明

第一版 R06 不需要证明完整策略，只需要验证一个最弱但关键的声明：

```text
在 R03 已 confirm-add 的 episode 中，
存在一个 confirm-add as-of 可观测特征子集，
能把样本分成 top-half / bottom-half；

top-half 上，trailing_stop_rule_simple 或 H20/H60 能通过 Track A；
bottom-half 上，该规则不通过或明显更差；
且 top-half 的 p05 / MAE / capital occupancy 不同步恶化。
```

如果这个声明成立，才有资格重新讨论 R05 full-model。

如果不成立，EP2 应直接降级为：

```text
short-horizon event sleeve
或
BaseRate / risk-filter overlay input
```

---

## 7. R06 candidate label 设计

R06 不应使用 “是否 120d big-winner” 作为训练标签。原因：

```text
R01-R05 已经显示：只提高 big-winner capture 不够；
必须同时避免 p05 / MAE / capital occupancy 被吃掉。
```

更合适的标签是 hold-vs-exit delta：

```text
label_continuation_delta_H20 =
  return(R03_confirmed_H20) - return(R03_original_H10)

label_continuation_delta_trailing =
  return(trailing_stop_rule_simple) - return(R03_original_H10)
```

也可以定义 risk-adjusted delta：

```text
risk_adjusted_delta =
  return_delta
  - lambda_mae * max(0, MAE_extension - MAE_R03)
  - lambda_exposure * max(0, exposure_days_extension - exposure_days_R03)
```

第一版建议同时输出 continuous delta 和 binary label：

```text
binary_positive_continuation =
  risk_adjusted_delta > pre_registered_threshold
```

注意：binary threshold 必须预注册，不能在 validation 上搜索。

---

## 8. R06 feature 边界

R06 feature 必须全部来自 confirm-add 时点 as-of 数据。

允许的候选 feature family：

```text
R02 hazard information:
  P_target_first
  P_stop_first
  target_minus_stop_score
  selected_threshold_margin
  stop_ceiling_margin

probe-to-confirm path:
  return_from_probe_to_confirm
  drawdown_from_probe_to_confirm
  intraday / close-to-open volatility before confirm
  missed_gain_to_confirm

launch-to-confirm context:
  days_from_launch_execution
  return_from_launch_to_confirm
  max_drawdown_from_launch_reference
  whether near pre-probe fast-fail boundary

liquidity / execution:
  turnover / money as-of
  volume expansion persistence
  executable status history

market / industry regime:
  market trend as-of
  market width as-of
  industry trend / sync as-of
  industry relative strength as-of
```

禁止：

```text
使用 confirm_add_execution_date 之后的 high / low / close；
使用 future target date；
使用 50h120 / 100h240 label 作为 feature；
用 robustness 选择 feature、threshold 或 bucket；
改变 R02 threshold；
改变 R03 confirm-add rule。
```

---

## 9. R06 selection 形态建议

为了避免变成新的大搜索，R06 第一版应限制复杂度。

建议允许：

```text
one shallow scorer
或
pre-registered feature buckets
或
single monotonic score with fixed direction
```

不建议允许：

```text
多模型 ensemble；
大规模 grid search；
daily policy optimization；
H20/H60/H120 同时作为可选 promotion target；
在 validation 上同时选 feature、threshold、holding policy。
```

推荐的最小结构：

```text
candidate scorer:
  trained on train split only

validation:
  split confirmed episodes into top-half / bottom-half by scorer
  apply one frozen extended policy, e.g. trailing_stop_rule_simple or H20
  compare top-half vs R03_H10

robustness:
  same scorer, same top-half rule, no threshold change
```

---

## 10. R06 proceed / stop 逻辑

R06 应该有非常保守的结论权限。

允许结论：

```text
proceed_to_R05_full_model_after_confirm_add_filter
proceed_to_regime_conditional_confirm_add_filter
keep_EP2_as_short_horizon_event_sleeve
reframe_EP2_as_risk_filter_overlay_input
stop_long_horizon_winner_holding_research
```

禁止结论：

```text
freeze_strategy
proceed_to_P1_strategy
full_portfolio_backtest
change_R02_threshold
change_primary_label
promote_long_horizon_holding_without_filter
```

如果 R06 无法证明 top-half / bottom-half 的有效分离，那么当前最合理的结论是：

```text
EP2 entry 只支持短周期事件暴露；
不支持长周期 winner holding system；
后续应转向 BaseRate overlap / risk-filter overlay / event sleeve integration。
```

---

## 11. 当前讨论的阶段性判断

当前最强的 working hypothesis 是：

```text
R03 entry 不是错的；
它解决的是短周期 exposure timing；
R04/R05 失败说明它没有解决 long-horizon continuation eligibility。
```

因此下一步不是继续调 exit，而是验证：

```text
R03 confirm-add 后，
是否还能用 as-of 信息再做一次 episode-level 二次过滤。
```

这就是 “反过来修 entry” 的严格含义。

如果这个二次过滤成立，R05 full-model 才有研究价值。
如果不成立，EP2 应停止 big-winner holding extension，把当前成果收敛为 short-horizon event sleeve。
