# EP4 discussion：右尾 Episode 管理系统

> 生成日期：2026-05-11
> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 P1 validation。
> 与 EP2 / EP3 的关系：EP4 不是继续调 EP2 entry，也不是继续修 EP3 A/C anchor。EP4 是在 EP2 / EP3 失败边界之后，对研究问题本身的重定义。

---

## 0. TL;DR

EP2 和 EP3 共同说明了一件事：

```text
继续问“今天能不能预测未来 120 天涨 50%”会把 entry、holding、exit、position sizing 和 winner capture 混成一个问题。
这个问题在早期信息结构下过难，也容易把研究带回低信噪比的终局预测。
```

EP4 应该把研究问题改成：

```text
如何在高召回地捕获潜在大涨 episode 的前提下，
通过小风险探针仓、早期失败识别、证据累积加仓和状态化动态退出，
实现右尾收益捕获，并控制大量失败样本的试错成本？
```

核心原则：

```text
早期信号只负责发现可能性；
小仓位负责买观察权；
失败识别负责降低试错成本；
证据累积负责加仓；
动态退出负责保留右尾。
```

EP4 的方向不是“更复杂的 entry 模型”，而是：

```text
Big Winner Episode Management System
```

系统每天只回答三个问题：

```text
1. 这个 episode 是否已经失败？
2. 如果没有失败，证据是否增强？
3. 如果证据增强，是否值得投入更多风险预算？
```

---

## 1. EP2 背景：短周期 exposure timing 成立，但 long-horizon holding 不成立

EP2 的正向发现是明确的。

从 `EP2_LAUNCH_DETECTOR_V0` 开始，EP2 冻结了一个可复现的 launch observation pool：

```text
60 trading-day price breakout
+ 20 trading-day money surge
+ PIT universe membership
+ signal_date 可见数据
+ next-open execution
```

R01 证明短周期 confirm-validity label 可以作为 exposure timing 标签：

```text
confirm_h10_u10_d06_conservative_fail
```

R02 进一步证明，在 frozen launch pool 内，可以用 hazard timing 选择更少、更好的 probe day。R03 再加入 deterministic confirm_add，形成：

```text
broad launch detector
  -> valid probe window filter
    -> short-horizon hazard probe selector
      -> bounded confirm_add continuation check
        -> H10 natural exit / 6% fast-fail
```

这个结构的实际意义是：

```text
EP2 证明了 launch 后存在低频、next-open 可执行、短周期可验证的 exposure timing alpha。
```

但 R04 / R05 暴露了更关键的边界：

```text
R03 entry 能找到短周期 probe / confirm-add 机会；
但它没有证明这些 confirm-add episode 已经属于 long-horizon winner holding pool。
```

R05-pre 中，三条 deterministic holding / exit policy 都把 validation strict big-winner capture 从 `2` 提高到 `5`，但同时带来：

```text
p05 return 恶化约 1.6-1.9 pct；
capital occupancy 上升到 2.56-3.32 倍；
trailing / partial exit 的 exposure-day multiple 超过 3.0；
Track A / Track B / matched-random p95 全部失败。
```

这说明问题不是简单的：

```text
exit rule 太粗糙。
```

更准确的解释是：

```text
当前 R03 confirm-add episode pool 中，
值得继续投入风险预算的 episode 与延长后会带来尾部损失的 episode 没有被分开。
```

因此，EP2 的教训不是“继续优化 entry precision”，而是：

```text
entry 只证明短周期 exposure timing；
右尾收益需要后续状态迁移、仓位管理和动态退出共同完成。
```

---

## 2. EP3 背景：winner formation anchor 没有形成稳定 forward lift

EP3 是对 EP2 的一次更激进换题：

```text
不再问 R03 confirm-add 后怎么多拿几天，
而是问真正大 winner 在启动前、启动初期、加速前，
有没有稳定、可观察、可执行的 lifecycle anchor。
```

