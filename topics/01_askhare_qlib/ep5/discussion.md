# EP5 discussion：从右尾 Episode 管理到正期望 Exposure Unit

> 生成日期：2026-05-20
> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 validation。
> 背景：基于 `ep4/FINAL_REPORT.md` 的终局结论，以及对“是否方向有问题 / 问题定义是否错了”的复盘。EP5 不是 EP4 R05c/R05d，也不是继续修同一组 family / fresh / volume_money / allocator 参数。EP5 只有在问题定义发生实质变化时才允许启动。

---

## 0. TL;DR

EP4 的中途重定义并不是错的。

```text
从“今天能不能预测未来 120 天涨 50%”
改成
“能否用 probe + evidence accumulation + risk budget 管理右尾 episode option”
```

这个改写比继续找单点 big-winner entry 更合理，也帮助研究避免了早期 winner 预测的低信噪比陷阱。

但 EP4 的最终证据说明：

```text
当前 A-share long-only / daily next-open / EP4 evidence family 框架下，
“右尾存在”没有转化为“右尾可被经营成正期望 exposure”。
```

因此，EP5 的起点不能再是：

```text
如何更好地管理 big winner episode？
```

而应该先退回到更底层的问题：

```text
在新的 universe / horizon / execution / hedge framing 下，
是否存在一个 action-time、after-cost、validation-first 的正期望 exposure unit？
```

只有这个问题先通过，才值得重新讨论右尾保留、仓位管理、allocator 或 sleeve composition。

在此前提下，§7.5 给出了一个讨论性的方向排序：主线推荐 7.1 short-horizon exposure timing（用 EP4 学到的纪律重做，不是 EP2 v2），7.2 low-overlap sparse event family 作为 7.1 的事件来源备选，7.3 hedged / relative framing 与 7.4 loss-avoidance / regime allocation 暂不启动（不是永久否决）。

这不是要彻底丢掉 big winner / right-tail diagnostic。更准确的边界是：

```text
big winner 不再是 entry objective；
big winner 不再是 short-horizon exposure pass/fail label；
big winner 不再用来救回一个负期望 exposure unit；

但 big winner 可以保留为 post-entry holding-extension diagnostic：
如果短周期 exposure unit 本身成立，
再讨论哪些持仓状态值得延长 holding、保留一部分右尾 optionality。
```

---

## 1. 对 EP4 方向的判断

EP4 不应被解释为“研究方向一开始就错了”。更准确的解释是：

```text
EP4 提出了一个更合理的问题定义，
然后用一整条实验链把这个问题在当前约束下有效证伪了。
```

EP4 的价值不是找到可上线策略，而是证明以下链条不能成立：

```text
high-recall seed
  -> path / fresh / family evidence
    -> bad-shape filtering
      -> exit / risk-budget
        -> union portfolio
          -> cash allocator / sleeve
            -> OOS positive strategy
```

失败不是来自某一个局部公式，而是每次试图把描述性信息升级为可交易规则时，都会在 action-time / validation-first 约束下被打回。

| 层级 | EP4 发现 | 对 EP5 的含义 |
|:--|:--|:--|
| coverage | 可以覆盖一部分右尾 episode，但触发密度和 entry quality 不足。 | 覆盖率不能再作为主要进展指标。 |
| path evidence | fresh / sequence / stage role 有解释价值，但 survival conditioning 很重。 | 后续信号不能天然当作新入场或加仓信号。 |
| bad-shape filter | 形态坏分没有稳定降低坏路径，还损失 winner。 | 直觉型过滤器不能只靠叙事成立，需要先看到单调性和 OOS 增量。 |
| risk management | exit / stop / sizing 可以压左尾，但不能稳定提高 validation net。 | 少亏不等于方向成立，需要同时讨论正期望和右尾保留。 |
| candidate pool | relative improvement pool 仍不是 alpha pool。 | matched delta > 0 不能替代 validation net > 0。 |
| portfolio | weak pool union 产生伪分散和库存拥挤。 | 组合不是弱信号的免费修复层。 |
| allocator | risk-on full exposure validation 为负，cash allocator 只能少亏。 | overlay 不能替代底层 exposure unit 的 alpha。 |

所以 EP4 的方向不是“荒谬”，但它已经在当前条件下走到终点。

---

## 2. 真正的问题定义漏洞

