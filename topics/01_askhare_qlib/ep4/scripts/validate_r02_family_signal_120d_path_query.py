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
from run_r02_family_signal_120d_path_query import RACE_STATUSES, required_output_columns  # noqa: E402


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


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _read_artifact_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def validate(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    signals_dir = reports_dir / "signals"
    episode_signals_dir = reports_dir / "episode_signals"
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
    path_quality_summary_path = reports_dir / "r02_family_signal_120d_path_quality_summary.csv"
    episode_summary_path = reports_dir / "r02_family_signal_120d_episode_summary.csv"
    r03_handoff_path = reports_dir / "r02_family_signal_120d_r03_handoff_diagnostics.csv"
    report_path = reports_dir / "r02_family_signal_120d_path_analysis_report.md"
    _check(path_quality_summary_path.exists(), "path_quality_summary_exists", relpath(path_quality_summary_path), rows)
    _check(episode_summary_path.exists(), "episode_summary_exists", relpath(episode_summary_path), rows)
    _check(r03_handoff_path.exists(), "r03_handoff_diagnostics_exists", relpath(r03_handoff_path), rows)
    _check(report_path.exists(), "markdown_analysis_report_exists", relpath(report_path), rows)
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
    _check(manifest.get("row_level_output_policy") == "per_signal_raw_csv_only_no_merged_all_signal_csv", "row_level_output_policy_per_signal_only", str(manifest.get("row_level_output_policy")), rows)
    _check(manifest.get("r03_handoff_boundary") == "descriptive_analysis_only", "r03_handoff_boundary_descriptive", str(manifest.get("r03_handoff_boundary")), rows)

    dictionary = _read_artifact_csv(reports_dir / "r02_family_signal_120d_signal_dictionary.csv") if (reports_dir / "r02_family_signal_120d_signal_dictionary.csv").exists() else pd.DataFrame()
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
    manifest_episode_paths = manifest.get("per_signal_episode_audit_paths", {})
    _check(set(manifest_episode_paths.keys()) == set(expected_signals), "manifest_episode_paths_exact", str(sorted(manifest_episode_paths.keys())), rows)
    row_counts: dict[str, int] = {}
    episode_counts: dict[str, int] = {}
    for signal_id in expected_signals:
        path = signals_dir / f"{signal_id}_120d_path.csv"
        if not path.exists():
            continue
        df = _read_artifact_csv(path)
        row_counts[signal_id] = int(len(df))
        missing_cols = [col for col in expected_cols if col not in df.columns]
        _check(not missing_cols, f"{signal_id}_required_columns_present", str(missing_cols), rows)
        forbidden_posthoc = {"episode_id", "episode_end_signal_date", "episode_trigger_count"}.intersection(df.columns)
        _check(not forbidden_posthoc, f"{signal_id}_raw_csv_has_no_posthoc_episode_fields", str(sorted(forbidden_posthoc)), rows)
        _check(set(df["signal_id"].astype(str).unique()) <= {signal_id}, f"{signal_id}_constant_signal_id", str(df["signal_id"].astype(str).unique().tolist()), rows)
        if not df.empty:
            entry_valid = _boolish(df["entry_valid"])
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
            statuses_ok = set(df["race_plus10_minus5_status"].dropna().astype(str)).issubset(RACE_STATUSES)
            _check(statuses_ok, f"{signal_id}_race_status_values_allowed", str(sorted(set(df["race_plus10_minus5_status"].dropna().astype(str)))), rows)
            derived_minus5 = df["race_plus10_minus5_status"].map(
                {
                    "downside_first": True,
                    "downside_only_complete": True,
                    "upside_first": False,
                    "upside_only_complete": False,
                    "neither_hit_complete": False,
                    "same_offset": pd.NA,
                    "censored_incomplete": pd.NA,
                }
            )
            comparable = ~(derived_minus5.isna() & df["minus5_before_plus10"].isna())
            if comparable.any():
                _check(
                    (derived_minus5.loc[comparable].astype(str).str.lower().values == df.loc[comparable, "minus5_before_plus10"].astype(str).str.lower().values).all(),
                    f"{signal_id}_minus5_before_plus10_derived_from_status",
                    "",
                    rows,
                )
            _check(
                df.loc[_boolish(df["incomplete_flag"]), "path_quality_flag"].eq("incomplete").all(),
                f"{signal_id}_incomplete_flag_implies_incomplete_quality",
                "",
                rows,
            )
        episode_path = episode_signals_dir / f"{signal_id}_120d_episode_audit.csv"
        _check(episode_path.exists(), f"{signal_id}_episode_audit_exists", relpath(episode_path), rows)
        if episode_path.exists():
            ep = _read_artifact_csv(episode_path)
            episode_counts[signal_id] = int(len(ep))
            required_episode_cols = {
                "signal_id",
                "instrument_id",
                "split",
                "episode_id",
                "episode_start_signal_date",
                "episode_end_signal_date",
                "episode_trigger_count",
                "episode_entry_valid",
                "episode_path_quality_flag",
            }
            _check(required_episode_cols.issubset(ep.columns), f"{signal_id}_episode_required_columns_present", str(sorted(required_episode_cols.difference(ep.columns))), rows)
            if not ep.empty:
                _check(
                    (pd.to_datetime(ep["episode_start_signal_date"]) <= pd.to_datetime(ep["episode_end_signal_date"])).all(),
                    f"{signal_id}_episode_dates_ordered",
                    "",
                    rows,
                )
    _check(row_counts == {k: int(v) for k, v in manifest.get("per_signal_row_counts", {}).items()}, "manifest_row_counts_match_csvs", str(row_counts), rows)
    _check(episode_counts == {k: int(v) for k, v in manifest.get("per_signal_episode_counts", {}).items()}, "manifest_episode_counts_match_csvs", str(episode_counts), rows)

    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8").lower()
        forbidden_report_tokens = ["production-ready", "r03-ready", "validated strategy", "buy signal", "可交易信号", "已验证策略"]
        found_forbidden = [token for token in forbidden_report_tokens if token in report_text]
        _check(not found_forbidden, "markdown_report_has_no_forbidden_promotion_language", str(found_forbidden), rows)
    forbidden_names = [p for p in reports_dir.glob("*.csv") if ("all" in p.name.lower() and "signal" in p.name.lower()) or "merged" in p.name.lower()]
    row_level_outside_signals = [p for p in reports_dir.glob("*.csv") if p.parent not in {signals_dir, episode_signals_dir} and _is_row_level_path_csv(p)]
    _check(not forbidden_names, "no_forbidden_merged_csv_names", str([p.name for p in forbidden_names]), rows)
    _check(not row_level_outside_signals, "no_row_level_path_csv_outside_signals_dir", str([p.name for p in row_level_outside_signals]), rows)

    if path_quality_summary_path.exists():
        summary = _read_artifact_csv(path_quality_summary_path)
        required_summary = {
            "signal_id",
            "signal_type",
            "grain",
            "row_count",
            "episode_count",
            "entry_valid_count",
            "atr_t0_usable_rate",
            "atr_evidence_status",
        }
        _check(required_summary.issubset(summary.columns), "path_quality_summary_required_columns_present", str(sorted(required_summary.difference(summary.columns))), rows)
        if required_summary.issubset(summary.columns):
            ep_grain = summary["grain"].eq("episode_first_trigger")
            _check((summary.loc[ep_grain, "episode_count"].fillna(-1).astype(int) == summary.loc[ep_grain, "row_count"].fillna(-2).astype(int)).all(), "path_quality_episode_count_equals_row_count", "", rows)
            _check(summary.loc[~ep_grain, "episode_count"].isna().all(), "path_quality_raw_episode_count_null", "", rows)
            zero_valid = summary["entry_valid_count"].fillna(0).astype(int).eq(0)
            _check(summary.loc[zero_valid, "atr_t0_usable_rate"].isna().all(), "atr_rate_null_when_no_valid_entries", "", rows)
            _check(summary.loc[zero_valid, "atr_evidence_status"].eq("low_coverage_audit_only").all(), "atr_status_low_coverage_when_no_valid_entries", "", rows)
    if r03_handoff_path.exists():
        handoff = _read_artifact_csv(r03_handoff_path)
        required_handoff = {
            "signal_id",
            "recommended_r03_status",
            "primary_blocker",
            "primary_opportunity",
            "status_basis_metrics",
            "atr_evidence_status",
        }
        _check(required_handoff.issubset(handoff.columns), "r03_handoff_required_columns_present", str(sorted(required_handoff.difference(handoff.columns))), rows)
        if required_handoff.issubset(handoff.columns):
            allowed_status = {"continue_to_r03_design", "needs_entry_delay_or_stop_design", "background_only", "stop_candidate"}
            _check(set(handoff["recommended_r03_status"].astype(str)).issubset(allowed_status), "r03_handoff_status_values_allowed", str(sorted(set(handoff["recommended_r03_status"].astype(str)))), rows)
            _check(handoff["primary_blocker"].astype(str).str.len().gt(0).all(), "r03_handoff_primary_blocker_nonempty", "", rows)
            _check(handoff["primary_opportunity"].astype(str).str.len().gt(0).all(), "r03_handoff_primary_opportunity_nonempty", "", rows)
            _check(handoff["status_basis_metrics"].astype(str).str.len().gt(0).all(), "r03_handoff_basis_nonempty", "", rows)

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
