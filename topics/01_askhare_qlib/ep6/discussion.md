# EP6 discussion：A 股中等周期波段方向

> 生成日期：2026-05-25
> 状态：研究方向讨论记录，不是 requirement，不是策略授权，不是 validation。
> 背景：EP5 已经把 H3/H5/H10 超短周期的常规 breakout / pullback / volume-rank family 大部分否决，仅 `daily-observed vwap_deviation H3` 通过 diagnostic 但未授权策略。本文把问题切到 EP6：如果放弃超短周期，A 股中等周期波段是否有更合理的研究入口。

---

## 0. TL;DR

从现有 A 股论文和 EP5 结果合并看，结论不是“中等周期一定更容易”，而是：

```text
A 股中等周期的裸 price momentum / breakout / pullback 并不是天然强项；
更可借鉴的方向是把中等周期重新定义成 residual / factor / industry / regime-conditioned exposure。
```

换句话说，EP6 不应直接写：

```text
过去 20/60/120 日涨得多的继续买；
突破 N 日新高继续买；
回撤到均线买反弹；
H3/H5 失败后换成 H20/H60 再扫一次。
```

更合理的主线是：

```text
1. residual / idiosyncratic momentum；
2. factor momentum / factor timing；
3. industry momentum / sector rotation；
4. price-limit-adjusted momentum；
5. regime-conditioned contrarian / reversal；
6. 上述方向的低维组合，而不是裸形态信号。
```

EP6 的核心问题应是：

```text
中等周期是否存在一个可以跨 validation 保留、可解释、可执行、after-cost 不被完全吃掉的 exposure unit？
```

不是：

```text
能不能把常规 breakout / pullback 参数换一组重新救活？
```

---

## 1. 为什么这个问题值得从 EP5 切到 EP6

EP5 的短周期诊断给了两个信息：

1. **H3/H5 alpha 并不会因为周期短就自然很多。**
   超短周期里，公开日线形态通常混合了微观结构、流动性、注意力、涨跌停、行业共振和 beta 暴露。它们看起来像 entry pattern，但在 validation-first、after-cost、fold-stable 的约束下容易退化成噪声。

2. **唯一通过的 R08.2 不是常规形态，而是 within-stock state。**
   `vwap_deviation` 的价值更像“价格相对成交锚的状态偏离”，不是“过去几天涨/跌所以未来继续/反转”。R08.3 同时证明 daily observation 不是通用增益，volume/rank family 没有被 daily 化救活。

所以 EP6 如果切到中等周期，不能只把 horizon 从 H3/H5 改成 H20/H60。真正要换的是问题定义：

```text
从日线形态 alpha
切到
残差状态 / 风格轮动 / 行业轮动 / 机制修正 / regime 条件化。
```

---

## 2. 外部论文给出的 A 股中等周期地图

这里把“中等周期”粗略定义为：

```text
formation: 4 周到 12 个月；
holding: 1 周到 6 个月；
data: 日频或周频可生成，最终以周/月为主做低换手 exposure；
目标: 波段型 exposure unit，不是 H3/H5 超短交易，也不是多年基本面持有。
```

### 2.1 裸 momentum 在 A 股并不稳

多篇文献共同指向一个事实：A 股的传统 stock-level momentum 明显弱于美股，并且经常被 reversal、turnover、投资者异质性和涨跌停事件污染。

关键证据：

| 论文 / 来源 | 样本与方法 | 主要发现 | 对 EP6 的含义 |
|:--|:--|:--|:--|
| Yue, Li, Ruan, `Does short-term momentum exist in China?` | 复制 Medhat and Schmeling 的前一月收益 x 换手双排序框架 | 中国市场没有 short-term momentum，主要是 short-term reversal 和负 turnover effect。论文认为原因可能是成交量不能有效映射基本面信息，且交易者异质性抵消了持续价格压力。 | 不应把“高换手 + 短期赢家”当成自然延续信号；需要先分离 turnover / attention / reversal。 |
| Gang, Qian, Xu, `Investment horizons, cash flow news...` | 比较不同投资周期的 momentum / reversal | 中国市场 momentum 只在小于一周的周期有盈利；更长周期 reversal 更占优；解释为中国投资者对现金流新闻更常过度反应。 | 中等周期裸追涨可能天然站在 reversal 的对手盘上。 |
| Kang / Liu / Ni 早期 China momentum/reversal 系列及后续综述 | 不同 J/K 周期的 winner-loser portfolio | 样本期和周期变化会导致 momentum / contrarian 结论混杂。 | EP6 必须做 validation-first 和 regime 分解，不能用一个全样本均值下判断。 |

