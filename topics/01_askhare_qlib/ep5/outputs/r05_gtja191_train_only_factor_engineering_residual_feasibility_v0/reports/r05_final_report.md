# EP5 R05 最终报告：GTJA191 Train-only Factor Engineering Residual Feasibility V0

## 1. 结论摘要

R05 没有支持 GTJA191 / Alpha191 在当前 EP5 short-horizon residual ranking 设定下继续推进。

最终决策为：

```text
final_decision = r05_factor_cluster_structure_not_viable_blocked
priority_rule  = rule_04
H10 quadrant   = absolute_false__relative_false
```

这不是样本不足导致的不可评价。H10 validation 有 `4,279` 个 complete events、`96` 个 decision observation dates，sample gate 通过；baseline 也可评价。失败来自两层：

1. 结构层：train-only 稳定筛选后形成 `54` 个 cluster，但只有 `50` 个 cluster 有 representative，`cluster_structure_ok = false`；同时 selected-week 集中度过高，H10 validation 的 top1 股票出现在 `53.54%` 的选股周，top5 股票覆盖 `97.98%` 的选股周。
2. 结果层：即使暂时忽略结构阻断，H10 validation 仍然是 absolute false、relative false、baseline false。mean matched delta 为正但很弱，median matched delta 为负，年度方向也不一致。

因此 R05 不能被解释为 long-only alpha，也不能被解释为稳定 residual edge。它最多说明：train-only 因子工程后仍存在一点均值层面的弱 residual 痕迹，但这条痕迹被负中位数、年度不一致、baseline median 失败、robustness 未确认和严重重复选股共同否定。

## 2. 实验边界

R05 遵守以下边界：

- 因子纳入、剔除、方向、稳定性筛选、聚类和 representative 选择只使用 train split。
- validation / robustness 只用于评价，不用于挑因子、调方向、调权重、调 top fraction 或调 horizon。
- primary horizon 固定为 H10；H5/H20 只作为 adjacent horizon check。
- 选股固定为每周 score top 20%。
- 打分使用 neutralized representative factor；cluster-level 等权，不使用 IC weighting、t-stat weighting、模型权重或动态权重。
- right-tail / big-winner readout 只作为诊断，不作为通过门。

validator 状态：

```text
validation_status = passed
passed_gates      = 22 / 22
```

## 3. 因子库实现与覆盖

| 项目 | 数值 |
|:--|--:|
| GTJA191 source factors | 191 |
| included factors | 125 |
| excluded factors | 66 |
| excluded_formula_implementation_failed | 65 |
| excluded_insufficient_cross_section_coverage | 1 |
| included factor max lookback median | 6 trading days |
| included factor max lookback p90 | 20 trading days |
| included factor max lookback max | 250 trading days |

此前布尔/数值运算映射失败的 `alpha055`、`alpha137`、`alpha182` 本次均已进入 included 集合：

| factor | status | train RankIC | neutralized train RankIC | stability selected | representative eligible | representative |
|:--|:--|--:|--:|:--:|:--:|:--:|
| alpha055 | included | -0.011849 | -0.008972 | true | true | true |
| alpha137 | included | -0.025972 | -0.025708 | true | true | true |
| alpha182 | included | 0.021557 | 0.008147 | true | true | true |

实现层已经不再是 R05 的主阻断项。真正的问题在于：可实现的 Alpha191 特征经过 train-only 工程后，仍没有形成稳定的 validation residual edge。

## 4. Train-only 稳定性筛选

R05 主训练 IC 口径为：

```text
raw_rank_factor_i × H10 matched_delta_label
```

最终 scoring 使用 neutralized representative，并要求 raw IC 与 neutralized audit IC 同号后才允许成为 representative。

| 项目 | 数值 |
|:--|--:|
| included factors | 125 |
| stability-selected factors | 89 |
| representative-eligible factors | 82 |
| raw / neutralized RankIC sign-agree factors | 107 |
| stability-selected negative direction | 49 |
| stability-selected positive direction | 40 |
| representative negative direction | 30 |
| representative positive direction | 20 |

