# EP4 需求 03e: Family Signal 后 10 日坏形态过滤诊断 V1

## 1. 需求元信息

- 需求 id: `ep4_r03e_family_signal_bad_shape_filter_diagnostic_v1`
- 简称: `r03e_family_signal_bad_shape_filter_diagnostic_v1`
- 状态: 可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion3.md`
- 上游 R02 precision 需求: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- 上游 R02 path-query 需求: `ep4/requirement_02_family_signal_120d_path_query_v1.md`
- 上游 R03b 需求: `ep4/requirement_03b_signal_sequence_big_winner_path_diagnostic_v1.md`
- 上游 R03c 需求: `ep4/requirement_03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1.md`
- 上游 R03d 需求: `ep4/requirement_03d_family_order_stage_role_diagnostic_v1.md`
- 必需输出根目录: `ep4/outputs/r03e_family_signal_bad_shape_filter_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r03e_family_signal_bad_shape_filter_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r03e_family_signal_bad_shape_filter_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r03e_family_signal_bad_shape_filter_diagnostic.py`
- 日期: 2026-05-17

## 2. 实验目的

R03b/R03c/R03d 的结果说明：

1. fresh family accumulation 能明显改善 seed-anchor 的 `P_good / P_bad`，但 fresh-anchor 剩余路径仍偏弱。
2. family 出现顺序本身没有稳定超过 unordered family presence / price-state baseline。
3. 后续更值得研究的不是更复杂的 sequence order，而是 family signal 出现后的 entry timing / bad-shape rejection。

本需求新增一个探查问题：

```text
当 7 个 frozen family signal 出现后，观察之后 10 个交易日内是否出现放量滞涨、
新高失败、长上影密集、跌破 MA20 后收不回等坏形态。
如果过滤掉坏形态，剩余样本的 big-winner rate、P_good、P_bad 是否改善？
```

核心输出必须回答：

1. 坏形态过滤能否降低 `P_bad`？
2. 降低 `P_bad` 的同时，会不会误杀太多后续 big winner？
3. 改善是否超过单纯等待到 T+10 的 survival / timing baseline？
4. 哪些 bad-shape component 最有解释力，哪些只是重复描述同一种顶部震荡状态？
5. 过滤后结果在 train / validation / robustness 中是否方向一致？

本实验是 diagnostic，不是 production entry rule，不是 stop rule，不是减仓规则。

## 3. 关键口径

### 3.1 时间锚点

对每个 family signal event：

```text
signal_date = family signal 出现日
t0_entry_date = signal 后第一天可执行开仓日，即 first executable next-open date
shape_eval_date = t0_entry_date 后第 10 个有效交易日
shape_core_window_20d = (T0-10 through T0-1) union (T0+1 through T0+10)
shape_post_entry_window = t0_entry_date + 1 through shape_eval_date
```

本需求里的“20 日内”统一指 `shape_core_window_20d`，也就是以 T0 开仓日为中心、排除 T0 当天的前后各 10 个交易日：

```text
core_pre_entry_window = relative_offset -10 through -1
core_post_entry_window = relative_offset +1 through +10
shape_core_window_20d = core_pre_entry_window union core_post_entry_window
core_bar_count_required = 20
```

T0 当天只作为开仓锚点和窗口中心，不进入 20 日形态计数、均值、最大涨跌日、上下影线天数或上下跌日均量。不得把 `shape_core_window_20d` 解释为 `shape_eval_date` 往前滚动 20 日，也不得把 `relative_offset = -10..+10` 的 21 根 bar 全部计入 primary BadScore。

所有坏形态特征只允许使用 `shape_eval_date` 当天或之前的数据。不得使用 `shape_eval_date + 1` 之后的价格、成交量、label 或 future return 构造 bad-shape flag。

`shape_eval_date` 与 filter-anchor forward path 必须保持 split-bounded：

```text
shape_eval_date must remain in the same split as t0_entry_date
filter-anchor h120 path must remain inside the same split boundary
```

如果跨 split 或 forward path 不完整，只能进入 incomplete audit，不得进入 headline denominator。

### 3.2 两套 outcome 必须分开

因为过滤器使用了 T0 开仓后 10 天的数据，不能把过滤后的样本直接解释成 T0 当时可知的可执行收益。因此必须同时输出两套 outcome。

Signal-anchor retention audit：

```text
从原始 T0 entry anchor 看：
  被过滤掉的样本里有多少原始 big winner / good_path？
  通过过滤的样本保留了多少原始 big winner / good_path？
```

这只回答误杀和覆盖问题，不得用作过滤后可执行收益。

Filter-decision-anchor primary outcome：

```text
从 shape_eval_date close 或 shape_eval_date 后 next open 重新锚定：
  通过坏形态过滤后，剩余样本之后 120D 的 big-winner rate、P_good、P_bad 是多少？
```

最终报告的过滤效果判断必须以 filter-decision-anchor 为主，并以 T+10 survivor baseline 为 parent baseline。

### 3.3 必需 baseline

必须比较三层样本：

```text
baseline_0_signal_anchor_all:
  signal_date 当天所有 family signal event。

baseline_1_t10_survivor_no_badshape_filter:
  有完整 shape_eval_date、完整 filter-decision-anchor outcome、
  完整 shape_core_window_20d，且 bad_score_complete_flag == true 的样本；
  不应用 bad-shape filter。

badshape_filtered:
  在 baseline_1 中，按 BadScore 或 component policy 过滤后的样本。
```

`baseline_1_t10_survivor_no_badshape_filter` 是 primary BadScore threshold 的 parent denominator。它不是纯 survival denominator，而是 “T+10 survivor + BadScore 可评估” denominator。BadScore 不完整的 event 必须保留在 audit 中，但不得进入 headline lift。

component-only policy 必须使用自己的 policy-evaluable denominator：

```text
component_policy_denominator(component_x) =
  baseline_1 rows where component_x is not null
