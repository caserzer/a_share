# Explore5 详细综合报告：两年滚动验证与状态保留检验

## 1. 核心结论

- 结论：`没有形成 Explore5 冻结版本`。
- `risk_unit_with_industry_cap` 是唯一允许进入冻结判断的 `candidate_baseline`，但只获得 `1` 个 distinct positive year，`qualified_valid_years = 1`，明显低于需求中的 `4` 年门槛。
- 风险单位仓位和行业上限确实降低了回撤和集中度，但没有把 2019-2024 的 year-weighted 收益稳定转正；它更像风险控制改良，不是足够稳定的 alpha 改良。
- `breakout_only_diagnostic` 和 `pullback_regime_gated_diagnostic` 的回撤明显更低，但都属于 `diagnostic_only`，而且现金比例很高、交易数下降明显，不能直接形成冻结版本。
- 状态保留检验最强的信号是：排除 pullback 相关交易会显著改善研究窗口，但改善主要来自减少亏损交易和提高现金，而不是证明 breakout 子系统已经足够完整。
- 2025-2026 已观察区间复现表现很好，但它已被 Explore3 / Explore4 观察过，本轮没有、也不应把它用于选择。

## 2. 实验边界和数据约束

- 数据源：`Explore1/data/qlib/cn_data`，股票池为 `mcap500_mainboard_20251231`。
- 股票池是 `2025-12-31` 静态宇宙，不是时点股票池；因此所有结论只能解释为规则稳定性和诊断，不是历史可实盘收益证明。
- 行业归属沿用 Explore4 的 as-of SW2021 membership，不是时点行业归属；行业同步和行业 cap 只能解释为当前分类口径下的研究结论。
- 研究窗口为 2019-2024 的 overlapping two-year valid folds；选择判断优先看 distinct-year 统计，避免重复年份被 fold 重叠放大。
- 2025-2026 只作为已观察区间复现，`used_for_selection = false`。

### 2.1 数据质量和覆盖

| 项目 | 状态 | 路径 |
| --- | --- | --- |
| provider_uri | ok | Explore1/data/qlib/cn_data |
| universe_csv | ok | Explore5/data/universe/mcap500_mainboard_20251231.csv |
| universe_qlib | ok | Explore5/data/universe/qlib_mcap500_mainboard_20251231.txt |
| target_history | ok | Explore5/data/targets/target_history.csv |
| source_explore4_config | ok | Explore4/configs/trend_rule_v1_frozen.yaml |
| static_universe_bias | not_point_in_time | Explore1/data/universe/mcap500_mainboard_20251231.csv |

| 字段 | 存在 | 有效行数 | 缺失行数 | 最早日期 | 最晚日期 |
| --- | --- | --- | --- | --- | --- |
| open | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| high | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| low | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| close | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| volume | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| money | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |
| factor | True | 594,792 | 4,740 | 2017-01-03 | 2026-04-30 |

## 3. 滚动验证稳定性总览

选择准则要求候选版本至少达到 `qualified_valid_years >= 4` 且 `positive_valid_years >= 3`。从结果看，没有任何可冻结候选接近该门槛。

| 版本 | 类型 | 正收益年份 | 受控持平年份 | 合格年份 | 最差年度回撤 | 年度收益集中度 | 是否冻结 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `frozen_fixed_weight` (固定权重基线) | 基线 | 0 | 0 | 0 | -11.66% | NA | False |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | 候选基线 | 1 | 0 | 1 | -7.31% | 100.00% | False |
| `breakout_only_diagnostic` (只保留突破诊断) | 仅诊断 | 2 | 1 | 3 | -3.35% | 79.31% | False |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | 仅诊断 | 2 | 0 | 2 | -5.66% | 89.14% | False |

解读：

- 固定权重基线在 2019-2024 没有任何 positive year，说明 Explore4 之前看到的 valid 脆弱性并不是偶然。
- `risk_unit_with_industry_cap` 把最差年度回撤从固定权重的约 `-11.66%` 降到约 `-7.31%`，但 `positive_valid_years` 只有 `1`，收益稳定性没有达标。
- `breakout_only_diagnostic` 的 `qualified_valid_years = 3`，接近但仍未达到 4 年门槛；更重要的是它不是可冻结候选，且交易覆盖不足。
- `pullback_regime_gated_diagnostic` 证明强 regime gating 能缓解 pullback 问题，但收益高度集中，year return concentration 达到 `89%` 左右，不能视为稳定规则。

