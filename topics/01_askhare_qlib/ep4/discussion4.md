# EP4 Discussion 4: Dynamic Momentum Exposure Eligibility, Volume-Money Participation, and Volatility-Gated Risk Budget

> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 validation。
>
> 背景：基于 `discussion3.md` 对 R02/R03 的总结、R03a/R03b/R03c/R03d/R03e 的结果，以及论文 *Momentum crashes* 对 momentum regime risk 的解释，讨论是否应停止继续沿着 single entry / anchor / family-order 路线寻找可交易入场点，并转向 RPS / momentum / volume_money / volatility / industry regime 的动态暴露资格框架。CTA 暂时只作为后续 hold / exit / trailing-risk 方向，不在第一阶段混入 entry/exposure eligibility 证明。

---

## 1. 当前判断

我现在倾向于把结论写得更精确：

```text
不是 single family 信息无效，
而是“单一事件信号作为可复用 entry anchor”的路线基本走死了。
```

R02/R03 到目前暴露出的核心问题不是信号完全没有信息，而是：

```text
信号经常能解释后续上冲或 episode 是否已经走强，
但它不能稳定解释从该 signal day / fresh day 重新入场后的剩余收益路径。
```

因此，继续寻找：

```text
最强 single family
最强 same-day bundle
最强 fresh sequence
最强 family order
最强 bad-shape filter
```

大概率会继续落入同一个陷阱：

```text
seed-anchor 看起来改善，
fresh-anchor / action-time entry 仍然 bad-heavy。
```

下一阶段更值得讨论的方向不是再找一个更强的 anchor，而是把 momentum 看成一个 regime-dependent exposure system。

---

## 2. R03 系列结果给出的约束

### 2.1 R03a: survival-step 不是独立 action-time edge

R03a 说明：

```text
T+10 survival 后 P_good 上升、P_bad 下降，
主要来自 bad path denominator 被 survival 条件过滤掉。
```

这不是无价值。它说明 fail-fast / probe lifecycle 是必要的。

但它不能证明：

```text
survival checkpoint 本身产生了新的 big-winner edge；
也不能证明 survival 后应该释放固定 1R sizing。
```

R03a 的最终状态是：

```text
blocked_no_stable_candidate_bucket
```

含义是：在 baseline survival 之上，没有可冻结的稳定 probability bucket。

### 2.2 R03b: fresh-count 是路径确认，不是 entry signal

R03b 发现：

```text
fresh distinct family count 越多，
seed-anchor P_good 越高，P_bad 越低。
```

但 big-winner rate 的提升弱很多，并且 validation 中不稳定。

更关键的是 survival bias：

```text
大量 episode 在等到 first fresh signal 之前已经失败。
```

所以 fresh-count lift 不能简单解释为：

```text
后续信号越多，越值得买。
```

更准确的解释是：

```text
能活到后续 signal 出现的 episode，本身已经经过路径过滤；
fresh signal 越多，越像 episode 已经进入持续活跃 / 持续趋势状态。
```

### 2.3 R03c: seed-anchor strong 不等于 fresh-anchor still attractive

R03c 是很关键的一步，因为它把 seed-anchor 和 fresh-anchor 拆开。

结论很直接：

```text
后续 fresh signal 出现时，价格往往已经上涨；
seed-anchor outcome 随 kth fresh / fresh-count 改善；
但 fresh-anchor 重新计算后的 path 没有同步改善。
```

典型现象：

```text
seed-anchor P_good 很高，
fresh-anchor P_bad 仍然很高。
```

所以：

```text
等更多 fresh signal 再入场
```

这个假设应被否定。fresh accumulation 更像 late confirmation，不是更好的买点。

### 2.4 R03d: stage role 有解释力，family order 没有交易增量

R03d 说明 7 个 family 在 episode lifecycle 里有阶段角色：

```text
range_breakout 更像 probe family；
oscillator / volatility_band / pullback_drawdown 常作为 fresh-stage 信息；
price_trend / momentum_rps 在 late continuation 阶段解释 seed-anchor 状态很强。
```

