# EP5 Requirement 07: Short-Horizon Timing and Failure Attribution Audit V0

## 1. Requirement Metadata

requirement_id: `ep5_r07_short_horizon_timing_failure_attribution_audit_v0`

short_name: `r07_short_horizon_timing_failure_attribution_audit_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-22`

primary_output_namespace: `ep5/outputs/r07_short_horizon_timing_failure_attribution_audit_v0/`

upstream_requirements:

- `ep5/requirement_01_short_horizon_local_feasibility_probe_v1.md`
- `ep5/requirement_04_gtja191_short_horizon_residual_composite_feasibility_v0.md`
- `ep5/requirement_05_gtja191_train_only_factor_engineering_residual_feasibility_v0.md`
- `ep5/requirement_06_gtja191_factor_decay_information_content_audit_v0.md`

upstream_reports:

- `ep5/outputs/r01_short_horizon_local_feasibility_probe_v1/reports/r01_final_report.md`
- `ep5/outputs/r04_gtja191_short_horizon_residual_composite_feasibility_v0/reports/r04_final_report.md`
- `ep5/outputs/r05_gtja191_train_only_factor_engineering_residual_feasibility_v0/reports/r05_final_report.md`
- `ep5/outputs/r06_gtja191_factor_decay_information_content_audit_v0/reports/r06_final_report.md`

upstream_final_decisions:

```text
r01: r01_no_local_feasibility_support
r04: r04_no_gtja191_residual_composite_support
r05: r05_factor_cluster_structure_not_viable_blocked
r06: r06_decay_information_exists_but_not_tradeable
```

R07 inherits the EP5 local PIT mcap500 mainboard universe, train/validation/robustness split, provider, weekly close-observed signal, next-open execution, 110bps round-trip cost, matched-comparator discipline, and no-online-data boundary used by R01/R04/R05/R06.

R07 deliberately does not inherit:

- R01's exposure-unit construction (`r01_launch_breakout_money_surge_natural_exit_v0` and variants);
- R04's equal-weight composite;
- R05's neutralization-cluster composite and weekly top20% selection;
- R06's family-level information audit treated as a final answer.

R07 is downstream of R06 and is the failure-attribution audit that R06's `r06_decay_information_exists_but_not_tradeable` outcome left open.

## 2. Upstream Motivation

R01 / R04 / R05 / R06 produced four formally distinct failures. They are not redundant. Treating them as one failure would lose information.

| requirement | primary object | sample status | failure form | distinct evidence |
|:--|:--|:--|:--|:--|
| R01 | event-based short-horizon exposure unit | pass (592 H10 events) | `absolute_false__relative_false`; mean matched delta +0.74% but final relative gate failed | weak residual mean exists, absolute negative |
| R04 | equal-weight Alpha191 composite, weekly top20% | pass (4271 H10 events) | `absolute_false__relative_false`; mean matched delta +0.13% but median -0.40% and 2023 negative | weak residual mean, relative gate failed |
| R05 | train-only neutralized cluster composite, weekly top20% | pass (4279 H10 events) | `absolute_false__relative_false`; mean matched delta +0.10% / median -0.34% / 2023 reversal / persistent-name top5 union 97.98% | cluster structure block + persistent-name dominance |
| R06 | factor / family / horizon information audit (diagnostic) | pass (all horizons) | H1/H3/H5 family weak positive, H10/H20 decayed; no clean residual family | three H3 families with information+cost positive, monotonicity / persistent / style failed |

The four failures share one signature:

```text
A small weak-residual-mean pocket (mean matched delta in the
+0.05% to +0.74% range, while formal relative gates still failed)
exists in some H1/H3/H5 slice of EP5 short-horizon evidence,
but every attempt to convert that pocket into a stable, clean,
tradable exposure has been rejected by at least one discipline gate.
```

In R07, "relative pocket" is shorthand for this weak residual-mean
pocket. It does not mean that any upstream requirement passed its formal
`relative_positive` gate.

The four failures also share one missing piece of information:

```text
No EP5 requirement so far has decomposed the H1 -> H3 -> H5 -> H10 path
of that relative pocket, conditional on a train-frozen state,
to determine whether the pocket survives style / beta / persistent-name
explanations under that state.
```

R07 is the diagnostic that fills exactly that missing piece. R07 does not propose a new exposure. R07 does not propose an improved composite. R07 does not propose an improved family. R07 does not change the universe, the cost, the execution rule, the matched comparator, or the four-quadrant interpretation.

## 3. Research Positioning

R07 is a diagnostic requirement.

R07 is not a strategy requirement.

R07 is not an improved-exposure requirement.

R07 does not output:

- a production strategy;
- a long-only alpha pass;
- a hedged alpha pass;
- a backtest equity curve;
- a top-fraction or top-N selection rule;
- a recommendation to enlarge horizon set, family set, or factor set;
- a recommendation to relax any R01 / R05 / R06 discipline gate.

R07 outputs:

- a factual decomposition of the EP5 short-horizon relative pocket
  along the H1 / H3 / H5 / H10 path, conditional on a train-frozen
  market-state or stock-state axis;
- a five-gate replay (information / monotonicity / persistent-clean /
  style-clean / cost-survives) per (family, horizon, state) cell;
