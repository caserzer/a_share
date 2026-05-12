# EP4 Requirement 02 V2: Winner-Anchored Structure Profile Discovery + Action-Time Prior Calibration

## 1. Requirement Metadata

- Requirement id: `ep4_r02_winner_anchored_structure_profile_discovery_v2`
- Short name: `r02_winner_anchored_structure_profile_discovery_v2`
- Status: implementation-ready research requirement
- Owner workflow: EP4
- Previous requirement: `ep4/requirement_02_evidence_family_discovery_v1.md`
- Required output root: `ep4/outputs/r02_winner_anchored_structure_profile_discovery_v2/`
- Required config path: `ep4/configs/r02_winner_anchored_structure_profile_discovery_v2.yaml`
- Required runner path: `ep4/scripts/run_r02_winner_anchored_structure_profile_discovery.py`
- Required validator path: `ep4/scripts/validate_r02_winner_anchored_structure_profile_discovery.py`

## 2. Background And Motivation

R02 V1 already tested a direct action-time primitive search:

1. Build a PIT action-time stock-day panel.
2. Search primitives and approved two-primitive AND combinations on train only.
3. Freeze evidence families.
4. Evaluate them unchanged on validation and robustness.

The result was directionally useful but not sufficient for R03. V1 mostly rediscovered broad strength states such as relative strength, near-high, gap, and market breadth. These states raise the big-winner likelihood somewhat, but they are too dense, too generic, and not execution-sufficient. More importantly, the search still asks a hard question at the wrong end:

> "Can we find an action-time primitive today that predicts a 120-day winner later?"

The new hypothesis is different:

> Big winners may share recurring observable structures during their early post-reference lifecycle. Instead of searching the whole action-time denominator first, first discover structures that repeatedly appear inside known big winners from `t0` to `t0 + 30`, then convert only observable structures back into action-time candidates and estimate their true prior/posterior probabilities on the PIT denominator.

This requirement therefore replaces direct primitive-first search with a two-stage workflow:

1. Winner-anchored structure profile discovery.
2. Action-time prior calibration and validation.

## 3. Research Question

The workflow must answer three questions in order:

1. Among known train-split big winners, what observable structures recur during `reference_date + 0` through `reference_date + 30`?
2. Among those recurring structures, which are potentially informative rather than merely generic strength, liquidity, or market beta states?
3. When each structure is frozen and mapped back to action time, what are its prior probability, posterior big-winner probability, likelihood ratio, execution diagnostics, and validation/robustness stability?

The workflow must not answer question 3 using winner-window denominators. Winner-window coverage is only a discovery and profiling statistic. True prior and posterior estimates must come from the full PIT action-time stock-day denominator.

## 4. Non-Goals

This requirement is not an R03 entry strategy.

The workflow must not:

- Build a final trading model.
- Tune position sizing, stop policy, or portfolio construction.
- Use validation or robustness splits to discover structures.
- Select structures because they look good after validation.
- Treat `exists within future 30 days` as an action-time signal.
- Compare R02 generic diagnostic `unit_return_R` numerically against R01 V3 `return_R`.
- Fetch new AkShare or Tushare data.
- Replace R01 or R02 V1 artifacts in place.

## 5. Key Conceptual Boundary

The central leakage risk is confusing these two statements:

- Winner-window profile statement: "This structure exists somewhere between `t0` and `t0 + 30` among many known big winners."
- Action-time signal statement: "On this trade date, this structure is already observable and can be used without knowing the future."

Only the second statement may be evaluated as a candidate evidence family.

Every discovered structure must therefore have two definitions:

1. `profile_definition`: how it is observed inside the `t0` to `t0 + 30` winner window.
2. `action_time_definition`: the exact formula that fires on a PIT trade date using only data available as of that trade date.

If a profile cannot be converted into a valid `action_time_definition`, it must be reported as a descriptive winner profile only and must not enter action-time prior calibration.

## 6. Required Inputs

The workflow must use existing local artifacts and PIT data only.

Required inputs:

- PIT Qlib stock-day data already available in the project.
- Existing EP4/R01 big-winner label conventions and local outputs as reproducibility references.
- Existing industry, calendar, buyability, and cost helpers used by EP4/R01/R02 V1.
- R02 V1 action-time label conventions for big-winner and diagnostic execution labels.
- R02 V1 final report as background evidence, not as a source of selected structures.

No new online data fetch is allowed.

### 6.1 Canonical Big-Winner Reference Event Contract

The workflow must build a canonical big-winner reference event panel before Stage A.

Required artifact:

`cache/r02_v2_winner_reference_events.parquet`

Required grain:

`winner_event_id`

Required fields:

- `winner_event_id`
- `instrument_id`
- `reference_date`
- `reference_date_policy`
- `split`
- `winner_label_version`
- `winner_label_formula`
- `entry_anchor_policy`
- `forward_horizon_days`
- `forward_peak_return`
- `forward_peak_date`
- `raw_positive_event_start`
- `raw_positive_event_end`
- `raw_positive_event_count`
- `episode_id`
- `episode_dedup_gap_days`
- `is_first_event_in_episode`
- `aggressive_dedup_warning`
- `overlap_policy`
- `profile_window_start`
- `profile_window_end`
- `complete_profile_window_flag`
- `incomplete_profile_window_reason`
- `r01_v3_reference_overlap_flag`
- `source_price_hash`
- `source_calendar_hash`

Default reference event construction:

- Use the same `big_winner_forward` semantics as R02 V1: `forward_close_peak_h120 / entry_price_t - 1 >= 0.50`.
- Build an R02 V2-owned PIT action-time label panel from raw local PIT inputs. The primary reference event pipeline must not depend on V1 `r02_action_time_panel.parquet`.
- Build the reference event pool from R02 V2-owned action-time rows whose retrospective `big_winner_forward` label is positive and complete.
- Default `reference_date_policy = first_positive_big_winner_forward_episode`.
- Under the default policy, group consecutive or near-consecutive positive action-time rows for the same instrument into one episode, then set `reference_date` to the first positive `event_t` in that episode.
- All features used at `reference_date` must remain PIT, but membership in the reference pool is allowed to be retrospective because Stage A is explicitly winner-anchored profiling.
- Deduplicate repeated reference dates for the same instrument into one episode when the next reference is within `episode_dedup_gap_days = 20` trading days of the prior reference.
- Keep only `is_first_event_in_episode = true` for Stage A discovery.
- Assign split by `reference_date`, not by `forward_peak_date`.
- Exclude reference events from Stage A discovery if their `0..30` profile window crosses the train split effective profile boundary.
- If an instrument has multiple raw positive event groups but only one final reference event after deduplication, mark `aggressive_dedup_warning = true`.

Allowed `reference_date_policy` enum:

- `first_positive_big_winner_forward_episode`

The implementation may report sensitivity-only alternatives such as `last_positive_before_forward_peak` or `r01_seed_aligned_reference`, but those alternatives must not affect Stage A discovery, representative selection, validation, robustness, or final decision.

The reference event audit must reconcile:

- raw positive action-time rows;
- positive rows after complete-window filtering;
- episode groups before first-event selection;
- final `winner_event_id` rows used by Stage A;
- rows removed because the profile window was incomplete;
- rows removed by split-boundary constraints.

The workflow must also reconcile the R02 V2-owned reference events against the R01 V3 canonical big-winner reference when that artifact is available.

Required reconciliation metrics:

- `r01_v3_reference_artifact_path`
- `r01_v3_reference_artifact_hash`
- `r02_v2_reference_event_count`
- `r01_v3_reference_event_count`
- `instrument_overlap_rate`
- `instrument_year_overlap_rate`
- `same_reference_date_rate`
- `within_20d_reference_date_rate`
- `overlap_status`

If `instrument_overlap_rate < 0.80`, the workflow must set `overlap_status = reference_drift_warning`, block `go_to_r03_evidence_accumulation`, and require the final report to explain the drift. If the R01 V3 canonical reference artifact is unavailable, the run may continue only with `overlap_status = r01_v3_reference_missing` and the final decision cannot be `go_to_r03_evidence_accumulation`.

The implementation may use an upstream reference panel for audit comparison only. It must rebuild the primary canonical R02 V2 reference panel from PIT data and record both the upstream artifact hash and the rebuilt artifact hash.

## 7. Splits

The workflow must preserve EP4 split conventions:

- Train split: discovery, scoring, clustering, and freezing only.
- Validation split: unchanged evaluation only.
- Robustness split: unchanged evaluation only.

All label effective windows must be split-bounded. If a forward label horizon extends beyond a split boundary, that row must be marked incomplete for that label and excluded from label-specific metrics. The row must not be silently dropped from the denominator.

## 8. Stage A: Winner-Anchored Structure Profile Discovery

### 8.1 Stage A Denominator

Stage A uses only train-split big-winner reference events.

The Stage A discovery denominator is:

`r02_v2_winner_reference_events where split = train and is_first_event_in_episode = true and complete_profile_window_flag = true`

Each event must have:

- `winner_event_id`
- `instrument_id`
- `reference_date`
- `split`
- `winner_label_version`
- `complete_profile_window_flag`
- `profile_window_start = reference_date`
- `profile_window_end = reference_date + 30 trading days`

Events without a complete `0..30` trading-day profile window must be retained in the audit but excluded from structure discovery metrics.

### 8.2 Winner Profile Panel

Build `r02_v2_winner_window_panel.parquet` at event-date grain:

- `winner_event_id`
- `instrument_id`
- `reference_date`
- `profile_trade_date`
- `offset_day`
- OHLCV and money fields
- market and industry context fields
- pre-reference lookback features available as of each `profile_trade_date`
- post-reference profile-only annotations

