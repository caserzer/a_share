# EP6 Paper Replica Requirement 12: Daily Price Limit Short After Upper Hit V0

## 1. Requirement Metadata

requirement_id: `ep6_paper_replica_12_daily_price_limit_short_after_upper_hit_v0`

short_name: `r12_daily_price_limit_short_after_upper_hit_v0`

status: `requirement-draft`

workflow: `EP6`

created_date: `2026-05-28`

requirement_path: `ep6/papers/replica/requirement_12_daily_price_limit_short_after_upper_hit_v0.md`

source_paper:

- local_pdf: `ep6/papers/12_daily_price_limits_and_destructive_market_behavior_chen_gao_he_jiang_xiong_2017.pdf`
- title: `Daily Price Limits and Destructive Market Behavior`
- authors: `Ting Chen, Zhenyu Gao, Jibao He, Wenxi Jiang, Wei Xiong`
- version: `NBER Working Paper 24014`
- paper_date: `2017-11`
- paper_sample: `Shenzhen Stock Exchange A-share stocks, account-level trading data, 2012-2015`

primary_output_namespace: `ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/`

authorization_scope:

```text
authorized_strategy_requirement = false
```

This requirement is a paper-inspired diagnostic contract only. It tests whether the paper's documented post-upper-limit reversal can be expressed as a local public-price short-after-涨停 proxy. It must not be interpreted as permission to trade short A-share books, because local data does not contain securities-lending availability, borrow fees, forced-buy-in rules, or account-level execution constraints.

## 2. Research Positioning

The source paper shows that daily price limits may induce destructive market behavior: large investors buy on the day a stock closes at the 10% upper price limit and sell on the next day, and stronger large-investor net buying predicts stronger long-run reversal.

The local research question is:

```text
Using the EP5 PIT mcap500 mainboard universe,
does shorting a stock after it closes at the regular 10% upper price limit
produce a positive out-of-sample reversal diagnostic,
and is that result stronger than shorting non-limit high-return stocks?
```

This is not an exact replication of the paper. The local repository does not have:

```text
SZSE account-level investor-group transactions
large-investor NetBuy by stock-day
CSMAR market-to-book controls
complete historical 2012-2015 SZSE account sample
raw exchange shortability / borrow inventory data
intraday order-book data at the limit price
```

Therefore the requirement is:

```text
paper-inspired public-price reversal diagnostic
not account-level destructive-trading replication
not executable short-sale authorization
```

Every final report under this requirement must include the caveat:

```text
local_short_after_limit_up_proxy_not_account_level_paper_replication
```

## 3. Paper Result To Reproduce Directionally

The paper's main setup:

```text
Data:
  SZSE account-level transactions and daily stock data, 2012-2015

Regular stocks:
  daily price limit = 10%

ST stocks:
  daily price limit = 5%

Investor groups:
  institutions plus five individual-account groups by prior-year average stock balance

Large investor group:
  individual accounts with stock balance above RMB 10 million

Primary mechanism:
  large investors buy on upper-limit day D
  large investors sell on D+1
  stronger large-investor buying on D predicts stronger long-run reversal
```

Directional targets for local public-price replication:

| Paper result | Local diagnostic target |
|:--|:--|
| upper-limit close is followed by next-open continuation | `D close -> D+1 open` return is positive for upper-hit events |
| continuation reverses over longer windows | short return from `D+1 open` to later close is positive for H in `{5, 10, 20, 60, 120}` |
| upper-limit events differ from near-limit high-return events | short-after-upper-hit outperforms short-after-nonlimit-high-return comparator |
| large-investor selling occurs on D+1 | local proxy starts at `D+1 open`; account-level selling itself is not observable |
| tighter ST limits strengthen the mechanism | ST 5% upper-hit analysis is diagnostic only if local ST status proxy is reliable |
| lower-limit side is not symmetric because shorting is constrained | this requirement does not infer a deployable long/short symmetric strategy |

The local strategy direction is intentionally contrarian:

```text
event: stock closes at upper price limit on D
primary entry: short at D+1 open if locally tradable
primary exits: D+5 close, D+10 close, D+20 close
long-run diagnostics: D+60 close and D+120 close if label-complete
```

The paper does not prove that a public investor can profitably short after the event. This requirement tests that implication locally and separately records execution blockers.

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
| Market benchmark | `SH000300` |
| Market benchmark feature directory | `data/qlib/cn_data_pit/features/sh000300` |
| Provider load end | `2026-04-30` |

