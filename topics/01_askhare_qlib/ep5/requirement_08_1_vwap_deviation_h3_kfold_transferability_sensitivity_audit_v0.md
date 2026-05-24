# EP5 Requirement 08.1: VWAP Deviation H3 K-Fold Transferability Sensitivity Audit V0

## 1. Requirement Metadata

requirement_id: `ep5_r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0`

short_name: `r08_1_vwap_h3_kfold_transferability_sensitivity_audit_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-24`

primary_output_namespace: `ep5/outputs/r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0/`

upstream_requirement:

- `ep5/requirement_08_h3_volume_price_single_stock_state_transferability_audit_v0.md`

upstream_report:

- `ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/reports/r08_final_report.md`

upstream_final_decision:

```text
r08_blocked_data_or_execution_contract
```

upstream_key_evidence:

```text
R08 latest run:
  train_direction_valid_instrument_count_min = 80
  direction no longer blocked
  retained factors:
    volume_price_correlation = 3 / 3
    volume_surge_money_flow  = 14 / 15
    vwap_deviation           = 6 / 6

R08 final blocker:
  segment-level seen / unseen instrument sample too thin
  selected rule = rule_02b
  sample_blocked_family_count = 3 / 3
  authorized_r09_flag = False
```

R08.1 继承 EP5 的本地 PIT mcap500 mainboard universe、weekly close-observed signal、next-open execution、H3 label、110bps round-trip cost、split-purity 规则和 no-online-data 边界。

R08.1 不继承 R08 的 downstream authorization 语义。R08 明确没有授权 R09 strategy；因此 R08.1 只能是 sensitivity diagnostic，不是 strategy requirement。

## 2. Research Positioning

R08.1 是一个 **transferability sensitivity audit**。

R08.1 只回答：

```text
R08 的 blocked 是否主要由单次 60/20/20 instrument split 下
unseen segment 过薄造成？

如果把 instrument transfer 改成 5-fold out-of-fold 评价，
vwap_deviation H3 的单股内状态收益关系是否仍然存在，
且是否在 fold-level 上足够稳定？
```

R08.1 不回答：

```text
vwap_deviation 是否可以交易？
是否可以写 production signal？
是否可以构造 long-only / hedged strategy？
```

R08.1 即使得到 positive result，也只能允许后续写：

```text
confirmatory transferability diagnostic requirement
```

不得直接授权：

```text
R09 strategy requirement
```

## 3. Upstream Motivation

R08 的最新结果有明确的信息增量：

```text
direction 阶段不再阻断；
三个 family 都能形成 family state score；
spread、monotonicity、concentration 都有可读数值；
但最终仍被 sample gate 阻断。
```

R08 的核心样本瓶颈集中在 unseen instrument segment：

| family | validation unseen valid instruments | robustness unseen valid instruments |
|:--|--:|--:|
| volume_price_correlation | 33 | 37 |
| volume_surge_money_flow | 24 | 34 |
| vwap_deviation | 22 | 35 |

而 R08 的 sample gate 要求：

```text
valid_instrument_count >= 100
```

因此 R08 不能诚实判断：

```text
single-stock state relation 是否能跨股票迁移。
```

在三类 family 中，`vwap_deviation` 是最强候选：

```text
validation all-instrument spread  = +0.2691%
robustness all-instrument spread  = +0.2606%
validation unseen spread          = +0.1698%
robustness unseen spread          = +0.2398%

all-instrument monotonicity:
  train       = 0.9273
  validation  = 0.6970
  robustness  = 0.9152
```

但 R08 也显示 `vwap_deviation` 不能授权：

```text
validation unseen valid instruments = 22
robustness unseen valid instruments = 35
validation unseen positive instrument share = 40.91%
validation unseen monotonicity = 0.3576
unseen concentration fail
```

所以 R08.1 的动机不是“救回策略”，而是做一个更合适的 instrument-transfer sensitivity diagnostic：

```text
把单次 unseen 20% segment 改成 5-fold out-of-fold unseen 汇总；
同时保留 fold-level dispersion，
判断 vwap_deviation 的状态关系是稳定迁移迹象，
还是薄样本偶然读数。
```

## 4. Core Question

R08.1 只回答一个核心问题：

```text
在固定 H3、固定 vwap_deviation family、固定 within-stock 252d percentile、
固定 H3 self-relative label、固定 train-only direction / bucket edge 的边界下，

vwap_deviation 的单股内状态收益关系，
是否能在 5-fold instrument out-of-fold unseen evaluation 中
跨股票、跨年份稳定存在？
```

关键词：

```text
vwap_deviation only
H3 only
single-stock state
k-fold instrument transfer
out-of-fold unseen evaluation
fold-level stability
diagnostic-only
no strategy authorization
```

## 5. Non-Goals and Explicit Prohibitions

R08.1 必须禁止：