```

component flag 为 null 的 row 不得被当作 component 未触发，也不得进入该 component-only policy 的 passed/dropped denominator。

headline lift 只能使用：

```text
badshape_filtered vs baseline_1_t10_survivor_no_badshape_filter
```

不得把 `badshape_filtered` 直接和 `baseline_0_signal_anchor_all` 比较后宣称过滤器有效，因为这会把等待 10 天的 survival bias 算进过滤器。

### 3.4 主决策粒度

R03e 的最终 `final_decision` 只允许由下面的 primary decision grain 决定：

```text
event_scope = r02_signal_episode_start
event_stage = r02_episode_start
family_group = all_families_dedup_weighted
outcome_anchor = filter_decision_next_open_anchor
filter_policy = drop_score_ge5
parent_policy = no_badshape_filter_t10_survivor
```

解释：

- `r02_signal_episode_start` 是 action-time family signal 的完整 T0 entry 分母，最适合作为“如果 T0 日开仓”的主判断。
- `all_families_dedup_weighted` 使用 `dedup_weight` 汇总，同一股票同日多个 family 只贡献 1 个 stock-day 权重。
- `filter_decision_next_open_anchor` 是 T+10 观察完成后的可执行锚点；`filter_decision_close_anchor` 只做 close-anchor audit。
- `r03_seed_family_event` 和 `r03_clean_fresh_family_event` 只能作为 lifecycle / stage audit，不得决定最终 `final_decision`。
- by-family、by-stage、by-component 结果可以在 final report 中点名，但不得覆盖 primary decision grain。

## 4. 实验边界

允许：

- 复用 R02 的 7 个 frozen single-family condition。
- 复用 R02 action-time panel 中的 family signal occurrence / signal episode 信息。
- 复用 R03b seed episode 与 R03c clean primary fresh step，构造 R03 lifecycle family signal event。
- 使用本地 PIT OHLCV / money / turnover 数据，计算 `shape_core_window_20d` 的坏形态，并在 T+10 做过滤决策。
- 重新从 `shape_eval_date` 计算 120D big-winner 和 path label。
- 按 family、event stage、bad-score bucket、component、split 输出统计。
- 输出 score threshold tradeoff，而不是只输出单一阈值。

禁止：

- 不得在线抓取数据。
- 不得用 validation / robustness outcome 选择 bad-shape 阈值、component 权重或过滤策略。
- 不得把本需求输出写成 production entry / add / stop / reduce 规则。
- 不得把 signal-anchor filtered outcome 解释成 T0 可执行收益。
- 不得忽略 T+10 survivor baseline。
- 不得用 future big winner、future good/bad label 或未来最大收益构造任何 bad-shape component。
- 不得把同日 multi-family signal 拆成有先后顺序的事件。
- 不得只报告通过过滤后的样本而不报告被过滤样本的 big-winner / good-path retention。

## 5. Family Universe

只允许使用下面 7 个 frozen family：

```text
range_breakout
volume_money
oscillator
volatility_band
pullback_drawdown
momentum_rps
price_trend
```

runner 必须 fail closed：

- 输入 family 不在上述 universe；
- 出现 `single_range_breakout` 这类带前缀名称但没有显式映射；
- 配置中的 7 个 frozen condition 与 R02 precision config 不一致。

## 6. 必需输入产物

所有输入必须来自本地 artifact。

R02 precision 输入：

```text
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_manifest.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_validation.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet
ep4/configs/r02_family_precision_forward_return_stats_v1.yaml
```

R02 path-query 输入：

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_manifest.json
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_validation.json
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/signals/*_120d_path.csv
```

R03 lifecycle 输入：

```text
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_manifest.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_validation.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_seed_episode_panel.parquet
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/manifests/r03c_price_aware_kth_fresh_family_set_pooling_manifest.json
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/manifests/r03c_price_aware_kth_fresh_family_set_pooling_validation.json
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/cache/r03c_fresh_step_price_panel.parquet
```

PIT OHLCV 输入：

```text
由 ep4/configs/r01_high_recall_probe_fail_fast_v2.yaml 指向的本地 provider spine 重建。
必须包含 instrument_id/date/split/open/high/low/close/volume。
money/amount/turnover 如果存在则保留；不存在时 money = volume * close。
```

runner 必须校验：

```text
r02_family_precision_forward_return_stats_validation.json.validation_status == passed
r02_family_signal_120d_path_query_validation.json.validation_status == passed
r03b_signal_sequence_big_winner_path_validation.json.validation_status == passed
r03c_price_aware_kth_fresh_family_set_pooling_validation.json.validation_status == passed
```

如果任一必需 validation 未通过或缺失，runner 不得继续生成 headline tables。

## 7. 输出目录结构

runner 必须写出：

```text
ep4/outputs/r03e_family_signal_bad_shape_filter_diagnostic_v1/
  cache/
    r03e_family_signal_event_panel.parquet
    r03e_ohlcv_shape_window_panel.parquet
    r03e_bad_shape_feature_panel.parquet
    r03e_bad_shape_filter_panel.parquet
  reports/
    r03e_input_readiness_audit.csv
    r03e_bad_shape_component_definition_audit.csv
    r03e_bad_shape_component_summary.csv
    r03e_bad_score_bucket_summary.csv
    r03e_bad_score_threshold_tradeoff.csv
    r03e_filtered_outcome_summary.csv
    r03e_component_overlap_audit.csv
    r03e_survival_and_timing_bias_audit.csv
    r03e_split_stability_audit.csv
    r03e_family_signal_bad_shape_filter_final_report.md
    r03e_family_signal_bad_shape_filter_validation_audit.csv
  manifests/
    r03e_family_signal_bad_shape_filter_manifest.json
    r03e_family_signal_bad_shape_filter_validation.json
```

## 8. Family Signal Event Panel

`r03e_family_signal_event_panel.parquet` 的 primary grain：

```text
one row per family signal event
```

必须包含三类 event scope：

```text
r03_seed_family_event:
  one row per seed_episode_id x family in seed_family_set

r03_clean_fresh_family_event:
  one row per clean primary fresh step x family in added_family_set

r02_signal_episode_start:
  one row per R02 family signal episode start from r02_family_action_time_panel
```

R03 clean fresh event 必须继承 R03c clean primary fresh step 定义：

```text
included_in_primary_fresh_count == true
step_status in {fresh_distinct_family_step, same_offset_multi_family_step}
3 <= step_offset <= 30
step_offset < observable_failure_offset, if observable_failure_offset exists
```

同一 offset 出现多个 family 时，可以拆成多条 family event row，但必须保留：