Current PIT data snapshot assumptions inherited from adjacent EP6 replica work:

```text
trading calendar starts no later than 2017-01-03
PIT signal universe starts on 2017-07-04
provider load end is 2026-04-30
local universe is PIT mcap500 mainboard, not all A shares
```

The implementation must recompute and record the actual snapshot in:

```text
r12_run_manifest.json
```

The universe on event day D is:

```text
PIT mcap500 mainboard universe as of D
```

Constituent eligibility on event day D must require:

1. instrument is a PIT universe member as of D;
2. instrument has valid provider `open`, `high`, `low`, `close`, `volume`, and `money` on D;
3. instrument has a valid previous traded close for price-limit detection;
4. instrument has nonzero `volume` and `money` on D;
5. no stock outside the PIT universe may enter the event set;
6. all joins must be keyed by `date + instrument`.

Forward entry or exit price availability must not be used to decide whether D is an upper-limit event. Future price availability is evaluated only after the event is fixed and must be reported separately with:

```text
event_detection_status
entry_status
exit_label_status
```

## 5. Local Data Availability Contract

Local data scan assumptions:

| Local source | Available fields |
|:--|:--|
| `data/qlib/cn_data_pit/features/*` | `open`, `close`, `high`, `low`, `volume`, `money`, `factor` |
| `data/universe/pit_mcap500_mainboard_daily.csv` | PIT membership, `name`, `market`, `list_date`, `delist_date`, `listing_age_trading_days`, `market_cap_asof_T` |
| `data/universe/pit_qlib_instrument_universe.csv` | instrument mapping and exchange |
| `data/targets/pit_industry_membership.csv` | PIT industry membership |
| `data/qlib/cn_data_pit/features/sh000300` / `data/targets/target_history.csv` | SH000300 index OHLCV |

Local data scan does not provide:

```text
account-level NetBuy by investor group
borrow availability by stock-day
borrow fee by stock-day
intraday limit-order-book queue position
raw official daily price-limit flag from exchange
market-to-book ratio for DGTW size/book-to-market adjustment
```

The run must create a local data availability manifest:

```text
r12_input_availability_manifest.csv
```

Required columns:

```text
input_id
paper_required_input
local_source
source_path
source_sha256
availability_status
official_unadjusted_daily_ohlc_status
replication_action
local_proxy_id
asof_policy
coverage_train_days
coverage_validation_days
coverage_robustness_days
fallback_reason
block_reason
```

Allowed `availability_status` values:

```text
available_full
available_partial
missing_required_account_level_data
missing_required_borrow_data
missing_required_intraday_data
missing_required_fundamental_control
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

Mandatory availability decisions:

| Paper input / mechanism | Local action | Reason |
|:--|:--|:--|
| upper-limit close event | `retain_local_proxy` | infer from the frozen limit-detection price source and previous traded close |
| next-day and long-run return reversal | `retain` | provider OHLC supports event return windows |
| large-investor NetBuy | `remove` | account-level transaction data absent |
| regular-stock 10% price limit | `retain_local_proxy` | local mainboard regular stocks should be 10%; infer with tolerance |
| ST 5% price limit | `diagnostic_only` | ST status can only be proxied from local name/status metadata unless explicit ST file exists |
| short-sale execution | `diagnostic_only` | borrow data absent; report price-return proxy only |
| high-return non-limit comparator | `retain` | infer from same provider prices |
| DGTW size/book-to-market abnormal return | `retain_local_proxy` | use size/industry/turnover controls because market-to-book is absent |

The manifest must include a distinct row:

```text
input_id = official_unadjusted_daily_ohlc_for_limit_detection
```

If this source is available, `source_path` and `source_sha256` must be populated, and `limit_detection_price_source = official_unadjusted_daily_ohlc_if_available`. If this source is absent, the row must set:

```text
availability_status = missing_required_price_fields
replication_action = remove
block_reason = official_unadjusted_daily_ohlc_absent
fallback_reason = use_provider_ohlc_with_factor_continuity_guard
```

The provider fallback for price-limit detection is valid only after this manifest row records why the official unadjusted source was unavailable.

For primary detection, the official unadjusted OHLC source counts as available only if it reproducibly covers every retained candidate date with open, high, low, close, volume, and money fields. A partial official source must be recorded as `availability_status = available_partial`, but must not be mixed into primary detection unless a later requirement defines a date-level source-merge policy.

Local price-adjustment contract:

```text
price_adjustment_mode = provider_ohlc_already_adjusted
primary_return_price = open and close from Qlib provider
do_not_reapply_factor_day_bin_to_ohlc = true
```

The local `factor` field may be used only as an audit field to confirm provider lineage. It must not be multiplied into OHLC prices in this requirement.

Price-limit detection uses a stricter source contract because official daily price limits are defined on exchange trading prices, not on adjusted return series:

```text
limit_detection_price_source_priority:
  1. official_unadjusted_daily_ohlc_if_available
  2. provider_ohlc_with_factor_continuity_guard