这个结论能解释 EP5 里常规 breakout / pullback 为什么容易失败：

```text
breakout 可能不是 underreaction continuation，
而是 attention / limit-up / lottery-demand / crowded buying 后的 overreaction；

pullback 可能不是 mean-reversion entry，
而是趋势破坏、流动性抽走、行业 beta 下行或负面信息慢反应。
```

### 2.2 Residual momentum 比 raw momentum 更像可研究对象

Qi Lin 的 `Residual momentum and the cross-section of stock returns: Chinese evidence` 是最值得 EP6 借鉴的单条线索之一。

文献要点：

```text
样本：上交所 / 深交所 A 股，1997-07 到 2017-12；
核心做法：不用原始过去收益排序，而是用 residual stock returns 排序；
结果：residual momentum 策略有显著盈利，文献页摘要称其不能被常见 factor model 解释；
公开摘要还报告 annualized return 约 10.584%；
解释：残差动量长期不反转，更支持 underreaction，而不是单纯过度反应。
```

对 EP6 的含义：

```text
如果 raw momentum 在 A 股弱，不代表 momentum 信息不存在；
它可能被 market / industry / size / value / liquidity / volatility common exposure 淹没。

EP6 应优先问：
过去中等周期的 stock-specific residual trend 是否比 raw trend 更可迁移？
```

这和 EP5 的 R09 思路一致：先拆 beta / industry / size / liquidity，再谈 edge。

### 2.3 Factor momentum 可能比个股 momentum 更稳定

Ma, Liao, Jiang 的 `Factor momentum in the Chinese stock market` 给出一个更高层的线索。

文献要点：

```text
样本：CSMAR，2001-01 到 2019-12，沪深 A 股；
对象：10 个常用 characteristic-based factors；
结果：factor momentum 年化收益约 9.91%，Sharpe 约 1.15；
论文认为 factor momentum 可以解释 / 吸收多类中国市场 momentum，包括 stock momentum、high-priced momentum、industry momentum；
经济解释：mispricing correction、factor premium exposure、predictability manifestation；
在高 aggregate idiosyncratic volatility、高 information asymmetry、强 short-sale constraints 环境下更强。
```

对 EP6 的含义：

```text
如果 A 股中等周期的价格延续不是稳定地发生在个股层，
可能稳定地发生在 factor sleeve 层。
```

这给 EP6 一个不同于“选股票”的路径：

```text
先判断市场当前奖励哪些因子；
再在那些因子暴露中找低成本、低换手、可执行的 long-only tilt；
而不是直接买过去涨幅最大的股票。
```

注意：factor momentum 不是“更多因子组合”的借口。它应被定义为低维 factor-return timing 问题，而不是重新打开大规模 factor mining。

### 2.4 Industry momentum / sector rotation 有一定证据，但要谨慎

Guiquan Lin 的 `Industry Momentum Strategies in A-shares Market` 研究了申万行业层面的 momentum。

文献要点：

```text
样本：2010-2019，30 个申万行业；
方法：行业过去收益形成期 J 与持有期 K 组合；
结果：6 个月形成 + 6 个月持有在该文中表现最稳；
跳过一个月并没有明显改善；
论文同时指出只有部分 winner-loser 组合统计显著；
其行业构造使用每个行业 5 个高市值股票，样本设计较窄。
```

对 EP6 的含义：

```text
行业动量值得作为 EP6 主线之一，
但不能直接照搬论文结果。

本地应使用完整 PIT 行业成分或稳定行业分类，
并区分：
1. 行业本身是否有 rotation edge；
2. 行业内选股是否增加 edge；
3. 行业 winner 是否只是 market beta / policy beta / liquidity beta。
```

