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
  total market cap greater than CNY `100,000,000,000`.
- ChiNext eligibility: ChiNext stocks with daily total market cap greater than
  CNY `50,000,000,000`.
- Prices: forward-adjusted (`qfq`) OHLCV plus turnover and basic trading
  fields.

The implementation has not been written yet. The frozen requirement is
`requirement.md`; the runnable parameters are in `config.yaml`.
