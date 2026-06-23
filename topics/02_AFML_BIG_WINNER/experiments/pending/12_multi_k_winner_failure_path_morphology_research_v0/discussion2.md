# Discussion 2: C0 Enrichment Ceiling and Event-family Mining Reset

## 0. 背景

`12A7f` 显示 C0 相对同期、同 regime、同 board、同日历控制组存在右尾富集，但幅度偏弱，且 C0 同时放大 fast-fail 左尾。

Robustness / direct-entry / `+20% / 20d`：

```text
control winner rate = 0.1236
C0 winner rate      = 0.1552
winner_diff         = +0.0316, CI95 [+0.0109, +0.0522]

control fast-fail   = 0.2466
C0 fast-fail        = 0.3059
fast_fail_diff      = +0.0592
```

这个结果足够说明 C0 不是完全错误的人群，但不足以说明 C0 是一个强 winner event。更准确的定位是：

```text
C0 is a weak right-tail enriched, two-tailed volatility event.
It is not a clean winner selector.
```

## 1. 对 +3pp 裸 event uplift 的判断

`+3.16pp` 的绝对 uplift 偏小。它有统计意义，但策略意义弱。

粗略用固定 barrier proxy 衡量：

```text
right-tail benefit ~= winner_diff * 20%
left-tail penalty  ~= fast_fail_diff * 10%

current:
  +3.16pp * 20% = +0.63%
  +5.92pp * 10% = -0.59%
```

也就是说，裸 C0 的右尾富集几乎被额外左尾惩罚抵消。这个计算还没有纳入交易成本、滑点、停牌/涨跌停可执行性、资金占用、未触 barrier 的路径收益分布。

因此当前 C0 的正确解释不是“event edge 已经够好”，而是：

```text
C0 has weak but real enrichment.
Direct-entry enrichment is too small to justify a selector by itself.
Failure and winner information remain entangled.
```

## 2. 裸 event 的实用门槛

如果目标是找一个“比较好”的裸 event，针对 `+20% / 20d` matched-control enrichment，建议门槛如下：

```text
+2pp 左右：有信号，但偏弱
+3pp：勉强说明 event 不是错人群，但不够好
+5pp：开始有研究价值
+6-8pp：比较好的裸 event 结果
+10pp+：强事件级富集
```

对当前 control rate `12.36%` 来说，比较好的裸 event 应大致达到：

```text
C0-like event rate ~= 18.5% - 20.5%
winner_diff        ~= +6pp - +8pp
CI95 low           >= +3pp
```

同时需要约束左尾：

```text
fast_fail_diff <= +3pp, ideally <= 0
+20%/20d and +20%/40d both positive
net utility after conservative cost buffer > 0
```

如果 fast-fail 仍然多 `+6pp`，winner uplift 至少要到 `+6-8pp` 才值得继续把裸 event 当核心资产看。当前 C0 更像“弱右尾富集 + 强左尾污染”。

## 3. 继续沿 C0 selector 路线的风险

从前序实验看，winner 与 failure 信息一直纠缠：

```text
1. C0 同时放大右尾与左尾。
2. stage-1 volatility defense 有用，但更像 participation throttle。
3. stage-2 continuation signal 有方向，但 strict random support 不足。
4. 加模型容量并没有稳定拆开 winner / failure。
```

因此继续在当前 C0 上直接堆 selector，会面临两个硬问题：

```text
signal ceiling:
  裸 event uplift 只有约 +3pp，扣掉左尾和成本后很薄。

separability ceiling:
  winner 与 failure 共用高波动/状态切换来源，很难通过单一 X 或简单 stage-2 score 干净切开。
```

更合理的下一步不是继续硬推 C0，而是重新做 event-family enrichment mining：先从现有数据里挖出相对更好的 event family。

## 4. Winner label 不应只用 120d +50%

`120d +50%` 更适合作为 episode registry / long-horizon reference，不适合作为 event discovery 的 primary label：

```text
1. horizon 太长，事件与结果之间混入大量后续 regime 和路径噪声。
2. positive 太稀疏，早期 discovery 容易被样本量卡住。
3. 固定 +50% 不 regime-aware，不同年份、板块、波动环境含义不同。
4. 它不能直接回答一个 event 在 20/40/60d 是否有可交易右尾优势。
```