行业线的好处是可解释、换手低、可能更适合 A 股的主题轮动结构。风险是容易被少数政策周期和高 beta 行业主导。

### 2.5 Price-limit-adjusted momentum 是 A 股特有的机制修正方向

Liu, Wu, Zhu 的 `Price overreaction to up-limit events and revised momentum strategies in the Chinese stock market` 对 A 股涨停机制给出一个很关键的解释。

文献要点：

```text
A 股 10% 日涨跌幅限制为识别极端消息过度反应提供自然实验；
涨停日可能导致 formation-period momentum 被高估；
这些被高估的 winner 在 holding period 反而更容易 reversal；
因此构造 momentum 时应识别并剔除 / 修正涨停相关过度反应日。
```

这和交易所机制一致：上交所英文交易机制页说明，主板 A/B 股竞价交易通常有 10% 日价格限制，风险警示股票为 5%，科创板竞价交易为 20%。

对 EP6 的含义：

```text
不要把所有强上涨都当成 trend；
要区分 smooth trend 和 limit-hit attention trend。
```

一个非常具体的 EP6 假设：

```text
中等周期 momentum 的有效部分可能来自“连续、小步、低涨停污染”的残差趋势；
无效甚至反向的部分来自“涨停驱动、注意力驱动、短期拥挤”的表面强势。
```

这也解释了为什么裸 breakout 失败：breakout 在 A 股里很可能过度捕捉涨停 / 题材 / 注意力尾部，而不是低噪声的趋势延续。

### 2.6 Weekly idiosyncratic momentum 和 regime 条件可能更接近“波段”

Shi and Zhou 的 `Horse race of weekly idiosyncratic momentum strategies...` 研究周频 idiosyncratic momentum。

文献要点：

```text
样本：A 股个股，1997-01 到 2017-12；
比较：raw weekly momentum 与 idiosyncratic momentum；
发现：全样本同时存在 contrarian effect 和 idiosyncratic momentum effect；
收益与 idiosyncratic risk metrics 有关；
IVol / maximum drawdown 相关的 IMOM portfolio 表现更强；
更高盈利与上行市场、高流动性、高投资者情绪有关。
```

对 EP6 的含义：

```text
中等周期不是固定方向问题，而是 state-dependent 问题。
同一个 residual momentum 在上行、高流动性、高情绪 regime 可能更强；
在下行或低流动性 regime 可能变弱或变成 reversal。
```

这条线比裸 H20/H60 momentum 更贴合 EP5 的经验：如果不做 regime / liquidity / breadth 分解，平均值会把多个互相抵消的状态混在一起。

### 2.7 Contrarian / reversal 不能忽略，尤其在中等周期

关于 A 股 contrarian 的文献很多，方向并不完全一致，但共同点是：A 股中长期和部分周/月周期的 reversal 证据不弱。

关键证据：

| 来源 | 主要发现 | 对 EP6 的含义 |
|:--|:--|:--|
| Shi, Jiang, Zhou, `Profitability of contrarian strategies in the Chinese stock market` | 月频 A 股 1997-2012；短期和长期 contrarian 均有证据，长期更稳；bull/bear state 下结果差异明显。 | 中等周期不应只研究 continuation，也要研究 regime-conditioned reversal。 |
| Chen, Jiang, Li, `The state of the market and the contrarian strategy...` | 周频 A 股 1995-2010；中等周期 momentum / contrarian 不显著；但调整微观结构后，4-8 周 contrarian 有约 0.2%/周收益，且下跌市场后更强。 | “下跌市场后的 4-8 周 reversal / loss-avoidance”可能比常规 pullback 更合理。 |
| `Investment horizons, cash flow news...` | 小于一周 momentum；更长周期 reversal；解释为过度反应。 | 如果中等周期主要是 overreaction correction，则 EP6 应把 reversal 作为一等公民。 |

对我们尤其重要的是：不要把 contrarian 简化成“跌多了就买”。更合理的表达是：

