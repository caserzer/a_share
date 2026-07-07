# Requirement: 19A Entry-Universe PIT Lineage, Tradability and Data Contract

## 0. Non-Negotiable Scope

19A is the first executable contract for EP19. It freezes the entry-universe
denominator, PIT lineage, execution convention, fill feasibility, forward-label
contract, TuShare DC concept-board data contract, baseline budget, matching
protocol, grid-search accounting, robustness protocol, and replay-path
eligibility before any enrichment scan or model training is allowed.

19A must not train a model, rank securities, tune thresholds from robustness or
validation outcomes, claim tail enrichment, claim policy utility, run an entry
strategy, or authorize production trading. It is a contract-freeze and
readout-only audit materialization phase: it may materialize PIT candidate rows
and forward labels only to compute lineage, density, path-completeness, censoring,
sample-support, and effective-sample gates.

The only positive 19A decision is:

```text
decision_state = 19A_entry_universe_contract_ready
next_allowed_requirement = requirement_19b0_fast_rule_grid_enrichment_scan.md
```

This positive decision authorizes only 19B0: a train-only fast rule-grid
enrichment scan under the frozen 19A contract. It does not authorize 19B
robustness conclusions, 19C oracle replay, or any policy/backtest deployment.

Fail-closed decision states:

```text
19A_upstream_closure_blocked
19A_entry_lineage_blocked
19A_tradability_contract_blocked
19A_forward_label_contract_blocked
19A_data_contract_blocked
19A_baseline_contract_blocked
19A_search_accounting_blocked
19A_sample_support_underpowered
19A_contract_not_impl_ready
```

## 1. Identity

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19A
run_id = 19A_entry_universe_pit_lineage_tradability_and_data_contract
requirement_file = requirement_19a_entry_universe_pit_lineage_tradability_and_data_contract.md
config_file = configs/config_19a_entry_universe_pit_lineage_tradability_and_data_contract.yaml
runner_file = src/run_19a_entry_universe_pit_lineage_tradability_and_data_contract.py
test_file = tests/test_19a_entry_universe_pit_lineage_tradability_and_data_contract.py
```

Execution working directory:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repository-relative or resolved from explicit path aliases.
No implementation may hard-code `/home/xiaolv/...` absolute paths.

Path aliases:

```text
REPO_ROOT = ../../..
TOPIC_ROOT = .
EXPERIMENT_ROOT = experiments/pending/19_entry_universe_pit_tradability_preflight

SOURCE_EP18_ROOT = experiments/pending/18_payoff_state_representation_research
SOURCE_EP14_ROOT = experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP07_ROOT = experiments/pending/07_topn_multichannel_repair_candidate_generator_v0
SOURCE_EP04_ROOT = experiments/pending/04_high_recall_repair_event_candidate_generator_v0

TUSHARE_DC_ROOT = EXPERIMENT_ROOT/outputs/tushare_dc_yearly_board_snapshot
AKSHARE_BOARD_FULL_DUMP_ROOT = EXPERIMENT_ROOT/outputs/akshare_board_full_dump
```

## 2. Upstream Closure Requirement

EP19 is a topic-level restart after the payoff-state utility bridge failed to
support a policy handoff. 19A must prove this closure explicitly before creating
a new entry-universe contract.

Required upstream evidence:

```text
SOURCE_EP18_ROOT/outputs/publishable/tables/18F_payoff_state_oracle_gap_bridge/payoff_state_oracle_gap_bridge_decision.csv
SOURCE_EP18_ROOT/outputs/manifests/18F_payoff_state_oracle_gap_bridge_manifest.json
SOURCE_EP18_ROOT/outputs/manifests/input_artifact_manifest_18f.json
EXPERIMENT_ROOT/research_plan.md
```

Required 18F decision facts:

```text
decision_state = 18F_utility_bridge_not_supported
next_allowed_requirement = none
policy_training_authorized = false
policy_replay_authorized = false
deployment_authorized = false
learned_utility_support_gate = fail
```

If the upstream closure evidence is missing, contradictory, or authorizes a
policy handoff, 19A must stop with:

```text
decision_state = 19A_upstream_closure_blocked
```

Required output:

```text
upstream_closure_audit.csv
```

## 3. Research Questions

19A answers only preflight questions:

```text
Q1. Can a no-hindsight candidate row be represented with instrument,
    decision_date, decision_time_bucket, entry_date, entry_price_source,
    generator lineage, PIT feature snapshot, and readout-only forward labels?

Q2. Can existing candidate sources and simple rule families be represented
    without outcome leakage and without validation-set threshold selection?

Q3. Can a next-tradable-open execution convention and fill-feasibility screen
    be frozen before any tail-enrichment scan?

Q4. Can forward outcome labels, path completeness, censoring, and survival
    fallback be frozen as readout-only evaluation fields?

Q5. Can TuShare Pro Eastmoney concept-board annual snapshots be used as
    vendor-derived annual theme buckets without claiming genuine PIT industry
    membership?

Q6. Can same-budget random, instrument-matched random, and
    liquidity/size/volatility-matched baselines be frozen with quality gates?

