# 20B TrendPV 与 Residual Momentum 历史设计诊断：中文详细解读

> 本文是 sealed `20B_v5` 的只读解释性 companion report。它引用 v5 已密封表中的数字，不修改 runner、配置、需求、测试或 v5 bundle，也不重新计算 outcome。

## 1. 执行结论

最终状态为：

```text
decision_state = 20B_underpowered_design_diagnostic
20C_requirement_generation_authorized = false
20C_execution_authorized = false
historical_support_claim_allowed = false
exact_replication_reachable = false
```

结论不是“所有候选信号都没有经济方向”，而是：

1. P1 project-strict 只有 `35` 个可评价月，early/late 为 `22/13`，低于冻结的 `48/24` 门；
2. P4 market-only residual momentum 只有 `43` 个可评价月，early/late 为 `25/18`，低于冻结的 `60/30` 门；
3. P4 的点估计方向实际上较好，但样本门先失败，因此不能把这些数字升级为正收益暴露候选；
4. P1 的 full/early 方向为负，late 才转正，既没有通过样本门，也没有稳定的跨折方向；
5. P5 的静态 board/size 二阶段残差没有增强 P4，反而在严格配对样本中消除了 P4 的大部分 spread；
6. LowVol comparator 的方向最稳定，但它是 comparator-only，不能独立授权 20C。

因此，当前最合理的 AFML 判断是：**先修复 outcome bridge 的可验证性和月份级可评价率，再决定是否保留 P4；不应基于本次结果调参、删窗口或更换分桶。**

## 2. 如何阅读本报告中的收益数字

本地收益均为 provider-qfq close-to-close gross proxy，不是 next-open、成本后或 cash-inclusive NAV。

核心指标定义：

| 指标 | 定义 | 在 20B 中的作用 |
|---|---|---|
| favorable extreme mean | 预期方向一端 decile 的月均绝对收益；P1/P4/P5/P0 为高分组，P6 为低波动组 | 正收益暴露门的经济方向 |
| unfavorable extreme mean | 预期方向相反一端 decile 的月均收益 | 解释排序形态，不是 cash hurdle |
| favorable-minus-unfavorable | favorable bucket 减 unfavorable bucket | paper-style sorting morphology |
| favorable-minus-middle | favorable bucket 减中间 bucket | 检查是否只有极端两端驱动 |
| spread positive month rate | 月度 spread 大于 0 的比例 | 方向稳定性描述 |
| raw bucket Spearman | bucket 编号与 bucket return 的月均 Spearman | 横截面单调性 |
| favorable-aligned Spearman | 对 LowVol 反转符号后的统一方向 Spearman | 跨 arm 可读性 |
| HAC t / p | Newey-West/Bartlett 的 design-only 诊断 | 不产生 support，不改变授权 |

所有百分比均为月收益。例如 `0.016189` 表示月均 `+1.6189%`，不是年化收益。

## 3. 理论日历、实际支持和样本门

Preoutcome 在读取收益前冻结：

| Arm/calendar | 理论月份 | Frozen early/late | 实际可评价 | 实际 early/late | 门槛 | 结果 |
|---|---:|---:|---:|---:|---:|---|
| P1 project-strict | 55 | 27/28 | 35 | 22/13 | 48 且 24/24 | fail |
| P1 paper-fill | 55 | 27/28 | 54 | 27/27 | 辅助诊断 48 且 24/24 | 数量够，但方向 fail |
| P4 R2 | 64 | 32/32 | 43 | 25/18 | 60 且 30/30 | fail |
| P5 retrospective | 64 | 32/32 | 46 | 27/19 | 辅助诊断 60 且 30/30 | fail |
| P0 TMOM | 101 | descriptive | 56 | 24/32 | comparator，无 gate | materialized |
| P6 LowVol | 77 | descriptive | 49 | 26/23 | comparator，无 gate | materialized |

P1 理论 calendar 为 `2021-10` 至 `2026-04`；P4/P5 为 `2021-01` 至 `2026-04`。本地 PIT universe 只物化到 `2026-03`，因此 P1 和 P4 都先少一个 scheduled decision month。剩余损失主要由 project-conservative unknown bridge 引起，而不是 decile 数量不足：所有列出的 P1/P4 月份都具有远高于 100 的 signal-eligible N。

## 4. Outcome resolution：为什么 99.8% 行覆盖仍会造成严重 underpower

`outcome_resolution_audit.csv.gz` 有 `666,000` 行。它包含 arm/track 与 quintile/decile 扩展，因此同一 instrument-decision outcome 会重复出现。两种口径必须区分：