```text
在 market-state / industry-state / liquidity-state / price-limit contamination 被控制后，
是否存在可执行的 overreaction-correction exposure？
```

---

## 3. 为什么常规 breakout / pullback 在 A 股中短周期容易失败

下面是结合 EP5 和外部论文后的原因猜想。它们不是已经验证的结论，而是 EP6 需要显式检验的假设。

### 3.1 裸形态混合了 underreaction 和 overreaction

美股传统 momentum 的经典解释偏 underreaction：信息逐步进入价格，趋势延续。

A 股文献里更常出现的是：

```text
短期注意力推升；
涨停吸引交易者；
现金流新闻过度反应；
赢家组合随后 reversal；
换手越高，短期 reversal 越强。
```

所以同一个 “breakout” 可能包含两类完全相反的东西：

| breakout 类型 | 未来含义 |
|:--|:--|
| smooth / residual / low attention breakout | 可能是真 underreaction continuation。 |
| limit-up / high attention / high turnover breakout | 可能是 overreaction，后面更容易 reversal。 |

如果不区分这两类，整体 spread 会被抵消。

### 3.2 A 股的涨跌停机制会污染 formation return

涨停不是普通的大涨。它同时代表：

```text
价格被机制截断；
未成交需求可能残留；
注意力集中；
次日拥挤交易；
后续反转风险上升。
```

所以过去 N 日收益如果包含涨停日，可能高估了“可延续趋势”。EP6 如果研究 momentum，应至少报告：

```text
formation return including limit-hit days；
formation return excluding up-limit days；
up-limit contribution share；
post-limit continuation / reversal；
smooth-return-only momentum。
```

### 3.3 个股形态常被行业 / factor 状态主导

一个股票突破，可能只是它所在行业在涨；一个股票回撤，可能只是整个风格在降温。

如果不拆 common exposure，裸形态会有两个问题：

```text
1. spread 来自行业 / 风格 beta，而不是 stock-level edge；
2. validation 年的行业 / 风格 regime 一换，方向就消失。
```

这正是 EP5 R09 要对 `vwap_deviation` 做 decomposition 的原因。EP6 更应该把 decomposition 前置，而不是先跑一堆 price pattern。

### 3.4 投资者异质性会让动量和反转同时存在

A 股中个人投资者占比高、交易者类型复杂。可能同时存在：

```text
一部分人追涨导致 continuation；
一部分人过度交易导致 reversal；
一部分机构在主题/行业层面做轮动；
一部分资金受融资融券、涨跌停、赎回压力、政策预期约束。
```

结果是平均意义上的 “winner minus loser” 不稳定。只有在特定 state 下，某个方向才可能占优。

### 3.5 中等周期可能是“主题/行业/factor 波段”，不是“单股票形态波段”

A 股的波段感很多时候来自：

```text
政策主题；
行业景气；
风格切换；
风险偏好；
流动性松紧；
成交拥挤程度。
```

这些变量在个股 K 线形态上会留下痕迹，但形态本身未必是根因。因此 EP6 应优先测试 higher-level exposure，再看个股选择是否增益。

### 3.6 成本和可执行性对中等周期仍然重要

中等周期换手低于 H3/H5，但不代表成本无关。尤其是：

```text
涨停后买不到；
跌停后卖不出；
高波动小票冲击成本高；
主题股拥挤时滑点集中；
long-short 论文收益在 A 股现实里未必可复制；
long-only 版本可能只剩 beta。
```

所以 EP6 不能直接采用文献的 long-short spread 作为可经营收益。必须报告 long-only、relative、after-cost 三层。

---

## 4. EP6 推荐研究主线

### 主线 A：Residual / Idiosyncratic Momentum

这是最高优先级的个股层中等周期方向。

核心假设：

```text
raw momentum 被 common exposure 和涨跌停污染；
剥离 market / industry / size / liquidity / volatility 后，
中等周期 residual trend 可能仍有可迁移的信息。
```

建议最小实验形态：

