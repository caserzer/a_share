# R02 Big Winner 覆盖比例搜索 V1 详细报告

## 结论摘要

本次运行是 full-sample descriptive profile，不是 holdout validation，不是 entry prior，也不直接支持下一阶段准入。它回答的是：在 845 个 canonical R01 primary big winner 的 `reference_date` 后 `T+0..T+30` 内，哪些同 family 的并列日级条件经常出现。

核心发现：

1. `volume_money` 是本轮最值得保留为描述性画像线索的 family。它给出了全局最低密度达标候选：覆盖 `745 / 845 = 88.17%`，eligible-day density 只有 `5.77%`。
2. 若只追求最高覆盖，多个 family 可以达到接近或等于 `100%`，但很多条件非常宽，density 高到 `24%` 到 `84%`，更像 big winner 发展过程中的常见状态，不像可执行筛选条件。
3. `range_breakout` 的低密度达标版本覆盖最高：`96.80%`，density `17.37%`，说明新高/区间上沿状态几乎是 big winner 后 30 日画像的核心结构。
4. `oscillator` 和 `volatility_band` 能在较低 density 下过 `85%`，但覆盖更贴近门槛，触发 offset 也偏后，像趋势确认后的状态，而不是早期锚点。
5. 这个结果应该用于下一轮描述、诊断和构造假设，不应直接转成买入信号、胜率先验或风险预算。

## 数据与执行

| item | value |
|:--|--:|
| canonical R01 primary big winner | 845 |
| R01 PIT-executable eligible stock-days | 395386 |
| profile window | T+0..T+30 |
| atomic conditions | 392 |
| selected atomic conditions | 168 |
| deterministic atom cap per family | 24 |
| condition groups searched | 88550 |
| coverage >= 85% groups | 31161 |
| parallel workers | 12 |
| chunks | 178 |
| failed / retried chunks | 0 / 0 |

并行结果 hash 与 audit hash 一致：

```text
23df173a287171dd5b068ce128755f888e3df809e45bb67b970ea93282c273bf
```

## 定义

覆盖率：

```text
同一股票在 reference_date 的 T+0 到 T+30 至少一天满足该 condition group
```

密度：

```text
condition group 在 R01 PIT-executable eligible stock-days 上的日级触发比例
```

所有 condition group 都是同一 family 内部的 `AND3` 或 `AND4`。`market_context` 只做分解审计，没有作为 filter 改变主结果。

## 全局最低密度达标候选

```text
volume_ratio5_r02 >= 1.5
AND money_zscore5_r02 >= 2.0
AND money_price_coherence5_r02 == 1.0
AND money_price_coherence10_r02 == 1.0
```

| metric | value |
|:--|--:|
| condition_group_id | volume_money__and4__4eb7a99e922f |
| family | volume_money |
| kind | same_family_and4 |
| coverage | 88.17% |
| covered events | 745 / 845 |
| uncovered events | 100 |
| eligible-day density | 5.77% |
| feature-eligible density | 5.77% |
| median earliest hit offset | 11 |

Split 覆盖：

| split | covered / total | coverage |
|:--|--:|--:|
| train | 388 / 446 | 86.99% |
| validation | 139 / 158 | 87.97% |
| robustness | 218 / 241 | 90.46% |

年度覆盖：

| year | event_count | coverage |
|--:|--:|--:|
| 2017 | 27 | 92.59% |
| 2018 | 62 | 90.32% |
| 2019 | 69 | 92.75% |
| 2020 | 182 | 85.16% |
| 2021 | 106 | 83.02% |
| 2022 | 112 | 91.07% |
| 2023 | 46 | 80.43% |
| 2024 | 95 | 85.26% |
| 2025 | 146 | 93.84% |

解读：这个组合强调放量、成交额异常和价量同向。它不是最早触发的画像，median earliest offset 是 `T+11`，但它用很低的全市场日级密度覆盖了接近九成 big winner。它更像“big winner 展开后成交确认状态”，不是 `T+0` 入场条件。

## Family 结果概览

