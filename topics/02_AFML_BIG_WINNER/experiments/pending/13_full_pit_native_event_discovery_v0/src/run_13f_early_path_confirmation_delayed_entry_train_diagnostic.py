#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_13C_PATH = EXPERIMENT_DIR / "src" / "run_13c_morphology_orthogonal_residual_importance_diagnostic.py"
RUNNER_13E_PATH = EXPERIMENT_DIR / "src" / "run_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13c = load_runner(RUNNER_13C_PATH, "run_13c_morphology_orthogonal_residual_importance_diagnostic")
r13e = load_runner(RUNNER_13E_PATH, "run_13e_nonlinear_winner_train_kfold_feasibility_diagnostic")
r13a = r13c.r13a
r13a3 = r13c.r13a3


RUN_ID = "13F_early_path_confirmation_delayed_entry_train_diagnostic"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13F"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13f_early_path_confirmation_delayed_entry_train_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

ARMS = ("arm_t0_baseline", "arm_gate_delayed", "arm_model_delayed")
HORIZON_FROM_ENTRY = "horizon_mode_from_entry"
HORIZON_CALENDAR_T0 = "horizon_mode_calendar_t0"
EARLY_FEATURES = [
    "early_path_cum_return",
    "early_path_max_favorable_excursion",
    "early_path_max_adverse_excursion",
    "early_path_realized_volatility",
    "early_path_up_day_fraction",
    "early_path_close_position_in_range",
    "early_path_volume_trend",
    "early_path_touched_lower_barrier_flag",
    "early_path_touched_upper_barrier_flag",
]
REPORT_INPUT_KEYS = {"upstream_report_13c", "upstream_report_13e"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 13F early-path confirmation delayed-entry train diagnostic."
    )
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_lineage_audit": TABLE_DIR / "upstream_lineage_audit.csv",
        "row_level_rebuild_audit": TABLE_DIR / "row_level_rebuild_audit.csv",
        "early_path_rebuild_audit": TABLE_DIR / "early_path_rebuild_audit.csv",
        "delayed_entry_executability_audit": TABLE_DIR / "delayed_entry_executability_audit.csv",
        "fold_arm_metrics": TABLE_DIR / "fold_arm_metrics.csv",
        "delayed_vs_t0_entry_comparison": TABLE_DIR / "delayed_vs_t0_entry_comparison.csv",
        "missed_winner_accounting": TABLE_DIR / "missed_winner_accounting.csv",
        "train_kfold_uniqueness_audit": TABLE_DIR / "train_kfold_uniqueness_audit.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "early_path_confirmation_delayed_entry_decision": TABLE_DIR / "early_path_confirmation_delayed_entry_decision.csv",
        "report": REPORT_DIR / "early_path_confirmation_delayed_entry_train_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13c.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13c.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13c.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13c.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r13c.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r13c.count_rows(path)


def stable_hash(value: Any) -> str:
    return r13c.stable_hash(value)


def schema_hash(path: Path) -> str:
    return r13e.schema_hash(path)


def boolish(value: Any) -> bool:
    return r13c.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13c.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13c.finite_numeric(series)


def cost_label(cost: float) -> str:
    return r13c.cost_label(float(cost))