```text
same_offset_multi_family_flag
same_date_family_count
dedup_weight = 1 / same_date_family_count
```

任何 overall summary 必须同时报告：

```text
unweighted family_event result
dedup_weighted stock_day result
```

不得用 unweighted multi-family rows 夸大总体样本量。

必需字段：

```text
family_signal_event_id
event_scope
source_event_id
seed_episode_id
instrument_id
split
family_id
condition_group_id
signal_date
signal_offset_from_seed
event_stage
same_offset_multi_family_flag
same_date_family_count
dedup_weight
t0_entry_date
t0_entry_price
signal_close
signal_next_open
signal_anchor_big_winner
signal_anchor_big_winner_anchor
signal_anchor_path_label
signal_anchor_path_label_policy
signal_anchor_complete_h120_flag
signal_anchor_outcome_source
shape_eval_date
shape_eval_close
shape_eval_next_open
shape_eval_complete_flag
filter_anchor_complete_h120_flag
```

`event_stage` 固定为：

```text
seed
fresh_1
fresh_2
fresh_3
fresh_4plus
r02_episode_start
```

`condition_group_id` 固定来源：

```text
r02_signal_episode_start:
  use R02 action panel `condition_group_id`

r03_seed_family_event:
  map `family_id` to the unique R02 frozen single-family `condition_group_id`
  from `ep4/configs/r02_family_precision_forward_return_stats_v1.yaml`

r03_clean_fresh_family_event:
  map `family_id` to the unique R02 frozen single-family `condition_group_id`
  from `ep4/configs/r02_family_precision_forward_return_stats_v1.yaml`
```

该映射必须是 1:1。若某个 `family_id` 对应 0 个或多个 frozen single-family `condition_group_id`，runner 必须 fail closed，并在 `r03e_input_readiness_audit.csv` 写出：

```text
blocked_missing_condition_group_mapping
blocked_ambiguous_condition_group_mapping
```

### 8.1 Signal-Anchor 字段 Lineage

`signal_anchor_*` 字段必须按 `event_scope` 使用固定来源，不得由实现自行选择。

| event_scope | signal_date | t0_entry_date / price | signal_anchor_big_winner | signal_anchor_path_label | signal_anchor_complete_h120_flag |
|:--|:--|:--|:--|:--|:--|
| `r03_seed_family_event` | R03b `seed_trade_date` | R03b `seed_entry_date` / `seed_entry_price` | R03b `big_winner_forward_h120_next_open_anchor` | R03b `label` | R03b `entry_valid == true` and `path_complete_120d == true` |
| `r03_clean_fresh_family_event` | R03c `step_signal_date` | R03c `fresh_entry_date` / `fresh_entry_price` | R03c `fresh_big_winner_forward_h120_next_open_anchor` | R03c `fresh_path_label` | R03c `fresh_entry_valid == true` and `fresh_path_complete_120d == true` |
| `r02_signal_episode_start` | R02 action panel `episode_signal_date` | first executable next-open after `episode_signal_date` from local PIT spine / `episode_entry_price_t` | R02 action panel episode-start row `big_winner_forward_from_next_open` | derive from R02 path-query matched row using `signal_anchor_path_label_policy = r02_path_query_label_v1` | R02 action panel `complete_h120_flag == true` and matched R02 path-query row `entry_valid == true` and `path_complete_120d == true` |

R02 path-query matching key:

```text
instrument_id
family_id
signal_date = episode_signal_date
```

`r02_path_query_label_v1`：

```text
censored_or_invalid:
  entry_valid == false
  or path_complete_120d == false

bad_path:
  path_complete_120d == true
  and (
    early_failure_flag == true
    or (
      first_minus5_offset is not null
      and (
        first_plus10_offset is null
        or first_minus5_offset <= first_plus10_offset
      )
    )
    or max_loss_before_first_plus10 <= -0.06
    or severe_drawdown_flag == true
  )

good_path:
  path_complete_120d == true
  and path_quality_flag in {clean_continuation, tradable_continuation}
  and hit_plus10_before_minus5 == true
  and max_loss_before_first_plus10 > -0.06

neutral_path:
  path_complete_120d == true
  and neither good_path nor bad_path
```

如果 `r02_signal_episode_start` 无法唯一匹配 R02 path-query row，runner 必须 fail closed，并在 `r03e_input_readiness_audit.csv` 写出：

```text
blocked_missing_r02_path_query_match
blocked_duplicate_r02_path_query_match
```

## 9. OHLCV Shape Window Panel

`r03e_ohlcv_shape_window_panel.parquet` 粒度：

```text
one row per family_signal_event_id x relative_offset
```

`relative_offset` 必须相对 `t0_entry_date`，不是相对 `signal_date`：

```text
relative_offset = 0 on t0_entry_date
relative_offset = -10 at T0 - 10 trading days
relative_offset = +10 at T0 + 10 trading days = shape_eval_date
```

`relative_offset` 对 complete headline event 的 event-window materialization 必须覆盖：

```text
-252 through +131
```

解释：

```text
shape_eval_date = relative_offset +10
filter_entry_date = first executable next-open date after shape_eval_date
ordinary filter_entry_relative_offset = +11
filter_path_offsets 0..120 inclusive therefore requires relative_offset +11..+131
```

如果 `filter_entry_date` 因停牌、不可交易或 executable spine 过滤而晚于 ordinary +11，则 complete headline event 必须额外覆盖到：

```text
dynamic_filter_path_end_offset = filter_entry_relative_offset + 120
```

如果 runner 没有额外 materialize 这些行，该 event 必须标记为 filter-anchor path incomplete，不得进入 headline denominator。

上述 event-window materialization 不是 as-of 指标历史上限。ATR20 / ATR252 分位数等长历史指标必须从本地 PIT provider 的 instrument full history 重算，且只允许读取 `date <= shape_eval_date` 的数据。

最小可保留 audit 覆盖：

```text
-60 through +120
```

最小可保留 audit 覆盖只允许用于 incomplete audit，不允许进入 primary headline。进入 primary headline 的 event 必须满足完整 as-of 历史、`shape_core_window_20d`、BadScore 和 filter-anchor path 覆盖要求。

如果某个 event 无法取得 `shape_eval_date`、必需 as-of 历史、完整 `shape_core_window_20d` 或 filter-anchor 120D path，必须保留 event row，并标记：

