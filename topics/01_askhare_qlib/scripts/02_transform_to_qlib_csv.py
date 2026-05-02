#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline_utils import (
    TOPIC_DIR,
    filter_universe,
    load_universe,
    qlib_date,
    topic_path,
    write_qlib_instrument_file,
)


BENCHMARK_INSTRUMENT = "SH000300"
OUTPUT_COLUMNS = ["date", "open", "close", "high", "low", "volume", "money", "factor"]
CHINESE_RENAME = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "money",
}
ENGLISH_RENAME = {
    "amount": "money",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform AkShare CSV files into Qlib dump_bin CSV format.")
    parser.add_argument("--universe", default="data/universe/selected_stock_pool.csv")
    parser.add_argument("--raw-dir", default="data/raw/akshare/day/raw")
    parser.add_argument("--qfq-dir", default="data/raw/akshare/day/qfq")
    parser.add_argument("--output-dir", default="data/interim/qlib_csv/day")
    parser.add_argument("--symbols", nargs="*", help="Optional stock codes or Qlib instruments to transform.")
    parser.add_argument("--limit", type=int, help="Transform only the first N instruments after filtering.")
    parser.add_argument("--include-benchmark", action="store_true", default=True)
    parser.add_argument("--skip-benchmark", action="store_false", dest="include_benchmark")
    parser.add_argument("--start-date", default="2017-01-01", help="Used for generated Qlib instrument files.")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="Used for generated Qlib instrument files.")
    parser.add_argument(
        "--instrument-output",
        default="data/universe/qlib_selected.txt",
        help="Path for the generated Qlib instrument file.",
    )
    parser.add_argument(
        "--volume-multiplier",
        type=float,
        default=100.0,
        help="AkShare A-share stock volume is usually in hands; use 100 to convert to shares.",
    )
    parser.add_argument(
        "--adjust-volume-by-factor",
        action="store_true",
        help="Divide raw volume by factor. Disabled by default to preserve real traded volume.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing Qlib CSV files.")
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def read_source(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype={"股票代码": "string"})


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns=CHINESE_RENAME).rename(columns=ENGLISH_RENAME).copy()
    required = {"date", "open", "close", "high", "low", "volume"}
    missing = required.difference(renamed.columns)
    if missing:
        raise ValueError(f"missing columns after rename: {sorted(missing)}")
    if "money" not in renamed.columns:
        renamed["money"] = np.nan

    keep = ["date", "open", "close", "high", "low", "volume", "money"]
    out = renamed[keep].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for column in keep[1:]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["date", "open", "close", "high", "low", "volume"])
    out = out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    return out


def transform_one(raw_path: Path, qfq_path: Path | None, volume_multiplier: float, adjust_volume: bool) -> pd.DataFrame:
    raw = normalize_frame(read_source(raw_path))
    has_qfq = qfq_path is not None and qfq_path.exists()
    adjusted = normalize_frame(read_source(qfq_path)) if has_qfq else raw.copy()

    df = adjusted[["date", "open", "close", "high", "low"]].merge(
        raw[["date", "close", "volume", "money"]].rename(columns={"close": "raw_close"}),
        on="date",
        how="inner",
    )
    df["factor"] = np.where(df["raw_close"] > 0, df["close"] / df["raw_close"], np.nan)
    if not has_qfq:
        df["factor"] = 1.0

    df["volume"] = df["volume"] * volume_multiplier
    if adjust_volume:
        df["volume"] = np.where(df["factor"] > 0, df["volume"] / df["factor"], np.nan)

    df = df[OUTPUT_COLUMNS].replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["date", "open", "close", "high", "low", "volume", "factor"])
    df = df[df["factor"] > 0]
    df = df[df["open"] > 0]
    df = df[df["close"] > 0]
    df = df[df["high"] > 0]
    df = df[df["low"] > 0]
    df = df.sort_values("date").reset_index(drop=True)
    return df


def validate_ohlc(df: pd.DataFrame, instrument: str) -> list[str]:
    errors: list[str] = []
    if df.empty:
        return [f"{instrument}: empty output"]
    if df["date"].duplicated().any():
        errors.append(f"{instrument}: duplicated dates")
    dates = pd.to_datetime(df["date"], errors="coerce")
    if not dates.is_monotonic_increasing:
        errors.append(f"{instrument}: dates are not strictly increasing")
    high_floor = df[["open", "close", "low"]].max(axis=1)
    low_ceiling = df[["open", "close", "high"]].min(axis=1)
    if (df["high"] < high_floor).any():
        errors.append(f"{instrument}: high is below one of open/close/low")
    if (df["low"] > low_ceiling).any():
        errors.append(f"{instrument}: low is above one of open/close/high")
    if (df["volume"] < 0).any():
        errors.append(f"{instrument}: negative volume")
    if (df["factor"] <= 0).any():
        errors.append(f"{instrument}: non-positive factor")
    return errors


def write_qlib_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=OUTPUT_COLUMNS, float_format="%.10g")


def main() -> int:
    args = parse_args()
    raw_dir = topic_path(args.raw_dir)
    qfq_dir = topic_path(args.qfq_dir)
    output_dir = topic_path(args.output_dir)
    universe = filter_universe(load_universe(args.universe), args.symbols, args.limit)

    instruments = list(universe["instrument"])
    if args.include_benchmark:
        instruments.append(BENCHMARK_INSTRUMENT)

    failures: list[str] = []
    for instrument in instruments:
        output_path = output_dir / f"{instrument}.csv"
        if output_path.exists() and not args.force:
            print(f"skip existing {output_path.relative_to(TOPIC_DIR)}")
            continue

        raw_path = raw_dir / f"{instrument}.csv"
        qfq_path = qfq_dir / f"{instrument}.csv"
        try:
            df = transform_one(raw_path, qfq_path, args.volume_multiplier, args.adjust_volume_by_factor)
            errors = validate_ohlc(df, instrument)
            if errors:
                raise ValueError("; ".join(errors))
            write_qlib_csv(df, output_path)
            print(f"wrote {output_path.relative_to(TOPIC_DIR)} rows={len(df)}")
        except Exception as exc:
            message = f"{instrument}: {exc}"
            failures.append(message)
            print(f"ERROR {message}", file=sys.stderr)
            if args.fail_fast:
                break

    write_qlib_instrument_file(
        universe,
        args.instrument_output,
        qlib_date(args.start_date),
        qlib_date(args.end_date),
    )

    if failures:
        print("\nTransform completed with failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
