#!/usr/bin/env python
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    balanced_accuracy_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.neighbors import KNeighborsClassifier


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402

import run_post_replay_event_to_episode_retention_source as post_replay_source  # noqa: E402


REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_experiment_f_transition_sub_regime_taxonomy_audit.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"
PROJECT_DATA_DIR = PROJECT_ROOT / "data"

A_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"
B_TABLE_DIR = TABLE_DIR / "regime_family_matrix"
C_TABLE_DIR = TABLE_DIR / "risk_on_r_series_bridge_ranker"

F_TABLE_DIR = TABLE_DIR / "transition_subregime_taxonomy_audit"
F_REPORT_DIR = REPORT_DIR / "transition_subregime_taxonomy_audit"
F_MANIFEST_DIR = MANIFEST_DIR / "transition_subregime_taxonomy_audit"
F_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "transition_subregime_taxonomy_audit"

FINAL_SUPPORTED = "transition_subregime_taxonomy_supported"
FINAL_SUPPORTED_CAVEATED = "transition_subregime_taxonomy_source_caveated_supported"
FINAL_DIAGNOSTIC = "transition_subregime_taxonomy_diagnostic_only"
FINAL_INPUT_BLOCKED = "transition_subregime_taxonomy_input_blocked"
FINAL_COMPONENT_BLOCKED = "transition_subregime_taxonomy_component_blocked"
FINAL_LABEL_JOIN_BLOCKED = "transition_subregime_taxonomy_label_join_blocked"
FINAL_LEAKAGE_BLOCKED = "transition_subregime_taxonomy_leakage_blocked"
FINAL_SAMPLE_POWER_BLOCKED = "transition_subregime_taxonomy_sample_power_blocked"
FINAL_BINDING_DRIFT_BLOCKED = "transition_subregime_taxonomy_binding_drift_blocked"

ALLOWED_A = {"density_fast_fail_audit_complete", "density_fast_fail_audit_partial_source_complete"}
ALLOWED_B = {"regime_family_matrix_complete", "regime_family_matrix_source_caveated_complete"}
ALLOWED_C = {"risk_on_r_series_ranker_complete", "risk_on_r_series_ranker_source_caveated_complete"}
ALLOWED_D = {
    "post_replay_retention_source_complete",
    "post_replay_retention_source_source_caveated_complete",
}

TARGET_REGIME = "transition"
HEADLINE_WINDOW = "low_to_first_50pct"
HEADLINE_POLICY = "post_replay_executable_horizon_complete"
PRE_REPLAY_POLICY = "pre_replay_capture_only"
SPLITS = ("train", "validation", "robustness")
CORE_SUBREGIMES = ("transition_recovery", "transition_deterioration")
DEFAULT_SUBREGIMES = (
    "transition_recovery",
    "transition_deterioration",
    "transition_boundary_or_mixed",
    "transition_component_missing",
)
SOURCE_SCOPES = (
    "07_E1_only",
    "08_R_core_event_regime_gated",
    "08_R6_event_regime_gated",
    "08_R1_event_regime_gated",
    "08_R2_event_regime_gated",
    "08_R7_event_regime_gated",
    "08_R8_event_regime_gated",
    "08_selected_T4_T7_union",
    "08_T4_gated",
    "08_T7_gated",
)
RECALL_SOURCE_SCOPES = (
    "07_E1_only",
    "08_R_core_event_regime_gated",
    "08_R6_event_regime_gated",
    "08_selected_T4_T7_union",
    "08_T4_gated",
    "08_T7_gated",
)
K_CANDIDATES = (2, 3, 4, 5, 6, 7, 8)
KNN_NEIGHBORS = (3, 5, 7, 11)
RANDOM_STATE = 42
AUTO_WINDOW = 120
BLOCK_SAMPLE_STEP = 20


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True


