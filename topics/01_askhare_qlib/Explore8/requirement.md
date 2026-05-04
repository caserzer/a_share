# Explore8 需求说明：PIT Universe 下 EMA 同源规则族逐年诊断

## 1. 背景

Explore3 到 Explore7 的结论已经说明：

- `layered_exit` 在 2025-2026 已观察区间表现好，但不能直接外推到 2017-2024。
- Explore5 的 2019-2024 rolling validation 没有形成冻结版本，说明单一 2025 风格规则不能稳定覆盖历史不同市场状态。
- Explore6 的 pullback meta-label 可以训练，但组合回放没有形成候选版本。
- Explore7 已经构建 point-in-time universe 和 point-in-time industry membership，但策略回放仍因 provider 覆盖不足被降级为 `coverage_limited_diagnostic`。
- 当前最需要回答的问题不是“再找一个总收益最高规则”，而是“每一年市场结构到底适合哪一类 EMA 同源规则，2025 的好表现属于哪种市场状态”。

Explore8 的核心问题是：

```text
在 Explore7 的 PIT universe 和 PIT industry 约束下，
用同一套 EMA 趋势交易规则族逐年回放 2017-2024，
找出每年相对有效和明显失效的规则形态，
再把这些同源规则按市场状态、入场类型、退出贡献和风险形态综合分析，
判断 2025 的规则表现是否有历史同类市场，以及下一步应继续规则切换、breakout coverage、pullback 重写，还是暂停策略优化。
```

Explore8 是诊断和归因实验，不是新的策略冻结阶段。

## 2. 与前序阶段的关系

Explore8 可以读取前序阶段作为背景，但必须独立计算。

允许读取：

- `Explore7/requirement.md`：PIT universe、PIT provider、PIT industry 和数据可信边界。
- `Explore7/configs/pullback_rebuild_v1.yaml`：PIT 数据路径、成本、风险和折叠定义参考。
- `Explore7/data/universe/pit_mcap500_mainboard_daily.csv`：唯一默认交易资格来源。
- `Explore7/data/targets/pit_industry_membership.csv`：默认行业归属来源。
- `Explore7/data/targets/market_targets.csv`、`industry_targets.csv`、`target_history.csv`：市场和行业状态的结构性输入，用于重新计算 market / industry regime。
- `Explore7/outputs/reports/pit_provider_coverage_audit.csv` 和 `pit_provider_coverage_summary.json`：只作为 `allowed_metadata_audit`，用于判断 provider 覆盖状态，不得参与信号、回放、收益、排序或聚类计算。
- `Explore3/reports/explore3_report.md`、`Explore5/outputs/reports/explore5_final_report.md`、`Explore7/outputs/reports/explore7_pullback_rebuild_report.md`：背景结论，只能作为报告叙述参考。

禁止：

- 读取 Explore3 / Explore4 / Explore5 / Explore6 / Explore7 的 `trade_detail`、`portfolio_daily`、`signals`、`daily_candidates`、`year_metrics`、模型预测或任何历史结果 CSV 作为 Explore8 的计算输入。
- 把任何一年内最优规则直接定义为下一年可交易策略。
- 使用 2025-2026 的表现选择 2017-2024 的规则族、阈值或版本。
- 继续使用 `mcap500_mainboard_20251231` 静态股票池作为交易资格来源。

source audit 必须把输入路径分成以下类别：

| Category | 允许用途 |
| --- | --- |
| `structural_input` | PIT universe、PIT industry、market / industry targets、target history、可读 provider 数据 |
| `allowed_config_reference` | 只读取白名单配置键，例如成本、基础规则和目标列表 |
| `allowed_metadata_audit` | 只读取覆盖率审计，不得参与信号或收益计算 |
| `background_reference` | 只用于报告背景叙述的 markdown |
| `forbidden_result_path` | 历史 trade/detail/signals/portfolio/year metrics/model predictions/result CSV，必须不进入计算路径 |

`run_manifest.json` 必须记录每类路径数量，并记录 `forbidden_result_path_used_for_calculation = false`。

Explore8 所有配置、脚本、缓存、回放、报告和 manifest 必须落在 `Explore8/` 下。

## 3. 数据契约

### 3.1 PIT Universe 硬约束

Explore8 必须使用 Explore7 的 PIT universe。

