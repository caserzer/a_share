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
- 可以读取 Explore1 的 Qlib provider 和 Explore3 已产出的只读诊断结果，但 Explore4 的回测、参数选择和报告必须完全独立重跑。
- 不得把 Explore4 产物写回 Explore1、Explore2 或 Explore3 的输出目录。
- 若复用 Explore3 代码，必须在 Explore4 中保留可复现入口和独立配置。
- 不得把 Explore3 的回测输出直接当作 Explore4 结果引用；最多只能作为来源说明、冻结版本校验或诊断背景。

## 3. 目标一：参数纪律重跑

### 3.1 冻结版本

Explore4 开始时必须冻结一个 `trend_rule_v1_frozen` 版本。该冻结版本是对 Explore3 候选框架的只读复制，用作 Explore4 独立重跑的输入基准；它属于 Explore3 规则框架冻结，不属于 Explore4 本次参数探索结果。

冻结版本必须记录：

- 来源配置。
- 来源报告。
- 配置 SHA256。
- 规则摘要。
- 已知偏差和 caveats。
- 是否来自已经观察过 2025-2026 测试区间的探索结果。

冻结版本用于后续对比，不允许继续用测试集表现反向修改。

必须产出冻结版本本身：

```text
Explore4/configs/trend_rule_v1_frozen.yaml
Explore4/outputs/reports/frozen_source_manifest.json
```

`frozen_source_manifest.json` 至少记录 Explore3 来源文件、来源 SHA256、冻结时间、Explore3 验证报告路径、是否已观察 2025-2026 区间，以及本次 Explore4 独立重跑入口。

### 3.2 时间切分

默认时间切分：

```text
train: 2017-01-01 到 2022-12-31
valid: 2023-01-01 到 2024-12-31
observed_test / frozen_replication: 2025-01-01 到 2026-04-30
observed_test executable end: 2026-04-29
```

2025-2026 区间已经在 Explore3 中被观察过，只能作为 `observed_test` / `frozen_replication`，不能再声明为真正未见样本外 test。Explore4 可以在该区间验证冻结规则是否能独立复现，但不能把该区间结果作为最终样本外证据。

真正的 `final_test` 只能来自后续新增行情日期，或在报告中显式降级为 observed-test 复现结论。若没有新增行情，`final_test_report.md` 必须写明：本轮没有真正未见 final test，最终结论仍是 frozen replication + valid selection。

若后续数据更新，必须在 manifest 中记录：

- 实际行情截止日。
- 实际可执行回测截止日。
- train / valid / observed_test / final_test 的实际起止日期。
- 与默认切分不一致的原因。

### 3.3 参数选择纪律

允许在 train / valid 中评估的参数必须按阶段进行，禁止把所有参数做全量笛卡尔积搜索。

搜索顺序固定为：

1. `frozen_replication`：不改任何参数，独立重跑 `trend_rule_v1_frozen`。
2. `risk_unit_stage`：只评估风险单位仓位，不改信号、过滤、入场和退出参数。
3. `industry_cap_stage`：在 `risk_unit_stage` 唯一入选版本基础上，只评估行业权重上限。
4. `optional_rule_stage`：只有前两阶段结论稳定且报告明确说明原因时，才允许做极小规模规则参数敏感性验证。

默认 Explore4 只做阶段 1 到阶段 3。阶段 4 不属于默认验收范围。

### 3.3.1 默认参数搜索空间

阶段 1：

- 组合数：`1`。
- 参数：完全等于 `trend_rule_v1_frozen`。

阶段 2：

| 参数 | 候选值 |
| --- | --- |
| `risk_budget_per_trade` | `0.5%`, `0.75%`, `1.0%` |
| `single_stock_max_weight` | `3%`, `5%`, `6%` |

阶段 2 最大组合数为 `9`。其他组合约束固定为：

```text
max_positions = 20
max_daily_new_weight = 20%
max_industry_weight = disabled
```

阶段 3：

| 参数 | 候选值 |
| --- | --- |
| `max_industry_weight` | `20%`, `25%`, `30%` |

阶段 3 只能基于阶段 2 唯一入选版本继续评估，最大组合数为 `3`。

默认总搜索组合数上限为 `13`，即 `1 + 9 + 3`。如果实现者增加任何组合，必须在报告中说明原因，并把超出默认上限后的结果降级为探索性敏感性分析。

阶段 4 如果启用，最多允许 `6` 个额外组合，并且只能从以下参数中选择不超过两个参数：