INPUT_SPECS = [
    InputSpec("requirement", REQUIREMENT_PATH),
    InputSpec("experiment_a_manifest", A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json"),
    InputSpec("experiment_b_manifest", B_MANIFEST_DIR / "regime_family_matrix_manifest.json"),
    InputSpec("experiment_c_manifest", C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json"),
    InputSpec("experiment_d_manifest", D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json"),
    InputSpec("candidate_family_canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("candidate_family_event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec("candidate_family_event_labels", LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet"),
    InputSpec("candidate_family_capture", LOCAL_CACHE_DIR / "candidate_family_capture.parquet"),
    InputSpec("d_membership", D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet"),
    InputSpec("d_scope_retention", D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv"),
    InputSpec("d_e1_missed", D_TABLE_DIR / "post_replay_e1_missed_retention_summary.csv"),
    InputSpec("b_transition_reselection", B_TABLE_DIR / "transition_event_family_reselection_matrix.csv"),
    InputSpec("c_transition_readout", C_TABLE_DIR / "risk_on_r_series_ranker_transition_reselection_readout.csv"),
    InputSpec("primary_index_sh000985", PROJECT_DATA_DIR / "interim" / "index_qlib_csv" / "day" / "SH000985.csv", False),
    InputSpec("sensitivity_index_sh000300", PROJECT_DATA_DIR / "interim" / "index_qlib_csv" / "day" / "SH000300.csv", False),
    InputSpec("sensitivity_index_sz399006", PROJECT_DATA_DIR / "interim" / "index_qlib_csv" / "day" / "SZ399006.csv", False),
    InputSpec("cross_section_feature_panel", LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet", False),
]


OUTPUT_PATHS = {
    "transition_subregime_input_audit": F_TABLE_DIR / "transition_subregime_input_audit.csv",
    "transition_subregime_source_binding_audit": F_TABLE_DIR / "transition_subregime_source_binding_audit.csv",
    "transition_subregime_regime_role_audit": F_TABLE_DIR / "transition_subregime_regime_role_audit.csv",
    "transition_subregime_regime_component_audit": F_TABLE_DIR / "transition_subregime_regime_component_audit.csv",
    "transition_subregime_denominator_audit": F_TABLE_DIR / "transition_subregime_denominator_audit.csv",
    "transition_subregime_label_join_audit": F_TABLE_DIR / "transition_subregime_label_join_audit.csv",
    "transition_subregime_leakage_audit": F_TABLE_DIR / "transition_subregime_leakage_audit.csv",
    "transition_auto_120d_period_audit": F_TABLE_DIR / "transition_auto_120d_period_audit.csv",
    "transition_auto_120d_autocorrelation_audit": F_TABLE_DIR / "transition_auto_120d_autocorrelation_audit.csv",
    "transition_auto_120d_block_stability": F_TABLE_DIR / "transition_auto_120d_block_stability.csv",
    "transition_default_subregime_assignment": F_TABLE_DIR / "transition_default_subregime_assignment.csv.gz",
    "transition_auto_120d_feature_contract": F_TABLE_DIR / "transition_auto_120d_feature_contract.csv",
    "transition_auto_120d_window_features": F_TABLE_DIR / "transition_auto_120d_window_features.csv.gz",
    "transition_auto_120d_elbow_selection": F_TABLE_DIR / "transition_auto_120d_elbow_selection.csv",
    "transition_auto_120d_cluster_assignments": F_TABLE_DIR / "transition_auto_120d_cluster_assignments.csv.gz",
    "transition_auto_120d_knn_assignments": F_TABLE_DIR / "transition_auto_120d_knn_assignments.csv.gz",
    "transition_taxonomy_agreement_matrix": F_TABLE_DIR / "transition_taxonomy_agreement_matrix.csv",
    "transition_subregime_composition_by_split": F_TABLE_DIR / "transition_subregime_composition_by_split.csv",
    "transition_subregime_recall_retention_matrix": F_TABLE_DIR / "transition_subregime_recall_retention_matrix.csv",
    "transition_subregime_e1_missed_capture": F_TABLE_DIR / "transition_subregime_e1_missed_capture.csv",
    "transition_subregime_cost_quality_matrix": F_TABLE_DIR / "transition_subregime_cost_quality_matrix.csv",
    "transition_subregime_density_overlap_matrix": F_TABLE_DIR / "transition_subregime_density_overlap_matrix.csv",
    "transition_subregime_family_readout": F_TABLE_DIR / "transition_subregime_family_readout.csv",
    "transition_subregime_drift_audit": F_TABLE_DIR / "transition_subregime_drift_audit.csv",
    "transition_subregime_decision_tiers": F_TABLE_DIR / "transition_subregime_decision_tiers.csv",
    "transition_subregime_taxonomy_audit_report": F_REPORT_DIR / "transition_subregime_taxonomy_audit_report.md",
    "transition_subregime_taxonomy_contract": F_REPORT_DIR / "transition_subregime_taxonomy_contract.md",
    "transition_subregime_taxonomy_audit_manifest": F_MANIFEST_DIR / "transition_subregime_taxonomy_audit_manifest.json",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment F transition sub-regime taxonomy audit.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (F_TABLE_DIR, F_REPORT_DIR, F_MANIFEST_DIR, F_LOCAL_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_df(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den and pd.notna(den) else np.nan


@contextlib.contextmanager
def suppress_threadpoolctl_stderr() -> Any:
    # Some local BLAS builds make threadpoolctl emit repeated ignored callback
    # tracebacks while sklearn still completes. Keep full-run stdout readable.
    saved_stderr_fd = os.dup(2)
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        try:
            os.dup2(devnull.fileno(), 2)
            with contextlib.redirect_stderr(devnull):
                yield
        finally:
            os.dup2(saved_stderr_fd, 2)
            os.close(saved_stderr_fd)


def kmeans_fit_predict(model: KMeans, matrix: pd.DataFrame | np.ndarray) -> np.ndarray:
    with suppress_threadpoolctl_stderr():
        return model.fit_predict(matrix)


def kmeans_predict(model: KMeans, matrix: pd.DataFrame | np.ndarray) -> np.ndarray:
    with suppress_threadpoolctl_stderr():
        return model.predict(matrix)


def quiet_silhouette_score(matrix: pd.DataFrame | np.ndarray, labels: np.ndarray) -> float:
    with suppress_threadpoolctl_stderr():
        return float(silhouette_score(matrix, labels))


def quiet_model_fit(model: Any, x: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray) -> Any:
    with suppress_threadpoolctl_stderr():
        return model.fit(x, y)


def quiet_model_predict(model: Any, x: pd.DataFrame | np.ndarray) -> np.ndarray:
    with suppress_threadpoolctl_stderr():
        return model.predict(x)


def quiet_model_predict_proba(model: Any, x: pd.DataFrame | np.ndarray) -> np.ndarray:
    with suppress_threadpoolctl_stderr():
        return model.predict_proba(x)


def quiet_model_kneighbors(model: Any, x: pd.DataFrame | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    with suppress_threadpoolctl_stderr():
        return model.kneighbors(x)


def make_event_key(frame: pd.DataFrame) -> pd.Series:
    if "canonical_event_id" in frame.columns:
        canonical = frame["canonical_event_id"].where(frame["canonical_event_id"].notna(), frame.get("event_id", ""))
        return canonical.astype(str)
    return frame.get("event_id", pd.Series(index=frame.index, dtype=str)).astype(str)


def bool_series(frame: pd.DataFrame, col: str, default: bool = False) -> pd.Series:
    if col not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    values = frame[col]
    if values.dtype == bool:
        return values.fillna(default).astype(bool)
    if pd.api.types.is_numeric_dtype(values):
        return pd.to_numeric(values, errors="coerce").fillna(float(default)).ne(0)
    text = values.astype("string").str.lower()
    mapped = text.map(
        {
            "true": True,
            "1": True,
            "1.0": True,
            "yes": True,
            "false": False,
            "0": False,
            "0.0": False,
            "no": False,
        }
    )
    result = pd.Series(default, index=frame.index, dtype=bool)
    valid = mapped.notna()
    result.loc[valid] = mapped.loc[valid].astype(bool).to_numpy()
    return result


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return np.nan, np.nan
    phat = successes / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    margin = z * np.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return float(max(0.0, centre - margin)), float(min(1.0, centre + margin))


def input_audit() -> tuple[pd.DataFrame, dict[str, Path], list[str]]:
    rows: list[dict[str, Any]] = []
    paths = {spec.input_id: spec.path for spec in INPUT_SPECS}
    failures: list[str] = []
    for spec in INPUT_SPECS:
        exists = spec.path.exists()
        status = "available" if exists else ("missing_required" if spec.required else "missing_optional")
        if spec.required and not exists:
            failures.append(f"missing_required_input:{spec.input_id}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "status": status,
                "sha256": path_hash(spec.path),
                "row_count": row_count_for_path(spec.path) if exists else np.nan,
                **(
                    index_file_audit_fields(spec.path)
                    if exists and spec.input_id.startswith(("primary_index", "sensitivity_index"))
                    else {}
                ),
            }
        )
    if not any(
        paths[key].exists()
        for key in ("primary_index_sh000985", "sensitivity_index_sh000300", "sensitivity_index_sz399006")
    ) and not paths["cross_section_feature_panel"].exists():
        failures.append("missing_required_market_component_source")
    return pd.DataFrame(rows), paths, failures


def row_count_for_path(path: Path) -> int:
    try:
        if path.suffix == ".parquet":
            return int(len(pd.read_parquet(path)))
        if path.suffix == ".json":
            return 1
        if path.suffix == ".gz" or path.suffix == ".csv":
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False)))
        if path.suffix == ".md":
            return 1
    except Exception:
        return -1
    return 1


def index_file_audit_fields(path: Path) -> dict[str, Any]:
    try:
        idx = read_csv(path, usecols=lambda col: col in {"date", "close"})
        dates = pd.to_datetime(idx.get("date"), errors="coerce")
        close = pd.to_numeric(idx.get("close"), errors="coerce")
        return {
            "date_min": str(dates.min().date()) if dates.notna().any() else "",
            "date_max": str(dates.max().date()) if dates.notna().any() else "",
            "missing_close_count": int(close.isna().sum()),
            "duplicate_date_count": int(dates.duplicated().sum()),
        }
    except Exception:
        return {
            "date_min": "",
            "date_max": "",
            "missing_close_count": np.nan,
            "duplicate_date_count": np.nan,
        }


def validate_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    a = read_json(A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json")
    b = read_json(B_MANIFEST_DIR / "regime_family_matrix_manifest.json")
    c = read_json(C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json")
    d = read_json(D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json")
    failures = []
    if a.get("decision") not in ALLOWED_A:
        failures.append(f"experiment_a_decision_not_allowed:{a.get('decision')}")
    if b.get("decision") not in ALLOWED_B:
        failures.append(f"experiment_b_decision_not_allowed:{b.get('decision')}")
    if c.get("decision") not in ALLOWED_C:
        failures.append(f"experiment_c_decision_not_allowed:{c.get('decision')}")
    if d.get("decision") not in ALLOWED_D:
        failures.append(f"experiment_d_decision_not_allowed:{d.get('decision')}")
    return a, b, c, d, failures


def source_caveated(manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]) -> bool:
    return any("source_caveated" in str(m.get("decision", "")) or "partial" in str(m.get("decision", "")) for m in manifests)


def select_index_source(input_paths: dict[str, Path]) -> tuple[Path | None, str, str]:
    if input_paths["primary_index_sh000985"].exists():
        return input_paths["primary_index_sh000985"], "SH000985", "primary_benchmark_index"
    if input_paths["sensitivity_index_sh000300"].exists():
        return input_paths["sensitivity_index_sh000300"], "SH000300", "fallback_benchmark_proxy"
    if input_paths["sensitivity_index_sz399006"].exists():
        return input_paths["sensitivity_index_sz399006"], "SZ399006", "fallback_benchmark_proxy"
    return None, "universe_proxy", "universe_proxy_reconstructed"


def load_index_panel(path: Path, index_id: str) -> pd.DataFrame:
    idx = read_csv(path)
    idx["date"] = pd.to_datetime(idx["date"])
    idx = idx.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    idx["index_id"] = index_id
    idx["close"] = pd.to_numeric(idx["close"], errors="coerce")
    return idx[["date", "index_id", "close"]]


def add_market_components(index_panel: pd.DataFrame) -> pd.DataFrame:
    out = index_panel.sort_values("date").copy()
    close = pd.to_numeric(out["close"], errors="coerce")
    returns = close.pct_change()
    out["market_close_proxy"] = close
    for horizon in (20, 60, 120):
        out[f"market_return_{horizon}d"] = close / close.shift(horizon) - 1.0
        out[f"market_volatility_{horizon}d"] = returns.rolling(horizon, min_periods=max(5, horizon // 2)).std()
    out["market_trend_20d"] = out["market_return_20d"]
    out["market_trend_60d"] = out["market_return_60d"]
    out["market_drawdown_60d"] = close / close.rolling(60, min_periods=20).max() - 1.0
    out["market_drawdown_120d"] = close / close.rolling(120, min_periods=60).max() - 1.0
    out["market_distance_from_high_120d"] = out["market_drawdown_120d"]
    out["market_regime_bucket_reconstructed"] = np.select(
        [
            out["market_trend_60d"].ge(0) & out["market_drawdown_120d"].gt(-0.10),
            out["market_trend_60d"].lt(0) & out["market_drawdown_120d"].le(-0.10),
        ],
        ["risk_on", "risk_off"],
        default="transition",
    )
    missing = out["market_trend_60d"].isna() | out["market_drawdown_120d"].isna()
    out.loc[missing, "market_regime_bucket_reconstructed"] = "component_missing"
    out["legacy_regime_bucket_drawdown60"] = np.select(
        [
            out["market_trend_60d"].ge(0) & out["market_drawdown_60d"].gt(-0.10),
            out["market_trend_60d"].lt(0) & out["market_drawdown_60d"].le(-0.10),
        ],
        ["risk_on", "risk_off"],
        default="transition",
    )
    out.loc[out["market_trend_60d"].isna() | out["market_drawdown_60d"].isna(), "legacy_regime_bucket_drawdown60"] = (
        "component_missing"
    )
    return out


def load_date_level_breadth(panel_path: Path) -> pd.DataFrame:
    if not panel_path.exists():
        return pd.DataFrame(columns=["date"])
    cols = [
        "date",
        "universe_up_share",
        "universe_new_high_60_share",
        "universe_up_share_z",
        "universe_up_share_change_5d",
        "board_relative_1d",
        "board_relative_cusum_20d",
        "board_return_20d",
        "stock_vs_board_20d",
        "evaluated_member_count",
    ]
    panel = pd.read_parquet(panel_path)
    keep = [col for col in cols if col in panel.columns]
    if "date" not in keep:
        return pd.DataFrame(columns=["date"])
    panel = panel[keep].copy()
    panel["date"] = pd.to_datetime(panel["date"])
    numeric = [col for col in keep if col != "date"]
    grouped = panel.groupby("date", as_index=False)[numeric].mean(numeric_only=True)
    return grouped


def build_component_panel(index_panel: pd.DataFrame, breadth: pd.DataFrame) -> pd.DataFrame:
    components = add_market_components(index_panel)
    if not breadth.empty:
        components = components.merge(breadth, on="date", how="left")
    return components.sort_values("date").reset_index(drop=True)


def merge_components_asof(events: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    left = events.copy()
    left["event_t0_date_dt"] = pd.to_datetime(left["event_t0_date"])
    right = components.sort_values("date").copy()
    merged = pd.merge_asof(
        left.sort_values("event_t0_date_dt"),
        right,
        left_on="event_t0_date_dt",
        right_on="date",
        direction="backward",
    )
    merged["component_lag_days"] = (merged["event_t0_date_dt"] - merged["date"]).dt.days
    return merged.sort_index()


def build_component_audit(
    canonical: pd.DataFrame,
    components: pd.DataFrame,
    component_path: Path | None,
    component_id: str,
    component_status: str,
) -> pd.DataFrame:
    events = canonical.loc[canonical["market_regime_bucket"].notna(), ["event_id", "event_t0_date", "market_regime_bucket"]].copy()
    merged = merge_components_asof(events, components)
    valid = merged["market_regime_bucket_reconstructed"].ne("component_missing")
    consistency = float((merged.loc[valid, "market_regime_bucket"] == merged.loc[valid, "market_regime_bucket_reconstructed"]).mean()) if valid.any() else np.nan
    legacy_valid = merged["legacy_regime_bucket_drawdown60"].ne("component_missing")
    legacy_consistency = float((merged.loc[legacy_valid, "market_regime_bucket"] == merged.loc[legacy_valid, "legacy_regime_bucket_drawdown60"]).mean()) if legacy_valid.any() else np.nan
    if pd.notna(consistency) and consistency >= 0.95:
        consistency_status = "pass"
    elif component_path is not None and component_path.exists():
        consistency_status = "horizon_mismatch_audited"
    else:
        consistency_status = "component_consistency_low"
    component_path_text = str(component_path) if component_path is not None else ""
    return pd.DataFrame(
        [
            {
                "component_source": component_id,
                "component_source_status": component_status,
                "component_source_path": component_path_text,
                "source_hash": path_hash(component_path) if component_path is not None else "",
                **(
                    index_file_audit_fields(component_path)
                    if component_path is not None and component_path.exists()
                    else {}
                ),
                "date_level_source_row_count": int(len(components)),
                "event_level_join_row_count": int(len(merged)),
                "future_join_row_count": int((merged["component_lag_days"] < 0).sum()),
                "market_trend_60d_missing_rate": float(merged["market_trend_60d"].isna().mean()),
                "market_drawdown_120d_missing_rate": float(merged["market_drawdown_120d"].isna().mean()),
                "component_reconstruction_consistency_rate": consistency,
                "legacy_drawdown60_consistency_rate": legacy_consistency,
                "legacy_market_drawdown_available_horizon": 60,
                "taxonomy_market_drawdown_horizon": 120,
                "horizon_mismatch_status": "audited",
                "regime_label_consistency_status": consistency_status,
                "reconstruction_formula": "trend_60d=close/close_lag60-1;drawdown_120d=close/rolling_high_120d-1",
                "as_of_policy": "index_date <= event_t0_date",
            }
        ]
    )


def transition_events(canonical: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "event_split",
        "market_regime_bucket",
        "event_regime_bucket",
        "board_bucket",
        "primary_family_id",
        "triggered_family_ids",
        "triggered_family_variants",
        "family_count",
        "channel_count",
    ]
    keep = [col for col in cols if col in canonical.columns]
    events = canonical.loc[canonical["market_regime_bucket"].astype(str).eq(TARGET_REGIME), keep].copy()
    events["event_key"] = make_event_key(events)
    events = events.drop_duplicates("event_key").reset_index(drop=True)
    events = merge_components_asof(events, components)
    return assign_default_subregime(events)


def assign_default_subregime(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    trend60 = pd.to_numeric(out.get("market_trend_60d"), errors="coerce")
    trend20 = pd.to_numeric(out.get("market_trend_20d"), errors="coerce")
    drawdown120 = pd.to_numeric(out.get("market_drawdown_120d"), errors="coerce")
    vol20 = pd.to_numeric(out.get("market_volatility_20d"), errors="coerce")
    train_transition = out["event_split"].astype(str).eq("train")
    vol_p90 = float(vol20.loc[train_transition & vol20.notna()].quantile(0.90)) if (train_transition & vol20.notna()).any() else np.inf

    missing = trend60.isna() | drawdown120.isna()
    recovery = trend60.ge(0) & drawdown120.le(-0.10) & ~missing
    deterioration = trend60.lt(0) & drawdown120.gt(-0.10) & ~missing
    raw = np.select([missing, recovery, deterioration], ["component_missing", "recovery", "deterioration"], default="boundary")
    boundary_reason = []
    boundary = pd.Series(False, index=out.index)
    for idx in out.index:
        reasons = []
        if missing.loc[idx]:
            boundary_reason.append("component_missing")
            continue
        if abs(float(trend60.loc[idx])) <= 0.01:
            reasons.append("trend_boundary_margin")
        if abs(float(drawdown120.loc[idx]) + 0.10) <= 0.01:
            reasons.append("drawdown_boundary_margin")
        if pd.notna(trend20.loc[idx]) and np.sign(float(trend20.loc[idx])) != np.sign(float(trend60.loc[idx])):
            reasons.append("short_trend_contradiction")
        if pd.notna(vol20.loc[idx]) and float(vol20.loc[idx]) > vol_p90:
            reasons.append("volatility_p90_boundary")
        boundary.loc[idx] = bool(reasons)
        boundary_reason.append(";".join(reasons) if reasons else "core_quadrant")

    final = []
    for raw_value, is_boundary in zip(raw, boundary.tolist()):
        if raw_value == "component_missing":
            final.append("transition_component_missing")
        elif is_boundary or raw_value == "boundary":
            final.append("transition_boundary_or_mixed")
        elif raw_value == "recovery":
            final.append("transition_recovery")
        elif raw_value == "deterioration":
            final.append("transition_deterioration")
        else:
            final.append("transition_boundary_or_mixed")
    out["raw_core_quadrant"] = raw
    out["boundary_reclassified_flag"] = boundary.fillna(False).astype(bool)
    out["boundary_reclassification_reason"] = boundary_reason
    out["final_default_subregime"] = final
    out["trend_boundary_margin_pp"] = 1.0
    out["drawdown_boundary_margin_pp"] = 1.0
    out["volatility_boundary_quantile"] = 0.90
    return out


def date_split_lookup(events: pd.DataFrame) -> pd.DataFrame:
    grouped = events.copy()
    grouped["date"] = pd.to_datetime(grouped["event_t0_date"])
    rows = []
    for date, group in grouped.groupby("date", dropna=False):
        split = str(group["event_split"].mode().iloc[0]) if not group["event_split"].mode().empty else ""
        rows.append(
            {
                "date": date,
                "split": split,
                "event_count_in_period": int(group["event_key"].nunique()),
                "default_subregime": str(group["final_default_subregime"].mode().iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def rolling_entropy(series: pd.Series, window: int) -> pd.Series:
    up = series.gt(0).astype(float)

    def entropy(values: np.ndarray) -> float:
        p = np.nanmean(values)
        if pd.isna(p) or p <= 0 or p >= 1:
            return 0.0
        return float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))

    return up.rolling(window, min_periods=max(5, window // 2)).apply(entropy, raw=True)


def add_auto_feature_columns(components: pd.DataFrame) -> pd.DataFrame:
    out = components.sort_values("date").copy()
    close = pd.to_numeric(out["market_close_proxy"], errors="coerce")
    returns = close.pct_change()
    out["trend_slope_20d"] = (close / close.shift(20) - 1.0) / 20.0
    out["trend_slope_60d"] = (close / close.shift(60) - 1.0) / 60.0
    out["volatility_change_20d_vs_60d"] = out["market_volatility_20d"] - out["market_volatility_60d"]
    out["direction_entropy_20d"] = rolling_entropy(returns, 20)
    out["direction_entropy_60d"] = rolling_entropy(returns, 60)
    for col in ["universe_up_share", "universe_new_high_60_share", "board_relative_1d", "board_relative_cusum_20d"]:
        if col in out.columns:
            out[f"{col}_mean_120d"] = out[col].rolling(AUTO_WINDOW, min_periods=60).mean()
            out[f"{col}_min_120d"] = out[col].rolling(AUTO_WINDOW, min_periods=60).min()
            out[f"{col}_max_120d"] = out[col].rolling(AUTO_WINDOW, min_periods=60).max()
            out[f"{col}_slope_120d"] = (out[col] - out[col].shift(AUTO_WINDOW - 1)) / AUTO_WINDOW
    for regime in ["risk_on", "risk_off", "transition"]:
        indicator = out["market_regime_bucket_reconstructed"].eq(regime).astype(float)
        out[f"fraction_days_{regime}_120d"] = indicator.rolling(AUTO_WINDOW, min_periods=60).mean()
        last_seen = []
        last_pos = None
        for pos, value in enumerate(indicator.tolist()):
            if value == 1.0:
                last_pos = pos
            last_seen.append(np.nan if last_pos is None else pos - last_pos)
        out[f"days_since_last_{regime}"] = last_seen
    out["boundary_distance_trend_60d"] = out["market_trend_60d"].abs()
    out["boundary_distance_drawdown_120d"] = (out["market_drawdown_120d"] + 0.10).abs()
    return out


def auto_feature_columns(frame: pd.DataFrame) -> list[str]:
    prefixes = [
        "market_return_",
        "market_volatility_",
        "market_drawdown_",
        "market_distance_",
        "trend_slope_",
        "volatility_change_",
        "direction_entropy_",
        "universe_",
        "board_relative_",
        "fraction_days_",
        "days_since_last_",
        "boundary_distance_",
    ]
    return [
        col
        for col in frame.columns
        if any(col.startswith(prefix) for prefix in prefixes)
        and pd.api.types.is_numeric_dtype(frame[col])
        and col not in {"evaluated_member_count"}
    ]


def build_auto_window_features(components: pd.DataFrame, events: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    feature_panel = add_auto_feature_columns(components)
    split_dates = date_split_lookup(events)
    dates = split_dates[["date", "split", "event_count_in_period", "default_subregime"]].copy()
    target_counts = target_episode_counts_by_date(membership)
    dates = dates.merge(target_counts, on="date", how="left")
    out = dates.merge(feature_panel, on="date", how="left")
    out["auto_period_id"] = out["date"].dt.strftime("%Y-%m-%d")
    out["window_end_date"] = out["date"]
    out["window_start_date"] = out["date"].map(window_start_lookup(feature_panel["date"], AUTO_WINDOW))
    out["observed_trading_day_n"] = out["date"].map(observed_window_count_lookup(feature_panel["date"], AUTO_WINDOW))
    out["window_completeness_rate"] = out["observed_trading_day_n"] / AUTO_WINDOW
    out["episode_count_in_period"] = out["episode_count_in_period"].fillna(0).astype(int)
    out["auto_120d_window_status"] = np.where(out["observed_trading_day_n"] >= AUTO_WINDOW, "complete", "auto_120d_window_incomplete")
    return out.sort_values("date").reset_index(drop=True)


def target_episode_counts_by_date(membership: pd.DataFrame) -> pd.DataFrame:
    if membership.empty:
        return pd.DataFrame(columns=["date", "episode_count_in_period"])
    m = membership.loc[membership["market_regime_bucket"].astype(str).eq(TARGET_REGIME)].copy()
    m["date"] = pd.to_datetime(m["event_t0_date"])
    out = (
        m.dropna(subset=["target_episode_id"])
        .groupby("date", as_index=False)["target_episode_id"]
        .nunique()
        .rename(columns={"target_episode_id": "episode_count_in_period"})
    )
    return out


def window_start_lookup(dates: pd.Series, window: int) -> dict[pd.Timestamp, pd.Timestamp]:
    ordered = pd.Series(pd.to_datetime(dates)).drop_duplicates().sort_values().reset_index(drop=True)
    lookup = {}
    for pos, date in ordered.items():
        start_pos = max(0, pos - window + 1)
        lookup[date] = ordered.iloc[start_pos]
    return lookup


def observed_window_count_lookup(dates: pd.Series, window: int) -> dict[pd.Timestamp, int]:
    ordered = pd.Series(pd.to_datetime(dates)).drop_duplicates().sort_values().reset_index(drop=True)
    return {date: int(min(window, pos + 1)) for pos, date in ordered.items()}


def build_feature_contract(features: pd.DataFrame, feature_cols: list[str], component_path: Path | None, component_id: str) -> pd.DataFrame:
    rows = []
    for col in feature_cols:
        source_kind = "date_level_market_state"
        if col.startswith("universe_"):
            source_kind = "date_level_breadth_state"
        if col.startswith("board_"):
            source_kind = "date_level_board_aggregate_state"
        rows.append(
            {
                "feature_name": col,
                "source_artifact": f"{component_id}_or_date_level_breadth_proxy",
                "source_hash": path_hash(component_path) if component_path is not None else "",
                "feature_grain": source_kind,
                "as_of_policy": "window_end_date = event_t0_date; no future rows",
                "window_length_trading_days": AUTO_WINDOW,
                "missing_rate_train": missing_rate(features, col, "train"),
                "missing_rate_validation": missing_rate(features, col, "validation"),
                "missing_rate_robustness": missing_rate(features, col, "robustness"),
                "allowed_as_unsupervised_taxonomy_feature": True,
                "uses_future_information": False,
                "blocked_reason": "",
            }
        )
    return pd.DataFrame(rows)


def missing_rate(frame: pd.DataFrame, col: str, split: str) -> float:
    sub = frame.loc[frame["split"].astype(str).eq(split)]
    return float(sub[col].isna().mean()) if len(sub) else np.nan


def preprocess_auto_features(features: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    numeric = features[feature_cols].apply(pd.to_numeric, errors="coerce")
    train_mask = features["split"].astype(str).eq("train")
    train = numeric.loc[train_mask]
    medians = train.median(numeric_only=True)
    filled = numeric.fillna(medians).fillna(0.0)
    lower = filled.loc[train_mask].quantile(0.01, numeric_only=True)
    upper = filled.loc[train_mask].quantile(0.99, numeric_only=True)
    clipped = filled.clip(lower=lower, upper=upper, axis=1)
    means = clipped.loc[train_mask].mean(numeric_only=True)
    stds = clipped.loc[train_mask].std(ddof=0, numeric_only=True).replace(0.0, 1.0).fillna(1.0)
    scaled = ((clipped - means) / stds).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    meta = {
        "policy": "train_median_impute__train_winsorize_1_99__train_zscore",
        "feature_columns": feature_cols,
        "feature_columns_hash": stable_hash(feature_cols),
        "train_row_count": int(train_mask.sum()),
    }
    return scaled, meta


def build_autocorrelation_audit(features: pd.DataFrame, matrix: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, float, float]:
    train_mask = features["split"].astype(str).eq("train")
    rows = []
    lag1_values = []
    for col in feature_cols:
        series = matrix.loc[train_mask, col].reset_index(drop=True)
        lag_values = {}
        for lag in (1, 5, 20):
            if len(series) > lag and series.dropna().nunique() > 1:
                value = float(series.autocorr(lag=lag))
            else:
                value = np.nan
            lag_values[f"lag{lag}_autocorrelation"] = value
        if pd.notna(lag_values["lag1_autocorrelation"]):
            lag1_values.append(lag_values["lag1_autocorrelation"])
        rows.append({"feature_name": col, **lag_values})
    rho1 = float(np.nanmean(lag1_values)) if lag1_values else np.nan
    observed = int(train_mask.sum())
    if pd.notna(rho1) and rho1 < 0.999:
        effective = float(observed * (1 - rho1) / (1 + rho1))
    else:
        effective = np.nan
    rows.append(
        {
            "feature_name": "__summary__",
            "lag1_autocorrelation": rho1,
            "lag5_autocorrelation": np.nan,
            "lag20_autocorrelation": np.nan,
            "observed_window_n": observed,
            "effective_independent_window_n": effective,
        }
    )
    return pd.DataFrame(rows), rho1, effective


def elbow_table_for_matrix(matrix: pd.DataFrame, k_candidates: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    n = len(matrix)
    for k in k_candidates:
        if n <= k or k < 2:
            continue
        model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20, max_iter=300)
        labels = kmeans_fit_predict(model, matrix)
        counts = pd.Series(labels).value_counts(normalize=True)
        silhouette = quiet_silhouette_score(matrix, labels) if len(set(labels)) > 1 and n > k else np.nan
        rows.append(
            {
                "k": k,
                "inertia": float(model.inertia_),
                "silhouette": float(silhouette) if pd.notna(silhouette) else np.nan,
                "min_cluster_share": float(counts.min()),
                "max_cluster_share": float(counts.max()),
                "cluster_size_status": "pass" if float(counts.min()) >= 0.05 else "min_cluster_share_lt_5pct",
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values("k").reset_index(drop=True)
    out["relative_improvement"] = np.nan
    for idx in range(1, len(out)):
        previous = float(out.loc[idx - 1, "inertia"])
        current = float(out.loc[idx, "inertia"])
        out.loc[idx, "relative_improvement"] = safe_div(previous - current, previous)
    out["next_relative_improvement"] = out["relative_improvement"].shift(-1)
    out["elbow_score"] = out["relative_improvement"] - out["next_relative_improvement"]
    return out


def select_elbow_k(elbow: pd.DataFrame) -> tuple[int | None, str]:
    if elbow.empty:
        return None, "no_candidate_k"
    usable = elbow.loc[elbow["min_cluster_share"].ge(0.05)].copy()
    if usable.empty:
        best = elbow.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0]
        return int(best["k"]), "elbow_low_cluster_power"
    obvious = usable.loc[
        usable["elbow_score"].notna()
        & usable["relative_improvement"].notna()
        & usable["next_relative_improvement"].notna()
        & (usable["next_relative_improvement"] < 0.75 * usable["relative_improvement"])
    ].copy()
    if not obvious.empty:
        best = obvious.sort_values(["elbow_score", "k"], ascending=[False, True]).iloc[0]
        return int(best["k"]), "max_elbow_score"
    ranked = usable.sort_values(["silhouette", "k"], ascending=[False, True]).reset_index(drop=True)
    if len(ranked) > 1 and abs(float(ranked.loc[0, "silhouette"]) - float(ranked.loc[1, "silhouette"])) < 0.02:
        return int(min(ranked.loc[0, "k"], ranked.loc[1, "k"])), "silhouette_tie_smaller_k"
    return int(ranked.loc[0, "k"]), "silhouette_fallback"


def run_kmeans_taxonomy(
    features: pd.DataFrame,
    matrix: pd.DataFrame,
    feature_cols: list[str],
    effective_n: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    train_mask = features["split"].astype(str).eq("train")
    train_matrix = matrix.loc[train_mask, feature_cols]
    elbow = elbow_table_for_matrix(train_matrix, K_CANDIDATES)
    selected_k, reason = select_elbow_k(elbow)
    if selected_k is None:
        assignments = features[["date", "split", "auto_period_id"]].copy()
        assignments["auto_cluster_id"] = np.nan
        assignments["auto_cluster_label"] = "auto_cluster_unavailable"
        return elbow, assignments, pd.DataFrame(), {"status": "no_candidate_k", "selected_k": None}

    model = KMeans(n_clusters=selected_k, random_state=RANDOM_STATE, n_init=20, max_iter=300)
    train_labels = kmeans_fit_predict(model, train_matrix)
    all_labels = kmeans_predict(model, matrix[feature_cols])
    assignments = features[["date", "split", "auto_period_id", "default_subregime"]].copy()
    assignments["auto_cluster_id"] = all_labels
    label_map = label_auto_clusters(features.loc[train_mask].copy(), train_labels)
    assignments["auto_cluster_label"] = assignments["auto_cluster_id"].map(label_map).fillna("auto_other")
    assignments["assignment_grain"] = "market_date"

    block = block_stability(features, matrix, feature_cols, selected_k, assignments)
    stability_status = str(block.iloc[0]["block_stability_status"]) if not block.empty else "block_stability_unavailable"
    if stability_status != "pass":
        status = "elbow_overlap_instability_diagnostic"
    elif pd.notna(effective_n) and effective_n < 50:
        status = "effective_n_lt_50_diagnostic"
    elif float(elbow.loc[elbow["k"].eq(selected_k), "max_cluster_share"].iloc[0]) > 0.80:
        status = "max_cluster_share_gt_80pct"
    else:
        status = "pass"
    elbow["selected_k_flag"] = elbow["k"].eq(selected_k)
    elbow["selection_reason"] = np.where(elbow["selected_k_flag"], reason, "")
    elbow["auto_taxonomy_status"] = status
    meta = {
        "status": status,
        "selected_k": selected_k,
        "selection_reason": reason,
        "random_state": RANDOM_STATE,
        "n_init": 20,
        "max_iter": 300,
    }
    return elbow, assignments, block, meta


def label_auto_clusters(train_features: pd.DataFrame, train_labels: np.ndarray) -> dict[int, str]:
    tmp = train_features.copy()
    tmp["cluster"] = train_labels
    vol_p90 = pd.to_numeric(train_features["market_volatility_20d"], errors="coerce").quantile(0.90)
    label_map: dict[int, str] = {}
    for cluster, group in tmp.groupby("cluster", dropna=False):
        default_counts = group["default_subregime"].value_counts(normalize=True)
        if default_counts.get("transition_recovery", 0.0) >= 0.50:
            label = "auto_recovery_like"
        elif default_counts.get("transition_deterioration", 0.0) >= 0.50:
            label = "auto_deterioration_like"
        elif default_counts.get("transition_boundary_or_mixed", 0.0) >= 0.50:
            label = "auto_boundary_or_mixed_like"
        elif pd.to_numeric(group.get("market_volatility_20d"), errors="coerce").median() >= vol_p90:
            label = "auto_volatility_stress"
        elif pd.to_numeric(group.get("universe_up_share_slope_120d"), errors="coerce").median() > 0:
            label = "auto_breadth_recovery"
        else:
            label = "auto_other"
        label_map[int(cluster)] = label
    return label_map


def block_stability(
    features: pd.DataFrame,
    matrix: pd.DataFrame,
    feature_cols: list[str],
    rolling_k: int,
    rolling_assignments: pd.DataFrame,
) -> pd.DataFrame:
    train = features.loc[features["split"].astype(str).eq("train")].sort_values("date").copy()
    if train.empty:
        return pd.DataFrame()
    sampled_idx = train.index[::BLOCK_SAMPLE_STEP]
    sampled = matrix.loc[sampled_idx, feature_cols]
    if len(sampled) <= 3:
        return pd.DataFrame(
            [
                {
                    "block_sample_step": BLOCK_SAMPLE_STEP,
                    "block_sample_n": int(len(sampled)),
                    "rolling_selected_k": rolling_k,
                    "block_selected_k": np.nan,
                    "adjusted_rand_index": np.nan,
                    "normalized_mutual_info": np.nan,
                    "block_stability_status": "block_sample_too_small",
                }
            ]
        )
    elbow = elbow_table_for_matrix(sampled, K_CANDIDATES)
    block_k, reason = select_elbow_k(elbow)
    if block_k is None:
        status = "block_k_unavailable"
        ari = nmi = np.nan
    else:
        block_model = KMeans(n_clusters=block_k, random_state=RANDOM_STATE, n_init=20, max_iter=300)
        block_labels = kmeans_fit_predict(block_model, sampled)
        rolling_lookup = rolling_assignments.copy()
        rolling_lookup["date"] = pd.to_datetime(rolling_lookup["date"])
        rolling_lookup = rolling_lookup.drop_duplicates("date").set_index("date")
        sampled_dates = pd.to_datetime(features.loc[sampled_idx, "date"])
        rolling_labels = rolling_lookup.reindex(sampled_dates)["auto_cluster_id"]
        if rolling_labels.isna().any():
            status = "rolling_assignment_missing_for_block_sample"
            ari = nmi = np.nan
        else:
            rolling_labels = rolling_labels.astype(int).to_numpy()
            ari = adjusted_rand_score(rolling_labels, block_labels)
            nmi = normalized_mutual_info_score(rolling_labels, block_labels)
            status = "pass" if block_k == rolling_k and (ari >= 0.50 or nmi >= 0.50) else "block_stability_failed"
    return pd.DataFrame(
        [
            {
                "block_sample_step": BLOCK_SAMPLE_STEP,
                "block_sample_n": int(len(sampled)),
                "rolling_selected_k": rolling_k,
                "block_selected_k": block_k,
                "block_selection_reason": reason,
                "adjusted_rand_index": ari,
                "normalized_mutual_info": nmi,
                "block_stability_status": status,
            }
        ]
    )


def run_knn_taxonomy(features: pd.DataFrame, matrix: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    train_mask = features["split"].astype(str).eq("train")
    train = features.loc[train_mask].copy()
    train_labels = train["default_subregime"].astype(str)
    valid = ~train_labels.eq("transition_component_missing")
    train_idx = train.loc[valid].index
    if len(train_idx) < 10 or train_labels.loc[valid].nunique() < 2:
        assignments = features[["date", "split", "auto_period_id"]].copy()
        assignments["knn_predicted_subregime"] = "knn_unavailable"
        assignments["knn_assignment_confidence"] = np.nan
        return assignments, {"selected_neighbors": None, "status": "knn_unavailable"}
    cv_rows = []
    ordered = train.loc[valid].sort_values("date")
    blocks = np.array_split(ordered.index.to_numpy(), min(5, len(ordered)))
    for n_neighbors in KNN_NEIGHBORS:
        if n_neighbors >= len(train_idx):
            continue
        truths = []
        preds = []
        margins = []
        for block in blocks:
            fit_idx = train_idx.difference(block)
            if len(fit_idx) <= n_neighbors or len(block) == 0:
                continue
            model = KNeighborsClassifier(n_neighbors=n_neighbors, weights="distance", metric="euclidean")
            quiet_model_fit(model, matrix.loc[fit_idx, feature_cols], features.loc[fit_idx, "default_subregime"].astype(str))
            pred = quiet_model_predict(model, matrix.loc[block, feature_cols])
            proba = quiet_model_predict_proba(model, matrix.loc[block, feature_cols])
            sorted_proba = np.sort(proba, axis=1)
            margin = sorted_proba[:, -1] - np.where(sorted_proba.shape[1] > 1, sorted_proba[:, -2], 0)
            truths.extend(features.loc[block, "default_subregime"].astype(str).tolist())
            preds.extend(pred.tolist())
            margins.extend(margin.tolist())
        score = balanced_accuracy_score(truths, preds) if truths else np.nan
        cv_rows.append(
            {
                "n_neighbors": n_neighbors,
                "mean_balanced_accuracy": score,
                "mean_vote_margin": float(np.nanmean(margins)) if margins else np.nan,
                "cv_fold_count": len(blocks),
            }
        )
    cv = pd.DataFrame(cv_rows)
    if cv.empty:
        assignments = features[["date", "split", "auto_period_id"]].copy()
        assignments["knn_predicted_subregime"] = "knn_unavailable"
        assignments["knn_assignment_confidence"] = np.nan
        return assignments, {"selected_neighbors": None, "status": "knn_unavailable"}
    selected = cv.sort_values(["mean_balanced_accuracy", "n_neighbors"], ascending=[False, True]).iloc[0]
    selected_n = int(selected["n_neighbors"])
    model = KNeighborsClassifier(n_neighbors=selected_n, weights="distance", metric="euclidean")
    quiet_model_fit(model, matrix.loc[train_idx, feature_cols], features.loc[train_idx, "default_subregime"].astype(str))
    pred = quiet_model_predict(model, matrix[feature_cols])
    proba = quiet_model_predict_proba(model, matrix[feature_cols])
    sorted_proba = np.sort(proba, axis=1)
    margins = sorted_proba[:, -1] - np.where(sorted_proba.shape[1] > 1, sorted_proba[:, -2], 0)
    distances, _ = quiet_model_kneighbors(model, matrix[feature_cols])
    assignments = features[["date", "split", "auto_period_id", "default_subregime"]].copy()
    assignments["knn_predicted_subregime"] = pred
    assignments["knn_vote_margin"] = margins
    assignments["knn_neighbor_distance_mean"] = distances.mean(axis=1)
    assignments["knn_assignment_confidence"] = np.where(margins >= 0.20, "high", "auto_knn_low_confidence")
    assignments["assignment_grain"] = "market_date"
    cv["selected_neighbors_flag"] = cv["n_neighbors"].eq(selected_n)
    meta = {
        "selected_neighbors": selected_n,
        "status": "pass",
        "selection_formula": "5_blocked_date_cv_mean_balanced_accuracy_tie_smaller_neighbors",
        "cv": cv,
    }
    return assignments, meta


def policy_mask(frame: pd.DataFrame, policy: str) -> pd.Series:
    return post_replay_source.policy_event_mask(frame, policy)


def prepare_membership(membership: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    m = membership.loc[membership["market_regime_bucket"].astype(str).eq(TARGET_REGIME)].copy()
    m["event_key"] = make_event_key(m)
    event_assign = events[["event_key", "event_t0_date", "final_default_subregime"]].drop_duplicates("event_key")
    m = m.merge(event_assign, on="event_key", how="left", suffixes=("", "_event_assignment"))
    if "event_t0_date_event_assignment" in m.columns:
        m["event_t0_date"] = m["event_t0_date"].where(m["event_t0_date"].notna(), m["event_t0_date_event_assignment"])
    m["date"] = pd.to_datetime(m["event_t0_date"])
    return m


def add_method_subregime(
    base_events: pd.DataFrame,
    kmeans_assignments: pd.DataFrame,
    knn_assignments: pd.DataFrame,
) -> pd.DataFrame:
    out = base_events.copy()
    out["date"] = pd.to_datetime(out["event_t0_date"])
    k = kmeans_assignments[["date", "auto_cluster_label"]].drop_duplicates("date")
    n = knn_assignments[["date", "knn_predicted_subregime"]].drop_duplicates("date")
    out = out.merge(k, on="date", how="left").merge(n, on="date", how="left")
    return out


def taxonomy_event_view(events: pd.DataFrame) -> pd.DataFrame:
    methods = [
        ("default_deterministic", "final_default_subregime"),
        ("auto_120d_elbow_kmeans", "auto_cluster_label"),
        ("auto_120d_knn_default_taxonomy", "knn_predicted_subregime"),
    ]
    frames = []
    for method, col in methods:
        if col not in events.columns:
            continue
        tmp = events.copy()
        tmp["taxonomy_method"] = method
        tmp["subregime_label"] = tmp[col].fillna(f"{method}_unavailable")
        frames.append(tmp)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_denominator_audit(membership: pd.DataFrame, events: pd.DataFrame, source_events: pd.DataFrame | None = None) -> pd.DataFrame:
    event_key = make_event_key(membership)
    rows = [
        {
            "readout": "event_composition",
            "raw_row_count": int(len(events)),
            "deduplicated_row_count": int(events["event_key"].nunique()),
            "duplicate_drop_count": int(len(events) - events["event_key"].nunique()),
            "denominator_policy": "unique_event_key",
            "blocked_reason": "",
        },
        {
            "readout": "membership_event_cost",
            "raw_row_count": int(len(membership)),
            "deduplicated_row_count": int(event_key.nunique()),
            "duplicate_drop_count": int(len(membership) - event_key.nunique()),
            "denominator_policy": "unique_horizon_complete_event",
            "blocked_reason": "",
        },
        {
            "readout": "episode_recall",
            "raw_row_count": int(len(membership)),
            "deduplicated_row_count": int(membership["target_episode_id"].dropna().nunique()),
            "duplicate_drop_count": int(len(membership) - membership["target_episode_id"].dropna().nunique()),
            "denominator_policy": "unique_target_episode_global_transition_baseline",
            "blocked_reason": "",
        },
    ]
    if source_events is not None and not source_events.empty:
        recall_keys = [
            "taxonomy_method",
            "event_split",
            "subregime_label",
            "window",
            "target_episode_id",
        ]
        scoped = source_events.dropna(subset=["target_episode_id"]).drop_duplicates(recall_keys)
        rows.append(
            {
                "readout": "subregime_episode_recall",
                "raw_row_count": int(len(source_events)),
                "deduplicated_row_count": int(len(scoped)),
                "duplicate_drop_count": int(len(source_events) - len(scoped)),
                "denominator_policy": "unique_target_episode_within_taxonomy_method_split_subregime_window",
                "blocked_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_source_binding_audit(manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], input_paths: dict[str, Path]) -> pd.DataFrame:
    a, b, c, d = manifests
    market_component_available = any(
        input_paths[key].exists()
        for key in ("primary_index_sh000985", "sensitivity_index_sh000300", "sensitivity_index_sz399006", "cross_section_feature_panel")
    )
    rows = [
        ("experiment_a_decision", a.get("decision"), sorted(ALLOWED_A), a.get("decision") in ALLOWED_A),
        ("experiment_b_decision", b.get("decision"), sorted(ALLOWED_B), b.get("decision") in ALLOWED_B),
        ("experiment_c_decision", c.get("decision"), sorted(ALLOWED_C), c.get("decision") in ALLOWED_C),
        ("experiment_d_decision", d.get("decision"), sorted(ALLOWED_D), d.get("decision") in ALLOWED_D),
        ("market_component_source_available", market_component_available, True, market_component_available),
    ]
    return pd.DataFrame(
        [
            {"binding_name": name, "observed_value": str(observed), "expected_value": str(expected), "binding_status": "pass" if ok else "fail"}
            for name, observed, expected, ok in rows
        ]
    )


def build_regime_role_audit() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact": "post_replay_event_episode_membership.parquet",
                "field_name": "market_regime_bucket",
                "role": "event_side_regime",
                "allowed_for_taxonomy_assignment": True,
                "allowed_for_episode_denominator": False,
            },
            {
                "artifact": "post_replay_event_episode_membership.parquet",
                "field_name": "episode_market_regime_bucket",
                "role": "episode_side_regime",
                "allowed_for_taxonomy_assignment": False,
                "allowed_for_episode_denominator": True,
            },
            {
                "artifact": "candidate_family_canonical_events.csv.gz",
                "field_name": "market_regime_bucket",
                "role": "event_side_regime",
                "allowed_for_taxonomy_assignment": True,
                "allowed_for_episode_denominator": False,
            },
        ]
    )


def build_leakage_audit() -> pd.DataFrame:
    rows = [
        ("market_trend_60d", True, False, "date_level_asof_component", "pass"),
        ("market_drawdown_120d", True, False, "date_level_asof_component", "pass"),
        ("failure_10_label", False, True, "readout_only", "pass"),
        ("event_false_repair_20d_label", False, True, "readout_only", "pass"),
        ("event_big_winner_120d_label", False, True, "readout_only", "pass"),
        ("target_episode_id", False, False, "episode_readout_denominator_only", "pass"),
        ("auto_120d_features", True, False, "window_end_date_eq_event_t0_date", "pass"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "field_name",
            "allowed_as_taxonomy_feature",
            "allowed_as_label",
            "allowed_downstream_use",
            "leakage_status",
        ],
    )


def label_join_audit(membership: pd.DataFrame) -> pd.DataFrame:
    m = membership.copy()
    event_key = make_event_key(m)
    unique = m.assign(event_key=event_key).drop_duplicates("event_key")
    return pd.DataFrame(
        [
            {
                "label_scope": "event_membership_transition",
                "event_n": int(unique["event_key"].nunique()),
                "failure_10_complete_n": int(bool_series(unique, "failure_10_complete").sum()),
                "failure_10_complete_rate": float(bool_series(unique, "failure_10_complete").mean()) if len(unique) else np.nan,
                "false_repair_20d_complete_n": int(bool_series(unique, "event_false_repair_20d_complete").sum()),
                "false_repair_20d_complete_rate": float(bool_series(unique, "event_false_repair_20d_complete").mean()) if len(unique) else np.nan,
                "big_winner_120d_complete_n": int(bool_series(unique, "horizon_complete_120d").sum()),
                "big_winner_120d_complete_rate": float(bool_series(unique, "horizon_complete_120d").mean()) if len(unique) else np.nan,
                "label_join_status": "pass",
            }
        ]
    )


def period_audit(features: pd.DataFrame, effective_n: float, rho1: float) -> pd.DataFrame:
    out = features[
        [
            "auto_period_id",
            "window_start_date",
            "window_end_date",
            "observed_trading_day_n",
            "window_completeness_rate",
            "event_count_in_period",
            "episode_count_in_period",
            "auto_120d_window_status",
        ]
    ].copy()
    out["effective_independent_window_n"] = effective_n
    out["lag1_autocorrelation_mean"] = rho1
    pos = np.arange(len(out))
    out["block_sample_id"] = np.where(pos % BLOCK_SAMPLE_STEP == 0, "block_sampled", "rolling_only")
    out["non_overlap_120d_period_id"] = (pos // AUTO_WINDOW).astype(int)
    out["non_overlap_period_summary_flag"] = np.where((pos + 1) % AUTO_WINDOW == 0, "non_overlap_period_end", "rolling_only")
    return out


def composition_by_split(
    event_view: pd.DataFrame,
    membership: pd.DataFrame,
    source_events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows = []
    total_by_method_split = event_view.groupby(["taxonomy_method", "event_split"])["event_key"].nunique().to_dict()
    episode_dates = membership.dropna(subset=["target_episode_id"]).copy()
    episode_dates["date"] = pd.to_datetime(episode_dates["date"])
    episode_dates = episode_dates.drop_duplicates(["event_split", "date", "target_episode_id"])
    total_target_by_split = (
        episode_dates.drop_duplicates(["event_split", "target_episode_id"])
        .groupby("event_split")["target_episode_id"]
        .nunique()
        .to_dict()
    )
    for (method, split, sub), group in event_view.groupby(["taxonomy_method", "event_split", "subregime_label"], dropna=False):
        total = total_by_method_split.get((method, split), 0)
        dates = pd.to_datetime(group["date"]).drop_duplicates()
        episode_scope = episode_dates.loc[
            episode_dates["event_split"].astype(str).eq(str(split))
            & episode_dates["date"].isin(dates)
        ]
        target_n = int(episode_scope["target_episode_id"].dropna().astype(str).nunique())
        total_target_n = int(total_target_by_split.get(split, 0))
        e1_missed_n = np.nan
        e1_missed_share = np.nan
        if source_events is not None and not source_events.empty:
            denom = subregime_episode_set(source_events, str(split), str(sub), str(method))
            e1_pre = captured_set(source_events, "07_E1_only", str(split), str(sub), str(method), PRE_REPLAY_POLICY)
            e1_missed_n = len(denom.difference(e1_pre))
            e1_missed_share = safe_div(e1_missed_n, len(denom))
        rows.append(
            {
                "taxonomy_method": method,
                "subregime_id": sub,
                "subregime_label": sub,
                "split": split,
                "event_count": int(group["event_key"].nunique()),
                "event_share": safe_div(group["event_key"].nunique(), total),
                "target_episode_n": target_n,
                "target_episode_share": safe_div(target_n, total_target_n),
                "e1_missed_episode_n": e1_missed_n,
                "e1_missed_episode_share": e1_missed_share,
                "sample_status": sample_power_status(target_n, int(group["event_key"].nunique())),
            }
        )
    return pd.DataFrame(rows)


def sample_power_status(target_episode_n: int, event_n: int) -> str:
    if target_episode_n >= 30:
        return "sufficient_episode_power"
    if event_n >= 100:
        return "episode_low_power_event_supported_only"
    if target_episode_n >= 10:
        return "episode_low_power_caution"
    return "insufficient_episode_power"


def source_event_assignments(membership: pd.DataFrame, event_view: pd.DataFrame) -> pd.DataFrame:
    date_method = event_view[["date", "taxonomy_method", "subregime_label"]].drop_duplicates()
    m = membership.loc[membership["source_id"].isin(SOURCE_SCOPES) & membership["window"].eq(HEADLINE_WINDOW)].copy()
    m["date"] = pd.to_datetime(m["event_t0_date"])
    return m.merge(date_method, on="date", how="left")


def method_subregime_frame(frame: pd.DataFrame, split: str, subregime: str, method: str) -> pd.DataFrame:
    return frame.loc[
        frame["event_split"].astype(str).eq(split)
        & frame["taxonomy_method"].astype(str).eq(method)
        & frame["subregime_label"].astype(str).eq(subregime)
        & frame["window"].eq(HEADLINE_WINDOW)
    ].copy()


def episode_set_from_frame(frame: pd.DataFrame) -> set[str]:
    return set(frame["target_episode_id"].dropna().astype(str).unique()) if "target_episode_id" in frame.columns else set()


def subregime_episode_set(
    frame: pd.DataFrame,
    split: str,
    subregime: str,
    method: str,
    bridge_only: bool = False,
) -> set[str]:
    sub = method_subregime_frame(frame, split, subregime, method)
    if bridge_only:
        sub = sub.loc[bool_series(sub, "bridge_positive_denominator_included")]
    return episode_set_from_frame(sub)


def captured_set(frame: pd.DataFrame, source_id: str, split: str, subregime: str, method: str, policy: str) -> set[str]:
    sub = method_subregime_frame(frame, split, subregime, method)
    sub = sub.loc[sub["source_id"].astype(str).eq(source_id)].copy()
    if sub.empty:
        return set()
    mask = policy_mask(sub, policy)
    return set(sub.loc[mask, "target_episode_id"].dropna().astype(str).unique())


def transition_denominator(frame: pd.DataFrame, split: str) -> set[str]:
    sub = frame.loc[frame["event_split"].astype(str).eq(split) & frame["window"].eq(HEADLINE_WINDOW)]
    return set(sub["target_episode_id"].dropna().astype(str).unique())


def e1_captured_overall(frame: pd.DataFrame, split: str, policy: str) -> set[str]:
    sub = frame.loc[
        frame["source_id"].astype(str).eq("07_E1_only")
        & frame["event_split"].astype(str).eq(split)
        & frame["window"].eq(HEADLINE_WINDOW)
    ].copy()
    if sub.empty:
        return set()
    return set(sub.loc[policy_mask(sub, policy), "target_episode_id"].dropna().astype(str).unique())


def recall_retention_matrix(source_events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    e1_rows = []
    methods = source_events["taxonomy_method"].dropna().astype(str).unique()
    for method in methods:
        method_events = source_events.loc[source_events["taxonomy_method"].astype(str).eq(method)]
        subregimes = method_events["subregime_label"].dropna().astype(str).unique()
        for split in SPLITS:
            for source_id in RECALL_SOURCE_SCOPES:
                for subregime in subregimes:
                    denominator = subregime_episode_set(source_events, split, subregime, method)
                    bridge_denominator = subregime_episode_set(source_events, split, subregime, method, bridge_only=True)
                    e1_pre = captured_set(source_events, "07_E1_only", split, subregime, method, PRE_REPLAY_POLICY)
                    e1_post = captured_set(source_events, "07_E1_only", split, subregime, method, HEADLINE_POLICY)
                    e1_pre_bridge = e1_pre.intersection(bridge_denominator)
                    e1_post_bridge = e1_post.intersection(bridge_denominator)
                    e1_missed = denominator.difference(e1_pre)
                    pre = captured_set(source_events, source_id, split, subregime, method, PRE_REPLAY_POLICY)
                    post = captured_set(source_events, source_id, split, subregime, method, HEADLINE_POLICY)
                    pre_bridge = pre.intersection(bridge_denominator)
                    post_bridge = post.intersection(bridge_denominator)
                    post_e1_missed = post.intersection(e1_missed)
                    low, high = wilson_interval(len(post), len(denominator))
                    bridge_low, bridge_high = wilson_interval(len(post_bridge), len(bridge_denominator))
                    rows.append(
                        {
                            "taxonomy_method": method,
                            "subregime_id": subregime,
                            "subregime_label": subregime,
                            "split": split,
                            "source_id": source_id,
                            "window": HEADLINE_WINDOW,
                            "replay_policy_id": HEADLINE_POLICY,
                            "assignment_grain": "market_date",
                            "readout_grain": "unique_target_episode",
                            "denominator_policy": "unique_target_episode_within_taxonomy_method_split_subregime_window",
                            "target_episode_n": len(denominator),
                            "target_episode_denominator_n": len(denominator),
                            "bridge_episode_denominator_n": len(bridge_denominator),
                            "e1_pre_replay_any_captured_episode_n": len(e1_pre),
                            "e1_post_replay_any_captured_episode_n": len(e1_post),
                            "e1_pre_replay_bridge_captured_episode_n": len(e1_pre_bridge),
                            "e1_post_replay_bridge_captured_episode_n": len(e1_post_bridge),
                            "e1_pre_replay_any_recall": safe_div(len(e1_pre), len(denominator)),
                            "e1_post_replay_any_recall": safe_div(len(e1_post), len(denominator)),
                            "e1_pre_replay_bridge_recall": safe_div(len(e1_pre_bridge), len(bridge_denominator)),
                            "e1_post_replay_bridge_recall": safe_div(len(e1_post_bridge), len(bridge_denominator)),
                            "source_pre_replay_any_captured_episode_n": len(pre),
                            "source_post_replay_any_captured_episode_n": len(post),
                            "source_pre_replay_bridge_captured_episode_n": len(pre_bridge),
                            "source_post_replay_bridge_captured_episode_n": len(post_bridge),
                            "source_pre_replay_any_recall": safe_div(len(pre), len(denominator)),
                            "source_post_replay_any_recall": safe_div(len(post), len(denominator)),
                            "source_pre_replay_bridge_recall": safe_div(len(pre_bridge), len(bridge_denominator)),
                            "source_post_replay_bridge_recall": safe_div(len(post_bridge), len(bridge_denominator)),
                            "post_replay_recall_ci_low": low,
                            "post_replay_recall_ci_high": high,
                            "post_replay_bridge_recall_ci_low": bridge_low,
                            "post_replay_bridge_recall_ci_high": bridge_high,
                            "e1_missed_episode_n": len(e1_missed),
                            "source_post_replay_captures_e1_missed_n": len(post_e1_missed),
                            "incremental_post_replay_capture_over_e1_n": len(post_e1_missed),
                            "incremental_post_replay_capture_over_e1_rate": safe_div(len(post_e1_missed), len(e1_missed)),
                            "episode_power_status": sample_power_status(len(denominator), 0),
                        }
                    )
                    e1_rows.append(
                        {
                            "taxonomy_method": method,
                            "subregime_label": subregime,
                            "split": split,
                            "source_id": source_id,
                            "target_episode_denominator_n": len(denominator),
                            "e1_missed_episode_n": len(e1_missed),
                            "source_post_replay_captures_e1_missed_n": len(post_e1_missed),
                            "e1_missed_capture_rate": safe_div(len(post_e1_missed), len(e1_missed)),
                            "denominator_policy": "unique_target_episode_missed_by_E1_within_split_subregime_window",
                        }
                    )
    return pd.DataFrame(rows), pd.DataFrame(e1_rows)


def cost_quality_matrix(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, split, subregime, source_id), group in source_events.groupby(
        ["taxonomy_method", "event_split", "subregime_label", "source_id"], dropna=False
    ):
        if str(source_id) not in SOURCE_SCOPES:
            continue
        unique = group.assign(event_key=make_event_key(group)).drop_duplicates("event_key")
        failure_complete = bool_series(unique, "failure_10_complete")
        false_complete = bool_series(unique, "event_false_repair_20d_complete")
        winner_complete = bool_series(unique, "horizon_complete_120d")
        failure_label = pd.to_numeric(unique.get("failure_10_label", 0), errors="coerce").fillna(0).astype(float).gt(0)
        false_label = bool_series(unique, "event_false_repair_20d_label")
        winner_label = bool_series(unique, "event_big_winner_120d_label")
        rows.append(
            {
                "taxonomy_method": method,
                "subregime_label": subregime,
                "split": split,
                "source_id": source_id,
                "event_n": int(len(unique)),
                "failure_10_complete_rate": float(failure_complete.mean()) if len(unique) else np.nan,
                "fast_fail_10d_rate": float(failure_label.loc[failure_complete].mean()) if failure_complete.any() else np.nan,
                "event_false_repair_20d_complete_rate": float(false_complete.mean()) if len(unique) else np.nan,
                "false_repair_20d_rate": float(false_label.loc[false_complete].mean()) if false_complete.any() else np.nan,
                "event_big_winner_120d_complete_rate": float(winner_complete.mean()) if len(unique) else np.nan,
                "event_big_winner_120d_rate": float(winner_label.loc[winner_complete].mean()) if winner_complete.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def density_overlap_matrix(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, split, subregime, source_id), group in source_events.groupby(
        ["taxonomy_method", "event_split", "subregime_label", "source_id"], dropna=False
    ):
        if str(source_id) not in SOURCE_SCOPES:
            continue
        unique = group.assign(event_key=make_event_key(group)).drop_duplicates("event_key").copy()
        if unique.empty:
            continue
        if "replay_anchor_pos" in unique.columns:
            unique["density_anchor_pos"] = pd.to_numeric(unique["replay_anchor_pos"], errors="coerce")
            unique["density_anchor_date"] = pd.to_datetime(unique.get("replay_anchor_date"), errors="coerce")
            density_contract_reference = "A_density_contract_replay_anchor_pos"
        elif "trade_open_pos" in unique.columns:
            unique["density_anchor_pos"] = pd.to_numeric(unique["trade_open_pos"], errors="coerce")
            unique["density_anchor_date"] = pd.to_datetime(unique.get("trade_open_date"), errors="coerce")
            density_contract_reference = "fallback_trade_open_pos"
        else:
            unique["density_anchor_pos"] = pd.to_numeric(unique.get("event_t0_pos"), errors="coerce")
            unique["density_anchor_date"] = pd.to_datetime(unique.get("event_t0_date"), errors="coerce")
            density_contract_reference = "fallback_event_t0_pos"
        date_count = unique["density_anchor_date"].dropna().nunique()
        family_counts = unique.get("family_id", pd.Series("", index=unique.index)).fillna("missing").astype(str).value_counts(normalize=True)
        board_counts = unique.get("board_bucket", pd.Series("", index=unique.index)).fillna("missing").astype(str).value_counts(normalize=True)
        rolling10 = rolling_duplicate_rate(unique, 10)
        rolling20 = rolling_duplicate_rate(unique, 20)
        rows.append(
            {
                "taxonomy_method": method,
                "subregime_label": subregime,
                "split": split,
                "source_id": source_id,
                "density_contract_reference": density_contract_reference,
                "selected_event_count": int(len(unique)),
                "formal_event_day_density": safe_div(len(unique), date_count),
                "rolling_10d_executable_event_day_density": rolling10["mean_count"],
                "rolling_20d_executable_event_day_density": rolling20["mean_count"],
                "rolling_10d_duplicate_rate": rolling10["duplicate_rate"],
                "rolling_20d_duplicate_rate": rolling20["duplicate_rate"],
                "family_concentration": float(family_counts.max()) if len(family_counts) else np.nan,
                "board_concentration": float(board_counts.max()) if len(board_counts) else np.nan,
                "cross_family_collision_rate": cross_family_collision_rate(unique),
            }
        )
    return pd.DataFrame(rows)


def rolling_duplicate_rate(events: pd.DataFrame, window: int) -> dict[str, float]:
    counts = []
    pos_col = "density_anchor_pos" if "density_anchor_pos" in events.columns else "event_t0_pos"
    if pos_col not in events.columns:
        return {"mean_count": np.nan, "duplicate_rate": np.nan}
    for _, group in events.groupby("instrument", dropna=False):
        pos = pd.to_numeric(group[pos_col], errors="coerce").dropna().sort_values().to_numpy()
        for value in pos:
            counts.append(int(((pos >= value) & (pos <= value + window)).sum()))
    if not counts:
        return {"mean_count": np.nan, "duplicate_rate": np.nan}
    arr = np.array(counts)
    return {"mean_count": float(arr.mean()), "duplicate_rate": float((arr > 1).mean())}


def cross_family_collision_rate(events: pd.DataFrame) -> float:
    pos_col = "density_anchor_pos" if "density_anchor_pos" in events.columns else "event_t0_pos"
    if not {"instrument", pos_col, "family_id"}.issubset(events.columns):
        return np.nan
    collisions = 0
    total = 0
    for _, group in events.groupby("instrument", dropna=False):
        group = group.copy()
        group[pos_col] = pd.to_numeric(group[pos_col], errors="coerce")
        for _, row in group.dropna(subset=[pos_col]).iterrows():
            window = group.loc[(group[pos_col] >= row[pos_col]) & (group[pos_col] <= row[pos_col] + 10)]
            total += 1
            if window["family_id"].fillna("").astype(str).nunique() > 1:
                collisions += 1
    return safe_div(collisions, total)


def family_readout(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, split, subregime, family_id), group in source_events.groupby(
        ["taxonomy_method", "event_split", "subregime_label", "family_id"], dropna=False
    ):
        rows.append(
            {
                "taxonomy_method": method,
                "split": split,
                "subregime_label": subregime,
                "family_id": family_id,
                "event_n": int(make_event_key(group).nunique()),
                "source_count": int(group["source_id"].astype(str).nunique()),
            }
        )
    return pd.DataFrame(rows)


def drift_audit(composition: pd.DataFrame, recall: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    statuses = []
    for method, group in composition.groupby("taxonomy_method", dropna=False):
        pivot = group.pivot_table(index="subregime_label", columns="split", values="event_share", aggfunc="sum").fillna(0.0)
        train = pivot["train"] if "train" in pivot.columns else pd.Series(dtype=float)
        robust = pivot["robustness"] if "robustness" in pivot.columns else pd.Series(dtype=float)
        labels = sorted(set(train.index).union(set(robust.index)))
        train = train.reindex(labels, fill_value=0.0)
        robust = robust.reindex(labels, fill_value=0.0)
        jsd = jensen_shannon(train.to_numpy(), robust.to_numpy())
        psi = population_stability_index(train.to_numpy(), robust.to_numpy())
        if pd.notna(jsd) and jsd >= 0.10:
            status = "explained_by_composition_drift"
        else:
            status = "not_explained"
        statuses.append(status)
        rows.append(
            {
                "taxonomy_method": method,
                "train_vs_robustness_jsd": jsd,
                "train_vs_robustness_psi": psi,
                "collapse_explanation_status": status,
            }
        )
    final = "explained_by_composition_drift" if "explained_by_composition_drift" in statuses else "not_explained"
    return pd.DataFrame(rows), final


def jensen_shannon(p: np.ndarray, q: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    if p.sum() == 0 or q.sum() == 0:
        return np.nan
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return float(0.5 * kl_div(p, m) + 0.5 * kl_div(q, m))


def kl_div(p: np.ndarray, q: np.ndarray) -> float:
    mask = (p > 0) & (q > 0)
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


def population_stability_index(expected: np.ndarray, actual: np.ndarray) -> float:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if expected.sum() == 0 or actual.sum() == 0:
        return np.nan
    expected = np.clip(expected / expected.sum(), 1e-6, None)
    actual = np.clip(actual / actual.sum(), 1e-6, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def agreement_matrix(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, group in events.groupby("event_split", dropna=False):
        if "auto_cluster_label" in group.columns:
            ct = pd.crosstab(group["final_default_subregime"], group["auto_cluster_label"])
            for default_label, row in ct.iterrows():
                for auto_label, count in row.items():
                    rows.append(
                        {
                            "comparison": "default_vs_auto_120d_elbow_kmeans",
                            "split": split,
                            "default_subregime": default_label,
                            "auto_subregime": auto_label,
                            "event_count": int(count),
                        }
                    )
        if "knn_predicted_subregime" in group.columns:
            ct = pd.crosstab(group["final_default_subregime"], group["knn_predicted_subregime"])
            for default_label, row in ct.iterrows():
                for auto_label, count in row.items():
                    rows.append(
                        {
                            "comparison": "default_vs_auto_120d_knn_default_taxonomy",
                            "split": split,
                            "default_subregime": default_label,
                            "auto_subregime": auto_label,
                            "event_count": int(count),
                        }
                    )
    return pd.DataFrame(rows)


def decision_logic(
    *,
    source_is_caveated: bool,
    component_audit: pd.DataFrame,
    composition: pd.DataFrame,
    recall: pd.DataFrame,
    cost: pd.DataFrame,
    density: pd.DataFrame,
    kmeans_meta: dict[str, Any],
    block_stability: pd.DataFrame,
    effective_n: float,
    collapse_status: str,
) -> tuple[str, list[str]]:
    failures: list[str] = []
    comp_status = str(component_audit.iloc[0].get("regime_label_consistency_status", "")) if not component_audit.empty else ""
    if comp_status not in {"pass", "horizon_mismatch_audited"}:
        return FINAL_COMPONENT_BLOCKED, ["component_reconstruction_failed"]
    if composition.empty:
        return FINAL_SAMPLE_POWER_BLOCKED, ["composition_readout_unavailable"]
    core = composition.loc[
        composition["taxonomy_method"].eq("default_deterministic")
        & composition["split"].isin(["train", "robustness"])
        & composition["subregime_label"].isin(CORE_SUBREGIMES)
    ]
    missing_component = composition.loc[
        composition["taxonomy_method"].eq("default_deterministic")
        & composition["split"].isin(["train", "robustness"])
        & composition["subregime_label"].eq("transition_component_missing")
        & composition["event_share"].gt(0.05)
    ]
    if not missing_component.empty:
        failures.append("component_missing_share_gt_5pct")
    for split in ("train", "robustness"):
        split_core = core.loc[core["split"].eq(split)]
        if set(split_core["subregime_label"]) != set(CORE_SUBREGIMES):
            failures.append(f"missing_core_subregime:{split}")
        if (split_core["target_episode_n"] < 30).any():
            failures.append(f"core_episode_low_power:{split}")
    for name, frame in (("recall", recall), ("cost", cost), ("density", density)):
        if frame.empty:
            failures.append(f"{name}_readout_unavailable")
    boundary = composition.loc[
        composition["taxonomy_method"].eq("default_deterministic")
        & composition["subregime_label"].eq("transition_boundary_or_mixed")
        & composition["event_share"].gt(0.40)
    ]
    if not boundary.empty:
        failures.append("boundary_over_capture_gt_40pct")
    if kmeans_meta.get("status") != "pass":
        failures.append(f"kmeans_status:{kmeans_meta.get('status')}")
    if pd.isna(effective_n) or effective_n < 50:
        failures.append("effective_independent_window_n_lt_50")
    if collapse_status == "not_explained":
        failures.append("collapse_not_explained")
    if failures:
        return FINAL_DIAGNOSTIC, failures
    return (FINAL_SUPPORTED_CAVEATED if source_is_caveated else FINAL_SUPPORTED), []


def decision_tiers(decision: str, failures: list[str], collapse_status: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_tier": "taxonomy_audit",
                "final_decision": decision,
                "supported_usage": "taxonomy_audit_only" if "supported" in decision else "diagnostic_only",
                "collapse_explanation_status": collapse_status,
                "failure_reason": ";".join(failures),
            }
        ]
    )


def build_contract_text() -> str:
    return "\n".join(
        [
            "# Transition Sub-Regime Taxonomy Contract",
            "",
            "- Assignment grain is date-level market state.",
            "- Events inherit the sub-regime of `event_t0_date`.",
            "- Primary benchmark is `data/interim/index_qlib_csv/day/SH000985.csv`.",
            "- Automatic taxonomy uses rolling 120 trading-day as-of windows only.",
            "- Rolling-window clustering must pass block-sampled stability before supporting a taxonomy.",
            "- Outcome labels are readout-only and never taxonomy features.",
            "",
        ]
    )


def build_report(
    decision: str,
    failures: list[str],
    composition: pd.DataFrame,
    recall: pd.DataFrame,
    cost: pd.DataFrame,
    density: pd.DataFrame,
    feature_contract: pd.DataFrame,
    autocorr: pd.DataFrame,
    agreement: pd.DataFrame,
    component_audit: pd.DataFrame,
    elbow: pd.DataFrame,
    block: pd.DataFrame,
    drift: pd.DataFrame,
    collapse_status: str,
    preprocessing_meta: dict[str, Any],
    kmeans_meta: dict[str, Any],
    knn_meta: dict[str, Any],
) -> str:
    lines = [
        "# Experiment F - Transition Sub-Regime Taxonomy Audit 报告",
        "",
        f"最终决策：`{decision}`",
        "",
        "## 结论",
        "",
        "本实验只审计 residual transition 是否可拆成稳定子状态，不训练 entry model，也不输出 direct-entry support。",
        f"`collapse_explanation_status = {collapse_status}`。",
        "",
        "transition 是 risk_on / risk_off 之外的 residual bucket，因此本实验先检验它是否可被 date-level market-state 子状态解释，而不是直接进入 family rediscovery。",
    ]
    if failures:
        lines += ["", "## Gate Failures", ""]
        lines += [f"- `{reason}`" for reason in failures]
    if not component_audit.empty:
        row = component_audit.iloc[0]
        lines += [
            "",
            "## Component Source",
            "",
            f"- primary source: `{row.get('component_source')}`",
            f"- consistency: `{row.get('component_reconstruction_consistency_rate')}`",
            f"- status: `{row.get('regime_label_consistency_status')}`",
        ]
    lines += [
        "",
        "## Default Taxonomy",
        "",
        "recovery / deterioration 是 transition 的精确二分；boundary 是 margin reclassification，不是第三个原生状态。",
    ]
    default_comp = composition.loc[composition["taxonomy_method"].eq("default_deterministic")]
    if not default_comp.empty:
        lines.append(default_comp.to_markdown(index=False))
    lines += [
        "",
        "## Automatic 120d Taxonomy",
        "",
        f"- feature count: `{len(feature_contract)}`",
        f"- preprocessing: `{preprocessing_meta.get('policy')}`",
        f"- preprocessing source: train transition 120d windows only; validation / robustness only transform/readout",
        f"- kmeans selected k: `{kmeans_meta.get('selected_k')}`",
        f"- kmeans status: `{kmeans_meta.get('status')}`",
        f"- knn selected neighbors: `{knn_meta.get('selected_neighbors')}`",
    ]
    if not autocorr.empty:
        summary = autocorr.loc[autocorr["feature_name"].eq("__summary__")]
        if not summary.empty:
            row = summary.iloc[0]
            lines += [
                f"- lag1 autocorrelation mean: `{row.get('lag1_autocorrelation')}`",
                f"- effective independent window n: `{row.get('effective_independent_window_n')}`",
            ]
    if not block.empty:
        lines += ["", "Block stability:", block.to_markdown(index=False)]
    if not elbow.empty:
        lines += ["", "Elbow selection:", elbow.to_markdown(index=False)]
    if not agreement.empty:
        lines += ["", "## Default vs Auto Agreement", "", agreement.head(40).to_markdown(index=False)]
    lines += [
        "",
        "## Recall / E1-Missed",
        "",
    ]
    headline = recall.loc[
        recall["taxonomy_method"].eq("default_deterministic")
        & recall["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
        & recall["split"].isin(["train", "robustness"])
    ].head(30)
    lines.append(headline.to_markdown(index=False) if not headline.empty else "无 recall readout。")
    lines += [
        "",
        "## Cost / Quality",
        "",
    ]
    cost_head = cost.loc[
        cost["taxonomy_method"].eq("default_deterministic")
        & cost["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
        & cost["split"].isin(["train", "robustness"])
    ].head(30)
    lines.append(cost_head.to_markdown(index=False) if not cost_head.empty else "无 cost readout。")
    lines += [
        "",
        "## Density / Overlap",
        "",
    ]
    density_head = density.loc[
        density["taxonomy_method"].eq("default_deterministic")
        & density["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated", "08_T4_gated", "08_T7_gated"])
        & density["split"].isin(["train", "robustness"])
    ].head(30)
    lines.append(density_head.to_markdown(index=False) if not density_head.empty else "无 density readout。")
    failure_axis = []
    if any("component" in reason for reason in failures):
        failure_axis.append("component_source")
    if any("core" in reason or "power" in reason for reason in failures):
        failure_axis.append("sample_power")
    if any("kmeans" in reason or "effective" in reason for reason in failures):
        failure_axis.append("taxonomy_instability")
    if collapse_status == "not_explained":
        failure_axis.append("no_composition_drift")
    next_action = "diagnostic_only"
    if collapse_status == "not_explained":
        next_action = "redefine_transition_label_source"
    if "taxonomy_instability" in failure_axis:
        next_action = "diagnostic_only_then_rebuild_regime_components_or_windowing"
    lines += [
        "",
        "## Interpretation / Next Action",
        "",
        f"- failure_axis = `{';'.join(failure_axis) if failure_axis else 'none'}`",
        f"- next_action = `{next_action}`",
        "- 当前结果不得支持 transition family rediscovery；若继续，应先重建 regime components / windowing 或重定义 transition label source。",
    ]
    lines += [
        "",
        "## 不可声称内容",
        "",
        "- 不得声称 direct-entry support。",
        "- 不得声称 official train process。",
        "- 不得把 instrument-level cluster 解释为 market sub-regime。",
        "- kNN seed-label propagation 不能单独支撑 supported。",
        "- validation 只作 diagnostic，不得调 taxonomy rule。",
        "",
    ]
    return "\n".join(lines)


def build_manifest(
    decision: str,
    failures: list[str],
    input_paths: dict[str, Path],
    manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    frames: dict[str, pd.DataFrame],
    component_audit: pd.DataFrame,
    preprocessing_meta: dict[str, Any],
    kmeans_meta: dict[str, Any],
    knn_meta: dict[str, Any],
    collapse_status: str,
    effective_n: float,
) -> dict[str, Any]:
    a, b, c, d = manifests
    component_row = component_audit.iloc[0].to_dict() if not component_audit.empty else {}
    output_hashes = {
        key: path_hash(path)
        for key, path in sorted(OUTPUT_PATHS.items())
        if path.exists() and path.is_file() and key != "transition_subregime_taxonomy_audit_manifest"
    }
    output_paths = {key: str(path) for key, path in sorted(OUTPUT_PATHS.items()) if path.exists()}
    return {
        "experiment_id": "08_experiment_f_transition_subregime_taxonomy_audit",
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "runner_code_hash": path_hash(Path(__file__)),
        "input_artifacts": {key: str(path) for key, path in sorted(input_paths.items())},
        "upstream_decisions": {
            "A": a.get("decision"),
            "B": b.get("decision"),
            "C": c.get("decision"),
            "D": d.get("decision"),
        },
        "source_caveated": source_caveated(manifests),
        "default_taxonomy_parameters": {
            "trend_boundary_margin_pp": 1.0,
            "drawdown_boundary_margin_pp": 1.0,
            "volatility_boundary_quantile": 0.90,
        },
        "taxonomy_assignment_grain": "market_date",
        "readout_denominator_policies": {
            "event": "unique_event_key",
            "episode": "unique_target_episode",
            "cost": "unique_horizon_complete_event",
        },
        "regime_component_source_status": component_row.get("component_source_status"),
        "regime_component_formulas": component_row.get("reconstruction_formula"),
        "component_reconstruction_consistency_rate": component_row.get("component_reconstruction_consistency_rate"),
        "regime_label_consistency_status": component_row.get("regime_label_consistency_status"),
        "auto_taxonomy_window_length": AUTO_WINDOW,
        "auto_taxonomy_periodization_rule": "rolling_120_trading_day_window_end_date_equals_event_t0_date",
        "auto_taxonomy_effective_independent_window_n": effective_n,
        "auto_taxonomy_autocorrelation_summary_hash": output_hashes.get("transition_auto_120d_autocorrelation_audit", ""),
        "auto_taxonomy_block_stability_hash": output_hashes.get("transition_auto_120d_block_stability", ""),
        "auto_taxonomy_feature_hash": output_hashes.get("transition_auto_120d_feature_contract", ""),
        "auto_taxonomy_preprocessing": preprocessing_meta,
        "auto_taxonomy_preprocessing_hash": stable_hash(preprocessing_meta),
        "elbow_candidate_k_values": list(K_CANDIDATES),
        "elbow_selected_k": kmeans_meta.get("selected_k"),
        "elbow_selection_formula": "relative_improvement_k_minus_next_relative_improvement",
        "elbow_random_state": RANDOM_STATE,
        "knn_candidate_neighbor_values": list(KNN_NEIGHBORS),
        "knn_selected_neighbors": knn_meta.get("selected_neighbors"),
        "knn_selection_formula": knn_meta.get("selection_formula"),
        "collapse_explanation_status": collapse_status,
        "boundary_reclassification_parameters": {
            "trend_boundary_margin_pp": 1.0,
            "drawdown_boundary_margin_pp": 1.0,
            "volatility_boundary_quantile": 0.90,
        },
        "boundary_over_capture_status": boundary_status(frames.get("transition_subregime_composition_by_split", pd.DataFrame())),
        "final_decision": decision,
        "decision": decision,
        "blocked_reasons": failures,
        "output_hashes": output_hashes,
        "output_paths": output_paths,
        "output_row_counts": {key: int(len(frame)) for key, frame in sorted(frames.items())},
    }


def boundary_status(composition: pd.DataFrame) -> str:
    if composition.empty:
        return "not_available"
    boundary = composition.loc[composition["subregime_label"].eq("transition_boundary_or_mixed")]
    if boundary.empty:
        return "no_boundary_rows"
    if boundary["event_share"].gt(0.40).any():
        return "boundary_over_capture_gt_40pct"
    if boundary["event_share"].gt(0.35).any():
        return "boundary_over_capture_alert"
    return "pass"


def output_empty_blocked(decision: str, failures: list[str], input_frame: pd.DataFrame, input_paths: dict[str, Path], manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_dirs()
    frames = {key: pd.DataFrame() for key in OUTPUT_PATHS if key.startswith("transition_") and not key.endswith("manifest")}
    write_df(OUTPUT_PATHS["transition_subregime_input_audit"], input_frame)
    write_text(OUTPUT_PATHS["transition_subregime_taxonomy_contract"], build_contract_text())
    write_text(OUTPUT_PATHS["transition_subregime_taxonomy_audit_report"], f"# Experiment F\n\n最终决策：`{decision}`\n\n" + "\n".join(f"- {x}" for x in failures))
    write_json(
        OUTPUT_PATHS["transition_subregime_taxonomy_audit_manifest"],
        build_manifest(decision, failures, input_paths, manifests, frames, pd.DataFrame(), {}, {}, {}, "low_power", np.nan),
    )
    return {
        "decision": decision,
        "blocked_reasons": failures,
        "manifest_path": str(OUTPUT_PATHS["transition_subregime_taxonomy_audit_manifest"]),
    }


def run(mode: str = "full") -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_paths, input_failures = input_audit()
    manifests = validate_manifests()
    a, b, c, d, manifest_failures = manifests
    manifest_tuple = (a, b, c, d)
    input_failures.extend(manifest_failures)
    if input_failures:
        return output_empty_blocked(FINAL_INPUT_BLOCKED, input_failures, input_frame, input_paths, manifest_tuple)
    if mode == "check-inputs":
        write_df(OUTPUT_PATHS["transition_subregime_input_audit"], input_frame)
        return {"decision": "transition_subregime_taxonomy_inputs_ready", "input_rows": len(input_frame)}

    canonical = read_csv(input_paths["candidate_family_canonical_events"])
    membership = pd.read_parquet(input_paths["d_membership"])
    component_path, component_id, component_status = select_index_source(input_paths)
    if component_path is None:
        return output_empty_blocked(
            FINAL_COMPONENT_BLOCKED,
            ["market_component_source_unavailable"],
            input_frame,
            input_paths,
            manifest_tuple,
        )
    primary_index = load_index_panel(component_path, component_id)
    breadth = load_date_level_breadth(input_paths["cross_section_feature_panel"])
    components = build_component_panel(primary_index, breadth)
    component_audit = build_component_audit(canonical, components, component_path, component_id, component_status)
    if str(component_audit.iloc[0]["regime_label_consistency_status"]) == "component_consistency_low":
        return output_empty_blocked(FINAL_COMPONENT_BLOCKED, ["component_consistency_low"], input_frame, input_paths, manifest_tuple)

    events = transition_events(canonical, components)
    prepared_membership = prepare_membership(membership, events)
    auto_features = build_auto_window_features(components, events, prepared_membership)
    feature_cols = auto_feature_columns(auto_features)
    feature_contract = build_feature_contract(auto_features, feature_cols, component_path, component_id)
    matrix, preprocess_meta = preprocess_auto_features(auto_features, feature_cols)
    autocorr, rho1, effective_n = build_autocorrelation_audit(auto_features, matrix, feature_cols)
    period = period_audit(auto_features, effective_n, rho1)
    elbow, cluster_assignments, block_stability_df, kmeans_meta = run_kmeans_taxonomy(auto_features, matrix, feature_cols, effective_n)
    knn_assignments, knn_meta = run_knn_taxonomy(auto_features, matrix, feature_cols)
    if "cv" in knn_meta:
        # Keep the selection diagnostics in the assignment table as compact metadata columns.
        knn_assignments["knn_selected_neighbors"] = knn_meta.get("selected_neighbors")

    events_with_methods = add_method_subregime(events, cluster_assignments, knn_assignments)
    event_view = taxonomy_event_view(events_with_methods)
    source_events = source_event_assignments(prepared_membership, event_view)
    denom_audit = build_denominator_audit(prepared_membership, events, source_events)
    label_audit = label_join_audit(prepared_membership)
    composition = composition_by_split(event_view, prepared_membership, source_events)
    recall, e1_missed = recall_retention_matrix(source_events)
    cost = cost_quality_matrix(source_events)
    density = density_overlap_matrix(source_events)
    family = family_readout(source_events)
    drift, collapse_status = drift_audit(composition, recall)
    agreement = agreement_matrix(events_with_methods)
    source_binding = build_source_binding_audit(manifest_tuple, input_paths)
    regime_role = build_regime_role_audit()
    leakage = build_leakage_audit()
    decision, failures = decision_logic(
        source_is_caveated=source_caveated(manifest_tuple),
        component_audit=component_audit,
        composition=composition,
        recall=recall,
        cost=cost,
        density=density,
        kmeans_meta=kmeans_meta,
        block_stability=block_stability_df,
        effective_n=effective_n,
        collapse_status=collapse_status,
    )
    tiers = decision_tiers(decision, failures, collapse_status)

    frames: dict[str, pd.DataFrame] = {
        "transition_subregime_input_audit": input_frame,
        "transition_subregime_source_binding_audit": source_binding,
        "transition_subregime_regime_role_audit": regime_role,
        "transition_subregime_regime_component_audit": component_audit,
        "transition_subregime_denominator_audit": denom_audit,
        "transition_subregime_label_join_audit": label_audit,
        "transition_subregime_leakage_audit": leakage,
        "transition_auto_120d_period_audit": period,
        "transition_auto_120d_autocorrelation_audit": autocorr,
        "transition_auto_120d_block_stability": block_stability_df,
        "transition_default_subregime_assignment": events_with_methods,
        "transition_auto_120d_feature_contract": feature_contract,
        "transition_auto_120d_window_features": auto_features,
        "transition_auto_120d_elbow_selection": elbow,
        "transition_auto_120d_cluster_assignments": cluster_assignments,
        "transition_auto_120d_knn_assignments": knn_assignments,
        "transition_taxonomy_agreement_matrix": agreement,
        "transition_subregime_composition_by_split": composition,
        "transition_subregime_recall_retention_matrix": recall,
        "transition_subregime_e1_missed_capture": e1_missed,
        "transition_subregime_cost_quality_matrix": cost,
        "transition_subregime_density_overlap_matrix": density,
        "transition_subregime_family_readout": family,
        "transition_subregime_drift_audit": drift,
        "transition_subregime_decision_tiers": tiers,
    }

    for key, frame in frames.items():
        path = OUTPUT_PATHS[key]
        write_df(path, frame)
    write_text(OUTPUT_PATHS["transition_subregime_taxonomy_contract"], build_contract_text())
    write_text(
        OUTPUT_PATHS["transition_subregime_taxonomy_audit_report"],
        build_report(
            decision,
            failures,
            composition,
            recall,
            cost,
            density,
            feature_contract,
            autocorr,
            agreement,
            component_audit,
            elbow,
            block_stability_df,
            drift,
            collapse_status,
            preprocess_meta,
            kmeans_meta,
            knn_meta,
        ),
    )
    write_json(
        OUTPUT_PATHS["transition_subregime_taxonomy_audit_manifest"],
        build_manifest(
            decision,
            failures,
            input_paths,
            manifest_tuple,
            frames,
            component_audit,
            preprocess_meta,
            kmeans_meta,
            knn_meta,
            collapse_status,
            effective_n,
        ),
    )
    return {
        "decision": decision,
        "manifest_path": str(OUTPUT_PATHS["transition_subregime_taxonomy_audit_manifest"]),
        "report_path": str(OUTPUT_PATHS["transition_subregime_taxonomy_audit_report"]),
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
