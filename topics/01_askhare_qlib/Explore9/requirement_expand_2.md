# Explore9 扩展需求 2：P0.6 启动观察池后的可执行入场触发与失败过滤探索

## 1. 背景

Explore9 P0 和 P0.5 已经证明两件事：

1. 大 winner 的可观察路径中，高波动、强趋势、相对强度、强势日、成交保持和 post-20/post-30 continuation 都有明显信息。
2. 这些信息多数更适合 confirmation / continuation / hold tolerance，而不是初始 entry。

P0.5 的关键负向结论是：

```text
很多结构在 stock-day 和 dedup trigger-event 口径下有明显 lift，
但一旦切到 instrument-year 口径，就全部低于 baseline。
```

这说明当前线索不能直接回答：

```text
什么时候上车？
```

同时，用户的实际目标也不是最低点 early entry，而是：

```text
目标标的已经出现启动迹象后，
如何找到一个可执行、可审计、可止损的上车点。
```

因此需要新增 P0.6。

## 2. 阶段定位

P0.6 是 Explore9 broad discovery 的第二轮扩展，不是 P1，也不是策略回测。

P0.6 不能被理解为：

```text
已经找到入场规则，下一步做策略回测。
```

P0.6 必须被理解为：

```text
在一个 T 日可观察的启动观察池里，
研究延迟入场、回踩守住、再次转强、成交确认、失败过滤，
是否能在可执行价格下同时降低回撤、保留大 winner 上行空间。
```

P0.6 的目标是：

```text
把 P0/P0.5 中的“启动观察信号”和“持有确认信号”拆开，
研究启动事件之后的 3/5/10/20 日内，
哪些回踩、守住、再确认或失败过滤结构可以形成可执行 entry trigger。
```

更严格地说，P0.6 的主研究问题是：

```text
给定一个 T 日可观察、未进入 post-20/post-30/late-acceleration 的 launch observation pool，
在 launch 后 3/5/10/20 日内，
等待价格守住、缩量回踩、higher low 再转强、成交确认或强势日 follow-through，
是否能在 next-open 可执行口径下，
相对 all-launch direct entry 和 matched-delay baseline，
同时降低 false positive / drawdown，
控制 missed gain / missed winner，
并保留 120 日 50% high/close 或 240 日 100% winner upside？
```

P0.6 必须拆成三段式研究：

```text
P0.6A: Launch observation pool 质量审计
P0.6B: Entry trigger after launch 可执行触发探索
P0.6C: Failure filter / stop reference / missed-winner 审计
```

顺序硬约束：

- 先审 launch pool，再审 entry trigger。
- launch pool 本身如果没有足够 winner upside 覆盖，后续 entry trigger 只能解释为风险过滤或持有确认，不能进入 P1 entry candidate。
- entry trigger 如果只跑赢 trigger-convertible baseline，但跑不赢 all-launch direct 和 matched-delay baseline，不能证明入场有效。

P0.6 不做：

- 最低点预测。
- 单日强势信号直接买入。
- 完整持有策略。
- 完整仓位管理。
- Explore10 strategy backtest。
- 使用 2025-2026 observed reference 做阈值选择。
- 使用 Explore3-Explore8 历史交易结果作为 label、feature、selection input 或排序依据。

P0.6 可以做：

- 定义 launch observation event。
- 审计 launch observation pool 质量。
- 定义 entry candidate event sequence。
- 定义 invalidation / failed launch。
- 比较直接追入 vs 等待确认入场。
- 比较 matched-delay baseline。
- 比较不同等待窗口。
- 审计 missed-winner、missed-gain 和 stop-distance。
- 生成 entry trigger discovery report。
- 为 P1 formal entry hypothesis 记录候选方向和淘汰方向。

## 3. 核心问题

P0.6 必须回答以下问题：

1. **启动观察池本身是否有足够质量？**

   P0.6 必须先回答 launch observation pool 是否真的覆盖大 winner 路径，而不是直接在幸存样本上研究 entry trigger。

   launch pool 至少按以下口径拆分：

   ```text
   primary_pre_20_launch_pool
   primary_pre_30_launch_pool
   sparse_strong_day_diagnostic_pool
   post_20_30_hold_only_pool
   late_acceleration_hold_only_pool
   ```

   主 entry leaderboard 只允许 `primary_pre_20_launch_pool` 和 `primary_pre_30_launch_pool`。

2. **启动后是否存在更好的入场触发？**

   当股票已经出现启动观察事件后，直接追入、等待 3/5/10/20 日确认、等待回踩守住、等待再次转强，哪一种后续收益 / 回撤结构更好？

3. **哪些启动观察事件只能观察，不能买？**

   例如高波 + 相对强、首次涨停、gap up、rank jump、修复收复等，P0.6 必须区分：

   ```text
   launch_observation_only
   entry_trigger_candidate
   confirmation_hold_only
   invalidation_warning
   ```

4. **“强后能守住”是否比“强当天追入”更好？**

   对每类 launch event，必须比较：

   - launch day close 直接入场。
   - launch 后 3 日价格保持入场。
   - launch 后 5 日价格保持入场。
   - launch 后回踩缩量但不破关键低点入场。
   - launch 后 higher low + 再转强入场。

5. **入场失败点是否能被 T 日可观察地定义？**

   每个 entry trigger 必须同时给出 invalidation rule，例如：

   - 跌破 launch day low。
   - 跌破 pullback low。
   - 跌破 20 日中位价 `median20` 或 `ema20`。
   - 放量后 3/5 日不能守住。
   - 长上影放量失败。
   - 相对强度消失。

   这里的 invalidation rule 只能作为：

   ```text
   pre_entry_no_trade_filter
   executable_entry_stop_reference
   post_entry_audit
   ```

   不得把 entry 之后才发生的结果反过来用于筛选 entry 样本。

6. **入场触发是否降低 false positive？**

   P0.6 不能只看收益 lift，必须同时比较：

   - false positive rate。
   - entry 后最大回撤。
   - entry 后达到 20% / 50% high 的概率。
   - entry 后达到 20% / 50% close 的概率。
   - entry 后 drawdown before gain。
   - missed gain from waiting。

7. **是否漏掉真正 winner？**

   P0.6 必须审计：

   ```text
   launch_winner_without_entry_trigger_count
   launch_winner_without_entry_trigger_rate
   missed_winner_due_to_no_trigger_rate
   direct_entry_winner_missed_by_waiting_rate
   missed_50pct_winner_episode_coverage
   missed_100pct_winner_episode_coverage
   ```

   如果某个 trigger 明显降低 false positive，但漏掉大部分 winner，它只能作为保守确认或加仓条件，不能作为主入场。