## 4. 滚动窗口维度结果

下表每个单元为 `成本后收益 / 最大回撤`。

| 滚动窗口 | 固定权重 | 风险单位+行业上限 | 只保留突破 | 强状态回踩门控 |
| --- | --- | --- | --- | --- |
| WF1 | -6.96% / -18.81% | -5.22% / -12.14% | -1.17% / -5.20% | -1.91% / -9.11% |
| WF2 | -3.58% / -10.06% | -3.72% / -6.40% | 1.18% / -2.09% | 0.23% / -3.74% |
| WF3 | -8.30% / -10.38% | -4.89% / -6.39% | -1.78% / -2.02% | -2.33% / -3.32% |
| WF4 | -3.30% / -5.14% | -1.85% / -3.24% | 0.91% / -1.13% | 0.12% / -1.62% |
| WF5 | -4.76% / -12.05% | -2.47% / -7.33% | 0.42% / -2.62% | 0.06% / -3.34% |

解读：

- `risk_unit_with_industry_cap` 在每个 fold 的回撤都优于固定权重，但 5 个 fold 的收益全部为负。
- `breakout_only_diagnostic` 在 WF2、WF4、WF5 为正，但 WF1、WF3 为负；这说明 breakout 更干净，但并不跨周期稳定。
- `pullback_regime_gated_diagnostic` 在 WF2、WF4、WF5 略正，但正收益幅度很薄，且 WF1 / WF3 仍明显亏损。
- WF1 和 WF3 是失败最明显的窗口。它们覆盖 2019、2021-2022 的风格变化，对趋势规则和回踩规则都不友好。

## 5. 独立年份结果

下表每个单元为 `年度成本后收益 / 年内最大回撤`。同一年在多个 overlapping folds 中出现时，先聚合为一个 distinct-year 结果。

| 年份 | 固定权重 | 风险单位+行业上限 | 只保留突破 | 强 regime 回踩 gating |
| --- | --- | --- | --- | --- |
| 2019 | -4.51% / -10.96% | -2.80% / -7.01% | -0.92% / -3.35% | -1.29% / -5.66% |
| 2020 | -1.52% / -11.62% | -2.25% / -7.31% | 0.51% / -2.50% | 0.15% / -4.30% |
| 2021 | -3.44% / -6.28% | -1.97% / -3.50% | -0.34% / -1.28% | -0.87% / -1.94% |
| 2022 | -3.95% / -4.87% | -2.30% / -2.87% | -1.12% / -1.24% | -1.20% / -1.32% |
| 2023 | -0.05% / -5.14% | 0.05% / -3.26% | 1.97% / -1.08% | 1.25% / -1.64% |
| 2024 | -4.77% / -11.66% | -2.58% / -6.85% | -1.55% / -2.39% | -1.20% / -3.09% |

解读：

- 2023 是唯一对大多数版本相对友好的年份；这也解释了为什么单一 `2023-2024 valid` 容易给出过于乐观或过于保守的片面判断。
- 2024 对固定权重和风险单位版本都很差，说明规则仍然无法处理部分趋势衰减或假突破环境。
- `breakout_only_diagnostic` 的正收益年份只有 2020 和 2023，且 2023 贡献过大；这不是稳定 alpha，而是少数年份驱动。
- `risk_unit_with_industry_cap` 只在 2023 略微转正，其他 5 个 distinct years 均为负，不满足冻结条件。

## 6. 状态保留检验复盘

所有 holdout 都是在 T 日信号资格阶段排除，并重新运行完整组合回放；不是事后过滤交易明细。

### 6.1 状态排除检验绝对表现

