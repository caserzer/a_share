# Episode 19 结题报告：PIT 入场宇宙、双尾暴露与方向性 Alpha 研究重启

## 0. 正式结题裁决

本报告正式关闭 Episode 19 的主动研究主线：

```text
episode_id = 19_entry_universe_pit_tradability_preflight
closure_date = 2026-07-10
closure_state = EP19_closed_entry_enrichment_only_no_tradeable_alpha_path
closing_phase = 19B3_b2_positive_exposure_left_tail_budget_frontier
closing_decision_state = 19B3_forward_oos_underpowered_not_pass

highest_supported_claim = B2_right_tail_exposure_with_two_tailed_burden_diagnostic
residual_alpha_supported = false
tradeable_entry_supported = false
static_t0_suppressor_mainline_closed = true
next_requirement_within_ep19 = none

frozen_19B3_future_monitoring_allowed = true
frozen_19B3_active_research_priority = dormant
validation_outcome_read_for_19B3 = false

19C_replay_authorized = false
EP20_policy_preflight_authorized = false
model_training_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

这里的 `positive exposure` 是 EP19 的操作性术语：候选集相对同期 eligible universe 更容易出现
`MFE_120 >= +50%`。它不是 CAPM beta 的估计，也不等于独立因子 alpha、可实现收益或可交易策略。

EP19 的最终判断是：我们已经能够用 PIT、next-open executable、cooldown 后的真实候选分母研究入场，
也找到了一个具有稳健右尾 exposure 的 B2 family；但 B2 同时显著放大左尾，且 matched baseline 无法支持
residual attribution。后续静态 T0 suppressor 只能沿“少一点左尾、也少一部分右尾”的同一前沿移动，
没有把 B2 转化为可交易 entry alpha。EP19 因而不再继续写 19B4、19C 或 policy preflight。

## 1. Executive summary

EP19 留下六条需要同时保留的结论：

1. **入场研究的统计地基成立。** 19A 建立了无 winner hindsight、PIT membership、after-close decision、
   next executable open、fill feasibility、cooldown、120-session label、split 和 outcome-access 边界。
2. **B2 的右尾 exposure 成立。** robustness 上 B2 的 +50% MFE 概率为 `28.03%`，同期 eligible universe
   为 `21.04%`，delta `+6.98pp`，ratio `1.3319`，cluster-bootstrap CI 为 `[4.48pp, 9.70pp]`。
3. **B2 不是已确认 alpha。** 所有 original/repaired matched baseline 的 common support 或 balance 均失败，
   residual attribution unresolved；不能把 eligible-universe exposure 写成因子 alpha。
4. **B2 是双尾放大器。** B2 的 `MAE_20 p10=-22.88%`，比 eligible universe 的 `-13.61%`
   恶化 `9.27pp`；fast-fail rate 为 `48.90%`。右尾越强的区域也包含大量左尾样本。
5. **静态风险过滤没有创造方向。** VOL60 top30 trim 能压低左尾，却同步删除 `35.40%` 的 +50% 右尾事件；
   full-capital/cash 口径的 120-session 历史均值从 `10.89%` 降到 `6.70%`。它是风险压缩，不是 alpha 提升。
6. **当前没有新的 forward OOS。** 19B3 在 outcome read 前 fail closed，forward candidate 为 0，validation
   未读取。因此 R2 既没有失败，也没有获得支持；它只能作为冻结的未来监控器，而不是当前研究主线。

核心研究洞察是：EP1–EP19 反复寻找的许多“event”，更容易识别**收益分布尺度**，而不是**条件均值方向**。
如果一个特征主要把波动率放大，那么它会同时产生更多大赢家和更厚左尾；随后用同一组波动率变量做过滤，
只能缩小分布，不能凭空产生方向性 alpha。

## 2. EP19 回答了什么问题

EP18 在 realized-winner 条件化宇宙中证明了 payoff representation，却没有得到正 utility，也没有解决真实入场。
EP19 因而把研究对象切换为：

```text
能否在任何 winner outcome 被观察之前，构造一个 PIT-valid、可成交、无 hindsight 的候选入场宇宙，
并证明该宇宙相对同期可交易机会具有稳健右尾富集、可接受的假阳性与左尾负担？
```

这不是“预测谁最终上涨 50%”的普通分类任务。完整证据链要求：

```text
PIT / tradability contract
    -> train-only family selection
    -> held-out robustness right-tail exposure
    -> matched/residual attribution
    -> false-positive and left-tail burden
    -> concentration / effective support
    -> independent forward confirmation
    -> validation stress veto
    -> replay / utility