- a non-deterioration replay (validation and robustness vs train,
  with explicit tolerance);
- a final decision enum grouped into A / B / C plus blocked/no-pocket
  terminal variants, where only branch A grants permission to write a
  narrow downstream requirement.

R07 is the last diagnostic EP5 will run on the short-horizon line.

If R07 lands in branch C, EP5 closes the short-horizon line and the
finding becomes the primary evidence for the EP5 final report.

## 4. Core Question

R07 answers three nested questions, in order:

```text
Q1 (path decomposition):
  Of the small relative pocket observed by R01 and by R06 H3 families,
  which sub-segment of the H1 / H3 / H5 / H10 path carries it?
  Is the pocket front-loaded (H1/H3), centered (H5), or smeared (H10)?

Q2 (unconditional clean-attribution baseline):
  Within the segment that carries the pocket, do the unconditioned
  R06 gates say that the pocket is already clean, or do they say it is
  explained by persistent names, industry, liquidity, beta, volatility,
  money exposure, monotonicity failure, or cost failure?

Q3 (state stability):
  For each Q1-pocket cell, regardless of whether the unconditioned Q2
  baseline is clean, does there exist a train-frozen state cell under
  which the family-score-ranked pocket is clean, positive in train,
  and does not deteriorate beyond the R07 tolerance in validation and
  in robustness?
```

The questions chain asymmetrically. Q2 is evaluated only on
(family, horizon) cells that show a non-trivial pocket in Q1, but Q2 is
not a hard precondition for Q3. Q3 is evaluated on every Q1-pocket cell
because R07's core question is whether train-frozen state conditioning
can separate a weak unconditional pocket from persistent-name and style
explanations.

R07 reports the answer to Q1 on every cell in scope, the answer to Q2
on every Q1-pocket cell, and the answer to Q3 on every Q1-pocket cell.
R07 reports the joint as the final A / B / C decision.

## 5. Non-Goals and Explicit Prohibitions

R07 must not:

1. introduce any new factor outside R06's `r06_factor_family_map.csv`
   included factors;
2. introduce any new family outside R06's eight primary families;
3. introduce any horizon outside { H1, H3, H5, H10 };
4. re-search per-family horizon; R07 inherits R06's
   `family_primary_horizon_train_selected` for any family-primary use
   and additionally audits the full H1/H3/H5/H10 grid for the path
   diagnostic only;
5. re-cluster, re-neutralize, or re-construct family composites in any
   way that changes R06's family score definition;
6. construct a strategy unit, a top-N rule, a top-fraction rule, or any
   selection rule that produces a tradable basket;
7. add a regime overlay, a kill switch, an entry probe, or a
   confirmation rule;
8. introduce big-winner labels, right-tail readouts, or hit-rate gates
   as decision inputs;
9. introduce a new universe, a new cost, a new execution rule, a new
   matched comparator, or a new horizon label definition;
10. introduce more than two state axes; the total state axis count is
    capped at two;
11. introduce a state axis whose definition depends on family score,
    on factor score, on R06 readouts, or on any future-period data;
12. relax any R06 gate threshold (information, monotonicity,
    persistent-clean, style-clean, cost-survives, non-deterioration);
13. report a hedged pass or a long-only pass; R07 only reports a
    diagnostic A / B / C decision;
14. trigger any backtest, paper-trading, or production pipeline;
15. use validation or robustness evidence to choose state axis, state
    boundary, family scope, horizon scope, factor scope, or any gate
    threshold.

## 6. Data, Split, and Execution Contract

R07 reuses without modification:

- universe: `ep5_pit_mcap500_mainboard_v1`
- split:
  - train: 2017-07-04 to 2021-12-31
  - validation: 2022-01-01 to 2023-12-31
  - robustness: 2024-01-01 to 2025-12-31
- signal observation: weekly Friday close (or first prior trading day)
- execution: next-open executable, T+1, no online data
- transaction cost: 110bps round-trip applied per H-event
- matched comparator: as defined in R05 / R06, used for matched-delta
  return computation; only `matched_comparator_status = comparable`
  rows are decision-bearing
- horizon label panel: { H1, H3, H5, H10 }; H20 is excluded from R07
  because R06 §4 shows H20 validation and robustness already negative
  for every train-selected family, and R07's question is about the
  short-horizon path, not the long-horizon decay tail
- primary label: `matched_delta_return_net` (matched-delta after 110bps)
- secondary label for cost decomposition: `matched_delta_return_gross`
- absolute label for reference only, not decision-bearing:
  `net_return_absolute`

R07 does not change any of the above. R07 does not introduce a new
calendar, a new label, or a new comparator.

## 7. Scope Lock: Family and Horizon

Family scope (frozen from R06 §9):

```text
close_location
composite_price_volume
other_gtja191
range_volatility
rank_ts_rank_structure
volume_price_correlation
volume_surge_money_flow
vwap_deviation
```

Factor scope (frozen from R06):

```text
included_factor_count = 125
family_assignment frozen from r06_factor_family_map.csv
family_score frozen from R06 family aggregation definition
created_before_metric_computation = true
```

Horizon scope:

```text
horizon_grid_audited = { H1, H3, H5, H10 }
horizon_primary_per_family = r06.family_primary_horizon_train_selected
```

