#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from pandas.errors import EmptyDataError

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402
from run_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic import _hash_text, _load_calendar, _split_bounds, _split_for_date  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r05_preflight_alpha_pool_quick_feasibility_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
REQUIRED_REPORTS = [
    "r05_preflight_candidate_formula_frozen.csv",
    "r05_preflight_split_return_summary.csv",
    "r05_preflight_execution_audit.csv",
    "r05_preflight_event_collapse_audit.csv",
    "r05_preflight_gate_audit.csv",
    "r05_preflight_final_decision.csv",
    "r05_preflight_alpha_pool_quick_feasibility_final_report.md",
]
REQUIRED_CACHE = [
    "r05_preflight_candidate_event_panel.parquet",
    "r05_preflight_forward_return_panel.parquet",
]
FINAL_DECISIONS = {
    "r05_preflight_go_r05a_full_protocol",
    "r05_preflight_stop_no_absolute_floor",
    "r05_preflight_insufficient_sample",
    "r05_preflight_execution_blocked",
}
GATE_STATUSES = {
    "preflight_pass",
    "preflight_fail_no_absolute_floor",
    "preflight_fail_insufficient_sample",
    "preflight_fail_execution_blocked",
}
CANONICAL_CANDIDATES = {
    "low_vol_uptrend_preflight",
    "base_breakout_vcp_preflight",
    "cross_sectional_low_beta_low_vol_preflight",
}
EVENT_COLUMNS = {
    "candidate_id",
    "candidate_family",
    "instrument_id",
    "decision_date",
    "entry_target_date",
    "event_key",
    "split",
    "split_assignment_date",
    "formula_hash",
    "membership_flag",
    "missing_feature_flag",
    "raw_trigger_date",
    "collapse_anchor_date",
    "collapse_window_trading_days",
    "raw_trigger_count_in_window",
    "suppressed_trigger_count_in_window",
    "kept_event_flag",
    "entry_open_available_flag",
    "entry_limit_up_inferred_flag",
    "entry_executable_flag",
    "actual_entry_execution_date",
    "entry_execution_lag_trading_days",
    "path_censor_reason",
}
FORWARD_COLUMNS = {
    "candidate_id",
    "candidate_family",
    "instrument_id",
    "event_key",
    "split",
    "decision_date",
    "actual_entry_execution_date",
    "actual_entry_price",
    "exit_target_date",
    "actual_exit_date",
    "actual_exit_price",
    "split_assignment_date",
    "split_end_date",
    "exit_available_flag",
    "exit_limit_down_inferred_flag",
    "exit_executable_flag",
    "exit_execution_lag_trading_days",
    "hold20_gross_return",
    "hold20_net_return",
    "path_complete_flag",
    "path_censor_reason",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def _add(rows: list[dict[str, Any]], check_id: str, name: str, condition: bool, severity: str = "error", details: str = "", artifact_path: str = "") -> None:
    rows.append(
        {
            "check_id": check_id,
            "check_name": name,
            "severity": severity,
            "status": "passed" if condition else "failed",
            "details": "" if condition else details,
            "artifact_path": artifact_path,
        }
    )


def _status(rows: list[dict[str, Any]]) -> str:
    audit = pd.DataFrame(rows)
    failed = audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"])
    return "failed" if bool(failed.any()) else "passed"


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, required: set[str], check_id: str, path: Path) -> None:
    missing = sorted(required - set(df.columns))
    _add(rows, check_id, f"{path.name}_columns", not missing, "error", f"missing columns: {missing}", relpath(path))


def _add_trading_days(calendar: pd.DatetimeIndex, date: Any, offset: int) -> pd.Timestamp:
    dt = pd.to_datetime(date, errors="coerce")
    if pd.isna(dt):
        return pd.NaT
    pos = int(calendar.searchsorted(pd.Timestamp(dt).normalize(), side="left"))
    target = pos + offset
    if target < 0 or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target]).normalize()


def _collapse_window_ok(events: pd.DataFrame, calendar: pd.DatetimeIndex) -> bool:
    if events.empty:
        return True
    for (_candidate, _instrument), part in events.groupby(["candidate_id", "instrument_id"], sort=False):
        dates = pd.to_datetime(part["collapse_anchor_date"], errors="coerce").dropna().sort_values().tolist()
        for prev, current in zip(dates, dates[1:], strict=False):
            if pd.Timestamp(current).normalize() <= _add_trading_days(calendar, prev, 20):
                return False
    return True