Allowed offset range:

- `offset_day in [0, 30]`

Required stage buckets:

- `early_window`: `offset_day in [0, 5]`
- `build_window`: `offset_day in [6, 15]`
- `continuation_window`: `offset_day in [16, 30]`
- `full_window`: `offset_day in [0, 30]`

### 8.3 Structure Candidate Families

The config must define candidate structure groups. At minimum:

- `momentum_persistence`
- `near_high_persistence`
- `volume_money_confirmation`
- `relative_strength_confirmation`
- `pullback_hold_and_recovery`
- `volatility_contraction_expansion`
- `distribution_absence`
- `industry_market_support`
- `acceleration_and_gap`
- `failure_absorption`

Each structure candidate must include:

- `structure_candidate_id`
- `group`
- `pattern_type`
- `profile_definition`
- `action_time_definition`
- `required_lookback_days`
- `profile_window_bucket`
- `observable_trigger_rule`
- `trigger_date_policy`
- `max_lag_days`
- `dedup_gap_days`
- `first_trigger_only_flag`
- `raw_feature_list`
- `shared_feature_family`
- `background_control_policy`
- `formula_hash`

### 8.4 Candidate Dictionary And Pattern Template Grid

The search space must be fully declared in config before running Stage A.

Required config sections:

- `structure_candidate_dictionary`
- `feature_atoms`
- `pattern_template_grid`
- `threshold_grid`
- `lookback_grid`
- `profile_window_grid`
- `sequence_lag_grid`
- `dedup_policy_grid`
- `structure_candidate_id_generation`

Every generated candidate must be derived mechanically from these config sections. The implementation must not create ad hoc candidates from intermediate results, validation results, robustness results, or manual inspection.

Candidate count limits:

- `max_total_candidates_per_group = 200`
- `max_total_candidates = 2000`

If the configured grid expands beyond either limit, the workflow must fail closed before Stage A metrics are computed. The implementation must not sample, truncate, or silently drop candidates to satisfy the limit.

Required candidate dictionary fields:

- `structure_candidate_id`
- `candidate_generation_version`
- `group`
- `pattern_type`
- `feature_atom_ids`
- `threshold_ids`
- `lookback_days`
- `profile_window_bucket`
- `sequence_lag_days`
- `dedup_gap_days`
- `profile_definition`
- `action_time_definition`
- `trigger_date_policy`
- `background_control_policy`
- `formula_hash`
- `config_row_hash`

Every `pattern_template_grid` row must declare `pattern_type` using one of the allowed pattern type enum values in §8.5.

Default `structure_candidate_id` generation:

`r02v2_{group}_{pattern_type}_{feature_atom_hash}_{threshold_hash}_{window_hash}_{lag_hash}_{dedup_hash}`

The generated value is stored as `structure_candidate_id` in every artifact. The name `candidate_id` is not allowed in R02 V2 artifacts except when reading external R02 V1 baseline artifacts.

The implementation must write `reports/r02_v2_candidate_dictionary.csv` before Stage A metrics are computed. The validator must fail if any `structure_candidate_id` appears in later artifacts but is missing from this dictionary.

### 8.5 Allowed Profile Pattern Types

The workflow may discover these profile pattern types:

- Point-in-window existence: a condition appears at least once in a profile bucket.
- Persistence: a condition appears at least `k` days in a profile bucket.
- Ordered sequence: condition A occurs before condition B within a maximum lag.
- Recovery structure: pullback or failure state followed by recovery above a defined level.
- Absence structure: no high-volume breakdown, no close below key moving average, or no failed seed state over a lookback window.
- Contraction-expansion structure: volatility or turnover compression followed by expansion.
- Support structure: industry or market confirmation around the trigger date.

For action-time use, every pattern must fire on the first date at which the full pattern has become observable. The implementation must not use knowledge that a future condition will happen later in the same `0..30` profile window.

### 8.6 Action-Time Eventization Contract

Every observable profile candidate must be converted into an action-time event rule before Stage B.

Required eventization fields:

- `structure_candidate_id`
- `signal_event_id`
- `instrument_id`
- `trigger_trade_date`
- `pattern_start_date`
- `pattern_complete_date`
- `max_lag_days`
- `dedup_gap_days`
- `trigger_offset_from_reference` when evaluated inside winner windows
- `first_trigger_in_profile_window_flag`
- `cooldown_active_flag`
- `lookback_start_date`
- `lookback_end_date`
- `future_data_used_flag`
- `eventization_rejection_reason`

Default eventization rules:

- A candidate may fire only on `pattern_complete_date`.
- `trigger_trade_date = pattern_complete_date`.
- `pattern_complete_date` must be less than or equal to the current PIT trade date when the signal fires.
- If the same instrument fires the same candidate multiple times within `dedup_gap_days = 20`, keep the first event and mark later events as deduplicated.
- For winner-window coverage, report both first-trigger coverage and any-trigger coverage, but Stage B calibration must use the same deduplicated action-time trigger policy used outside winner windows.
- If a pattern cannot define `pattern_complete_date` without future data, it is non-observable and must be excluded from Stage B.

### 8.7 Stage A Background Information Screen

Stage A must not rank candidates by winner coverage alone.

For each candidate, build a train-only background comparison using one of these configured control policies:

- `matched_non_winner_window`: match non-winner instruments by year, industry, liquidity bucket, and market-cap bucket, then evaluate the same `0..30` pseudo-reference window.
- `action_time_background`: evaluate the observable action-time formula on all eligible train action-time rows.
- `both`: compute both comparisons and use the stricter information score.

Default `background_control_policy = both`.

If the config uses any policy other than `both`, it must record `non_default_background_policy_reason`, and the validator must require the matching conditional gates below. The default research run must use `both`.

Matched non-winner windows must be built from train-split R02 V2-owned action-time rows with:

- complete `big_winner_forward` label window;
- `big_winner_forward = false`;
- complete `0..30` pseudo-profile window;
- no overlap with any canonical big-winner reference episode for the same instrument within `episode_dedup_gap_days`;
- deterministic matching keys and replacement policy recorded in the manifest.

Default pseudo-reference generation:

- For every train winner reference event, set `pseudo_reference_date = winner.reference_date`.
- Search non-winner instruments that are eligible on the same `pseudo_reference_date`.
- Match by same calendar year, same industry when available, liquidity bucket, market-cap bucket, and `executable_entry_available`.
- If exact same-industry matches are insufficient, the row must record `industry_match_relaxed = true`; relaxed rows are audit-visible and cannot be hidden by replacement.
- The implementation must not substitute a different pseudo-reference date to increase match capacity.
- If the same-date matched pool is insufficient, record `matched_background_capacity_shortfall = true`; do not fill by random date or future date.
- Default `matched_controls_per_winner_event = 5`.

Required matched background fields:

- `matched_background_event_id`
- `matched_to_winner_event_id`
- `instrument_id`
- `pseudo_reference_date`
- `match_year`
- `match_industry`
- `match_liquidity_bucket`
- `match_mcap_bucket`
- `match_executable_entry_available`
- `match_rank`
- `industry_match_relaxed`
- `matched_background_capacity_shortfall`

Required background metrics:

- `matched_background_event_count`
- `matched_background_coverage`
- `matched_background_coverage_ci90_upper`
- `action_time_background_signal_rate`
- `winner_vs_background_coverage_lift`
- `winner_vs_background_coverage_lift_ci90_lower`
- `generic_strength_proxy_flag`
- `generic_strength_proxy_reason`
- `background_control_policy`
- `non_default_background_policy_reason`

A high `winner_coverage` candidate with no enrichment versus background must be treated as a descriptive winner profile, not a candidate evidence family.

### 8.8 Stage A Metrics

For every structure candidate, compute at least:

- `train_winner_event_count`
- `complete_profile_event_count`
- `winner_coverage`
- `winner_coverage_ci90_lower`
- `winner_coverage_by_year`
- `min_year_coverage`
- `median_first_trigger_offset`
- `p25_first_trigger_offset`
- `p75_first_trigger_offset`
- `triggered_event_count`
- `trigger_days_per_event_mean`
- `trigger_days_per_event_p90`
- `stage_bucket_distribution`
- `group`
- `observable_action_time_flag`
- `non_observable_reason`
- `matched_background_coverage`
- `action_time_background_signal_rate`
- `winner_vs_background_coverage_lift`
- `winner_vs_background_coverage_lift_ci90_lower`
- `generic_strength_proxy_flag`

### 8.9 Stage A Early Rejection

A structure candidate must be rejected before action-time calibration if any of the following hold:

- It is not train-only discovered.
- It cannot be expressed as an observable `action_time_definition`.
- `winner_coverage` is below the configured minimum.
- `winner_coverage_ci90_lower` is below the configured minimum.
- It fires on too many days per winner event and is therefore not structurally selective.
- It is present in too few train years.
- Its definition uses future information relative to its declared action-time trigger date.
- It is a duplicate of a simpler candidate under the configured redundancy thresholds.
- It has no measurable enrichment versus the configured train-only background control.
- It is flagged as a generic broad-strength proxy and has no incremental information score.
- It is missing from `reports/r02_v2_candidate_dictionary.csv`.

The default config should use conservative but not final-entry-level thresholds:

- `min_winner_coverage = 0.30`
- `min_winner_coverage_ci90_lower = 0.20`
- `min_years_present = 3`
- `max_trigger_days_per_event_p90 = 12`
- `default_background_control_policy = both`
- `min_winner_vs_background_coverage_lift = 1.20`
- `min_winner_vs_background_coverage_lift_ci90_lower = 1.00`
- `max_action_time_background_signal_rate = 0.12`
- `max_stage_a_candidates_to_calibrate = 60`

