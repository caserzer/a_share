# EP4 Requirement 02 Follow-up: Family Precision And Forward Return Statistics V1

## 1. Requirement Metadata

- Requirement id: `ep4_r02_family_precision_forward_return_stats_v1`
- Short name: `r02_family_precision_forward_return_stats_v1`
- Status: implementation-ready statistical requirement
- Owner workflow: EP4
- Upstream requirement: `ep4/requirement_02_big_winner_coverage_ratio_search_v1.md`
- Upstream report: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/reports/r02_big_winner_coverage_final_report.md`
- Required output root: `ep4/outputs/r02_family_precision_forward_return_stats_v1/`
- Required config path: `ep4/configs/r02_family_precision_forward_return_stats_v1.yaml`
- Required runner path: `ep4/scripts/run_r02_family_precision_forward_return_stats.py`
- Required validator path: `ep4/scripts/validate_r02_family_precision_forward_return_stats.py`
- Date: 2026-05-13

## 2. Purpose

R02 coverage search 已经找到 7 个在 big winner `reference_date + 0` 到 `reference_date + 30` 窗口内具有高 recall 的技术状态 family。这个结果只说明：

```text
P(signal appears in winner lifecycle | known big winner) is high
```

它还没有回答：

```text
P(future big winner | signal appears on an action-time stock-day) 是否足够高？
signal 出现后 T+1 / T+3 / T+5 / T+10 / T+20 的价格分布是什么？
```

本需求只做冻结条件的统计校准：

1. 在全市场 PIT action-time eligible stock-day 分母上，统计 7 个冻结条件对 future big winner 的 precision。
2. 统计每个冻结条件发生后 `T+1, T+3, T+5, T+10, T+20` 收盘价相对于发生日收盘价的收益分布：最大、最小、平均、中位数。
3. 按 split 输出同一批指标，检查高 recall 条件是否也有稳定 precision 和短期 forward return 结构。
4. 统计 7 个冻结条件之间的信号冗余、相关性和 pairwise 增量信息，判断 precision 接近是否来自同一批底层状态。
5. 在不使用 outcome / precision 的前提下，挑出独立性最强的 4 个 family，并统计这 4 个 family 同日全部满足时的统合 precision。

本需求不是新一轮 search，不允许根据 precision 或 forward return 结果改写 7 个条件。

## 3. Hard Scope

允许：

- 使用 R02 coverage search 已冻结的 7 个最低密度达标 family 条件；
- 在 PIT action-time eligible stock-days 上重放这 7 个条件；
- 统计 stock-day grain 和 episode grain 的 precision；
- 统计触发后固定 horizon 的 close-to-close forward return；
- 输出 split / year / family 分层统计；
- 报告 global 和 feature-matched background prior 与 signal precision 的 lift；
- 输出 family 之间的 signal redundancy / correlation / incremental diagnostic tables；
- 输出 top-4 independent family set 的 deterministic selection audit 和 combined-AND precision。

禁止：

- 重新搜索阈值、窗口或 family 组合；
- 用 validation / robustness precision 反向修改条件；
- 把 7 个 family 组合成新的 production signal、entry rule、ranking score 或 R03 promotion candidate；
- 根据 redundancy / incremental 结果选择、删除、重写或重排 production / R03 candidate 条件；Section 10.4 的 top-4 independent set 只允许作为诊断输出；
- 用 precision、future return、big winner label 或 split 后验结果挑选 top-4 independent family set；
- 把本需求输出直接解释为 entry strategy 或 R03-ready 信号；
- 使用 winner-window 分母估计 precision；
- 用 `reference_date + 0..30` 内的命中日作为 action-time precision 分母；
- 引入新的在线数据抓取。

## 4. Frozen Indicator Set

主统计对象固定为 R02 final report 中“最低密度达标候选”的 7 个 family representative。实现必须从配置中显式冻结以下 condition group，并校验它们可在上游 R02 output 中找到。

| family_id | condition_group_id | frozen condition |
|:--|:--|:--|
| `momentum_rps` | `momentum_rps__and3__68b32373ce93` | `roc5_r02 >= 0.05 AND rps5_r02 >= 0.8 AND rps10_r02 >= 0.5` |
| `oscillator` | `oscillator__and4__95dbd99ae828` | `kdj_k5_r02 >= 60 AND cci5_r02 >= 100 AND kdj_k10_r02 >= 55 AND cci10_r02 >= 150` |
| `price_trend` | `price_trend__and3__6030760ed19f` | `close_over_ma5_r02 >= 0.03 AND ema_slope5_r02 >= 0.0 AND close_over_ma10_r02 >= 0.03` |
| `pullback_drawdown` | `pullback_drawdown__and3__11795aa42e45` | `pullback_depth5_r02 >= -0.05 AND rebound_from_low5_r02 >= 0.05 AND days_since_high10_r02 <= 5` |
| `range_breakout` | `range_breakout__and3__00e51295d9c3` | `range_position5_r02 >= 0.9 AND new_high_flag10_r02 == 1.0 AND range_position10_r02 >= 0.7` |
| `volatility_band` | `volatility_band__and4__ef9c875dde10` | `boll_pct_b5_r02 >= 0.8 AND boll_width5_r02 >= 1.0 AND boll_width10_r02 >= 1.0 AND price_channel_position10_r02 >= 0.8` |
| `volume_money` | `volume_money__and4__4eb7a99e922f` | `volume_ratio5_r02 >= 1.5 AND money_zscore5_r02 >= 2.0 AND money_price_coherence5_r02 == 1.0 AND money_price_coherence10_r02 == 1.0` |

Validator 必须 fail closed：

- 配置中的 condition group 不等于上表 7 个；
- 任一 condition text 与上游 R02 candidate / all results 不一致；
- 任一 condition group 使用了未冻结的新阈值、新窗口或跨 family term；
- 上游 R02 manifest 的 `reference_event_count`、`global_eligible_day_denominator` 或 `parallel_result_hash` 未记录到本次 manifest。

## 5. Required Inputs

主输入必须来自本地已有 PIT 数据和 R02 artifacts：

- R02 eligible-day density panel: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_eligible_day_density_panel.parquet`
- R02 atomic condition dictionary: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/reports/r02_big_winner_coverage_atomic_condition_dictionary.csv`
- R02 candidate dictionary / all results for condition validation
- PIT OHLCV / amount / turnover fields needed to recompute or verify the 7 conditions
- EP4 split calendar and R01 / R02 eligible stock-day conventions
- Local PIT price data sufficient to compute `T+1, T+3, T+5, T+10, T+20, T+120` forward fields

No new online fetch is allowed.

## 6. Signal Occurrence Definition

Primary signal grain:

```text
instrument_id
trade_date
condition_group_id
```

`signal_occurs = true` when all frozen condition terms are true on `trade_date` using only data observable as of that date.

Base action-time row eligibility:

```text
row is in R02 / R01 PIT-executable eligible stock-day denominator
close_t is available and valid
condition-group atomic features can be computed or explicitly marked incomplete
```

The base action-time panel must retain every `(instrument_id, trade_date, condition_group_id)` row that satisfies the denominator and price-validity rules above, whether or not `signal_occurs = true`.

Feature completeness is condition-specific:

```text
feature_complete_flag(condition_group_id, row) =
  every atomic condition in that condition_group_id has complete required lookback