默认输入：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
benchmark: SH000300
```

规则：

- 每个信号日 `T` 的可交易资格必须通过 `date + instrument` 显式 join PIT membership。
- Qlib instrument 文件只能作为 provider 可读性的 superset，不得当作静态 universe。
- 若某只股票不在 `T` 日 PIT membership 中，即使 provider 有行情，也不得交易。
- 若 PIT membership 中某只股票在 `T` 日缺行情，必须记录 coverage miss，不得用未来行情或静态池替代。
- PIT industry 必须按 `T` 日有效关系 join；缺失行业统一记为 `UNKNOWN`，且必须参与行业归因和行业集中度统计。

### 3.2 Provider 处理

默认目标 provider：

```text
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
provider_mode: pit_primary | coverage_limited_diagnostic
```

要求：

- 如果 `Explore7/data/qlib/cn_data_pit` 已存在且覆盖率满足要求，应优先使用该 provider。
- 如果 PIT provider 不存在或覆盖不足，允许使用 `PIT universe ∩ existing provider` 做诊断，但 `provider_mode` 必须设为 `coverage_limited_diagnostic`，所有回放、表格和报告必须带上该 run-level 标记。
- `coverage_limited_diagnostic` 是 provider 使用模式，不是年度覆盖状态。年度结论权限只由 3.3 的 `coverage_status` 控制。
- 当 `provider_mode = coverage_limited_diagnostic` 时，Explore8 不得形成任何 `candidate_for_future_final_test` 或生产结论；若某些年份仍满足 `coverage_status = coverage_ok`，只允许形成 retrospective diagnostic leaderboard、cluster 和 2025 reference 对照。
- provider 覆盖审计必须按年输出覆盖率，至少包括 PIT membership 行数、可读行情行数、缺失行数、覆盖比例、缺失股票数和缺失行业分布。

### 3.3 Provider 覆盖 gating

每个自然年都必须单独计算覆盖状态：

```text
year_coverage_ratio = readable_pit_membership_rows / pit_membership_rows
required_field_coverage_ratio = rows_with_all_required_fields / pit_membership_rows
```

`readable_pit_membership_rows` 只统计 `date + instrument` 同时存在于 PIT membership 和实际 provider 的行。`rows_with_all_required_fields` 必须同时具备 `open`、`high`、`low`、`close`、`volume`、`money`、`factor`。rolling 特征历史窗口不足属于 warmup / feature eligibility 问题，不得计入 provider coverage miss。

年度覆盖状态定义：

| Status | 条件 | 允许结论 |
| --- | --- | --- |
| `coverage_ok` | `year_coverage_ratio >= 98%` 且 `required_field_coverage_ratio >= 98%`，benchmark 可读 | 可进入年度 leaderboard、rule-family cluster 和 2025 reference 对照 |
| `coverage_limited` | `90% <= year_coverage_ratio < 98%` 或 required fields 局部不足 | 只能输出年度诊断表；不得进入跨年聚类、2025 相似性判断或下一步决策树 |
| `data_insufficient` | `year_coverage_ratio < 90%`，或 benchmark 缺失，或关键字段缺失导致有效交易日不可判定 | 不得运行年度策略结论；只能输出覆盖阻断原因 |

如果任一研究年份不是 `coverage_ok`，最终报告必须把跨年结论标记为 `coverage_limited_research = true`，并逐年列出哪些结论被禁用。

如果所有研究年份都不是 `coverage_ok`，Explore8 第一版只能生成数据审计和阻断报告，不得生成“最适合规则”“市场相似性”或决策树结论。

权限优先级：

- `provider_mode` 控制 run-level 风险标签和是否允许形成未来候选。
- `coverage_status` 控制每个自然年是否允许进入 leaderboard、cluster 和 2025 reference 相似度。
- 任一年只要 `coverage_status != coverage_ok`，该年不得参与跨年排序、聚类、相似度或“最适合规则”结论，即使其他年份可用。

## 4. 时间范围

默认研究期：

```text
data_start: 2017-01-01
warmup_start: 2017-01-01 unless earlier PIT data exists
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30
```

规则：

- 2017-2024 是逐年规则族诊断窗口。
- 2025-2026 只能作为 `observed_reference`，用于描述 2025 的市场画像，不参与任何规则选择。
- 所有 rolling 指标必须满足 warmup 后才能生成信号。默认 `min_warmup_trading_days = max(ema_record, breakout_lookback, atr_window, slope_window) + 20`，实现必须在配置中显式记录实际值。
- 2017 年如果因为数据从 2017-01-01 才开始而无法完整 warmup，必须标记为 `warmup_partial_year = true`，并报告 `first_signal_eligible_date`。warmup 前不得交易。
- 主回放口径必须是 2017-01-01 到 2024-12-31 的连续组合净值回放，年度 return / max drawdown 按自然年切片统计。
- 若某年首尾缺交易日，必须在报告中说明有效交易日范围。
- 如果存在跨年持仓，年度统计必须同时报告：
  - 按年度净值切片的 return / max drawdown。
  - 按平仓日期归属的 trade PnL。
  - 年末未平仓强平或结转处理方式。

## 5. 同源 EMA 规则族

Explore8 只允许在同一 EMA 趋势交易框架内做有限规则族比较，不做无限参数搜索。

### 5.1 固定底座

所有规则版本必须共享：

- 市场状态：指数 EMA、指数 EMA slope、市场宽度。
- 个股趋势候选：`EMA20 > EMA60`、`close > EMA60`、`EMA60 slope`。
- 趋势质量评分：沿用 Explore3 / Explore4 的 `trend_score` 思路，但阈值只能在有限档位内变化。
- 成交：T 日收盘生成信号，T+1 开盘成交。
- 成本：沿用 Explore7 / Explore4 成本口径。
- 涨跌停处理：沿用主板近似 limit threshold，并记录跳过订单。
- 风控：固定权重、risk unit、industry cap 三类要分开比较。

### 5.2 入场形态族

默认比较以下 entry families：

1. `breakout_core`
   - 只保留突破入场。
   - 目标是衡量干净趋势启动信号的覆盖率和年份稳定性。

2. `pullback_original`
   - 原 Explore3 / Explore4 pullback 定义。
   - 作为 pullback 问题基线。

3. `pullback_strict_trend`
   - 更强趋势延续回踩。
   - 用于判断 pullback 失败是否来自趋势确认不足。

4. `pullback_strict_money`
   - 更严格成交额 / 缩量回踩确认。
   - 用于判断弱成交额反弹是否应被排除。

5. `pullback_top_score`
   - 只保留 trend_score 更靠前的 pullback，例如 top10。
   - 用于检查 top10_20 区间是否确实质量不足。

6. `breakdown_repair_diagnostic`
   - Explore7 中出现的跌破后修复形态。
   - 只能作为 diagnostic family，不能直接进入候选。

7. `ema_state_baseline`
   - 宽松 EMA 多头状态基线。
   - 用于衡量入场触发层是否真的提供增量价值。

### 5.3 退出形态族

默认比较以下 exit families：

1. `ema60_exit_only`
   - 用于衡量趋势尾部保留能力。

2. `stop_plus_time`
   - 结构止损 + time stop，不使用 trailing。

3. `layered_exit`
   - Explore3 风格分层退出。

4. `fast_failure_exit_diagnostic`
   - 更早识别失败交易，例如跌破短期均线、行业同步转弱、相对强度回落。
   - 只能作为 diagnostic family；任何阈值必须在当年之前的训练窗口或固定规则中定义，不能使用当年收益反推。

### 5.4 参数空间边界

参数只能使用小型离散网格，第一版建议：

```text
ema_fast: [20]
ema_mid: [30]
ema_slow: [60]
ema_record: [120]
trend_score_pct: [0.10, 0.20]
pullback_band_pct: [0.02, 0.03]
breakout_money_min: [1.2]
pullback_money_floor: [0.60, 0.80]
pullback_money_ceiling: [1.00]
time_stop_days: [5, 10, 15]
atr_stop_multiplier: [1.5, 2.0]
risk_budget_per_trade: [0.005]
single_stock_max_weight: [0.03, 0.05]
max_industry_weight: [0.20, 0.25]
```

禁止为了提高某一年表现临时加入新阈值。新增规则必须先写入 requirement 或 config，并标记为下一轮实验。

### 5.5 第一版组合矩阵

Explore8 必须显式列出第一版要跑的 entry / exit / 参数组合。实现不得默认对所有 entry families、exit families 和参数档位做完整笛卡尔积。

原因：

- 全量盲目笛卡尔积会把诊断实验变成过拟合搜索。
- 很多参数只对特定 entry 或 exit 有意义，例如 `pullback_band_pct` 不适用于纯 breakout。
- Explore8 的目标是比较同源规则形态和市场状态，不是寻找年度最高收益参数。

第一版参数必须先归并成命名参数套件：

| Param suite | trend_score_pct | pullback_band_pct | breakout_money_min | pullback_money_floor | pullback_money_ceiling | time_stop_days | atr_stop_multiplier | 适用目的 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `base` | 0.20 | 0.03 | 1.2 | 0.60 | 1.00 | 10 | 2.0 | 复现 Explore3 / Explore4 风格基线 |
| `strict_score` | 0.10 | 0.03 | 1.2 | 0.60 | 1.00 | 10 | 2.0 | 检查 top10 是否比 top20 更稳 |
| `strict_pullback` | 0.20 | 0.02 | 1.2 | 0.80 | 1.00 | 10 | 2.0 | 检查更窄回踩和排除过弱成交额 |
| `fast_failure` | 0.20 | 0.03 | 1.2 | 0.60 | 1.00 | 5 | 1.5 | 诊断更早失败退出 |
| `slow_hold` | 0.20 | 0.03 | 1.2 | 0.60 | 1.00 | 15 | 2.0 | 诊断趋势尾部是否需要更长持有 |

第一版 sizing 也必须归并成命名套件：

| Sizing suite | sizing_family | risk_budget_per_trade | single_stock_max_weight | max_industry_weight | 适用目的 |
| --- | --- | ---: | ---: | ---: | --- |
| `fixed_w05` | fixed_weight | NA | 0.05 | NA | 复现固定权重风险形态 |
| `risk_unit_w03_ind20` | risk_unit_with_industry_cap | 0.005 | 0.03 | 0.20 | 低单票和低行业暴露 |
| `risk_unit_w05_ind25` | risk_unit_with_industry_cap | 0.005 | 0.05 | 0.25 | 接近 Explore3 暴露但带行业 cap |

第一版只允许下表组合。每一行只展开到列出的 sizing suites；不得额外展开未列出的 entry / exit / param / sizing 组合。

实现必须把每个展开后的组合生成为唯一 `rule_version_id`：

```text
rule_version_id = rule_family_id + "__" + sizing_suite
```

所有 leaderboard、trade attribution、formula audit、manifest 和报告表格都必须以 `rule_version_id` 作为唯一结果键，`rule_family_id` 只作为同源规则族分组键。

| Rule family id | Entry family | Exit family | Param suite | Sizing suites | Scope | 诊断目的 |
| --- | --- | --- | --- | --- | --- | --- |
| `ema_state_ema60_base` | `ema_state_baseline` | `ema60_exit_only` | `base` | `fixed_w05`, `risk_unit_w03_ind20` | baseline | 宽松 EMA 状态是否本身有价值 |
| `ema_state_stop_time_base` | `ema_state_baseline` | `stop_plus_time` | `base` | `fixed_w05`, `risk_unit_w03_ind20` | baseline | 宽松状态加硬风控后的磨损 |
| `breakout_layered_base` | `breakout_core` | `layered_exit` | `base` | `fixed_w05`, `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | 突破 + 分层退出是否是趋势年核心 |
| `breakout_stop_time_base` | `breakout_core` | `stop_plus_time` | `base` | `fixed_w05`, `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | 突破收益是否依赖 trailing |
| `breakout_fast_failure_diag` | `breakout_core` | `fast_failure_exit_diagnostic` | `fast_failure` | `risk_unit_w03_ind20` | diagnostic_only | 早退出是否破坏突破尾部收益 |
| `pullback_original_layered_base` | `pullback_original` | `layered_exit` | `base` | `fixed_w05`, `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | 原 pullback 在 PIT universe 下逐年表现 |
| `pullback_original_stop_time_base` | `pullback_original` | `stop_plus_time` | `base` | `fixed_w05`, `risk_unit_w03_ind20` | year_diagnostic | 原 pullback 是否主要依赖 trailing 覆盖亏损 |
| `pullback_strict_trend_layered` | `pullback_strict_trend` | `layered_exit` | `strict_score` | `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | 更强趋势确认是否改善 pullback |
| `pullback_strict_money_layered` | `pullback_strict_money` | `layered_exit` | `strict_pullback` | `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | 更严格成交额确认是否改善 pullback |
| `pullback_top_score_layered` | `pullback_top_score` | `layered_exit` | `strict_score` | `risk_unit_w03_ind20`, `risk_unit_w05_ind25` | year_diagnostic | top10 是否明显优于 top10_20 |
| `pullback_strict_trend_fast_failure_diag` | `pullback_strict_trend` | `fast_failure_exit_diagnostic` | `fast_failure` | `risk_unit_w03_ind20` | diagnostic_only | 早失败退出能否减少 stop/time 损失 |
| `pullback_slow_hold_diag` | `pullback_original` | `layered_exit` | `slow_hold` | `risk_unit_w03_ind20` | diagnostic_only | 延长 time stop 是否只是扩大亏损 |
| `breakdown_repair_layered_diag` | `breakdown_repair_diagnostic` | `layered_exit` | `base` | `risk_unit_w03_ind20` | diagnostic_only | 跌破后修复是否独立成型 |
| `breakdown_repair_fast_failure_diag` | `breakdown_repair_diagnostic` | `fast_failure_exit_diagnostic` | `fast_failure` | `risk_unit_w03_ind20` | diagnostic_only | 跌破修复是否需要更快失败退出 |

