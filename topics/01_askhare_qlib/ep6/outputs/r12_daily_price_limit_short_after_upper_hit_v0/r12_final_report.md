# R12 涨停后做空本地诊断报告

## 1. 结论摘要

`final_decision = r12_not_evaluable_insufficient_comparator_coverage`

`authorized_strategy_requirement = false`

本轮 R12 测试只检验一个公共日频价格代理：在 PIT mcap500 主板股票中，如果股票在事件日 D 以普通 10% 涨停价附近收盘，是否可以在 D+1 开盘建立短空，并在后续 H=5/10/20 个交易日获得反转收益。它不是论文的账户级复现，因为本地数据没有大户 NetBuy、D+1 大户卖出、融券可得性、融券费、盘中排队位置，也没有交易所原始未复权日线涨跌停标记。

形式上的最终状态是 `not_evaluable_insufficient_comparator_coverage`，原因是同日非涨停高收益 comparator 的匹配覆盖率只有约 31%-33%，低于 70% gate。更重要的是，即使不看 comparator gate，primary H10/H20 的本地做空代理也没有给出支持：validation H10/H20 的 date-weighted gross short return 分别为 -0.68% 和 -0.09%，robustness H10/H20 分别为 -1.84% 和 -2.88%，扣除 110 bps 交易成本后全部更负。

Required caveat: `local_short_after_limit_up_proxy_not_account_level_paper_replication`

## 2. 数据源与检测边界

本次运行使用 `data/qlib/cn_data_pit`，PIT universe 为 `data/universe/pit_mcap500_mainboard_daily.csv`，样本切分为 train 2018-07-01 至 2021-12-31、validation 2022-01-01 至 2023-12-31、robustness 2024-01-01 至 2025-12-31。事件日 D 必须是 PIT mcap500 主板成员，且检测只能用 D 当天及前一有效交易日信息；D+1 及之后价格只用于 entry/exit label，不参与事件筛选。

| 项目 | 当前状态 |
|:--|:--|
| price adjustment | `provider_ohlc_already_adjusted` |
| limit detection source | `provider_ohlc_with_factor_continuity_guard` |
| official unadjusted OHLC | `absent_used_provider_fallback` |
| outside PIT audit | `not_evaluable_local_source_absent` |
| factor continuity tolerance | 0.0001 |
| factor discontinuity blocked rows | 216,385 |
| factor discontinuity blocked share | 56.95% |

关键解释：由于没有官方未复权 OHLC，本轮涨停识别不是交易所级精确识别，而是 provider OHLC 加 factor continuity guard 的代理。factor guard 很严格，导致 216,385 个 instrument-date 在事件分类前被阻断。这个设计提高了检测保守性，但也意味着样本不是全市场、全事件、官方涨跌停标记下的样本。

## 3. 事件检测结果

| split | candidate rows | regular 10% upper-hit | nonlimit high-return | not event / blocked |
|:--|--:|--:|--:|--:|
| train | 159,785 | 483 | 292 | 159,010 |
| validation | 109,722 | 187 | 157 | 109,378 |
| robustness | 110,419 | 538 | 222 | 109,659 |

最小样本 gate 是通过的：validation 有 187 个 regular upper-hit，robustness 有 538 个 regular upper-hit，均超过 100；两段样本均覆盖 23 个事件月，超过 12 个月要求。也就是说，本轮不是因为“涨停事件太少”而无法评估；真正卡住的是 comparator 覆盖率，以及 primary return 本身不支持。

检测阻断分布：

| split | factor discontinuity blocked | missing previous traded close | valid non-event |
|:--|--:|--:|--:|
| train | 103,539 | 19 | 55,452 |
| validation | 65,228 | 1 | 44,149 |
| robustness | 47,618 | 11 | 62,030 |

## 4. Primary d1_open 事件收益