Q7. Can cooldown, canonicalization, effective sample size, and minimum support
    thresholds be frozen before 19B0?

Q8. Can grid-search size, family accounting, multiplicity correction, and
    validation non-use be proven from manifests?
```

19A must not answer whether any entry rule works. Tail enrichment, matched
baseline improvement, false-positive burden, and replay value are frozen here
but evaluated only in later phases.

## 4. Allowed and Forbidden Work

Allowed in 19A:

```text
1. Read existing EP18 closure artifacts.
2. Read EP19 research_plan.md.
3. Audit candidate-source availability from EP04, EP07, EP13, and EP14.
4. Define candidate row schema and generator lineage requirements.
5. Define canonical event and cooldown denominators.
6. Define next-open execution and fill-feasibility rules.
7. Define forward label, path-completeness, censoring, and survival fallback.
8. Freeze TuShare DC concept-board snapshot mapping and data status.
9. Freeze baseline budget, matching keys, and matching quality gates.
10. Freeze grid-search budget, family accounting, and correction protocol.
11. Freeze robustness, validation stress, and replay-path eligibility rules.
12. Materialize readout-only candidate and label audit rows to compute
    denominator, density, path-completeness, censoring, sample-support, and
    effective-sample gates.
13. Emit a contract report and machine-readable audit tables.
```

Forbidden in 19A:

```text
1. No model training.
2. No candidate ranking by forward outcome.
3. No threshold tuning using robustness or validation outcomes.
4. No validation-set selection.
5. No strategy PnL or portfolio simulation.
6. No claim that pre-2025 concept membership is historical PIT evidence.
7. No use of TuShare DC concept boards as genuine PIT industry classification.
8. No use of forward labels as candidate membership, ranking, threshold,
   family-selection, grid-cell selection, or trading-policy inputs.
9. No use of quarantined AkShare board dumps as feature, matching key, PIT
   industry source, board/style source, theme source, or candidate-family input.
10. No expansion to new data vendors unless this requirement is amended.
11. No handoff to policy training or deployment.
```

## 5. Required Inputs

### 5.1 Planning Inputs

```text
EXPERIMENT_ROOT/research_plan.md
EXPERIMENT_ROOT/requirement_19a_entry_universe_pit_lineage_tradability_and_data_contract.md
```

The runner must hash these files into `input_artifact_audit.csv`.

### 5.2 TuShare DC Concept-Board Inputs

19A uses only the already produced TuShare Pro Eastmoney concept-board snapshot
bundle:

```text
TUSHARE_DC_ROOT/README.md
TUSHARE_DC_ROOT/metadata/classification_year_snapshot_mapping.csv
TUSHARE_DC_ROOT/metadata/year_first_trade_dates.csv
TUSHARE_DC_ROOT/metadata/dataset_summary.csv
TUSHARE_DC_ROOT/metadata/run_config.json
TUSHARE_DC_ROOT/combined/dc_index_yearly_first_open.csv
TUSHARE_DC_ROOT/combined/dc_member_yearly_first_open.csv
```

TuShare token values must never be written to outputs, manifests, reports, or
logs. If the runner needs to refresh TuShare data in a future phase, the token
must come from environment/config secret handling, not from this requirement.

### 5.3 Candidate-Source Inputs

Existing candidate sources are audit inputs, not automatically supported
sources:

```text
SOURCE_EP04_ROOT
SOURCE_EP07_ROOT
SOURCE_EP13_ROOT
SOURCE_EP14_ROOT
```

Each source must be assigned one of these statuses:

```text
lineage_supported
lineage_supported_with_adapter
candidate_source_optional_until_adapter_selected
lineage_blocked
source_missing
```

Missing optional sources do not fail 19A. A source can contribute to later 19B0
only if it is marked `lineage_supported` or `lineage_supported_with_adapter` and
its adapter contract is emitted in `entry_candidate_lineage_audit.csv`.

### 5.4 Market and Security-Master Inputs

19A must resolve these through config, manifest, or existing project data
contracts:

```text
qfq daily OHLCV
daily amount or turnover
suspension/trading-status fields
price-limit status or sufficient data to infer one-day limit-up block
security master with listing date, delisting date, exchange, and board metadata
ST or special-treatment status if available
trading calendar
```

If a required field is unavailable, 19A must record the unavailable field and
fail only the dependent contract gate. It must not silently substitute a
current-view field for PIT metadata.

Required field-availability output:

```text
tradability_field_availability_audit.csv
```

If a field is not used by the active 19A primary adapter, it may be marked
`unavailable_not_used_in_primary_19a_adapter` or `partial_adapter_*` without
failing unrelated gates, but the unavailable field and affected gate scope must
be explicit.

## 6. Candidate Row Contract

The atomic 19A row is an entry candidate row, not a stock-day universe row.

Required candidate row fields:

```text
instrument
decision_date
decision_time_bucket
entry_date
entry_price_source
entry_executable_price
entry_fill_feasibility_status
candidate_generator_id
candidate_generator_family
candidate_event_id
canonical_event_id
cooldown_key
cooldown_window_sessions
source_artifact_path
source_artifact_hash
source_row_id
pit_feature_snapshot_id
classification_year
effective_start_date
effective_end_date
classification_first_open_trade_date
source_snapshot_year
source_snapshot_trade_date
snapshot_policy
label_snapshot_id
```

Rules:

```text
1. `decision_date` is the date when all candidate features are observable.
2. `decision_time_bucket` defaults to `after_close_t`.
3. `entry_date` defaults to the next tradable date after `decision_date` for
   the same instrument.
