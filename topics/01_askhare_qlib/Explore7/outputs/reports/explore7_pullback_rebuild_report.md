# Explore7 Pullback 子系统重建详细报告

## 1. 核心结论
- 未形成 `candidate_for_future_final_test`。所有 rebuilt/strong-trend 候选仍为 diagnostic-only。
- rebuilt pullback 被降级：改善主要来自交易数下降或现金比例升高。
- 本次策略回放只能视为 `coverage_limited_diagnostic`：PIT universe 与 PIT industry 已构建，但行情 provider 回退到旧 Explore1 provider，覆盖率只有 `86.17%` 左右，不能作为最终可交易结论。
- rebuilt/strong-trend 版本没有通过验收：正收益年份 `2/3`，qualified 年份 `3/4`，expectancy 改善年份 `2/4`，交易数比例 `0.41`，平均现金 `97.77%`。

## 2. 数据可信边界
- Universe point-in-time: `True`
- Industry point-in-time: `True`
- Provider coverage ratio: `86.17%`
- Coverage-limited diagnostic: `True`
- Historical result CSV used for calculation: `False`
- Provider used for this diagnostic replay: `Explore1/data/qlib/cn_data`
- Missing PIT membership rows in provider: `60,735` / `439,140`

### 2.1 PIT Universe 摘要
| Metric | Value |
| --- | --- |
| daily membership rows | 439,140 |
| distinct instruments | 539 |
| daily members min/median/max | 113 / 220.0 / 310 |
| daily membership changed | True |
| static 2025-12-31 universe used as authority | False |

解释：PIT universe 已经替代静态 `2025-12-31` 股票池作为交易资格来源；membership 是逐日变化的，说明当前不再把未来静态股票池直接投射回历史。

### 2.2 PIT Universe 与旧静态 universe 差异
| Metric | Value |
| --- | --- |
| 旧静态 universe instruments | 282 |
| PIT research-window distinct instruments | 440 |
| 两者重叠 instruments | 250 |
| 只在 PIT research-window 出现 | 190 |
| 只在旧静态 universe 出现 | 32 |
| PIT daily member mean/median | 210.1 / 222.0 |

旧静态 universe 与 PIT universe 的行业结构也不同。PIT research-window 平均权重最高的是非银金融、银行、电子；旧静态池中有色金属、非银金融、电子、银行更靠前。这说明 Explore7 的结果不能和 Explore1 静态池结果直接等同。
| PIT industry | Avg daily members | Avg share |
| --- | --- | --- |
| 非银金融 | 22.0 | 10.67% |
| 银行 | 21.4 | 10.37% |
| 电子 | 15.6 | 7.34% |
| 交通运输 | 12.8 | 6.20% |
| 医药生物 | 12.9 | 6.11% |
| 食品饮料 | 12.8 | 6.09% |
| 公用事业 | 10.2 | 4.87% |
| 电力设备 | 10.6 | 4.86% |
| Static industry | Members |
| --- | --- |
| 有色金属 | 25 |
| 非银金融 | 24 |
| 电子 | 24 |
| 银行 | 24 |
| 交通运输 | 19 |
| 公用事业 | 17 |
| 电力设备 | 15 |
| 汽车 | 14 |

### 2.3 Source Audit
- Rows: `41`
- Forbidden result paths used for calculation: `0`
- Classification counts: `{'allowed_structural_config_key': 10, 'background_reference': 3, 'forbidden_result_path': 21, 'source_config_non_path_value': 7}`

## 3. Fold 回放结果
| Version | Trades | Positive folds | Mean return | Worst return | Worst DD | Avg cash | Max cash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| breakdown-repair diagnostic | 3598 | 2/5 | 0.20% | -30.96% | -34.40% | 48.15% | 49.77% |
| breakout core baseline | 91 | 3/5 | 0.63% | -0.99% | -2.04% | 98.00% | 99.30% |
| original pullback baseline | 288 | 1/5 | -0.11% | -2.82% | -4.21% | 95.86% | 98.29% |
| rebuilt pullback candidate | 117 | 3/5 | 0.29% | -1.70% | -2.52% | 97.77% | 99.28% |
| strong-trend candidate | 117 | 3/5 | 0.29% | -1.70% | -2.52% | 97.77% | 99.28% |
| weak-volume diagnostic | 2811 | 2/5 | -5.60% | -26.24% | -28.06% | 63.13% | 66.64% |

