# EP2 discussion: low-turnover launch exposure timing after BaseRate and Explore10 C/D

## 1. 当前背景

BaseRate 已经建立，项目现在有了一个更朴素、可复现、可比较的 PIT 宽基 ML 基线：

- 固定 Alpha158 + LightGBM；
- PIT `mcap500_mainboard` universe；
- next-open 执行；
- after-cost OOS 组合结果；
- daily / weekly / monthly rebalance 敏感性；
- benchmark、random baseline、cost、capacity、execution audit。

这个 BaseRate 的作用不是直接替代 Explore9 / Explore10 的事件研究，而是提供一个锚点：任何后续 launch / exposure timing / failure / primitive 研究，都需要说明它相对这个宽基基线到底增加了什么。

在 BaseRate 之前，Explore9 / Explore10 的主线大致是：

1. 从 yearly big winner 观察开始；
2. 拆解 launch / exposure / failure / hold；
3. 用 LGBM 或 tree path 尝试把 winner / failure 结构翻译成 primitive；
4. 再审计这些 primitive 是否能形成可执行策略。

这条路线的价值在于排除了很多看起来有效、但在样本、执行、null、concentration、false reject 等审计下不稳定的方向。但 Explore10 C/D 暴露了一个更根本的问题：我们可能把 launch 后 exposure timing 问题定义错了。

## 2. Explore10 C/D 暴露的问题

Explore10 C/D 中，`winner launcher` 方向表现不理想，而 `failure / reject` 方向反而看起来更有信号。这个现象不一定说明：

- winner 方向没有任何可预测性；
- LGBM 参数不合适；
- primitive search space 太小；
- failure 模型天然更高级。

更可能的解释是：`winner launcher` 的 label horizon 和 decision time 不匹配。

如果我们在启动早期，用 T 日或 T+N 日很少的信息去预测未来 120d 是否成为 big winner，本质上是在要求模型提前知道很多未来才会出现的信息：

- 后续行业行情是否扩散；
- 后续资金风格是否持续；
- 公司或行业是否出现新的催化；
- 价格趋势是否能继续确认；
- 回撤中是否有承接；
- 大盘环境是否配合；
- 交易拥挤和流动性是否恶化。

这些信息在早期 exposure decision 时点并不可见。因此，直接预测 `120d big winner` 很容易变成低信噪比的终局预测。

相反，failure / reject 更容易被早期识别。失败经常会在启动后较短窗口暴露出来，例如：

- 放量不涨；
- 冲高回落；
- 很快跌回启动区间；
- 行业内扩散失败；
- 相对行业转弱；
- 成交额退潮；
- 承接不足；
- 3d / 5d / 10d 内先触发明显回撤。

因此，failure / reject 表现更好，可能不是因为它能预测长期终局，而是因为它的目标更近、信息更快暴露、label 和 feature 的时间结构更匹配。

## 3. 关键重定义：exposure timing 不是预测 120d winner

现在要找的是 launch 后 exposure timing schedule，而不是完整 holding / exit 策略。

整体策略目标是：

- 尽量减少交易；
- exposure 动作必须可执行；
- 错了要快速 fail；
- 对最终 big winner 保持捕获能力；
- 暂时不研究完整 holding / exit。

在这个目标下，exposure timing 研究不应该定义为：

> 今天买入后，120d 内会不会成为 big winner？

而应该定义为：

> 在一个已经进入 frozen launch observation pool 的股票中，如何用低换手、next-open 可执行、短期可验证的 exposure timing schedule 安排 probe / add / fail？

更完整的主问题是：

> 在 frozen launch observation pool 中，是否存在低换手、next-open 可执行、短期可验证的 exposure timing schedule，通过 `probe_entry` 保留 winner optionality，通过 `confirm_add` 提高有效下注比例，通过 `fast_fail_exit` 限制失败 launch 损失，并且不明显牺牲 big winner coverage？

这意味着研究对象应从 `winner launcher` 转成：

> low-turnover launch exposure timing

也就是低频、可执行、早期可验证的 exposure timing schedule。

## 4. 研究对象的边界

新的 exposure timing 研究不应该从全市场每日 TopK 排名开始，而应该从 frozen launch / observation pool 内部安排稀疏 exposure。

建议的研究对象：

```text
low_turnover_launch_exposure_timing
```

它需要满足几个基本边界：

1. 只在已冻结的 PIT launch / observation pool 内安排 exposure。
2. 一个 launch episode 最多触发 1 次 `probe_entry`、1 次 `confirm_add`、1 次 `fast_fail_exit`。
3. 所有 exposure 动作使用 next-open 可执行价格。
4. probe 后 5d / 10d / 20d 内必须出现可观察确认、失败或自然退出。
5. 如果确认失败，需要快速标记为 fail 并触发 `fast_fail_exit`。
6. 120d big winner 只能作为 coverage / missed-upside 审计，不作为 primary training label。

这样定义后，exposure timing 不再承担预测完整 winner 终局的责任，而是承担一个更合理的问题：launch 后如何安排低频、可验证的下注节奏。