但 family order 没有在 fresh-anchor 上提供稳定增量：

```text
ordered prefix denominator 稀疏；
pair order signed lift 接近 0；
last-added family 不可用；
same-offset multi-family 很多，严格顺序本身难以观察。
```

因此 family 的阶段角色可以作为 hold-state / risk-state 协变量，但不应写成 entry / add rule。

### 2.5 R03e: bad-shape filter 没有救回 T+10 新开仓

R03e 测试了 family signal 后 T+10 再做坏形态过滤。

结果是：

```text
BadScore >= 5 没有稳定降低 P_bad；
高 BadScore 不是更坏路径；
多个坏形态 component overlap 很高；
很多 component 只是描述高波动 / 高分歧状态。
```

这说明：

```text
在 family signal 后等 10 天，
再用形态过滤去修 action-time quality，
当前版本不成立。
```

这也进一步支持停止“修 anchor”的思路。

---

## 3. 论文 Momentum Crashes 的直接启发

论文 *Momentum crashes* 的核心结论对当前问题很有启发：

```text
momentum 平均收益强，
但 crash state 部分可预测；
crash 常出现在 panic state、市场前期下跌、高波动之后，
并且与市场反弹同时发生。
```

论文里动量不是被当成静态信号，而是被当成一个 conditional payoff。但这里必须先声明迁移边界：

```text
论文研究的是 long winners / short losers 的 WML momentum；
其中 crash 很大部分来自 short-loser leg 在 panic rebound 中被打爆。

当前语境更接近 A-share long-only / stock selection；
不能机械照搬“momentum payoff reverses or crashes”的结论。
```

可以借用的是 regime-conditioning 的方法论，而不是 long-short payoff 的方向性结论：

```text
normal regime:
  momentum expected edge may be stronger

panic / high volatility / market rebound regime:
  static momentum exposure forward edge may deteriorate
  rotation / beta reversal / crowding risk may rise
```

其动态策略思想是：

```text
用 momentum expected return forecast 和 variance forecast
动态调整 WML exposure。
```

转到当前 A-share / long-only 语境，不应机械照搬 long winner / short loser 的 WML 结构，但可以借用最重要的方法论：

```text
RPS / momentum 不能作为静态 entry trigger；
momentum exposure eligibility 必须 condition on market regime、industry regime、volatility state。
```

尤其需要警惕：

```text
市场前期大跌 + 高波动 + 快速反弹
```

这类状态下，静态 RPS 强势股不一定继续强，可能被超跌反弹、beta reversal、风格切换或行业轮动打断。更稳妥的表述不是“动量一定反转”，而是：

```text
momentum exposure 的 forward edge 和 path risk 需要按 regime 重新估计。
```

---

## 4. 新方向：Dynamic Momentum Exposure，而不是 New Anchor

下一阶段可以把研究问题改写为：

```text
是否存在一个 regime-conditioned momentum exposure eligibility system，
在 action-time anchor 下优于 static single-family / fresh-family / family-order anchor？
```

这个系统的组成不是同日 hard AND，而是分工明确的状态机。下表中的 CTA 只作为架构占位，R04 v1 不评估 CTA / trailing exit：

| component | role | 不应做什么 |
|:--|:--|:--|
| market regime | 决定是否允许做 momentum beta | 不应只做简单 bull/bear 标签 |
| industry regime | 判断 momentum 是否有行业 leadership 支撑 | 不应事后用强行业解释个股上涨 |
| RPS / momentum | 负责方向和相对强度排序 | 不应单独作为 entry anchor |
| CTA / trend | 负责后续 R04b 的持有、退出、trailing risk 实验 | R04 v1 不评估 |
| volume_money | 确认资金参与和可交易性 | 不应与 momentum 做 same-day 拥挤 AND |
| volatility | 决定 regime risk、position sizing、stop distance | 不应简单解释为高波动更好 |
| price extension | 避免追在局部过热点 | 不应只作为事后解释变量 |

