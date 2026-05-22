# EP5 Requirement 05: GTJA191 Train-only Factor Engineering Residual Feasibility V0

## 1. Requirement Metadata

requirement_id: `ep5_r05_gtja191_train_only_factor_engineering_residual_feasibility_v0`

short_name: `r05_gtja191_factor_engineering_residual_feasibility_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-22`

primary_output_namespace: `ep5/outputs/r05_gtja191_train_only_factor_engineering_residual_feasibility_v0/`

upstream_requirement:

- `ep5/requirement_04_gtja191_short_horizon_residual_composite_feasibility_v0.md`

upstream_report:

- `ep5/outputs/r04_gtja191_short_horizon_residual_composite_feasibility_v0/reports/r04_final_report.md`

upstream_final_decision:

```text
r04_no_gtja191_residual_composite_support
```

R05 inherits R04's PIT universe, split, execution, cost, H5/H10/H20 natural exits, matched comparator, and nonselected baseline discipline.

R05 does not inherit R04's core composite:

```text
train-only direction sign + all active factors equal weight
```

R04 already evaluated that raw equal-weight composite under the current EP5 contract and found no support. R05 changes the research question before the run. It is not allowed to rescue R04 by tuning R04's outputs.

## 2. Upstream Motivation

R04's final report concluded that the GTJA191 train-only direction equal-weight composite has no sufficient local support.

Key R04 H10 validation evidence:

```text
complete_event_count = 4,271
sample_status = pass
mean_net_return = -1.3210%
median_net_return = -1.8517%
loss_rate = 61.20%
mean_matched_delta_return = +0.1332%
median_matched_delta_return = -0.4001%
2022 mean_matched_delta_return = +0.6295%
2023 mean_matched_delta_return = -0.3900%
mean_baseline_lift = +0.0614%
median_baseline_lift = -0.1028%
baseline_lift_gate = false
final_decision = r04_no_gtja191_residual_composite_support
```

R04's useful observation is narrow:

```text
The raw GTJA191 equal-weight composite may contain weak ranking traces,
but they do not survive as a stable H10 residual edge or long-only alpha.
```

Therefore R05 must not continue by:

- changing top fraction based on R04 validation;
- changing the primary horizon based on R04 validation;
- selecting the best validation year, market state, bucket, or score bucket;
- keeping validation-positive factors;
- adding RS20, rebound, volatility, regime, or right-tail filters;
- using a model to mine validation performance.

The valid R05 motivation is:

```text
Use only train split information to denoise, neutralize, de-redundant,
and stabilize GTJA191 factors before forming a new frozen composite.

Then test whether Alpha191 as a feature library still contains a stable
H10 residual ranking edge under the unchanged EP5 validation contract.
```

## 3. Core Question

R05 asks:

```text
Within the current PIT mcap500 mainboard universe,
weekly close-observed signal cadence,
next-open execution,
110 bps round-trip cost,
fixed H5 / H10 / H20 natural exits,
matched comparator discipline,
and same-day nonselected baseline discipline,

can a train-only engineered GTJA191 feature-library composite produce
a stable H10 residual ranking edge?
```

The primary target is:

```text
H10 matched-delta residual edge
```

Long-only pass is allowed only when both absolute and relative gates pass. A residual-only pass cannot be reported as long-only alpha.

## 4. Non-Goals

R05 is not:

- R04.1;
- original Alpha191 report replication;
- validation-driven factor selection;
- top-fraction grid search;
- horizon grid search;
- score-bucket selection;
- market-state or beta-regime filter discovery;
- LGBM, neural network, linear model, PCA, autoencoder, or optimizer research;
- production strategy work.

R05 must not:

1. Use validation or robustness to select factors.
2. Use validation or robustness to choose factor direction.
3. Use validation or robustness to choose factor weights.
4. Use validation or robustness to choose clusters.
5. Tune top fraction based on validation.
6. Tune H5/H10/H20 primary horizon based on validation.
7. Add validation-discovered filters such as RS20, rebound, volatility, money repair, market state, or beta bucket.
8. Add stop-loss, take-profit, re-entry, layered exit, or portfolio optimizer logic.
9. Use right-tail or big-winner readouts as pass/fail gates.
10. Treat audit-only decomposition as decision authority.

R05's discipline is:

```text
train engineers;
validation evaluates;
robustness confirms or rejects.
```

## 5. Canonical Units

Only one R05 unit has final-decision authority.

### 5.1 Primary Unit

canonical_unit_id:

```text
r05_gtja191_train_stable_cluster_neutralized_composite_v0
```

Meaning:

- compute local GTJA191 factors as-of each signal date;
- apply the same factor implementation and as-of-safety contract as R04 unless explicitly tightened here;
- create raw rank-normalized factors;
- create industry / liquidity / beta neutralized rank factors;
- learn train-only H10 matched-delta RankIC by factor and year;
- filter factors using frozen train-only stability rules;
- cluster retained factors using train-only factor correlation;
- select cluster representatives using train-only quality score;
- assign factor direction using train-only mean RankIC sign;
- form a cluster-level equal-weight composite;
- select weekly top 20% by final score;
- execute fixed H5/H10/H20 natural exits with inherited EP5 cost and execution rules.

### 5.2 Baseline Unit

baseline_unit_id:

```text
r05_weekly_nonselected_liquid_baseline_v0
```

Meaning:

- same signal date D;
- same PIT universe and eligibility filters;
- same executable entry / exit / cost rules;
- all eligible stocks not selected by the top-20% primary composite;
- used only for date-level lift and market-wide rebound / beta differentiation.

The baseline cannot create a positive decision by itself.

### 5.3 Audit-Only Units

Allowed audit-only outputs:

- raw rank factor composite readout;
- neutralized rank factor readout;
- rejected-factor readout by rejection reason;
- factor cluster decomposition;
- score bucket readout;
- industry / liquidity / beta / market-state decomposition;
- right-tail / big-winner readout.

Audit-only units cannot override final-decision priority.

## 6. Data Contract

R05 inherits the EP5 local data boundary. E05 must not fetch market data online during the run.

Required local inputs:

- local PIT Qlib provider used by R01/R02/R03/R04;
- PIT mcap500 mainboard universe;
- PIT industry membership;
- trading calendar;
- `SH000300` index `open` and `close`;
- local GTJA191 source file or a byte-for-byte documented local copy.

Required stock fields:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `money`
- `vwap = money / volume`

If PIT universe, split, raw fields, factor registry, execution, cost, or comparator contracts cannot be reproduced, the run must stop as:

```text
r05_blocked_data_or_execution_contract
```

## 7. Split Contract

R05 inherits the frozen EP5 split:

```text
train:      2017-07-04 through 2021-12-31
validation: 2022-01-01 through 2023-12-31
robustness: 2024-01-01 through 2025-12-31
```

Train is allowed only for:

- formula feasibility and coverage checks;
- neutralization design using fixed fields only;
- H10 matched-delta labels for factor RankIC;
- factor stability selection;
- factor correlation clustering;
- cluster representative selection;
- factor direction signs;
- immutable manifests and audit records.

Train labels must be split-pure. A train signal date can enter factor RankIC learning only if its entry execution and natural H10 exit execution both occur on or before `2021-12-31`. Any train signal date whose H10 label would require validation or robustness prices must be excluded from RankIC learning and audited as:

```text
train_label_purged_cross_split
```

H5 and H20 labels must not be used for train-only factor engineering.

Validation is allowed only for:

- applying the frozen R05 factor-engineered composite;
- pass/fail evaluation;
- decomposition readouts that cannot change the run.

Robustness is allowed only for:

- applying the same frozen composite;
- confirming or rejecting validation-led evidence.

## 8. Execution Contract

R05 inherits R04 execution:

```text
signal_date_rule: close_observed_iso_week_last_trading_day
entry_execution_rule: first_executable_next_open
natural_exit_rule: open_after_h_trading_days
horizons: H5, H10, H20
primary_horizon: H10
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
max_entry_execution_lag_trading_days = 5
max_exit_execution_lag_trading_days = 5
```

R05 must not add stop-loss, take-profit, early exit, re-entry, position sizing, cash allocation, or portfolio optimizer logic.

## 9. Factor Registry and Feasibility

R05 starts from the local GTJA191 factor registry.

Allowed implementation exclusions:

- formula implementation failed;
- not as-of safe;
- missing required field;
- insufficient train coverage;
- constant or degenerate train values;
- lookback exceeds allowed window.

Frozen registry constants:

```text
max_lookback_trading_days = 252
min_included_factor_count = 120
min_train_factor_coverage_date_count = 150
min_train_factor_cross_section_count_per_date = 100
min_instrument_valid_cluster_share = 0.60
```

If fewer than `min_included_factor_count` factors are included before train-only engineering, final decision must be:

```text
r05_factor_library_not_implementable_blocked
```

Implementation status must be audited for all 191 source factors. Rejected formulas must remain visible in the registry; E05 must not silently drop them.

## 10. Eligibility and Selection Contract

For each signal date D, an instrument is eligible for score ranking only if all of the following hold as-of D:

- instrument is a PIT universe member;
- instrument is mainboard under inherited EP5 board classification;
- `avg_money20_D >= 50,000,000`;
- `open_D`, `high_D`, `low_D`, `close_D`, `volume_D`, `money_D`, and `vwap_D` exist;
- `close_D > 0`;
- `volume_D > 0`;
- `money_D > 0`;
- `vwap_D` is finite;
- at least `min_instrument_valid_cluster_share` of selected representative cluster scores are finite after all factor computation and neutralization steps.

`min_instrument_valid_cluster_share` is evaluated after representative factors are selected. Each stock-week needs finite neutralized residual values for at least 60% of representative clusters; merely having 60% of pre-cluster factors available is not sufficient.

R05 inherits the R04 small-universe contract:

```text
small_universe_contract_accepted = true
min_eligible_cross_section_count = 175
selected_top_fraction = 0.20
min_selected_count_per_signal_date = 35
min_nonselected_count_per_signal_date = 140
min_complete_nonselected_baseline_count_per_date_horizon = 120
```

If a weekly signal date fails the revised floors, it is excluded from event creation and must be audited as one of:

```text
blocked_insufficient_eligible_cross_section
blocked_insufficient_selected_or_baseline_count
```

Selection is deterministic:

```text
selected_count_target(D) = ceil(selected_top_fraction * eligible_count(D))
selected = first selected_count_target(D) instruments after sorting by:
  score_final desc
  instrument_id asc
```

R05 must not test alternative top fractions.

## 11. Factor Construction

For each included GTJA191 factor and each signal date D:

1. Compute raw factor values using only data available on or before D.
2. Replace nonfinite values with missing.
3. Winsorize finite raw values cross-sectionally at the 1st and 99th percentiles.
4. Convert winsorized values to average-rank percentile within the eligible cross-section.
5. Normalize rank as:

```text
raw_rank_factor_i = rank_pct_i - 0.5
```

This produces values approximately in `[-0.5, +0.5]`.

## 12. Cross-sectional Neutralization

R05 primary uses neutralized rank factors.

For each signal date D and factor i:

1. Start from `raw_rank_factor_i(D, stock)`.
2. Regress cross-sectionally against:
   - industry dummies;
   - liquidity quintile dummies;
   - beta bucket dummies;
   - intercept.
3. Use the residual as `factor_residual_i(D, stock)`.
4. Rank-normalize residuals cross-sectionally:

```text
neutralized_rank_factor_i = rank_pct(factor_residual_i) - 0.5
```

Rules:

- Neutralization uses the same field definitions in train, validation, and robustness.
- Neutralization does not use return labels.
- Industry, liquidity, and beta category values are constructed as-of each signal date from PIT fields only. Missing category values must be mapped to an explicit `__missing__` bucket and audited.
- Liquidity quintiles and beta buckets are date-local cross-sectional buckets with deterministic average-rank tie handling; they are not fit on validation or robustness returns.
- The neutralization design matrix is date-local. For each dummy family, drop the lexicographically first non-empty bucket after sorting bucket labels, then include the intercept.
- If a signal date has an underdetermined design matrix or fewer than 100 usable instruments for a factor, that factor-date is missing and must be audited.
- Raw rank factors are retained only for audit.

Required neutralization audit:

- per-factor usable date count before and after neutralization;
- per-factor missing share before and after neutralization;
- per-date neutralization failure count;
- cross-sectional mean and standard deviation before and after neutralization;
- residual exposure check by industry / liquidity / beta.

## 13. Train-only H10 Labels

R05 factor engineering labels use train split only.

For each train candidate instrument and signal date:

```text
candidate_h10_net_return =
  H10 net return of this eligible candidate using the same
  entry, exit, and cost contract as selected events

label = candidate_h10_net_return
        - H10 matched comparator net return
```

Because the final selected set does not exist before factor engineering, the train matched comparator pool is the same-date eligible universe excluding the target instrument, using inherited industry / liquidity / beta matching rules.

The label is available only when both the candidate event and its matched comparator event are complete inside the train split. Missing or cross-split labels must be excluded from RankIC and counted in `r05_train_rankic_by_factor_year.csv`.

Train label purge audit must report:

```text
total_train_signal_date_count
train_label_purged_cross_split_signal_date_count
train_label_unpurged_signal_date_share
```

These fields must be stored in `audit/r05_train_label_purge_audit.csv`.

The frozen floor is:

```text
min_train_label_unpurged_signal_date_share = 0.90
```

If `train_label_unpurged_signal_date_share < min_train_label_unpurged_signal_date_share`, final decision must be `r05_blocked_data_or_execution_contract`.

After the primary composite is frozen, E05 must run an audit-only train comparator consistency check. It recomputes train H10 labels using the validation-style nonselected-preferred comparator, where train selected / nonselected membership is defined by the frozen primary composite on train dates. This audit must not change factor inclusion, direction, clustering, representative selection, or score construction.

R05 must not use validation or robustness labels for:

- factor inclusion;
- factor direction;
- stability selection;
- cluster construction;
- representative selection;
- score construction.

## 14. Train-only RankIC Stability Selection

R05 primary stability IC uses the raw rank factor against the matched-delta residual label:

```text
rankIC_i(D) = SpearmanCorr(
  raw_rank_factor_i(D, eligible stocks),
  H10 matched_delta_label(D, eligible stocks)
)
```

This avoids double neutralization: the label side carries the industry / liquidity / beta matched-delta residual meaning, while the primary feature-side IC uses the raw rank signal. The final score in §16 still uses neutralized representative factors to reduce style and beta exposure at selection time.

For audit only, E05 must also compute:

```text
neutralized_rankIC_i(D) = SpearmanCorr(
  neutralized_rank_factor_i(D, eligible stocks),
  H10 matched_delta_label(D, eligible stocks)
)
```

The audit must report whether the raw and neutralized train IC signs agree for each selected representative. Audit ICs cannot change the primary stability decision.

Representative eligibility uses this audit as a hard consistency guard:

```text
neutralized_mean_train_rankIC_i =
  mean_year neutralized_yearly_rankIC_i(year)

raw_neutralized_rankIC_sign_agree_i =
  sign(mean_train_rankIC_i) = sign(neutralized_mean_train_rankIC_i)
```

A factor can become a cluster representative only if:

```text
neutralized_mean_train_rankIC_i is finite
neutralized_mean_train_rankIC_i != 0
raw_neutralized_rankIC_sign_agree_i = true
```

This prevents R05 from learning direction on the raw rank factor and then applying the opposite direction after neutralized scoring. A factor may pass stability selection while failing representative eligibility; it remains in the cluster audit but cannot be selected as the representative.

Then compute yearly summaries by calendar year:

```text
yearly_rankIC_i(year) = mean_D rankIC_i(D)
mean_train_rankIC_i = mean_year yearly_rankIC_i(year)
ic_vol_i = std_year yearly_rankIC_i(year)
positive_year_count_i
negative_year_count_i
same_sign_year_count_i
sign_consistency_i = same_sign_year_count_i / valid_train_year_count_i
single_year_ic_contribution_share_i =
  max_year abs(yearly_rankIC_i(year)) /
  sum_year abs(yearly_rankIC_i(year))
```