这里有一个实施前提：launch / observation pool 不能在 exposure timing 研究期间继续变化。Explore9 / Explore10 对 launch 的定义经历过多轮迭代，如果 pool 本身没有 PIT freeze，那么 exposure 评价指标没有可比性。

因此，EP2 实施前应先做一个很短的 pool freeze 步骤：

- 固化 launch detector 的 input、threshold、lookback、reset 规则；
- 固化 universe、industry、price、volume、money 等输入的 as-of 口径；
- 生成每日 launch episode 列表；
- 将冻结后的 pool dump 成唯一输入，例如 `ep2_launch_observation_pool.parquet`；
- 后续 exposure timing discovery、base-rate sweep、null、模型训练、report 都只能从这个 pool 读取。

## 5. 主标签方向

主标签不建议继续使用 `launch_winner_50h120` 作为 exposure timing primary label。

更合理的是短周期 confirm-validity label，例如：

```text
confirm_success_10d_12pct_before_6pct_drawdown
```

含义可以是：

- 从 next-open exposure reference price 开始；
- 未来 10 个交易日内先达到 `+12%`；
- 且在达到 `+12%` 前没有先发生 `-6%` drawdown；
- 结果需要 after-cost 仍有足够空间；
- 使用 high / low 路径判断先后顺序时必须避免同日歧义，无法判断先后时必须在 config 中写死处理策略。

这个标签回答的是：

> 这个 exposure schedule 中的 confirm window 是否很快证明自己有效？

而不是：

> 这个股票未来 120d 是否成为 big winner？

可以保留多 horizon 敏感性：

- `confirm_success_5d`
- `confirm_success_10d` as primary
- `confirm_success_20d`

但不建议一开始把 120d winner 重新放回 primary。

这个标签在方向上合理，但不应该一开始就把 `+12% / -6% / 10d` 锁死。三个阈值是耦合的，且会直接决定 base rate。如果正样本率低于可学习区间，模型很容易退化成多数类预测器；如果正样本率过高，标签又可能变成普通短线波动。

因此，正式训练前应先在冻结 pool 上做不带模型的 base-rate 普查：

- horizon: 5d / 10d / 20d；
- upside target: 8% / 10% / 12% / 15%；
- drawdown barrier: 4% / 6% / 8%；
- same-day high/low ambiguity policy: `fail` / `drop` / `conservative_fail` sensitivity；
- 输出每组标签的 positive rate、样本数、行业/年份分布、instrument-year concentration。

只有 base-rate 普查证明某组阈值既有足够正样本、又没有过度集中，才能把它选为 primary label。primary 阈值必须在模型训练前冻结，不能用 OOS 模型结果反复挑。

## 6. fast fail 的角色

fast fail 不是完整 exit 策略，但必须进入 exposure schedule 定义。

原因是：如果一个 probe / confirm exposure 无法在短窗口内证明有效，也无法在短窗口内证明无效，那么它对“减少交易、快速 fail、拿到 big winner”的目标没有帮助。

fast fail 可以定义为 exposure validity test：

- exposure 后 5d 内不能先跌破 exposure reference 的某个回撤阈值；
- exposure 后 10d 内必须出现最低幅度的价格确认；
- exposure 后不能快速跌回 launch base；
- exposure 后不能明显弱于行业；
- exposure 后量价不能快速退潮。

这个部分要和 holding / exit 区分清楚：

- holding / exit 研究的是已经买入后的完整持仓管理；
- fast fail 只研究 exposure 是否被快速证伪。

所以当前阶段不需要设计完整卖出系统，但需要设计 exposure 的短期失败判定，否则 exposure timing 研究会重新退化成长期 winner 预测。

## 7. big winner 在新研究中的位置

big winner 仍然重要，但它不应该再是 exposure primary label。

它更适合作为两个审计指标。

### 7.1 Big winner capture rate

```text
big_winner_capture_rate
```

问题是：

> 最终成为 120d big winner 的 launch episode 中，有多少被这个 exposure schedule 捕获？

这个指标防止 exposure timing 研究变成只抓短线反弹、完全错过真正大 winner。

### 7.2 Missed gain to exposure

```text
missed_gain_to_exposure
```

问题是：

> 从 launch seed 到 probe / confirm signal，中间已经错过了多少涨幅？

这个指标防止模型等到股票已经涨太多才发出确认信号。一个 exposure schedule 如果短期 label 很好，但已经错过了 30% 到 50% 的启动段，就未必是想要的 timing。

因此，big winner 在新研究中的位置是：

- 作为 coverage constraint；
- 作为 missed-upside audit；
- 作为长期潜力保留审计；
- 不作为早期 exposure 的 primary prediction target。

## 8. 评价顺序

exposure timing 研究应该按以下顺序评价。

实施时不能只列评价维度，还需要粗略 go/no-go 门槛。否则后续评审会变成主观解释，重复 Explore10 中“结果能否继续推进”不闭合的问题。

