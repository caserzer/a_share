# 需求：Risk-on / Transition 召回修复探索 V0

## 1. 背景

本实验承接 `07_topn_multichannel_repair_candidate_generator_v0`。

07 已经在 `06_rerun_02_reverse_lifecycle_on_topn_universe_v0` 冻结的 PIT Top-N/proxy denominator 上完成多通道候选生成器重跑。它证明了一个重要事实：

```text
E1_early_ema60_repair backbone 已经能提供大部分 before-first-50pct any-event recall；
但当前 repair / reclaim 事件族对 risk_on 与 transition episode 的覆盖明显不足。
```

07 的关键输入约束仍然成立：

1. 05 universe 是 `available_source_topn_candidate`，不是精确全市场 top400/100。
2. 06 冻结了 Top-N/proxy big-winner episode denominator。
3. 07 事件必须先在完整 Top-N/proxy evaluated instrument-days 上生成，再事后 link 到 target episodes。
4. 07 不是交易信号、不是模型、不是回测，只是候选事件池。

08 不能推翻这些约束。08 的任务不是把 07 full union 直接放大，而是针对 07 暴露出的结构性漏召回，先做 regime-specific recall exploration。

## 2. 07 暴露的问题

### 2.1 总体事件池与 E1 backbone

07 全量运行的核心规模：

| 指标 | 数值 |
|---|---:|
| event_generation_instrument_days | 912,851 |
| recommended canonical events | 15,161 |
| target episodes evaluated | 2,493 |

07 的 density frontier 显示：

| candidate union | canonical events | density vs full | any recall | bridge recall |
|---|---:|---:|---:|---:|
| full E1+E2+E3+E6 | 15,161 | 100.0% | 72.0% | 34.8% |
| E1 only | 6,820 | 45.0% | 71.1% | 32.6% |
| E1+E3 | 10,257 | 67.7% | 71.6% | 33.7% |
| E1+E6 | 11,714 | 77.3% | 71.8% | 33.9% |

直接含义：

1. `E1_early_ema60_repair` 是当前候选池的主召回骨架。
2. E1-only 只损失 `0.9 pct` any-event recall，却把 canonical events 降到 full union 的 `45.0%`。
3. `E2_money_vwap_repair_confirmation` 与 `E6_continuation_discriminator` 在 07 中缺少足够独立召回，更适合作为 feature / confirmation tag，而不是 headline union 扩张通道。
4. 08 不应从 full union 继续加事件，也不应把 E1-only 当作新事件的构造 backbone；更合理的设计是独立探索 risk_on / transition 的新 event family，并用 E1-only 做对照基线。

### 2.2 Regime composition 会掩盖漏召回

06 denominator 的 regime 构成：

| bucket | episodes | share |
|---|---:|---:|
| risk_off | 1,580 | 63.4% |
| transition | 485 | 19.5% |
| risk_on | 428 | 17.2% |

由于 `risk_off` 占比高，all-split recall 容易被 risk_off 表现掩盖。08 必须把 `risk_on` 和 `transition` 作为一等诊断对象，而不是只报告 all / split。

### 2.3 07 before-first-50pct any-event recall by regime

| split | regime | numerator | denominator | recall |
|---|---|---:|---:|---:|
| train | risk_off | 584 | 761 | 76.7% |
| train | risk_on | 145 | 225 | 64.4% |
| train | transition | 192 | 304 | 63.2% |
| validation | risk_off | 287 | 342 | 83.9% |
| validation | risk_on | 9 | 22 | 40.9% |
| validation | transition | 57 | 81 | 70.4% |
| robustness | risk_off | 392 | 477 | 82.2% |
| robustness | risk_on | 90 | 181 | 49.7% |
| robustness | transition | 40 | 100 | 40.0% |

解释：

1. `risk_off` recall 在三个 split 都较高，说明当前 E1 repair / reclaim path 更适合压力市场后的修复型 winner。
2. `risk_on` 在 validation 只有 `40.9%`，但 denominator 只有 22，必须标记为 sample-small diagnostic。
3. `risk_on` 在 robustness 为 `49.7%`，样本 181，更能说明结构性覆盖不足。
4. `transition` 在 validation 为 `70.4%`，但 robustness 只有 `40.0%`，说明混合市场状态下存在不稳定漏召回。

### 2.4 Missed episode by regime

| regime | missed episodes | denominator episodes | miss rate |
|---|---:|---:|---:|
| risk_off | 317 | 1,580 | 20.1% |
| risk_on | 184 | 428 | 43.0% |
| transition | 196 | 485 | 40.4% |

结论：

```text
08 的首要问题不是继续 thinning 当前 full union，
而是识别 risk_on / transition 中当前 E1 backbone 抓不到的结构性路径。
```

这些漏召回可能来自：

1. risk_on 中的浅回撤、平台延续、强势突破、相对强度扩张。
2. transition 中的市场修复早期、风格轮动、行业或 board 相对市场转强。
3. 已经处在 EMA60 之上、没有经历典型 60d new-low -> EMA60 reclaim path 的 winner。
4. first +50% 前的最佳观察点不一定是 repair anchor，而可能是 breakout / continuation anchor。

## 3. Regime 定义

08 必须沿用 02 / 03 / 06 / 07 的 market regime 定义，不得重定义或重算成新口径。

通用市场状态由 `all_a` 指数 close 计算：

```text
market_trend_60d = all_a_close / rolling_mean(all_a_close, 60) - 1
market_drawdown_120d = all_a_close / rolling_max(all_a_close, 120) - 1

risk_on:
  market_trend_60d >= 0 and market_drawdown_120d > -0.10

risk_off:
  market_trend_60d < 0 and market_drawdown_120d <= -0.10

transition:
  all other complete observations
```

如果 60d 或 120d lookback 不足，状态为 `missing_insufficient_lookback`。

08 必须区分两个 regime 字段：

1. `episode_regime_bucket`：episode low date 上的 market regime，用于 episode recall 主分层。
2. `event_regime_bucket`：event t0 date 上的 market regime，用于 event density、event precision 和候选触发诊断。