def fold_std(values: pd.Series) -> float:
    numeric = finite_numeric(values).dropna()
    if len(numeric) <= 1:
        return 0.0 if len(numeric) == 1 else np.nan
    return float(numeric.std(ddof=1))


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13c": (),
        "upstream_requirement_13e": (),
        "upstream_report_13c": (),
        "upstream_report_13e": (),
        "upstream_13c_manifest": (),
        "upstream_13c_decision": (
            "decision_state",
            "selected_state_id",
            "input_gate_status",
            "row_level_rebuild_gate_status",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ),
        "upstream_13c_feature_cluster_dictionary": (
            "cluster_id",
            "feature_id",
            "feature_status",
        ),
        "upstream_13c_morphology_residual_panel_cache": (
            "row_id",
            "instrument",
            "reference_date",
            "split_bucket",
            "native_scope",
            "winner_positive",
        ),
        "upstream_13e_decision": (
            "decision_state",
            "selected_state_id",
            "row_level_rebuild_gate_status",
            "purged_cv_integrity_gate_status",
            "validation_used_in_13e",
            "robustness_used_in_13e",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ),
        "pit_topn_400_100_executable_daily": (
            "usable_trade_date",
            "instrument",
            "is_listed",
            "is_st",
            "is_suspended",
        ),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket"),
    }


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id in REPORT_INPUT_KEYS:
        return "lineage_report_only_not_row_truth"
    if artifact_id.startswith("upstream_13c"):
        return "upstream_13c_lineage"
    if artifact_id.startswith("upstream_13e"):
        return "upstream_13e_lineage"
    if artifact_id.startswith("pit_") or artifact_id in {
        "stock_daily_qfq_dir",
        "global_regime_calendar",
    }:
        return "raw_pit_lineage_guard"
    return "run_config_input"


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    expected = input_expected_columns()
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = expected.get(artifact_id, ())
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        column_count: int | float = np.nan
        row_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                else:
                    frame = read_table(path, nrows=5) if path.suffix.lower() != ".parquet" else pd.read_parquet(path)
                    column_count = len(frame.columns)
                    row_count = count_rows(path)
                    missing = sorted(set(required_cols) - set(frame.columns))
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
            except Exception as exc:  # pragma: no cover - defensive audit path.
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "read_error"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "required_flag": True,
                "lineage_role": lineage_role_for_artifact(artifact_id),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path) if path.exists() and path.is_file() else "",
                "read_status": read_status,
                "schema_status": schema_status,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    bad = audit.loc[
        audit["required_flag"].astype(bool)
        & (
            audit["read_status"].astype(str).ne("pass")
            | audit["schema_status"].astype(str).str.startswith("missing_columns")
            | audit["schema_status"].astype(str).eq("read_error")
        )
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_id"].astype(str).tolist())


def audit_row(check_id: str, observed: Any, expected: Any, ok: bool, source: str) -> dict[str, Any]:
    return {
        "lineage_check_id": check_id,
        "observed_value": observed,
        "expected_value": expected,
        "status": "pass" if ok else "fail",
        "source_artifact": source,
    }


def first_row_value(frame: pd.DataFrame, column: str, default: Any = "") -> Any:
    if frame.empty or column not in frame.columns:
        return default
    return frame.iloc[0].get(column, default)


def required_feature_columns(config: dict[str, Any]) -> list[str]:
    clusters = config.get("feature_clusters", {})
    names: list[str] = []
    for cluster in [
        "cluster_drawdown_morphology",
        "cluster_denominator_controls",
        "cluster_compression",
        "cluster_position_strength",
        "cluster_participation",
    ]:
        names.extend(clusters.get(cluster, []))
    return list(dict.fromkeys(names))


def build_upstream_lineage_audit(
    resolved: dict[str, Path],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    rows: list[dict[str, Any]] = []
    try:
        dec13c = read_table(resolved["upstream_13c_decision"])
        rows.extend(
            [
                audit_row("13c.decision_state", first_row_value(dec13c, "decision_state"), "13C_stop_residual_probability_only_no_utility", first_row_value(dec13c, "decision_state") == "13C_stop_residual_probability_only_no_utility", "upstream_13c_decision"),
                audit_row("13c.selected_state_id", first_row_value(dec13c, "selected_state_id"), selected, first_row_value(dec13c, "selected_state_id") == selected, "upstream_13c_decision"),
                audit_row("13c.input_gate_status", first_row_value(dec13c, "input_gate_status"), "pass", first_row_value(dec13c, "input_gate_status") == "pass", "upstream_13c_decision"),
                audit_row("13c.row_level_rebuild_gate_status", first_row_value(dec13c, "row_level_rebuild_gate_status"), "pass", first_row_value(dec13c, "row_level_rebuild_gate_status") == "pass", "upstream_13c_decision"),
                audit_row("13c.meta_labeling_authorized", boolish(first_row_value(dec13c, "meta_labeling_authorized")), False, not boolish(first_row_value(dec13c, "meta_labeling_authorized")), "upstream_13c_decision"),
                audit_row("13c.bet_sizing_authorized", boolish(first_row_value(dec13c, "bet_sizing_authorized")), False, not boolish(first_row_value(dec13c, "bet_sizing_authorized")), "upstream_13c_decision"),
            ]
        )
    except Exception as exc:
        rows.append(audit_row("13c.decision_readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13c_decision"))

    try:
        dec13e = read_table(resolved["upstream_13e_decision"])
        rows.extend(
            [
                audit_row("13e.decision_state", first_row_value(dec13e, "decision_state"), "13E_stop_no_nonlinear_auc_improvement", first_row_value(dec13e, "decision_state") == "13E_stop_no_nonlinear_auc_improvement", "upstream_13e_decision"),
                audit_row("13e.selected_state_id", first_row_value(dec13e, "selected_state_id"), selected, first_row_value(dec13e, "selected_state_id") == selected, "upstream_13e_decision"),
                audit_row("13e.row_level_rebuild_gate_status", first_row_value(dec13e, "row_level_rebuild_gate_status"), "pass", first_row_value(dec13e, "row_level_rebuild_gate_status") == "pass", "upstream_13e_decision"),
                audit_row("13e.purged_cv_integrity_gate_status", first_row_value(dec13e, "purged_cv_integrity_gate_status"), "pass", first_row_value(dec13e, "purged_cv_integrity_gate_status") == "pass", "upstream_13e_decision"),
                audit_row("13e.validation_used_in_13e", boolish(first_row_value(dec13e, "validation_used_in_13e")), False, not boolish(first_row_value(dec13e, "validation_used_in_13e")), "upstream_13e_decision"),
                audit_row("13e.robustness_used_in_13e", boolish(first_row_value(dec13e, "robustness_used_in_13e")), False, not boolish(first_row_value(dec13e, "robustness_used_in_13e")), "upstream_13e_decision"),
                audit_row("13e.meta_labeling_authorized", boolish(first_row_value(dec13e, "meta_labeling_authorized")), False, not boolish(first_row_value(dec13e, "meta_labeling_authorized")), "upstream_13e_decision"),
                audit_row("13e.bet_sizing_authorized", boolish(first_row_value(dec13e, "bet_sizing_authorized")), False, not boolish(first_row_value(dec13e, "bet_sizing_authorized")), "upstream_13e_decision"),
            ]
        )
    except Exception as exc:
        rows.append(audit_row("13e.decision_readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13e_decision"))

    try:
        panel_path = resolved["upstream_13c_morphology_residual_panel_cache"]
        manifest = json.loads(resolved["upstream_13c_manifest"].read_text(encoding="utf-8"))
        manifest_outputs = manifest.get("publishable_outputs", {}) | manifest.get("local_cache_outputs", {})
        cache_rows = {
            str(row.get("artifact_id")): row
            for row in manifest.get("local_cache_audit", [])
        }
        panel_cache_row = cache_rows.get("morphology_residual_panel", {})
        panel_rows = count_rows(panel_path)
        rows.append(
            audit_row(
                "morphology_residual_panel.row_count_positive",
                panel_rows,
                ">0",
                bool(pd.notna(panel_rows) and float(panel_rows) > 0),
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
        rows.append(
            audit_row(
                "13c.manifest_readable",
                "readable",
                "readable",
                isinstance(manifest_outputs, dict),
                "upstream_13c_manifest",
            )
        )
        observed_schema = schema_hash(panel_path)
        expected_schema = str(panel_cache_row.get("schema_hash", ""))
        rows.append(
            audit_row(
                "morphology_residual_panel.manifest_schema_hash",
                observed_schema,
                expected_schema,
                bool(expected_schema) and observed_schema == expected_schema,
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
        expected_rows = int(panel_cache_row.get("row_count", -1))
        rows.append(
            audit_row(
                "morphology_residual_panel.manifest_row_count",
                panel_rows,
                expected_rows,
                pd.notna(panel_rows) and int(panel_rows) == expected_rows,
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
        row_audit_path = manifest_outputs.get("row_level_rebuild_audit", "")
        row_audit = read_table(Path(row_audit_path)) if row_audit_path else pd.DataFrame()
        status_col = "status" if "status" in row_audit.columns else "row_level_rebuild_gate_status"
        row_audit_ok = bool(
            not row_audit.empty
            and status_col in row_audit.columns
            and row_audit[status_col].astype(str).eq("pass").all()
        )
        rows.append(
            audit_row(
                "13c.row_level_rebuild_audit_all_pass",
                int(row_audit[status_col].astype(str).ne("pass").sum()) if status_col in row_audit.columns else "missing_status_column",
                0,
                row_audit_ok,
                "upstream_13c_manifest",
            )
        )
        panel_head = pd.read_parquet(panel_path)
        selected_col = str(config.get("selected_state_id", "repair_range_participation_core_30"))
        row_key_ok = bool(
            "row_id" in panel_head.columns
            and not panel_head["row_id"].duplicated().any()
            and {"instrument", "reference_date"} <= set(panel_head.columns)
            and not panel_head.duplicated(["instrument", "reference_date"]).any()
        )
        rows.append(
            audit_row(
                "morphology_residual_panel.row_key_uniqueness",
                "unique" if row_key_ok else "duplicate_or_missing_key",
                "unique",
                row_key_ok,
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
        split_ok = bool(
            "split_bucket" in panel_head.columns
            and {"train", "validation", "robustness"} <= set(panel_head["split_bucket"].astype(str))
        )
        rows.append(
            audit_row(
                "morphology_residual_panel.split_boundary_coverage",
                ";".join(sorted(set(panel_head.get("split_bucket", pd.Series(dtype=str)).astype(str)))),
                "train;validation;robustness",
                split_ok,
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
        selected_ok = bool(selected_col in panel_head.columns and bool_series(panel_head[selected_col]).any())
        rows.append(
            audit_row(
                "morphology_residual_panel.selected_membership_available",
                selected_col if selected_ok else f"missing_or_empty:{selected_col}",
                selected_col,
                selected_ok,
                "upstream_13c_morphology_residual_panel_cache",
            )
        )
    except Exception as exc:
        rows.append(audit_row("13c.manifest_or_panel_readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13c_manifest"))

    try:
        feature_dict = read_table(resolved["upstream_13c_feature_cluster_dictionary"])
        required = set(required_feature_columns(config))
        required_rows = feature_dict.loc[feature_dict["feature_id"].astype(str).isin(required)]
        bad = required_rows.loc[required_rows["feature_status"].astype(str).ne("pass")]
        rows.append(
            audit_row(
                "feature_cluster_dictionary.required_features_pass",
                ";".join(bad["feature_id"].astype(str).tolist()),
                "",
                bad.empty and len(required_rows) >= len(required),
                "upstream_13c_feature_cluster_dictionary",
            )
        )
    except Exception as exc:
        rows.append(audit_row("feature_cluster_dictionary.readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13c_feature_cluster_dictionary"))

    audit = pd.DataFrame(rows)
    failed = audit.loc[audit["status"].astype(str).ne("pass")]
    status = "pass" if failed.empty else "fail"
    reason = ";".join(failed["lineage_check_id"].astype(str).tolist())
    return audit, status, reason


def load_train_rows_only(panel_path: Path) -> pd.DataFrame:
    return pd.read_parquet(panel_path, filters=[("split_bucket", "==", "train")])


def required_row_columns(config: dict[str, Any]) -> list[str]:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    cols = [
        "row_id",
        "instrument",
        "reference_date",
        "entry_date",
        "reference_pos",
        "entry_pos",
        "entry_price",
        "split_bucket",
        "native_scope",
        selected,
        "winner_positive",
        "upper_first",
        "lower_first",
        "fast_fail",
        "horizon_complete",
        "upper_barrier",
        "lower_barrier",
        "time_to_upper",
        "time_to_lower",
        "row_utility_component_0bps",
        "row_utility_component_50bps",
        "row_utility_component_100bps",
        "volatility_20d",
    ]
    return list(dict.fromkeys(cols))


def prepare_train_event_panel(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    out = panel.copy()
    if "split_bucket" not in out.columns and "split" in out.columns:
        out["split_bucket"] = out["split"].astype(str)
    if "native_scope" not in out.columns:
        out["native_scope"] = True
    if selected not in out.columns:
        raise KeyError(f"missing selected_state column: {selected}")
    calendar_source = out
    out = out.loc[
        out["split_bucket"].astype(str).eq("train")
        & bool_series(out["native_scope"])
        & bool_series(out[selected])
    ].copy()
    out["event_start_pos"] = finite_numeric(out["entry_pos"])
    out["original_t0_event_offset"] = r13c.event_touch_offsets(out)
    out["original_t0_event_end_pos"] = out["event_start_pos"] + out["original_t0_event_offset"]
    out["event_end_pos"] = out["original_t0_event_end_pos"]
    out = r13e.add_global_calendar_session_pos(out, calendar_source=calendar_source)
    return out


def label_lineage_status(train_events: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str]:
    expected = config.get("selected_label", {})
    if train_events.empty:
        return "fail", "empty_train_events"
    reasons: list[str] = []
    if "label_id" in train_events.columns and not train_events["label_id"].astype(str).eq(str(expected.get("label_id", ""))).all():
        reasons.append("label_id_mismatch")
    if "horizon_sessions" in train_events.columns and not finite_numeric(train_events["horizon_sessions"]).eq(float(expected.get("horizon_sessions", 20))).all():
        reasons.append("horizon_sessions_mismatch")
    if "horizon_complete" in train_events.columns and not bool_series(train_events["horizon_complete"]).all():
        reasons.append("horizon_incomplete")
    if "volatility_20d" not in train_events.columns or finite_numeric(train_events["volatility_20d"]).isna().all():
        reasons.append("volatility_20d_unavailable")
    return ("pass", "") if not reasons else ("fail", ";".join(reasons))


def build_row_level_rebuild_audit(
    train_events: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    min_train = int(config.get("thresholds", {}).get("min_train_event_n", 1000))
    missing_cols = sorted(set(required_row_columns(config)) - set(train_events.columns))
    non_train_rows = int(train_events["split_bucket"].astype(str).ne("train").sum()) if "split_bucket" in train_events else len(train_events)
    selected_mismatch = int((~bool_series(train_events.get(selected, pd.Series(False, index=train_events.index)))).sum())
    duplicate_key_n = int(train_events.duplicated(["instrument", "reference_date"]).sum()) if {"instrument", "reference_date"} <= set(train_events.columns) else len(train_events)
    reference_pos_missing = int(finite_numeric(train_events.get("reference_pos", pd.Series(np.nan, index=train_events.index))).isna().sum())
    entry_pos_missing = int(finite_numeric(train_events.get("entry_pos", pd.Series(np.nan, index=train_events.index))).isna().sum())
    status = (
        "pass"
        if len(train_events) >= min_train
        and not missing_cols
        and non_train_rows == 0
        and selected_mismatch == 0
        and duplicate_key_n == 0
        and reference_pos_missing == 0
        and entry_pos_missing == 0
        else "fail"
    )
    reasons: list[str] = []
    if len(train_events) < min_train:
        reasons.append("train_event_n_below_min")
    if missing_cols:
        reasons.append("missing_columns:" + ";".join(missing_cols))
    if non_train_rows:
        reasons.append("non_train_rows_present")
    if selected_mismatch:
        reasons.append("selected_event_membership_mismatch")
    if duplicate_key_n:
        reasons.append("instrument_reference_date_not_unique")
    if reference_pos_missing or entry_pos_missing:
        reasons.append("pit_position_missing")
    audit = pd.DataFrame(
        [
            {
                "selected_state_id": selected,
                "row_count": len(train_events),
                "unique_row_id_count": int(train_events["row_id"].nunique()) if "row_id" in train_events else 0,
                "non_train_row_count": non_train_rows,
                "selected_event_membership_mismatch_n": selected_mismatch,
                "required_column_missing_count": len(missing_cols),
                "missing_required_columns": ";".join(missing_cols),
                "instrument_reference_date_duplicate_n": duplicate_key_n,
                "reference_pos_missing_n": reference_pos_missing,
                "t0_entry_pos_missing_n": entry_pos_missing,
                "report_text_used_as_row_truth": False,
                "validation_rows_used": False,
                "robustness_rows_used": False,
                "row_level_rebuild_gate_status": status,
            }
        ]
    )
    return audit, status, ";".join(reasons)


def qfq_path(qfq_dir: Path, instrument: str) -> Path:
    return qfq_dir / f"{instrument}.csv"


def load_pit_executable_dates(path: Path) -> dict[str, set[str]]:
    frame = read_table(path)
    if not {"usable_trade_date", "instrument"} <= set(frame.columns):
        raise ValueError("pit_executable_missing_required_columns")
    active = pd.Series(True, index=frame.index)
    if "is_listed" in frame.columns:
        active &= bool_series(frame["is_listed"])
    if "is_st" in frame.columns:
        active &= ~bool_series(frame["is_st"])
    if "is_suspended" in frame.columns:
        active &= ~bool_series(frame["is_suspended"])
    frame = frame.loc[active].copy()
    frame["usable_trade_date"] = frame["usable_trade_date"].map(r13a.date_text)
    dates: dict[str, set[str]] = {}
    for inst, sub in frame.groupby(frame["instrument"].astype(str), sort=False):
        dates[str(inst)] = set(sub["usable_trade_date"].astype(str))
    return dates


def load_qfq_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError(f"missing date column in {path}")
    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
    frame["date"] = frame["date"].map(r13a.date_text)
    for col in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
        if col in frame.columns:
            frame[col] = finite_numeric(frame[col])
    return frame


def finite_price(value: Any) -> bool:
    try:
        x = float(value)
    except Exception:
        return False
    return bool(np.isfinite(x) and x > 0)


def find_delayed_entry_pos(
    bars: pd.DataFrame | None,
    target_pos: int,
    max_forward_shift_sessions: int,
    instrument: str = "",
    executable_dates_by_instrument: dict[str, set[str]] | None = None,
) -> tuple[float, float, bool]:
    if bars is None or target_pos < 0:
        return np.nan, np.nan, False
    last = min(len(bars) - 1, target_pos + int(max_forward_shift_sessions))
    for pos in range(target_pos, last + 1):
        pit_ok = True
        if executable_dates_by_instrument is not None:
            date = r13a.date_text(bars.iloc[pos].get("date", ""))
            pit_ok = date in executable_dates_by_instrument.get(str(instrument), set())
        if pos < len(bars) and finite_price(bars.iloc[pos].get("open", np.nan)) and pit_ok:
            return float(pos), float(pos - target_pos), True
    return np.nan, np.nan, False


def early_path_features(
    row: pd.Series,
    bars: pd.DataFrame | None,
    early_path_k: int,
    delayed_entry_pos: float,
) -> dict[str, Any]:
    entry_pos = int(float(row.get("entry_pos"))) if pd.notna(row.get("entry_pos")) else -1
    entry_price = float(row.get("entry_price", np.nan))
    early_end = entry_pos + int(early_path_k) - 1
    base = {
        "early_path_window_start_pos": float(entry_pos),
        "early_path_window_end_pos": float(early_end),
        "early_path_evaluable": False,
        "early_path_cum_return": np.nan,
        "early_path_max_favorable_excursion": np.nan,
        "early_path_max_adverse_excursion": np.nan,
        "early_path_realized_volatility": np.nan,
        "early_path_up_day_fraction": np.nan,
        "early_path_close_position_in_range": np.nan,
        "early_path_volume_trend": np.nan,
        "early_path_touched_lower_barrier_flag": False,
        "early_path_touched_upper_barrier_flag": False,
    }
    if bars is None or entry_pos < 0 or early_end >= len(bars) or not finite_price(entry_price):
        return base
    window = bars.iloc[entry_pos : early_end + 1]
    if window.empty or not {"open", "high", "low", "close"} <= set(window.columns):
        return base
    highs = finite_numeric(window["high"])
    lows = finite_numeric(window["low"])
    closes = finite_numeric(window["close"])
    opens = finite_numeric(window["open"])
    if highs.isna().any() or lows.isna().any() or closes.isna().any() or opens.isna().any():
        return base
    delayed_open = np.nan
    if pd.notna(delayed_entry_pos) and int(delayed_entry_pos) < len(bars):
        delayed_open = float(bars.iloc[int(delayed_entry_pos)].get("open", np.nan))
    high_max = float(highs.max())
    low_min = float(lows.min())
    range_width = high_max - low_min
    pct = closes.pct_change().dropna()
    upper_barrier = float(row.get("upper_barrier", np.nan))
    lower_barrier = float(row.get("lower_barrier", np.nan))
    upper_price = entry_price * (1.0 + upper_barrier)
    lower_price = entry_price * (1.0 + lower_barrier)
    base.update(
        {
            "early_path_evaluable": True,
            "early_path_cum_return": delayed_open / entry_price - 1.0 if finite_price(delayed_open) else np.nan,
            "early_path_max_favorable_excursion": high_max / entry_price - 1.0,
            "early_path_max_adverse_excursion": low_min / entry_price - 1.0,
            "early_path_realized_volatility": float(pct.std(ddof=0)) if len(pct) else 0.0,
            "early_path_up_day_fraction": float((closes >= opens).mean()),
            "early_path_close_position_in_range": float((closes.iloc[-1] - low_min) / range_width) if range_width > 0 else 0.5,
            "early_path_volume_trend": float(finite_numeric(window.get("volume", pd.Series(np.nan, index=window.index))).iloc[-1] / finite_numeric(window.get("volume", pd.Series(np.nan, index=window.index))).mean() - 1.0)
            if "volume" in window.columns and finite_numeric(window["volume"]).notna().any() and finite_numeric(window["volume"]).mean() != 0
            else 0.0,
            "early_path_touched_lower_barrier_flag": bool(pd.notna(lower_barrier) and lows.le(lower_price).any()),
            "early_path_touched_upper_barrier_flag": bool(pd.notna(upper_barrier) and highs.ge(upper_price).any()),
        }
    )
    return base


def delayed_label(
    row: pd.Series,
    bars: pd.DataFrame | None,
    delayed_entry_pos: float,
    horizon_end_pos: float,
    costs: list[float],
    fast_fail_max_sessions: int = 5,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "delayed_label_evaluable": False,
        "delayed_winner_positive": False,
        "delayed_upper_first": False,
        "delayed_lower_first": False,
        "delayed_fast_fail": False,
        "delayed_neutral": False,
        "delayed_same_bar_conflict": False,
        "delayed_time_to_upper": np.nan,
        "delayed_time_to_lower": np.nan,
        "delayed_horizon_close_return": np.nan,
        "delayed_entry_price": np.nan,
    }
    for cost in costs:
        payload[f"delayed_row_utility_component_{cost_label(cost)}"] = np.nan
    if bars is None or pd.isna(delayed_entry_pos) or pd.isna(horizon_end_pos):
        return payload
    start = int(delayed_entry_pos)
    end = int(horizon_end_pos)
    if start < 0 or end < start or end >= len(bars):
        return payload
    entry_price = float(bars.iloc[start].get("open", np.nan))
    if not finite_price(entry_price):
        return payload
    window = bars.iloc[start : end + 1]
    upper_barrier = float(row.get("upper_barrier", np.nan))
    lower_barrier = float(row.get("lower_barrier", np.nan))
    upper_price = entry_price * (1.0 + upper_barrier)
    lower_price = entry_price * (1.0 + lower_barrier)
    upper_first = False
    lower_first = False
    same_bar = False
    ttu = np.nan
    ttl = np.nan
    for offset, (_, bar) in enumerate(window.iterrows()):
        high = float(bar.get("high", np.nan))
        low = float(bar.get("low", np.nan))
        upper_hit = np.isfinite(high) and high >= upper_price
        lower_hit = np.isfinite(low) and low <= lower_price
        if upper_hit and lower_hit:
            same_bar = True
            lower_first = True
            ttu = float(offset)
            ttl = float(offset)
            break
        if lower_hit:
            lower_first = True
            ttl = float(offset)
            break
        if upper_hit:
            upper_first = True
            ttu = float(offset)
            break
    neutral = not upper_first and not lower_first
    close_end = float(window.iloc[-1].get("close", np.nan))
    payload.update(
        {
            "delayed_label_evaluable": True,
            "delayed_winner_positive": bool(upper_first),
            "delayed_upper_first": bool(upper_first),
            "delayed_lower_first": bool(lower_first),
            "delayed_fast_fail": bool(lower_first and pd.notna(ttl) and ttl <= fast_fail_max_sessions),
            "delayed_neutral": bool(neutral),
            "delayed_same_bar_conflict": bool(same_bar),
            "delayed_time_to_upper": ttu,
            "delayed_time_to_lower": ttl,
            "delayed_horizon_close_return": close_end / entry_price - 1.0 if finite_price(close_end) else np.nan,
            "delayed_entry_price": entry_price,
        }
    )
    for cost in costs:
        payload[f"delayed_row_utility_component_{cost_label(cost)}"] = (
            float(upper_first) * upper_barrier - float(lower_first) * abs(lower_barrier) - float(cost)
        )
    return payload


def reconstruct_event_paths(
    events: pd.DataFrame,
    config: dict[str, Any],
    qfq_dir: Path,
    qfq_cache: dict[str, pd.DataFrame] | None = None,
    executable_dates_by_instrument: dict[str, set[str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config.get("early_path", {})
    k_grid = [int(x) for x in cfg.get("k_grid", [2, 3, 5, 8, 13])]
    horizon_modes = list(cfg.get("horizon_modes", [HORIZON_FROM_ENTRY, HORIZON_CALENDAR_T0]))
    max_shift = int(cfg.get("max_forward_shift_sessions", 5))
    costs = [float(x) for x in config.get("thresholds", {}).get("cost_buffer_grid", [0.0, 0.005, 0.01])]
    horizon_sessions = int(config.get("selected_label", {}).get("horizon_sessions", 20))
    cache = qfq_cache if qfq_cache is not None else {}
    rows: list[dict[str, Any]] = []
    events = events.copy()
    for inst, group in events.groupby("instrument", dropna=False):
        inst_text = str(inst)
        if inst_text in cache:
            bars = cache[inst_text]
        else:
            path = qfq_path(qfq_dir, inst_text)
            bars = load_qfq_bars(path) if path.exists() else None
            cache[inst_text] = bars
        for idx, row in group.iterrows():
            entry_pos = int(float(row.get("entry_pos"))) if pd.notna(row.get("entry_pos")) else -1
            for k in k_grid:
                target_pos = entry_pos + int(k)
                delayed_pos, forward_shift, executable = find_delayed_entry_pos(
                    bars,
                    target_pos,
                    max_shift,
                    inst_text,
                    executable_dates_by_instrument,
                )
                early = early_path_features(row, bars, int(k), delayed_pos)
                early_end = early["early_path_window_end_pos"]
                for horizon_mode in horizon_modes:
                    if horizon_mode == HORIZON_FROM_ENTRY:
                        planned_label_end = delayed_pos + horizon_sessions - 1 if pd.notna(delayed_pos) else np.nan
                    elif horizon_mode == HORIZON_CALENDAR_T0:
                        planned_label_end = entry_pos + horizon_sessions - 1 if entry_pos >= 0 else np.nan
                    else:
                        planned_label_end = np.nan
                    disjoint = bool(pd.notna(delayed_pos) and pd.notna(early_end) and delayed_pos > early_end)
                    label = delayed_label(row, bars, delayed_pos, planned_label_end, costs)
                    payload = {
                        "base_index": idx,
                        "row_id": row.get("row_id", idx),
                        "instrument": inst_text,
                        "reference_date": row.get("reference_date", ""),
                        "entry_pos": float(entry_pos) if entry_pos >= 0 else np.nan,
                        "t0_entry_price": row.get("entry_price", np.nan),
                        "early_path_k": int(k),
                        "horizon_mode": horizon_mode,
                        "delayed_entry_target_pos": float(target_pos),
                        "delayed_entry_pos": delayed_pos,
                        "delayed_entry_forward_shift": forward_shift,
                        "delayed_entry_executable": bool(executable),
                        "delayed_label_start_pos": delayed_pos,
                        "delayed_label_end_pos": planned_label_end,
                        "label_window_disjoint": disjoint,
                        "upper_barrier": row.get("upper_barrier", np.nan),
                        "lower_barrier": row.get("lower_barrier", np.nan),
                        "winner_positive": boolish(row.get("winner_positive", False)),
                        "fast_fail": boolish(row.get("fast_fail", False)),
                        "row_utility_component_0bps": row.get("row_utility_component_0bps", np.nan),
                        "row_utility_component_50bps": row.get("row_utility_component_50bps", np.nan),
                        "row_utility_component_100bps": row.get("row_utility_component_100bps", np.nan),
                    }
                    payload.update(early)
                    payload.update(label)
                    rows.append(payload)
    path_panel = pd.DataFrame(rows)
    if path_panel.empty:
        events["max_observable_event_end_pos"] = events["original_t0_event_end_pos"]
        events["event_end_pos"] = events["original_t0_event_end_pos"]
        return events, path_panel
    max_delayed_end = path_panel.groupby("base_index")["delayed_label_end_pos"].max()
    events["max_observable_event_end_pos"] = np.maximum(
        finite_numeric(events["original_t0_event_end_pos"]),
        finite_numeric(events.index.to_series().map(max_delayed_end)),
    )
    events["event_end_pos"] = events["max_observable_event_end_pos"]
    return events, path_panel


def build_early_path_rebuild_audit(path_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    min_fraction = float(config.get("early_path", {}).get("min_early_path_evaluable_fraction", 0.95))
    rows: list[dict[str, Any]] = []
    if path_panel.empty:
        return pd.DataFrame(), "fail", "empty_path_panel"
    for k, sub in path_panel.groupby("early_path_k"):
        row_count = int(sub["row_id"].nunique())
        eval_n = int(sub.loc[sub["early_path_evaluable"].astype(bool), "row_id"].nunique())
        if {"delayed_entry_executable", "delayed_label_evaluable"} <= set(sub.columns):
            disjoint_scope = sub.loc[
                sub["delayed_entry_executable"].astype(bool)
                & sub["delayed_label_evaluable"].astype(bool)
            ]
        else:
            disjoint_scope = sub
        disjoint_ok = bool(disjoint_scope["label_window_disjoint"].fillna(False).all())
        target_ok = bool((finite_numeric(sub["delayed_entry_target_pos"]) >= finite_numeric(sub["entry_pos"]) + int(k)).all())
        frac = eval_n / row_count if row_count else 0.0
        status = "pass" if frac >= min_fraction and disjoint_ok and target_ok else "fail"
        rows.append(
            {
                "early_path_k": int(k),
                "row_count": row_count,
                "early_path_evaluable_n": eval_n,
                "early_path_window_start_min_pos": float(finite_numeric(sub["early_path_window_start_pos"]).min()),
                "early_path_window_end_max_pos": float(finite_numeric(sub["early_path_window_end_pos"]).max()),
                "delayed_entry_target_pos_check_status": "pass" if target_ok else "fail",
                "label_window_disjoint_status": "pass" if disjoint_ok else "fail",
                "barrier_uses_t0_volatility_status": "pass",
                "lookahead_column_count": 0,
                "early_path_pit_gate_status": status,
            }
        )
    audit = pd.DataFrame(rows)
    failed = audit.loc[audit["early_path_pit_gate_status"].astype(str).ne("pass")]
    return audit, ("pass" if failed.empty else "fail"), ";".join(failed["early_path_k"].astype(str).tolist())


def build_delayed_entry_executability_audit(path_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    max_fraction = float(config.get("early_path", {}).get("delayed_entry_not_executable_max_fraction", 0.10))
    primary_k = int(config.get("early_path", {}).get("primary_k", 3))
    primary_mode = str(config.get("early_path", {}).get("primary_horizon_mode", HORIZON_FROM_ENTRY))
    rows: list[dict[str, Any]] = []
    if path_panel.empty:
        return pd.DataFrame(), "fail", "empty_path_panel"
    for (k, mode), sub in path_panel.groupby(["early_path_k", "horizon_mode"]):
        event_n = int(sub["row_id"].nunique())
        not_exec = int((~sub["delayed_entry_executable"].astype(bool)).sum())
        shifted = int(finite_numeric(sub["delayed_entry_forward_shift"]).fillna(0).gt(0).sum())
        missing_label = int((~sub["delayed_label_evaluable"].astype(bool)).sum())
        frac = not_exec / event_n if event_n else 1.0
        status = "pass" if frac <= max_fraction else "fail"
        rows.append(
            {
                "early_path_k": int(k),
                "horizon_mode": mode,
                "evaluable_n": int(sub["delayed_label_evaluable"].astype(bool).sum()),
                "not_executable_n": not_exec,
                "forward_shifted_entry_n": shifted,
                "missing_label_horizon_n": missing_label,
                "not_executable_fraction": frac,
                "delayed_entry_executability_gate_status": status,
            }
        )
    audit = pd.DataFrame(rows)
    primary = audit.loc[audit["early_path_k"].eq(primary_k) & audit["horizon_mode"].eq(primary_mode)]
    if primary.empty:
        return audit, "fail", "primary_executability_row_missing"
    status = str(primary.iloc[0]["delayed_entry_executability_gate_status"])
    return audit, status, "" if status == "pass" else "primary_not_executable_fraction_exceeded"


def exact_uniqueness_from_span(events: pd.DataFrame) -> tuple[pd.Series, list[int], str]:
    if events.empty:
        return pd.Series(dtype=float), [], "pass_with_exact_t1"
    if not {"instrument", "event_start_pos", "event_end_pos"} <= set(events.columns):
        return pd.Series(np.nan, index=events.index, dtype=float), [], "exact_uniqueness_unavailable"
    start = finite_numeric(events["event_start_pos"])
    end = finite_numeric(events["event_end_pos"])
    valid = start.notna() & end.notna() & end.ge(start)
    if not bool(valid.all()):
        return pd.Series(np.nan, index=events.index, dtype=float), [], "exact_uniqueness_unavailable"
    spans: list[tuple[Any, str, int, int]] = []
    counts: dict[tuple[str, int], int] = {}
    for idx, inst, s, e in zip(events.index, events["instrument"].astype(str), start.astype(int), end.astype(int)):
        spans.append((idx, inst, int(s), int(e)))
        for pos in range(int(s), int(e) + 1):
            key = (inst, pos)
            counts[key] = counts.get(key, 0) + 1
    uniqueness: dict[Any, float] = {}
    concurrency_values: list[int] = []
    for idx, inst, s, e in spans:
        active = [counts[(inst, pos)] for pos in range(s, e + 1)]
        concurrency_values.extend(active)
        uniqueness[idx] = float(np.mean([1.0 / x for x in active])) if active else np.nan
    return pd.Series(uniqueness).reindex(events.index), concurrency_values, "pass_with_exact_t1"


def fold_sample_uniqueness_status(train: pd.DataFrame, test: pd.DataFrame, train_status: str, config: dict[str, Any]) -> str:
    protocol = config.get("fold_protocol", {})
    min_train = int(protocol.get("min_effective_train_event_n_per_fold", 300))
    min_test = int(protocol.get("min_effective_test_event_n_per_fold", 50))
    if train_status != "pass_with_exact_t1":
        return "exact_uniqueness_unavailable"
    if len(train) < min_train or len(test) < min_test:
        return "purged_cv_integrity_caveat"
    return "pass_with_exact_t1"


def sample_uniqueness_gate_status(uniqueness: pd.DataFrame) -> str:
    if uniqueness.empty or "sample_uniqueness_gate_status" not in uniqueness.columns:
        return "exact_uniqueness_unavailable"
    statuses = set(uniqueness["sample_uniqueness_gate_status"].astype(str).tolist())
    if "exact_uniqueness_unavailable" in statuses:
        return "exact_uniqueness_unavailable"
    if "purged_cv_integrity_caveat" in statuses:
        return "purged_cv_integrity_caveat"
    if statuses == {"pass_with_exact_t1"}:
        return "pass_with_exact_t1"
    return "exact_uniqueness_unavailable"


@dataclass
class DelayedModel:
    spec: Any
    model: Any | None
    constant_probability: float | None


def delayed_model_features(config: dict[str, Any]) -> list[str]:
    features = list(EARLY_FEATURES)
    if bool(config.get("model", {}).get("include_t0_context_features", False)):
        features.extend(required_feature_columns(config))
    return list(dict.fromkeys(features))


def fit_delayed_model(
    train_path: pd.DataFrame,
    sample_weight_by_row_id: dict[Any, float],
    config: dict[str, Any],
) -> DelayedModel:
    trainable = train_path.loc[
        train_path["delayed_label_evaluable"].astype(bool)
        & train_path["delayed_entry_executable"].astype(bool)
        & train_path["early_path_evaluable"].astype(bool)
    ].copy()
    features = [c for c in delayed_model_features(config) if c in trainable.columns]
    spec = r13c.fit_design_spec(trainable, features)
    if trainable.empty:
        return DelayedModel(spec, None, 0.0)
    y = bool_series(trainable["delayed_winner_positive"]).astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        return DelayedModel(spec, None, float(y.mean()) if len(y) else 0.0)
    x = r13c.transform_design(trainable, spec)
    weights = trainable["row_id"].map(sample_weight_by_row_id).fillna(1.0).to_numpy(dtype=float)
    params = config.get("model", {}).get("logistic_l2", {})
    model = LogisticRegression(
        C=float(params.get("C", 0.5)),
        penalty=str(params.get("penalty", "l2")),
        solver=str(params.get("solver", "liblinear")),
        max_iter=int(params.get("max_iter", 200)),
    )
    model.fit(x, y, sample_weight=weights)
    return DelayedModel(spec, model, None)


def predict_delayed_model(fit: DelayedModel, frame: pd.DataFrame) -> np.ndarray:
    if fit.model is None:
        return np.full(len(frame), float(fit.constant_probability or 0.0), dtype=float)
    x = r13c.transform_design(frame, fit.spec)
    return fit.model.predict_proba(x)[:, 1]


def selected_for_model(scores: np.ndarray, candidates: pd.Series, top_fraction: float, denominator_n: int) -> pd.Series:
    selected = pd.Series(False, index=candidates.index)
    candidate_idx = candidates.index[candidates.astype(bool)]
    if len(candidate_idx) == 0 or denominator_n <= 0:
        return selected
    top_n = min(len(candidate_idx), max(1, int(round(float(top_fraction) * denominator_n))))
    score_s = pd.Series(scores, index=candidates.index).loc[candidate_idx]
    chosen = score_s.sort_values(ascending=False, kind="mergesort").head(top_n).index
    selected.loc[chosen] = True
    return selected


def arm_metrics(test_path: pd.DataFrame, arm: str, selected: pd.Series) -> dict[str, Any]:
    event_n = len(test_path)
    selected = selected.reindex(test_path.index).fillna(False).astype(bool)
    if arm == "arm_t0_baseline":
        util0 = finite_numeric(test_path["row_utility_component_0bps"])
        util50 = finite_numeric(test_path["row_utility_component_50bps"])
        util100 = finite_numeric(test_path["row_utility_component_100bps"])
        winner = bool_series(test_path["winner_positive"])
        fast_fail = bool_series(test_path["fast_fail"]) if "fast_fail" in test_path else pd.Series(False, index=test_path.index)
        selected = pd.Series(True, index=test_path.index)
    else:
        util0 = finite_numeric(test_path["delayed_row_utility_component_0bps"]).where(selected, 0.0).fillna(0.0)
        util50 = finite_numeric(test_path["delayed_row_utility_component_50bps"]).where(selected, 0.0).fillna(0.0)
        util100 = finite_numeric(test_path["delayed_row_utility_component_100bps"]).where(selected, 0.0).fillna(0.0)
        winner = bool_series(test_path["delayed_winner_positive"])
        fast_fail = bool_series(test_path["delayed_fast_fail"])
    selected_n = int(selected.sum())
    selected_util50 = util50.loc[selected]
    missed = bool_series(test_path["early_path_touched_upper_barrier_flag"])
    early_lower = bool_series(test_path["early_path_touched_lower_barrier_flag"])
    t0_util50 = finite_numeric(test_path["row_utility_component_50bps"]).fillna(0.0)
    missed_cost = float((t0_util50.loc[missed] - util50.loc[missed]).sum() / event_n) if event_n else np.nan
    return {
        "evaluable_n": int(
            bool_series(test_path.get("delayed_label_evaluable", pd.Series(True, index=test_path.index))).sum()
        )
        if arm != "arm_t0_baseline"
        else event_n,
        "selected_n": selected_n,
        "selected_fraction": selected_n / event_n if event_n else np.nan,
        "winner_rate": float(winner.loc[selected].mean()) if selected_n else np.nan,
        "fast_fail_rate": float(fast_fail.loc[selected].mean()) if selected_n else np.nan,
        "utility_per_event_mean_0bps": float(util0.mean()) if event_n else np.nan,
        "utility_per_event_mean_50bps": float(util50.mean()) if event_n else np.nan,
        "utility_per_event_mean_100bps": float(util100.mean()) if event_n else np.nan,
        "utility_per_selected_entry_mean_50bps": float(selected_util50.mean()) if selected_n else np.nan,
        "utility_per_event_median_50bps": float(util50.median()) if event_n else np.nan,
        "missed_upper_in_window_n": int(missed.sum()),
        "early_lower_in_window_n": int(early_lower.sum()),
        "missed_upper_opportunity_cost_50bps": missed_cost,
    }


def build_train_kfold_outputs(
    events: pd.DataFrame,
    path_panel: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    protocol = config.get("fold_protocol", {})
    fold_n = int(protocol.get("fold_n", 5))
    top_fraction = float(config.get("model", {}).get("top_fraction", 0.50))
    state_id = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    folded = r13e.assign_chronological_folds(events, fold_n)
    fold_metrics: list[dict[str, Any]] = []
    uniqueness_rows: list[dict[str, Any]] = []
    fold_payloads: list[tuple[int, pd.DataFrame, pd.DataFrame, pd.Series, int, int]] = []
    for fold_id in sorted(folded["fold_id"].unique()):
        train, test, purged_n, embargoed_n = r13e.purged_train_for_fold(folded, int(fold_id), config)
        train_uniqueness, train_concurrency, train_exact = exact_uniqueness_from_span(train)
        test_uniqueness, test_concurrency, test_exact = exact_uniqueness_from_span(test)
        sample_status = fold_sample_uniqueness_status(train, test, train_exact, config)
        uniqueness_rows.append(
            {
                "state_id": state_id,
                "fold_id": int(fold_id),
                "event_n": len(test),
                "t1_reconstruction_status": "exact_t1_reconstructed"
                if train_exact == "pass_with_exact_t1" and test_exact == "pass_with_exact_t1"
                else "t1_unavailable",
                "purged_rows_n": purged_n,
                "embargoed_rows_n": embargoed_n,
                "effective_train_event_n": len(train),
                "effective_test_event_n": len(test),
                "train_mean_average_uniqueness": float(train_uniqueness.mean()) if len(train_uniqueness) else np.nan,
                "train_median_average_uniqueness": float(train_uniqueness.median()) if len(train_uniqueness) else np.nan,
                "train_p10_average_uniqueness": float(train_uniqueness.quantile(0.10)) if len(train_uniqueness) else np.nan,
                "train_mean_concurrency": float(np.mean(train_concurrency)) if train_concurrency else np.nan,
                "train_p95_concurrency": float(np.quantile(train_concurrency, 0.95)) if train_concurrency else np.nan,
                "test_mean_average_uniqueness": float(test_uniqueness.mean()) if len(test_uniqueness) else np.nan,
                "test_mean_concurrency": float(np.mean(test_concurrency)) if test_concurrency else np.nan,
                "sample_uniqueness_gate_status": sample_status,
            }
        )
        fold_payloads.append((int(fold_id), train, test, train_uniqueness, purged_n, embargoed_n))
    uniqueness = pd.DataFrame(uniqueness_rows)
    if sample_uniqueness_gate_status(uniqueness) != "pass_with_exact_t1":
        return pd.DataFrame(fold_metrics), uniqueness

    for fold_id, train, test, train_uniqueness, purged_n, embargoed_n in fold_payloads:
        train_ids = set(train["row_id"].tolist())
        test_ids = set(test["row_id"].tolist())
        sample_weight_by_row_id = dict(zip(train["row_id"], train_uniqueness))
        for (k, mode), path_sub in path_panel.groupby(["early_path_k", "horizon_mode"]):
            train_path = path_sub.loc[path_sub["row_id"].isin(train_ids)].copy()
            test_path = path_sub.loc[path_sub["row_id"].isin(test_ids)].copy()
            if test_path.empty:
                continue
            base_selected = pd.Series(True, index=test_path.index)
            row = {
                "fold_id": int(fold_id),
                "early_path_k": int(k),
                "horizon_mode": mode,
                "arm": "arm_t0_baseline",
                "event_n": len(test_path),
                "purged_rows_n": purged_n,
                "embargoed_rows_n": embargoed_n,
                "sample_weight_source": "fold_local_exact_13f_max_event_span_average_uniqueness",
            }
            row.update(arm_metrics(test_path, "arm_t0_baseline", base_selected))
            fold_metrics.append(row)

            gate_selected = (
                test_path["delayed_entry_executable"].astype(bool)
                & test_path["delayed_label_evaluable"].astype(bool)
                & (~test_path["early_path_touched_lower_barrier_flag"].astype(bool))
            )
            row = {
                "fold_id": int(fold_id),
                "early_path_k": int(k),
                "horizon_mode": mode,
                "arm": "arm_gate_delayed",
                "event_n": len(test_path),
                "purged_rows_n": purged_n,
                "embargoed_rows_n": embargoed_n,
                "sample_weight_source": "fold_local_exact_13f_max_event_span_average_uniqueness",
            }
            row.update(arm_metrics(test_path, "arm_gate_delayed", gate_selected))
            fold_metrics.append(row)

            fit = fit_delayed_model(train_path, sample_weight_by_row_id, config)
            candidates = (
                test_path["delayed_entry_executable"].astype(bool)
                & test_path["delayed_label_evaluable"].astype(bool)
                & test_path["early_path_evaluable"].astype(bool)
            )
            scores = predict_delayed_model(fit, test_path)
            model_selected = selected_for_model(scores, candidates, top_fraction, len(test_path))
            row = {
                "fold_id": int(fold_id),
                "early_path_k": int(k),
                "horizon_mode": mode,
                "arm": "arm_model_delayed",
                "event_n": len(test_path),
                "purged_rows_n": purged_n,
                "embargoed_rows_n": embargoed_n,
                "sample_weight_source": "fold_local_exact_13f_max_event_span_average_uniqueness",
            }
            row.update(arm_metrics(test_path, "arm_model_delayed", model_selected))
            fold_metrics.append(row)
    return pd.DataFrame(fold_metrics), uniqueness


def build_delayed_vs_t0_comparison(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if fold_metrics.empty:
        return pd.DataFrame()
    for (k, mode, arm), sub in fold_metrics.groupby(["early_path_k", "horizon_mode", "arm"]):
        base = fold_metrics.loc[
            fold_metrics["early_path_k"].eq(k)
            & fold_metrics["horizon_mode"].eq(mode)
            & fold_metrics["arm"].eq("arm_t0_baseline")
        ][["fold_id", "utility_per_event_mean_50bps"]].rename(columns={"utility_per_event_mean_50bps": "t0_utility"})
        gate = fold_metrics.loc[
            fold_metrics["early_path_k"].eq(k)
            & fold_metrics["horizon_mode"].eq(mode)
            & fold_metrics["arm"].eq("arm_gate_delayed")
        ][["fold_id", "utility_per_event_mean_50bps"]].rename(columns={"utility_per_event_mean_50bps": "gate_utility"})
        merged = sub.merge(base, on="fold_id", how="left").merge(gate, on="fold_id", how="left")
        util = finite_numeric(sub["utility_per_event_mean_50bps"])
        delta_vs_t0 = finite_numeric(merged["utility_per_event_mean_50bps"]) - finite_numeric(merged["t0_utility"])
        delta_vs_gate = finite_numeric(merged["utility_per_event_mean_50bps"]) - finite_numeric(merged["gate_utility"])
        delta_mean = float(delta_vs_t0.mean()) if delta_vs_t0.notna().any() else np.nan
        sign_count = int(delta_vs_t0.gt(0).sum())
        status = "improved_vs_t0" if pd.notna(delta_mean) and delta_mean > 0 and sign_count >= 3 else "no_improvement_vs_t0"
        if arm == "arm_model_delayed" and pd.notna(float(delta_vs_gate.mean())) and float(delta_vs_gate.mean()) > 0:
            status = status + "_and_gate"
        rows.append(
            {
                "early_path_k": int(k),
                "horizon_mode": mode,
                "arm": arm,
                "fold_mean_utility_per_event_mean_50bps": float(util.mean()) if util.notna().any() else np.nan,
                "fold_std_utility_per_event_mean_50bps": fold_std(util),
                "fold_mean_utility_per_selected_entry_mean_50bps": float(finite_numeric(sub["utility_per_selected_entry_mean_50bps"]).mean()),
                "fold_mean_utility_per_event_median_50bps": float(finite_numeric(sub["utility_per_event_median_50bps"]).mean()),
                "fold_mean_winner_rate": float(finite_numeric(sub["winner_rate"]).mean()),
                "fold_mean_fast_fail_rate": float(finite_numeric(sub["fast_fail_rate"]).mean()),
                "fold_mean_selected_fraction": float(finite_numeric(sub["selected_fraction"]).mean()),
                "fold_mean_missed_upper_fraction": float((finite_numeric(sub["missed_upper_in_window_n"]) / finite_numeric(sub["event_n"]).replace(0, np.nan)).mean()),
                "delta_utility_per_event_mean_50bps_vs_t0": delta_mean,
                "delta_utility_per_event_mean_50bps_vs_gate": float(delta_vs_gate.mean()) if delta_vs_gate.notna().any() else np.nan,
                "missed_upper_opportunity_cost_50bps": float(finite_numeric(sub["missed_upper_opportunity_cost_50bps"]).mean()),
                "delta_sign_consistency_folds": sign_count,
                "comparison_status": status,
            }
        )
    return pd.DataFrame(rows)


def build_missed_winner_accounting(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if fold_metrics.empty:
        return pd.DataFrame()
    for (k, mode, fold_id), sub in fold_metrics.groupby(["early_path_k", "horizon_mode", "fold_id"]):
        base = sub.loc[sub["arm"].eq("arm_t0_baseline")]
        if base.empty:
            continue
        t0_utility = float(base.iloc[0]["utility_per_event_mean_50bps"])
        t0_selected = float(base.iloc[0]["utility_per_selected_entry_mean_50bps"])
        for _, row in sub.iterrows():
            same_delta = float(row["utility_per_event_mean_50bps"]) - t0_utility
            selected_delta = float(row["utility_per_selected_entry_mean_50bps"]) - t0_selected if pd.notna(row["utility_per_selected_entry_mean_50bps"]) else np.nan
            rows.append(
                {
                    "early_path_k": int(k),
                    "horizon_mode": mode,
                    "arm": row["arm"],
                    "fold_id": int(fold_id),
                    "event_n": int(row["event_n"]),
                    "missed_upper_in_window_n": int(row["missed_upper_in_window_n"]),
                    "early_lower_in_window_n": int(row["early_lower_in_window_n"]),
                    "missed_upper_fraction": float(row["missed_upper_in_window_n"]) / float(row["event_n"]) if row["event_n"] else np.nan,
                    "missed_upper_opportunity_cost_50bps": row["missed_upper_opportunity_cost_50bps"],
                    "same_event_delta_utility_50bps_vs_t0": same_delta,
                    "selected_entry_only_delta_utility_50bps_vs_t0": selected_delta,
                    "missed_winner_offset_gate_status": "pass" if same_delta > 0 else "fail",
                }
            )
    return pd.DataFrame(rows)


def build_search_audit(config: dict[str, Any]) -> pd.DataFrame:
    ep = config.get("early_path", {})
    k_grid = ep.get("k_grid", [2, 3, 5, 8, 13])
    horizon_modes = ep.get("horizon_modes", [HORIZON_FROM_ENTRY, HORIZON_CALENDAR_T0])
    return pd.DataFrame(
        [
            {
                "selected_state_id": str(config.get("selected_state_id", "repair_range_participation_core_30")),
                "posthoc_after_13e_report": True,
                "validation_used_in_13f": False,
                "robustness_used_in_13f": False,
                "early_path_k_grid": json.dumps(k_grid),
                "horizon_mode_n": len(horizon_modes),
                "arm_n": len(ARMS),
                "primary_k": int(ep.get("primary_k", 3)),
                "primary_horizon_mode": str(ep.get("primary_horizon_mode", HORIZON_FROM_ENTRY)),
                "primary_arm": str(ep.get("primary_arm", "arm_model_delayed")),
                "effective_search_space_n": int(len(k_grid) * len(horizon_modes) * len(ARMS)),
                "hyperparameter_search_used": False,
                "oos_used_for_selection": False,
                "confirmatory_status": False,
                "search_accounting_status": "diagnostic_train_only_not_confirmatory",
            }
        ]
    )


def utility_gate_pass(comparison: pd.DataFrame, arm: str, config: dict[str, Any]) -> bool:
    required = {
        "early_path_k",
        "horizon_mode",
        "arm",
        "fold_mean_utility_per_event_mean_50bps",
        "fold_std_utility_per_event_mean_50bps",
        "delta_utility_per_event_mean_50bps_vs_t0",
        "delta_sign_consistency_folds",
    }
    if comparison.empty or not required <= set(comparison.columns):
        return False
    ep = config.get("early_path", {})
    primary_k = int(ep.get("primary_k", 3))
    primary_mode = str(ep.get("primary_horizon_mode", HORIZON_FROM_ENTRY))
    row = comparison.loc[
        comparison["early_path_k"].eq(primary_k)
        & comparison["horizon_mode"].eq(primary_mode)
        & comparison["arm"].eq(arm)
    ]
    if row.empty:
        return False
    rec = row.iloc[0]
    mean = float(rec.get("fold_mean_utility_per_event_mean_50bps", np.nan))
    std = float(rec.get("fold_std_utility_per_event_mean_50bps", np.nan))
    delta = float(rec.get("delta_utility_per_event_mean_50bps_vs_t0", np.nan))
    sign = int(rec.get("delta_sign_consistency_folds", 0))
    return bool(pd.notna(mean) and pd.notna(std) and pd.notna(delta) and mean > 0 and delta > 0 and mean - std > 0 and sign >= 3)


def primary_model_vs_gate_delta(comparison: pd.DataFrame, config: dict[str, Any]) -> float:
    required = {
        "early_path_k",
        "horizon_mode",
        "arm",
        "delta_utility_per_event_mean_50bps_vs_gate",
    }
    if comparison.empty or not required <= set(comparison.columns):
        return np.nan
    ep = config.get("early_path", {})
    row = comparison.loc[
        comparison["early_path_k"].eq(int(ep.get("primary_k", 3)))
        & comparison["horizon_mode"].eq(str(ep.get("primary_horizon_mode", HORIZON_FROM_ENTRY)))
        & comparison["arm"].eq("arm_model_delayed")
    ]
    if row.empty:
        return np.nan
    return float(row.iloc[0].get("delta_utility_per_event_mean_50bps_vs_gate", np.nan))


def offset_condition(missed: pd.DataFrame, config: dict[str, Any]) -> bool:
    if missed.empty:
        return False
    ep = config.get("early_path", {})
    primary_k = int(ep.get("primary_k", 3))
    primary_mode = str(ep.get("primary_horizon_mode", HORIZON_FROM_ENTRY))
    sub = missed.loc[
        missed["early_path_k"].eq(primary_k)
        & missed["horizon_mode"].eq(primary_mode)
        & missed["arm"].isin(["arm_gate_delayed", "arm_model_delayed"])
    ]
    if sub.empty:
        return False
    selected_delta = finite_numeric(sub["selected_entry_only_delta_utility_50bps_vs_t0"])
    same_delta = finite_numeric(sub["same_event_delta_utility_50bps_vs_t0"])
    return bool((selected_delta.gt(0) & same_delta.le(0)).any())


def build_decision(
    input_status: str,
    upstream_status: str,
    label_status: str,
    row_status: str,
    early_path_status: str,
    executable_status: str,
    purged_status: str,
    uniqueness_status: str,
    comparison: pd.DataFrame,
    missed: pd.DataFrame,
    search: pd.DataFrame,
    config: dict[str, Any],
    primary_failure_reason: str = "",
) -> pd.DataFrame:
    ep = config.get("early_path", {})
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    gate_pass = utility_gate_pass(comparison, "arm_gate_delayed", config)
    model_pass = utility_gate_pass(comparison, "arm_model_delayed", config)
    model_delta = primary_model_vs_gate_delta(comparison, config)
    offset = offset_condition(missed, config)

    utility_status = "fail"
    missed_status = "fail"
    decision_state = "13F_stop_no_delayed_utility_improvement"
    reason = "delayed_utility_improvement_gate_failed"
    capacity = "delayed_entry_no_utility_signal"
    if input_status != "pass":
        decision_state = "13F_blocked_input_or_lineage_failure"
        reason = primary_failure_reason or "input_or_lineage_failure"
    elif upstream_status != "pass":
        decision_state = "13F_blocked_upstream_lineage_failure"
        reason = primary_failure_reason or "upstream_lineage_failure"
    elif label_status != "pass":
        decision_state = "13F_blocked_label_lineage_failure"
        reason = primary_failure_reason or "label_lineage_failure"
    elif row_status != "pass":
        decision_state = "13F_blocked_row_level_rebuild_failure"
        reason = primary_failure_reason or "row_level_rebuild_failure"
    elif early_path_status != "pass":
        decision_state = "13F_blocked_early_path_pit_failure"
        reason = primary_failure_reason or "early_path_pit_failure"
    elif executable_status != "pass":
        decision_state = "13F_blocked_delayed_entry_not_executable"
        reason = primary_failure_reason or "delayed_entry_not_executable"
    elif purged_status != "pass":
        decision_state = "13F_blocked_purged_cv_integrity_failure"
        reason = primary_failure_reason or "purged_cv_integrity_failure"
    elif uniqueness_status == "exact_uniqueness_unavailable":
        decision_state = "13F_stop_uniqueness_unavailable_for_downstream"
        reason = "exact_t1_unavailable_for_13f_max_event_span"
    elif not gate_pass and not model_pass:
        decision_state = "13F_stop_no_delayed_utility_improvement"
        reason = "delayed_utility_improvement_gate_failed"
        capacity = "delayed_entry_no_utility_signal"
    elif offset:
        decision_state = "13F_stop_delayed_improvement_offset_by_missed_winners"
        reason = "selected_entry_improvement_offset_by_same_event_denominator"
        capacity = "delayed_entry_offset_by_missed_winners"
    elif model_pass and pd.notna(model_delta) and model_delta > 0:
        decision_state = "13F_diagnostic_delayed_entry_utility_signal_present"
        reason = "model_delayed_same_event_utility_gate_passed"
        capacity = "delayed_entry_model_utility_signal_present"
        utility_status = "pass"
        missed_status = "pass"
    elif gate_pass:
        decision_state = "13F_diagnostic_delayed_gate_effect_only"
        reason = "gate_delayed_improved_without_model_edge"
        capacity = "delayed_entry_gate_effect_only"
        utility_status = "gate_effect_only_no_model_edge"
        missed_status = "pass"
    else:
        missed_status = "fail"

    if decision_state.startswith("13F_blocked"):
        capacity = "delayed_entry_no_utility_signal"
    search_status = str(search.iloc[0]["search_accounting_status"]) if len(search) else "diagnostic_train_only_not_confirmatory"
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": "none",
                "sequence_mining_authorized": False,
                "meta_labeling_authorized": False,
                "bet_sizing_authorized": False,
                "selected_state_id": selected,
                "primary_k": int(ep.get("primary_k", 3)),
                "primary_horizon_mode": str(ep.get("primary_horizon_mode", HORIZON_FROM_ENTRY)),
                "primary_arm": str(ep.get("primary_arm", "arm_model_delayed")),
                "effect_interpretation": "train_only_delayed_entry_diagnostic",
                "confirmatory_status": False,
                "input_gate_status": input_status,
                "upstream_lineage_gate_status": upstream_status,
                "row_level_rebuild_gate_status": row_status,
                "early_path_pit_gate_status": early_path_status,
                "delayed_entry_executability_gate_status": executable_status,
                "purged_cv_integrity_gate_status": purged_status,
                "delayed_utility_improvement_gate_status": utility_status,
                "missed_winner_offset_gate_status": missed_status,
                "sample_uniqueness_gate_status": uniqueness_status,
                "validation_used_in_13f": False,
                "robustness_used_in_13f": False,
                "search_accounting_status": search_status,
                "primary_failure_reason": reason,
                "delayed_entry_capacity_readout": capacity,
            }
        ]
    )


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_无记录_"
    existing = [c for c in cols if c in df.columns]
    return df[existing].head(max_rows).to_markdown(index=False)


def render_report(
    decision: pd.DataFrame,
    comparison: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    missed: pd.DataFrame,
    uniqueness: pd.DataFrame,
    early_audit: pd.DataFrame,
    exec_audit: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    dec = decision.iloc[0]
    pk = int(dec["primary_k"])
    pm = str(dec["primary_horizon_mode"])
    if {"early_path_k", "horizon_mode"} <= set(comparison.columns):
        primary = comparison.loc[comparison["early_path_k"].eq(pk) & comparison["horizon_mode"].eq(pm)]
    else:
        primary = pd.DataFrame()
    sensitivity = (
        comparison.sort_values(["early_path_k", "horizon_mode", "arm"], kind="mergesort")
        if not comparison.empty and {"early_path_k", "horizon_mode", "arm"} <= set(comparison.columns)
        else comparison
    )
    missed_primary = (
        missed.loc[missed["early_path_k"].eq(pk) & missed["horizon_mode"].eq(pm)]
        if {"early_path_k", "horizon_mode"} <= set(missed.columns)
        else pd.DataFrame()
    )
    fold_primary = (
        fold_metrics.loc[fold_metrics["early_path_k"].eq(pk) & fold_metrics["horizon_mode"].eq(pm)]
        if {"early_path_k", "horizon_mode"} <= set(fold_metrics.columns)
        else pd.DataFrame()
    )
    lines = [
        "# 13F Early-Path Confirmation Delayed-Entry Train Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"单行裁决：`decision_state = {dec['decision_state']}`；`delayed_entry_capacity_readout = {dec['delayed_entry_capacity_readout']}`。本读数是 train-only diagnostic，不授权 sequence mining、meta-labeling、bet sizing 或任何 next requirement。",
        "",
        f"- selected_state_id: `{dec['selected_state_id']}`",
        f"- primary comparison: `k={pk}`, `{pm}`, `{dec['primary_arm']}`",
        f"- primary_failure_reason: `{dec['primary_failure_reason']}`",
        f"- next_allowed_requirement: `{dec['next_allowed_requirement']}`",
        "",
        "13F 不推翻 13C/13E。13C/13E 否决的是 t0 winner entry / nonlinear winner capacity；13F 只检查 event 发生后先观察 early path、再延迟入场是否能改善 train-fold same-event after-cost utility。",
        "",
        "## Train-Only / Search Accounting",
        "",
        md_table(search, ["selected_state_id", "validation_used_in_13f", "robustness_used_in_13f", "early_path_k_grid", "horizon_mode_n", "arm_n", "primary_k", "primary_horizon_mode", "primary_arm", "effective_search_space_n", "search_accounting_status"]),
        "",
        "## PIT Early Path 与 Delayed Entry 审计",
        "",
        md_table(early_audit, ["early_path_k", "row_count", "early_path_evaluable_n", "label_window_disjoint_status", "barrier_uses_t0_volatility_status", "lookahead_column_count", "early_path_pit_gate_status"], 10),
        "",
        md_table(exec_audit, ["early_path_k", "horizon_mode", "evaluable_n", "not_executable_n", "forward_shifted_entry_n", "missing_label_horizon_n", "not_executable_fraction", "delayed_entry_executability_gate_status"], 15),
        "",
        "Utility 口径：delayed arm 在 early_path_window 内尚未持仓，收益计 0；未进场、not-executable、missed-upper 样本保留在 same-event 分母内。selected-entry utility 和 median utility 只作诊断，不替代主 gate。",
        "",
        "## 主对照与 Sensitivity",
        "",
        md_table(primary, ["arm", "fold_mean_utility_per_event_mean_50bps", "fold_std_utility_per_event_mean_50bps", "fold_mean_utility_per_selected_entry_mean_50bps", "fold_mean_utility_per_event_median_50bps", "fold_mean_winner_rate", "fold_mean_fast_fail_rate", "fold_mean_selected_fraction", "fold_mean_missed_upper_fraction", "delta_utility_per_event_mean_50bps_vs_t0", "delta_utility_per_event_mean_50bps_vs_gate", "delta_sign_consistency_folds", "comparison_status"], 10),
        "",
        "完整 sensitivity readout（非主对照只作线索，不得升级 decision）：",
        "",
        md_table(sensitivity, ["early_path_k", "horizon_mode", "arm", "fold_mean_utility_per_event_mean_50bps", "fold_std_utility_per_event_mean_50bps", "delta_utility_per_event_mean_50bps_vs_t0", "delta_utility_per_event_mean_50bps_vs_gate", "delta_sign_consistency_folds", "comparison_status"], 40),
        "",
        "## Missed-Winner 会计",
        "",
        md_table(missed_primary, ["fold_id", "arm", "event_n", "missed_upper_in_window_n", "missed_upper_fraction", "missed_upper_opportunity_cost_50bps", "same_event_delta_utility_50bps_vs_t0", "selected_entry_only_delta_utility_50bps_vs_t0", "missed_winner_offset_gate_status"], 20),
        "",
        "## Fold-Level 明细",
        "",
        md_table(fold_primary, ["fold_id", "arm", "event_n", "selected_n", "selected_fraction", "winner_rate", "fast_fail_rate", "utility_per_event_mean_50bps", "utility_per_selected_entry_mean_50bps", "utility_per_event_median_50bps", "missed_upper_in_window_n"], 30),
        "",
        "## Sample Uniqueness",
        "",
        md_table(uniqueness, ["fold_id", "event_n", "t1_reconstruction_status", "purged_rows_n", "embargoed_rows_n", "effective_train_event_n", "effective_test_event_n", "train_mean_average_uniqueness", "test_mean_average_uniqueness", "sample_uniqueness_gate_status"], 10),
        "",
        "## Interpretation Boundary",
        "",
        "若 diagnostic positive，它仍只是人工讨论线索；若 negative，应按 no utility improvement、missed-winner offset、PIT/executability failure、CV integrity failure 或 uniqueness failure 分类。任何结论都不得写成 deployable alpha、confirmed edge、OOS validated、holding policy validated 或 bet sizing ready。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if key != "manifest"}


def build_manifest(
    config_path: Path,
    config: dict[str, Any],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
) -> dict[str, Any]:
    publishable = publishable_manifest_outputs(outputs)
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": r13a.git_revision(REPO_ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "output_hashes": {key: file_sha(path) for key, path in publishable.items()},
        "publishable_outputs": {key: str(path) for key, path in publishable.items()},
        "local_cache_outputs_excluded": [],
        "local_cache_audit": [],
    }


def empty_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    upstream, upstream_status, upstream_reason = build_upstream_lineage_audit(resolved, config)
    write_df(outputs["upstream_lineage_audit"], upstream)
    search = build_search_audit(config)
    write_df(outputs["search_multiplicity_audit"], search)

    early_audit, exec_audit, fold_metrics, comparison, missed, uniqueness = empty_outputs()
    row_status = "fail"
    row_reason = ""
    label_status = "fail"
    label_reason = ""
    early_status = "fail"
    early_reason = ""
    exec_status = "fail"
    exec_reason = ""
    purged_status = "fail"
    uniqueness_status = "exact_uniqueness_unavailable"

    if check_inputs_only or mode == "check-inputs":
        row_audit = pd.DataFrame([{"row_level_rebuild_gate_status": "not_run_check_inputs_only"}])
        write_df(outputs["row_level_rebuild_audit"], row_audit)
    elif input_status == "pass" and upstream_status == "pass":
        raw_train = load_train_rows_only(resolved["upstream_13c_morphology_residual_panel_cache"])
        train_events = prepare_train_event_panel(raw_train, config)
        row_audit, row_status, row_reason = build_row_level_rebuild_audit(train_events, config)
        label_status, label_reason = label_lineage_status(train_events, config)
        write_df(outputs["row_level_rebuild_audit"], row_audit)
        if row_status == "pass" and label_status == "pass":
            executable_dates = load_pit_executable_dates(resolved["pit_topn_400_100_executable_daily"])
            train_events, path_panel = reconstruct_event_paths(
                train_events,
                config,
                resolved["stock_daily_qfq_dir"],
                executable_dates_by_instrument=executable_dates,
            )
            early_audit, early_status, early_reason = build_early_path_rebuild_audit(path_panel, config)
            exec_audit, exec_status, exec_reason = build_delayed_entry_executability_audit(path_panel, config)
            if early_status == "pass" and exec_status == "pass":
                fold_metrics, uniqueness = build_train_kfold_outputs(train_events, path_panel, config)
                comparison = build_delayed_vs_t0_comparison(fold_metrics)
                missed = build_missed_winner_accounting(fold_metrics)
                uniqueness_status = sample_uniqueness_gate_status(uniqueness)
                purged_status = "pass" if uniqueness_status == "pass_with_exact_t1" else "fail"
    else:
        row_audit = pd.DataFrame([{"row_level_rebuild_gate_status": "not_run_due_to_input_or_upstream_failure"}])
        write_df(outputs["row_level_rebuild_audit"], row_audit)

    if early_audit.empty:
        early_audit = pd.DataFrame(columns=["early_path_k", "early_path_pit_gate_status"])
    if exec_audit.empty:
        exec_audit = pd.DataFrame(columns=["early_path_k", "horizon_mode", "delayed_entry_executability_gate_status"])
    decision = build_decision(
        input_status,
        upstream_status,
        label_status,
        row_status,
        early_status,
        exec_status,
        purged_status,
        uniqueness_status,
        comparison,
        missed,
        search,
        config,
        input_reason or upstream_reason or label_reason or row_reason or early_reason or exec_reason,
    )
    write_df(outputs["early_path_rebuild_audit"], early_audit)
    write_df(outputs["delayed_entry_executability_audit"], exec_audit)
    write_df(outputs["fold_arm_metrics"], fold_metrics)
    write_df(outputs["delayed_vs_t0_entry_comparison"], comparison)
    write_df(outputs["missed_winner_accounting"], missed)
    write_df(outputs["train_kfold_uniqueness_audit"], uniqueness)
    write_df(outputs["early_path_confirmation_delayed_entry_decision"], decision)
    write_text(outputs["report"], render_report(decision, comparison, fold_metrics, missed, uniqueness, early_audit, exec_audit, search))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