signal_occurs can be true only when feature_complete_flag = true
```

Rows with `feature_complete_flag = false` stay in the base panel, enter feature-coverage audits, and do not enter signal precision or feature-matched background-prior denominators.

Forward-window completeness is metric-specific and must not be part of base row eligibility:

```text
metric_complete(row, horizon) =
  all required forward prices for that horizon exist
  and the horizon remains inside the same split's effective boundary
```

The implementation must keep rows with incomplete forward windows in the cache, but exclude them from the affected metric denominator and report the excluded count by horizon and reason.

### 6.1 Episode View

Because some conditions may fire on many consecutive days, the report must include an episode-collapsed view in addition to raw stock-day precision.

Default episode rule:

```text
For each instrument_id, condition_group_id:
  consecutive signal stock-days belong to the same signal_episode_id;
  if the next signal occurs within 5 trading days after the previous episode end,
  merge it into the same episode.
episode_signal_date = first trade_date in the episode
```

The primary precision table is stock-day grain. Episode precision is required as a de-duplication audit and must not replace the stock-day table.

Episode-grain precision and forward-return statistics must use only the episode start anchor:

```text
episode_occurrence_price_t = close(instrument_id, episode_signal_date)
episode_entry_price_t = next_open_after(episode_signal_date)
```

Rows after `episode_signal_date` inside the same episode may be used only to describe episode length and repeated-trigger behavior. They must not be re-aggregated into episode-grain precision or episode-grain forward-return statistics.

## 7. Big Winner Precision

Precision must be estimated from full action-time eligible signal occurrences, not from known winner windows.

### 7.1 Primary Close-Anchored Precision

Primary precision answers the user's direct question against occurrence-day price:

```text
occurrence_price_t = close(instrument_id, trade_date)
forward_close_peak_h120 =
  max(close over trade_date + 1 through trade_date + 120 trading days)

