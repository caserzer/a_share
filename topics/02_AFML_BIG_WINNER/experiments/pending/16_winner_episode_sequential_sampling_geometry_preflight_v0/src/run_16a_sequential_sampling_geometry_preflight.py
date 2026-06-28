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
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP15_ROOT = (
    TOPIC_ROOT
    / "experiments"
    / "pending"
    / "15_path_defined_winner_episode_label_v0"
)
RUNNER_15B_PATH = SOURCE_EP15_ROOT / "src" / "run_15b_winner_path_shape_taxonomy_diagnostic.py"
SOURCE_ROOTS = {
    "SOURCE_EP15_ROOT": SOURCE_EP15_ROOT,
    "SOURCE_EP14_ROOT": TOPIC_ROOT
    / "experiments"
    / "pending"
    / "14_full_native_sparse_state_change_event_utility_preflight_v0",
    "SOURCE_EP13_ROOT": TOPIC_ROOT
    / "experiments"
    / "pending"
    / "13_full_pit_native_event_discovery_v0",
}


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r15b = load_runner(RUNNER_15B_PATH, "run_15b_for_16a")
r15a = r15b.r15a
r13a = r15b.r13a

RUN_ID = "16A_sequential_sampling_geometry_preflight"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16a_sequential_sampling_geometry_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
DECISION_READY = "16A_sampling_geometry_ready_for_sequential_label_design"
NEXT_16B = "requirement_16b_sequential_continuation_label_design_diagnostic.md"
AUTHORIZATION_BASIS = "ep15_effective_sample_and_position_dependence_not_shape_taxonomy"
HORIZON_TEXT = "5;8;13;15;20"

MEMBERSHIP_REQUIRED_COLUMNS = [
    "instrument",
    "reference_date",
    "row_id",
    "threshold_id",
    "split_bucket",
    "entry_pos",
    "time_to_threshold_sessions",
    "path_winner",
    "is_censored",
    "available_forward_sessions",
    "episode_threshold_pos",
    "episode_cluster_id",
    "cluster_start_pos",
    "cluster_end_pos",
    "cluster_split_bucket",
    "touches_multiple_split_buckets",
    "touches_multiple_calendar_split_buckets",
]

CACHE_CLUSTER_COLUMNS = [
    "threshold_id",
    "instrument",
    "episode_cluster_id",
    "cluster_start_pos",
    "cluster_end_pos",
]

LABEL_REBUILD_COLUMNS = [
    "instrument",
    "reference_date",
    "row_id",
    "threshold_id",
    "entry_pos",
    "episode_threshold_pos",
    "path_winner",
    "is_censored",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16A sequential sampling geometry preflight.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    for alias, root in SOURCE_ROOTS.items():
        prefix = f"{alias}/"
        if text.startswith(prefix):
            return root / text[len(prefix) :]
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
        "price_path_completeness_audit": TABLE_DIR / "price_path_completeness_audit.csv",
        "cluster_interval_adapter_audit": TABLE_DIR / "cluster_interval_adapter_audit.csv",
        "cluster_interval_rebuild_audit": TABLE_DIR / "cluster_interval_rebuild_audit.csv",
        "sampling_unit_count_readout": TABLE_DIR / "sampling_unit_count_readout.csv",
        "horizon_grid_step_readout": TABLE_DIR / "horizon_grid_step_readout.csv",
        "anchor_overcount_readout": TABLE_DIR / "anchor_overcount_readout.csv",
        "effective_sample_size_readout": TABLE_DIR / "effective_sample_size_readout.csv",
        "episode_cluster_non_overlap_audit": TABLE_DIR / "episode_cluster_non_overlap_audit.csv",
        "geometry_by_split_readout": TABLE_DIR / "geometry_by_split_readout.csv",
        "geometry_by_threshold_sensitivity_readout": TABLE_DIR / "geometry_by_threshold_sensitivity_readout.csv",
        "sampling_geometry_decision": TABLE_DIR / "sampling_geometry_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "episode_interval_panel": LOCAL_CACHE_DIR / "episode_interval_panel.parquet",
        "step_geometry_panel": LOCAL_CACHE_DIR / "step_geometry_panel.parquet",
        "report": REPORT_DIR / "sequential_sampling_geometry_preflight_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r15a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r15a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r15a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r15a.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r15b.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r15a.count_rows(path)


def safe_rate(num: Any, den: Any, *, default_denominator: float = 0.0) -> float:
    try:
        den_f = float(den)
        if den_f == 0 or not np.isfinite(den_f):
            if default_denominator > 0:
                return float(num) / default_denominator
            return np.nan
        return float(num) / den_f
    except Exception:
        return np.nan


def bool_series(series: pd.Series) -> pd.Series:
    return r15a.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def path_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["instrument"].astype(str)
        + "|"
        + frame["reference_date"].astype(str)
        + "|"
        + frame["row_id"].astype(str)
        + "|"
        + frame["threshold_id"].astype(str)
    )


def artifact_required_columns(role: str) -> tuple[str, ...]:
    expected = {
        "upstream_15b_membership_audit": tuple(MEMBERSHIP_REQUIRED_COLUMNS),
        "upstream_15b_split_overlap_audit": (
            "instrument",
            "threshold_id",
            "episode_cluster_id",
            "cluster_split_bucket",
            "touches_multiple_split_buckets",
            "touches_multiple_calendar_split_buckets",
            "split_overlap_status",
        ),
        "upstream_15a_price_path_completeness_audit": (
            "instrument",
            "qfq_row_n",
            "price_path_status",
        ),
        "upstream_15b_price_path_completeness_audit": (
            "instrument",
            "qfq_row_n",
            "price_path_status",
        ),
        "upstream_15c2_decision": (
            "decision_state",
            "next_allowed_requirement",
            "decision_status",
        ),
        "upstream_15c2_membership_vs_random_baseline": (
            "threshold_id",
            "cluster_split_bucket",
            "baseline_variant",
            "random_baseline_status",
        ),
        "upstream_15a_path_defined_label_cache": tuple(LABEL_REBUILD_COLUMNS),
        "upstream_15b_winner_episode_cluster_cache": tuple(CACHE_CLUSTER_COLUMNS),
    }
    return expected.get(role, ())


def optional_artifacts() -> set[str]:
    return {
        "upstream_15a_path_defined_label_cache",
        "upstream_15b_winner_episode_cluster_cache",
    }


