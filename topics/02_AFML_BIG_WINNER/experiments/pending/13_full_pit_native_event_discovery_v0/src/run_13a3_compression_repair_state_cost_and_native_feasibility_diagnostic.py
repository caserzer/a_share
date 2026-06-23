#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_13A_PATH = EXPERIMENT_DIR / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"
RUNNER_13A2_PATH = EXPERIMENT_DIR / "src" / "run_13a2_compression_directional_disambiguation_preflight.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13a = load_runner(RUNNER_13A_PATH, "run_13a_full_pit_native_token_cartography_preflight")
r13a2 = load_runner(RUNNER_13A2_PATH, "run_13a2_compression_directional_disambiguation_preflight")


RUN_ID = "13A3_compression_repair_state_cost_and_native_feasibility_diagnostic"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13A3"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
SPLITS = ("train", "validation", "robustness")
FAST_FAIL_MAX_SESSIONS = 5
BASE_TOKEN_ID = "volatility_20d__bottom_20pct"
ANCHOR_PRIMITIVES = ("max_drawdown_20d", "distance_to_20d_low", "rebound_from_20d_low", "ret_20d", "volatility_20d")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 13A3 compression repair-state diagnostic.")
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
        "upstream_13a_lineage_audit": TABLE_DIR / "upstream_13a_lineage_audit.csv",
        "upstream_13a2_lineage_audit": TABLE_DIR / "upstream_13a2_lineage_audit.csv",
        "label_lineage_audit": TABLE_DIR / "label_lineage_audit.csv",
        "cost_buffer_lineage_audit": TABLE_DIR / "cost_buffer_lineage_audit.csv",
        "row_level_cache_audit": TABLE_DIR / "row_level_cache_audit.csv",
        "composite_repair_state_dictionary": TABLE_DIR / "composite_repair_state_dictionary.csv",
        "cost_buffer_sensitivity_audit": TABLE_DIR / "cost_buffer_sensitivity_audit.csv",
        "cost_buffer_turning_point_summary": TABLE_DIR / "cost_buffer_turning_point_summary.csv",
        "composite_native_readout": TABLE_DIR / "composite_native_readout.csv",
        "composite_badside_utility_audit": TABLE_DIR / "composite_badside_utility_audit.csv",
        "composite_denominator_drift_audit": TABLE_DIR / "composite_denominator_drift_audit.csv",
        "composite_morphology_independent_evidence_audit": TABLE_DIR / "composite_morphology_independent_evidence_audit.csv",
        "composite_search_multiplicity_audit": TABLE_DIR / "composite_search_multiplicity_audit.csv",
        "compression_repair_state_feasibility_decision": TABLE_DIR / "compression_repair_state_feasibility_decision.csv",
        "composite_state_matrix": LOCAL_CACHE_DIR / "composite_state_matrix.parquet",
        "report": REPORT_DIR / "compression_repair_state_cost_and_native_feasibility_diagnostic_report.md",
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


def safe_rate(num: Any, den: Any) -> float:
    return r13a.safe_rate(num, den)


def boolish(value: Any) -> bool:
    return r13a.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13a.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13a.finite_numeric(series)


def auc_score(values: pd.Series, labels: pd.Series) -> float:
    return r13a.auc_score(values, labels)


def normal_ci_diff(p1: float, n1: int, p0: float, n0: int, alpha: float = 0.10) -> tuple[float, float]:
    return r13a.normal_ci_diff(p1, n1, p0, n0, alpha=alpha)


def fast_fail_mask(frame: pd.DataFrame) -> pd.Series:
    lower = bool_series(frame.get("lower_first", pd.Series(False, index=frame.index)))
    ttl = finite_numeric(frame.get("time_to_lower", pd.Series(np.nan, index=frame.index)))
    return lower & ttl.le(FAST_FAIL_MAX_SESSIONS)


def utility_per_entry(frame: pd.DataFrame, cost: float) -> float:
    n = len(frame)
    if n == 0:
        return np.nan
    upper = safe_rate(bool_series(frame.get("upper_first", pd.Series(dtype=bool))).sum(), n)
    lower = safe_rate(bool_series(frame.get("lower_first", pd.Series(dtype=bool))).sum(), n)
    median_upper = finite_numeric(frame.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(frame.get("lower_barrier", pd.Series(dtype=float))).median())
    if pd.isna(upper) or pd.isna(lower) or pd.isna(median_upper) or pd.isna(median_lower):
        return np.nan
    return float(upper * median_upper - lower * median_lower - cost)


def utility_total_indexed(frame: pd.DataFrame, native_n: int, cost: float) -> float:
    utility = utility_per_entry(frame, cost)
    return utility * safe_rate(len(frame), native_n) if pd.notna(utility) else np.nan


def cost_label(cost: float) -> str:
    return f"{int(round(cost * 10000))}bps"


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13a": (),
        "upstream_requirement_13a2": (),
        "upstream_report_13a": (),
        "upstream_report_13a2": (),
        "upstream_requirement_12a7g": (),
        "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument"),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket"),
        "upstream_12a7g_table_dir": (),
        "upstream_12a7g_manifest": (),
        "upstream_13a_manifest": (),
        "upstream_13a_decision": ("decision_state", "selected_token_id", "sequence_mining_authorized"),
        "upstream_13a_token_dictionary": ("token_id", "primitive_id", "threshold_rule", "threshold_value"),
        "upstream_13a_morphology": ("token_id", "split_bucket"),
        "upstream_13a_native_universe_cache": ("row_id", "native_scope", "split", "winner_positive"),
        "upstream_13a_native_token_matrix_cache": ("row_id",),
        "upstream_13a2_manifest": (),
        "upstream_13a2_decision": ("decision_state", "sequence_mining_authorized"),
        "upstream_13a2_filter_dictionary": ("filter_id", "primitive_id_1", "threshold_rule_1"),
        "upstream_13a2_threshold_freeze": ("primitive_id", "threshold_rule", "threshold_value"),
        "upstream_13a2_readout": ("filter_id", "split_bucket"),
        "upstream_13a2_badside": ("filter_id", "split_bucket", "cost_buffer_return"),
        "upstream_13a2_match": ("filter_id", "split_bucket"),
        "upstream_13a2_search": ("candidate_grid_n", "effective_search_space_n"),
        "upstream_13a2_compression_base_cache": ("row_id", "split", "winner_positive"),
        "upstream_13a2_directional_filter_matrix_cache": ("row_id",),
        "upstream_13a_config": (),
        "upstream_13a2_config": (),
    }


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id.startswith("upstream_13a2"):
        return "upstream_13a2_lineage"
    if artifact_id.startswith("upstream_13a"):
        return "upstream_13a_lineage"
    if artifact_id.startswith("upstream_requirement_12a7g"):
        return "upstream_12a7g_label_lineage"
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


def table_status(frame: pd.DataFrame, status_col: str) -> tuple[str, str]:
    if frame.empty or status_col not in frame.columns:
        return "fail", "missing_status_table"
    bad = frame.loc[~frame[status_col].astype(str).isin(["pass", "reported", "not_applicable"])]
    if len(bad):
        key_col = frame.columns[0]
        return "fail", ";".join(bad[key_col].astype(str).head(20).tolist())
    return "pass", ""


def ensure_upstream_outputs(resolved: dict[str, Path], mode: str) -> None:
    if mode == "check-inputs":
        return
    a_required = [resolved["upstream_13a_native_universe_cache"], resolved["upstream_13a_native_token_matrix_cache"]]
    if any(not p.exists() for p in a_required):
        r13a.run(resolved["upstream_13a_config"], mode="full")
    a2_required = [resolved["upstream_13a2_compression_base_cache"], resolved["upstream_13a2_directional_filter_matrix_cache"]]
    if any(not p.exists() for p in a2_required):
        r13a2.run(resolved["upstream_13a2_config"], mode="full")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def selected_label_from_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return r13a.load_yaml(path).get("selected_label", {})
    except Exception:
        return {}


def build_label_lineage_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    expected = {
        "label_id": "vol20d_kup2p0_kdn1p0_H20",
        "vol_reference_id": "volatility_20d",
        "horizon_sessions": 20,
        "k_up": 2.0,
        "k_dn": 1.0,
    }
    rows: list[dict[str, Any]] = []
    for source_id, path_key in [("13A_config", "upstream_13a_config"), ("13A2_config", "upstream_13a2_config")]:
        label = selected_label_from_config(resolved[path_key])
        for field, exp in expected.items():
            obs = label.get(field)
            ok = obs == exp
            if isinstance(exp, float):
                ok = pd.notna(obs) and math.isclose(float(obs), exp, rel_tol=1e-12, abs_tol=1e-12)
            rows.append(
                {
                    "lineage_check_id": f"{source_id}.{field}",
                    "observed_value": obs,
                    "expected_value": exp,
                    "lineage_status": "pass" if ok else "fail",
                }
            )
    req_text = resolved["upstream_requirement_12a7g"].read_text() if resolved["upstream_requirement_12a7g"].exists() else ""
    for check_id, needle in [
        ("12A7g.same_bar_priority", "same_bar_priority = lower_first"),
        ("12A7g.vol_reference_id", "vol_reference_id = volatility_20d"),
        ("12A7g.horizon_grid_contains_20", "horizon_sessions in {20, 40, 60}"),
        ("12A7g.k_grid_contains_primary", "k_up in {1.0, 1.5, 2.0, 2.5}"),
    ]:
        rows.append(
            {
                "lineage_check_id": check_id,
                "observed_value": "present" if needle in req_text else "missing",
                "expected_value": needle,
                "lineage_status": "pass" if needle in req_text else "fail",
            }
        )
    return pd.DataFrame(rows)