When R07 needs to refer to a single horizon per family for a
family-primary statistic, it uses `horizon_primary_per_family` exactly
as R06 chose it. When R07 needs to audit the H1 -> H3 -> H5 -> H10
path, it uses every horizon in `horizon_grid_audited` for every
family.

R07 does not add families. R07 does not add horizons. R07 does not
re-select per-family horizon.

## 8. State Axis Definition and Train-only Freeze

R07 admits at most two state axes. Each state axis must satisfy all
of the following:

```text
S1: axis_definition_is_public_and_independent_of_family_score = true
S2: axis_definition_is_independent_of_factor_score             = true
S3: axis_definition_uses_only_information_available_at_signal_date = true
S4: axis_binning_method_is_fixed_before_metric_computation     = true
S5: axis_bin_edges_are_chosen_using_train_split_only           = true
S6: axis_bin_edges_are_frozen_before_validation_is_read        = true
S7: axis_bin_count_in_{2,3}                                    = true
```

The two admitted axes for R07 V0 are:

```text
axis_market_regime:
  definition  = CSI300 close-to-close 20-day return, observed at signal date
  binning     = three bins by tercile of train-period values
  bin_labels  = { market_down, market_flat, market_up }
  bin_edges   = frozen from train split values, recorded in artifact

axis_stock_short_momentum:
  definition  = stock close-to-close 10-day return, observed at signal date
  binning     = three bins by train-period stock-date pooled terciles
                across all eligible instruments and all train signal dates
  bin_labels  = { stock_down, stock_flat, stock_up }
  bin_edges   = one global pair of train-pooled tercile cut points,
                recorded in artifact and applied unchanged to every stock
```

R07 does not admit a third axis. R07 does not admit a turnover-based,
volatility-based, money-based, or industry-based axis in V0, because
those overlap with the style exposure that R06 §17 already audits and
would re-introduce the explanation R07 is trying to separate from.

Cross-axis state cell:

```text
state_cell = (market_regime_bin, stock_short_momentum_bin)
state_cell_count = 3 * 3 = 9
```

State cells are common to all (family, horizon) cells.

State axis selection is closed before R07 reads any validation or
robustness data. R07 does not search for a better axis.

## 9. Audit Units

R07 evaluates three classes of audit units. They are independent
artifacts.

```text
audit_unit_path_decomposition:
  granularity = (family, horizon in {H1, H3, H5, H10})
  question    = Q1
  metric      = family_score_rankIC_net
                + top_decile_minus_bottom_decile_matched_delta_net
                + spread_positive_date_share
  comparator  = R06 baseline (no state conditioning)

audit_unit_clean_attribution:
  granularity = (family, horizon)
  question    = Q2
  gates       = R06 five gates (information, monotonicity,
                persistent_clean, style_clean, cost_survives)
  evaluated_on = Q1-pocket cells only
  scope_floor  = at least one of horizon in {H1, H3, H5}; H10 is
                 accepted for evaluation but is not preferred in
                 final A-branch consideration because R06 already
                 showed H10 validation is at or below zero for every
                 train-selected family

audit_unit_state_stability:
  granularity = (family, horizon, state_cell)
  question    = Q3
  gates       = R07 state-conditional five gates
                + non-deterioration gate
                + state-conditional sample floor
  evaluated_on = Q1-pocket cells only
```

All three audit units write per-cell rows. The final A/B/C decision is
a first-match rule replay over these per-cell rows.

## 10. Per-State Metric Definitions

For every (family, horizon, state_cell, split) tuple:

In R07, "week" means the weekly signal observation week (Friday close
or first prior trading day), not a selection week. R07 has no selection
rule and does not create a tradable selected-week basket.

```text
event_count_state_cell                  = count of decision-bearing events
                                          within state_cell, within split
date_count_state_cell                   = count of signal dates with at
                                          least one decision-bearing event
state_date_cross_section_count          = count of decision-bearing stocks
                                          per (state_cell, signal_date)
min_state_date_cross_section_count      = minimum of
                                          state_date_cross_section_count
                                          across dates in the split

family_score_rankIC_net_state           = Spearman rank correlation between
                                          R06 family_score and
                                          matched_delta_return_net within
                                          each (state_cell, signal_date),
                                          then mean over dates
family_score_rankIC_gross_state         = same using
                                          matched_delta_return_gross

state_score_bucket_rule                 = primary decision bucket is
                                          tercile within each
                                          (state_cell, signal_date),
                                          sorted by R06 family_score.
                                          Quintile/decile readouts are
                                          audit-only and are emitted only
                                          when cross-section floors permit.
top_minus_bottom_spread_net_state       = top-tercile minus bottom-tercile
                                          matched_delta_return_net
                                          within state_cell, averaged over
                                          dates
top_minus_bottom_spread_gross_state     = same using
                                          matched_delta_return_gross
positive_spread_date_share_state        = share of dates whose
                                          top-minus-bottom net spread > 0
monotonicity_state                      = Spearman rank correlation of
                                          tercile_index vs tercile_mean
                                          matched_delta_return_net,
                                          averaged over dates

top1_signal_week_share_state            = share of weeks (within split)
                                          whose top-tercile bucket includes
                                          the most-selected stock
top5_signal_week_union_share_state      = union share over the top-five
                                          most-selected stocks in the
                                          top-tercile bucket
new_name_share_state                    = share of (week, stock) entries
                                          whose stock did not appear in
                                          the cell's top-tercile bucket in
                                          the previous signal week within
                                          the same state cell
rank_turnover_state                     = average per-week top-tercile
                                          membership turnover within the
                                          cell

style_explained_score_r2_state          = median per-date R^2 from
                                          stock-level cross-sectional OLS
                                          of R06 family_score on style-bin
                                          dummies within state_cell
style_explained_spread_share_state      = mean per-date share of raw
                                          top-bottom spread explained by
                                          style-bin projection, using
                                          stock-level observations
neutralized_spread_retention_state      = (post-style-neutralization
                                          top-bottom spread) /
                                          (pre-style-neutralization
                                          top-bottom spread)
raw_and_neutralized_sign_agree_state    = true only when raw and
                                          style-neutralized spread signs
                                          agree on validation and
                                          robustness
style_evaluable_date_count_state        = count of dates where style OLS
                                          and spread-retention metrics are
                                          evaluable

gross_minus_net_drag_state              = top_minus_bottom_spread_gross_state
                                          minus
                                          top_minus_bottom_spread_net_state
cost_survival_ratio_state               = top_minus_bottom_spread_net_state /
                                          top_minus_bottom_spread_gross_state,
                                          defined only when gross spread > 0

top_bucket_mean_net_return_absolute     = mean absolute net return of the
                                          top-tercile bucket; audit-only
top_bucket_median_net_return_absolute   = median absolute net return of the
                                          top-tercile bucket; audit-only
```