一句话：

```text
市场/行业决定能不能做 momentum；
RPS 决定候选池；
volume_money 确认资金是否真的参与；
volatility / extension 决定风险预算和是否降权；
CTA 只在后续独立验证中决定持有和退出；
price extension 防止追在 crowded point。
```

---

## 5. 暴露资格的候选状态结构

一个更合理的候选结构不是：

```text
momentum_rps = 1
AND volume_money = 1
AND volatility_band = 1
```

而是：

```text
market_panic_state = false
AND industry_regime = positive
AND stock_relative_momentum = high_or_improving
AND stock_trend_state = constructive
AND volume_money_state = active_but_not_blowoff
AND volatility_state = tradable
AND price_extension_state = not_overextended
```

这里每个字段都应是 action-time as-of 可观察状态，而不是从 future path 回填。它们也不应被解释为多个独立证据相加；第一版应把它们作为分层和 ablation 状态，验证每一层是否改善 action-time forward path。

这里最大的风险是 specification search。R04 立项前必须冻结一份 spec sheet：

```text
field list
lookback window
bucket cutpoints
max bucket count
minimum denominator
primary metric
kill criteria
ablation matrix
```

禁止在看完 outcome 之后再调整 regime 字段、分位断点或 bucket 合并方式。

### 5.1 Market Regime

R04 v1 的 market regime 应先收敛到 minimal feature set，而不是一次性展开所有候选字段。

must-have：

```text
index_120d_return / 252d_return
index drawdown from 120d / 252d high
index realized volatility 20d / 60d / 126d
market rebound state after drawdown
market breadth
```

nice-to-have / later audit：

```text
volatility percentile
limit-up / limit-down breadth
```

初始 regime bucket 可以粗化为：

```text
normal_uptrend
normal_range
panic_high_vol
post_drawdown_rebound
downtrend_low_breadth
```

重点是识别论文里的高危状态：

```text
prior market decline + high volatility + rebound
```

这个 bucket 不能预设为默认降权 gate。论文中的 high-vol rebound 风险来自 long-short WML 的 short-loser leg，A-share long-only 里 post-drawdown rebound 也可能是强 momentum / 龙头股的高收益窗口。

因此 R04 应把它写成待验证假设：

```text
prior market decline + high volatility + rebound
  may reduce momentum edge
  may improve momentum edge
  must be estimated from action-time outcome
```

只有 OOS 结果稳定显示该状态下 primary metric 恶化，才能升级为降权或 block 规则。

### 5.2 Industry Regime

industry regime 用来回答：

```text
个股 RPS 是孤立 spike，
还是行业 leadership 的一部分？
```

候选字段：

```text
industry_RPS_20 / 60 / 120
industry breadth above MA20 / MA60
industry volume_money percentile
industry realized volatility
industry return dispersion
industry leader concentration
stock_RPS_minus_industry_RPS
```

R04 必须冻结行业归属口径：

```text
industry taxonomy = one fixed classification, e.g. Shenwan/CITIC
industry_membership_asof_date <= entry_signal_date
concept / theme boards excluded in v1
```

如果只能拿到静态行业归属，也必须把它标记为 leakage-risk audit，不得把概念板块或事后题材映射写入 v1。

可讨论的 bucket：

```text
industry_leading_low_vol
industry_leading_high_vol
industry_rebound_from_drawdown
industry_lagging_stock_outlier
industry_crowded_blowoff
```

我会特别区分：

```text
行业级趋势延续
vs
行业级超跌反弹
vs
个股孤立放量强势
```

这三类的 momentum payoff 应该完全不同。

### 5.3 Stock Momentum / RPS

RPS 不应只用一个 horizon。

建议拆成：

```text
short RPS: 20d / 30d
medium RPS: 60d / 120d
long context: 250d
RPS slope / improvement
RPS consistency
stock RPS relative to industry
```

核心不是绝对强，而是：