4. `entry_price_source` defaults to `qfq_open_next_tradable_day`.
5. `entry_executable_price` is never allowed to depend on future high, low,
   close, or forward return.
6. `candidate_event_id` identifies the raw generator event.
7. `canonical_event_id` identifies the de-duplicated event after same-day and
   cooldown canonicalization.
8. `label_snapshot_id` links to readout-only forward labels and must not be
   used to form candidate membership.
```

Any source that emits pre-open, intraday, or same-open decisions must provide an
explicit observability proof. Without that proof, the source is demoted to
`lineage_supported_with_adapter` under the default after-close to next-open
convention, or blocked if adaptation is impossible.

## 7. Denominator Contract

19A freezes these denominators:

```text
raw_trigger_rows:
    All rows emitted by the source generator before canonicalization.

canonical_event_rows:
    One row per instrument and decision_date after merging all same-day
    generator families into deterministic feature/source flags.

cooldown_entry_rows:
    Canonical rows after applying the frozen cooldown rule.

candidate_denominator:
    Valid PIT cooldown entry rows after canonicalization, before fill
    feasibility, label completeness, and forward outcome availability filters.

fill_feasible_candidate_denominator:
    candidate_denominator rows that pass the frozen fill-feasibility contract.

eligible_universe_baseline:
    All baseline-eligible instrument-date rows under the same calendar,
    listing, data-availability, and fill-feasibility constraints.

matched_budget_baseline:
    Same-budget matched baseline rows selected under frozen matching rules.

primary_enrichment_denominator:
    fill_feasible_candidate_denominator rows intersect
    label_eligible_rows_under_frozen_censoring_rule.

replay_denominator:
    fill_feasible_candidate_denominator rows intersect
    replay_path_eligible_rows_under_frozen_replay_horizon_rule.
```

Default cooldown:

```text
primary_cooldown_window_sessions = 10
sensitivity_cooldown_window_sessions = [5, 20]
cooldown_scope = instrument
```

Cooldown must be applied before any label readout. If two events collide inside
the same cooldown scope, the earliest decision date survives. Ties on the same
decision date must be merged into one canonical event row with all triggering
family/source flags preserved. If source-specific scalar fields cannot be
merged losslessly, the tie must be resolved by deterministic source priority and
row hash, and the tie rule must be written to `cooldown_audit.csv`.

## 8. Execution and Fill-Feasibility Contract

Default execution convention:

```text
decision_time_bucket = after_close_t
entry_date = next_tradable_date(decision_date, instrument)
entry_price_source = qfq_open_next_tradable_day
entry_executable_price = qfq_open on entry_date
```

Primary fill-feasibility requirements:

```text
entry_open_price_available = true
entry_suspended_flag = false
entry_limit_up_blocked_flag = false
entry_amount_available = true
entry_liquidity_primary_gate = pass
```

Default liquidity gate:

```text
entry_day_amount_cny > 0
rolling_20d_median_amount_cny_asof_decision_date >= 20000000
```

Default impact-cost diagnostic:

```text
impact_cost_proxy_bps = 10000 * candidate_budget_cny / max(entry_day_amount_cny, 1)
impact_cost_proxy_warn_bps = 50
```

19C replay cost assumptions must be frozen in 19A, even though 19A does not run
the replay:

```text
cost_schedule_source
commission_buy_bps
commission_sell_bps
minimum_commission_cny
stamp_tax_sell_bps_by_effective_date
slippage_bps
next_open_execution_delay_sessions = 1
limit_up_buy_handling = blocked_unfilled
limit_up_fill_premium_bps
limit_down_exit_failure_handling
blocked_fill_opportunity_loss_policy
cost_assumption_status
```

If any cost or tax schedule is unavailable, later 19C replay remains
diagnostic-only until the missing cost assumption is frozen by requirement.

An entry-day limit-down state does not block a buy in the primary convention,
but it must be recorded as a stress field. Missing price-limit data must not be
treated as pass; it must be recorded as `limit_status_unknown`, and the
fill-feasibility gate must decide whether the affected source can remain
supported.

Required output:

```text
entry_execution_convention_audit.csv
entry_fill_feasibility_audit.csv
replay_cost_assumption_freeze.csv
```

## 9. Forward Label and Censoring Contract

Forward labels are readout-only evaluation fields. They must not be used to
create, filter, rank, or tune candidate membership in 19A or 19B0.

Primary label:

```text
forward_big_winner_120d =
    max(qfq_high from entry_date through entry_date + 120 trading sessions)
    / entry_executable_price - 1 >= 0.50

forward_big_winner_120d is equivalent to:
    forward_mfe_120d >= 0.50