These definitions are the R06 metric definitions restricted to the
state_cell sub-sample, except that R07 uses terciles rather than deciles
for state-conditional decision gates because 9-way state slicing makes
per-date deciles too thin. Decile readouts remain audit-only when
`state_date_cross_section_count >= 100`; quintile readouts are audit-only
when `state_date_cross_section_count >= 50`. Decision gates use terciles
only.

## 11. Five-Gate Recap (State-Conditional)

R07 inherits R06's economic and cleanliness thresholds where the metric
is unchanged. State-cell sample and bucket construction are explicitly
state-specific because the 9-way slicing changes per-date cross-section
size. These state-specific sample rules are not allowed to be tuned after
validation is read.

```text
gate_information_train_positive:
  train_top_minus_bottom_spread_net_state >= +0.0003   (3 bps)
  train_family_score_rankIC_net_state     >= 0

gate_information_state_positive:
  validation_top_minus_bottom_spread_net_state >= +0.0005   (5 bps)
  validation_family_score_rankIC_net_state     >= 0
  validation_positive_spread_date_share_state  >= 0.50

gate_monotonicity_state_positive:
  validation_monotonicity_state >= 0.60

gate_persistent_clean_state:
  validation_top1_signal_week_share_state        <= 0.35
  validation_top5_signal_week_union_share_state  <= 0.75
  validation_new_name_share_state                >= 0.30
  validation_rank_turnover_state                 >= 0.35

gate_style_clean_state:
  validation_style_evaluable_date_count_state       >= 20
  validation_style_explained_score_r2_state         <= 0.35
  validation_style_explained_spread_share_state     <= 0.50
  validation_neutralized_spread_retention_state     >= 0.50
  validation_raw_and_neutralized_sign_agree_state   = true

gate_cost_survives_state:
  validation_top_minus_bottom_spread_gross_state > 0
  validation_cost_survival_ratio_state           >= 0.50
```

`gate_information_train_positive` must pass before a cell can be
Q3-stable. This preserves R07's train-only discipline: validation is not
allowed to create a state cell from a near-zero train signal.

Robustness equivalents use the same thresholds on the robustness split
except that no separate robustness-vs-train-positive gate is needed
beyond the robustness information gate and §12 non-deterioration rule.

## 12. Non-deterioration Gate

For every (family, horizon, state_cell) cell that passes the five
state-conditional gates on the validation split, R07 additionally
requires:

```text
non_deterioration_validation_vs_train:
  validation_top_minus_bottom_spread_net_state
    >= train_top_minus_bottom_spread_net_state - 0.0010    (-10 bps)
  validation_family_score_rankIC_net_state
    >= train_family_score_rankIC_net_state - 0.0100
  validation_monotonicity_state
    >= train_monotonicity_state - 0.10
  validation_top5_signal_week_union_share_state
    <= train_top5_signal_week_union_share_state + 0.10

non_deterioration_robustness_vs_train:
  robustness_top_minus_bottom_spread_net_state
    >= train_top_minus_bottom_spread_net_state - 0.0015    (-15 bps)
  robustness_family_score_rankIC_net_state
    >= train_family_score_rankIC_net_state - 0.0150
  robustness_monotonicity_state
    >= train_monotonicity_state - 0.15
  robustness_top5_signal_week_union_share_state
    <= train_top5_signal_week_union_share_state + 0.15
```

A cell that fails non-deterioration on either split is not a clean
state-stable cell, even if its in-split metrics pass the five gates.

## 13. State-Conditional Sample Floor

```text
state_cell_sample_gate:
  train_event_count_state_cell      >= 200
  validation_event_count_state_cell >= 80
  robustness_event_count_state_cell >= 60
  validation_date_count_state_cell  >= 20
  robustness_date_count_state_cell  >= 20
  validation_min_state_date_cross_section_count >= 30
  robustness_min_state_date_cross_section_count >= 30
```

