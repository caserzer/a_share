# discussion2：EP2 R01-R03 当前实验解读与后续研究方向

> 生成日期：2026-05-09
> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 P1 validation。
> 适用范围：基于当前 EP2 Requirement 01 / 02 / 03 已完成实验结果，对后续研究方向做阶段性判断。

---

## 0. TL;DR

当前 EP2 的 R01 / R02 / R03 是目前为止比较健康的一条正向路线。

它和之前 Explore10 primitive 路线的最大区别是：

```text
不是继续从高层 semantic primitive / LGBM path 里解释 alpha，
而是把问题重新定义成：

在 frozen launch observation pool 中，
能否用低换手、next-open 可执行、短周期可验证的 exposure timing，
安排 probe_entry、confirm_add 和 fast_fail_exit。
```

当前结论可以概括为：

```text
EP2 已经证明：
存在一个低频 launch exposure timing 结构，
能在 validation / robustness 上相对 no-model baseline 提高 after-cost return，
并显著降低 probe 频率 / turnover proxy。

但 EP2 还没有证明：
它是完整策略；
它能长期持有 big winner；
它能跑赢 BaseRate 组合层收益；
它已经解决 holding / exit。
```

下一步不应继续优化 entry / threshold / hazard feature，也不应回到 primitive / 行业 LGBM / path extraction。
**下一阶段应该做 Requirement 04：Holding / Exit and Winner-Capture Extension。**

---

## 1. 当前实验结果如何

### 1.1 总体状态

EP2 当前前三个 requirement 全部通过：

```text
Requirement 01: passed, 20/20 gates
Requirement 02: passed, 27/27 gates
Requirement 03: passed, 17/17 gates
```

阶段性含义：

```text
R01: primary label 与 no-model baseline 已冻结。
R02: hazard timing model 能选择低频 probe，并跑赢 frozen baseline。
R03: 在 hazard probe 上加入 deterministic confirm_add 后，短期 after-cost return 进一步改善，且 BaseRate overlap 显示它不是简单复刻 BaseRate TopK。
```

但这个通过状态只允许进入 holding / exit 研究，不允许进入：

```text
P1 strategy
Explore10/11 primitive rerun
full strategy backtest
freeze strategy
BaseRate 年化收益直接比较
```

---

## 2. Requirement 01 解读：label 和 no-model baseline 冻结成功

### 2.1 Frozen primary label

R01 冻结的 primary label 是：

```text
confirm_h10_u10_d06_conservative_fail
```

含义：

```text
从 next-open exposure reference price 开始，
未来 10 个交易日内先达到 +10%，
且在达到 +10% 前没有先触发 -6% drawdown，
同日 high/low 歧义按 conservative_fail 处理。
```

主要统计：

```text
candidate_positive_rate: 0.224157
episode_any_positive_rate: 0.431616
episode_first_valid_positive_rate: 0.267022
episode_weighted_positive_rate: 0.243188
event_count: 12692
episode_count: 1689
year_count: 7
top1_instrument_year_positive_share: 0.009139
same_day_ambiguity_rate: 0.0
```

解读：

```text
1. 标签不是过宽标签，candidate positive rate 约 22.4%。
2. episode 层面仍有足够正样本，episode any positive rate 约 43.2%。
3. 同日歧义为 0，说明 conservative_fail 没有把大量样本变成路径不确定。
4. top1 instrument-year positive share 很低，说明正样本不是由单一股票年份支撑。
```

这说明短周期 confirm-validity label 是可用的。它比早期研究中直接预测 50h120 / 100h240 big winner 更符合 launch 后短期 exposure decision 的信息结构。

### 2.2 Frozen no-model baseline

R01 中唯一通过全部 no-model baseline gates 的 schedule 是：

```text
probe_with_simple_stop
```

规则：

```text
launch effective date 建立 0.30 probe 仓位；
不启用 confirm_add；
使用 -6% fast-fail；
H=10 natural exit。
```

主要结果：

