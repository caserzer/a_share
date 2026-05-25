# EP5 Requirement 08.3: Daily-Observed Volume/Rank Families H3 Transferability Diagnostic with H5/H10 Horizon Labels V0

## 1. Requirement Metadata

requirement_id: `ep5_r08_3_daily_observed_volume_rank_families_h3_h5_h10_transferability_diagnostic_v0`

short_name: `r08_3_daily_volume_rank_h3_h5_h10_transferability_diagnostic_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-25`

primary_output_namespace: `ep5/outputs/r08_3_daily_observed_volume_rank_families_h3_h5_h10_transferability_diagnostic_v0/`

upstream_requirements:

- `ep5/requirement_07_short_horizon_timing_failure_attribution_audit_v0.md`
- `ep5/requirement_08_h3_volume_price_single_stock_state_transferability_audit_v0.md`
- `ep5/requirement_08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0.md`
- `ep5/requirement_08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0.md`

upstream_reports:

- `ep5/outputs/r07_short_horizon_timing_failure_attribution_audit_v0/reports/r07_final_report.md`
- `ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/reports/r08_final_report.md`
- `ep5/outputs/r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0/reports/r08_1_final_report.md`
- `ep5/outputs/r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0/reports/r08_2_final_report.md`

upstream_final_decisions:

```text
R07:
  r07_insufficient_state_cell_sample_blocked

R08:
  r08_blocked_data_or_execution_contract

R08.1:
  r08_1_no_vwap_kfold_transferability_support

R08.2:
  r08_2_daily_vwap_h3_transferability_diagnostic_supported
```

R08.3 is a new diagnostic requirement. It does not alter R07, R08, R08.1, or R08.2 decisions.

## 2. Research Positioning

R07 found short-horizon information pockets outside `vwap_deviation`:

```text
volume_surge_money_flow:
  H1/H3/H5/H10 pockets; widest coverage

volume_price_correlation:
  H1/H3 pockets; strongest H3 positive example in R07

rank_ts_rank_structure:
  H1/H3 pockets; only 1 included factor, so interpretation breadth is weak
```

R08.2 then showed that daily observation can materially improve transferability diagnostics for a short-lived within-stock state. R08.3 applies the same daily-observed, overlap-controlled H3 transferability contract to three non-vwap families synchronously:

```text
volume_surge_money_flow
volume_price_correlation
rank_ts_rank_structure
```

R08.3 does not ask which family is best. It asks whether each pre-registered family independently has a transferable daily-observed H3 single-stock state-return relation.

## 3. Core Question

Under the current PIT mcap500 mainboard universe, daily close-observed signal, next-open execution, 110bps round-trip cost, within-stock 252d percentile state, 5-fold instrument out-of-fold unseen evaluation, and explicit overlapping-label controls:

```text
Does each of the following families independently have
cross-instrument, cross-year transferable H3 return meaning?

1. volume_surge_money_flow
2. volume_price_correlation
3. rank_ts_rank_structure
```

Secondary diagnostic question:

```text
Using the same daily-observed family state definition,
what happens to each family at H5 and H10?
```

Primary decision is H3 only. H5/H10 may describe horizon shape but cannot rescue H3 or authorize horizon switching.

## 4. Non-Goals and Explicit Prohibitions

R08.3 must not:

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
11. Select factor direction using validation or robustness.
12. Select threshold using validation or robustness.
13. Select horizon using H5 or H10 diagnostic results.
14. Replace H3 with H5 or H10 if H3 fails.
15. Optimize per-stock factor, threshold, family, or horizon.
16. Choose one winning family after seeing validation or robustness.
17. Combine the three families into a learned or hand-tuned meta-score.
18. Introduce LGBM, neural network, optimizer, PCA, autoencoder, or any learned combiner.
19. Use right-tail, big-winner, hit-rate, or isolated extreme events to rescue a failed gate.
20. Treat overlapping daily labels as independent observations.
21. Use online data.
22. Trigger backtest, paper trading, live trading, or production pipeline.

One-line boundary:

```text
R08.3 synchronously diagnoses three pre-registered families;
it does not start a family-selection or strategy path.
```

## 5. Canonical Scope

Co-primary diagnostic families:

```text
volume_surge_money_flow
volume_price_correlation
rank_ts_rank_structure
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

Each family must be scored, bucketed, evaluated, and decided independently. A pass or fail in one family must not change another family's direction, factor set, bucket edges, gates, or final decision.

`vwap_deviation` may be mentioned as R08.2 reference context only. It is not an R08.3 primary family and must not be included in any R08.3 family score.

## 6. Data and Execution Contract

R08.3 uses the same local data boundary as R08.2:

- local PIT Qlib provider;
- PIT mcap500 mainboard universe;
- PIT industry membership;
- trading calendar;
- R06/R05 Alpha191 factor registry and family map;
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

R08.3 must not reuse weekly candidate rows as the primary signal panel. It must build or load one shared daily decision-bearing candidate panel:

```text
one event per eligible (signal_date, instrument_id)
for every trading day D in the PIT universe
where close-observed factor state and next-open execution contract are available.
```

The same candidate panel, execution panel, label panel, fold assignment, and global daily calendar index must be used for all three families.

## 7. Daily Signal Panel Construction

R08.3 must construct a daily candidate panel with:

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

H5 or H10 unavailability must not remove an otherwise valid H3 primary event.

## 8. Within-Stock Normalization

For every in-scope factor `f`, instrument `i`, and signal date `D`:

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

## 9. Label Design

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
label_self_relative_H10_i(D)
```

Each diagnostic label uses the same self-relative rule for its own horizon.

Audit-only labels:

```text
label_raw_H3
label_raw_H5
label_raw_H10
label_industry_relative_H3
label_industry_relative_H5
label_industry_relative_H10
label_self_relative_H3_gross
label_self_relative_H5_gross
label_self_relative_H10_gross
```

Primary gates use only `label_self_relative_H3`.

H5/H10 must not alter:

```text
factor direction
retained factor set
state score definition
bucket edges
final H3 support decision
```

## 10. Data Availability Audit

R08.3 must audit data availability separately for each horizon:

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

Primary final decision uses H3 actual availability. H5/H10 truncation may only affect diagnostic readout.

Evaluable year definition:

```text
robustness_actual_evaluable_year_count_H
  counts a calendar year only if
  H-complete signal date count in that year >= 60.
```

## 11. Overlapping-Label Control

Daily H3/H5/H10 labels overlap heavily. R08.3 must not treat all daily events as independent evidence.

For each horizon H:

```text
anchor_stride_H = H trading days
anchor_offset in {0, ..., H-1}

event belongs to anchor_offset a if:
  daily_trading_calendar_index mod H = a
```

Anchor offset identity must be stable:

```text
anchor_offset is defined on the global daily_trading_calendar_index.
It must not be recomputed separately inside train, validation,
robustness, fold, family, instrument, or horizon-specific subsets.
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

Primary H3 gates use overlap-controlled readout. Full daily readout must also be reported, but cannot replace anchor-controlled evidence.

Full-daily versus anchor-controlled conflict flags must be reported per family:

```text
full_daily_anchor_sign_conflict_flag
full_daily_anchor_spread_gap
```

## 12. Instrument K-Fold Transfer Design

R08.3 keeps R08.1/R08.2 deterministic 5-fold instrument transfer:

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

For each family `F` and fold `k`:

```text
direction input:
  train years only
  seen_folds(k) only
  H3 label only

state bucket edge input:
  train years only
  seen_folds(k) only
  family score only

primary evaluation:
  unseen_fold(k)
  validation / robustness
  H3 label only

diagnostic evaluation:
  unseen_fold(k)
  validation / robustness
  H5/H10 labels using the same family score and bucket edges
```

No fold may be dropped, merged, or reweighted based on performance.

## 13. Family Scope and Factor Retention

R08.3 primary families are assigned using the R06 pre-metric family map and the R06 executable factor list:

```text
primary_family in {
  volume_surge_money_flow,
  volume_price_correlation,
  rank_ts_rank_structure
}