```text
shape_eval_complete_flag = false
shape_incomplete_reason
filter_anchor_complete_h120_flag = false
filter_anchor_incomplete_reason
```

不得因为不完整而静默删除 event。

必需 OHLCV 字段：

```text
family_signal_event_id
instrument_id
date
relative_offset
split
open
high
low
close
volume
money
turnover_proxy
daily_return
true_range
```

## 10. 坏形态定义

所有 primary “20 日内”形态、`ret20`、`volume_mean20`、`upper_shadow_count20`、上下跌日统计和最大涨跌日统计，都必须使用排除 T0 的 `shape_core_window_20d = [-10..-1] union [+1..+10]`。需要 60 日均量、MA20 或 252 日 ATR 分位数时可以使用更长 as-of 历史，但不得超过 `shape_eval_date`。

核心窗口字段必须按下面口径落地：

```text
core_start_date = date at relative_offset = -10
core_end_date = date at relative_offset = +10 = shape_eval_date
ret20_core = close(core_end_date) / close(core_start_date) - 1
volume_mean20_core = mean(volume over relative_offset -10..-1 and +1..+10)
upper_shadow_count20_core = count upper-shadow days over relative_offset -10..-1 and +1..+10
core_recent_segment = relative_offset +6 through +10
core_prior_segment = relative_offset -10 through -1 and +1 through +5
```

如果 `shape_core_window_20d` 的 20 根必需 OHLCV 任一缺失，则 primary BadScore 不能进入 headline denominator；该 event 必须进入 incomplete audit。T0 当天 OHLCV 缺失不影响形态窗口计数，但如果 T0 entry 本身缺失，则该 event 不得进入任何 T0 entry-anchor retention denominator。

通用 as-of 字段：

```text
volume_mean60_asof_t10 =
  mean(volume over the latest 60 valid trading rows ending at relative_offset +10)

volume_mean60_asof_d =
  mean(volume over the latest 60 valid trading rows ending at event day d)

atr20_pct_asof(offset) =
  Wilder ATR20(offset) / close(offset), using full local PIT history
  with data <= offset

atr20_pct_rank252(offset) =
  percentile rank of atr20_pct_asof(offset) among the latest 252 valid
  atr20_pct_asof values ending at offset

atr20_pct_rank252_complete(offset) =
  at least 252 valid atr20_pct_asof values ending at offset,
  and each atr20_pct_asof value is computed after ATR20 warmup is complete

ma20_asof(offset) =
  mean(close over the latest 20 valid trading rows ending at offset)

ma20_slope5_t10 =
  ma20_asof(+10) / ma20_asof(+5) - 1

prior20_high_before(d) =
  max(high over the 20 valid trading rows ending at d-1)

ret60_asof_t10 =
  close(relative_offset +10) / close(relative_offset -50) - 1
  using 60 trading intervals ending at +10

core_followup_window_after(d, n) =
  offsets in shape_core_window_20d where offset > d and offset <= min(d+n, +10)
  this window must exclude relative_offset 0
```

ATR20 / ATR252 完整性要求：

```text
asof_history_policy = provider_full_history_until_shape_eval
atr20_warmup_min_tr_rows = 20
atr_rank252_min_values = 252
atr_rank252_min_ohlcv_rows_ending_at_target = 281
```

解释：`atr20_pct_rank252(-10)` 不能只靠 event-window 的 `-252..` 覆盖计算。若没有 provider-wide precomputed ATR20 cache，则 validator 必须能从本地 PIT OHLCV 重算，并确认目标 offset 之前至少有 `252 + 20 + prior_close` 对应的有效历史。若 `atr20_pct_rank252(-10)` 或 `atr20_pct_rank252(+10)` 不完整，相关 component / BadScore item 必须为 null，并触发 BadScore incomplete 规则。

如上述任一 required as-of field 缺失，对应 component flag 必须为 null，并进入 `shape_incomplete_reason`；不得把缺失当作 false。

任何 detailed flag 或 BadScore item 需要 “随后 N 日” 判断时，必须使用 `core_followup_window_after(d, N)`。不得因为 `d < 0` 把 T0 当天纳入 follow-up check。如果 `core_followup_window_after(d, N)` 为空，该 candidate day `d` 不能触发对应 flag；若所有 candidate day 都因为 follow-up 不足而无法判断，则该 component flag 必须为 null。

### 10.1 详细坏形态 flags

必须输出下面 10 个 detailed shape flags：

| flag | 定义 | 用户意图 |
|:--|:--|:--|
| `volume_stall_flag` | `volume_mean20_core / volume_mean60_asof_t10 >= 1.10` 且 `ret20_core <= 0.02`；如果本地行业收益可用，还要求或报告 `ret20_core - industry_ret20_core <= -0.02` | 放量但价格推不动 |
| `failed_breakout_flag` | 存在 `d` 属于 `shape_core_window_20d`，满足 `(high_d > prior20_high_before(d) or close_d > prior20_high_before(d))`，且 `volume_d / volume_mean60_asof_d >= 1.30`；`core_followup_window_after(d, 5)` 任一日 `close < prior20_high_before(d)` | 新高失败 |
| `dense_upper_shadow_flag` | `shape_core_window_20d` 内 `upper_shadow / intraday_range >= 0.50` 的天数 >= 3；`intraday_range = high - low`，若 `high == low` 则该日不计入分子但计入缺失审计 | 长上影线密集 |
| `down_volume_dominance_flag` | `shape_core_window_20d` 内下跌日均量 > 上涨日均量，且下跌日平均绝对跌幅 > 上涨日平均涨幅；上下跌日都至少各 3 天，否则 component flag = null | 下跌日量大，上涨日量小 |
| `ma20_break_no_reclaim_flag` | 存在 `d` 属于 `shape_core_window_20d`，`close_d < ma20_asof(d)`；非空 `core_followup_window_after(d, 5)` 全部 `close <= ma20_asof(day)`，且 `ma20_slope5_t10 <= 0` | 跌破 20 日线后收不回 |
| `large_bearish_engulf_flag` | 存在 `d` 属于 `shape_core_window_20d`，满足 `daily_return_d <= -2.5 * mean(abs(daily_return), core window)`，`volume_d / volume_mean60_asof_d >= 1.5`，`(close_d - low_d) / (high_d - low_d) <= 0.25`，并且 `(close_{d-1} / close_{d-6} - 1 > 0 and close_d <= close_{d-6}) or (close_{d-1} / close_{d-11} - 1 > 0 and close_d <= close_{d-11})` | 大阴线吞没前期涨幅 |
| `volatility_up_no_price_flag` | T+10 的 `atr20_pct_rank252` 较 T-10 上升 >= 0.20 或 T+10 当前 >= 0.70，且 `ret20_core <= 0.05` | 波动率抬升但价格不涨 |
| `low_efficiency_flag` | `abs(ret20_core) / sum(abs(daily_return), core window) <= 0.25`，并且 `volume_mean20_core / volume_mean60_asof_t10 >= 1.10` 或 `atr20_pct_asof(+10) / atr20_pct_asof(-10) - 1 >= 0.10`；若 denominator 为 0，则 flag = null | 上涨效率下降 |
| `lower_low_lower_high_flag` | `core_recent_segment` 最低价 < `core_prior_segment` 最低价，且 `core_recent_segment` 最高价未有效突破 `core_prior_segment` 最高价 1% | 低点连续下移 |
| `gap_up_fade_cluster_flag` | `shape_core_window_20d` 内高开 `open / prev_close - 1 >= 0.01` 且收盘低于开盘的天数 >= 2；若 `ret60_asof_t10 > 0.20` 必须另行标记 high-level version | 跳空高开低走 |