实现配置必须逐行枚举 `rule_family_id`，并记录展开后的 `rule_version_id`、`entry_family`、`exit_family`、`param_suite`、`sizing_suite`。如果后续需要新增组合，必须先更新本节或配置中的显式矩阵，并在报告中把新增组合标记为新一轮实验。

### 5.6 规则公式契约

本节定义第一版必须实现的 T 日可观察规则。实现可以为了代码结构拆函数，但不得改变公式含义。

特征计算字典：

| Feature | 计算口径 |
| --- | --- |
| `emaN_T` | 使用复权后 `close` 到 T 日为止计算 EMA，N 为 20、30、60、120 |
| `ema60_slope10_T` / `ema60_slope20_T` | `ema60_T / ema60_{T-N} - 1`，历史不足则为缺失 |
| `money_ratio20_T` | `money_T / mean(money, prior 20 trading days excluding T)`，分母缺失或为 0 则为缺失 |
| `rolling_high(close, 60, exclude_T)` | T 日以前 60 个交易日最高收盘价，不包含 T |
| `recent_low5_T` | 包含 T 在内最近 5 个交易日最低价 |
| `close_pos_T` | `(close_T - low_T) / max(high_T - low_T, epsilon)` |
| `upper_shadow_ratio_T` | `(high_T - max(open_T, close_T)) / max(high_T - low_T, epsilon)` |
| `volatility20_T` | 最近 20 个交易日日收益率标准差，包含 T |
| `daily_cross_section_p90(volatility20_T)` | 当日 PIT membership 且 required fields 可读股票的 90 分位，不使用未来股票池 |
| `trend_score_pct_T` | 当日 PIT membership 内按 Explore3 / Explore4 trend_score 口径升序 percentile rank，数值越小表示排名越靠前 |
| `retN_T` | `close_T / close_{T-N} - 1` |
| `ret60_excess_T` / `ret20_excess_T` | 个股 `retN_T - broad_market.retN_T` |
| `market_width_T` | 当日 PIT membership 且 required fields 可读股票中满足条件的比例 |
| `industry.ret60_T` | `industry_targets` 对应行业指数从 target history 重新计算，不得读取历史 `industry_regime.csv` |

