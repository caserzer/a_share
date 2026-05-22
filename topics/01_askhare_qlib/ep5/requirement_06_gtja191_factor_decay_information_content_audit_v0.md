# EP5 Requirement 06: GTJA191 Factor Decay and Information Content Audit V0

## 1. Requirement Metadata

requirement_id: `ep5_r06_gtja191_factor_decay_information_content_audit_v0`

short_name: `r06_gtja191_factor_decay_information_content_audit_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-22`

primary_output_namespace: `ep5/outputs/r06_gtja191_factor_decay_information_content_audit_v0/`

upstream_requirement:

- `ep5/requirement_05_gtja191_train_only_factor_engineering_residual_feasibility_v0.md`

upstream_report:

- `ep5/outputs/r05_gtja191_train_only_factor_engineering_residual_feasibility_v0/reports/r05_final_report.md`

upstream_final_decision:

```text
r05_factor_cluster_structure_not_viable_blocked
```

R06 inherits the EP5 local PIT universe, split, provider, execution calendar, next-open executability, transaction cost, matched-comparator discipline, and no-online-data boundary used by R01/R02/R03/R04/R05.

R06 deliberately does not inherit R05's primary object:

```text
weekly top20% train-only engineered composite strategy
```

R05 already tested that strategy-style question and did not support it. R06 steps back from strategy construction to information-content auditing.

## 2. Upstream Motivation

R05 changed R04's raw equal-weight composite into a train-only engineered Alpha191 composite:

- factor coverage filtering;
- rank normalization;
- industry / liquidity / beta neutralization;
- train-only RankIC stability filtering;
- train-only redundancy clustering;
- train-only cluster representative selection;
- cluster-level equal-weight scoring;
- fixed weekly top 20% selection;
- fixed H5/H10/H20 natural exits.

R05 still failed under a sufficient H10 validation sample.

Key R05 H10 validation evidence:

```text
complete_event_count = 4,279
decision_observation_date_count = 96
sample_status = pass
mean_net_return = -1.3245%
median_net_return = -1.6726%
loss_rate = 61.91%
mean_matched_delta_return = +0.1028%
median_matched_delta_return = -0.3440%
2022 mean_matched_delta_return = +0.2936%
2023 mean_matched_delta_return = -0.0980%
mean_baseline_lift = +0.0582%
median_baseline_lift = -0.1553%
absolute_positive = false
relative_positive = false
baseline_lift_gate = false
robustness_confirmed = false
H10 quadrant = absolute_false__relative_false
```

R05 also exposed a severe persistent-name problem:

```text
H10 validation top1_instrument_selected_week_share = 53.54%
H10 validation top5_instrument_selected_week_share = 97.98%
H10 train top1_instrument_selected_week_share = 54.65%
H10 train top5_instrument_selected_week_share = 95.35%
```

The important R05 finding is:

```text
Train-only GTJA191 engineering can identify repeated price/volume shapes,
but those shapes do not become a stable H10 residual ranking edge.
```

Therefore R06 must not try to repair R05 by:

- changing top fraction;
- filtering persistent names after seeing validation;
- changing H10 to the best validation horizon;
- changing family definitions after seeing validation;
- keeping only validation-positive factors;
- adding a strategy overlay.

The valid R06 question is narrower and earlier in the research chain:

```text
Does the GTJA191 / Alpha191 feature library still contain reproducible
short-horizon cross-sectional information under the current EP5 data and
execution contract?
```

## 3. Research Positioning

R06 is a diagnostic requirement.

R06 is not a strategy requirement.

R06 does not output:

- production strategy;
- long-only alpha pass;
- residual portfolio pass;
- top20% selected-event pass;
- exposure unit approval.

R06 outputs:

- whether factor information exists;
- where that information decays across H1/H3/H5/H10/H20;
- which factor families still carry information;
- whether information is gross-only or survives cost;
- whether information is residual or style / beta / liquidity driven;
- whether information is dynamic or persistent-name driven;
- whether a later R07 strategy requirement is justified.

R06's discipline is:

```text
train can choose diagnostic horizons;
validation evaluates frozen diagnostic choices;
robustness confirms or rejects information persistence;
no split constructs a tradable strategy in R06.
```

## 4. Core Question

R06 asks:

```text
Within the current PIT mcap500 mainboard universe,
weekly close-observed signal cadence,
next-open executable return labels,
fixed transaction costs,
matched-comparator discipline,
and local GTJA191 factor registry,

does GTJA191 / Alpha191 contain reproducible, non-pure-style,
non-persistent-name, short-horizon cross-sectional information?

If yes, which horizon, factor family, market state, and cost regime
does that information belong to?
```

The primary object is:

```text
factor / family / horizon information content
```

The primary evidence types are:

- RankIC decay;
- top-bottom spread;
- decile monotonicity;
- validation / robustness consistency;
- persistent-name concentration;
- style exposure attribution;
- cost sensitivity.

## 5. Non-Goals and Explicit Prohibitions

R06 is not:

- R05.1;
- improved GTJA191 composite strategy;
- top20% strategy search;
- horizon grid search for a strategy;
- family grid search for a strategy;
- validation-driven factor selection;
- validation-driven horizon selection;
- validation-driven family selection;
- LGBM, neural network, linear model, PCA, autoencoder, or optimizer research;
- production strategy work.

R06 must not:

1. Construct a top20% trading strategy.
2. Output long-only alpha support.
3. Output residual strategy support.
4. Use validation or robustness to choose factor inclusion.
5. Use validation or robustness to choose factor direction.
6. Use validation or robustness to choose factor family.
7. Use validation or robustness to choose horizon.
8. Tune top fraction or decile cutoff based on validation.
9. Add stop-loss, take-profit, layered exit, re-entry, or portfolio optimizer logic.
10. Add validation-discovered regime, RS20, rebound, volatility, persistent-name, or liquidity filters.
11. Use right-tail or big-winner readouts as decision evidence.
12. Re-label diagnostic evidence as a tradable exposure unit.

R06 may recommend a later R07 requirement only if R06's pre-declared information gates pass.

## 6. Data, Split, and Execution Contract

R06 inherits local EP5 data inputs:

- local PIT Qlib provider used by R01-R05;
- PIT mcap500 mainboard universe;
- PIT industry membership;
- trading calendar;
- `SH000300` index `open` and `close`;
- local GTJA191 source file or documented byte-for-byte local copy.

R06 must not fetch online data during execution.

R06 inherits split boundaries:

```text
train:
  2017-07-04 through 2021-12-31

validation:
  2022-01-01 through 2023-12-31

robustness:
  2024-01-01 through 2025-12-31
```

Signal cadence:

```text
weekly close-observed signal date D
```

Execution label convention:

```text
entry = first executable next open after signal date D
exit  = fixed natural horizon exit open
```

R06 horizons:

```text
H1
H3
H5
H10
H20
```

Cost:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
```

R06 must compute both gross and net labels. Net labels include the same transaction cost convention as R01-R05.

## 7. Canonical Audit Units

R06 has no strategy unit.

R06 has three audit units.

### 7.1 Factor-Horizon Audit Unit

canonical_unit_id:

```text
r06_gtja191_factor_horizon_decay_audit_v0
```

Purpose:

- evaluate each included GTJA191 factor independently;
- compute factor-level RankIC and spread for each horizon;
- do not combine factors into a tradable portfolio.

### 7.2 Family-Horizon Audit Unit

canonical_unit_id:

```text
r06_gtja191_family_horizon_information_audit_v0
```

Purpose:

- aggregate factor evidence by frozen factor family;
- compute family-level RankIC decay, spread, monotonicity, persistence, and style exposure;
- identify which information type, if any, remains viable.

### 7.3 Train-Selected Family-Horizon Diagnostic Unit

canonical_unit_id:

```text
r06_gtja191_train_selected_family_horizon_audit_v0
```

Purpose:

- choose one diagnostic horizon per family using train split only;
- evaluate the frozen family horizon in validation and robustness;
- decide whether a later R07 strategy requirement is allowed.

This unit still cannot trade or output a strategy pass.

## 8. Factor Registry and Coverage Contract

R06 must reuse the R05 local GTJA191 factor registry and formula implementation when available.

For every GTJA191 source factor, output:

- `factor_id`;
- `source_name`;
- `source_formula_text`;
- `source_formula_hash`;
- `local_formula_hash`;
- `required_fields`;
- `max_lookback_trading_days`;
- `effective_first_usable_date`;
- `asof_safe`;
- `factor_status`;
- `exclusion_reason`;
- `implementation_error`.

Allowed exclusion reasons:

```text
formula_implementation_failed
unsupported_or_slow_v0_construct
not_asof_safe
missing_required_field
insufficient_train_factor_coverage_date_count
insufficient_cross_section_coverage
constant_or_degenerate
lookback_exceeds_allowed_window
```

R06 must not exclude a factor because of validation or robustness performance.

Minimum implementation requirement:

```text
min_included_factor_count = 100
max_lookback_trading_days = 252
```

If fewer than `100` factors are included, R06 final decision must be a data / implementation block, not an information conclusion.

## 9. Factor Family Map

R06 must create a frozen factor-family map before reading validation or robustness performance.

Artifact:

```text
audit/r06_factor_family_map.csv
```

Required columns:

- `factor_id`;
- `primary_family`;
- `secondary_family_tags`;
- `family_assignment_method`;
- `assignment_rule_text`;
- `formula_terms_used`;
- `manual_override_flag`;
- `manual_override_reason`;
- `created_before_metric_computation`.

Allowed primary families:

```text
price_momentum_reversal
volume_price_correlation
vwap_deviation
close_location
range_volatility
volume_surge_money_flow
rank_ts_rank_structure
ohlc_pattern
composite_price_volume
other_gtja191
```

Family assignment may use:

- local formula text;
- formula operators and field names;
- pre-declared keyword rules;
- pre-declared manual overrides.

If `manual_override_flag = true`, `manual_override_reason` must cite either:

- a public GTJA191 / JoinQuant factor classification source;
- local formula text features such as field names, operators, and lookback structure;
- a pre-declared taxonomy rule in this requirement.

`manual_override_reason` must not cite or depend on:

- R04 performance evidence;
- R05 performance evidence;
- validation / robustness RankIC;
- validation / robustness spread;
- selected-name concentration outcomes.

Family assignment must not use:

- train RankIC;
- validation RankIC;
- robustness RankIC;
- spread performance;
- selected-name behavior;
- final decision outcomes.

If a factor has multiple tags, final family-level decision authority uses only `primary_family`. Secondary tags are audit-only.

Validator requirement:

```text
created_before_metric_computation = true
```

for all rows.

## 10. Factor Transform Contract

R06 must compute both raw and neutralized rank factors.

For each signal date D and factor i:

1. Use as-of-safe raw factor value.
2. Winsorize cross-sectionally at p01 / p99.
3. Rank-normalize to `[-0.5, 0.5]`.
4. Build neutralized version by cross-sectional residualization against:
   - industry;
   - liquidity quintile;
   - beta bucket;
   - optional volatility bucket;
   - optional money / size bucket.

Primary R06 RankIC is computed on:

```text
raw_rank_factor_i x matched_delta_label_H
```

Neutralized RankIC is mandatory audit evidence.

Reason:

```text
The label already uses matched comparator discipline.
Using raw factor for primary RankIC avoids double neutralization.
Neutralized factor evidence is used to identify style-exposure fragility.
```

R06 must report both:

```text
primary_raw_rankIC
neutralized_rankIC_audit
raw_neutralized_sign_agreement
```

## 11. Horizon Label Panel

R06 must compute a full horizon label panel for each eligible candidate stock and signal date.

Artifact:

```text
audit/r06_horizon_label_panel_audit.csv
```

Required labels:

```text
gross_return_H1
gross_return_H3
gross_return_H5
gross_return_H10
gross_return_H20

