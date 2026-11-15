# EP34 早期模型主池：全指标统计

统计日2026-11-13；观察区间2020-01-03至2026-10-16；价格版本截至2026-10-21。主池solo_BALANCED_COMPETE，对照solo_BROAD20_COMPETE。只汇总冻结历史产物，不训练、不修改标签。

## 覆盖、质量、负担全部标量（原字段）

所有rate/coverage及pre_gain字段为小数；new_all_lower/upper为把未知全部计错/计对的边界，不是置信区间。新增重复仍计入质量分母。父子不得相加。

| metric | early_model | momentum |
|---|---|---|
| run_id | solo_BALANCED_COMPETE | solo_BROAD20_COMPETE |
| parent_total | 4540 | 4540 |
| parent_covered | 1380 | 1440 |
| parent_missed | 3160 | 3100 |
| parent_coverage | 0.3040 | 0.3172 |
| parent_timely | 804 | 554 |
| parent_late | 576 | 886 |
| child_total | 458 | 458 |
| child_covered | 176 | 254 |
| child_missed | 282 | 204 |
| child_coverage | 0.3843 | 0.5546 |
| new_total | 1651 | 1648 |
| new_unknown | 23 | 18 |
| new_evaluable | 1628 | 1630 |
| new_effective | 1313 | 1374 |
| new_effective_rate | 0.8065 | 0.8429 |
| new_all_lower | 0.7953 | 0.8337 |
| new_all_upper | 0.8092 | 0.8447 |
| new_repeat | 77 | 120 |
| new_week_median | 5.0000 | 5.0000 |
| new_week_p90 | 5.0000 | 5.0000 |
| new_week_max | 5 | 5 |
| pool_median | 20.0000 | 20.0000 |
| pool_p90 | 20.0000 | 20.0000 |
| pool_max | 20 | 20 |
| updates | 4787 | 4767 |
| workload_unknown_weeks | 5 | 5 |
| workload_supported_weeks | 343 | 343 |
| lag_p50 | 18.0000 | 23.0000 |
| lag_p90 | 56.1000 | 66.2000 |
| pre_gain_p50 | 0.1361 | 0.1817 |
| pre_gain_p90 | 0.3107 | 0.3967 |
| new_before_confirmation | 710 | 521 |
| new_on_confirmation | 200 | 260 |
| new_after_confirmation | 403 | 593 |
| left_scope_parents | 170 | 170 |
| left_scope_covered | 23 | 27 |
| timely_rate | 0.1771 | 0.1220 |
| late_rate | 0.1269 | 0.1952 |
| miss_rate | 0.6960 | 0.6828 |

## 完整新增/更新分类

SHORT_OR_UNCONFIRMED_PROCESS是短过程或未确认的合并类别，不能都解释为短暂反弹；UNKNOWN不计失败。UPDATE不并入唯一新增质量分母。