稳定入选因子的 mean_train_rankIC 分布：

| percentile | mean_train_rankIC |
|:--|--:|
| min | -0.064836 |
| p10 | -0.023778 |
| p25 | -0.013854 |
| median | -0.006595 |
| p75 | 0.018909 |
| p90 | 0.040039 |
| max | 0.060290 |

代表因子中按绝对 train RankIC 排名前列的是：

| factor | direction | cluster | cluster_size | train RankIC | neutralized RankIC | same_sign_year_count |
|:--|--:|:--|--:|--:|--:|--:|
| alpha013 | -1 | alpha007 | 2 | -0.064836 | -0.034827 | 5 |
| alpha124 | -1 | alpha124 | 1 | -0.056753 | -0.032716 | 5 |
| alpha100 | -1 | alpha081 | 3 | -0.054639 | -0.027194 | 4 |
| alpha114 | 1 | alpha114 | 1 | 0.053182 | 0.037313 | 5 |
| alpha189 | 1 | alpha010 | 14 | 0.040615 | 0.022522 | 4 |
| alpha127 | -1 | alpha127 | 1 | -0.033270 | -0.013187 | 3 |
| alpha094 | -1 | alpha084 | 2 | -0.030128 | -0.013014 | 5 |
| alpha098 | 1 | alpha098 | 1 | 0.029313 | 0.017638 | 5 |
| alpha137 | -1 | alpha137 | 1 | -0.025972 | -0.025708 | 4 |
| alpha163 | 1 | alpha163 | 1 | 0.025357 | 0.023421 | 5 |

这个筛选不是“没有筛出东西”。相反，它筛出了 `89` 个 train-stable factors 和 `50` 个 representatives。但 validation 结果仍失败，说明 R04 的失败不只是 raw equal-weight 太粗；train-only 去噪、去冗余和中性化也没有把 Alpha191 变成稳定 residual signal。

## 5. 聚类结构与代表因子问题

| 项目 | 数值 |
|:--|--:|
| stability-selected factors | 89 |
| total clusters | 54 |
| representative clusters | 50 |
| representative factors | 50 |
| cluster_structure_ok | false |
| cluster block reason | no_representative_eligible_factor |

最大的 cluster 为 `alpha010`，包含 `14` 个 factor，占 stability-selected factors 的 `15.73%`，没有超过 `max_cluster_top_factor_share = 20%`。所以本次 cluster gate 不是因为单一大簇过大，而是因为存在没有合格 representative 的 cluster：

| cluster | size | representative count | representative eligible count |
|:--|--:|--:|--:|
| alpha122 | 2 | 0 | 0 |
| alpha037 | 1 | 0 | 0 |
| alpha102 | 1 | 0 | 0 |
| alpha166 | 1 | 0 | 0 |

这很重要：R05 的 cluster 工程不是简单减少因子数量，而是要求每个 train-stable cluster 都能找到方向一致、neutralized audit 也支持的代表。如果某些 cluster 虽然进入 stability-selected，但无法通过 representative eligibility，它们不能被静默丢弃后继续声称“完整特征库结构可用”。

## 6. Train 标签纯度与比较器一致性

train 标签 purge 通过：

| 项目 | 数值 |
|:--|--:|
| total_train_signal_date_count | 227 |
| train_label_purged_cross_split_signal_date_count | 3 |
| train_label_unpurged_signal_date_count | 224 |
| train_label_unpurged_signal_date_share | 98.68% |
| min required share | 90.00% |

train comparator consistency audit 显示，primary train label 与 audit comparator 的方向一致性并不完美：

| 范围 | sign agree |
|:--|--:|
| all included factors | 86 / 125 |
| stability-selected factors | 64 / 89 |
| representative factors | 42 / 50 |

