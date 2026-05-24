# EP5 Requirement 08.2: Daily-Observed VWAP Deviation H3 Transferability Diagnostic with H5/H10 Horizon Labels V0

## 1. Requirement Metadata

requirement_id: `ep5_r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0`

short_name: `r08_2_daily_vwap_h3_h5_h10_transferability_diagnostic_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-24`

primary_output_namespace: `ep5/outputs/r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0/`

upstream_requirements:

- `ep5/requirement_08_h3_volume_price_single_stock_state_transferability_audit_v0.md`
- `ep5/requirement_08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0.md`

upstream_reports:

- `ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/reports/r08_final_report.md`
- `ep5/outputs/r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0/reports/r08_1_final_report.md`

upstream_final_decisions:

```text
R08:
  r08_blocked_data_or_execution_contract

R08.1:
  r08_1_no_vwap_kfold_transferability_support
```

R08.2 is a new diagnostic requirement. It does not alter R08 or R08.1 decisions.

## 2. Research Positioning

R08.2 exists because R08 and R08.1 used:

```text
weekly close-observed signal
H3 label
```

This is methodologically conservative but may be misaligned with `vwap_deviation`, whose state can be short-lived and may decay before the next weekly observation.

R08.2 changes only the signal observation frequency:

```text
from:
  weekly close-observed signal

to:
  daily close-observed signal
```

Primary question remains H3:

```text
Does daily-observed within-stock vwap_deviation state have
cross-instrument, cross-year transferable H3 return meaning?
```

H5 and H10 are diagnostic labels only:

```text
H5 / H10 may describe horizon shape and decay,
but may not select a better horizon,
may not rescue a failed H3 result,
and may not authorize a strategy.
```

R08.2 is still diagnostic-only. It is not a strategy requirement.

R08.2 also preserves the R08.1 cleanliness gates:

```text
fold-level monotonicity remains a support gate;
fold-level concentration remains a support gate;
daily observation does not downgrade either gate to diagnostic-only.
```

Expected diagnostic split:

```text
If daily observation improves H3 spread / sample density
but fold-level monotonicity or concentration still fails,
R08.2 must report:
  daily_observation_spread_improved_but_cleanliness_failed

This is an informative diagnostic outcome,
not transferability support.
```

## 3. Upstream Motivation

R08.1 resolved the biggest R08 sample blocker:

```text
R08 vwap_deviation validation unseen valid instruments:
  22

R08.1 vwap_deviation validation OOF full-valid instruments:
  181

R08.1 aggregate_oof_sample_status:
  pass
```

R08.1 also found positive H3 OOF spread:

```text
vwap_deviation validation OOF mean spread:
  +0.2638%

vwap_deviation robustness OOF mean spread:
  +0.2484%
```

But R08.1 did not support transferability:

```text
validation positive instrument share:
  52.49% < 55%

validation fold monotonicity median:
  0.3818 < 0.50

fold concentration:
  validation fold 3 top1 instrument share = 17.51% > 15%

final_decision:
  r08_1_no_vwap_kfold_transferability_support
```

This creates a specific follow-up question:

```text
Was weekly observation too sparse for a short-lived VWAP deviation state?
```

R08.2 tests that question by observing signals daily while preserving strict transferability gates and adding overlap controls.

Therefore R08.2 is not expected to automatically solve every R08.1 failure mode. It specifically tests whether weekly observation was too sparse for a short-lived VWAP state. Any remaining failure in fold-level monotonicity, fold-level concentration, or positive instrument breadth must remain a hard blocker for support.

## 4. Core Question

R08.2 answers one primary question:

```text
Under the current PIT mcap500 mainboard universe,
daily close-observed signal,
next-open execution,
110bps round-trip cost,
within-stock 252d percentile state,
5-fold instrument out-of-fold unseen evaluation,
and explicit overlapping-label controls,

does vwap_deviation have a transferable H3 single-stock state-return relation?
```

Secondary diagnostic question:

```text
Using the same daily-observed vwap state definition,
what happens to the relation at H5 and H10?
```

Primary decision is based on H3 only.

## 5. Non-Goals and Explicit Prohibitions

R08.2 must not:

1. Construct a trading strategy.
2. Output long-only alpha pass.
3. Output hedged alpha pass.
4. Output production signal.
5. Output top-N, top20%, top-decile, or any cross-sectional selection basket.
6. Use cross-sectional rank as primary score.
7. Select stocks using validation or robustness results.
8. Select dates using validation or robustness results.
9. Select fold using fold performance.
10. Select factor using validation or robustness.
11. Select direction using validation or robustness.
12. Select threshold using validation or robustness.
13. Select horizon using H5 or H10 diagnostic results.
14. Replace H3 with H5 or H10 if H3 fails.
15. Optimize per-stock factor, threshold, or horizon.
16. Introduce a new primary family.
17. Introduce LGBM, neural network, optimizer, PCA, autoencoder, or any learned combiner.
18. Use right-tail, big-winner, hit-rate, or isolated extreme events to rescue a failed gate.
19. Treat overlapping daily labels as independent observations.
20. Use online data.
21. Trigger backtest, paper trading, live trading, or production pipeline.

One-line boundary:

```text
R08.2 tests whether daily observation changes the transferability diagnosis;
it does not start a strategy path.
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

Diagnostic horizons:

```text
H5
H10
```

Primary state:

```text
within-stock 252d percentile
```

Primary label:

```text
H3 self-relative net return
```

Diagnostic labels:

```text
H5 self-relative net return
H10 self-relative net return
```

Primary transfer design:

```text
5-fold instrument out-of-fold unseen evaluation
```

No comparator family is required in R08.2. `volume_price_correlation` may be mentioned as upstream context, but it is outside the canonical R08.2 scope unless a later requirement explicitly adds it.

## 7. Data and Execution Contract

R08.2 uses the same local data boundary as R08/R08.1:

- local PIT Qlib provider;
- PIT mcap500 mainboard universe;
- PIT industry membership;
- trading calendar;
- R06/R08 frozen Alpha191 factor registry and family map;
- no-online-data boundary.

Time split:

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
  daily close-observed trading date

entry:
  first executable next open after D

exit H3:
  open after 3 trading days

exit H5:
  open after 5 trading days

exit H10:
  open after 10 trading days

label:
  net of 110bps round-trip cost
```

R08.2 must not reuse weekly candidate rows as the primary signal panel. It must build or load a daily decision-bearing candidate panel:

```text
one event per eligible (signal_date, instrument_id)
for every trading day D in the PIT universe
where close-observed factor state and next-open execution contract are available.
```

## 8. Daily Signal Panel Construction

R08.2 must construct a daily candidate panel with:

```text
instrument_id
signal_date
split
industry_id
industry_name
base_eligible
candidate_row_id
daily_trading_calendar_index
```

`daily_trading_calendar_index` must be globally replayable:

```text
daily_trading_calendar_index:
  global exchange trading-calendar index
  shared by all instruments
  continuous across train / validation / robustness
  not reset by split, instrument, listing date, or universe entry date
  starts from the first available PIT trading date in the local provider
```

Eligibility:

```text
base_eligible = true
instrument is in PIT mcap500 mainboard universe at D
instrument has close-observed feature values at D
next-open entry is executable within execution-lag contract
H3/H5/H10 labels are either complete or explicitly marked unavailable
```

Daily candidate panel must not:

```text
forward-fill cross-stock state
use future universe membership
include post-exit information in features
drop losing or missing events based on realized label
```

Signal date split is assigned by signal date D, but each label must pass split-purity:

```text
entry_execution_date and exit_execution_date for horizon H
must be observable and must not violate the local execution contract.
```

If a horizon label cannot be completed because local data ends before exit, that horizon is unavailable for that event. H3 availability controls primary evaluation; H5/H10 availability controls diagnostic evaluation only.

Horizon availability must be independent:

```text
H5_unavailable_flag or H10_unavailable_flag
  must not remove an otherwise valid H3 primary event.

H3_unavailable_flag
  removes the event from H3 primary evaluation,
  but does not imply a data-contract violation if the event is outside
  the H3 actual complete window.
```

## 9. Data Availability Audit

R08.2 must audit data availability separately for each horizon:

```text
declared_robustness_end_date = 2025-12-31
last_available_trading_date
last_H3_label_complete_signal_date
last_H5_label_complete_signal_date
last_H10_label_complete_signal_date

robustness_window_actual_end_date_H
  = min(
      declared_robustness_end_date,
      last_available_trading_date,
      last_H_label_complete_signal_date
    )
```

Required fields:

```text
horizon
declared_robustness_end_date
last_available_trading_date
last_label_complete_signal_date
robustness_window_actual_end_date
robustness_end_date_data_available
robustness_window_truncated_by_data_availability
robustness_actual_evaluable_year_count
robustness_actual_signal_date_count
```

Primary final decision uses H3 actual availability. H5/H10 truncation may only affect diagnostic label readout.

Evaluable year definition:

```text
robustness_actual_evaluable_year_count_H
  counts a calendar year only if
  H-complete signal date count in that year >= 60.

Years below the 60 H-complete signal-date floor
  must be reported as partial_year_not_counted.
```

## 10. Within-Stock Normalization

R08.2 uses the same primary state normalization as R08/R08.1:

```text
factor_ts_percentile_f,i(D)
  = mid-rank percentile of current factor value
    against instrument i's prior 252 trading days
```

As-of rule:

```text
lookback_window_end = D - 1 trading day
current factor value at D may use close-observed information at D
execution starts at next open after D
```

Minimum history:

```text
within_stock_lookback_trading_days = 252
within_stock_min_history_count = 126
```

Tie handling:

```text
mid_rank_percentile
  = share(values strictly less than current)
    + 0.5 * share(values exactly equal to current)
```

Required audit flags:

```text
uses_future_data_flag = false
cross_stock_fill_flag = false
within_stock_lookback_excludes_future_data = true
within_stock_lookback_ends_at_D_minus_1 = true
mid_rank_tie_handling_used = true
```

`zscore` may be reported audit-only but cannot be used in primary gates.

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

Diagnostic labels:

```text
label_self_relative_H5_i(D)
  = stock_H5_net_return_i(D)
    - rolling_mean_stock_H5_net_return_i(
        over completed H5 labels whose H5 exit_date <= D - 1 trading day,
        within the prior 252 trading days before D
      )

label_self_relative_H10_i(D)
  = stock_H10_net_return_i(D)
    - rolling_mean_stock_H10_net_return_i(
        over completed H10 labels whose H10 exit_date <= D - 1 trading day,
        within the prior 252 trading days before D
      )
```

Audit-only labels:

```text
label_raw_H3
label_raw_H5
label_raw_H10
label_industry_relative_H3
label_industry_relative_H5
label_industry_relative_H10
```

Primary gates use only `label_self_relative_H3`.

H5/H10 must not alter:

```text
factor direction
retained factor set
state score definition
bucket edges
final support decision
```

## 12. Overlapping-Label Control

Daily H3/H5/H10 labels overlap heavily. R08.2 must not treat all daily events as independent evidence.

R08.2 must produce two readouts:

### 12.1 Full Daily Readout

All eligible daily events are included:

```text
full_daily_readout
```

This is useful for signal coverage and point estimates, but it is not sufficient for support.

### 12.2 Anchor-Offset Overlap-Controlled Readout

For each horizon H:

```text
anchor_stride_H = H trading days
anchor_offset in {0, ..., H-1}

event belongs to anchor_offset a if:
  daily_trading_calendar_index mod H = a
```

This creates non-overlapping event streams inside each anchor offset.

Anchor offset identity must be stable:

```text
anchor_offset is defined on the global daily_trading_calendar_index.
It must not be recomputed separately inside train, validation,
robustness, fold, instrument, or horizon-specific subsets.
```

Required anchor counts:

```text
H3:
  3 anchor offsets

H5:
  5 anchor offsets

H10:
  10 anchor offsets
```

Primary H3 gates use overlap-controlled readout:

```text
H3_anchor_controlled_mean_spread
H3_anchor_controlled_median_spread
H3_anchor_positive_offset_count
H3_anchor_offset_spread_min
H3_anchor_offset_spread_median
H3_anchor_controlled_positive_instrument_share
```

Full daily readout must also be reported, but cannot replace anchor-controlled evidence.

Overlap-adjusted confidence summary:

```text
For H3 primary:
  compute anchor_offset_mean_spread_a for a in {0,1,2}
  compute monthly_block_mean_spread_m within each anchor offset
  report:
    anchor_mean_spread_mean
    anchor_mean_spread_median
    anchor_mean_spread_min
    positive_anchor_offset_count
    monthly_block_positive_share
    monthly_block_spread_p25
    monthly_block_spread_p75

These fields are diagnostic confidence controls.
They do not replace the hard gates in Sections 19-22.
```

Full-daily versus anchor-controlled conflict flags:

```text
full_daily_anchor_sign_conflict_flag
  = sign(H3_full_daily_oof_mean_spread)
    != sign(H3_anchor_controlled_mean_spread)

full_daily_anchor_spread_gap
  = H3_full_daily_oof_mean_spread
    - H3_anchor_controlled_mean_spread
```

## 13. Instrument K-Fold Transfer Design

R08.2 keeps R08.1 deterministic 5-fold instrument transfer:

```text
instrument_fold_id
  = int.from_bytes(sha256(canonical_instrument_id.lower()).digest()[:8], "big") mod 5
```

For each fold `k`:

```text
seen_folds(k):
  instruments where instrument_fold_id != k

unseen_fold(k):
  instruments where instrument_fold_id == k
```

For each fold:

```text
direction input:
  train years only
  seen_folds(k) only
  H3 label only

state bucket edge input:
  train years only
  seen_folds(k) only
  score only

primary evaluation:
  unseen_fold(k)
  validation / robustness
  H3 label only

diagnostic evaluation:
  unseen_fold(k)
  validation / robustness
  H5/H10 labels using same state score and bucket edges
```

No fold may be dropped, merged, or reweighted based on performance.

## 14. Factor Direction and Family Score

R08.2 primary family is:

```text
vwap_deviation
```

For each fold `k` and factor `f`:

```text
instrument_factor_rankic_full_daily_f,i,k
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )

instrument_factor_rankic_anchor_a_f,i,k
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )
    over events where daily_trading_calendar_index mod 3 = a
```

Direction input:

```text
split = train
instrument scope = seen_folds(k)
horizon = H3 only
```

Because daily H3 labels overlap, direction must be learned under anchor offsets. Full daily direction is audit-only:

```text
factor_direction_stat_full_daily_f,k
factor_direction_stat_anchor_offset_a_f,k for a in {0,1,2}
factor_direction_anchor_positive_sign_count_f,k
factor_direction_anchor_negative_sign_count_f,k
factor_direction_stat_anchor_median_f,k
```

Direction sign:

```text
factor_direction_stat_anchor_offset_a_f,k
  = median over valid train-seen instruments of
    instrument_factor_rankic_anchor_a_f,i,k

factor_direction_stat_anchor_median_f,k
  = median over a in {0,1,2} of
    factor_direction_stat_anchor_offset_a_f,k

direction_f,k = sign(factor_direction_stat_anchor_median_f,k)
```

Direction stability condition:

```text
full_daily_direction_sign agrees with at least 2 / 3 H3 anchor-offset direction signs
anchor_median_direction_sign is nonzero
```

Valid instrument condition:

```text
train_signal_count_for_instrument_factor >= 160 daily events
factor_nonconstant_observation_share >= 0.80
```

`factor_nonconstant_observation_share` must be reported for every factor / fold. Any factor below `0.80` is removed from `retained_vwap_factor_set_k` before family scoring.

Direction sample gate:

```text
fold_direction_valid_instrument_count_f,k >= 80
```

Insufficient factors are dropped:

```text
if direction_status == factor_direction_sample_insufficient
or direction_anchor_stability_pass == false
or factor_nonconstant_observation_share < 0.80:
  remove factor f from retained_vwap_factor_set_k
```

Retained family condition:

```text
retained_vwap_factor_count_k >= 5
```

Family state score:

```text
vwap_state_score_i,k(D)
  = mean_over_retained_vwap_factors(
      0.5 + direction_f,k * (factor_ts_percentile_f,i(D) - 0.5)
    )
```

H5/H10 may not influence direction.

## 15. State Bucket Design

For each fold `k`, freeze bucket edges using:

```text
split = train
instrument scope = seen_folds(k)
score = vwap_state_score_i,k(D)
frequency = daily
```

Primary state buckets:

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

No validation / robustness data may affect bucket edges.

