#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
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
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.yaml"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r15b = load_runner(RUNNER_15B_PATH, "run_15b_winner_path_shape_taxonomy_diagnostic_for_15c")

RUN_ID = "15C_winner_entry_phase_and_mixture_taxonomy_diagnostic"
PHASE_ID = "15C"
SELECTED_THRESHOLD_ID = "up50pct"
SPLITS = ("train", "validation", "robustness")
READOUT_SPLITS = ("train", "validation", "robustness")
PHASE_SCHEMES = ("pit", "outcome")
CAPTURE_FRIENDLY_TYPES = {"smooth_trend_winner", "stair_step_winner", "slow_grind_winner"}
UNRESOLVED_TYPES = {"unclassified_short_path", "unclassified_mixed_path", "data_quality_blocked"}
MIXED_SUBTYPE = "mixed_episode_winner"
SPARSE_SUBTYPE = "sparse_phase_subgroup"
PIT_PHASES = ("late_chase_pit", "breakout_pit", "early_base_pit", "mid_trend_pit", "undetermined_pit")
OUTCOME_PHASES = ("early_cluster_entry", "mid_cluster_entry", "breakout_cluster_entry", "late_cluster_entry")

MEDOID_FEATURES_15B = [
    "path_efficiency",
    "max_drawdown_before_hit_abs",
    "underwater_days_share",
    "directional_entropy_5state",
    "trend_line_r2",
    "top1_positive_gain_share",
    "top3_positive_gain_share",
    "log_time_to_threshold",
]

PIT_FEATURES = [
    "ret_60d",
    "distance_to_60d_high",
    "distance_to_20d_low",
    "trend_ma_20_60_spread",
]

TAXONOMY_REQUIRED_COLUMNS = [
    "source_row_key",
    "instrument",
    "reference_date",
    "row_id",
    "split_bucket",
    "threshold_id",
    "threshold_return",
    "episode_cluster_id",
    "cluster_split_bucket",
    "touches_multiple_split_buckets",
    "touches_multiple_calendar_split_buckets",
    "entry_pos",
    "first_threshold_hit_pos",
    "segment_start_pos",
    "segment_end_pos",
    "entry_price",
    "time_to_threshold_sessions",
    "path_efficiency",
    "max_drawdown_before_hit",
    "max_drawdown_before_hit_abs",
    "underwater_days_share",
    "directional_entropy_5state",
    "trend_line_r2",
    "top1_positive_gain_share",
    "top3_positive_gain_share",
    "log_time_to_threshold",
    "path_type",
    "path_shape_quality",
    "wick_hit_only",
]

TAXONOMY_OPTIONAL_COLUMNS = [
    "assignment_unit",
    "segment_sessions",
    "shape_close_start",
    "shape_close_end",
    "large_up_day_count",
    "pullback_5pct_count",
]

MEMBERSHIP_COLUMNS = [
    "source_row_key",
    "instrument",
    "reference_date",
    "row_id",
    "split_bucket",
    "threshold_id",
    "path_winner",
    "is_censored",
    "episode_cluster_id",
    "cluster_start_pos",
    "cluster_end_pos",
    "cluster_split_bucket",
    "touches_multiple_split_buckets",
    "touches_multiple_calendar_split_buckets",
    "ret_20d",
    "ret_60d",
    "distance_to_20d_high",
    "distance_to_20d_low",
    "distance_to_60d_high",
    "trend_ma_20_60_spread",
    "rebound_from_20d_low",
    "vol_compression_20d_60d",
    "volatility_20d",
]