Headline recall exploration 以 `episode_regime_bucket in {risk_on, transition}` 为核心对象。事件生成可以使用 `event_regime_bucket` 作为可观测 gating feature，但必须披露其对 density 与 missed episode 的影响。

## 4. 目标

08 的目标是在 06 冻结 denominator 上，独立探索 risk_on / transition 下不同于 repair / reclaim path 的新候选事件族。

`07 E1-only` 在 08 中只作为 baseline / comparator，不作为新事件 family 的构造前提。新事件不要求存在 seed low，不要求发生 EMA60 reclaim，也不要求与 E1 同日或同 episode 相邻。

本实验必须回答：

1. 在 `risk_on` episode 中，哪些 observable event family 能捕捉不经过 EMA60 repair 的强趋势 winner？
2. 在 `transition` episode 中，哪些 observable event family 能捕捉 regime 刚切换时的早期 winner？
3. 新候选族的增量 recall 是否真实来自 missed episode，而不是与 E1 / E2 / E6 高度重叠？
4. 新候选族是否能保持低事件密度，而不是重新制造 07 full union 的 density drag？
5. 新候选族的 bridge-positive recall 与 forward label 质量是否足够支持进入下一阶段 meta-label / ranking？
6. `risk_on` 与 `transition` 是否需要不同的候选逻辑，还是可以由同一类 momentum / breakout / relative-strength event 覆盖？

08 只授权“候选族是否值得进入下一阶段”。08 不授权交易化 entry contract。

## 5. 非目标

本实验不得：

1. 不训练 primary model、meta model、ranking model 或 deep learning 模型。
2. 不做 portfolio backtest、收益曲线、仓位模拟、止损止盈或交易规则。
3. 不把单一 candidate family 解释成可交易买点。
4. 不用未来 MFE、episode high、first-50pct touch、first-100pct touch、future return 或 outcome 构造事件。
5. 不移动 06 / 07 的 train、validation、robustness split 边界。
6. 不在 validation / robustness 上调参。
7. 不只在 target episode window 内搜索事件。
8. 不只输出 captured target 的事件，必须保留 non-target、failed、bridge-negative 事件。
9. 不因为本实验聚焦 risk_on / transition，就从 audit 或 density denominator 中删除 risk_off instrument-days。
10. 不直接把 07 full union 作为 08 默认 headline union。
11. 不把 E2 / E6 继续作为 headline union 扩张起点；它们默认应降级为 feature / confirmation tag，除非 train-only evidence 证明其有独立增量召回。
12. 不要求新事件 family 从 E0 seed low、E1 EMA60 reclaim、E2 quality burst 或 E6 continuation 继承。

## 6. 上游输入

08 必须读取并记录以下 artifact：

1. `06_rerun_02_reverse_lifecycle_on_topn_universe_v0`
   - run manifest
   - frozen Top-N/proxy episode reference
   - denominator summary
   - split / regime / board denominator diagnostics
2. `07_topn_multichannel_repair_candidate_generator_v0`
   - run manifest
   - `topn_multichannel_candidate_event_instances.csv`
   - `topn_multichannel_candidate_event_canonical.csv`
   - `topn_any_event_recall_by_split_regime_board.csv`
   - `topn_bridge_positive_recall_by_split_regime_board.csv`
   - `topn_channel_recall_contribution.csv`
   - `topn_channel_overlap_matrix.csv`
   - `topn_event_precision_label_readout.csv`
   - `topn_false_repair_diagnostic.csv`
   - `topn_episode_capture_audit.csv` or equivalent local cache if publishable table is too large
3. 05 universe manifest 与 coverage audit，用于传播 `available_source_topn_candidate` caveat。
4. 01 日频 PIT 数据、benchmark daily、board / market regime features。

如果 06 decision 不是可接受的 frozen denominator 状态，08 必须停止并输出：

```text
decision = risk_on_transition_recall_exploration_input_blocked
```

如果 07 decision、manifest 或 canonical event outputs 不可读，08 必须停止；不得用报告中的汇总数字伪造逐事件输入。

### 6.1 Industry / style / breadth 输入契约

由于 08 的新 family 包含 industry breadth、stock-vs-industry、industry-vs-market、style rotation 和 volume regime shift，必须显式审计这些输入是否可用。

实现必须输出 `industry_style_input_contract_audit.csv`，至少包含：

1. `feature_domain`
2. `source_path`
3. `source_manifest_hash`
4. `pit_available_flag`
5. `effective_date_policy`
6. `min_constituents`
7. `coverage_rate`
8. `fallback_policy`
9. `blocked_family_list`
10. `notes`

Industry 输入要求：

1. 行业分类必须是 PIT 或可证明不会使用未来修订信息。
2. 至少需要 `instrument`、`effective_date` 或 `trade_date`、`industry_id`、`industry_name`、`source`。
3. 行业 breadth 和 industry return 只能使用 t0 当天可见的 Top-N/proxy evaluated instruments。
4. 如果某行业当天有效成分数低于预声明 `min_constituents`，相关 industry feature 必须标记为 missing，不得用未来补齐。
5. 当前 08 默认假设行业分类数据明确缺失，除非 input audit 证明存在 PIT 行业分类。
6. 如果行业分类不可用，`R4_industry_breadth_expansion`、`T1_stock_vs_industry_CUSUM_break`、`T2_industry_vs_market_CUSUM_break` 必须降级为 `family_data_blocked`。
7. 可运行替代 family 必须使用新的 family_id 单独声明，不得静默替换语义或继续冒充 industry family。
8. board-level fallback 必须单独命名为 fallback variant，不得继续冒充 industry family。

Style 输入要求：

