# EP5 Requirement 04: GTJA191 Short-Horizon Residual Composite Feasibility V0

## 1. Requirement Metadata

requirement_id: `ep5_r04_gtja191_short_horizon_residual_composite_feasibility_v0`

short_name: `r04_gtja191_short_horizon_residual_composite_feasibility_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-22`

primary_output_namespace: `ep5/outputs/r04_gtja191_short_horizon_residual_composite_feasibility_v0/`

upstream_requirements:

- `ep5/requirement_01_short_horizon_local_feasibility_probe_v1.md`
- `ep5/requirement_02_simple_rs20_continuation_v0.md`
- `ep5/requirement_03_downside_volatility_shock_rebound_natural_exit_v0.md`

upstream_reports:

- `ep5/outputs/r01_short_horizon_local_feasibility_probe_v1/reports/r01_final_report.md`
- `ep5/outputs/r02_simple_rs20_continuation_v0/reports/r02_final_report.md`
- `ep5/outputs/r03_downside_volatility_shock_rebound_natural_exit_v0/reports/r03_final_report.md`

external_formula_references:

- DolphinDB GTJA 191 Alpha module documentation: <https://docs.dolphindb.com/zh/modules/gtja191Alpha/191alpha.html>
- JoinQuant Alpha191 factor dictionary: <https://joinquant.com/data/dict/alpha191>

These external references are formula-library references only. They do not establish current profitability under this repository's PIT universe, execution, cost, split, or validation contract.

## 2. Upstream Motivation

R01, R02, and R03 tested increasingly different hand-written short-horizon exposures:

- R01 tested local short-horizon feasibility around the original discussion units.
- R02 tested simple RS20 continuation.
- R03 tested downside volatility shock rebound after short-term selloff and stabilization.

The important R03 observation is not that the downside rebound idea should be tuned further. R03 ended with `r03_no_downside_rebound_support`, but its H10 validation quadrant was `absolute_false__relative_true`: the absolute long-only gate failed, while matched-comparator relative evidence showed a directional lead that was not robust enough, was sample-limited, and had baseline evaluability failure.

Therefore R04 must not continue by tuning R03 thresholds such as `ret5`, volatility rank, stabilization, or money repair. The next valid direction is to move from sparse hand-written event rules to a wider, denser, train-frozen short-cycle price-volume feature representation.

GTJA191 / Alpha191 is suitable for that role because it is a public short-horizon price-volume factor library. In R04 it is not a ready-made strategy and not a proof that the original report's historical performance still exists. It is only a fixed feature library used to test whether a simple residual ranking composite has local support under the EP5 contract.

## 3. Core Question

R04 asks:

```text
Within the current PIT mcap500 mainboard universe,
weekly close-observed signal cadence,
next-open execution,
110 bps round-trip cost,
fixed H5 / H10 / H20 natural exits,
and R01/R02/R03 matched-comparator discipline,
can a train-only frozen GTJA191 directional equal-weight composite produce
a stable H10 residual ranking edge?
```

The primary target is not raw long-only net return. The primary target is H10 residual edge measured against matched comparators and checked against a same-day nonselected liquid baseline.

R04 can still pass as long-only only if absolute and relative gates both pass. But the most important diagnostic quadrant is `absolute_false__relative_true`: it would mean the feature library has stock-level residual information that may require hedged or relative feasibility work rather than direct long-only deployment.

## 4. Non-Goals

R04 is not allowed to become a broad alpha search.

R04 must not:

- replicate or validate the original GTJA research report's historical return claims;
- use the original 2012-2017 results as evidence for the 2022-2025 validation/robustness period;
- run 191 factors one by one in validation and keep the best factors;
- choose top 5%, top 10%, top 20%, or top 30% by validation performance;
- search H5, H10, and H20 as candidate primary horizons;
- add RS20 continuation, downside rebound, volatility, regime, or market-state filters;
- use validation or robustness data to choose factor direction;
- use validation or robustness data to choose factor inclusion;
- use IC weighting, t-stat weighting, LGBM, neural networks, linear models, PCA, autoencoders, dynamic weights, or model search;
- add stop-loss, take-profit, layered exit, re-entry, or portfolio optimizer logic;
- treat big-winner or right-tail readouts as pass/fail gates;
- create a positive conclusion from audit-only decompositions.

Any E04 implementation that needs one of the above to produce a positive result must stop and return to requirement revision.

## 5. Canonical Units

Only one R04 unit has final-decision authority.

### 5.1 Primary Unit

canonical_unit_id:

```text
r04_gtja191_train_direction_equal_weight_residual_composite_v0
```

Meaning:

- compute as-of-D GTJA191 factor values for eligible PIT universe members;
- cross-sectionally clean and rank-normalize each factor on each weekly signal date;
- learn each factor's sign using train-only H10 matched-delta RankIC;
- freeze factor directions before validation;
- form a simple equal-weight composite;
- select weekly top 20% by composite score;
- evaluate selected events under fixed H5 / H10 / H20 natural exits.

