# Explore9 P0 大涨股早期结构广度探索详细报告

> 本报告是对 Explore9 P0 已生成 CSV / JSON 结果的人工研究解读，不由 `explore9-report` 命令重新生成。
> 后续如果再次运行 `uv run python Explore9/scripts/run_explore9.py explore9-report ...`，本手工报告会被覆盖。

## 1. 核心结论

Explore9 P0 的主要结论不是“已经找到可交易策略”，而是：PIT universe 中的年度大涨股在早期到中期修复阶段，确实存在一组可观察结构，但这些结构更像 **winner discovery / continuation confirmation / hold tolerance** 的线索，而不是可以直接冻结的入场规则。

最重要的发现有五点：

1. **P0 最低覆盖已经满足**
   `broad_discovery_p0_minimum_coverage_met = true`。本轮覆盖了 `11` 类 feature family、`55` 个 P0 单变量原语、`10` 个双变量组合，并输出 `8` 条 preliminary discovery leads。

2. **最强线索不是低波压缩，而是高波动扩张和强趋势速度**
   `volatility60 == p90_100` 的 120 日 50% high 命中率为 `24.99%`，lift `2.00`；`amplitude20 == p90_100` 命中率 `23.18%`，lift `1.86`；`atr20_pct == p90_100` 命中率 `23.13%`，lift `1.86`。反过来，低波动分箱是最弱的一组，`volatility60 == p0_10` 的 lift 只有 `0.28`。这说明大 winner 的可观察结构更接近“波动扩张中的强势延展”，而不是传统意义上安静压缩后的低风险启动。

3. **相对强度有效，但更像确认条件，不足以单独解决早期发现**
   `ret20_universe_pctile == p90_100` 的 120 日 50% high 命中率为 `21.11%`，lift `1.69`；`relative_ret60_vs_benchmark == p90_100` 命中率 `20.67%`，lift `1.66`。它们覆盖 8 个年份、行业集中度不高，是值得进入 P1 的方向。但它们本质上要求 T 日已经表现出强势，因此不是“底部最早识别器”。

4. **post-20% / post-30% continuation 是明确的 hold/refine 方向**
   `post_30pct_from_recent_low == true` 的样本有 `86,575` 个，120 日 50% high 命中率 `20.02%`，lift `1.60`。双变量 `已涨20% + 仍然相对强` 的 120 日 50% high 命中率 `19.25%`，lift `1.54`；240 日 100% high 命中率 `11.77%`，lift `1.63`。这不是初始买点，但对 Explore8 暴露出的 early_exit 问题很重要：有些已经涨过 20% / 30% 的 winner 不应该被普通 time stop / stop loss 规则过早处理。

5. **Explore9 尚未真正解决“足够早”的问题**
   最强的 `observable_late_acceleration_risk` 命中率最高，120 日 50% high 命中率 `35.86%`，lift `2.87`，但它的语义已经偏后段：平均到 50% high 的 lead time 约 `64` 个交易日，且 2020 年贡献明显，2022/2024 的年度 lift 为 0。它更适合 P1 中做“末端加速识别”和“持有/减仓容忍度”研究，而不是直接升级为 early discovery 主线。

本轮结论可以进入 P1 hypothesis refine，但不能进入 Explore10 策略回测。P1 的重点应该是把“高波扩张、相对强度、修复延展、行业宽度共振”拆成可解释、可审计、按年份稳定的候选假设。

## 2. 数据纪律与可用性

Explore9 P0 使用的计算输入是 Explore7 PIT universe、PIT industry membership、target history 和 Qlib PIT provider。Explore8 输出只作为背景和 schema/audit reference，不进入 label、signal 或 selection。

| 项目 | 结果 |
| --- | --- |
| 主研究期 | 2017-01-01 至 2024-12-31 |
| observed reference | 2025-01-01 至 2026-04-30，仅用于观察，不用于选择 |
| stock-day label panel | 439,140 行，170 列 |
| PIT instruments | 539 |
| provider | `Explore7/data/qlib/cn_data_pit` |
| fallback provider used | false |
| price adjustment | `provider_ohlc_already_adjusted` |
| Explore8 label/signal/selection use | 全部 false |
| historical trade results use | false |

