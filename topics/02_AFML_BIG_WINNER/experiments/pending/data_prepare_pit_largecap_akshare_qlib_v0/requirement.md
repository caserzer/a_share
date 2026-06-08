# Requirement: PIT Largecap AkShare Qlib Data Preparation V0

## 1. Objective

Build the first reusable data layer for `02_AFML_BIG_WINNER`.

The experiment must create a point-in-time A-share universe and a Qlib daily
data provider using AkShare as the data source. All raw, interim, processed,
and Qlib cache artifacts must live under:

```text
topics/02_AFML_BIG_WINNER/data/
```

This experiment is data infrastructure only. It must not train models, create
entry labels, run backtests, or infer alpha.

## 2. Date Range

The calendar range is:

```text
start_date = 2017-01-01
end_date = 2026-05-31
```

The implementation must resolve this range to the actual A-share trading
calendar:

- If `2017-01-01` is not a trading session, the first covered trading date must
  be the first valid session on or after `2017-01-01`.
- If `2026-05-31` is not a trading session, the final covered trading date must
  be the last valid session on or before `2026-05-31`.

The run manifest must record the requested start/end dates, resolved start/end
trading dates, calendar source, and number of resolved sessions.

## 3. Universe Definition

Create a daily point-in-time universe using same-day total market
capitalization.

### 3.1 Board Buckets

Main-board bucket:

- Shanghai main board: code prefixes `600`, `601`, `603`, `605`.
- Shenzhen main board: code prefixes `000`, `001`, `002`, `003`.

ChiNext bucket:

- Code prefixes `300`, `301`.

Excluded from these two buckets:

- STAR Market / 科创板, including `688` and `689`.
- Beijing Stock Exchange instruments.
- Funds, indexes, bonds, preferred shares, B-shares, and non-common-stock
  instruments.

### 3.2 Market-Cap Thresholds

For each trading date:

```text
main_board_member = total_market_cap_cny > 100_000_000_000
chinext_member = total_market_cap_cny > 50_000_000_000
```

The comparison is strict `>`, not `>=`.

The market-cap field must be historical total market capitalization in CNY as
of date `D`. If AkShare provides an authoritative historical total market-cap
field with a source trade date, use it and record the source column. If not,
compute:

```text
total_market_cap_cny_D = unadjusted_close_D * total_share_asof_D
```

The price used for market capitalization must not be forward-adjusted. QFQ
prices are for OHLC research fields, not for market-cap eligibility.

Disallowed market-cap fallbacks:

- Latest/current total shares without a historical as-of date.
- Latest spot market cap.
- Current security profile market cap.
- QFQ close multiplied by shares.
- Any source whose units cannot be mapped to CNY.

If AkShare cannot provide either historical total market cap or historical
`total_share_asof_D` needed for the formula above, the experiment must stop
with `data_source_market_cap_not_supported`.

### 3.3 Point-in-Time Clock

Raw daily membership for date `D` is based only on information observable as of
the close of `D`.

The raw membership-date output must record:

- `membership_date`
- `available_time = membership_date close`
- `usable_trade_date = next trading session after membership_date`
- `instrument`
- `ts_code`
- `board_bucket`
- `is_listed`
- `is_st`
- `is_suspended`
- `total_market_cap_cny`
- `market_cap_threshold_cny`
- `market_cap_source`
- `price_source`
- `share_source`
- `status_source`
- `membership_rule_version`

If a downstream experiment trades at the next open, it must use the membership
available after the previous close. This experiment must not silently use
same-day close-derived membership for same-day open execution.

Two membership tables are required:

- Raw close-observed table keyed by `membership_date`.
- Executable table keyed by `usable_trade_date`.

The Qlib market must be built from the executable table, not from same-day raw
membership dates.

### 3.4 Status Fields

The implementation must build historical listing, delisting, ST, suspension,
and missing-bar status from AkShare or derived AkShare daily-bar coverage.

The primary membership rule is:

```text
member_D =
    board_bucket in {main_board, chinext}
    and total_market_cap_cny_D > bucket_threshold
    and is_listed_D is true
    and is_st_D is false
    and is_suspended_D is false
```

