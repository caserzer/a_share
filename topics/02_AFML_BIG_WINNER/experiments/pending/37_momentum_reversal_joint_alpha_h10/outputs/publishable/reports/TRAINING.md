# EP37 训练方式与稳健性结果

本轮训练季度推进，共216个最终模型；主expanding含5种目标/特征/样本权重组合，rolling36及后移5交易日仅复核A_R与J_R。正则从1、10、100中用内层最近12月的共同有效日期选择；所有外层目标在出分时隔离。

| scheme    |   offset | model   | status   |   fold_count |
|:----------|---------:|:--------|:---------|-------------:|
| expanding |        0 | A_R     | OK       |           24 |
| expanding |        0 | A_Z     | OK       |           24 |
| expanding |        0 | J_R     | OK       |           24 |
| expanding |        0 | J_RW    | OK       |           24 |
| expanding |        0 | J_Z     | OK       |           24 |
| expanding |        5 | A_R     | OK       |           24 |
| expanding |        5 | J_R     | OK       |           24 |
| rolling36 |        0 | A_R     | OK       |           24 |
| rolling36 |        0 | J_R     | OK       |           24 |

## 内层正则选择分布

| scheme    |   offset | model   |    alpha |   fold_count |
|:----------|---------:|:--------|---------:|-------------:|
| expanding |        0 | A_R     |   1.0000 |            8 |
| expanding |        0 | A_R     |  10.0000 |            3 |
| expanding |        0 | A_R     | 100.0000 |           13 |
| expanding |        0 | A_Z     |   1.0000 |            9 |
| expanding |        0 | A_Z     |  10.0000 |            6 |
| expanding |        0 | A_Z     | 100.0000 |            9 |
| expanding |        0 | J_R     |   1.0000 |            9 |
| expanding |        0 | J_R     |  10.0000 |            8 |
| expanding |        0 | J_R     | 100.0000 |            7 |
| expanding |        0 | J_RW    |   1.0000 |           13 |
| expanding |        0 | J_RW    |  10.0000 |            5 |
| expanding |        0 | J_RW    | 100.0000 |            6 |
| expanding |        0 | J_Z     |   1.0000 |           11 |
| expanding |        0 | J_Z     |  10.0000 |            4 |
| expanding |        0 | J_Z     | 100.0000 |            9 |
| expanding |        5 | A_R     |   1.0000 |            7 |
| expanding |        5 | A_R     |  10.0000 |            6 |
| expanding |        5 | A_R     | 100.0000 |           11 |
| expanding |        5 | J_R     |   1.0000 |            8 |
| expanding |        5 | J_R     |  10.0000 |            5 |
| expanding |        5 | J_R     | 100.0000 |           11 |
| rolling36 |        0 | A_R     |   1.0000 |            7 |
| rolling36 |        0 | A_R     |  10.0000 |            5 |
| rolling36 |        0 | A_R     | 100.0000 |           12 |
| rolling36 |        0 | J_R     |   1.0000 |           10 |
| rolling36 |        0 | J_R     |  10.0000 |            7 |
| rolling36 |        0 | J_R     | 100.0000 |            7 |

## 滚动训练与起点敏感性

下表每条策略与其同方案A_R使用相同起止；不同起点的净值不能解释成同日期纯Alpha差。均固定H10。

| scheme    |   offset | scope    | model   | start      | end        | valuation_complete   | cagr     |   max_drawdown |
|:----------|---------:|:---------|:--------|:-----------|:-----------|:---------------------|:---------|---------------:|
| expanding |        5 | primary  | A_R     | 2021-01-18 | 2025-02-24 | True                 | -10.8681 |       -52.7047 |
| expanding |        5 | extended | A_R     | 2021-01-18 | 2026-10-19 | True                 | -13.8042 |       -58.1127 |
| expanding |        5 | primary  | J_R     | 2021-01-18 | 2025-02-24 | True                 | -12.5227 |       -59.9935 |
| expanding |        5 | extended | J_R     | 2021-01-18 | 2026-10-19 | True                 | -14.8306 |       -60.2143 |
| rolling36 |        0 | primary  | A_R     | 2021-01-11 | 2025-03-03 | True                 | -11.381  |       -50.7867 |
| rolling36 |        0 | extended | A_R     | 2021-01-11 | 2025-03-03 | False                | NA       |       -50.7867 |
| rolling36 |        0 | primary  | J_R     | 2021-01-11 | 2025-03-03 | True                 | -14.3862 |       -55.5304 |
| rolling36 |        0 | extended | J_R     | 2021-01-11 | 2026-10-12 | True                 | -12.2358 |       -55.5304 |

## 时间块敏感性

| scope   | test   |   n |   calendar_n |   mean |     low |   high |      p |   block |   holm_p | positive_support   |
|:--------|:-------|----:|-------------:|-------:|--------:|-------:|-------:|--------:|---------:|:-------------------|
| primary | P1     | 100 |          100 | 0.0050 | -0.0130 | 0.0238 | 0.6017 |       3 |   1.0000 | False              |
| primary | P2a    |  95 |          100 | 0.0000 | -0.0043 | 0.0044 | 0.9990 |       3 |   1.0000 | False              |
| primary | P2b    |  95 |          100 | 0.0021 | -0.0047 | 0.0090 | 0.5497 |       3 |   1.0000 | False              |
| primary | P2c    |  92 |          100 | 0.0017 | -0.0028 | 0.0064 | 0.4643 |       3 |   1.0000 | False              |
| primary | P2d    |  96 |          100 | 0.0037 | -0.0024 | 0.0097 | 0.2264 |       3 |   1.0000 | False              |
| primary | P3     |  35 |          100 | 0.0098 | -0.0095 | 0.0319 | 0.3538 |       3 |   1.0000 | False              |
| primary | P1     | 100 |          100 | 0.0050 | -0.0114 | 0.0217 | 0.5502 |      12 |   1.0000 | False              |
| primary | P2a    |  95 |          100 | 0.0000 | -0.0045 | 0.0041 | 1.0000 |      12 |   1.0000 | False              |
| primary | P2b    |  95 |          100 | 0.0021 | -0.0042 | 0.0079 | 0.4983 |      12 |   1.0000 | False              |
| primary | P2c    |  92 |          100 | 0.0017 | -0.0030 | 0.0060 | 0.4513 |      12 |   1.0000 | False              |
| primary | P2d    |  96 |          100 | 0.0037 | -0.0018 | 0.0085 | 0.1544 |      12 |   0.9265 | False              |
| primary | P3     |  35 |          100 | 0.0098 | -0.0068 | 0.0281 | 0.2684 |      12 |   1.0000 | False              |

[逐折时序及模型哈希](../folds.csv) · [内层候选完整结果](../inner_selection.csv) · [所有模型系数](../coefficients.csv) · [四状态训练权重](../training_state_weights.csv.gz) · [事后集中性描述](../concentration_diagnostics.csv) · [总报告](REPORT.md)
