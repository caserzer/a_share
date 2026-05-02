#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline_utils import TOPIC_DIR, topic_path


FIELDS = ["open", "close", "high", "low", "volume", "money", "factor"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run data quality checks on generated Qlib CSV/bin data.")
    parser.add_argument("--csv-dir", default="data/interim/qlib_csv/day")
    parser.add_argument("--qlib-dir", default="data/qlib/cn_data")
    parser.add_argument("--sample-instrument", default="SZ000001")
    parser.add_argument("--start-time", default="2020-01-01")
    parser.add_argument("--end-time", default="2020-01-31")
    parser.add_argument("--report", default="outputs/reports/data_quality_report.csv")
    parser.add_argument("--check-provider", action="store_true", help="Also verify qlib.data.D can read a sample.")
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def check_csv(path: Path) -> dict[str, object]:
    instrument = path.stem
    row: dict[str, object] = {"instrument": instrument, "path": str(path.relative_to(TOPIC_DIR))}
    errors: list[str] = []

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        row.update(rows=0, errors=f"read failed: {exc}")
        return row

    row["rows"] = len(df)
    missing = set(["date", *FIELDS]).difference(df.columns)
    if missing:
        errors.append(f"missing columns {sorted(missing)}")
        row["errors"] = "; ".join(errors)
        return row

    dates = pd.to_datetime(df["date"], errors="coerce")
    row["start"] = dates.min().date().isoformat() if dates.notna().any() else ""
    row["end"] = dates.max().date().isoformat() if dates.notna().any() else ""
    row["duplicate_dates"] = int(df["date"].duplicated().sum())
    row["missing_values"] = int(df[["date", *FIELDS]].isna().sum().sum())

    if df.empty:
        errors.append("empty file")
    if row["duplicate_dates"]:
        errors.append("duplicated dates")
    if not dates.is_monotonic_increasing:
        errors.append("dates not increasing")

    numeric = df[FIELDS].apply(pd.to_numeric, errors="coerce")
    if (numeric[["open", "close", "high", "low"]] <= 0).any().any():
        errors.append("non-positive price")
    if (numeric["factor"] <= 0).any():
        errors.append("non-positive factor")
    if (numeric["volume"] < 0).any():
        errors.append("negative volume")
    if (numeric["money"].dropna() < 0).any():
        errors.append("negative money")

    high_floor = numeric[["open", "close", "low"]].max(axis=1)
    low_ceiling = numeric[["open", "close", "high"]].min(axis=1)
    if (numeric["high"] < high_floor).any():
        errors.append("high below open/close/low")
    if (numeric["low"] > low_ceiling).any():
        errors.append("low above open/close/high")

    close_jump = numeric["close"].pct_change().abs()
    row["max_abs_close_jump"] = float(close_jump.max(skipna=True) or 0.0)
    factor_jump = numeric["factor"].pct_change().abs()
    row["max_abs_factor_jump"] = float(factor_jump.max(skipna=True) or 0.0)
    row["errors"] = "; ".join(errors)
    return row


def check_provider(qlib_dir: Path, sample_instrument: str, start_time: str, end_time: str) -> None:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(qlib_dir), region=REG_CN)
    df = D.features(
        instruments=[sample_instrument],
        fields=["$open", "$close", "$high", "$low", "$volume", "$factor"],
        start_time=start_time,
        end_time=end_time,
        freq="day",
    )
    if df.empty:
        raise RuntimeError(f"Qlib provider returned no rows for {sample_instrument}")
    print(df.tail())


def main() -> int:
    args = parse_args()
    csv_dir = topic_path(args.csv_dir)
    report_path = topic_path(args.report)
    qlib_dir = topic_path(args.qlib_dir)

    files = sorted(csv_dir.glob("*.csv"))
    if not files:
        print(f"No Qlib CSV files found in {csv_dir}", file=sys.stderr)
        return 1

    rows = [check_csv(path) for path in files]
    report = pd.DataFrame(rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(report_path, index=False)

    error_rows = report[report["errors"].fillna("") != ""]
    summary = {
        "files": len(report),
        "rows": int(report["rows"].sum()),
        "files_with_errors": int(len(error_rows)),
        "report": str(report_path.relative_to(TOPIC_DIR)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check_provider:
        try:
            check_provider(qlib_dir, args.sample_instrument, args.start_time, args.end_time)
        except ImportError as exc:
            print(f"Qlib import failed: {exc}", file=sys.stderr)
            return 1

    if args.fail_on_error and not error_rows.empty:
        print(error_rows[["instrument", "errors"]].to_string(index=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