| candidate | kind | status | count | denominator | fraction |
|---|---|---|---|---|---|
| early_model | new_status | COVERED | 1313 | 1651 | 0.7953 |
| early_model | new_status | SHORT_OR_UNCONFIRMED_PROCESS | 167 | 1651 | 0.1012 |
| early_model | new_status | REPEAT | 77 | 1651 | 0.0466 |
| early_model | new_status | NO_PROCESS | 70 | 1651 | 0.0424 |
| early_model | new_status | UNKNOWN_PROCESS | 12 | 1651 | 0.0073 |
| early_model | new_status | UNKNOWN_DATA_OR_CONTEXT | 6 | 1651 | 0.0036 |
| early_model | new_status | RIGHT_CONTEXT_UNKNOWN | 4 | 1651 | 0.0024 |
| early_model | new_status | NO_CURRENT_ALIGNMENT | 1 | 1651 | 0.0006 |
| early_model | new_status | DURATION_RIGHT_UNKNOWN | 1 | 1651 | 0.0006 |
| early_model | update_status | REPEAT | 2436 | 4787 | 0.5089 |
| early_model | update_status | NO_PRICE_EVIDENCE | 1400 | 4787 | 0.2925 |
| early_model | update_status | NO_PROCESS | 552 | 4787 | 0.1153 |
| early_model | update_status | SHORT_OR_UNCONFIRMED_PROCESS | 222 | 4787 | 0.0464 |
| early_model | update_status | COVERED | 122 | 4787 | 0.0255 |
| early_model | update_status | RIGHT_CONTEXT_UNKNOWN | 41 | 4787 | 0.0086 |
| early_model | update_status | UNKNOWN_PROCESS | 11 | 4787 | 0.0023 |
| early_model | update_status | NO_CURRENT_ALIGNMENT | 3 | 4787 | 0.0006 |
| momentum | new_status | COVERED | 1374 | 1648 | 0.8337 |
| momentum | new_status | REPEAT | 120 | 1648 | 0.0728 |
| momentum | new_status | SHORT_OR_UNCONFIRMED_PROCESS | 84 | 1648 | 0.0510 |
| momentum | new_status | NO_PROCESS | 50 | 1648 | 0.0303 |
| momentum | new_status | UNKNOWN_PROCESS | 8 | 1648 | 0.0049 |
| momentum | new_status | UNKNOWN_DATA_OR_CONTEXT | 7 | 1648 | 0.0042 |
| momentum | new_status | NO_CURRENT_ALIGNMENT | 2 | 1648 | 0.0012 |
| momentum | new_status | RIGHT_CONTEXT_UNKNOWN | 1 | 1648 | 0.0006 |
| momentum | new_status | DURATION_RIGHT_UNKNOWN | 1 | 1648 | 0.0006 |
| momentum | new_status | UNKNOWN_ENHANCEMENT | 1 | 1648 | 0.0006 |
| momentum | update_status | REPEAT | 2424 | 4767 | 0.5085 |
| momentum | update_status | NO_PRICE_EVIDENCE | 1422 | 4767 | 0.2983 |
| momentum | update_status | NO_PROCESS | 602 | 4767 | 0.1263 |
| momentum | update_status | COVERED | 130 | 4767 | 0.0273 |
| momentum | update_status | SHORT_OR_UNCONFIRMED_PROCESS | 120 | 4767 | 0.0252 |
| momentum | update_status | RIGHT_CONTEXT_UNKNOWN | 57 | 4767 | 0.0120 |
| momentum | update_status | UNKNOWN_PROCESS | 9 | 4767 | 0.0019 |
| momentum | update_status | NO_CURRENT_ALIGNMENT | 3 | 4767 | 0.0006 |

## 新增与更新的首次覆盖贡献

每个父/子过程分别去重。一次提示可能覆盖父过程并属于其增强，故父子贡献之和不等于有效提示数。

| candidate | process | source | covered | total |
|---|---|---|---|---|
| early_model | parent | NEW | 1301 | 4540 |
| early_model | parent | UPDATE | 79 | 4540 |
| early_model | child | NEW | 133 | 458 |
| early_model | child | UPDATE | 43 | 458 |
| momentum | parent | NEW | 1352 | 4540 |
| momentum | parent | UPDATE | 88 | 4540 |
| momentum | child | NEW | 212 | 458 |
| momentum | child | UPDATE | 42 | 458 |

## 发现时机与尾部

lag_days为相对事后参考起点的交易日差；pre_gain为提示前相对参考基准已有涨幅。confirmation_delay为提示后距过程确认的交易日数，max(0,确认日−提示日)，0包含当日或此前已确认。只统计有值的已覆盖过程，不给遗漏过程填零。

