# 12A6 C0 本地 Survival Episode 审计报告

## 结论

本轮 12A6 审计支持把 C0 事件构造成一个独立的 `survival episode` 目标，而不是重构 big winner episode registry。最终决策为 `12A6_survival_threshold_candidates_supported`，可以进入下一步 `requirement_12a7_c0_survival_meta_label_feasibility.md`。

被选中的主阈值是 `survival_U0.10_L0.20_H120`：从次日开盘进入后，在 120 个交易 session 内，优先触达 +10% 上障碍，同时没有先触达 -20% 下障碍。这个定义在 train 和 robustness split 上都成立，但 validation 明显弱一些，因此它更适合作为 survival meta-label 的候选目标，而不是直接解释为可交易收益策略。

更强的高门槛候选是 `survival_U0.30_L0.20_H80`。它在 robustness 上仍然通过，但命中率只有 28.3%，且 validation 只有 13.8%，因此更适合作为强 survival / acceleration 诊断，而不是主目标。

## 样本与可执行性

本报告的样本是一行一个 12A2 C0 canonical event，不是 episode-collapse 后的 big winner registry。`source_scope_id` 是 12A6 派生字段 `12A2_C0_primary_canonical_union`。

| 维度 | 值 | 事件数 | 占比 |
|:--|:--|--:|--:|
| split | train | 14560 | 50.7% |
| split | validation | 6860 | 23.9% |
| split | robustness | 7271 | 25.3% |
| regime | risk_on | 15113 | 52.7% |
| regime | transition | 7435 | 25.9% |
| regime | risk_off | 6143 | 21.4% |
| board | main_board | 22797 | 79.5% |
| board | chinext | 5894 | 20.5% |
| family | B5 | 10887 | 37.9% |
| family | B1 | 4570 | 15.9% |
| family | B8 | 3771 | 13.1% |
| family | B3 | 3508 | 12.2% |
| family | B2 | 3143 | 11.0% |
| family | B6 | 2443 | 8.5% |
| family | B4 | 369 | 1.3% |

入口可执行性没有阻断：28691 个 C0 event 中，`entry_status=ok` 为 28691，`trade_open_pit_membership_status=pass` 为 28691。缺价格文件、开盘价缺失、trade-open 日期/位置不匹配、PIT membership 缺失或不可执行均为 0。这个结果很关键：后续 survival 统计不是由 entry 过滤造成的幸存者偏差。

## 主 Survival 阈值

主候选 `U=+10%, L=-20%, H=120` 的核心读数如下。

| split | event_n | complete_n | upper_first | lower_first | neutral | median upper days | median lower days | expected_R proxy | time-penalized R | true survivor killed by lower |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| all | 28691 | 28679 | 64.3% | 27.3% | 8.4% | 14 | 36 | 0.0218 | 0.0056 | 7.6% |
| train | 14560 | 14560 | 65.5% | 27.8% | 6.7% | 12 | 33 | 0.0256 | 0.0071 | 7.5% |
| validation | 6860 | 6860 | 54.6% | 34.0% | 11.5% | 15 | 38 | -0.1013 | -0.0253 | 7.7% |
| robustness | 7271 | 7259 | 71.0% | 19.9% | 9.1% | 16 | 39 | 0.1306 | 0.0317 | 7.7% |

核心 insight：+10% 是一个很容易被 C0 后续波动触达的 survival upper barrier，-20% 则给出了足够宽的下行容忍度，使得主标签更像“事件后还能活过回撤并继续上冲”，而不是“短期止损交易”。这解释了为什么 upper_first 很高，但 expected_R proxy 并不高：这是 first-hit proxy，不是可成交收益。

validation 明显弱于 train 和 robustness：upper_first 54.6%，lower_first 34.0%，expected_R proxy 为 -0.1013。这说明该 survival 结构具有样本期差异，不能只看 overall 64.3% 的上穿率。后续 12A7 如果要把它做成 meta-label，应该把 validation 的弱化当成重点泛化风险。

## 候选排序与阈值选择

train all-C0 中共有 56 个候选达到 selection eligibility，其中 upper barrier 大于等于 30% 的 strong 候选有 6 个。前 8 个 train eligible 候选如下。

