# Explore3 扩展需求：结果验真与鲁棒性报告

## 1. 背景

`Explore3/reports/explore3_report.md` 已经完成规则版 EMA 趋势系统第一阶段实验。当前最有价值的结论不是 `layered_exit` 的绝对收益最高，而是它相对 `ema_state_only` 明显降低最大回撤，并改善交易质量。

但该结论仍属于探索性结果。进入新策略、新参数或模型搜索之前，Explore3 需要补一层结果验真和鲁棒性报告，确认当前结论不是由实现偏差、统计汇总错误、少数大盈利交易或过短测试窗口造成。

## 2. 扩展边界

本扩展仍属于 Explore3，不新建策略研究阶段。

必须遵守：

- 不改变 `Explore3/configs/trend_rule_v1.yaml` 中已评估的核心交易规则和参数。
- 不引入 Alpha360、LightGBM 或其他模型。
- 不重新发明股票池口径。
- 不用 2025-2026 测试结果反向调参。
- 不把本扩展产物写入 Explore1 或 Explore2。
- 可以增加验证脚本、诊断报表和补充报告。

## 3. 目标一：结果验真

### 3.1 信号、订单和成交对齐

必须验证：

- 所有入场信号只使用 `T` 日收盘后可观察数据。
- 实际买入发生在 `T+1` 交易日开盘。
- 所有退出信号只使用 `T` 日收盘后可观察数据。
- 实际卖出发生在 `T+1` 交易日开盘。
- 回测结束日前保留足够的下一个交易日用于成交和收益计算。
- 报告中明确列出 `signal_date`、`order_date`、`deal_date` 的对齐规则和抽样校验结果。

### 3.2 涨跌停和交易跳过

必须验证：

- 买入时若 `open >= prev_close * (1 + limit_threshold)`，订单被跳过。
- 卖出时若 `open <= prev_close * (1 - limit_threshold)`，订单被跳过。
- 被跳过的订单数量、日期、标的和后续处理方式需要输出明细。
- `limit_threshold=0.095` 只能用于主板近似，报告必须再次说明该假设依赖当前静态主板股票池。

### 3.3 行业过滤生效性

当前报告中 `market_width` 和 `industry_theme_state` 的组合结果完全一致，需要专门验证行业过滤是否真的改变了候选集或交易集。

必须输出：

- 每日 `width_ok_entry` 到 `industry_ok_entry` 的候选减少数量。
- 每日被行业过滤排除的股票数量和占比。
- 被行业过滤排除但后续满足入场触发的候选明细。
- `market_width` 与 `industry_theme_state` 的交易明细差异。
- 若两者结果一致，必须说明原因：例如行业过滤未在对应版本中参与交易、过滤后候选未改变最终交易、或实现存在遗漏。

### 3.4 组合收益和交易明细一致性

必须从交易明细反向核对组合结果：

- 每个版本的初始资金、现金、持仓市值、总资产逐日连贯。
- 成交成本、最小费用和买卖方向汇总正确。
- `trade_detail.csv` 能解释 `portfolio_daily.csv` 的主要收益变化。
- 强制期末平仓的交易需要和回测结束日规则一致。
- 报告中给出至少 `layered_exit`、`ema_state_only` 和 `market_width` 三个版本的核对结果。

## 4. 目标二：鲁棒性报告

### 4.1 基准补充

补充以下基准，不替代现有 ablation：

- `SH000300` 沪深300同期表现。
- `mcap500_mainboard_20251231` 股票池等权持有基准。
- `ema_state_only`。
- `layered_exit`。

基准必须使用同一回测窗口、同一数据截止约束和一致的成本口径。

### 4.2 时间维度稳定性

必须输出：

- 月度收益表。
- 月度超额收益表。
- 年度和部分年度收益表。
- 滚动最大回撤。
- 滚动 20/60/120 交易日收益。
- 最大回撤区间的起止日期、持续天数和恢复日期。

### 4.3 肥尾依赖检验

必须检查收益是否主要来自少数大盈利交易。

至少输出：

- 剔除最大 1 笔盈利交易后的组合收益和最大回撤。
- 剔除最大 3 笔盈利交易后的组合收益和最大回撤。
- 剔除最大 5 笔盈利交易后的组合收益和最大回撤。
- 剔除最大 10 笔盈利交易后的组合收益和最大回撤。
- 剔除贡献最大的 1/3/5 只股票后的组合收益和最大回撤。
- 大盈利交易贡献占总盈利比例。

若剔除少数交易后策略收益明显消失，报告必须把 `layered_exit` 结论降级为趋势捕捉结构有效但收益稳定性未验证。

### 4.4 分组稳定性

必须按以下维度输出交易层和组合层诊断：

- 年份：`2025`、`2026`。
- 入场类型：`breakout`、`pullback`。
- 退出类型：`stop_loss`、`time_stop`、`trailing_stop`、`ema60_exit`。
- 行业。
- 市场状态通过与不通过。
- 市场宽度通过与不通过。
- trend_score 分位数组。

每个分组至少包含：

- 交易笔数。
- 胜率。
- 平均净收益。
- 收益中位数。
- 最大单笔盈利。
- 最大单笔亏损。
- 平均持仓天数。
- 总净收益贡献。

## 5. 产物要求

新增或更新产物应落在 Explore3 内：

```text
Explore3/expand_requirement.md
Explore3/outputs/reports/explore3_verification_report.md
Explore3/outputs/reports/signal_execution_audit.csv
Explore3/outputs/reports/limit_skip_audit.csv
Explore3/outputs/reports/industry_filter_audit.csv
Explore3/outputs/reports/portfolio_reconciliation.csv
Explore3/outputs/reports/benchmark_comparison.csv
Explore3/outputs/reports/monthly_returns.csv
Explore3/outputs/reports/rolling_risk_report.csv
Explore3/outputs/reports/fat_tail_stress.csv
Explore3/outputs/reports/group_stability.csv
```

如果实现时需要新增脚本，脚本必须放在：

```text
Explore3/scripts/
```

## 6. 验收标准

本扩展完成后，报告必须能回答：

- 当前 `layered_exit` 结果是否通过信号和成交对齐审计。
- 当前 `layered_exit` 结果是否能从交易明细反向核对。
- 行业过滤在当前 ablation 中是否真实生效。
- `layered_exit` 的低回撤是否稳定存在，还是由少数交易或少数股票贡献。
- 相对沪深300和股票池等权基准，规则策略是否有成本后优势。
- 是否具备进入 Explore4 的条件。

进入 Explore4 的最低条件：

- 没有发现会推翻当前回测结论的实现错误。
- `layered_exit` 在剔除少数最大赢家后仍保留一定成本后优势，或报告能明确说明优势主要来自趋势尾部捕捉。
- 行业过滤是否生效已有明确解释。
- 参数没有基于测试区间继续调优。
