# Explore4 需求说明：参数纪律重跑与风险单位仓位验证

## 1. 背景

Explore3 第一阶段已经完成规则版 EMA 趋势策略和分层 ablation。下一步不应直接进入大规模模型搜索，而应先把策略研究从“看过测试结果后的探索”推进到更严格的参数纪律和组合风险控制验证。

Explore4 的核心问题：

```text
在冻结 Explore3 规则框架后，若参数选择只允许发生在 train / valid 区间，
并加入基于初始止损距离的风险单位仓位，策略是否仍能保持可解释的成本后优势和更可控的回撤？
```

## 2. 与 Explore3 的关系

Explore4 继承 Explore3 的研究方向，但必须作为独立阶段管理。

必须遵守：

- Explore3 的 `layered_exit` 作为当前候选框架，不直接视为最终策略。
- Explore4 的配置、脚本、输出和报告必须落在 `Explore4` 目录下。
- 可以读取 Explore1 的 Qlib provider 和 Explore3 已产出的只读诊断结果。
- 不得把 Explore4 产物写回 Explore1、Explore2 或 Explore3 的输出目录。
- 若复用 Explore3 代码，必须在 Explore4 中保留可复现入口和独立配置。

## 3. 目标一：参数纪律重跑

### 3.1 冻结版本

Explore4 开始时必须冻结一个 `trend_rule_v1_frozen` 版本，记录：

- 来源配置。
- 来源报告。
- 配置 SHA256。
- 规则摘要。
- 已知偏差和 caveats。
- 是否来自已经观察过 2025-2026 测试区间的探索结果。

冻结版本用于后续对比，不允许继续用测试集表现反向修改。

### 3.2 时间切分

默认时间切分：

```text
train: 2017-01-01 到 2022-12-31
valid: 2023-01-01 到 2024-12-31
test:  2025-01-01 到 2026-04-30
backtest executable end: 2026-04-29
```

若后续数据更新，必须在 manifest 中记录：

- 实际行情截止日。
- 实际可执行回测截止日。
- train / valid / test 的实际起止日期。
- 与默认切分不一致的原因。

### 3.3 参数选择纪律

允许在 train / valid 中评估的参数包括：

- 市场宽度阈值。
- trend_score top 分位阈值。
- 候选距离 EMA20 的上限。
- 突破成交额确认阈值。
- 回踩接近 EMA20 / EMA30 的容忍度。
- 时间止损天数。
- ATR trailing 倍数。
- 单票最大权重。
- 单日新增仓位上限。

必须遵守：

- 参数网格要小，优先使用规则先验和少量候选值。
- valid 只用于选择一组最终参数。
- test 只允许最终评估一次。
- 如果根据 test 结果继续修改参数，报告必须显式把结论降级为探索性。
- 所有参数候选、选择过程和最终版本必须写入 manifest。

### 3.4 参数选择指标

参数选择不能只看总收益。

valid 选择应综合：

- 成本后收益。
- 最大回撤。
- 收益回撤比。
- 月度收益稳定性。
- 交易笔数是否足够。
- 剔除最大赢家后的收益保留情况。
- 换手和成本占比。

若收益和风险指标冲突，优先选择回撤更可控、肥尾依赖更低的版本。

## 4. 目标二：风险单位仓位

### 4.1 仓位逻辑

在固定权重版本之外，Explore4 必须实现风险单位仓位版本。

候选规则：

```text
initial_risk_per_share = entry_price - initial_stop
target_loss_per_trade = account_value * risk_budget_per_trade
raw_shares = target_loss_per_trade / initial_risk_per_share
target_weight = min(raw_position_value / account_value, single_stock_max_weight)
```

基础候选值：

| 参数 | 候选值 |
| --- | --- |
| `risk_budget_per_trade` | `0.5%`, `0.75%`, `1.0%` |
| `single_stock_max_weight` | `3%`, `5%`, `6%` |
| `max_positions` | `15`, `20`, `30` |
| `max_daily_new_weight` | `10%`, `15%`, `20%` |
| `max_industry_weight` | `20%`, `25%`, `30%` |

