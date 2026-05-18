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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.yaml"
FINAL_DECISIONS = {
    "blocked_upstream_r04_validation_failed",
    "blocked_missing_required_input",
    "blocked_gate0_metric_replay_spec_failed",
    "blocked_policy_matrix_invalid",
    "blocked_selection_leakage_detected",
    "r04b_no_policy_family_passed_validation",
    "r04b_policy_not_robust_hold_exit_diagnostic_complete",
    "r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only",
}
REPORTS = [
    "r04b_gate0_metric_replay_spec_frozen.csv",
    "r04b_input_reconciliation_audit.csv",
    "r04b_policy_matrix_frozen.csv",
    "r04b_policy_replay_summary.csv",
    "r04b_policy_vs_hold120_summary.csv",
    "r04b_policy_selection_trace.csv",
    "r04b_winner_retention_audit.csv",
    "r04b_bad_path_compression_audit.csv",
    "r04b_censored_replay_audit.csv",
    "r04b_market_industry_interaction_audit.csv",
    "r04b_year_instrument_concentration_audit.csv",
    "r04b_cost_turnover_audit.csv",
    "r04b_legacy_metric_audit.csv",
    "r04b_final_decision.csv",
    "r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md",
]
CACHE = [
    "r04b_candidate_replay_base_panel.parquet",
    "r04b_daily_policy_path_panel.parquet",
    "r04b_policy_replay_panel.parquet",
    "r04b_policy_selection_panel.parquet",
    "r04b_subgroup_interaction_panel.parquet",
]