建议先建立 label panel，而不是单一 winner 定义。

Primary tradable labels：

```text
U15/H20
U20/H20
U20/H40
vol-scaled U = k_up * pre_event_vol, H = 20/40/60
```

Penalty labels：

```text
fast_fail_L10_H20
early MAE / drawdown
hit_down_before_up
```

Secondary big-winner references：

```text
MFE_60d / pre_event_vol >= k
MFE_120d top quantile
fixed +50% / 120d only as reference, not primary gate
```

Primary scoring 不应只看 winner rate，而应看：

```text
winner uplift vs matched control
failure uplift / downside penalty
net utility proxy after conservative cost buffer
cross split / year / board stability
event_n and positive_n support
```

## 5. 不做 full grid search，先做方向扫描

一开始不要对 CUSUM、vol、threshold、horizon、debounce、组合条件做全笛卡尔积。计算量会大，而且更重要的是容易数据挖掘过拟合。

第一阶段应该做 primitive direction scan，只问“哪个方向值得展开”。

候选 primitive：

```text
cusum up/down intensity
vol compression / vol expansion
ret_5d / ret_10d / ret_20d / ret_60d
distance_to_high / distance_to_low
drawdown / rebound
turnover_zscore / volume_zscore
board-relative strength
trend_ma_5_20 / trend_ma_20_60 spread
range / entropy / path disorder
```

每个 primitive 先做单变量诊断：

```text
AUC / rank IC
top/bottom decile winner rate
top/bottom decile fast-fail rate
winner uplift vs matched control
fast-fail penalty vs matched control
net utility proxy
year / board stability
```

这一阶段的目标不是找最终 event，而是确定大方向：

```text
low-vol compression?
volume expansion?
relative strength?
oversold rebound?
CUSUM state transition?
trend continuation?
```

没有方向的 family 不进入 grid。

## 6. Coarse-to-fine event grid

第二阶段再做 event grid，但必须 coarse-to-fine，而不是全量展开。

### Stage A: 单 family 粗 grid

每个 family 只扫少量粗阈值：

```text
quantile thresholds: top/bottom 5%, 10%, 20%, 30%
vol multiples: 1.0, 1.5, 2.0
lookbacks: 10d, 20d, 60d
horizons: 20d, 40d, 60d
```

每个 candidate event 都必须输出：

```text
event_n
winner_rate
winner_diff_vs_control
winner_diff_ci
fast_fail_rate
fast_fail_diff_vs_control
net_utility_proxy
stability slices
```

### Stage B: Pareto 前沿筛选

只保留同时在以下维度不过分差的候选：

```text
winner uplift
fast-fail penalty
event_n / positive_n
net utility
year / board stability
control matching coverage
```

候选不能只因 winner rate 高入选；如果 fast-fail 同步大幅升高，应降级为 two-tailed event。

### Stage C: top family 局部细化

只对 Stage B 前沿候选做局部加密：

```text
threshold 附近加密
lookback 附近加密
horizon 附近加密
debounce / cooldown 微调
canonicalization priority 微调
```

### Stage D: 只允许低阶组合

组合搜索必须后置，且第一轮只允许两个条件：

```text
vol_compression + relative_strength
cusum_up + volume_expansion
drawdown_rebound + board_relative_strength
trend_state + low_failure_history
```

不应一开始做三层或四层 AND/OR 搜索。

## 7. 搜索纪律

必须沿用 12A 系列的 train-frozen 纪律：

```text
train:
  选择 family / direction / threshold / label preference

validation:
  shortlist stress readout only

robustness:
  final readout only, 不允许回头调参
```

还需要额外控制：

```text
1. matched control 必须按 split x board x calendar_month x regime 构造。
2. overlapping horizon / same instrument clustering 要用 block bootstrap 或 instrument-date block。
3. all-sample 最优 grid 不得回头解释为发现过程。
4. 每个 candidate 的搜索来源、grid_size、family_size 必须记录，方便做多重检验折扣。
5. local positive 不能直接升级，必须跨 year / board 稳定。
```

## 8. 建议的新诊断定位

建议新增一个 discovery diagnostic，而不是 selector：

```text
event_family_enrichment_cartography
```

它的目标不是训练模型，也不是输出交易规则，而是回答：