net_return_H1
net_return_H3
net_return_H5
net_return_H10
net_return_H20

matched_comparator_gross_return_H1
matched_comparator_gross_return_H3
matched_comparator_gross_return_H5
matched_comparator_gross_return_H10
matched_comparator_gross_return_H20

matched_comparator_net_return_H1
matched_comparator_net_return_H3
matched_comparator_net_return_H5
matched_comparator_net_return_H10
matched_comparator_net_return_H20

matched_delta_gross_H1
matched_delta_gross_H3
matched_delta_gross_H5
matched_delta_gross_H10
matched_delta_gross_H20

matched_delta_net_H1
matched_delta_net_H3
matched_delta_net_H5
matched_delta_net_H10
matched_delta_net_H20
```

Primary information label:

```text
matched_delta_net_H
```

Gross label is audit-only, used to distinguish:

```text
information exists but cost removes it
```

from:

```text
information does not exist
```

Split-purity rule:

For a label in split S and horizon H, both entry execution and natural exit execution must occur within split S. Cross-split labels are purged and counted in audit.

Required purge audit fields:

- `split`;
- `horizon`;
- `total_signal_date_count`;
- `purged_cross_split_signal_date_count`;
- `unpurged_signal_date_count`;
- `unpurged_signal_date_share`;
- `min_unpurged_signal_date_share`;
- `purge_gate`.

Frozen minimum:

```text
min_unpurged_signal_date_share = 0.90
```

Frozen minimum valid signal-date counts after split-pure purging:

```text
min_train_unpurged_signal_date_count = 180
min_validation_unpurged_signal_date_count = 70
min_robustness_unpurged_signal_date_count = 70
```

The horizon label sample gate is:

```text
all_horizon_label_sample_gate = true
```

only when every split / horizon pair in:

```text
split in {train, validation, robustness}
horizon in {H1, H3, H5, H10, H20}
```

satisfies:

```text
purge_gate = true
unpurged_signal_date_share >= min_unpurged_signal_date_share
unpurged_signal_date_count >= split_specific_min_unpurged_signal_date_count
finite_label_date_share >= 0.90
```

where `finite_label_date_share` is the share of unpurged signal dates with at least one finite candidate label and one finite matched-comparator label for that split / horizon.

## 12. Factor Decay RankIC Audit

For each included factor i, horizon H, split S, and signal date D:

```text
date_rankIC_i,H,D = SpearmanRankCorr(
  factor_value_i(D, eligible_cross_section),
  matched_delta_net_H(D, eligible_cross_section)
)
```

R06 must compute this for:

```text
H1, H3, H5, H10, H20
```

Metrics per factor / horizon / split:

- `valid_date_count`;
- `mean_rankIC`;
- `median_rankIC`;
- `rankIC_std`;
- `ICIR = mean_rankIC / rankIC_std`;
- `positive_date_share`;
- `p10_date_rankIC`;
- `p90_date_rankIC`;
- `year_count`;
- `positive_year_count`;
- `negative_year_count`;
- `yearly_rankIC_min`;
- `yearly_rankIC_max`;
- `single_year_ic_contribution_share`;
- `raw_neutralized_rankIC_sign_agree`;
- `missing_share`.

Artifacts:

```text
audit/r06_factor_decay_rankic_panel.csv
metrics/r06_factor_horizon_rankic_summary.csv
```

Minimum factor-level evaluability:

```text
valid_validation_dates >= 70
valid_robustness_dates >= 70
valid_year_count >= 2
missing_share <= 0.30
```

These thresholds do not create strategy support. They only determine whether a factor / horizon is evaluable.

## 13. Family Decay Summary

For each primary family F and horizon H, aggregate factor-level evidence without validation-driven factor selection.

All included and evaluable factors in the family must be used for the family summary.

Allowed family aggregation must keep raw and train-oriented views separate:

```text
raw_family_mean_rankIC
  = mean_over_evaluable_factors(mean_rankIC_i)

raw_family_median_rankIC
  = median_over_evaluable_factors(mean_rankIC_i)

neutralized_family_mean_rankIC
  = mean_over_evaluable_factors(neutralized_mean_rankIC_i)

neutralized_family_median_rankIC
  = median_over_evaluable_factors(neutralized_mean_rankIC_i)

direction_i,F,H,train
  = sign(train_mean_rankIC_i,H)

oriented_rankIC_i,S,H
  = direction_i,F,H,train * rankIC_i,S,H

family_oriented_mean_rankIC(F,S,H)
  = mean_over_evaluable_factors(oriented_rankIC_i,S,H)

family_oriented_median_rankIC(F,S,H)
  = median_over_evaluable_factors(oriented_rankIC_i,S,H)

family_oriented_positive_factor_share(F,S,H)
  = share(oriented_rankIC_i,S,H > 0)

