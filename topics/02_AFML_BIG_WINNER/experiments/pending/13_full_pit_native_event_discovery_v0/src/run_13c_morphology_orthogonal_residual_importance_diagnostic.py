#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_13A_PATH = EXPERIMENT_DIR / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"
RUNNER_13A2_PATH = EXPERIMENT_DIR / "src" / "run_13a2_compression_directional_disambiguation_preflight.py"
RUNNER_13A3_PATH = EXPERIMENT_DIR / "src" / "run_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13a = load_runner(RUNNER_13A_PATH, "run_13a_full_pit_native_token_cartography_preflight")
r13a2 = load_runner(RUNNER_13A2_PATH, "run_13a2_compression_directional_disambiguation_preflight")
r13a3 = load_runner(RUNNER_13A3_PATH, "run_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic")


RUN_ID = "13C_morphology_orthogonal_residual_importance_diagnostic"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13c_morphology_orthogonal_residual_importance_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
EVAL_SPLITS = ("validation", "robustness")
FAST_FAIL_MAX_SESSIONS = 3
SELECTED_LABEL_ID = "vol20d_kup2p0_kdn1p0_H20"
BASE_TOKEN_ID = "volatility_20d__bottom_20pct"
REPORT_INPUT_KEYS = {"upstream_report_13a", "upstream_report_13a2", "upstream_report_13a3"}
MORPHOLOGY_ANCHORS = [
    "max_drawdown_20d",
    "distance_from_20d_low",
    "close_position_20d",
    "ret_20d",
    "ret_60d",
    "rebound_from_20d_low",
    "volatility_20d",
    "volatility_60d",
]
RESIDUAL_TARGETS = [
    "winner_positive",
    "lower_first",
    "fast_fail",
    "row_utility_component_50bps",
]
MODEL_TARGETS = ["winner_positive", "lower_first", "fast_fail", "utility_positive_50bps"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 13C morphology-orthogonal residual importance diagnostic.")
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
        "utility_reconciliation_audit": TABLE_DIR / "utility_reconciliation_audit.csv",
        "morphology_anchor_dictionary": TABLE_DIR / "morphology_anchor_dictionary.csv",
        "feature_cluster_dictionary": TABLE_DIR / "feature_cluster_dictionary.csv",
        "residualization_design_audit": TABLE_DIR / "residualization_design_audit.csv",
        "residual_calibration_audit": TABLE_DIR / "residual_calibration_audit.csv",
        "residual_state_effect_readout": TABLE_DIR / "residual_state_effect_readout.csv",
        "clustered_mda_importance": TABLE_DIR / "clustered_mda_importance.csv",
        "incremental_model_comparison": TABLE_DIR / "incremental_model_comparison.csv",
        "sample_uniqueness_audit": TABLE_DIR / "sample_uniqueness_audit.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "morphology_orthogonal_residual_importance_decision": TABLE_DIR / "morphology_orthogonal_residual_importance_decision.csv",
        "morphology_residual_panel": LOCAL_CACHE_DIR / "morphology_residual_panel.parquet",
        "report": REPORT_DIR / "morphology_orthogonal_residual_importance_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13a.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r13a.file_sha256(path) if path.exists() and path.is_file() else ""


def count_rows(path: Path) -> int | float:
    return r13a.count_rows(path)


def stable_hash(value: Any) -> str:
    return r13a.stable_hash(value)


def boolish(value: Any) -> bool:
    return r13a.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13a.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13a.finite_numeric(series)


def safe_rate(num: Any, den: Any) -> float:
    return r13a.safe_rate(num, den)


def auc_score(values: pd.Series, labels: pd.Series) -> float:
    return r13a.auc_score(values, labels)


def cost_label(cost: float) -> str:
    return f"{int(round(cost * 10000))}bps"


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13a": (),
        "upstream_requirement_13a2": (),
        "upstream_requirement_13a3": (),
        "upstream_report_13a": (),
        "upstream_report_13a2": (),
        "upstream_report_13a3": (),
        "upstream_requirement_12a7g": (),
        "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument"),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket"),
        "upstream_13a_manifest": (),
        "upstream_13a_token_dictionary": ("token_id", "primitive_id", "threshold_rule", "threshold_value"),
        "upstream_13a_morphology": ("token_id", "split_bucket"),
        "upstream_13a_native_thresholds": ("threshold_id", "threshold_value"),
        "upstream_13a_label_portability": ("split_bucket", "denominator_n"),
        "upstream_13a_native_universe_cache": ("row_id", "native_scope", "split", "winner_positive"),
        "upstream_13a_native_token_matrix_cache": ("row_id",),
        "upstream_13a2_manifest": (),
        "upstream_13a2_filter_dictionary": ("filter_id", "primitive_id_1", "threshold_rule_1"),
        "upstream_13a2_threshold_freeze": ("primitive_id", "threshold_rule", "threshold_value"),
        "upstream_13a2_compression_base_cache": ("row_id", "split"),
        "upstream_13a2_directional_filter_matrix_cache": ("row_id",),
        "upstream_13a3_manifest": (),
        "upstream_13a3_decision": ("decision_state", "sequence_mining_authorized", "selected_state_id"),
        "upstream_13a3_dictionary": ("state_id", "source_13a2_filter_id", "state_reproduction_status"),
        "upstream_13a3_native_readout": ("state_id", "split_bucket"),
        "upstream_13a3_badside": ("state_id", "split_bucket", "cost_buffer_return"),
        "upstream_13a3_morphology": ("state_id", "split_bucket", "independent_evidence_status"),
        "upstream_13a3_denominator_drift": ("state_id", "split_bucket", "drift_status"),
        "upstream_13a3_cost_buffer_sensitivity": ("filter_id_or_state_id", "split_bucket", "cost_buffer_return"),
        "upstream_13a3_row_level_cache_audit": ("cache_check_id", "cache_status"),
        "upstream_13a3_composite_state_matrix_cache": ("row_id",),
        "upstream_13a_config": (),
        "upstream_13a2_config": (),
        "upstream_13a3_config": (),
    }


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id in REPORT_INPUT_KEYS:
        return "lineage_report_only_not_row_truth"
    if artifact_id.startswith("upstream_13a3"):
        return "upstream_13a3_lineage"
    if artifact_id.startswith("upstream_13a2"):
        return "upstream_13a2_lineage"
    if artifact_id.startswith("upstream_13a"):
        return "upstream_13a_lineage"
    if artifact_id.startswith("upstream_requirement_12a7g"):
        return "upstream_12a7g_label_lineage"
    if artifact_id in {"pit_topn_400_100_executable_daily", "pit_topn_400_100_membership_daily", "stock_daily_qfq_dir", "global_regime_calendar"}:
        return "raw_pit_rebuild_input"
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
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        sample = pd.read_parquet(path).head(5)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    column_count = len(sample.columns) if suffixes.endswith((".csv", ".csv.gz", ".parquet")) else np.nan
                    missing = sorted(set(required_cols) - set(sample.columns)) if required_cols else []
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                    row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": True,
                "lineage_role": lineage_role_for_artifact(artifact_id),
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    bad = input_audit.loc[
        input_audit["required_flag"].astype(bool)
        & (
            input_audit["read_status"].astype(str).ne("pass")
            | input_audit["schema_status"].astype(str).str.startswith("missing_columns")
        )
    ]
    if len(bad):
        return "fail", ";".join(bad["artifact_id"].astype(str).tolist())
    return "pass", ""


def table_gate_status(frame: pd.DataFrame, status_col: str, pass_values: set[str] | None = None) -> tuple[str, str]:
    pass_values = pass_values or {"pass", "reported", "not_applicable"}
    if frame.empty or status_col not in frame.columns:
        return "fail", "missing_status_table"
    bad = frame.loc[~frame[status_col].astype(str).isin(pass_values)]
    if len(bad):
        return "fail", ";".join(bad.iloc[:, 0].astype(str).head(20).tolist())
    return "pass", ""