limit_detection_price_source must be recorded in:
  r12_run_manifest.json
  r12_detection_candidate_audit.csv
  r12_event_path_returns.csv

official_unadjusted_daily_ohlc_status must be recorded in:
  r12_run_manifest.json
  r12_input_availability_manifest.csv

Allowed official_unadjusted_daily_ohlc_status values:
  available_full_range
  available_partial_not_used
  absent_used_provider_fallback
  blocked_unreproducible_source

provider_ohlc_with_factor_continuity_guard is allowed only when:
  factor_{i,D} is finite
  factor_{i,prev_traded_day} is finite
  abs(factor_{i,D} / factor_{i,prev_traded_day} - 1) <= factor_continuity_tolerance

factor_continuity_tolerance = 0.0001
```

If the provider price is used for limit detection and the factor continuity guard fails, block the instrument-date before event classification:

```text
event_detection_status = blocked_factor_discontinuity_for_limit_detection
```

The final report must disclose:

```text
limit_detection_price_source
factor_discontinuity_blocked_count
factor_discontinuity_blocked_share
```

`money` is the local turnover amount field. Implementations must not silently substitute `amount` or another provider-specific alias.

## 6. Daily Calendar And Sample Split

Daily event dates must be derived from the local trading calendar:

```text
D = retained local trading-calendar date
D+1 = next retained local trading-calendar date
D+H = H-th retained local trading-calendar date after D
```

The previous traded close used for price-limit detection is:

```text
prev_traded_day(i, D) =
  max date e < D such that
    limit_detection_close_{i,e} is finite
    volume_{i,e} > 0
    money_{i,e} > 0
    e is no more than max_prev_trade_gap trading days before D

max_prev_trade_gap = 10 trading days
```

If no such `prev_traded_day` exists, the instrument-date is blocked for event detection:

```text
event_detection_status = blocked_missing_previous_traded_close
```

The local evaluation split is:

| Split | Calendar window | Notes |
|:--|:--|:--|
| warmup | `2017-01-03` to `2018-06-30` | used for previous-close, turnover, size, and control histories |
| train | `2018-07-01` to `2021-12-31` | calibration / descriptive only |
| validation | `2022-01-01` to `2023-12-31` | primary out-of-sample decision window |
| robustness | `2024-01-01` to `2025-12-31` | post-validation robustness window |

Split assignment is based on event date D, not exit date. If an event cannot complete a requested H-day exit before provider end, mark:

```text
exit_label_status = blocked_incomplete_future_return_label
```

and exclude that event from H-specific return metrics. Do not impute missing future returns.

Primary reported horizons are intentionally short enough to be well covered in validation and robustness:

```text
primary_report_horizons = {5, 10, 20} trading days
primary_decision_horizons = {10, 20} trading days
```

`H=5` is an early-reversal diagnostic. It must be reported, but it cannot substitute for `H=10` or `H=20` in final support gates.

Additional paper-aligned long-run diagnostics must be reported where label-complete:

```text
diagnostic_horizons = {1, 2, 60, 120} trading days
```

No horizon may be selected after validation returns are observed.

## 7. Upper-Limit Event Definitions

The primary event is a regular-stock close at the 10% upper price limit.

Daily return to previous traded close:

```text
ret_to_prev_traded_close_{i,D} =
  limit_detection_close_{i,D}
  / limit_detection_close_{i,prev_traded_day(i,D)} - 1
```

Close-at-high condition:

```text
close_at_high_{i,D} =
  abs(limit_detection_close_{i,D} / limit_detection_high_{i,D} - 1)
    <= close_high_tolerance