### 2.1 Provider 覆盖

2017-2026 的 PIT membership 行情覆盖都为 `coverage_ok`，研究期 2017-2024 每年必需字段覆盖率均为 `100%`。这意味着 P0 的主要限制不是 provider 缺失，而是标签 horizon、warmup 和 stock-day 去重问题。

| 年份 | PIT stock-days | 必需字段覆盖率 | 覆盖状态 |
| --- | ---: | ---: | --- |
| 2017 | 18,497 | 100.00% | coverage_ok |
| 2018 | 33,698 | 100.00% | coverage_ok |
| 2019 | 36,651 | 100.00% | coverage_ok |
| 2020 | 48,165 | 100.00% | coverage_ok |
| 2021 | 59,241 | 100.00% | coverage_ok |
| 2022 | 55,241 | 100.00% | coverage_ok |
| 2023 | 54,481 | 100.00% | coverage_ok |
| 2024 | 51,916 | 100.00% | coverage_ok |

### 2.2 Forward label 覆盖

P0 同时计算 high-gain 和 close-gain 标签。high-gain 数量显著高于 close-gain，尤其短 horizon 更明显：20 日内达到 50% high 的样本中，约 `30.74%` 没有对应 close 确认；120 日下降到 `13.00%`；240 日下降到 `9.94%`。这说明短线 spike 对标签有较大影响，P1 不能只看 intraday high，需要继续区分 close-confirmed winner。

| Horizon | 研究样本 | horizon valid | 50% high | 50% close | high-only 占 high | 100% high | 100% close |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20d | 357,890 | 354,928 | 2,476 | 1,715 | 30.74% | 132 | 99 |
| 60d | 357,890 | 349,684 | 18,855 | 15,444 | 18.09% | 2,044 | 1,650 |
| 120d | 357,890 | 342,821 | 43,675 | 37,996 | 13.00% | 8,212 | 6,990 |
| 240d | 357,890 | 330,964 | 83,439 | 75,147 | 9.94% | 23,749 | 21,450 |

2024 年 240 日 horizon 有 `93.93%` 的样本跨入 observed reference，因此 240 日结论不能简单把 2024 当完整研究年。主 lift 已排除 observed reference overlap 样本；报告解读也必须避免用 2025-2026 结果选择特征。

### 2.3 Episode 复核

Explore9 独立重算得到 `734` 个 in-year episode，与 Explore8 报告中的年度大涨 episode 数一致；另有 `286` 个 cross-year episode，用于识别自然年切割问题。

| 年份 | in-year episodes | 股票数 | 平均 intraday gain | 中位持续交易日 |
| --- | ---: | ---: | ---: | ---: |
| 2017 | 34 | 34 | 67.15% | 80.5 |
| 2018 | 19 | 19 | 63.37% | 68.0 |
| 2019 | 90 | 90 | 89.74% | 121.0 |
| 2020 | 140 | 140 | 117.55% | 129.0 |
| 2021 | 151 | 151 | 103.27% | 83.0 |
| 2022 | 93 | 93 | 80.81% | 55.0 |
| 2023 | 46 | 46 | 82.01% | 77.5 |
| 2024 | 161 | 161 | 74.81% | 157.0 |

机会年份不是均匀分布的。2020、2021、2024 的 episode 数量高，而 2018、2023 明显弱。这会影响所有 lift 的解释：一个线索即使 pooled lift 很高，也必须看它在弱年份是否仍然有正 lift。

## 3. P0 搜索覆盖

P0 coverage audit 全部通过。