A cell that fails the sample floor is recorded as
`state_cell_sample_blocked` and is excluded from the Q3 decision
computation. It is not treated as a pass and not treated as a fail.

The sample floor is necessary because cross-axis state cells split
the per-split sample by roughly 9x.

## 14. Q1 Path Decomposition Audit

For every (family, horizon) cell in scope:

```text
path_metric:
  validation_family_score_rankIC_net
  robustness_family_score_rankIC_net
  validation_top_decile_minus_bottom_decile_matched_delta_net
  robustness_top_decile_minus_bottom_decile_matched_delta_net
  validation_spread_positive_date_share
  robustness_spread_positive_date_share

pocket_flag:
  validation_top_decile_minus_bottom_decile_matched_delta_net
    >= +0.0005   (5 bps)
  validation_family_score_rankIC_net
    >= 0
  validation_spread_positive_date_share
    >= 0.50
```

Cells with `pocket_flag = true` are Q1-pocket cells. The Q1 report
shall describe, per family, which horizon in {H1, H3, H5, H10} carries
the pocket, and whether the pocket is monotonic in horizon
(front-loaded, centered, smeared, or absent).

R07 expects, based on R06 §4 and §13, that Q1-pocket cells will be
concentrated in H1 / H3 for the three R06 information-positive
families and largely absent for the H20-train-selected families. R07
records that expectation as a prior, not as a gate.

## 15. Q2 Clean Attribution Audit

For every Q1-pocket cell:

- Evaluate all five R06 gates without state conditioning, using R06
  metric definitions on validation and robustness.
- Record per-cell pass / fail for each gate.
- A Q1-pocket cell that passes all five R06 gates is a
  `Q2_unconditional_clean_cell`.
- A Q1-pocket cell that fails one or more gates records
  `Q2_failure_explanation_set`, with one or more of:
  `information_fail`, `monotonicity_fail`, `persistent_clean_fail`,
  `style_clean_fail`, `cost_survival_fail`.

`Q2_unconditional_clean_cell = true` only when validation gates pass and
robustness equivalents do not fail. A validation-only clean readout with
robustness failure is recorded as `Q2_validation_only_clean_lead`, not
as Q2-unconditional-clean.

R07 does not state-condition the Q2 evaluation, because Q2 is asking
whether the pocket is already clean at the unconditioned level. Q2 is
a baseline attribution readout, not a hard precondition for Q3. State
conditioning is reserved for Q3, where the question is whether a
train-frozen state slice can stabilize a pocket that may fail
unconditionally.

R07 expects, based on R06, that the Q2-unconditional-clean cell count
will be small or zero. R07 still computes Q2 because absence of
Q2-unconditional-clean cells,
combined with absence of Q3-stable cells, is a decision input for the
style / persistent-name explanation branch.

Q2 is an explanatory readout, not a strategy gate. It is used for the
final report's attribution questions, especially §21 questions 6, 12,
and 13. Q3 is still evaluated on every Q1-pocket cell regardless of the
Q2 readout.

## 16. Q3 State Stability Audit

For every Q1-pocket cell:

- Compute per-state-cell metrics defined in §10.
- Apply the state-conditional five gates of §11.
- Apply the non-deterioration gate of §12.
- Apply the state-conditional sample floor of §13.
- A (family, horizon, state_cell) that passes all of the above is a
  Q3-stable cell.

R07 does not aggregate Q3-stable cells into a composite. R07 does not
recommend selecting on Q3-stable cells. R07 only counts and reports
them.

## 17. Hedged Feasibility Preflight, Read-Only

R07 conducts a read-only hedged feasibility preflight, scoped tightly:

```text
hedged_preflight_trigger:
  exists (family, horizon, state_cell) such that
    Q3_stable_flag                                = true and
    validation_top_minus_bottom_spread_net_state  >  0 and
    robustness_top_minus_bottom_spread_net_state  >  0 and
    long_only_absolute_candidate_gate(state_cell) = false

hedged_preflight_outputs (read-only, no backtest):
  - local_hedge_data_status in
      { local_data_available, not_evaluable_local_data_absent }
  - margin/hedge instrument availability on triggering universe
  - estimated hedge slippage and financing cost band
  - matched-comparator basket realizability under hedge constraints
  - sample of hedge-paired (long, short) date counts

hedged_preflight_conclusion:
  one of { feasible_to_write_hedged_requirement,
           not_feasible_to_write_hedged_requirement,
           not_evaluable_local_data_absent }
```

The hedged preflight does not change R07's A/B/C decision. It only
attaches a feasibility tag to a possible downstream requirement.

If the hedged preflight trigger is not satisfied, R07 records
`hedged_preflight_skipped = true` and does not run the preflight.

The hedged preflight may only use local data already available in the
repository or an explicitly configured local data path. It must not fetch
online margin, financing, securities-lending, futures, or options data.
If local hedge feasibility data is absent, the conclusion is
`not_evaluable_local_data_absent`, not feasible.

`long_only_absolute_candidate_gate(state_cell)` is defined in §18.

