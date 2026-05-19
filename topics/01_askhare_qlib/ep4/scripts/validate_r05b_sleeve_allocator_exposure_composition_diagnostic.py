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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r05b_sleeve_allocator_exposure_composition_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
SLEEVE_IDS = {
    "r04e_union_primary_sleeve",
    "base_breakout_vcp_secondary_sleeve",
    "low_vol_uptrend_diagnostic_sleeve",
    "low_beta_low_vol_diagnostic_sleeve",
    "cash_sleeve",
    "benchmark_reporting_sleeve",
}
POLICIES = {
    "full_exposure_primary_baseline",
    "market_state_cash_allocator_v1",
    "market_state_cash_plus_basebreakout_secondary_v1",
}
SELECTABLE_POLICIES = {"market_state_cash_allocator_v1", "market_state_cash_plus_basebreakout_secondary_v1"}
RIGHT_TAIL_MODES = {"retention_vs_full_exposure", "absolute_p90_floor"}
RIGHT_TAIL_STATUSES = {"right_tail_pass", "right_tail_fail"}
VALIDATION_STATUSES = {
    "validation_pass",
    "validation_fail",
    "baseline_reference_only",
    "blocked_secondary_sleeve_insufficient_activation",
    "robustness_secondary_sleeve_insufficient_activation",
    "blocked_preflight_replay_complete_share",
    "robustness_readonly_failed",
}
FINAL_DECISION_CONTRACT = {
    "r05b_sleeve_allocator_passed_diagnostic_only": (False, "oos_roll_forward_retest_only"),
    "r05b_mostly_cash_illusion": (True, "ep5_escape_hatch_only"),
    "r05b_risk_on_full_exposure_failed": (True, "ep5_escape_hatch_only"),
    "r05b_allocator_not_viable_validation": (True, "ep5_escape_hatch_only"),
    "r05b_blocked_upstream_state_changed": (False, "rerun_upstream_or_refresh_requirement"),
    "r05b_blocked_validation_failed": (False, "fix_validation_failure_only"),
}

REQUIRED_CACHE = [
    "r05b_sleeve_daily_return_panel.parquet",
    "r05b_allocator_daily_return_panel.parquet",
]
REQUIRED_REPORTS = [
    "r05b_sleeve_registry_frozen.csv",
    "r05b_market_state_classifier_frozen.csv",
    "r05b_market_state_panel.csv",
    "r05b_allocator_policy_registry_frozen.csv",
    "r05b_preflight_replay_censor_audit.csv",
    "r05b_secondary_sleeve_activation_audit.csv",
    "r05b_sleeve_return_decomposition.csv",
    "r05b_risk_on_full_exposure_audit.csv",
    "r05b_mostly_cash_illusion_audit.csv",
    "r05b_allocator_policy_summary.csv",
    "r05b_allocator_monthly_summary.csv",
    "r05b_validation_gate_audit.csv",
    "r05b_terminal_decision_audit.csv",
    "r05b_final_decision.csv",
    "r05b_sleeve_allocator_exposure_composition_final_report.md",
]

