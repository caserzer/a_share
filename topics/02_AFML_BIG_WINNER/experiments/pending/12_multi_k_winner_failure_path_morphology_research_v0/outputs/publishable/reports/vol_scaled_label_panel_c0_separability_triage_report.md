# 12A7g 波动率缩放 Winner Label Panel 与 C0 可分性分诊报告

## 结论

本轮 12A7g 不再被 regime calendar 缺失日期阻断。缺失 regime 的日期已按逐行 bypass 处理，输入门禁通过。最终裁决是：

```text
decision_state = 12A7g_baserate_only_not_separable_stop_winner_selection
next_allowed_requirement = defense_overlay_plus_rule_based_participation_summary
```

含义是：新的 event-agnostic vol-scaled winner label 可以稳定构造，C0 也确实有一定右尾富集；但这不足以支持继续把 C0 作为 winner selector。可部署 stage-2 denominator 的右尾可分性和 utility 都没有过关，post-hoc survivor 的改善主要是诊断意义，不能转成可部署选股规则。更合适的路线是把 C0 降级为 defense overlay / rule-based participation 的辅助条件。

## 输入与样本治理

| 项目 | 结果 |
|---|---:|
| input_gate_status | pass |
| lineage_gate_status | pass |
| global_regime_calendar_status | pass_with_missing_date_bypass |
| missing regime bypass rows | 184,500 |
| missing regime bypass unique dates | 369 |
| retained primary-scope rows | 431,239 |
| selected label | vol20d_kup2p0_kdn1p0_H20 |
| active-band cartography gate eligible | False |

Regime calendar 由于前后窗口计算约束，覆盖范围短于 PIT universe。缺失日期没有被硬判为 input failure，而是从 primary-scope denominator 中剔除。保留下来的 primary rows 仍有 431,239 行，足够支持 label selection 和 full-universe diagnostic readout。

需要注意：`full_pit_c0_comparable_active_band` 没有进入可决策状态。active-band audit 显示 `fallback_status = volatility_reconciliation_fail`，因此 `active_band_cartography_gate_eligible = False`。这意味着 full-universe raw separability 只能作为诊断信号，不能授权 event-family cartography。

## Label 选择

本次 label grid 共 75 个候选：

| label 类型 | eligible | ineligible |
|---|---:|---:|
| vol_scaled | 22 | 50 |
| fixed_anchor | 0 | 3 |

被选中的 label 是 `vol20d_kup2p0_kdn1p0_H20`。它使用 20 日历史波动率作为 scale，20 session horizon，上轨为 `2.0 x volatility_20d x sqrt(20)`，下轨为 `1.0 x volatility_20d x sqrt(20)`。

| 指标 | 数值 |
|---|---:|
| train denominator | 232,640 |
| train horizon complete rate | 1.0000 |
| train positive n | 34,621 |
| train winner base rate | 0.1488 |
| same-bar conflict rate | 0.0000 |
| label base-rate dispersion | 0.0985 |
| label stability score | 0.9003 |
| selection reason | only_eligible_vol_scaled |

fixed anchor 的稳定性不够好。`fixed_U20_L10_H20` 的 train base rate 是 0.1592，看似接近目标，但 base-rate dispersion 达到 0.1261，超过阈值；`fixed_U15_L10_H20` 和 `fixed_U20_L10_H40` 的 base rate 分别为 0.2403 和 0.2427，漂移更明显。因此，本轮选择 vol-scaled label 是合理的：它不是为了提高 C0 表现而定制，而是在全 PIT universe 上先取得更稳定的 winner 定义。

## Denominator Base Rate

| denominator | rows | positive n | winner base rate |
|---|---:|---:|---:|
| c0_entry_t0 | 15,113 | 2,308 | 0.1527 |
| c0_posthoc_no_fast_fail_survivor | 9,481 | 2,225 | 0.2347 |
| c0_deployable_stage2_reference | 3,616 | 571 | 0.1579 |
| full_pit_risk_on_universe_raw_diagnostic | 431,239 | 59,447 | 0.1379 |

C0 entry 的 base rate 为 15.27%，只比 full raw diagnostic 的 13.79% 略高。post-hoc no-fast-fail survivor 的 base rate 提升到 23.47%，但这个 denominator 使用了事后 survivor 信息，只能说明“如果已经知道没有 fast fail，样本更干净”。真正可部署的 stage-2 denominator base rate 是 15.79%，几乎回到 C0 entry 水平。