R07 does not run a low-overlap event source preflight in V0. That
question is out of scope; if EP5 ever needs it, it will be a separate
requirement.

## 18. Final Decisions

R07 emits exactly one final decision, drawn from the following enum:

```text
r07_state_stable_clean_pocket_supported
r07_relative_pocket_clean_but_not_state_stable
r07_relative_pocket_explained_by_style_or_persistent_name
r07_no_relative_pocket_in_scope
r07_insufficient_state_cell_sample_blocked
r07_audit_scope_violation_blocked
```

Decision definitions:

```text
r07_state_stable_clean_pocket_supported:
  - at least one (family, horizon) cell is Q1-pocket;
  - at least one (family, horizon, state_cell) is Q3-stable;
  - Q3-stable cell exists in horizon in {H1, H3, H5};
  - this is the only decision that grants permission to write a
    downstream narrow requirement.

r07_relative_pocket_clean_but_not_state_stable:
  - at least one (family, horizon) cell is Q2-unconditional-clean
    or at least one H10-only Q3-stable cell exists;
  - no Q3-stable cell exists in horizon in {H1, H3, H5};
  - hedged_preflight may attach a feasibility tag.
  - for H10-only Q3-stable cases, "not_state_stable" means not
    short-horizon state-stable for R07 authorization purposes. H10-only
    state stability is treated as decay-tail evidence, not a usable
    short-horizon pocket, because R06 §4 / §13 already showed H10 is
    near zero or unstable.

r07_relative_pocket_explained_by_style_or_persistent_name:
  - at least one (family, horizon) cell is Q1-pocket;
  - no (family, horizon) cell is Q2-unconditional-clean;
  - the unconditional pocket is explained by persistent-name or style
    or fails monotonicity or fails cost survival;
  - no downstream requirement is authorized.

r07_no_relative_pocket_in_scope:
  - no (family, horizon) cell is Q1-pocket;
  - the EP5 short-horizon relative pocket observed by R01 and R06 does
    not appear in any cell once R07's audit conditions are applied;
  - no downstream requirement is authorized.

r07_insufficient_state_cell_sample_blocked:
  - state_cell_sample_gate fails for the majority of state cells under
    Q1-pocket cells; the audit cannot conclude Q3 honestly;
  - no downstream requirement is authorized;
  - V0 must declare the sample shortfall.

r07_audit_scope_violation_blocked:
  - any §5 prohibition is detected during execution or replay;
  - no downstream requirement is authorized.
```

Downstream authorization scope (only when
`r07_state_stable_clean_pocket_supported` is selected):

```text
A downstream requirement may be written if and only if it satisfies:
  - scope_family_count <= 1
  - scope_horizon_count <= 1
  - scope_state_axis_count <= 2
  - scope_state_cell_count <= 9
  - decision_label IN {
      relative_research_candidate,
      hedged_research_candidate,
      long_only_research_candidate
    }
  - hedged_preflight_feasibility_tag_required = true when label is
    hedged_research_candidate
  - long_only_absolute_candidate_gate_required = true when label is
    long_only_research_candidate
  - explicit_inheritance_of_R07_gates = true
```

`long_only_absolute_candidate_gate(state_cell)` is audit-only inside R07 and cannot
create an R07 pass by itself. It is true only when the triggering
Q3-stable cell also satisfies:

```text
validation_top_bucket_mean_net_return_absolute   > 0
validation_top_bucket_median_net_return_absolute >= -0.0010
robustness_top_bucket_mean_net_return_absolute   >= -0.0005
```

If `long_only_absolute_candidate_gate = false`, downstream authorization
may only be `relative_research_candidate` or, if the hedged preflight is
locally feasible, `hedged_research_candidate`.

R07 itself never produces a strategy. R07 itself never produces an
allocation. R07 itself never produces a backtest.

## 19. First-Match Rule Replay

The R07 final decision is computed by first-match rule replay over a
fixed rule list. The first rule whose condition holds wins; later
rules are not evaluated.

```text
rule_01: scope_violation_detected
  -> r07_audit_scope_violation_blocked

rule_02: Q1_pocket_cell_count == 0
  -> r07_no_relative_pocket_in_scope

rule_03: Q1_pocket_cell_count > 0
         and state_cell_sample_majority_blocked
  -> r07_insufficient_state_cell_sample_blocked

rule_04: Q3_stable_cell_count > 0 and exists Q3-stable cell with
         horizon in {H1, H3, H5}
  -> r07_state_stable_clean_pocket_supported

rule_05: Q3_stable_cell_count > 0 and no Q3-stable cell with horizon
         in {H1, H3, H5}, i.e. only H10
  -> r07_relative_pocket_clean_but_not_state_stable
     (H10-only Q3-stable cells are not strong enough to authorize a
      downstream requirement, because R06 already showed H10 is
      decay-tail-near-zero; see R06 §4 / §13.)

rule_06: Q2_unconditional_clean_cell_count > 0
         and Q3_stable_cell_count == 0
  -> r07_relative_pocket_clean_but_not_state_stable

rule_07: Q1_pocket_cell_count > 0
         and Q2_unconditional_clean_cell_count == 0
         and Q3_stable_cell_count == 0
  -> r07_relative_pocket_explained_by_style_or_persistent_name
```

Rule order is fixed. R07 does not change rule order based on any
intermediate observation.