big_winner_forward_from_signal_close =
  forward_close_peak_h120 / occurrence_price_t - 1 >= 0.50

precision_stock_day_h120 =
  count(signal stock-days with big_winner_forward_from_signal_close = true)
  / count(signal stock-days with complete h120 forward window)
```

Important execution boundary:

```text
close-anchor precision is a post-close observable statistical metric
```

Many frozen conditions use same-day close-derived fields. Therefore the close-anchor metric must not be described as an intraday executable entry or same-day buyable win rate. It answers whether a state visible after the close is associated with future right-tail continuation. The next-open anchor in Section 7.2 is the audit view for executable timing.

The same formula must be reported by:

- `split`
- `year`
- `family_id`
- `condition_group_id`
- `market_state_bucket` if the existing local market-state field is available

### 7.2 Compatibility Precision

For continuity with existing EP4 / R02 labels, also report a compatibility label:

```text
entry_price_t = next_open_after(trade_date)
big_winner_forward_from_next_open =
  max(close over next 120 trading days after entry) / entry_price_t - 1 >= 0.50
```

This compatibility precision is audit-only. The final report must make clear whether headline precision uses close anchor or next-open anchor.

### 7.3 Background Prior And Lift

For every split and globally, compute background priors on matched eligible denominators.

```text
background_big_winner_prior_global_h120 =
  count(eligible stock-days with complete h120 forward window
        and big_winner_forward_from_signal_close = true)
  / count(eligible stock-days with complete h120 forward window)

background_big_winner_prior_feature_matched_h120(condition_group_id) =
  count(base action-time rows for this condition_group_id
        where signal_occurs is either true or false
        and feature_complete_flag = true
        and complete_h120_flag = true
        and big_winner_forward_from_signal_close = true)
  / count(base action-time rows for this condition_group_id
          where signal_occurs is either true or false
          and feature_complete_flag = true
          and complete_h120_flag = true)

precision_lift =
  precision_stock_day_h120
  / background_big_winner_prior_feature_matched_h120(condition_group_id)
```

The headline lift must use the feature-matched background prior. The global prior is required as a reference only. This prevents a condition with narrower feature availability from being compared against a different denominator.

Required precision fields:

- `condition_group_id`
- `family_id`
- `grain`: `stock_day` or `episode`
- `split`
- `signal_count`
- `complete_h120_count`
- `positive_h120_count`
- `precision_h120_close_anchor`
- `background_prior_global_h120_close_anchor`
- `background_prior_feature_matched_h120_close_anchor`
- `precision_lift_feature_matched_h120_close_anchor`
- `precision_h120_next_open_anchor`
- `incomplete_h120_count`
- `feature_complete_ratio`
- `positive_h120_count_min_gate_pass`
- `bootstrap_precision_lift_ci90_lower`
- `bootstrap_precision_lift_ci90_upper`

### 7.4 Bootstrap Lift Confidence Interval

Because `bootstrap_precision_lift_ci90_lower` is a decision-gate field, the bootstrap method is fixed:

```yaml
bootstrap:
  enabled: true
  metric: precision_lift_feature_matched_h120_close_anchor
  confidence_level: 0.90
  iterations: 1000
  random_seed: 20260513
  resample_unit: instrument_year
  resample_scope: split_condition_group
  replacement: true
  percentile_method: nearest_rank