```text
episode_with_any_exposure_count: 2447
probe_rate: 0.993101
fast_fail_exit_rate: 0.404221
mean_after_cost_return: -0.001409
median_after_cost_return: -0.006526
big_winner_capture_rate: 0.039660
missed_gain_to_exposure_median: 0.0
turnover_proxy: 15.006477
top1_instrument_year_exposure_share: 0.002043
top5_instrument_exposure_share: 0.009399
```

解读：

```text
1. 这个 baseline 本身不是收益很强的策略。
2. 它几乎覆盖所有 episode，probe_rate 接近 99%。
3. fast-fail 触发率高，说明 launch pool 中 false positive 很多。
4. 它提供了一个干净、低仓位、同口径、可执行的 frozen baseline。
```

R02 / R03 的价值不在于证明 R01 baseline 很强，而在于证明模型和 schedule 可以在不改变 pool / label / baseline 的前提下，显著减少 probe 频率并改善 after-cost return。

---

## 3. Requirement 02 解读：hazard timing 是当前最有价值的正向发现

R02 使用 frozen pool、frozen label、frozen baseline，训练一个 discrete-time three-class hazard model：

```text
target_first
stop_first
neither
```

probe score 定义为：

```text
score_probe_day = P(target_first) - P(stop_first) - missed_gain_penalty
```

R02 不是 full trading strategy，也不是 BaseRate bridge。它只回答：

```text
一个预注册 hazard score 能否在 frozen launch pool 中选择更少、更好的 probe day？
```

### 3.1 R02 相对 R01 的核心结果

```text
validation:
  mean_after_cost_return_diff vs R01 = +0.005353
  median_after_cost_return_diff vs R01 = +0.006526
  big_winner_coverage_loss = 0
  turnover_reduction = 0.940514
  top1 instrument-year exposure share = 0.019231

robustness:
  mean_after_cost_return_diff vs R01 = +0.005210
  median_after_cost_return_diff vs R01 = +0.006500
  big_winner_coverage_loss = 0
  turnover_reduction = 0.941117
  top1 instrument-year exposure share = 0.020134
```

解读：

```text
1. R02 把 R01 的 almost-all-episode probe 变成约 19%-21% 的低频 probe。
2. validation / robustness 上都相对 R01 有正 after-cost lift。
3. 相对 daily BaseRate turnover reference，turnover reduction 约 94%。
4. validation / robustness 中没有额外损失 big-winner coverage。
5. top1 instrument-year exposure share 约 2%，不是少数股票年份撑起来的结果。
```

我的判断：

```text
R02 是当前 EP2 中最关键的正向发现。
它说明 frozen launch pool 内确实存在一个短周期、低频、可执行的 timing structure。
```

---

## 4. Requirement 03 解读：confirm_add bridge 改善短期收益，但仍未解决 holding

R03 把 R02 的 hazard probe 组装成 deterministic schedule：

```text
hazard_probe_confirm_add_fast_fail
```

规则：

```text
1. R02 selected probe 后先建 0.30 仓位；
2. probe 后 +1 到 +3 个交易日内寻找最早 valid confirm_add；
3. confirm_add 后目标权重变成 1.00；
4. 仍使用 fast-fail 和 H=10 natural exit；
5. BaseRate row-level 数据只能用于 overlap audit，不能反向影响 schedule。
```

### 4.1 R03 schedule 结果

```text
validation:
  episode_count = 532
  exposed_count = 104
  probe_rate = 0.195489
  confirm_add_rate = 0.139098
  fast_fail_exit_rate = 0.015038
  mean_after_cost_return = 0.008592
  p05 = -0.007543
  p95 = 0.080889
  big_winner_capture_rate = 0.046512
  turnover_proxy = 7.920000

robustness:
  episode_count = 770
  exposed_count = 149
  probe_rate = 0.193506
  confirm_add_rate = 0.142857
  fast_fail_exit_rate = 0.031169
  mean_after_cost_return = 0.005769
  p05 = -0.018225
  p95 = 0.057771
  big_winner_capture_rate = 0.023622
  turnover_proxy = 8.044364
```

解读：