| 检查项 | 实际 | 要求 | 结果 |
| --- | ---: | ---: | --- |
| feature family registry | 11 | 10 | pass |
| P0 univariate primitives | 55 | 30 | pass |
| pairwise combos | 10 | 10 | pass |
| preliminary discovery leads | 8 | 5 | pass |
| 非 EMA / breakout / pullback leads | 8 | 3 | pass |
| relative strength / industry leads | 2 | 2 | pass |
| money / volatility leads | 3 | 2 | pass |
| continuation / hold leads | 1 | 1 | pass |

Warmup 的主要影响来自 120/240 日窗口。`drawdown_from_high240` 和 `repair_from_low240` 的 eligible rows 为 `389,992`，缺失/不足明显高于短窗口，首个完整可用日期到 2017-12-26。2017 年使用 240 日相关指标时要降低结论权限。

## 4. 单变量发现：哪些结构真的有 lift

### 4.1 最强线索：已进入末端加速风险的可观察状态

`observable_state_stage == observable_late_acceleration_risk` 是单变量里最高 precision 的线索：

| 指标 | 数值 |
| --- | ---: |
| stock-day 样本 | 5,967 |
| 120 日 50% high precision | 35.86% |
| 240 日 100% high precision | 21.92% |
| lift vs baseline | 2.87 |
| distinct years | 8 |
| distinct industries | 24 |
| top1 industry concentration | 18.25% |
| avg lead time to 50% | 64.34 个交易日 |
| avg future max gain | 44.68% |
| avg drawdown before gain | -10.10% |

但它不能简单解释为“早期买点”。年度稳定性显示，2020 年 lift 达到 `2.05`，但 2022 和 2024 为 0，2018 也低于 baseline。这个状态更像已经发生较大涨幅和趋势年龄后的继续冲刺窗口。它对 P1 的意义是：

- 作为 early discovery 线索不够早。
- 作为 winner hold / late acceleration / 减仓风险线索值得保留。
- 必须在 P1 中拆分为“继续扩展”和“末端过热”两个方向，否则会把趋势延展和回撤风险混在一起。

### 4.2 高波动、高 ATR、高振幅是稳定 winner 线索

高波动相关原语表现最一致。低波动并没有更早找到 winner，反而显著低于 baseline。

| 原语 | 分箱 | 样本 | 120d 50% high | lift | 240d 100% high | 年份正 lift |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| volatility60 | p90_100 | 27,979 | 24.99% | 2.00 | 13.89% | 8/8 |
| amplitude20 | p90_100 | 27,792 | 23.18% | 1.86 | 13.04% | 8/8 |
| atr20_pct | p90_100 | 27,953 | 23.13% | 1.86 | 12.91% | 8/8 |
| volatility20 | p90_100 | 27,964 | 23.16% | 1.85 | 12.26% | 8/8 |
| volatility10 | p90_100 | 28,510 | 21.12% | 1.69 | 11.31% | 8/8 |

年度稳定性比 pooled lift 更重要。`volatility60 == p90_100` 在 2017-2024 每年都高于当年 baseline：

| 年份 | 样本 | 命中率 | 当年 baseline | 年度 lift |
| --- | ---: | ---: | ---: | ---: |
| 2017 | 1,656 | 20.35% | 12.58% | 1.62 |
| 2018 | 3,108 | 22.43% | 9.46% | 2.37 |
| 2019 | 3,435 | 33.86% | 12.14% | 2.79 |
| 2020 | 4,294 | 41.73% | 29.39% | 1.42 |
| 2021 | 5,041 | 28.63% | 12.96% | 2.21 |
| 2022 | 4,524 | 18.68% | 8.02% | 2.33 |
| 2023 | 4,841 | 11.30% | 4.64% | 2.44 |
| 2024 | 1,080 | 15.46% | 9.69% | 1.60 |

解释：

- 高波动不是噪声过滤项，至少在 winner discovery 中不能被硬性排除。
- Explore6/7 那类偏风险控制的 bad-trade gate 如果简单惩罚高波动，可能会错杀真正 winner。
- P1 应该研究“高波动可承受”的结构条件，例如是否伴随相对强度、行业宽度、修复高度，而不是单独用 volatility 作为风险否决。

