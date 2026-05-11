# Big Winner 前 60 天组合指标覆盖率搜索

- 样本：845 个 canonical R01 primary big winner
- 覆盖定义：同一股票在 `reference_date` 前 60 个交易日内，即 T-60 到 T-1，至少有一天满足条件
- 参考口径：也同时报告 T-60 到 T0 覆盖，但排序使用 T-60 到 T-1
- 密度定义：条件在 R01 PIT-executable eligible stock-days 上的日级触发比例
- 搜索空间：单条件、两条件 AND、beam 三条件 AND、以及若干 at-least-K-of-N 组合

## 最低密度且覆盖 >=85% 的条件

```text
money_ratio20_gt_1_5 AND vol_ratio20_gt_2_0
```

| metric | value |
|:--|--:|
| coverage T-60..T-1 | 86.51% |
| covered events | 731 / 845 |
| coverage T-60..T0 | 87.34% |
| eligible-day density | 4.96% |
| median closest hit offset | -16.0 |
| median earliest hit offset | -42.0 |

## Split 覆盖

| split      |   event_count |   covered_pre60_excl_t0 |   coverage_pre60_excl_t0 |   covered_pre60_to_t0 |   coverage_pre60_to_t0 |
|:-----------|--------------:|------------------------:|-------------------------:|----------------------:|-----------------------:|
| robustness |           241 |                     222 |                 0.921162 |                   223 |               0.925311 |
| train      |           446 |                     380 |                 0.852018 |                   382 |               0.856502 |
| validation |           158 |                     129 |                 0.816456 |                   133 |               0.841772 |

## Top 30 覆盖 >=85% 条件

| condition                                                            | kind   |   n_terms |   coverage_pre60_excl_t0 |   covered_events_excl_t0 |   coverage_pre60_to_t0 |   eligible_day_density |   median_closest_hit_offset |   median_earliest_hit_offset |
|:---------------------------------------------------------------------|:-------|----------:|-------------------------:|-------------------------:|-----------------------:|-----------------------:|----------------------------:|-----------------------------:|
| money_ratio20_gt_1_5 AND vol_ratio20_gt_2_0                          | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND money_ratio20_gt_1_5 AND vol_ratio20_gt_2_0 | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_2 AND money_ratio20_gt_1_5 AND vol_ratio20_gt_2_0 | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_5 AND vol_ratio20_gt_1_0 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_5 AND vol_ratio20_gt_1_2 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_5 AND vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0495668 |                         -16 |                          -42 |
| money_ratio20_gt_1_2 AND vol_ratio20_gt_2_0                          | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0496097 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND money_ratio20_gt_1_2 AND vol_ratio20_gt_2_0 | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496097 |                         -16 |                          -42 |
| money_ratio20_gt_1_2 AND vol_ratio20_gt_1_0 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496097 |                         -16 |                          -42 |
| money_ratio20_gt_1_2 AND vol_ratio20_gt_1_2 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496097 |                         -16 |                          -42 |
| money_ratio20_gt_1_2 AND vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496097 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND vol_ratio20_gt_2_0                          | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0496148 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND vol_ratio20_gt_1_0 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496148 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND vol_ratio20_gt_1_2 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496148 |                         -16 |                          -42 |
| money_ratio20_gt_1_0 AND vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0   | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496148 |                         -16 |                          -42 |
| vol_ratio20_gt_2_0                                                   | single |         1 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_0 AND vol_ratio20_gt_2_0                            | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_2 AND vol_ratio20_gt_2_0                            | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0                            | and2   |         2 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_0 AND vol_ratio20_gt_1_2 AND vol_ratio20_gt_2_0     | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_0 AND vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0     | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| vol_ratio20_gt_1_2 AND vol_ratio20_gt_1_5 AND vol_ratio20_gt_2_0     | and3   |         3 |                 0.865089 |                      731 |               0.873373 |              0.0496173 |                         -16 |                          -42 |
| above_ema30 AND new_high_20 AND vol_ratio20_gt_1_5                   | and3   |         3 |                 0.850888 |                      719 |               0.853254 |              0.0517899 |                         -18 |                          -43 |
| ema30_up AND new_high_20 AND vol_ratio20_gt_1_5                      | and3   |         3 |                 0.850888 |                      719 |               0.853254 |              0.0517899 |                         -18 |                          -43 |
| ma20_up AND new_high_20 AND vol_ratio20_gt_1_5                       | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0518177 |                         -18 |                          -43 |
| new_high_20 AND ret20_gt_0 AND vol_ratio20_gt_1_5                    | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0518177 |                         -18 |                          -43 |
| money_ratio20_gt_1_5 AND new_high_20 AND vol_ratio20_gt_1_5          | and3   |         3 |                 0.850888 |                      719 |               0.853254 |              0.0518329 |                         -18 |                          -43 |
| new_high_20 AND rsi14_gt_50 AND vol_ratio20_gt_1_5                   | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0518936 |                         -18 |                          -43 |
| new_high_20 AND ret10_gt_0 AND vol_ratio20_gt_1_5                    | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0519138 |                         -18 |                          -43 |
| money_ratio20_gt_1_2 AND new_high_20 AND vol_ratio20_gt_1_5          | and3   |         3 |                 0.853254 |                      721 |               0.855621 |              0.0519594 |                         -18 |                          -43 |

## 解释

这个搜索说明：若目标是 60 天窗口内覆盖 85% big winner，最稳的是“趋势位置 + 横截面强度中等偏上”的宽组合，而不是成交量爆发或 RPS>90。强 volume / RPS90 条件可以提高纯度，但会明显压低覆盖。
