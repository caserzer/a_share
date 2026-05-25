# EP5 discussion2：R08.2 / R08.3 之后的 R09 方向收敛

> 生成日期：2026-05-25
> 状态：研究方向讨论记录，不是 requirement，不是策略冻结，不是 validation。
> 背景：基于 `ep5/discussion.md` 的 exposure-unit framing，以及 R01-R08.3 的已完成诊断结果。本文只讨论 R08.2 / R08.3 之后 EP5 是否应继续、如何继续，以及下一步 R09 应该问什么问题。

---

## 0. TL;DR

R08.2 和 R08.3 合在一起，把 EP5 的方向明显收窄了：

```text
R08.2:
  daily-observed vwap_deviation H3
  diagnostic-supported
  authorized_strategy_requirement = false

R08.3:
  daily-observed volume/rank families H3
  no family support
  authorized_strategy_requirement = false
```

因此当前不能得出：

```text
daily observation 本身普遍有效；
R08.2 可以直接进入策略构造；
R08.3 中某个 H5/H10 diagnostic 可以救回 H3；
应该继续批量扫描更多 family。
```

更合理的结论是：

```text
daily observation 解决了一部分样本密度 / overlap-control / cleanliness 问题，
但只有 vwap_deviation 在当前证据链中真正通过了 H3 diagnostic gates。

下一步应围绕 vwap_deviation H3 写一个 confirmatory diagnostic，
先确认它到底是 stock-level residual edge、beta/regime residual，
还是执行 / 成本之后不可经营的表面 spread。
```

所以 R09 的定位应该是：

```text
R09 = vwap_deviation H3 confirmatory diagnostic
不是 strategy requirement
不是 portfolio construction
不是 horizon shopping
不是 family sweep
```

---

## 1. 当前 EP5 已知地图

| 模块 | 状态 | 关键结论 |
|:--|:--|:--|
| R01 short-horizon feasibility probe | 已完成 | 本地短周期 exposure-unit feasibility 的第一批读数。 |
| R02 RS20 continuation | 已完成 | 简单延续型不成立。 |
| R03 downside volatility shock rebound | 已完成 | 反弹型不成立。 |
| R04-R06 GTJA191 family 系列 | 已完成 | residual composite / factor decay audit 给出 family-level 信息含量地图，但没有直接策略授权。 |
| R07 short-horizon timing failure attribution | 已完成 | 失败归因明确，说明不能靠状态切片自然修复。 |
| R08 / R08.1 vwap_deviation H3 weekly | 已完成 | weekly H3 spread 有，但 validation breadth、monotonicity、concentration 不够干净。 |
| R08.2 daily vwap_deviation H3 | diagnostic supported | H3 spread 约 22-27bp，breadth、anchor、fold、monotonicity、concentration 均通过；但不授权策略。 |
| R08.3 daily volume/rank families H3 | no support | 三个非 vwap family 全部没有 H3 support，证伪了 daily 化通用论。 |

EP5 现在不是一个多 family 平行探索问题。它已经收缩到一个唯一通过 diagnostic 门禁的候选：

```text
daily-observed vwap_deviation H3 within-stock state
```

R08.2 的 supported 应理解为：

```text
研究解封；
允许进入更严格的 confirmatory diagnostic；
不允许直接写策略或 production signal。
```

R08.3 的 no support 应理解为：

```text
daily 化不是方法学 inflation；
也不是所有 within-stock / rank / volume family 都能被 daily observation 修复；
后续不能把 R08.2 的成功泛化成 family sweep。
```

---

## 2. 从 discussion.md 继承的边界

`ep5/discussion.md` 的核心框架仍然有效：

```text
EP5 不是继续经营 big-winner episode；
EP5 要先确认是否存在 action-time、after-cost、validation-first 的 exposure unit。
```

R08.2 给了一个候选 exposure unit，但还没有回答三个问题：

