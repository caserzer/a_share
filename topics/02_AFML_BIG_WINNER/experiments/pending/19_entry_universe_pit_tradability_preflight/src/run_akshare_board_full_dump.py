#!/usr/bin/env python3
"""Dump full AkShare Eastmoney/THS industry and concept board datasets.

This script writes complete CSVs for the AkShare board endpoints that are
available in the local package. It deliberately distinguishes board-index
history from historical stock membership; board-index OHLCV is not PIT
membership evidence.

Recommended run:

    timeout 7200s env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy -u NO_PROXY -u no_proxy \
      python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_akshare_board_full_dump.py
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


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    provider: str
    board_type: str
    role: str
    api: str
    symbol_column: str
    code_column: str
    output_subdir: str
    kwargs_template: dict[str, Any]
    timeout_seconds: int


class CallTimeoutError(TimeoutError):
    pass


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


def unset_proxy_env() -> tuple[list[str], list[str]]:
    removed = []
    for key in PROXY_ENV_KEYS:
        if key in os.environ:
            removed.append(key)
            os.environ.pop(key, None)
    remaining = sorted(key for key in os.environ if "proxy" in key.lower())
    return sorted(removed), remaining


def default_end_date() -> str:
    return date.today().strftime("%Y%m%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/akshare_board_full_dump",
        help="Output directory for full board dump.",
    )
    parser.add_argument("--start-date", default="19900101", help="History start date, YYYYMMDD.")
    parser.add_argument("--end-date", default=default_end_date(), help="History end date, YYYYMMDD.")
    parser.add_argument("--retries", type=int, default=2, help="Retries after the first failed call.")
    parser.add_argument("--retry-sleep", type=float, default=1.5, help="Seconds between retries.")
    parser.add_argument("--rate-sleep", type=float, default=0.5, help="Seconds between successful calls.")
    parser.add_argument(
        "--skip-provider",
        action="append",
        choices=("eastmoney", "ths"),
        default=[],
        help="Provider to skip; repeatable.",
    )
    parser.add_argument("--max-boards-per-set", type=int, default=0, help="Debug limit per provider/board_type; 0 means all.")
    parser.add_argument("--clean", action="store_true", help="Remove output dir before running.")
    parser.add_argument("--no-resume-existing", action="store_true", help="Refetch even when a by-board CSV already exists.")
    parser.add_argument("--no-history", action="store_true", help="Skip per-board historical board-index OHLCV.")
    parser.add_argument("--no-current", action="store_true", help="Skip per-board current membership/quote/info calls.")
    return parser.parse_args()


def clean_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def board_file_stem(provider: str, board_type: str, board_code: str, board_name: str, ordinal: int) -> str:
    code = clean_value(board_code)
    if code:
        token = "".join(ch for ch in code if ch.isalnum() or ch in ("_", "-"))
    else:
        token = f"{ordinal:04d}"
    if not token:
        token = f"{ordinal:04d}"
    return f"{provider}_{board_type}_{token}"


def call_dataframe(
    ak: Any,
    api: str,
    kwargs: dict[str, Any],
    timeout_seconds: int,
    retries: int,
    retry_sleep: float,
) -> tuple[str, pd.DataFrame | None, str, str, float, int]:
    func = getattr(ak, api, None)
    if func is None:
        return "api_missing", None, "AttributeError", f"akshare.{api} is not available", 0.0, 0

    last_error_type = ""
    last_error_message = ""
    total_elapsed = 0.0
    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            buffer = io.StringIO()
            with time_limit(timeout_seconds), contextlib.redirect_stderr(buffer):
                result = func(**kwargs)
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            if not isinstance(result, pd.DataFrame):
                return (
                    "non_dataframe",
                    None,
                    type(result).__name__,
                    "AkShare call returned a non-DataFrame object",
                    total_elapsed,
                    attempt + 1,
                )
            status = "ok" if not result.empty else "ok_empty"
            return status, result, "", "", total_elapsed, attempt + 1
        except Exception as exc:  # noqa: BLE001 - endpoint dump must keep going.
            elapsed = time.perf_counter() - started
            total_elapsed += elapsed
            last_error_type = type(exc).__name__
            last_error_message = str(exc).replace("\n", " ")[:1000]
            if attempt < retries:
                time.sleep(retry_sleep)

    status = "timeout" if last_error_type == "CallTimeoutError" else "error"
    return status, None, last_error_type, last_error_message, total_elapsed, retries + 1


def add_metadata(
    df: pd.DataFrame,
    *,
    provider: str,
    board_type: str,
    role: str,
    api: str,
    board_name: str = "",
    board_code: str = "",
    snapshot_date: str,
    fetched_at_utc: str,
    start_date: str = "",
    end_date: str = "",
) -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "source_api", api)
    out.insert(0, "role", role)
    out.insert(0, "board_code", board_code)
    out.insert(0, "board_name", board_name)
    out.insert(0, "board_type", board_type)
    out.insert(0, "provider", provider)
    out.insert(0, "snapshot_date", snapshot_date)
    out.insert(0, "fetched_at_utc", fetched_at_utc)
    if start_date or end_date:
        out.insert(8, "history_start_requested", start_date)
        out.insert(9, "history_end_requested", end_date)
    return out


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


def date_bounds(df: pd.DataFrame) -> tuple[str, str]:
    for column in ("日期", "date", "Date", "交易日期", "时间"):
        if column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce").dropna()
            if not parsed.empty:
                return parsed.min().strftime("%Y-%m-%d"), parsed.max().strftime("%Y-%m-%d")
    return "", ""


def manifest_row(
    *,
    dataset_id: str,
    provider: str,
    board_type: str,
    role: str,
    api: str,
    board_name: str,
    board_code: str,
    output_path: str,
    status: str,
    rows: int | str,
    cols: int | str,
    first_date: str,
    last_date: str,
    elapsed_seconds: float,
    attempts: int,
    error_type: str,
    error_message: str,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "provider": provider,
        "board_type": board_type,
        "role": role,
        "api": api,
        "board_name": board_name,
        "board_code": board_code,
        "output_path": output_path,
        "status": status,
        "rows": rows,
        "cols": cols,
        "first_date": first_date,
        "last_date": last_date,
        "elapsed_seconds": f"{elapsed_seconds:.3f}",
        "attempts": attempts,
        "error_type": error_type,
        "error_message": error_message,
    }


def load_board_list(
    ak: Any,
    *,
    provider: str,
    board_type: str,
    api: str,
    output_dir: Path,
    snapshot_date: str,
    fetched_at_utc: str,
    retries: int,
    retry_sleep: float,
    resume_existing: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = output_dir / "lists" / f"{provider}_{board_type}_board_list.csv"
    status, df, error_type, error_message, elapsed, attempts = call_dataframe(
        ak=ak,
        api=api,
        kwargs={},
        timeout_seconds=90,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    rows = ""
    cols = ""
    first_date = ""
    last_date = ""
    if df is not None:
        df = add_metadata(
            df,
            provider=provider,
            board_type=board_type,
            role="board_list",
            api=api,
            snapshot_date=snapshot_date,
            fetched_at_utc=fetched_at_utc,
        )
        write_dataframe(path, df)
        rows = len(df)
        cols = len(df.columns)
        first_date, last_date = date_bounds(df)
    elif resume_existing and path.exists():
        df = pd.read_csv(path)
        status = "ok_cached"
        error_type = ""
        error_message = ""
        rows = len(df)
        cols = len(df.columns)
        first_date, last_date = date_bounds(df)
    return df if df is not None else pd.DataFrame(), manifest_row(
        dataset_id=f"{provider}_{board_type}_board_list",
        provider=provider,
        board_type=board_type,
        role="board_list",
        api=api,
        board_name="",
        board_code="",
        output_path=str(path) if df is not None else "",
        status=status,
        rows=rows,
        cols=cols,
        first_date=first_date,
        last_date=last_date,
        elapsed_seconds=elapsed,
        attempts=attempts,
        error_type=error_type,
        error_message=error_message,
    )


def board_records(board_df: pd.DataFrame, provider: str) -> list[dict[str, str]]:
    if board_df.empty:
        return []
    if provider == "eastmoney":
        name_col = "板块名称"
        code_col = "板块代码"
    else:
        name_col = "name"
        code_col = "code"
    records = []
    for idx, row in board_df.reset_index(drop=True).iterrows():
        records.append(
            {
                "ordinal": str(idx + 1),
                "board_name": clean_value(row.get(name_col, "")),
                "board_code": clean_value(row.get(code_col, "")),
            }
        )
    return records


def dataset_specs(start_date: str, end_date: str, include_current: bool, include_history: bool) -> list[DatasetSpec]:
    specs: list[DatasetSpec] = []
    if include_current:
        specs.extend(
            [
                DatasetSpec(
                    "eastmoney_industry_current_membership",
                    "eastmoney",
                    "industry",
                    "current_membership",
                    "stock_board_industry_cons_em",
                    "symbol",
                    "board_code",
                    "eastmoney/industry/current_membership",
                    {"symbol": "{board_name}"},
                    60,
                ),
                DatasetSpec(
                    "eastmoney_industry_current_quote",
                    "eastmoney",
                    "industry",
                    "current_quote",
                    "stock_board_industry_spot_em",
                    "symbol",
                    "board_code",
                    "eastmoney/industry/current_quote",
                    {"symbol": "{board_name}"},
                    45,
                ),
                DatasetSpec(
                    "eastmoney_concept_current_membership",
                    "eastmoney",
                    "concept",
                    "current_membership",
                    "stock_board_concept_cons_em",
                    "symbol",
                    "board_code",
                    "eastmoney/concept/current_membership",
                    {"symbol": "{board_name}"},
                    75,
                ),
                DatasetSpec(
                    "eastmoney_concept_current_quote",
                    "eastmoney",
                    "concept",
                    "current_quote",
                    "stock_board_concept_spot_em",
                    "symbol",
                    "board_code",
                    "eastmoney/concept/current_quote",
                    {"symbol": "{board_name}"},
                    45,
                ),
                DatasetSpec(
                    "ths_industry_current_info",
                    "ths",
                    "industry",
                    "current_info",
                    "stock_board_industry_info_ths",
                    "symbol",
                    "board_code",
                    "ths/industry/current_info",
                    {"symbol": "{board_name}"},
                    45,
                ),
                DatasetSpec(
                    "ths_concept_current_info",
                    "ths",
                    "concept",
                    "current_info",
                    "stock_board_concept_info_ths",
                    "symbol",
                    "board_code",
                    "ths/concept/current_info",
                    {"symbol": "{board_name}"},
                    45,
                ),
            ]
        )
    if include_history:
        specs.extend(
            [
                DatasetSpec(
                    "eastmoney_industry_historical_index_ohlcv",
                    "eastmoney",
                    "industry",
                    "historical_board_index_ohlcv",
                    "stock_board_industry_hist_em",
                    "symbol",
                    "board_code",
                    "eastmoney/industry/historical_index_ohlcv",
                    {"symbol": "{board_name}", "start_date": start_date, "end_date": end_date, "period": "日k"},
                    75,
                ),
                DatasetSpec(
                    "eastmoney_concept_historical_index_ohlcv",
                    "eastmoney",
                    "concept",
                    "historical_board_index_ohlcv",
                    "stock_board_concept_hist_em",
                    "symbol",
                    "board_code",
                    "eastmoney/concept/historical_index_ohlcv",
                    {"symbol": "{board_name}", "period": "daily", "start_date": start_date, "end_date": end_date},
                    75,
                ),
                DatasetSpec(
                    "ths_industry_historical_index_ohlcv",
                    "ths",
                    "industry",
                    "historical_board_index_ohlcv",
                    "stock_board_industry_index_ths",
                    "symbol",
                    "board_code",
                    "ths/industry/historical_index_ohlcv",
                    {"symbol": "{board_name}", "start_date": start_date, "end_date": end_date},
                    75,
                ),
                DatasetSpec(
                    "ths_concept_historical_index_ohlcv",
                    "ths",
                    "concept",
                    "historical_board_index_ohlcv",
                    "stock_board_concept_index_ths",
                    "symbol",
                    "board_code",
                    "ths/concept/historical_index_ohlcv",
                    {"symbol": "{board_name}", "start_date": start_date, "end_date": end_date},
                    75,
                ),
            ]
        )
    return specs


def build_kwargs(template: dict[str, Any], board_name: str, board_code: str) -> dict[str, Any]:
    kwargs = {}
    for key, value in template.items():
        if isinstance(value, str):
            kwargs[key] = value.format(board_name=board_name, board_code=board_code)
        else:
            kwargs[key] = value
    return kwargs


def fetch_dataset(
    ak: Any,
    spec: DatasetSpec,
    records: list[dict[str, str]],
    *,
    output_dir: Path,
    snapshot_date: str,
    fetched_at_utc: str,
    start_date: str,
    end_date: str,
    retries: int,
    retry_sleep: float,
    rate_sleep: float,
    resume_existing: bool,
    checkpoint_path: Path,
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    parts: list[pd.DataFrame] = []
    board_dir = output_dir / "by_board" / spec.output_subdir
    board_dir.mkdir(parents=True, exist_ok=True)
    combined_path = output_dir / "combined" / f"{spec.dataset_id}.csv"

    for record in records:
        ordinal = int(record["ordinal"])
        board_name = record["board_name"]
        board_code = record["board_code"]
        stem = board_file_stem(spec.provider, spec.board_type, board_code, board_name, ordinal)
        board_path = board_dir / f"{stem}.csv"
        kwargs = build_kwargs(spec.kwargs_template, board_name, board_code)

        rows: int | str = ""
        cols: int | str = ""
        first_date = ""
        last_date = ""
        output_path = ""
        if resume_existing and board_path.exists():
            with_meta = pd.read_csv(board_path)
            parts.append(with_meta)
            first_date, last_date = date_bounds(with_meta)
            rows = len(with_meta)
            cols = len(with_meta.columns)
            output_path = str(board_path)
            row = manifest_row(
                dataset_id=spec.dataset_id,
                provider=spec.provider,
                board_type=spec.board_type,
                role=spec.role,
                api=spec.api,
                board_name=board_name,
                board_code=board_code,
                output_path=output_path,
                status="ok_cached",
                rows=rows,
                cols=cols,
                first_date=first_date,
                last_date=last_date,
                elapsed_seconds=0.0,
                attempts=0,
                error_type="",
                error_message="",
            )
        else:
            status, df, error_type, error_message, elapsed, attempts = call_dataframe(
                ak=ak,
                api=spec.api,
                kwargs=kwargs,
                timeout_seconds=spec.timeout_seconds,
                retries=retries,
                retry_sleep=retry_sleep,
            )

            if df is not None:
                first_date, last_date = date_bounds(df)
                with_meta = add_metadata(
                    df,
                    provider=spec.provider,
                    board_type=spec.board_type,
                    role=spec.role,
                    api=spec.api,
                    board_name=board_name,
                    board_code=board_code,
                    snapshot_date=snapshot_date,
                    fetched_at_utc=fetched_at_utc,
                    start_date=start_date if spec.role == "historical_board_index_ohlcv" else "",
                    end_date=end_date if spec.role == "historical_board_index_ohlcv" else "",
                )
                write_dataframe(board_path, with_meta)
                parts.append(with_meta)
                rows = len(with_meta)
                cols = len(with_meta.columns)
                output_path = str(board_path)

            row = manifest_row(
                dataset_id=spec.dataset_id,
                provider=spec.provider,
                board_type=spec.board_type,
                role=spec.role,
                api=spec.api,
                board_name=board_name,
                board_code=board_code,
                output_path=output_path,
                status=status,
                rows=rows,
                cols=cols,
                first_date=first_date,
                last_date=last_date,
                elapsed_seconds=elapsed,
                attempts=attempts,
                error_type=error_type,
                error_message=error_message,
            )
        manifest.append(row)
        append_manifest_row(checkpoint_path, row)

        print(
            f"{spec.dataset_id} {ordinal}/{len(records)} {board_name} "
            f"status={row['status']} rows={rows}",
            flush=True,
        )
        if rate_sleep > 0:
            time.sleep(rate_sleep)

    if parts:
        write_dataframe(combined_path, pd.concat(parts, ignore_index=True, sort=False))
    return manifest


def write_single_endpoint(
    ak: Any,
    *,
    output_dir: Path,
    dataset_id: str,
    provider: str,
    board_type: str,
    role: str,
    api: str,
    snapshot_date: str,
    fetched_at_utc: str,
    retries: int,
    retry_sleep: float,
    resume_existing: bool,
) -> dict[str, Any]:
    path = output_dir / "combined" / f"{dataset_id}.csv"
    status, df, error_type, error_message, elapsed, attempts = call_dataframe(
        ak=ak,
        api=api,
        kwargs={},
        timeout_seconds=120,
        retries=retries,
        retry_sleep=retry_sleep,
    )
    rows: int | str = ""
    cols: int | str = ""
    first_date = ""
    last_date = ""
    output_path = ""
    if df is not None:
        first_date, last_date = date_bounds(df)
        with_meta = add_metadata(
            df,
            provider=provider,
            board_type=board_type,
            role=role,
            api=api,
            snapshot_date=snapshot_date,
            fetched_at_utc=fetched_at_utc,
        )
        write_dataframe(path, with_meta)
        rows = len(with_meta)
        cols = len(with_meta.columns)
        output_path = str(path)
    elif resume_existing and path.exists():
        with_meta = pd.read_csv(path)
        status = "ok_cached"
        error_type = ""
        error_message = ""
        first_date, last_date = date_bounds(with_meta)
        rows = len(with_meta)
        cols = len(with_meta.columns)
        output_path = str(path)
    return manifest_row(
        dataset_id=dataset_id,
        provider=provider,
        board_type=board_type,
        role=role,
        api=api,
        board_name="",
        board_code="",
        output_path=output_path,
        status=status,
        rows=rows,
        cols=cols,
        first_date=first_date,
        last_date=last_date,
        elapsed_seconds=elapsed,
        attempts=attempts,
        error_type=error_type,
        error_message=error_message,
    )


def write_unsupported(output_dir: Path) -> pd.DataFrame:
    rows = [
        {
            "provider": "ths",
            "board_type": "industry",
            "role": "current_membership",
            "api": "stock_board_industry_cons_ths",
            "status": "api_missing",
            "interpretation": "AkShare 1.18.10 does not expose THS industry constituent endpoint.",
        },
        {
            "provider": "ths",
            "board_type": "industry",
            "role": "historical_membership",
            "api": "stock_board_industry_hist_ths",
            "status": "api_missing",
            "interpretation": "AkShare 1.18.10 does not expose THS industry historical constituent endpoint.",
        },
        {
            "provider": "ths",
            "board_type": "concept",
            "role": "current_membership",
            "api": "stock_board_concept_cons_ths",
            "status": "api_missing",
            "interpretation": "AkShare 1.18.10 does not expose THS concept constituent endpoint.",
        },
        {
            "provider": "ths",
            "board_type": "concept",
            "role": "historical_membership",
            "api": "stock_board_concept_hist_ths",
            "status": "api_missing",
            "interpretation": "AkShare 1.18.10 does not expose THS concept historical constituent endpoint.",
        },
    ]
    df = pd.DataFrame(rows)
    write_dataframe(output_dir / "metadata" / "unsupported_endpoints.csv", df)
    return df


def write_summary(output_dir: Path, manifest: pd.DataFrame) -> None:
    summary = (
        manifest.groupby(["dataset_id", "provider", "board_type", "role", "status"], dropna=False)
        .agg(calls=("status", "size"), rows=("rows", lambda values: pd.to_numeric(values, errors="coerce").sum()))
        .reset_index()
    )
    write_dataframe(output_dir / "metadata" / "dataset_summary.csv", summary)

    lines = [
        "# AkShare Board Full Dump",
        "",
        "## Files",
        "",
        "- `combined/`: full concatenated CSVs for each available dataset.",
        "- `by_board/`: per-board CSVs used to build combined datasets.",
        "- `lists/`: full board lists from each provider.",
        "- `metadata/call_manifest.csv`: every attempted endpoint call and status.",
        "- `metadata/dataset_summary.csv`: grouped status and row totals.",
        "- `metadata/unsupported_endpoints.csv`: AkShare endpoints absent in this local version.",
        "",
        "## PIT Boundary",
        "",
        "- Eastmoney current constituent files are current snapshots only, with no effective dates.",
        "- THS constituent endpoints are not available in AkShare 1.18.10.",
        "- Historical board-index OHLCV files are board/concept index histories, not historical stock membership.",
        "- These files can support diagnostics and snapshot archiving, but cannot alone prove PIT industry/concept membership.",
    ]
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    removed_proxy_keys, remaining_proxy_keys = unset_proxy_env()

    try:
        import akshare as ak
    except Exception as exc:  # noqa: BLE001 - environment probe.
        print(f"failed to import akshare: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata").mkdir(parents=True, exist_ok=True)

    snapshot_date = date.today().isoformat()
    fetched_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    config = {
        "generated_at_utc": fetched_at_utc,
        "snapshot_date": snapshot_date,
        "akshare_version": getattr(ak, "__version__", "unknown"),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "removed_proxy_env_keys": removed_proxy_keys,
        "remaining_proxy_env_keys_after_cleanup": remaining_proxy_keys,
        "retries": args.retries,
        "retry_sleep": args.retry_sleep,
        "rate_sleep": args.rate_sleep,
        "skip_provider": sorted(set(args.skip_provider)),
        "max_boards_per_set": args.max_boards_per_set,
        "resume_existing": not args.no_resume_existing,
        "no_history": args.no_history,
        "no_current": args.no_current,
    }
    (output_dir / "metadata" / "run_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checkpoint_path = output_dir / "metadata" / "call_manifest_checkpoint.csv"
    checkpoint_path.unlink(missing_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    board_lists: dict[tuple[str, str], list[dict[str, str]]] = {}
    enabled_providers = {"eastmoney", "ths"} - set(args.skip_provider)
    list_specs = [
        ("eastmoney", "industry", "stock_board_industry_name_em"),
        ("eastmoney", "concept", "stock_board_concept_name_em"),
        ("ths", "industry", "stock_board_industry_name_ths"),
        ("ths", "concept", "stock_board_concept_name_ths"),
    ]

    for provider, board_type, api in list_specs:
        if provider not in enabled_providers:
            print(f"skipped {provider}/{board_type} board list by --skip-provider", flush=True)
            continue
        df, row = load_board_list(
            ak,
            provider=provider,
            board_type=board_type,
            api=api,
            output_dir=output_dir,
            snapshot_date=snapshot_date,
            fetched_at_utc=fetched_at_utc,
            retries=args.retries,
            retry_sleep=args.retry_sleep,
            resume_existing=not args.no_resume_existing,
        )
        manifest_rows.append(row)
        append_manifest_row(checkpoint_path, row)
        records = board_records(df, provider)
        if args.max_boards_per_set > 0:
            records = records[: args.max_boards_per_set]
        board_lists[(provider, board_type)] = records
        print(f"loaded {provider}/{board_type} boards={len(records)} status={row['status']}", flush=True)

    for provider, board_type, role, api, dataset_id in [
        ("ths", "industry", "current_overview", "stock_board_industry_summary_ths", "ths_industry_current_overview"),
        ("ths", "concept", "concept_event_table", "stock_board_concept_summary_ths", "ths_concept_event_table"),
    ]:
        if provider not in enabled_providers:
            print(f"skipped {dataset_id} by --skip-provider", flush=True)
            continue
        row = write_single_endpoint(
            ak,
            output_dir=output_dir,
            dataset_id=dataset_id,
            provider=provider,
            board_type=board_type,
            role=role,
            api=api,
            snapshot_date=snapshot_date,
            fetched_at_utc=fetched_at_utc,
            retries=args.retries,
            retry_sleep=args.retry_sleep,
            resume_existing=not args.no_resume_existing,
        )
        manifest_rows.append(row)
        append_manifest_row(checkpoint_path, row)
        print(f"loaded {dataset_id} status={row['status']} rows={row['rows']}", flush=True)

    for spec in dataset_specs(args.start_date, args.end_date, not args.no_current, not args.no_history):
        if spec.provider not in enabled_providers:
            print(f"skipped {spec.dataset_id} by --skip-provider", flush=True)
            continue
        records = board_lists.get((spec.provider, spec.board_type), [])
        if not records:
            manifest_rows.append(
                manifest_row(
                    dataset_id=spec.dataset_id,
                    provider=spec.provider,
                    board_type=spec.board_type,
                    role=spec.role,
                    api=spec.api,
                    board_name="",
                    board_code="",
                    output_path="",
                    status="skipped_no_board_list",
                    rows="",
                    cols="",
                    first_date="",
                    last_date="",
                    elapsed_seconds=0.0,
                    attempts=0,
                    error_type="",
                    error_message="board list unavailable",
                )
            )
            continue
        manifest_rows.extend(
            fetch_dataset(
                ak,
                spec,
                records,
                output_dir=output_dir,
                snapshot_date=snapshot_date,
                fetched_at_utc=fetched_at_utc,
                start_date=args.start_date,
                end_date=args.end_date,
                retries=args.retries,
                retry_sleep=args.retry_sleep,
                rate_sleep=args.rate_sleep,
                resume_existing=not args.no_resume_existing,
                checkpoint_path=checkpoint_path,
            )
        )

    unsupported = write_unsupported(output_dir)
    for _, row in unsupported.iterrows():
        manifest_rows.append(
            row := manifest_row(
                dataset_id=f"{row['provider']}_{row['board_type']}_{row['role']}",
                provider=str(row["provider"]),
                board_type=str(row["board_type"]),
                role=str(row["role"]),
                api=str(row["api"]),
                board_name="",
                board_code="",
                output_path=str(output_dir / "metadata" / "unsupported_endpoints.csv"),
                status=str(row["status"]),
                rows="",
                cols="",
                first_date="",
                last_date="",
                elapsed_seconds=0.0,
                attempts=0,
                error_type="AttributeError",
                error_message=str(row["interpretation"]),
            )
        )
        append_manifest_row(checkpoint_path, row)

    manifest = pd.DataFrame(manifest_rows)
    write_dataframe(output_dir / "metadata" / "call_manifest.csv", manifest)
    write_summary(output_dir, manifest)

    status_counts = manifest["status"].value_counts(dropna=False).to_dict()
    print(f"output_dir={output_dir}")
    print(f"manifest={output_dir / 'metadata' / 'call_manifest.csv'}")
    print(f"status_counts={status_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
