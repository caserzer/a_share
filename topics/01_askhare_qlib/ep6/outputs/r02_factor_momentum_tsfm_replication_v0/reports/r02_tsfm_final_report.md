# R02 Factor Momentum TSFM Local Feasible Replication 最终报告

## 1. 结论摘要

`final_decision = ep6_tsfm_4factor_local_proxy_positive_diagnostic_only`

`authorized_strategy_requirement = false`

本轮实现的是 Ma / Liao / Jiang (2023) 中 `time-series factor momentum` (`TSFM`) 的本地可实现版本。它不是论文 10 因子的完整复现，而是一个 **4-factor local feasible proxy diagnostic**：

```text
retained factors = SIZE, ILL, TURN, BAB
removed factors = BM, GP, CINVEST, EP, ACC, CFP
```

被移除的 6 个因子全部需要 PIT accounting fields 和 announcement-date as-of 规则；当前本地数据没有这些字段，因此不能用 price-only proxy 补。

核心读数：

| split | month count | gross ann mean | after-cost ann mean | gross Sharpe | after-cost Sharpe | gross positive month | after-cost positive month |
|:--|--:|--:|--:|--:|--:|--:|--:|
| train | 28 | 3.10% | -4.16% | 0.232 | -0.309 | 50.00% | 46.43% |
| validation | 24 | 8.68% | 2.35% | 0.807 | 0.211 | 58.33% | 58.33% |
| robustness | 24 | 15.02% | 9.95% | 0.966 | 0.643 | 66.67% | 58.33% |

当前结论可以支持：

```text
在 EP5 PIT mcap500 mainboard universe 下，
4 个本地可实现因子的 factor-level TSFM 在 2022-2025 OOS 上有正向 diagnostic 读数。
```

当前结论不能支持：

```text
不能宣称复现了论文完整 10-factor TSFM；
不能宣称 A 股个股 long-short 可直接交易；
不能授权 strategy requirement 或 portfolio allocator。
```

最重要的发现是：本轮 TSFM 的有效部分不是简单“赢家因子继续涨”，而是 **对亏损 factor leg 的反向暴露**。validation 和 robustness 中，`TURN` / `BAB` 的 raw factor return 多数为负，但 TSFM 因为过去 12 个月 factor return 为负而做空这些因子，反而贡献了主要正收益。这使结果在统计上有意义，但在 A 股执行上更敏感，因为每个月都涉及 short exposure。

## 2. 数据边界与运行口径

| item | value |
|:--|:--|
| Qlib provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| loaded instruments | 539 |
| calendar | 2017-01-03 ~ 2026-04-30 |
| factor return labels | 2017-08 ~ 2025-12 |
| first evaluable TSFM holding month | 2018-08 |
| signal month count | 101 |
| price adjustment mode | `provider_ohlc_already_adjusted` |
| TURN volume unit audit | `verified_volume_shares_by_money_div_volume_close_parity` |
| money / volume relative to PIT close median | 1.0006 |
| volume unit audit sample count | 10,247 |

数据约束：

1. 所有 PIT join 使用 `date + instrument`。
2. `close` 直接使用 provider-adjusted close，不再二次套用 `factor.day.bin`。
3. `money` 使用本地成交额字段，不替换成其他 provider alias。
4. `TURN = mean(volume / (total_share * 10000))` 只在 volume unit audit 通过后保留。
5. 月度 factor return 标注为 holding month `m+1`，TSFM position 在 `S_m` 形成，只使用 `m-11` 到 `m` 的已完成 factor return。

TSFM 公式：

```text
factor_return_{f,m+1} =
  mean(high_quintile_return) - mean(low_quintile_return)

past_12m_factor_return_{f,m} =
  compounded_return(factor_return_{f,m-11}, ..., factor_return_{f,m})

tsfm_position_{f,m+1} =
  +1 if past_12m_factor_return_{f,m} > 0
  -1 if past_12m_factor_return_{f,m} < 0
   0 otherwise

tsfm_return_{m+1} =
  mean(tsfm_position_{f,m+1} * factor_return_{f,m+1})
  over active retained factors
```