EP3 P0 先做两个 primary anchor family：

```text
A. pullback_hold_restrengthen
C. second_breakout
```

P0 的结果说明：

```text
winner lifecycle 中确实能看到类似 anchor；
但这些 anchor 转成可执行 forward-audit event 后，
没有稳定跑赢 matched-delay baseline。
```

P0.5 diagnostic 进一步说明，A/C 的失败不是简单的公式太窄、窗口位置不对或 EP2 reference 污染：

```text
h1_formula_too_narrow: rejected
h2_window_position_problem: rejected
h3_ep2_reference_pollution: rejected
h4_matched_baseline_too_strong_or_anchor_no_lift: supported
h5_tail_risk_not_trigger_rate_is_core_failure: supported
```

P0.5 因此对两个 family 都给出：

```text
stop_current_family
```

Deferred-family audit 尝试把 A/C-like 失败状态与后续 observable recovery 区分出来，但最终仍然停止：

```text
recommended_decision = stop_deferred_family
validation trigger rate = 18.47%
validation mean diff vs matched-delay = -2.06%
robustness mean diff vs matched-delay = -1.13%
robustness p05 diff vs matched-delay = -2.46%
```

Rolling continuation / risk-state audit 也没有形成可推广动作：

```text
recommended_decision = stop_rolling_continuation_risk_state
passed_action_count = 0
```

EP3 的教训是：

```text
把 winner formation anchor 当作新的 entry source，仍然容易陷入“找一个更准入口”的问题。
形态 recall 不等于 forward lift；
trigger rate 不等于 payoff edge；
matched baseline 和 tail risk 会把很多看似合理的 anchor 打回原形。
```

因此，EP4 不应继续沿着 “再找一个更好的 anchor / filter / primitive” 前进。

---

## 3. 核心重定义：不是预测大牛股，而是经营右尾期权

原始问题是：

```text
今天能不能预测未来 120 天涨 50%？
```

这个问题天然困难，因为早期信息不足。更合理的问题是：

```text
今天这个结构是否值得用小风险买入一个观察权？
未来 5 / 10 / 20 / 40 / 60 天新增的信息，是否支持继续投入风险预算？
```

第一天不是为了重仓下注大牛股，而是为了买一个便宜的观察权。

这个系统真正赚的钱来自：

```text
大量小亏损
+ 一批小盈利 / 中盈利
+ 极少数大盈利
```

而不是来自高胜率，也不是来自 entry AUC。趋势 / 动量类系统通常依赖正偏 payoff distribution：大部分 trial 不重要，少数右尾决定总收益。

所以 EP4 的目标应该是：

```text
给不确定性定价，而不是试图在 entry 时点消灭不确定性。
```

---

## 4. 系统拆分：五个模块，五个目标

EP4 不应再把所有任务塞进一个 entry model。系统应拆成五个模块：

```text
Seed Generator
  -> Probe Position
    -> Early Failure Detector
      -> Continuation / Conviction Model
        -> Dynamic Exit & Position Sizing
```

| 模块 | 目标 | 错误做法 |
|:--|:--|:--|
| Seed Generator | 高召回地找到可能启动的股票 | 追求高 AUC、高 precision |
| Probe Position | 用小风险获得观察权 | 一开始就重仓 |
| Early Failure Detector | 快速证伪失败启动 | 用它预测 +50% |
| Continuation / Conviction Model | 判断是否值得继续投入风险 | 固定 H20 / H60 / H120 |
| Dynamic Exit & Position Sizing | 保护趋势生命力并控制风险预算 | 只用机械止盈止损 |

关键规则：

```text
不同模块不能共用一个 label。
```

EP2 / EP3 的很多问题，本质上来自把以下问题混在一个 entry / anchor 里：

```text
是否值得试探？
是否已经失败？
是否值得加仓？
是否进入右尾发展？
是否应该退出？
```

EP4 必须把这些问题拆开。

---

## 5. Entry 层应该宽，风险和退出层应该严

