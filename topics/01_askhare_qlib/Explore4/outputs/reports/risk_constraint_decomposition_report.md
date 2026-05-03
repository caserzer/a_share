# Explore4 风险单位仓位约束拆解报告

- 版本：`risk_unit_rb050_sw03_cap20`。
- 分解订单行数：`179`。
- 成交订单相对 raw position 的平均使用比例：`36.49%`。

| 约束层 | 状态 | 数量 |
| --- | --- | --- |
| none | executed | 167 |
| round_lot | skipped | 9 |
| industry_cap | skipped | 3 |

## 初步结论

- `blocked_layer` 用于定位订单最终被哪一层约束压低或阻断。
- `zero_lot` 应优先结合 `after_*` 预算列判断是 cap、现金还是整数手造成。