family_oriented_date_rankIC(F,H,D)
  = mean_over_evaluable_factors(
      direction_i,F,H,train * date_rankIC_i,H,D
    )

family_oriented_yearly_rankIC(F,H,year)
  = mean_over_evaluable_factors(
      direction_i,F,H,train * yearly_rankIC_i,H,year
    )
```

Final information gates must use `family_oriented_*` fields. Raw family RankIC fields are audit-only and must not be used to pass or fail a family.

R06 must also compute raw, neutralized, and residualized family-level scores.

```text
raw_family_score_F,H,D,stock
  = mean_over_evaluable_family_factors(
      direction_i,F,H,train * raw_rank_factor_i(D, stock)
    )

neutralized_family_score_F,H,D,stock
  = mean_over_evaluable_family_factors(
      direction_i,F,H,train * neutralized_rank_factor_i(D, stock)
    )
```

The primary family score used for §15 monotonicity, spread, and persistent-name gates is:

```text
family_score_F,H,D,stock = neutralized_family_score_F,H,D,stock
```

`raw_family_score_F,H,D,stock` is audit-only and is used for style-retention comparisons in §17.

where:

```text
direction_i,F,H,train = sign(train_mean_rankIC_i,H)
```

If `train_mean_rankIC_i,H = 0`, the factor has no train direction for that horizon and cannot contribute to the oriented family score for that family / horizon. The exclusion must be reported as `zero_train_direction_excluded`.

This family score is diagnostic only. It is not a strategy exposure unit.

Artifacts:

```text
audit/r06_family_decay_summary.csv
metrics/r06_family_horizon_rankic_summary.csv
```

Required fields:

- `primary_family`;
- `horizon`;
- `split`;
- `source_factor_count`;
- `included_factor_count`;
- `evaluable_factor_count`;
- `raw_family_mean_rankIC`;
- `raw_family_median_rankIC`;
- `neutralized_family_mean_rankIC`;
- `neutralized_family_median_rankIC`;
- `family_oriented_mean_rankIC`;
- `family_oriented_median_rankIC`;
- `family_oriented_ICIR`;
- `family_oriented_positive_factor_share`;
- `family_oriented_positive_date_share`;
- `family_oriented_positive_year_count`;
- `family_oriented_negative_year_count`;
- `family_oriented_date_rankIC`;
- `family_oriented_rankIC_p10`;
- `family_oriented_rankIC_p90`;
- `family_oriented_yearly_rankIC`;
- `zero_train_direction_excluded_count`;
- `family_redundancy_mean_abs_corr`;
- `family_redundancy_p90_abs_corr`.

## 14. Train-only Horizon Selection Audit

R06 may choose one diagnostic primary horizon per family using train split only.

Artifact:

```text
audit/r06_family_horizon_selection_train_only.csv
```

Only train-eligible family horizons may enter horizon selection. A family horizon is train-eligible when:

```text
valid_train_year_count >= 4
family_oriented_same_sign_year_count >= 3
family_oriented_single_year_ic_contribution_share <= 0.60
train_valid_date_count >= 70
train_family_oriented_mean_rankIC > 0
```

Family-level train stability fields are computed from `family_oriented_yearly_rankIC(F,H,year)`:

```text
family_oriented_same_sign_year_count
  = count(train years where family_oriented_yearly_rankIC(F,H,year) > 0)

family_oriented_single_year_ic_contribution_share
  = max_year(abs(family_oriented_yearly_rankIC(F,H,year)))
    / sum_year(abs(family_oriented_yearly_rankIC(F,H,year)))

train_family_oriented_positive_year_share
  = family_oriented_same_sign_year_count / valid_train_year_count

train_family_oriented_positive_date_share
  = share(train signal dates where family_oriented_date_rankIC(F,H,D) > 0)

train_family_oriented_rankIC_std
  = std(train family_oriented_date_rankIC(F,H,D))
```

If the denominator of `family_oriented_single_year_ic_contribution_share` is zero, that family horizon is not train-eligible.

If no horizon in a family is train-eligible, then:

```text
family_primary_horizon_train_selected = not_selected_insufficient_train_stability
```

and that family cannot pass final information gates.

```text
train_horizon_quality_score(F,H)
  = train_family_oriented_mean_rankIC(F,H)
    * train_family_oriented_positive_year_share(F,H)
    * train_family_oriented_positive_date_share(F,H)
    / (1 + abs(train_family_oriented_rankIC_std(F,H)))
```

Tie-break order:

1. higher `train_horizon_quality_score`;
2. higher `train_family_oriented_mean_rankIC`;
3. lower `family_oriented_single_year_ic_contribution_share`;
4. shorter horizon in the order `H1`, `H3`, `H5`, `H10`, `H20`;
5. alphabetical `primary_family`.

The selected horizon is:

```text
family_primary_horizon_train_selected
```

Validation and robustness must evaluate this frozen horizon only for final family information gates.

R06 must also report full all-horizon decay curves. The train-selected horizon does not suppress the other audit horizons.

Prohibition:

```text
Validation or robustness cannot change family_primary_horizon_train_selected.
```

## 15. Monotonicity and Spread Audit

R06 must evaluate cross-sectional information using deciles, not top20% strategy selection.

For each factor i and family F, horizon H, split S, and signal date D:

1. Orient score using train direction for the relevant horizon.
2. Assign eligible stocks to deciles 1-10 by oriented score using the deterministic rule below.
3. Compute mean gross return, net return, and matched delta for each decile.
4. Compute top-bottom spreads.

Deterministic decile assignment:

```text
decile 10 = highest oriented score
decile 1 = lowest oriented score