| family | all groups | ge85 groups | ge85 rate | max coverage | median ge85 coverage | min density in ge85 | median density in ge85 |
|:--|--:|--:|--:|--:|--:|--:|--:|
| momentum_rps | 12650 | 1791 | 14.16% | 99.29% | 89.11% | 11.16% | 16.76% |
| oscillator | 12650 | 8530 | 67.43% | 99.76% | 91.36% | 5.85% | 16.40% |
| price_trend | 12650 | 674 | 5.33% | 100.00% | 89.11% | 8.75% | 19.65% |
| pullback_drawdown | 12650 | 4845 | 38.30% | 100.00% | 96.45% | 14.28% | 32.55% |
| range_breakout | 12650 | 5985 | 47.31% | 100.00% | 98.11% | 17.37% | 19.29% |
| volatility_band | 12650 | 4480 | 35.42% | 100.00% | 92.66% | 7.14% | 20.44% |
| volume_money | 12650 | 4856 | 38.39% | 100.00% | 97.99% | 5.77% | 11.84% |

主要含义：

- `price_trend` 的达标比例最低，说明单纯趋势条件要么太宽，要么不容易在同 family AND3/AND4 下稳定覆盖 85%。
- `oscillator` 达标数量最多，但很多震荡条件可能只是趋势展开后的确认状态，需要避免过度解释。
- `volume_money` 的密度-覆盖关系最好：既能出现 `100%` 覆盖候选，也能给出全局最低密度达标候选。
- `range_breakout` 的覆盖稳定性强，但最低密度也不低，说明突破/新高本身是 big winner 的共同画像，却不是稀有事件。

## 最高覆盖候选

这里的“最高覆盖”只按 `coverage_t0_t30 desc` 排序，density 只是同覆盖率下的 tie-breaker。因此它回答的是“这个 family 最共同的 winner 状态是什么”，不是“哪个条件最稀疏”。

| family | condition | coverage | density | median offset |
|:--|:--|--:|--:|--:|
| momentum_rps | market_relative_ret5 >= 0.0 AND rps5 >= 0.5 AND rps5 >= 0.6 | 99.29% | 39.53% | 3 |
| oscillator | macd_hist5 >= 0 AND macd_hist10 >= 0 AND macd_hist30 >= 0 | 99.76% | 51.00% | 4 |
| price_trend | close over MA5 / EMA5 / MA10 all >= 0 | 100.00% | 40.24% | 3 |
| pullback_drawdown | close within 5d high by -5%, days_since_high5 <= 5, 10d drawdown >= -20% | 100.00% | 84.25% | 0 |
| range_breakout | 5d new high and 5d range position >= 0.7 / 0.9 | 100.00% | 24.42% | 4 |
| volatility_band | realized_vol5 <= 8%, boll_pct_b5 >= 0.5, channel position5 >= 0.9, boll_pct_b10 >= 0.5 | 100.00% | 27.47% | 4 |
| volume_money | volume_ratio5 >= 1.2, money_zscore5 >= 2.0, amount_ratio10 >= 1.0, turnover_ratio10 >= 1.0 | 100.00% | 12.96% | 4 |

发现：最高覆盖条件普遍非常宽。比如 `pullback_drawdown` 的最高覆盖版本 density 高达 `84.25%`，几乎不能当成筛选信息。相比之下，`volume_money` 的 `100%` 覆盖版本 density `12.96%`，是最高覆盖表里最有信息含量的候选。

## 最低密度达标候选

这里先要求 `coverage >= 85%`，再按 density 从低到高排序。它回答的是“这个 family 是否存在一个不太泛滥但仍能覆盖大多数 winner 的状态”。

