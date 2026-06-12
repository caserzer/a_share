# Requirement: Experiment C - Risk-on R-series Bridge-Positive Ranker

## 1. Background

The R-series compression patch showed that risk_on R1 / R2 / R6 / R7 / R8 are not recall-blocked and are not obviously bridge-quality-blocked. The binding constraint is density / p95 / concentration. Deterministic compression arms did not find a direct-entry candidate.

Experiment C tests whether a train-only event selection ranker can retain risk_on bridge-positive episode coverage while controlling 10d fast-fail cost and event-day density.

Experiment C must preserve two possible useful outcomes:

1. direct-entry candidate support.
2. meta-label / rejector feature-source support.

A no-direct-entry result is valid and must still produce reusable ranker diagnostics.

## 2. Required Dependency

Experiment C must read and reference:

```text
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
```

If missing, return:

```text
risk_on_r_series_ranker_contract_blocked
```

C must not redefine density, fast-fail, adjacent gap, or episode-window diagnostic rules.

## 3. Primary Question

```text
Can a train-only ranker / budgeted selector find a risk_on R-series subset
that preserves bridge-positive coverage and E1-missed recall while controlling
10d executable event-day density and fast-fail cost?
```

## 4. Non-Goals

Experiment C must not:

1. run a trading strategy or portfolio backtest.
2. use validation / robustness for threshold tuning.
3. use target episode membership to generate event candidates.
4. use future 120d returns as event features.
5. silently drop R2 because it is unscored.
6. report a direct-entry candidate if only the 65% feature-source guard passes.
7. overwrite 08 full-run or R-series compression patch artifacts.

## 5. Inputs

Required read-only inputs:

1. `outputs/manifests/run_manifest.json`
2. `outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md`
3. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_summary.csv`
4. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_fast_fail_readout.csv`
5. `outputs/publishable/tables/density_fast_fail_audit/candidate_adjacent_event_gap_diagnostic.csv`
6. `outputs/publishable/tables/candidate_family_event_instances.csv.gz`
7. `outputs/publishable/tables/candidate_family_canonical_events.csv.gz`
8. `outputs/publishable/tables/candidate_family_incremental_recall_over_e1.csv`
9. `outputs/publishable/tables/candidate_family_bridge_positive_recall.csv`
10. `outputs/publishable/tables/candidate_family_density_summary.csv`
11. `outputs/publishable/tables/candidate_family_label_quality_readout.csv`
12. `outputs/publishable/tables/candidate_family_false_repair_diagnostic.csv`
13. `outputs/publishable/tables/candidate_family_overlap_matrix.csv`
14. `outputs/publishable/tables/candidate_family_feature_snapshot_summary.csv`
15. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_compression_frontier.csv`
16. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_score_spec.csv`
17. `outputs/publishable/tables/risk_on_r_series_density_compression/risk_on_r_series_source_pool_summary.csv`
18. this requirement file.

Optional supervised-ranker inputs:

1. `outputs/local_cache/candidate_family_event_labels.parquet`
2. `outputs/local_cache/candidate_family_capture.parquet`
3. `outputs/local_cache/cross_section_feature_panel.parquet`

If optional local cache is absent, supervised arms must fail closed with:

```text
ranker_arm_status = supervised_ranker_input_blocked_missing_local_cache
```

but deterministic budget / score arms must still run if publishable tables are sufficient.

## 6. Source Families

Default source families:

1. `R1_relative_strength_breakout`
2. `R2_near_high_volume_expansion`
3. `R6_market_breadth_thrust`
4. `R7_cross_sectional_momentum_rank_jump`
5. `R8_persistent_distance_above_ema`

Optional support family:

1. `R3_vcp_breakout`

Negative-control family:

1. `R5_growth_or_small_style_confirmation`

R5 may be included only in diagnostics and must not contribute to selected pools.

## 7. R2 Handling

R2 is a core semantic family but was unscored in the R-series compression patch because amount / volume expansion fields were unavailable.

Experiment C must choose one explicit R2 policy:

1. `r2_recomputed_volume_score`: amount / volume fields are available and hash-audited; R2 enters score ranker.
2. `r2_family_budget_only`: R2 remains unscored but receives an explicit family budget / cooldown.
3. `r2_diagnostic_only`: R2 is excluded from selected pools but retained in diagnostics.

Silent R2 dropping is forbidden.

## 8. Feature Rules

Allowed feature classes:

1. t0-visible R1 / R6 / R7 / R8 score fields.
2. audited R2 amount / volume expansion fields if available.
3. family id and mechanism cluster id.
4. same-day overlap tags.
5. rolling 10d / 20d duplicate counts computed by Experiment A contract.
6. event-regime / board / market context available at t0.
7. E2 / E3 / E6 same-day tags as context features only.

Forbidden features:

1. future return.
2. future high / low.
3. first +50% touch date.
4. target episode membership.
5. post-event volume.
6. validation / robustness rank labels.
7. any field that is label-derived before event t0.

## 9. Labels and Objectives

Training labels may use future outcomes only as labels, never as event-generation features.

Primary training objective:

```text
bridge_positive_event_or_episode_capture
```

Primary constraints:

1. `failure_10` / fast-fail cost.
2. 10d executable event-day density.
3. family concentration.

Secondary evaluation label:

```text
winner_120
```

`winner_120` must remain a staged downstream label and must not be the sole ranker objective.

## 10. Selection Discipline

All fitting, feature selection, calibration, score thresholds, family budgets, and cooldown parameters must be learned or chosen using train risk_on only.

Validation risk_on is small and must be read-only diagnostic.

Robustness is support / block readout only and must not be used for tuning.

If any code path uses validation or robustness for threshold selection, final decision must be:

```text
risk_on_r_series_ranker_leakage_blocked
```

## 11. Candidate Arms

Experiment C must evaluate at least:

1. `baseline_event_regime_gated_r_pool`
2. `family_budget_equal_weight`
3. `family_budget_bridge_weighted_train_only`
4. `cooldown_20d_ranked_within_bucket`
5. `cooldown_40d_ranked_within_bucket`
6. `top_k_per_instrument_month_family_aware`
7. `market_day_family_quota`
8. `supervised_bridge_ranker` if optional local-cache inputs are available.
9. `r2_budget_only_arm` if R2 is unscored.

Each arm must output selected canonical events, rejected events, rank scores if available, and failure reasons.

## 12. Required Outputs

Write outputs under:

```text
outputs/publishable/tables/risk_on_r_series_bridge_ranker/
outputs/publishable/reports/risk_on_r_series_bridge_ranker/
outputs/manifests/risk_on_r_series_bridge_ranker/
outputs/local_cache/risk_on_r_series_bridge_ranker/
```

Required tables:

1. `risk_on_r_series_ranker_arm_frontier.csv`
2. `risk_on_r_series_ranker_selected_events.csv`
3. `risk_on_r_series_ranker_rejected_events.csv`
4. `risk_on_r_series_ranker_feature_spec.csv`
5. `risk_on_r_series_ranker_family_budget_audit.csv`
6. `risk_on_r_series_ranker_density_fast_fail_readout.csv`
7. `risk_on_r_series_ranker_bridge_recall_readout.csv`
8. `risk_on_r_series_ranker_oos_separability.csv`
9. `risk_on_r_series_ranker_decision_tiers.csv`
10. `risk_on_r_series_ranker_failure_distribution.csv`

Required report:

1. `risk_on_r_series_bridge_ranker_report.md`

Required manifest:

1. `risk_on_r_series_bridge_ranker_manifest.json`

## 13. Output Schemas

`risk_on_r_series_ranker_arm_frontier.csv` must include:

1. `arm_id`
2. `arm_type`
3. `source_family_ids`
4. `r2_policy`
5. `train_selected_event_count`
6. `validation_selected_event_count`
7. `robustness_selected_event_count`
8. `density_vs_e1_full_denominator`
9. `events_per_instrument_year_p95`
10. `rolling_10d_duplicate_rate`
11. `adjacent_gap_median`
12. `single_family_density_share_max`
13. `train_risk_on_incremental_recall_over_e1`
14. `train_risk_on_bridge_delta_vs_e1`
15. `robustness_risk_on_incremental_recall_over_e1`
16. `robustness_risk_on_bridge_delta_vs_e1`
17. `fast_fail_10d_rate`
18. `direct_entry_gate_pass`
19. `feature_source_gate_pass`
20. `decision_tier`
21. `failure_reason`

`risk_on_r_series_ranker_decision_tiers.csv` must include one row per selected candidate tier:

1. `decision_tier`
2. `selected_arm_id`
3. `direct_entry_35pct_share_pass`
4. `feature_source_65pct_share_pass`
5. `density_gate_pass`
6. `p95_gate_pass`
7. `bridge_gate_pass`
8. `recall_gate_pass`
9. `fast_fail_gate_pass`
10. `oos_separability_status`
11. `supported_usage`

## 14. Decision Tiers

Experiment C must use three decision tiers.

### 14.1 Direct-entry candidate

Decision:

```text
direct_entry_candidate_supported
```

Required:

1. train risk_on incremental recall >= +8 pct.
2. train risk_on bridge delta >= +5 pct.
3. robustness risk_on incremental recall >= +8 pct.
4. robustness risk_on bridge delta >= +5 pct.
5. density <= Experiment A contract limit.
6. p95 <= Experiment A contract limit.
7. downstream direct-entry family share <= 35%.
8. fast_fail_10d_rate not materially worse than E1.
9. OOS separability does not reverse.

### 14.2 Meta-label feature source

Decision:

```text
meta_label_feature_source_supported
```

Allowed when direct-entry fails but:

1. single-family density share <= 65%.
2. train bridge delta is positive.
3. robustness bridge delta is non-negative or only mildly degraded with explanation.
4. at least one OOS separability readout remains positive.
5. fast-fail 10d cost is auditable and not materially worse than E1.
6. selected events are clearly marked as feature-source only.

This tier may feed a meta-label / rejector experiment, but must not be reported as an entry union.

### 14.3 Diagnostic only / no candidate

Decision:

```text
diagnostic_only_or_no_candidate
```

Required when neither of the above tiers passes.

This is a valid negative result. It must still output:

1. ranker scores.
2. rejected-arm frontier.
3. family budget audit.
4. failure distribution.
5. explanation of whether the blocker is density, bridge, fast-fail, concentration, OOS separability, or missing features.

Other blocking decisions:

1. `risk_on_r_series_ranker_input_blocked`
2. `risk_on_r_series_ranker_contract_blocked`
3. `risk_on_r_series_ranker_leakage_blocked`

## 15. OOS Separability

Report OOS separability for:

1. bridge-positive vs bridge-negative.
2. non-fast-fail vs fast-fail 10d.
3. 120d winner vs non-winner as secondary.
4. E1-missed captured vs still missed.

Metrics:

1. AUC.
2. PR-AUC.
3. top-decile lift.
4. calibration by score decile.
5. sample count by split / regime.

Cells with n < 30 must be `diagnostic_only`. Cells with 30 <= n < 100 must be `low_power_caution`.

## 16. Report Requirements

`risk_on_r_series_bridge_ranker_report.md` must include:

1. one-page conclusion with decision tier.
2. input / contract audit.
3. R2 policy.
4. source family summary.
5. arm frontier.
6. selected arm explanation.
7. direct-entry gate replay.
8. feature-source gate replay.
9. density / fast-fail readout.
10. bridge / recall readout.
11. OOS separability readout.
12. negative-result explanation if no tier passes.
13. downstream recommendation.

## 17. Tests

At minimum, tests must verify:

1. validation / robustness are never used for threshold tuning.
2. missing contract blocks the run.
3. missing optional local cache blocks only supervised arms.
4. R2 policy is explicit.
5. direct-entry tier requires 35% share gate.
6. feature-source tier uses 65% share gate and cannot be labeled entry.
7. no future-return or episode-membership feature enters training.
8. no-candidate still writes frontier, scores, and failure distribution.
