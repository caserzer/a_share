# Requirement: Rerun 02 Reverse Lifecycle on PIT Top-N Universe V0

## 1. Objective

Rerun the reverse lifecycle profile from
`02_big_winner_reverse_lifecycle_profile_v0` on the new PIT top-N
400/100 universe/proxy produced by
`05_pit_topn_400_100_universe_v0`.

The purpose is to rebuild the target big-winner episode denominator under a
more stable daily opportunity set, then compare lifecycle dominance and split /
regime diagnostics against the fixed-cap 02 baseline.

This experiment answers:

```text
After replacing the fixed market-cap threshold universe with the PIT daily
top-N 400/100 universe/proxy, how many big-winner episodes exist, how many
universe-years are observed, what is the episode rate per 100 universe-years,
and do the 02 lifecycle dominance conclusions remain directionally supported
under the accepted source-coverage caveat?
```

The final artifact is a frozen top-N reverse lifecycle manifest and report.
If 05 still has accepted candidate-panel gaps, the final artifact is a frozen
**available-source top-N proxy** manifest and report, not a claim of exact
historical top 400/100 membership. It is not a 04 candidate-generator rerun and
does not authorize a new primary / meta model.

## 2. Current Prerequisite Status

As of the current committed `05` run, the top-N universe manifest reports:

```text
decision = topn_universe_candidate_panel_blocked
validation_passed = false
validation_failures = active_source_gaps
active_source_gap_count = 229
```

This experiment accepts that some historical stock rows are missing from the
local source cache. Therefore 05 does not have to be an exact top 400/100
universe to be used here, but the precision status must be explicit.

The implementation may proceed only under one of these 05 states:

```text
exact_topn:
  05_manifest.decision == topn_universe_supported
  05_manifest.gate_summary.validation_passed == true
  05_manifest.gate_summary.active_source_gap_count == 0

available_source_topn_candidate_gap:
  05_manifest.decision == topn_universe_candidate_panel_blocked
  05_manifest.gate_summary.validation_failures == ["active_source_gaps"]
  05_manifest.gate_summary.active_source_gap_count is reported
  05_manifest.gate_summary.candidate_panel_source == full_board_candidate_panel
  05_manifest.gate_summary.max_daily_member_count <= 500
  05_manifest.gate_summary.max_main_board_count <= 400
  05_manifest.gate_summary.max_chinext_count <= 100
  data_source_coverage_audit.csv reports missing_active_source rows
  count(support_state == "missing_active_source"
        and active_in_requested_window == true) == active_source_gap_count
  if source_gap_count is reported:
    count(support_state in {"missing_active_source", "missing_inactive_source"})
      == source_gap_count
```

If the second state is used, all outputs must label the denominator as:

```text
universe_precision_status = available_source_topn_candidate_gap
```

and must state that membership is top-N among available audited candidate rows,
not guaranteed exact historical top 400/100 across all active listed stocks.

If 05 has any failure other than accepted `active_source_gaps`, this experiment
must write a blocked manifest/report and must not produce a target denominator.

### 2.1 Controlled Difference From 02

This experiment is a 02 universe rerun. The scientific comparison is valid only
if the universe is the controlled change.

Allowed differences from `02_big_winner_reverse_lifecycle_profile_v0`:

```text
target universe input:
  02 = fixed-cap pit_largecap_main_chinext executable universe
  06 = PIT top-N 400/100 universe/proxy from 05

denominator precision metadata:
  exact_topn or available_source_topn_candidate_gap

output namespace:
  topn_* tables, report, manifest, and local cache names

additional reporting:
  universe-years, episodes per 100 universe-years, 05 source-gap caveat,
  fixed-cap 02 baseline comparison, and downstream 04 handoff gate
```

Everything else must be copied from 02 without retuning:

```text
episode definition and local-low extraction
cluster and deduplication policy
canonical episode_low_date binding
date splits and label-completeness rules
anchor definitions and anchor search bounds
feature bank and qfq-compatible VWAP basis
matched-control construction and match fields
control candidate non-chain deduplication
cross-split-boundary match handling
near-winner and false-repair control definitions
market-regime definitions
frozen sequence families, windows, order constraints, and forbidden states
sample gates, claim gates, stability gates, and multiple-testing accounting
industry-data status behavior
```

If the implementation cannot replay a 02 rule exactly, it must fail closed or
publish a diagnostic-only blocked state. It must not silently substitute a new
formula, threshold, match rule, sequence variant, split boundary, or claim gate.

## 3. Non-Goals

This experiment must not:

- Run 03 observable anchor event contract.
- Run 04 high-recall candidate generation.
- Train primary, meta, ranking, or sizing models.
- Run a backtest or create portfolio rules.
- Tune the top-N quota to improve episode count, recall, precision, or split
  stability.
- Change the big-winner definition from `mfe_120 >= 50%`.
- Change the 120-session forward horizon.
- Shorten the 250-session prior lookback to increase early sample counts.
- Use fixed-cap universe membership as the target denominator.
- Use fixed-cap universe results except as baseline comparison.
- Treat 04 `+50 bridge recall` as reusable under the new denominator.
- Claim exact historical top 400/100 membership when
  `universe_precision_status = available_source_topn_candidate_gap`.
- Change any 02 lifecycle, matching, sequence, regime, sample, claim, or
  stability rule except for the controlled universe replacement named above.

## 4. Required Inputs

### 4.1 Top-N Universe Inputs

Primary universe inputs come from `05_pit_topn_400_100_universe_v0`.

Required files:

```text
experiments/pending/05_pit_topn_400_100_universe_v0/outputs/manifests/run_manifest.json
experiments/pending/05_pit_topn_400_100_universe_v0/outputs/publishable/tables/yearly_universe_summary.csv
experiments/pending/05_pit_topn_400_100_universe_v0/outputs/publishable/tables/daily_universe_counts.csv
experiments/pending/05_pit_topn_400_100_universe_v0/outputs/publishable/tables/data_source_coverage_audit.csv
data/processed/universe/pit_topn_400_100_executable_daily.csv
data/processed/universe/pit_topn_400_100_membership_daily.csv
```

Hard input gate:

```text
05_manifest.decision in {
  topn_universe_supported,
  topn_universe_candidate_panel_blocked
}

If 05_manifest.decision == topn_universe_candidate_panel_blocked:
  validation_failures must equal ["active_source_gaps"]
  active_source_gap_count must be reported
  data_source_coverage_audit.csv must be present
  data_source_coverage_audit.csv must be the 05 manifest-referenced audit
  count(support_state == "missing_active_source" and active_in_requested_window == true)
    must equal active_source_gap_count
  if source_gap_count is reported:
    count(support_state in {"missing_active_source", "missing_inactive_source"})
      must equal source_gap_count
  run-level universe_precision_status must be set to available_source_topn_candidate_gap
```

`universe_precision_status` is a 06-derived run field. It does not have to
exist in the 05 manifest, but it must be inferred from the accepted 05 state
before denominator construction and then propagated to every 06 output.

If this gate fails, the decision must be:

```text
topn_reverse_lifecycle_topn_universe_blocked
```

and no episode extraction may run.

### 4.2 Daily Price and Benchmark Inputs

Reuse the 01 data layer and 02 feature basis:

```text
data/interim/qlib_csv/day/
data/processed/index/benchmark_indices_daily.csv
experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/outputs/manifests/run_manifest.json
experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/outputs/tables/source_coverage_audit.csv
```

Required stock fields:

```text
date
open
high
low
close
volume
money
turnover_rate
factor
```

The episode engine must use qfq prices for low/high/MFE logic. Raw prices may
only be used for already audited data-layer fields such as derived VWAP basis
when units are compatible.

