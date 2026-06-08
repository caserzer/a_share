# Data Directory

This directory contains generated data for the
`data_prepare_pit_largecap_akshare_qlib_v0` experiment. The data source is
AkShare, and the primary consumers are Qlib-based research experiments under
`topics/02_AFML_BIG_WINNER`.

Most files under `raw/`, `interim/`, `processed/`, and `qlib/` are generated
caches and are intentionally ignored by Git. The experiment reports and audit
tables under `experiments/pending/data_prepare_pit_largecap_akshare_qlib_v0/outputs/`
are the publishable summary artifacts.

## Coverage

- Requested date range: `2017-01-01` to `2026-05-31`
- Resolved A-share trading range: `2017-01-03` to `2026-05-29`
- Resolved sessions: `2281`
- PIT stock market: `pit_largecap_main_chinext`
- Stock Qlib provider: `qlib/cn_data_pit_largecap/`
- Benchmark index Qlib provider: `qlib/cn_index_data/`

## Directory Layout

```text
data/
|-- raw/
|   `-- akshare/
|       |-- day/
|       |   |-- raw/          # unadjusted stock daily bars
|       |   `-- qfq/          # forward-adjusted stock daily bars
|       |-- index/day/        # raw benchmark index source CSVs
|       |-- market_cap/       # share-history caches used for market cap
|       `-- status/           # listing, delisting, ST, calendar, and status caches
|-- interim/
|   |-- qlib_csv/day/         # stock CSVs before Qlib bin conversion
|   `-- index_qlib_csv/day/   # benchmark index CSVs before Qlib bin conversion
|-- processed/
|   |-- universe/             # PIT stock universe tables and Qlib instrument file
|   `-- index/                # normalized benchmark index tables and audit
|-- qlib/
|   |-- cn_data_pit_largecap/ # Qlib stock provider
|   `-- cn_index_data/        # Qlib benchmark index provider
`-- external/                 # reserved for manually supplied external inputs
```

## Stock Universe Data

The stock universe is point-in-time and close-observed. Membership on
`membership_date = D` uses information observable after the close of `D`, and
the executable Qlib market starts on `usable_trade_date`, the next trading
session after `D`.

Main-board members require:

```text
total_market_cap_cny > 50_000_000_000
```

ChiNext members require:

```text
total_market_cap_cny > 20_000_000_000
```

Market cap is computed from unadjusted close and historical total shares:

```text
total_market_cap_cny_D = raw_close_D * total_share_asof_D
```

Forward-adjusted prices are used for research OHLC fields, not for market-cap
eligibility. ST and suspended rows are excluded from final membership.

Key universe files:

- `processed/universe/pit_largecap_main_chinext_candidate_before_status_exclusion.csv`
  contains threshold candidates before final status filters.
- `processed/universe/pit_largecap_main_chinext_membership_daily.csv`
  contains close-observed raw membership keyed by `membership_date`.
- `processed/universe/pit_largecap_main_chinext_executable_daily.csv`
  contains executable membership keyed by `usable_trade_date`.
- `processed/universe/pit_largecap_main_chinext_intervals.csv`
  contains contiguous executable membership intervals.
- `processed/universe/qlib_pit_largecap_main_chinext.txt`
  is the Qlib market instrument file.

## Benchmark Index Data

Benchmark index data is separate from the tradable stock universe and must not
be mixed into `pit_largecap_main_chinext`.

Configured index series:

| Alias | Instrument | Source symbol | Current source |
| --- | --- | --- | --- |
| `csi300` | `SH000300` | `sh000300` | `stock_zh_index_daily` |
| `chinext_index` | `SZ399006` | `sz399006` | `stock_zh_index_daily` |
| `all_a` | `SH000985` | `sh000985` | `stock_zh_index_daily_tx` |

Key index files:

- `processed/index/benchmark_indices_daily.csv`
  contains normalized daily OHLCV rows plus source audit columns.
- `processed/index/benchmark_indices_source_audit.csv`
  records source function, symbol, units, coverage, and nullable fields.
- `processed/index/qlib_benchmark_indices.txt`
  is the Qlib market instrument file for benchmark indices.
- `interim/index_qlib_csv/day/*.csv`
  are the pre-bin Qlib index CSVs.
- `qlib/cn_index_data/`
  is the generated Qlib benchmark index provider.

Current index sources provide OHLC and volume but do not provide a verified
transaction-value field, so index `$money` is nullable and is reported as such
in the index audit and provider check.

## Regeneration

Run commands from `topics/02_AFML_BIG_WINNER`.

Validate configuration:

```bash
uv run python experiments/pending/data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode validate-config
```

Refresh only benchmark index data and the index Qlib provider:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  uv run python experiments/pending/data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode index-only
```

Run the full stock-universe and benchmark-index pipeline:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  uv run python experiments/pending/data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode full
```

Do not hand-edit generated data files. Change the requirement, config, or
pipeline code, then regenerate the affected artifact family.