反例同样清楚：低波动分箱是明显负向。

| 原语 | 分箱 | 120d 50% high | lift |
| --- | --- | ---: | ---: |
| volatility60 | p0_10 | 3.45% | 0.28 |
| atr20_pct | p0_10 | 4.37% | 0.35 |
| volatility20 | p0_10 | 4.48% | 0.36 |
| amplitude20 | p0_10 | 4.56% | 0.37 |
| narrow_range10 | true | 7.57% | 0.61 |

这直接推翻了“先找极窄幅整理再等放量”的 P0 版本假设。窄幅整理不是不能产生 winner，但在当前 PIT stock-day 口径下不是好的一阶筛选。

### 4.3 趋势速度与短期全市场排名有效

`trend_speed_bucket == speed_fast` 和 `ret20_universe_pctile == p90_100` 都显示强正 lift。

| 原语 | 样本 | 120d 50% high | lift | 240d 100% high | top1行业占比 |
| --- | ---: | ---: | ---: | ---: | ---: |
| trend_speed_bucket == speed_fast | 10,466 | 27.07% | 2.17 | 14.47% | 11.50% |
| ret20_universe_pctile == p90_100 | 29,969 | 21.11% | 1.69 | 11.26% | 10.25% |
| relative_ret60_vs_benchmark == p90_100 | 29,600 | 20.67% | 1.66 | 11.24% | 10.27% |
| relative_ret120_vs_benchmark == p90_100 | 30,061 | 20.07% | 1.61 | 11.48% | 10.74% |

年度分布显示它们不是单一年份现象，但 2024 相对弱：

- `trend_speed_bucket == speed_fast` 在 2017-2023 均高于 baseline，2024 年年度 lift `0.97`。
- `ret20_universe_pctile == p90_100` 在 2017-2023 均高于 baseline，2024 年年度 lift `1.00`，基本等于 baseline。
- `relative_ret60_vs_benchmark == p90_100` 在 2019、2020、2021、2023 明显有效，2024 年 lift 只有 `0.61`。

解释：

- 相对强度是必要方向，但不能只做一条“过去 N 日涨幅排名前 10%”规则。
- 2024 的机会很多，但强 RS 分箱没有显著优于 baseline，说明 2024 winner 的结构可能更分散，或者大量样本的前向 horizon 被 observed reference overlap 削弱。
- P1 应拆分“市场整体强势中的强者”和“弱市独立 alpha”，不能把所有 RS 混成一个固定阈值。

### 4.4 从低点修复后的 continuation 明确存在

`repair_from_low120/240`、`dist_low120/240`、`post_30pct_from_recent_low` 都表明：大 winner 往往不是在最低点附近被捕获，而是在已经修复出一段幅度后仍有后续空间。

| 原语 | 样本 | 120d 50% high | lift | 240d 100% high | 解释 |
| --- | ---: | ---: | ---: | ---: | --- |
| repair_from_low240 == p90_100 | 24,689 | 22.25% | 1.83 | 14.42% | 长窗口修复强度 |
| repair_from_low120 == p90_100 | 27,652 | 21.90% | 1.77 | 12.34% | 中期修复强度 |
| dist_low120 == p90_100 | 27,652 | 21.90% | 1.77 | 12.34% | 与 repair_from_low120 等价 |
| post_30pct_from_recent_low == true | 86,575 | 20.02% | 1.60 | 10.88% | hold/continuation 方向 |

`post_30pct_from_recent_low == true` 的年度表现：

| 年份 | 样本 | 命中率 | baseline | lift |
| --- | ---: | ---: | ---: | ---: |
| 2017 | 5,169 | 18.69% | 12.64% | 1.48 |
| 2018 | 4,477 | 10.65% | 9.46% | 1.13 |
| 2019 | 12,055 | 17.90% | 12.14% | 1.47 |
| 2020 | 19,058 | 42.76% | 29.39% | 1.45 |
| 2021 | 19,899 | 18.55% | 12.96% | 1.43 |
| 2022 | 11,326 | 8.20% | 8.02% | 1.02 |
| 2023 | 8,694 | 5.94% | 4.64% | 1.28 |
| 2024 | 5,897 | 7.55% | 9.69% | 0.78 |