```

Required forward fields:

```text
forward_label_id
entry_price_source
forward_horizon_sessions
max_forward_high_price_source
forward_mfe_20d
forward_mfe_60d
forward_mfe_120d
forward_mae_10d
forward_mae_20d
forward_mae_60d
forward_mae_120d
forward_return_20d
forward_return_60d
forward_return_120d
fast_fail_10d
false_repair_20d
big_failure_20d_or_60d
forward_big_winner_20d
forward_big_winner_60d
forward_big_winner_120d
path_complete_flag
path_complete_20d
path_complete_60d
path_complete_120d
censoring_status
last_available_forward_session
label_readout_only_flag = true
candidate_membership_uses_forward_label = false
```

Primary censoring rule:

```text
primary_label_requires_path_complete_120 = true
```

Survival fallback rule:

```text
If validation path_complete_120_rate < 0.70, later phases may emit a
survival-adjusted diagnostic readout, but it remains diagnostic unless a future
requirement explicitly promotes it before looking at validation outcomes.
```

If the primary path-complete denominator is too small under the minimum support
rules in Section 17, 19A must fail closed with:

```text
decision_state = 19A_sample_support_underpowered
```

Required outputs:

```text
forward_outcome_label_freeze.csv
censoring_treatment_freeze.csv
```

## 10. Split Construction Freeze

19A must freeze split construction before any 19B0 grid scan.

Rules:

```text
1. Splits are chronological.
2. Purge and embargo are applied around split boundaries.
3. Validation is never used for threshold selection, family selection, or
   grid-cell selection.
4. Split dates must be declared in config and written to output before any
   label readout table is evaluated.
5. If existing candidate-source splits are reused, their dates, purge, embargo,
   and source hashes must be recorded.
```

Default purge and embargo:

```text
purge_window_sessions = 120
embargo_window_sessions = 20
```

Required output:

```text
split_construction_freeze.csv
```

## 11. TuShare DC Concept-Board Data Contract

19A uses only TuShare Pro Eastmoney concept-board data:

```text
source = Tushare Pro / 东方财富概念板块
interfaces = dc_index, dc_member
```

Frozen annual mapping:

```text
classification_year < 2025:
    effective_start_date = classification_year first-open A-share trading day
    effective_end_date = classification_year last-open A-share trading day
    classification_first_open_trade_date = classification_year first-open A-share trading day
    source_snapshot_year = 2025
    source_snapshot_trade_date = 2025 first-open A-share trading day
    snapshot_policy = pre_2025_backfilled_from_2025_snapshot

classification_year = 2025:
    effective_start_date = 2025 first-open A-share trading day
    effective_end_date = 2025 last-open A-share trading day
    classification_first_open_trade_date = 2025 first-open A-share trading day
    source_snapshot_year = 2025
    source_snapshot_trade_date = 2025 first-open A-share trading day
    snapshot_policy = exact_year_first_open_snapshot

classification_year = 2026:
    effective_start_date = 2026 first-open A-share trading day
    effective_end_date = 2026 last-open A-share trading day
    classification_first_open_trade_date = 2026 first-open A-share trading day
    source_snapshot_year = 2026
    source_snapshot_trade_date = 2026 first-open A-share trading day
    snapshot_policy = exact_year_first_open_snapshot
```

Boundary:

```text
1. Pre-2025 rows are fixed taxonomy backfill, not historical PIT membership
   evidence.
2. No row may claim that pre-2025 TuShare DC concept membership was the true
   membership at the historical decision date.
3. No intrayear constituent change is inferred.
4. TuShare DC concept membership may support annual matched buckets,
   concentration readouts, and theme-diffusion diagnostics.
5. TuShare DC concept membership cannot rescue a feature that requires genuine
   PIT industry membership.
```

Matching-key boundary:

```text
1. `pre_2025_backfilled_from_2025_snapshot` concept/theme buckets are
   diagnostic-only and forbidden as PIT matching keys for classification years
   before 2025.
2. `instrument_or_industry_bucket_if_supported` cannot be filled by pre-2025
   TuShare DC backfilled concept/theme membership.
3. Exact-year 2025/2026 TuShare DC concept/theme buckets may be used only as
   explicitly labeled annual vendor theme buckets, never as genuine PIT industry
   buckets.
4. Any baseline matching spec that uses a concept/theme bucket must report
   `theme_bucket_matching_policy`, `snapshot_policy`, and
   `historical_pit_membership_evidence_flag`.
```

Out-of-contract source quarantine:

```text
AKSHARE_BOARD_FULL_DUMP_ROOT:
    status = quarantined_out_of_contract
    allowed_use = inventory/hash/provenance audit only
    forbidden_use = 19A/19B0 feature, PIT industry source, board/style source,
        concept/theme matching key, or candidate-family input

Reason:
    AkShare board dumps and board-index histories do not prove historical stock
    constituent membership. They must not be interpreted as PIT industry,
    board, or theme membership evidence in EP19.
```

EP19A industry support status:

```text
industry_classification:
    unsupported_external_pit_industry_source

industry_relative_strength:
    unsupported_primary_feature

industry_breadth:
    unsupported_primary_feature