Entry 层只做三件事：

```text
1. 它是不是有启动结构？
2. 它是不是可以交易？
3. 它是不是值得一个很小的 probe position？
```

不要让 entry 层判断：

```text
它是不是 120 天后会涨 50%？
```

因为这个问题早期基本不可稳定回答。

### 5.1 硬过滤：只过滤不可交易样本

硬过滤可以直接剔除：

| 硬过滤 | 作用 |
|:--|:--|
| 流动性太差 | 防止无法成交 |
| ST / 退市风险 | 防止制度性风险 |
| 停牌、重大异常数据 | 防止脏样本 |
| 涨停无法买入 | 防止回测虚假成交 |
| 极端一字板连续拉升后 | 防止无法真实进入 |

### 5.2 软过滤：不剔除，只调低仓位或提高确认门槛

| 软风险 | 不建议做法 | 建议做法 |
|:--|:--|:--|
| 波动过大 | 不买 | 降低仓位 |
| 行业弱 | 不买 | 降低初始风险预算 |
| 市场环境差 | 不买 | 降低组合总 risk budget |
| 拥挤度高 | 不买 | 收紧止损 / 限制加仓 |
| 基本面差 | 不买 | 降低最大持仓上限 |
| 短期涨幅过高 | 不买 | 延后加仓 / 提高确认门槛 |

核心规则：

```text
entry 层尽量保留右尾种子；
risk 层负责控制亏损和仓位；
exit 层负责证伪和保护利润。
```

---

## 6. 从 winner / loser 改成状态迁移问题

EP4 不应只把 episode 分成：

```text
winner / loser
```

而应定义状态机：

```text
S0: Candidate 候选结构
S1: Probe 探针仓
S2: Early Fail 早期失败
S3: Survived 未失败但未确认
S4: Confirmed Continuation 趋势确认
S5: Big Winner Development 主升浪发展
S6: Exhaustion / Distribution 衰竭或派发
S7: Exit 退出
```

模型不是预测：

```text
S0 -> S5
```

而是逐步判断：

```text
S1 是否应该进入 S2？
S3 是否应该进入 S4？
S4 是否应该加仓？
S5 是否仍值得持有？
S6 是否应该减仓或退出？
```

这会比直接预测 `+50% / 120d` 更稳定，因为每一步的 label、feature、action 和风险预算都更接近当时可见信息。

---

## 7. Label 重新设计：至少五组 label

EP4 不应只有一个 `future_50h120` 标签。至少需要五组 label。

### 7.1 Label A：Seed Quality Label

目的：

```text
判断 seed signal 是否有短期交易价值。
```

建议使用 triple-barrier 风格标签：

```text
entry 后 10 / 20 日内：
是否先触发 upper barrier，而不是先触发 lower barrier？

upper barrier = +1.5ATR 或 +2ATR
lower barrier = -1ATR
vertical barrier = 10 / 20 trading days
```

这个 label 用于评价 seed 的短期可交易性，不用于判断它是否会成为 big winner。

它和 EP2 R01 的关系必须单独说明。EP2 已经冻结过一个固定百分比版本的 confirm-validity label：

```text
confirm_h10_u10_d06_conservative_fail
```

EP4 的 Label A 不应该在 R01 中直接无解释地替换这个口径。更合理的讨论定位是：

```text
EP2 fixed-percent label = 既有 reference / bridge anchor；
EP4 ATR-normalized triple-barrier = 后续 normalization candidate；
R01 至少要能同时报告二者的 bridge audit，不能因为 label 口径变化而失去和 EP2 baseline 的可比性。
```

也就是说，Label A 可以是 EP4 长期更自然的 seed quality label，但 R01 不应把 label 切换本身也变成新的自由度。

### 7.2 Label B：Early Failure Label

目的：

```text
训练 fail-fast 模型。
```

入场后 5 / 10 / 20 日内是否出现结构性失败：