这组线索对 “早期发现” 帮助有限，但对 Explore8 的 early_exit 问题很关键。它说明已经涨过 30% 的股票仍可能在未来 120 日继续达到更高 winner 标签，尤其如果叠加相对强度，会更适合做 P1 hold / exit refinement。

## 5. 双变量组合：哪些组合值得进入 P1

P0 的 10 个双变量组合里，6 个在 120 日 50% high 上有正 lift，5 个在 240 日 100% high 上仍有正 lift。

| 双变量组合 | 120d 样本 | 120d 命中率 | 120d lift | 240d 命中率 | 240d lift | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 全市场强排名 + 行业强宽度 | 40,200 | 19.23% | 1.55 | 12.29% | 1.72 | P1 主线 |
| 已涨20% + 仍然相对强 | 47,022 | 19.25% | 1.54 | 11.77% | 1.63 | P1 hold/exit |
| 回撤修复 + 相对强 | 45,100 | 18.60% | 1.50 | 10.81% | 1.54 | P1 主线 |
| 20日强收益 + 成交放大 | 21,057 | 16.08% | 1.29 | 9.38% | 1.31 | P1 次级 |
| 个股强于行业 + 行业未同步 | 40,515 | 13.87% | 1.12 | 7.84% | 1.10 | 诊断保留 |
| 相对强度领先 + 弱市场 | 36,986 | 14.18% | 1.14 | 6.96% | 0.97 | 120d 有效，240d 不稳定 |
| 成交 regime shift + 接近新高 | 19,293 | 11.78% | 0.95 | 6.15% | 0.86 | drop |
| 可观察修复阶段 + 市场非强 | 33,864 | 10.99% | 0.88 | 5.76% | 0.80 | drop |
| 窄幅整理 + 振幅扩张 | 13,639 | 5.81% | 0.47 | 2.57% | 0.36 | drop |
| 低波压缩 + 放量扩张 | 12,221 | 5.56% | 0.45 | 3.07% | 0.43 | drop |

这里有一个重要的反直觉结论：**放量本身不是主线**。
`20日强收益 + 成交放大` 有正 lift，但 weaker than `全市场强排名 + 行业强宽度`、`已涨20% + 仍然相对强`、`回撤修复 + 相对强`。而 `成交 regime shift + 接近新高` 不如 baseline。也就是说，成交应该作为辅助确认，而不是优先级最高的 discovery primitive。

另一个关键结论是：**低波压缩 + 放量扩张不成立**。
这不是样本太少导致的偶然：它有 12,221 个 120d 样本，命中率只有 5.56%，lift 0.45；240d 100% high lift 也只有 0.43。P1 不应把它作为主线假设。

## 6. Preliminary discovery leads 逐条解释

| Rank | Lead | 样本 | 120d 50% precision | 240d 100% precision | lift | 年份 | 行业Top1 | 下一步 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | observable_late_acceleration_risk | 5,967 | 35.86% | 21.92% | 2.87 | 8 | 18.25% | P1 重新定义生命周期 |
| 2 | volatility60 p90_100 | 27,979 | 24.99% | 13.89% | 2.00 | 8 | 15.97% | P1 高波趋势 |
| 3 | trend_speed speed_fast | 10,466 | 27.07% | 14.47% | 2.17 | 8 | 11.50% | P1 强趋势速度 |
| 4 | ret20 universe top10% | 29,969 | 21.11% | 11.26% | 1.69 | 8 | 10.25% | P1 横截面领先 |
| 5 | relative_ret60 vs benchmark top10% | 29,600 | 20.67% | 11.24% | 1.66 | 8 | 10.27% | P1 相对强度 |
| 6 | amplitude20 p90_100 | 27,792 | 23.18% | 13.04% | 1.86 | 8 | 13.91% | P1 波动扩张 |
| 7 | post_30pct_from_recent_low | 86,575 | 20.02% | 10.88% | 1.60 | 8 | 10.65% | P1 hold/exit |
| 8 | atr20_pct p90_100 | 27,953 | 23.13% | 12.91% | 1.86 | 8 | 13.79% | P1 高ATR容忍 |

