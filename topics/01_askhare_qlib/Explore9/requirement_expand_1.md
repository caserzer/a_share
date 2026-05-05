# Explore9 扩展需求 1：P0.5 早期结构扩展探索

## 1. 背景

Explore9 P0 第一版已经完成 broad discovery 的基础目标：

- PIT 数据、标签、episode、source audit 和 manifest 已跑通。
- `primitive_feature_dictionary.csv` 已覆盖 10 类以上 feature family。
- P0 已输出单变量 lift、双变量 lift、年度稳定性、行业稳定性和 preliminary discovery leads。
- `broad_discovery_p0_minimum_coverage_met = true`。

但 P0 报告也暴露出一个关键问题：

```text
当前最强的 preliminary discovery leads 多数偏确认期、延展期或 hold tolerance，
还没有充分证明“足够早的 entry discovery 结构”已经被覆盖。
```

典型例子：

- `observable_late_acceleration_risk` precision 高，但语义偏后段，且 episode 去重后 lift 不同步。
- `post_30pct_from_recent_low` 对 hold / exit 很有价值，但不是初始 entry discovery。
- `trend_speed_bucket == speed_fast`、`ret20_universe_pctile == p90_100`、`relative_ret60_vs_benchmark == p90_100` 都要求 T 日已经有明显强势。
- 高波动、高 ATR、高振幅 lift 明显，但 P0 尚未区分“扩张性高波”和“破坏性高波”。
- stock-day 口径可能把同一个 winner 的连续强势日重复计数，导致部分 lead 的 pooled lift 高估。

因此，在进入 P1 formal hypothesis refine 前，需要先做一轮 P0.5 扩展探索。

## 2. 阶段定位

P0.5 是 P0 的扩展，不是 P1。

P0.5 的目标是：

```text
在保持 P0 数据纪律和 lift 审计口径不变的前提下，
扩展 early discovery、high-volatility decomposition、repair initiation、
cross-section leadership jump、money quality 和 sparse strong-day diagnostics，
确认是否存在比 P0 第一版更早、更可解释、更少依赖 stock-day 重复计数的 preliminary leads。
```

P0.5 不做：

- formal hypothesis generation。
- frozen strategy。
- Explore10 strategy backtest。
- shape clustering / motif discovery 的正式实现。
- 完整 hold / exit 策略设计。
- 使用 2025-2026 observed reference 做阈值选择、特征选择或 family 选择。

P0.5 可以做：

- 增加 P0 primitive。
- 增加 P0 pairwise / diagnostic combos。
- 增加 lead 分层榜单。
- 增加 false-positive 对照。
- 扩展报告分析。
- 为 P1 记录更清晰的候选方向和淘汰方向。

## 3. 核心问题

P0.5 必须回答以下问题：

1. **是否存在真正偏 early-entry 的 lead？**
   `early_entry_discovery` 主榜必须硬性排除 `post_20pct_from_recent_low = true`、`post_30pct_from_recent_low = true`、`observable_state_stage == observable_late_acceleration_risk` 等确认期状态；这些状态只能进入 confirmation / hold 榜或 shadow audit。P0.5 必须回答在这个更严格 denominator 下，是否仍有跨年份、跨行业、有正 lift 的 early discovery lead。

2. **高波动为什么有效？**
   高波动 lift 是来自上涨扩张、趋势延展、行业共振，还是来自少数 winner 的连续重复状态？破坏性高波和扩张性高波必须拆开。

3. **修复初期是否可识别？**
   在 trend score 尚低、涨幅尚未达到 post-20/post-30 的阶段，是否存在长期回撤后第一次稳定修复、低点抬高、高点抬高或区间收复信号？

4. **横截面领先是否比绝对强度更早？**
   排名跃迁、行业内领先、行业尚未同步前的个股强势，是否能比固定 top10% 强度分位更早发现 winner？

5. **成交额的有效形态是什么？**
   P0 已说明放量本身不是主线。P0.5 必须区分上涨中放量、回撤缩量、放量后价格保持、成交背离和失败放量。

6. **强势日是否只是 sparse diagnostic，还是可以解释 winner path？**
   涨停、接近涨停、gap up、极强实体日等样本较少，但可能提供路径诊断。P0.5 必须明确其泛化权限。

7. **去重后 lead 是否仍然成立？**
   P0.5 的主榜单必须同时看 stock-day、instrument-year、dedup trigger-event lift 和 winner episode coverage，不能只用 stock-day pooled lift 排名。