def _load_config(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


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


def _bool_series(values: pd.Series) -> pd.Series:
    return values.map(_to_bool).astype(bool)


def _require_columns(rows: list[dict[str, Any]], df: pd.DataFrame, cols: set[str], name: str, path: Path) -> None:
    missing = sorted(cols - set(df.columns))
    _add(rows, name, not missing, "error", f"missing columns: {missing}", relpath(path))


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    manifest_path = manifests_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json"
    validation_path = manifests_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json"
    audit_path = reports_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_validation_audit.csv"
    rows: list[dict[str, Any]] = []

    for name in REPORTS:
        _add(rows, f"required_report_exists_{name}", (reports_dir / name).exists(), "fatal", "required report missing", relpath(reports_dir / name))
    for name in CACHE:
        _add(rows, f"required_cache_exists_{name}", (cache_dir / name).exists(), "fatal", "required cache missing", relpath(cache_dir / name))
    _add(rows, "required_manifest_exists", manifest_path.exists(), "fatal", "manifest missing", relpath(manifest_path))

    if not manifest_path.exists():
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": "failed", "failed_checks": ["required_manifest_exists"], "audit_path": relpath(audit_path)}
        write_json(result, validation_path)
        return result

    manifest = _read_json(manifest_path)
    upstream = _read_json(Path(config["upstream_r04"]["validation"]))
    _add(rows, "upstream_r04_validation_passed", upstream.get("validation_status") == "passed", "fatal", f"status={upstream.get('validation_status')}")
    _add(rows, "final_decision_allowed", manifest.get("final_decision") in FINAL_DECISIONS, "error", str(manifest.get("final_decision")))
    _add(rows, "manifest_has_price_source_hash", bool(manifest.get("price_source_hash")), "error", "missing price_source_hash")
    _add(rows, "manifest_has_calendar_hash", bool(manifest.get("calendar_source_hash")), "error", "missing calendar_source_hash")
    _add(rows, "manifest_adjustment_policy_frozen", manifest.get("adjustment_policy") == config["price_provider"]["adjustment_policy"], "error", "adjustment policy mismatch")
    _add(rows, "manifest_cost_model_frozen", manifest.get("cost_model") == config["cost_model"], "error", "cost model mismatch")

    paths = {
        "gate0": reports_dir / "r04b_gate0_metric_replay_spec_frozen.csv",
        "input": reports_dir / "r04b_input_reconciliation_audit.csv",
        "matrix": reports_dir / "r04b_policy_matrix_frozen.csv",
        "summary": reports_dir / "r04b_policy_replay_summary.csv",
        "selection": reports_dir / "r04b_policy_selection_trace.csv",
        "winner": reports_dir / "r04b_winner_retention_audit.csv",
        "interaction": reports_dir / "r04b_market_industry_interaction_audit.csv",
        "final": reports_dir / "r04b_final_decision.csv",
        "report": reports_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md",
        "base": cache_dir / "r04b_candidate_replay_base_panel.parquet",
        "replay": cache_dir / "r04b_policy_replay_panel.parquet",
        "daily": cache_dir / "r04b_daily_policy_path_panel.parquet",
    }
    if not all(path.exists() for path in paths.values()):
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(audit_path, index=False)
        result = {"validation_status": _status(rows), "failed_checks": [r["check_name"] for r in rows if r["status"] == "failed"], "audit_path": relpath(audit_path)}
        write_json(result, validation_path)
        return result

    gate0 = pd.read_csv(paths["gate0"])
    input_audit = pd.read_csv(paths["input"])
    matrix = pd.read_csv(paths["matrix"])
    summary = pd.read_csv(paths["summary"])
    selection = pd.read_csv(paths["selection"])
    winner = pd.read_csv(paths["winner"])
    interaction = pd.read_csv(paths["interaction"])
    final = pd.read_csv(paths["final"])
    base = pd.read_parquet(paths["base"])
    replay = pd.read_parquet(paths["replay"])
    daily = pd.read_parquet(paths["daily"])
    report_text = paths["report"].read_text(encoding="utf-8")

    _require_columns(rows, gate0, {"spec_section", "spec_item", "frozen_value_json", "formula_text", "source_config_key", "formula_hash"}, "gate0_columns", paths["gate0"])
    _add(rows, "gate0_formula_hash_complete", "formula_hash" in gate0.columns and gate0["formula_hash"].astype(str).str.len().ge(32).all(), "error", "formula_hash incomplete", relpath(paths["gate0"]))
    required_sections = {"return", "cost", "sizing", "execution", "price_adjustment", "censored", "max_gain50_retention", "baseline_delta"}
    _add(rows, "gate0_required_sections_present", required_sections.issubset(set(gate0["spec_section"].astype(str))), "error", "missing required sections")

    _require_columns(
        rows,
        input_audit,
        {
            "split",
            "r04_candidate_rows",
            "included_rows",
            "valid_entry_rows",
            "policy_replay_eligible_rows",
            "excluded_entry_price_mismatch",
            "entry_price_rel_diff_p95",
            "entry_price_rel_diff_max",
        },
        "input_reconciliation_columns",
        paths["input"],
    )
    if {"excluded_entry_price_mismatch", "policy_replay_eligible_rows"}.issubset(input_audit.columns):
        mismatch_share = input_audit["excluded_entry_price_mismatch"] / input_audit["policy_replay_eligible_rows"].replace(0, np.nan)
        _add(
            rows,
            "entry_price_reconciliation_within_split_tolerance",
            bool((mismatch_share.fillna(0) <= float(config["candidate"]["max_split_entry_price_mismatch_share"])).all()),
            "error",
            "entry price mismatch share exceeded tolerance",
            relpath(paths["input"]),
        )

    matrix_cols = {
        "policy_id",
        "hold_rule_id",
        "exit_rule_id",
        "exit_rule_family_id",
        "sizing_rule_id",
        "policy_family_id",
        "parameter_set_id",
        "parameter_values_json",
        "is_train_selectable",
        "is_validation_selectable",
        "is_sensitivity_policy",
        "parameter_reference_group_id",
        "validation_family_reference_set_id",
        "selection_family_key",
        "invalid_policy_reason",
        "formula_hash",
    }
    _require_columns(rows, matrix, matrix_cols, "policy_matrix_columns", paths["matrix"])
    if matrix_cols.issubset(matrix.columns):
        expected_family = matrix["hold_rule_id"].astype(str) + "|" + matrix["exit_rule_family_id"].astype(str) + "|" + matrix["sizing_rule_id"].astype(str)
        _add(rows, "policy_family_id_formula", bool(matrix["policy_family_id"].astype(str).eq(expected_family).all()), "error", "policy_family_id formula mismatch", relpath(paths["matrix"]))
        _add(rows, "policy_formula_hash_complete", bool(matrix["formula_hash"].astype(str).str.len().ge(32).all()), "error", "formula_hash incomplete", relpath(paths["matrix"]))
        profit_invalid = matrix["invalid_policy_reason"].fillna("").eq("locked_gain_pct_ge_activation_gain_pct")
        train_selectable = _bool_series(matrix["is_train_selectable"])
        validation_selectable = _bool_series(matrix["is_validation_selectable"])
        sensitivity_policy = _bool_series(matrix["is_sensitivity_policy"])
        _add(
            rows,
            "profit_lock_invalid_not_selectable",
            bool((~profit_invalid | (~train_selectable & ~validation_selectable)).all()),
            "error",
            "invalid profit-lock policy selectable",
            relpath(paths["matrix"]),
        )
        time_invalid = matrix["invalid_policy_reason"].fillna("").eq("time_stop_days_ge_max_holding_days")
        _add(
            rows,
            "time_stop_invalid_not_selectable",
            bool((~time_invalid | (~train_selectable & ~validation_selectable)).all()),
            "error",
            "invalid time-stop policy selectable",
            relpath(paths["matrix"]),
        )
        atr_sensitivity = sensitivity_policy & matrix["exit_rule_family_id"].astype(str).eq("ATR_trailing")
        _add(
            rows,
            "activated_atr_sensitivity_not_selectable",
            bool((~atr_sensitivity | (~train_selectable & ~validation_selectable)).all()),
            "error",
            "ATR sensitivity policy selectable",
            relpath(paths["matrix"]),
        )

    summary_cols = {
        "policy_id",
        "policy_family_id",
        "exit_rule_family_id",
        "sizing_rule_id",
        "parameter_values_json",
        "split",
        "event_count",
        "replay_complete_count",
        "censored_share",
        "net_return_mean_delta_vs_hold120",
        "left_tail_net_return_p10_delta_vs_hold120",
        "bad_path_loss_compression_vs_hold120",
        "max_gain50_retention_vs_hold120",
        "winner_exit_efficiency",
        "denominator_status",
        "winner_retention_status",
    }
    _require_columns(rows, summary, summary_cols, "policy_summary_columns", paths["summary"])
    _add(rows, "summary_splits_valid", set(summary["split"].astype(str)).issubset({"train", "validation", "robustness"}), "error", "unexpected split", relpath(paths["summary"]))
    _add(rows, "retention_threshold_present", bool(np.isclose(winner["retention_gate_threshold"].dropna().astype(float), float(config["thresholds"]["min_max_gain50_retention_vs_hold120"])).all()), "error", "retention threshold mismatch", relpath(paths["winner"]))

    _require_columns(rows, selection, {"selection_stage", "split_used", "policy_family_id", "candidate_policy_id", "parameter_set_id", "selection_metric_name", "selected_flag"}, "selection_trace_columns", paths["selection"])
    if "split_used" in selection.columns:
        _add(rows, "robustness_not_used_for_selection", not selection["split_used"].astype(str).eq("robustness").any(), "error", "robustness used in selection", relpath(paths["selection"]))
        train_ok = selection.loc[selection["selection_stage"].astype(str).eq("train_parameter_selection"), "split_used"].astype(str).eq("train").all()
        val_ok = selection.loc[selection["selection_stage"].astype(str).eq("validation_family_selection"), "split_used"].astype(str).eq("validation").all()
        _add(rows, "train_selection_uses_train_only", bool(train_ok), "error", "train selection used non-train split", relpath(paths["selection"]))
        _add(rows, "validation_selection_uses_validation_only", bool(val_ok), "error", "validation selection used non-validation split", relpath(paths["selection"]))

    replay_statuses = {
        "replay_complete",
        "censored_by_split_boundary",
        "censored_by_missing_price",
        "censored_by_missing_required_indicator",
        "censored_by_suspension_or_dirty_bar",
        "censored_by_no_exit_execution",
        "invalid_entry",
    }
    _add(rows, "replay_status_allowed", set(replay["replay_status"].astype(str)).issubset(replay_statuses), "error", "unexpected replay_status", relpath(paths["replay"]))
    _add(rows, "daily_path_has_pre_entry_lookback", int(daily["calendar_offset"].min()) <= -int(config["execution"]["pre_entry_lookback_trading_days"]), "error", "missing pre-entry lookback", relpath(paths["daily"]))
    _add(
        rows,
        "daily_path_has_exit_lag_buffer",
        int(daily["calendar_offset"].max()) >= int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"]),
        "error",
        "missing exit lag buffer",
        relpath(paths["daily"]),
    )
    _add(rows, "candidate_pool_baseline_A_only", bool(base["r04_inclusion_status"].astype(str).eq("included").all()), "error", "non-included candidates in base panel", relpath(paths["base"]))
    _add(rows, "mask_columns_not_in_base_panel", not any(col.startswith("mask_B") or col.startswith("mask_C") for col in base.columns), "error", "mask column leaked into base panel", relpath(paths["base"]))

    _require_columns(rows, final, {"final_decision", "selected_policy_id", "validation_gate_pass", "robustness_gate_pass"}, "final_decision_columns", paths["final"])
    if "final_decision" in final.columns:
        _add(rows, "final_decision_matches_manifest", str(final.iloc[0]["final_decision"]) == str(manifest.get("final_decision")), "error", "final decision mismatch", relpath(paths["final"]))
    selected_policy = str(final.iloc[0].get("selected_policy_id", "")) if len(final) else ""
    if selected_policy and selected_policy != "nan":
        selected = summary[summary["policy_id"].astype(str).eq(selected_policy)]
        _add(rows, "selected_policy_has_validation_and_robustness", {"validation", "robustness"}.issubset(set(selected["split"].astype(str))), "error", "selected policy missing OOS split rows", relpath(paths["summary"]))

    _require_columns(rows, interaction, {"policy_id", "split", "interaction_dimension", "interaction_value", "replay_complete_count", "top1_calendar_year_share", "research_lead_eligible_flag"}, "interaction_columns", paths["interaction"])
    if {"research_lead_eligible_flag", "replay_complete_count", "top1_calendar_year_share"}.issubset(interaction.columns):
        eligible = _bool_series(interaction["research_lead_eligible_flag"])
        min_count = int(config["thresholds"]["interaction_min_replay_complete_count"])
        max_year = float(config["thresholds"]["interaction_max_top1_calendar_year_share"])
        _add(
            rows,
            "interaction_research_leads_meet_thresholds",
            bool((~eligible | ((interaction["replay_complete_count"] >= min_count) & (interaction["top1_calendar_year_share"] <= max_year))).all()),
            "error",
            "ineligible interaction cell promoted",
            relpath(paths["interaction"]),
        )

    for boundary in config["validation"]["required_boundary_strings"]:
        _add(rows, f"report_boundary_string_present_{boundary[:24]}", boundary in report_text, "error", "missing boundary string", relpath(paths["report"]))
    forbidden = ["production ready", "entry gate passed", "market gate passed", "industry gate passed", "CTA strategy passed"]
    for phrase in forbidden:
        # The requirement allows explicit denial; the report generated by this runner should avoid these phrases except in the mandatory denial.
        _add(rows, f"report_forbidden_phrase_not_asserted_{phrase}", phrase not in report_text.replace("No production entry gate, sizing rule, or CTA strategy is emitted by this diagnostic.", ""), "error", f"forbidden phrase present: {phrase}", relpath(paths["report"]))

    reports_dir.mkdir(parents=True, exist_ok=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False)
    failed = audit.loc[audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"]), "check_name"].tolist()
    result = {
        "validation_status": "failed" if failed else "passed",
        "check_count": int(len(audit)),
        "failed_checks": failed,
        "audit_path": relpath(audit_path),
        "manifest_path": relpath(manifest_path),
        "final_decision": manifest.get("final_decision"),
    }
    write_json(result, validation_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate EP4 R04b fixed-entry hold/exit/risk-budget CTA diagnostic artifacts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = validate(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