解释：R05 的主训练口径可复现且 train-only，但 `42 / 50` 的 representative 在替代 train comparator 下同号，意味着仍有 `8 / 50` 个代表因子的训练方向对 comparator 口径敏感。这不是硬失败门，但它削弱了“训练方向非常稳”的解释。

## 7. 样本、eligible_count 与选股结构

R05 明确接受每周 eligible_count 小于 300 的统计代价，改用 complete event、observation date 和年度覆盖来判断 sample gate。本次结果显示 sample gate 通过，且 validation / robustness 的 cross-section 规模稳定。

| split | selected weeks | eligible min | eligible median | eligible max | selected median | active factor median |
|:--|--:|--:|--:|--:|--:|--:|
| train selected weeks | 86 | 175 | 229.5 | 269 | 46 | 50 |
| validation selected weeks | 99 | 203 | 226.0 | 252 | 46 | 50 |
| robustness selected weeks | 104 | 179 | 224.0 | 275 | 45 | 50 |

train 早期另有 `141` 个 signal dates 被 `blocked_insufficient_eligible_cross_section` 阻断，eligible median 为 `146`。这说明 R05 的有效训练窗口并不是完整日历 train，而是从可形成足够 weekly cross-section 后才实际参与选股。

H10 validation 的样本门：

| 指标 | 数值 |
|:--|--:|
| complete_event_count | 4,279 |
| complete_event_share | 94.86% |
| decision_observation_date_count | 96 |
| sample_status | pass |
| fallback_comparator_share | 0.00% |

因此不能把 R05 失败归因于“样本不可评价”。

## 8. 集中度与 active overlap

H10 validation 的 active overlap gate 通过，但 concentration gate 失败。

| split | horizon | top1 selected-week share | top5 selected-week share | median active overlap | p90 active overlap | effective independent event count |
|:--|:--|--:|--:|--:|--:|--:|
| train | H10 | 54.65% | 95.35% | 53.49% | 67.82% | 1,772 |
| validation | H10 | 53.54% | 97.98% | 56.17% | 67.05% | 3,749 |
| robustness | H10 | 47.12% | 97.12% | 54.55% | 67.39% | 5,867 |

validation top selected instruments：

| instrument | selected weeks | week share | H10 mean net | H10 mean matched delta |
|:--|--:|--:|--:|--:|
| SZ002460 | 53 | 53.54% | -2.0853% | -0.5248% |
| SH603799 | 51 | 51.52% | -2.9566% | -0.7142% |
| SZ002049 | 49 | 49.49% | -1.4280% | 0.2080% |
| SZ002142 | 49 | 49.49% | -2.2760% | -0.7426% |
| SH600188 | 47 | 47.47% | -2.0180% | -0.4331% |

这里的核心问题不是 active overlap 本身，而是 score 对少数股票的长期重复偏好过强。top5 股票覆盖接近全部选股周，说明 cluster-neutralized composite 仍然在横截面上形成了高度持久的“常驻名单”。这会让事件数看起来很多，但真正独立的信息来源较少，并且一旦常驻股票在 validation 中表现不好，整体结论会被显著拖累。

需要澄清的是，`top5_instrument_selected_week_share` 是 top5 股票的 selected-week 并集覆盖率，不是每只股票都在 95%-98% 的周里入选。validation 共有 `99` 个 selected weeks，其中这 5 只股票的出现数量分布为：

| 每周出现的 top5 股票数 | 周数 |
|:--|--:|
| 0 | 2 |
| 1 | 20 |
| 2 | 25 |
| 3 | 33 |
| 4 | 15 |
| 5 | 4 |

也就是说，validation 的集中度问题不是单一股票永久入选，而是一个 persistent candidate set 在绝大多数周里轮流或共同出现。

同一套 frozen R05 参数在 train 中也已经出现了类似结构。Train H10 的 headline 是：