这个结构说明：C0 的右尾富集主要存在于 post-hoc survivor 条件里，而不是稳定地保留在可部署 continuation 决策点上。

## C0 可分性

### C0 Entry

Entry denominator 的 train split 有可分性，但 robustness 不通过。

| split | selected feature | orientation | AUC | rank IC | top-decile rate | base rate | lift abs | adjusted status |
|---|---|---|---:|---:|---:|---:|---:|---|
| train | rebound_from_20d_low | asc | 0.5987 | 0.1272 | 0.2768 | 0.1660 | 0.1108 | pass |
| validation | rebound_from_20d_low | asc | 0.6665 | 0.1815 | 0.2083 | 0.1116 | 0.0968 | fail |
| robustness | rebound_from_20d_low | asc | 0.5501 | 0.0616 | 0.1781 | 0.1481 | 0.0300 | fail |

Entry 层面不是完全没有信号。它在 train 和 validation 的 AUC / lift 都不差，但 robustness lift 只有 3.00pp，未能通过 search-adjusted gate。这个现象更像弱形态倾向，而不是可迁移的 winner selector。

### Post-hoc Survivor

Post-hoc survivor 的 train 表现更强，但 out-of-sample 失效。

| split | selected feature | orientation | AUC | rank IC | top-decile rate | base rate | lift abs | adjusted status |
|---|---|---|---:|---:|---:|---:|---:|---|
| train | freshness_decay_tau_5 | asc | 0.5527 | 0.0814 | 0.4099 | 0.2733 | 0.1367 | pass |
| validation | freshness_decay_tau_5 | asc | 0.4734 | -0.0340 | 0.1549 | 0.1627 | -0.0077 | fail |
| robustness | freshness_decay_tau_5 | asc | 0.4964 | -0.0050 | 0.2130 | 0.2087 | 0.0042 | fail |

这里的核心不是“survivor 条件没用”，而是 survivor 条件无法作为可部署 winner selector。Train 上的 top-decile lift 达到 13.67pp，但 validation 和 robustness 都接近随机甚至反向，说明 post-hoc survivor 改善不能外推。

### Deployable Stage-2

可部署 stage-2 denominator 是本需求的关键门。它没有通过。

| split | selected feature | orientation | AUC | rank IC | top-decile rate | base rate | lift abs | adjusted status |
|---|---|---|---:|---:|---:|---:|---:|---|
| train | turnover_zscore_20d | asc | 0.6086 | 0.1277 | 0.2201 | 0.1327 | 0.0874 | fail |
| validation | turnover_zscore_20d | asc | 0.4393 | -0.0766 | 0.1429 | 0.1573 | -0.0145 | fail |
| robustness | turnover_zscore_20d | asc | 0.5186 | 0.0252 | 0.1811 | 0.1897 | -0.0086 | fail |

即使 train split 看起来有 8.74pp top-decile lift，search-adjusted status 仍是 fail；validation 和 robustness 的 top-decile lift 直接变成负值。这个结果是最终裁决的关键证据：C0 经过 defense / stage-2 之后，并没有留下一个稳定可排序的 continuation winner 信号。

## Full-universe Diagnostic

Full raw universe 上的 primitive feature separability 很强，但不能直接解释为 event-family 支持。

| split | selected feature | orientation | AUC | rank IC | top-decile rate | base rate | lift abs | adjusted status |
|---|---|---|---:|---:|---:|---:|---:|---|
| train | max_drawdown_20d | desc | 0.6045 | 0.1289 | 0.2301 | 0.1488 | 0.0813 | pass |
| validation | max_drawdown_20d | desc | 0.6121 | 0.1176 | 0.2089 | 0.1022 | 0.1067 | pass |
| robustness | max_drawdown_20d | desc | 0.6301 | 0.1544 | 0.2180 | 0.1357 | 0.0823 | pass |

这说明全市场 PIT universe 里确实存在一种可排序的 path morphology：近期 drawdown 更深的股票，在 vol-scaled winner label 下更容易进入 top-decile winner。它更像一个 broad primitive / reversal-morphology 现象，而不是 C0 event family 的证据。

为什么不能据此启动 event cartography？因为 primary full-vs-C0 gate 要求 C0-comparable active band 可用，而本轮 active band 因 `volatility_reconciliation_fail` 被降级；`full_pit_c0_comparable_active_band` 的 effective denominator 为 0。因此 raw full-universe separability 只能说明“市场层面有形态可分性”，不能说明“C0 事件族值得扩展”。

## Utility 与 Recall

