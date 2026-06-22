# Research Plan 3: Winner Label Form Revision and Decoupled Survivor-stage Selector

## 0. 阶段定位

本计划承接 `research_plan_2_stage2_random_baseline_and_defense_participation.md` 以及其后的实跑链条：

- `12A7d_stage2_random_baseline_support_triage`：chained stage-2 的 strict random baseline 无法稳定构造，最终 `12A7d_stage2_signal_diagnostic_only`。
- `12A7e_defense_participation_frontier`：stage-1 X 是 participation throttle 而非 winner separator；没有单一 X 同时兼顾 downside defense 与 winner participation；`12A7e_x030_defense_optimal_for_downside_not_winner`。
- `12A7f_c0_winner_baserate_enrichment_control_diagnostic`：相对同期、同 regime、同 board、同日历配对的非 C0 控制组，C0 在右尾上**确有** enrichment，但同时放大左尾，且 big-winner / long-horizon barrier 支持偏弱；`12A7f_c0_winner_enrichment_weak_or_horizon_dependent`。

本计划不是 implementation requirement，而是 12A7f 之后的研究路线修订。它**改写**了 research_plan_2 中“先怀疑 event 选错”的假设：12A7f 已证伪“C0 选错人群”，瓶颈被重新定位到 **winner label 形态** 与 **架构拓扑**，而不是 event 选择。

核心判断：

```text
C0 event is not the wrong population. It is a two-tailed volatility amplifier.
The unresolved bottleneck is the winner label form and the serial architecture,
not the event definition.
The next decisive question is separability, not base-rate enrichment:
can a vol-scaled winner label make the right tail single-feature separable
on the left-tail-cleaned survivor pool?
```

## 1. 12A7f 带来的三个决定性事实

裁决是 `weak_or_horizon_dependent`，但报告中的三张表比裁决本身更重要。

### 1.1 C0 是双尾放大器，不是 winner-only event

12A7f Fast-fail Contrast（robustness）：

```text
C0 fast-fail      = 0.3059
control fast-fail = 0.2466
fast_fail_diff    = +0.0592
```

同一 robustness split，direct-entry `+20% / 20d`：

```text
C0 rate      = 0.1552
control rate = 0.1236
winner_diff  = +0.0316, CI95 [+0.0109, +0.0522]
```

含义：C0 同时把左尾（fast-fail）和右尾（big-winner）都放大了。它不是天然的 winner-only selector，而是一个高波动、高机会、高风险的候选池。**这证伪了 research_plan_2 中“C0 可能选出平庸标的”的猜测，event 定义层不需要回退。**

### 1.2 先做防守后，右尾 enrichment 显著变干净

同一 `+20% / 20d`，两个 readout 视角对比（robustness）：

```text
direct_entry (裸入场):
  C0 0.1552 vs control 0.1236, diff +0.0316, CI [+0.0109, +0.0522]

survivor_conditional (先过 no_fast_fail_L10_H20):
  C0 0.2146 vs control 0.1575, diff +0.0567, CI [+0.0304, +0.0830]
```

含义：清掉左尾后，右尾 enrichment 幅度接近翻倍且 CI 更远离 0。**防守不是单纯牺牲 participation，它净化了右尾人群。** 这是“防守与选择应解耦、且 winner selector 应跑在 survivor 池上”的直接证据。

### 1.3 Enrichment 存在强 regime / time 漂移

12A7f Calendar Year（`+20% / 20d` diff 摘选）：

```text
2018 +0.0145   2019 +0.0078   2020 +0.0178   2021 +0.0216
2022 +0.0027   2023 +0.0107   2024 +0.0343   2025 +0.0294
```

含义：右尾 enrichment 近年明显更强，早年偏弱。固定 `+20% / -10%` 矩形 barrier 在不同年份含义不同——这与 12A6c→12A7 一路的 prior shift 同源，现在在 event 富集层面再次显形。**固定全样本 threshold 不可迁移；winner label 必须 regime-aware（vol-scaled）。**

### 1.4 label 形态敏感性的旁证

12A7f direct-entry / unconditional / robustness 显示：

```text
+15% / 20d : diff +0.0318, CI [+0.0066, +0.0560]  -> positive
+20% / 20d : diff +0.0316, CI [+0.0109, +0.0522]  -> positive
+20% / 40d : diff +0.0296, CI [-0.0000, +0.0597]  -> uncertain
```

`+15%/20d` 比 `+20%/40d` 更稳，说明“赢家”的形态对阈值与 horizon 极敏感，单一矩形 barrier 抓不准 big-winner。

