# Explore5 需求说明：两年滚动验证与 Regime Holdout

## 1. 背景

Explore4 发现单一 `train / valid / observed_test` 切分过于脆弱：

- `2023`、`2024`、`2025` 的市场风格差异显著。
- `2023-2024` 作为唯一 valid 会把参数选择推向过度保守和高现金。
- `2025-2026` 已经被 Explore3 / Explore4 观察过，只能作为 observed replication，不能再用于调参。
- pullback 在不同年份表现差异很大，不能简单判断为全局有效或全局无效。

Explore5 的核心问题改为：

```text
在不使用 2025-2026 调参的前提下，规则模块在 2017-2024 多个两年窗口和不同市场 regime 下是否具有稳定、可解释的适用边界？
```

Explore5 不再追求单一固定 valid 年份上的最优参数，而是评估：

- 哪些规则在多数时间窗口稳定。
- 哪些规则只在特定 regime 下有效。
- pullback 是否应条件启用。
- 风险单位仓位是否在不同 regime 下稳定降低回撤。

## 2. 与 Explore4 的关系

Explore5 继承 Explore4 的冻结规则、风险单位仓位和扩展诊断结论，但必须作为独立阶段管理。

必须遵守：

- Explore5 的配置、脚本、输出和报告必须落在 `Explore5` 目录下。
- 可以读取 Explore4 的冻结配置、诊断报告和只读 CSV 作为背景，但 Explore5 的回测、验证和报告必须独立重跑。
- 不得把 Explore4 的回测结果直接当作 Explore5 结果引用。
- 不得修改 Explore4 默认结果和扩展诊断产物。
- 不得使用 2025-2026 的结果做参数选择或规则筛选。
- 2025-2026 只能作为 `observed_replication`，且必须在报告中单独标记。

## 3. 数据契约与偏差边界

Explore5 默认复用 Explore4 / Explore1 的数据口径，但必须在 Explore5 自己的 manifest 和报告中重新声明并校验。

默认数据契约：

```text
provider_uri: Explore1/data/qlib/cn_data
market: mcap500_mainboard_20251231
benchmark: SH000300
data_start: 2017-01-01
data_end: 2026-04-30
required_fields: $open, $high, $low, $close, $volume, $money, $factor
```

股票池口径：

- 使用 Explore1 静态股票池 `mcap500_mainboard_20251231`。
- 股票池基准日为 `2025-12-31`，不是 point-in-time universe。
- 必须在报告中明确幸存者偏差和未来函数风险。
- Explore5 的结论只能解释为规则稳定性研究，不能解释为真实历史可投资业绩证明。

行业归属口径：

- 默认复用 Explore4 的 as-of SW2021 membership。
- 若股票缺失行业归属，统一归入 `UNKNOWN`。
- `UNKNOWN` 必须参与行业权重上限、行业暴露审计和 regime 分组。
- 若没有 point-in-time industry membership，行业同步和行业 cap 只能解释为当前分类口径下的诊断。

目标数据口径：

- 市场、行业、主题目标默认沿用 Explore4 冻结配置中的固定列表。
- 不得在 Explore5 中自动新增市场、行业或主题目标。
- 如果需要重新获取目标数据，Tushare 只用于市场、行业和主题指数目标；股票日线仍使用 Explore1 Qlib provider。
- Tushare token 只能从 topic 根目录 `.env` 或环境变量 `TUSHARE_TOKEN` 读取，不得写入命令行、日志、CSV、报告、manifest 或 git 追踪文件。

Explore5 运行前必须校验：

- provider 是否覆盖所有 fold 和 observed replication 日期。
- 所有 required fields 是否可读。
- market instrument 文件是否与股票池文件一致。
- Explore4 来源配置、来源诊断 CSV 和 Explore5 复制配置的 SHA256。
- 数据最大日期和可执行回测截止日期。

## 4. 时间切分

### 4.1 数据区间角色

默认区间：

```text
research_window: 2017-01-01 到 2024-12-31
observed_replication: 2025-01-01 到 2026-04-30
observed_replication_executable_end: 2026-04-29
future_final_test: 2026-04-30 之后新增行情
```

