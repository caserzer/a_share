# EP4 R01 Seed Trial: MA60 Trend + 20D High + VOL1.5 + RPS120>90

- Trial seed id: `ep4_trend_ma60_high20_vol15_rps90_seed_v0`
- Generated at: `2026-05-11T10:26:16.190321+00:00`
- Output root: `ep4/outputs/r01_seed_trial_trend_ma60_high20_vol15_rps90`
- Scope: exploratory seed trial only. Canonical R01 output is not overwritten. Matched-random gates are not run.

## Formula

```text
trend_ok = close_T > MA60(close, ending T) AND MA60_T > MA60_(T-1)
structure_ok = close_T >= max(close, previous 20 trading days)
volume_ok = volume_T > 1.5 * mean(volume, previous 20 trading days)
strength_ok = RPS120_T > 90th percentile cross-sectionally
seed = trend_ok AND structure_ok AND volume_ok AND strength_ok AND PIT/execution hard filters
entry = next open after signal_date
```

## Headline

| metric | value |
|:--|--:|
| primary reference count | 845 |
| trial episodes | 1132 |
| trial executable episodes | 795 |
| captured primary big winners | 55 |
| total primary recall | 6.51% |

## Density

| split      |   eligible_stock_day_count |   executable_seed_stock_day_count |   seed_episode_count |   seed_day_rate |   seed_episode_rate |   seed_day_rate_vs_ep2 |   seed_episode_rate_vs_ep2 |   suppressed_reentry_count |   risk_distance_ineligible_count |
|:-----------|---------------------------:|----------------------------------:|---------------------:|----------------:|--------------------:|-----------------------:|---------------------------:|---------------------------:|---------------------------------:|
| train      |                     170220 |                              1014 |                  447 |      0.005957   |            0.642241 |               0.882507 |                   0.389034 |                        569 |                              122 |
| validation |                     107733 |                               666 |                  309 |      0.00618195 |            0.689732 |               1.25188  |                   0.580827 |                        377 |                              101 |
| robustness |                     108330 |                               852 |                  376 |      0.00786486 |            0.858447 |               1.20339  |                   0.531073 |                        454 |                              114 |

## Recall

| split      |   big_winner_reference_count |   captured_big_winner_count |   missed_big_winner_count |   primary_big_winner_seed_recall |   seed_recall_diff_vs_ep2_detector |
|:-----------|-----------------------------:|----------------------------:|--------------------------:|---------------------------------:|-----------------------------------:|
| train      |                          446 |                          29 |                       417 |                        0.0650224 |                        -0.0156951  |
| validation |                          158 |                           9 |                       149 |                        0.056962  |                         0.0379747  |
| robustness |                          241 |                          17 |                       224 |                        0.0705394 |                         0.00829876 |

## Probe Quality

| split      |   raw_trigger_days |   hard_filter_pass_days |   episodes |   executable_episodes |   risk_below_min |   risk_above_max |   suppressed_reentry_count |   probe_mean_return_r |   probe_median_return_r |   probe_p05_return_r |   probe_failed_primary_rate |   fail_fast_trigger_rate |   no_ff_mean_return_r |   no_ff_p05_return_r |   no_ff_median_holding_days |   probe_median_holding_days |
|:-----------|-------------------:|------------------------:|-----------:|----------------------:|-----------------:|-----------------:|---------------------------:|----------------------:|------------------------:|---------------------:|----------------------------:|-------------------------:|----------------------:|---------------------:|----------------------------:|----------------------------:|
| train      |               3022 |                    1014 |        447 |                   325 |              109 |               12 |                        569 |             0.011882  |               -0.285532 |            -0.790884 |                    0.910769 |                 0.492308 |             0.0383393 |             -1.62439 |                          22 |                          22 |
| validation |               1591 |                     666 |        309 |                   208 |               96 |                5 |                        377 |            -0.119175  |               -0.321238 |            -0.621294 |                    0.956731 |                 0.576923 |            -0.194518  |             -1.28483 |                          22 |                           8 |
| robustness |               1988 |                     852 |        376 |                   262 |              100 |               14 |                        454 |            -0.0577557 |               -0.30842  |            -0.636126 |                    0.92827  |                 0.526718 |            -0.0345435 |             -1.13685 |                          22 |                          10 |

## Interpretation

This seed fixes the density problem but sacrifices the high-recall objective. It is a quality-biased strong-momentum seed, not a replacement for the R01 high-recall candidate. Validation recall improves over EP2 bridge but total recall drops far below `ep4_wide_seed_v0`.