Primary entry 是 `d1_open`：D 日收盘触发涨停事件，D+1 开盘短空，D+H 收盘平仓。下表为 regular upper-hit 事件的 date-weighted 结果，决策 horizon 是 H10 和 H20；H5 是早期反转诊断，H60/H120 是长窗口描述性诊断。

| split | H | events | event dates | gross short | after cost ex borrow | borrow 2bps | borrow 5bps | borrow 10bps | positive date share | NW t |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 1 | 480 | 260 | 0.18% | -0.92% | -0.94% | -0.97% | -1.02% | 53.08% | 0.78 |
| train | 2 | 480 | 260 | 0.26% | -0.84% | -0.88% | -0.94% | -1.04% | 51.92% | 0.74 |
| train | 5 | 480 | 260 | -0.09% | -1.19% | -1.29% | -1.44% | -1.69% | 51.92% | -0.13 |
| train | 10 | 480 | 260 | -0.60% | -1.70% | -1.90% | -2.20% | -2.70% | 52.31% | -0.59 |
| train | 20 | 479 | 260 | -0.57% | -1.67% | -2.07% | -2.67% | -3.67% | 53.85% | -0.30 |
| train | 60 | 478 | 258 | -1.71% | -2.81% | -4.01% | -5.81% | -8.81% | 57.36% | -0.53 |
| train | 120 | 480 | 260 | -6.78% | -7.88% | -10.28% | -13.88% | -19.88% | 51.92% | -1.29 |
| validation | 1 | 186 | 132 | 0.10% | -1.00% | -1.02% | -1.05% | -1.10% | 50.00% | 0.31 |
| validation | 2 | 186 | 132 | -0.28% | -1.38% | -1.42% | -1.48% | -1.58% | 48.48% | -0.58 |
| validation | 5 | 186 | 132 | -1.02% | -2.12% | -2.22% | -2.37% | -2.62% | 50.76% | -1.13 |
| validation | 10 | 186 | 132 | -0.68% | -1.78% | -1.98% | -2.28% | -2.78% | 52.27% | -0.54 |
| validation | 20 | 186 | 132 | -0.09% | -1.19% | -1.59% | -2.19% | -3.19% | 59.85% | -0.04 |
| validation | 60 | 186 | 132 | 5.43% | 4.33% | 3.13% | 1.33% | -1.67% | 66.67% | 1.62 |
| validation | 120 | 186 | 132 | 9.39% | 8.29% | 5.89% | 2.29% | -3.71% | 71.97% | 3.33 |
| robustness | 1 | 531 | 195 | 0.11% | -0.99% | -1.01% | -1.04% | -1.09% | 49.23% | 0.45 |
| robustness | 2 | 531 | 195 | -0.23% | -1.33% | -1.37% | -1.43% | -1.53% | 50.26% | -0.53 |
| robustness | 5 | 529 | 194 | -0.84% | -1.94% | -2.04% | -2.19% | -2.44% | 50.00% | -0.95 |
| robustness | 10 | 530 | 195 | -1.84% | -2.94% | -3.14% | -3.44% | -3.94% | 49.74% | -1.25 |
| robustness | 20 | 529 | 195 | -2.88% | -3.98% | -4.38% | -4.98% | -5.98% | 51.28% | -1.15 |
| robustness | 60 | 530 | 195 | -5.14% | -6.24% | -7.44% | -9.24% | -12.24% | 51.79% | -1.03 |
| robustness | 120 | 447 | 162 | -8.29% | -9.39% | -11.79% | -15.39% | -21.39% | 51.85% | -1.38 |

主要发现：

- H10 和 H20 是正式决策 horizon；两段 OOS 都是负的，且扣成本后更差。
- validation H20 的 positive date share 达到 59.85%，但平均收益仍为 -0.09%，说明正收益日期的幅度不足以抵消负收益日期，而 t-stat 也接近 0。
- validation 的 H60/H120 出现正收益，但 requirement 已冻结 H60/H120 为长窗口 diagnostic，不能替代 H10/H20。更重要的是 robustness H60/H120 仍为负，说明长窗口正收益不稳健。
- 110 bps 交易成本已经足以让 H1 的微弱 gross edge 变成约 -1%。融券费 stress 后，H10/H20 全部进一步恶化。