| 口径 | valid mark | unknown bridge | suspension carry | delisting -1 |
|---|---:|---:|---:|---:|
| Audit expanded rows | 663,156 | 2,844 | 0 | 0 |
| Unique instrument-decision | 55,263 | 237 | 0 | 0 |

237 个 unique unknown 涉及 `180` 只股票和 `60` 个 decision months。没有任何 partial qfq month 被擅自解释为 suspension carry；没有已选股票触发 confirmed delisting -1。

关键的非线性在于：

```text
一个已分桶股票出现 unknown
    -> 该股票不能被删除后对其余股票重加权
    -> 整个 arm-track-bucket-month 不可评价
    -> 该 decision month 不能进入 decile spread / favorable mean
```

因此，行级 resolution rate 接近 100% 并不意味着月份级 gate 基本完整。

具体损失如下：

| Arm | 有 signal 的 frozen months | 含 unknown 的 months | Project-evaluable months |
|---|---:|---:|---:|
| P1 strict | 54 | 19 | 35 |
| P1 paper-fill signal + project outcome | 54 | 19 | 35 |
| P4 | 63 | 20 | 43 |
| P5 | 63 | 17 | 46 |

P1 late fold 的损失尤其集中：冻结 late 有 28 个月，但只剩 13 个可评价月。P4 late 从 32 降至 18。这解释了为什么点估计看似有方向，却不能通过 24/30 个月的折内门。

### 4.1 研究含义

这是一个 outcome-lineage bottleneck，而不是典型的 feature sparsity bottleneck。继续增加 signal coverage 无法修复整桶不可评价；真正需要的是可审计的 suspension、corporate-action bridge 和 recovery lineage。

## 5. TrendPV 公式是否正确物化

TrendPV 使用固定的 9 个 price windows 与 9 个 normalized-volume windows，共 18 个 predictors：

```text
L = 3, 5, 10, 20, 50, 100, 200, 300, 400 exchange sessions
```

两个 semantic tracks 均得到：

| Track | Coefficient rows | Complete coefficient months | 首个 complete month | 第 38 个 complete month | 最大 staleness |
|---|---:|---:|---|---|---:|
| project-strict | 113 | 93 | 2018-09 | 2021-10 | 0 |
| paper-fill | 113 | 93 | 2018-09 | 2021-10 | 0 |

这说明 400-session readiness、`m-1 signals -> m return` OLS、EMA `lambda=0.02` 和 38-complete-month burn-in 都成功物化。每个月都保存 realized beta 与 EMA beta，各 18 列；没有用未来 coefficient 填补缺口。

组件月均值：

| Track | Price component mean | Volume component mean | Total score mean |
|---|---:|---:|---:|
| project-strict | +0.000041 | -0.002340 | -0.002300 |
| paper-fill | +0.025574 | -0.003251 | +0.022323 |

这不是收益贡献分解，而是 signal-score 的尺度描述。可以看到 volume component 均值相对小且偏负，score 的月际波动主要由 price component 决定。两个 track 的 score level 不可直接当成经济收益比较。

## 6. P1 project-strict：完整结果

Primary 口径为 EW decile + project-conservative outcome：

| Scope | 月数 | Favorable | Unfavorable | Spread | Spread>0 | Spearman | HAC t / p |
|---|---:|---:|---:|---:|---:|---:|---:|
| full | 35 | -1.2722% | +1.0499% | -2.3221% | 34.3% | -0.259 | -2.149 / 0.0316 |
| early | 22 | -3.7870% | +0.0951% | -3.8821% | 22.7% | -0.393 | -3.595 / 0.0003 |
| late | 13 | +2.9836% | +2.6657% | +0.3179% | 53.8% | -0.032 | 0.231 / 0.8172 |

### 6.1 Findings

1. Full sample 和 early fold 都是明显反向排序：高 TrendPV score 组表现低于低分组；
2. Late fold 的 favorable bucket 转为正收益，spread 也略为正，但只有 13 个月；
3. 从 early 的 `-3.88%` spread 到 late 的 `+0.32%`，变化幅度大于 full-sample 均值，表明 regime/time instability；
4. HAC 只说明当前 35 个月中的负 spread 不是由普通 iid 标准误造成，不能越过样本门，也不能形成 support。

### 6.2 Dominance

P1 strict 的最大单月绝对贡献为 `10.62%`，top-3 月贡献为 `28.03%`。Leave-one-month-out 的最差均值仍为 `-2.6392%`；LOIO 范围为 `-2.4105%` 至 `-2.2505%`，最大单股票偏移只有 `0.0884` 个百分点。