`state_cell_sample_majority_blocked` is evaluated only when
`Q1_pocket_cell_count > 0`. Its denominator is:

```text
Q1_pocket_cell_count * state_cell_count
```

with `state_cell_count = 9`. It is true when more than 50% of those
state cells fail `state_cell_sample_gate`.

## 20. Required Artifacts

R07 writes the following artifacts under
`ep5/outputs/r07_short_horizon_timing_failure_attribution_audit_v0/`:

```text
artifacts/
  r07_state_axis_definition.csv
    columns: axis_name, definition_text, bin_count, bin_edges_train,
             frozen_at_timestamp, frozen_before_validation_read

  r07_state_axis_validator.csv
    columns: axis_name, S1..S7_pass_flags

  r07_scope_lock.csv
    columns: family, horizon_primary, horizon_grid_audited,
             included_factor_count_in_family,
             family_score_definition_hash_from_R06

  r07_path_decomposition.csv
    columns: family, horizon, split, event_count,
             family_score_rankIC_net,
             top_decile_minus_bottom_decile_matched_delta_net,
             spread_positive_date_share, pocket_flag

  r07_clean_attribution.csv
    columns: family, horizon,
             gate_information_pass, gate_monotonicity_pass,
             gate_persistent_clean_pass, gate_style_clean_pass,
             gate_cost_survives_pass, Q2_unconditional_clean_flag,
             Q2_failure_explanation_set

  r07_state_stability.csv
    columns: family, horizon, state_cell,
             train_event_count, validation_event_count, robustness_event_count,
             validation_min_state_date_cross_section_count,
             robustness_min_state_date_cross_section_count,
             train_family_score_rankIC_net,
             train_top_minus_bottom_spread_net,
             validation_family_score_rankIC_net,
             validation_top_minus_bottom_spread_net,
             validation_positive_spread_date_share,
             validation_style_explained_score_r2,
             validation_style_explained_spread_share,
             train_information_positive_pass,
             validation_state_gates_pass_count, robustness_state_gates_pass_count,
             non_deterioration_validation_pass, non_deterioration_robustness_pass,
             state_cell_sample_pass, Q3_stable_flag

  r07_hedged_preflight.csv
    columns: family, horizon, trigger_satisfied,
             local_hedge_data_status,
             hedge_instrument_available, hedge_slippage_band,
             hedge_financing_band, hedge_paired_date_count,
             preflight_conclusion

  r07_final_decision_inputs.csv
    columns: Q1_pocket_cell_count, Q2_unconditional_clean_cell_count,
             Q3_stable_cell_count, Q3_stable_short_horizon_cell_count,
             Q3_sample_denominator_cell_count,
             Q3_sample_blocked_cell_count,
             state_cell_sample_majority_blocked_flag,
             scope_violation_detected_flag

  r07_final_decision_replay_audit.csv
    columns: rule_id, rule_condition_text, rule_fires_flag,
             selected_rule_flag

  r07_final_decision.csv
    columns: final_decision

reports/
  r07_final_report.md
```

## 21. Required Report Questions

`r07_final_report.md` must answer the following questions in order:

1. Did R07 honor every §5 prohibition?
2. Which family scope and horizon scope did R07 use, and are they
   identical to R06 §9 and §14?
3. What are the two state axes, their definitions, their bin edges,
   and the timestamp at which the bin edges were frozen?
4. How many state cells reached the §13 sample floor in each split?
5. For each (family, horizon) cell, what is the Q1 path-decomposition
   readout, and which cells are Q1-pocket?
6. For each Q1-pocket cell, which of the five unconditioned R06 gates
   pass and which fail, which cells are Q2-unconditional-clean, and what
   is each cell's Q2 failure explanation set?
7. For each Q1-pocket cell, which (family, horizon, state_cell) cells
   are Q3-stable on validation and on robustness, which fail the
   state sample / cross-section floor, and which fail the
   non-deterioration gate?
8. Does any Q3-stable cell exist in horizon in {H1, H3, H5}?
9. Does the hedged feasibility preflight fire? If so, what is its
   conclusion? If not, why was it skipped?
10. What is the first-match rule that fires, and what is the final
    decision?
11. Compared to R01's relative pocket (mean matched delta +0.74% on
    H10, 592 events, absolute_false__relative_false), does R07 locate
    where on the H1/H3/H5/H10 path that pocket lives, and does it
    survive Q2 and Q3?
12. Compared to R05's H10 validation pocket (mean matched delta
    +0.10%, median -0.34%, 2023 reversal, persistent-name top5 union
    97.98%), does R07 confirm or refute persistent-name as the
    primary explanation?
13. Compared to R06's three H3 information-positive families, does
    R07 confirm or refute style-exposure as the primary explanation?
14. Does R07 authorize a downstream requirement? If yes, what is the
    allowed scope (family, horizon, state-axis count, decision label),
    and if the label is long-only did the absolute candidate gate pass?
15. If R07 does not authorize a downstream requirement, is the EP5
    short-horizon line ready to close? On what evidence?
16. Are there any state cells where the audit could not conclude due
    to sample shortfall, and what fraction of total Q3 cells they
    represent?
17. Are there any anomalies in the path-decomposition readout that
    contradict R06 §4 (the family-level RankIC decay curve)? If yes,
    how are they reconciled?

