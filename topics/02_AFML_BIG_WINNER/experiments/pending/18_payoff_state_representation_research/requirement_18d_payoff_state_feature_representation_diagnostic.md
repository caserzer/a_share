# Requirement: 18D Payoff-state Feature Representation Diagnostic

## 0. Non-negotiable Scope

18D is a diagnostic-only phase after 18C failed closed:

```text
decision_state = 18C_payoff_state_signal_weak_or_nonmonotone
next_allowed_requirement = none
all_hard_gates_pass = false
rank_ic_support_gate = fail
baseline_improvement_gate = fail
monotonicity_support_gate = pass
bucket_lift_gate = pass
bootstrap_ci_gate = pass
risk_only_gate = pass
```

18C showed that the current 18B F1-F5 feature set has weak positive payoff
ranking information, but it is not strong enough for an oracle-gap bridge:

```text
robustness_payoff_rank_ic = 0.064398
rank_ic_materiality_floor = 0.080000
robustness_decile_payoff_monotonicity_spearman = 0.612121
robustness_cluster_bootstrap_rank_ic_ci_low = 0.020608
rank_ic_vs_volatility20d_delta = -0.000374
baseline_improvement_required_delta = +0.005000
```

18D answers one question:

```text
Which PIT-valid, t0-available feature representation gaps explain why the
current F1-F5 state cannot robustly rank broad h20 payoff state, and which
candidate feature families should be prioritized for a refreshed feature matrix?
```

18D must not:

```text
train a final payoff separability model
select features by robustness or validation target correlation
start an oracle-gap bridge
define entry policy
define exit policy
define holding policy
define position sizing
construct a portfolio
run a portfolio backtest
deploy a model
emit a production signal
authorize live trading
weaken 18C materiality gates
switch binary metrics into the primary target
drop neutral rows
use delayed t0+k observed-state features in a primary candidate family
```

18D may:

```text
read 18A/18B/18C artifacts and manifests
replay 18C diagnostic model evidence
diagnose capacity-vs-representation using existing 18C model readouts
audit candidate feature family lineage and PIT/t0 availability
compute train-only candidate priors
compute predeclared robustness readouts for diagnostic evidence only
run orthogonality tests versus current volatility and participation proxies
prioritize feature families for a refreshed 18B/18C cycle
```

The only positive 18D decision is:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
```

All blocked decisions must emit:

```text
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18D
run_id = 18D_payoff_state_feature_representation_diagnostic
requirement_file = requirement_18d_payoff_state_feature_representation_diagnostic.md
config_file = configs/config_18d_payoff_state_feature_representation_diagnostic.yaml
runner_file = src/run_18d_payoff_state_feature_representation_diagnostic.py
test_file = tests/test_18d_payoff_state_feature_representation_diagnostic.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

Path aliases:

```text
TOPIC_ROOT = topics/02_AFML_BIG_WINNER
EP18_ROOT = experiments/pending/18_payoff_state_representation_research
```

All paths must be repo-relative or resolver-alias based. Do not hard-code
author-machine absolute paths. Paths beginning with `experiments/...` are
relative to `TOPIC_ROOT`. Paths beginning with `outputs/...` in this requirement
are local aliases relative to `EP18_ROOT`.

### 1.1 Required 18D config contract

`configs/config_18d_payoff_state_feature_representation_diagnostic.yaml` must
make all source discovery explicit. The runner must not discover candidate
sources by walking arbitrary directories.

Required config keys:

```yaml
paths:
  research_plan: experiments/pending/18_payoff_state_representation_research/research_plan.md
  requirement_18d: experiments/pending/18_payoff_state_representation_research/requirement_18d_payoff_state_feature_representation_diagnostic.md
  eighteen_b_matrix: experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
  eighteen_c_score_panel: experiments/pending/18_payoff_state_representation_research/outputs/local_cache/18C_payoff_state_separability_diagnostic/payoff_state_score_panel.parquet
  eighteen_c_decision: experiments/pending/18_payoff_state_representation_research/outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
  eighteen_c_manifest: experiments/pending/18_payoff_state_representation_research/outputs/manifests/18C_payoff_state_separability_diagnostic_manifest.json
  sixteen_b_label_step_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
  sixteen_b_materialized_step_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/materialized_step_panel.parquet
  sixteen_b_label_panel_readout: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
  sixteen_a_episode_interval_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16A_sequential_sampling_geometry_preflight/episode_interval_panel.parquet
  sixteen_a_step_geometry_panel: experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/local_cache/16A_sequential_sampling_geometry_preflight/step_geometry_panel.parquet
  stock_daily_qfq_dir: data/raw/akshare/day/qfq
  ep02_anchor_aligned_daily_panel: experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/large_raw/anchor_aligned_daily_panel.parquet
  ep02_episode_aligned_daily_panel: experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/local_cache/episode_aligned_daily_panel.parquet

source_aliases:
  ep18_matrix_row_keys: [eighteen_b_matrix]
  ep18_current_feature_matrix: [eighteen_b_matrix]
  pit_price_path_panel: [stock_daily_qfq_dir]
  pit_money_flow_proxy_panel: [stock_daily_qfq_dir]
  episode_geometry_panel: [sixteen_b_label_step_panel, sixteen_b_materialized_step_panel, sixteen_a_episode_interval_panel, stock_daily_qfq_dir]
  pre_t0_supply_zone_panel: [stock_daily_qfq_dir, ep02_anchor_aligned_daily_panel]
  market_or_regime_context_panel: [ep02_anchor_aligned_daily_panel, ep02_episode_aligned_daily_panel]

entropy_params:
  window_ids: [episode_low_to_t0, trailing_20, trailing_60]
  return_state_flat_abs_return_max: 0.001
  close_location_bins: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  log_base: e
  probability_epsilon: 1.0e-12
  min_observation_n: 5

money_flow_proxy_params:
  amount_column_priority: [amount, money, turnover_value, volume_times_close]
  close_column_priority: [qfq_close, close]
  zero_return_flow_sign: 0
  denominator_epsilon: 1.0e-12
  min_observation_n: 5

capacity_probe_params:
  model_ids: [decision_tree_depth3_grouped_cv_probe_v1, decision_tree_depth4_grouped_cv_probe_v1]
  max_depth_values: [3, 4]
  random_state: 1818
  min_samples_leaf_floor: 50
  min_samples_leaf_train_fraction: 0.02
  cv_fold_n: 5
  cv_fold_seed: 1818
  cv_aggregation: unweighted_mean_across_pass_folds
```

Optional config paths may be absent without failing `check-inputs`; however any
candidate family that requires an absent optional source must be marked
`blocked` or `appendix_only` before target evidence is computed.

## 2. Required Upstream State

18D is authorized by the observed 18C failure mode, not by 18C support.

Required 18C decision:

```text
decision_state = 18C_payoff_state_signal_weak_or_nonmonotone
next_allowed_requirement = none
rank_ic_support_gate = fail
baseline_improvement_gate = fail
monotonicity_support_gate = pass
bucket_lift_gate = pass
bootstrap_ci_gate = pass
risk_only_gate = pass
binary_sanity_boundary_gate = pass
search_accounting_gate = pass
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

If 18C instead emits `18C_payoff_state_separability_supported`, 18D is not the
right next step; the deferred EP18F oracle bridge may be considered under the
research plan. If 18C artifacts are missing, stale, schema-incompatible, or
hash-misaligned:

```text
decision_state = 18D_upstream_18c_contract_blocked
next_allowed_requirement = none
```

18C handoff authority order:

```text
1. payoff_state_separability_decision.csv
2. 18C_payoff_state_separability_diagnostic_manifest.json
3. payoff_state_separability_diagnostic_report.md
4. config_18c expected block, audit-only
```

If the 18C config `expected.next_allowed_requirement` still contains a pre-run
planned next step that conflicts with the actual 18C decision table and manifest,
18D must record:

```text
legacy_config_expected_next_mismatch = true
legacy_config_expected_next_status = audit_only_not_authoritative
```

This mismatch must not fail the upstream gate when the 18C decision table and
manifest both state `next_allowed_requirement = none`. 18D must not edit the
published 18C config in place unless the whole 18C bundle is rerun and its
manifest hashes are regenerated.

## 3. Research Questions

18D answers seven questions:

```text
Q1. Which payoff morphology information is missing from current F1-F5?

Q2. Is the current weak signal mostly participation/sponsorship rather than
    payoff-state shape?

Q3. Can the current 23 features be rescued by low-capacity nonlinear capacity,
    or is the bottleneck genuinely feature representation?

Q4. Which candidate feature families can be PIT-valid and t0-available before
    any target-correlation evidence is inspected?

Q5. Which candidate features carry payoff information orthogonal to the current
    volatility and participation proxies?

Q6. Which candidate families should be added to a refreshed feature matrix for
    a new separability run?

Q7. Can search accounting prove that no robustness/validation target-correlation
    feature selection, binary primary substitution, policy, backtest, deployment,
    production signal, or trading authorization occurred?
