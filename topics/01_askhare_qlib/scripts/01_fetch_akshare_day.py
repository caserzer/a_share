#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline_utils import (
    TOPIC_DIR,
    ak_date,
    akshare_index_symbol,
    filter_universe,
    load_universe,
    qlib_date,
    topic_path,
)


BENCHMARK_INSTRUMENT = "SH000300"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch A-share daily bars from AkShare.")
    parser.add_argument("--universe", default="data/universe/selected_stock_pool.csv")
    parser.add_argument("--start-date", default="2017-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--symbols", nargs="*", help="Optional stock codes or Qlib instruments to fetch.")
    parser.add_argument("--symbols-file", help="Optional newline-delimited stock codes or Qlib instruments to fetch.")
    parser.add_argument("--limit", type=int, help="Fetch only the first N instruments after filtering.")
    parser.add_argument("--raw-dir", default="data/raw/akshare/day/raw")
    parser.add_argument("--qfq-dir", default="data/raw/akshare/day/qfq")
    parser.add_argument("--skip-qfq", action="store_true", help="Fetch only unadjusted stock data.")
    parser.add_argument("--skip-benchmark", action="store_true", help="Do not fetch SH000300 benchmark index data.")
    parser.add_argument("--sleep", type=float, default=0.3, help="Seconds to sleep between AkShare calls.")
    parser.add_argument("--timeout", type=float, default=20.0, help="AkShare HTTP timeout where supported.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing CSV files.")
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def load_symbols(args: argparse.Namespace) -> list[str] | None:
    symbols = list(args.symbols or [])
    if args.symbols_file:
        path = topic_path(args.symbols_file)
        with path.open("r", encoding="utf-8") as file:
            symbols.extend(line.strip() for line in file if line.strip() and not line.lstrip().startswith("#"))
    return symbols or None


def save_frame(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def stock_symbol_with_market(code: str) -> str:
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "2", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    raise ValueError(f"Cannot infer market prefix for {code}")


def normalize_akshare_daily(df: pd.DataFrame, code: str, volume_in_shares: bool) -> pd.DataFrame:
    renamed = df.rename(columns={"date": "日期", "open": "开盘", "close": "收盘", "high": "最高", "low": "最低", "volume": "成交量", "amount": "成交额"}).copy()
    if "成交量" not in renamed.columns and "成交额" in renamed.columns:
        # Tencent's endpoint names traded hands as amount and does not provide money.
        renamed["成交量"] = renamed["成交额"]
        renamed["成交额"] = pd.NA
    if volume_in_shares and "成交量" in renamed.columns:
        renamed["成交量"] = pd.to_numeric(renamed["成交量"], errors="coerce") / 100.0
    renamed["股票代码"] = code
    for column in ["振幅", "涨跌幅", "涨跌额", "换手率"]:
        if column not in renamed.columns:
            renamed[column] = pd.NA
    columns = ["日期", "股票代码", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
    return renamed[columns]


def fetch_stock_sina(ak, code: str, start_date: str, end_date: str, adjust: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(
        symbol=stock_symbol_with_market(code),
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    return normalize_akshare_daily(df, code, volume_in_shares=True)


def fetch_stock_tencent(ak, code: str, start_date: str, end_date: str, adjust: str, timeout: float) -> pd.DataFrame:
    df = ak.stock_zh_a_hist_tx(
        symbol=stock_symbol_with_market(code),
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
        timeout=timeout,
    )
    return normalize_akshare_daily(df, code, volume_in_shares=False)


def fetch_stock(ak, code: str, start_date: str, end_date: str, adjust: str, timeout: float) -> pd.DataFrame:
    try:
        return ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            timeout=timeout,
        )
    except Exception as eastmoney_error:
        try:
            print(f"fallback sina stock_zh_a_daily {code} {adjust or 'raw'}: {eastmoney_error}", file=sys.stderr)
            return fetch_stock_sina(ak, code, start_date, end_date, adjust)
        except Exception as sina_error:
            print(f"fallback tencent stock_zh_a_hist_tx {code} {adjust or 'raw'}: {sina_error}", file=sys.stderr)
            return fetch_stock_tencent(ak, code, start_date, end_date, adjust, timeout)


def fetch_benchmark(ak, instrument: str, start_date: str, end_date: str) -> pd.DataFrame:
    symbol = akshare_index_symbol(instrument)
    try:
        df = ak.stock_zh_index_daily_em(symbol=symbol, start_date=start_date, end_date=end_date)
    except Exception as eastmoney_error:
        print(f"fallback sina stock_zh_index_daily {instrument}: {eastmoney_error}", file=sys.stderr)
        df = pd.DataFrame()
    if df.empty:
        df = ak.stock_zh_index_daily(symbol=symbol)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            start = pd.to_datetime(qlib_date(start_date))
            end = pd.to_datetime(qlib_date(end_date))
            df = df[(df["date"] >= start) & (df["date"] <= end)]
    return df


def maybe_fetch(path: Path, force: bool, fetcher) -> bool:
    if path.exists() and not force:
        print(f"skip existing {path.relative_to(TOPIC_DIR)}")
        return False
    df = fetcher()
    if df.empty:
        raise RuntimeError(f"AkShare returned no rows for {path.name}")
    save_frame(df, path)
    print(f"wrote {path.relative_to(TOPIC_DIR)} rows={len(df)}")
    return True


def main() -> int:
    args = parse_args()
    import akshare as ak

    raw_dir = topic_path(args.raw_dir)
    qfq_dir = topic_path(args.qfq_dir)
    universe = filter_universe(load_universe(args.universe), load_symbols(args), args.limit)
    start = ak_date(args.start_date)
    end = ak_date(args.end_date)

    failures: list[str] = []
    for row in universe.itertuples(index=False):
        instrument = row.instrument
        code = row.code
        try:
            wrote = maybe_fetch(
                raw_dir / f"{instrument}.csv",
                args.force,
                lambda code=code: fetch_stock(ak, code, start, end, "", args.timeout),
            )
            if wrote:
                time.sleep(args.sleep)
            if not args.skip_qfq:
                wrote = maybe_fetch(
                    qfq_dir / f"{instrument}.csv",
                    args.force,
                    lambda code=code: fetch_stock(ak, code, start, end, "qfq", args.timeout),
                )
                if wrote:
                    time.sleep(args.sleep)
        except Exception as exc:
            message = f"{instrument}: {exc}"
            failures.append(message)
            print(f"ERROR {message}", file=sys.stderr)
            if args.fail_fast:
                break

    if not args.skip_benchmark:
        benchmark_raw = raw_dir / f"{BENCHMARK_INSTRUMENT}.csv"
        try:
            wrote = maybe_fetch(
                benchmark_raw,
                args.force,
                lambda: fetch_benchmark(ak, BENCHMARK_INSTRUMENT, start, end),
            )
            if wrote and not args.skip_qfq:
                qfq_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(benchmark_raw, qfq_dir / benchmark_raw.name)
                print(f"copied benchmark to {(qfq_dir / benchmark_raw.name).relative_to(TOPIC_DIR)}")
        except Exception as exc:
            message = f"{BENCHMARK_INSTRUMENT}: {exc}"
            failures.append(message)
            print(f"ERROR {message}", file=sys.stderr)

    if failures:
        print("\nFetch completed with failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