Conditional background gates:

- If `background_control_policy = both`, the candidate must satisfy both matched-window enrichment and action-time background density gates.
- If `background_control_policy = matched_non_winner_window`, the candidate must satisfy matched-window enrichment gates and the report must mark action-time density as not computed for Stage A; Stage B density gates still apply.
- If `background_control_policy = action_time_background`, the candidate must satisfy action-time background density gates and the report must mark matched-window enrichment as not computed.
- Any non-default policy must be visible in the final report and validator output.

These thresholds are discovery gates only. They do not imply tradability.

## 9. Stage B: Action-Time Prior Calibration

### 9.1 Stage B Denominator

Stage B must evaluate frozen Stage A candidates on the PIT action-time stock-day denominator.

Stage B must build an R02 V2-owned action-time denominator from raw local PIT inputs. It may reuse R02 V1 label, effective-window, entry-availability, and split-boundary conventions, but it must not reuse V1 action-time panel cache as authority.

- Preserve stock-days with unavailable T+1 entry.
- Mark `executable_entry_available`.
- Mark label-specific incomplete forward windows instead of dropping rows globally.
- Anchor labels on `event_t` and `next_open_after(signal_date)`.

### 9.2 Required Labels

Compute or reuse fixed labels:

- `big_winner_forward`
- `continuation_h20`
- `continuation_h60`
- `failed_seed_forward`
- `executable_entry_available`

Labels must be deterministic and reproducible from PIT inputs.

### 9.3 Required Prior And Posterior Metrics

For each frozen candidate and each split, compute:

- `action_time_denominator_n`
- `effective_label_n`
- `signal_n`
- `signal_rate = P(signal)`
- `winner_base_rate = P(big_winner_forward)`
- `winner_given_signal = P(big_winner_forward | signal)`
- `signal_given_winner = P(signal | big_winner_forward)`
- `signal_given_non_winner = P(signal | not big_winner_forward)`
- `primary_LR = P(signal | winner) / P(signal | non_winner)`
- `primary_LR_ci90_lower`
- `precision_lift = winner_given_signal / winner_base_rate`
- `failed_seed_rate_given_signal`
- `continuation_h20_rate_given_signal`
- `continuation_h60_rate_given_signal`
- `executable_entry_available_rate`
- `buyable_signal_n`

The report must explicitly state that `P(signal | winner)` from Stage B is not the same as Stage A `winner_coverage`. Stage A coverage is measured inside a post-reference winner window; Stage B probability is measured at action-time stock-day grain.

### 9.4 Required Prior Decomposition

The prior estimate must be decomposed, not only reported as a global split-level value.

For each frozen candidate, compute Stage B prior and posterior metrics by:

- split
- calendar year
- industry
- market breadth bucket
- liquidity bucket
- market-cap bucket when available

Bucket freeze contract:

- `market_breadth_bucket` must use the configured train-frozen market breadth series. Default boundaries are `[-inf, 0.20)`, `[0.20, 0.40)`, `[0.40, 0.60)`, `[0.60, 0.80)`, `[0.80, inf]`, where the value is the eligible-universe share above its configured moving average.
- `liquidity_bucket` must use train-split global quintile boundaries of `money_20d_median` over eligible action-time rows.
- `market_cap_bucket` must use train-split global quintile boundaries of available float or total market cap over eligible action-time rows.
- Bucket boundaries are computed on train split only, written to `reports/r02_v2_bucket_boundaries.csv`, and then reused unchanged for validation and robustness.
- Missing market-cap rows must be assigned to `market_cap_bucket = missing_mcap`, reported separately, and excluded from market-cap concentration gates unless the missing share exceeds `max_missing_mcap_share = 0.20`.
- `reports/r02_v2_bucket_boundaries.csv` must include `missing_mcap_share` by split and `missing_mcap_status`.

Required decomposition fields:

- `bucket_type`
- `bucket_id`
- `action_time_denominator_n`
- `signal_n`
- `signal_rate`
- `winner_base_rate`
- `winner_given_signal`
- `primary_LR`
- `primary_LR_ci90_lower`
- `posterior_stability_flag`

The final report must call out candidates whose global lift is driven by one year, one industry, or one market regime.

### 9.5 Diagnostic Execution

The workflow must reuse the R02 generic diagnostic execution logic:

- Generic stop candidates:
  - `signal_day_low`
  - `prior_10d_low`
  - `prior_20d_low`
- Risk bounds:
  - minimum initial risk: `2%`
  - maximum initial risk: `12%`
- Fail-fast horizon: `H10`
- Terminal horizon: `H20`
- `unit_return_R = after_cost_return_pct / initial_risk_pct`

This diagnostic R is not the R01 V3 `return_R`.

