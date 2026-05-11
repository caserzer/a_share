# Big Winner 前 60 天组合指标覆盖率搜索 v2

- 样本：845 个 canonical R01 primary big winner
- 覆盖定义：同一股票在 T-60 到 T-1 至少一天满足条件
- 密度定义：条件在 R01 PIT-executable eligible stock-days 上的日级触发比例；`window_and2` 的密度是近似参考，不等同于日级 seed 密度
- 搜索规模：312 个原子条件，155062 个组合/窗口条件

## 推荐的日级 seed-like 条件（覆盖 >=85% 中密度最低）

```text
money_ratio20_gt_1_0 AND money_ratio5_gt_2_0 AND rps5_gt_50
```

| metric | value |
|:--|--:|
| kind | and3 |
| coverage T-60..T-1 | 85.09% |
| covered events | 719 / 845 |
| coverage T-60..T0 | 85.21% |
| eligible-day density | 3.45% |
| median closest hit offset | -18.0 |
| median earliest hit offset | -42.0 |

## Split 覆盖

| split      |   event_count |   covered_pre60_excl_t0 |   coverage_pre60_excl_t0 |   covered_pre60_to_t0 |   coverage_pre60_to_t0 |
|:-----------|--------------:|------------------------:|-------------------------:|----------------------:|-----------------------:|
| robustness |           241 |                     210 |                 0.871369 |                   210 |               0.871369 |
| train      |           446 |                     384 |                 0.860987 |                   385 |               0.863229 |
| validation |           158 |                     125 |                 0.791139 |                   125 |               0.791139 |

## 覆盖 >=85% 的 Top 50 低密度条件

