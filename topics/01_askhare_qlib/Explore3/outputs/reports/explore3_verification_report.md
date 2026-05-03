# Explore3 扩展验证报告

- 生成时间：`2026-05-03 09:15:48` Asia/Shanghai。
- 本报告只验证 Explore3 既有规则结果，不修改交易规则、不调参、不引入模型。
- 审计使用配置：`Explore3/configs/trend_rule_v1.yaml`。

## 1. 结论摘要

- 信号/成交对齐失败数：`0`。
- 组合资产连续性错误数：`0`。
- 被跳过订单数：`23`，其中涨跌停阻断：`9`。
- 行业过滤与 market_width 交易差异数：`0`。
- 被行业过滤排除但无行业过滤口径下会触发入场的候选数：`837`。
- `layered_exit` 区间收益：`41.89%`；`SH000300`：`25.91%`；月度等权股票池：`20.84%`。
- 肥尾压力测试：baseline `41.89%`，剔除前 5 笔最大盈利后 `35.23%`。剔除前 5 笔最大盈利后仍为正收益，说明不是完全依赖少数单笔交易。

## 2. 验收问题回答

1. `layered_exit` 是否通过信号和成交对齐审计：通过。
2. `layered_exit` 是否能从交易明细反向核对：通过。
3. 行业过滤是否真实生效：当前 market_width 与 industry_theme_state 交易集仍完全一致；需要把该现象解释为行业过滤未改变最终交易，而不是证明行业过滤有效。
4. 低回撤是否稳定：`layered_exit` 低回撤仍成立，但肥尾压力测试显示：剔除前 5 笔最大盈利后仍为正收益，说明不是完全依赖少数单笔交易。
5. 相对基准是否有成本后优势：`layered_exit` 相对 `SH000300` 有优势，相对月度等权股票池 有优势。
6. 是否具备进入 Explore4 条件：可以进入，但必须保留静态股票池和肥尾依赖 caveat。

## 3. 文件索引

| File | Purpose |
| --- | --- |
| `signal_execution_audit.csv` | 信号日、订单日和成交日对齐审计 |
| `limit_skip_audit.csv` | 被跳过订单和涨跌停阻断明细 |
| `industry_filter_audit.csv` | 行业过滤候选与交易差异诊断 |
| `portfolio_reconciliation.csv` | 组合收益和交易明细核对 |
| `benchmark_comparison.csv` | 沪深300、月度等权、EMA baseline 和 layered_exit 对比 |
| `monthly_returns.csv` | 月度收益和相对沪深300超额 |
| `rolling_risk_report.csv` | 滚动收益、滚动回撤和最大回撤区间 |
| `fat_tail_stress.csv` | 剔除最大赢家后的重跑压力测试 |
| `group_stability.csv` | 分组交易稳定性统计 |