```text
在现有 PIT 数据和 qfq path 下，是否存在比 C0 更干净的 event family，
能在 matched control 下提供更高 winner uplift、更低 failure penalty、
且跨 split / year / board 稳定？
```

建议输出：

```text
label_panel.parquet
primitive_feature_panel.parquet
univariate_feature_direction_readout.csv
coarse_event_grid_readout.csv
event_family_frontier.csv
matched_control_enrichment_readout.csv
stability_slice_audit.csv
event_search_decision.md
```

## 9. Go / No-go 建议

裸 event 候选进入后续 selector 研究，至少应满足：

```text
winner_diff >= +6pp
winner_diff_ci95_low >= +3pp
fast_fail_diff <= +3pp, ideally <= 0
event_n / positive_n 足够支持 split readout
+20%/20d 与 +20%/40d 不方向冲突
net utility proxy after cost buffer > 0
```

如果某个 event 只有 `+3pp` 级别 winner uplift：

```text
status = weak_enrichment_only
allowed_use = diagnostic comparator
not_allowed = primary event backbone
```

如果粗 grid / 单变量方向扫描都找不到 `+6pp` 级别且不放大 failure 的 event，则应接受：

```text
winner/failure entanglement may be structural in current event universe.
Continuing to add selector capacity is unlikely to solve the core problem.
```

## 10. 当前结论

当前 C0 继续作为主线裸 event 的胜率不高。更务实的路线是：

```text
1. 暂停直接推进 C0 survivor selector 为主线。
2. 建立多 winner label panel，避免单押 120d +50%。
3. 先做 primitive direction scan，找事件族大方向。
4. 再做 coarse-to-fine event grid。
5. 只让 winner uplift 明显高、failure 不同步放大的 event 进入后续 selector。
```

短版：

```text
C0 gave enough evidence to avoid calling the population completely wrong,
but not enough evidence to keep treating it as the main winner event.
The next move should be event-family enrichment cartography, not more selector capacity.
```

---

## 11. 与 research_plan_3 的分叉（必须先收敛）

本讨论(discussion2)与 `research_plan_3_winner_label_form_and_decoupled_selector.md` 是**从同一个 12A7f 结果(+3.16pp)推出的相反结论**。在动手之前这个分叉必须先解决，否则会用大量成本去赌一个还没被裁决的方向。

```text
discussion2 读法:
  +3pp 太弱，扣掉左尾和成本几乎归零 -> 推倒 event，做 event-family cartography。

research_plan_3 读法:
  +3pp 真实显著，survivor-conditional 翻倍到 +5.67pp，event 没选错
  -> 不动 event，在 survivor 池上做 vol-scaled label 的 separability 诊断。

用户提出的第三条（更激进）:
  event 整链不可信，连 C0 都不要
  -> 从 PIT universe 直接做 vol-scaled。
```

三者必须用同一把尺子(separability + 净值，而非 base-rate)裁决，不能各读各的。

## 12. “从 PIT universe 直接做 vol-scaled” 要拆成三层

“直接上 vol-scaled” 是对还是危险，取决于 vol-scaled 指**哪一层**：

```text
A. vol-scaled LABEL（barrier 按事件前波动率缩放的“赢家”定义） —— 结果层
B. vol-scaled EVENT（vol compression / expansion 当事件触发）   —— 选择层
C. fast-fail defense overlay（左尾清洗）                        —— 风险层
```

判断：

```text
A 放到全 PIT universe 上做 = 对，且是三份文档的真正交集。
  label 是 outcome 的性质，本就不该被 C0 selection 污染；
  全 universe base rate 又天然给出 discussion2 §7 想要的干净 matched-control 分母；
  vol-scaling 又正面回应 12A7f §1.3 的年度/regime 漂移。
  注意：research_plan_3 §5.2 把 label 分母锁在 survivor 池，
  其实把 event selection 烤进了 label，全 universe 提法在这点上更干净。

“直接” 不能等于跳过 C 和丢掉 C0。
  若 “直接从 PIT universe 上 vol-scaled” 意味着不做 fast-fail 防守、不用 C0，
  就丢掉了目前唯一被量化、且效果最大的结构性发现。
  正确形态：label 定义在全 universe（event-agnostic），
  但评估时仍保留 defense overlay，并把 C0 当作“众多 selector 之一”同尺度量，
  不预先判死。

B（vol 当事件）就是本讨论 §5 的 primitive scan。
  可以做，但与 A 是两回事，且会把多重检验面积放大一个数量级，不要和 A 混着上。
```