因此 full-sample 负方向不是一只股票或一个月份造成的。P1 当前更适合被降级为“公式已物化但历史方向不稳定的 comparator”，不适合通过调窗口寻找局部正结果。

## 7. P1 paper-fill：缺失语义并不能解释负排序

Paper-fill complete-case 有 54 个可评价月，满足辅助诊断的 48/24 数量要求：

| Scope | 月数 | Favorable | Unfavorable | Spread | Spread>0 | Spearman | HAC t / p |
|---|---:|---:|---:|---:|---:|---:|---:|
| full | 54 | -0.3056% | +1.1339% | -1.4394% | 44.4% | -0.120 | -2.152 / 0.0314 |
| early | 27 | -2.4891% | -0.5045% | -1.9846% | 40.7% | -0.195 | -2.685 / 0.0073 |
| late | 27 | +1.8779% | +2.7722% | -0.8943% | 48.1% | -0.046 | -0.760 / 0.4473 |

Paper-fill 的 spread 在 full、early、late 三个 scope 中都为负。它比 project-strict 的缺失更少，但仍未恢复 TrendPV 预期方向。

这说明 P1 的问题不能简单归因于 project-conservative whole-bucket fail-closed。更可能的解释是：本地 U_project、样本期和 raw TrendPV adaptation 下，论文式横截面排序没有稳定迁移。

## 8. P4 market-only residual momentum：最值得保留但仍未获授权的方向

P4 的 primary 结果：

| Scope | 月数 | Favorable | Unfavorable | Spread | Spread>0 | Spearman | HAC t / p |
|---|---:|---:|---:|---:|---:|---:|---:|
| full | 43 | +0.5798% | -1.0391% | +1.6189% | 58.1% | +0.177 | 2.007 / 0.0447 |
| early | 25 | +0.0169% | -1.3559% | +1.3728% | 60.0% | +0.197 | 0.946 / 0.3444 |
| late | 18 | +1.3616% | -0.5990% | +1.9606% | 55.6% | +0.149 | 2.587 / 0.0097 |

### 8.1 Findings

1. favorable bucket 在 full/early/late 都大于 0；
2. spread 在三个 scope 都为正，late 强于 early；
3. full 与 late 的 design-only HAC p-value 分别约为 `0.045` 和 `0.010`；
4. 但 43/25/18 明确低于 60/30/30，所以 `P4_materialization_gate=false`，进而 `P4_positive_exposure_design_gate=false`。

P4 是本次最有经济方向的 primary arm，但“点估计满足方向”与“冻结门通过”必须分开。将 43 个月结果称为已识别候选会绕过预先注册的功效门。

### 8.2 Robustness / dominance

P4 最大单月贡献为 `7.48%`，top-3 为 `18.75%`；leave-one-month-out 最低 spread 仍为 `+1.2595%`。LOIO 后 spread 在 `+1.4730%` 至 `+1.6787%`，最大单股票偏移 `0.1458` 个百分点，对应 `SH600111`。

因此，P4 正方向不是由单月或单股票支配。真正的阻断项是可评价月份数，而不是脆弱的均值构成。

### 8.3 R2 回归质量

R2 time-series audit 有 `101,273` 个 pass rows、`76` 个 residual months、`1,615` 只股票；所有 returned rank 都为 2。Market beta 中位数为 `0.857`，10%/90% 分位数为 `0.325/1.498`。

这说明 sequential 36-month OLS 本身稳定物化；P4 underpower 发生在后续 outcome-evaluable bucket months，而不是回归 rank 失败。

## 9. P5 size/board residual：没有提供正向增量

R3 ridge 共 `76` 个 residual months。每月 final fit N 中位数 `426.5`，范围 `315–468`；非恒定 predictors 中位数 `228`，范围 `220–232`。只有 `16` 个 residual months 的 board snapshot 在 predictor as-of 时点已经可知。

P5 full-history retrospective 结果：

| Scope | 月数 | Favorable | Unfavorable | Spread | HAC p |
|---|---:|---:|---:|---:|---:|
| full | 46 | -0.0531% | -0.0592% | +0.0061% | 0.9879 |
| early | 27 | -0.3478% | -0.5509% | +0.2031% | 0.7311 |
| late | 19 | +0.3658% | +0.6394% | -0.2737% | 0.5629 |

只有 `1` 个 fully-post-snapshot score month 可评价，因此 P5 几乎完全是 retrospective/mixed sensitivity，不能用于历史 PIT board 结论。

### 9.1 P4/P5 严格配对归因

Score pair 共 `19,108` 个 instrument-month；P4/P5 raw score correlation 只有 `0.402`，说明二阶段 size/board residualization 显著改变了排序。

