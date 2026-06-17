# 11 系列讨论：K3 是诊断窗口，不是策略

> 本文档记录 11A2 与 11C 之后的讨论结论。它不是新的 requirement，也不改变已运行的 11A2/11B/11C 口径；它用于明确下一步为什么不应继续直接调 K3 policy。更精细的 winner / failure early-path 统计与实验是否值得做、以何种方法做，本文档**不预设**，留待单独开一章去 scope（见 §4）。

---

## 0. TL;DR

11A2 已经证明：在 `risk_on ∩ strict PIT-valid` 的 4,665 条 evaluated rows 内，winner 与 failure proxy 的 post-t0 path divergence 可以在 K3 附近出现。

11C 进一步证明：把这个 K3 信号直接压成一个粗糙的 two-stage hard rule 后，虽然能降低 failure exposure，但还不能形成可支持的 after-cost / capacity-constrained policy。

因此当前缺口不是“要不要 K3”，而是：

```text
winner 形态与 failure 形态尚未建模；
最佳分离点不一定是单一 K；
不同 failure 子类 / winner 子类可能对应不同 observed-state decision time。
```

AFML 的处理方式是把问题从“找一个 K 点做规则”重新理解为 `event -> early-path observed state -> meta-label probability -> bet sizing / wait / reject / upgrade` 的 meta-labeling 问题。但**本文档只把它作为理解框架，不预设下一步就去做更精细的 morphology 建模**：那部分更精细的统计与实验，连同它的方法形式，值得单独开一章独立 scope，且开章前要先验证「多 K 是否真有超过 11A2 单 K 的额外可分自由度」（见 §4）。

---

## 1. 11A2 到 11C 暴露出的真实缺口

### 1.1 11A2 给出的正证据

11A2 的核心结论不是“K3 可以直接交易”，而是“在严格 PIT 分母内，某些 failure proxy 与 winner 的早期路径确实开始分岔”：

| contrast | full-cohort confirmed onset | return channel | structure channel | 解释 |
|---|---:|---:|---:|---|
| C1 winner vs big failure proxy | K3 | K1 | K3 | 主结论，双通道成立 |
| C2 winner vs false repair only | K3 | K3 | K3 | false-repair 子类同样 K3 可分 |
| C3 winner vs fast fail | K5 | K3 | K5 | fast-fail 结构通道更晚 |
| C4 winner vs neutral | none | none | K10 | 不构成稳定双通道确认 |
| C5 winner vs all nonwinner | none | K10 | none | all-nonwinner 聚合会冲掉结构信号 |

这说明两个事实：

1. `all nonwinner` 不是一个可建模的同质负类。
2. 分离点不是全局唯一值；failure proxy 内部至少有 K3 与 K5 两种时间结构。

11A2 还给出一个重要保护边界：fast-fail barrier touch 只能做 label-overlap audit，不能成为 primary policy feature。K5 时 fast-fail touch overlap 已经明显上升，K10 与 fast-fail label 完全重合，因此越晚使用 fast-fail touch 越容易变成 label tautology。

### 1.2 11C 给出的负证据

11C 把 K3 observed state 放进可执行 replay 后，selected diagnostic candidate 是：

```text
B2_wait_confirm_K3__S1_reclaim_damage__target_1.00

S1_reclaim_damage:
  ep_close_vs_t0_close_at_3 >= 0
  AND ep_breach_t0_low_through_3_flag == false
  AND entry_t0p4_executable_flag == true
```

在 base cost、primary capacity=50、Lane A ∪ Lane B composite 口径下：

| metric | B0 baseline | B2 K3 wait-confirm | readout |
|---|---:|---:|---:|
| entry_filled_n | 971 | 740 | fewer entries |
| net EV / exposure-day | -0.000678 | -0.000554 | +0.000124 lift, but still negative |
| winner capture | 0.2390 | 0.1951 | captured winner loss |
| big_failure_proxy entry rate | 0.0764 | 0.0433 | failure exposure lower |
| false_repair entry rate | 0.0797 | 0.0454 | failure exposure lower |
| turnover | 38.2504 | 29.2556 | lower turnover |
| cash drag | 0.5415 | 0.6663 | higher cash drag |