行业相对收益只允许作为 local-input audit。若本地没有可靠行业映射，不得在线补数据，必须输出：

```text
industry_relative_status = unavailable_local_input
```

### 10.2 Primary BadScore V1

Primary BadScore 必须严格按下面 10 个可复核 item 计算，每个 item 满足加 1 分：

| item | 字段 | 条件 |
|:--|:--|:--|
| 1 | `badscore_ret20_negative` | `ret20_core < 0` |
| 2 | `badscore_close_below_ma20` | `close(shape_eval_date) < MA20(shape_eval_date)` |
| 3 | `badscore_ma20_slope_negative` | `MA20(shape_eval_date) / MA20(shape_eval_date - 5) - 1 < 0` |
| 4 | `badscore_recent_low_breaks_prev_low` | `min(low, core_recent_segment) < min(low, core_prior_segment)` |
| 5 | `badscore_down_volume_gt_up_volume` | `down_day_avg_volume_core > up_day_avg_volume_core` |
| 6 | `badscore_max_down_gt_max_up` | `abs(min(daily_return, core window)) > max(daily_return, core window)` |
| 7 | `badscore_atr_up_return_low` | `atr20_pct_rank252(+10) - atr20_pct_rank252(-10) >= 0.20` 且 `ret20_core <= 0.05` |
| 8 | `badscore_upper_shadow_count_ge3` | `upper_shadow_count20_core >= 3` |
| 9 | `badscore_high_volume_down_days_ge2` | `shape_core_window_20d` 内 `daily_return < 0` 且 `volume / volume_mean60_asof_d >= 1.5` 的天数 >= 2 |
| 10 | `badscore_failed_breakout_3d` | `shape_core_window_20d` 内突破 prior20 high 后，`core_followup_window_after(d, 3)` 中任一日收盘跌回突破位下方 |

总分：

```text
badscore_item_complete_count =
  count of non-null badscore item flags

bad_score_complete_flag =
  badscore_item_complete_count == 10

bad_score_v1 =
  sum(10 badscore item flags), only when bad_score_complete_flag == true
```

如果任一 BadScore item 为 null：

```text
bad_score_complete_flag = false
bad_score_v1 = null
bad_score_bucket = incomplete_badscore_item
pass_primary_badshape_filter = null
drop_primary_badshape_filter = null
```

这类 row 必须保留在 audit 中，但不得进入 `baseline_1_t10_survivor_no_badshape_filter`、threshold tradeoff 或 primary final decision denominator。不得把 null item 当作 0 分。

分桶：

```text
0_2_normal
3_4_degraded_entry_quality
5_6_clear_bad_shape_avoid_new_entry
7plus_exit_or_reduce_candidate_audit
```

Primary filter policy：

```text
pass_primary_badshape_filter = bad_score_v1 <= 4
drop_primary_badshape_filter = bad_score_v1 >= 5
```

必须同时输出阈值 tradeoff：

```text
drop_score_ge3
drop_score_ge5
drop_score_ge7
component_only filters for each detailed shape flag
```

policy denominator 规则：

```text
score-threshold policies:
  denominator = baseline_1_t10_survivor_no_badshape_filter
  requires bad_score_complete_flag == true

drop_component_<component_x>:
  denominator = component_policy_denominator(component_x)
  requires component_x is not null
  dropped rows are component_x == true
  passed rows are component_x == false
```

component-only policy 必须报告因 `component_x is null` 被排除的样本数。null component 不得当作 false。

## 11. Filter-Anchor Outcome

Primary filter-anchor price：

```text
filter_signal_close_price = close(shape_eval_date)
filter_entry_date = first executable next-open date after shape_eval_date
filter_entry_price = open(filter_entry_date)
```

Primary big winner：

```text
filter_forward_close_peak_h120 =
  max(close over shape_eval_date + 1 through shape_eval_date + 120 trading days)

filter_anchor_big_winner_close =
  filter_forward_close_peak_h120 / filter_signal_close_price - 1 >= 0.50

filter_anchor_big_winner_next_open =
  max(close over filter_path_offsets 0..120 inclusive) / filter_entry_price - 1 >= 0.50
```

Primary path label 必须复用 R02/R03 path-query 的阈值方向，但所有字段必须从 `filter_entry_date / filter_entry_price` 重新计算，不得从 signal-anchor path 向前填充：

```text
filter_path_label in {good_path, bad_path, neutral_path, censored_or_invalid}
```

filter-anchor path recomputation：