```

Definitions:

```text
instrument_year = instrument_id + calendar year of trade_date

For each split and condition_group_id:
  build bootstrap samples by resampling instrument_year blocks with replacement;
  include all action-time rows inside each sampled instrument_year block;
  recompute signal precision, feature-matched background prior, and precision lift;
  ci90_lower = 5th percentile of bootstrap precision lift samples;
  ci90_upper = 95th percentile of bootstrap precision lift samples.
```

Bootstrap must run separately for stock-day grain and episode grain. Decision gates use the CI from `decision_grain`. The manifest must record `bootstrap_iterations`, `bootstrap_random_seed`, `bootstrap_resample_unit`, `bootstrap_confidence_level`, and `bootstrap_sample_count_by_split_condition`.

Validator must fail closed if:

- bootstrap uses row-level stock-day resampling instead of `instrument_year` block resampling;
- bootstrap mixes train / validation / robustness rows in one resample pool;
- bootstrap omits `signal_occurs = false` feature-matched background rows;
- bootstrap output is missing for any split / condition_group_id used in decision gates.

## 8. Forward Return Statistics

For each signal occurrence and each horizon:

```text
horizon in [1, 3, 5, 10, 20]
return_close_t_plus_h =
  close(instrument_id, trade_date + h trading days) / close(instrument_id, trade_date) - 1
```

The required aggregate statistics are:

```text
max_return = max(return_close_t_plus_h)
min_return = min(return_close_t_plus_h)
mean_return = mean(return_close_t_plus_h)
median_return = median(return_close_t_plus_h)
```

These are endpoint returns at exactly `T+h`, not max/min path returns inside the interval.

To avoid hiding path risk, the implementation must also report diagnostic intra-horizon extremes:

```text
path_max_return_to_h =
  max(close from T+1 through T+h) / close_t - 1

path_min_return_to_h =
  min(close from T+1 through T+h) / close_t - 1
```

Required forward-return fields:

- `condition_group_id`
- `family_id`
- `grain`: `stock_day` or `episode`
- `split`
- `horizon`
- `signal_count`
- `complete_horizon_count`
- `incomplete_horizon_count`
- `endpoint_return_max`
- `endpoint_return_min`
- `endpoint_return_mean`
- `endpoint_return_median`
- `endpoint_return_p25`
- `endpoint_return_p75`
- `endpoint_return_positive_rate`
- `path_max_return_mean`
- `path_max_return_median`
- `path_min_return_mean`
- `path_min_return_median`

The final report's headline table must include at least the user-requested four endpoint statistics: maximum, minimum, average, and median.

## 9. Required Artifacts

### 9.1 Manifest

`manifests/r02_family_precision_forward_return_stats_manifest.json`

Required fields:

- `phase`
- `generated_at`
- `requirement_path`
- `config_path`
- `config_hash`
- `output_root`
- `upstream_r02_manifest_path`
- `upstream_r02_manifest_hash`
- `upstream_parallel_result_hash`
- `frozen_condition_group_count`
- `eligible_stock_day_count`
- `signal_stock_day_count_by_condition`
- `episode_count_by_condition`
- `base_action_time_row_count_by_condition`
- `feature_matched_background_row_count_by_condition`
- `split_policy`
- `price_anchor_policy`
- `horizons`
- `forward_label_horizon`
- `decision_grain`
- `decision_min_lift_validation`
- `decision_min_lift_robustness`
- `decision_min_positive_h120_count`
- `decision_min_signal_count`
- `bootstrap_iterations`
- `bootstrap_random_seed`
- `bootstrap_resample_unit`
- `bootstrap_confidence_level`
- `bootstrap_sample_count_by_split_condition`
- `top4_independence_selection_rule`
- `top4_independent_family_set`
- `top4_independence_score`
- `top4_combined_signal_count`
- `final_decision`

### 9.2 Action-Time Occurrence Panel

`cache/r02_family_action_time_panel.parquet`

Grain: `instrument_id, trade_date, condition_group_id`

This panel must include both `signal_occurs = true` and `signal_occurs = false` rows for every frozen condition group. It is the authority for signal precision, feature-matched background prior, missingness, and split-boundary audits.

Episode-field null policy:

```text
if signal_occurs = false:
  signal_episode_id = null
  is_episode_start = false
  episode_signal_date = null
  episode_occurrence_price_t = null
  episode_entry_price_t = null
  episode_length_trading_days = null
  episode_trigger_day_count = 0