ST and suspended assets must be removed from the final raw membership table and
the executable Qlib market. The report must show before/after counts for the
ST and suspension exclusions.

If historical listed/delisted, ST, or suspension status cannot be determined for
an instrument-date, that instrument-date must not be included. If the run cannot
produce auditable status coverage over the requested date range, it must stop
with `data_source_status_not_supported`.

## 4. Data Source Contract

Use AkShare for all external data pulls.

Required pull categories:

- Instrument list and security metadata.
- Daily unadjusted OHLCV, amount, turnover, and status-supporting fields.
- Daily forward-adjusted (`qfq`) OHLCV, amount, turnover, and basic trading
  fields.
- Historical total market cap, or the raw fields needed to compute it without
  future leakage.
- Trading calendar or a verifiable session list derived from daily data.

The preflight API audit must resolve exact AkShare function names for each
category before the full pull starts:

- Historical raw daily bars.
- Historical QFQ daily bars.
- Historical total market cap, or historical total shares plus raw close.
- Instrument metadata with board classification.
- Historical listed/delisted status.
- Historical ST status.
- Suspension or tradability status.
- Trading calendar.

For every source, the audit must record source columns, units, source date,
whether the source is historical or latest-only, and the fallback state. A
latest-only source is not allowed for PIT membership, market-cap eligibility, or
historical status.

Expected AkShare daily bar source:

```text
ak.stock_zh_a_hist(symbol=<six_digit_code>, start_date=YYYYMMDD,
                   end_date=YYYYMMDD, adjust="qfq")
```

The implementation must run a preflight API audit before the full pull and
write the result to `outputs/reports/akshare_api_audit.md`. The audit must
freeze the actual AkShare function names, source columns, units, and fallback
logic used in the run.

If an AkShare request fails with a proxy error, the runner should retry once
with `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, and `https_proxy` unset before
classifying the failure as a data error.

## 5. Required Fields

At minimum, the Qlib daily provider must expose:

```text
$open
$high
$low
$close
$volume
$money
$turnover_rate
$factor
```

Canonical transaction value:

```text
$money = transaction value in CNY
```

AkShare source columns such as `成交额`, `amount`, or `turnover` must be mapped
to canonical Qlib `$money`. Do not require Qlib `$amount` unless the converter
explicitly writes a duplicate alias column. If `$amount` is written, it must be
bitwise equal to `$money` after numeric normalization, and the provider check
must test both fields.

The processed daily panel should also retain these audit fields when available:

```text
raw_open
raw_high
raw_low
raw_close
raw_volume
raw_amount
raw_money
total_market_cap_cny
float_market_cap_cny
total_share_asof
float_share_asof
board_bucket
is_listed
is_st
is_suspended
source_trade_date
```

Field naming must be consistent across raw cache, Qlib CSV, and reports.

## 6. Cache Layout

All cache and generated data must stay under the topic data directory:

```text
data/
|-- raw/
|   `-- akshare/
|       |-- day/
|       |   |-- raw/
|       |   `-- qfq/
|       |-- market_cap/
|       `-- status/
|-- interim/
|   `-- qlib_csv/
|       `-- day/
|-- processed/
|   `-- universe/
`-- qlib/
    `-- cn_data_pit_largecap/
```

Expected key artifacts:

- `data/processed/universe/pit_largecap_main_chinext_candidate_before_status_exclusion.csv`
- `data/processed/universe/pit_largecap_main_chinext_membership_daily.csv`
- `data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- `data/processed/universe/qlib_pit_largecap_main_chinext.txt`
- `data/processed/universe/pit_largecap_main_chinext_intervals.csv`
- `data/qlib/cn_data_pit_largecap/`
- `data/raw/akshare/cache_manifest.csv`

Large raw files should remain ignored by Git. Publishable outputs must be
summaries, manifests, reports, compressed artifacts, or small schema samples.

## 7. Qlib Contract

The Qlib provider URI is:

```text
data/qlib/cn_data_pit_largecap
```

The Qlib market name is:

```text
pit_largecap_main_chinext
```

The Qlib market is executable-date keyed:

- Raw membership date `D` is available after the close of `D`.
- Qlib market membership begins on `usable_trade_date`, the next trading session
  after `D`.