1. style proxy 的定义必须写入 config，不得在代码中临时拼接。
2. 可接受 style proxy 包括但不限于 `growth`、`small`、`ChiNext`、`high_beta`、`main_board`、`large_cap`。
3. 每个 style proxy 必须声明 membership、return calculation、rebalance policy、lag policy 和 missing policy。
4. `R5_growth_or_small_style_confirmation` 与 `T3_style_rotation_break` 必须证明不是简单复刻 `event_regime_bucket = risk_on`。
5. 如果 style proxy 不能 PIT 构造，相关 family 必须降级为 `family_data_blocked` 或 `diagnostic_only`。

Breadth 输入要求：

1. breadth 只能基于当日可见收盘后数据构造，并默认在 next-open 才可执行。
2. 必须同时输出 raw breadth、breadth change、breadth z-score 或 percentile。
3. breadth 的 universe scope 必须明确，是 industry、board、style proxy 还是全 Top-N/proxy evaluated universe。
4. breadth 缺失不得用未来日期前填。

## 7. Baseline

08 的主 baseline / comparator 是：

```text
07 E1-only canonical event set
```

而不是：

```text
07 full E1+E2+E3+E6 union
```

原因：

1. E1-only 已覆盖 `71.1%` before-first-50pct any-event recall。
2. E1-only canonical events 只有 full union 的 `45.0%`。
3. E2 / E6 在 07 中主要是 confirmation / continuation tag，不提供足够独立召回。

08 必须重放并输出 E1-only baseline 的以下指标：

1. all / train / validation / robustness before-first-50pct any-event recall。
2. `risk_on` / `transition` / `risk_off` 分层 recall。
3. `risk_on` / `transition` missed episode 列表。
4. E1-only bridge-positive recall。
5. E1-only event density。
6. E1-only event label completeness。
7. E1-only first-event lead-time distribution。

E1-only baseline 必须由 08 重新计算，不得直接读取 07 report 中的汇总数字作为 baseline。实现必须从 07 的 canonical / instance artifacts 重建 E1-only set：

1. 优先使用 07 canonical event 中的 triggered channel membership，筛选包含 `E1_early_ema60_repair` 的 canonical events。
2. 如果 canonical 表缺少可解析 triggered membership，必须从 07 event instances 按 instrument + event_t0_date 重建 canonical channel membership。
3. 07 report 中的 `6,820` canonical events、`71.1%` any recall 和 `32.6%` bridge recall 只能作为 reconciliation reference，不能作为计算输入。
4. 必须输出 `e1_only_baseline_recompute_audit.csv`，列出 recomputed value、07 reported value、difference、reconciliation_status。

Full union 只能作为 diagnostic comparator，不得作为默认下一步候选池。

08 的探索分为两层：

1. Discovery layer：独立生成 risk_on / transition 新 event family，不依赖 E1 path。
2. Comparison layer：事后与 E1-only、07 full union 比较 incremental recall、overlap、density、bridge-positive recall 和 label quality。

## 8. 事件生成全集

08 的候选事件必须先在完整 Top-N/proxy evaluated instrument-days 上生成，然后再 link 到 target episodes。

允许使用 regime 作为可观测条件：

```text
event_regime_bucket in {risk_on, transition}
```

但这只是 event t0 上可见的条件，不得使用 episode outcome 或 target label。

每个新 family 必须至少输出两个版本：

1. `ungated`：不使用 `event_regime_bucket` 做触发过滤。
2. `event_regime_gated`：只允许在 `event_regime_bucket in {risk_on, transition}` 时触发。

如果某 family 因语义原因只能有 gated 版本，必须在 config 和 report 中说明，并输出 gating drop audit。Headline exploration 以 `episode_regime_bucket` 为主，不能因为 event_t0 已经切到其他 regime 就静默过滤掉目标 episode 内的候选事件。

必须满足：

1. 覆盖 06 / 07 一致的 evaluated instrument-days。
2. 事件生成不依赖 target episode window。
3. 事件可以在 target episode 内、target episode 外、non-target symbol 上出现。
4. event density denominator 必须使用被候选族实际允许触发的 PIT instrument-days，并同时报告全 denominator density。
5. 所有 candidate family 都必须保留 event instance 和 canonical event 两层输出。
6. 同一股票同一交易日多 family 触发时，必须构造 canonical union，并保留 triggered family list。

禁止：

1. 只对 missed episode 反向搜索最优 event。
2. 只对 risk_on / transition target symbols 生成事件。
3. 根据未来 first +50% 日期选择 event。
4. 根据 future MFE / future return 调整 event_t0。

### 8.1 统一比较口径

08 必须统一以下 denominator / gate 口径，避免 E1-only、新 family、ungated 和 gated 版本不可比。

Recall 口径：

1. 所有 before-first-50pct any-event recall 都以相同的 06 target episode denominator 为准。
2. regime recall 的 denominator 是同一 `episode_split + episode_regime_bucket + capture_window` 下的 episode count。
3. `incremental recall over E1-only` 的公式为：

```text
(candidate_union_captured_episodes - E1_only_captured_episodes)
/ same_split_same_episode_regime_same_window_denominator
```

4. `+8 pct`、`+12 pct` 等门槛单位均为 percentage points，不是相对提升百分比。
5. 对 E1 已捕捉 episode 的 earlier / better-basis 改善，必须单独报告，不得混入 unique missed episode recall。

Density 口径：

1. Headline density gate 默认使用 06 / 07 全 evaluated instrument-days 或 universe-years 作为 denominator。
2. `event_regime_gated` 版本必须同时报告：
   - `density_full_denominator`：以全 evaluated instrument-days / universe-years 为 denominator。
   - `density_eligible_gated_denominator`：以 event_regime gate 允许触发的 instrument-days / universe-years 为 denominator。
   - `density_vs_e1_full_denominator`：相对 E1-only 全 denominator 密度。
   - `density_vs_same_gated_denominator`：相对同 gating scope 的密度。
3. Headline gate 优先使用 `density_full_denominator`，不得因为 gating 缩小 eligible universe 而低估 density drag。
4. 所有 candidate union 必须同时对照：
   - 08 recomputed E1-only density。
   - 07 full union density。
   - 本 family ungated density。
   - 本 family event-regime-gated density。

