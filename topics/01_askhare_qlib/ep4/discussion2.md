# EP4 Discussion 2: 多 Probe 点、30 日建仓与风险预算分配

> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 P1 validation。
>
> 背景：基于 `discussion.md` 的状态机思路，以及 R01 V3 post30 profile seed 的结果。V3 说明：某些结构作为 `profile / probe point` 很有价值，但不能直接当作完整 entry trigger。这里讨论的是：如果未来能找到若干个 probe / evidence family，如何在 30 个交易日内完成建仓，并把 1R 风险预算分配给这些不完全独立的 evidence。

---

## 1. 核心转向：从单一入口转向 Evidence Accumulation

R01 V3 暴露了一个重要事实：

```text
post30 profile 能覆盖大量 big winner，
但它不是一个干净、低密度、直接可执行的 entry trigger。
```

这意味着后续不应该继续寻找一个万能结构来回答：

```text
今天是否应该一次性买入完整仓位？
```

更合理的问题是：

```text
在初始 probe 后的 30 个交易日内，
是否有多个相互不完全重叠的 evidence family 逐步出现，
这些 evidence 是否足以支持从小 probe 仓升级到较完整的风险预算？
```

因此，仓位变化不应由单个 entry signal 决定，而应由状态迁移和证据累积决定。

---

## 2. 30 日建仓窗口

建议把建仓过程明确限制在初始 probe 后的 30 个交易日内：

```text
build_window = entry_date + 1 .. entry_date + 30
```

在这个窗口内，系统允许：

```text
enter_probe
hold_probe
add_small
add_to_confirmed
stop_build_due_to_failure
```

30 个交易日之后：

```text
no new build risk
only track / trail / reduce / exit
```

也就是说：

```text
+30 天前：解决是否逐步建仓
+30 天后：解决是否继续持有、减仓或退出
```

这个边界很重要。否则系统会在任何新高、任何放量、任何强势状态下不断解释为“还可以加仓”，最后变成无限追涨。

---

## 3. 多个 Probe 点不应叫多个 Entry

如果有 10 个 family，应该称为：

```text
evidence family
```

而不是 10 个 entry signal。

原因是：很多 family 并不是第一次买入点，而是状态证据。例如 V3 的 post30 profile：

```text
close_near_high5
vol_ratio10 > 1.2
vol_ratio3 > 1.2
rps5 > 60
```

它很可能不是 S0 -> S1 的直接 entry trigger，而更像：

```text
S3 -> S4 的 continuation evidence
或 S4/S5 的 winner development profile
```

所以每个 family 应回答不同问题：

```text
它是否支持初始 probe？
它是否支持 probe 存活？
它是否支持第一次加仓？
它是否支持继续跟踪？
它是否只是状态标记，不给新增风险预算？
```

---

## 4. Evidence Family 候选与第一版收缩

下面只是长期候选分类，不是冻结公式。真正写成第一版实验时，不应一次性上 10 个 family。更合理的裁剪是先选 3 到 5 个互补 family，验证 evidence accumulation 框架本身是否成立。

| family | 例子 | 主要含义 | 更适合的状态 |
|:--|:--|:--|:--|
| price breakout | close > high20 / high60 | 价格确认 | S1 / S4 |
| volume / money expansion | vol_ratio / money_ratio 放大 | 资金参与 | S1 / S4 |
| relative strength | rps5 / rps20 / rps60 | 横截面强度 | S1 / S4 |
| pullback hold | 回踩 EMA20 / pivot 不破 | 低风险结构 | S1 / S4 |
| volatility contraction | ATR 收缩后扩张 | 整理后启动 | S1 / S4 |
| industry breadth | 行业内上涨比例、行业强度 | 主题共振 | S4 / S5 |
| market regime | 指数、宽度、风险偏好 | beta 环境 | 组合预算调整 |
| no-failure survival | H10/H20 未失败 | 负证据消失 | S3 |
| acceleration | 新高 + 放量 + gap / 大阳 | 主升浪加速 | S5 |
| distribution absence | 无放量长阴、无反复冲高失败 | 未派发 | S5 / S6 |

这些 family 必须通过数据证明“不完全相干”，不能只靠命名。

第一版更适合从下面几类开始：

```text
post30 profile / momentum state
pullback or structure hold
no-failure survival
industry or market support
```

这样做的目的不是降低研究野心，而是减少自由度。否则 10 个 family、多个阈值、cluster cap、posterior mapping 会一起变成大规模搜索。

---