```

## 4. Required Input Artifacts

### 4.1 EP18 planning and requirements

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18_payoff_state_representation_research.md
experiments/pending/18_payoff_state_representation_research/requirement_18a_payoff_state_contract_preflight.md
experiments/pending/18_payoff_state_representation_research/requirement_18b_payoff_state_feature_matrix_audit.md
experiments/pending/18_payoff_state_representation_research/requirement_18c_payoff_state_separability_diagnostic.md
experiments/pending/18_payoff_state_representation_research/requirement_18d_payoff_state_feature_representation_diagnostic.md
```

### 4.2 18A/18B/18C artifacts

Required:

```text
outputs/local_cache/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix.parquet
outputs/local_cache/18C_payoff_state_separability_diagnostic/payoff_state_score_panel.parquet

outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv

outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/payoff_state_feature_matrix_schema.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_lineage_audit.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/feature_family_coverage.csv
outputs/publishable/tables/18B_payoff_state_feature_matrix_audit/train_only_preprocessing_audit.csv

outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_separability_decision.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_registry.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_cv_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_oos_rank_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_decile_monotonicity.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/baseline_comparison_readout.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/topk_removal_sensitivity.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/payoff_state_model_coefficients.csv
outputs/publishable/tables/18C_payoff_state_separability_diagnostic/binary_sanity_readout.csv
outputs/publishable/reports/payoff_state_separability_diagnostic_report.md

outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
outputs/manifests/18B_payoff_state_feature_matrix_audit_manifest.json
outputs/manifests/18C_payoff_state_separability_diagnostic_manifest.json
outputs/manifests/payoff_state_feature_matrix_manifest.json
outputs/manifests/payoff_state_score_panel_manifest.json
```

All inputs must be recorded in `input_artifact_audit.csv` and
`input_artifact_manifest_18d.json` with source role, row count, sha256, schema
status, manifest hash status, and blocking reason.

### 4.3 Candidate source discovery contract

18D must not assume M1/M3/M5 can be computed from the 18B matrix alone. The
current 18B matrix contains F1-F5 current-state features and row keys, but it
does not contain episode-low, reclaim, episode-high, or raw t0 path columns.

Before candidate scoring, 18D must discover and audit source aliases for each
candidate family:

| source_artifact_alias | role | required columns or semantics | family usage |
|:--|:--|:--|:--|
| ep18_matrix_row_keys | required row alignment source | step_id, label_id, instrument, episode_cluster_id, step_index, step_start_date, cluster_split_bucket | all |
| ep18_current_feature_matrix | required current F1-F5 source | current raw and model-ready F1-F5 columns, including mr_volatility_20d and mr_volume_20d_zscore | all residualization and gap decomposition |
| pit_price_path_panel | required if any raw morphology proxy is primary | instrument, date, date_pos or position index, qfq open/high/low/close, volume, amount or money if available, qfq-adjustment status | M1/M2/M3 |
| pit_money_flow_proxy_panel | required if any money-flow in/out proxy is primary | instrument, date, date_pos or position index, close or return, amount or money or volume*close fallback, signed-flow construction rule, buy/sell direction source if available, PIT freeze status | M2 |
| episode_geometry_panel | required for primary episode-local features | step_id or stable join key, episode_cluster_id, step_start_pos, cluster_start_pos, derived episode_low_pos_t0, derived episode_high_pos_t0, optional reclaim_pos_t0, full-episode cluster_end_pos only as leakage-audited metadata | M1/M5 |
| pre_t0_supply_zone_panel | optional unless M3 supply-zone proxy is primary | instrument, source_date, source_pos, zone_low, zone_high, construction_window, PIT-valid freeze status | M3 |
| market_or_regime_context_panel | optional and M4-only | PIT-valid date/index context, board or market breadth context, no future revisions | M4 |

If a source alias is unavailable, stale, not PIT-valid, or missing required
columns, the affected candidate family must be marked `blocked` or
`appendix_only`. A missing candidate source must not be silently replaced by an
ad hoc source during implementation.

Resolved source rules:

```text
ep18_matrix_row_keys must resolve only from paths.eighteen_b_matrix
ep18_current_feature_matrix must resolve only from paths.eighteen_b_matrix
episode_geometry_panel must be materialized from the configured 16B/16A panels and qfq path
pit_price_path_panel must resolve from paths.stock_daily_qfq_dir for primary features
pit_money_flow_proxy_panel must resolve from paths.stock_daily_qfq_dir for primary features
ep02 aligned panels are appendix/context sources unless their row join and PIT freeze are proven
full-episode interval boundaries after step_start_pos must not be treated as t0-available feature inputs
```

Primary row identity for all materialized candidate features:

```text
primary_identity_key_columns = step_id, label_id
lineage_key_columns = step_id, label_id, threshold_id, horizon_sessions,
                      instrument, episode_cluster_id, step_index,
                      step_start_pos, step_start_date
```

Episode geometry derivation:

```text
cluster_start_pos = from sixteen_b_materialized_step_panel or sixteen_a_episode_interval_panel
cluster_end_pos = from sixteen_b_materialized_step_panel or sixteen_a_episode_interval_panel,
                  used only as full-episode metadata for leakage audit unless
                  cluster_end_pos <= step_start_pos or a separate t0-frozen
                  endpoint proof exists
step_start_pos = from sixteen_b_label_step_panel, reconciled to eighteen_b_matrix
step_start_date = from sixteen_b_label_step_panel, reconciled to qfq date at step_start_pos
episode_low_pos_t0 = argmin(qfq_low[p]) for p in [cluster_start_pos, step_start_pos]
episode_low_date_t0 = qfq_date[episode_low_pos_t0]
episode_high_pos_t0 = argmax(qfq_high[p]) for p in [cluster_start_pos, step_start_pos]
episode_high_date_t0 = qfq_date[episode_high_pos_t0]
episode_range_low_t0 = qfq_low[episode_low_pos_t0]
episode_range_high_t0 = qfq_high[episode_high_pos_t0]
```

Full-episode boundary rule:

```text
If cluster_end_pos > step_start_pos, cluster_end_pos is future episode geometry
from the completed winner interval. It may be recorded for lineage diagnostics,
but it must not enter any primary candidate feature formula, denominator,
normalizer, bucket boundary, rank key, imputation rule, or finite-rate decision.

Any candidate using cluster_end_pos with cluster_end_pos > step_start_pos must be
marked:
  candidate_primary_allowed_after_lineage = false
  candidate_appendix_only = true only if emitted as leakage/oracle diagnostic
  pit_valid_status = appendix_only
  t0_available_status = blocked
  blocking_reason = full_episode_boundary_after_t0

The lineage audit must compute source_pos_max_minus_step_start_pos from the
actual formula dependencies. Hard-coded zero values are forbidden.
```

Reclaim-specific candidate features may be primary only if `reclaim_pos_t0` is
available under a deterministic rule:

```text
qfq_ma60[p] = rolling_mean(qfq_close, 60)[p], using positions <= p
reclaim_pos_t0 = first p in [episode_low_pos_t0, step_start_pos]
                 where qfq_close[p - 1] < qfq_ma60[p - 1]
                 and qfq_close[p] >= qfq_ma60[p]
```

If a row has insufficient qfq history for `qfq_ma60`, or no reclaim crossing
exists before `step_start_pos`, reclaim-specific features for that row must be
missing with `blocking_reason = reclaim_pos_t0_unavailable`. They must not be
backfilled from future path information.

QFQ path reconciliation must prove for every primary candidate row:

```text
qfq date at step_start_pos equals step_start_date
qfq close at step_start_pos matches step_start_qfq_close when the source column exists
all source positions used by the candidate feature are <= step_start_pos
all source positions used by denominators, normalizers, buckets, and imputation
  rules are <= step_start_pos
missing required qfq row -> affected candidate family blocked or row marked missing
```

## 5. Candidate Family Priority Contract

18D must not treat candidate families as flat. It must prioritize them using
18C evidence.

| family_id | candidate family | priority | evidence from 18C |
|:--|:--|:--|:--|
| M1 | episode-local morphology | high | Report identifies missing repair quality; current F1 has distance to 20/60d high but no episode-internal repair morphology |
| M3 | payoff asymmetry context | high | Directly targets missing structural upside room and asymmetry; current F1-F5 has no explicit upside/downside asymmetry representation |
| M5 | episode position and maturity | high_medium | Report identifies missing episode-internal position; only t0-known position and age features are eligible; full-episode lifecycle percentages are blocked unless a t0-frozen endpoint is proven |
| M2 | supply and pressure dynamics | medium | F2 is the only effective current source, but current F2 is mostly level/z-score; first-order and second-order dynamic pressure morphology may add marginal information |
| M4 | regime and cross-sectional context | low | F5 contributes approximately zero in the current low-capacity linear setting unless new PIT regime/industry/breadth data are available |

Hard prioritization rule:

```text
primary_audit_focus = M1 + M3 + M5
secondary_audit_focus = M2
defer_by_default = M4
```