| candidate | process | group | metric | n | mean | p10 | p50 | p90 | p95 | maximum |
|---|---|---|---|---|---|---|---|---|---|---|
| early_model | parent | all_covered | lag_days | 1380 | 25.6457 | 5.0000 | 18.0000 | 56.1000 | 81.0000 | 232.0000 |
| early_model | parent | all_covered | pre_gain | 1380 | 0.1646 | 0.0566 | 0.1361 | 0.3107 | 0.3927 | 1.0709 |
| early_model | parent | all_covered | confirmation_delay | 1380 | 5.5094 | 0.0000 | 0.0000 | 15.0000 | 20.0000 | 64.0000 |
| early_model | parent | TIMELY | lag_days | 804 | 12.2537 | 5.0000 | 10.0000 | 23.0000 | 29.0000 | 61.0000 |
| early_model | parent | TIMELY | pre_gain | 804 | 0.1131 | 0.0445 | 0.1005 | 0.2006 | 0.2312 | 0.5036 |
| early_model | parent | TIMELY | confirmation_delay | 804 | 9.0286 | 0.0000 | 10.0000 | 19.0000 | 20.0000 | 64.0000 |
| early_model | parent | LATE | lag_days | 576 | 44.3385 | 18.0000 | 34.0000 | 86.0000 | 109.2500 | 232.0000 |
| early_model | parent | LATE | pre_gain | 576 | 0.2364 | 0.1077 | 0.2114 | 0.3995 | 0.4683 | 1.0709 |
| early_model | parent | LATE | confirmation_delay | 576 | 0.5972 | 0.0000 | 0.0000 | 0.0000 | 5.0000 | 44.0000 |
| early_model | child | all_covered | lag_days | 176 | 11.8977 | 0.0000 | 10.0000 | 21.0000 | 28.2500 | 71.0000 |
| early_model | child | all_covered | pre_gain | 176 | 0.1290 | 0.0228 | 0.1243 | 0.2491 | 0.3098 | 0.5204 |
| early_model | child | all_covered | confirmation_delay | 176 | 9.2216 | 0.0000 | 10.0000 | 18.0000 | 20.0000 | 20.0000 |
| early_model | child | TIMELY | lag_days | 58 | 2.6724 | 0.0000 | 4.0000 | 5.0000 | 5.0000 | 5.0000 |
| early_model | child | TIMELY | pre_gain | 58 | 0.0503 | 0.0111 | 0.0373 | 0.1206 | 0.1253 | 0.1393 |
| early_model | child | TIMELY | confirmation_delay | 58 | 16.4828 | 14.7000 | 15.0000 | 20.0000 | 20.0000 | 20.0000 |
| early_model | child | LATE | lag_days | 118 | 16.4322 | 10.0000 | 15.0000 | 25.0000 | 30.4500 | 71.0000 |
| early_model | child | LATE | pre_gain | 118 | 0.1677 | 0.0868 | 0.1472 | 0.2836 | 0.3418 | 0.5204 |
| early_model | child | LATE | confirmation_delay | 118 | 5.6525 | 0.0000 | 5.0000 | 10.0000 | 10.0000 | 15.0000 |
| momentum | parent | all_covered | lag_days | 1440 | 31.5514 | 5.0000 | 23.0000 | 66.2000 | 88.0500 | 238.0000 |
| momentum | parent | all_covered | pre_gain | 1440 | 0.2107 | 0.0675 | 0.1817 | 0.3967 | 0.4774 | 0.9470 |
| momentum | parent | all_covered | confirmation_delay | 1440 | 3.4125 | 0.0000 | 0.0000 | 13.0000 | 15.0000 | 69.0000 |
| momentum | parent | TIMELY | lag_days | 554 | 13.0469 | 1.0000 | 12.0000 | 24.0000 | 31.0000 | 77.0000 |
| momentum | parent | TIMELY | pre_gain | 554 | 0.1279 | 0.0346 | 0.1159 | 0.2237 | 0.2846 | 0.6430 |
| momentum | parent | TIMELY | confirmation_delay | 554 | 8.1931 | 0.0000 | 5.0000 | 19.0000 | 20.0000 | 69.0000 |
| momentum | parent | LATE | lag_days | 886 | 43.1219 | 18.0000 | 35.0000 | 81.0000 | 99.7500 | 238.0000 |
| momentum | parent | LATE | pre_gain | 886 | 0.2625 | 0.1139 | 0.2338 | 0.4553 | 0.5314 | 0.9470 |
| momentum | parent | LATE | confirmation_delay | 886 | 0.4233 | 0.0000 | 0.0000 | 0.0000 | 5.0000 | 44.0000 |
| momentum | child | all_covered | lag_days | 254 | 15.2992 | 5.0000 | 14.5000 | 28.0000 | 34.3500 | 79.0000 |
| momentum | child | all_covered | pre_gain | 254 | 0.1620 | 0.0484 | 0.1504 | 0.2884 | 0.3340 | 0.4476 |
| momentum | child | all_covered | confirmation_delay | 254 | 6.6811 | 0.0000 | 5.0000 | 15.0000 | 17.0000 | 20.0000 |
| momentum | child | TIMELY | lag_days | 62 | 3.5968 | 0.0000 | 5.0000 | 5.0000 | 5.0000 | 5.0000 |
| momentum | child | TIMELY | pre_gain | 62 | 0.0621 | 0.0177 | 0.0592 | 0.1153 | 0.1266 | 0.1552 |
| momentum | child | TIMELY | confirmation_delay | 62 | 15.3710 | 13.1000 | 15.0000 | 19.0000 | 20.0000 | 20.0000 |
| momentum | child | LATE | lag_days | 192 | 19.0781 | 10.0000 | 15.0000 | 30.0000 | 38.9000 | 79.0000 |
| momentum | child | LATE | pre_gain | 192 | 0.1942 | 0.1122 | 0.1746 | 0.3082 | 0.3404 | 0.4476 |
| momentum | child | LATE | confirmation_delay | 192 | 3.8750 | 0.0000 | 5.0000 | 10.0000 | 10.0000 | 15.0000 |