- 市场宽度阈值。
- trend_score top 分位阈值。
- 候选距离 EMA20 的上限。
- 突破成交额确认阈值。
- 回踩接近 EMA20 / EMA30 的容忍度。
- 时间止损天数。
- ATR trailing 倍数。
- 单票最大权重。
- 单日新增仓位上限。

阶段 4 禁止进入最终版本选择；只能报告敏感性，不得覆盖阶段 2 或阶段 3 的唯一选择。

必须遵守：

- 参数网格必须遵守上述组合数上限。
- valid 只用于按固定选择准则选择一组最终参数。
- observed_test 只允许用于冻结复现，不得用于选择参数。
- final_test 只有在存在新增未见数据时才允许最终评估一次。
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

唯一选择准则固定如下：

1. valid 最大回撤必须不差于 frozen fixed-weight 版本，或改善幅度为正。
2. valid 成本后收益必须为正。
3. valid 交易笔数不能低于 frozen fixed-weight 版本的 `70%`。
4. 在满足 1 到 3 的候选中，选择 `return_drawdown_ratio` 最高者。
5. 若 `return_drawdown_ratio` 差距小于 `0.10`，选择剔除前 5 笔最大盈利后收益更高者。
6. 若仍并列，选择换手率更低者。

该选择准则必须在运行前固定，并写入 `parameter_selection_report.md`。

## 4. 目标二：风险单位仓位

### 4.1 仓位逻辑

在固定权重版本之外，Explore4 必须实现风险单位仓位版本。

候选规则：

```text
entry_price = T+1 open
initial_stop = structure_or_atr_stop computed with T signal data and T+1 entry_price
initial_risk_per_share = entry_price - initial_stop
target_loss_per_trade = account_value * risk_budget_per_trade
raw_shares = target_loss_per_trade / initial_risk_per_share
raw_position_value = raw_shares * entry_price
target_position_value = min(raw_position_value, account_value * single_stock_max_weight)
```

仓位计算时间点：

- 信号日 `T` 收盘后决定是否生成订单。
- 成交日 `T+1` 使用开盘价计算 `entry_price`。
- `initial_stop` 使用 `T` 日可观察结构/ATR 数据，并结合 `T+1 open` 的 `entry_price` 计算。
- `account_value` 使用下单成交前的组合账户值。
- 同一交易日多笔新仓按排序顺序逐笔计算，现金和当日新增权重逐笔扣减。

### 4.2 约束和异常处理

必须处理：

- `initial_stop` 缺失、无效、非有限值时直接跳过交易，不使用 fallback。
- `initial_risk_per_share <= 0` 时不得开仓。
- 约束顺序固定为：单票最大权重 -> 单行业权重 -> 当日新增权重 -> 可用现金 -> 100 股整数手向下取整。
- 最大持仓数在进入仓位计算前检查，超过上限不得开仓。
- 剩余现金不足时按可用现金缩小订单；缩小后不足 100 股则跳过。
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

行业权重上限的解释边界：

- `max_industry_weight` 只使用当前 as-of SW2021 membership 做风险约束实验。
- 缺失行业归属的股票统一归入 `UNKNOWN` 行业。
- `UNKNOWN` 也必须参与行业权重上限约束。
- `industry_exposure_audit.csv` 必须单独输出每个交易日的行业暴露，包含 `UNKNOWN`。
- 行业 cap 只能解释为当前分类口径下的集中度约束实验，不能解释为历史真实行业暴露控制。

## 6. 产物要求

Explore4 至少应产出：

```text
Explore4/requirement.md
Explore4/configs/
Explore4/configs/trend_rule_v1_frozen.yaml
Explore4/scripts/
Explore4/outputs/reports/run_manifest.json
Explore4/outputs/reports/frozen_source_manifest.json
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
- 2025-2026 是否只作为 observed-test / frozen replication 使用。
- 若存在新增未见数据，最终 final_test 结果是否只评估一次；若不存在，是否明确说明没有真正 final_test。
- 风险单位仓位是否降低最大回撤或改善回撤稳定性。
- 止损交易的实际损失是否接近预设单笔风险预算。
- 行业权重上限是否降低集中度风险。
- 固定权重和风险单位仓位相比，收益、回撤、换手、成本和肥尾依赖如何变化。
- Explore4 是否完全独立重跑，而不是引用 Explore3 回测输出作为结果。
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