board_or_style_proxy_from_tushare_dc:
    forbidden

concept_or_theme_proxy:
    supported_as_annual_vendor_theme_bucket
```

The simple B3 industry/board breadth family must fail closed for genuine PIT
industry features unless a future requirement introduces a separate PIT industry
source. It may emit a concept/theme diagnostic only if clearly labeled
diagnostic and excluded from primary feature support.

Required outputs:

```text
industry_data_contract.csv
industry_pit_audit.csv
theme_snapshot_status.csv
board_source_quarantine_audit.csv
```

`theme_snapshot_status.csv` required fields:

```text
classification_year
effective_start_date
effective_end_date
classification_first_open_trade_date
source_snapshot_year
source_snapshot_trade_date
snapshot_policy
dc_index_row_n
dc_member_row_n
concept_board_n
member_instrument_n
pre_2025_backfill_flag
historical_pit_membership_evidence_flag = false for pre-2025 backfill rows
source_hash
status
blocking_reason
```

`board_source_quarantine_audit.csv` required fields:

```text
source_root
source_vendor
source_payload_type
inventory_hash
quarantine_status
allowed_use
forbidden_use
historical_pit_membership_evidence_flag = false
feature_use_detected_flag
matching_use_detected_flag
candidate_source_use_detected_flag
blocking_reason
```

## 12. Candidate Families and Source Accounting

19A freezes the candidate-family inventory but does not evaluate outcomes.

Existing source families to audit:

```text
EP04 high-recall repair event candidate generator
EP07 top-N multichannel repair candidate generator
EP13 full PIT native event discovery outputs
EP14 full native sparse state-change event utility preflight outputs
```

Simple baseline families:

```text
B1_near_120d_high_plus_volume_expansion
B2_relative_strength_breakout
B3_industry_or_theme_breadth_expansion
B4_volatility_contraction_then_breakout
B5_recent_high_close_plus_amount_expansion
B6_low_drawdown_reclaim_or_ema_reclaim
```

B3 primary support rule:

```text
If B3 requires genuine PIT industry classification, status =
unsupported_primary_feature. If B3 is rewritten as TuShare DC concept/theme
diagnostic, status = diagnostic_only_theme_proxy and it cannot enter the
primary supported family set.

Unsupported or diagnostic-only B3 variants remain in the manifest with blocking
reason, but do not consume `N_family_cap`.
```

Family cap:

```text
N_family_cap = 10
```

`N_family_cap` counts supported primary family units, not source roots. One
source root may emit more than one family only if each family has a distinct
predeclared generator contract and consumes one family slot. Unsupported,
data-contract-blocked, or diagnostic-only families remain in the manifest with
blocking reason but do not consume the cap. Any supported primary family above
the cap must be marked `family_excluded_by_predeclared_cap` before label readout.
Excluded families cannot be inspected later and re-added without a new
requirement.

Required output:

```text
entry_candidate_lineage_audit.csv
family_search_accounting_manifest.csv
```

## 13. Baseline Budget and Matching Contract

19A must freeze three baseline families:

```text
calendar_time_random_same_budget
instrument_matched_random_same_budget
liquidity_size_volatility_matched_same_budget
```

Default primary baseline rule:

```text
primary_baseline_pass_rule = conjunctive_pass_across_all_three_baselines
```

Same-budget must be reported at every denominator level. For the later primary
tail-lift gate, each baseline receives the same row count as the
`primary_enrichment_denominator` under the same split, cooldown,
fill-feasibility, and censoring rules. The broader `candidate_denominator` is
kept for density, availability, and untradeable-opportunity audits, not for
primary label-rate comparison.

Default matching keys:

```text
decision_month
instrument_or_industry_bucket_if_supported
market_cap_bucket_asof_decision_date
rolling_20d_amount_bucket_asof_decision_date
rolling_60d_volatility_bucket_asof_decision_date
recent_20d_return_bucket_asof_decision_date
```

If PIT market cap is unavailable, the implementation must either use a
predeclared resolver-backed substitute or mark the size key unavailable. It must
not use current market cap as a historical matching key.

Theme/concept matching-key rule:

```text
pre_2025_backfilled_from_2025_snapshot:
    forbidden_as_matching_key = true
    allowed_role = diagnostic_only

exact_year_first_open_snapshot:
    may be used only as annual_vendor_theme_bucket if explicitly declared in
    `baseline_matching_spec.csv`; it cannot fill a PIT industry bucket.

AKSHARE_BOARD_FULL_DUMP_ROOT:
    forbidden_as_matching_key = true