所有特征缺失时，该股票当日不得产生信号，但必须进入候选漏斗的缺失原因统计。

除 `breakdown_repair_diagnostic` 外，所有 entry family 都必须先满足共享候选条件：

```text
pit_member_T = true
has_required_ohlcvf_T = true
market_ok_T = broad_market.close_T > broad_market.ema60_T and broad_market.ema60_slope20_T > 0
width_ok_T = close_gt_ema60_ratio_T > 0.55 and ema20_gt_ema60_ratio_T > 0.45
industry_ok_T = industry != UNKNOWN and industry.close_T > industry.ema60_T and industry.ema60_slope20_T > 0 and industry.ret60_T > broad_market.ret60_T
trend_candidate_T = ema20_T > ema60_T and ema60_slope10_T > 0 and close_T > ema60_T
volatility_ok_T = volatility20_T <= daily_cross_section_p90(volatility20_T)
score_ok_T(param_suite) = trend_score_pct_T <= param_suite.trend_score_pct
shared_entry_gate_T = pit_member_T and has_required_ohlcvf_T and market_ok_T and width_ok_T and industry_ok_T and trend_candidate_T and volatility_ok_T and score_ok_T
```

若 `industry = UNKNOWN`，该股票不得通过 `industry_ok_T`，但必须保留在 coverage、行业缺失和候选漏斗审计中。