### 8.1 Signal frequency

目标是低交易，因此首先看：

- 每年触发多少次；
- 每个 instrument-year 触发多少次；
- 每个 launch episode 是否最多一次 `probe_entry`、一次 `confirm_add`、一次 `fast_fail_exit`；
- 是否集中在少数股票、少数年份、少数行业。

如果频率过高，它就不是当前要找的 exposure schedule，而会退化成 daily alpha 或短线 TopK。

示例门槛可以先粗设为：

- 每个 launch episode 最多 1 次 `probe_entry`、1 次 `confirm_add`、1 次 `fast_fail_exit`；
- 每个 instrument-year 平均 probe 次数低于 0.5；
- 组合层 annual turnover 明显低于 daily BaseRate，具体阈值在 requirement 中冻结。

### 8.2 Short-horizon after-cost expectancy

主评价应看 probe / confirm 后 5d / 10d / 20d 的 after-cost 表现：

- mean / median return；
- hit rate；
- payoff ratio；
- drawdown before target；
- worst decile；
- benchmark-relative return；
- industry-relative return。

这里要明确：短周期正期望是 exposure timing 质量的主证据。

示例门槛可以先粗设为：

- primary 10d after-cost expectancy 为正；
- worst-year 不允许完全由单一年份贡献；
- 相对 launch-pool random exposure 的 lift 必须为正；
- 正收益不能只来自少数 instrument-year。

### 8.3 Fast-fail quality

看失败是否能快速暴露：

- fail rate；
- median days to fail；
- average loss at fail；
- tail loss；
- 是否减少长期无效持有；
- 是否减少进入明显失败结构的次数。

fast fail 如果不能减少坏 exposure，就没有实际价值。

示例门槛可以先粗设为：

- median days to fail 足够短；
- fail loss 的尾部小于 buy-all launch baseline；
- fast-fail 不能显著增加后续 big winner 的 false reject。

### 8.4 Big winner coverage

看长期大 winner 是否仍被保留：

- `big_winner_capture_rate`；
- 被错过的 winner 数；
- 被 fast fail 错杀但后续成为 winner 的比例；
- false reject 的收益影响。

示例门槛可以先粗设为：

- 相对全 launch pool 的 big-winner coverage 不应低于预注册比例；
- 如果 coverage 明显下降，必须由更低交易频率、更低回撤或更高 short-horizon expectancy 补偿；
- false reject winner 必须单独列出 case review。

### 8.5 Missed upside

看 exposure 是否太晚：

- launch 到 probe / confirm 的涨幅；
- launch 到 probe / confirm 的天数；
- probe / confirm 前已经发生的最大涨幅；
- probe / confirm 后剩余上行空间。

示例门槛可以先粗设为：

- `missed_gain_to_exposure` 中位数不能过高；
- confirm_add 不能主要发生在 launch 后已经大幅上涨的尾部确认阶段；
- 如果 short-horizon label 很好但 missed upside 很大，不能直接解释为有效 exposure timing。

### 8.6 Turnover and capacity

最后看组合层面是否符合低交易目标：

- annual turnover；
- average holding overlap；
- capacity proxy；
- cost drag；
- blocked order rate；
- cash drag。

## 9. 和 BaseRate 的关系

BaseRate 现在是宽基 ML 锚点。新的 exposure timing 研究需要回答：

> 这个低频 exposure timing schedule 是否比 BaseRate 更适合捕获启动事件中的可交易机会？

但当前阶段不能直接和 BaseRate 比组合收益，因为 EP2 exposure timing 还没有接完整 holding / exit，且 BaseRate 是日频 TopK 组合，没有 launch episode 概念，也没有 schedule-level expectancy。更合理的比较结构应分三层。

第一层：EP2 exposure timing vs launch pool random exposure。

- 同一个冻结 launch pool；
- 同一个 horizon；
- 同一个 next-open execution；
- 同一个 cost model；
- 同一个 fast-fail / label evaluation rule。

这层回答：exposure timing 本身是否比随机时点有价值。

第二层：EP2 exposure timing vs buy-all-on-launch baseline。

- 所有 launch episode 在 launch day 或固定可执行参考日买入；
- 与 EP2 exposure schedule 使用相同 horizon、成本、label 和 coverage audit；
- 用来判断 exposure timing 是否优于“看到 launch 就全买”。

第三层：EP2 strategy vs BaseRate。

- 只有当 EP2 后续接上明确 holding / exit 后才做；
- 当前阶段最多比较 signal frequency、turnover proxy、capacity proxy 和 short-horizon expectancy；
- 不应把当前 schedule-only 结果直接解释成组合层优于 BaseRate。

因此，当前阶段更合理的比较是：

- probe / confirm 后短 horizon 是否有更高 after-cost expectancy；
- signal 是否明显低频；
- bad exposure 是否更快失败；
- big winner coverage 是否可接受；
- turnover proxy 是否显著低于 daily BaseRate；
- 是否能作为后续 holding / exit 研究的入口。