EP4 暴露出的核心漏洞不是：

```text
entry formula 不够复杂
exit rule 不够聪明
allocator 参数不够细
```

而是：

```text
把“右尾样本存在”误当成“存在可经营的右尾 exposure unit”。
```

这两个命题需要分开。

### 2.1 右尾存在 != 右尾可经营

A 股里当然存在大 winner，也存在许多可以事后解释 winner 形成过程的结构。

但 EP4 的结果反复说明：

```text
winner-anchored structure
path-state confirmation
fresh evidence accumulation
relative left-tail improvement
```

都不能直接推出：

```text
在当时可观察信息下，
next-open 买入，
扣除成本后，
validation split 仍为正期望。
```

EP5 如果继续研究右尾，核心前提应先变成 entry-time exposure unit 本身是否成立，而不是先设计如何经营右尾。

### 2.2 描述性信息 != Action-Time Alpha

EP4 中最容易诱导误判的现象是：

```text
seed-anchor 看起来改善，
fresh-anchor / action-time entry 仍然 bad-heavy。
```

也就是说，很多变量能解释 episode 已经走强，不能证明从该日重新买入后仍有足够剩余收益。

EP5 应默认所有后验描述都只是候选解释，除非它们在 action-time 语境里仍然说得通：

```text
entry date as-of observable
entry price next executable
no future path leakage
validation 上不是显著为负，且不依赖少数右尾才勉强为正
median / p10 / loss rate 不崩
robustness read-only
```

### 2.3 管理模块不能弥补负期望底池

EP4 后半段的最大教训是：

```text
risk budget / exit / cash timing / sleeve allocator
只能改变收益分布形态，
不能凭空创造底层 alpha。
```

如果 full-exposure pool 在 validation 上为负，那么 cash allocator 的收益改善通常只是：

```text
更少暴露
更少亏损
更少右尾
```

这不能作为策略通过。

---

## 3. EP5 的新问题定义

EP5 的主问题可以先讨论为：

```text
是否存在一个新的 exposure unit，
在 changed framing 下至少具备这些方向特征：

1. action-time as-of 可观察
2. next executable price 可执行
3. 扣成本后不依赖少数右尾才勉强成立
4. median / p10 / loss-rate 不被少数右尾掩盖
5. 样本充足且不过度集中
6. robustness 只读不救回
```

这里的关键词是：

```text
exposure unit first,
right-tail management second.
```

这里的 "second" 不是说 right-tail 完全无关，而是说它的位置要后移。完整的两层 working hypothesis 放在 §9；这里先只固定原则：

```text
先讨论 H5/H10/H20 exposure unit 是否独立成立；
再讨论 big-winner / right-tail 是否能作为 holding-extension diagnostic。
```

EP5 第一阶段不应直接问：

```text
怎样把少数 winner 拿得更久？
```

而应先问：

```text
是否存在值得承担风险的基础暴露？
```

如果基础暴露不存在，后续关于 holding、加仓、exit、sleeve、allocator 的讨论价值会很低。

---

## 4. EP5 不应继续做什么

EP5 不应成为 EP4 的参数续集。

禁止方向：

```text
1. 不继续在同一 R02/R03 family set 上做 R05c/R05d。
2. 不把 R04d volume_money relative improvement 包装成 alpha pool。
3. 不用 robustness 正收益反推 validation 失败可忽略。
4. 不把 cash allocator 的回撤改善当作策略通过。
5. 不继续寻找更复杂的 fresh sequence / family order / bad-shape filter。
6. 不在 validation 结果之后微调 threshold、bucket、market state 或 sample gate。
```

这些方向的问题不是“没有完全调好”，而是已经被 EP4 的重复失败模式覆盖。

如果 EP5 只是继续做这些事情，它不是 escape hatch，而是 EP4 overfit loop。

---

## 5. 什么才算实质改变

EP5 至少要改变一个结构性维度，而且这个改变要影响问题定义本身。