## 13. 关键修正：survivor-conditional 的“翻倍”不是免费的

research_plan_3 §1.2 用 “清掉左尾后右尾 enrichment 从 +3.16pp 接近翻倍到 +5.67pp、CI 更远离 0” 来论证 “防守净化了右尾人群”。这条**会被误读成防守是净增益**。实际上它有显著的隐藏成本，必须显式记账：

```text
1. rate != count，分母被砍。
   survivor_conditional 是“先过 no_fast_fail_L10_H20 之后”的条件率。
   分母（survivor_n）远小于 direct-entry entry_n。
   绝对捕获的 winner 数 = rate x denominator，
   完全可能比裸入场 0.1552 x entry_n 更少。
   “enrichment 翻倍” 是 precision 提升，是用 recall 换来的，不是白拿。

2. fast-fail 闸对真实 continuation 有实打实的误杀。
   discussion.md §6 已记录：部分真正 +30% survivor 在成功前曾跌到 -12% ~ -15%。
   -10% 的 fast-fail 闸会先把这些真机会砍掉。
   也就是说该闸对 continuation 有非零 false-negative，
   它消耗的是“先深蹲后启动”的那一类真实大赢家。

3. 与 12A7e 的结论自洽。
   12A7e 已证 stage-1 X 是 participation throttle：
   stage-2 正样本随 survivor 分母大致成比例缩放。
   “去掉左尾的同时也按比例去掉右尾” 与此处“翻倍是条件率假象”同源。
```

因此 §1.2 的正确表述应是：

```text
survivor-conditional 的右尾“变干净” 是一次 precision / recall 取舍，
不是免费净化。它买到更高条件命中率，代价是牺牲一部分真实 continuation 机会。
是否净正，取决于 precision / recall 曲线与效用函数 —— 这要被测量，不能被假设。
```

这同时反过来加强了本讨论的核心怀疑：把 fast-fail defense 当作“免费净化层”再在其上堆 selector，可能只是在一个被 recall 削薄的池子上追逐更高的条件率，而真实可捕获的大赢家总量在下降。

## 14. 真正的 go/no-go 是 separability + 净值，不是 base rate

无论走 discussion2 的 event 重做、research_plan_3 的 label 修正、还是用户的全 universe 重建，最坏情况都一样：

```text
base-rate 更厚 != 可预测。
花大代价得到一个 base rate 更漂亮、但单特征仍不可分的 label，
selector 还是立不住。
```

所以下一步的闸门必须是：

```text
1. separability：换上 vol-scaled label 后，在（清过左尾、且 recall 成本被记账的）池上，
   右尾赢家是否单特征可分（AUC >= 0.55 / rank-IC 跨 split 同号 / top-decile lift 显著）。
2. 净值（含 recall 成本）：用第 13 节的 precision/recall 记账，
   而不是 §2 那把固定 barrier proxy，来判断 defense + selector 配对后是否净正。
```

## 15. 建议的最省力验证序列（避免直接梭哈全 universe 重做）

```text
1. label-only：在全 PIT universe 上定义 vol-scaled winner label 面板，
   产出 universe-wide base rate（干净分母，几乎免费解决 §7 一半的 matched-control 复杂度）。

2. 不重做 event：把现有 C0 survivor 池贴上这个新 label，跑 separability 诊断；
   同时输出 fast-fail 闸的 continuation recall 成本（第 13 节记账），裸 entry 池做对照。

3. 决策判据（预注册）：
   - C0 survivor 池上新 label 单特征可分、且净值（含 recall 成本）为正
     -> research_plan_3 方向成立，不需要重做 event。
   - 不可分，但全 universe 上同一 label 明显更可分
     -> 才有理由付全 universe 重做（discussion2 / 用户方向）的代价。
   - 两边都只是 base-rate 更厚、都不可分
     -> winner-selection 路线重判，转 defense overlay + 规则化参与（干净结论，非失败）。

4. 只有第 3 步给出“全 universe 才可分”的证据，才启动整体重做；
   且重做时 defense overlay 必须保留，不能“直接”跳过左尾清洗，
   并且必须同时报告 continuation recall 成本，不允许只报条件率。
```

