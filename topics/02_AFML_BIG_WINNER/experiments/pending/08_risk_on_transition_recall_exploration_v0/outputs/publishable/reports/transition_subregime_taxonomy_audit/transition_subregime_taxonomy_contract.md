# Transition Sub-Regime Taxonomy Contract

- Assignment grain is date-level market state.
- Events inherit the sub-regime of `event_t0_date`.
- Primary benchmark is `data/interim/index_qlib_csv/day/SH000985.csv`.
- Automatic taxonomy uses rolling 120 trading-day as-of windows only.
- Rolling-window clustering must pass block-sampled stability before supporting a taxonomy.
- Outcome labels are readout-only and never taxonomy features.