def lineage_role_for_artifact(role: str) -> str:
    if role.startswith("upstream_requirement"):
        return "upstream_requirement_context"
    if role.startswith("upstream_15a"):
        return "upstream_15a_lineage"
    if role.startswith("upstream_15b"):
        return "upstream_15b_cluster_lineage"
    if role.startswith("upstream_15c2"):
        return "upstream_15c2_override_guard"
    if role == "source_plan":
        return "episode_16_research_plan"
    return "run_config_input"


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw_paths = config.get("paths", {})
    for role, path in resolved.items():
        required_cols = artifact_required_columns(role)
        required = role not in optional_artifacts()
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        missing_cols: list[str] = []
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                elif path.suffix == ".md" or path.suffix in {".yaml", ".yml", ".json"}:
                    schema_status = "not_checked"
                else:
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        sample = pd.read_parquet(path).head(5)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    if suffixes.endswith((".csv", ".csv.gz", ".parquet")):
                        column_count = len(sample.columns)
                        missing_cols = sorted(set(required_cols) - set(sample.columns))
                        schema_status = "pass" if not missing_cols else "missing_columns:" + ";".join(missing_cols)
                        row_count = count_rows(path)
            except Exception as exc:  # pragma: no cover - defensive audit
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        gate_status = "pass"
        if required and read_status != "pass":
            gate_status = "fail"
        if required and schema_status.startswith("missing_columns"):
            gate_status = "fail"
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": str(raw_paths.get(role, path)),
                "resolved_path": str(path),
                "required_flag": required,
                "lineage_role": lineage_role_for_artifact(role),
                "read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing_cols),
                "input_gate_status": gate_status,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    if audit.empty or "input_gate_status" not in audit.columns:
        return "fail", "empty_or_malformed_input_artifact_audit"
    bad = audit.loc[audit["input_gate_status"].astype(str).ne("pass")]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_role"].astype(str).tolist())


def status_all(frame: pd.DataFrame, status_col: str, allowlist: set[str]) -> str:
    if frame.empty or status_col not in frame.columns:
        return "fail"
    statuses = set(frame[status_col].astype(str).fillna(""))
    return "pass" if statuses.issubset(allowlist) else "fail"


def load_membership(path: Path) -> pd.DataFrame:
    frame = read_table(path)
    if "source_row_key" not in frame.columns and set(["instrument", "reference_date", "row_id", "threshold_id"]).issubset(frame.columns):
        frame["source_row_key"] = path_key(frame)
    numeric_cols = [
        "entry_pos",
        "time_to_threshold_sessions",
        "available_forward_sessions",
        "episode_threshold_pos",
        "cluster_start_pos",
        "cluster_end_pos",
    ]
    for col in numeric_cols:
        if col in frame.columns:
            frame[col] = finite(frame[col])
    return frame


