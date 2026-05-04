# Explore7 Pullback 子系统重建详细报告

## 1. 核心结论
- 未形成 `candidate_for_future_final_test`。所有 rebuilt/strong-trend 候选仍为 diagnostic-only。
- rebuilt pullback 被降级：改善主要来自交易数下降或现金比例升高。
- rebuilt/strong-trend 版本没有通过验收：正收益年份 `2/3`，qualified 年份 `3/4`，expectancy 改善年份 `4/4`，交易数比例 `0.39`，平均现金 `97.71%`。

## 2. 数据可信边界
- Universe point-in-time: `True`
- Industry point-in-time: `True`
- Provider coverage ratio: `100.00%`
- Coverage-limited diagnostic: `False`
- Historical result CSV used for calculation: `False`
- Provider used for this diagnostic replay: `Explore7/data/qlib/cn_data_pit`
- Missing PIT membership rows in provider: `0` / `439,140`

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
| breakdown-repair diagnostic | 3662 | 2/5 | -6.31% | -37.87% | -42.04% | 47.72% | 50.04% |
| breakout core baseline | 103 | 2/5 | 0.05% | -1.03% | -2.32% | 97.96% | 99.17% |
| original pullback baseline | 341 | 1/5 | -1.44% | -3.64% | -5.38% | 95.35% | 97.78% |
| rebuilt pullback candidate | 133 | 1/5 | -0.18% | -1.73% | -2.89% | 97.71% | 99.12% |
| strong-trend candidate | 133 | 1/5 | -0.18% | -1.73% | -2.89% | 97.71% | 99.12% |
| weak-volume diagnostic | 3061 | 2/5 | -8.96% | -32.47% | -33.90% | 60.24% | 62.89% |

解读：`pit_rebuilt_pullback_candidate` 与 `pit_strong_trend_pullback_candidate` 完全一致，说明第一版 rebuilt 只保留 strong-trend continuation。它的 fold return 均值略高于原 pullback baseline，但交易数从 288 降到 117，平均现金从 95.86% 升到 97.77%，因此改善主要是少交易和高现金，而不是 pullback 子规则质量显著提升。

### 3.1 Fold 明细
| Version | Fold | Trades | Return | Max DD | Avg Cash |
| --- | --- | --- | --- | --- | --- |
| breakout core baseline | WF1 | 34 | 0.07% | -2.32% | 96.88% |
| breakout core baseline | WF2 | 20 | 2.32% | -1.16% | 97.49% |
| breakout core baseline | WF3 | 8 | -0.34% | -1.17% | 99.17% |
| breakout core baseline | WF4 | 14 | -0.75% | -1.04% | 98.81% |
| breakout core baseline | WF5 | 27 | -1.03% | -1.77% | 97.47% |
| original pullback baseline | WF1 | 95 | -2.22% | -5.38% | 93.31% |
| original pullback baseline | WF2 | 74 | 2.41% | -3.60% | 94.11% |
| original pullback baseline | WF3 | 36 | -1.70% | -3.59% | 97.78% |
| original pullback baseline | WF4 | 37 | -2.04% | -2.57% | 97.73% |
| original pullback baseline | WF5 | 99 | -3.64% | -4.99% | 93.85% |
| strong-trend candidate | WF1 | 42 | -0.01% | -2.89% | 96.35% |
| strong-trend candidate | WF2 | 23 | 2.23% | -1.34% | 97.44% |
| strong-trend candidate | WF3 | 10 | -0.43% | -1.27% | 99.12% |
| strong-trend candidate | WF4 | 18 | -0.98% | -1.04% | 98.66% |
| strong-trend candidate | WF5 | 40 | -1.73% | -2.43% | 96.95% |
| weak-volume diagnostic | WF1 | 517 | 11.09% | -13.26% | 61.07% |
| weak-volume diagnostic | WF2 | 646 | -4.49% | -16.49% | 58.11% |
| weak-volume diagnostic | WF3 | 669 | -32.47% | -33.90% | 62.63% |
| weak-volume diagnostic | WF4 | 634 | -24.79% | -25.13% | 62.89% |
| weak-volume diagnostic | WF5 | 595 | 5.84% | -15.05% | 56.53% |
| breakdown-repair diagnostic | WF1 | 595 | 31.74% | -12.08% | 46.04% |
| breakdown-repair diagnostic | WF2 | 690 | 10.95% | -17.66% | 46.72% |
| breakdown-repair diagnostic | WF3 | 851 | -37.87% | -42.04% | 50.04% |
| breakdown-repair diagnostic | WF4 | 805 | -33.24% | -33.46% | 49.10% |
| breakdown-repair diagnostic | WF5 | 721 | -3.14% | -17.16% | 46.71% |
| rebuilt pullback candidate | WF1 | 42 | -0.01% | -2.89% | 96.35% |
| rebuilt pullback candidate | WF2 | 23 | 2.23% | -1.34% | 97.44% |
| rebuilt pullback candidate | WF3 | 10 | -0.43% | -1.27% | 99.12% |
| rebuilt pullback candidate | WF4 | 18 | -0.98% | -1.04% | 98.66% |
| rebuilt pullback candidate | WF5 | 40 | -1.73% | -2.43% | 96.95% |

