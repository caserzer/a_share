# Requirement: Big Winner Reverse Lifecycle Profile V0

## 1. Objective

Build a reverse lifecycle profile for A-share big-winner episodes under
`topics/02_AFML_BIG_WINNER`.

This experiment must not start from candidate trading events. It must first
construct a reproducible retrospective reference set of big-winner episodes,
align winners and matched controls on shared axes, and identify which lifecycle
features differ between winners and controls.

The research question is:

```text
Which market, stock-path, volume-price, VWAP, volatility, and relative-strength
features dominate the lifecycle of A-share big winners, after matched controls?
```

The final output is a profile/diagnostic report. It is not an event contract,
strategy requirement, model, or backtest.

## 2. Non-Goals

This experiment must not:

- Train predictive models.
- Run a backtest.
- Produce entry, exit, sizing, or portfolio rules.
- Simulate stop-loss or time-stop policies.
- Promote retrospective lows or highs into tradable signals.
- Use current-as-of industry labels for primary historical conclusions.
- Authorize `03_observable_anchor_event_contract_v0`.
- Claim an event edge from winner-only descriptive statistics.

## 3. Input Data Contract

Primary inputs come from
`experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0` and
`topics/02_AFML_BIG_WINNER/data/`.

Required inputs:

```text
PIT executable stock universe:
  pit_largecap_main_chinext keyed by usable_trade_date

Stock daily bars:
  qfq OHLCV, money, turnover
  raw OHLC only for previously built data-layer eligibility audits

Benchmark index daily bars:
  csi300
  chinext_index
  all_a

Calendar:
  A-share trading sessions
```

The implementation must record input paths, data-layer manifest hashes, and the
source git revision in `outputs/manifests/run_manifest.json`.

### 3.1 Industry Data Status

The current data layer does not guarantee PIT industry membership. Therefore
industry diagnostics are conditional.

The run must set:

```text
industry_data_status in {
  pit_available,
  best_effort_non_pit,
  unavailable
}
```

Rules:

- If `pit_available`, industry diagnostics may be primary diagnostics.
- If `best_effort_non_pit`, industry diagnostics are diagnostic-only and must
  carry an explicit as-of caveat.
- If `unavailable`, industry-relative features and industry-regime conclusions
  must be skipped.
- If industry data is not PIT, industry-relative rows must not enter
  `shared_axis_factor_dominance.csv`.

Primary PIT industry membership, if used, must include:

```text
instrument
industry_code
industry_name
source
as_of_date
available_time
usable_trade_date
```

## 4. Date Range and Splits

Use the available data-layer trading range, currently expected to start at
`2017-01-03`.

Split assignment uses `episode_low_date` and must be frozen before computing
dominance results:

```text
train:
  2017-01-03 <= episode_low_date <= 2021-12-31

validation:
  2022-01-01 <= episode_low_date <= 2023-12-31

robustness:
  2024-01-01 <= episode_low_date <= latest_label_complete_low_date
```

Where:

```text
latest_label_complete_low_date =
  latest trading session D such that D has at least 120 forward trading sessions
```

The 2022-2023 validation split is a negative-beta stress validation window. It
must not be treated as an ordinary market-neutral validation window.

The report must separate:

```text
unconditional_validation_readout
regime_conditioned_validation_readout
validation_opportunity_audit
```

If validation or robustness lacks sample support, the experiment must return a
sample-blocked decision. It must not move split boundaries, shorten the 120-day
horizon, lower the +50% threshold, or include label-incomplete lows to satisfy
sample gates.

Because episode extraction requires 250 prior sessions, the effective first
eligible low date may be later than `2017-01-03`. The report must disclose the
effective first eligible low date and the number of otherwise in-range rows
blocked by insufficient lookback.

## 5. Reference Episode Extraction

### 5.1 Core Definition

For each instrument inside the executable PIT universe, construct candidate
retrospective local lows using qfq prices.

An eligible `candidate_low_date = D` must satisfy:

```text
qfq_low[D] is the minimum qfq_low in [D - 20 sessions, D + 20 sessions]
at least 250 prior sessions exist for full-lookback profile features
at least 120 forward sessions exist for primary MFE evaluation
```

For each candidate:

```text
forward_window = next 120 trading sessions after D, inclusive of D+1
episode_high_date = earliest date of maximum qfq_high in forward_window
mfe_120 = qfq_high[episode_high_date] / qfq_low[D] - 1
keep candidate if mfe_120 >= 0.50
high_at_horizon_boundary = episode_high_date is the last date in forward_window
```

The primary big-winner threshold is:

```text
mfe_120 >= 50%
```

### 5.2 Cluster and Deduplication Policy

Candidate episodes must be clustered per instrument using non-chain direct
interval overlap.

For each retained candidate:

```text
interval_i = [candidate_low_date_i, episode_high_date_i]
```

Cluster rule:

```text
sort candidates by candidate_low_date
start a cluster with seed interval_i
add candidate_j only if interval_j directly overlaps seed interval_i
do not expand the seed interval when adding candidate_j
if candidate_j does not overlap the seed interval, start a new cluster
```

This intentionally allows limited adjacent-boundary overlap. The run must
produce a cluster-boundary overlap audit so episode counts are interpretable.

### 5.3 Retrospective Anchors Per Cluster

For each cluster, keep all three retrospective anchors:

```text
earliest_qualifying_low:
  earliest low date in the cluster that already qualifies as +50% / 120d

max_mfe_low:
  low date with highest mfe_120 in the cluster

structural_low:
  lowest qfq low inside the union of cluster intervals
```

Primary low-aligned profiles use `earliest_qualifying_low` and must label it as
the earliest right-tail boundary, not as the true low. `max_mfe_low` and
`structural_low` are required sensitivity views.

Canonical episode-level dates are fixed as:

```text
episode_low_date = earliest_qualifying_low_date
episode_high_date = earliest_qualifying_high_date
```

`episode_low_date` controls split assignment, primary low-aligned panels, and
retrospective-low opportunity matching. Sensitivity anchors must not overwrite
the canonical split or matching date.

Required reference fields:

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
low_detection_window
forward_horizon_days
dedup_cluster_id
cluster_policy
primary_low_selection_policy
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

If `high_at_horizon_boundary = true`, post-high exhaustion diagnostics must
report the episode separately or exclude it from post-high exhaustion readouts.

Missing feature values must distinguish:

```text
missing_insufficient_lookback
missing_event_absent
missing_source_field
missing_unit_incompatible
```

These states must not be collapsed.

## 6. Alignment Views

Control-adjusted dominance may only be computed on shared axes that exist for
winners and controls:

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
controls. They are allowed only in winner-only descriptive outputs.

The run must produce:

```text
low_aligned view
baseline ema60 anchor-aligned view
duration-bucketed view
winner-only retrospective-stage view
```

Duration buckets use trading sessions, not calendar days. Initial duration
buckets are placeholders:

```text
fast:   low_to_high_sessions <= 40
medium: 41 <= low_to_high_sessions <= 80
long:   81 <= low_to_high_sessions <= 120
```

The formal implementation must either justify these from the reference duration
distribution or replace them with train-only quantile buckets. Validation and
robustness must not tune duration bucket boundaries. A `>120` trading-session
bucket is invalid under the primary 120-session MFE horizon.

## 7. Anchors and Feature Bank

### 7.1 Baseline Observable Anchor

The initial anchor-aligned view uses `first_ema60_reclaim`. It is the only
frozen observable anchor in v0 unless this requirement is explicitly amended.

Definition:

```text
ema60[D] = rolling_mean(qfq_close, 60)[D]
first_ema60_reclaim = first D after anchor_search_start such that:
  qfq_close[D-1] < ema60[D-1]
  qfq_close[D] >= ema60[D]
  ema60[D] is computed only from closes up to D close
```

Winner search bounds:

```text
anchor_search_start = episode_low_date
anchor_search_end = episode_high_date
```

Retrospective-low control search bounds:

```text
anchor_search_start = control_candidate_low_date
anchor_search_end = control_candidate_low_date + 120 trading sessions
```

If no `first_ema60_reclaim` exists inside the relevant search bounds, mark the
anchor-aligned view as `missing_event_absent`. Do not impute it. Anchor-aligned
winner-control dominance may only use winners and controls with a present,
same-family anchor and sufficient lookback coverage.

### 7.2 Anchor Is Not Feature Restriction

`first_ema60_reclaim` is a stable shared alignment anchor. It is not a claim
that EMA-style features are the only useful information.

The lifecycle feature bank must include hidden volume-price, VWAP, money-flow,
range-position, gap/fade, turnover, and rank-persistence expressions. A feature
may become important without becoming an event anchor.

Complex features such as VWAP deviation must first be tested as lifecycle
dominance candidates, not directly promoted to events.

### 7.3 Candidate Observable Anchors

Candidate anchors pending requirement-level definitions:

```text
first_ema20_reclaim
first_trailing_60d_low_repair_10pct
first_trailing_60d_low_repair_20pct
first_trailing_120d_low_repair_20pct
first_volatility_expansion
first_volume_or_amount_expansion
first_upper_half_close_after_expansion
first_stock_leads_industry, only if PIT industry data is available
first_industry_leads_market, only if PIT industry data is available
first_rank_jump_persistent
first_near_limit_upper_close
first_120d_high_breakout
first_destructive_high_vol
first_gap_fade
first_rank_evaporation
```