也就是说，BaseRate 是背景锚点，不是 exposure timing 研究的直接替代。

## 10. 当前阶段不做什么

为了避免重新发散，当前 exposure timing 研究不应做以下事情：

1. 不直接训练 `120d big winner` 作为 primary exposure label。
2. 不从全市场每日 TopK 重新开始。
3. 不把 holding / exit 完整系统混入当前阶段。
4. 不用 OOS 结果反复挑 threshold。
5. 不把 failure / reject 解释成长期不会涨。
6. 不把短期高 hit rate 直接解释成 big winner 捕获能力。
7. 不忽略 missed-upside。
8. 不做高换手 daily trading 策略。
9. 不在 pool 未冻结时开始 exposure timing 模型训练。
10. 不把 schedule-only 结果直接和 BaseRate 组合年化收益比较。

当前阶段只回答一个问题：

> 是否存在一个低频、可执行、短期可验证的 exposure timing schedule，使得我们可以通过 probe 保留 winner optionality、通过 confirm_add 提高有效下注比例、通过 fast_fail_exit 限制失败 launch 损失，同时不明显牺牲 big winner coverage？

## 11. 建议的研究方向表述

可以把下一阶段研究方向定义为：

```text
在 frozen launch observation pool 中，寻找低频 next-open 可执行 exposure timing schedule。
该 schedule 不直接预测 120d big winner，而是通过 probe_entry / confirm_add / fast_fail_exit 安排 launch 后 exposure。
120d big winner 仅作为 coverage 和 missed-upside 审计。
fast_fail_exit 是 exposure validity 的一部分，但不扩展为完整 holding / exit 策略。
研究目标是在减少交易的前提下，提高短期 exposure 质量，并保留对最终 big winner 的捕获能力。
```

这个定义把问题从“早期预测长期终局”改成“安排更好的下注节奏”，也解释了为什么过去 failure / reject 比 winner launcher 更稳定：失败是近端状态，winner 是远端终局。exposure timing 研究应该站在近端可验证状态上，而不是要求模型在启动早期预测 120d 后的结果。

## 12. 实施前必须闭合的问题

这一节记录从讨论走向 requirement / implementation 时必须补齐的工程约束。

### 12.1 Freeze launch / observation pool

整篇研究依赖一个稳定的 launch / observation pool。没有 pool freeze，后续所有 exposure 指标都不可比。

必须先冻结：

- launch detector version；
- universe definition；
- industry membership as-of rule；
- price adjustment rule；
- volume / money availability rule；
- lookback windows；
- threshold；
- episode start / reset / end rule；
- duplicate episode merge rule；
- daily PIT episode dump schema。

冻结后的 pool 是 EP2 的唯一输入。exposure timing 研究期间不得重新定义 pool 来改善结果。

### 12.2 Label base-rate sweep before model training

`confirm_success_10d_12pct_before_6pct_drawdown` 是候选 primary label，不是默认锁死的最终 label。

实施第一步应先做 base-rate sweep：

- 不训练模型；
- 只在冻结 launch pool 上计算标签；
- 覆盖 5d / 10d / 20d；
- 覆盖多组 upside / drawdown 阈值；
- 输出正样本率、样本数、年份分布、行业分布、instrument-year concentration；
- 输出 same-day high/low ambiguity 占比；
- 明确 ambiguity policy 对 base rate 的影响。

如果某个标签正样本率过低、过高或过度集中，则不能作为 primary label。

### 12.3 Same-day high/low ambiguity policy

A 股 launch 后波动可能很大，同一天 high 达到 target、low 达到 stop 的情况不能假设先后顺序。

必须在 config 中固定一种 primary 处理方式，例如：

```text
same_day_target_and_stop_policy: conservative_fail
```

并至少输出 sensitivity：

- `conservative_fail`
- `drop_ambiguous`
- `target_first_optimistic`

primary 结论必须使用保守口径，乐观口径只能作为 sensitivity。

### 12.4 Go/no-go thresholds

requirement 落地时，每个评价维度都需要最低门槛：

- signal frequency；
- short-horizon expectancy；
- fast-fail quality；
- big-winner capture；
- missed-gain-to-exposure；
- concentration；
- turnover proxy；
- null lift。

门槛可以先粗，但必须预注册。否则实施完成后无法判断是继续、重做还是停止。

v0 requirement 应直接冻结一组初始 config，即使后续可以在新版本中修订：

```yaml
label_sweep:
  primary_selection_scope: pre_2024_core_research_years
  robustness_only_years: [2024, 2025]
  positive_rate_min: 0.20
  positive_rate_max: 0.55
  max_same_day_ambiguity_rate: 0.20
  max_top1_instrument_year_positive_share: 0.10

timing_gate:
  min_after_cost_lift_vs_random: 1.05
  max_big_winner_coverage_loss_vs_buy_all: 0.20
  max_median_missed_gain_to_exposure: 0.08
  max_top1_instrument_year_probe_share: 0.10
  max_top5_instrument_probe_share: 0.35
  min_turnover_reduction_vs_daily_baserate: 0.50
```