## 2. 研究路线的修正

### 2.1 嫌疑重排

```text
research_plan_2 假设:
  suspect_1 = winner label form
  suspect_2 = C0 event selection（需先证伪）

12A7f 之后:
  C0 event selection 已证伪（确有右尾 enrichment）。
  确定瓶颈 = winner label form + architecture topology。
  event definition layer NOT to be rebuilt.
```

### 2.2 关键问题从 base-rate 变成 separability

12A7f 证明的是 base-rate enrichment（C0 右尾统计上更厚）。但 base-rate 更厚不等于可预测：

```text
flat base rate without separability = not useful
high base rate without separability = still not a deployable selector
```

因此下一步的 go/no-go 不再是“C0 富不富集”，而是：

```text
在已清左尾的 C0 survivor 池上，用 vol-scaled / 路径敏感 winner label，
右尾赢家是否单特征可分（不只是 base-rate 更高）？
```

### 2.3 架构从串联改为解耦 overlay + survivor-stage selector

```text
old (12A6c..12A7e):
  serial: stage-1 X defense gate -> stage-2 selector on chained survivors
  同一个 X 同时承担防守与右尾捕获 -> 12A7e 证明此架构对 big-winner 错配。

new:
  defense overlay (volatility_20d asc, already supported) 固定为风险层;
  winner selector 在 left-tail-cleaned survivor pool 上独立建立;
  defense 与 winner-capture 是两个目标，不再用单一 X 串联。
```

12A7f §1.2 已证明 survivor 池是右尾信号最干净的地方，所以 selector 的分母应是 survivor 池，而非裸 entry。

## 3. 当前已落袋资产（不重做）

```text
1. C0 event 富集右尾，event 定义层不回退。
   robustness direct-entry +20%/20d diff +3.16pp, CI 下沿 +1.09pp。

2. stage-1 downside defense 有独立价值，必须保留为 overlay。
   12A7b robustness delta_vs_random_p50 -8.20pp, CI [-9.96, -6.37];
   12A7f robustness C0 fast-fail 比 control 高 +5.92pp，左尾必须清。

3. 防守净化右尾的结构已被量化。
   survivor-conditional +20%/20d diff +5.67pp vs direct-entry +3.16pp。

4. 固定矩形 barrier 不可迁移（regime 漂移已显形），必须 vol-scaled。
```

## 4. 推荐序列

```text
P0:   12A7g survivor-pool vol-scaled winner-label separability diagnostic（go/no-go 闸）
P0/P1:12A7h decoupled defense-overlay + survivor-stage winner selector（仅当 P0 可分）
P2:   12A8  probability / budget calibration（仅当 selector 立住后）
不做: event definition layer rebuild（12A7f 已证伪）
```

## 5. 12A7g: Survivor-pool Vol-scaled Winner-label Separability Diagnostic

### 5.1 目的

12A7g 是本计划的 go/no-go 闸。它回答：

```text
在 left-tail-cleaned C0 survivor 池上，
vol-scaled / 路径敏感 winner label 是否让右尾赢家单特征可分，
而不仅仅是 base-rate 更高？
```

它**不**训练复杂模型、**不**做 operating point、**不**声明 alpha。它只度量 label 可分性。

### 5.2 Denominator

```text
scope = C0 risk_on, stage_1_evaluable
survivor pool = no_fast_fail_L10_H20 = true 且 path 可评估的 survivors
理由 = 12A7f §1.2 证明 survivor 池右尾信号最干净
```

裸 entry 池可作为对照诊断，但 go/no-go 裁决基于 survivor 池。

### 5.3 Vol-scaled winner label grid

固定矩形 barrier 必须替换为事件前波动率缩放的 barrier。预注册 grid（具体系数在 requirement 固化）：

```text
vol_reference = 事件前 PIT 波动率（例如 volatility_20d / volatility_60d，t0 可得）

vol_scaled_up_barrier = k_up * vol_reference
vol_scaled_lower_barrier = k_dn * vol_reference

pre-registered k grid 用于检验 winner 形态对缩放系数的敏感性;
同时保留固定 +15% / +20% barrier 作为可比 anchor（与 12A7f 对账）。
```

label 必须 PIT、horizon completeness 显式检查、不可复现即 fail-closed。

### 5.4 Separability 度量（核心，go/no-go 依据）

对每个 vol-scaled label 与每个 anchor label，在 survivor 池上度量**单特征可分性**，而不是只看 base rate：

