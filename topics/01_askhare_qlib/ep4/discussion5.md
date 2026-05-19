# EP4 Discussion 5: Alpha Pool Discovery, Relative-Improvement Pools, and Market-State Exposure Limits

> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 validation。
>
> 背景：基于 `discussion4.md`、R04/R04b/R04c/R04d/R04e 的结论，以及后续关于 `Market-State Cash / Exposure Sleeve` 和 alpha pool discovery 的讨论，重新界定 EP4 后续研究方向。核心问题是：如果现有 RPS / family pools 只能做到 relative improvement，下一步应如何寻找真正有 alpha 的新事件 universe。

---

## 1. 当前判断

EP4 到 R04d/R04e 前的证据已经比较清楚：

```text
已有 stock-level signals 有信息，
但大多只表现为：
  right-tail enrichment
  path-state confirmation
  relative left-tail improvement

它们还没有稳定表现为：
  action-time after-cost positive expectancy alpha pool
```

因此后续必须把两个概念严格分开：

```text
matched delta > 0
AND validation net < 0
= relative improvement pool
!= alpha pool
```

这是 R04c/R04d 最重要的术语纪律。一个 pool 相对很差的 matched baseline_A 少亏，不等于它已经可以承担主仓。

---

## 2. Market-State Cash / Exposure Sleeve 的边界

Market-state cash sleeve 的价值在于组合层风险控制，而不是创造 alpha。

它的形式是：

```text
fixed candidate pool
fixed stock membership
fixed event entry / exit policy

portfolio gross exposure =
  1.0 / 0.5 / 0.0
  based on market state
```

它最多能做三件事：

```text
1. 少亏
2. 降低 max drawdown / worst 20d / monthly p10
3. 改善几何复利路径
```

但它不能凭空解决盈利问题。

如果：

```text
pool_return | risk_on <= 0
pool_return | risk_neutral <= 0
pool_return | risk_off < 0
```

那么 exposure sleeve 最多把大亏改成小亏，不会把底层 pool 变成正期望。

因此 cash sleeve 的正确研究问题不是：

```text
能否靠空仓规则让策略赚钱？
```

而是：

```text
亏损是否主要来自可识别的 bad market states？
如果剔除或降权这些 states，
剩余 risk-on full-exposure portfolio 是否本身已经为正？
```

### 2.1 必须加入的 hard condition

任何 market-state exposure overlay 不能只靠左尾改善通过。它至少需要证明：

```text
risk_on full-exposure portfolio validation net > 0
overall overlay validation period return > 0
overall overlay daily mean > 0
monthly p10 improved vs full-exposure baseline
max drawdown improved vs full-exposure baseline
average gross exposure not too low
positive return not solely from being mostly cash
robustness does not destroy right-tail / positive-year payoff
```

如果 risk-on full-exposure portfolio 在 validation 上都不赚钱，则 cash sleeve 不允许 claim success。

建议写成 kill criteria：

```text
if risk_on_full_exposure_validation_net <= 0:
  market_state_cash_sleeve_cannot_pass
```

### 2.2 更准确的研究名称

这个方向不应直接命名为：

```text
Market-State Cash Sleeve Strategy
```

更准确的是：

```text
Market-State Return Decomposition and Exposure Overlay Diagnostic
```

第一阶段先做 return decomposition：

```text
risk_on
risk_neutral
risk_off

for each state:
  active days share
  gross exposure share
  net return contribution
  left-tail contribution
  right-tail contribution
  drawdown contribution
```

只有发现某些 market state 下 full-exposure pool 本身为正，且 bad states 贡献主要左尾，才值得进入 exposure overlay。

---

## 3. 相关文献给出的先验

这些文献不应被当作可直接搬到 A 股日频 long-only 策略的结论。它们更适合作为 EP4 后续研究的先验和风险提示。

### 3.1 Low-Vol / Low-Risk Anomaly

低波 / 低风险异象给出的启发是：

```text
更高波动不必然对应更高风险调整收益；
高波动 / 高 beta / 高 idiosyncratic risk 状态可能反而包含 lottery overpricing 和更重左尾。
```