解读：`pit_rebuilt_pullback_candidate` 与 `pit_strong_trend_pullback_candidate` 完全一致，说明第一版 rebuilt 只保留 strong-trend continuation。它的 fold return 均值略高于原 pullback baseline，但交易数从 288 降到 117，平均现金从 95.86% 升到 97.77%，因此改善主要是少交易和高现金，而不是 pullback 子规则质量显著提升。

### 3.1 Fold 明细
| Version | Fold | Trades | Return | Max DD | Avg Cash |
| --- | --- | --- | --- | --- | --- |
| breakout core baseline | WF1 | 30 | 0.92% | -2.04% | 96.98% |
| breakout core baseline | WF2 | 17 | 3.90% | -1.07% | 97.50% |
| breakout core baseline | WF3 | 6 | 0.15% | -1.16% | 99.30% |
| breakout core baseline | WF4 | 13 | -0.82% | -1.25% | 98.75% |
| breakout core baseline | WF5 | 25 | -0.99% | -1.86% | 97.47% |
| original pullback baseline | WF1 | 79 | -0.19% | -3.95% | 93.77% |
| original pullback baseline | WF2 | 59 | 4.33% | -2.44% | 94.86% |
| original pullback baseline | WF3 | 27 | -0.20% | -2.27% | 98.29% |
| original pullback baseline | WF4 | 33 | -1.68% | -2.09% | 97.84% |
| original pullback baseline | WF5 | 90 | -2.82% | -4.21% | 94.53% |
| strong-trend candidate | WF1 | 36 | 0.66% | -2.39% | 96.57% |
| strong-trend candidate | WF2 | 20 | 3.35% | -1.07% | 97.42% |
| strong-trend candidate | WF3 | 7 | 0.15% | -1.18% | 99.28% |
| strong-trend candidate | WF4 | 16 | -0.99% | -1.25% | 98.64% |
| strong-trend candidate | WF5 | 38 | -1.70% | -2.52% | 96.95% |
| weak-volume diagnostic | WF1 | 472 | 11.63% | -12.27% | 64.32% |
| weak-volume diagnostic | WF2 | 576 | -0.87% | -13.88% | 62.45% |
| weak-volume diagnostic | WF3 | 590 | -26.24% | -28.06% | 66.64% |
| weak-volume diagnostic | WF4 | 594 | -20.97% | -21.64% | 65.47% |
| weak-volume diagnostic | WF5 | 579 | 8.46% | -14.36% | 56.78% |
| breakdown-repair diagnostic | WF1 | 587 | 38.52% | -11.91% | 47.08% |
| breakdown-repair diagnostic | WF2 | 683 | 20.87% | -14.27% | 46.81% |
| breakdown-repair diagnostic | WF3 | 824 | -26.49% | -34.40% | 49.77% |
| breakdown-repair diagnostic | WF4 | 808 | -30.96% | -31.40% | 49.75% |
| breakdown-repair diagnostic | WF5 | 696 | -0.94% | -17.43% | 47.32% |
| rebuilt pullback candidate | WF1 | 36 | 0.66% | -2.39% | 96.57% |
| rebuilt pullback candidate | WF2 | 20 | 3.35% | -1.07% | 97.42% |
| rebuilt pullback candidate | WF3 | 7 | 0.15% | -1.18% | 99.28% |
| rebuilt pullback candidate | WF4 | 16 | -0.99% | -1.25% | 98.64% |
| rebuilt pullback candidate | WF5 | 38 | -1.70% | -2.52% | 96.95% |