```text
1. R03 没有扩大 probe 覆盖率，probe rate 仍约 19%-20%。
2. confirm_add rate 约 14% 是以全部 episode 为分母；若只看已 probe episode，
   validation 约 74/104 = 71.15%，robustness 约 110/149 = 73.83%，
   说明一旦 probe，大多数会进入 confirm_add。
3. mean after-cost return 高于 R02 simple-stop。
4. turnover proxy 从 R02 的约 3 提高到约 8，但仍远低于 daily BaseRate reference。
5. strict big-winner capture rate 仍然很低。
```

### 4.2 R03 的真实含义

R03 证明的是：

```text
在 R02 hazard-selected probe 上，
一个 deterministic confirm_add 可以进一步提高短期 after-cost return，
同时不明显扩大 probe 覆盖率、不明显恶化 concentration。
```

R03 没有证明的是：

```text
1. 这是完整策略；
2. 它能充分持有 big winner；
3. 它能在组合层跑赢 BaseRate；
4. 它已经解决 exit / holding / position management。
```

---

## 5. BaseRate overlap 解读：EP2 不是简单复制 BaseRate TopK

R03 的 BaseRate 部分是 audit-only。BaseRate rows 必须在 schedule action / exposure artifacts 生成后才读取，且不能影响 threshold、stop-risk ceiling、probe date、confirm_add rule 或 schedule selection。

当前 overlap 结果显示：

```text
validation:
  BaseRate trade overlap rate = 0.005618
  uncovered exposure share = 0.994382
  uncovered mean after-cost return = 0.044379
  uncovered big-winner capture rate = 0.125000

robustness:
  BaseRate trade overlap rate = 0.054054
  uncovered exposure share = 0.945946
  uncovered mean after-cost return = 0.033847
  uncovered big-winner capture rate = 0.068182
```

解读：

```text
1. EP2 exposure 大部分没有被 BaseRate primary buy / trade 覆盖。
2. EP2 暂时更像独立低频 event opportunity set，而不是 BaseRate TopK 的简单子集。
3. 但这仍然不是组合层收益比较。
4. BaseRate integration 必须等 holding / exit 定义后再做。
```

---

## 6. 当前结果的真实边界

### 6.1 已经证明的事情

```text
1. Frozen launch pool 和 label / baseline 合同可用。
2. 短周期 confirm-validity label 是可学、可审计的。
3. R01 no-model baseline 提供了公平对照。
4. Hazard timing 可以显著减少 probe 频率。
5. Hazard timing 相对 no-model baseline 在 validation / robustness 上有正 after-cost lift。
6. Deterministic confirm_add 可以进一步提高短期 after-cost return。
7. EP2 exposure 与 BaseRate primary trade 重合度很低。
```

### 6.2 尚未证明的事情

```text
1. EP2 是完整策略。
2. EP2 能长期持有 big winner 主升段。
3. EP2 能在组合层跑赢 BaseRate。
4. EP2 的 exit / holding 规则已经合理。
5. EP2 可以进入 P1 或 freeze strategy。
6. EP2 可以用当前 H=10 natural exit 直接回测组合年化收益。
```

---

## 7. 最大未解决问题：holding / exit

当前 R03 的最大短板不是 entry，而是：

```text
big-winner strict capture rate 很低。
```

当前 R03 的 strict capture 定义很严格：

```text
必须在 +50% target 到来前有 exposure，
并且在达到 +50% target 当天仍未完全退出。
```

R03 中：

```text
validation big_winner_capture_rate = 0.046512
robustness big_winner_capture_rate = 0.023622
```

这说明：

```text
R03 确实能抓到短期正 expectancy，
但它大多没有把 exposure 延展到 big-winner 主升段。
```

因此，下一阶段不应该继续改 entry / hazard / label，而应该研究：

```text
如何在 R03 的 first exposure / confirm_add 之后，
用 deterministic、预注册、可执行的 holding / exit 规则，
提高 big-winner capture，
同时不吞掉短期 after-cost edge。
```

---

## 8. 建议下一阶段：Requirement 04

建议文件名：