M4 may be promoted only if the input artifact audit proves new PIT-valid
cross-sectional or regime data that were not present in 18B F5.

## 6. Candidate Feature Family Definitions

Candidate families are representation hypotheses, not selected model features.
18D may generate candidate definitions and diagnostic readouts, but it must not
publish a final refreshed model-ready matrix.

Every candidate feature that appears outside appendix must have a deterministic
`candidate_feature_formula` using one of the audited `source_artifact_alias`
values. Natural-language feature names alone are not sufficient for a primary
recommendation.

18D must materialize the predeclared candidate universe exactly before any
target-correlation or residual-rank evidence is computed. The required candidate
universe is the exact 41-feature set listed in section 6.5.

Required candidate inventory completeness rule:

```text
expected_candidate_feature_ids_by_family must be declared in config or emitted
  in candidate_feature_inventory.csv before target evidence is computed
total_required_candidate_feature_n = 41
candidate_inventory_missing_feature_n = 0
candidate_inventory_extra_feature_n = 0 unless extra_feature_role = appendix_only_exploratory
candidate_inventory_duplicate_feature_id_n = 0
candidate_inventory_formula_missing_n = 0 for all non-M4 candidates
candidate_inventory_completeness_gate = pass only if all checks above pass
```

If the candidate inventory omits any required expanded candidate, silently keeps
only the legacy 18D candidate list, or adds target-driven candidates after
readouts:

```text
candidate_inventory_completeness_gate = fail
decision_state = 18D_feature_representation_contract_blocked
next_allowed_requirement = none
```

Candidate de-duplication is mandatory because this requirement intentionally
includes several closely related representations. 18D must assign every
candidate to a `candidate_primary_dedup_group_id` before target evidence:

```text
candidate_primary_dedup_group_id is predeclared and target-blind
candidate_overlap_group_ids is optional pipe-delimited target-blind metadata
candidate_priority_score uses at most one representative per dedup group
dedup_group_representative_source = highest_abs_train_residual_ic_after_lineage
dedup_group_representative_selection_uses_robustness = false
dedup_group_representative_selection_uses_validation = false
candidate_alias_of may be populated for exact formula aliases
exact aliases must not both contribute to orthogonal_payoff_candidate_n or
  candidate_priority_score
orthogonal_payoff_candidate_n counts dedup-group representatives only
```

Known exact or near-exact alias groups that must be predeclared:

```text
candidate_primary_dedup_group_id = m1_range_location_group:
  m1_close_location_episode_range
  m1_episode_recovery_ratio_to_high_t0

candidate_primary_dedup_group_id = m3_downside_room_group:
  m3_downside_crowding_to_episode_low
  m3_downside_room_to_episode_low_t0

candidate_overlap_group_ids includes m1_m3_range_position_related_group:
  m1_close_location_episode_range
  m1_episode_recovery_ratio_to_high_t0
  m3_asymmetric_range_position_t0
```

The range-position related group is allowed to keep multiple readout rows, but
only one representative may contribute to a family priority score unless a
train-only residual correlation check proves `abs(pairwise_spearman) < 0.70`
against the already retained representative.

Common numeric and missingness rules:

```text
candidate_denominator_epsilon = 1.0e-12
candidate_min_observation_n = 5 unless a feature-specific floor is stricter
range_denominator = high - low
if range_denominator <= candidate_denominator_epsilon -> feature missing
if qfq_close_t0 <= 0 -> price-ratio feature missing
if required window has fewer than candidate_min_observation_n observations -> feature missing
if a deterministic follow-up subwindow is required and the full subwindow is not
  available before or at step_start_pos -> that anchor is excluded from the
  count, not filled from future bars
missing feature rows must keep the row in the denominator and set the candidate
  value to NaN; missingness may block primary use through finite-rate gates
```

### M1 episode-local morphology, high priority

Examples:

```text
low reclaim quality
high reclaim quality
distance from episode low
distance from episode high
repair slope from episode low
drawdown recovery shape
close location in episode range
close location in recent range
path linearity from episode low to t0
pullback from pre-t0 episode high
recovery ratio to pre-t0 episode high
failed repair count
up/down run imbalance
reclaim persistence before t0
return sign entropy before t0
path transition entropy before t0
close-location bin entropy before t0
episode repair path efficiency
```

Required lineage stance:

```text
source dates <= step_start_date
source positions <= step_start_pos
episode boundaries known at t0 only
no use of step_end_date or h20 future path
```

Path entropy requirements:

```text
entropy_window must end at step_start_pos
entropy_window_id must be one of episode_low_to_t0, trailing_20, trailing_60
state binning must be train-predeclared and not target-selected
log base = natural log
probability_epsilon = 1e-12
entropy features must use qfq-adjusted price path when price levels enter formulas
```

Default entropy windows:

```text
episode_low_to_t0 = [episode_low_pos_t0, step_start_pos]
trailing_20 = [max(first_valid_qfq_pos, step_start_pos - 19), step_start_pos]
trailing_60 = [max(first_valid_qfq_pos, step_start_pos - 59), step_start_pos]
minimum observation count for any entropy window = 5
```

Return-state binning:

```text
ret_t = qfq_close[t] / qfq_close[t - 1] - 1
state_t = down if ret_t < -0.001
state_t = flat if abs(ret_t) <= 0.001
state_t = up if ret_t > 0.001
transition_state_t = state_{t-1} -> state_t across the same window
```

Close-location binning:

```text
close_location_t = (qfq_close[t] - window_low) / (window_high - window_low)
window_low = min(qfq_low over entropy window)
window_high = max(qfq_high over entropy window)
close_location_t is clipped to [0, 1]
close_location_bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
window_high == window_low -> feature missing with blocking_reason = zero_price_range
```

Probability calculation:

```text
p_bin = (count_bin + probability_epsilon) /
        (sum(count_bin over bins) + bin_count * probability_epsilon)
entropy = -sum(p_bin * ln(p_bin))
entropy_normalized = entropy / ln(bin_count)
```

Allowed path entropy candidate formulas include:

```text
return_sign_entropy_w = -sum_{s in {up, flat, down}} p_s * log(p_s)
path_transition_entropy_w = -sum_{i,j in state_transition_bins} p_ij * log(p_ij)
close_location_entropy_w = entropy(discretize((close-low_w)/(high_w-low_w)))
repair_path_efficiency_w = abs(qfq_close_t0 - qfq_close_episode_low_t0) /
                           sum(abs(diff(qfq_close over w)))
```

`repair_path_efficiency_w` is a path-complexity proxy, not an entropy measure;
it may be grouped with path entropy diagnostics because it tests whether the
repair path is clean/direct or noisy/choppy.

Expanded M1 candidate formulas include:

```text
m1_episode_drawdown_pre_t0 =
    min(qfq_low[p] / running_max(qfq_close[p]) - 1)
    for p in [cluster_start_pos, step_start_pos]
    where running_max(qfq_close[p]) > candidate_denominator_epsilon;
    otherwise feature missing

m1_episode_recovery_ratio_to_high_t0 =
    (qfq_close_t0 - episode_low_price_t0) /
    (episode_high_price_t0 - episode_low_price_t0)
    if episode_high_price_t0 - episode_low_price_t0 > candidate_denominator_epsilon

m1_pullback_from_episode_high_t0 =
    qfq_close_t0 / episode_high_price_t0 - 1
    if episode_high_price_t0 > candidate_denominator_epsilon

m1_close_location_trailing60_range =
    (qfq_close_t0 - min(qfq_low over trailing_60)) /
    (max(qfq_high over trailing_60) - min(qfq_low over trailing_60))
    if trailing_60 range_denominator > candidate_denominator_epsilon

m1_path_linearity_r2_low_to_t0 =
    R2 of qfq_close[p] ~ p for p in [episode_low_pos_t0, step_start_pos]
    with minimum observation count = 5 and nonzero qfq_close variance

m1_up_down_run_imbalance_20 =
    longest_up_run_trailing20 - longest_down_run_trailing20

m1_failed_repair_count_low_to_t0 =
    count of local highs p in [episode_low_pos_t0 + 3, step_start_pos - 5]
    where qfq_close[p] > max(qfq_close[p-3:p-1])
    and min(qfq_close[p+1:p+5]) / qfq_close[p] - 1 <= -0.05
    and max(qfq_close[p+1:p+5]) <= qfq_close[p]
```

Required expanded M1 candidate feature ids:

```text
m1_episode_drawdown_pre_t0
m1_episode_recovery_ratio_to_high_t0
m1_pullback_from_episode_high_t0
m1_close_location_trailing60_range
m1_path_linearity_r2_low_to_t0
m1_up_down_run_imbalance_20
m1_failed_repair_count_low_to_t0
```

### M3 payoff asymmetry context, high priority

Examples:

```text
upside room proxy
downside crowding proxy
upside/downside room ratio
asymmetric range position
failed breakout count before t0
volatility-adjusted repair strength
distance to pre-breakdown supply zone
asymmetric range expansion before t0
positive convexity proxy from current state only
upper-shadow pressure before t0
upside/downside path entropy imbalance
low-entropy upside repair after high-entropy selloff
```