NATIVE_COLUMNS = [
    "instrument",
    "reference_date",
    "row_id",
    "reference_pos",
    "ret_20d",
    "ret_60d",
    "distance_to_20d_high",
    "distance_to_20d_low",
    "distance_to_60d_high",
    "trend_ma_20_60_spread",
    "rebound_from_20d_low",
    "vol_compression_20d_60d",
    "volatility_20d",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 15C winner entry-phase and mixture taxonomy diagnostic.")
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


def stable_hash(value: Any) -> str:
    return r15b.stable_hash(value)


def safe_rate(num: Any, den: Any) -> float:
    return r15b.safe_rate(num, den)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def bool_series(series: pd.Series) -> pd.Series:
    return r15b.bool_series(series)


def table_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.suffix == ".parquet":
        return list(pd.read_parquet(path).head(0).columns)
    return list(pd.read_csv(path, nrows=0).columns)


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    try:
        return int(r15b.r15a.count_rows(path))
    except Exception:
        try:
            if path.suffix == ".parquet":
                return int(len(pd.read_parquet(path, columns=[])))
            return int(sum(1 for _ in path.open("rb")) - 1)
        except Exception:
            return np.nan


def read_table_columns(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    available = table_columns(path)
    usecols = None
    if columns is not None:
        usecols = [col for col in columns if col in available]
    if path.suffix == ".parquet":
        return pd.read_parquet(path, columns=usecols)
    return pd.read_csv(path, usecols=usecols)


def input_status(path: Path, required_columns: list[str]) -> tuple[str, str, list[str]]:
    if not path.exists():
        return "fail", "missing_artifact", required_columns
    cols = table_columns(path)
    missing = [col for col in required_columns if col not in cols]
    if missing:
        return "fail", "missing_required_columns", missing
    return "pass", "", []


def build_input_artifact_audit(paths: dict[str, Path]) -> pd.DataFrame:
    required: dict[str, list[str]] = {
        "decision_15b": ["decision_state", "next_allowed_requirement"],
        "rule_audit_15b": ["rule_type", "feature_id", "value", "scale", "train_rule_fit_status"],
        "taxonomy_assignment_panel_15b": TAXONOMY_REQUIRED_COLUMNS,
        "winner_episode_cluster_membership_15b": MEMBERSHIP_COLUMNS,
        "representative_audit_15b": [
            "threshold_id",
            "episode_cluster_id",
            "representative_taxonomy_disagreement",
            "cluster_internal_path_type_entropy",
        ],
        "split_overlap_audit_15b": ["episode_cluster_id", "split_overlap_status"],
        "upstream_lineage_audit_15b": ["lineage_status"],
        "price_path_completeness_audit_15b": ["price_path_status"],
        "search_accounting_15b": ["search_accounting_status"],
        "native_universe_panel_13a": NATIVE_COLUMNS,
    }
    roles = {
        "decision_15b": "15B background decision guard",
        "rule_audit_15b": "15B frozen taxonomy rule and medoid scaler",
        "taxonomy_assignment_panel_15b": "15B anchor-level path type source priority 1",
        "winner_episode_cluster_membership_15b": "cluster interval and split-boundary proof",
        "representative_audit_15b": "15B representative disagreement baseline",
        "split_overlap_audit_15b": "split boundary proof",
        "upstream_lineage_audit_15b": "15B inherited upstream lineage proof",
        "price_path_completeness_audit_15b": "15B inherited price path proof",
        "search_accounting_15b": "15B search accounting guard",
        "path_shape_feature_panel_15b": "fallback priority 2 anchor feature source",
        "native_universe_panel_13a": "PIT-observable morphology source",
        "config_15b": "15B config lineage",
    }
    rows: list[dict[str, Any]] = []
    for name in paths:
        if name not in roles:
            continue
        req = required.get(name, [])
        status, reason, missing = input_status(paths[name], req)
        rows.append(
            {
                "artifact_id": name,
                "resolved_path": str(paths[name]),
                "required_flag": name != "path_shape_feature_panel_15b",
                "lineage_role": roles[name],
                "row_count": count_rows(paths[name]) if paths[name].exists() else np.nan,
                "sha256": file_sha(paths[name]),
                "required_columns": "|".join(req),
                "missing_columns": "|".join(missing),
                "schema_status": status,
                "read_status": status,
                "input_gate_status": status,
                "blocking_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def build_upstream_lineage_audit(paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    lineage = read_table_columns(paths["upstream_lineage_audit_15b"])
    status = "pass" if "lineage_status" in lineage.columns and lineage["lineage_status"].eq("pass").all() else "fail"
    for artifact in ["upstream_lineage_audit_15b", "decision_15b", "rule_audit_15b", "native_universe_panel_13a"]:
        rows.append(
            {
                "upstream_artifact_role": artifact,
                "upstream_path": str(paths[artifact]),
                "upstream_sha256": file_sha(paths[artifact]),
                "upstream_row_count": count_rows(paths[artifact]),
                "lineage_claim": "15C inherits row lineage, split boundaries, episode clustering, and anchor-level path-quality only as inputs; it does not inherit 15B decision authorization.",
                "lineage_status": status if artifact == "upstream_lineage_audit_15b" else ("pass" if paths[artifact].exists() else "fail"),
                "blocking_reason": "" if paths[artifact].exists() and status == "pass" else "missing_or_failed_upstream_lineage",
            }
        )
    return pd.DataFrame(rows)


def build_price_path_completeness_audit(paths: dict[str, Path]) -> pd.DataFrame:
    src = read_table_columns(paths["price_path_completeness_audit_15b"])
    status = "pass" if "price_path_status" in src.columns and src["price_path_status"].eq("pass").all() else "fail"
    return pd.DataFrame(
        [
            {
                "price_path_source": str(paths["price_path_completeness_audit_15b"]),
                "price_path_source_sha256": file_sha(paths["price_path_completeness_audit_15b"]),
                "price_path_source_row_count": len(src),
                "price_path_inheritance_role": "15C reuses 15B anchor-level path-quality and therefore inherits 15B publishable price path completeness proof.",
                "price_path_status": status,
                "blocking_reason": "" if status == "pass" else "15b_price_path_proof_failed",
            }
        ]
    )


def load_medoid_scaler(rule_audit: pd.DataFrame) -> dict[str, dict[str, float]]:
    rows = rule_audit.loc[rule_audit["rule_type"].eq("medoid_scaler")]
    scaler: dict[str, dict[str, float]] = {}
    for feature in MEDOID_FEATURES_15B:
        sub = rows.loc[rows["feature_id"].eq(feature)]
        if sub.empty:
            scaler[feature] = {"center": 0.0, "scale": 1.0}
            continue
        center = float(pd.to_numeric(sub["value"], errors="coerce").iloc[0])
        scale = float(pd.to_numeric(sub["scale"], errors="coerce").iloc[0])
        if not np.isfinite(scale) or scale == 0:
            scale = 1.0
        if not np.isfinite(center):
            center = 0.0
        scaler[feature] = {"center": center, "scale": scale}
    return scaler


def taxonomy_quantiles_from_rule_audit(rule_audit: pd.DataFrame) -> dict[str, float]:
    quantile_rows = rule_audit.loc[rule_audit["rule_type"].eq("taxonomy_quantile")]
    quantiles: dict[str, float] = {}
    for row in quantile_rows.itertuples(index=False):
        name = str(getattr(row, "quantile_name", ""))
        value = pd.to_numeric(getattr(row, "value", np.nan), errors="coerce")
        if name and np.isfinite(value):
            quantiles[name] = float(value)
    return quantiles


def apply_frozen_15b_taxonomy(frame: pd.DataFrame, rule_audit: pd.DataFrame) -> pd.DataFrame:
    quantiles = taxonomy_quantiles_from_rule_audit(rule_audit)
    if not quantiles:
        out = frame.copy()
        out["path_type"] = "data_quality_blocked"
        return out
    return r15b.assign_taxonomy(frame, quantiles)


def read_priority_1_taxonomy(paths: dict[str, Path], rule_audit: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    path = paths["taxonomy_assignment_panel_15b"]
    meta: dict[str, Any] = {
        "source_path": str(path),
        "source_priority": 1,
        "required_present": False,
        "duplicate_n": np.nan,
        "reproducible": False,
        "status": "fail",
    }
    if not path.exists():
        return None, meta
    available = table_columns(path)
    if not all(col in available for col in TAXONOMY_REQUIRED_COLUMNS):
        return None, meta
    taxonomy_cols = [col for col in TAXONOMY_REQUIRED_COLUMNS + TAXONOMY_OPTIONAL_COLUMNS if col in available]
    taxonomy = read_table_columns(path, taxonomy_cols)
    if "assignment_unit" in taxonomy.columns:
        taxonomy = taxonomy.loc[taxonomy["assignment_unit"].eq("anchor_path")].copy()
    duplicate_n = int(taxonomy["source_row_key"].duplicated().sum()) if "source_row_key" in taxonomy.columns else len(taxonomy)
    reproduced = apply_frozen_15b_taxonomy(taxonomy.drop(columns=["path_type"], errors="ignore"), rule_audit)
    reproducible = bool("path_type" in reproduced.columns and taxonomy["path_type"].astype(str).reset_index(drop=True).equals(reproduced["path_type"].astype(str).reset_index(drop=True)))
    meta.update(
        {
            "required_present": True,
            "duplicate_n": duplicate_n,
            "reproducible": reproducible,
            "status": "pass" if duplicate_n == 0 and reproducible else "fail",
        }
    )
    return taxonomy if meta["status"] == "pass" else None, meta


def read_priority_2_feature_panel(paths: dict[str, Path], rule_audit: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    path = paths["path_shape_feature_panel_15b"]
    meta: dict[str, Any] = {
        "source_path": str(path),
        "source_priority": 2,
        "required_present": False,
        "duplicate_n": np.nan,
        "reproducible": False,
        "status": "fail",
    }
    if not path.exists():
        return None, meta
    required = [col for col in TAXONOMY_REQUIRED_COLUMNS if col != "path_type"]
    available = table_columns(path)
    if not all(col in available for col in required):
        return None, meta
    feature_cols = [col for col in required + TAXONOMY_OPTIONAL_COLUMNS if col in available and col != "assignment_unit"]
    features = read_table_columns(path, feature_cols)
    duplicate_n = int(features["source_row_key"].duplicated().sum()) if "source_row_key" in features.columns else len(features)
    assigned = apply_frozen_15b_taxonomy(features, rule_audit)
    assigned["assignment_unit"] = "anchor_path"
    reproducible = "path_type" in assigned.columns and assigned["path_type"].notna().all()
    meta.update(
        {
            "required_present": True,
            "duplicate_n": duplicate_n,
            "reproducible": bool(reproducible),
            "status": "pass" if duplicate_n == 0 and reproducible else "fail",
        }
    )
    return assigned if meta["status"] == "pass" else None, meta


def load_taxonomy_anchor_panel(paths: dict[str, Path], rule_audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    taxonomy, meta = read_priority_1_taxonomy(paths, rule_audit)
    rebuild_attempted = False
    rebuild_status = "not_required_pass"
    rebuild_skip_reason = "adapter_or_rule_reproduction_passed"
    if taxonomy is None:
        taxonomy, meta = read_priority_2_feature_panel(paths, rule_audit)
        if taxonomy is not None:
            rebuild_status = "not_required_pass"
            rebuild_skip_reason = "adapter_or_rule_reproduction_passed"
    if taxonomy is None:
        rebuild_attempted = True
        rebuild_status = "fail"
        rebuild_skip_reason = "priority_3_raw_qfq_rebuild_not_configured"
        taxonomy = pd.DataFrame(columns=TAXONOMY_REQUIRED_COLUMNS + TAXONOMY_OPTIONAL_COLUMNS)
    membership = read_table_columns(paths["winner_episode_cluster_membership_15b"], MEMBERSHIP_COLUMNS)
    native = read_table_columns(paths["native_universe_panel_13a"], NATIVE_COLUMNS)

    duplicate_n = int(taxonomy["source_row_key"].duplicated().sum()) if "source_row_key" in taxonomy.columns else len(taxonomy)
    required_present = all(col in taxonomy.columns for col in TAXONOMY_REQUIRED_COLUMNS)

    membership_cols = [
        "source_row_key",
        "path_winner",
        "is_censored",
        "cluster_start_pos",
        "cluster_end_pos",
        "touches_multiple_split_buckets",
        "touches_multiple_calendar_split_buckets",
        "ret_20d",
        "ret_60d",
        "distance_to_20d_high",
        "distance_to_20d_low",
        "distance_to_60d_high",
        "trend_ma_20_60_spread",
        "rebound_from_20d_low",
        "vol_compression_20d_60d",
        "volatility_20d",
    ]
    merged = taxonomy.merge(
        membership[[col for col in membership_cols if col in membership.columns]],
        on="source_row_key",
        how="left",
        suffixes=("", "_membership"),
    )
    for col in ["cluster_start_pos", "cluster_end_pos", "touches_multiple_split_buckets", "touches_multiple_calendar_split_buckets"]:
        alt = f"{col}_membership"
        if alt in merged.columns:
            merged[col] = merged[col].where(merged[col].notna(), merged[alt]) if col in merged.columns else merged[alt]

    native_key = ["instrument", "reference_date", "row_id"]
    native = native.drop_duplicates(native_key).copy()
    native_rename = {col: f"{col}_native" for col in NATIVE_COLUMNS if col not in native_key}
    merged = merged.merge(native.rename(columns=native_rename), on=native_key, how="left")
    for col in [c for c in NATIVE_COLUMNS if c not in native_key]:
        native_col = f"{col}_native"
        if native_col in merged.columns:
            merged[col] = merged[native_col].where(merged[native_col].notna(), merged.get(col))

    merged["path_winner"] = bool_series(merged.get("path_winner", pd.Series(False, index=merged.index)))
    merged["is_censored"] = bool_series(merged.get("is_censored", pd.Series(False, index=merged.index)))
    merged["touches_multiple_split_buckets"] = bool_series(merged["touches_multiple_split_buckets"])
    merged["touches_multiple_calendar_split_buckets"] = bool_series(merged["touches_multiple_calendar_split_buckets"])
    merged["path_shape_quality"] = merged["path_shape_quality"].fillna("missing_path_shape_quality")
    merged["path_type"] = merged["path_type"].fillna("data_quality_blocked")
    merged["eligible_primary_anchor"] = (
        merged["path_winner"]
        & ~merged["is_censored"]
        & merged["cluster_split_bucket"].isin(SPLITS)
        & ~merged["touches_multiple_split_buckets"]
        & ~merged["touches_multiple_calendar_split_buckets"]
        & merged["path_shape_quality"].eq("pass")
    )
    merged["primary_gate_eligible"] = merged["eligible_primary_anchor"] & merged["threshold_id"].eq(SELECTED_THRESHOLD_ID)

    interval_backfilled = merged[["cluster_start_pos", "cluster_end_pos"]].notna().all(axis=1).all()
    rule_status = "pass" if rule_audit.get("train_rule_fit_status", pd.Series(["fail"])).eq("pass").all() else "fail"
    adapter_status = "pass" if required_present and duplicate_n == 0 and interval_backfilled and rule_status == "pass" and bool(meta["reproducible"]) else "fail"
    adapter_audit = pd.DataFrame(
        [
            {
                "source_row_key": "source_row_key",
                "adapter_source_path": meta["source_path"],
                "adapter_source_priority": meta["source_priority"],
                "adapter_required_columns_present": bool(required_present),
                "adapter_anchor_path_type_reproducible": bool(meta["reproducible"]) and rule_status == "pass",
                "adapter_cluster_interval_backfilled": bool(interval_backfilled),
                "adapter_row_count": len(merged),
                "adapter_duplicate_source_row_key_n": duplicate_n,
                "adapter_status": adapter_status,
            }
        ]
    )
    rebuild_audit = pd.DataFrame(
        [
            {
                "rebuild_attempted": rebuild_attempted,
                "rebuild_status": rebuild_status if adapter_status == "pass" or rebuild_attempted else "fail",
                "rebuild_skip_reason": rebuild_skip_reason if adapter_status == "pass" or rebuild_attempted else "adapter_failed_priority_3_not_attempted",
                "rebuild_formula_source": "15B_frozen_path_shape_formula",
                "rebuild_row_count": 0 if not rebuild_attempted else len(merged),
                "rebuild_duplicate_source_row_key_n": 0,
                "rebuild_required_columns_present": True,
            }
        ]
    )
    return merged, adapter_audit, rebuild_audit


def fit_pit_quantiles(anchor: pd.DataFrame, selected_threshold_id: str) -> dict[str, float]:
    fit = anchor.loc[
        anchor["eligible_primary_anchor"]
        & anchor["threshold_id"].eq(selected_threshold_id)
        & anchor["cluster_split_bucket"].eq("train")
    ]
    return {
        "q_ret60d_30": float(finite(fit["ret_60d"]).quantile(0.30)),
        "q_ret60d_50": float(finite(fit["ret_60d"]).quantile(0.50)),
        "q_ret60d_70": float(finite(fit["ret_60d"]).quantile(0.70)),
        "q_distance_to_60d_high_70": float(finite(fit["distance_to_60d_high"]).quantile(0.70)),
        "q_distance_to_60d_high_90": float(finite(fit["distance_to_60d_high"]).quantile(0.90)),
        "q_distance_to_20d_low_30": float(finite(fit["distance_to_20d_low"]).quantile(0.30)),
        "q_distance_to_20d_low_70": float(finite(fit["distance_to_20d_low"]).quantile(0.70)),
        "q_trend_ma_20_60_spread_50": float(finite(fit["trend_ma_20_60_spread"]).quantile(0.50)),
    }


def assign_pit_phase(frame: pd.DataFrame, quantiles: dict[str, float]) -> pd.DataFrame:
    out = frame.copy()
    for col in PIT_FEATURES:
        out[col] = finite(out[col])
    missing = out[PIT_FEATURES].isna().any(axis=1)
    late_raw = (out["ret_60d"] >= quantiles["q_ret60d_70"]) & (
        out["distance_to_20d_low"] >= quantiles["q_distance_to_20d_low_70"]
    )
    breakout_raw = out["distance_to_60d_high"] >= quantiles["q_distance_to_60d_high_90"]
    early_raw = (
        (out["ret_60d"] <= quantiles["q_ret60d_30"])
        & (out["distance_to_20d_low"] <= quantiles["q_distance_to_20d_low_30"])
        & (out["distance_to_60d_high"] < quantiles["q_distance_to_60d_high_70"])
    )
    mid_raw = (
        (out["ret_60d"] > quantiles["q_ret60d_50"])
        & (out["trend_ma_20_60_spread"] >= quantiles["q_trend_ma_20_60_spread_50"])
        & (out["distance_to_60d_high"] < quantiles["q_distance_to_60d_high_90"])
    )
    breakout = breakout_raw & ~late_raw
    mid = mid_raw & ~late_raw & ~breakout
    phase = pd.Series("undetermined_pit", index=out.index, dtype="object")
    phase = phase.mask(mid & ~missing, "mid_trend_pit")
    phase = phase.mask(early_raw & ~missing, "early_base_pit")
    phase = phase.mask(breakout & ~missing, "breakout_pit")
    phase = phase.mask(late_raw & ~missing, "late_chase_pit")

    hits = []
    for late, breakout_hit, early, mid_hit, miss in zip(late_raw, breakout_raw, early_raw, mid_raw, missing):
        if miss:
            hits.append("")
            continue
        names = []
        if late:
            names.append("late_chase_pit")
        if breakout_hit:
            names.append("breakout_pit")
        if early:
            names.append("early_base_pit")
        if mid_hit:
            names.append("mid_trend_pit")
        hits.append("|".join(names))
    out["entry_phase_pit"] = phase
    out["entry_phase_pit_predicate_hits"] = hits
    out["entry_phase_pit_missing_feature_flag"] = missing
    out["entry_phase_pit_conflict_flag"] = [len(x.split("|")) > 1 if x else False for x in hits]
    return out


def assign_outcome_phase(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    entry = finite(out["entry_pos"])
    start = finite(out["cluster_start_pos"])
    end = finite(out["cluster_end_pos"])
    denom = (end - start).clip(lower=1)
    progress = (entry - start) / denom
    out["cluster_progress"] = progress.clip(lower=0, upper=1)
    phase = pd.Series("late_cluster_entry", index=out.index, dtype="object")
    phase = phase.mask(out["cluster_progress"] <= 0.80, "breakout_cluster_entry")
    phase = phase.mask(out["cluster_progress"] <= 0.60, "mid_cluster_entry")
    phase = phase.mask(out["cluster_progress"] <= 0.25, "early_cluster_entry")
    phase = phase.mask(out["cluster_progress"].isna(), "late_cluster_entry")
    out["entry_phase_outcome"] = phase
    return out


def build_entry_phase_rule_audit(anchor: pd.DataFrame, quantiles: dict[str, float], config: dict[str, Any]) -> pd.DataFrame:
    fit_filter = (
        "eligible_primary_anchor and threshold_id == selected_threshold_id and "
        "cluster_split_bucket == train; cross_split and boundary-touching clusters excluded"
    )
    fit = anchor.loc[
        anchor["eligible_primary_anchor"]
        & anchor["threshold_id"].eq(config["selected_threshold_id"])
        & anchor["cluster_split_bucket"].eq("train")
    ]
    cross_in_fit = int(fit["cluster_split_bucket"].eq("cross_split").sum()) if "cluster_split_bucket" in fit.columns else 1
    quantile_finite = all(np.isfinite(value) for value in quantiles.values())
    status = "pass" if len(fit) > 0 and cross_in_fit == 0 and quantile_finite else "fail"
    rows: list[dict[str, Any]] = []
    predicate_map = {
        "predicate_late_chase_pit": "ret_60d >= q_ret60d_70 and distance_to_20d_low >= q_distance_to_20d_low_70",
        "predicate_breakout_pit": "distance_to_60d_high >= q_distance_to_60d_high_90 and not predicate_late_chase_pit",
        "predicate_early_base_pit": "ret_60d <= q_ret60d_30 and distance_to_20d_low <= q_distance_to_20d_low_30 and distance_to_60d_high < q_distance_to_60d_high_70",
        "predicate_mid_trend_pit": "ret_60d > q_ret60d_50 and trend_ma_20_60_spread >= q_trend_ma_20_60_spread_50 and distance_to_60d_high < q_distance_to_60d_high_90 and not predicate_late_chase_pit and not predicate_breakout_pit",
    }
    priority = {
        "predicate_late_chase_pit": 1,
        "predicate_breakout_pit": 2,
        "predicate_early_base_pit": 3,
        "predicate_mid_trend_pit": 4,
    }
    for q_name, value in quantiles.items():
        feature = q_name.replace("q_", "")
        rows.append(
            {
                "phase_scheme": "pit",
                "rule_id": q_name,
                "fit_split": "train",
                "fit_population_filter": fit_filter,
                "fit_population_n": len(fit),
                "feature_id": feature,
                "quantile_name": q_name,
                "quantile_value": value,
                "predicate_expression": "",
                "predicate_priority": np.nan,
                "missing_feature_count": int(fit[PIT_FEATURES].isna().any(axis=1).sum()) if len(fit) else 0,
                "conflict_policy": "priority_order_late_breakout_early_mid_undetermined",
                "upgradeable_to_t0_feature": True,
                "cross_split_excluded_from_fit": cross_in_fit == 0,
                "entry_phase_rule_fit_status": status,
                "entry_phase_provenance_status": "pass",
            }
        )
    for rule_id, expression in predicate_map.items():
        rows.append(
            {
                "phase_scheme": "pit",
                "rule_id": rule_id,
                "fit_split": "train",
                "fit_population_filter": fit_filter,
                "fit_population_n": len(fit),
                "feature_id": "PIT_morphology_bundle",
                "quantile_name": "",
                "quantile_value": np.nan,
                "predicate_expression": expression,
                "predicate_priority": priority[rule_id],
                "missing_feature_count": int(fit[PIT_FEATURES].isna().any(axis=1).sum()) if len(fit) else 0,
                "conflict_policy": "priority_order_late_breakout_early_mid_undetermined",
                "upgradeable_to_t0_feature": True,
                "cross_split_excluded_from_fit": cross_in_fit == 0,
                "entry_phase_rule_fit_status": status,
                "entry_phase_provenance_status": "pass",
            }
        )
    rows.append(
        {
            "phase_scheme": "outcome",
            "rule_id": "cluster_progress_cutoffs",
            "fit_split": "train",
            "fit_population_filter": "deterministic descriptor; no fit; cross_split excluded from support gates",
            "fit_population_n": 0,
            "feature_id": "cluster_progress",
            "quantile_name": "",
            "quantile_value": np.nan,
            "predicate_expression": "progress <= 0.25 / <= 0.60 / <= 0.80 / > 0.80",
            "predicate_priority": 1,
            "missing_feature_count": int(anchor[["entry_pos", "cluster_start_pos", "cluster_end_pos"]].isna().any(axis=1).sum()),
            "conflict_policy": "closed_intervals_ordered_by_cutoff",
            "upgradeable_to_t0_feature": False,
            "cross_split_excluded_from_fit": True,
            "entry_phase_rule_fit_status": status,
            "entry_phase_provenance_status": "pass",
        }
    )
    return pd.DataFrame(rows)


def build_entry_phase_assignment_readout(anchor: pd.DataFrame) -> pd.DataFrame:
    out = anchor.copy()
    out["entry_phase_pit_upgradeable_to_t0_feature"] = True
    out["entry_phase_outcome_upgradeable_to_t0_feature"] = False
    out["phase_assignment_status"] = np.where(
        out[["entry_phase_pit", "entry_phase_outcome", "cluster_start_pos", "cluster_end_pos"]].notna().all(axis=1),
        "pass",
        "fail",
    )
    cols = [
        "source_row_key",
        "threshold_id",
        "instrument",
        "reference_date",
        "row_id",
        "split_bucket",
        "cluster_split_bucket",
        "episode_cluster_id",
        "entry_pos",
        "cluster_start_pos",
        "cluster_end_pos",
        "entry_phase_pit",
        "entry_phase_pit_predicate_hits",
        "entry_phase_pit_missing_feature_flag",
        "entry_phase_outcome",
        "cluster_progress",
        "entry_phase_pit_upgradeable_to_t0_feature",
        "entry_phase_outcome_upgradeable_to_t0_feature",
        "phase_assignment_status",
        "primary_gate_eligible",
    ]
    return out[[col for col in cols if col in out.columns]].copy()


def path_type_distribution(path_types: pd.Series) -> tuple[dict[str, float], str, float, int, float]:
    counts = path_types.fillna("data_quality_blocked").astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return {}, "", np.nan, 0, np.nan
    shares = (counts / total).to_dict()
    dominant = str(counts.idxmax())
    dominant_share = float(counts.max() / total)
    distinct = int((counts > 0).sum())
    p = counts.to_numpy(dtype=float) / total
    entropy = float(-(p * np.log(p)).sum() / math.log(max(distinct, 2))) if distinct > 1 else 0.0
    return shares, dominant, dominant_share, distinct, entropy


def subtype_from_dominant(anchor_n: int, dominant_path_type: str, dominant_share: float, threshold: float, min_anchor_n: int) -> str:
    if anchor_n < min_anchor_n:
        return SPARSE_SUBTYPE
    if dominant_share >= threshold and dominant_path_type not in UNRESOLVED_TYPES:
        return dominant_path_type
    return MIXED_SUBTYPE


def select_subgroup_medoid(group: pd.DataFrame, scaler: dict[str, dict[str, float]]) -> pd.Series:
    if len(group) == 1:
        return group.iloc[0]
    matrix = r15b.standardized_matrix(group, scaler, MEDOID_FEATURES_15B)
    median_vec = np.nanmedian(matrix, axis=0)
    distances = np.sqrt(np.sum((matrix - median_vec) ** 2, axis=1))
    work = group.copy()
    work["_medoid_distance_15c"] = distances
    return work.sort_values(["_medoid_distance_15c", "time_to_threshold_sessions", "entry_pos", "row_id"], kind="stable").iloc[0]


def build_phase_conditioned_mixture(
    anchor: pd.DataFrame,
    scaler: dict[str, dict[str, float]],
    dominant_threshold: float,
    sensitivity_threshold: float,
    min_anchor_n: int,
) -> pd.DataFrame:
    source = anchor.loc[anchor["eligible_primary_anchor"]].copy()
    rows: list[dict[str, Any]] = []
    for scheme, phase_col in [("pit", "entry_phase_pit"), ("outcome", "entry_phase_outcome")]:
        keys = ["threshold_id", "cluster_split_bucket", phase_col, "episode_cluster_id"]
        for (threshold_id, split_bucket, phase_value, cluster_id), group in source.groupby(keys, sort=False, dropna=False):
            shares, dominant, dominant_share, distinct, entropy = path_type_distribution(group["path_type"])
            earliest = group.sort_values(["entry_pos", "row_id"], kind="stable").iloc[0]
            shortest = group.sort_values(["time_to_threshold_sessions", "entry_pos", "row_id"], kind="stable").iloc[0]
            medoid = select_subgroup_medoid(group, scaler)
            rep_types = {
                str(earliest["path_type"]),
                str(shortest["path_type"]),
                str(medoid["path_type"]),
            }
            anchor_n = int(len(group))
            if scheme == "pit" and phase_value == "undetermined_pit" and anchor_n >= min_anchor_n:
                subtype_070 = MIXED_SUBTYPE
                subtype_075 = MIXED_SUBTYPE
                subtype_status = "pass_undetermined_pit_residual"
            else:
                subtype_070 = subtype_from_dominant(anchor_n, dominant, dominant_share, dominant_threshold, min_anchor_n)
                subtype_075 = subtype_from_dominant(anchor_n, dominant, dominant_share, sensitivity_threshold, min_anchor_n)
                subtype_status = "pass"
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "split_bucket": split_bucket,
                    "phase_scheme": scheme,
                    "entry_phase_value": phase_value,
                    "episode_cluster_id": cluster_id,
                    "anchor_n": anchor_n,
                    "eligible_phase_subgroup": bool(anchor_n >= min_anchor_n and split_bucket in SPLITS),
                    "sparse_phase_subgroup": bool(anchor_n < min_anchor_n),
                    "distinct_path_type_n": distinct,
                    "path_type_distribution_vector": json.dumps(shares, sort_keys=True),
                    "dominant_path_type": dominant,
                    "dominant_share": dominant_share,
                    "internal_entropy": entropy,
                    "subgroup_earliest_anchor_path_type": earliest["path_type"],
                    "subgroup_shortest_duration_anchor_path_type": shortest["path_type"],
                    "subgroup_medoid_anchor_path_type": medoid["path_type"],
                    "subgroup_representative_disagreement": len(rep_types) > 1,
                    "subtype_0p70": subtype_070,
                    "subtype_0p75": subtype_075,
                    "subtype_assignment_status": subtype_status,
                }
            )
    return pd.DataFrame(rows)


def aggregate_weighted_metrics(mixture: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (threshold_id, split_bucket, scheme), sub in mixture.groupby(["threshold_id", "split_bucket", "phase_scheme"], sort=False):
        total_anchor = sub["anchor_n"].sum()
        eligible = sub.loc[sub["eligible_phase_subgroup"]]
        eligible_weight = eligible["anchor_n"].sum()
        rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "phase_scheme": scheme,
                "eligible_phase_subgroup_n": int(len(eligible)),
                "mean_dominant_share_phase": safe_rate((eligible["dominant_share"] * eligible["anchor_n"]).sum(), eligible_weight),
                "mean_internal_entropy_phase": safe_rate((eligible["internal_entropy"] * eligible["anchor_n"]).sum(), eligible_weight),
                "sparse_phase_subgroup_share": safe_rate(sub.loc[sub["sparse_phase_subgroup"], "anchor_n"].sum(), total_anchor),
            }
        )
    return pd.DataFrame(rows)


def random_partition_summary(path_types: np.ndarray, size_profile: list[int], rng: np.random.Generator, min_anchor_n: int) -> dict[str, float]:
    permuted = rng.permutation(path_types)
    offset = 0
    dominant_weighted = 0.0
    entropy_weighted = 0.0
    eligible_weight = 0
    sparse_weight = 0
    total_weight = int(sum(size_profile))
    for size in size_profile:
        chunk = pd.Series(permuted[offset : offset + size])
        offset += size
        if size < min_anchor_n:
            sparse_weight += size
            continue
        _, _, dominant_share, _, entropy = path_type_distribution(chunk)
        dominant_weighted += dominant_share * size
        entropy_weighted += entropy * size
        eligible_weight += size
    return {
        "mean_dominant_share_random": safe_rate(dominant_weighted, eligible_weight),
        "mean_internal_entropy_random": safe_rate(entropy_weighted, eligible_weight),
        "sparse_phase_subgroup_share_random": safe_rate(sparse_weight, total_weight),
        "eligible_random_anchor_n": eligible_weight,
    }


def build_random_baseline(
    anchor: pd.DataFrame,
    mixture: pd.DataFrame,
    random_seed: int,
    repeat_n: int,
    min_anchor_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = anchor.loc[anchor["eligible_primary_anchor"]].copy()
    rng = np.random.default_rng(random_seed)
    rows: list[dict[str, Any]] = []
    for (threshold_id, split_bucket, scheme, cluster_id), sub_mix in mixture.groupby(
        ["threshold_id", "split_bucket", "phase_scheme", "episode_cluster_id"], sort=False
    ):
        group = source.loc[
            source["threshold_id"].eq(threshold_id)
            & source["cluster_split_bucket"].eq(split_bucket)
            & source["episode_cluster_id"].eq(cluster_id)
        ]
        if group.empty:
            continue
        size_profile = sub_mix["anchor_n"].astype(int).tolist()
        path_types = group["path_type"].astype(str).to_numpy()
        for repeat_idx in range(repeat_n):
            metrics = random_partition_summary(path_types, size_profile, rng, min_anchor_n)
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "split_bucket": split_bucket,
                    "phase_scheme": scheme,
                    "episode_cluster_id": cluster_id,
                    "random_repeat_idx": repeat_idx,
                    "size_profile": "|".join(str(x) for x in size_profile),
                    **metrics,
                }
            )
    random_panel = pd.DataFrame(rows)
    real = aggregate_weighted_metrics(mixture)
    rand_rows: list[dict[str, Any]] = []
    if not random_panel.empty:
        for keys, sub in random_panel.groupby(["threshold_id", "split_bucket", "phase_scheme", "random_repeat_idx"], sort=False):
            threshold_id, split_bucket, scheme, repeat_idx = keys
            weight = sub["eligible_random_anchor_n"].sum()
            rand_rows.append(
                {
                    "threshold_id": threshold_id,
                    "split_bucket": split_bucket,
                    "phase_scheme": scheme,
                    "random_repeat_idx": repeat_idx,
                    "mean_dominant_share_random": safe_rate(
                        (sub["mean_dominant_share_random"] * sub["eligible_random_anchor_n"]).sum(), weight
                    ),
                    "mean_internal_entropy_random": safe_rate(
                        (sub["mean_internal_entropy_random"] * sub["eligible_random_anchor_n"]).sum(), weight
                    ),
                }
            )
    rand_agg = pd.DataFrame(rand_rows)
    if rand_agg.empty:
        readout = real.copy()
        readout["mean_dominant_share_random"] = np.nan
        readout["mean_internal_entropy_random"] = np.nan
    else:
        rand_mean = (
            rand_agg.groupby(["threshold_id", "split_bucket", "phase_scheme"], sort=False)[
                ["mean_dominant_share_random", "mean_internal_entropy_random"]
            ]
            .mean()
            .reset_index()
        )
        readout = real.merge(rand_mean, on=["threshold_id", "split_bucket", "phase_scheme"], how="left")
    readout["dominant_share_uplift_vs_random"] = readout["mean_dominant_share_phase"] - readout["mean_dominant_share_random"]
    readout["internal_entropy_reduction_vs_random"] = readout["mean_internal_entropy_random"] - readout["mean_internal_entropy_phase"]
    readout["phase_split_is_real"] = (
        readout["dominant_share_uplift_vs_random"].ge(0.10) & readout["internal_entropy_reduction_vs_random"].ge(0.10)
    )
    readout["primary_support_gate_threshold"] = readout["threshold_id"].eq(SELECTED_THRESHOLD_ID)
    readout["random_baseline_seed"] = random_seed
    readout["random_baseline_repeat_n"] = repeat_n
    readout["min_phase_subgroup_anchor_n"] = min_anchor_n
    readout["subgroup_weighting"] = "anchor_weighted"
    readout["random_baseline_status"] = "pass"
    cols = [
        "threshold_id",
        "split_bucket",
        "phase_scheme",
        "primary_support_gate_threshold",
        "random_baseline_seed",
        "random_baseline_repeat_n",
        "min_phase_subgroup_anchor_n",
        "subgroup_weighting",
        "eligible_phase_subgroup_n",
        "mean_dominant_share_phase",
        "mean_dominant_share_random",
        "dominant_share_uplift_vs_random",
        "mean_internal_entropy_phase",
        "mean_internal_entropy_random",
        "internal_entropy_reduction_vs_random",
        "sparse_phase_subgroup_share",
        "phase_split_is_real",
        "random_baseline_status",
    ]
    return random_panel, readout[cols]


def build_disagreement_readout(mixture: pd.DataFrame, representative: pd.DataFrame) -> pd.DataFrame:
    rep = representative[
        [
            "threshold_id",
            "episode_cluster_id",
            "representative_taxonomy_disagreement",
            "cluster_internal_path_type_entropy",
        ]
    ].copy()
    rep["representative_taxonomy_disagreement"] = bool_series(rep["representative_taxonomy_disagreement"])
    work = mixture.merge(rep, on=["threshold_id", "episode_cluster_id"], how="left")
    rows: list[dict[str, Any]] = []
    for (threshold_id, split_bucket, scheme), sub in work.groupby(["threshold_id", "split_bucket", "phase_scheme"], sort=False):
        eligible = sub.loc[sub["eligible_phase_subgroup"]].copy()
        weight = eligible["anchor_n"].sum()
        baseline_aw = safe_rate((eligible["representative_taxonomy_disagreement"].astype(float) * eligible["anchor_n"]).sum(), weight)
        phased_aw = safe_rate((eligible["subgroup_representative_disagreement"].astype(float) * eligible["anchor_n"]).sum(), weight)
        total_anchor = sub["anchor_n"].sum()
        rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "phase_scheme": scheme,
                "primary_support_gate_threshold": threshold_id == SELECTED_THRESHOLD_ID,
                "primary_improvement_split": split_bucket == "train",
                "baseline_unit": "cluster_medoid_15b",
                "phased_unit": "cluster_phase_subgroup_15c",
                "representative_disagreement_share_baseline": float(eligible["representative_taxonomy_disagreement"].mean())
                if len(eligible)
                else np.nan,
                "representative_disagreement_share_phased": float(eligible["subgroup_representative_disagreement"].mean())
                if len(eligible)
                else np.nan,
                "representative_disagreement_share_baseline_anchor_weighted": baseline_aw,
                "representative_disagreement_share_phased_anchor_weighted": phased_aw,
                "internal_entropy_median_baseline": float(eligible["cluster_internal_path_type_entropy"].median())
                if len(eligible)
                else np.nan,
                "internal_entropy_median_phased": float(eligible["internal_entropy"].median()) if len(eligible) else np.nan,
                "internal_entropy_p75_baseline": float(eligible["cluster_internal_path_type_entropy"].quantile(0.75))
                if len(eligible)
                else np.nan,
                "internal_entropy_p75_phased": float(eligible["internal_entropy"].quantile(0.75)) if len(eligible) else np.nan,
                "disagreement_reduction": np.nan,
                "disagreement_reduction_anchor_weighted": baseline_aw - phased_aw,
                "eligible_phase_subgroup_n": int(len(eligible)),
                "sparse_phase_subgroup_share": safe_rate(sub.loc[sub["sparse_phase_subgroup"], "anchor_n"].sum(), total_anchor),
                "subgroup_weighting": "anchor_weighted",
                "baseline_source": "15B_representative_anchor_audit",
                "primary_gate_metric": "anchor_weighted",
            }
        )
    out = pd.DataFrame(rows)
    out["disagreement_reduction"] = out["representative_disagreement_share_baseline"] - out["representative_disagreement_share_phased"]
    return out


def build_coverage_readout(anchor: pd.DataFrame, mixture: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_rows = []
    source = anchor.loc[anchor["eligible_primary_anchor"]].copy()
    source["baseline_unresolved"] = source["path_type"].isin(UNRESOLVED_TYPES)
    for (threshold_id, split_bucket), sub in source.groupby(["threshold_id", "cluster_split_bucket"], sort=False):
        baseline_rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "baseline_unclassified_or_mixed_share": safe_rate(sub["baseline_unresolved"].sum(), len(sub)),
            }
        )
    baseline = pd.DataFrame(baseline_rows)
    for (threshold_id, split_bucket, scheme), sub in mixture.groupby(["threshold_id", "split_bucket", "phase_scheme"], sort=False):
        total = sub["anchor_n"].sum()
        single = sub.loc[~sub["subtype_0p70"].isin([MIXED_SUBTYPE, SPARSE_SUBTYPE]), "anchor_n"].sum()
        mixed = sub.loc[sub["subtype_0p70"].eq(MIXED_SUBTYPE), "anchor_n"].sum()
        sparse = sub.loc[sub["subtype_0p70"].eq(SPARSE_SUBTYPE), "anchor_n"].sum()
        capture = sub.loc[sub["subtype_0p70"].isin(CAPTURE_FRIENDLY_TYPES), "anchor_n"].sum()
        rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "phase_scheme": scheme,
                "primary_support_gate_threshold": threshold_id == SELECTED_THRESHOLD_ID,
                "single_subtype_coverage": safe_rate(single, total),
                "mixed_share": safe_rate(mixed, total),
                "sparse_phase_subgroup_share": safe_rate(sparse, total),
                "capture_friendly_subtype_share": safe_rate(capture, total),
                "coverage_denominator": "eligible_primary_anchor",
            }
        )
    out = pd.DataFrame(rows).merge(baseline, on=["threshold_id", "split_bucket"], how="left")
    out["coverage_improvement"] = out["single_subtype_coverage"] - (1.0 - out["baseline_unclassified_or_mixed_share"])
    cols = [
        "threshold_id",
        "split_bucket",
        "phase_scheme",
        "primary_support_gate_threshold",
        "baseline_unclassified_or_mixed_share",
        "single_subtype_coverage",
        "mixed_share",
        "sparse_phase_subgroup_share",
        "capture_friendly_subtype_share",
        "coverage_improvement",
        "coverage_denominator",
    ]
    return out[cols]