## 5. Entry Timing Robustness

下表比较 `d0_close_oracle`、`d1_open`、`d1_close` 在 H10/H20 的表现。`d0_close_oracle` 是非可执行路径，只用于理解从涨停收盘价开始计算时的反转形态。

| split | entry variant | H | events | gross short | after cost ex borrow | positive date share | NW t |
|:--|:--|--:|--:|--:|--:|--:|--:|
| validation | d0_close_oracle | 10 | 187 | -1.71% | -2.81% | 46.62% | -1.26 |
| validation | d0_close_oracle | 20 | 187 | -1.11% | -2.21% | 57.89% | -0.50 |
| validation | d1_open | 10 | 186 | -0.68% | -1.78% | 52.27% | -0.54 |
| validation | d1_open | 20 | 186 | -0.09% | -1.19% | 59.85% | -0.04 |
| validation | d1_close | 10 | 186 | -0.79% | -1.89% | 47.73% | -0.67 |
| validation | d1_close | 20 | 186 | -0.20% | -1.30% | 58.33% | -0.10 |
| robustness | d0_close_oracle | 10 | 537 | -3.63% | -4.73% | 46.94% | -2.24 |
| robustness | d0_close_oracle | 20 | 536 | -4.67% | -5.77% | 45.41% | -1.83 |
| robustness | d1_open | 10 | 530 | -1.84% | -2.94% | 49.74% | -1.25 |
| robustness | d1_open | 20 | 529 | -2.88% | -3.98% | 51.28% | -1.15 |
| robustness | d1_close | 10 | 530 | -1.96% | -3.06% | 51.28% | -1.41 |
| robustness | d1_close | 20 | 529 | -2.96% | -4.06% | 47.18% | -1.24 |

Insight：entry timing 没有改变结论。`d1_open` 相比 `d0_close_oracle` 略好，说明从 D close 到 D+1 open 可能已经释放了一部分涨停后的继续上涨压力；但 D+1 open 之后的 H10/H20 仍不是正收益。`d1_close` 也没有改善，说明简单推迟到 D+1 收盘并不能把这个 proxy 变成可支持的短空信号。

## 6. Comparator 结果

Comparator 是同日 `8% <= return < 9.8%` 的非涨停高收益股票，按同日、同行业优先、size percentile 最近匹配，并且同一 comparator 当天不可重复使用。

| split | H | upper-hit denominator | matched | matched share | same-industry share | median size pct diff | coverage status | incremental short return | NW t |
|:--|--:|--:|--:|--:|--:|--:|:--|--:|--:|
| train | 5 | 480 | 160 | 33.33% | 36.88% | 15.30% | fail_insufficient_matched_event_share | -0.31% | -0.31 |
| train | 10 | 480 | 160 | 33.33% | 36.88% | 15.30% | fail_insufficient_matched_event_share | -0.69% | -0.51 |
| train | 20 | 479 | 160 | 33.40% | 36.88% | 15.30% | fail_insufficient_matched_event_share | -0.01% | -0.00 |
| validation | 5 | 186 | 57 | 30.65% | 31.58% | 15.42% | fail_insufficient_matched_event_share | -0.88% | -0.73 |
| validation | 10 | 186 | 57 | 30.65% | 31.58% | 15.42% | fail_insufficient_matched_event_share | -0.07% | -0.04 |
| validation | 20 | 186 | 57 | 30.65% | 31.58% | 15.42% | fail_insufficient_matched_event_share | -0.78% | -0.46 |
| robustness | 5 | 529 | 173 | 32.70% | 46.24% | 10.61% | fail_insufficient_matched_event_share | -0.83% | -0.65 |
| robustness | 10 | 530 | 172 | 32.45% | 46.51% | 10.75% | fail_insufficient_matched_event_share | -1.27% | -0.59 |
| robustness | 20 | 529 | 173 | 32.70% | 46.24% | 10.61% | fail_insufficient_matched_event_share | -0.04% | -0.03 |