对同月、同 return semantics、同 weighting、同 decile 的严格 paired spread：

| Scope | Paired N | P4 spread | P5 spread | P5-P4 |
|---|---:|---:|---:|---:|
| full | 58 | +0.5714% | -0.4022% | -0.9737% |
| early | 30 | +0.7358% | +0.0556% | -0.6803% |
| late | 28 | +0.3952% | -0.8927% | -1.2880% |

这里必须使用 paired means；不能拿 P4 和 P5 各自不同月份的全样本均值直接相减。

### 9.2 Insight

P5 并没有证明 board/size “解释了 alpha”。更准确的描述是：在当前 static-board proxy 下，第二阶段 residualization 删除了 P4 的大部分排序结构，尤其 late paired spread 从正值变为明显负值。

结合只有一个 fully-post-snapshot month，无法区分这是：

- board/size 确实吸收了 P4 的经济暴露；
- 静态 board look-ahead/misalignment 破坏了排序；
- ridge 横截面残差在小样本中引入了噪声。

因此 P5 应继续保持 attribution-only，不能替代 P4，也不能改变 20A 冻结的 residual primary。

## 10. Comparator：P0 与 P6 告诉了什么

### 10.1 P0 Total Momentum

P0 full favorable return 为 `-0.2581%`，spread 为 `+0.3406%`。Early spread 为 `-0.7342%`，late 为 `+1.1466%`，方向发生翻转。

这说明普通 12-1 momentum 在本地样本也存在明显时间不稳定，不能把 P1 的失败简单归因于 TrendPV 特有实现错误。

### 10.2 P6 LowVol

P6 的 favorable 是低波动 decile：

| Scope | 月数 | LowVol favorable | HighVol unfavorable | Favorable spread | Aligned Spearman |
|---|---:|---:|---:|---:|---:|
| full | 49 | +1.0250% | -0.0338% | +1.0588% | +0.117 |
| early | 26 | +1.2415% | -0.1420% | +1.3835% | +0.043 |
| late | 23 | +0.7802% | +0.0885% | +0.6917% | +0.199 |

LowVol 是唯一在 full/early/late 都同时满足 favorable return > 0 和 spread > 0 的 comparator。其最大单月贡献 `7.06%`、top-3 `17.25%`；LOIO spread 范围 `+1.0056%` 至 `+1.1431%`。

这不授权把 LowVol 晋升为 20B primary，但它提示：未来任何 positive-beta sleeve 设计都必须保留 LowVol 控制，否则 residual/momentum 结果可能只是波动暴露的另一种表达。

## 11. 3/6/12 个月 overlapping sensitivity

以下为 EW decile favorable bucket 的 overlapping portfolio-month readout：

| Arm | H | Evaluable months | Mean return | Median | Positive month rate |
|---|---:|---:|---:|---:|---:|
| P4 | 3 | 55 | +0.7754% | -0.6804% | 43.6% |
| P4 | 6 | 39 | +0.9592% | +0.0741% | 53.8% |
| P4 | 12 | 12 | +0.5215% | -0.5488% | 41.7% |
| P5 | 3 | 58 | +0.6574% | +0.1670% | 51.7% |
| P5 | 6 | 49 | +1.0530% | +0.3902% | 57.1% |
| P5 | 12 | 22 | +1.9025% | +1.2703% | 54.5% |

这些数字只能作为 horizon sensitivity：

- overlapping cohorts 不是独立观察；
- H=12 的可评价月份只有 12/22；
- P5 仍受 static-board retrospective scope 约束；
- 该 appendix 不进入任何 gate。

P5 H=12 的高均值不能推翻 1-month paired attribution，也不能独立授权下一阶段。

## 12. Exact route 与文献比较边界

P2/P3 均为 `registered_not_run`：

| Route | 缺失条件 |
|---|---|
| P2 full Trend exact | wide PIT market cap、PIT E/P、paper universe、exact history |
| P3 CH-3 residual exact | risk-free、CH-3 vintage、paper universe、exact history |

P1/P4/P5 都是 U_project adaptation。Paper sample、数据库、组合形成和持有规则不同，因此 local number 与文献数字不具有直接可比性；方向相同也不能升级 exact claim。

## 13. 为什么 terminal state 必须是 underpowered

Truth table 的关键布尔量为：

```text
P1_formula_integrity_gate = true
P4_formula_integrity_gate = true
P1_sample_support_gate = false
P4_sample_support_gate = false
P1_materialization_gate = false
P4_materialization_gate = false
global_underpowered = true
```