| denominator | precision | captured positives | utility per 20d |
|---|---:|---:|---:|
| c0_entry_t0 | 0.1527 | 2,308 | -0.011122 |
| c0_posthoc_no_fast_fail_survivor | 0.2347 | 2,225 | 0.024371 |
| c0_deployable_stage2_reference | 0.1579 | 571 | -0.009238 |
| full_pit_risk_on_universe_raw_diagnostic | 0.1379 | 59,447 | -0.015174 |

Post-hoc survivor 的 utility 是正的，且 precision 从 15.27% 提高到 23.47%。但它不是可部署入口，因为它依赖已经发生的 no-fast-fail 信息。可部署 stage-2 的 precision 只有 15.79%，utility per 20d 为 -0.009238，仍然是负值。

Recall 进一步说明 defense / continuation 链的代价：

| denominator | recall vs entry | recall cost |
|---|---:|---:|
| c0_posthoc_no_fast_fail_survivor | 0.9640 | 0.0360 |
| c0_deployable_stage2_reference | 0.2474 | 0.7526 |

post-hoc survivor 保留了 2,225 / 2,308 个 entry-anchor positives，recall 仍有 96.40%；但 deployable stage-2 只保留 571 / 2,308 个 positives，recall 下降到 24.74%。也就是说，可部署链路为了获得更干净的判断点，丢掉了 75.26% 的 entry-anchor winner positives，而剩余样本的 separability 和 utility 又没有通过。

## 有效样本与重叠控制

| denominator | raw rows | instruments | instrument-month blocks | overlap status |
|---|---:|---:|---:|---|
| c0_entry_t0 | 15,113 | 1,310 | 13,493 | pass |
| c0_posthoc_no_fast_fail_survivor | 9,481 | 1,114 | 8,564 | pass |
| c0_deployable_stage2_reference | 3,616 | 759 | 3,400 | pass |
| full_pit_risk_on_universe_raw_diagnostic | 431,239 | 1,489 | 33,903 | pass |

样本多样性不是主要瓶颈。C0 三个 denominator 的 instrument 和 instrument-month block 数都足够，overlap audit 也通过。问题不是样本太少，而是可部署 denominator 上的信号不稳定。

## Findings

1. Vol-scaled label 修复了 label 定义层面的不稳定性。固定阈值 label 全部 ineligible，而 vol-scaled grid 中有 22 个 eligible label，最终选中的 `vol20d_kup2p0_kdn1p0_H20` 兼顾了 14.88% train base rate、完整 horizon coverage 和较低 drift。

2. C0 entry 有弱可分性，但不够稳健。Entry split 的 selected feature 在 train / validation 有较高 lift，但 robustness only 3.00pp，search-adjusted gate fail。

3. Post-hoc survivor 的改善不能转化为可部署 winner selector。Train 上 top-decile lift 很高，但 validation / robustness 失效；它更像事后净化诊断，而不是可部署排名信号。

4. Deployable stage-2 是主要失败点。它既没有 robust separability，也没有正 utility；同时只保留 24.74% 的 entry-anchor positives，recall cost 太大。

5. Full-universe raw primitive separability 很强，但当前只能作为 diagnostic。`max_drawdown_20d` 在 train / validation / robustness 全部 pass，说明市场层面存在可排序的 path morphology；但 active-band cartography gate 因 volatility reconciliation fail 不可用，不能据此启动 event-family cartography。

## Insight

这组结果把问题拆清楚了：失败不在 label form，而在 event family 和 deployable decision point。Vol-scaled label 能稳定描述“相对自身波动率的右尾 winner”，但 C0 并没有提供足够稳定的条件分布变化，让这个 label 在可部署阶段可排序。

C0 更像一个 defense / participation context，而不是 winner discovery engine。它能帮助识别一些风险状态或 survivor 条件，但一旦要求在 entry-time 或 deployable stage-2 上做 winner 排名，信号就变弱并且不稳。继续沿 C0 直接优化 winner selector，容易把 post-hoc survivor 的净化误当成可部署 alpha。

下一步不应直接扩大 C0 winner-selection 搜索空间。更合理的方向是：把 C0 纳入 defense overlay 或 participation rule，明确它在哪些状态下减少参与、降低仓位或避免 fast-fail，而不是让它承担挑选右尾 winner 的主任务。如果后续仍想做 event-family cartography，应先修复 active-band 的 volatility reconciliation，让 full-vs-C0 比较有可比 denominator；否则 raw full-universe 的强 separability 只会把 broad market morphology 误解释成 event-family 证据。