短版：

```text
The survivor-conditional doubling (+3.16pp -> +5.67pp) is precision bought with
continuation recall, not a free purification. Decide the discussion2 / research_plan_3 /
full-universe fork by separability AND recall-accounted net utility, not base-rate enrichment.
Define the vol-scaled label on the full PIT universe (event-agnostic), but keep the
fast-fail defense and C0 as evaluated assets — do not drop them by going "directly".
```

## 16. 反向寻找：先建 winner uplift panel，再在左侧寻找 event

另一个方向是 label-first / outcome-anchored event discovery：

```text
先构建 winner uplift panel；
再把每个 instrument x reference_date 左侧的 PIT history 离散成 event tokens；
然后在 winner label 的左侧区域寻找可能的 event sequence；
最后对每个 event sequence 计算 winner uplift / failure uplift / utility proxy。
```

这个方向是合理的，而且比继续围绕 C0 小修小补更有发现能力。但它不能做成“枚举所有可能 event 序列”，否则会立刻变成高维数据挖掘。正确形态应该是有语法约束的 reverse event mining。

建议框架：

```text
1. winner uplift panel
   row = instrument x reference_date
   future labels =
     U15/H20
     U20/H20
     U20/H40
     vol-scaled U = k_up * pre_event_vol, H = 20/40/60
     fast_fail_L10_H20
     lower_first / hit_down_before_up

2. left-side PIT region
   lookback window in {10, 20, 40, 60}
   only use information available at reference_date close or earlier

3. event tokenization
   vol_compress_20d
   vol_expand_5d
   cusum_up_intensity_high
   cusum_down_exhaustion
   ret_5d / ret_20d direction buckets
   drawdown_20d_deep
   rebound_5d
   near_60d_high / near_60d_low
   turnover_spike
   board_relative_strength

4. constrained event grammar
   max_sequence_len in {1, 2, 3}
   min_support >= pre-registered floor
   token family repetition limited
   optional order relation: A before B within lookback window
   no future label-derived token
```

核心 scoring 不是“winner 样本里有什么共同特征”，而是 contrastive uplift：

```text
event_pattern:
  event_n
  winner_positive_n
  winner_rate(event)
  winner_rate(matched_control)
  winner_uplift = rate_diff / lift / odds_ratio

  fast_fail_rate(event)
  fast_fail_rate(matched_control)
  fast_fail_uplift

  lower_first_rate
  neutral_rate
  utility_proxy_after_cost_buffer
  year / board / regime stability
```

必须避免的后验陷阱：

```text
从 winner samples 左侧挖 pattern，
然后直接说该 pattern 是 winner event。
```

这会严重高估效果。所有 event pattern 必须 train-only 发现：

```text
train:
  mine token / sequence / threshold / orientation

validation:
  frozen pattern readout only

robustness:
  final readout only，不允许再改 pattern
```

因此，这条路线更适合作为 12A7g 之后的高成本 follow-up：

```text
如果 12A7g 显示：
  full-universe primitive separability 明显强于 C0，
  且不是单纯 base-rate 变厚，
  且 recall-accounted utility proxy 有希望，

则启动 event-family enrichment cartography，
用 reverse event mining 在 full PIT universe 左侧区域搜索候选 event sequence。
```

短版判断：

```text
反向寻找是可行的，但必须是受限 grammar + matched control + train-frozen 的 event mining。
它不是当前最低成本验证的替代品，而是当 12A7g 证明 full universe 左侧 primitive
确实更可分之后，才值得支付的下一阶段计算成本。
```

## 17. 反向寻找的可行性评审

### 17.1 它不是新估计量，只是反向搜索

contrastive uplift `P(winner|event)` vs `P(winner|control)` 是对称的：从 event 端正向枚举（§6）还是从 winner 端反向挖（§16），估的是同一个量。所以 §16 不是新方法论，而是对同一搜索空间的另一种遍历顺序。

```text
反向挖在心理上更有迷惑性：“看赢家左侧都有什么共同点” 天然让人高估，
正好踩中本节自己警告的后验陷阱。
相对 §6，它没有增加信息，却增加了过拟合诱惑。
```