### 4.3 Fixed-Cap Baseline Inputs

The fixed-cap 02 run is a baseline only.

Required comparison inputs:

```text
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/manifests/run_manifest.json
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/big_winner_episode_reference_summary.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/validation_opportunity_audit.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/unconditional_validation_readout.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/regime_conditioned_validation_readout.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/shared_axis_sequence_dominance.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/shared_axis_factor_dominance.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/shared_axis_market_regime_dominance.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/winner_vs_matched_control_stats.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/frozen_anchor_profile_summary.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/winner_only_retrospective_stage_profile.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/near_winner_comparison_stats.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/false_repair_comparison_stats.csv
experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/tables/sequence_family_test_count.csv
```

These files must not seed the new top-N denominator. They are only allowed for:

```text
baseline metric comparison
directional lifecycle conclusion comparison
fixed-cap vs top-N episode-rate delta
```

## 5. Universe Denominator Contract

The top-N executable universe is keyed by:

```text
usable_trade_date, instrument
```

For episode extraction, an instrument-date is in the opportunity set only if
that instrument is present in the top-N executable universe/proxy on the same
`usable_trade_date`.

The denominator must be rebuilt from the top-N executable universe/proxy, not
from fixed-cap 02 outputs.

Required denominator fields:

```text
usable_trade_date
instrument
board_bucket
source_membership_date
membership_available_time
upstream_history_ready_240d_flag
history_ready_250d_flag
label_complete_120d_flag
universe_precision_status
active_source_gap_count
```

The implementation must preserve the 05 PIT clock:

```text
source_membership_date < usable_trade_date
membership_available_time = source_membership_date close
```

Rows violating this clock must hard fail.

`upstream_history_ready_240d_flag` is inherited from 05 only for audit
continuity. It is not sufficient for 02 episode extraction. The evaluated
episode denominator must use `history_ready_250d_flag` and
`label_complete_120d_flag`.

If `universe_precision_status = available_source_topn_candidate_gap`, the
denominator is still usable for this rerun, but every denominator summary,
episode-rate table, report conclusion, and downstream handoff must carry the
candidate-gap caveat. The report must not describe the denominator as exact
top 400/100.

## 6. Universe-Years and Episode Rate

This experiment must report opportunity-set scale before reporting episode
counts.

Definitions:

```text
raw_topn_instrument_days =
  count of top-N executable universe/proxy rows with a valid PIT clock

evaluated_instrument_days =
  count of top-N executable universe/proxy rows where:
    history_ready_250d_flag = true
    label_complete_120d_flag = true
    usable_trade_date is inside the evaluated split/window

instrument_days =
  evaluated_instrument_days unless a table explicitly names raw_topn_instrument_days

universe_years_252 =
  instrument_days / 252

episodes_per_100_universe_years =
  target_episode_count / universe_years_252 * 100
```

The report must provide episode-rate metrics by:

```text
all sample
year
split
board_bucket
market_regime_bucket
```

The report may provide episode counts and episode mix by:

```text
duration_bucket
```

`episodes_per_100_universe_years` must be recomputed for the top-N universe.
It must not use fixed-cap 02 universe-years or episode counts.

`duration_bucket` is an episode attribute, not an ex-ante opportunity-set
attribute. Duration-bucket tables may report episode counts and episode mix. A
duration-bucket-specific universe-year denominator is not allowed unless a
pre-event duration denominator is explicitly defined in a later requirement.

When `universe_precision_status = available_source_topn_candidate_gap`, the
metric name and report prose must make clear that this is:

```text
episodes_per_100_available_source_topn_universe_years
```

The CSV column may remain `episodes_per_100_universe_years`, but the manifest
and report must define the denominator precision status.

## 7. Episode Extraction Contract

Inherit 02 V0 episode extraction unless explicitly overridden here.

For each instrument inside the top-N executable universe, construct candidate
retrospective lows using qfq prices.