这支持 EP4 后续优先测试：

```text
low-vol uptrend
low-vol relative strength
moderate volatility breakout
avoid high-vol blowoff / lottery state
```

但这里必须保守。低波异象通常是横截面组合或因子层面结果，不等于某个日级 event pool 在 next-open 后天然正期望。对 EP4 的可用解释只能是：

```text
low-vol 是候选 universe 的先验，
不是 alpha pass 的证据。
```

相关参考：

- [The Volatility Effect in China](https://link.springer.com/article/10.1057/s41260-021-00218-0)
- [Betting Against Beta](https://www.nber.org/papers/w16601)
- [The Volatility Effect Revisited](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3442749_code296465.pdf?abstractid=3442749)

### 3.2 Momentum Crash 与 Market-State Dependence

`Momentum Crashes` 和中国市场 momentum-state 研究共同提示：

```text
momentum / RPS 不应被当成 unconditional entry alpha；
market state 会改变 momentum payoff；
在某些 transition / rebound / high-vol states，momentum 的左尾可能显著恶化。
```

这和 R04 的发现一致：

```text
RPS 有右尾，
但 action-time path 风险重；
market regime 有解释力，
但很多效果来自 background regime 而不是 RPS 增量。
```

因此 market state 在 EP4 里更适合做：

```text
return decomposition
gross exposure overlay
insurance-cost state diagnostic
```

不应直接升级为：

```text
stock-level entry gate
RPS + market + industry high-dimensional AND
```

相关参考：

- [Momentum Crashes](https://www.nber.org/papers/w20439.pdf)
- [Momentum has its moments](https://colab.ws/articles/10.1016/j.jfineco.2014.11.010)
- [Momentum returns, market states, and market dynamics: Is China different?](https://www.sciencedirect.com/science/article/abs/pii/S1059056017302885)

### 3.3 Volatility-Managed Portfolios 的双重启发

Volatility-managed portfolio 文献支持一个方向：

```text
当 realized volatility 高时降低 factor exposure，
有时能改善 Sharpe / utility / drawdown。
```

但后续实证也提醒：

```text
volatility management 的 real-time OOS 表现可能不稳定；
它常常改善 risk-adjusted 结果，不一定改善 absolute profit；
它不能替代底层 factor / pool 的 alpha。
```

对应 EP4：

```text
cash / exposure sleeve 是风险控制和 return decomposition；
不是利润来源。
```

如果 `risk_on full-exposure` 自身不赚钱，volatility / market-state overlay 不允许 pass。

相关参考：

- [Volatility Managed Portfolios](https://www.nber.org/papers/w22208)
- [On the performance of volatility-managed portfolios](https://www.sciencedirect.com/science/article/pii/S0304405X2030132X)

### 3.4 Residual Momentum 与 52-Week High

Raw RPS / raw momentum 的问题是：

```text
它容易混入 market beta、industry beta、high-vol lottery 和 crowded extension。
```

Residual momentum 与 52-week high 文献给出的启发是：

```text
不要只看过去收益排名；
可以尝试更结构化的 momentum proxy：
  residual / idiosyncratic strength
  closeness to 52-week high
  industry-adjusted leadership
  near-high but not extended
```

这支持 EP4 的候选方向：

```text
base breakout / VCP
industry leader but not extended
residual strength after removing market / industry context
```

但这些仍然必须通过 action-time next-open、after-cost、matched comparator 和 validation net > 0 约束。

相关参考：

- [The 52-Week High and Momentum Investing](https://www.bauer.uh.edu/TGeorge/papers/gh4-paper.pdf)
- [Residual Momentum](https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf)
- [Horse race of weekly idiosyncratic momentum strategies: Evidence from China](https://arxiv.org/abs/1910.13115)

### 3.5 Factor Zoo、Trading Costs 与 Overfitting

后续如果进入 R05 alpha discovery，很容易重新掉进 factor zoo：

```text
大量 primitive
大量 threshold
大量窗口
大量组合
最后找到一个 validation 前看起来漂亮的 pool
```

相关文献给出的约束是：

```text
交易成本和 turnover 会显著削弱 anomaly；
高 turnover anomaly 尤其脆弱；
大量搜索必须控制 false discovery / backtest overfitting；
new factor / new pool 必须有更严格的 OOS 和统计门槛。
```

这直接支持 `discussion5` 的 protocol：

```text
capacity / turnover 在 discovery 阶段 binding
train-only discovery
validation freeze
robustness read-only
block bootstrap
mechanical kill criteria
no robustness rescue
```

相关参考：

- [A Taxonomy of Anomalies and their Trading Costs](https://www.nber.org/papers/w20721)
- [Taming the Factor Zoo](https://www.nber.org/papers/w25481)
- [How Backtest Overfitting in Finance Leads to False Discoveries](https://academic.oup.com/jrssig/article/18/6/22/7038278)

---

## 4. 为什么继续找候选池不能沿用旧方法

EP4 之前的很多搜索都容易落入三个陷阱：

```text
1. 用 big-winner coverage 替代 action-time posterior
2. 用 matched delta 替代 absolute expectancy
3. 在同一个 RPS / momentum universe 上反复切 gate
```

R04c 已经说明 R04-derived high-RPS pools 大多是 baseline_A 子集，右尾更肥，但左尾更差。继续在 RPS95 / RPS+money / RPS+industry 这类子集上切，大概率是 diminishing return。

新的 alpha pool search 应优先寻找：

```text
low-overlap new event universe
action-time return distribution cleaner by construction
right-tail still present
left-tail naturally lighter
after-cost validation net positive
```

重点不是更高 `+50 rate`，而是更干净的入场后收益分布。

但这仍然只是待检验假设，不是研究前提。结合 EP4 现有失败结构和文献先验，应该默认：

```text
left-tail naturally lighter long-only alpha pool may be rare or nonexistent
```

因此 R05 的 null hypothesis 应写成：

```text
H0:
  在当前 A-share long-only universe、日频 next-open execution、
  成本、容量、停牌/跌停约束下，
  不存在可复用的 low-left-tail positive-expectancy alpha pool。
```

如果 R05a/R05b 不能拒绝这个 null，不应继续扩大 primitive search，而应把现有信号降级为：

```text
lifecycle tags
relative-improvement sleeves
risk overlays
explanatory diagnostics
```

---

## 5. Alpha Pool 与 Relative Improvement Pool 的定义

### 5.1 Relative Improvement Pool

定义：

```text
matched net delta > 0
p10 delta >= 0
loss delta < 0
but validation net <= 0
```

解释：

```text
它比 matched bad baseline 少亏，
但没有证明自身可承担主仓。
```

用途：

```text
descriptive lead
diversifying sleeve candidate
loss-reduction sleeve
state diagnostic variable
ensemble member with capped allocation
```

禁止：

```text
promote to alpha pool
call it production candidate
use it as main strategy pool
use robustness positive result to reverse validation failure
```

### 5.2 Alpha Pool

定义应更严格：

```text
validation net mean > 0
validation median not materially negative
validation p10 >= matched baseline p10
validation loss<=-5% < matched baseline
after-cost and capacity-adjusted result still passes
robustness direction not reversed
right-tail not fully destroyed
top1 year / industry / instrument not dominant
```

一个 pool 只有在 action-time 后自身 return distribution 通过这些约束，才可以称为 alpha pool。

---

## 6. Alpha Pool Discovery 的推荐方法

### 6.1 先做 Return Decomposition，不先做 Gate Search

每个候选 pool 必须先输出完整分布：

```text
T+1 / T+5 / T+20 / T+60 / T+120 net return
net_return_mean
net_return_median
net_return_p10 / p25 / p75 / p90
loss <= -5%
loss <= -10%
max_drawdown_20 / 60 / 120
max_gain_20 / 60 / 120
max_gain50_rate
right-tail retention
turnover
calendar / industry / instrument concentration
```

如果一个 pool 只有 p90 或 `+50 rate` 很好，但 median、p10、loss rate 很差，它是 right-tail lottery，不是 alpha pool。

### 6.2 使用 Matched Comparator，而不是全市场平均

新 pool discovery 应先冻结统一 comparator spec。

推荐匹配维度：

```text
split
calendar year / quarter
market regime
industry
liquidity bucket
volatility bucket
RPS / momentum context bucket, if relevant
```

目的不是让 comparator 更复杂，而是避免把以下暴露误认成 alpha：

```text
bull year
hot industry
high beta
liquidity regime
volatility regime
recent momentum background
```

R04c/R04e 已经有 matched baseline 思路，但后续 alpha discovery 需要把它上升为统一协议，而不是每个 requirement 临时定义。

### 6.3 Train-Only Discovery + Validation Freeze

生命周期必须固定：

```text
train:
  large primitive / pool search
  select small number of candidates

validation:
  confirm train-selected frozen candidates only
  no threshold adjustment
  no new bucket merge
  no reverse selection

robustness:
  read-only final readout
```

如果 discovery 使用了 all-splits，只能输出：

```text
oos_retest_required
```

不能直接进入 promotion。

### 6.4 每个 Candidate Pool 必须带固定八元组

每个 pool 必须预注册：

```text
1. source rule
2. as-of rule
3. entry rule
4. event collapse rule
5. cost / capacity rule
6. matched comparator rule
7. statistical evidence rule
8. kill criteria
```

其中 `statistical evidence rule` 必须先于 outcome 运行冻结。

这条很关键：`p10 明显改善`、`loss<=-5% 明显下降`、`matched delta > 0` 都不能只靠点估计。它们必须在 train 阶段写成可计算的统计门槛，validation 只负责一次性判定。

---

## 7. 统计显著性与稳健性要求

点估计不够。尤其在按 year / industry / regime / liquidity / volatility 匹配后，样本会迅速变薄，event-level matched delta 的噪声会很大。

建议至少输出：

```text
event bootstrap CI
calendar-day or calendar-month block bootstrap CI
year leave-one-out
industry leave-one-out
instrument concentration stress
```

需要特别注意：

```text
event-level bootstrap 会低估同日/同周市场冲击相关性。
```

因此 block bootstrap 必须成为 primary robustness evidence 之一。

建议 gate 例子：

```text
validation net mean > 0
after-cost net mean block-bootstrap lower bound > 0
p10 delta block-bootstrap lower bound >= 0
loss<=-5 delta block-bootstrap upper bound < 0
year leave-one-out does not flip all positive evidence
industry leave-one-out does not rely on one industry
```

如果样本太薄，导致 CI 无法稳定支持这些判断，则结论不能写成 alpha pass。允许的结论只能是：

```text
insufficient_statistical_power
descriptive_lead_only
oos_retest_required
```

这比放宽门槛更合理。否则按行业 x 年份 x regime 分层后，很容易把 event noise 误读成 pool edge。

---

## 8. As-Of、Look-Ahead 与 A 股结构风险

新候选方向通常会使用：

```text
volatility contraction
base breakout
industry relative strength
market breadth improvement
liquidity dry-to-active
post-capitulation recovery
```

这些 primitive 很容易发生 as-of 漏洞。必须规定：

```text
decision_date = D after close
entry_execution_date = next tradable open after D
all entry features known no later than D close
if entry_date = E open, feature_asof_date <= previous tradable close before E
no same-day close feature for same-day open execution
no future high/low window in base / VCP definition
industry membership asof D
universe membership asof D
```

具体到候选 primitive，容易翻车的地方包括：

```text
volatility contraction:
  contraction window must end before breakout confirmation, or be known by D close

base breakout:
  base high / base low cannot use post-entry bars
  if breakout is confirmed by D close, earliest entry is D+1 open

industry relative strength:
  industry return / ranking must use asof industry membership and D-close-known prices

market breadth improvement:
  breadth signal must be computed from securities tradable and observable as of D

liquidity dry-to-active:
  volume / money expansion cannot use entry-day turnover
```

特别是 `post-capitulation recovery` 在 A 股要谨慎。

风险包括：

```text
停牌
ST / 退市风险
监管事件
流动性塌陷
不可交易跌停
长期 suspended path
```

这类 pool 的 left tail 可能不是一般统计噪声，而是结构性不可恢复风险。matched baseline 和 sample filter 必须显式处理：

```text
survivorship bias
suspension path
limit-down buy/sell feasibility
ST / delisting status asof
liquidity capacity
regulatory event status asof
```

否则 p10 / drawdown 会被严重高估。

这里不能简单删除坏路径后再评估 recovery pool。必须在 train 阶段冻结处理规则：

```text
include suspended / delisted / ST paths if they were tradable candidates asof entry
or explicitly define an asof-executable exclusion rule

never exclude an event because the later path became untradable
never assume exit at a price unavailable under limit-down / suspension constraints
```

---

## 9. Capacity / Turnover 必须在 Discovery 阶段 Binding

成本、turnover 和 capacity 不能只在最后 robustness 里补充说明。它们必须是 discovery 阶段的硬约束。

建议每个候选 pool 必须输出：

```text
daily candidate count
active count p95 / p99
turnover event count
median holding days
position notional vs money percentile
max participation rate assumption
capacity-adjusted slippage stress
```

并冻结约束：

```text
daily candidate count p99 <= pre_registered_cap
active_count_p95 <= pre_registered_cap
per-name participation <= pre_registered_limit
capacity-adjusted return still passes
turnover <= pre_registered_turnover_cap
```

很多窄 pool 在回测里漂亮，是因为默认可以吃掉单票成交额的非平凡比例。这个假设必须在 discovery 阶段就被约束。

因此每个 pool 的 validation result 必须同时报告两个版本：

```text
raw after-cost result
capacity-adjusted after-cost result
```

只要 capacity-adjusted 版本失败，就不能用 raw 版本 claim alpha。

---

## 10. 候选 Alpha Universe 方向

在当前 EP4 语境下，不建议继续优先研究 momentum 强化版。更值得测试的是低 overlap、低左尾的新 universe。

### 10.1 Low-Vol Uptrend Pool

假设：

```text
长期趋势向上
中短期波动收敛
价格不过度远离均线 / ATR
成交保持可执行但不 blowoff
```

目标：

```text
保留部分右尾
天然降低 bad path / early failure
```

### 10.2 Base Breakout / VCP Pool

假设：

```text
突破前存在 volatility contraction
base 内回撤受控
突破当天不过度 extension
volume expansion 温和确认
```

重点是 `breakout before chase`，而不是已经上涨很多后的 RPS / fresh confirmation。

### 10.3 Industry Leader But Not Extended

假设：

```text
行业本身走强
个股相对行业更强
但价格距离 MA / ATR 不极端
```

这里 industry 不是 entry gate，而是 context。必须防止事后题材 / 概念板块 leakage。

### 10.4 Liquidity Dry-to-Active

假设：

```text
从低关注 / 低流动性状态
切换到温和活跃状态
但尚未进入 blowoff
```

这和 R02/R04 的 `volume_money` 不同。后者很多时候已经是 winner 展开后的 participation marker；新方向要寻找的是更早、更温和的 liquidity transition。

### 10.5 Post-Capitulation Recovery

只作为谨慎候选。必须先解决停牌、ST、退市、不可交易跌停等结构风险。

这个方向的核心风险是：左尾不一定是可分散的统计左尾，而可能是结构性不可恢复左尾。比如：

```text
长期停牌后复牌继续下跌
连续跌停无法退出
ST / 退市路径被样本过滤掉
监管处罚导致 liquidity collapse
```

所以 `post-capitulation recovery` 不能和普通 price reversal pool 用同一套轻量 filter。它至少需要：

```text
asof tradability filter
limit-down executable exit model
suspension-aware holding return
delisting / ST path handling
matched baseline with the same structural risk treatment
```

如果这些处理不能落地，这个方向应直接 archive，不应作为第一批 R05b 候选。

---

## 11. 对 EP4 当前路线的直接含义

### 11.1 R04e 可以跑，但应定位为 Closure Test

R04e 仍值得跑完，因为它是对现有 RPS/family relative-improvement route 的组合层终局诊断。

但 R04e 不应被解释为：

```text
new alpha search
R04c pass rewrite
R04d v2
production entry rule
```

如果 R04e 失败，下一步不应继续：

```text
R04d parameter expansion
more CTA / trailing
validation-tuned union weights
more RPS/family slicing
```

### 11.2 Existing R02 Family Pools 应降级

当前 `volume_money / range_breakout / pullback_drawdown` 更适合标记为：

```text
relative_improvement_pool
not_alpha_pool
```

它们可以保留为：

```text
diversifying sleeve candidate
loss-reduction sleeve
state diagnostic variable
ensemble member with capped allocation
```

但不应继续占据主策略 alpha pool 的位置。

### 11.3 下一步更合理的文档

如果 R04e 跑完后仍未形成 portfolio-level positive lead，建议新开：

```text
R05a Alpha Pool Discovery Protocol / Matched Comparator Spec
```

先冻结：

```text
matched comparator
capacity
cost
bootstrap
as-of
kill criteria
promotion language
```

再进入：

```text
R05b Low-Overlap Alpha Pool Discovery V1
```

第一版只测 1 到 2 个候选 universe：

```text
low-vol uptrend
base breakout / VCP
```

不要一次性展开多个主题，否则会重新进入 specification search。

---

## 12. 推荐的 Mechanical Kill Criteria

每个 candidate pool 在 train 阶段冻结后，validation 只能跑一次。

kill criteria 必须是机械规则，不是研究者看完 validation 后的解释框架。每个候选 pool 在进入 validation 前，应写死：

```text
net mean floor
median floor
p10 delta floor
loss-rate delta ceiling
bootstrap CI rule
top1 year / industry / instrument concentration cap
daily candidate / active count cap
participation / capacity cap
turnover cap
```

建议 validation hard fail 条件：

```text
validation net mean <= 0
validation median < pre_registered_floor
validation p10 < matched baseline p10
validation loss<=-5% >= matched baseline
after-cost net mean block-bootstrap lower bound <= 0
p10 delta block-bootstrap lower bound < 0
loss<=-5 delta block-bootstrap upper bound >= 0
right-tail retention below floor
top1 year share above cap
top1 industry share above cap
top1 instrument share above cap
daily candidate p99 above capacity cap
capacity-adjusted net mean <= 0
turnover above pre_registered_cap
```

如果失败：

```text
archive_candidate_pool
no threshold tuning
no validation bucket merge
no robustness rescue
no promote as alpha
no second validation pass with adjusted thresholds
```

允许的输出只有：

```text
relative_improvement_lead
descriptive_lead
archive_no_alpha
oos_retest_required, if discovery used all splits
```

---

## 13. 阶段性结论

EP4 的下一阶段不应继续问：

```text
哪个 RPS / family / fresh / order / bad-shape 条件更强？
```

而应问：

```text
是否存在一个低 overlap 的新 action-time event universe，
其原始 after-cost return distribution 本身足够干净，
可以在 validation 上形成 absolute positive expectancy？
```

如果答案是否定的，那么后续的 cash sleeve、exit insurance、risk budget 都只能降低损失，不能创造主策略利润。

因此当前建议：

```text
1. R04e 跑完，作为 existing route closure。
2. 将 R02 family relative-improvement pools 从 alpha promotion 候选中移除。
3. 新建 R05a，冻结 alpha discovery protocol 和 matched comparator spec。
4. 新建 R05b，只测试 low-vol uptrend 和 base breakout / VCP 这类低 overlap universe。
5. 所有通过语言必须保留 alpha pool 与 relative improvement pool 的区别。
```

一句话：

```text
不要再用更复杂的风控去修一个本身不赚钱的 pool；
先找到 action-time 后原始分布更干净、扣成本后仍为正的新事件 universe。
```
