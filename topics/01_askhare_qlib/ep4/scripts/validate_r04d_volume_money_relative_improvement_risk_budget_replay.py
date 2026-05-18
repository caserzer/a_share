#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04d_volume_money_relative_improvement_risk_budget_replay_v1.yaml"
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_upstream_r04c_state_changed",
    "blocked_pool_reconstruction_failed",
    "blocked_gate0_metric_replay_spec_failed",
    "blocked_policy_matrix_invalid",
    "blocked_selection_leakage_detected",
    "r04d_no_policy_passed_validation",
    "r04d_policy_validation_only_not_robust",
    "r04d_policy_passed_relative_improvement_diagnostic_only",
    "r04d_policy_strong_pass_diagnostic_only",
}
REPORTS = [
    "r04d_upstream_state_audit.csv",
    "r04d_gate0_metric_replay_spec_frozen.csv",
    "r04d_volume_money_pool_reconstruction_audit.csv",
    "r04d_policy_matrix_frozen.csv",
    "r04d_policy_duplicate_audit.csv",
    "r04d_policy_replay_summary.csv",
    "r04d_matched_baseline_policy_replay_summary.csv",
    "r04d_policy_vs_volume_money_hold120_summary.csv",
    "r04d_train_policy_selection_trace.csv",
    "r04d_validation_gate_audit.csv",
    "r04d_robustness_readout.csv",
    "r04d_winner_retention_audit.csv",
    "r04d_censored_replay_audit.csv",
    "r04d_cost_turnover_audit.csv",
    "r04d_final_decision.csv",
    "r04d_volume_money_relative_improvement_risk_budget_final_report.md",
]
CACHE = [
    "r04d_volume_money_pool_event_panel.parquet",
    "r04d_daily_policy_path_panel.parquet",
    "r04d_policy_replay_panel.parquet",
    "r04d_policy_selection_panel.parquet",
]
FORBIDDEN_FAMILIES = {
    "ATR_trailing",
    "EMA_trailing",
    "CTA",
    "profit_lock_after_gain",
    "market_state_scaled",
    "industry_state_scaled",
}


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _add(rows: list[dict[str, Any]], name: str, condition: bool, severity: str = "error", details: str = "", artifact_path: str = "") -> None:
    rows.append(
        {
            "check_name": name,
            "status": "passed" if condition else "failed",
            "severity": severity,
            "details": "" if condition else details,
            "artifact_path": artifact_path,
        }
    )


