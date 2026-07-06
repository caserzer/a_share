#!/usr/bin/env python3
"""Smoke-test AkShare board/theme endpoints for EP19 source-contract preflight.

Run with proxy variables unset, for example:

    timeout 360s env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
      -u ALL_PROXY -u all_proxy \
      python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_akshare_board_availability_smoke.py

The test separates current snapshots from historical board-index OHLCV. Historical
board-index data is not historical stock membership and must not be used as a
PIT industry/concept membership proof.
"""

from __future__ import annotations

import contextlib
import io
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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
class CheckSpec:
    check_id: str
    provider: str
    board_type: str
    role: str
    api: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None
    sample_symbol: str = ""
    history_interpretation: str = ""
    pit_membership_verdict: str = "not_proven"
    timeout_seconds: int = 45


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


def first_date_bounds(df: pd.DataFrame) -> tuple[str, str]:
    date_columns = ["日期", "date", "Date", "交易日期", "时间"]
    for column in date_columns:
        if column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce")
            parsed = parsed.dropna()
            if not parsed.empty:
                return (
                    parsed.min().strftime("%Y-%m-%d"),
                    parsed.max().strftime("%Y-%m-%d"),
                )
    return "", ""


def compact_columns(df: pd.DataFrame) -> str:
    columns = [str(column) for column in df.columns]
    if len(columns) <= 16:
        return ";".join(columns)
    return ";".join(columns[:16]) + f";...(+{len(columns) - 16})"


def run_check(ak: Any, spec: CheckSpec, sample_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    row: dict[str, Any] = {
        "check_id": spec.check_id,
        "provider": spec.provider,
        "board_type": spec.board_type,
        "role": spec.role,
        "api": spec.api,
        "sample_symbol": spec.sample_symbol,
        "status": "",
        "rows": "",
        "cols": "",
        "columns": "",
        "first_date": "",
        "last_date": "",
        "sample_path": "",
        "elapsed_seconds": "",
        "error_type": "",
        "error_message": "",
        "history_interpretation": spec.history_interpretation,
        "pit_membership_verdict": spec.pit_membership_verdict,
    }

    func = getattr(ak, spec.api, None)
    if func is None:
        row["status"] = "api_missing"
        row["elapsed_seconds"] = "0.000"
        row["error_type"] = "AttributeError"
        row["error_message"] = f"akshare.{spec.api} is not available"
        return row

    try:
        stderr_buffer = io.StringIO()
        with time_limit(spec.timeout_seconds), contextlib.redirect_stderr(stderr_buffer):
            result = func(*spec.args, **(spec.kwargs or {}))
        elapsed = time.perf_counter() - started
        row["elapsed_seconds"] = f"{elapsed:.3f}"
        if not isinstance(result, pd.DataFrame):
            row["status"] = "non_dataframe"
            row["error_type"] = type(result).__name__
            row["error_message"] = "AkShare call returned a non-DataFrame object"
            return row

        row["rows"] = str(len(result))
        row["cols"] = str(len(result.columns))
        row["columns"] = compact_columns(result)
        row["first_date"], row["last_date"] = first_date_bounds(result)
        row["status"] = "ok" if not result.empty else "ok_empty"

        sample_path = sample_dir / f"{spec.check_id}.csv"
        result.head(20).to_csv(sample_path, index=False, encoding="utf-8")
        row["sample_path"] = str(sample_path)
        return row
    except CallTimeoutError as exc:
        row["status"] = "timeout"
        row["elapsed_seconds"] = f"{time.perf_counter() - started:.3f}"
        row["error_type"] = type(exc).__name__
        row["error_message"] = str(exc)
        return row
    except Exception as exc:  # noqa: BLE001 - this is an endpoint smoke-test.
        row["status"] = "error"
        row["elapsed_seconds"] = f"{time.perf_counter() - started:.3f}"
        row["error_type"] = type(exc).__name__
        row["error_message"] = str(exc).replace("\n", " ")[:800]
        return row


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    def clean(value: Any) -> str:
        text = str(value)
        return text.replace("|", "\\|").replace("\n", " ")

    output = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(clean(row.get(column, "")) for column in columns) + " |")
    return output