### 5.2 Baseline Unit

baseline_unit_id:

```text
r04_weekly_nonselected_liquid_baseline_v0
```

Meaning:

- same signal date D;
- same PIT universe and eligibility filters;
- same executable entry / exit / cost rules;
- all eligible stocks not selected by the top-20% composite;
- used only for date-level lift and market-wide rebound/beta differentiation.

The baseline cannot create a positive decision by itself.

### 5.3 Audit-Only Units

The following are allowed as audit-only outputs:

- factor formula registry;
- factor coverage and missingness audit;
- train-only factor direction audit;
- score distribution audit;
- score quintile or decile readout;
- industry / liquidity / beta / market-state decomposition;
- right-tail / large-winner readout.

Audit-only outputs cannot override §15 final-decision priority.

## 6. Data Contract

R04 inherits the EP5 local data boundary.

Input data must come from the local PIT Qlib provider already used by R01/R02/R03. E04 must not fetch market data online during the run.

Required raw fields:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `money`
- `vwap = money / volume`
- benchmark index `SH000300` `open`
- benchmark index `SH000300` `close`

Required PIT universe:

```text
PIT mcap500 mainboard universe
```

R04 must preserve the same delisting, suspension, ST, board, and point-in-time membership treatment inherited from R01/R02/R03. If E04 cannot reproduce that inherited universe contract exactly, the run must stop as `r04_blocked_data_or_execution_contract`.

## 7. Split Contract

R04 inherits the frozen EP5 split:

```text
train:      2017-07-04 through 2021-12-31
validation: 2022-01-01 through 2023-12-31
robustness: 2024-01-01 through 2025-12-31
```

Train is allowed only for:

- formula implementability checks that do not use outcomes;
- factor coverage / degeneracy checks that do not use outcomes;
- factor direction learning using train-only H10 matched-delta RankIC;
- composite formula finalization before validation.

Train is not allowed to:

- choose a top subset of factors by performance;
- choose composite weights by performance;
- tune the selected top fraction;
- tune costs, horizons, execution rules, comparator rules, or sample gates.

Validation and robustness are not allowed to change:

- factor formulas;
- included factor list after formula/coverage gates;
- factor directions;
- factor weights;
- top fraction;
- horizon set;
- comparator, baseline, or final-decision rules.

## 8. Execution Contract

R04 inherits the R01/R02/R03 execution contract.

signal_date:

```text
Each ISO week's final trading day, observed after close.
```

entry:

```text
First executable next open after signal_date.
```

exit:

```text
Natural exit at H5 / H10 / H20 trading-day horizons.
```