这些数值是 v0 guardrail，不是优化目标。实施时如果发现不合理，应该形成新 requirement 版本，而不是在当前实验结果出来后临时改门槛。

### 12.5 BaseRate comparison boundary

当前 schedule-only 阶段不直接和 BaseRate 比组合收益。

当前阶段的主要 baselines 应该是：

1. same-pool random exposure；
2. fair buy-all-on-launch；
3. simple delay exposure，例如 launch 后固定第 3 / 5 / 10 个交易日 probe。

BaseRate 只作为项目级锚点和后续组合层比较对象。只有接入 holding / exit 后，EP2 才能与 BaseRate 做完整 annual return / drawdown / turnover / cost comparison。

buy-all-on-launch 必须有公平版本，不能让 schedule 使用 fast-fail / horizon exit，而 buy-all 使用另一个默认持有周期。至少需要两版：

```yaml
buy_all_on_launch_hold_to_H:
  exposure_start: launch_next_open
  target_weight: 1.0
  exit: next_open_after_H_trading_days
  cost_model: same_as_schedule

buy_all_on_launch_with_same_fast_fail:
  exposure_start: launch_next_open
  target_weight: 1.0
  exit:
    - same_fast_fail_exit_as_schedule
    - otherwise_next_open_after_H_trading_days
  cost_model: same_as_schedule
```

第一版回答：分阶段 exposure 是否优于最朴素看到 launch 就全买。第二版回答：分阶段 sizing 是否比全仓加同样 fast-fail 更好。如果 schedule 只跑赢没有 fast-fail 的 buy-all，但跑不赢 `buy_all_on_launch_with_same_fast_fail`，说明价值主要来自 stop，而不是 exposure timing。

### 12.6 PIT contracts

必须单独定义 PIT contract，避免重复 Explore9 / Explore10 中容易出现的 leakage 风险。

需要明确：

- launch detector 不得使用未来 universe 或未来 industry membership；
- exposure feature as-of 必须早于 next-open execution；
- 如果某个指标需要 T 日 close 后才能计算，则最早只能用于 T+1 open decision；
- label 使用的 high / low / close 必须和 exposure reference price 使用同一套复权规则；
- episode reset 规则必须 PIT 单调，不能因为未来价格路径重写历史 episode；
- frozen pool dump 必须包含 `asof_date`、`signal_date`、`decision_date`、`execution_date`。

### 12.7 Episode-level dedup and split discipline

“一个 launch episode 最多 1 次主 probe / confirm / fail 动作”不仅是策略约束，也是训练和验证约束。

如果同一个 episode 在多个日期贡献高度相关样本，会污染 OOS 评估。因此必须：

- 定义 `launch_episode_id`；
- 定义 `exposure_candidate_id`；
- 定义 episode-level primary exposure selection rule；
- 训练和验证 split 不允许同一个 episode 跨 train / valid / test；
- split 必须按时间切，且 train / valid 之间设置 embargo（≥ primary horizon，例如 10 个交易日），避免相邻 episode 的 cross-section 泄漏；
- metric 同时输出 row-level 和 episode-level；
- primary metric 使用 episode-level dedup 后结果。

否则模型可能只是学到同一个 launch episode 的重复路径，而不是可泛化的 exposure timing。

## 13. exposure timing schedule 的最终主语

EP2 的正式研究对象应统一为 `low_turnover_launch_exposure_timing`，即"在 frozen launch pool 内安排低换手、next-open 可执行、短期可验证的 exposure schedule"。旧的单点确认框架只保留为被替换的早期讨论背景，不作为 requirement 标题、主问题或输出枚举。

但 P0.6 已经实证：等待确认类 trigger 的 missed-winner 非常高。最温和的 `hold_3d_close_above_ema20` 仍漏掉 91.9% 的 launch winner，更严格的 price hold / pullback / higher-low 条件会把 miss winner 推到 98%–99%。

这意味着如果 EP2 严格按 §3–§12 实施成"只有确认后才建立 exposure"，§7.1 `big_winner_capture_rate` 这个约束在机制层面**没有任何保护手段**，大概率会复现 P0.6 的失败模式。

### 13.1 研究对象 reframe

将研究对象彻底升级为：

```text
low_turnover_launch_exposure_timing
```

核心问题从"是否等待确认后才首次建立 exposure"改为"launch 后如何以低换手方式安排 exposure"。这允许三种动作：

- `probe_entry`：launch 后 next-open 小仓试探（例如 20%–30% 目标仓位），保留 winner optionality；
- `confirm_add`：5d / 10d 内出现 §5 confirm-validity 确认后加仓到目标仓位；
- `fast_fail_exit`：触发 §6 failure / reject 条件后退出或不再加仓。

这个升级同时回应了两个矛盾：