```

EP19 走到了“held-out right-tail exposure + burden diagnosis”，但没有跨过 residual attribution、burden、
independent forward 和 utility，因此不能授权策略。

## 3. Phase decision ledger

| Phase | 决策状态 | 主要发现 | 对结题的含义 |
|---|---|---|---|
| 19A | `19A_entry_universe_contract_ready` | PIT、next-open、fill、cooldown、split、label 与 outcome boundary 冻结完成 | 入场研究地基可复用，但不证明信号有效 |
| 19B0 | `19B0_candidate_family_eligible_for_19B` | train-only grid 选择 B2、B5 进入 robustness | 只完成候选选型 |
| 19B | `19B_false_positive_burden_blocked` | B2 positive exposure pass；B5 fail；B2 burden/top-k fail | 最高只能 enrichment-only diagnostic |
| 19B1 | `19B1_t0_left_right_tail_separable_diagnostic` | 左尾与 clean right-tail 在 T0 特征上可分 | 只生成 suppressor 假设，不授权规则 |
| 19B2 | `19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic` | 简单 ATR/VOL 单因子压过交互 suppressor | high-vol×extension 没有独立交互优势 |
| 19B3 | `19B3_forward_oos_underpowered_not_pass` | arm、placebo、泄漏边界已冻结；forward 样本为 0 | 没有新支持，不读取 validation，不进入 19B4 |

## 4. 19A：真正的正成果是可审计的入场分母

19A 的意义不是产生信号，而是把此前 winner-first 研究中最危险的 hindsight 条件化移除。EP19 的 primary
denominator 是真实 candidate entry rows，不是 realized-winner episode steps。

冻结的关键约束包括：

- 决策时点为当日收盘后，只允许使用 decision date 当时可知的字段；
- 入场锚为 next executable open，停牌、ST、历史不足、不可成交 next-open 均需显式处理；
- 同一 instrument 的重复事件执行 frozen cooldown，不能用 raw trigger count 夸大样本量；
- `MFE_120`、`MAE_20` 与 fixed-horizon return 均从可执行入场价重建；
- family/grid、baseline budget、multiple testing、purge/embargo、validation veto 与 outcome access 均在读数前冻结；
- validation 只允许压力测试和否决，不能用于选择、确认或补足 forward 样本。

这一套 contract 是 EP19 最可复用的工程资产。后续 OHLCV alpha 研究应复用其 PIT、execution、cooldown、
lineage 和 outcome-access 纪律，但不能复用 EP19 的 MFE-only success definition。

## 5. 19B：B2 有右尾 exposure，但不是可交易 alpha

### 5.1 B2 与 B5 的 robustness 结果

| family | candidate n | instrument n | p(+50 MFE) | eligible p(+50 MFE) | delta | ratio | positive gate | 最终 cell state |
|---|---:|---:|---:|---:|---:|---:|---|---|
| B2 relative-strength breakout | 1,552 | 524 | 28.03% | 21.04% | +6.98pp | 1.3319 | pass | `false_positive_burden_blocked` |
| B5 recent-high + amount expansion | 2,983 | 749 | 22.70% | 21.04% | +1.65pp | 1.0785 | fail | `robustness_not_supported` |

B2 的 cluster-bootstrap delta CI 为 `[4.48pp, 9.70pp]`，p-value=`1.14e-07`，说明 positive exposure
并非纯粹的 train 过拟合读数。B5 的 CI 穿过 0，且未通过 Sidak-adjusted gate，因此关闭。

### 5.2 residual attribution 为什么 unresolved

B2/B5 的 calendar、instrument、liquidity-size-volatility matched baselines 及两类 repair variants 均未通过
质量门。B2 各方案的最低 max standardized mean difference 仍为 `0.7781`，远高于 `0.10` 门槛；
common support 与 covariate balance 不足。

因此以下两种说法都不成立：

```text
错误说法 A：B2 已证明独立 alpha。
错误说法 B：matched sample 的 +50% rate 更高，所以 B2 已证明负 alpha。
```

正确边界是：B2 相对同期 eligible universe 有右尾 exposure，但该 exposure 究竟来自市场/行业/规模/
流动性/波动暴露，还是独立方向信息，EP19 没有可靠识别。

### 5.3 决定性阻断来自左尾

| family | +50 winner rate | non-winner rate | candidate / winner | fast-fail rate | MAE20 p10 | eligible MAE20 p10 | worsening |
|---|---:|---:|---:|---:|---:|---:|---:|
| B2 | 28.03% | 71.97% | 3.57 | 48.90% | -22.88% | -13.61% | 9.27pp |
| B5 | 22.70% | 77.30% | 4.41 | 46.53% | -20.63% | -13.61% | 7.02pp |

B2 的 right-tail lift 随 threshold 增强：+20%、+30%、+50%、+100% 的 eligible-universe lift 分别约为
`1.09x / 1.20x / 1.33x / 1.58x`。但在等量 eligible sample 诊断口径下，-10%、-20%、-30%
MAE burden lift 约为 `2.39x / 5.59x / 8.86x`。B2 更准确的分类不是“entry alpha”，而是：

```text
right_tail_reservoir + two_tailed_volatility_amplifier
```

## 6. 19B1/19B2：左右尾可分，但没有可晋级的静态修复

### 6.1 四组结构

B2 robustness primary denominator 的 1,552 行分为：

| outcome group | n | 含义 |
|---|---:|---|
| right_clean | 290 | `MFE_120 >= +50%` 且没有 `MAE_20 <= -10%` |
| both | 145 | 同时经历 +50% 右尾与 -10% 左尾 |
| left_bad | 614 | 左尾坏样本且不属于 clean right-tail |
| neither | 503 | 两类尾部都不满足 |

19B1 找到四个方向稳定的 T0 separability features：

| feature | oriented AUC: left_bad vs right_clean | 左尾方向 | 解释 |
|---|---:|---|---|
| VOL60 | 0.6264 | 越高越坏 | 最强单变量，但不是 winner selector |
| ATR20% | 0.6147 | 越高越坏 | 日内/短期 range 风险 |
| return60 | 0.5936 | 越高越坏 | 过强延伸伴随风险 |
| close / EMA60 distance | 0.5888 | 越高越坏 | 趋势延伸程度 |

这些 AUC 证明“左尾风险有统计结构”，但没有证明“删除高风险行后资本收益提高”。`both=145` 也说明部分
大赢家路径本身会先经历显著回撤；用 outcome-observed 的路径顺序无法反向生成 T0 membership。

### 6.2 交互 suppressor 为什么关闭

19B2 的最佳 primary interaction `B_vol60_80_ret60_80`：

```text
left_bad_removed_per_right_clean_removed = 3.30
right_clean_kept_rate = 0.897
MAE20 p10 improvement vs S0 = +0.0128
```

但相近删除预算下，简单 `A_ATR20_top10` 的效率为 `4.50`，right_clean kept=`0.931`，并给出更高的
`p_candidate_50_after=0.2828`。所有 interaction/basis variants 均未超过简单单因子 comparator，
`interaction_superiority_gate=fail`。

结论不是“波动率没用”，而是“复杂的 high-vol×extension 交互没有带来增量”；继续扩展相似静态网格
只会增加研究自由度。

## 7. 19B3 spent-design 前沿：左尾改善不等于收益改善

### 7.1 冻结 arm 的历史设计读数

下表只来自已经消费的 2024-01-02 至 2025-11-26 robustness 数据，角色是 design-only，不能贡献
19B3 forward support：

| arm | retained / 1,552 | +50 右尾 capture | ES10 | MAE20 p10 | P(MAE20 <= -20%) |
|---|---:|---:|---:|---:|---:|
| R0 untrimmed | 1,552 | 100.00% | 29.51% | -22.88% | 14.76% |
| R1 ATR20 top10 trim | 1,393 | 90.57% | 27.94% | -21.73% | 12.78% |
| R2 VOL60 top30 trim | 1,082 | 64.60% | 26.07% | -19.99% | 9.98% |
| R3 continuous vol budget | 1,552；gross 988.9 | 58.00% | 27.46% | -21.39% | 11.75% |

R2 相对 R0：ES10 改善 `3.43pp`，MAE p10 改善 `2.89pp`，-20% 左尾概率相对下降 `32.35%`，
代价是删除 `30.28%` 候选和牺牲 `35.40%` 的 +50% 右尾。R3 gross 更低，却在左右尾指标上同时
落后于 R2；36 个 continuous feasibility variants 没有一个联合通过设计门。因此 R3 不再承担救活角色。

### 7.2 固定持有收益审计

为避免把 MFE 当成可实现收益，本报告补充同一 spent B2 denominator 的 120-session fixed-hold 读数：

```text
entry  = next executable open
exit   = close[entry_session + 119]
return = exit_close / entry_open - 1
R2     = q_vol60 < B2 candidate p70；被删除的 470 行保持现金收益 0
cost   = 未扣交易成本
role   = spent-design economic diagnostic，不是 backtest 或 support
```

| 指标 | R0 全部 B2 | R2 retained 条件口径 | R2 full-capital / cash 口径 |
|---|---:|---:|---:|
| candidate / active n | 1,552 | 1,082 | 1,082 active + 470 cash |
| mean 120-session return | 10.89% | 9.60% | 6.70% |
| median | -0.53% | +0.25% | 不适用：含现金质量 |
| positive rate | 48.90% | 50.55% | 不适用：含现金质量 |
| p10 | -28.57% | -25.62% | 不适用：混合分布 |
| p90 | +59.56% | +52.10% | 不适用：混合分布 |

R2 的 retained 条件均值比 R0 低 `1.29pp`；按原始 1,552 unit capital、被删除部分留现金计算，均值比
R0 低 `4.20pp`。虽然 median、positive rate 和 p10 改善，但 p90 与均值下降，说明 R2 在缩小收益分布，
而不是提高方向性期望收益。该读数未处理同时持仓竞争、资金容量、交易成本和组合 NAV，不能被写成策略回测；
但它足以阻止把“左尾压低”直接解释为“预期收益提高”。

## 8. 19B3：为什么没有新的 OOS 结论

现有 qfq、top-N executable universe 与 benchmark 数据均止于 `2026-05-29`。robustness 最后决策日为
`2025-11-26`，其 120-session outcome path 恰好延伸到数据终点。19B3 还要求 20-session embargo，
然后才允许形成新决策，再等待完整 120-session path。

```text
spent robustness last decision = 2025-11-26
spent robustness path end = 2026-05-29
effective forward start = not_yet_observed
forward candidate n = 0
forward outcome read count = 0
validation outcome read count = 0
minimum additional sessions for first label-complete row = 141
```

19B3 的 primary、incremental、right-tail、placebo、bootstrap、month stability、concentration 与 absolute burden
gates 全部是 `not_evaluated`；唯一的 `support_gate=fail` 来自样本为 0。validation 仍是 stress-test-only，
没有被用来补样本或救结论。

所以：

- 不能说 R2 已被 forward 否定；
- 不能说 R2 已证明能压低未来左尾；
- 不能用 spent robustness 的数值填入 forward 栏位；
- 不能读取 validation 作为替代 OOS；
- 可以保留完全冻结的 19B3，在未来满足全部 evaluability floors 后机械重跑。

但“等待 19B3 数据”不再占用主动研究主线，因为即使历史 R2 效果复现，它更可能证明风险压缩，而不是
当前项目真正缺失的方向性 alpha。

## 9. EP19 的因果收口

### 9.1 为什么反复出现左右尾同步上升

EP19 与此前 episode 共同暴露了同一结构：

```text
breakout / extension / volume expansion / high recent return
    -> 更高 ex-ante volatility 与更宽 future path distribution
    -> 更多 +50% MFE
    -> 同时更多 -10%/-20% MAE