## 工作负担分布

343个支持周；5个目录未知周排除分布但保留为未知。pool的sum为行业周占用，不是独立机会数量。

| candidate | metric | supported_weeks | sum | mean | median | p90 | p95 | maximum | zero_weeks |
|---|---|---|---|---|---|---|---|---|---|
| early_model | NEW | 343 | 1651.0000 | 4.8134 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 11 |
| early_model | UPDATE | 343 | 4787.0000 | 13.9563 | 15.0000 | 15.0000 | 15.0000 | 17.0000 | 13 |
| early_model | EXIT | 343 | 1631.0000 | 4.7551 | 5.0000 | 5.0000 | 7.0000 | 20.0000 | 21 |
| early_model | pool | 343 | 6438.0000 | 18.7697 | 20.0000 | 20.0000 | 20.0000 | 20.0000 | 11 |
| momentum | NEW | 343 | 1648.0000 | 4.8047 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 12 |
| momentum | UPDATE | 343 | 4767.0000 | 13.8980 | 15.0000 | 15.0000 | 15.0000 | 16.0000 | 13 |
| momentum | EXIT | 343 | 1628.0000 | 4.7464 | 5.0000 | 5.0000 | 7.0000 | 20.0000 | 21 |
| momentum | pool | 343 | 6415.0000 | 18.7026 | 20.0000 | 20.0000 | 20.0000 | 20.0000 | 11 |

## 入池后20/60/90/180交易日完整追踪

每期限均从所有唯一NEW出发；未知/未成熟/价格链缺口不填零。收益等权按提示事件统计，允许同一行业不同入池轮次；不是可交易组合收益。超额=行业简单收益−同期CSI_ALL简单收益。回撤是提示至期限内的最大峰谷回撤，负号越大越差；不扣交易成本。