Bridge-positive 口径：

1. Bridge-positive recall 必须输出 exclusion 前后的 denominator。
2. 每个 split / regime / family / union 至少输出：
   - `bridge_denominator_before_exclusion`
   - `bridge_excluded_count`
   - `bridge_excluded_rate`
   - `bridge_denominator_after_exclusion`
   - `bridge_positive_captured`
   - `bridge_positive_recall`
   - `bridge_exclusion_reason`
3. 如果某 family 的 bridge exclusion rate 明显高于 E1-only 同 split / regime baseline，则该 family 的 bridge-positive 结论只能标记为 `diagnostic_only`，不得用于推荐进入下一阶段。
4. Bridge exclusion audit 必须区分 forward-120 incomplete、缺少 next-open basis、缺少价格路径和其他 input completeness 问题。

## 9. 候选探索方向

08 至少需要探索以下方向。每个方向可以包含多个 train-only threshold variant，但必须在 config 中预声明候选网格。

每个 candidate family 必须有可复现的 formula spec，并写入 config 或单独的 publishable spec table。至少包含：

1. `family_id`
2. `variant_id`
3. `input_series`
4. `transform`
5. `lookback_window`
6. `threshold_grid`
7. `direction`
8. `confirmation_window`
9. `cooldown_or_density_window`
10. `missing_policy`
11. `event_regime_gating`
12. `event_t0_confirmation_time`
13. `fallback_policy`
14. `family_input_status`

任何没有 formula spec 的 family 只能进入 `diagnostic_only`，不得进入推荐 candidate union。

`family_input_status` 必须取以下之一：

```text
runnable_existing_data
family_data_blocked
diagnostic_only
fallback_variant
```

依赖行业归属的 family 默认标记为 `family_data_blocked`，除非 `industry_style_input_contract_audit.csv` 证明 PIT 行业分类可用。

08 必须额外输出 `candidate_family_run_capability_summary.csv`，把声明状态与实际执行闭合。字段至少包括：

1. `family_id`
2. `family_input_status`
3. `data_dependency`
4. `is_fallback_of`
5. `executed_flag`
6. `blocked_reason`
7. `variant_count`
8. `selected_variant_id`
9. `notes`

所有 family，包括 `R6` / `R7` / `R8` / `T8` 这类只依赖行情或横截面的 family，都必须出现在该表中。Report 必须给出 family 总数、可运行数量、blocked 数量、fallback 数量和 diagnostic-only 数量。

### 9.1 Risk-on path

目的：覆盖没有经历深回撤修复、但在顺风市场中通过强势延续进入 +50% 路径的 winner。

08 必须至少把以下 risk_on 新候选 family 纳入 formula spec / input audit：

```text
R1_relative_strength_breakout
R2_near_high_volume_expansion
R3_vcp_breakout
R4_industry_breadth_expansion
R5_growth_or_small_style_confirmation
R6_market_breadth_thrust
R7_cross_sectional_momentum_rank_jump
R8_persistent_distance_above_ema
```

这些 family 的共同目标：

1. 提高 risk_on winner recall。
2. 捕捉不经过 EMA60 repair 的强趋势 winner。
3. 识别浅回撤、平台整理、相对强度扩张和高位突破路径。
4. 避免把已经接近 first +50% 的过晚事件误当成早期候选。

每个 family 的建议语义如下。

`R1_relative_strength_breakout`：

1. 股票相对市场强度已经扩张或刚突破。
2. 可使用 `stock_vs_market_10d`、`stock_vs_market_20d`、rank percentile improvement。
3. 重点检查是否能捕捉 E1 missed 的 risk_on episode。

`R2_near_high_volume_expansion`：

1. close 接近 60d / 120d high 或 recent range upper band。
2. 成交额、换手率或 money flow 相对 20d / 60d 均值扩张。
3. 必须控制高位追涨导致的 basis 过高问题。

`R3_vcp_breakout`：

1. volatility contraction / range compression 之后出现方向性突破。
2. 可使用 ATR pct、rolling range width、higher-low count、close position in range。
3. 目标是捕捉 risk_on 中的 high-base breakout，而不是深回撤修复。

`R4_industry_breadth_expansion`：

1. 个股所在行业或 proxy group 的上涨广度扩张。
2. 可使用行业内上涨比例、创新高比例、行业等权 return、行业相对 all_a / benchmark return。
3. 当前默认 `family_input_status = family_data_blocked`，除非 `industry_style_input_contract_audit.csv` 证明 PIT 行业分类可用。
4. 不得用 market breadth 或 board breadth 冒充 industry breadth；可运行替代必须使用 `R6_market_breadth_thrust` 或明确命名的 board fallback variant。

`R5_growth_or_small_style_confirmation`：

1. growth / small style proxy 开始确认风险偏好扩张。
2. 可使用 ChiNext vs main board、small-cap proxy vs large-cap proxy、high-beta basket vs market。
3. 该 family 必须证明不是简单复刻 `event_regime_bucket = risk_on`。
4. 如果使用 `ChiNext vs main_board`，必须与 `T7_board_relative_strength_break` 做专门 overlap + independent contribution 对照；否则该 ChiNext proxy variant 只能进入 `diagnostic_only`。

`R6_market_breadth_thrust`：

1. 这是在无行业数据下对 R4 breadth 语义的现有数据替代，不依赖行业归属。
2. 输入是全 Top-N/proxy evaluated universe 每日横截面。
3. 可构造当日上涨家数占比、创 N 日新高占比、等权 universe return 的 z-score / percentile。
4. 触发条件是 breadth 从低位快速扩张，即 market breadth thrust，且个股本身处于强势侧。
5. 价值是捕捉 risk_on 启动期的广度点火。
6. 横截面分母随 PIT universe membership 逐日变化，feature snapshot 必须记录每日有效成分数、缺失数和有效 coverage。
7. 默认 `family_input_status = runnable_existing_data`。

`R7_cross_sectional_momentum_rank_jump`：

