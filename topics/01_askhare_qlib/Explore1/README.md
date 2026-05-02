# Explore1 Runbook

This experiment uses a static universe of Shanghai/Shenzhen mainboard A-shares whose estimated total market cap on `2025-12-31` is greater than RMB 50 billion.

Important caveat: the universe is static and uses a future-date screen for the full backtest window. Treat results as workflow and diagnostic evidence, not strict live-trading evidence.

## 1. Build Universe

```bash
uv run python Explore1/scripts/build_mcap500_universe.py
```

Outputs:

```text
Explore1/data/universe/mcap500_mainboard_20251231.csv
Explore1/data/universe/qlib_mcap500_mainboard_20251231.txt
Explore1/outputs/reports/mcap500_universe_audit.csv
Explore1/outputs/reports/mcap500_universe_candidates.csv
```

## 2. Fetch Daily Bars

```bash
uv run python scripts/01_fetch_akshare_day.py \
  --universe Explore1/data/universe/mcap500_mainboard_20251231.csv \
  --start-date 2017-01-01 \
  --end-date 2026-04-30 \
  --raw-dir Explore1/data/raw/akshare/day/raw \
  --qfq-dir Explore1/data/raw/akshare/day/qfq
```

## 3. Transform To Qlib CSV

```bash
uv run python scripts/02_transform_to_qlib_csv.py \
  --universe Explore1/data/universe/mcap500_mainboard_20251231.csv \
  --raw-dir Explore1/data/raw/akshare/day/raw \
  --qfq-dir Explore1/data/raw/akshare/day/qfq \
  --output-dir Explore1/data/interim/qlib_csv/day \
  --start-date 2017-01-01 \
  --end-date 2026-04-30 \
  --instrument-output Explore1/data/universe/qlib_mcap500_mainboard_20251231.txt
```

## 4. Dump Qlib Bin

```bash
QLIB_DIR="$PWD/Explore1/data/qlib/cn_data" \
CSV_DIR="$PWD/Explore1/data/interim/qlib_csv/day" \
QLIB_INSTRUMENT_FILE="$PWD/Explore1/data/universe/qlib_mcap500_mainboard_20251231.txt" \
QLIB_MARKET_NAME="mcap500_mainboard_20251231" \
bash scripts/03_dump_qlib_bin.sh
```

## 5. Check Data

```bash
uv run python scripts/04_check_qlib_data.py \
  --csv-dir Explore1/data/interim/qlib_csv/day \
  --qlib-dir Explore1/data/qlib/cn_data \
  --report Explore1/outputs/reports/data_quality_report.csv \
  --check-provider
```

## 6. Train Alpha158 + LightGBM

```bash
uv run qrun Explore1/configs/qlib_lightgbm_alpha158_mcap500.yaml -e alpha158_lightgbm_mcap500
```

## 7. Run TopK Grid

```bash
uv run python Explore1/scripts/backtest_alpha158_grid.py
```

This runs all 9 combinations:

```text
topk: 30, 50, 100
n_drop: 3, 5, 10
```

## 8. Run Equal-Weight Baseline

```bash
uv run python Explore1/scripts/run_equal_weight_benchmark.py
```

The baseline rebalances monthly and uses the same universe, costs, benchmark, and backtest window.

## 9. Collect Report

```bash
uv run python Explore1/scripts/collect_explore1_report.py
```

Outputs:

```text
Explore1/outputs/reports/explore1_summary.csv
Explore1/outputs/reports/explore1_report.md
```