| upper | lower | horizon | upper_first | lower_first | neutral | median upper days | expected_R proxy | time-penalized R | killed by lower |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0.10 | -0.20 | 120 | 65.5% | 27.8% | 6.7% | 12 | 0.0256 | 0.0071 | 7.5% |
| 0.10 | -0.20 | 80 | 62.2% | 24.4% | 13.4% | 11 | 0.0219 | 0.0063 | 4.3% |
| 0.10 | -0.15 | 120 | 59.8% | 37.1% | 3.2% | 11 | 0.0181 | 0.0052 | 15.6% |
| 0.10 | -0.20 | 60 | 58.8% | 21.5% | 19.7% | 10 | 0.0116 | 0.0035 | 2.9% |
| 0.10 | -0.15 | 80 | 57.9% | 34.9% | 7.2% | 10 | 0.0176 | 0.0053 | 10.9% |
| 0.10 | -0.15 | 60 | 55.7% | 32.8% | 11.5% | 9 | 0.0092 | 0.0029 | 8.0% |
| 0.15 | -0.20 | 120 | 54.4% | 34.3% | 11.3% | 21 | 0.0360 | 0.0077 | 8.7% |
| 0.10 | -0.20 | 40 | 53.5% | 16.1% | 30.4% | 9 | 0.0152 | 0.0048 | 1.6% |

排序没有把 raw expected_R proxy 放在第一位，而是优先 upper_first、time-to-upper、lower_first 和 killed-by-lower。这个选择是合理的：如果直接按 raw expected_R 排序，会偏向极窄 lower barrier 或极端组合，弱化 survival label 的稳定性。

## Horizon 形态

`U=+10%, L=-20%` 的 upper_first 随 horizon 增加持续上升，train 从 10d 的 29.8% 增至 120d 的 65.5%，robustness 从 27.4% 增至 71.0%。这说明 C0 survival 不是非常短的 10-20d 信号，而是一个需要更长观察窗才能展开的 episode。

| split | horizon | complete_n | upper_first | lower_first | median upper days | p75 upper days | plateau cohort n | plateau upper_first | next increment | plateau flag |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| train | 10 | 14560 | 29.8% | 3.3% | 4 | 7 | 14560 | 29.8% | 12.4% | False |
| train | 20 | 14560 | 42.2% | 8.6% | 6 | 12 | 14560 | 42.2% | 11.3% | False |
| train | 40 | 14560 | 53.5% | 16.1% | 9 | 18 | 14560 | 53.5% | 5.2% | False |
| train | 60 | 14560 | 58.8% | 21.5% | 10 | 23 | 14560 | 58.8% | 3.4% | False |
| train | 80 | 14560 | 62.2% | 24.4% | 11 | 26 | 14560 | 62.2% | 3.3% | False |
| train | 120 | 14560 | 65.5% | 27.8% | 12 | 30 | 14560 | 65.5% |  | False |
| robustness | 10 | 7271 | 27.4% | 1.8% | 4 | 7 | 7259 | 27.3% | 12.8% | False |
| robustness | 20 | 7271 | 40.1% | 4.6% | 6 | 12 | 7259 | 40.1% | 13.9% | False |
| robustness | 40 | 7271 | 54.1% | 10.2% | 10 | 21 | 7259 | 54.1% | 7.1% | False |
| robustness | 60 | 7271 | 61.3% | 13.9% | 13 | 28 | 7259 | 61.2% | 4.1% | False |
| robustness | 80 | 7271 | 65.4% | 16.8% | 14 | 33 | 7259 | 65.4% | 5.6% | False |
| robustness | 120 | 7259 | 71.0% | 19.9% | 16 | 39.75 | 7259 | 71.0% |  | False |

重要解释：120d 被选中不是因为 plateau 已经出现，而是因为在当前 grid 里它仍然提供更高 upper_first。也就是说，当前结果支持“至少到 120d survival episode 还在展开”，不支持“60d 已经充分饱和”的说法。

## Forward Path 分布

全样本 120d 的 MFE 中位数是 18.6%，p90 是 65.4%；MAE 中位数是 -17.1%，close return 中位数是 -3.5%。这组数字解释了为什么需要使用 triple-barrier first-hit，而不是直接用 horizon close return：路径中有大量上冲，但最终收盘收益不一定保留。