8. **是否存在可进入 P1 的入场假设？**

   P0.6 必须明确：

   - 哪些 entry trigger 可以进入 P1 formal hypothesis。
   - 哪些只能作为观察池。
   - 哪些只能作为 hold / continuation。
   - 哪些必须淘汰。

## 4. 数据与纪律

P0.6 沿用 Explore9 数据边界：

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
- P0/P0.5 输出可以作为 schema reference、candidate family reference 和 audit reference。
- P0/P0.5 输出不得直接作为 label，不得把其 ranked result 作为训练或排序输入。
- Explore3-Explore8 的交易结果、signals、daily candidates、model predictions、portfolio daily 不得作为 label、feature、selection input 或排序依据。
- 2025-2026 observed reference 只能观察，不得用于阈值选择。
- 所有新增输出必须落在 `Explore9/outputs/` 下。

允许复用：

```text
Explore9/outputs/cache/stock_day_label_panel.parquet
Explore9/outputs/reports/episode_lifecycle_labels.csv
Explore9/outputs/reports/p0_5_primitive_feature_dictionary.csv
Explore9/outputs/reports/p0_5_pairwise_lift.csv
Explore9/outputs/reports/p0_5_candidate_pattern_audit.csv
```

复用 P0/P0.5 输出时，manifest 必须记录：

```text
p0_label_panel_reused = true / false
p0_5_feature_panel_reused = true / false
p0_5_reports_used_for_schema_or_family_reference_only = true
p0_5_ranked_results_used_for_selection = false
historical_trade_results_used_for_labeling = false
historical_trade_results_used_for_signal = false
historical_trade_results_used_for_selection = false
observed_reference_used_for_selection = false
same_close_proxy_used_in_main_leaderboard = false
post_20_30_launch_used_in_primary_entry_leaderboard = false
post_entry_invalidation_audit_used_for_selection = false
false_positive_definitions_used_for_selection = false
matched_delay_baseline_required = true
entry_labels_rebased_to_entry_price = true
p0_stock_day_label_panel_used_for_entry_label_directly = false
entry_price_reference_used = next_open
missed_gain_uses_entry_price_reference = true
primary_lifecycle_gate_applied = true
instrument_year_ranking_required = true
convertible_baseline_required = true
launch_pool_quality_audit_required = true
missed_winner_audit_required = true
execution_feasibility_audit_required = true
```

## 5. 样本单位

P0.6 的基本样本单位不是普通 stock-day，而是 event sequence。

### 5.1 Launch Observation Event

`launch_observation_event` 表示股票已经出现启动迹象，但还不等于可买入点。

每个 launch event 至少包含：

```text
launch_event_id
launch_episode_id
instrument
launch_date
launch_family
launch_formula
launch_close
launch_high
launch_low
launch_volume_or_money_context
launch_market_regime
launch_industry_regime
launch_observable_stage
launch_pool
launch_primary_entry_leaderboard_eligible
launch_lifecycle_role
late_acceleration_flag
```

第一版 launch family 至少覆盖：

- `expansion_high_volatility`
- `high_vol_money_upper_close`
- `rank_jump_leadership`
- `repair_reclaim`
- `first_limit_up_like`
- `first_near_limit_up_like`
- `gap_up_upper_close`
- `strong_body_day`
- `post_20pct_relative_strength`
- `post_30pct_relative_strength`

Launch event 必须去重：

```text
same instrument launch events with gap <= 20 trading days collapse into one launch episode
```

默认字段：

```text
launch_dedup_gap_trading_days = 20
```

### 5.1.1 Launch Family v1 公式矩阵

P0.6 不能只写 launch family 名称。第一版实现必须输出可复现的 `launch_formula_matrix`，每个 family 必须有明确公式、阈值、角色和主榜资格。

通用派生字段默认如下，除非配置文件显式覆盖：

```text
ret_1d = close / prev_close - 1
ret_5d = close / close_5d_ago - 1
ret_20d = close / close_20d_ago - 1
day_range = high / low - 1
body_ret = close / open - 1
close_location = (close - low) / max(high - low, eps)
money_ratio_20 = money / rolling_median(money, 20)
money_ratio_60 = money / rolling_median(money, 60)
ret_rank_20d_market = percentile_rank(ret_20d within PIT universe on date)
ret_rank_20d_market_5d_ago = ret_rank_20d_market shifted by 5 trading days per instrument
money_rank_20d_market = percentile_rank(money_ratio_20 within PIT universe on date)
ema20 = EMA(close, 20)
ema20_1d_ago = ema20 shifted by 1 trading day per instrument
median20 = rolling_median(close, 20)
low60 = rolling_min(low, 60)
low90 = rolling_min(low, 90)
low120 = rolling_min(low, 120)
launch_gain_from_recent_low_60d = close / low60 - 1
launch_gain_from_recent_low_90d = close / low90 - 1
launch_gain_from_recent_low_120d = close / low120 - 1
industry_breadth_20d = PIT industry member share with close > ema20
```

第一版 launch matrix 至少包含：

| launch_family | v1 触发公式 | launch_pool | launch_lifecycle_role | primary_entry_leaderboard_eligible |
|---|---|---|---|---|
| `expansion_high_volatility` | `day_range >= 0.08 and ret_1d > 0 and close_location >= 0.55` | `primary_pre_20_launch_pool` | `launch_observation_only` | `true` |
| `high_vol_money_upper_close` | `day_range >= 0.08 and money_ratio_20 >= 1.5 and close_location >= 0.65` | `primary_pre_20_launch_pool` | `launch_observation_only` | `true` |
| `rank_jump_leadership` | `ret_rank_20d_market >= 0.80 and ret_rank_20d_market - ret_rank_20d_market_5d_ago >= 0.30` | `primary_pre_30_launch_pool` | `launch_observation_only` | `true` |
| `repair_reclaim` | `close > ema20 and close_1d_ago <= ema20_1d_ago and ret_5d > 0` | `primary_pre_20_launch_pool` | `launch_observation_only` | `true` |
| `first_limit_up_like` | `ret_1d >= 0.095 and close_location >= 0.80 and no same-family event in prior 60 trading days` | `sparse_strong_day_diagnostic_pool` | `sparse_launch_observation` | `false` |
| `first_near_limit_up_like` | `ret_1d >= 0.07 and ret_1d < 0.095 and close_location >= 0.75 and no same-family event in prior 60 trading days` | `sparse_strong_day_diagnostic_pool` | `sparse_launch_observation` | `false` |
| `gap_up_upper_close` | `open / prev_close - 1 >= 0.03 and close >= open and close_location >= 0.60` | `sparse_strong_day_diagnostic_pool` | `sparse_launch_observation` | `false` |
| `strong_body_day` | `body_ret >= 0.05 and close_location >= 0.70 and money_ratio_20 >= 1.2` | `sparse_strong_day_diagnostic_pool` | `sparse_launch_observation` | `false` |
| `post_20pct_relative_strength` | `launch_gain_from_recent_low_60d >= 0.20 and ret_rank_20d_market >= 0.70` | `post_20_30_hold_only_pool` | `add_on_or_hold_only` | `false` |
| `post_30pct_relative_strength` | `launch_gain_from_recent_low_90d >= 0.30 and ret_rank_20d_market >= 0.70` | `post_20_30_hold_only_pool` | `add_on_or_hold_only` | `false` |

