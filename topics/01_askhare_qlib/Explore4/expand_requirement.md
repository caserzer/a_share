# Explore4 扩展需求：Valid 负收益归因与风险单位仓位复查

## 1. 背景

Explore4 默认阶段 1 到阶段 3 已完成独立重跑。当前结果显示：

- `valid` 区间没有 risk-unit 或 industry-cap 候选满足完整验收条件。
- 当前最终标记版本 `risk_unit_rb050_sw03_cap20` 只能作为 `diagnostic_fallback_no_eligible`，不能视为正式入选参数。
- risk-unit 和行业 cap 能降低回撤、成本和集中度，但没有把 `valid` 成本后收益转正。
- `2025-2026` 只能作为 `observed_test / frozen_replication`，不能用于继续调参。

因此下一步不进入 meta-labeling，而应先定位 `valid` 负收益来源。

## 2. 扩展目标

本扩展阶段只回答一个问题：

```text
Explore4 的 valid 负收益主要来自信号质量、pullback 入场、退出规则、仓位约束，
还是来自当前静态股票池和行情阶段本身？
```

## 3. 研究边界

必须遵守：

- 暂停进入 meta-labeling。
- 不使用 `observed_test` 结果反向修改参数。
- 不把 2025-2026 当作未见样本外 final test。
- 不扩大成大规模参数搜索。
- CSV 明细和中间诊断表统一写入 `Explore4/outputs/diagnostics/`。
- Markdown 汇总报告统一写入 `Explore4/outputs/reports/`。
- 原 Explore4 默认结果保留，不覆盖为“合格最终版本”。
- 所有交易归因字段必须使用 `signal_date` T 日收盘后可观察数据。T+1 只能用于 `entry_open`、跳空、成交和执行审计，不能混入未来市场状态。
- 若运行 `observed_test` 诊断，只能标记为 `observed_diagnostic_not_for_selection`，不得参与选择、不得覆盖 valid 结论、不得形成新参数。

## 4. 任务一：Valid 交易级归因

针对 `valid` 区间交易，优先分析失败交易：

- `pullback + stop_loss`
- `pullback + time_stop`
- `breakout + stop_loss`
- `breakout + time_stop`

至少按以下维度分组：

- 市场状态，使用 T 日 `market_ok_entry` / broad market regime。
- 行业状态，使用 T 日 `industry_ok_entry` / `industry_trend_ok`。
- 宽度状态，使用 T 日 `width_ok_entry` / market width。
- `trend_score` 分位。
- 入场类型。
- 退出类型。
- 成交额确认。
- T 日到 T+1 open 的跳空。
- 初始 R / entry price。
- 持仓天数。

`valid_trade_attribution.csv` 至少包含以下列：

```text
period, version, group_name, group_value, trades, win_rate,
avg_cost_after_return, median_cost_after_return, net_pnl_sum,
gross_pnl_sum, avg_holding_days, stop_loss_count, time_stop_count,
trailing_stop_count, max_drawdown_proxy, avg_initial_risk_pct,
avg_gap_pct, avg_trend_score_pct
```

`valid_failure_samples.csv` 至少包含以下列：

```text
version, instrument, signal_date, order_date, exit_date,
entry_type, exit_reason, industry_name, market_ok_entry,
width_ok_entry, industry_ok_entry, trend_score_pct,
money_ratio20, ret60, entry_open, signal_close, gap_pct,
initial_stop, initial_risk_per_share, initial_risk_pct,
holding_days, cost_after_return, net_pnl
```

需要输出：

```text
Explore4/outputs/diagnostics/valid_trade_attribution.csv
Explore4/outputs/diagnostics/valid_failure_samples.csv
Explore4/outputs/reports/valid_trade_attribution_report.md
```

## 5. 任务二：Pullback 子规则复查

单独评估 pullback 是否是 valid 负收益的主要来源。

默认只允许做以下小规模诊断，不进入最终参数选择：

1. `breakout_only`：保留 breakout，关闭 pullback。
2. `pullback_only`：只保留 pullback。
3. `pullback_strict_money`：只改 pullback 成交额条件，固定为 `0.60 <= money_ratio20 <= 0.95`，并把 `avg_money20` 的日内流动性门槛从原 p20 提高到 p30。
4. `pullback_strict_trend`：只改 pullback 趋势确认，固定为 `trend_score_pct <= 0.15`，并要求 T 日 market width 同时满足 `close_gt_ema60_ratio > 0.60`、`ema20_gt_ema60_ratio > 0.50`。

要求：

- 默认只运行 `valid` 诊断。
- 如显式开启 observed 对照，输出必须标记为 `observed_diagnostic_not_for_selection`，且报告必须把 observed 结果放在单独章节，不允许用于解释“哪个诊断版本更好”。
- 每个诊断版本都必须标记为 `diagnostic_only`。
- 不得覆盖 Explore4 当前选择结果。
- 诊断版本总数固定为 4，不允许新增笛卡尔积组合。
- 所有诊断只用于定位问题，不能形成新的最终版本。

需要输出：

```text
Explore4/outputs/diagnostics/pullback_rule_diagnostic.csv
Explore4/outputs/reports/pullback_rule_diagnostic_report.md
```