1. 它是否是 stock-level residual edge，而不是 beta / industry / size / liquidity residual？
2. 它在 next-open、110bps cost、停牌 / 涨跌停、turnover 和库存碰撞下是否仍然可经营？
3. H3 到 H5/H10 的 persistent state shape 是否仍然成立，还是 horizon 累积了 beta/regime contamination？

因此 R09 不是从 R08.2 直接升级策略，而是把 R08.2 的 supported 拆成可否继续的 confirmatory evidence。

还要保留 `discussion.md` §6.1 的 absolute / relative 双层解释：

| absolute | relative / residual | 解释 |
|:--|:--|:--|
| positive | positive | 最强，说明 exposure unit 可能具备 long-only 和 residual 两层支持。 |
| negative | positive | 可能有 stock-level edge，但 long-only beta / regime pressure 阻断。 |
| positive | weak / negative | 可能主要是 market beta 或 common exposure，不应当作 stock-selection edge。 |
| negative | negative | 当前 candidate 没有继续价值。 |

这个框架不会放宽 validation-first 纪律。它只是避免把 2022-2023 的 beta/regime concentration 简单误读成“所有 stock-level edge 都不存在”，也避免把 bad validation 当成忽略失败的借口。

---

## 3. R09 的推荐主线

### 3.1 R09.1 Beta / Industry / Size / Liquidity Decomposition

最高优先级是先拆 `vwap_deviation` H3 的 spread 来源。

要回答的问题：

```text
R08.2 的 22-27bp H3 spread，
到底是 stock-level within-stock edge，
还是 industry / size / liquidity / beta residual？
```

建议的 diagnostic 口径：

1. industry-neutral matched comparator；
2. size-neutral matched comparator；
3. liquidity-neutral matched comparator；
4. multi-constraint matched comparator；
5. absolute spread 与 relative / residual spread 同表报告。

判读：

| 结果 | 解释 | 下一步 |
|:--|:--|:--|
| absolute 和 relative 都保留 | vwap_deviation H3 可能是真 stock-level exposure unit。 | 进入 R09.2 / R09.3。 |
| absolute 保留，relative 消失 | spread 可能主要来自 beta / common exposure。 | 做 beta/regime attribution，不进入策略。 |
| absolute 消失，relative 保留 | long-only deployability 被阻断，但 residual edge 可能存在。 | 条件性进入 hedged / relative framing。 |
| 两者都消失 | R08.2 可能是未剥离 common exposure 的表面读数。 | 终止该主线。 |

R09.1 应先于 fold 2 子样本剖析。否则 fold 2 的负 spread 可能被过早解释成行业 / 市值 / 流动性问题，而不是通过 matched comparator 先证实。

### 3.2 R09.2 Fold 2 Weak-Spread Decomposition

R08.2 validation fold 2 是唯一负 spread fold：

```text
validation fold 2 mean spread = -0.0731%
positive instrument share = 63.27%
decile monotonicity = 0.6121
```

它更像 fold-specific weak spread，而不是完整 transfer failure。但 R09 仍需要解释它。

建议拆分维度：

1. industry；
2. size；
3. liquidity；
4. volatility regime；
5. calendar time window；
6. market beta / broad market state；
7. bucket edge 与 factor-direction stability。

目标不是把 fold 2 修成正数，而是判断：

```text
fold 2 是可解释的 sub-regime fragility，
还是 R08.2 supported 里隐藏的结构性弱点？
```

如果 fold 2 负 spread 只在某个明显 regime / industry / liquidity pocket 集中，并且 matched comparator 后 residual edge 仍然保留，可以继续。若 fold 2 的负 spread 在多维拆分后仍无解释，R09 应降低 vwap_deviation 的可经营信心。

### 3.3 R09.3 Executability / Turnover / After-Cost Exposure Audit

这一段必须保持 diagnostic，不应提前写成 portfolio requirement。

不建议使用：

```text
top-quintile long-only portfolio simulation
```