```text
requirement_04_holding_exit_winner_capture_extension.md
```

建议标题：

```text
EP2 Requirement 04: Holding / Exit and Winner-Capture Extension
```

一句话目标：

```text
在不改变 R01 label、R02 hazard threshold、R03 schedule bridge 的前提下，
研究 R03 exposure 后如何延长 / 分层 / 退出持仓，
以提高 +50% big-winner capture，
并控制 after-cost return、tail loss、turnover、blocked exit 和 concentration。
```

### 8.1 R04 的 frozen inputs

R04 不得改变：

```text
frozen launch pool
primary label: confirm_h10_u10_d06_conservative_fail
R01 frozen baseline: probe_with_simple_stop
R02 selected threshold: 0.3205667777673395
R02 selected stop-risk ceiling: 0.27410397287415667
R03 schedule bridge: hazard_probe_confirm_add_fast_fail
probe weight: 0.30
confirm_add window: probe +1 to +3 trading days
confirm_add target weight: 1.00
fast-fail base rule
```

R04 可以研究的只有：

```text
natural exit horizon
confirmed-position holding extension
winner-hold mode
trailing / break-even / time-stop variants
partial exit / scale-down variants
```

---

## 9. R04 候选 holding / exit families

R04 第一版不应把所有候选 family 都作为可选搜索空间。validation 中 R03 exposure 数量有限，过大的 holding / exit matrix 很容易变成新的参数搜索。建议将 R04 分成：

```text
primary pre-registered matrix:
  用于 validation selection 与 robustness holdout。

diagnostic-only counterfactuals:
  只解释机制，不允许成为 promoted schedule。
```

### 9.1 Baseline family

```text
R03_original_H10:
  保留 R03 当前规则，H=10 natural exit。
```

这是所有 R04 variant 的主对照。

### 9.2 Primary matrix：小型预注册规则集合

```text
R03_original_H10:
  R03 当前规则，H=10 natural exit。

R03_confirmed_H20:
  未触发 confirm_add 的 probe 仍 H=10 出；
  已触发 confirm_add 的 full exposure 允许 H=20；
  用于测试短延长是否已经足够。

R03_confirmed_H60:
  未触发 confirm_add 的 probe 仍 H=10 出；
  已触发 confirm_add 的 full exposure 允许 H=60；
  用于测试中期趋势持有是否能明显提升 winner capture。

R03_confirmed_H120:
  未触发 confirm_add 的 probe 仍 H=10 出；
  已触发 confirm_add 的 full exposure 允许 H=120；
  用于测试长 winner hold，但必须通过更严格的 drawdown / concentration gates。

R03_winner_state_hold_H120:
  已 confirm_add 后进入 normal hold；
  若满足可观测 winner-state，则下一交易日进入 winner hold；
  winner hold 使用 H120 上限和 trailing / profit-floor exit。
```

目标：

```text
1. 只让已经通过 confirm_add 的 exposure 延长持有；
2. 分层检验 H=10 是否过早退出 winner：
   H20 = 短延长，H60 = 中期趋势，H120 = 长 winner hold；
3. 避免把未确认的 probe 全部延长，导致 tail loss 扩大；
4. 避免把 20 / 40 / 60 / 120 全部作为平等搜索空间，
   将 R04 从参数扫表收敛成少量可解释假设。
```

H40 可以保留，但更适合放入 diagnostic-only interpolation，而不是 primary selection。原因是 H40 夹在 H20 与 H60 之间，信息增量不如 H60 / H120 明确；如果 H20 与 H60 的结果方向不一致，再用 H40 解释曲线形态即可。

### 9.3 Winner-hold execution rule must be observable

R04 不允许使用 label target 作为交易退出条件。例如：

```text
hold_to_50h120_target_or_H60
```

这种写法有 lookahead / 不可执行歧义，因为 `50h120 target` 是事后标签概念。正式 requirement 中必须改成可观察状态机，而不是“固定持仓时长 + 固定盈利阈值”的单点规则：