## 5. 先验概率不能只看 Big Winner 覆盖率

以 post30 profile 为例：

```text
P(signal appears within +30d | big_winner) ≈ 94%
```

这个 94% 是 coverage / recall，不是先验胜率。

建仓预算真正需要的是：

```text
P(big_winner | signal appears)
```

如果这个概率小于 5%，那么它就是：

```text
high recall, low precision
```

这不是坏事，但含义必须正确：

```text
它适合帮助系统不漏掉 winner；
它不适合单独给大仓位。
```

每个 family 至少要估四个量：

```text
P(signal | winner)
P(signal | non_winner)
P(winner | signal)
EV_R(signal)
```

其中 `EV_R` 比单纯胜率更重要：

```text
EV_R = P(win) * avg_win_R - P(loss) * avg_loss_R
```

趋势系统可能胜率低，但 payoff skew 高。一个 `P(winner | signal) = 4%` 的 family 如果少数 winner 平均贡献很大，仍然可能有价值。

---

## 6. 先验应按 Action-Time 样本估计

不能只在 big winner 样本内统计 family。

这一点必须写死：先验概率不能来自 winner-anchored window。winner-anchored coverage 只能作为 recall diagnostic，不能作为仓位预算的 prior。

正确 grain 应是：

```text
instrument + date + family_id
```

或在 episode 层：

```text
seed_episode_id + family_id + family_trigger_date
```

然后定义：

```text
event_t = family_i 在 t 日触发
label = t 后 H 日是否形成 continuation / big winner / failed seed
```

先验计算：

```text
prior_win_rate_i =
  count(event_t 后成为目标状态) / count(event_t)
```

例如：

```text
post30_profile 触发 10000 次
其中 400 次后续成为 big winner
P(big_winner | signal) = 4%
```

这个 4% 才能进入风险预算模型。

因此，prior 的分母应是 train split 里所有 eligible action-time rows，而不是 big winner reference 后的窗口样本。否则会重复 V3 的问题：看起来 coverage 很高，但 precision 和 executable capture 不足。

---

## 7. 用 Likelihood Ratio 表达证据强度

单独看 `P(winner | signal)` 还不够，因为不同 family 的 base rate 不同。

更好的表达是 likelihood ratio：

```text
LR_i = P(signal_i | winner) / P(signal_i | non_winner)
```

或 log-lift：

```text
log_lift_i = log(LR_i)
```

如果：

```text
P(signal | winner) = 94%
P(signal | non_winner) = 20%
LR = 4.7
```

这是很强的 evidence。

但如果：

```text
P(signal | winner) = 94%
P(signal | non_winner) = 80%
LR = 1.175
```

那它只是市场里很常见的强势噪音。

所以每个 family 都必须同时报告：

```text
coverage among winners
base rate among non-winners
posterior precision
expected R value
density / turnover / delay sensitivity
```

---

## 8. 1R 风险预算的含义

这里的 `1R` 是完整单笔风险预算，不是资金比例。

例如账户 100 万，完整单笔风险预算设为 1%：

```text
1R = 10000 元
0.25R = 2500 元最大可承受亏损
```

实际仓位由 stop distance 反推：

```text
position_value = risk_budget_cash / initial_risk_pct
```

因此 risk budget 是亏损预算，不是买入金额。

如果 stop 太近，例如 `initial_risk_pct = 0.5%`，即使只给 0.25R，也会导致 position value 过大。这就是为什么 R01 V3 要求 `initial_risk_pct >= 2%`。

多次 add 时也必须重新计算 R。每一笔 add 都应有自己的：

```text
add_price
add_stop
add_risk_pct = (add_price - add_stop) / add_price
```

总持仓风险不能只看 average cost。更合理的是按当前 protective stop 计算总 open risk：

```text
total_open_risk =
  sum(position_tranche_qty * max(0, tranche_price - current_protective_stop))
```

如果 add-time risk distance 低于下限，或者 total open risk 超过目标 R，这次 add 就不应该发生。这是后续 requirement 前必须补清楚的工程边界。

---

## 9. 风险预算不应按 10 个 Family 平分

假设总建仓风险预算为：

```text
max_build_risk_budget_30d = 1.0R
```

有 10 个 family：

```text
family_1 ... family_10
```

不能简单：

```text
每个 family = 0.1R
```

也不能直接按 `P(winner | signal)` 线性分。

正确原则是：

```text
每个 signal 只拿“边际新增证据”对应的风险预算。
```