## 3. 因子可实现性

| factor_id | paper factor | availability | action | local formula | train coverage | validation coverage | robustness coverage | median instruments validation / robustness | block reason |
|:--|:--|:--|:--|:--|--:|--:|--:|:--|:--|
| SIZE | Size | available_full | retain | `local_SIZE_market_cap_high_minus_low_v0` | 52 | 24 | 24 | 227.0 / 222.5 |  |
| BM | Book-to-market / value | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| GP | Gross profitability | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| CINVEST | Investment | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| ILL | Illiquidity | available_full | retain | `local_ILL_amihud_21d_v0` | 52 | 24 | 24 | 226.0 / 222.0 |  |
| EP | Earnings-to-price | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| ACC | Accruals | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| CFP | Cash-flow-to-price | missing_required_fundamental_fields | remove |  | 0 | 0 | 0 | NA / NA | missing PIT accounting fields and announcement timestamps |
| TURN | Turnover | available_full | retain | `local_TURN_share_turnover_21d_v0` | 52 | 24 | 24 | 227.0 / 222.5 |  |
| BAB | Betting-against-beta | available_full | retain | `local_BAB_beta_sort_252d_v0` | 52 | 24 | 24 | 227.0 / 222.5 |  |

训练期每个 retained factor 有 52 个 complete factor months，但 expected train factor months 是 53。缺口来自 2018-11 的 PIT universe / coverage 不足，触发 `blocked_insufficient_factor_month_coverage`。这会造成 train TSFM 可评价月份少于直觉上的月数，但 validation 和 robustness 各 24 个月全部完整。

因子月覆盖质量：

| factor | split | months | complete | blocked | eligible median | eligible min | high median | low median | gross mean | after-cost mean |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SIZE | train | 53 | 52 | 1 | 156.0 | 117.0 | 31.0 | 32.0 | 0.26% | -0.22% |
| SIZE | validation | 24 | 24 | 0 | 227.0 | 212.0 | 45.0 | 46.0 | 0.28% | -0.18% |
| SIZE | robustness | 24 | 24 | 0 | 222.5 | 189.0 | 44.0 | 45.0 | 0.04% | -0.42% |
| ILL | train | 53 | 52 | 1 | 155.0 | 116.0 | 31.0 | 31.0 | -0.28% | -0.77% |
| ILL | validation | 24 | 24 | 0 | 226.0 | 211.0 | 45.0 | 46.0 | 1.11% | 0.58% |
| ILL | robustness | 24 | 24 | 0 | 222.0 | 189.0 | 44.0 | 45.0 | -0.48% | -1.00% |
| TURN | train | 53 | 52 | 1 | 156.0 | 116.0 | 31.0 | 32.0 | 0.75% | 0.20% |
| TURN | validation | 24 | 24 | 0 | 227.0 | 212.0 | 45.0 | 46.0 | -2.69% | -3.21% |
| TURN | robustness | 24 | 24 | 0 | 222.5 | 189.0 | 44.0 | 45.0 | 0.22% | -0.32% |
| BAB | train | 53 | 52 | 1 | 156.0 | 116.0 | 31.0 | 32.0 | 0.33% | -0.03% |
| BAB | validation | 24 | 24 | 0 | 227.0 | 212.0 | 45.0 | 46.0 | -2.15% | -2.47% |
| BAB | robustness | 24 | 24 | 0 | 222.5 | 189.0 | 44.0 | 45.0 | 0.38% | 0.06% |

## 4. Split 级结果

