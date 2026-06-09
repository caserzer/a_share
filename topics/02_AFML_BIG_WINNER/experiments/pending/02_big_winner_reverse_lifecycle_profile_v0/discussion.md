# Big Winner Reverse Lifecycle Profile Discussion

## 1. 讨论结论

本实验不从候选信号正向搜索 event。当前阶段先做反向研究：

```text
先找出所有 big winner episode
再观察 episode 前 30 天到 episode 后 30 天的完整生命周期
同时叠加市场 regime、行业 regime、个股路径、成交、波动和相对强度
最后再判断哪些可观察锚点、状态路径或序列完成条件
有资格进入下一阶段 AFML event contract
```

核心问题不是：

```text
哪个单日信号能预测 +50% / 120d?
```

而是：

```text
A 股市场中，big winner 在启动、确认、主升和衰竭过程中，
到底被哪些因素统治?
```

因此本实验更准确地应命名为：

```text
02_big_winner_reverse_lifecycle_profile_v0
```

而不是 `event_search` 或普通 `diagnostic`。

## 2. 与正向搜索的区别

过去在 `topics/01_askhare_qlib/` 下做过很多正向尝试，包括：

- dense stock-day prediction。
- Alpha158 / Alpha191 / GTJA191 类特征。
- EMA trend、breakout、pullback、high-recall seed。
- launch 后确认触发。
- failure filter。
- short-horizon factor/state transferability。

这些尝试大多没有形成可授权的 entry edge。主要问题不是完全没有局部信息，而是：

- 信号太密，靠 seed-day density 买 recall。
- breakout 太晚，很多 winner 已经涨过一大段。
- pullback / higher-low confirmation 成本高，系统性漏掉 winner。
- 高波、放量、涨停附近状态有局部 lift，但更像 lifecycle context，不是稳定首入场 trigger。
- failure filter 可以解释一部分失败，但 false reject 和 winner coverage loss 太高。
- instrument-year lift、matched-delay 对照、robustness transfer 经常不过。

所以这次不再从“候选信号是否有效”出发，而是先从 winner 本身出发，反向拆解真实 winner 生命周期。

本轮 reviewer 反馈后的关键修正是：

- 反向画像必须承认它天然使用事后信息，不能伪装成可交易信号。
- 任何 lifecycle dominance 结论都必须是 `winner vs matched controls` 的差异结论。
- 只基于 winner 单侧分布的统计只能作为 descriptive profile，不能写成规律或因果解释。
- 如果没有稳定差异，本实验必须允许输出 null result，而不是硬挤出 event anchor 或 sequence-completion event。
- 行业相关结论必须先解决 PIT 行业数据依赖；没有 PIT 行业表时不能做 primary industry claim。

## 2.1 Lifecycle State Path, not Single-Point Event

本实验必须明确区分三件事：

```text
alignment anchor != signal
signal != event
event != single-day condition
```

`first_ema60_reclaim` 这类简单锚点首先是 shared alignment axis，用来让
winners 和 matched controls 站在同一张坐标轴上比较。它不是结论，也不是
默认的 entry event。

big winner 的生命周期可能由一组可观察状态按顺序出现共同决定，而不是由某个
单日事件独立决定。因此 v0 不只观察 marginal factor dominance，还必须允许
评估少数冻结的 lifecycle state sequences。

初始状态层级：

```text
state_0_context:
  market regime, industry regime if PIT industry data is available, liquidity regime

state_1_repair:
  stops making lower lows, EMA/VWAP/range repair, drawdown repair

state_2_confirmation:
  amount expansion, upper-half close, VWAP hold, no gap fade, no destructive upper shadow

state_3_leadership:
  stock-vs-market persistence, stock-vs-industry persistence if available, rank jump persistence

state_4_continuation:
  persistence after +20%, near-winner vs true-winner continuation difference

state_5_exhaustion_or_failure:
  rank evaporation, destructive high-vol, gap fade, volume expansion without price hold
```

The state_0 ... state_5 list is a vocabulary of observable lifecycle states.
The publishable sequence tests are the smaller frozen subset `S1` ... `S6`
defined later in this document. Other state combinations remain backlog until
their definitions are frozen.

如果后续进入 AFML event contract，`t0` 可以是：

```text
sequence_completion_date:
  first close-observed date when all required states in a frozen sequence
  have become observable and all forbidden states are absent
```

也就是说，`t0` 是工程上的样本起点和 next-open executable date，不等于声称
全部 alpha 都来自这一天。

## 3. Reference Episode 定义

第一步先构建 big winner reference episode。这是整个实验的地基，后续 requirement 必须把它写成确定性算法，而不是描述性口径。

建议冻结为：

```text
universe:
  PIT large-cap main board + ChiNext universe

membership clock:
  executable PIT universe keyed by usable_trade_date

price basis:
  qfq research OHLC

primary forward horizon:
  120 trading days

winner threshold:
  forward high MFE from retrospective low >= 50%

episode window:
  [episode_low_date - 30 trading days, episode_high_date + 30 trading days]
```

初始确定性抽取伪代码：