def build_cluster_subtype_readout(mixture: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (threshold_id, split_bucket, scheme, cluster_id), sub in mixture.groupby(
        ["threshold_id", "split_bucket", "phase_scheme", "episode_cluster_id"], sort=False
    ):
        total = sub["anchor_n"].sum()
        subtype_set = sorted(set(sub["subtype_0p70"].astype(str)))
        non_mixed = [s for s in subtype_set if s not in {MIXED_SUBTYPE, SPARSE_SUBTYPE}]
        rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "phase_scheme": scheme,
                "episode_cluster_id": cluster_id,
                "cluster_anchor_n": int(total),
                "cluster_subtype_set": "|".join(subtype_set),
                "cluster_phase_resolved": len(non_mixed) > 0,
                "cluster_single_subtype_after_phase": len(non_mixed) == 1,
                "cluster_residual_mixed_share": safe_rate(
                    sub.loc[sub["subtype_0p70"].eq(MIXED_SUBTYPE), "anchor_n"].sum(), total
                ),
                "cluster_sparse_phase_anchor_share": safe_rate(
                    sub.loc[sub["subtype_0p70"].eq(SPARSE_SUBTYPE), "anchor_n"].sum(), total
                ),
                "cluster_outcome_only_descriptor_flag": scheme == "outcome",
            }
        )
    return pd.DataFrame(rows)