```

Default matching quality gates to freeze before any tail-lift test:

```text
unmatched_candidate_rate <= 0.05
baseline_reuse_rate <= 0.20
max_standardized_mean_difference_after_matching <= 0.10
decision_month_coverage_delta <= 0.02
instrument_coverage_delta <= 0.05
matched_baseline_primary_row_count >= primary_enrichment_denominator_row_count
```

19A freezes these thresholds and the required audit columns. It does not
materialize the final matched baseline rows or claim that the matching quality
has already been observed. Therefore `baseline_matching_quality_audit.csv` must
use:

```text
quality_status = frozen_pending_19B0_baseline_materialization
baseline_materialized_in_19a = false
```

If the baseline contract, matching keys, or quality-threshold freeze is missing
or uses forbidden keys, 19A must stop with:

```text
decision_state = 19A_baseline_contract_blocked
```

After 19B0 materializes train-only matched baselines, and before any later
tail-lift support claim, these quality gates must be evaluated on observed
matched rows. If the observed matching quality gate fails, later tail-lift tests
are not authorized.

Required outputs:

```text
baseline_budget_freeze.csv
baseline_matching_spec.csv
baseline_matching_quality_audit.csv
```

## 14. Grid Search and Multiple-Testing Freeze

19A freezes search accounting before any scan.

Grid limits:

```text
grid_parameter_n_per_family <= 5
grid_total_cells_all_families <= 300
validation_selected_cells = 0
```

Selection rule for later 19B0:

```text
1. Train split may select candidate cells.
2. Validation split cannot select cells.
3. Default promotion is one train-selected cell per family.
4. A top-2 or top-3 low-correlation promotion is allowed only if declared
   before the scan and counted in the multiplicity correction.
```

Default correction:

```text
family_level_correction = Bonferroni-Sidak
cell_level_accounting = all_tried_cells_counted
default_correction_scope =
    N_family_brought_to_robustness * primary_metric

expanded_cell_correction_scope =
    N_tested_family_cell_pairs * primary_metric

active_correction_scope =
    default_correction_scope when exactly one train-selected cell per family
    enters 19B robustness; otherwise expanded_cell_correction_scope.
```

Required outputs:

```text
grid_search_manifest.csv
family_search_accounting_manifest.csv
multiple_testing_correction_freeze.csv
```

`multiple_testing_correction_freeze.csv` required fields:

```text
family_level_correction
cell_level_accounting
primary_metric
selected_cell_rule
expanded_cell_rule_enabled
N_family_brought_to_robustness_source
N_tested_family_cell_pairs_source
correction_scope_formula
active_correction_scope
validation_selected_cells
status
blocking_reason
```

`robustness_test_manifest.csv` required fields after 19B0 train-only triage and
before any 19B robustness readout:

```text
family_id
grid_cell_id
selected_for_19B_robustness_flag
selection_split = train
selection_rank
low_correlation_group_id
N_family_brought_to_robustness
N_tested_family_cell_pairs
active_correction_scope
manifest_frozen_before_robustness_readout = true
status
blocking_reason
```

## 15. Primary Metric, Margin, and Burden Freeze

19A freezes metrics for later phases but does not evaluate them as evidence.

Primary metric:

```text
primary_metric = primary_tail_lift_50
primary_tail_lift_50 =
    candidate_forward_big_winner_120d_rate /
    matched_baseline_forward_big_winner_120d_rate
```

Sensitivity metrics:

```text
tail_lift_20
tail_lift_30
tail_lift_100
CCDF of forward_mfe_120d
forward_mae_20d distribution
forward_mae_60d distribution
forward_mae_120d distribution
candidate_per_winner
```

Zero-baseline rule:

```text
If matched_baseline_forward_big_winner_120d_rate = 0, the primary ratio is not
supportable as a pass metric. Jeffreys-smoothed ratios may be reported as
diagnostic only, and the primary gate cannot pass on a zero raw baseline rate.
```

Default margin rule for later robustness:

```text
cluster_bootstrap_SE_candidate_big_winner_120d_rate =
    cluster bootstrap SE of candidate_forward_big_winner_120d_rate on the
    primary enrichment denominator.

matched_baseline_uncertainty_treatment =
    matched baseline rows must be resampled or rerandomized under the frozen
    matching/budget protocol so uncertainty in matched_baseline_forward_
    big_winner_120d_rate is included.

cluster_bootstrap_SE_delta_big_winner_120d_rate =
    SE of candidate_forward_big_winner_120d_rate -
    matched_baseline_forward_big_winner_120d_rate using the joint
    cluster-aware candidate bootstrap plus matched-baseline rerandomization.

primary_tail_lift_50_margin_probability =
    2 * cluster_bootstrap_SE_delta_big_winner_120d_rate
    unit = absolute probability points, not a ratio

primary_tail_lift_50_margin_ratio =
    max(
        0.10,
        primary_tail_lift_50_margin_probability
          / matched_baseline_forward_big_winner_120d_rate
    )

train_to_robustness_winners_curse_treatment =
    no train-split lift enters the pass metric. Later 19B support must be based
    on robustness-split effect after frozen family/cell multiplicity correction.
    The report must include a train-selected-to-robustness shrinkage diagnostic;
    if that diagnostic cannot be computed, support is downgraded to diagnostic.
```

Default false-positive burden tolerance:

```text
primary_left_tail_burden =
    candidate_forward_mae_20d_p10 - matched_baseline_forward_mae_20d_p10

primary_left_tail_burden_pass =
    primary_left_tail_burden >= -0.02