entry family 公式：

| Entry family | T 日公式 |
| --- | --- |
| `ema_state_baseline` | `shared_entry_gate_T` |
| `breakout_core` | `shared_entry_gate_T and close_T > rolling_high(close, 60, exclude_T) and money_ratio20_T >= param_suite.breakout_money_min and close_pos_T >= 0.5 and upper_shadow_ratio_T <= 0.40` |
| `pullback_original` | `shared_entry_gate_T and min(abs(close_T / ema20_T - 1), abs(close_T / ema30_T - 1)) <= param_suite.pullback_band_pct and close_T > ema60_T and recent_low5_T <= max(ema20_T, ema30_T) * (1 + param_suite.pullback_band_pct) and param_suite.pullback_money_floor <= money_ratio20_T <= param_suite.pullback_money_ceiling and close_T >= ema20_T and close_T > open_T` |
| `pullback_strict_trend` | `pullback_original and trend_score_pct_T <= 0.10 and ema20_T > ema60_T and ema60_slope20_T > 0 and ret20_T > 0 and ret60_excess_T > 0` |
| `pullback_strict_money` | `pullback_original` using `strict_pullback` param suite, especially `pullback_money_floor = 0.80` and `pullback_band_pct = 0.02` |
| `pullback_top_score` | `pullback_original and trend_score_pct_T <= 0.10` |
| `breakdown_repair_diagnostic` | `pit_member_T and has_required_ohlcvf_T and market_ok_T and width_ok_T and close_T > ema20_T and close_T > ema60_T and min(close / ema60 - 1 over prior 10 trading days) < 0 and ret5_T > 0 and ret20_T > 0` |