1. 输入是全 universe 每日 return / 多窗口动量。
2. 构造个股在 20d / 60d 动量上的横截面 percentile，以及 short-window rank 跃升幅度。
3. 典型触发是 rank 从中游快速进入头部，例如从 `<50%` 跃入 `>80%`，具体阈值必须在 config grid 中声明。
4. R1 是 stock vs all_a 的相对市场强度；R7 是相对同侪截面的 leadership jump，二者必须分别报告 overlap。
5. 横截面分母随 PIT universe membership 逐日变化，feature snapshot 必须记录每日有效成分数、缺失数和有效 coverage。
6. 默认 `family_input_status = runnable_existing_data`。

`R8_persistent_distance_above_ema`：

1. 输入是个股 close、EMA20、EMA60、ATR。
2. 构造 close 持续位于 EMA 之上，且 `(close - EMA) / ATR` 在正区间维持 K 日，无深回撤。
3. 该 family 明确针对已经在 EMA60 之上、没有经历 `60d new-low -> EMA60 reclaim` 的 winner。
4. R8 不要求 seed low，不要求 reclaim，不要求先跌破 EMA60。
5. 默认 `family_input_status = runnable_existing_data`。

Risk-on path 禁止：

```text
不要求 seed low
不要求 EMA60 reclaim
不要求先跌破 EMA60
不使用 future MFE / first +50% / episode high
```

### 9.2 Transition path

目的：捕捉 regime 刚切换时的早期 winner，尤其是市场状态尚未完全 risk_on、但个股或行业已经率先转强的路径。

08 必须至少把以下 transition 新候选 family 纳入 formula spec / input audit：

```text
T1_stock_vs_industry_CUSUM_break
T2_industry_vs_market_CUSUM_break
T3_style_rotation_break
T4_entropy_compression_then_directional_expansion
T5_volume_regime_shift
T6_stock_vs_market_CUSUM_break
T7_board_relative_strength_break
T8_volatility_regime_contraction_break
```

这些 family 的共同目标：

1. 捕捉 regime 刚切换时的早期 winner。
2. 识别市场仍处 transition 时，个股、行业或风格已经先于市场确认的路径。
3. 避免只复刻 risk_on momentum；transition path 必须强调“状态切换”和“相对关系断裂”。

每个 family 的建议语义如下。

`T1_stock_vs_industry_CUSUM_break`：

1. 个股相对自身行业的超额收益序列出现 CUSUM break。
2. 目标是发现行业内部率先转强的 leader。
3. 当前默认 `family_input_status = family_data_blocked`，除非 PIT 行业分类可用。
4. 不得静默退化为 stock vs market；stock-vs-market 替代必须使用 `T6_stock_vs_market_CUSUM_break`。
5. CUSUM 必须声明 input return、drift、threshold、lookback、reset rule 和 one-sided / two-sided 方向。

`T2_industry_vs_market_CUSUM_break`：

1. 行业相对 all_a 或 board benchmark 出现 CUSUM break。
2. 目标是发现 transition 中的行业级 early leadership。
3. 个股事件可以要求股票不弱于行业，避免只买行业内弱股。
4. 当前默认 `family_input_status = family_data_blocked`，除非 PIT 行业分类可用。
5. 不得静默退化为 board vs market；board 替代必须使用 `T7_board_relative_strength_break`。
6. CUSUM spec 必须与 T1 同样可审计，并报告行业成分覆盖率。

`T3_style_rotation_break`：

1. style proxy 相对市场出现方向性切换。
2. style proxy 可以包括 growth / small / ChiNext / high beta 等可审计组合。
3. 必须记录 style proxy 的构造方法和 PIT 可用性。
4. 必须输出 style proxy return、relative return、break statistic 和 selected threshold。
5. 如果使用 `ChiNext vs main_board`，必须与 `T7_board_relative_strength_break` 做专门 overlap + independent contribution 对照；否则该 ChiNext proxy variant 只能进入 `diagnostic_only`。

`T4_entropy_compression_then_directional_expansion`：

1. 先出现横截面或个股路径的波动 / 方向 entropy compression。
2. 随后出现方向性扩张，且方向与个股或行业相对强度一致。
3. 该 family 主要用于捕捉盘整后的 regime transition breakout。
4. 必须定义 entropy 输入、bucket 方法、compression lookback、expansion confirmation 和方向一致性规则。

`T5_volume_regime_shift`：

1. 成交额、换手率或量能分布出现 regime shift。
2. 量能切换必须与价格或相对强度方向一致。
3. 单纯放量不够，必须防止把下跌放量或事件噪声计入正向候选。
4. 必须定义 volume baseline、shift statistic、confirmation window 和负向放量排除规则。

`T6_stock_vs_market_CUSUM_break`：

1. 这是 T1 在无行业数据下的 market-level fallback，但必须使用独立 family_id，不冒充 industry family。
2. 输入是个股相对 all_a 的超额收益序列。
3. 构造与 T1 相同的 CUSUM 机制，包括 drift、threshold、reset、one-sided / two-sided 方向。
4. 价值是捕捉 transition 早期 leader 的相对强度结构性断裂。
5. 必须纳入 relative-strength cluster overlap audit，因为 R1 是阈值 / 突破式相对强度，T6 是累积漂移检测，R7 是横截面同侪 leadership jump。
6. 默认 `family_input_status = runnable_existing_data`。

`T7_board_relative_strength_break`：

1. 这是 T2 在现有数据下的 board-level fallback，但必须使用独立 family_id，不冒充 industry family。
2. 输入可以是 ChiNext universe 等权 return vs main-board 等权 return，或 `chinext_index` vs `csi300` / `all_a`。
3. 构造 board 级相对收益的 CUSUM / 方向性切换。
4. 个股事件要求所在 board 正在转强，且个股不弱于本 board。
5. board 来源必须来自 05 / 06 universe 已审计字段或 benchmark alias，不得临时手工分类。
6. 如果 R5 / T3 使用 `ChiNext vs main_board` 作为 style proxy，T7 必须与这些 style variants 做专门 overlap + independent contribution 对照，避免同一 board-relative signal 被重复计数。
7. 默认 `family_input_status = runnable_existing_data`。