```

`MFE_120 >= +50%` 是“路径上曾经达到过上界”，不是“固定持有最终获得 +50%”。当 success metric 主要奖励
上界触达时，高波动天然提高命中概率，即使条件均值没有改善。随后按 VOL/ATR 删除高风险区域，会机械降低
两侧尾部；这是一条 scale frontier，不是 drift discovery。

### 9.2 为什么 separability 仍然没有 utility

19B1 证明 left_bad 与 right_clean 可分，只回答：

```text
P(left_bad | X_t0) 是否随某些 T0 feature 变化？
```

真正的资本问题则是：

```text
E[fixed-horizon net return | keep, X_t0]
- E[fixed-horizon net return | cash/baseline]
是否提高，并且是否覆盖被删除右尾的机会成本？
```

这两个 estimand 不同。一个风险分类器可以改善 precision、median 或 drawdown，却因误删少数厚右尾样本而降低
均值。EP16、EP18 与 EP19 的 utility failure 具有相同经济结构：规避的负样本收益不足以覆盖牺牲的正样本机会。

### 9.3 EP19 关闭的不是所有 OHLCV 研究

EP19 关闭的是：

- 继续扩大 B2/B5 一类静态 event grid；
- 把 MFE precision 当作方向性 alpha；
- 在同一高波区域里继续调 hard trim / smooth weight；
- 用 validation 或已消费 robustness 选择新 suppressor；
- 在 residual attribution 与 full-capital utility 未通过前进入 replay/policy。

EP19 没有关闭的是：

- 独立于 Big Winner event 的横截面 OHLCV 因子复制；
- 对市场/行业/规模/流动性/波动暴露做显式 residualization；
- 使用 fixed-horizon return 和 first-hit ordering 区分 drift 与 scale；
- 将低波动、择时和 CNN 分别放在正确的研究层级。

## 10. 后续研究总纲：从 event-first 切换到 directional-alpha-first

建议下一 Episode 若按编号连续，定义为：

```text
proposed_episode_id = 20_ohlcv_directional_alpha_replication
restart_type = topic_level_human_research_restart
authorization_source = human_direction_change_not_EP19_pipeline
primary_object = cross_sectional_directional_return_signal
primary_outcome = fixed_horizon_net_return_not_MFE
```

它不是 EP19 自动授权的 `EP20 policy preflight`，也不是 19B4。第一目标不是找可交易策略，而是建立一个
能够被本地证伪的 OHLCV 方向性 alpha 基线。

后续研究按四层组织：

| 层级 | 研究对象 | 正确角色 | 禁止的误读 |
|---|---|---|---|
| Directional alpha | TrendPV、Residual Momentum | 核心候选 | 不能用 MFE lift 替代 fixed-return alpha |
| Path quality | Frog-in-the-Pan / trend clarity | drift-vs-jump 诊断与有限交互 | 不能单独当 entry event 扫描 |
| Risk/exposure | Low Vol、MA timing | 仓位、风险预算、portfolio overlay | 不能把降波动写成 alpha |
| Representation oracle | OHLCV image CNN | 判断手工特征是否遗漏非线性信息 | 不能只凭 AUC/Sharpe 跳过成本与 OOS |

## 11. 详细后续研究计划

### 11.1 Phase 20A：Paper-native replication contract

目标：先回答“公开研究中的方向性因子，能否在本地 PIT A 股宇宙中按原定义复现”，不接 Big Winner label。

最小 arms：

```text
A0 = eligible-universe equal-weight / calendar-matched baseline
A1 = simple total momentum baseline
A2 = TrendPV exact-paper replication
A3 = residual momentum, market-residual primary
A4 = low-volatility factor comparator, risk benchmark only
```

要求：

1. 先逐项提取论文原始形成期、调仓频率、价量输入、standardization、portfolio construction 和持有期，
   形成 formula registry；不得边看本地结果边改论文定义。
2. 同时报告 paper-native long-short replication 和 A 股可实现的 long-only/full-capital 版本。只有 long-short 成立、
   long-only 不成立时，状态只能是 `factor_replication_only_no_entry_path`。
3. primary 调仓频率跟随论文；若论文为月频，不能为了增加样本把日频重叠行当独立 observation。
4. primary return 使用 paper-native fixed horizon；20/60/120-session return 只作为预注册 bridge sensitivity。
5. entry 继续使用 after-close decision -> next executable open；成本、停牌、涨跌停、ST、history readiness 延续 19A。
6. 行业残差需要独立 PIT membership contract。当前行业 source 若不能证明 as-of membership，
   `market+industry residual momentum` 只能 diagnostic，不得进入 primary。

20A 必须先建立 replication，而不是直接寻找最优组合权重。

### 11.2 Phase 20B：Scale-vs-drift decomposition

只有 A2 或 A3 至少一个在历史本地复制中显示稳定方向后，才进入 20B。

20B 研究问题：

```text
在匹配或残差化 ex-ante volatility、market beta、size、liquidity、recent return 后，
TrendPV / residual momentum 是否仍提高固定持有超额收益，且不是只扩大上下尾？
```

强制读数：

- `forward_return_20/60/120` 与 benchmark-relative return；
- mean、median、positive rate、p10、ES10、p90；
- full-capital return：未入选资金留现金或基准，不只报 selected-row conditional mean；
- turnover、commission、slippage、stamp tax 与 blocked fill；
- market beta、size、liquidity、VOL60、ATR20 与行业暴露；
- volatility-matched 与 return-matched comparator；
- 上下 barrier first-hit ordering，而不是只报 MFE/MAE 是否曾触达；
- instrument、instrument-month、decision-month concentration 和 cluster bootstrap。

建议 primary estimand：

```text
net_full_capital_fixed_horizon_return_lift
    = candidate portfolio net fixed-horizon return
    - calendar-matched eligible baseline net fixed-horizon return