```text
for each instrument:
  load daily qfq OHLC rows that are inside executable PIT universe

  candidate_low_date is a local-low candidate if:
    qfq_low[D] is the minimum qfq_low in [D - 20 sessions, D + 20 sessions]
    and at least 250 prior sessions exist for full-lookback profile features
    and at least 120 forward sessions exist for primary MFE evaluation

  for each candidate_low_date:
    forward_window = next 120 trading sessions after D, inclusive of D+1
    episode_high_date = earliest date of maximum qfq_high in forward_window
    mfe_120 = qfq_high[episode_high_date] / qfq_low[D] - 1
    keep candidate if mfe_120 >= 0.50
    high_at_horizon_boundary = episode_high_date is the last date in forward_window

  de-duplicate candidates:
    sort candidates by candidate_low_date
    define interval_i = [candidate_low_date_i, episode_high_date_i]
    build non-chain overlap clusters:
      start a new cluster with seed interval_i
      add candidate_j to that cluster only if interval_j directly overlaps seed interval_i
      do not expand the seed interval when adding candidate_j
      if candidate_j does not overlap the current seed interval, start a new cluster
    record multiple profile anchors per cluster:
      earliest_qualifying_low_date = earliest low date in the cluster
      earliest_qualifying_high_date = its high date
      max_mfe_low_date = low date with highest mfe_120
      max_mfe_high_date = its high date
      max_mfe_120 = highest mfe_120 in the cluster
      structural_low_date = date with the lowest qfq_low inside union of cluster intervals
      structural_low_to_cluster_high_mfe = max qfq_high after structural_low_date within cluster horizon / structural_low - 1
```

The cluster rule is intentionally non-chain. It merges candidates whose `[low, high]` intervals directly overlap the current seed interval, but it does not keep extending the cluster boundary with every newly added candidate. This prevents a long trend from becoming one super-cluster simply because many nearby 120d forward windows overlap in a chain.

This is a deliberate counting tradeoff. In an A-B-C pattern where A overlaps B,
B overlaps C, but A does not overlap C, B may be represented in both adjacent
cluster neighborhoods and C may start a new cluster. The experiment accepts
limited boundary overlap to avoid creating a single super-episode from a long
chain. The report must include a cluster-boundary overlap audit so episode
counts are interpretable.

No single low is the "true" start of a winner. The profile must keep three distinct anchors:

```text
earliest_qualifying_low:
  earliest point from which the stock can already become a +50% / 120d winner;
  useful for studying the earliest right-tail boundary, but may include pre-launch chop

max_mfe_low:
  best payoff low inside the same cluster;
  useful as a sensitivity view, but too hindsight-optimized for primary lifecycle claims

structural_low:
  lowest observed qfq low inside the cluster interval;
  useful for path-shape interpretation, but still retrospective and not tradable
```

Primary low-aligned profile uses `earliest_qualifying_low` and must state this interpretation explicitly. Structural-low and max-MFE-low views are required sensitivity outputs, not replacements.

必须记录的 reference fields：

```text
instrument
episode_id
episode_low_date
episode_high_date
qfq_low_at_low_date
qfq_high_at_high_date
mfe_120
low_to_high_sessions
low_to_high_calendar_days
low_detection_window = 20
forward_horizon_days = 120
dedup_cluster_id
cluster_policy = non_chain_direct_interval_overlap
primary_low_selection_policy = earliest_qualifying_low_for_right_tail_boundary
earliest_qualifying_low_date
earliest_qualifying_high_date
max_mfe_low_date
max_mfe_high_date
max_mfe_120
structural_low_date
structural_low_to_cluster_high_mfe
high_at_horizon_boundary
profile_start_date
profile_end_date
profile_pre_low_complete
profile_post_high_complete
lookback_60_complete
lookback_120_complete
lookback_250_complete
```

注意：

- `episode_low_date` 是事后画像锚点，不是可交易 event。
- `episode_high_date` 也是事后画像锚点，不是退出规则。
- 反向画像可以使用事后锚点，但后续转 event 时必须重新检查 as-of 可观察性。
- 对照组定义也会使用未来标签；这在 profile 阶段允许，但禁止泄漏到未来 event contract。
- MFE 主口径必须使用 qfq OHLC；unadjusted OHLC 只用于市值资格等数据层用途。
- 不应只按自然年切片，因为自然年会切碎完整主升段。
- 需要保留跨年连续 episode，避免把一个完整 winner 拆成多个不完整年度片段。
- 如果 `profile_end_date = episode_high_date + 30 trading days` 不完整，应保留 episode 但标记 `profile_post_high_complete = false`，post-high 统计只使用 complete 子样本或显式 censored 口径。
- 如果 `high_at_horizon_boundary = true`，说明 120d horizon 内的最高点可能只是窗口截断点，不一定是完整主升高点。这类 episode 的 `post_high_30d` 衰竭分析必须单独报告或排除，不能和已观察到高点后的 rank evaporation / gap fade 统计混在一起。
- Full-lookback profile features require enough history. Missing feature values must distinguish:

```text
missing_insufficient_lookback
missing_event_absent
missing_source_field
missing_unit_incompatible
```

These states must not be collapsed.

## 3.1 数据依赖和行业口径

当前 `01_data_prepare_pit_largecap_akshare_qlib_v0` 交付的是：

- PIT large-cap main board + ChiNext universe。
- 股票 qfq / raw daily OHLCV cache。
- benchmark index provider: `csi300`, `chinext_index`, `all_a`。
- 市值、上市/ST/停牌等 universe 资格审计。

它没有明确交付 PIT 行业归属表。因此本实验对行业相关分析必须采用以下 gate：