| split | horizon | complete_n | MFE p50 | MFE p90 | MAE p50 | MAE p90 | close return p50 | close return p90 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| all | 20 | 28691 | 7.5% | 26.2% | -7.1% | -1.4% | -1.2% | 15.9% |
| all | 60 | 28691 | 12.9% | 45.5% | -12.5% | -2.3% | -3.0% | 25.9% |
| all | 120 | 28679 | 18.6% | 65.4% | -17.1% | -3.4% | -3.5% | 36.3% |
| train | 20 | 14560 | 8.2% | 27.3% | -7.7% | -1.5% | -1.3% | 17.0% |
| train | 60 | 14560 | 13.7% | 47.9% | -13.5% | -2.7% | -4.0% | 27.0% |
| train | 120 | 14560 | 20.0% | 69.0% | -18.3% | -4.0% | -4.6% | 38.2% |
| validation | 20 | 6860 | 6.3% | 20.5% | -7.5% | -1.5% | -2.2% | 11.7% |
| validation | 60 | 6860 | 9.9% | 32.1% | -13.7% | -2.7% | -4.8% | 17.4% |
| validation | 120 | 6860 | 13.1% | 44.1% | -19.5% | -4.4% | -7.9% | 20.4% |
| robustness | 20 | 7271 | 7.7% | 29.5% | -5.8% | -1.0% | 0.1% | 17.1% |
| robustness | 60 | 7271 | 14.7% | 51.8% | -9.7% | -1.6% | 0.8% | 30.9% |
| robustness | 120 | 7259 | 22.4% | 77.7% | -12.8% | -2.1% | 2.9% | 47.3% |

insight：validation 的 MFE 明显低、MAE 更深、close return 更弱，是主候选最大的外推风险。robustness 则更强，说明这个目标不是单调劣化，而是对市场阶段敏感。

## Pre-success MAE 与 Lower Barrier 选择

对最终会触达 +10% 的事件，触达前的 MAE 中位数约 -4.9%，p25 约 -10.7%，p90 约 -0.7%。这说明许多成功 survival episode 在成功前仍会经历明显回撤；如果 lower barrier 过紧，会把大量真实 survivor 提前杀掉。

| split | upper touch n | pre-success MAE p25 | p50 | p75 | p90 | p95 | killed by -10 | killed by -15 | killed by -20 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| all | 19950 | -10.7% | -4.9% | -1.9% | -0.7% | -0.3% | 27.3% | 15.1% | 7.6% |
| train | 10310 | -11.2% | -5.1% | -2.0% | -0.7% | -0.3% | 28.7% | 15.6% | 7.5% |
| validation | 4057 | -10.0% | -4.7% | -1.8% | -0.7% | -0.3% | 25.1% | 13.8% | 7.7% |
| robustness | 5583 | -10.4% | -4.8% | -1.9% | -0.7% | -0.3% | 26.4% | 15.0% | 7.7% |

lower=-20% 的选择有统计依据：-10% 会杀掉约 27.3% 的最终 +10% survivor，-15% 仍会杀掉 15.1%，而 -20% 降至 7.6%。所以这里的 -20% 不是“拍脑袋放宽止损”，而是为了保留 C0 后续 survival path 中真实存在的先回撤后上冲形态。

## Regime、Board 与 Family 稳定性

robustness split 中，主候选在 risk_on、transition、risk_off 都保持可用，但强弱排序并不符合“risk_on 必然更好”的直觉。risk_off 的 upper_first 最高，为 81.0%，lower_first 最低，为 11.9%；risk_on 的 upper_first 为 67.2%，lower_first 为 22.9%。

| slice | event_n | complete_n | upper_first | lower_first | neutral | median upper days | expected_R proxy | killed by lower |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| regime_risk_on | 4659 | 4658 | 67.2% | 22.9% | 9.9% | 15.5 | 0.0785 | 8.1% |
| regime_transition | 1385 | 1374 | 75.0% | 16.6% | 8.4% | 21 | 0.1854 | 9.0% |
| regime_risk_off | 1227 | 1227 | 81.0% | 11.9% | 7.1% | 16 | 0.2668 | 4.8% |
| board_main_board | 5727 | 5720 | 71.6% | 17.4% | 11.0% | 19 | 0.1534 | 5.8% |
| board_chinext | 1544 | 1539 | 68.8% | 28.9% | 2.3% | 9 | 0.0455 | 14.3% |

board 层面，创业板更快触达 upper，median upper days 为 9，但 lower_first 也更高，达到 28.9%，true survivor killed by lower 为 14.3%。主板更慢，median upper days 为 19，但 lower-first 风险更低。后续建模时，board 不是简单的控制变量，应该作为路径形态差异的重要解释变量。