in_scope_factor_set_F
  = R06 factor_ids from r06_factor_matrix_columns.json
    intersect R06 r06_factor_family_map.csv where primary_family = F
```

R07 executable scope reference:

```text
volume_surge_money_flow:
  expected executable included factor count = 15

volume_price_correlation:
  expected executable included factor count = 3

rank_ts_rank_structure:
  expected executable included factor count = 1
```

These counts are a replay reference from R07 `r07_scope_lock.csv`, not a count of every row in the raw R06 family map. R08.3 must report both:

```text
r06_family_map_primary_count_F
r06_executable_in_scope_factor_count_F
```

If the executable count differs from the R07 reference count, R08.3 must continue only when the difference is explained by a replayable R06 cache or registry change and must flag:

```text
family_scope_reference_count_changed = true
family_scope_reference_count_change_explained = true / false
unexplained_family_scope_reference_count_changed
  = family_scope_reference_count_changed
    and family_scope_reference_count_change_explained = false
```

The explanation source must be replayable from the manifest and scope audit. An unexplained executable scope count change is a disallowed caveat.

Minimum retained factor floors:

```text
volume_surge_money_flow:
  retained_factor_count >= max(5, ceil(0.60 * in_scope_factor_count))

volume_price_correlation:
  retained_factor_count >= 3

rank_ts_rank_structure:
  retained_factor_count >= 1
  single_factor_family_caveat = true
```

If `rank_ts_rank_structure` passes all H3 gates, the report may say:

```text
rank_ts_rank_structure single-factor H3 diagnostic supported
```

It must not say:

```text
rank_ts_rank_structure broad family evidence supported
```

## 14. Factor Direction and Family Score

For each family `F`, fold `k`, and factor `f`:

```text
instrument_factor_rankic_full_daily_f,i,k
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )
    over all train-seen daily events

instrument_factor_rankic_anchor_a_f,i,k
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )
    over train-seen events where daily_trading_calendar_index mod 3 = a
```

Direction input:

```text
split = train
instrument scope = seen_folds(k)
horizon = H3 only
family = F
```

Direction sign:

```text
factor_direction_stat_anchor_offset_a_f,k
  = median over valid train-seen instruments of
    instrument_factor_rankic_anchor_a_f,i,k

factor_direction_stat_full_daily_f,k
  = median over valid train-seen instruments of
    instrument_factor_rankic_full_daily_f,i,k

factor_direction_stat_anchor_median_f,k
  = median over a in {0,1,2} of
    factor_direction_stat_anchor_offset_a_f,k

direction_f,k = sign(factor_direction_stat_anchor_median_f,k)
```

Direction stability condition:

```text
full_daily_direction_sign = sign(factor_direction_stat_full_daily_f,k)
anchor_offset_direction_sign_a = sign(factor_direction_stat_anchor_offset_a_f,k)

full_daily_direction_sign agrees with at least 2 / 3 H3 anchor-offset direction signs
anchor_median_direction_sign is nonzero
```

Valid instrument condition:

```text
train_signal_count_for_instrument_factor >= 160 daily events
factor_nonconstant_observation_share >= 0.80
fold_direction_valid_instrument_count_f,k >= 80
```

Insufficient factors are dropped before family scoring.

Family state score:

```text
family_state_score_F,i,k(D)
  = mean_over_retained_factors_in_F(
      0.5 + direction_f,k * (factor_ts_percentile_f,i(D) - 0.5)
    )
```

There are no learned continuous factor weights. All retained factors are equally weighted after direction alignment. H5/H10 may not influence direction.

## 15. State Bucket Design

For each family `F` and fold `k`, freeze bucket edges using:

```text
split = train
instrument scope = seen_folds(k)
score = family_state_score_F,i,k(D)
frequency = daily
```

Primary state buckets:

```text
bottom_quintile_state:
  score <= train_seen_family_fold_q20_F,k

middle_state:
  train_seen_family_fold_q20_F,k < score < train_seen_family_fold_q80_F,k

