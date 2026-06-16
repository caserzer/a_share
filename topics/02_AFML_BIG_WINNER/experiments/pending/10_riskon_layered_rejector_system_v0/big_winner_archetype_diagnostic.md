# Big Winner Archetype Diagnostic

> Status: preliminary v0 diagnostic definition. This is not a frozen requirement and not a supported predictor contract. The thresholds below are starting hypotheses only; they must be checked against existing forward-path data before being finalized.

## 1. Purpose

The current `winner_120` label is an endpoint label:

```text
winner_120 = true if 120d forward outcome reaches the big-winner threshold
```

That endpoint should remain the primary KPI / retention denominator. The issue exposed by 10C is that endpoint winners are not path-homogeneous: the false-repair rejector appears to injure a specific winner path, especially E1-missed / early-shakeout winners.

This diagnostic adds a secondary path readout:

```text
winner_path_archetype_v0
```

It is meant for readout, target engineering discussion, and exit / continuation policy design. It must not be used as a t0 entry-rejector feature.

## 2. Scope And Discipline

Supported scope for the diagnostic should start from the same 10A default population used by 10C:

```text
population_id = 10A__same_instrument_cooldown_10d
denominator_id = post_dedup_risk_on_r_core
admission_status = admitted
```

Classification is only meaningful for rows where:

```text
winner_120 == true
horizon_complete_120d == true
forward path OHLC is available for d = 1..120
```

If forward path is missing, output:

```text
winner_path_status = input_blocked_missing_forward_path
```

Do not infer path archetypes from aggregate tables.

## 3. Required Inputs

Reuse the 04 label convention: returns are measured from `trade_open_price` using forward OHLC.

```text
trade_open_pos
trade_open_price
horizon_complete_20d
horizon_complete_60d
horizon_complete_120d
mfe_20d
mae_20d
mfe_60d
mae_60d
mfe_120d
mae_120d
forward qfq_open[d], qfq_high[d], qfq_low[d], qfq_close[d] for d = 1..120
```

## 4. Derived Fields

```text
ret_high[d]  = qfq_high[d]  / trade_open_price - 1
ret_low[d]   = qfq_low[d]   / trade_open_price - 1
ret_close[d] = qfq_close[d] / trade_open_price - 1

day_to_mfe50 =
  min d in [1, 120] where ret_high[d] >= 0.50

day_to_confirm12 =
  min d in [1, 120] where ret_high[d] >= 0.12
  else null

day_to_mae20_low =
  argmin d in [1, 20] of ret_low[d]

running_high[d] =
  max qfq_high[1..d]

max_drawdown_to_mfe50 =
  min over d in [1, day_to_mfe50] of qfq_low[d] / running_high[d] - 1

max_single_day_close_return_to_mfe50 =
  max over d in [1, day_to_mfe50] of qfq_close[d] / qfq_close[d-1] - 1
  where qfq_close[0] = trade_open_price

max_gap_open_return_to_mfe50 =
  max over d in [1, day_to_mfe50] of qfq_open[d] / qfq_close[d-1] - 1
  where qfq_close[0] = trade_open_price

limit_like_up_day_count_to_mfe50 =
  count d in [1, day_to_mfe50] where qfq_close[d] / qfq_close[d-1] - 1 >= 0.095
```

## 5. Preliminary Multi-Hot Flags

These flags are intentionally multi-hot. They should be output before assigning a single primary archetype so overlap can be audited.

```text
gap_or_event_driven_flag =
  limit_like_up_day_count_to_mfe50 >= 2
  OR max_gap_open_return_to_mfe50 >= 0.08
  OR max_single_day_close_return_to_mfe50 >= 0.18

shakeout_reversal_flag =
  mae_20d <= -0.08
  AND day_to_mae20_low < day_to_mfe50

volatile_chop_flag =
  max_drawdown_to_mfe50 <= -0.15
  AND mfe_60d >= 0.20
  AND mae_60d <= -0.12

early_momentum_flag =
  day_to_confirm12 <= 20
  AND day_to_mfe50 <= 60
  AND mae_20d > -0.08
  AND max_drawdown_to_mfe50 > -0.12

late_bloomer_flag =
  day_to_mfe50 > 60
  AND mfe_20d < 0.12
```

## 6. Preliminary Primary Label

The primary label is assigned with a fixed precedence order to keep downstream crosstabs simple. The multi-hot flags remain the more important diagnostic output.

```text
if winner_120 != true:
  winner_path_archetype_v0 = not_winner
elif horizon_complete_120d != true or day_to_mfe50 is null:
  winner_path_archetype_v0 = input_blocked
elif gap_or_event_driven_flag:
  winner_path_archetype_v0 = gap_or_event_driven_winner
elif shakeout_reversal_flag:
  winner_path_archetype_v0 = shakeout_reversal_winner
elif volatile_chop_flag:
  winner_path_archetype_v0 = volatile_chop_winner
elif early_momentum_flag:
  winner_path_archetype_v0 = early_momentum_winner
elif late_bloomer_flag:
  winner_path_archetype_v0 = late_bloomer_winner
else:
  winner_path_archetype_v0 = mixed_or_unclassified_winner
```

## 7. Threshold Notes

These thresholds are not final.

```text
0.50 = current big-winner endpoint threshold
0.12 = current confirm_20 upper barrier
-0.08 = current confirm_20 lower barrier, reused as the early-shakeout floor
-0.12 / -0.15 = provisional deeper drawdown thresholds for volatile paths
0.095 = provisional A-share limit-up proxy; should be replaced by board / ST-aware limits if available
```

## 8. Required Empirical Audits Before Finalizing

Before promoting this from preliminary v0 to a frozen diagnostic definition, compute these audits on existing data:

1. **Coverage audit**: count rows with complete 120d path OHLC, missing path rows, and horizon-incomplete rows by split.
2. **Distribution audit**: quantiles by split for `day_to_mfe50`, `mae_20d`, `mae_60d`, `max_drawdown_to_mfe50`, gap metrics, and limit-like up-day counts.
3. **Flag overlap audit**: multi-hot overlap matrix across all proposed flags; if overlap is high, revise precedence or split labels.
4. **Archetype balance audit**: primary archetype counts by split / regime / family; flag any category with too little power.
5. **10C injury concentration audit**: crosstab `10C full / keep_9000 rejected winner` by archetype and by E1-missed flag.
6. **OOS stability audit**: compare archetype proportions and rejected-winner concentration across train / validation / robustness.
7. **Threshold sensitivity audit**: vary provisional thresholds around local quantiles and check whether conclusions change materially.
8. **E1 alignment audit**: measure overlap between `shakeout_reversal_winner`, E1-missed winners, and bridge winners.

Only after these audits should thresholds be frozen into a v1 diagnostic. If the audits show unstable or low-power categories, keep `winner_path_archetype_v0` as exploratory readout only.

## 9. Usage Boundary

Allowed:

```text
diagnostic crosstabs
winner retention by path
10C / 10D rejected-winner concentration readout
winner-safe label engineering discussion
exit / continuation policy design after t+k path information exists
```

Forbidden:

```text
t0 entry-rejector predictor
threshold / model selection on validation or robustness
claiming a supported gate from path archetype readout alone
replacing winner_120 as the primary endpoint KPI
```