| split | months | active median | gross ann | after-cost ann | cost drag ann | gross Sharpe | after-cost Sharpe | gross positive | after-cost positive | max drawdown | buy turnover | sell turnover | months requiring short |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 28 | 4 | 3.10% | -4.16% | 7.25% | 0.232 | -0.309 | 50.00% | 46.43% | -17.23% | 54.96% | 54.96% | 28 |
| validation | 24 | 4 | 8.68% | 2.35% | 6.32% | 0.807 | 0.211 | 58.33% | 58.33% | -12.19% | 47.90% | 47.90% | 24 |
| robustness | 24 | 4 | 15.02% | 9.95% | 5.07% | 0.966 | 0.643 | 66.67% | 58.33% | -10.02% | 38.44% | 38.44% | 24 |

解读：

1. OOS gross result 明显强于 train。train after-cost 为负，说明这个结果不是“全样本一路顺滑”；真正支持来自 validation 和 robustness 两段。
2. 成本拖累很大：validation 年化拖累 6.32%，robustness 年化拖累 5.07%。after-cost 仍为正，但 validation after-cost Sharpe 只有 0.211，不能被解释成稳健可交易策略。
3. validation / robustness 每个月都需要 short exposure。即使 after-cost 为正，这仍然是 factor-level diagnostic，不等于 A 股个股可直接 long-short 落地。
4. robustness 比 validation 更强，主要来自 2024-01、2025-08、2025-12 等月份的正贡献。这个形态更像 factor regime timing，而不是均匀小 alpha。

## 5. 年度拆解

| split | year | months | gross ann | after-cost ann | gross positive | after-cost positive | buy turnover | sell turnover | max drawdown |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 2018 | 3 | 33.91% | 28.68% | 100.00% | 100.00% | 39.60% | 39.60% | 0.00% |
| train | 2019 | 1 | 21.60% | 9.35% | 100.00% | 100.00% | 92.80% | 92.80% | 0.00% |
| train | 2020 | 12 | 12.43% | 6.60% | 50.00% | 50.00% | 44.18% | 44.18% | -6.86% |
| train | 2021 | 12 | -15.48% | -24.25% | 33.33% | 25.00% | 66.43% | 66.43% | -16.28% |
| validation | 2022 | 12 | 3.45% | -3.92% | 50.00% | 50.00% | 55.83% | 55.83% | -12.19% |
| validation | 2023 | 12 | 13.90% | 8.63% | 66.67% | 66.67% | 39.98% | 39.98% | -1.91% |
| robustness | 2024 | 12 | 15.26% | 10.13% | 75.00% | 66.67% | 38.82% | 38.82% | -10.02% |
| robustness | 2025 | 12 | 14.78% | 9.76% | 58.33% | 50.00% | 38.05% | 38.05% | -8.12% |

年度层面有两个关键点：

1. validation 不是两年都强。2022 gross 仅 3.45%，after-cost 为 -3.92%；2023 才明显转强。也就是说 validation pass 不是一个均匀的 24 个月平稳过程。
2. robustness 两年都为正，且 after-cost 也为正，这是本轮 final decision 能通过的主要原因。

## 6. 因子贡献与信号方向

| factor | split | raw factor mean | raw t-stat | raw positive month | avg past 12m | TSFM long months | TSFM short months | contribution mean | abs contribution share |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| SIZE | train | 0.26% | 0.521 | 53.85% | -1.08% | 7 | 21 | 0.05% | 14.14% |
| ILL | train | -0.28% | -0.540 | 42.31% | -6.68% | 5 | 23 | -0.28% | 18.74% |
| TURN | train | 0.75% | 0.807 | 51.92% | 24.26% | 25 | 3 | 0.59% | 37.00% |
| BAB | train | 0.33% | 0.405 | 48.08% | 7.66% | 20 | 8 | -0.11% | 30.11% |
| SIZE | validation | 0.28% | 0.354 | 50.00% | -1.35% | 9 | 15 | -0.37% | 18.67% |
| ILL | validation | 1.11% | 1.901 | 75.00% | 13.61% | 24 | 0 | 0.28% | 13.78% |
| TURN | validation | -2.69% | -2.348 | 25.00% | -23.18% | 2 | 22 | 0.28% | 33.31% |
| BAB | validation | -2.15% | -1.637 | 29.17% | -20.78% | 0 | 24 | 0.54% | 34.24% |
| SIZE | robustness | 0.04% | 0.046 | 58.33% | 8.48% | 20 | 4 | 0.25% | 16.40% |
| ILL | robustness | -0.48% | -1.022 | 50.00% | -3.85% | 7 | 17 | 0.02% | 9.46% |
| TURN | robustness | 0.22% | 0.132 | 41.67% | -15.78% | 5 | 19 | 0.42% | 35.94% |
| BAB | robustness | 0.38% | 0.221 | 41.67% | -11.86% | 6 | 18 | 0.56% | 38.21% |

