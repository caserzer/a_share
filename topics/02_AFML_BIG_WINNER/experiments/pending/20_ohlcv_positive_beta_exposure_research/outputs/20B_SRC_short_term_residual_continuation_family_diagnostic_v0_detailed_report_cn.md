# 20B-SRC Short-Term Residual Continuation Family：中文详细数据、发现与研究解读

> 本文是 sealed `20B_SRC_short_term_residual_continuation_family_diagnostic_v0` 的只读解释性 companion report。原始报告 SHA-256 为 `d7c21156e306ce6c2f58b8643b69f6942783a952899ddecea5d5424889b0007c`。本文只引用已经密封的 preoutcome、signal 与 historical artifacts，不修改原报告、manifest、runner、配置、需求或测试，也没有重新计算 outcome。

## 1. 执行结论

最终状态保持不变：

```text
terminal_state = 20B_SRC_not_identified_design_only
historical_sample_role = design_contaminated_historical
short_term_true_forward_freeze_recommended = false
participation_meta_label_research_recommended = false
next_requirement_generation_authorized = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

这次结果不是“有效历史不足，所以暂时无法判断”。两个 matched primary 的 sample support 与 paired attribution support 都通过，真正失败的是经济方向、跨时期稳定性与 residualization 增量价值：

1. **5D formation × H5 已基本否定。** EW decile favorable return 在 FULL/EARLY 为负，spread 在 FULL/EARLY/LATE 全为负，成本压力测试也失败；8 个 weighting/bucket/outcome sensitivity 中，没有一个 favorable 或 spread 能在三个 fold 同时为正。
2. **10D formation × H10 有局部正向信息，但不是稳定识别。** FULL favorable mean 为 `+28.06 bp/10D`，LATE 为 `+65.07 bp/10D`，但 EARLY 为 `-10.71 bp/10D`；冻结 primary gate 要求三个 fold 全部大于零，因此失败。
3. **10D 的正向结果具有明显 weighting 与 regime sensitivity。** 8 个 secondary specifications 中，5 个 favorable、4 个 spread 在三个 fold 同时为正；通过者高度集中于 VW，而冻结的 EW decile primary 没有通过。
4. **Residual score 并没有与 total continuation 充分分离。** Residual 与 matched Total score 的周度中位 Spearman 分别为 `0.931/0.938`，top-decile 中位 Jaccard 为 `0.548/0.600`。在短 formation window 下，减去市场成分通常没有大幅改变横截面排序。
5. **严格 paired attribution 不支持 residualization value。** 5D residual 相对 Total 在 FULL 期少 `5.63 bp`；10D 虽多 `5.88 bp`，但低于冻结的 `10 bp` materiality threshold，EARLY 又比允许的 non-degradation floor 多差 `0.64 bp`，同时 spread 与波动也恶化。
6. **10D 正向不是单周或单股票偶然值，但集中于后期 regime。** 10D top-1/top-3 week 绝对贡献仅为 `3.66%/7.26%`，leave-one-month-out 后均值仍为正；然而 EARLY/LATE 翻转、2024–2026 明显增强，说明问题更像时间状态依赖，而不是已识别的 unconditional continuation family。

因此，最准确的研究判断是：**5D 不值得继续；10D 留下了“后期、偏 VW、收益主要在第 6–10 日出现”的机制线索，但当前 short-term residual continuation family 本身没有获得稳定识别，更没有证明 residualization 是必要增量。**

## 2. 如何阅读本报告中的口径

### 2.1 `5×5` / `10×10` 的含义

本文中的：

- `5×5` 表示 `formation_sessions=5`、`holding_sessions=5`；
- `10×10` 表示 `formation_sessions=10`、`holding_sessions=10`；
- 它们不是 5 桶或 10 桶的缩写；冻结 primary 都使用 `EW + decile(K=10) + project_conservative_close_to_close_proxy`。

### 2.2 三种容易混淆的周数 denominator

| Denominator | 含义 | 5×5 FULL | 10×10 FULL |
|---|---|---:|---:|
| favorable standalone weeks | favorable bucket 自身可评价 | 405 | 391 |
| favorable/spread joint weeks | favorable 与 unfavorable 两端共同可评价，用于 stability/dominance | 386 | 367 |
| residual/total paired weeks | Residual 与 matched Total 在同周共同可评价 | 373 | 347 |

因此，原报告中的 favorable mean、stability mean 和 paired SRC mean 可能略有不同。这不是重复统计矛盾，而是 denominator 不同。本文在每张表中显式标注口径，不把 unpaired means 相减。

### 2.3 收益单位与边界

- 表中 `bp` 是对应 holding horizon 的 gross close-to-close return；`28.06 bp/10D` 不是单日收益，也不是净收益。
- `EARLY = 2018-01-26..2022-03-18`，`LATE = 2022-03-25..2026-05-22`，各有 213 个 signal-possible weeks。
- 2017-01-06 至 2018-01-19 的 54 周属于 rolling-regression warm-up，不进入 fold。
- 所有 registered denominator rows 均被乐观地假设可交易；没有逐日停牌、涨跌停成交约束、next-open fill、现金腿、持续资本、实际滑点或 minimum commission。

## 3. 数据规模、lineage 与完整性

### 3.1 冻结设计与主要物化规模

| Artifact / audit | Rows |
|---|---:|
| arm/horizon registry | 84 |
| weekly calendar | 480 |
| daily return resolution audit | 4,114,924 |
| daily market residual panel | 3,656,484 |
| rolling market-model audit | 3,656,484 |
| weekly signal panel | 1,200,000 |
| weekly bucket assignment | 2,400,000 |
| forward return resolution | 960,000 |
| bucket return panel | 481,920 |
| arm summary statistics | 1,212 |
| HAC / block-bootstrap inference | 2,424 |
| horizon path decomposition | 144,000 |
| dominance audit | 3,755 |
| paired residual-vs-total attribution | 48 |
| style morphology attribution | 962 |
| turnover / break-even cost | 80 |

`U_ever=1,803`，每个 registered week 的 project denominator 为 500。所有 signal/outcome access firewall 均通过，`future_rows_contributed_to_signal=0`，signal stage 没有读取 outcome-role table。

### 3.2 Signal coverage 不是阻断项

| Arm | Pass weeks | First / last pass | Median eligible N | Minimum eligible N | Median coverage | Minimum coverage | Minimum observed bucket N |
|---|---:|---|---:|---:|---:|---:|---:|
| 5D Residual | 426 | 2018-01-26 / 2026-05-22 | 481 | 429 | 96.2% | 85.8% | 42 |
| 10D Residual | 426 | 2018-01-26 / 2026-05-22 | 480 | 427 | 96.0% | 85.4% | 42 |

两个 arm 的 median coverage 均远高于冻结的 `70%` floor，minimum eligible N 也远高于 `100`。每周 decile 至少约 42 只股票，说明失败不是由无法分桶或极小 bucket 造成。

### 3.3 Outcome-evaluable support 也足够

| Primary series | FULL | EARLY | LATE | Frozen floor | Gate |
|---|---:|---:|---:|---:|---|
| 5D favorable standalone | 405 | 201 | 204 | 156 / 78 / 78 | pass |
| 5D residual-vs-total paired | 373 | 177 | 196 | 156 / 78 / 78 | pass |
| 10D favorable standalone | 391 | 191 | 200 | 156 / 78 / 78 | pass |
| 10D residual-vs-total paired | 347 | 159 | 188 | 156 / 78 / 78 | pass |

这一点很关键：终态不是 `underpowered`。在当前冻结门下，样本已经足以对“是否值得推进”作出 design-only 否定判断。

## 4. Matched primary：绝对收益结果

### 4.1 5D formation × H5

以下使用 favorable standalone weeks：

| Fold | N | Mean | Median | Positive rate | Annualized arithmetic mean | Annualized vol | Diagnostic Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| FULL | 405 | -5.21 bp | -6.38 bp | 49.14% | -2.62% | 21.87% | -0.120 |
| EARLY | 201 | -16.05 bp | +0.00 bp | 50.25% | -8.09% | 23.47% | -0.345 |
| LATE | 204 | +5.47 bp | -6.70 bp | 48.04% | +2.76% | 20.20% | +0.137 |

FULL 的 10% left-tail threshold 为 `-3.70%`，ES10 loss 为 `5.59%`，worst cohort 为 `-9.76%`。LATE 虽然均值略正，但中位数仍为负、positive rate 低于 50%，更像少数右尾周抬高均值，而不是稳定的 1 周 continuation。

### 4.2 10D formation × H10

| Fold | N | Mean | Median | Positive rate | Annualized arithmetic mean | Annualized vol | Diagnostic Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| FULL | 391 | +28.06 bp | +0.79 bp | 50.13% | +7.07% | 25.56% | +0.277 |
| EARLY | 191 | -10.71 bp | -26.63 bp | 48.17% | -2.70% | 24.02% | -0.112 |
| LATE | 200 | +65.07 bp | +16.28 bp | 52.00% | +16.40% | 26.88% | +0.610 |

FULL 的 ES10 loss 为 `7.54%`，worst cohort 为 `-17.68%`。这里可以看到两个事实同时成立：

1. 10D 的 full-sample point estimate 确实比 5D 更有经济方向；
2. mean、median 与 positive rate 的差距很大，而且 EARLY 为负，说明均值并不是均匀、稳定地来自大多数周。

## 5. 为什么 positive-exposure gate 失败

冻结 gate 不是要求 FULL mean 单独大于零，而是要求 matched primary 的 FULL、EARLY、LATE favorable mean 全部严格大于零。

| Primary | FULL | EARLY | LATE | Gate |
|---|---:|---:|---:|---|
| 5D × H5 | -5.21 bp | -16.05 bp | +5.47 bp | fail |
| 10D × H10 | +28.06 bp | -10.71 bp | +65.07 bp | fail |

5D 同时败在 FULL 与 EARLY；10D 只败在 EARLY，但这正是稳定性门存在的原因。若在看到 LATE 后删掉 EARLY 或移动 fold cut，就会把 outcome-contaminated historical diagnostic 变成事后选 regime。

## 6. Sort morphology：高分组是否稳定优于低分组

Stability table 使用 favorable/unfavorable 共同可评价周：

| Primary | Fold | Joint N | Favorable mean | Favorable-minus-unfavorable | Favorable > 0 | Spread > 0 |
|---|---|---:|---:|---:|---|---|
| 5D × H5 | FULL | 386 | -5.12 bp | -24.69 bp | no | no |
| 5D × H5 | EARLY | 190 | -13.63 bp | -29.93 bp | no | no |
| 5D × H5 | LATE | 196 | +3.13 bp | -19.62 bp | yes | no |
| 10D × H10 | FULL | 367 | +38.78 bp | +8.66 bp | yes | yes |
| 10D × H10 | EARLY | 175 | +1.11 bp | -13.39 bp | yes | no |
| 10D × H10 | LATE | 192 | +73.11 bp | +28.75 bp | yes | yes |

5D spread 三个 fold 全负，不存在正确的 cross-sectional continuation morphology。10D 的 joint sample 中 favorable 在三个 fold 略为正，但 EARLY spread 为负；也就是说，EARLY 高分组的绝对收益接近零，却没有稳定跑赢低分组。

Spread 只能说明排序形态，不能替代 long-only favorable bucket 的绝对收益。反过来，favorable 为正但 spread 为负，也可能只是整个 positive-beta universe 同涨，而非 score 提供了有用区分。

## 7. Residual vs Total：对原报告 line 61 的完整展开

以下全部使用 Residual 与 matched Total 在同一周共同可评价的 paired population。

### 7.1 5D Residual vs 5D Total

| Fold | Paired N | Residual favorable | Total favorable | Residual − Total | Residual spread | Total spread | Spread delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 177 | -6.24 bp | +7.13 bp | -13.38 bp | -33.41 bp | -11.73 bp | -21.69 bp |
| FULL | 373 | -1.32 bp | +4.31 bp | -5.63 bp | -26.16 bp | -14.13 bp | -12.03 bp |
| LATE | 196 | +3.13 bp | +1.75 bp | +1.37 bp | -19.62 bp | -16.31 bp | -3.31 bp |

FULL favorable volatility ratio 为 `1.012`，ES10 loss ratio 为 `1.028`：Residual 既没有提高收益，也没有降低波动或尾部损失。

5D 冻结标准要求：

- FULL favorable delta 至少 `+5 bp`，或 spread/risk 达到等价 material improvement；
- EARLY 与 LATE favorable delta 均不得低于 `-2.5 bp`。

实际 FULL 为 `-5.63 bp`，EARLY 为 `-13.38 bp`，所以不是 borderline，而是明确失败。

### 7.2 10D Residual vs 10D Total

| Fold | Paired N | Residual favorable | Total favorable | Residual − Total | Residual spread | Total spread | Spread delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 159 | -0.61 bp | +5.04 bp | -5.64 bp | -15.00 bp | +1.39 bp | -16.39 bp |
| FULL | 347 | +44.12 bp | +38.23 bp | +5.88 bp | +8.36 bp | +25.95 bp | -17.59 bp |
| LATE | 188 | +81.94 bp | +66.31 bp | +15.63 bp | +28.12 bp | +46.72 bp | -18.60 bp |

10D 的 FULL favorable delta 为正，但仍失败，原因可以机械拆解：

| Frozen branch | Requirement | Observed | Result |
|---|---:|---:|---|
| Favorable materiality | FULL ≥ +10 bp | +5.88 bp | fail |
| Fold non-degradation | EARLY ≥ -5 bp | -5.64 bp | fail by 0.64 bp |
| Spread materiality | FULL ≥ +10 bp | -17.59 bp | fail |
| Volatility improvement | ratio ≤ 0.95 | 1.072 | fail |
| ES10 improvement | ratio ≤ 0.95 | 0.966 | fail |

Residual 10D 的 LATE favorable 改善是真实存在的 paired point estimate，但 FULL 改善不够大、EARLY 略超容忍线、spread 在三个 fold 全部比 Total 更差。故 `SRC_10x10_residualization_value=False` 是多项证据共同决定的，不是单一阈值误杀。

### 7.3 最重要的 attribution insight

这组 paired 结果更接近：

```text
short-window continuation payoff exists in parts of the sample
but market residualization is not the source of the payoff
```

而不是：

```text
market residualization creates an independent short-term alpha
```

换句话说，当前 10D 结果即使保留研究兴趣，也首先是 **Total continuation / regime payoff** 的线索，而不是 Residual Momentum 已被确认。

## 8. 完整 formation × holding matrix

以下仍是冻结的 `project + EW + decile`，单位为 horizon bp：

| Formation × Holding | Role | Favorable FULL | EARLY | LATE | Spread FULL | EARLY | LATE |
|---|---|---:|---:|---:|---:|---:|---:|
| 5D × H5 | matched primary | -5.21 | -16.05 | +5.47 | -24.69 | -29.93 | -19.62 |
| 5D × H10 | cross-decay | +5.67 | -36.07 | +44.49 | -24.05 | -30.28 | -18.53 |
| 10D × H5 | cross-decay | +6.30 | -15.30 | +26.97 | -5.88 | -24.06 | +10.96 |
| 10D × H10 | matched primary | +28.06 | -10.71 | +65.07 | +8.66 | -13.39 | +28.75 |

矩阵呈现一致的时间结构：四个 cell 的 favorable 都是 EARLY 弱、LATE 强；5D score 的 spread 即使延长到 H10 仍全 fold 为负；10D score 延长至 H10 才在 FULL/LATE 显示正 spread。

这更像“2022 年后出现的、需要较长 realization window 的 payoff”，而不是 formation 越短、立即延续越强的经典短期 continuation。

## 9. Weighting、bucket 与 outcome sensitivity

每个 matched primary 有 8 个 secondary specifications：

```text
2 return semantics × 2 weighting(EW/VW) × 2 bucket counts(quintile/decile)
```

三个 fold 同时大于零的数量：

| Arm | Favorable all-fold positive | Spread all-fold positive |
|---|---:|---:|
| 5D × H5 | 0 / 8 | 0 / 8 |
| 10D × H10 | 5 / 8 | 4 / 8 |

### 9.1 5D robustness

5D 的结论很稳定：所有 EW/VW、quintile/decile、project/complete-case 组合都无法让 favorable 或 spread 在三个 fold 同时为正。它不是 primary 选择过严造成的假阴性。

### 9.2 10D robustness

10D 的 secondary morphology 值得记录，但不能替代冻结 primary：

- project + EW + quintile favorable 为 `EARLY +3.82 bp / FULL +31.84 bp / LATE +57.03 bp`，但 EARLY spread 仍为 `-14.34 bp`；
- project + EW + decile favorable 即 primary，为 `-10.71 / +28.06 / +65.07 bp`；
- complete-case + EW + decile EARLY favorable 为 `-3.29 bp`，仍为负，因此 primary failure 不能简单归因于 project-conservative outcome gaps；
- 四个 VW variants 的 favorable 与 spread 都在三个 fold 为正。

这说明 10D payoff 对 portfolio weighting 很敏感。更准确的表述是“收益实现偏向 value-weighted payoff”，而不是“score 本身是 size factor”：后面的 style audit 显示 score 与 log market cap 的中位 rank correlation 接近零，size warning 也没有触发。

VW sensitivity 只能生成机制问题，不能事后把 VW 提升为 primary。否则会在已经看见 outcome 后更换冻结决策口径。

## 10. Score morphology、LowVol、size 与 beta

| Metric（weekly median） | 5D Residual | 10D Residual |
|---|---:|---:|
| Spearman vs matched Total score | 0.931 | 0.938 |
| Top-decile Jaccard vs Total | 0.548 | 0.600 |
| Spearman vs `-VOL20` | -0.024 | -0.060 |
| Top-decile Jaccard vs LowVol | 0.044 | 0.034 |
| Spearman vs log market cap | 0.004 | 0.011 |
| Favorable-bucket weighted beta | 0.953 | 0.949 |

### 10.1 Findings

1. Residual 与 Total 的 rank correlation 非常高，top decile 仍有约 55%–60% 重合。这直接解释了 residualization paired delta 较小：市场残差化没有构造出一个完全不同的短周期横截面排序。
2. LowVol overlap 很低，score 与 size rank correlation 也接近零，因此结果不是明显的 LowVol 或静态 size proxy。
3. Favorable bucket beta 中位数约 `0.95`，符合 positive-beta research 的方向，但“beta 为正”不等于 favorable return 或 residual alpha 已通过。
4. VW 比 EW 表现更好与“score-size correlation 很低”可以同时成立：前者是 **realized return weighting**，后者是 **signal ranking morphology**。当前 warning 只排除了明显的 score-level size dependence，没有排除 payoff 在大权重股票上更强。

## 11. 年度稳定性

以下使用 favorable/spread joint-evaluable weeks，单位为 bp：

| Year | 5D favorable | 5D spread | 10D favorable | 10D spread |
|---|---:|---:|---:|---:|
| 2018 | -52.43 | -22.63 | -32.56 | +16.16 |
| 2019 | +9.43 | -46.32 | +20.64 | -41.44 |
| 2020 | +14.64 | -9.72 | +61.68 | +32.71 |
| 2021 | -5.46 | -20.46 | +1.46 | -29.49 |
| 2022 | -73.34 | -72.15 | -91.18 | -69.18 |
| 2023 | -37.64 | +9.39 | -59.79 | -13.40 |
| 2024 | -2.47 | -63.63 | +118.75 | -9.04 |
| 2025 | +64.39 | -4.55 | +191.57 | +79.78 |
| 2026* | +86.11 | +79.21 | +292.38 | +356.94 |

`2026*` 只有 15 个 5D、14 个 10D evaluable weeks，是 partial year。

5D favorable 只有 4/9 个年份为正，spread 只有 2/9 为正，两者同时为正仅 2026。10D favorable 有 6/9 年为正，spread 有 4/9 年为正，两者同时为正的是 2020、2025 与 partial 2026。

10D FULL 正均值因此不是一个平稳的九年效应：2022–2023 明显为负，2024 favorable 转强但 spread 仍负，2025–2026 才同时变强。这是 regime concentration，而不是单一异常值 dominance。

## 12. Horizon path：收益发生在第几天

以下使用 decile favorable、project/EW、H5/H10 joint-evaluable population。由于 denominator 更严格，R1-10 mean 与 standalone H10 mean 不必完全相同。

| Signal | Fold | Joint N | R1-5 | R6-10 | R1-10 |
|---|---|---:|---:|---:|---:|
| 5D Residual | FULL | 382 | -8.83 bp | +12.36 bp | +3.84 bp |
| 5D Residual | EARLY | 183 | -21.47 bp | -16.33 bp | -37.66 bp |
| 5D Residual | LATE | 199 | +2.79 bp | +38.75 bp | +42.01 bp |
| 10D Residual | FULL | 379 | +1.19 bp | +21.43 bp | +22.81 bp |
| 10D Residual | EARLY | 182 | -20.65 bp | +1.96 bp | -19.35 bp |
| 10D Residual | LATE | 197 | +21.37 bp | +39.41 bp | +61.77 bp |

### 12.1 Insight

- 5D signal 在 FULL 的前 5 日为负，后 5 日才回补；它不支持“1 周 immediate residual continuation”。
- 10D signal 在 FULL 的收益主要来自第 6–10 日：`+21.43 bp`，而第 1–5 日只有 `+1.19 bp`。
- EARLY 的 10D 第 1–5 日为 `-20.65 bp`，第 6–10 日接近零；LATE 两段都转正，且后半段更强。

所以 10D 线索更像 **delayed payoff + late-regime strengthening**。如果把它简单命名为 short-term immediate continuation，会掩盖真正的 path morphology。

## 13. Dominance：是否由少数周、月份或股票驱动

Dominance 使用 favorable/spread joint population：

| Audit | 5D × H5 | 10D × H10 |
|---|---:|---:|
| Base favorable mean | -5.12 bp | +38.78 bp |
| Base spread mean | -24.69 bp | +8.66 bp |
| Max single-week absolute contribution share | 1.59% | 3.66% |
| Top-3 week absolute contribution share | 3.77% | 7.26% |
| LOMO favorable range | -10.16..+0.83 bp | +17.22..+48.49 bp |
| LOMO spread range | -29.05..-20.97 bp | +0.27..+15.25 bp |
| LOIO favorable range | -5.79..-4.51 bp | +36.29..+39.45 bp |
| H5/H10 joint correlation | 0.657 | 0.651 |

5D 的负方向不会因删除某个股票而消失；10D 的正 full-sample mean 也不是单周、单月或单股票制造，leave-one-month-out 的 favorable 与 spread 均保持正值。

这并不与 fold failure 冲突：LOMO 每次只删除一个月份，检验的是局部 dominance；EARLY/LATE 检验的是持续数年的 regime stability。10D 通过前者、失败后者，说明它不是 outlier-driven，但仍然 regime-dependent。

## 14. HAC、block bootstrap 与不确定性

| Primary favorable | N | Estimate | HAC 95% CI | HAC p | 13-week block-bootstrap 95% CI | Bootstrap p | Holm p |
|---|---:|---:|---:|---:|---:|---:|---:|
| 5D × H5 | 405 | -5.21 bp | [-36.77, +26.36] bp | 0.746 | [-37.71, +20.72] bp | 0.734 | 0.845 |
| 10D × H10 | 391 | +28.06 bp | [-40.51, +96.62] bp | 0.423 | [-40.09, +90.50] bp | 0.423 | 0.845 |

HAC 使用 lag 4；block bootstrap 使用 non-circular 13-week contiguous blocks、5,000 repetitions。两个 primary 的区间都跨零，Holm family size 为 2，调整后 p-value 都为 `0.845`。

这些统计量不是 gate 的替代品，但它们与 gate 给出一致信息：5D 没有正方向，10D 点估计虽正但不确定性很大，无法与零清晰分离。

## 15. Turnover 与成本压力测试

| Primary | Transitions | Mean target turnover | Mean gross return | Break-even one-way cost | Frozen one-way cost | Multiple | Cost gate |
|---|---:|---:|---:|---:|---:|---:|---|
| 5D × H5 | 404 | 89.57% | -3.82 bp | -2.13 bp | 10.15 bp | -0.210× | fail |
| 10D × H10 | 390 | 69.25% | +31.47 bp | 22.72 bp | 10.15 bp | 2.239× | pass |

5D 在成本前均值已经为负。10D 的 break-even multiple 高于冻结 floor `1.25×`，所以 design-level cost pressure test 通过。

但 10D cost pass 不能解释为“策略净收益可执行”，因为该 proxy：

- 假设 registered rows 均可交易；
- 没有 blocked entry/exit 与涨跌停；
- 历史统一使用现行 5 bps stamp tax，而非历史税率；
- 没有 5 CNY minimum commission；
- 使用 target turnover，不是逐笔 fill 与持续 NAV。

因此成本结果只能说明“当前 gross mean 没有立刻被冻结成本 proxy 吞没”，不能越过 positive-exposure、residualization 或 execution gates。

## 16. 综合 findings

### Finding 1：5D 是稳定的负结论

5D 的问题不是统计功效、数据覆盖或某个异常月。它在 primary、cross H10、8 个 secondary specifications、paired attribution、spread 与 cost 上都缺乏支持。当前设计下，没有理由继续把 1 周 residual continuation 当作独立候选。

### Finding 2：10D 是“有形态但未识别”

10D 同时具备：

- FULL/LATE 正 favorable；
- cost proxy 可承受；
- 非单周、单月、单股票驱动；
- 多个 VW/quintile sensitivity 为正。

但也同时存在：

- 冻结 EW/decile EARLY 为负；
- 年度结果集中于 2025–2026；
- HAC/bootstrap 区间宽且跨零；
- paired residualization materiality 不足；
- spread 相对 Total 在所有 fold 都更差。

所以它不是“完全没有研究信息”，却也不能写成“Residual Momentum 已经找到”。准确分类仍是 `not_identified_design_only`。

### Finding 3：真正值得解释的是 Total overlap，而不是继续调 residual window

Residual 与 Total score correlation 接近 `0.94`，top decile 重合约 60%。这意味着短 window 的市场成分扣除没有强烈改变横截面身份。继续在同一历史上调 7D、8D、12D 或换 residual normalization，很容易只是在高相关信号附近做 outcome-driven search。

当前证据更支持把机制问题写成：

```text
为什么 10D total/residual continuation 在 late regime、VW 和第 6–10 日更强？
```

而不是：

```text
怎样调参让 residual momentum primary gate 通过？
```

### Finding 4：size warning 没触发，不等于 weighting 不重要

Score 与 log market cap 的 rank correlation 接近零，说明没有静态 size-score proxy；但所有 VW variants 表现更稳定，说明 realized payoff 对 constituent weight 可能敏感。未来若重新打开研究，应该把“signal morphology”与“portfolio weighting payoff”分成两个归因问题，而不是用单一 size warning 概括。

### Finding 5：不能据此降级为 meta-label

Meta-label/participation filter 至少需要一个稳定、低成本、具有增量条件信息的信号。5D 方向与成本均差；10D 虽成本可行，但 early instability 与 residualization false 表明它尚未证明独立条件价值。因此 `participation_meta_label_research_recommended=false` 是合理的，而不是过度保守。

## 17. 10D 与原始 1M Residual Momentum 的逐年比较

这不是同一 signal 只改变 holding horizon 的 sensitivity：

- 原始 1M P4 使用月度 `t-11...t-1` residual momentum，持有 1 个月；
- 当前 10D 使用逐日 immediate 10-session residual continuation，持有 10 个交易日。

比较时保留各自冻结的 `project + EW + decile favorable bucket`。10D 机械年化为 `mean 10D return × 252/10`；1M 机械年化为 `mean monthly return × 12`。两者都不是 compounded CAGR 或成本后收益。

为与两份原报告的 FULL favorable headline 一致，本节 10D favorable 使用 standalone favorable-evaluable weeks，spread 使用 favorable/unfavorable joint-evaluable weeks。Section 11 为了年度 stability 同时比较 favorable 与 spread，统一使用 joint weeks，因此其中 10D favorable 年度数字会与本节略有差异。

| Year | 10D N（Fav/Spread） | 10D favorable 年化 | 10D spread 年化 | 1M N | 1M favorable 年化 | 1M spread 年化 |
|---|---:|---:|---:|---:|---:|---:|
| 2018 | 42 / 32 | -27.72% | +4.07% | — | — | — |
| 2019 | 49 / 45 | +4.38% | -10.44% | — | — | — |
| 2020 | 42 / 41 | +22.00% | +8.24% | — | — | — |
| 2021 | 49 / 48 | +1.79% | -7.43% | 9 | -14.35% | -7.67% |
| 2022 | 46 / 46 | -22.98% | -17.43% | 9 | +14.82% | +17.50% |
| 2023 | 48 / 47 | -13.19% | -3.38% | 11 | -13.49% | +39.74% |
| 2024 | 48 / 46 | +27.15% | -2.28% | 6 | +21.51% | +32.54% |
| 2025 | 50 / 48 | +42.99% | +20.10% | 8 | +39.29% | +14.31% |
| 2026* | 17 / 14 | +55.27% | +89.95% | — | — | — |
| **FULL** | **391 / 367** | **+7.07%** | **+2.18%** | **43** | **+6.96%** | **+19.43%** |

`2026*` 的 10D 只有 17 个 favorable weeks、14 个 spread weeks，是截至 2026-05-22 的 partial year。原始 1M 在 2026 没有通过 whole-arm project-conservative resolution 的可评价月；不得用 bucket-level 局部可评价值补入 primary。

### 17.1 逐年发现

1. **FULL long-only gross 基本持平。** 10D favorable 机械年化为 `+7.07%`，1M 为 `+6.96%`，差异只有 `+0.11` 个百分点；没有证据表明缩短到 10D 提高了 unconditional long-only mean。
2. **FULL spread 大幅下降。** 10D spread 年化只有 `+2.18%`，原始 1M 为 `+19.43%`，下降约 `17.25` 个百分点或 `88.8%`。短周期 residual score 的横截面区分力明显更弱。
3. **2021 两者都没有正 spread。** 10D/1M spread 年化分别为 `-7.43%/-7.67%`；10D favorable 较好，但仍接近零。
4. **2022 的方向完全相反。** 10D favorable/spread 均明显为负，1M 两者均为正，说明 horizon/family 对市场状态高度敏感。
5. **2023 不能把 1M 的高 spread 当成 long-only alpha。** 两者 favorable 年化都约 `-13%`，但 1M spread 达 `+39.74%`，主要含义是 unfavorable bucket 跌得更多。
6. **2024–2025 favorable 都较强，但 spread 不一致。** 2024 的 10D favorable 为正而 spread 仍负；2025 两者才都为正。10D 的 full mean 因此不是稳定地来自每个年份。
7. **样本质量不同。** 10D 有 `391/367` 个 weekly favorable/spread observations；1M 只有 43 个可评价月，每个年度仅 6–11 个月。1M 的高 spread 方向值得记录，但逐年估计的不确定性明显更高。

### 17.2 比较结论

若 performance 指 favorable long-only gross，10D 与 1M 的 FULL 机械年化几乎相同；若 performance 指 Residual Momentum 应有的 cross-sectional sorting edge，10D 明显下降。结合 10D 与 Total score 的高重合及 paired residualization value=false，更合理的结论是：

```text
10D did not improve the long-only annualized mean,
and materially weakened the residual-momentum spread.
```

所以 10D 的正收益不能解释为原始 1M Residual Momentum 的增强版；它更像样本更充分、但排序更弱且 regime-dependent 的 short-term continuation adaptation。

## 18. AFML 决策含义

从 AFML 角度，当前 family 的问题不是单纯的 p-value，而是 utility morphology 没有同时满足：

```text
sample support
    -> pass