`first_near_limit_upper_close` must use actual exchange daily limit rules for
the instrument/date. Fixed 10% or 20% thresholds are not allowed without an
audited limit-price source or rule table.

Pending anchors are a definition backlog. They may be listed in the report as
future candidates, but they must not enter publishable anchor statistics,
validation gates, or final decisions until their formulas and search bounds are
frozen in this requirement.

### 7.4 Fixed Snapshot Schema

Every anchor snapshot must use the same schema:

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
stock_vs_industry_20d, if PIT industry data is available
industry_vs_market_20d, if PIT industry data is available
```

VWAP fields are daily derived fields:

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
`missing_source_field`.

## 8. Matched Controls

All dominance claims must be winner-vs-control claims on a shared axis.
Winner-only descriptive tables may not support dominance, edge, or causal
language.

Every control set must record:

```text
match_anchor_date
match_fields
match_distance
matched_control_count
unmatched_reason
future_label_used_for_profile_only
```

If match coverage is insufficient, the related claim is sample-blocked.

### 8.1 Retrospective-Low Opportunity Controls

For low-aligned profiles, controls must also satisfy the same
`candidate_low_date` eligibility.

Required match fields:

```text
same date or nearest available same-week date
same industry, if PIT industry data is available
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return
similar prior drawdown
similar volatility bucket
same candidate_low_date eligibility
not a 50% winner in the 120d forward horizon
```

### 8.2 Observable-Anchor Opportunity Controls

For anchor-aligned profiles, controls must trigger the same observable anchor
family.

For the v0 baseline `first_ema60_reclaim` profile, anchor-aligned controls must
come from the same retrospective-low opportunity pool as low-aligned controls:
they first satisfy `candidate_low_date` eligibility, then search for
`first_ema60_reclaim` inside the 120-session control search bounds. Controls
without a present EMA60 reclaim anchor are unavailable for the EMA60-aligned
dominance view, not silently treated as zero-effect controls.

Required match fields:

```text
same anchor family
same anchor date or nearest available same-week anchor date
same industry, if PIT industry data is available
similar market cap bucket
similar liquidity bucket
similar prior return / drawdown / volatility bucket
not a 50% winner in the 120d forward horizon
```

### 8.3 Near-Winner Controls

Near-winner controls:

```text
forward MFE over the same 120 trading day window in 30% to 50%
never reaches 50% within that same 120d horizon
```

They must use the same opportunity-set matching rules as the winner comparison.

### 8.4 False-Repair Controls

False-repair controls:

```text
same early repair anchor family
same anchor date or nearest available same-week anchor date
same industry, if PIT industry data is available
same market-regime bucket
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return
similar prior drawdown
similar volatility bucket
fails within 10d / 20d or forward MFE is insufficient
```

## 9. Dominance Families

The experiment must test these dominance families on shared axes:

```text
market regime
industry regime, conditional on PIT industry data
price structure
volume, money, VWAP, turnover
volatility structure
relative strength
path tolerance
```

Volume-price / VWAP / money-flow candidates are mandatory. The report must not
conclude that traditional trend features dominate until VWAP and volume-price
candidates have been evaluated under the same winner-control design.

Path-tolerance diagnostics are profile diagnostics only. They must not simulate
stop-loss or time-stop policies.

Path-tolerance features used in `shared_axis_factor_dominance.csv` must be
defined on fixed shared-axis windows, for example max drawdown from axis day to
`+20` / `+60` sessions. Retrospective path measures that depend on winner-only
high dates, such as `low_to_high_max_drawdown` or `post_high_30d_drawdown`, are
winner-only descriptive and must not be reported as dominance.

### 9.1 Market Regime Definition

Market-regime features must be computed as-of each anchor or relative-day date
from benchmark closes only.

Primary benchmark assignment:

```text
main-board stock rows: csi300
ChiNext stock rows: chinext_index
cross-market summary rows: all_a
```

The common market-regime bucket uses `all_a`:

```text
market_trend_60d = all_a_close / rolling_mean(all_a_close, 60) - 1
market_drawdown_120d = all_a_close / rolling_max(all_a_close, 120) - 1

risk_on:
  market_trend_60d >= 0 and market_drawdown_120d > -0.10

risk_off:
  market_trend_60d < 0 and market_drawdown_120d <= -0.10

transition:
  all other complete observations
