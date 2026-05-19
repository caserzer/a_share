# EP4 Discussion 5: Alpha Pool Discovery, Relative-Improvement Pools, and Sleeve Allocation

> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 validation。
>
> 背景：基于 `discussion4.md`、R04/R04b/R04c/R04d/R04e 的结论，以及 R05 Preflight 对 standalone alpha discovery 的前置否决，重新界定 EP4 后续研究方向。当前核心问题已经从“继续寻找真正有 alpha 的新事件 universe”转为“现有 relative-improvement pools 是否只能作为 sleeve 被有限配置”。

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

R05 Preflight 已经把这个判断推进了一步：换成新的 fixed primitive 后，validation floor 仍然没有成立。

```text
R05 Preflight final_decision = r05_preflight_stop_no_absolute_floor
candidate_pass_count = 0
allowed_next_requirement = sleeve_allocator_direction_requirement
```

三个 preflight candidate 的 validation 结果是：

| candidate | validation events | complete share | hold20 net mean | median | p10 | gate |
|---|---:|---:|---:|---:|---:|---|
| low_vol_uptrend | 574 | 96.86% | -0.72% | -1.36% | -9.46% | no absolute floor |
| base_breakout_vcp | 73 | 95.89% | +1.00% | -1.47% | -7.61% | insufficient sample |
| cross_sectional_low_beta_low_vol | 810 | 96.05% | -1.52% | -1.83% | -9.24% | no absolute floor |

因此 `requirement_05a_alpha_pool_discovery_protocol_v1.md` 不再是 active next step。它应标记为 abandoned / preflight-blocked，作为一份被前置实验否决的完整协议草案保留，不再默认执行。

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

### 2.3 Market State Classifier 冻结要求

`risk_on / risk_neutral / risk_off` 不能在 validation 上调参。任何 sleeve allocator requirement 启动前，market state classifier 必须先满足：

```text
state classifier fit source = train split only
state thresholds frozen before validation
state count <= 3
state data source = index-level as-of data only
candidate pool outcome must not define market state
state signal date = D close
exposure adjustment date = D+1 open
validation cannot adjust thresholds, labels, or transition rules
```

这条约束是为了避免 cash sleeve 变成新的 free-parameter search。只要 market state 可以在 validation 上微调，sleeve allocator 就会退化成另一种 validation mining。

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

R05 Preflight 已经没有拒绝这个 null，因此不应继续扩大 primitive search，而应把现有信号降级为：

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

### 6.0 当前状态说明

§6 到 §10 以及 §12 描述的是一套严谨 alpha pool discovery protocol 的参考框架。根据 §11.3，当前 R05 Preflight 没有通过，R05a 已被 abandoned / preflight-blocked，因此这些章节不是 active next requirement。

这些内容只作为 future reference 保留：

```text
only if a future preflight genuinely passes,
then reuse §§6-10 and §12 as protocol reference;
current next requirement = sleeve allocator / exposure composition diagnostic
```

任何后续 requirement 不能引用本节作为重新启动 primitive search 的理由。

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

### 10.0 当前状态说明

本节最初列出的是 R05 alpha discovery 的候选 universe 目录。R05 Preflight 后，其中三类已经有实证结论：

```text
low_vol_uptrend: validation mean = -0.72%, median = -1.36%, p10 = -9.46%
base_breakout_vcp: validation mean = +1.00%, event_count = 73, median = -1.47%
cross_sectional_low_beta_low_vol: validation mean = -1.52%, median = -1.83%, p10 = -9.24%
```

因此本节只作为 historical research record 保留，不是 active R05b candidate list。剩余未跑方向也不会因为 R05 Preflight 失败而自动升级；若未来有人重启 alpha discovery，必须先重新论证 state-type vs sparse-event 区分，并通过新的 preflight，而不是直接从本目录挑选下一个 primitive。

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

### 11.3 R05 Preflight 后的更新结论

R05 Preflight 已经按低成本前置门跑完，结果没有允许 R05a full protocol 继续：

```text
validation_status = passed
final_decision = r05_preflight_stop_no_absolute_floor
candidate_pass_count = 0
```

这改变了本讨论早期对下一份 requirement 的排序。`R05a Alpha Pool Discovery Protocol / Matched Comparator Spec` 已经不应继续作为 active execution plan；它只能作为 abandoned protocol draft 保留。

原因很直接：

1. `low_vol_uptrend` validation 样本足够，但 hold20 net mean = -0.72%，median = -1.36%。
2. `cross_sectional_low_beta_low_vol` validation 样本足够，但 hold20 net mean = -1.52%，median = -1.83%。
3. `base_breakout_vcp` validation mean = +1.00%，但只有 73 个事件，且 median = -1.47%，不能支撑 full protocol。
4. 三个 candidate 的 execution complete share 都超过 95%，所以失败不是执行不可得，而是 validation floor 不成立。

这里 73 个 `base_breakout_vcp` 事件不应被解释成“等样本攒够或放宽阈值再试”。在 A 股 mcap500 mainboard 的两年 validation 中，这更像该 primitive 的真实稀疏事件率。若为了凑样本放宽阈值，VCP 容易退化成 `low_vol_uptrend` 类状态信号，失去 sparse-event 特征。

因此 `base_breakout_vcp` 不应作为下一轮 alpha discovery 主线。它最多可以在 sleeve allocator 中作为 conditional secondary sleeve 被受限评估，且不能承担 standalone alpha gate。

因此下一步不应再写 R05b/R05c 继续换 primitive，而应把研究对象从 standalone alpha pool 改为 sleeve allocation。