| family | condition | coverage | density | mean first hit | median first hit | split stability |
|:--|:--|--:|--:|--:|--:|:--|
| momentum_rps | roc5 >= 5%, rps5 >= 80%, rps10 >= 50% | 85.09% | 11.16% | T+9.2 | T+8 | robustness 83.82% below 85% |
| oscillator | kdj_k5 >= 60, cci5 >= 100, kdj_k10 >= 55, cci10 >= 150 | 85.09% | 5.85% | T+11.3 | T+11 | validation 82.91% below 85% |
| price_trend | close_over_ma5 >= 3%, ema_slope5 >= 0, close_over_ma10 >= 3% | 86.15% | 8.75% | T+9.3 | T+7 | validation 82.28% below 85% |
| pullback_drawdown | pullback_depth5 >= -5%, rebound_from_low5 >= 5%, days_since_high10 <= 5 | 90.30% | 14.28% | T+8.8 | T+7 | all splits above 88% |
| range_breakout | range_position5 >= 0.9, 10d new high, range_position10 >= 0.7 | 96.80% | 17.37% | T+8.0 | T+7 | all splits above 95% |
| volatility_band | boll_pct_b5 >= 0.8, boll_width5 >= 1.0, boll_width10 >= 1.0, channel position10 >= 0.8 | 85.21% | 7.14% | T+10.1 | T+8 | train 83.41% below 85% |
| volume_money | volume_ratio5 >= 1.5, money_zscore5 >= 2.0, 5d/10d money-price coherence | 88.17% | 5.77% | T+11.8 | T+11 | all splits above 86% |

发现：最低密度达标条件比最高覆盖条件更接近“有信息量的画像”。其中 `volume_money` 的全局最低 density 与 split 稳定性最好，`range_breakout` 的 coverage 最强但 density 也较高。

## Tradeoff 观察

### 1. 覆盖率最高不等于研究价值最高

`coverage = 100%` 的条件很多，但它们可能只是趋势展开后几乎必然出现的状态。`price_trend`、`range_breakout`、`volatility_band` 的最高覆盖候选都能覆盖全部 845 个 winner，但对应 density 分别是 `40.24%`、`24.42%`、`27.47%`。这些状态适合描述 winner 的共性，不适合直接当成可执行筛选。

### 2. 成交量/成交额确认是本轮最强画像

`volume_money` 同时满足两个条件：

- 高覆盖版本可以达到 `100%`，density `12.96%`；
- 最低密度版本仍覆盖 `88.17%`，density 只有 `5.77%`。

这说明 big winner 在 reference 后 30 日内经常伴随成交活跃、资金异常和价量同向。这个 family 比单纯价格趋势更像一个可进一步研究的状态确认层。

### 3. 突破/新高是核心状态，但不是稀有状态

`range_breakout` 的最低密度达标候选覆盖 `96.80%`，是所有最低密度达标候选中覆盖最高的。但它的 density `17.37%`，说明新高/区间上沿在全市场 eligible days 中并不稀有。它更适合作为 big winner 生命周期的结构标签，而不是单独筛选器。

### 4. 震荡与波动条件更像后验确认

`oscillator` 和 `volatility_band` 的最低密度分别是 `5.85%` 和 `7.14%`，看起来很稀疏，但 coverage 都贴近 `85%` 门槛，median earliest offset 分别是 `11` 和 `8`。这类条件可能更多出现在趋势确认之后，后续如果使用，应该注意 timing lag。

### 5. full-sample profile 的边界必须保留

本报告没有提供 `P(winner | signal)`、LR、EV_R 或 matched background enrichment。所有结果都来自 845 个已知 winner 的 post-reference 窗口，因此不能解释为 entry edge。最合理的下一步不是直接交易，而是把这些 family 作为候选画像，再回到 action-time denominator 做 prior/posterior 校准。

## 数据文件

主要输出：

- `reports/r02_big_winner_coverage_all.csv`
- `reports/r02_big_winner_coverage_ge85.csv`
- `reports/r02_big_winner_coverage_lowest_density_ge85.csv`
- `reports/r02_big_winner_coverage_top_by_family.csv`
- `reports/r02_big_winner_coverage_uncovered_events.csv`
- `reports/r02_big_winner_coverage_market_context_decomposition.csv`
- `reports/r02_big_winner_coverage_validation_audit.csv`
- `manifests/r02_big_winner_coverage_manifest.json`

validation status: `passed`

## Final Decision

`descriptive_coverage_profiles_found`

解释：本轮已经找到多个 full-sample high-recall winner profiles，尤其是 `volume_money` 和 `range_breakout`。但这些结果只构成描述性 evidence，不构成 holdout validation、entry prior、posterior precision 或可进入下一阶段的 family 结论。