```text
filter_path_offsets = 0..120 inclusive, where offset 0 is filter_entry_date
filter_entry_relative_offset = relative_offset of filter_entry_date in r03e_ohlcv_shape_window_panel
filter_path_end_relative_offset = filter_entry_relative_offset + 120
filter_available_forward_trading_days = max available offset in same split
filter_path_complete_120d = offsets 0..120 all available in same split

filter_first_plus10_offset =
  first offset where high / filter_entry_price - 1 >= 0.10

filter_first_minus5_offset =
  first offset where low / filter_entry_price - 1 <= -0.05

same_bar_plus10_minus5_policy:
  if plus10 and minus5 both first occur on the same offset,
  classify the race as downside_first for label purposes and set
  filter_same_bar_race_ambiguous_flag = true.

filter_hit_plus10_before_minus5 =
  filter_first_plus10_offset exists
  and (
    filter_first_minus5_offset is null
    or filter_first_plus10_offset < filter_first_minus5_offset
  )

filter_max_loss_before_first_plus10 =
  min(low / filter_entry_price - 1)
  over offsets 0 through filter_first_plus10_offset - 1,
  or offsets 0..120 if plus10 never occurs

filter_max_drawdown_120d =
  max peak-to-trough drawdown using prior-peak-only policy over offsets 0..120
```

Primary label mapping：

```text
censored_or_invalid:
  filter_entry_date missing
  or filter_entry_price invalid
  or filter_path_complete_120d == false

bad_path:
  filter_path_complete_120d == true
  and (
    filter_first_minus5_offset exists
    and (
      filter_first_plus10_offset is null
      or filter_first_minus5_offset <= filter_first_plus10_offset
    )
    or filter_max_loss_before_first_plus10 <= -0.06
    or filter_max_drawdown_120d <= -0.20
  )

good_path:
  filter_path_complete_120d == true
  and filter_hit_plus10_before_minus5 == true
  and filter_max_loss_before_first_plus10 > -0.06
  and filter_max_drawdown_120d > -0.20

neutral_path:
  filter_path_complete_120d == true
  and neither good_path nor bad_path
```

`P_good / P_bad / P_neutral` denominator：

```text
rows where filter_path_label in {good_path, bad_path, neutral_path}
```

`censored_or_invalid` 必须保留在 audit 中，不得进入 `P_good / P_bad` denominator。

### 11.1 Filter Panel 必需字段

`r03e_bad_shape_filter_panel.parquet` 必须至少包含：

```text
family_signal_event_id
event_scope
event_stage
family_id
dedup_weight
t0_entry_date
shape_eval_date
filter_entry_date
filter_entry_price
filter_path_complete_120d
filter_available_forward_trading_days
filter_entry_relative_offset
filter_path_end_relative_offset
filter_first_plus10_offset
filter_first_minus5_offset
filter_same_bar_race_ambiguous_flag
filter_hit_plus10_before_minus5
filter_max_loss_before_first_plus10
filter_max_drawdown_120d
filter_anchor_big_winner_close
filter_anchor_big_winner_next_open
filter_path_label
bad_score_complete_flag
badscore_item_complete_count
bad_score_v1
bad_score_bucket
pass_primary_badshape_filter
drop_primary_badshape_filter
```

## 12. 必需 Summary Tables

### 12.0 Family Group 聚合规则

凡是 summary table 粒度里包含 `family_id`，都必须同时输出两类 `family_group`：

```text
family_group = per_family
  family_id = one of the 7 frozen family ids
  aggregation_weight = 1 for unweighted family_event metrics
  aggregation_weight = dedup_weight for dedup_weighted metrics

family_group = all_families_dedup_weighted
  family_id = ALL
  aggregation_weight = dedup_weight
```

`all_families_dedup_weighted` 是 final decision 的唯一 family aggregation authority。同一 `instrument_id x signal_date x event_scope` 上多个 family row 的 `dedup_weight` 合计必须等于 1；如果不能重算，validator 必须 fail closed。

所有 headline delta、split stability 和 final report 主结论必须从 `family_group = all_families_dedup_weighted, family_id = ALL` 的 row 读取。per-family row 只用于解释和诊断。

### 12.1 Component Definition Audit

输出：`r03e_bad_shape_component_definition_audit.csv`

粒度：

```text
component_id
```

必需字段：

```text
component_id
component_group
lookback_window
formula_text
uses_industry_relative_input
required_ohlcv_fields
future_data_used_flag
config_thresholds
implementation_status
```

`future_data_used_flag` 必须恒为 false。

### 12.2 Bad Shape Component Summary

输出：`r03e_bad_shape_component_summary.csv`

粒度：

```text
split x event_scope x event_stage x family_group x family_id x component_id x component_flag
```

必需指标：

```text
family_event_count
dedup_weight_sum
unique_instrument_count
unique_signal_date_count
signal_anchor_big_winner_rate
signal_anchor_P_good
signal_anchor_P_bad
filter_anchor_big_winner_rate
filter_anchor_P_good
filter_anchor_P_bad
filter_anchor_P_good_minus_P_bad
retention_rate_vs_baseline_1
sample_sufficiency_status
```

用途：判断每个坏形态 component 是否真的对应更高 `P_bad` 或更低 big-winner rate。

### 12.3 Bad Score Bucket Summary

输出：`r03e_bad_score_bucket_summary.csv`

粒度：

```text
split x event_scope x event_stage x family_group x family_id x bad_score_bucket
```

必需指标：

```text
family_event_count
dedup_weight_sum
unique_instrument_count
unique_signal_date_count
bad_score_min
bad_score_max
bad_score_mean
signal_anchor_big_winner_rate
signal_anchor_P_good
signal_anchor_P_bad
filter_anchor_big_winner_rate
filter_anchor_P_good
filter_anchor_P_bad
filter_anchor_P_good_minus_P_bad
sample_sufficiency_status
```

### 12.4 Threshold Tradeoff Summary

输出：`r03e_bad_score_threshold_tradeoff.csv`

粒度：

```text
split x event_scope x event_stage x family_group x family_id x filter_policy
```

`filter_policy` 至少包括：

```text
no_badshape_filter_t10_survivor
drop_score_ge3
drop_score_ge5
drop_score_ge7
drop_component_volume_stall
drop_component_failed_breakout
drop_component_dense_upper_shadow
drop_component_down_volume_dominance
drop_component_ma20_break_no_reclaim
drop_component_large_bearish_engulf
drop_component_volatility_up_no_price
drop_component_low_efficiency
drop_component_lower_low_lower_high
drop_component_gap_up_fade_cluster
```