close_high_tolerance = 0.0015
```

Allowed `event_type` values:

```text
regular_10pct_upper_close_hit
st_5pct_upper_close_hit_diagnostic
nonlimit_high_return
return_bucket_8_9
return_bucket_9_near_limit
not_event
```

Allowed non-blocking `event_detection_status` values:

```text
detected_regular_10pct_upper_close_hit
detected_st_5pct_upper_close_hit_diagnostic
detected_nonlimit_high_return
detected_return_bucket_8_9
detected_return_bucket_9_near_limit
not_detected_not_upper_hit_or_comparator
```

Rows that are valid candidates but do not satisfy any upper-hit or comparator definition must use:

```text
event_type = not_event
event_detection_status = not_detected_not_upper_hit_or_comparator
detection_block_reason = none
```

They are non-events, not detection blockers. They must stay out of `r12_event_path_returns.csv`, which contains only detected upper-hit and comparator events.

Regular 10% upper-limit proxy:

```text
regular_10pct_upper_close_hit_{i,D} =
  st_status_proxy_{i,D} = false
  ret_to_prev_traded_close_{i,D} >= 0.0980
  ret_to_prev_traded_close_{i,D} <= 0.1025
  close_at_high_{i,D} = true
  volume_{i,D} > 0
  money_{i,D} > 0
```

ST status proxy:

```text
st_status_proxy_{i,D} =
  name contains "ST" or "*ST" as of D
```

If a future explicit ST status file exists, it may replace the name proxy only if it is point-in-time and the replacement is recorded in `r12_input_availability_manifest.csv`.

ST 5% upper-limit proxy:

```text
st_5pct_upper_close_hit_{i,D} =
  st_status_proxy_{i,D} = true
  ret_to_prev_traded_close_{i,D} >= 0.0480
  ret_to_prev_traded_close_{i,D} <= 0.0525
  close_at_high_{i,D} = true
  volume_{i,D} > 0
  money_{i,D} > 0
```

ST events are diagnostic only. They must not enter the primary final decision unless a later requirement upgrades local ST status quality.

High-return non-limit comparator:

```text
nonlimit_high_return_{i,D} =
  st_status_proxy_{i,D} = false
  ret_to_prev_traded_close_{i,D} >= 0.0800
  ret_to_prev_traded_close_{i,D} < 0.0980
  regular_10pct_upper_close_hit_{i,D} = false
  volume_{i,D} > 0
  money_{i,D} > 0
```

The implementation must also create narrower paper-style comparator buckets:

```text
return_bucket_8_9 = [0.0800, 0.0900)
return_bucket_9_near_limit = [0.0900, 0.0980)
```

Event clustering:

```text
upper_hit_cluster_id =
  consecutive regular_10pct_upper_close_hit events for the same instrument
  separated by one retained trading day

cluster_position =
  first_hit | continuation_hit
```

The primary event-study table must include all regular 10% upper-close hits. A `first_hit_only` subset is required as robustness and execution-risk interpretation. The final decision must not switch from all hits to first hits after seeing validation returns.

## 8. Short-After-Upper-Hit Return Definitions

Primary entry variant:

```text
entry_variant = d1_open
entry_date = D+1
entry_price = open_{i,D+1}
```

An event is entry-evaluable only if:

```text
open_{i,D+1} is finite
volume_{i,D+1} > 0
money_{i,D+1} > 0
not one_price_limit_locked_{i,D+1}
```

One-price locked day proxy:

```text
one_price_limit_locked_{i,d} =
  max(open_{i,d}, high_{i,d}, low_{i,d}, close_{i,d})
    / min(open_{i,d}, high_{i,d}, low_{i,d}, close_{i,d}) - 1
    <= one_price_lock_tolerance
  and volume_{i,d} > 0

one_price_lock_tolerance = 0.0005
```

Because daily OHLC cannot identify queue position, one-price locked days are blocked for executable-entry diagnostics:

```text
entry_status = blocked_one_price_limit_locked
```

Required entry variants:

| Variant | Role | Formula |
|:--|:--|:--|
| `d1_open` | primary | short at `D+1` open |
| `d1_close` | conservative diagnostic | short at `D+1` close |
| `d0_close_oracle` | non-executable paper-path diagnostic | short at D close after observing the close-at-limit event |

`d0_close_oracle` must be labeled non-executable and must not enter the final decision.

For entry variant `v` and horizon H:

```text
exit_date = D+H
exit_price = close_{i,D+H}

stock_long_return_{i,D,H,v} =
  exit_price / entry_price_v - 1

gross_short_return_{i,D,H,v} =
  1 - exit_price / entry_price_v