| candidate | horizon | total | mature | immature | gap | excess_n | absolute_mean | absolute_median | absolute_p10 | absolute_p90 | excess_mean | excess_median | positive_fraction | outperform_fraction | positive_and_outperform | drawdown_mean | drawdown_median | drawdown_p10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| early_model | 20 | 1651 | 1604 | 25 | 22 | 1604 | 0.0071 | -0.0017 | -0.1085 | 0.1411 | 0.0000 | -0.0086 | 0.4913 | 0.4483 | 0.3734 | -0.0950 | -0.0835 | -0.1671 |
| early_model | 60 | 1651 | 1512 | 65 | 74 | 1512 | 0.0290 | 0.0088 | -0.1546 | 0.2557 | 0.0057 | -0.0049 | 0.5245 | 0.4802 | 0.4114 | -0.1592 | -0.1455 | -0.2599 |
| early_model | 90 | 1651 | 1449 | 95 | 107 | 1449 | 0.0493 | 0.0200 | -0.1697 | 0.3086 | 0.0143 | -0.0071 | 0.5431 | 0.4831 | 0.4141 | -0.1878 | -0.1730 | -0.3016 |
| early_model | 180 | 1651 | 1260 | 188 | 203 | 1260 | 0.0928 | 0.0531 | -0.2166 | 0.4377 | 0.0212 | -0.0134 | 0.5762 | 0.4746 | 0.4159 | -0.2466 | -0.2340 | -0.3801 |
| momentum | 20 | 1648 | 1603 | 25 | 20 | 1603 | 0.0050 | -0.0043 | -0.1184 | 0.1375 | -0.0019 | -0.0125 | 0.4860 | 0.4460 | 0.3849 | -0.1009 | -0.0868 | -0.1791 |
| momentum | 60 | 1648 | 1515 | 65 | 68 | 1515 | 0.0244 | 0.0011 | -0.1616 | 0.2372 | 0.0016 | -0.0150 | 0.5017 | 0.4455 | 0.3809 | -0.1694 | -0.1563 | -0.2786 |
| momentum | 90 | 1648 | 1453 | 95 | 100 | 1453 | 0.0481 | 0.0209 | -0.1856 | 0.3171 | 0.0138 | -0.0099 | 0.5382 | 0.4742 | 0.4081 | -0.1978 | -0.1828 | -0.3160 |
| momentum | 180 | 1648 | 1259 | 189 | 200 | 1259 | 0.1007 | 0.0523 | -0.2138 | 0.4397 | 0.0296 | -0.0117 | 0.5806 | 0.4742 | 0.4178 | -0.2519 | -0.2406 | -0.3812 |

## 按提示年份的质量

按NEW日期分年，与按过程起点分年的覆盖表分母不同。2026为不完整年度，质量截至数据末日后验评价。

| candidate | alert_year | new | mature | unknown | effective | effective_rate |
|---|---|---|---|---|---|---|
| early_model | 2020 | 259 | 259 | 0 | 204 | 0.7876 |
| early_model | 2021 | 235 | 227 | 8 | 194 | 0.8546 |
| early_model | 2022 | 195 | 189 | 6 | 159 | 0.8413 |
| early_model | 2023 | 250 | 250 | 0 | 190 | 0.7600 |
| early_model | 2024 | 251 | 251 | 0 | 183 | 0.7291 |
| early_model | 2025 | 263 | 263 | 0 | 232 | 0.8821 |
| early_model | 2026 | 198 | 189 | 9 | 151 | 0.7989 |
| momentum | 2020 | 259 | 258 | 1 | 215 | 0.8333 |
| momentum | 2021 | 235 | 231 | 4 | 194 | 0.8398 |
| momentum | 2022 | 194 | 186 | 8 | 151 | 0.8118 |
| momentum | 2023 | 250 | 250 | 0 | 211 | 0.8440 |
| momentum | 2024 | 250 | 249 | 1 | 204 | 0.8193 |
| momentum | 2025 | 261 | 261 | 0 | 230 | 0.8812 |
| momentum | 2026 | 199 | 195 | 4 | 169 | 0.8667 |

## 完整年度、此前状态及市场环境分层

year按过程起点年：2019的170个跨评价起点过程仍在分母中。PRIOR8_DOWN/UP是此前价格状态，不是基本面。市场分层为此前60日方向，不能据此证明行业独立alpha。