一个 family 的有效贡献可以写成：

```text
score_i =
  max(0, lift_i)
  * novelty_discount_i
  * cost_quality_i
  * freshness_i
```

其中：

```text
lift_i = logit(P(winner | family_i)) - logit(base_rate)
novelty_discount_i = 独立性折扣
cost_quality_i = 成本与尾部质量折扣
freshness_i = 信号时效折扣
```

---

## 10. 相关性折扣

family 之间不能假设完全独立。很多 family 可能共享同一类 raw feature，例如：

```text
high breakout
close near high
short-term momentum
rps5
```

这些都可能是 momentum cluster 的变体。

需要估相关性矩阵：

```text
corr_ij
```

相关性可由以下指标组合得到：

```text
binary signal correlation
event overlap
Jaccard overlap
captured winner overlap
failed episode overlap
shared raw feature penalty
```

简单可执行折扣：

```text
novelty_discount_i =
  1 - max(corr_i_with_already_active_families)
```

如果 family_2 和已触发 family_1 的相关度是 0.80：

```text
family_2 的新增证据只按 20% 计算
```

如果两个 family 几乎是同一个指标变体，第二个 family 基本不应新增风险预算。

但这个折扣只能作为二级启发式，不能作为主要去重机制。A 股趋势类信号在 winner 子样本中的相关性往往比全样本更强，简单 marginal correlation 可能低估冗余。

---

## 11. Family Cluster Cap

Cluster cap 应该是主约束，相关性折扣只是 cluster 内的二级折扣。原因是很多 family 会共享同一类 raw feature，例如 price / momentum / relative strength，不能让它们重复贡献仓位。

讨论级别上可先设：

| family cluster | max contribution |
|:--|--:|
| price / breakout / momentum | 0.30R |
| volume / money | 0.25R |
| relative strength | 0.20R |
| pullback / structure | 0.30R |
| industry / theme | 0.25R |
| market regime | 0.20R |
| survival / no-failure | 0.20R |
| anti-distribution / exit-quality | 0.20R |

同一 cluster 内多个 signal 触发时，可用递减权重：

```text
first signal = 100%
second related signal = 30%
third related signal = 0% or audit-only
```

这样可以避免：

```text
5 个 momentum 变体同时触发，
系统误以为有 5 份独立证据。
```

---

## 12. 从 Signal Budget 改成 Target Total Risk

更稳的方式不是每个 signal 一触发就分配一笔固定加仓，而是更新目标总风险预算。

先计算 posterior：

```text
posterior_log_odds =
  base_log_odds
  + sum(discounted_log_lift_i)
```

得到：

```text
posterior_prob = sigmoid(posterior_log_odds)
```

再映射到目标风险：

| posterior big-winner / continuation probability | target total risk |
|:--|--:|
| below 3% | 0R |
| 3% - 5% | 0.10R |
| 5% - 8% | 0.25R |
| 8% - 12% | 0.50R |
| 12% - 18% | 0.80R |
| above 18% | 1.00R |

这张映射表本身也是自由参数。不能在 validation 上调。第一版可以先用更粗的三档映射，并在 train split 冻结：

```text
probe only
moderate add
full build cap
```

validation 和 robustness 只评估，不再改断点。

实际加仓：

```text
add_risk =
  min(target_total_risk - current_effective_risk,
      remaining_build_budget,
      single_add_cap)
```

其中：

```text
single_add_cap = 0.25R or 0.30R
total_build_budget_30d = 1.0R
```

这比“每个 signal 固定给 0.1R”更合理，因为它只按当前总证据调整目标风险。

---

## 13. 示例：三个 Family 同时触发

假设：

```text
base_rate = 2%
family_1 posterior = 5%
family_2 posterior = 4%
family_3 posterior = 8%
```

对应 lift 假设为：

```text
lift_1 = 0.95
lift_2 = 0.71
lift_3 = 1.45
```

但 family_1 和 family_2 很相似：

```text
corr_12 = 0.80
corr_13 = 0.20
```

如果三者都触发：

```text
score_1 = 0.95
score_2 = 0.71 * (1 - 0.80) = 0.14
score_3 = 1.45 * (1 - 0.20) = 1.16
total = 2.25
```

边际贡献：

```text
family_1 ≈ 42%
family_2 ≈ 6%
family_3 ≈ 52%
```

但如果 family_1 和 family_2 都属于 price / momentum cluster，而该 cluster cap 是 0.30R，则这两个 family 合计最多只能支持 0.30R。

