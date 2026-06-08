#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
CODE_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", CODE_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402
from pipeline import (  # noqa: E402
    DataSourceUnsupported,
    akshare_symbol_with_exchange_suffix,
    audit_akshare_sources,
    audit_rows_to_frame,
    board_bucket,
    blocking_audit_issues,
    build_qlib_index_daily,
    build_qlib_daily,
    call_akshare,
    call_akshare_unproxied,
    compress_executable_intervals,
    expand_share_asof,
    fetch_stock_bars,
    has_any_st_name_marker,
    has_st_name_marker,
    instrument_from_code,
    market_cap_threshold_cny,
    next_trade_date_map,
    normalize_index_bars,
    normalize_share_history,
    resolve_trade_calendar,
    shift_membership_to_executable,
    strip_code,
    write_audit_report,
    write_csv,
    write_qlib_csv,
    write_qlib_index_csv,
    write_qlib_instrument_intervals,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the PIT large-cap AkShare/Qlib data layer."
    )
    parser.add_argument(
        "--config",
        default=str(EXPERIMENT_ROOT / "config.yaml"),
        help="Experiment config YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=["validate-config", "preflight", "full", "index-only"],
        default="preflight",
        help="Run static checks, AkShare source audit, full stock+index run, or benchmark-index-only run.",
    )
    parser.add_argument("--sample-symbol", default="600519")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--symbols", nargs="*", help="Optional stock codes or Qlib instruments for a partial run.")
    parser.add_argument("--symbols-file", help="Optional newline-delimited stock codes or Qlib instruments.")
    parser.add_argument("--limit", type=int, help="Optional first-N instrument limit after filtering.")
    parser.add_argument("--max-workers", type=int, default=4, help="Concurrent per-instrument fetch workers.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Optional sleep after each instrument job.")
    parser.add_argument("--force", action="store_true", help="Overwrite cached AkShare CSV files.")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--skip-qlib-dump", action="store_true")
    parser.add_argument("--dump-bin-path", help="Path to microsoft/qlib scripts/dump_bin.py.")
    parser.add_argument("--live-audit", action="store_true", default=None)
    parser.add_argument("--no-live-audit", action="store_false", dest="live_audit")
    parser.add_argument(
        "--allow-unsupported-preflight",
        action="store_true",
        help="Write the audit artifacts and exit 0 even when live audit found unsupported sources.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_yaml(config_path)
    validate_config(config)

    if args.mode == "validate-config":
        print("config validation passed")
        return 0

    live = args.live_audit
    if live is None:
        live = True

    rows = run_preflight(args=args, config=config, config_path=config_path, live=live)
    blocking = blocking_audit_issues(rows, require_evaluated=live)

    if args.mode == "preflight":
        if blocking and not args.allow_unsupported_preflight:
            print(
                "preflight found unsupported PIT data sources: "
                + ", ".join(row.category for row in blocking),
                file=sys.stderr,
            )
            return 2
        return 0

    try:
        enforce_full_run_source_support(rows, require_evaluated=True)
    except DataSourceUnsupported as exc:
        write_final_failure_report(config, rows, exc)
        write_run_manifest(
            config=config,
            config_path=config_path,
            decision=f"blocked_{exc.code}",
            audit_rows=rows,
            extra={"error": str(exc)},
        )
        print(str(exc), file=sys.stderr)
        return 2

    if args.mode == "index-only":
        return run_index_only(args=args, config=config, config_path=config_path, audit_rows=rows)

    return run_full(args=args, config=config, config_path=config_path, audit_rows=rows)


def validate_config(config: dict[str, Any]) -> None:
    required_sections = {"experiment", "date_range", "universe", "akshare", "indices", "fields", "paths", "outputs", "validation"}
    missing_sections = required_sections.difference(config)
    if missing_sections:
        raise ValueError(f"config missing sections: {sorted(missing_sections)}")
    if config["paths"]["project_data_root"] != "data":
        raise ValueError("project_data_root must remain data")
    if config["universe"]["qlib_market_date_key"] != "usable_trade_date":
        raise ValueError("Qlib market must be executable-date keyed")
    if not config["universe"]["exclude_st"] or not config["universe"]["exclude_suspended"]:
        raise ValueError("ST and suspended assets must be excluded")
    qlib_required = set(config["fields"]["qlib_required"])
    expected = {"$open", "$high", "$low", "$close", "$volume", "$money", "$turnover_rate", "$factor"}
    if not expected.issubset(qlib_required):
        raise ValueError(f"Qlib required fields missing: {sorted(expected.difference(qlib_required))}")
    if "$amount" in qlib_required:
        raise ValueError("$amount must not be required unless explicitly written as an alias")
    index_required = set(config["fields"].get("index_qlib_required", []))
    expected_index = {"$open", "$high", "$low", "$close", "$volume", "$money"}
    if not expected_index.issubset(index_required):
        raise ValueError(f"Index Qlib required fields missing: {sorted(expected_index.difference(index_required))}")
    required_index_aliases = {"csi300", "chinext_index", "all_a"}
    index_specs = config["indices"].get("required", [])
    aliases = {item.get("alias") for item in index_specs}
    missing_aliases = required_index_aliases.difference(aliases)
    if missing_aliases:
        raise ValueError(f"Index specs missing aliases: {sorted(missing_aliases)}")
    for spec in index_specs:
        instrument = str(spec.get("qlib_instrument", ""))
        if not (instrument.startswith(("SH", "SZ")) and len(instrument) == 8):
            raise ValueError(f"Invalid index qlib_instrument: {instrument!r}")
    required_path_keys = {
        "index_raw_dir",
        "index_qlib_csv_dir",
        "processed_index_dir",
        "index_qlib_provider_uri",
        "index_daily_csv",
        "index_source_audit_csv",
        "index_qlib_instrument_file",
    }
    missing_path_keys = required_path_keys.difference(config["paths"])
    if missing_path_keys:
        raise ValueError(f"config paths missing index keys: {sorted(missing_path_keys)}")


def run_preflight(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    config_path: Path,
    live: bool,
):
    import akshare as ak

    rows = audit_akshare_sources(
        ak,
        requested_start=config["date_range"]["start_date"],
        requested_end=config["date_range"]["end_date"],
        sample_symbol=args.sample_symbol,
        live=live,
        retry_without_proxy=config["akshare"]["retry_without_proxy_on_proxy_error"],
        timeout=args.timeout,
    )
    output_paths = resolved_output_paths(config)
    source_audit_table = output_paths["tables"]["source_coverage_audit"]
    audit_report = output_paths["reports"]["akshare_api_audit"]
    write_csv(audit_rows_to_frame(rows), source_audit_table)
    write_audit_report(rows, audit_report, require_evaluated=live)
    write_run_manifest(
        config=config,
        config_path=config_path,
        decision="preflight",
        audit_rows=rows,
        extra={"live_audit": live, "sample_symbol": args.sample_symbol},
    )
    return rows


def enforce_full_run_source_support(rows, *, require_evaluated: bool) -> None:
    blocking = blocking_audit_issues(rows, require_evaluated=require_evaluated)
    if not blocking:
        return
    categories = {row.category for row in blocking}
    market_cap_categories = {"historical_total_market_cap_or_total_share_asof"}
    status_categories = {
        "historical_listed_delisted_status",
        "historical_st_status",
        "suspension_or_tradability_status",
        "instrument_metadata_board_classification",
        "trading_calendar",
    }
    index_categories = {"benchmark_index_daily_bars"}
    if categories & market_cap_categories:
        raise DataSourceUnsupported(
            "data_source_market_cap_not_supported",
            "AkShare did not provide historical total market cap or historical total-share-as-of support.",
        )
    if categories & status_categories:
        detail = ", ".join(sorted(categories & status_categories))
        raise DataSourceUnsupported(
            "data_source_status_not_supported",
            f"AkShare did not provide auditable historical status coverage for: {detail}.",
        )
    if categories & index_categories:
        raise DataSourceUnsupported(
            "data_source_benchmark_index_not_supported",
            "AkShare did not provide auditable historical benchmark index daily bars.",
        )
    raise DataSourceUnsupported(
        "data_source_required_category_not_supported",
        "Unsupported source categories: " + ", ".join(sorted(categories)),
    )


def run_full(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    config_path: Path,
    audit_rows,
) -> int:
    import akshare as ak

    data_paths = resolved_data_paths(config)
    output_paths = resolved_output_paths(config)
    ensure_full_directories(data_paths, output_paths)

    calendar = load_trade_calendar(ak, config, data_paths, args)
    metadata = load_instrument_metadata(ak, config, data_paths, args)
    selected = select_instruments(metadata, args)
    if selected.empty:
        raise ValueError("No instruments selected for full run")

    sz_name_changes = load_sz_name_changes(ak, data_paths, args)
    sz_changes_by_code = {
        code: group.sort_values("change_date").reset_index(drop=True)
        for code, group in sz_name_changes.groupby("code")
    }

    print(f"full run selected instruments={len(selected)} sessions={len(calendar)}")
    results = process_instruments(ak, selected, calendar, sz_changes_by_code, data_paths, args, config)
    if not results["candidate_frames"]:
        raise RuntimeError("Full run produced no market-cap candidate rows")

    candidate = pd.concat(results["candidate_frames"], ignore_index=True)
    raw_membership = pd.concat(results["membership_frames"], ignore_index=True)
    raw_membership["usable_trade_date"] = raw_membership["membership_date"].map(
        next_trade_date_map(calendar)
    )
    executable = shift_membership_to_executable(raw_membership, calendar)
    intervals = compress_executable_intervals(executable, calendar)

    write_csv(candidate, data_paths["candidate_before_status_exclusion_csv"])
    write_csv(raw_membership, data_paths["raw_membership_csv"])
    write_csv(executable, data_paths["executable_membership_csv"])
    write_csv(intervals, data_paths["interval_csv"])
    write_qlib_instrument_intervals(intervals, data_paths["qlib_instrument_file"])

    write_summary_outputs(
        candidate=candidate,
        raw_membership=raw_membership,
        executable=executable,
        intervals=intervals,
        results=results,
        data_paths=data_paths,
        output_paths=output_paths,
    )

    qlib_check = pd.DataFrame()
    if not args.skip_qlib_dump:
        dump_qlib_provider(config, data_paths, args)
        qlib_check = check_qlib_provider(config, data_paths, intervals, calendar)
        write_csv(qlib_check, output_paths["tables"]["qlib_provider_check"])
    else:
        qlib_check = pd.DataFrame(
            [
                {
                    "status": "skipped",
                    "reason": "--skip-qlib-dump",
                }
            ]
        )
        write_csv(qlib_check, output_paths["tables"]["qlib_provider_check"])

    index_results = prepare_benchmark_indices(
        ak=ak,
        config=config,
        data_paths=data_paths,
        output_paths=output_paths,
        calendar=calendar,
        args=args,
    )
    if not args.skip_qlib_dump:
        dump_index_qlib_provider(config, data_paths, args)
        index_qlib_check = check_index_qlib_provider(
            config, data_paths, index_results["intervals"], calendar
        )
        write_csv(index_qlib_check, output_paths["tables"]["index_qlib_provider_check"])
    else:
        index_qlib_check = pd.DataFrame(
            [
                {
                    "status": "skipped",
                    "reason": "--skip-qlib-dump",
                }
            ]
        )
        write_csv(index_qlib_check, output_paths["tables"]["index_qlib_provider_check"])

    write_final_success_report(
        config=config,
        calendar=calendar,
        selected=selected,
        candidate=candidate,
        raw_membership=raw_membership,
        executable=executable,
        intervals=intervals,
        results=results,
        qlib_check=qlib_check,
        index_results=index_results,
        index_qlib_check=index_qlib_check,
    )
    write_run_manifest(
        config=config,
        config_path=config_path,
        decision="full_run_complete",
        audit_rows=audit_rows,
        extra={
            "selected_instruments": int(len(selected)),
            "resolved_start_date": calendar[0],
            "resolved_end_date": calendar[-1],
            "resolved_sessions": int(len(calendar)),
            "candidate_rows": int(len(candidate)),
            "raw_membership_rows": int(len(raw_membership)),
            "executable_membership_rows": int(len(executable)),
            "interval_rows": int(len(intervals)),
            "instrument_failures": int(len(results["failures"])),
            "benchmark_index_rows": int(len(index_results["daily"])),
            "benchmark_index_failures": int(len(index_results["failures"])),
            "skip_qlib_dump": bool(args.skip_qlib_dump),
        },
    )
    if results["failures"] and args.fail_fast:
        return 1
    return 0


def run_index_only(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    config_path: Path,
    audit_rows,
) -> int:
    import akshare as ak

    data_paths = resolved_data_paths(config)
    output_paths = resolved_output_paths(config)
    ensure_full_directories(data_paths, output_paths)

    calendar = load_trade_calendar(ak, config, data_paths, args)
    index_results = prepare_benchmark_indices(
        ak=ak,
        config=config,
        data_paths=data_paths,
        output_paths=output_paths,
        calendar=calendar,
        args=args,
    )
    if not args.skip_qlib_dump:
        dump_index_qlib_provider(config, data_paths, args)
        index_qlib_check = check_index_qlib_provider(
            config, data_paths, index_results["intervals"], calendar
        )
        write_csv(index_qlib_check, output_paths["tables"]["index_qlib_provider_check"])
    else:
        index_qlib_check = pd.DataFrame(
            [
                {
                    "status": "skipped",
                    "reason": "--skip-qlib-dump",
                }
            ]
        )
        write_csv(index_qlib_check, output_paths["tables"]["index_qlib_provider_check"])

    write_index_success_report(
        config=config,
        calendar=calendar,
        index_results=index_results,
        index_qlib_check=index_qlib_check,
    )
    write_run_manifest(
        config=config,
        config_path=config_path,
        decision="index_only_complete",
        audit_rows=audit_rows,
        extra={
            "resolved_start_date": calendar[0],
            "resolved_end_date": calendar[-1],
            "resolved_sessions": int(len(calendar)),
            "benchmark_index_rows": int(len(index_results["daily"])),
            "benchmark_index_failures": int(len(index_results["failures"])),
            "skip_qlib_dump": bool(args.skip_qlib_dump),
        },
    )
    return 0


def configured_index_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("indices", {}).get("enabled", False):
        return []
    return list(config["indices"].get("required", []))


def prepare_benchmark_indices(
    *,
    ak: Any,
    config: dict[str, Any],
    data_paths: dict[str, Path],
    output_paths: dict[str, dict[str, Path]],
    calendar: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    specs = configured_index_specs(config)
    if not specs:
        empty = pd.DataFrame()
        return {
            "daily": empty,
            "source_audit": empty,
            "coverage": empty,
            "intervals": empty,
            "failures": [],
        }

    daily_frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    interval_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for spec in specs:
        try:
            result = load_or_fetch_index_daily(
                ak=ak,
                spec=spec,
                config=config,
                data_paths=data_paths,
                calendar=calendar,
                args=args,
            )
            daily = result["daily"]
            qlib_daily = build_qlib_index_daily(daily)
            qlib_csv_path = data_paths["index_qlib_csv_dir"] / f"{spec['qlib_instrument']}.csv"
            write_qlib_index_csv(qlib_daily, qlib_csv_path)

            missing_calendar_dates = sorted(set(calendar).difference(set(daily["date"])))
            interval_rows.append(
                {
                    "instrument": spec["qlib_instrument"],
                    "start_datetime": daily["date"].min(),
                    "end_datetime": daily["date"].max(),
                    "session_count": int(len(daily)),
                }
            )
            audit_row = {
                "index_alias": spec["alias"],
                "name": spec["name"],
                "instrument": spec["qlib_instrument"],
                "status": "ok",
                "source_function": result["source_function"],
                "source_symbol": result["source_symbol"],
                "source_volume_unit": result["source_volume_unit"],
                "source_money_unit": result["source_money_unit"],
                "amount_role": result["amount_role"],
                "raw_cache_path": str(result["raw_cache_path"]),
                "qlib_csv_path": str(qlib_csv_path),
                "first_date": daily["date"].min(),
                "last_date": daily["date"].max(),
                "row_count": int(len(daily)),
                "missing_calendar_dates": int(len(missing_calendar_dates)),
                "missing_calendar_sample": "|".join(missing_calendar_dates[:10]),
                "nullable_volume_rows": int(daily["volume"].isna().sum()),
                "nullable_money_rows": int(daily["money"].isna().sum()),
            }
            audit_rows.append(audit_row)
            coverage_rows.append(audit_row.copy())
            daily_frames.append(daily)
            print(
                f"index {spec['alias']} ok source={result['source_function']} "
                f"rows={len(daily)} range={daily['date'].min()}..{daily['date'].max()}"
            )
        except Exception as exc:
            failure = {
                "index_alias": spec.get("alias"),
                "name": spec.get("name"),
                "instrument": spec.get("qlib_instrument"),
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
            }
            failures.append(failure)
            audit_rows.append(failure)
            coverage_rows.append(failure)
            if args.fail_fast:
                break

    if failures:
        write_csv(pd.DataFrame(audit_rows), data_paths["index_source_audit_csv"])
        write_csv(pd.DataFrame(coverage_rows), output_paths["tables"]["index_coverage_audit"])
        raise RuntimeError("Benchmark index preparation failed: " + "; ".join(row["reason"] for row in failures))
    if not daily_frames:
        raise RuntimeError("Benchmark index preparation produced no rows")

    daily_all = pd.concat(daily_frames, ignore_index=True).sort_values(["instrument", "date"])
    source_audit = pd.DataFrame(audit_rows)
    coverage = pd.DataFrame(coverage_rows)
    intervals = pd.DataFrame(interval_rows).sort_values(["instrument", "start_datetime"])

    write_csv(daily_all, data_paths["index_daily_csv"])
    write_csv(source_audit, data_paths["index_source_audit_csv"])
    write_csv(coverage, output_paths["tables"]["index_coverage_audit"])
    write_qlib_instrument_intervals(intervals, data_paths["index_qlib_instrument_file"])
    return {
        "daily": daily_all.reset_index(drop=True),
        "source_audit": source_audit,
        "coverage": coverage,
        "intervals": intervals,
        "failures": failures,
    }


def load_or_fetch_index_daily(
    *,
    ak: Any,
    spec: dict[str, Any],
    config: dict[str, Any],
    data_paths: dict[str, Path],
    calendar: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    attempts = index_source_attempts(spec, calendar)
    errors: list[str] = []
    calendar_set = set(calendar)
    for attempt in attempts:
        name = attempt["source_function"]
        func = getattr(ak, name, None)
        if func is None:
            errors.append(f"{name}: missing")
            continue
        raw_cache_path = (
            data_paths["index_raw_dir"]
            / f"{spec['alias']}_{name}_{attempt['source_symbol']}.csv"
        )
        try:
            if raw_cache_path.exists() and not args.force:
                df = read_csv_cache(raw_cache_path)
                if df is None:
                    df = call_akshare_unproxied(func, **attempt["kwargs"])
                    write_csv(df, raw_cache_path)
            else:
                df = call_akshare_unproxied(func, **attempt["kwargs"])
                write_csv(df, raw_cache_path)
            normalized = normalize_index_bars(
                df,
                index_alias=spec["alias"],
                instrument=spec["qlib_instrument"],
                source_symbol=attempt["source_symbol"],
                source_function=name,
                volume_unit=attempt["source_volume_unit"],
                money_unit=attempt["source_money_unit"],
                amount_role=attempt["amount_role"],
            )
            covered = normalized[normalized["date"].isin(calendar_set)].copy()
            if covered.empty:
                raise ValueError("no rows matched resolved A-share calendar")
            missing = sorted(calendar_set.difference(set(covered["date"])))
            if covered["date"].min() != calendar[0] or covered["date"].max() != calendar[-1]:
                raise ValueError(
                    "coverage range "
                    f"{covered['date'].min()}..{covered['date'].max()} does not match "
                    f"{calendar[0]}..{calendar[-1]}"
                )
            if missing:
                raise ValueError(
                    f"missing {len(missing)} resolved sessions, first={missing[:5]}"
                )
            result = {
                "daily": covered.reset_index(drop=True),
                "source_function": name,
                "source_symbol": attempt["source_symbol"],
                "source_volume_unit": attempt["source_volume_unit"],
                "source_money_unit": attempt["source_money_unit"],
                "amount_role": attempt["amount_role"],
                "raw_cache_path": raw_cache_path,
            }
            return result
        except Exception as exc:
            errors.append(f"{name}({attempt['source_symbol']}): {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def index_source_attempts(spec: dict[str, Any], calendar: list[str]) -> list[dict[str, Any]]:
    symbol = str(spec["preferred_source_symbol"])
    return [
        {
            "source_function": "stock_zh_index_daily",
            "source_symbol": symbol,
            "kwargs": {"symbol": symbol},
            "source_volume_unit": "shares",
            "source_money_unit": "missing",
            "amount_role": "ignore",
        },
        {
            "source_function": "stock_zh_index_daily_tx",
            "source_symbol": symbol,
            "kwargs": {"symbol": symbol},
            "source_volume_unit": "hands",
            "source_money_unit": "missing",
            "amount_role": "volume",
        },
    ]


def resolved_data_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {
        key: PROJECT_ROOT / value
        for key, value in config["paths"].items()
        if isinstance(value, str)
    }


def ensure_full_directories(
    data_paths: dict[str, Path], output_paths: dict[str, dict[str, Path]]
) -> None:
    directory_keys = [
        "raw_daily_dir",
        "qfq_daily_dir",
        "market_cap_dir",
        "status_dir",
        "qlib_csv_dir",
        "index_raw_dir",
        "index_qlib_csv_dir",
        "processed_universe_dir",
        "processed_index_dir",
        "qlib_provider_uri",
        "index_qlib_provider_uri",
    ]
    for key in directory_keys:
        data_paths[key].mkdir(parents=True, exist_ok=True)
    for section_paths in output_paths.values():
        for path in section_paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)


def load_trade_calendar(
    ak: Any,
    config: dict[str, Any],
    data_paths: dict[str, Path],
    args: argparse.Namespace,
) -> list[str]:
    path = data_paths["status_dir"] / "trading_calendar.csv"
    if path.exists() and not args.force:
        df = pd.read_csv(path)
    else:
        df = call_akshare(
            ak.tool_trade_date_hist_sina,
            retry_without_proxy=config["akshare"]["retry_without_proxy_on_proxy_error"],
        )
        write_csv(df, path)
    return resolve_trade_calendar(
        df["trade_date"],
        config["date_range"]["start_date"],
        config["date_range"]["end_date"],
    )


def load_or_fetch_table(
    *,
    path: Path,
    fetcher,
    force: bool,
) -> pd.DataFrame:
    if path.exists() and not force:
        cached = read_csv_cache(path, dtype="string")
        if cached is not None:
            return cached
    df = fetcher()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return df


def read_csv_cache(path: Path, **kwargs: Any) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        return None
    try:
        return pd.read_csv(path, **kwargs)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        path.unlink(missing_ok=True)
        return None


def load_instrument_metadata(
    ak: Any,
    config: dict[str, Any],
    data_paths: dict[str, Path],
    args: argparse.Namespace,
) -> pd.DataFrame:
    status_dir = data_paths["status_dir"]
    retry = config["akshare"]["retry_without_proxy_on_proxy_error"]
    sh_current = load_or_fetch_table(
        path=status_dir / "stock_info_sh_name_code_main_board.csv",
        force=args.force,
        fetcher=lambda: call_akshare(
            ak.stock_info_sh_name_code, retry_without_proxy=retry, symbol="主板A股"
        ),
    )
    sz_current = load_or_fetch_table(
        path=status_dir / "stock_info_sz_name_code_a_share.csv",
        force=args.force,
        fetcher=lambda: call_akshare(
            ak.stock_info_sz_name_code, retry_without_proxy=retry, symbol="A股列表"
        ),
    )
    sh_delist = load_or_fetch_table(
        path=status_dir / "stock_info_sh_delist_all.csv",
        force=args.force,
        fetcher=lambda: call_akshare(
            ak.stock_info_sh_delist, retry_without_proxy=retry, symbol="全部"
        ),
    )
    sz_delist = load_or_fetch_table(
        path=status_dir / "stock_info_sz_delist_all.csv",
        force=args.force,
        fetcher=lambda: call_akshare(
            ak.stock_info_sz_delist, retry_without_proxy=retry, symbol="终止上市公司"
        ),
    )

    frames = [
        normalize_metadata_frame(
            sh_current,
            code_col="证券代码",
            name_col="证券简称",
            listing_col="上市日期",
            delist_col=None,
            exchange="SH",
            source="stock_info_sh_name_code",
            is_delisted=False,
        ),
        normalize_metadata_frame(
            sz_current,
            code_col="A股代码",
            name_col="A股简称",
            listing_col="A股上市日期",
            delist_col=None,
            exchange="SZ",
            source="stock_info_sz_name_code",
            is_delisted=False,
        ),
        normalize_metadata_frame(
            sh_delist,
            code_col="公司代码",
            name_col="公司简称",
            listing_col="上市日期",
            delist_col="暂停上市日期",
            exchange="SH",
            source="stock_info_sh_delist",
            is_delisted=True,
        ),
        normalize_metadata_frame(
            sz_delist,
            code_col="证券代码",
            name_col="证券简称",
            listing_col="上市日期",
            delist_col="终止上市日期",
            exchange="SZ",
            source="stock_info_sz_delist",
            is_delisted=True,
        ),
    ]
    metadata = pd.concat(frames, ignore_index=True)
    metadata = metadata.dropna(subset=["code", "instrument", "board_bucket"])
    metadata = metadata.sort_values(["instrument", "is_delisted"])
    metadata = metadata.drop_duplicates("instrument", keep="first")
    metadata = metadata.sort_values("instrument").reset_index(drop=True)
    write_csv(metadata, status_dir / "instrument_metadata_target_universe.csv")
    return metadata


def normalize_metadata_frame(
    df: pd.DataFrame,
    *,
    code_col: str,
    name_col: str,
    listing_col: str,
    delist_col: str | None,
    exchange: str,
    source: str,
    is_delisted: bool,
) -> pd.DataFrame:
    out = pd.DataFrame()
    out["code"] = df[code_col].map(strip_code)
    out["instrument"] = out["code"].map(instrument_from_code)
    out["exchange"] = exchange
    out["name"] = df[name_col].astype("string")
    out["listing_date"] = pd.to_datetime(df[listing_col], errors="coerce").dt.strftime("%Y-%m-%d")
    if delist_col and delist_col in df.columns:
        out["delist_date"] = pd.to_datetime(df[delist_col], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        out["delist_date"] = pd.NA
    out["board_bucket"] = out["code"].map(board_bucket)
    out["metadata_source"] = source
    out["is_delisted"] = is_delisted
    return out


def selected_symbol_set(args: argparse.Namespace) -> set[str] | None:
    values = list(args.symbols or [])
    if args.symbols_file:
        with Path(args.symbols_file).open("r", encoding="utf-8") as handle:
            values.extend(
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            )
    if not values:
        return None
    return {instrument_from_code(value) for value in values}


def select_instruments(metadata: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    selected = metadata.copy()
    symbols = selected_symbol_set(args)
    if symbols is not None:
        selected = selected[selected["instrument"].isin(symbols)]
        missing = sorted(symbols.difference(set(selected["instrument"])))
        if missing:
            raise ValueError(f"Symbols not found in target metadata: {missing}")
    if args.limit is not None:
        selected = selected.head(args.limit)
    return selected.reset_index(drop=True)


def load_sz_name_changes(
    ak: Any, data_paths: dict[str, Path], args: argparse.Namespace
) -> pd.DataFrame:
    path = data_paths["status_dir"] / "stock_info_sz_change_name_short.csv"
    if path.exists() and not args.force:
        df = read_csv_cache(path, dtype="string")
        if df is None:
            df = call_akshare_unproxied(ak.stock_info_sz_change_name, symbol="简称变更")
            write_csv(df, path)
    else:
        df = call_akshare_unproxied(ak.stock_info_sz_change_name, symbol="简称变更")
        write_csv(df, path)
    out = df.rename(
        columns={
            "变更日期": "change_date",
            "证券代码": "code",
            "证券简称": "current_name",
            "变更前简称": "previous_name",
            "变更后简称": "next_name",
        }
    ).copy()
    required = {"change_date", "code", "previous_name", "next_name"}
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"Shenzhen name-change data missing columns: {sorted(missing)}")
    out["code"] = out["code"].map(strip_code)
    out["change_date"] = pd.to_datetime(out["change_date"], errors="coerce")
    out = out.dropna(subset=["change_date", "code"])
    return out.sort_values(["code", "change_date"]).reset_index(drop=True)


def process_instruments(
    ak: Any,
    selected: pd.DataFrame,
    calendar: list[str],
    sz_changes_by_code: dict[str, pd.DataFrame],
    data_paths: dict[str, Path],
    args: argparse.Namespace,
    config: dict[str, Any],
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "candidate_frames": [],
        "membership_frames": [],
        "market_cap_audit_rows": [],
        "missing_rows": [],
        "failures": [],
        "processed": [],
    }

    def submit(row: dict[str, Any]) -> dict[str, Any]:
        try:
            if args.sleep:
                time.sleep(args.sleep)
            return process_one_instrument(
                ak=ak,
                row=row,
                calendar=calendar,
                sz_changes_by_code=sz_changes_by_code,
                data_paths=data_paths,
                args=args,
                config=config,
            )
        except Exception as exc:
            return {
                "instrument": row["instrument"],
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }

    rows = selected.to_dict("records")
    max_workers = max(1, int(args.max_workers))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(submit, row): row for row in rows}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            row = futures[future]
            item = future.result()
            instrument = row["instrument"]
            if item.get("status") == "ok":
                results["candidate_frames"].append(item["candidate"])
                if not item["membership"].empty:
                    results["membership_frames"].append(item["membership"])
                results["market_cap_audit_rows"].append(item["market_cap_audit"])
                results["missing_rows"].extend(item["missing_rows"])
                results["processed"].append(item["summary"])
                print(
                    f"[{completed}/{len(rows)}] {instrument} ok "
                    f"candidate={len(item['candidate'])} member={len(item['membership'])}"
                )
            else:
                failure = {
                    "instrument": instrument,
                    "reason": item.get("error", "unknown"),
                }
                results["failures"].append(failure)
                results["missing_rows"].append(
                    {
                        "instrument": instrument,
                        "reason": "instrument_processing_failed",
                        "detail": failure["reason"],
                        "row_count": 0,
                    }
                )
                print(f"[{completed}/{len(rows)}] {instrument} failed: {failure['reason']}", file=sys.stderr)
                if args.fail_fast:
                    for pending in futures:
                        pending.cancel()
                    break
    if not results["membership_frames"]:
        results["membership_frames"].append(empty_membership_frame())
    return results


def process_one_instrument(
    *,
    ak: Any,
    row: dict[str, Any],
    calendar: list[str],
    sz_changes_by_code: dict[str, pd.DataFrame],
    data_paths: dict[str, Path],
    args: argparse.Namespace,
    config: dict[str, Any],
) -> dict[str, Any]:
    instrument = row["instrument"]
    code = strip_code(row["code"])
    bucket = row["board_bucket"]
    threshold = market_cap_threshold_cny(bucket)
    retry = config["akshare"]["retry_without_proxy_on_proxy_error"]

    raw = load_or_fetch_bars(
        ak=ak,
        instrument=instrument,
        adjust="",
        directory=data_paths["raw_daily_dir"],
        calendar=calendar,
        args=args,
        retry_without_proxy=retry,
    )
    qfq = load_or_fetch_bars(
        ak=ak,
        instrument=instrument,
        adjust="qfq",
        directory=data_paths["qfq_daily_dir"],
        calendar=calendar,
        args=args,
        retry_without_proxy=retry,
    )
    qlib_daily = build_qlib_daily(raw, qfq)
    write_qlib_csv(qlib_daily, data_paths["qlib_csv_dir"] / f"{instrument}.csv")

    share_history = load_or_fetch_share_history(ak, instrument, data_paths, args, retry)
    share_source_label = ";".join(sorted(share_history["share_source"].dropna().unique()))
    share_panel = expand_share_asof(share_history, calendar)
    panel = qlib_daily.merge(share_panel, on="date", how="left")
    panel["membership_date"] = panel["date"]
    panel["available_time"] = panel["membership_date"] + " close"
    panel["instrument"] = instrument
    panel["ts_code"] = code
    panel["board_bucket"] = bucket
    panel["market_cap_threshold_cny"] = threshold
    panel["total_market_cap_cny"] = panel["raw_close"] * panel["total_share_asof"]
    panel["share_source"] = panel["share_source"].fillna(share_source_label)
    panel["market_cap_source"] = "raw_close_times_total_share_asof"
    panel["price_source"] = "raw_close"
    panel["source_trade_date"] = panel["date"]
    panel["membership_rule_version"] = "pit_largecap_akshare_qlib_v0"
    panel["is_listed"] = listed_mask(panel, row)
    panel["is_st"] = st_mask_for_instrument(ak, row, panel["date"], sz_changes_by_code, data_paths, args)
    panel["is_suspended"] = False
    panel["status_source"] = status_source_for_row(row)

    threshold_rows = panel[panel["total_market_cap_cny"] > threshold].copy()
    candidate = membership_columns(threshold_rows)
    membership = candidate[
        candidate["is_listed"]
        & ~candidate["is_st"]
        & ~candidate["is_suspended"]
    ].copy()
    if membership.duplicated(["membership_date", "instrument"]).any():
        raise ValueError(f"{instrument} duplicate raw membership rows")

    missing_rows = []
    missing_share_count = int(panel["total_share_asof"].isna().sum())
    if missing_share_count:
        missing_rows.append(
            {
                "instrument": instrument,
                "reason": "missing_total_share_asof",
                "detail": "No prior stock_zh_a_gbjg_em share-change row for trade date",
                "row_count": missing_share_count,
            }
        )

    market_cap_audit = {
        "instrument": instrument,
        "board_bucket": bucket,
        "market_cap_source": "raw_close_times_total_share_asof",
        "price_source": "raw_close",
        "share_source": share_source_label,
        "first_price_date": qlib_daily["date"].min(),
        "last_price_date": qlib_daily["date"].max(),
        "price_rows": int(len(qlib_daily)),
        "candidate_rows": int(len(candidate)),
        "member_rows": int(len(membership)),
        "missing_share_asof_rows": missing_share_count,
    }
    summary = {
        "instrument": instrument,
        "candidate_rows": int(len(candidate)),
        "member_rows": int(len(membership)),
        "is_sh_lifetime_st_excluded": bool(
            row["exchange"] == "SH" and candidate["is_st"].any()
        ),
    }
    return {
        "status": "ok",
        "candidate": candidate,
        "membership": membership,
        "market_cap_audit": market_cap_audit,
        "missing_rows": missing_rows,
        "summary": summary,
    }


def load_or_fetch_bars(
    *,
    ak: Any,
    instrument: str,
    adjust: str,
    directory: Path,
    calendar: list[str],
    args: argparse.Namespace,
    retry_without_proxy: bool,
) -> pd.DataFrame:
    path = directory / f"{instrument}.csv"
    if path.exists() and not args.force:
        cached = read_csv_cache(path)
        if cached is not None:
            return cached
    df, _, _, _ = fetch_stock_bars(
        ak,
        code_or_instrument=instrument,
        start_date=calendar[0],
        end_date=calendar[-1],
        adjust=adjust,
        timeout=args.timeout,
        retry_without_proxy=retry_without_proxy,
    )
    write_csv(df, path)
    return df


def load_or_fetch_share_history(
    ak: Any,
    instrument: str,
    data_paths: dict[str, Path],
    args: argparse.Namespace,
    retry_without_proxy: bool,
) -> pd.DataFrame:
    path = data_paths["market_cap_dir"] / f"{instrument}_shares.csv"
    if path.exists() and not args.force:
        raw = read_csv_cache(path)
        if raw is not None:
            return normalize_cached_share_history(raw)
    try:
        raw = call_akshare_unproxied(
            ak.stock_zh_a_gbjg_em,
            symbol=akshare_symbol_with_exchange_suffix(instrument),
        )
        normalized = normalize_share_history(raw, source_function="stock_zh_a_gbjg_em")
        normalized["share_unit"] = "shares"
        normalized["share_source"] = "stock_zh_a_gbjg_em"
    except Exception as gbjg_exc:
        raw = call_akshare(
            ak.stock_share_change_cninfo,
            retry_without_proxy=retry_without_proxy,
            symbol=strip_code(instrument),
            start_date="19900101",
            end_date="20260531",
        )
        normalized = normalize_cninfo_share_history(raw)
        normalized["share_source"] = "stock_share_change_cninfo"
        normalized["share_fallback_reason"] = f"{type(gbjg_exc).__name__}: {gbjg_exc}"
    write_csv(normalized, path)
    return normalized


def normalize_cached_share_history(raw: pd.DataFrame) -> pd.DataFrame:
    if {"share_date", "total_share_asof"}.issubset(raw.columns):
        out = raw.copy()
        out["share_date"] = pd.to_datetime(out["share_date"], errors="coerce")
        for column in ["total_share_asof", "float_share_asof", "listed_float_share_asof"]:
            if column in out.columns:
                out[column] = pd.to_numeric(out[column], errors="coerce")
        return out.dropna(subset=["share_date", "total_share_asof"]).sort_values("share_date")
    if {"变更日期", "总股本"}.issubset(raw.columns):
        out = normalize_share_history(raw, source_function="stock_zh_a_gbjg_em")
        out["share_unit"] = "shares"
        return out
    if {"变动日期", "总股本"}.issubset(raw.columns):
        return normalize_cninfo_share_history(raw)
    raise ValueError("Cached share history has unsupported schema")


def normalize_cninfo_share_history(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(
        columns={
            "变动日期": "share_date",
            "总股本": "total_share_asof",
            "已流通股份": "float_share_asof",
            "人民币普通股": "listed_float_share_asof",
        }
    ).copy()
    required = {"share_date", "total_share_asof"}
    missing = required.difference(renamed.columns)
    if missing:
        raise ValueError(f"stock_share_change_cninfo missing share columns: {sorted(missing)}")
    keep = [column for column in ["share_date", "total_share_asof", "float_share_asof", "listed_float_share_asof"] if column in renamed.columns]
    out = renamed[keep].copy()
    out["share_date"] = pd.to_datetime(out["share_date"], errors="coerce")
    for column in keep:
        if column != "share_date":
            out[column] = pd.to_numeric(out[column], errors="coerce") * 10_000.0
    out = out.dropna(subset=["share_date", "total_share_asof"])
    out = out.drop_duplicates("share_date", keep="last").sort_values("share_date")
    out["share_unit"] = "ten_thousand_shares_to_shares"
    return out.reset_index(drop=True)


def listed_mask(panel: pd.DataFrame, row: dict[str, Any]) -> pd.Series:
    dates = pd.to_datetime(panel["date"], errors="coerce")
    listing = pd.to_datetime(row.get("listing_date"), errors="coerce")
    delist = pd.to_datetime(row.get("delist_date"), errors="coerce")
    mask = dates >= listing if pd.notna(listing) else pd.Series(False, index=panel.index)
    if pd.notna(delist):
        mask = mask & (dates < delist)
    return mask.fillna(False)


def st_mask_for_instrument(
    ak: Any,
    row: dict[str, Any],
    dates: pd.Series,
    sz_changes_by_code: dict[str, pd.DataFrame],
    data_paths: dict[str, Path],
    args: argparse.Namespace,
) -> pd.Series:
    code = strip_code(row["code"])
    exchange = row["exchange"]
    if exchange == "SH":
        history = load_or_fetch_sh_name_history(ak, row["instrument"], data_paths, args)
        value = has_any_st_name_marker(history)
        return pd.Series(value, index=dates.index)
    if exchange == "SZ":
        changes = sz_changes_by_code.get(code)
        return sz_st_mask_for_dates(dates, changes)
    return pd.Series(True, index=dates.index)


def load_or_fetch_sh_name_history(
    ak: Any,
    instrument: str,
    data_paths: dict[str, Path],
    args: argparse.Namespace,
) -> pd.DataFrame:
    directory = data_paths["status_dir"] / "sh_name_history"
    path = directory / f"{instrument}.csv"
    if path.exists() and not args.force:
        cached = read_csv_cache(path, dtype="string")
        if cached is not None:
            return cached
    try:
        df = call_akshare_unproxied(ak.stock_info_change_name, symbol=strip_code(instrument))
    except Exception as exc:
        if "No tables found" not in str(exc):
            raise
        df = pd.DataFrame(
            columns=[
                "instrument",
                "source_function",
                "source_note",
            ],
            data=[
                {
                    "instrument": instrument,
                    "source_function": "stock_info_change_name",
                    "source_note": "akshare_no_tables_found_interpreted_as_no_recorded_sh_name_change",
                }
            ],
        )
    write_csv(df, path)
    return df


def sz_st_mask_for_dates(dates: pd.Series, changes: pd.DataFrame | None) -> pd.Series:
    if changes is None or changes.empty:
        return pd.Series(False, index=dates.index)
    change_rows = changes.sort_values("change_date").copy()
    base = pd.DataFrame(
        {
            "date": pd.to_datetime(dates, errors="coerce"),
            "_idx": dates.index,
        }
    ).sort_values("date")
    merged = pd.merge_asof(
        base,
        change_rows[["change_date", "previous_name", "next_name"]],
        left_on="date",
        right_on="change_date",
        direction="backward",
    )
    first_previous = str(change_rows.iloc[0]["previous_name"])
    merged["status_name"] = merged["next_name"]
    merged.loc[merged["change_date"].isna(), "status_name"] = first_previous
    merged["is_st"] = merged["status_name"].map(has_st_name_marker).fillna(False)
    return merged.set_index("_idx").sort_index()["is_st"].reindex(dates.index).fillna(False)


def status_source_for_row(row: dict[str, Any]) -> str:
    if row["exchange"] == "SH":
        return "stock_info_change_name_lifetime_st_exclusion;daily_bar_presence"
    if row["exchange"] == "SZ":
        return "stock_info_sz_change_name_asof;daily_bar_presence"
    return "unsupported_exchange"


def membership_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "membership_date",
        "available_time",
        "instrument",
        "ts_code",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "total_market_cap_cny",
        "market_cap_threshold_cny",
        "market_cap_source",
        "price_source",
        "share_source",
        "status_source",
        "source_trade_date",
        "membership_rule_version",
    ]
    out = df[columns].copy()
    out["is_listed"] = out["is_listed"].astype(bool)
    out["is_st"] = out["is_st"].astype(bool)
    out["is_suspended"] = out["is_suspended"].astype(bool)
    return out.sort_values(["membership_date", "instrument"]).reset_index(drop=True)


def empty_membership_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "membership_date",
            "available_time",
            "instrument",
            "ts_code",
            "board_bucket",
            "is_listed",
            "is_st",
            "is_suspended",
            "total_market_cap_cny",
            "market_cap_threshold_cny",
            "market_cap_source",
            "price_source",
            "share_source",
            "status_source",
            "source_trade_date",
            "membership_rule_version",
        ]
    )


def write_summary_outputs(
    *,
    candidate: pd.DataFrame,
    raw_membership: pd.DataFrame,
    executable: pd.DataFrame,
    intervals: pd.DataFrame,
    results: dict[str, Any],
    data_paths: dict[str, Path],
    output_paths: dict[str, dict[str, Path]],
) -> None:
    daily_counts = raw_membership.groupby("membership_date", dropna=False).agg(
        member_count=("instrument", "nunique")
    ).reset_index()
    write_csv(daily_counts, output_paths["tables"]["daily_universe_counts"])

    board_counts = raw_membership.groupby(["membership_date", "board_bucket"], dropna=False).agg(
        member_count=("instrument", "nunique")
    ).reset_index()
    write_csv(board_counts, output_paths["tables"]["board_bucket_counts"])

    status_counts = build_status_exclusion_counts(candidate)
    write_csv(status_counts, output_paths["tables"]["status_exclusion_counts"])
    write_csv(
        pd.DataFrame(results["market_cap_audit_rows"]),
        output_paths["tables"]["market_cap_source_audit"],
    )
    write_csv(
        pd.DataFrame(results["missing_rows"] + results["failures"]),
        output_paths["tables"]["missing_data_summary"],
    )
    processed = pd.DataFrame(results["processed"])
    if not processed.empty:
        processed["interval_rows"] = len(intervals)
        processed["executable_rows_total"] = len(executable)
    write_csv(processed, output_paths["manifests"]["cache_manifest"])
    write_csv(processed, data_paths["cache_manifest"])


def build_status_exclusion_counts(candidate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if candidate.empty:
        return pd.DataFrame(
            columns=[
                "membership_date",
                "board_bucket",
                "candidate_before_status_exclusion_count",
                "excluded_not_listed_count",
                "excluded_st_count",
                "excluded_suspended_count",
                "final_member_count",
                "status_source",
            ]
        )
    for keys, group in candidate.groupby(["membership_date", "board_bucket"], dropna=False):
        membership_date, bucket = keys
        listed = group["is_listed"].astype(bool)
        st = group["is_st"].astype(bool)
        suspended = group["is_suspended"].astype(bool)
        rows.append(
            {
                "membership_date": membership_date,
                "board_bucket": bucket,
                "candidate_before_status_exclusion_count": int(len(group)),
                "excluded_not_listed_count": int((~listed).sum()),
                "excluded_st_count": int((listed & st).sum()),
                "excluded_suspended_count": int((listed & ~st & suspended).sum()),
                "final_member_count": int((listed & ~st & ~suspended).sum()),
                "status_source": ";".join(sorted(group["status_source"].dropna().unique())),
            }
        )
    return pd.DataFrame(rows)


def dump_qlib_provider(
    config: dict[str, Any], data_paths: dict[str, Path], args: argparse.Namespace
) -> None:
    dump_bin = resolve_dump_bin(args)
    provider_uri = data_paths["qlib_provider_uri"]
    if provider_uri.exists():
        shutil.rmtree(provider_uri)
    provider_uri.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(dump_bin),
        "dump_all",
        "--data_path",
        str(data_paths["qlib_csv_dir"]),
        "--qlib_dir",
        str(provider_uri),
        "--freq",
        "day",
        "--include_fields",
        "open,close,high,low,volume,money,turnover_rate,factor",
        "--date_field_name",
        "date",
        "--file_suffix",
        ".csv",
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    instruments_dir = provider_uri / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        data_paths["qlib_instrument_file"],
        instruments_dir / f"{config['universe']['market_name']}.txt",
    )


def dump_index_qlib_provider(
    config: dict[str, Any], data_paths: dict[str, Path], args: argparse.Namespace
) -> None:
    dump_bin = resolve_dump_bin(args)
    provider_uri = data_paths["index_qlib_provider_uri"]
    if provider_uri.exists():
        shutil.rmtree(provider_uri)
    provider_uri.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(dump_bin),
        "dump_all",
        "--data_path",
        str(data_paths["index_qlib_csv_dir"]),
        "--qlib_dir",
        str(provider_uri),
        "--freq",
        "day",
        "--include_fields",
        "open,close,high,low,volume,money",
        "--date_field_name",
        "date",
        "--file_suffix",
        ".csv",
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    instruments_dir = provider_uri / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        data_paths["index_qlib_instrument_file"],
        instruments_dir / f"{config['indices']['qlib_market_name']}.txt",
    )


