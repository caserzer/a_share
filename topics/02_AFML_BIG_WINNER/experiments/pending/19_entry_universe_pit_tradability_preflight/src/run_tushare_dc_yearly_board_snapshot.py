#!/usr/bin/env python3
"""Fetch yearly first-open-day Eastmoney board snapshots from Tushare.

This script uses Tushare Pro's Eastmoney board endpoints:

- dc_index: board list/status by trade date and board type.
- dc_member: board constituents by trade date and board code.

For each classification year, it records the first open A-share trading day from
trade_cal. Because Tushare DC board data is unavailable before 2025, years before
2025 are assigned the 2025 first-open snapshot as a fixed taxonomy backfill. 2025
uses the 2025 snapshot, and 2026 uses the 2026 snapshot. The output keeps both
the classification year and the source snapshot year/date explicit.

Recommended run:

    TUSHARE_TOKEN=... \
      python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_tushare_dc_yearly_board_snapshot.py
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_DIR = (
    "topics/02_AFML_BIG_WINNER/experiments/pending/"
    "19_entry_universe_pit_tradability_preflight/outputs/"
    "tushare_dc_yearly_board_snapshot"
)

BOARD_FIELDS = (
    "ts_code,trade_date,name,leading,leading_code,pct_change,leading_pct,"
    "total_mv,turnover_rate,up_num,down_num,idx_type,level"
)
MEMBER_FIELDS = "trade_date,ts_code,con_code,name"
CALENDAR_FIELDS = "exchange,cal_date,is_open,pretrade_date"
DEFAULT_IDX_TYPES = ("概念板块",)
DEFAULT_BACKFILL_BEFORE_YEAR = 2025
DEFAULT_BACKFILL_SOURCE_YEAR = 2025
BOARD_OUTPUT_COLUMNS = [
    "fetched_at_utc",
    "classification_year",
    "effective_start_date",
    "effective_end_date",
    "classification_first_open_trade_date",
    "source_snapshot_year",
    "source_snapshot_trade_date",
    "snapshot_policy",
    "snapshot_trade_date",
    "source_api",
    "board_ts_code",
    "board_name",
    "idx_type",
    "level",
    "leading",
    "leading_code",
    "pct_change",
    "leading_pct",
    "total_mv",
    "turnover_rate",
    "up_num",
    "down_num",
]
MEMBER_OUTPUT_COLUMNS = [
    "fetched_at_utc",
    "classification_year",
    "effective_start_date",
    "effective_end_date",
    "classification_first_open_trade_date",
    "source_snapshot_year",
    "source_snapshot_trade_date",
    "snapshot_policy",
    "snapshot_trade_date",
    "source_api",
    "board_ts_code",
    "board_name",
    "idx_type",
    "level",
    "con_code",
    "con_name",
]


class CallTimeoutError(TimeoutError):
    pass


@dataclass(frozen=True)
class SnapshotYear:
    classification_year: int
    first_open_trade_date: str
    calendar_status: str
    calendar_error: str = ""


@contextlib.contextmanager
def time_limit(seconds: int):
    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise CallTimeoutError(f"call exceeded {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument(
        "--backfill-before-year", type=int, default=DEFAULT_BACKFILL_BEFORE_YEAR
    )
    parser.add_argument(
        "--backfill-source-year", type=int, default=DEFAULT_BACKFILL_SOURCE_YEAR
    )
    parser.add_argument(
        "--idx-type",
        action="append",
        default=[],
        help="Board type to fetch; repeatable. Defaults to Tushare DC concept boards.",
    )
    parser.add_argument("--calendar-exchange", default="SSE")
    parser.add_argument("--token-env", default="TUSHARE_TOKEN")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=2.0)
    parser.add_argument("--rate-sleep", type=float, default=0.18)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--no-resume-existing",
        action="store_true",
        help="Refetch member files even when per-board CSVs already exist.",
    )
    parser.add_argument(
        "--max-boards-per-snapshot",
        type=int,
        default=0,
        help="Debug limit per year after dc_index; 0 means all boards.",
    )
    parser.add_argument(
        "--no-members",
        action="store_true",
        help="Only fetch yearly board lists, not dc_member constituents.",
    )
    return parser.parse_args()


def clean_error(message: Any, limit: int = 1000) -> str:
    return str(message).replace("\n", " ").replace("\r", " ")[:limit]


def write_dataframe(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def append_manifest_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8",
    )


def call_pro(
    pro: Any,
    api_name: str,
    *,
    fields: str,
    params: dict[str, Any],
    timeout_seconds: int,
    retries: int,
    retry_sleep: float,
) -> tuple[str, pd.DataFrame | None, float, int, str, str]:
    last_error_type = ""
    last_error_message = ""
    total_elapsed = 0.0
    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            stderr_buffer = io.StringIO()
            with time_limit(timeout_seconds), contextlib.redirect_stderr(stderr_buffer):
                result = pro.query(api_name, fields=fields, **params)
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            if not isinstance(result, pd.DataFrame):
                return (
                    "non_dataframe",
                    None,
                    total_elapsed,
                    attempt + 1,
                    type(result).__name__,
                    "Tushare call returned a non-DataFrame object",
                )
            status = "ok" if not result.empty else "ok_empty"
            return status, result, total_elapsed, attempt + 1, "", ""
        except Exception as exc:  # noqa: BLE001 - endpoint harvesting must continue.
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            last_error_type = type(exc).__name__
            last_error_message = clean_error(exc)
            if attempt < retries:
                time.sleep(retry_sleep)

    status = "timeout" if last_error_type == "CallTimeoutError" else "error"
    return status, None, total_elapsed, retries + 1, last_error_type, last_error_message


def manifest_row(
    *,
    classification_year: int | str,
    snapshot_trade_date: str,
    dataset_id: str,
    api: str,
    idx_type: str,
    board_ts_code: str,
    board_name: str,
    output_path: str,
    status: str,
    rows: int | str,
    cols: int | str,
    elapsed_seconds: float,
    attempts: int,
    error_type: str,
    error_message: str,
    classification_first_open_trade_date: str = "",
    source_snapshot_year: int | str = "",
    source_snapshot_trade_date: str = "",
    snapshot_policy: str = "",
) -> dict[str, Any]:
    return {
        "classification_year": classification_year,
        "snapshot_trade_date": snapshot_trade_date,
        "classification_first_open_trade_date": classification_first_open_trade_date,
        "source_snapshot_year": source_snapshot_year,
        "source_snapshot_trade_date": source_snapshot_trade_date,
        "snapshot_policy": snapshot_policy,
        "dataset_id": dataset_id,
        "api": api,
        "idx_type": idx_type,
        "board_ts_code": board_ts_code,
        "board_name": board_name,
        "output_path": output_path,
        "status": status,
        "rows": rows,
        "cols": cols,
        "elapsed_seconds": f"{elapsed_seconds:.3f}",
        "attempts": attempts,
        "error_type": error_type,
        "error_message": error_message,
    }


def effective_start(year: int) -> str:
    return f"{year}-01-01"


def effective_end(year: int) -> str:
    return f"{year}-12-31"


def normalize_board_df(
    df: pd.DataFrame,
    *,
    classification_year: int,
    idx_type_requested: str,
    fetched_at_utc: str,
) -> pd.DataFrame:
    out = df.copy()
    if "idx_type" not in out.columns:
        out["idx_type"] = idx_type_requested
    out = out.rename(columns={"ts_code": "board_ts_code", "name": "board_name"})
    for column in ("board_ts_code", "trade_date", "board_name"):
        if column not in out.columns:
            out[column] = ""
    out["snapshot_trade_date"] = out["trade_date"].astype(str)
    out["classification_first_open_trade_date"] = out["snapshot_trade_date"]
    out["source_snapshot_year"] = classification_year
    out["source_snapshot_trade_date"] = out["snapshot_trade_date"]
    out["snapshot_policy"] = "exact_year_first_open_snapshot"
    out.insert(0, "source_api", "dc_index")
    out.insert(0, "effective_end_date", effective_end(classification_year))
    out.insert(0, "effective_start_date", effective_start(classification_year))
    out.insert(0, "classification_year", classification_year)
    out.insert(0, "fetched_at_utc", fetched_at_utc)
    return order_columns(out, BOARD_OUTPUT_COLUMNS)


def normalize_member_df(
    df: pd.DataFrame,
    *,
    board_row: pd.Series,
    classification_year: int,
    snapshot_trade_date: str,
    fetched_at_utc: str,
) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={"ts_code": "board_ts_code", "name": "con_name"})
    for column in ("board_ts_code", "con_code", "con_name"):
        if column not in out.columns:
            out[column] = ""
    out["snapshot_trade_date"] = snapshot_trade_date
    out["classification_first_open_trade_date"] = snapshot_trade_date
    out["source_snapshot_year"] = classification_year
    out["source_snapshot_trade_date"] = snapshot_trade_date
    out["snapshot_policy"] = "exact_year_first_open_snapshot"
    out["board_name"] = board_row.get("board_name", "")
    out["idx_type"] = board_row.get("idx_type", "")
    out["level"] = board_row.get("level", "")
    out.insert(0, "source_api", "dc_member")
    out.insert(0, "effective_end_date", effective_end(classification_year))
    out.insert(0, "effective_start_date", effective_start(classification_year))
    out.insert(0, "classification_year", classification_year)
    out.insert(0, "fetched_at_utc", fetched_at_utc)
    return order_columns(out, MEMBER_OUTPUT_COLUMNS)


def order_columns(df: pd.DataFrame, ordered: list[str]) -> pd.DataFrame:
    for column in ordered:
        if column not in df.columns:
            df[column] = ""
    rest = [column for column in df.columns if column not in ordered]
    return df[ordered + rest]


def snapshot_source_year(
    classification_year: int, *, backfill_before_year: int, backfill_source_year: int
) -> int:
    if classification_year < backfill_before_year:
        return backfill_source_year
    return classification_year


def snapshot_policy(classification_year: int, source_year: int) -> str:
    if classification_year == source_year:
        return "exact_year_first_open_snapshot"
    return f"pre_{source_year}_backfilled_from_{source_year}_snapshot"


def board_snapshot_path(
    output_dir: Path, year: int, trade_date: str, idx_type: str
) -> Path:
    return (
        output_dir
        / "by_year"
        / str(year)
        / f"dc_index_{year}_{trade_date}_{idx_type}.csv"
    )


def annual_member_path(output_dir: Path, year: int, trade_date: str) -> Path:
    return output_dir / "by_year" / str(year) / f"dc_member_{year}_{trade_date}.csv"


def remap_snapshot_df(
    df: pd.DataFrame,
    *,
    output_columns: list[str],
    classification_year: int,
    classification_first_open_trade_date: str,
    source_snapshot_year: int,
    source_snapshot_trade_date: str,
    policy: str,
) -> pd.DataFrame:
    out = df.copy()
    out["classification_year"] = classification_year
    out["effective_start_date"] = effective_start(classification_year)
    out["effective_end_date"] = effective_end(classification_year)
    out["classification_first_open_trade_date"] = classification_first_open_trade_date
    out["source_snapshot_year"] = source_snapshot_year
    out["source_snapshot_trade_date"] = source_snapshot_trade_date
    out["snapshot_policy"] = policy
    out["snapshot_trade_date"] = source_snapshot_trade_date
    return order_columns(out, output_columns)


def load_year_calendar(
    pro: Any,
    *,
    years: list[int],
    exchange: str,
    timeout_seconds: int,
    retries: int,
    retry_sleep: float,
    manifest_path: Path,
) -> list[SnapshotYear]:
    rows: list[SnapshotYear] = []
    calendar_rows: list[dict[str, Any]] = []
    for year in years:
        start_date = f"{year}0101"
        end_date = f"{year}0115"
        status, df, elapsed, attempts, error_type, error_message = call_pro(
            pro,
            "trade_cal",
            fields=CALENDAR_FIELDS,
            params={
                "exchange": exchange,
                "start_date": start_date,
                "end_date": end_date,
            },
            timeout_seconds=timeout_seconds,
            retries=retries,
            retry_sleep=retry_sleep,
        )
        first_open = ""
        if df is not None and not df.empty and "is_open" in df.columns:
            open_days = df.loc[
                pd.to_numeric(df["is_open"], errors="coerce").eq(1)
            ].copy()
            if not open_days.empty:
                open_days["cal_date"] = open_days["cal_date"].astype(str)
                first_open = str(open_days.sort_values("cal_date").iloc[0]["cal_date"])
        calendar_status = "ok" if first_open else status
        if status == "ok" and not first_open:
            calendar_status = "no_open_day_found"
        rows.append(SnapshotYear(year, first_open, calendar_status, error_message))
        calendar_rows.append(
            {
                "classification_year": year,
                "calendar_start_date": start_date,
                "calendar_end_date": end_date,
                "calendar_exchange": exchange,
                "first_open_trade_date": first_open,
                "calendar_status": calendar_status,
                "calendar_error_type": error_type,
                "calendar_error_message": error_message,
            }
        )
        append_manifest_row(
            manifest_path,
            manifest_row(
                classification_year=year,
                snapshot_trade_date=first_open,
                dataset_id="trade_cal_first_open",
                api="trade_cal",
                idx_type="",
                board_ts_code="",
                board_name="",
                output_path="",
                status=calendar_status,
                rows=len(df) if df is not None else "",
                cols=len(df.columns) if df is not None else "",
                elapsed_seconds=elapsed,
                attempts=attempts,
                error_type=error_type,
                error_message=error_message,
            ),
        )
    write_dataframe(
        manifest_path.parent / "year_first_trade_dates.csv", pd.DataFrame(calendar_rows)
    )
    return rows


def load_cached_board(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def fetch_board_snapshot(
    pro: Any,
    *,
    year: SnapshotYear,
    idx_type: str,
    fetched_at_utc: str,
    output_dir: Path,
    timeout_seconds: int,
    retries: int,
    retry_sleep: float,
    resume_existing: bool,
    manifest_path: Path,
) -> pd.DataFrame:
    path = board_snapshot_path(
        output_dir, year.classification_year, year.first_open_trade_date, idx_type
    )
    if resume_existing and path.exists():
        df = load_cached_board(path)
        append_manifest_row(
            manifest_path,
            manifest_row(
                classification_year=year.classification_year,
                snapshot_trade_date=year.first_open_trade_date,
                classification_first_open_trade_date=year.first_open_trade_date,
                source_snapshot_year=year.classification_year,
                source_snapshot_trade_date=year.first_open_trade_date,
                snapshot_policy="exact_year_first_open_snapshot",
                dataset_id="dc_index_yearly_first_open",
                api="dc_index",
                idx_type=idx_type,
                board_ts_code="",
                board_name="",
                output_path=str(path),
                status="ok_cached",
                rows=len(df),
                cols=len(df.columns),
                elapsed_seconds=0.0,
                attempts=0,
                error_type="",
                error_message="",
            ),
        )
        return df

    status, df, elapsed, attempts, error_type, error_message = call_pro(
        pro,
        "dc_index",
        fields=BOARD_FIELDS,
        params={"trade_date": year.first_open_trade_date, "idx_type": idx_type},
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    normalized = pd.DataFrame()
    rows: int | str = ""
    cols: int | str = ""
    output_path = ""
    if df is not None:
        normalized = normalize_board_df(
            df,
            classification_year=year.classification_year,
            idx_type_requested=idx_type,
            fetched_at_utc=fetched_at_utc,
        )
        write_dataframe(path, normalized)
        rows = len(normalized)
        cols = len(normalized.columns)
        output_path = str(path)

    append_manifest_row(
        manifest_path,
        manifest_row(
            classification_year=year.classification_year,
            snapshot_trade_date=year.first_open_trade_date,
            classification_first_open_trade_date=year.first_open_trade_date,
            source_snapshot_year=year.classification_year,
            source_snapshot_trade_date=year.first_open_trade_date,
            snapshot_policy="exact_year_first_open_snapshot",
            dataset_id="dc_index_yearly_first_open",
            api="dc_index",
            idx_type=idx_type,
            board_ts_code="",
            board_name="",
            output_path=output_path,
            status=status,
            rows=rows,
            cols=cols,
            elapsed_seconds=elapsed,
            attempts=attempts,
            error_type=error_type,
            error_message=error_message,
        ),
    )
    return normalized


def board_member_path(
    output_dir: Path, year: int, trade_date: str, board_ts_code: str
) -> Path:
    safe_code = "".join(
        ch for ch in str(board_ts_code) if ch.isalnum() or ch in ("_", "-", ".")
    )
    return (
        output_dir
        / "by_year"
        / str(year)
        / "members"
        / f"dc_member_{trade_date}_{safe_code}.csv"
    )


def fetch_member_snapshot(
    pro: Any,
    *,
    board_row: pd.Series,
    classification_year: int,
    snapshot_trade_date: str,
    fetched_at_utc: str,
    output_dir: Path,
    timeout_seconds: int,
    retries: int,
    retry_sleep: float,
    resume_existing: bool,
    manifest_path: Path,
) -> pd.DataFrame:
    board_ts_code = str(board_row.get("board_ts_code", "")).strip()
    board_name = str(board_row.get("board_name", "")).strip()
    idx_type = str(board_row.get("idx_type", "")).strip()
    path = board_member_path(
        output_dir, classification_year, snapshot_trade_date, board_ts_code
    )
    if resume_existing and path.exists():
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        append_manifest_row(
            manifest_path,
            manifest_row(
                classification_year=classification_year,
                snapshot_trade_date=snapshot_trade_date,
                classification_first_open_trade_date=snapshot_trade_date,
                source_snapshot_year=classification_year,
                source_snapshot_trade_date=snapshot_trade_date,
                snapshot_policy="exact_year_first_open_snapshot",
                dataset_id="dc_member_yearly_first_open",
                api="dc_member",
                idx_type=idx_type,
                board_ts_code=board_ts_code,
                board_name=board_name,
                output_path=str(path),
                status="ok_cached",
                rows=len(df),
                cols=len(df.columns),
                elapsed_seconds=0.0,
                attempts=0,
                error_type="",
                error_message="",
            ),
        )
        return df

    status, df, elapsed, attempts, error_type, error_message = call_pro(
        pro,
        "dc_member",
        fields=MEMBER_FIELDS,
        params={"trade_date": snapshot_trade_date, "ts_code": board_ts_code},
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    normalized = pd.DataFrame()
    rows: int | str = ""
    cols: int | str = ""
    output_path = ""
    if df is not None:
        normalized = normalize_member_df(
            df,
            board_row=board_row,
            classification_year=classification_year,
            snapshot_trade_date=snapshot_trade_date,
            fetched_at_utc=fetched_at_utc,
        )
        write_dataframe(path, normalized)
        rows = len(normalized)
        cols = len(normalized.columns)
        output_path = str(path)

    append_manifest_row(
        manifest_path,
        manifest_row(
            classification_year=classification_year,
            snapshot_trade_date=snapshot_trade_date,
            classification_first_open_trade_date=snapshot_trade_date,
            source_snapshot_year=classification_year,
            source_snapshot_trade_date=snapshot_trade_date,
            snapshot_policy="exact_year_first_open_snapshot",
            dataset_id="dc_member_yearly_first_open",
            api="dc_member",
            idx_type=idx_type,
            board_ts_code=board_ts_code,
            board_name=board_name,
            output_path=output_path,
            status=status,
            rows=rows,
            cols=cols,
            elapsed_seconds=elapsed,
            attempts=attempts,
            error_type=error_type,
            error_message=error_message,
        ),
    )
    return normalized


def write_combined_outputs(
    output_dir: Path, board_parts: list[pd.DataFrame], member_parts: list[pd.DataFrame]
) -> None:
    if board_parts:
        boards = pd.concat(board_parts, ignore_index=True, sort=False)
    else:
        boards = pd.DataFrame(columns=BOARD_OUTPUT_COLUMNS)
    if member_parts:
        members = pd.concat(member_parts, ignore_index=True, sort=False)
    else:
        members = pd.DataFrame(columns=MEMBER_OUTPUT_COLUMNS)
    write_dataframe(output_dir / "combined" / "dc_index_yearly_first_open.csv", boards)
    write_dataframe(
        output_dir / "combined" / "dc_member_yearly_first_open.csv", members
    )


def csv_row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        return len(pd.read_csv(path, usecols=[0]))
    except pd.errors.EmptyDataError:
        return 0


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def write_summary(output_dir: Path, manifest_path: Path) -> None:
    manifest = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    write_dataframe(output_dir / "metadata" / "call_manifest.csv", manifest)
    summary = (
        manifest.groupby(["dataset_id", "api", "idx_type", "status"], dropna=False)
        .agg(
            calls=("status", "size"),
            rows=("rows", lambda values: pd.to_numeric(values, errors="coerce").sum()),
        )
        .reset_index()
    )
    write_dataframe(output_dir / "metadata" / "dataset_summary.csv", summary)

    boards_path = output_dir / "combined" / "dc_index_yearly_first_open.csv"
    members_path = output_dir / "combined" / "dc_member_yearly_first_open.csv"
    board_rows = csv_row_count(boards_path)
    member_rows = csv_row_count(members_path)
    boards = read_csv_or_empty(boards_path)
    members = read_csv_or_empty(members_path)
    calendar = read_csv_or_empty(output_dir / "metadata" / "year_first_trade_dates.csv")
    mapping = read_csv_or_empty(
        output_dir / "metadata" / "classification_year_snapshot_mapping.csv"
    )

    board_counts: dict[str, int] = {}
    member_counts: dict[str, int] = {}
    member_board_counts: dict[str, int] = {}
    if not boards.empty and "classification_year" in boards.columns:
        board_counts = (
            boards.groupby("classification_year").size().astype(int).to_dict()
        )
    if not members.empty and "classification_year" in members.columns:
        member_counts = (
            members.groupby("classification_year").size().astype(int).to_dict()
        )
        member_board_counts = (
            members.groupby("classification_year")["board_ts_code"]
            .nunique()
            .astype(int)
            .to_dict()
        )

    coverage_lines: list[str] = []
    if not mapping.empty:
        coverage_lines.extend(
            [
                "",
                "## Year Coverage",
                "",
                "| classification_year | classification_first_open_trade_date | source_snapshot_year | source_snapshot_trade_date | snapshot_policy | board_rows | member_rows | boards_with_members |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for _, row in mapping.iterrows():
            year = str(row.get("classification_year", ""))
            coverage_lines.append(
                "| "
                + " | ".join(
                    [
                        year,
                        str(row.get("classification_first_open_trade_date", "")),
                        str(row.get("source_snapshot_year", "")),
                        str(row.get("source_snapshot_trade_date", "")),
                        str(row.get("snapshot_policy", "")),
                        str(board_counts.get(year, 0)),
                        str(member_counts.get(year, 0)),
                        str(member_board_counts.get(year, 0)),
                    ]
                )
                + " |"
            )
    elif not calendar.empty:
        coverage_lines.extend(
            [
                "",
                "## Year Coverage",
                "",
                "| classification_year | first_open_trade_date | board_rows | member_rows | boards_with_members |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for _, row in calendar.iterrows():
            year = str(row.get("classification_year", ""))
            coverage_lines.append(
                "| "
                + " | ".join(
                    [
                        year,
                        str(row.get("first_open_trade_date", "")),
                        str(board_counts.get(year, 0)),
                        str(member_counts.get(year, 0)),
                        str(member_board_counts.get(year, 0)),
                    ]
                )
                + " |"
            )

    lines = [
        "# Tushare DC Yearly Board Snapshot",
        "",
        "## Files",
        "",
        "- `combined/dc_index_yearly_first_open.csv`: yearly first-open-day board lists/status.",
        "- `combined/dc_member_yearly_first_open.csv`: yearly first-open-day board constituents.",
        "- `by_year/<year>/`: per-year board and per-board member source files.",
        "- `metadata/year_first_trade_dates.csv`: first open trading day used for each year.",
        "- `metadata/classification_year_snapshot_mapping.csv`: classification year to source snapshot mapping.",
        "- `metadata/call_manifest.csv`: every Tushare call and cache hit.",
        "- `metadata/dataset_summary.csv`: grouped status and row totals.",
        "",
        "## Interpretation",
        "",
        "- Source APIs: Tushare `dc_index` and `dc_member` for Eastmoney concept boards.",
        "- Years before 2025 are explicitly backfilled from the 2025 first-open TuShare DC snapshot.",
        "- 2025 uses the 2025 first-open snapshot; 2026 uses the 2026 first-open snapshot.",
        "- Effective policy: each mapped snapshot is recorded as that calendar year's board-classification contract.",
        "- Pre-2025 rows are a fixed taxonomy proxy, not historical PIT membership evidence.",
        "",
        "## Row Counts",
        "",
        f"- board_rows: `{board_rows}`",
        f"- member_rows: `{member_rows}`",
    ]
    lines.extend(coverage_lines)
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.start_year > args.end_year:
        print("--start-year must be <= --end-year", file=sys.stderr)
        return 2

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        print(f"missing token: set {args.token_env}", file=sys.stderr)
        return 2

    try:
        import tushare as ts
    except Exception as exc:  # noqa: BLE001 - environment probe.
        print(f"failed to import tushare: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata").mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "metadata" / "call_manifest_checkpoint.csv"
    checkpoint_path.unlink(missing_ok=True)

    fetched_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    idx_types = tuple(args.idx_type) if args.idx_type else DEFAULT_IDX_TYPES
    config = {
        "generated_at_utc": fetched_at_utc,
        "source": "tushare",
        "tushare_version": getattr(ts, "__version__", "unknown"),
        "token_env": args.token_env,
        "token_env_set": bool(token),
        "start_year": args.start_year,
        "end_year": args.end_year,
        "backfill_before_year": args.backfill_before_year,
        "backfill_source_year": args.backfill_source_year,
        "idx_types": list(idx_types),
        "calendar_exchange": args.calendar_exchange,
        "retries": args.retries,
        "retry_sleep": args.retry_sleep,
        "rate_sleep": args.rate_sleep,
        "timeout_seconds": args.timeout_seconds,
        "resume_existing": not args.no_resume_existing,
        "max_boards_per_snapshot": args.max_boards_per_snapshot,
        "no_members": args.no_members,
    }
    (output_dir / "metadata" / "run_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    requested_years = list(range(args.start_year, args.end_year + 1))
    source_years = sorted(
        {
            snapshot_source_year(
                year,
                backfill_before_year=args.backfill_before_year,
                backfill_source_year=args.backfill_source_year,
            )
            for year in requested_years
        }
    )
    calendar_years = sorted(set(requested_years) | set(source_years))

    pro = ts.pro_api(token)
    years = load_year_calendar(
        pro,
        years=calendar_years,
        exchange=args.calendar_exchange,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        retry_sleep=args.retry_sleep,
        manifest_path=checkpoint_path,
    )
    year_by_number = {item.classification_year: item for item in years}

    mapping_rows: list[dict[str, Any]] = []
    for classification_year in requested_years:
        target_snapshot = year_by_number.get(classification_year)
        source_year = snapshot_source_year(
            classification_year,
            backfill_before_year=args.backfill_before_year,
            backfill_source_year=args.backfill_source_year,
        )
        source_snapshot = year_by_number.get(source_year)
        policy = snapshot_policy(classification_year, source_year)
        target_trade_date = (
            target_snapshot.first_open_trade_date if target_snapshot is not None else ""
        )
        source_trade_date = (
            source_snapshot.first_open_trade_date if source_snapshot is not None else ""
        )
        mapping_status = "ok" if target_trade_date and source_trade_date else "blocked"
        mapping_rows.append(
            {
                "classification_year": classification_year,
                "classification_first_open_trade_date": target_trade_date,
                "source_snapshot_year": source_year,
                "source_snapshot_trade_date": source_trade_date,
                "snapshot_policy": policy,
                "mapping_status": mapping_status,
                "classification_calendar_status": (
                    target_snapshot.calendar_status
                    if target_snapshot is not None
                    else "missing_calendar"
                ),
                "source_calendar_status": (
                    source_snapshot.calendar_status
                    if source_snapshot is not None
                    else "missing_calendar"
                ),
            }
        )
    write_dataframe(
        output_dir / "metadata" / "classification_year_snapshot_mapping.csv",
        pd.DataFrame(mapping_rows),
    )

    board_parts: list[pd.DataFrame] = []
    member_parts: list[pd.DataFrame] = []
    resume_existing = not args.no_resume_existing
    source_boards_cache: dict[tuple[int, str], pd.DataFrame] = {}
    source_members_cache: dict[tuple[int, tuple[str, ...], int], pd.DataFrame] = {}

    for classification_year in requested_years:
        target_snapshot = year_by_number.get(classification_year)
        source_year = snapshot_source_year(
            classification_year,
            backfill_before_year=args.backfill_before_year,
            backfill_source_year=args.backfill_source_year,
        )
        source_snapshot = year_by_number.get(source_year)
        policy = snapshot_policy(classification_year, source_year)
        if (
            target_snapshot is None
            or source_snapshot is None
            or not target_snapshot.first_open_trade_date
            or not source_snapshot.first_open_trade_date
        ):
            print(
                f"skip classification_year={classification_year} "
                f"source_year={source_year} calendar_status=blocked",
                flush=True,
            )
            continue

        target_board_parts: list[pd.DataFrame] = []
        for idx_type in idx_types:
            source_key = (source_year, idx_type)
            if source_key not in source_boards_cache:
                source_boards_cache[source_key] = fetch_board_snapshot(
                    pro,
                    year=source_snapshot,
                    idx_type=idx_type,
                    fetched_at_utc=fetched_at_utc,
                    output_dir=output_dir,
                    timeout_seconds=args.timeout_seconds,
                    retries=args.retries,
                    retry_sleep=args.retry_sleep,
                    resume_existing=resume_existing,
                    manifest_path=checkpoint_path,
                )
                if args.rate_sleep > 0:
                    time.sleep(args.rate_sleep)

            source_boards = source_boards_cache[source_key]
            target_boards = remap_snapshot_df(
                source_boards,
                output_columns=BOARD_OUTPUT_COLUMNS,
                classification_year=classification_year,
                classification_first_open_trade_date=target_snapshot.first_open_trade_date,
                source_snapshot_year=source_year,
                source_snapshot_trade_date=source_snapshot.first_open_trade_date,
                policy=policy,
            )
            target_board_path = board_snapshot_path(
                output_dir,
                classification_year,
                target_snapshot.first_open_trade_date,
                idx_type,
            )
            write_dataframe(target_board_path, target_boards)
            append_manifest_row(
                checkpoint_path,
                manifest_row(
                    classification_year=classification_year,
                    snapshot_trade_date=source_snapshot.first_open_trade_date,
                    classification_first_open_trade_date=target_snapshot.first_open_trade_date,
                    source_snapshot_year=source_year,
                    source_snapshot_trade_date=source_snapshot.first_open_trade_date,
                    snapshot_policy=policy,
                    dataset_id="dc_index_classification_contract",
                    api="dc_index",
                    idx_type=idx_type,
                    board_ts_code="",
                    board_name="",
                    output_path=str(target_board_path),
                    status="mapped_from_source_snapshot",
                    rows=len(target_boards),
                    cols=len(target_boards.columns),
                    elapsed_seconds=0.0,
                    attempts=0,
                    error_type="",
                    error_message="",
                ),
            )
            if not target_boards.empty:
                target_board_parts.append(target_boards)
                board_parts.append(target_boards)
            print(
                f"classification_year={classification_year} "
                f"source_year={source_year} "
                f"source_trade_date={source_snapshot.first_open_trade_date} "
                f"idx_type={idx_type} boards={len(target_boards)}",
                flush=True,
            )

        if args.no_members or not target_board_parts:
            continue

        source_member_key = (source_year, idx_types, args.max_boards_per_snapshot)
        if source_member_key not in source_members_cache:
            source_board_frames = [
                source_boards_cache.get((source_year, idx_type), pd.DataFrame())
                for idx_type in idx_types
            ]
            source_board_frames = [
                frame for frame in source_board_frames if not frame.empty
            ]
            if source_board_frames:
                source_all_boards = pd.concat(
                    source_board_frames, ignore_index=True, sort=False
                )
            else:
                source_all_boards = pd.DataFrame(columns=BOARD_OUTPUT_COLUMNS)
            source_all_boards = source_all_boards.drop_duplicates(
                subset=["board_ts_code", "idx_type"]
            )
            if args.max_boards_per_snapshot > 0:
                source_all_boards = source_all_boards.head(args.max_boards_per_snapshot)

            source_member_parts: list[pd.DataFrame] = []
            for ordinal, (_, board_row) in enumerate(
                source_all_boards.iterrows(), start=1
            ):
                members = fetch_member_snapshot(
                    pro,
                    board_row=board_row,
                    classification_year=source_snapshot.classification_year,
                    snapshot_trade_date=source_snapshot.first_open_trade_date,
                    fetched_at_utc=fetched_at_utc,
                    output_dir=output_dir,
                    timeout_seconds=args.timeout_seconds,
                    retries=args.retries,
                    retry_sleep=args.retry_sleep,
                    resume_existing=resume_existing,
                    manifest_path=checkpoint_path,
                )
                if not members.empty:
                    source_member_parts.append(members)
                print(
                    f"source_year={source_year} "
                    f"member {ordinal}/{len(source_all_boards)} "
                    f"{board_row.get('board_ts_code', '')} "
                    f"rows={len(members)}",
                    flush=True,
                )
                if args.rate_sleep > 0:
                    time.sleep(args.rate_sleep)

            if source_member_parts:
                source_members = pd.concat(
                    source_member_parts, ignore_index=True, sort=False
                )
            else:
                source_members = pd.DataFrame(columns=MEMBER_OUTPUT_COLUMNS)
            source_members_cache[source_member_key] = source_members

        target_members = remap_snapshot_df(
            source_members_cache[source_member_key],
            output_columns=MEMBER_OUTPUT_COLUMNS,
            classification_year=classification_year,
            classification_first_open_trade_date=target_snapshot.first_open_trade_date,
            source_snapshot_year=source_year,
            source_snapshot_trade_date=source_snapshot.first_open_trade_date,
            policy=policy,
        )
        target_member_path = annual_member_path(
            output_dir, classification_year, target_snapshot.first_open_trade_date
        )
        write_dataframe(target_member_path, target_members)
        append_manifest_row(
            checkpoint_path,
            manifest_row(
                classification_year=classification_year,
                snapshot_trade_date=source_snapshot.first_open_trade_date,
                classification_first_open_trade_date=target_snapshot.first_open_trade_date,
                source_snapshot_year=source_year,
                source_snapshot_trade_date=source_snapshot.first_open_trade_date,
                snapshot_policy=policy,
                dataset_id="dc_member_classification_contract",
                api="dc_member",
                idx_type=",".join(idx_types),
                board_ts_code="",
                board_name="",
                output_path=str(target_member_path),
                status="mapped_from_source_snapshot",
                rows=len(target_members),
                cols=len(target_members.columns),
                elapsed_seconds=0.0,
                attempts=0,
                error_type="",
                error_message="",
            ),
        )
        if not target_members.empty:
            member_parts.append(target_members)

    write_combined_outputs(output_dir, board_parts, member_parts)
    write_summary(output_dir, checkpoint_path)

    manifest = pd.read_csv(checkpoint_path, dtype=str, keep_default_na=False)
    status_counts = manifest["status"].value_counts(dropna=False).to_dict()
    print(f"output_dir={output_dir}")
    print(f"manifest={output_dir / 'metadata' / 'call_manifest.csv'}")
    print(f"status_counts={status_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