| 排除项 | 平均收益 | 最差收益 | 平均回撤 | 平均交易数 |
| --- | --- | --- | --- | --- |
| pullback | -0.09% | -1.78% | -2.61% | 28.0 |
| pullback_money_weak | -0.28% | -2.30% | -3.50% | 48.2 |
| pullback_top10_20 | -1.69% | -3.34% | -4.88% | 66.4 |
| industry_sync_off | -3.63% | -5.22% | -7.10% | 110.4 |
| width_weak | -3.63% | -5.22% | -7.10% | 110.4 |

### 6.2 相对 `risk_unit_with_industry_cap` 的变化

| 排除项 | 平均收益改善 | 最小改善 | 最大改善 | 平均回撤改善 | 平均交易变化 |
| --- | --- | --- | --- | --- | --- |
| pullback | 3.54% | 2.77% | 4.90% | 4.49% | -82.4 |
| pullback_money_weak | 3.35% | 2.45% | 5.80% | 3.60% | -62.2 |
| pullback_top10_20 | 1.94% | 1.42% | 2.63% | 2.21% | -44.0 |
| industry_sync_off | 0.00% | 0.00% | 0.00% | 0.00% | 0.0 |
| width_weak | 0.00% | 0.00% | 0.00% | 0.00% | 0.0 |

解读：

- `exclude_pullback` 的平均收益改善最大，约 `+3.54%`，平均回撤也显著改善，但平均少做约 `82` 笔交易。这说明 pullback 是主要亏损来源，但关闭 pullback 也让组合更接近低暴露状态。
- `exclude_pullback_money_weak` 平均改善约 `+3.35%`，说明成交额较弱的回踩是很重要的负贡献来源。
- `exclude_pullback_top10_20` 平均改善约 `+1.94%`，说明 trend_score 的 top10_20 区间质量不足，当前排序没有充分区分高质量回踩和弱反弹。
- `exclude_width_weak` 和 `exclude_industry_sync_off` 对结果几乎没有影响，说明当前基础规则已经基本不会在这些 regime 下开仓；问题不在弱市硬过滤缺失，而在通过过滤后的 pullback 质量仍然不足。

## 7. 交易级归因

### 7.1 入场类型

| 版本 | 入场类型 | 交易数 | 净 PnL | 平均单笔收益 | 胜率 |
| --- | --- | --- | --- | --- | --- |
| `breakout_only_diagnostic` (只保留突破诊断) | breakout | 140 | -4,673 | 0.36% | 23.57% |
| `frozen_fixed_weight` (固定权重基线) | pullback | 447 | -293,012 | -1.37% | 25.28% |
| `frozen_fixed_weight` (固定权重基线) | breakout | 112 | 20,945 | 0.71% | 23.21% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | pullback | 176 | -44,131 | -0.75% | 32.95% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | breakout | 127 | 5,090 | 0.68% | 23.62% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | pullback | 442 | -192,249 | -1.36% | 25.11% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | breakout | 110 | 8,818 | 0.88% | 22.73% |

解读：

- 在固定权重版本中，pullback 净亏损约 `-293,012`，breakout 净盈利约 `20,945`。
- 在风险单位 + 行业上限版本中，pullback 净亏损仍约 `-192,249`，breakout 净盈利约 `8,818`。仓位控制降低了亏损幅度，但没有改变 pullback 的负期望。
- 强 regime gating 后，pullback 净亏损收窄到约 `-44,131`，但仍为负；它是方向正确的诊断，不是可冻结规则。
- `breakout_only_diagnostic` 交易数很少，总体净 PnL 略负；这提醒我们不能简单说“只做 breakout 就够了”，因为低交易数和高现金会让结果对少数交易高度敏感。

### 7.2 退出类型