`mean_train_rankIC_i` is defined as `mean_year(yearly_rankIC_i)`. This intentionally differs from a pure date-mean IC when train years have different numbers of usable signal dates; it is an R05 design choice, not an R04 implementation bug.

Frozen stability constants:

```text
min_valid_train_year_count = 4
min_abs_mean_train_rankIC = 0.0050
min_same_sign_year_count = 3
max_single_year_ic_contribution_share = 0.60
min_stability_selected_factor_count = 20
```

A factor passes stability selection only if:

```text
valid_train_year_count >= min_valid_train_year_count
abs(mean_train_rankIC_i) >= min_abs_mean_train_rankIC
same_sign_year_count_i >= min_same_sign_year_count
single_year_ic_contribution_share_i <= max_single_year_ic_contribution_share
```

If fewer than `min_stability_selected_factor_count` factors pass, final decision must be:

```text
r05_factor_stability_selection_not_viable_blocked
```

## 15. Train-only Redundancy Clustering

R05 must reduce redundant factor voting.

For stability-selected factors only, compute train-only factor correlation:

```text
corr_ij = SpearmanCorr(
  neutralized_rank_factor_i(D, stock),
  neutralized_rank_factor_j(D, stock)
)
```

The correlation is computed over the stacked train panel of `(signal_date, instrument)` observations where both factors are finite. Using Spearman here keeps the redundancy metric aligned with the RankIC family and avoids relying on Pearson behavior under unequal missingness patterns.

Frozen clustering constants:

```text
cluster_abs_corr_threshold = 0.70
min_pairwise_factor_corr_observation_count = 5000
max_representatives_per_cluster = 1
min_cluster_count = 10
max_cluster_top_factor_share = 0.20
```

Pairwise eligibility:

```text
pair_eligible_ij =
  finite_pair_observation_count_ij >= min_pairwise_factor_corr_observation_count
```

A factor pair with fewer than `min_pairwise_factor_corr_observation_count` finite paired train observations is ineligible for clustering similarity and must be audited as `insufficient_pairwise_factor_overlap`.

V0 clustering algorithm is fixed as complete-link agglomerative clustering:

```text
1. Start with one cluster per stability-selected factor.
2. For any two clusters A and B, define:
     complete_link_similarity(A, B)
       = min abs(corr_ij)
         for all eligible factor pairs i in A, j in B.
3. Pairs with any ineligible i,j pair cannot be merged.
4. Repeatedly merge the cluster pair with the highest
   complete_link_similarity when it is >= cluster_abs_corr_threshold.
5. Ties are broken by:
     a. higher complete_link_similarity;
     b. smaller min factor_id across the merged pair;
     c. smaller max factor_id across the merged pair.
6. Stop when no cluster pair satisfies the threshold.
7. Cluster IDs are assigned by the ascending smallest factor_id in each final cluster.
```

The algorithm must use only train factor values. Complete-link is required in V0 to prevent single-link chain merging of weakly related factor families.

Cluster source-factor concentration:

```text
cluster_source_factor_share_c =
  stability_selected_factor_count_in_cluster_c
  / total_stability_selected_factor_count
```

If any cluster has `cluster_source_factor_share_c > max_cluster_top_factor_share`, the cluster structure is too concentrated and final decision must be `r05_factor_cluster_structure_not_viable_blocked`.

Factor quality score:

```text
factor_quality_score_i =
  abs(mean_train_rankIC_i)
  * sign_consistency_i
  / (1 + ic_vol_i)
```

Within each cluster, choose the representative factor from representative-eligible factors only by:

1. higher `factor_quality_score_i`;
2. higher `abs(mean_train_rankIC_i)`;
3. lower missing share after neutralization;
4. `factor_id` ascending.

If any cluster has no representative-eligible factor, or fewer than `min_cluster_count` clusters remain, final decision must be:

```text
r05_factor_cluster_structure_not_viable_blocked
```

## 16. Composite Score

For each selected representative factor i:

```text
direction_i = sign(mean_train_rankIC_i)
```

Factors with zero direction cannot be representatives.

For each cluster c:

```text
cluster_score_c(D, stock) =
  direction_rep(c) * neutralized_rank_factor_rep(c)(D, stock)
```

Primary score:

```text
score_final(D, stock) = mean_over_clusters(cluster_score_c(D, stock))
```

Rules:

- Each cluster has equal weight.
- Each cluster has exactly one representative in V0.
- Missing cluster scores are ignored only if the instrument still satisfies `min_instrument_valid_cluster_share`.
- R05 must not use train IC magnitude as a continuous weight in the primary score.
- Raw equal-weight R04-style score may be reported only as audit.

## 17. Comparator and Baseline Contract

R05 inherits the R04 matched-comparator contract.

Matched comparator must be same-date and matched by industry / liquidity / beta according to the existing EP5 comparator implementation.

For validation and robustness outcome evaluation, matched comparator should prefer same-day nonselected baseline constituents when available.

Baseline lift:

```text
selected_equal_weight_net_return(D, H)
nonselected_baseline_equal_weight_net_return(D, H)
baseline_lift(D, H)
  = selected_equal_weight_net_return(D, H)
  - nonselected_baseline_equal_weight_net_return(D, H)
```