def build_cluster_interval_adapter_audit(membership: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    missing = sorted(set(MEMBERSHIP_REQUIRED_COLUMNS) - set(membership.columns))
    required_present = not missing
    if not required_present:
        return pd.DataFrame(
            [
                {
                    "source_row_key": "instrument,reference_date,row_id,threshold_id",
                    "adapter_source_path": str(source_path),
                    "adapter_required_columns_present": False,
                    "adapter_missing_columns": ";".join(missing),
                    "adapter_cluster_interval_present": False,
                    "adapter_row_count": len(membership),
                    "adapter_duplicate_source_row_key_n": np.nan,
                    "anchor_entry_pos_source_field": "entry_pos",
                    "missing_entry_pos_n": np.nan,
                    "missing_episode_threshold_pos_n": np.nan,
                    "hit_pos_relation_mismatch_n": np.nan,
                    "entry_pos_interval_violation_n": np.nan,
                    "entry_hit_interval_violation_n": np.nan,
                    "missing_available_forward_sessions_n": np.nan,
                    "adapter_status": "fail",
                    "blocking_reason": "missing_required_columns",
                }
            ]
        )

    frame = membership.copy()
    if "source_row_key" not in frame.columns:
        frame["source_row_key"] = path_key(frame)
    entry = finite(frame["entry_pos"])
    hit = finite(frame["episode_threshold_pos"])
    time_to_hit = finite(frame["time_to_threshold_sessions"])
    start = finite(frame["cluster_start_pos"])
    end = finite(frame["cluster_end_pos"])
    available = finite(frame["available_forward_sessions"])
    duplicate_n = int(frame["source_row_key"].duplicated().sum())
    missing_entry_n = int(entry.isna().sum())
    missing_hit_n = int(hit.isna().sum())
    relation_valid = entry.notna() & hit.notna() & time_to_hit.notna()
    relation_mismatch_n = int((hit.loc[relation_valid].sub(entry.loc[relation_valid] + time_to_hit.loc[relation_valid]).abs() > 1e-9).sum())
    entry_interval_valid = start.notna() & end.notna() & entry.notna()
    entry_violation_n = int(((entry < start) | (entry > end)).loc[entry_interval_valid].sum())
    hit_interval_valid = entry_interval_valid & hit.notna()
    hit_violation_n = int(((entry > hit) | (hit > end)).loc[hit_interval_valid].sum())
    missing_available_n = int(available.isna().sum())
    interval_present = start.notna().all() and end.notna().all()
    bad = [
        duplicate_n,
        missing_entry_n,
        missing_hit_n,
        relation_mismatch_n,
        entry_violation_n,
        hit_violation_n,
        missing_available_n,
    ]
    status = "pass" if interval_present and all(value == 0 for value in bad) else "fail"
    return pd.DataFrame(
        [
            {
                "source_row_key": "instrument,reference_date,row_id,threshold_id",
                "adapter_source_path": str(source_path),
                "adapter_required_columns_present": True,
                "adapter_missing_columns": "",
                "adapter_cluster_interval_present": bool(interval_present),
                "adapter_row_count": len(frame),
                "adapter_duplicate_source_row_key_n": duplicate_n,
                "anchor_entry_pos_source_field": "entry_pos",
                "missing_entry_pos_n": missing_entry_n,
                "missing_episode_threshold_pos_n": missing_hit_n,
                "hit_pos_relation_mismatch_n": relation_mismatch_n,
                "entry_pos_interval_violation_n": entry_violation_n,
                "entry_hit_interval_violation_n": hit_violation_n,
                "missing_available_forward_sessions_n": missing_available_n,
                "adapter_status": status,
                "blocking_reason": "" if status == "pass" else "cluster_interval_adapter_invariant_failed",
            }
        ]
    )


def build_cluster_interval_rebuild_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    cache_path = resolved["upstream_15b_winner_episode_cluster_cache"]
    source_path = resolved["upstream_15a_path_defined_label_cache"]
    config_path = resolved["upstream_15b_config"]
    base = {
        "rebuild_source_path": str(source_path),
        "rebuild_source_sha256": file_sha(source_path),
        "rebuild_config_path": str(config_path),
        "rebuild_config_sha256": file_sha(config_path),
        "rebuild_rule_authority": "upstream_requirement_15b_section_6_2",
        "rebuild_population_predicate": "path_winner == true and is_censored == false",
        "rebuild_group_key": "instrument,threshold_id",
        "rebuild_interval_start_field": "entry_pos",
        "rebuild_interval_end_field": "episode_threshold_pos",
        "rebuild_overlap_predicate": "interval_i.start_pos <= interval_j.end_pos and interval_j.start_pos <= interval_i.end_pos",
        "rebuild_connected_component_algorithm": "single_pass_sorted_transitive_interval_merge",
    }
    if cache_path.exists():
        try:
            cache = read_table(cache_path)
            missing = sorted(set(CACHE_CLUSTER_COLUMNS) - set(cache.columns))
            if not missing:
                return pd.DataFrame(
                    [
                        {
                            **base,
                            "rebuild_trigger": "cache_schema_pass",
                            "rebuilt_episode_cluster_n": int(cache["episode_cluster_id"].nunique()),
                            "rebuilt_membership_row_n": np.nan,
                            "rebuild_status": "not_required_pass",
                            "blocking_reason": "",
                        }
                    ]
                )
        except Exception as exc:
            cache_error = f"cache_read_error:{type(exc).__name__}"
        else:
            cache_error = "cache_missing_required_columns"
    else:
        cache_error = "cache_missing"

    if not source_path.exists():
        return pd.DataFrame(
            [
                {
                    **base,
                    "rebuild_trigger": cache_error,
                    "rebuilt_episode_cluster_n": np.nan,
                    "rebuilt_membership_row_n": np.nan,
                    "rebuild_status": "fail",
                    "blocking_reason": "missing_15a_path_defined_label_panel",
                }
            ]
        )
    try:
        label = read_table(source_path)
        missing = sorted(set(LABEL_REBUILD_COLUMNS) - set(label.columns))
        if missing:
            raise ValueError("missing_columns:" + ";".join(missing))
        membership, clusters = r15b.build_winner_episode_clusters(label)
        status = "pass"
        reason = ""
    except Exception as exc:
        membership = pd.DataFrame()
        clusters = pd.DataFrame()
        status = "fail"
        reason = f"cluster_interval_rebuild_error:{type(exc).__name__}"
    return pd.DataFrame(
        [
            {
                **base,
                "rebuild_trigger": cache_error,
                "rebuilt_episode_cluster_n": int(clusters["episode_cluster_id"].nunique()) if not clusters.empty else 0,
                "rebuilt_membership_row_n": len(membership),
                "rebuild_status": status,
                "blocking_reason": reason,
            }
        ]
    )


def build_upstream_lineage_audit(
    resolved: dict[str, Path],
    membership: pd.DataFrame,
    split_overlap: pd.DataFrame,
    price_15a: pd.DataFrame,
    price_15b: pd.DataFrame,
    decision_15c2: pd.DataFrame,
    random_15c2: pd.DataFrame,
) -> pd.DataFrame:
    checks = [
        (
            "upstream_15b_membership_audit",
            "15B row-level winner episode membership is the adapter source for cluster intervals.",
            "pass"
            if not membership.empty and status_all(membership, "episode_cluster_status", {"pass"}) == "pass"
            else "fail",
        ),
        (
            "upstream_15b_split_overlap_audit",
            "15B split-overlap audit proves cross-split isolation flags.",
            status_all(split_overlap, "split_overlap_status", {"pass"}),
        ),
        (
            "upstream_15a_price_path_completeness_audit",
            "15A price path audit is required lineage for qfq session position completeness.",
            status_all(price_15a, "price_path_status", {"pass"}),
        ),
        (
            "upstream_15b_price_path_completeness_audit",
            "15B price path audit is required lineage for episode hit/cluster bounds.",
            status_all(price_15b, "price_path_status", {"pass"}),
        ),
        (
            "upstream_15b_config",
            "15B config freezes selected threshold and threshold sensitivity grid lineage.",
            "pass" if resolved["upstream_15b_config"].exists() else "fail",
        ),
        (
            "upstream_15c2_decision",
            "15C2 next_allowed_requirement none is treated as taxonomy denial, not as denial of 16A sampling geometry preflight.",
            "pass"
            if not decision_15c2.empty
            and status_all(decision_15c2, "decision_status", {"pass"}) == "pass"
            and "none" in set(decision_15c2["next_allowed_requirement"].astype(str))
            else "fail",
        ),
        (
            "upstream_15c2_membership_vs_random_baseline",
            "15C2 random baseline readout guards the effective-sample override rationale.",
            status_all(random_15c2, "random_baseline_status", {"pass"}),
        ),
    ]
    rows: list[dict[str, Any]] = []
    for role, claim, status in checks:
        path = resolved[role]
        rows.append(
            {
                "upstream_artifact_role": role,
                "upstream_path": str(path),
                "upstream_sha256": file_sha(path),
                "upstream_row_count": count_rows(path) if path.exists() else np.nan,
                "lineage_claim": claim,
                "lineage_status": status,
                "blocking_reason": "" if status == "pass" else "upstream_lineage_status_failed",
            }
        )
    return pd.DataFrame(rows)


def build_price_path_completeness_audit(
    membership: pd.DataFrame,
    price_15a: pd.DataFrame,
    price_15b: pd.DataFrame,
) -> pd.DataFrame:
    price_15a_ok = status_all(price_15a, "price_path_status", {"pass"}) == "pass"
    price_15b_ok = status_all(price_15b, "price_path_status", {"pass"}) == "pass"
    qfq_map = {}
    if "instrument" in price_15b.columns and "qfq_row_n" in price_15b.columns:
        qfq_map = dict(zip(price_15b["instrument"].astype(str), finite(price_15b["qfq_row_n"])))
    rows: list[dict[str, Any]] = []
    group_cols = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"]
    for keys, sub in membership.groupby(group_cols, dropna=False, sort=False):
        threshold_id, split, instrument, cluster_id = keys
        start = finite(sub["cluster_start_pos"]).min()
        end = finite(sub["cluster_end_pos"]).max()
        available = finite(sub["available_forward_sessions"])
        entry = finite(sub["entry_pos"])
        qfq_row_n = qfq_map.get(str(instrument), np.nan)
        start_bad = int(pd.isna(start) or start < 0)
        end_bad = int(pd.isna(end) or pd.isna(qfq_row_n) or end >= qfq_row_n)
        beyond = int(((end - entry + 1) > available).fillna(True).sum())
        missing_qfq = pd.isna(qfq_row_n)
        status = "pass" if price_15a_ok and price_15b_ok and not missing_qfq and start_bad == 0 and end_bad == 0 and beyond == 0 else "fail"
        reasons = []
        if not price_15a_ok or not price_15b_ok:
            reasons.append("upstream_price_path_audit_nonpass")
        if missing_qfq:
            reasons.append("missing_qfq_row_n")
        if start_bad:
            reasons.append("cluster_start_out_of_bounds")
        if end_bad:
            reasons.append("cluster_end_out_of_bounds")
        if beyond:
            reasons.append("cluster_end_beyond_anchor_available_forward_sessions")
        rows.append(
            {
                "threshold_id": threshold_id,
                "cluster_split_bucket": split,
                "instrument": instrument,
                "episode_cluster_id": cluster_id,
                "anchor_n": len(sub),
                "qfq_row_n": qfq_row_n,
                "cluster_start_pos": start,
                "cluster_end_pos": end,
                "available_forward_sessions_min": available.min(),
                "cluster_start_out_of_bounds_n": start_bad,
                "cluster_end_out_of_bounds_n": end_bad,
                "cluster_end_beyond_anchor_available_forward_sessions_n": beyond,
                "price_path_status": status,
                "blocking_reason": ";".join(reasons),
            }
        )
    return pd.DataFrame(rows)


def build_episode_interval_panel(membership: pd.DataFrame, price_audit: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    sg = config["sampling_geometry"]
    thresholds = set(sg["threshold_sensitivity_grid"])
    eligible_splits = set(sg["eligible_split_buckets"])
    frame = membership.copy()
    if "source_row_key" not in frame.columns:
        frame["source_row_key"] = path_key(frame)
    frame["_path_winner"] = bool_series(frame["path_winner"])
    frame["_is_censored"] = bool_series(frame["is_censored"])
    frame["_touch_member"] = bool_series(frame["touches_multiple_split_buckets"])
    frame["_touch_calendar"] = bool_series(frame["touches_multiple_calendar_split_buckets"])
    group_cols = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"]
    rows: list[dict[str, Any]] = []
    for keys, sub in frame.groupby(group_cols, dropna=False, sort=False):
        threshold_id, split, instrument, cluster_id = keys
        start = int(finite(sub["cluster_start_pos"]).min()) if finite(sub["cluster_start_pos"]).notna().any() else np.nan
        end = int(finite(sub["cluster_end_pos"]).max()) if finite(sub["cluster_end_pos"]).notna().any() else np.nan
        anchor_mask = sub["_path_winner"] & ~sub["_is_censored"]
        touch_member = bool(sub["_touch_member"].any())
        touch_calendar = bool(sub["_touch_calendar"].any())
        interval_len = end - start + 1 if pd.notna(start) and pd.notna(end) else np.nan
        rows.append(
            {
                "threshold_id": threshold_id,
                "cluster_split_bucket": split,
                "instrument": instrument,
                "episode_cluster_id": cluster_id,
                "cluster_start_pos": start,
                "cluster_end_pos": end,
                "episode_length_sessions": interval_len,
                "anchor_n": int(anchor_mask.sum()),
                "source_anchor_row_n": len(sub),
                "touches_multiple_split_buckets": touch_member,
                "touches_multiple_calendar_split_buckets": touch_calendar,
                "path_winner_uncensored_anchor_n": int(anchor_mask.sum()),
            }
        )
    intervals = pd.DataFrame(rows)
    if intervals.empty:
        intervals["eligible_episode_cluster"] = False
        return intervals
    intervals = intervals.merge(
        price_audit[
            [
                "threshold_id",
                "cluster_split_bucket",
                "instrument",
                "episode_cluster_id",
                "price_path_status",
            ]
        ],
        on=["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"],
        how="left",
    )
    intervals["eligible_episode_cluster"] = (
        intervals["threshold_id"].astype(str).isin(thresholds)
        & intervals["cluster_split_bucket"].astype(str).isin(eligible_splits)
        & ~bool_series(intervals["touches_multiple_split_buckets"])
        & ~bool_series(intervals["touches_multiple_calendar_split_buckets"])
        & intervals["price_path_status"].astype(str).eq("pass")
        & finite(intervals["cluster_start_pos"]).notna()
        & finite(intervals["cluster_end_pos"]).notna()
        & (finite(intervals["episode_length_sessions"]) > 0)
        & (finite(intervals["path_winner_uncensored_anchor_n"]) > 0)
    )
    return intervals


def overlapping_uniqueness_for_interval(length: int, horizon: int) -> tuple[int, float, float]:
    if length < horizon or horizon <= 0:
        return 0, 0.0, 0.0
    step_n = length - horizon + 1
    effective = float(length) / float(horizon)
    average = effective / float(step_n)
    return int(step_n), float(average), float(effective)


def build_step_geometry_panel(intervals: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    eligible = intervals.loc[bool_series(intervals["eligible_episode_cluster"])].copy()
    for row in eligible.itertuples(index=False):
        length = int(row.episode_length_sessions)
        for horizon in horizons:
            nonoverlap = int(math.ceil(length / horizon))
            full = int(length // horizon)
            partial = int(1 if length % horizon else 0)
            overlap, avg_unique, eff_overlap = overlapping_uniqueness_for_interval(length, horizon)
            status = "pass"
            if nonoverlap != full + partial:
                status = "fail"
            if overlap != max(length - horizon + 1, 0):
                status = "fail"
            if not 0 <= avg_unique <= 1:
                status = "fail"
            rows.append(
                {
                    "threshold_id": row.threshold_id,
                    "cluster_split_bucket": row.cluster_split_bucket,
                    "instrument": row.instrument,
                    "episode_cluster_id": row.episode_cluster_id,
                    "horizon_sessions": horizon,
                    "cluster_start_pos": row.cluster_start_pos,
                    "cluster_end_pos": row.cluster_end_pos,
                    "episode_length_sessions": length,
                    "anchor_n": int(row.anchor_n),
                    "step_n_nonoverlap": nonoverlap,
                    "full_horizon_nonoverlap_step_n": full,
                    "partial_tail_step_n": partial,
                    "labelable_step_n_for_future_16B": full,
                    "step_n_overlap": overlap,
                    "average_uniqueness": avg_unique,
                    "average_uniqueness_nonoverlap": 1.0,
                    "effective_sample_size_overlap": eff_overlap,
                    "effective_sample_size_nonoverlap": float(full),
                    "geometry_status": status,
                }
            )
    return pd.DataFrame(rows)


def group_or_empty(frame: pd.DataFrame, group_cols: list[str]):
    if frame.empty:
        return []
    if len(group_cols) == 1:
        return frame.groupby(group_cols[0], dropna=False, sort=False)
    return frame.groupby(group_cols, dropna=False, sort=False)


def build_sampling_unit_count_readout(intervals: pd.DataFrame, primary_horizon: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    eligible = intervals.loc[bool_series(intervals["eligible_episode_cluster"])].copy()
    for (threshold, split), sub in group_or_empty(eligible, ["threshold_id", "cluster_split_bucket"]):
        lengths = finite(sub["episode_length_sessions"])
        anchors = int(finite(sub["anchor_n"]).sum())
        nonoverlap = int(np.ceil(lengths / primary_horizon).sum())
        full = int(np.floor(lengths / primary_horizon).sum())
        partial = int(((lengths % primary_horizon) != 0).sum())
        clusters = int(sub["episode_cluster_id"].nunique())
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "anchor_n": anchors,
                "episode_cluster_n": clusters,
                "nonoverlap_step_n_at_primary_horizon": nonoverlap,
                "full_horizon_nonoverlap_step_n_at_primary_horizon": full,
                "partial_tail_step_n_at_primary_horizon": partial,
                "anchor_to_episode_ratio": safe_rate(anchors, max(clusters, 1)),
                "anchor_to_nonoverlap_step_ratio_primary_horizon": safe_rate(anchors, max(nonoverlap, 1)),
                "anchor_to_full_horizon_step_ratio_primary_horizon": safe_rate(anchors, max(full, 1)),
                "unit_count_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_horizon_grid_step_readout(intervals: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (threshold, split, horizon), sub in group_or_empty(steps, ["threshold_id", "cluster_split_bucket", "horizon_sessions"]):
        length_sum = float(finite(sub["episode_length_sessions"]).sum())
        full_sum = int(finite(sub["full_horizon_nonoverlap_step_n"]).sum())
        nonoverlap_sum = int(finite(sub["step_n_nonoverlap"]).sum())
        partial_sum = int(finite(sub["partial_tail_step_n"]).sum())
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "horizon_sessions": int(horizon),
                "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
                "median_episode_length_sessions": float(finite(sub["episode_length_sessions"]).median()),
                "step_n_nonoverlap": nonoverlap_sum,
                "full_horizon_nonoverlap_step_n": full_sum,
                "partial_tail_step_n": partial_sum,
                "labelable_step_n_for_future_16B": full_sum,
                "step_n_overlap": int(finite(sub["step_n_overlap"]).sum()),
                "partial_tail_step_share": safe_rate(partial_sum, max(nonoverlap_sum, 1)),
                "coverage_share": safe_rate(full_sum * int(horizon), max(length_sum, 1.0)),
                "horizon_status": "pass" if set(sub["geometry_status"].astype(str)) == {"pass"} else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_anchor_overcount_readout(steps: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (threshold, split, horizon), sub in group_or_empty(steps, ["threshold_id", "cluster_split_bucket", "horizon_sessions"]):
        anchor = finite(sub["anchor_n"])
        nonoverlap = finite(sub["step_n_nonoverlap"]).clip(lower=1)
        labelable = finite(sub["labelable_step_n_for_future_16B"]).clip(lower=1)
        ratios = anchor / nonoverlap
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "horizon_sessions": int(horizon),
                "anchor_overcount_ratio_median": float(ratios.median()) if len(ratios) else np.nan,
                "anchor_overcount_ratio_p90": float(ratios.quantile(0.90)) if len(ratios) else np.nan,
                "anchor_overcount_ratio_anchor_weighted": safe_rate(anchor.sum(), max(finite(sub["step_n_nonoverlap"]).sum(), 1)),
                "anchor_to_labelable_step_ratio_anchor_weighted": safe_rate(anchor.sum(), max(finite(sub["labelable_step_n_for_future_16B"]).sum(), 1)),
                "overcount_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def validate_effective_sample_readout(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    avg = finite(frame["average_uniqueness"])
    avg_non = finite(frame["average_uniqueness_nonoverlap"])
    eff_overlap = finite(frame["effective_sample_size_overlap"])
    step_overlap = finite(frame["step_n_overlap"])
    eff_non = finite(frame["effective_sample_size_nonoverlap"])
    full = finite(frame["full_horizon_nonoverlap_step_n"])
    good = (
        avg.between(0, 1)
        & avg_non.eq(1.0)
        & (eff_overlap <= step_overlap + 1e-9)
        & (eff_non <= full + 1e-9)
        & step_overlap.ge(0)
        & full.ge(0)
    )
    return good.map({True: "pass", False: "fail"})


def build_effective_sample_size_readout(steps: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (threshold, split, horizon), sub in group_or_empty(steps, ["threshold_id", "cluster_split_bucket", "horizon_sessions"]):
        anchor_n = int(finite(sub["anchor_n"]).sum())
        step_overlap = int(finite(sub["step_n_overlap"]).sum())
        eff_overlap = float(finite(sub["effective_sample_size_overlap"]).sum())
        full = int(finite(sub["full_horizon_nonoverlap_step_n"]).sum())
        eff_non = float(finite(sub["effective_sample_size_nonoverlap"]).sum())
        cluster_n = int(sub["episode_cluster_id"].nunique())
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "horizon_sessions": int(horizon),
                "episode_cluster_n": cluster_n,
                "anchor_n": anchor_n,
                "step_n_overlap": step_overlap,
                "average_uniqueness": safe_rate(eff_overlap, step_overlap) if step_overlap else 0.0,
                "average_uniqueness_nonoverlap": 1.0,
                "full_horizon_nonoverlap_step_n": full,
                "effective_sample_size_overlap": eff_overlap,
                "effective_sample_size_nonoverlap": eff_non,
                "effective_sample_size_episode_cluster_blocked": float(cluster_n),
                "partial_tail_step_n": int(finite(sub["partial_tail_step_n"]).sum()),
                "effective_to_anchor_ratio": safe_rate(eff_non, max(anchor_n, 1)),
                "episode_cluster_to_anchor_ratio": safe_rate(cluster_n, max(anchor_n, 1)),
                "time_block_to_anchor_ratio": safe_rate(eff_non, max(anchor_n, 1)),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["effective_sample_status"] = validate_effective_sample_readout(out)
    return out


def _overlap_stats(interval_frame: pd.DataFrame) -> tuple[int, int, list[str]]:
    pair_n = 0
    max_concurrency = 0
    examples: list[str] = []
    for _instrument, inst in interval_frame.groupby("instrument", sort=False):
        sorted_inst = inst.sort_values(
            ["cluster_start_pos", "cluster_end_pos", "episode_cluster_id"],
            kind="stable",
        )
        active: list[tuple[int, str]] = []
        for row in sorted_inst.itertuples(index=False):
            if pd.isna(row.cluster_start_pos) or pd.isna(row.cluster_end_pos):
                continue
            start = int(row.cluster_start_pos)
            end = int(row.cluster_end_pos)
            cluster_id = str(row.episode_cluster_id)
            active = [(active_end, active_id) for active_end, active_id in active if active_end >= start]
            pair_n += len(active)
            for _active_end, active_id in active:
                if len(examples) < 5:
                    examples.append(f"{active_id}|{cluster_id}")
            active.append((end, cluster_id))
            max_concurrency = max(max_concurrency, len(active))
    return pair_n, max_concurrency, examples


def build_episode_cluster_non_overlap_audit(intervals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source = intervals.copy()
    audit_groups: list[tuple[Any, str, pd.DataFrame]] = []
    for threshold, sub in group_or_empty(source, ["threshold_id"]):
        audit_groups.append((threshold, "all_cluster_split_buckets", sub))
    for (threshold, split), sub in group_or_empty(source, ["threshold_id", "cluster_split_bucket"]):
        audit_groups.append((threshold, str(split), sub))

    for threshold, split, sub in audit_groups:
        pair_n, max_concurrency, examples = _overlap_stats(sub)
        status = "pass_no_same_threshold_overlap" if pair_n == 0 else "fail_same_threshold_overlap"
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "instrument_n": int(sub["instrument"].nunique()),
                "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
                "same_threshold_instrument_overlap_pair_n": pair_n,
                "max_same_threshold_instrument_concurrency": max_concurrency,
                "overlap_example_episode_cluster_ids": ";".join(examples),
                "concurrency_status": status,
            }
        )
    return pd.DataFrame(rows)


def build_geometry_by_split_readout(effective: pd.DataFrame, selected_threshold: str, primary_horizon: int) -> pd.DataFrame:
    return effective.loc[
        effective["threshold_id"].astype(str).eq(selected_threshold)
        & finite(effective["horizon_sessions"]).eq(primary_horizon)
    ].reset_index(drop=True)


def build_geometry_by_threshold_sensitivity_readout(effective: pd.DataFrame, primary_horizon: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    primary = effective.loc[finite(effective["horizon_sessions"]).eq(primary_horizon)].copy()
    for threshold, sub in group_or_empty(primary, ["threshold_id"]):
        anchor_n = int(finite(sub["anchor_n"]).sum())
        rows.append(
            {
                "threshold_id": threshold,
                "primary_horizon_sessions": primary_horizon,
                "cluster_split_bucket": "all_eligible_splits",
                "anchor_n": anchor_n,
                "episode_cluster_n": int(finite(sub["episode_cluster_n"]).sum()),
                "full_horizon_nonoverlap_step_n": int(finite(sub["full_horizon_nonoverlap_step_n"]).sum()),
                "effective_sample_size_nonoverlap": float(finite(sub["effective_sample_size_nonoverlap"]).sum()),
                "effective_to_anchor_ratio": safe_rate(finite(sub["effective_sample_size_nonoverlap"]).sum(), max(anchor_n, 1)),
                "threshold_sensitivity_status": "pass" if set(sub["effective_sample_status"].astype(str)) == {"pass"} else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_search_accounting_audit(config: dict[str, Any]) -> pd.DataFrame:
    sg = config["sampling_geometry"]
    row = {
        "startup_authorization_basis": sg.get("startup_authorization_basis"),
        "manual_research_plan_override": bool(sg.get("manual_research_plan_override")),
        "selected_threshold_id": sg.get("selected_threshold_id"),
        "threshold_selection_source": sg.get("threshold_selection_source"),
        "geometry_fit_split": "none_descriptive_only",
        "validation_usage": "stress_test_readout_only",
        "robustness_usage": "readout_only",
        "horizon_grid_sessions": ";".join(str(x) for x in sg.get("horizon_grid_sessions", [])),
        "primary_horizon_sessions": int(sg.get("primary_horizon_sessions")),
        "forward_return_computed": False,
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
        "separability_search_authorized": False,
        "sequential_label_authorized": False,
    }
    status = (
        row["startup_authorization_basis"] == AUTHORIZATION_BASIS
        and row["manual_research_plan_override"] is True
        and row["selected_threshold_id"] == "up50pct"
        and row["threshold_selection_source"] == "inherited_from_15A_lowest_pre_registered_material_censoring_threshold"
        and row["geometry_fit_split"] == "none_descriptive_only"
        and row["validation_usage"] == "stress_test_readout_only"
        and row["robustness_usage"] == "readout_only"
        and row["horizon_grid_sessions"] == HORIZON_TEXT
        and row["primary_horizon_sessions"] == 20
        and not any(
            [
                row["forward_return_computed"],
                row["entry_search_authorized"],
                row["signal_search_authorized"],
                row["model_training_authorized"],
                row["separability_search_authorized"],
                row["sequential_label_authorized"],
            ]
        )
    )
    row["search_accounting_status"] = "pass" if status else "fail"
    return pd.DataFrame([row])


def _lookup(
    frame: pd.DataFrame,
    threshold: str,
    split: str,
    horizon: int | None = None,
) -> pd.Series | None:
    if frame.empty:
        return None
    mask = frame["threshold_id"].astype(str).eq(threshold) & frame["cluster_split_bucket"].astype(str).eq(split)
    if horizon is not None and "horizon_sessions" in frame.columns:
        mask &= finite(frame["horizon_sessions"]).eq(horizon)
    sub = frame.loc[mask]
    if sub.empty:
        return None
    return sub.iloc[0]


def build_sampling_geometry_decision(
    config: dict[str, Any],
    hard_gates: dict[str, str],
    sampling_units: pd.DataFrame,
    anchor_overcount: pd.DataFrame,
    effective: pd.DataFrame,
    horizon_readout: pd.DataFrame,
) -> pd.DataFrame:
    sg = config["sampling_geometry"]
    selected = sg["selected_threshold_id"]
    primary = int(sg["primary_horizon_sessions"])
    train_unit = _lookup(sampling_units, selected, "train")
    train_eff = _lookup(effective, selected, "train", primary)
    train_over = _lookup(anchor_overcount, selected, "train", primary)

    def unit_value(split: str, column: str) -> float:
        row = _lookup(sampling_units, selected, split)
        if row is None or column not in row:
            return 0.0
        value = row[column]
        return float(value) if pd.notna(value) else 0.0

    split_cluster_counts = {split: unit_value(split, "episode_cluster_n") for split in SPLITS}
    stability_splits = tuple(sg.get("stability_gate_split_buckets", ["train", "robustness"]))
    stress_splits = tuple(sg.get("stress_test_split_buckets", ["validation"]))
    stability_cluster_counts = {
        split: split_cluster_counts.get(split, 0.0) for split in stability_splits
    }
    min_split_cluster_n = min(stability_cluster_counts.values()) if stability_cluster_counts else 0.0
    train_cluster_n = split_cluster_counts["train"]
    train_anchor_n = unit_value("train", "anchor_n")
    train_nonoverlap = unit_value("train", "nonoverlap_step_n_at_primary_horizon")
    train_full = unit_value("train", "full_horizon_nonoverlap_step_n_at_primary_horizon")
    train_partial = unit_value("train", "partial_tail_step_n_at_primary_horizon")
    train_eff_sample = float(train_eff["effective_sample_size_nonoverlap"]) if train_eff is not None else 0.0
    train_eff_ratio = float(train_eff["effective_to_anchor_ratio"]) if train_eff is not None else 0.0
    overcount_ratio = (
        float(train_over["anchor_overcount_ratio_anchor_weighted"])
        if train_over is not None
        else 0.0
    )
    support_min = float(sg["split_stability_episode_clusters_min"])
    sufficient_clusters = train_cluster_n >= float(sg["sufficient_episode_clusters_min"])
    min_split_support = min_split_cluster_n >= support_min
    split_stability_evaluable = bool(min_split_support)
    split_ratios = []
    if split_stability_evaluable:
        for split in stability_splits:
            row = _lookup(effective, selected, split, primary)
            split_ratios.append(float(row["effective_to_anchor_ratio"]) if row is not None else np.nan)
    ratio_range = (
        float(np.nanmax(split_ratios) - np.nanmin(split_ratios))
        if split_ratios and np.isfinite(split_ratios).all()
        else np.nan
    )
    geometry_stable = bool(split_stability_evaluable and ratio_range <= float(sg["effective_to_anchor_ratio_abs_range_max"]))
    overcount_demonstrated = overcount_ratio > float(sg["anchor_overcount_ratio_min"])
    effective_nontrivial = train_eff_sample >= float(sg["effective_sample_size_min"])
    hard_fail = any(status != "pass" for status in hard_gates.values())
    if hard_fail:
        decision = "16A_blocked_input_or_lineage_failure"
        next_allowed = "none"
    elif not sufficient_clusters:
        decision = "16A_sampling_geometry_inconclusive_too_sparse"
        next_allowed = "none"
    elif not min_split_support:
        decision = "16A_sampling_geometry_inconclusive_too_sparse"
        next_allowed = "none"
    elif not geometry_stable:
        decision = "16A_sampling_geometry_unstable_across_splits"
        next_allowed = "none"
    elif overcount_demonstrated and not effective_nontrivial:
        decision = "16A_sampling_geometry_overcount_confirmed_but_effective_sample_too_small"
        next_allowed = "none"
    elif overcount_demonstrated and effective_nontrivial:
        decision = DECISION_READY
        next_allowed = NEXT_16B
    else:
        decision = "16A_sampling_geometry_overcount_not_demonstrated"
        next_allowed = "none"

    train_horizons = horizon_readout.loc[
        horizon_readout["threshold_id"].astype(str).eq(selected)
        & horizon_readout["cluster_split_bucket"].astype(str).eq("train")
    ]
    candidate_horizons = train_horizons.loc[
        finite(train_horizons["full_horizon_nonoverlap_step_n"]) >= float(sg["effective_sample_size_min"])
    ]["horizon_sessions"].astype(int).astype(str).tolist()
    if not candidate_horizons:
        candidate_horizons = ["none"]
    sparse_reason = ""
    if not min_split_support:
        sparse = [
            f"{split}={int(count)}"
            for split, count in stability_cluster_counts.items()
            if count < support_min
        ]
        sparse_reason = "split_cluster_support_below_100:" + ";".join(sparse)
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "selected_threshold_id": selected,
                "primary_horizon_sessions": primary,
                "anchor_n_train": train_anchor_n,
                "episode_cluster_n_train": train_cluster_n,
                "episode_cluster_n_validation": split_cluster_counts["validation"],
                "episode_cluster_n_robustness": split_cluster_counts["robustness"],
                "nonoverlap_step_n_train_primary_horizon": train_nonoverlap,
                "full_horizon_nonoverlap_step_n_train_primary_horizon": train_full,
                "partial_tail_step_n_train_primary_horizon": train_partial,
                "effective_sample_size_train_primary_horizon": train_eff_sample,
                "effective_to_anchor_ratio_train": train_eff_ratio,
                "split_stability_evaluable": split_stability_evaluable,
                "stability_gate_split_buckets": ";".join(stability_splits),
                "stress_test_split_buckets": ";".join(stress_splits),
                "validation_stress_test_readout_only": "validation" in stress_splits,
                "min_split_episode_cluster_n": min_split_cluster_n,
                "stability_not_evaluable_reason": sparse_reason,
                "recommended_sampling_unit": "non_overlapping_time_blocked_sampling_geometry_step",
                "recommended_horizon_candidate_set": ";".join(candidate_horizons),
                "geometry_stable_across_splits": geometry_stable,
                "anchor_overcount_demonstrated": overcount_demonstrated,
                "anchor_overcount_ratio_train_primary_horizon": overcount_ratio,
                "effective_sample_nontrivial": effective_nontrivial,
                "effective_to_anchor_ratio_abs_range": ratio_range,
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
                "sequential_label_authorized": False,
                **{f"{name}_gate": status for name, status in hard_gates.items()},
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if frame.empty:
        return "_无可用记录。_"
    sub = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    headers = list(sub.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in sub.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, float):
                cells.append("" if pd.isna(value) else f"{value:.4f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_report(
    decision: pd.DataFrame,
    sampling_units: pd.DataFrame,
    horizon_readout: pd.DataFrame,
    effective: pd.DataFrame,
    non_overlap: pd.DataFrame,
    threshold_readout: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    selected = str(d["selected_threshold_id"])
    primary = int(d["primary_horizon_sessions"])
    train_horizon = _lookup(horizon_readout, selected, "train", primary)
    median_len = float(train_horizon["median_episode_length_sessions"]) if train_horizon is not None else np.nan
    short_note = ""
    if pd.notna(median_len) and median_len < primary:
        short_note = (
            "\n\n注意：train 的 median_episode_length_sessions 小于 primary horizon，"
            "因此 full-horizon labelable step 稀疏是预注册 horizon 下的预期结果，不是实现错误。"
        )
    sparse_note = "\n\nvalidation 是压力测试 / stress-test readout，不进入 split-stability gate；validation cluster 数低于 100 不会单独阻断 primary decision。"
    if not bool(d["split_stability_evaluable"]):
        sparse_note += f"\n\nsplit stability 不可评估：{d['stability_not_evaluable_reason']}。"
    selected_effective = effective.loc[
        effective["threshold_id"].astype(str).eq(selected)
        & finite(effective["horizon_sessions"]).eq(primary)
    ]
    return f"""# 16A Winner Episode Sequential Sampling Geometry Preflight Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

本实验只回答采样几何问题，不定义 continuation label，不计算 forward return，不授权 entry、exit、holding、cost、模型、separability 或 label deployment。

## 2. 为什么 15C2 none 后仍可启动 16A

15C2 否定的是 winner 形态作为独立离散 taxonomy 或 t0 可预测标签。16A 没有复活 15B/15C/15C2 的形态线，而是把 Episode 15 反复暴露的隐含假设单独拿出来审计：anchor row 是否高估有效独立样本量。

启动依据被记录为 `{AUTHORIZATION_BASIS}`。这意味着 16A 的对象是 sampling geometry，不是收益、形态分类或信号搜索。

## 3. Anchor / Cluster / 非重叠 Step

selected threshold 为 `{selected}`，primary horizon 为 `{primary}` sessions。train 中 anchor_n = {d['anchor_n_train']:.0f}，episode_cluster_n = {d['episode_cluster_n_train']:.0f}，primary horizon 非重叠 step_n = {d['nonoverlap_step_n_train_primary_horizon']:.0f}，full-horizon labelable step_n = {d['full_horizon_nonoverlap_step_n_train_primary_horizon']:.0f}。

anchor_to_nonoverlap_step_ratio(primary) = {d['anchor_overcount_ratio_train_primary_horizon']:.4f}，用于量化 anchor 当独立样本时的高估倍数。

{markdown_table(sampling_units.loc[sampling_units['threshold_id'].astype(str).eq(selected)], ['threshold_id', 'cluster_split_bucket', 'anchor_n', 'episode_cluster_n', 'nonoverlap_step_n_at_primary_horizon', 'full_horizon_nonoverlap_step_n_at_primary_horizon', 'anchor_to_nonoverlap_step_ratio_primary_horizon'])}

## 4. Horizon Grid 与 Partial Tail

{markdown_table(horizon_readout.loc[horizon_readout['threshold_id'].astype(str).eq(selected)], ['threshold_id', 'cluster_split_bucket', 'horizon_sessions', 'episode_cluster_n', 'median_episode_length_sessions', 'step_n_nonoverlap', 'full_horizon_nonoverlap_step_n', 'partial_tail_step_n', 'coverage_share'], max_rows=20)}

partial tail 只作为 coverage/tail readout，不能作为未来 16B 的完整 continuation labelable step。{short_note}

## 5. Effective Sample Size

overlapping step 的 average uniqueness 在同一 instrument 内计算，跨 instrument 视为独立。non-overlapping step 的 average_uniqueness_nonoverlap 按定义为 1，effective_sample_size_nonoverlap 只计 full-horizon step。

{markdown_table(selected_effective, ['threshold_id', 'cluster_split_bucket', 'horizon_sessions', 'episode_cluster_n', 'step_n_overlap', 'average_uniqueness', 'full_horizon_nonoverlap_step_n', 'effective_sample_size_overlap', 'effective_sample_size_nonoverlap', 'effective_to_anchor_ratio'])}

episode-cluster-blocked 与 time-block 两种去重口径都在 `effective_sample_size_readout.csv` 同表输出。primary train effective_to_anchor_ratio = {d['effective_to_anchor_ratio_train']:.4f}。{sparse_note}

## 6. Episode Cluster Non-overlap Audit

{markdown_table(non_overlap, ['threshold_id', 'cluster_split_bucket', 'instrument_n', 'episode_cluster_n', 'same_threshold_instrument_overlap_pair_n', 'max_same_threshold_instrument_concurrency', 'concurrency_status'])}

同 threshold / instrument 若出现 cluster interval overlap，说明 15B transitive clustering lineage 不可用，必须 fail closed。

## 7. Threshold Sensitivity

{markdown_table(threshold_readout, ['threshold_id', 'primary_horizon_sessions', 'anchor_n', 'episode_cluster_n', 'full_horizon_nonoverlap_step_n', 'effective_sample_size_nonoverlap', 'effective_to_anchor_ratio'])}

三档阈值只分开报告，不得把 `{selected}` 的采样几何外推到 up100pct 或 up150pct。

## 8. 后续边界

recommended_sampling_unit = `{d['recommended_sampling_unit']}`；recommended_horizon_candidate_set = `{d['recommended_horizon_candidate_set']}`。

即使采样几何读数干净，16A 也只可能授权 16B 设计一个新的 sequential continuation label diagnostic。当前所有部署/搜索授权字段均为 false：label_deployment_authorized、signal_search_authorized、model_training_authorized、entry_policy_authorized、separability_search_authorized、sequential_label_authorized。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    publishable = {
        key: value
        for key, value in outputs.items()
        if key != "manifest" and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": r15a.git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": r15a.stable_hash(config),
        "config_file_hash": file_sha(config_path),
        "decision_state": decision,
        "outputs": {key: str(value) for key, value in publishable.items()},
        "output_hashes": {key: file_sha(value) for key, value in publishable.items() if value.is_file()},
    }
    return write_json(path, payload)


def hard_gate_status(
    input_gate: str,
    upstream: pd.DataFrame,
    price: pd.DataFrame,
    adapter: pd.DataFrame,
    rebuild: pd.DataFrame,
    non_overlap: pd.DataFrame,
    effective: pd.DataFrame,
    search: pd.DataFrame,
) -> dict[str, str]:
    return {
        "input_artifact": input_gate,
        "upstream_lineage": status_all(upstream, "lineage_status", {"pass"}),
        "price_path_completeness": status_all(price, "price_path_status", {"pass"}),
        "cluster_interval_adapter": status_all(adapter, "adapter_status", {"pass"}),
        "cluster_interval_rebuild": status_all(rebuild, "rebuild_status", {"pass", "not_required_pass"}),
        "episode_cluster_non_overlap": status_all(non_overlap, "concurrency_status", {"pass_no_same_threshold_overlap"}),
        "geometry_consistency": status_all(effective, "effective_sample_status", {"pass"}),
        "search_accounting": status_all(search, "search_accounting_status", {"pass"}),
    }


def blocked_decision(reason: str, config: dict[str, Any]) -> pd.DataFrame:
    sg = config.get("sampling_geometry", {})
    return pd.DataFrame(
        [
            {
                "decision_state": "16A_blocked_input_or_lineage_failure",
                "next_allowed_requirement": "none",
                "selected_threshold_id": sg.get("selected_threshold_id", "up50pct"),
                "primary_horizon_sessions": sg.get("primary_horizon_sessions", 20),
                "blocking_reason": reason,
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
                "sequential_label_authorized": False,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for directory in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        decision = blocked_decision(input_reason, config)
        write_df(outputs["sampling_geometry_decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, "16A_blocked_input_or_lineage_failure", outputs)
        return 2

    membership = load_membership(resolved["upstream_15b_membership_audit"])
    split_overlap = read_table(resolved["upstream_15b_split_overlap_audit"])
    price_15a = read_table(resolved["upstream_15a_price_path_completeness_audit"])
    price_15b = read_table(resolved["upstream_15b_price_path_completeness_audit"])
    decision_15c2 = read_table(resolved["upstream_15c2_decision"])
    random_15c2 = read_table(resolved["upstream_15c2_membership_vs_random_baseline"])

    upstream = build_upstream_lineage_audit(
        resolved,
        membership,
        split_overlap,
        price_15a,
        price_15b,
        decision_15c2,
        random_15c2,
    )
    adapter = build_cluster_interval_adapter_audit(membership, resolved["upstream_15b_membership_audit"])
    rebuild = build_cluster_interval_rebuild_audit(resolved)
    price = build_price_path_completeness_audit(membership, price_15a, price_15b)
    intervals = build_episode_interval_panel(membership, price, config)
    horizons = [int(x) for x in config["sampling_geometry"]["horizon_grid_sessions"]]
    primary = int(config["sampling_geometry"]["primary_horizon_sessions"])
    steps = build_step_geometry_panel(intervals, horizons)
    sampling_units = build_sampling_unit_count_readout(intervals, primary)
    horizon_readout = build_horizon_grid_step_readout(intervals, steps)
    anchor_overcount = build_anchor_overcount_readout(steps)
    effective = build_effective_sample_size_readout(steps)
    non_overlap = build_episode_cluster_non_overlap_audit(intervals)
    by_split = build_geometry_by_split_readout(effective, config["sampling_geometry"]["selected_threshold_id"], primary)
    by_threshold = build_geometry_by_threshold_sensitivity_readout(effective, primary)
    search = build_search_accounting_audit(config)

    write_df(outputs["upstream_lineage_audit"], upstream)
    write_df(outputs["cluster_interval_adapter_audit"], adapter)
    write_df(outputs["cluster_interval_rebuild_audit"], rebuild)
    write_df(outputs["price_path_completeness_audit"], price)
    write_df(outputs["episode_interval_panel"], intervals)
    write_df(outputs["step_geometry_panel"], steps)
    write_df(outputs["sampling_unit_count_readout"], sampling_units)
    write_df(outputs["horizon_grid_step_readout"], horizon_readout)
    write_df(outputs["anchor_overcount_readout"], anchor_overcount)
    write_df(outputs["effective_sample_size_readout"], effective)
    write_df(outputs["episode_cluster_non_overlap_audit"], non_overlap)
    write_df(outputs["geometry_by_split_readout"], by_split)
    write_df(outputs["geometry_by_threshold_sensitivity_readout"], by_threshold)
    write_df(outputs["search_accounting_audit"], search)

    gates = hard_gate_status(input_gate, upstream, price, adapter, rebuild, non_overlap, effective, search)
    decision = build_sampling_geometry_decision(
        config,
        gates,
        sampling_units,
        anchor_overcount,
        effective,
        horizon_readout,
    )
    write_df(outputs["sampling_geometry_decision"], decision)
    write_text(
        outputs["report"],
        render_report(decision, sampling_units, horizon_readout, effective, non_overlap, by_threshold),
    )
    write_manifest(outputs["manifest"], config_path, config, str(decision.iloc[0]["decision_state"]), outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