```text
industry_data_status:
  pit_available:
    industry claims can be primary diagnostics
  best_effort_non_pit:
    industry claims are diagnostic-only with explicit as-of caveat
  unavailable:
    skip industry-relative features and industry regime conclusions
```

如果要把行业 regime 作为 primary diagnostic，本实验需要前置或同时交付：

```text
PIT industry membership table:
  instrument
  industry_code
  industry_name
  source
  as_of_date
  available_time
  usable_trade_date
```

禁止事项：

- 禁止使用 current-as-of 行业标签生成历史 primary 结论。
- 禁止把非 PIT 行业宽度、行业相对强度写成正式 dominance 结论。
- 禁止在没有行业数据的情况下，让 same-industry control matching 静默降级；必须在 manifest 和报告中记录 fallback。

没有 PIT 行业表时，primary profile 仍可继续，但只使用 market regime、个股路径、成交、波动、相对 benchmark 强度和 matched controls。

## 3.2 对照组优先原则

反向画像最大的风险是 winner-only bias。为避免自欺，报告中的 dominance 结论必须满足：

```text
dominance_claim = statistic(winner) - statistic(matched_controls)
```

或者：

```text
dominance_claim = lift_or_odds_ratio(winner vs matched_controls)
```

允许输出 winner-only descriptive tables，但这些表只能用于描述样本，不能单独支持如下表述：

```text
winner 普遍具有 X
X 统治 winner
X 是 big winner 规律
```

正式报告中的每条规律都必须标记：

```text
comparison_group
control_match_quality
effect_size
split_stability
sample_count
as_of_status
```

## 4. Aligned Lifecycle Panel

对每个 winner episode 构建对齐后的日频面板：

```text
relative_day = -30 ... 0 ... high_lag ... high_lag + 30
```

其中：

```text
relative_day = 0
```

先对应 retrospective low date，仅用于画像。

Control-adjusted dominance can only be computed on shared alignment axes that
exist for both winners and controls:

```text
shared_axis_low:
  relative_day from candidate_low_date

shared_axis_ema60:
  relative_day from first_ema60_reclaim

shared_axis_anchor:
  relative_day from the same frozen observable anchor family
```

Retrospective winner-only lifecycle stages such as `reclaim_to_20pct`,
`20pct_to_high`, and `post_high_30d` do not exist for ordinary non-winner
controls. They are allowed only as descriptive winner-path summaries and must
not be written to control-adjusted dominance tables.

单一 low-date 对齐会把短主升和长主升混在一起。因此必须同时生成三种 profile view：

```text
low_aligned:
  relative_day = date - retrospective_low_date

observable_anchor_aligned:
  relative_day = date - baseline_observable_anchor_date
  baseline anchor is first_ema60_reclaim
  secondary anchor-aligned views are generated only after their anchor definitions are frozen

duration_bucketed:
  group episodes by low_to_high_duration bucket before aggregating
```

Duration buckets use trading sessions, not calendar days. 初始 duration buckets：

```text
fast:        low_to_high_sessions <= 40
medium:      41 <= low_to_high_sessions <= 80
long:        81 <= low_to_high_sessions <= 120
```

These boundaries are initial placeholders. The formal requirement must either justify them from the reference duration distribution or replace them with frozen quantile buckets computed on the train split only. Validation and robustness must not be used to tune duration bucket boundaries. A `>120` trading-session bucket is invalid under the primary 120-session MFE horizon.

报告禁止只输出全样本平均生命周期曲线。任何平均曲线必须同时给出 duration bucket 或 anchor-aligned 版本，以避免把不同生命周期长度强行混合。

每一天记录：

- 个股 OHLCV / amount / turnover。
- 个股收益、累计收益、MFE、MAE、drawdown。
- 个股均线状态、EMA reclaim、均线斜率。
- 个股到 60d / 120d / 250d high 的距离。
- 个股波动、ATR、日内振幅、上半区收盘比例。
- 个股成交额相对 20d / 60d / 120d 分位。
- 个股相对市场收益。
- 个股相对行业收益，仅在 `industry_data_status = pit_available` 或 diagnostic fallback 时记录。
- 行业相对市场收益、行业宽度、行业同步状态，仅在行业数据 gate 允许时记录。
- 市场 trend、market drawdown、market breadth、market volatility。
- 是否触发后续可观察锚点。
- 是否满足冻结的 lifecycle state / sequence 条件。

## 5. 可观察锚点

反向画像中需要同时记录事后锚点和可观察锚点。

事后锚点：

- `low_date_retrospective`
- `high_date_retrospective`

Profile-only milestones:

- `first_retrospective_low_gain_10pct`
- `first_retrospective_low_gain_20pct`
- `first_retrospective_low_gain_30pct`

这些 milestone 从 `low_date_retrospective` 起算，不能声称为 close-observed event anchor。它们只用于描述 winner 从事后低点到后续确认段的路径。

Baseline observable anchor:

- `first_ema60_reclaim`

This anchor is frozen for the initial anchor-aligned profile:

```text
ema60[D] = rolling_mean(close, 60)[D]
first_ema60_reclaim = first D after retrospective low such that:
  close[D-1] < ema60[D-1]
  and close[D] >= ema60[D]
  and ema60[D] is computed only from closes up to D close
```