SCHEMAS = {
    "r05b_sleeve_registry_frozen.csv": {
        "sleeve_id",
        "sleeve_role",
        "source_artifact",
        "source_filter",
        "allocation_status",
        "max_weight",
        "formula_hash",
        "blocking_reason",
    },
    "r05b_allocator_policy_registry_frozen.csv": {
        "allocator_policy_id",
        "policy_role",
        "allowed_sleeve_ids_json",
        "state_weight_rule_text",
        "secondary_activation_rule_text",
        "gross_exposure_formula_text",
        "cash_excluded_from_gross_exposure_flag",
        "is_selectable",
        "formula_hash",
        "blocking_reason",
    },
    "r05b_market_state_classifier_frozen.csv": {
        "classifier_id",
        "fit_split",
        "index_instrument",
        "feature_set_json",
        "thresholds_json",
        "state_rule_text",
        "state_rule_hash",
        "state_count",
        "signal_timing",
        "execution_timing",
        "active_flag",
    },
    "r05b_market_state_panel.csv": {
        "trade_date",
        "split",
        "state_signal_date",
        "exposure_effective_date",
        "market_state",
        "index_close",
        "index_ma20",
        "index_ma60",
        "index_ret20",
        "index_realized_vol20",
        "index_drawdown60",
        "classifier_id",
    },
    "r05b_preflight_replay_censor_audit.csv": {
        "sleeve_id",
        "candidate_id",
        "split",
        "source_event_count",
        "kept_event_count",
        "entry_executable_event_count",
        "complete_replay_event_count",
        "complete_replay_event_share",
        "complete_share_min",
        "lookahead_safe_event_count",
        "lookahead_censored_event_count",
        "lookahead_audit_status",
        "replay_censor_status",
        "blocking_reason",
    },
    "r05b_secondary_sleeve_activation_audit.csv": {
        "allocator_policy_id",
        "split",
        "validation_trading_day_count",
        "risk_on_day_count",
        "primary_active_lt20_day_count",
        "secondary_active_day_count",
        "secondary_activation_day_count",
        "secondary_activation_day_share",
        "activation_day_count_min",
        "activation_day_share_min",
        "secondary_activation_status",
        "robustness_secondary_activation_status",
        "policy_blocking_reason",
    },
    "r05b_sleeve_return_decomposition.csv": {
        "sleeve_id",
        "split",
        "market_state",
        "active_day_count",
        "active_day_share",
        "sleeve_period_return",
        "all_day_period_return",
        "active_only_period_return",
        "sleeve_daily_mean",
        "sleeve_monthly_p10",
        "sleeve_monthly_p90",
        "sleeve_max_drawdown",
        "sleeve_return_contribution",
        "allocation_status",
        "decomposition_status",
        "blocking_reason",
    },
    "r05b_risk_on_full_exposure_audit.csv": {
        "split",
        "risk_on_day_count",
        "risk_on_day_share",
        "full_exposure_primary_period_return",
        "full_exposure_primary_daily_mean",
        "full_exposure_primary_monthly_p10",
        "full_exposure_primary_max_drawdown",
        "risk_on_full_exposure_period_return",
        "risk_on_full_exposure_daily_mean",
        "risk_on_full_exposure_gate_status",
        "blocking_reason",
    },
    "r05b_mostly_cash_illusion_audit.csv": {
        "allocator_policy_id",
        "split",
        "average_gross_exposure",
        "average_gross_exposure_min",
        "cash_only_day_share",
        "cash_only_day_share_max",
        "risk_on_full_exposure_period_return",
        "risk_on_full_exposure_daily_mean",
        "overall_allocator_period_return",
        "overall_allocator_daily_mean",
        "mostly_cash_illusion_status",
        "blocking_reason",
    },
    "r05b_allocator_policy_summary.csv": {
        "allocator_policy_id",
        "split",
        "period_return",
        "daily_mean",
        "monthly_p10",
        "monthly_p90",
        "right_tail_gate_mode",
        "right_tail_gate_status",
        "absolute_p90_floor_min",
        "max_drawdown",
        "worst_20d_return",
        "average_gross_exposure",
        "cash_only_day_share",
        "right_tail_retention_vs_full_exposure",
        "secondary_activation_status",
        "robustness_secondary_activation_status",
        "validation_gate_status",
        "robustness_readonly_status",
        "blocking_reason",
    },
    "r05b_allocator_monthly_summary.csv": {
        "allocator_policy_id",
        "month",
        "split",
        "monthly_return",
        "full_exposure_primary_monthly_return",
        "monthly_return_delta_vs_full_exposure",
        "average_gross_exposure",
        "cash_only_day_share",
        "risk_on_day_count",
        "risk_neutral_day_count",
        "risk_off_day_count",
    },
    "r05b_validation_gate_audit.csv": {
        "allocator_policy_id",
        "split",
        "validation_gate_status",
        "period_return",
        "daily_mean",
        "monthly_p10",
        "monthly_p10_delta_vs_full_exposure",
        "max_drawdown",
        "max_drawdown_delta_vs_full_exposure",
        "worst_20d_delta_vs_full_exposure",
        "average_gross_exposure",
        "cash_only_day_share",
        "risk_on_full_exposure_period_return",
        "risk_on_full_exposure_daily_mean",
        "right_tail_retention_vs_full_exposure",
        "absolute_p90_floor_min",
        "allocator_monthly_p90",
        "full_exposure_primary_monthly_p90",
        "right_tail_gate_mode",
        "right_tail_gate_status",
        "robustness_readonly_status",
        "robustness_period_return",
        "robustness_allocator_monthly_p90",
        "robustness_full_exposure_primary_monthly_p90",
        "robustness_right_tail_gate_mode",
        "robustness_right_tail_gate_status",
        "robustness_right_tail_retention_vs_full_exposure",
        "robustness_absolute_p90_floor_min",
        "robustness_average_gross_exposure",
        "blocking_reason",
    },
    "r05b_final_decision.csv": {
        "requirement_id",
        "final_decision",
        "selected_allocator_policy_id",
        "validation_gate_status",
        "terminal_stop_flag",
        "allowed_next_requirement",
        "blocking_reason",
        "created_at",
    },
    "r05b_terminal_decision_audit.csv": {
        "decision_priority",
        "condition_name",
        "condition_met",
        "candidate_final_decision",
        "selected_final_decision",
        "terminal_stop_flag",
        "allowed_next_requirement",
        "blocking_reason",
    },
}