```

For `d1_open`, `H=1` means short at `D+1` open and cover at `D+1` close.

For `d1_close`, `H=1` is mechanically zero and must not be reported in decision tables. The first meaningful `d1_close` diagnostic horizon is `H=2`.

Benchmark-adjusted short return:

```text
benchmark_long_return_{D,H,v} =
  close_{SH000300,D+H} / benchmark_entry_price_v - 1

benchmark_entry_price for d1_open = open_{SH000300,D+1}
benchmark_entry_price for d1_close = close_{SH000300,D+1}
benchmark_entry_price for d0_close_oracle = close_{SH000300,D}

market_hedged_short_return =
  gross_short_return + benchmark_long_return
```

After-cost diagnostic:

```text
short_sell_cost_bps = 80
buy_to_cover_cost_bps = 30
round_trip_cost_bps = 110

after_cost_short_return_ex_borrow =
  gross_short_return
  - short_sell_cost_bps / 10000
  - buy_to_cover_cost_bps / 10000
```

Borrow cost and borrow availability are missing locally. The run must also publish stress diagnostics:

```text
borrow_fee_stress_bps_per_trading_day in {0, 2, 5, 10}
after_cost_short_return_with_borrow_stress =
  after_cost_short_return_ex_borrow
  - borrow_fee_stress_bps_per_trading_day * H / 10000
```

No final report may call the short proxy executable unless borrow data is later added and a new requirement explicitly authorizes execution evaluation.

## 9. Detection And Event-Study Outputs

The implementation must separate event detection from post-event path evaluation. Detection blockers belong in the detection audit, while entry and exit blockers belong in the event-path table.

Detection audit:

```text
r12_detection_candidate_audit.csv
```

Required columns:

```text
split
date
instrument
candidate_scope
pit_member_on_date
limit_detection_price_source
factor_continuity_status
event_detection_status
event_type
prev_traded_day
ret_to_prev_traded_close
close_high_gap
st_status_proxy
market_cap_asof_T
industry
turnover_money
detection_block_reason
```

Required `candidate_scope` values:

```text
pit_universe_candidate
outside_pit_audit_only
```

`pit_universe_candidate` is mandatory. `outside_pit_audit_only` is optional and may be populated only if a reproducible local full-market daily OHLC source exists. If no such source exists, the run manifest must record:

```text
outside_pit_audit_status = not_evaluable_local_source_absent
```

Allowed `factor_continuity_status` values:

```text
not_required_official_unadjusted_source
passed_provider_factor_continuity_guard
blocked_factor_discontinuity_for_limit_detection
blocked_missing_factor_for_limit_detection
```

Required detection blocker categories:

```text
blocked_not_pit_member_on_event_day
blocked_missing_event_day_ohlcv
blocked_missing_previous_traded_close
blocked_factor_discontinuity_for_limit_detection
blocked_missing_factor_for_limit_detection
blocked_invalid_event_day_liquidity
```

Allowed `detection_block_reason` values are `none` plus the required detection blocker categories above. For blocked candidate rows:

```text
event_detection_status = detection_block_reason
event_type = not_event
```

The detection audit is allowed to be large. The event-path table below must contain only detected upper-hit and comparator events, expanded by entry variant, horizon, and borrow-stress setting.

```text
r12_event_path_returns.csv
```

Required columns:

```text
split
date
instrument
event_type
event_detection_status
limit_detection_price_source
factor_continuity_status
entry_variant
entry_status
horizon
exit_label_status
prev_traded_day
ret_to_prev_traded_close
close_high_gap
cluster_id
cluster_position
st_status_proxy
market_cap_asof_T
industry
turnover_money
entry_price
exit_price
stock_long_return
gross_short_return
market_hedged_short_return
after_cost_short_return_ex_borrow
borrow_fee_stress_bps_per_trading_day
after_cost_short_return_with_borrow_stress
```

The event table must include detected events even when post-event entry or exit labels are blocked, with `entry_status` or `exit_label_status` populated. Entry/exit-blocked rows must not disappear silently.

The implementation must publish event-count and blocker diagnostics:

```text
r12_event_count_by_split.csv
r12_entry_exit_block_audit.csv
r12_upper_hit_cluster_diagnostics.csv
```

Required blocker categories:

```text
blocked_entry_missing_d1_open
blocked_entry_nontrading_d1
blocked_one_price_limit_locked
blocked_incomplete_future_return_label
blocked_exit_missing_price
```

Allowed `entry_status` values:

```text
complete
blocked_entry_missing_d1_open
blocked_entry_nontrading_d1
blocked_one_price_limit_locked
```

Allowed `exit_label_status` values:

```text
complete
blocked_incomplete_future_return_label
blocked_exit_missing_price
```

## 10. Portfolio Aggregation Rules

The primary evidence is event-study return by horizon. A calendar-time portfolio diagnostic is also required to detect concentration and overlapping-event fragility.

Event-study aggregation:

```text
for each split, event_type, entry_variant, horizon:
  event-weighted descriptive metrics:
    equal-weight average over all event rows with complete entry and exit labels

  date-weighted decision metrics:
    first aggregate complete event rows into one equal-weight mean per event date D
    then equal-weight average over event-date means