```text
normal_hold:
  已 confirm_add 的 exposure 默认进入 normal hold；
  使用对应 schedule 的 H20 / H60 / H120 natural exit；
  fast-fail 与 blocked-exit retry 继续沿用 R03 mechanics。

winner_state_entry:
  已 confirm_add；
  且 close_return_from_first_exposure >= +12%；
  且 max_drawdown_since_first_exposure <= 8%；
  且 current close > confirm_add_price；
  且未触发 fast-fail state；
  则下一交易日 open 起进入 winner hold。

winner_state_exit:
  H120 natural exit；
  或从进入 winner hold 后的最高 close 回撤 15%；
  或 close 跌破 first_exposure_price * 1.03 的 profit floor；
  或 close 跌破 confirm_add_price；
  所有退出均 next-open 执行，并沿用 blocked-exit retry。
```

注意：

```text
1. +15% 不应作为唯一 promoted rule；
2. +10% / +12% / +15% / +20% 可以作为 diagnostic sensitivity；
3. trailing / profit floor 不能成为新的 entry filter，只能作用于已经有 exposure 的持仓；
4. winner hold 是持仓状态转换，不是新的买入信号。
```

### 9.4 Diagnostic-only counterfactuals

以下规则可以作为机制解释，但不进入 R04 promoted schedule selection：

```text
R03_all_H20:
  所有 exposure 的 natural exit 从 H=10 改为 H=20。

R03_all_H40:
  所有 exposure 的 natural exit 从 H=10 改为 H=40。

R03_confirmed_H40:
  只延长 confirmed exposure 到 H=40；
  用于解释 H20 和 H60 之间的插值形态。

winner_state_gain_threshold_sensitivity:
  +10% / +15% / +20% winner-state entry threshold；
  只用于敏感性分析，不参与 promoted schedule selection。

winner_state_trailing_sensitivity:
  10% / 15% / 20% trailing drawdown；
  只用于解释 exit tightness，不参与 promoted schedule selection。

R03_no_fast_fail:
  禁用 fast-fail，用于量化 fast-fail 的 tail-risk 价值。

R03_relaxed_fast_fail:
  放宽 fast-fail drawdown，用于解释 fast-fail 是否过早错杀 winner。

half_exit_at_10d_keep_half_to_H40
half_exit_after_15pct_gain_keep_half_trailing
```

目标：

```text
1. 区分“holding 延长是否有效”和“是否只因为删除风险保护才有效”；
2. 量化 fast-fail 对 mean return、p05、max adverse excursion 和 big-winner capture 的影响；
3. 检查固定 H20 / H60 / H120 是否存在非线性；
4. 检查 winner-state 是否真的优于单一 +15% 阈值；
5. 为 R05 / later portfolio design 提供机制解释。
```

---

## 10. R04 主指标

R04 不能只看 mean return。至少需要同时报告：

```text
mean_after_cost_return
median_after_cost_return
p05_after_cost_return
p95_after_cost_return
max_adverse_excursion
mean_holding_days
median_holding_days
turnover_proxy
blocked_sell_rate
blocked_exit_retry_rate
natural_exit_rate
fast_fail_exit_rate
confirm_add_rate
winner_hold_mode_entry_rate
big_winner_capture_rate_50h120
big_winner_capture_count_50h120
big_winner_capture_rate_100h240 sensitivity
big_winner_coverage_loss_vs_R03
mean_return_diff_vs_R03
p05_return_diff_vs_R03
top1_instrument_year_exposure_share
top5_instrument_exposure_share
```

### 10.1 必须重点看 tail loss

如果某个 holding extension 提高了 big-winner capture，但：

```text
p05_after_cost_return 明显恶化；
max adverse excursion 明显恶化；
blocked_exit_retry_rate 上升；
或 concentration 上升；
```

则不能视为通过。

---

## 11. R04 Go / No-Go 建议

### 11.1 允许进入 R05，当且仅当

