# Explore4 Valid 交易级归因报告

- 覆盖版本：`fixed_weight_layered_exit, risk_unit_rb050_sw03, risk_unit_rb050_sw03_cap20`。
- 归因分组行数：`159`。
- 失败样本行数：`294`。
- 所有归因字段使用 T 日 as-of 数据；T+1 仅用于 open/gap/execution 审计。

## 净亏损最大的分组

| 版本 | 分组 | 取值 | 交易数 | 胜率 | 平均收益 | 净收益 | 回撤代理 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_weight_layered_exit | exit_reason | stop_loss | 40 | 0.00% | -5.51% | -95,132 | -9.40% |
| fixed_weight_layered_exit | gap_bucket | flat | 147 | 26.53% | -1.32% | -87,340 | -9.60% |
| fixed_weight_layered_exit | entry_type | pullback | 145 | 28.28% | -1.23% | -80,392 | -9.66% |
| fixed_weight_layered_exit | exit_reason | time_stop | 59 | 6.78% | -2.90% | -77,425 | -7.70% |
| fixed_weight_layered_exit | industry_ok_entry | True | 170 | 28.82% | -0.91% | -69,850 | -10.62% |
| fixed_weight_layered_exit | market_ok_entry | True | 170 | 28.82% | -0.91% | -69,850 | -10.62% |
| fixed_weight_layered_exit | width_ok_entry | True | 170 | 28.82% | -0.91% | -69,850 | -10.62% |
| fixed_weight_layered_exit | holding_days_bucket | 11_20 | 88 | 22.73% | -1.64% | -68,060 | -7.99% |
| risk_unit_rb050_sw03 | exit_reason | stop_loss | 39 | 0.00% | -5.44% | -60,519 | -5.98% |
| risk_unit_rb050_sw03_cap20 | exit_reason | stop_loss | 39 | 0.00% | -5.43% | -60,514 | -5.98% |

## 初步结论

- 该报告用于定位 valid 负收益来源，不形成新参数。
- 优先查看 `valid_failure_samples.csv` 中的 pullback + stop_loss/time_stop 样本。