| 指标 | train H10 |
|:--|--:|
| complete_event_count | 3,716 |
| decision_observation_date_count | 83 |
| mean_net_return | -0.2173% |
| median_net_return | -1.1925% |
| loss_rate | 56.57% |
| mean_matched_delta_return | 0.3192% |
| median_matched_delta_return | -0.7130% |
| mean_baseline_lift | 0.2929% |
| median_baseline_lift | 0.0538% |
| absolute_positive | false |
| relative_positive | false |
| baseline_lift_gate | true |

Train top selected instruments：

| instrument | selected weeks | week share | median rank | median score pct | industry | liquidity | beta | H10 mean net | H10 mean matched delta |
|:--|--:|--:|--:|--:|:--|:--|:--|--:|--:|
| SZ002371 | 47 | 54.65% | 16.0 | 93.58% | 电子 | q4 | high_beta | 0.6700% | 2.0177% |
| SH601318 | 46 | 53.49% | 14.5 | 94.01% | 非银金融 | q5 | low_beta | -2.3073% | -2.3736% |
| SH600845 | 45 | 52.33% | 16.0 | 92.15% | 计算机 | q2 | low_beta | 0.5966% | 0.0246% |
| SH601336 | 44 | 51.16% | 16.5 | 92.56% | 非银金融 | q3 | high_beta | -0.0354% | -0.9775% |
| SH603806 | 44 | 51.16% | 17.0 | 93.14% | 电力设备 | q2 | mid_beta | 3.4663% | 4.0030% |

这些股票在 train 中被反复选中，是因为它们长期落在 weekly cross-section 的前 6%-8% 左右。每周 eligible 中位数约 `229.5`，top20% 大约选 `46` 只；这些常驻票的 median rank 在 `14` 到 `17` 附近，因此自然反复进入 selected basket。

Train top5 常驻票的收益结构并不稳：

| group | events | mean net | median net | loss rate | mean matched delta | median matched delta |
|:--|--:|--:|--:|--:|--:|--:|
| train top5 常驻票 | 216 | 0.4388% | -1.5514% | 57.87% | 0.5051% | -1.1012% |
| train 全部 selected | 3,716 | -0.2173% | -1.1925% | 56.57% | 0.3192% | -0.7130% |

这说明 train 常驻票确实有更高的 mean matched delta，但 median matched delta 更差，loss rate 也更高。它不是稳定胜率或稳定中位数优势，而是少数好事件抬高均值。

从 score 构成看，train top5 常驻票主要被以下 representative factors 推高：

| factor | direction | train RankIC | target signed value | positive share | excess vs all train selected |
|:--|--:|--:|--:|--:|--:|
| alpha013 | -1 | -0.0648 | 0.4287 | 100.00% | 0.3101 |
| alpha124 | -1 | -0.0568 | 0.4195 | 96.46% | 0.3283 |
| alpha012 | 1 | 0.0232 | 0.3827 | 100.00% | 0.2440 |
| alpha114 | 1 | 0.0532 | 0.3781 | 97.35% | 0.2729 |
| alpha100 | -1 | -0.0546 | 0.3668 | 98.67% | 0.2086 |
| alpha189 | 1 | 0.0406 | 0.2843 | 89.82% | 0.1799 |

这些 driver 的共同含义大致是价量偏离、成交量相关性、日内 high-low range、收盘位置和价格/成交量协方差。换句话说，R05 train-only 工程学到的是一组可重复识别的价量形态；这些形态能把某些股票长期推到 score 前列，但在 train 内部已经没有稳定 median residual advantage。Validation 只是把这个问题进一步暴露出来。

## 9. H10 Validation 主证据