```text
强势是否持续；
强势是否刚从行业 leadership 中冒出来；
强势是否已经进入过热段。
```

初始假设：

```text
medium RPS high + short RPS improving
优于 short RPS extreme one-day spike。
```

### 5.4 Volume Money

volume_money 的角色应从 entry trigger 改成 participation confirmation。

需要避免：

```text
volume_money 极端放大 + momentum 极端强
```

因为 R02/R03 已经显示，同日多 family 共振容易筛出短期拥挤状态。

候选字段：

```text
amount percentile vs own 252d history
amount percentile vs industry peers
turnover percentile
amount / free_float_mcap
volume expansion persistence
volume spike reversal
up-volume vs down-volume
```

R04 v1 不建议把 volume_money 放进 primary gate。它应先作为 descriptive / R04 v2 candidate，避免和 RPS / extension 同时进入后形成高维 AND。

更合理的状态不是越大越好，而是：

```text
active_liquidity:
  资金参与增强，且价格不过度延展

blowoff_liquidity:
  资金极端拥挤，价格已经远离均线 / ATR band

dry_liquidity:
  RPS 强但成交额不支持可执行性
```

### 5.5 Volatility / Extension

volatility 要分两层：

```text
market / industry volatility:
  regime risk

stock volatility / ATR:
  execution risk、stop distance、sizing
```

候选字段：

```text
ATR20_pct
realized_vol_20 / 60
volatility percentile
volatility expansion ratio
price distance from MA20 / MA60
price distance in ATR units
gap risk proxy
intraday range percentile
```

初始假设：

```text
RPS high 但 extension 太高 -> late crowded exposure risk
RPS high 但 volatility expansion too extreme -> reduce or block
RPS high + moderate vol + constructive industry -> potentially better action-time forward path
```

volume_money blowoff、short-RPS extreme、price extension、volatility expansion 可能高度共线。R04 v2 若引入这些字段，必须先输出相关性 / overlap audit：

```text
pairwise phi / jaccard among negative gates
denominator shrink by each gate
incremental drop contribution under fixed parent
winner retention by gate and by overlap cluster
```

否则同一个“已经很热”的现象会被多个 gate 重复惩罚，导致 denominator 被过度压缩。

---

## 6. 为什么不能重回 Same-Day Composite

这个新方向最容易犯的错误是把它写成：

```text
RPS + volume_money + volatility + industry regime 同日共振 entry / exposure
```

这会直接回到 R02/R03 已经否定过的结构。

需要避免两个问题：

### 6.1 相关证据重复计数

RPS、price trend、range breakout、volume_money、volatility expansion 往往不是独立证据。

同日一起出现时，它们可能共同指向：

```text
已经很热；
已经被资金推了一段；
next-open 位置偏差；
短期拥挤。
```

所以同日组合不能释放多份 risk budget。

### 6.2 Late Confirmation 被误当成 Action-Time Edge

R03c/R03d 已经证明：

```text
seed-anchor strong
!= fresh-anchor still attractive
```

因此新框架必须从一开始就规定：

```text
所有 exposure / entry 结论使用 action-time / next-open anchor；
所有 seed-anchor improvement 只能作为状态解释；
不能用 seed-anchor P_good 替代 action-time edge。
```

---

## 7. R04 Non-Negotiables

如果这条路线进入 requirement，以下约束必须作为硬约束，而不是建议。

### 7.1 Anchor 与 As-Of

R04 不能再混用 seed-anchor / fresh-anchor。

应固定：

```text
entry_signal_date = action-time signal date
entry_execution_date = next tradable open
entry_price = next-open executable price
forward path = from entry_execution_date
```

所有 regime / RPS / volume / volatility / industry 字段必须满足：

```text
feature_asof_date <= entry_signal_date
```

### 7.2 Anti-Patterns

R04 必须显式禁止以下解释：

```text
same-day multi-signal AND as independent evidence
seed-anchor P_good as action-time edge
fresh-count lift as "wait for more signals then buy"
denominator shrink as posterior improvement
exit / trailing-stop improvement as exposure eligibility improvement
```