## 4. 数据与纪律

P0.5 沿用 Explore9 P0 的数据边界：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

硬约束：

- 每个 `date + instrument` 样本必须在当日 PIT membership 中。
- 行业归属必须按 PIT industry membership join。
- 成交额字段继续使用 `money`，不得改用 `amount`。
- OHLC 默认已调整，不得再次乘 `factor`。
- Explore8 输出只能作为背景、schema reference 或 audit reference。
- Explore8 / Explore3-Explore8 的交易结果、signals、daily candidates、model predictions、portfolio daily 不得作为 label、feature、selection input 或排序依据。
- 2025-2026 observed reference 只能观察，不得用于阈值选择。
- 所有新增输出必须落在 `Explore9/outputs/` 下。

## 5. P0.5 扩展探索范围

### 5.1 Entry Discovery 与 Confirmation / Hold 分榜

P0.5 必须把 leads 至少拆成三张榜：

- `early_entry_discovery`
- `confirmation_continuation`
- `hold_exit_tolerance`

`early_entry_discovery` 主榜 denominator 必须同时满足：

```text
post_20pct_from_recent_low = false
post_30pct_from_recent_low = false
observable_state_stage != observable_late_acceleration_risk
label_horizon_truncated = false
observed_reference_overlap = false
feature_eligible = true
```

在上述主榜之外，可以额外输出 shadow audit：

- `early_entry_shadow_with_post_20pct`
- `early_entry_shadow_with_post_30pct`
- `early_entry_shadow_with_late_acceleration`

shadow audit 只能用于解释样本迁移和生命周期差异，不得计入 `early_entry_discovery` 主榜 qualified lead。

`early_entry_discovery` 必须额外报告：

- trend speed 是否尚未进入最强 bucket。
- 是否已有修复迹象。
- 未来 120 日 50% high / close 的 lead time。
- 未来 240 日 100% high / close 的 lead time。

报告必须明确：

- 哪些 lead 只能用于 entry discovery。
- 哪些 lead 只能用于 confirmation。
- 哪些 lead 只适合 hold / exit tolerance。
- 哪些 lead 混合了 entry 和 hold 语义，不能直接进入 P1。

### 5.2 高波动拆解

P0.5 必须新增或派生 high-volatility decomposition primitive。

至少覆盖：

- 上涨日波动 vs 下跌日波动。
- 高振幅但 close 位于日内区间上部。
- 高振幅但 close 位于日内区间下部。
- 高 ATR 且 close 高于过去 N 日中位价。
- 高 ATR 且 close 跌破短期结构。
- 高波动 + 相对强度。
- 高波动 + 行业宽度改善。
- 高波动 + drawdown 受控。
- 高波动 + money quality 支持。
- 高波动 false-positive 对照。

需要区分：

```text
expansion_volatility
destructive_volatility
reversal_volatility
late_acceleration_volatility
failed_high_volatility
```

每个 high-volatility category 必须在 dictionary 中给出：

```text
category_id
human_readable_definition
formula_or_bin
lookback_window
required_columns
feature_eligible_rule
close_location_rule
trend_or_drawdown_context
evaluation_only_false_positive_definition
```

其中 `evaluation_only_false_positive_definition` 只能由 forward label 和评估结果计算，不得进入 T 日 feature、lead formula、candidate selection 或任何排序输入。

高波动 lead 不得只用 `volatility60 p90_100`、`amplitude20 p90_100`、`atr20_pct p90_100` 做结论，必须解释其结构来源。若某个分类无法用 T 日可观察公式定义，必须标记为 `diagnostic_only_not_p1_ready`。

### 5.3 修复初期结构

P0.5 必须补充早期修复原语，而不是只看已经大幅修复后的 continuation。

至少覆盖：

- 长期回撤后第一次收复 20 日 / 60 日中位价。
- 从 120 日或 240 日低点修复但尚未达到 20% / 30%。
- 低点抬高。
- 高点抬高。
- 低点抬高 + 高点尚未突破。
- 假跌破后快速收复。
- 回撤幅度大但近期下跌速度减弱。
- drawdown_from_high 与 repair_from_low 的二维组合。
- repair_from_low 与 relative strength 的二维组合。
- 修复初期 + 行业尚未同步。

报告必须说明：

- 这些结构是否比 P0 第一版 lead 更早。
- 是否牺牲了过多 precision。
- dedup trigger-event lift 和 winner episode coverage 是否仍支持该方向。

### 5.4 横截面 Rank Jump 与领先性