`breakdown_repair_diagnostic` 是共享 gate 的明确例外：它不要求 `industry_ok_T`、`trend_candidate_T` 或 `score_ok_T`，只能用于诊断，不能进入候选策略或未来决策树。

exit family 公式：

| Exit family | T 日公式，T+1 开盘成交 |
| --- | --- |
| `ema60_exit_only` | 持仓后仅在 `close_T < ema60_T` 触发退出；回测结束后按统一期末处理 |
| `stop_plus_time` | `close_T <= current_stop_T` 触发 `stop_loss`；`holding_days >= param_suite.time_stop_days and close_T <= entry_price` 触发 `time_stop`；`close_T < ema60_T` 触发 `ema60_exit`；不启用 break-even 或 trailing stop |
| `layered_exit` | 沿用 Explore3 分层退出：1R 后 stop 提到 entry，2R 后 `max(ema20_T, close_T - atr_stop_multiplier * atr20_T)` trailing，3R 且远离 EMA20 时进一步上移；同时保留 `stop_loss`、`time_stop` 和 `ema60_exit` |
| `fast_failure_exit_diagnostic` | 在 `stop_plus_time` 基础上增加固定早失败退出：`holding_days >= 3 and close_T < ema20_T`，或 `holding_days >= 3 and ret20_excess_T <= 0`，或 `industry_ok_T = false for 2 consecutive trading days`。该 family 只能作为 diagnostic，不得形成候选 |

所有公式都必须只使用 T 日或 T 日以前数据。不得用当年收益、未来收益、未来行业归属或未来 universe membership 反推阈值。

## 6. 年度诊断流程

Explore8 第一版按自然年执行以下流程。

### 6.1 年度规则族 leaderboard

对 2017-2024 每一年、每个 `rule_version_id` 输出：

- `year`
- `coverage_status`
- `warmup_partial_year`
- `first_signal_eligible_date`
- `rule_version_id`
- `rule_family_id`
- `rule_family`
- `entry_family`
- `exit_family`
- `sizing_family`
- `param_suite`
- `sizing_suite`
- `scope`
- `trades`
- `win_count`
- `loss_count`
- `win_rate`
- `avg_win_pnl`
- `avg_loss_pnl`
- `profit_factor`
- `return_after_cost`
- `max_drawdown`
- `net_pnl`
- `gross_pnl`
- `avg_cash_ratio`
- `avg_positions`
- `avg_holding_days`
- `stop_loss_count`
- `time_stop_count`
- `trailing_stop_count`
- `stop_time_trade_ratio`
- `top5_trade_pnl_share`
- `coverage_limited_diagnostic`

主 leaderboard 粒度是 `year + rule_version_id`。按 `rule_family_id` 的聚合表必须单独输出，不能覆盖 sizing suite 维度。

年度榜单必须同时给出：

- 收益最高规则。
- 回撤最小且交易数足够的规则。
- 交易质量最高规则。
- 最差规则。
- 现金过高或交易数过低而不能解释为有效的规则。

只有 `coverage_status = coverage_ok` 的年份才允许输出“收益最高规则”“最适合规则”和 rule-family cluster 标签。`coverage_limited` 或 `data_insufficient` 年份只能输出覆盖状态、可读样本范围和被禁用的结论列表。