## 16. Primary H3 Evaluation Units

R08.2 must output primary H3 metrics at:

1. Fold-level unseen full daily.
2. Fold-level unseen H3 anchor offsets.
3. Aggregate OOF unseen full daily.
4. Aggregate OOF unseen H3 anchor-controlled.
5. Year-level aggregate.
6. Instrument-level aggregate.
7. Decile monotonicity.
8. Concentration.

Required H3 aggregate metrics:

```text
H3_full_daily_oof_mean_spread
H3_full_daily_oof_median_spread
H3_full_daily_oof_positive_date_share
H3_full_daily_oof_positive_instrument_share

H3_train_oof_full_daily_mean_spread
H3_train_oof_full_daily_median_spread
H3_train_oof_anchor_controlled_mean_spread
H3_train_oof_anchor_controlled_median_spread

H3_anchor_controlled_mean_spread
H3_anchor_controlled_median_spread
H3_anchor_positive_offset_count
H3_anchor_offset_spread_min
H3_anchor_offset_spread_median
H3_anchor_controlled_positive_instrument_share

H3_aggregate_decile_monotonicity_score
H3_fold_monotonicity_median
H3_top1_instrument_contribution_share
H3_top5_instrument_contribution_share
H3_top1_industry_contribution_share

full_daily_anchor_sign_conflict_flag
full_daily_anchor_spread_gap
```

Gate usage:

```text
primary H3 support gates use anchor-controlled metrics.
full daily metrics are report-only unless explicitly used as a non-contradiction check.
```

Full daily non-contradiction:

```text
H3_full_daily_oof_mean_spread_validation >= -0.0010
H3_full_daily_oof_mean_spread_robustness >= -0.0015
full_daily_anchor_sign_conflict_flag_validation = false
full_daily_anchor_sign_conflict_flag_robustness = false
```

## 17. H5/H10 Diagnostic Label Evaluation

H5 and H10 use:

```text
same vwap_state_score
same factor directions learned from H3 train-seen data
same bucket edges learned from train-seen score distribution
same instrument folds
same PIT daily signal panel
```

For each diagnostic horizon H in `{H5, H10}`:

```text
anchor_stride_H = H
anchor_offset in {0, ..., H-1}
```

Required diagnostic metrics:

```text
H5_anchor_controlled_mean_spread
H5_anchor_controlled_positive_offset_count
H5_anchor_controlled_positive_instrument_share
H5_aggregate_decile_monotonicity_score

H10_anchor_controlled_mean_spread
H10_anchor_controlled_positive_offset_count
H10_anchor_controlled_positive_instrument_share
H10_aggregate_decile_monotonicity_score
```

Required horizon-shape outputs:

```text
horizon_shape_validation:
  H3_mean_spread
  H5_mean_spread
  H10_mean_spread
  H5_minus_H3
  H10_minus_H3
  H10_minus_H5
  sign_pattern

horizon_shape_robustness:
  same fields
```

Diagnostic interpretations:

```text
short_lived_state_only:
  H3 diagnostic-positive,
  and both H5/H10 are weak_or_negative

state_persistence_candidate:
  H3, H5, H10 are all diagnostic-positive,
  with diagnostic concentration pass for H5/H10

horizon_mismatch_diagnostic_only:
  H3 primary support fails,
  but H5 or H10 is diagnostic-positive
  and exceeds H3 mean spread by >= 0.0010

no_horizon_shape_support:
  H3/H5/H10 all weak or unstable
```

Horizon-shape terms:

```text
weak_or_negative:
  anchor_controlled_mean_spread < 0.0010
  or positive_instrument_share < 0.50

diagnostic-positive:
  diagnostic_horizon_positive = true
```

H5/H10 cannot trigger supported decision.

## 18. Sample Gate

### 18.1 Daily Panel Sample Gate

```text
full_scope_instrument_count >= 300
daily_signal_date_count_train >= 700
daily_signal_date_count_validation >= 300
daily_signal_date_count_robustness >= 300
primary_family = vwap_deviation
primary_horizon = H3
diagnostic_horizons = H5,H10
```

### 18.2 Direction Sample Gate

For each fold:

```text
retained_vwap_factor_count_k >= 5
direction_source_split = train
direction_source_instrument_scope = seen_folds(k)
direction_label_horizon = H3
min(fold_direction_valid_instrument_count_f,k over retained factors) >= 80
direction_anchor_stability_pass = true
```

### 18.3 Fold-Level H3 Evaluability Gate

For validation and robustness:

```text
fold_unseen_full_valid_instrument_count_k,S >= 30
fold_unseen_valid_signal_date_count_k,S >= 120 full daily dates
H3_anchor_valid_signal_date_count_k,S,a >= 35 for each anchor offset a
```

Per-instrument full-valid condition:

```text
validation / robustness:
  min_per_instrument_signal_count >= 120 daily events

train:
  min_per_instrument_signal_count >= 300 daily events
```

Partial instruments:

```text
For each horizon H:
  full_valid_instrument_flag_H
  partial_instrument_flag_H
  positive_instrument_denominator_H

60 <= H_complete_split_signal_count < full_valid_threshold_H:
  may contribute to event-level spread
  must be excluded from positive_instrument_share denominator for horizon H
  must be excluded from sample gates for horizon H
```

H3, H5, and H10 must have separate full-valid / partial flags. H5 or H10 partial status must not change the H3 primary denominator.

### 18.4 Aggregate H3 OOF Sample Gate

For validation and robustness:

```text
evaluable_fold_count >= 4
aggregate_oof_full_valid_instrument_count >= 200
aggregate_oof_full_daily_valid_signal_date_count >= 300
H3_anchor_offset_evaluable_count = 3 / 3
H3_anchor_min_valid_signal_date_count >= 80 per split
```