P0.5 必须扩展横截面异常和领先性原语。

至少覆盖：

- ret rank 5/20/60 日跃迁。
- money rank 5/20/60 日跃迁。
- industry rank 5/20/60 日跃迁。
- 个股从行业中位以下跃迁到行业前 20%。
- 个股进入全市场前 20% 但行业宽度尚未同步。
- 个股持续强于行业但行业尚未转强。
- 弱市场中的孤立强势。
- 市场转折初期的前排个股。
- 行业宽度刚改善时的前排个股。

P0.5 必须比较：

- absolute strength top10%。
- rank jump。
- rank jump + industry lag。
- rank jump + market weak。
- rank jump + industry width improving。

如果 rank jump 比绝对强度更早但 precision 较低，报告必须明确它是否适合作为 P1 的 first-stage candidate filter。

### 5.5 成交质量

P0 已说明单纯放量不是主线。P0.5 必须从成交质量角度重新拆解 money / volume。

至少覆盖：

- 上涨日成交放大。
- 下跌日成交放大。
- 回撤缩量。
- 放量后 3/5/10 日价格保持。
- 放量后快速跌破。
- money ratio 与 close location 的组合。
- money rank jump 与 ret rank jump 的组合。
- 高成交额持续天数。
- 成交放大但收益不跟随。
- 成交放大 + 行业宽度改善。

报告必须回答：

- 成交是 confirmation variable、failure warning，还是 early discovery variable？
- 成交质量是否能改善高波动 lead 的 false-positive 问题？
- 成交质量是否能提高 dedup trigger-event lift 或 winner episode coverage？

### 5.6 强势日路径与 Sparse Diagnostic

P0.5 必须把强势日作为 sparse diagnostic 单独处理。

至少覆盖：

- `limit_up_like`。
- 近 5 / 20 日涨停或接近涨停次数。
- 首次涨停 / 首次接近涨停。
- gap up 后是否收在上半区。
- gap up 后 3/5/10 日是否守住。
- 大阳线实体占比。
- 长上影强势失败。
- 极强日后是否缩量回撤但不破关键低点。

强势日 lead 必须标记：

```text
sparse_diagnostic = true / false
generalizable_entry_lead = true / false
path_explanation_only = true / false
```

如果样本少但 precision 高，不得直接升级为 general hypothesis；只能作为 P1 diagnostic 或 path decomposition 的输入。

### 5.7 去重优先的 Lead 排名

P0.5 必须新增去重优先 ranking。

每个 lead 至少报告：

- stock-day precision / lift。
- instrument-year hit rate / lift。
- dedup trigger-event precision / lift。
- winner episode coverage。
- stock-day 与 dedup trigger-event lift 差异。
- positive stock-day 是否被少数 trigger event 或 winner episode 主导。
- top1 instrument contribution。
- top5 instrument contribution。
- top1 episode contribution。
- top5 episode contribution。

去重口径必须固定如下：

```text
lead_stock_day_set =
  满足 lead formula、feature_eligible、label eligibility 和对应 lifecycle denominator 的 stock-day rows

lead_instrument_year_set =
  lead_stock_day_set 去重后的 instrument + calendar_year

positive_lead_instrument_year_set =
  lead_instrument_year_set 中至少有一个 lead stock-day 命中目标 forward label 的 instrument-year

instrument_year_hit_rate =
  positive_lead_instrument_year_count / lead_instrument_year_count

baseline_instrument_year_hit_rate =
  同一年、同一 horizon、同一 lifecycle denominator 下，
  所有 eligible instrument-year 中至少有一个 eligible stock-day 命中目标 forward label 的比例

instrument_year_hit_lift =
  instrument_year_hit_rate / baseline_instrument_year_hit_rate

trigger_count_per_instrument_year =
  lead_stock_day_set 在 instrument + calendar_year 内的触发次数
```

`instrument_year_hit_rate` 不是 precision，不能单独用于证明 lead 有效。每个 lead 必须同时报告 `mean_trigger_count_per_instrument_year`、`median_trigger_count_per_instrument_year` 和 `p95_trigger_count_per_instrument_year`，避免高频触发 lead 只靠“年内命中过一次”获得虚高评价。

`episode precision` 不得直接把 future winner episode 当作 denominator，因为 negative stock-day 没有自然 episode id。P0.5 必须改用 `dedup trigger-event` 作为 precision denominator：