| 改变维度 | 合格的 EP5 改变 | 不合格的伪改变 |
|:--|:--|:--|
| universe | 换到明显不同的股票池、行业范围、流动性/市值层、或非 EP4 候选 universe。 | 在 EP4 family pool 内再切一个更窄 bucket。 |
| horizon | 从 H120 big-winner 目标切到 H5/H10/H20 可验证收益、或另一种持有合约。 | 仍以 big-winner label 为核心，只微调 exit day。 |
| execution | 重新定义可执行价格、成交约束、停牌/涨跌停处理和成本模型。 | 沿用 EP4 replay，只改 policy 名称。 |
| hedge / benchmark | 引入 market-neutral、industry-neutral、pair/relative value 或 explicit beta hedge。 | long-only pool 亏损后再用 cash timing 包装。 |
| objective | 改成 loss avoidance、relative value、regime allocation、或 short-horizon exposure timing。 | 继续以“抓大 winner”为主要目标。 |
| event source | 设计 low-overlap sparse event family，先测基础收益分布。 | 扩大 RPS / volume_money / fresh family 的 threshold grid。 |

实质改变的判定标准：

```text
如果 EP4 的负结果仍然直接适用，
那就不是 EP5。
```

---

## 6. 当前讨论焦点：先回到 Exposure Unit

这里还不是 requirement 阶段。当前更重要的是先对齐一个方向判断：

```text
EP4 失败以后，
我们到底是在继续寻找“更会管理右尾的方法”，
还是应该先怀疑“可管理的基础暴露”本身不存在？
```

我倾向于第二种。

因为 EP4 后半段已经显示：

```text
exit / stop / sizing 能改变路径形状；
union portfolio 能改变持仓组织方式；
cash allocator 能改变暴露比例；

但如果底层 exposure unit 本身没有正期望，
这些模块只是把亏损重新分布。
```

所以 EP5 讨论的第一层不是“如何设计新策略”，而是：

```text
我们是否还相信存在一个基础 exposure unit？
如果相信，它和 EP4 的 exposure unit 到底哪里不同？
如果不相信，EP5 就不应该继续沿着 stock-level long-only episode 方向走。
```

这是一道方向问题，不是字段问题。

需要讨论清楚的不是：

```text
阈值设多少？
样本门槛多少？
用哪个 output artifact？
```

而是：

```text
EP5 凭什么不是 EP4 的另一次参数搜索？
它新增的经济假设是什么？
它要证明的是个股选择、风险规避、相对价值，还是市场状态配置？
它是否还需要 big-winner 这个目标？
```

### 6.1 PIT Universe / Validation Beta Regime 的背景问题

EP4 还有一个必须带进 EP5 的背景：PIT universe 和时间切分本身暴露出明显的 market-regime concentration。

EP4 R05b 的 split 是：

```text
train:      2017-07-04 ~ 2021-12-31
validation: 2022-01-01 ~ 2023-12-31
robustness: 2024-01-01 ~ 2025-12-31
```

validation 这段不是一个中性环境。它包含很强的 long-only beta pressure / market rebound / 风格切换压力。在 R05b 中，full-exposure primary baseline 的 validation return 为 -22.81%，risk-on full-exposure validation 也为 -7.91%（数字源自 `ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/reports/r05b_sleeve_allocator_exposure_composition_final_report.md`，并在 `ep4/FINAL_REPORT.md` 的 R05b 小节汇总）。这说明很多 long-only exposure 在这个 validation 结果集上都会很差。

这个背景不能被忽略，但也不能被用来放宽 validation。

错误处理方式是：

```text
validation 年份太差，所以 validation failure 可以忽略。
```

正确处理方式是把结果拆成两层：

```text
1. absolute local tradability
   在真实 long-only、成本后、next-open 条件下是否能赚钱？

2. relative / residual edge
   相对同日同宇宙、同市值 / 行业 / 流动性、
   同 market-state 的 comparator，
   是否仍有可重复的超额或更干净的分布？
```

如果一个 exposure 在 bad beta validation period 里绝对收益为负，但明显跑赢 matched comparator，它既不是 pass，也不是普通 fail。更准确的解释是：

```text
relative edge exists,
absolute long-only deployability blocked by regime / beta pressure.
```

这类结果会把讨论导向两个不同问题：

```text
1. 它可能只适合作为 relative / hedged framing；
2. 它可能需要 market-regime exposure control，
   但不能靠 allocator 去救一个负期望底池。
```

因此 EP5 不能只问：

```text
validation net 是否为正？
```

还要问：

```text
这个结果到底来自 stock-level edge、
market beta、
regime pressure，
还是 PIT universe / split concentration？
```