The `aggregate_oof_full_valid_instrument_count >= 200` floor is intentionally above the R08.1 weekly OOF observed level (`181` validation / `188` robustness). R08.2 only changes signal observation to daily, so the daily panel must demonstrate materially better instrument coverage before claiming that weekly sampling was the main sample-density blocker.

Aggregate sample status:

```text
aggregate_oof_sample_status = pass
aggregate_oof_sample_status = pass_with_fold_coverage_caveat
aggregate_oof_sample_status = fail
```

`pass_with_fold_coverage_caveat` is allowed only when:

```text
validation_evaluable_fold_count = 4
robustness_evaluable_fold_count >= 4
aggregate sample floors pass
H3_anchor_controlled_validation_mean_spread >= 0.0015
H3_anchor_controlled_positive_instrument_share_validation >= 0.60
H3_positive_fold_count_validation >= 3
```

## 19. Time Transfer Gate

Primary time transfer uses H3 overlap-controlled OOF unseen metrics.

Train baseline:

```text
H3_train_oof_anchor_controlled_mean_spread
H3_train_oof_anchor_controlled_median_spread
H3_train_oof_full_daily_mean_spread
```

Train baseline is computed with the same fold-specific OOF rule as validation / robustness:

```text
for each fold k:
  direction and bucket edges are learned from train years + seen_folds(k)
  train baseline events are train years + unseen_fold(k)
  H3 anchor offsets are computed from the global calendar index

H3_train_oof_anchor_controlled_mean_spread
  = aggregate across fold-specific train OOF unseen anchor-controlled events
```

Validation gate:

```text
H3_validation_anchor_controlled_mean_spread > 0
H3_validation_anchor_controlled_median_spread >= 0
H3_validation_anchor_positive_offset_count >= 2
H3_validation_positive_year_count >= 1
H3_validation_anchor_controlled_mean_spread
  >= H3_train_oof_anchor_controlled_mean_spread - 0.0030
H3_full_daily_oof_mean_spread_validation >= -0.0010
full_daily_anchor_sign_conflict_flag_validation = false
```

If validation has only one positive year:

```text
validation_single_positive_year_caveat = true
H3_validation_anchor_controlled_mean_spread >= 0.0010
H3_validation_negative_year_mean_spread >= -0.0015
```

Robustness gate:

```text
H3_robustness_anchor_controlled_mean_spread >= -0.0025
H3_robustness_anchor_controlled_median_spread >= -0.0025
H3_robustness_anchor_positive_offset_count >= 2
H3_robustness_positive_year_count
  >= max(1, ceil(0.50 * robustness_actual_evaluable_year_count_H3))
H3_robustness_anchor_controlled_mean_spread
  >= H3_train_oof_anchor_controlled_mean_spread - 0.0040
H3_full_daily_oof_mean_spread_robustness >= -0.0015
full_daily_anchor_sign_conflict_flag_robustness = false
```

`robustness_actual_evaluable_year_count_H3` uses the Section 9 evaluable-year rule: a calendar year counts only when H3-complete signal date count in that year is at least `60`.

## 20. Instrument Transfer and Fold Stability Gate

Instrument transfer gate:

```text
H3_validation_anchor_controlled_positive_instrument_share >= 0.55
H3_robustness_anchor_controlled_positive_instrument_share >= 0.50
```

Spread sign and non-deterioration checks belong to the time transfer gate in Section 19. They must be present in gate inputs, but they must not be double-counted as separate instrument-transfer conditions.

Fold stability gate:

```text
H3_positive_fold_count_validation >= 3
H3_positive_fold_count_robustness >= 3
H3_median_fold_spread_validation > 0
H3_median_fold_spread_robustness >= 0
H3_min_fold_spread_validation >= -0.0040
H3_min_fold_spread_robustness >= -0.0040
H3_fold_positive_instrument_share_median_validation >= 0.50
H3_fold_positive_instrument_share_median_robustness >= 0.50
```

Anchor stability gate:

```text
H3_positive_anchor_offset_count_validation >= 2
H3_positive_anchor_offset_count_robustness >= 2
H3_anchor_offset_spread_min_validation >= -0.0040
H3_anchor_offset_spread_min_robustness >= -0.0040
```

## 21. Monotonicity Gate

Primary H3 monotonicity gate:

```text
H3_validation_anchor_controlled_decile_monotonicity_score >= 0.60
H3_robustness_anchor_controlled_decile_monotonicity_score >= 0.60
H3_fold_monotonicity_median_validation >= 0.50
H3_fold_monotonicity_median_robustness >= 0.50
H3_fold_monotonicity_positive_count_validation >= 3
H3_fold_monotonicity_positive_count_robustness >= 3
middle_state_violently_inverted_flag = false
```

Full daily monotonicity must be reported but is not sufficient for support.

Fold-level monotonicity is intentionally retained as a support gate. R08.2 must not downgrade it to diagnostic-only even if daily observation improves aggregate spread.

## 22. Concentration Gate

Concentration is computed on H3 overlap-controlled OOF unseen contribution decomposition.

Instrument contribution:

```text
instrument_high_low_contribution_i
  = (mean(top_quintile_state_label_i) - mean(bottom_quintile_state_label_i))
    * (top_quintile_event_count_i + bottom_quintile_event_count_i)
```

Contribution share:

```text
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

Fold concentration gate:

```text
max_fold_top1_instrument_contribution_share <= 0.15
max_fold_top5_instrument_contribution_share <= 0.45
max_fold_contribution_share_of_total_abs_contribution <= 0.35
```

Anchor concentration audit:

```text
max_anchor_top1_instrument_contribution_share
max_anchor_top5_instrument_contribution_share
max_anchor_industry_contribution_share
max_anchor_abs_contribution_share_of_total
```

Anchor concentration is audit-only unless it reveals a denominator-zero or single-anchor dominance problem.

Escalation rule:

```text
if concentration_denominator_zero_flag = true
or max_anchor_abs_contribution_share_of_total > 0.60:
  anchor_concentration_disallowed_caveat = true
  H3 concentration gate fails
```

Fold-level concentration is intentionally retained as a support gate. R08.2 must not downgrade it to diagnostic-only even if daily observation improves aggregate spread.

## 23. H5/H10 Diagnostic Gates

H5/H10 have diagnostic gates, not support gates.

For each diagnostic horizon H in `{H5, H10}`:

```text
H_anchor_controlled_mean_spread_validation
H_anchor_controlled_mean_spread_robustness
H_anchor_controlled_positive_instrument_share_validation
H_anchor_controlled_positive_instrument_share_robustness
H_anchor_decile_monotonicity_validation
H_anchor_decile_monotonicity_robustness
H_positive_anchor_offset_count_validation
H_positive_anchor_offset_count_robustness
H_diagnostic_top1_instrument_contribution_share_validation
H_diagnostic_top1_instrument_contribution_share_robustness
H_diagnostic_top5_instrument_contribution_share_validation
H_diagnostic_top5_instrument_contribution_share_robustness
H_diagnostic_concentration_denominator_zero_flag_validation
H_diagnostic_concentration_denominator_zero_flag_robustness
```

Diagnostic labels:

```text
diagnostic_horizon_positive:
  validation mean > 0
  robustness mean >= -0.0025
  validation positive instrument share >= 0.55
  robustness positive instrument share >= 0.50
  validation anchor decile monotonicity >= 0.50
  robustness anchor decile monotonicity >= 0.50
  validation positive anchor offset count >= ceil(0.60 * H)
  robustness positive anchor offset count >= ceil(0.50 * H)
  validation top1 instrument contribution share <= 0.10
  robustness top1 instrument contribution share <= 0.10
  validation top5 instrument contribution share <= 0.35
  robustness top5 instrument contribution share <= 0.35
  diagnostic concentration denominator zero flag = false
```

Diagnostic results may produce annotations:

```text
horizon_shape_short_lived
horizon_shape_persistent
horizon_shape_horizon_mismatch
horizon_shape_no_support
```

But:

```text
H5/H10 diagnostic pass cannot change final_decision to supported.
```

## 24. Final Decisions

R08.2 final decision is first-match and H3-primary.

### 24.1 Data or Execution Blocked

```text
r08_2_blocked_data_or_execution_contract
```

Triggers:

```text
daily signal panel cannot be constructed
PIT universe contract violation
H3 execution / label contract violation
as-of violation
fold assignment violation
missing required artifacts
```

### 24.2 Overlap-Controlled Sample Blocked

```text
r08_2_blocked_overlap_controlled_sample_insufficient
```

Triggers:

```text
direction sample gate fails
or aggregate_oof_sample_status = fail
or H3 anchor offset sample gate fails
or evaluable_fold_count_validation < 4
or evaluable_fold_count_robustness < 4
```

### 24.3 No Daily H3 Transferability Support

```text
r08_2_no_daily_vwap_h3_transferability_support
```

Triggers:

```text
H3 sample passes,
but H3 time transfer,
instrument transfer,
anchor stability,
monotonicity,
or concentration fails.
```

Required diagnostic annotation when applicable:

```text
daily_observation_spread_improved_but_cleanliness_failed:
  H3 time transfer gate passes
  H3 full daily or anchor-controlled spread improves versus R08.1 weekly H3
  but H3 monotonicity gate fails
  or H3 concentration gate fails
```

### 24.4 Daily H3 Fold-Fragile Candidate

```text
r08_2_daily_vwap_h3_fold_fragile_candidate
```

Triggers:

```text
H3 aggregate time / instrument / anchor / monotonicity / concentration gates pass,
but fold stability fails.
```

### 24.5 Daily H3 Time Transfer Only

```text
r08_2_daily_vwap_h3_time_transfer_only
```

Triggers:

```text
H3 time transfer passes,
but H3 instrument transfer fails,
while fold stability, anchor stability, monotonicity, concentration,
robustness non-deterioration, and overlap-controlled sample gates pass.
```

### 24.6 Horizon Mismatch Diagnostic Only

```text
r08_2_horizon_mismatch_diagnostic_only
```

Triggers:

```text
H3 sample passes,
H3 primary support fails,
but H5 or H10 diagnostic horizon passes.
```

Meaning:

```text
The state may not be an H3 state.
This does not authorize horizon switching.
A new requirement would be required to study H5/H10 as primary.
```

### 24.7 Daily H3 Transferability Diagnostic Supported

```text
r08_2_daily_vwap_h3_transferability_diagnostic_supported
```

Required:

```text
aggregate_oof_sample_status in {pass, pass_with_fold_coverage_caveat}
H3 time transfer gate pass
H3 instrument transfer gate pass
H3 fold stability gate pass
H3 anchor stability gate pass
H3 monotonicity gate pass
H3 concentration gate pass
H3 robustness non-deterioration pass
no disallowed caveat active
```

Meaning:

```text
Daily-observed vwap_deviation H3 state relation survives
overlap-controlled, out-of-fold transferability diagnostic.
```

This still does not authorize strategy.

Allowed next step:

```text
allowed_next_requirement = confirmatory_daily_vwap_h3_transferability_diagnostic
authorized_strategy_requirement = false
```

## 25. Decision Replay Priority

```text
rule_01:
  if data / execution / scope / as-of / fold contract violation
  -> r08_2_blocked_data_or_execution_contract