```text
lead_trigger_event =
  同一 instrument 内，连续或间隔不超过 dedup_gap_trading_days 的 lead_stock_day_set 聚合事件

default dedup_gap_trading_days = 20

positive_lead_trigger_event =
  trigger event 的 first_trigger_date 之后，在目标 horizon 内命中目标 forward label

dedup_trigger_event_precision =
  positive_lead_trigger_event_count / lead_trigger_event_count

baseline_trigger_event_precision =
  同一年、同一 horizon、同一 lifecycle denominator 下，
  使用 baseline_eligible_stock_day_set 生成 baseline_pseudo_trigger_event 后的 positive rate

baseline_eligible_stock_day_set =
  满足 label eligibility、lifecycle denominator、
  以及该 lead 所需所有 feature eligibility 前置条件的 stock-day rows，
  但不叠加 lead formula_or_bin

baseline_pseudo_trigger_event =
  对每个 instrument + calendar_year，
  从 baseline_eligible_stock_day_set 的首个 eligible date 开始，
  每隔 dedup_gap_trading_days 取一个 pseudo first_trigger_date；
  不得把全部连续 eligible 日期直接合并成一个长事件

dedup_trigger_event_lift =
  dedup_trigger_event_precision / baseline_trigger_event_precision
```

同时必须报告 winner episode coverage：

```text
winner_episode_coverage =
  研究期独立重算的大涨 episode 中，
  在 episode high_date 之前且满足 lead time 要求的窗口内至少出现一次 lead trigger 的 episode 占比
```

`dedup_trigger_event_lift` 用于排序，`winner_episode_coverage` 用于解释覆盖能力；二者不得混为一个指标。

P0.5 主报告不能只按 stock-day lift 排序。推荐排序口径：

1. dedup trigger-event lift 为正。
2. instrument-year lift 为正。
3. distinct years 足够。
4. top1 industry concentration 不过高。
5. stock-day precision 和 lead time 有实际意义。

## 6. 最低覆盖要求

P0.5 最低覆盖不是替代 P0，而是在 P0 基础上扩展。

覆盖要求必须满足：

- P0 enabled primitives 总数扩展到至少 `90` 个。
- 新增 primitive 至少 `35` 个。
- pairwise / diagnostic combos 总数扩展到至少 `30` 个。
- 至少 `10` 个 combos 专门用于 high-volatility decomposition。
- 至少 `8` 个 combos 专门用于 repair initiation。
- 至少 `6` 个 combos 专门用于 rank jump / leadership。
- 至少 `6` 个 combos 专门用于 money quality。
- 至少 `5` 个 sparse strong-day diagnostic candidate patterns。
- 至少输出 `early_entry_discovery`、`confirmation_continuation`、`hold_exit_tolerance` 三类榜单。

专门用于某一类的 combo 在最低覆盖计数中默认不得跨类别重复计数。同一个公式可以在报告中附加 secondary tags，但只能选择一个 `primary_combo_family` 计入最低覆盖。

发现结果不得用“明确否定”冒充 lead。P0.5 必须分别报告：

```text
tested_early_entry_candidate_patterns >= 8
tested_high_volatility_candidate_patterns >= 10
tested_repair_initiation_candidate_patterns >= 8
tested_rank_jump_candidate_patterns >= 6
tested_money_quality_candidate_patterns >= 6

qualified_early_entry_leads >= 0
qualified_high_volatility_leads >= 0
qualified_repair_initiation_leads >= 0
qualified_rank_jump_leads >= 0
qualified_money_quality_leads >= 0
```

如果某类 `qualified_*_leads = 0`，报告和 `p0_5_candidate_pattern_audit.csv` 必须输出 negative evidence，包括样本数、precision、lift、年度稳定性、dedup trigger-event lift、winner episode coverage 和失败原因。

如果无法满足，报告必须写明：

```text
explore9_p0_5_minimum_coverage_met = false
```

并说明缺失原因。

## 7. 输出文件

P0.5 至少新增以下报告文件：