核心读数是：

```text
K3 wait-confirm 能减少坏样本进入，
但同时牺牲 winner capture；
净 EV/day 只小幅改善且仍为负；
train split、top-k sensitivity、11B upstream ceiling 都不支持 policy positive。
```

B3 trial-entry 也没有解决问题。10% / 25% trial 会提高 winner capture，但更大幅度提高 big_failure / false_repair exposure，变成“买回 winner 的同时买回大量 failure”。这说明单纯 staged sizing 不是答案；必须先知道哪些 trial path 是 constructive shakeout，哪些是真 failure。

Lane B delayed rescue 有研究价值，但 power 不足。它提示“被 10C 拒绝后，如果后续路径自证，可以作为新的 observed-state event”这一方向值得研究，但不能据此 override 10C。

---

## 2. AFML 会如何重写这个问题

### 2.1 这不是一个直接分类问题

AFML 不会把当前问题写成：

```text
给定 K3 state，判断 winner / failure。
```

更合理的写法是：

```text
给定 t0 candidate event 和 t0+K observed path state，
估计该事件在当前 regime / liquidity / execution constraint 下的
conditional payoff-risk distribution，
再决定 wait / no trade / trial / upgrade / exit。
```

也就是说，11C 做的是 meta-labeling policy replay，而不是新的 alpha model。

### 2.2 primary model 与 meta-model 必须分开

在 AFML 框架下：

```text
primary model:
  负责产生候选机会 / event source。
  在当前系统里近似对应 10A/10B/10C 后的 candidate universe。

meta-model:
  负责回答这个机会是否值得执行、何时执行、执行多大。
  K1/K3/K5/K10 observed path state 应进入这一层。
```

因此 K3 path state 不应该被理解成“新的买入信号”，而应被理解成对已有 candidate 的二次条件化：

```text
P(winner | event, observed_state_K, regime, execution_feasible)
P(big_failure | event, observed_state_K, regime, execution_feasible)
E[net payoff / exposure-day | same conditioning]
```

### 2.3 label 是 outcome，不是 feature

winner、fast_fail、false_repair、big_failure 都是 outcome label。它们可以定义目标、分母、分层 readout，但不能以未来路径形式泄漏进 primary feature。

允许进入 observed-state 的应是当时已经发生、可执行可观测的信息，例如：

```text
K-day return from executable anchor
K-day drawdown / path damage
K-day close position / reclaim status
K-day liquidity / volume confirmation
K-day executable status
```

不能进入 primary policy feature 的是：

```text
future MFE / MAE beyond K
winner_120 / forward_return_120d
fast-fail label-derived barrier touch
任何 label-derived future coordinate
```

这条边界比模型形式更重要。否则得到的“分离”只是把标签重新编码进特征。

### 2.4 最佳分离点不应预设为一个全局 K

11A2 已经暗示：不同负类的分离 onset 不一样。

因此下一步不应问：

```text
K3、K5、K10 哪个最好？
```

而应问：

```text
对哪一种 winner archetype，
相对于哪一种 failure archetype，
在哪一个 K，
用哪一组非泄漏 observed-state feature，
可以形成稳定且可交易的 conditional advantage？
```

可能的结果是：

| path family | 可能分离点 | policy 含义 |
|---|---:|---|
| immediate reclaim winner vs obvious damage failure | K1/K3 | 可早确认或低风险 upgrade |
| shakeout-reversal winner vs false repair | K3/K5 | 需要等路径自证，不能 t0 硬拒 |
| winner vs fast fail | K5 | 需严防 label-overlap |
| winner vs neutral chop | none / late | 不适合硬分离，可能只能做 exposure control |
| rejected then reclaim | K3/K5 | 可能是新 event，不是 10C override |

这就是“multi-K separation frontier”，不是单一阈值搜索。

### 2.5 AFML 更关心概率、下注规模和样本依赖

即使某个 state 能提高 winner rate，也不等于能交易。AFML 会继续要求：