| 指标 | 数值 | gate 解读 |
|:--|--:|:--|
| complete_event_count | 4,279 | sample pass |
| decision_observation_date_count | 96 | sample pass |
| mean_net_return | -1.3245% | absolute fail |
| median_net_return | -1.6726% | absolute fail |
| p10_net_return | -9.4984% | tail risk high |
| loss_rate | 61.91% | absolute fail |
| mean_matched_delta_return | 0.1028% | weak positive mean |
| median_matched_delta_return | -0.3440% | relative fail |
| p10_matched_delta_return | -7.1162% | downside remains large |
| matched_loss_rate_delta | -7.1512% | relative loss-rate improves |
| mean_baseline_lift | 0.0582% | weak positive mean |
| median_baseline_lift | -0.1553% | baseline fail |
| fallback_comparator_share | 0.00% | comparator usable |
| absolute_positive | false | fail |
| relative_positive | false | fail |
| baseline_lift_gate | false | fail |
| multi_comparator_relative_status | unstable | fail |
| robustness_confirmed | false | fail |
| adjacent_horizon_clean | true | soft clean only |

H10 的均值 residual 为正，但中位数 residual 为负。这种形态意味着收益不是稳定排序，而是少数事件拉高均值。R05 的 primary target 是 residual ranking edge，不是 right-tail existence；所以 `mean_matched_delta_return > 0` 本身不能构成通过证据。

## 10. Horizon Shape

| split | horizon | mean net | median net | loss rate | mean matched delta | median matched delta | mean baseline lift | baseline gate | horizon pass |
|:--|:--|--:|--:|--:|--:|--:|--:|:--:|:--:|
| validation | H5 | -1.2076% | -1.5356% | 64.43% | 0.0483% | -0.2607% | 0.0087% | false | false |
| validation | H10 | -1.3245% | -1.6726% | 61.91% | 0.1028% | -0.3440% | 0.0582% | false | false |
| validation | H20 | -1.7756% | -2.5207% | 61.45% | 0.1092% | -0.7092% | 0.0103% | false | false |
| robustness | H5 | -0.6460% | -1.0967% | 61.85% | 0.0764% | -0.3353% | 0.0495% | true | false |
| robustness | H10 | -0.2318% | -0.8950% | 56.98% | 0.0086% | -0.5112% | -0.0049% | false | false |
| robustness | H20 | 0.6380% | -0.4371% | 52.23% | 0.0911% | -0.7112% | 0.0376% | true | false |

H5/H20 没有支持 H10。H20 robustness 的 mean net 为正，但 median net 仍为负，且 H10 primary validation 不通过，不能倒推出 H10 residual edge 成立。

## 11. 年度稳定性

H10 年度表现：

| split | year | complete events | decision dates | mean net | mean matched delta |
|:--|--:|--:|--:|--:|--:|
| train | 2020 | 1,407 | 34 | 0.7975% | 0.4234% |
| train | 2021 | 2,309 | 49 | -0.8357% | 0.2556% |
| validation | 2022 | 2,194 | 49 | -1.1952% | 0.2936% |
| validation | 2023 | 2,085 | 47 | -1.4605% | -0.0980% |
| robustness | 2024 | 2,137 | 51 | -0.4183% | -0.0094% |
| robustness | 2025 | 2,366 | 50 | -0.0634% | 0.0248% |

baseline lift 年度表现：

| split | year | selected mean | nonselected baseline mean | lift mean | lift median |
|:--|--:|--:|--:|--:|--:|
| validation | 2022 | -1.1517% | -1.3983% | 0.2466% | 0.0489% |
| validation | 2023 | -1.4837% | -1.3455% | -0.1382% | -0.2026% |
| robustness | 2024 | -0.2659% | -0.2451% | -0.0208% | 0.0790% |
| robustness | 2025 | -0.0451% | -0.0564% | 0.0113% | 0.0214% |

2022 的 residual mean 为正，但 2023 转负；robustness 2024 接近 0 且略负，2025 也只是微正。这不是稳定 edge 的年度形态。更直白地说，R05 没有把 R04 的“弱均值痕迹”转成跨年一致的排序优势。

## 12. Date-weighted 视角

Date-weighted H10：