sort key:
  oriented_score ascending
  instrument_id ascending

decile bucket construction:
  count-balanced deciles
  first bucket after ascending sort = decile 1
  last bucket after ascending sort = decile 10
  bucket sizes may differ by at most 1
  ties are broken only by instrument_id

not evaluable when:
  eligible_count < min_decile_cross_section_count
```

`min_decile_cross_section_count` is fixed at:

```text
min_decile_cross_section_count = 100
```

Required spreads:

```text
top_decile_minus_bottom_decile_matched_delta_net
top_quintile_minus_bottom_quintile_matched_delta_net
top_decile_minus_bottom_decile_net_return
top_quintile_minus_bottom_quintile_net_return
top_decile_minus_bottom_decile_gross_return
top_quintile_minus_bottom_quintile_gross_return
```

Monotonicity score:

```text
decile_monotonicity_score
  = SpearmanRankCorr(decile_number, decile_mean_matched_delta_net)
```

Gate thresholds:

```text
decile_monotonicity_score >= 0.60
top_quintile_minus_bottom_quintile_matched_delta_net > 0
top_decile_minus_bottom_decile_matched_delta_net > 0
matched_delta_spread_positive_date_share >= 0.55
```

Artifacts:

```text
audit/r06_monotonicity_decile_audit.csv
audit/r06_decile_assignment_audit.csv
metrics/r06_family_spread_summary.csv
```

R06 must not convert the top decile or top quintile into a proposed trading strategy. Decile spread is information evidence only.

## 16. Persistent-name Audit

R06 must explicitly test whether factor or family information is driven by persistent names.

For each factor / family / horizon / split:

Compute for top decile and top quintile:

- `top1_instrument_signal_week_share`;
- `top5_instrument_signal_week_union_share`;
- `persistent_candidate_ratio`;
- `average_rank_stability`;
- `rank_turnover`;
- `new_name_share`;
- `top_decile_unique_instrument_count`;
- `top_quintile_unique_instrument_count`;
- `median_weekly_top_decile_size`;
- `median_weekly_top_quintile_size`.

Definitions:

```text
top1_instrument_signal_week_share
  = max_i(count(signal weeks where i is in top bucket) / total_signal_weeks)

top5_instrument_signal_week_union_share
  = count(signal weeks where any of the top5 recurrent instruments is in top bucket)
    / total_signal_weeks

new_name_share(D)
  = share(top_bucket_names(D) not in top_bucket_names(previous_signal_date))

rank_turnover(D)
  = 1 - Jaccard(top_bucket_names(D), top_bucket_names(previous_signal_date))

average_rank_stability
  = mean adjacent-week Spearman rank correlation among overlapping eligible names
```

Persistent-name clean gate must be computed separately for the top decile and top quintile.

For each bucket type B in `{top_decile, top_quintile}`:

```text
persistent_name_clean_gate_B = true
```

only when:

```text
top1_instrument_signal_week_share_B <= 0.35
top5_instrument_signal_week_union_share_B <= 0.75
new_name_share_B >= 0.30
rank_turnover_B >= 0.35
```

The family-level persistent-name clean gate is:

```text
persistent_name_clean_gate
  = persistent_name_clean_gate_top_decile
    AND persistent_name_clean_gate_top_quintile
```

Artifact:

```text
audit/r06_persistent_name_audit.csv
```

If information exists but fails persistent-name clean gate, R06 cannot recommend a direct event-driven strategy. It may only output:

```text
r06_decay_information_exists_but_not_tradeable
```

unless another family passes all clean gates.

## 17. Style Exposure Audit

R06 must distinguish residual information from style / exposure artifacts.

For each factor / family / horizon / split, compute:

- industry exposure;
- liquidity exposure;
- beta exposure;
- volatility exposure;
- market-state exposure readout;
- money / size exposure;
- style-explained score R2;
- style-explained spread share;
- raw vs neutralized RankIC difference;
- raw vs neutralized spread difference.

Required cross-sectional style groups:

```text
industry
liquidity_quintile
beta_bucket
volatility_bucket
money_bucket
```

`market_state` must not be included in the per-date cross-sectional OLS because it is constant within a signal date. It is reported only through the market-state / regime readout in §19.

Required calculations:

```text
style_explained_score_r2(D,F,H)
  = cross-sectional OLS R2 from regressing raw_family_score_F,H,D,stock on
    industry + liquidity_quintile + beta_bucket + volatility_bucket
    + money_bucket dummies

residualized_family_score_F,H,D,stock
  = residual from the same cross-sectional OLS

raw_top_bottom_spread_matched_delta_net
  = top_decile_minus_bottom_decile_matched_delta_net
    using raw_family_score

residualized_top_bottom_spread_matched_delta_net
  = top_decile_minus_bottom_decile_matched_delta_net
    using residualized_family_score

neutralized_top_bottom_spread_matched_delta_net
  = top_decile_minus_bottom_decile_matched_delta_net
    using neutralized_family_score

style_explained_spread_share
  = (raw_top_bottom_spread_matched_delta_net
     - residualized_top_bottom_spread_matched_delta_net)
    / abs(raw_top_bottom_spread_matched_delta_net)

neutralized_spread_retention
  = neutralized_top_bottom_spread_matched_delta_net
    / raw_top_bottom_spread_matched_delta_net

raw_neutralized_family_rankIC_sign_agree
  = sign(raw_family_mean_rankIC)
    == sign(neutralized_family_mean_rankIC)