## 4. Distinct Year 对照
| Version | Year | Trades | Return | Expectancy | Cash |
| --- | --- | --- | --- | --- | --- |
| breakout core baseline | 2019 | 17 | -1.00% | -939.89 | 97.39% |
| breakout core baseline | 2020 | 13 | 2.29% | 2142.88 | 96.73% |
| breakout core baseline | 2021 | 3 | 0.91% | 1966.33 | 98.49% |
| breakout core baseline | 2022 | 3 | -0.44% | -1467.12 | 99.74% |
| breakout core baseline | 2023 | 10 | -0.38% | -378.90 | 97.77% |
| breakout core baseline | 2024 | 15 | -0.61% | -416.62 | 97.17% |
| original pullback baseline | 2019 | 34 | -0.90% | -458.66 | 94.74% |
| original pullback baseline | 2020 | 45 | 1.11% | 541.48 | 92.94% |
| original pullback baseline | 2021 | 13 | 1.76% | 558.09 | 97.22% |
| original pullback baseline | 2022 | 14 | -0.92% | -661.12 | 98.79% |
| original pullback baseline | 2023 | 19 | -0.76% | -397.89 | 96.91% |
| original pullback baseline | 2024 | 71 | -2.08% | -303.86 | 92.13% |
| rebuilt pullback candidate | 2019 | 20 | -0.66% | -657.48 | 96.74% |
| rebuilt pullback candidate | 2020 | 16 | 1.71% | 1421.89 | 96.57% |
| rebuilt pullback candidate | 2021 | 3 | 0.91% | 1966.33 | 98.48% |
| rebuilt pullback candidate | 2022 | 4 | -0.44% | -1110.24 | 99.71% |
| rebuilt pullback candidate | 2023 | 12 | -0.55% | -455.16 | 97.58% |
| rebuilt pullback candidate | 2024 | 26 | -1.16% | -450.62 | 96.31% |

### 4.1 Rebuilt vs Original vs Breakout
| Year | Original return | Rebuilt return | Breakout return | Expectancy delta | Rebuilt/orig trades | Rebuilt cash |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | -0.90% | -0.66% | -1.00% | -198.82 | 20/34 | 96.74% |
| 2020 | 1.11% | 1.71% | 2.29% | 880.40 | 16/45 | 96.57% |
| 2021 | 1.76% | 0.91% | 0.91% | 1408.23 | 3/13 | 98.48% |
| 2022 | -0.92% | -0.44% | -0.44% | -449.12 | 4/14 | 99.71% |
| 2023 | -0.76% | -0.55% | -0.38% | -57.27 | 12/19 | 97.58% |
| 2024 | -2.08% | -1.16% | -0.61% | -146.76 | 26/71 | 96.31% |

逐年看，rebuilt 的 yearly expectancy 只在 `2` 个 distinct years 优于原 pullback，相对 breakout core 同时满足收益不低且交易覆盖增加的年份只有 `1` 个；两项都没有达到验收要求。2021 和 2022 的 rebuilt 交易数尤其低，说明该版本没有提供稳定交易覆盖。

## 5. Pullback 三类拆分结果
### 5.1 分类覆盖
说明：下表按 fold-valid 视角统计，fold 之间有重叠年份，因此用于覆盖审计，不解释为去重样本数。
| Class | Candidate rows | PIT member count sum | Insufficient rows |
| --- | --- | --- | --- |
| breakdown_repair | 36,040 | 3,828 | 0 |
| weak_volume_rebound | 12,326 | 3,228 | 0 |
| unclassified_pullback | 7,354 | 1,700 | 0 |
| strong_trend_continuation | 99 | 81 | 24 |

### 5.2 分类回放表现
| Version | Class | Trades | Net PnL | Avg Expectancy | Positive class-years | Stop/Time |
| --- | --- | --- | --- | --- | --- | --- |
| breakdown-repair diagnostic | breakdown_repair | 3573 | 29132.24 | 83.03 | 4/10 | 45.37% |
| original pullback baseline | breakdown_repair | 68 | -981.58 | 286.96 | 6/10 | 46.23% |
| original pullback baseline | strong_trend_continuation | 23 | -16519.61 | -660.75 | 1/8 | 46.88% |
| original pullback baseline | unclassified_pullback | 30 | -23488.42 | -731.55 | 3/10 | 92.50% |
| original pullback baseline | weak_volume_rebound | 89 | 10359.23 | -76.59 | 4/10 | 57.23% |
| rebuilt pullback candidate | strong_trend_continuation | 27 | -18410.49 | -689.43 | 1/8 | 49.72% |
| strong-trend candidate | strong_trend_continuation | 27 | -18410.49 | -689.43 | 1/8 | 49.72% |
| weak-volume diagnostic | weak_volume_rebound | 2774 | -320005.40 | -85.39 | 4/10 | 53.51% |