这不会降低 validation-first 的纪律。它只是避免把一个高度集中的 beta regime 误读成“所有 stock-level edge 都不存在”，也避免把 bad validation year 当成忽略失败的借口。

---

## 7. 候选 EP5 方向

以下方向只是讨论入口，不是候选 requirement。它们的作用是帮助判断“问题是否真的换了”。

这四个方向不是同一类东西，也不是简单四选一：

```text
short-horizon exposure timing 是 horizon / objective 的改变；
hedged / relative framing 是 payoff definition 的改变；
low-overlap sparse event family 是 event source 的改变；
loss-avoidance / regime allocation 是 risk-state problem 的改变。
```

其中 7.1 和 7.3 天然可以组合，例如短周期相对收益；7.2 可以作为 7.1 或 7.3 的事件来源；7.4 更像另一个问题层级，不应该在底层 exposure unit 还没说清楚时被当成保护壳直接套上去。

### 7.1 Short-Horizon Exposure Timing

问题：

```text
能否放弃 H120 / +50 big-winner 目标，
只寻找 H5/H10/H20 的可执行短周期 exposure unit？
```

更准确地说，7.1 不是要从零证明：

```text
短周期 momentum / continuation alpha 是否存在？
```

这个方向本身已经有很强的外部先验。大量 momentum、breakout、continuation、短周期 reversal / continuation 研究都说明：短周期可交易暴露不是一个荒谬假设。

EP5 真正需要讨论和验证的是本地化问题：

```text
在我们的 A-share universe、
当前数据口径、
next executable price、
交易成本、
停牌 / 涨跌停约束、
event collapse、
库存压力和集中度约束下，
一个具体 short-horizon exposure unit 是否仍然可交易？

如果绝对收益被 validation beta regime 压住，
它是否仍然有相对同日同宇宙 / 同行业 / 同流动性 comparator 的 residual edge？
```

所以 7.1 更像：

```text
local feasibility + regime/beta decomposition / implementation audit
```

而不是：

```text
large-scale alpha discovery / pool search
```

动机：

```text
EP2 曾证明短周期 exposure timing 比 long-horizon winner holding 更可行。
EP4 失败主要集中在把右尾持有和长期 winner capture 做成体系。
```

风险：

```text
如果 turnover / cost / execution friction 吃掉收益，
短周期方向会快速失败。
```

这里的关键讨论点是：我们是否愿意放弃 big-winner 叙事，把目标降维成更小、更可验证的 exposure timing？如果不愿意，短周期方向就不是 EP5 的主线。

但也要警惕另一个相反风险：不能因为短周期有强先验，就把 7.1 写成大规模 grid / pool search。

7.1 的第一步应该是低自由度 feasibility probe，而不是：

```text
RPS threshold grid
volume threshold grid
holding-day grid
stop-loss grid
industry / regime bucket grid
entry family combination search
```

更合理的讨论顺序是：

```text
Phase A: local feasibility probe
  少数机制清楚、事前冻结的 canonical exposure unit；
  固定 H5/H10/H20 replay；
  重点看成本、turnover、collapse、median、p10、loss rate、concentration；
  同时拆分 absolute return、relative return、year / regime / beta-state 表现。

Phase B: controlled discovery / search
  只有 Phase A 出现清晰正向结构后，
  才讨论是否值得做 train-only、低自由度、强约束的 search。
```

如果 Phase A 的固定 exposure units 结果为负，不能推出：

```text
short-horizon alpha 不存在。
```

只能推出：

```text
在当前少数可信 canonical unit 下，
本地 short-horizon feasibility 没有获得初步支持；
不能直接升级到大规模 grid / pool search。
```

如果 Phase A 出现：

```text
absolute negative,
relative positive
```

也不能简单丢弃。它说明可能存在 stock-level / residual edge，但 long-only deployability 被 validation beta regime 阻断。这个结果应进入 hedged / relative framing 或 regime exposure-control 讨论，而不是直接被当作 production pass。

更清晰的四类解释是：

这张表是方向讨论框架，不是 pass / fail 判定表；具体 matched comparator 定义、relative edge 显著性门槛、regime decomposition 口径，应留到 requirement 阶段冻结。