```

`style_explained_spread_share` and `neutralized_spread_retention` are not evaluable when `abs(raw_top_bottom_spread_matched_delta_net) < 0.0001`. A non-evaluable style spread metric cannot pass the style-exposure clean gate.

Split-level style gate inputs must be aggregated as:

```text
style_explained_score_r2 = median_D(style_explained_score_r2(D,F,H))
style_explained_spread_share = mean_D(style_explained_spread_share(D,F,H))
neutralized_spread_retention = mean_D(neutralized_spread_retention(D,F,H))
```

The aggregation uses only evaluable style dates. The style-exposure clean gate is false when the evaluable style date count is below 70 in validation or robustness.

Style-exposure clean gate:

```text
style_explained_score_r2 <= 0.35
style_explained_spread_share <= 0.50
neutralized_spread_retention >= 0.50
raw_neutralized_family_rankIC_sign_agree = true
```

Artifact:

```text
audit/r06_style_exposure_audit.csv
```

If a family has positive raw RankIC or spread but fails style clean gates, R06 must label that evidence as style-exposure driven, not residual information.

## 18. Cost Sensitivity Audit

R06 must report whether information exists before cost and after cost.

For each factor / family / horizon:

```text
gross_rankIC
net_rankIC
gross_return_spread
net_return_spread
matched_delta_gross_spread
matched_delta_net_spread
cost_drag = gross_return_spread - net_return_spread
cost_survival_ratio = net_return_spread / gross_return_spread
```

Cost survival must be computed from long-only decile return spreads, not from matched-delta spreads. Matched-delta spreads remain residual information evidence, but comparator costs can cancel or distort the economic cost drag.

`cost_survival_ratio` is not evaluable when:

```text
gross_return_spread <= 0.0001
```

A non-evaluable `cost_survival_ratio` cannot pass `family_cost_survives`.

Artifact:

```text
audit/r06_cost_sensitivity_audit.csv
```

Interpretation:

- gross return spread positive but net return spread negative means information may exist but is not currently tradeable;
- gross and net return spreads both negative means no information support;
- net positive but persistent/style gates fail means not tradeable without a new research question;
- net positive and all clean gates pass may justify R07.

## 19. Market-State and Regime Readout

R06 may report information by market state, beta bucket, and liquidity bucket, but these are audit-only unless specified by a future R07 requirement.

Allowed readouts:

- `risk_on`;
- `risk_off`;
- `mixed`;
- beta bucket;
- liquidity quintile;
- volatility bucket;
- money bucket.

R06 must not use these readouts to filter the final decision inside R06.

Required artifact:

```text
metrics/r06_validation_robustness_consistency.csv
```

This artifact must show whether family-level evidence survives:

- train selected horizon;
- validation aggregate;
- validation by year;
- robustness aggregate;
- robustness by year.

## 20. Family-level Information Gates

R06 final decision is family-level, not single-factor-level.

A family F at its train-selected horizon H is `family_evaluable` when:

```text
included_factor_count >= 3
evaluable_factor_count >= 2
valid_validation_dates >= 70
valid_robustness_dates >= 70
validation_year_count >= 2
robustness_year_count >= 2
```

A family F is `family_information_positive` when all are true:

```text
family_evaluable = true
train_selected_horizon_frozen = true
validation_family_oriented_mean_rankIC > 0
validation_family_oriented_median_rankIC >= -0.001
validation_top_decile_minus_bottom_decile_matched_delta_net > 0
validation_matched_delta_spread_positive_date_share >= 0.55
not both validation years have negative family_oriented_mean_rankIC
robustness_family_oriented_mean_rankIC >= -0.001
robustness_top_decile_minus_bottom_decile_matched_delta_net >= -0.0025
```

A family F is `family_monotonicity_positive` when:

```text
validation_decile_monotonicity_score >= 0.60
validation_top_quintile_minus_bottom_quintile_matched_delta_net > 0
validation_top_decile_minus_bottom_decile_matched_delta_net > 0
robustness_decile_monotonicity_score >= 0.45
```

A family F is `family_clean_residual` when:

```text
persistent_name_clean_gate = true
style_exposure_clean_gate = true
```

A family F is `family_cost_survives` when:

```text
validation_top_decile_minus_bottom_decile_net_return > 0
robustness_top_decile_minus_bottom_decile_net_return >= -0.0025
cost_survival_ratio >= 0.50
```

A family F is `family_information_supported` when:

```text
family_information_positive = true
family_monotonicity_positive = true
family_clean_residual = true
```

A family F is `family_tradeable_research_candidate` when:

```text
family_information_supported = true
family_cost_survives = true
gross_only_short_horizon_blocked = false
```

where:

```text
gross_only_short_horizon_blocked = true
```

only when:

```text
train_selected_horizon in {H1, H3}
and family passes only gross return spread or gross RankIC evidence
and family_cost_survives = false
```

R06 must report all gate inputs per family.

Artifact:

```text
metrics/r06_information_decision_inputs.csv
```

## 21. Final Decisions

R06 final decisions are information conclusions, not strategy approvals.

Allowed final decisions:

```text
r06_blocked_data_or_execution_contract
r06_factor_library_not_implementable_blocked
r06_family_map_not_reproducible_blocked
r06_insufficient_information_audit_sample_blocked
r06_no_factor_information_support
r06_decay_information_exists_but_not_tradeable
r06_relative_information_only
r06_factor_family_information_supported
```

### 21.1 `r06_blocked_data_or_execution_contract`

Meaning:

```text
Required local data, execution labels, split-pure labels, or matched comparator
panels could not be reproduced.
```

No information conclusion is allowed.

### 21.2 `r06_factor_library_not_implementable_blocked`

Meaning:

```text
Included GTJA191 factor count is below frozen minimum or factor registry cannot
be replayed.
```

No information conclusion is allowed.

### 21.3 `r06_family_map_not_reproducible_blocked`

Meaning:

```text
Family assignment is missing, post-metric, validation-driven, or not replayable.
```

No family-level conclusion is allowed.

### 21.4 `r06_insufficient_information_audit_sample_blocked`

Meaning:

```text
Enough factors exist, but horizon labels or family-level validation/robustness
samples are insufficient for information audit.
```

No positive or negative Alpha191 information conclusion is allowed.

### 21.5 `r06_no_factor_information_support`

Meaning:

```text
No family at its train-selected horizon has stable validation and robustness
RankIC / spread / monotonicity evidence.
```

Next step:

```text
Pause Alpha191 short-horizon direction under current EP5 framing.
```

### 21.6 `r06_decay_information_exists_but_not_tradeable`

Meaning:

```text
Some train-selected gross or short-horizon H1/H3/H5 information exists, but it
fails cost, robustness, persistent-name, style-exposure, or monotonicity
requirements.
```

Next step:

```text
Do not write a strategy requirement from this evidence.
Keep the evidence as research background only.
If a successor is written, it must be a non-strategy cost-revisited or
hedged-only diagnostic requirement, never a long-only strategy requirement.
```

### 21.7 `r06_relative_information_only`

Meaning:

```text
At least one family has stable matched-delta information and clean residual
evidence, but long-only net spread or cost survival is not sufficient.
```

Next step:

```text
Only a hedged / relative R07 requirement is allowed.
No long-only R07 is allowed.
```

### 21.8 `r06_factor_family_information_supported`

Meaning:

```text
At least one family passes family_information_supported and
family_tradeable_research_candidate gates.
```

Next step:

```text
R07 may write a narrow strategy requirement for the supported family and
train-selected horizon only.
```

This is not a strategy pass. It is permission to write the next requirement.

## 22. Final Decision Priority

E06 must replay final decisions using first-match priority.

Rule 01:

```text
if data_contract_ok = false
or execution_label_contract_ok = false
or matched_comparator_contract_ok = false
or split_purity_gate = false
then r06_blocked_data_or_execution_contract
```

Rule 02:

```text
else if included_factor_count < 100
then r06_factor_library_not_implementable_blocked
```

Rule 03:

```text
else if family_map_reproducible = false
then r06_family_map_not_reproducible_blocked
```

Rule 04:

```text
else if evaluable_family_count < 3
or all_horizon_label_sample_gate = false
then r06_insufficient_information_audit_sample_blocked
```

Coverage warning:

```text
partial_family_coverage_warning = true
```

when:

```text
3 <= evaluable_family_count < 5
```

This warning does not block final decision by itself, but `reports/r06_final_report.md` must explain the source of family coverage loss and must not overstate broad Alpha191 coverage.

Rule 05:

```text
else if exists family_tradeable_research_candidate = true
then r06_factor_family_information_supported
```

Rule 06:

```text
else if exists family_information_supported = true
and no family_tradeable_research_candidate = true
then r06_relative_information_only
```

Rule 07:

```text
else if exists family_gross_or_short_horizon_weak_information = true
then r06_decay_information_exists_but_not_tradeable
```

Rule 08:

```text
else r06_no_factor_information_support
```

Where:

```text
family_gross_or_short_horizon_weak_information = true
```

only if a family has a train-selected and train-oriented horizon where:

```text
train_selected_horizon_frozen = true
and (
  validation_top_decile_minus_bottom_decile_gross_return > 0
  or validation_family_oriented_mean_rankIC > 0
  or validation_top_decile_minus_bottom_decile_matched_delta_net > 0
)
```

but fails at least one of robustness, cost, monotonicity, persistent-name, or style clean gates.

## 23. Required Artifacts

R06 must write at least the following artifacts.

Audit:

```text
audit/r06_factor_registry.csv
audit/r06_factor_family_map.csv
audit/r06_horizon_label_panel_audit.csv
audit/r06_label_purge_audit.csv
audit/r06_factor_decay_rankic_panel.csv
audit/r06_family_decay_summary.csv
audit/r06_family_horizon_selection_train_only.csv
audit/r06_monotonicity_decile_audit.csv
audit/r06_decile_assignment_audit.csv
audit/r06_persistent_name_audit.csv
audit/r06_style_exposure_audit.csv
audit/r06_cost_sensitivity_audit.csv
audit/r06_execution_block_audit.csv
audit/r06_comparator_quality_audit.csv
audit/r06_validation_gate_audit.csv
```

Metrics:

```text
metrics/r06_factor_horizon_rankic_summary.csv
metrics/r06_family_horizon_rankic_summary.csv
metrics/r06_family_spread_summary.csv
metrics/r06_family_persistent_name_summary.csv
metrics/r06_family_style_exposure_summary.csv
metrics/r06_validation_robustness_consistency.csv
metrics/r06_information_decision_inputs.csv
```

Decision:

```text
decision/r06_final_decision_inputs.csv
decision/r06_final_decision_replay.csv
```

Reports and manifests:

```text
reports/r06_final_report.md
manifests/r06_validation.json
manifests/r06_artifact_hashes.json
```

Optional cache files are allowed under:

```text
ep5/outputs/r06_gtja191_factor_decay_information_content_audit_v0/cache/
```

Cache files are not required publish artifacts.

## 24. Final Report Required Questions

`reports/r06_final_report.md` must answer:

1. Did R06 avoid building a strategy or top20% exposure unit?
2. How many GTJA191 factors were included and excluded?
3. How were factors mapped to families?
4. Does Alpha191 still have short-horizon cross-sectional information?
5. What are the H1/H3/H5/H10/H20 RankIC decay curves?
6. Which horizons carry the strongest train evidence?
7. Which family horizons were selected by train only?
8. Which families, if any, keep validation information?
9. Which families, if any, keep robustness information?
10. Which families fail monotonic decile spread?
11. Which families are gross-positive but net-negative after cost?
12. Which families are persistent-name driven?
13. Which families are industry / liquidity / beta / volatility / money exposure driven?
14. Does any family show residual information after style neutralization?
15. Does any family justify a later R07 strategy requirement?
16. If R07 is allowed, must it be long-only or hedged / relative only?
17. If R06 fails, should the Alpha191 short-horizon direction pause?
18. Compared with R05 H10 validation's weak mean residual, negative median residual, 2023 reversal, and persistent-name concentration, does R06 explain the source of that pattern? Specifically, which family / horizon contributed the weak positive mean, and was it explained by persistent names or style exposure?

## 25. Validator Requirements

E06 validator must check:

1. `requirement_id` matches this document.
2. All required local data inputs exist.
3. No online data path or URL is used.
4. R06 does not emit a top20% strategy pass artifact.
5. Factor registry has 191 source rows.
6. Included factor count is replayable.
7. Family map exists and is marked pre-metric.
8. No family assignment uses performance columns.
9. Manual family overrides cite formula text, public taxonomy, or pre-declared taxonomy rules, not R04/R05 performance evidence.
10. H1/H3/H5/H10/H20 labels exist.
11. Split-pure label purge audit exists.
12. Matched comparator panel is replayable.
13. Gross and net labels are both present.
14. RankIC uses Spearman, not Pearson.
15. Family RankIC gates use train-oriented `family_oriented_*` fields, not raw signed family means.
16. Train-selected family horizons are chosen from train only.
17. Train-selected family horizons satisfy `valid_train_year_count >= 4`, `family_oriented_same_sign_year_count >= 3`, `family_oriented_single_year_ic_contribution_share <= 0.60`, `train_valid_date_count >= 70`, and `train_family_oriented_mean_rankIC > 0`.
18. Validation and robustness do not alter chosen horizons.
19. `partial_family_coverage_warning` is emitted when `3 <= evaluable_family_count < 5`.
20. Monotonicity decile audit and decile assignment audit exist.
21. Decile assignment uses deterministic score/instrument ordering and count-balanced buckets.
22. Persistent-name audit exists, uses union share for top5, and computes top-decile and top-quintile clean gates separately.
23. `all_horizon_label_sample_gate` is replayable from split / horizon purge gates, unpurged signal-date counts, and finite-label date share.
24. Style exposure audit exists and exposes the OLS R2, residualized spread, neutralized spread retention, aggregation method, and non-evaluable denominator flags.
25. Per-date style OLS does not include `market_state`; market state is readout-only.
26. Cost sensitivity audit exists and computes cost survival from long-only decile return spreads, not matched-delta spreads.
27. H1/H3 gross-only evidence cannot authorize long-only R07.
28. Final decision is in the allowed enum.
29. Final decision replay first-match priority reproduces final decision.
30. Report answers all required questions, including the R05 failure-shape reconciliation question.
31. Artifact hashes are written after final report generation.

## 26. Interpretation Boundary

R06 is allowed to say:

```text
Alpha191 contains short-horizon information, but it is not tradeable.
Alpha191 contains relative information only.
Alpha191 contains family-level information that justifies a narrow R07.
Alpha191 contains no reproducible information under current EP5.
```

R06 is not allowed to say:

```text
Alpha191 strategy passed.
GTJA191 long-only alpha passed.
Top20% selected basket is supported.
R05 can be rescued by tuning.
Validation-positive family should be traded directly.
```

The strongest positive R06 conclusion is only:

```text
R07 may be written for a specific supported family and train-selected horizon.
```

## 27. Stop Conditions

If final decision is:

```text
r06_no_factor_information_support
```

then the Alpha191 / GTJA191 short-horizon research line under the current EP5 universe and execution contract should pause.

If final decision is:

```text
r06_decay_information_exists_but_not_tradeable
```

then no direct strategy requirement should be written from R06. The evidence may be archived as diagnostic background only, or used for a non-strategy cost-revisited / hedged-only diagnostic successor if the report explicitly justifies that narrower question.

If final decision is:

```text
r06_relative_information_only
```

then the only allowed R07 direction is hedged / market-relative feasibility.

If final decision is:

```text
r06_factor_family_information_supported
```

then R07 must be narrow:

- one or more named supported families only;
- train-selected horizon only;
- no validation-selected additional factors;
- explicit persistent-name and style exposure controls inherited from R06;
- no claim of long-only pass unless R07 independently proves it.

Additional horizon / cost boundary:

```text
if train-selected horizon in {H1, H3}
and evidence passes only on gross return spread or gross RankIC
and net return spread / cost survival does not pass,
then gross_only_short_horizon_blocked = true.
```

This condition cannot produce `r06_factor_family_information_supported`. It may only appear under `r06_decay_information_exists_but_not_tradeable` or, if matched-delta information is clean but long-only cost does not survive, `r06_relative_information_only`. Long-only R07 is never allowed from H1/H3 gross-only evidence because H1/H3 information can be real but economically unusable under the inherited 110 bps round-trip cost.

## 28. One-line Summary

R06 does not try to make Alpha191 trade.

R06 only asks whether Alpha191 still contains reproducible, short-horizon, residual information worth turning into a later, narrow R07 strategy requirement.
