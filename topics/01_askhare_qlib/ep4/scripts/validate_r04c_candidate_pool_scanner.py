#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04c_candidate_pool_scanner_v1.yaml"
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_price_materialization_mismatch",
    "blocked_pool_definition_invalid",
    "blocked_selection_leakage_detected",
    "r04c_no_candidate_pool_passed_validation",
    "r04c_candidate_pool_not_robust_scanner_complete",
    "r04c_candidate_pool_passed_diagnostic_only",
}
PROMOTABLE_ADAPTERS = {
    "r04_deterministic_auxiliary",
    "r02_family_precision_frozen_family_occurrence",
    "r03c_config_frozen_family_set_pool",
}
REPORTS = [
    "r04c_source_readiness_audit.csv",
    "r04c_pool_registry_frozen.csv",
    "r04c_pool_definition_leakage_audit.csv",
    "r04c_pool_membership_waterfall.csv",
    "r04c_hold120_pool_profile.csv",
    "r04c_global_baseline_delta_summary.csv",
    "r04c_matched_baseline_delta_summary.csv",
    "r04c_train_pool_selection_trace.csv",
    "r04c_validation_gate_audit.csv",
    "r04c_robustness_readout.csv",
    "r04c_concentration_audit.csv",
    "r04c_overlap_uniqueness_audit.csv",
    "r04c_source_family_comparison.csv",
    "r04c_rejected_descriptive_leads.csv",
    "r04c_final_decision.csv",
    "r04c_candidate_pool_scanner_final_report.md",
]
CACHE = [
    "r04c_pool_event_panel.parquet",
    "r04c_hold120_replay_panel.parquet",
    "r04c_matched_baseline_panel.parquet",
    "r04c_pool_selection_panel.parquet",
]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _hash_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


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


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], name: str, path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, name, not missing, "error", f"missing columns: {missing}", relpath(path))


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r04c_candidate_pool_scanner_manifest.json"
    validation_path = manifests_dir / "r04c_candidate_pool_scanner_validation.json"
    audit_path = reports_dir / "r04c_candidate_pool_scanner_validation_audit.csv"
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
    upstream_r04 = _read_json(Path(config["upstream_r04"]["validation"]))
    upstream_r04b = _read_json(Path(config["upstream_r04b"]["validation"]))
    _add(rows, "upstream_r04_validation_passed", upstream_r04.get("validation_status") == "passed", "fatal", f"status={upstream_r04.get('validation_status')}")
    _add(rows, "upstream_r04b_validation_passed", upstream_r04b.get("validation_status") == "passed", "fatal", f"status={upstream_r04b.get('validation_status')}")
    _add(rows, "final_decision_allowed", manifest.get("final_decision") in FINAL_DECISIONS, "error", str(manifest.get("final_decision")))
    _add(rows, "manifest_has_price_source_hash", bool(manifest.get("price_source_hash")), "error", "missing price_source_hash")
    _add(rows, "manifest_has_calendar_hash", bool(manifest.get("calendar_source_hash")), "error", "missing calendar_source_hash")
    _add(rows, "manifest_price_materialization_semantics_r04b", "R04b" in str(manifest.get("price_materialization_semantics", "")), "error", "missing R04b price materialization semantics")

    required_paths = [reports_dir / name for name in REPORTS] + [cache_dir / name for name in CACHE]
    if not all(path.exists() for path in required_paths):
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": _status(rows), "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed"], "audit_path": relpath(audit_path), "manifest_path": relpath(manifest_path)}
        write_json(result, validation_path)
        return result

    registry_path = reports_dir / "r04c_pool_registry_frozen.csv"
    profile_path = reports_dir / "r04c_hold120_pool_profile.csv"
    matched_path = reports_dir / "r04c_matched_baseline_delta_summary.csv"
    train_path = reports_dir / "r04c_train_pool_selection_trace.csv"
    validation_gate_path = reports_dir / "r04c_validation_gate_audit.csv"
    robustness_path = reports_dir / "r04c_robustness_readout.csv"
    final_path = reports_dir / "r04c_final_decision.csv"
    report_path = reports_dir / "r04c_candidate_pool_scanner_final_report.md"
    event_path = cache_dir / "r04c_pool_event_panel.parquet"
    replay_path = cache_dir / "r04c_hold120_replay_panel.parquet"
    selection_panel_path = cache_dir / "r04c_pool_selection_panel.parquet"

    registry = _read_csv(registry_path)
    profile = _read_csv(profile_path)
    matched = _read_csv(matched_path)
    train = _read_csv(train_path)
    validation_gate = _read_csv(validation_gate_path)
    robustness = _read_csv(robustness_path)
    final = _read_csv(final_path)
    events = pd.read_parquet(event_path)
    replay = pd.read_parquet(replay_path)
    selection_panel = pd.read_parquet(selection_panel_path)
    report_text = report_path.read_text(encoding="utf-8")

    _require_columns(
        rows,
        registry,
        {"pool_id", "adapter_id", "membership_rule_hash", "field_source_map_hash", "pool_promotability_status", "leakage_risk_class", "selection_stage_allowed"},
        "registry_columns",
        registry_path,
    )
    _add(rows, "registry_pool_id_unique", "pool_id" in registry.columns and registry["pool_id"].notna().all() and registry["pool_id"].is_unique, "error", "pool_id must be unique/non-null", relpath(registry_path))
    _add(rows, "registry_hashes_complete", {"membership_rule_hash", "field_source_map_hash"}.issubset(registry.columns) and registry["membership_rule_hash"].astype(str).str.len().ge(32).all() and registry["field_source_map_hash"].astype(str).str.len().ge(32).all(), "error", "registry hashes incomplete", relpath(registry_path))
    promotable = registry[registry["pool_promotability_status"].eq("promotable")]
    _add(rows, "promotable_no_known_oos_leakage", promotable.empty or promotable["leakage_risk_class"].eq("no_known_oos_leakage").all(), "error", "promotable pool leakage risk not clean", relpath(registry_path))
    _add(rows, "r01_r02_winner_anchored_descriptive_only", not registry["adapter_id"].isin(["r01_pre60_indicator_search_v2", "r01_post30_indicator_search_v1", "r02_winner_anchored_v2"]).any(), "error", "winner anchored adapter should not be promotable in v1", relpath(registry_path))
    _add(rows, "r03c_default_columns_frozen", config["r03c_adapter"]["r03c_pooling_key_column"] == "pooling_key" and config["r03c_adapter"]["r03c_anchor_signal_date_column"] == "step_signal_date", "error", "R03c key/anchor defaults changed")
    _add(rows, "r04_field_source_map_present", set(["stock_rps_60d", "stock_rps_minus_industry_rps_60d", "money_rank_20d", "industry_rps_60d"]).issubset(config.get("r04_derived_field_source_map", {})), "error", "missing R04 derived field map")

    _require_columns(rows, profile, {"pool_id", "adapter_id", "split", "replay_complete_count", "censored_share", "net_return_mean", "loss_le_minus5_rate", "max_gain50_count", "max_gain50_rate", "top1_calendar_year_share", "top1_instrument_share", "pool_denominator_status"}, "profile_columns", profile_path)
    _require_columns(rows, matched, {"pool_id", "split", "matched_comparator_status", "matched_comparator_effective_sample_size", "net_return_mean_delta_vs_matched_baseline_A", "p10_delta_vs_matched_baseline_A", "loss_le_minus5_delta_vs_matched_baseline_A", "matched_baseline_top1_calendar_year_share", "matched_baseline_top1_instrument_share"}, "matched_columns", matched_path)
    _require_columns(rows, final, {"final_decision", "selected_candidate_pool_id", "selected_adapter_id", "validation_gate_pass", "robustness_gate_pass", "validation_selected_rank", "decision_reason"}, "final_decision_columns", final_path)
    _require_columns(rows, events, {"pool_event_id", "pool_id", "adapter_id", "instrument_id", "anchor_signal_date", "entry_execution_date", "entry_resolution_status"}, "event_panel_columns", event_path)
    _require_columns(rows, replay, {"pool_event_id", "pool_id", "adapter_id", "split", "replay_status", "replay_complete", "net_return", "max_gain50_flag"}, "replay_panel_columns", replay_path)

    selected_pool = ""
    selected_adapter = ""
    decision = ""
    if not final.empty:
        decision = str(final.iloc[0]["final_decision"])
        selected_pool = "" if pd.isna(final.iloc[0].get("selected_candidate_pool_id", "")) else str(final.iloc[0].get("selected_candidate_pool_id", ""))
        selected_adapter = "" if pd.isna(final.iloc[0].get("selected_adapter_id", "")) else str(final.iloc[0].get("selected_adapter_id", ""))
    _add(rows, "final_decision_csv_matches_manifest", decision == manifest.get("final_decision"), "error", "final decision mismatch", relpath(final_path))
    if selected_pool:
        _add(rows, "selected_adapter_promotable_v1", selected_adapter in PROMOTABLE_ADAPTERS, "error", f"selected_adapter={selected_adapter}", relpath(final_path))
        selected_reg = registry[registry["pool_id"].eq(selected_pool)]
        _add(rows, "selected_pool_registry_promotable", not selected_reg.empty and selected_reg.iloc[0]["pool_promotability_status"] == "promotable", "error", "selected pool not promotable", relpath(registry_path))
        selected_matched = matched[matched["pool_id"].eq(selected_pool)]
        _add(rows, "selected_pool_matched_sufficient", not selected_matched.empty and selected_matched["matched_comparator_status"].eq("sufficient").all(), "error", "selected matched comparator insufficient", relpath(matched_path))

    if not train.empty:
        _add(rows, "train_selection_trace_train_only", "split_used" in train.columns and train["split_used"].astype(str).eq("train").all(), "error", "train trace used non-train split", relpath(train_path))
    if not validation_gate.empty:
        _add(rows, "validation_inputs_train_selected", "pool_id" in selection_panel.columns and set(validation_gate["pool_id"]).issubset(set(selection_panel.loc[selection_panel["train_selected_flag"].map(_to_bool), "pool_id"])), "error", "validation pool not train-selected", relpath(validation_gate_path))
        selected_rows = validation_gate[validation_gate.get("selected_flag", pd.Series(False, index=validation_gate.index)).map(_to_bool)]
        if selected_pool:
            _add(rows, "validation_freezes_unique_selected", len(selected_rows) == 1 and str(selected_rows.iloc[0]["pool_id"]) == selected_pool, "error", "validation did not freeze unique selected pool", relpath(validation_gate_path))
            _add(rows, "validation_selected_rank_one", "validation_selected_rank" in selected_rows.columns and int(selected_rows.iloc[0]["validation_selected_rank"]) == 1, "error", "selected rank is not 1", relpath(validation_gate_path))
        else:
            _add(rows, "validation_no_selected_when_no_pool", selected_rows.empty, "error", "selected row exists despite empty selected pool", relpath(validation_gate_path))
    if not robustness.empty and selected_pool:
        _add(rows, "robustness_only_selected_pool", set(robustness["pool_id"].astype(str)) == {selected_pool}, "error", "robustness readout changed selected pool", relpath(robustness_path))
    if decision == "r04c_candidate_pool_passed_diagnostic_only":
        _add(rows, "passed_decision_has_robustness_pass", not final.empty and bool(_to_bool(final.iloc[0]["robustness_gate_pass"])), "error", "passed decision without robustness gate pass", relpath(final_path))
    if decision == "r04c_candidate_pool_not_robust_scanner_complete":
        _add(rows, "not_robust_decision_not_passed", final.empty or not bool(_to_bool(final.iloc[0]["robustness_gate_pass"])), "error", "not robust decision has robustness pass", relpath(final_path))

    bad_selected = set(matched.loc[matched["matched_comparator_status"].ne("sufficient"), "pool_id"]) & {selected_pool}
    _add(rows, "matched_insufficient_not_selected", not bad_selected, "error", f"selected insufficient pools: {sorted(bad_selected)}", relpath(matched_path))
    if selected_pool:
        val_selected = validation_gate[validation_gate["pool_id"].astype(str).eq(selected_pool)]
        _add(rows, "validation_failed_not_selected", val_selected.empty or bool(_to_bool(val_selected.iloc[0].get("validation_gate_pass", False))), "error", "selected pool failed validation", relpath(validation_gate_path))
    _add(rows, "no_exit_policy_columns_used_for_selection", not any("exit_rule" in col or "policy_id" in col for col in selection_panel.columns), "error", "selection panel contains exit policy columns", relpath(selection_panel_path))
    for boundary in config["validation"]["required_boundary_strings"]:
        _add(rows, f"report_boundary_string_{boundary[:24]}", boundary in report_text, "error", "missing boundary string", relpath(report_path))

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    failed_checks = audit.loc[audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"]), "check_name"].tolist()
    result = {
        "validation_status": _status(rows),
        "check_count": int(len(rows)),
        "failed_checks": failed_checks,
        "audit_path": relpath(audit_path),
        "manifest_path": relpath(manifest_path),
        "final_decision": manifest.get("final_decision"),
    }
    write_json(result, validation_path)
    manifest = _read_json(manifest_path)
    artifact_hashes = dict(manifest.get("artifact_hashes", {}))
    for path in [*required_paths, audit_path, validation_path]:
        if path.exists() and path.is_file():
            artifact_hashes[relpath(path)] = _hash_file(path)
    manifest["artifact_hashes"] = artifact_hashes
    write_json(manifest, manifest_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = validate(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