| absolute | relative / residual | 解释 |
|:--|:--|:--|
| positive | positive | 最强，说明 short-horizon unit 自身可能可交易。 |
| negative | positive | 有 alpha 线索，但 long-only beta / regime pressure 阻断。 |
| positive | weak / negative | 可能只是 market beta，不应当成 stock-selection edge。 |
| negative | negative | 当前 canonical unit 没有继续价值。 |

还需要明确它和 EP2 的边界。短周期方向不能简单变成：

```text
EP2 v2
```

如果 EP5 走短周期，它更像是用 EP4 学到的纪律重做 exposure timing 问题：

```text
不默认复活 EP2 的 launch / confirm-add 结构；
不再把短周期成功外推成长周期 winner holding；
先讨论新的 exposure unit、成本、collapse、库存压力和验证口径；
把 right-tail management 降级为后续问题，而不是主目标。
```

这里的边界还要更清楚：

```text
H120 / +50 big winner 可以作为 diagnostic readout；
但不能反过来定义 H5/H10/H20 entry 是否成功。

如果 short-horizon exposure unit 不成立，
big-winner diagnostic 不允许救回该方向。
```

### 7.2 Low-Overlap Sparse Event Family

问题：

```text
是否存在与 EP4 RPS / volume_money / fresh family 低重叠的稀疏事件，
其 action-time return distribution 天然更干净？
```

动机：

```text
R05 Preflight 中 base_breakout_vcp 虽然样本不足，
但比状态型 low-vol / low-beta 信号更像稀疏事件。
```

风险：

```text
不能通过放宽阈值强行堆样本；
否则会从 sparse event 退化成状态型噪声暴露。
```

这里的关键讨论点是：我们是否真的能提出一个低重叠的新事件来源，而不是把 EP4 里的 RPS / volume_money / fresh family 换个名字继续切。

### 7.3 Hedged / Relative Framing

问题：

```text
如果 long-only inventory pressure 是主要失败源，
market-neutral / industry-neutral / relative-value framing 是否能保留个股选择信息？
```

动机：

```text
R05b 表明 cash allocator 不能拯救负期望 long-only pool。
如果仍怀疑信号含有相对信息，就应该用 hedge / relative comparator 重新定义 payoff。
```

风险：

```text
对冲腿会引入新的成本、容量、融券/做空可行性和 beta-estimation 问题。
不能假设 hedge 免费。
```

这里的关键讨论点是：如果 long-only 是主要失败源，我们是否应该承认 EP5 不再是“抓个股右尾”，而是转向相对收益或残差收益问题。

### 7.4 Loss-Avoidance / Regime Allocation

问题：

```text
是否存在一个独立于 EP4 candidate pool 的 regime / risk-state loss-avoidance edge？
```

动机：

```text
EP4 的 allocator 失败，是因为它试图拯救一个 validation 为负的 primary pool。
如果 EP5 做 regime allocation，应该先把它定义为独立问题，
而不是 EP4 pool 的补丁。
```

风险：

```text
regime classifier 极易 validation-mining。
至少要讨论如何避免 state 过多、事后调参、以及用 outcome 反向定义 state。
```

这里的关键讨论点是：regime allocation 是否是独立研究问题，还是只是想给 EP4 的亏损池再加一个保护壳。如果是后者，就不值得继续。

### 7.5 方向推荐与排序（讨论性，不是冻结）

把 7.1–7.4 放到同一组尺子下比较，用来支撑下一轮方向讨论，而不是直接选定 requirement。

用四把尺子衡量：

```text
1. 离 EP4 失败模式的距离
   （改的是 horizon / objective / payoff / event source 中的哪几个，
    EP4 的负结果还能不能直接覆盖它）
2. 可证伪速度
   （在多短的时间内能拿到一个可信的 local feasibility 信号）
3. 研究成本
   （数据、执行假设、基础设施需要新建多少；
    同时要区分工程成本和概念边界成本）
4. Beta / regime 解释力
   （结果是 stock-level edge、market beta、regime pressure，
    还是 PIT universe / split concentration 的产物）
```

粗略排序：