Required lineage stance:

```text
no future high/low after step_start_date
no realized h20 payoff component
no oracle or top30/top20 label component
```

M3 path entropy variants must be explicitly asymmetric. A generic entropy
feature belongs to M1; M3 may use entropy only when it contrasts upside repair
versus downside crowding or selloff complexity using pre-t0 path segments.

Expanded M3 candidate formulas include:

```text
m3_downside_room_to_episode_low_t0 =
    (qfq_close_t0 - episode_low_price_t0) / qfq_close_t0
    if qfq_close_t0 > candidate_denominator_epsilon

m3_upside_downside_room_ratio_t0 =
    (episode_high_price_t0 - qfq_close_t0) /
    (qfq_close_t0 - episode_low_price_t0)
    if qfq_close_t0 - episode_low_price_t0 > candidate_denominator_epsilon

m3_asymmetric_range_position_t0 =
    2 * (qfq_close_t0 - episode_low_price_t0) /
    (episode_high_price_t0 - episode_low_price_t0) - 1
    if episode_high_price_t0 - episode_low_price_t0 > candidate_denominator_epsilon

m3_failed_breakout_count_pre_t0 =
    count of qfq_high[p] reaching a new pre-t0 episode high followed by
    qfq_close falling below that breakout day's low within the next 5 sessions,
    with all counted follow-up positions <= step_start_pos

m3_upper_shadow_pressure_share_20 =
    mean((qfq_high - max(qfq_open, qfq_close)) /
         (qfq_high - qfq_low) over valid trailing_20 candles where
         qfq_high - qfq_low > candidate_denominator_epsilon)
    with minimum valid candle count = 5
```

Required expanded M3 candidate feature ids:

```text
m3_downside_room_to_episode_low_t0
m3_upside_downside_room_ratio_t0
m3_asymmetric_range_position_t0
m3_failed_breakout_count_pre_t0
m3_upper_shadow_pressure_share_20
```

### M5 episode position and maturity, high/medium priority

Examples:

```text
bars since episode low
bars since reclaim
episode age
local trend phase
non-overlap step position diagnostics
t0-known relative position diagnostics
```

Required lineage stance:

```text
episode anchor must be known by t0
position count must not use future step_end information
position denominator must not use full episode end after t0
cluster_end_pos from completed 16A/16B intervals is not a t0-known denominator
```

Allowed M5 primary candidate formulas:

```text
m5_bars_since_episode_low = step_start_pos - episode_low_pos_t0
m5_bars_since_episode_high_t0 = step_start_pos - episode_high_pos_t0
m5_episode_age_to_t0 = step_start_pos - cluster_start_pos
m5_nonoverlap_step_index_to_t0 = floor((step_start_pos - cluster_start_pos) / horizon_sessions)
m5_low_to_t0_age_ratio =
    (step_start_pos - episode_low_pos_t0) /
    max(step_start_pos - cluster_start_pos, 1)
m5_high_to_t0_age_ratio =
    (step_start_pos - episode_high_pos_t0) /
    max(step_start_pos - cluster_start_pos, 1)
m5_low_before_high_t0 = episode_low_pos_t0 < episode_high_pos_t0
```

Required expanded M5 candidate feature ids:

```text
m5_bars_since_episode_high_t0
m5_low_to_t0_age_ratio
m5_high_to_t0_age_ratio
m5_low_before_high_t0
```

Blocked unless a separate t0-frozen endpoint source is proven:

```text
m5_lifecycle_progress_to_t0 =
    (step_start_pos - cluster_start_pos) /
    (cluster_end_pos - cluster_start_pos)
```

`m5_lifecycle_progress_to_t0` is a required inventory row, not a required
primary feature. Its default contract is:

```text
candidate_inventory_expected = true
primary_candidate_allowed_before_lineage = false
candidate_appendix_only = true
t0_frozen_endpoint_proof_status = missing_or_not_proven
```

Allowed `t0_frozen_endpoint_proof_status` values:

```text
not_required
proven
missing_or_not_proven
```

If the only available denominator is a completed episode interval with
`cluster_end_pos > step_start_pos`, `m5_lifecycle_progress_to_t0` must not be a
primary candidate and must not contribute to `candidate_priority_score`,
`orthogonal_payoff_candidate_n`, `recommended_for_refresh`, or the positive 18D
decision. If emitted at all, it must be clearly labeled
`oracle_or_leakage_diagnostic_only`.

### M2 supply and pressure dynamics, medium priority

Examples:

```text
turnover compression before reclaim
turnover expansion after reclaim but before t0
volume dry-up after low
money-flow persistence
signed money-flow inflow/outflow imbalance
positive-money-flow share before t0
negative-money-flow share before t0
money-flow reversal after episode low
price-up/flow-down divergence before t0
abnormal participation decay
high-volume failure bars before t0
money-flow acceleration before t0
money-flow curvature across nested trailing windows
flow reversal acceleration before t0
```

Required constraint:

```text
must prove incremental information beyond mr_volume_20d_zscore, mr_money_20d_zscore, and current F2 levels
true buy/sell direction fields may be primary only if PIT-valid and t0-available
daily signed-flow proxies must disclose their proxy rule and cannot be described as true order flow
delayed or vendor-revised money-flow fields are appendix-only
second-order money-flow proxies must be derived only from pre-t0 first-order
  proxy sequences and must not use future realized payoff, future volume, or
  vendor-revised intraday/order-flow fields
```

Allowed money-flow proxy formulas include:

```text
signed_money_proxy_t = amount_t * sign(close_t - close_{t-1})
net_signed_money_flow_w = sum(signed_money_proxy_t) /
                          sum(abs(amount_t))
                          if sum(abs(amount_t)) > candidate_denominator_epsilon
positive_money_flow_share_w = sum(amount_t where close_t > close_{t-1}) /
                              sum(amount_t)
                              if sum(amount_t) > candidate_denominator_epsilon
negative_money_flow_share_w = sum(amount_t where close_t < close_{t-1}) /
                              sum(amount_t)
                              if sum(amount_t) > candidate_denominator_epsilon
money_flow_persistence_w = mean(sign(signed_money_proxy_t) == sign(signed_money_proxy_{t-1}))
price_flow_divergence_w = sign(ret_w) * sign(net_signed_money_flow_w)
```

Allowed second-order money-flow proxy formulas include:

```text
window set = trailing_5, trailing_10, trailing_20, trailing_60
all windows end at step_start_pos

net_signed_money_flow_accel_5v20 =
    net_signed_money_flow_trailing5 - net_signed_money_flow_trailing20

positive_money_flow_share_accel_5v20 =
    positive_money_flow_share_trailing5 - positive_money_flow_share_trailing20

money_flow_reversal_rate_w =
    mean(sign(signed_money_proxy_t) != sign(signed_money_proxy_{t-1}))

money_flow_reversal_accel_5v20 =
    money_flow_reversal_rate_trailing5 - money_flow_reversal_rate_trailing20

net_signed_money_flow_curvature_5_10_20 =
    net_signed_money_flow_trailing5
    - 2 * net_signed_money_flow_trailing10
    + net_signed_money_flow_trailing20

flow_price_divergence_persistence_20 =
    mean over trailing_20 endpoints u of
    sign(qfq_close[u] / qfq_close[u-4] - 1)
    != sign(net_signed_money_flow over [u-4, u])
    where each 5-session subwindow is fully <= step_start_pos

high_amount_negative_bar_share_20 =
    count(ret_t < 0 and amount_t >= trailing_60_amount_p80_t0) /
    count(valid trailing_20 amount observations)
    where trailing_60_amount_p80_t0 is computed only from positions
    [max(first_valid_qfq_pos, step_start_pos - 59), step_start_pos]

signed_flow_volatility_20 =
    std(signed_money_proxy_t / abs(amount_t)
        over trailing_20)
    where abs(amount_t) > candidate_denominator_epsilon

flow_concentration_top3_share_20 =
    sum(top 3 abs(signed_money_proxy_t) over trailing_20) /
    sum(abs(signed_money_proxy_t) over trailing_20)
    if sum(abs(signed_money_proxy_t) over trailing_20) > candidate_denominator_epsilon
```

Required M2 second-order candidate feature ids:

```text
m2_net_signed_money_flow_accel_5v20
m2_positive_money_flow_share_accel_5v20
m2_money_flow_reversal_accel_5v20
m2_net_signed_money_flow_curvature_5_10_20
m2_flow_price_divergence_persistence_20
m2_high_amount_negative_bar_share_20
m2_signed_flow_volatility_20
m2_flow_concentration_top3_share_20
```

These are representation candidates only. They must pass the same lineage,
finite-rate, train-only residualization, and train-prior support gates as other
M2 features before they can affect family prioritization.

Money-flow source resolution:

```text
amount_t source priority = amount, money, turnover_value, volume * qfq_close
close_t source priority = qfq_close, close
zero close-to-close return -> signed_money_proxy_t sign = 0
nonpositive or nonfinite amount_t is excluded from the window denominator
minimum observation count for trailing_5 = 5
minimum observation count for trailing_10 = 10
minimum observation count for trailing_20 = 20
minimum observation count for trailing_60 = 60
```

If no amount-like field and no `volume * close` fallback can be constructed from
the configured source, money-flow in/out proxies must be marked `blocked`.
Turnover-rate-only fields may support turnover compression/expansion diagnostics,
but they must not be labeled money-flow proxies.

### M4 regime and cross-sectional context, low priority

Examples:

```text
board-relative leadership drift
PIT-valid industry context
market breadth state
largecap/smallcap regime interaction
market beta state
```

Default decision:

```text
M4_defer_unless_new_PIT_context_available
```

### 6.5 Required Predeclared Candidate Universe

The implementation must materialize these required candidate ids in
`candidate_feature_inventory.csv` before any target evidence:

```text
M1:
  m1_return_sign_entropy_trailing20
  m1_path_transition_entropy_episode
  m1_repair_path_efficiency_episode
  m1_close_location_episode_range
  m1_episode_drawdown_pre_t0
  m1_episode_recovery_ratio_to_high_t0
  m1_pullback_from_episode_high_t0
  m1_close_location_trailing60_range
  m1_path_linearity_r2_low_to_t0
  m1_up_down_run_imbalance_20
  m1_failed_repair_count_low_to_t0

M3:
  m3_upside_room_to_episode_high
  m3_downside_crowding_to_episode_low
  m3_vol_adjusted_repair_strength
  m3_downside_room_to_episode_low_t0
  m3_upside_downside_room_ratio_t0
  m3_asymmetric_range_position_t0
  m3_failed_breakout_count_pre_t0
  m3_upper_shadow_pressure_share_20

M5:
  m5_bars_since_episode_low
  m5_bars_since_episode_high_t0
  m5_episode_age_to_t0
  m5_nonoverlap_step_index_to_t0
  m5_low_to_t0_age_ratio
  m5_high_to_t0_age_ratio
  m5_low_before_high_t0
  m5_bars_since_reclaim
  m5_lifecycle_progress_to_t0

M2:
  m2_net_signed_money_flow_trailing20
  m2_positive_money_flow_share_trailing20
  m2_money_flow_persistence_trailing20
  m2_turnover_compression_20_vs_60
  m2_net_signed_money_flow_accel_5v20
  m2_positive_money_flow_share_accel_5v20
  m2_money_flow_reversal_accel_5v20
  m2_net_signed_money_flow_curvature_5_10_20
  m2_flow_price_divergence_persistence_20
  m2_high_amount_negative_bar_share_20
  m2_signed_flow_volatility_20
  m2_flow_concentration_top3_share_20

M4:
  m4_regime_context_deferred
```

For `m5_lifecycle_progress_to_t0`, inclusion in the required universe only means
that the row must be present in `candidate_feature_inventory.csv` and lineage
tables. It must be emitted as blocked or appendix-only unless a separate
t0-frozen endpoint source proves that the denominator was known at
`step_start_pos`.

Expected required candidate counts:

```text
M1 candidate_feature_n = 11
M3 candidate_feature_n = 8
M5 candidate_feature_n = 9
M2 candidate_feature_n = 12
M4 candidate_feature_n = 1
total_required_candidate_feature_n = 41
```

## 7. Pre-diagnostic Gate 1: Capacity vs Representation

18D must first determine whether the 18C failure can be explained by insufficient
model capacity on the existing 23 features. This gate must be narrated as a
thin-margin diagnostic, not as proof that capacity has been fully ruled out.

Required source:

```text
payoff_state_oos_rank_readout.csv
payoff_state_model_registry.csv
payoff_state_model_cv_readout.csv
payoff_state_separability_decision.csv
```

Required models to replay from 18C:

```text
ridge_payoff_rank_h20_v1
elastic_net_payoff_rank_h20_v1
shallow_tree_payoff_depth2_v1
ridge_ordinal_payoff_state_v1
volatility20d_defense_baseline
```

Required current 18C handoff sanity values:

```text
ridge_payoff_rank_h20_v1 robustness rank_ic = 0.064397895867
elastic_net_payoff_rank_h20_v1 robustness rank_ic = 0.063310254141
shallow_tree_payoff_depth2_v1 robustness rank_ic = 0.076791687716
ridge_ordinal_payoff_state_v1 robustness rank_ic = -0.015911419271
volatility20d_defense_baseline robustness rank_ic = 0.064771549906
max_aux_existing_feature_rank_ic = 0.076791687716
max_aux_minus_primary_rank_ic = 0.012393791850
max_aux_margin_to_floor = 0.003208312284
max_aux_margin_to_capacity_delta_threshold = 0.002606208150
capacity_margin_status = thin_margin_caveat
```

Implementation must recompute these from 18C artifacts. If the observed value
differs from the expected value by more than `1e-9`, mark the upstream handoff
as stale or changed and emit the observed value in `upstream_18c_handoff_audit.csv`.
Validation stress rows must not be used to clear the capacity gate.

Threshold rationale and sensitivity:

```text
capacity_delta_threshold = 0.015000
threshold_rationale = approximately half of the legacy +0.030 external-context
                      improvement band and approximately the current primary
                      ridge shortfall to the 0.080000 materiality floor
sensitivity_thresholds = 0.010000, 0.015000, 0.020000
thin_margin_threshold = 0.005000
```

If either of these is true:

```text
0.080000 - max_aux_existing_feature_rank_ic <= thin_margin_threshold
capacity_delta_threshold - max_aux_minus_primary_rank_ic <= thin_margin_threshold
```

then `capacity_margin_status = thin_margin_caveat`. The report must state that
the current evidence supports only:

```text
capacity_conclusion_scope = low_capacity_representation_gap_with_capacity_caveat
```

It must not state:

```text
capacity_fully_ruled_out = true
```

### 7.1 Bounded Medium-capacity Train-only Probe

18D must add a bounded capacity probe on the existing 23 features to avoid
overstating the representation conclusion.

Allowed probe models:

```text
decision_tree_depth3_grouped_cv_probe_v1
decision_tree_depth4_grouped_cv_probe_v1
```

Optional if already available in local dependencies:

```text
small_gbm_depth2_grouped_cv_probe_v1
```

Probe rules:

```text
fit_split = train only
cv_scheme = episode_cluster_grouped_cv
feature_set = current 18B 23 model-ready features only
target = y_payoff_h20
max_tree_depth <= 4
min_samples_leaf = max(50, ceil(0.02 * fit_fold_train_row_n))
robustness_rows_used_for_probe_training = false
validation_rows_used_for_probe_training = false
robustness_rows_used_for_probe_selection = false
validation_rows_used_for_probe_selection = false
probe_role = capacity_diagnostic_only
```

Grouped-CV reproducibility contract:

```text
cv_fold_n = 5
cv_fold_seed = 1818
fold_unit = episode_cluster_id
fold_assignment = shuffle sorted unique train episode_cluster_id with cv_fold_seed,
                  then assign fold_id = shuffled_index mod cv_fold_n
fold_status = pass only if test_row_n > 0
cv_mean_rank_ic_spearman = unweighted arithmetic mean of payoff_rank_ic across pass folds
cv_weighted_mean_rank_ic_spearman = sum(payoff_rank_ic * test_row_n) / sum(test_row_n)
primary_cv_rank_ic = cv_mean_rank_ic_spearman for ridge_payoff_rank_h20_v1
max_train_grouped_cv_probe_rank_ic = max cv_mean_rank_ic_spearman across allowed probe models
max_train_grouped_cv_probe_minus_primary_cv_rank_ic =
    max_train_grouped_cv_probe_rank_ic - primary_cv_rank_ic
```

The `cv_weighted_mean_rank_ic_spearman` value is a required diagnostic column,
but the gate comparator must use the unweighted `cv_mean_rank_ic_spearman` value.
The primary ridge comparator must be recomputed under the same fold assignment as
the bounded probes; do not compare a newly computed probe against an unrelated
18C summary statistic.

The bounded probe must not authorize a production model, select a model family,
tune thresholds, or change feature recommendations. It is used only to decide
whether the report should describe the bottleneck as clearly representational or
capacity/representation ambiguous.

Medium-capacity caveat rule:

```text
medium_capacity_probe_caveat = true
if max_train_grouped_cv_probe_rank_ic >= 0.080000
or max_train_grouped_cv_probe_minus_primary_cv_rank_ic >= 0.015000
```

If `medium_capacity_probe_caveat = true`, 18D may still compute the candidate
feature diagnostics as appendix/readout evidence, but the positive refresh
handoff is not allowed. The report and decision table must state:

```text
capacity_conclusion_scope = capacity_not_excluded_by_train_cv_probe
```

Required readout:

```text
primary_ridge_robustness_rank_ic
elastic_net_robustness_rank_ic
shallow_tree_robustness_rank_ic
ordinal_ridge_robustness_rank_ic
volatility20d_robustness_rank_ic
max_aux_existing_feature_rank_ic
max_aux_minus_primary_rank_ic
max_aux_margin_to_floor
max_aux_margin_to_capacity_delta_threshold
capacity_delta_threshold
capacity_threshold_sensitivity_status
capacity_margin_status
capacity_conclusion_scope
max_train_grouped_cv_probe_rank_ic
max_train_grouped_cv_probe_minus_primary_cv_rank_ic
medium_capacity_probe_caveat
capacity_bottleneck_flag
representation_bottleneck_flag
cv_fold_n
cv_fold_seed
cv_aggregation_method
primary_cv_rank_ic
cv_weighted_mean_rank_ic_spearman
```

Decision rule:

```text
capacity_bottleneck_flag = true
if max_aux_existing_feature_rank_ic >= 0.080000
or max_aux_minus_primary_rank_ic >= 0.015000
or medium_capacity_probe_caveat = true

representation_bottleneck_flag = true
if max_aux_existing_feature_rank_ic < 0.080000
and max_aux_minus_primary_rank_ic < 0.015000
and medium_capacity_probe_caveat = false
```

If capacity_bottleneck_flag is true:

```text
decision_state = 18D_capacity_bottleneck_on_existing_features
next_allowed_requirement = none
```

This decision means the research plan must revisit model capacity diagnostics
before creating new features. It does not authorize a more complex production
model.

## 8. Pre-diagnostic Gate 2: Volatility and Participation Orthogonality

18D must prevent new features from merely rediscovering the current weak signal
ceiling around volatility and participation.

For each candidate feature or candidate feature proxy:

```text
residualization_control_set_id = base_vol_participation
residualization_control_set_role = standard_orthogonality_readout
candidate_feature ~ mr_volatility_20d + mr_volume_20d_zscore

apply train-fitted residualization to train, robustness, validation
compute residual_candidate_rank_ic_vs_y_payoff_h20 by split
compute raw_candidate_rank_ic_vs_y_payoff_h20 by split
compute residual_retention = residual_rank_ic / raw_rank_ic
```

For M2 first-order and second-order money-flow proxy candidates, an additional
train-only incremental residualization must be reported:

```text
residualization_control_set_id = f2_extended_participation_money
residualization_control_set_role = m2_recommendation_gate
candidate_feature ~ mr_volatility_20d
                  + mr_volume_20d_zscore
                  + mr_turnover_rate_20d_zscore
                  + mr_money_20d_zscore
```

Required residualization rows:

```text
all candidates must emit base_vol_participation rows for train, robustness, validation
M2 candidates must additionally emit f2_extended_participation_money rows for
  train, robustness, validation
orthogonal readout unique key =
  candidate_family_id, candidate_feature_id, split_bucket,
  residualization_control_set_id
```

Recommendation eligibility by residualization control set:

```text
Non-M2 candidates:
  recommendation_eligible_residualization = true only for base_vol_participation

M2 candidates:
  recommendation_eligible_residualization = false for base_vol_participation
  recommendation_eligible_residualization = true only for f2_extended_participation_money
```

An M2 feature may be recommended only if the F2-extended train-prior row passes
the support rule. Its base residualization row is diagnostic-only. This prevents
a new money-flow proxy, including second-order acceleration or curvature terms,
from merely renaming the existing participation/money z-score signal.

Hard requirements:

```text
residualization_fit_split = train
residualization_uses_target = false
residualization_uses_robustness_rows = false
residualization_uses_validation_rows = false
candidate_priority_score must not include robustness target evidence
candidate_priority_score must not include validation target evidence
candidate_priority_score may include train-only residual prior evidence after lineage passes
candidate_priority_score must use only recommendation_eligible_residualization rows
```

Candidate train-prior support rule:

```text
orthogonal_payoff_candidate = true
if abs(residual_train_rank_ic) >= 0.010000
and residual_rank_ic_same_sign_as_raw = true
and recommendation_eligible_residualization = true
```

Robustness and validation residual rank ICs are diagnostic readouts only. They
must be reported for stress evidence, but they must not change
`recommended_for_refresh`, `candidate_priority_score`, or the positive 18D
decision. Candidates failing the train-prior support rule may remain in
appendix, but cannot be recommended for the refreshed primary feature matrix.

Required target evidence roles:

```text
train rows -> target_evidence_role = train_priority_prior
robustness rows -> target_evidence_role = robustness_diagnostic_only
validation rows -> target_evidence_role = validation_diagnostic_only
```

Only `train_priority_prior` rows with `recommendation_eligible_residualization =
true` may set `orthogonal_payoff_candidate = true`.

## 9. Lineage Before Correlation Gate

18D must evaluate candidate feature lineage before any payoff target correlation
or rank IC is computed.

Required lineage statuses:

```text
pit_valid_status in {pass, blocked, appendix_only}
t0_available_status in {pass, blocked, delayed_appendix_only}
source_pos_max_minus_step_start_pos <= 0
source_date_max_minus_step_start_date <= 0
normalizer_pos_max_minus_step_start_pos <= 0
uses_full_episode_boundary_after_t0 = false for every primary candidate
uses_future_h20_path = false
uses_step_end_outcome = false
uses_oracle_label = false
uses_payoff_target = false
uses_binary_target = false
```

If a candidate family cannot pass lineage/PIT/t0 requirements:

```text
candidate_primary_allowed = false
candidate_appendix_only = true if delayed but diagnostically useful
```

Feature lineage audit rules:

```text
source_pos_max_minus_step_start_pos must be computed from every source position
  referenced by the feature formula.
normalizer_pos_max_minus_step_start_pos must include denominator, bucket,
  normalization, rolling-stat, finite-rate, and imputation dependencies.
For path-window features, source_pos_max is the max window endpoint.
For M5 position features, source_pos_max includes every boundary used in the
  numerator or denominator.
If cluster_end_pos > step_start_pos and the feature formula references
  cluster_end_pos, uses_full_episode_boundary_after_t0 = true and the candidate
  is blocked from primary use.
Implementation must not emit pass lineage rows by assigning constant zero values
  without replaying formula dependencies.
```

The published lineage table may be candidate-level, but it must be a rollup from
row-level dependency evaluation:

```text
lineage_scope = candidate_row_rollup
row_n = number of candidate panel rows evaluated for this feature
finite_candidate_value_row_n = number of finite emitted candidate values
source_dependency_row_n = number of rows with any source dependency observed
future_source_dependency_row_n = number of rows with any source dependency > step_start_pos
normalizer_dependency_row_n = number of rows with denominator, bucket,
  normalization, rolling-stat, finite-rate, or imputation dependency observed
future_normalizer_dependency_row_n = number of rows with any normalizer
  dependency > step_start_pos
max_source_pos_minus_step_start_pos = max row-level source position delta
max_normalizer_pos_minus_step_start_pos = max row-level normalizer position delta
source_pos_max_minus_step_start_pos must equal max_source_pos_minus_step_start_pos
normalizer_pos_max_minus_step_start_pos must equal max_normalizer_pos_minus_step_start_pos
```

For a primary candidate:

```text
future_source_dependency_row_n = 0
future_normalizer_dependency_row_n = 0
max_source_pos_minus_step_start_pos <= 0
max_normalizer_pos_minus_step_start_pos <= 0
```

Rows that are made missing because a pre-t0 window is incomplete are not future
dependencies. Rows whose finite feature value, denominator, bucket, or imputation
uses future data are future dependencies and must block primary use.

If any primary recommendation was selected before lineage/PIT/t0 checks:

```text
lineage_before_correlation_gate = fail
decision_state = 18D_feature_representation_contract_blocked
next_allowed_requirement = none
```

## 10. Required Outputs

All publishable tables must be CSV with LF line endings and deterministic row
ordering.

Required publishable tables:

```text
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/upstream_18c_handoff_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/capacity_vs_representation_readout.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_inventory.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_lineage_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/candidate_feature_pit_availability_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/current_feature_gap_decomposition.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/payoff_morphology_proxy_readout.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/orthogonal_payoff_information_readout.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/feature_family_candidate_prioritization.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/search_accounting_audit.csv
outputs/publishable/tables/18D_payoff_state_feature_representation_diagnostic/representation_refresh_decision.csv
```

Required report:

```text
outputs/publishable/reports/payoff_state_feature_representation_diagnostic_report.md
```

Required manifests:

```text
outputs/manifests/18D_payoff_state_feature_representation_diagnostic_manifest.json
outputs/manifests/input_artifact_manifest_18d.json
```

## 11. Required Table Schemas

### 11.1 `capacity_vs_representation_readout.csv`

Required columns:

```text
model_id
model_family
source_feature_set
split_bucket
rank_ic_spearman
cv_mean_rank_ic_spearman
cv_weighted_mean_rank_ic_spearman
cv_rank_ic_delta_vs_primary
rank_ic_materiality_floor
delta_vs_primary_ridge
delta_vs_volatility20d_baseline
capacity_delta_threshold
max_aux_margin_to_floor
max_aux_margin_to_capacity_delta_threshold
capacity_threshold_sensitivity_threshold
capacity_threshold_sensitivity_status
capacity_margin_status
capacity_conclusion_scope
medium_capacity_probe_caveat
capacity_bottleneck_flag
representation_bottleneck_flag
cv_fold_n
cv_fold_seed
cv_aggregation_method
primary_cv_rank_ic
readout_status
```

### 11.2 `candidate_feature_inventory.csv`

Required columns:

```text
candidate_family_id
candidate_feature_id
candidate_feature_name
candidate_feature_definition
candidate_feature_formula
candidate_primary_dedup_group_id
candidate_overlap_group_ids
candidate_alias_of
candidate_priority_before_evidence
source_artifact_alias
source_columns
expected_availability
primary_candidate_allowed_before_lineage
appendix_only_if_delayed
extra_feature_role
candidate_inventory_expected
candidate_inventory_completeness_gate
t0_frozen_endpoint_proof_status
notes
```

### 11.3 `candidate_feature_lineage_audit.csv`

Required columns:

```text
candidate_family_id
candidate_feature_id
source_artifact_alias
lineage_scope
row_n
finite_candidate_value_row_n
source_dependency_row_n
future_source_dependency_row_n
normalizer_dependency_row_n
future_normalizer_dependency_row_n
source_pos_max_minus_step_start_pos
source_date_max_minus_step_start_date
normalizer_pos_max_minus_step_start_pos
max_source_pos_minus_step_start_pos
max_normalizer_pos_minus_step_start_pos
uses_full_episode_boundary_after_t0
uses_future_h20_path
uses_step_end_outcome
uses_oracle_label
uses_payoff_target
uses_binary_target
pit_valid_status
t0_available_status
candidate_primary_allowed_after_lineage
candidate_appendix_only
lineage_before_correlation_gate
blocking_reason
```

### 11.4 `orthogonal_payoff_information_readout.csv`

Required columns:

```text
candidate_family_id
candidate_feature_id
split_bucket
candidate_primary_dedup_group_id
residualization_control_set_id
residualization_control_set_role
raw_candidate_rank_ic
residual_candidate_rank_ic
residual_retention
residualization_fit_split
residualization_covariates
residualization_uses_target
residualization_uses_robustness_rows
residualization_uses_validation_rows
residual_rank_ic_same_sign_as_raw
orthogonal_payoff_candidate
dedup_group_representative
recommendation_eligible_residualization
target_evidence_role
orthogonality_status
```

Required row identity:

```text
candidate_family_id, candidate_feature_id, split_bucket,
residualization_control_set_id must be unique
M2 candidates must have both base_vol_participation and
  f2_extended_participation_money rows for each split
Non-M2 candidates must have base_vol_participation rows for each split
orthogonal_payoff_candidate can be true only on train_priority_prior rows where
  recommendation_eligible_residualization = true
```

### 11.5 `feature_family_candidate_prioritization.csv`

Required columns:

```text
candidate_family_id
planned_priority
evidence_adjusted_priority
priority_reason
candidate_feature_n
primary_allowed_candidate_n
orthogonal_payoff_candidate_n
delayed_appendix_candidate_n
dedup_group_n
dedup_group_representative_candidate_ids
raw_candidate_priority_score
candidate_priority_score
priority_score_method
priority_source
recommended_for_refresh
recommendation_role
blocking_reason
```

Required priority constraints:

```text
M1 recommended_for_refresh should be evaluated first if lineage/PIT/t0 and train-prior checks pass
M3 recommended_for_refresh should be evaluated first if lineage/PIT/t0 and train-prior checks pass
M5 recommended_for_refresh should be evaluated first or second if lineage/PIT/t0 and train-prior checks pass
M2 recommended only if train-prior residual evidence survives participation controls
M4 recommended only if new PIT context data exists
robustness and validation target readouts must not alter recommended_for_refresh
candidate_priority_score = sum(abs(train residual IC)) across dedup-group representatives only
candidate_priority_score uses base_vol_participation train rows for non-M2 candidates
candidate_priority_score uses f2_extended_participation_money train rows for M2 candidates
raw_candidate_priority_score must be reported separately when non-representative candidate readouts exist
```

### 11.6 `representation_refresh_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
all_hard_gates_pass
upstream_18c_contract_gate
input_artifact_gate
capacity_vs_representation_gate
candidate_inventory_completeness_gate
candidate_lineage_gate
pit_t0_availability_gate
orthogonal_payoff_information_gate
feature_family_prioritization_gate
search_accounting_gate
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
recommended_refresh_family_ids
deferred_family_ids
appendix_only_family_ids
```

### 11.7 `input_artifact_audit.csv`

Required columns:

```text
artifact_path
source_artifact_alias
config_path_key
resolver_priority
artifact_role
required
required_for_primary_candidate
affected_family_ids
exists
row_count
column_count
sha256
manifest_path
manifest_hash_status
schema_status
freshness_status
resolved_source_status
blocking_reason
```

### 11.8 `upstream_18c_handoff_audit.csv`

Required columns:

```text
source_table
source_model_id
source_split_bucket
source_metric
expected_value
observed_value
tolerance
handoff_status
blocking_reason
```

### 11.9 `candidate_feature_pit_availability_audit.csv`

Required columns:

```text
candidate_family_id
candidate_feature_id
source_artifact_alias
required_source_columns
source_available_at_t0
source_max_lag_bars
delayed_observed_state
t0_frozen_endpoint_proof_status
pit_valid_status
t0_available_status
primary_allowed
appendix_only
blocking_reason
```

### 11.10 `current_feature_gap_decomposition.csv`

Required columns:

```text
current_family_id
current_feature_ids
existing_signal_role
represented_information
missing_payoff_information
evidence_metric
evidence_value
gap_status
candidate_family_mapping
```

### 11.11 `payoff_morphology_proxy_readout.csv`

Required columns:

```text
candidate_family_id
candidate_feature_id
proxy_type
split_bucket
row_n
source_window_id
formula_params_id
raw_candidate_rank_ic
residual_candidate_rank_ic
residual_retention
residualization_control_set_id
residualization_control_set_role
residualization_covariates
residual_rank_ic_same_sign_as_raw
orthogonal_payoff_candidate
recommendation_eligible_residualization
target_evidence_role
missingness_rate
drift_status
diagnostic_status
```

### 11.12 `search_accounting_audit.csv`

Required columns:

```text
check_name
expected_value
observed_value
status
blocking_reason
```

## 12. Required Gates

Positive 18D support requires:

```text
upstream_18c_contract_gate = pass
input_artifact_gate = pass
capacity_vs_representation_gate = pass
candidate_inventory_completeness_gate = pass
candidate_lineage_gate = pass
pit_t0_availability_gate = pass
orthogonal_payoff_information_gate = pass
feature_family_prioritization_gate = pass
search_accounting_gate = pass
```

Capacity-vs-representation gate:

```text
representation_bottleneck_flag = true
capacity_bottleneck_flag = false
capacity_margin_status in {clear_margin, thin_margin_caveat}
capacity_conclusion_scope != capacity_fully_ruled_out
```

`thin_margin_caveat` does not fail the gate by itself. It requires explicit
report disclosure and prevents the report from claiming that capacity has been
fully excluded.

Candidate lineage gate:

```text
lineage_before_correlation_gate = pass for every recommended primary candidate
candidate_primary_allowed_after_lineage = true for every recommended primary candidate
uses_full_episode_boundary_after_t0 = false for every recommended primary candidate
normalizer_pos_max_minus_step_start_pos <= 0 for every recommended primary candidate
future_source_dependency_row_n = 0 for every recommended primary candidate
future_normalizer_dependency_row_n = 0 for every recommended primary candidate
max_source_pos_minus_step_start_pos <= 0 for every recommended primary candidate
max_normalizer_pos_minus_step_start_pos <= 0 for every recommended primary candidate
```

PIT/t0 gate:

```text
pit_valid_status = pass for every recommended primary candidate
t0_available_status = pass for every recommended primary candidate
delayed t0+k features are appendix_only
m5_lifecycle_progress_to_t0 may be primary only if
  t0_frozen_endpoint_proof_status = proven