## 4. Distinct Year 对照
| Version | Year | Trades | Return | Expectancy | Cash |
| --- | --- | --- | --- | --- | --- |
| breakout core baseline | 2019 | 20 | -1.02% | -806.47 | 97.10% |
| breakout core baseline | 2020 | 14 | 1.45% | 1339.64 | 96.81% |
| breakout core baseline | 2021 | 5 | 0.30% | 196.01 | 98.31% |
| breakout core baseline | 2022 | 3 | -0.44% | -1466.70 | 99.74% |
| breakout core baseline | 2023 | 11 | -0.31% | -280.40 | 97.88% |
| breakout core baseline | 2024 | 16 | -0.73% | -463.29 | 97.05% |
| original pullback baseline | 2019 | 43 | -1.99% | -645.13 | 93.95% |
| original pullback baseline | 2020 | 52 | 0.46% | 363.78 | 92.63% |
| original pullback baseline | 2021 | 22 | 0.24% | -352.24 | 96.22% |
| original pullback baseline | 2022 | 14 | -0.93% | -662.87 | 98.75% |
| original pullback baseline | 2023 | 23 | -1.14% | -492.74 | 96.75% |
| original pullback baseline | 2024 | 76 | -2.54% | -340.00 | 90.91% |
| rebuilt pullback candidate | 2019 | 25 | -0.86% | -644.26 | 96.29% |
| rebuilt pullback candidate | 2020 | 17 | 1.29% | 1062.10 | 96.64% |
| rebuilt pullback candidate | 2021 | 5 | 0.30% | 196.01 | 98.31% |
| rebuilt pullback candidate | 2022 | 5 | -0.53% | -1053.44 | 99.65% |
| rebuilt pullback candidate | 2023 | 13 | -0.46% | -349.20 | 97.69% |
| rebuilt pullback candidate | 2024 | 27 | -1.28% | -477.42 | 96.20% |

### 4.1 Rebuilt vs Original vs Breakout
| Year | Original return | Rebuilt return | Breakout return | Expectancy delta | Rebuilt/orig trades | Rebuilt cash |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | -1.99% | -0.86% | -1.02% | 0.87 | 25/43 | 96.29% |
| 2020 | 0.46% | 1.29% | 1.45% | 698.33 | 17/52 | 96.64% |
| 2021 | 0.24% | 0.30% | 0.30% | 548.25 | 5/22 | 98.31% |
| 2022 | -0.93% | -0.53% | -0.44% | -390.57 | 5/14 | 99.65% |
| 2023 | -1.14% | -0.46% | -0.31% | 143.55 | 13/23 | 97.69% |
| 2024 | -2.54% | -1.28% | -0.73% | -137.41 | 27/76 | 96.20% |

逐年看，rebuilt 的 yearly expectancy 只在 `4` 个 distinct years 优于原 pullback，相对 breakout core 同时满足收益不低且交易覆盖增加的年份只有 `1` 个；两项都没有达到验收要求。2021 和 2022 的 rebuilt 交易数尤其低，说明该版本没有提供稳定交易覆盖。