| 方向 | 离 EP4 距离 | 可证伪速度 | 研究成本 | 综合判断 |
|:--|:--|:--|:--|:--|
| 7.1 short-horizon | 远（horizon + objective 都换） | 快（local feasibility readout 快，不是 search 快） | 工程低 / 概念边界中（数据和框架已有，但必须防止滑成 grid search） | 推荐为主线 |
| 7.2 sparse event | 中（仍是 entry-signal 范式） | 中（受样本稀缺限制） | 中 | 作为 7.1 的事件来源备选，不独立成主线 |
| 7.3 hedged | 远（payoff 重定义） | 慢（融券 / 容量 / beta 估计要先打基础） | 高（执行 + 数据基础设施需新建） | 暂不启动，先做 feasibility 才有意义 |
| 7.4 regime | 中（最容易退化成 EP4 allocator 续集） | 慢（state 数少 → 统计功效低） | 中 | 暂不启动，应放到主线有正期望底池之后 |

我的方向推荐：

```text
主线推荐：7.1 Short-Horizon Exposure Timing，
         但它是 local feasibility + regime/beta decomposition，
         不是 large-scale pool search，也不是 EP2 v2。
事件来源备选：7.2 Low-Overlap Sparse Event Family，
         作为 7.1 内部的 event source 候选之一。
暂不启动：7.3 Hedged / Relative Framing
        （A 股做空可行性是硬约束，没有 feasibility audit 之前任何
         market-neutral 回测都和“假设 cash allocator 免费”同构）。
暂不启动：7.4 Loss-Avoidance / Regime Allocation
        （样本天然稀少 + validation-mining 风险最高，
         若要做也应在主线已有正期望底池之后作为 overlay，
         而不是 primary）。
```

7.3 的“暂不启动”是默认状态，不是永久排除。如果 7.1 的 Phase A 实际落在：

```text
absolute negative,
relative positive
```

并且 relative / residual edge 在多个 matched comparator 上稳健，那么 7.3 的 feasibility audit 才应被激活。这里的 feasibility audit 指的是先检查融券标的、券源、对冲成本、容量、beta 估计和执行可得性，而不是直接启动 market-neutral 策略回测。在此之前，7.3 仍保持暂不启动。

之所以倾向 7.1，不是因为它最容易成功，而是因为它**最干脆地放弃了 big-winner 作为 entry objective**。其他三个方向都还隐性保留“找大收益”的目标：

```text
7.3 找的是相对意义上的大收益；
7.4 找的是规避大亏损反过来留下的大收益；
7.2 找的是稀缺意义上的大收益。
```

只有 7.1 主动接受目标降维 —— 把研究对象从“能不能抓 big winner”改成“能不能稳定捕捉小段 exposure”。这正是 §6 / §9 想要的方向位移。

但这不等于删除 big winner 研究。更准确的 working structure 是：

```text
Primary:
  short-horizon positive exposure unit
  = H5/H10/H20 是否能独立形成可执行正期望。

Secondary:
  big-winner / right-tail holding-extension diagnostic
  = 只在 primary exposure unit 成立以后，
    研究哪些 post-entry state 支持延长 holding。
```

也就是说，big winner 从：

```text
entry label
pool-selection objective
pass/fail rescue
```

降级为：

```text
post-entry state diagnostic
holding-extension readout
right-tail optionality audit
```

如果走 7.1，讨论阶段就该约好以下避坑点，否则它很容易退化成 EP2 复活：

```text
1. 不预设 launch / confirm-add 这类多段结构，
   先从最简单的 single-entry / single-exit unit 开始。
2. 不把 H5/H10 的可行性当成 H120 winner 的早期信号；
   短周期成立就是短周期成立，不外推。
3. H120 / +50 可以保留为 diagnostic readout，
   但不能参与 short-horizon exposure 的成功定义。
4. 不做大规模 grid / pool search；
   第一阶段只做少数 canonical unit 的 local feasibility probe。
5. 固定参数结果为负，不等于证明 short-horizon alpha 不存在；
   只说明当前 canonical unit 没有给出足够继续搜索的初步证据。
6. 若要从 feasibility probe 进入 search，
   需要新的经济假设，而不是直接扩大阈值和组合空间。
7. turnover / cost / collapse / 库存压力 必须在 preflight 阶段就上桌，
   不能放到后期再补 —— EP2 当年就是因此被吃掉的。
8. validation 不能只看 absolute net；
   必须同时输出 yearly / regime / beta-state decomposition。
9. 口径沿用 EP4 的纪律：
   matched comparator、median、p10、loss rate、concentration、
   robustness read-only，不退回 EP2 当时较宽松的口径。
```