硬约束：

- `post_20pct_relative_strength` 和 `post_30pct_relative_strength` 只能进入 add-on / hold / continuation audit，不得进入主 entry leaderboard。
- `first_limit_up_like`、`first_near_limit_up_like`、`gap_up_upper_close` 和 `strong_body_day` 必须标记 `sparse_diagnostic = true`，只能进入 follow-through、pullback-hold 或 diagnostic board，不得进入 direct-launch recommended board。
- late acceleration 必须额外识别为 `late_acceleration_hold_only_pool`。默认规则为 `launch_gain_from_recent_low_120d >= 0.50` 或配置中定义的 late-stage lifecycle label。
- 每条 launch formula 必须记录 `lookback_days`、`thresholds`、`required_fields`、`launch_pool`、`lifecycle_role`、`primary_entry_leaderboard_eligible`。
- 上述通用派生字段必须进入 `p0_6_launch_event_dictionary.csv`、`p0_6_launch_formula_matrix.csv` 和 `p0_6_run_manifest.json`，不能只在代码里隐式出现。
- 如果实现中调整任何阈值，必须在 config 和 dictionary 输出中同时记录，不能只写在代码里。

### 5.1.1.1 Launch Pool 生命周期 Gate

Launch family 公式只决定候选事件，最终 `launch_pool` 必须先经过生命周期 gate。不得因为当天再次出现高波、放量或 rank jump，就把已经进入 continuation / late acceleration 的样本重新放回 entry 主榜。

优先级规则：

```text
if late_acceleration_flag = true:
    launch_pool = late_acceleration_hold_only_pool
    primary_entry_leaderboard_eligible = false
elif post_30pct_relative_strength = true:
    launch_pool = post_20_30_hold_only_pool
    primary_entry_leaderboard_eligible = false
elif post_20pct_relative_strength = true and launch_family not eligible for primary_pre_30:
    launch_pool = post_20_30_hold_only_pool
    primary_entry_leaderboard_eligible = false
```

`primary_pre_20_launch_pool` 必须同时满足：

```text
post_20pct_relative_strength = false
post_30pct_relative_strength = false
late_acceleration_flag = false
launch_gain_from_recent_low_60d < 0.20
```

`primary_pre_30_launch_pool` 必须同时满足：

```text
post_30pct_relative_strength = false
late_acceleration_flag = false
launch_gain_from_recent_low_90d < 0.30
```

如果某个 family 公式触发但不满足其声明的 primary pool gate，必须：

```text
primary_entry_leaderboard_eligible = false
launch_pool = lifecycle_gate_rejected_or_hold_only
```

并在 launch pool quality audit 中单独报告 `lifecycle_gate_rejected_count`。

### 5.1.2 Launch Pool 质量审计

P0.6A 必须先输出 launch pool 质量审计，再进入 entry trigger 排名。

每个 launch pool 至少报告：

```text
launch_pool
launch_episode_count
distinct_instrument_count
distinct_year_count
future_20pct_high_60d_rate_from_launch
future_50pct_high_120d_rate_from_launch
future_50pct_close_120d_rate_from_launch
future_100pct_high_240d_rate_from_launch
future_100pct_close_240d_rate_from_launch
winner_episode_coverage_from_launch
top1_instrument_contribution
top5_instrument_contribution
median_launch_to_20pct_high_days
median_launch_to_50pct_high_days
lifecycle_gate_rejected_count
post_20_30_contamination_count
late_acceleration_contamination_count
```

解释规则：

- `primary_pre_20_launch_pool` 和 `primary_pre_30_launch_pool` 是主 entry discovery 池。
- `sparse_strong_day_diagnostic_pool` 只能输出 secondary / diagnostic / follow-through board。
- `post_20_30_hold_only_pool` 和 `late_acceleration_hold_only_pool` 只能输出 hold / add-on / continuation / failure audit，不得进入主 entry leaderboard。
- 如果 launch pool 本身的 `future_50pct_high_120d_rate_from_launch` 或 `winner_episode_coverage_from_launch` 过低，entry trigger 即使短线表现较好，也不得进入 P1 candidate。

### 5.2 Entry Candidate Event

`entry_candidate_event` 表示 launch 后出现可执行入场触发。

每个 entry event 必须从某个 launch event 派生：

```text
entry_event_id
launch_event_id
launch_episode_id
instrument
launch_date
entry_signal_date
entry_date
entry_signal_delay_trading_days
entry_execution_delay_trading_days
entry_family
entry_formula
entry_price_reference
entry_execution_assumption
next_open_gap_from_signal_close
next_open_vs_launch_close
entry_to_invalidation_risk_pct
entry_open_above_prior_high_pct
next_day_limit_like_open_flag
stop_distance_too_wide_flag
invalidation_rule_id
invalidation_price_reference
entry_rank_within_launch
entry_rank_within_launch_family
is_first_valid_entry_for_launch_family
is_primary_counted_entry
```

Entry event 必须满足：

```text
entry_signal_date > launch_date
entry_date > entry_signal_date
entry_date = next_trading_day(entry_signal_date)
entry_signal_date <= launch_date + max_entry_signal_wait_trading_days
entry_date <= launch_date + max_entry_execution_wait_trading_days
default max_entry_signal_wait_trading_days = 20
default max_entry_execution_wait_trading_days = 21
entry_date sample is PIT member
label_horizon_truncated = false
observed_reference_overlap = false
```

执行时点硬约束：

- entry trigger 条件只能使用 `entry_signal_date` 当日收盘及以前可观察信息。
- 默认可执行入场日为 `entry_signal_date` 的下一交易日，默认价格引用为 `next_open`。
- 如果为了 discovery 同时输出 `same_close_proxy`，必须单独标记 `entry_execution_assumption = same_close_proxy`，不得混入主榜。
- `launch_day_direct_entry` 只能作为 baseline，执行假设可用 `launch_close_proxy` 和 `next_open_after_launch` 两版，但必须分开报告。
- 所有 hold 3/5/10 日触发的 `entry_signal_date` 分别是 launch 后第 3/5/10 个交易日，`entry_date` 是其下一交易日。
- higher-low 不能使用 centered pivot 或未来确认；若需要确认，只能在确认日收盘后生成 signal。

