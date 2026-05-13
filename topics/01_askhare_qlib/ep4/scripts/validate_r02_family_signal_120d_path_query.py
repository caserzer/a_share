#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402
from run_r02_family_signal_120d_path_query import required_output_columns  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_family_signal_120d_path_query_v1.yaml"


def load_config(config_path: Path) -> dict[str, Any]:
    with topic_path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _check(condition: bool, check_id: str, detail: str, rows: list[dict[str, Any]]) -> None:
    rows.append({"check_id": check_id, "status": "passed" if condition else "failed", "detail": detail})


def _is_row_level_path_csv(path: Path) -> bool:
    try:
        header = pd.read_csv(path, nrows=0).columns
    except Exception:
        return False
    return {"instrument_id", "signal_date", "max_gain_120d", "max_drawdown_120d"}.issubset(set(header))


def validate(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    signals_dir = reports_dir / "signals"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r02_family_signal_120d_path_query_manifest.json"
    validation_path = manifests_dir / "r02_family_signal_120d_path_query_validation.json"
    rows: list[dict[str, Any]] = []

    expected_single = [item["signal_id"] for item in config["single_signals"]]
    expected_review = [item["signal_id"] for item in config["review_composite_signals"]]
    expected_signals = expected_single + expected_review
    expected_cols = required_output_columns()

    _check(manifest_path.exists(), "manifest_exists", relpath(manifest_path), rows)
    _check((reports_dir / "r02_family_signal_120d_signal_dictionary.csv").exists(), "signal_dictionary_exists", relpath(reports_dir / "r02_family_signal_120d_signal_dictionary.csv"), rows)
    _check((reports_dir / "r02_family_signal_120d_validation_audit.csv").exists(), "validation_audit_csv_exists", relpath(reports_dir / "r02_family_signal_120d_validation_audit.csv"), rows)
    if not manifest_path.exists():
        result = {"validation_status": "failed", "failed_checks": ["manifest_exists"]}
        write_json(result, validation_path)
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _check(manifest.get("single_signal_count") == 7, "single_signal_count_7", str(manifest.get("single_signal_count")), rows)
    _check(manifest.get("review_composite_signal_count") == 4, "review_composite_signal_count_4", str(manifest.get("review_composite_signal_count")), rows)
    _check(manifest.get("total_signal_count") == 11, "total_signal_count_11", str(manifest.get("total_signal_count")), rows)
    _check(manifest.get("primary_grain") == "raw_signal_stock_day", "primary_grain_raw_signal_stock_day", str(manifest.get("primary_grain")), rows)
    _check(
        manifest.get("entry_anchor") == "first_executable_next_open_after_signal_date",
        "entry_anchor_first_executable_next_open",
        str(manifest.get("entry_anchor")),
        rows,
    )
    _check(manifest.get("path_horizon_trading_days") == 120, "path_horizon_120", str(manifest.get("path_horizon_trading_days")), rows)
    _check(manifest.get("path_complete_bar_count") == 121, "path_complete_bar_count_121", str(manifest.get("path_complete_bar_count")), rows)
    _check(manifest.get("minus5_trigger_price") == "low", "minus5_trigger_low", str(manifest.get("minus5_trigger_price")), rows)
    _check(manifest.get("max_drawdown_ohlc_order_policy") == "prior_peak_only", "drawdown_policy_prior_peak_only", str(manifest.get("max_drawdown_ohlc_order_policy")), rows)
    _check(manifest.get("atr_method") == "wilder", "atr_method_wilder", str(manifest.get("atr_method")), rows)
    _check(int(manifest.get("atr_period", 0)) == 14, "atr_period_14", str(manifest.get("atr_period")), rows)
    _check(manifest.get("row_level_output_policy") == "per_signal_csv_only_no_merged_all_signal_csv", "row_level_output_policy_per_signal_only", str(manifest.get("row_level_output_policy")), rows)

    dictionary = pd.read_csv(reports_dir / "r02_family_signal_120d_signal_dictionary.csv") if (reports_dir / "r02_family_signal_120d_signal_dictionary.csv").exists() else pd.DataFrame()
    _check(set(dictionary.get("signal_id", [])) == set(expected_signals), "dictionary_has_exact_expected_signals", str(sorted(dictionary.get("signal_id", []))), rows)
    if not dictionary.empty:
        _check(set(dictionary.loc[dictionary["signal_type"].eq("single_family"), "signal_id"]) == set(expected_single), "dictionary_single_signals_match", "", rows)
        _check(set(dictionary.loc[dictionary["signal_type"].eq("same_day_family_and4"), "signal_id"]) == set(expected_review), "dictionary_review_signals_match", "", rows)
        _check(dictionary.loc[dictionary["signal_type"].eq("single_family"), "lineage_check_status"].eq("passed").all(), "single_signal_lineage_passed", "", rows)

    actual_signal_files = sorted(path.name for path in signals_dir.glob("*_120d_path.csv")) if signals_dir.exists() else []
    expected_signal_files = sorted(f"{signal_id}_120d_path.csv" for signal_id in expected_signals)
    _check(actual_signal_files == expected_signal_files, "per_signal_csv_file_set_exact", str(actual_signal_files), rows)

    manifest_paths = manifest.get("per_signal_csv_paths", {})
    _check(set(manifest_paths.keys()) == set(expected_signals), "manifest_per_signal_paths_exact", str(sorted(manifest_paths.keys())), rows)
    row_counts: dict[str, int] = {}
    for signal_id in expected_signals:
        path = signals_dir / f"{signal_id}_120d_path.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        row_counts[signal_id] = int(len(df))
        missing_cols = [col for col in expected_cols if col not in df.columns]
        _check(not missing_cols, f"{signal_id}_required_columns_present", str(missing_cols), rows)
        _check(set(df["signal_id"].astype(str).unique()) <= {signal_id}, f"{signal_id}_constant_signal_id", str(df["signal_id"].astype(str).unique().tolist()), rows)
        if not df.empty:
            entry_valid = df["entry_valid"].astype(bool)
            valid = df.loc[entry_valid]
            if not valid.empty:
                _check(
                    (pd.to_datetime(valid["entry_date"]) > pd.to_datetime(valid["signal_date"])).all(),
                    f"{signal_id}_entry_after_signal_for_valid_rows",
                    "",
                    rows,
                )
                _check(valid["entry_price"].gt(0).all(), f"{signal_id}_entry_price_positive_for_valid_rows", "", rows)
            invalid = df.loc[~entry_valid]
            metric_cols = [
                "first_minus5_date",
                "max_gain_120d",
                "max_loss_120d",
                "max_drawdown_120d",
                "atr14_t0",
                "atr14_t120",
            ]
            if not invalid.empty:
                _check(invalid["entry_invalid_reason"].astype(str).str.len().gt(0).all(), f"{signal_id}_invalid_rows_have_reason", "", rows)
                _check(invalid[metric_cols].isna().all().all(), f"{signal_id}_invalid_rows_have_null_path_metrics", "", rows)
            _check(df["max_drawdown_ohlc_order_policy"].eq("prior_peak_only").all(), f"{signal_id}_drawdown_policy_column_fixed", "", rows)
            _check(df["available_forward_trading_days"].fillna(0).between(0, 120).all(), f"{signal_id}_available_forward_days_range", "", rows)
    _check(row_counts == {k: int(v) for k, v in manifest.get("per_signal_row_counts", {}).items()}, "manifest_row_counts_match_csvs", str(row_counts), rows)

    markdown_files = list(output_root.rglob("*.md"))
    _check(not markdown_files, "no_markdown_report_generated", str([relpath(p) for p in markdown_files]), rows)
    forbidden_names = [p for p in reports_dir.glob("*.csv") if ("all" in p.name.lower() and "signal" in p.name.lower()) or "merged" in p.name.lower()]
    row_level_outside_signals = [p for p in reports_dir.glob("*.csv") if p.parent != signals_dir and _is_row_level_path_csv(p)]
    _check(not forbidden_names, "no_forbidden_merged_csv_names", str([p.name for p in forbidden_names]), rows)
    _check(not row_level_outside_signals, "no_row_level_path_csv_outside_signals_dir", str([p.name for p in row_level_outside_signals]), rows)

    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r02_family_signal_120d_validation_audit.csv"
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    result = {
        "validation_status": "passed" if not failed else "failed",
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
    }
    write_json(result, validation_path)
    manifest["validation_status"] = result["validation_status"]
    write_json(manifest, manifest_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EP4 R02 family signal 120D path query artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