它与 `data_or_formula_materialization_blocked` 不同：公式和模型都已成功运行；失败的是两个 primary arm 都没有达到冻结的月份支持门。

它也不能降级成 `mixed_direction`：P4 虽有正方向，P1 late 也有正值，但 materialization gate 先失败，states 8–11 不应覆盖 state 7。

## 14. 综合 findings

### Finding 1：P4 是唯一值得保留的 primary research lead

P4 的 favorable return、spread、Spearman 在 full/early/late 均同方向，且 dominance/LOIO 不显示单点支配。若未来通过 outcome-lineage 修复补足样本，P4 是最合理的再验证对象。

### Finding 2：P1 的问题不只是 conservative missingness

Paper-fill 有 54 个月，但三个 fold 的 spread 仍为负。继续放宽 outcome semantics 不会自然恢复预期排序。P1 不应通过换窗口、删 volume component 或挑 late period 来“修复”。

### Finding 3：P5 没有提供 board-adjusted 增量证据

严格 paired attribution 显示 P5-P4 spread delta 为负，且 fully-post-snapshot 只有一个月。P5 目前只能说明排序对静态 board/size transform 很敏感，不能说明 board-adjusted residual 更优。

### Finding 4：缺失机制在 bucket-month 层面被放大

237 个 unique unknown 只占 instrument-decision rows 的约 `0.43%`，却让 P1/P4 分别损失 19/20 个 outcome months。下一步最有价值的投入是修复 valuation bridge lineage，而不是增加模型复杂度。

### Finding 5：LowVol 是不可删除的风险控制

LowVol comparator 的方向比 momentum/residual arms 更稳定。未来重新评价 P4 时，应并列 LowVol 和 volatility-neutral sensitivity，避免把低风险暴露误写为 residual momentum 的独立价值。

## 15. AFML 视角下的研究判断

从 AFML 的 decision framing 看，本轮不是“预测模型效果差”，而是 utility gate 尚不可评价：

```text
formula integrity: pass
signal materialization: pass
outcome lineage completeness at row level: high
outcome evaluability at bucket-month level: insufficient
cross-fold utility gate: not reached
```

因此正确动作不是模型选择，而是 denominator/label engineering：

1. 保留 frozen arm、窗口、bucket 和 sample floors；
2. 建立因果可审计的 suspension/delist/corporate-action resolution source；
3. 在不看 spread 的条件下预先冻结 bridge coverage gate；
4. 使用同一公式重跑，检查 P4 是否达到 60/30；
5. 只有样本门通过后，才读取 positive-exposure gate；
6. 若补足 lineage 后 P4 仍无法达到门槛，则关闭该 research lead，而不是继续调参。

## 16. 建议的下一研究方向

当前 `20C_requirement_generation_authorized=false`，所以不能直接生成或执行 20C。允许讨论但尚未获授权的下一步应是独立的数据契约修复：

### 优先级 A：Outcome bridge lineage

- 对 partial-month qfq observation 取得 PIT suspension/status 证明；
- 对 corporate action gap 建立可复算的 adjusted-price continuity audit；
- 对 confirmed delisting 建立 recovery 或 conservative terminal lineage；
- 在 outcome read 前冻结 bridge source whitelist 和 coverage threshold。

### 优先级 B：P4 保留原公式复验

如果数据契约补齐，不改变 36m regression、11 residual months、EW decile 或 60/30 floor，重新计算 P4。这样才能判断当前 `+1.62%` full spread 是否在完整月份上保持。

### 优先级 C：P1/P5 降级

- P1 保留为 negative/unstable morphology comparator，不做窗口优化；
- P5 保留为 board-attribution sensitivity，等待真正 PIT board history；
- LowVol 作为任何后续设计的 mandatory comparator。

## 17. Evidence 与授权边界

本报告的主要数字来自：

- `20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5/20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv`
- `.../historical/monthly_signal_support.csv`
- `.../historical/sort_monotonicity_readout.csv`
- `.../historical/arm_summary_statistics.csv`
- `.../historical/month_instrument_dominance_audit.csv`
- `.../historical/outcome_resolution_audit.csv.gz`
- `.../historical/trendpv_coefficient_path.csv.gz`
- `.../historical/residual_time_series_regression_audit.csv.gz`
- `.../historical/residual_board_ridge_audit.csv.gz`
- `.../historical/p4_p5_board_attribution_readout.csv`
- `.../historical/residual_overlapping_portfolio_returns.csv.gz`

固定授权边界：

```text
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
policy_training_authorized = false
policy_replay_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

本报告不改变 sealed v5 的 decision、manifest 或任何 hash。