```text
1. 至少一个 R04 holding / exit variant 在 validation 和 robustness 上提高 big_winner_capture_rate；
2. mean_after_cost_return 不显著低于 R03；
3. p05_after_cost_return 不显著恶化；
4. turnover_proxy 不失控；
5. blocked_sell / blocked_exit_retry 不主导结果；
6. top1 instrument-year exposure share <= 0.10；
7. top5 instrument exposure share <= 0.35；
8. 不需要修改 R01 / R02 / R03 frozen contract 才能通过。
```

### 11.2 如果 R04 失败

如果所有 holding extension 都失败，应停止“big-winner holding system”解释，改写 EP2 定位：

```text
EP2 是短周期、低换手、launch exposure timing alpha，
不是 big-winner 主升段捕获系统。
```

这时下一步不应继续优化 entry，而应研究：

```text
risk-filter overlay
BaseRate bad-trade avoidance
short-horizon event sleeve
```

---

## 12. Requirement 05 建议：BaseRate Integration / Attribution Bridge

R05 应该在 R04 之后，而不是现在。

R05 的目标不应是简单比较：

```text
EP2 annual return vs BaseRate annual return
```

而应回答：

```text
1. EP2 未覆盖于 BaseRate 的 exposure 是否能成为独立 sleeve？
2. BaseRate 已持仓时，EP2 confirm_add 是否支持加仓？
3. BaseRate 持仓中触发 EP2 fast-fail 是否能减少亏损？
4. EP2 与 BaseRate 是否存在冲突：BaseRate 卖出但 EP2 加仓，或 BaseRate 买入但 EP2 fast-fail？
5. EP2 是否能作为 BaseRate 的 timing overlay / risk overlay？
```

R05 之前必须先有 R04 定义的 holding / exit，否则 EP2 仍然不是完整 exposure process。

---

## 13. 当前不建议继续做什么

当前不建议：

```text
1. 不重新选择 primary label；
2. 不修改 10d / +10% / -6% primary label；
3. 不改变 R02 selected threshold；
4. 不扩 hazard feature bank；
5. 不做 Alpha158 path-to-primitive；
6. 不回到行业专用 LGBM；
7. 不把 R03 schedule-only 结果直接与 BaseRate annual return 比较；
8. 不把 uncovered mean return 直接解释成可组合化收益；
9. 不忽略 strict big-winner capture rate 低的问题；
10. 不把删除 fast-fail 后的结果直接推广为正式 schedule；
11. 允许把 no-fast-fail / relaxed-fast-fail 作为 diagnostic counterfactual，
    用来量化 fast-fail 的 tail-risk 价值。
```

---

## 14. 决策树

```text
Current state:
  R01/R02/R03 passed
  -> proceed to R04 holding / exit

R04 passes:
  -> proceed to R05 BaseRate Integration / Attribution Bridge

R04 fails:
  -> stop big-winner holding interpretation
  -> reframe EP2 as short-horizon launch timing signal or risk-filter overlay

R05 passes:
  -> consider portfolio-level EP2 + BaseRate integration study

R05 fails:
  -> keep EP2 as standalone low-frequency event sleeve diagnostic or stop integration branch
```

---

## 15. Final recommendation

当前 EP2 是一个值得继续的方向，但继续点不在 entry，而在 holding / exit。

建议：

```text
1. 冻结 R01 / R02 / R03 当前合同；
2. 不重新调 label、threshold、feature 或 launch pool；
3. 立即生成 Requirement 04；
4. R04 只研究 holding / exit / winner capture extension；
5. R04 通过后，再进入 R05 BaseRate integration；
6. R04 失败则停止 big-winner holding 解释，把 EP2 降级为 short-horizon timing / risk-filter overlay。
```

一句话：

```text
EP2 当前不是失败，而是第一次证明了一个低频 launch exposure timing 信号；
但真正决定它有没有策略价值的，不是继续优化 entry，
而是能否把 R03 的短期 positive expectancy 延展成可持有、可组合化、可控制尾部风险的 exposure process。
```

---

## 16. Source artifacts

本讨论基于以下阶段性文件和报告：

```text
requirement_01_label_and_baseline_freeze.md
requirement_02_hazard_timing_model.md
requirement_03_schedule_bridge.md
requirement_01_02_03_experiment_summary.md
```