def status_by_id(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {str(row["check_id"]): str(row["status"]) for row in rows}


def ok(status: str) -> bool:
    return status == "ok"


def source_readouts(rows: list[dict[str, Any]]) -> list[str]:
    status = status_by_id(rows)

    lines = [
        "- Eastmoney industry: "
        f"name={status.get('em_industry_name', 'not_run')}, "
        f"current_membership={status.get('em_industry_cons_current', 'not_run')}, "
        f"current_quote={status.get('em_industry_spot_current', 'not_run')}, "
        f"historical_board_index_ohlcv={status.get('em_industry_hist_ohlcv', 'not_run')}.",
        "- Eastmoney concept: "
        f"name={status.get('em_concept_name', 'not_run')}, "
        f"current_membership={status.get('em_concept_cons_current', 'not_run')}, "
        f"current_quote={status.get('em_concept_spot_current', 'not_run')}, "
        f"historical_board_index_ohlcv={status.get('em_concept_hist_ohlcv', 'not_run')}.",
        "- THS industry: "
        f"name={status.get('ths_industry_name', 'not_run')}, "
        f"current_membership_api={status.get('ths_industry_cons_missing', 'not_run')}, "
        f"current_info={status.get('ths_industry_info_current', 'not_run')}, "
        f"current_overview={status.get('ths_industry_summary_current', 'not_run')}, "
        f"historical_board_index_ohlcv={status.get('ths_industry_index_ohlcv', 'not_run')}, "
        f"historical_membership_api={status.get('ths_industry_hist_membership_missing', 'not_run')}.",
        "- THS concept: "
        f"name={status.get('ths_concept_name', 'not_run')}, "
        f"current_membership_api={status.get('ths_concept_cons_missing', 'not_run')}, "
        f"current_info={status.get('ths_concept_info_current', 'not_run')}, "
        f"concept_event_table={status.get('ths_concept_summary_current', 'not_run')}, "
        f"historical_board_index_ohlcv={status.get('ths_concept_index_ohlcv', 'not_run')}, "
        f"historical_membership_api={status.get('ths_concept_hist_membership_missing', 'not_run')}.",
        "- Historical PIT stock membership: not proven by these AkShare board endpoints. "
        "Current constituents/snapshots require daily archiving before they can become PIT features.",
    ]
    return lines


def write_report(
    rows: list[dict[str, Any]],
    output_dir: Path,
    summary_csv: Path,
    removed_proxy_keys: list[str],
    remaining_proxy_keys: list[str],
    akshare_version: str,
) -> Path:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_path = output_dir / "akshare_board_availability_report.md"

    columns = [
        "check_id",
        "provider",
        "board_type",
        "role",
        "api",
        "sample_symbol",
        "status",
        "rows",
        "first_date",
        "last_date",
        "error_type",
    ]

    lines = [
        "# AkShare Board Availability Smoke Test",
        "",
        f"- generated_at_utc: `{generated_at}`",
        f"- akshare_version: `{akshare_version}`",
        f"- summary_csv: `{summary_csv}`",
        f"- removed_proxy_env_keys: `{','.join(removed_proxy_keys) if removed_proxy_keys else 'none'}`",
        f"- remaining_proxy_env_keys_after_cleanup: `{','.join(remaining_proxy_keys) if remaining_proxy_keys else 'none'}`",
        "",
        "## Readout",
        "",
        *source_readouts(rows),
        "",
        "## Endpoint Summary",
        "",
        *markdown_table(rows, columns),
        "",
        "## Interpretation Rule",
        "",
        "- `historical_board_index_ohlcv` means the board/concept index price history is available.",
        "- It does not prove historical stock membership in that industry or concept.",
        "- `current_membership` or current board snapshots can only become PIT usable after daily snapshotting with snapshot dates.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def specs() -> list[CheckSpec]:
    return [
        CheckSpec(
            "em_industry_name",
            "eastmoney",
            "industry",
            "current_board_list",
            "stock_board_industry_name_em",
            history_interpretation="current board list only",
        ),
        CheckSpec(
            "em_industry_cons_current",
            "eastmoney",
            "industry",
            "current_membership",
            "stock_board_industry_cons_em",
            kwargs={"symbol": "小金属"},
            sample_symbol="小金属",
            history_interpretation="current constituents only; no effective_date",
        ),
        CheckSpec(
            "em_industry_hist_ohlcv",
            "eastmoney",
            "industry",
            "historical_board_index_ohlcv",
            "stock_board_industry_hist_em",
            kwargs={
                "symbol": "小金属",
                "start_date": "20240101",
                "end_date": "20240701",
                "period": "日k",
            },
            sample_symbol="小金属",
            history_interpretation="historical board index OHLCV, not historical membership",
        ),
        CheckSpec(
            "em_industry_spot_current",
            "eastmoney",
            "industry",
            "current_board_quote",
            "stock_board_industry_spot_em",
            kwargs={"symbol": "小金属"},
            sample_symbol="小金属",
            history_interpretation="current board quote only",
        ),
        CheckSpec(
            "em_concept_name",
            "eastmoney",
            "concept",
            "current_board_list",
            "stock_board_concept_name_em",
            history_interpretation="current board list only",
        ),
        CheckSpec(
            "em_concept_cons_current",
            "eastmoney",
            "concept",
            "current_membership",
            "stock_board_concept_cons_em",
            kwargs={"symbol": "融资融券"},
            sample_symbol="融资融券",
            history_interpretation="current constituents only; no effective_date",
        ),
        CheckSpec(
            "em_concept_hist_ohlcv",
            "eastmoney",
            "concept",
            "historical_board_index_ohlcv",
            "stock_board_concept_hist_em",
            kwargs={
                "symbol": "绿色电力",
                "period": "daily",
                "start_date": "20240101",
                "end_date": "20240701",
            },
            sample_symbol="绿色电力",
            history_interpretation="historical board index OHLCV, not historical membership",
        ),
        CheckSpec(
            "em_concept_spot_current",
            "eastmoney",
            "concept",
            "current_board_quote",
            "stock_board_concept_spot_em",
            kwargs={"symbol": "可燃冰"},
            sample_symbol="可燃冰",
            history_interpretation="current board quote only",
        ),
        CheckSpec(
            "ths_industry_name",
            "ths",
            "industry",
            "current_board_list",
            "stock_board_industry_name_ths",
            history_interpretation="current board list only",
        ),
        CheckSpec(
            "ths_industry_cons_missing",
            "ths",
            "industry",
            "current_membership",
            "stock_board_industry_cons_ths",
            sample_symbol="半导体",
            history_interpretation="expected missing in akshare 1.18.10",
        ),
        CheckSpec(
            "ths_industry_hist_membership_missing",
            "ths",
            "industry",
            "historical_membership",
            "stock_board_industry_hist_ths",
            sample_symbol="半导体",
            history_interpretation="expected missing in akshare 1.18.10",
        ),
        CheckSpec(
            "ths_industry_info_current",
            "ths",
            "industry",
            "current_board_info",
            "stock_board_industry_info_ths",
            kwargs={"symbol": "半导体"},
            sample_symbol="半导体",
            history_interpretation="current board quote/info only",
        ),
        CheckSpec(
            "ths_industry_index_ohlcv",
            "ths",
            "industry",
            "historical_board_index_ohlcv",
            "stock_board_industry_index_ths",
            kwargs={
                "symbol": "半导体",
                "start_date": "20240101",
                "end_date": "20240701",
            },
            sample_symbol="半导体",
            history_interpretation="historical board index OHLCV, not historical membership",
        ),
        CheckSpec(
            "ths_industry_summary_current",
            "ths",
            "industry",
            "current_board_overview",
            "stock_board_industry_summary_ths",
            history_interpretation="current industry overview only",
        ),
        CheckSpec(
            "ths_concept_name",
            "ths",
            "concept",
            "current_board_list",
            "stock_board_concept_name_ths",
            history_interpretation="current board list only",
            timeout_seconds=75,
        ),
        CheckSpec(
            "ths_concept_cons_missing",
            "ths",
            "concept",
            "current_membership",
            "stock_board_concept_cons_ths",
            sample_symbol="阿里巴巴概念",
            history_interpretation="expected missing in akshare 1.18.10",
        ),
        CheckSpec(
            "ths_concept_hist_membership_missing",
            "ths",
            "concept",
            "historical_membership",
            "stock_board_concept_hist_ths",
            sample_symbol="阿里巴巴概念",
            history_interpretation="expected missing in akshare 1.18.10",
        ),
        CheckSpec(
            "ths_concept_info_current",
            "ths",
            "concept",
            "current_board_info",
            "stock_board_concept_info_ths",
            kwargs={"symbol": "阿里巴巴概念"},
            sample_symbol="阿里巴巴概念",
            history_interpretation="current board quote/info only",
        ),
        CheckSpec(
            "ths_concept_index_ohlcv",
            "ths",
            "concept",
            "historical_board_index_ohlcv",
            "stock_board_concept_index_ths",
            kwargs={
                "symbol": "阿里巴巴概念",
                "start_date": "20240101",
                "end_date": "20240701",
            },
            sample_symbol="阿里巴巴概念",
            history_interpretation="historical board index OHLCV, not historical membership",
            timeout_seconds=75,
        ),
        CheckSpec(
            "ths_concept_summary_current",
            "ths",
            "concept",
            "concept_event_table",
            "stock_board_concept_summary_ths",
            history_interpretation="concept event/date table, not stock membership",
            timeout_seconds=75,
        ),
    ]


def main() -> int:
    removed_proxy_keys, remaining_proxy_keys = unset_proxy_env()

    try:
        import akshare as ak
    except Exception as exc:  # noqa: BLE001 - environment probe.
        print(f"failed to import akshare: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    experiment_dir = Path(__file__).resolve().parents[1]
    output_dir = experiment_dir / "outputs" / "akshare_board_availability_smoke"
    sample_dir = output_dir / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for stale_sample in sample_dir.glob("*.csv"):
        stale_sample.unlink()

    rows = [run_check(ak, spec, sample_dir) for spec in specs()]

    summary_csv = output_dir / "akshare_board_availability_summary.csv"
    pd.DataFrame(rows).to_csv(summary_csv, index=False, encoding="utf-8")

    report_path = write_report(
        rows=rows,
        output_dir=output_dir,
        summary_csv=summary_csv,
        removed_proxy_keys=removed_proxy_keys,
        remaining_proxy_keys=remaining_proxy_keys,
        akshare_version=getattr(ak, "__version__", "unknown"),
    )

    print(f"summary_csv={summary_csv}")
    print(f"report={report_path}")
    print("status_counts=" + str(pd.Series([row["status"] for row in rows]).value_counts().to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