If no `first_ema60_reclaim` exists before `episode_high_date`, the baseline anchor-aligned view for that episode is marked missing and must not be imputed.

Important:

```text
anchor is not feature restriction
```

`first_ema60_reclaim` is used as a stable shared alignment anchor, not as a
claim that EMA-style features are the only useful information. The lifecycle
feature bank must remain broader than the anchor set. Hidden volume-price,
VWAP, money-flow, range-position, gap/fade, turnover, and rank-persistence
expressions are valid dominance candidates as long as they are close-observed
and compared against matched controls on a shared axis.

Therefore:

- Simple anchors define when to align observations.
- The feature bank defines what information may explain the lifecycle.
- A feature may become important without becoming an event anchor.
- A sequence of states may become important even if no single state is dominant.
- An AFML `t0` may represent the completion date of an observable sequence,
  not the causal start of the winner.
- A complex feature such as VWAP deviation should first be tested as a
  lifecycle dominance candidate, not directly promoted to an event.

Candidate observable anchors, pending requirement-level definitions:

- `first_ema20_reclaim`
- `first_trailing_60d_low_repair_10pct`
- `first_trailing_60d_low_repair_20pct`
- `first_trailing_120d_low_repair_20pct`
- `first_volatility_expansion`
- `first_volume_or_amount_expansion`
- `first_upper_half_close_after_expansion`
- `first_stock_leads_industry` only if PIT industry data is available
- `first_industry_leads_market` only if PIT industry data is available
- `first_rank_jump_persistent`
- `first_near_limit_upper_close`
- `first_120d_high_breakout`
- `first_destructive_high_vol`
- `first_gap_fade`
- `first_rank_evaporation`

这些锚点现在只是 discussion-level candidates。正式 requirement 必须冻结每个锚点的可计算定义，例如：

```text
first_volume_or_amount_expansion:
  amount[D] / rolling_median(amount, 60)[D-1] >= threshold

first_trailing_60d_low_repair_20pct:
  close[D] / rolling_min(low, 60)[D-1] - 1 >= 20%

first_upper_half_close_after_expansion:
  close_position_in_daily_range[D] >= threshold
  and expansion condition is true

first_rank_jump_persistent:
  rank_delta over N sessions >= threshold
  and rank remains above threshold for M sessions

first_near_limit_upper_close:
  close is near the actual exchange daily upper-limit price for that instrument/date
  board-specific and date-specific limit rules must be used
  fixed 10% or 20% thresholds are not allowed without an audited limit-price source or rule table
```

在定义冻结之前，这些锚点不得进入可复现实验产物的 final decision。

每个锚点都要记录：

```text
anchor_date
lag_from_low
gain_from_low
lag_to_high
remaining_gain_to_high
market_regime_at_anchor
industry_regime_at_anchor
feature_snapshot_at_anchor
anchor_as_of_status
anchor_observable_basis
```

`feature_snapshot_at_anchor` must use one fixed schema across all anchors:

```text
close_to_ema20
close_to_ema60
ema20_slope_20d
ema60_slope_20d
return_5d
return_20d
return_60d
drawdown_from_60d_high
distance_to_120d_high
amount_ratio_20d
amount_ratio_60d
turnover_ratio_20d
derived_daily_vwap_available
derived_daily_vwap_price_basis
qfq_adjustment_factor_available
close_to_derived_daily_vwap
open_to_derived_daily_vwap
vwap_deviation_20d_z
vwap_reclaim_flag
intraday_range_pct
close_position_in_range
upper_shadow_pct
gap_open_pct
gap_fade_flag
atr_20_pct
market_return_20d
market_drawdown_60d
market_volatility_20d
market_regime_bucket
benchmark_alias
stock_vs_market_20d
stock_vs_industry_20d if PIT industry data is available
industry_vs_market_20d if PIT industry data is available
```

Anchor-specific custom fields may be emitted in separate diagnostic tables, but not inside the shared snapshot schema.

VWAP fields are derived from daily source data, not intraday bars:

```text
raw_daily_vwap = money / volume
qfq_daily_vwap = raw_daily_vwap * qfq_adjustment_factor
qfq_adjustment_factor = qfq_close / raw_close
```

They may be used only when the source audit confirms compatible CNY money and
share-volume units, and when raw close and qfq close are available on the same
instrument-date. Snapshot fields such as `close_to_derived_daily_vwap`,
`open_to_derived_daily_vwap`, `vwap_deviation_20d_z`, and `vwap_reclaim_flag`
must compare qfq prices to `qfq_daily_vwap`.

Raw VWAP may be retained for audit, but raw VWAP must not be compared directly
with qfq prices in dominance tables. If money or volume is missing, zero,
unit-incompatible, or the qfq adjustment factor cannot be verified,
VWAP-derived fields must be marked `missing_unit_incompatible` or
`missing_source_field` rather than filled or inferred.

这样可以回答：

- 哪些锚点最早出现?
- 哪些锚点太晚，只能做 confirmation / continuation?
- 哪些锚点覆盖大多数 winner?
- 哪些锚点只覆盖少数极端 winner?
- 哪些锚点在不同市场 regime 下完全不同?

## 6. 需要统计的主导因素

本实验重点不是单因子 alpha，而是 lifecycle dominance。

本节所有因素都必须按 `winner vs matched controls` 输出差异。可以展示 winner 单侧分布，但不能把单侧分布写成 dominance 结论。