def resolve_dump_bin(args: argparse.Namespace) -> Path:
    if args.dump_bin_path:
        path = Path(args.dump_bin_path).expanduser()
    else:
        path = Path("/home/xiaolv/code/qlib/scripts/dump_bin.py")
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing Qlib dump_bin.py at {path}; pass --dump-bin-path"
        )
    return path


def check_qlib_provider(
    config: dict[str, Any],
    data_paths: dict[str, Path],
    intervals: pd.DataFrame,
    calendar: list[str],
) -> pd.DataFrame:
    if intervals.empty:
        return pd.DataFrame([{"status": "failed", "reason": "empty intervals"}])
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(data_paths["qlib_provider_uri"]), region=REG_CN)
    fields = list(config["fields"]["qlib_required"])
    instruments = sorted(intervals["instrument"].unique())[:5]
    frame = D.features(
        instruments,
        fields,
        start_time=calendar[0],
        end_time=calendar[-1],
        freq="day",
    )
    return pd.DataFrame(
        [
            {
                "status": "passed",
                "sample_instruments": "|".join(instruments),
                "fields": "|".join(fields),
                "rows": int(len(frame)),
                "non_null_rows": int(frame.dropna(how="all").shape[0]),
            }
        ]
    )


def check_index_qlib_provider(
    config: dict[str, Any],
    data_paths: dict[str, Path],
    intervals: pd.DataFrame,
    calendar: list[str],
) -> pd.DataFrame:
    if intervals.empty:
        return pd.DataFrame([{"status": "failed", "reason": "empty index intervals"}])
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(data_paths["index_qlib_provider_uri"]), region=REG_CN)
    fields = list(config["fields"]["index_qlib_required"])
    instruments = sorted(intervals["instrument"].unique())
    frame = D.features(
        instruments,
        fields,
        start_time=calendar[0],
        end_time=calendar[-1],
        freq="day",
    )
    ohlc_fields = ["$open", "$high", "$low", "$close"]
    rows: list[dict[str, Any]] = []
    for instrument in instruments:
        try:
            one = frame.xs(instrument, level=0, drop_level=False)
        except KeyError:
            one = pd.DataFrame(columns=fields)
        ohlc_non_null = int(one[ohlc_fields].dropna(how="any").shape[0]) if not one.empty else 0
        rows.append(
            {
                "status": "passed" if ohlc_non_null > 0 else "failed",
                "instrument": instrument,
                "fields": "|".join(fields),
                "rows": int(len(one)),
                "ohlc_non_null_rows": ohlc_non_null,
                "volume_nullable_rows": int(one["$volume"].isna().sum()) if "$volume" in one else 0,
                "money_nullable_rows": int(one["$money"].isna().sum()) if "$money" in one else 0,
            }
        )
    return pd.DataFrame(rows)