```text
Explore9/outputs/reports/p0_5_primitive_feature_dictionary.csv
Explore9/outputs/reports/p0_5_primitive_feature_coverage.csv
Explore9/outputs/reports/p0_5_univariate_lift.csv
Explore9/outputs/reports/p0_5_pairwise_lift.csv
Explore9/outputs/reports/p0_5_lead_ranking_stock_day.csv
Explore9/outputs/reports/p0_5_lead_ranking_instrument_year.csv
Explore9/outputs/reports/p0_5_lead_ranking_dedup_trigger_event.csv
Explore9/outputs/reports/p0_5_winner_episode_coverage.csv
Explore9/outputs/reports/p0_5_early_entry_discovery_leads.csv
Explore9/outputs/reports/p0_5_confirmation_continuation_leads.csv
Explore9/outputs/reports/p0_5_hold_exit_tolerance_leads.csv
Explore9/outputs/reports/p0_5_high_volatility_decomposition.csv
Explore9/outputs/reports/p0_5_repair_initiation_leads.csv
Explore9/outputs/reports/p0_5_rank_jump_leadership_leads.csv
Explore9/outputs/reports/p0_5_money_quality_leads.csv
Explore9/outputs/reports/p0_5_sparse_strong_day_diagnostics.csv
Explore9/outputs/reports/p0_5_candidate_pattern_audit.csv
Explore9/outputs/reports/p0_5_false_positive_audit.csv
Explore9/outputs/reports/p0_5_scope_completion_audit.csv
Explore9/outputs/reports/p0_5_run_manifest.json
Explore9/outputs/reports/explore9_p0_5_expand_1_report.md
```

可以复用 P0 的 label panel 和 episode labels，但 `p0_5_run_manifest.json` 必须独立记录：

```text
p0_label_panel_reused = true / false
p0_episode_labels_reused = true / false
p0_5_new_feature_panel_generated = true / false
config_path
command_line
input_report_paths
input_cache_paths
output_report_paths
output_cache_paths
row_count_by_output
column_count_by_output
file_size_by_output
observed_reference_used_for_selection = false
historical_trade_results_used_for_labeling = false
historical_trade_results_used_for_signal = false
historical_trade_results_used_for_selection = false
```

## 8. 报告要求

`explore9_p0_5_expand_1_report.md` 必须用中文撰写，并包含：

- P0.5 与 P0 第一版的差异。
- 是否仍建议进入 P1。
- 是否因为 P0.5 发现不足而需要继续 broad discovery。
- early-entry、confirmation、hold/exit 三类 lead 的分离结果。
- 高波动有效性的结构解释。
- 修复初期 lead 是否存在。
- rank jump 是否比绝对强度更早。
- 成交质量是否能改善 lead。
- sparse strong-day 是否只是 path diagnostic。
- stock-day、instrument-year hit-rate、dedup trigger-event、winner episode coverage 四种口径的差异。
- 哪些 P0 第一版 lead 被降级。
- 哪些新增 lead 值得进入 P1。
- 哪些方向明确不值得进入 P1。

报告结论必须给出以下四类判断之一：

```text
recommendation = proceed_to_p1_after_p0_5
recommendation = proceed_to_p1_for_confirmation_hold_only_continue_entry_discovery
recommendation = continue_p0_broad_discovery
recommendation = stop_explore9_due_to_no_stable_discovery
```

不得直接输出：

```text
recommendation = proceed_to_explore10_backtest
```

Explore10 只能作为远期路径记录。

## 9. 成功标准

P0.5 成功不要求找到可交易策略。

最低成功标准：

- P0.5 新增原语和组合通过 feature eligibility、source audit 和 coverage audit。
- 所有主 lift 排除 `label_horizon_truncated = true` 和 `observed_reference_overlap = true`。
- 三类 lead 榜单能明确区分 entry、confirmation 和 hold/exit。
- 至少说明一个高波动 lead 的结构来源，或明确证明高波动 lift 主要来自重复计数 / 确认期。
- 至少给出 early-entry 是否存在的明确判断。
- 至少给出去重后仍值得进入 P1 的 lead，或明确说明没有足够稳定 lead。
- 最终报告清晰说明是否进入 P1。

如果 P0.5 没有任何 early-entry lead 达标，仍可视为有效研究结果，但必须明确：

```text
未发现足够稳定的 early-entry 结构。
当前 Explore9 的有效方向主要是 confirmation / continuation / hold tolerance，
不应把这些 lead 误写成初始买点。
```

## 10. 执行边界

本文件只定义 Explore9 P0.5 的扩展需求。

后续如果实现，建议新增独立命令或配置，避免覆盖 P0 第一版结果：

```text
uv run python Explore9/scripts/run_explore9.py profile-p0-5 --config Explore9/configs/broad_discovery_expand_1.yaml
uv run python Explore9/scripts/run_explore9.py report-p0-5 --config Explore9/configs/broad_discovery_expand_1.yaml
```

实现时不得删除或重写 P0 第一版报告，除非用户明确要求重新生成。