分类解释：
- `strong_trend_continuation` 没有证明自己是可选候选。valid 覆盖中样本非常少，rebuilt/strong-trend 实际 pullback 交易只有 27 笔，合计 net PnL 为负，且 positive class-years 只有 1/8。
- `weak_volume_rebound` 在 diagnostic-only 回放中交易数充足，但合计 net PnL 明显为负，且 stop/time 占比高，继续支持 Explore4/5 对弱量反弹区域的风险判断。
- `breakdown_repair` diagnostic 的合计 net PnL 为正，但 fold 回撤和年度波动很大，2021-2022 明显转弱；它不能直接提升为默认 pullback，只能作为独立规则研究对象，且必须重新设计风险约束。
- `unclassified_pullback` 在原始 baseline 中 stop/time 占比极高，说明原 pullback 定义里仍有大量没有明确结构优势的噪声样本。

## 6. 验收门槛逐项解释
| Version | Candidate | Avg Cash | Max Fold Cash | Trade Ratio | Failed Checks |
| --- | --- | --- | --- | --- | --- |
| rebuilt pullback candidate | False | 97.77% | 99.28% | 0.41 | provider 覆盖不是完整 PIT provider; 正收益 distinct year 数不足; qualified valid year 数不足; yearly expectancy 改善年份不足; 相对 breakout core 的收益/覆盖改善年份不足; 平均现金比例超过 95%; 至少一个 fold 现金比例超过 97%; 交易数低于原 pullback baseline 的 60%; 至少一个 fold 交易数少于 40; stop_loss + time_stop 占比没有下降 15%; 年度收益集中度超过 45% |
| strong-trend candidate | False | 97.77% | 99.28% | 0.41 | provider 覆盖不是完整 PIT provider; 正收益 distinct year 数不足; qualified valid year 数不足; yearly expectancy 改善年份不足; 相对 breakout core 的收益/覆盖改善年份不足; 平均现金比例超过 95%; 至少一个 fold 现金比例超过 97%; 交易数低于原 pullback baseline 的 60%; 至少一个 fold 交易数少于 40; stop_loss + time_stop 占比没有下降 15%; 年度收益集中度超过 45% |

验收解释：
- 现金门槛失败：平均现金 `97.77%`，高于 95%；最大 fold 现金 `99.28%`，高于 97%。
- 覆盖门槛失败：rebuilt 总交易数 `117`，只有原 pullback baseline 的 `40.62%`。
- 期望改善不足：expectancy 改善年份 `2`，低于要求的 4 年。
- 风险结构没有改善：stop_loss + time_stop 占比变化为 `-0.95%`，没有达到至少下降 15% 的要求。
- 年度收益集中度 `65.32%`，高于 45%，说明少数年份贡献过高。

## 7. 对需求问题的逐项回答
- PIT universe 构建成功，并已替代静态 `2025-12-31` universe 作为交易资格来源；但行情 provider 尚未完全替换为 Explore7 PIT provider，所以策略结论仍是 coverage-limited diagnostic。
- 旧 pullback 在 PIT universe 下没有稳定正贡献；原始 pullback baseline 只有 1/5 个 positive folds，2019-2024 distinct-year 表现也不稳定。
- `strong_trend_continuation` 没有稳定正 expectancy，不能进入 future final test。
- `weak_volume_rebound` 应继续剔除或单独重写；当前 diagnostic 回放显示其大样本下仍有明显负贡献。
- `breakdown_repair` 不应直接进入默认交易。它有阶段性收益，但风险和年份稳定性不合格，必须作为独立子系统研究。
- rebuilt pullback 的表观改善主要来自更少交易和更高现金，不是更高质量的 pullback alpha。
- 本轮不存在可等待 future final test 的候选版本。

## 8. 下一步
- 第一优先级是补齐 `Explore7/data/qlib/cn_data_pit`，使 provider 覆盖 PIT daily membership，而不是继续调 pullback 阈值。
- provider 补齐后必须重跑 `audit-pit-data -> run-walk-forward -> report`；只有当 `coverage_limited_diagnostic=False` 时，策略结果才可进入候选讨论。
- 如果补齐 provider 后 strong-trend 仍失败，应暂停默认 pullback，转向 breakout coverage 或 breakdown-repair 独立规则研究。