### 6.2 年度市场画像

每年必须输出市场状态画像：

- SH000300 年度收益、最大回撤、波动率。
- 市场宽度均值和分位：`close > EMA60`、`EMA20 > EMA60`。
- 趋势日占比：market trend on / off。
- 行业同步占比：industry sync on / off。
- 行业集中度：每年交易 PnL 和持仓暴露前 5 行业。
- 成交额环境：money ratio 分布、弱成交额 pullback 占比。
- 波动环境：ATR / close 分布、跳空分布。
- 信号密度：breakout、pullback、breakdown-repair 每年触发次数和成交次数。

### 6.3 年度失效归因

每年必须对失败交易归因：

- `entry_type`
- `exit_reason`
- `industry`
- `market_trend`
- `market_width`
- `trend_score_bucket`
- `money_ratio_bucket`
- `gap_bucket`
- `initial_risk_bucket`
- `holding_days_bucket`

重点回答：

- 当年亏损主要来自 entry 问题、exit 问题、仓位问题还是市场状态误判。
- `stop_loss + time_stop` 是否主导亏损。
- `trailing_stop` 是否足以覆盖失败交易。
- 当年有效规则是否只是高现金 / 少交易。

## 7. 跨年综合分析

Explore8 的最终报告必须把年度结果合并成规则族和市场状态结论。

### 7.1 同源规则族聚类

同源规则族聚类只能使用 `coverage_status = coverage_ok` 的年份。所有聚类标签都必须标记为 retrospective explanation，不得解释为未来可交易 regime classifier。

至少输出以下分类：

1. `trend_continuation_year`
   - breakout 或 strong trend pullback 有效。
   - trailing stop 贡献主要收益。

2. `pullback_failure_year`
   - pullback、weak money、top10_20 pullback 主导亏损。
   - stop/time stop 占比高。

3. `low_signal_cash_year`
   - 所有规则交易少、现金高。
   - 不能把低回撤解释为规则质量。

4. `regime_filter_failure_year`
   - market/industry/width 过滤为 on，但交易仍亏。
   - 说明过滤通过不是充分条件。

5. `industry_concentration_year`
   - 行业暴露或行业 PnL 高度集中。
   - 需要判断是风格机会还是集中风险。

### 7.2 2025 reference 对照

2025 只能作为参考画像，不参与规则选择。

必须回答：

- 2025 的有效规则属于哪个 rule family cluster。
- 2017-2024 中哪些年份最像 2025。
- 2025 的收益是否来自少数行业、少数股票、少数 trailing-stop 大赢家。
- 2025 的市场宽度、行业同步、成交额和波动状态是否显著不同于失败年份。
- 如果当前市场不像 2025，应降低仓位、切换规则、只做 breakout，还是暂停交易。

如果 2025 的 PIT provider 覆盖不是 `coverage_ok`，本节只能引用已观察报告中的市场画像作为 `background_reference`，不得把 2025 加入任何相似度数值排序。

### 7.3 决策树草案

Explore8 不输出最终策略，但必须输出下一步研究决策树草案：

```text
if market_state resembles trend_continuation_year:
    prioritize breakout coverage and layered exit
elif pullback_failure_conditions dominate:
    disable or rewrite pullback
elif signal_density too low:
    do not force trades; report no-edge / high-cash regime
elif industry_concentration extreme:
    keep industry cap and report concentration risk
else:
    no strategy candidate; continue regime diagnostics
```

该决策树是下一阶段研究假设，不是可交易规则。若未来要把它变成 regime switch，必须另起阶段实现 walk-forward regime classifier，并且只能用每个交易日 T 日可观察状态做切换。

## 8. 产物要求

Explore8 至少产出：

```text
Explore8/requirement.md
Explore8/configs/yearly_rule_diagnostic_v1.yaml
Explore8/scripts/run_explore8.py
Explore8/outputs/reports/run_manifest.json
Explore8/outputs/reports/source_data_audit.csv
Explore8/outputs/reports/year_data_eligibility.csv
Explore8/outputs/reports/pit_provider_coverage_by_year.csv
Explore8/outputs/reports/rule_formula_audit.csv
Explore8/outputs/reports/year_rule_leaderboard.csv
Explore8/outputs/reports/year_market_regime_summary.csv
Explore8/outputs/reports/year_entry_exit_attribution.csv
Explore8/outputs/reports/year_failure_attribution.csv
Explore8/outputs/reports/rule_family_cluster_summary.csv
Explore8/outputs/reports/reference_2025_comparison.csv
Explore8/outputs/reports/explore8_yearly_rule_diagnostic_report.md
```