这里是本轮最有信息量的部分：

1. **validation 的主要贡献来自做空负 momentum factor**。`BAB` 24 个月全为 short，raw factor mean 为 -2.15%，TSFM contribution mean 为 +0.54%；`TURN` 22 个月 short，raw factor mean 为 -2.69%，contribution mean 为 +0.28%。
2. `ILL` 是 validation 中唯一稳定 long 的因子：24 个月全 long，raw factor mean +1.11%，positive month share 75.00%。它提供了方向确认，但贡献占比只有 13.78%。
3. `SIZE` 在 validation 中是拖累项：raw factor mean +0.28%，但 TSFM 多数月份 short，contribution mean -0.37%。
4. robustness 中 `BAB` / `TURN` 仍然是主要贡献来源，abs contribution share 分别为 38.21% 和 35.94%。这说明 supported token 很大程度依赖两个 trading/market-state 因子，而不是四个因子平均贡献。

集中度门禁：

| split | top1 factor abs contribution share | top2 factor abs contribution share | pass |
|:--|--:|--:|:--|
| validation | 34.24% | 67.54% | true |
| robustness | 38.21% | 74.15% | true |

集中度没有越过门槛，但不算宽。4 个因子里 `BAB` / `TURN` 已经占据 OOS 主要解释权；后续如果要把这个方向推进，必须确认这两个因子不是 beta / market regime 的残余。

## 7. OOS 月度明细

