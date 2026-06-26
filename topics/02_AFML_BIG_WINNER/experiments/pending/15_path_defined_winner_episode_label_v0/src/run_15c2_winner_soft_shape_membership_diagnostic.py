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
RUNNER_15B_PATH = EXPERIMENT_DIR / "src" / "run_15b_winner_path_shape_taxonomy_diagnostic.py"
RUNNER_15C_PATH = EXPERIMENT_DIR / "src" / "run_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.py"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_15c2_winner_soft_shape_membership_diagnostic.yaml"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r15b = load_runner(RUNNER_15B_PATH, "run_15b_winner_path_shape_taxonomy_diagnostic_for_15c2")
r15c = load_runner(RUNNER_15C_PATH, "run_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic_for_15c2")

RUN_ID = "15C2_winner_soft_shape_membership_diagnostic"
PHASE_ID = "15C2"
SELECTED_THRESHOLD_ID = "up50pct"
SPLITS = ("train", "validation", "robustness")
PROTOTYPE_TYPES = (
    "smooth_trend_winner",
    "stair_step_winner",
    "jump_repricing_winner",
    "choppy_reversal_winner",
    "slow_grind_winner",
    "late_rescue_winner",
)
CAPTURE_FRIENDLY_TYPES = {"smooth_trend_winner", "stair_step_winner", "slow_grind_winner"}
BASELINE_VARIANTS = (
    "column_shuffle_joint_break",
    "hard_label_permutation_refit",
    "episode_cluster_blocked_shuffle",
)
SHAPE_FEATURES_15C2 = [
    "path_efficiency",
    "max_drawdown_before_hit_abs",
    "underwater_days_share",
    "directional_entropy_5state",
    "trend_line_r2",
    "top1_positive_gain_share",
    "top3_positive_gain_share",
    "pullback_5pct_count",
    "log_time_to_threshold",
]