```

If 60d or 120d index lookback is unavailable, market-regime fields must be
`missing_insufficient_lookback`. The 2022-2023 split remains the fixed
negative-beta validation split even if some individual dates fall into
`transition` or `risk_on` by this rule.

## 10. Required Outputs

Publishable outputs:

```text
outputs/publishable/tables/big_winner_episode_reference_summary.csv
outputs/publishable/tables/frozen_anchor_profile_summary.csv
outputs/publishable/tables/winner_vs_matched_control_stats.csv
outputs/publishable/tables/near_winner_comparison_stats.csv
outputs/publishable/tables/false_repair_comparison_stats.csv
outputs/publishable/tables/shared_axis_market_regime_dominance.csv
outputs/publishable/tables/shared_axis_factor_dominance.csv
outputs/publishable/tables/winner_only_retrospective_stage_profile.csv
outputs/publishable/tables/winner_only_industry_regime_x_retrospective_stage.csv, conditional on PIT industry data
outputs/publishable/reports/reverse_lifecycle_profile_report.md
outputs/manifests/run_manifest.json
```

Large or regenerable outputs:

```text
outputs/local_cache/big_winner_episode_reference.parquet
outputs/local_cache/episode_aligned_daily_panel.parquet
outputs/local_cache/matched_control_panel.parquet
outputs/large_raw/control_candidate_pool.parquet
outputs/large_raw/anchor_aligned_daily_panel.parquet
```

If `industry_data_status != pit_available`:

```text
do not generate primary winner_only_industry_regime_x_retrospective_stage.csv
do not include industry-relative rows in shared_axis_factor_dominance.csv
report industry diagnostics as skipped or diagnostic-only caveat
```

## 11. Validation Gates and Final Decisions

Sample gates:

```text
min_total_winner_episodes = 150
min_validation_winner_episodes = 30
min_robustness_winner_episodes = 30
min_control_match_coverage = 80%
min_average_controls_per_winner = 3
min_anchor_occurrences_for_claim = 50
min_feature_non_missing_coverage_for_claim = 70%
min_anchor_year_coverage_for_claim = 3, auxiliary concentration check
min_anchor_split_coverage_for_headline_claim = train + validation + robustness
```

Claim gates:

```text
continuous_factor:
  abs(standardized_mean_difference_winner_vs_control) >= 0.25

binary_or_bucket_factor:
  odds_ratio_or_lift_winner_vs_control >= 1.25
  or absolute_rate_difference >= 5 percentage points

stability:
  same sign in validation and robustness
  headline claims have nonzero support in train, validation, and robustness
  no single year or instrument explains the majority of the effect
```

Universal headline claims must pass the negative-beta validation split. Claims
that are unsupported or sample-blocked in 2022-2023 may only be reported as
`regime_conditional_candidate` or sample-blocked.

The experiment must count all tested factor x stage x anchor x regime x
duration-bucket comparisons. Winner-only retrospective stages must be counted
separately from shared-axis dominance tests. If p-values are reported, BH-FDR
adjusted q-values must be reported within each claim family.

Allowed final decisions:

```text
reverse_lifecycle_profile_supported_universal_dominance
reverse_lifecycle_profile_regime_conditional_candidate
reverse_lifecycle_profile_negative_beta_not_supported
reverse_lifecycle_profile_validation_sample_blocked
reverse_lifecycle_profile_sample_blocked
reverse_lifecycle_no_stable_dominance_found
descriptive_profile_only_no_control_adjusted_support
```

`reverse_lifecycle_profile_supported_universal_dominance` is intentionally
difficult to reach. A valid result may be regime-conditional,
negative-beta-unsupported, or sample-blocked. Those states are not
implementation failures.

## 12. Report Requirements

The final report must include:

- Input data and manifest hashes.
- Industry data status and caveats.
- Reference episode counts by split and year.
- Cluster-boundary overlap audit.
- `high_at_horizon_boundary` audit.
- Lookback coverage audit for 60d / 120d / 250d features.
- VWAP source-unit and qfq-adjustment availability audit.
- Control match coverage and match-distance summary.
- Validation opportunity audit for 2022-2023.
- Market-regime bucket counts by split.
- Shared-axis dominance results.
- Winner-only retrospective-stage profile, clearly labeled descriptive.
- Per-feature non-missing coverage for every reported claim.
- Multiple-testing count and claim-family summary.
- Final decision replay.

The report must not present winner-only retrospective stages as
control-adjusted dominance.

## 13. Tests and Verification

Focused tests must cover:

- Reference episode extraction on a small synthetic price path.
- Non-chain interval clustering, including A-B-C overlap behavior.
- `high_at_horizon_boundary` marking.
- Missing reason separation for insufficient lookback vs absent event.
- `first_ema60_reclaim` as-of computation.
- `first_ema60_reclaim` control search bounds.
- VWAP qfq adjustment and unavailability when money/volume units or price-basis
  alignment are missing or incompatible.
- Market-regime bucket computation from benchmark closes.
- Control matching remains in the same opportunity set.
- Split assignment by `episode_low_date`.
- Conditional industry artifact behavior.

The run must fail closed if required inputs are missing, source units are
incompatible, or output gates cannot be evaluated.