Baseline cannot create a positive decision by itself, but it can block a relative or long-only claim.

## 18. Gate Definitions

Unless explicitly stated otherwise, gate functions are parameterized as `(split, H)`. In the H10 validation decision path, shorthand such as `sample_status(H10)` means `sample_status(validation, H10)`.

### 18.1 Sample Gate

Frozen sample constants:

```text
sample_pass_min_complete_event_count = 3000
sample_pass_min_complete_event_share = 0.90
sample_block_min_complete_event_count = 1500
sample_pass_min_decision_observation_date_count = 70
sample_pass_min_year_complete_event_count = 1000
sample_pass_min_year_decision_observation_date_count = 30
sample_limited_min_decision_observation_date_count = 50
```

`sample_status(H10) = pass` requires:

```text
complete_event_count >= sample_pass_min_complete_event_count
complete_event_share >= sample_pass_min_complete_event_share
decision_observation_date_count >= sample_pass_min_decision_observation_date_count
min_year_complete_event_count >= sample_pass_min_year_complete_event_count
min_year_decision_observation_date_count >= sample_pass_min_year_decision_observation_date_count
```

Sample status values:

- `pass`
- `sample_limited_lead`
- `blocked_insufficient_sample`
- `blocked_insufficient_execution_completeness`
- `blocked_insufficient_year_coverage_sample`

Only `pass` can support a primary H10 positive decision. The three `blocked_*` statuses mean the primary H10 validation sample is not economically adjudicable. They must not fall through to `r05_no_gtja191_factor_engineering_support`.

The first matching status in the following order must be assigned:

```text
pass:
  all sample gate conditions hold

blocked_insufficient_sample:
  complete_event_count < sample_block_min_complete_event_count

blocked_insufficient_execution_completeness:
  complete_event_count >= sample_block_min_complete_event_count
  AND complete_event_share < sample_pass_min_complete_event_share

sample_limited_lead:
  complete_event_count >= sample_block_min_complete_event_count
  AND complete_event_count < sample_pass_min_complete_event_count
  AND complete_event_share >= sample_pass_min_complete_event_share
  AND decision_observation_date_count >= sample_limited_min_decision_observation_date_count

blocked_insufficient_year_coverage_sample:
  complete_event_count >= sample_block_min_complete_event_count
  AND complete_event_share >= sample_pass_min_complete_event_share
  AND the pass condition does not hold
  AND the sample_limited_lead condition does not hold
```

### 18.2 Concentration and Active Overlap Gates

R05 tightens selected-week recurrence because R04 found repeated selection risk.

Concentration gate passes only if:

```text
top1_instrument_event_share <= 0.02
top5_instrument_event_share <= 0.08
top1_instrument_selected_week_share <= 0.50
top5_instrument_selected_week_share <= 0.80
top1_industry_event_share <= 0.25
top1_observation_date_event_share <= 0.03
top5_observation_date_event_share <= 0.15
top1_observation_date_profit_contribution_share <= 0.15
fallback_comparator_share <= 0.30
```

`top1_instrument_selected_week_share` and `top5_instrument_selected_week_share` must be computed from selected weeks, not from event rows alone:

```text
instrument_selected_week_share(inst, split)
  = count_unique_signal_dates_where_inst_selected / selected_signal_date_count(split)
```

Active overlap gate passes only if:

```text
active_overlap_median_max = 0.90
active_overlap_p90_max = 0.97
active_overlap_min_effective_independent_event_count = 1000

median_active_overlap_share_H <= active_overlap_median_max
p90_active_overlap_share_H <= active_overlap_p90_max
effective_independent_event_count_H >= active_overlap_min_effective_independent_event_count
```

### 18.3 Date Independence Gate

Date independence passes only if:

```text
decision_observation_date_count >= 70
min_year_decision_observation_date_count >= 30
top1_observation_date_event_share <= 0.03
top5_observation_date_event_share <= 0.15
top1_observation_date_profit_contribution_share <= 0.15
```

### 18.4 Relative Positive Gate

R05's primary gate is `relative_positive(H10)`.

It is true only if:

```text
mean_matched_delta_return > 0
median_matched_delta_return >= 0
every non-empty validation calendar-year mean_matched_delta_return >= -0.0025
fallback_comparator_share <= 0.30
matched_loss_rate_delta <= -0.03
```

This is stricter than R04's relative gate because R05's purpose is explicitly residual ranking support after train-only engineering.

### 18.5 Baseline Lift Gate

`baseline_lift_evaluable(split, H)` is true only if:

```text
baseline_lift_min_comparable_observation_date_count = 70
baseline_lift_min_year_comparable_observation_date_count = 30
baseline_comparable_observation_date_count >= baseline_lift_min_comparable_observation_date_count
min_year_baseline_comparable_observation_date_count >= baseline_lift_min_year_comparable_observation_date_count
```

`baseline_lift_gate(split, H)` is true only if:

```text
baseline_lift_evaluable(split, H) = true
mean_baseline_lift > 0
median_baseline_lift >= 0
every non-empty split calendar-year mean_baseline_lift >= -0.0025
```

In the H10 validation decision path, shorthand `baseline_lift_evaluable(H10)` and `baseline_lift_gate(H10)` mean `baseline_lift_evaluable(validation, H10)` and `baseline_lift_gate(validation, H10)`.

### 18.6 Absolute Positive Gate

`absolute_positive(H10)` is true only if:

```text
mean_net_return > 0
median_net_return >= -0.0025
p10_net_return >= -0.08
loss_rate <= 0.55
every non-empty validation calendar-year mean_net_return >= -0.0025
```

Absolute positive is required for long-only support, but not for residual-only support.

### 18.7 Multi-Comparator Relative Status

`multi_comparator_relative_status(H10)` must be one of:

- `stable`
- `unstable`
- `unavailable`

It is `stable` only if:

```text
relative_positive(H10) = true
fallback_comparator_share <= 0.30
industry_matched_delta_mean > 0
liquidity_matched_delta_mean > 0
beta_matched_delta_mean > 0
```

It is `unavailable` if any required comparator family is unavailable.

Otherwise it is `unstable`.

### 18.8 H10 Validated Pass and Horizon Pass

`h10_residual_validated_pass` is true only if:

```text
sample_status(H10) = pass
concentration_gate(H10) = true
active_overlap_gate(H10) = true
date_independence_gate(H10) = true
relative_positive(H10) = true
```

`h10_long_only_validated_pass` is true only if:

```text
h10_residual_validated_pass = true
absolute_positive(H10) = true
```

`horizon_pass(H)` for H5 or H20 requires:

```text
sample_status(H) = pass
concentration_gate(H) = true
active_overlap_gate(H) = true
date_independence_gate(H) = true
relative_positive(H) = true
```

Rule 16 in §20 must read horizon-specific lead as:

```text
(horizon_pass(H5) = true OR horizon_pass(H20) = true)
AND h10_residual_validated_pass = false
```

### 18.9 Robustness Confirmed

`robustness_confirmed(H10)` is true only if robustness split H10 satisfies:

```text
robustness_min_complete_event_count = 3000
robustness_min_complete_event_share = 0.90
robustness_min_decision_observation_date_count = 70
robustness_min_year_complete_event_count = 1000
robustness_min_year_decision_observation_date_count = 30

complete_event_count >= robustness_min_complete_event_count
complete_event_share >= robustness_min_complete_event_share
decision_observation_date_count >= robustness_min_decision_observation_date_count
min_year_complete_event_count >= robustness_min_year_complete_event_count
min_year_decision_observation_date_count >= robustness_min_year_decision_observation_date_count
concentration_gate(robustness, H10) = true
active_overlap_gate(robustness, H10) = true
mean_matched_delta_return >= -0.0025
median_matched_delta_return >= -0.005
mean_net_return >= -0.005
fallback_comparator_share <= 0.30
baseline_lift_evaluable(robustness, H10) = true
mean_baseline_lift >= -0.0025
median_baseline_lift >= -0.005
every non-empty robustness calendar-year mean_baseline_lift >= -0.005
```

Robustness is a non-deterioration gate, not a second validation pass.

### 18.10 Adjacent Horizon Clean

`adjacent_horizon_clean` is true only if both H5 and H20 validation are evaluable and each adjacent horizon H satisfies:

```text
adjacent_min_complete_event_count = 1500
adjacent_min_decision_observation_date_count = 50
complete_event_count >= adjacent_min_complete_event_count
decision_observation_date_count >= adjacent_min_decision_observation_date_count
active_overlap_gate(validation, H) = true
mean_matched_delta_return >= -0.005
fallback_comparator_share <= 0.30
```

H5 and H20 cannot create the primary H10 positive decision. They can only confirm, block, or produce a horizon-specific lead label.

## 19. Interpretation Boundary

R05's interpretation table:

| H10 validation quadrant | Meaning | Allowed next step |
| --- | --- | --- |
| `absolute_true__relative_true` | Factor-engineered composite has both long-only and residual support. | Continue only if baseline, robustness, adjacent horizons, and concentration are clean. |
| `absolute_false__relative_true` | Residual edge exists but not direct long-only support. | Next step can only be hedged / relative feasibility. |
| `absolute_true__relative_false` | Likely beta, regime, or style exposure without stock-selection support. | Do not pursue stock-selection deployment. |
| `absolute_false__relative_false` | No residual support under current engineered feature-library contract. | Pause GTJA191 EP5 residual-ranking direction unless a later requirement changes the research question materially. |

The `absolute_false__relative_true` quadrant must not be reported as a long-only alpha pass.

R05's relative gate is deliberately stricter than R04's relative gate. It requires mean, median, loss-rate improvement, and yearly non-deterioration to align; therefore `absolute_false__relative_true` should be expected to occur less often in R05. This is a design choice, not a reason to loosen thresholds after seeing validation.

## 20. Final Decision Priority

Final decision uses first-match priority. Later rules cannot override earlier rules.

Allowed `final_decision` values:

- `r05_blocked_data_or_execution_contract`
- `r05_factor_library_not_implementable_blocked`
- `r05_factor_stability_selection_not_viable_blocked`
- `r05_factor_cluster_structure_not_viable_blocked`
- `r05_primary_sample_not_evaluable_blocked`
- `r05_gtja191_factor_engineered_long_only_and_residual_supported`
- `r05_gtja191_factor_engineered_residual_edge_only_hedged_required`
- `r05_baseline_not_evaluable_validation_lead`
- `r05_comparator_unavailable_validation_lead`
- `r05_absolute_only_baseline_lift_no_relative_pass`
- `r05_beta_or_style_exposure_only_no_stock_selection_pass`
- `r05_unstable_validation_only_lead`
- `r05_unstable_horizon_shape_no_search_allowed`
- `r05_adjacent_horizon_not_evaluable_validation_lead`
- `r05_horizon_specific_lead_only_no_search_allowed`
- `r05_sample_limited_primary_lead_only`
- `r05_no_gtja191_factor_engineering_support`