top_quintile_state:
  score >= train_seen_family_fold_q80_F,k
```

Decile audit:

```text
state_decile = 1 ... 10
```

No validation / robustness data may affect bucket edges.

## 16. Primary H3 Evaluation Units

R08.3 must output primary H3 metrics per family at:

1. Fold-level unseen full daily.
2. Fold-level unseen H3 anchor offsets.
3. Aggregate OOF unseen full daily.
4. Aggregate OOF unseen H3 anchor-controlled.
5. Year-level aggregate.
6. Instrument-level aggregate.
7. Decile monotonicity.
8. Concentration.

Required H3 aggregate metrics per family:

```text
H3_full_daily_oof_mean_spread
H3_full_daily_oof_median_spread
H3_full_daily_oof_positive_date_share
H3_full_daily_oof_positive_instrument_share

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

State spread definition:

```text
spread(D)
  = mean(label_self_relative_H3 for top_quintile_state on D)
    - mean(label_self_relative_H3 for bottom_quintile_state on D)
```

Primary H3 support gates use anchor-controlled metrics. Full daily metrics are report-only unless explicitly used as a non-contradiction check.

## 17. H5/H10 Diagnostic Label Evaluation

H5 and H10 use:

```text
same family_state_score_F
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

Required diagnostic metrics per family:

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

Required horizon-shape outputs per family:

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

H5/H10 diagnostic pass cannot change a family H3 decision to supported.

## 18. Sample Gates

Daily panel sample gate:

```text
full_scope_instrument_count >= 300
daily_signal_date_count_train >= 700
daily_signal_date_count_validation >= 300
daily_signal_date_count_robustness >= 300
primary_families = volume_surge_money_flow,volume_price_correlation,rank_ts_rank_structure
primary_horizon = H3
diagnostic_horizons = H5,H10
```

Direction sample gate per family/fold:

```text
direction_source_split = train
direction_source_instrument_scope = seen_folds(k)
direction_label_horizon = H3
min(fold_direction_valid_instrument_count_f,k over retained factors) >= 80
direction_anchor_stability_pass = true
retained_factor_count_F,k >= family-specific retained floor
```

Fold-level H3 evaluability gate for validation and robustness:

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
For each family F and horizon H:
  full_valid_instrument_flag_F,H
  partial_instrument_flag_F,H
  positive_instrument_denominator_F,H

60 <= H_complete_split_signal_count < full_valid_threshold_H:
  may contribute to event-level spread
  must be excluded from positive_instrument_share denominator for horizon H
  must be excluded from sample gates for horizon H
```

H3, H5, and H10 must have separate full-valid / partial flags. H5 or H10 partial status must not change the H3 primary denominator.

Aggregate H3 OOF sample gate for validation and robustness:

```text
evaluable_fold_count >= 4
aggregate_oof_full_valid_instrument_count >= 200
aggregate_oof_full_daily_valid_signal_date_count >= 300
H3_anchor_offset_evaluable_count = 3 / 3
H3_anchor_min_valid_signal_date_count >= 80 per split
```

Aggregate sample status per family:

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
H3_validation_anchor_controlled_mean_spread >= 0.0015
H3_validation_anchor_controlled_positive_instrument_share >= 0.60
H3_positive_fold_count_validation >= 3
```

Sample gates must be reported per family. A sample failure in one family does not block evaluation of the other families if shared data/execution contracts are valid.

## 19. H3 Support Gates Per Family

Every family must pass all H3 gates independently to receive H3 diagnostic support.

Time transfer gate:

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

If validation has only one positive year for a family:

```text
validation_single_positive_year_caveat_F = true
H3_validation_anchor_controlled_mean_spread >= 0.0010
H3_validation_negative_year_mean_spread >= -0.0015
```

These single-positive-year requirements are part of the H3 time transfer gate.

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

Non-deterioration replay fields:

```text
H3_validation_non_deterioration_pass
  = H3_validation_anchor_controlled_mean_spread
    >= H3_train_oof_anchor_controlled_mean_spread - 0.0030