可执行性硬约束：

- 主榜 entry 必须计算 `next_open_gap_from_signal_close`。
- 主榜 entry 必须计算 `next_open_vs_launch_close`，用于判断等待后是否已经错过过多空间。
- 主榜 entry 必须计算 `entry_to_invalidation_risk_pct = entry_price_reference / invalidation_price_reference - 1`。
- 如果 `entry_to_invalidation_risk_pct` 过高，必须标记 `stop_distance_too_wide_flag = true`。
- 默认 P1 candidate 需要 `median_entry_to_stop_risk_pct <= 0.12`；如果放宽到 `0.15`，必须在报告中说明原因。
- first-limit-up-like、gap-up、strong-body 等强势日后必须额外报告 `next_day_limit_like_open_flag` 和 `entry_open_above_prior_high_pct`。

不得把 launch day 本身直接当作唯一 entry。P0.6 可以输出 `launch_day_direct_entry` 作为对照，但它不是推荐默认。

## 6. Entry Trigger 候选族

P0.6 第一版必须覆盖以下 entry trigger families。

### 6.1 Price Hold After Launch

研究 launch 后价格能否守住。

至少覆盖：

- launch 后第 3 日 close 不低于 launch close，signal 在第 3 日收盘生成，entry 为下一交易日。
- launch 后第 5 日 close 不低于 launch close，signal 在第 5 日收盘生成，entry 为下一交易日。
- launch 后第 10 日 close 不低于 launch close，signal 在第 10 日收盘生成，entry 为下一交易日。
- launch 后 3/5/10 日窗口内 low 不跌破 launch low。
- launch 后 3/5/10 日窗口末 close 仍在 `ema20` / `median20` 之上。

必须比较：

```text
launch_day_direct_entry
hold_3d_entry
hold_5d_entry
hold_10d_entry
```

### 6.2 Pullback Hold Entry

研究启动后回踩是否提供更好的入场。

至少覆盖：

- launch 后出现 3%-8% 回撤，但回撤 low 不破 launch low。
- launch 后出现 5%-12% 回撤，但回撤 low 不破 20 日中位价 `median20`。
- 回撤期间 money ratio 低于 launch day。
- 回撤期间 close location 不连续 2 日落在日内下半区。
- 回撤后重新收回 `ema20` / `median20`，signal 在收回日收盘生成，entry 为下一交易日。

必须报告：

```text
pullback_depth
pullback_duration_trading_days
pullback_money_contraction
pullback_low_vs_launch_low
entry_after_reclaim
```

### 6.3 Higher Low Re-acceleration Entry

研究启动后是否形成更高低点并再次转强。

至少覆盖：

- launch 后形成可确认 higher low：候选 low 高于 launch low，且之后 close 收回候选 low 前 2 日高点。
- higher low 确认后 3/5 日内 ret rank 再次跃迁。
- higher low 确认后 close 重新进入 20 日相对强分位前 20%。
- higher low 确认后 money quality 改善。
- higher low 确认后行业宽度继续改善。

Higher low 的 signal date 是确认日，不是候选 low 当日；不得用未来 pivot 直接把 low 当成事前信号。

### 6.4 Volume Confirmation Entry

研究成交质量是否能把观察信号升级为入场信号。

至少覆盖：

- launch 后放量，但价格 3/5 日保持。
- launch 后缩量回撤，再次放量转强。
- money rank jump + ret rank jump 二次出现。
- 高成交额持续但 drawdown 受控。
- 放量后不跌破关键低点。

二次放量、rank jump 二次出现或持续成交确认都以确认日收盘作为 `entry_signal_date`，下一交易日作为 `entry_date`。

### 6.5 Sparse Strong-Day Follow-through Entry

研究强势日后是否可以等待 follow-through 入场。

至少覆盖：

- 首次涨停后 3/5 日不破涨停日 low。
- 首次接近涨停后 3/5 日不破强势日 low。
- gap up 上半区后 3/5 日守住 gap day low。
- 极强实体日后缩量回撤不破关键低点。
- 强势日后再次强势日。

强势日不得直接升级为入场，必须有 follow-through 或 pullback hold。

再次强势日以再次强势日收盘作为 `entry_signal_date`，下一交易日作为 `entry_date`。

主榜硬约束：

- `sparse_strong_day_diagnostic_pool` 只能进入 `follow_through_entry`、`pullback_hold_entry` 或 diagnostic board。
- `sparse_strong_day_diagnostic_pool` 不得进入 `direct_launch_entry_recommended`。
- 如果 sparse strong-day trigger 只表现为 continuation / hold tolerance，必须标记为 `hold_or_add_on_only`。

### 6.6 Failure Filter

每个 entry trigger 必须同时定义失败过滤，但必须拆成两类：

```text
pre_entry_failure_filter: 入场前或 signal 当日可观察，用于决定不生成 entry。
post_entry_invalidation_audit: 入场后才知道，只能用于评价和止损审计，不得用于筛选 entry 样本。
```

`pre_entry_failure_filter` 至少覆盖：

- high-vol 后跌破 launch low。
- gap up 后 3/5 日回补并跌破 gap day low。
- 放量后 3/5 日 close 低于 launch close。
- 长上影 + 放量 + close location 下半区。

`post_entry_invalidation_audit` 至少覆盖：

- entry 后 10 日内跌破 invalidation price。
- entry 后相对强度跌出市场前 40%。
- entry 后行业宽度恶化。
- entry 后 20 日内未出现任何 10% high gain 且最大回撤超过 12%。

Failure filter 只能使用 T 日或 T 日以前可观察信息，不得使用 forward label。Post-entry audit 是 evaluation-only，manifest 必须记录：

```text
false_positive_definitions_used_for_selection = false
post_entry_invalidation_audit_used_for_selection = false
```

### 6.7 Entry 去重与多触发计数

同一个 launch episode 可能派生多个 entry trigger。P0.6 必须避免重复计数造成虚假 lift。

主榜计数规则：

```text
primary_counting_unit = launch_episode + entry_family
primary_entry = first valid entry by entry_signal_date within launch_episode + entry_family
secondary_entries = later entries from same launch_episode + entry_family
```

硬约束：

- 主 leaderboard 只能使用 `is_first_valid_entry_for_launch_family = true` 的 entry。
- 后续同族 entry 只能进入 diagnostic / add-on audit。
- 不同 entry family 可以分别评估，但必须报告 `entry_rank_within_launch` 和 `entry_rank_within_launch_family`。
- 同一 launch episode 的多 trigger 贡献必须在 top1/top5 instrument 和 winner episode coverage 中去重。
- 如果一个 launch 同时触发多个 family，必须输出 family-level 结果和 launch-level aggregated 结果，不能只输出重复 event row。