- 等确认 → missed winner 高（P0.6 证据）；
- 直接全买 → false positive 与回撤高；
- 分阶段 exposure → 先保留 capture optionality，再用短期确认决定是否加大下注。

### 13.2 与 §3 / §6 的范围声明的关系

§3 明确"暂时不研究完整 holding / exit"；§6 明确"fast fail 不是完整 exit 策略"。引入 probe / confirm_add / fast_fail_exit 实际上已经包含 **position sizing** 与 **partial exit** 两个 holding 元素，因此必须诚实标注范围扩展：

> EP2 范围扩展说明：exposure timing 包含 probe sizing 与 partial exit 两个 holding 元素，但**不研究** take-profit、trailing stop、再平衡、容量管理、组合层 cash drag 优化。完整 holding / exit 仍属 EP2 之后的工作。

§5 confirm-validity label 的角色随之变化：它不是"是否首次建立 exposure"的 trigger，而是 `confirm_add` 的 trigger。§6 fast-fail 是 `fast_fail_exit` 的 trigger。两者不再争夺同一语义，§5 与 §6 的概念重叠也由此解决。

### 13.3 turnover 的口径澄清

probe → confirm_add → fast_fail_exit 路径意味着每个 launch episode 最多 3 次交易（1 买 + 1 加仓 + 1 卖），而 §3 / §4 原本的 single-action exposure 形态每个 episode 最多 1 次。所以 "low turnover" 的口径必须明确：

- 对标对象是 **daily BaseRate** 的换手率，不是 "episode 内最少交易次数"；
- 评价指标使用 **annual turnover proxy**（组合层），不使用 trades-per-episode；
- 没有触发 confirm_add 也没有触发 fast_fail_exit 的 probe 仓位，必须在 EP2-2 baseline 阶段就定义自然退出规则，否则 baseline 跑不出来。

默认自然退出规则直接写死为：

```yaml
default_natural_exit:
  if: no_confirm_add_and_no_fast_fail_exit
  exit: next_open_after_H_trading_days
  primary_H: 10
  sensitivity_H: [20]
```

每个 schedule 都必须输出：

- `natural_exit_rate`
- `natural_exit_return`
- `natural_exit_median_days`

否则 `probe_with_simple_stop` 这类 baseline 会出现隐含无限持有。

## 14. 阶段化实施结构

把 §12 的"实施前必须闭合"显式排成有序阶段，每一步是否进入下一步由 go/no-go 决定，而不是默认推进。

### 14.1 EP2-0 Freeze launch / observation pool

只做 §12.1 的 pool freeze，不评价收益、不训练模型。

输出：

- `ep2_launch_observation_pool.parquet`
- `ep2_launch_episode_dictionary.csv`
- `ep2_pool_freeze_manifest.json`
- `ep2_pool_frequency_audit.csv`

输出 schema 必须满足 §12.6 的 PIT contract，至少包含 `asof_date / signal_date / decision_date / execution_date`。

进入 EP2-1 的 gate：pool 通过 PIT / asof / episode dedup 审计。

### 14.2 EP2-1 Label base-rate sweep

执行 §12.2 与 §12.3。primary 必须使用 §12.3 保守口径，乐观口径仅作 sensitivity。

进入 EP2-2 的 gate：

- 至少存在一组 `(horizon, upside, drawdown)` 标签 positive rate 落在可学区间（例如 20%–55%）；
- same-day ambiguity 占比不主导 label；
- 该标签的 instrument-year concentration 不过高；
- primary label **冻结**，EP2-2 / 3 / 4 不得重新挑选。如必须重挑，记为一次完整 EP2 重启，重启次数上限 1 次。

primary label 选择范围必须预先分开：

```yaml
label_primary_selection_scope: 2017_2023_core_research_years
robustness_only_years: [2024, 2025]
```

也就是说，primary label threshold 只能基于 2017-2023 的 core research years 冻结。2024 / 2025 只做 robustness，不参与 label threshold 选择，避免 label selection leakage。

### 14.3 EP2-2 No-model timing baseline（exposure 形态）

在不训练模型前提下，跑两类 baseline。

单点 exposure 基线（仅作为旧 single-action exposure 形态的对照）：

- `buy_all_on_launch_hold_to_H`
- `buy_all_on_launch_with_same_fast_fail`
- `fixed_delay_{1,3,5,10}d`
- `random_probe_within_launch_window`
- `first_valid_after_no_failure`
- `simple_confirmation`：close_above_launch_close / close_above_ema20 / volume_hold / no_break_launch_low

Schedule 形态基线（对应 exposure timing 形态，与 EP2-3 模型版同形态）：

- `staged_buy_all`：launch 当天 30%，T+5 再 30%，T+10 再 40%，无 fast-fail；
- `probe_then_naive_add`：probe 30%，T+10 不看条件直接加到 100%；
- `probe_with_simple_stop`：probe 30%，触发 -6% 全退，否则 T+10 加到 100%。