### 6.1 Market Regime

统计：

- CSI300 trend on / off。
- ChiNext trend on / off。
- All-A trend on / off。
- 市场 drawdown 状态。
- 市场波动状态。
- 市场宽度。
- risk-on / risk-off。

market regime 定义必须 close-observed，例如：

```text
trend_on[D] uses index data up to D close
drawdown[D] uses index high/close observed up to D close
volatility[D] uses returns up to D close
```

具体 trend / drawdown / volatility 阈值在 requirement 中冻结，不能从 validation / robustness 事后调参。

需要回答：

- winner 更多发生在 market trend on，还是 market drawdown repair?
- market regime 是启动条件，还是只是放大条件?
- 市场过滤是否会系统性漏掉弱市中的结构性 winner?

### 6.2 Industry Regime

行业 regime 只在 `industry_data_status = pit_available` 时作为 primary diagnostic。若只有非 PIT 行业标签，本节只能作为 diagnostic-only caveat；若行业数据不可用，本节跳过。

统计：

- 行业相对市场强度。
- 行业自身 trend。
- 行业宽度。
- 行业内同步上涨比例。
- 行业是否先于市场转强。
- 个股是否先于行业转强。

需要回答：

- big winner 是先有行业，再有个股，还是先有个股 leader，再带动行业?
- 行业强度是 early signal，还是 continuation amplifier?
- 哪些行业的 winner 依赖行业同步，哪些行业更依赖个股独立叙事?

### 6.3 Price Structure

统计：

- prior drawdown。
- low 前 30 天的下跌路径。
- low 后 EMA reclaim。
- low 后 10d / 20d / 30d 修复幅度。
- 到 120d high 的距离。
- 均线 slope repair。
- high 前最大回撤。

需要回答：

- winner 更像深跌修复，还是高位突破?
- EMA60 reclaim 是否是最早稳定可观察结构?
- first breakout 是否普遍太晚?
- 主升前允许多大回撤?

### 6.4 Volume, Money, VWAP, Turnover

统计：

- amount ratio。
- turnover ratio。
- volume expansion。
- derived daily VWAP availability and source-unit audit。
- close-to-VWAP / open-to-VWAP distance。
- VWAP deviation z-score。
- VWAP reclaim / loss around shared anchors。
- amount expansion with price holding above VWAP。
- money expansion without upper-shadow distribution。
- 放量后是否守住价格。
- 放量是否伴随上影线。
- 放量是否伴随 gap fade。

需要回答：

- 成交额是启动因素、确认因素，还是失败风险?
- VWAP / money-flow 结构是否比 EMA / slope 更能解释 winner-control 差异?
- VWAP reclaim 是 early repair、confirmation，还是 false-repair trap?
- 放量不涨、放量长上影、gap fade 是否是 failure signal?
- money expansion 与 industry regime 是否共同决定 continuation?

This family is the main guardrail against missing deeper non-EMA information.
The experiment must not conclude that traditional trend features dominate until
VWAP / volume-price / money-flow candidates have been tested on the same
winner-control shared axes.

### 6.5 Volatility Structure

统计：

- volatility contraction。
- volatility expansion。
- high-vol upper-half close。
- destructive high vol。
- ATR regime。
- intraday amplitude。
- upper shadow。

需要回答：

- big winner 是否普遍经历 contraction to expansion?
- 高波是右尾通道，还是失败风险?
- 扩张性高波和破坏性高波如何区分?

### 6.6 Relative Strength

统计：

- stock vs industry, only if PIT industry data is available。
- stock vs market。
- industry vs market, only if PIT industry data is available。
- rank jump。
- rank persistence。
- rank evaporation。

需要回答：

- 个股是否总是先于行业和市场?
- rank jump 是否太噪声，需要 persistence 才有意义?
- rank evaporation 是否解释 post-high 或 false repair?

### 6.7 Path Tolerance

统计：

- low 到 high 的最大回撤。
- high 前最大单日回撤。
- high 前 failure-looking events。
- stop-like path events 在哪些阶段出现。

需要回答：

- 真正 winner 的路径有多不平滑?
- 传统止损和 time stop 是否可能天然不适配右尾 winner?
- 哪些失败信号是真的失败，哪些只是 winner 主升中的正常波动?

这里不模拟具体交易 policy，不评估 stop-loss / time-stop 策略，也不输出 exit recommendation。规则模拟留给后续 event / strategy 实验。

## 7. 必须加入对照组

只看 winner 会导致所有特征都看起来有意义。因此必须构造 matched controls。

对照组会使用未来结果来定义 `non-winner`、`near-winner` 或 `false-repair`。这在 profile 阶段允许，因为本实验不是 event contract；但这些未来标签禁止进入后续可交易 event 定义。

每个 control set 必须记录：

```text
match_anchor_date
match_fields
match_distance
matched_control_count
unmatched_reason
future_label_used_for_profile_only
```

如果某类 control 的 match coverage 不足，相关 dominance claim 必须降级为 sample-blocked。

对照必须来自同一 opportunity set。禁止拿 retrospective low 上的 winner 去对比普通 stock-day control。

Control candidate pools must use the same per-instrument non-chain
direct-interval deduplication policy as winner episode extraction before
matching. Otherwise one choppy non-winner instrument can contribute many nearby
`candidate_low_date` rows and inflate control coverage, average controls per
winner, and sequence-rate denominators.