def _split_assignment_ok(events: pd.DataFrame, config: dict[str, Any]) -> bool:
    bounds = _split_bounds(config)
    if events.empty:
        return True
    actual = pd.to_datetime(events["actual_entry_execution_date"], errors="coerce")
    target = pd.to_datetime(events["entry_target_date"], errors="coerce")
    assigned = pd.to_datetime(events["split_assignment_date"], errors="coerce")
    expected = actual.where(actual.notna(), target)
    expected_match = (assigned.fillna(pd.Timestamp("1900-01-01")) == expected.fillna(pd.Timestamp("1900-01-01"))).all()
    split_match = events.apply(lambda r: _split_for_date(r["split_assignment_date"], bounds) == str(r["split"]), axis=1).all()
    return bool(expected_match and split_match)


def _final_decision_consistent(gate: pd.DataFrame, final_decision: str) -> bool:
    statuses = gate["preflight_gate_status"].astype(str)
    if statuses.eq("preflight_pass").any():
        return final_decision == "r05_preflight_go_r05a_full_protocol"
    if statuses.eq("preflight_fail_insufficient_sample").all():
        return final_decision == "r05_preflight_insufficient_sample"
    if statuses.eq("preflight_fail_execution_blocked").any():
        return final_decision == "r05_preflight_execution_blocked"
    return final_decision == "r05_preflight_stop_no_absolute_floor"