| split | date-weighted net | date-weighted matched delta | date-weighted baseline lift | date count |
|:--|--:|--:|--:|--:|
| train | -0.1549% | 0.3161% | 0.2929% | 83 |
| validation | -1.3142% | 0.1042% | 0.0582% | 96 |
| robustness | -0.1566% | 0.0152% | -0.0049% | 101 |

date-weighted 后结论没有改变：validation residual 仍然只是弱正，robustness H10 residual 近乎消失，baseline lift 在 robustness H10 转为负。

## 13. Score bucket 读数

H10 validation score bucket 的 net return 没有形成单调排序：

| score bucket | count | mean net |
|:--|--:|--:|
| (0.0556, 0.0899] | 858 | -1.6080% |
| (0.0899, 0.106] | 817 | -1.1362% |
| (0.106, 0.127] | 859 | -1.4803% |
| (0.127, 0.157] | 880 | -0.9505% |
| (0.157, 0.322] | 865 | -1.4469% |

最高 score bucket 并不是最好的一组，且所有 bucket 的 H10 validation mean net 都为负。R05 的 composite 在 selected universe 内没有显示出可用的分层收益曲线。

H10 robustness 同样不单调：

| score bucket | count | mean net |
|:--|--:|--:|
| (0.0556, 0.0899] | 939 | -0.4022% |
| (0.0899, 0.106] | 934 | -0.0141% |
| (0.106, 0.127] | 893 | -0.5182% |
| (0.127, 0.157] | 921 | -0.1787% |
| (0.157, 0.322] | 816 | -0.0318% |

这支持一个判断：R05 的 score 更像是弱风格/持久名单排序，而不是稳定收益排序。

## 14. Market State 与 Beta 分解

H10 validation decomposition：

| market_state | beta_bucket | count | mean net |
|:--|:--|--:|--:|
| mixed | high_beta | 221 | -1.5319% |
| mixed | low_beta | 284 | -0.9761% |
| mixed | mid_beta | 296 | -1.8870% |
| risk_off | high_beta | 782 | -1.4296% |
| risk_off | low_beta | 918 | -1.3337% |
| risk_off | mid_beta | 921 | -1.1741% |
| risk_on | high_beta | 246 | -1.0730% |
| risk_on | low_beta | 314 | -1.5876% |
| risk_on | mid_beta | 297 | -1.0341% |

没有哪个 market_state / beta bucket 能自然解释为“主要可交易优势来源”。所有分组平均收益均为负，说明 R05 不是简单地在某个 beta regime 中被局部拖累，而是整体 long-only 口径失效。

## 15. Right-tail 诊断

| split | horizon | count | mean net | max net |
|:--|:--|--:|--:|--:|
| validation | H5 | 4,357 | -1.2076% | 30.7573% |
| validation | H10 | 4,279 | -1.3245% | 42.2414% |
| validation | H20 | 4,156 | -1.7756% | 85.1137% |
| robustness | H5 | 4,582 | -0.6460% | 46.0519% |
| robustness | H10 | 4,503 | -0.2318% | 49.8823% |
| robustness | H20 | 4,367 | 0.6380% | 60.9330% |

right tail 存在，但这不能救回 R05。原因是 R05 的目标不是证明“偶尔能选到大涨股票”，而是证明 fixed train-only composite 有稳定 residual ranking edge。当前结果显示：right tail 被大量负中位数和高 loss rate 抵消。

## 16. 与 R04 的直接对比

H10 validation 对比：

| 指标 | R04 raw equal-weight | R05 train-only engineered | 解读 |
|:--|--:|--:|:--|
| complete_event_count | 4,271 | 4,279 | 样本相近 |
| mean_net_return | -1.3210% | -1.3245% | 没有改善 |
| median_net_return | -1.8517% | -1.6726% | 中位数略改善但仍明显为负 |
| loss_rate | 61.20% | 61.91% | 略变差 |
| mean_matched_delta_return | 0.1332% | 0.1028% | R05 反而更弱 |
| median_matched_delta_return | -0.4001% | -0.3440% | 略改善但仍为负 |
| matched_loss_rate_delta | -9.0845% | -7.1512% | 仍改善，但幅度下降 |
| mean_baseline_lift | 0.0614% | 0.0582% | 基本持平 |
| median_baseline_lift | -0.1028% | -0.1553% | R05 更差 |
| absolute_positive | false | false | 未改善 |
| relative_positive | false | false | 未改善 |
| baseline_lift_gate | false | false | 未改善 |