```

The relative tolerance
`candidate_forward_mae_20d_p10 / matched_baseline_forward_mae_20d_p10 >= 0.90`
may be reported as a sensitivity diagnostic but is not the primary burden gate.

Required output:

```text
primary_metric_and_margin_freeze.csv
```

## 16. Validation Stress and Replay Eligibility Freeze

Validation rule:

```text
1. Validation never selects thresholds, families, or cells.
2. If train and robustness pass but validation has insufficient sample support,
   later phases must downgrade the conclusion to underpowered rather than pass.
3. If validation support is sufficient and validation tail lift is below 1.0,
   later phases must fail the validation stress gate.
4. If validation support is sufficient and left-tail burden fails the frozen
   tolerance, later phases must fail the validation stress gate.
```

Replay eligibility for later 19C:

```text
replay_path_eligible = true only if:
    entry_fill_feasibility_status = pass
    cooldown_entry_row = true
    path_complete_for_replay_horizon = true
    entry_executable_price is available
    no unsupported same-day execution assumption is used
```

19A must freeze these rules but must not run an oracle replay.

Required outputs:

```text
validation_stress_rule_freeze.csv
replay_path_eligibility_freeze.csv
replay_cost_assumption_freeze.csv
```

## 17. Minimum Sample Support and Effective Sample Size

Default support thresholds:

```text
train_primary_denominator_n >= 5000
robustness_primary_denominator_n >= 1000
validation_primary_denominator_n >= 300

train_instrument_n >= 100
robustness_instrument_n >= 50
validation_instrument_n >= 30

primary_path_complete_120_rate >= 0.70
effective_sample_ratio >= 0.30
```

Effective sample size must account for clustering by instrument and decision
month. The implementation may use cluster-count diagnostics or an explicit
design-effect estimate, but the chosen method must be written to:

```text
effective_sample_size_readout.csv
```

If minimum support fails, 19A must not lower thresholds after seeing the label
distribution. It must stop with:

```text
decision_state = 19A_sample_support_underpowered
```

## 18. Required Outputs

19A output root:

```text
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract
```

Required machine-readable outputs:

```text
input_artifact_audit.csv
upstream_closure_audit.csv
entry_candidate_lineage_audit.csv
pit_feature_availability_audit.csv
entry_execution_convention_audit.csv
entry_fill_feasibility_audit.csv
tradability_field_availability_audit.csv
replay_cost_assumption_freeze.csv
event_canonicalization_audit.csv
cooldown_audit.csv
split_construction_freeze.csv
forward_outcome_label_freeze.csv
censoring_treatment_freeze.csv
candidate_density_and_overlap_audit.csv
effective_sample_size_readout.csv
industry_data_contract.csv
industry_pit_audit.csv
theme_snapshot_status.csv
board_source_quarantine_audit.csv
baseline_budget_freeze.csv
baseline_matching_spec.csv
baseline_matching_quality_audit.csv
grid_search_manifest.csv
family_search_accounting_manifest.csv
robustness_test_manifest.csv
primary_metric_and_margin_freeze.csv
multiple_testing_correction_freeze.csv
validation_stress_rule_freeze.csv
replay_path_eligibility_freeze.csv
entry_universe_preflight_decision.csv
```

Required narrative outputs:

```text
19A_contract_freeze.md
19A_entry_universe_pit_lineage_tradability_and_data_contract_report.md
```

Required manifest outputs:

```text
manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
output_hashes_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
```

## 19. Decision Gates

Critical 19A gates:

```text
upstream_closure_gate
pit_lineage_gate
entry_execution_gate
fill_feasibility_gate
forward_label_freeze_gate
winner_membership_independence_gate
event_canonicalization_gate
cooldown_entry_denominator_gate
primary_enrichment_denominator_gate
censoring_treatment_gate
split_stability_gate
industry_data_contract_gate
industry_pit_gate
theme_snapshot_status_gate
primary_metric_margin_freeze_gate
baseline_budget_gate
baseline_matching_quality_gate
sample_support_gate
candidate_density_gate
effective_sample_size_gate
validation_stress_rule_freeze_gate
search_accounting_gate
family_level_multiplicity_gate
replay_path_eligibility_freeze_gate
minimum_sample_support_gate
no_policy_authorization_gate
implementation_readiness_gate
```

Gates intentionally not evaluated in 19A:

```text
tail_enrichment_gate = frozen_not_evaluated_in_19A
matched_baseline_improvement_gate = frozen_not_evaluated_in_19A
false_positive_burden_gate = frozen_not_evaluated_in_19A
policy_utility_gate = not_authorized_in_19A
oracle_replay_gate = not_authorized_in_19A
```

Positive decision requires every critical 19A gate to pass. Any critical gate
with missing evidence, contradictory evidence, or unauditable assumptions must
produce a fail-closed decision.

Fail-closed state mapping:

```text
19A_upstream_closure_blocked:
    upstream_closure_gate

19A_entry_lineage_blocked:
    pit_lineage_gate
    winner_membership_independence_gate
    event_canonicalization_gate
    cooldown_entry_denominator_gate

19A_tradability_contract_blocked:
    entry_execution_gate
    fill_feasibility_gate
    replay_path_eligibility_freeze_gate