| condition                                                            | kind   |   n_terms |   coverage_pre60_excl_t0 |   covered_events_excl_t0 |   coverage_pre60_to_t0 |   eligible_day_density |   median_closest_hit_offset |   median_earliest_hit_offset |
|:---------------------------------------------------------------------|:-------|----------:|-------------------------:|-------------------------:|-----------------------:|-----------------------:|----------------------------:|-----------------------------:|
| money_ratio20_gt_1_0 AND money_ratio5_gt_2_0 AND rps5_gt_50          | and3   |         3 |                 0.850888 |                      719 |               0.852071 |              0.0345005 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps5_gt_50 AND vol_ratio20_gt_1_0            | and3   |         3 |                 0.850888 |                      719 |               0.852071 |              0.0345081 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps5_gt_50 AND vol_ratio10_gt_1_0            | and3   |         3 |                 0.853254 |                      721 |               0.854438 |              0.0345814 |                         -18 |                          -42 |
| money_ratio10_gt_1_0 AND money_ratio5_gt_2_0 AND rps5_gt_50          | and3   |         3 |                 0.853254 |                      721 |               0.854438 |              0.0345814 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps5_gt_50                                   | and2   |         2 |                 0.853254 |                      721 |               0.854438 |              0.0345839 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps5_gt_50 AND vol_ratio5_gt_1_0             | and3   |         3 |                 0.853254 |                      721 |               0.854438 |              0.0345839 |                         -18 |                          -42 |
| money_ratio5_gt_1_0 AND money_ratio5_gt_2_0 AND rps5_gt_50           | and3   |         3 |                 0.853254 |                      721 |               0.854438 |              0.0345839 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps10_gt_40                                  | and2   |         2 |                 0.853254 |                      721 |               0.855621 |              0.0351479 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps10_gt_40 AND vol_ratio5_gt_1_0            | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0351479 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND money_ratio10_gt_2_0                         | and2   |         2 |                 0.861538 |                      728 |               0.871006 |              0.0355779 |                         -15 |                          -42 |
| money_ratio20_gt_1_2 AND money_ratio5_gt_2_0 AND rps5_gt_40          | and3   |         3 |                 0.861538 |                      728 |               0.863905 |              0.0360686 |                         -18 |                          -42 |
| money_ratio5_gt_2_0 AND rps5_gt_40 AND vol_ratio20_gt_1_2            | and3   |         3 |                 0.859172 |                      726 |               0.861538 |              0.0361014 |                         -18 |                          -42 |
| money_ratio10_gt_1_2 AND money_ratio5_gt_2_0 AND rps5_gt_40          | and3   |         3 |                 0.865089 |                      731 |               0.867456 |              0.0364884 |                         -18 |                          -43 |
| money_ratio5_gt_2_0 AND rps5_gt_40 AND vol_ratio10_gt_1_2            | and3   |         3 |                 0.865089 |                      731 |               0.867456 |              0.0364909 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_2_0 AND vol_ratio10_gt_1_2       | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365061 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio10_gt_1_2 AND money_ratio5_gt_2_0     | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365061 |                         -18 |                          -43 |
| money_ratio5_gt_2_0 AND rps5_gt_40                                   | and2   |         2 |                 0.865089 |                      731 |               0.867456 |              0.0365314 |                         -18 |                          -43 |
| money_ratio5_gt_2_0 AND rps5_gt_40 AND vol_ratio5_gt_1_2             | and3   |         3 |                 0.865089 |                      731 |               0.867456 |              0.0365314 |                         -18 |                          -43 |
| money_ratio5_gt_1_2 AND money_ratio5_gt_2_0 AND rps5_gt_40           | and3   |         3 |                 0.865089 |                      731 |               0.867456 |              0.0365314 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_2_0 AND vol_ratio10_gt_1_0       | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365516 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio10_gt_1_0 AND money_ratio5_gt_2_0     | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365516 |                         -18 |                          -43 |
| money_ratio5_gt_2_0 AND close_ema5_gt_0                              | and2   |         2 |                 0.850888 |                      719 |               0.854438 |              0.0365567 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_2_0 AND vol_ratio5_gt_1_2        | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365567 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_1_2 AND money_ratio5_gt_2_0      | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365567 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_2_0 AND vol_ratio5_gt_1_0        | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365567 |                         -18 |                          -43 |
| close_ema5_gt_0 AND money_ratio5_gt_1_0 AND money_ratio5_gt_2_0      | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0365567 |                         -18 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio20_gt_1_2 AND money_ratio5_gt_2_0 | and3   |         3 |                 0.852071 |                      720 |               0.855621 |              0.0372927 |                         -17 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio5_gt_2_0 AND vol_ratio20_gt_1_2   | and3   |         3 |                 0.850888 |                      719 |               0.854438 |              0.0373256 |                         -17 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio5_gt_2_0 AND vol_ratio10_gt_1_2   | and3   |         3 |                 0.854438 |                      722 |               0.857988 |              0.0377302 |                         -17 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio10_gt_1_2 AND money_ratio5_gt_2_0 | and3   |         3 |                 0.854438 |                      722 |               0.857988 |              0.0377302 |                         -17 |                          -43 |
| money_ratio5_gt_2_0 AND boll20_pct_b_gt_0_3                          | and2   |         2 |                 0.854438 |                      722 |               0.857988 |              0.0377808 |                         -17 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio5_gt_2_0 AND vol_ratio5_gt_1_2    | and3   |         3 |                 0.854438 |                      722 |               0.857988 |              0.0377808 |                         -17 |                          -43 |
| boll20_pct_b_gt_0_3 AND money_ratio5_gt_1_2 AND money_ratio5_gt_2_0  | and3   |         3 |                 0.854438 |                      722 |               0.857988 |              0.0377808 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio20_gt_1_2 AND money_ratio5_gt_2_0    | and3   |         3 |                 0.865089 |                      731 |               0.868639 |              0.0379933 |                         -17 |                          -43 |
| money_ratio5_gt_2_0 AND close_ema20_gt_m2                            | and2   |         2 |                 0.853254 |                      721 |               0.856805 |              0.0380008 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio5_gt_2_0 AND vol_ratio20_gt_1_2      | and3   |         3 |                 0.863905 |                      730 |               0.867456 |              0.0380413 |                         -17 |                          -43 |
| close_ema10_gt_m2 AND money_ratio20_gt_1_2 AND money_ratio5_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.868639 |              0.0382108 |                         -17 |                          -43 |
| vol_ratio5_gt_2_0 AND money_ratio20_gt_1_5                           | and2   |         2 |                 0.860355 |                      727 |               0.872189 |              0.0382512 |                         -14 |                          -43 |
| close_ema10_gt_m2 AND money_ratio5_gt_2_0 AND vol_ratio20_gt_1_2     | and3   |         3 |                 0.863905 |                      730 |               0.867456 |              0.0382563 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio10_gt_1_2 AND money_ratio5_gt_2_0    | and3   |         3 |                 0.869822 |                      735 |               0.873373 |              0.0384713 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio5_gt_2_0 AND vol_ratio10_gt_1_2      | and3   |         3 |                 0.869822 |                      735 |               0.873373 |              0.0384738 |                         -17 |                          -43 |
| close_ma5_gt_m2 AND money_ratio20_gt_1_2 AND money_ratio5_gt_2_0     | and3   |         3 |                 0.868639 |                      734 |               0.872189 |              0.0384763 |                         -17 |                          -43 |
| money_ratio5_gt_2_0 AND close_near_high10_gt_m5                      | and2   |         2 |                 0.860355 |                      727 |               0.865089 |              0.0384839 |                         -17 |                          -43 |
| money_ratio5_gt_2_0 AND close_ma10_gt_m2                             | and2   |         2 |                 0.869822 |                      735 |               0.873373 |              0.0385244 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio5_gt_2_0 AND vol_ratio5_gt_1_2       | and3   |         3 |                 0.869822 |                      735 |               0.873373 |              0.0385244 |                         -17 |                          -43 |
| close_ma10_gt_m2 AND money_ratio5_gt_1_2 AND money_ratio5_gt_2_0     | and3   |         3 |                 0.869822 |                      735 |               0.873373 |              0.0385244 |                         -17 |                          -43 |
| close_ma5_gt_m2 AND money_ratio5_gt_2_0 AND vol_ratio20_gt_1_2       | and3   |         3 |                 0.867456 |                      733 |               0.871006 |              0.038532  |                         -17 |                          -43 |
| money_ratio20_gt_1_2 AND vol_ratio20_gt_1_5 AND vol_ratio5_gt_2_0    | and3   |         3 |                 0.863905 |                      730 |               0.87574  |              0.0386078 |                         -14 |                          -44 |
| money_ratio5_gt_1_0 AND vol_ratio20_gt_1_5 AND vol_ratio5_gt_2_0     | and3   |         3 |                 0.863905 |                      730 |               0.87574  |              0.0386104 |                         -14 |                          -44 |
| money_ratio5_gt_0_8 AND vol_ratio20_gt_1_5 AND vol_ratio5_gt_2_0     | and3   |         3 |                 0.863905 |                      730 |               0.87574  |              0.0386104 |                         -14 |                          -44 |

## 观察

1. 最低密度且能达到 85% 覆盖的日级条件仍集中在成交量/成交额放大，尤其 `vol_ratio > 2` 一类。它覆盖高，是因为 60 天窗口给了很多触发机会。
2. 加入 `new_high_20`、短期收益、RSI>50、MA/EMA 上方等条件后，覆盖仍可在 85% 附近，但密度略高或覆盖略低。这些更接近可解释的启动结构。
3. RPS>90、完整均线多头、持续站上 Bollinger 上轨通常过窄，不适合作为 85% 覆盖型条件。
4. `window_and2` 结果只能说明画像共现，不代表同一天可执行 seed；若做入口规则，应优先看 `single/and2/and3/kof`。