def subtype_distribution(mixture: pd.DataFrame, split_bucket: str, threshold_id: str, scheme: str) -> pd.Series:
    sub = mixture.loc[
        mixture["threshold_id"].eq(threshold_id)
        & mixture["split_bucket"].eq(split_bucket)
        & mixture["phase_scheme"].eq(scheme)
    ]
    return sub.groupby("subtype_0p70")["anchor_n"].sum()


def material_subtype_n(mixture: pd.DataFrame, threshold_id: str, split_bucket: str, scheme: str, share_min: float, count_min: int) -> int:
    base = mixture.loc[
        mixture["threshold_id"].eq(threshold_id)
        & mixture["split_bucket"].eq(split_bucket)
        & mixture["phase_scheme"].eq(scheme)
    ]
    total = base["anchor_n"].sum()
    if total == 0:
        return 0
    sub = base.loc[~base["subtype_0p70"].isin([MIXED_SUBTYPE, SPARSE_SUBTYPE])]
    agg = sub.groupby("subtype_0p70")["anchor_n"].sum()
    return int(((agg / total >= share_min) & (agg >= count_min)).sum())


def build_mixture_by_split_readout(mixture: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, sub in mixture.groupby(["threshold_id", "split_bucket", "phase_scheme", "subtype_0p70"], sort=False):
        threshold_id, split_bucket, scheme, subtype = keys
        total = mixture.loc[
            mixture["threshold_id"].eq(threshold_id)
            & mixture["split_bucket"].eq(split_bucket)
            & mixture["phase_scheme"].eq(scheme),
            "anchor_n",
        ].sum()
        rows.append(
            {
                "threshold_id": threshold_id,
                "split_bucket": split_bucket,
                "phase_scheme": scheme,
                "subtype_0p70": subtype,
                "subtype_anchor_n": int(sub["anchor_n"].sum()),
                "subtype_anchor_share": safe_rate(sub["anchor_n"].sum(), total),
            }
        )
    return pd.DataFrame(rows)


def build_threshold_sensitivity_readout(mixture: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, sub in mixture.groupby(["threshold_id", "phase_scheme", "subtype_0p70"], sort=False):
        threshold_id, scheme, subtype = keys
        total = mixture.loc[mixture["threshold_id"].eq(threshold_id) & mixture["phase_scheme"].eq(scheme), "anchor_n"].sum()
        rows.append(
            {
                "threshold_id": threshold_id,
                "phase_scheme": scheme,
                "subtype_0p70": subtype,
                "subtype_anchor_n": int(sub["anchor_n"].sum()),
                "subtype_anchor_share": safe_rate(sub["anchor_n"].sum(), total),
                "threshold_sensitivity_role": "readout_only_not_primary_decision"
                if threshold_id != SELECTED_THRESHOLD_ID
                else "primary_support_threshold",
            }
        )
    return pd.DataFrame(rows)


def build_stability_gate(
    mixture: pd.DataFrame,
    random_readout: pd.DataFrame,
    disagreement: pd.DataFrame,
    coverage: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    share_min = float(config["material_subtype_anchor_share_threshold"])
    split_min = {
        "train": int(config["material_subtype_train_n_min"]),
        "validation": int(config["material_subtype_validation_n_min"]),
        "robustness": int(config["material_subtype_robustness_n_min"]),
    }
    rows: list[dict[str, Any]] = []
    thresholds = sorted(mixture["threshold_id"].dropna().unique())
    for threshold_id in thresholds:
        for scheme in PHASE_SCHEMES:
            rand_train = random_readout.loc[
                random_readout["threshold_id"].eq(threshold_id)
                & random_readout["split_bucket"].eq("train")
                & random_readout["phase_scheme"].eq(scheme)
            ]
            cov_train = coverage.loc[
                coverage["threshold_id"].eq(threshold_id)
                & coverage["split_bucket"].eq("train")
                & coverage["phase_scheme"].eq(scheme)
            ]
            dis_train = disagreement.loc[
                disagreement["threshold_id"].eq(threshold_id)
                & disagreement["split_bucket"].eq("train")
                & disagreement["phase_scheme"].eq(scheme)
            ]
            train_phase_n = int(rand_train["eligible_phase_subgroup_n"].iloc[0]) if not rand_train.empty else 0
            single_cov = float(cov_train["single_subtype_coverage"].iloc[0]) if not cov_train.empty else np.nan
            mixed_share = float(cov_train["mixed_share"].iloc[0]) if not cov_train.empty else np.nan
            sparse_share = float(cov_train["sparse_phase_subgroup_share"].iloc[0]) if not cov_train.empty else np.nan
            phase_real = bool(rand_train["phase_split_is_real"].iloc[0]) if not rand_train.empty else False
            uplift = float(rand_train["dominant_share_uplift_vs_random"].iloc[0]) if not rand_train.empty else np.nan
            entropy_red = float(rand_train["internal_entropy_reduction_vs_random"].iloc[0]) if not rand_train.empty else np.nan
            phased_dis = (
                float(dis_train["representative_disagreement_share_phased_anchor_weighted"].iloc[0])
                if not dis_train.empty
                else np.nan
            )
            dis_red = float(dis_train["disagreement_reduction_anchor_weighted"].iloc[0]) if not dis_train.empty else np.nan
            material_train = material_subtype_n(mixture, threshold_id, "train", scheme, share_min, split_min["train"])
            material_val = material_subtype_n(mixture, threshold_id, "validation", scheme, share_min, split_min["validation"])
            material_rob = material_subtype_n(mixture, threshold_id, "robustness", scheme, share_min, split_min["robustness"])
            train_dist = subtype_distribution(mixture, "train", threshold_id, scheme)
            val_dist = subtype_distribution(mixture, "validation", threshold_id, scheme)
            rob_dist = subtype_distribution(mixture, "robustness", threshold_id, scheme)
            scheme_supported = (
                threshold_id == SELECTED_THRESHOLD_ID
                and phase_real
                and np.isfinite(phased_dis)
                and phased_dis <= 0.50
                and np.isfinite(dis_red)
                and dis_red >= 0.15
                and np.isfinite(single_cov)
                and single_cov >= 0.50
                and np.isfinite(mixed_share)
                and mixed_share <= 0.45
                and np.isfinite(sparse_share)
                and sparse_share <= 0.25
                and material_train >= 3
                and material_val >= 2
                and material_rob >= 2
            )
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "phase_scheme": scheme,
                    "primary_support_gate_threshold": threshold_id == SELECTED_THRESHOLD_ID,
                    "eligible_train_phase_subgroup_n": train_phase_n,
                    "single_subtype_coverage_train": single_cov,
                    "mixed_share_train": mixed_share,
                    "material_subtype_n_train": material_train,
                    "material_subtype_n_validation": material_val,
                    "material_subtype_n_robustness": material_rob,
                    "js_divergence_train_validation_subtype": r15b.js_divergence(train_dist, val_dist),
                    "js_divergence_train_robustness_subtype": r15b.js_divergence(train_dist, rob_dist),
                    "phase_split_is_real": phase_real,
                    "dominant_share_uplift_vs_random": uplift,
                    "internal_entropy_reduction_vs_random": entropy_red,
                    "sparse_phase_subgroup_share_train": sparse_share,
                    "pit_scheme_supported_for_15d": bool(scheme == "pit" and scheme_supported),
                    "outcome_scheme_descriptive_supported": bool(scheme == "outcome" and scheme_supported),
                    "primary_gate_population_id": "threshold_id=up50pct;split=train;subgroup_weighting=anchor_weighted",
                    "mixture_stability_status": "pass",
                }
            )
    out = pd.DataFrame(rows)
    pit_supported = bool(
        out.loc[
            out["threshold_id"].eq(SELECTED_THRESHOLD_ID) & out["phase_scheme"].eq("pit"),
            "pit_scheme_supported_for_15d",
        ].any()
    )
    if pit_supported:
        out.loc[:, "outcome_scheme_descriptive_supported"] = False
    else:
        out.loc[:, "outcome_scheme_descriptive_supported"] = (
            out["outcome_scheme_descriptive_supported"]
            & out["threshold_id"].eq(SELECTED_THRESHOLD_ID)
            & out["phase_scheme"].eq("outcome")
        )
    return out


def build_pit_vs_outcome_comparison(
    random_readout: pd.DataFrame,
    disagreement: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    thresholds = sorted(random_readout["threshold_id"].dropna().unique())
    metric_sources = {
        "dominant_share_uplift_vs_random": (random_readout, "higher"),
        "internal_entropy_reduction_vs_random": (random_readout, "higher"),
        "representative_disagreement_share_phased_anchor_weighted": (disagreement, "lower"),
        "single_subtype_coverage": (coverage, "higher"),
        "mixed_share": (coverage, "lower"),
    }
    for threshold_id in thresholds:
        for metric, (source, direction) in metric_sources.items():
            pit = source.loc[
                source["threshold_id"].eq(threshold_id) & source["split_bucket"].eq("train") & source["phase_scheme"].eq("pit")
            ]
            outcome = source.loc[
                source["threshold_id"].eq(threshold_id)
                & source["split_bucket"].eq("train")
                & source["phase_scheme"].eq("outcome")
            ]
            pit_value = float(pit[metric].iloc[0]) if not pit.empty and metric in pit.columns else np.nan
            outcome_value = float(outcome[metric].iloc[0]) if not outcome.empty and metric in outcome.columns else np.nan
            if not np.isfinite(pit_value) or not np.isfinite(outcome_value):
                better = "not_comparable"
            elif direction == "higher":
                better = "pit" if pit_value > outcome_value else ("outcome" if outcome_value > pit_value else "tie")
            else:
                better = "pit" if pit_value < outcome_value else ("outcome" if outcome_value < pit_value else "tie")
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "metric": metric,
                    "pit_value": pit_value,
                    "outcome_value": outcome_value,
                    "better_scheme": better,
                    "pit_can_authorize_15d": threshold_id == SELECTED_THRESHOLD_ID,
                    "outcome_can_authorize_15d": False,
                }
            )
    return pd.DataFrame(rows)