`run_manifest.json` 至少记录：

- PIT universe 文件路径、行数、SHA256。
- PIT industry 文件路径、行数、SHA256。
- market / industry target 文件路径、行数、SHA256。
- target history 文件路径、行数、SHA256。
- provider 使用路径、`provider_mode`、覆盖率、是否 coverage-limited。
- 年度 `coverage_status` 和被禁用结论列表。
- warmup 参数、每年 `first_signal_eligible_date`、是否 `warmup_partial_year`。
- 是否使用静态 `mcap500_mainboard_20251231` 作为交易资格，必须为 `false`。
- 是否使用任何历史 result CSV 作为计算输入，必须为 `false`。
- 规则族列表、参数套件、sizing 套件、显式组合矩阵和公式版本。
- 逐年有效交易日范围。
- 2025-2026 是否用于选择，必须为 `false`。

## 9. 报告必须回答的问题

最终报告必须回答：

- Explore8 是否成功使用 Explore7 PIT universe 替代静态股票池。
- provider 覆盖是否足够；若不足，哪些年份和行业受影响最大，哪些结论被禁用。
- 对 `coverage_ok` 年份，2017-2024 每一年最适合哪类 EMA 同源规则；对非 `coverage_ok` 年份，只说明为什么不能判断。
- 每一年最主要的失败来源是什么；非 `coverage_ok` 年份只能作为数据覆盖诊断。
- pullback 在哪些 coverage-ok 年份、哪些状态下仍有价值；哪些状态下必须禁用。
- breakout 是否只是低覆盖、低现金风险，还是有可扩展的趋势启动价值。
- layered exit 的收益是否来自稳定尾部捕捉，还是少数年份/行业/股票。
- 2025 的好表现与历史哪些 coverage-ok 年份相似，哪些方面不可复制。
- 下一步应该优先补 PIT provider、做 breakout coverage、重写 pullback、做 regime switch，还是暂停策略优化。

## 10. 验收标准

Explore8 需求阶段验收：

- `Explore8/requirement.md` 存在，且明确使用 Explore7 PIT universe。
- 不允许把 Explore8 描述为策略冻结阶段。
- 不允许使用 2025-2026 做规则选择。
- 不允许使用历史结果 CSV 做计算输入。

实现阶段验收：

- 若 `universe_point_in_time != true`，策略阶段必须失败。
- 若 `industry_membership_point_in_time != true`，策略阶段必须失败或降级为数据诊断。
- 若 `provider_mode = coverage_limited_diagnostic`，报告不得形成生产候选或 `candidate_for_future_final_test`，但允许对 `coverage_ok` 年份输出 retrospective diagnostics。
- 若某年 `coverage_status != coverage_ok`，该年不得进入 rule-family cluster、2025 reference 相似度排序或“最适合规则”结论。
- `source_data_audit.csv` 必须区分 `structural_input`、`allowed_config_reference`、`allowed_metadata_audit`、`background_reference` 和 `forbidden_result_path`。
- `rule_formula_audit.csv` 必须列出每个 `rule_version_id` 对应的 `rule_family_id`、entry formula、exit formula、param suite、sizing suite 和 scope。
- `year_data_eligibility.csv` 必须列出每年 coverage status、warmup status、first signal eligible date 和 disabled conclusions。
- `year_rule_leaderboard.csv` 必须覆盖 2017-2024 每个自然年。
- `year_rule_leaderboard.csv` 必须以 `year + rule_version_id` 唯一，且包含 `win_count`、`loss_count`、`avg_win_pnl`、`avg_loss_pnl` 和 `profit_factor`。
- `year_market_regime_summary.csv` 必须覆盖每个自然年。
- 报告必须把“年度最优规则”降级为诊断证据，不得直接外推为未来策略。

## 11. 测试计划

静态检查：

```text
uv run python -m compileall Explore8/scripts
uv run python Explore8/scripts/run_explore8.py self-test --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

数据审计：

```text
uv run python Explore8/scripts/run_explore8.py audit-data --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

年度回放：

```text
uv run python Explore8/scripts/run_explore8.py run-yearly --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

报告：

```text
uv run python Explore8/scripts/run_explore8.py report --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

第一版只要求整理需求，不要求立即实现脚本或运行实验。