Rules:

1. If PIT universe, split, raw fields, factor registry, execution, cost, train label purity, or comparator contract cannot be reproduced exactly, or if `train_label_unpurged_signal_date_share < min_train_label_unpurged_signal_date_share`, output `r05_blocked_data_or_execution_contract`.

2. If included factor count is below `min_included_factor_count`, output `r05_factor_library_not_implementable_blocked`.

3. If train-only stability-selected factor count is below `min_stability_selected_factor_count`, output `r05_factor_stability_selection_not_viable_blocked`.

4. If cluster count is below `min_cluster_count`, any cluster breaches `max_cluster_top_factor_share`, or any cluster has no representative-eligible factor, output `r05_factor_cluster_structure_not_viable_blocked`.

5. If `sample_status(H10)` is one of `blocked_insufficient_sample`, `blocked_insufficient_execution_completeness`, or `blocked_insufficient_year_coverage_sample`, output `r05_primary_sample_not_evaluable_blocked`.

6. If `h10_long_only_validated_pass = true`, `baseline_lift_gate(H10) = true`, `multi_comparator_relative_status(H10) = stable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r05_gtja191_factor_engineered_long_only_and_residual_supported`.

7. If `h10_residual_validated_pass = true`, `absolute_positive(H10) = false`, `baseline_lift_gate(H10) = true`, `multi_comparator_relative_status(H10) = stable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r05_gtja191_factor_engineered_residual_edge_only_hedged_required`.

8. If `h10_residual_validated_pass = true`, `multi_comparator_relative_status(H10) = unavailable`, output `r05_comparator_unavailable_validation_lead`.

9. If `h10_residual_validated_pass = true`, `multi_comparator_relative_status(H10) != unavailable`, `baseline_lift_evaluable(H10) = false`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r05_baseline_not_evaluable_validation_lead`.

10. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = true`, `relative_positive(H10) = false`, `baseline_lift_gate(H10) = true`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r05_absolute_only_baseline_lift_no_relative_pass`.

11. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = true`, `relative_positive(H10) = false`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r05_beta_or_style_exposure_only_no_stock_selection_pass`.

12. If H10 sample status is `sample_limited_lead` and either absolute or relative evidence is positive, output `r05_sample_limited_primary_lead_only`.

13. If `sample_status(H10) = pass`, and H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, but robustness is not confirmed, output `r05_unstable_validation_only_lead`.

14. If `sample_status(H10) = pass`, and H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, but either H5 or H20 is not evaluable, output `r05_adjacent_horizon_not_evaluable_validation_lead`.

15. If `sample_status(H10) = pass`, and H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, and both H5 and H20 are evaluable, but `adjacent_horizon_clean = false`, output `r05_unstable_horizon_shape_no_search_allowed`.

16. If `(horizon_pass(H5) = true OR horizon_pass(H20) = true)` and `h10_residual_validated_pass = false`, output `r05_horizon_specific_lead_only_no_search_allowed`.

17. Otherwise output `r05_no_gtja191_factor_engineering_support`.

## 21. Required Artifacts

E05 must produce at least:

```text
audit/r05_run_manifest.json
audit/r05_input_data_audit.csv
audit/r05_factor_registry.csv
audit/r05_factor_neutralization_audit.csv
audit/r05_train_label_purge_audit.csv
audit/r05_train_rankic_by_factor_year.csv
audit/r05_train_comparator_consistency_audit.csv
audit/r05_factor_stability_selection_audit.csv
audit/r05_factor_cluster_audit.csv
audit/r05_selected_factor_manifest.csv
audit/r05_score_cross_section_audit.csv
audit/r05_active_overlap_audit.csv
audit/r05_comparator_quality_audit.csv
audit/r05_baseline_comparison_audit.csv
audit/r05_validation_gate_audit.csv

events/r05_selected_event_panel.csv
events/r05_execution_event_panel.csv
events/r05_matched_comparator_panel.csv
events/r05_nonselected_baseline_candidates.csv
events/r05_nonselected_baseline_panel.csv

metrics/r05_split_horizon_summary.csv
metrics/r05_year_horizon_summary.csv
metrics/r05_baseline_lift_summary.csv
metrics/r05_date_weighted_summary.csv
metrics/r05_score_bucket_readout.csv
metrics/r05_decomposition_summary.csv
metrics/r05_right_tail_readout.csv

decision/r05_gate_inputs.csv
decision/r05_final_decision_inputs.csv
decision/r05_final_decision_replay.csv