```text
跌回突破区间
跌破启动日低点
跌破 EMA20 / EMA30
相对强度明显回落
行业共振消失
放量长阴吞没
```

这个模型只回答：

```text
这个 episode 是不是已经不值得继续观察？
```

### 7.3 Label C：Continuation Label

目的：

```text
判断是否从 probe position 升级成正式仓位。
```

入场后 20 / 40 日内是否形成 continuation：

```text
价格没有回到突破区下方
高点和低点逐步抬升
相对强度继续提升
成交额没有明显萎缩
行业内更多股票同步走强
```

这个 label 比 `future_50h120` 更早、更接近当时可见信息。

### 7.4 Label D：Winner Development Label

目的：

```text
识别中期是否进入真正右尾发展阶段。
```

episode 生命周期内是否出现：

```text
MAE / MFE 达到 +30% / +50%
且未先触发结构性退出
```

这个 label 不应该用于最早期 entry，而应该用于中期状态判断。

### 7.5 Label E：Exit / Exhaustion Label

目的：

```text
优化退出和降仓。
```

未来 5 / 10 / 20 日内：

```text
继续持有的边际收益是否为负？
是否出现主升浪衰竭？
是否出现高波动派发？
```

这个 label 用来训练动态退出，而不是训练入场。

---

## 8. 仓位管理是主模型之一

EP4 中，仓位管理不是配角，而是核心。

因为早期无法确定，所以正确的资金结构应该是：

```text
低确定性 -> 小仓位
证据增强 -> 加仓
证据变弱 -> 降仓
证据证伪 -> 退出
```

一个初始框架：

| 阶段 | 仓位行为 | 风险预算 |
|:--|:--|:--|
| Seed 出现 | 探针仓 | 0.2R - 0.3R |
| 通过 early failure 检查 | 保留 | 0.3R - 0.5R |
| 出现 continuation | 第一次加仓 | 0.5R - 0.8R |
| 行业 / 资金 / 趋势共振 | 第二次加仓 | 0.8R - 1.2R |
| 加速但拥挤 | 不再加仓 | 锁利润 |
| 趋势衰竭 | 降仓 / 退出 | 释放风险预算 |

仓位不要按固定资金比例给，而应按止损距离反推：

```text
position_size = risk_budget / stop_distance
```

这样波动越大的股票，仓位自然越小。

---

## 9. 止损分三层：结构、波动、状态

### 9.1 结构止损

适合早期 probe position：

```text
跌破突破区
跌破启动日低点
跌破最近 pivot low
跌破 EMA20 / EMA30
突破后快速回到平台内部
```

作用：

```text
快速 fail。
```

### 9.2 波动止损

适合趋势确认后：

```text
trailing_stop = highest_close - k * ATR
```

`k` 不应固定：

| 状态 | k 值 |
|:--|:--|
| 初始探针 | 1.0 - 1.5 |
| 趋势确认 | 2.0 - 3.0 |
| 强趋势发展 | 3.0 - 4.0 |
| 高拥挤 / 放量滞涨 | 1.5 - 2.0 |
| 行业退潮 | 1.0 - 1.5 |

### 9.3 状态止损

适合中后期，是 EP4 中最重要的退出层。

核心问题不是：

```text
跌了多少就卖？
```

而是：

```text
趋势生命力是否还存在？
```

状态止损可以看：

| 变量 | 衰竭迹象 |
|:--|:--|
| trend strength | 趋势斜率下降 |
| relative strength | 从市场前 20% 回落到后 50% |
| volume quality | 上涨缩量、下跌放量 |
| volatility quality | 下跌波动显著大于上涨波动 |
| industry breadth | 同行业强势股数量下降 |
| drawdown health | 回撤幅度和速度异常 |
| crowding | 极端换手、极端乖离、连续加速 |

---

## 10. Validation 改写：不要先看 AUC

EP4 不应把 entry AUC 作为主指标。主指标应该是 episode / payoff / capital efficiency 级别。