family 切片只作为 diagnostic，不参与 selected candidate gate。B4 只有 369 个事件，统计不适合和大样本 family 同等参与选择。

| family slice | event_n | upper_first | lower_first | neutral | expected_R proxy | killed by lower |
|:--|--:|--:|--:|--:|--:|--:|
| primary_family_B1 | 4570 | 64.7% | 27.3% | 8.0% | 0.0254 | 7.0% |
| primary_family_B2 | 3143 | 63.8% | 23.9% | 12.3% | 0.0429 | 5.1% |
| primary_family_B3 | 3508 | 64.5% | 27.0% | 8.5% | 0.0237 | 7.9% |
| primary_family_B4 | 369 | 65.3% | 33.1% | 1.6% | -0.0101 | 11.7% |
| primary_family_B5 | 10887 | 64.0% | 27.7% | 8.3% | 0.0151 | 8.3% |
| primary_family_B6 | 2443 | 64.4% | 26.7% | 9.0% | 0.0343 | 7.7% |
| primary_family_B8 | 3771 | 64.7% | 28.9% | 6.5% | 0.0126 | 7.5% |

insight：family 间 upper_first 非常接近，大多在 63.8%-65.3% 区间；差异主要体现在 lower_first、neutral 和 expected_R proxy。也就是说 survival episode 的核心“能否上穿 +10%”不是由单一 family 独占，而是 C0 作为事件骨架整体带来的路径属性。

## Big-winner 富集

survival episode 与 big winner registry 是两件事，但 survival upper-first 事件应该富集 big winner。当前结果支持这个理论预期。

headline enrichment 使用 risk_on selected events 对 risk_on baseline，不使用 all-C0 baseline 稀释或虚高。06 registry 的 pre120_to_high 在 robustness split 中，selected upper-first overlap rate 为 18.0%，risk_on baseline 为 14.2%，富集倍数 1.267。06 low_to_high 在 robustness 中富集倍数 1.339。11a2 registry 的基数更小，但同样显示富集。

| registry | window | split | selected upper-first n | selected overlap rate | baseline n | baseline overlap rate | enrichment |
|:--|:--|:--|--:|--:|--:|--:|--:|
| 06_registry | low_to_high | all | 9572 | 9.4% | 15112 | 6.7% | 1.400 |
| 06_registry | low_to_high | train | 5314 | 10.0% | 8303 | 7.3% | 1.373 |
| 06_registry | low_to_high | validation | 1128 | 3.5% | 2151 | 2.0% | 1.690 |
| 06_registry | low_to_high | robustness | 3130 | 10.6% | 4658 | 7.9% | 1.339 |
| 06_registry | pre120_to_high | all | 9572 | 14.0% | 15112 | 10.6% | 1.320 |
| 06_registry | pre120_to_high | train | 5314 | 13.6% | 8303 | 10.6% | 1.283 |
| 06_registry | pre120_to_high | validation | 1128 | 4.7% | 2151 | 2.8% | 1.684 |
| 06_registry | pre120_to_high | robustness | 3130 | 18.0% | 4658 | 14.2% | 1.267 |
| 11a2_registry | pre120_to_high | all | 9572 | 1.1% | 15112 | 0.7% | 1.465 |
| 11a2_registry | pre120_to_high | train | 5314 | 0.6% | 8303 | 0.4% | 1.425 |
| 11a2_registry | pre120_to_high | validation | 1128 | 0.3% | 2151 | 0.1% | 1.907 |
| 11a2_registry | pre120_to_high | robustness | 3130 | 2.2% | 4658 | 1.6% | 1.388 |

关键 insight：富集倍数是正的，但绝对 overlap rate 仍然不高。以 06 pre120_to_high robustness 为例，selected upper-first 中 overlap rate 为 18.0%，意味着 survival episode 不是 big winner episode 的替代品。它更像一个更高召回、更高样本量的中间目标：在其中 big winner 更密集，但多数 survival 仍不是 big winner。

## Late-stage 诊断

late-stage 特征只用于 readout，不改变 label。特征口径是 qfq close-observed 的 EMA/rolling readout，policy status 为 `pass`。