| run_id | stratification | stratum | processes | covered | timely | late | lag_p50 | pre_gain_p50 | coverage_rate | timely_rate | missed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| solo_BALANCED_COMPETE | prior_state | PRIOR8_DOWN | 3616 | 1053 | 594 | 459 | 18.0000 | 0.1372 | 0.2912 | 0.1643 | 2563 |
| solo_BALANCED_COMPETE | prior_state | PRIOR8_UP | 924 | 327 | 210 | 117 | 15.0000 | 0.1287 | 0.3539 | 0.2273 | 597 |
| solo_BALANCED_COMPETE | market_state | MARKET_PRIOR60_NONPOSITIVE | 2639 | 765 | 462 | 303 | 18.0000 | 0.1362 | 0.2899 | 0.1751 | 1874 |
| solo_BALANCED_COMPETE | market_state | MARKET_PRIOR60_POSITIVE | 1901 | 615 | 342 | 273 | 18.0000 | 0.1360 | 0.3235 | 0.1799 | 1286 |
| solo_BALANCED_COMPETE | year | 2019 | 170 | 23 | 3 | 20 | 33.0000 | 0.1947 | 0.1353 | 0.0176 | 147 |
| solo_BALANCED_COMPETE | year | 2020 | 496 | 201 | 119 | 82 | 18.0000 | 0.1199 | 0.4052 | 0.2399 | 295 |
| solo_BALANCED_COMPETE | year | 2021 | 459 | 190 | 120 | 70 | 17.5000 | 0.1197 | 0.4139 | 0.2614 | 269 |
| solo_BALANCED_COMPETE | year | 2022 | 724 | 211 | 122 | 89 | 20.0000 | 0.1575 | 0.2914 | 0.1685 | 513 |
| solo_BALANCED_COMPETE | year | 2023 | 618 | 163 | 116 | 47 | 14.0000 | 0.1068 | 0.2638 | 0.1877 | 455 |
| solo_BALANCED_COMPETE | year | 2024 | 755 | 197 | 114 | 83 | 15.0000 | 0.1802 | 0.2609 | 0.1510 | 558 |
| solo_BALANCED_COMPETE | year | 2025 | 835 | 270 | 123 | 147 | 24.5000 | 0.1604 | 0.3234 | 0.1473 | 565 |
| solo_BALANCED_COMPETE | year | 2026 | 483 | 125 | 87 | 38 | 14.0000 | 0.1375 | 0.2588 | 0.1801 | 358 |
| solo_BROAD20_COMPETE | prior_state | PRIOR8_DOWN | 3616 | 1068 | 343 | 725 | 25.0000 | 0.1960 | 0.2954 | 0.0949 | 2548 |
| solo_BROAD20_COMPETE | prior_state | PRIOR8_UP | 924 | 372 | 211 | 161 | 18.0000 | 0.1498 | 0.4026 | 0.2284 | 552 |
| solo_BROAD20_COMPETE | market_state | MARKET_PRIOR60_NONPOSITIVE | 2639 | 826 | 325 | 501 | 21.5000 | 0.1812 | 0.3130 | 0.1232 | 1813 |
| solo_BROAD20_COMPETE | market_state | MARKET_PRIOR60_POSITIVE | 1901 | 614 | 229 | 385 | 24.0000 | 0.1819 | 0.3230 | 0.1205 | 1287 |
| solo_BROAD20_COMPETE | year | 2019 | 170 | 27 | 1 | 26 | 39.0000 | 0.2578 | 0.1588 | 0.0059 | 143 |
| solo_BROAD20_COMPETE | year | 2020 | 496 | 205 | 96 | 109 | 20.0000 | 0.1410 | 0.4133 | 0.1935 | 291 |
| solo_BROAD20_COMPETE | year | 2021 | 459 | 186 | 69 | 117 | 22.0000 | 0.1705 | 0.4052 | 0.1503 | 273 |
| solo_BROAD20_COMPETE | year | 2022 | 724 | 206 | 68 | 138 | 25.0000 | 0.2101 | 0.2845 | 0.0939 | 518 |
| solo_BROAD20_COMPETE | year | 2023 | 618 | 188 | 83 | 105 | 20.0000 | 0.1287 | 0.3042 | 0.1343 | 430 |
| solo_BROAD20_COMPETE | year | 2024 | 755 | 214 | 95 | 119 | 19.0000 | 0.2265 | 0.2834 | 0.1258 | 541 |
| solo_BROAD20_COMPETE | year | 2025 | 835 | 276 | 78 | 198 | 33.0000 | 0.2381 | 0.3305 | 0.0934 | 559 |
| solo_BROAD20_COMPETE | year | 2026 | 483 | 138 | 64 | 74 | 20.0000 | 0.1839 | 0.2857 | 0.1325 | 345 |

## 过程右边界状态