### 6.8 Entry Trigger v1 公式矩阵

P0.6 必须输出 `entry_trigger_formula_matrix`。每个 trigger variant 至少包含：

```text
entry_family
entry_variant_id
allowed_launch_families
excluded_launch_families
signal_window_start_after_launch
signal_window_end_after_launch
entry_signal_condition
entry_signal_date_definition
entry_execution_lag_trading_days
entry_execution_price_reference
entry_execution_assumption
invalidation_rule_id
invalidation_price_reference
pre_entry_failure_filter_ids
post_entry_invalidation_audit_ids
primary_leaderboard_eligible
same_close_proxy_allowed
```

硬约束：

- 主榜 trigger 的 `entry_execution_lag_trading_days` 必须大于等于 1。
- `same_close_proxy_allowed = true` 的行只能进入 sensitivity audit。
- `allowed_launch_families` 不得包含 `primary_entry_leaderboard_eligible = false` 的 launch family，除非该 trigger 自身也标记为 secondary / add-on / hold-only。
- 每个 trigger variant 必须能从 formula matrix 复现，不能只在代码中隐式实现。

## 7. Label 与评估口径

P0.6 不再只看 future 50% high。

每个 entry event 必须至少评估：

```text
future_max_high_gain_20d_after_entry
future_max_high_gain_60d_after_entry
future_max_high_gain_120d_after_entry
future_max_high_gain_240d_after_entry
future_max_close_gain_20d_after_entry
future_max_close_gain_60d_after_entry
future_max_close_gain_120d_after_entry
future_max_close_gain_240d_after_entry
future_max_drawdown_20d_after_entry
future_max_drawdown_60d_after_entry
future_max_drawdown_120d_after_entry
future_drawdown_before_20pct_high_gain
future_drawdown_before_50pct_high_gain
future_time_to_20pct_high_gain
future_time_to_50pct_high_gain
```

Drawdown 符号必须统一：`future_max_drawdown_*` 默认使用负数表示亏损回撤，例如 `-0.12` 表示从 entry reference 到后续低点最大下跌 12%。如果实现同时输出正数 loss 口径，字段必须命名为 `future_max_drawdown_loss_*`，不得混用。

二分类 label 至少包括：

```text
entry_future_20pct_high_60d
entry_future_20pct_close_60d
entry_future_50pct_high_120d
entry_future_50pct_close_120d
entry_future_100pct_high_240d
entry_future_100pct_close_240d
entry_max_drawdown_20d_le_8pct
entry_max_drawdown_60d_le_12pct
entry_drawdown_before_20pct_gain_le_10pct
```

当 drawdown 使用负数口径时，阈值判断必须写成：

```text
entry_max_drawdown_60d_le_12pct =
  future_max_drawdown_60d_after_entry >= -0.12
```

Entry label 重算纪律：

- entry event 的所有 forward return / drawdown / time-to-gain 必须以 `entry_price_reference` 为起点重新计算。
- 默认主榜 `entry_price_reference = next_open`。
- P0 stock-day label panel 可以复用为原始 OHLC / launch label cache，但不得直接把 launch 日 forward label 用作 delayed entry label。
- manifest 必须记录 `entry_labels_rebased_to_entry_price = true` 和 `p0_stock_day_label_panel_used_for_entry_label_directly = false`。

必须新增等待成本：

```text
missed_gain_from_launch_to_entry =
  entry_price_reference / launch_close - 1

missed_gain_from_launch_to_entry_close_proxy =
  entry_close / launch_close - 1

missed_intraday_high_from_launch_to_entry =
  max(high between launch_date and entry_date) / launch_close - 1
```

主 leaderboard 只能使用 `missed_gain_from_launch_to_entry`，即基于可执行入场价 `entry_price_reference` 的等待成本。`missed_gain_from_launch_to_entry_close_proxy` 只能进入 sensitivity audit，不得用于主榜排序或 P1 eligibility。

必须新增直接追入对照：

```text
all_launch_direct_entry_outcome
trigger_convertible_direct_entry_outcome
matched_delay_entry_outcome
entry_trigger_outcome
entry_trigger_vs_all_launch_direct_delta_return
entry_trigger_vs_all_launch_direct_delta_drawdown
entry_trigger_vs_convertible_direct_delta_return
entry_trigger_vs_convertible_direct_delta_drawdown
entry_trigger_vs_matched_delay_delta_return
entry_trigger_vs_matched_delay_delta_drawdown
entry_trigger_vs_direct_missed_gain
```

Baseline 必须拆成三个分母：

1. `all_launch_direct_baseline`

   同一 launch family 下所有 launch episode 的直接追入结果。它回答：

   ```text
   如果看到这个 launch family 就直接上车，整体结果如何？
   ```

2. `trigger_convertible_launch_direct_baseline`

   只包含后来确实出现某个 entry trigger 的 launch episode 的直接追入结果。它回答：

   ```text
   对于最终等到了该 trigger 的这批 launch，
   直接追入 vs 等 trigger 后入场，哪个更好？
   ```

3. `matched_delay_baseline`

   对同一 launch family，按 entry trigger 的实际 delay 分布随机或固定等待同样天数，但不要求触发该 entry 条件。它回答：

   ```text
   trigger 变好，是因为结构条件真的有效，
   还是因为等待几天自然过滤了一部分失败 launch？
   ```

解释规则：

- `all_launch_direct_baseline` 是 discovery 主基线。
- `trigger_convertible_launch_direct_baseline` 是 paired comparison，不得单独作为 trigger 有效的证明。
- `matched_delay_baseline` 是延迟过滤审计基线；如果 trigger 只跑赢 direct，但跑不赢 matched-delay，必须标记为 `delay_filter_only_not_structural_entry_signal`。
- 如果 entry trigger 只跑赢 convertible baseline，但跑不赢 all-launch baseline，必须标记为 `survivorship_or_waiting_filter_risk`。
- 如果 entry trigger 跑赢 all-launch baseline，但 missed gain 明显过高，必须标记为 `too_late_for_entry_hold_only`。

P0.6 的目标不是单纯最大收益，而是：

```text
entry 后仍有足够 upside，
同时 entry 前等待能降低 drawdown / false positive。
```

主目标必须显式定义，默认使用：

```text
entry_success_primary =
  entry_future_20pct_high_60d
  and entry_drawdown_before_20pct_gain_le_10pct
  and missed_gain_from_launch_to_entry <= 0.15

entry_failure_primary =
  not entry_future_20pct_high_60d
  and future_max_drawdown_60d_after_entry <= -0.12
```