```text
calibrated probability
payoff-risk distribution
EV / exposure-day
transaction cost
capital utilization
concurrency
sample uniqueness
instrument-block dependency
top-k sensitivity
purged / embargoed validation
```

这解释了为什么 11C 没有因为 B2 降低 failure exposure 就给 positive：它没有跨过 after-cost、winner capture、train/robustness、top-k 和 upstream prerequisite 的联合门。

---

## 3. 当前系统设计含义

### 3.1 不要继续直接调 K3 hard rule

11C 已经显示：单一 `S1_reclaim_damage` hard state 太粗。它把部分 failure 排掉，但也排掉太多 winner；trial-entry 又把 failure 暴露买回来。

继续在 11C 上微调 state threshold，容易变成 rule fishing。但「正确方向就是 morphology」也不应在这里被预设成结论。当前能确定的只有一条边界：

```text
不要继续在单一 K3 hard rule 上 fishing；
更精细的 winner / failure 早期路径统计与实验，应单独开一章去 scope，
而不是在本讨论里直接钦定方法（见 §4）。
```

### 3.2 winner 不是同质类，failure 也不是同质类

从 10C 到 11A2/11C 的链条看，最容易被误伤的 winner 往往不是“直线快速上涨型”，而是 early shakeout / reclaim / delayed realization 一类。failure 也不是同质类：fast_fail、false_repair、neutral chop 的 path dynamics 不一样。

所以后续 label / readout 至少要允许：

```text
winner_path_archetype
failure_path_archetype
neutral_or_chop_path_state
rejected_then_reclaim_state
```

这些 archetype 可以用未来 outcome 做 offline profiling，但进入 policy 的必须是 K 时点可见的 observed-state proxy 或 meta-model probability。

### 3.3 Lane B 应被看成新事件，不是 10C override

11C 的 Lane B delayed rescue readout 很重要，但它的正确解释是：

```text
10C 在 t0 仍有效；
若被拒样本在 K3/K5 后用可观测路径自证，
它可以作为新的 observed-state event 被重新评估。
```

这不是“放宽 10C”，也不是“用 K3 覆盖 10C”。它是 event time 的移动：从 t0 rejected candidate 变成 t0+K observed-state candidate。

但必须同时承认 Lane B 的**结构性约束**，否则会高估它的地位：

```text
Lane B 的样本少是市场结构性的，不是采样口径能改的：
“被 10C 在 t0 拒绝、随后路径自证”这种事件本身就稀有。
330 个 Lane B 样本 / 62 个 winner 不是“我们没扩”，而是这类机会的真实频率就这么低；
样本量不可由我们主动扩充，只能等更多年份数据自然积累。
```

因此 Lane B 的正确定位是：**低频、高赔率的 opportunistic readout-only 分支**——在 robustness 上它的 LB2 delayed rescue 确实同时降低 failure exposure、提高 winner capture 并把 EV 推正，说明“遇到了就值得吃、吃到就赚得多”。但它撑不起一条需要稳定样本流来反复验证 EV / 容量 / 稳定性的主线。正确处理是：把它作为以后的一个分支挂在系统里，待数据自然积累后再单独审视，**不进入主线、不据此 override 10C、本轮仍只 readout**。

主线必须建立在样本量足够、能反复验证的 population 上，也就是 Lane A 的全量 candidate；Lane A 的真问题不是样本不够，而是 11A2 已显示的「winner / failure 在 K3 纠缠且双通道高度共线」。

---

## 4. 下一步定位：精细化统计与实验值得单独开一章

本讨论**不预设**下一步就是「winner archetype / failure archetype morphology」实验，也不在这里冻结任何实验编号或方法形式。理由是：11C 已经证明 Lane A 上 winner / failure 在 K3 是纠缠且双通道高度共线的；在这种自由度可能本就很低的数据上，直接跳到更复杂的 morphology clustering，很容易在 train 上凑出漂亮的 archetype、却在 robustness 上塌掉（见 §5）。

因此这里只记录一个定位，而不是一个设计：

```text
更精细的 winner / failure early-path 统计与实验，
是一个独立的、需要自己单独 scope 的章节，
不应作为 11C 的延伸或本讨论的既定结论被直接写死。
```