| holding_period | split | winner factors | loser factors | gross return | after-cost return | buy turnover | sell turnover |
|:--|:--|--:|--:|--:|--:|--:|--:|
| 2022-01 | validation | 2 | 2 | -1.49% | -2.64% | 105.24% | 105.24% |
| 2022-02 | validation | 1 | 3 | -0.98% | -1.75% | 69.70% | 69.70% |
| 2022-03 | validation | 1 | 3 | 4.09% | 3.83% | 24.23% | 24.23% |
| 2022-04 | validation | 2 | 2 | -2.43% | -3.19% | 68.97% | 68.97% |
| 2022-05 | validation | 2 | 2 | -3.59% | -4.64% | 95.79% | 95.79% |
| 2022-06 | validation | 1 | 3 | -6.65% | -7.30% | 59.04% | 59.04% |
| 2022-07 | validation | 1 | 3 | 3.80% | 3.45% | 31.84% | 31.84% |
| 2022-08 | validation | 1 | 3 | 3.88% | 3.54% | 30.82% | 30.82% |
| 2022-09 | validation | 2 | 2 | 4.86% | 4.16% | 63.73% | 63.73% |
| 2022-10 | validation | 2 | 2 | 1.04% | 0.78% | 23.48% | 23.48% |
| 2022-11 | validation | 1 | 3 | 1.03% | 0.35% | 61.55% | 61.55% |
| 2022-12 | validation | 1 | 3 | -0.13% | -0.52% | 35.51% | 35.51% |
| 2023-01 | validation | 2 | 2 | -5.09% | -5.83% | 67.62% | 67.62% |
| 2023-02 | validation | 1 | 3 | 4.69% | 3.96% | 66.04% | 66.04% |
| 2023-03 | validation | 1 | 3 | 1.95% | 1.60% | 31.46% | 31.46% |
| 2023-04 | validation | 1 | 3 | 3.48% | 3.11% | 34.03% | 34.03% |
| 2023-05 | validation | 1 | 3 | 3.69% | 3.37% | 29.18% | 29.18% |
| 2023-06 | validation | 1 | 3 | -1.03% | -1.41% | 34.69% | 34.69% |
| 2023-07 | validation | 1 | 3 | -0.89% | -1.26% | 33.65% | 33.65% |
| 2023-08 | validation | 2 | 2 | 3.26% | 2.60% | 60.69% | 60.69% |
| 2023-09 | validation | 2 | 2 | 1.62% | 1.27% | 31.75% | 31.75% |
| 2023-10 | validation | 2 | 2 | -0.39% | -0.73% | 31.07% | 31.07% |
| 2023-11 | validation | 2 | 2 | 1.25% | 0.91% | 30.70% | 30.70% |
| 2023-12 | validation | 2 | 2 | 1.36% | 1.05% | 28.86% | 28.86% |
| 2024-01 | robustness | 2 | 2 | 11.70% | 11.32% | 34.35% | 34.35% |
| 2024-02 | robustness | 2 | 2 | -5.91% | -6.42% | 46.37% | 46.37% |
| 2024-03 | robustness | 2 | 2 | 1.99% | 1.63% | 33.25% | 33.25% |
| 2024-04 | robustness | 2 | 2 | 2.42% | 2.09% | 30.01% | 30.01% |
| 2024-05 | robustness | 2 | 2 | 2.22% | 1.88% | 30.56% | 30.56% |
| 2024-06 | robustness | 2 | 2 | 1.61% | 1.27% | 30.59% | 30.59% |
| 2024-07 | robustness | 2 | 2 | 0.15% | -0.22% | 33.93% | 33.93% |
| 2024-08 | robustness | 1 | 3 | 3.74% | 3.06% | 62.02% | 62.02% |
| 2024-09 | robustness | 1 | 3 | -5.43% | -5.81% | 35.19% | 35.19% |
| 2024-10 | robustness | 1 | 3 | -4.85% | -5.47% | 56.26% | 56.26% |
| 2024-11 | robustness | 1 | 3 | 2.16% | 1.73% | 39.31% | 39.31% |
| 2024-12 | robustness | 1 | 3 | 5.45% | 5.08% | 34.03% | 34.03% |
| 2025-01 | robustness | 1 | 3 | -1.41% | -1.72% | 28.22% | 28.22% |
| 2025-02 | robustness | 1 | 3 | -2.59% | -2.84% | 23.06% | 23.06% |
| 2025-03 | robustness | 1 | 3 | 3.16% | 2.87% | 26.25% | 26.25% |
| 2025-04 | robustness | 1 | 3 | 2.82% | 2.54% | 25.89% | 25.89% |
| 2025-05 | robustness | 1 | 3 | 2.49% | 2.12% | 33.55% | 33.55% |
| 2025-06 | robustness | 1 | 3 | -1.90% | -2.19% | 25.77% | 25.77% |
| 2025-07 | robustness | 2 | 2 | 0.33% | -0.37% | 63.06% | 63.06% |
| 2025-08 | robustness | 3 | 1 | 8.09% | 7.36% | 66.07% | 66.07% |
| 2025-09 | robustness | 2 | 2 | 5.41% | 4.65% | 69.35% | 69.35% |
| 2025-10 | robustness | 2 | 2 | -3.98% | -4.34% | 32.01% | 32.01% |
| 2025-11 | robustness | 2 | 2 | -4.30% | -4.63% | 29.95% | 29.95% |
| 2025-12 | robustness | 2 | 2 | 6.68% | 6.31% | 33.43% | 33.43% |

最大正负月份：