if signal_occurs = true and row is inside an episode:
  signal_episode_id must be non-null
  episode_signal_date must equal the first signal date of that episode
  is_episode_start is true only on episode_signal_date
  episode_occurrence_price_t and episode_entry_price_t are populated from episode_signal_date
  only is_episode_start = true rows enter episode-grain metrics
```

Required fields:

- `instrument_id`
- `trade_date`
- `split`
- `year`
- `condition_group_id`
- `family_id`
- `base_action_time_eligible_flag`
- `signal_occurs`
- `feature_complete_flag`
- `close_t`
- `next_open_t1`
- `signal_episode_id`
- `is_episode_start`
- `episode_signal_date`
- `episode_occurrence_price_t`
- `episode_entry_price_t`
- `episode_length_trading_days`
- `episode_trigger_day_count`
- `same_day_family_count`
- `complete_h1_flag`
- `complete_h3_flag`
- `complete_h5_flag`
- `complete_h10_flag`
- `complete_h20_flag`
- `complete_h120_flag`
- `return_close_t1`
- `return_close_t3`
- `return_close_t5`
- `return_close_t10`
- `return_close_t20`
- `path_max_return_to_1`
- `path_min_return_to_1`
- `path_max_return_to_3`
- `path_min_return_to_3`
- `path_max_return_to_5`
- `path_min_return_to_5`
- `path_max_return_to_10`
- `path_min_return_to_10`
- `path_max_return_to_20`
- `path_min_return_to_20`
- `forward_close_peak_h120_return_from_close`
- `big_winner_forward_from_signal_close`
- `forward_close_peak_h120_return_from_next_open`
- `big_winner_forward_from_next_open`
- `incomplete_forward_reason`

### 9.3 Background Prior Panel

`cache/r02_family_background_prior_panel.parquet`

Grain: `instrument_id, trade_date, condition_group_id, background_denominator_role`

Required fields:

- `instrument_id`
- `trade_date`
- `split`
- `year`
- `condition_group_id`
- `family_id`
- `base_action_time_eligible_flag`
- `feature_complete_flag`
- `signal_occurs`
- `complete_h120_flag`
- `close_t`
- `forward_close_peak_h120_return_from_close`
- `big_winner_forward_from_signal_close`
- `background_denominator_role`: `global` or `feature_matched`

The background prior panel may physically reuse the action-time occurrence panel, but the manifest must record the exact source path and hash used for global and feature-matched prior calculations.

### 9.4 Summary Tables

Required CSV outputs:

- `reports/r02_family_precision_summary.csv`
- `reports/r02_family_precision_by_split.csv`
- `reports/r02_family_precision_by_year.csv`
- `reports/r02_family_forward_return_stats.csv`
- `reports/r02_family_forward_return_stats_by_split.csv`
- `reports/r02_family_episode_precision_summary.csv`
- `reports/r02_family_episode_forward_return_stats.csv`
- `reports/r02_family_signal_overlap_matrix.csv`
- `reports/r02_family_signal_redundancy_long.csv`
- `reports/r02_family_signal_phi_correlation_matrix.csv`
- `reports/r02_family_signal_jaccard_matrix.csv`
- `reports/r02_family_signal_incremental_precision.csv`
- `reports/r02_family_top4_independence_selection_audit.csv`
- `reports/r02_family_top4_combined_precision.csv`
- `reports/r02_family_missingness_audit.csv`
- `reports/r02_family_background_prior_audit.csv`
- `reports/r02_family_decision_gate_audit.csv`
- `reports/r02_family_precision_forward_return_final_report.md`

## 10. Signal Redundancy And Incremental Information

Because several family conditions may describe similar underlying market states, the implementation must report signal redundancy and incremental information on the same action-time denominator used by the precision analysis.

### 10.1 Family Signal Matrix

Build a family-level binary signal matrix:

```text
row grain = instrument_id, trade_date
columns = family_id
value = 1 if any frozen condition_group_id in that family has signal_occurs = true on that stock-day, else 0
```

In this requirement there is exactly one frozen condition group per family, but the matrix must still use `family_id` as the public column name so the report remains readable.

Pairwise metrics must use a feature-complete pair denominator:

```text
pair_denominator(a, b) =
  stock-days where base_action_time_eligible_flag = true
  and feature_complete_flag(a) = true
  and feature_complete_flag(b) = true