Comparator 的低覆盖不是一个小瑕疵，而是这个实验能否声称“涨停事件比普通高收益事件更可反转”的核心约束。validation 只有 157 个 nonlimit high-return 候选，对应 187 个 upper-hit；robustness 有 222 个 nonlimit high-return 候选，对应 538 个 upper-hit。由于还要求同日匹配和 comparator 不复用，最终可匹配 upper-hit 只剩约三分之一。

在已经匹配到的样本里，incremental short return 也没有支持涨停事件更好做空：validation H10/H20 分别是 -0.07% 和 -0.78%，robustness H10/H20 分别是 -1.27% 和 -0.04%。因此，即使放松 coverage gate，这条线也不是“涨停后短空明显强于普通高收益短空”。

## 7. Gate Replay

| gate group | pass | fail | 含义 |
|:--|--:|--:|:--|
| minimum_sample | 12 | 0 | 样本数量、事件月、entry/label completeness 均过关 |
| support | 2 | 12 | H10/H20 的收益方向、成本后收益、validation t-stat 多数失败 |
| comparator_coverage | 0 | 4 | validation/robustness H10/H20 matched share 均低于 70% |
| comparator_direction | 0 | 4 | matched subset 的 incremental short return 均未转正 |

失败 gate 的集中含义很清楚：

- `r12_not_evaluable_insufficient_comparator_coverage` 是按 contract priority 得出的正式结果。
- `support` 组失败说明 primary short-after-upper-hit proxy 本身没有过收益门槛。
- `comparator_direction` 组失败说明当前可匹配 comparator 样本中，涨停事件也没有优于普通高收益事件。

## 8. Entry/Exit 可评估性

Primary entry 的可评估性很高，因此本轮负结果不能主要归因于 D+1 无法入场或未来 label 缺失。

| split | H | complete rows | one-price locked | exit missing |
|:--|--:|--:|--:|--:|
| train | 5 | 480 | 3 | 0 |
| train | 10 | 480 | 3 | 0 |
| train | 20 | 479 | 3 | 1 |
| validation | 5 | 186 | 1 | 0 |
| validation | 10 | 186 | 1 | 0 |
| validation | 20 | 186 | 1 | 0 |
| robustness | 5 | 529 | 7 | 2 |
| robustness | 10 | 530 | 7 | 1 |
| robustness | 20 | 529 | 7 | 2 |

Interpretation：日频 OHLC 无法确认涨停队列成交，所以 one-price locked 被保守阻断。但阻断量很小，primary evidence 主要来自完整可评估事件。

## 9. Cluster 与状态归因

涨停事件多数是 first-hit，而不是连续涨停的 continuation-hit。

| split | first-hit events | continuation-hit events | cluster count | mean cluster length | max cluster length |
|:--|--:|--:|--:|--:|--:|
| train | 457 | 26 | 457 | 1.06 | 3 |
| validation | 180 | 7 | 180 | 1.04 | 3 |
| robustness | 464 | 74 | 464 | 1.16 | 4 |

状态归因只做描述，不进入最终 gate。几个值得注意的模式：

- robustness 的 down market H20 很弱：gross short return -6.55%，positive date share 40.00%。
- robustness 的 continuation-hit H10 很弱：gross short return -5.69%，尽管 positive date share 为 58.97%，说明亏损日幅度较大。
- validation 的 up market H20 较好：gross short return 1.54%，positive date share 70.73%，但这是状态子样本，不是 frozen primary decision。
- robustness 中低 turnover / middle money-liquidity 的若干子样本 H10 为正，例如 turnover middle H10 为 3.34%，但这些是事后状态切片，不能替代整体 H10/H20 gate。