| holding_period | split | gross return | after-cost return | winner factors | loser factors | buy / sell turnover |
|:--|:--|--:|--:|--:|--:|:--|
| 2024-01 | robustness | 11.70% | 11.32% | 2 | 2 | 34.35% / 34.35% |
| 2025-08 | robustness | 8.09% | 7.36% | 3 | 1 | 66.07% / 66.07% |
| 2025-12 | robustness | 6.68% | 6.31% | 2 | 2 | 33.43% / 33.43% |
| 2024-12 | robustness | 5.45% | 5.08% | 1 | 3 | 34.03% / 34.03% |
| 2025-09 | robustness | 5.41% | 4.65% | 2 | 2 | 69.35% / 69.35% |
| 2022-09 | validation | 4.86% | 4.16% | 2 | 2 | 63.73% / 63.73% |
| 2025-11 | robustness | -4.30% | -4.63% | 2 | 2 | 29.95% / 29.95% |
| 2024-10 | robustness | -4.85% | -5.47% | 1 | 3 | 56.26% / 56.26% |
| 2023-01 | validation | -5.09% | -5.83% | 2 | 2 | 67.62% / 67.62% |
| 2024-09 | robustness | -5.43% | -5.81% | 1 | 3 | 35.19% / 35.19% |
| 2024-02 | robustness | -5.91% | -6.42% | 2 | 2 | 46.37% / 46.37% |
| 2022-06 | validation | -6.65% | -7.30% | 1 | 3 | 59.04% / 59.04% |

月度层面说明：

1. 最强月份集中在 robustness，尤其是 2024-01 和 2025-08。
2. validation 最大亏损出现在 2022-06 和 2023-01，和 2022 年整体 after-cost 为负一致。
3. 即使在正收益月份，turnover 仍然不低；例如 2025-09 gross +5.41%，after-cost +4.65%，买卖单边 turnover 各 69.35%。

## 8. 与论文结果的参考比较

| metric | paper | local train | local validation | local robustness | local full | comparability | reference gap |
|:--|--:|--:|--:|--:|--:|:--|--:|
| annualized_mean_return | 9.91% | 3.10% | 8.68% | 15.02% | 8.62% | not comparable due to 4-factor proxy | -1.29% |
| t_stat_monthly_mean | 4.880 | 0.354 | 1.141 | 1.366 | 1.636 | not comparable due to 4-factor proxy | -3.244 |
| sharpe_ratio | 1.150 | 0.232 | 0.807 | 0.966 | 0.650 | not comparable due to 4-factor proxy | -0.500 |
| winner_leg_annualized_mean_return | 14.07% | 8.64% | 0.37% | 15.24% | 8.11% | not comparable due to 4-factor proxy | -5.96% |
| loser_leg_annualized_mean_return | 3.37% | 0.73% | -14.07% | -15.50% | -9.33% | not comparable due to 4-factor proxy | -12.70% |
| FF5 alpha | 9.59% | NA | NA | NA | NA | not evaluated | NA |
| CH3 alpha | 7.76% | NA | NA | NA | NA | not evaluated | NA |
| conditional CH3 alpha | 7.04% | NA | NA | NA | NA | not evaluated | NA |

不能把 `local_full annualized_mean_return = 8.62%` 与论文 `9.91%` 直接对比成“接近复现”。原因很明确：

1. 论文是 10 个非 momentum characteristic factors；本地只有 4 个可实现 proxy factors。
2. 论文样本是 2001-2019；本地 OOS 主要是 2022-2025。
3. 论文使用 CSMAR 全市场构造；本地使用 EP5 PIT mcap500 mainboard universe。
4. 本地没有 FF5 / CH3 / conditional CH3 回归，因此 alpha 读数不可比。

更稳妥的说法是：**论文 TSFM 的方向性机制在本地 4 因子 proxy 上没有被否决，并且在 2022-2025 OOS 有正读数。**

## 9. Gate Replay