cost:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
```

R04 must not add stop-loss, take-profit, early exit, re-entry, position sizing, cash allocation, or portfolio optimizer logic.

Repeated weekly selection of the same instrument is allowed because R04 is a dense ranking feasibility probe, not a sparse event-collapsed signal. E04 must audit repeated-instrument and active-overlap concentration, but it must not introduce a new same-instrument collapse rule unless R04 is revised.

## 9. Factor Formula Contract

### 9.1 Formula Source

E04 must materialize a local GTJA191 formula registry before running outcomes.

Required artifact:

```text
ep5/outputs/r04_gtja191_short_horizon_residual_composite_feasibility_v0/audit/r04_gtja191_factor_registry.csv
```

The registry must include:

- `factor_id`
- `source_name`
- `source_formula_text`
- `source_formula_hash`
- `local_formula_hash`
- `required_fields`
- `max_lookback_trading_days`
- `asof_safe`
- `factor_status`
- `exclusion_reason`

Allowed `factor_status` values:

- `included`
- `excluded_not_asof_safe`
- `excluded_missing_required_field`
- `excluded_insufficient_cross_section_coverage`
- `excluded_constant_or_degenerate`
- `excluded_formula_implementation_failed`

Factor exclusion is allowed only for formula availability, as-of safety, missing required fields, insufficient coverage, degeneracy, or implementation failure. Factor exclusion must not use validation or robustness performance.

### 9.2 Minimum Feature-Library Viability

R04 requires a sufficiently broad feature library.

Frozen constants:

```text
min_included_factor_count = 120
min_train_factor_coverage_date_count = 150
min_train_factor_cross_section_count_per_date = 100
min_instrument_valid_factor_share = 0.60
min_direction_active_factor_count = 80
```

If fewer than `min_included_factor_count` factors survive formula/coverage gates, the final decision must be:

```text
r04_factor_library_not_implementable_blocked
```

If fewer than `min_direction_active_factor_count` factors receive nonzero train-only direction, the final decision must be:

```text
r04_factor_direction_learning_not_viable_blocked
```

These are data/formula contract failures, not economic failures.

## 10. Eligibility Contract

For each signal date D, an instrument is eligible for score ranking only if all of the following hold as-of D:

- instrument is a PIT universe member;
- instrument is mainboard under inherited EP5 board classification;
- `avg_money20_D >= 50,000,000`;
- `open_D`, `high_D`, `low_D`, `close_D`, `volume_D`, `money_D` exist;
- `close_D > 0`;
- `volume_D > 0`;
- `money_D > 0`;
- `vwap_D = money_D / volume_D` is finite;
- at least `min_instrument_valid_factor_share` of included factor values are finite after factor computation.

Frozen cross-section constants:

```text
min_eligible_cross_section_count = 300
selected_top_fraction = 0.20
min_selected_count_per_signal_date = 50
min_nonselected_count_per_signal_date = 200
```

If a weekly signal date has fewer than `min_eligible_cross_section_count` eligible instruments after factor coverage checks, that date is excluded from event creation and must be audited as:

```text
blocked_insufficient_eligible_cross_section
```

If selected or nonselected counts fail their frozen floors, that date is excluded from event creation and must be audited as:

```text
blocked_insufficient_selected_or_baseline_count
```

## 11. Factor Processing

For each included factor and each signal date D:

1. Compute raw factor values using only data available on or before D.
2. Replace nonfinite values with missing.
3. Winsorize finite raw factor values cross-sectionally at the 1st and 99th percentiles.
4. Convert winsorized values to average-rank percentile within the eligible cross-section.
5. Normalize factor rank as:

```text
normalized_alpha_i = rank_pct_i - 0.5
```

This produces factor values in approximately `[-0.5, +0.5]`.

Tie handling:

```text
Use average rank for tied values.
```

Missing values remain missing and are not imputed.

No validation-period or robustness-period statistics may be used in normalization.

## 12. Train-Only Direction Learning

Factor direction is learned once in train and then frozen.

For each included factor `alpha_i`:

1. For every train signal date D, compute `normalized_alpha_i(D, instrument)`.
2. For every train candidate instrument with complete execution, compute the H10 matched-delta label:

```text
label_i(D, instrument) = H10_net_return(D, instrument) - H10_matched_comparator_net_return(D, instrument)
```

During train direction learning, the composite selected set does not exist yet. Therefore the H10 matched comparator pool for a train candidate is the same-date eligible universe excluding the target instrument, subject to the inherited industry / liquidity / beta matching rules. Train direction learning must not use the later top-20% selected/nonselected assignment.

3. For each train date D with at least `min_train_factor_cross_section_count_per_date` labeled candidates, compute Spearman rank correlation:

```text
date_rankIC_i(D) = corr_rank(normalized_alpha_i(D, .), label_i(D, .))
```

4. Compute:

```text
mean_train_rankIC_i = mean(date_rankIC_i(D))
```

5. Freeze direction:

```text
direction_i = +1 if mean_train_rankIC_i > 0
direction_i = -1 if mean_train_rankIC_i < 0
direction_i =  0 if mean_train_rankIC_i = 0 or nonfinite
```

If a factor has fewer than `min_train_factor_coverage_date_count` valid train IC dates, set:

```text
direction_i = 0
direction_status = direction_zero_insufficient_train_label_coverage
```

Direction learning must not use validation or robustness outcomes.

No IC magnitude threshold, t-stat threshold, p-value threshold, or top-factor selection rule is allowed. Direction is sign-only.

## 13. Composite Score

For each signal date D and eligible instrument:

```text
score_raw(D, instrument)
  = mean(direction_i * normalized_alpha_i(D, instrument))
    over included factors where direction_i in {-1, +1}
    and normalized_alpha_i is finite
```

The denominator counts only active factors with `direction_i in {-1, +1}` and finite values for that instrument/date. Factors with `direction_i = 0` must not enter the numerator or denominator.

Then compute cross-sectional average-rank percentile for audit:

```text
score_rank_pct(D, instrument)
```

Primary selection:

```text
selected_count_target(D) = ceil(selected_top_fraction * eligible_count(D))
selected = first selected_count_target(D) instruments after sorting by:
  score_raw descending,
  instrument_id ascending