解释：

- `research_window` 用于滚动验证和 regime holdout。
- `observed_replication` 只用于冻结复现，不参与选择。
- `future_final_test` 只有在新增行情形成后才能启用。

### 4.2 两年滚动验证

Explore5 默认使用 expanding train + 2 年 valid，但默认候选版本不在 fold 内重新调参。

默认 folds：

| Fold | Train | Valid |
| --- | --- | --- |
| WF1 | 2017-01-01 到 2018-12-31 | 2019-01-01 到 2020-12-31 |
| WF2 | 2017-01-01 到 2019-12-31 | 2020-01-01 到 2021-12-31 |
| WF3 | 2017-01-01 到 2020-12-31 | 2021-01-01 到 2022-12-31 |
| WF4 | 2017-01-01 到 2021-12-31 | 2022-01-01 到 2023-12-31 |
| WF5 | 2017-01-01 到 2022-12-31 | 2023-01-01 到 2024-12-31 |

Train 的含义：

- 默认候选版本来自 Explore4 冻结配置或 Explore4 预定义诊断规则，Train 只用于 fold 元数据、可观察样本边界和后续可扩展的 train-derived 参数校验。
- 默认 Explore5 不允许在每个 Train 内重新选择阈值。
- 如果某个后续版本确实包含 train-derived 阈值，必须在每个 fold 的 Train 内独立推导，并写入 `fold_parameter_audit.csv`；该版本默认标记为 `exploratory`，不得进入本轮冻结选择。

Valid 的含义：

- Valid 窗口固定为两年，用于降低单一年份风格噪声。
- Fold 之间允许 valid 年份重叠，这是为了观察规则在连续风格切换中的稳定性。
- 重叠 valid 年份不视为独立样本。
- 报告必须同时输出 fold 维度和 distinct-calendar-year 维度结果。
- 所有选择准则必须优先使用 year-weighted 结果；fold 数量只能作为辅助稳定性诊断。
- 如果某个 fold 因数据不足无法运行，必须在 manifest 中记录原因。

### 4.3 Year-weighted 统计

为避免重叠 fold 重复计算同一年份，Explore5 必须生成 `year_metrics.csv`。

计算规则：

- 对每个 `version + calendar_year`，先汇总该年份在所有包含它的 valid folds 中的观测结果。
- 如果同一年份在多个 fold 中出现，先对该年份的 fold 实例取平均或按交易日加权汇总，再把该年份作为一个独立年份计数。
- `positive_valid_years`、`worst_year_drawdown`、`year_return_concentration` 必须基于 distinct calendar years 计算。
- 选择准则中若 fold 结论和 year-weighted 结论冲突，按更保守的 year-weighted 结论处理。

### 4.4 禁止事项

禁止：

- 把 2025-2026 放入任何 fold 的 train 或 valid。
- 看完 observed_replication 后修改 fold 定义。
- 只报告最好 fold，不报告最差 fold。
- 用单个 fold 的最佳结果形成最终版本。
- 用重叠 fold 数量替代 distinct-year 稳定性判断。

## 5. Regime Holdout

### 5.1 目标

Regime holdout 用于回答：

```text
策略模块在不同市场状态下的收益、回撤、失败类型是否稳定？
```

它不是新的参数搜索空间，而是稳定性诊断。

### 5.2 Regime 数据源

所有 regime 必须使用 T 日可观察数据，不得使用未来收益定义。

默认来源：

| Regime 字段 | 来源 |
| --- | --- |
| `close_gt_ema60_ratio` | `Explore5/outputs/reports/market_width.csv` 或独立重算的同口径表 |
| `ema20_gt_ema60_ratio` | `Explore5/outputs/reports/market_width.csv` 或独立重算的同口径表 |
| `broad_market close / ema60 / ema60_slope20` | `market_regime.csv` 中 `target_key = broad_market` |
| `industry_trend_ok` | `industry_regime.csv` 按 T 日和股票行业归属 join |
| `entry_type` | Explore5 独立交易明细 |
| `trend_score_pct` | Explore5 独立信号或交易明细 |
| `money_ratio20` | Explore5 独立信号或交易明细 |