```text
formation windows:
  20 / 40 / 60 / 120 trading days

skip windows:
  0 / 5 / 10 trading days

holding horizons:
  H20 / H40 / H60

residualization:
  market beta
  industry return
  size bucket
  liquidity bucket
  volatility bucket

controls:
  raw momentum baseline
  industry-neutral comparator
  size/liquidity matched comparator
  up-limit-adjusted variant
```

必须回答：

1. residual momentum 是否优于 raw momentum；
2. spread 是否来自少数行业 / 小票 / 高换手；
3. H20/H40/H60 是否有稳定 horizon shape；
4. after-cost 后是否还剩 exposure；
5. long-only 是否可行，还是只能 relative framing。

### 主线 B：Factor Momentum / Factor Timing

这是最值得和 A 股文献接轨的 higher-level exposure 方向。

核心假设：

```text
A 股的中等周期 continuation 更稳定地发生在 factor-return 层，
而不是个股 raw return 层。
```

候选 factor sleeves：

```text
size
value
quality
profitability
investment / asset growth
low volatility
liquidity / turnover
short-term reversal
residual momentum
industry-adjusted momentum
```

建议做法：

```text
1. 先构造少数固定 factor portfolios，不做大规模 mining；
2. 每周或每月计算 factor sleeve return；
3. 用过去 3/6/12 个月 factor return 做 time-series momentum；
4. 对下一期 factor return 做 validation-first 检验；
5. 再把 factor signal 映射回 long-only stock tilt。
```

关键判读：

| 结果 | 含义 |
|:--|:--|
| factor momentum 通过，个股 raw momentum 不通过 | EP6 应转向 factor-level allocation / tilt。 |
| factor momentum 只在高情绪 / 高流动性 regime 有效 | 可作为 regime-conditioned exposure，不应全时运行。 |
| factor momentum 消失但 residual momentum 保留 | 个股残差信息更重要。 |
| 两者都不通过 | 中等周期 continuation 方向弱，应转入 reversal / regime 主线。 |

### 主线 C：Industry Momentum / Sector Rotation

这是解释性最强、可能换手最低的方向。

核心假设：

```text
A 股中等周期波段更多是行业/主题资金迁移，
个股形态只是行业状态的局部表达。
```

建议最小实验：

```text
industry classification:
  申万一级 / 中信一级，必须固定口径，避免未来成分泄漏

formation:
  20 / 60 / 120 trading days 或 1 / 3 / 6 months

holding:
  H20 / H40 / H60 或 1 / 3 months

portfolio:
  top industries long-only
  industry-neutral stock selection inside winner industries
  market / beta / liquidity controlled comparator
```

必须避免：

```text
只买过去涨幅最高行业；
不剥离 broad market beta；
用少数龙头股票代表行业却不报告 concentration；
把 policy theme hindsight 写成可执行信号。
```

### 主线 D：Price-Limit-Adjusted Momentum

这是 A 股机制特色方向，适合作为主线 A/C 的修正层。

核心假设：

```text
过去收益里的涨停贡献越高，后续 momentum 越不可靠；
剔除涨停日后的 smooth residual trend 更可能延续。
```

建议分组：

```text
up_limit_count in formation window
up_limit_return_share
post_limit_gap / next-open feasibility
smooth_return = formation return excluding up-limit days
limit_contaminated_return = formation return - smooth_return
```

关键输出：

1. smooth-return momentum spread；
2. limit-contaminated momentum spread；
3. up-limit-heavy winners 的后续 reversal；
4. 买入可执行率；
5. 行业 / 市值 / 流动性集中度。

如果这条线成立，EP6 可以解释为什么传统 breakout 无效：

```text
不是趋势不存在；
而是最显眼的趋势常常是涨停/注意力污染后的反向样本。
```

### 主线 E：Regime-Conditioned Contrarian / Reversal

这是 continuation 失败后的平行主线，不是补丁。

核心假设：

```text
A 股在超过一周的周期上更容易出现 overreaction correction；
但 reversal 必须受 market state、行业 state、流动性 state 约束。
```

候选状态：