def upstream_cost_from_config(path: Path, source_id: str) -> tuple[float | None, str]:
    if not path.exists():
        return None, f"{source_id}:missing_config"
    cfg = r13a.load_yaml(path)
    if "cost_buffer" in cfg and "default_return" in cfg["cost_buffer"]:
        return float(cfg["cost_buffer"]["default_return"]), f"{source_id}:cost_buffer.default_return"
    thresholds = cfg.get("thresholds", {})
    if "cost_buffer_bps" in thresholds:
        return float(thresholds["cost_buffer_bps"]) / 10000.0, f"{source_id}:thresholds.cost_buffer_bps"
    return None, f"{source_id}:not_declared"


def build_cost_buffer_lineage_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    local_reference = float(config.get("cost_buffer", {}).get("reference_return", 0.01))
    rows: list[dict[str, Any]] = []
    upstream_values: list[float] = []
    for source_id, path_key in [("13A", "upstream_13a_config"), ("13A2", "upstream_13a2_config")]:
        value, source = upstream_cost_from_config(resolved[path_key], source_id)
        if value is not None:
            upstream_values.append(value)
        ok = value is not None and math.isclose(float(value), local_reference, rel_tol=1e-12, abs_tol=1e-12)
        rows.append(
            {
                "lineage_check_id": f"{source_id}.cost_buffer_return",
                "upstream_cost_buffer_return": np.nan if value is None else value,
                "upstream_cost_buffer_source": source,
                "reference_cost_buffer_return": local_reference,
                "lineage_status": "pass" if ok else "fail",
            }
        )
    consistent = bool(upstream_values) and all(math.isclose(v, upstream_values[0], rel_tol=1e-12, abs_tol=1e-12) for v in upstream_values)
    rows.append(
        {
            "lineage_check_id": "upstream_cost_consistency",
            "upstream_cost_buffer_return": upstream_values[0] if consistent else np.nan,
            "upstream_cost_buffer_source": "13A_and_13A2",
            "reference_cost_buffer_return": local_reference,
            "lineage_status": "pass" if consistent and math.isclose(upstream_values[0], local_reference, rel_tol=1e-12, abs_tol=1e-12) else "fail",
        }
    )
    return pd.DataFrame(rows)


def manifest_schema_lookup(path: Path) -> dict[str, str]:
    manifest = load_json_if_exists(path)
    out: dict[str, str] = {}
    for row in manifest.get("local_cache_audit", []) or []:
        artifact = str(row.get("artifact_id", ""))
        if artifact:
            out[artifact] = str(row.get("schema_hash", ""))
    return out


def cache_audit_row(check_id: str, observed: Any, expected: Any, ok: bool, detail: str = "") -> dict[str, Any]:
    return {
        "cache_check_id": check_id,
        "observed_value": observed,
        "expected_value": expected,
        "cache_status": "pass" if ok else "fail",
        "detail": detail,
    }