- If there is no next trading session within the resolved date range, the raw
  membership row remains in the raw membership table but must not create a Qlib
  executable membership row.

Coverage definitions:

- `price_provider_coverage`: QFQ and raw OHLCV coverage by `trade_date`.
- `raw_membership_coverage`: raw close-observed membership coverage by
  `membership_date`; this must span the resolved trading-date range.
- `executable_membership_coverage`: executable membership coverage by
  `usable_trade_date`; this starts no earlier than the second resolved trading
  session and ends no later than the resolved final trading date.

The executable PIT membership file must be compressed into Qlib-style
instrument intervals. If an instrument repeatedly enters and exits the universe,
the interval output must preserve all contiguous executable membership periods
rather than collapsing to one broad start/end range.

The implementation must verify that Qlib can load a sample of instruments and
fields from the provider after conversion.

## 8. Validation Gates

The experiment passes only if all gates are satisfied:

- `price_provider_coverage` resolves from the first trading session on or after
  `2017-01-01` through the final trading session on or before `2026-05-31`.
- `raw_membership_coverage` covers every resolved trading session for which
  market-cap and status sources are supported.
- `executable_membership_coverage` equals raw membership shifted to
  `usable_trade_date`, excluding raw rows whose next session is outside the
  resolved date range.
- Every included row has exactly one board bucket: `main_board` or `chinext`.
- Every included row satisfies its bucket's strict market-cap threshold.
- Market-cap computation uses non-adjusted price or an explicit historical
  market-cap field, never QFQ price.
- Market-cap computation uses historical `total_share_asof_D` when direct
  historical total market cap is unavailable.
- Market-cap, listing, ST, and suspension sources are historical/as-of sources,
  not latest-only sources.
- No included raw membership row has `is_st = true`, `is_suspended = true`, or
  `is_listed = false`.
- Every Qlib instrument interval is keyed by `usable_trade_date`, not
  `membership_date`.
- QFQ OHLC fields are positive and internally valid:
  `low <= open <= high`, `low <= close <= high` when all fields exist.
- Volume and amount are non-negative.
- Duplicate `(membership_date, instrument)` rows in the raw table and duplicate
  `(usable_trade_date, instrument)` rows in the executable table are rejected.
- Qlib provider load check succeeds for `$open`, `$high`, `$low`, `$close`,
  `$volume`, `$money`, `$turnover_rate`, and `$factor`. If `$amount` is written
  as an alias, the provider check must also verify `$amount == $money`.
- Manifest records AkShare version, command, config hash, input/output paths,
  source column map, requested date range, resolved date range, executable-date
  mapping, and output hashes.

## 9. Required Outputs

Reports:

- `outputs/reports/akshare_api_audit.md`
- `outputs/reports/data_prepare_final_report.md`

Tables:

- `outputs/tables/daily_universe_counts.csv`
- `outputs/tables/board_bucket_counts.csv`
- `outputs/tables/status_exclusion_counts.csv`
- `outputs/tables/market_cap_source_audit.csv`
- `outputs/tables/source_coverage_audit.csv`
- `outputs/tables/missing_data_summary.csv`
- `outputs/tables/qlib_provider_check.csv`

`outputs/tables/status_exclusion_counts.csv` must include at least:

```text
membership_date
board_bucket
candidate_before_status_exclusion_count
excluded_not_listed_count
excluded_st_count
excluded_suspended_count
final_member_count
status_source
```

The candidate-before-status-exclusion artifact may be a full CSV if small
enough, otherwise it must be a schema sample plus the full aggregate counts
above.

Manifests:

- `outputs/manifests/run_manifest.json`
- `outputs/manifests/cache_manifest.csv`

Publishable bundle:

- Small reports and summary tables only.
- No uncompressed full raw daily panel unless it is small enough and explicitly
  reviewed.

## 10. Non-Goals

This experiment must not:

- Build AFML event labels.
- Train a model.
- Backtest a strategy.
- Tune market-cap thresholds.
- Reuse `topics/01_askhare_qlib` data as an input cache.
- Write generated data outside `topics/02_AFML_BIG_WINNER/data/`.