def write_final_success_report(
    *,
    config: dict[str, Any],
    calendar: list[str],
    selected: pd.DataFrame,
    candidate: pd.DataFrame,
    raw_membership: pd.DataFrame,
    executable: pd.DataFrame,
    intervals: pd.DataFrame,
    results: dict[str, Any],
    qlib_check: pd.DataFrame,
    index_results: dict[str, Any] | None = None,
    index_qlib_check: pd.DataFrame | None = None,
) -> None:
    output_paths = resolved_output_paths(config)
    path = output_paths["reports"]["final_report"]
    lines = [
        "# Data Prepare Final Report",
        "",
        "Decision: `full_run_complete`",
        "",
        "## Coverage",
        "",
        f"- Requested range: `{config['date_range']['start_date']}` to `{config['date_range']['end_date']}`",
        f"- Resolved trading range: `{calendar[0]}` to `{calendar[-1]}`",
        f"- Resolved sessions: `{len(calendar)}`",
        f"- Selected instruments: `{len(selected)}`",
        f"- Candidate before status rows: `{len(candidate)}`",
        f"- Raw membership rows: `{len(raw_membership)}`",
        f"- Executable membership rows: `{len(executable)}`",
        f"- Qlib interval rows: `{len(intervals)}`",
        f"- Instrument failures: `{len(results['failures'])}`",
        "",
        "## Status Policy",
        "",
        "- Shenzhen ST handling uses dated `stock_info_sz_change_name` rows.",
        "- Shanghai ST handling removes the whole asset when `stock_info_change_name`",
        "  ever returns an ST-marked name.",
        "- Suspension handling for membership rows is derived from daily bar presence;",
        "  rows without same-day raw/QFQ bars cannot enter market-cap membership.",
        "",
        "## Qlib Provider Check",
        "",
    ]
    if qlib_check.empty:
        lines.append("- No Qlib provider check rows were produced.")
    else:
        for row in qlib_check.to_dict("records"):
            lines.append("- " + ", ".join(f"{key}={value}" for key, value in row.items()))
    if index_results is not None:
        coverage = index_results["coverage"]
        lines.extend(["", "## Benchmark Index Data", ""])
        lines.append(f"- Index rows: `{len(index_results['daily'])}`")
        lines.append(f"- Index failures: `{len(index_results['failures'])}`")
        if coverage.empty:
            lines.append("- No index coverage rows were produced.")
        else:
            for row in coverage.to_dict("records"):
                lines.append(
                    "- "
                    + ", ".join(
                        f"{key}={value}"
                        for key, value in row.items()
                        if key
                        in {
                            "index_alias",
                            "instrument",
                            "source_function",
                            "source_symbol",
                            "first_date",
                            "last_date",
                            "row_count",
                            "nullable_money_rows",
                        }
                    )
                )
        lines.extend(["", "## Benchmark Index Qlib Provider Check", ""])
        if index_qlib_check is None or index_qlib_check.empty:
            lines.append("- No index Qlib provider check rows were produced.")
        else:
            for row in index_qlib_check.to_dict("records"):
                lines.append("- " + ", ".join(f"{key}={value}" for key, value in row.items()))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index_success_report(
    *,
    config: dict[str, Any],
    calendar: list[str],
    index_results: dict[str, Any],
    index_qlib_check: pd.DataFrame,
) -> None:
    output_paths = resolved_output_paths(config)
    path = output_paths["reports"]["index_report"]
    coverage = index_results["coverage"]
    lines = [
        "# Benchmark Index Data Prepare Report",
        "",
        "Decision: `index_only_complete`",
        "",
        "## Coverage",
        "",
        f"- Requested range: `{config['date_range']['start_date']}` to `{config['date_range']['end_date']}`",
        f"- Resolved trading range: `{calendar[0]}` to `{calendar[-1]}`",
        f"- Resolved sessions: `{len(calendar)}`",
        f"- Index rows: `{len(index_results['daily'])}`",
        f"- Index failures: `{len(index_results['failures'])}`",
        "",
        "## Index Series",
        "",
    ]
    if coverage.empty:
        lines.append("- No index coverage rows were produced.")
    else:
        for row in coverage.to_dict("records"):
            lines.append(
                "- "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in row.items()
                    if key
                    in {
                        "index_alias",
                        "name",
                        "instrument",
                        "source_function",
                        "source_symbol",
                        "first_date",
                        "last_date",
                        "row_count",
                        "missing_calendar_dates",
                        "nullable_volume_rows",
                        "nullable_money_rows",
                    }
                )
            )
    lines.extend(["", "## Index Qlib Provider Check", ""])
    if index_qlib_check.empty:
        lines.append("- No index Qlib provider check rows were produced.")
    else:
        for row in index_qlib_check.to_dict("records"):
            lines.append("- " + ", ".join(f"{key}={value}" for key, value in row.items()))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolved_output_paths(config: dict[str, Any]) -> dict[str, dict[str, Path]]:
    paths: dict[str, dict[str, Path]] = {"reports": {}, "tables": {}, "manifests": {}}
    for section in paths:
        for key, value in config["outputs"][section].items():
            paths[section][key] = EXPERIMENT_ROOT / value
    return paths