每条 baseline 都必须使用同一个 horizon / exit / cost 口径。primary H 与 primary label horizon 对齐，默认 H=10d；20d 仅作为 sensitivity。没有 confirm_add、没有 fast_fail_exit 的 probe 仓位，必须按 §13.3 的 `default_natural_exit` 在 H 日后 next-open 退出。

每条 baseline 都必须输出 §8.1 – §8.6 全部维度，并额外输出：

- `natural_exit_rate`
- `natural_exit_return`
- `natural_exit_median_days`
- `buy_all_hold_to_H_comparison`
- `buy_all_same_fast_fail_comparison`

进入 EP2-3 的 gate（综合 §8 与外部评审三档判定）：

- 至少有一条 schedule baseline 相对 same-pool random exposure 有正 after-cost lift；
- 相对 `buy_all_on_launch_hold_to_H` 和 `buy_all_on_launch_with_same_fast_fail` 都不明显牺牲 big-winner coverage；
- median `missed_gain_to_exposure` 不过高；
- signal frequency 明显低于 daily BaseRate；
- episode-level top instrument / top instrument-year 不集中。

如果 schedule baseline 完全跑不赢 `buy_all_on_launch_hold_to_H`、`buy_all_on_launch_with_same_fast_fail` 与 random exposure，**直接停止 EP2，不进入 EP2-3**。

如果 schedule 只跑赢 random exposure，但跑不赢任一公平 buy-all-on-launch baseline，也必须停止或重写 EP2。EP2 如果不能打赢 buy-all-on-launch，就不能证明 timing 有价值。

### 14.4 EP2-3 Hazard timing model（条件开启）

仅当 EP2-2 gate 通过时启动。

不使用普通 binary LGBM。第一版限定为 **discrete-time three-class softmax**：每天预测 `target_first / stop_first / neither` 三类概率，输出：

```text
score_probe_day =
    P(target_before_stop_within_H)
  - lambda * P(stop_before_target_within_H)
  - mu * missed_upside_penalty
```

以 episode-level first valid day 作为主 probe 触发。

first valid day 必须有明确冲突优先级，避免模型用后段确认日"补票"：

```yaml
episode_primary_probe_day:
  search_window:
    start: launch_effective_date
    end: launch_effective_date + max_probe_window
  valid_if:
    - score_probe_day >= threshold
    - no_fast_fail_has_occurred
    - missed_gain_to_exposure <= max_missed_gain
  if_multiple: earliest_valid_day_only
  if_none: no_probe
```

如果同一天 `target_first / stop_first / neither` score 冲突，primary rule 使用 `score_probe_day` 排序，且 `P(stop_before_target_within_H)` 超过预注册风险阈值时强制判为 invalid day。`first valid day` 如果晚于 `max_probe_window` 或 `missed_gain_to_exposure` 超过阈值，则该 episode 记为 `no_probe`，不能用后段确认日补票。

明确禁止（避免 EP2-3 失控）：

- 不直接上 Cox / Fine-Gray competing-risk 模型（A 股 small-pool 下 censoring 独立性假设不成立）；
- 不做 path-to-primitive；
- 不做 leaf rule extraction；
- 不做行业专用 LGBM；
- 不做 20–40 个 CSV gate；
- 不做复杂 FDR / null family（保留 §12.5 的 same-pool random / fixed-delay null 即可）；
- 不做 full strategy annual return（无 holding / exit 时无意义）。

### 14.5 EP2-4 Exposure schedule + BaseRate-overlap bridge（条件开启）

仅当 EP2-3 hazard score 相对 EP2-2 schedule baseline 有可验证 lift 时启动。

任务：

- 把 hazard score 装配成 probe / confirm_add / fast_fail_exit 完整 schedule；
- 输出与 EP2-2 schedule baseline 同口径的对比；
- 完成 BaseRate-overlap bridge audit（仅前 3 个问题）：
  1. EP2 launch pool 中有多少事件也被 BaseRate TopK 命中？
  2. EP2 exposure signal 是否出现在 BaseRate 高分区域？
  3. EP2 exposure schedule 是否提供 BaseRate 没覆盖的低频机会？

剩余两个组合层归因问题（fast-fail 解释 BaseRate 亏损 / 是否重复加仓）推迟到 EP2 之后的完整 holding / exit 阶段。

### 14.6 三档判定与停止 / 重写规则

**允许进入 EP2-3** 当且仅当 §14.3 gate 全部满足。

**允许进入 EP2-4** 当且仅当：

1. exposure / probe signal 相对 same-pool random exposure 有正 after-cost lift；
2. 相对 `buy_all_on_launch_hold_to_H` 与 `buy_all_on_launch_with_same_fast_fail` 不明显牺牲 big-winner coverage；
3. median `missed_gain_to_exposure` 不过高；
4. fast-fail 明显减少坏 exposure 的尾部损失；
5. signal frequency 明显低于 daily BaseRate；
6. episode-level concentration 不过高。

**必须停止或重写 EP2** 当出现：