```text
market_state:
  up / down / high volatility / low volatility

industry_state:
  industry uptrend / downtrend / high dispersion

liquidity_state:
  high turnover / low turnover
  liquidity contraction / expansion

attention_state:
  limit-hit cluster
  abnormal turnover
  abnormal amplitude
```

建议最小实验：

```text
formation:
  prior 4 / 8 / 12 weeks return

holding:
  next 4 / 8 weeks

direction:
  loser rebound
  winner fade
  long-only loser rebound first

controls:
  market down vs up
  industry down vs up
  limit-hit contamination
  liquidity bucket
```

注意：A 股现实里 short leg 不一定可行，所以 winner fade 不能直接等同策略收益。更实际的是先问 long-only loser rebound 是否有 after-cost exposure。

### 主线 F：Hybrid Confirmation

如果 EP6 单主线出现弱通过，可以考虑低维组合，但必须遵守两个约束：

```text
1. 组合必须来自已通过单独 diagnostic 的 component；
2. 组合只能用于 confirmation，不允许用 validation 搜参数。
```

可能组合：

```text
residual momentum + low limit-hit contamination
residual momentum + industry momentum confirmation
factor momentum + industry breadth confirmation
regime-conditioned reversal + liquidity recovery
```

---

## 5. EP6 不建议启动的方向

| 不建议方向 | 原因 |
|:--|:--|
| 裸 H20/H60 breakout / new-high sweep | 很可能只是把 EP5 失败的裸形态换周期，无法解释 common exposure 和涨停污染。 |
| 裸 pullback / 均线回踩 | 容易混合 falling knife、行业 beta 下行和短期 liquidity shock。 |
| 全量 GTJA / TA 指标重扫 | EP4/EP5 已经显示 family sweep 容易变成多重比较和 horizon shopping。 |
| 直接复刻 long-short 论文组合 | A 股 short leg、融券、涨跌停、成本、冲击和可交易性会改变结论。 |
| 只看全样本 IC 或多空均值 | A 股周期结论高度依赖 regime，需要 fold / year / market-state 分解。 |
| 用行业主题事后叙事代替信号 | 行业 rotation 值得做，但必须是 ex-ante 可计算信号。 |

---

## 6. EP6 的推荐成功标准

EP6 应比 EP5 更明确地区分三种读数：

```text
diagnostic-supported:
  有可迁移 spread / breadth / monotonicity / concentration 证据，
  但未证明可交易。

exposure-unit-supported:
  after-cost、可执行性、turnover、blocked execution、regime fragility 后仍保留。

strategy-authorized:
  只有在 exposure unit 通过后，才允许写 portfolio / strategy requirement。
```

建议 EP6 收敛条件：

```text
满足其一即可：

1. residual / factor / industry / adjusted momentum 中至少一条形成 after-cost 可经营 exposure unit；
2. continuation 方向全部失败，但 regime-conditioned reversal 形成可经营 exposure unit；
3. 所有方向均失败，明确输出：
   当前 A 股日频/周频/当前 universe 下，中等周期波段不存在可经营 exposure unit，
   后续必须切换数据维度（分钟/盘口/订单流）、universe、或研究目标。
```

不允许的失败模式：

```text
用一个文献结论直接授权策略；
用全样本显著掩盖 validation fold 不稳定；
用行业/主题叙事解释失败但不重跑分解；
在 continuation 失败后继续扩大 pattern search。
```

---

## 7. 一个可执行的 EP6 研究顺序

建议顺序如下：

```text
EP6.R01:
  A 股中等周期文献映射与本地 baseline audit
  只跑 raw momentum / breakout / pullback / reversal baseline，建立失败或弱基线。

EP6.R02:
  residual / idiosyncratic momentum diagnostic
  对比 raw momentum，前置 industry/size/liquidity/volatility decomposition。

EP6.R03:
  factor momentum diagnostic
  低维 factor sleeve，不做大规模 family mining。

EP6.R04:
  industry momentum / sector rotation diagnostic
  行业层先行，再判断行业内选股是否增益。

EP6.R05:
  price-limit-adjusted momentum
  验证涨停污染是否解释 raw momentum 失败。

EP6.R06:
  regime-conditioned contrarian / reversal
  continuation 若不稳，正式测试 overreaction correction。
```

