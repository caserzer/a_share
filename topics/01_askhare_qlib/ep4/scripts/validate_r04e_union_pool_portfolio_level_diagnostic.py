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
from pandas.errors import EmptyDataError
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04e_union_pool_portfolio_level_diagnostic_v1.yaml"
FINAL_DECISIONS = {
    "r04e_union_portfolio_strong_lead",
    "r04e_union_portfolio_conditional_lead",
    "r04e_union_validation_positive_but_robustness_mixed",
    "r04e_union_validation_positive_but_robustness_failed",
    "r04e_union_not_viable_validation",
    "r04e_long_only_validation_ceiling_suspected",
    "r04e_blocked_upstream_validation_failed",
    "r04e_blocked_upstream_state_changed",
    "r04e_blocked_missing_required_input",
    "r04e_blocked_validation_failed",
}
REQUIRED_REPORTS = [
    "r04e_source_pool_reconciliation.csv",
    "r04e_union_event_overlap_audit.csv",
    "r04e_same_instrument_nearby_event_audit.csv",
    "r04e_pseudo_diversification_audit.csv",
    "r04e_daily_candidate_count_audit.csv",
    "r04e_union_hold120_readiness.csv",
    "r04e_policy_matrix_frozen.csv",
    "r04e_event_policy_replay_summary.csv",
    "r04e_portfolio_policy_summary.csv",
    "r04e_portfolio_monthly_summary.csv",
    "r04e_family_contribution_decomposition.csv",
    "r04e_baseline_A_portfolio_comparison.csv",
    "r04e_matched_baseline_reconstruction_audit.csv",
    "r04e_gate_audit.csv",
    "r04e_final_decision.csv",
    "r04e_union_pool_portfolio_level_final_report.md",
]
REQUIRED_CACHE = [
    "r04e_source_pool_event_panel.parquet",
    "r04e_union_event_panel.parquet",
    "r04e_event_policy_path_panel.parquet",
    "r04e_portfolio_daily_return_panel.parquet",
    "r04e_baseline_A_portfolio_daily_return_panel.parquet",
    "r04e_matched_baseline_event_replay_panel.parquet",
]
FORBIDDEN_POLICY_TOKENS = ("ATR", "EMA", "CTA", "profit_lock", "market_state_gate", "industry_state_gate")
FORBIDDEN_REPORT_STRINGS = ("production ready", "deployable strategy", "entry rule approved", "CTA strategy passed")


def _load_config(path: Path) -> dict[str, Any]:
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


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _add(rows: list[dict[str, Any]], check_id: str, name: str, condition: bool, severity: str = "error", details: str = "") -> None:
    rows.append(
        {
            "check_id": check_id,
            "check_name": name,
            "status": "passed" if condition else "failed",
            "severity": severity,
            "details": "" if condition else details,
        }
    )