If nearest same-week matching would cross a split boundary, the control match
must be dropped or explicitly marked `cross_split_boundary_unusable`. A control
row from validation or robustness must not enter train dominance statistics
through nearest-week matching.

建议四类对照：

### 7.1 Retrospective-Low Opportunity Controls

用途：

- 用于 low-aligned profile。
- 对比对象也必须满足同类 `candidate_low_date` 条件。

对每个 winner episode，在同一 `candidate_low_date` 附近找非 winner candidate-low 股票：

```text
same date
same industry if PIT industry data is available
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return
similar prior drawdown
similar volatility bucket
same candidate_low_date eligibility
not a 50% winner in forward horizon
```

用途：

- 区分 winner 特征和当时市场共同特征。
- 避免把牛市 beta 当作 winner 特征。

### 7.2 Observable-Anchor Opportunity Controls

用途：

- 用于 observable-anchor-aligned profile。
- 对比对象必须触发同一类 observable anchor。

对每个 winner observable anchor，匹配：

```text
same anchor family
same anchor date or nearest available same-week anchor date
same industry if PIT industry data is available
similar market cap bucket
similar liquidity bucket
similar prior return / drawdown / volatility bucket
not a 50% winner in forward horizon
```

如果某个 anchor family 的 opportunity controls 不足，该 anchor 的 dominance claim 必须 sample-blocked。

### 7.3 Near-Winner Controls

定义：

```text
forward MFE over the same 120 trading day window in 30% to 50%
but never reaches 50% within that same 120d horizon
```

Matching requirements:

```text
same opportunity-set type as the winner comparison:
  candidate_low_date for low-aligned profile
  same anchor family for anchor-aligned profile
same date or nearest available same-week date
same industry if PIT industry data is available
same market-regime bucket
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return
similar prior drawdown
similar volatility bucket
```

用途：

- 区分真正右尾 winner 和普通强势波段。
- 找出从 30% 到 50% 的 continuation path difference。

### 7.4 False-Repair Controls

定义：

```text
出现 early repair anchor
but fails within 10d / 20d
or forward MFE insufficient
```

Matching requirements:

```text
same early repair anchor family
same anchor date or nearest available same-week anchor date
same industry if PIT industry data is available
same market-regime bucket
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return
similar prior drawdown
similar volatility bucket
```

用途：

- 区分 early repair 中的真启动和假修复。
- 为后续 `failure_10` meta-label 提供依据。

## 7.5 固定 Split 口径

Split assignment 使用 `episode_low_date`，不能在看到画像结果后调整。

初始 split：

```text
train:
  2017-01-03 <= episode_low_date <= 2021-12-31

validation:
  2022-01-01 <= episode_low_date <= 2023-12-31

robustness:
  2024-01-01 <= episode_low_date <= latest_label_complete_low_date
```

Validation interpretation:

```text
validation_2022_2023_role = negative_beta_stress_validation
```

The 2022-2023 window is intentionally kept as the chronological validation
split, even though it may be a negative-beta / weak-opportunity market regime.
This split should answer a narrower question:

```text
Does the lifecycle dominance survive a weak-market stress regime,
or is it explicitly regime-conditional?
```

It must not be interpreted as an ordinary market-neutral validation window. The
report must separate:

```text
unconditional_validation_readout:
  all validation episodes and matched controls

regime_conditioned_validation_readout:
  validation episodes and controls grouped by market-regime bucket

validation_opportunity_audit:
  winner episode count, near-winner count, false-repair count, and control
  match coverage inside the validation window
```

If validation has too few winner episodes or matched controls, the result is
sample-blocked for unconditional validation. The experiment must not move the
split boundary, shorten the horizon, lower the +50% winner threshold, or use
2024-2025 robustness results to rescue a failed or sample-blocked 2022-2023
validation readout.

Allowed interpretation states:

```text
universal_dominance_candidate:
  claim passes train, negative-beta validation, and robustness

regime_conditional_candidate:
  claim fails or is weak in negative-beta validation,
  but passes within matching market-regime buckets where sample support exists

negative_beta_not_supported:
  claim has adequate validation sample support but does not hold in 2022-2023

validation_sample_blocked:
  validation winner/control sample support is insufficient
```

其中：

```text
latest_label_complete_low_date =
  latest trading session D such that D has at least 120 forward trading sessions
```

If robustness has fewer than `min_robustness_winner_episodes`, the experiment must return `reverse_lifecycle_profile_sample_blocked`. It must not move the split boundary, shorten the 120d horizon, lower the +50% threshold, or include label-incomplete lows just to satisfy the sample gate.

如果 post-high 30d 画像不完整，只影响 post-high 统计，不允许把该 episode 从 primary reference 中静默删除。相关输出必须用 `profile_post_high_complete` 或 censored 口径分开报告。

Matched controls inherit the split of the winner episode or anchor they are matched to. A control row must not be used to improve split stability in a different split.

## 8. 统计输出

输出目录需要对齐 experiment template：