### 4.1 在单独开章之前必须先回答的前置问题

任何后续精细化章节在投入复杂建模之前，应先用最简单的方式回答一个先决问题：

```text
多 K（K=1/3/5/10）叠加，是否真的提供了
超过 11A2 单 K 双通道（return/structure，rank corr 约 0.77）的额外可分自由度？
```

- 若答案是「没有实质增量」：说明可分信息就是那一个早期路径质量维度，更复杂的 morphology 只是把同一个共线信号换更复杂的包装，应停在 diagnostic，不开大章。
- 若答案是「有可复现的额外自由度」：才值得把它写成一个独立章节，去做 archetype / multi-K separation / meta-label probability。

### 4.2 单独开章时必须预注册的纪律（不是现在就做）

如果将来确实开这一章，它**必须**满足下列纪律，否则会比 11C 更容易 rule fishing：

- label 是 outcome 不是 feature（§2.3 边界），fast-fail touch 越晚越接近 label tautology。
- 任何 clustering / prototype 的全部自由度（簇数、距离度量、初始化、随机种子）预注册并 hash；archetype 必须在 instrument-block split 上复现才算数，只在 train 成立的不算。
- multi-K × multi-contrast × multi-feature 会放大多重比较，必须继承 11A2 的 multiple-comparison null audit 并加严。
- 概率必须 calibrated，并照常过 EV/exposure-day、transaction cost、capital utilization、concurrency、sample uniqueness、instrument-block dependency、top-k sensitivity、purged/embargoed validation 的联合门。
- 输出只能是诊断态读数（archetype 可得时点、允许的 feature family、label-overlap 风险、power、split 稳定性、top-k 状态、是否够格进入后续 policy replay），**不得**直接输出 `K state-positive => buy` 这类规则。

### 4.3 暂不纳入主线的分支

- Lane B「rejected-then-reclaim」：§3.3 已说明是市场结构性稀缺、样本不可主动扩充的低频高赔率分支，只作 opportunistic readout-only，待数据自然积累后单独审视，不进入下一章主任务。

---

## 5. 预注册失败模式

若将来开精细化章节，必须提前接受以下可能结论（现在不预设它一定会做）：

| case | 结论 | 系统含义 |
|---|---|---|
| 多 K 无增量自由度 | 叠加 K 后相对 11A2 单 K 无实质增量 | 停在 diagnostic，不开大章 |
| morphology 不稳定 | clustering / archetype 只在 train 成立 | 回到 diagnostic，不进 policy |
| 只有 fast-fail K5 可分 | 但 label-overlap 风险高 | 只允许 readout，不进 primary feature |
| winner archetype 可分但 EV 不支持 | 形态真实但不可交易 | 不进入 policy |
| 分离只来自少数 instrument | top-k dependent | 不支持上线 |
| Lane B reclaim 有信号但 power 不足 | 市场结构性稀缺、不可扩样本 | opportunistic readout-only 分支，不进主线 |
| K3 降 failure 但杀 winner | 重复 11C | 说明 hard rule 过粗 |

---

## 6. 当前工作结论

11 系列到目前为止的正确解释是：

```text
11A1 / 11B:
  先确认 archetype proxy 与 protected retention 的稳健性边界。

11A2:
  证明 post-t0 path divergence 存在，尤其 C1/C2 在 K3 开始可分。

11C:
  证明粗糙 K3 two-stage rule 还不能转化成可支持策略；
  wait-confirm 比 trial-entry 干净，但 winner capture 与 net EV 不够；
  Lane B rescue 有研究信号但样本市场结构性稀缺。

下一步:
  不应继续调单一 K3 policy；
  更精细的 winner / failure early-path 统计与实验值得单独开一章，
  但本讨论不预设其方法形式，开章前先验证多 K 是否提供额外可分自由度；
  Lane B 仅作 opportunistic readout-only 分支，不进主线。
```

一句话：

> K3 是一个有效诊断窗口，但还不是一个完整策略，也还不能断定更精细的形态建模就是答案。是否、以及如何把它建成 meta-label probability 与路径形态问题，应在单独一章里先验证多 K 增量自由度后再决定。