absolute positive exposure across folds
    -> fail
sort morphology across folds
    -> fail
residualization incremental value
    -> fail
cost pressure
    -> 5D fail / 10D pass
style evaluability
    -> pass
```

因此：

1. 不应生成 20C requirement；
2. 不应 true-forward freeze；
3. 不应训练 policy 或把 10D arm 直接加入 portfolio optimizer；
4. 不应在同一污染历史上根据 VW、quintile、2025–2026 或 H10 的结果重新选择 primary；
5. 可以保留一个研究事实：**若未来有独立的新样本或新的、预先冻结的机制诊断，最值得核验的是 10D late/VW/delayed-payoff morphology，而不是 5D immediate continuation。**

最后一句结论：**当前结果排除了 1 周 Residual Momentum，也没有确认 2 周 Residual Momentum；2 周只留下了 regime-dependent continuation 线索，而且现有证据更像 Total continuation payoff，而不是 residualization 带来的独立 alpha。**

## 19. 数据来源与 no-authorization footer

本文只读引用以下 sealed artifacts：

- `historical/arm_summary_statistics.csv`
- `historical/fold_and_year_stability.csv`
- `historical/paired_residual_vs_total_attribution.csv`
- `historical/hac_and_block_bootstrap_inference.csv`
- `historical/horizon_path_decomposition.csv`
- `historical/month_instrument_dominance_audit.csv`
- `historical/style_morphology_attribution.csv`
- `historical/turnover_break_even_cost_readout.csv`
- `historical/bucket_return_panel.csv.gz`
- `signal/signal_coverage_audit.csv`
- `preoutcome/calendar_freeze.csv`
- `preoutcome/sample_floor_and_gate_registry.csv`
- `20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5/historical/monthly_bucket_returns.csv.gz`
- `20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5/historical/monthly_signal_support.csv`

本文不属于 sealed v0 manifest，不改变任何 bundle hash、decision state 或 authorization。`next_requirement_generation_authorized=false`，`true_forward_execution_authorized=false`，`20C_requirement_generation_authorized=false`，`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。
