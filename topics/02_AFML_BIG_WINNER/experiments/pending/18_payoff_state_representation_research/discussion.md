# EP18 讨论：18F 收口之后——头顶空间、分布迁移与入场缺失

> 本文档记录 18F（`payoff_state_oracle_gap_bridge`）运行并收口为 `18F_utility_bridge_not_supported` 之后的评审与讨论结论。它**不是新的 requirement**，也不改变已运行的 18A–18F 口径。它用于说明：18F 的负结论意味着什么，以及为什么下一步的真正 open problem 是"入场"，而不是继续精修退出。正式收口与 EP19 handoff 见 §6。

---

## 0. TL;DR

1. **18F 报告可信、收口正确**：primary robustness learned mean incremental return = `-0.010552`（为负），payoff retention、bootstrap CI、frontier 全线证据一致，`18F_utility_bridge_not_supported / next=none` 与决策优先级相符。核心洞察成立：**"可排序" ≠ "可直接作为 defend/continue 动作掩码"**。

2. **oracle 头顶空间天生薄（≈2.94%）**：不是"人人赢家所以无险可防"，而是 **payoff 右偏 + 动作集不对称（continue 上不封顶、defend 封顶在现金）+ winner-episode 事后选择抬高 continue 基线** 三者叠加。头顶空间薄 → 对"误防守正样本"零容忍。

3. **分布迁移（train 防守 30% → robustness 44%）** 主要是"用未校准 ranking score 的冻结绝对分位当阈值"造成的假象；应改成**成本锚定的经济边界**（`Ê[defend_advantage] > cost`）或**同日横截面相对排序**，二者都 PIT 合法、非 OOS 调参。但迁移里也有真实 regime 衰减，阈值技巧消不掉。

4. **根本质疑（最重要）**：整条 EP16→EP18 线是在一个 **hindsight 条件化、右偏、且抽掉了入场** 的子宇宙上做评估。程序**自己已承认"entry position 在 t0 不可知"**（Ep15 关闭了 t0 入场预测）。因此**即便 O5 可达，也不可部署**——你无法在 t0 进入"realized winner episode"这个集合。"怎么入场"在这条线里没有答案，而且是被有意识搁置的。

5. **后续方向上修一级**：不要急着做 `defend_advantage` 可分性 precheck（仍在同一条件化退出子问题里打转）。**先做前置判定**：这条持有/退出研究线在没有可部署入场模型的前提下是否还值得继续投入。要么作为 representation 上界诊断正式收口 EP18，要么把下一章 scope 到 **入场宇宙的 PIT 可交易性 preflight**。

---

## 1. 18F 结论回顾与可信度核对

18F 上游 18C refresh 已通过（rank_ic 0.1253、monotonicity 0.7333、bootstrap ci_low 0.08822），43 个输入 artifact 可读、join 一对一、O5 identity replay 通过。真正的阻塞点是 ranking score 没有转成正的 action-value utility。

primary operating point `defend_bottom30_continue_rest` 在 robustness labelable_full 上：

| 指标 | 值 |
|---|---:|
| learned mean incremental return | `-0.010552` |
| O5 perfect utility oracle | `0.029467` |
| O2 drawdown oracle | `0.018511` |
| O5 approximation ratio | `-0.358080`（方向为负） |
| top30 payoff retention | `0.6256`（< 0.70 门槛） |
| top20 payoff retention | `0.6365`（< 0.80 门槛） |
| cluster bootstrap 95% CI | `[-0.014387, -0.007484]`（全负） |
| positive sacrifice / avoidance | `1.5688` |

失败机制（six-cell 分解，收支闭合）：被防守的 519 个 positive 行（占 20.79%）贡献 `-0.025077` 拖累；被防守的 negative（298 行）+`0.010495`、neutral +`0.004031`，合计不足以覆盖。**负样本规避 + neutral 收益 < positive 机会成本**。整条 robustness frontier（bottom10→bottom50、top30→top10）**无一为正** → 不是 cutoff 选点问题。