### 17.2 多重检验是生死线

```text
token 家族 ~12 × 方向/分位桶 ~3-5 -> base token ~40-60
len-1: ~50
len-2(带 order): ~数千
len-3(带 order): ~10^4 - 10^5
```

即便有 min_support 和家族重复限制，候选模式轻松到 `10^3 - 10^5`。而当前最好的单 event（C0）也只有 +3pp。一个 len-2 / len-3 序列要在 FDR / Bonferroni 折扣后还稳定站上 +6pp，概率很低。

```text
能在严格多重检验折扣后活下来的，几乎只会是 len-1、少量 len-2;
而 len-1 本质就是 §5 的 primitive scan。
-> §16 在“能过统计关”的深度上，与 §5/§6 高度重叠，增量有限。
grammar 被夹在中间：太浅 = 退化成 §5;太深 = 没 support。可用区很窄。
```

### 17.3 Power / support 先于 compute 卡死

winner 正样本本就稀（项目根因）。条件在 len-2 / len-3 序列上 support 指数级缩小，uplift 的 CI 立刻宽到无法裁决。

```text
计算不是瓶颈（PrefixSpan / SPADE 式 min_support 剪枝完全 tractable）;
正样本量才是瓶颈。深序列在当前数据上不具备统计功效。
```

### 17.4 两个会系统性高估的隐藏陷阱

```text
a. 控制组 reference_date 必须匹配 winner 的时间分布。
   winner 在牛市 / 特定 regime 聚集;若控制组只按 board/month 配、
   不按“winner 出现的日历密度”配，会把“赢家多发生在牛市”当 event 重新发现一遍。

b. episode 级去重。
   同一个大赢家生成一串相邻 reference_date，左侧 token 几乎相同;
   naive event_n / positive_n 会把少数 episode 灌成“高频 pattern”。
   必须 episode 去重或 instrument-date block bootstrap。
```

### 17.5 tokenization 是新增自由度

token 分桶阈值、lookback、`A before B` 时序关系，每个都是研究者自由度与过拟合入口。`order relation` 是大乘子，但在 A 股日线噪声里边际信号很薄。token 之间高度共线（ret_5/20、near_high/near_low、vol_compress/expand），共线 token 的序列会再次虚增 pattern 计数。必须预注册 tokenization，并先做方向簇去共线。

### 17.6 它不解决真正的问题：entanglement / separability

整条失败链的瓶颈是 winner / failure 纠缠与可分性，不是缺 event 候选。

```text
一个高频左侧 pattern 完全可能和 C0 一样是双尾的(winner_uplift 高、fast_fail_uplift 同步高);
即换个名字重新发现一个 C0-like 双尾事件。
base-rate 厚 != 可分 != 可交付。
```

### 17.7 低风险拆分：panel 该建，mining 该 gate

```text
建 winner uplift panel（§16 第 1 步） = 低后悔。
  它就是 §15 那个全 universe vol-scaled label 面板，无论反向挖是否成功都复用，先建无妨。

在 panel 上做 sequence mining（§16 第 2-4 步） = 高风险，必须 gate。
```

### 17.8 可行性裁决

```text
可行性 = 条件可行，但优先级排在 12A7g 之后，且不能替代最低成本验证。

成立前提(缺一不可):
  1. 预注册 tokenization + 方向簇去共线;
  2. 严格 FDR / deflated metric，按真实 grid_size x family_size 折扣;
  3. episode 去重 + instrument-date block bootstrap;
  4. 控制组 reference_date 按 winner 时间密度匹配;
  5. train-frozen，validation / robustness readout-only;
  6. fast_fail_uplift 设为同等否决项，显式拒绝双尾 pattern。

满足以上后，能活下来的多半是浅序列，增量相对 §5/§6 有限;
它不解决 separability，只扩大候选集，且有重新发现 C0-like 双尾事件的风险。

排序:先做便宜的 12A7g(survivor 池 + vol-scaled label 的 separability + recall 记账);
仅当 full-universe primitive 可分性明显强于 C0、且非单纯 base-rate 变厚时，
才支付 reverse mining 的成本。现在就上 §16，等于在尚未证明
“全 universe 左侧更可分” 之前，先承担全文档最大的数据挖掘风险。
```