说明：

- `entry_success_primary` 是主 leaderboard 的默认 precision/lift 目标。
- `entry_future_50pct_high_120d` 和 `entry_future_50pct_close_120d` 是 secondary evidence。
- drawdown 与 missed gain 是 entry 问题的硬约束，不是报告附录。
- 如果配置调整主目标，必须在 manifest 中记录 `primary_entry_target_definition`。

P1 entry hypothesis 准入不能只依赖 `entry_success_primary`。进入 P1 candidate 至少还要满足以下 winner upside 条件之一：

```text
entry_future_50pct_high_120d_lift_vs_all_launch_direct > 1
entry_future_50pct_close_120d_lift_vs_all_launch_direct > 1
entry_future_100pct_high_240d_lift_vs_all_launch_direct > 1
winner_episode_coverage_after_entry >= configured_min_winner_episode_coverage
```

如果只优化 20% / 60d 成功率，但 50% / 120d 或 100% / 240d winner upside 没有正 lift，必须标记：

```text
short_swing_entry_not_big_winner_entry
```

### 7.1 Missed Winner 审计

P0.6C 必须新增 missed-winner audit，用来判断等待 trigger 是否漏掉真正 winner。

每个 launch family + entry trigger 至少报告：

```text
launch_winner_without_entry_trigger_count
launch_winner_without_entry_trigger_rate
missed_winner_due_to_no_trigger_rate
direct_entry_winner_missed_by_waiting_rate
missed_50pct_winner_episode_coverage
missed_100pct_winner_episode_coverage
winner_episode_coverage_after_entry
winner_episode_coverage_loss_vs_all_launch_direct
```

解释规则：

- 如果 `missed_winner_due_to_no_trigger_rate` 过高，trigger 只能作为保守确认或加仓条件。
- 如果 trigger 降低 false positive 但同时显著损失 winner episode coverage，不得进入主 P1 candidate。
- missed-winner audit 是 entry 研究的主审计，不是报告附录。

## 8. Ranking 规则

P0.6 不得只按 stock-day 或 event precision 排序。

P0.6 主 ranking 必须延续 P0.5 的教训：stock-day lift 只能作为 diagnostic，主判断必须同时看 dedup trigger-event 和 instrument-year。任何只在 event-level 好看、但 instrument-year 不为正的 trigger，都不能进入 P1 candidate。

每个 entry trigger 至少报告：

- launch event count。
- entry event count。
- launch-to-entry conversion rate。
- `entry_success_primary` precision。
- `entry_success_primary` lift vs all-launch direct baseline。
- `entry_success_primary` lift vs trigger-convertible direct baseline。
- `entry_success_primary` lift vs matched-delay baseline。
- `entry_lift_vs_convertible_direct`。
- instrument-year entry lift vs all-launch direct baseline。
- instrument-year entry lift vs matched-delay baseline。
- positive unique instrument-year count。
- entry success unique instrument-year rate。
- entry lift vs same launch family unconditional baseline。
- entry_future_50pct_high_120d lift vs all-launch direct baseline。
- entry_future_50pct_close_120d lift vs all-launch direct baseline。
- entry_future_100pct_high_240d lift vs all-launch direct baseline。
- median missed gain。
- missed winner due to no trigger rate。
- median future 60d / 120d high gain。
- median future drawdown before gain。
- median entry-to-stop risk pct。
- primary false positive rate。
- pre-entry failure filter hit rate。
- post-entry invalidation audit hit rate。
- distinct years。
- distinct industries。
- top1 instrument contribution。
- top5 instrument contribution。
- winner episode coverage。
- non-winner false positive drawdown。

排序建议：

1. entry event count 足够。
2. entry lift vs all-launch direct baseline 为正。
3. entry lift vs trigger-convertible direct baseline 为正。
4. entry lift vs matched-delay baseline 为正。
5. instrument-year lift vs all-launch direct baseline 为正。
6. instrument-year lift vs matched-delay baseline 为正。
7. positive unique instrument-year count 足够。
8. drawdown before gain 明显低于 direct launch entry。
9. missed gain 不过高。
10. missed winner 不过高。
11. entry-to-stop risk 不过高。
12. 50% / 120d 或 100% / 240d winner upside 保留。
13. distinct years 足够。
14. top1 instrument contribution 不过高。
15. failure filter 可解释且 T 日可观察。

默认最低门槛：

```text
min_entry_event_count = 100
min_distinct_year_count = 3
max_top1_instrument_contribution = 0.20
entry_lift_vs_all_launch_direct_min = 1.05
entry_lift_vs_convertible_direct_min = 1.02
entry_lift_vs_matched_delay_min = 1.00
instrument_year_entry_lift_vs_all_launch_direct_min = 1.00
instrument_year_entry_lift_vs_matched_delay_min = 1.00
min_positive_unique_instrument_year_count = 20
drawdown_reduction_vs_direct_min = 0.10
max_median_missed_gain = 0.15
max_median_entry_to_stop_risk_pct = 0.12
max_missed_winner_due_to_no_trigger_rate = 0.50
winner_upside_lift_vs_all_launch_direct_min = 1.00
```

默认综合排序分数：

```text
entry_quality_score =
  z(entry_success_lift_vs_all_launch_direct)
  + z(entry_success_lift_vs_matched_delay)
  + z(instrument_year_entry_lift_vs_all_launch_direct)
  + z(instrument_year_entry_lift_vs_matched_delay)
  + z(drawdown_reduction_vs_all_launch_direct)
  + z(winner_upside_lift_vs_all_launch_direct)
  - z(median_missed_gain)
  - z(missed_winner_due_to_no_trigger_rate)
  - z(median_entry_to_stop_risk_pct)
  - z(primary_false_positive_rate)
  - z(top1_instrument_contribution)
```

硬约束：

- 未通过 `min_entry_event_count`、`min_distinct_year_count` 或 `max_top1_instrument_contribution` 的 trigger 不得进入 P1 candidate。
- `instrument_year_entry_lift_vs_all_launch_direct < 1.00` 的 trigger 不得进入 P1 candidate。
- `instrument_year_entry_lift_vs_matched_delay < 1.00` 的 trigger 不得进入 P1 candidate。
- `positive_unique_instrument_year_count < min_positive_unique_instrument_year_count` 的 trigger 不得进入 P1 candidate。
- 未跑赢 matched-delay baseline 的 trigger 不得进入 P1 candidate。
- `missed_winner_due_to_no_trigger_rate` 过高的 trigger 不得进入 P1 candidate。
- `median_entry_to_stop_risk_pct > 0.12` 的 trigger 默认不得进入 P1 candidate；如果放宽到 0.15，报告必须单独说明。
- `entry_future_50pct_high_120d`、`entry_future_50pct_close_120d` 或 `entry_future_100pct_high_240d` 没有正 lift 的 trigger 不得进入 P1 candidate。
- `primary_entry_leaderboard_eligible = false` 的 launch family 只能进入 secondary / hold / add-on board。
- `same_close_proxy` 只能进入 sensitivity audit，不得进入主 leaderboard。
- 主 lift 行必须排除 `label_horizon_truncated = true` 和 `observed_reference_overlap = true`。
- 主 lift 行必须满足 `entry_labels_rebased_to_entry_price = true`。