## 22. Validator

The R07 validator must pass all of the following checks:

```text
V01: artifact set complete (r07_state_axis_definition.csv,
     r07_state_axis_validator.csv, r07_scope_lock.csv,
     r07_path_decomposition.csv, r07_clean_attribution.csv,
     r07_state_stability.csv, r07_hedged_preflight.csv,
     r07_final_decision_inputs.csv, r07_final_decision_replay_audit.csv,
     r07_final_decision.csv, r07_final_report.md)

V02: state_axis_count <= 2
V03: every state axis passes S1..S7
V04: state_axis_bin_edges_frozen_before_validation_read = true
V05: family scope identical to R06 family map (8 families)
V06: horizon scope subset of {H1, H3, H5, H10}
V07: family_score_definition_hash matches R06 hash
V08: horizon_primary_per_family identical to R06 train-selected horizon
V09: no factor outside R06 included_factor_count = 125
V10: no R06 economic or cleanliness threshold was relaxed
     (information, monotonicity, persistent_clean, style_clean,
     cost_survives, non_deterioration); state-specific bucket and sample
     rules match §10-§13 exactly
V11: state_cell_sample_floor and min state-date cross-section floor
     evaluated per cell and recorded
V12: train information positive gate is evaluated per state cell and
     Q3_stable_flag cannot be true unless
     train_top_minus_bottom_spread_net_state >= +0.0003 and
     train_family_score_rankIC_net_state >= 0
V13: Q2 evaluation restricted to Q1-pocket cells
V14: Q3 evaluation restricted to Q1-pocket cells, not to
     Q2-unconditional-clean cells
V15: rule replay order matches §19 list exactly
V16: exactly one rule_fires_flag = true (first-match)
V17: state_cell_sample_majority_blocked denominator equals
     Q1_pocket_cell_count * 9 and is only evaluated when
     Q1_pocket_cell_count > 0
V18: hedged_preflight_trigger evaluated exactly per §17 definition
     and no online hedge / margin / financing data is fetched
V19: hedged_preflight outputs are read-only (no equity curve,
     no allocation, no top-N rule)
V20: no big-winner label, no right-tail readout, no hit-rate gate
     appears in any decision-bearing artifact
V21: no validation or robustness evidence was used to choose state
     axis, state binning, family scope, horizon scope, or any gate
     threshold
V22: final_decision is one of the §18 enum
V23: when final_decision is r07_state_stable_clean_pocket_supported,
     the downstream authorization scope is recorded with
     scope_family_count <= 1 and scope_horizon_count <= 1
V24: when downstream decision_label is long_only_research_candidate,
     long_only_absolute_candidate_gate = true
V25: when downstream decision_label is hedged_research_candidate,
     hedged_preflight_conclusion = feasible_to_write_hedged_requirement
V26: when final_decision is anything other than
     r07_state_stable_clean_pocket_supported, no downstream
     authorization scope is recorded
V27: r07_final_report.md answers all §21 questions
V28: pocket_flag and state information gates use family-score-ranked
     RankIC / top-bottom spread metrics, not unranked mean
     matched-delta averages
```

## 23. Interpretation Boundary

R07's grouped A / B / C decision is a research conclusion, not a market
prediction. The conclusion holds under the EP5 PIT mcap500 mainboard
universe, the weekly close-observed signal cadence, the next-open
execution rule, and the 110bps round-trip cost. Changing any of these
contract parameters invalidates the conclusion.

R07 says nothing about:

- single-stock alpha;
- daily-rebalanced strategies;
- intraday execution;
- alternative data sources;
- regime-overlay strategies;
- options or futures structures;
- any universe outside mcap500 mainboard.

R07 does not claim that Alpha191 contains no usable information. R07
only claims that within this contract, the answer to Q1 / Q2 / Q3
falls in one of the six enumerated branches.

## 24. Stop Conditions

R07 stops EP5's short-horizon line under any of:

```text
final_decision in {
  r07_relative_pocket_explained_by_style_or_persistent_name,
  r07_no_relative_pocket_in_scope,
  r07_audit_scope_violation_blocked,
  r07_insufficient_state_cell_sample_blocked
}
```

In any of these stop cases, EP5 must write its `FINAL_REPORT.md`
using R01 / R04 / R05 / R06 / R07 as the primary evidence chain. EP5
must not start a new short-horizon requirement under any new name in
the same contract.

R07 allows EP5's short-horizon line to continue, in a narrowed scope,
only under:

```text
final_decision == r07_state_stable_clean_pocket_supported
```

and only via a downstream requirement that satisfies §18
authorization scope.

R07 allows EP5 to write a hedged feasibility requirement only under:

```text
final_decision == r07_relative_pocket_clean_but_not_state_stable
and
hedged_preflight_conclusion == feasible_to_write_hedged_requirement
```

In every other case, R07 closes the EP5 short-horizon line.

## 25. One-line Summary

```text
R07 does not try to find an exposure. R07 decomposes the EP5 short-horizon
relative pocket along H1/H3/H5/H10 conditional on a train-frozen state,
and decides whether the pocket survives persistent-name, style, and
non-deterioration discipline well enough to authorize a single narrow
downstream requirement, or whether the EP5 short-horizon line closes.
```