def build_mixture_rule_audit(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dominant_share_threshold_primary": float(config["dominant_share_threshold"]),
                "dominant_share_threshold_sensitivity": float(config["sensitivity_dominant_share_threshold"]),
                "min_phase_subgroup_anchor_n": int(config["min_phase_subgroup_anchor_n"]),
                "subgroup_weighting": "anchor_weighted",
                "unclassified_policy": "unclassified_and_data_quality_blocked_never_become_single_subtype",
                "sparse_policy": "anchor_n_below_min_counted_as_sparse_residual_not_single_subtype",
                "random_baseline_seed": int(config["random_seed"]),
                "random_baseline_repeat_n": int(config["random_repeat_n"]),
                "cross_split_excluded_from_primary_gate": True,
                "mixture_rule_fit_status": "pass",
            }
        ]
    )


def build_search_accounting(config: dict[str, Any]) -> pd.DataFrame:
    row = {
        "startup_authorization_basis": "15B_unit_granularity_insufficiency_not_15B_separability_block",
        "manual_research_plan_override": True,
        "selected_threshold_id": config["selected_threshold_id"],
        "threshold_selection_source": "inherited_from_15A_lowest_pre_registered_material_censoring_threshold",
        "taxonomy_fit_split": "train",
        "validation_usage": "support_gate_no_fit",
        "robustness_usage": "support_gate_no_fit",
        "validation_robustness_usage_detail": "frozen_train_rules_applied_for_material_confirmation_only",
        "entry_phase_pit_upgradeable_to_t0_feature": True,
        "entry_phase_outcome_upgradeable_to_t0_feature": False,
        "random_baseline_seed": int(config["random_seed"]),
        "random_baseline_repeat_n": int(config["random_repeat_n"]),
        "dominant_share_threshold": float(config["dominant_share_threshold"]),
        "min_phase_subgroup_anchor_n": int(config["min_phase_subgroup_anchor_n"]),
        "subgroup_weighting": "anchor_weighted",
        "pit_scheme_required_for_15d": True,
        "outcome_phase_can_authorize_15d": False,
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
        "separability_search_authorized": False,
    }
    expected = {
        "startup_authorization_basis": "15B_unit_granularity_insufficiency_not_15B_separability_block",
        "manual_research_plan_override": True,
        "selected_threshold_id": SELECTED_THRESHOLD_ID,
        "taxonomy_fit_split": "train",
        "validation_usage": "support_gate_no_fit",
        "robustness_usage": "support_gate_no_fit",
        "entry_phase_pit_upgradeable_to_t0_feature": True,
        "entry_phase_outcome_upgradeable_to_t0_feature": False,
        "pit_scheme_required_for_15d": True,
        "outcome_phase_can_authorize_15d": False,
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
        "separability_search_authorized": False,
    }
    status = "pass" if all(row.get(key) == value for key, value in expected.items()) else "fail"
    row["search_accounting_status"] = status
    return pd.DataFrame([row])