def _status(rows: list[dict[str, Any]]) -> str:
    audit = pd.DataFrame(rows)
    failed = audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"])
    return "failed" if bool(failed.any()) else "passed"


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], check_id: str, path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, check_id, f"{path.name}_columns", not missing, "error", f"missing columns: {missing}")


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r04e_union_pool_portfolio_level_manifest.json"
    validation_path = manifests_dir / "r04e_union_pool_portfolio_level_validation.json"
    audit_path = reports_dir / "r04e_union_pool_portfolio_level_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    required_inputs = [
        config["upstream_r04c"]["validation"],
        config["upstream_r04c"]["manifest"],
        config["upstream_r04c"]["final_decision"],
        config["upstream_r04c"]["pool_event_panel"],
        config["upstream_r04d"]["validation"],
        config["upstream_r04d"]["final_decision"],
        config["upstream_r04b"]["validation"],
        config["upstream_r02_family_precision"]["action_time_panel"],
        config["price_provider"]["calendar_source_path"],
        config["price_provider"]["instrument_source_path"],
    ]
    for idx, path in enumerate(required_inputs, start=1):
        _add(rows, f"C{idx:02d}", f"required_input_exists_{Path(path).name}", topic_path(path).exists(), "fatal", path)

    r04c_val = _read_json(config["upstream_r04c"]["validation"])
    r04d_val = _read_json(config["upstream_r04d"]["validation"])
    r04b_val = _read_json(config["upstream_r04b"]["validation"])
    r04c_final = _read_csv(topic_path(config["upstream_r04c"]["final_decision"]))
    r04d_final = _read_csv(topic_path(config["upstream_r04d"]["final_decision"]))
    _add(rows, "C11", "r04c_validation_passed", r04c_val.get("validation_status") == "passed", "fatal", str(r04c_val.get("validation_status")))
    _add(rows, "C12", "r04c_final_decision_frozen", not r04c_final.empty and str(r04c_final.iloc[0].get("final_decision", "")) == "r04c_no_candidate_pool_passed_validation", "fatal", str(r04c_final.iloc[0].get("final_decision", "")) if not r04c_final.empty else "missing")
    _add(rows, "C13", "r04d_validation_passed", r04d_val.get("validation_status") == "passed", "fatal", str(r04d_val.get("validation_status")))
    _add(rows, "C14", "r04d_final_decision_frozen", not r04d_final.empty and str(r04d_final.iloc[0].get("final_decision", "")) == "r04d_no_policy_passed_validation", "fatal", str(r04d_final.iloc[0].get("final_decision", "")) if not r04d_final.empty else "missing")
    _add(rows, "C15", "r04b_validation_passed", r04b_val.get("validation_status") == "passed", "fatal", str(r04b_val.get("validation_status")))

    for name in REQUIRED_REPORTS:
        _add(rows, f"R_{name}", f"required_report_exists_{name}", (reports_dir / name).exists(), "fatal", relpath(reports_dir / name))
    for name in REQUIRED_CACHE:
        _add(rows, f"K_{name}", f"required_cache_exists_{name}", (cache_dir / name).exists(), "fatal", relpath(cache_dir / name))
    _add(rows, "M01", "required_manifest_exists", manifest_path.exists(), "fatal", relpath(manifest_path))

    if not manifest_path.exists() or not all((reports_dir / name).exists() for name in REQUIRED_REPORTS) or not all((cache_dir / name).exists() for name in REQUIRED_CACHE):
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {
            "validation_status": _status(rows),
            "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] in {"fatal", "error"}],
            "warning_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] == "warning"],
            "final_decision": "r04e_blocked_validation_failed",
            "selected_portfolio_policy_id": None,
            "gate0_status": "",
            "gate0_stop_category": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audit_path": relpath(audit_path),
        }
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    source = pd.read_parquet(cache_dir / "r04e_source_pool_event_panel.parquet")
    union = pd.read_parquet(cache_dir / "r04e_union_event_panel.parquet")
    path = pd.read_parquet(cache_dir / "r04e_event_policy_path_panel.parquet", columns=["r04e_event_id", "policy_id", "split", "trade_date", "daily_net_return", "source_family_set", "source_family_count"])
    portfolio_daily = pd.read_parquet(cache_dir / "r04e_portfolio_daily_return_panel.parquet")
    baseline_daily = pd.read_parquet(cache_dir / "r04e_baseline_A_portfolio_daily_return_panel.parquet")
    matched_replay = pd.read_parquet(cache_dir / "r04e_matched_baseline_event_replay_panel.parquet")
    recon = _read_csv(reports_dir / "r04e_source_pool_reconciliation.csv")
    nearby = _read_csv(reports_dir / "r04e_same_instrument_nearby_event_audit.csv")
    pseudo = _read_csv(reports_dir / "r04e_pseudo_diversification_audit.csv")
    policy = _read_csv(reports_dir / "r04e_policy_matrix_frozen.csv")
    event_summary = _read_csv(reports_dir / "r04e_event_policy_replay_summary.csv")
    portfolio = _read_csv(reports_dir / "r04e_portfolio_policy_summary.csv")
    comparison = _read_csv(reports_dir / "r04e_baseline_A_portfolio_comparison.csv")
    matched_audit = _read_csv(reports_dir / "r04e_matched_baseline_reconstruction_audit.csv")
    gate = _read_csv(reports_dir / "r04e_gate_audit.csv")
    final = _read_csv(reports_dir / "r04e_final_decision.csv")
    report_text = (reports_dir / "r04e_union_pool_portfolio_level_final_report.md").read_text(encoding="utf-8")

    _require_columns(rows, source, {"source_family_id", "pool_id", "source_pool_event_id", "entry_execution_date", "entry_resolution_status", "source_membership_authority"}, "C16", cache_dir / "r04e_source_pool_event_panel.parquet")
    _require_columns(rows, union, {"union_event_key", "instrument_id", "entry_execution_date", "source_family_set", "source_family_count", "membership_filter_text"}, "C17", cache_dir / "r04e_union_event_panel.parquet")
    _require_columns(rows, nearby, {"nearby_window_trading_days", "same_instrument_nearby_source_event_count", "same_instrument_nearby_union_event_count", "nearby_event_status"}, "C18", reports_dir / "r04e_same_instrument_nearby_event_audit.csv")
    _require_columns(rows, policy, {"policy_id", "hold_rule_id", "hold_rule_max_days", "exit_rule_family_id", "parameter_values_json", "formula_hash"}, "C19", reports_dir / "r04e_policy_matrix_frozen.csv")
    _require_columns(rows, event_summary, {"policy_id", "split", "pool_id", "policy_max_gain50_retention_rate_vs_hold120_no_exit", "matched_comparator_status", "net_return_mean_delta_vs_matched_baseline_A"}, "C20", reports_dir / "r04e_event_policy_replay_summary.csv")
    _require_columns(rows, portfolio, {"portfolio_id", "policy_id", "split", "period_compounded_return", "monthly_return_p10", "max_drawdown", "active_count_p95"}, "C21", reports_dir / "r04e_portfolio_policy_summary.csv")
    _require_columns(rows, comparison, {"portfolio_monthly_p10_delta_vs_baseline_A", "portfolio_max_drawdown_delta_vs_baseline_A", "portfolio_worst_20d_delta_vs_baseline_A"}, "C22", reports_dir / "r04e_baseline_A_portfolio_comparison.csv")
    _require_columns(rows, matched_audit, {"fallback_level", "fallback_level_share", "matched_comparator_effective_sample_size", "matched_comparator_status"}, "C23", reports_dir / "r04e_matched_baseline_reconstruction_audit.csv")
    _require_columns(rows, gate, {"gate0_status", "readiness_failure_reason", "gate0_stop_category"}, "C24", reports_dir / "r04e_gate_audit.csv")
    _require_columns(rows, final, {"final_decision", "selected_portfolio_policy_id", "gate0_status", "gate0_stop_category"}, "C25", reports_dir / "r04e_final_decision.csv")

    expected_families = {"volume_money", "range_breakout", "pullback_drawdown"}
    _add(rows, "C26", "source_family_set_exact", set(source.get("source_family_id", pd.Series(dtype=str)).dropna().astype(str).unique()) == expected_families, "error", str(set(source.get("source_family_id", pd.Series(dtype=str)).dropna().astype(str).unique())))
    _add(rows, "C27", "reconciliation_overlap_passed", not recon.empty and recon["reconciliation_status"].eq("passed").all() and pd.to_numeric(recon["overlap_share_vs_r04c"], errors="coerce").ge(0.99).all(), "error", relpath(reports_dir / "r04e_source_pool_reconciliation.csv"))
    _add(rows, "C28", "union_event_key_unique", "union_event_key" in union.columns and union["union_event_key"].is_unique, "error", "duplicate union_event_key")
    _add(rows, "C29", "nearby_window_frozen_20", not nearby.empty and pd.to_numeric(nearby["nearby_window_trading_days"], errors="coerce").eq(20).all(), "error", "nearby window must be 20")
    _add(rows, "C30", "source_family_count_diagnostic_only", "source_family_count" in union.columns and "source_family_count" in path.columns and not union.get("membership_filter_text", pd.Series(dtype=str)).astype(str).str.contains("source_family_count", regex=False).any(), "error", "source_family_count used in membership text")
    _add(rows, "C31", "no_market_industry_rps_gate_in_membership", union.get("membership_filter_text", pd.Series(dtype=str)).astype(str).eq("fixed_source_families_only_no_market_industry_rps_gate").all(), "error", "membership filter text changed")
    allowed_exits = {"no_exit", "break_even_after_gain", "fixed_stop"}
    _add(rows, "C32", "policy_matrix_allowed_v1_exits", set(policy.get("exit_rule_family_id", pd.Series(dtype=str)).astype(str).unique()).issubset(allowed_exits), "error", str(set(policy.get("exit_rule_family_id", pd.Series(dtype=str)).astype(str).unique())))
    forbidden_present = any(policy.astype(str).apply(lambda col: col.str.contains(token, case=False, regex=False)).any().any() for token in FORBIDDEN_POLICY_TOKENS)
    _add(rows, "C33", "forbidden_policy_families_absent", not forbidden_present, "error", "forbidden policy token present")
    _add(rows, "C34", "event_replay_execution_semantics", config["execution"]["execution_policy"] == "close_signal_next_open", "error", str(config["execution"].get("execution_policy")))
    _add(rows, "C35", "cost_model_default", config["cost_model"].get("cost_model_id") == "a_share_daily_replay_default_v1", "error", str(config["cost_model"]))
    _add(rows, "C36", "matched_baseline_rebuilt_after_union", not matched_audit.empty and set(matched_audit["fallback_level"].dropna().astype(str)).intersection({"split+entry_calendar_year+entry_calendar_quarter+market_regime_bucket+industry_regime_bucket", "split+entry_calendar_year+market_regime_bucket+industry_regime_bucket", "split+entry_calendar_year+market_regime_bucket", "split+entry_calendar_year"}), "error", "fallback levels missing")
    _add(rows, "C37", "matched_replay_same_policy_present", not matched_replay.empty and {"policy_id", "event_weight", "net_return"}.issubset(matched_replay.columns), "error", "matched replay missing same-policy rows")
    _add(rows, "C38", "baseline_portfolio_same_construction_present", not baseline_daily.empty and set(baseline_daily.get("portfolio_weighting_id", pd.Series(dtype=str)).astype(str).unique()) >= {"active_equal_weight", "family_balanced_active_equal_weight"}, "error", "baseline daily missing portfolio construction")
    _add(rows, "C39", "primary_portfolio_gross_exposure_lte_one", pd.to_numeric(portfolio_daily.get("gross_exposure", pd.Series(dtype=float)), errors="coerce").fillna(0).le(1.0000001).all(), "error", "gross exposure > 1")
    _add(rows, "C40", "right_tail_gate_uses_retention_metric", "policy_max_gain50_retention_rate_vs_hold120_no_exit" in event_summary.columns and "policy_max_gain50_retention_rate_vs_hold120_no_exit" in report_text, "error", "retention metric missing")
    selected_id = "" if final.empty else str(final.iloc[0].get("selected_portfolio_policy_id", ""))
    _add(rows, "C41", "active_cap_not_primary_selected", "cap" not in selected_id, "error", selected_id)
    _add(rows, "C42", "gate0_audit_has_reasons", {"readiness_failure_reason", "gate0_stop_category"}.issubset(gate.columns), "error", "gate audit missing reason/category")
    _add(rows, "C43", "robustness_not_selection_source", "robustness" not in selected_id.lower(), "error", selected_id)
    final_decision = "" if final.empty else str(final.iloc[0].get("final_decision", ""))
    _add(rows, "C44", "final_decision_allowed", final_decision in FINAL_DECISIONS, "error", final_decision)
    for idx, text in enumerate(config["validation"]["required_boundary_strings"], start=45):
        _add(rows, f"C{idx}", f"report_contains_boundary_{idx}", text in report_text, "error", text)
    forbidden_report = [text for text in FORBIDDEN_REPORT_STRINGS if text.lower() in report_text.lower()]
    _add(rows, "C51", "report_forbidden_production_language_absent", not forbidden_report, "error", str(forbidden_report))
    required_manifest_keys = {
        "requirement_id",
        "config_hash",
        "runner_hash",
        "validator_hash",
        "upstream_r04c_manifest_hash",
        "upstream_r04d_manifest_hash",
        "upstream_r04b_manifest_hash",
        "r02_family_action_time_panel_hash",
        "price_provider_hash",
        "cost_model_id",
        "source_pool_ids",
        "union_pool_id",
        "policy_matrix_hash",
        "portfolio_weighting_matrix_hash",
        "split_definition_hash",
        "artifact_hashes",
        "created_at",
    }
    _add(rows, "C52", "manifest_required_keys_present", required_manifest_keys.issubset(manifest.keys()), "error", str(sorted(required_manifest_keys - set(manifest.keys()))))
    artifact_hashes = manifest.get("artifact_hashes", {})
    _add(rows, "C53", "manifest_hashes_for_required_artifacts", isinstance(artifact_hashes, dict) and all(relpath(reports_dir / name) in artifact_hashes for name in REQUIRED_REPORTS if name.endswith(".csv")) and all(relpath(cache_dir / name) in artifact_hashes for name in REQUIRED_CACHE), "error", "missing artifact hashes")

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    validation_status = _status(rows)
    result = {
        "validation_status": validation_status,
        "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] in {"fatal", "error"}],
        "warning_checks": [r["check_name"] for r in rows if r["status"] == "failed" and r["severity"] == "warning"],
        "final_decision": final_decision if validation_status == "passed" else "r04e_blocked_validation_failed",
        "selected_portfolio_policy_id": None if not selected_id or selected_id == "nan" else selected_id,
        "gate0_status": "" if gate.empty else str(gate.iloc[0].get("gate0_status", "")),
        "gate0_stop_category": "" if gate.empty else str(gate.iloc[0].get("gate0_stop_category", "")),
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