```

Orthogonal payoff information gate:

```text
at least one high-priority family among M1/M3/M5 has train-prior orthogonal_payoff_candidate_n > 0
recommended candidate features must not be only volatility/participation replicas
robustness/validation target evidence is diagnostic-only and cannot clear or fail this gate
```

Feature-family prioritization gate:

```text
recommended_refresh_family_ids must prioritize M1/M3/M5 over M2/M4
M4 cannot be recommended unless new PIT context data exists
```

## 13. Required Decisions

Allowed decisions:

```text
18D_feature_representation_refresh_supported
18D_upstream_18c_contract_blocked
18D_input_artifact_blocked
18D_capacity_bottleneck_on_existing_features
18D_feature_representation_contract_blocked
18D_no_pit_valid_candidate_features_found
18D_candidate_features_delayed_or_leaky
18D_no_orthogonal_payoff_information_found
18D_representation_gap_diagnostic_only
18D_search_accounting_blocked
```

Decision precedence:

```text
1. upstream_18c_contract_gate fail -> 18D_upstream_18c_contract_blocked
2. input_artifact_gate fail -> 18D_input_artifact_blocked
3. capacity_bottleneck_flag true -> 18D_capacity_bottleneck_on_existing_features
4. candidate_inventory_completeness_gate fail -> 18D_feature_representation_contract_blocked
5. candidate_lineage_gate fail -> 18D_feature_representation_contract_blocked
6. pit_t0_availability_gate fail with no primary candidates -> 18D_no_pit_valid_candidate_features_found
7. pit_t0_availability_gate fail with delayed-only candidates -> 18D_candidate_features_delayed_or_leaky
8. orthogonal_payoff_information_gate fail -> 18D_no_orthogonal_payoff_information_found
9. feature_family_prioritization_gate fail -> 18D_representation_gap_diagnostic_only
10. search_accounting_gate fail -> 18D_search_accounting_blocked
11. all hard gates pass -> 18D_feature_representation_refresh_supported
```

Positive handoff:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
```

No 18D decision may authorize policy, backtest, deployment, production signal,
or live trading.

## 14. Search Accounting

18D must emit `search_accounting_audit.csv` proving:

```text
no_feature_selection_from_target_correlation_before_lineage = true
no_candidate_added_after_target_readout = true
no_candidate_removed_after_target_readout = true
candidate_inventory_completeness_verified_before_target_readout = true
no_feature_selection_from_robustness = true
no_feature_selection_from_validation = true
no_final_model_training = true
no_model_family_selection_from_robustness = true
no_threshold_tuning_on_robustness = true
no_threshold_tuning_on_validation = true
binary_metric_not_primary_gate = true
neutral_rows_not_dropped = true
delayed_features_not_primary = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

## 15. Report Requirements

`payoff_state_feature_representation_diagnostic_report.md` must include:

1. One-line decision and next allowed requirement.
2. 18C evidence summary.
3. Capacity-vs-representation readout with existing 18C model ICs.
4. Capacity thin-margin caveat, threshold sensitivity, and bounded depth<=4 train-only probe results.
5. Candidate family priority table mapping M1-M5 to 18C report evidence.
6. Candidate inventory completeness summary, including expected/observed counts and missing/extra feature ids.
7. Candidate de-duplication and alias-group summary, including representative selection rules.
8. Lineage/PIT/t0 audit summary, including row-level future dependency counts.
9. Orthogonal payoff information summary after volatility/participation residualization, with residualization control-set ids.
10. M1 expanded morphology diagnostics, including path entropy, repair path efficiency, drawdown/recovery, run-imbalance, and failed-repair definitions.
11. M3 expanded asymmetry diagnostics, including room ratio, asymmetric range position, failed breakout, and upper-shadow pressure definitions.
12. M5 t0-known position diagnostics, including why full-episode lifecycle progress is blocked unless a t0-frozen endpoint is proven.
13. Money-flow inflow/outflow proxy diagnostics, including signed-flow proxy rule, second-order proxy definitions, and F2-extended residualization.
14. Recommended feature families for refresh.
15. Families deferred or appendix-only, with reasons.
16. Search accounting and authorization boundary.

The report must state clearly:

```text
18D diagnoses feature representation gaps only.
18D does not train the final payoff separability model.
18D does not authorize policy, backtest, deployment, production signal, or trading.
Lineage/PIT/t0 validity must be established before target correlation evidence.
The predeclared candidate inventory must be complete before target evidence.
Candidate family scores must use de-duplicated train-prior representatives, not
raw sums over correlated aliases.
M1/M3/M5 are the primary audit focus; M2 is secondary; M4 is deferred by default.
Completed episode boundaries after t0 are not PIT-valid primary feature inputs.
M2 second-order money-flow proxies are secondary representation candidates and
must survive F2-extended train-only residualization before recommendation.
M2 base volatility/participation residualization rows are diagnostic-only; M2
recommendation and family score use the f2_extended_participation_money train row.
The current capacity-vs-representation conclusion is thin-margin and limited to
low-capacity representation evidence unless bounded train-only probes also fail
to show material capacity rescue.
```

## 16. Manifest Requirements

`18D_payoff_state_feature_representation_diagnostic_manifest.json` must include:

```text
run_id
phase_id
requirement_file_sha256
config_file_sha256
runner_file_sha256
input_artifact_manifest_sha256
publishable_table_sha256_by_name
report_sha256
decision_state
next_allowed_requirement
all_hard_gates_pass
upstream_18c_decision_state
candidate_inventory_completeness_gate
candidate_inventory_expected_feature_n
candidate_inventory_observed_feature_n
candidate_inventory_missing_feature_n
candidate_inventory_extra_feature_n
capacity_bottleneck_flag
representation_bottleneck_flag
recommended_refresh_family_ids
deferred_family_ids
appendix_only_family_ids
capacity_margin_status
capacity_conclusion_scope
medium_capacity_probe_caveat
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
```

## 17. Handoff to 18E

18E is the payoff-state feature matrix refresh phase. It may begin only if:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
all hard gates = pass
```

18E is expected to refresh the feature matrix contract before any new
separability run. The deferred oracle-gap bridge is EP18F and remains blocked
until a future separability diagnostic emits:

```text
decision_state = 18C_payoff_state_separability_supported
```

## 18. Validation Commands

Required validation commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/18_payoff_state_representation_research/src/run_18d_payoff_state_feature_representation_diagnostic.py
python experiments/pending/18_payoff_state_representation_research/src/run_18d_payoff_state_feature_representation_diagnostic.py --mode check-inputs
python experiments/pending/18_payoff_state_representation_research/src/run_18d_payoff_state_feature_representation_diagnostic.py --mode full
pytest experiments/pending/18_payoff_state_representation_research/tests/test_18d_payoff_state_feature_representation_diagnostic.py -q
```

Before publish:

```bash
git diff --check
```

## 19. Required Test Coverage

`tests/test_18d_payoff_state_feature_representation_diagnostic.py` must include
focused tests for the implementation contract:

```text
test_config_declares_explicit_source_aliases
test_runner_does_not_walk_arbitrary_candidate_source_directories
test_legacy_18c_config_expected_next_is_audit_only_when_decision_manifest_next_is_none
test_input_artifact_audit_records_config_key_resolver_priority_and_affected_family
test_candidate_inventory_materializes_exact_required_41_feature_universe
test_candidate_inventory_completeness_gate_blocks_legacy_candidate_subset
test_candidate_inventory_blocks_target_driven_added_or_removed_candidates
test_candidate_dedup_groups_are_predeclared_before_target_readout
test_candidate_priority_score_uses_dedup_representatives_not_raw_alias_sum
test_formula_missingness_rules_cover_zero_range_zero_close_and_insufficient_windows
test_episode_geometry_derives_low_high_only_from_positions_lte_step_start_pos
test_full_episode_cluster_end_after_t0_blocks_lifecycle_progress_primary_candidate
test_lineage_source_pos_replays_formula_dependencies_not_hardcoded_zero
test_lineage_audit_rolls_up_row_level_future_dependency_counts
test_reclaim_features_missing_when_reclaim_pos_t0_unavailable
test_m5_expanded_position_features_use_only_t0_known_denominators
test_m5_lifecycle_progress_inventory_row_is_blocked_without_t0_endpoint_proof
test_qfq_step_start_reconciliation_blocks_affected_primary_candidates_on_mismatch
test_entropy_windows_bins_log_base_and_epsilon_are_deterministic
test_m1_expanded_morphology_features_use_episode_low_to_t0_or_trailing_windows
test_m1_failed_repair_count_uses_only_complete_pre_t0_followup_windows
test_m3_expanded_asymmetry_features_use_only_pre_t0_high_low_and_shadow_paths
test_m3_failed_breakout_count_uses_only_complete_pre_t0_followup_windows
test_money_flow_proxy_uses_amount_priority_and_labels_volume_times_close_fallback
test_turnover_only_source_cannot_be_labeled_money_flow_proxy
test_m2_second_order_money_flow_proxy_windows_end_at_step_start
test_m2_second_order_money_flow_proxy_uses_f2_extended_train_residualization
test_orthogonal_readout_unique_key_includes_residualization_control_set
test_m2_recommendation_uses_f2_extended_residualization_not_base_row
test_m2_high_amount_negative_bar_threshold_is_t0_rolling_not_trainwide
test_capacity_probe_reuses_grouped_cv_leaf_rule_and_unweighted_mean_comparator
test_medium_capacity_probe_caveat_blocks_positive_18e_handoff
test_morphology_readout_includes_target_evidence_role_and_residual_retention
test_robustness_validation_rank_ic_cannot_change_recommended_for_refresh
test_search_accounting_blocks_policy_backtest_deployment_signal_and_trading
```