| gate group | gate | result |
|:--|:--|:--|
| data | retained_factor_count_min | true |
| data | validation_evaluable_month_count_min | true |
| data | robustness_evaluable_month_count_min | true |
| data | validation_active_factor_count_median_min | true |
| data | robustness_active_factor_count_median_min | true |
| validation | annualized_mean_return_positive | true |
| validation | t_stat_monthly_mean_positive | true |
| validation | sharpe_ratio_min | true |
| validation | positive_month_share_min | true |
| validation | active_factor_count_median_min | true |
| robustness | annualized_mean_return_positive | true |
| robustness | t_stat_monthly_mean_positive | true |
| robustness | sharpe_ratio_min | true |
| robustness | positive_month_share_min | true |
| robustness | active_factor_count_median_min | true |
| after-cost | validation_after_cost_mean_positive | true |
| after-cost | robustness_after_cost_mean_positive | true |
| concentration | validation_top1_factor_abs_contribution_share | 34.24% |
| concentration | validation_top2_factor_abs_contribution_share | 67.54% |
| concentration | robustness_top1_factor_abs_contribution_share | 38.21% |
| concentration | robustness_top2_factor_abs_contribution_share | 74.15% |

Gate 通过的含义是 diagnostic support，不是 tradability support。尤其要注意：本轮 cost replay 假设了 long-short stock book 可以形成，报告并没有解决 A 股 short constraint、融券可得性、借券成本、ETF/期货替代路径或行业/市值中性执行问题。

## 10. Findings

### Finding 1: TSFM 支持来自 factor-level direction，不来自裸 factor premium

validation 中 `TURN` 和 `BAB` 的 raw factor mean 分别是 -2.69% 和 -2.15%，但 TSFM 通过 short 这些过去 12 个月表现差的 factor，得到正贡献。这说明本轮不是在发现“高 turnover / 高 beta 本身赚钱”，而是在发现 **这些 factor return 的时间序列方向有可利用延续性**。

这点非常关键。若后续误把结果解释为“买某个因子高分组”，方向会完全错。

### Finding 2: OOS 支持比 train 更强，但 train 弱点不能忽略

train gross 年化只有 3.10%，after-cost 为 -4.16%。真正强的读数来自 validation / robustness：

```text
validation after-cost ann mean = 2.35%
robustness after-cost ann mean = 9.95%
```

这不是传统意义上 train 强、OOS 保留的形态，而是近年样本更强。可能解释包括：

1. 2022-2025 的市场结构更适合 factor-level regime timing；
2. EP5 PIT mcap500 universe 在后期覆盖更多、因子腿更稳定；
3. `BAB` / `TURN` 的负向 factor momentum 在近年更突出；
4. 也可能只是短样本下的 regime luck。

因此下一步不能直接进入策略，而应先做 regime decomposition。

### Finding 3: 成本没有完全杀死信号，但大幅降低质量

after-cost 仍为正，这是一个正面结果；但成本影响不能被淡化：

| split | gross ann | after-cost ann | annual cost drag | gross Sharpe | after-cost Sharpe |
|:--|--:|--:|--:|--:|--:|
| validation | 8.68% | 2.35% | 6.32% | 0.807 | 0.211 |
| robustness | 15.02% | 9.95% | 5.07% | 0.966 | 0.643 |

validation after-cost Sharpe 只有 0.211，说明可执行版本的安全边际很薄。这个结果更适合继续做 confirmatory diagnostic，而不是直接变成组合构造。

### Finding 4: 每个 OOS 月都需要 short exposure

validation 24/24 个月、robustness 24/24 个月都 `requires_short_exposure = true`。这意味着本轮 positive diagnostic 与 A 股现实执行之间还有一个很大的缺口。

如果不能稳定做空个股，那么这个方向只能走以下几类替代：

1. factor timing overlay，用于调节已有 long-only factor exposure；
2. ETF / 股指期货 / 行业篮子替代 short leg；
3. 只使用 long-side 的风险预算切换，但这需要重新定义 requirement；
4. 在可融券池或机构可借券 universe 中重跑。

### Finding 5: `BAB` / `TURN` 是主轴，`ILL` 是辅助确认，`SIZE` 较弱

OOS 贡献占比：

| split | top factors |
|:--|:--|
| validation | `BAB` 34.24%, `TURN` 33.31%, `SIZE` 18.67%, `ILL` 13.78% |
| robustness | `BAB` 38.21%, `TURN` 35.94%, `SIZE` 16.40%, `ILL` 9.46% |