H3_robustness_non_deterioration_pass
  = H3_robustness_anchor_controlled_mean_spread
    >= H3_train_oof_anchor_controlled_mean_spread - 0.0040
```

Instrument transfer gate:

```text
H3_validation_anchor_controlled_positive_instrument_share >= 0.55
H3_robustness_anchor_controlled_positive_instrument_share >= 0.50
```

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

Monotonicity gate:

```text
H3_validation_anchor_controlled_decile_monotonicity_score >= 0.60
H3_robustness_anchor_controlled_decile_monotonicity_score >= 0.60
H3_fold_monotonicity_median_validation >= 0.50
H3_fold_monotonicity_median_robustness >= 0.50
H3_fold_monotonicity_positive_count_validation >= 3
H3_fold_monotonicity_positive_count_robustness >= 3
middle_state_violently_inverted_flag = false
```

Concentration gate:

```text
top1_instrument_contribution_share <= 0.05
top5_instrument_contribution_share <= 0.20
top1_industry_contribution_share <= 0.35
max_fold_top1_instrument_contribution_share <= 0.15
max_fold_top5_instrument_contribution_share <= 0.45
max_fold_contribution_share_of_total_abs_contribution <= 0.35
concentration_denominator_zero_flag = false
max_anchor_abs_contribution_share_of_total <= 0.60
```

Fold-level monotonicity and concentration remain hard support gates. Daily observation must not downgrade either gate to diagnostic-only.

If H3 spread / breadth readouts are positive but monotonicity or concentration fails for a family, R08.3 must report:

```text
daily_observation_spread_positive_but_cleanliness_failed_F = true
```

This is an informative diagnostic outcome, not H3 transferability support.

Disallowed caveats:

```text
unexplained_family_scope_reference_count_changed = true
concentration_denominator_zero_flag = true
max_anchor_abs_contribution_share_of_total > 0.60
required_anchor_offset_missing = true
```

`single_factor_family_caveat = true` for `rank_ts_rank_structure` is interpretive, not disallowed by itself.

## 20. H5/H10 Diagnostic Gates

For each family and each diagnostic horizon H in `{H5, H10}`:

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

H5/H10 diagnostic pass cannot authorize a new primary horizon.

## 21. Multi-Family Interpretation Rules

R08.3 tests three families in one synchronized run. This creates multiple-testing risk. The control is pre-registration and complete reporting, not validation-time selection.

Required rules:

```text
tested_family_count = 3
all pre-registered families reported = true
no family dropped for weak validation or robustness = true
no family selected as winner = true
no cross-family score formed = true
```

Allowed statements:

```text
family F independently passed H3 transferability diagnostic gates.
family F failed because of sample / time transfer / breadth / monotonicity / concentration.
family F has H5/H10 diagnostic persistence or horizon mismatch.
```

Forbidden statements:

```text
family F is the best tradable signal.
family F should replace another family in production.
combine supported families into a portfolio.
rank families by validation spread and proceed with the top family.
```

If multiple families pass, each supported family may be named independently. If only one family passes, the conclusion remains diagnostic and must mention that two other pre-registered families were tested and failed.

## 22. Final Decisions

R08.3 produces:

```text
per_family_final_decision
aggregate_r08_3_final_decision
```

Per-family final decisions are first-match within each family:

```text
r08_3_family_blocked_scope_or_sample_insufficient
r08_3_no_daily_family_h3_transferability_support
r08_3_daily_family_h3_fold_fragile_candidate
r08_3_daily_family_h3_time_transfer_only
r08_3_family_horizon_mismatch_diagnostic_only
r08_3_daily_family_h3_transferability_diagnostic_supported
```

Data or execution contract failure is global:

```text
r08_3_blocked_data_or_execution_contract
```

### 22.1 Per-Family Supported

```text
r08_3_daily_family_h3_transferability_diagnostic_supported
```

Required for family `F`:

```text
family scope pass
aggregate_oof_sample_status in {pass, pass_with_fold_coverage_caveat}
H3 time transfer gate pass
H3 instrument transfer gate pass
H3 fold stability gate pass
H3 anchor stability gate pass
H3 monotonicity gate pass
H3 concentration gate pass
H3_robustness_non_deterioration_pass = true
no disallowed caveat active
```

Meaning:

```text
Daily-observed family F H3 state relation survives
overlap-controlled, out-of-fold transferability diagnostic.
```

This still does not authorize strategy.

### 22.2 Aggregate R08.3 Decision

Aggregate decision is descriptive:

```text
r08_3_blocked_data_or_execution_contract
r08_3_all_families_sample_blocked
r08_3_no_family_h3_transferability_support
r08_3_some_family_horizon_mismatch_diagnostic_only
r08_3_at_least_one_family_h3_transferability_diagnostic_supported
```

Aggregate decision must not hide per-family decisions. The report must show all three family decisions.

Allowed next step:

```text
allowed_next_requirement = confirmatory_daily_family_h3_transferability_diagnostic
authorized_strategy_requirement = false
```

## 23. Decision Replay Priority

Global replay:

```text
rule_01:
  if data / execution / as-of / fold contract violation
  -> r08_3_blocked_data_or_execution_contract