主 leaderboard eligibility 必须显式计算：

```text
primary_entry_leaderboard_eligible =
  launch_pool in {primary_pre_20_launch_pool, primary_pre_30_launch_pool}
  and launch_pool not in {post_20_30_hold_only_pool, late_acceleration_hold_only_pool, sparse_strong_day_diagnostic_pool}
  and entry_execution_assumption == next_open
  and same_close_proxy == false
  and entry_signal_date > launch_date
  and entry_date == next_trading_day(entry_signal_date)
  and is_first_valid_entry_for_launch_family == true
  and label_horizon_truncated == false
  and observed_reference_overlap == false
  and entry_labels_rebased_to_entry_price == true
  and entry_event_count >= min_entry_event_count
  and distinct_year_count >= min_distinct_year_count
  and top1_instrument_contribution <= max_top1_instrument_contribution
  and entry_lift_vs_all_launch_direct >= entry_lift_vs_all_launch_direct_min
  and entry_lift_vs_convertible_direct >= entry_lift_vs_convertible_direct_min
  and entry_lift_vs_matched_delay_baseline > entry_lift_vs_matched_delay_min
  and instrument_year_entry_lift_vs_all_launch_direct >= instrument_year_entry_lift_vs_all_launch_direct_min
  and instrument_year_entry_lift_vs_matched_delay >= instrument_year_entry_lift_vs_matched_delay_min
  and positive_unique_instrument_year_count >= min_positive_unique_instrument_year_count
  and drawdown_reduction_vs_all_launch_direct >= drawdown_reduction_vs_direct_min
  and median_missed_gain <= max_median_missed_gain
  and missed_winner_due_to_no_trigger_rate <= max_missed_winner_due_to_no_trigger_rate
  and median_entry_to_stop_risk_pct <= max_median_entry_to_stop_risk_pct
  and winner_upside_lift_vs_all_launch_direct >= winner_upside_lift_vs_all_launch_direct_min
```

如果某个 trigger precision 高但 missed gain 太高，必须标记：

```text
too_late_for_entry_hold_only
```

## 9. 输出文件

P0.6 至少输出：

```text
Explore9/outputs/reports/p0_6_launch_event_dictionary.csv
Explore9/outputs/reports/p0_6_launch_formula_matrix.csv
Explore9/outputs/reports/p0_6_launch_pool_quality_audit.csv
Explore9/outputs/reports/p0_6_launch_pool_lifecycle_gate_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_dictionary.csv
Explore9/outputs/reports/p0_6_entry_trigger_formula_matrix.csv
Explore9/outputs/reports/p0_6_launch_event_panel.csv
Explore9/outputs/reports/p0_6_entry_event_panel.csv
Explore9/outputs/reports/p0_6_direct_launch_entry_baseline.csv
Explore9/outputs/reports/p0_6_all_launch_direct_baseline.csv
Explore9/outputs/reports/p0_6_trigger_convertible_direct_baseline.csv
Explore9/outputs/reports/p0_6_matched_delay_baseline.csv
Explore9/outputs/reports/p0_6_entry_trigger_lift.csv
Explore9/outputs/reports/p0_6_entry_trigger_vs_direct.csv
Explore9/outputs/reports/p0_6_entry_trigger_year_breakdown.csv
Explore9/outputs/reports/p0_6_entry_trigger_instrument_year_breakdown.csv
Explore9/outputs/reports/p0_6_entry_trigger_industry_breakdown.csv
Explore9/outputs/reports/p0_6_entry_execution_assumption_audit.csv
Explore9/outputs/reports/p0_6_entry_execution_feasibility_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_dedup_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_failure_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_missed_gain_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_missed_winner_audit.csv
Explore9/outputs/reports/p0_6_entry_trigger_leaderboard.csv
Explore9/outputs/reports/p0_6_entry_trigger_rejected.csv
Explore9/outputs/reports/p0_6_scope_completion_audit.csv
Explore9/outputs/reports/p0_6_run_manifest.json
Explore9/outputs/reports/explore9_p0_6_entry_trigger_report.md
```

可选缓存：

```text
Explore9/outputs/cache/p0_6_launch_event_panel.parquet
Explore9/outputs/cache/p0_6_entry_event_panel.parquet
```

## 10. 报告要求

`explore9_p0_6_entry_trigger_report.md` 必须用中文撰写，并包含：

- P0.6 与 P0.5 的目标差异。
- 为什么 P0.6 不是 hold 策略。
- 为什么 P0.6 也不是最低点 early-entry。
- P0.6A / P0.6B / P0.6C 三段式研究结果。
- launch observation event 的构成和覆盖。
- launch pool quality audit，以及哪些 pool 不允许进入主 entry leaderboard。
- lifecycle gate audit，确认 primary_pre_20 / primary_pre_30 没有混入 post-20/post-30/late-acceleration。
- launch formula matrix 和哪些 family 被排除主 entry leaderboard。
- entry signal date、entry executable date 和执行价格假设。
- entry labels 是否已按 entry price 重新计算。
- all-launch direct baseline。
- trigger-convertible direct baseline。
- matched-delay baseline。
- 不同 waiting window 的结果。
- pullback hold entry 的结果。
- higher low re-acceleration entry 的结果。
- volume confirmation entry 的结果。
- sparse strong-day follow-through entry 的结果。
- pre-entry failure filter 是否有效。
- post-entry invalidation audit 的结果。
- entry trigger 相比 direct launch entry 是否降低 drawdown。
- entry trigger 相比 matched-delay baseline 是否仍有结构性优势。
- entry trigger 在 instrument-year 口径下是否仍有正 lift。
- entry trigger 是否牺牲过多 missed gain。
- entry trigger 是否漏掉过多 missed winner。
- entry trigger 的 next-open 可执行性和 stop-distance 风险。
- entry trigger 是否保留 50% / 120d 或 100% / 240d winner upside。
- 是否存在只跑赢 convertible baseline 的幸存者偏差风险。
- 哪些 trigger 可以进入 P1。
- 哪些 trigger 只能作为观察池。
- 哪些 trigger 只适合 hold / continuation。
- 哪些方向明确淘汰。