SLEEVE_DAILY_COLUMNS = {
    "trade_date",
    "split",
    "sleeve_id",
    "sleeve_role",
    "sleeve_daily_return",
    "sleeve_active_count",
    "sleeve_gross_exposure_before_allocator",
    "source_artifact",
    "source_candidate_id",
    "source_policy_id",
    "source_portfolio_id",
    "position_replay_method",
}
ALLOCATOR_DAILY_COLUMNS = {
    "trade_date",
    "split",
    "allocator_policy_id",
    "state_signal_date",
    "exposure_effective_date",
    "market_state",
    "r04e_union_primary_sleeve_active_count",
    "base_breakout_vcp_secondary_sleeve_active_count",
    "r04e_union_primary_sleeve_gross_exposure_before_allocator",
    "base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator",
    "r04e_union_primary_effective_gross_exposure",
    "base_breakout_vcp_secondary_effective_gross_exposure",
    "r04e_union_primary_sleeve_weight",
    "base_breakout_vcp_secondary_sleeve_weight",
    "cash_sleeve_weight",
    "total_gross_exposure",
    "allocator_daily_return",
    "full_exposure_primary_daily_return",
    "benchmark_daily_return",
    "cash_only_flag",
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


def _load_calendar(path: str | Path) -> pd.DatetimeIndex:
    values = [line.strip() for line in topic_path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize()).sort_values()


def _add(rows: list[dict[str, Any]], check_id: str, name: str, condition: bool, severity: str = "error", details: str = "", artifact_path: str = "") -> None:
    rows.append(
        {
            "check_id": check_id,
            "check_name": name,
            "severity": severity,
            "status": "passed" if bool(condition) else "failed",
            "details": "" if bool(condition) else details,
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


def _expected_final_decision(gate: pd.DataFrame, risk: pd.DataFrame, mostly: pd.DataFrame, upstream_ok: bool) -> str:
    if not upstream_ok:
        return "r05b_blocked_upstream_state_changed"
    risk_val = risk.loc[risk["split"].astype(str).eq("validation")]
    if not risk_val.empty and float(risk_val.iloc[0]["risk_on_full_exposure_period_return"]) <= 0:
        return "r05b_risk_on_full_exposure_failed"
    val_mostly = mostly.loc[mostly["split"].astype(str).eq("validation") & mostly["allocator_policy_id"].isin(SELECTABLE_POLICIES)]
    if len(val_mostly) and val_mostly["mostly_cash_illusion_status"].astype(str).eq("mostly_cash_illusion_fail").all():
        return "r05b_mostly_cash_illusion"
    passed = gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES), "validation_gate_status"].astype(str).eq("validation_pass")
    return "r05b_sleeve_allocator_passed_diagnostic_only" if bool(passed.any()) else "r05b_allocator_not_viable_validation"


def _benchmark_returns(config: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(topic_path(config["price_provider"]["price_source_path"])), region=REG_CN)
    instrument = config["price_provider"]["index_instrument"].upper()
    data = D.features([instrument], ["$close"], start_time=start.date().isoformat(), end_time=end.date().isoformat(), freq="day")
    out = data.rename(columns={"$close": "benchmark_close"}).reset_index().rename(columns={"instrument": "instrument_id", "datetime": "trade_date"})
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
    out["benchmark_close"] = pd.to_numeric(out["benchmark_close"], errors="coerce")
    out = out.sort_values("trade_date")
    out["benchmark_prev_close"] = out["benchmark_close"].shift(1)
    out["expected_benchmark_daily_return"] = out["benchmark_close"] / out["benchmark_prev_close"] - 1.0
    return out[["trade_date", "benchmark_close", "benchmark_prev_close", "expected_benchmark_daily_return"]]


def validate(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    validation_path = manifests_dir / "r05b_sleeve_allocator_exposure_composition_validation.json"
    audit_path = reports_dir / "r05b_sleeve_allocator_exposure_composition_validation_audit.csv"
    manifest_path = manifests_dir / "r05b_sleeve_allocator_exposure_composition_manifest.json"
    rows: list[dict[str, Any]] = []

    required_inputs = [
        config["upstream_r04e"]["validation"],
        config["upstream_r04e"]["final_decision"],
        config["upstream_r04e"]["portfolio_daily_return_panel"],
        config["upstream_r05_preflight"]["validation"],
        config["upstream_r05_preflight"]["final_decision"],
        config["upstream_r05_preflight"]["candidate_event_panel"],
        config["upstream_r05_preflight"]["forward_return_panel"],
        config["upstream_r05_preflight"]["candidate_formula_frozen"],
        config["upstream_r05a"]["status"],
        config["price_provider"]["calendar_source_path"],
        Path(config["price_provider"]["index_feature_path"]) / "close.day.bin",
    ]
    for idx, path in enumerate(required_inputs, start=1):
        _add(rows, f"I{idx:02d}", f"required_input_exists_{Path(path).name}", topic_path(path).exists(), "fatal", str(path), str(path))

    r04e_validation = _read_json(config["upstream_r04e"]["validation"])
    r04e_final = _read_csv(topic_path(config["upstream_r04e"]["final_decision"]))
    r05_validation = _read_json(config["upstream_r05_preflight"]["validation"])
    r05_final = _read_csv(topic_path(config["upstream_r05_preflight"]["final_decision"]))
    r05a_status = _read_json(config["upstream_r05a"]["status"])
    formula = _read_csv(topic_path(config["upstream_r05_preflight"]["candidate_formula_frozen"]))
    r04e_final_decision = "" if r04e_final.empty else str(r04e_final.iloc[0].get("final_decision", ""))
    r05_final_decision = "" if r05_final.empty else str(r05_final.iloc[0].get("final_decision", ""))
    r05_pass_count = np.nan if r05_final.empty else pd.to_numeric(r05_final.iloc[0].get("candidate_pass_count"), errors="coerce")
    upstream_ok = (
        r04e_validation.get("validation_status") == "passed"
        and r04e_final_decision == "r04e_union_not_viable_validation"
        and r05_validation.get("validation_status") == "passed"
        and r05_final_decision == "r05_preflight_stop_no_absolute_floor"
        and np.isfinite(r05_pass_count)
        and int(r05_pass_count) == 0
        and {"candidate_id", "round_trip_cost_bp"}.issubset(set(formula.columns))
        and r05a_status.get("status") == "abandoned_preflight_blocked"
        and r05a_status.get("active_implementation_allowed") is False
        and r05a_status.get("allowed_next_requirement") == "sleeve_allocator_direction_requirement"
    )
    _add(rows, "U01", "required_upstream_state_frozen", upstream_ok, "fatal", "upstream state mismatch", "")

    for idx, name in enumerate(REQUIRED_CACHE, start=1):
        _add(rows, f"O{idx:02d}", f"cache_exists_{name}", (cache_dir / name).exists(), "error", name, relpath(cache_dir / name))
    for idx, name in enumerate(REQUIRED_REPORTS, start=1):
        _add(rows, f"R{idx:02d}", f"report_exists_{name}", (reports_dir / name).exists(), "error", name, relpath(reports_dir / name))
    _add(rows, "M01", "manifest_exists", manifest_path.exists(), "error", relpath(manifest_path), relpath(manifest_path))

    if _status(rows) == "failed":
        audit = pd.DataFrame(rows)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit.to_csv(audit_path, index=False)
        payload = {
            "validation_status": "failed",
            "failed_checks": audit.loc[audit["status"].eq("failed"), "check_id"].tolist(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audit_path": relpath(audit_path),
            "manifest_path": relpath(manifest_path),
        }
        write_json(payload, validation_path)
        return payload

    sleeve_daily = pd.read_parquet(cache_dir / "r05b_sleeve_daily_return_panel.parquet")
    allocator_daily = pd.read_parquet(cache_dir / "r05b_allocator_daily_return_panel.parquet")
    _require_columns(rows, sleeve_daily, SLEEVE_DAILY_COLUMNS, "S01", cache_dir / "r05b_sleeve_daily_return_panel.parquet")
    _require_columns(rows, allocator_daily, ALLOCATOR_DAILY_COLUMNS, "A01", cache_dir / "r05b_allocator_daily_return_panel.parquet")

    reports: dict[str, pd.DataFrame] = {}
    for name, schema in SCHEMAS.items():
        path = reports_dir / name
        reports[name] = _read_csv(path)
        _require_columns(rows, reports[name], schema, f"C{len(reports):02d}", path)

    registry = reports["r05b_sleeve_registry_frozen.csv"]
    policy_registry = reports["r05b_allocator_policy_registry_frozen.csv"]
    market_state = reports["r05b_market_state_panel.csv"]
    classifier = reports["r05b_market_state_classifier_frozen.csv"]
    replay = reports["r05b_preflight_replay_censor_audit.csv"]
    activation = reports["r05b_secondary_sleeve_activation_audit.csv"]
    policy_summary = reports["r05b_allocator_policy_summary.csv"]
    risk = reports["r05b_risk_on_full_exposure_audit.csv"]
    mostly = reports["r05b_mostly_cash_illusion_audit.csv"]
    gate = reports["r05b_validation_gate_audit.csv"]
    final_df = reports["r05b_final_decision.csv"]
    terminal = reports["r05b_terminal_decision_audit.csv"]

    _add(rows, "S02", "registered_sleeve_set_exact", set(registry["sleeve_id"].astype(str)) == SLEEVE_IDS, "error", str(sorted(set(registry.get("sleeve_id", [])))), relpath(reports_dir / "r05b_sleeve_registry_frozen.csv"))
    _add(rows, "P01", "registered_policy_set_exact", set(policy_registry["allocator_policy_id"].astype(str)) == POLICIES, "error", str(sorted(set(policy_registry.get("allocator_policy_id", [])))), relpath(reports_dir / "r05b_allocator_policy_registry_frozen.csv"))

    sleeve_daily["trade_date"] = pd.to_datetime(sleeve_daily["trade_date"]).dt.normalize()
    allocator_daily["trade_date"] = pd.to_datetime(allocator_daily["trade_date"]).dt.normalize()
    allocator_daily["state_signal_date"] = pd.to_datetime(allocator_daily["state_signal_date"]).dt.normalize()
    allocator_daily["exposure_effective_date"] = pd.to_datetime(allocator_daily["exposure_effective_date"]).dt.normalize()
    market_state["trade_date"] = pd.to_datetime(market_state["trade_date"]).dt.normalize()
    market_state["state_signal_date"] = pd.to_datetime(market_state["state_signal_date"]).dt.normalize()
    market_state["exposure_effective_date"] = pd.to_datetime(market_state["exposure_effective_date"]).dt.normalize()

    _add(rows, "S03", "sleeve_daily_all_sleeves_present", set(sleeve_daily["sleeve_id"].astype(str)) == SLEEVE_IDS, "error", "", relpath(cache_dir / "r05b_sleeve_daily_return_panel.parquet"))
    gross = pd.to_numeric(sleeve_daily["sleeve_gross_exposure_before_allocator"], errors="coerce")
    active = pd.to_numeric(sleeve_daily["sleeve_active_count"], errors="coerce").fillna(0)
    _add(rows, "S04", "sleeve_gross_exposure_between_zero_one", gross.between(0, 1).all(), "error", "", relpath(cache_dir / "r05b_sleeve_daily_return_panel.parquet"))
    _add(rows, "S05", "inactive_sleeve_gross_zero", (gross[active.eq(0)].abs() <= 1e-12).all(), "error", "", relpath(cache_dir / "r05b_sleeve_daily_return_panel.parquet"))
    primary = sleeve_daily.loc[sleeve_daily["sleeve_id"].astype(str).eq("r04e_union_primary_sleeve")]
    primary_zero = pd.to_numeric(primary["sleeve_active_count"], errors="coerce").fillna(0).eq(0)
    _add(
        rows,
        "S06",
        "primary_active_zero_return_and_gross_zero",
        (pd.to_numeric(primary.loc[primary_zero, "sleeve_daily_return"], errors="coerce").abs() <= 1e-12).all()
        and (pd.to_numeric(primary.loc[primary_zero, "sleeve_gross_exposure_before_allocator"], errors="coerce").abs() <= 1e-12).all(),
        "error",
        "",
        relpath(cache_dir / "r05b_sleeve_daily_return_panel.parquet"),
    )

    market_required = ["index_close", "index_ma20", "index_ma60", "index_ret20", "index_realized_vol20", "index_drawdown60"]
    _add(rows, "MS01", "market_state_features_non_missing", not market_state[market_required].isna().any().any(), "error", "", relpath(reports_dir / "r05b_market_state_panel.csv"))
    _add(rows, "MS02", "market_state_count_lte_three", market_state["market_state"].nunique() <= 3 and pd.to_numeric(classifier["state_count"], errors="coerce").max() <= 3, "error", "", relpath(reports_dir / "r05b_market_state_panel.csv"))
    _add(rows, "MS03", "classifier_fit_train_only", classifier["fit_split"].astype(str).eq("train").all(), "error", "", relpath(reports_dir / "r05b_market_state_classifier_frozen.csv"))

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    prev_by_date = {pd.Timestamp(calendar[i]).normalize(): pd.Timestamp(calendar[i - 1]).normalize() for i in range(1, len(calendar))}
    date_semantics = allocator_daily["trade_date"].eq(allocator_daily["exposure_effective_date"]) & allocator_daily["state_signal_date"].eq(allocator_daily["trade_date"].map(prev_by_date))
    _add(rows, "A02", "allocator_trade_date_timing_semantics", bool(date_semantics.all()), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))
    primary_gross = pd.to_numeric(allocator_daily["r04e_union_primary_sleeve_weight"], errors="coerce") * pd.to_numeric(
        allocator_daily["r04e_union_primary_sleeve_gross_exposure_before_allocator"], errors="coerce"
    )
    secondary_gross = pd.to_numeric(allocator_daily["base_breakout_vcp_secondary_sleeve_weight"], errors="coerce") * pd.to_numeric(
        allocator_daily["base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator"], errors="coerce"
    )
    total_gross = pd.to_numeric(allocator_daily["total_gross_exposure"], errors="coerce")
    _add(rows, "A03", "gross_exposure_formula", np.allclose(total_gross, primary_gross + secondary_gross, atol=1e-12), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))
    _add(rows, "A04", "cash_excluded_from_gross_exposure", bool(total_gross.between(0, 1).all()), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))
    _add(rows, "A05", "cash_only_flag_total_gross_zero", (allocator_daily["cash_only_flag"].astype(bool) == total_gross.eq(0)).all(), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))
    sec_weight = pd.to_numeric(allocator_daily["base_breakout_vcp_secondary_sleeve_weight"], errors="coerce")
    _add(rows, "A06", "secondary_weight_cap", bool((sec_weight <= 0.2000000001).all()), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))
    sec_rows = allocator_daily.loc[sec_weight > 0]
    _add(
        rows,
        "A07",
        "secondary_activation_only_risk_on_primary_lt20_active",
        sec_rows.empty
        or (
            sec_rows["market_state"].astype(str).eq("risk_on")
            & (pd.to_numeric(sec_rows["r04e_union_primary_sleeve_active_count"], errors="coerce") < 20)
            & (pd.to_numeric(sec_rows["base_breakout_vcp_secondary_sleeve_active_count"], errors="coerce") > 0)
        ).all(),
        "error",
        "",
        relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"),
    )

    sleeve_pivot = sleeve_daily.pivot_table(index="trade_date", columns="sleeve_id", values="sleeve_daily_return", aggfunc="first")
    joined = allocator_daily.join(sleeve_pivot[["r04e_union_primary_sleeve", "base_breakout_vcp_secondary_sleeve"]], on="trade_date")
    expected_return = (
        pd.to_numeric(joined["r04e_union_primary_sleeve_weight"], errors="coerce") * pd.to_numeric(joined["r04e_union_primary_sleeve"], errors="coerce")
        + pd.to_numeric(joined["base_breakout_vcp_secondary_sleeve_weight"], errors="coerce") * pd.to_numeric(joined["base_breakout_vcp_secondary_sleeve"], errors="coerce")
    )
    _add(rows, "A08", "allocator_return_no_gross_double_scaling", np.allclose(pd.to_numeric(joined["allocator_daily_return"], errors="coerce"), expected_return, atol=1e-12), "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))

    start = allocator_daily["trade_date"].min()
    start_pos = max(0, int(calendar.searchsorted(start, side="left")) - 1)
    benchmark = _benchmark_returns(config, pd.Timestamp(calendar[start_pos]), allocator_daily["trade_date"].max())
    bench_join = allocator_daily[["trade_date", "benchmark_daily_return"]].drop_duplicates().merge(benchmark, on="trade_date", how="left")
    bench_ok = (
        bench_join["benchmark_close"].notna().all()
        and bench_join["benchmark_prev_close"].notna().all()
        and np.allclose(bench_join["benchmark_daily_return"], bench_join["expected_benchmark_daily_return"], atol=1e-12)
    )
    _add(rows, "B01", "benchmark_close_to_close_formula", bench_ok, "error", "", relpath(cache_dir / "r05b_allocator_daily_return_panel.parquet"))

    base_replay = replay.loc[replay["sleeve_id"].astype(str).eq("base_breakout_vcp_secondary_sleeve")]
    _add(rows, "PF01", "base_replay_complete_share_min", (pd.to_numeric(base_replay["complete_replay_event_share"], errors="coerce") >= pd.to_numeric(base_replay["complete_share_min"], errors="coerce")).all(), "error", "", relpath(reports_dir / "r05b_preflight_replay_censor_audit.csv"))
    _add(rows, "PF02", "preflight_lookahead_audit_pass", replay["lookahead_audit_status"].astype(str).eq("pass").all() and pd.to_numeric(replay["lookahead_censored_event_count"], errors="coerce").fillna(1).eq(0).all(), "error", "", relpath(reports_dir / "r05b_preflight_replay_censor_audit.csv"))
    _add(rows, "PF03", "secondary_activation_not_block_cash_or_baseline", not activation.loc[activation["allocator_policy_id"].isin(["full_exposure_primary_baseline", "market_state_cash_allocator_v1"]), "policy_blocking_reason"].astype(str).replace("nan", "").str.len().gt(0).any(), "error", "", relpath(reports_dir / "r05b_secondary_sleeve_activation_audit.csv"))

    mode_ok = policy_summary["right_tail_gate_mode"].astype(str).isin(RIGHT_TAIL_MODES).all() and gate["right_tail_gate_mode"].astype(str).isin(RIGHT_TAIL_MODES).all() and gate["robustness_right_tail_gate_mode"].astype(str).isin(RIGHT_TAIL_MODES).all()
    status_ok = policy_summary["right_tail_gate_status"].astype(str).isin(RIGHT_TAIL_STATUSES).all() and gate["right_tail_gate_status"].astype(str).isin(RIGHT_TAIL_STATUSES).all() and gate["robustness_right_tail_gate_status"].astype(str).isin(RIGHT_TAIL_STATUSES).all()
    _add(rows, "RT01", "right_tail_modes_and_statuses_allowed", mode_ok and status_ok, "error", "", relpath(reports_dir / "r05b_allocator_policy_summary.csv"))
    floors = pd.to_numeric(policy_summary["absolute_p90_floor_min"], errors="coerce")
    expected_floor = policy_summary["split"].map({"validation": 0.02, "robustness": 0.01, "train": 0.02}).astype(float)
    _add(rows, "RT02", "absolute_p90_floor_thresholds", np.allclose(floors, expected_floor, atol=1e-12), "error", "", relpath(reports_dir / "r05b_allocator_policy_summary.csv"))
    abs_mode = policy_summary["right_tail_gate_mode"].astype(str).eq("absolute_p90_floor")
    retention = pd.to_numeric(policy_summary["right_tail_retention_vs_full_exposure"], errors="coerce")
    _add(rows, "RT03", "right_tail_retention_null_semantics", retention[abs_mode].isna().all() and retention[~abs_mode].notna().all(), "error", "", relpath(reports_dir / "r05b_allocator_policy_summary.csv"))

    _add(rows, "G01", "validation_gate_status_allowed", gate["validation_gate_status"].astype(str).isin(VALIDATION_STATUSES).all(), "error", "", relpath(reports_dir / "r05b_validation_gate_audit.csv"))
    baseline_gate = gate.loc[gate["allocator_policy_id"].astype(str).eq("full_exposure_primary_baseline")]
    _add(rows, "G02", "baseline_reference_only_not_selectable", baseline_gate["validation_gate_status"].astype(str).eq("baseline_reference_only").all(), "error", "", relpath(reports_dir / "r05b_validation_gate_audit.csv"))
    selectable = gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES)]
    _add(rows, "G03", "selectable_gate_rows_present", set(selectable["allocator_policy_id"].astype(str)) == SELECTABLE_POLICIES, "error", "", relpath(reports_dir / "r05b_validation_gate_audit.csv"))
    _add(rows, "G04", "robustness_guardrail_pass_blocking", not ((selectable["robustness_readonly_status"].astype(str).eq("robustness_readonly_failed")) & selectable["validation_gate_status"].astype(str).eq("validation_pass")).any(), "error", "", relpath(reports_dir / "r05b_validation_gate_audit.csv"))

    final_decision = "" if final_df.empty else str(final_df.iloc[0].get("final_decision", ""))
    contract = FINAL_DECISION_CONTRACT.get(final_decision)
    _add(rows, "D01", "final_decision_allowed", contract is not None, "error", final_decision, relpath(reports_dir / "r05b_final_decision.csv"))
    if contract is not None and not final_df.empty:
        terminal_flag = str(final_df.iloc[0].get("terminal_stop_flag")).strip().lower() in {"true", "1"}
        _add(rows, "D02", "terminal_and_next_requirement_contract", terminal_flag == contract[0] and str(final_df.iloc[0].get("allowed_next_requirement")) == contract[1], "error", "", relpath(reports_dir / "r05b_final_decision.csv"))
    expected_decision = _expected_final_decision(gate, risk, mostly, upstream_ok)
    _add(rows, "D03", "final_decision_precedence", final_decision == expected_decision, "error", f"expected {expected_decision}, got {final_decision}", relpath(reports_dir / "r05b_final_decision.csv"))
    _add(rows, "D04", "terminal_decision_audit_selected_matches", terminal["selected_final_decision"].astype(str).eq(final_decision).all(), "error", "", relpath(reports_dir / "r05b_terminal_decision_audit.csv"))

    report_path = reports_dir / "r05b_sleeve_allocator_exposure_composition_final_report.md"
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    forbidden = config.get("validation", {}).get("forbidden_report_strings", [])
    _add(rows, "FR01", "final_report_forbidden_strings_absent", not any(s in report_text for s in forbidden), "error", str(forbidden), relpath(report_path))
    _add(rows, "FR02", "final_report_required_disclaimer_present", "R05b does not discover alpha." in report_text and "R05b only tests whether failed / relative-improvement pools have limited sleeve value." in report_text, "error", "", relpath(report_path))

    audit = pd.DataFrame(rows)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)
    status = _status(rows)
    failed = audit.loc[audit["status"].eq("failed"), "check_id"].tolist()
    warnings = audit.loc[audit["status"].eq("failed") & audit["severity"].eq("warning"), "check_id"].tolist()
    selected_allocator_policy_id = "" if final_df.empty else final_df.iloc[0].get("selected_allocator_policy_id", "")
    if pd.isna(selected_allocator_policy_id):
        selected_allocator_policy_id = ""
    payload = {
        "validation_status": status,
        "failed_checks": failed,
        "warning_checks": warnings,
        "final_decision": final_decision,
        "selected_allocator_policy_id": selected_allocator_policy_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audit_path": relpath(audit_path),
        "manifest_path": relpath(manifest_path),
    }
    write_json(payload, validation_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate EP4 R05b sleeve allocator exposure composition diagnostic outputs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    payload = validate(args.config)
    print(json.dumps({"validation_status": payload["validation_status"], "failed_checks": payload["failed_checks"]}, ensure_ascii=False))
    if payload["validation_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