1. 构造交易策略。
2. 输出 long-only alpha pass。
3. 输出 hedged alpha pass。
4. 输出 production signal。
5. 输出 top-N、top20%、top-decile 或任意横截面选股 basket。
6. 使用横截面 rank 作为 primary score。
7. 根据 validation 选择股票。
8. 根据 validation 选择 fold。
9. 根据 validation 选择 factor。
10. 根据 validation 选择 direction。
11. 根据 validation 选择 state threshold。
12. 根据 validation 选择 horizon。
13. 根据 fold 表现丢弃坏 fold。
14. 给每只股票单独调 factor、阈值或 horizon。
15. 引入 `vwap_deviation` 以外的新 primary family。
16. 引入 H1、H5、H10、H20 或任意非 H3 primary horizon。
17. 引入 LGBM、neural network、optimizer、PCA、autoencoder 或组合优化器。
18. 使用 right-tail、big-winner、hit-rate 或单笔极端收益救回结论。
19. 使用 online data。
20. 触发 backtest、paper trading 或 production pipeline。

一句话：

```text
R08.1 不是 vwap_deviation 策略启动；
R08.1 只是检验 R08 的 unseen sample blocker 是否由 split 设计造成。
```

## 6. Canonical Scope

Primary family:

```text
vwap_deviation
```

Primary horizon:

```text
H3
```

Primary state:

```text
within-stock 252d percentile
```

Primary label:

```text
H3 self-relative net return
```

Audit-only comparator:

```text
volume_price_correlation
```

Comparator usage:

```text
volume_price_correlation 只用于连接 R07/R08 evidence chain；
不得参与 final supported decision；
不得因为 comparator 表现更好而替代 vwap_deviation 成为 primary family。
```

Excluded from R08.1:

```text
volume_surge_money_flow
```

Exclusion reason:

```text
R08 中 volume_surge_money_flow validation / robustness all-instrument spread 为负，
unseen spread 不稳，
robustness monotonicity 为负，
更接近 stock-specific behavior only。
```

## 7. Data and Execution Contract

R08.1 继承 R08 的数据和执行边界：

- local PIT Qlib provider；
- PIT mcap500 mainboard universe；
- PIT industry membership；
- trading calendar；
- R06/R08 frozen Alpha191 factor registry and family map；
- weekly close-observed signal；
- next-open entry；
- H3 natural exit；
- round-trip cost = 110bps；
- no-online-data boundary。

Time split 固定：

```text
train:
  2017-07-04 through 2021-12-31

validation:
  2022-01-01 through 2023-12-31

robustness:
  2024-01-01 through 2025-12-31
```

Signal and execution:

```text
signal date D:
  weekly close-observed signal date

entry:
  first executable next open after D

exit:
  open after H3 trading days

label:
  net of 110bps round-trip cost
```

R08.1 不得重新定义 execution timing。

Data availability audit:

```text
declared_robustness_end_date = 2025-12-31
last_available_trading_date = max trading date available in local PIT provider
last_h3_label_complete_signal_date = latest signal date whose H3 exit is observable

robustness_window_actual_end_date
  = min(
      declared_robustness_end_date,
      last_available_trading_date,
      last_h3_label_complete_signal_date
    )

robustness_end_date_data_available
  = robustness_window_actual_end_date >= declared_robustness_end_date
```

If local data ends before the declared robustness end, R08.1 must use the actual end date and report:

```text
robustness_window_truncated_by_data_availability = true
robustness_actual_evaluable_year_count
robustness_actual_signal_date_count
```

Year-count gates must use actual evaluable years, not declared calendar years.

## 8. K-Fold Instrument Transfer Design

R08.1 替代 R08 的单次 60/20/20 instrument segment 评价，改为 deterministic 5-fold instrument transfer。

Fold assignment:

```text
instrument_fold_id
  = canonical sha256 instrument hash mod 5
```

Canonical hash input:

```text
canonical_instrument_id:
  repo-native instrument id used in the PIT panel, for example SH600000
  not vendor-reformatted symbols such as 600000.SH

hash_input:
  utf-8 bytes of canonical_instrument_id.lower()

hash_value:
  int.from_bytes(sha256(hash_input).digest()[:8], "big")

instrument_fold_id:
  hash_value mod 5
```

The implementation must persist `canonical_instrument_id`, `hash_value`, and `instrument_fold_id` in the fold assignment audit.

Fold ids:

```text
fold_id in {0, 1, 2, 3, 4}
```

For each fold `k`:

```text
unseen_fold(k):
  instruments where instrument_fold_id == k

seen_folds(k):
  instruments where instrument_fold_id != k
```

R08.1 必须跑完 5 个 fold。不得根据 fold 表现跳过、合并、删除或重排 fold。

每个 fold 的 training / evaluation contract：

```text
direction input:
  train years only
  seen_folds(k) only

state bucket edge input:
  train years only
  seen_folds(k) only

primary evaluation:
  unseen_fold(k)
  validation years
  robustness years

train baseline:
  unseen_fold(k)
  train years
  using direction / bucket edge frozen from seen_folds(k)
```