### 5.3 Regime 定义

默认 regime 维度为闭合集合，不能在实现中自动新增。

1. 市场宽度：
   - `width_strong`: `close_gt_ema60_ratio > 0.60` 且 `ema20_gt_ema60_ratio > 0.50`
   - `width_neutral`: 不满足 `width_strong`，且满足 `close_gt_ema60_ratio > 0.55` 或 `ema20_gt_ema60_ratio > 0.45`
   - `width_weak`: `close_gt_ema60_ratio <= 0.55` 且 `ema20_gt_ema60_ratio <= 0.45`

2. 市场趋势：
   - `market_trend_on`: `broad_market close > EMA60` 且 `ema60_slope20 > 0`
   - `market_trend_off`: 不满足 `market_trend_on`

3. 行业同步：
   - `industry_sync_on`: 个股所属行业 T 日 `industry_trend_ok = true`
   - `industry_sync_off`: 个股所属行业 T 日 `industry_trend_ok = false` 或行业归属缺失

4. 信号类型：
   - `breakout`
   - `pullback`

5. Trend score 分位：
   - `top10`: `trend_score_pct <= 0.10`
   - `top10_20`: `0.10 < trend_score_pct <= 0.20`
   - `outside_top20`: `trend_score_pct > 0.20` 或缺失

6. 回踩成交额状态：
   - `pullback_money_weak`: `entry_type = pullback` 且 `0.60 <= money_ratio20 <= 1.00`
   - `pullback_money_other`: `entry_type = pullback` 且不满足 `pullback_money_weak`
   - `not_pullback`: `entry_type != pullback`

7. 组合 regime alias：
   - `pullback_top10_20`: `entry_type = pullback` 且 `0.10 < trend_score_pct <= 0.20`
   - `pullback`: `entry_type = pullback`

### 5.4 Regime Holdout 方式

Explore5 默认做两类 holdout：

1. Regime 分层报告：
   - 对每个 fold 的 valid 交易，按 regime 分组统计收益、回撤、交易数、胜率、失败退出。
   - 同时输出 distinct-year 维度的 regime 统计。

2. Regime leave-one-out：
   - 每次排除一个 regime 子集，重新运行完整组合回放。
   - 排除必须发生在 T 日信号资格判断阶段，不能在完成交易后过滤 trade rows。
   - 每个 holdout 必须重新计算订单、现金、持仓、行业 cap、风险预算、回撤和交易成本。
   - 默认只允许以下 holdout：
     - exclude `width_weak`
     - exclude `industry_sync_off`
     - exclude `pullback`
     - exclude `pullback_top10_20`
     - exclude `pullback_money_weak`

Regime holdout 版本必须标记为 `diagnostic_only`，不得直接形成最终冻结版本。

## 6. 候选规则和搜索纪律

Explore5 不做大规模参数搜索。

默认比较对象：

1. `frozen_fixed_weight`
   - Explore4 冻结规则的 fixed-weight 独立重跑。
   - 作为 `baseline`，用于所有 drawdown 和 stability 对比。

2. `risk_unit_with_industry_cap`
   - Explore4 当前 diagnostic fallback 口径的独立重跑。
   - 作为 `candidate_baseline`，只有在满足 Explore5 全部稳定性准则后，才允许报告为“可考虑冻结等待 future final_test 的候选”。
   - 即使满足准则，也必须保留 Explore4 中“valid 未满足原验收”的历史说明。

3. `breakout_only_diagnostic`
   - 关闭 pullback，仅用于评估 breakout 的跨 fold 稳定性。
   - 标记为 `diagnostic_only`，不得直接形成冻结版本。

4. `pullback_regime_gated_diagnostic`
   - 只允许一个预定义 gating 版本：
   ```text
   pullback 仅在 width_strong 且 industry_sync_on 且 trend_score_pct <= 0.10 时启用
   ```
   - 标记为 `diagnostic_only`，不得直接形成冻结版本。

