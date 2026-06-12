# Requirement: Experiment B - Regime x Event-Family Performance Matrix

## 1. Background

07 / 08 reports show materially different behavior by market regime. The next step is not to ask only whether one family is stable across all regimes. Experiment B must evaluate which event families are useful in which regimes, while enforcing sample-size guardrails so small cells do not drive conclusions.

Experiment B is a diagnostic / design experiment. It does not select a final entry union and does not train a model.

## 2. Primary Question

```text
Which event families provide recall, bridge quality, acceptable 10d fast-fail
cost, and acceptable density in risk_off, risk_on, and transition regimes?
```

## 3. Required Dependency

Experiment B must read and reference:

```text
outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
```

If the contract is missing, the final decision must be:

```text
regime_family_matrix_contract_blocked
```

Experiment B must not redefine 10d density, adjacent gap, fast-fail, or episode-window diagnostic rules.

## 4. Required Inputs

Read-only inputs:

1. `outputs/manifests/run_manifest.json`
2. `outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md`
3. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_summary.csv`
4. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_fast_fail_readout.csv`
5. `outputs/publishable/tables/density_fast_fail_audit/candidate_10d_retention_by_split_regime.csv`
6. `outputs/publishable/tables/density_fast_fail_audit/candidate_adjacent_event_gap_diagnostic.csv`
7. `outputs/publishable/tables/candidate_family_incremental_recall_over_e1.csv`
8. `outputs/publishable/tables/candidate_family_bridge_positive_recall.csv`
9. `outputs/publishable/tables/candidate_family_recall_by_split_regime.csv`
10. `outputs/publishable/tables/candidate_family_density_summary.csv`
11. `outputs/publishable/tables/candidate_family_label_quality_readout.csv`
12. `outputs/publishable/tables/candidate_family_false_repair_diagnostic.csv`
13. `outputs/publishable/tables/candidate_family_overlap_matrix.csv`
14. `outputs/publishable/tables/candidate_family_mechanism_cluster_summary.csv`
15. `outputs/publishable/tables/regime_recall_baseline_07_e1_only.csv`
16. 07 tables needed for E1 / E2 / E3 / E6 context:
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_channel_recall_contribution.csv`
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_channel_density_summary.csv`
    - `../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_false_repair_diagnostic.csv`
17. this requirement file.

If Experiment A tables are missing but the user intentionally runs B as a pre-A planning pass, B may output only a schema / plan report with:

```text
regime_family_matrix_waiting_for_density_contract
```

It must not output family support claims.

## 5. Candidate Families

Experiment B must include at least:

1. `E1_early_ema60_repair`
2. `E2_same_day_confirmation_tag`
3. `E3_persistence_quality`
4. `E6_continuation_tag`
5. `T4_entropy_compression_directional_expansion`
6. `T7_board_relative_strength_break`
7. `R1_relative_strength_breakout`
8. `R2_near_high_volume_expansion`
9. `R6_market_breadth_thrust`
10. `R7_cross_sectional_momentum_rank_jump`
11. `R8_persistent_distance_above_ema`

Optional diagnostic families may include R3, T3, T5, T6, T8, and R5, but optional families must never replace the required list.

## 6. Regime and Split Grid

Required regimes:

1. `risk_off`
2. `risk_on`
3. `transition`

Required splits:

1. `train`
2. `validation`
3. `robustness`
4. `all`

Headline conclusions may use `all` only as context. Support / block conclusions must be split-aware and must respect sample-size guardrails.

## 7. Required Outputs

Write outputs under:

```text
outputs/publishable/tables/regime_family_matrix/
outputs/publishable/reports/regime_family_matrix/
outputs/manifests/regime_family_matrix/
```

Required tables:

1. `regime_family_performance_matrix.csv`
2. `regime_family_sample_guardrail.csv`
3. `regime_family_density_fast_fail_matrix.csv`
4. `regime_family_bridge_recall_matrix.csv`
5. `regime_family_overlap_concentration_matrix.csv`
6. `regime_family_design_recommendations.csv`

Required report:

1. `regime_family_matrix_report.md`

Required manifest:

1. `regime_family_matrix_manifest.json`

## 8. Required Metrics

For each split / regime / family cell, report:

1. `episode_denominator_n`
2. `bridge_denominator_n`
3. `event_n`
4. `candidate_captured_episode_n`
5. `before_first_50pct_any_recall`
6. `bridge_positive_recall`
7. `incremental_recall_over_e1`
8. `incremental_captures_over_e1`
9. `e1_missed_capture_n`
10. `fast_fail_10d_rate`
11. `false_repair_20d_rate`
12. `events_per_instrument_year_mean`
13. `events_per_instrument_year_p95`
14. `rolling_10d_duplicate_rate`
15. `adjacent_gap_median`
16. `single_family_density_share`
17. `mechanism_cluster_share`
18. `label_completeness_rate`
19. `next_open_executable_rate`
20. `cell_sample_status`
21. `family_regime_role_recommendation`

## 9. Sample-Size Guardrails

Every split / regime / family cell must report `episode_denominator_n` and `bridge_denominator_n`.

Cell status rules:

1. If `episode_denominator_n < 30` or `bridge_denominator_n < 30`, set:

```text
cell_sample_status = diagnostic_only
```

The cell must not be used for support / block decisions, threshold tuning, or family selection.

2. If `30 <= episode_denominator_n < 100` or `30 <= bridge_denominator_n < 100`, set:

```text
cell_sample_status = low_power_caution
```

The cell may be discussed only with train / robustness consistency and must not be a sole support claim.

3. If both denominators are >= 100, set:

```text
cell_sample_status = sufficient_for_cell_readout
```

4. Known small cells, including validation risk_on with denominator around 22, must be explicitly marked `diagnostic_only`.

## 10. Family Role Classification

Experiment B must classify each family / regime pair into one of:

1. `backbone_candidate`
2. `support_feature_candidate`
3. `context_tag_only`
4. `density_or_fast_fail_blocked`
5. `bridge_quality_blocked`
6. `sample_blocked`
7. `negative_control`

Classification rules:

1. `backbone_candidate` requires sufficient sample cells, positive incremental recall over E1, bridge-positive recall not worse than E1, acceptable 10d fast-fail cost, and no concentration block.
2. `support_feature_candidate` allows concentration or density to fail direct-entry limits, but requires positive bridge readout and acceptable fast-fail cost.
3. `context_tag_only` applies when overlap is high or incremental recall is near zero but the family may help as a feature.
4. `sample_blocked` overrides all positive claims when sample guardrails fail.
5. `negative_control` applies to families such as R5 if low density comes with poor recall / bridge quality.

## 11. Regime Design Hypotheses

The report must evaluate, but not assume as true:

1. `risk_off`: E1 repair backbone may dominate; R/T families may be context only.
2. `risk_on`: R1 / R6 / R7 / R8 may provide high recall and bridge quality, but need density and fast-fail control.
3. `transition`: T4 / volatility-compression families may matter, but overlap with R3 / T8 must be separated before support claims.

## 12. Decisions

Allowed final decisions:

1. `regime_family_matrix_complete`
2. `regime_family_matrix_contract_blocked`
3. `regime_family_matrix_input_blocked`
4. `regime_family_matrix_waiting_for_density_contract`

This experiment must not emit direct-entry support. It only emits design recommendations.

## 13. Report Requirements

`regime_family_matrix_report.md` must contain:

1. one-page conclusion.
2. sample-size guardrail summary.
3. family role matrix by regime.
4. risk_off findings.
5. risk_on findings.
6. transition findings.
7. density / fast-fail summary using Experiment A contract.
8. small-cell caveats, including validation risk_on.
9. recommendations for Experiment C and T4 overlap decomposition.

## 14. Tests

At minimum, tests must verify:

1. cells with denominator < 30 are forced to `diagnostic_only`.
2. cells with denominator 30-99 are marked `low_power_caution`.
3. Experiment B fails closed if the density contract is absent.
4. no metric redefines 10d density outside the contract.
5. `all` split cannot override split-level sample-blocked cells.
6. high overlap families can be classified only as `context_tag_only` unless non-overlap bucket evidence is available.