An eligible `candidate_low_date = D` must satisfy:

```text
instrument is in top-N executable universe/proxy on D
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

The primary target episode definition remains:

```text
mfe_120 >= 50%
```

Cluster and deduplication policy must match 02:

```text
per instrument
non-chain direct interval overlap
seed interval does not expand while adding overlapping candidates
```

The run must preserve all 02 retrospective anchors per cluster:

```text
earliest_qualifying_low
max_mfe_low
structural_low
```

Canonical episode-level dates remain:

```text
episode_low_date = earliest_qualifying_low_date
episode_high_date = earliest_qualifying_high_date
```

Split assignment, low-aligned profiles, and matched controls must use
`episode_low_date`.

All 02 reference fields, missing-reason states, and cluster-boundary overlap
audits remain required. `high_at_horizon_boundary` episodes must be reported
separately or excluded from post-high exhaustion readouts exactly as in 02.

## 8. Splits and Label Completeness

Use the same date split policy as 02:

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

The implementation must disclose:

```text
resolved_start_trading_date
resolved_end_trading_date
effective_first_eligible_low_date
latest_label_complete_low_date
insufficient_lookback_blocked_candidate_count
label_incomplete_blocked_candidate_count
```

Split boundaries must not be moved to satisfy gates.

## 9. Lifecycle Profile Contract

The run must rerun the same core lifecycle profiles from 02 on the new top-N
denominator:

```text
low_aligned view
baseline first_ema60_reclaim anchor-aligned view
duration-bucketed view
winner-only retrospective-stage view
matched-control dominance
market-regime diagnostics
sequence dominance diagnostics
```

The 02 boundary still applies:

```text
first_ema60_reclaim is a shared alignment anchor
anchor is not a feature restriction
winner-only retrospective stages are descriptive only
dominance claims require matched controls on a shared axis
```

The following 02 mechanics must be replayed exactly:

```text
first_ema60_reclaim formula and as-of close-time computation
winner anchor search bounds from episode_low_date to episode_high_date
control anchor search bounds from control_candidate_low_date to +120 sessions
same-date or nearest same-week matching
same split or cross_split_boundary_unusable handling
control candidate pool non-chain deduplication before matching
near-winner controls with 30% <= MFE < 50% over the same 120-session horizon
false-repair control definitions
market-regime buckets computed from benchmark closes only
industry diagnostics conditional on PIT industry availability
frozen sequence families S1 through S6
sequence order constraints, forbidden states, thresholds, and missing rules
train-only sequence variant selection
multiple-testing and claim-family accounting
```

Any new sequence family, anchor family, match field, bucket boundary, feature
formula, or claim threshold is out of scope for 06.

Matching feature sources must be local to the 06 top-N opportunity set and 01
daily feature basis:

```text
board_bucket:
  from the 06 top-N executable universe/proxy row on the candidate date

total_market_cap_cny:
  from the 06 top-N executable universe/proxy row on the candidate date,
  using the PIT source_membership_date / source_asof_date already audited by 05

market_cap_bucket:
  computed by the same 02 bucket procedure from the 06 winner/control pool's
  total_market_cap_cny values

liquidity_money_20d:
  computed from qfq-compatible daily feature panel using money_mean_20d

liquidity_bucket:
  computed by the same 02 bucket procedure from 06 liquidity_money_20d values

prior_return_20d_bucket, prior_return_60d_bucket, prior_drawdown_bucket,
volatility_bucket:
  computed by the same 02 bucket procedure from 06 qfq daily features as of the
  candidate_low_date or control_candidate_low_date