## 5. Pullback 三类拆分结果
### 5.1 分类覆盖
说明：下表按 fold-valid 视角统计，fold 之间有重叠年份，因此用于覆盖审计，不解释为去重样本数。
| Class | Candidate rows | PIT member count sum | Insufficient rows |
| --- | --- | --- | --- |
| breakdown_repair | 42,072 | 4,908 | 0 |
| weak_volume_rebound | 14,218 | 3,892 | 0 |
| unclassified_pullback | 8,257 | 2,031 | 0 |
| strong_trend_continuation | 120 | 105 | 24 |

### 5.2 分类回放表现
| Version | Class | Trades | Net PnL | Avg Expectancy | Positive class-years | Stop/Time |
| --- | --- | --- | --- | --- | --- | --- |
| breakdown-repair diagnostic | breakdown_repair | 3630 | -297611.87 | -7.85 | 4/10 | 46.00% |
| original pullback baseline | breakdown_repair | 72 | 453.38 | 629.36 | 6/10 | 41.36% |
| original pullback baseline | strong_trend_continuation | 30 | -11236.71 | -424.95 | 0/8 | 44.79% |
| original pullback baseline | unclassified_pullback | 32 | -14862.28 | -550.09 | 3/10 | 88.33% |
| original pullback baseline | weak_volume_rebound | 122 | -43163.49 | -534.89 | 2/10 | 65.50% |
| rebuilt pullback candidate | strong_trend_continuation | 33 | -12831.57 | -424.75 | 0/8 | 44.51% |
| strong-trend candidate | strong_trend_continuation | 33 | -12831.57 | -424.75 | 0/8 | 44.51% |
| weak-volume diagnostic | weak_volume_rebound | 3016 | -469014.23 | -115.81 | 4/10 | 53.16% |

分类解释：
- `strong_trend_continuation` 没有证明自己是可选候选。valid 覆盖中样本非常少，rebuilt/strong-trend 实际 pullback 交易只有 27 笔，合计 net PnL 为负，且 positive class-years 只有 1/8。
- `weak_volume_rebound` 在 diagnostic-only 回放中交易数充足，但合计 net PnL 明显为负，且 stop/time 占比高，继续支持 Explore4/5 对弱量反弹区域的风险判断。
- `breakdown_repair` diagnostic 的合计 net PnL 为正，但 fold 回撤和年度波动很大，2021-2022 明显转弱；它不能直接提升为默认 pullback，只能作为独立规则研究对象，且必须重新设计风险约束。
- `unclassified_pullback` 在原始 baseline 中 stop/time 占比极高，说明原 pullback 定义里仍有大量没有明确结构优势的噪声样本。

## 6. 验收门槛逐项解释
| Version | Candidate | Avg Cash | Max Fold Cash | Trade Ratio | Failed Checks |
| --- | --- | --- | --- | --- | --- |
| rebuilt pullback candidate | False | 97.71% | 99.12% | 0.39 | 正收益 distinct year 数不足; qualified valid year 数不足; 相对 breakout core 的收益/覆盖改善年份不足; 平均现金比例超过 95%; 至少一个 fold 现金比例超过 97%; 交易数低于原 pullback baseline 的 60%; 至少一个 fold 交易数少于 40; stop_loss + time_stop 占比没有下降 15%; 年度收益集中度超过 45% |
| strong-trend candidate | False | 97.71% | 99.12% | 0.39 | 正收益 distinct year 数不足; qualified valid year 数不足; 相对 breakout core 的收益/覆盖改善年份不足; 平均现金比例超过 95%; 至少一个 fold 现金比例超过 97%; 交易数低于原 pullback baseline 的 60%; 至少一个 fold 交易数少于 40; stop_loss + time_stop 占比没有下降 15%; 年度收益集中度超过 45% |

验收解释：
- 现金门槛失败：平均现金 `97.71%`，高于 95%；最大 fold 现金 `99.12%`，高于 97%。
- 覆盖门槛失败：rebuilt 总交易数 `133`，只有原 pullback baseline 的 `39.00%`。
- 期望改善不足：expectancy 改善年份 `4`，低于要求的 4 年。
- 风险结构没有改善：stop_loss + time_stop 占比变化为 `0.83%`，没有达到至少下降 15% 的要求。
- 年度收益集中度 `81.03%`，高于 45%，说明少数年份贡献过高。

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