```

Rows where either side is feature-incomplete must be excluded from that pair's correlation denominator and counted in a pairwise missingness audit.

### 10.2 Redundancy Metrics

The implementation must report the existing directional overlap matrix:

```text
P(condition_b occurs | condition_a occurs)
joint_signal_count(condition_a, condition_b)
joint_precision_h120(condition_a, condition_b)
```

In addition, it must report two symmetric redundancy matrices:

```text
phi_correlation(a, b) =
  Pearson correlation between binary signal_occurs(a) and signal_occurs(b)
  over pair_denominator(a, b)

jaccard_overlap(a, b) =
  joint_signal_count(a, b) / union_signal_count(a, b)
```

Required fields for the long-form source table behind these matrices:

- `family_a`
- `family_b`
- `pair_denominator_count`
- `pair_feature_incomplete_count`
- `signal_count_a`
- `signal_count_b`
- `joint_signal_count`
- `union_signal_count`
- `p_b_given_a`
- `p_a_given_b`
- `phi_correlation`
- `jaccard_overlap`
- `joint_precision_h120_close_anchor`
- `joint_complete_h120_count`
- `joint_positive_h120_count`
- `phi_null_reason`

If either family has zero variance on the pair denominator, `phi_correlation` must be null and `phi_null_reason` must be populated.

### 10.3 Incremental Precision Diagnostics

To answer whether one family adds information beyond another, the implementation must compute ordered pairwise incremental precision diagnostics. For every ordered pair `(base_family, added_family)`:

```text
base = base_family occurs
added = added_family occurs
base_and_added = base_family occurs AND added_family occurs
base_only = base_family occurs AND added_family does not occur
added_only = added_family occurs AND base_family does not occur
```

All precision fields must use the same close-anchor h120 label and complete-h120 denominator as Section 7.1.

Required fields:

- `base_family`
- `added_family`
- `pair_denominator_count`
- `base_signal_count`
- `added_signal_count`
- `base_and_added_signal_count`
- `base_only_signal_count`
- `added_only_signal_count`
- `base_precision_h120_close_anchor`
- `base_and_added_precision_h120_close_anchor`
- `base_only_precision_h120_close_anchor`
- `added_only_precision_h120_close_anchor`
- `delta_precision_base_and_added_minus_base`
- `lift_base_and_added_vs_base`
- `signal_retention_base_and_added_vs_base`
- `positive_h120_count_base_and_added`
- `complete_h120_count_base_and_added`

Interpretation rules:

- High `phi_correlation` or high `jaccard_overlap` means two families are likely redundant as state descriptors.
- High `p_b_given_a` with much lower `p_a_given_b` means `b` is often contained inside `a` or vice versa, depending on direction.
- Positive `delta_precision_base_and_added_minus_base` with acceptable `signal_retention_base_and_added_vs_base` is evidence that `added_family` may provide incremental confirmation.
- A large precision increase with very low retained sample count must be described as fragile, not as a stronger signal.

These pairwise AND / only / overlap calculations are diagnostic only. They are explicitly not new frozen conditions, not entry strategies, and not R03 promotion candidates.

### 10.4 Top-4 Independent Combined Precision

To test whether relatively independent family states produce a cleaner signal when all are present, the implementation must select one deterministic top-4 independent family set and compute its combined-AND precision.

The selection universe is fixed:

```text
all 4-family combinations from the 7 frozen family_id values
combination_count = C(7, 4) = 35
```

The selection must use only redundancy metrics from Section 10.2. It must not use precision, forward returns, big winner labels, split-level outcome stability, or any future outcome field.

For each 4-family combination:

```text
combo_pair_count = 6
combo_mean_abs_phi = mean(abs(phi_correlation) across 6 pairs)
combo_max_abs_phi = max(abs(phi_correlation) across 6 pairs)
combo_mean_jaccard = mean(jaccard_overlap across 6 pairs)
combo_max_jaccard = max(jaccard_overlap across 6 pairs)
```

Default deterministic ranking:

```text
sort by:
  combo_mean_abs_phi ascending
  combo_max_abs_phi ascending
  combo_mean_jaccard ascending
  combo_max_jaccard ascending
  sorted_family_id_tuple ascending