必需指标：

```text
baseline_1_event_count
policy_evaluable_event_count
policy_null_excluded_count
passed_event_count
dropped_event_count
retention_rate
signal_anchor_big_winner_retained_count
signal_anchor_big_winner_dropped_count
signal_anchor_big_winner_retention_rate
filter_anchor_big_winner_rate
filter_anchor_P_good
filter_anchor_P_bad
filter_anchor_P_good_minus_P_bad
delta_big_winner_rate_vs_t10_survivor
delta_P_good_vs_t10_survivor
delta_P_bad_vs_t10_survivor
delta_P_good_minus_P_bad_vs_t10_survivor
sample_sufficiency_status
```

### 12.5 Filtered Outcome Summary

输出：`r03e_filtered_outcome_summary.csv`

这是 final report 的主表。

粒度：

```text
split x event_scope x event_stage x family_group x family_id x outcome_anchor x filter_policy
```

`outcome_anchor`：

```text
signal_anchor_retention_audit
filter_decision_close_anchor
filter_decision_next_open_anchor
```

必需指标：

```text
event_count
dedup_weight_sum
complete_h120_denominator
big_winner_count
big_winner_rate
path_label_denominator
good_path_count
bad_path_count
neutral_path_count
P_good
P_bad
P_neutral
P_good_minus_P_bad
baseline_event_count
retention_rate
delta_big_winner_rate_vs_parent
delta_P_good_vs_parent
delta_P_bad_vs_parent
delta_P_good_minus_P_bad_vs_parent
sample_sufficiency_status
```

### 12.6 Component Overlap Audit

输出：`r03e_component_overlap_audit.csv`

粒度：

```text
split x event_scope x family_group x family_id x component_a x component_b
```

必需指标：

```text
component_a_count
component_b_count
joint_count
jaccard_overlap
phi_correlation
same_bad_shape_cluster_status
```

用途：防止把高度重复的坏形态当成多个独立证据加分。

### 12.7 Survival And Timing Bias Audit

输出：`r03e_survival_and_timing_bias_audit.csv`

粒度：

```text
split x event_scope x event_stage x family_group x family_id
```

必需指标：

```text
baseline_0_signal_anchor_event_count
baseline_1_t10_survivor_event_count
t10_survivor_rate
missing_shape_eval_date_count
missing_filter_anchor_h120_count
baseline_0_signal_anchor_big_winner_rate
baseline_1_filter_anchor_big_winner_rate
baseline_0_signal_anchor_P_good
baseline_1_filter_anchor_P_good
baseline_0_signal_anchor_P_bad
baseline_1_filter_anchor_P_bad
survival_bias_interpretation
```

final report 必须把该表作为过滤效果解释的前置条件。

### 12.8 Split Stability Audit

输出：`r03e_split_stability_audit.csv`

粒度：

```text
event_scope x event_stage x family_group x family_id x filter_policy x metric
```

必需字段：

```text
train_denominator
validation_denominator
robustness_denominator
train_value
validation_value
robustness_value
validation_delta_vs_parent
robustness_delta_vs_parent
direction_consistent
magnitude_stable
sample_sufficiency_status
stability_status
```

`stability_status`：

```text
stable_descriptive
direction_only
unstable
denominator_thin
split_missing
```

任何 final report 中点名的 filter policy / family / component，必须能在该表中找到对应 row。

## 13. Sample Sufficiency

默认 config：

```yaml
shape_observation_horizon_td: 10
shape_core_pre_entry_td: 10
shape_core_post_entry_td: 10
shape_core_exclude_t0: true
materialized_event_window_start_offset: -252
ordinary_filter_path_end_offset: 131
asof_history_policy: provider_full_history_until_shape_eval
volume_long_window_td: 60
atr20_warmup_min_tr_rows: 20
atr_percentile_window_td: 252
atr_rank252_min_values: 252
atr_rank252_min_ohlcv_rows_ending_at_target: 281
primary_drop_bad_score_gte: 5
threshold_policies: [3, 5, 7]
primary_decision:
  event_scope: r02_signal_episode_start
  event_stage: r02_episode_start
  family_group: all_families_dedup_weighted
  outcome_anchor: filter_decision_next_open_anchor
  filter_policy: drop_score_ge5
  parent_policy: no_badshape_filter_t10_survivor
min_event_count: 80
min_split_denominator: 30
min_unique_instrument_count: 20
min_unique_signal_date_count: 20
min_signal_anchor_big_winner_retention_rate: 0.70
min_material_pbad_reduction_pp: 0.05
min_material_pgood_minus_pbad_lift_pp: 0.05
max_allowed_pgood_drop_pp: 0.02
```

`sample_sufficiency_status`：

```text
sufficient
thin_event_count
thin_split_denominator
thin_unique_instrument
thin_unique_signal_date
incomplete_filter_anchor_path
split_missing
```

## 14. Validation 与 Fail-Closed 条件

validator 必须检查：