### 6.1 Lead 1：高 precision 但不是早期

`observable_late_acceleration_risk` 是最强 precision，但有两个限制：

- `episode_dedup_lift = 0.71`，`instrument_year_dedup_lift = 0.80`。stock-day lift 很高，但去重后没有同步增强，说明部分优势来自同一 winner 的连续多日状态重复。
- 年度上不稳定：2020 强，2022/2024 弱。

因此它不能直接作为 general early discovery hypothesis。它更适合成为 P1 的生命周期状态：什么时候应该继续持有，什么时候已经进入末端加速风险。

### 6.2 Lead 2/6/8：高波动族是最值得优先研究的 P1 方向

`volatility60`、`amplitude20`、`atr20_pct` 都指向同一个结构：winner 的可观察阶段伴随较高波动、较高振幅和较宽价格区间。这和很多风控直觉冲突，但数据上很稳定。

下一步不应该问“是否过滤高波动”，而应该问：

- 高波动是否伴随正的相对强度？
- 高波动是在下跌破坏中，还是在上升扩张中？
- 高波动是否发生在行业宽度改善阶段？
- 高波动 winner 的正常回撤容忍区间是多少？

### 6.3 Lead 3/4/5：强趋势和相对强度有效，但 P1 需要分市场状态

强趋势速度、全市场 top10% 收益、相对 benchmark top10% 都有效。问题是它们可能已经偏确认期，且 2024 年表现弱。P1 不能只固定一个 top10% threshold；应至少分：

- 弱市独立 alpha。
- 市场修复初期的领先股。
- 行业强宽度中的同步扩展股。
- 已经涨幅过大但仍有 continuation 的 winner。

### 6.4 Lead 7：post-30% 是 hold/exit 研究，不是 entry 研究

`post_30pct_from_recent_low == true` 的样本很多，lift 也稳定，但它天然是已经发生涨幅后的状态。它不能解决“买在低点附近”的问题，却能回答 Explore8 的一个核心失败：为什么部分 winner 会被过早退出。

这个 lead 的平均 drawdown before gain 是 `-7.87%`，比高波动族的 `-9.8%` 到 `-10.4%` 更温和。它暗示：已经修复 30% 且仍保持强势的股票，后续 winner extension 可能不需要非常宽的止损，但需要避免简单 time stop。

## 7. 行业与市场环境

P0 没有发现“某个行业独占”的问题。主要 lead 的 top1 industry concentration 都低于 20%，满足 general hypothesis 的初步分散要求。

但行业差异仍然很重要。高波动、趋势速度、相对强度在以下行业切片上 lift 更高：

| 线索 | 高 lift 行业示例 | 解读 |
| --- | --- | --- |
| volatility60 p90_100 | 公用事业、交通运输、建筑材料、国防军工、基础化工、汽车 | 高波动 winner 不只集中在 TMT 或成长行业，周期与传统行业也明显存在 |
| trend_speed speed_fast | 交通运输、机械设备、建筑装饰、建筑材料、石油石化、基础化工 | 快速趋势在周期/制造方向更突出 |
| ret20 universe top10% | 交通运输、机械设备、基础化工、建筑材料、传媒、电力设备 | 横截面强度跨行业有效 |
| relative_ret60 vs benchmark top10% | 建筑材料、交通运输、基础化工、钢铁、电子 | 相对强度更偏行业周期和结构行情 |
| post_30pct_from_recent_low | 商贸零售、钢铁、机械设备、基础化工、交通运输 | continuation 不只发生在高成长行业 |