### 7.3 Pre-Registered Spec Sheet

R04 在跑 outcome 前必须冻结一份 spec sheet：

```text
feature_name
feature_asof_rule
lookback_window
bucket_cutpoints
bucket_count_cap
missing_value_policy
minimum_train_denominator
minimum_validation_denominator
minimum_robustness_denominator
primary_metric
secondary_metrics
kill_criteria
ablation_matrix
```

任何跑完 outcome 后新增字段、改断点、合并 bucket 的行为，都只能进入下一版 requirement，不能回填当前 R04。

---

## 8. 下一版 Requirement 的建议形态

如果继续推进，我建议不要写成：

```text
R04: better entry signal search
```

而写成：

```text
R04: Dynamic Momentum Exposure Eligibility Audit
```

目标不是找一个单点 entry，而是验证 market / industry / volume / volatility 条件化之后，momentum exposure 是否仍有 action-time forward edge。这里的 entry price 只是统一观测路径的执行锚点，不是新的 anchor-hunt。

### 8.1 Baseline / Ablation

R04 v1 应先缩小范围，只验证 RPS + market + industry 三层，避免一上来进入六维 specification search。

```text
baseline_A:
  RPS candidate pool only

baseline_B:
  RPS + market regime eligibility

baseline_C:
  RPS + market regime eligibility + industry regime
```

volume_money、volatility / extension、risk-budget cap 延后到 R04 v2，只有在 R04 v1 证明 market / industry conditioning 有 OOS 增量后再进入：

```text
baseline_D:
  RPS + market regime + industry regime + volume_money state

baseline_E:
  RPS + market regime + industry regime + volume_money state + volatility/extension eligibility

baseline_F:
  baseline_E + volatility risk-budget cap
```

CTA / trailing exit 不属于 R04 exposure eligibility：

```text
R04b_hold_exit_only:
  selected R04 candidate pool + CTA trailing exit
  evaluated separately with fixed entry/exposure eligibility
```

每一层都必须回答：

```text
是否在 validation / robustness 中改善 action-time outcome？
是否降低 bad path？
是否保留 enough big-winner capture？
是否只是减少 denominator 后造成表面比例改善？
是否把 exit / trailing-stop 改善误算成 exposure eligibility 改善？
```

### 8.2 Negative Ablation

Nested baseline 只能回答“加一层是否变好”，不能回答共线性和虚假增量。因此 R04 v1 至少应补两组 negative ablation：

```text
single_component:
  RPS only
  market only
  industry only

leave_one_out:
  RPS + market + industry
  minus market
  minus industry
```

R04 v2 若加入 volume / volatility / extension，还必须加入：

```text
minus volume_money
minus volatility
minus extension
overlap-adjusted gate contribution
```

这组结果用于回答：

```text
market regime 是否真的有增量？
industry regime 是否只是替代 RPS？
volatility / extension 是否只是重复惩罚 short-RPS extreme？
```

### 8.3 Outcome Hierarchy

不能只看一个 winner rate，也不能在多个指标里事后挑一个汇报。

primary metric 必须预注册：

```text
primary_metric:
  EV_R if EV_R inputs are materialized
  else +10_before_-5_rate with P_bad constraint
```

如果 EV_R 仍不可用，probability-only 版本必须把 `+10_before_-5_rate` 当主指标，同时用以下硬约束防止只筛出高尾部但坏路径更重的 bucket：

```text
P_bad must not increase vs parent
big_winner_retention must not fall below threshold
denominator shrink must be reported
```

secondary / diagnostic metrics：

```text
big_winner_forward_h120_close_anchor
good_path
bad_path
+10 before -5
early_failure
max_drawdown_20 / 60 / 120
max_gain_20 / 60 / 120
T20 / T60 / T120 median return
EV_R if risk inputs available
```

特别是：

```text
big winner raw rate 不能单独筛选；
必须同时看 path-risk-adjusted outcome。
```