```

The first row is `top4_independent_family_set`.

After the top-4 set is selected, compute combined precision:

```text
top4_common_denominator =
  stock-days where base_action_time_eligible_flag = true
  and feature_complete_flag = true for all 4 selected families

top4_combined_signal_occurs =
  all 4 selected families have signal_occurs = true on the same instrument_id, trade_date

top4_combined_precision_h120_close_anchor =
  count(top4_combined_signal_occurs stock-days with complete_h120_flag = true
        and big_winner_forward_from_signal_close = true)
  / count(top4_combined_signal_occurs stock-days with complete_h120_flag = true)
```

The combined-AND precision must also report:

- `selected_family_set`
- `selection_rank`
- `combo_mean_abs_phi`
- `combo_max_abs_phi`
- `combo_mean_jaccard`
- `combo_max_jaccard`
- `top4_common_denominator_count`
- `top4_combined_signal_count`
- `top4_combined_complete_h120_count`
- `top4_combined_positive_h120_count`
- `top4_combined_precision_h120_close_anchor`
- `top4_background_prior_common_denominator_h120_close_anchor`
- `top4_precision_lift_vs_common_denominator`
- `top4_precision_h120_next_open_anchor`
- `top4_signal_retention_vs_min_single_family`
- `top4_signal_retention_vs_max_single_family`
- `sample_sufficiency_status`

The same combined precision table must be reported globally and by split.

Sample sufficiency rules:

```text
if top4_combined_complete_h120_count < 200 or top4_combined_positive_h120_count < 10:
  sample_sufficiency_status = fragile_low_sample
else:
  sample_sufficiency_status = sufficient_for_diagnostic