Market regime 的发现比较克制：

- `相对强度领先 + 弱市场` 在 120d 有正 lift `1.14`，但 240d 100% high lift 低于 1。
- `可观察修复阶段 + 市场非强` 低于 baseline。
- 这说明弱市场中个股领先是一个现象，但不能简单把弱市场当作 alpha 加分项。

行业宽度比单纯 market regime 更有价值。`全市场强排名 + 行业强宽度` 是最强双变量组合，120d lift `1.55`，240d lift `1.72`。这说明 P1 应把 regime 作为确认强度、仓位或 hold tolerance 的调节项，而不是硬过滤。

## 8. 明确淘汰或降级的方向

### 8.1 低波压缩不是 P1 主线

`低波压缩 + 放量扩张` 和 `窄幅整理 + 振幅扩张` 都明显低于 baseline。它们不是因为样本过少失败，而是在足够样本下失败。

| 方向 | 120d 样本 | 120d lift | 240d lift | 处理 |
| --- | ---: | ---: | ---: | --- |
| 低波压缩 + 放量扩张 | 12,221 | 0.45 | 0.43 | drop |
| 窄幅整理 + 振幅扩张 | 13,639 | 0.47 | 0.36 | drop |
| volatility60 p0_10 | 33,966 | 0.28 | 0.24 | drop |
| atr20_pct p0_10 | 33,533 | 0.35 | 0.22 | drop |

### 8.2 大市值、老上市年限不是 winner 友好切片

`market_cap_bucket == cap_300b_plus` 和 `listing_age_bucket == listing_old` 在 120/240 日 winner 标签上明显弱。P1 不应把大市值稳定性误认为 winner 潜力。

### 8.3 成交额不能单独成为主线

成交放大在 `20日强收益 + 成交放大` 中有帮助，但 `money_regime_shift60 + near_high` 低于 baseline。成交额更像 confirmation variable，不适合作为单独发现器。

## 9. 关键 Caveats

### 9.1 Stock-day 口径会重复计数 winner

P0 主 precision/lift 是 stock-day 口径。多个 lead 的 positive stock-day 很高，但 episode dedup lift 不同步。例如：

- `volatility60 == p90_100` 的 stock-day lift `2.00`，但 `episode_dedup_lift = 0.88`。
- `trend_speed_bucket == speed_fast` 的 stock-day lift `2.17`，但 `episode_dedup_lift = 0.47`。
- `ret20_universe_pctile == p90_100` 的 stock-day lift `1.69`，但 `episode_dedup_lift = 0.48`。

这不否定线索，但说明 P1 必须增加 episode-level 或 instrument-year-level leaderboard。否则会把同一只大 winner 的连续多个强势日误读为多次独立发现。

### 9.2 很多强线索偏“确认期”，不是“低点早期”

`observable_late_acceleration_risk`、`post_30pct_from_recent_low`、`trend_speed_bucket == speed_fast` 都要求 T 日已经出现明确修复或扩展。它们可以帮助解决 continuation / hold，但不能单独承担 early discovery。

真正 early discovery 仍需要补充：

- 修复初期但 trend score 尚低的结构。
- 行业尚未同步前的个股领先。
- 从长期回撤中第一次稳定修复的信号。
- high volatility 中的“破坏性高波”和“扩张性高波”区分。

### 9.3 2024 的 horizon 不完整

2024 有很多 episode，但 240 日 horizon 大量跨入 2025-2026。P0 主 lift 已排除 overlap，但任何讲 2024 240d continuation 的结论都应谨慎。P1 不应使用 observed reference 选择阈值。

### 9.4 高波动不是低风险

高波动族有高 lift，但平均 drawdown before gain 约 `-9.8%` 到 `-10.4%`。如果 P1 发展成规则，必须同步研究：

- 正常 winner pullback 的容忍区间。
- 快速失败条件。
- 高波动但相对强度不足的排除条件。
- 行业/市场状态是否支持放宽退出。

## 10. P1 建议路线