作为主措辞，因为它容易把 R09 推到策略构造层。

更合适的定位是：

```text
after-cost exposure-unit executability audit
```

要回答的问题：

1. next-open execution 后，状态暴露的 gross / net spread 是否仍保留？
2. 110bps round-trip cost 下，spread 被吃掉多少？
3. daily observation 带来的 turnover 有多高？
4. 同一股票连续触发造成的 inventory overlap / collision 有多重？
5. 停牌、涨跌停、不可成交样本是否系统性偏向某个 bucket？
6. signal collapse 后，样本是否仍足够？

这里可以构造最小 exposure replay，但它只能用于 audit，不生成策略授权：

```text
允许：
  report exposure-unit net spread
  report turnover / holding overlap
  report blocked execution share
  report inventory collision
  report after-cost degradation

不允许：
  选择 top-N / top20% 作为生产组合
  调仓优化
  权重优化
  horizon switching
  根据 validation 调 threshold
  写 strategy requirement
```

判读：

| R09.3 结果 | 解释 |
|:--|:--|
| after-cost 仍为正，turnover / collision 可控 | 可以讨论下一层 confirmatory 或 relative framing。 |
| before-cost 正，after-cost <= 0 | R08.2 不可直接 long-only 落地；若 R09.1 relative edge 保留，可转入 hedged / relative feasibility。 |
| execution-blocked 样本集中 | 需要先解释可执行性偏差，不能继续策略化。 |
| collapse 后样本过薄 | R08.2 的 daily diagnostic 不能自然升级到 executable exposure。 |

### 3.4 R09.4 Persistent State Shape Confirmation

R08.2 的 H5/H10 diagnostic 也是正的，说明 `vwap_deviation` 不像 H3-only micro effect：

```text
validation: H3 +0.2710%, H5 +0.4417%, H10 +0.8393%
robustness: H3 +0.2178%, H5 +0.2879%, H10 +0.3795%
```

但 H5/H10 仍然不能替代 H3，也不能救回 H3。R09.4 只应确认：

```text
H3 -> H5 -> H10 的 persistent state shape
是否在 matched comparator / beta-regime decomposition 后仍然存在？
```

如果 neutralized H5/H10 仍保持正向且不集中，说明状态可能有持续性。如果 neutralized 后消失，则原始 horizon shape 可能只是 beta/regime 累积。

---

## 4. 条件性主线 B：Hedged / Relative Framing

`discussion.md` §7.3 的 hedged / relative framing 仍应默认暂不启动。

触发条件需要严格：

```text
只有当：
  1. R09.1 显示 relative / residual edge 在多个 matched comparator 下稳定；
  2. R09.3 显示 long-only after-cost / executability 被阻断；
  3. H3 primary edge 没有被 H5/H10 horizon shopping 替代；
才允许启动 hedged / relative framing。
```

如果触发，方向也不是立即写 pair-trading 策略，而是先做 feasibility diagnostic：

1. 同日同行业 matched long-short；
2. 同市值 / 同流动性 matched long-short；
3. beta-neutral residual replay；
4. 做空腿可获得性；
5. ETF hedge 与个股 hedge 的成本差异；
6. A 股融资融券约束和容量约束。

关键边界：

```text
hedge 不是免费的；
relative edge 不是 strategy pass；
long-only 失败不能自动转 hedged；
只有 stable residual edge 才能触发 relative framing。
```

---

## 5. 受控横向延展

R08.3 已经证伪了：

```text
daily 化对 volume/rank family 通用有效。
```

因此不建议再做：

1. EP4 family 大范围重开；
2. R04/R06 GTJA191 family 批量扫描；
3. volume/rank family winner selection；
4. 用 R08.3 的 H5/H10 反向生成 H3 需求；
5. 用 single-factor family 写 H3 策略。

横向延展只有在 R09 继续通过后才有意义。即使要做，也只能小步：