结论：`18F_utility_bridge_not_supported`，`next_allowed_requirement = none`，全部 policy/backtest/deployment 授权为 false。报告纪律正确，明确"下一步不应是调参找一个能过关的 threshold"。

---

## 2. 为什么 oracle 头顶空间薄（对"是不是天生赢家"的回答）

分布事实（`target_distribution_readout.csv`）：

| split | 全体 mean | 全体 median | state_0(≈66–70%) mean |
|---|---:|---:|---:|
| train | +2.04% | +0.41% | **−4.55%** |
| robustness | +3.49% | +1.51% | **−3.86%** |
| validation | +2.63% | +0.45% | **−5.27%** |

- **不是"每行都是赢家"**：占 66–70% 的 state_0（below-top30）前向 h20 平均是亏的；均值为正靠右尾（top10 均值 +31%，最大 +223%）撑起——高度右偏。
- **压小头顶空间的是动作不对称**：O5 = `max(0, defend_advantage)`，只有 defend（去现金=0）打赢 continue 时才计入。右偏宇宙里 blind-continue 已吃掉右尾，defend 天花板是现金、只能规避左尾（小的那一侧）。O5=2.94% 就是这块避损空间。
- **winner-episode 事后选择进一步抬高 continue 基线**：只看"最终成为 winner"的标的，其前向无条件收益被系统性抬高（+2~3.5%），直接放大 blind-continue、压薄 O5 defend 增量——这一层就是"反向挑赢家"效应，成立。

一句话：**payoff 右偏 + 动作封顶 + winner 选择**，使 defend-only oracle 结构头顶空间天生就薄。这也解释 18F 为何脆：总空间 2.94%，误吃一点右尾正样本（519 行 = 2.51% 机会成本）就把 utility 打成负。

---

## 3. 分布迁移问题与解法

现象：train 冻结 q30 score 阈值搬到 robustness，因 score 分布左移吃到 44%。阈值本身无经济含义，不可迁移。

解法按优先级：

1. **成本锚定的经济边界（首选）**：先把模型校准到 `Ê[defend_advantage]`（或 `P(defend_advantage>0)`），"当且仅当 `Ê[defend_advantage] > 成本(≈50bps)` 才防守"。阈值有稳定经济含义、跨 regime 可迁移、非 OOS 调参。这也指向真正该建模的目标是 `defend_advantage` 而非 payoff 幅度。
2. **同日横截面相对排序**：用当日同截面的 score 排 bottom-X%，PIT 合法，对 level 漂移免疫。
3. **横截面特征标准化**：缓解但治不了根（迁移可能来自 regime/label）。

诚实警告：迁移里有一部分是**真实 regime 差异 / alpha 衰减**，任何阈值技巧都消不掉。正确诊断顺序：先确认 `defend_advantage` 的 OOS 可分性是否存活；存活再用成本锚定边界解决动作规则不可迁移；不存活则是 representation 在 OOS 失效，停在 diagnostic。

---

## 4. 根本质疑：hindsight 条件化 + 入场缺失（最关键）

程序自己的原文（16A / research_plan）：

- *"entry position 在 t0 不可知，因此 't0 给整段路径贴形态标签' 是错误的提法"*；
- *"winner 形态不是固有离散类别，而是 'entry position within realized episode' 的连续函数"*；
- 序贯范式定义：*"t0 不预测终局形态，只在**持有过程中**一段一段地判断'下一小段是否值得继续参与'"*；
- Episode 15 已**关闭 t0 入场预测**（离散形态 taxonomy、t0-predictable 形态均被否定）。

由此：

1. **评估宇宙 = realized winner episode 段内采样**，成员资格带 hindsight。右偏（§2）正是它的产物。
2. **defend/continue 本质是"已持有下的 exit/holding 决策"，预设你已在仓位里**。O5/O4/18F 全部是"假设已在赢家里，退出技巧上限还有多少"。
3. **程序自己承认 t0 入场不可预测** → "怎么入场"在这条线里没有答案，而且是被有意识放弃的。