```text
outputs/publishable/tables/big_winner_episode_reference_summary.csv
outputs/publishable/tables/frozen_anchor_profile_summary.csv
outputs/publishable/tables/winner_vs_matched_control_stats.csv
outputs/publishable/tables/near_winner_comparison_stats.csv
outputs/publishable/tables/false_repair_comparison_stats.csv
outputs/publishable/tables/shared_axis_market_regime_dominance.csv
outputs/publishable/tables/winner_only_retrospective_stage_profile.csv
outputs/publishable/tables/winner_only_industry_regime_x_retrospective_stage.csv  # conditional on PIT industry data
outputs/publishable/tables/shared_axis_factor_dominance.csv
outputs/publishable/tables/shared_axis_sequence_dominance.csv
outputs/publishable/tables/sequence_family_test_count.csv
outputs/publishable/tables/sequence_examples_descriptive.csv
outputs/publishable/reports/reverse_lifecycle_profile_report.md
outputs/manifests/run_manifest.json
```

Conditional artifact rule:

```text
if industry_data_status != pit_available:
  do not generate primary winner_only_industry_regime_x_retrospective_stage.csv
  do not include industry-relative rows in shared_axis_factor_dominance.csv
  do not include industry-relative states in shared_axis_sequence_dominance.csv
  report industry diagnostics as skipped or diagnostic-only caveat
```

Large or regenerable artifacts must not be treated as publishable by default:

```text
outputs/local_cache/big_winner_episode_reference.parquet
outputs/local_cache/episode_aligned_daily_panel.parquet
outputs/local_cache/matched_control_panel.parquet
outputs/large_raw/control_candidate_pool.parquet
outputs/large_raw/anchor_aligned_daily_panel.parquet
```

If a raw CSV would be large, publish a summary table and keep the raw artifact in `local_cache` or `large_raw`.

Control-adjusted dominance tables:

```text
shared_axis_market_regime_dominance.csv:
  winner vs control comparisons by shared alignment axis,
  relative-day bucket, split, and market-regime bucket

shared_axis_factor_dominance.csv:
  winner vs control factor differences by shared alignment axis,
  relative-day bucket, split, anchor family, and optional regime bucket

shared_axis_sequence_dominance.csv:
  winner vs control sequence-rate differences by shared alignment axis,
  frozen sequence family, relative window, split, regime bucket, and duration bucket
```

Sequence dominance is reported separately from marginal factor dominance.
Winner-only sequence maps are descriptive and must not support event claims.

Initial frozen sequence families should be small enough to avoid open-ended
data snooping:

```text
S1_context_to_repair:
  market/industry context -> price repair

S2_repair_to_money_confirmation:
  price repair -> amount expansion -> VWAP or range hold

S3_repair_to_rank_persistence:
  price repair -> rank jump -> rank persistence

S4_contraction_to_expansion:
  volatility contraction -> expansion -> upper-half close

S5_money_expansion_without_distribution:
  amount expansion -> no gap fade -> no destructive upper shadow

S6_continuation_discriminator:
  +20% path state -> rank/money persistence -> near-winner vs big-winner continuation
```

`S6_continuation_discriminator` can only use a close-observed `+20%` state
measured from the same shared axis price basis. It must not use winner-only
retrospective stages such as `20pct_to_high` or any retrospective high date.
`near-winner` and `big-winner` are outcome groups for this discriminator; they
must not appear as required states inside the sequence definition.

Each sequence family must freeze required states, forbidden states, windows,
order constraints, missing-value rules, and shared-axis eligibility before
entering publishable dominance statistics.

All sequence windows, order constraints, forbidden-state windows, thresholds,
and admissible variants must be frozen once using train-split evidence only.
Validation and robustness must not be used to select, prune, retime, or
otherwise tune sequence structure. `sequence_family_test_count.csv` must count
every tested variant, including variants inspected and rejected before the
reported sequence was selected.

At minimum, `sequence_family_test_count.csv` must expose tested, reported, and
rejected variant counts, the `train_only` selection basis, and the FDR
denominator used for each sequence family.

Winner-only descriptive tables:

```text
winner_only_retrospective_stage_profile.csv:
  reclaim_to_20pct, 20pct_to_high, post_high_30d,
  and other stages that only exist for winner paths
```

The report may show a winner-only lifecycle map, but it must label it as
descriptive profile, not dominance:

```text
pre_low_30d:
  market / industry / stock drawdown context

low_to_reclaim:
  early repair pattern, individual leadership, volume/money repair

reclaim_to_20pct:
  confirmation pattern, volatility expansion, industry reaction if PIT industry data is available

20pct_to_high:
  continuation path pattern, industry breadth if available, rank persistence, path tolerance

post_high_30d:
  rank evaporation, gap fade, destructive high-vol, exhaustion / continuation split
```

Any statement using the retrospective lifecycle stages above must use language
such as `winner-only descriptive pattern`. It must not be written as
`dominance`, `edge`, or `winner-control difference`.

## 8.1 成功标准和证伪条件

本实验必须能成功地产生 null result。不是每次反向画像都应该蒸馏出 event anchor 或 sequence-completion event。

实验级 sample gates：

```text
min_total_winner_episodes = 150
min_validation_winner_episodes = 30
min_robustness_winner_episodes = 30
min_control_match_coverage = 80%
min_average_controls_per_winner = 3
min_anchor_occurrences_for_claim = 50
min_sequence_occurrences_for_claim = 50
min_feature_non_missing_coverage_for_claim = 70%
min_anchor_year_coverage_for_claim = 3  # auxiliary concentration check
min_anchor_split_coverage_for_headline_claim = train + validation + robustness
min_sequence_split_coverage_for_headline_claim = train + validation + robustness
```