报告结论必须给出以下判断之一：

```text
recommendation = proceed_to_p1_entry_hypothesis_refine
recommendation = continue_p0_6_entry_discovery
recommendation = entry_not_solved_but_hold_direction_valid
recommendation = stop_entry_discovery_due_to_no_stable_trigger
```

不得输出：

```text
recommendation = proceed_to_explore10_backtest
```

推荐结论口径：

- 默认优先使用 `recommendation = continue_p0_6_entry_discovery`。
- 如果没有 entry trigger 同时跑赢 all-launch direct、matched-delay baseline，并且保留 winner upside，则不得输出 `proceed_to_p1_entry_hypothesis_refine`。
- 如果 entry 仍未解决，但 hold / continuation / failure-filter 方向有效，应输出 `recommendation = entry_not_solved_but_hold_direction_valid`。

只有当主榜 trigger 同时满足以下条件，才允许输出 `proceed_to_p1_entry_hypothesis_refine`：

```text
entry_lift_vs_all_launch_direct >= 1.05
entry_lift_vs_convertible_direct >= 1.02
entry_lift_vs_matched_delay_baseline > 1.00
instrument_year_entry_lift_vs_all_launch_direct >= 1.00
instrument_year_entry_lift_vs_matched_delay >= 1.00
positive_unique_instrument_year_count >= configured_min
drawdown_reduction_vs_all_launch_direct >= 0.10
median_missed_gain <= 0.15
missed_winner_due_to_no_trigger_rate <= configured_max
median_entry_to_stop_risk_pct <= configured_max
winner_upside_lift_vs_all_launch_direct >= 1.00
```

## 11. 成功标准

P0.6 成功不要求找到最终可交易策略。

最低成功标准：

- 至少生成 `5` 类 launch event。
- 每个 launch family 都有明确公式、阈值、role 和主榜 eligibility。
- 每个 primary launch pool 都显式通过 lifecycle gate，不能混入 post-20/post-30 或 late acceleration。
- 先输出 launch pool quality audit，再输出 entry trigger leaderboard。
- 主 entry leaderboard 只允许 `primary_pre_20_launch_pool` 和 `primary_pre_30_launch_pool`。
- `post_20pct_relative_strength`、`post_30pct_relative_strength`、late acceleration 和 sparse strong-day family 不进入主 entry leaderboard。
- 至少生成 `20` 个 entry trigger variants。
- 每个 entry trigger 都有 all-launch direct baseline 和 trigger-convertible direct baseline。
- 每个 entry trigger 都有 matched-delay baseline。
- 每个 entry trigger 都有 invalidation rule。
- 每个 entry trigger 都有 entry signal date 和 executable entry date，且主榜不混入 `same_close_proxy`。
- 每个 entry trigger 的 label 都按 `entry_price_reference` 重新计算，不得直接复用 launch 日 forward label。
- 主榜 missed gain 必须使用 `entry_price_reference / launch_close - 1`，不能使用 `entry_close / launch_close - 1`。
- 每个主榜 entry trigger 都有 next-open execution feasibility audit 和 entry-to-stop risk audit。
- 主 leaderboard 使用 first valid entry per launch episode + entry family 去重。
- 主 leaderboard 必须报告 instrument-year lift，且 P1 candidate 的 instrument-year lift 不得低于 1.00。
- 每个主 lift 排除 `label_horizon_truncated = true` 和 `observed_reference_overlap = true`。
- 至少比较 3/5/10/20 日等待窗口中的 3 个。
- 至少比较 direct launch entry vs delayed/confirmed entry。
- 至少输出 false-positive / drawdown / missed-gain / missed-winner audit。
- P1 candidate 必须保留 50% / 120d 或 100% / 240d winner upside。
- 明确说明是否存在可进入 P1 的入场触发。

如果没有任何 entry trigger 达标，仍可视为有效研究结果，但必须明确：

```text
入场问题仍未解决。
当前 Explore9 的有效方向主要是启动后持有和失败过滤，
不应把 confirmation / hold 变量误写成 entry trigger。
```

## 12. 执行边界

建议新增独立命令或配置，避免覆盖 P0/P0.5 结果：

```text
uv run python Explore9/scripts/run_explore9.py profile-p0-6 --config Explore9/configs/entry_trigger_p0_6.yaml
uv run python Explore9/scripts/run_explore9.py report-p0-6 --config Explore9/configs/entry_trigger_p0_6.yaml
```

实现时不得删除或重写以下文件：

```text
Explore9/outputs/reports/explore9_broad_discovery_report.md
Explore9/outputs/reports/explore9_p0_5_expand_1_report.md
Explore9/outputs/reports/p0_5_*.csv
```

P0.6 输出必须独立命名为 `p0_6_*`。

### 12.1 Implementation Clarification

1. `primary_pre_30_launch_pool` 与 `post_20pct_relative_strength` 的关系必须显式处理。

   `post_20pct_relative_strength` family 本身不进入主 leaderboard；但 20%-30% 区间内、尚未进入 post-30 或 late acceleration 的 `primary_pre_30_launch_pool` early-confirmation 样本可以单独审计。实现必须在 `p0_6_launch_pool_lifecycle_gate_audit.csv` 中区分：

   ```text
   post_20_family_hold_only
   primary_pre_30_early_confirmation_20_30_band
   post_30_or_late_acceleration_hold_only
   ```

2. 报告结论中的 P1 gate 必须同步包含三类 baseline / 稳定性约束：

   ```text
   entry_lift_vs_convertible_direct >= entry_lift_vs_convertible_direct_min
   instrument_year_entry_lift_vs_all_launch_direct >= instrument_year_entry_lift_vs_all_launch_direct_min
   instrument_year_entry_lift_vs_matched_delay >= instrument_year_entry_lift_vs_matched_delay_min
   positive_unique_instrument_year_count >= min_positive_unique_instrument_year_count
   ```

3. Drawdown 使用负数口径时，`le_12pct` 表示最大回撤不超过 12%，必须实现为：

   ```text
   entry_max_drawdown_60d_le_12pct =
     future_max_drawdown_60d_after_entry >= -0.12
   ```

4. `matched_delay_baseline` 必须记录可复现参数和敏感性结果：

   ```text
   matched_delay_random_seed
   matched_delay_n_repeats
   matched_delay_sample_count
   matched_delay_valid_count
   matched_delay_bootstrap_sensitivity
   ```

5. Launch / entry panel 必须包含 `launch_episode_id`。

   主 leaderboard 去重单位必须是：

   ```text
   launch_episode_id + entry_family
   ```

   主榜只统计该单位下 `entry_signal_date` 最早的 first-valid-entry。