def hard_fail_present(
    input_audit: pd.DataFrame,
    lineage: pd.DataFrame,
    price_path: pd.DataFrame,
    adapter: pd.DataFrame,
    rebuild: pd.DataFrame,
    entry_rule: pd.DataFrame,
    mixture_rule: pd.DataFrame,
    random_readout: pd.DataFrame,
    search: pd.DataFrame,
) -> bool:
    def status_ok(frame: pd.DataFrame, column: str, allowlist: set[str]) -> bool:
        if frame.empty or column not in frame.columns:
            return False
        values = frame[column].dropna().astype(str)
        if values.empty:
            return False
        return bool(values.isin(allowlist).all())

    input_required = input_audit
    if "required_flag" in input_required.columns:
        input_required = input_required.loc[input_required["required_flag"].astype(bool)]
    checks = [
        status_ok(input_required, "input_gate_status", {"pass"}),
        status_ok(lineage, "lineage_status", {"pass"}),
        status_ok(price_path, "price_path_status", {"pass"}),
        status_ok(adapter, "adapter_status", {"pass"}),
        status_ok(rebuild, "rebuild_status", {"pass", "not_required_pass"}),
        status_ok(entry_rule, "entry_phase_rule_fit_status", {"pass"}),
        status_ok(entry_rule, "entry_phase_provenance_status", {"pass"}),
        status_ok(mixture_rule, "mixture_rule_fit_status", {"pass"}),
        status_ok(random_readout, "random_baseline_status", {"pass"}),
        status_ok(search, "search_accounting_status", {"pass"}),
    ]
    return not all(bool(x) for x in checks)