限制：

- 默认最多 4 个版本。
- 所有版本必须跑完整 walk-forward folds。
- 不允许新增笛卡尔积参数搜索。
- 若新增任何版本，必须降级为 `exploratory`，并且不能进入最终选择。
- `diagnostic_only` 和 `exploratory` 版本即使表现最好，也只能形成后续研究建议，不能覆盖本轮候选选择。

## 7. 选择准则

Explore5 的目标不是选出收益最高版本，而是判断是否存在“可冻结等待未来 final test”的稳定候选。

### 7.1 可进入冻结判断的版本

只有 `candidate_baseline` 版本可以进入 Explore5 冻结判断。

- `baseline` 只作为对比基线。
- `diagnostic_only` 只回答规则边界问题。
- `exploratory` 只作为后续研究建议。

若没有 `candidate_baseline` 满足准则，报告必须写明：

```text
没有形成 Explore5 冻结版本
```

### 7.2 固定选择阈值

候选版本必须同时满足：

1. `qualified_valid_years >= 4`，其中 `qualified_valid_years = positive_valid_years + min(controlled_flat_years, 1)`。
2. `positive_valid_years >= 3`，其中 positive year 定义为该 calendar year 的成本后收益 `> 0`。
3. `controlled_flat_year` 定义为该年成本后收益 `>= -0.5%`，且最大回撤绝对值相对同年 `frozen_fixed_weight` 至少降低 `10%`。
4. `worst_year_drawdown` 不得比同年 `frozen_fixed_weight` 更差超过 `1.0` 个百分点。
5. `worst_fold_drawdown` 不得比同 fold `frozen_fixed_weight` 更差超过 `1.0` 个百分点。
6. 任一 fold 不得贡献超过全部正收益 fold PnL 的 `60%`。
7. 任一 distinct calendar year 不得贡献超过全部正收益 year PnL 的 `45%`。
8. 交易笔数不得低于 `frozen_fixed_weight` 同期交易笔数的 `50%`，否则稳定性结论降级为样本不足。
9. `observed_replication` 不参与任何选择字段。

### 7.3 Pullback 相关约束

包含 pullback 的候选版本还必须满足：

- `width_weak` regime 的成本后收益 `>= -0.5%`，或规则在该 regime 下明确关闭 pullback 且交易数为 0。
- `industry_sync_off` regime 的成本后收益 `>= -0.5%`，或规则在该 regime 下明确关闭 pullback 且交易数为 0。
- `pullback_top10_20` 和 `pullback_money_weak` 必须单独报告交易数、成本后收益和失败退出类型。

若 pullback 只在 diagnostic gating 后改善，结论应写为：

```text
pullback 可能需要 regime gating，但本轮没有形成可直接冻结的 pullback 新规则
```

## 8. 产物要求

Explore5 至少产出：

```text
Explore5/requirement.md
Explore5/configs/
Explore5/configs/walk_forward_v1.yaml
Explore5/scripts/
Explore5/outputs/reports/run_manifest.json
Explore5/outputs/reports/data_quality_report.csv
Explore5/outputs/reports/provider_coverage_report.csv
Explore5/outputs/reports/walk_forward_summary.csv
Explore5/outputs/reports/fold_metrics.csv
Explore5/outputs/reports/year_metrics.csv
Explore5/outputs/reports/fold_trade_detail.csv
Explore5/outputs/reports/fold_portfolio_daily.csv
Explore5/outputs/reports/fold_execution_audit.csv
Explore5/outputs/reports/fold_risk_budget_audit.csv
Explore5/outputs/reports/fold_industry_exposure_audit.csv
Explore5/outputs/reports/regime_attribution.csv
Explore5/outputs/reports/regime_holdout_summary.csv
Explore5/outputs/reports/observed_replication_summary.csv
Explore5/outputs/reports/walk_forward_report.md
Explore5/outputs/reports/regime_holdout_report.md
Explore5/outputs/reports/explore5_final_report.md
```

如果启用任何 train-derived 阈值版本，还必须产出：

```text
Explore5/outputs/reports/fold_parameter_audit.csv
```