```

Interpretation boundary:

```text
top4_combined_precision is a diagnostic stress test of independent-state confluence.
It is not a new production condition, not a strategy entry rule, and not an R03 promotion candidate.
```

If one instrument has multiple different family signals on the same trade date, each `condition_group_id` keeps its own row. A separate `same_day_family_count` field must be reported in the occurrence panel for diagnostics.

## 11. Split Boundary And Leakage Rules

All metrics must be split-bounded:

- A row may enter `T+20` return statistics only if `trade_date + 20 trading days` remains inside the same split's effective price boundary.
- A row may enter h120 precision only if the complete h120 forward close path exists inside the allowed label boundary.
- Rows near the end of a split are retained in cache with incomplete flags but excluded from affected metric denominators.
- No row may use future data to decide whether the signal occurs.

Validator must fail closed if:

- `signal_occurs` uses any forward return, future label, winner id, or reference-date field;
- endpoint return uses a non-trading-day calendar offset instead of trading-day offset;
- h120 precision denominator includes incomplete h120 rows;
- split boundary crossing rows enter headline precision;
- episode view changes stock-day headline metrics;
- non-signal rows contain non-null episode anchor fields;
- signal rows with `is_episode_start = true` have null episode anchor fields;
- episode-grain metrics include rows where `is_episode_start != true`;
- feature-matched background prior excludes `signal_occurs = false` rows;
- headline lift uses the global background prior instead of the feature-matched background prior;
- close-anchor precision is described as same-day executable;
- redundancy / incremental diagnostics use winner-window rows instead of action-time rows;
- pairwise correlation denominators include rows where either family's feature_complete_flag is false;
- pairwise incremental precision uses a different h120 label or split-boundary rule from Section 7.1;
- top-4 independent family selection uses precision, future return, big winner label, or split outcome stability;
- top-4 combined precision uses a different h120 label, price anchor, feature-complete denominator, or split-boundary rule from Section 7.1;
- final report treats pairwise AND / only diagnostics or top-4 combined-AND diagnostics as new candidate production signals.

## 12. Final Report Requirements

The final report must answer these questions in Chinese:

1. 7 个高 recall family 在 action-time 分母上的 precision 是否明显高于 feature-matched 背景 prior？
2. precision 是否在 train / validation / robustness 三个 split 中稳定？
3. 每个 family 触发后 `T+1, T+3, T+5, T+10, T+20` 的 endpoint return 最大、最小、平均、中位数是什么？
4. 哪些 family 的短期 forward return 是立即延续，哪些更像滞后确认？
5. stock-day precision 与 episode precision 是否差异很大，是否存在重复触发导致的假象？
6. 哪些 family 在 action-time stock-day 上高度冗余，precision 接近是否可能来自同一批底层状态？
7. 在 pairwise 诊断中，是否存在某个 added family 在保留足够样本的前提下提升 base family precision？
8. 按不看 outcome 的独立性排序，前 4 个最独立 family 同日全部满足时的统合 precision 是否明显改善，样本是否足够？
9. 这 7 个条件是否值得进入下一阶段 evidence accumulation，还是只能保留为 descriptive lifecycle tags？

The report must include at least:

- headline precision table by family;
- precision by split table;
- forward return horizon table by family;
- episode de-dup audit table;
- overlap warning table;
- signal redundancy matrix summary;
- incremental precision diagnostic table;
- top-4 independent family selection audit and combined precision table;
- missingness / incomplete-window audit;
- background-prior denominator audit;
- conservative conclusion.

## 13. Final Decision Enum

The implementation must emit exactly one final decision:

| decision | meaning |
|:--|:--|
| `statistical_calibration_positive` | 至少 3 个 family 在 validation 和 robustness 上都满足决策门槛，且 T+20 median return 为正 |
| `mixed_precision_keep_as_lifecycle_tags` | 部分 family 有 lift，但 split 稳定性或 forward return 不足，暂不进入 evidence accumulation |
| `precision_not_supported` | 大多数 family precision 接近背景 prior，说明高 recall 只是 winner lifecycle 描述 |
| `invalid_run` | 输入、冻结条件、split、missingness 或 leakage audit 失败 |

Decision gates are evaluated on stock-day grain unless config explicitly sets `decision_grain = episode`. If `decision_grain = episode`, the final report must still show stock-day results as the headline descriptive table and explain the grain change.

For a family to count toward `statistical_calibration_positive`, all of the following must hold on both validation and robustness:

```text
signal_count >= 500
complete_h120_count >= 500
positive_h120_count >= 20
precision_lift_feature_matched_h120_close_anchor >= 1.50
bootstrap_precision_lift_ci90_lower > 1.00
endpoint_return_median at T+20 > 0
```

If fewer than 3 families pass all gates, the decision cannot be `statistical_calibration_positive`.

本需求不设置 R03 promotion gate。即使 final decision 为 `statistical_calibration_positive`，也只能说明这些 family 值得作为下一阶段 evidence candidate；不能直接生成交易策略。