`T8_volatility_regime_contraction_break`：

1. 输入是个股 realized volatility、ATR pct 或 rolling range volatility。
2. 构造波动率从高 regime 切换到低 regime，即收缩稳定，随后出现方向性放量突破。
3. T4 是 entropy compression，T8 是 volatility-level regime shift；二者必须作为机制不同的 robustness 对照分别报告。
4. 必须定义 volatility baseline、high-to-low regime state、break confirmation、direction rule 和 volume confirmation。
5. 必须与 `R3_vcp_breakout` 报告 overlap，并说明二者的 regime 归属差异：R3 偏 risk_on high-base，T8 偏 transition volatility regime shift。
6. 默认 `family_input_status = runnable_existing_data`。

### 9.3 机制簇与高风险重叠

08 必须维护 `candidate_family_mechanism_cluster`，用于防止同质信号重复计数。

至少包含以下机制簇：

1. `relative_strength_cluster`：
   - `R1_relative_strength_breakout`
   - `R7_cross_sectional_momentum_rank_jump`
   - `T6_stock_vs_market_CUSUM_break`
2. `breadth_cluster`：
   - `R4_industry_breadth_expansion`
   - `R6_market_breadth_thrust`
3. `board_style_cluster`：
   - `R5_growth_or_small_style_confirmation` 中使用 `ChiNext vs main_board` 的 variant
   - `T3_style_rotation_break` 中使用 `ChiNext vs main_board` 的 variant
   - `T7_board_relative_strength_break`
4. `compression_break_cluster`：
   - `R3_vcp_breakout`
   - `T4_entropy_compression_then_directional_expansion`
   - `T8_volatility_regime_contraction_break`

必须输出 cluster-level overlap 和 cluster ablation：

1. 每个 family 对 E1-only 的 incremental recall。
2. 每个 cluster 对 E1-only 的 incremental recall。
3. 推荐 union 去掉任一 cluster 后的 incremental recall。
4. 如果推荐 union 的 incremental recall 主要来自单一 cluster，必须标记为 `homogeneous_signal_caveat`。

### 9.4 E1-adjacent feature tags

08 应保留 E2 / E6 的信息，但默认不把它们作为 headline union 增量通道。

必须至少把以下内容作为 feature / tag 输出：

1. E2 money / VWAP quality flags。
2. E3 rank persistence flags。
3. E6 continuation discriminator flags。
4. false-repair diagnostic labels。
5. event basis quality：
   - close_to_ema60
   - close_to_derived_daily_vwap
   - close_position_in_range
   - amount_ratio_20d
   - stock_vs_market_20d

如果 E2 / E6 被重新纳入某个 candidate union，必须报告：

1. 独立 captured episodes。
2. incremental recall over E1-only。
3. density increase over E1-only。
4. overlap with E1。
5. 是否仍然只是同日 tag。

## 10. Threshold 与调参纪律

08 可以探索多个 candidate family variant，但必须遵守：

1. 候选阈值网格必须在 config 中预声明。
2. variant selection 只能基于 train。
3. validation / robustness 只能只读评估。
4. 如果 validation 或 robustness 表现差，不得回调阈值。
5. `validation risk_on` denominator 只有 22，应自动标记为 sample-small diagnostic；不得作为单独 hard pass/fail。
6. risk_on / transition 的最终结论必须同时报告 train、validation、robustness，不得只展示最优 split。

推荐的 train selection 排序：

1. risk_on / transition incremental recall over E1-only。
2. unique missed episode capture count。
3. earlier first-event capture than E1 on already captured episodes。
4. better-basis first-event capture than E1 on already captured episodes。
5. event density increase。
6. bridge-positive recall。
7. lead time before first +50%。
8. feature completeness / execution completeness。

## 11. Evaluation windows

必须至少评估以下 episode-anchored windows：

1. `low_plus_20`
2. `low_plus_30`
3. `low_plus_60`
4. `low_plus_120`
5. `before_first_50pct`
6. `before_episode_high`

主指标是：

```text
before_first_50pct any-event recall
```

辅助指标是：

```text
bridge-positive recall
```

Bridge-positive 的定义沿用 07：

```text
event 从 next-open basis 往后 120 日 MFE >= +50%
且 forward-120 label complete
```

如果某 episode 的 bridge window 内所有 event 都 forward-120 label incomplete，则必须从 bridge-positive denominator 中排除，并记录 exclusion reason。

## 12. 必须输出的诊断指标

### 12.1 Recall

每个 candidate family、candidate union、split、episode regime 至少输出：

1. denominator episodes
2. captured episodes
3. recall
4. incremental captures over E1-only
5. incremental recall over E1-only
6. unique captures not captured by E1 / E2 / E3 / E6
7. earlier first-event captures vs E1
8. better-basis first-event captures vs E1
9. missed episodes remaining
10. capture window

### 12.2 Density

必须输出：

1. event instances per instrument-year
2. canonical events per instrument-year
3. mean / p50 / p95 events per instrument-year
4. density by split
5. density by event_regime_bucket
6. density by board
7. density increase over E1-only
8. triggered family share
9. same-day merge rate
10. `density_full_denominator`
11. `density_eligible_gated_denominator`
12. `density_vs_e1_full_denominator`
13. `density_vs_same_gated_denominator`

### 12.3 Bridge / label

必须输出：

1. bridge-positive recall by split / regime
2. event label completeness rate
3. forward MFE distribution for candidate events
4. forward MAE distribution
5. false-repair 10d / 20d rate
6. bridge-negative but any-captured event count
7. first event basis diagnostics

`better-basis first event` 必须在 config 中预声明比较口径，至少包含以下字段中的一项或多项：