robustness split 中，near-high 类型并没有明显削弱 survival：near_60d_high 的 upper_first 为 71.7%，near_120d_high 为 71.0%。但 extended_20d、extended_60d 和 late_stage_composite 的 lower_first 明显抬升，分别为 28.1%、31.5%、30.2%。

| late-stage bucket | event_n | upper_first | lower_first | neutral | expected_R proxy | bigwinner enrichment |
|:--|--:|--:|--:|--:|--:|--:|
| near_60d_high | 3330 | 71.7% | 18.9% | 9.2% | 0.142 | 1.217 |
| near_120d_high | 3133 | 71.0% | 20.5% | 8.4% | 0.124 | 1.253 |
| extended_20d | 1150 | 69.7% | 28.1% | 2.2% | 0.061 | 1.113 |
| extended_60d | 818 | 66.3% | 31.5% | 2.0% | 0.009 | 1.193 |
| late_stage_composite | 748 | 67.9% | 30.2% | 1.7% | 0.033 | 1.133 |

insight：接近阶段高点本身不是失败信号；真正更危险的是“已经明显 extended”。这符合主升浪后期的直觉：靠近高点可能代表趋势强，但过度拉伸后，虽然仍可能继续上穿 +10%，但先触达 lower barrier 的风险也显著提高。

## Event 重叠密度

C0 事件不是彼此独立的稀疏事件。全样本中，同一 instrument 过去 20d 内已有 C0 的比例为 40.3%，平均 survival window 与其他 C0 survival window 重叠 5.83 个，p95 为 9 个。

| scope | split | event_n | prior C0 10d | prior C0 20d | overlap mean | overlap p95 |
|:--|:--|--:|--:|--:|--:|--:|
| all_c0 | all | 28691 | 7.2% | 40.3% | 5.83 | 9 |
| all_c0 | train | 14560 | 7.3% | 40.2% | 5.90 | 10 |
| all_c0 | validation | 6860 | 7.0% | 39.3% | 5.84 | 9 |
| all_c0 | robustness | 7271 | 7.3% | 41.2% | 5.66 | 9 |

这个密度会影响后续建模：如果把每个 C0 survival event 当作完全独立样本，模型评估会过于乐观。12A7 至少需要考虑 instrument-level clustering、time split、overlap-aware sample weighting 或 purging。

## 强候选 `U=+30%, L=-20%, H=80`

强候选在 train/robustness 上可用，但它的含义不同：它更像强上冲事件，而不是普适 survival target。

| split | event_n | upper_first | lower_first | neutral | median upper days | expected_R proxy | killed by lower |
|:--|--:|--:|--:|--:|--:|--:|--:|
| all | 28691 | 24.2% | 31.8% | 44.1% | 33 | 0.0311 | 4.4% |
| train | 14560 | 27.0% | 33.9% | 39.2% | 33 | 0.0478 | 4.1% |
| validation | 6860 | 13.8% | 38.0% | 48.2% | 35 | -0.2078 | 6.0% |
| robustness | 7271 | 28.3% | 21.7% | 50.0% | 33 | 0.2231 | 4.3% |

insight：+30% 的 upper_first 低很多，neutral 高很多，说明它不是 C0 的基础 survival 定义，而是更强的 post-C0 continuation 子集。它适合在 12A7 中作为 secondary target 或 high-conviction calibration，不适合作为主 meta-label 的唯一目标。

## 风险与下一步

1. 主结论是支持 survival episode，而不是支持一个可直接交易的收益策略。`expected_r_multiple_proxy` 是 first-hit proxy，没有处理涨跌停不可成交、滑点、成交量约束和 time-to-hit 成本。
2. validation split 明显弱于 train/robustness，是下一步最重要的泛化风险。12A7 不应该只报告 all 或 robustness 的强结果。
3. `U=+10%, L=-20%, H=120` 的 lower barrier 有 pre-success MAE 支撑。把 lower 改成 -10% 或 -15% 会杀掉大量最终 survivor。
4. big winner 在 survival episode 中富集，但绝对比例仍低；survival episode 是更宽的中间监督目标，不是 big winner registry 替代品。
5. event overlap 密度高，后续模型评估必须处理同一 instrument 的重叠事件，否则 precision/recall 会被相关样本放大。
6. family slice 中 B4 只有 369 个事件，只能 diagnostic-only。当前实现没有 B7 slice，实际 family 是 B1、B2、B3、B4、B5、B6、B8。