如果对这套排序有分歧，分歧点更可能是以下两个，而不是"要不要做 7.1"：

```text
A. 是否承认放弃 big-winner 中心是 EP5 的前提？
   （如果不承认，7.1 就不是主线，讨论应回到 §9 的根问题。）
B. 7.3 的暂不启动是否合理？
   （如果有人愿意先承担一个独立的“A 股做空 / 融券可行性”研究，
    7.3 可以并入 EP5；否则它本质上是另一个项目。）
```

这一节是方向推荐，不是 requirement，也不构成对 7.3 / 7.4 的永久否决 —— 它们随时可以在主线有阶段性结论之后被重新启动。

---

## 8. 伪新方向陷阱

§5 已经从正面说了什么算实质改变。这里从反面列一些看起来像新方向、但其实仍是 EP4 包装的陷阱。

这些不是 implementation gate，而是讨论时要主动拆穿的命名漂移：

```text
1. 把 RPS bucket 改叫 momentum regime，但 entry / payoff 仍然相同。
2. 把 volume_money pool 改叫 liquidity / participation state，但仍然是 R04d relative improvement。
3. 把 fresh-count / stage-role 改叫 lifecycle state，但还是从 fresh day 重新买入。
4. 把 R04e weak-pool union 改叫 diversified sleeve，却没有解释伪分散和 active inventory。
5. 把 cash allocator 改叫 regime allocation，但底层 full-exposure pool 仍为负。
6. 把 sparse event 阈值放宽到样本够多，结果重新变成 EP4 的状态型暴露。
7. 把 short-horizon 写成 EP2 v2，而没有说明新经济假设和 EP2 边界。
8. 提到 hedged / relative framing，但实际评估仍按 long-only absolute return。
```

如果一个方向无法回答“为什么它不是 EP4 overfit loop”，就不值得进入下一步。

---

## 9. 当前建议

当前最合理的下一步不是立刻写 implementation-level requirement，而是先把 EP5 的问题边界讨论清楚。

我现在的 working hypothesis 是：

```text
EP5 不应默认延续 big-winner episode management。

Primary objective:
  short-horizon positive exposure unit.

Secondary diagnostic:
  big-winner / right-tail holding extension,
  only after the short-horizon unit itself is viable.
```

之所以这样分层，不是因为 right-tail 不存在，而是因为 EP4 已经把：

```text
right-tail 存在
  -> right-tail 可经营
```

这一步走完了。再做一遍 right-tail management，需要先解释新增的经济假设是什么；而短周期、hedged / relative、loss-avoidance / regime、low-overlap sparse event 这些方向，至少都在改变经济假设本身。

所以 §9 的答案不是简单的“继续”或“不继续”，而是：

```text
不继续把 big winner 作为中心目标；
保留 big winner 作为后期持仓诊断。
```

这个边界对应两层问题：

```text
Layer 1:
  H5/H10/H20 exposure unit 是否独立成立？

Layer 2:
  如果 Layer 1 成立，
  是否存在 post-entry state 支持延长 holding、
  保留一部分 right-tail optionality？
```

在这个判断之上，方向选择本身交给 §7.5：当前推荐主线是 7.1 short-horizon exposure timing，7.2 作为事件来源备选，7.3 / 7.4 暂不启动。§9 只负责把 EP5 的中心目标和 big-winner diagnostic 的保留边界钉住。

这不是最终结论，但这是现在最值得讨论的方向分歧。如果这个 working hypothesis 被接受，下一步才进入 §10 所说的 R01 / E01 分轨推进。

---

## 10. 推进方式：Requirement 与 Engineering 分轨

§9 把方向钉住后，下一步不是直接写"EP5 策略系统"或"大规模 alpha search 框架"。EP5 当前最大的风险不是工程复杂，而是 7.1 容易在落地时悄悄滑成"换个 horizon 的 alpha pool search"。

为了让方向纪律和工程纪律互相约束，建议把推进切成两条**分轨但有先后依赖**的轨：

```text
Requirement 轨：先回答“这个方向是否值得继续”。
Engineering 轨：在 requirement 边界冻结后，搭一个可复用、可审计的 short-horizon 测量装置。
```

两轨的分工：

```text
Requirement 防止方向漂移；
Engineering 防止实验不可复现。
```

任何一轨单独跑都会出问题：

