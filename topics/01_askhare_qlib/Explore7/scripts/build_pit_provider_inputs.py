#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd


TOPIC_DIR = Path(__file__).resolve().parents[2]
BENCHMARK_INSTRUMENT = "SH000300"


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Explore7 PIT provider input files.")
    parser.add_argument("--qlib-instruments", default="Explore7/data/universe/qlib_pit_mcap500_mainboard.txt")
    parser.add_argument("--membership", default="Explore7/data/universe/pit_mcap500_mainboard_daily.csv")
    parser.add_argument("--universe-output", default="Explore7/data/universe/pit_qlib_instrument_universe.csv")
    parser.add_argument("--source-raw-dir", default="Explore1/data/raw/akshare/day/raw")
    parser.add_argument("--source-qfq-dir", default="Explore1/data/raw/akshare/day/qfq")
    parser.add_argument("--source-qlib-csv-dir", default="Explore1/data/interim/qlib_csv/day")
    parser.add_argument("--target-raw-dir", default="Explore7/data/raw/akshare/day/raw")
    parser.add_argument("--target-qfq-dir", default="Explore7/data/raw/akshare/day/qfq")
    parser.add_argument("--target-qlib-csv-dir", default="Explore7/data/interim/qlib_csv/day")
    parser.add_argument("--summary-output", default="Explore7/outputs/reports/pit_provider_input_summary.json")
    parser.add_argument("--missing-output", default="Explore7/outputs/reports/pit_provider_missing_fetch_symbols.txt")
    parser.add_argument("--force-copy", action="store_true")
    return parser.parse_args()


def read_qlib_instruments(path: Path) -> list[str]:
    instruments: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if not parts:
                continue
            instrument = parts[0].upper()
            if instrument not in seen:
                instruments.append(instrument)
                seen.add(instrument)
    if not instruments:
        raise ValueError(f"no instruments found in {path}")
    return instruments


def latest_names(membership_path: Path) -> dict[str, str]:
    df = pd.read_csv(membership_path, usecols=["instrument", "name"], dtype={"instrument": "string", "name": "string"})
    df["instrument"] = df["instrument"].str.upper()
    return df.dropna(subset=["instrument"]).drop_duplicates("instrument", keep="last").set_index("instrument")["name"].to_dict()


def write_universe(instruments: list[str], names: dict[str, str], output_path: Path) -> pd.DataFrame:
    rows = []
    for instrument in instruments:
        rows.append(
            {
                "code": instrument[2:],
                "name": names.get(instrument, instrument),
                "instrument": instrument,
                "exchange": instrument[:2],
            }
        )
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return df


def copy_available(instruments: list[str], source_dir: Path, target_dir: Path, force: bool) -> tuple[int, list[str]]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    missing: list[str] = []
    for instrument in instruments:
        source = source_dir / f"{instrument}.csv"
        target = target_dir / f"{instrument}.csv"
        if not source.exists():
            missing.append(instrument)
            continue
        if target.exists() and not force:
            continue
        shutil.copy2(source, target)
        copied += 1
    return copied, missing


def present_count(instruments: list[str], directory: Path) -> tuple[int, int]:
    present = {path.stem for path in directory.glob("*.csv")}
    wanted = set(instruments)
    return len(wanted & present), len(wanted - present)


def main() -> int:
    args = parse_args()
    qlib_path = topic_path(args.qlib_instruments)
    membership_path = topic_path(args.membership)
    universe_output = topic_path(args.universe_output)
    summary_output = topic_path(args.summary_output)
    missing_output = topic_path(args.missing_output)

    instruments = read_qlib_instruments(qlib_path)
    names = latest_names(membership_path)
    universe = write_universe(instruments, names, universe_output)

    copy_instruments = instruments + [BENCHMARK_INSTRUMENT]
    raw_copied, raw_missing = copy_available(
        copy_instruments,
        topic_path(args.source_raw_dir),
        topic_path(args.target_raw_dir),
        args.force_copy,
    )
    qfq_copied, qfq_missing = copy_available(
        copy_instruments,
        topic_path(args.source_qfq_dir),
        topic_path(args.target_qfq_dir),
        args.force_copy,
    )
    qlib_copied, qlib_missing = copy_available(
        copy_instruments,
        topic_path(args.source_qlib_csv_dir),
        topic_path(args.target_qlib_csv_dir),
        args.force_copy,
    )

    missing_to_fetch = sorted(set(raw_missing).union(qfq_missing).difference({BENCHMARK_INSTRUMENT}))
    missing_output.parent.mkdir(parents=True, exist_ok=True)
    missing_output.write_text("\n".join(missing_to_fetch) + ("\n" if missing_to_fetch else ""), encoding="utf-8")

    target_raw_present, target_raw_missing = present_count(copy_instruments, topic_path(args.target_raw_dir))
    target_qfq_present, target_qfq_missing = present_count(copy_instruments, topic_path(args.target_qfq_dir))
    target_qlib_present, target_qlib_missing = present_count(copy_instruments, topic_path(args.target_qlib_csv_dir))
    summary = {
        "qlib_instruments": relpath(qlib_path),
        "membership": relpath(membership_path),
        "universe_output": relpath(universe_output),
        "universe_rows": int(len(universe)),
        "unique_instruments": int(universe["instrument"].nunique()),
        "missing_names": int((universe["name"] == universe["instrument"]).sum()),
        "copied_raw_files": raw_copied,
        "copied_qfq_files": qfq_copied,
        "copied_qlib_csv_files": qlib_copied,
        "source_raw_missing_for_copy": len(raw_missing),
        "source_qfq_missing_for_copy": len(qfq_missing),
        "source_qlib_csv_missing_for_copy": len(qlib_missing),
        "missing_fetch_symbols_initial": len(missing_to_fetch),
        "missing_fetch_symbols_file": relpath(missing_output),
        "target_raw_files_present": target_raw_present,
        "target_raw_missing_after_build": target_raw_missing,
        "target_qfq_files_present": target_qfq_present,
        "target_qfq_missing_after_build": target_qfq_missing,
        "target_qlib_csv_files_present": target_qlib_present,
        "target_qlib_csv_missing_after_build": target_qlib_missing,
        "benchmark_included_for_provider": BENCHMARK_INSTRUMENT,
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