def build_row_level_cache_audit(
    native_panel: pd.DataFrame,
    filter_matrix: pd.DataFrame,
    native_token_matrix: pd.DataFrame,
    base_panel: pd.DataFrame,
    dictionary: pd.DataFrame,
    base_threshold: float,
    resolved: dict[str, Path],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    native_ids = native_panel["row_id"]
    filter_ids = filter_matrix["row_id"]
    token_ids = native_token_matrix["row_id"]
    base_ids = base_panel["row_id"]
    rows.append(cache_audit_row("native_panel.row_id_unique", int(native_ids.nunique()), len(native_panel), native_ids.is_unique))
    rows.append(cache_audit_row("filter_matrix.row_id_unique", int(filter_ids.nunique()), len(filter_matrix), filter_ids.is_unique))
    rows.append(cache_audit_row("native_token_matrix.row_id_unique", int(token_ids.nunique()), len(native_token_matrix), token_ids.is_unique))
    rows.append(cache_audit_row("compression_base.row_id_unique", int(base_ids.nunique()), len(base_panel), base_ids.is_unique))
    native_set = set(native_ids.tolist())
    rows.append(cache_audit_row("filter_matrix.coverage_equals_native", len(set(filter_ids.tolist()) ^ native_set), 0, set(filter_ids.tolist()) == native_set))
    rows.append(cache_audit_row("native_token_matrix.coverage_equals_native", len(set(token_ids.tolist()) ^ native_set), 0, set(token_ids.tolist()) == native_set))
    rows.append(cache_audit_row("compression_base.subset_native", len(set(base_ids.tolist()) - native_set), 0, set(base_ids.tolist()).issubset(native_set)))
    if {"row_id", "split"} <= set(base_panel.columns):
        base_split = base_panel.set_index("row_id")["split"].astype(str)
        native_split = native_panel.set_index("row_id").loc[base_split.index, "split"].astype(str)
        mismatch = int((base_split != native_split).sum())
        rows.append(cache_audit_row("compression_base.split_boundary_equality", mismatch, 0, mismatch == 0))
    else:
        rows.append(cache_audit_row("compression_base.split_boundary_equality", "missing_columns", "row_id+split", False))
    if {"native_scope", "volatility_20d"} <= set(native_panel.columns) and pd.notna(base_threshold):
        expected_base = bool_series(native_panel["native_scope"]) & finite_numeric(native_panel["volatility_20d"]).le(float(base_threshold))
        observed_base = native_panel["row_id"].isin(set(base_ids.tolist()))
        mismatch = int((expected_base.to_numpy(dtype=bool) != observed_base.to_numpy(dtype=bool)).sum())
        rows.append(cache_audit_row("compression_base.membership_equality", mismatch, 0, mismatch == 0))
    else:
        rows.append(cache_audit_row("compression_base.membership_equality", "missing_columns_or_threshold", "native_scope+volatility_20d+threshold", False))
    required_label_cols = ["winner_positive", "upper_first", "lower_first", "upper_barrier", "lower_barrier", "time_to_lower", "split"]
    missing = sorted(set(required_label_cols) - set(native_panel.columns))
    rows.append(cache_audit_row("selected_label.fields_present", ";".join(missing), "", not missing))
    rows.append(cache_audit_row("composite_threshold_value_equality", int(dictionary["state_reproduction_status"].astype(str).ne("pass").sum()), 0, dictionary["state_reproduction_status"].astype(str).eq("pass").all()))
    fm = filter_matrix.set_index("row_id")
    base_set = set(base_ids.tolist())
    for d in dictionary.itertuples(index=False):
        source_id = str(d.source_13a2_filter_id)
        if source_id not in fm.columns:
            rows.append(cache_audit_row(f"{d.state_id}.source_filter_present", "missing", source_id, False))
            continue
        outside_base = int((fm[source_id].astype(bool) & ~fm.index.to_series().isin(base_set)).sum())
        rows.append(cache_audit_row(f"{d.state_id}.membership_subset_compression_base", outside_base, 0, outside_base == 0))
    expected_schema = manifest_schema_lookup(resolved["upstream_13a2_manifest"])
    for artifact_id, path_key in [
        ("compression_base_panel", "upstream_13a2_compression_base_cache"),
        ("directional_filter_matrix", "upstream_13a2_directional_filter_matrix_cache"),
    ]:
        expected = expected_schema.get(artifact_id, "")
        if expected:
            observed = schema_hash(resolved[path_key])
            rows.append(cache_audit_row(f"{artifact_id}.manifest_schema_hash", observed, expected, observed == expected))
        else:
            rows.append(cache_audit_row(f"{artifact_id}.manifest_schema_hash", "not_declared", "record_if_declared", True, "manifest_does_not_declare_schema_hash"))
    return pd.DataFrame(rows)


def upstream_13a_lineage_audit(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str, str, float]:
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []
    threshold = np.nan
    try:
        decision = read_table(resolved["upstream_13a_decision"]).iloc[0]
        token_dict = read_table(resolved["upstream_13a_token_dictionary"])
        tok = token_dict.loc[token_dict["token_id"].astype(str).eq(BASE_TOKEN_ID)]
        checks = {
            "input_gate_status": str(decision.get("input_gate_status", "")) == "pass",
            "upstream_lineage_gate_status": str(decision.get("upstream_lineage_gate_status", "")) == "pass",
            "native_universe_gate_status": str(decision.get("native_universe_gate_status", "")) == "pass",
            "label_portability_gate_status": str(decision.get("label_portability_gate_status", "")) == "pass",
            "selected_token_id": str(decision.get("selected_token_id", "")) == BASE_TOKEN_ID,
            "selected_token_family_id": str(decision.get("selected_token_family_id", "")) == "volatility_range",
            "sequence_mining_authorized": not boolish(decision.get("sequence_mining_authorized", False)),
            "dictionary_token_present": not tok.empty,
        }
        if not tok.empty:
            t = tok.iloc[0]
            threshold = float(t["threshold_value"])
            checks.update(
                {
                    "dictionary_primitive_id": str(t.get("primitive_id", "")) == "volatility_20d",
                    "dictionary_threshold_rule": str(t.get("threshold_rule", "")) == "bottom_20pct",
                    "dictionary_threshold_split": str(t.get("threshold_split", "")) == "train",
                    "dictionary_future_data_used": not boolish(t.get("future_data_used", True)),
                    "dictionary_comparator": str(t.get("comparator", "")) == "le",
                }
            )
        for check_id, ok in checks.items():
            if not ok:
                status = "fail"
                reason.append(check_id)
            rows.append({"lineage_check_id": check_id, "observed_value": "contract", "expected_value": "pass", "lineage_status": "pass" if ok else "fail"})
    except Exception as exc:
        status = "fail"
        reason.append(f"read_error:{type(exc).__name__}")
        rows.append({"lineage_check_id": "upstream_13a_read", "observed_value": str(exc), "expected_value": "readable", "lineage_status": "fail"})
    return pd.DataFrame(rows), status, ";".join(reason), threshold


def upstream_13a2_lineage_audit(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str, str]:
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []
    try:
        decision = read_table(resolved["upstream_13a2_decision"]).iloc[0]
        if boolish(decision.get("sequence_mining_authorized", False)):
            status = "fail"
            reason.append("already_authorized")
            rows.append(
                {
                    "lineage_check_id": "sequence_mining_authorized",
                    "observed_value": str(decision.get("sequence_mining_authorized", "")),
                    "expected_value": "False",
                    "lineage_status": "fail_already_authorized",
                }
            )
            return pd.DataFrame(rows), status, ";".join(reason)
        required = {
            "input_gate_status": "pass",
            "upstream_13a_lineage_gate_status": "pass",
            "label_lineage_gate_status": "pass",
            "cost_buffer_lineage_gate_status": "pass",
            "base_compression_gate_status": "pass",
            "candidate_grid_gate_status": "pass",
            "decision_state": "13A2_no_directional_filter_survives_stop_event_mining",
        }
        for key, expected in required.items():
            observed = str(decision.get(key, ""))
            ok = observed == expected
            if not ok:
                status = "fail"
                reason.append(key)
            rows.append({"lineage_check_id": key, "observed_value": observed, "expected_value": expected, "lineage_status": "pass" if ok else "fail"})
        rows.append({"lineage_check_id": "sequence_mining_authorized", "observed_value": str(decision.get("sequence_mining_authorized", "")), "expected_value": "False", "lineage_status": "pass"})
        for optional in [
            "winner_uplift_gate_status",
            "direction_readout_gate_status",
            "control_quality_gate_status",
            "badside_utility_gate_status",
            "morphology_gate_status",
            "morphology_independent_evidence_gate_status",
            "stability_gate_status",
            "search_control_gate_status",
            "deployability_gate_status",
            "decision_reason",
        ]:
            rows.append({"lineage_check_id": optional, "observed_value": str(decision.get(optional, "")), "expected_value": "record_only", "lineage_status": "reported"})
    except Exception as exc:
        status = "fail"
        reason.append(f"read_error:{type(exc).__name__}")
        rows.append({"lineage_check_id": "upstream_13a2_read", "observed_value": str(exc), "expected_value": "readable", "lineage_status": "fail"})
    return pd.DataFrame(rows), status, ";".join(reason)


def load_cost_grid(config: dict[str, Any]) -> list[float]:
    return [float(x) for x in config.get("cost_buffer", {}).get("grid", [0.0, 0.0025, 0.005, 0.0075, 0.01])]


def build_composite_dictionary(config: dict[str, Any], resolved: dict[str, Path], base_threshold: float) -> tuple[pd.DataFrame, str, str]:
    filter_dict = read_table(resolved["upstream_13a2_filter_dictionary"])
    threshold = read_table(resolved["upstream_13a2_threshold_freeze"])
    threshold_lookup = {
        (str(row.primitive_id), str(row.threshold_rule)): float(row.threshold_value)
        for row in threshold.itertuples(index=False)
        if str(getattr(row, "threshold_freeze_status", "pass")) == "pass"
    }
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []
    for item in config.get("composite_states", []):
        source_id = str(item["source_13a2_filter_id"])
        source = filter_dict.loc[filter_dict["filter_id"].astype(str).eq(source_id)]
        row_status = "pass"
        if source.empty:
            row_status = "fail_missing_source_filter"
            status = "fail"
            reason.append(source_id)
            src = pd.Series(dtype=object)
        else:
            src = source.iloc[0]
            for primitive_col, rule_col, value_col in [("primitive_id_1", "threshold_rule_1", "threshold_value_1"), ("primitive_id_2", "threshold_rule_2", "threshold_value_2")]:
                primitive = str(src.get(primitive_col, ""))
                rule = str(src.get(rule_col, ""))
                if not primitive or primitive.lower() == "nan":
                    continue
                key = (primitive, rule)
                if key not in threshold_lookup or not math.isclose(float(src[value_col]), threshold_lookup[key], rel_tol=1e-12, abs_tol=1e-12):
                    row_status = "fail_threshold_mismatch"
                    status = "fail"
                    reason.append(f"{source_id}:{primitive}:{rule}")
        rows.append(
            {
                "state_id": item["state_id"],
                "state_priority": int(item["state_priority"]),
                "source_13a2_filter_id": source_id,
                "base_token_id": BASE_TOKEN_ID,
                "base_threshold_value": base_threshold,
                "component_1_primitive_id": str(src.get("primitive_id_1", "")),
                "component_1_threshold_rule": str(src.get("threshold_rule_1", "")),
                "component_1_threshold_value": src.get("threshold_value_1", np.nan),
                "component_2_primitive_id": str(src.get("primitive_id_2", "")),
                "component_2_threshold_rule": str(src.get("threshold_rule_2", "")),
                "component_2_threshold_value": src.get("threshold_value_2", np.nan),
                "component_family": item["component_family"],
                "directional_component_class": item["directional_component_class"],
                "morphology_risk": item["morphology_risk"],
                "shortlist_source": "post_13A2_diagnostic_report",
                "confirmatory_status": False,
                "threshold_source_split": "train",
                "future_data_used": False,
                "state_reproduction_status": row_status,
            }
        )
    return pd.DataFrame(rows), status, ";".join(reason)


def build_composite_state_matrix(native_panel: pd.DataFrame, filter_matrix: pd.DataFrame, dictionary: pd.DataFrame) -> pd.DataFrame:
    matrix = filter_matrix.set_index("row_id", drop=False)
    row_ids = native_panel["row_id"].to_numpy()
    out: dict[str, Any] = {"row_id": row_ids}
    for row in dictionary.itertuples(index=False):
        source_id = str(row.source_13a2_filter_id)
        if source_id in matrix.columns and str(row.state_reproduction_status) == "pass":
            out[str(row.state_id)] = matrix[source_id].reindex(row_ids).fillna(False).to_numpy(dtype=bool)
        else:
            out[str(row.state_id)] = np.zeros(len(row_ids), dtype=bool)
    return pd.DataFrame(out)


def split_mask(panel: pd.DataFrame, split: str) -> pd.Series:
    return bool_series(panel["native_scope"]) & panel["split"].astype(str).eq(split)


def frame_for(panel: pd.DataFrame, split: str, mask: pd.Series | None = None) -> pd.DataFrame:
    base = split_mask(panel, split)
    if mask is not None:
        base = base & mask.reindex(panel.index).fillna(False).astype(bool)
    return panel.loc[base]


def readout_for_state(state_id: str, split: str, panel: pd.DataFrame, state_mask: pd.Series) -> dict[str, Any]:
    native_mask = split_mask(panel, split)
    treated_mask = native_mask & state_mask
    native = panel.loc[native_mask]
    treated = panel.loc[treated_mask]
    treated_n = int(len(treated))
    native_n = int(len(native))
    treated_pos = int(bool_series(treated.get("winner_positive", pd.Series(dtype=bool))).sum()) if treated_n else 0
    native_pos = int(bool_series(native.get("winner_positive", pd.Series(dtype=bool))).sum()) if native_n else 0
    treated_rate = safe_rate(treated_pos, treated_n)
    native_rate = safe_rate(native_pos, native_n)
    diff = treated_rate - native_rate if pd.notna(treated_rate) and pd.notna(native_rate) else np.nan
    ci_low, ci_high = normal_ci_diff(treated_rate, treated_n, native_rate, native_n) if pd.notna(diff) else (np.nan, np.nan)
    auc = auc_score(state_mask.loc[native.index].astype(float), native["winner_positive"]) if native_n else np.nan
    return {
        "state_id": state_id,
        "split_bucket": split,
        "treated_n": treated_n,
        "treated_positive_n": treated_pos,
        "native_denominator_n": native_n,
        "native_positive_n": native_pos,
        "coverage_share": safe_rate(treated_n, native_n),
        "captured_positive_share": safe_rate(treated_pos, native_pos),
        "treated_winner_rate": treated_rate,
        "native_winner_rate": native_rate,
        "winner_rate_diff_vs_native": diff,
        "winner_rate_diff_ci_low": ci_low,
        "winner_rate_diff_ci_high": ci_high,
        "treated_lower_first_rate": safe_rate(bool_series(treated.get("lower_first", pd.Series(dtype=bool))).sum(), treated_n),
        "native_lower_first_rate": safe_rate(bool_series(native.get("lower_first", pd.Series(dtype=bool))).sum(), native_n),
        "lower_first_uplift_vs_native": safe_rate(bool_series(treated.get("lower_first", pd.Series(dtype=bool))).sum(), treated_n) - safe_rate(bool_series(native.get("lower_first", pd.Series(dtype=bool))).sum(), native_n),
        "treated_fast_fail_rate": safe_rate(fast_fail_mask(treated).sum(), treated_n),
        "native_fast_fail_rate": safe_rate(fast_fail_mask(native).sum(), native_n),
        "fast_fail_uplift_vs_native": safe_rate(fast_fail_mask(treated).sum(), treated_n) - safe_rate(fast_fail_mask(native).sum(), native_n),
        "binary_state_auc": auc,
        "top_lift_proxy": diff,
        "readout_status": "pass" if treated_n > 0 and pd.notna(diff) and diff > 0 else "fail",
    }


def build_composite_native_readout(panel: pd.DataFrame, state_matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    matrix = state_matrix.set_index("row_id")
    rows: list[dict[str, Any]] = []
    th = config.get("thresholds", {})
    for state_id in [x["state_id"] for x in config.get("composite_states", [])]:
        mask = matrix[state_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        for split in SPLITS:
            row = readout_for_state(state_id, split, panel, mask)
            min_n = int(th.get("min_train_treated_n" if split == "train" else "min_eval_treated_n", 500))
            min_pos = int(th.get("min_train_positive_n" if split == "train" else "min_eval_positive_n", 50))
            if row["treated_n"] < min_n or row["treated_positive_n"] < min_pos:
                row["readout_status"] = "insufficient_support"
            rows.append(row)
    return pd.DataFrame(rows)


def block_key_series(frame: pd.DataFrame) -> pd.Series:
    if {"instrument", "reference_date"} <= set(frame.columns):
        month = pd.to_datetime(frame["reference_date"], errors="coerce").dt.to_period("M").astype(str)
        return frame["instrument"].astype(str) + "|" + month
    if "row_id" in frame.columns:
        return frame["row_id"].astype(str)
    return pd.Series(frame.index.astype(str), index=frame.index)


def bootstrap_base_distribution(treated: pd.DataFrame, native_n: int, config: dict[str, Any], seed_key: str) -> tuple[np.ndarray, np.ndarray, str]:
    boot = config.get("bootstrap", {})
    n_resamples = int(boot.get("n_resamples", 300))
    min_valid = int(boot.get("min_valid_replicates", max(1, n_resamples // 2)))
    if treated.empty or native_n <= 0:
        return np.array([], dtype=float), np.array([], dtype=float), "insufficient_ci_fail"
    median_upper = finite_numeric(treated.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(treated.get("lower_barrier", pd.Series(dtype=float))).median())
    if pd.isna(median_upper) or pd.isna(median_lower):
        return np.array([], dtype=float), np.array([], dtype=float), "insufficient_ci_fail"
    component = bool_series(treated.get("upper_first", pd.Series(False, index=treated.index))).astype(float) * median_upper
    component -= bool_series(treated.get("lower_first", pd.Series(False, index=treated.index))).astype(float) * median_lower
    grouped = pd.DataFrame({"block": block_key_series(treated), "component": component, "n": 1}).groupby("block", dropna=False).agg({"component": "sum", "n": "sum"})
    if grouped.empty:
        return np.array([], dtype=float), np.array([], dtype=float), "insufficient_ci_fail"
    seed_base = int(boot.get("seed", 13303))
    seed_offset = int(stable_hash(seed_key)[:8], 16)
    rng = np.random.default_rng(seed_base + seed_offset)
    comp_values = grouped["component"].to_numpy(dtype=float)
    n_values = grouped["n"].to_numpy(dtype=float)
    block_n = len(grouped)
    per_entry: list[float] = []
    coverage: list[float] = []
    for _ in range(n_resamples):
        idx = rng.integers(0, block_n, size=block_n)
        count = float(n_values[idx].sum())
        if count <= 0:
            continue
        per_entry.append(float(comp_values[idx].sum() / count))
        coverage.append(float(count / native_n))
    status = "pass" if len(per_entry) >= min_valid else "insufficient_ci_fail"
    return np.asarray(per_entry, dtype=float), np.asarray(coverage, dtype=float), status


def bootstrap_ci_from_distribution(per_entry: np.ndarray, coverage: np.ndarray, cost: float, config: dict[str, Any]) -> tuple[float, float]:
    if len(per_entry) == 0 or len(coverage) == 0:
        return np.nan, np.nan
    boot = config.get("bootstrap", {})
    q = float(boot.get("ci_low_quantile", 0.05))
    values = (per_entry - cost) * coverage
    return float(np.nanquantile(values, q)), float(np.nanquantile(values, 1.0 - q))


def cost_sensitivity_row_prepared(
    scope_id: str,
    obj_id: str,
    source_phase: str,
    split: str,
    native: pd.DataFrame,
    treated: pd.DataFrame,
    native_n: int,
    cost: float,
    config: dict[str, Any] | None = None,
    bootstrap_distribution: tuple[np.ndarray, np.ndarray, str] | None = None,
) -> dict[str, Any]:
    config = config or {}
    treated_n = len(treated)
    utility = utility_per_entry(treated, cost)
    total = utility * safe_rate(treated_n, native_n) if pd.notna(utility) else np.nan
    lower = safe_rate(bool_series(treated.get("lower_first", pd.Series(dtype=bool))).sum(), treated_n)
    native_lower = safe_rate(bool_series(native.get("lower_first", pd.Series(dtype=bool))).sum(), native_n)
    fast = safe_rate(fast_fail_mask(treated).sum(), treated_n)
    native_fast = safe_rate(fast_fail_mask(native).sum(), native_n)
    if bootstrap_distribution is None:
        bootstrap_distribution = bootstrap_base_distribution(treated, native_n, config, f"{scope_id}|{obj_id}|{source_phase}|{split}")
    boot_per_entry, boot_coverage, ci_status = bootstrap_distribution
    ci_low, ci_high = bootstrap_ci_from_distribution(boot_per_entry, boot_coverage, cost, config)
    return {
        "scope_id": scope_id,
        "filter_id_or_state_id": obj_id,
        "source_phase": source_phase,
        "split_bucket": split,
        "cost_buffer_return": cost,
        "cost_tier_label": cost_label(cost),
        "treated_n": treated_n,
        "treated_positive_n": int(bool_series(treated.get("winner_positive", pd.Series(dtype=bool))).sum()) if treated_n else 0,
        "winner_rate": safe_rate(bool_series(treated.get("winner_positive", pd.Series(dtype=bool))).sum(), treated_n),
        "lower_first_rate": lower,
        "fast_fail_rate": fast,
        "self_utility_proxy_per_entry": utility,
        "self_utility_proxy_total_indexed": total,
        "self_utility_margin_vs_100bps": np.nan,
        "self_utility_positive": bool(pd.notna(utility) and utility > 0),
        "lower_first_uplift_vs_native": lower - native_lower if pd.notna(lower) and pd.notna(native_lower) else np.nan,
        "fast_fail_uplift_vs_native": fast - native_fast if pd.notna(fast) and pd.notna(native_fast) else np.nan,
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "ci_status": ci_status,
    }


def cost_sensitivity_row(
    scope_id: str,
    obj_id: str,
    source_phase: str,
    split: str,
    panel: pd.DataFrame,
    mask: pd.Series,
    cost: float,
    config: dict[str, Any] | None = None,
    bootstrap_distribution: tuple[np.ndarray, np.ndarray, str] | None = None,
) -> dict[str, Any]:
    native = frame_for(panel, split)
    treated = frame_for(panel, split, mask)
    return cost_sensitivity_row_prepared(scope_id, obj_id, source_phase, split, native, treated, len(native), cost, config, bootstrap_distribution)


def build_cost_sensitivity(panel: pd.DataFrame, filter_matrix: pd.DataFrame, state_matrix: pd.DataFrame, filter_dict: pd.DataFrame, dictionary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    costs = load_cost_grid(config)
    fm = filter_matrix.set_index("row_id")
    sm = state_matrix.set_index("row_id")
    split_masks = {split: split_mask(panel, split) for split in SPLITS}
    split_frames = {split: panel.loc[split_masks[split]].copy() for split in SPLITS}
    for filter_id in filter_dict["filter_id"].astype(str).tolist():
        if filter_id not in fm.columns:
            continue
        mask = fm[filter_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        for split in SPLITS:
            native = split_frames[split]
            treated = panel.loc[split_masks[split] & mask]
            native_n = len(native)
            boot_dist = bootstrap_base_distribution(treated, native_n, config, f"all_13a2_candidate_grid|{filter_id}|13A2_filter|{split}")
            for cost in costs:
                rows.append(cost_sensitivity_row_prepared("all_13a2_candidate_grid", filter_id, "13A2_filter", split, native, treated, native_n, cost, config, boot_dist))
    for row in dictionary.itertuples(index=False):
        state_id = str(row.state_id)
        mask = sm[state_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        for split in SPLITS:
            native = split_frames[split]
            treated = panel.loc[split_masks[split] & mask]
            native_n = len(native)
            boot_dist = bootstrap_base_distribution(treated, native_n, config, f"required_repair_state_shortlist|{state_id}|13A3_composite_state|{split}")
            for cost in costs:
                rows.append(cost_sensitivity_row_prepared("required_repair_state_shortlist", state_id, "13A3_composite_state", split, native, treated, native_n, cost, config, boot_dist))
    out = pd.DataFrame(rows)
    ref = (
        out.loc[np.isclose(finite_numeric(out["cost_buffer_return"]), float(config.get("cost_buffer", {}).get("reference_return", 0.01)))]
        .set_index(["scope_id", "filter_id_or_state_id", "source_phase", "split_bucket"])["self_utility_proxy_total_indexed"]
        .to_dict()
    )
    out["self_utility_margin_vs_100bps"] = [
        row.self_utility_proxy_total_indexed - ref.get((row.scope_id, row.filter_id_or_state_id, row.source_phase, row.split_bucket), np.nan)
        for row in out.itertuples(index=False)
    ]
    return out


def strongest_positive_cost(frame: pd.DataFrame) -> float | None:
    pos = frame.loc[finite_numeric(frame["self_utility_proxy_per_entry"]).gt(0)].copy()
    if pos.empty:
        return None
    return float(pos["cost_buffer_return"].max())


def build_cost_turning_points(cost_audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = cost_audit.groupby(["filter_id_or_state_id", "source_phase"], dropna=False)
    for (obj_id, source_phase), frame in grouped:
        summary: dict[str, Any] = {"filter_id_or_state_id": obj_id, "source_phase": source_phase}
        for split in ("validation", "robustness"):
            cost = strongest_positive_cost(frame.loc[frame["split_bucket"].eq(split)])
            summary[f"first_cost_tier_with_{split}_self_utility_positive"] = "" if cost is None else cost_label(cost)
        both_cost = None
        for cost in sorted(finite_numeric(frame["cost_buffer_return"]).dropna().unique(), reverse=True):
            vals = frame.loc[np.isclose(finite_numeric(frame["cost_buffer_return"]), cost) & frame["split_bucket"].isin(["validation", "robustness"])]
            if len(vals) == 2 and vals["self_utility_positive"].astype(bool).all():
                both_cost = float(cost)
                break
        summary["first_cost_tier_with_both_validation_and_robustness_self_utility_positive"] = "" if both_cost is None else cost_label(both_cost)
        for cost in [0.0, 0.0025, 0.005, 0.0075, 0.01]:
            vals = frame.loc[np.isclose(finite_numeric(frame["cost_buffer_return"]), cost) & frame["split_bucket"].isin(["validation", "robustness"])]
            summary[f"self_utility_positive_at_{cost_label(cost)}"] = bool(len(vals) == 2 and vals["self_utility_positive"].astype(bool).all())
        if summary["self_utility_positive_at_100bps"]:
            status = "cost_robust_100bps"
        elif summary["self_utility_positive_at_50bps"]:
            status = "cost_viable_50bps"
        elif summary["self_utility_positive_at_25bps"]:
            status = "cost_fragile_25bps_only"
        elif summary["self_utility_positive_at_0bps"]:
            status = "cost_fragile_0bps_only"
        else:
            status = "no_economic_amplitude"
        summary["cost_sensitivity_status"] = status
        rows.append(summary)
    return pd.DataFrame(rows)


def badside_utility_row(state_id: str, split: str, panel: pd.DataFrame, state_mask: pd.Series, base_mask: pd.Series, cost: float) -> dict[str, Any]:
    native = frame_for(panel, split)
    treated = frame_for(panel, split, state_mask)
    base = frame_for(panel, split, base_mask)
    native_n = len(native)
    treated_n = len(treated)
    base_n = len(base)
    lower = safe_rate(bool_series(treated.get("lower_first", pd.Series(dtype=bool))).sum(), treated_n)
    native_lower = safe_rate(bool_series(native.get("lower_first", pd.Series(dtype=bool))).sum(), native_n)
    base_lower = safe_rate(bool_series(base.get("lower_first", pd.Series(dtype=bool))).sum(), base_n)
    fast = safe_rate(fast_fail_mask(treated).sum(), treated_n)
    native_fast = safe_rate(fast_fail_mask(native).sum(), native_n)
    base_fast = safe_rate(fast_fail_mask(base).sum(), base_n)
    utility = utility_per_entry(treated, cost)
    total = utility * safe_rate(treated_n, native_n) if pd.notna(utility) else np.nan
    native_total = utility_per_entry(native, cost)
    base_total = utility_per_entry(base, cost) * safe_rate(base_n, native_n) if base_n else np.nan
    lower_vs_base = lower - base_lower if pd.notna(lower) and pd.notna(base_lower) else np.nan
    fast_vs_base = fast - base_fast if pd.notna(fast) and pd.notna(base_fast) else np.nan
    lower_vs_native = lower - native_lower if pd.notna(lower) and pd.notna(native_lower) else np.nan
    fast_vs_native = fast - native_fast if pd.notna(fast) and pd.notna(native_fast) else np.nan
    badside = (
        "pass"
        if pd.notna(lower_vs_base)
        and lower_vs_base <= 0
        and pd.notna(fast_vs_base)
        and fast_vs_base <= 0.01
        else "fail"
    )
    margin_native = total - native_total if pd.notna(total) and pd.notna(native_total) else np.nan
    margin_base = total - base_total if pd.notna(total) and pd.notna(base_total) else np.nan
    return {
        "state_id": state_id,
        "split_bucket": split,
        "cost_buffer_return": cost,
        "cost_tier_label": cost_label(cost),
        "treated_n": treated_n,
        "upper_first_rate": safe_rate(bool_series(treated.get("upper_first", pd.Series(dtype=bool))).sum(), treated_n),
        "lower_first_rate": lower,
        "fast_fail_rate": fast,
        "native_upper_first_rate": safe_rate(bool_series(native.get("upper_first", pd.Series(dtype=bool))).sum(), native_n),
        "native_lower_first_rate": native_lower,
        "native_fast_fail_rate": native_fast,
        "compression_base_lower_first_rate": base_lower,
        "compression_base_fast_fail_rate": base_fast,
        "lower_first_uplift_vs_native": lower_vs_native,
        "fast_fail_uplift_vs_native": fast_vs_native,
        "lower_first_uplift_vs_compression_base": lower_vs_base,
        "fast_fail_uplift_vs_compression_base": fast_vs_base,
        "median_upper_barrier_return": finite_numeric(treated.get("upper_barrier", pd.Series(dtype=float))).median(),
        "median_abs_lower_barrier_return": abs(finite_numeric(treated.get("lower_barrier", pd.Series(dtype=float))).median()),
        "utility_proxy_per_entry": utility,
        "utility_proxy_total_indexed": total,
        "utility_margin_vs_native": margin_native,
        "utility_margin_vs_compression_base": margin_base,
        "utility_status": "utility_pass" if pd.notna(utility) and utility > 0 and pd.notna(margin_native) and margin_native > 0 else "utility_fail",
        "badside_status": badside,
    }


def build_badside_utility(panel: pd.DataFrame, state_matrix: pd.DataFrame, base_mask: pd.Series, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sm = state_matrix.set_index("row_id")
    for state_id in [x["state_id"] for x in config.get("composite_states", [])]:
        mask = sm[state_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        for split in SPLITS:
            for cost in load_cost_grid(config):
                rows.append(badside_utility_row(state_id, split, panel, mask, base_mask, cost))
    return pd.DataFrame(rows)


def drift_status_for_axis(axis: str, max_native: float, max_complement: float, config: dict[str, Any]) -> str:
    th = config.get("thresholds", {})
    if axis == "board":
        if pd.notna(max_native) and max_native > float(th.get("board_extreme_drift_vs_native", 0.35)):
            return "fail_extreme_drift"
        if max_native <= float(th.get("board_primary_drift_vs_native", 0.20)) and max_complement <= float(th.get("board_primary_drift_vs_complement", 0.25)):
            return "primary_pass"
        return "caveat_relative_drift"
    if axis == "year":
        if pd.notna(max_native) and max_native > float(th.get("year_extreme_drift_vs_native", 0.30)):
            return "fail_extreme_drift"
        if max_native <= float(th.get("year_primary_drift_vs_native", 0.15)):
            return "primary_pass"
        return "caveat_relative_drift"
    return "primary_pass"


def build_denominator_drift(panel: pd.DataFrame, state_matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sm = state_matrix.set_index("row_id")
    th = config.get("thresholds", {})
    for state_id in [x["state_id"] for x in config.get("composite_states", [])]:
        mask = sm[state_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        for split in SPLITS:
            native_mask = split_mask(panel, split)
            treated_mask = native_mask & mask
            complement_mask = native_mask & ~mask
            for axis, col in [("board", "board_bucket"), ("year", "calendar_year"), ("regime", "market_regime_bucket")]:
                native_counts = panel.loc[native_mask, col].astype(str).value_counts(normalize=True)
                treated_counts = panel.loc[treated_mask, col].astype(str).value_counts(normalize=True)
                complement_counts = panel.loc[complement_mask, col].astype(str).value_counts(normalize=True)
                buckets = sorted(set(native_counts.index) | set(treated_counts.index) | set(complement_counts.index))
                max_native = max([abs(float(treated_counts.get(b, 0.0)) - float(native_counts.get(b, 0.0))) for b in buckets] or [np.nan])
                max_complement = max([abs(float(treated_counts.get(b, 0.0)) - float(complement_counts.get(b, 0.0))) for b in buckets] or [np.nan])
                status = "regime_single_bucket_caveat" if axis == "regime" and len([b for b in buckets if float(treated_counts.get(b, 0.0)) > 0]) < 2 else drift_status_for_axis(axis, max_native, max_complement, config)
                for b in buckets:
                    rows.append(
                        {
                            "state_id": state_id,
                            "split_bucket": split,
                            "drift_axis": axis,
                            "bucket_id": b,
                            "treated_n": int(treated_mask.sum()),
                            "treated_share": float(treated_counts.get(b, 0.0)),
                            "native_share": float(native_counts.get(b, 0.0)),
                            "complement_share": float(complement_counts.get(b, 0.0)),
                            "treated_minus_native_share": float(treated_counts.get(b, 0.0)) - float(native_counts.get(b, 0.0)),
                            "treated_minus_complement_share": float(treated_counts.get(b, 0.0)) - float(complement_counts.get(b, 0.0)),
                            "drift_status": status,
                        }
                    )
            for axis, col, primary_min, primary_max, extreme_min, extreme_max in [
                ("liquidity", "money_median_20d", th.get("liquidity_primary_ratio_min", 0.5), th.get("liquidity_primary_ratio_max", 2.0), th.get("liquidity_extreme_ratio_min", 0.25), th.get("liquidity_extreme_ratio_max", 4.0)),
                ("compression_severity", "volatility_20d", th.get("compression_primary_ratio_min", 0.5), th.get("compression_primary_ratio_max", 1.5), 0.0, np.inf),
            ]:
                treated_med = finite_numeric(panel.loc[treated_mask, col]).median()
                native_med = finite_numeric(panel.loc[native_mask, col]).median()
                complement_med = finite_numeric(panel.loc[complement_mask, col]).median()
                ratio_native = treated_med / native_med if native_med and pd.notna(native_med) else np.nan
                ratio_comp = treated_med / complement_med if complement_med and pd.notna(complement_med) else np.nan
                if pd.notna(ratio_native) and (ratio_native < float(extreme_min) or ratio_native > float(extreme_max)):
                    status = "fail_extreme_drift"
                elif pd.notna(ratio_native) and float(primary_min) <= ratio_native <= float(primary_max):
                    status = "primary_pass"
                else:
                    status = "caveat_relative_drift"
                rows.append(
                    {
                        "state_id": state_id,
                        "split_bucket": split,
                        "drift_axis": axis,
                        "bucket_id": "median_ratio",
                        "treated_n": int(treated_mask.sum()),
                        "treated_share": ratio_native,
                        "native_share": 1.0,
                        "complement_share": ratio_comp,
                        "treated_minus_native_share": ratio_native - 1.0 if pd.notna(ratio_native) else np.nan,
                        "treated_minus_complement_share": ratio_native - ratio_comp if pd.notna(ratio_native) and pd.notna(ratio_comp) else np.nan,
                        "drift_status": status,
                    }
                )
    return pd.DataFrame(rows)


def anchor_token_columns(native_token_matrix: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in native_token_matrix.columns:
        if any(str(col).startswith(f"{anchor}__") for anchor in ANCHOR_PRIMITIVES):
            cols.append(str(col))
    return cols


def build_morphology_audit(panel: pd.DataFrame, state_matrix: pd.DataFrame, native_token_matrix: pd.DataFrame, base_mask: pd.Series, dictionary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sm = state_matrix.set_index("row_id")
    tm = native_token_matrix.set_index("row_id")
    anchors = anchor_token_columns(native_token_matrix)
    dict_lookup = dictionary.set_index("state_id").to_dict(orient="index")
    for state_id in [x["state_id"] for x in config.get("composite_states", [])]:
        mask = sm[state_id].reindex(panel["row_id"]).fillna(False).astype(bool)
        mask.index = panel.index
        meta = dict_lookup[state_id]
        for split in SPLITS:
            native_mask = split_mask(panel, split)
            native = panel.loc[native_mask]
            state_auc = auc_score(mask.loc[native.index].astype(float), native["winner_positive"]) if len(native) else np.nan
            corr_vals: dict[str, float] = {}
            for anchor in ANCHOR_PRIMITIVES:
                corr_vals[anchor] = mask.loc[native.index].astype(float).corr(finite_numeric(native.get(anchor, pd.Series(np.nan, index=native.index))), method="spearman") if len(native) else np.nan
            top_anchor = max(corr_vals, key=lambda k: abs(corr_vals[k]) if pd.notna(corr_vals[k]) else -1)
            max_corr = abs(corr_vals[top_anchor]) if pd.notna(corr_vals[top_anchor]) else np.nan
            for cost in load_cost_grid(config):
                native_n = int(native_mask.sum())
                state_total = utility_total_indexed(panel.loc[native_mask & mask], native_n, cost)
                base_total = utility_total_indexed(panel.loc[native_mask & base_mask], native_n, cost)
                broad_auc = np.nan
                broad_utility = np.nan
                for col in anchors:
                    anchor_mask = tm[col].reindex(panel["row_id"]).fillna(False).astype(bool)
                    anchor_mask.index = panel.index
                    if native_n:
                        auc = auc_score(anchor_mask.loc[native.index].astype(float), native["winner_positive"])
                        total = utility_total_indexed(panel.loc[native_mask & anchor_mask], native_n, cost)
                        if pd.isna(broad_auc) or (pd.notna(auc) and auc > broad_auc):
                            broad_auc = auc
                        if pd.isna(broad_utility) or (pd.notna(total) and total > broad_utility):
                            broad_utility = total
                margin_broad = state_total - broad_utility if pd.notna(state_total) and pd.notna(broad_utility) else np.nan
                margin_base = state_total - base_total if pd.notna(state_total) and pd.notna(base_total) else np.nan
                rows.append(
                    {
                        "state_id": state_id,
                        "split_bucket": split,
                        "cost_buffer_return": cost,
                        "cost_tier_label": cost_label(cost),
                        "morphology_risk": meta["morphology_risk"],
                        "max_abs_rank_corr_with_anchor": max_corr,
                        "top_anchor_id": top_anchor,
                        "state_auc": state_auc,
                        "broad_morphology_baseline_auc": broad_auc,
                        "auc_margin_vs_broad": state_auc - broad_auc if pd.notna(state_auc) and pd.notna(broad_auc) else np.nan,
                        "state_utility_total_indexed": state_total,
                        "broad_morphology_utility_total_indexed": broad_utility,
                        "utility_margin_vs_broad": margin_broad,
                        "compression_base_utility_total_indexed": base_total,
                        "utility_margin_vs_compression_base": margin_base,
                        "independent_evidence_status": "pass" if pd.notna(margin_broad) and margin_broad > 0 and pd.notna(margin_base) and margin_base > 0 else "morphology_rediscovery_without_independent_utility",
                    }
                )
    return pd.DataFrame(rows)


def build_search_audit(config: dict[str, Any]) -> pd.DataFrame:
    state_n = len(config.get("composite_states", []))
    cost_n = len(load_cost_grid(config))
    return pd.DataFrame(
        [
            {
                "composite_state_n": state_n,
                "cost_grid_n": cost_n,
                "effective_search_space_n": state_n * cost_n,
                "posthoc_shortlist_from_13a2_report": True,
                "validation_used_for_shortlist": True,
                "robustness_used_for_shortlist": True,
                "validation_used_for_final_selection": False,
                "robustness_used_for_final_selection": False,
                "state_priority_policy": "pre_registered_in_requirement_13a3",
                "cost_tier_policy": "100bps_gt_75bps_gt_50bps_gt_25bps_gt_0bps",
                "train_selection_rule": "train_support_winner_badside_self_utility_then_priority",
                "fdr_or_deflation_method": "diagnostic_posthoc_accounting_no_confirmatory_pvalue",
                "search_accounting_status": "diagnostic_posthoc_not_confirmatory",
            }
        ]
    )


def route_cost_rows(badside: pd.DataFrame, state_id: str, cost: float) -> pd.DataFrame:
    return badside.loc[badside["state_id"].eq(state_id) & np.isclose(finite_numeric(badside["cost_buffer_return"]), cost)]


def route_morph_rows(morphology: pd.DataFrame, state_id: str, cost: float) -> pd.DataFrame:
    return morphology.loc[morphology["state_id"].eq(state_id) & np.isclose(finite_numeric(morphology["cost_buffer_return"]), cost)]


def eval_splits_pass(rows: pd.DataFrame, col: str, pass_value: str = "pass") -> bool:
    sub = rows.loc[rows["split_bucket"].isin(["validation", "robustness"])]
    return len(sub) == 2 and sub[col].astype(str).eq(pass_value).all()


def utility_route_pass(badside: pd.DataFrame, state_id: str, cost: float, require_margin: bool = True) -> bool:
    rows = route_cost_rows(badside, state_id, cost)
    sub = rows.loc[rows["split_bucket"].isin(["validation", "robustness"])]
    if len(sub) != 2:
        return False
    ok = finite_numeric(sub["utility_proxy_per_entry"]).gt(0).all()
    if require_margin:
        ok = ok and finite_numeric(sub["utility_margin_vs_native"]).gt(0).all()
    return bool(ok)


def morphology_route_pass(morphology: pd.DataFrame, state_id: str, cost: float) -> bool:
    rows = route_morph_rows(morphology, state_id, cost)
    sub = rows.loc[rows["split_bucket"].isin(["validation", "robustness"])]
    return len(sub) == 2 and sub["independent_evidence_status"].astype(str).eq("pass").all()


def readout_route_pass(readout: pd.DataFrame, state_id: str, config: dict[str, Any]) -> bool:
    th = config.get("thresholds", {})
    sub = readout.loc[readout["state_id"].eq(state_id) & readout["split_bucket"].isin(["validation", "robustness"])]
    if len(sub) != 2:
        return False
    return bool(
        finite_numeric(sub["treated_n"]).ge(float(th.get("min_eval_treated_n", 500))).all()
        and finite_numeric(sub["treated_positive_n"]).ge(float(th.get("min_eval_positive_n", 50))).all()
        and finite_numeric(sub["winner_rate_diff_vs_native"]).gt(0).all()
    )


def badside_route_pass(badside: pd.DataFrame, state_id: str, cost: float) -> bool:
    return eval_splits_pass(route_cost_rows(badside, state_id, cost), "badside_status", "pass")


def selected_has_extreme_drift(drift: pd.DataFrame, state_id: str) -> bool:
    return bool(drift.loc[drift["state_id"].eq(state_id), "drift_status"].astype(str).eq("fail_extreme_drift").any())


def select_train_state(readout: pd.DataFrame, badside: pd.DataFrame, dictionary: pd.DataFrame, config: dict[str, Any]) -> tuple[str, float | None]:
    th = config.get("thresholds", {})
    rows: list[dict[str, Any]] = []
    for d in dictionary.sort_values("state_priority").itertuples(index=False):
        state_id = str(d.state_id)
        r = readout.loc[readout["state_id"].eq(state_id) & readout["split_bucket"].eq("train")]
        if r.empty:
            continue
        rr = r.iloc[0]
        if not (
            int(rr["treated_n"]) >= int(th.get("min_train_treated_n", 1000))
            and int(rr["treated_positive_n"]) >= int(th.get("min_train_positive_n", 100))
            and float(rr["winner_rate_diff_vs_native"]) > 0
        ):
            continue
        bs = badside.loc[badside["state_id"].eq(state_id) & badside["split_bucket"].eq("train")]
        bs = bs.loc[finite_numeric(bs["lower_first_uplift_vs_compression_base"]).le(0)]
        bs = bs.loc[finite_numeric(bs["utility_proxy_per_entry"]).gt(0)]
        if bs.empty:
            continue
        best = bs.sort_values(["cost_buffer_return", "utility_proxy_per_entry"], ascending=[False, False]).iloc[0]
        rows.append(
            {
                "state_id": state_id,
                "cost": float(best["cost_buffer_return"]),
                "train_utility": float(best["utility_proxy_per_entry"]),
                "train_lower": float(best["lower_first_uplift_vs_compression_base"]),
                "priority": int(d.state_priority),
            }
        )
    if not rows:
        return "", None
    selected = sorted(rows, key=lambda x: (-x["cost"], -x["train_utility"], x["train_lower"], x["priority"]))[0]
    return str(selected["state_id"]), float(selected["cost"])


def build_decision(
    input_status: str,
    upstream_13a_status: str,
    upstream_13a2_status: str,
    upstream_13a2_reason: str,
    label_status: str,
    cost_lineage_status: str,
    cache_status: str,
    composite_status: str,
    composite_reason: str,
    cost_summary: pd.DataFrame,
    readout: pd.DataFrame,
    badside: pd.DataFrame,
    drift: pd.DataFrame,
    morphology: pd.DataFrame,
    dictionary: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    required_summary = cost_summary.loc[cost_summary["filter_id_or_state_id"].isin(dictionary["state_id"].astype(str))]
    any_cost_amp = required_summary["cost_sensitivity_status"].isin(["cost_fragile_25bps_only", "cost_viable_50bps", "cost_robust_100bps"]).any()
    selected_state, selected_train_cost = select_train_state(readout, badside, dictionary, config)
    ref_cost = float(config.get("cost_buffer", {}).get("reference_return", 0.01))
    mid_cost = float(config.get("cost_buffer", {}).get("moderate_return", 0.005))
    selected_100_utility = utility_route_pass(badside, selected_state, ref_cost) if selected_state else False
    selected_50_utility = utility_route_pass(badside, selected_state, mid_cost) if selected_state else False
    selected_25_utility = utility_route_pass(badside, selected_state, 0.0025, require_margin=False) if selected_state else False
    selected_readout = readout_route_pass(readout, selected_state, config) if selected_state else False
    selected_bad_100 = badside_route_pass(badside, selected_state, ref_cost) if selected_state else False
    selected_bad_50 = badside_route_pass(badside, selected_state, mid_cost) if selected_state else False
    selected_morph_100 = morphology_route_pass(morphology, selected_state, ref_cost) if selected_state else False
    selected_morph_50 = morphology_route_pass(morphology, selected_state, mid_cost) if selected_state else False
    extreme = selected_has_extreme_drift(drift, selected_state) if selected_state else False
    state = "13A3_selected_composite_state_not_supported"
    next_req = "none"
    reason = "one_or_more_final_gates_failed"
    if input_status != "pass":
        state = "13A3_blocked_input_or_lineage_failure"
        reason = "input_schema_or_path_failure"
    elif upstream_13a_status != "pass":
        state = "13A3_blocked_upstream_13a_lineage_failure"
        reason = "upstream_13a_lineage_failure"
    elif "already_authorized" in str(upstream_13a2_reason):
        state = "13A3_blocked_upstream_13a2_already_authorized"
        reason = "upstream_13a2_already_authorized"
    elif upstream_13a2_status != "pass":
        state = "13A3_blocked_upstream_13a2_lineage_failure"
        reason = "upstream_13a2_lineage_failure"
    elif label_status != "pass":
        state = "13A3_blocked_label_lineage_failure"
        reason = "label_lineage_failure"
    elif cost_lineage_status != "pass":
        state = "13A3_blocked_input_or_lineage_failure"
        reason = "cost_buffer_lineage_failure"
    elif cache_status != "pass":
        state = "13A3_blocked_input_or_lineage_failure"
        reason = "row_level_cache_validation_failure"
    elif composite_status != "pass":
        if "threshold" in str(composite_reason) or "missing" in str(composite_reason):
            state = "13A3_blocked_required_composite_threshold_missing"
            reason = "required_composite_threshold_missing"
        else:
            state = "13A3_blocked_composite_state_reproduction_failure"
            reason = "composite_state_reproduction_failure"
    elif not any_cost_amp:
        state = "13A3_stop_cost_sensitivity_no_economic_amplitude"
        reason = "cost_sensitivity_no_actionable_economic_amplitude"
    elif not selected_state:
        state = "13A3_no_train_composite_state_survives"
        reason = "no_train_eligible_composite_state"
    elif selected_100_utility and selected_readout and selected_bad_100 and not selected_morph_100:
        state = "13A3_stop_morphology_rediscovery_without_independent_utility"
        reason = "reference_cost_utility_pass_but_morphology_independent_evidence_failed"
    elif selected_50_utility and selected_readout and selected_bad_50 and not selected_morph_50:
        state = "13A3_stop_morphology_rediscovery_without_independent_utility"
        reason = "cost_caveat_utility_pass_but_morphology_independent_evidence_failed"
    elif (selected_100_utility or selected_50_utility) and extreme:
        state = "13A3_stop_extreme_denominator_drift"
        reason = "extreme_denominator_drift"
    elif selected_100_utility and selected_readout and selected_bad_100 and selected_morph_100 and not extreme:
        state = "13A3_reference_cost_repair_state_diagnostic_supported_requires_confirmatory_preflight"
        next_req = "requirement_13a4_compression_repair_state_confirmatory_preflight.md"
        reason = "reference_cost_total_native_effect_supported_requires_confirmatory_preflight"
    elif selected_50_utility and selected_readout and selected_bad_50 and selected_morph_50 and not extreme:
        state = "13A3_cost_caveat_repair_state_supported_requires_cost_model_calibration"
        next_req = "requirement_13a4_cost_model_calibration_for_compression_repair_state.md"
        reason = "50bps_total_native_effect_supported_requires_cost_model_calibration"
    elif selected_25_utility:
        state = "13A3_diagnostic_only_cost_too_fragile"
        reason = "only_25bps_self_utility_positive"
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "next_allowed_requirement": next_req,
                "sequence_mining_authorized": False,
                "selected_state_id": selected_state,
                "selected_state_cost_status": "" if selected_train_cost is None else cost_label(selected_train_cost),
                "selected_state_reference_cost_pass": selected_100_utility and selected_bad_100 and selected_morph_100,
                "selected_state_50bps_cost_pass": selected_50_utility and selected_bad_50 and selected_morph_50,
                "confirmatory_status": False,
                "shortlist_source": "post_13A2_diagnostic_report",
                "effect_interpretation": "total_native_effect_only",
                "distribution_vs_state_edge_disentanglement_required": True if selected_state else False,
                "badside_primary_baseline": "compression_base",
                "input_gate_status": input_status,
                "upstream_13a_lineage_gate_status": upstream_13a_status,
                "upstream_13a2_lineage_gate_status": upstream_13a2_status,
                "cost_sensitivity_gate_status": "pass" if any_cost_amp else "fail",
                "composite_readout_gate_status": "pass" if selected_readout else "fail",
                "badside_gate_status": "pass" if (selected_bad_100 or selected_bad_50) else "fail",
                "utility_gate_status": "pass" if (selected_100_utility or selected_50_utility) else "fail",
                "denominator_drift_gate_status": "fail" if extreme else "pass",
                "morphology_independent_evidence_gate_status": "pass" if (selected_morph_100 or selected_morph_50) else "fail",
                "search_accounting_status": "diagnostic_posthoc_not_confirmatory",
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
    cost_summary: pd.DataFrame,
    readout: pd.DataFrame,
    badside: pd.DataFrame,
    drift: pd.DataFrame,
    morphology: pd.DataFrame,
    dictionary: pd.DataFrame,
    label_lineage: pd.DataFrame,
    cost_lineage: pd.DataFrame,
    cache_audit: pd.DataFrame,
) -> str:
    dec = decision.iloc[0]
    selected = str(dec.get("selected_state_id", ""))
    required_summary = cost_summary.loc[cost_summary["filter_id_or_state_id"].isin(dictionary["state_id"].astype(str))].copy()
    selected_readout = readout.loc[readout["state_id"].astype(str).eq(selected)].copy()
    selected_badside = badside.loc[badside["state_id"].astype(str).eq(selected)].copy()
    selected_morphology = morphology.loc[morphology["state_id"].astype(str).eq(selected)].copy()
    selected_drift = drift.loc[drift["state_id"].astype(str).eq(selected)].copy()
    fragile_n = int(required_summary["cost_sensitivity_status"].astype(str).eq("cost_fragile_25bps_only").sum()) if len(required_summary) else 0
    viable50_n = int(required_summary["cost_sensitivity_status"].astype(str).eq("cost_viable_50bps").sum()) if len(required_summary) else 0
    robust100_n = int(required_summary["cost_sensitivity_status"].astype(str).eq("cost_robust_100bps").sum()) if len(required_summary) else 0
    no_amp_n = int(required_summary["cost_sensitivity_status"].astype(str).eq("no_economic_amplitude").sum()) if len(required_summary) else 0
    cache_fail_n = int(cache_audit["cache_status"].astype(str).eq("fail").sum()) if len(cache_audit) and "cache_status" in cache_audit else 0
    label_fail_n = int(label_lineage["lineage_status"].astype(str).eq("fail").sum()) if len(label_lineage) else 0
    cost_fail_n = int(cost_lineage["lineage_status"].astype(str).eq("fail").sum()) if len(cost_lineage) else 0
    selected_50_100 = selected_badside.loc[selected_badside["cost_buffer_return"].isin([0.005, 0.01])]
    selected_all_cost = selected_badside.loc[selected_badside["split_bucket"].isin(["validation", "robustness"])].sort_values(["split_bucket", "cost_buffer_return"])
    drift_caveat = selected_drift.loc[selected_drift["drift_status"].astype(str).ne("primary_pass")]
    morph_route = selected_morphology.loc[selected_morphology["cost_buffer_return"].isin([0.005, 0.01])]
    lines = [
        "# 13A3 Compression Repair-State Cost and Native Feasibility Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"- `decision_state`: `{dec['decision_state']}`",
        f"- `selected_state_id`: `{selected or 'none'}`",
        f"- `sequence_mining_authorized`: `{boolish(dec['sequence_mining_authorized'])}`",
        f"- `next_allowed_requirement`: `{dec['next_allowed_requirement']}`",
        f"- `primary_failure_reason`: `{dec['primary_failure_reason']}`",
        "",
        "13A3 使用 13A2 报告后的 diagnostic shortlist，因此本轮只评估 `total_native_effect`，不把正读数解释为已经证明 `pure_conditional_state_edge`。本轮仍不授权 13B sequence mining。",
        "",
        "## Lineage / Cache Gate",
        "",
        f"- label lineage fail count: `{label_fail_n}`",
        f"- cost lineage fail count: `{cost_fail_n}`",
        f"- row-level cache fail count: `{cache_fail_n}`",
        "",
        md_table(label_lineage, ["lineage_check_id", "observed_value", "expected_value", "lineage_status"], 12),
        "",
        md_table(cost_lineage, ["lineage_check_id", "upstream_cost_buffer_return", "upstream_cost_buffer_source", "reference_cost_buffer_return", "lineage_status"], 8),
        "",
        "## Composite State Dictionary",
        "",
        md_table(dictionary, ["state_id", "state_priority", "source_13a2_filter_id", "component_family", "directional_component_class", "morphology_risk", "state_reproduction_status"], 10),
        "",
        "## Cost Sensitivity",
        "",
        f"required composite shortlist 中 `{robust100_n}` 个 state 在 100bps 下 validation/robustness 同时 self-utility 为正，`{viable50_n}` 个达到 50bps，`{fragile_n}` 个只达到 25bps，`{no_amp_n}` 个即使降到 0bps 仍没有双 split 正 self-utility。因此，本轮没有证明“13A2 主要死于 100bps cost buffer”；更准确的读法是：多数 repair state 的经济幅度不足，少数 morphology-suspect state 只有低成本脆弱读数。",
        "",
        md_table(cost_summary.loc[cost_summary["filter_id_or_state_id"].isin(dictionary["state_id"].astype(str))], ["filter_id_or_state_id", "source_phase", "first_cost_tier_with_both_validation_and_robustness_self_utility_positive", "self_utility_positive_at_50bps", "self_utility_positive_at_100bps", "cost_sensitivity_status"], 20),
        "",
        "## Full-Native Readout",
        "",
        "Full-native frame 把 composite state 当成完整 native event，与 full PIT native denominator 比较。它回答的是“这个完整状态的总效应是否可用”，不同于 13A2 的 compression-control frame，后者回答“在已经 compression 的样本内，方向 filter 是否有纯增量”。因此 full-native 正读数可能混合 state edge 与 board/liquidity/calendar/compression severity 分布迁移。",
        "",
        md_table(selected_readout if selected else readout, ["state_id", "split_bucket", "treated_n", "treated_positive_n", "coverage_share", "captured_positive_share", "treated_winner_rate", "native_winner_rate", "winner_rate_diff_vs_native", "treated_lower_first_rate", "native_lower_first_rate", "lower_first_uplift_vs_native", "treated_fast_fail_rate", "native_fast_fail_rate", "fast_fail_uplift_vs_native", "readout_status"], 30),
        "",
        "## Bad-side / Utility",
        "",
        "Bad-side primary gate 使用 `vs_compression_base`：repair state 继承 compression base，所以首要问题是它是否降低或至少不放大 compression 的左尾风险。`vs_native` 继续报告，但只作为 total-effect caveat。Utility gate 仍要求同一 cost tier 下 `utility_proxy_per_entry > 0` 且 `utility_margin_vs_native > 0`。",
        "",
        md_table(selected_all_cost if selected else badside.loc[badside["cost_buffer_return"].isin([0.005, 0.01])], ["state_id", "split_bucket", "cost_tier_label", "lower_first_uplift_vs_compression_base", "fast_fail_uplift_vs_compression_base", "utility_proxy_per_entry", "utility_margin_vs_native", "utility_margin_vs_compression_base", "badside_status", "utility_status"], 40),
        "",
        "## Denominator Drift",
        "",
        "Denominator drift audit 只暴露分母迁移，不能证明已经剥离分布效应。若 13A3 出现 positive route，下一份 confirmatory preflight 必须用预注册 stratification / weighting / matched-denominator diagnostics 分离 distribution effect 与 conditional state edge。",
        "",
        md_table(drift_caveat if selected else drift.loc[drift["drift_status"].astype(str).ne("primary_pass")], ["state_id", "split_bucket", "drift_axis", "bucket_id", "treated_share", "native_share", "complement_share", "treated_minus_native_share", "drift_status"], 40),
        "",
        "## Morphology Independent Evidence",
        "",
        "Morphology gate 不接受 AUC margin 单独通过；必须在 route cost tier 下同时优于 broad morphology baseline 和 compression base 的 utility total indexed。若 robustness split 对 broad morphology margin 为负，即判为 morphology rediscovery without independent utility。",
        "",
        md_table(morph_route if selected else morphology.loc[morphology["cost_buffer_return"].isin([0.005, 0.01])], ["state_id", "split_bucket", "cost_tier_label", "morphology_risk", "top_anchor_id", "state_auc", "broad_morphology_baseline_auc", "utility_margin_vs_broad", "utility_margin_vs_compression_base", "independent_evidence_status"], 40),
        "",
        "## Findings",
        "",
        "- `self_utility_*` 只用于 cost sensitivity，不能替代相对 native / compression base 的 utility margin。",
        "- 本轮 selected state 的 winner uplift 在 full-native frame 中为正，但 utility route 没有通过；因此正 winner 读数不足以支持下一步 sequence mining。",
        "- 当前停止原因需要优先读成 signal amplitude / cost fragility / morphology independence 的组合问题，而不是单纯 100bps 参数过严。",
        "- 若未来出现 50bps positive，只能进入 cost model calibration；若出现 100bps positive，也只能进入 confirmatory preflight，并且必须显式分离 distribution effect 与 state edge。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if "local_cache" not in path.parts and key != "manifest"}


def schema_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        suffixes = "".join(path.suffixes)
        if suffixes.endswith(".parquet"):
            frame = pd.read_parquet(path).head(0)
        elif suffixes.endswith((".csv", ".csv.gz")):
            frame = pd.read_csv(path, nrows=0)
        else:
            return ""
        return stable_hash({"columns": frame.columns.tolist(), "dtypes": {col: str(dtype) for col, dtype in frame.dtypes.items()}})
    except Exception:
        return ""


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
    if not check_inputs_only:
        ensure_upstream_outputs(resolved, mode)
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, _input_reason = input_gate_status(input_audit)
    a_lineage, a_status, _a_reason, base_threshold = upstream_13a_lineage_audit(resolved)
    a2_lineage, a2_status, a2_reason = upstream_13a2_lineage_audit(resolved)
    label_lineage = build_label_lineage_audit(resolved)
    label_status, _label_reason = table_status(label_lineage, "lineage_status")
    cost_lineage = build_cost_buffer_lineage_audit(config, resolved)
    cost_lineage_status, _cost_lineage_reason = table_status(cost_lineage, "lineage_status")
    write_df(outputs["upstream_13a_lineage_audit"], a_lineage)
    write_df(outputs["upstream_13a2_lineage_audit"], a2_lineage)
    write_df(outputs["label_lineage_audit"], label_lineage)
    write_df(outputs["cost_buffer_lineage_audit"], cost_lineage)
    if check_inputs_only or mode == "check-inputs":
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
        return outputs

    native_panel = read_table(resolved["upstream_13a_native_universe_cache"])
    filter_matrix = read_table(resolved["upstream_13a2_directional_filter_matrix_cache"])
    native_token_matrix = read_table(resolved["upstream_13a_native_token_matrix_cache"])
    base_panel = read_table(resolved["upstream_13a2_compression_base_cache"])
    base_ids = set(base_panel["row_id"].tolist())
    base_mask = native_panel["row_id"].isin(base_ids)
    dictionary, composite_status, _comp_reason = build_composite_dictionary(config, resolved, base_threshold)
    state_matrix = build_composite_state_matrix(native_panel, filter_matrix, dictionary)
    filter_dict = read_table(resolved["upstream_13a2_filter_dictionary"])
    cache_audit = build_row_level_cache_audit(native_panel, filter_matrix, native_token_matrix, base_panel, dictionary, base_threshold, resolved)
    cache_status, _cache_reason = table_status(cache_audit, "cache_status")

    cost_audit = build_cost_sensitivity(native_panel, filter_matrix, state_matrix, filter_dict, dictionary, config)
    cost_summary = build_cost_turning_points(cost_audit)
    readout = build_composite_native_readout(native_panel, state_matrix, config)
    badside = build_badside_utility(native_panel, state_matrix, base_mask, config)
    drift = build_denominator_drift(native_panel, state_matrix, config)
    morphology = build_morphology_audit(native_panel, state_matrix, native_token_matrix, base_mask, dictionary, config)
    search = build_search_audit(config)
    decision = build_decision(
        input_status,
        a_status,
        a2_status,
        a2_reason,
        label_status,
        cost_lineage_status,
        cache_status,
        composite_status,
        _comp_reason,
        cost_summary,
        readout,
        badside,
        drift,
        morphology,
        dictionary,
        config,
    )

    write_df(outputs["composite_repair_state_dictionary"], dictionary)
    write_df(outputs["composite_state_matrix"], state_matrix)
    write_df(outputs["row_level_cache_audit"], cache_audit)
    write_df(outputs["cost_buffer_sensitivity_audit"], cost_audit)
    write_df(outputs["cost_buffer_turning_point_summary"], cost_summary)
    write_df(outputs["composite_native_readout"], readout)
    write_df(outputs["composite_badside_utility_audit"], badside)
    write_df(outputs["composite_denominator_drift_audit"], drift)
    write_df(outputs["composite_morphology_independent_evidence_audit"], morphology)
    write_df(outputs["composite_search_multiplicity_audit"], search)
    write_df(outputs["compression_repair_state_feasibility_decision"], decision)
    write_text(outputs["report"], render_report(decision, cost_summary, readout, badside, drift, morphology, dictionary, label_lineage, cost_lineage, cache_audit))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