`run_manifest.json` 至少记录：

- 来源 Explore4 配置、诊断 CSV、报告路径和 SHA256。
- Explore5 配置路径和 SHA256。
- provider_uri、market、benchmark、required_fields。
- universe source、universe as-of date、是否 point-in-time。
- 行业 membership 来源、是否 point-in-time、缺失行业处理方式。
- 数据最大日期、observed replication 可执行截止日期。
- fold 定义、可执行状态和跳过原因。
- regime 定义和阈值。
- 候选版本列表、候选类型、是否可进入冻结判断。
- regime leave-one-out 是否使用 full portfolio replay，必须为 `true`。
- `observed_replication_used_for_selection`，必须为 `false`。
- 是否形成 Explore5 冻结版本。
- 若形成冻结版本，记录冻结版本路径和 SHA256。

## 9. 报告必须回答的问题

Explore5 最终报告必须回答：

- 单一 `train / valid / test` 为什么不适合当前研究阶段。
- 两年 rolling valid 下，各候选版本是否稳定。
- 重叠 fold 是否改变判断，year-weighted 结论是否更保守。
- 哪些 fold 和哪些 calendar year 是失败区间，失败是否集中在特定年份或风格。
- pullback 的问题是否主要来自 `width_weak`、`industry_sync_off`、`top10_20`、还是成交额弱回踩。
- breakout 是否在多数 fold 和多数 distinct years 中保持正贡献。
- risk-unit 和 industry cap 是否跨 fold 稳定降低回撤。
- diagnostic-only 版本是否只是定位问题，还是足以支持后续重新冻结需求。
- 是否存在可冻结等待 future final_test 的版本。
- 若不存在，下一步应继续做规则诊断还是转向数据 / universe / point-in-time 修复。

## 10. 测试计划

静态检查：

```text
uv run python -m compileall Explore5/scripts
uv run python Explore5/scripts/run_explore5.py self-test
```

产物生成：

```text
uv run python Explore5/scripts/run_explore5.py all --config Explore5/configs/walk_forward_v1.yaml
```

内容验收：

- `data_quality_report.csv` 和 `provider_coverage_report.csv` 必须存在且覆盖所有 required fields。
- `fold_metrics.csv` 至少包含 5 个 folds。
- `year_metrics.csv` 必须覆盖 `2019` 到 `2024` 的 distinct calendar years。
- 每个默认版本必须覆盖所有可执行 folds。
- `walk_forward_summary.csv` 必须包含 best fold、worst fold、positive_valid_years、controlled_flat_years、qualified_valid_years、worst_year_drawdown、worst_fold_drawdown、fold_return_concentration、year_return_concentration。
- `regime_attribution.csv` 必须按 fold、year、version、regime 维度输出。
- `regime_holdout_summary.csv` 必须记录每个 holdout 是否使用 full portfolio replay。
- `fold_portfolio_daily.csv` 必须能复算最大回撤。
- `fold_execution_audit.csv` 必须验证 signal date、order date、deal date 对齐。
- `fold_risk_budget_audit.csv` 必须能检查风险单位仓位和实际亏损关系。
- `fold_industry_exposure_audit.csv` 必须包含 `UNKNOWN` 行业。
- `observed_replication_summary.csv` 必须存在，但任何选择字段不得使用它。
- `run_manifest.json` 中 `observed_replication_used_for_selection` 必须为 `false`。
- `run_manifest.json` 中 `regime_holdout_full_replay` 必须为 `true`。
- 若没有满足选择准则的候选，`explore5_final_report.md` 必须明确写“没有形成 Explore5 冻结版本”。

## 11. 后续边界

Explore5 完成前不得进入 meta-labeling。

只有当 Explore5 形成稳定冻结版本，且后续出现 `2026-04-30` 之后至少 20 个可执行交易日，才允许开启真正 final test。

如果 Explore5 只得到 diagnostic-only 的改善结论，下一步应先整理新的冻结规则需求，再等待 future final_test；不得直接把 diagnostic-only 版本当作 final test 候选。