```text
对 12A6c / 12A7 已有的 t0 / realized-path 候选特征:
  auc_robustness
  rank_ic_robustness
  decile_lift_robustness（top decile winner rate vs base）
  single_feature_separation_spread（最高分 bucket vs 最低分 bucket）
```

必须 train-frozen 选特征方向，validation / robustness readout-only（沿用 12A7 系列纪律）。

### 5.5 go/no-go 裁决

```text
12A7g_winner_label_separable_on_survivor_pool:
  存在 vol-scaled label 使 robustness 上至少一个 PIT 单特征
  auc >= 0.55、rank_ic 跨 split 同号、top-decile lift 显著为正;
  -> 进入 12A7h 解耦 selector。

12A7g_winner_label_baserate_only_not_separable:
  vol-scaled label 仍只有 base-rate enrichment，无单特征可分性;
  -> winner-selection 路线证伪，转向“防守 overlay + 规则化参与”。

12A7g_vol_scaling_does_not_fix_regime_drift:
  vol-scaled label 未能消除 12A7f 观测到的年度/regime 漂移;
  -> 需要先解决 label 时间非平稳，再谈 selector。

12A7g_blocked_input_or_pit_failure:
  输入 / PIT / label 复现 / split boundary 失败。
```

### 5.6 必须正视的天花板

12A7f survivor 池 +20%/20d 仍只是 C0 21.5% vs control 15.8%，绝对幅度不大。因此：

```text
若换 vol-scaled label 后右尾仍仅 base-rate 更厚、个体不可预测，
则 winner-selection 这条路本身要重判，
转向 defense overlay + equal-weight / rule-based participation
（这本身是一个干净、可交付的结论，不是失败）。
```

## 6. 12A7h: Decoupled Defense-overlay + Survivor-stage Winner Selector

仅当 `12A7g_winner_label_separable_on_survivor_pool` 才启动。

```text
defense_overlay = volatility_20d asc（已支持，固定为风险层，不再调 X 来抓 winner）
selector_denominator = left-tail-cleaned survivor pool
selector_label = 12A7g 选出的可分 vol-scaled winner label
selector_discipline:
  train-frozen feature / orientation / operating point;
  strict random baseline support（沿用 12A7d 弱 null 只配弱结论的纪律）;
  低容量优先，复杂模型须显著超过单特征 backbone。
```

架构上 defense 与 selector 解耦：defense 控制左尾暴露，selector 在已净化的 survivor 池上挑右尾，两者不再用同一个 X 串联。

## 7. 12A8: Calibration（后置）

```text
理由:
  12A7f 显示瓶颈是 label form + regime drift，不是概率刻度;
  calibration 修不了“赢家定义随 regime 变”。
  仅当 12A7h selector 立住、需要稳定 budget exposure 时才做。
```

## 8. What Not To Do Next

```text
1. 不回退 event 定义层。12A7f 已证 C0 富集右尾。
2. 不直接做 calibration。label form 与 separability 未解决前，calibration 是空中楼阁。
3. 不在裸 entry 池上建 winner selector。survivor 池右尾更干净（12A7f §1.2）。
4. 不用固定矩形 +20%/-10% barrier 继续建模。regime 漂移已显形，必须 vol-scaled。
5. 不再用单一 stage-1 X 同时承担防守与右尾捕获。12A7e 已证此架构错配。
6. 不在 separability 未通过前增加模型容量。base-rate 厚 != 可预测。
```

## 9. 建议的下一份 requirement

```text
requirement_12a7g_survivor_pool_vol_scaled_winner_label_separability_diagnostic.md
```

它必须显式继承 12A7f 的三个事实（双尾放大、防守后右尾更干净、regime 漂移），把 denominator 锁在 survivor 池，把 vol-scaled label 与固定 anchor 并列，并把 **separability（不是 base-rate）设为 go/no-go 闸**。

延后：

```text
requirement_12a7h_decoupled_defense_overlay_survivor_stage_winner_selector.md
requirement_12a8_winner_selector_budget_probability_calibration.md
```

## 10. Final Recommendation

```text
1. 接受 12A7f 结论：C0 是双尾放大器，event 不退，瓶颈在 label form + 架构。
2. 写 12A7g：survivor 池上的 vol-scaled winner-label separability 诊断，separability 为 go/no-go。
3. 若可分 -> 12A7h 解耦 selector；若不可分 -> 转向防守 overlay + 规则化参与。
4. calibration / event rebuild 都不是下一步。
```

短版：

```text
Stop testing whether C0 enriches winners. It does, weakly and regime-dependently.
Start testing whether a vol-scaled winner label is separable on the cleaned survivor pool.
Separability is the real go/no-go. Everything else waits.
```