def write_final_failure_report(config: dict[str, Any], rows, exc: DataSourceUnsupported) -> None:
    output_paths = resolved_output_paths(config)
    path = output_paths["reports"]["final_report"]
    path.parent.mkdir(parents=True, exist_ok=True)
    blocking = blocking_audit_issues(rows, require_evaluated=True)
    lines = ["# Data Prepare Final Report", "", f"Decision: `{exc.code}`", ""]
    if blocking:
        lines.extend(
            [
                "The full PIT universe build did not start because at least one required",
                "AkShare source category failed the preflight audit. This is intentional:",
                "the requirement disallows latest-only market-cap, ST, suspension, or",
                "security-status fallbacks.",
                "",
                "## Blocking Sources",
                "",
            ]
        )
        for row in blocking:
            lines.append(f"- `{row.category}` via `{row.function_name}`: {row.notes}")
    else:
        lines.extend(
            [
                "All preflight source categories passed under the configured audit policy.",
                "The full data pull is still guarded until the membership writer is",
                "reviewed against the now-supported status-source policy.",
                "",
                "## Status Policy",
                "",
                "- Shenzhen ST handling uses dated `stock_info_sz_change_name` name-change rows.",
                "- Shanghai ST handling uses conservative whole-asset exclusion: if",
                "  `stock_info_change_name` ever returns an ST-marked name for a Shanghai",
                "  instrument, that instrument is removed from the entire universe.",
                "",
                f"Error: `{exc}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_manifest(
    *,
    config: dict[str, Any],
    config_path: Path,
    decision: str,
    audit_rows,
    extra: dict[str, Any] | None = None,
) -> Path:
    output_paths = resolved_output_paths(config)
    manifest_path = output_paths["manifests"]["run_manifest"]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    outputs = {
        f"{section}.{key}": path
        for section, section_paths in output_paths.items()
        for key, path in section_paths.items()
    }
    existing_outputs = {
        key: path
        for key, path in outputs.items()
        if path.is_file() and path != manifest_path
    }
    try:
        import akshare as ak

        akshare_version = getattr(ak, "__version__", None)
    except Exception:
        akshare_version = None
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(PROJECT_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "akshare_version": akshare_version,
        "decision": decision,
        "requested_start_date": config["date_range"]["start_date"],
        "requested_end_date": config["date_range"]["end_date"],
        "qlib_market_date_key": config["universe"]["qlib_market_date_key"],
        "audit": [row.as_dict() for row in audit_rows],
        "outputs": {key: str(path) for key, path in outputs.items()},
        "output_hashes": {
            key: file_sha256(path) for key, path in existing_outputs.items()
        },
        "extra": extra or {},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    raise SystemExit(main())