```

Required statistics:

```text
event_count
instrument_count
event_month_count
event_date_count
event_weighted_mean_gross_short_return
event_weighted_median_gross_short_return
event_weighted_positive_event_share
date_weighted_mean_gross_short_return
date_weighted_positive_event_date_share
date_weighted_mean_market_hedged_short_return
date_weighted_mean_after_cost_short_return_ex_borrow
date_weighted_mean_after_cost_short_return_borrow_2bps
date_weighted_mean_after_cost_short_return_borrow_5bps
date_weighted_mean_after_cost_short_return_borrow_10bps
newey_west_observation_unit
newey_west_lag
newey_west_tstat_date_weighted_mean_gross_short_return
newey_west_tstat_date_weighted_mean_market_hedged_short_return
newey_west_tstat_date_weighted_mean_after_cost_ex_borrow
```

Use Newey-West standard errors on the event-date mean return series, not on raw event rows. This prevents same-date cross-sectional event clusters from being treated as independent time-series observations. The default lag by horizon is:

```text
newey_west_observation_unit = event_date_mean_return_series
newey_west_lag = min(H, 20)
```

Calendar-time portfolio diagnostic:

```text
entry day portfolio:
  all entry-evaluable upper-hit events from the same event date D
  equal weight across new short entries

active holding:
  each event vintage remains active until its horizon-specific exit date

calendar day return:
  equal-weight average of active vintage daily short returns
```

Name cap for calendar-time diagnostics:

```text
max_abs_weight_per_instrument = 0.05
renormalize_after_name_cap = true
```

If the same instrument has multiple active event vintages, aggregate the instrument's active weights before applying the cap. The cap is diagnostic only and must be reported in:

```text
r12_calendar_time_short_returns.csv
```

The final decision is based on event-study primary horizons, not on a post-hoc chosen calendar-time portfolio variant.

## 11. Comparator And Attribution Diagnostics

The implementation must compare upper-limit events against non-limit high-return events using the same entry variant and horizons.

Required comparator outputs:

```text
r12_upper_hit_vs_nonlimit_high_return_summary.csv
r12_matched_comparator_pairs.csv
```

Matching policy:

```text
For every upper-hit event, find same-date nonlimit_high_return candidates.
Match by nearest market_cap_asof_T percentile and same industry if available.
If same-industry match is unavailable, use same date and nearest size percentile.
No future returns may be used in matching.
Matching is performed once per upper-hit event before horizon returns are read.
The same matched instrument is reused for all entry variants and horizons.
```

Within each date, same-industry matching is attempted first. If several upper-hit events compete for the same comparator candidate, assign matches greedily by smallest size-percentile absolute difference, then by `upper_hit_instrument` ascending, then by `matched_instrument` ascending. A comparator instrument may be used at most once per event date.

Allowed `match_status` values:

```text
matched_same_industry
matched_same_date_size_only
unmatched_no_same_date_candidate
unmatched_candidate_already_used
unmatched_missing_match_fields
```

Required matched-pair columns:

```text
split
date
entry_variant
upper_hit_instrument
matched_instrument
match_status
unmatched_reason
same_industry_match
upper_hit_market_cap_percentile
matched_market_cap_percentile
size_percentile_abs_diff
horizon
upper_hit_gross_short_return
matched_gross_short_return
incremental_short_return
```

Required comparator coverage statistics:

```text
split
entry_variant
horizon
upper_hit_event_count_for_comparator
matched_upper_hit_event_count
matched_event_share
matched_same_industry_share
median_size_percentile_abs_diff
comparator_coverage_status
event_weighted_mean_incremental_short_return_vs_nonlimit_high_return
date_weighted_mean_incremental_short_return_vs_nonlimit_high_return
newey_west_tstat_date_weighted_mean_incremental_short_return
```

For comparator coverage by horizon, the denominator is complete upper-hit events for the same split, entry variant, and horizon. A matched pair contributes to `matched_upper_hit_event_count` only when both the upper-hit event and matched comparator have complete entry and exit labels for that same horizon.

Allowed `comparator_coverage_status` values:

```text
pass
fail_insufficient_matched_event_share
fail_no_same_date_candidates
not_evaluable_no_upper_hit_events
```

Required attribution axes:

```text
cluster_position
market_state
industry
size_bucket
turnover_bucket
money_liquidity_bucket
event_month
event_year
```

Market state proxy:

```text
market_state_20d =
  up if SH000300 close_D / close_{D-20} - 1 >= 0
  down otherwise