P1 不应把 P0 leads 直接改写成策略规则。建议拆成五组 hypothesis refine。

### 10.1 高波动趋势扩张假设

候选描述：

```text
在 PIT universe 中，过去 20/60 日波动、ATR 或振幅进入年度横截面高分位，
且价格处于修复/扩展状态时，未来 120/240 日大涨概率高于同年 baseline。
```

必须补充的约束：

- 区分上涨中的高波动和下跌中的高波动。
- 加入相对强度或行业宽度确认。
- 报告正常回撤容忍区间，避免把高波动 winner 当作 bad trade。

### 10.2 横截面领先 + 行业宽度假设

候选描述：

```text
个股 20 日收益进入全市场前 10%-20%，且所在行业宽度较强时，
比单纯全市场强排名更稳定地指向后续 winner。
```

该方向的双变量 lift 最强，且 240d 100% high lift 仍为 `1.72`。P1 应优先做年度 breakdown、行业 breakdown 和 formula 简化。

### 10.3 修复后相对强假设

候选描述：

```text
股票已从 120 日低点明显修复，且相对沪深300仍处于高分位时，
后续 continuation 概率高于普通修复股。
```

对应双变量 `回撤修复 + 相对强` 的 120d lift `1.50`，240d lift `1.54`。这比单纯 `post_30pct` 更适合形成 human-readable rule。

### 10.4 post-20/post-30 winner hold 假设

候选描述：

```text
当股票已从近期低点上涨 20%/30%，且仍保持相对强度时，
默认退出规则应从普通 time stop 切换为 winner hold / pullback tolerance。
```

这条假设不应和 entry 混在一起。它应该服务于 Explore8 的 early_exit 问题：什么时候已持仓 winner 不应被普通失败条件处理。

### 10.5 涨停/极强日作为 sparse diagnostic

`limit_up_like == true` 的样本只有 `2,136`，但 120d 50% high precision `25.52%`，lift `2.04`。它样本较少，不适合泛化为 general rule，但可以作为 P1 的 sparse diagnostic：强势涨停后的 winner path 与普通高波动扩张是否不同。

## 11. P2 建议路线

P2 shape clustering 不应现在抢跑为策略。更合理的输入窗口是 P1 筛出的高价值族：

- high volatility / high ATR winner early windows。
- repair_from_low + relative strength windows。
- post-20/post-30 continuation windows。
- failed high-volatility false positives。

P2 应重点解释“高波扩张为什么有效”，而不是泛泛对所有价格序列聚类。

## 12. 最终判断

Explore9 P0 已经完成 broad discovery 的基础目标：标签、episode、primitive registry、univariate/pairwise lift、稳定性和 preliminary leads 都已跑通，并且最低覆盖通过。

当前最有价值的研究结论是：

- 大 winner 的可观察特征不是低波安静启动，而是高波动、高振幅、强趋势速度、相对强度和修复后延展。
- 高波动应该被重新理解为 winner discovery 的候选状态，而不是默认风险否决。
- 相对强度和行业宽度是更可靠的确认变量。
- post-20/post-30 continuation 是 hold/exit 改造方向，不是入场方向。
- 低波压缩、窄幅整理、成交 regime shift 单独使用都不值得进入 P1 主线。

建议进入 P1，但 P1 只应做 hypothesis refine，不应进入 Explore10 回测。Explore10 是否启动，必须等待 P1/P2 产生可解释、年度稳定、episode 去重后仍有效的候选假设。

## 13. Manifest 纪律

| 字段 | 值 |
| --- | --- |
| `explore8_profile_csv_used_for_label` | false |
| `explore8_profile_csv_used_for_signal` | false |
| `explore8_profile_csv_used_for_selection` | false |
| `historical_trade_results_used_for_labeling` | false |
| `historical_trade_results_used_for_signal` | false |
| `observed_reference_used_for_selection` | false |
| P1 outputs | deferred_to_p1 |
| P2 outputs | deferred_to_p2 |