```text
只选择少数信息含量曾经偏高、
且具有 within-stock state 语义的 family；
使用 R08.2 同等严格 gate；
不放宽 sample / concentration / monotonicity；
不做 cross-family score；
不以 validation 表现选择 family。
```

如果没有第二个 family 通过，结论就应收窄为：

```text
daily within-stock state 在当前证据下是 vwap_deviation 特例。
```

---

## 6. 明确不做的方向

| 不做 | 原因 |
|:--|:--|
| 基于 R08.2 直接写 strategy requirement | R08.2 是 diagnostic-supported，不是 authorized strategy。 |
| 基于 R08.3 选择 family winner | R08.3 明确 no family support，且禁止 cross-family score。 |
| 用 H5/H10 救 H3 | horizon shopping；R08.2/R08.3 都规定 diagnostic horizons 不替代 primary H3。 |
| 把 `volume_surge_money_flow` 包装成 H3 family score | sample、fold、monotonicity、concentration 同时失败。 |
| 把 `rank_ts_rank_structure` 当作 broad family | single-factor caveat，robustness H3 转负。 |
| 重新打开 EP4 family / fresh / allocator | `discussion.md` 已把 EP4 loop 定义为终止背景，不是 EP5 主线。 |
| 继续大规模 family sweep | R08.3 已经给出 daily 化非通用的反证。 |
| 在 R09 中调 threshold / bucket / horizon | R09 是 confirmatory diagnostic，不是 discovery search。 |

---

## 7. EP5 的收敛条件

R09 之后，EP5 应该进入一个明确的四路判定，而不是无限追加实验。

| R09 结果 | 解释 | 后续 |
|:--|:--|:--|
| absolute positive + relative positive + after-cost positive | `vwap_deviation` H3 可能是真正可经营 exposure unit。 | 可以讨论下一阶段 confirmatory 或 very constrained strategy requirement。 |
| absolute negative + relative positive | long-only 被 beta/regime/execution 阻断，但 residual edge 可能存在。 | 条件性启动 hedged / relative feasibility diagnostic。 |
| absolute positive + relative weak/negative | spread 可能主要来自 beta/common exposure。 | 做 beta/regime attribution；不策略化。 |
| absolute negative + relative negative | R08.2 不能转化为可经营 exposure unit。 | 终止 EP5 vwap 主线，考虑 EP6 的 universe / data / horizon 实质切换。 |

最终成功标准可以写成：

```text
EP5 成功条件（满足其一）：

1. vwap_deviation H3 经 R09 confirmatory 后，
   至少得到 long-only after-cost 或 relative-framing 中一个稳定正向 exposure unit；

2. R09 全套确认后明确否决，
   EP5 输出“当前 universe / data / execution / horizon 口径下
   不存在可经营 exposure unit”的终局判定，
   然后启动 EP6 的实质性切换。
```

不允许的失败模式：

```text
用 R08.2 的 diagnostic-supported 当作“差不多可以了”，
然后跳进策略构造。
```

这正是 EP4 已经反复暴露的问题：描述性信息、局部 spread、右尾存在，不能自动升级成 action-time positive expectancy。

---

## 8. 下一步建议

建议下一份正式 requirement 只写：

```text
R09 vwap_deviation H3 confirmatory diagnostic
```

推荐 scope：

1. R09.1 neutralized / matched comparator decomposition；
2. R09.2 validation fold 2 weak-spread decomposition；
3. R09.3 after-cost executability / turnover / collision audit；
4. R09.4 neutralized H5/H10 persistent shape confirmation；
5. strict no-strategy / no-portfolio / no-threshold-search clauses；
6. explicit final decision tree：continue / relative-feasibility / beta-attribution / stop。

R09 的文本需要比 R08.2 更强地防止误读：

```text
R09 通过也不等于 production；
R09 失败则应终止 vwap H3 主线；
R09 不能用 H5/H10 或 portfolio construction 救回 H3；
R09 不能变成新的 family search。
```