R03d 已经出现过局部 big-winner delta 为正但 path-edge 更差的情况，这个坑必须写进 requirement。

CTA / trailing exit 若进入后续 R04b，应使用同一候选池另跑 hold / exit ablation，不能和 R04 exposure eligibility 的结论合并。

### 8.4 Split Stability

候选 bucket 必须满足：

```text
train denominator sufficient
validation denominator sufficient
robustness denominator sufficient
direction consistent
not dominated by one year / one industry / one instrument
not purely denominator shrink
```

尤其要对 2025 这类明显更好的年份单独审计，避免 pooled result 被最近年份 regime 拉动。

### 8.5 Stopping Rule

R04 必须有 kill criteria，避免研究方向无限延长。

具体阈值应写入 spec sheet。讨论层面的建议是：

```text
if baseline_C vs baseline_A:
  OOS primary_metric lift < pre_registered_min_lift
  OR P_bad increases materially
  OR big_winner_retention falls below pre_registered_floor
  OR improvement is mostly denominator shrink

then:
  stop exposure eligibility route
  do not proceed to volume_money / volatility v2
  move research budget to R04b hold/exit-only or risk-budget diagnostics
```

如果要给一个起步门槛，R04 可以要求：

```text
validation and robustness both improve primary metric directionally
pooled OOS lift exceeds a fixed minimum effect size
big-winner retention remains above a fixed floor
no single year / industry dominates the lift
```

这些数字不应在 discussion 中临时决定，应由 R04 spec sheet 在运行前冻结。

---

## 9. 预期可能出现的结果

我现在的先验不是“这个方向一定能成”，而是：

```text
它比 single entry / anchor / family-order 更符合目前证据。
```

可能出现三类结果。

### 9.1 最好结果

```text
market regime + industry regime 显著降低 high-risk momentum exposure state；
volume_money 只在非 blowoff 状态下改善 action-time forward path；
volatility/extension gate 降低 early failure；
volatility risk-budget cap 改善 path-risk-adjusted outcome；
最终 action-time EV_R 或 path-adjusted edge 通过 OOS；
CTA exit 在独立 R04b 中继续改善 payoff distribution。
```

这会支持一个真正的 dynamic momentum framework。

### 9.2 中性结果

```text
market/industry regime 有解释力，
但 action-time forward path 仍不足；
volume_money 和 volatility 主要用于 sizing / risk monitor；
CTA exit 可能比 exposure eligibility gate 更重要。
```

这时可以把研究转向 holding / exit / risk-budget，而不是继续优化 action-time eligibility。

### 9.3 负面结果

```text
所有 regime-conditioned momentum exposure 仍然 bad-heavy；
improvement 主要来自 denominator shrink；
big-winner retention 不够；
OOS 不稳定。
```

这会说明 EP4 当前特征族不适合做新开仓策略，只能作为持仓状态、风控或解释变量。

---

## 10. 当前我的工作假设

当前最值得验证的工作假设是：

```text
RPS / momentum 是方向选择器，不是 entry trigger；
volume_money 是 participation confirmation，不是 alpha multiplier；
volatility 是 regime risk 和 sizing input，不是简单 filter；
industry regime 是区分 leadership 与 isolated spike 的关键 context；
CTA 是持有和退出框架，应在 exposure eligibility 之后单独验证。
```

因此，新路线应避免：

```text
single-family full entry
same-day multi-signal full entry
fresh-signal re-entry
family-order add
late bad-shape repair
```

更合理的结构是：

```text
small or moderate momentum exposure only when:
  market regime allows momentum
  industry leadership is present
  stock RPS is strong but not exhausted
  volume_money confirms participation but not blowoff
  volatility / extension keeps risk tradable

then:
  risk budget scales with forecast volatility and path survival
  CTA / trailing risk manages continuation in a separate hold/exit layer
```

一句话总结：

```text
下一阶段不应继续问“哪个 anchor 最强”，
而应问“在什么 regime 下，momentum exposure 才值得承担风险”。
```
