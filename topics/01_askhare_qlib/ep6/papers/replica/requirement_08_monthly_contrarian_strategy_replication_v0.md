# EP6 Paper Replica Requirement 08: Monthly Contrarian Strategy Replication V0

## 1. Requirement Metadata

requirement_id: `ep6_paper_replica_08_monthly_contrarian_strategy_replication_v0`

short_name: `r08_monthly_contrarian_strategy_replication_v0`

status: `requirement-draft`

workflow: `EP6`

created_date: `2026-05-27`

requirement_path: `ep6/papers/replica/requirement_08_monthly_contrarian_strategy_replication_v0.md`

source_paper:

- local_pdf: `ep6/papers/08_profitability_of_contrarian_strategies_in_chinese_stock_market_shi_jiang_zhou_2015.pdf`
- title: `Profitability of Contrarian Strategies in the Chinese Stock Market`
- authors: `Huai-Long Shi, Zhi-Qiang Jiang, Wei-Xing Zhou`
- journal: `PLOS ONE`
- published_date: `2015-09-14`
- doi: `10.1371/journal.pone.0137892`
- paper_sample: `Shanghai and Shenzhen A-share stocks, monthly data, 1997-01 to 2012-12`

primary_output_namespace: `ep6/outputs/r08_monthly_contrarian_strategy_replication_v0/`

authorization_scope:

```text
authorized_strategy_requirement = false
```

This requirement is a paper-replication diagnostic contract only. It must not be interpreted as a live strategy, production allocator, or permission to trade long-short A-share books.

## 2. Research Positioning

This requirement replicates the paper's monthly cross-sectional loser / winner / contrarian portfolio construction under the local EP5 universe and data discipline.

The local research question is:

```text
Using the EP5 PIT mcap500 mainboard universe,
does the paper's monthly loser-minus-winner contrarian effect survive directionally
across short, intermediate, and long J/K horizons in local out-of-sample windows?
```

This is a replication diagnostic, not a strategy authorization.

The requirement does not attempt to replicate:

```text
full RESSET all-A-share universe
paper's 1997-2012 historical sample
separate exhaustive all-listed SHSE and SZSE universes
B-share exclusion audit from raw exchange files
IPO-month exclusion from original listing-event database
production short book or deployable allocator
```

Because the local repository uses a PIT mcap500 mainboard universe and a post-2017 local sample, this requirement is:

```text
paper-inspired local monthly contrarian replication diagnostic
not exact RESSET all-A-share 1997-2012 paper replication
```

Every final report under this requirement must include the caveat:

```text
local_universe_and_sample_not_paper_equivalent
```

## 3. Paper Result To Reproduce Directionally

The paper's main setup:

```text
Data:
  monthly adjusted returns of all A-share stocks on SHSE and SZSE
  January 1997 to December 2012

Ranking:
  rank stocks by prior J-month return

Grouping:
  decile, quintile, and tertile grouping

Loser portfolio:
  worst prior-return group

Winner portfolio:
  best prior-return group

Contrarian portfolio:
  long loser portfolio and short winner portfolio

J values:
  1, 6, 12, 18, 24, 30, 36, 42, 48 months

K values:
  1, 6, 12, 18, 24, 30, 36, 42, 48 months

Primary portfolio weight:
  equal weight

Primary reported return:
  annualized average return with heteroscedasticity/autocorrelation adjusted t-statistics
```

Key paper readouts to reproduce directionally:

| Paper claim | Directional target |
|:--|:--|
| Whole-sample contrarian effect | loser-minus-winner portfolios are positive for most J/K cells |
| Long-term contrarian effect | J or K longer than 12 months is more stable and statistically significant |
| Short-term contrarian effect | `J=1, K=1` is positive; short-term result is more regime-sensitive |
| Intermediate horizon | `J=6` or `J=12` cells are weaker and often insignificant |
| Loser leg contribution | loser portfolios outperform winner portfolios; long-only loser leg contributes most of L-minus-W return |
| Grouping resolution | decile grouping outperforms quintile and tertile grouping in long horizons |
| State dependence | long-term contrarian survives both bullish and bearish states; short-term contrarian is stronger in bearish states |
| One-month skip robustness | `J=1,K=1` return declines but remains positive; long-horizon contrarian remains robust |
| SHSE/SZSE comparison | most exchange-level differences are not significant |

Local replication is not expected to match the paper's magnitudes because it uses a different universe, later sample, local provider fields, and explicit after-cost diagnostics. The target is to test whether the paper's ordering survives locally:

```text
loser > winner
contrarian_L_minus_W > 0
long-horizon contrarian stronger than intermediate-horizon contrarian
decile grouping stronger than coarser grouping in long horizons
short-term contrarian more state-sensitive than long-term contrarian
```

## 4. EP5 Universe And Data Inheritance

The replication must inherit EP5's local universe and timing discipline:

| Component | Required path / value |
|:--|:--|
| Qlib provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` |
| PIT industry membership | `data/targets/pit_industry_membership.csv` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` |
| Qlib instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` |
| Market benchmark / state benchmark | `SH000300` |
| Market benchmark feature directory | `data/qlib/cn_data_pit/features/sh000300` |
| Provider load end | `2026-04-30` |

Current PIT data snapshot used to calibrate this requirement:

| Actual local object | Current value |
|:--|:--|
| Trading calendar range | `2017-01-03` to `2026-04-30` |
| PIT universe membership range | `2017-07-04` to `2026-04-30` |
| Monthly PIT endpoints | `106` calendar months, `2017-07` to `2026-04` |
| Instruments ever in PIT file | `539` |
| Instruments on first PIT month-end `2017-07-31` | `143` |
| Instruments on provider end `2026-04-30` | `296` |
| Exchange split on `2026-04-30` | `SH=188`, `SZ=108` |
| Instrument map exchange field | available as `SH` / `SZ` in `data/universe/pit_qlib_instrument_universe.csv` |

These values are descriptive guardrails from the current local PIT files. The implementation must recompute and record the same snapshot in `r08_monthly_contrarian_run_manifest.json`; if the local data is refreshed, gate feasibility must be recomputed from the refreshed provider end instead of hard-coding the counts above.

The universe is:

```text
PIT mcap500 mainboard universe as of each monthly signal date.
```

Constituent eligibility on each monthly signal date must require:

1. instrument is a PIT universe member as of the signal date;
2. instrument has enough historical monthly close observations for the relevant J window;
3. instrument has enough price observations to compute the prior J-month ranking return;
4. instrument has valid signal-date close and volume/money fields for tradability diagnostics;
5. no stock outside the PIT universe may enter any portfolio;
6. all joins must be keyed by `date + instrument`.

The ranking denominator close at `M_{t-J}` may come from a date when the instrument was not yet a PIT universe member, provided that the instrument is a PIT member at signal date `M_t` and provider price data exists at `M_{t-J}`. If the provider close at `M_{t-J}` is missing, non-finite, or not loaded for that instrument, the instrument-month is blocked for that J and must be counted in the J-window feasibility audit.

Forward holding-period price availability must not be used in signal-date eligibility, ranking, or leg assignment. Future label availability is evaluated only after a portfolio is fixed and must be reported separately with:

```text
signal_eligibility_status
holding_label_status
assigned_leg_count
label_evaluable_leg_count
```

The universe is not the old `selected` 36-stock pool and not the static `mcap500_mainboard_20251231` Explore1 universe.

## 5. Local Data Availability Contract

Local data scan assumptions inherited from EP6 replica work:

| Local source | Available fields |
|:--|:--|
| `data/qlib/cn_data_pit/features/*` | `open`, `close`, `high`, `low`, `volume`, `money`, `factor` |
| `data/universe/pit_mcap500_mainboard_daily.csv` | PIT membership, `total_share`, `market_cap_asof_T`, listing/status metadata |
| `data/targets/pit_industry_membership.csv` | PIT industry membership |
| `data/qlib/cn_data_pit/features/sh000300` / `data/targets/target_history.csv` | SH000300 index OHLCV |

Required paper inputs and local decisions:

| Paper input | Local action | Reason |
|:--|:--|:--|
| monthly adjusted stock returns | `retain_local_proxy` | provider close is used under local price-adjustment contract |
| SHSE/SZSE exchange split | `retain_local_proxy` | current instrument map contains auditable `exchange` values `SH` / `SZ`; if a future map lacks this field, downgrade only the exchange diagnostic |
| full all-A-share universe | `remove` | local PIT mcap500 mainboard universe is mandatory |
| IPO first-month exclusion | `retain_local_proxy` | current PIT universe is already filtered to `listing_age_trading_days >= 120`; this satisfies local IPO-first-month exclusion but is not paper-equivalent raw IPO-month deletion |
| market state | `retain_local_proxy` | use SH000300 monthly cumulative return states |
| one-month skip robustness | `retain` | implementable from monthly close series, but primary scope is paper-style `J=K` robustness |

The run must create a local data availability manifest:

`r08_input_availability_manifest.csv`

The run must also create an IPO/listing-age audit:

`r08_pit_listing_age_ipo_audit.csv`

Required fields:

```text
split
date_min
date_max
row_count
instrument_count
listing_age_min
listing_age_p01
listing_age_median
listing_age_rows_lt_20
listing_age_rows_lt_120
local_ipo_first_month_exclusion_status
```

For the current local PIT snapshot, `local_ipo_first_month_exclusion_status` is expected to be:

```text
satisfied_by_pit_listing_age_min_120
```

Input availability manifest required columns:

```text
input_id
paper_required_input
local_source
availability_status
replication_action
local_proxy_id
asof_policy
coverage_train_months
coverage_validation_months
coverage_robustness_months
block_reason
```

Allowed `availability_status` values:

```text
available_full
available_partial
missing_required_exchange_mapping
missing_required_listing_metadata
missing_required_price_fields
missing_asof_timestamp
blocked_not_reproducible
```

Allowed `replication_action` values:

```text
retain
retain_local_proxy
remove
diagnostic_only
```

Local price-adjustment contract:

```text
price_adjustment_mode = provider_ohlc_already_adjusted
primary_return_price = close from Qlib provider
do_not_reapply_factor_day_bin_to_ohlc = true
```

The local `factor` field may be used only as an audit field to confirm provider lineage. It must not be multiplied into OHLC prices in this requirement.

`money` is the local turnover amount field. Implementations must not silently substitute `amount` or another provider-specific alias.

## 6. Monthly Calendar And Sample Split

Monthly endpoints must be derived from the local trading calendar:

```text
calendar_month_id = YYYY-MM
month_end M_t =
  max(local trading-calendar day in calendar_month_id)

monthly_close_{i,t} =
  provider close for instrument i on M_t

monthly_return_{i,t} =
  monthly_close_{i,t} / monthly_close_{i,t-1} - 1
```

If an instrument has no valid close on `M_t` or the immediately preceding calendar month-end `M_{t-1}`, the instrument-month is missing. Missing instrument-month returns must not be filled with zero and must not be compressed to the previous retained valid month.

Ranking and holding without skip:

```text
formation window for signal month t:
  months t-J+1 through t

holding window for K-month return:
  months t+1 through t+K

portfolio construction date:
  M_t close
```

Ranking and holding with one-month skip:

```text
formation window for signal month t:
  months t-J+1 through t

skip month:
  month t+1

holding window for K-month return:
  months t+2 through t+K+1

portfolio construction date:
  M_t close
```

Portfolio construction may only use data available no later than `M_t`.

The local evaluation split is:

| Split | Calendar window | Notes |
|:--|:--|:--|
| price_history_warmup | `2017-01-03` to `2017-07-03` | provider price history may be used only as ranking-return denominator history; no PIT signal universe is available before `2017-07-04` |
| pit_signal_warmup | `2017-07-04` to cell-specific first evaluable signal month | used only for return-history formation and early portfolio warmup; first evaluable signal month is measured separately by J and by J/K feasibility tables |
| train | `2018-07-01` to `2021-12-31` | nominal train window; cell-specific evaluable start may be later |
| validation | `2022-01-01` to `2023-12-31` | primary out-of-sample decision window |
| robustness | `2024-01-01` to `2025-12-31` | post-validation robustness window |

Long formation windows may become evaluable after the nominal train start. In particular, `J=48` requires 48 complete prior monthly returns. The implementation must not backfill or relax history requirements to force train-start availability. Instead, it must compute and publish:

```text
first_evaluable_signal_month_by_J
first_evaluable_signal_month_by_JK
first_evaluable_portfolio_month_by_JK
effective_split_start_by_JK
train_months_lost_to_warmup_by_JK
```

`first_evaluable_signal_month_by_J` is the first signal month where at least one grouping method has enough PIT signal-date members with valid `M_t` and `M_{t-J}` closes and passes the minimum portfolio coverage rules before holding-label checks. `first_evaluable_signal_month_by_JK` additionally requires that the corresponding K-month holding label can be completed before provider end for the split under evaluation.

Split assignment is based on the first month of the holding window. If a J/K portfolio cannot complete the full holding window before provider end, mark:

```text
holding_status = blocked_incomplete_future_return_label
```

and exclude that portfolio-month from metrics. Do not impute missing holding returns.

Primary split metrics use a fixed vintage-pool policy:

```text
split_vintage_policy = first_holding_month_fixed_vintage_pool

vintage belongs to split S if:
  first_holding_month is inside split S

primary split calendar-time return series for S:
  use only active vintages assigned to split S
  include their realized holding-month returns through the full K-month window
  do not include carry-in vintages whose first_holding_month is before split S
```

This means a validation vintage that starts near the end of validation may contribute realized return months after the validation calendar end if its full K-month label is complete before provider end. The split summary must therefore report both:

```text
first_holding_month_min
first_holding_month_max
return_calendar_month_min
return_calendar_month_max
return_calendar_months_beyond_split_end_count
carry_in_vintage_count
```

`carry_in_vintage_count` must be zero for the primary split metrics. A separate carry-in calendar-month diagnostic may be reported, but it must not replace the primary metrics or gate decision.

Under the current provider end `2026-04-30`, completed holding-label coverage by first holding month is materially different across K. Before applying any gate, the implementation must publish `r08_provider_end_feasibility_by_K.csv` with at least:

```text
split
K
first_holding_month_count_with_complete_label
first_evaluable_first_holding_month
last_evaluable_first_holding_month
provider_end_month
```

The implementation must also publish `r08_signal_history_feasibility_by_JK.csv` with at least:

```text
split
J
K
signal_month_count
first_evaluable_signal_month
last_evaluable_signal_month
first_holding_month_count_with_complete_label
first_evaluable_first_holding_month
last_evaluable_first_holding_month
median_signal_eligible_instrument_count
min_signal_eligible_instrument_count
median_rank_denominator_missing_count
min_intermediate_month_coverage_share
blocked_reason
```

The current PIT provider implies the following feasibility pattern for the configured splits:

| Split | K=1 | K=6 | K=12 | K=18 | K=24 | K=30 | K=36 | K=42 | K=48 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| validation `2022-2023` | 24 | 24 | 24 | 24 | 24 | 23 | 17 | 11 | 5 |
| robustness `2024-2025` | 24 | 23 | 17 | 11 | 5 | 0 | 0 | 0 | 0 |

Therefore full paper-grid long-holding windows `K>=18` are descriptive under the current local provider and must not be used as the primary robustness gate. The primary local decision cluster is defined in Section 14 from locally complete windows.

## 7. Signal Definitions

Canonical J values:

```text
1, 6, 12, 18, 24, 30, 36, 42, 48 months
```

Canonical K values:

```text
1, 6, 12, 18, 24, 30, 36, 42, 48 months
```

Canonical grouping methods:

```text
tertile = 3 groups
quintile = 5 groups
decile = 10 groups
```

Prior J-month ranking return:

```text
rank_return_{i,t,J} =
  monthly_close_{i,t} / monthly_close_{i,t-J} - 1
```

This formula requires valid closes at `M_t` and `M_{t-J}`. A diagnostic compounded monthly-return equivalent may be reported, but the primary ranking formula must be frozen before validation metrics are computed.

The primary ranking formula is intentionally a single-pair J-month return, but it must pass a light intermediate-history sanity check:

```text
intermediate_months_checked = months t-J+1 through t-1
intermediate_month_count = count(intermediate_months_checked)
min_valid_intermediate_monthly_closes_required =
  min(ceil(J * 0.50), intermediate_month_count)
```

If an instrument has fewer than this number of valid intermediate month-end closes between the denominator and signal month, block the instrument-month for that J with:

```text
rank_history_status = blocked_insufficient_intermediate_monthly_close_coverage
```

This check prevents a stock with only two distant endpoint prices and a mostly missing intermediate history from entering the rank sort.

Holding K-month realized return without skip:

```text
holding_return_{i,t,K} =
  monthly_close_{i,t+K} / monthly_close_{i,t} - 1
```

Holding K-month realized return with one-month skip:

```text
holding_return_skip1_{i,t,K} =
  monthly_close_{i,t+K+1} / monthly_close_{i,t+1} - 1
```

If `M_{t+1}` is missing for an instrument in the skip-one-month variant, mark the instrument's holding label as missing after portfolio assignment. Do not remove it before ranking.

## 8. Portfolio Construction Rules

For each no-skip signal month `t`, J, K, and grouping method `G`:

1. Build eligible stock universe from EP5 PIT universe as of `M_t`.
2. Drop instruments only for insufficient as-of formation price data or invalid ranking return.
3. Sort by `rank_return_{i,t,J}` using deterministic tie rules:

```text
sort by rank_return ascending, stable_hash_tiebreak ascending
split into G near-equal buckets
```

The stable tiebreak must be frozen before validation metrics are computed:

```text
stable_hash_tiebreak =
  sha256(requirement_id + "|" + instrument_id + "|" + signal_month + "|" + J + "|" + grouping_method + "|" + tiebreak_seed)

tiebreak_seed:
  frozen in configs/r08_monthly_contrarian_strategy_replication_v0.yaml
```

Do not use raw instrument string ordering as the primary tie-break because it can introduce exchange-prefix ordering artifacts.

4. Define:

```text
loser_leg = lowest rank_return bucket
winner_leg = highest rank_return bucket
```

5. Assign equal weights within each leg at the signal date.
6. Compute realized holding returns after assignment using the relevant K-month holding window.

For one-month skip robustness, repeat the same construction only for the paper-style diagonal grid:

```text
skip1_scope = J_equals_K_only
skip1_JK_values = {1, 6, 12, 18, 24, 30, 36, 42, 48}
```

Full varying-J/K skip-one-month results may be added only as optional diagnostic output and must not enter the primary gate.

Primary long-short return conventions:

```text
winner_return_W =
  equal-weight holding return of winner_leg

loser_return_L =
  equal-weight holding return of loser_leg

contrarian_return_L_minus_W =
  loser_return_L - winner_return_W

momentum_return_W_minus_L =
  winner_return_W - loser_return_L
```

The primary stored long-short series is `contrarian_return_L_minus_W`. The momentum view is a deterministic sign flip used only for diagnostic interpretation.

Minimum portfolio coverage:

```text
signal_eligible_instrument_count >= 120
decile_leg_assigned_count_min >= 10
quintile_leg_assigned_count_min >= 15
tertile_leg_assigned_count_min >= 20
label_evaluable_leg_count_min >= 5 per leg
label_evaluable_leg_share_min >= 0.60 per assigned leg
```

If a portfolio-month fails coverage, set:

```text
portfolio_month_status = blocked_insufficient_portfolio_coverage
```

Coverage failures after leg assignment must not rewrite the original signal membership. They only determine whether that portfolio-month contributes to return metrics.

The implementation must report block counts separately by split, grouping method, skip mode, J, K, and block reason:

```text
insufficient_signal_eligible_universe
assigned_leg_too_small
label_evaluable_leg_count_too_small
label_evaluable_leg_share_too_low
blocked_incomplete_future_return_label
```

## 9. Overlapping Holding Accounting

For K greater than 1, portfolio returns must be computed as calendar-time overlapping portfolios rather than a single non-overlapping sequence.

Vintage accounting:

```text
vintage_signal_month = s
vintage_holding_months_without_skip = s+1 through s+K
vintage_holding_months_skip1 = s+2 through s+K+1

active_vintages_for_calendar_month h =
  all vintages s where h is inside the vintage holding window

calendar_month_return_h =
  equal-weight average of active vintage monthly returns realized in h
```

Each vintage target weight vector is equal-weight inside its assigned long and short legs. The primary calendar-time return is computed from monthly returns of the fixed vintage legs, not by spreading or reusing the K-month cumulative holding return.

For each active vintage `s` and calendar holding month `h`:

```text
vintage_loser_month_return_{s,h} =
  equal-weight mean over original loser_leg_s of:
    close_{i,h} / close_{i,h-1} - 1

vintage_winner_month_return_{s,h} =
  equal-weight mean over original winner_leg_s of:
    close_{i,h} / close_{i,h-1} - 1

vintage_contrarian_month_return_{s,h} =
  vintage_loser_month_return_{s,h}
  - vintage_winner_month_return_{s,h}

vintage_momentum_month_return_{s,h} =
  - vintage_contrarian_month_return_{s,h}
```

If an instrument assigned to a vintage lacks the month `h-1 -> h` return, keep the original assigned leg unchanged, mark that instrument-month's `holding_label_status`, and compute the leg return only if the label-evaluable leg count and share thresholds pass.

If fewer than K vintages are active because the sample is warming up, average over active vintages and record:

```text
active_vintage_count
expected_vintage_count = K
vintage_warmup_status
```

The implementation must publish both:

```text
vintage-level K-month cumulative holding return diagnostics
vintage-level monthly holding return diagnostics
calendar-time overlapping monthly return series
```

Primary split metrics and t-statistics must be computed from the calendar-time overlapping monthly return series.

## 10. Cost And Executability Diagnostics

Paper-style replication must report gross returns first. Because the local run reconstructs stock portfolios, after-cost diagnostics are mandatory unless the run is data-blocked before portfolio construction.

EP5-style transaction-cost assumptions:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
execution_mode = monthly_stock_constituent_replay_after_cost_mode
drift_adjusted_weights_reported = false by default
```

These cost values inherit the local EP5/EP6 diagnostic convention. The implementation must cross-check the frozen config against the active local cost convention used in EP5/EP6 configs:

```text
ep5_cost_contract_reference = ep5/configs/r08_h3_volume_price_single_stock_state_transferability_audit_v0.yaml
ep6_cost_contract_reference = ep6/configs/r07_weekly_imom_horse_race_v0.yaml
cost_contract_status = matched | mismatched_requires_manual_review
```

For each calendar-month replayed portfolio:

```text
vintage_signed_weight_{i,s,h} =
  +1 / loser_leg_count_s   if i is in loser_leg_s and h is an active holding month for vintage s
  -1 / winner_leg_count_s  if i is in winner_leg_s and h is an active holding month for vintage s
   0 otherwise

active_vintage_count_h =
  count of vintages active in calendar month h for the split and J/K/grouping family

combined_signed_weight_{i,h} =
  sum over active vintages s of vintage_signed_weight_{i,s,h}
  / active_vintage_count_h

buy_turnover_t =
  sum positive changes from previous combined signed stock weights to current combined signed stock weights

sell_turnover_t =
  sum absolute negative changes from previous combined signed stock weights to current combined signed stock weights

first_active_month_previous_weight = 0

vintage_entry_timing =
  a vintage enters combined weights at the close before its first holding month

vintage_exit_timing =
  a vintage exits combined weights at the close after its final holding month;
  the weight decrease from exiting vintages is included in sell_turnover_t for the first month in which they are no longer active

after_cost_return_t =
  gross_return_t
  - buy_turnover_t * 30bps
  - sell_turnover_t * 80bps
```

The cost replay is a diagnostic, not a deployability claim. The final report must explicitly identify:

```text
gross paper-style diagnostic
after-cost executability diagnostic
long-only loser leg
long-short contrarian L-minus-W book
months requiring short exposure
```

The final report must not assume shorting is freely available in A shares. Any positive long-short result remains diagnostic unless a later requirement defines a feasible long-only or hedge-instrument implementation.

If the implementation cannot reconstruct stock-level turnover for a non-data-blocked run, final decision must be downgraded to:

```text
ep6_monthly_contrarian_execution_replay_blocked
```

## 11. State And Exchange Diagnostics

The paper uses a 1997-2007 bullish subperiod and a 2007-2012 bearish/adjustment subperiod. The local sample cannot reuse those paper dates. Local state diagnostics must therefore be defined from SH000300.

Sign-based market state definitions use a fixed zero threshold:

```text
market_state_12m_up:
  cumulative SH000300 return over prior 12 months > 0

market_state_12m_down:
  cumulative SH000300 return over prior 12 months <= 0

market_state_24m_up:
  cumulative SH000300 return over prior 24 months > 0

market_state_24m_down:
  cumulative SH000300 return over prior 24 months <= 0
```

Train-threshold regime buckets are separate from the sign-based states:

```text
sh000300_prior_12m_return_train_percentile:
  compute train-only 33rd and 67th percentile thresholds

weak_market:
  prior 12m SH000300 return <= train 33rd percentile

middle_market:
  prior 12m SH000300 return between train 33rd and 67th percentile

strong_market:
  prior 12m SH000300 return >= train 67th percentile
```

Because the train-period monthly state sample is short, the implementation must report percentile-threshold uncertainty:

```text
train_pctile_bootstrap_ci:
  bootstrap train monthly state observations with replacement
  bootstrap_iterations = 1000
  random_seed frozen in YAML
  report 33rd and 67th percentile threshold p05 / p50 / p95
```

Exchange diagnostics are retained only if exchange mapping is available:

```text
raw_exchange = SH | SZ | unknown
exchange_group = SHSE | SZSE | unknown

mapping:
  SH -> SHSE
  SZ -> SZSE
```

If exchange mapping is unavailable or unreliable, the run must not infer exchange from ambiguous identifiers. Instead set:

```text
exchange_diagnostic_status = blocked_missing_required_exchange_mapping
```

State and exchange diagnostics are explanatory. They must not override the primary validation decision.

## 12. Required Artifacts

The implementation must create:

```text
ep6/outputs/r08_monthly_contrarian_strategy_replication_v0/
  configs/
    r08_monthly_contrarian_strategy_replication_v0.yaml
  manifests/
    r08_input_availability_manifest.csv
    r08_monthly_contrarian_run_manifest.json
    r08_environment_snapshot.json
    r08_price_adjustment_audit.csv
    r08_provider_end_feasibility_by_K.csv
    r08_signal_history_feasibility_by_JK.csv
    r08_pit_listing_age_ipo_audit.csv
  validation/
    r08_validation_manifest.json
  calendar/
    r08_monthly_calendar.csv
    r08_monthly_stock_returns.parquet
    r08_monthly_signal_eligibility_audit.csv
  signals/
    r08_rank_return_signal_panel.parquet
    r08_bucket_assignment_panel.parquet
  returns/
    r08_vintage_holding_returns.csv
    r08_vintage_monthly_returns.csv
    r08_calendar_time_portfolio_returns.csv
    r08_portfolio_month_label_status.csv
    r08_after_cost_returns.csv
  reports/
    r08_jk_summary_decile.csv
    r08_jk_summary_quintile.csv
    r08_jk_summary_tertile.csv
    r08_grouping_relative_performance_summary.csv
    r08_skip1_robustness_summary.csv
    r08_state_conditional_summary.csv
    r08_state_threshold_bootstrap_ci.csv
    r08_exchange_conditional_summary.csv
    r08_loser_winner_leg_summary.csv
    r08_paper_reference_comparison.csv
    r08_gate_decision_summary.csv
    r08_final_report.md
```

Parquet may be replaced by CSV only if the implementation records the reason in `r08_monthly_contrarian_run_manifest.json`.

If data is blocked, the run must still produce:

```text
manifests/r08_input_availability_manifest.csv
manifests/r08_monthly_contrarian_run_manifest.json
reports/r08_final_report.md
validation/r08_validation_manifest.json
```

## 13. Required Metrics

Each no-skip J/K/grouping portfolio family and each skip1 `J=K` grouping portfolio family must report by split:

```text
month_count
active_portfolio_count
active_vintage_count_mean
signal_eligible_instrument_count_mean
signal_eligible_instrument_count_min
assigned_loser_leg_count_mean
assigned_winner_leg_count_mean
label_evaluable_loser_leg_count_mean
label_evaluable_winner_leg_count_mean
label_evaluable_loser_leg_share_mean
label_evaluable_winner_leg_share_mean
loser_monthly_mean_return
winner_monthly_mean_return
contrarian_monthly_mean_return
momentum_monthly_mean_return
loser_annualized_mean_return = loser_monthly_mean_return * 12
winner_annualized_mean_return = winner_monthly_mean_return * 12
contrarian_annualized_mean_return = contrarian_monthly_mean_return * 12
monthly_volatility
annualized_volatility = monthly_volatility * sqrt(12)
sharpe_ratio
t_stat_monthly_mean_newey_west
newey_west_lag_used = min(K - 1, month_count - 1)
newey_west_lag_alternative = floor(4 * (month_count / 100) ** (2 / 9))
t_stat_monthly_mean_newey_west_alternative
positive_month_share
max_drawdown
first_holding_month_min
first_holding_month_max
return_calendar_month_min
return_calendar_month_max
return_calendar_months_beyond_split_end_count
carry_in_vintage_count
mean_buy_turnover
mean_sell_turnover
after_cost_monthly_mean_return
after_cost_annualized_mean_return
after_cost_t_stat_newey_west
after_cost_sharpe_ratio
loser_long_only_after_cost_monthly_mean_return
loser_long_only_after_cost_annualized_mean_return
loser_long_only_after_cost_t_stat_newey_west
months_requiring_short_exposure
```

Primary summary rows:

```text
decile_contrarian_L_minus_W
quintile_contrarian_L_minus_W
tertile_contrarian_L_minus_W
decile_loser_long_only
decile_winner_long_only
decile_momentum_W_minus_L
decile_contrarian_L_minus_W_skip1_J_equals_K
```

The final report must include a compact paper-reference comparison table:

| Paper claim | Local test | Supported locally? |
|:--|:--|:--|
| loser portfolios outperform winner portfolios | loser vs winner leg summary | yes/no/mixed |
| long-horizon contrarian is positive | full paper-grid descriptive summary for `K>=18` where labels are complete; primary local cluster tests long-formation `J>=18` with locally complete `K in {1,6,12}` and is not paper-equivalent long-holding robustness | yes/no/mixed |
| short-term `J=1,K=1` contrarian is positive | decile/quintile/tertile `1,1` summary | yes/no/mixed |
| intermediate `J=6/12` region is weaker | grouped J/K heatmap comparison | yes/no/mixed |
| decile grouping outperforms coarser grouping in long horizons | grouping relative performance summary | yes/no/mixed |
| one-month skip keeps long-term effect robust | skip1 robustness summary | yes/no/mixed |
| weak/bearish states strengthen short-term contrarian | state conditional summary | yes/no/mixed |
| SHSE/SZSE differences are limited | exchange conditional summary | yes/no/mixed/unavailable |

## 14. Validation Gates

This requirement has no strategy-authorization gate. It has only diagnostic gates.

The full paper grid remains required as a descriptive diagnostic:

```text
full_paper_grid_descriptive:
  J in {1, 6, 12, 18, 24, 30, 36, 42, 48}
  K in {1, 6, 12, 18, 24, 30, 36, 42, 48}
  grouping in {decile, quintile, tertile}

paper_long_holding_cells:
  K in {18, 24, 30, 36, 42, 48}
  report coverage and returns when complete labels exist
  do not use as primary robustness gate under current provider end
```

Primary local cluster aggregation is fixed from currently feasible PIT coverage. It is a long-formation / locally complete holding-window diagnostic, not a paper-equivalent long-holding robustness gate:

```text
short_cluster:
  J in {1}, K in {1}

intermediate_cluster:
  J in {6, 12}, K in {6, 12}

primary_local_decision_cluster:
  J in {18, 24, 30, 36, 42, 48}
  K in {1, 6, 12}

canonical_primary_grouping:
  decile

primary_local_decision_cell_count:
  18

primary_local_decision_family_mean =
  equal-weight mean of contrarian_monthly_mean_return across evaluable primary local decision J/K cells

primary_local_decision_family_after_cost_mean =
  equal-weight mean of after_cost_monthly_mean_return across evaluable primary local decision J/K cells
```

Data sufficiency gate:

```text
validation_evaluable_primary_local_decision_cell_count >= 15
robustness_evaluable_primary_local_decision_cell_count >= 15
validation_primary_local_decision_min_month_count_per_cell >= 12
robustness_primary_local_decision_min_month_count_per_cell >= 12
```

The intended primary local decision grid has 18 cells. The gate allows up to 3 cells to be unavailable because J-window history may be missing for late entrants or incomplete provider histories. Missing cells must be identified in `r08_signal_history_feasibility_by_JK.csv`; they cannot be silently dropped from the denominator.

Primary long-formation local contrarian diagnostic gate:

```text
validation_primary_local_decision_decile_contrarian_mean > 0
validation_primary_local_decision_decile_contrarian_t_stat_newey_west > 0
validation_primary_local_decision_decile_loser_mean > validation_primary_local_decision_decile_winner_mean

robustness_primary_local_decision_decile_contrarian_mean > 0
robustness_primary_local_decision_decile_contrarian_t_stat_newey_west > 0
robustness_primary_local_decision_decile_loser_mean > robustness_primary_local_decision_decile_winner_mean
```

Grouping-resolution support gate:

```text
validation_primary_local_decision_decile_contrarian_mean
  >= validation_primary_local_decision_tertile_contrarian_mean

robustness_primary_local_decision_decile_contrarian_mean
  >= robustness_primary_local_decision_tertile_contrarian_mean
```

Quintile grouping remains a required descriptive diagnostic but does not need to sit monotonically between decile and tertile in both splits. The report must still show:

```text
validation_primary_local_decision_quintile_contrarian_mean
robustness_primary_local_decision_quintile_contrarian_mean
quintile_between_decile_and_tertile_status = yes | no
```

Short-term diagnostic is report-only:

```text
short_term_decile_1_1_contrarian_supported =
  validation_decile_J1_K1_contrarian_mean > 0
  and robustness_decile_J1_K1_contrarian_mean > 0
```

The short-term diagnostic must not override the final decision because the paper itself treats short-horizon behavior as more regime-sensitive and more exposed to measurement issues.

After-cost diagnostic guard:

```text
validation_primary_local_decision_decile_after_cost_mean > 0
robustness_primary_local_decision_decile_after_cost_mean > 0
```

Long-only loser after-cost evidence is diagnostic and must not override the long-short final decision:

```text
validation_primary_local_decision_decile_loser_long_only_after_cost_mean > 0
robustness_primary_local_decision_decile_loser_long_only_after_cost_mean > 0
loser_long_only_after_cost_positive_tag =
  positive_both_splits | validation_only | robustness_only | not_positive
```

If long-short after-cost fails but loser long-only after-cost is positive in both splits, keep the machine-readable final decision at `ep6_monthly_contrarian_gross_positive_after_cost_not_supported` and add the report interpretation label:

```text
loser_long_only_after_cost_positive_followup_candidate
```

First-match final decision priority:

```text
1. If required local price inputs or PIT universe are unavailable:
   ep6_monthly_contrarian_data_blocked

2. Else if portfolio replay, overlapping vintage accounting, or after-cost replay cannot be produced:
   ep6_monthly_contrarian_execution_replay_blocked

3. Else if data sufficiency gate fails:
   ep6_monthly_contrarian_sample_insufficient

4. Else if primary local decision contrarian validation gate fails:
   ep6_monthly_contrarian_local_proxy_not_supported

5. Else if validation passes but robustness primary local decision gate fails:
   ep6_monthly_contrarian_validation_only_not_robust

6. Else if primary local contrarian is positive but grouping-resolution support fails:
   ep6_monthly_contrarian_positive_grouping_order_not_supported

7. Else if primary local decision gates pass but after-cost guard fails:
   ep6_monthly_contrarian_gross_positive_after_cost_not_supported

8. Else:
   ep6_monthly_contrarian_local_proxy_positive_diagnostic_only
```

Weak or mixed support may be used only as a report interpretation label, not as the machine-readable final decision.

If the final decision is positive but individual primary local decision cells are mixed in sign or significance, the report must add:

```text
ep6_monthly_contrarian_local_proxy_mixed_positive_diagnostic
```

Even if all diagnostic gates pass, the final report must state:

```text
authorized_strategy_requirement = false
```

## 15. Reproducibility Rules

All configuration choices must be frozen in:

```text
configs/r08_monthly_contrarian_strategy_replication_v0.yaml
```

before validation and robustness metrics are computed.

The run manifest must record:

```text
git_commit_or_worktree_status
created_at
python_version
qlib_version
pandas_version
numpy_version
qlib_provider_path
universe_path
calendar_path
benchmark_feature_dir
benchmark_feature_dir_hash
provider_end_month
pit_universe_actual_snapshot
provider_end_feasibility_by_K
local_ipo_first_month_exclusion_status
price_adjustment_mode
J_values
K_values
grouping_methods
skip_modes
skip1_scope
tiebreak_seed
bootstrap_seed
split_boundaries
monthly_calendar_policy
ranking_return_formula
rank_history_intermediate_coverage_policy
holding_return_formula
overlapping_vintage_accounting_policy
split_vintage_policy
primary_local_decision_cluster
paper_grid_descriptive_policy
label_availability_policy
newey_west_lag_policy
sign_state_definition_policy
train_percentile_state_definition_policy
train_pctile_bootstrap_ci_policy
exchange_mapping_status
exchange_mapping_policy
cost_assumptions
cost_contract_status
blocked_inputs
final_decision
```

`r08_environment_snapshot.json` must include at least:

```text
python_version
qlib_version
pandas_version
numpy_version
platform
executable
package_freeze
git_commit_or_worktree_status
created_at
```

`r08_gate_decision_summary.csv` must be validator-readable. Its first row must contain one boolean or scalar column per gate input:

```text
data_inputs_available
portfolio_replay_available
after_cost_replay_available
validation_evaluable_primary_local_decision_cell_count
robustness_evaluable_primary_local_decision_cell_count
validation_primary_local_decision_min_month_count_per_cell
robustness_primary_local_decision_min_month_count_per_cell
validation_primary_local_decision_decile_contrarian_mean
robustness_primary_local_decision_decile_contrarian_mean
validation_primary_local_decision_decile_contrarian_t_stat_newey_west
robustness_primary_local_decision_decile_contrarian_t_stat_newey_west
validation_primary_local_decision_decile_loser_gt_winner
robustness_primary_local_decision_decile_loser_gt_winner
validation_decile_ge_tertile
robustness_decile_ge_tertile
validation_primary_local_decision_decile_after_cost_mean
robustness_primary_local_decision_decile_after_cost_mean
loser_long_only_after_cost_positive_tag
final_decision
interpretation_labels
```

No rule may be tuned after observing validation or robustness returns:

```text
J/K subset
grouping methods
skip-mode inclusion
ranking-return formula
holding-return formula
winsorization
minimum coverage thresholds
cost assumptions
split boundaries
split vintage policy
state thresholds
cluster aggregation
Newey-West lag policy
exchange mapping rule
tiebreak seed
bootstrap seed
```

If a bug fix changes historical metrics, the implementation must regenerate all downstream artifacts and document the change in `r08_validation_manifest.json`.

## 16. Final Report Requirements

The final report must be written in Chinese and include:

1. paper result and exact paper sample used as reference;
   include paper table / column references for each headline comparison where applicable;
2. local EP5 universe and sample differences;
3. local input availability table;
4. monthly calendar, PIT eligibility rules, listing-age / IPO audit, and split vintage policy;
5. J/K/grouping/skip-mode definitions;
6. loser, winner, contrarian, and momentum return conventions;
7. train / validation / robustness metrics;
8. full paper-grid J/K heatmap summary with explicit incomplete-label coverage;
9. short-term `J=1,K=1` diagnostic;
10. intermediate-horizon weakness diagnostic;
11. primary local decision cluster summary using long-formation `J>=18` and locally complete `K in {1,6,12}`, with an explicit note that this is not paper-equivalent long-holding robustness;
12. grouping-resolution comparison;
13. one-month skip `J=K` robustness;
14. state-conditional results;
    include train percentile bootstrap confidence intervals for state thresholds;
15. exchange-conditional results using `SH -> SHSE` and `SZ -> SZSE` mapping, or explicit blocked reason;
16. gross vs after-cost comparison;
17. loser long-only after-cost diagnostic tag and whether it merits a separate long-only follow-up requirement;
18. explicit statement:

```text
This is a local PIT mcap500 monthly contrarian replication diagnostic.
This is not an exact RESSET all-A-share 1997-2012 paper replication.
This is a paper-replication diagnostic only.
It does not authorize strategy construction.
```

## 17. Explicit Prohibitions

The implementation must not:

1. Use the 36-stock `selected` universe.
2. Use the static Explore1 `mcap500_mainboard_20251231` universe.
3. Use future holding-period label availability to alter signal-date membership.
4. Fill missing stock monthly returns with zero.
5. Tune J/K subsets based on validation returns.
6. Tune grouping methods based on validation returns.
7. Tune state thresholds based on validation or robustness returns.
8. Switch from equal-weight primary portfolios to value-weight primary portfolios.
9. Treat a data-blocked run as a negative alpha result.
10. Reapply `factor.day.bin` or the provider `factor` field to OHLC prices under this requirement.
11. Switch `price_adjustment_mode` after observing returns.
12. Infer exchange labels from ambiguous identifiers without an auditable mapping.
13. Claim exact paper replication when using the local PIT mcap500 universe.
14. Use full paper-grid long-holding `K>=18` cells as the primary robustness gate under the current `2026-04-30` provider end.
15. Use raw instrument string ordering as the primary tie-breaker for bucket assignment.
16. Output strategy authorization.

## 18. Implementation Notes

The first implementation should start with the data availability and calendar manifests before building any returns.

Recommended implementation sequence:

```text
1. Load EP5 PIT universe, instrument map, and trading calendar.
2. Load local close, volume, money, and SH000300 benchmark data.
3. Build input availability manifest.
4. Freeze `price_adjustment_mode = provider_ohlc_already_adjusted`.
5. Build monthly calendar and monthly close/return panel.
6. Build rank-return signal panel for all canonical J values.
7. Build J/K signal-history feasibility and provider-end feasibility manifests.
8. Assign tertile, quintile, and decile buckets with deterministic hash tie rules.
9. Publish provider-end feasibility by K and freeze the primary local decision cluster.
10. Build vintage-level loser, winner, and contrarian holding returns for all J/K cells.
11. Convert K-month holdings into calendar-time overlapping monthly return series using vintage monthly returns.
12. Run paper-style one-month skip `J=K` robustness.
13. Compute gross, long-short after-cost, and loser long-only after-cost diagnostics.
14. Compute sign-state, train-percentile-state, train-threshold bootstrap, listing-age / IPO, and exchange diagnostics.
15. Apply gate logic and write validator-readable gate decision summary.
16. Write Chinese final report.
```

The requirement is intentionally strict about local-vs-paper comparison language because a post-2017 PIT mcap500 replay answers a different question from the paper's 1997-2012 all-A-share RESSET study.