```

The implementation must not use fixed-cap 02 winner/control rows, fixed-cap 02
bucket cutoffs, current/latest market-cap snapshots, or instruments outside the
06 top-N executable universe/proxy to fill missing matching fields.

VWAP and volume-price fields must preserve 02's qfq-compatible basis:

```text
raw_daily_vwap = money / volume
qfq_daily_vwap = raw_daily_vwap * qfq_adjustment_factor
qfq_adjustment_factor = qfq_close / raw_close
```

Raw VWAP must not be compared directly with qfq prices in dominance tables.

## 10. Fixed-Cap Baseline Comparison

The report must compare top-N against the original fixed-cap 02 baseline:

```text
target_episode_count
universe_years_252
episodes_per_100_universe_years
train / validation / robustness episode counts
duration bucket mix
market regime mix
board bucket mix
low_to_high_sessions distribution
shared_axis_sequence_dominance direction
shared_axis_factor_dominance direction
control match coverage
```

Baseline comparison must be clearly labeled:

```text
fixed_cap_baseline_comparison_only
```

The top-N run decision must be based on the top-N denominator/proxy, not
whether it matches fixed-cap 02 conclusions.

## 11. Outputs

Output root:

```text
topics/02_AFML_BIG_WINNER/experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/
```

### 11.1 Local Cache / Large Raw

Allowed local or large raw outputs:

```text
outputs/local_cache/topn_big_winner_episode_reference.parquet
outputs/local_cache/topn_extraction_eligibility_audit.csv
outputs/local_cache/topn_cluster_boundary_overlap_audit.csv
outputs/local_cache/topn_matched_control_panel.parquet
outputs/large_raw/topn_episode_aligned_daily_panel.parquet
outputs/large_raw/topn_anchor_aligned_daily_panel.parquet
outputs/large_raw/topn_control_candidate_pool.parquet
outputs/large_raw/topn_sequence_entity_panel.parquet
```

Large raw artifacts should remain local or ignored unless explicitly requested
for publication.

### 11.2 Publishable Tables

Required publishable tables:

```text
outputs/publishable/tables/topn_denominator_summary.csv
outputs/publishable/tables/topn_yearly_denominator_summary.csv
outputs/publishable/tables/topn_split_denominator_summary.csv
outputs/publishable/tables/topn_episode_count_summary.csv
outputs/publishable/tables/topn_episode_rate_by_year.csv
outputs/publishable/tables/topn_episode_rate_by_split.csv
outputs/publishable/tables/topn_episode_rate_by_board.csv
outputs/publishable/tables/topn_vs_fixed_cap_episode_rate_comparison.csv
outputs/publishable/tables/topn_big_winner_episode_reference_summary.csv
outputs/publishable/tables/topn_validation_opportunity_audit.csv
outputs/publishable/tables/topn_unconditional_validation_readout.csv
outputs/publishable/tables/topn_regime_conditioned_validation_readout.csv
outputs/publishable/tables/topn_shared_axis_factor_dominance.csv
outputs/publishable/tables/topn_shared_axis_market_regime_dominance.csv
outputs/publishable/tables/topn_shared_axis_sequence_dominance.csv
outputs/publishable/tables/topn_winner_vs_matched_control_stats.csv
outputs/publishable/tables/topn_near_winner_comparison_stats.csv
outputs/publishable/tables/topn_false_repair_comparison_stats.csv
outputs/publishable/tables/topn_frozen_anchor_profile_summary.csv
outputs/publishable/tables/topn_winner_only_retrospective_stage_profile.csv
outputs/publishable/tables/topn_sequence_family_test_count.csv
outputs/publishable/tables/topn_sequence_examples_descriptive.csv
outputs/publishable/tables/topn_data_source_coverage_audit.csv
outputs/publishable/tables/topn_02_rule_invariant_audit.csv
```

`topn_episode_count_summary.csv` must include:

```text
scope
year
split
board_bucket
duration_bucket
market_regime_bucket
episode_count
raw_topn_instrument_days
evaluated_instrument_days
instrument_days
universe_years_252
episodes_per_100_universe_years
```

If `duration_bucket` is populated, `instrument_days`,
`universe_years_252`, and `episodes_per_100_universe_years` must either use
the all-denominator value with an explicit `denominator_scope` column or be
left null. They must not imply that duration is known before an episode exists.

`topn_02_rule_invariant_audit.csv` must include one row per replayed 02 rule:

```text
rule_family
rule_name
02_value
06_value
allowed_difference
status
blocking
notes
```

Allowed `status` values:

```text
pass
allowed_difference
fail
not_applicable
```

Any row with `status = fail` and `blocking = true` must force:

```text
topn_reverse_lifecycle_invariant_replay_blocked
```

### 11.3 Report

Required report:

```text
outputs/publishable/reports/topn_reverse_lifecycle_profile_report.md
```

The report must include:

1. Final decision.
2. 05 universe manifest decision and hash.
3. Explicit statement whether the top-N denominator is exact or
   `available_source_topn_candidate_gap`.
4. Top-N denominator summary.
5. Episode count by year / split / board.
6. Universe-years and episodes per 100 universe-years by year / split / board.
7. Fixed-cap 02 baseline comparison.
8. Lifecycle sequence dominance rerun.
9. Split and market-regime diagnostics.
10. Control match coverage.
11. Duration bucket mix, including whether the prior long-bucket dominance
    remains.
12. Active source-gap caveat and the list/count of missing-active-source
    instruments inherited from 05, if applicable.
13. 02 invariant replay audit covering extraction, matching, sequence,
    regime, claim-gate, and multiple-testing rules.
14. Raw Top-N instrument-days vs evaluated episode-denominator instrument-days.
15. Final decision mapping from 02 semantic outcome to 06 top-N decision.
16. Clear statement that 04 must not be rerun until this manifest is frozen.

## 12. Manifest

Required manifest:

```text
outputs/manifests/run_manifest.json
```

Manifest fields:

```text
experiment_name
source_git_revision
created_at_utc
config_hash
input_paths
input_hashes
output_paths
output_hashes
upstream_01_manifest_hash
upstream_02_manifest_hash
upstream_05_manifest_hash
upstream_05_data_source_coverage_audit_hash
upstream_05_decision
topn_universe_input_accepted
exact_topn_supported
universe_precision_status
topn_candidate_gap_accepted
active_source_gap_count
source_gap_count
missing_active_source_instrument_count
missing_active_source_audit_count_reconciled
resolved_start_trading_date
resolved_end_trading_date
effective_first_eligible_low_date
latest_label_complete_low_date
episode_definition_version
universe_definition_version
inherited_02_config_hash
inherited_02_rule_invariant_status
industry_data_status
target_episode_count
raw_topn_instrument_days
evaluated_instrument_days
instrument_days
universe_years_252
episodes_per_100_universe_years
semantic_02_decision
topn_decision_mapping_version
decision
gate_summary
```

Manifest boolean semantics:

```text
topn_universe_input_accepted:
  true when the 05 input passes one of the accepted states in Section 2