`min_anchor_occurrences_for_claim = 50` and
`min_sequence_occurrences_for_claim = 50` are all-split cumulative gates.
`*_split_coverage_for_headline_claim = train + validation + robustness` means
nonzero support in each split, not 50 occurrences per split.

若不满足，final decision 应为：

```text
reverse_lifecycle_profile_sample_blocked
```

单个 dominance claim 的最低证据要求：

```text
continuous_factor:
  abs(standardized_mean_difference_winner_vs_control) >= 0.25

binary_or_bucket_factor:
  odds_ratio_or_lift_winner_vs_control >= 1.25
  or absolute_rate_difference >= 5 percentage points

sequence_pattern:
  odds_ratio_or_lift_winner_vs_control >= 1.25
  or absolute_rate_difference >= 5 percentage points

stability:
  same sign in validation and robustness
  headline claims must have nonzero support in train, validation, and robustness
  no single year or instrument explains the majority of the effect
```

Universal headline claims must pass the negative-beta validation split. A claim
that is sample-blocked or unsupported in 2022-2023 can only be reported as a
`regime_conditional_candidate`, and the report must name the unsupported regime
explicitly. Robustness performance in 2024-2025 cannot upgrade a
negative-beta-unsupported claim into a universal claim.

This design intentionally makes `universal_dominance_candidate` difficult to
achieve. The most likely valid outputs may be `regime_conditional_candidate`,
`negative_beta_not_supported`, or sample-blocked states. Those outcomes are not
implementation failures; they are expected conclusions if the negative-beta
validation window has weak opportunity support or rejects the pattern.

Multiple-testing discipline:

```text
report_total_tests:
  every factor x stage x anchor x regime x duration-bucket comparison must be counted
  every sequence family x shared axis x relative window x regime x duration-bucket comparison must be counted

headline_claim:
  must report total tests in its family
  must pass the effect-size threshold in validation and robustness
  must not be selected solely from winner-only descriptive tables
  if p-values are reported, also report BH-FDR adjusted q-values within each claim family

non_headline_claim:
  label as exploratory unless confirmed by the frozen validation and robustness criteria
```

BH-FDR claim-family boundaries are fixed:

```text
marginal_factor_families:
  market_regime
  industry_regime, conditional on PIT industry data
  price_structure
  volume_money_vwap_turnover
  volatility_structure
  relative_strength
  path_tolerance

sequence_families:
  S1_context_to_repair
  S2_repair_to_money_confirmation
  S3_repair_to_rank_persistence
  S4_contraction_to_expansion
  S5_money_expansion_without_distribution
  S6_continuation_discriminator
```

BH-FDR, if reported, is computed separately within each fixed family. Marginal
families and sequence families must not borrow significance from each other.

Split-stable sign alone is not enough to promote a claim when hundreds of candidate comparisons were inspected.

如果没有任何 factor 或 sequence 满足上述要求，final decision 应为：

```text
marginal_and_sequence_no_stable_dominance_found
```

如果单因子无稳定 dominance，但冻结状态序列有 matched-control 支持，必须根据支持强度写成以下唯一 decision 之一：

```text
reverse_lifecycle_sequence_supported_universal_dominance
reverse_lifecycle_sequence_conditional_candidate
```

如果只有 winner-only profile 显著、matched-control 差异不显著，必须写成：

```text
descriptive_profile_only_no_control_adjusted_support
```

本实验成功的最低标准不是找到 event，而是：

- reference episode 可复现。
- control matching 可审计。
- factor 或 sequence dominance claim 有对照、有样本、有稳定性。
- null result 被明确允许。

## 9. 后续如何转成 AFML Event

本实验本身不直接授权 event 或 strategy。

Non-goals:

- 不训练模型。
- 不运行 backtest。
- 不输出 entry / exit / sizing rule。
- 不模拟 stop-loss / time-stop policy。
- 不把 retrospective low/high 转成可交易信号。
- 不在缺少 PIT 行业数据时输出 primary industry conclusion。
- 不把 current discussion 直接升级为 `03_observable_anchor_event_contract_v0`。

它的目标是从反向画像中筛出可观察候选锚点、状态路径或序列完成条件：

```text
reverse lifecycle profile
  -> observable anchors for alignment
  -> lifecycle state/path dominance
  -> candidate anchor or sequence-completion event
  -> sparse / conditional event contract
  -> AFML t0 / t1 labels
  -> failure_10 / confirm_20 / continuation_60 / winner_120
  -> purged walk-forward validation
```

只有当某个锚点或序列完成条件同时满足以下条件，才进入下一阶段 event contract：

- 可 close-observed。
- next open 可执行。
- 不依赖 retrospective low/high。
- 若是序列，`t0` 必须是全部 required states 已可观察的 completion date。
- seed-day density 可控。
- winner recall 不靠高密度买来。
- 与 matched controls 相比有稳定差异。
- instrument-year lift 不塌。
- market / industry regime 解释清楚。
- failure false reject 可控。

## 10. 当前共识

当前最重要的共识：

```text
不要再急着正向找 event。
先反向找出 A 股 big winner 的生命周期统治因素。
再从这些统治因素中挑出可观察、稀疏、可验证的 anchor 或 sequence-completion event。
```

这个实验完成后，下一步才是：

```text
03_observable_anchor_event_contract_v0
```

或者类似的 AFML event 需求。