### 11.4 Sleeve Allocator 应该问什么

Sleeve allocator 的对象不是单个 entry primitive，而是组合里的子组合权重。它承认现有 pool 不是 standalone alpha，但仍可能在某些 market state 下有相对可用的风险收益形状。

推荐把下一份 requirement 命名为：

```text
R05b Sleeve Allocator / Exposure Composition Diagnostic V1
```

它应把已有对象拆成 sleeves：

| role | sleeve | source artifact / rule | allocation status |
|---|---|---|---|
| primary sleeve | R04e union pool | `ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/cache/r04e_union_event_panel.parquet` and `r04e_portfolio_daily_return_panel.parquet` | eligible for allocation |
| conditional secondary sleeve | base_breakout_vcp | `ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/cache/r05_preflight_candidate_event_panel.parquet`, filtered to `base_breakout_vcp_preflight` | capped, secondary only |
| diagnostic sleeve | low_vol_uptrend | R05 preflight event/return panels | decomposition only, no direct allocation |
| diagnostic sleeve | cross_sectional_low_beta_low_vol | R05 preflight event/return panels | decomposition only, no direct allocation |
| cash sleeve | cash / zero exposure | fixed gross exposure set `{0.0, 0.5, 1.0}` driven by frozen market state | eligible for allocation |
| benchmark sleeve | benchmark / defensive baseline | reporting baseline only unless a separate data contract permits actual holding | no allocation in v1 |

allocator 要回答的问题是：

```text
在不把任何 sleeve 重新解释为 alpha source 的前提下，
能否通过 market-state / exposure / inventory 分配，
把 validation portfolio-level return 和 tail risk 改善到可解释水平？
```

它必须避免两个误区：

```text
1. mostly-cash illusion:
   大部分时间空仓导致回撤降低，但没有真实风险资产收益能力。

2. alpha relabeling:
   exposure overlay 改善组合路径后，把底层 failed pool 改写成 alpha pool。
```

更合理的 hard gate 应该是：

```text
risk_on full-exposure sleeve return must be reported separately
overall allocator validation period return must be positive
monthly p10 and max drawdown must improve vs full-exposure baseline
average gross exposure must not be trivially low
positive result cannot come solely from being mostly cash
robustness must not destroy right-tail participation
```

这条线的目标不是证明“新的 entry alpha 存在”，而是判断现有 relative-improvement pools 是否还有组合层使用价值。

---

## 12. 推荐的 Mechanical Kill Criteria

本节是 alpha discovery 的 archived protocol reference，不是当前 active R05b sleeve allocator gate。R05b 应继承这里的术语纪律和 no-validation-mining 原则，但它的主 gate 应围绕 exposure allocation、mostly-cash illusion、risk-on full-exposure return 和 sleeve role freeze 重新定义。

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

## 13. 阶段性结论

EP4 的下一阶段不应继续问：

```text
哪个 RPS / family / fresh / order / bad-shape 条件更强？
```

而应问：

```text
在 standalone alpha pool discovery 被 R05 Preflight 否决后，
现有 relative-improvement pools 是否还能作为 sleeves，
通过 market-state / exposure / inventory allocation
形成可解释的组合层改善？
```

R05 Preflight 已经给出当前 alpha-discovery 方向的前置答案：

```text
low_vol_uptrend: validation net mean < 0
cross_sectional_low_beta_low_vol: validation net mean < 0
base_breakout_vcp: validation sample insufficient
```

这意味着 R05a full protocol 不应继续执行。后续的 cash sleeve、exit insurance、risk budget 仍然不能创造底层 alpha，但可以作为组合层 allocator 诊断，判断现有 pool 是否还有 limited sleeve value。

因此当前建议：

```text
1. R04e 保持 existing route closure。
2. R05 Preflight 作为 alpha-discovery 前置门，结论为 stop_no_absolute_floor。
3. 将 R05a 标记为 abandoned / preflight-blocked，不再执行 full protocol。
4. 将 R02/R04/R04e 相关 pools 降级为 relative-improvement sleeves / diagnostics。
5. 下一份 active requirement 转向 `ep4/requirement_05b_sleeve_allocator_exposure_composition_diagnostic_v1.md`。
6. 所有通过语言必须保留 alpha pool、relative-improvement pool、risk-control sleeve 三者的区别。
```

### 13.1 Terminal Stop / EP5 Escape Hatch

如果下一份 sleeve allocator requirement 也失败，EP4 应终止，而不是继续派生 `sleeve v2 / sleeve v3 / sleeve + exit insurance / sleeve + regime overlay`。

建议 terminal rule 写成：

```text
if R05b sleeve allocator fails validation under:
  non-trivial average gross exposure
  risk_on full-exposure positive return requirement
  positive overall allocator validation return
  monthly p10 and max drawdown improvement
  no mostly-cash illusion
  no alpha relabeling
then:
  terminate EP4
  do not create R05c/R05d sleeve variants
```

如果还要继续研究，应新开 EP5，并改变问题维度：

```text
new universe
new horizon
hedged or market-neutral leg
different execution model
different portfolio objective
different problem framing
```

这比在 EP4 内继续叠加 overlay 更诚实。当前证据已经连续显示：在 long-only mcap500 mainboard、2022-2023 validation、next-open execution、after-cost 约束下，standalone candidate pool 很可能不存在稳定正期望。

一句话：

```text
不要再用更复杂的 alpha protocol 去证明一个 preflight 已否决的 primitive；
下一步应研究现有 failed/relative pools 是否只能作为组合 sleeve 被有限使用。
```