| 版本 | 退出原因 | 交易数 | 净 PnL | 平均单笔收益 |
| --- | --- | --- | --- | --- |
| `breakout_only_diagnostic` (只保留突破诊断) | time_stop | 98 | -114,063 | -4.30% |
| `breakout_only_diagnostic` (只保留突破诊断) | stop_loss | 2 | -12,118 | -20.68% |
| `breakout_only_diagnostic` (只保留突破诊断) | ema60_exit | 14 | -10,493 | -2.29% |
| `breakout_only_diagnostic` (只保留突破诊断) | end_of_backtest | 4 | 6,871 | 11.95% |
| `breakout_only_diagnostic` (只保留突破诊断) | trailing_stop | 22 | 125,130 | 22.61% |
| `frozen_fixed_weight` (固定权重基线) | stop_loss | 147 | -464,102 | -7.13% |
| `frozen_fixed_weight` (固定权重基线) | time_stop | 203 | -325,782 | -3.58% |
| `frozen_fixed_weight` (固定权重基线) | ema60_exit | 16 | -37,986 | -6.40% |
| `frozen_fixed_weight` (固定权重基线) | end_of_backtest | 24 | 65,308 | 7.44% |
| `frozen_fixed_weight` (固定权重基线) | trailing_stop | 169 | 490,494 | 6.88% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | time_stop | 135 | -152,154 | -4.08% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | stop_loss | 48 | -114,179 | -8.15% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | ema60_exit | 13 | -11,333 | -2.72% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | end_of_backtest | 13 | 14,513 | 5.70% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | trailing_stop | 94 | 224,112 | 9.13% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | stop_loss | 148 | -295,297 | -7.08% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | time_stop | 202 | -193,629 | -3.60% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | ema60_exit | 14 | -21,683 | -5.29% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | end_of_backtest | 24 | 37,735 | 7.44% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | trailing_stop | 164 | 289,444 | 7.11% |

解读：

- 所有版本的亏损主要来自 `stop_loss` 和 `time_stop`，盈利主要来自 `trailing_stop`。
- 风险单位仓位能压低 `stop_loss` 和 `time_stop` 的绝对损失，但无法阻止失败交易数量累积。
- 当前系统不是完全抓不到趋势，而是失败交易识别太晚：亏损交易进入后，靠 stop/time_stop 才被动退出。
- 下一步如果继续规则诊断，应优先研究入场前的失败识别，而不是先改 trailing stop。

## 8. 状态归因

### 8.1 单滚动窗口 / 年份最大亏损分组

| 滚动窗口 | 年份 | 版本 | 维度 | 状态 | 交易数 | 净 PnL | 收益贡献 | 回撤代理 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | industry_sync | industry_sync_on | 73 | -64,813 | -6.48% | -7.24% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | market_trend | market_trend_on | 73 | -64,813 | -6.48% | -7.24% |
| WF3 | 2021 | `frozen_fixed_weight` (固定权重基线) | market_trend | market_trend_on | 30 | -51,702 | -5.17% | -4.82% |
| WF3 | 2021 | `frozen_fixed_weight` (固定权重基线) | industry_sync | industry_sync_on | 30 | -51,702 | -5.17% | -4.82% |
| WF5 | 2024 | `frozen_fixed_weight` (固定权重基线) | industry_sync | industry_sync_on | 138 | -50,255 | -5.03% | -7.68% |
| WF5 | 2024 | `frozen_fixed_weight` (固定权重基线) | market_trend | market_trend_on | 138 | -50,255 | -5.03% | -7.68% |
| WF5 | 2024 | `frozen_fixed_weight` (固定权重基线) | trend_score | top10_20 | 86 | -48,938 | -4.89% | -7.01% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | trend_score | top10_20 | 41 | -48,213 | -4.82% | -5.63% |
| WF5 | 2024 | `frozen_fixed_weight` (固定权重基线) | width | width_strong | 132 | -48,173 | -4.82% | -7.47% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | entry_type | pullback | 56 | -47,334 | -4.73% | -5.50% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | width | width_strong | 60 | -44,492 | -4.45% | -5.87% |
| WF2 | 2021 | `frozen_fixed_weight` (固定权重基线) | market_trend | market_trend_on | 25 | -41,716 | -4.17% | -3.82% |
| WF2 | 2021 | `frozen_fixed_weight` (固定权重基线) | industry_sync | industry_sync_on | 25 | -41,716 | -4.17% | -3.82% |
| WF1 | 2019 | `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | market_trend | market_trend_on | 72 | -40,658 | -4.07% | -4.55% |
| WF1 | 2019 | `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | industry_sync | industry_sync_on | 72 | -40,658 | -4.07% | -4.55% |
| WF1 | 2020 | `frozen_fixed_weight` (固定权重基线) | pullback_money | pullback_money_weak | 60 | -39,505 | -3.95% | -7.28% |
| WF1 | 2020 | `frozen_fixed_weight` (固定权重基线) | alias | pullback_money_weak | 60 | -39,505 | -3.95% | -7.28% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | alias | pullback_money_weak | 48 | -38,808 | -3.88% | -4.64% |
| WF1 | 2019 | `frozen_fixed_weight` (固定权重基线) | pullback_money | pullback_money_weak | 48 | -38,808 | -3.88% | -4.64% |
| WF5 | 2024 | `frozen_fixed_weight` (固定权重基线) | alias | pullback_top10_20 | 74 | -37,680 | -3.77% | -6.15% |