def build_upstream_lineage_audit(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str, str]:
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []

    def add(source_id: str, check_id: str, observed: Any, expected: Any, ok: bool, artifact_key: str) -> None:
        nonlocal status
        if not ok and status == "pass":
            status = "fail"
        if not ok:
            reason.append(f"{source_id}.{check_id}")
        path = resolved.get(artifact_key, Path(""))
        rows.append(
            {
                "lineage_source_id": source_id,
                "lineage_check_id": check_id,
                "observed_value": observed,
                "expected_value": expected,
                "lineage_status": "pass" if ok else "fail",
                "artifact_path": str(path),
                "sha256": file_sha(path) if path else "",
            }
        )

    try:
        decision = read_table(resolved["upstream_13a3_decision"]).iloc[0]
        if boolish(decision.get("sequence_mining_authorized", False)):
            add("13A3", "sequence_mining_authorized", decision.get("sequence_mining_authorized"), "False", False, "upstream_13a3_decision")
            return pd.DataFrame(rows), "fail_already_authorized", "upstream_13a3_already_authorized"
        required = {
            "input_gate_status": "pass",
            "upstream_13a_lineage_gate_status": "pass",
            "upstream_13a2_lineage_gate_status": "pass",
            "cost_sensitivity_gate_status": "pass",
            "composite_readout_gate_status": "pass",
            "badside_gate_status": "pass",
            "utility_gate_status": "fail",
            "morphology_independent_evidence_gate_status": "fail",
            "decision_state": "13A3_selected_composite_state_not_supported",
            "selected_state_id": "repair_range_participation_core_30",
        }
        for key, expected in required.items():
            observed = str(decision.get(key, ""))
            add("13A3", key, observed, expected, observed == expected, "upstream_13a3_decision")
        add("13A3", "sequence_mining_authorized", decision.get("sequence_mining_authorized", ""), "False", not boolish(decision.get("sequence_mining_authorized", False)), "upstream_13a3_decision")
    except Exception as exc:
        add("13A3", "decision_read", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13a3_decision")

    try:
        cache_audit = read_table(resolved["upstream_13a3_row_level_cache_audit"])
        cache_ok = bool(len(cache_audit) and cache_audit["cache_status"].astype(str).eq("pass").all())
        add("13A3", "row_level_cache_audit_all_pass", int(cache_audit["cache_status"].astype(str).ne("pass").sum()), 0, cache_ok, "upstream_13a3_row_level_cache_audit")
    except Exception as exc:
        add("13A3", "row_level_cache_audit_read", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13a3_row_level_cache_audit")

    for source_id, artifact_keys in [
        ("13A", ["upstream_13a_manifest", "upstream_13a_token_dictionary", "upstream_13a_label_portability"]),
        ("13A2", ["upstream_13a2_manifest", "upstream_13a2_filter_dictionary", "upstream_13a2_threshold_freeze"]),
    ]:
        for key in artifact_keys:
            path = resolved[key]
            add(source_id, f"{key}.exists", path.exists(), True, path.exists(), key)

    return pd.DataFrame(rows), status, ";".join(reason)


def report_text_inputs_are_lineage_only(resolved: dict[str, Path]) -> bool:
    return all(key in resolved for key in REPORT_INPUT_KEYS)


def audit_row(check_id: str, observed: Any, expected: Any, ok: bool, source_id: str = "13C", artifact_key: str = "", resolved: dict[str, Path] | None = None) -> dict[str, Any]:
    path = resolved.get(artifact_key, Path("")) if resolved is not None and artifact_key else Path("")
    return {
        "lineage_source_id": source_id,
        "lineage_check_id": check_id,
        "observed_value": observed,
        "expected_value": expected,
        "lineage_status": "pass" if ok else "fail",
        "artifact_path": str(path),
        "sha256": file_sha(path) if path and path.exists() else "",
    }


def expected_selected_label(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "label_id": "vol20d_kup2p0_kdn1p0_H20",
        "vol_reference_id": "volatility_20d",
        "k_up": 2.0,
        "k_dn": 1.0,
        "horizon_sessions": 20,
        "same_bar_priority": "lower_first",
        **config.get("selected_label", {}),
    }


def label_from_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return r13a.load_yaml(path).get("selected_label", {}) or {}
    except Exception:
        return {}


def compare_label_config(source_id: str, label: dict[str, Any], expected: dict[str, Any], artifact_key: str, resolved: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ["label_id", "vol_reference_id", "k_up", "k_dn", "horizon_sessions"]:
        exp = expected[key]
        obs = label.get(key)
        if isinstance(exp, float):
            ok = obs is not None and math.isclose(float(obs), float(exp), rel_tol=1e-12, abs_tol=1e-12)
        else:
            ok = str(obs) == str(exp)
        rows.append(audit_row(f"selected_label.{key}", obs, exp, ok, source_id, artifact_key, resolved))
    return rows


def manifest_schema_for(path: Path, artifact_id: str) -> str:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    for row in manifest.get("local_cache_audit", []) or []:
        if str(row.get("artifact_id", "")) == artifact_id:
            return str(row.get("schema_hash", ""))
    return ""


def cache_schema_check(path: Path, manifest_path: Path, artifact_id: str) -> tuple[str, str, bool]:
    expected = manifest_schema_for(manifest_path, artifact_id)
    observed = schema_hash(path)
    if not expected:
        return observed, "not_declared", True
    return observed, expected, observed == expected


def build_cache_lineage_audit(
    native_panel: pd.DataFrame,
    filter_matrix: pd.DataFrame,
    base_panel: pd.DataFrame,
    state_matrix: pd.DataFrame,
    rebuilt_state_matrix: pd.DataFrame,
    dictionary: pd.DataFrame,
    config: dict[str, Any],
    resolved: dict[str, Path],
    base_threshold: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    expected = expected_selected_label(config)
    native_ids = native_panel["row_id"] if "row_id" in native_panel.columns else pd.Series(dtype=int)
    filter_ids = filter_matrix["row_id"] if "row_id" in filter_matrix.columns else pd.Series(dtype=int)
    base_ids = base_panel["row_id"] if "row_id" in base_panel.columns else pd.Series(dtype=int)
    state_ids = state_matrix["row_id"] if "row_id" in state_matrix.columns else pd.Series(dtype=int)
    native_set = set(native_ids.tolist())

    rows.append(audit_row("native_panel.row_id_unique", int(native_ids.nunique()), len(native_panel), native_ids.is_unique, "13A", "upstream_13a_native_universe_cache", resolved))
    if {"instrument", "reference_date"} <= set(native_panel.columns):
        duplicate_n = int(native_panel.duplicated(["instrument", "reference_date"]).sum())
        rows.append(audit_row("native_panel.instrument_reference_date_unique", duplicate_n, 0, duplicate_n == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    else:
        rows.append(audit_row("native_panel.instrument_reference_date_unique", "missing_columns", "instrument+reference_date", False, "13A", "upstream_13a_native_universe_cache", resolved))
    rows.append(audit_row("filter_matrix.coverage_equals_native", len(set(filter_ids.tolist()) ^ native_set), 0, set(filter_ids.tolist()) == native_set, "13A2", "upstream_13a2_directional_filter_matrix_cache", resolved))
    rows.append(audit_row("state_matrix.coverage_equals_native", len(set(state_ids.tolist()) ^ native_set), 0, set(state_ids.tolist()) == native_set, "13A3", "upstream_13a3_composite_state_matrix_cache", resolved))

    if {"row_id", "split"} <= set(base_panel.columns):
        native_split = native_panel.set_index("row_id")["split"].astype(str)
        base_split = base_panel.set_index("row_id")["split"].astype(str)
        common = base_split.index.intersection(native_split.index)
        mismatch = int((base_split.loc[common] != native_split.loc[common]).sum()) + int(len(base_split.index.difference(native_split.index)))
        rows.append(audit_row("compression_base.split_boundary_equality", mismatch, 0, mismatch == 0, "13A2", "upstream_13a2_compression_base_cache", resolved))
    else:
        rows.append(audit_row("compression_base.split_boundary_equality", "missing_columns", "row_id+split", False, "13A2", "upstream_13a2_compression_base_cache", resolved))

    if {"native_scope", "volatility_20d"} <= set(native_panel.columns) and pd.notna(base_threshold):
        expected_base = bool_series(native_panel["native_scope"]) & finite_numeric(native_panel["volatility_20d"]).le(float(base_threshold))
        observed_base = native_panel["row_id"].isin(set(base_ids.tolist()))
        mismatch = int((expected_base.to_numpy(dtype=bool) != observed_base.to_numpy(dtype=bool)).sum())
        rows.append(audit_row("compression_base.membership_equality", mismatch, 0, mismatch == 0, "13A2", "upstream_13a2_compression_base_cache", resolved))
    else:
        rows.append(audit_row("compression_base.membership_equality", "missing_columns_or_threshold", "native_scope+volatility_20d+base_threshold", False, "13A2", "upstream_13a2_compression_base_cache", resolved))

    state_cols = [c for c in state_matrix.columns if c != "row_id"]
    left = state_matrix.set_index("row_id")
    right = rebuilt_state_matrix.set_index("row_id")
    common_ids = left.index.intersection(right.index)
    mismatch_total = 0
    for col in state_cols:
        if col not in right.columns:
            mismatch_total += len(common_ids)
            continue
        mismatch_total += int((left.loc[common_ids, col].astype(bool) != right.loc[common_ids, col].astype(bool)).sum())
    rows.append(audit_row("required_composite_state_membership_equality", mismatch_total, 0, mismatch_total == 0, "13A3", "upstream_13a3_composite_state_matrix_cache", resolved))

    native = native_panel.loc[bool_series(native_panel.get("native_scope", pd.Series(False, index=native_panel.index)))]
    for col in ["reference_pos", "entry_pos", "entry_price"]:
        missing = int(finite_numeric(native.get(col, pd.Series(np.nan, index=native.index))).isna().sum())
        rows.append(audit_row(f"pit_mapping.{col}_nonnull", missing, 0, missing == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    if "entry_executable" in native.columns:
        bad = int((~bool_series(native["entry_executable"])).sum())
        rows.append(audit_row("pit_mapping.entry_executable", bad, 0, bad == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    if "horizon_complete" in native.columns:
        bad = int((~bool_series(native["horizon_complete"])).sum())
        rows.append(audit_row("label_lineage.horizon_complete", bad, 0, bad == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    if "label_id" in native.columns:
        mismatch = int(native["label_id"].astype(str).ne(str(expected["label_id"])).sum())
        rows.append(audit_row("label_lineage.selected_label_id", mismatch, 0, mismatch == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    if "horizon_sessions" in native.columns:
        mismatch = int(finite_numeric(native["horizon_sessions"]).dropna().astype(int).ne(int(expected["horizon_sessions"])).sum())
        rows.append(audit_row("label_lineage.horizon_sessions", mismatch, 0, mismatch == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    same_bar = native.loc[bool_series(native.get("same_bar_conflict", pd.Series(False, index=native.index)))]
    if len(same_bar):
        bad_same = int((~bool_series(same_bar.get("lower_first", pd.Series(False, index=same_bar.index)))).sum())
        rows.append(audit_row("label_lineage.same_bar_priority_lower_first", bad_same, 0, bad_same == 0, "13A", "upstream_13a_native_universe_cache", resolved))
    else:
        rows.append(audit_row("label_lineage.same_bar_priority_lower_first", "no_same_bar_conflict_rows", "lower_first_priority_when_present", True, "13A", "upstream_13a_native_universe_cache", resolved))

    rows.extend(compare_label_config("13A_config", label_from_config(resolved["upstream_13a_config"]), expected, "upstream_13a_config", resolved))
    rows.extend(compare_label_config("13A2_config", label_from_config(resolved["upstream_13a2_config"]), expected, "upstream_13a2_config", resolved))
    cfg_label = config.get("selected_label", {})
    rows.append(audit_row("13C_config.selected_label.same_bar_priority", cfg_label.get("same_bar_priority"), expected["same_bar_priority"], str(cfg_label.get("same_bar_priority")) == str(expected["same_bar_priority"]), "13C_config", "requirement", resolved))

    for artifact_id, path_key, manifest_key, manifest_artifact_id in [
        ("native_universe_panel", "upstream_13a_native_universe_cache", "upstream_13a_manifest", "native_universe_panel"),
        ("native_token_matrix", "upstream_13a_native_token_matrix_cache", "upstream_13a_manifest", "native_token_matrix"),
        ("compression_base_panel", "upstream_13a2_compression_base_cache", "upstream_13a2_manifest", "compression_base_panel"),
        ("directional_filter_matrix", "upstream_13a2_directional_filter_matrix_cache", "upstream_13a2_manifest", "directional_filter_matrix"),
        ("composite_state_matrix", "upstream_13a3_composite_state_matrix_cache", "upstream_13a3_manifest", "composite_state_matrix"),
    ]:
        observed, exp, ok = cache_schema_check(resolved[path_key], resolved[manifest_key], manifest_artifact_id)
        rows.append(audit_row(f"{artifact_id}.manifest_schema_hash", observed, exp, ok, "cache_schema", path_key, resolved))
    return pd.DataFrame(rows)


def lineage_status(frame: pd.DataFrame) -> tuple[str, str]:
    if frame.empty or "lineage_status" not in frame.columns:
        return "fail", "missing_lineage_audit"
    bad = frame.loc[frame["lineage_status"].astype(str).ne("pass")]
    if len(bad):
        return "fail", ";".join((bad["lineage_source_id"].astype(str) + "." + bad["lineage_check_id"].astype(str)).head(20).tolist())
    return "pass", ""


def reload_input_caches(resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    native_panel = read_table(resolved["upstream_13a_native_universe_cache"])
    filter_matrix = read_table(resolved["upstream_13a2_directional_filter_matrix_cache"])
    base_panel = read_table(resolved["upstream_13a2_compression_base_cache"])
    state_matrix = read_table(resolved["upstream_13a3_composite_state_matrix_cache"])
    dictionary = read_table(resolved["upstream_13a3_dictionary"])
    upstream_badside = read_table(resolved["upstream_13a3_badside"])
    return native_panel, filter_matrix, base_panel, state_matrix, dictionary, upstream_badside


def rebuild_upstream_caches(resolved: dict[str, Path]) -> None:
    r13a.run(resolved["upstream_13a_config"])
    r13a2.run(resolved["upstream_13a2_config"], mode="full")
    r13a3.run(resolved["upstream_13a3_config"], mode="full")


def load_verified_inputs(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str, float]:
    native_panel, filter_matrix, base_panel, state_matrix, dictionary, upstream_badside = reload_input_caches(resolved)
    base_threshold = float(dictionary["base_threshold_value"].dropna().iloc[0])
    rebuilt_state_matrix = r13a3.build_composite_state_matrix(native_panel, filter_matrix, dictionary)
    audit = build_cache_lineage_audit(native_panel, filter_matrix, base_panel, state_matrix, rebuilt_state_matrix, dictionary, config, resolved, base_threshold)
    status, reason = lineage_status(audit)
    if status != "pass":
        rebuild_upstream_caches(resolved)
        native_panel, filter_matrix, base_panel, state_matrix, dictionary, upstream_badside = reload_input_caches(resolved)
        base_threshold = float(dictionary["base_threshold_value"].dropna().iloc[0])
        rebuilt_state_matrix = r13a3.build_composite_state_matrix(native_panel, filter_matrix, dictionary)
        audit = build_cache_lineage_audit(native_panel, filter_matrix, base_panel, state_matrix, rebuilt_state_matrix, dictionary, config, resolved, base_threshold)
        status, reason = lineage_status(audit)
        audit["lineage_check_id"] = "post_rebuild." + audit["lineage_check_id"].astype(str)
    return native_panel, filter_matrix, base_panel, state_matrix, dictionary, upstream_badside, audit, status, reason, base_threshold


def fast_fail_mask(frame: pd.DataFrame) -> pd.Series:
    lower = bool_series(frame.get("lower_first", pd.Series(False, index=frame.index)))
    ttl = finite_numeric(frame.get("time_to_lower", pd.Series(np.nan, index=frame.index)))
    return lower & ttl.le(FAST_FAIL_MAX_SESSIONS)


def row_utility_component(frame: pd.DataFrame, cost: float) -> pd.Series:
    upper = bool_series(frame.get("upper_first", pd.Series(False, index=frame.index))).astype(float)
    lower = bool_series(frame.get("lower_first", pd.Series(False, index=frame.index))).astype(float)
    upper_barrier = finite_numeric(frame.get("upper_barrier", pd.Series(np.nan, index=frame.index)))
    lower_barrier = finite_numeric(frame.get("lower_barrier", pd.Series(np.nan, index=frame.index))).abs()
    return upper * upper_barrier - lower * lower_barrier - float(cost)


def ensure_required_feature_aliases(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    if "distance_from_20d_low" not in out.columns and "distance_to_20d_low" in out.columns:
        out["distance_from_20d_low"] = finite_numeric(out["distance_to_20d_low"])
    if "range_width_20d" not in out.columns and {"distance_to_20d_high", "distance_from_20d_low"} <= set(out.columns):
        high_over_close = 1.0 + finite_numeric(out["distance_to_20d_high"])
        low_over_close = 1.0 / (1.0 + finite_numeric(out["distance_from_20d_low"])).replace(0, np.nan)
        out["range_width_20d"] = high_over_close - low_over_close
    if "rebound_from_20d_low" not in out.columns and "distance_from_20d_low" in out.columns:
        out["rebound_from_20d_low"] = finite_numeric(out["distance_from_20d_low"])
    return out


def quantile_edges(values: pd.Series, n: int) -> list[float]:
    clean = finite_numeric(values).dropna()
    if clean.empty:
        return []
    qs = [i / n for i in range(1, n)]
    edges = sorted(float(x) for x in clean.quantile(qs).dropna().unique())
    return edges


def assign_bucket(values: pd.Series, edges: list[float], prefix: str) -> pd.Series:
    numeric = finite_numeric(values)
    if not edges:
        return pd.Series(f"{prefix}_missing", index=values.index, dtype=object)
    bins = [-np.inf, *edges, np.inf]
    labels = [f"{prefix}_{i + 1:02d}" for i in range(len(bins) - 1)]
    return pd.cut(numeric, bins=bins, labels=labels, include_lowest=True).astype(object).where(numeric.notna(), f"{prefix}_missing").astype(str)


def fit_train_frozen_buckets(panel: pd.DataFrame, base_threshold: float, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, list[float]]]:
    out = panel.copy()
    th = config.get("residualization", {})
    train = out["split"].astype(str).eq("train") & bool_series(out["native_scope"])
    qn = int(th.get("quantile_bucket_n", 5))
    dn = int(th.get("decile_bucket_n", 10))
    edges = {
        "liquidity_bucket": quantile_edges(out.loc[train, "money_median_20d"], qn),
        "volatility_bucket": quantile_edges(out.loc[train, "volatility_20d"], qn),
        "max_drawdown_20d_decile": quantile_edges(out.loc[train, "max_drawdown_20d"], dn),
        "max_drawdown_20d_quintile": quantile_edges(out.loc[train, "max_drawdown_20d"], qn),
    }
    base_train = train & finite_numeric(out["volatility_20d"]).le(float(base_threshold))
    edges["compression_severity_bucket"] = quantile_edges(out.loc[base_train, "volatility_20d"], qn)
    out["liquidity_bucket"] = assign_bucket(out["money_median_20d"], edges["liquidity_bucket"], "liq")
    out["volatility_bucket"] = assign_bucket(out["volatility_20d"], edges["volatility_bucket"], "vol")
    out["max_drawdown_20d_decile"] = assign_bucket(out["max_drawdown_20d"], edges["max_drawdown_20d_decile"], "mdd_d")
    out["max_drawdown_20d_quintile"] = assign_bucket(out["max_drawdown_20d"], edges["max_drawdown_20d_quintile"], "mdd_q")
    out["compression_severity_bucket"] = assign_bucket(out["volatility_20d"], edges["compression_severity_bucket"], "comp")
    return out, edges


def fit_zscore(panel: pd.DataFrame, columns: list[str]) -> dict[str, tuple[float, float]]:
    train = panel["split"].astype(str).eq("train") & bool_series(panel["native_scope"])
    stats: dict[str, tuple[float, float]] = {}
    for col in columns:
        values = finite_numeric(panel.loc[train, col])
        mean = float(values.mean()) if values.notna().any() else 0.0
        std = float(values.std(ddof=0)) if values.notna().any() else 1.0
        if not np.isfinite(std) or std <= 0:
            std = 1.0
        stats[col] = (mean, std)
    return stats


def apply_morphology_scores(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    out = panel.copy()
    stats = fit_zscore(out, MORPHOLOGY_ANCHORS)
    zcols: list[str] = []
    for col, (mean, std) in stats.items():
        zcol = f"{col}__train_z"
        out[zcol] = (finite_numeric(out[col]) - mean) / std
        zcols.append(zcol)
    out["broad_drawdown_score"] = out[[f"{c}__train_z" for c in ["max_drawdown_20d", "distance_from_20d_low", "ret_20d"]]].mean(axis=1)
    out["broad_reversal_score"] = out[[f"{c}__train_z" for c in ["rebound_from_20d_low", "close_position_20d", "ret_60d"]]].mean(axis=1)
    out["broad_morphology_score"] = out[zcols].mean(axis=1)
    return out, stats


def build_morphology_anchor_dictionary(panel: pd.DataFrame, stats: dict[str, tuple[float, float]], bucket_edges: dict[str, list[float]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for anchor in MORPHOLOGY_ANCHORS:
        rows.append(
            {
                "anchor_id": anchor,
                "source_column": anchor,
                "available_row_n": int(finite_numeric(panel.get(anchor, pd.Series(np.nan, index=panel.index))).notna().sum()),
                "transform": "train_frozen_zscore",
                "train_mean": stats.get(anchor, (np.nan, np.nan))[0],
                "train_std": stats.get(anchor, (np.nan, np.nan))[1],
                "future_data_used": False,
                "anchor_status": "pass" if anchor in panel.columns and finite_numeric(panel[anchor]).notna().any() else "missing",
            }
        )
    for bucket, edges in bucket_edges.items():
        rows.append(
            {
                "anchor_id": bucket,
                "source_column": bucket,
                "available_row_n": int(panel[bucket].notna().sum()) if bucket in panel else 0,
                "transform": "train_frozen_quantile_bucket",
                "train_mean": np.nan,
                "train_std": np.nan,
                "future_data_used": False,
                "bucket_edges": json.dumps(edges),
                "anchor_status": "pass" if edges else "missing",
            }
        )
    return pd.DataFrame(rows)


def build_feature_cluster_dictionary(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cluster_id, features in config.get("feature_clusters", {}).items():
        for feature in features:
            required = feature != "range_width_20d"
            available = feature in panel.columns and (not required or finite_numeric(panel[feature]).notna().any() if pd.api.types.is_numeric_dtype(panel.get(feature, pd.Series(dtype=float))) else panel[feature].notna().any())
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "feature_id": feature,
                    "feature_role": "categorical_control" if feature in {"board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket"} else "numeric",
                    "required_flag": required,
                    "available_row_n": int(panel[feature].notna().sum()) if feature in panel.columns else 0,
                    "feature_status": "pass" if available else ("optional_missing" if not required else "missing_required"),
                    "future_data_used": False,
                    "threshold_source_split": "train",
                }
            )
    return pd.DataFrame(rows)


def feature_cluster_gate_status(feature_clusters: pd.DataFrame) -> tuple[str, str]:
    if feature_clusters.empty:
        return "fail", "missing_feature_cluster_dictionary"
    bad = feature_clusters.loc[feature_clusters["required_flag"].astype(bool) & feature_clusters["feature_status"].astype(str).ne("pass")]
    if len(bad):
        return "fail", ";".join(bad["feature_id"].astype(str).tolist())
    return "pass", ""


def prepare_row_level_panel(
    native_panel: pd.DataFrame,
    state_matrix: pd.DataFrame,
    base_panel: pd.DataFrame,
    config: dict[str, Any],
    resolved: dict[str, Path],
) -> pd.DataFrame:
    panel, _availability = r13a2.derive_directional_features(native_panel, resolved)
    panel = ensure_required_feature_aliases(panel)
    panel["split_bucket"] = panel["split"].astype(str)
    panel["fast_fail"] = fast_fail_mask(panel)
    for cost in config.get("cost_buffer", {}).get("grid", [0.0, 0.0025, 0.005, 0.0075, 0.01]):
        panel[f"row_utility_component_{cost_label(float(cost))}"] = row_utility_component(panel, float(cost))
    panel["utility_positive_50bps"] = finite_numeric(panel["row_utility_component_50bps"]).gt(0)
    panel["median_upper_barrier_return_source"] = finite_numeric(panel.get("upper_barrier", pd.Series(np.nan, index=panel.index)))
    panel["median_abs_lower_barrier_return_source"] = finite_numeric(panel.get("lower_barrier", pd.Series(np.nan, index=panel.index))).abs()
    base_ids = set(base_panel["row_id"].tolist())
    panel["compression_base"] = panel["row_id"].isin(base_ids)
    sm = state_matrix.set_index("row_id")
    for col in sm.columns:
        panel[col] = sm[col].reindex(panel["row_id"]).fillna(False).to_numpy(dtype=bool)
    return panel


def build_row_level_rebuild_audit(panel: pd.DataFrame, state_matrix: pd.DataFrame, rebuilt_state_matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    state_cols = [x for x in state_matrix.columns if x != "row_id"]
    left = state_matrix.set_index("row_id")
    right = rebuilt_state_matrix.set_index("row_id")
    shared_ids = left.index.intersection(right.index)
    membership_matches = []
    for col in state_cols:
        if col in left.columns and col in right.columns and len(shared_ids):
            membership_matches.append(float((left.loc[shared_ids, col].astype(bool) == right.loc[shared_ids, col].astype(bool)).mean()))
    match_rate = min(membership_matches) if membership_matches else np.nan
    optional_features = {"range_width_20d"}
    required_feature_cols = sorted(
        {
            f
            for fs in config.get("feature_clusters", {}).values()
            for f in fs
            if f in panel.columns and f not in {"board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket"} and f not in optional_features
        }
    )
    required_key_cols = ["row_id", "instrument", "reference_date", "entry_date", "entry_price", "reference_pos", "entry_pos", "split_bucket", "board_bucket", "calendar_year", "calendar_month", "market_regime_bucket"]
    required_label_cols = ["winner_positive", "upper_first", "lower_first", "fast_fail", "neutral", "censored", "same_bar_conflict", "horizon_complete", "upper_barrier", "lower_barrier", "time_to_upper", "time_to_lower", "horizon_close_return", "row_utility_component_0bps", "row_utility_component_25bps", "row_utility_component_50bps", "row_utility_component_75bps", "row_utility_component_100bps", "utility_positive_50bps", "median_upper_barrier_return_source", "median_abs_lower_barrier_return_source"]
    for split in SPLITS:
        frame = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)]
        missing_required_cols = sorted(set(required_key_cols + required_label_cols) - set(frame.columns))
        required_feature_nonnull_rate = float(frame[required_feature_cols].notna().mean().mean()) if len(frame) and required_feature_cols else np.nan
        required_cols_present = not missing_required_cols
        pit_mapping_ok = all(finite_numeric(frame[col]).notna().all() for col in ["reference_pos", "entry_pos", "entry_price"] if col in frame.columns)
        horizon_ok = bool(len(frame) and bool_series(frame["horizon_complete"]).all()) if "horizon_complete" in frame.columns else False
        rows.append(
            {
                "audit_id": f"row_level_panel_{split}",
                "row_count": len(frame),
                "unique_row_id_count": int(frame["row_id"].nunique()),
                "instrument_count": int(frame["instrument"].nunique()) if "instrument" in frame.columns else 0,
                "split_bucket": split,
                "horizon_complete_rate": float(bool_series(frame["horizon_complete"]).mean()) if len(frame) else np.nan,
                "selected_label_match_rate_vs_cache": float(frame["label_id"].astype(str).eq(SELECTED_LABEL_ID).mean()) if len(frame) and "label_id" in frame else np.nan,
                "composite_membership_match_rate_vs_13a3_cache": match_rate,
                "required_feature_nonnull_rate": required_feature_nonnull_rate,
                "required_column_missing_count": len(missing_required_cols),
                "missing_required_columns": ";".join(missing_required_cols),
                "pit_mapping_status": "pass" if pit_mapping_ok else "fail",
                "status": "pass"
                if len(frame)
                and frame["row_id"].is_unique
                and required_cols_present
                and pit_mapping_ok
                and horizon_ok
                and pd.notna(match_rate)
                and match_rate >= 0.999999
                and (not required_feature_cols or required_feature_nonnull_rate >= 1.0)
                else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_utility_reconciliation(panel: pd.DataFrame, dictionary: pd.DataFrame, upstream_badside: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    upstream_lookup = upstream_badside.set_index(["state_id", "split_bucket", "cost_buffer_return"], drop=False) if not upstream_badside.empty else pd.DataFrame()
    native_counts = {split: int((bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)).sum()) for split in SPLITS}
    for state_id in dictionary["state_id"].astype(str):
        for split in SPLITS:
            native_n = native_counts[split]
            treated = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split) & bool_series(panel[state_id])]
            treated_n = len(treated)
            for cost in config.get("cost_buffer", {}).get("grid", [0.005]):
                cost = float(cost)
                comp = finite_numeric(treated[f"row_utility_component_{cost_label(cost)}"]) if treated_n else pd.Series(dtype=float)
                row_per_entry = float(comp.mean()) if len(comp) else np.nan
                row_total = row_per_entry * safe_rate(treated_n, native_n) if pd.notna(row_per_entry) else np.nan
                up_per = np.nan
                up_total = np.nan
                key = (state_id, split, cost)
                try:
                    u = upstream_lookup.loc[key]
                    if isinstance(u, pd.DataFrame):
                        u = u.iloc[0]
                    up_per = float(u.get("utility_proxy_per_entry", np.nan))
                    up_total = float(u.get("utility_proxy_total_indexed", np.nan))
                except Exception:
                    pass
                rows.append(
                    {
                        "state_id": state_id,
                        "split_bucket": split,
                        "cost_buffer_return": cost,
                        "cost_tier_label": cost_label(cost),
                        "treated_n": treated_n,
                        "row_component_utility_per_entry": row_per_entry,
                        "row_component_utility_total_indexed": row_total,
                        "median_barrier_utility_per_entry_from_13a3": up_per,
                        "median_barrier_utility_total_indexed_from_13a3": up_total,
                        "per_entry_delta_row_vs_13a3": row_per_entry - up_per if pd.notna(row_per_entry) and pd.notna(up_per) else np.nan,
                        "total_indexed_delta_row_vs_13a3": row_total - up_total if pd.notna(row_total) and pd.notna(up_total) else np.nan,
                        "reconciliation_status": "reported_not_decision_gate",
                    }
                )
    return pd.DataFrame(rows)


def join_key(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    if not cols:
        return pd.Series("global", index=frame.index)
    return frame[cols].astype(str).agg("|".join, axis=1)


@dataclass
class ResidualSpec:
    target_id: str
    primary_cols: list[str]
    fallback_cols: list[list[str]]
    train_maps: dict[str, dict[str, float]]
    global_mean: float


def fit_residual_spec(panel: pd.DataFrame, target_id: str) -> ResidualSpec:
    primary_cols = ["board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket", "max_drawdown_20d_decile", "compression_severity_bucket"]
    fallback_cols = [
        ["board_bucket", "calendar_year", "max_drawdown_20d_quintile"],
        ["board_bucket", "max_drawdown_20d_quintile"],
        ["max_drawdown_20d_quintile"],
        [],
    ]
    train = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq("train")].copy()
    y = finite_numeric(train[target_id])
    maps: dict[str, dict[str, float]] = {}
    for i, cols in enumerate([primary_cols, *fallback_cols]):
        scope = "primary_cell" if i == 0 else (f"fallback_level_{i}" if cols else "global")
        if cols:
            tmp = pd.DataFrame({"key": join_key(train, cols), "y": y})
            maps[scope] = tmp.groupby("key", dropna=False)["y"].mean().to_dict()
        else:
            maps[scope] = {"global": float(y.mean()) if y.notna().any() else 0.0}
    global_mean = float(y.mean()) if y.notna().any() else 0.0
    return ResidualSpec(target_id=target_id, primary_cols=primary_cols, fallback_cols=fallback_cols, train_maps=maps, global_mean=global_mean)


def apply_residual_spec(panel: pd.DataFrame, spec: ResidualSpec) -> tuple[pd.Series, pd.Series, pd.Series]:
    expected = pd.Series(np.nan, index=panel.index, dtype=float)
    scope = pd.Series("", index=panel.index, dtype=object)
    cell = pd.Series("", index=panel.index, dtype=object)
    choices = [("primary_cell", spec.primary_cols), ("fallback_level_1", spec.fallback_cols[0]), ("fallback_level_2", spec.fallback_cols[1]), ("fallback_level_3", spec.fallback_cols[2]), ("global", [])]
    for scope_id, cols in choices:
        missing = expected.isna()
        if not bool(missing.any()):
            break
        if cols:
            keys = join_key(panel.loc[missing], cols)
            vals = keys.map(spec.train_maps.get(scope_id, {}))
            fill_idx = vals.notna()
            idx = vals.index[fill_idx]
            expected.loc[idx] = vals.loc[idx].astype(float)
            scope.loc[idx] = scope_id
            cell.loc[idx] = keys.loc[idx]
        else:
            idx = expected.loc[missing].index
            expected.loc[idx] = spec.global_mean
            scope.loc[idx] = "global"
            cell.loc[idx] = "global"
    return expected.fillna(spec.global_mean), scope.replace("", "global"), cell.replace("", "global")


def add_residuals(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = panel.copy()
    design_rows: list[dict[str, Any]] = []
    for target in RESIDUAL_TARGETS:
        spec = fit_residual_spec(out, target)
        expected, scope, cell = apply_residual_spec(out, spec)
        out[f"expected_{target}"] = expected
        out[f"residual_{target}"] = finite_numeric(out[target]) - expected
        if target == "winner_positive":
            out["residualization_cell_scope"] = scope
            out["residualization_cell_key"] = cell
        for split in SPLITS:
            split_scope = scope.loc[out["split_bucket"].eq(split)].value_counts().to_dict()
            for scope_id, row_count in split_scope.items():
                design_rows.append(
                    {
                        "target_id": target,
                        "split_bucket": split,
                        "residualization_method": "cell_mean_residualization",
                        "cell_scope": scope_id,
                        "row_count": int(row_count),
                        "fit_scope": "train",
                        "apply_scope": "train_validation_robustness",
                        "validation_labels_used_to_fit_expectation": False,
                        "robustness_labels_used_to_fit_expectation": False,
                        "primary_cell_fields": "|".join(spec.primary_cols),
                        "backoff_hierarchy": "board+year+mdd_quintile|board+mdd_quintile|mdd_quintile|global",
                        "purge_window_sessions": 20,
                        "embargo_sessions": 20,
                        "design_status": "pass",
                    }
                )
    return out, pd.DataFrame(design_rows)


def build_residual_calibration(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    thresholds = config.get("thresholds", {})
    for target in RESIDUAL_TARGETS:
        target_threshold = float(thresholds.get("utility_calibration_weighted_abs_error", 0.0025)) if target == "row_utility_component_50bps" else float(thresholds.get("binary_calibration_weighted_abs_error", 0.02))
        for split in EVAL_SPLITS:
            frame = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)].copy()
            if frame.empty:
                rows.append(
                    {
                        "target_id": target,
                        "split_bucket": split,
                        "residualization_method": "cell_mean_residualization",
                        "cell_scope": "none",
                        "cell_count": 0,
                        "row_count": 0,
                        "predicted_mean_from_train": np.nan,
                        "realized_mean_in_split": np.nan,
                        "calibration_error": np.nan,
                        "abs_calibration_error": np.nan,
                        "weighted_abs_calibration_error": np.nan,
                        "max_abs_cell_calibration_error": np.nan,
                        "calibration_status": "insufficient_calibration_support",
                    }
                )
                continue
            tmp = pd.DataFrame(
                {
                    "scope": frame["residualization_cell_scope"].astype(str),
                    "expected": finite_numeric(frame[f"expected_{target}"]),
                    "realized": finite_numeric(frame[target]),
                }
            )
            for scope_id, g in tmp.groupby("scope", dropna=False):
                by_cell = (
                    pd.DataFrame({"cell": frame.loc[g.index, "residualization_cell_key"].astype(str), "expected": g["expected"], "realized": g["realized"]})
                    .groupby("cell", dropna=False)
                    .agg(predicted_mean_from_train=("expected", "mean"), realized_mean_in_split=("realized", "mean"), row_count=("realized", "size"))
                    .reset_index()
                )
                by_cell["abs_error"] = (by_cell["realized_mean_in_split"] - by_cell["predicted_mean_from_train"]).abs()
                weighted = float(np.average(by_cell["abs_error"], weights=by_cell["row_count"])) if len(by_cell) else np.nan
                status = "calibration_pass" if pd.notna(weighted) and weighted <= target_threshold else "residual_drift_caveat"
                if len(by_cell) < 1 or int(by_cell["row_count"].sum()) < 1:
                    status = "insufficient_calibration_support"
                rows.append(
                    {
                        "target_id": target,
                        "split_bucket": split,
                        "residualization_method": "cell_mean_residualization",
                        "cell_scope": scope_id,
                        "cell_count": len(by_cell),
                        "row_count": int(by_cell["row_count"].sum()) if len(by_cell) else 0,
                        "predicted_mean_from_train": float(np.average(by_cell["predicted_mean_from_train"], weights=by_cell["row_count"])) if len(by_cell) else np.nan,
                        "realized_mean_in_split": float(np.average(by_cell["realized_mean_in_split"], weights=by_cell["row_count"])) if len(by_cell) else np.nan,
                        "calibration_error": float(np.average(by_cell["realized_mean_in_split"] - by_cell["predicted_mean_from_train"], weights=by_cell["row_count"])) if len(by_cell) else np.nan,
                        "abs_calibration_error": float(by_cell["abs_error"].mean()) if len(by_cell) else np.nan,
                        "weighted_abs_calibration_error": weighted,
                        "max_abs_cell_calibration_error": float(by_cell["abs_error"].max()) if len(by_cell) else np.nan,
                        "calibration_status": status,
                    }
                )
    return pd.DataFrame(rows)


def mean_or_nan(series: pd.Series) -> float:
    values = finite_numeric(series)
    return float(values.mean()) if values.notna().any() else np.nan


def broad_threshold_for_state(panel: pd.DataFrame, state_id: str) -> float:
    if "broad_morphology_score" not in panel.columns:
        return np.nan
    train = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq("train")]
    native_n = len(train)
    treated_n = int(bool_series(train[state_id]).sum()) if state_id in train else 0
    if native_n <= 0 or treated_n <= 0:
        return np.nan
    q = max(0.0, min(1.0, 1.0 - treated_n / native_n))
    return float(finite_numeric(train["broad_morphology_score"]).quantile(q))


def residual_state_effect_row(panel: pd.DataFrame, state_id: str, split: str, config: dict[str, Any]) -> dict[str, Any]:
    native_mask = bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)
    state_mask = bool_series(panel[state_id])
    treated_mask_all = native_mask & state_mask
    control_mask_all = native_mask & ~state_mask
    treated_all = panel.loc[treated_mask_all]
    cell_counts = (
        pd.DataFrame(
            {
                "cell": panel.loc[native_mask, "residualization_cell_key"].astype(str),
                "treated": state_mask.loc[native_mask].astype(bool).to_numpy(),
                "control": (~state_mask.loc[native_mask].astype(bool)).to_numpy(),
                "winner_positive": bool_series(panel.loc[native_mask, "winner_positive"]).to_numpy(),
            },
            index=panel.loc[native_mask].index,
        )
        .groupby("cell", dropna=False)
        .agg(treated_n=("treated", "sum"), control_n=("control", "sum"), positive_n=("winner_positive", "sum"))
    )
    th = config.get("residualization", {})
    min_treated = int(th.get("min_treated_per_cell", 20))
    min_control = int(th.get("min_control_per_cell", 50))
    min_positive = int(th.get("min_positive_per_split", 50))
    supported = cell_counts.loc[cell_counts["treated_n"].ge(min_treated) & cell_counts["control_n"].ge(min_control)]
    supported_cells = set(supported.index.astype(str).tolist())
    treated_mask = treated_mask_all & panel["residualization_cell_key"].astype(str).isin(supported_cells)
    control_mask = control_mask_all & panel["residualization_cell_key"].astype(str).isin(supported_cells)
    treated = panel.loc[treated_mask]
    control = panel.loc[control_mask]
    supported_treated_positive_n = int(bool_series(treated.get("winner_positive", pd.Series(False, index=treated.index))).sum())
    support_status = "pass" if len(supported_cells) and supported_treated_positive_n >= min_positive else "insufficient_support"
    threshold = broad_threshold_for_state(panel, state_id)
    broad_score = finite_numeric(panel["broad_morphology_score"]) if "broad_morphology_score" in panel.columns else pd.Series(np.nan, index=panel.index)
    broad_mask = native_mask & broad_score.ge(threshold)
    broad_excl = broad_mask & ~bool_series(panel[state_id])
    min_broad = int(config.get("thresholds", {}).get("broad_baseline_min_control_n", 50))
    comparator_overlap_caveat = bool(int(broad_excl.sum()) < min_broad)
    broad_rows = panel.loc[broad_mask if comparator_overlap_caveat else broad_excl]
    compression_base = bool_series(panel["compression_base"]) if "compression_base" in panel.columns else pd.Series(False, index=panel.index)
    comp_base = panel.loc[native_mask & compression_base & ~bool_series(panel[state_id])]
    native_n = int(native_mask.sum())
    treated_n = len(treated)
    control_n = len(control)
    residual_winner_diff = mean_or_nan(treated["residual_winner_positive"]) - mean_or_nan(control["residual_winner_positive"]) if control_n else np.nan
    residual_lower_diff = mean_or_nan(treated["residual_lower_first"]) - mean_or_nan(control["residual_lower_first"]) if control_n else np.nan
    residual_fast_diff = mean_or_nan(treated["residual_fast_fail"]) - mean_or_nan(control["residual_fast_fail"]) if control_n else np.nan
    residual_utility = mean_or_nan(treated["residual_row_utility_component_50bps"])
    broad_resid_utility = mean_or_nan(broad_rows["residual_row_utility_component_50bps"])
    if pd.notna(residual_lower_diff) and residual_lower_diff > 0:
        badside_status = "caveat_left_tail_residual_positive"
    elif pd.notna(residual_fast_diff) and residual_fast_diff > 0.01:
        badside_status = "caveat_fast_fail_residual_positive"
    else:
        badside_status = "no_badside_residual_caveat"
    if support_status != "pass":
        winner_status = "insufficient_support"
    elif pd.notna(residual_winner_diff) and residual_winner_diff > 0 and pd.notna(residual_utility) and residual_utility > 0:
        winner_status = "pass"
    elif pd.notna(residual_winner_diff) and residual_winner_diff > 0:
        winner_status = "residual_readout_probability_only_no_utility"
    else:
        winner_status = "fail"
    return {
        "state_id": state_id,
        "split_bucket": split,
        "residualization_method": "cell_mean_residualization",
        "treated_n": treated_n,
        "control_n": control_n,
        "cell_count": int(treated_all["residualization_cell_key"].astype(str).nunique()) if len(treated_all) else 0,
        "supported_cell_count": len(set(control["residualization_cell_key"].astype(str).tolist())) if control_n else 0,
        "unsupported_cell_count": int(max(0, (treated_all["residualization_cell_key"].astype(str).nunique() if len(treated_all) else 0) - len(supported_cells))),
        "cell_support_status": support_status,
        "raw_winner_diff": mean_or_nan(treated["winner_positive"]) - mean_or_nan(control["winner_positive"]) if control_n else np.nan,
        "residual_winner_diff": residual_winner_diff,
        "raw_lower_first_diff": mean_or_nan(treated["lower_first"]) - mean_or_nan(control["lower_first"]) if control_n else np.nan,
        "residual_lower_first_diff": residual_lower_diff,
        "raw_fast_fail_diff": mean_or_nan(treated["fast_fail"]) - mean_or_nan(control["fast_fail"]) if control_n else np.nan,
        "residual_fast_fail_diff": residual_fast_diff,
        "raw_utility_per_entry": mean_or_nan(treated["row_utility_component_50bps"]),
        "residual_utility_per_entry": residual_utility,
        "raw_utility_total_indexed": mean_or_nan(treated["row_utility_component_50bps"]) * safe_rate(treated_n, native_n),
        "residual_utility_total_indexed": residual_utility * safe_rate(treated_n, native_n) if pd.notna(residual_utility) else np.nan,
        "residual_utility_margin_vs_broad": residual_utility - broad_resid_utility if pd.notna(residual_utility) and pd.notna(broad_resid_utility) else np.nan,
        "compression_base_residual_utility_per_entry": mean_or_nan(comp_base["residual_row_utility_component_50bps"]),
        "residual_control_definition": "primary_same_cell_native_complement",
        "broad_morphology_baseline_threshold_train_frozen": threshold,
        "broad_morphology_baseline_n": len(broad_rows),
        "comparator_overlap_caveat": comparator_overlap_caveat,
        "residual_winner_gate_status": winner_status,
        "residual_badside_readout_status": badside_status,
    }


def build_residual_state_effect_readout(panel: pd.DataFrame, dictionary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for state_id in dictionary["state_id"].astype(str):
        for split in SPLITS:
            rows.append(residual_state_effect_row(panel, state_id, split, config))
    return pd.DataFrame(rows)


@dataclass
class DesignSpec:
    numeric_cols: list[str]
    categorical_cols: list[str]
    means: dict[str, float]
    stds: dict[str, float]
    categories: dict[str, list[str]]


def feature_columns_for_set(config: dict[str, Any], feature_set: str) -> list[str]:
    clusters = config.get("feature_clusters", {})
    if feature_set == "baseline":
        names = clusters.get("cluster_drawdown_morphology", []) + clusters.get("cluster_denominator_controls", [])
    else:
        names = (
            clusters.get("cluster_drawdown_morphology", [])
            + clusters.get("cluster_denominator_controls", [])
            + clusters.get("cluster_compression", [])
            + clusters.get("cluster_position_strength", [])
            + clusters.get("cluster_participation", [])
        )
    return list(dict.fromkeys(names))


def fit_design_spec(train: pd.DataFrame, features: list[str]) -> DesignSpec:
    categorical = [c for c in features if c in {"board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket", "max_drawdown_20d_quintile", "max_drawdown_20d_decile", "compression_severity_bucket"}]
    numeric = [c for c in features if c not in categorical]
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for col in numeric:
        values = finite_numeric(train[col]) if col in train else pd.Series(np.nan, index=train.index)
        mean = float(values.mean()) if values.notna().any() else 0.0
        std = float(values.std(ddof=0)) if values.notna().any() else 1.0
        means[col] = mean
        stds[col] = std if np.isfinite(std) and std > 0 else 1.0
    categories = {col: sorted(train[col].astype(str).fillna("missing").unique().tolist()) if col in train else ["missing"] for col in categorical}
    return DesignSpec(numeric_cols=numeric, categorical_cols=categorical, means=means, stds=stds, categories=categories)


def transform_design(frame: pd.DataFrame, spec: DesignSpec) -> np.ndarray:
    parts: list[np.ndarray] = []
    for col in spec.numeric_cols:
        values = finite_numeric(frame[col]) if col in frame else pd.Series(np.nan, index=frame.index)
        values = values.fillna(spec.means[col])
        parts.append(((values - spec.means[col]) / spec.stds[col]).to_numpy(dtype=float).reshape(-1, 1))
    for col in spec.categorical_cols:
        vals = frame[col].astype(str).fillna("missing") if col in frame else pd.Series("missing", index=frame.index)
        cats = spec.categories[col]
        arr = np.zeros((len(frame), len(cats)), dtype=float)
        pos = {cat: i for i, cat in enumerate(cats)}
        for i, val in enumerate(vals):
            j = pos.get(str(val))
            if j is not None:
                arr[i, j] = 1.0
        parts.append(arr)
    if not parts:
        return np.zeros((len(frame), 1), dtype=float)
    return np.hstack(parts)


@dataclass
class FittedModel:
    target_id: str
    feature_set_id: str
    spec: DesignSpec
    model: LogisticRegression | None
    constant_probability: float | None


def fit_model(panel: pd.DataFrame, target_id: str, feature_set_id: str, features: list[str], config: dict[str, Any]) -> FittedModel:
    train = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq("train")].copy()
    spec = fit_design_spec(train, [f for f in features if f in panel.columns])
    y = bool_series(train[target_id]).astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        return FittedModel(target_id=target_id, feature_set_id=feature_set_id, spec=spec, model=None, constant_probability=float(y.mean()) if len(y) else 0.0)
    x = transform_design(train, spec)
    model = LogisticRegression(C=float(config.get("model", {}).get("l2_C", 0.5)), penalty="l2", solver="liblinear", max_iter=int(config.get("model", {}).get("max_iter", 200)))
    model.fit(x, y)
    return FittedModel(target_id=target_id, feature_set_id=feature_set_id, spec=spec, model=model, constant_probability=None)


def predict_model(fit: FittedModel, frame: pd.DataFrame) -> np.ndarray:
    if fit.model is None:
        return np.full(len(frame), float(fit.constant_probability or 0.0), dtype=float)
    x = transform_design(frame, fit.spec)
    return fit.model.predict_proba(x)[:, 1]


def utility_proxy_from_scores(frame: pd.DataFrame, scores: np.ndarray, n: int) -> float:
    if len(frame) == 0 or n <= 0:
        return np.nan
    take = min(int(n), len(frame))
    order = np.argsort(scores)[::-1][:take]
    return float(finite_numeric(frame.iloc[order]["row_utility_component_50bps"]).mean())


def model_metrics(frame: pd.DataFrame, scores: np.ndarray, target_id: str, utility_n: int) -> dict[str, float]:
    y = bool_series(frame[target_id])
    auc = auc_score(pd.Series(scores, index=frame.index), y)
    if int(y.sum()) == 0 or int((~y).sum()) == 0:
        ll = np.nan
    else:
        ll = float(log_loss(y.astype(int).to_numpy(), np.clip(scores, 1e-6, 1 - 1e-6), labels=[0, 1]))
    return {"auc": auc, "logloss": ll, "utility_proxy": utility_proxy_from_scores(frame, scores, utility_n)}


def selected_treated_n_by_split(panel: pd.DataFrame, selected_state_id: str) -> dict[str, int]:
    return {split: int((bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split) & bool_series(panel[selected_state_id])).sum()) for split in SPLITS}


def build_incremental_model_comparison(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[tuple[str, str], FittedModel]]:
    rows: list[dict[str, Any]] = []
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    top_n = selected_treated_n_by_split(panel, selected)
    fits: dict[tuple[str, str], FittedModel] = {}
    baseline_features = feature_columns_for_set(config, "baseline")
    augmented_features = feature_columns_for_set(config, "augmented")
    for target in MODEL_TARGETS:
        fits[(target, "baseline")] = fit_model(panel, target, "baseline", baseline_features, config)
        fits[(target, "augmented")] = fit_model(panel, target, "augmented", augmented_features, config)
        for split in EVAL_SPLITS:
            frame = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)].copy()
            base_scores = predict_model(fits[(target, "baseline")], frame)
            aug_scores = predict_model(fits[(target, "augmented")], frame)
            base_metrics = model_metrics(frame, base_scores, target, top_n[split])
            aug_metrics = model_metrics(frame, aug_scores, target, top_n[split])
            auc_delta = aug_metrics["auc"] - base_metrics["auc"] if pd.notna(aug_metrics["auc"]) and pd.notna(base_metrics["auc"]) else np.nan
            utility_delta = aug_metrics["utility_proxy"] - base_metrics["utility_proxy"] if pd.notna(aug_metrics["utility_proxy"]) and pd.notna(base_metrics["utility_proxy"]) else np.nan
            logloss_delta = base_metrics["logloss"] - aug_metrics["logloss"] if pd.notna(aug_metrics["logloss"]) and pd.notna(base_metrics["logloss"]) else np.nan
            rows.append(
                {
                    "model_family": str(config.get("model", {}).get("family", "low_capacity_logistic_l2")),
                    "target_id": target,
                    "split_bucket": split,
                    "baseline_feature_set_metric_auc": base_metrics["auc"],
                    "augmented_feature_set_metric_auc": aug_metrics["auc"],
                    "auc_delta": auc_delta,
                    "baseline_feature_set_utility_proxy": base_metrics["utility_proxy"],
                    "augmented_feature_set_utility_proxy": aug_metrics["utility_proxy"],
                    "utility_delta": utility_delta,
                    "baseline_logloss": base_metrics["logloss"],
                    "augmented_logloss": aug_metrics["logloss"],
                    "logloss_delta": logloss_delta,
                    "incremental_status": "pass" if pd.notna(auc_delta) and auc_delta > 0 and pd.notna(utility_delta) and utility_delta > 0 else ("auc_only_no_utility" if pd.notna(auc_delta) and auc_delta > 0 else "fail"),
                }
            )
    return pd.DataFrame(rows), fits


def grouped_permute_cluster(frame: pd.DataFrame, cluster_features: list[str], group_cols: list[str], rng: np.random.Generator) -> pd.DataFrame:
    out = frame.copy()
    features = [f for f in cluster_features if f in out.columns]
    if not features:
        return out
    for _, idx in out.groupby(group_cols, dropna=False, sort=False).groups.items():
        idx_list = list(idx)
        if len(idx_list) <= 1:
            continue
        permuted = rng.permutation(idx_list)
        out.loc[idx_list, features] = out.loc[permuted, features].to_numpy()
    return out


def build_clustered_mda(panel: pd.DataFrame, config: dict[str, Any], fits: dict[tuple[str, str], FittedModel]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rng_seed = int(config.get("model", {}).get("random_seed", 13013))
    permutation_n = int(config.get("model", {}).get("permutation_n", 10))
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    top_n = selected_treated_n_by_split(panel, selected)
    clusters = config.get("feature_clusters", {})
    group_cols = ["board_bucket", "calendar_year", "max_drawdown_20d_quintile"]
    target_metric = {"winner_positive": "auc", "lower_first": "auc", "fast_fail": "auc", "utility_positive_50bps": "utility_proxy"}
    for target in MODEL_TARGETS:
        fit = fits[(target, "augmented")]
        metric_id = target_metric[target]
        for split in EVAL_SPLITS:
            frame = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split)].copy()
            base_scores = predict_model(fit, frame)
            base_metrics = model_metrics(frame, base_scores, target, top_n[split])
            baseline_metric = base_metrics[metric_id]
            for cluster_id, features in clusters.items():
                vals: list[float] = []
                for i in range(permutation_n):
                    rng = np.random.default_rng(rng_seed + int(stable_hash(f"{target}|{split}|{cluster_id}|{i}")[:8], 16))
                    permuted = grouped_permute_cluster(frame, list(features), group_cols, rng)
                    scores = predict_model(fit, permuted)
                    metric = model_metrics(permuted, scores, target, top_n[split])[metric_id]
                    vals.append(metric)
                arr = np.asarray(vals, dtype=float)
                perm_mean = float(np.nanmean(arr)) if len(arr) else np.nan
                perm_std = float(np.nanstd(arr, ddof=1)) if len(arr) > 1 else 0.0
                importance = baseline_metric - perm_mean if metric_id in {"auc", "utility_proxy"} else perm_mean - baseline_metric
                se = perm_std / math.sqrt(len(arr)) if len(arr) else np.nan
                ci_low = importance - 1.64 * se if pd.notna(importance) and pd.notna(se) else np.nan
                ci_high = importance + 1.64 * se if pd.notna(importance) and pd.notna(se) else np.nan
                rows.append(
                    {
                        "model_id": "augmented_low_capacity_logistic_l2",
                        "target_id": target,
                        "split_bucket": split,
                        "metric_id": metric_id,
                        "cluster_id": cluster_id,
                        "baseline_metric": baseline_metric,
                        "permuted_metric_mean": perm_mean,
                        "permuted_metric_std": perm_std,
                        "mda_importance": importance,
                        "mda_importance_ci_low": ci_low,
                        "mda_importance_ci_high": ci_high,
                        "permutation_n": permutation_n,
                        "importance_status": "positive_ci" if pd.notna(ci_low) and ci_low > 0 else ("positive_mean" if pd.notna(importance) and importance > 0 else "not_positive"),
                    }
                )
    return pd.DataFrame(rows)


def event_touch_offsets(events: pd.DataFrame) -> pd.Series:
    horizon = finite_numeric(events.get("horizon_sessions", pd.Series(20, index=events.index))).fillna(20)
    ttu = finite_numeric(events.get("time_to_upper", pd.Series(np.nan, index=events.index)))
    ttl = finite_numeric(events.get("time_to_lower", pd.Series(np.nan, index=events.index)))
    upper_first = bool_series(events.get("upper_first", pd.Series(False, index=events.index)))
    lower_first = bool_series(events.get("lower_first", pd.Series(False, index=events.index)))
    same_bar = bool_series(events.get("same_bar_conflict", pd.Series(False, index=events.index)))
    offset = horizon.copy()
    offset.loc[upper_first & ttu.notna()] = ttu.loc[upper_first & ttu.notna()]
    offset.loc[(lower_first | same_bar) & ttl.notna()] = ttl.loc[(lower_first | same_bar) & ttl.notna()]
    both = ttu.notna() & ttl.notna() & ~(upper_first | lower_first | same_bar)
    offset.loc[both] = np.minimum(ttu.loc[both], ttl.loc[both])
    return offset


def exact_uniqueness(events: pd.DataFrame) -> tuple[pd.Series, list[int], str]:
    if events.empty:
        return pd.Series(dtype=float), [], "pass_with_exact_t1"
    if not {"instrument", "entry_pos"} <= set(events.columns):
        return pd.Series(np.nan, index=events.index, dtype=float), [], "t1_unavailable"
    start = finite_numeric(events["entry_pos"])
    offset = event_touch_offsets(events)
    end = start + offset
    valid = start.notna() & end.notna() & end.ge(start)
    if not bool(valid.all()):
        return pd.Series(np.nan, index=events.index, dtype=float), [], "t1_unavailable"
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


def build_sample_uniqueness(panel: pd.DataFrame, dictionary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for state_id in dictionary["state_id"].astype(str):
        for split in SPLITS:
            events = panel.loc[bool_series(panel["native_scope"]) & panel["split_bucket"].eq(split) & bool_series(panel[state_id])].copy()
            if {"instrument", "reference_date"} <= set(events.columns):
                month = pd.to_datetime(events["reference_date"], errors="coerce").dt.to_period("M").astype(str)
                blocks = events["instrument"].astype(str) + "|" + month
            else:
                blocks = pd.Series(events.index.astype(str), index=events.index)
            block_counts = blocks.value_counts()
            avg_uniqueness, concurrency_values, exact_status = exact_uniqueness(events)
            exact_ok = exact_status == "pass_with_exact_t1"
            rows.append(
                {
                    "state_id": state_id,
                    "split_bucket": split,
                    "event_n": len(events),
                    "t1_reconstruction_status": "exact_t1_reconstructed" if exact_ok else "t1_unavailable",
                    "mean_average_uniqueness": float(avg_uniqueness.mean()) if exact_ok and len(avg_uniqueness) else np.nan,
                    "median_average_uniqueness": float(avg_uniqueness.median()) if exact_ok and len(avg_uniqueness) else np.nan,
                    "p25_average_uniqueness": float(avg_uniqueness.quantile(0.25)) if exact_ok and len(avg_uniqueness) else np.nan,
                    "p10_average_uniqueness": float(avg_uniqueness.quantile(0.10)) if exact_ok and len(avg_uniqueness) else np.nan,
                    "mean_concurrency": float(np.mean(concurrency_values)) if exact_ok and concurrency_values else np.nan,
                    "p95_concurrency": float(np.quantile(concurrency_values, 0.95)) if exact_ok and concurrency_values else np.nan,
                    "instrument_month_block_n": int(len(block_counts)),
                    "mean_rows_per_block": float(block_counts.mean()) if len(block_counts) else np.nan,
                    "p95_rows_per_block": float(block_counts.quantile(0.95)) if len(block_counts) else np.nan,
                    "effective_block_n": float((block_counts.sum() ** 2) / (block_counts.pow(2).sum())) if len(block_counts) and block_counts.pow(2).sum() > 0 else np.nan,
                    "overlap_status": "exact_t1_event_span" if exact_ok else "instrument_month_block_proxy_only",
                    "sample_uniqueness_gate_status": "pass_with_exact_t1" if exact_ok else "pass_with_downstream_exact_t1_requirement",
                    "downstream_requirement_requires_exact_t1_rebuild": not exact_ok,
                }
            )
    return pd.DataFrame(rows)


def build_search_audit(config: dict[str, Any]) -> pd.DataFrame:
    clusters = config.get("feature_clusters", {})
    anchor_n = len(MORPHOLOGY_ANCHORS)
    target_n = len(MODEL_TARGETS)
    model_family_n = 1
    return pd.DataFrame(
        [
            {
                "required_state_n": 6,
                "selected_state_id": str(config.get("selected_state_id", "repair_range_participation_core_30")),
                "posthoc_after_13a3_report": True,
                "validation_seen_before_requirement": True,
                "robustness_seen_before_requirement": True,
                "feature_cluster_n": len(clusters),
                "anchor_n": anchor_n,
                "model_family_n": model_family_n,
                "target_n": target_n,
                "effective_search_space_n": 6 * len(clusters) * anchor_n * model_family_n * target_n,
                "hyperparameter_search_used": False,
                "validation_used_for_selection": False,
                "robustness_used_for_selection": False,
                "confirmatory_status": False,
                "search_accounting_status": "diagnostic_posthoc_not_confirmatory",
            }
        ]
    )


def residual_winner_gate_status(readout: pd.DataFrame, selected_state_id: str) -> str:
    rows = readout.loc[readout["state_id"].astype(str).eq(selected_state_id) & readout["split_bucket"].isin(EVAL_SPLITS)]
    if len(rows) != 2:
        return "fail"
    if "cell_support_status" in rows.columns and rows["cell_support_status"].astype(str).ne("pass").any():
        return "insufficient_support"
    if "residual_winner_gate_status" in rows.columns and rows["residual_winner_gate_status"].astype(str).eq("insufficient_support").any():
        return "insufficient_support"
    winner = finite_numeric(rows["residual_winner_diff"]).gt(0).all()
    utility = finite_numeric(rows["residual_utility_per_entry"]).gt(0).all()
    if winner and utility:
        return "pass"
    if winner:
        return "residual_readout_probability_only_no_utility"
    return "fail"


def residual_badside_status(readout: pd.DataFrame, selected_state_id: str) -> str:
    rows = readout.loc[readout["state_id"].astype(str).eq(selected_state_id) & readout["split_bucket"].isin(EVAL_SPLITS)]
    if finite_numeric(rows["residual_lower_first_diff"]).gt(0).any():
        return "caveat_left_tail_residual_positive"
    if finite_numeric(rows["residual_fast_fail_diff"]).gt(0.01).any():
        return "caveat_fast_fail_residual_positive"
    return "no_badside_residual_caveat"


def residual_calibration_status(calibration: pd.DataFrame) -> str:
    sub = calibration.loc[calibration["split_bucket"].isin(EVAL_SPLITS)]
    if sub.empty or sub["calibration_status"].astype(str).eq("insufficient_calibration_support").all():
        return "insufficient_calibration_support"
    if sub["calibration_status"].astype(str).eq("residual_drift_caveat").any():
        return "residual_drift_caveat"
    return "calibration_pass"


def clustered_mda_gate_status(mda: pd.DataFrame) -> str:
    non_morph_clusters = ["cluster_position_strength", "cluster_participation"]
    drawdown_positive = False
    for cluster_id in ["cluster_drawdown_morphology"]:
        rows = mda.loc[mda["cluster_id"].eq(cluster_id) & mda["target_id"].eq("winner_positive") & mda["split_bucket"].isin(EVAL_SPLITS)]
        drawdown_positive = drawdown_positive or (len(rows) == 2 and finite_numeric(rows["mda_importance_ci_low"]).gt(0).all())
    for cluster_id in non_morph_clusters:
        auc_rows = mda.loc[mda["cluster_id"].eq(cluster_id) & mda["target_id"].eq("winner_positive") & mda["split_bucket"].isin(EVAL_SPLITS)]
        util_rows = mda.loc[mda["cluster_id"].eq(cluster_id) & mda["target_id"].eq("utility_positive_50bps") & mda["split_bucket"].isin(EVAL_SPLITS)]
        auc_ok = len(auc_rows) == 2 and finite_numeric(auc_rows["mda_importance_ci_low"]).gt(0).all()
        util_ok = len(util_rows) == 2 and finite_numeric(util_rows["mda_importance"]).gt(0).all()
        if auc_ok and util_ok:
            return "pass"
        if auc_ok and not util_ok:
            return "residual_importance_no_utility_translation"
    if drawdown_positive:
        return "morphology_only_importance"
    return "fail"


def incremental_gate_status(incremental: pd.DataFrame) -> str:
    rows = incremental.loc[incremental["target_id"].eq("winner_positive") & incremental["split_bucket"].isin(EVAL_SPLITS)]
    if len(rows) == 2 and finite_numeric(rows["auc_delta"]).gt(0).all() and finite_numeric(rows["utility_delta"]).gt(0).all():
        return "pass"
    if len(rows) == 2 and finite_numeric(rows["auc_delta"]).gt(0).all():
        return "auc_only_no_utility"
    return "fail"


def sample_uniqueness_gate_status(uniqueness: pd.DataFrame, selected_state_id: str) -> tuple[str, bool]:
    rows = uniqueness.loc[uniqueness["state_id"].astype(str).eq(selected_state_id) & uniqueness["split_bucket"].isin(EVAL_SPLITS)]
    if rows.empty:
        return "exact_uniqueness_unavailable", False
    statuses = set(rows["sample_uniqueness_gate_status"].astype(str).tolist())
    downstream = bool(rows["downstream_requirement_requires_exact_t1_rebuild"].astype(bool).any())
    if "pass_with_exact_t1" in statuses:
        return "pass_with_exact_t1", downstream
    if "pass_with_downstream_exact_t1_requirement" in statuses:
        return "pass_with_downstream_exact_t1_requirement", True
    return "exact_uniqueness_unavailable", downstream


def build_decision(
    input_status: str,
    upstream_status: str,
    upstream_reason: str,
    row_status: str,
    anchor_status: str,
    residualization_status: str,
    residual_readout: pd.DataFrame,
    calibration: pd.DataFrame,
    mda: pd.DataFrame,
    incremental: pd.DataFrame,
    uniqueness: pd.DataFrame,
    search: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    residual_gate = residual_winner_gate_status(residual_readout, selected)
    badside = residual_badside_status(residual_readout, selected)
    cal_status = residual_calibration_status(calibration)
    mda_status = clustered_mda_gate_status(mda)
    inc_status = incremental_gate_status(incremental)
    unique_status, downstream_t1 = sample_uniqueness_gate_status(uniqueness, selected)
    search_status = str(search.iloc[0]["search_accounting_status"]) if len(search) else "missing"
    decision_state = "13C_authorize_meta_labeling_feasibility_preflight"
    reason = "all_primary_gates_pass"
    if upstream_status == "fail_already_authorized":
        decision_state = "13C_blocked_upstream_13a3_already_authorized"
        reason = "upstream_13a3_already_authorized"
    elif input_status != "pass" or upstream_status != "pass":
        decision_state = "13C_blocked_input_or_lineage_failure"
        reason = "input_or_upstream_lineage_failure" if upstream_reason == "" else upstream_reason
    elif row_status != "pass":
        decision_state = "13C_blocked_row_level_rebuild_failure"
        reason = "row_level_rebuild_failure"
    elif anchor_status != "pass":
        decision_state = "13C_stop_morphology_anchor_unavailable"
        reason = "morphology_anchor_unavailable"
    elif residual_gate in {"fail", "insufficient_support"}:
        decision_state = "13C_stop_no_morphology_orthogonal_residual_effect"
        reason = "residual_support_insufficient" if residual_gate == "insufficient_support" else "residual_winner_gate_failed"
    elif residual_gate == "residual_readout_probability_only_no_utility":
        decision_state = "13C_stop_residual_probability_only_no_utility"
        reason = "residual_winner_positive_but_utility_non_positive"
    elif mda_status == "morphology_only_importance":
        decision_state = "13C_stop_morphology_only_importance"
        reason = "clustered_mda_morphology_only"
    elif mda_status in {"residual_importance_no_utility_translation", "fail"}:
        decision_state = "13C_stop_residual_importance_no_utility_translation"
        reason = "clustered_mda_non_morphology_no_utility_translation"
    elif inc_status != "pass":
        decision_state = "13C_stop_residual_importance_no_utility_translation"
        reason = "incremental_model_utility_gate_failed"
    elif unique_status == "exact_uniqueness_unavailable" and not downstream_t1:
        decision_state = "13C_stop_uniqueness_unavailable_for_downstream"
        reason = "exact_t1_unavailable_without_downstream_requirement"
    positive = decision_state == "13C_authorize_meta_labeling_feasibility_preflight"
    residual_drift = cal_status == "residual_drift_caveat"
    next_req = "requirement_13d_compression_repair_meta_labeling_feasibility_preflight.md" if positive else "none"
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": next_req,
                "sequence_mining_authorized": False,
                "meta_labeling_authorized": bool(positive),
                "bet_sizing_authorized": False,
                "selected_state_id": selected,
                "effect_interpretation": "morphology_orthogonal_residual_diagnostic_only_with_residual_drift_caveat" if positive and residual_drift else ("morphology_orthogonal_residual_diagnostic_only" if positive else "none"),
                "confirmatory_status": False,
                "input_gate_status": input_status,
                "upstream_lineage_gate_status": upstream_status,
                "row_level_rebuild_gate_status": row_status,
                "morphology_anchor_gate_status": anchor_status,
                "residualization_gate_status": residualization_status,
                "residual_winner_gate_status": residual_gate,
                "residual_badside_readout_status": badside,
                "residual_calibration_status": cal_status,
                "clustered_mda_gate_status": mda_status,
                "incremental_utility_gate_status": inc_status,
                "sample_uniqueness_gate_status": unique_status,
                "downstream_requirement_requires_exact_t1_rebuild": bool(downstream_t1 and positive),
                "residual_drift_caveat_from_13c": bool(residual_drift),
                "calibration_recheck_required": bool(residual_drift),
                "search_accounting_status": search_status,
                "primary_failure_reason": reason,
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
    readout: pd.DataFrame,
    incremental: pd.DataFrame,
    mda: pd.DataFrame,
    uniqueness: pd.DataFrame,
    calibration: pd.DataFrame,
    residual_design: pd.DataFrame,
) -> str:
    dec = decision.iloc[0]
    selected = str(dec["selected_state_id"])
    selected_readout = readout.loc[readout["state_id"].astype(str).eq(selected) & readout["split_bucket"].isin(EVAL_SPLITS)]
    selected_uniqueness = uniqueness.loc[uniqueness["state_id"].astype(str).eq(selected)]
    selected_cal = calibration.loc[calibration["split_bucket"].isin(EVAL_SPLITS)]
    positive_text = "存在" if dec["decision_state"] == "13C_authorize_meta_labeling_feasibility_preflight" else "不存在"
    exact_t1 = bool(len(selected_uniqueness) and selected_uniqueness["sample_uniqueness_gate_status"].astype(str).eq("pass_with_exact_t1").any())
    uniqueness_text = (
        "Exact `t1` event span 已用 `entry_pos + first-touch/vertical-horizon offset` 重建；表内 average uniqueness / concurrency 为 exact event-span overlap readout，instrument-month block 只保留为 proxy context。"
        if exact_t1
        else "Exact `t1` event span 当前未从 qfq bars 重建；本轮报告 instrument-month block overlap proxy。若其他 gate positive，13D 必须重建 exact `t1` 与 average uniqueness 后才能训练任何 meta-labeling model。"
    )
    lines = [
        "# 13C Morphology-Orthogonal Residual Importance Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"单行裁决：selected state `{selected}` 的 morphology-orthogonal residual information `{positive_text}`；`decision_state = {dec['decision_state']}`。",
        "",
        f"- `next_allowed_requirement`: `{dec['next_allowed_requirement']}`",
        f"- `sequence_mining_authorized`: `{boolish(dec['sequence_mining_authorized'])}`",
        f"- `meta_labeling_authorized`: `{boolish(dec['meta_labeling_authorized'])}`",
        f"- `bet_sizing_authorized`: `{boolish(dec['bet_sizing_authorized'])}`",
        f"- `primary_failure_reason`: `{dec['primary_failure_reason']}`",
        "",
        "13C 不推翻 13A3。13A3 否决的是 direct winner-buy / sequence mining 的 total native effect；13C 只检查 broad drawdown / reversal morphology 被剥离后是否还剩 residual information。即使 13C 为 positive，下一步也只是独立的 meta-labeling feasibility preflight，不授权 13B sequence mining、不授权 bet sizing。",
        "",
        "## Residualization 设计",
        "",
        "Residual expectation 使用 train-only cell mean residualization。Primary cell 为 board、calendar year、liquidity bucket、volatility bucket、max_drawdown decile 与 compression severity bucket；validation / robustness 的 unseen cell 只按预注册 fallback 层级回退，不用 OOS label refit expectation。",
        "",
        md_table(residual_design, ["target_id", "split_bucket", "cell_scope", "row_count", "fit_scope", "validation_labels_used_to_fit_expectation", "robustness_labels_used_to_fit_expectation", "purge_window_sessions", "embargo_sessions"], 18),
        "",
        "## Selected State Raw vs Residual Readout",
        "",
        "Row-level utility component 用于 residualization / model target；13A3 的 median-barrier aggregate utility 仍只是 lineage readout，二者不混作同一数。",
        "",
        md_table(selected_readout, ["split_bucket", "treated_n", "control_n", "cell_count", "supported_cell_count", "unsupported_cell_count", "cell_support_status", "raw_winner_diff", "residual_winner_diff", "raw_lower_first_diff", "residual_lower_first_diff", "raw_fast_fail_diff", "residual_fast_fail_diff", "raw_utility_per_entry", "residual_utility_per_entry", "residual_utility_margin_vs_broad", "residual_winner_gate_status", "residual_badside_readout_status"], 10),
        "",
        "## Baseline vs Augmented Model",
        "",
        "Baseline model 只使用 drawdown morphology 与 denominator controls；augmented model 额外加入 compression、position strength 与 participation clusters。`model_utility_proxy` 是 evaluation split 内 top-N 排序的乐观上界，decision 只依赖 validation / robustness 的 `utility_delta` 符号一致性，不依赖绝对 utility 水平。",
        "",
        md_table(incremental.loc[incremental["target_id"].eq("winner_positive")], ["split_bucket", "baseline_feature_set_metric_auc", "augmented_feature_set_metric_auc", "auc_delta", "baseline_feature_set_utility_proxy", "augmented_feature_set_utility_proxy", "utility_delta", "incremental_status"], 10),
        "",
        "## Clustered MDA",
        "",
        md_table(mda.loc[mda["target_id"].isin(["winner_positive", "utility_positive_50bps"])], ["target_id", "split_bucket", "metric_id", "cluster_id", "baseline_metric", "permuted_metric_mean", "mda_importance", "mda_importance_ci_low", "importance_status"], 40),
        "",
        "## Sample Uniqueness / Overlap",
        "",
        uniqueness_text,
        "",
        md_table(selected_uniqueness, ["split_bucket", "event_n", "t1_reconstruction_status", "instrument_month_block_n", "mean_rows_per_block", "p95_rows_per_block", "effective_block_n", "sample_uniqueness_gate_status", "downstream_requirement_requires_exact_t1_rebuild"], 10),
        "",
        "## Residual Calibration Caveat",
        "",
        "Residual calibration 比较 train-fitted expected cell rates 与 validation / robustness realized rates。若触发 `residual_drift_caveat`，说明 residual winner 仍可能吸收 calendar / regime drift，13D 必须重检 calibration。",
        "",
        md_table(selected_cal, ["target_id", "split_bucket", "cell_scope", "row_count", "predicted_mean_from_train", "realized_mean_in_split", "weighted_abs_calibration_error", "calibration_status"], 30),
        "",
        "## Bad-side Caveat",
        "",
        f"`residual_badside_readout_status = {dec['residual_badside_readout_status']}`。Residual lower-first / fast-fail caveat 不 hard-block 13C winner residual question，但若进入 13D，必须进入 meta-labeling risk controls。",
        "",
        "## Negative / Positive Boundary",
        "",
        "若本轮 negative，应按 decision_state 区分：no residual effect、probability-only residual without utility、morphology-only importance、residual importance no utility translation，或 uniqueness / event-span 不可审计。若 positive，也只能授权 feasibility preflight，不产生交易、仓位、资金曲线或 alpha 结论。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if "local_cache" not in path.parts and key != "manifest"}


def schema_hash(path: Path) -> str:
    return r13a3.schema_hash(path)


def build_manifest(config_path: Path, config: dict[str, Any], outputs: dict[str, Path], input_audit: pd.DataFrame) -> dict[str, Any]:
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
        "local_cache_outputs_excluded": [str(path) for path in outputs.values() if "local_cache" in path.parts],
        "local_cache_audit": [
            {
                "artifact_id": key,
                "path": str(path),
                "exists": path.exists(),
                "row_count": count_rows(path) if path.exists() else np.nan,
                "schema_hash": schema_hash(path),
                "cache_used_as_input": False,
            }
            for key, path in outputs.items()
            if "local_cache" in path.parts
        ],
    }


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    upstream, upstream_status, upstream_reason = build_upstream_lineage_audit(resolved)
    if check_inputs_only or mode == "check-inputs":
        write_df(outputs["upstream_lineage_audit"], upstream)
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
        return outputs

    native_panel, filter_matrix, base_panel, state_matrix, dictionary, upstream_badside, cache_lineage, cache_status, cache_reason, base_threshold = load_verified_inputs(config, resolved)
    upstream = pd.concat([upstream, cache_lineage], ignore_index=True)
    if upstream_status == "pass" and cache_status != "pass":
        upstream_status = "fail"
        upstream_reason = cache_reason
    elif upstream_status == "pass":
        upstream_reason = cache_reason if cache_reason else upstream_reason
    write_df(outputs["upstream_lineage_audit"], upstream)
    rebuilt_state_matrix = r13a3.build_composite_state_matrix(native_panel, filter_matrix, dictionary)

    panel = prepare_row_level_panel(native_panel, state_matrix, base_panel, config, resolved)
    panel, bucket_edges = fit_train_frozen_buckets(panel, base_threshold, config)
    panel, zstats = apply_morphology_scores(panel)
    row_audit = build_row_level_rebuild_audit(panel, state_matrix, rebuilt_state_matrix, config)
    row_status, _row_reason = table_gate_status(row_audit, "status", {"pass"})
    utility_recon = build_utility_reconciliation(panel, dictionary, upstream_badside, config)
    anchor_dict = build_morphology_anchor_dictionary(panel, zstats, bucket_edges)
    anchor_status, _anchor_reason = table_gate_status(anchor_dict.loc[anchor_dict["anchor_id"].isin(MORPHOLOGY_ANCHORS)], "anchor_status", {"pass"})
    feature_clusters = build_feature_cluster_dictionary(panel, config)
    feature_status, _feature_reason = feature_cluster_gate_status(feature_clusters)
    if anchor_status == "pass" and feature_status != "pass":
        anchor_status = "fail"

    panel, residual_design = add_residuals(panel)
    residualization_status, _residualization_reason = table_gate_status(residual_design, "design_status", {"pass"})
    residual_calibration = build_residual_calibration(panel, config)
    residual_readout = build_residual_state_effect_readout(panel, dictionary, config)
    incremental, fits = build_incremental_model_comparison(panel, config)
    mda = build_clustered_mda(panel, config, fits)
    uniqueness = build_sample_uniqueness(panel, dictionary, config)
    search = build_search_audit(config)
    decision = build_decision(
        input_status if input_status == "pass" else f"fail:{input_reason}",
        upstream_status,
        upstream_reason,
        row_status,
        anchor_status,
        residualization_status,
        residual_readout,
        residual_calibration,
        mda,
        incremental,
        uniqueness,
        search,
        config,
    )

    write_df(outputs["row_level_rebuild_audit"], row_audit)
    write_df(outputs["utility_reconciliation_audit"], utility_recon)
    write_df(outputs["morphology_anchor_dictionary"], anchor_dict)
    write_df(outputs["feature_cluster_dictionary"], feature_clusters)
    write_df(outputs["residualization_design_audit"], residual_design)
    write_df(outputs["residual_calibration_audit"], residual_calibration)
    write_df(outputs["residual_state_effect_readout"], residual_readout)
    write_df(outputs["clustered_mda_importance"], mda)
    write_df(outputs["incremental_model_comparison"], incremental)
    write_df(outputs["sample_uniqueness_audit"], uniqueness)
    write_df(outputs["search_multiplicity_audit"], search)
    write_df(outputs["morphology_orthogonal_residual_importance_decision"], decision)
    write_df(outputs["morphology_residual_panel"], panel)
    write_text(outputs["report"], render_report(decision, residual_readout, incremental, mda, uniqueness, residual_calibration, residual_design))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