right_open为数据右端过程未闭合，不等于无效；closed也不能直接等同于入池后失败。本汇总不新定义“中断率”。

| candidate | process | total | right_open | closed | covered_right_open |
|---|---|---|---|---|---|
| early_model | parent | 4540 | 177 | 4363 | 56 |
| early_model | child | 458 | 14 | 444 | 6 |
| momentum | parent | 4540 | 177 | 4363 | 55 |
| momentum | child | 458 | 14 | 444 | 9 |

## 同实际新增1615次的主对照

与独立池1651/1648次的数字分开；主池独立路径不能使用这里的1360作为其覆盖数。

| run_id | parent_total | parent_covered | parent_missed | parent_coverage | parent_timely | parent_late | child_total | child_covered | child_missed | child_coverage | new_total | new_unknown | new_evaluable | new_effective | new_effective_rate | new_all_lower | new_all_upper | new_repeat | new_week_median | new_week_p90 | new_week_max | pool_median | pool_p90 | pool_max | updates | workload_unknown_weeks | workload_supported_weeks | lag_p50 | lag_p90 | pre_gain_p50 | pre_gain_p90 | new_before_confirmation | new_on_confirmation | new_after_confirmation | left_scope_parents | left_scope_covered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q5_d0_BALANCED_COMPETE | 4540 | 1360 | 3180 | 0.2996 | 786 | 574 | 458 | 176 | 282 | 0.3843 | 1615 | 23 | 1592 | 1295 | 0.8134 | 0.8019 | 0.8161 | 73 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4748 | 5 | 343 | 18.0000 | 58.1000 | 0.1375 | 0.3126 | 692 | 202 | 401 | 170 | 23 |
| q5_d0_BROAD20_COMPETE | 4540 | 1421 | 3119 | 0.3130 | 533 | 888 | 458 | 254 | 204 | 0.5546 | 1615 | 18 | 1597 | 1357 | 0.8497 | 0.8402 | 0.8514 | 114 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4729 | 5 | 343 | 24.0000 | 68.0000 | 0.1847 | 0.3991 | 503 | 261 | 593 | 170 | 27 |

## 同新增比较的不确定性

差值为模型减动量；rate单位为小数，乘100为百分点。沿用登记13周时间块、2000次重采样；反复研究的历史不是独立样本外。

| comparison | metric | difference | lo95 | hi95 |
|---|---|---|---|---|
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | parent_coverage | -0.0134 | -0.0276 | 0.0016 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | timely_coverage | 0.0557 | 0.0427 | 0.0723 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | new_matching_rate | -0.0363 | -0.0653 | -0.0080 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | child_coverage | -0.1703 | -0.2251 | -0.1269 |

## 实际质量—覆盖取舍点

保留所有登记容量档实际点，不在曲线上插值声称精确同质量优势。

