# Data Prepare PIT Largecap AkShare Qlib V0

This is the first data-preparation experiment for `02_AFML_BIG_WINNER`.

Goal:

- Build a point-in-time large-cap A-share universe from AkShare data.
- Cache raw and processed data under `topics/02_AFML_BIG_WINNER/data/`.
- Convert daily bars into a Qlib provider usable by later event, label, and
  model experiments.

Primary contract:

- Calendar range: `2017-01-01` through `2026-05-31`, inclusive by calendar
  date and resolved to actual A-share sessions by the trading calendar.
- Main-board eligibility: Shanghai and Shenzhen main-board stocks with daily
  total market cap greater than CNY `50,000,000,000`.
- ChiNext eligibility: ChiNext stocks with daily total market cap greater than
  CNY `20,000,000,000`.
- Prices: forward-adjusted (`qfq`) OHLCV plus turnover and basic trading
  fields.

Runnable entrypoint:

```bash
cd topics/02_AFML_BIG_WINNER
uv run python experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode validate-config
uv run python experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode preflight
uv run python experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode index-only
uv run python experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/code/run.py --mode full
```

The full mode is source-gated. It first writes the AkShare API audit artifacts,
then refuses to build the PIT universe when a required source is unsupported or
latest-only. In the current tested AkShare environment, historical share
structure is available through `stock_zh_a_gbjg_em`, suspension sampling is
date-keyed, and unproxied Shenzhen name-change history provides dated ST
markers. For Shanghai instruments, `stock_info_change_name` returns names
without dates; the experiment therefore uses a conservative whole-asset
exclusion policy: if any Shanghai name-history row contains an ST marker, the
instrument is removed from the entire universe. Benchmark index data is written
to a separate Qlib provider so index instruments cannot enter the tradable stock
market universe.

Primary implementation files:

- `code/pipeline.py`: pure PIT/calendar/normalization/audit helpers.
- `code/run.py`: CLI, source audit, reports, and run manifest.
- `tests/test_pipeline.py`: offline tests for board buckets, raw/QFQ
  normalization, share-as-of expansion, executable-date shifting, and interval
  compression.