| state axis | state value | split | H | events | gross short | positive date share |
|:--|:--|:--|--:|--:|--:|--:|
| market_state | down | robustness | 20 | 104 | -6.55% | 40.00% |
| cluster_position | continuation_hit | robustness | 10 | 72 | -5.69% | 58.97% |
| size_bucket | middle | robustness | 10 | 190 | -4.63% | 50.00% |
| turnover_bucket | high | robustness | 20 | 469 | -3.26% | 50.00% |
| cluster_position | first_hit | validation | 20 | 179 | 0.64% | 61.42% |
| market_state | up | validation | 20 | 62 | 1.54% | 70.73% |
| turnover_bucket | middle | robustness | 10 | 40 | 3.34% | 69.23% |

Insight：如果后续继续研究，状态条件更像“失败诊断/规避条件”而不是直接策略授权信号。当前整体样本不支持短空，但某些状态切片显示涨停后路径差异较大，值得单独 requirement 重新冻结规则后再测。

## 10. Calendar-Time Portfolio 诊断

Calendar-time 组合把同一事件日的 entry-evaluable upper-hit 作为同日短空 vintage，并按 horizon 持有到期。这个诊断用于检查重叠事件和集中度，不参与最终 decision。

| split | H | calendar days | mean active events | daily gross return | name-capped daily return | positive day share |
|:--|--:|--:|--:|--:|--:|--:|
| validation | 5 | 367 | 2.53 | -0.209% | -0.208% | 49.591% |
| validation | 10 | 448 | 4.13 | -0.132% | -0.104% | 51.116% |
| validation | 20 | 476 | 7.84 | -0.100% | -0.106% | 50.420% |
| robustness | 5 | 375 | 6.95 | 0.034% | 0.029% | 50.133% |
| robustness | 10 | 438 | 11.76 | -0.038% | -0.038% | 50.228% |
| robustness | 20 | 475 | 21.19 | 0.117% | 0.134% | 54.105% |

Calendar-time 结果比 event-study 更接近零，但没有改变结论：它没有提供稳定、成本后、可解释的短空 edge。name cap 后结果变化很小，说明这批事件的结论不是由单一股票极端集中驱动的。

## 11. Paper vs Local Gap

本地结果不能被解释为“推翻论文”。论文的核心机制是账户级：大户在涨停日买入、次日卖出，随后出现长窗口反转。本地 R12 只看到公共 OHLCV，无法观察大户买卖、账户分类、卖出压力、排队成交、融券约束。

主要差异：

| 维度 | 论文 | R12 本地代理 |
|:--|:--|:--|
| 样本 | SZSE A-share，2012-2015 | PIT mcap500 主板，2018-2025 |
| 机制变量 | account-level large-investor NetBuy | 不可用 |
| 涨停识别 | 交易所价格限制与日线 | provider OHLC + factor continuity guard |
| entry timing | 研究 D 和 D+1 大户行为 | D+1 open 短空代理 |
| 执行可行性 | 不证明可做空策略 | 明确不授权策略 |
| comparator | 论文 near-limit / DGTW 等控制 | 同日 nonlimit high-return size/industry match |

结论应该表述为：在当前本地 PIT500 主板、provider OHLC、D+1 open entry、H10/H20 决策 horizon 下，公开价格短空代理没有获得支持；它不回答论文账户级 destructive market behavior 是否存在。

## 12. 后续建议

1. 不应直接把“涨停后做空”推进为策略实验。当前 H10/H20、成本后收益、comparator direction 都不支持。
2. 如果继续研究，优先做数据质量方向：找到官方未复权 OHLC / 涨跌停价字段，减少 provider adjusted OHLC + factor guard 对样本的影响。
3. Comparator 需要重新设计独立 requirement：当前同日 nonlimit high-return 太稀疏，导致 coverage 不足；可考虑事前冻结更宽的同日高收益桶或 date-level benchmark，但不能在本轮结果后回填 gate。
4. 状态条件只能作为下一轮 hypothesis source。比如 market_state、turnover、cluster_position 有明显差异，但必须先写新 requirement，再跑新的 OOS gate。