这说明 4-factor proxy 并不是四条独立强边，而更像 `BAB + TURN` 主导的 factor timing signal。后续最应该拆的是：

```text
BAB / TURN 的贡献到底是 beta-regime、liquidity-regime、还是真正 factor momentum？
```

### Finding 6: 2022 是主要弱点

validation split 内部差异很大：

```text
2022 after-cost ann = -3.92%
2023 after-cost ann = +8.63%
```

如果后续要推进，这个方向必须解释 2022 为什么弱：是市场下行、beta exposure、turnover crowding、还是本地 universe 在 2022 的结构性偏差。否则这个结果容易被 2023-2025 的强样本掩盖。

## 11. Insight 与后续研究建议

### Insight 1: 这更像“因子状态动量”，不是个股 alpha

EP5 里很多 H3/H5 个股短周期 alpha 失败，而这里月频 TSFM 有支持，一个合理解释是：

```text
个股级短周期 signal 很快被噪声、交易约束、涨跌停和 crowding 吞掉；
factor-level return series 更平滑，能保留 regime / crowding / risk appetite 的慢变量。
```

也就是说，EP6 的方向不应该简单回到“找更多个股 signal”，而应认真考虑 **factor state / regime timing** 这条线。

### Insight 2: TSFM 的 edge 可能来自“避开错误因子”，而不是“追逐赢家因子”

validation 中 winner-leg annualized mean 只有 0.37%，但 loser-leg annualized mean 是 -14.07%。TSFM 的收益更像来自：

```text
识别过去 12 个月持续变差的 factor，并反向持有。
```

这和常见的“买最近表现好的 factor”叙事不完全一样。后续应该单独拆：

1. long past-winner factor leg；
2. short past-loser factor leg；
3. long-only timing overlay；
4. short-only / de-risking overlay。

### Insight 3: 当前 result 不能直接导出为 long-only stock strategy

虽然 after-cost 为正，但所有 OOS 月份都需要 short exposure。若强行改写成 long-only，可能会丢掉 `BAB` / `TURN` 的主要收益来源。因此后续不应直接写 long-only portfolio requirement，而应先做 execution framing：

```text
factor timing overlay > hedged factor basket > ETF/futures proxy > long-only fallback
```

### Insight 4: 论文复现价值在于“方向框架”，不是数值复刻

本地 full annualized mean 8.62% 看起来接近论文 9.91%，但这个接近不能被过度解释。真正有价值的是：

```text
在没有完整 fundamental factor set 的情况下，
仅用 SIZE / ILL / TURN / BAB，
仍然可以看到 factor return 的 time-series momentum / reversal-like structure。
```

这给 EP6 的研究方向提供了一个比 H3/H5 个股 signal 更稳定的候选框架。

## 12. 当前结论边界

最终判断：

```text
ep6_tsfm_4factor_local_proxy_positive_diagnostic_only
```

含义：

1. 数据门禁通过。
2. validation 和 robustness 的 gross support gates 通过。
3. validation 和 robustness 的 after-cost mean 都为正。
4. concentration guard 通过。
5. 但结果仍是 4-factor proxy diagnostic，不是完整 paper replication。
6. 不授权策略构造。

下一步如果继续推进，建议优先做：

1. `BAB / TURN` contribution decomposition：beta / liquidity / market regime 中性化后是否保留。
2. 2022 weak-year attribution：确认弱点是否来自特定市场状态。
3. long-only overlay feasibility：如果不能 short，信号还能否用于减少错误暴露。
4. ETF / futures / industry-neutral implementation audit：把 factor-level signal 转换为可执行 framing。
5. PIT fundamental data extension：补齐 BM / GP / CINVEST / EP / ACC / CFP 后再做完整 10-factor paper replication。

This is a 4-factor local feasible TSFM proxy diagnostic.

This is a paper-replication diagnostic only.

It does not authorize strategy construction.