这使得 train / validation / robustness 的 primary readout 都是 out-of-fold unseen readout：

```text
train_oof_unseen
validation_oof_unseen
robustness_oof_unseen
```

## 9. Factor Direction and Family State Score

R08.1 只对 `vwap_deviation` primary family 冻结 direction。

For each fold `k` and factor `f`:

```text
instrument_factor_rankic_f,i,k
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )
```

Direction input:

```text
split = train
instrument scope = seen_folds(k)
```

Valid instrument condition for direction:

```text
train_signal_count_for_instrument_factor >= 80
factor_nonconstant_observation_share >= 0.80
```

Direction statistic:

```text
factor_direction_stat_f,k
  = median_over_valid_seen_train_instruments(
      instrument_factor_rankic_f,i,k
    )
```

Direction:

```text
direction_f,k = +1 if factor_direction_stat_f,k >= 0
direction_f,k = -1 if factor_direction_stat_f,k < 0
```

Direction sample gate:

```text
fold_direction_valid_instrument_count_f,k >= 80
```

Factor with insufficient direction sample:

```text
direction_status = factor_direction_sample_insufficient
```

Direction-insufficient factors are dropped before state-score construction:

```text
if direction_status == factor_direction_sample_insufficient:
  remove factor f from retained_vwap_factor_set_k
  exclude factor f from retained_factor_count_k
  exclude factor f from vwap_state_score_i,k(D)
```

Family retained factor condition:

```text
retained_factor_count_k >= 5
```

Rationale:

```text
R08 retained 6 / 6 vwap_deviation factors after lowering direction threshold to 80.
R08.1 allows one factor to fail direction sample,
but a fold with fewer than 5 retained vwap factors is not decision-bearing.
```

Directional percentile:

```text
factor_oriented_percentile_f,i,k(D)
  = 0.5 + direction_f,k * (factor_ts_percentile_f,i(D) - 0.5)
```

Family state score:

```text
vwap_state_score_i,k(D)
  = mean_over_retained_vwap_factors(
      factor_oriented_percentile_f,i,k(D)
    )
```

No validation / robustness data may affect direction or retained-factor choice.

## 10. Within-Stock Normalization

R08.1 uses the same primary normalization as R08:

```text
factor_ts_percentile_f,i(D)
  = mid-rank percentile of current factor value
    against the stock's prior 252 trading days
```

Lookback constraints:

```text
within_stock_lookback_trading_days = 252
within_stock_min_history_count = 126
lookback_window_end = D - 1 trading day
```

The current factor value at signal date `D` may use close-observed information at `D` because execution starts at next open, but the percentile reference distribution must end at `D - 1`.

Tie handling:

```text
mid_rank_percentile
  = share(values strictly less than current)
    + 0.5 * share(values exactly equal to current)
```

As-of constraints:

```text
uses_future_data_flag = false
cross_stock_fill_flag = false
within_stock_lookback_excludes_future_data = true
within_stock_lookback_ends_at_D_minus_1 = true
```

`zscore` may be reported audit-only, but cannot be used in any primary gate.

## 11. Label Design

Primary label:

```text
label_self_relative_H3_i(D)
  = stock_H3_net_return_i(D)
    - rolling_mean_stock_H3_net_return_i(
        over completed H3 labels whose H3 exit_date <= D - 1 trading day,
        within the prior 252 trading days before D
      )
```

Audit-only labels:

```text
label_raw_H3
label_industry_relative_H3
```

As-of requirements:

```text
self_relative_label_lookback_only_uses_completed_h3_labels = true
self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1 = true
```

Primary gates must use `label_self_relative_H3`.

## 12. State Bucket Design

For each fold `k`, freeze state bucket edges using:

```text
split = train
instrument scope = seen_folds(k)
family = vwap_deviation
score = vwap_state_score_i,k(D)
```

Primary three-bucket state:

```text
bottom_quintile_state:
  score <= train_seen_fold_q20_k

middle_state:
  train_seen_fold_q20_k < score < train_seen_fold_q80_k

top_quintile_state:
  score >= train_seen_fold_q80_k
```

Decile audit:

```text
state_decile = 1 ... 10
```

Decile edges are also fold-specific and train-seen-only.

No validation / robustness data may affect bucket edges.

## 13. Primary Evaluation Units

R08.1 must output metrics at four levels:

### 13.1 Fold-Level Unseen Metrics

Granularity:

```text
family
fold_id
split
unseen_fold
```

Required splits:

```text
train_oof_unseen
validation_oof_unseen
robustness_oof_unseen
```

Fold spread definitions mirror aggregate definitions:

```text
fold_unseen_daily_spread_k(D)
  = mean(label_self_relative_H3 for top_quintile_state events in fold k on D)
    - mean(label_self_relative_H3 for bottom_quintile_state events in fold k on D)

fold_unseen_mean_spread
  = mean over valid signal dates of fold_unseen_daily_spread_k(D)

fold_unseen_median_spread
  = median over valid signal dates of fold_unseen_daily_spread_k(D)

fold_unseen_pooled_high_minus_low_spread
  = pooled mean label of all top_quintile_state events in fold k
    - pooled mean label of all bottom_quintile_state events in fold k
```

Metrics:

```text
fold_unseen_mean_spread
fold_unseen_median_spread
fold_unseen_pooled_high_minus_low_spread
fold_unseen_positive_instrument_share
fold_unseen_positive_date_share
fold_unseen_valid_instrument_count
fold_unseen_full_valid_instrument_count
fold_unseen_partial_event_only_instrument_count
fold_unseen_valid_signal_date_count
fold_unseen_within_stock_rankIC_median
fold_unseen_decile_monotonicity_score
fold_unseen_top1_instrument_contribution_share
fold_unseen_top5_instrument_contribution_share
fold_unseen_top1_industry_contribution_share
```

### 13.2 Fold-Aggregated Out-of-Fold Unseen Metrics

For each split:

```text
split in:
  train_oof_unseen
  validation_oof_unseen
  robustness_oof_unseen

aggregate all events where each instrument is evaluated only in its own unseen fold
```

Daily spread definition:

```text
aggregate_oof_unseen_daily_spread(D)
  = mean(label_self_relative_H3 for top_quintile_state events on D)
    - mean(label_self_relative_H3 for bottom_quintile_state events on D)
```

Aggregate spread definitions:

```text
aggregate_oof_unseen_mean_spread
  = mean over valid signal dates of aggregate_oof_unseen_daily_spread(D)

aggregate_oof_unseen_median_spread
  = median over valid signal dates of aggregate_oof_unseen_daily_spread(D)

aggregate_oof_unseen_pooled_high_minus_low_spread
  = pooled mean label of all top_quintile_state events
    - pooled mean label of all bottom_quintile_state events
```

Gate usage:

```text
time transfer and instrument transfer gates use:
  aggregate_oof_unseen_mean_spread
  aggregate_oof_unseen_median_spread

pooled_high_minus_low_spread is report-only,
unless explicitly referenced by concentration or decomposition artifacts.
```

Metrics:

```text
split
aggregate_oof_unseen_mean_spread
aggregate_oof_unseen_median_spread
aggregate_oof_unseen_pooled_high_minus_low_spread
aggregate_oof_unseen_positive_instrument_share
aggregate_oof_unseen_positive_date_share
aggregate_oof_unseen_valid_instrument_count
aggregate_oof_unseen_full_valid_instrument_count
aggregate_oof_unseen_partial_event_only_instrument_count
aggregate_oof_unseen_valid_signal_date_count
aggregate_oof_unseen_within_stock_rankIC_median
aggregate_oof_unseen_decile_monotonicity_score
```

### 13.3 Fold Dispersion Metrics

Across the 5 folds:

```text
positive_fold_count
negative_fold_count
median_fold_spread
min_fold_spread
max_fold_spread
fold_spread_iqr
fold_positive_instrument_share_median
fold_positive_instrument_share_min
fold_monotonicity_median
fold_monotonicity_min
worst_fold_id_by_spread
worst_fold_id_by_positive_instrument_share
```

Fold dispersion uses `fold_unseen_mean_spread` as `fold_spread` unless explicitly stated otherwise.

### 13.4 Comparator Metrics

For `volume_price_correlation`, output the same metrics audit-only:

```text
vpc_fold_unseen_spread
vpc_aggregate_oof_unseen_spread
vpc_fold_dispersion
comparator_dominates_primary_flag
```

Comparator metrics cannot affect primary final decision.

## 14. Sample Gate

R08.1 has separate sample gates for:

- fold construction;
- fold-level evaluability;
- aggregate out-of-fold evaluability.

### 14.1 Scope Sample Gate

```text
full_scope_instrument_count >= 300
primary_family = vwap_deviation
primary_horizon = H3
fold_count = 5
```

### 14.2 Direction Sample Gate

For each fold:

```text
retained_vwap_factor_count_k >= 5
direction_source_split = train
direction_source_instrument_scope = seen_folds(k)
min(fold_direction_valid_instrument_count_f,k over retained factors) >= 80
```

### 14.3 Fold-Level Unseen Evaluability Gate

A fold is evaluable in split `S` if:

```text
fold_unseen_valid_instrument_count_k,S >= 20
fold_unseen_valid_signal_date_count_k,S >= 30
per_date_high_state_event_count >= 5
per_date_low_state_event_count >= 5
```

Per-instrument event floor:

```text
train_oof_unseen:
  min_per_instrument_signal_count >= 80

validation_oof_unseen / robustness_oof_unseen:
  min_per_instrument_signal_count_for_full_instrument_metric >= 60
```