```

This is fixed top 20% with deterministic rounding and tie-break. `score_rank_pct` is an audit field and must not be used as the authoritative selected-count rule.

R04 must not test alternative top fractions.

Required score audit fields:

- `signal_date`
- `eligible_count`
- `selected_count_target`
- `selected_count`
- `nonselected_count`
- `top1_instrument_selected_week_share`
- `active_factor_count_min`
- `active_factor_count_p10`
- `active_factor_count_median`
- `score_raw_mean`
- `score_raw_std`
- `score_tie_share`
- `selected_repeated_instrument_share`
- `active_overlap_share_H5`
- `active_overlap_share_H10`
- `active_overlap_share_H20`
- `effective_independent_event_count_H5`
- `effective_independent_event_count_H10`
- `effective_independent_event_count_H20`

## 14. Comparator and Baseline Contract

### 14.1 Matched Comparator

R04 inherits the R01/R02/R03 matched-comparator contract.

Matched comparator must be same-date, nonselected when possible, and matched by industry / liquidity / beta according to the existing EP5 comparator implementation.

For train direction labels, "nonselected" means only "not the target instrument" because the composite selected set has not yet been formed. For validation and robustness outcome evaluation, matched comparators should exclude the selected event instrument and should prefer nonselected liquid baseline constituents when available.

Fallback comparator use must be audited. Fallback quality is weak if:

```text
fallback_comparator_share > 0.30
```

Weak comparator quality must block positive relative conclusions.

### 14.2 Same-Day Nonselected Liquid Baseline

For each signal date D and horizon H, baseline is all eligible instruments that are not selected by the top-20% composite and are executable under the same H-specific entry/exit path.

baseline_comparison_status(D, H) must be one of:

- `comparable`
- `blocked_insufficient_baseline_constituents`
- `blocked_primary_date_not_evaluable`

Frozen baseline threshold:

```text
min_complete_nonselected_baseline_count_per_date_horizon = 200
```

If a primary selected date is evaluable and the nonselected complete baseline count is at least 200 for that same `(D, H)`, then:

```text
baseline_comparison_status(D, H) = comparable
```

If a primary selected date is evaluable but the complete baseline count is below 200:

```text
baseline_comparison_status(D, H) = blocked_insufficient_baseline_constituents
```

If no selected primary events are evaluable on `(D, H)`:

```text
baseline_comparison_status(D, H) = blocked_primary_date_not_evaluable
```

Baseline metrics are computed per `(split, horizon, signal_date)`:

```text
selected_equal_weight_net_return(D, H)
nonselected_baseline_equal_weight_net_return(D, H)
baseline_lift(D, H)
  = selected_equal_weight_net_return(D, H)
    - nonselected_baseline_equal_weight_net_return(D, H)
```

## 15. Gate Definitions

All gates below use final executable events after execution blocking and cost.

Unless explicitly stated otherwise, gate functions are parameterized as `(split, H)`. In the H10 validation decision path, shorthand such as `sample_status(H10)` means `sample_status(validation, H10)`. Inside `robustness_confirmed`, gate names refer to `robustness` split. Inside `adjacent_horizon_clean`, gate names refer to validation split H5/H20.

Empty calendar-year rows are excluded from year-level gates and must be separately audited. A split cannot pass a year-level gate by silently including empty years as zero.

### 15.1 Sample Gate

For H10 validation:

```text
complete_event_count >= 3000
complete_event_share >= 0.95
decision_observation_date_count >= 70
min_year_complete_event_count >= 1000
min_year_decision_observation_date_count >= 30
```

sample_status values:

- `pass`
- `sample_limited_lead`
- `blocked_insufficient_sample`
- `blocked_insufficient_execution_completeness`
- `blocked_insufficient_date_independence_sample`

Rules:

```text
pass:
  all sample gate conditions hold

blocked_insufficient_sample:
  complete_event_count < 1500

blocked_insufficient_execution_completeness:
  complete_event_count >= 1500
  AND complete_event_share < 0.95

sample_limited_lead:
  complete_event_count >= 1500
  AND complete_event_count < 3000
  AND complete_event_share >= 0.95
  AND decision_observation_date_count >= 50

blocked_insufficient_date_independence_sample:
  complete_event_count >= 1500
  AND complete_event_share >= 0.95
  AND the pass condition does not hold
  AND the sample_limited_lead condition does not hold
