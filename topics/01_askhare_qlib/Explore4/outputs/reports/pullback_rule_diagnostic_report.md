# Explore4 Pullback 子规则诊断报告

- 本诊断只运行 valid 区间。
- 4 个版本均标记为 `diagnostic_only`，不参与最终参数选择。
- observed_test 未运行；不存在 observed 反向调参。

| 诊断版本 | 范围 | 成本后收益 | 最大回撤 | 交易数 | 胜率 | 平均现金 |
| --- | --- | --- | --- | --- | --- | --- |
| breakout_only | diagnostic_only | 0.15% | -2.88% | 32 | 28.12% | 96.75% |
| pullback_strict_trend | diagnostic_only | -2.00% | -5.11% | 124 | 29.84% | 91.93% |
| pullback_strict_money | diagnostic_only | -3.00% | -6.68% | 140 | 27.14% | 91.17% |
| pullback_only | diagnostic_only | -5.35% | -6.75% | 155 | 27.10% | 91.48% |

## 初步结论

- valid 中收益最高的诊断版本为 `breakout_only`，成本后收益 `0.15%`。
- 该结果只用于判断 pullback 是否是负收益来源，不形成新冻结版本。