这个顺序的好处是：

```text
先确认裸 baseline 是否真的弱；
再逐层剥离 common exposure；
再从 stock-level 转向 factor / industry level；
再处理 A 股特有机制；
最后把 continuation 与 reversal 分成两个问题。
```

---

## 8. 对当前问题的直接回答

“A 股做波段，也就是中等周期，有没有论文？”

有，而且结论并不支持简单乐观。更准确的说法是：

```text
A 股有中等周期相关论文，
但它们普遍不鼓励直接做裸 stock momentum / breakout。

论文更支持：
1. residual momentum；
2. factor momentum；
3. industry momentum；
4. 涨停/价格限制修正后的 momentum；
5. 特定 regime 下的 contrarian / reversal。
```

因此 EP6 应该把“波段”重新定义为：

```text
一个经过 residualization、mechanism adjustment、regime conditioning 后的中等周期 exposure unit。
```

而不是：

```text
过去涨得多所以继续涨；
突破所以买；
回踩所以买。
```

---

## 9. 参考资料

1. Qi Lin, `Residual momentum and the cross-section of stock returns: Chinese evidence`, Finance Research Letters, 2019.
   https://ideas.repec.org/a/eee/finlet/v29y2019icp206-215.html

2. Tian Ma, Cunfei Liao, Fuwei Jiang, `Factor momentum in the Chinese stock market`, Journal of Empirical Finance, 2023.
   https://www.sciencedirect.com/science/article/abs/pii/S0927539823001251

3. Ruolan Ouyang, Kun Zhang, Xuan Zhang, Dongming Zhu, `Can factor momentum beat momentum factor? Evidence from China`, Finance Research Letters, 2024.
   https://www.sciencedirect.com/science/article/pii/S1544612324000515

4. Guiquan Lin, `Industry Momentum Strategies in A-shares Market`, Atlantis Press, 2022.
   https://www.atlantis-press.com/article/125980489.pdf

5. Jianhua Gang, Zongxin Qian, Tiange Xu, `Investment horizons, cash flow news, and the profitability of momentum and reversal strategies in the Chinese stock market`, Economic Modelling, 2019.
   https://www.sciencedirect.com/science/article/abs/pii/S026499931930207X

6. Chenye Liu, Ying Wu, Dongming Zhu, `Price overreaction to up-limit events and revised momentum strategies in the Chinese stock market`, Economic Modelling, 2022.
   https://www.sciencedirect.com/science/article/abs/pii/S0264999322001560

7. Huai-Long Shi, Wei-Xing Zhou, `Horse race of weekly idiosyncratic momentum strategies with respect to various risk metrics: Evidence from the Chinese stock market`, The North American Journal of Economics and Finance, 2021.
   https://ideas.repec.org/a/eee/ecofin/v58y2021ics106294082100098x.html

8. Huai-Long Shi, Zhi-Qiang Jiang, Wei-Xing Zhou, `Profitability of contrarian strategies in the Chinese stock market`, PLOS ONE, 2015.
   https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0137892

9. Qiwei Chen, Ying Jiang, Yuan Li, `The state of the market and the contrarian strategy: evidence from China's stock market`, Journal of Chinese Economic and Business Studies, 2012.
   https://ideas.repec.org/a/taf/jocebs/v10y2012i1p89-108.html

10. Yue Tian, Tianjiao Li, Xinfeng Ruan, `Does short-term momentum exist in China?`, China Finance Review International, 2023.
    https://www.sciencedirect.com/science/article/abs/pii/S0927538X22002153

11. Shanghai Stock Exchange, `Stock Trading Mechanism`.
    https://english.sse.com.cn/start/trading/mechanism/

12. Ting Chen, Zhenyu Gao, Jibao He, Wenxi Jiang, Wei Xiong, `Daily Price Limits and Destructive Market Behavior`, NBER Working Paper 24014, 2017.
    https://www.nber.org/papers/w24014