### 4.2 约束和异常处理

必须处理：

- `initial_stop` 缺失或无效时不得使用风险单位仓位，应跳过交易或使用明确 fallback。
- `initial_risk_per_share <= 0` 时不得开仓。
- 买入股数必须按 100 股整数手向下取整。
- 单票权重、单行业权重、最大持仓数、单日新增权重必须同时满足。
- 剩余现金不足时按可用现金缩小订单。
- 不能因为风险单位仓位让单只低风险股票获得异常大仓位。

### 4.3 对比实验

至少比较：

- `fixed_weight_layered_exit`：Explore3 固定权重版本。
- `risk_unit_layered_exit`：同规则，仅改变仓位逻辑。
- `risk_unit_with_industry_cap`：风险单位仓位加行业权重上限。

每个版本必须输出：

- 成本前收益。
- 成本后收益。
- 年化收益。
- 最大回撤。
- 收益回撤比。
- 月度收益。
- 平均持仓数。
- 平均现金比例。
- 换手率。
- 成本占比。
- 最大单票权重。
- 最大行业权重。
- 止损交易的实际亏损是否接近风险预算。

## 5. 数据和偏差处理

Explore4 仍可复用 Explore1 的 Qlib provider，但报告必须保持以下风险提示：

- 当前股票池不是 point-in-time universe。
- 当前股票池存在幸存者偏差和未来函数风险。
- SW2021 行业归属若仍使用单一 as-of membership，不得解释为历史可投资行业归属。
- 若没有 point-in-time universe 和 point-in-time industry membership，Explore4 仍是研究验证，不是可直接实盘的历史业绩证明。

## 6. 产物要求

Explore4 至少应产出：

```text
Explore4/requirement.md
Explore4/configs/
Explore4/scripts/
Explore4/outputs/reports/run_manifest.json
Explore4/outputs/reports/parameter_selection_report.md
Explore4/outputs/reports/risk_unit_sizing_report.md
Explore4/outputs/reports/final_test_report.md
Explore4/outputs/reports/parameter_grid_summary.csv
Explore4/outputs/reports/valid_selection_summary.csv
Explore4/outputs/reports/test_result_summary.csv
Explore4/outputs/reports/risk_budget_audit.csv
Explore4/outputs/reports/industry_exposure_audit.csv
```

## 7. 验收标准

Explore4 完成后必须回答：

- 在 train / valid 参数纪律下，冻结规则是否仍有稳定成本后优势。
- 最终 test 结果是否只评估一次。
- 风险单位仓位是否降低最大回撤或改善回撤稳定性。
- 止损交易的实际损失是否接近预设单笔风险预算。
- 行业权重上限是否降低集中度风险。
- 固定权重和风险单位仓位相比，收益、回撤、换手、成本和肥尾依赖如何变化。
- 是否值得进入后续 meta-labeling 阶段。

## 8. 后续扩展：Meta-labeling

Meta-labeling 只能在 Explore4 验收通过后启动，不能替代当前规则系统。

后续研究问题：

```text
在 EMA 候选、市场过滤、行业过滤和入场触发已经确定的前提下，
模型能否判断某个候选交易是否具有足够的未来 R 调整收益，从而提升交易筛选质量？
```

建议边界：

- 模型只做候选交易过滤或排序，不直接生成全市场买入信号。
- 标签应围绕未来 R 倍数、先触发止盈还是止损、20/40/60 日成本后收益构造。
- 特征必须只使用信号日可观察数据。
- 训练和验证必须沿用 Explore4 的参数纪律。
- 初版优先使用简单模型，例如 LightGBM 或 logistic regression，不做大规模模型搜索。
- 必须与无模型的 `risk_unit_layered_exit` 对比。

后续验收重点：

- 模型是否减少亏损交易，而不是只减少交易数量。
- 模型是否改善剔除最大赢家后的收益稳定性。
- 模型是否在 valid 和 test 上方向一致。
- 模型特征是否存在未来函数。
- 模型收益是否能覆盖额外复杂度和过拟合风险。