19A_forward_label_contract_blocked:
    forward_label_freeze_gate
    censoring_treatment_gate
    primary_enrichment_denominator_gate

19A_data_contract_blocked:
    industry_data_contract_gate
    industry_pit_gate
    theme_snapshot_status_gate

19A_baseline_contract_blocked:
    baseline_budget_gate
    baseline_matching_quality_gate

19A_search_accounting_blocked:
    search_accounting_gate
    family_level_multiplicity_gate
    primary_metric_margin_freeze_gate
    validation_stress_rule_freeze_gate

19A_sample_support_underpowered:
    sample_support_gate
    minimum_sample_support_gate
    candidate_density_gate
    effective_sample_size_gate

19A_contract_not_impl_ready:
    implementation_readiness_gate
    no_policy_authorization_gate
```

If multiple mappings fail, the decision must choose the first state in the
ordering above and list all failed gates in `blocking_reason`.

Required decision row fields:

```text
run_id
created_at
requirement_file_hash
config_file_hash
decision_state
next_allowed_requirement
upstream_closure_gate
pit_lineage_gate
entry_execution_gate
fill_feasibility_gate
forward_label_freeze_gate
winner_membership_independence_gate
event_canonicalization_gate
cooldown_entry_denominator_gate
primary_enrichment_denominator_gate
censoring_treatment_gate
split_stability_gate
industry_data_contract_gate
industry_pit_gate
theme_snapshot_status_gate
primary_metric_margin_freeze_gate
baseline_budget_gate
baseline_matching_quality_gate
sample_support_gate
candidate_density_gate
effective_sample_size_gate
validation_stress_rule_freeze_gate
search_accounting_gate
family_level_multiplicity_gate
replay_path_eligibility_freeze_gate
minimum_sample_support_gate
no_policy_authorization_gate
implementation_readiness_gate
blocking_reason
```

## 20. Report Requirements

The 19A report must include:

```text
1. Upstream closure summary and why EP19 is a restart, not a policy handoff.
2. Candidate row schema and lineage status by source.
3. Execution convention, fill-feasibility rules, and blocked-row accounting.
4. Event canonicalization and cooldown denominator accounting.
5. Forward-label and censoring contract, with explicit readout-only status.
6. Split construction, purge, embargo, and validation non-use statement.
7. TuShare DC concept-board annual snapshot contract, including pre-2025
   backfill caveat.
8. AkShare board dump quarantine status and forbidden-use audit.
9. Industry/board/theme support matrix.
10. Baseline budget, matching keys, and matching quality gates.
11. Grid-search budget, family cap, and multiplicity correction.
12. Minimum sample support and effective sample size readout.
13. Final decision state and exact next allowed requirement.
```

The report must state clearly:

```text
19A does not prove that any entry signal works.
19A does not train a model.
19A does not authorize a strategy.
Pre-2025 TuShare DC concept membership is a fixed taxonomy backfill, not
historical PIT membership evidence.
```

## 21. Validation Commands

Expected command sequence:

```bash
cd topics/02_AFML_BIG_WINNER

python -m py_compile \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19a_entry_universe_pit_lineage_tradability_and_data_contract.py

python -m pytest \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19a_entry_universe_pit_lineage_tradability_and_data_contract.py

python \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19a_entry_universe_pit_lineage_tradability_and_data_contract.py \
  --config experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19a_entry_universe_pit_lineage_tradability_and_data_contract.yaml

git diff --check
```

If `ruff` is available in the environment, also run:

```bash
python -m ruff check \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19a_entry_universe_pit_lineage_tradability_and_data_contract.py \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19a_entry_universe_pit_lineage_tradability_and_data_contract.py
```

## 22. Acceptance Checklist

19A is implementation-ready only if:

```text
[ ] The requirement exists at the declared path.
[ ] The config path, runner path, and test path are declared.
[ ] Upstream 18F closure is required and fail-closed.
[ ] Candidate row schema is fully specified.
[ ] Readout-only materialization is allowed only for denominator, density,
    path-completeness, censoring, sample-support, and effective-sample audits.
[ ] Decision-time and next-open entry convention are frozen.
[ ] Fill feasibility is frozen and auditable.
[ ] Forward labels are readout-only and censoring is frozen.
[ ] Cooldown and denominator levels are frozen.
[ ] Split, purge, embargo, and validation non-use are frozen.
[ ] TuShare DC concept-board source is the only board/theme source.
[ ] Pre-2025 TuShare DC backfill caveat is explicit.
[ ] Pre-2025 TuShare DC backfilled concept/theme buckets are forbidden as
    baseline matching keys.
[ ] AkShare board dumps are quarantined out of contract and cannot enter
    features, matching, or candidate families.
[ ] Genuine PIT industry features are unsupported unless a future source is
    introduced.
[ ] Baseline budget and matching quality gates are frozen.
[ ] Grid budget, family cap, and multiple-testing correction are frozen.
[ ] Metric, margin, and left-tail burden definitions are frozen.
[ ] Validation stress and replay eligibility rules are frozen.
[ ] Minimum sample support thresholds are frozen.
[ ] Required outputs, manifests, decision states, and validation commands are
    declared.
```