def validate(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r05_preflight_alpha_pool_quick_feasibility_manifest.json"
    validation_path = manifests_dir / "r05_preflight_alpha_pool_quick_feasibility_validation.json"
    audit_path = reports_dir / "r05_preflight_alpha_pool_quick_feasibility_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    required_inputs = [
        config["upstream_r04e"]["validation"],
        config["upstream_r04e"]["final_decision"],
        config["price_provider"]["calendar_source_path"],
        config["price_provider"]["instrument_source_path"],
    ]
    for idx, path in enumerate(required_inputs, start=1):
        _add(rows, f"I{idx:02d}", f"required_input_exists_{Path(path).name}", topic_path(path).exists(), "fatal", path, path)

    r04e_validation = _read_json(config["upstream_r04e"]["validation"])
    r04e_final = _read_csv(topic_path(config["upstream_r04e"]["final_decision"]))
    r04e_final_decision = "" if r04e_final.empty else str(r04e_final.iloc[0].get("final_decision", ""))
    _add(rows, "U01", "r04e_validation_passed", r04e_validation.get("validation_status") == "passed", "fatal", str(r04e_validation.get("validation_status")), config["upstream_r04e"]["validation"])
    _add(rows, "U02", "r04e_final_decision_frozen", r04e_final_decision == "r04e_union_not_viable_validation", "fatal", r04e_final_decision, config["upstream_r04e"]["final_decision"])

    for name in REQUIRED_REPORTS:
        _add(rows, f"R_{name}", f"required_report_exists_{name}", (reports_dir / name).exists(), "fatal", relpath(reports_dir / name), relpath(reports_dir / name))
    for name in REQUIRED_CACHE:
        _add(rows, f"K_{name}", f"required_cache_exists_{name}", (cache_dir / name).exists(), "fatal", relpath(cache_dir / name), relpath(cache_dir / name))
    _add(rows, "M01", "required_manifest_exists", manifest_path.exists(), "fatal", relpath(manifest_path), relpath(manifest_path))

    if _status(rows) == "failed":
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {
            "validation_status": "failed",
            "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] in {"fatal", "error"}],
            "warning_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] == "warning"],
            "final_decision": "",
            "candidate_pass_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audit_path": relpath(audit_path),
            "manifest_path": relpath(manifest_path),
        }
        write_json(result, validation_path)
        return result

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    manifest = _read_json(manifest_path)
    formula = _read_csv(reports_dir / "r05_preflight_candidate_formula_frozen.csv")
    event = pd.read_parquet(cache_dir / "r05_preflight_candidate_event_panel.parquet")
    forward = pd.read_parquet(cache_dir / "r05_preflight_forward_return_panel.parquet")
    collapse = _read_csv(reports_dir / "r05_preflight_event_collapse_audit.csv")
    summary = _read_csv(reports_dir / "r05_preflight_split_return_summary.csv")
    execution = _read_csv(reports_dir / "r05_preflight_execution_audit.csv")
    gate = _read_csv(reports_dir / "r05_preflight_gate_audit.csv")
    final = _read_csv(reports_dir / "r05_preflight_final_decision.csv")
    report_text = (reports_dir / "r05_preflight_alpha_pool_quick_feasibility_final_report.md").read_text(encoding="utf-8")

    _require_columns(rows, formula, {"candidate_id", "candidate_family", "formula_text", "formula_hash", "parameter_json", "decision_date_policy", "entry_policy", "exit_policy", "round_trip_cost_bp", "active_flag"}, "C01", reports_dir / "r05_preflight_candidate_formula_frozen.csv")
    _require_columns(rows, event, EVENT_COLUMNS, "C02", cache_dir / "r05_preflight_candidate_event_panel.parquet")
    _require_columns(rows, forward, FORWARD_COLUMNS, "C03", cache_dir / "r05_preflight_forward_return_panel.parquet")
    _require_columns(rows, collapse, {"candidate_id", "candidate_family", "instrument_id", "raw_trigger_count", "kept_event_count", "suppressed_by_collapse_count", "collapse_window_trading_days", "first_raw_trigger_date", "last_raw_trigger_date", "collapse_audit_status", "blocking_reason"}, "C04", reports_dir / "r05_preflight_event_collapse_audit.csv")
    _require_columns(rows, summary, {"candidate_id", "candidate_family", "split", "event_count", "raw_trigger_count", "suppressed_by_collapse_count", "complete_event_count", "complete_event_share", "hold20_net_mean", "hold20_net_median", "hold20_net_p10", "loss_le_5_rate"}, "C05", reports_dir / "r05_preflight_split_return_summary.csv")
    _require_columns(rows, execution, {"candidate_id", "candidate_family", "split", "event_count", "entry_unavailable_after_lag_count", "entry_limit_up_block_count", "exit_unavailable_after_lag_count", "exit_limit_down_block_count", "split_boundary_exit_out_of_split_count", "complete_event_count", "complete_event_share", "execution_audit_status", "blocking_reason"}, "C06", reports_dir / "r05_preflight_execution_audit.csv")
    _require_columns(rows, gate, {"candidate_id", "candidate_family", "validation_event_count", "validation_complete_event_share", "validation_hold20_net_mean", "validation_hold20_net_median", "validation_hold20_net_p10", "validation_loss_le_5_rate", "preflight_gate_status", "blocking_reason"}, "C07", reports_dir / "r05_preflight_gate_audit.csv")
    _require_columns(rows, final, {"requirement_id", "final_decision", "candidate_pass_count", "passed_candidate_ids", "passed_candidate_families", "blocking_reason", "allowed_next_requirement", "created_at"}, "C08", reports_dir / "r05_preflight_final_decision.csv")

    formula_ids = set(formula.get("candidate_id", pd.Series(dtype=str)).astype(str))
    _add(rows, "C09", "canonical_candidate_count_exact", formula_ids == CANONICAL_CANDIDATES and len(formula_ids) == 3, "error", str(formula_ids))
    _add(rows, "C10", "no_noncanonical_candidates", set(event.get("candidate_id", pd.Series(dtype=str)).astype(str)).issubset(CANONICAL_CANDIDATES), "error", str(set(event.get("candidate_id", pd.Series(dtype=str)).astype(str)) - CANONICAL_CANDIDATES))
    hash_ok = True
    if {"formula_text", "formula_hash"}.issubset(formula.columns):
        hash_ok = bool((formula["formula_text"].astype(str).map(_hash_text) == formula["formula_hash"].astype(str)).all())
    _add(rows, "C11", "formula_text_hash_consistent", hash_ok, "error", relpath(reports_dir / "r05_preflight_candidate_formula_frozen.csv"))
    _add(rows, "C12", "gate_status_registered", set(gate.get("preflight_gate_status", pd.Series(dtype=str)).astype(str)).issubset(GATE_STATUSES), "error", str(set(gate.get("preflight_gate_status", pd.Series(dtype=str)).astype(str)) - GATE_STATUSES))
    final_decision = "" if final.empty else str(final.iloc[0].get("final_decision", ""))
    _add(rows, "C13", "final_decision_registered", final_decision in FINAL_DECISIONS, "error", final_decision)
    _add(rows, "C14", "final_decision_consistent_with_gate", _final_decision_consistent(gate, final_decision), "error", final_decision)
    if final_decision == "r05_preflight_go_r05a_full_protocol":
        passed_ids = str(final.iloc[0].get("passed_candidate_ids", ""))
        passed_families = str(final.iloc[0].get("passed_candidate_families", ""))
        _add(rows, "C15", "go_decision_has_passed_candidates", bool(passed_ids and passed_ids != "nan" and passed_families and passed_families != "nan"), "error", "empty passed candidate ids/families")

    _add(rows, "C16", "event_panel_kept_events_only", event.empty or pd.to_numeric(event["kept_event_flag"], errors="coerce").eq(1).all(), "error", "kept_event_flag non-1")
    _add(rows, "C17", "collapse_window_respected", _collapse_window_ok(event, calendar), "error", "same instrument candidate kept inside 20 trading days")
    collapse_balance = True
    if not collapse.empty:
        raw = pd.to_numeric(collapse["raw_trigger_count"], errors="coerce")
        kept = pd.to_numeric(collapse["kept_event_count"], errors="coerce")
        suppressed = pd.to_numeric(collapse["suppressed_by_collapse_count"], errors="coerce")
        collapse_balance = bool((raw == kept + suppressed).all())
    _add(rows, "C18", "collapse_raw_count_balanced", collapse_balance, "error", "raw != kept + suppressed")
    if not summary.empty:
        summary_balance = bool((pd.to_numeric(summary["raw_trigger_count"], errors="coerce") == pd.to_numeric(summary["event_count"], errors="coerce") + pd.to_numeric(summary["suppressed_by_collapse_count"], errors="coerce")).all())
    else:
        summary_balance = False
    _add(rows, "C19", "split_level_raw_suppressed_balanced", summary_balance, "error", "summary raw count mismatch")
    _add(rows, "C20", "split_assignment_rule", _split_assignment_ok(event, config), "error", "split_assignment_date mismatch")
    complete = forward[pd.to_numeric(forward.get("path_complete_flag", 0), errors="coerce").eq(1)].copy()
    complete_dates_ok = True
    if not complete.empty:
        complete_dates_ok = bool((pd.to_datetime(complete["actual_exit_date"], errors="coerce") <= pd.to_datetime(complete["split_end_date"], errors="coerce")).all())
    _add(rows, "C21", "complete_paths_do_not_cross_split", complete_dates_ok, "error", "actual_exit_date > split_end_date")
    boundary = forward[pd.to_datetime(forward.get("exit_target_date"), errors="coerce") > pd.to_datetime(forward.get("split_end_date"), errors="coerce")]
    _add(rows, "C22", "cross_split_paths_censored", boundary.empty or boundary["path_censor_reason"].astype(str).eq("split_boundary_exit_out_of_split").all(), "error", "cross split path not censored")
    _add(rows, "C23", "out_of_scope_excluded_from_summary", set(summary["split"].astype(str)).issubset(set(SPLITS)), "error", str(set(summary["split"].astype(str)) - set(SPLITS)))

    required_manifest = {
        "requirement_id",
        "requirement_path",
        "config_path",
        "output_root",
        "created_at",
        "split_definition_hash",
        "price_provider_hash",
        "upstream_artifact_hashes_json",
        "formula_hashes_json",
        "final_decision",
        "artifact_hashes_json",
    }
    _add(rows, "C24", "manifest_required_keys_present", required_manifest.issubset(manifest.keys()), "error", str(sorted(required_manifest - set(manifest.keys()))))
    expected_split_hash = _hash_text(json.dumps(config["split"], sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str))
    _add(rows, "C25", "split_definition_hash_matches_config", manifest.get("split_definition_hash") == expected_split_hash, "error", str(manifest.get("split_definition_hash")))
    forbidden = [s for s in config["validation"]["forbidden_report_strings"] if s.lower() in report_text.lower()]
    _add(rows, "C26", "final_report_forbidden_language_absent", not forbidden, "error", str(forbidden), relpath(reports_dir / "r05_preflight_alpha_pool_quick_feasibility_final_report.md"))

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    validation_status = _status(rows)
    result = {
        "validation_status": validation_status,
        "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] in {"fatal", "error"}],
        "warning_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] == "warning"],
        "final_decision": final_decision,
        "candidate_pass_count": int(final.iloc[0].get("candidate_pass_count", 0)) if not final.empty else 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audit_path": relpath(audit_path),
        "manifest_path": relpath(manifest_path),
    }
    write_json(result, validation_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = validate(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
