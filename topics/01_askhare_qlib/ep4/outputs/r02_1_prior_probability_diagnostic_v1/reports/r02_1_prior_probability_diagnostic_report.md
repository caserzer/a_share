# R02.1 Prior Probability Diagnostic Report

This is an exploratory prior diagnostic, not an entry strategy, not a staged-build experiment, and not R03 validation.

## Scope

The diagnostic uses the seven frozen R02 single-family signals and R02 next-open 120D path labels.

## Availability

- Global action-time prior: `unavailable_background_path_not_materialized`
- EV_R status: `unavailable_missing_inputs`
- Fresh evidence prior: `available`
- Risk-budget R03 launch status: insufficient until EV_R inputs and action-time denominator are materialized.

## Single Family Ranking

| family_id         |   row_count |   label_denominator_count |   P_good |    P_bad |
|:------------------|------------:|--------------------------:|---------:|---------:|
| range_breakout    |       68679 |                     54069 | 0.358034 | 0.612095 |
| volume_money      |       22806 |                     17900 | 0.358777 | 0.61395  |
| oscillator        |       23132 |                     18293 | 0.356406 | 0.614828 |
| volatility_band   |       28211 |                     22023 | 0.344395 | 0.631003 |
| pullback_drawdown |       56446 |                     44307 | 0.330549 | 0.656746 |
| momentum_rps      |       44120 |                     33909 | 0.330095 | 0.657776 |
| price_trend       |       34592 |                     26899 | 0.324467 | 0.664096 |

## Same-Day Family Count

|   same_day_family_count |   row_count |   label_denominator_count |   P_good |    P_bad |
|------------------------:|------------:|--------------------------:|---------:|---------:|
|                       1 |       29908 |                     23692 | 0.365885 | 0.599639 |
|                       2 |       23677 |                     18525 | 0.362138 | 0.609093 |
|                       3 |       14587 |                     11507 | 0.353579 | 0.622745 |
|                       4 |       10248 |                      7985 | 0.345277 | 0.636304 |
|                       5 |        8624 |                      6746 | 0.334479 | 0.652607 |
|                       6 |        7187 |                      5616 | 0.310325 | 0.673365 |
|                       7 |        4247 |                      3253 | 0.333443 | 0.658555 |

## Bundle Sparsity And Fallback

| fallback_level        |   bucket_count |
|:----------------------|---------------:|
| same_day_family_count |            802 |
| same_day_bundle_key   |            105 |

## Context Bucket Availability

| sample_sufficiency_status   |   bucket_count |
|:----------------------------|---------------:|
| too_sparse_use_fallback     |            628 |
| thin_bucket_report_only     |            157 |
| sufficient                  |            105 |
| unusable                    |             17 |

## Survival Checkpoints

| checkpoint   |   pre_checkpoint_row_count |   survivor_count |   non_survivor_count |   survivor_label_denominator_count |   survivor_P_good |   survivor_P_bad |   survivor_rate |
|:-------------|---------------------------:|-----------------:|---------------------:|-----------------------------------:|------------------:|-----------------:|----------------:|
| T+10         |                      98478 |            54064 |                44414 |                              42751 |          0.667037 |         0.295385 |        0.548996 |
| T+3          |                      98478 |            75269 |                23209 |                              59491 |          0.460959 |         0.51216  |        0.764323 |
| T+5          |                      98478 |            66907 |                31571 |                              52872 |          0.524455 |         0.445752 |        0.679411 |

## Fresh Evidence Offset Distribution

| fresh_evidence_status    |   row_count |
|:-------------------------|------------:|
| found_within_t3_t30      |        6343 |
| seed_failed_before_fresh |        2725 |
| seed_failed_before_t3    |        1533 |
| none_within_t3_t30       |         305 |
| ambiguous_same_offset    |          65 |
| censored_before_t30      |          32 |

Numeric fresh offset median: `3.0`.

## Fresh Evidence Posterior

| fresh_evidence_status    |   row_count |   label_denominator_count |     P_good |      P_bad |   median_fresh_offset |
|:-------------------------|------------:|--------------------------:|-----------:|-----------:|----------------------:|
| ambiguous_same_offset    |          65 |                         0 | nan        | nan        |                     3 |
| censored_before_t30      |          32 |                         0 | nan        | nan        |                   nan |
| found_within_t3_t30      |        6343 |                      5032 |   0.593794 |   0.365592 |                     5 |
| none_within_t3_t30       |         305 |                       216 |   0.512159 |   0.427448 |                   nan |
| seed_failed_before_fresh |        2725 |                      2115 |   0.021557 |   0.962057 |                   nan |
| seed_failed_before_t3    |        1533 |                      1195 |   0        |   1        |                   nan |

## T+30 Plausibility

T+30 has observable fresh-evidence coverage when found rows exist, but censored and seed-failed rows must remain in R03 controls.

## Split Stability

| stability_status                    |   row_count |
|:------------------------------------|------------:|
| insufficient_sample                 |         974 |
| missing_split                       |         652 |
| stable_enough_for_requirement_input |         129 |
| unstable_do_not_freeze              |          22 |

## R03 Readiness

| readiness_scope               | global_prior_ready          | single_family_prior_ready   | same_day_bundle_prior_ready   | context_bucket_prior_ready   | survival_checkpoint_prior_ready   | fresh_evidence_prior_ready   | ev_r_ready           | split_stability_ready   | recommended_r03_bucket_grain   | recommended_build_window_status   | primary_blocker      | secondary_blocker                                  | required_next_action                                                            |
|:------------------------------|:----------------------------|:----------------------------|:------------------------------|:-----------------------------|:----------------------------------|:-----------------------------|:---------------------|:------------------------|:-------------------------------|:----------------------------------|:---------------------|:---------------------------------------------------|:--------------------------------------------------------------------------------|
| r03_direct_posterior_table_v1 | blocked_missing_denominator | ready                       | ready                         | ready                        | ready                             | ready                        | blocked_missing_ev_r | blocked_unstable_split  | same_day_bundle_context        | build_window_t30_supported        | blocked_missing_ev_r | blocked_missing_denominator|blocked_unstable_split | materialize EV_R inputs and action-time path denominator before risk-budget R03 |