def _status(rows: list[dict[str, Any]]) -> str:
    audit = pd.DataFrame(rows)
    failed = audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"])
    return "failed" if bool(failed.any()) else "passed"


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], name: str, path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, name, not missing, "error", f"missing columns: {missing}", relpath(path))


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_manifest.json"
    validation_path = manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_validation.json"
    audit_path = reports_dir / "r04d_volume_money_relative_improvement_risk_budget_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _add(rows, f"required_report_exists_{name}", (reports_dir / name).exists(), "fatal", "required report missing", relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", (cache_dir / name).exists(), "fatal", "required cache missing", relpath(cache_dir / name))
    _add(rows, "required_manifest_exists", manifest_path.exists(), "fatal", "manifest missing", relpath(manifest_path))

    if not manifest_path.exists():
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": "failed", "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed"], "audit_path": relpath(audit_path)}
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    r04c_val = _read_json(Path(config["upstream_r04c"]["validation"]))
    r04b_val = _read_json(Path(config["upstream_r04b"]["validation"]))
    _add(rows, "upstream_r04c_validation_passed", r04c_val.get("validation_status") == "passed", "fatal", f"status={r04c_val.get('validation_status')}")
    _add(rows, "upstream_r04b_validation_passed", r04b_val.get("validation_status") == "passed", "fatal", f"status={r04b_val.get('validation_status')}")
    _add(rows, "upstream_r04c_final_decision_frozen", r04c_val.get("final_decision") == "r04c_no_candidate_pool_passed_validation", "fatal", f"final_decision={r04c_val.get('final_decision')}")
    _add(rows, "manifest_final_decision_allowed", manifest.get("final_decision") in FINAL_DECISIONS, "error", str(manifest.get("final_decision")))
    _add(rows, "manifest_metric_basis_weighted", manifest.get("net_return_metric_basis") == "weighted_net_return", "error", "net_return_metric_basis mismatch")
    _add(rows, "manifest_has_artifact_hashes", bool(manifest.get("artifact_hashes")), "error", "missing artifact hashes")

    required_upstream = [
        config["upstream_r04c"]["pool_event_panel"],
        config["upstream_r04c"]["matched_baseline_panel"],
        config["upstream_r02_family_precision"]["action_time_panel"],
    ]
    for path in required_upstream:
        _add(rows, f"required_input_exists_{Path(path).name}", topic_path(path).exists(), "fatal", "required input missing", path)

    required_paths = [reports_dir / name for name in REPORTS] + [cache_dir / name for name in CACHE]
    if not all(path.exists() for path in required_paths):
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": _status(rows), "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed"], "audit_path": relpath(audit_path), "manifest_path": relpath(manifest_path)}
        write_json(result, validation_path)
        return result

    gate0_path = reports_dir / "r04d_gate0_metric_replay_spec_frozen.csv"
    recon_path = reports_dir / "r04d_volume_money_pool_reconstruction_audit.csv"
    matrix_path = reports_dir / "r04d_policy_matrix_frozen.csv"
    summary_path = reports_dir / "r04d_policy_replay_summary.csv"
    matched_path = reports_dir / "r04d_matched_baseline_policy_replay_summary.csv"
    selection_path = reports_dir / "r04d_train_policy_selection_trace.csv"
    validation_gate_path = reports_dir / "r04d_validation_gate_audit.csv"
    robustness_path = reports_dir / "r04d_robustness_readout.csv"
    final_path = reports_dir / "r04d_final_decision.csv"
    report_path = reports_dir / "r04d_volume_money_relative_improvement_risk_budget_final_report.md"
    replay_path = cache_dir / "r04d_policy_replay_panel.parquet"

    gate0 = _read_csv(gate0_path)
    recon = _read_csv(recon_path)
    matrix = _read_csv(matrix_path)
    summary = _read_csv(summary_path)
    matched = _read_csv(matched_path)
    selection = _read_csv(selection_path)
    validation_gate = _read_csv(validation_gate_path)
    robustness = _read_csv(robustness_path)
    final = _read_csv(final_path)
    replay = pd.read_parquet(replay_path)
    report_text = report_path.read_text(encoding="utf-8")

    _require_columns(rows, gate0, {"spec_section", "spec_item", "frozen_value_json", "formula_text", "source_config_key", "formula_hash"}, "gate0_columns", gate0_path)
    required_sections = {"return", "cost", "sizing", "execution", "censored", "matched_comparator", "max_gain50_retention", "baseline_delta", "gate_threshold", "selection_score"}
    _add(rows, "gate0_required_sections_present", required_sections.issubset(set(gate0.get("spec_section", pd.Series(dtype=str)).astype(str))), "error", "missing gate0 sections", relpath(gate0_path))
    _add(rows, "gate0_formula_hash_complete", "formula_hash" in gate0.columns and gate0["formula_hash"].astype(str).str.len().ge(32).all(), "error", "formula_hash incomplete", relpath(gate0_path))

    _require_columns(rows, recon, {"reconciliation_status", "overlap_share_vs_r04d", "overlap_share_vs_r04c", "entry_price_rel_diff_p95"}, "reconstruction_columns", recon_path)
    _add(rows, "pool_reconstruction_passed", not recon.empty and recon["reconciliation_status"].eq("passed").all(), "fatal", "reconstruction failed", relpath(recon_path))

    matrix_cols = {"policy_id", "policy_family_id", "hold_rule_id", "hold_rule_max_days", "exit_rule_family_id", "sizing_rule_id", "parameter_set_id", "parameter_values_json", "is_train_selectable", "is_validation_selectable", "invalid_policy_reason", "duplicate_policy_group_id", "canonical_policy_id", "formula_hash"}
    _require_columns(rows, matrix, matrix_cols, "policy_matrix_columns", matrix_path)
    _add(rows, "policy_matrix_formula_hash_complete", "formula_hash" in matrix.columns and matrix["formula_hash"].astype(str).str.len().ge(32).all(), "error", "matrix formula_hash incomplete", relpath(matrix_path))
    _add(rows, "forbidden_policy_families_absent", not set(matrix.get("exit_rule_family_id", pd.Series(dtype=str)).astype(str)).intersection(FORBIDDEN_FAMILIES), "error", "forbidden families present", relpath(matrix_path))
    if "invalid_policy_reason" in matrix.columns:
        selectable_invalid = matrix[matrix["is_train_selectable"].map(_to_bool) & matrix["invalid_policy_reason"].fillna("").ne("")]
        _add(rows, "invalid_rows_not_train_selectable", selectable_invalid.empty, "error", "invalid rows train selectable", relpath(matrix_path))
    if {"duplicate_policy_group_id", "canonical_policy_id", "policy_id", "is_train_selectable"}.issubset(matrix.columns):
        noncanon = matrix[matrix["duplicate_policy_group_id"].fillna("").ne("") & matrix["canonical_policy_id"].fillna("").ne(matrix["policy_id"].fillna(""))]
        _add(rows, "duplicate_noncanonical_not_train_selectable", not noncanon["is_train_selectable"].map(_to_bool).any(), "error", "duplicate noncanonical selectable", relpath(matrix_path))

    summary_cols = {
        "policy_id",
        "split",
        "replay_complete_count",
        "censored_share",
        "net_return_mean",
        "unweighted_net_return_mean",
        "weighted_net_return_mean",
        "loss_le_minus5_rate",
        "max_gain50_count",
        "max_gain50_retention_vs_volume_money_hold120",
        "net_return_mean_delta_vs_volume_money_hold120",
        "p10_delta_vs_volume_money_hold120",
        "loss_le_minus5_delta_vs_volume_money_hold120",
        "net_return_mean_delta_vs_matched_baseline_A",
        "net_return_metric_basis",
        "denominator_status",
    }
    _require_columns(rows, summary, summary_cols, "summary_columns", summary_path)
    _add(rows, "summary_metric_basis_weighted", "net_return_metric_basis" in summary.columns and summary["net_return_metric_basis"].eq("weighted_net_return").all(), "error", "summary metric basis mismatch", relpath(summary_path))

    _require_columns(rows, matched, {"policy_id", "split", "volume_money_replay_complete_count", "matched_baseline_replay_complete_count", "matched_comparator_effective_sample_size", "net_return_mean_delta_vs_matched_baseline_A", "matched_comparator_status"}, "matched_summary_columns", matched_path)
    _add(rows, "matched_same_policy_summary_nonempty", not matched.empty, "error", "matched summary empty", relpath(matched_path))

    _require_columns(rows, replay, {"r04d_event_id", "replay_universe", "event_weight", "policy_id", "split", "replay_status", "replay_complete", "unweighted_net_return", "weighted_net_return", "net_return_metric_basis"}, "replay_columns", replay_path)
    _add(rows, "replay_has_both_universes", {"volume_money", "matched_baseline_A"}.issubset(set(replay["replay_universe"].astype(str))), "error", "missing replay universe", relpath(replay_path))
    _add(rows, "replay_metric_basis_weighted", replay["net_return_metric_basis"].dropna().eq("weighted_net_return").all(), "error", "replay metric basis mismatch", relpath(replay_path))

    _require_columns(rows, selection, {"selection_stage", "split_used", "candidate_policy_id", "selected_flag"}, "selection_trace_columns", selection_path)
    _add(rows, "selection_trace_no_robustness", not selection.get("split_used", pd.Series(dtype=str)).astype(str).eq("robustness").any(), "error", "robustness used in selection", relpath(selection_path))

    _require_columns(rows, validation_gate, {"policy_id", "validation_gate_pass", "validation_selected_rank", "selected_policy_id", "selected_flag", "failed_gate_list"}, "validation_gate_columns", validation_gate_path)
    selected_rows = validation_gate[validation_gate.get("selected_flag", pd.Series(dtype=bool)).map(_to_bool)] if not validation_gate.empty else pd.DataFrame()
    final_decision = final.iloc[0]["final_decision"] if not final.empty else ""
    if final_decision != "r04d_no_policy_passed_validation":
        _add(rows, "unique_validation_selected_policy", len(selected_rows) == 1, "error", "selected policy must be unique", relpath(validation_gate_path))
        if len(selected_rows) == 1:
            _add(rows, "selected_policy_validation_gate_passed", _to_bool(selected_rows.iloc[0]["validation_gate_pass"]), "error", "selected policy did not pass validation", relpath(validation_gate_path))

    _require_columns(rows, final, {"final_decision", "selected_policy_id", "validation_gate_pass", "robustness_gate_pass", "robustness_relative_improvement_status", "net_return_metric_basis", "decision_reason"}, "final_decision_columns", final_path)
    _add(rows, "final_decision_allowed", not final.empty and final_decision in FINAL_DECISIONS, "error", str(final_decision), relpath(final_path))
    _add(rows, "final_decision_matches_manifest", final_decision == manifest.get("final_decision"), "error", "manifest/final CSV mismatch", relpath(final_path))
    _add(rows, "passed_decision_requires_robustness_gate", final_decision not in {"r04d_policy_passed_relative_improvement_diagnostic_only", "r04d_policy_strong_pass_diagnostic_only"} or (not final.empty and _to_bool(final.iloc[0]["robustness_gate_pass"])), "error", "passed decision without robustness gate", relpath(final_path))

    if final_decision != "r04d_no_policy_passed_validation" and not robustness.empty:
        _add(rows, "robustness_readout_single_selected_policy", robustness["policy_id"].nunique() == 1 and robustness.iloc[0]["policy_id"] == final.iloc[0]["selected_policy_id"], "error", "robustness changed selected policy", relpath(robustness_path))
        if _to_bool(final.iloc[0]["robustness_gate_pass"]):
            _add(rows, "robustness_censored_gate_passed", float(final.iloc[0]["robustness_censored_share"]) <= float(config["thresholds"]["max_robustness_censored_share"]), "error", "robustness censored gate failed", relpath(final_path))

    for required in config["validation"]["required_boundary_strings"]:
        _add(rows, f"report_boundary_{required[:32]}", required in report_text, "error", "boundary string missing", relpath(report_path))
    for forbidden in ["production ready", "R04c passed\n", "entry rule approved", "CTA strategy passed"]:
        if forbidden == "R04c passed\n":
            condition = "R04c passed\n" not in report_text
        else:
            condition = forbidden not in report_text
        _add(rows, f"report_forbidden_absent_{forbidden[:24]}", condition, "error", "forbidden language present", relpath(report_path))

    status = _status(rows)
    failed = [row["check_name"] for row in rows if row["status"] == "failed" and row["severity"] in {"fatal", "error"}]
    reports_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(audit_path, index=False)
    result = {
        "validation_status": status,
        "final_decision": final_decision,
        "failed_checks": failed,
        "check_count": len(rows),
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
    print(json.dumps({"validation_status": result["validation_status"], "failed_checks": result["failed_checks"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