| 指标 | 解释 |
|:--|:--|
| big winner seed recall | 历史大牛股早期有多少被 seed 捕获 |
| failed seed average loss | 每个失败种子平均亏损 |
| failed seed median holding days | 失败样本资金占用天数 |
| winner capture ratio | 大牛股涨幅实际吃到多少 |
| payoff skew | 收益分布是否右偏 |
| exposure-adjusted return | 单位资金占用收益 |
| max drawdown | 组合层面最大回撤 |
| Calmar ratio | 回撤控制后的收益能力 |
| turnover | 换手成本 |
| capital efficiency | 单位风险预算产出 |

最关键的验收项：

```text
1. failed seed loss 是否足够小；
2. big winner recall 是否足够高；
3. winner capture ratio 是否足够高；
4. portfolio max drawdown 是否可控；
5. payoff distribution 是否右偏。
```

EP3 P0.5 的核心教训是：trigger rate、recall、event count 本身都不够，必须放到 baseline 对照下解释。因此，EP4 的 validation 不应只报告 absolute metric，而应默认报告：

```text
metric level
metric diff vs matched-delay baseline
metric diff vs matched-random baseline
robustness split consistency
p05 / tail no-harm
```

尤其是 R01，不能只看 `big winner seed recall 没被明显杀掉` 和 `failed seed average loss 略有下降`。这两个条件组合起来太弱，容易让一个几乎没有经济意义的宽 seed 通过。更合理的方向是看 recall-cost trade-off：

```text
每保留 / 新增一个 big winner seed，
需要付出多少 failed-seed loss 和 exposure-days？
```

R01 的问题应该被表述为：

```text
宽 seed 买观察权这件事，
是否在 matched baseline 下足够便宜，
并且保留了足够多右尾种子？
```

---

## 11. EP4 整体实验规划

本节只讨论实验方向，不是 requirement，也不细化到具体 contract。

EP4 不应该把 `seed`、`probe`、`fail-fast`、`add`、`dynamic stop`、`position sizing` 一次性放进 R01。那会重复 EP3 的主要问题：同时引入太多自由度，最后无法判断到底是哪一层有效，哪一层只是过拟合或噪音。

更合理的原则是：

```text
每一阶段只新增一个主自由度；
前一阶段没有证明的东西，后一阶段不能假设已经成立。
```

因此，EP4 应拆成四个逐层推进的研究阶段：

| 阶段 | 新增研究对象 | 暂不研究什么 | 阶段意义 |
|:--|:--|:--|:--|
| R01 | High-Recall Seed + Probe + Fail-Fast | 不加仓、不做复杂动态止损、不做组合优化 | 证明高召回 seed 的试错成本是否可控 |
| R02 | Continuation / Add Eligibility | 不重新改 seed、不改 fail-fast 主规则 | 证明存活 episode 是否能分出值得加仓的子集 |
| R03 | ATR / Dynamic Stop | 不重新选 entry、不重新定义 add eligibility | 证明退出层是否改善 payoff skew 和 drawdown |
| R04 | State Stop / Position Sizing System | 不再单看 episode alpha | 证明能否升级为组合层右尾管理系统 |

这个拆法的重点不是把 EP4 变慢，而是让每一步都能回答一个清楚的问题。R01 只证明“买观察权是否可行”；R02 才证明“证据增强后是否值得加仓”；R03 才证明“动态退出是否真的保护右尾”；R04 才讨论“组合层风险预算是否承受得住”。

---

## 12. EP4 R01：High-Recall Seed + Probe + Fail-Fast

R01 是 EP4 的地基。它不要急着赚钱，也不要急着证明完整策略。

R01 只问：

```text
如果 entry 保持宽召回，
用小 probe 仓位 + 快速失败退出，
能不能让失败 seed 的成本足够小，
同时不明显杀掉 big winner seed recall？
```

R01 的正确定位是：