```

MFE50、MFE100、Big Winner recall 只保留为右尾解释指标，不能成为 promotion gate。

建议 gate 结构在 requirement 中于 outcome read 前冻结：

```text
direction_gate:
    full-capital net return lift > 0
    and instrument-cluster bootstrap CI_low > 0

scale_independence_gate:
    volatility-matched / residualized return lift > 0
    and right-tail lift is not accompanied by predeclared excessive ES10 worsening

economic_gate:
    effect exceeds frozen transaction-cost and research-effect floor
    and survives leave-one-month/quarter-out stability

concentration_gate:
    no single instrument, month or regime explains the result
```

具体 effect floor 应在新 requirement 中依据交易成本和最小经济价值直接冻结，不能用 EP19 已消费 outcome
反推一个刚好通过的阈值。

### 11.3 Phase 20C：FIP / trend clarity，只做有限增量检验

Frog-in-the-Pan 的角色是区分“渐进漂移”和“离散跳跃”，不是再造一个独立事件网格。

允许的 pre-outcome formation-path 特征可以包括：

- 正收益日占比与 signed return continuity；
- formation return 中 top-1/top-3 日贡献占比；
- jump concentration / return entropy；
- realized path roughness、drawdown frequency；
- 价量一致性与 TrendPV score stability。

只允许最多两个预注册增量比较：

```text
C1 = best supported directional alpha arm
C2 = C1 + one frozen FIP/trend-clarity quality term
C3 = C1 + one frozen jump-concentration penalty
```

检验必须在相同 directional-score bucket、相同 volatility bucket 内比较。若 A2/A3 standalone 不成立，
禁止用 FIP interaction 做大规模 rescue search。

### 11.4 Phase 20D：Low Vol 与 MA timing 降级到风险层

Low Vol 单独回答“风险调整后持有哪些股票”，不直接回答“何时进入大赢家”。因此它应提供：

- independent low-vol factor baseline；
- 对已支持 alpha sleeve 的 target-vol sizing；
- 风险预算与最大 gross/cash 约束；
- alpha-on / alpha-off 状态下的 exposure stability。

MA timing 只允许作为 portfolio/regime overlay：例如对完整 alpha sleeve 的 gross exposure 做一个冻结的风险开关。
它不能改变 individual-stock membership，也不能在同一 outcome 上选择均线长度。

报告必须同时给出 conditional active return 和 full-capital/cash return，防止再次出现“留下的股票更稳，
但总资本期望收益更低”的错觉。

### 11.5 Phase 20E：OHLCV image CNN 作为 representation oracle

只有在 paper-native 手工因子已完成严格复制后，才考虑 CNN。目的不是立即生产模型，而是回答：

```text
日频 OHLCV 中是否存在 TrendPV、momentum、FIP、volatility 等手工特征没有捕获的非线性方向信息？
```

约束：

- 与 20A/20B 使用完全相同的 PIT universe、decision dates、entry、labels、costs 和 split；
- image construction 只能读取 T0 及以前数据；
- architecture/hyperparameter search 只在 discovery data 内完成；
- CNN 与手工因子必须比较相同 full-capital net-return estimand，不只比较 classification AUC；
- turnover/capacity/blocked fills 必须进入最终读数；
- validation/forward 不得用于选择 image window、resolution、network depth 或 ensemble。

决策解释：

| 结果 | 含义 | 下一步 |
|---|---|---|
| 手工因子成功，CNN 无增量 | 简单方向结构已足够 | 优先简单因子，停止复杂表征 |
| 手工因子失败，CNN 成功 | 存在 representation gap | 再研究可解释压缩与稳定性，不直接部署 |
| 两者都失败 | 日频 OHLCV 缺少可用方向信息 | 关闭静态 OHLCV entry 主线，转向替代数据/更高频/基本面 |
| 只有 gross/AUC 成功，成本后失败 | 表征存在但不可交易 | 诊断收口，不进入 policy |

## 12. 数据与 OOS 治理计划

### 12.1 现有历史数据全部降级为 local replication / design-only

EP1–EP19 已反复读取 2018–2025 的标签、收益和市场状态。即使重新切分，也不能把这些年份重新命名为
“全新 OOS”。后续报告必须使用：

```text
historical_role = local_replication_or_spent_diagnostic
independent_support = false
```

2022–2023 在 EP19 中虽然保持 validation stress 未读取，但整个研究计划已多次观察相邻时期与同类 outcome；
新 Episode 最稳妥的治理是把全部当前历史期都视为设计/压力读数，而不把它包装成新的支持性样本。

### 12.2 真 forward 从新 contract freeze 之后开始

新 Episode 的 forward 起点应定义为：

```text
first_exchange_session_strictly_after_preoutcome_contract_freeze
```

在 freeze 之前已经发生、只是尚未补入本地数据库的 2026 年 6–7 月数据属于 backfill historical data，
不能因为“程序之前没读过”就称为 forward OOS。

建议两阶段证据治理：

1. **现在：** 用历史数据完成 exact replication、数据契约、实现 QA 和 design-only effect sizing；
2. **未来：** 冻结最多一至两个候选，积累至少 6 个独立 decision months，并等待 primary horizon 完整后，
   才允许 support claim。

若 primary 是月频 one-month return，forward 等待期可以短于 19B3 的 120-session label；若要桥接 Big Winner，
120-session 结论仍必须等待完整 path。不能为了加快结论在 outcome 后切换 primary horizon。

## 13. 预注册的停止规则

后续研究应在开始前写明关闭状态，避免再次形成无限 episode 链：

```text
directional_factor_not_locally_replicated
    -> TrendPV / residual momentum 均未得到成本后方向性收益；不进入 FIP interaction search。