1. exposure 成功主要来自同一年度 / 少数 instrument-year；
2. signal 太高频，退化成 daily alpha；
3. short-horizon expectancy 为正但 `missed_gain_to_exposure` 很大；
4. fast-fail 错杀大量后续 winner；
5. exposure timing 只跑赢 random，但跑不赢 `buy_all_on_launch_hold_to_H` 或 `buy_all_on_launch_with_same_fast_fail`；
6. 需要反复改 label threshold 才能成立（违反 §14.2 label freeze）。

## 15. 进入 requirement 前必须完成的工程基座

§14 描述的是研究阶段，但在写 requirement 之前还有一层更基础的工作：把 EP2 的"工程基座"先搭出来。没有这层基座，requirement 写得再细也只是研究愿景，无法落成可执行合同。

具体只需要 4 个基座，**不要急着写模型、hazard、EP2-3**。

### 15.1 Frozen launch / observation pool builder

最先做。没有它，后面所有 exposure timing 都不可比。

需要产出一个可重复生成的 frozen pool：

- 固定 universe：用现在 canonical `data/` 下的 PIT universe；
- 固定 price / volume / money / industry as-of 口径；
- 固定 launch detector 版本；
- 固定 episode start / reset / end / merge 规则；
- 输出 `launch_episode_id`；
- dump 成唯一输入：
  - `ep2_launch_observation_pool.parquet`
  - `ep2_launch_episode_dictionary.csv`
  - `ep2_pool_freeze_manifest.json`
  - `ep2_pool_frequency_audit.csv`

最关键的是：**先决定 launch detector 的机械定义**。否则 requirement 写得再细，实施时也会卡在"什么算 launch"。

### 15.2 PIT data access layer / audit layer

EP2 强依赖 PIT 正确性，需要一个小的数据读取与审计基座。

至少要能稳定读：

- PIT universe；
- daily open / high / low / close / volume / money；
- industry membership as-of；
- trading calendar；
- next-open executable date / price；
- limit / zero-volume / missing-open block flags。

同时输出 audit：

- feature / signal / decision / execution date 是否单调；
- universe 是否未来泄漏；
- industry 是否未来泄漏；
- price adjustment 是否一致；
- episode 是否被未来路径重写；
- missing / suspended / limit rows 占比。

可以复用 BaseRate 的 `data/` 与 execution audit 思路，但 EP2 要加 episode-level as-of 检查。

### 15.3 Label and path evaluator

写 requirement 前需要确认 label sweep 能被机械计算。

先实现一个不训练模型的 evaluator：

- 输入 frozen launch pool；
- 对每个 candidate / probe day 计算 future path；
- 支持 horizon: 5d / 10d / 20d；
- 支持 upside target: 8 / 10 / 12 / 15%；
- 支持 drawdown barrier: 4 / 6 / 8%；
- 支持 same-day high/low ambiguity policy:
  - `conservative_fail`
  - `drop_ambiguous`
  - `target_first_optimistic`
- 输出 positive rate、样本数、年份分布、行业分布、instrument-year concentration。

这一步的目标不是选最优 label，而是确认：**这个研究有没有可学的短 horizon confirm label**。如果 base rate 全部极端，requirement 阶段就应该停止或重写。

### 15.4 No-model baseline simulator

模型之前，先把 EP2-2 baseline runner 做出来。

至少支持：

- `buy_all_on_launch_hold_to_H`
- `buy_all_on_launch_with_same_fast_fail`
- `fixed_delay_{1,3,5,10}d`
- `random_probe_within_launch_window`
- `staged_buy_all`
- `probe_then_naive_add`
- `probe_with_simple_stop`

必须统一：

- same frozen pool；
- same next-open execution；
- same cost model；
- same H horizon；
- same natural exit；
- same fast-fail rule；
- same blocked execution logic。

输出：

- after-cost return；
- `natural_exit_rate / return / median_days`；
- `fast_fail_rate`；
- `big_winner_capture_rate`；
- `missed_gain_to_exposure`；
- turnover proxy；
- concentration；
- comparison vs random exposure；
- comparison vs both buy-all baselines。

这个 baseline simulator 是进入正式 requirement 的现实门槛。如果 no-model schedule 完全打不赢 buy-all / random，EP2 不应该进入模型阶段。

### 15.5 建议实施顺序

```text
ep2/scripts/build_launch_pool.py        # §15.1
ep2/scripts/audit_ep2_pit_inputs.py     # §15.2
ep2/scripts/sweep_confirm_labels.py     # §15.3
ep2/scripts/run_no_model_baselines.py   # §15.4
```

做到这一步后再写 requirement 才会扎实。否则 requirement 会继续停留在研究愿景，而不是可执行合同。

## 16. 下一步

工程基座（§15）完成后，再产出第一版 requirement，且仅承诺 EP2-0 / EP2-1 / EP2-2，不预先承诺 EP2-3 / EP2-4，由 gate 决定是否开启。

requirement 文件名建议：`ep2/EP2_low_turnover_launch_exposure_timing.md`。`ep2/discussion.md` 保留为历史 context，不删。