Partial instruments:

```text
30 <= split_signal_count < 60:
  may contribute to event-level aggregate spread
  must be excluded from positive_instrument_share denominator
  must be excluded from fold_unseen_full_valid_instrument_count
  must be excluded from aggregate_oof_unseen_full_valid_instrument_count
  must be flagged as partial_instrument_event_only

split_signal_count < 30:
  excluded from fold-level evaluation
```

Full valid instruments:

```text
fold_unseen_full_valid_instrument_count:
  count of unseen instruments with split_signal_count >= 60

aggregate_oof_unseen_full_valid_instrument_count:
  count of unique out-of-fold unseen instruments with split_signal_count >= 60

sample gates and positive_instrument_share denominators use only full valid instruments.
Partial instruments can improve event-level spread precision,
but they cannot help satisfy instrument-count sample gates.
```

### 14.4 Aggregate Out-of-Fold Sample Gate

For validation and robustness:

```text
evaluable_fold_count >= 4
aggregate_oof_unseen_full_valid_instrument_count >= 100
aggregate_oof_unseen_valid_signal_date_count >= 70
```

Aggregate sample status:

```text
aggregate_oof_sample_status = pass
  if evaluable_fold_count_validation = 5
  and evaluable_fold_count_robustness >= 4
  and aggregate sample floors pass

aggregate_oof_sample_status = pass_with_fold_coverage_caveat
  if evaluable_fold_count_validation = 4
  and evaluable_fold_count_robustness >= 4
  and aggregate sample floors pass
  and caveat margin conditions pass

aggregate_oof_sample_status = fail
  otherwise
```

Caveat margin conditions:

```text
validation_oof_unseen_mean_spread >= 0.0015
validation_oof_unseen_positive_instrument_share >= 0.60
positive_fold_count_validation >= 3
```

If only 4 folds are evaluable, the report must set:

```text
fold_coverage_caveat = true
```

For `pass_with_fold_coverage_caveat`, supported decision is not allowed unless the caveat margin conditions above pass. No additional undefined margin language may be used.

```text
validation_oof_unseen_mean_spread >= 0.0015
validation_oof_unseen_positive_instrument_share >= 0.60
```

Support caveat policy:

```text
fold_coverage_caveat:
  allowed for supported decision only when
  aggregate_oof_sample_status = pass_with_fold_coverage_caveat

validation_single_positive_year_caveat:
  allowed for supported decision only when
  validation_single_positive_year margin conditions in Section 15 pass

robustness_single_positive_year_caveat:
  allowed for supported decision only if
  robustness_actual_evaluable_year_count = 1
  and all robustness spread / non-deterioration gates pass

concentration_caveat:
  not allowed
  concentration gate is binary

fold_stability_caveat:
  not allowed for supported decision
  fold stability failure maps to fold-fragile

no_disallowed_caveat_active:
  true only if no concentration_caveat is active,
  no fold_stability_caveat is active,
  and robustness_single_positive_year_caveat is allowed under the rule above
```

## 15. Time Transfer Gate

Primary time transfer uses aggregate out-of-fold unseen metrics.

Train baseline:

```text
train_oof_unseen_mean_spread
train_oof_unseen_median_spread
train_oof_unseen_pooled_high_minus_low_spread
```

Validation gate:

```text
validation_oof_unseen_mean_spread > 0
validation_oof_unseen_median_spread >= 0
validation_positive_year_count >= 1
validation_oof_unseen_mean_spread
  >= train_oof_unseen_mean_spread - 0.0030
```

If validation has only one positive year:

```text
validation_single_positive_year_caveat = true
validation_oof_unseen_mean_spread >= 0.0010
validation_negative_year_mean_spread >= -0.0015
```

Clean validation support:

```text
validation_positive_year_count >= 2
```

Robustness gate:

```text
robustness_oof_unseen_mean_spread >= -0.0025
robustness_oof_unseen_median_spread >= -0.0025
robustness_actual_evaluable_year_count >= 1
robustness_positive_year_count
  >= max(1, ceil(0.50 * robustness_actual_evaluable_year_count))
robustness_oof_unseen_mean_spread
  >= train_oof_unseen_mean_spread - 0.0040
```

Preferred robust support condition:

```text
robustness_positive_year_count = robustness_actual_evaluable_year_count
```

If robustness has only one positive year:

```text
robustness_single_positive_year_caveat = true
```

Supported decision with this caveat is allowed only when:

```text
robustness_actual_evaluable_year_count = 1
robustness_oof_unseen_mean_spread >= 0
robustness_oof_unseen_median_spread >= 0
fold stability gate passes
concentration gate passes
```

If `robustness_actual_evaluable_year_count >= 2` and only one robustness year is positive, supported decision is not allowed.

## 16. Instrument Transfer and Fold Stability Gate

Primary instrument transfer is the fold-aggregated out-of-fold unseen readout.

Aggregate unseen gate:

```text
validation_oof_unseen_mean_spread > 0
validation_oof_unseen_median_spread >= 0
robustness_oof_unseen_mean_spread >= -0.0025
validation_oof_unseen_positive_instrument_share >= 0.55
robustness_oof_unseen_positive_instrument_share >= 0.50
```

Fold stability gate:

```text
positive_fold_count_validation >= 3
positive_fold_count_robustness >= 3
median_fold_spread_validation > 0
median_fold_spread_robustness >= 0
min_fold_spread_validation >= -0.0040
min_fold_spread_robustness >= -0.0040
fold_positive_instrument_share_median_validation >= 0.50
fold_positive_instrument_share_median_robustness >= 0.50
```

Clean fold stability annotation:

```text
clean_positive_fold_count_validation = true if positive_fold_count_validation >= 4
clean_positive_fold_count_robustness = true if positive_fold_count_robustness >= 4
```

If validation and robustness aggregate instrument-transfer metrics pass, time transfer passes, monotonicity passes, concentration passes, robustness non-deterioration passes, but fold stability fails, final decision must be:

```text
r08_1_fold_fragile_vwap_state_candidate
```

not supported.

## 17. Monotonicity Gate

Primary monotonicity uses aggregate out-of-fold unseen deciles.

Aggregate monotonicity gate:

```text
validation_oof_unseen_decile_monotonicity_score >= 0.60
robustness_oof_unseen_decile_monotonicity_score >= 0.60
```

Fold-level monotonicity gate:

```text
fold_monotonicity_median_validation >= 0.50
fold_monotonicity_median_robustness >= 0.50
fold_monotonicity_positive_count_validation >= 3
fold_monotonicity_positive_count_robustness >= 3
```

Middle-state inversion:

```text
middle_state_violently_inverted_flag = false
```

R08.1 must report decile mean labels for every fold and aggregate split.

## 18. Concentration Gate

R08.1 must compute concentration on the aggregate out-of-fold unseen contribution decomposition.

Instrument contribution:

```text
instrument_high_low_contribution_i
  = (mean(high_state_label_i) - mean(low_state_label_i))
    * (high_state_event_count_i + low_state_event_count_i)

instrument_contribution_share_i
  = abs(instrument_high_low_contribution_i)
    / sum_j(abs(instrument_high_low_contribution_j))
```

Industry contribution uses PIT industry at signal date:

```text
industry_contribution_share_k
  = sum over event-weighted absolute contribution where industry(i, D) = k
    / total absolute contribution
```

Aggregate concentration gate:

```text
top1_instrument_contribution_share <= 0.05
top5_instrument_contribution_share <= 0.20
top1_industry_contribution_share <= 0.35
```

Industry overweight audit:

```text
top1_industry_universe_weight
top1_industry_contribution_minus_universe_weight
top1_industry_contribution_to_weight_ratio
```

The overweight audit is required for interpretation but does not replace the hard concentration gate.

Fold concentration gate:

```text
max_fold_top1_instrument_contribution_share <= 0.15
max_fold_top5_instrument_contribution_share <= 0.45
max_fold_contribution_share_of_total_abs_contribution <= 0.35
```

The last gate prevents a single fold from dominating the aggregate readout.

## 19. Comparator and Negative-Control Policy

`volume_price_correlation` is audit-only.

It must answer:

```text
Does R07/R08 vpc H3 evidence improve under 5-fold unseen aggregation?
```

Comparator dominance flag:

```text
comparator_dominates_primary_flag = true
  if vpc aggregate validation and robustness spread
     both exceed vwap by >= 0.0010
  or vpc fold stability passes while vwap fold stability fails
```

But it cannot:

- replace `vwap_deviation` as primary;
- trigger supported decision;
- authorize strategy;
- be selected because it performs better than vwap.

`volume_surge_money_flow` is excluded from R08.1 primary and comparator scope. The report may mention its R08 failure, but no R08.1 metric is required for it.

## 20. Final Decisions

R08.1 final decision must be first-match and replayable.

### 20.1 Data or Contract Blocked

```text
r08_1_blocked_data_or_execution_contract
```

Triggers:

```text
scope violation
H3 contract violation
as-of violation
fold assignment violation
missing required artifacts
primary family unavailable
```

### 20.2 K-Fold Sample Blocked

```text
r08_1_blocked_kfold_sample_insufficient
```

Triggers:

```text
direction sample gate fails
or aggregate_oof_sample_status = fail
or evaluable_fold_count_validation < 4
or evaluable_fold_count_robustness < 4
```

### 20.3 No Vwap K-Fold Transferability Support

```text
r08_1_no_vwap_kfold_transferability_support
```

Triggers:

```text
aggregate_oof_sample_status in {pass, pass_with_fold_coverage_caveat},
but aggregate validation / robustness spread,
positive instrument share,
monotonicity,
or concentration does not pass.
```