```

Turnover and liquidity buckets are computed cross-sectionally on event date D using only as-of fields:

```text
turnover_money = money_{i,D} / market_cap_asof_T_{i,D}
money_liquidity = money_{i,D}
bucket method = tercile within event-date PIT universe
```

## 12. Required Output Artifacts

If implemented, the run must create:

```text
ep6/configs/r12_daily_price_limit_short_after_upper_hit_v0.yaml
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_run_manifest.json
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_input_availability_manifest.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_detection_candidate_audit.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_event_count_by_split.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_entry_exit_block_audit.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_upper_hit_cluster_diagnostics.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_event_path_returns.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_short_return_summary_by_horizon.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_upper_hit_vs_nonlimit_high_return_summary.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_matched_comparator_pairs.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_calendar_time_short_returns.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_attribution_by_state.csv
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_validation_manifest.json
ep6/outputs/r12_daily_price_limit_short_after_upper_hit_v0/r12_final_report.md
```

The final report must be Chinese unless the user explicitly requests otherwise.

## 13. Validation Gates

Validation status must be deterministic and replayable from artifacts.

The validation manifest must contain one row-equivalent object per gate and enough metadata to replay the final decision without reading the report prose.

Required `r12_validation_manifest.json` fields:

```text
requirement_id
short_name
config_path
config_sha256
requirement_path
requirement_sha256
run_started_at
run_completed_at
provider_uri
provider_calendar_min
provider_calendar_max
provider_load_end
pit_universe_path
pit_universe_sha256
event_detection_method_id
limit_detection_price_source
outside_pit_audit_status
entry_variant_primary
primary_report_horizons
primary_decision_horizons
final_decision
authorized_strategy_requirement
gate_results
```

Each `gate_results` item must contain:

```text
gate_id
gate_group
split
event_type
entry_variant
horizon
metric_name
observed_value
threshold_value
comparison_operator
denominator
numerator
gate_status
block_reason
source_artifact
```

Allowed `gate_status` values:

```text
pass
fail
not_evaluable
not_applicable
```

Minimum sample gates:

```text
validation_regular_upper_hit_event_count >= 100
robustness_regular_upper_hit_event_count >= 100
validation_event_month_count >= 12
robustness_event_month_count >= 12
primary_entry_complete_share >= 0.70 for split in {validation, robustness}
primary_horizon_label_complete_share >= 0.70 for split in {validation, robustness}, H in {5, 10, 20}
```

Minimum sample gate denominators are frozen:

```text
regular_upper_hit_event_count denominator:
  detected events where event_type = regular_10pct_upper_close_hit
  candidate_scope = pit_universe_candidate
  counted before entry and exit filters

event_month_count denominator:
  unique event months among the same detected regular upper-hit events

primary_entry_complete_share:
  numerator = detected regular upper-hit events with entry_status = complete
              for entry_variant = d1_open
  denominator = detected regular upper-hit events before entry filters

primary_horizon_label_complete_share(H):
  numerator = detected regular upper-hit events with entry_status = complete
              and exit_label_status = complete
              for entry_variant = d1_open and horizon = H
  denominator = detected regular upper-hit events with entry_status = complete
                for entry_variant = d1_open