```

Per-family replay:

```text
rule_F_01:
  if family scope, direction sample, retained factor, or H3 sample gate fails
  -> r08_3_family_blocked_scope_or_sample_insufficient

rule_F_02:
  if H3 support gates pass except fold stability
  -> r08_3_daily_family_h3_fold_fragile_candidate

rule_F_03:
  if H3 time transfer passes
  and H3 instrument transfer fails
  while fold stability, anchor stability, monotonicity, concentration,
  robustness non-deterioration, and overlap-controlled sample gates pass
  -> r08_3_daily_family_h3_time_transfer_only

rule_F_04:
  if all H3 support gates pass
  -> r08_3_daily_family_h3_transferability_diagnostic_supported

rule_F_05:
  if no previous rule selected
  and H3 sample passes
  and H3 support fails
  and H5 or H10 diagnostic horizon passes
  -> r08_3_family_horizon_mismatch_diagnostic_only

rule_F_06:
  otherwise
  -> r08_3_no_daily_family_h3_transferability_support
```

Decision replay must include:

```text
family
rule_id
raw_condition_met
selected_rule_flag
decision_if_selected
```

Exactly one per-family rule may be selected for each family.

Aggregate replay:

```text
aggregate_rule_01:
  if global rule_01 selected
  -> r08_3_blocked_data_or_execution_contract

aggregate_rule_02:
  if all per-family decisions are r08_3_family_blocked_scope_or_sample_insufficient
  -> r08_3_all_families_sample_blocked

aggregate_rule_03:
  if any per-family decision is r08_3_daily_family_h3_transferability_diagnostic_supported
  -> r08_3_at_least_one_family_h3_transferability_diagnostic_supported

aggregate_rule_04:
  if no family is H3 supported
  and any per-family decision is r08_3_family_horizon_mismatch_diagnostic_only
  -> r08_3_some_family_horizon_mismatch_diagnostic_only

aggregate_rule_05:
  otherwise
  -> r08_3_no_family_h3_transferability_support