```text
只有 requirement：结论不可复现，下一轮重做时又会重新争论口径。
只有 engineering：很容易把 harness 升级成 alpha search system，
                 偷偷把 7.1 滑成 EP4 evidence-family pool 的横向克隆。
```

### 10.1 Requirement 轨：第一份 requirement

建议第一份 requirement 只做一件事：

```text
EP5 R01: short-horizon local feasibility probe.
```

它应负责冻结以下边界（具体口径留给 requirement 文档本身展开，这里只圈范围）：

| 部分 | requirement 负责 |
|:--|:--|
| 核心问题 | 是否存在可交易的 H5/H10/H20 short-horizon exposure unit |
| 非目标 | 不证明 short-horizon alpha 是否普遍存在；不做大规模 grid search；不做 pool search |
| exposure unit | 少数几个 canonical units，参数低自由度，事前冻结 |
| 成本 / 执行 | D signal -> D+1 open / close 类口径必须固定，停牌 / 涨跌停约束写清 |
| validation 拆分 | 必须同时输出 absolute return、relative / residual edge、year / regime / beta-state |
| comparator | same-day universe / industry / liquidity / benchmark 等 matched comparator |
| big winner | 只作为 read-only / optional 的 post-entry holding diagnostic，不参与 pass / fail，也不在 R01 里做 holding-tuning |
| 输出判断 | 沿用 §7.1 的四象限：absolute positive + relative positive / absolute negative + relative positive / absolute positive + relative weak-or-negative / absolute negative + relative negative |

R01 **不应规定代码结构**。它的产出是边界 + 判断口径，不是接口；canonical exposure units 也应由 R01 事前冻结，不能留给 E01 在工程实现时自由选择。

### 10.2 Engineering 轨：第一份 engineering plan

Engineering 不要写成策略优化系统。建议第一份只做：

```text
EP5 E01: short-horizon exposure audit harness.
```

它负责的范围：

| 部分 | engineering 负责 |
|:--|:--|
| runner | 一个 config-driven runner，可复现 R01 |
| data panel | 复用已有 Qlib / PIT universe / price / industry / liquidity 数据 |
| exposure replay | 支持固定 horizon：H5/H10/H20 |
| cost model | 统一扣成本、换手、持仓天数、执行价 |
| decomposition | 自动输出 train / validation / robustness、year、regime、beta-state 分解 |
| comparator | 自动生成 matched comparator / relative return |
| report artifacts | CSV + markdown summary + manifest |
| scope ownership | 只实现 R01 冻结的 canonical exposure units，不负责选择、扩展或搜索 exposure units |
| guardrail | 明确禁止 Phase A 变成 grid search（例如限制 config 中 exposure unit 组合数量，并禁止通过 config schema 暗含大搜索空间） |

Engineering **可以为 Phase B 留接口**，但第一版不实现 search scheduler，也不接入 hedged infra。E01 的职责是让 R01 可复现，不是替 R01 发现新的 exposure unit。

### 10.3 推进顺序

```text
1. 先写 requirement_01_short_horizon_local_feasibility_probe_v1.md
   把 R01 的问题边界钉死，
   尤其是“不做 search”和“validation beta regime 如何解释”这两条。

2. 再写 engineering_plan_01_short_horizon_audit_harness.md
   只定义 runner / 输入 / 输出 / 目录 / artifact schema，
   不讨论经济结论。

3. 实现 R01 所需的最小 harness
   不做泛化优化，不接 hedged 基础设施，不实现 Phase B。

4. 跑 R01。根据结果决定下一条 requirement：

   - absolute positive and relative positive
       -> 进入 controlled discovery / holding tuning（仍是 7.1 内部）；
   - absolute positive but relative weak / negative
       -> 先做 market beta / regime attribution，
          不直接当作 stock-selection edge 通过；
   - absolute negative but relative positive
       -> 触发 7.3 feasibility audit（见 §7.5 激活条件）；
   - absolute negative and relative negative
       -> 7.1 暂停，回到 7.2 或重新定义事件来源。
```

这一节是推进方式建议，不是 requirement 本身，也不锁定 engineering 目录结构。具体文档命名 / 路径 / artifact schema 由 R01 和 E01 各自落地时决定。要点只有一个：

```text
R01 requirement 必须比 E01 engineering 更早出现，
否则 harness 会先把方向偷偷定下来。
```