### 20.4 Fold-Fragile Vwap State Candidate

```text
r08_1_fold_fragile_vwap_state_candidate
```

Triggers:

```text
validation and robustness aggregate out-of-fold instrument-transfer metrics pass,
time transfer gate passes,
monotonicity gate passes,
concentration gate passes,
robustness non-deterioration passes,
but fold stability gate fails.
```

Meaning:

```text
vwap_deviation may contain state information,
but the evidence is driven by unstable fold composition.
```

### 20.5 Time Transfer Only

```text
r08_1_time_transfer_only_not_instrument_transfer
```

Triggers:

```text
time transfer gate passes,
aggregate instrument transfer gate fails,
monotonicity gate passes,
concentration gate passes,
and robustness non-deterioration passes.
```

### 20.6 K-Fold Transferability Sensitivity Supported

```text
r08_1_vwap_kfold_transferability_sensitivity_supported
```

Required:

```text
aggregate_oof_sample_status in {pass, pass_with_fold_coverage_caveat}
time transfer gate pass
instrument transfer gate pass
fold stability gate pass
monotonicity gate pass
concentration gate pass
robustness non-deterioration pass
no disallowed caveat active
```

Comparator dominance is not a support gate:

```text
comparator_dominates_primary_flag may be true,
but it cannot block or trigger the primary vwap decision.
It is an annotation for the next confirmatory diagnostic only.
```

Meaning:

```text
R08's single-split unseen sample blocker was likely too strict / too thin,
and vwap_deviation H3 single-stock state relation survives
5-fold out-of-fold transfer sensitivity.
```

This decision still does not authorize strategy.

Allowed next step:

```text
allowed_next_requirement = confirmatory_vwap_state_transferability_diagnostic
authorized_strategy_requirement = false
```

## 21. Decision Replay Priority

Final decision priority:

```text
rule_01:
  if data / execution / scope / as-of / fold contract violation
  -> r08_1_blocked_data_or_execution_contract

rule_02:
  if primary vwap family cannot form fold-specific state score
  -> r08_1_blocked_kfold_sample_insufficient

rule_03:
  if aggregate_oof_sample_status = fail
  -> r08_1_blocked_kfold_sample_insufficient

rule_04:
  if time transfer gate passes
  and aggregate instrument transfer gate passes
  and monotonicity gate passes
  and concentration gate passes
  and robustness non-deterioration passes
  and fold stability gate fails
  -> r08_1_fold_fragile_vwap_state_candidate

rule_05:
  if time transfer gate passes
  and aggregate instrument transfer gate fails
  and monotonicity gate passes
  and concentration gate passes
  and robustness non-deterioration passes
  -> r08_1_time_transfer_only_not_instrument_transfer

rule_06:
  if all support gates pass
  -> r08_1_vwap_kfold_transferability_sensitivity_supported

rule_07:
  otherwise
  -> r08_1_no_vwap_kfold_transferability_support
```

Only one rule may be selected.

The decision replay artifact must show both:

```text
raw_condition_met
selected_rule_flag
```

## 22. Required Artifacts

Audit artifacts:

```text
audit/r08_1_run_manifest.json
audit/r08_1_input_data_audit.csv
audit/r08_1_data_availability_audit.csv
audit/r08_1_scope_audit.csv
audit/r08_1_fold_assignment_audit.csv
audit/r08_1_within_stock_normalization_audit.csv
audit/r08_1_h3_label_audit.csv
audit/r08_1_factor_direction_by_fold_audit.csv
audit/r08_1_family_scope_by_fold_audit.csv
audit/r08_1_state_bucket_by_fold_audit.csv
audit/r08_1_fold_sample_audit.csv
audit/r08_1_concentration_audit.csv
audit/r08_1_comparator_vpc_audit.csv
```

Metric artifacts:

```text
metrics/r08_1_fold_unseen_state_spread.csv
metrics/r08_1_aggregate_oof_unseen_state_spread.csv
metrics/r08_1_fold_dispersion_summary.csv
metrics/r08_1_instrument_transfer_summary.csv
metrics/r08_1_time_transfer_summary.csv
metrics/r08_1_year_availability_and_positive_count.csv
metrics/r08_1_decile_monotonicity_by_fold.csv
metrics/r08_1_aggregate_decile_monotonicity.csv
metrics/r08_1_concentration_summary.csv
metrics/r08_1_vpc_comparator_summary.csv
```

Decision artifacts:

```text
decision/r08_1_gate_inputs.csv
decision/r08_1_final_decision_replay.csv
decision/r08_1_final_decision.csv
```

Report and manifest:

```text
reports/r08_1_final_report.md
manifests/r08_1_artifact_hashes.json
manifests/r08_1_validation.json
```

## 23. Report Required Questions

The final report must answer:

1. R08.1 是否保持 diagnostic-only，且没有构造任何策略？
2. 是否只把 `vwap_deviation` 作为 primary family？
3. 是否只研究 H3？
4. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？
5. 每个 fold 的 direction 是否只来自 train years + seen folds？
6. 每个 fold 的 state bucket edge 是否只来自 train years + seen folds？
7. 是否每只股票只在自己的 unseen fold 中参与 primary out-of-fold evaluation？
8. validation aggregate out-of-fold spread 是否为正？
9. robustness aggregate out-of-fold spread 是否确认？
10. validation / robustness aggregate positive instrument share 是否达标？
11. 5 个 fold 中有多少 fold spread 为正？
12. 最差 fold 的 spread 与 positive instrument share 是多少？
13. aggregate monotonicity 是否 >= 0.60？
14. fold-level monotonicity 是否稳定？
15. aggregate concentration 是否通过？
16. 是否有单一 fold、单一股票或单一行业贡献过大？
17. `vwap_deviation` 相比 R08 单次 unseen split 的结果是否改善？
18. `volume_price_correlation` comparator 是否只是 audit-only？
19. 最终结果是 k-fold sensitivity supported、fold-fragile，还是 no support？
20. 是否允许写 strategy requirement？答案必须是 no。
21. 如果结果 supported，允许的下一步 confirmatory diagnostic 是什么？
22. aggregate OOF metric 命名是否一致，gate 使用的是 mean / median spread 还是 pooled spread？
23. train_oof_unseen baseline 是否落盘并用于 non-deterioration replay？
24. robustness 实际可用结束日期是哪一天，是否发生 data availability truncation？
25. fold coverage caveat path 是否触发，`aggregate_oof_sample_status` 是什么？
26. direction-insufficient factor 是否已从 retained set 中删除？
27. `comparator_dominates_primary_flag` 是否为 true，它是否只作为 audit annotation？
28. partial instruments 是否只进入 event-level spread，且没有计入 sample gate 或 positive instrument denominator？
29. 如果 final decision 是 fold-fragile，是否确认 monotonicity、concentration、time transfer 与 aggregate instrument transfer 均已通过？

## 24. Validation Requirements

Validator must check:

```text
required_artifacts_exist = true
primary_family_only_vwap_deviation = true
primary_horizon_only_H3 = true
no_strategy_artifacts = true
no_top_fraction_selection = true
fold_assignment_sha256_mod5 = true
fold_hash_input_canonicalized = true
all_5_folds_present = true
no_fold_dropped_for_performance = true
direction_train_seen_only = true
direction_insufficient_factors_dropped = true
bucket_edges_train_seen_only = true
primary_evaluation_unseen_fold_only = true
self_relative_label_asof_safe = true
normalization_prior_252d_asof_safe = true
within_stock_lookback_ends_at_D_minus_1 = true
mid_rank_tie_handling_used = true
aggregate_oof_metrics_exist = true
aggregate_metric_names_replayable = true
train_oof_unseen_baseline_exists = true
data_availability_audit_exists = true
aggregate_oof_sample_status_replayable = true
partial_instruments_excluded_from_sample_gate = true
partial_instruments_excluded_from_positive_instrument_share = true
fold_dispersion_metrics_exist = true
concentration_formula_replayable = true
comparator_dominates_primary_flag_reported = true
fold_fragile_rule_requires_all_non_fold_gates_pass = true
decision_replay_first_match = true
authorized_strategy_requirement_false = true
```

Validation failure must block final decision.

## 25. Interpretation Boundary

R08.1 has three interpretation boundaries:

### 25.1 Positive Sensitivity Is Not Strategy Authorization

Even if R08.1 returns:

```text
r08_1_vwap_kfold_transferability_sensitivity_supported
```

the only allowed conclusion is:

```text
vwap_deviation H3 deserves a confirmatory transferability diagnostic.
```

It cannot conclude:

```text
vwap_deviation H3 can be traded.
```

### 25.2 Aggregate Positive Without Fold Stability Is Weak Evidence

If aggregate spread is positive but fold stability fails, conclusion must be:

```text
fold-fragile candidate
```

not supported.

### 25.3 Comparator Cannot Change Primary Scope

If `volume_price_correlation` outperforms `vwap_deviation`, R08.1 may report it, but cannot switch the primary family. A new requirement would be required to study vpc as primary.

## 26. Minimal Implementation Scope

Minimal R08.1 implementation:

```text
primary family:
  vwap_deviation

audit-only comparator:
  volume_price_correlation

horizon:
  H3

state:
  within-stock 252d percentile

label:
  H3 self-relative net return

transfer:
  canonical sha256 instrument hash mod 5
  5-fold out-of-fold unseen evaluation

primary readout:
  aggregate_oof_unseen mean / median spread
  positive instrument share
  fold-level dispersion
  decile monotonicity
  concentration
```

One-sentence summary:

```text
R08.1 tests whether vwap_deviation H3's single-stock state relation survives
5-fold out-of-fold instrument transfer sensitivity,
without authorizing any strategy.
```