```

This status order is exhaustive. E04 must assign the first matching status in the order shown above.

### 15.2 Concentration Gate

H10 validation concentration gate passes only if:

```text
top1_instrument_event_share <= 0.02
top5_instrument_event_share <= 0.08
top1_instrument_selected_week_share <= 0.50
top1_industry_event_share <= 0.25
top1_observation_date_event_share <= 0.03
top5_observation_date_event_share <= 0.15
top1_observation_date_profit_contribution_share <= 0.15
fallback_comparator_share <= 0.30
```

The concentration gate is designed for a dense weekly ranking system. It is intentionally stricter than sparse event probes on date concentration.

The `top1_instrument_event_share` floor is not expected to be the binding protection in a dense weekly system because a stock selected every week can still have low total event share. The binding repeated-name protection is `top1_instrument_selected_week_share` plus the active-overlap gate below.

### 15.2.1 Active Overlap Gate

`active_overlap_gate(split, H)` is true only if that split and horizon H satisfy:

```text
median_active_overlap_share_H <= 0.85
p90_active_overlap_share_H <= 0.95
effective_independent_event_count_H >= 1000
```

For readability, `active_overlap_gate(H)` without an explicit split means `active_overlap_gate(validation, H)` unless it appears inside `robustness_confirmed`.

`active_overlap_share_H(D)` is the share of selected events on signal date D whose instrument already has at least one prior selected event that has not reached its natural H-day exit.

`effective_independent_event_count_H` is computed by merging overlapping selected events for the same instrument into one active-entry cluster per horizon H, then counting those clusters. This gate does not collapse the return panel; it prevents repeated weekly selections of the same names from masquerading as independent evidence.

### 15.3 Date Independence Gate

H10 validation date independence passes only if:

```text
decision_observation_date_count >= 70
min_year_decision_observation_date_count >= 30
top1_observation_date_event_share <= 0.03
top5_observation_date_event_share <= 0.15
top1_observation_date_profit_contribution_share <= 0.15
```

### 15.4 Absolute Positive Gate

`absolute_positive(H10)` is true only if all of the following hold on validation:

```text
mean_net_return > 0
median_net_return >= -0.0025
p10_net_return >= -0.08
loss_rate <= 0.55
every non-empty validation calendar-year mean_net_return >= -0.0025
```

### 15.5 Relative Positive Gate

`relative_positive(H10)` is true only if all of the following hold on validation:

```text
mean_matched_delta_return > 0
fallback_comparator_share <= 0.30
every non-empty validation calendar-year mean_matched_delta_return >= -0.0025
```

and at least two of the following three conditions hold:

```text
median_matched_delta_return >= 0
p10_matched_delta_return >= -0.08
matched_loss_rate_delta <= -0.03
```

The `-0.03` floor on `matched_loss_rate_delta` is intentionally stricter than R02/R03 because the dense ranking system has materially lower per-event sampling noise. A residual edge claim must show measurable distributional improvement, not only mean drift.

### 15.6 Baseline Lift Gate

`baseline_lift_evaluable(H10)` is true only if:

```text
baseline_comparable_observation_date_count >= 70
min_year_baseline_comparable_observation_date_count >= 30
```

`baseline_lift_gate(H10)` is true only if `baseline_lift_evaluable(H10)` is true and:

```text
mean_baseline_lift > 0
median_baseline_lift >= 0
every non-empty validation calendar-year mean_baseline_lift >= -0.0025
```

If `baseline_lift_evaluable(H10) = false`, then `baseline_lift_gate(H10) = false`.

The R04 baseline-lift distribution check is intentionally lighter than R02/R03 because each weekly observation aggregates many selected names and at least 200 complete nonselected baseline names. Date-level mean and median already absorb most distribution information; per-event p10 and loss-rate deltas are reported in audit but do not enter this gate.

### 15.7 H10 Validated Pass

`h10_validated_pass` is true only if all of the following hold:

```text
sample_status(H10) = pass
concentration_gate(H10) = true
active_overlap_gate(H10) = true
date_independence_gate(H10) = true
absolute_positive(H10) = true
relative_positive(H10) = true
```

`h10_validated_pass` does not include baseline lift or robustness. Those are separate gates for final-decision authority.

`horizon_pass(H)` for H5 or H20 uses the same gate combination as `h10_validated_pass`, applied to that horizon with the same §15.1-§15.5 constants:

```text
sample_status(H) = pass
concentration_gate(H) = true
active_overlap_gate(H) = true
date_independence_gate(H) = true
absolute_positive(H) = true
relative_positive(H) = true
```

Rule 14 in §17 must read this as:

```text
(horizon_pass(H5) = true OR horizon_pass(H20) = true)
AND h10_validated_pass = false
```

### 15.8 Multi-Comparator Relative Status

`multi_comparator_relative_status(H10)` must be one of:

- `stable`
- `unstable`
- `unavailable`

`multi_comparator_relative_status(H10) = stable` only if:

```text
relative_positive(H10) = true
fallback_comparator_share <= 0.30
industry_matched_delta_mean > 0
liquidity_matched_delta_mean > 0
beta_matched_delta_mean > 0
```

`multi_comparator_relative_status(H10) = unstable` if all required comparator families are available and either:

- `relative_positive(H10) = false`; or
- `relative_positive(H10) = true` but at least one required comparator-family delta mean is `<= 0`.

`multi_comparator_relative_status(H10) = unavailable` if any required comparator family is unavailable.

For backward-readable rules:

```text
multi_comparator_relative_stable(H10) = true
  iff multi_comparator_relative_status(H10) = stable
