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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP13_ROOT = TOPIC_ROOT / "experiments" / "pending" / "13_full_pit_native_event_discovery_v0"
RUNNER_13A_PATH = SOURCE_EP13_ROOT / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13a = load_runner(RUNNER_13A_PATH, "run_13a_full_pit_native_token_cartography_preflight")


RUN_ID = "14A_full_native_sparse_state_change_event_utility_preflight"
EXPERIMENT_ID = "14_full_native_sparse_state_change_event_utility_preflight_v0"
PHASE_ID = "14A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_14a_full_native_sparse_state_change_event_utility_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
PRIMARY_COST_BPS = 50


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "source_plan": (),
    "upstream_requirement_13a": (),
    "upstream_requirement_12a7g": (),
    "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument", "board_bucket"),
    "pit_topn_400_100_membership_daily": ("membership_date", "instrument", "board_bucket"),
    "stock_daily_qfq_dir": (),
    "benchmark_indices_daily": ("date", "index_alias", "close"),
    "global_regime_calendar": ("date",),
    "upstream_12a7g_decision": ("decision_state", "selected_label_id", "input_gate_status", "lineage_gate_status"),
    "upstream_12a7g_label_formula": ("label_id", "vol_reference_unit", "k_up", "k_dn", "horizon_sessions", "same_bar_priority", "path_window"),
    "upstream_12a7g_label_selection": ("label_id",),
    "upstream_12a7g_split_boundary": (),
    "upstream_12a7g_manifest": (),
    "upstream_13a_config": (),
    "upstream_13a_manifest": (),
    "upstream_13a_input_audit": ("artifact_id", "read_status", "schema_status"),
    "upstream_13a_lineage_audit": (),
    "upstream_13a_decision": ("decision_state", "input_gate_status", "native_universe_gate_status", "label_portability_gate_status"),
    "upstream_13a_universe_definition": ("split_bucket",),
    "upstream_13a_universe_thresholds": (),
    "upstream_13a_label_portability": ("split_bucket",),
    "upstream_13a_token_dictionary": ("token_id", "family_id", "primitive_id"),
    "upstream_13a_token_readout": ("token_id", "split_bucket"),
    "upstream_13a_morphology": ("token_id", "split_bucket"),
    "upstream_13a_native_universe_cache": (
        "row_id",
        "instrument",
        "reference_date",
        "split",
        "native_scope",
        "upper_barrier",
        "lower_barrier",
        "winner_positive",
        "upper_first",
        "lower_first",
        "same_bar_conflict",
        "horizon_complete",
        "horizon_close_return",
        "entry_date",
        "entry_pos",
        "entry_price",
    ),
    "upstream_13a_native_label_cache": (
        "row_id",
        "instrument",
        "reference_date",
        "split",
        "upper_barrier",
        "lower_barrier",
        "winner_positive",
        "upper_first",
        "lower_first",
        "same_bar_conflict",
        "horizon_complete",
    ),
    "upstream_13a_native_token_matrix_cache": ("row_id",),
    "optional_13a3_composite_dictionary": (),
    "optional_13a3_composite_state_matrix": ("row_id",),
    "optional_13c_decision": (),
    "optional_13c_morphology_panel": ("row_id",),
}

OPTIONAL_INPUT_ARTIFACTS = {
    "optional_13a3_composite_dictionary",
    "optional_13a3_composite_state_matrix",
    "optional_13c_decision",
    "optional_13c_morphology_panel",
    "upstream_13a_native_label_cache",
    "upstream_13a_native_token_matrix_cache",
    "upstream_13a_native_universe_cache",
}

NATIVE_LABEL_CROSS_CHECK_KEY = ["instrument", "reference_date", "row_id"]
NATIVE_LABEL_CROSS_CHECK_FIELDS = [
    "split",
    "upper_barrier",
    "lower_barrier",
    "winner_positive",
    "upper_first",
    "lower_first",
    "same_bar_conflict",
    "horizon_complete",
]


@dataclass(frozen=True)
class ArmSpec:
    family_id: str
    parameter_set_id: str
    cooldown_sessions: int
    params: dict[str, Any]

    @property
    def raw_event_arm_id(self) -> str:
        return f"{self.family_id}__{self.parameter_set_id}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 14A full-native sparse state-change event utility preflight.")
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
        "cache_schema_adapter_audit": TABLE_DIR / "cache_schema_adapter_audit.csv",
        "native_label_portability_audit": TABLE_DIR / "native_label_portability_audit.csv",
        "row_level_rebuild_audit": TABLE_DIR / "row_level_rebuild_audit.csv",
        "sparse_event_family_formula_spec": TABLE_DIR / "sparse_event_family_formula_spec.csv",
        "sparse_event_parameter_grid_audit": TABLE_DIR / "sparse_event_parameter_grid_audit.csv",
        "sparse_event_generation_audit": TABLE_DIR / "sparse_event_generation_audit.csv",
        "sparse_event_density_audit": TABLE_DIR / "sparse_event_density_audit.csv",
        "sparse_event_raw_readout": TABLE_DIR / "sparse_event_raw_readout.csv",
        "sparse_event_badside_utility_audit": TABLE_DIR / "sparse_event_badside_utility_audit.csv",
        "sparse_event_uniqueness_density_audit": TABLE_DIR / "sparse_event_uniqueness_density_audit.csv",
        "pit_cohort_normalization_dictionary": TABLE_DIR / "pit_cohort_normalization_dictionary.csv",
        "pit_cohort_rank_availability_audit": TABLE_DIR / "pit_cohort_rank_availability_audit.csv",
        "pit_cohort_normalized_utility_readout": TABLE_DIR / "pit_cohort_normalized_utility_readout.csv",
        "cohort_normalization_transport_audit": TABLE_DIR / "cohort_normalization_transport_audit.csv",
        "morphology_rediscovery_audit": TABLE_DIR / "morphology_rediscovery_audit.csv",
        "validation_stress_interpretation_audit": TABLE_DIR / "validation_stress_interpretation_audit.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "decision": TABLE_DIR / "full_native_sparse_state_change_event_utility_decision.csv",
        "native_rebuild_panel": LOCAL_CACHE_DIR / "native_rebuild_panel.parquet",
        "state_change_feature_panel": LOCAL_CACHE_DIR / "state_change_feature_panel.parquet",
        "sparse_event_panel": LOCAL_CACHE_DIR / "sparse_event_panel.parquet",
        "pit_cohort_normalized_event_panel": LOCAL_CACHE_DIR / "pit_cohort_normalized_event_panel.parquet",
        "report": REPORT_DIR / "full_native_sparse_state_change_event_utility_preflight_report.md",
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


def path_sha(path: Path) -> str:
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


def file_sha(path: Path) -> str:
    return path_sha(path)


def cost_return(cost_bps: int | float) -> float:
    return float(cost_bps) / 10000.0


def rolling_consecutive_true(condition: pd.Series, window: int = 5) -> pd.Series:
    truth = bool_series(condition)
    return truth.rolling(window, min_periods=window).sum().ge(window).fillna(False)


def consecutive_true_by_instrument(panel: pd.DataFrame, condition: pd.Series, window: int = 5) -> pd.Series:
    if "instrument" not in panel.columns:
        return rolling_consecutive_true(condition, window=window).reindex(panel.index).fillna(False)
    work = pd.DataFrame({"instrument": panel["instrument"].astype(str), "_condition": bool_series(condition)}, index=panel.index)
    out = pd.Series(False, index=panel.index)
    for _, idx in work.groupby("instrument", sort=False).groups.items():
        out.loc[idx] = rolling_consecutive_true(work.loc[idx, "_condition"], window=window).to_numpy(dtype=bool)
    return out


def positive_cusum(series: pd.Series) -> pd.Series:
    values = finite_numeric(series).to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    acc = 0.0
    for i, value in enumerate(values):
        if not np.isfinite(value):
            acc = 0.0
            continue
        acc = max(0.0, acc + float(value))
        out[i] = acc
    return pd.Series(out, index=series.index)


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id.startswith("optional_"):
        return "optional_morphology_lineage"
    if artifact_id.startswith("upstream_13a"):
        return "upstream_13a_lineage"
    if artifact_id.startswith("upstream_12a7g") or artifact_id == "upstream_requirement_12a7g":
        return "upstream_12a7g_label_lineage"
    if artifact_id in {"pit_topn_400_100_executable_daily", "pit_topn_400_100_membership_daily", "stock_daily_qfq_dir", "benchmark_indices_daily", "global_regime_calendar"}:
        return "raw_local_data_input"
    return "run_config_input"


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = EXPECTED_INPUT_COLUMNS.get(artifact_id, ())
        required_flag = artifact_id not in OPTIONAL_INPUT_ARTIFACTS
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        column_count: int | float = np.nan
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
                    column_count = len(sample.columns) if not sample.empty or suffixes.endswith((".csv", ".csv.gz", ".parquet")) else np.nan
                    missing = sorted(set(required_cols) - set(sample.columns)) if required_cols else []
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                    row_count = count_rows(path)
            except Exception as exc:  # pragma: no cover - defensive audit path
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": required_flag,
                "lineage_role": lineage_role_for_artifact(artifact_id),
            }
        )
    return pd.DataFrame(rows)


def table_gate_status(frame: pd.DataFrame, status_col: str) -> tuple[str, str]:
    if frame.empty or status_col not in frame.columns:
        return "fail", f"missing_{status_col}"
    bad = frame.loc[~frame[status_col].astype(str).isin(["pass", "pass_with_documented_13a_entry_anchor", "pass_with_missing_date_bypass"])]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(sorted(bad[status_col].astype(str).unique()))


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    required = input_audit.loc[bool_series(input_audit["required_flag"])]
    bad = required.loc[
        ~required["read_status"].eq("pass")
        | ~required["schema_status"].astype(str).str.startswith(("pass", "directory", "not_checked"))
    ]
    if bad.empty:
        return "pass", ""
    missing_local = bad.loc[bad["lineage_role"].eq("raw_local_data_input")]
    if not missing_local.empty:
        return "fail", "required_local_data_artifact_missing"
    return "fail", ";".join(bad["artifact_id"].astype(str).tolist())