| run_id | parent_total | parent_covered | parent_missed | parent_coverage | parent_timely | parent_late | child_total | child_covered | child_missed | child_coverage | new_total | new_unknown | new_evaluable | new_effective | new_effective_rate | new_all_lower | new_all_upper | new_repeat | new_week_median | new_week_p90 | new_week_max | pool_median | pool_p90 | pool_max | updates | workload_unknown_weeks | workload_supported_weeks | lag_p50 | lag_p90 | pre_gain_p50 | pre_gain_p90 | new_before_confirmation | new_on_confirmation | new_after_confirmation | left_scope_parents | left_scope_covered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q1_d0_BALANCED_COMPETE | 4540 | 318 | 4222 | 0.0700 | 189 | 129 | 458 | 46 | 412 | 0.1004 | 331 | 4 | 327 | 285 | 0.8716 | 0.8610 | 0.8731 | 2 | 1.0000 | 1.0000 | 1 | 6.0000 | 8.0000 | 8 | 1667 | 5 | 343 | 15.5000 | 55.3000 | 0.1695 | 0.4001 | 152 | 47 | 86 | 170 | 5 |
| q1_d0_BROAD20_COMPETE | 4540 | 344 | 4196 | 0.0758 | 106 | 238 | 458 | 80 | 378 | 0.1747 | 331 | 4 | 327 | 312 | 0.9541 | 0.9426 | 0.9547 | 3 | 1.0000 | 1.0000 | 1 | 6.0000 | 8.0000 | 8 | 1632 | 5 | 343 | 27.0000 | 77.4000 | 0.2806 | 0.6012 | 96 | 66 | 150 | 170 | 6 |
| q3_d0_BALANCED_COMPETE | 4540 | 903 | 3637 | 0.1989 | 530 | 373 | 458 | 123 | 335 | 0.2686 | 980 | 15 | 965 | 808 | 0.8373 | 0.8245 | 0.8398 | 23 | 3.0000 | 3.0000 | 3 | 18.0000 | 20.0000 | 20 | 4624 | 5 | 343 | 17.0000 | 60.8000 | 0.1495 | 0.3331 | 429 | 125 | 254 | 170 | 15 |
| q3_d0_BROAD20_COMPETE | 4540 | 949 | 3591 | 0.2090 | 341 | 608 | 458 | 192 | 266 | 0.4192 | 980 | 9 | 971 | 874 | 0.9001 | 0.8918 | 0.9010 | 37 | 3.0000 | 3.0000 | 3 | 18.0000 | 20.0000 | 20 | 4608 | 5 | 343 | 25.0000 | 71.0000 | 0.2027 | 0.4552 | 305 | 170 | 399 | 170 | 17 |
| q5_d0_BALANCED_COMPETE | 4540 | 1360 | 3180 | 0.2996 | 786 | 574 | 458 | 176 | 282 | 0.3843 | 1615 | 23 | 1592 | 1295 | 0.8134 | 0.8019 | 0.8161 | 73 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4748 | 5 | 343 | 18.0000 | 58.1000 | 0.1375 | 0.3126 | 692 | 202 | 401 | 170 | 23 |
| q5_d0_BROAD20_COMPETE | 4540 | 1421 | 3119 | 0.3130 | 533 | 888 | 458 | 254 | 204 | 0.5546 | 1615 | 18 | 1597 | 1357 | 0.8497 | 0.8402 | 0.8514 | 114 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4729 | 5 | 343 | 24.0000 | 68.0000 | 0.1847 | 0.3991 | 503 | 261 | 593 | 170 | 27 |
| solo_BALANCED_COMPETE | 4540 | 1380 | 3160 | 0.3040 | 804 | 576 | 458 | 176 | 282 | 0.3843 | 1651 | 23 | 1628 | 1313 | 0.8065 | 0.7953 | 0.8092 | 77 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4787 | 5 | 343 | 18.0000 | 56.1000 | 0.1361 | 0.3107 | 710 | 200 | 403 | 170 | 23 |
| solo_BROAD20_COMPETE | 4540 | 1440 | 3100 | 0.3172 | 554 | 886 | 458 | 254 | 204 | 0.5546 | 1648 | 18 | 1630 | 1374 | 0.8429 | 0.8337 | 0.8447 | 120 | 5.0000 | 5.0000 | 5 | 20.0000 | 20.0000 | 20 | 4767 | 5 | 343 | 23.0000 | 66.2000 | 0.1817 | 0.3967 | 521 | 260 | 593 | 170 | 27 |

## 覆盖与解释边界

目录含574个分类制度内行业身份（SW2014 227、SW2021 347），不能相加解释为574个永续独立行业；既有覆盖审计中99个身份无有效价格。每候选107141条行业日期记录，343个支持期，另5个分类衔接未知周。最新347行业中83数据不足、20在池。

完整分母为4540父过程及458增强子过程，后者单列。现有口径衡量价格观察入口，不衡量订单/盈利改善。高匹配率不等于高覆盖率或提示后上涨率。父覆盖30.40%、及时覆盖17.71%、遗漏69.60%同时保留。

模型强项是相对动量更及时；尚有大量遗漏，增强弱于动量。四期限超额中位数均为负，不应将选择主池解释为证明投资超额收益。

持续性中断严格沿用既有短过程及阶段分类；目前没有一项独立冻结的“提示后中断率”总指标，不能临时挑选跌幅阈值计算后冒称原协议指标。任何进一步细分应单独登记口径。