```

### 15.9 Robustness Confirmed

`robustness_confirmed(H10)` is true only if robustness split H10 satisfies:

```text
complete_event_count >= 3000
complete_event_share >= 0.95
decision_observation_date_count >= 70
min_year_complete_event_count >= 1000
min_year_decision_observation_date_count >= 30
concentration_gate(robustness, H10) = true
active_overlap_gate(robustness, H10) = true
mean_net_return >= -0.0025
median_net_return >= -0.005
p10_net_return >= -0.10
mean_matched_delta_return >= -0.0025
fallback_comparator_share <= 0.30
baseline_lift_evaluable(robustness, H10) = true
mean_baseline_lift >= -0.0025
```

In §§16-17, `robustness_confirmed` without a horizon means `robustness_confirmed(H10)`.

Unless a gate is explicitly described as a robustness gate, all gate names in §17 refer to validation split values. Robustness split values are used only inside `robustness_confirmed(H10)`.

### 15.10 Adjacent Horizon Clean

`adjacent_horizon_clean` is true only if both H5 and H20 validation are evaluable and each adjacent horizon H in `{H5, H20}` satisfies:

```text
complete_event_count >= 1500
decision_observation_date_count >= 50
active_overlap_gate(validation, H) = true
mean_net_return >= -0.005
mean_matched_delta_return >= -0.005
fallback_comparator_share <= 0.30
```

H5 or H20 cannot create the primary positive decision. They can only block a fragile H10 pass or produce a horizon-specific lead.

## 16. Four-Quadrant Interpretation

R04 retains the EP5 four-quadrant interpretation.

| H10 validation quadrant | Meaning | Allowed next step |
| --- | --- | --- |
| `absolute_true__relative_true` | GTJA191 composite has both long-only and residual local support. | Continue only if baseline lift, robustness, and adjacent horizons are clean. |
| `absolute_false__relative_true` | GTJA191 composite has residual ranking evidence but not direct long-only support. | Consider hedged / relative feasibility only if baseline lift, robustness, adjacent horizons, and multi-comparator status are explicitly clean or flagged by §17. |
| `absolute_true__relative_false` | Likely beta, regime, or style exposure without stock-selection evidence. | Do not enter stock-selection search. |
| `absolute_false__relative_false` | No local support under current contract. | Pause EP5 short-horizon long-only stock-level alpha mainline unless a new requirement changes the question. |

The `absolute_false__relative_true` quadrant must not be reported as a long-only alpha pass.

## 17. Final Decision Priority

Final decision uses first-match priority. Later rules cannot override earlier rules.

Allowed `final_decision` values:

- `r04_factor_library_not_implementable_blocked`
- `r04_factor_direction_learning_not_viable_blocked`
- `r04_blocked_data_or_execution_contract`
- `r04_gtja191_residual_composite_supported_continue_research`
- `r04_baseline_not_evaluable_validation_lead`
- `r04_relative_residual_edge_only_hedged_or_regime_audit_required`
- `r04_comparator_unavailable_validation_lead`
- `r04_absolute_only_baseline_lift_no_relative_pass`
- `r04_beta_or_style_exposure_only_no_stock_selection_pass`
- `r04_unstable_validation_only_lead`
- `r04_unstable_horizon_shape_no_search_allowed`
- `r04_adjacent_horizon_not_evaluable_validation_lead`
- `r04_horizon_specific_lead_only_no_search_allowed`
- `r04_sample_limited_primary_lead_only`
- `r04_no_gtja191_residual_composite_support`

Rules:

1. If PIT universe, split, raw fields, factor registry, execution, cost, or comparator contract cannot be reproduced exactly, output `r04_blocked_data_or_execution_contract`.

2. If included factor count is below `min_included_factor_count`, output `r04_factor_library_not_implementable_blocked`.

3. If nonzero train-direction factor count is below `min_direction_active_factor_count`, output `r04_factor_direction_learning_not_viable_blocked`.

4. If `h10_validated_pass = true`, `baseline_lift_gate(H10) = true`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_gtja191_residual_composite_supported_continue_research`.

5. If `h10_validated_pass = true`, `baseline_lift_evaluable(H10) = false`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_baseline_not_evaluable_validation_lead`.

6. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = false`, `relative_positive(H10) = true`, `baseline_lift_gate(H10) = true`, `multi_comparator_relative_status(H10) = stable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_relative_residual_edge_only_hedged_or_regime_audit_required`.

7. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = false`, `relative_positive(H10) = true`, `baseline_lift_gate(H10) = true`, `multi_comparator_relative_status(H10) = unstable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_relative_residual_edge_only_hedged_or_regime_audit_required` and set `multi_comparator_unstable_subflag = true` in `r04_final_decision_inputs.csv`.

8. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = false`, `relative_positive(H10) = true`, `baseline_lift_gate(H10) = true`, `multi_comparator_relative_status(H10) = unavailable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_comparator_unavailable_validation_lead` and set `multi_comparator_unavailable_subflag = true` in `r04_final_decision_inputs.csv`.

9. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = false`, `relative_positive(H10) = true`, `baseline_lift_evaluable(H10) = false`, `multi_comparator_relative_status(H10) != unavailable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_baseline_not_evaluable_validation_lead`.

10. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = false`, `relative_positive(H10) = true`, `baseline_lift_evaluable(H10) = false`, `multi_comparator_relative_status(H10) = unavailable`, `robustness_confirmed = true`, and `adjacent_horizon_clean = true`, output `r04_comparator_unavailable_validation_lead` and set `multi_comparator_unavailable_subflag = true` in `r04_final_decision_inputs.csv`.

11. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = true`, `relative_positive(H10) = false`, and `baseline_lift_gate(H10) = true`, output `r04_absolute_only_baseline_lift_no_relative_pass`.

12. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, `absolute_positive(H10) = true`, and `relative_positive(H10) = false`, output `r04_beta_or_style_exposure_only_no_stock_selection_pass`.

13. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, and H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, but robustness is not confirmed, output `r04_unstable_validation_only_lead`.

14. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, and H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, but either H5 or H20 is not evaluable, output `r04_adjacent_horizon_not_evaluable_validation_lead`.

15. If `sample_status(H10) = pass`, `concentration_gate(H10) = true`, `active_overlap_gate(H10) = true`, `date_independence_gate(H10) = true`, H10 validation has `absolute_positive(H10) = true` or `relative_positive(H10) = true`, and both H5 and H20 are evaluable, but `adjacent_horizon_clean = false`, output `r04_unstable_horizon_shape_no_search_allowed`.

16. If `(horizon_pass(H5) = true OR horizon_pass(H20) = true)` and `h10_validated_pass = false`, output `r04_horizon_specific_lead_only_no_search_allowed`.

17. If H10 sample status is `sample_limited_lead` and either absolute or relative evidence is positive, output `r04_sample_limited_primary_lead_only`.

18. Otherwise output `r04_no_gtja191_residual_composite_support`.

Note on rules 11 and 12:

Rule 11 is more informative than rule 12 when baseline lift is true. Therefore E04 final-decision replay must preserve the listed order. The report must show the replayed ordered rule list exactly as implemented.

Rules 11 and 12 do not subdivide on robustness because the absolute-only outcome is already a downgrade and robustness instability does not change the structural conclusion: R04 has no stock-selection residual pass. Robustness status must still be reported in audit.

## 18. Required Artifacts

E04 must write the following artifacts.

### 18.1 Audit Artifacts

```text
audit/r04_run_manifest.json
audit/r04_input_data_audit.csv
audit/r04_gtja191_factor_registry.csv
audit/r04_factor_coverage_audit.csv
audit/r04_factor_direction_audit.csv
audit/r04_train_rankic_by_factor_date.csv
audit/r04_score_cross_section_audit.csv
audit/r04_execution_block_audit.csv
audit/r04_comparator_quality_audit.csv
audit/r04_baseline_comparison_audit.csv
```

### 18.2 Event and Outcome Artifacts

```text
events/r04_selected_event_panel.csv
events/r04_execution_event_panel.csv
events/r04_matched_comparator_panel.csv
events/r04_nonselected_baseline_panel.csv
metrics/r04_split_horizon_summary.csv
metrics/r04_year_horizon_summary.csv
metrics/r04_baseline_lift_summary.csv
metrics/r04_score_bucket_readout.csv
metrics/r04_decomposition_summary.csv
metrics/r04_right_tail_readout.csv
decision/r04_gate_inputs.csv
decision/r04_final_decision_inputs.csv
decision/r04_final_decision_replay.csv
reports/r04_final_report.md
```

## 19. Report Requirements

`reports/r04_final_report.md` must be written in Chinese.

The report must answer:

1. What is the final decision and which priority rule triggered it?
2. How many GTJA191 factors were implementable, included, excluded, and direction-active?
3. What were the main exclusion reasons?
4. What is the train-only RankIC direction distribution?
5. Did the composite use equal weights and fixed top 20% without validation tuning?
6. How many H10 validation events, dates, years, selected instruments, and industries were evaluated?
7. Did H10 validation pass absolute, relative, baseline, concentration, active-overlap, and date-independence gates?
8. If relative failed, which specific relative sub-gate failed?
9. If absolute failed, which specific distribution or yearly stability condition failed?
10. Did validation evidence survive robustness?
11. Did H5 and H20 confirm or contradict H10?
12. Did selected top-20% outperform the same-day nonselected liquid baseline?
13. Was the matched comparator clean, including `multi_comparator_relative_status`, or was fallback usage too high?
14. Is the outcome best read as long-only alpha, residual ranking edge, beta/style exposure, or no support?
15. How should R04 map back to the R01/R02/R03 failure path?

If the final quadrant is `absolute_false__relative_true`, the report must explicitly state that this is not a long-only pass.

If R04 fails but shows stable relative evidence, the report may recommend a hedged / relative feasibility requirement. It must not recommend validation-driven factor selection or top-fraction tuning.

## 20. Validator Requirements

E04 must include a validator that fails the run if any of the following is false:

1. Split dates exactly match §7.
2. PIT universe path and inherited universe filters match R01/R02/R03.
3. No online market-data fetch occurred during run.
4. Required raw fields exist and are as-of safe.
5. Factor formula registry exists and includes formula hashes.
6. Factor exclusion reasons are limited to §9 allowed reasons.
7. Included factor count is at least `min_included_factor_count`, unless final decision is `r04_factor_library_not_implementable_blocked`.
8. Direction learning uses train-only H10 matched-delta RankIC.
9. Direction-active factor count is at least `min_direction_active_factor_count`, unless final decision is `r04_factor_direction_learning_not_viable_blocked`.
10. Validation and robustness do not alter factor direction.
11. Composite weights are equal-weight across nonzero-direction available factors.
12. No model, IC weighting, t-stat weighting, factor subset search, or dynamic weighting fields exist.
13. Selected count equals `ceil(0.20 * eligible_count)` on every evaluable signal date, using `score_raw desc, instrument_id asc` as deterministic tie-break.
14. No RS20, downside rebound, volatility shock, regime, or market-state filter is applied to primary selection.
15. Execution, cost, horizon, and weekly cadence match §8.
16. Matched comparator and nonselected baseline are both present and distinct.
17. Train direction comparator labels do not use later top-20% selected/nonselected assignment.
18. Baseline comparison status is one of the three enumerated §14.2 values for every `(D, H)`.
19. Empty calendar-year rows are excluded from year-level gates and separately audited.
20. Sample, concentration, active-overlap, date-independence, absolute, relative, baseline, robustness, and adjacent-horizon gates are computed from frozen §15 definitions.
21. `sample_status` is assigned by the exhaustive first-match status order in §15.1.
22. Final decision replay follows §17 first-match priority.
23. Rules 6-8 relative-only decisions with `baseline_lift_gate(H10) = true` require `robustness_confirmed = true` and `adjacent_horizon_clean = true`.
24. Rule 7 multi-comparator-unstable relative lead must set `multi_comparator_unstable_subflag = true`; rule 8 multi-comparator-unavailable lead must set `multi_comparator_unavailable_subflag = true`.
25. Rules 9-10 baseline-not-evaluable relative leads cannot be used when robustness or adjacent horizons fail.
26. Big-winner and right-tail outputs are read-only and do not affect final decision.
27. The final report is Chinese and answers all §19 questions.

## 21. Relationship to E01 / E02 / E03 / E04

E01/E02/E03 already define and exercise the EP5 harness for:

- PIT universe;
- split;
- weekly signal cadence;
- next-open execution;
- H5/H10/H20 natural exits;
- 110 bps round-trip cost;
- matched comparator;
- fallback comparator audit;
- nonselected baseline;
- concentration gates;
- date-independence gates;
- final-decision replay;
- Chinese final report.

E04 must reuse that harness. E04 is allowed to extend only:

- GTJA191 factor formula builders;
- factor registry and formula hash audit;
- factor coverage audit;
- train-only H10 matched-delta RankIC direction learning;
- equal-weight composite score construction;
- weekly top-20% selected event construction;
- nonselected liquid baseline for top-20% ranking;
- R04-specific §15 gates and §17 final-decision priority;
- R04-specific validator checks.

E04 must not redefine:

- universe membership;
- split dates;
- weekly cadence;
- execution path;
- limit-up / limit-down inference;
- cost;
- horizon set;
- matched comparator semantics;
- fallback comparator threshold;
- big-winner read-only boundary;
- final-decision authority of the primary canonical unit.

## 22. Stop-and-Revise Conditions

E04 must stop and return to requirement revision if:

- GTJA191 formulas cannot be mapped to local fields without ambiguous lookahead assumptions;
- the local provider lacks required OHLCV/money/index fields;
- less than `min_included_factor_count` factors are implementable;
- less than `min_direction_active_factor_count` factors have nonzero train-only directions;
- top-20% selection cannot produce enough selected or nonselected names on most validation dates;
- matched comparator or baseline construction requires changing inherited EP5 semantics;
- runtime feasibility requires dropping large parts of validation/robustness without an auditable blocked reason;
- a positive result requires validation-driven factor picking, weighting, threshold tuning, or filter addition.

Stopping under these conditions is a correct outcome. It prevents R04 from silently becoming a broad search experiment.

## 23. Expected Interpretation Boundary

R04 has four legitimate outcomes:

1. GTJA191 composite has both absolute and relative support.
2. GTJA191 composite has residual support only.
3. GTJA191 composite has beta/style exposure only.
4. GTJA191 composite has no local support.

Only outcome 1 can justify continuing a long-only short-horizon stock-selection path.

Outcome 2 can justify a new hedged / relative feasibility requirement, but not a long-only pass.

Outcome 3 should stop stock-selection search because it suggests exposure capture without residual edge.

Outcome 4 should pause the EP5 short-horizon stock-level alpha mainline unless a new requirement changes the economic question.

R04 is therefore a feasibility boundary test. It is not a license to search the GTJA191 library until something works.