### 8.2 跨滚动窗口聚合亏损分组

| 版本 | 维度 | 状态 | 交易数 | 净 PnL | 平均收益贡献 |
| --- | --- | --- | --- | --- | --- |
| `frozen_fixed_weight` (固定权重基线) | entry_type | pullback | 447 | -293,012 | -2.93% |
| `frozen_fixed_weight` (固定权重基线) | alias | pullback_money_weak | 379 | -289,931 | -2.90% |
| `frozen_fixed_weight` (固定权重基线) | pullback_money | pullback_money_weak | 379 | -289,931 | -2.90% |
| `frozen_fixed_weight` (固定权重基线) | industry_sync | industry_sync_on | 559 | -272,068 | -2.72% |
| `frozen_fixed_weight` (固定权重基线) | market_trend | market_trend_on | 559 | -272,068 | -2.72% |
| `frozen_fixed_weight` (固定权重基线) | trend_score | top10_20 | 338 | -213,483 | -2.13% |
| `frozen_fixed_weight` (固定权重基线) | alias | pullback_top10_20 | 265 | -199,616 | -2.00% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | entry_type | pullback | 442 | -192,249 | -1.92% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | alias | pullback_money_weak | 375 | -191,158 | -1.91% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | pullback_money | pullback_money_weak | 375 | -191,158 | -1.91% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | industry_sync | industry_sync_on | 552 | -183,431 | -1.83% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | market_trend | market_trend_on | 552 | -183,431 | -1.83% |
| `frozen_fixed_weight` (固定权重基线) | width | width_neutral | 84 | -151,321 | -1.51% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | trend_score | top10_20 | 343 | -146,586 | -1.47% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | alias | pullback_top10_20 | 268 | -139,412 | -1.39% |
| `frozen_fixed_weight` (固定权重基线) | width | width_strong | 475 | -120,746 | -1.21% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | width | width_neutral | 84 | -94,665 | -0.95% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | width | width_strong | 468 | -88,766 | -0.89% |
| `frozen_fixed_weight` (固定权重基线) | trend_score | top10 | 221 | -58,585 | -0.59% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | alias | pullback_money_weak | 138 | -57,691 | -0.58% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | pullback_money | pullback_money_weak | 138 | -57,691 | -0.58% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | entry_type | pullback | 176 | -44,131 | -0.44% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | industry_sync | industry_sync_on | 303 | -39,041 | -0.39% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | market_trend | market_trend_on | 303 | -39,041 | -0.39% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | trend_score | top10 | 209 | -36,844 | -0.37% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | width | width_strong | 278 | -27,932 | -0.28% |
| `breakout_only_diagnostic` (只保留突破诊断) | trend_score | top10_20 | 87 | -26,704 | -0.27% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | trend_score | top10_20 | 81 | -22,652 | -0.23% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | trend_score | top10 | 222 | -16,389 | -0.16% |
| `breakout_only_diagnostic` (只保留突破诊断) | width | width_neutral | 26 | -13,100 | -0.13% |

解读：

- 最大亏损分组反复出现在 `pullback`、`pullback_money_weak`、`pullback_top10_20`，这与 holdout 结论一致。
- 固定权重和风险单位版本的 `industry_sync_on` / `market_trend_on` 仍然大幅亏损，说明“通过行业和市场过滤”不是充分条件；通过过滤后的信号质量仍需二次审计。
- `width_strong` 下仍有亏损，说明宽度强不等于个股回踩质量好；宽度指标更适合做全局风险开关，不足以单独确认入场。