```

If any minimum sample gate fails, final decision must be:

```text
r12_not_evaluable_insufficient_limit_up_events
```

Primary decision horizons are frozen:

```text
primary_decision_horizons = {10, 20}
```

`H=10` and `H=20` must both pass. `H=5`, `H=60`, `H=120`, `d1_close`, and `d0_close_oracle` are diagnostics only and cannot replace a failed primary decision horizon.

Define `split_horizon_support_pass(split, H)` for `entry_variant = d1_open`, `event_type = regular_10pct_upper_close_hit`, and `H in {10, 20}`:

```text
date_weighted_mean_gross_short_return(split, H) > 0
date_weighted_mean_after_cost_short_return_ex_borrow(split, H) > 0
date_weighted_positive_event_date_share(split, H) >= 0.52
newey_west_tstat_date_weighted_mean_gross_short_return(validation, H) >= 1.50 if split = validation
```

Comparator gates:

```text
comparator_coverage_pass(split, H):
  comparator_coverage_status(split, H) = pass
  matched_event_share(split, H) >= 0.70

comparator_direction_pass(split, H):
  date_weighted_mean_incremental_short_return_vs_nonlimit_high_return(split, H) > 0

These comparator gates apply for split in {validation, robustness}, H in {10, 20}.
```

Define `horizon_pass(H)`:

```text
horizon_pass(H) =
  split_horizon_support_pass(validation, H)
  and split_horizon_support_pass(robustness, H)
  and comparator_coverage_pass(validation, H)
  and comparator_coverage_pass(robustness, H)
  and comparator_direction_pass(validation, H)
  and comparator_direction_pass(robustness, H)
```

Define `validation_directional_pass(H)`:

```text
validation_directional_pass(H) =
  date_weighted_mean_gross_short_return(validation, H) > 0
  and date_weighted_mean_incremental_short_return_vs_nonlimit_high_return(validation, H) > 0
```

Borrow stress gates are not required for diagnostic support, but must be reported:

```text
borrow_stress_2bps_status
borrow_stress_5bps_status
borrow_stress_10bps_status
```

Allowed final decisions:

```text
r12_not_evaluable_insufficient_limit_up_events
r12_not_evaluable_insufficient_comparator_coverage
r12_short_after_limit_up_not_supported
r12_short_after_limit_up_descriptive_only
r12_short_after_limit_up_diagnostic_supported_not_executable
```

Decision priority:

1. If minimum sample gates fail, use `r12_not_evaluable_insufficient_limit_up_events`.
2. If comparator coverage gates fail for any split in `{validation, robustness}` and any `H in {10, 20}`, use `r12_not_evaluable_insufficient_comparator_coverage`.
3. If `horizon_pass(10)` and `horizon_pass(20)` are both true, use `r12_short_after_limit_up_diagnostic_supported_not_executable`.
4. If at least one `validation_directional_pass(H)` is true for `H in {10, 20}` but the support condition in step 3 fails, use `r12_short_after_limit_up_descriptive_only`.
5. Otherwise use `r12_short_after_limit_up_not_supported`.

Even when diagnostic support passes, `authorized_strategy_requirement` remains `false` because local borrow feasibility is not observed.

## 14. Interpretation Rules

Required positive-result interpretation:

```text
The local public-price proxy supports a post-upper-limit reversal diagnostic
inside the PIT mcap500 mainboard universe.
It does not replicate the paper's account-level large-investor mechanism
and does not prove a borrowable short strategy.
```

Required negative-result interpretation:

```text
Failure of the local short-after-limit-up proxy does not refute the paper.
The local test differs on sample period, universe, data source, account-level information,
short-sale feasibility, and entry timing.
```

The final report must explicitly distinguish:

```text
paper mechanism:
  large investors buy D and sell D+1, causing overreaction and reversal

local proxy:
  public-price short after D close upper-limit event

strategy feasibility:
  not evaluated because borrow data and intraday execution data are absent
```

The report must not claim:

```text
large investors are identified locally
shorting after 涨停 is executable
the result is an exact paper replication
ST causal evidence is replicated unless ST status quality is validated
```

## 15. Implementation Notes For Later Work

This requirement intentionally freezes the first local test as a low-parameter event-study. Do not add discretionary filters such as "only after two limit-ups", "only low turnover", "only specific industries", or "only bear markets" before the primary validation is run.

Allowed follow-up experiments after this requirement:

```text
cluster-aware short timing:
  first_hit vs continuation_hit vs post-cluster-break

entry timing robustness:
  D+1 open vs D+1 close vs D+2 open

long-only avoidance:
  remove upper-hit contaminated winners from momentum portfolios

regime-conditioned reversal:
  only after market/industry attention states pass descriptive gates
```

Those follow-ups require separate requirements if they are used for final decisions.