```text
验证“买观察权”这件事是否成立。
```

因此，R01 里的“高召回”必须是可证伪的，而不是口号。进入正式 requirement 前，至少要先冻结三个讨论边界：

```text
big winner reference set 的分母；
recall 掉多少算明显杀掉；
seed-day / episode-count / universe coverage 的上限。
```

如果没有 seed density 或 universe coverage 的对偶约束，`seed 越宽 recall 越高` 会成为平凡解。EP3 P0.5 已经说明 trigger rate 不等于 payoff edge；EP4 R01 同样不能让 high recall 变成 unlimited trigger rate。

R01 与 EP2 `EP2_LAUNCH_DETECTOR_V0` 的关系也要先定性清楚。比较稳妥的讨论定位是：

```text
EP2 detector = baseline / control；
EP4 wide seed = 可以更宽，但必须解释新增 coverage 的代价；
R01 不应默认用 wide seed replace EP2 detector 后直接比较收益。
```

也就是说，R01 应回答：

```text
相对 EP2 detector，
是否增加 big-winner early coverage；
新增 coverage 是否没有被 failed-seed cost 吞掉；
新增 seed density 是否仍然可交易。
```

它应该包含：

```text
wide seed
small probe
early fail-fast
simple / fixed exit baseline
```

它不应该包含：

```text
staged add
ATR dynamic stop
state stop
portfolio-level position sizing
复杂 continuation model
```

原因很简单：一旦 R01 引入加仓和动态退出，失败成本、收益来源、右尾捕获和资金占用都会混在一起。那样即使结果变好，也无法知道是 seed 有效、fail-fast 有效、加仓有效，还是 exit 偶然有效。

同理，R01 的 fail-fast 也不应该是训练出来的模型。R01 只能使用 deterministic fail-fast，例如：

```text
跌回突破区
跌破启动日低点 / pivot low
跌破结构 reference
固定 H10 / H20 vertical barrier
```

Label B 可以在 R01 里作为 audit label 出现，但不应在 R01 里训练 Early Failure Detector。训练式 fail-fast 应该放到 R01.5 或 R02 之后，否则 R01 会同时引入 seed 宽度和 fail-fast 模型两个主自由度。

R01 如果失败，说明高召回 seed + 小 probe 的路径本身不值得继续。如果 R01 成立，才说明后面有资格讨论“哪些存活 episode 值得加风险”。

R01 的方向性验收不应是 AUC，而应看：

```text
big winner seed recall 是否没有被明显杀掉；
failed seed average loss 是否在 matched baseline 下可控；
failed seed holding days 是否在 matched baseline 下缩短；
payoff distribution 是否至少没有明显左偏；
wide seed + small probe + deterministic fail-fast 是否优于同 seed 的无 fail-fast baseline；
recall-cost trade-off 是否足够便宜，而不是只靠 seed 变宽刷 recall。
```

这里需要注意：`Scale` 不是 R01 的任务。R01 不应再叫 `Probe-Observe-Scale`，更准确的名字是：

```text
High-Recall Probe Cost-Control
```

---

## 13. EP4 R02：Continuation / Add Eligibility

R02 只在 R01 存活 episode 里做。

它的问题不是：

```text
怎么找到新的 entry？
```

而是：

```text
哪些已经通过早期失败检验的 episode，
值得从 probe 升级到正式风险？
```

R02 的关键是 attribution。Seed、probe、fail-fast 在 R01 已经固定；R02 只新增一个判断：

```text
add or not add
```

R02 如果成立，说明右尾管理系统开始有“证据累积加仓”的基础。R02 如果不成立，EP4 仍然可能是一个小仓位 event sleeve，但不能升级成 scale system。

R02 不应该重新调宽 seed，也不应该改变 R01 的 fail-fast 主规则。否则它会重新变成 entry search，而不是 continuation eligibility。

---

## 14. EP4 R03：ATR / Dynamic Stop

R03 的位置应该在 add eligibility 之后，而不是之前。