## 9. 仓位、现金和集中度

| 版本 | 平均现金 | 平均持仓数 | 最大单票权重 | 最大行业权重 |
| --- | --- | --- | --- | --- |
| `frozen_fixed_weight` (固定权重基线) | 87.65% | 2.62 | 8.44% | 49.89% |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | 92.63% | 2.59 | 5.43% | 21.38% |
| `breakout_only_diagnostic` (只保留突破诊断) | 97.46% | 0.89 | 5.45% | 10.96% |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | 95.33% | 1.63 | 5.46% | 18.53% |

解读：

- 固定权重平均现金约 `87.65%`，风险单位 + 行业上限平均现金约 `92.63%`；系统长期处于低暴露状态。
- `breakout_only_diagnostic` 平均现金约 `97.46%`，所以它的低回撤不能直接等同于策略质量高。
- 风险单位仓位和行业 cap 成功降低了单票和行业集中度，但也进一步稀释收益；它们解决的是风险形态，不是信号胜率或期望。

## 10. 已观察区间复现

2025-2026 的表现如下，但该区间已被前序实验观察过，只能作为冻结规则复现 / 已观察区间复现，不参与选择。

| 版本 | 类型 | 成本后收益 | 最大回撤 | 交易数 | 平均现金 | 是否用于选择 |
| --- | --- | --- | --- | --- | --- | --- |
| `frozen_fixed_weight` (固定权重基线) | 基线 | 42.28% | -8.60% | 134 | 68.48% | False |
| `risk_unit_with_industry_cap` (风险单位仓位 + 行业上限候选) | 候选基线 | 23.93% | -5.12% | 129 | 81.14% | False |
| `pullback_regime_gated_diagnostic` (强状态回踩门控诊断) | 仅诊断 | 20.51% | -4.80% | 88 | 84.86% | False |
| `breakout_only_diagnostic` (只保留突破诊断) | 仅诊断 | 8.61% | -3.21% | 46 | 90.27% | False |

解读：

- 2025-2026 的固定权重和风险单位版本表现明显好于 2019-2024 研究窗口，这正是不能继续用已观察区间复现调参的原因。
- 如果根据已观察区间复现选择版本，会把策略推向已经看过的市场状态，结论会被污染。
- 当前最合理的做法是把 2025-2026 仅作为“冻结规则可复现”的参考，而不是样本外证据。

## 11. 我的判断

1. 当前版本不应进入 meta-labeling。候选交易集合还没有清理干净，模型很可能只是学习 pullback 失败样本和低暴露状态，而不是学习稳定 alpha。
2. pullback 不是完全不能做，但必须重新定义。当前证据支持先收紧或拆分 pullback，重点审计 `money_ratio20` 弱回踩、`trend_score_pct` 的 top10_20 区间、以及 time_stop 前是否已有趋势衰减。
3. breakout 子规则比 pullback 更干净，但交易太少。它可以作为下一轮规则核心，但需要解决覆盖率和现金拖累问题，不能直接拿 `breakout_only_diagnostic` 当成最终策略。
4. 风险单位仓位和行业 cap 应保留为风险控制层，但不要期待它们修复负期望信号。它们能降低回撤和集中度，却无法让多数年份转正。
5. 下一步优先级应是规则诊断和数据真实性修复：先做 point-in-time universe / industry membership 或者更严格的 pullback failure audit，再考虑模型。

## 12. 下一步建议

- 新建 Explore6 或 Explore5 扩展需求，专门研究 pullback failure audit，而不是直接扩参数网格。
- 把 pullback 拆成至少三类：强趋势中继回踩、弱成交额反弹、跌破后修复；分别看胜率、R 分布、time_stop 比例。
- 对 breakout 做覆盖率诊断：找出交易少是因为候选少、突破触发少、成交额确认过严，还是行业/宽度过滤过严。
- 如果继续保留 risk-unit，报告中应固定说明：它是风险控制，不是信号选择。
- 在真正有 2026-04-30 之后至少 20 个可执行交易日之前，不应声明 final test。