exact_topn_supported:
  true only when universe_precision_status = exact_topn

topn_candidate_gap_accepted:
  true only when universe_precision_status = available_source_topn_candidate_gap

missing_active_source_audit_count_reconciled:
  true only when the data_source_coverage_audit.csv support_state formula
  reconciles to active_source_gap_count and, if present, source_gap_count
```

## 13. Decisions and Gates

Decision values:

```text
topn_reverse_lifecycle_profile_supported_universal_dominance
topn_reverse_lifecycle_profile_regime_conditional_candidate
topn_reverse_lifecycle_profile_negative_beta_not_supported
topn_reverse_lifecycle_profile_validation_sample_blocked
topn_reverse_lifecycle_profile_sample_blocked
topn_reverse_lifecycle_sequence_supported_universal_dominance
topn_reverse_lifecycle_sequence_conditional_candidate
topn_reverse_lifecycle_marginal_and_sequence_no_stable_dominance_found
topn_reverse_lifecycle_descriptive_profile_only_no_control_adjusted_support
topn_reverse_lifecycle_topn_universe_blocked
topn_reverse_lifecycle_source_blocked
topn_reverse_lifecycle_match_coverage_blocked
topn_reverse_lifecycle_label_completion_blocked
topn_reverse_lifecycle_invariant_replay_blocked
topn_reverse_lifecycle_diagnostic_only
```

`universe_precision_status` carries the exact/proxy caveat. It must not be
encoded by weakening the decision taxonomy. The final `decision` must preserve
the 02 semantic result with a `topn_reverse_lifecycle_*` prefix.

Decision priority is:

```text
input/source hard block
invariant replay block
label completion block
match coverage block
02 semantic profile/sequence decision
diagnostic_only
```

If sample support fails under the 02 gates, use the matching 02-semantic
sample decision:

```text
topn_reverse_lifecycle_profile_validation_sample_blocked
topn_reverse_lifecycle_profile_sample_blocked
```

### 13.1 Hard Fail / Blocked Gates

The run must fail closed or return a blocked decision for:

```text
05 manifest missing
05 decision not in {topn_universe_supported, topn_universe_candidate_panel_blocked}
05 decision == topn_universe_candidate_panel_blocked with failures other than active_source_gaps
05 decision == topn_universe_candidate_panel_blocked without data_source_coverage_audit.csv
05 active_source_gap_count is missing when active_source_gaps is accepted
05 data_source_coverage_audit.csv does not reconcile to active_source_gap_count
05 audit file is stale or not hash-linked to the accepted 05 manifest
02 manifest or required 02 comparison table missing
02 invariant replay cannot be verified
topn_02_rule_invariant_audit.csv missing or has a blocking fail row
06 config changes any 02 rule outside the allowed controlled differences
matching feature sources use 02 fixed-cap rows, 02 cutoffs, latest snapshots,
or outside-top-N rows
top-N executable membership missing
top-N executable duplicate key
source_membership_date >= usable_trade_date
fixed-cap membership used as target denominator
stock daily bars missing required qfq fields
benchmark daily bars missing required regime fields
latest-only market cap/status source used for top-N denominator
target denominator does not reconcile to top-N executable universe
instrument_days denominator scope ambiguous
duration_bucket used as an ex-ante universe-year denominator
universe_precision_status missing from manifest/report
exact top 400/100 claimed while active_source_gaps are accepted
episode_low_date split assignment missing or mutable
label completion cannot be determined
```

### 13.2 Sample Gates

Minimum sample gates must match 02 exactly:

```text
min_total_winner_episodes = 150
min_validation_winner_episodes = 30
min_robustness_winner_episodes = 30
min_control_match_coverage = 0.80
min_average_controls_per_winner = 3.0
min_anchor_occurrences_for_claim = 50
min_sequence_occurrences_for_claim = 50
min_feature_non_missing_coverage_for_claim = 0.70
min_anchor_year_coverage_for_claim = 3, auxiliary concentration check
min_anchor_split_coverage_for_headline_claim = train + validation + robustness
min_sequence_split_coverage_for_headline_claim = train + validation + robustness
continuous_factor_smd_gate = 0.25
binary_or_bucket_factor_lift_gate = 1.25
sequence_pattern_lift_gate = 1.25
absolute_rate_difference_gate = 0.05
negative_beta_validation_required_for_universal_claim = true
```

If sample gates fail, the run may still publish denominator and extraction
audits, but dominance conclusions must be blocked or diagnostic-only.

Multiple-testing accounting must match 02: count all tested factor x stage x
anchor x regime x duration-bucket comparisons and all tested sequence family x
shared-axis x relative-window x regime x duration-bucket comparisons. If
p-values are reported, BH-FDR q-values must be computed within the same 02
claim-family boundaries.

## 14. Tests

Add focused tests under:

```text
tests/test_topn_reverse_lifecycle_requirement.py
```

Minimum test coverage:

1. A 05 manifest blocked for non-`active_source_gaps` rejects the run before
   episode extraction.
2. A supported 05 manifest allows input validation to proceed with
   `universe_precision_status = exact_topn`.
3. A 05 manifest blocked only by accepted `active_source_gaps` allows input
   validation to proceed with
   `universe_precision_status = available_source_topn_candidate_gap`.
4. Fixed-cap membership cannot be used as target denominator.
5. Top-N executable duplicate keys are rejected.
6. `source_membership_date < usable_trade_date` is enforced.
7. 05 `data_source_coverage_audit.csv`
   `count(support_state == "missing_active_source" and active_in_requested_window == true)`
   must reconcile to manifest `active_source_gap_count`.
8. `raw_topn_instrument_days` equals executable universe row count over the raw
   PIT-clock-valid window.
9. `evaluated_instrument_days` excludes rows without 250-session lookback or
   120-session label completion.
10. `instrument_days = evaluated_instrument_days`.
11. `universe_years_252 = instrument_days / 252`.
12. `episodes_per_100_universe_years = episode_count / universe_years_252 * 100`.
13. `duration_bucket` rows cannot claim a duration-specific universe-year
    denominator.
14. Split assignment uses `episode_low_date`, not anchor or high dates.
15. Label-incomplete lows are excluded rather than shortening horizon.
16. 250-session lookback is enforced and separately audited.
17. A changed 02 rule outside the allowed universe replacement rejects the run
    with `topn_reverse_lifecycle_invariant_replay_blocked`.
18. `topn_02_rule_invariant_audit.csv` contains one row per replayed 02 rule
    and a blocking fail row forces `topn_reverse_lifecycle_invariant_replay_blocked`.
19. 02 matching rules are replayed, including control candidate non-chain
    deduplication and cross-split-boundary handling.
20. Matching feature sources come from 06 top-N executable/proxy rows and 01/qfq
    features, not 02 fixed-cap rows, 02 cutoffs, or latest snapshots.
21. 02 sequence families S1-S6, order constraints, and train-only variant
    selection are replayed.
22. 02 claim gates and multiple-testing family counts are replayed.
23. Manifest booleans distinguish `topn_universe_input_accepted`,
    `exact_topn_supported`, and `topn_candidate_gap_accepted`.
24. The generic `topn_reverse_lifecycle_sample_blocked` decision is not emitted.
25. Fixed-cap baseline comparison cannot affect top-N decision.
26. Report wording cannot claim exact top 400/100 when
    `universe_precision_status = available_source_topn_candidate_gap`.
27. 04 rerun handoff is blocked unless decision is one of the supported or
    conditional top-N lifecycle decisions and the manifest is frozen.

## 15. Downstream Handoff to 04

Only after this experiment reaches:

```text
decision in {
  topn_reverse_lifecycle_profile_supported_universal_dominance,
  topn_reverse_lifecycle_profile_regime_conditional_candidate,
  topn_reverse_lifecycle_sequence_supported_universal_dominance,
  topn_reverse_lifecycle_sequence_conditional_candidate
}

universe_precision_status in {
  exact_topn,
  available_source_topn_candidate_gap
}
```

may a later 04 rerun use:

```text
outputs/manifests/run_manifest.json
outputs/local_cache/topn_big_winner_episode_reference.parquet
outputs/publishable/tables/topn_big_winner_episode_reference_summary.csv
```

The later 04 rerun must recompute:

```text
episode-level recall
before-first-50pct recall
low+20 / low+30 / low+120 recall
+50 bridge recall
duration-bucket actionable recall
```

against the frozen top-N denominator. It must not reuse the old fixed-cap 02
target episode denominator. If
`universe_precision_status = available_source_topn_candidate_gap`, the 04 rerun
must carry the same available-source proxy caveat in every recall denominator.