1. event close 相对 episode low 的涨幅更低。
2. event close 相对 60d high / 120d high 的位置更低。
3. event close-to-EMA60 或 close-to-VWAP 更低且仍满足趋势确认。
4. forward-120 label complete 时，same-episode first event 的 MFE / MAE profile 不劣于 E1。

不得用事后 episode high 或 first +50% 位置定义 better-basis。

### 12.4 Lead time

必须输出：

1. event_t0 to first_50pct_touch sessions
2. event_t0 to episode_high sessions
3. event_t0 from episode_low sessions
4. event_t0 lead / lag versus E1 first event when both exist
5. median / p25 / p75 by family and regime

### 12.5 Overlap

必须输出：

1. overlap matrix vs E1 / E2 / E3 / E6。
2. overlap matrix among new candidate families。
3. same-day overlap。
4. same-episode different-day overlap。
5. incremental capture waterfall。
6. mechanism cluster overlap。
7. mechanism cluster ablation。
8. high-risk overlap pairs:
   - `R1` / `R7` / `T6`
   - `R5` ChiNext variant / `T3` ChiNext variant / `T7`
   - `R3` / `T4` / `T8`

## 13. 推荐进入下一阶段的门槛

08 是探索实验，不要求直接达到 entry contract 标准。但如果某候选族要被推荐进入 09 meta-label / ranking，必须满足以下门槛。

### 13.1 Input gate

必须全部满足：

1. 06 frozen denominator 可读。
2. 07 E1-only baseline 可由 08 从 07 canonical / instances 重新计算。
3. event generation universe 与 06 / 07 evaluated instrument-days 一致，或差异可审计且不会改变结论。
4. 无 future leakage。
5. next-open execution audit 可计算。

### 13.2 Recall gate

候选族或候选 union 至少满足其一：

1. `risk_on` robustness before-first-50pct incremental recall over E1-only >= `+8 pct`。
2. `transition` robustness before-first-50pct incremental recall over E1-only >= `+8 pct`。
3. train + robustness 合并后，对 `risk_on` 或 `transition` 的 missed episode capture count >= `30`，且 density increase 可接受。
4. 对 E1 已捕捉的 `risk_on` 或 `transition` episode，新增 family 的 first event 比 E1 更早至少 `10` 个交易日的 episode count >= `30`，且 bridge-positive recall 不劣于 E1。
5. 对 E1 已捕捉的 `risk_on` 或 `transition` episode，新增 family 的 first event basis 明显优于 E1，并且 forward label quality 不劣于 E1。

Validation `risk_on` 因样本数小，不作为 hard gate，但必须报告。

上述 `+8 pct` 和 `+12 pct` 必须按 8.1 的 same split / same episode_regime / same window denominator 计算，且单位为 percentage points。

如果推荐 union 的 incremental recall 主要来自单一 mechanism cluster，必须额外报告去掉该 cluster 后的 incremental recall。如果去掉该 cluster 后 incremental recall 近似归零，最终 decision 不能直接给 `candidate_supported_for_meta_label`，必须降级为 `diagnostic_only` 或附带 `homogeneous_signal_caveat`。

### 13.3 Density gate

推荐候选 union 必须满足：

1. canonical event count 按 full evaluated denominator 计算时，不得超过 08 recomputed E1-only 的 `1.50x`，除非 incremental recall 明显超过 `+12 pct`。
2. 必须同时通过 config 中预声明的绝对 density 上限：
   - `max_candidate_union_canonical_events_per_instrument_year_mean`
   - `max_candidate_union_canonical_events_per_instrument_year_p95`
   - `max_candidate_family_canonical_events_per_instrument_year_mean`
   - `max_candidate_family_canonical_events_per_instrument_year_p95`
3. 绝对 density 上限必须在 config 中声明；默认建议继承 07 的 recommended union density gate，但实现不得硬编码 report 数字。
4. new family 单独 canonical density share 不得超过 recommended union 的 `35%`。
5. 若某 family incremental recall < `+2 pct` 且 density share > `20%`，必须标记为 density drag。
6. 必须报告 full denominator density，不得只报告 risk_on / transition 子集 density。
7. 对 event-regime-gated 版本，headline density gate 使用 `density_full_denominator`；`density_eligible_gated_denominator` 只能作为 diagnostic。

### 13.4 Bridge / label gate

候选族进入下一阶段前必须满足：

1. event precision label complete rate >= `70%`。
2. next-open executable rate >= `95%`。
3. bridge-positive recall 不得明显低于 E1-only 同 regime baseline。
4. bridge exclusion rate 不得明显高于 E1-only 同 split / regime baseline；否则 bridge-positive 结论只能 `diagnostic_only`。
5. false-repair 10d / 20d rate 必须可审计；高 false-repair 不自动失败，但必须进入 feature / rejector 设计建议。

### 13.5 Stability gate

候选族不得只在 train 有效。

如果 train 表现好，但 validation / robustness 任一 split 出现以下情况，必须降级：

1. recall 增量为负。
2. density 明显放大。
3. label completeness 不足。
4. 事件主要集中在少数年份、少数股票或单一 board。
5. 推荐 union 的增量召回主要来自单一 mechanism cluster，且 cluster ablation 后不再有实质增量。

## 14. 决策状态

08 最终 decision 必须是以下之一：

```text
risk_on_transition_recall_exploration_input_blocked
risk_on_transition_recall_exploration_no_incremental_recall
risk_on_transition_recall_exploration_density_blocked
risk_on_transition_recall_exploration_sample_blocked
risk_on_transition_recall_exploration_diagnostic_only
risk_on_transition_recall_exploration_candidate_supported_for_meta_label
```

含义：

1. `input_blocked`：上游 06 / 07 artifact 不可用或不一致。
2. `no_incremental_recall`：新候选族不能补充 E1 missed episodes，也不能在 E1 已捕捉 episode 上提供更早或更好 basis 的 first event。
3. `density_blocked`：有召回增量，但事件密度不可接受。
4. `sample_blocked`：主要证据来自过小样本，不能下结论。
5. `diagnostic_only`：发现结构性模式，但不足以进入下一阶段。
6. `candidate_supported_for_meta_label`：至少一个候选族通过 graduation gate，可进入下一阶段 meta-label / ranking。