rule_02:
  if primary vwap family cannot form fold-specific state score
  -> r08_2_blocked_overlap_controlled_sample_insufficient

rule_03:
  if aggregate_oof_sample_status = fail
  or H3 anchor sample gate fails
  -> r08_2_blocked_overlap_controlled_sample_insufficient

rule_04:
  if H3 time transfer gate passes
  and H3 instrument transfer gate passes
  and H3 anchor stability gate passes
  and H3 monotonicity gate passes
  and H3 concentration gate passes
  and H3 robustness non-deterioration passes
  and H3 fold stability gate fails
  -> r08_2_daily_vwap_h3_fold_fragile_candidate

rule_05:
  if H3 time transfer gate passes
  and H3 instrument transfer gate fails
  and H3 fold stability gate passes
  and H3 anchor stability gate passes
  and H3 monotonicity gate passes
  and H3 concentration gate passes
  and H3 robustness non-deterioration passes
  -> r08_2_daily_vwap_h3_time_transfer_only

rule_06:
  if all H3 support gates pass
  -> r08_2_daily_vwap_h3_transferability_diagnostic_supported

rule_07:
  if no previous rule selected
  and H3 sample passes
  and H3 support fails
  and H5 or H10 diagnostic horizon passes
  -> r08_2_horizon_mismatch_diagnostic_only

rule_08:
  otherwise
  -> r08_2_no_daily_vwap_h3_transferability_support
```

Decision replay must include:

```text
raw_condition_met
selected_rule_flag
decision_if_selected
```

Exactly one rule may be selected.

## 26. Required Artifacts

Audit artifacts:

```text
audit/r08_2_run_manifest.json
audit/r08_2_input_data_audit.csv
audit/r08_2_daily_signal_panel_audit.csv
audit/r08_2_data_availability_by_horizon_audit.csv
audit/r08_2_scope_audit.csv
audit/r08_2_fold_assignment_audit.csv
audit/r08_2_within_stock_normalization_audit.csv
audit/r08_2_label_asof_audit.csv
audit/r08_2_factor_direction_by_fold_audit.csv
audit/r08_2_factor_nonconstant_observation_audit.csv
audit/r08_2_family_scope_by_fold_audit.csv
audit/r08_2_state_bucket_by_fold_audit.csv
audit/r08_2_overlap_anchor_audit.csv
audit/r08_2_fold_sample_audit.csv
audit/r08_2_horizon_specific_instrument_validity_audit.csv
audit/r08_2_concentration_audit.csv
```

Metric artifacts:

```text
metrics/r08_2_h3_full_daily_oof_spread.csv
metrics/r08_2_h3_anchor_controlled_oof_spread.csv
metrics/r08_2_h3_train_baseline_summary.csv
metrics/r08_2_h3_fold_unseen_state_spread.csv
metrics/r08_2_h3_fold_dispersion_summary.csv
metrics/r08_2_h3_instrument_transfer_summary.csv
metrics/r08_2_h3_time_transfer_summary.csv
metrics/r08_2_h3_year_availability_and_positive_count.csv
metrics/r08_2_h3_decile_monotonicity_by_anchor.csv
metrics/r08_2_h3_concentration_summary.csv
metrics/r08_2_h5_diagnostic_oof_spread.csv
metrics/r08_2_h10_diagnostic_oof_spread.csv
metrics/r08_2_horizon_shape_summary.csv
metrics/r08_2_overlap_adjusted_confidence_summary.csv
```

Decision artifacts:

```text
decision/r08_2_gate_inputs.csv
decision/r08_2_horizon_diagnostic_inputs.csv
decision/r08_2_final_decision_replay.csv
decision/r08_2_final_decision.csv
```

Report and manifest:

```text
reports/r08_2_final_report.md
manifests/r08_2_artifact_hashes.json
manifests/r08_2_validation.json
```

## 27. Report Required Questions

The final report must answer:

1. R08.2 是否保持 diagnostic-only，且没有构造任何策略？
2. 是否把 signal frequency 从 weekly 改成 daily？
3. 是否只把 `vwap_deviation` 作为 primary family？
4. 是否只把 H3 作为 primary horizon？
5. H5/H10 是否只作为 diagnostic labels？
6. daily signal panel 是否 PIT / as-of safe？
7. daily factor percentile 是否使用 D-1 之前的 252 日 reference distribution？
8. H3/H5/H10 self-relative labels 是否只使用 completed labels？
9. daily overlapping label 是否被显式控制？
10. H3 anchor offsets 是否全部可评价？
11. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？
12. direction 是否只来自 train years + seen folds + H3？
13. H5/H10 是否没有参与 direction、bucket edge、factor retention？
14. validation H3 anchor-controlled spread 是否为正？
15. robustness H3 anchor-controlled spread 是否确认？
16. full daily readout 是否与 anchor-controlled readout 冲突？
17. validation / robustness H3 positive instrument share 是否达标？
18. H3 fold stability 是否达标？
19. H3 anchor stability 是否达标？
20. H3 monotonicity 是否达标？
21. H3 concentration 是否达标？
22. H5 diagnostic label 的 spread / monotonicity / positive instrument share 是什么？
23. H10 diagnostic label 的 spread / monotonicity / positive instrument share 是什么？
24. horizon shape 是 short-lived、persistent、horizon-mismatch 还是 no-support？
25. 如果 H5/H10 强于 H3，是否确认这不改变 primary final decision？
26. 结果相比 R08.1 weekly H3 是否改善？
27. final decision 是 supported、fold-fragile、time-transfer-only、horizon-mismatch 还是 no-support？
28. 是否允许写 strategy requirement？答案必须是 no。
29. 如果 supported，允许的下一步 confirmatory diagnostic 是什么？
30. `daily_trading_calendar_index` 是否为全市场共用、跨 split 连续、且没有按 instrument 重置？
31. direction canonical sign 是否来自 H3 anchor-controlled train-seen stats，而不是 full daily overlapping stats？
32. train OOF anchor-controlled baseline 是否落盘并用于 non-deterioration replay？
33. H3/H5/H10 full-valid 与 partial instrument denominator 是否 horizon-specific？
34. 如果 daily spread 改善但 monotonicity / concentration 仍失败，是否标注 `daily_observation_spread_improved_but_cleanliness_failed`？
35. H5/H10 diagnostic horizon pass 是否同时通过 spread、instrument breadth、anchor count、monotonicity 和 diagnostic concentration？

## 28. Validation Requirements

Validator must check:

```text
required_artifacts_exist = true
primary_family_only_vwap_deviation = true
primary_horizon_only_H3 = true
diagnostic_horizons_only_H5_H10 = true
signal_frequency_daily = true
weekly_signal_panel_not_used_as_primary = true
no_strategy_artifacts = true
no_top_fraction_selection = true
fold_assignment_sha256_mod5 = true
all_5_folds_present = true
no_fold_dropped_for_performance = true
daily_trading_calendar_index_global_continuous = true
direction_train_seen_only = true
direction_label_horizon_H3_only = true
direction_canonical_sign_anchor_controlled = true
H5_H10_not_used_for_direction = true
direction_anchor_stability_checked = true
factor_nonconstant_observation_audit_exists = true
bucket_edges_train_seen_only = true
primary_evaluation_unseen_fold_only = true
within_stock_lookback_ends_at_D_minus_1 = true
mid_rank_tie_handling_used = true
self_relative_labels_use_completed_labels_only = true
overlap_anchor_offsets_exist_for_H3_H5_H10 = true
H3_primary_gate_uses_anchor_controlled_metrics = true
full_daily_metrics_report_only_or_noncontradiction = true
train_oof_anchor_baseline_exists = true
full_daily_anchor_conflict_flags_exist = true
H5_H10_diagnostic_only = true
horizon_switching_forbidden = true
partial_instruments_horizon_specific = true
partial_instruments_excluded_from_sample_gate_by_horizon = true
partial_instruments_excluded_from_positive_instrument_share_by_horizon = true
concentration_formula_replayable = true
anchor_concentration_escalation_rule_exists = true
H5_H10_diagnostic_pass_replayable = true
decision_replay_first_match = true
authorized_strategy_requirement_false = true
```

Validation failure must block final decision.

## 29. Interpretation Boundary

R08.2 has three strict interpretation boundaries.

### 29.1 Daily H3 Support Is Not Strategy Authorization

Even if R08.2 returns:

```text
r08_2_daily_vwap_h3_transferability_diagnostic_supported
```

the only allowed conclusion is:

```text
daily-observed vwap_deviation H3 deserves a confirmatory diagnostic.
```

It cannot conclude:

```text
vwap_deviation H3 can be traded.
```

### 29.2 H5/H10 Positive Does Not Rescue H3

If H3 fails but H5 or H10 is positive:

```text
final_decision may be:
  r08_2_horizon_mismatch_diagnostic_only