1. 所有必需输入存在且 validation passed。
2. 7-family universe 与 R02 precision frozen conditions 完全一致。
3. `r03e_family_signal_event_panel` 至少包含 `r03_seed_family_event`、`r03_clean_fresh_family_event`、`r02_signal_episode_start` 三类 scope。
4. R03 seed event 数能从 R03b seed panel x `seed_family_set` 重算。
5. R03 fresh event 数能从 R03c clean fresh step x `added_family_set` 重算。
6. `condition_group_id` 对 R02 scope 来自 R02 action panel，对 R03 seed/fresh scope 来自 R02 frozen single-family config 的 1:1 family mapping。
7. same-offset multi-family event 没有被赋予任意顺序，且 `dedup_weight` 合计可重算。
8. `shape_core_window_20d` 对每个 complete event 恰好包含 20 根 bar，且不包含 `relative_offset = 0`。
9. 任何 “随后 N 日” component / BadScore item 的 follow-up window 都使用 `core_followup_window_after(d, N)`，且不包含 `relative_offset = 0`。
10. 每个 bad-shape component 的公式只使用 `shape_eval_date` 或之前的数据。
11. `future_data_used_flag == false`。
12. `ret60_asof_t10`、`volume_mean60_asof_*`、`atr20_pct_rank252`、`ma20_asof`、`prior20_high_before` 等 as-of 字段都能按第 10 节公式重算。
13. `atr20_pct_rank252(-10)` 和 `atr20_pct_rank252(+10)` 使用 provider full history 重算，满足 `atr_rank252_min_values` 和 `atr_rank252_min_ohlcv_rows_ending_at_target`；不得只用 `materialized_event_window_start_offset = -252` 的 event window 近似。
14. `BadScore` 的 10 个 item 字段都存在；当且仅当 10 个 item 都非 null 时，`bad_score_complete_flag == true` 且 `bad_score_v1` 等于 item flags 之和。
15. 任一 BadScore item 为 null 时，`bad_score_v1/pass_primary_badshape_filter/drop_primary_badshape_filter` 均为 null，且该 row 不进入 headline denominator。
16. `baseline_1_t10_survivor_no_badshape_filter` 只包含 `bad_score_complete_flag == true` 的 row，且所有 primary headline delta 都以它为 parent。
17. component-only policy 使用 `component_x is not null` 的 policy-evaluable denominator，null component row 不得当作 false。
18. `pass_primary_badshape_filter` 等于 `bad_score_v1 <= 4`，仅适用于 `bad_score_complete_flag == true` 的 row。
19. `filter_entry_relative_offset` 与 `filter_path_end_relative_offset = filter_entry_relative_offset + 120` 可重算；complete filter-anchor row 必须覆盖到该 end offset。
20. 所有包含 `family_id` 的 summary table 都包含 `family_group`，且存在唯一 `family_group = all_families_dedup_weighted, family_id = ALL` 聚合 row。
21. `all_families_dedup_weighted` row 的 `dedup_weight` 聚合可从 event panel 重算，同一 `instrument_id x signal_date x event_scope` 权重合计为 1。
22. `signal_anchor_*` 字段按第 8.1 节 lineage 生成；R02 path-query match 必须唯一。
23. `filter_path_label` 和 filter-anchor big-winner 字段由第 11 节 filter-anchor path recomputation 生成，不能从 signal-anchor 字段复制。
24. `signal_anchor_retention_audit` 与 `filter_decision_*_anchor` outcome 没有混用。
25. `P_good / P_bad` denominator 排除了 `censored_or_invalid`，但 censored rows 保留在 audit。
26. `r03e_filtered_outcome_summary.csv` 必须输出拆分后的 4 个 parent delta 字段，不得只输出单个 `delta_vs_parent`。
27. `final_decision` 只读取第 3.4 节 primary decision grain 的 validation / robustness rows，且该 row 必须唯一。
28. `all` split 没有参与阈值选择或 final decision。
29. final report 点名的 component / filter policy 都存在 split stability row。

若任一硬校验失败，validation status 必须为 failed，decision 必须为：

```text
blocked_validation_failed
```

## 15. Final Report 必答问题

`r03e_family_signal_bad_shape_filter_final_report.md` 必须使用中文，并回答：

1. signal 后 T+10 的坏形态过滤，在 filter-decision-anchor 下是否降低 `P_bad`？
2. primary `drop_score_ge5` 相对 T+10 survivor baseline 的 `P_good / P_bad / big-winner rate` 改善是多少？
3. 被过滤掉的样本里包含多少原始 signal-anchor big winner？误杀是否可接受？
4. 哪些 detailed shape flag 单独最有效？
5. BadScore 分桶是否单调：`0_2` 是否明显好于 `5_6` / `7plus`？
6. 改善是否在 validation 和 robustness 中方向一致？
7. 结果是否只是 T+10 survival / timing bias，而非 bad-shape filter 本身？
8. 该过滤器更适合研究 entry delay、probe hold-state，还是直接停止这条线？

必须包含明确边界：

```text
本实验不证明 T0 入场 edge。
本实验只能说明在 T0 开仓后观察 10 个交易日后，
坏形态状态是否有助于过滤剩余路径较差的样本。
本实验中的 20 日坏形态窗口是排除 T0 的 T-10..T-1 + T+1..T+10，
不是包含 T0 的 21 根 bar。
```

## 16. 决策状态

最终 manifest 必须给出 `final_decision`：

```text
badshape_filter_supported_descriptive
badshape_filter_reduces_bad_path_but_costs_winners
badshape_filter_no_increment_vs_t10_survivor
badshape_filter_unstable_across_splits
insufficient_denominator
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_validation_failed
```

判定规则：

- 下列判定只允许读取第 3.4 节 primary decision grain：

```text
event_scope = r02_signal_episode_start
event_stage = r02_episode_start
family_group = all_families_dedup_weighted
outcome_anchor = filter_decision_next_open_anchor
filter_policy = drop_score_ge5
```

- `badshape_filter_supported_descriptive` 只有在 primary decision grain 的 validation 和 robustness 中同时满足：
  - primary `drop_score_ge5` 的 `P_bad` 相对 T+10 survivor baseline 下降 >= `min_material_pbad_reduction_pp`；
  - `P_good_minus_P_bad` lift >= `min_material_pgood_minus_pbad_lift_pp`；
  - `P_good` 相对 T+10 survivor baseline 的下降不超过 `max_allowed_pgood_drop_pp`；
  - signal-anchor big-winner retention rate >= `min_signal_anchor_big_winner_retention_rate`；
  - denominator sufficient。
- 如果 `P_bad` 下降成立，但 signal-anchor big-winner retention rate 低于阈值，或 `P_good` 下降超过 `max_allowed_pgood_drop_pp`，选择 `badshape_filter_reduces_bad_path_but_costs_winners`。
- 如果相对 T+10 survivor baseline 没有 material lift，选择 `badshape_filter_no_increment_vs_t10_survivor`。
- 如果 validation / robustness 方向不一致，选择 `badshape_filter_unstable_across_splits`。
- 如果 denominator 不足，选择 `insufficient_denominator`。

优先级：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_validation_failed
insufficient_denominator
badshape_filter_unstable_across_splits
badshape_filter_reduces_bad_path_but_costs_winners
badshape_filter_supported_descriptive
badshape_filter_no_increment_vs_t10_survivor
```

即使最终状态为 `badshape_filter_supported_descriptive`，final report 也不得把它升级成 production filter。下一步若继续，只能另开 requirement 做 train-frozen threshold、entry-delay execution 和 transaction-cost-aware validation。