BASE_REQUIRED_COLUMNS = [
    "source_row_key",
    "threshold_id",
    "instrument",
    "reference_date",
    "row_id",
    "split_bucket",
    "episode_cluster_id",
    "path_winner",
    "is_censored",
    "cluster_split_bucket",
    "touches_multiple_split_buckets",
    "touches_multiple_calendar_split_buckets",
    "max_drawdown_20d",
    "vol_compression_20d_60d",
]
SHAPE_REQUIRED_COLUMNS = [
    "source_row_key",
    "threshold_id",
    "episode_cluster_id",
    "cluster_split_bucket",
    "path_shape_quality",
    "path_type",
    *SHAPE_FEATURES_15C2,
]
FEATURE_PANEL_REQUIRED_COLUMNS = [c for c in SHAPE_REQUIRED_COLUMNS if c != "path_type"]
PHASE_REQUIRED_COLUMNS = [
    "source_row_key",
    "threshold_id",
    "episode_cluster_id",
    "entry_phase_pit",
    "entry_phase_outcome",
    "phase_assignment_status",
    "primary_gate_eligible",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 15C2 winner soft shape membership diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    return r15b.r13a.load_yaml(path)


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
    return (EXPERIMENT_DIR / path).resolve()


def resolve_config_paths(config: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for section in ("inputs", "outputs"):
        for key, value in config.get(section, {}).items():
            paths[key] = topic_path(value)
    return paths


def ensure_output_dirs(paths: dict[str, Path]) -> None:
    for key in ("table_dir", "local_cache_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
    paths["report_path"].parent.mkdir(parents=True, exist_ok=True)
    paths["manifest_path"].parent.mkdir(parents=True, exist_ok=True)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r15b.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r15b.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r15b.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r15b.file_sha(path)


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    try:
        return int(r15c.count_rows(path))
    except Exception:
        return np.nan


def safe_rate(num: Any, den: Any) -> float:
    return r15b.safe_rate(num, den)


def bool_series(series: pd.Series) -> pd.Series:
    return r15b.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def table_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.suffix == ".parquet":
        return list(pd.read_parquet(path).head(0).columns)
    return list(pd.read_csv(path, nrows=0).columns)


def read_table(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    available = table_columns(path)
    usecols = None
    if columns is not None:
        usecols = [col for col in columns if col in available]
    if path.suffix == ".parquet":
        return pd.read_parquet(path, columns=usecols)
    return pd.read_csv(path, usecols=usecols)


def status_from_columns(path: Path, required: list[str]) -> tuple[str, list[str]]:
    if not path.exists():
        return "fail", required
    cols = table_columns(path)
    missing = [col for col in required if col not in cols]
    return ("pass" if not missing else "fail", missing)


def build_input_artifact_audit(paths: dict[str, Path]) -> pd.DataFrame:
    required = {
        "rule_audit_15b": ["rule_type", "feature_id", "value", "scale", "train_rule_fit_status"],
        "winner_episode_cluster_membership_15b": BASE_REQUIRED_COLUMNS,
        "split_overlap_audit_15b": ["episode_cluster_id", "split_overlap_status"],
        "taxonomy_assignment_panel_15b": SHAPE_REQUIRED_COLUMNS,
        "path_shape_feature_panel_15b": FEATURE_PANEL_REQUIRED_COLUMNS,
        "upstream_lineage_audit_15b": ["lineage_status"],
        "price_path_completeness_audit_15b": ["price_path_status"],
        "decision_15c": ["decision_state", "next_allowed_requirement"],
        "entry_phase_assignment_15c": PHASE_REQUIRED_COLUMNS,
        "search_accounting_15c": ["search_accounting_status"],
    }
    roles = {
        "rule_audit_15b": "15B frozen hard taxonomy rule",
        "winner_episode_cluster_membership_15b": "authoritative eligibility, cluster, censoring, and failed-morphology source",
        "split_overlap_audit_15b": "split-boundary proof",
        "taxonomy_assignment_panel_15b": "priority-1 anchor shape feature and hard path_type source",
        "path_shape_feature_panel_15b": "priority-2 fallback shape feature source",
        "upstream_lineage_audit_15b": "15B upstream lineage proof",
        "price_path_completeness_audit_15b": "15B price path proof",
        "decision_15c": "15C descriptive background decision",
        "entry_phase_assignment_15c": "15C entry-phase descriptive stratification source",
        "search_accounting_15c": "15C authorization guard",
    }
    rows = []
    for name, path in paths.items():
        if name not in roles:
            continue
        req = required[name]
        status, missing = status_from_columns(path, req)
        required_flag = name != "path_shape_feature_panel_15b"
        rows.append(
            {
                "artifact_id": name,
                "resolved_path": str(path),
                "required_flag": required_flag,
                "lineage_role": roles[name],
                "row_count": count_rows(path),
                "sha256": file_sha(path),
                "required_columns": "|".join(req),
                "missing_columns": "|".join(missing),
                "schema_status": status if required_flag or path.exists() else "not_required_pass",
                "read_status": status if required_flag or path.exists() else "not_required_pass",
                "input_gate_status": status if required_flag or path.exists() else "not_required_pass",
            }
        )
    return pd.DataFrame(rows)


def build_upstream_lineage_audit(paths: dict[str, Path]) -> pd.DataFrame:
    src = read_table(paths["upstream_lineage_audit_15b"])
    src_status = "pass" if "lineage_status" in src.columns and src["lineage_status"].astype(str).eq("pass").all() else "fail"
    rows = []
    for artifact in ["upstream_lineage_audit_15b", "decision_15c", "entry_phase_assignment_15c", "rule_audit_15b"]:
        rows.append(
            {
                "upstream_artifact_role": artifact,
                "upstream_path": str(paths[artifact]),
                "upstream_sha256": file_sha(paths[artifact]),
                "upstream_row_count": count_rows(paths[artifact]),
                "lineage_claim": "15C2 uses 15B/15C artifacts as inputs only; no label deployment or separability authorization is inherited.",
                "lineage_status": src_status if artifact == "upstream_lineage_audit_15b" else ("pass" if paths[artifact].exists() else "fail"),
            }
        )
    return pd.DataFrame(rows)


def build_price_path_completeness_audit(paths: dict[str, Path]) -> pd.DataFrame:
    src = read_table(paths["price_path_completeness_audit_15b"])
    status = "pass" if "price_path_status" in src.columns and src["price_path_status"].astype(str).eq("pass").all() else "fail"
    return pd.DataFrame(
        [
            {
                "price_path_source": str(paths["price_path_completeness_audit_15b"]),
                "price_path_source_sha256": file_sha(paths["price_path_completeness_audit_15b"]),
                "price_path_source_row_count": len(src),
                "price_path_inheritance_role": "15C2 uses 15B anchor-segment shape features and inherits 15B price path completeness proof.",
                "price_path_status": status,
            }
        ]
    )


def taxonomy_quantiles_from_rule_audit(rule_audit: pd.DataFrame) -> dict[str, float]:
    rows = rule_audit.loc[rule_audit["rule_type"].astype(str).eq("taxonomy_quantile")]
    quantiles: dict[str, float] = {}
    for row in rows.itertuples(index=False):
        name = str(getattr(row, "quantile_name", ""))
        value = pd.to_numeric(getattr(row, "value", np.nan), errors="coerce")
        if name and np.isfinite(value):
            quantiles[name] = float(value)
    return quantiles


def apply_frozen_taxonomy(frame: pd.DataFrame, rule_audit: pd.DataFrame) -> pd.DataFrame:
    quantiles = taxonomy_quantiles_from_rule_audit(rule_audit)
    if not quantiles:
        out = frame.copy()
        out["path_type"] = "data_quality_blocked"
        return out
    return r15b.assign_taxonomy(frame, quantiles)


def read_shape_source(paths: dict[str, Path], rule_audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    source_priority = 0
    source_path = ""
    required_present = False
    duplicate_n = np.nan
    reproducible = False
    shape = pd.DataFrame()
    priority1_attempted = False
    priority1_schema_ok = False
    priority1_hard_fail = False

    if paths["taxonomy_assignment_panel_15b"].exists():
        priority1_attempted = True
        cols = table_columns(paths["taxonomy_assignment_panel_15b"])
        required_present = all(col in cols for col in SHAPE_REQUIRED_COLUMNS)
        priority1_schema_ok = required_present
        if required_present:
            extra = [
                "assignment_unit",
                "segment_start_pos",
                "segment_end_pos",
                "segment_sessions",
                "entry_price",
                "shape_close_start",
                "shape_close_end",
                "max_drawdown_before_hit",
                "time_to_threshold_sessions",
                "large_up_day_count",
            ]
            read_cols = list(dict.fromkeys(SHAPE_REQUIRED_COLUMNS + extra))
            shape = read_table(paths["taxonomy_assignment_panel_15b"], read_cols)
            if "assignment_unit" in shape.columns:
                shape = shape.loc[shape["assignment_unit"].astype(str).eq("anchor_path")].drop(
                    columns=["assignment_unit"]
                )
            duplicate_n = int(shape.duplicated(["source_row_key", "threshold_id"]).sum())
            reproduced = apply_frozen_taxonomy(shape.drop(columns=["path_type"], errors="ignore"), rule_audit)
            reproducible = bool(
                "path_type" in reproduced.columns
                and shape["path_type"].astype(str).reset_index(drop=True).equals(
                    reproduced["path_type"].astype(str).reset_index(drop=True)
                )
            )
            if duplicate_n == 0 and reproducible:
                source_priority = 1
                source_path = str(paths["taxonomy_assignment_panel_15b"])
            else:
                priority1_hard_fail = True

    fallback_allowed = not priority1_attempted or not priority1_schema_ok
    if source_priority == 0 and fallback_allowed and paths["path_shape_feature_panel_15b"].exists():
        cols = table_columns(paths["path_shape_feature_panel_15b"])
        required_present = all(col in cols for col in FEATURE_PANEL_REQUIRED_COLUMNS)
        if required_present:
            extra = [
                "segment_start_pos",
                "segment_end_pos",
                "segment_sessions",
                "entry_price",
                "shape_close_start",
                "shape_close_end",
                "max_drawdown_before_hit",
                "time_to_threshold_sessions",
                "large_up_day_count",
            ]
            read_cols = list(dict.fromkeys(FEATURE_PANEL_REQUIRED_COLUMNS + extra))
            features = read_table(paths["path_shape_feature_panel_15b"], read_cols)
            duplicate_n = int(features.duplicated(["source_row_key", "threshold_id"]).sum())
            shape = apply_frozen_taxonomy(features, rule_audit)
            reproducible = bool("path_type" in shape.columns and shape["path_type"].notna().all())
            if duplicate_n == 0 and reproducible:
                source_priority = 2
                source_path = str(paths["path_shape_feature_panel_15b"])

    if priority1_hard_fail:
        source_priority = 0
        source_path = ""
    adapter_status = "pass" if source_priority in {1, 2} and required_present and duplicate_n == 0 and reproducible else "fail"
    rows.append(
        {
            "source_row_key": "source_row_key",
            "adapter_source_path": source_path,
            "adapter_source_priority": source_priority,
            "adapter_required_columns_present": bool(required_present),
            "adapter_hard_path_type_reproducible": bool(reproducible),
            "adapter_row_count": len(shape),
            "adapter_duplicate_source_row_key_n": duplicate_n,
            "adapter_status": adapter_status,
        }
    )
    rebuild = pd.DataFrame(
        [
            {
                "rebuild_attempted": False,
                "rebuild_status": "not_required_pass" if adapter_status == "pass" else "fail",
                "rebuild_skip_reason": "adapter_or_rule_reproduction_passed"
                if adapter_status == "pass"
                else "priority_3_raw_qfq_rebuild_not_configured",
                "rebuild_formula_source": "15B_frozen_path_shape_formula",
                "rebuild_row_count": 0,
                "rebuild_duplicate_source_row_key_n": 0,
                "rebuild_required_columns_present": adapter_status == "pass",
            }
        ]
    )
    return shape, pd.DataFrame(rows), rebuild


def load_authoritative_panel(paths: dict[str, Path], rule_audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = read_table(paths["winner_episode_cluster_membership_15b"], BASE_REQUIRED_COLUMNS)
    shape, adapter, rebuild = read_shape_source(paths, rule_audit)
    phase = read_table(paths["entry_phase_assignment_15c"], PHASE_REQUIRED_COLUMNS)

    base_dups = int(base.duplicated(["source_row_key", "threshold_id"]).sum())
    shape_dups = int(shape.duplicated(["source_row_key", "threshold_id"]).sum()) if not shape.empty else 1
    phase_dups = int(phase.duplicated(["source_row_key", "threshold_id"]).sum())
    if base_dups or shape_dups or phase_dups:
        adapter.loc[:, "adapter_status"] = "fail"

    panel = base.merge(shape, on=["source_row_key", "threshold_id"], how="inner", suffixes=("", "_shape"))
    phase_cols = [c for c in PHASE_REQUIRED_COLUMNS if c not in {"episode_cluster_id"}]
    panel = panel.merge(phase[phase_cols], on=["source_row_key", "threshold_id"], how="left")

    incompatible_episode = False
    if "episode_cluster_id_shape" in panel.columns:
        incompatible_episode = bool(
            panel["episode_cluster_id_shape"].notna().any()
            and ~panel["episode_cluster_id"].astype(str).eq(panel["episode_cluster_id_shape"].astype(str)).all()
        )
        panel = panel.drop(columns=["episode_cluster_id_shape"])
    if incompatible_episode:
        adapter.loc[:, "adapter_status"] = "fail"

    for col in ["path_winner", "is_censored", "touches_multiple_split_buckets", "touches_multiple_calendar_split_buckets"]:
        panel[col] = bool_series(panel[col])
    panel["path_shape_quality"] = panel["path_shape_quality"].fillna("missing")
    panel["eligible_primary_anchor"] = (
        panel["path_winner"]
        & ~panel["is_censored"]
        & panel["cluster_split_bucket"].isin(SPLITS)
        & ~panel["touches_multiple_split_buckets"]
        & ~panel["touches_multiple_calendar_split_buckets"]
        & panel["path_shape_quality"].eq("pass")
    )
    panel["primary_gate_eligible"] = panel["eligible_primary_anchor"] & panel["threshold_id"].eq(SELECTED_THRESHOLD_ID)
    panel["phase_assignment_status"] = panel["phase_assignment_status"].fillna("missing_phase_assignment")
    return panel, adapter, rebuild


def fit_scaler(fit: pd.DataFrame, features: list[str]) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    scaler: dict[str, dict[str, float]] = {}
    missing_rates: dict[str, float] = {}
    for feature in features:
        values = finite(fit[feature])
        center = float(values.median()) if values.notna().any() else 0.0
        q75 = float(values.quantile(0.75)) if values.notna().any() else 1.0
        q25 = float(values.quantile(0.25)) if values.notna().any() else 0.0
        scale = q75 - q25
        if not np.isfinite(center):
            center = 0.0
        if not np.isfinite(scale) or scale == 0:
            scale = 1.0
        scaler[feature] = {"center": center, "scale": scale}
        missing_rates[feature] = safe_rate(values.isna().sum(), len(values))
    return scaler, missing_rates


def standardize(frame: pd.DataFrame, scaler: dict[str, dict[str, float]], features: list[str]) -> np.ndarray:
    cols = []
    for feature in features:
        values = finite(frame[feature])
        center = scaler[feature]["center"]
        scale = scaler[feature]["scale"]
        values = values.fillna(center)
        cols.append(((values - center) / scale).to_numpy(dtype=float))
    return np.column_stack(cols) if cols else np.empty((len(frame), 0))


def fit_prototypes(
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    config: dict[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    features = list(config["shape_features"])
    z = standardize(fit, scaler, features)
    centers: dict[str, np.ndarray] = {}
    meta: dict[str, dict[str, Any]] = {}
    min_n = int(config["min_prototype_anchor_n"])
    drop_n = int(config["drop_prototype_anchor_n"])
    for proto in config["morphology_prototypes"]:
        mask = fit["path_type"].astype(str).eq(proto).to_numpy()
        n = int(mask.sum())
        dropped = n < drop_n
        under = n < min_n
        if n > 0:
            center = np.nanmedian(z[mask], axis=0)
        else:
            center = np.zeros(z.shape[1], dtype=float)
        if not dropped:
            centers[proto] = center
        meta[proto] = {
            "prototype_train_anchor_n": n,
            "prototype_underpopulated": under,
            "prototype_dropped": dropped,
        }
    return centers, meta


def membership_from_z(
    z: np.ndarray,
    centers: dict[str, np.ndarray],
    temperature: float,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    names = list(centers)
    if not names:
        return np.empty((len(z), 0)), np.empty((len(z), 0)), []
    center_matrix = np.vstack([centers[name] for name in names])
    diff = z[:, None, :] - center_matrix[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    logits = -distances / float(temperature)
    logits = logits - np.nanmax(logits, axis=1, keepdims=True)
    weights = np.exp(logits)
    memberships = weights / np.sum(weights, axis=1, keepdims=True)
    return memberships, distances, names


def entropy_from_membership(membership: np.ndarray) -> np.ndarray:
    if membership.shape[1] <= 1:
        return np.zeros(membership.shape[0], dtype=float)
    clipped = np.clip(membership, 1e-12, 1.0)
    return -(clipped * np.log(clipped)).sum(axis=1) / math.log(membership.shape[1])


def distance_percentiles(
    top_names: np.ndarray,
    top_distances: np.ndarray,
    fit: pd.DataFrame,
    fit_distances: np.ndarray,
    proto_names: list[str],
) -> np.ndarray:
    distributions: dict[str, np.ndarray] = {}
    hard = fit["path_type"].astype(str).to_numpy()
    for idx, proto in enumerate(proto_names):
        vals = fit_distances[hard == proto, idx]
        distributions[proto] = np.sort(vals[np.isfinite(vals)])
    out = np.ones(len(top_distances), dtype=float)
    for proto in proto_names:
        mask = top_names == proto
        vals = distributions.get(proto, np.array([]))
        if mask.any() and len(vals):
            out[mask] = np.searchsorted(vals, top_distances[mask], side="right") / len(vals)
    return out


def build_membership_panel(
    panel: pd.DataFrame,
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    config: dict[str, Any],
    temperature: float,
) -> pd.DataFrame:
    source = panel.loc[panel["eligible_primary_anchor"]].copy()
    features = list(config["shape_features"])
    z = standardize(source, scaler, features)
    fit_z = standardize(fit, scaler, features)
    membership, distances, proto_names = membership_from_z(z, centers, temperature)
    _, fit_distances, _ = membership_from_z(fit_z, centers, temperature)
    if membership.shape[1] == 0:
        raise ValueError("No active membership prototypes.")

    order = np.argsort(-membership, axis=1)
    top1_idx = order[:, 0]
    top2_idx = order[:, 1] if membership.shape[1] > 1 else order[:, 0]
    top1_names = np.array([proto_names[i] for i in top1_idx])
    top2_names = np.array([proto_names[i] for i in top2_idx])
    top1 = membership[np.arange(len(source)), top1_idx]
    top2 = membership[np.arange(len(source)), top2_idx]
    top_dist = distances[np.arange(len(source)), top1_idx]
    percentile = distance_percentiles(top1_names, top_dist, fit, fit_distances, proto_names)
    missing_ratio = source[features].isna().mean(axis=1).to_numpy(dtype=float)
    entropy = entropy_from_membership(membership)
    out = source[
        [
            "source_row_key",
            "threshold_id",
            "instrument",
            "reference_date",
            "row_id",
            "split_bucket",
            "cluster_split_bucket",
            "episode_cluster_id",
            "path_type",
            "path_winner",
            "is_censored",
            "max_drawdown_20d",
            "vol_compression_20d_60d",
            "entry_phase_pit",
            "entry_phase_outcome",
            "phase_assignment_status",
        ]
    ].copy()
    out = out.rename(columns={"path_type": "hard_path_type_15b"})
    out["top1_prototype"] = top1_names
    out["top1_membership"] = top1
    out["top2_prototype"] = top2_names
    out["top2_membership"] = top2
    out["top2_membership_gap"] = top1 - top2
    out["membership_entropy"] = entropy
    out["top1_distance"] = top_dist
    out["top1_distance_percentile"] = percentile
    out["out_of_prototype_residual"] = percentile >= float(config["out_of_prototype_distance_percentile_threshold"])
    out["membership_missing_feature_share"] = missing_ratio
    out["membership_low_confidence"] = missing_ratio > 0.30
    out["sharp_episode"] = (
        (out["membership_entropy"] <= float(config["sharpness_entropy_threshold"]))
        & (out["top1_membership"] >= float(config["sharpness_top1_threshold"]))
        & ~out["membership_low_confidence"]
        & ~out["out_of_prototype_residual"]
    )
    for idx, proto in enumerate(proto_names):
        out[f"membership_{proto}"] = membership[:, idx]
    for proto in config["morphology_prototypes"]:
        col = f"membership_{proto}"
        if col not in out.columns:
            out[col] = 0.0
    return out


def build_rule_audit(
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    missing_rates: dict[str, float],
    centers: dict[str, np.ndarray],
    meta: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    status = "pass" if len(fit) >= 200 and len(centers) >= 4 else "fail"
    scaler_center = json.dumps({k: scaler[k]["center"] for k in config["shape_features"]}, sort_keys=True)
    scaler_scale = json.dumps({k: scaler[k]["scale"] for k in config["shape_features"]}, sort_keys=True)
    missing_policy = json.dumps({"impute_to": "train_median", "missing_rate_by_feature": missing_rates}, sort_keys=True)
    for proto in config["morphology_prototypes"]:
        center = centers.get(proto)
        rows.append(
            {
                "prototype_type": proto,
                "prototype_center_vector": json.dumps(center.tolist() if center is not None else [], sort_keys=True),
                "prototype_train_anchor_n": meta[proto]["prototype_train_anchor_n"],
                "prototype_underpopulated": meta[proto]["prototype_underpopulated"],
                "prototype_dropped": meta[proto]["prototype_dropped"],
                "scaler_center_vector": scaler_center,
                "scaler_scale_vector": scaler_scale,
                "scaler_missing_policy": missing_policy,
                "temperature_primary": float(config["temperature_primary"]),
                "temperature_sensitivity_set": "|".join(str(x) for x in config["temperature_sensitivity_set"]),
                "sharpness_entropy_threshold": float(config["sharpness_entropy_threshold"]),
                "sharpness_top1_threshold": float(config["sharpness_top1_threshold"]),
                "min_prototype_anchor_n": int(config["min_prototype_anchor_n"]),
                "out_of_prototype_distance_percentile_threshold": float(
                    config["out_of_prototype_distance_percentile_threshold"]
                ),
                "random_baseline_seed": int(config["random_baseline_seed"]),
                "random_baseline_repeat_n": int(config["random_baseline_repeat_n"]),
                "baseline_variant_set": "|".join(config["baseline_variant_set"]),
                "membership_prototype_set": "|".join(centers),
                "membership_rule_fit_status": status,
            }
        )
    rows.append(
        {
            "prototype_type": "__global_scaler_temperature_seed__",
            "prototype_center_vector": json.dumps([], sort_keys=True),
            "prototype_train_anchor_n": int(len(fit)),
            "prototype_underpopulated": False,
            "prototype_dropped": True,
            "scaler_center_vector": scaler_center,
            "scaler_scale_vector": scaler_scale,
            "scaler_missing_policy": missing_policy,
            "temperature_primary": float(config["temperature_primary"]),
            "temperature_sensitivity_set": "|".join(str(x) for x in config["temperature_sensitivity_set"]),
            "sharpness_entropy_threshold": float(config["sharpness_entropy_threshold"]),
            "sharpness_top1_threshold": float(config["sharpness_top1_threshold"]),
            "min_prototype_anchor_n": int(config["min_prototype_anchor_n"]),
            "out_of_prototype_distance_percentile_threshold": float(
                config["out_of_prototype_distance_percentile_threshold"]
            ),
            "random_baseline_seed": int(config["random_baseline_seed"]),
            "random_baseline_repeat_n": int(config["random_baseline_repeat_n"]),
            "baseline_variant_set": "|".join(config["baseline_variant_set"]),
            "membership_prototype_set": "|".join(centers),
            "membership_rule_fit_status": status,
        }
    )
    return pd.DataFrame(rows)


def build_prototype_fit_quality(
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    meta: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> pd.DataFrame:
    z = standardize(fit, scaler, list(config["shape_features"]))
    _, distances, proto_names = membership_from_z(z, centers, float(config["temperature_primary"]))
    rows = []
    hard = fit["path_type"].astype(str).to_numpy()
    for proto in config["morphology_prototypes"]:
        if proto in proto_names:
            vals = distances[hard == proto, proto_names.index(proto)]
            vals = vals[np.isfinite(vals)]
        else:
            vals = np.array([])
        dropped = meta[proto]["prototype_dropped"]
        rows.append(
            {
                "threshold_id": SELECTED_THRESHOLD_ID,
                "cluster_split_bucket": "train",
                "prototype_type": proto,
                "prototype_train_anchor_n": meta[proto]["prototype_train_anchor_n"],
                "prototype_underpopulated": meta[proto]["prototype_underpopulated"],
                "prototype_dropped": dropped,
                "median_top1_distance_for_hard_type": float(np.median(vals)) if len(vals) else np.nan,
                "p90_top1_distance_for_hard_type": float(np.quantile(vals, 0.90)) if len(vals) else np.nan,
                "p95_top1_distance_for_hard_type": float(np.quantile(vals, 0.95)) if len(vals) else np.nan,
                "prototype_fit_quality_status": "dropped_not_required" if dropped else ("pass" if len(vals) else "fail"),
            }
        )
    return pd.DataFrame(rows)


def build_prototype_bootstrap_stability(
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    meta: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> pd.DataFrame:
    rng = np.random.default_rng(int(config["random_baseline_seed"]))
    repeat_n = int(config["bootstrap_repeat_n"])
    z = standardize(fit, scaler, list(config["shape_features"]))
    original_membership, _, proto_names = membership_from_z(z, centers, float(config["temperature_primary"]))
    original_top1 = np.argmax(original_membership, axis=1) if original_membership.size else np.array([])
    rows = []
    hard = fit["path_type"].astype(str).to_numpy()
    for proto in config["morphology_prototypes"]:
        if meta[proto]["prototype_dropped"] or proto not in centers:
            rows.append(
                {
                    "threshold_id": SELECTED_THRESHOLD_ID,
                    "prototype_type": proto,
                    "bootstrap_repeat_n": repeat_n,
                    "center_coordinate_median_shift": np.nan,
                    "center_coordinate_p90_shift": np.nan,
                    "top1_assignment_agreement_mean": np.nan,
                    "prototype_stability_status": "dropped_not_required",
                }
            )
            continue
        shifts = []
        agreements = []
        for _ in range(repeat_n):
            bootstrap_centers = dict(centers)
            mask = hard == proto
            idx = np.where(mask)[0]
            sample_idx = rng.choice(idx, size=len(idx), replace=True)
            boot_center = np.nanmedian(z[sample_idx], axis=0)
            bootstrap_centers[proto] = boot_center
            shifts.extend(np.abs(boot_center - centers[proto]).tolist())
            boot_membership, _, _ = membership_from_z(z, bootstrap_centers, float(config["temperature_primary"]))
            agreements.append(float(np.mean(np.argmax(boot_membership, axis=1) == original_top1)))
        rows.append(
            {
                "threshold_id": SELECTED_THRESHOLD_ID,
                "prototype_type": proto,
                "bootstrap_repeat_n": repeat_n,
                "center_coordinate_median_shift": float(np.median(shifts)) if shifts else np.nan,
                "center_coordinate_p90_shift": float(np.quantile(shifts, 0.90)) if shifts else np.nan,
                "top1_assignment_agreement_mean": float(np.mean(agreements)) if agreements else np.nan,
                "prototype_stability_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def aggregate_sharpness(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (threshold, split), sub in panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "anchor_n": int(len(sub)),
                "sharp_share": safe_rate(sub["sharp_episode"].sum(), len(sub)),
                "mean_membership_entropy": float(sub["membership_entropy"].mean()),
                "mean_top1_membership": float(sub["top1_membership"].mean()),
                "mean_top2_membership_gap": float(sub["top2_membership_gap"].mean()),
                "out_of_prototype_residual_share": safe_rate(sub["out_of_prototype_residual"].sum(), len(sub)),
                "low_confidence_share": safe_rate(sub["membership_low_confidence"].sum(), len(sub)),
                "short_path_excluded_share": np.nan,
            }
        )
    return pd.DataFrame(rows)


def membership_metrics(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "sharp_share": safe_rate(frame["sharp_episode"].sum(), len(frame)),
        "mean_membership_entropy": float(frame["membership_entropy"].mean()) if len(frame) else np.nan,
        "mean_top1_membership": float(frame["top1_membership"].mean()) if len(frame) else np.nan,
    }


def synthetic_membership_metrics(
    z: np.ndarray,
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    config: dict[str, Any],
    variant: str,
    rng: np.random.Generator,
) -> dict[str, float]:
    active_centers = centers
    synthetic_z = z.copy()
    if variant == "column_shuffle_joint_break":
        for col in range(synthetic_z.shape[1]):
            synthetic_z[:, col] = rng.permutation(synthetic_z[:, col])
    elif variant == "hard_label_permutation_refit":
        labels = rng.permutation(fit["path_type"].astype(str).to_numpy())
        refit: dict[str, np.ndarray] = {}
        fit_z = standardize(fit, scaler, list(config["shape_features"]))
        for proto in centers:
            mask = labels == proto
            refit[proto] = np.nanmedian(fit_z[mask], axis=0) if mask.sum() else centers[proto]
        active_centers = refit
    elif variant == "episode_cluster_blocked_shuffle":
        clusters = fit["episode_cluster_id"].astype(str).to_numpy()
        synthetic_z = z.copy()
        for cluster in pd.unique(clusters):
            idx = np.where(clusters == cluster)[0]
            if len(idx) > 1:
                synthetic_z[idx] = synthetic_z[rng.permutation(idx)]
    membership, distances, names = membership_from_z(synthetic_z, active_centers, float(config["temperature_primary"]))
    order = np.argsort(-membership, axis=1)
    top1_idx = order[:, 0]
    top2_idx = order[:, 1] if membership.shape[1] > 1 else order[:, 0]
    top1 = membership[np.arange(len(z)), top1_idx]
    top2 = membership[np.arange(len(z)), top2_idx]
    entropy = entropy_from_membership(membership)
    sharp = (entropy <= float(config["sharpness_entropy_threshold"])) & (top1 >= float(config["sharpness_top1_threshold"]))
    return {
        "sharp_share": safe_rate(sharp.sum(), len(sharp)),
        "mean_membership_entropy": float(np.mean(entropy)),
        "mean_top1_membership": float(np.mean(top1)),
        "mean_top2_membership_gap": float(np.mean(top1 - top2)),
    }


def build_random_baseline_readout(
    train_panel: pd.DataFrame,
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    config: dict[str, Any],
) -> pd.DataFrame:
    rng = np.random.default_rng(int(config["random_baseline_seed"]))
    features = list(config["shape_features"])
    z = standardize(fit, scaler, features)
    real = membership_metrics(train_panel)
    rows = []
    repeat_n = int(config["random_baseline_repeat_n"])
    for variant in config["baseline_variant_set"]:
        metrics = [synthetic_membership_metrics(z, fit, scaler, centers, config, variant, rng) for _ in range(repeat_n)]
        sharp_random = float(np.mean([m["sharp_share"] for m in metrics]))
        entropy_random = float(np.mean([m["mean_membership_entropy"] for m in metrics]))
        uplift = real["sharp_share"] - sharp_random
        entropy_reduction = entropy_random - real["mean_membership_entropy"]
        if variant == "column_shuffle_joint_break":
            is_real = uplift >= 0.10 and entropy_reduction >= 0.10
        elif variant == "hard_label_permutation_refit":
            is_real = uplift >= 0.05 and entropy_reduction >= 0.05
        else:
            is_real = uplift >= 0.00
        rows.append(
            {
                "threshold_id": SELECTED_THRESHOLD_ID,
                "cluster_split_bucket": "train",
                "baseline_variant": variant,
                "sharp_share_real": real["sharp_share"],
                "sharp_share_random": sharp_random,
                "sharp_share_uplift": uplift,
                "mean_membership_entropy_real": real["mean_membership_entropy"],
                "mean_membership_entropy_random": entropy_random,
                "membership_entropy_reduction": entropy_reduction,
                "membership_sharpness_is_real": bool(is_real),
                "random_baseline_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_distribution_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (threshold, split), sub in panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        for proto in config["morphology_prototypes"]:
            col = f"membership_{proto}"
            rows.append(
                {
                    "threshold_id": threshold,
                    "cluster_split_bucket": split,
                    "prototype_type": proto,
                    "anchor_n": int(len(sub)),
                    "soft_mass_mean": float(sub[col].mean()),
                    "high_membership_share_50": safe_rate((sub[col] >= 0.50).sum(), len(sub)),
                    "high_membership_share_70": safe_rate((sub[col] >= 0.70).sum(), len(sub)),
                    "top1_share": safe_rate(sub["top1_prototype"].eq(proto).sum(), len(sub)),
                    "hard_path_type_share_15b": safe_rate(sub["hard_path_type_15b"].astype(str).eq(proto).sum(), len(sub)),
                    "distribution_status": "pass",
                }
            )
    return pd.DataFrame(rows)


def build_co_occurrence(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (threshold, split, pair), sub in panel.assign(
        type_pair=lambda x: [
            "|".join(sorted([str(a), str(b)])) for a, b in zip(x["top1_prototype"], x["top2_prototype"])
        ]
    ).groupby(["threshold_id", "cluster_split_bucket", "type_pair"], sort=False):
        total = len(panel.loc[panel["threshold_id"].eq(threshold) & panel["cluster_split_bucket"].eq(split)])
        gap = float(sub["top2_membership_gap"].mean())
        share = safe_rate(len(sub), total)
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "type_pair": pair,
                "anchor_share": share,
                "mean_top2_membership_gap": gap,
                "is_bridge_pair": share >= float(config["bridge_pair_anchor_share_threshold"])
                and gap <= float(config["bridge_pair_gap_threshold"]),
            }
        )
    return pd.DataFrame(rows)


def mean_vector(sub: pd.DataFrame, config: dict[str, Any]) -> str:
    return json.dumps(
        {proto: float(sub[f"membership_{proto}"].mean()) for proto in config["morphology_prototypes"]},
        sort_keys=True,
    )


def build_split_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (threshold, split), sub in panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "anchor_n": int(len(sub)),
                "mean_membership_vector": mean_vector(sub, config),
                "sharp_share": safe_rate(sub["sharp_episode"].sum(), len(sub)),
                "mean_membership_entropy": float(sub["membership_entropy"].mean()),
                "mean_top1_membership": float(sub["top1_membership"].mean()),
                "out_of_prototype_residual_share": safe_rate(sub["out_of_prototype_residual"].sum(), len(sub)),
                "low_confidence_share": safe_rate(sub["membership_low_confidence"].sum(), len(sub)),
                "split_stability_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_threshold_sensitivity(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (threshold, split), sub in panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        sums = {proto: float(sub[f"membership_{proto}"].mean()) for proto in config["morphology_prototypes"]}
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "anchor_n": int(len(sub)),
                "frozen_up50_projection": True,
                "threshold_refit_role": "none_primary_uses_up50_projection",
                "mean_membership_vector": json.dumps(sums, sort_keys=True),
                "top1_prototype_by_soft_mass": max(sums, key=sums.get),
                "sharp_share": safe_rate(sub["sharp_episode"].sum(), len(sub)),
                "mean_membership_entropy": float(sub["membership_entropy"].mean()),
                "out_of_prototype_residual_share": safe_rate(sub["out_of_prototype_residual"].sum(), len(sub)),
                "threshold_sensitivity_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_entry_phase_readout(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for scheme, phase_col in [("pit", "entry_phase_pit"), ("outcome", "entry_phase_outcome")]:
        for (threshold, split, phase), sub in panel.groupby(["threshold_id", "cluster_split_bucket", phase_col], sort=False):
            sums = {proto: float(sub[f"membership_{proto}"].mean()) for proto in config["morphology_prototypes"]}
            rows.append(
                {
                    "threshold_id": threshold,
                    "cluster_split_bucket": split,
                    "phase_scheme": scheme,
                    "entry_phase": phase,
                    "phase_stratification_role": "descriptive_only_not_t0_feature",
                    "anchor_n": int(len(sub)),
                    "mean_membership_vector": json.dumps(sums, sort_keys=True),
                    "top1_prototype_by_soft_mass": max(sums, key=sums.get),
                    "sharp_share": safe_rate(sub["sharp_episode"].sum(), len(sub)),
                    "mean_membership_entropy": float(sub["membership_entropy"].mean()),
                    "out_of_prototype_residual_share": safe_rate(sub["out_of_prototype_residual"].sum(), len(sub)),
                }
            )
    return pd.DataFrame(rows)


def build_cluster_mixture(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (threshold, split, cluster), sub in panel.groupby(["threshold_id", "cluster_split_bucket", "episode_cluster_id"], sort=False):
        vec = {proto: float(sub[f"membership_{proto}"].mean()) for proto in config["morphology_prototypes"]}
        ordered = sorted(vec, key=vec.get, reverse=True)
        values = np.array(list(vec.values()), dtype=float)
        entropy = float(-(values * np.log(np.clip(values, 1e-12, 1))).sum() / math.log(len(values)))
        member_cols = [f"membership_{p}" for p in config["morphology_prototypes"]]
        rows.append(
            {
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "episode_cluster_id": cluster,
                "cluster_anchor_n": int(len(sub)),
                "cluster_mean_membership_vector": json.dumps(vec, sort_keys=True),
                "cluster_top1_prototype": ordered[0],
                "cluster_top2_prototype": ordered[1] if len(ordered) > 1 else ordered[0],
                "cluster_membership_entropy": entropy,
                "cluster_within_membership_dispersion": float(sub[member_cols].std(ddof=0).mean()),
                "cluster_sharp_anchor_share": safe_rate(sub["sharp_episode"].sum(), len(sub)),
                "cluster_out_of_prototype_residual_share": safe_rate(sub["out_of_prototype_residual"].sum(), len(sub)),
            }
        )
    return pd.DataFrame(rows)


def build_known_failed_overlap(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    fit = panel.loc[panel["threshold_id"].eq(SELECTED_THRESHOLD_ID) & panel["cluster_split_bucket"].eq("train")]
    source_ok = bool({"max_drawdown_20d", "vol_compression_20d_60d"}.issubset(panel.columns) and len(fit))
    compression_q20 = float(finite(fit["vol_compression_20d_60d"]).quantile(0.20)) if source_ok else np.nan
    drawdown_q20 = float(finite(fit["max_drawdown_20d"]).quantile(0.20)) if source_ok else np.nan
    state_defs = {
        "compression_state": ("vol_compression_20d_60d", compression_q20),
        "drawdown_reversal_state": ("max_drawdown_20d", drawdown_q20),
    }
    rows = []
    min_n = int(config["known_failed_high_membership_min_n"])
    for (threshold, split), sub in panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        for proto in config["morphology_prototypes"]:
            high = sub.loc[sub[f"membership_{proto}"] >= float(config["high_membership_threshold"])]
            for state, (field, cutoff) in state_defs.items():
                state_all = finite(sub[field]) <= cutoff if source_ok and np.isfinite(cutoff) else pd.Series(False, index=sub.index)
                state_high = finite(high[field]) <= cutoff if source_ok and np.isfinite(cutoff) else pd.Series(False, index=high.index)
                high_share = safe_rate(state_high.sum(), len(high))
                base_share = safe_rate(state_all.sum(), len(sub))
                delta = high_share - base_share if np.isfinite(high_share) and np.isfinite(base_share) else np.nan
                if not source_ok:
                    overlap_status = "source_failure"
                    source_status = "fail"
                elif len(high) < min_n:
                    overlap_status = "inconclusive_too_sparse"
                    source_status = "pass"
                elif delta >= float(config["overlap_tolerance"]):
                    overlap_status = "rediscovered_known_failure"
                    source_status = "pass"
                else:
                    overlap_status = "independent_of_known_failure"
                    source_status = "pass"
                rows.append(
                    {
                        "prototype_type": proto,
                        "cluster_split_bucket": split,
                        "threshold_id": threshold,
                        "state": state,
                        "high_membership_anchor_n": int(len(high)),
                        "high_membership_state_share": high_share,
                        "baseline_state_share": base_share,
                        "share_delta": delta,
                        "overlap_status": overlap_status,
                        "overlap_source_status": source_status,
                    }
                )
    return pd.DataFrame(rows)


def decision_state_from_gates(
    *,
    hard_fail: bool,
    prototype_fit_population_anchor_n: int,
    prototype_population_ok: bool,
    residual_share_ok: bool,
    low_confidence_share_ok: bool,
    temperature_stable: bool,
    sharpness_real: bool,
    morphology_not_all_rediscovered: bool,
    material_sharp_share: bool,
    bridge_information_present: bool,
) -> str:
    if hard_fail:
        return "15C2_blocked_input_or_lineage_failure"
    if (
        prototype_fit_population_anchor_n < 200
        or not prototype_population_ok
        or not residual_share_ok
        or not low_confidence_share_ok
        or not temperature_stable
    ):
        return "15C2_winner_shape_inconclusive_too_sparse_or_unstable"
    if not sharpness_real:
        return "15C2_winner_shape_not_real_over_baselines"
    if not morphology_not_all_rediscovered:
        return "15C2_winner_shape_real_but_overlaps_known_failure"
    if material_sharp_share:
        return "15C2_winner_shape_discrete_descriptive_taxonomy"
    if bridge_information_present:
        return "15C2_winner_shape_continuous_spectrum_descriptive_taxonomy"
    return "15C2_winner_shape_real_but_not_material"


def build_temperature_sensitivity(
    panel_source: pd.DataFrame,
    fit: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    centers: dict[str, np.ndarray],
    config: dict[str, Any],
    decision_context: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    rows = []
    for temp in config["temperature_sensitivity_set"]:
        temp_panel = build_membership_panel(panel_source, fit, scaler, centers, config, float(temp))
        temp_co_occurrence = build_co_occurrence(temp_panel, config)
        for (threshold, split), sub in temp_panel.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
            sharp = safe_rate(sub["sharp_episode"].sum(), len(sub))
            residual_share = safe_rate(sub["out_of_prototype_residual"].sum(), len(sub))
            low_confidence = safe_rate(sub["membership_low_confidence"].sum(), len(sub))
            bridge_pair_n = int(
                temp_co_occurrence.loc[
                    temp_co_occurrence["threshold_id"].eq(threshold)
                    & temp_co_occurrence["cluster_split_bucket"].eq(split)
                    & temp_co_occurrence["is_bridge_pair"],
                ].shape[0]
            )
            decision = decision_state_from_gates(
                hard_fail=False,
                prototype_fit_population_anchor_n=int(decision_context["prototype_fit_population_anchor_n"]),
                prototype_population_ok=bool(decision_context["prototype_population_ok"]),
                residual_share_ok=bool(
                    np.isfinite(residual_share) and residual_share <= float(config["max_residual_share_threshold"])
                ),
                low_confidence_share_ok=bool(
                    np.isfinite(low_confidence)
                    and low_confidence <= float(config["max_low_confidence_share_threshold"])
                ),
                temperature_stable=True,
                sharpness_real=bool(decision_context["sharpness_real"]),
                morphology_not_all_rediscovered=bool(decision_context["morphology_not_all_rediscovered"]),
                material_sharp_share=bool(
                    np.isfinite(sharp) and sharp >= float(config["material_sharp_share_threshold"])
                ),
                bridge_information_present=bridge_pair_n >= 1,
            )
            rows.append(
                {
                    "threshold_id": threshold,
                    "cluster_split_bucket": split,
                    "temperature": float(temp),
                    "anchor_n": int(len(sub)),
                    "sharp_share": sharp,
                    "mean_membership_entropy": float(sub["membership_entropy"].mean()),
                    "mean_top1_membership": float(sub["top1_membership"].mean()),
                    "decision_state_under_temperature": decision,
                    "decision_matches_primary": True,
                    "temperature_sensitivity_status": "pass",
                }
            )
    out = pd.DataFrame(rows)
    primary_temp = float(config["temperature_primary"])
    primary_by_group = {
        (str(row.threshold_id), str(row.cluster_split_bucket)): str(row.decision_state_under_temperature)
        for row in out.loc[out["temperature"].eq(primary_temp)].itertuples(index=False)
    }
    out["decision_matches_primary"] = [
        str(row.decision_state_under_temperature)
        == primary_by_group.get((str(row.threshold_id), str(row.cluster_split_bucket)), "")
        for row in out.itertuples(index=False)
    ]
    group_status = (
        out.groupby(["threshold_id", "cluster_split_bucket"], sort=False)["decision_matches_primary"]
        .all()
        .map(lambda ok: "pass" if bool(ok) else "fail")
        .to_dict()
    )
    out["temperature_sensitivity_status"] = [
        group_status[(row.threshold_id, row.cluster_split_bucket)] for row in out.itertuples(index=False)
    ]
    selected_status = group_status.get((SELECTED_THRESHOLD_ID, "train"), "fail")
    return out, selected_status


def build_stability_gate(
    split_readout: pd.DataFrame,
    threshold_readout: pd.DataFrame,
    temperature_status: str,
    prototype_fit_population_anchor_n: int,
) -> pd.DataFrame:
    split_status = "pass" if set(SPLITS).issubset(set(split_readout["cluster_split_bucket"].dropna().astype(str))) else "fail"
    threshold_status = "pass" if {"up50pct", "up100pct", "up150pct"}.issubset(set(threshold_readout["threshold_id"].dropna().astype(str))) else "fail"
    membership_status = "pass" if split_status == threshold_status == temperature_status == "pass" else "fail"
    return pd.DataFrame(
        [
            {
                "selected_threshold_id": SELECTED_THRESHOLD_ID,
                "prototype_fit_population_anchor_n": int(prototype_fit_population_anchor_n),
                "primary_cluster_split_bucket": "train",
                "validation_cluster_split_bucket": "validation",
                "robustness_cluster_split_bucket": "robustness",
                "split_stability_status": split_status,
                "threshold_sensitivity_status": threshold_status,
                "temperature_stability_status": temperature_status,
                "membership_stability_status": membership_status,
                "stability_gate_status": membership_status,
            }
        ]
    )


def hard_fail_present(*frames: tuple[pd.DataFrame, str, set[str]]) -> bool:
    for frame, column, allow in frames:
        if frame.empty or column not in frame.columns:
            return True
        values = frame[column].dropna().astype(str)
        if values.empty or not values.isin(allow).all():
            return True
    return False


def build_search_accounting(config: dict[str, Any]) -> pd.DataFrame:
    row = {
        "startup_authorization_basis": "15C_real_structure_compressed_by_hard_cut_not_15C_separability_block",
        "manual_research_plan_override": True,
        "selected_threshold_id": SELECTED_THRESHOLD_ID,
        "threshold_selection_source": "inherited_from_15A_lowest_pre_registered_material_censoring_threshold",
        "prototype_fit_split": "train",
        "validation_usage": "frozen_rule_confirmation_no_fit",
        "robustness_usage": "frozen_rule_confirmation_no_fit",
        "membership_method": "rule_distance_softmax",
        "unsupervised_method_role": "exploratory_appendix_not_primary_decision",
        "temperature_primary": float(config["temperature_primary"]),
        "random_baseline_seed": int(config["random_baseline_seed"]),
        "random_baseline_repeat_n": int(config["random_baseline_repeat_n"]),
        "baseline_variant_set": "|".join(config["baseline_variant_set"]),
        "soft_membership_upgradeable_to_t0_feature": False,
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
        "separability_search_authorized": False,
        "prototype_role": "seeded_morphology_prototypes_not_unsupervised_clusters",
        "outcome_entry_phase_role": "descriptive_stratification_not_t0_feature",
        "search_accounting_status": "pass",
    }
    return pd.DataFrame([row])


def build_decision(
    input_audit: pd.DataFrame,
    lineage: pd.DataFrame,
    price_path: pd.DataFrame,
    adapter: pd.DataFrame,
    rebuild: pd.DataFrame,
    rule_audit: pd.DataFrame,
    random_readout: pd.DataFrame,
    fit_quality: pd.DataFrame,
    bootstrap: pd.DataFrame,
    overlap: pd.DataFrame,
    stability: pd.DataFrame,
    search: pd.DataFrame,
    sharpness: pd.DataFrame,
    co_occurrence: pd.DataFrame,
    distribution: pd.DataFrame,
    config: dict[str, Any],
    prototype_fit_population_anchor_n: int,
) -> pd.DataFrame:
    required_inputs = input_audit.loc[input_audit["required_flag"].astype(bool)]
    hard_fail = hard_fail_present(
        (required_inputs, "input_gate_status", {"pass"}),
        (lineage, "lineage_status", {"pass"}),
        (price_path, "price_path_status", {"pass"}),
        (adapter, "adapter_status", {"pass"}),
        (rebuild, "rebuild_status", {"pass", "not_required_pass"}),
        (rule_audit, "membership_rule_fit_status", {"pass"}),
        (random_readout, "random_baseline_status", {"pass"}),
        (fit_quality, "prototype_fit_quality_status", {"pass", "dropped_not_required"}),
        (bootstrap, "prototype_stability_status", {"pass", "dropped_not_required"}),
        (overlap, "overlap_source_status", {"pass"}),
        (search, "search_accounting_status", {"pass"}),
    )
    train = sharpness.loc[sharpness["threshold_id"].eq(SELECTED_THRESHOLD_ID) & sharpness["cluster_split_bucket"].eq("train")]
    sharp_share = float(train["sharp_share"].iloc[0]) if not train.empty else np.nan
    residual_share = float(train["out_of_prototype_residual_share"].iloc[0]) if not train.empty else np.nan
    low_confidence = float(train["low_confidence_share"].iloc[0]) if not train.empty else np.nan
    random_train = random_readout.loc[
        random_readout["threshold_id"].eq(SELECTED_THRESHOLD_ID) & random_readout["cluster_split_bucket"].eq("train")
    ]
    sharpness_real = bool(random_train["membership_sharpness_is_real"].all()) if len(random_train) else False
    bridge_pair_n = int(
        co_occurrence.loc[
            co_occurrence["threshold_id"].eq(SELECTED_THRESHOLD_ID)
            & co_occurrence["cluster_split_bucket"].eq("train")
            & co_occurrence["is_bridge_pair"],
        ].shape[0]
    )
    non_underpop = int((~rule_audit["prototype_underpopulated"].astype(bool) & ~rule_audit["prototype_dropped"].astype(bool)).sum())
    train_overlap = overlap.loc[
        overlap["threshold_id"].eq(SELECTED_THRESHOLD_ID) & overlap["cluster_split_bucket"].eq("train")
    ]
    capture = set(config["capture_friendly_prototypes"])
    capture_rediscovered = []
    for proto in capture:
        sub = train_overlap.loc[train_overlap["prototype_type"].eq(proto)]
        capture_rediscovered.append(bool(sub["overlap_status"].eq("rediscovered_known_failure").any()))
    all_rediscovered = bool(capture_rediscovered and all(capture_rediscovered))
    train_distribution = distribution.loc[
        distribution["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & distribution["cluster_split_bucket"].eq("train")
        & distribution["prototype_type"].isin(config["capture_friendly_prototypes"])
    ]
    capture_soft_mass = float(train_distribution["soft_mass_mean"].sum()) if len(train_distribution) else np.nan
    material = bool(np.isfinite(sharp_share) and sharp_share >= float(config["material_sharp_share_threshold"]))
    residual_ok = bool(np.isfinite(residual_share) and residual_share <= float(config["max_residual_share_threshold"]))
    low_conf_ok = bool(np.isfinite(low_confidence) and low_confidence <= float(config["max_low_confidence_share_threshold"]))
    proto_ok = non_underpop >= 4
    temp_ok = bool(stability["temperature_stability_status"].astype(str).eq("pass").all())
    decision_state = decision_state_from_gates(
        hard_fail=hard_fail,
        prototype_fit_population_anchor_n=int(prototype_fit_population_anchor_n),
        prototype_population_ok=proto_ok,
        residual_share_ok=residual_ok,
        low_confidence_share_ok=low_conf_ok,
        temperature_stable=temp_ok,
        sharpness_real=sharpness_real,
        morphology_not_all_rediscovered=not all_rediscovered,
        material_sharp_share=material,
        bridge_information_present=bridge_pair_n >= 1,
    )

    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": "none",
                "selected_threshold_id": SELECTED_THRESHOLD_ID,
                "prototype_fit_population_anchor_n": int(prototype_fit_population_anchor_n),
                "sharp_share_train": sharp_share,
                "sharp_share_uplift_train": float(random_train["sharp_share_uplift"].min()) if len(random_train) else np.nan,
                "membership_sharpness_is_real_train": sharpness_real,
                "bridge_pair_n": bridge_pair_n,
                "discrete_shape_taxonomy_supported": decision_state == "15C2_winner_shape_discrete_descriptive_taxonomy",
                "continuous_shape_spectrum_supported": decision_state
                == "15C2_winner_shape_continuous_spectrum_descriptive_taxonomy",
                "capture_friendly_prototype_soft_mass_train": capture_soft_mass,
                "capture_friendly_all_rediscovered_known_failure": all_rediscovered,
                "out_of_prototype_residual_share_train": residual_share,
                "low_confidence_share_train": low_confidence,
                "temperature_stability_status": stability["temperature_stability_status"].iloc[0],
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
                "soft_membership_upgradeable_to_t0_feature": False,
                "decision_status": "pass" if not hard_fail else "fail",
            }
        ]
    )


def render_report(
    decision: pd.DataFrame,
    sharpness: pd.DataFrame,
    random_readout: pd.DataFrame,
    distribution: pd.DataFrame,
    entry_phase: pd.DataFrame,
    fit_quality: pd.DataFrame,
    bootstrap: pd.DataFrame,
    co_occurrence: pd.DataFrame,
    split_readout: pd.DataFrame,
    threshold_readout: pd.DataFrame,
    overlap: pd.DataFrame,
    temperature: pd.DataFrame,
    stability: pd.DataFrame,
) -> str:
    def f4(value: Any) -> str:
        num = pd.to_numeric(value, errors="coerce")
        return f"{float(num):.4f}" if np.isfinite(num) else "nan"

    d = decision.iloc[0]
    train = sharpness.loc[sharpness["threshold_id"].eq(SELECTED_THRESHOLD_ID) & sharpness["cluster_split_bucket"].eq("train")]
    t = train.iloc[0] if not train.empty else pd.Series(dtype=object)
    top_proto = distribution.loc[
        distribution["threshold_id"].eq(SELECTED_THRESHOLD_ID) & distribution["cluster_split_bucket"].eq("train")
    ].sort_values("soft_mass_mean", ascending=False)
    top_rows = "\n".join(
        f"| {row.prototype_type} | {f4(row.soft_mass_mean)} | {f4(row.top1_share)} | {f4(row.high_membership_share_50)} |"
        for row in top_proto.itertuples(index=False)
    )
    rand_rows = "\n".join(
        f"| {row.baseline_variant} | {f4(row.sharp_share_real)} | {f4(row.sharp_share_random)} | {f4(row.sharp_share_uplift)} | {f4(row.membership_entropy_reduction)} | {row.membership_sharpness_is_real} |"
        for row in random_readout.itertuples(index=False)
    )
    phase_top = entry_phase.loc[
        entry_phase["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & entry_phase["cluster_split_bucket"].eq("train")
    ].sort_values(["phase_scheme", "anchor_n"], ascending=[True, False]).head(16)
    phase_rows = "\n".join(
        f"| {row.phase_scheme} | {row.entry_phase} | {row.phase_stratification_role} | {row.anchor_n} | {row.top1_prototype_by_soft_mass} | {f4(row.sharp_share)} | {f4(row.out_of_prototype_residual_share)} |"
        for row in phase_top.itertuples(index=False)
    )
    fit_rows = "\n".join(
        f"| {row.prototype_type} | {row.prototype_train_anchor_n} | {row.prototype_underpopulated} | {row.prototype_dropped} | {f4(row.p95_top1_distance_for_hard_type)} | {row.prototype_fit_quality_status} |"
        for row in fit_quality.itertuples(index=False)
    )
    bootstrap_rows = "\n".join(
        f"| {row.prototype_type} | {f4(row.center_coordinate_median_shift)} | {f4(row.center_coordinate_p90_shift)} | {f4(row.top1_assignment_agreement_mean)} | {row.prototype_stability_status} |"
        for row in bootstrap.itertuples(index=False)
    )
    bridge = co_occurrence.loc[
        co_occurrence["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & co_occurrence["cluster_split_bucket"].eq("train")
    ].sort_values(["is_bridge_pair", "anchor_share"], ascending=[False, False]).head(12)
    bridge_rows = "\n".join(
        f"| {row.type_pair} | {f4(row.anchor_share)} | {f4(row.mean_top2_membership_gap)} | {row.is_bridge_pair} |"
        for row in bridge.itertuples(index=False)
    )
    split_rows = "\n".join(
        f"| {row.threshold_id} | {row.cluster_split_bucket} | {row.anchor_n} | {f4(row.sharp_share)} | {f4(row.mean_membership_entropy)} | {f4(row.out_of_prototype_residual_share)} | {f4(row.low_confidence_share)} |"
        for row in split_readout.loc[split_readout["threshold_id"].eq(SELECTED_THRESHOLD_ID)].itertuples(index=False)
    )
    threshold_rows = "\n".join(
        f"| {row.threshold_id} | {row.cluster_split_bucket} | {row.anchor_n} | {row.top1_prototype_by_soft_mass} | {f4(row.sharp_share)} | {f4(row.out_of_prototype_residual_share)} |"
        for row in threshold_readout.loc[threshold_readout["cluster_split_bucket"].eq("train")].itertuples(index=False)
    )
    overlap_rows = "\n".join(
        f"| {row.prototype_type} | {row.state} | {row.high_membership_anchor_n} | {f4(row.high_membership_state_share)} | {f4(row.baseline_state_share)} | {f4(row.share_delta)} | {row.overlap_status} |"
        for row in overlap.loc[
            overlap["threshold_id"].eq(SELECTED_THRESHOLD_ID)
            & overlap["cluster_split_bucket"].eq("train")
            & overlap["prototype_type"].isin(CAPTURE_FRIENDLY_TYPES)
        ].itertuples(index=False)
    )
    temp_rows = "\n".join(
        f"| {row.temperature} | {row.anchor_n} | {f4(row.sharp_share)} | {f4(row.mean_membership_entropy)} | {row.decision_state_under_temperature} | {row.decision_matches_primary} | {row.temperature_sensitivity_status} |"
        for row in temperature.loc[
            temperature["threshold_id"].eq(SELECTED_THRESHOLD_ID)
            & temperature["cluster_split_bucket"].eq("train")
        ].itertuples(index=False)
    )
    s = stability.iloc[0]
    return f"""# 15C2 Winner Soft Shape Membership Diagnostic

## 1. 单行裁决

`decision_state = {d.decision_state}`；`next_allowed_requirement = {d.next_allowed_requirement}`。

15C2 是纯 descriptive label-form diagnostic：它把 winner anchor 投影到 6 个 morphology prototype 的 soft membership 坐标系中，只回答 winner 上涨形态能否被区分。它不授权 t0 feature、signal search、entry policy、model training、separability search 或 label deployment。

| item | value |
|---|---:|
| selected_threshold_id | `{SELECTED_THRESHOLD_ID}` |
| prototype_fit_population_anchor_n | {int(d.prototype_fit_population_anchor_n)} |
| sharp_share_train | {float(d.sharp_share_train):.4f} |
| residual_share_train | {float(d.out_of_prototype_residual_share_train):.4f} |
| low_confidence_share_train | {float(d.low_confidence_share_train):.4f} |
| bridge_pair_n | {int(d.bridge_pair_n)} |
| temperature_stability_status | `{d.temperature_stability_status}` |

## 2. 启动依据与边界

15C 的 `next_allowed_requirement = none` 阻断的是 separability、signal search 和 t0 feature search，不是阻断一个纯 descriptive 的 label-form 诊断。15C2 的 override basis 是：15C 已经显示 outcome-relative entry phase 存在真实结构，但硬分类和 t0 可知性约束把大量边界 episode 压成 mixed。15C2 因此只把 15B morphology hard type 软化为 6 维 membership vector，不把结果解释成可交易信号。

`startup_authorization_basis = 15C_real_structure_compressed_by_hard_cut_not_15C_separability_block`。本报告所有 phase / threshold / split 分层都只是已发生 winner path 的描述，不改变 `soft_membership_upgradeable_to_t0_feature = false`。

## 3. 方法与 Train-Only 冻结

15C2 从 up50 train eligible anchors 拟合 scaler 与 prototype center：每个 feature 用 train median / IQR 标准化，每个 prototype center 是对应 15B hard path type 的标准化中位向量。每个 anchor 到各 prototype 的欧氏距离经 `softmax(-distance / temperature)` 转为 membership；`mixed` / `unclassified` 不进入 membership 维度，只保留 residual / low-confidence readout。

## 4. Prototype Fit Quality

| prototype | train anchors | underpopulated | dropped | p95 hard-type distance | fit status |
|---|---:|---|---|---:|---|
{fit_rows}

Bootstrap stability：

| prototype | median center shift | p90 center shift | top1 agreement | status |
|---|---:|---:|---:|---|
{bootstrap_rows}

## 5. Primary Sharpness

| metric | value |
|---|---:|
| anchor_n | {int(t.get('anchor_n', 0)) if len(t) else 0} |
| sharp_share | {float(t.get('sharp_share', np.nan)):.4f} |
| mean_membership_entropy | {float(t.get('mean_membership_entropy', np.nan)):.4f} |
| mean_top1_membership | {float(t.get('mean_top1_membership', np.nan)):.4f} |
| out_of_prototype_residual_share | {float(t.get('out_of_prototype_residual_share', np.nan)):.4f} |
| low_confidence_share | {float(t.get('low_confidence_share', np.nan)):.4f} |

`out_of_prototype_residual` 衡量 anchor 是否离所有原型都远；它保留 membership vector，但不能计入 sharp numerator。`membership_low_confidence` 由 shape feature 缺失比例触发，同样不进入 sharp numerator。

## 6. Random / Permutation Baselines

| baseline | real sharp | random sharp | sharp uplift | entropy reduction | pass |
|---|---:|---:|---:|---:|---|
{rand_rows}

这些 baseline 分别检查 feature joint structure、hard label 与 prototype 的真实对应关系、以及 cluster duplication 是否制造虚假尖锐度。若任一 primary baseline 不支持，positive shape taxonomy 不能成立。

## 7. Train Prototype Soft Mass

| prototype | soft mass mean | top1 share | high membership >= 0.50 |
|---|---:|---:|---:|
{top_rows}

## 8. Entry Phase 分层

PIT 与 outcome phase 都只作为 descriptive stratification；尤其 outcome phase 使用未来 cluster interval，永远不能升级为 t0 feature。

| phase scheme | entry phase | role | anchors | top prototype | sharp share | residual share |
|---|---|---|---:|---|---:|---:|
{phase_rows}

## 9. Path-Type 共现谱

| type pair | anchor share | mean top2 gap | bridge pair |
|---|---:|---:|---|
{bridge_rows}

`is_bridge_pair = true` 表示一批 winner anchor 真实处在两个 morphology prototype 之间，这正是硬分类里 mixed 被压扁的信息。

## 10. Split 与 Threshold Sensitivity

Up50 split confirmation：

| threshold | split | anchors | sharp share | entropy | residual share | low confidence |
|---|---|---:|---:|---:|---:|---:|
{split_rows}

Train threshold projection（全部使用 up50 train 冻结 scaler / prototype，不允许 threshold refit 改变 primary decision）：

| threshold | split | anchors | top prototype | sharp share | residual share |
|---|---|---:|---|---:|---:|
{threshold_rows}

## 11. Known-Failure Overlap

| prototype | state | high-member n | high state share | baseline share | delta | status |
|---|---|---:|---:|---:|---:|---|
{overlap_rows}

如果 capture-friendly prototypes 全部只是 compression / drawdown-reversal 的换名，即使 soft membership 看起来真实，也只能降级为 known-failure overlap。

## 12. Temperature Stability

| temperature | anchors | sharp share | entropy | decision under temperature | matches primary | status |
|---:|---:|---:|---:|---|---|---|
{temp_rows}

| gate | value |
|---|---|
| split_stability_status | `{s.split_stability_status}` |
| threshold_sensitivity_status | `{s.threshold_sensitivity_status}` |
| temperature_stability_status | `{s.temperature_stability_status}` |
| membership_stability_status | `{s.membership_stability_status}` |

## 13. Findings

1. 15C2 使用 15B frozen morphology prototypes，避免重新搜索形态定义。
2. `out_of_prototype_residual` 单独衡量 anchor 是否远离所有原型，避免 softmax 强行分类。
3. 多重 baseline 同时检查 softmax geometry、prototype label 偶然性和 cluster duplication。
4. 本实验即使给出正向 taxonomy，也只是 winner 形态图谱，不是 t0 可预测性证据。

## 14. 最终授权边界

无论 decision state 如何，15C2 均不授权 label deployment、signal search、entry / exit / holding policy、model training、separability search，或把 soft membership / entry phase 分层升级为 t0 feature。`next_allowed_requirement` 保持 `none`。
"""


def write_manifest(paths: dict[str, Path], output_files: dict[str, Path], decision: pd.DataFrame) -> None:
    payload = {
        "run_id": RUN_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "decision_state": decision["decision_state"].iloc[0],
        "next_allowed_requirement": decision["next_allowed_requirement"].iloc[0],
        "outputs": {
            name: {
                "path": str(path),
                "sha256": file_sha(path),
                "row_count": count_rows(path) if path.suffix in {".csv", ".parquet"} else np.nan,
            }
            for name, path in sorted(output_files.items())
        },
    }
    write_json(paths["manifest_path"], payload)


def output_paths(paths: dict[str, Path]) -> dict[str, Path]:
    table = paths["table_dir"]
    cache = paths["local_cache_dir"]
    return {
        "input_artifact_audit": table / "input_artifact_audit.csv",
        "upstream_lineage_audit": table / "upstream_lineage_audit.csv",
        "price_path_completeness_audit": table / "price_path_completeness_audit.csv",
        "shape_feature_adapter_audit": table / "shape_feature_adapter_audit.csv",
        "shape_feature_rebuild_audit": table / "shape_feature_rebuild_audit.csv",
        "shape_membership_rule_audit": table / "shape_membership_rule_audit.csv",
        "prototype_fit_quality_readout": table / "prototype_fit_quality_readout.csv",
        "prototype_bootstrap_stability_readout": table / "prototype_bootstrap_stability_readout.csv",
        "anchor_soft_membership_panel": table / "anchor_soft_membership_panel.csv",
        "episode_cluster_soft_membership_mixture_readout": table / "episode_cluster_soft_membership_mixture_readout.csv",
        "soft_membership_distribution_readout": table / "soft_membership_distribution_readout.csv",
        "sharpness_readout": table / "sharpness_readout.csv",
        "membership_vs_random_baseline_readout": table / "membership_vs_random_baseline_readout.csv",
        "path_type_co_occurrence_readout": table / "path_type_co_occurrence_readout.csv",
        "known_failed_morphology_overlap_readout": table / "known_failed_morphology_overlap_readout.csv",
        "membership_by_split_readout": table / "membership_by_split_readout.csv",
        "membership_by_threshold_sensitivity_readout": table / "membership_by_threshold_sensitivity_readout.csv",
        "membership_by_entry_phase_readout": table / "membership_by_entry_phase_readout.csv",
        "temperature_sensitivity_readout": table / "temperature_sensitivity_readout.csv",
        "membership_stability_gate": table / "membership_stability_gate.csv",
        "winner_soft_shape_membership_decision": table / "winner_soft_shape_membership_decision.csv",
        "search_accounting_audit": table / "search_accounting_audit.csv",
        "anchor_soft_membership_panel_cache": cache / "anchor_soft_membership_panel.parquet",
        "random_baseline_membership_panel_cache": cache / "random_baseline_membership_panel.parquet",
        "report": paths["report_path"],
        "manifest": paths["manifest_path"],
    }


def run(config_path: Path, check_inputs_only: bool = False) -> dict[str, Path]:
    config = load_config(config_path)
    paths = resolve_config_paths(config)
    ensure_output_dirs(paths)
    outs = output_paths(paths)

    input_audit = build_input_artifact_audit(paths)
    write_df(outs["input_artifact_audit"], input_audit)
    if check_inputs_only:
        return {"input_artifact_audit": outs["input_artifact_audit"]}

    rule_15b = read_table(paths["rule_audit_15b"])
    lineage = build_upstream_lineage_audit(paths)
    price_path = build_price_path_completeness_audit(paths)
    panel, adapter, rebuild = load_authoritative_panel(paths, rule_15b)
    fit = panel.loc[
        panel["eligible_primary_anchor"]
        & panel["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & panel["cluster_split_bucket"].eq("train")
    ].copy()

    scaler, missing_rates = fit_scaler(fit, list(config["shape_features"]))
    centers, proto_meta = fit_prototypes(fit, scaler, config)
    membership_panel = build_membership_panel(panel, fit, scaler, centers, config, float(config["temperature_primary"]))
    train_panel = membership_panel.loc[
        membership_panel["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & membership_panel["cluster_split_bucket"].eq("train")
    ].copy()

    rule_audit = build_rule_audit(fit, scaler, missing_rates, centers, proto_meta, config)
    fit_quality = build_prototype_fit_quality(fit, scaler, centers, proto_meta, config)
    bootstrap = build_prototype_bootstrap_stability(fit, scaler, centers, proto_meta, config)
    sharpness = aggregate_sharpness(membership_panel)
    random_readout = build_random_baseline_readout(train_panel, fit, scaler, centers, config)
    distribution = build_distribution_readout(membership_panel, config)
    co_occurrence = build_co_occurrence(membership_panel, config)
    split_readout = build_split_readout(membership_panel, config)
    threshold_readout = build_threshold_sensitivity(membership_panel, config)
    entry_phase = build_entry_phase_readout(membership_panel, config)
    cluster_mixture = build_cluster_mixture(membership_panel, config)
    overlap = build_known_failed_overlap(membership_panel, config)
    prototype_fit_population_anchor_n = int(len(fit))
    non_underpop = int(
        sum(
            not bool(meta["prototype_underpopulated"]) and not bool(meta["prototype_dropped"])
            for meta in proto_meta.values()
        )
    )
    random_train = random_readout.loc[
        random_readout["threshold_id"].eq(SELECTED_THRESHOLD_ID)
        & random_readout["cluster_split_bucket"].eq("train")
    ]
    train_overlap = overlap.loc[
        overlap["threshold_id"].eq(SELECTED_THRESHOLD_ID) & overlap["cluster_split_bucket"].eq("train")
    ]
    capture_rediscovered = []
    for proto in config["capture_friendly_prototypes"]:
        sub = train_overlap.loc[train_overlap["prototype_type"].eq(proto)]
        capture_rediscovered.append(bool(sub["overlap_status"].eq("rediscovered_known_failure").any()))
    decision_context = {
        "prototype_fit_population_anchor_n": prototype_fit_population_anchor_n,
        "prototype_population_ok": non_underpop >= 4,
        "sharpness_real": bool(random_train["membership_sharpness_is_real"].all()) if len(random_train) else False,
        "morphology_not_all_rediscovered": not bool(capture_rediscovered and all(capture_rediscovered)),
    }
    temp_readout, temp_status = build_temperature_sensitivity(panel, fit, scaler, centers, config, decision_context)
    stability = build_stability_gate(split_readout, threshold_readout, temp_status, prototype_fit_population_anchor_n)
    search = build_search_accounting(config)
    decision = build_decision(
        input_audit,
        lineage,
        price_path,
        adapter,
        rebuild,
        rule_audit,
        random_readout,
        fit_quality,
        bootstrap,
        overlap,
        stability,
        search,
        sharpness,
        co_occurrence,
        distribution,
        config,
        prototype_fit_population_anchor_n,
    )
    report = render_report(
        decision,
        sharpness,
        random_readout,
        distribution,
        entry_phase,
        fit_quality,
        bootstrap,
        co_occurrence,
        split_readout,
        threshold_readout,
        overlap,
        temp_readout,
        stability,
    )

    frames = {
        "upstream_lineage_audit": lineage,
        "price_path_completeness_audit": price_path,
        "shape_feature_adapter_audit": adapter,
        "shape_feature_rebuild_audit": rebuild,
        "shape_membership_rule_audit": rule_audit,
        "prototype_fit_quality_readout": fit_quality,
        "prototype_bootstrap_stability_readout": bootstrap,
        "anchor_soft_membership_panel": membership_panel,
        "episode_cluster_soft_membership_mixture_readout": cluster_mixture,
        "soft_membership_distribution_readout": distribution,
        "sharpness_readout": sharpness,
        "membership_vs_random_baseline_readout": random_readout,
        "path_type_co_occurrence_readout": co_occurrence,
        "known_failed_morphology_overlap_readout": overlap,
        "membership_by_split_readout": split_readout,
        "membership_by_threshold_sensitivity_readout": threshold_readout,
        "membership_by_entry_phase_readout": entry_phase,
        "temperature_sensitivity_readout": temp_readout,
        "membership_stability_gate": stability,
        "winner_soft_shape_membership_decision": decision,
        "search_accounting_audit": search,
    }
    output_files: dict[str, Path] = {"input_artifact_audit": outs["input_artifact_audit"]}
    for name, frame in frames.items():
        output_files[name] = write_df(outs[name], frame)
    membership_panel.to_parquet(outs["anchor_soft_membership_panel_cache"], index=False)
    pd.DataFrame({"baseline_variant": config["baseline_variant_set"]}).to_parquet(
        outs["random_baseline_membership_panel_cache"], index=False
    )
    output_files["anchor_soft_membership_panel_cache"] = outs["anchor_soft_membership_panel_cache"]
    output_files["random_baseline_membership_panel_cache"] = outs["random_baseline_membership_panel_cache"]
    output_files["report"] = write_text(outs["report"], report)
    write_manifest(paths, output_files, decision)
    output_files["manifest"] = outs["manifest"]
    return output_files


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check_only = args.check_inputs_only or args.mode == "check-inputs"
    outputs = run(Path(args.config), check_inputs_only=check_only)
    print(json.dumps({k: str(v) for k, v in outputs.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