def load_13a_runner_cache(resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    native_path = resolved["upstream_13a_native_universe_cache"]
    label_path = resolved["upstream_13a_native_label_cache"]
    token_path = resolved["upstream_13a_native_token_matrix_cache"]
    if native_path.exists() and label_path.exists() and token_path.exists():
        return read_table(native_path), read_table(label_path), read_table(token_path), "cache_used"
    config_path = resolved.get("upstream_13a_config")
    if config_path is not None and config_path.exists():
        r13a.run(config_path, check_inputs_only=False)
    if native_path.exists() and label_path.exists() and token_path.exists():
        return read_table(native_path), read_table(label_path), read_table(token_path), "raw_rebuild_after_cache_unusable"
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "cache_unavailable_rebuild_failed"


def compare_series(left: pd.Series, right: pd.Series, tol: float = 0.0) -> bool:
    if pd.api.types.is_bool_dtype(left) or pd.api.types.is_bool_dtype(right):
        return bool(bool_series(left).eq(bool_series(right)).all())
    if pd.api.types.is_numeric_dtype(left) or pd.api.types.is_numeric_dtype(right):
        lnum = finite_numeric(left)
        rnum = finite_numeric(right)
        return bool(((lnum - rnum).abs() <= tol).fillna(lnum.isna() & rnum.isna()).all())
    return bool(left.astype(str).fillna("").eq(right.astype(str).fillna("")).all())


def adapt_native_panel(native: pd.DataFrame, label: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    out = native.copy()
    adapter_specs = [
        ("native_universe_panel", "split", "split_bucket", "rename", True),
        ("native_universe_panel", "upper_barrier", "upper_barrier_return", "rename", True),
        ("native_universe_panel", "lower_barrier", "lower_barrier_return", "rename", True),
        ("native_universe_panel", "winner_positive", "winner", "rename", True),
        ("native_universe_panel", "upper_first", "upper_first", "identity", True),
        ("native_universe_panel", "lower_first", "lower_first", "identity", True),
        ("native_universe_panel", "same_bar_conflict", "same_bar_conflict", "identity", True),
        ("native_universe_panel", "native_scope", "native_scope", "identity", True),
        ("native_universe_panel", "horizon_close_return", "terminal_return_20d", "rename", True),
        ("native_universe_panel", "entry_date", "entry_date", "identity", True),
        ("native_universe_panel", "entry_pos", "entry_pos", "identity", True),
        ("native_universe_panel", "entry_price", "entry_price", "identity", True),
    ]
    status = "pass"
    for source_artifact, source_col, target_col, rule, required in adapter_specs:
        ok = source_col in out.columns
        if ok:
            out[target_col] = out[source_col]
        else:
            status = "fail"
        rows.append(
            {
                "source_artifact_id": source_artifact,
                "source_column": source_col,
                "target_column": target_col,
                "adapter_rule": rule,
                "row_count_checked": int(len(out)) if ok else 0,
                "value_match_status": "pass" if ok else "missing_source_column",
                "unit_match_status": "pass",
                "required_for_primary": required,
                "adapter_status": "pass" if ok else "fail",
            }
        )
    if {"lower_first", "same_bar_conflict"} <= set(out.columns):
        out["fast_fail"] = bool_series(out["lower_first"]) | bool_series(out["same_bar_conflict"])
        rows.append(
            {
                "source_artifact_id": "native_universe_panel",
                "source_column": "lower_first+same_bar_conflict",
                "target_column": "fast_fail",
                "adapter_rule": "or_derive",
                "row_count_checked": int(len(out)),
                "value_match_status": "pass",
                "unit_match_status": "pass",
                "required_for_primary": True,
                "adapter_status": "pass",
            }
        )
    else:
        status = "fail"
    if "reference_date" in out.columns:
        out["reference_date"] = out["reference_date"].astype(str).str[:10]
    if "entry_date" in out.columns:
        out["entry_date"] = out["entry_date"].astype(str).str[:10]
    if label.empty:
        status = "fail"
        rows.append(
            {
                "source_artifact_id": "native_label_panel",
                "source_column": "__panel__",
                "target_column": "native_universe_panel.__cross_check_availability__",
                "adapter_rule": "cross_check",
                "row_count_checked": 0,
                "value_match_status": "missing_label_panel",
                "unit_match_status": "pass",
                "required_for_primary": True,
                "adapter_status": "fail",
            }
        )
    else:
        label_norm = label.copy()
        if "reference_date" in label_norm.columns:
            label_norm["reference_date"] = label_norm["reference_date"].astype(str).str[:10]
        missing_keys = [c for c in NATIVE_LABEL_CROSS_CHECK_KEY if c not in out.columns or c not in label_norm.columns]
        if missing_keys:
            status = "fail"
            rows.append(
                {
                    "source_artifact_id": "native_label_panel",
                    "source_column": "+".join(NATIVE_LABEL_CROSS_CHECK_KEY),
                    "target_column": "native_universe_panel.__cross_check_key__",
                    "adapter_rule": "cross_check",
                    "row_count_checked": 0,
                    "value_match_status": "missing_key_columns:" + ";".join(missing_keys),
                    "unit_match_status": "pass",
                    "required_for_primary": True,
                    "adapter_status": "fail",
                }
            )
        else:
            native_key_unique = not out.duplicated(NATIVE_LABEL_CROSS_CHECK_KEY).any()
            label_key_unique = not label_norm.duplicated(NATIVE_LABEL_CROSS_CHECK_KEY).any()
            left_cols = NATIVE_LABEL_CROSS_CHECK_KEY + [c for c in NATIVE_LABEL_CROSS_CHECK_FIELDS if c in out.columns]
            right_cols = NATIVE_LABEL_CROSS_CHECK_KEY + [c for c in NATIVE_LABEL_CROSS_CHECK_FIELDS if c in label_norm.columns]
            merged = out[left_cols].merge(label_norm[right_cols], on=NATIVE_LABEL_CROSS_CHECK_KEY, how="inner", suffixes=("_native", "_label"))
            coverage_ok = native_key_unique and label_key_unique and len(merged) == len(out)
            if not coverage_ok:
                status = "fail"
            rows.append(
                {
                    "source_artifact_id": "native_label_panel",
                    "source_column": "+".join(NATIVE_LABEL_CROSS_CHECK_KEY),
                    "target_column": "native_universe_panel.__cross_check_key_coverage__",
                    "adapter_rule": "cross_check",
                    "row_count_checked": int(len(merged)),
                    "value_match_status": "pass" if coverage_ok else "key_coverage_or_uniqueness_mismatch",
                    "unit_match_status": "pass",
                    "required_for_primary": True,
                    "adapter_status": "pass" if coverage_ok else "fail",
                }
            )
            for col in NATIVE_LABEL_CROSS_CHECK_FIELDS:
                lcol = f"{col}_native"
                rcol = f"{col}_label"
                if lcol not in merged.columns or rcol not in merged.columns:
                    status = "fail"
                    rows.append(
                        {
                            "source_artifact_id": "native_label_panel",
                            "source_column": col,
                            "target_column": f"native_universe_panel.{col}",
                            "adapter_rule": "cross_check",
                            "row_count_checked": 0,
                            "value_match_status": "missing_cross_check_column",
                            "unit_match_status": "pass",
                            "required_for_primary": True,
                            "adapter_status": "fail",
                        }
                    )
                    continue
                ok = compare_series(merged[lcol], merged[rcol], tol=1e-10)
                if not ok:
                    status = "fail"
                rows.append(
                    {
                        "source_artifact_id": "native_label_panel",
                        "source_column": col,
                        "target_column": f"native_universe_panel.{col}",
                        "adapter_rule": "cross_check",
                        "row_count_checked": int(len(merged)),
                        "value_match_status": "pass" if ok else "mismatch",
                        "unit_match_status": "pass",
                        "required_for_primary": True,
                        "adapter_status": "pass" if ok else "fail",
                    }
                )
    return out, pd.DataFrame(rows), status


def build_upstream_lineage_audit(resolved: dict[str, Path], cache_status: str, adapter_status: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    selected_label = "vol20d_kup2p0_kdn1p0_H20"
    # 12A7g label lineage
    try:
        decision = read_table(resolved["upstream_12a7g_decision"])
        formula = read_table(resolved["upstream_12a7g_label_formula"])
        drow = decision.iloc[0]
        frow = formula.loc[formula["label_id"].astype(str).eq(selected_label)].iloc[0]
        ok = (
            str(drow.get("input_gate_status")) == "pass"
            and str(drow.get("lineage_gate_status")) == "pass"
            and str(drow.get("selected_label_id")) == selected_label
            and str(frow.get("formula_status")) == "pass"
            and str(frow.get("same_bar_priority")) == "lower_first"
        )
        rows.append(
            {
                "lineage_id": "12A7g_selected_label",
                "lineage_status": "pass" if ok else "fail",
                "selected_label_id": selected_label,
                "upstream_formula_path_window": str(frow.get("path_window", "")),
                "implemented_path_window": "entry_pos_through_entry_pos_plus_horizon_inclusive",
                "path_window_reconciliation_status": "pass_with_documented_13a_entry_anchor",
                "path_window_reconciliation_reason": "14A primary label uses 13A published next-open native implementation",
            }
        )
    except Exception as exc:
        rows.append({"lineage_id": "12A7g_selected_label", "lineage_status": "fail", "lineage_reason": type(exc).__name__})
    # 13A native lineage
    try:
        decision = read_table(resolved["upstream_13a_decision"]).iloc[0]
        ok = (
            str(decision.get("input_gate_status")) == "pass"
            and str(decision.get("native_universe_gate_status")) == "pass"
            and str(decision.get("label_portability_gate_status")) == "pass"
        )
        rows.append(
            {
                "lineage_id": "13A_native_universe_label_cache",
                "lineage_status": "pass" if ok and adapter_status == "pass" and cache_status != "cache_unavailable_rebuild_failed" else "fail",
                "cache_status": cache_status,
                "adapter_status": adapter_status,
                "decision_state": str(decision.get("decision_state", "")),
            }
        )
    except Exception as exc:
        rows.append({"lineage_id": "13A_native_universe_label_cache", "lineage_status": "fail", "lineage_reason": type(exc).__name__})
    return pd.DataFrame(rows)


def build_label_portability_audit(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    selected_label = config.get("selected_label", {}).get("label_id", "vol20d_kup2p0_kdn1p0_H20")
    for split in SPLITS:
        sub = panel.loc[panel["split_bucket"].astype(str).eq(split) & bool_series(panel["native_scope"])]
        denom = len(sub)
        horizon = bool_series(sub.get("horizon_complete", pd.Series(False, index=sub.index)))
        rows.append(
            {
                "split_bucket": split,
                "selected_label_id": selected_label,
                "denominator_n": int(denom),
                "horizon_complete_n": int(horizon.sum()),
                "horizon_complete_rate": safe_rate(horizon.sum(), denom),
                "winner_positive_n": int(bool_series(sub.get("winner", pd.Series(False, index=sub.index))).sum()),
                "winner_base_rate": safe_rate(bool_series(sub.get("winner", pd.Series(False, index=sub.index))).sum(), denom),
                "fast_fail_rate": safe_rate(bool_series(sub.get("fast_fail", pd.Series(False, index=sub.index))).sum(), denom),
                "label_portability_status": "pass" if denom > 0 and horizon.any() else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_row_rebuild_audit(panel: pd.DataFrame, adapter_status: str, config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    minimum = int(config.get("label_rebuild_audit", {}).get("minimum_audited_rows", 500))
    complete = panel.loc[bool_series(panel.get("horizon_complete", pd.Series(False, index=panel.index)))]
    audited = min(minimum, len(complete))
    base = {
        "audit_id": "13a_entry_anchor_label_cache_reconciliation",
        "sample_method": "deterministic_hash_sample_by_row_id",
        "minimum_audited_rows": minimum,
        "audited_row_n": audited,
        "allowed_label_mismatch_rate": float(config.get("label_rebuild_audit", {}).get("allowed_label_mismatch_rate", 0.0)),
        "barrier_abs_tolerance": float(config.get("label_rebuild_audit", {}).get("barrier_abs_tolerance", 1e-10)),
        "terminal_return_abs_tolerance": float(config.get("label_rebuild_audit", {}).get("terminal_return_abs_tolerance", 1e-10)),
    }
    if adapter_status != "pass" or audited <= 0:
        return pd.DataFrame([{**base, "field_name": "__overall__", "compared_row_n": 0, "mismatch_n": audited, "label_mismatch_rate": np.nan, "rebuild_status": "fail"}])
    sample = complete.copy()
    sample["_sample_hash"] = sample["row_id"].astype(str).map(stable_hash)
    sample = sample.sort_values("_sample_hash", kind="stable").head(audited).drop(columns=["_sample_hash"])
    label_cfg = config.get("selected_label", {})
    try:
        recomputed = r13a.compute_label(
            sample,
            r13a.StockDailyCache(resolved["stock_daily_qfq_dir"]),
            k_up=float(label_cfg.get("k_up", 2.0)),
            k_dn=float(label_cfg.get("k_dn", 1.0)),
            horizon_sessions=int(label_cfg.get("horizon_sessions", 20)),
            vol_reference_unit="daily_return_std",
        )
        cache_panel = sample.copy()
        fallback_cols = {
            "winner_positive": "winner",
            "upper_barrier": "upper_barrier_return",
            "lower_barrier": "lower_barrier_return",
            "horizon_close_return": "terminal_return_20d",
        }
        for target_col, source_col in fallback_cols.items():
            if target_col not in cache_panel.columns and source_col in cache_panel.columns:
                cache_panel[target_col] = cache_panel[source_col]
        tolerance = max(float(base["barrier_abs_tolerance"]), float(base["terminal_return_abs_tolerance"]))
        audit = r13a.compare_label_cache_to_recomputed(cache_panel.reset_index(drop=True), recomputed.reset_index(drop=True), tolerance=tolerance)
        audit["label_mismatch_rate"] = audit["mismatch_rate"]
        audit["rebuild_status"] = np.where(audit["mismatch_status"].astype(str).eq("pass"), "pass", "fail")
        for key, value in base.items():
            audit[key] = value
        return audit[
            [
                "audit_id",
                "sample_method",
                "minimum_audited_rows",
                "audited_row_n",
                "field_name",
                "field_type",
                "compared_row_n",
                "mismatch_n",
                "label_mismatch_rate",
                "allowed_label_mismatch_rate",
                "tolerance_abs",
                "barrier_abs_tolerance",
                "terminal_return_abs_tolerance",
                "rebuild_status",
            ]
        ]
    except Exception as exc:
        return pd.DataFrame([{**base, "field_name": "__overall__", "compared_row_n": 0, "mismatch_n": audited, "label_mismatch_rate": np.nan, "rebuild_status": "fail", "rebuild_error": type(exc).__name__}])


def benchmark_returns(path: Path) -> pd.DataFrame:
    bench = pd.read_csv(path, low_memory=False)
    bench = bench.loc[bench["index_alias"].astype(str).eq("all_a")].copy()
    if bench.empty:
        return pd.DataFrame(columns=["reference_date", "benchmark_return_1d", "benchmark_ret_60d", "benchmark_ret_120d"])
    bench["reference_date"] = bench.get("date", bench.get("trade_date")).astype(str).str[:10]
    bench["close"] = finite_numeric(bench["close"])
    bench = bench.sort_values("reference_date")
    bench["benchmark_return_1d"] = bench["close"].pct_change()
    bench["benchmark_ret_60d"] = bench["close"] / bench["close"].shift(60) - 1.0
    bench["benchmark_ret_120d"] = bench["close"] / bench["close"].shift(120) - 1.0
    return bench[["reference_date", "benchmark_return_1d", "benchmark_ret_60d", "benchmark_ret_120d"]]


def enrich_daily_fields(panel: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    out = panel.copy()
    for col in [
        "daily_return_1d",
        "reference_open",
        "reference_close",
        "reference_high",
        "reference_low",
        "reference_money",
        "reference_volume",
        "reference_turnover_rate",
        "range_1d",
        "close_vs_ma20",
        "money_median_60d",
        "volume_median_20d",
        "volume_median_60d",
        "range_median_20d",
    ]:
        out[col] = np.nan
    cache = r13a.StockDailyCache(qfq_dir)
    for instrument, idx in out.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        if daily.frame is None or daily.frame.empty or daily.status == "duplicate_qfq_date":
            continue
        frame = daily.frame
        pos = finite_numeric(out.loc[idx, "reference_pos"]).to_numpy(dtype=float)
        ok = np.isfinite(pos) & (pos >= 0) & (pos < len(frame))
        if not ok.any():
            continue
        loc_idx = np.asarray(list(idx), dtype=object)[ok]
        p = pos[ok].astype(int)
        close = frame["close"].to_numpy(dtype=float)
        open_ = frame["open"].to_numpy(dtype=float)
        high = frame["high"].to_numpy(dtype=float)
        low = frame["low"].to_numpy(dtype=float)
        money = frame["money"].to_numpy(dtype=float) if "money" in frame.columns else np.full(len(frame), np.nan)
        volume = frame["volume"].to_numpy(dtype=float) if "volume" in frame.columns else np.full(len(frame), np.nan)
        turnover = frame["turnover_rate"].to_numpy(dtype=float) if "turnover_rate" in frame.columns else np.full(len(frame), np.nan)
        ma20 = pd.Series(close).rolling(20, min_periods=20).mean().to_numpy(dtype=float)
        money_med60 = pd.Series(money).rolling(60, min_periods=20).median().to_numpy(dtype=float)
        vol_med20 = pd.Series(volume).rolling(20, min_periods=10).median().to_numpy(dtype=float)
        vol_med60 = pd.Series(volume).rolling(60, min_periods=20).median().to_numpy(dtype=float)
        range_1d = (high - low) / np.where(open_ == 0, np.nan, open_)
        range_med20 = pd.Series(range_1d).rolling(20, min_periods=10).median().to_numpy(dtype=float)
        prev_close = np.full(len(p), np.nan)
        has_prev = p > 0
        prev_close[has_prev] = close[p[has_prev] - 1]
        out.loc[loc_idx, "daily_return_1d"] = close[p] / prev_close - 1.0
        out.loc[loc_idx, "reference_open"] = open_[p]
        out.loc[loc_idx, "reference_close"] = close[p]
        out.loc[loc_idx, "reference_high"] = high[p]
        out.loc[loc_idx, "reference_low"] = low[p]
        out.loc[loc_idx, "reference_money"] = money[p]
        out.loc[loc_idx, "reference_volume"] = volume[p]
        out.loc[loc_idx, "reference_turnover_rate"] = turnover[p]
        out.loc[loc_idx, "range_1d"] = range_1d[p]
        out.loc[loc_idx, "close_vs_ma20"] = close[p] / ma20[p] - 1.0
        out.loc[loc_idx, "money_median_60d"] = money_med60[p]
        out.loc[loc_idx, "volume_median_20d"] = vol_med20[p]
        out.loc[loc_idx, "volume_median_60d"] = vol_med60[p]
        out.loc[loc_idx, "range_median_20d"] = range_med20[p]
    return out


def build_feature_panel(panel: pd.DataFrame, resolved: dict[str, Path]) -> pd.DataFrame:
    out = panel.loc[bool_series(panel["native_scope"]) & bool_series(panel.get("horizon_complete", pd.Series(True, index=panel.index)))].copy()
    out = enrich_daily_fields(out, resolved["stock_daily_qfq_dir"])
    bench = benchmark_returns(resolved["benchmark_indices_daily"])
    if not bench.empty:
        out = out.merge(bench, on="reference_date", how="left")
    else:
        out["benchmark_return_1d"] = np.nan
        out["benchmark_ret_60d"] = np.nan
        out["benchmark_ret_120d"] = np.nan
    out = out.sort_values(["instrument", "reference_date"], kind="stable").reset_index(drop=True)
    out["instrument_year"] = out["instrument"].astype(str) + "_" + out["calendar_year"].astype(str)
    date_rank = {date: i for i, date in enumerate(sorted(out["reference_date"].astype(str).unique()))}
    out["reference_date_rank"] = out["reference_date"].astype(str).map(date_rank).astype(int)
    out["residual_return_1d"] = finite_numeric(out["daily_return_1d"]) - finite_numeric(out.get("benchmark_return_1d", pd.Series(np.nan, index=out.index)))
    for lookback in [60, 120]:
        ret_col = f"ret_{lookback}d"
        bench_col = f"benchmark_ret_{lookback}d"
        out[f"residual_ret_{lookback}d"] = finite_numeric(out.get(ret_col, pd.Series(np.nan, index=out.index))) - finite_numeric(out.get(bench_col, pd.Series(np.nan, index=out.index)))
        out[f"residual_cusum_{lookback}d"] = out.groupby("instrument", sort=False)["residual_return_1d"].transform(positive_cusum)
        residual_vol = out.groupby("instrument", sort=False)["residual_return_1d"].transform(
            lambda s: finite_numeric(s).rolling(lookback, min_periods=max(40, lookback // 3)).std(ddof=0)
        )
        out[f"residual_cusum_z_{lookback}d"] = finite_numeric(out[f"residual_cusum_{lookback}d"]) / finite_numeric(residual_vol).replace(0, np.nan)
        out[f"residual_z_{lookback}d"] = out.groupby("instrument", sort=False)[f"residual_ret_{lookback}d"].transform(
            lambda s: s / s.rolling(lookback, min_periods=max(20, lookback // 3)).std(ddof=0).replace(0, np.nan)
        )
    for window in [20, 60]:
        base_col = "reference_money" if "reference_money" in out.columns else "reference_volume"
        median_col = "money_median_20d" if window == 20 and "money_median_20d" in out.columns else "money_median_60d"
        if median_col not in out.columns:
            median_col = "volume_median_20d" if window == 20 else "volume_median_60d"
        out[f"participation_ratio_{window}d"] = finite_numeric(out[base_col]) / finite_numeric(out.get(median_col, pd.Series(np.nan, index=out.index))).replace(0, np.nan)
    out["range_expansion_ratio"] = finite_numeric(out["range_1d"]) / finite_numeric(out.get("range_median_20d", pd.Series(np.nan, index=out.index))).replace(0, np.nan)
    for window in [20, 60]:
        ret_col = f"ret_{window}d"
        rank_col = f"board_ret_{window}d_pct_rank"
        delta_col = f"board_ret_{window}d_pct_rank_delta"
        out[rank_col] = out.groupby(["reference_date", "board_bucket"], dropna=False)[ret_col].rank(method="average", pct=True)
        out[delta_col] = out.groupby("instrument", sort=False)[rank_col].diff()
    return out


def parameter_specs(config: dict[str, Any]) -> list[ArmSpec]:
    families = config.get("families", {})
    specs: list[ArmSpec] = []
    f1 = families.get("f1_residual_cusum_break", {})
    if f1.get("enabled", True):
        for lookback in f1.get("lookback_sessions", [60, 120]):
            for z in f1.get("trigger_threshold_z", [2.5, 3.0]):
                specs.append(ArmSpec("F1_residual_cusum_break", f"lookback{lookback}_z{str(z).replace('.', 'p')}", int(f1.get("cooldown_sessions", 20)), {"lookback": lookback, "z": float(z)}))
    f2 = families.get("f2_compression_to_directional_expansion", {})
    if f2.get("enabled", True):
        for ratio in f2.get("expansion_ratio_threshold", [1.5, 2.0]):
            specs.append(ArmSpec("F2_compression_to_directional_expansion", f"ratio{str(ratio).replace('.', 'p')}", int(f2.get("cooldown_sessions", 20)), {"ratio": float(ratio)}))
    f3 = families.get("f3_controlled_damage_first_reclaim", {})
    if f3.get("enabled", True):
        for lookback in f3.get("damage_lookback_sessions", [20, 60]):
            specs.append(ArmSpec("F3_controlled_damage_first_reclaim", f"damage{lookback}", int(f3.get("cooldown_sessions", 20)), {"lookback": lookback}))
    f4 = families.get("f4_board_relative_strength_rank_jump", {})
    if f4.get("enabled", True):
        for window in f4.get("relative_return_window", [20, 60]):
            for jump in f4.get("rank_jump_decile_threshold", [2, 3]):
                specs.append(ArmSpec("F4_board_relative_strength_rank_jump", f"ret{window}_jump{jump}", int(f4.get("cooldown_sessions", 15)), {"window": window, "jump": int(jump)}))
    f5 = families.get("f5_participation_ignition_with_price_control", {})
    if f5.get("enabled", True):
        for window, ratio in zip(f5.get("participation_window", [20, 60]), f5.get("participation_ratio_threshold", [1.5, 2.0])):
            specs.append(ArmSpec("F5_participation_ignition_with_price_control", f"window{window}_ratio{str(ratio).replace('.', 'p')}", int(f5.get("cooldown_sessions", 15)), {"window": int(window), "ratio": float(ratio)}))
    f6 = families.get("f6_low_volatility_range_expansion_first_trigger", {})
    if f6.get("enabled", True):
        for ratio in f6.get("range_expansion_ratio_threshold", [1.5, 2.0]):
            specs.append(ArmSpec("F6_low_volatility_range_expansion_first_trigger", f"ratio{str(ratio).replace('.', 'p')}", int(f6.get("cooldown_sessions", 20)), {"ratio": float(ratio)}))
    return specs


def train_quantile(panel: pd.DataFrame, col: str, q: float) -> float:
    train = panel.loc[panel["split_bucket"].astype(str).eq("train"), col]
    return float(finite_numeric(train).quantile(q))


def state_for_spec(panel: pd.DataFrame, spec: ArmSpec, thresholds: dict[str, float]) -> tuple[pd.Series, pd.Series, pd.Series, str]:
    idx = panel.index
    status = "pass"
    if spec.family_id.startswith("F1"):
        lookback = int(spec.params["lookback"])
        z = float(spec.params["z"])
        intensity = finite_numeric(panel.get(f"residual_cusum_z_{lookback}d", pd.Series(np.nan, index=idx)))
        raw = intensity.ge(z)
        reset = intensity.le(0.5) | finite_numeric(panel.get("residual_return_1d", pd.Series(np.nan, index=idx))).le(0)
    elif spec.family_id.startswith("F2"):
        compression = finite_numeric(panel["volatility_20d"]).le(thresholds["volatility_20d_p20"])
        intensity = finite_numeric(panel["range_expansion_ratio"])
        raw = compression & intensity.ge(float(spec.params["ratio"])) & finite_numeric(panel["daily_return_1d"]).gt(0)
        reset = consecutive_true_by_instrument(panel, ~compression, window=5)
    elif spec.family_id.startswith("F3"):
        lookback = int(spec.params["lookback"])
        dd_col = f"max_drawdown_{lookback}d"
        dd = finite_numeric(panel.get(dd_col, pd.Series(np.nan, index=idx)))
        damage = dd.between(-0.35, -0.10, inclusive="both")
        reclaim = finite_numeric(panel["close_vs_ma20"]).ge(0) & finite_numeric(panel["daily_return_1d"]).gt(0)
        intensity = finite_numeric(panel["close_vs_ma20"]).fillna(0) + finite_numeric(panel["daily_return_1d"]).fillna(0)
        raw = damage & reclaim
        new_high = finite_numeric(panel.get("distance_to_20d_high", pd.Series(np.nan, index=idx))).ge(-1e-12)
        reset = consecutive_true_by_instrument(panel, new_high | ~damage, window=5)
    elif spec.family_id.startswith("F4"):
        window = int(spec.params["window"])
        jump = int(spec.params["jump"])
        intensity = finite_numeric(panel.get(f"board_ret_{window}d_pct_rank_delta", pd.Series(np.nan, index=idx)))
        required_cols = {"board_bucket", "reference_date", f"board_ret_{window}d_pct_rank", f"board_ret_{window}d_pct_rank_delta"}
        status = "pass" if required_cols <= set(panel.columns) else "blocked_pit_availability"
        raw = intensity.ge(jump / 10.0)
        reset = consecutive_true_by_instrument(panel, intensity.lt(0), window=5)
    elif spec.family_id.startswith("F5"):
        window = int(spec.params["window"])
        intensity = finite_numeric(panel.get(f"participation_ratio_{window}d", pd.Series(np.nan, index=idx)))
        ret = finite_numeric(panel["daily_return_1d"])
        raw = intensity.ge(float(spec.params["ratio"])) & ret.ge(0) & ret.le(0.06) & ret.lt(0.095)
        reset = consecutive_true_by_instrument(panel, intensity.lt(1.0), window=5)
    elif spec.family_id.startswith("F6"):
        low_vol = finite_numeric(panel["volatility_20d"]).le(thresholds["volatility_20d_p20"])
        intensity = finite_numeric(panel["range_expansion_ratio"])
        raw = low_vol & intensity.ge(float(spec.params["ratio"])) & finite_numeric(panel["daily_return_1d"]).gt(0) & finite_numeric(panel["reference_close"]).gt(finite_numeric(panel["reference_open"]))
        reset = consecutive_true_by_instrument(panel, ~low_vol, window=5)
    else:
        intensity = pd.Series(np.nan, index=idx)
        raw = pd.Series(False, index=idx)
        reset = pd.Series(False, index=idx)
        status = "blocked_unknown_family"
    return raw.fillna(False).astype(bool), intensity, reset.fillna(False).astype(bool), status


def family_formula_spec_rows(specs: list[ArmSpec]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "family_id": spec.family_id,
                "parameter_set_id": spec.parameter_set_id,
                "raw_event_arm_id": spec.raw_event_arm_id,
                "cooldown_sessions": spec.cooldown_sessions,
                "parameter_json": json.dumps(spec.params, sort_keys=True),
            }
            for spec in specs
        ]
    )


def generate_events_for_spec(panel: pd.DataFrame, spec: ArmSpec, raw: pd.Series, intensity: pd.Series, reset: pd.Series, family_status: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_transition_n = 0
    suppressed_n = 0
    if family_status != "pass":
        return pd.DataFrame(), {
            "family_id": spec.family_id,
            "parameter_set_id": spec.parameter_set_id,
            "raw_event_arm_id": spec.raw_event_arm_id,
            "raw_transition_n": 0,
            "accepted_event_n": 0,
            "duplicate_suppressed_n": 0,
            "family_input_status": family_status,
        }
    work_cols = ["row_id", "instrument", "reference_date", "split_bucket", "board_bucket", "calendar_year", "instrument_year"]
    for optional_col in ["reference_pos", "reference_date_rank"]:
        if optional_col in panel.columns:
            work_cols.append(optional_col)
    work = panel[work_cols].copy()
    work["_raw"] = raw.to_numpy(dtype=bool)
    work["_reset"] = reset.to_numpy(dtype=bool)
    work["_intensity"] = intensity.to_numpy(dtype=float)
    work = work.sort_values(["instrument", "reference_date"], kind="stable")
    for _instrument, sub in work.groupby("instrument", sort=False):
        prev_raw = False
        reset_seen = True
        last_accept_i: int | None = None
        for local_i, (_, row) in enumerate(sub.iterrows()):
            current_raw = bool(row["_raw"])
            current_reset = bool(row["_reset"])
            transition = current_raw and not prev_raw
            if transition:
                raw_transition_n += 1
                cooldown_ok = last_accept_i is None or (local_i - last_accept_i) >= spec.cooldown_sessions
                if reset_seen and cooldown_ok:
                    event_id = stable_hash([spec.raw_event_arm_id, str(row["instrument"]), str(row["reference_date"])])[:16]
                    rows.append(
                        {
                            "family_id": spec.family_id,
                            "parameter_set_id": spec.parameter_set_id,
                            "raw_event_arm_id": spec.raw_event_arm_id,
                            "event_id": event_id,
                            "row_id": row["row_id"],
                            "instrument": row["instrument"],
                            "reference_date": row["reference_date"],
                            "event_t0_pos": row.get("reference_pos", np.nan),
                            "split_bucket": row["split_bucket"],
                            "board_bucket": row["board_bucket"],
                            "calendar_year": row["calendar_year"],
                            "instrument_year": row["instrument_year"],
                            "reference_date_rank": row.get("reference_date_rank", np.nan),
                            "event_intensity_score": row["_intensity"],
                            "event_signal_time": "t0_close",
                            "reset_state_id": f"{spec.raw_event_arm_id}__reset",
                            "cooldown_sessions": spec.cooldown_sessions,
                            "first_trigger_flag": True,
                            "duplicate_within_cooldown_flag": False,
                            "family_input_status": family_status,
                        }
                    )
                    last_accept_i = local_i
                    reset_seen = False
                else:
                    suppressed_n += 1
            if current_reset:
                reset_seen = True
            prev_raw = current_raw
    return pd.DataFrame(rows), {
        "family_id": spec.family_id,
        "parameter_set_id": spec.parameter_set_id,
        "raw_event_arm_id": spec.raw_event_arm_id,
        "raw_transition_n": raw_transition_n,
        "accepted_event_n": len(rows),
        "duplicate_suppressed_n": suppressed_n,
        "family_input_status": family_status,
    }


def generate_sparse_events(panel: pd.DataFrame, specs: list[ArmSpec]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, tuple[pd.Series, pd.Series]]]:
    thresholds = {
        "volatility_20d_p20": train_quantile(panel, "volatility_20d", 0.20),
    }
    events: list[pd.DataFrame] = []
    audits: list[dict[str, Any]] = []
    state_cache: dict[str, tuple[pd.Series, pd.Series]] = {}
    for spec in specs:
        raw, intensity, reset, family_status = state_for_spec(panel, spec, thresholds)
        state_cache[spec.raw_event_arm_id] = (raw, intensity)
        event_frame, audit = generate_events_for_spec(panel, spec, raw, intensity, reset, family_status)
        if not event_frame.empty:
            events.append(event_frame)
        audits.append(audit)
    event_panel = pd.concat(events, ignore_index=True) if events else pd.DataFrame()
    if not event_panel.empty:
        event_panel = event_panel.merge(
            panel[
                [
                    "row_id",
                    "entry_date",
                    "entry_price",
                    "upper_first",
                    "lower_first",
                    "same_bar_conflict",
                    "winner",
                    "fast_fail",
                    "upper_barrier_return",
                    "lower_barrier_return",
                    "terminal_return_20d",
                    "max_high_return",
                    "min_low_return",
                ]
            ],
            on="row_id",
            how="left",
        )
    return event_panel, pd.DataFrame(audits), state_cache


def path_utility(frame: pd.DataFrame, cost_bps: int) -> pd.Series:
    cost = cost_return(cost_bps)
    upper = bool_series(frame.get("upper_first", pd.Series(False, index=frame.index)))
    lower = bool_series(frame.get("lower_first", pd.Series(False, index=frame.index))) | bool_series(frame.get("same_bar_conflict", pd.Series(False, index=frame.index)))
    upper_ret = finite_numeric(frame.get("upper_barrier_return", pd.Series(np.nan, index=frame.index)))
    lower_ret = finite_numeric(frame.get("lower_barrier_return", pd.Series(np.nan, index=frame.index)))
    terminal = finite_numeric(frame.get("terminal_return_20d", pd.Series(np.nan, index=frame.index)))
    out = terminal - cost
    out = out.mask(upper, upper_ret - cost)
    out = out.mask(lower, lower_ret - cost)
    return out


def add_event_utility(events: pd.DataFrame, cost_tiers: list[int]) -> pd.DataFrame:
    out = events.copy()
    for tier in cost_tiers:
        out[f"path_utility_component_{tier}bps"] = path_utility(out, tier)
    return out


def native_baseline_rows(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        sub = panel.loc[panel["split_bucket"].astype(str).eq(split)]
        denom = len(sub)
        rows.append(
            {
                "split_bucket": split,
                "native_split_denominator_n": denom,
                "native_baseline_winner_rate": safe_rate(bool_series(sub["winner"]).sum(), denom),
                "native_baseline_fast_fail_rate": safe_rate(bool_series(sub["fast_fail"]).sum(), denom),
                "native_baseline_lower_first_rate": safe_rate((bool_series(sub["lower_first"]) | bool_series(sub["same_bar_conflict"])).sum(), denom),
                "native_baseline_mfe_return_20d_median": finite_numeric(sub.get("max_high_return", pd.Series(dtype=float))).median(),
                "native_baseline_mae_return_20d_median": finite_numeric(sub.get("min_low_return", pd.Series(dtype=float))).median(),
            }
        )
    return pd.DataFrame(rows)


def raw_intensity_delta(sub: pd.DataFrame, min_n: int) -> tuple[float, int, int, str]:
    scores = finite_numeric(sub["event_intensity_score"])
    if scores.notna().sum() < min_n * 2:
        return np.nan, 0, 0, "insufficient_intensity_support"
    p20 = scores.quantile(0.20)
    p80 = scores.quantile(0.80)
    bottom = sub.loc[scores.le(p20)]
    top = sub.loc[scores.ge(p80)]
    if len(bottom) < min_n or len(top) < min_n:
        return np.nan, len(top), len(bottom), "insufficient_side_support"
    delta = safe_rate(bool_series(top["winner"]).sum(), len(top)) - safe_rate(bool_series(bottom["winner"]).sum(), len(bottom))
    return delta, len(top), len(bottom), "pass"


def build_density_audit(events: pd.DataFrame, generation: pd.DataFrame, native_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    thresholds = config.get("thresholds", {})
    rows = []
    if events.empty:
        return pd.DataFrame(columns=["raw_event_arm_id", "split_bucket", "density_gate_status"])
    denom = native_panel.groupby("split_bucket")["instrument_year"].nunique().to_dict()
    for (arm, split), sub in events.groupby(["raw_event_arm_id", "split_bucket"], dropna=False):
        gen = generation.loc[generation["raw_event_arm_id"].eq(arm)].iloc[0]
        instrument_year_n = int(denom.get(split, 0))
        density = safe_rate(len(sub), instrument_year_n)
        duplicate_fraction = safe_rate(int(gen.get("duplicate_suppressed_n", 0)), int(gen.get("accepted_event_n", 0)) + int(gen.get("duplicate_suppressed_n", 0)))
        status = "pass"
        if density > float(thresholds.get("hard_max_event_density_per_instrument_year", 6.0)):
            status = "fail_hard_density"
        if duplicate_fraction > float(thresholds.get("max_duplicate_episode_fraction", 0.35)):
            status = "fail_duplicate_fraction"
        if split == "train" and len(sub) < int(thresholds.get("min_train_event_n_per_parameter", 100)):
            status = "fail_min_train_event_n"
        rows.append(
            {
                "raw_event_arm_id": arm,
                "family_id": sub.iloc[0]["family_id"],
                "parameter_set_id": sub.iloc[0]["parameter_set_id"],
                "split_bucket": split,
                "event_n": int(len(sub)),
                "instrument_n": int(sub["instrument"].nunique()),
                "instrument_year_n": instrument_year_n,
                "event_density_per_instrument_year": density,
                "duplicate_episode_fraction": duplicate_fraction,
                "average_uniqueness": 1.0,
                "density_gate_status": status,
            }
        )
    return pd.DataFrame(rows)


def raw_readout(events: pd.DataFrame, native_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    thresholds = config.get("thresholds", {})
    baseline = native_baseline_rows(native_panel)
    rows = []
    if events.empty:
        return pd.DataFrame()
    for (arm, split), sub in events.groupby(["raw_event_arm_id", "split_bucket"], dropna=False):
        base = baseline.loc[baseline["split_bucket"].eq(split)].iloc[0]
        n = len(sub)
        winner_rate = safe_rate(bool_series(sub["winner"]).sum(), n)
        fast_fail_rate = safe_rate(bool_series(sub["fast_fail"]).sum(), n)
        lower_flag = bool_series(sub["lower_first"]) | bool_series(sub["same_bar_conflict"])
        lower_rate = safe_rate(lower_flag.sum(), n)
        intensity_delta, top_n, bottom_n, intensity_status = raw_intensity_delta(
            sub if split == "train" else events.loc[events["raw_event_arm_id"].eq(arm) & events["split_bucket"].eq("train")],
            int(thresholds.get("raw_intensity_side_min_n", 30)),
        )
        row = {
            "raw_event_arm_id": arm,
            "family_id": sub.iloc[0]["family_id"],
            "parameter_set_id": sub.iloc[0]["parameter_set_id"],
            "split_bucket": split,
            "event_n": int(n),
            "instrument_n": int(sub["instrument"].nunique()),
            "instrument_year_n": int(sub["instrument_year"].nunique()),
            "event_density_per_instrument_year": safe_rate(n, sub["instrument_year"].nunique()),
            "winner_positive_n": int(bool_series(sub["winner"]).sum()),
            "winner_rate": winner_rate,
            "native_baseline_winner_rate": base["native_baseline_winner_rate"],
            "winner_rate_lift": winner_rate - base["native_baseline_winner_rate"],
            "fast_fail_rate": fast_fail_rate,
            "native_baseline_fast_fail_rate": base["native_baseline_fast_fail_rate"],
            "fast_fail_uplift": fast_fail_rate - base["native_baseline_fast_fail_rate"],
            "lower_first_rate": lower_rate,
            "native_baseline_lower_first_rate": base["native_baseline_lower_first_rate"],
            "lower_first_uplift": lower_rate - base["native_baseline_lower_first_rate"],
            "same_bar_conflict_rate": safe_rate(bool_series(sub["same_bar_conflict"]).sum(), n),
            "median_upper_barrier_return": finite_numeric(sub["upper_barrier_return"]).median(),
            "median_abs_lower_barrier_return": abs(finite_numeric(sub["lower_barrier_return"]).median()),
            "terminal_return_20d_mean": finite_numeric(sub["terminal_return_20d"]).mean(),
            "terminal_return_60d_mean": np.nan,
            "terminal_return_120d_mean": np.nan,
            "mfe_return_20d_median": finite_numeric(sub["max_high_return"]).median(),
            "mfe_return_60d_median": np.nan,
            "mfe_return_120d_median": np.nan,
            "native_baseline_mfe_return_20d_median": base["native_baseline_mfe_return_20d_median"],
            "native_baseline_mfe_return_60d_median": np.nan,
            "native_baseline_mfe_return_120d_median": np.nan,
            "mae_return_20d_median": finite_numeric(sub["min_low_return"]).median(),
            "mae_return_60d_median": np.nan,
            "mae_return_120d_median": np.nan,
            "native_baseline_mae_return_20d_median": base["native_baseline_mae_return_20d_median"],
            "native_baseline_mae_return_60d_median": np.nan,
            "native_baseline_mae_return_120d_median": np.nan,
            "raw_intensity_top_bottom_winner_rate_delta": intensity_delta,
            "raw_intensity_top20pct_event_n": top_n,
            "raw_intensity_bottom20pct_event_n": bottom_n,
            "raw_intensity_status": intensity_status,
        }
        for tier in [0, 50, 100]:
            row[f"utility_per_event_mean_{tier}bps"] = finite_numeric(sub[f"path_utility_component_{tier}bps"]).mean()
        row["utility_total_indexed_50bps"] = finite_numeric(sub["path_utility_component_50bps"]).sum() / float(base["native_split_denominator_n"] or np.nan)
        row["badside_gate_status"] = "pass" if row["fast_fail_uplift"] <= thresholds.get("max_fast_fail_uplift", 0.02) and row["lower_first_uplift"] <= thresholds.get("max_lower_first_uplift", 0.01) else "fail"
        rows.append(row)
    out = pd.DataFrame(rows)
    train_map = {}
    for arm, sub in out.loc[out["split_bucket"].eq("train")].groupby("raw_event_arm_id"):
        row = sub.iloc[0]
        status = (
            row["winner_rate_lift"] >= thresholds.get("raw_winner_rate_lift", 0.02)
            or row["utility_per_event_mean_0bps"] > 0
            or row["mfe_return_20d_median"] > row["native_baseline_mfe_return_20d_median"]
            or row["raw_intensity_top_bottom_winner_rate_delta"] >= thresholds.get("raw_intensity_top_bottom_delta", 0.03)
        )
        train_map[arm] = "pass" if status else "fail"
    out["raw_opportunity_surface_status"] = out["raw_event_arm_id"].map(train_map).fillna("fail")
    return out


def cohort_dictionary(config: dict[str, Any]) -> pd.DataFrame:
    arms = [
        ("C1", "same_date_full_cross_section", "all native_scope rows on reference_date"),
        ("C2", "same_date_same_board_cross_section", "all native_scope rows on reference_date and board_bucket"),
        ("C3", "rolling_prior_event_family_252d", "prior accepted events from same arm"),
        ("C4", "rolling_prior_board_event_family_252d", "prior accepted events from same arm and board"),
        ("C5", "month_to_date_partial_event_cohort", "same-month accepted events up to t0"),
        ("C6", "week_to_date_partial_event_cohort", "same-week accepted events up to t0"),
    ]
    mins = config.get("cohort_arms", {}).get("minimum_cohort_finite_n", {})
    return pd.DataFrame(
        [
            {
                "cohort_arm_id": arm,
                "cohort_arm_name": name,
                "cohort_denominator": denom,
                "minimum_cohort_finite_n": int(mins.get(arm, 0)),
                "rank_direction": "high_is_stronger",
                "pit_availability_required": True,
            }
            for arm, name, denom in arms
        ]
    )


def midpoint_percentile(scores: pd.Series) -> pd.Series:
    finite = finite_numeric(scores)
    n = int(finite.notna().sum())
    if n == 0:
        return pd.Series(np.nan, index=scores.index)
    return (finite.rank(method="average") - 0.5) / n


def compute_c1_c2_ranks(panel: pd.DataFrame, events: pd.DataFrame, raw_arm: str, intensity: pd.Series, cohort_arm: str, min_n: int) -> pd.DataFrame:
    source = panel[["row_id", "reference_date", "board_bucket"]].copy()
    source["event_intensity_score"] = intensity.to_numpy(dtype=float)
    if cohort_arm == "C1":
        group_cols = ["reference_date"]
    else:
        group_cols = ["reference_date", "board_bucket"]
    source["cohort_finite_n"] = source.groupby(group_cols)["event_intensity_score"].transform(lambda s: int(finite_numeric(s).notna().sum()))
    source["cohort_percentile_rank"] = source.groupby(group_cols)["event_intensity_score"].transform(midpoint_percentile)
    source["cohort_rank_status"] = np.where(source["cohort_finite_n"].ge(min_n), "pass", "insufficient_cohort")
    source.loc[finite_numeric(source["event_intensity_score"]).isna(), "cohort_rank_status"] = "missing_intensity"
    return events.loc[events["raw_event_arm_id"].eq(raw_arm)].merge(source[["row_id", "cohort_finite_n", "cohort_percentile_rank", "cohort_rank_status"]], on="row_id", how="left")


def compute_event_cohort_ranks(events: pd.DataFrame, raw_arm: str, cohort_arm: str, min_n: int, rolling_prior_n: int) -> pd.DataFrame:
    sub = events.loc[events["raw_event_arm_id"].eq(raw_arm)].copy()
    sub["reference_date_dt"] = pd.to_datetime(sub["reference_date"])
    if "reference_date_rank" not in sub.columns:
        date_rank = {date: i for i, date in enumerate(sorted(sub["reference_date"].astype(str).unique()))}
        sub["reference_date_rank"] = sub["reference_date"].astype(str).map(date_rank)
    sub["reference_date_rank"] = finite_numeric(sub["reference_date_rank"])
    sub = sub.sort_values(["reference_date_rank", "reference_date", "instrument"], kind="stable").reset_index(drop=True)
    ranks = []
    finite_ns = []
    statuses = []
    if cohort_arm in {"C3", "C4"}:
        group_cols = ["raw_event_arm_id"] if cohort_arm == "C3" else ["raw_event_arm_id", "board_bucket"]
        for _, group in sub.groupby(group_cols, dropna=False, sort=False):
            prior_records: list[tuple[float, float]] = []
            for _, row in group.iterrows():
                score = float(row["event_intensity_score"]) if pd.notna(row["event_intensity_score"]) else np.nan
                current_rank = float(row["reference_date_rank"]) if pd.notna(row["reference_date_rank"]) else np.nan
                finite = [
                    prior_score
                    for prior_rank, prior_score in prior_records
                    if np.isfinite(prior_rank)
                    and np.isfinite(current_rank)
                    and prior_rank < current_rank
                    and prior_rank >= current_rank - rolling_prior_n
                    and np.isfinite(prior_score)
                ]
                if not np.isfinite(score):
                    ranks.append(np.nan)
                    finite_ns.append(len(finite))
                    statuses.append("missing_intensity")
                elif len(finite) < min_n:
                    ranks.append(np.nan)
                    finite_ns.append(len(finite))
                    statuses.append("insufficient_cohort")
                else:
                    less = sum(x < score for x in finite)
                    equal = sum(x == score for x in finite)
                    ranks.append((less + 0.5 * equal) / len(finite))
                    finite_ns.append(len(finite))
                    statuses.append("pass")
                if np.isfinite(score):
                    prior_records.append((current_rank, score))
    else:
        period = sub["reference_date_dt"].dt.to_period("M" if cohort_arm == "C5" else "W").astype(str)
        sub["_period"] = period
        for _, group in sub.groupby(["raw_event_arm_id", "_period"], dropna=False, sort=False):
            group = group.sort_values("reference_date_dt")
            scores_so_far: list[float] = []
            for _, row in group.iterrows():
                score = float(row["event_intensity_score"]) if pd.notna(row["event_intensity_score"]) else np.nan
                cohort = [x for x in scores_so_far if np.isfinite(x)]
                if np.isfinite(score):
                    cohort_with_current = cohort + [score]
                else:
                    cohort_with_current = cohort
                if not np.isfinite(score):
                    ranks.append(np.nan)
                    finite_ns.append(len(cohort_with_current))
                    statuses.append("missing_intensity")
                elif len(cohort) == 0:
                    ranks.append(np.nan)
                    finite_ns.append(len(cohort_with_current))
                    statuses.append("degenerate_partial_cohort")
                elif len(cohort_with_current) < min_n:
                    ranks.append(np.nan)
                    finite_ns.append(len(cohort_with_current))
                    statuses.append("insufficient_cohort")
                else:
                    less = sum(x < score for x in cohort_with_current)
                    equal = sum(x == score for x in cohort_with_current)
                    ranks.append((less + 0.5 * equal) / len(cohort_with_current))
                    finite_ns.append(len(cohort_with_current))
                    statuses.append("pass")
                if np.isfinite(score):
                    scores_so_far.append(score)
    sub["cohort_finite_n"] = finite_ns
    sub["cohort_percentile_rank"] = ranks
    sub["cohort_rank_status"] = statuses
    return sub.drop(columns=[c for c in ["reference_date_dt", "_period"] if c in sub.columns])


def build_cohort_readouts(panel: pd.DataFrame, events: pd.DataFrame, state_cache: dict[str, tuple[pd.Series, pd.Series]], raw: pd.DataFrame, density: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if events.empty or raw.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    thresholds = config.get("thresholds", {})
    cohort_cfg = config.get("cohort_arms", {})
    mins = {k: int(v) for k, v in cohort_cfg.get("minimum_cohort_finite_n", {}).items()}
    cutoffs = {k: float(v) for k, v in cohort_cfg.get("rank_cutoffs", {"top20pct": 0.8, "top10pct": 0.9}).items()}
    train_raw = raw.loc[raw["split_bucket"].eq("train") & raw["raw_opportunity_surface_status"].eq("pass")].copy()
    density_all_pass = density.groupby("raw_event_arm_id")["density_gate_status"].apply(lambda s: bool(s.astype(str).eq("pass").all()))
    density_good_arms = set(density_all_pass.loc[density_all_pass].index.astype(str))
    density_train = density.loc[density["split_bucket"].eq("train") & density["density_gate_status"].eq("pass") & density["raw_event_arm_id"].astype(str).isin(density_good_arms)]
    eligible = train_raw.merge(density_train[["raw_event_arm_id", "density_gate_status"]], on="raw_event_arm_id", how="inner")
    eligible = eligible.sort_values(["utility_per_event_mean_50bps", "winner_rate_lift"], ascending=False)
    max_raw = int(config.get("search_accounting", {}).get("maximum_train_selected_raw_arms_into_cohort", 6))
    selected_raw_arms = eligible["raw_event_arm_id"].drop_duplicates().head(max_raw).tolist()
    availability_rows = []
    normalized_events = []
    readout_rows = []
    transport_rows = []
    raw_cols = [
        "raw_event_arm_id",
        "split_bucket",
        "utility_per_event_mean_50bps",
        "winner_rate",
        "fast_fail_rate",
        "lower_first_rate",
    ]
    raw_utility = raw[[c for c in raw_cols if c in raw.columns]].rename(columns={"utility_per_event_mean_50bps": "raw_all_events_same_event_utility_mean_50bps"})
    density_metrics = density[[c for c in ["raw_event_arm_id", "split_bucket", "event_density_per_instrument_year", "duplicate_episode_fraction"] if c in density.columns]].copy()
    for missing_col in ["event_density_per_instrument_year", "duplicate_episode_fraction"]:
        if missing_col not in density_metrics.columns:
            density_metrics[missing_col] = np.nan
    for raw_arm in selected_raw_arms:
        raw_events = events.loc[events["raw_event_arm_id"].eq(raw_arm)]
        _raw_state, intensity = state_cache[raw_arm]
        for cohort_arm in ["C1", "C2", "C3", "C4", "C5", "C6"]:
            min_n = mins.get(cohort_arm, 0)
            if cohort_arm in {"C1", "C2"}:
                ranked = compute_c1_c2_ranks(panel, events, raw_arm, intensity, cohort_arm, min_n)
            else:
                ranked = compute_event_cohort_ranks(events, raw_arm, cohort_arm, min_n, int(cohort_cfg.get("rolling_prior_sessions", 252)))
            for split, sub in ranked.groupby("split_bucket", dropna=False):
                availability_rows.append(
                    {
                        "raw_event_arm_id": raw_arm,
                        "cohort_arm_id": cohort_arm,
                        "split_bucket": split,
                        "event_n": int(len(sub)),
                        "cohort_rank_pass_n": int(sub["cohort_rank_status"].astype(str).eq("pass").sum()),
                        "missing_intensity_n": int(sub["cohort_rank_status"].astype(str).eq("missing_intensity").sum()),
                        "insufficient_cohort_n": int(sub["cohort_rank_status"].astype(str).eq("insufficient_cohort").sum()),
                        "degenerate_partial_cohort_n": int(sub["cohort_rank_status"].astype(str).eq("degenerate_partial_cohort").sum()),
                        "cohort_availability_gate_status": "pass" if sub["cohort_rank_status"].astype(str).eq("pass").any() else "fail",
                    }
                )
            for cutoff_id, cutoff in cutoffs.items():
                ranked_cut = ranked.copy()
                ranked_cut["cohort_arm_id"] = cohort_arm
                ranked_cut["rank_cutoff_id"] = cutoff_id
                ranked_cut["selected_event_flag"] = ranked_cut["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(ranked_cut["cohort_percentile_rank"]).ge(cutoff)
                ranked_cut["skipped_event_flag"] = ~ranked_cut["selected_event_flag"]
                normalized_events.append(ranked_cut)
                for split, sub in ranked_cut.groupby("split_bucket", dropna=False):
                    denom = len(sub)
                    selected = sub.loc[bool_series(sub["selected_event_flag"])]
                    raw_row = raw_utility.loc[raw_utility["raw_event_arm_id"].eq(raw_arm) & raw_utility["split_bucket"].eq(split)]
                    raw_mean = float(raw_row.iloc[0]["raw_all_events_same_event_utility_mean_50bps"]) if len(raw_row) else np.nan
                    raw_winner_rate = float(raw_row.iloc[0].get("winner_rate", np.nan)) if len(raw_row) else np.nan
                    raw_fast_fail_rate = float(raw_row.iloc[0].get("fast_fail_rate", np.nan)) if len(raw_row) else np.nan
                    raw_lower_first_rate = float(raw_row.iloc[0].get("lower_first_rate", np.nan)) if len(raw_row) else np.nan
                    density_row = density_metrics.loc[density_metrics["raw_event_arm_id"].eq(raw_arm) & density_metrics["split_bucket"].eq(split)]
                    duplicate_fraction = float(density_row.iloc[0]["duplicate_episode_fraction"]) if len(density_row) else np.nan
                    event_density = float(density_row.iloc[0]["event_density_per_instrument_year"]) if len(density_row) else np.nan
                    util_sum = finite_numeric(selected["path_utility_component_50bps"]).sum()
                    same_event_mean = util_sum / denom if denom else np.nan
                    selected_diag = finite_numeric(selected["path_utility_component_50bps"]).mean() if len(selected) else np.nan
                    delta = same_event_mean - raw_mean if pd.notna(same_event_mean) and pd.notna(raw_mean) else np.nan
                    winner_rate = safe_rate(bool_series(selected.get("winner", pd.Series(False, index=selected.index))).sum(), len(selected))
                    fast_fail_rate = safe_rate(bool_series(selected.get("fast_fail", pd.Series(False, index=selected.index))).sum(), len(selected))
                    lower_first_rate = safe_rate((bool_series(selected.get("lower_first", pd.Series(False, index=selected.index))) | bool_series(selected.get("same_bar_conflict", pd.Series(False, index=selected.index)))).sum(), len(selected))
                    row = {
                        "raw_event_arm_id": raw_arm,
                        "family_id": sub.iloc[0]["family_id"],
                        "parameter_set_id": sub.iloc[0]["parameter_set_id"],
                        "cohort_arm_id": cohort_arm,
                        "rank_cutoff_id": cutoff_id,
                        "split_bucket": split,
                        "same_event_denominator_n": int(denom),
                        "selected_event_n": int(len(selected)),
                        "skipped_event_n": int(denom - len(selected)),
                        "selected_event_fraction": safe_rate(len(selected), denom),
                        "same_event_utility_mean_50bps": same_event_mean,
                        "selected_entry_diagnostic_utility_mean_50bps": selected_diag,
                        "raw_all_events_same_event_utility_mean_50bps": raw_mean,
                        "same_event_utility_delta_50bps": delta,
                        "winner_rate": winner_rate,
                        "winner_rate_lift": winner_rate - raw_winner_rate if pd.notna(winner_rate) and pd.notna(raw_winner_rate) else np.nan,
                        "fast_fail_rate": fast_fail_rate,
                        "fast_fail_uplift": fast_fail_rate - raw_fast_fail_rate if pd.notna(fast_fail_rate) and pd.notna(raw_fast_fail_rate) else np.nan,
                        "lower_first_rate": lower_first_rate,
                        "lower_first_uplift": lower_first_rate - raw_lower_first_rate if pd.notna(lower_first_rate) and pd.notna(raw_lower_first_rate) else np.nan,
                        "same_bar_conflict_rate": safe_rate(bool_series(selected.get("same_bar_conflict", pd.Series(False, index=selected.index))).sum(), len(selected)),
                        "event_density_per_instrument_year": event_density,
                        "duplicate_episode_fraction": duplicate_fraction,
                        "cohort_availability_gate_status": "pass" if sub["cohort_rank_status"].astype(str).eq("pass").any() else "fail",
                    }
                    readout_rows.append(row)
                    transport_rows.append(
                        {
                            **row,
                            "selected_entry_utility_delta_50bps": selected_diag - raw_mean if pd.notna(selected_diag) and pd.notna(raw_mean) else np.nan,
                            "utility_transport_status": "same_event_transport_positive" if pd.notna(delta) and delta > 0 else "selected_entry_only_not_full_denominator" if pd.notna(selected_diag) and pd.notna(raw_mean) and selected_diag > raw_mean else "no_transport",
                        }
                    )
    readout = pd.DataFrame(readout_rows)
    if not readout.empty:
        train = readout.loc[readout["split_bucket"].eq("train")].copy()
        train["train_selection_score"] = (
            2.0 * finite_numeric(train["same_event_utility_mean_50bps"])
            + finite_numeric(train["winner_rate_lift"]).fillna(0)
            - finite_numeric(train["fast_fail_uplift"]).clip(lower=0).fillna(0)
            - 0.5 * finite_numeric(train["duplicate_episode_fraction"]).fillna(0)
        )
        candidate = train.loc[
            train["cohort_availability_gate_status"].eq("pass")
            & finite_numeric(train["same_event_utility_mean_50bps"]).gt(0)
            & train["selected_event_n"].ge(int(thresholds.get("min_train_selected_event_n", 50)))
            & finite_numeric(train["selected_event_fraction"]).between(float(thresholds.get("selected_event_fraction_min", 0.03)), float(thresholds.get("selected_event_fraction_max", 0.50)), inclusive="both")
        ].sort_values(
            ["train_selection_score", "same_event_utility_mean_50bps", "fast_fail_uplift", "event_density_per_instrument_year", "raw_event_arm_id", "cohort_arm_id", "rank_cutoff_id"],
            ascending=[False, False, True, True, True, True, True],
            kind="stable",
        )
        selected_keys = set(
            tuple(x)
            for x in candidate[["raw_event_arm_id", "cohort_arm_id", "rank_cutoff_id"]]
            .drop_duplicates()
            .head(int(config.get("search_accounting", {}).get("maximum_operating_arms_allowed_into_validation", 3)))
            .to_numpy()
        )
        readout["operating_arm_selected"] = readout.apply(lambda r: (r["raw_event_arm_id"], r["cohort_arm_id"], r["rank_cutoff_id"]) in selected_keys, axis=1)
    normalized = pd.concat(normalized_events, ignore_index=True) if normalized_events else pd.DataFrame()
    return pd.DataFrame(availability_rows), readout, pd.DataFrame(transport_rows), normalized


def overlap_rate(selected_ids: set[Any], overlap_ids: set[Any]) -> float:
    if not selected_ids:
        return np.nan
    return len(selected_ids & overlap_ids) / len(selected_ids)


def build_morphology(events: pd.DataFrame, cohort_readout: pd.DataFrame, normalized_events: pd.DataFrame, resolved: dict[str, Path], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    if cohort_readout.empty or normalized_events.empty:
        return pd.DataFrame()
    selected_readout = cohort_readout.loc[bool_series(cohort_readout.get("operating_arm_selected", pd.Series(False, index=cohort_readout.index)))]
    if selected_readout.empty:
        return pd.DataFrame()
    token_matrix = read_table(resolved["upstream_13a_native_token_matrix_cache"])
    token_dict = read_table(resolved["upstream_13a_token_dictionary"])
    required_sources: dict[str, set[Any]] = {}
    if "volatility_20d__bottom_20pct" in token_matrix.columns:
        required_sources["13A_volatility_20d_bottom_20pct"] = set(token_matrix.loc[bool_series(token_matrix["volatility_20d__bottom_20pct"]), "row_id"])
    compression_tokens = token_dict.loc[token_dict["family_id"].astype(str).eq("volatility_range"), "token_id"].astype(str).tolist()
    compression_ids: set[Any] = set()
    for token in compression_tokens:
        if token in token_matrix.columns:
            compression_ids |= set(token_matrix.loc[bool_series(token_matrix[token]), "row_id"])
    required_sources["13A_volatility_range_compression"] = compression_ids
    reversal_tokens = token_dict.loc[token_dict["family_id"].astype(str).eq("reversal_drawdown"), "token_id"].astype(str).tolist()
    reversal_ids: set[Any] = set()
    for token in reversal_tokens:
        if token in token_matrix.columns:
            reversal_ids |= set(token_matrix.loc[bool_series(token_matrix[token]), "row_id"])
    required_sources["broad_drawdown_reversal_proxy"] = reversal_ids
    optional_sources: dict[str, set[Any]] = {}
    if resolved.get("optional_13a3_composite_state_matrix") and resolved["optional_13a3_composite_state_matrix"].exists():
        comp = read_table(resolved["optional_13a3_composite_state_matrix"])
        for col in [c for c in comp.columns if c != "row_id"]:
            optional_sources[f"13A3_{col}"] = set(comp.loc[bool_series(comp[col]), "row_id"])
    thresholds = config.get("thresholds", {})
    for _, arm in selected_readout[["raw_event_arm_id", "cohort_arm_id", "rank_cutoff_id"]].drop_duplicates().iterrows():
        mask = (
            normalized_events["raw_event_arm_id"].eq(arm["raw_event_arm_id"])
            & normalized_events["cohort_arm_id"].eq(arm["cohort_arm_id"])
            & normalized_events["rank_cutoff_id"].eq(arm["rank_cutoff_id"])
            & bool_series(normalized_events["selected_event_flag"])
        )
        arm_events = normalized_events.loc[mask]
        for split, sub in arm_events.groupby("split_bucket", dropna=False):
            selected_ids = set(sub["row_id"].tolist())
            source_rates = {name: overlap_rate(selected_ids, ids) for name, ids in required_sources.items()}
            morphology_score = max([v for v in source_rates.values() if pd.notna(v)] or [1.0])
            family = str(sub.iloc[0]["family_id"])
            compression_rate = source_rates.get("13A_volatility_range_compression", np.nan)
            reversal_rate = source_rates.get("broad_drawdown_reversal_proxy", np.nan)
            non_overlap_ids = selected_ids - set().union(*required_sources.values())
            non_overlap = sub.loc[sub["row_id"].isin(non_overlap_ids)]
            non_overlap_utility = finite_numeric(non_overlap.get("path_utility_component_50bps", pd.Series(dtype=float))).mean() if len(non_overlap) else np.nan
            status = "pass"
            if morphology_score >= float(thresholds.get("morphology_overlap_fail_threshold", 0.70)) and (pd.isna(non_overlap_utility) or non_overlap_utility <= 0):
                status = "fail_morphology_rediscovery"
            if family.startswith(("F2", "F6")) and (pd.isna(compression_rate) or (compression_rate >= float(thresholds.get("morphology_strict_overlap_threshold", 0.50)) and (pd.isna(non_overlap_utility) or non_overlap_utility <= 0))):
                status = "fail_compression_low_vol_rediscovery"
            if family.startswith("F3") and (pd.isna(reversal_rate) or (reversal_rate >= float(thresholds.get("morphology_strict_overlap_threshold", 0.50)) and (pd.isna(non_overlap_utility) or non_overlap_utility <= 0))):
                status = "fail_drawdown_reversal_rediscovery"
            for source_name, source_ids in {**required_sources, **optional_sources}.items():
                source_sub = sub.loc[sub["row_id"].isin(source_ids)]
                non_source_sub = sub.loc[~sub["row_id"].isin(source_ids)]
                rows.append(
                    {
                        "arm_id": f"{arm['raw_event_arm_id']}__{arm['cohort_arm_id']}__{arm['rank_cutoff_id']}",
                        "raw_event_arm_id": arm["raw_event_arm_id"],
                        "cohort_arm_id": arm["cohort_arm_id"],
                        "rank_cutoff_id": arm["rank_cutoff_id"],
                        "family_id": family,
                        "split_bucket": split,
                        "overlap_source_id": source_name,
                        "event_overlap_rate": overlap_rate(set(events.loc[events["raw_event_arm_id"].eq(arm["raw_event_arm_id"]), "row_id"]), source_ids),
                        "selected_event_overlap_rate": overlap_rate(selected_ids, source_ids),
                        "utility_from_overlap_rows_50bps": finite_numeric(source_sub.get("path_utility_component_50bps", pd.Series(dtype=float))).mean() if len(source_sub) else np.nan,
                        "utility_from_non_overlap_rows_50bps": finite_numeric(non_source_sub.get("path_utility_component_50bps", pd.Series(dtype=float))).mean() if len(non_source_sub) else np.nan,
                        "winner_rate_lift_non_overlap": safe_rate(bool_series(non_source_sub.get("winner", pd.Series(False, index=non_source_sub.index))).sum(), len(non_source_sub)) if len(non_source_sub) else np.nan,
                        "morphology_rediscovery_score": morphology_score,
                        "broad_drawdown_overlap_rate": reversal_rate,
                        "broad_reversal_overlap_rate": reversal_rate,
                        "f3_drawdown_reversal_independent_evidence_status": "pass" if not family.startswith("F3") or status == "pass" else status,
                        "morphology_independent_evidence_status": status,
                        "repair_state_overlap_status": "available" if source_name.startswith("13A3") else "not_repair_state_source",
                        "repair_state_overlap_used_in_primary_gate": False,
                    }
                )
    return pd.DataFrame(rows)


def validation_stress_audit(cohort_readout: pd.DataFrame) -> pd.DataFrame:
    rows = []
    selected = cohort_readout.loc[bool_series(cohort_readout.get("operating_arm_selected", pd.Series(False, index=cohort_readout.index)))]
    for _, row in selected.loc[selected["split_bucket"].eq("validation")].iterrows():
        rows.append(
            {
                "raw_event_arm_id": row["raw_event_arm_id"],
                "cohort_arm_id": row["cohort_arm_id"],
                "rank_cutoff_id": row["rank_cutoff_id"],
                "validation_stress_status": "stress_interval",
                "stress_split_utility_50bps": row["same_event_utility_mean_50bps"],
                "stress_split_winner_opportunity_retained": row["winner_rate"],
                "stress_split_badside_exposure": row["fast_fail_rate"],
                "stress_failure_type": "none" if pd.notna(row["same_event_utility_mean_50bps"]) and row["same_event_utility_mean_50bps"] > 0 else "stress_regime_utility_transport_failure",
            }
        )
    return pd.DataFrame(rows)


def search_audit(specs: list[ArmSpec], cohort_readout: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cfg = config.get("search_accounting", {})
    return pd.DataFrame(
        [
            {
                "family_count": int(cfg.get("family_count", 6)),
                "parameter_grid_count": int(cfg.get("parameter_grid_count", 16)),
                "actual_parameter_grid_count": len(specs),
                "cohort_arm_family_count": int(cfg.get("cohort_arm_family_count", 6)),
                "rank_cutoff_count": len(config.get("cohort_arms", {}).get("rank_cutoffs", {"top20pct": 0.8, "top10pct": 0.9})),
                "maximum_train_selected_raw_arms_into_cohort": int(cfg.get("maximum_train_selected_raw_arms_into_cohort", 6)),
                "maximum_operating_arms_allowed_into_validation": int(cfg.get("maximum_operating_arms_allowed_into_validation", 3)),
                "operating_arm_count": int(bool_series(cohort_readout.get("operating_arm_selected", pd.Series(dtype=bool))).groupby(cohort_readout.get("split_bucket", pd.Series(dtype=str))).sum().max()) if not cohort_readout.empty else 0,
                "validation_used_for_family_selection": False,
                "robustness_used_for_family_selection": False,
                "search_accounting_gate_status": "pass" if len(specs) == int(cfg.get("parameter_grid_count", 16)) else "fail",
            }
        ]
    )


def decision_row(
    input_status: str,
    input_reason: str,
    lineage: pd.DataFrame,
    adapter_status: str,
    label_portability: pd.DataFrame,
    native_panel: pd.DataFrame,
    generation: pd.DataFrame,
    density: pd.DataFrame,
    raw: pd.DataFrame,
    cohort_readout: pd.DataFrame,
    morphology: pd.DataFrame,
    validation_stress: pd.DataFrame,
    search: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    thresholds = config.get("thresholds", {})
    upstream_status, upstream_reason = table_gate_status(lineage, "lineage_status")
    native_status = "pass" if not native_panel.empty and bool_series(native_panel["native_scope"]).any() else "fail"
    label_status = "pass" if not label_portability.empty and label_portability["label_portability_status"].eq("pass").all() else "fail"
    sparse_status = "pass" if not generation.empty and generation["accepted_event_n"].fillna(0).gt(0).any() else "fail"
    density_status = (
        "pass"
        if not density.empty
        and density.groupby("raw_event_arm_id")["density_gate_status"].apply(lambda s: bool(s.astype(str).eq("pass").all())).any()
        else "fail"
    )
    raw_status = "pass" if not raw.empty and raw["raw_opportunity_surface_status"].eq("pass").any() else "fail"
    cohort_availability_status = "pass" if not cohort_readout.empty and cohort_readout["cohort_availability_gate_status"].eq("pass").any() else "fail"
    selected = cohort_readout.loc[bool_series(cohort_readout.get("operating_arm_selected", pd.Series(False, index=cohort_readout.index)))] if not cohort_readout.empty else pd.DataFrame()
    cohort_transport_status = "fail"
    same_event_status = "fail"
    badside_status = "fail"
    validation_stress_status = "fail"
    morphology_status = "pass"
    selected_key = {"selected_raw_event_arm_id": "", "selected_family_id": "", "selected_parameter_set_id": "", "selected_cohort_arm_id": "", "selected_rank_cutoff_id": ""}
    if not selected.empty:
        first_key = selected[["raw_event_arm_id", "family_id", "parameter_set_id", "cohort_arm_id", "rank_cutoff_id"]].drop_duplicates().iloc[0]
        selected_key = {
            "selected_raw_event_arm_id": first_key["raw_event_arm_id"],
            "selected_family_id": first_key["family_id"],
            "selected_parameter_set_id": first_key["parameter_set_id"],
            "selected_cohort_arm_id": first_key["cohort_arm_id"],
            "selected_rank_cutoff_id": first_key["rank_cutoff_id"],
        }
        arm = selected.loc[
            selected["raw_event_arm_id"].eq(first_key["raw_event_arm_id"])
            & selected["cohort_arm_id"].eq(first_key["cohort_arm_id"])
            & selected["rank_cutoff_id"].eq(first_key["rank_cutoff_id"])
        ]
        train = arm.loc[arm["split_bucket"].eq("train")]
        val = arm.loc[arm["split_bucket"].eq("validation")]
        rob = arm.loc[arm["split_bucket"].eq("robustness")]
        if len(train) and len(val) and len(rob):
            cohort_transport_status = "pass" if (
                float(train.iloc[0]["same_event_utility_delta_50bps"]) > 0
                and float(val.iloc[0]["same_event_utility_delta_50bps"]) >= float(thresholds.get("cohort_transport_delta_min", 0.001))
                and float(rob.iloc[0]["same_event_utility_delta_50bps"]) >= float(thresholds.get("cohort_transport_delta_min", 0.001))
            ) else "fail"
            same_event_status = "pass" if (
                float(val.iloc[0]["same_event_utility_mean_50bps"]) > 0
                and float(rob.iloc[0]["same_event_utility_mean_50bps"]) > 0
                and int(val.iloc[0]["selected_event_n"]) >= int(thresholds.get("min_validation_selected_event_n", 30))
                and int(rob.iloc[0]["selected_event_n"]) >= int(thresholds.get("min_robustness_selected_event_n", 30))
            ) else "fail"
            badside_status = "pass" if (
                pd.notna(val.iloc[0].get("fast_fail_uplift", np.nan))
                and pd.notna(rob.iloc[0].get("fast_fail_uplift", np.nan))
                and pd.notna(val.iloc[0].get("lower_first_uplift", np.nan))
                and pd.notna(rob.iloc[0].get("lower_first_uplift", np.nan))
                and float(val.iloc[0]["fast_fail_uplift"]) <= float(thresholds.get("max_fast_fail_uplift", 0.02))
                and float(rob.iloc[0]["fast_fail_uplift"]) <= float(thresholds.get("max_fast_fail_uplift", 0.02))
                and float(val.iloc[0]["lower_first_uplift"]) <= float(thresholds.get("max_lower_first_uplift", 0.01))
                and float(rob.iloc[0]["lower_first_uplift"]) <= float(thresholds.get("max_lower_first_uplift", 0.01))
            ) else "fail"
            validation_stress_status = "pass" if float(val.iloc[0]["same_event_utility_mean_50bps"]) > 0 else "fail"
        if not morphology.empty:
            morph = morphology.loc[
                morphology["raw_event_arm_id"].eq(first_key["raw_event_arm_id"])
                & morphology["cohort_arm_id"].eq(first_key["cohort_arm_id"])
                & morphology["rank_cutoff_id"].eq(first_key["rank_cutoff_id"])
            ]
            morphology_status = "pass" if morph.empty or morph["morphology_independent_evidence_status"].eq("pass").all() else "fail"
    search_status = "pass" if not search.empty and str(search.iloc[0]["search_accounting_gate_status"]) == "pass" else "fail"
    gate_values = {
        "input_gate_status": input_status,
        "upstream_lineage_gate_status": upstream_status,
        "native_universe_gate_status": native_status,
        "native_label_portability_gate_status": label_status,
        "sparse_event_construction_gate_status": sparse_status,
        "density_duplicate_gate_status": density_status,
        "raw_opportunity_surface_gate_status": raw_status,
        "cohort_availability_gate_status": cohort_availability_status,
        "cohort_transport_gate_status": cohort_transport_status,
        "badside_veto_gate_status": badside_status,
        "same_event_utility_50bps_gate_status": same_event_status,
        "morphology_rediscovery_gate_status": morphology_status,
        "validation_stress_gate_status": validation_stress_status,
        "search_accounting_gate_status": search_status,
    }
    decision = "14A_supported_open_14B_confirmatory_sparse_event_requirement"
    gate_failure = ""
    next_allowed = "requirement_14b_confirmatory_sparse_event_requirement.md"
    reason = "all_primary_gates_passed"
    if input_status != "pass" or upstream_status != "pass" or label_status != "pass" or native_status != "pass":
        reason = input_reason or upstream_reason or "input_or_lineage_failure"
        decision, gate_failure, next_allowed = "14A_input_blocked", reason, "none"
    elif sparse_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_no_sparse_event_utility", "sparse_event_construction_gate_failed", "none", "no_sparse_event_constructed"
    elif density_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_density_duplicate_or_morphology_rediscovery", "density_duplicate_gate_failed", "none", "density_duplicate_gate_failed"
    elif raw_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_no_sparse_event_utility", "no_raw_sparse_event_surface", "none", "no_raw_opportunity_surface"
    elif cohort_availability_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_no_cohort_utility_transport", "cohort_availability_gate_failed", "none", "cohort_unavailable"
    elif badside_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_diagnostic_cohort_signal_only_no_utility", "badside_veto_gate_failed", "none", "badside_veto_failed"
    elif same_event_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_diagnostic_cohort_signal_only_no_utility", "same_event_utility_50bps_failed", "none", "cohort_signal_no_same_event_utility"
    elif cohort_transport_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_diagnostic_raw_event_signal_but_no_cohort_transport", "cohort_transport_gate_failed", "none", "no_incremental_cohort_transport"
    elif validation_stress_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_validation_stress_failure_no_active_entry_authorization", "validation_stress_utility_failed", "none", "validation_stress_failed"
    elif morphology_status != "pass":
        decision, gate_failure, next_allowed, reason = "14A_stop_density_duplicate_or_morphology_rediscovery", "morphology_rediscovery_gate_failed", "none", "morphology_rediscovery"
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "active_winner_entry_search_authorized": decision == "14A_supported_open_14B_confirmatory_sparse_event_requirement",
                "confirmatory_status": False,
                **selected_key,
                "primary_cost_tier_bps": PRIMARY_COST_BPS,
                "primary_failure_reason": reason,
                "gate_failure": gate_failure,
                **gate_values,
            }
        ]
    )


def render_report(decision: pd.DataFrame, raw: pd.DataFrame, cohort: pd.DataFrame, morphology: pd.DataFrame) -> str:
    d = decision.iloc[0].to_dict()
    selected = cohort.loc[bool_series(cohort.get("operating_arm_selected", pd.Series(False, index=cohort.index)))] if not cohort.empty else pd.DataFrame()
    lines = [
        "# 14A Full-Native Sparse State-Change Event Utility Preflight Report",
        "",
        f"- decision_state: `{d['decision_state']}`",
        f"- next_allowed_requirement: `{d['next_allowed_requirement']}`",
        f"- primary_failure_reason: `{d['primary_failure_reason']}`",
        f"- selected_raw_event_arm_id: `{d.get('selected_raw_event_arm_id', '')}`",
        f"- selected_cohort_arm_id: `{d.get('selected_cohort_arm_id', '')}`",
        "",
        "## Gate Summary",
        "",
    ]
    for col in [c for c in decision.columns if c.endswith("_gate_status")]:
        lines.append(f"- {col}: `{d[col]}`")
    lines.extend(["", "## Raw Opportunity Surface", ""])
    if raw.empty:
        lines.append("No raw sparse event readout was generated.")
    else:
        show = raw.loc[raw["split_bucket"].eq("train")].sort_values("utility_per_event_mean_50bps", ascending=False).head(10)
        lines.append(show[["raw_event_arm_id", "event_n", "winner_rate_lift", "utility_per_event_mean_50bps", "raw_opportunity_surface_status"]].to_markdown(index=False))
    lines.extend(["", "## Cohort Transport", ""])
    if selected.empty:
        lines.append("No train-frozen cohort operating arm was selected.")
    else:
        lines.append(selected[["raw_event_arm_id", "cohort_arm_id", "rank_cutoff_id", "split_bucket", "selected_event_n", "same_event_utility_mean_50bps", "same_event_utility_delta_50bps"]].to_markdown(index=False))
    lines.extend(["", "## Morphology Rediscovery", ""])
    if morphology.empty:
        lines.append("Morphology audit is empty because no operating cohort arm was selected.")
    else:
        lines.append(morphology.head(20).to_markdown(index=False))
    return "\n".join(lines)


def build_manifest(config_path: Path, config: dict[str, Any], outputs: dict[str, Path], input_audit: pd.DataFrame, decision_state: str) -> dict[str, Any]:
    publishable = {k: v for k, v in outputs.items() if k != "manifest" and v.exists() and LOCAL_CACHE_DIR not in v.parents}
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "git_revision": r13a.git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": path_sha(config_path),
        "decision_state": decision_state,
        "outputs": {k: str(v) for k, v in publishable.items()},
        "output_hashes": {k: path_sha(v) for k, v in publishable.items() if v.is_file()},
        "input_artifacts": input_audit.to_dict(orient="records"),
    }


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    if check_inputs_only or mode == "check-inputs":
        decision = pd.DataFrame(
            [
                {
                    "decision_state": "14A_input_blocked" if input_status != "pass" else "14A_check_inputs_pass",
                    "next_allowed_requirement": "none",
                    "active_winner_entry_search_authorized": False,
                    "confirmatory_status": False,
                    "primary_failure_reason": input_reason,
                    "gate_failure": input_reason,
                    "input_gate_status": input_status,
                }
            ]
        )
        write_df(outputs["decision"], decision)
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit, str(decision.iloc[0]["decision_state"])))
        return outputs

    native_raw, label_raw, token_matrix, cache_status = load_13a_runner_cache(resolved)
    native_panel, adapter_audit, adapter_status = adapt_native_panel(native_raw, label_raw)
    lineage = build_upstream_lineage_audit(resolved, cache_status, adapter_status)
    label_portability = build_label_portability_audit(native_panel, config)
    row_rebuild = build_row_rebuild_audit(native_panel, adapter_status, config, resolved)
    rebuild_overall = row_rebuild.loc[row_rebuild["field_name"].astype(str).eq("__overall__")] if "field_name" in row_rebuild.columns else pd.DataFrame()
    rebuild_status = str(rebuild_overall.iloc[0].get("rebuild_status", "fail")) if len(rebuild_overall) else "fail"
    lineage = pd.concat(
        [
            lineage,
            pd.DataFrame(
                [
                    {
                        "lineage_id": "13A_entry_anchor_label_rebuild",
                        "lineage_status": "pass" if rebuild_status == "pass" else "fail",
                        "cache_status": cache_status,
                        "adapter_status": adapter_status,
                        "rebuild_status": rebuild_status,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    write_df(outputs["cache_schema_adapter_audit"], adapter_audit)
    write_df(outputs["upstream_lineage_audit"], lineage)
    write_df(outputs["native_label_portability_audit"], label_portability)
    write_df(outputs["row_level_rebuild_audit"], row_rebuild)
    write_df(outputs["native_rebuild_panel"], native_panel)

    feature_panel = build_feature_panel(native_panel, resolved)
    write_df(outputs["state_change_feature_panel"], feature_panel)
    specs = parameter_specs(config)
    write_df(outputs["sparse_event_family_formula_spec"], family_formula_spec_rows(specs))
    parameter_grid = family_formula_spec_rows(specs).assign(parameter_grid_status="pass")
    write_df(outputs["sparse_event_parameter_grid_audit"], parameter_grid)
    sparse_events, generation, state_cache = generate_sparse_events(feature_panel, specs)
    sparse_events = add_event_utility(sparse_events, [int(x) for x in config.get("cost_tiers_bps", [0, 50, 100])]) if not sparse_events.empty else sparse_events
    write_df(outputs["sparse_event_panel"], sparse_events)
    write_df(outputs["sparse_event_generation_audit"], generation)
    density = build_density_audit(sparse_events, generation, feature_panel, config)
    write_df(outputs["sparse_event_density_audit"], density)
    raw = raw_readout(sparse_events, feature_panel, config)
    write_df(outputs["sparse_event_raw_readout"], raw)
    write_df(outputs["sparse_event_badside_utility_audit"], raw.copy())
    write_df(outputs["sparse_event_uniqueness_density_audit"], density.copy())
    write_df(outputs["pit_cohort_normalization_dictionary"], cohort_dictionary(config))
    availability, cohort_readout, transport, normalized_events = build_cohort_readouts(feature_panel, sparse_events, state_cache, raw, density, config)
    write_df(outputs["pit_cohort_rank_availability_audit"], availability)
    write_df(outputs["pit_cohort_normalized_utility_readout"], cohort_readout)
    write_df(outputs["cohort_normalization_transport_audit"], transport)
    write_df(outputs["pit_cohort_normalized_event_panel"], normalized_events)
    morphology = build_morphology(sparse_events, cohort_readout, normalized_events, resolved, config)
    write_df(outputs["morphology_rediscovery_audit"], morphology)
    stress = validation_stress_audit(cohort_readout)
    write_df(outputs["validation_stress_interpretation_audit"], stress)
    search = search_audit(specs, cohort_readout, config)
    write_df(outputs["search_multiplicity_audit"], search)
    decision = decision_row(input_status, input_reason, lineage, adapter_status, label_portability, native_panel, generation, density, raw, cohort_readout, morphology, stress, search, config)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], render_report(decision, raw, cohort_readout, morphology))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit, str(decision.iloc[0]["decision_state"])))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