## 15. 输出 artifact

必须输出以下 publishable tables：

1. `regime_recall_baseline_07_e1_only.csv`
2. `e1_only_baseline_recompute_audit.csv`
3. `risk_on_transition_missed_episode_audit.csv`
4. `candidate_family_event_instances.csv`
5. `candidate_family_canonical_events.csv`
6. `candidate_family_recall_by_split_regime.csv`
7. `candidate_family_incremental_recall_over_e1.csv`
8. `candidate_family_bridge_positive_recall.csv`
9. `candidate_family_bridge_exclusion_audit.csv`
10. `candidate_family_density_summary.csv`
11. `candidate_family_density_denominator_comparison.csv`
12. `candidate_family_overlap_matrix.csv`
13. `candidate_family_lead_time_distribution.csv`
14. `candidate_family_label_quality_readout.csv`
15. `candidate_family_false_repair_diagnostic.csv`
16. `candidate_family_feature_snapshot_summary.csv`
17. `risk_on_transition_candidate_frontier.csv`
18. `candidate_family_run_capability_summary.csv`
19. `candidate_family_mechanism_cluster_summary.csv`
20. `candidate_family_cluster_ablation.csv`
21. `industry_style_input_contract_audit.csv`
22. `candidate_family_formula_spec.csv`
23. `event_regime_gating_comparison.csv`
24. `candidate_vs_e1_timing_basis_comparison.csv`
25. `leakage_and_execution_audit.csv`
26. `input_manifest_audit.csv`

必须输出：

```text
outputs/publishable/reports/risk_on_transition_recall_exploration_report.md
outputs/manifests/run_manifest.json
```

如果 intermediate data 太大，可以放入：

```text
outputs/local_cache/
outputs/large_raw/
```

但 manifest 必须记录路径、hash、row count、column schema。

## 16. 报告要求

报告必须用中文撰写，并至少包含：

1. 08 final decision。
2. 07 背景与为什么不从 full union 继续扩张。
3. 06 denominator 与 regime composition。
4. risk_on / transition missed episode 问题说明。
5. regime 定义与 episode_regime / event_regime 区分。
6. E1-only baseline 重放。
7. E1-only baseline 重新计算与 07 report 数字 reconciliation。
8. 新 candidate family 定义。
9. 每个 family 的 train-only threshold selection 说明。
10. before-first-50pct any-event recall by split / regime。
11. incremental recall over E1-only，并明确 denominator 与 percentage-point 口径。
12. earlier / better-basis first-event comparison versus E1。
13. bridge-positive recall 与 bridge exclusion audit。
14. density summary、absolute density anchor、full vs gated denominator density 对照和 density drag。
15. family run capability summary，包括 runnable / blocked / fallback / diagnostic-only 数量。
16. overlap matrix 和高风险重叠对照。
17. mechanism cluster summary 与 cluster ablation。
18. lead-time distribution。
19. label completeness 与 next-open execution audit。
20. false-repair diagnostic。
21. industry / style / breadth input contract audit。
22. ungated vs event-regime-gated 对照。
23. validation risk_on sample-small caveat。
24. 是否有候选族进入下一阶段 meta-label / ranking。
25. 明确说明本实验不是交易信号、不是模型、不是回测。

## 17. 实现要求

实现必须：

1. 使用 config 管理所有阈值、路径、候选 family 开关和 gate。
2. 对所有输入 artifact 做 manifest hash 审计。
3. 保持 point-in-time 特征构造。
4. 使用 next-open execution convention。
5. 保留 event instance 与 canonical event 两层输出。
6. 不覆盖 06 / 07 上游 artifact。
7. 不硬编码报告中的 denominator 数字作为通过条件。
8. 对 validation / robustness 只读评估。
9. 单元测试至少覆盖：
   - regime 定义沿用
   - E1-only baseline replay
   - E1-only baseline recomputation from 07 canonical / instances
   - no target-only event generation
   - no future feature leakage
   - incremental recall calculation
   - incremental recall percentage-point denominator convention
   - earlier / better-basis comparison versus E1
   - density drag calculation
   - absolute density anchor and gated density denominator convention
   - bridge exclusion denominator audit
   - event-regime gated vs ungated comparison
   - industry / style input blocking or fallback policy
   - fallback family must use independent family_id and must not masquerade as blocked industry family
   - candidate family run capability summary completeness
   - high-risk overlap pairs and mechanism cluster ablation
   - sample-small validation caveat

## 18. 推荐执行顺序

建议按以下顺序实现：

1. 重放 07 E1-only baseline。
2. 构造 risk_on / transition missed episode audit。
3. 生成 candidate family formula spec 与 run capability summary。
4. 只对 `runnable_existing_data` / 合法 fallback family 生成全 universe event instances。
5. 生成 canonical union 与 overlap matrix。
6. 计算 risk_on / transition incremental recall。
7. 计算 mechanism cluster overlap 和 cluster ablation。
8. 计算 density frontier。
9. 计算 bridge / label / execution / false-repair diagnostics。
10. 在 train 上选择推荐候选族。
11. 对 validation / robustness 做只读评估。
12. 输出报告和 manifest。

## 19. 预期结论形态

08 的理想输出不是“更多事件”，而是一个清晰的 frontier：

```text
在 risk_on / transition 中，
哪些少量、可观测、低密度事件能捕捉 E1 missed episodes；
哪些事件能在 E1 已捕捉 episode 上给出更早或 basis 更好的 first event；
哪些只是与 E1 同日重叠或制造 density drag；
哪些适合作为下一阶段 meta-label / ranking 的输入特征。
```

如果没有候选族通过 gate，08 仍然有价值：它应明确说明 risk_on / transition 的漏召回是否来自当前特征体系缺失、event timing 过晚、basis 过高、样本不足，或该 regime 下 winner 本身更难由 rule-based candidate generator 早期覆盖。