## 6. 任务三：风险单位仓位约束拆解

重新审视“风险预算没有用满”的原因。

需要拆解每笔订单在以下约束后的可用预算：

1. 原始风险预算。
2. 单票上限后预算。
3. 行业上限后预算。
4. 当日新增上限后预算。
5. 现金约束后预算。
6. 100 股整数手后实际成交金额。

`risk_constraint_decomposition.csv` 至少包含以下列：

```text
period, version, instrument, signal_date, order_date,
entry_type, status, skip_reason, entry_price, initial_stop,
initial_risk_per_share, initial_risk_pct, account_value_before,
cash_before, raw_risk_budget_value, raw_position_value,
after_single_stock_cap, after_industry_cap, after_daily_new_cap,
after_cash_cap, rounded_value, rounded_amount, entry_cost,
cash_after, blocked_layer, industry_name, industry_exposure_before,
daily_new_value_before
```

`blocked_layer` 固定枚举：

```text
none, invalid_initial_stop, max_positions, single_stock_cap,
industry_cap, daily_new_cap, cash_cap, round_lot, limit_blocked,
invalid_open, no_market_row
```

重点回答：

- 是 `initial_stop` 太宽导致 raw position 过小，还是单票 / 行业 cap 把仓位压低？
- `zero_lot` 订单主要被哪一层约束压到无法成交？
- 当前 `0.5% risk_budget + 3% single_stock_max + 20% industry_cap` 是否过于保守？
- 风险预算使用不足是否会导致组合长期高现金、收益被稀释？

需要输出：

```text
Explore4/outputs/diagnostics/risk_constraint_decomposition.csv
Explore4/outputs/reports/risk_constraint_decomposition_report.md
```

## 7. 任务四：等待真正 Final Test

若后续新增行情形成真正未见数据，才允许进行一次 final test。

触发条件：

- 当前冻结观察区间截止日为 `2026-04-30`。
- Qlib provider 中必须存在 `2026-04-30` 之后的新交易日行情。
- 至少形成 20 个可执行交易日后，才允许开启 final test。
- `final_test_start` 固定为 `observed_test_end` 后第一个交易日。
- `final_test_executable_end` 固定为新增数据最后一个交易日前一日，确保最后一个信号仍可在 T+1 open 执行。

要求：

- final test 只评估冻结版本或扩展阶段明确冻结后的唯一版本。
- 不得根据 final test 结果继续修改参数。
- manifest 必须记录新增行情截止日、可执行回测截止日、实际 final test 起止日期、冻结版本 SHA256、是否满足 20 个可执行交易日。
- 若没有新增行情，报告继续写明“没有真正 final_test”。

## 8. 执行入口和产物

建议在 `Explore4/scripts/run_explore4.py` 中新增以下命令：

```text
diagnose-valid
pullback-diagnostic
risk-decompose
expand-report
```

其中：

- `diagnose-valid` 生成 valid 交易归因和失败样本。
- `pullback-diagnostic` 只运行 4 个固定诊断版本。
- `risk-decompose` 生成逐订单风险约束拆解。
- `expand-report` 依次运行以上三个命令，并生成中文扩展汇总报告。

必须新增 `run_manifest.json` 字段：

```text
expand_diagnostic_versions
observed_diagnostic_used_for_selection
valid_trade_attribution_rows
risk_constraint_decomposition_rows
final_test_available
final_test_trigger_reason
```

扩展汇总报告：

```text
Explore4/outputs/reports/explore4_expand_report.md
```

## 9. 测试计划

静态检查：

```text
uv run python -m compileall Explore4/scripts
uv run python Explore4/scripts/run_explore4.py self-test
```

产物生成：

```text
uv run python Explore4/scripts/run_explore4.py expand-report --config Explore4/configs/trend_rule_v1_frozen.yaml
```

内容验收：

- `pullback_rule_diagnostic.csv` 只能包含 4 个 `diagnostic_only` 版本。
- 若存在 observed 对照，所有 observed 行必须标记为 `observed_diagnostic_not_for_selection`。
- `run_manifest.json` 中 `observed_diagnostic_used_for_selection` 必须为 `false`。
- `valid_trade_attribution.csv` 和 `risk_constraint_decomposition.csv` 必须包含本需求列出的必需列。
- `risk_constraint_decomposition.csv` 的 `blocked_layer` 只能使用固定枚举。
- 所有 diagnostics CSV 非空。
- 所有 Markdown 报告为中文。
- 不得修改 `parameter_grid_summary.csv`、`valid_selection_summary.csv`、`test_result_summary.csv` 的既有 Explore4 默认结果。

## 10. 验收标准

扩展阶段完成后必须回答：

- `valid` 负收益主要来自哪类交易和哪类退出。
- pullback 是否需要收紧、关闭或拆分。
- breakout 是否独立保持正贡献。
- stop loss / time stop 的亏损是否来自初始 R 过宽、趋势衰减、行业同步性不足或开盘跳空。
- 风险预算使用不足的主要约束层是哪一层。
- 行业 cap 是否只是降低暴露，还是也明显牺牲收益来源。
- 是否仍应暂停 meta-labeling。
- 是否有条件形成新的冻结版本等待真正 final test。