R05 相比 R04 的增量主要在研究纪律和诊断清晰度，而不是收益结果：

- R05 证明了“仅仅把 Alpha191 做 train-only 稳定筛选、中性化和聚类”不足以把 R04 的 raw equal-weight 失败转成 pass。
- R05 把失败原因拆得更清楚：不是样本不足，不是 comparator 不可用，也不是公式实现失败；而是 residual edge 不稳定、median 不支持、年度不一致、baseline median 不支持，并伴随严重选股集中。
- R05 的 selected-week concentration 暴露了一个 R04 没有充分惩罚的问题：composite 可能长期重复选中少数股票，导致表面事件数多，但信息来源集中。

## 17. 必答问题

| 问题 | 回答 |
|:--|:--|
| 1. R05 是否真的只用了 train 做因子工程？ | 是。因子方向、稳定性筛选、cluster 和 representative 选择均来自 train；validator 通过，报告没有发现 train-only violation。 |
| 2. 原始 GTJA191 有多少因子 included？ | 125 / 191。 |
| 3. 稳定性筛选后保留多少因子？ | 89 个 stability-selected factors。 |
| 4. 聚类后保留多少 cluster？ | 54 个 total clusters，其中 50 个有 representative。 |
| 5. 每个 cluster 的代表因子如何选择？ | 在 train-only representative eligible 集合内，按 factor_quality_score、mean_train_rankIC、missing share 和 factor_id tie-break 选代表。 |
| 6. 因子方向是否全部来自 train-only RankIC？ | 是，direction_i 来自 train mean RankIC sign。 |
| 7. 中性化前后 score 分布是否变化显著？ | 中性化后可用 representative 为 50 个；raw/neutralized RankIC sign-agree 为 107 / 125，但 comparator consistency 只有 42 / 50 representatives 同号，说明方向仍有口径敏感性。 |
| 8. selected top20% 是否仍高度重复选择少数股票？ | 是。H10 validation top1 selected-week share 为 53.54%，top5 为 97.98%，concentration gate 失败。 |
| 9. H10 validation 是否通过 relative gate？ | 否。mean matched delta 为正，但 median matched delta 为 -0.3440%，年度 2023 为负，relative_positive = false。 |
| 10. H10 validation 是否跑赢 nonselected baseline？ | 不通过。mean baseline lift 为 0.0582%，但 median baseline lift 为 -0.1553%，2023 lift mean 为 -0.1382%，baseline_lift_gate = false。 |
| 11. 2022 和 2023 是否方向一致？ | 否。2022 H10 mean matched delta 为 0.2936%，2023 为 -0.0980%。 |
| 12. robustness 2024-2025 是否确认？ | 否。2024 H10 mean matched delta 为 -0.0094%，2025 仅 0.0248%；robustness_confirmed = false。 |
| 13. H5/H20 是否支持 H10？ | 否。validation H5/H20 horizon_pass 均为 false。 |
| 14. 结果是 long-only alpha、residual edge、style/beta exposure，还是 no support？ | 不是 long-only alpha，也不是稳定 residual edge。正式 final decision 是 cluster structure blocked；若只看表现证据，则是 no support。 |
| 15. R05 相比 R04 的增量来自哪里？ | 增量来自更严格的 train-only 工程和诊断，而不是收益改善。R05 明确证明工程化后仍不能通过 H10 residual gate。 |

## 18. Findings