**"oracle 可实现 ⇒ 可部署"不成立**，两层封锁：

- **封锁 A（入场）**：要进入评估集，必须在 t0 就知道"这只票正处在将成为 winner 的 episode 里"——正是 Ep15 判定不可预测者。没有入场模型就进不了这个宇宙。
- **封锁 B（条件偏移）**：换一个能实盘触发的宽入场规则，真实宇宙会混入大量非赢家（真实左尾），退出技巧价值必须在那个入场条件化宇宙上重测，届时 payoff 几何、O5 头顶空间全变。当前 2.94% 是**双重条件化子问题的上界**，不是可部署期望。

一句话：**当前这条线量的是"给定你已经神奇地在赢家里，退出技巧的天花板"，而'神奇地在赢家里'恰是它承认解不了的部分。**

三者收敛：Q1 右偏、Q2 迁移、本节入场缺失，都源于"在一个 hindsight 条件化、抽掉入场的子宇宙上做评估"。

---



---

## 5. 后续方向判定

18F 已证明 **18C payoff ranking score + 当前 train-frozen threshold action mapping** 转不成正的 exit/defend utility；§4 进一步说明**没有入场就没有部署路径**。因此后续方向应**上修一级**，先回答一个前置判定：

> 这条 winner-episode 持有/退出研究线，在**没有可部署入场模型**的前提下，是否还值得继续投入？

- **若"作为 representation 上界诊断，够了"** → 正式收口 EP18，归档为有界结论：payoff-state 在 realized-winner 段内有 ranking representation 价值（18C），但（a）当前 ranking-to-threshold action bridge 转不成 exit utility（18F），（b）无入场故无部署路径。回到 topic-level 方向。
- **若"要奔部署"** → 下一个 requirement 不应是继续精修退出，而应是 **入场宇宙的 PIT 可交易性 preflight**：能否在 t0 用纯 PIT 信息构造一个高触发、无 hindsight 的候选入场集；并在该**入场条件化宇宙**上（含真实输家、含成本）重测 O5 头顶空间与 defend/continue 价值。注意 Ep15 已警告 t0 入场预测很难，这是高风险新研究，不是 18 系列的续集。

**不建议**：在未回答入场之前，直接跳到 `defend_advantage` 损失函数重设或新一轮退出精修——那仍在同一个 hindsight 条件化子问题里打转。`defend_advantage` 可分性 precheck 若要做，也应**内建成本锚定的 sign 边界（阈值=0/cost）**，绕开分位迁移，并明确它只是退出子问题的诊断、不解决入场。

---

## 6. EP18 收口与 EP19 handoff

EP18 正式收口为：

```text
closure_state = EP18_closed_representation_only_no_policy_path
closing_phase = 18F_payoff_state_oracle_gap_bridge
closing_decision_state = 18F_utility_bridge_not_supported
next_requirement_within_ep18 = none
policy_backtest_deployment_authorized = false
```

这是一份 topic-level research closure note，不是 18F pipeline 自动授权的下一需求。18F 决策产物本身仍保持 `next_allowed_requirement = none`；EP19 是人工研究重启，用来换研究对象，而不是沿 18F pipeline 往下走。

收口含义：

1. EP18 保留一个正结论：refreshed 18C 证明 payoff-state score 在 realized-winner 条件化宇宙里有 ranking representation value。
2. EP18 的负结论同样成立：当前 payoff ranking score 不能直接桥接为 defend/continue action-value utility。
3. EP18 不再继续写 18G/18H 来调 threshold、换 cutoff 或精修 exit。
4. 如果继续推进 Big Winner 主线，应新开 EP19，研究对象从 realized-winner 内部退出问题切换到无 hindsight 的 PIT 入场宇宙。

EP19 handoff：

```text
new_episode_id = 19_entry_universe_pit_tradability_preflight
research_plan = topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/research_plan.md
first_expected_requirement = requirement_19a_entry_universe_pit_lineage_and_tradability_preflight.md
primary_question = can a deployable PIT entry universe be constructed before any winner-episode conditioning?
```