```

Exactly one aggregate rule may be selected.

## 24. Required Artifacts

Audit artifacts:

```text
audit/r08_3_run_manifest.json
audit/r08_3_input_data_audit.csv
audit/r08_3_daily_signal_panel_audit.csv
audit/r08_3_data_availability_by_horizon_audit.csv
audit/r08_3_scope_audit.csv
audit/r08_3_family_factor_scope_audit.csv
audit/r08_3_fold_assignment_audit.csv
audit/r08_3_within_stock_normalization_audit.csv
audit/r08_3_label_asof_audit.csv
audit/r08_3_factor_direction_by_family_fold_audit.csv
audit/r08_3_factor_nonconstant_observation_audit.csv
audit/r08_3_family_scope_by_fold_audit.csv
audit/r08_3_state_bucket_by_family_fold_audit.csv
audit/r08_3_overlap_anchor_audit.csv
audit/r08_3_fold_sample_audit.csv
audit/r08_3_horizon_specific_instrument_validity_audit.csv
audit/r08_3_concentration_audit.csv
```

Metric artifacts:

```text
metrics/r08_3_h3_full_daily_oof_spread_by_family.csv
metrics/r08_3_h3_anchor_controlled_oof_spread_by_family.csv
metrics/r08_3_h3_train_baseline_summary_by_family.csv
metrics/r08_3_h3_fold_unseen_state_spread_by_family.csv
metrics/r08_3_h3_fold_dispersion_summary_by_family.csv
metrics/r08_3_h3_instrument_transfer_summary_by_family.csv
metrics/r08_3_h3_time_transfer_summary_by_family.csv
metrics/r08_3_h3_year_availability_and_positive_count_by_family.csv
metrics/r08_3_h3_decile_monotonicity_by_family_anchor.csv
metrics/r08_3_h3_concentration_summary_by_family.csv
metrics/r08_3_h5_diagnostic_oof_spread_by_family.csv
metrics/r08_3_h10_diagnostic_oof_spread_by_family.csv
metrics/r08_3_horizon_shape_summary_by_family.csv
metrics/r08_3_overlap_adjusted_confidence_summary_by_family.csv
metrics/r08_3_family_comparison_audit.csv
```

Decision artifacts:

```text
decision/r08_3_gate_inputs_by_family.csv
decision/r08_3_horizon_diagnostic_inputs_by_family.csv
decision/r08_3_per_family_final_decision_replay.csv
decision/r08_3_per_family_final_decision.csv
decision/r08_3_aggregate_final_decision_replay.csv
decision/r08_3_aggregate_final_decision.csv
```

Report and manifest:

```text
reports/r08_3_final_report.md
manifests/r08_3_artifact_hashes.json
manifests/r08_3_validation.json
```

All per-family audit, metric, and decision artifacts must include a `family` column.

## 25. Report Required Questions

The final report must answer:

1. R08.3 是否保持 diagnostic-only，且没有构造任何策略？
2. 是否同步验证了 `volume_surge_money_flow`、`volume_price_correlation`、`rank_ts_rank_structure` 三个 family？
3. 是否没有使用 `vwap_deviation` 作为 R08.3 primary family？
4. 是否把 signal frequency 固定为 daily close-observed？
5. 是否只把 H3 作为 primary horizon？
6. H5/H10 是否只作为 diagnostic labels？
7. daily signal panel 是否 PIT / as-of safe，且三个 family 共用同一 panel？
8. daily factor percentile 是否使用 D-1 之前的 252 日 reference distribution？
9. H3/H5/H10 self-relative labels 是否只使用 completed labels？
10. daily overlapping label 是否被显式控制？
11. H3 anchor offsets 是否全部可评价？
12. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？
13. direction 是否只来自 train years + seen folds + H3？
14. H5/H10 是否没有参与 direction、bucket edge、factor retention？
15. 每个 family 的 retained factor count 和 dropped factor list 是什么？
16. family scope reference count 是否发生变化？若发生变化，是否有 replayable explanation？
17. `rank_ts_rank_structure` 是否被明确标注 single-factor caveat？
18. 每个 family 的 validation H3 anchor-controlled spread 是否为正？
19. 每个 family 的 robustness H3 anchor-controlled spread 是否确认？
20. 每个 family 的 full daily readout 是否与 anchor-controlled readout 冲突？
21. 每个 family 的 validation / robustness H3 positive instrument share 是否达标？
22. 每个 family 的 H3 fold stability 是否达标？
23. 每个 family 的 H3 anchor stability 是否达标？
24. 每个 family 的 H3 monotonicity 是否达标？
25. 每个 family 的 H3 concentration 是否达标？
26. 每个 family 的 H5/H10 diagnostic spread、monotonicity、positive instrument share、diagnostic concentration 是什么？
27. 每个 family 的 horizon shape 是 short-lived、persistent、horizon-mismatch 还是 no-support？
28. 是否确认没有按 validation / robustness 选择 winning family？
29. per-family final decisions 是什么？
30. aggregate R08.3 final decision 是什么？
31. direction canonical sign 是否来自 H3 anchor-controlled train-seen stats，而不是 full daily overlapping stats？
32. train OOF anchor-controlled baseline 是否落盘并用于 non-deterioration replay？
33. 每个 family 是否存在 validation single-positive-year caveat？
34. 如果 daily spread / breadth 为正但 monotonicity / concentration 失败，是否标注 `daily_observation_spread_positive_but_cleanliness_failed_F`？
35. 是否允许写 strategy requirement？答案必须是 no。

## 26. Validation Requirements

Validator must check:

```text
required_artifacts_exist = true
primary_families_exactly_volume_surge_vpc_rank_ts = true
primary_horizon_only_H3 = true
diagnostic_horizons_only_H5_H10 = true
signal_frequency_daily = true
weekly_signal_panel_not_used_as_primary = true
shared_daily_panel_across_families = true
no_strategy_artifacts = true
no_top_fraction_selection = true
no_cross_family_score = true
no_family_winner_selection = true
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
family_specific_retained_factor_floors_checked = true
family_scope_uses_r06_executable_factor_list = true
family_scope_reference_count_change_flag_replayable = true
family_scope_reference_count_change_explanation_replayable = true
unexplained_family_scope_reference_count_change_blocks_support = true
rank_ts_single_factor_caveat_present = true
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
validation_single_positive_year_caveat_replayable = true
H5_H10_diagnostic_only = true
horizon_switching_forbidden = true
partial_instruments_horizon_specific = true
partial_instruments_excluded_from_sample_gate_by_horizon = true
partial_instruments_excluded_from_positive_instrument_share_by_horizon = true
concentration_formula_replayable = true
anchor_concentration_escalation_rule_exists = true
H5_H10_diagnostic_pass_replayable = true
H5_H10_diagnostic_concentration_reported = true
daily_observation_cleanliness_failure_flag_exists = true
per_family_decision_replay_first_match = true
aggregate_decision_replay_first_match = true
aggregate_decision_does_not_hide_family_decisions = true
authorized_strategy_requirement_false = true
```

Validation failure must block final decision.

## 27. Interpretation Boundary

R08.3 has four strict interpretation boundaries.

### 27.1 Per-Family H3 Support Is Not Strategy Authorization

Even if a family returns:

```text
r08_3_daily_family_h3_transferability_diagnostic_supported
```

the only allowed conclusion is:

```text
daily-observed family F H3 deserves a confirmatory diagnostic.
```

It cannot conclude:

```text
family F H3 can be traded.
```

### 27.2 H5/H10 Positive Does Not Rescue H3

If H3 fails but H5 or H10 is positive:

```text
per_family_final_decision may be:
  r08_3_family_horizon_mismatch_diagnostic_only
```

It cannot become:

```text
r08_3_daily_family_h3_transferability_diagnostic_supported
```

### 27.3 Overlap-Controlled Evidence Dominates Full Daily Evidence

If full daily spread is positive but anchor-controlled spread fails:

```text
R08.3 must not claim support for that family.
```

Full daily readout can describe the point estimate, but overlap-controlled readout controls the primary conclusion.

### 27.4 Synchronous Testing Does Not Authorize Family Selection

If one family looks better than the others:

```text
R08.3 may report the difference.
```

It must not:

```text
select that family for strategy;
drop weaker families from the report;
combine families into a new primary score;
recommend production deployment.
```

## 28. Minimal Implementation Scope

Minimal R08.3 implementation:

```text
primary families:
  volume_surge_money_flow
  volume_price_correlation
  rank_ts_rank_structure

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

primary readout per family:
  H3 anchor-controlled OOF spread
  H3 positive instrument share
  H3 fold stability
  H3 anchor stability
  H3 decile monotonicity
  H3 concentration
```

One-sentence summary:

```text
R08.3 tests whether daily observation reveals transferable H3
single-stock state relations in the pre-registered volume/rank families,
while using H5/H10 only to diagnose horizon shape and never to rescue H3.
```