---

## 14. Post30 Profile 的仓位含义

V3 post30 profile 的意义应这样理解：

```text
94% winner coverage 说明它不漏；
<5% precision 说明它不能单独重仓。
```

所以：

```text
post30_profile alone:
  max 0.10R - 0.25R

post30_profile + survived + pullback_hold:
  maybe 0.40R - 0.60R

post30_profile + industry_confirmed + no_distribution + trend_alive:
  maybe 0.80R - 1.00R
```

但这些数字只能作为设计假设，不能直接冻结。实际阈值必须通过 train freeze、validation check、robustness check 来确定。

---

## 15. 与状态机的连接

可以把仓位变化写成：

```text
S0 Candidate:
  no position

S1 Probe:
  enter 0.10R - 0.25R

S3 Survived:
  hold probe, no add

S4 Confirmed Continuation:
  evidence score reaches add threshold
  target total risk = 0.40R - 0.80R

S5 Big Winner Development:
  build window closed or strong continuation confirmed
  target total risk <= 1.00R / 1.20R only with profit cushion

S6 Exhaustion:
  reduce

S7 Exit:
  zero risk
```

关键是：

```text
S4 / S5 不是主观状态名，
而是 posterior evidence score 和 action authority 的组合。
```

---

## 16. +30 天后进入 Tracking State

30 日建仓结束后，系统不再新增 risk budget。

Tracking state 只允许：

```text
hold
trail stop
partial reduce
exit
```

不允许：

```text
new add
reset build window
because new family appears, restart position construction
```

除非未来单独设计一个新 requirement，证明 S5 之后的 late add 有独立收益和 tail-risk no-harm。

如果担心 +30 cutoff 砍掉一部分右尾，可以把 `+30..+60 trailing add` 放进附录 ablation，而不是主规则。附录版本也应更保守，例如只允许很小的新增预算，并要求已有 profit cushion。第一版主实验仍应保留 +30 hard build cutoff，避免重新变成无限追涨。

---

## 17. 主要风险：Post-Selection 与 Double Counting

这个方向有两个最大风险。

第一，post-selection：

```text
我们已经看过 post30 winner profile，
如果继续从同一批 winner 里挑 10 个 family，
很容易把事后发现包装成先验。
```

因此必须：

```text
train: family discovery / prior estimation
validation: freeze weights and thresholds
robustness: only evaluate
```

第一版还应限制 family 数量。10 个 family 可以作为长期路线图，但不适合作为第一个实现目标。先从 3 到 5 个 family 开始，才能判断框架是否真的有增量。

如果 family 来自 all-splits discovery，只能输出：

```text
go_to_oos_retest_required
```

不能直接进入 R02/R03。

第二，double counting：

```text
多个 family 可能只是同一个 momentum signal 的不同写法。
```

所以必须输出：

```text
family correlation audit
cluster cap audit
marginal contribution audit
```

---

## 18. 建议的新 Requirement 方向

如果继续推进，不应叫普通 R02 continuation single-rule search。

更准确的方向是：

```text
EP4 R02: 30-Day Evidence-Accumulation Build Probe
```

核心问题：

```text
多个低相关 evidence families 是否能在 initial probe 后 30 个交易日内，
把小 probe 仓位逐步升级为合理 risk budget，
同时提升 winner capture ratio，
并且不显著恶化 failed-loss / tail risk / density / turnover？
```

最小输出应包括：

```text
family prior audit
family correlation / cluster cap audit
posterior score path
build action path
risk budget allocation audit
no-add and matched-delay baselines
false-add and missed-winner audit
```

这仍然只是讨论方向，不是 requirement。真正 requirement 需要再冻结 family 公式、R-unit 口径、窗口边界和 gate。

---

## 19. 暂定判断

这个方向是可行的，而且比寻找单一 S4 结构更贴近 EP4 的核心思想：

```text
右尾收益不是来自一次性预测，
而是来自小风险观察、证据累积、逐步加仓和状态化退出。
```

但它必须被严格约束：

```text
第一版不能让 10 个 family 变成 10 次自由调参；
prior 不能用 winner-anchored coverage 估；
staged add 必须重新计算 add-time R 和 total open risk；
cluster cap 必须是主约束；
不能让相关指标重复贡献仓位；
不能用 winner coverage 替代 posterior precision；
不能在 +30 后继续无限建仓；
不能在 all-splits discovery 后直接授权下一阶段。
```

因此下一步应该先写成 requirement，而不是直接实现策略。