原因是：退出规则的价值取决于前面的持仓结构。如果还不知道哪些 episode 值得加仓，就先做复杂动态止损，结果会很难解释。

R03 只问：

```text
在已有 probe / add 结构下，
ATR trailing 或其他相对机械的 dynamic stop，
是否改善 payoff skew、winner capture 和 drawdown？
```

R03 应优先研究机械、可解释、低自由度的退出规则，例如：

```text
structure stop
ATR trailing stop
simple profit giveback
time stop
```

R03 不应一开始就上复杂 state stop。复杂 state stop 很容易变成 EP3 anchor formula 的翻版：变量看起来都合理，但很难证明它们在 matched baseline 和 tail risk 下仍然有真实增量。

---

## 15. EP4 R04：State Stop / Position Sizing System

R04 才是完整系统层。

它研究的是：

```text
组合层 risk budget
行业 / 主题集中度
多 episode 同时存活时的风险分配
state stop
capital efficiency
```

R04 不能提前放到 R01。A 股右尾经常按行业、主题、市场风格聚集；单个 episode 看起来都应该加仓时，组合层风险可能反而最高。如果没有组合层 risk budget，系统会在“证据最强”的时候承担最集中的风险。

所以 R04 的目标不是再证明某个 episode 规则有效，而是证明：

```text
这个右尾 episode 管理系统能不能在组合层承受真实风险。
```

R04 通过之后，EP4 才能从 episode research 进入 portfolio system research。

---

## 16. EP4 的输出形态

最终系统可以定义为：

```text
Big Winner Episode Management System
```

输入：

```text
价格
成交
波动
相对强度
行业广度
市场状态
基本面事件
```

输出：

```text
action_t in {enter_probe, hold, add, reduce, exit}
risk_budget_t
stop_level_t
episode_state_t
```

每一天系统只回答：

```text
这个 episode 是否已经失败？
如果没有失败，证据是否增强？
如果证据增强，是否值得投入更多风险预算？
```

而不是每天问：

```text
它最后会不会涨 50%？
```

---

## 17. 三条原则

### 17.1 不要把不确定性消灭掉，要给不确定性定价

早期结构本来就不确定。

不应该试图通过 filter 把它变确定，而应该做：

```text
不确定性高 -> 小仓位
不确定性下降 -> 加仓
不确定性重新上升 -> 降仓
不确定性被证伪 -> 退出
```

### 17.2 Entry 保持高召回，退出负责高精度

```text
entry 负责不漏掉右尾；
exit 负责快速砍掉错误；
position sizing 负责控制损失。
```

如果 entry 太精，会漏掉大牛股种子。
如果 exit 太宽，会被失败样本拖死。
如果仓位太大，会在不确定阶段亏太多。

### 17.3 优化对象不是单笔交易，而是 episode payoff distribution

不应把胜率、AUC、单次收益率作为主优化对象。

应该看：

```text
失败样本亏损是否小；
成功样本是否拿得住；
右尾是否足够厚；
资金占用是否合理；
组合回撤是否可控。
```

---

## 18. 阶段性判断

EP4 的一句话定义：

```text
这个系统不是“预测大牛股系统”，而是“右尾机会管理系统”：
用宽松结构信号发现潜在种子，
用小仓位购买观察权，
用 fail-fast 控制失败成本，
用证据累积决定加仓，
用状态化动态止损保护趋势生命力，
最终让少数 big winner 覆盖大量小失败。
```

EP4 下一步应该先写 R01 requirement，但 R01 requirement 不应从完整系统开始，而应从最小可证伪问题开始：

```text
High-Recall Seed
Small Probe
early failure definition
simple / fixed exit baseline
seed recall and failed-seed cost validation
```

只有当 R01 证明“高召回 seed + 小 probe + fail-fast”这件事本身成立后，才应该进入 R02 加仓资格、R03 动态退出和 R04 组合层 risk budget。