factor_replication_only_no_long_only_entry_path
    -> long-short 因子成立，但 long-only/full-capital 不成立；保留资产定价证据，关闭 entry claim。

two_tailed_scale_factor_only
    -> 右尾提高但 ES10/左尾同步超预算，vol-matched return lift 消失；归类为 scale factor。

risk_overlay_supported_no_alpha_increment
    -> Low Vol/MA 改善风险但降低或不提高 full-capital mean；只保留风险层角色。

representation_gap_diagnostic
    -> CNN 有增量而手工因子失败；允许新表征研究，不授权策略。

daily_ohlcv_directional_information_not_supported
    -> 手工因子与 CNN 在严格 OOS、成本后均失败；关闭日频 OHLCV 静态入场主线。

directional_alpha_candidate_supported
    -> 只有 fixed-return、scale-independence、economic、stability、concentration 与 true-forward gates
       全部通过后，才允许另立 policy/portfolio requirement。
```

## 14. 建议执行顺序与产物

不要同时启动六条路线。建议顺序：

1. 先写 `EP20 OHLCV directional alpha replication research plan`，冻结方向、角色和停止规则；
2. 生成 20A requirement，只做 TrendPV、total momentum、market-residual momentum、low-vol comparator；
3. 完成 paper formula registry、PIT industry availability audit、cost/execution contract；
4. 运行历史 local replication，产出 fixed-return、full-capital、exposure 和 scale-vs-drift 诊断；
5. 只有 TrendPV 或 residual momentum 至少一个成立，才生成 20B/20C requirement；
6. Low Vol/MA 留在风险层；CNN 最后作为 oracle；
7. 在 true-forward 数据到齐前，不生成 policy、portfolio optimization 或 production signal。

建议的最小 publishable artifacts：

```text
paper_formula_registry.csv
factor_feature_lineage_audit.csv
pit_industry_membership_availability_audit.csv
historical_replication_role_audit.csv
factor_portfolio_return_readout.csv
long_only_full_capital_return_readout.csv
volatility_matched_directionality_readout.csv
factor_exposure_and_concentration_readout.csv
turnover_cost_capacity_readout.csv
barrier_first_hit_ordering_readout.csv
forward_evaluability_preflight.csv
episode_20_replication_report.md
```

## 15. B2 的保留方式

B2 不应被删除，也不应继续主动调参。建议将其归档为：

```text
research_role = frozen_two_tailed_right_tail_reservoir_benchmark
active_optimization = false
future_action = rerun_frozen_19B3_only_when_all_forward_support_floors_are_met
```

它在下一 Episode 中可以作为一个“已知的 scale-amplifier negative control”：新的 TrendPV/residual/FIP signal
如果只是复现 B2 的高 MFE、高 MAE、高 VOL60 暴露，就不能被认定为方向性突破。

未来 19B3 机械重跑若通过，只能说明 R2 的左尾预算在新 cohort 可复现；它仍需 fixed-return/full-capital utility
验证，不能自动恢复 19C 或原 EP20 policy authorization。

## 16. 最终研究判断

EP19 没有找到“相对较好的 entry”，但它完成了一次重要的研究对象校正：

```text
从：在大赢家事件附近寻找更多形态，再过滤明显坏样本
到：先证明一个信号提高固定期限条件均值，再研究右尾与风险预算
```

B2 告诉我们的不是“突破无效”，而是“突破/强势/高波动能够增加极端路径暴露，却没有自动提供方向性收益”。
R2 告诉我们的不是“低波动过滤成功”，而是“风险压缩可以改善中位数和左尾，同时牺牲决定均值的厚右尾”。

因此后续最值得投入的不是新的 RSI、MACD、均线交叉或 B2 suppressor，而是：

1. A 股价量多期限 TrendPV 的精确复制；
2. market/industry/style residual momentum 的 PIT 本地复制；
3. 用 FIP/trend clarity 区分渐进 drift 与离散 jump；
4. 把 Low Vol 和 MA timing 固定在风险/组合层；
5. 最后用 OHLCV image CNN 检验是否存在手工特征遗漏的表征上限。

EP19 至此结题。任何新正向主张必须来自新的研究对象、预注册 fixed-return estimand，以及 freeze 之后真正形成的
forward cohort，而不能来自对 EP19 已消费 outcome 的继续切割。

## 17. 证据索引

EP19 本地主要证据：

- `outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/19A_entry_universe_pit_lineage_tradability_and_data_contract_report.md`
- `outputs/19B0_fast_rule_grid_enrichment_scan/19B0_fast_rule_grid_enrichment_scan_report.md`
- `outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md`
- `outputs/19B1_t0_left_right_tail_separability_readout/19B1_t0_left_right_tail_separability_readout_report.md`
- `outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/19B2_b2_high_vol_extension_left_tail_suppressor_ablation_report.md`
- `outputs/19B3_b2_positive_exposure_left_tail_budget_frontier/19B3_b2_positive_exposure_left_tail_budget_frontier_report.md`
- `research_plan.md` Section 11–12

后续研究方向的公开证据入口：

- [Trend Factor in China: The Role of Large Individual Trading](https://academic.oup.com/raps/article-abstract/14/2/348/7590854)
- [Residual Momentum](https://www.sciencedirect.com/science/article/pii/S0927539811000041)
- [Anomalies in the China A-share Market](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3810114)
- [Frog in the Pan: Continuous Information and Momentum](https://academic.oup.com/rfs/article-abstract/27/7/2171/1578455)
- [The Volatility Effect in China](https://link.springer.com/article/10.1057/s41260-021-00218-0)
- [A New Anomaly: The Cross-Sectional Profitability of Technical Analysis](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29)
- [(Re-)Imagining Price Trends: A Machine Learning Approach to Stock Return Prediction](https://economics.yale.edu/sites/default/files/2023-11/The%20Journal%20of%20Finance%20-%202023%20-%20JIANG%20-%20Re%25E2%2580%2590%20Imag%20in%20ing%20Price%20Trends_0.pdf)
