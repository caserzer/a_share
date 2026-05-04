# Explore8 扩展需求：PIT Universe 年度大涨股画像探查

## 1. 背景

Explore8 的 EMA 同源规则族逐年诊断没有形成足够好的策略结论。继续扩大规则搜索容易变成在失败规则附近调参，因此下一步先暂停策略优化，转为探查 PIT universe 中真实年度大涨股票的结构。

本扩展阶段只回答一个问题：

```text
在 point-in-time universe 中，每一年真正从低点到高点涨幅超过 50% 的股票，
它们出现在什么时间段、持续多久、波动和成交特征如何、之前有什么可观察结构，
以及现有 EMA / breakout / pullback 规则为什么没有稳定捕捉这些机会？
```

本扩展是 retrospective profiling，不是新策略回测，不得直接产出可交易候选。

## 2. 数据边界

必须使用 Explore7 / Explore8 已确认的 PIT 数据链路：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
industry_membership: Explore7/data/targets/pit_industry_membership.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
benchmark: SH000300
```

硬约束：

- 股票样本必须来自对应日期的 `date + instrument` PIT membership，不得使用 `mcap500_mainboard_20251231` 静态池补历史。
- 行情数据必须能读到 `open`、`high`、`low`、`close`、`volume`、`money`、`factor`。
- 行业归属必须按事件日期或事件起点日期 join PIT industry；缺失行业记录为 `UNKNOWN`。
- 若某个股票年存在 membership 但缺行情，必须进入 coverage audit，不得静默删除。
- 2025-2026 只能作为 observed reference，不参与规则选择；本扩展默认先覆盖 2017-2024。
- 本阶段允许使用未来完整年度信息定义“大涨事件标签”，但这些标签只能用于事后画像，不能作为交易信号或调参目标。

## 3. 大涨事件定义

默认按自然年逐年扫描 PIT universe，但必须区分“年内可比主口径”和“跨年行情审计”。

扫描分两层：

- `in_year_scan`：按自然年逐年扫描，只在同一 `year` 内寻找 `low_date <= high_date` 的最大前向涨幅，用于年度可比统计。
- `continuous_cross_year_scan`：在 `research_start..research_end` 连续区间内扫描完整低高点，再按 `episode_overlap_year` 拆到各自然年审计，用于发现被自然年边界切碎的主升段。
- 若跨年事件延伸到 `observed_reference`，必须标记为 `observed_reference_overlap`，只能作为背景审计，不得改变 2017-2024 的研究期选择和规则判断。

对每个 `year + instrument`：

1. 取该股票在该自然年内、且当天属于 PIT membership、且 required fields 可读的所有交易日。
2. 在同一年内寻找满足 `low_date <= high_date` 的最大前向盘中涨幅：

```text
forward_gain_intraday = adjusted_high_on_high_date / adjusted_low_on_low_date - 1
```

3. 同时计算收盘确认涨幅和对应日期：

```text
forward_gain_close_confirmed = max(adjusted_close_on_or_after_low_date) / adjusted_low_on_low_date - 1
close_confirmed_peak_date = argmax(adjusted_close_on_or_after_low_date)
```

4. 若 `forward_gain_intraday >= 50%`，该股票年进入大涨样本；若 `forward_gain_close_confirmed >= 50%`，标记为 `close_confirmed_50pct = true`。
5. 默认事件窗口为 `low_date` 到 `high_date`，并记录这个最大前向涨幅事件。

主口径说明：

- `in_year_episode`：`low_date` 和 `high_date` 都在同一自然年内，用于逐年可比统计。
- `cross_year_overlap_episode`：完整低高点跨越自然年边界，但事件窗口与该年份有重叠；必须单独输出审计，避免把跨年主升段误判为缺失或失败。
- `observed_reference_overlap`：研究期内低点或重叠段延伸到 2025-2026 observed reference；只能作为背景审计。
- 最终报告中不得把 `in_year_episode` 直接描述为完整牛股生命周期；若主升段被自然年截断，必须标记 `truncated_by_year_boundary = true`。

实现时必须显式记录价格口径：

- 当前 Explore 数据链路中，provider 的 `open/high/low/close` 可能已经来自前复权行情，`factor` 只用于审计和兼容。实现不得默认把 `open/high/low/close` 再乘一次 `factor`。
- 必须在 manifest 中记录 `price_adjustment_mode`，固定枚举为 `provider_ohlc_already_adjusted`、`raw_ohlc_times_factor`、`raw_ohlc_unadjusted`。
- 若使用 `raw_ohlc_times_factor`，必须显式写出公式，例如 `adjusted_price = raw_price * factor / factor_ref`，并记录 `factor_ref_date`。
- 若无法确认复权口径，必须标记 `adjusted_price_used = false` 和 `price_adjustment_mode = raw_ohlc_unadjusted`，报告中说明结果只适合粗略形态探查。

补充事件：

- 第一版只强制输出每个 `year + instrument` 的主事件，主事件为 `episode_rank = 1`。
- 若实现 `secondary_episode`，必须先定义局部低高点算法、最小间隔交易日和重叠处理规则，不得简单输出所有非完全包含的 `>= 50%` 片段。
- 同一股票年若存在多段大涨，必须保留 `episode_rank` 和 `secondary_episode_generation_rule`。

事件标签使用约束：

- `low_date` 是事后标签，不是可交易启动点。
- 所有“启动前状态”必须同时输出以 `low_date` 为锚的事后画像，以及以可观察锚点为锚的交易可见画像。
- 默认可观察锚点包括：首次收盘站上 EMA60、首次满足 breakout 条件、首次从 `low_date` 后收盘涨幅达到 20%、首次从 `low_date` 后收盘涨幅达到 30%。
- 若某个可观察锚点不存在，必须记录为 `anchor_missing`，不得用 `low_date` 替代。

## 4. 必须抓取的事件级字段

`yearly_big_winner_episodes.csv` 至少包含：

```text
year, instrument, name, industry_name, episode_rank,
episode_scope, cross_year_episode_id, episode_overlap_year,
truncated_by_year_boundary, price_adjustment_mode,
low_date, high_date, start_trade_index, end_trade_index,
duration_trading_days, duration_calendar_days,
low_price_adj, high_price_adj, forward_gain_intraday,
forward_gain_close_confirmed, intraday_50pct, close_confirmed_50pct,
close_confirmed_peak_date,
close_to_close_gain, max_intraday_gain,
max_drawdown_before_high, max_pullback_before_high,
avg_daily_amplitude, median_daily_amplitude, max_daily_amplitude,
prev_close_missing_count, prev_close_from_non_member_day_count,
avg_gap_pct, max_gap_up_pct, max_gap_down_pct,
avg_turnover_money, median_turnover_money, max_turnover_money,
avg_volume, median_volume, max_volume,
low_is_retrospective_label,
first_ema60_reclaim_date, first_breakout_signal_date,
first_close_gain_20pct_date, first_close_gain_30pct_date,
primary_profile_anchor_date, primary_profile_anchor_type,
anchor_missing_count, volume_ratio20_at_high,
money_ratio20_at_high, atr20_pct_at_high,
benchmark_ret_during_episode,
industry_target_ret_during_episode,
membership_days_in_year, readable_days_in_year,
coverage_status
```

其中：

- `avg_daily_amplitude = mean((high - low) / prev_close)`，首日没有 `prev_close` 时使用 `(high - low) / close` 并标记。
- `prev_close` 可以来自该股票前一可读交易日，即使前一日不在 PIT membership；但必须标记 `prev_close_from_non_member_day = true`，并汇总到 `prev_close_from_non_member_day_count`。
- 若前一可读交易日不存在，必须标记 `prev_close_missing = true`，并汇总到 `prev_close_missing_count`。
- `max_daily_amplitude` 是事件窗口内每日振幅最大值。
- `max_drawdown_before_high` 只统计 `low_date` 到 `high_date` 之间、到达最高点前的最大回撤。
- `max_pullback_before_high` 用于描述上涨途中最大回踩深度，不得使用 `high_date` 之后的数据。
- 事件级表只保留主事件和锚点日期摘要；多锚点启动前画像必须写入 `yearly_big_winner_anchor_profile.csv`。

## 5. 需要补充分析的数据

除用户指定的最低点、最高点、持续时间、振幅和成交量外，必须补充以下画像维度。

### 5.1 启动前状态

`low_date` 是事后最低点，只能作为标签解释，不得作为唯一启动锚点。

必须分别对以下锚点前 20 / 60 / 120 个交易日统计：

- `low_date`：事后最低点画像，用于理解大涨前的底部状态。
- `first_ema60_reclaim_date`：首次收盘重新站上 EMA60。
- `first_breakout_signal_date`：首次满足 Explore8 breakout 条件。
- `first_close_gain_20pct_date`：从 `low_date` 后首次收盘涨幅达到 20%。
- `first_close_gain_30pct_date`：从 `low_date` 后首次收盘涨幅达到 30%。

对每个可用锚点统计：

- 启动前是否已经处于 EMA 多头。
- 是否刚从长期下跌或横盘中修复。
- `ret20`、`ret60`、`ret120`。
- `volatility20`、`atr20_pct`。
- `money_ratio20` 和成交额分位。
- 是否处于市场宽度改善期。
- 所属行业是否同步走强。
- 该锚点相对 `low_date` 滞后多少交易日。
- 该锚点前已经发生多少涨幅，避免把事后最低点误当成可交易启动信号。

多锚点画像必须独立输出为长表，不得把多个锚点硬塞进事件表的一行。

`yearly_big_winner_anchor_profile.csv` 至少包含：

```text
year, instrument, episode_rank, low_date, high_date,
anchor_type, anchor_date,
anchor_missing, anchor_missing_reason,
anchor_lag_trading_days_from_low,
gain_intraday_from_low_to_anchor,
gain_close_from_low_to_anchor,
ret20_before_anchor, ret60_before_anchor, ret120_before_anchor,
volatility20_before_anchor, atr20_pct_before_anchor,
volume_ratio20_before_anchor, money_ratio20_before_anchor,
money_percentile_in_pit_universe,
ema20_gt_ema60_at_anchor, close_gt_ema60_at_anchor,
ema60_slope_at_anchor, trend_score_pct_at_anchor,
market_regime_at_anchor, market_width_at_anchor,
industry_regime_at_anchor, industry_width_at_anchor,
lookback_readable_days_20, lookback_readable_days_60,
lookback_readable_days_120
```

`anchor_type` 固定枚举：

```text
low_date_retrospective, first_ema60_reclaim,
first_breakout_signal, first_close_gain_20pct,
first_close_gain_30pct
```

若锚点缺失，仍保留一行 `anchor_missing = true`，画像字段置空，并写明 `anchor_missing_reason`。

### 5.2 上涨过程形态

对 `low_date` 到 `high_date`：

- 涨幅分布：20%、30%、50%、100% 节点首次到达日期。
- 上涨斜率：日均收益、复合日均收益。
- 途中回撤：最大回撤、回撤次数、超过 8% / 12% / 20% 的回撤次数。
- 振幅结构：平均振幅、最高振幅、高振幅日占比。
- 成交结构：成交量放大倍数、成交额放大倍数、放量日占比。
- 跳空结构：最大向上跳空、最大向下跳空、跳空后回补情况。
- 涨停近似：接近涨停日数量、连续接近涨停段。

### 5.3 高点后行为

对 `high_date` 后 20 / 60 / 120 个交易日统计：

- 高点后最大回撤。
- 高点后 20 / 60 / 120 日收益。
- 是否快速跌回 EMA20 / EMA60。
- 大涨是否属于可持续趋势、尖峰冲高，还是事件驱动的一次性行情。

这部分不能用于定义事件，只用于事后理解“卖出和持有问题”。

### 5.4 与 Explore8 规则错配分析

必须把大涨事件与 Explore8 已定义的规则族做事后对齐，但不得读取 Explore8 历史交易结果作为标签。

规则错配必须有可复算搜索窗口：

- `signal_search_start` 默认取 `low_date`。
- `signal_search_end` 默认取 `high_date`。
- 对可观察锚点附近复查时，额外输出 `anchor_search_start = anchor_date - 20 trading days` 和 `anchor_search_end = anchor_date + 20 trading days`。
- 若窗口因年初、年末、membership 边界或 provider 缺行情被截断，必须记录 `search_window_truncated = true` 和 `search_window_truncate_reason`。
- 任何 `first_signal_date`、`entry_date`、`exit_date` 都必须落在已记录的搜索窗口内，且对应行情和 membership 可复查。

需要回答：

- 大涨事件的可观察锚点附近是否满足 `breakout_core` 入场条件，不得只在事后 `low_date` 附近判断。
- 是否满足原始 `pullback_original`，还是大涨股很少出现规则定义的回踩。
- `trend_score` 在启动时是否真的靠前，还是大涨早期常常处于低分位。
- 当前 `time_stop` 是否会在主要上涨前把股票卖掉。
- 当前风险距离、ATR 和 gap 过滤是否会把大涨股排除。
- 未捕捉原因应归类为：`no_signal`、`late_signal`、`early_exit`、`risk_filtered`、`liquidity_filtered`、`industry_filtered`、`market_filtered`、`coverage_missing`。

## 6. 聚合报告要求

必须输出以下聚合表。

### 6.1 年度大涨股清单

```text
Explore8/outputs/reports/yearly_big_winner_episodes.csv
Explore8/outputs/reports/yearly_big_winner_stock_summary.csv
Explore8/outputs/reports/yearly_big_winner_anchor_profile.csv
Explore8/outputs/reports/yearly_big_winner_cross_year_audit.csv
Explore8/outputs/reports/yearly_big_winner_coverage_audit.csv
```

`yearly_big_winner_stock_summary.csv` 至少包含：

```text
year, instrument, name, industry_name,
max_forward_gain_intraday, max_forward_gain_close_confirmed,
main_low_date, main_high_date, close_confirmed_peak_date,
main_duration_trading_days, episode_count,
first_intraday_50pct_date, first_close_confirmed_50pct_date,
readable_days_in_year, membership_days_in_year,
coverage_status, truncated_by_year_boundary
```

`yearly_big_winner_cross_year_audit.csv` 至少包含：

```text
cross_year_episode_id, instrument, name, industry_name,
episode_start_year, episode_end_year, overlap_year,
low_date, high_date, forward_gain_intraday,
forward_gain_close_confirmed, close_confirmed_peak_date,
overlap_start_date, overlap_end_date, overlap_trading_days,
in_year_episode_linked, truncated_by_year_boundary,
observed_reference_overlap
```

`yearly_big_winner_coverage_audit.csv` 至少包含：

```text
year, instrument, membership_days_in_year, readable_days_in_year,
missing_days, missing_required_fields, first_missing_date,
last_missing_date, excluded_from_big_winner_scan,
excluded_reason, coverage_status
```

### 6.2 年度和行业分布

```text
Explore8/outputs/reports/yearly_big_winner_year_summary.csv
Explore8/outputs/reports/yearly_big_winner_industry_summary.csv
```

至少回答：

- 每年 PIT universe 中有多少股票年满足 `>= 50%`。
- 大涨股票占当年 PIT universe 的比例。
- 盘中触达 50% 和收盘确认 50% 的数量差异。
- 每年大涨事件的平均涨幅、中位涨幅、最高涨幅。
- 每年大涨事件的平均持续交易日和中位持续交易日。
- 每年大涨事件平均振幅、最高振幅和成交额放大情况。
- 有多少事件被自然年边界截断，跨年审计是否改变年度判断。
- 哪些行业贡献了最多大涨股票。
- 哪些行业虽然大涨股票数量少但平均涨幅高。

### 6.3 市场和行业背景

```text
Explore8/outputs/reports/yearly_big_winner_market_context.csv
Explore8/outputs/reports/yearly_big_winner_regime_summary.csv
```

至少按以下维度聚合：

- market regime。
- market width 分位。
- benchmark 同期收益。
- industry regime。
- industry target 同期收益。
- 启动前 60 日市场收益。
- 启动前 60 日行业收益。
- 所有启动前统计必须标明锚点类型，区分 `low_date` 事后画像和可观察锚点画像。

### 6.4 规则错配归因

```text
Explore8/outputs/reports/yearly_big_winner_rule_miss_attribution.csv
```

至少包含：

```text
year, instrument, episode_rank, low_date, high_date,
entry_family, exit_family,
signal_search_start, signal_search_end,
anchor_search_start, anchor_search_end,
search_window_truncated, search_window_truncate_reason,
would_have_signal_near_start, first_signal_date,
entry_date, entry_price, signal_lag_trading_days,
would_exit_before_high,
exit_before_high_reason, missed_reason,
gain_before_first_signal_intraday,
gain_before_first_signal_close_confirmed,
gain_after_first_signal_intraday,
gain_lost_by_early_exit,
anchor_type_used_for_alignment
```

## 7. 报告必须回答的问题

最终扩展报告：

```text
Explore8/outputs/reports/explore8_big_winner_profile_report.md
```

必须回答：

- 2017-2024 每一年 PIT universe 中有哪些股票从年内低点到后续高点涨幅超过 50%。
- 哪些大涨事件属于盘中触达 50%，哪些属于收盘确认 50%。
- 哪些主升段跨越自然年边界，逐年统计是否切碎了完整趋势。
- 连续区间跨年扫描和年度扫描的结论差异是什么。
- 这些大涨事件平均持续多久，最快和最慢分别是什么。
- 大涨过程的平均每日振幅、最高振幅、成交量和成交额放大是否有稳定特征。
- 以可观察锚点看，大涨股启动前更像 breakout、pullback、趋势延续，还是底部修复。
- 当前 Explore8 EMA 同源规则为什么没有稳定抓住这些股票。
- 失败主要来自没有信号、信号太晚、过早退出、风控过滤、行业过滤、市场过滤，还是数据覆盖问题。
- 是否存在适合下一阶段单独研究的候选方向，例如 breakout coverage、early trend detection、post-low repair、volume expansion filter、late-entry avoidance。

报告结论必须保持诊断口径，不得写成“推荐交易策略”或“冻结候选”。

## 8. Manifest 和审计

新增或更新 manifest 字段：

```text
big_winner_profile_enabled
big_winner_threshold
big_winner_years
universe_point_in_time
industry_membership_point_in_time
adjusted_price_used
price_adjustment_mode
provider_mode
coverage_limited_years
big_winner_episode_rows
big_winner_stock_year_rows
big_winner_anchor_profile_rows
big_winner_cross_year_audit_rows
big_winner_coverage_audit_rows
rule_miss_attribution_rows
labels_used_for_trading_signal
historical_trade_results_used_for_labeling
```

必须满足：

- `labels_used_for_trading_signal = false`
- `historical_trade_results_used_for_labeling = false`
- `universe_point_in_time = true`
- `price_adjustment_mode` 必须是固定枚举值，且不得重复复权。

## 9. 执行入口建议

如果实现本扩展，建议在 `Explore8/scripts/run_explore8.py` 增加以下命令：

```text
profile-big-winners
big-winner-report
```

其中：

- `profile-big-winners` 生成大涨事件、股票年摘要、多锚点画像、跨年审计、覆盖审计、年度行业聚合和规则错配归因 CSV。
- `big-winner-report` 读取结构化 CSV，生成中文扩展报告。

第一版也可以先实现为独立脚本，但脚本必须落在：

```text
Explore8/scripts/
```

## 10. 验收标准

需求阶段验收：

- `Explore8/expand_requirement.md` 存在。
- 文档明确大涨事件来自 PIT universe，而不是静态股票池。
- 文档明确 `>= 50%` 的定义、低点到高点时间段、持续时间、平均每日振幅、最高振幅、成交量和成交额字段。
- 文档明确区分盘中触达 50% 和收盘确认 50%。
- 文档明确 `low_date` 是事后标签，并要求输出可观察锚点画像。
- 文档明确多锚点画像使用独立长表，不和事件表一行混写。
- 文档明确跨年事件审计，不能因为自然年切片漏掉完整主升段。
- 文档明确跨年事件来自连续区间扫描。
- 文档明确复权口径和 coverage audit schema。
- 文档明确本扩展是探查需求，不是策略回测和候选冻结。

实现阶段验收：

- 事件级、锚点画像和规则错配输出 CSV 都能直接追溯到 `year + instrument + low_date + high_date`。
- 任一大涨事件的低点必须早于或等于高点。
- 事件窗口内的 daily amplitude、volume、money、ATR、gap 计算有可复查字段。
- `intraday_50pct` 和 `close_confirmed_50pct` 必须分别可复算。
- `yearly_big_winner_anchor_profile.csv` 必须对每个事件输出固定锚点集合；锚点缺失时保留缺失行，不得自动回退为 `low_date`。
- `yearly_big_winner_rule_miss_attribution.csv` 中的信号、成交和退出日期必须落在显式搜索窗口内。
- `price_adjustment_mode` 必须和输入行情构建口径一致，不得重复复权。
- coverage audit 能解释所有被排除股票年。
- 报告能列出逐年大涨股票清单，并给出初步结构判断。

## 11. 测试计划

静态检查：

```text
uv run python -m compileall Explore8/scripts
```

数据画像：

```text
uv run python Explore8/scripts/run_explore8.py profile-big-winners --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

报告：

```text
uv run python Explore8/scripts/run_explore8.py big-winner-report --config Explore8/configs/yearly_rule_diagnostic_v1.yaml
```

当前阶段只要求整理扩展探查需求，不要求立即实现脚本或运行实验。
