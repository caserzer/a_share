# Big Winner T+0 到 T+30 组合指标覆盖率搜索 v1

- 样本：845 个 canonical R01 primary big winner
- 覆盖定义：同一股票在 reference_date 的 T+0 到 T+30 至少一天满足日级条件
- 密度定义：条件在 R01 PIT-executable eligible stock-days 上的日级触发比例
- 搜索规模：368 个原子条件，65273 个单条件/组合条件

## 推荐的低密度 T+0..T+30 覆盖条件（coverage >=85%）

```text
close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60
```

| metric | value |
|:--|--:|
| kind | and4 |
| coverage T+0..T+30 | 94.32% |
| covered events | 797 / 845 |
| eligible-day density | 7.91% |
| median closest hit offset | 8.0 |
| median earliest hit offset | 8.0 |

## Split 覆盖

| split      |   event_count |   covered_t0_t30 |   coverage_t0_t30 |
|:-----------|--------------:|-----------------:|------------------:|
| robustness |           241 |              226 |          0.937759 |
| train      |           446 |              420 |          0.941704 |
| validation |           158 |              151 |          0.955696 |

## 覆盖 >=85% 的 Top 100 低密度条件

| condition                                                                                | kind   |   n_terms |   coverage_t0_t30 |   covered_events_t0_t30 |   eligible_day_density |   median_closest_hit_offset |   median_earliest_hit_offset |
|:-----------------------------------------------------------------------------------------|:-------|----------:|------------------:|------------------------:|-----------------------:|----------------------------:|-----------------------------:|
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60     | and4   |         4 |          0.943195 |                     797 |              0.0790974 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60           | and4   |         4 |          0.943195 |                     797 |              0.0790974 |                         8   |                          8   |
| close_near_high5_gt_0pct AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60   | and4   |         4 |          0.946746 |                     800 |              0.0814647 |                         8   |                          8   |
| close_breaks_high5 AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60         | and4   |         4 |          0.946746 |                     800 |              0.0814647 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60   | and4   |         4 |          0.947929 |                     801 |              0.0822285 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60         | and4   |         4 |          0.947929 |                     801 |              0.0822285 |                         8   |                          8   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60     | and4   |         4 |          0.950296 |                     803 |              0.0822943 |                         8   |                          8   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60           | and4   |         4 |          0.950296 |                     803 |              0.0822943 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60     | and4   |         4 |          0.947929 |                     801 |              0.0826408 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60           | and4   |         4 |          0.947929 |                     801 |              0.0826408 |                         8   |                          8   |
| money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60   | and4   |         4 |          0.953846 |                     806 |              0.0846692 |                         8   |                          8   |
| money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60         | and4   |         4 |          0.953846 |                     806 |              0.0846692 |                         8   |                          8   |
| close_near_high5_gt_0pct AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60   | and4   |         4 |          0.952663 |                     805 |              0.0850966 |                         8   |                          8   |
| close_breaks_high5 AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60         | and4   |         4 |          0.952663 |                     805 |              0.0850966 |                         8   |                          8   |
| close_near_high5_gt_0pct AND money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60 | and4   |         4 |          0.956213 |                     808 |              0.0851522 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60       | and4   |         4 |          0.956213 |                     808 |              0.0851522 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60   | and4   |         4 |          0.953846 |                     806 |              0.0854937 |                         8   |                          8   |
| vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60         | and4   |         4 |          0.953846 |                     806 |              0.0854937 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_60   | and4   |         4 |          0.953846 |                     806 |              0.0858579 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_60         | and4   |         4 |          0.953846 |                     806 |              0.0858579 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60      | and4   |         4 |          0.956213 |                     808 |              0.0861563 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60            | and4   |         4 |          0.956213 |                     808 |              0.0861563 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND rps5_gt_60     | and4   |         4 |          0.949112 |                     802 |              0.0864092 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND rps5_gt_60           | and4   |         4 |          0.949112 |                     802 |              0.0864092 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60       | and4   |         4 |          0.951479 |                     804 |              0.0864902 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60             | and4   |         4 |          0.951479 |                     804 |              0.0864902 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60     | and4   |         4 |          0.951479 |                     804 |              0.0870592 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60           | and4   |         4 |          0.951479 |                     804 |              0.0870592 |                         7   |                          7   |
| close_near_high5_gt_0pct AND money_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60    | and4   |         4 |          0.957396 |                     809 |              0.0881569 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60          | and4   |         4 |          0.957396 |                     809 |              0.0881569 |                         7   |                          7   |
| money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60 | and4   |         4 |          0.96213  |                     813 |              0.0884275 |                         7   |                          7   |
| money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60       | and4   |         4 |          0.96213  |                     813 |              0.0884275 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND rps5_gt_60   | and4   |         4 |          0.951479 |                     804 |              0.088554  |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND rps5_gt_60         | and4   |         4 |          0.951479 |                     804 |              0.088554  |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_50     | and4   |         4 |          0.959763 |                     811 |              0.0887664 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_50           | and4   |         4 |          0.959763 |                     811 |              0.0887664 |                         7   |                          7   |
| close_near_high5_gt_0pct AND money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_60 | and4   |         4 |          0.96213  |                     813 |              0.0888651 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_60       | and4   |         4 |          0.96213  |                     813 |              0.0888651 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60    | and4   |         4 |          0.959763 |                     811 |              0.0890623 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60          | and4   |         4 |          0.959763 |                     811 |              0.0890623 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND rps3_gt_60 AND rps5_gt_60             | and4   |         4 |          0.960947 |                     812 |              0.0892975 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND rps3_gt_60 AND rps5_gt_60                   | and4   |         4 |          0.960947 |                     812 |              0.0892975 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps3_gt_60     | and4   |         4 |          0.960947 |                     812 |              0.0895555 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps3_gt_60           | and4   |         4 |          0.960947 |                     812 |              0.0895555 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60     | and4   |         4 |          0.95503  |                     807 |              0.0895707 |                         8   |                          8   |
| vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND close_breaks_high3 AND rps5_gt_60           | and4   |         4 |          0.95503  |                     807 |              0.0895707 |                         8   |                          8   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND rps3_gt_60     | and4   |         4 |          0.953846 |                     806 |              0.089773  |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND vol_ratio5_gt_1_2 AND rps3_gt_60           | and4   |         4 |          0.953846 |                     806 |              0.089773  |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ma3_gt_0pct            | and4   |         4 |          0.957396 |                     809 |              0.0899248 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND money_ratio5_gt_1_2 AND rps5_gt_60   | and4   |         4 |          0.949112 |                     802 |              0.0899526 |                         8   |                          8   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND money_ratio5_gt_1_2 AND rps5_gt_60         | and4   |         4 |          0.949112 |                     802 |              0.0899526 |                         8   |                          8   |
| vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60      | and4   |         4 |          0.963314 |                     814 |              0.0901726 |                         7   |                          7   |
| vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60            | and4   |         4 |          0.963314 |                     814 |              0.0901726 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND vol_ratio10_gt_1 AND rps5_gt_60       | and4   |         4 |          0.95858  |                     810 |              0.0903573 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND vol_ratio10_gt_1 AND rps5_gt_60             | and4   |         4 |          0.95858  |                     810 |              0.0903573 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps3_gt_60       | and4   |         4 |          0.959763 |                     811 |              0.0906228 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps3_gt_60             | and4   |         4 |          0.959763 |                     811 |              0.0906228 |                         7   |                          7   |
| vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND vol_ratio20_gt_1 AND rps5_gt_60       | and4   |         4 |          0.959763 |                     811 |              0.0906304 |                         7   |                          7   |
| vol_ratio3_gt_1_2 AND close_breaks_high3 AND vol_ratio20_gt_1 AND rps5_gt_60             | and4   |         4 |          0.959763 |                     811 |              0.0906304 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60      | and4   |         4 |          0.963314 |                     814 |              0.0906709 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60            | and4   |         4 |          0.963314 |                     814 |              0.0906709 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ema3_gt_0pct           | and4   |         4 |          0.957396 |                     809 |              0.090724  |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_60 AND rps5_gt_60                   | and4   |         4 |          0.953846 |                     806 |              0.0907695 |                         7   |                          7   |
| close_near_high5_gt_0pct AND money_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60     | and4   |         4 |          0.95858  |                     810 |              0.0907721 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio3_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60           | and4   |         4 |          0.95858  |                     810 |              0.0907721 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND ret3_gt_0pct                 | and4   |         4 |          0.953846 |                     806 |              0.0907999 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND money_ratio10_gt_1 AND rps5_gt_60     | and4   |         4 |          0.960947 |                     812 |              0.0910503 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND money_ratio10_gt_1 AND rps5_gt_60           | and4   |         4 |          0.960947 |                     812 |              0.0910503 |                         7   |                          7   |
| vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND money_ratio20_gt_1 AND rps5_gt_60     | and4   |         4 |          0.959763 |                     811 |              0.0911464 |                         7   |                          7   |
| vol_ratio3_gt_1_2 AND close_breaks_high3 AND money_ratio20_gt_1 AND rps5_gt_60           | and4   |         4 |          0.959763 |                     811 |              0.0911464 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps3_gt_60     | and4   |         4 |          0.95858  |                     810 |              0.091159  |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps3_gt_60           | and4   |         4 |          0.95858  |                     810 |              0.091159  |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ma10_gt_0pct           | and4   |         4 |          0.953846 |                     806 |              0.0913032 |                         8   |                          8   |
| close_near_high5_gt_0pct AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_50   | and4   |         4 |          0.964497 |                     815 |              0.0913184 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps3_gt_50         | and4   |         4 |          0.964497 |                     815 |              0.0913184 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ma5_gt_0pct            | and4   |         4 |          0.957396 |                     809 |              0.091417  |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND ret5_gt_0pct                 | and4   |         4 |          0.95503  |                     807 |              0.0914499 |                         8   |                          8   |
| close_near_high5_gt_0pct AND money_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60   | and4   |         4 |          0.95858  |                     810 |              0.0915283 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio3_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60         | and4   |         4 |          0.95858  |                     810 |              0.0915283 |                         7   |                          7   |
| vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ema5_gt_0pct           | and4   |         4 |          0.957396 |                     809 |              0.091637  |                         7   |                          7   |
| vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60   | and4   |         4 |          0.957396 |                     809 |              0.0916952 |                         7   |                          7   |
| vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND close_breaks_high3 AND rps5_gt_60         | and4   |         4 |          0.957396 |                     809 |              0.0916952 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60       | and4   |         4 |          0.95503  |                     807 |              0.091761  |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND vol_ratio20_gt_1 AND rps5_gt_60             | and4   |         4 |          0.95503  |                     807 |              0.091761  |                         7   |                          7   |
| close_near_high5_gt_0pct AND money_ratio5_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60  | and4   |         4 |          0.963314 |                     814 |              0.0919051 |                         7   |                          7   |
| close_breaks_high5 AND money_ratio5_gt_1_2 AND money_ratio3_gt_1_2 AND rps5_gt_60        | and4   |         4 |          0.963314 |                     814 |              0.0919051 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND rps3_gt_60   | and4   |         4 |          0.957396 |                     809 |              0.0919481 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND money_ratio10_gt_1_2 AND rps3_gt_60         | and4   |         4 |          0.957396 |                     809 |              0.0919481 |                         7   |                          7   |
| money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps3_gt_60   | and4   |         4 |          0.964497 |                     815 |              0.0919759 |                         7   |                          7   |
| money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps3_gt_60         | and4   |         4 |          0.964497 |                     815 |              0.0919759 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_50   | and4   |         4 |          0.963314 |                     814 |              0.0921024 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio10_gt_1_2 AND money_ratio3_gt_1_2 AND rps3_gt_50         | and4   |         4 |          0.963314 |                     814 |              0.0921024 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60     | and4   |         4 |          0.953846 |                     806 |              0.092158  |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND money_ratio20_gt_1 AND rps5_gt_60           | and4   |         4 |          0.953846 |                     806 |              0.092158  |                         7   |                          7   |
| money_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND close_near_high3_gt_0pct AND rps5_gt_60    | and4   |         4 |          0.964497 |                     815 |              0.0922162 |                         7   |                          7   |
| money_ratio5_gt_1_2 AND vol_ratio3_gt_1_2 AND close_breaks_high3 AND rps5_gt_60          | and4   |         4 |          0.964497 |                     815 |              0.0922162 |                         7   |                          7   |
| money_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60 AND close_ma3_gt_0pct          | and4   |         4 |          0.959763 |                     811 |              0.0924489 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio5_gt_1_2 AND rps3_gt_60 AND rps5_gt_60             | and4   |         4 |          0.952663 |                     805 |              0.0926057 |                         7   |                          7   |
| close_breaks_high5 AND vol_ratio5_gt_1_2 AND rps3_gt_60 AND rps5_gt_60                   | and4   |         4 |          0.952663 |                     805 |              0.0926057 |                         7   |                          7   |
| close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND rps5_gt_60 AND vol_ratio3_gt_1       | and4   |         4 |          0.956213 |                     808 |              0.0926386 |                         7.5 |                          7.5 |

## 观察

1. 这个搜索是 post-reference 画像搜索，不是可提前执行的 seed。它回答 winner 出现后 30 天内哪些状态最常共现。
2. 因为窗口在 T+0..T+30，覆盖率更容易被趋势确认、均线站上、成交活跃和强势排序条件推高；这些条件若用于 entry，需要另行证明可执行性和成本。
3. `AND` 条件更像日级 seed；`kof` 条件更像宽松状态画像，覆盖高但通常密度更高。

## 输出文件

- `reports/post30_condition_search_v1_all.csv`
- `reports/post30_condition_search_v1_ge85.csv`
- `reports/post30_condition_search_v1_top_single.csv`
- `reports/post30_condition_search_v1_top_and2.csv`
- `reports/post30_condition_search_v1_top_and3.csv`
- `reports/post30_condition_search_v1_top_and4.csv`
- `reports/post30_condition_search_v1_top_kof.csv`