```

It cannot become:

```text
r08_2_daily_vwap_h3_transferability_diagnostic_supported
```

It also cannot directly authorize an H5 or H10 primary requirement after seeing the diagnostic results. A later H5/H10 requirement must be explicitly pre-registered as confirmatory diagnostic, with its own primary horizon and gates fixed before implementation.

### 29.3 Overlap-Controlled Evidence Dominates Full Daily Evidence

If full daily spread is positive but anchor-controlled spread fails:

```text
R08.2 must not claim support.
```

Full daily readout can describe the point estimate, but overlap-controlled readout controls the primary conclusion.

### 29.4 Daily Spread Improvement Does Not Override Cleanliness Gates

If daily observation improves spread relative to R08.1 weekly H3 but fold-level monotonicity or concentration fails:

```text
R08.2 may report:
  daily_observation_spread_improved_but_cleanliness_failed

R08.2 must not report:
  r08_2_daily_vwap_h3_transferability_diagnostic_supported
```

This preserves the R08.1 lesson that spread without clean fold-level structure is not transferable support.

## 30. Minimal Implementation Scope

Minimal R08.2 implementation:

```text
primary family:
  vwap_deviation

signal frequency:
  daily close-observed

primary horizon:
  H3

diagnostic horizons:
  H5
  H10

state:
  within-stock 252d percentile

label:
  H3 self-relative net return primary
  H5/H10 self-relative net return diagnostic

transfer:
  5-fold instrument OOF unseen evaluation

overlap control:
  H3 anchor offsets 0/1/2
  H5 anchor offsets 0..4 diagnostic
  H10 anchor offsets 0..9 diagnostic

primary readout:
  H3 anchor-controlled OOF spread
  H3 positive instrument share
  H3 fold stability
  H3 anchor stability
  H3 decile monotonicity
  H3 concentration
```

One-sentence summary:

```text
R08.2 tests whether daily observation reveals a transferable
vwap_deviation H3 single-stock state relation,
while using H5/H10 only to diagnose horizon shape and never to rescue H3.
```