1. `sample_status = pass`，所以这次不能再说“样本不够导致没法判断”。R05 已经在 accepted eligible_count < 300 的条件下形成了足够的 H10 validation events。
2. R05 的 factor engineering 有实际产出：125 个 included factors、89 个 train-stable factors、50 个 representatives。但这些结构产出没有转化成 validation pass。
3. Cluster structure gate 的失败是有意义的。4 个 cluster 没有合格 representative，说明“先筛稳定因子，再完整覆盖每个稳定 cluster”的结构约束没有满足。
4. Concentration 是非常强的负面证据。top5 selected-week share 接近 100%，意味着策略几乎每周都会在少数常驻股票里反复下注。
5. H10 residual mean 为正但 median 为负，是典型的“均值被少数事件拉动”形态，不是稳定 ranking edge。
6. 2022 有正 residual，2023 转负，2024 仍不确认；这破坏了 validation year consistency 和 robustness confirmation。
7. Baseline lift 也只有均值弱正，中位数和年度 2023 不支持，不能作为 selection lift 通过。
8. Score bucket 没有单调性，最高分桶并不最好；这直接削弱了 composite score 作为排序分数的可信度。
9. Right-tail 存在，但 right-tail 不等于 alpha。R05 的失败正是因为大赢家被高亏损率、负中位数和不稳定 residual 抵消。
10. 相比 R04，R05 没有改善核心指标。mean net 基本不变，mean matched delta 反而从 0.1332% 降到 0.1028%，baseline median 更差。

## 19. Insight

R05 的最重要信息不是“Alpha191 完全没有任何信号”，而是“Alpha191 在这个 EP5 设定下没有形成可冻结、可复现、可解释的 short-horizon residual ranking edge”。

train-only 工程做了三件正确的事：去掉明显不可实现或覆盖不足的因子；用 train RankIC 做稳定性筛选和方向冻结；用 complete-link cluster 避免高相关因子重复投票。但最终仍失败，说明问题更深：这些 Alpha191 价量结构在当前 PIT mcap500 mainboard universe、weekly close-observed signal、next-open execution、110bps cost、H10 exit 的组合下，主要留下的是弱均值偏移和重复名单，而不是可交易排序。

如果继续在 R05 内部调 top fraction、改 cluster threshold、按 validation 剔除常驻股票、挑 2022 表现好的因子或改 horizon，本质上会重新滑回 validation-driven alpha mining。按当前证据，R05 应该停止在 GTJA191 train-only composite 这条线上继续调参。

可接受的下一步只能是改变研究问题，而不是“修 R05”：

- 若仍研究 Alpha191，应转向新的 requirement，明确是 hedged / market-relative feasibility，并重新定义组合、对冲和风险约束。
- 若继续 short-horizon residual ranking，应考虑换 feature library 或引入完全不同的信息来源，而不是继续在 GTJA191 内部挖 validation 子集。
- 若研究 long-only alpha，R05 已经给出否定证据：当前 composite 的 absolute return、loss rate、baseline lift 和 robustness 都不支持部署。

## 20. Artifact 索引

核心证据文件：

- `audit/r05_factor_registry.csv`
- `audit/r05_factor_stability_selection_audit.csv`
- `audit/r05_factor_cluster_audit.csv`
- `audit/r05_selected_factor_manifest.csv`
- `audit/r05_train_comparator_consistency_audit.csv`
- `audit/r05_score_cross_section_audit.csv`
- `audit/r05_active_overlap_audit.csv`
- `metrics/r05_split_horizon_summary.csv`
- `metrics/r05_year_horizon_summary.csv`
- `metrics/r05_baseline_lift_summary.csv`
- `metrics/r05_score_bucket_readout.csv`
- `metrics/r05_decomposition_summary.csv`
- `metrics/r05_right_tail_readout.csv`
- `decision/r05_final_decision_inputs.csv`
- `decision/r05_final_decision_replay.csv`
- `manifests/r05_validation.json`