reports/r05_final_report.md
manifests/r05_validation.json
manifests/r05_artifact_hashes.json
```

`audit/r05_selected_factor_manifest.csv` must include at least:

```text
factor_id
cluster_id
is_representative
direction
mean_train_rankIC
ic_vol
sign_consistency
single_year_ic_contribution_share
factor_quality_score
primary_rankic_feature_version
neutralized_mean_train_rankIC
raw_neutralized_rankIC_sign_agree
neutralized_missing_share
cluster_source_factor_share
representative_tie_break_rank
```

`audit/r05_train_label_purge_audit.csv` must report, at minimum:

```text
split
primary_horizon
total_train_signal_date_count
train_label_purged_cross_split_signal_date_count
train_label_unpurged_signal_date_count
train_label_unpurged_signal_date_share
min_train_label_unpurged_signal_date_share
train_label_purge_gate
```

`audit/r05_train_rankic_by_factor_year.csv` must include both primary raw-factor RankIC and audit-only neutralized-factor RankIC. It must identify the primary IC used for stability selection and direction.

`audit/r05_train_comparator_consistency_audit.csv` must report, at minimum:

```text
factor_id
primary_label_comparator = eligible_minus_target
audit_label_comparator = frozen_composite_nonselected_preferred
primary_mean_train_rankIC
audit_mean_train_rankIC
primary_audit_sign_agree
representative_flag
selected_factor_flag
```

`metrics/r05_date_weighted_summary.csv` must report, by split and horizon:

```text
date_weighted_net_return
date_weighted_matched_delta
date_weighted_baseline_lift
date_count
year_min_date_count
```

## 22. Final Report Required Questions

The final report must answer:

1. Did R05 use only train data for factor engineering?
2. How many source GTJA191 factors were implementable?
3. How many factors survived stability selection?
4. How many train-only clusters remained?
5. Which representative factors were selected for each cluster?
6. Are all factor directions train-only RankIC signs?
7. How different are raw rank and neutralized rank score distributions?
8. Does selected top 20% repeatedly select a small number of stocks?
9. Does H10 validation pass the relative gate?
10. Does H10 validation beat the same-day nonselected baseline?
11. Are 2022 and 2023 aligned in residual direction?
12. Does robustness 2024-2025 confirm validation?
13. Do H5 and H20 support or contradict H10?
14. Do date-weighted H10 metrics confirm or weaken the event-weighted conclusion?
15. Is the result long-only alpha, residual edge, beta/style exposure, unstable lead, or no support?
16. What incremental evidence did R05 add beyond R04?
17. Did any factor inclusion, exclusion, direction, cluster assignment, or representative choice use information outside train? If yes, list the exact audit rows; if no, state zero violations.

## 23. Validator Checklist

The validator must check:

1. Requirement ID and output namespace match this document.
2. All required artifacts exist.
3. Local PIT data only; no online market data dependency.
4. Factor registry includes all 191 source factor IDs.
5. Included factor count meets `min_included_factor_count`.
6. Every train-only engineering decision has a frozen audit record.
7. No validation or robustness column is used in factor stability selection.
8. No validation or robustness column is used in clustering or representative selection.
9. Neutralization audit exists and covers industry / liquidity / beta exposure.
10. Train label purge audit exists and `train_label_purge_gate` is replayed in §20.
11. Stability selection audit includes yearly RankIC and contribution-share fields.
12. Train RankIC labels are complete inside the train split and cross-split labels are purged.
13. Train comparator consistency audit exists and cannot modify primary engineering decisions.
14. Cluster audit uses the fixed complete-link algorithm and includes train-only Spearman correlation, pairwise observation counts, source-factor concentration, representative eligibility, and representative tie-break fields.
15. Selected factor manifest includes direction, cluster ID, quality score, primary IC feature version, neutralized audit IC, `raw_neutralized_rankIC_sign_agree`, and `cluster_source_factor_share`.
16. Score selection uses fixed top 20% and deterministic tie-break.
17. Selected-week recurrence fields are computed from unique selected dates.
18. Matched comparator and nonselected baseline panels exist and are distinct.
19. Baseline lift equals selected equal-weight net return minus nonselected baseline equal-weight net return.
20. Date-weighted summary exists and is not used to override final gates.
21. Sample status is assigned by exhaustive first-match order.
22. Blocked H10 sample statuses cannot fall through to no-support.
23. Final decision replay follows §20 first-match priority.
24. Report states that R05 allows train-only engineering but prohibits validation-driven alpha mining.
25. Report explicitly lists any train-only violations, or states zero violations.
26. Report does not use right-tail / big-winner readout as a pass/fail gate.

## 24. Stop-and-Revise Conditions

E05 must stop and return to requirement revision if:

- GTJA191 formulas cannot be mapped locally without ambiguous lookahead assumptions;
- local provider lacks required OHLCV/money/index fields;
- fewer than `min_included_factor_count` factors are implementable;
- `train_label_unpurged_signal_date_share < min_train_label_unpurged_signal_date_share`;
- neutralization cannot be performed without changing the inherited field contract;
- fewer than `min_stability_selected_factor_count` factors pass train-only stability selection;
- fewer than `min_cluster_count` clusters remain;
- top-20% selection cannot produce enough selected or nonselected names under the revised small-universe floors on most validation dates;
- matched comparator or baseline construction requires changing inherited EP5 semantics;
- a positive result requires validation-driven factor selection, direction changes, cluster changes, weighting, threshold tuning, or filter addition.

Stopping under these conditions is a correct outcome. It prevents R05 from silently becoming validation-driven alpha mining.

## 25. EP5 GTJA191 Pause Boundary

R05 allows train-only factor engineering, but it does not allow validation-driven alpha mining.

R04 failed the raw equal-weight GTJA191 composite. R05 tests a different question:

```text
Does GTJA191 still have short-horizon residual ranking value after
train-only neutralization, stability filtering, redundancy reduction,
and cluster-level equal-weight composition?
```

If R05 also ends as `r05_no_gtja191_factor_engineering_support`, the EP5 GTJA191 / Alpha191 short-horizon residual-ranking direction should pause unless a later requirement changes the research target materially.