def build_decision(
    stability: pd.DataFrame,
    input_audit: pd.DataFrame,
    lineage: pd.DataFrame,
    price_path: pd.DataFrame,
    adapter: pd.DataFrame,
    rebuild: pd.DataFrame,
    entry_rule: pd.DataFrame,
    mixture_rule: pd.DataFrame,
    random_readout: pd.DataFrame,
    search: pd.DataFrame,
) -> pd.DataFrame:
    hard_fail = hard_fail_present(input_audit, lineage, price_path, adapter, rebuild, entry_rule, mixture_rule, random_readout, search)
    primary = stability.loc[stability["threshold_id"].eq(SELECTED_THRESHOLD_ID)].copy()
    pit = primary.loc[primary["phase_scheme"].eq("pit")]
    outcome = primary.loc[primary["phase_scheme"].eq("outcome")]
    pit_n = int(pit["eligible_train_phase_subgroup_n"].iloc[0]) if not pit.empty else 0
    outcome_n = int(outcome["eligible_train_phase_subgroup_n"].iloc[0]) if not outcome.empty else 0
    any_real = bool(primary["phase_split_is_real"].any()) if not primary.empty else False
    pit_supported = bool(primary["pit_scheme_supported_for_15d"].any()) if not primary.empty else False
    outcome_supported = bool(primary["outcome_scheme_descriptive_supported"].any()) if not primary.empty else False
    if hard_fail:
        decision_state = "15C_blocked_input_or_lineage_failure"
        next_allowed = "none"
    elif pit_n < 200 and outcome_n < 200:
        decision_state = "15C_inconclusive_too_sparse"
        next_allowed = "none"
    elif not any_real:
        decision_state = "15C_entry_phase_no_real_improvement_over_random"
        next_allowed = "none"
    elif pit_supported:
        decision_state = "15C_entry_phase_mixture_supported_for_separability"
        next_allowed = "requirement_15d_capture_friendly_winner_separability_diagnostic.md"
    elif outcome_supported:
        decision_state = "15C_outcome_phase_only_descriptive_improvement"
        next_allowed = "none"
    else:
        decision_state = "15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient"
        next_allowed = "none"
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": next_allowed,
                "selected_threshold_id": SELECTED_THRESHOLD_ID,
                "eligible_train_phase_subgroup_n_pit": pit_n,
                "eligible_train_phase_subgroup_n_outcome": outcome_n,
                "pit_scheme_supported_for_15d": pit_supported,
                "outcome_scheme_descriptive_supported": outcome_supported,
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
                "decision_status": "pass" if not hard_fail else "fail",
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    random_readout: pd.DataFrame,
    disagreement: pd.DataFrame,
    coverage: pd.DataFrame,
    stability: pd.DataFrame,
    split_readout: pd.DataFrame,
    threshold_readout: pd.DataFrame,
) -> str:
    decision_row = decision.iloc[0].to_dict()

    def primary_row(frame: pd.DataFrame, scheme: str) -> dict[str, Any]:
        sub = frame.loc[
            frame["threshold_id"].eq(SELECTED_THRESHOLD_ID)
            & frame.get("split_bucket", pd.Series("", index=frame.index)).eq("train")
            & frame["phase_scheme"].eq(scheme)
        ]
        return sub.iloc[0].to_dict() if not sub.empty else {}

    pit_rand = primary_row(random_readout, "pit")
    out_rand = primary_row(random_readout, "outcome")
    pit_dis = primary_row(disagreement, "pit")
    out_dis = primary_row(disagreement, "outcome")
    pit_cov = primary_row(coverage, "pit")
    out_cov = primary_row(coverage, "outcome")

    def fmt(value: Any) -> str:
        try:
            if pd.isna(value):
                return "NA"
            if isinstance(value, (int, np.integer)):
                return str(int(value))
            return f"{float(value):.4f}"
        except Exception:
            return str(value)

    threshold_lines = []
    for _, row in threshold_readout.sort_values(["threshold_id", "phase_scheme", "subtype_anchor_share"], ascending=[True, True, False]).head(18).iterrows():
        threshold_lines.append(
            f"- {row['threshold_id']} / {row['phase_scheme']} / {row['subtype_0p70']}: share={fmt(row['subtype_anchor_share'])}, n={int(row['subtype_anchor_n'])}, role={row['threshold_sensitivity_role']}"
        )
    split_lines = []
    for _, row in split_readout.loc[split_readout["threshold_id"].eq(SELECTED_THRESHOLD_ID)].sort_values(
        ["split_bucket", "phase_scheme", "subtype_anchor_share"], ascending=[True, True, False]
    ).head(24).iterrows():
        split_lines.append(
            f"- {row['split_bucket']} / {row['phase_scheme']} / {row['subtype_0p70']}: share={fmt(row['subtype_anchor_share'])}, n={int(row['subtype_anchor_n'])}"
        )

    return f"""# 15C Winner Entry Phase and Mixture Taxonomy Diagnostic

## 1. 单行裁决

`decision_state = {decision_row['decision_state']}`；`next_allowed_requirement = {decision_row['next_allowed_requirement']}`。

无论该裁决如何，本实验都不授权 label deployment、signal search、entry policy、model training 或 separability search。若后续允许 15D，也只允许对 PIT-observable entry-phase + capture-friendly subtype 做新的 separability 诊断。

## 2. 为什么 15C 可以在 15B no-stable 后启动

15B 的 `next_allowed_requirement = none` 否定的是 cluster-medoid 统计单元上的稳定 path-shape taxonomy，不是否定 entry-phase 子单元。15B 的核心失败信号是 unit granularity：同一个 winner episode cluster 内部的 anchor path type 高度混合，medoid 单点代表不足。15C 因此只做 label-form diagnostic，把统计单元改成 `(episode_cluster_id, entry_phase, anchor)`，不复活 entry、signal、model 或 separability 搜索。

Search accounting 记录的启动依据为 `15B_unit_granularity_insufficiency_not_15B_separability_block`。

## 3. 四层框架与因果顺序

15C 固定四层：outcome（是否 hit） -> threshold（up50/up100/up150 分开） -> entry phase（同一行情内不同进入阶段） -> path-quality（anchor 自己 segment 上的 15B path type）。因果顺序不能倒置：先确定 entry phase，再引用 anchor-level path-quality，再做 cluster mixture；不能用 episode medoid 的 shape 反推 anchor quality。

## 4. 两套 entry phase

PIT-observable phase 使用 t0 可见 morphology 字段和 train-only quantile，后续理论上可升级为 t0 feature。Outcome-relative phase 使用 cluster interval 中的相对位置，只是事后 descriptor，永远不能授权 15D。

## 5. 切分前后异质性

Primary gate 只看 `threshold_id = up50pct` 且 `split = train` 的 anchor-weighted 指标：

| scheme | baseline disagreement | phased disagreement | reduction | baseline entropy median | phased entropy median |
|---|---:|---:|---:|---:|---:|
| pit | {fmt(pit_dis.get('representative_disagreement_share_baseline_anchor_weighted'))} | {fmt(pit_dis.get('representative_disagreement_share_phased_anchor_weighted'))} | {fmt(pit_dis.get('disagreement_reduction_anchor_weighted'))} | {fmt(pit_dis.get('internal_entropy_median_baseline'))} | {fmt(pit_dis.get('internal_entropy_median_phased'))} |
| outcome | {fmt(out_dis.get('representative_disagreement_share_baseline_anchor_weighted'))} | {fmt(out_dis.get('representative_disagreement_share_phased_anchor_weighted'))} | {fmt(out_dis.get('disagreement_reduction_anchor_weighted'))} | {fmt(out_dis.get('internal_entropy_median_baseline'))} | {fmt(out_dis.get('internal_entropy_median_phased'))} |

## 6. 随机切分基线

随机基线只在同一 cluster 内打乱 anchor -> subgroup 分配，保留 cluster 成员与 anchor path-quality。Primary metrics 使用 anchor-weighted average。

| scheme | phase dominant | random dominant | uplift | phase entropy | random entropy | entropy reduction | real |
|---|---:|---:|---:|---:|---:|---:|---|
| pit | {fmt(pit_rand.get('mean_dominant_share_phase'))} | {fmt(pit_rand.get('mean_dominant_share_random'))} | {fmt(pit_rand.get('dominant_share_uplift_vs_random'))} | {fmt(pit_rand.get('mean_internal_entropy_phase'))} | {fmt(pit_rand.get('mean_internal_entropy_random'))} | {fmt(pit_rand.get('internal_entropy_reduction_vs_random'))} | {pit_rand.get('phase_split_is_real')} |
| outcome | {fmt(out_rand.get('mean_dominant_share_phase'))} | {fmt(out_rand.get('mean_dominant_share_random'))} | {fmt(out_rand.get('dominant_share_uplift_vs_random'))} | {fmt(out_rand.get('mean_internal_entropy_phase'))} | {fmt(out_rand.get('mean_internal_entropy_random'))} | {fmt(out_rand.get('internal_entropy_reduction_vs_random'))} | {out_rand.get('phase_split_is_real')} |

## 7. Mixture taxonomy 覆盖率

Dominant-share 贴标阈值固定为 0.70；小于 10 个 anchor 的 phase subgroup 记为 sparse，不算 single subtype coverage。

| scheme | baseline unresolved | single subtype coverage | mixed share | sparse share | capture-friendly share |
|---|---:|---:|---:|---:|---:|
| pit | {fmt(pit_cov.get('baseline_unclassified_or_mixed_share'))} | {fmt(pit_cov.get('single_subtype_coverage'))} | {fmt(pit_cov.get('mixed_share'))} | {fmt(pit_cov.get('sparse_phase_subgroup_share'))} | {fmt(pit_cov.get('capture_friendly_subtype_share'))} |
| outcome | {fmt(out_cov.get('baseline_unclassified_or_mixed_share'))} | {fmt(out_cov.get('single_subtype_coverage'))} | {fmt(out_cov.get('mixed_share'))} | {fmt(out_cov.get('sparse_phase_subgroup_share'))} | {fmt(out_cov.get('capture_friendly_subtype_share'))} |

## 8. 三档阈值不可外推

以下是按 threshold / scheme 聚合后的 dominant subtype 读数摘录。up50 是 primary support threshold；up100/up150 只做 sensitivity readout，不得改变 primary decision。

{chr(10).join(threshold_lines)}

## 9. Split 内 subtype 结构

Primary threshold `up50pct` 在 train / validation / robustness 的 subtype 结构摘录：

{chr(10).join(split_lines)}

## 10. 后续候选与描述性读数

只有 PIT scheme 同时满足 real-over-random、disagreement reduction、coverage、validation/robustness material confirmation 时，才允许后续 15D。Outcome scheme 即使改善，也只能说明事后 entry-zone 对 label-form 有解释力，不能作为 t0 feature。

当前 `pit_scheme_supported_for_15d = {decision_row['pit_scheme_supported_for_15d']}`，`outcome_scheme_descriptive_supported = {decision_row['outcome_scheme_descriptive_supported']}`。
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


def run(config_path: Path, check_inputs_only: bool = False) -> dict[str, Path]:
    config = load_config(config_path)
    config.setdefault("selected_threshold_id", SELECTED_THRESHOLD_ID)
    paths = resolve_config_paths(config)
    ensure_output_dirs(paths)
    table_dir = paths["table_dir"]
    local_cache_dir = paths["local_cache_dir"]

    input_audit = build_input_artifact_audit(paths)
    output_files: dict[str, Path] = {"input_artifact_audit": table_dir / "input_artifact_audit.csv"}
    write_df(output_files["input_artifact_audit"], input_audit)
    if check_inputs_only:
        return output_files

    rule_audit_15b = read_table_columns(paths["rule_audit_15b"])
    representative_15b = read_table_columns(paths["representative_audit_15b"])
    anchor, adapter_audit, rebuild_audit = load_taxonomy_anchor_panel(paths, rule_audit_15b)
    quantiles = fit_pit_quantiles(anchor, config["selected_threshold_id"])
    anchor = assign_pit_phase(anchor, quantiles)
    anchor = assign_outcome_phase(anchor)

    entry_rule = build_entry_phase_rule_audit(anchor, quantiles, config)
    assignment = build_entry_phase_assignment_readout(anchor)
    scaler = load_medoid_scaler(rule_audit_15b)
    mixture = build_phase_conditioned_mixture(
        anchor,
        scaler,
        float(config["dominant_share_threshold"]),
        float(config["sensitivity_dominant_share_threshold"]),
        int(config["min_phase_subgroup_anchor_n"]),
    )
    random_panel, random_readout = build_random_baseline(
        anchor,
        mixture,
        int(config["random_seed"]),
        int(config["random_repeat_n"]),
        int(config["min_phase_subgroup_anchor_n"]),
    )
    disagreement = build_disagreement_readout(mixture, representative_15b)
    coverage = build_coverage_readout(anchor, mixture)
    cluster_subtype = build_cluster_subtype_readout(mixture)
    split_readout = build_mixture_by_split_readout(mixture)
    threshold_readout = build_threshold_sensitivity_readout(mixture)
    comparison = build_pit_vs_outcome_comparison(random_readout, disagreement, coverage)
    mixture_rule = build_mixture_rule_audit(config)
    search = build_search_accounting(config)
    lineage = build_upstream_lineage_audit(paths)
    price_path = build_price_path_completeness_audit(paths)
    stability = build_stability_gate(mixture, random_readout, disagreement, coverage, config)
    decision = build_decision(
        stability,
        input_audit,
        lineage,
        price_path,
        adapter_audit,
        rebuild_audit,
        entry_rule,
        mixture_rule,
        random_readout,
        search,
    )
    report = build_report(decision, random_readout, disagreement, coverage, stability, split_readout, threshold_readout)

    output_files.update(
        {
            "upstream_lineage_audit": table_dir / "upstream_lineage_audit.csv",
            "price_path_completeness_audit": table_dir / "price_path_completeness_audit.csv",
            "path_quality_adapter_audit": table_dir / "path_quality_adapter_audit.csv",
            "path_quality_rebuild_audit": table_dir / "path_quality_rebuild_audit.csv",
            "entry_phase_rule_audit": table_dir / "entry_phase_rule_audit.csv",
            "entry_phase_assignment_readout": table_dir / "entry_phase_assignment_readout.csv",
            "phase_conditioned_mixture_readout": table_dir / "phase_conditioned_mixture_readout.csv",
            "mixture_rule_audit": table_dir / "mixture_rule_audit.csv",
            "cluster_subtype_readout": table_dir / "cluster_subtype_readout.csv",
            "phase_split_vs_random_baseline_readout": table_dir / "phase_split_vs_random_baseline_readout.csv",
            "disagreement_before_after_phase_readout": table_dir / "disagreement_before_after_phase_readout.csv",
            "coverage_before_after_phase_readout": table_dir / "coverage_before_after_phase_readout.csv",
            "mixture_by_split_readout": table_dir / "mixture_by_split_readout.csv",
            "mixture_by_threshold_sensitivity_readout": table_dir / "mixture_by_threshold_sensitivity_readout.csv",
            "pit_vs_outcome_phase_comparison_readout": table_dir / "pit_vs_outcome_phase_comparison_readout.csv",
            "mixture_stability_gate": table_dir / "mixture_stability_gate.csv",
            "winner_entry_phase_mixture_decision": table_dir / "winner_entry_phase_mixture_decision.csv",
            "search_accounting_audit": table_dir / "search_accounting_audit.csv",
            "anchor_entry_phase_panel": local_cache_dir / "anchor_entry_phase_panel.parquet",
            "phase_conditioned_mixture_panel": local_cache_dir / "phase_conditioned_mixture_panel.parquet",
            "random_baseline_panel": local_cache_dir / "random_baseline_panel.parquet",
            "report": paths["report_path"],
            "manifest": paths["manifest_path"],
        }
    )

    write_df(output_files["upstream_lineage_audit"], lineage)
    write_df(output_files["price_path_completeness_audit"], price_path)
    write_df(output_files["path_quality_adapter_audit"], adapter_audit)
    write_df(output_files["path_quality_rebuild_audit"], rebuild_audit)
    write_df(output_files["entry_phase_rule_audit"], entry_rule)
    write_df(output_files["entry_phase_assignment_readout"], assignment)
    write_df(output_files["phase_conditioned_mixture_readout"], mixture)
    write_df(output_files["mixture_rule_audit"], mixture_rule)
    write_df(output_files["cluster_subtype_readout"], cluster_subtype)
    write_df(output_files["phase_split_vs_random_baseline_readout"], random_readout)
    write_df(output_files["disagreement_before_after_phase_readout"], disagreement)
    write_df(output_files["coverage_before_after_phase_readout"], coverage)
    write_df(output_files["mixture_by_split_readout"], split_readout)
    write_df(output_files["mixture_by_threshold_sensitivity_readout"], threshold_readout)
    write_df(output_files["pit_vs_outcome_phase_comparison_readout"], comparison)
    write_df(output_files["mixture_stability_gate"], stability)
    write_df(output_files["winner_entry_phase_mixture_decision"], decision)
    write_df(output_files["search_accounting_audit"], search)
    write_df(output_files["anchor_entry_phase_panel"], anchor)
    write_df(output_files["phase_conditioned_mixture_panel"], mixture)
    write_df(output_files["random_baseline_panel"], random_panel)
    write_text(output_files["report"], report)
    write_manifest(paths, output_files, decision)
    return output_files


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check_only = args.check_inputs_only or args.mode == "check-inputs"
    run(Path(args.config), check_inputs_only=check_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