### 9.6 Stage B Train Early Rejection

Before clustering and representative selection, calibrated candidates must pass train-only action-time gates.

Default train gates:

- `min_train_signal_n = 200`
- `min_train_buyable_signal_n = 100`
- `max_train_signal_rate = 0.08`
- `min_train_primary_LR = 1.10`
- `min_train_primary_LR_ci90_lower = 0.95`
- `min_train_precision_lift = 1.10`
- `min_train_EV_R = -0.10`
- `max_train_failed_seed_rate_given_signal = 0.60`
- `min_prior_decomposition_bucket_count = 3`
- `max_single_year_signal_share = 0.45`
- `max_single_industry_signal_share = 0.35`

A candidate that fails Stage B train gates may still be reported as a descriptive profile but must not enter Stage C representative selection.

The train gates are intentionally wider than validation and robustness gates. R02 V2 is a discovery funnel: train gates preserve plausible candidates for out-of-sample evaluation, while validation and robustness gates are stricter to control train overfit.

## 10. Stage C: Redundancy, Clustering, And Representative Selection

Stage C operates on train split only.

Candidate redundancy must be assessed using:

- Same-day overlap.
- Within-5-trading-day overlap.
- Signal correlation.
- Jaccard overlap.
- Conditional overlap among winners.
- Conditional overlap among non-winners.
- Shared raw feature family penalty.
- Incremental likelihood ratio versus existing representatives.
- Incremental diagnostic `EV_R` versus existing representatives.

Default redundancy merge thresholds:

- Merge if `same_day_jaccard >= 0.70`.
- Merge if `within_5d_jaccard >= 0.80`.
- Merge if `signal_correlation >= 0.85`.
- Merge if `conditional_winner_overlap >= 0.80`.
- Merge if `conditional_non_winner_overlap >= 0.80`.
- Apply `shared_raw_feature_penalty = 0.10` to ranking score when candidates share the same raw feature family.
- A candidate may become a new representative only if `incremental_primary_LR >= 0.03` or `incremental_EV_R >= 0.03` versus already selected representatives in the same cluster.

The workflow must freeze representative profile families from train only.

Default representative constraints:

- Minimum representatives required to proceed to validation: `3`.
- Maximum representatives to freeze: `8`.
- At least `3` distinct structure groups unless fewer than `3` pass Stage B train gates.
- No more than `2` representatives from the same structure group unless explicitly justified in the audit.

## 11. Validation And Robustness Evaluation

Validation and robustness must use frozen representatives unchanged.

The implementation must record:

- frozen config hash
- frozen candidate list hash
- validation no-retuning flag
- robustness no-retuning flag
- candidate formula hash per representative

No thresholds, formulas, groups, clustering assignments, or selected representatives may be modified after looking at validation or robustness metrics.

If a frozen representative passes validation but fails robustness with `robustness primary_LR < 1.00` or `robustness EV_R < -0.05`, it must be removed from the R03 family pool and retained as audit-only in `reports/r02_v2_representative_selection.csv`.

## 12. Mandatory Baselines

The workflow must include these baselines:

1. Full PIT action-time denominator with no signal.
2. Mandatory R01 V3 post30 profile seed baseline as a comparison-only composite with frozen formula hash.
3. Frozen broad-strength reference primitive from R02 V1, selected deterministically by the V1 train ranking artifact when available.

Baselines must be reported separately and must not count as normal discovered profile families.

For the no-signal baseline, diagnostic `EV_R` is the unconditional mean diagnostic execution result across all executable PIT action-time rows with complete H20 diagnostic windows. It is not a random sample. Any random-sample baseline must be reported as optional and separately named.

The broad-strength reference primitive must be resolved as follows:

- Read the R02 V1 primitive summary artifact if available.
- Filter to single primitives in broad-strength groups: `momentum`, `relative_strength`, `near_high`, `market_breadth`, or their configured V1 aliases.
- Sort by train primary score, then train `primary_LR`, then lower signal density, then `candidate_id`.
- Freeze the first row as `r02_v1_broad_strength_reference_baseline`.
- Record source artifact path, source artifact hash, selected candidate id, selected formula, and selected formula hash.

If the V1 artifact is missing, the baseline must be marked `missing_with_reason` and the validator must allow the run only if the final report explicitly states the missing baseline.

## 13. Final Decision Gates

Allowed final decision enum:

- `go_to_r03_evidence_accumulation`
- `revise_profile_search_space`
- `archive_profile_discovery_no_r03`

The workflow may set `go_to_r03_evidence_accumulation` only if all conditions hold:

- At least `3` non-baseline frozen representative profile families.
- At least `2` distinct structure groups among frozen representatives.
- R01 V3 reference reconciliation `instrument_overlap_rate >= 0.80`.
- Validation `primary_LR_ci90_lower >= 1.00` for at least `2` representatives.
- Robustness `primary_LR >= 1.00` for at least `2` representatives.
- Validation diagnostic `EV_R >= -0.05` for at least `2` representatives.
- Robustness diagnostic `EV_R >= -0.05` for at least `2` representatives.
- No major validator leakage finding.
- No validation/robustness retuning.
- Report clearly separates Stage A winner coverage from Stage B action-time prior.

The workflow must set `revise_profile_search_space` if:

- Stage A finds recurring winner structures, but Stage B action-time prior calibration is weak or too dense.
- Fewer than `3` representative families pass validation/robustness gates, but at least one family has stable positive likelihood evidence.

The workflow must set `archive_profile_discovery_no_r03` if:

- Stage A fails to find recurring observable structures, or
- Stage B shows no stable action-time lift, or
- The discovered structures are only generic broad-strength proxies with no incremental value.

## 14. Required Artifacts

All artifacts must be written under:

`ep4/outputs/r02_winner_anchored_structure_profile_discovery_v2/`

### 14.1 Cache Artifacts

- `cache/r02_v2_winner_reference_events.parquet`
- `cache/r02_v2_reference_action_time_label_panel.parquet`
- `cache/r02_v2_winner_window_panel.parquet`
- `cache/r02_v2_profile_candidate_event_panel.parquet`
- `cache/r02_v2_matched_background_windows.parquet`
- `cache/r02_v2_action_time_eventized_signals.parquet`
- `cache/r02_v2_action_time_panel.parquet`
- `cache/r02_v2_action_time_signal_panel.parquet`
- `cache/r02_v2_frozen_representatives.parquet`

Large cache files must be ignored by git.

### 14.2 Report Artifacts

- `reports/r02_v2_winner_profile_search_summary.csv`
- `reports/r02_v2_winner_reference_event_audit.csv`
- `reports/r02_v2_r01_v3_reference_reconciliation.csv`
- `reports/r02_v2_candidate_dictionary.csv`
- `reports/r02_v2_bucket_boundaries.csv`
- `reports/r02_v2_stage_a_rejection_audit.csv`
- `reports/r02_v2_profile_observability_audit.csv`
- `reports/r02_v2_eventization_audit.csv`
- `reports/r02_v2_background_information_screen.csv`
- `reports/r02_v2_profile_redundancy_matrix.csv`
- `reports/r02_v2_stage_b_prior_calibration.csv`
- `reports/r02_v2_prior_decomposition.csv`
- `reports/r02_v2_stage_b_train_gate_audit.csv`
- `reports/r02_v2_representative_selection.csv`
- `reports/r02_v2_validation_summary.csv`
- `reports/r02_v2_robustness_summary.csv`
- `reports/r02_v2_execution_diagnostics.csv`
- `reports/r02_v2_year_stability.csv`
- `reports/r02_v2_label_confusion_matrix.csv`
- `reports/r02_v2_mandatory_baselines.csv`
- `reports/r02_v2_gate_audit.csv`
- `reports/r02_v2_final_report.md`

### 14.3 Manifest Artifacts

- `manifest/r02_v2_manifest.json`
- `manifest/r02_v2_input_hashes.json`
- `manifest/r02_v2_config_hash.json`
- `manifest/r02_v2_validation_contract.json`

## 15. Final Report Requirements

The final report must be written in Chinese and include:

- Executive conclusion and final decision.
- Why R02 V1 was insufficient.
- Canonical big-winner reference event construction and audit.
- R01 V3 reference reconciliation and overlap status.
- Fixed `reference_date_policy` and raw-positive-to-final-reference reconciliation.
- Candidate dictionary and configured pattern template grid summary.
- Candidate count limit audit.
- Stage A winner-window structure discovery results.
- Top recurring structures by winner coverage.
- Stage A background information screen and generic-strength rejection summary.
- Structures rejected because they were not action-time observable.
- Structures rejected because they were too generic or too dense.
- Stage B action-time prior calibration table.
- Train-frozen bucket boundary table.
- Stage B prior decomposition by year, industry, market breadth, liquidity, and market-cap buckets.
- Clear explanation of prior, posterior, and likelihood ratio.
- Validation and robustness summary.
- Mandatory baseline comparison.
- Execution feasibility diagnostics.
- Initial interpretation, findings, and hypotheses for the next iteration.

The report must explicitly warn when a result is only a guess or hypothesis rather than validated evidence.

## 16. Validator Requirements

The validator must fail closed.

It must check:

- All required artifacts exist.
- Canonical `r02_v2_winner_reference_events.parquet` exists and has reproducible event ids.
- Primary reference event pipeline is rebuilt from R02 V2-owned PIT inputs and does not depend on V1 action-time panel cache.
- `reference_date_policy` equals `first_positive_big_winner_forward_episode` for the primary run.
- Reference event audit reconciles raw positive action-time rows to final Stage A reference rows.
- R01 V3 reference reconciliation exists; `go_to_r03_evidence_accumulation` is blocked when overlap is below `0.80` or the R01 V3 reference artifact is missing.
- `reports/r02_v2_candidate_dictionary.csv` exists and covers every `structure_candidate_id` in downstream artifacts.
- Downstream R02 V2 artifacts use `structure_candidate_id`; `candidate_id` is forbidden except for external R02 V1 baseline ingestion.
- Candidate dictionary size is at or below `max_total_candidates_per_group` and `max_total_candidates`.
- `structure_candidate_id` values are generated deterministically from config-defined feature atoms, thresholds, windows, lags, and dedup policy.
- Every candidate template declares a valid §8.5 `pattern_type`.
- Stage A discovery uses train split only.
- Stage A denominator uses only first complete train reference events.
- Validation and robustness are not used for discovery, filtering, clustering, or threshold tuning.
- Every calibrated candidate has an observable `action_time_definition`.
- Every action-time formula uses only data available as of trigger date.
- Every calibrated candidate has a valid eventization audit with `future_data_used_flag = false`.
- Winner-window first-trigger coverage and action-time trigger policy use the same dedup gap.
- Stage A background comparison exists and uses train-only controls.
- Matched non-winner pseudo-reference dates equal the matched winner `reference_date`; no random or shifted pseudo-reference dates are used.
- Matched background artifacts contain `industry_match_relaxed` and `matched_background_capacity_shortfall`, and the final report summarizes relaxed-industry share and capacity-shortfall share.
- Default Stage A background policy is `both`; non-default background policy has a recorded reason and satisfies the matching conditional gates.
- Candidates without winner-versus-background enrichment do not enter Stage B calibration.
- Stage A `winner_coverage` is not used as Stage B prior probability.
- Stage B denominator is rebuilt from R02 V2-owned PIT inputs, includes PIT stock-days, preserves entry-unavailable rows, and does not treat V1 panel cache as authority.
- Stage B train gate audit exists and blocks failed candidates from Stage C.
- Stage C redundancy merge thresholds are present in the config and applied in representative selection.
- Robustness-failed representatives are removed from the R03 family pool and retained audit-only.
- Prior decomposition exists for year, industry, market breadth, liquidity, and market-cap buckets.
- Bucket boundaries are computed on train only and reused unchanged for validation and robustness.
- `missing_mcap_share` is reported by split and does not exceed `max_missing_mcap_share = 0.20` unless market-cap concentration gates are marked invalid.
- Effective label windows are split-bounded.
- Incomplete forward windows are excluded from label-specific metrics.
- `executable_entry_available` handles unavailable T+1 entry without dropping rows.
- Mandatory baselines are present and excluded from normal representative counts.
- No-signal baseline diagnostic `EV_R` is computed as the unconditional executable-denominator mean, not as a random-sample baseline.
- Representative selection is reproducible with `effective_n_jobs=1`.
- Bootstrap confidence intervals are present for primary LR.
- Final decision enum is valid.
- Final report contains the required Chinese sections.

## 17. Determinism Requirements

The workflow must be deterministic.

Required deterministic checks:

- Re-run representative selection with `effective_n_jobs=1`.
- Compare selected representative ids against the configured parallel run.
- Compare top Stage A candidate ids.
- Compare top Stage A background-enriched candidate ids.
- Compare top Stage B calibrated candidate ids.
- Compare final decision.
- Compare frozen formula hashes.
- Record all hashes in the manifest.

## 18. Implementation Notes

The implementation should reuse existing EP4 helpers where possible:

- PIT provider loading.
- Trading calendar handling.
- Split conventions.
- Label effective-window handling.
- Buyability and entry availability handling.
- Cost model.
- Deterministic writes.
- Hash and manifest helpers.

R02 V2-specific code should stay separate from R02 V1-specific primitive search and combo search logic. V2 may reuse shared helpers but should not mutate V1 outputs.

## 19. Expected Interpretation Pattern

This workflow is expected to produce one of three possible research outcomes:

1. Strong outcome: recurring winner structures remain informative when mapped back to action time. This supports R03 evidence accumulation.
2. Mixed outcome: recurring winner structures exist but are too common in the full denominator. This means the profiles describe winners but do not isolate tradable priors.
3. Negative outcome: even winner-anchored structures are mostly generic strength states. This means the next research direction should move away from structure discovery and toward lifecycle/risk-state modeling.

The workflow must not overstate outcome 2 as a trading edge.

## 20. Success Definition

The requirement is successfully implemented when:

- The default config runs end to end.
- The validator passes.
- All required cache, report, and manifest artifacts exist.
- The final report provides enough data to distinguish:
  - high winner-window coverage,
  - high winner-versus-background enrichment,
  - high action-time posterior probability,
  - high likelihood ratio,
  - execution feasibility,
  - validation stability.
- The final decision is produced by the configured gates, not by manual interpretation.
