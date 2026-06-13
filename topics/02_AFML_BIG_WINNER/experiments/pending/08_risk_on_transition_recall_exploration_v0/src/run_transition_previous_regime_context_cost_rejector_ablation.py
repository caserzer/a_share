#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402

import run_risk_on_post_filter_cost_rejector as e_runner  # noqa: E402


REQUIREMENT_PATH = (
    EXPERIMENT_DIR
    / "requirement_experiment_i_transition_previous_regime_context_cost_rejector_ablation.md"
)
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

I_TABLE_DIR = TABLE_DIR / "transition_previous_regime_context_cost_rejector_ablation"
I_REPORT_DIR = REPORT_DIR / "transition_previous_regime_context_cost_rejector_ablation"
I_MANIFEST_DIR = MANIFEST_DIR / "transition_previous_regime_context_cost_rejector_ablation"
I_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "transition_previous_regime_context_cost_rejector_ablation"

G_TABLE_DIR = TABLE_DIR / "transition_previous_regime_outcome_audit"
G_MANIFEST_DIR = MANIFEST_DIR / "transition_previous_regime_outcome_audit"
H_TABLE_DIR = TABLE_DIR / "risk_on_cost_rejector_research_entry_hardening"
H_MANIFEST_DIR = MANIFEST_DIR / "risk_on_cost_rejector_research_entry_hardening"
D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"
E_MANIFEST_DIR = MANIFEST_DIR / "risk_on_post_filter_cost_rejector"

TARGET_LABEL = "cost_bad_10_20"
SOURCE_POOL = "transition_previous_regime_primary"
MODEL_TYPE = "logistic_regression_balanced_l2"
TARGET_REGIME = "transition"
HEADLINE_WINDOW = e_runner.HEADLINE_WINDOW
HEADLINE_POLICY = e_runner.HEADLINE_POLICY
SPLITS = ("train", "validation", "robustness")
KEEP_FRACTIONS = (0.90, 0.875, 0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70)
PRIMARY_CONTEXTS = ("transition_from_risk_on", "transition_from_risk_off")
PRIMARY_BINDING_STATUSES = (
    "published_and_reconstructed_transition",
    "reconstructed_transition_not_published_transition",
)
FINAL_UPLIFT = "transition_previous_regime_context_cost_rejector_diagnostic_uplift_observed"
FINAL_NO_UPLIFT = "transition_previous_regime_context_cost_rejector_diagnostic_no_uplift"
FINAL_LOW_POWER = "transition_previous_regime_context_diagnostic_low_power"
FINAL_INPUT_BLOCKED = "transition_previous_regime_context_input_blocked"
FINAL_LEAKAGE_BLOCKED = "transition_previous_regime_context_feature_leakage_blocked"
FINAL_LABEL_BLOCKED = "transition_previous_regime_context_label_binding_blocked"
FINAL_G_HASH_BLOCKED = "transition_previous_regime_context_g_artifact_hash_blocked"
FINAL_H_HASH_BLOCKED = "transition_previous_regime_context_h_artifact_hash_blocked"
FINAL_GRID_BLOCKED = "transition_previous_regime_context_grid_binding_blocked"
FINAL_FUTURE_BLOCKED = "transition_previous_regime_context_future_outcome_leakage_blocked"

MODEL_ARMS = {
    "transition_cost_rejector_no_context": "H allowed t0 features only",
    "transition_cost_rejector_prev_context": "H allowed t0 features + PIT previous-regime context",
    "transition_cost_rejector_context_only": "PIT previous-regime context only",
}
CONTEXT_MODEL_FEATURES = [
    "pit_transition_context",
    "previous_non_transition_trading_day_n",
    "previous_non_transition_duration_bucket",
    "segment_age_at_event_t0",
    "observed_segment_trading_day_n_asof_t0",
    "days_since_previous_regime_end_asof_event",
]
CONTEXT_AUDIT_ONLY_FEATURES = ["previous_non_transition_regime"]
CONTEXT_CATEGORICAL_FEATURES = {"pit_transition_context", "previous_non_transition_duration_bucket"}
FORCED_DROP_FEATURES = {
    "momentum_percentile_20d_lag20",
    "event_regime_bucket",
    "market_regime_bucket",
    "published_market_regime_bucket",
    "reconstructed_market_regime_bucket",
    "universe_binding_status",
    "grid_rule_id",
    "rule_event_included",
    "online_confirmation_status",
    "source_pool",
}
FORBIDDEN_FUTURE_FEATURES = {
    "segment_end_date",
    "final_segment_trading_day_n",
    "final_segment_calendar_day_n",
    "segment_remaining_days_ex_post",
    "next_non_transition_regime",
    "next_non_transition_start_date",
    "days_to_next_regime_start",
    "transition_outcome_label",
    "transition_outcome_direction",
}
REQUIRED_G_ARTIFACT_KEYS = [
    "transition_previous_regime_event_assignment",
    "transition_previous_regime_segment_catalog",
    "transition_previous_regime_universe_binding_audit",
    "transition_previous_regime_leakage_audit",
    "transition_previous_regime_label_join_audit",
    "transition_previous_regime_segment_matrix",
    "transition_previous_regime_cost_quality_matrix",
    "transition_previous_regime_recall_retention_matrix",
    "transition_previous_regime_e1_missed_capture",
]
REQUIRED_H_ARTIFACT_KEYS = [
    "risk_on_hardening_feature_contract",
    "risk_on_hardening_feature_delta_from_e",
    "risk_on_hardening_asof_join_audit",
    "risk_on_hardening_model_registry",
]


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True


INPUT_SPECS = [
    InputSpec("requirement", REQUIREMENT_PATH),
    InputSpec(
        "g_manifest",
        G_MANIFEST_DIR / "transition_previous_regime_outcome_audit_manifest.json",
    ),
    InputSpec(
        "h_manifest",
        H_MANIFEST_DIR / "risk_on_cost_rejector_research_entry_hardening_manifest.json",
    ),
    InputSpec(
        "d_manifest",
        D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json",
    ),
    InputSpec(
        "e_manifest",
        E_MANIFEST_DIR / "risk_on_post_filter_cost_rejector_manifest.json",
    ),
    InputSpec("g_event_assignment", G_TABLE_DIR / "transition_previous_regime_event_assignment.csv.gz"),
    InputSpec("g_segment_catalog", G_TABLE_DIR / "transition_previous_regime_segment_catalog.csv"),
    InputSpec("g_universe_binding_audit", G_TABLE_DIR / "transition_previous_regime_universe_binding_audit.csv"),
    InputSpec("g_leakage_audit", G_TABLE_DIR / "transition_previous_regime_leakage_audit.csv"),
    InputSpec("g_label_join_audit", G_TABLE_DIR / "transition_previous_regime_label_join_audit.csv"),
    InputSpec("g_segment_matrix", G_TABLE_DIR / "transition_previous_regime_segment_matrix.csv"),
    InputSpec("g_cost_quality_matrix", G_TABLE_DIR / "transition_previous_regime_cost_quality_matrix.csv"),
    InputSpec("g_recall_retention_matrix", G_TABLE_DIR / "transition_previous_regime_recall_retention_matrix.csv"),
    InputSpec("g_e1_missed_capture", G_TABLE_DIR / "transition_previous_regime_e1_missed_capture.csv"),
    InputSpec("h_feature_contract", H_TABLE_DIR / "risk_on_hardening_feature_contract.csv"),
    InputSpec("h_feature_delta_from_e", H_TABLE_DIR / "risk_on_hardening_feature_delta_from_e.csv"),
    InputSpec("h_asof_join_audit", H_TABLE_DIR / "risk_on_hardening_asof_join_audit.csv"),
    InputSpec("h_model_registry", H_TABLE_DIR / "risk_on_hardening_model_registry.csv"),
    InputSpec("canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec("event_labels", LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet"),
    InputSpec("cross_section_feature_panel", LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet"),
    InputSpec("d_membership", D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet"),
    InputSpec("d_scope_retention", D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv"),
    InputSpec("d_label_leakage_audit", D_TABLE_DIR / "post_replay_label_leakage_audit.csv"),
]


OUTPUT_PATHS = {
    "transition_context_ablation_input_audit": I_TABLE_DIR / "transition_context_ablation_input_audit.csv",
    "transition_context_ablation_upstream_binding_audit": I_TABLE_DIR / "transition_context_ablation_upstream_binding_audit.csv",
    "transition_context_ablation_feature_contract": I_TABLE_DIR / "transition_context_ablation_feature_contract.csv",
    "transition_context_ablation_leakage_audit": I_TABLE_DIR / "transition_context_ablation_leakage_audit.csv",
    "transition_context_ablation_label_join_audit": I_TABLE_DIR / "transition_context_ablation_label_join_audit.csv",
    "transition_context_ablation_training_universe_audit": I_TABLE_DIR / "transition_context_ablation_training_universe_audit.csv",
    "transition_context_ablation_model_registry": I_TABLE_DIR / "transition_context_ablation_model_registry.csv",
    "transition_context_ablation_segment_grouped_stability": I_TABLE_DIR / "transition_context_ablation_segment_grouped_stability.csv",
    "transition_context_ablation_segment_grouped_uplift": I_TABLE_DIR / "transition_context_ablation_segment_grouped_uplift.csv",
    "transition_context_ablation_oos_separability": I_TABLE_DIR / "transition_context_ablation_oos_separability.csv",
    "transition_context_ablation_threshold_frontier": I_TABLE_DIR / "transition_context_ablation_threshold_frontier.csv",
    "transition_context_ablation_selected_threshold_readout": I_TABLE_DIR / "transition_context_ablation_selected_threshold_readout.csv",
    "transition_context_ablation_cost_quality_readout": I_TABLE_DIR / "transition_context_ablation_cost_quality_readout.csv",
    "transition_context_ablation_recall_retention_readout": I_TABLE_DIR / "transition_context_ablation_recall_retention_readout.csv",
    "transition_context_ablation_density_overlap_readout": I_TABLE_DIR / "transition_context_ablation_density_overlap_readout.csv",
    "transition_context_ablation_segment_concentration_audit": I_TABLE_DIR / "transition_context_ablation_segment_concentration_audit.csv",
    "transition_context_ablation_outcome_readout": I_TABLE_DIR / "transition_context_ablation_outcome_readout.csv",
    "transition_context_ablation_uplift_comparison": I_TABLE_DIR / "transition_context_ablation_uplift_comparison.csv",
    "transition_context_ablation_decision_tiers": I_TABLE_DIR / "transition_context_ablation_decision_tiers.csv",
    "transition_context_ablation_event_scores": I_TABLE_DIR / "transition_context_ablation_event_scores.csv.gz",
    "transition_context_ablation_selected_events": I_TABLE_DIR / "transition_context_ablation_selected_events.csv.gz",
    "transition_context_ablation_rejected_events": I_TABLE_DIR / "transition_context_ablation_rejected_events.csv.gz",
    "transition_previous_regime_context_cost_rejector_ablation_report": I_REPORT_DIR / "transition_previous_regime_context_cost_rejector_ablation_report.md",
    "transition_previous_regime_context_cost_rejector_ablation_contract": I_REPORT_DIR / "transition_previous_regime_context_cost_rejector_ablation_contract.md",
    "transition_previous_regime_context_cost_rejector_ablation_manifest": I_MANIFEST_DIR / "transition_previous_regime_context_cost_rejector_ablation_manifest.json",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment I transition previous-regime context cost rejector ablation."
    )
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (I_TABLE_DIR, I_REPORT_DIR, I_MANIFEST_DIR, I_LOCAL_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        frame.to_csv(path, index=False, compression="gzip")
    else:
        frame.to_csv(path, index=False)
    return path


def file_row_count(path: Path) -> int | float:
    if not path.exists() or not path.is_file():
        return np.nan
    if path.suffix == ".parquet":
        return np.nan
    opener = gzip.open if path.suffix == ".gz" else open
    mode = "rt" if path.suffix == ".gz" else "r"
    with opener(path, mode, encoding="utf-8", errors="ignore") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def dataframe_schema_fingerprint(frame: pd.DataFrame) -> str:
    return stable_hash([(str(col), str(dtype)) for col, dtype in frame.dtypes.items()])


def build_schema_fingerprints(frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    return {
        key: dataframe_schema_fingerprint(frame)
        for key, frame in frames.items()
        if isinstance(frame, pd.DataFrame)
    }


def record_loaded_input_metadata(input_frame: pd.DataFrame, loaded_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    out = input_frame.copy()
    for input_id, frame in loaded_frames.items():
        mask = out["input_id"].astype(str).eq(input_id)
        if not bool(mask.any()):
            continue
        out.loc[mask, "loaded_row_count"] = int(len(frame))
        out.loc[mask, "loaded_column_count"] = int(len(frame.columns))
        out.loc[mask, "loaded_schema_fingerprint"] = dataframe_schema_fingerprint(frame)
    return out


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return e_runner.bool_series(frame, column)


def safe_div(num: float | int, den: float | int) -> float:
    return e_runner.safe_div(num, den)


def relative_reduction(before: float, after: float) -> float:
    return e_runner.relative_reduction(before, after)


def input_audit() -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    paths: dict[str, Path] = {}
    for spec in INPUT_SPECS:
        exists = spec.path.exists()
        status = "present" if exists else ("missing_required" if spec.required else "missing_optional")
        if spec.required and not exists:
            failures.append(f"missing_input:{spec.input_id}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "status": status,
                "sha256": path_hash(spec.path),
                "row_count": file_row_count(spec.path),
            }
        )
        paths[spec.input_id] = spec.path
    return pd.DataFrame(rows), failures, paths


def validate_manifest_artifacts(
    manifest: dict[str, Any],
    artifact_keys: list[str],
    fallback_paths: dict[str, Path],
    upstream_name: str,
) -> tuple[pd.DataFrame, list[str]]:
    output_hashes = manifest.get("output_hashes", {}) or {}
    output_paths = manifest.get("output_paths", {}) or {}
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for key in artifact_keys:
        expected = str(output_hashes.get(key, ""))
        path = Path(str(output_paths.get(key, ""))) if output_paths.get(key) else fallback_paths[key]
        if not path.exists():
            path = fallback_paths[key]
        actual = path_hash(path)
        status = "pass" if expected and actual == expected else "hash_mismatch_or_missing"
        if status != "pass":
            failures.append(f"{upstream_name}_artifact_hash_mismatch:{key}")
        rows.append(
            {
                "upstream": upstream_name,
                "artifact_key": key,
                "path": str(path),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "hash_status": status,
            }
        )
    return pd.DataFrame(rows), failures


def build_upstream_binding_audit(
    g_manifest: dict[str, Any],
    h_manifest: dict[str, Any],
    d_manifest: dict[str, Any],
    e_manifest: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    decisions = {
        "G": (g_manifest.get("decision", ""), "transition_previous_regime_conditioning_diagnostic_only"),
        "H": (h_manifest.get("decision", ""), "risk_on_cost_rejector_diagnostic_only_or_no_candidate"),
        "D": (d_manifest.get("decision", ""), "post_replay_retention_source_source_caveated_complete"),
        "E": (e_manifest.get("decision", ""), "risk_on_cost_rejector_feature_source_caveated_supported"),
    }
    for name, (observed, expected) in decisions.items():
        status = "pass" if observed == expected else "decision_caveat"
        rows.append(
            {
                "binding_name": f"{name}_decision",
                "observed_value": observed,
                "required_or_expected_value": expected,
                "binding_status": status,
            }
        )
    selected_grid = str(g_manifest.get("selected_grid_rule_id", ""))
    if not selected_grid:
        failures.append("g_selected_grid_rule_id_missing")
    rows.append(
        {
            "binding_name": "g_selected_grid_rule_id",
            "observed_value": selected_grid,
            "required_or_expected_value": "non_empty",
            "binding_status": "pass" if selected_grid else "missing",
        }
    )
    g_fallback = {
        "transition_previous_regime_event_assignment": G_TABLE_DIR / "transition_previous_regime_event_assignment.csv.gz",
        "transition_previous_regime_segment_catalog": G_TABLE_DIR / "transition_previous_regime_segment_catalog.csv",
        "transition_previous_regime_universe_binding_audit": G_TABLE_DIR / "transition_previous_regime_universe_binding_audit.csv",
        "transition_previous_regime_leakage_audit": G_TABLE_DIR / "transition_previous_regime_leakage_audit.csv",
        "transition_previous_regime_label_join_audit": G_TABLE_DIR / "transition_previous_regime_label_join_audit.csv",
        "transition_previous_regime_segment_matrix": G_TABLE_DIR / "transition_previous_regime_segment_matrix.csv",
        "transition_previous_regime_cost_quality_matrix": G_TABLE_DIR / "transition_previous_regime_cost_quality_matrix.csv",
        "transition_previous_regime_recall_retention_matrix": G_TABLE_DIR / "transition_previous_regime_recall_retention_matrix.csv",
        "transition_previous_regime_e1_missed_capture": G_TABLE_DIR / "transition_previous_regime_e1_missed_capture.csv",
    }
    h_fallback = {
        "risk_on_hardening_feature_contract": H_TABLE_DIR / "risk_on_hardening_feature_contract.csv",
        "risk_on_hardening_feature_delta_from_e": H_TABLE_DIR / "risk_on_hardening_feature_delta_from_e.csv",
        "risk_on_hardening_asof_join_audit": H_TABLE_DIR / "risk_on_hardening_asof_join_audit.csv",
        "risk_on_hardening_model_registry": H_TABLE_DIR / "risk_on_hardening_model_registry.csv",
    }
    g_hash, g_failures = validate_manifest_artifacts(g_manifest, REQUIRED_G_ARTIFACT_KEYS, g_fallback, "G")
    h_hash, h_failures = validate_manifest_artifacts(h_manifest, REQUIRED_H_ARTIFACT_KEYS, h_fallback, "H")
    for _, row in pd.concat([g_hash, h_hash], ignore_index=True).iterrows():
        rows.append(
            {
                "binding_name": f"{row['upstream']}_artifact_hash:{row['artifact_key']}",
                "observed_value": row["actual_sha256"],
                "required_or_expected_value": row["expected_sha256"],
                "binding_status": row["hash_status"],
                "path": row["path"],
            }
        )
    failures.extend(g_failures)
    failures.extend(h_failures)
    return pd.DataFrame(rows), failures, {**g_fallback, **h_fallback}


def label_leakage_pass(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    failures: list[str] = []
    status_cols = [col for col in frame.columns if col.endswith("_status") or col.endswith("status")]
    failed = pd.Series(False, index=frame.index)
    for col in status_cols:
        failed |= frame[col].astype(str).str.contains("fail|blocked|leak", case=False, na=False)
    if bool(failed.any()):
        failures.append("d_label_leakage_audit_not_pass")
    return frame, failures


def derive_duration_bucket(days: pd.Series) -> pd.Series:
    value = pd.to_numeric(days, errors="coerce")
    out = pd.Series("missing", index=days.index, dtype="object")
    out.loc[value.between(1, 5, inclusive="both")] = "1_5"
    out.loc[value.between(6, 20, inclusive="both")] = "6_20"
    out.loc[value.between(21, 60, inclusive="both")] = "21_60"
    out.loc[value.ge(61)] = "61_plus"
    return out


def prepare_primary_events(
    assignments: pd.DataFrame,
    canonical: pd.DataFrame,
    labels: pd.DataFrame,
    membership: pd.DataFrame,
    segment_catalog: pd.DataFrame,
    selected_grid_rule_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    failures: list[str] = []
    if assignments["grid_rule_id"].astype(str).nunique() > 1:
        filtered = assignments.loc[assignments["grid_rule_id"].astype(str).eq(selected_grid_rule_id)].copy()
        if filtered.empty:
            failures.append("selected_grid_rule_id_not_present_in_assignment")
    else:
        filtered = assignments.loc[assignments["grid_rule_id"].astype(str).eq(selected_grid_rule_id)].copy()
    primary = filtered.loc[
        bool_series(filtered, "rule_event_included")
        & filtered["universe_binding_status"].astype(str).isin(PRIMARY_BINDING_STATUSES)
        & filtered["pit_transition_context"].astype(str).isin(PRIMARY_CONTEXTS)
    ].copy()
    if primary.empty:
        failures.append("primary_transition_universe_empty_after_g_binding")
    if filtered["grid_rule_id"].astype(str).nunique() > 1:
        failures.append("grid_rule_filter_failed_multiple_grid_ids_remain")
    primary["source_pool"] = SOURCE_POOL
    primary["event_id"] = primary["event_id"].astype(str)
    canonical = canonical.drop_duplicates("event_id", keep="last").copy()
    merge_cols = ["event_id"] + [col for col in canonical.columns if col not in primary.columns]
    events = primary.merge(canonical[merge_cols], on="event_id", how="left")
    if "primary_family_id" not in events.columns and "family_id" in events.columns:
        events["primary_family_id"] = events["family_id"]
    if "canonical_event_id" not in events.columns:
        events["canonical_event_id"] = events["event_id"]
    if "market_regime_bucket" not in events.columns:
        events["market_regime_bucket"] = events.get("published_market_regime_bucket", "")
    if "event_regime_bucket" not in events.columns:
        events["event_regime_bucket"] = TARGET_REGIME

    segment_small = segment_catalog[
        [
            col
            for col in [
                "transition_segment_id",
                "previous_non_transition_end_date",
                "days_since_previous_regime_end",
            ]
            if col in segment_catalog.columns
        ]
    ].drop_duplicates("transition_segment_id")
    events = events.merge(segment_small, on="transition_segment_id", how="left", suffixes=("", "_segment_catalog"))
    event_dates = pd.to_datetime(events["event_t0_date"], errors="coerce")
    prev_end = pd.to_datetime(events.get("previous_non_transition_end_date"), errors="coerce")
    events["days_since_previous_regime_end_asof_event"] = (event_dates - prev_end).dt.days
    fallback_days = pd.to_numeric(events.get("days_since_previous_regime_end"), errors="coerce")
    events["days_since_previous_regime_end_asof_event"] = events["days_since_previous_regime_end_asof_event"].fillna(
        fallback_days
    )
    events["previous_non_transition_duration_bucket"] = derive_duration_bucket(
        events["previous_non_transition_trading_day_n"]
    )

    label_cols = [
        "event_id",
        "label_scope",
        "failure_10_label",
        "failure_10_complete",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
        "event_big_winner_120d_label",
        "horizon_complete_120d",
    ]
    label_scope = "all_new_candidate_union"
    scoped_labels = labels.loc[labels["label_scope"].astype(str).eq(label_scope), label_cols].copy()
    duplicate_n = int(scoped_labels.duplicated(["event_id", "label_scope"]).sum())
    scoped_labels = scoped_labels.drop_duplicates(["event_id", "label_scope"], keep="last")
    events["label_scope"] = label_scope
    events = events.merge(scoped_labels, on=["event_id", "label_scope"], how="left")
    events["horizon_complete"] = bool_series(events, "failure_10_complete") & bool_series(
        events, "event_false_repair_20d_complete"
    )
    events["fast_fail_bad_10d"] = bool_series(events, "failure_10_label")
    events["false_repair_bad_20d"] = bool_series(events, "event_false_repair_20d_label")
    events["cost_bad_10_20"] = events["fast_fail_bad_10d"] | events["false_repair_bad_20d"]
    events["cost_label_status"] = np.where(events["horizon_complete"], "complete", "incomplete_or_censored")

    label_audit, label_failures = label_reconciliation_audit(events, membership, duplicate_n)
    failures.extend(label_failures)
    return events, label_audit, failures


def label_reconciliation_audit(
    events: pd.DataFrame,
    membership: pd.DataFrame,
    duplicate_label_join_n: int,
) -> tuple[pd.DataFrame, list[str]]:
    failures: list[str] = []
    event_labels = events[
        [
            "event_id",
            "failure_10_label",
            "failure_10_complete",
            "event_false_repair_20d_label",
            "event_false_repair_20d_complete",
            "horizon_complete",
        ]
    ].drop_duplicates("event_id")
    mem = membership.loc[membership["event_id"].astype(str).isin(set(event_labels["event_id"].astype(str)))].copy()
    compare_cols = [
        "failure_10_label",
        "failure_10_complete",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
    ]
    mismatch_n = 0
    compared_n = 0
    if not mem.empty:
        mem_small = mem[["event_id", *compare_cols]].drop_duplicates()
        merged = mem_small.merge(event_labels[["event_id", *compare_cols]], on="event_id", how="inner", suffixes=("_mem", "_label"))
        compared_n = int(len(merged))
        mismatch = pd.Series(False, index=merged.index)
        for col in compare_cols:
            left = bool_series(merged, f"{col}_mem")
            right = bool_series(merged, f"{col}_label")
            mismatch |= left.ne(right)
        mismatch_n = int(mismatch.sum())
    complete_n = int(events["horizon_complete"].sum())
    complete_rate = safe_div(complete_n, len(events))
    missing_label_n = int(events["failure_10_complete"].isna().sum())
    if mismatch_n:
        failures.append(f"membership_label_mismatch:{mismatch_n}")
    if missing_label_n:
        failures.append(f"missing_label_rows:{missing_label_n}")
    row = {
        "source_pool": SOURCE_POOL,
        "label_scope": "all_new_candidate_union",
        "event_n": int(len(events)),
        "label_joined_n": int(events["failure_10_complete"].notna().sum()),
        "duplicate_join_n": duplicate_label_join_n,
        "missing_label_n": missing_label_n,
        "cost_label_complete_n": complete_n,
        "cost_label_complete_rate": complete_rate,
        "membership_label_compared_n": compared_n,
        "membership_label_mismatch_n": mismatch_n,
        "label_join_status": "pass" if not mismatch_n and not missing_label_n else "fail_closed",
    }
    return pd.DataFrame([row]), failures


def build_training_universe_audit(events: pd.DataFrame) -> pd.DataFrame:
    cross_segments = (
        events.dropna(subset=["transition_segment_id"])
        .drop_duplicates(["transition_segment_id", "event_split"])
        .groupby("transition_segment_id")["event_split"]
        .nunique()
    )
    cross_set = set(cross_segments.loc[cross_segments.gt(1)].index.astype(str))
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_frame = events.loc[events["event_split"].astype(str).eq(split)].copy()
        complete = split_frame.loc[split_frame["horizon_complete"]].copy()
        seg_counts = complete["transition_segment_id"].dropna().astype(str).value_counts()
        rows.append(
            {
                "split": split,
                "event_n": int(len(split_frame)),
                "horizon_complete_event_n": int(len(complete)),
                "positive_n": int(complete["cost_bad_10_20"].sum()) if len(complete) else 0,
                "label_prevalence": float(complete["cost_bad_10_20"].mean()) if len(complete) else np.nan,
                "unique_transition_segment_n": int(complete["transition_segment_id"].nunique()) if len(complete) else 0,
                "effective_transition_segment_n": inverse_herfindahl(seg_counts),
                "cross_split_segment_n": int(len(set(complete["transition_segment_id"].dropna().astype(str)).intersection(cross_set))),
                "transition_from_risk_on_event_n": int(split_frame["pit_transition_context"].astype(str).eq("transition_from_risk_on").sum()),
                "transition_from_risk_off_event_n": int(split_frame["pit_transition_context"].astype(str).eq("transition_from_risk_off").sum()),
                "power_status": split_power_status(split, complete, seg_counts),
            }
        )
    return pd.DataFrame(rows)


def split_power_status(split: str, complete: pd.DataFrame, seg_counts: pd.Series) -> str:
    unique_seg = int(seg_counts.shape[0])
    effective_seg = inverse_herfindahl(seg_counts)
    positive_n = int(complete["cost_bad_10_20"].sum()) if len(complete) else 0
    if split == "train" and (len(complete) < 300 or positive_n < 50 or unique_seg < 20 or effective_seg < 8):
        return "low_power_train"
    if split == "robustness" and (len(complete) < 500 or positive_n < 100 or unique_seg < 10):
        return "low_power_robustness"
    return "pass"


def inverse_herfindahl(counts: pd.Series) -> float:
    counts = pd.to_numeric(counts, errors="coerce").dropna()
    counts = counts.loc[counts > 0]
    total = float(counts.sum())
    if total <= 0:
        return np.nan
    shares = counts / total
    denom = float(np.square(shares).sum())
    return float(1.0 / denom) if denom > 0 else np.nan


def build_feature_contract(
    events: pd.DataFrame,
    h_contract: pd.DataFrame,
    g_assignment_hash: str,
    panel_hash: str,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    h_allowed = h_contract.loc[h_contract["allowed_as_t0_feature"].astype(str).str.lower().eq("true")].copy()
    rows: list[dict[str, Any]] = []
    baseline_features: list[str] = []
    for _, hrow in h_allowed.iterrows():
        feature = str(hrow["feature_name"])
        if feature not in events.columns:
            rows.append(feature_contract_row(feature, "h_feature_contract", "", "missing_in_i_events", False, "missing_in_i_events"))
            continue
        forced_drop = feature in FORCED_DROP_FEATURES
        miss = split_missing_rates(events, feature)
        coverage_drop = miss["missing_rate_train"] > 0.05 or miss["missing_rate_robustness"] > 0.05
        allowed = not forced_drop and not coverage_drop
        reason = ""
        if forced_drop:
            reason = "forced_drop_regime_or_binding_proxy_or_i_constant"
        elif coverage_drop:
            reason = "missing_rate_above_5pct_dropped"
        if allowed:
            baseline_features.append(feature)
        rows.append(
            {
                "feature_name": feature,
                "source_artifact": hrow.get("source_artifact", "h_feature_contract"),
                "source_hash": hrow.get("source_hash", ""),
                "as_of_policy": hrow.get("as_of_policy", "event_t0_or_panel_asof"),
                "source_kind": hrow.get("source_kind", "baseline"),
                "feature_join_key": hrow.get("feature_join_key", ""),
                "feature_as_of_date_policy": hrow.get("feature_as_of_date_policy", ""),
                "max_feature_as_of_date_minus_event_t0_date": hrow.get("max_feature_as_of_date_minus_event_t0_date", np.nan),
                "uses_future_information": False,
                "allowed_as_t0_feature": allowed,
                "allowed_for_model": allowed,
                "model_role": "baseline_model_feature" if allowed else "blocked",
                **miss,
                "blocked_reason": reason,
            }
        )
    for feature in CONTEXT_MODEL_FEATURES:
        miss = split_missing_rates(events, feature)
        coverage_drop = miss["missing_rate_train"] > 0.05 or miss["missing_rate_robustness"] > 0.05
        allowed = feature in events.columns and not coverage_drop
        rows.append(
            {
                "feature_name": feature,
                "source_artifact": "transition_previous_regime_event_assignment_or_segment_catalog",
                "source_hash": g_assignment_hash,
                "as_of_policy": "event_t0_visible_previous_regime_context",
                "source_kind": "previous_regime_context",
                "feature_join_key": "event_id_or_transition_segment_id",
                "feature_as_of_date_policy": "feature_available_date_lte_event_t0_date",
                "max_feature_as_of_date_minus_event_t0_date": 0,
                "uses_future_information": False,
                "allowed_as_t0_feature": allowed,
                "allowed_for_model": allowed,
                "model_role": "context_model_feature" if allowed else "blocked",
                **miss,
                "blocked_reason": "" if allowed else "missing_or_context_coverage_below_95pct",
            }
        )
    for feature in CONTEXT_AUDIT_ONLY_FEATURES:
        rows.append(
            {
                "feature_name": feature,
                "source_artifact": "transition_previous_regime_event_assignment",
                "source_hash": g_assignment_hash,
                "as_of_policy": "event_t0_visible_previous_regime_context",
                "source_kind": "previous_regime_context",
                "feature_join_key": "event_id",
                "feature_as_of_date_policy": "feature_available_date_lte_event_t0_date",
                "max_feature_as_of_date_minus_event_t0_date": 0,
                "uses_future_information": False,
                "allowed_as_t0_feature": False,
                "allowed_for_model": False,
                "model_role": "audit_only_collinear_with_pit_transition_context",
                **split_missing_rates(events, feature),
                "blocked_reason": "collinear_with_pit_transition_context_after_unknown_filter",
            }
        )
    for feature in sorted(FORBIDDEN_FUTURE_FEATURES):
        if feature in events.columns:
            rows.append(
                {
                    "feature_name": feature,
                    "source_artifact": "transition_previous_regime_event_assignment",
                    "source_hash": g_assignment_hash,
                    "as_of_policy": "future_or_expost_forbidden",
                    "source_kind": "forbidden_future_outcome_or_segment_complete_field",
                    "feature_join_key": "event_id",
                    "feature_as_of_date_policy": "future_or_expost",
                    "max_feature_as_of_date_minus_event_t0_date": np.nan,
                    "uses_future_information": True,
                    "allowed_as_t0_feature": False,
                    "allowed_for_model": False,
                    "model_role": "forbidden_readout_only",
                    **split_missing_rates(events, feature),
                    "blocked_reason": "forbidden_future_or_complete_segment_field",
                }
            )
    context_features = [f for f in CONTEXT_MODEL_FEATURES if f in events.columns]
    feature_sets = {
        "baseline": baseline_features,
        "context": context_features,
        "no_context": baseline_features,
        "prev_context": baseline_features + context_features,
        "context_only": context_features,
    }
    return pd.DataFrame(rows), feature_sets


def feature_contract_row(
    feature: str,
    source_artifact: str,
    source_hash: str,
    asof_policy: str,
    allowed: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "feature_name": feature,
        "source_artifact": source_artifact,
        "source_hash": source_hash,
        "as_of_policy": asof_policy,
        "source_kind": "missing",
        "feature_join_key": "",
        "feature_as_of_date_policy": asof_policy,
        "max_feature_as_of_date_minus_event_t0_date": np.nan,
        "uses_future_information": False,
        "allowed_as_t0_feature": allowed,
        "allowed_for_model": allowed,
        "model_role": "blocked",
        "missing_rate_train": np.nan,
        "missing_rate_validation": np.nan,
        "missing_rate_robustness": np.nan,
        "blocked_reason": reason,
    }


def split_missing_rates(events: pd.DataFrame, feature: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for split in SPLITS:
        frame = events.loc[events["event_split"].astype(str).eq(split)]
        if feature not in frame.columns or frame.empty:
            out[f"missing_rate_{split}"] = np.nan
        else:
            out[f"missing_rate_{split}"] = float(frame[feature].isna().mean())
    return out


def build_leakage_audit(feature_contract: pd.DataFrame, feature_sets: dict[str, list[str]]) -> tuple[pd.DataFrame, list[str]]:
    model_features = set(feature_sets["no_context"]) | set(feature_sets["prev_context"]) | set(feature_sets["context_only"])
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for _, row in feature_contract.iterrows():
        feature = str(row["feature_name"])
        in_model = feature in model_features
        uses_future = bool(row.get("uses_future_information", False))
        blocked = ""
        if in_model and uses_future:
            blocked = "model_feature_uses_future_information"
            failures.append(f"future_feature_used:{feature}")
        if in_model and feature in FORBIDDEN_FUTURE_FEATURES:
            blocked = "forbidden_future_outcome_or_complete_segment_field"
            failures.append(f"forbidden_future_feature_used:{feature}")
        rows.append(
            {
                "feature_name": feature,
                "source_artifact": row.get("source_artifact", ""),
                "feature_as_of_policy": row.get("feature_as_of_date_policy", row.get("as_of_policy", "")),
                "max_feature_as_of_date_minus_event_t0_date": row.get("max_feature_as_of_date_minus_event_t0_date", np.nan),
                "uses_future_information": uses_future,
                "allowed_for_model": bool(row.get("allowed_for_model", False)),
                "used_by_model": in_model,
                "blocked_reason": blocked or row.get("blocked_reason", ""),
            }
        )
    return pd.DataFrame(rows), failures


def feature_missing_coverage(events: pd.DataFrame, feature_cols: list[str], mask: pd.Series) -> float:
    if not feature_cols or not bool(mask.any()):
        return np.nan
    return float(1.0 - events.loc[mask, feature_cols].isna().mean().mean())


def split_design_columns(events: pd.DataFrame, feature_cols: list[str]) -> tuple[list[str], list[str]]:
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    for col in feature_cols:
        if col not in events.columns:
            continue
        if col in CONTEXT_CATEGORICAL_FEATURES:
            categorical_cols.append(col)
        elif pd.api.types.is_numeric_dtype(events[col]):
            numeric_cols.append(col)
        else:
            numeric_cols.append(col) if pd.to_numeric(events[col], errors="coerce").notna().mean() > 0.95 else categorical_cols.append(col)
    return numeric_cols, categorical_cols


def build_design_matrix(
    events: pd.DataFrame,
    feature_cols: list[str],
    train_mask: pd.Series,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    numeric_cols, categorical_cols = split_design_columns(events, feature_cols)
    numeric_raw = (
        events[numeric_cols].apply(pd.to_numeric, errors="coerce")
        if numeric_cols
        else pd.DataFrame(index=events.index)
    )
    numeric, numeric_meta = e_runner.preprocess_numeric_features(numeric_raw, train_mask)
    cat, cat_meta = e_runner.build_categorical_matrix(events, categorical_cols, train_mask)
    matrix = pd.concat([numeric, cat], axis=1)
    columns = list(matrix.columns)
    matrix = matrix.reindex(columns=columns, fill_value=0.0).astype(float)
    preprocessing = {
        "policy": e_runner.FEATURE_PREPROCESSING_POLICY,
        "numeric": numeric_meta,
        "categorical": cat_meta,
        "feature_columns": feature_cols,
        "raw_numeric_columns": numeric_cols,
        "raw_categorical_columns": categorical_cols,
    }
    return matrix, columns, preprocessing


def fit_model_arm(
    events: pd.DataFrame,
    model_id: str,
    feature_cols: list[str],
    train_universe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frame = events.reset_index(drop=True).copy()
    train_mask = frame["event_split"].astype(str).eq("train") & frame["horizon_complete"]
    y_train = frame.loc[train_mask, TARGET_LABEL].astype(int)
    matrix, design_columns, preprocessing = build_design_matrix(frame, feature_cols, train_mask)
    train_row = train_universe.loc[train_universe["split"].astype(str).eq("train")].iloc[0].to_dict()
    status = "trained"
    scores = np.full(len(frame), np.nan)
    if len(y_train) < 300 or int(y_train.sum()) < 50 or y_train.nunique() < 2:
        status = "blocked_low_power_event_label"
    else:
        if train_row.get("power_status") != "pass":
            status = "trained_segment_low_power_exploratory"
        model = LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
        model.fit(matrix.loc[train_mask], y_train)
        scores = model.predict_proba(matrix)[:, 1]
    score = frame[
        [
            "source_pool",
            "event_id",
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_t0_pos",
            "event_split",
            "transition_segment_id",
            "pit_transition_context",
            "previous_non_transition_regime",
            "transition_outcome_label",
            "transition_outcome_direction",
            "horizon_complete",
            "fast_fail_bad_10d",
            "false_repair_bad_20d",
            "cost_bad_10_20",
        ]
    ].copy()
    score["model_id"] = model_id
    score["target_label"] = TARGET_LABEL
    score["cost_bad_score"] = scores
    registry = pd.DataFrame(
        [
            {
                "model_id": model_id,
                "source_pool": SOURCE_POOL,
                "target_label": TARGET_LABEL,
                "model_type": MODEL_TYPE,
                "model_status": status,
                "train_sample_n": int(train_mask.sum()),
                "train_positive_n": int(y_train.sum()) if len(y_train) else 0,
                "train_unique_segment_n": int(train_row.get("unique_transition_segment_n", 0)),
                "train_effective_segment_n": train_row.get("effective_transition_segment_n", np.nan),
                "feature_count": len(feature_cols),
                "design_feature_count": len(design_columns),
                "feature_columns_hash": stable_hash(feature_cols),
                "feature_preprocessing_policy": e_runner.FEATURE_PREPROCESSING_POLICY,
                "feature_preprocessing_hash": stable_hash(preprocessing),
                "context_collinearity_policy": "previous_non_transition_regime=audit_only",
            }
        ]
    )
    oos_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_mask = frame["event_split"].astype(str).eq(split) & frame["horizon_complete"]
        row = separability_row(
            model_id,
            frame.loc[split_mask, TARGET_LABEL].astype(int),
            pd.Series(scores, index=frame.index).loc[split_mask],
            split,
            feature_missing_coverage(frame, feature_cols, split_mask),
        )
        row["train_unique_segment_n"] = train_row.get("unique_transition_segment_n", np.nan)
        row["train_effective_segment_n"] = train_row.get("effective_transition_segment_n", np.nan)
        oos_rows.append(row)
    return score, registry, pd.DataFrame(oos_rows), preprocessing


def separability_row(
    model_id: str,
    y: pd.Series,
    score: pd.Series,
    split: str,
    feature_coverage: float = np.nan,
) -> dict[str, Any]:
    y = y.astype(int)
    score = pd.to_numeric(score, errors="coerce")
    valid = score.notna()
    y = y.loc[valid]
    score = score.loc[valid]
    prevalence = float(y.mean()) if len(y) else np.nan
    roc = np.nan
    pr = np.nan
    brier = np.nan
    top_lift = np.nan
    bottom_rate = np.nan
    monotonicity = "insufficient_bins"
    if len(y) and y.nunique() == 2:
        roc = float(roc_auc_score(y, score))
        pr = float(average_precision_score(y, score))
        brier = float(brier_score_loss(y, score.clip(0, 1)))
    if len(y) >= 10 and pd.notna(prevalence) and prevalence > 0:
        top_n = max(int(np.ceil(len(y) * 0.10)), 1)
        ordered = pd.DataFrame({"y": y, "score": score}).sort_values("score", ascending=False)
        top_lift = float(ordered.head(top_n)["y"].mean() / prevalence)
        bottom_rate = float(ordered.tail(top_n)["y"].mean())
        monotonicity = score_monotonicity_by_decile(y, score)
    return {
        "model_id": model_id,
        "source_pool": SOURCE_POOL,
        "target_label": TARGET_LABEL,
        "split": split,
        "sample_n": int(len(y)),
        "positive_n": int(y.sum()) if len(y) else 0,
        "label_prevalence": prevalence,
        "roc_auc": roc,
        "pr_auc": pr,
        "top_decile_lift": top_lift,
        "bottom_decile_cost_bad_rate": bottom_rate,
        "brier_score": brier,
        "score_monotonicity_by_decile": monotonicity,
        "feature_missing_coverage": feature_coverage,
        "oos_separability_status": "pass" if pd.notna(roc) and roc >= 0.5 else "diagnostic_or_reversed",
    }


def score_monotonicity_by_decile(y: pd.Series, score: pd.Series) -> str:
    frame = pd.DataFrame({"y": y.astype(float), "score": score.astype(float)}).dropna()
    if len(frame) < 20 or frame["score"].nunique() < 3:
        return "insufficient_bins"
    try:
        frame["decile"] = pd.qcut(frame["score"], q=min(10, frame["score"].nunique()), labels=False, duplicates="drop")
    except ValueError:
        return "insufficient_bins"
    means = frame.groupby("decile")["y"].mean().dropna()
    if len(means) < 3:
        return "insufficient_bins"
    corr = means.reset_index()["decile"].corr(means.reset_index()["y"], method="spearman")
    if pd.isna(corr):
        return "insufficient_bins"
    return "monotone_increasing" if corr >= 0.60 else "weak_or_non_monotone"


def run_segment_cv(
    events: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, Any]] = []
    train_events = events.loc[events["event_split"].astype(str).eq("train") & events["horizon_complete"]].copy()
    segment_order = (
        train_events[["transition_segment_id", "segment_start_date"]]
        .dropna(subset=["transition_segment_id"])
        .drop_duplicates("transition_segment_id")
        .sort_values(["segment_start_date", "transition_segment_id"])
    )
    segments = segment_order["transition_segment_id"].astype(str).tolist()
    grouped_folds = make_grouped_folds(segments, 5)
    purged_folds = make_purged_folds(segments, 5)
    for scheme, folds in (("segment_grouped_cv", grouped_folds), ("chronological_purged_segment_cv", purged_folds)):
        if not folds:
            for model_id in MODEL_ARMS:
                fold_rows.append(low_power_fold_row(model_id, scheme, "all", "insufficient_train_segments"))
            continue
        for fold_id, holdout_segments, purged_segments in folds:
            holdout_set = set(holdout_segments)
            purge_set = set(purged_segments)
            train_set = set(segments).difference(holdout_set).difference(purge_set)
            for model_id, feature_cols in arm_feature_map(feature_sets).items():
                fold_rows.append(fit_fold(events, model_id, feature_cols, scheme, fold_id, train_set, holdout_set, purge_set))
    folds = pd.DataFrame(fold_rows)
    uplift = build_cv_uplift(folds)
    stability = build_cv_stability(folds, uplift)
    return stability, uplift


def make_grouped_folds(segments: list[str], max_splits: int) -> list[tuple[str, list[str], list[str]]]:
    if len(segments) < 5:
        return []
    n_splits = min(max_splits, len(segments))
    folds = [[] for _ in range(n_splits)]
    for idx, seg in enumerate(segments):
        folds[idx % n_splits].append(seg)
    return [(f"fold_{i + 1}", fold, []) for i, fold in enumerate(folds)]


def make_purged_folds(segments: list[str], max_splits: int) -> list[tuple[str, list[str], list[str]]]:
    if len(segments) < 5:
        return []
    n_splits = min(max_splits, len(segments))
    blocks = np.array_split(np.arange(len(segments)), n_splits)
    folds: list[tuple[str, list[str], list[str]]] = []
    for idx, block in enumerate(blocks):
        holdout_idx = [int(x) for x in block.tolist()]
        purge_idx = set()
        if holdout_idx:
            if min(holdout_idx) - 1 >= 0:
                purge_idx.add(min(holdout_idx) - 1)
            if max(holdout_idx) + 1 < len(segments):
                purge_idx.add(max(holdout_idx) + 1)
        folds.append(
            (
                f"fold_{idx + 1}",
                [segments[i] for i in holdout_idx],
                [segments[i] for i in sorted(purge_idx)],
            )
        )
    return folds


def arm_feature_map(feature_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "transition_cost_rejector_no_context": feature_sets["no_context"],
        "transition_cost_rejector_prev_context": feature_sets["prev_context"],
        "transition_cost_rejector_context_only": feature_sets["context_only"],
    }


def low_power_fold_row(model_id: str, scheme: str, fold_id: str, reason: str) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "cv_scheme": scheme,
        "fold_id": fold_id,
        "train_segment_n": 0,
        "holdout_segment_n": 0,
        "purged_segment_n": 0,
        "train_event_n": 0,
        "holdout_event_n": 0,
        "holdout_positive_n": 0,
        "roc_auc": np.nan,
        "pr_auc": np.nan,
        "top_decile_lift": np.nan,
        "fold_status": f"fold_low_power:{reason}",
    }


def fit_fold(
    events: pd.DataFrame,
    model_id: str,
    feature_cols: list[str],
    scheme: str,
    fold_id: str,
    train_segments: set[str],
    holdout_segments: set[str],
    purged_segments: set[str],
) -> dict[str, Any]:
    frame = events.loc[events["event_split"].astype(str).eq("train") & events["horizon_complete"]].reset_index(drop=True)
    seg = frame["transition_segment_id"].astype(str)
    train_mask = seg.isin(train_segments)
    holdout_mask = seg.isin(holdout_segments)
    y_train = frame.loc[train_mask, TARGET_LABEL].astype(int)
    y_holdout = frame.loc[holdout_mask, TARGET_LABEL].astype(int)
    status = "valid"
    if int(train_mask.sum()) == 0 or int(holdout_mask.sum()) == 0:
        status = "fold_low_power:empty_train_or_holdout"
    elif int(y_train.sum()) < 30 or int(y_holdout.sum()) < 10 or y_train.nunique() < 2 or y_holdout.nunique() < 2:
        status = "fold_low_power:label_count_or_variation"
    if status != "valid":
        return {
            "model_id": model_id,
            "cv_scheme": scheme,
            "fold_id": fold_id,
            "train_segment_n": int(len(train_segments)),
            "holdout_segment_n": int(len(holdout_segments)),
            "purged_segment_n": int(len(purged_segments)),
            "train_event_n": int(train_mask.sum()),
            "holdout_event_n": int(holdout_mask.sum()),
            "holdout_positive_n": int(y_holdout.sum()) if len(y_holdout) else 0,
            "roc_auc": np.nan,
            "pr_auc": np.nan,
            "top_decile_lift": np.nan,
            "fold_status": status,
        }
    matrix, _, _ = build_design_matrix(frame, feature_cols, train_mask)
    model = LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
    model.fit(matrix.loc[train_mask], y_train)
    score = pd.Series(model.predict_proba(matrix.loc[holdout_mask])[:, 1], index=y_holdout.index)
    metrics = separability_row(model_id, y_holdout, score, "train_cv")
    return {
        "model_id": model_id,
        "cv_scheme": scheme,
        "fold_id": fold_id,
        "train_segment_n": int(len(train_segments)),
        "holdout_segment_n": int(len(holdout_segments)),
        "purged_segment_n": int(len(purged_segments)),
        "train_event_n": int(train_mask.sum()),
        "holdout_event_n": int(holdout_mask.sum()),
        "holdout_positive_n": int(y_holdout.sum()),
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "top_decile_lift": metrics["top_decile_lift"],
        "fold_status": "valid",
    }


def build_cv_uplift(folds: pd.DataFrame) -> pd.DataFrame:
    if folds.empty:
        return pd.DataFrame()
    base = folds.loc[folds["model_id"].eq("transition_cost_rejector_no_context")].copy()
    prev = folds.loc[folds["model_id"].eq("transition_cost_rejector_prev_context")].copy()
    merged = prev.merge(base, on=["cv_scheme", "fold_id"], suffixes=("_prev_context", "_no_context"))
    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        valid = str(row.get("fold_status_prev_context")) == "valid" and str(row.get("fold_status_no_context")) == "valid"
        rows.append(
            {
                "cv_scheme": row["cv_scheme"],
                "fold_id": row["fold_id"],
                "roc_auc_prev_context": row.get("roc_auc_prev_context", np.nan),
                "roc_auc_no_context": row.get("roc_auc_no_context", np.nan),
                "roc_auc_uplift": row.get("roc_auc_prev_context", np.nan) - row.get("roc_auc_no_context", np.nan) if valid else np.nan,
                "pr_auc_prev_context": row.get("pr_auc_prev_context", np.nan),
                "pr_auc_no_context": row.get("pr_auc_no_context", np.nan),
                "pr_auc_uplift": row.get("pr_auc_prev_context", np.nan) - row.get("pr_auc_no_context", np.nan) if valid else np.nan,
                "top_decile_lift_prev_context": row.get("top_decile_lift_prev_context", np.nan),
                "top_decile_lift_no_context": row.get("top_decile_lift_no_context", np.nan),
                "top_decile_lift_uplift": row.get("top_decile_lift_prev_context", np.nan) - row.get("top_decile_lift_no_context", np.nan) if valid else np.nan,
                "fold_status": "valid" if valid else "fold_low_power_or_invalid",
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    summaries = []
    for scheme, group in out.groupby("cv_scheme", dropna=False):
        valid = group.loc[group["fold_status"].eq("valid")]
        median_roc = pd.to_numeric(valid["roc_auc_uplift"], errors="coerce").median()
        median_pr = pd.to_numeric(valid["pr_auc_uplift"], errors="coerce").median()
        median_lift = pd.to_numeric(valid["top_decile_lift_uplift"], errors="coerce").median()
        positive_share = safe_div(
            int(
                (
                    pd.to_numeric(valid["roc_auc_uplift"], errors="coerce").fillna(-np.inf).ge(0)
                    | pd.to_numeric(valid["pr_auc_uplift"], errors="coerce").fillna(-np.inf).ge(0)
                ).sum()
            ),
            len(valid),
        )
        summaries.append(
            {
                "cv_scheme": scheme,
                "fold_id": "summary",
                "roc_auc_uplift": median_roc,
                "pr_auc_uplift": median_pr,
                "top_decile_lift_uplift": median_lift,
                "median_roc_auc_uplift": median_roc,
                "median_pr_auc_uplift": median_pr,
                "median_top_decile_lift_uplift": median_lift,
                "positive_uplift_fold_share": positive_share,
                "valid_fold_n": int(len(valid)),
                "fold_status": "summary",
                "stability_status": cv_uplift_summary_status(valid, median_roc, median_pr, positive_share),
            }
        )
    return pd.concat([out, pd.DataFrame(summaries)], ignore_index=True, sort=False)


def cv_uplift_summary_status(valid: pd.DataFrame, median_roc: float, median_pr: float, positive_share: float) -> str:
    if len(valid) < 3:
        return "low_power_valid_fold_n_lt_3"
    nonnegative = (pd.notna(median_roc) and median_roc >= 0) or (pd.notna(median_pr) and median_pr >= 0)
    if nonnegative and pd.notna(positive_share) and positive_share >= 0.60:
        return "stable_nonnegative_context_uplift"
    return "unstable_or_negative_context_uplift"


def build_cv_stability(folds: pd.DataFrame, uplift: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if folds.empty:
        return pd.DataFrame()
    summary_uplift = uplift.loc[uplift["fold_id"].astype(str).eq("summary")] if not uplift.empty else pd.DataFrame()
    for (model_id, scheme), group in folds.groupby(["model_id", "cv_scheme"], dropna=False):
        valid = group.loc[group["fold_status"].astype(str).eq("valid")]
        up = summary_uplift.loc[summary_uplift["cv_scheme"].astype(str).eq(str(scheme))]
        rows.append(
            {
                "model_id": model_id,
                "cv_scheme": scheme,
                "fold_n": int(len(group)),
                "valid_fold_n": int(len(valid)),
                "median_roc_auc": pd.to_numeric(valid["roc_auc"], errors="coerce").median(),
                "median_pr_auc": pd.to_numeric(valid["pr_auc"], errors="coerce").median(),
                "median_top_decile_lift": pd.to_numeric(valid["top_decile_lift"], errors="coerce").median(),
                "median_roc_auc_uplift_vs_no_context": float(up.iloc[0]["roc_auc_uplift"]) if not up.empty and model_id == "transition_cost_rejector_prev_context" else np.nan,
                "median_pr_auc_uplift_vs_no_context": float(up.iloc[0]["pr_auc_uplift"]) if not up.empty and model_id == "transition_cost_rejector_prev_context" else np.nan,
                "positive_uplift_fold_share": float(up.iloc[0]["positive_uplift_fold_share"]) if not up.empty and model_id == "transition_cost_rejector_prev_context" else np.nan,
                "fold_low_power_n": int(group["fold_status"].astype(str).ne("valid").sum()),
                "stability_status": stability_status(model_id, scheme, valid, up),
            }
        )
    return pd.DataFrame(rows)


def stability_status(model_id: str, scheme: str, valid: pd.DataFrame, uplift_summary: pd.DataFrame) -> str:
    if len(valid) < 3:
        return "low_power_valid_fold_n_lt_3"
    if model_id != "transition_cost_rejector_prev_context":
        return "diagnostic"
    if uplift_summary.empty:
        return "uplift_not_evaluable"
    roc = float(uplift_summary.iloc[0].get("roc_auc_uplift", np.nan))
    pr = float(uplift_summary.iloc[0].get("pr_auc_uplift", np.nan))
    share = float(uplift_summary.iloc[0].get("positive_uplift_fold_share", np.nan))
    if ((pd.notna(roc) and roc >= 0) or (pd.notna(pr) and pr >= 0)) and pd.notna(share) and share >= 0.60:
        return "stable_nonnegative_context_uplift"
    return "unstable_or_negative_context_uplift"


def build_threshold_frontier(
    events: pd.DataFrame,
    scores: pd.DataFrame,
    membership: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    for model_id in MODEL_ARMS:
        score_group = scores.loc[scores["model_id"].astype(str).eq(model_id)].copy()
        train_scores = score_group.loc[
            score_group["event_split"].astype(str).eq("train")
            & score_group["horizon_complete"]
            & score_group["cost_bad_score"].notna(),
            "cost_bad_score",
        ]
        if train_scores.empty:
            selected_rows.append(no_threshold_row(model_id, "no_train_scores"))
            continue
        for keep_fraction in KEEP_FRACTIONS:
            threshold = float(train_scores.quantile(keep_fraction))
            selected_ids = set(score_group.loc[score_group["cost_bad_score"].le(threshold), "event_id"].astype(str))
            rows.append(threshold_metrics(events, membership, model_id, keep_fraction, threshold, selected_ids))
        arm_rows = [row for row in rows if row["model_id"] == model_id]
        selected, reason = select_threshold(pd.DataFrame(arm_rows))
        selected_rows.append(selected if selected else no_threshold_row(model_id, reason))
    return pd.DataFrame(rows), pd.DataFrame(selected_rows)


def threshold_id_for(model_id: str, keep_fraction: float) -> str:
    return f"{model_id}__keep_{int(round(keep_fraction * 1000)):04d}"


def threshold_metrics(
    events: pd.DataFrame,
    membership: pd.DataFrame,
    model_id: str,
    keep_fraction: float,
    threshold: float,
    selected_ids: set[str],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_pool": SOURCE_POOL,
        "model_id": model_id,
        "threshold_id": threshold_id_for(model_id, keep_fraction),
        "threshold_value": threshold,
        "keep_fraction": float(keep_fraction),
        "threshold_selection_policy": "train_constrained_lowest_keep_fraction_then_cost_reduction",
        "selected_model_threshold_flag": False,
    }
    for split in SPLITS:
        split_events = events.loc[events["event_split"].astype(str).eq(split)]
        selected = split_events.loc[split_events["event_id"].astype(str).isin(selected_ids)]
        before = e_runner.cost_rates_for_events(split_events)
        after = e_runner.cost_rates_for_events(selected)
        retention = retention_metrics(events, membership, split, selected_ids)
        row.update(
            {
                f"before_{split}_horizon_complete_event_n": before["horizon_complete_event_n"],
                f"after_{split}_horizon_complete_event_n": after["horizon_complete_event_n"],
                f"{split}_reject_rate": 1 - safe_div(len(selected), len(split_events)),
                f"{split}_fast_fail_rate_before": before["fast_fail_bad_10d_rate"],
                f"{split}_fast_fail_rate_after": after["fast_fail_bad_10d_rate"],
                f"{split}_false_repair_rate_before": before["false_repair_bad_20d_rate"],
                f"{split}_false_repair_rate_after": after["false_repair_bad_20d_rate"],
                f"{split}_cost_bad_rate_before": before["cost_bad_10_20_rate"],
                f"{split}_cost_bad_rate_after": after["cost_bad_10_20_rate"],
                f"{split}_cost_reduction_relative": relative_reduction(
                    before["cost_bad_10_20_rate"], after["cost_bad_10_20_rate"]
                ),
                f"{split}_any_recall_retention": retention["post_filter_any_recall_retention"],
                f"{split}_bridge_recall_retention": retention["post_filter_bridge_recall_retention"],
                f"{split}_e1_missed_capture_retention": retention["post_filter_e1_missed_capture_retention"],
                f"{split}_post_filter_e1_missed_captured_episode_n": retention[
                    "post_filter_e1_missed_captured_episode_n"
                ],
            }
        )
    return row


def select_threshold(frontier: pd.DataFrame) -> tuple[dict[str, Any], str]:
    if frontier.empty:
        return {}, "no_threshold_frontier"
    eligible = frontier.loc[
        frontier["train_cost_reduction_relative"].ge(0.10)
        & frontier["train_any_recall_retention"].ge(0.80)
        & frontier["train_e1_missed_capture_retention"].ge(0.70)
        & frontier["train_fast_fail_rate_after"].le(frontier["train_fast_fail_rate_before"])
        & frontier["train_false_repair_rate_after"].le(frontier["train_false_repair_rate_before"])
        & frontier["after_train_horizon_complete_event_n"].gt(0)
    ].copy()
    if eligible.empty:
        return {}, "no_train_diagnostic_threshold"
    selected = eligible.sort_values(["keep_fraction", "train_cost_reduction_relative"], ascending=[True, False]).iloc[
        0
    ].to_dict()
    selected["selected_keep_fraction"] = selected.get("keep_fraction", np.nan)
    selected["selection_status"] = "train_selected"
    selected["failure_reason"] = ""
    selected["selected_model_threshold_flag"] = True
    return selected, ""


def no_threshold_row(model_id: str, reason: str) -> dict[str, Any]:
    return {
        "source_pool": SOURCE_POOL,
        "model_id": model_id,
        "threshold_id": "",
        "selected_keep_fraction": np.nan,
        "threshold_selection_policy": "train_constrained_lowest_keep_fraction_then_cost_reduction",
        "selection_status": "no_train_diagnostic_threshold",
        "failure_reason": reason,
    }


def membership_policy_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(False, index=frame.index)
    horizon = bool_series(frame, "failure_10_complete") & bool_series(frame, "event_false_repair_20d_complete")
    executable = bool_series(frame, "event_executable_flag") if "event_executable_flag" in frame.columns else pd.Series(True, index=frame.index)
    return horizon & executable


def event_reference_sets(frame: pd.DataFrame) -> tuple[set[str], set[str]]:
    event_ids = set(frame["event_id"].dropna().astype(str)) if "event_id" in frame.columns else set()
    if "canonical_event_id" in frame.columns:
        canonical_ids = set(frame["canonical_event_id"].dropna().astype(str))
    else:
        canonical_ids = set()
    return event_ids, canonical_ids


def membership_match_mask(membership: pd.DataFrame, event_ids: set[str], canonical_ids: set[str]) -> pd.Series:
    mask = pd.Series(False, index=membership.index)
    if event_ids and "event_id" in membership.columns:
        mask |= membership["event_id"].astype(str).isin(event_ids)
    if canonical_ids and "canonical_event_id" in membership.columns:
        mask |= membership["canonical_event_id"].astype(str).isin(canonical_ids)
    return mask


def primary_event_frame(events: pd.DataFrame, split: str, context: str = "all_primary_contexts") -> pd.DataFrame:
    base_events = events.loc[events["event_split"].astype(str).eq(split)].copy()
    if context != "all_primary_contexts":
        base_events = base_events.loc[base_events["pit_transition_context"].astype(str).eq(context)].copy()
    return base_events


def primary_membership(events: pd.DataFrame, membership: pd.DataFrame, split: str, context: str = "all_primary_contexts") -> pd.DataFrame:
    base_events = primary_event_frame(events, split, context)
    event_ids, canonical_ids = event_reference_sets(base_events)
    mem = membership.loc[
        membership_match_mask(membership, event_ids, canonical_ids)
        & membership["window"].astype(str).eq(HEADLINE_WINDOW)
        & membership["event_split"].astype(str).eq(split)
        & membership["episode_split"].astype(str).eq(split)
    ].copy()
    return mem.loc[membership_policy_mask(mem)].copy()


def retention_metrics(
    events: pd.DataFrame,
    membership: pd.DataFrame,
    split: str,
    selected_ids: set[str],
    context: str = "all_primary_contexts",
) -> dict[str, Any]:
    mem = primary_membership(events, membership, split, context)
    selected_events = primary_event_frame(events, split, context).loc[
        lambda frame: frame["event_id"].astype(str).isin(selected_ids)
    ].copy()
    selected_event_ids, selected_canonical_ids = event_reference_sets(selected_events)
    selected_mem = mem.loc[membership_match_mask(mem, selected_event_ids, selected_canonical_ids)].copy()
    pre_episodes = set(mem["target_episode_id"].dropna().astype(str))
    selected_episodes = set(selected_mem["target_episode_id"].dropna().astype(str))
    pre_bridge = set(
        mem.loc[
            bool_series(mem, "bridge_positive_denominator_included")
            & bool_series(mem, "event_big_winner_120d_label"),
            "target_episode_id",
        ].dropna().astype(str)
    )
    selected_bridge = set(
        selected_mem.loc[
            bool_series(selected_mem, "bridge_positive_denominator_included")
            & bool_series(selected_mem, "event_big_winner_120d_label"),
            "target_episode_id",
        ].dropna().astype(str)
    )
    e1 = membership.loc[
        membership["source_id"].astype(str).eq("07_E1_only")
        & membership["window"].astype(str).eq(HEADLINE_WINDOW)
        & membership["event_split"].astype(str).eq(split)
        & membership["episode_split"].astype(str).eq(split)
    ].copy()
    e1 = e1.loc[membership_policy_mask(e1)]
    e1_episodes = set(e1["target_episode_id"].dropna().astype(str))
    e1_missed = pre_episodes.difference(e1_episodes)
    selected_e1_missed = selected_episodes.intersection(e1_missed)
    return {
        "target_episode_denominator_n": int(len(pre_episodes)),
        "pre_filter_captured_episode_n": int(len(pre_episodes)),
        "post_filter_captured_episode_n": int(len(selected_episodes)),
        "post_filter_any_recall_retention": safe_div(len(selected_episodes), len(pre_episodes)),
        "bridge_episode_denominator_n": int(len(pre_bridge)),
        "post_filter_bridge_captured_episode_n": int(len(selected_bridge)),
        "post_filter_bridge_recall_retention": safe_div(len(selected_bridge), len(pre_bridge)),
        "e1_missed_episode_denominator_n": int(len(e1_missed)),
        "post_filter_e1_missed_captured_episode_n": int(len(selected_e1_missed)),
        "post_filter_e1_missed_capture_retention": safe_div(len(selected_e1_missed), len(e1_missed)),
        "replay_policy_id": HEADLINE_POLICY,
        "window": HEADLINE_WINDOW,
    }


def selected_ids_for_threshold(scores: pd.DataFrame, selected: dict[str, Any]) -> set[str]:
    if not selected or not str(selected.get("threshold_id", "")):
        return set()
    model_scores = scores.loc[scores["model_id"].astype(str).eq(str(selected["model_id"]))]
    return set(model_scores.loc[model_scores["cost_bad_score"].le(float(selected["threshold_value"])), "event_id"].astype(str))


def build_selected_event_tables(
    events: pd.DataFrame,
    scores: pd.DataFrame,
    selected_readout: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_frames: list[pd.DataFrame] = []
    rejected_frames: list[pd.DataFrame] = []
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        model_id = str(selected["model_id"])
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        score_map = scores.loc[scores["model_id"].astype(str).eq(model_id), ["event_id", "cost_bad_score"]].drop_duplicates(
            "event_id"
        )
        frame = events.merge(score_map, on="event_id", how="left")
        frame["model_id"] = model_id
        frame["threshold_id"] = str(selected["threshold_id"])
        keep = frame["event_id"].astype(str).isin(ids)
        cols = selected_event_columns(frame)
        selected_frames.append(frame.loc[keep, cols].copy())
        rejected_frames.append(frame.loc[~keep, cols].copy())
    return (
        pd.concat(selected_frames, ignore_index=True, sort=False) if selected_frames else empty_selected_events(),
        pd.concat(rejected_frames, ignore_index=True, sort=False) if rejected_frames else empty_selected_events(),
    )


def selected_event_columns(frame: pd.DataFrame) -> list[str]:
    cols = [
        "source_pool",
        "model_id",
        "threshold_id",
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "event_split",
        "transition_segment_id",
        "pit_transition_context",
        "previous_non_transition_regime",
        "transition_outcome_label",
        "transition_outcome_direction",
        "cost_bad_score",
        "fast_fail_bad_10d",
        "false_repair_bad_20d",
        "cost_bad_10_20",
        "horizon_complete",
    ]
    return [col for col in cols if col in frame.columns]


def empty_selected_events() -> pd.DataFrame:
    return pd.DataFrame(columns=selected_event_columns(pd.DataFrame()))


def build_cost_quality_readout(events: pd.DataFrame, scores: pd.DataFrame, selected_readout: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        for split in SPLITS:
            for context in ("all_primary_contexts", *PRIMARY_CONTEXTS):
                frame = events.loc[events["event_split"].astype(str).eq(split)].copy()
                if context != "all_primary_contexts":
                    frame = frame.loc[frame["pit_transition_context"].astype(str).eq(context)].copy()
                selected_frame = frame.loc[frame["event_id"].astype(str).isin(ids)]
                before = e_runner.cost_rates_for_events(frame)
                after = e_runner.cost_rates_for_events(selected_frame)
                rows.append(
                    {
                        "source_pool": SOURCE_POOL,
                        "model_id": selected["model_id"],
                        "threshold_id": selected["threshold_id"],
                        "split": split,
                        "pit_transition_context": context,
                        "before_horizon_complete_event_n": before["horizon_complete_event_n"],
                        "after_horizon_complete_event_n": after["horizon_complete_event_n"],
                        "reject_rate": 1 - safe_div(len(selected_frame), len(frame)),
                        "cost_bad_rate_before": before["cost_bad_10_20_rate"],
                        "cost_bad_rate_after": after["cost_bad_10_20_rate"],
                        "cost_reduction_relative": relative_reduction(
                            before["cost_bad_10_20_rate"], after["cost_bad_10_20_rate"]
                        ),
                        "fast_fail_rate_before": before["fast_fail_bad_10d_rate"],
                        "fast_fail_rate_after": after["fast_fail_bad_10d_rate"],
                        "false_repair_rate_before": before["false_repair_bad_20d_rate"],
                        "false_repair_rate_after": after["false_repair_bad_20d_rate"],
                        "denominator_policy": "same_universe_split_context_horizon_complete_before_after",
                    }
                )
    return pd.DataFrame(rows)


def build_recall_retention_readout(
    events: pd.DataFrame,
    membership: pd.DataFrame,
    scores: pd.DataFrame,
    selected_readout: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        for split in SPLITS:
            metrics = retention_metrics(events, membership, split, ids)
            rows.append(
                {
                    "source_pool": SOURCE_POOL,
                    "model_id": selected["model_id"],
                    "threshold_id": selected["threshold_id"],
                    "split": split,
                    "window": HEADLINE_WINDOW,
                    "replay_policy_id": HEADLINE_POLICY,
                    **metrics,
                    "denominator_policy": "primary_transition_prefilter_unique_target_episode",
                }
            )
    return pd.DataFrame(rows)


def build_density_overlap_readout(events: pd.DataFrame, scores: pd.DataFrame, selected_readout: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        for split in SPLITS:
            frame = events.loc[
                events["event_split"].astype(str).eq(split) & events["event_id"].astype(str).isin(ids)
            ].copy()
            family_col = "primary_family_id" if "primary_family_id" in frame.columns else "family_id"
            rows.append(
                {
                    "source_pool": SOURCE_POOL,
                    "model_id": selected["model_id"],
                    "threshold_id": selected["threshold_id"],
                    "split": split,
                    "selected_event_count": int(len(frame)),
                    "formal_event_day_density": safe_div(len(frame), frame["event_t0_date"].nunique()),
                    "unique_instrument_n": int(frame["instrument"].nunique()) if "instrument" in frame.columns else 0,
                    "unique_event_date_n": int(frame["event_t0_date"].nunique()) if "event_t0_date" in frame.columns else 0,
                    "family_concentration": max_share(frame[family_col]) if family_col in frame.columns else np.nan,
                    "board_concentration": max_share(frame["board_bucket"]) if "board_bucket" in frame.columns else np.nan,
                    "density_readout_status": "diagnostic_no_predeclared_gate",
                }
            )
    return pd.DataFrame(rows)


def max_share(series: pd.Series) -> float:
    denom = int(series.notna().sum())
    if denom == 0:
        return np.nan
    return float(series.dropna().astype(str).value_counts().iloc[0] / denom)


def attach_transition_segment_to_membership(mem: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    event_segments = events[
        [col for col in ["event_id", "canonical_event_id", "transition_segment_id"] if col in events.columns]
    ].drop_duplicates("event_id")
    out = mem.merge(
        event_segments[[col for col in ["event_id", "transition_segment_id"] if col in event_segments.columns]],
        on="event_id",
        how="left",
    )
    if "canonical_event_id" in out.columns and "canonical_event_id" in event_segments.columns:
        canonical_segments = (
            event_segments[["canonical_event_id", "transition_segment_id"]]
            .dropna(subset=["canonical_event_id"])
            .drop_duplicates("canonical_event_id")
            .rename(columns={"transition_segment_id": "transition_segment_id_from_canonical"})
        )
        out = out.merge(canonical_segments, on="canonical_event_id", how="left")
        out["transition_segment_id"] = out["transition_segment_id"].fillna(
            out["transition_segment_id_from_canonical"]
        )
        out = out.drop(columns=["transition_segment_id_from_canonical"])
    return out


def build_segment_concentration_audit(
    events: pd.DataFrame,
    membership: pd.DataFrame,
    scores: pd.DataFrame,
    selected_readout: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cross_segments = (
        events.dropna(subset=["transition_segment_id"])
        .drop_duplicates(["transition_segment_id", "event_split"])
        .groupby("transition_segment_id")["event_split"]
        .nunique()
    )
    cross_set = set(cross_segments.loc[cross_segments.gt(1)].index.astype(str))
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        for split in SPLITS:
            selected_events = events.loc[
                events["event_split"].astype(str).eq(split) & events["event_id"].astype(str).isin(ids)
            ].copy()
            selected_segments = selected_events["transition_segment_id"].dropna().astype(str)
            event_counts = selected_segments.value_counts()
            mem = primary_membership(events, membership, split)
            selected_event_ids, selected_canonical_ids = event_reference_sets(selected_events)
            selected_mem = mem.loc[membership_match_mask(mem, selected_event_ids, selected_canonical_ids)].copy()
            selected_mem = attach_transition_segment_to_membership(selected_mem, events)
            pairs = selected_mem[["transition_segment_id", "target_episode_id"]].dropna().drop_duplicates()
            episode_counts = pairs.groupby("transition_segment_id")["target_episode_id"].nunique()
            episode_den = int(selected_mem["target_episode_id"].dropna().astype(str).nunique())
            top1_episode_share = safe_div(int(episode_counts.max()), episode_den) if len(episode_counts) else np.nan
            top3_episode_share = (
                safe_div(int(episode_counts.sort_values(ascending=False).head(3).sum()), episode_den)
                if len(episode_counts)
                else np.nan
            )
            overlap_n = int(pairs.groupby("target_episode_id")["transition_segment_id"].nunique().gt(1).sum()) if len(pairs) else 0
            status = "pass"
            effective_episode_seg = inverse_herfindahl(episode_counts)
            if split == "robustness" and pd.notna(top1_episode_share) and top1_episode_share > 0.50:
                status = "low_power_top1_segment_episode_share_gt_50pct"
            elif split == "robustness" and pd.notna(effective_episode_seg) and effective_episode_seg < 5:
                status = "low_power_effective_selected_segment_n_lt_5"
            rows.append(
                {
                    "source_pool": SOURCE_POOL,
                    "model_id": selected["model_id"],
                    "threshold_id": selected["threshold_id"],
                    "split": split,
                    "selected_transition_segment_n": int(selected_segments.nunique()),
                    "effective_selected_transition_segment_n": effective_episode_seg,
                    "top1_segment_selected_event_share": safe_div(int(event_counts.max()), len(selected_events)) if len(event_counts) else np.nan,
                    "top1_segment_target_episode_share": top1_episode_share,
                    "top3_segment_target_episode_share": top3_episode_share,
                    "multi_segment_episode_overlap_n": overlap_n,
                    "cross_split_segment_n": int(len(set(selected_segments).intersection(cross_set))),
                    "segment_concentration_status": status,
                }
            )
    return pd.DataFrame(rows)


def build_outcome_readout(events: pd.DataFrame, scores: pd.DataFrame, selected_readout: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    dims = ["pit_transition_context", "transition_outcome_label", "transition_outcome_direction"]
    for _, selected in selected_readout.iterrows():
        if str(selected.get("selection_status", "")) != "train_selected":
            continue
        ids = selected_ids_for_threshold(scores, selected.to_dict())
        for split in SPLITS:
            split_frame = events.loc[events["event_split"].astype(str).eq(split)].copy()
            for keys, group in split_frame.groupby(dims, dropna=False):
                for bucket, mask in (
                    ("all_prefilter", pd.Series(True, index=group.index)),
                    ("selected", group["event_id"].astype(str).isin(ids)),
                    ("rejected", ~group["event_id"].astype(str).isin(ids)),
                ):
                    sub = group.loc[mask].copy()
                    rates = e_runner.cost_rates_for_events(sub)
                    rows.append(
                        {
                            "source_pool": SOURCE_POOL,
                            "model_id": selected["model_id"],
                            "threshold_id": selected["threshold_id"],
                            "split": split,
                            "pit_transition_context": keys[0],
                            "transition_outcome_label": keys[1],
                            "transition_outcome_direction": keys[2],
                            "selection_bucket": bucket,
                            "event_n": int(len(sub)),
                            "unique_segment_n": int(sub["transition_segment_id"].nunique()),
                            "horizon_complete_event_n": rates["horizon_complete_event_n"],
                            "cost_bad_10_20_rate": rates["cost_bad_10_20_rate"],
                            "fast_fail_bad_10d_rate": rates["fast_fail_bad_10d_rate"],
                            "false_repair_bad_20d_rate": rates["false_repair_bad_20d_rate"],
                            "readout_only_not_used_for_training": True,
                        }
                    )
    return pd.DataFrame(rows)


def build_uplift_comparison(
    oos: pd.DataFrame,
    selected: pd.DataFrame,
    cost: pd.DataFrame,
    recall: pd.DataFrame,
    concentration: pd.DataFrame,
    stability: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        base_oos = get_row(oos, model_id="transition_cost_rejector_no_context", split=split)
        prev_oos = get_row(oos, model_id="transition_cost_rejector_prev_context", split=split)
        base_sel = selected_row(selected, "transition_cost_rejector_no_context")
        prev_sel = selected_row(selected, "transition_cost_rejector_prev_context")
        base_cost = selected_metric_row(cost, base_sel, split)
        prev_cost = selected_metric_row(cost, prev_sel, split)
        base_recall = selected_metric_row(recall, base_sel, split)
        prev_recall = selected_metric_row(recall, prev_sel, split)
        prev_conc = selected_metric_row(concentration, prev_sel, split)
        rows.append(
            {
                "split": split,
                "comparison": "prev_context_vs_no_context",
                "roc_auc_uplift": diff(prev_oos.get("roc_auc"), base_oos.get("roc_auc")),
                "pr_auc_uplift": diff(prev_oos.get("pr_auc"), base_oos.get("pr_auc")),
                "top_decile_lift_uplift": diff(prev_oos.get("top_decile_lift"), base_oos.get("top_decile_lift")),
                "cost_reduction_uplift": diff(
                    prev_cost.get("cost_reduction_relative"), base_cost.get("cost_reduction_relative")
                ),
                "any_recall_retention_delta": diff(
                    prev_recall.get("post_filter_any_recall_retention"),
                    base_recall.get("post_filter_any_recall_retention"),
                ),
                "e1_missed_capture_retention_delta": diff(
                    prev_recall.get("post_filter_e1_missed_capture_retention"),
                    base_recall.get("post_filter_e1_missed_capture_retention"),
                ),
                "prev_context_segment_concentration_status": prev_conc.get("segment_concentration_status", ""),
            }
        )
    for scheme in ("segment_grouped_cv", "chronological_purged_segment_cv"):
        row = stability.loc[
            stability["model_id"].astype(str).eq("transition_cost_rejector_prev_context")
            & stability["cv_scheme"].astype(str).eq(scheme)
        ]
        if not row.empty:
            rows.append(
                {
                    "split": "train_internal",
                    "comparison": f"prev_context_vs_no_context:{scheme}",
                    "roc_auc_uplift": row.iloc[0].get("median_roc_auc_uplift_vs_no_context", np.nan),
                    "pr_auc_uplift": row.iloc[0].get("median_pr_auc_uplift_vs_no_context", np.nan),
                    "positive_uplift_fold_share": row.iloc[0].get("positive_uplift_fold_share", np.nan),
                    "stability_status": row.iloc[0].get("stability_status", ""),
                }
            )
    return pd.DataFrame(rows)


def get_row(frame: pd.DataFrame, **filters: str) -> dict[str, Any]:
    if frame.empty:
        return {}
    sub = frame.copy()
    for col, value in filters.items():
        if col not in sub.columns:
            return {}
        sub = sub.loc[sub[col].astype(str).eq(str(value))]
    return sub.iloc[0].to_dict() if not sub.empty else {}


def selected_row(selected: pd.DataFrame, model_id: str) -> dict[str, Any]:
    if selected.empty or "model_id" not in selected.columns or "selection_status" not in selected.columns:
        return {}
    row = selected.loc[
        selected["model_id"].astype(str).eq(model_id)
        & selected["selection_status"].astype(str).eq("train_selected")
    ]
    return row.iloc[0].to_dict() if not row.empty else {}


def selected_metric_row(frame: pd.DataFrame, selected: dict[str, Any], split: str) -> dict[str, Any]:
    if frame.empty or not selected:
        return {}
    sub = frame.loc[
        frame["model_id"].astype(str).eq(str(selected.get("model_id", "")))
        & frame["threshold_id"].astype(str).eq(str(selected.get("threshold_id", "")))
        & frame["split"].astype(str).eq(split)
    ]
    if "pit_transition_context" in sub.columns:
        all_rows = sub.loc[sub["pit_transition_context"].astype(str).eq("all_primary_contexts")]
        if not all_rows.empty:
            sub = all_rows
    return sub.iloc[0].to_dict() if not sub.empty else {}


def diff(left: Any, right: Any) -> float:
    left_num = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
    right_num = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
    if pd.isna(left_num) or pd.isna(right_num):
        return np.nan
    return float(left_num - right_num)


def decide(
    selected: pd.DataFrame,
    oos: pd.DataFrame,
    uplift: pd.DataFrame,
    training: pd.DataFrame,
    concentration: pd.DataFrame,
    outcome: pd.DataFrame,
    stability: pd.DataFrame,
) -> tuple[str, list[str]]:
    failures: list[str] = []
    train = training.loc[training["split"].astype(str).eq("train")].iloc[0]
    robustness = training.loc[training["split"].astype(str).eq("robustness")].iloc[0]
    if str(train.get("power_status")) != "pass":
        failures.append(str(train.get("power_status")))
    if str(robustness.get("power_status")) != "pass":
        failures.append(str(robustness.get("power_status")))
    for scheme in ("segment_grouped_cv", "chronological_purged_segment_cv"):
        row = stability.loc[
            stability["model_id"].astype(str).eq("transition_cost_rejector_prev_context")
            & stability["cv_scheme"].astype(str).eq(scheme)
        ]
        if row.empty or int(row.iloc[0].get("valid_fold_n", 0)) < 3:
            failures.append(f"{scheme}_valid_fold_n_lt_3")
    prev_sel = selected_row(selected, "transition_cost_rejector_prev_context")
    no_sel = selected_row(selected, "transition_cost_rejector_no_context")
    if not prev_sel:
        failures.append("prev_context_no_train_diagnostic_threshold")
    if not no_sel:
        failures.append("no_context_no_train_diagnostic_threshold")
    robust_conc = selected_metric_row(concentration, prev_sel, "robustness")
    if str(robust_conc.get("segment_concentration_status", "")).startswith("low_power"):
        failures.append(str(robust_conc.get("segment_concentration_status")))
    outcome_low = outcome_power_failures(outcome)
    failures.extend(outcome_low)
    if failures:
        return FINAL_LOW_POWER, sorted(set(failures))

    robust = uplift.loc[uplift["split"].astype(str).eq("robustness")]
    valid = uplift.loc[uplift["split"].astype(str).eq("validation")]
    robust_row = robust.iloc[0].to_dict() if not robust.empty else {}
    valid_row = valid.iloc[0].to_dict() if not valid.empty else {}
    grouped = stability_row(stability, "segment_grouped_cv")
    purged = stability_row(stability, "chronological_purged_segment_cv")
    uplift_pass = (
        (
            pd.to_numeric(pd.Series([robust_row.get("roc_auc_uplift")]), errors="coerce").iloc[0] >= 0.02
            or pd.to_numeric(pd.Series([robust_row.get("pr_auc_uplift")]), errors="coerce").iloc[0] >= 0.02
        )
        and pd.to_numeric(pd.Series([robust_row.get("top_decile_lift_uplift")]), errors="coerce").iloc[0] >= 0.15
        and pd.to_numeric(pd.Series([robust_row.get("cost_reduction_uplift")]), errors="coerce").iloc[0] >= 0.05
        and pd.to_numeric(pd.Series([robust_row.get("any_recall_retention_delta")]), errors="coerce").iloc[0] >= -0.05
        and pd.to_numeric(pd.Series([robust_row.get("e1_missed_capture_retention_delta")]), errors="coerce").iloc[0] >= -0.05
        and grouped.get("stable", False)
        and purged.get("nonnegative", False)
        and validation_same_direction(valid_row, robust_row)
    )
    if uplift_pass:
        return FINAL_UPLIFT, []
    reasons = ["robustness_or_validation_uplift_gate_not_met"]
    if not grouped.get("stable", False):
        reasons.append(f"grouped_status:{grouped.get('status', '')}")
    if not purged.get("nonnegative", False):
        reasons.append(f"purged_status:{purged.get('status', '')}")
    return FINAL_NO_UPLIFT, sorted(set(reasons))


def stability_row(stability: pd.DataFrame, scheme: str) -> dict[str, Any]:
    row = stability.loc[
        stability["model_id"].astype(str).eq("transition_cost_rejector_prev_context")
        & stability["cv_scheme"].astype(str).eq(scheme)
    ]
    if row.empty:
        return {"stable": False, "nonnegative": False, "status": "missing"}
    item = row.iloc[0]
    roc = pd.to_numeric(pd.Series([item.get("median_roc_auc_uplift_vs_no_context")]), errors="coerce").iloc[0]
    pr = pd.to_numeric(pd.Series([item.get("median_pr_auc_uplift_vs_no_context")]), errors="coerce").iloc[0]
    share = pd.to_numeric(pd.Series([item.get("positive_uplift_fold_share")]), errors="coerce").iloc[0]
    nonnegative = (pd.notna(roc) and roc >= 0) or (pd.notna(pr) and pr >= 0)
    return {
        "stable": bool(nonnegative and pd.notna(share) and share >= 0.60),
        "nonnegative": bool(nonnegative),
        "status": item.get("stability_status", ""),
    }


def validation_same_direction(validation_row: dict[str, Any], robust_row: dict[str, Any]) -> bool:
    for metric in ("roc_auc_uplift", "pr_auc_uplift", "cost_reduction_uplift"):
        robust = pd.to_numeric(pd.Series([robust_row.get(metric)]), errors="coerce").iloc[0]
        validation = pd.to_numeric(pd.Series([validation_row.get(metric)]), errors="coerce").iloc[0]
        if pd.notna(robust) and robust > 0 and pd.notna(validation) and validation < 0:
            return False
    return True


def outcome_power_failures(outcome: pd.DataFrame) -> list[str]:
    failures: list[str] = []
    if outcome.empty:
        return failures
    pre = outcome.loc[
        outcome["split"].astype(str).eq("robustness")
        & outcome["selection_bucket"].astype(str).eq("all_prefilter")
    ].copy()
    if pre.empty:
        return failures
    aggregate = (
        pre.groupby("transition_outcome_label", dropna=False)["unique_segment_n"].max().reset_index()
    )
    for _, row in aggregate.iterrows():
        label = str(row["transition_outcome_label"])
        if label in {"transition_continuation", "transition_conversion"} and int(row["unique_segment_n"]) < 3:
            failures.append(f"robustness_{label}_segment_n_lt_3")
    return failures


def build_decision_tiers(decision: str, failures: list[str], selected: pd.DataFrame) -> pd.DataFrame:
    prev = selected_row(selected, "transition_cost_rejector_prev_context")
    return pd.DataFrame(
        [
            {
                "candidate_tier": "diagnostic_ablation",
                "selected_model_id": prev.get("model_id", ""),
                "selected_threshold_id": prev.get("threshold_id", ""),
                "selected_keep_fraction": prev.get("selected_keep_fraction", np.nan),
                "final_decision": decision,
                "supported_usage": "diagnostic_only",
                "failure_reason": ";".join(failures),
                "non_claim": "not_research_entry_not_production_not_conversion_classifier",
            }
        ]
    )


def build_contract() -> str:
    return "\n".join(
        [
            "# Experiment I Contract",
            "",
            "- Scope: transition primary universe only.",
            "- Primary question: previous-regime PIT context ablation for cost_bad sorting.",
            "- Model: balanced L2 logistic regression; train-only preprocessing and threshold selection.",
            "- Context collinearity policy: `previous_non_transition_regime` is audit-only; only `pit_transition_context` enters the model matrix.",
            "- Forbidden fields: future outcome, next regime, complete segment duration, and conversion/continuation labels as model features.",
            "- Decisions are diagnostic only and do not modify E/H risk_on selected threshold or manifests.",
            "",
        ]
    )


def build_report(decision: str, failures: list[str], frames: dict[str, pd.DataFrame], manifests: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = [
        "# Experiment I - Transition Previous-Regime Context Cost Rejector Ablation 报告",
        "",
        f"最终决策：`{decision}`",
        "",
        "## 实验定位",
        "",
        "本实验只验证 transition universe 内的 PIT previous-regime context 是否改善 `cost_bad_10_20` 排序。"
        "它不并入 E/H 的 risk_on-only research-entry gate，也不训练 conversion / continuation classifier。",
        "",
        f"- G decision: `{manifests['g'].get('decision', '')}`",
        f"- H decision: `{manifests['h'].get('decision', '')}`",
        f"- D decision: `{manifests['d'].get('decision', '')}`",
        f"- E decision: `{manifests['e'].get('decision', '')}`",
        "",
    ]
    if failures:
        lines.extend(["## Non-Pass Reasons", "", *[f"- `{reason}`" for reason in failures], ""])
    training = frames.get("transition_context_ablation_training_universe_audit", pd.DataFrame())
    if not training.empty:
        lines.extend(["## Universe 与 Segment Power", ""])
        for _, row in training.iterrows():
            lines.append(
                f"- {row['split']}: events `{row['event_n']}`, complete `{row['horizon_complete_event_n']}`, "
                f"positive `{row['positive_n']}`, unique segments `{row['unique_transition_segment_n']}`, "
                f"effective segments `{row['effective_transition_segment_n']:.2f}`, status `{row['power_status']}`。"
            )
        lines.append("")
    registry = frames.get("transition_context_ablation_model_registry", pd.DataFrame())
    if not registry.empty:
        lines.extend(["## Model Arms", ""])
        for _, row in registry.iterrows():
            lines.append(
                f"- `{row['model_id']}`: status `{row['model_status']}`, features `{row['feature_count']}`, "
                f"train positives `{row['train_positive_n']}`。"
            )
        lines.append("")
    oos = frames.get("transition_context_ablation_oos_separability", pd.DataFrame())
    if not oos.empty:
        lines.extend(["## OOS Separability", ""])
        for _, row in oos.loc[oos["split"].isin(["validation", "robustness"])].iterrows():
            lines.append(
                f"- {row['split']} `{row['model_id']}`: ROC-AUC `{fmt(row['roc_auc'])}`, "
                f"PR-AUC `{fmt(row['pr_auc'])}`, top-decile lift `{fmt(row['top_decile_lift'])}`。"
            )
        lines.append("")
    stability = frames.get("transition_context_ablation_segment_grouped_stability", pd.DataFrame())
    if not stability.empty:
        lines.extend(["## Segment-Aware Stability", ""])
        for _, row in stability.loc[stability["model_id"].eq("transition_cost_rejector_prev_context")].iterrows():
            lines.append(
                f"- `{row['cv_scheme']}`: valid folds `{row['valid_fold_n']}/{row['fold_n']}`, "
                f"median ROC uplift `{fmt(row['median_roc_auc_uplift_vs_no_context'])}`, "
                f"median PR uplift `{fmt(row['median_pr_auc_uplift_vs_no_context'])}`, "
                f"positive fold share `{fmt(row['positive_uplift_fold_share'])}`, status `{row['stability_status']}`。"
            )
        lines.append("")
    selected = frames.get("transition_context_ablation_selected_threshold_readout", pd.DataFrame())
    if not selected.empty:
        lines.extend(["## Train-Selected Thresholds", ""])
        for _, row in selected.iterrows():
            lines.append(
                f"- `{row['model_id']}`: status `{row['selection_status']}`, threshold `{row.get('threshold_id', '')}`, "
                f"keep `{fmt(row.get('selected_keep_fraction', np.nan))}`, reason `{row.get('failure_reason', '')}`。"
            )
        lines.append("")
    frontier = frames.get("transition_context_ablation_threshold_frontier", pd.DataFrame())
    if not frontier.empty:
        lines.extend(["## Selected-Threshold Frontier", ""])
        frontier_cols = [
            "model_id",
            "threshold_id",
            "keep_fraction",
            "selected_model_threshold_flag",
            "train_cost_reduction_relative",
            "train_any_recall_retention",
            "train_e1_missed_capture_retention",
            "robustness_cost_reduction_relative",
            "robustness_any_recall_retention",
        ]
        ordered = frontier.sort_values(["model_id", "keep_fraction"], ascending=[True, False])
        lines.extend(report_table(ordered, frontier_cols, max_rows=60))
        lines.append("")
    cost = frames.get("transition_context_ablation_cost_quality_readout", pd.DataFrame())
    if not cost.empty:
        lines.extend(["## Cost Quality Readout", ""])
        cost_cols = [
            "model_id",
            "split",
            "pit_transition_context",
            "before_horizon_complete_event_n",
            "after_horizon_complete_event_n",
            "reject_rate",
            "cost_bad_rate_before",
            "cost_bad_rate_after",
            "cost_reduction_relative",
            "fast_fail_rate_after",
            "false_repair_rate_after",
        ]
        lines.extend(report_table(cost, cost_cols, max_rows=80))
        lines.append("")
    recall = frames.get("transition_context_ablation_recall_retention_readout", pd.DataFrame())
    if not recall.empty:
        lines.extend(["## Recall Retention Readout", ""])
        recall_cols = [
            "model_id",
            "split",
            "target_episode_denominator_n",
            "post_filter_captured_episode_n",
            "post_filter_any_recall_retention",
            "bridge_episode_denominator_n",
            "post_filter_bridge_recall_retention",
            "e1_missed_episode_denominator_n",
            "post_filter_e1_missed_capture_retention",
        ]
        lines.extend(report_table(recall, recall_cols, max_rows=40))
        lines.append("")
    density = frames.get("transition_context_ablation_density_overlap_readout", pd.DataFrame())
    if not density.empty:
        lines.extend(["## Density / Overlap Readout", ""])
        density_cols = [
            "model_id",
            "split",
            "selected_event_count",
            "formal_event_day_density",
            "unique_instrument_n",
            "unique_event_date_n",
            "family_concentration",
            "board_concentration",
            "density_readout_status",
        ]
        lines.extend(report_table(density, density_cols, max_rows=40))
        lines.append("")
    uplift = frames.get("transition_context_ablation_uplift_comparison", pd.DataFrame())
    if not uplift.empty:
        lines.extend(["## Uplift Readout", ""])
        for _, row in uplift.loc[uplift["split"].isin(["validation", "robustness"])].iterrows():
            lines.append(
                f"- {row['split']}: ROC uplift `{fmt(row['roc_auc_uplift'])}`, PR uplift `{fmt(row['pr_auc_uplift'])}`, "
                f"cost reduction uplift `{fmt(row['cost_reduction_uplift'])}`, any recall delta `{fmt(row['any_recall_retention_delta'])}`。"
            )
        lines.append("")
    outcome = frames.get("transition_context_ablation_outcome_readout", pd.DataFrame())
    if not outcome.empty:
        lines.extend(["## Ex-Post Continuation / Conversion Readout", ""])
        outcome_view = outcome.loc[
            outcome["model_id"].astype(str).eq("transition_cost_rejector_prev_context")
            & outcome["selection_bucket"].astype(str).isin(["all_prefilter", "selected"])
        ].copy()
        outcome_cols = [
            "split",
            "pit_transition_context",
            "transition_outcome_label",
            "transition_outcome_direction",
            "selection_bucket",
            "event_n",
            "unique_segment_n",
            "horizon_complete_event_n",
            "cost_bad_10_20_rate",
            "fast_fail_bad_10d_rate",
            "false_repair_bad_20d_rate",
        ]
        lines.extend(report_table(outcome_view, outcome_cols, max_rows=80))
        lines.append("")
    concentration = frames.get("transition_context_ablation_segment_concentration_audit", pd.DataFrame())
    if not concentration.empty:
        lines.extend(["## Segment Concentration", ""])
        prev = concentration.loc[concentration["model_id"].eq("transition_cost_rejector_prev_context")]
        for _, row in prev.iterrows():
            lines.append(
                f"- {row['split']}: selected segments `{row['selected_transition_segment_n']}`, "
                f"effective episode segments `{fmt(row['effective_selected_transition_segment_n'])}`, "
                f"top1 episode share `{fmt(row['top1_segment_target_episode_share'])}`, status `{row['segment_concentration_status']}`。"
            )
        lines.append("")
    lines.extend(
        [
            "## Findings / Insight",
            "",
            "1. 本实验的关键风险不是 event_n 不足，而是 transition segment 内事件高度相关；因此 grouped / purged 稳定性比普通 event-level AUC 更重要。",
            "2. `pit_transition_context` 是可在 t0 使用的上下文变量，但它只在 transition universe 内定义，不能直接污染 H 的 risk_on-only gate。",
            "3. `transition_outcome_label` 与 `transition_outcome_direction` 只用于 ex-post readout；若 uplift 只来自 conversion 子样本，应视为下一轮研究线索，而不是当前可用模型证据。",
            "",
            "## Explicit Non-Claims",
            "",
            "- 不是 E/H research-entry gate。",
            "- 不是 direct-entry support。",
            "- 不是 production-ready model。",
            "- 没有训练 conversion / continuation classifier。",
            "- 即便出现 uplift，也只说明 previous-regime context 值得进入 future multi-regime rejector 研究。",
            "",
        ]
    )
    return "\n".join(lines)


def fmt(value: Any) -> str:
    value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return "nan" if pd.isna(value) else f"{float(value):.4f}"


def fmt_report_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return fmt(value)
    text = str(value)
    return text.replace("|", "\\|")


def report_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 40) -> list[str]:
    cols = [col for col in columns if col in frame.columns]
    if frame.empty or not cols:
        return ["_无可报告行。_"]
    view = frame.loc[:, cols].head(max_rows).copy()
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(fmt_report_cell(row[col]) for col in cols) + " |")
    if len(frame) > max_rows:
        lines.append(f"_仅显示前 {max_rows} 行；完整数据见对应 publishable table。_")
    return lines


def build_manifest(
    decision: str,
    failures: list[str],
    input_paths: dict[str, Path],
    frames: dict[str, pd.DataFrame],
    manifests: dict[str, dict[str, Any]],
    feature_sets: dict[str, list[str]],
    preprocessing_hashes: dict[str, str],
    schema_fingerprints: dict[str, str],
) -> dict[str, Any]:
    output_hashes = {
        key: path_hash(path)
        for key, path in OUTPUT_PATHS.items()
        if key != "transition_previous_regime_context_cost_rejector_ablation_manifest" and path.exists()
    }
    output_rows = {
        key: int(len(frame))
        for key, frame in frames.items()
        if isinstance(frame, pd.DataFrame)
    }
    train = frames.get("transition_context_ablation_training_universe_audit", pd.DataFrame())
    train_row = train.loc[train["split"].astype(str).eq("train")].iloc[0].to_dict() if not train.empty else {}
    stability = frames.get("transition_context_ablation_segment_grouped_stability", pd.DataFrame())
    selected = selected_row(
        frames.get("transition_context_ablation_selected_threshold_readout", pd.DataFrame()),
        "transition_cost_rejector_prev_context",
    )
    upstream_source_caveat_status = stable_hash(
        {
            "G": manifests["g"].get("decision", ""),
            "H": manifests["h"].get("decision", ""),
            "D": manifests["d"].get("decision", ""),
            "E": manifests["e"].get("decision", ""),
        }
    )
    return {
        "experiment_id": "08_experiment_i_transition_previous_regime_context_cost_rejector_ablation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "final_decision": decision,
        "blocked_reasons": failures,
        "non_pass_reasons": failures,
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "runner_code_hash": path_hash(Path(__file__)),
        "input_artifacts": {key: str(path) for key, path in input_paths.items()},
        "input_hashes": {key: path_hash(path) for key, path in input_paths.items()},
        "schema_fingerprints": schema_fingerprints,
        "input_schema_fingerprints": schema_fingerprints,
        "upstream_g_decision": manifests["g"].get("decision", ""),
        "upstream_h_decision": manifests["h"].get("decision", ""),
        "upstream_d_decision": manifests["d"].get("decision", ""),
        "upstream_e_decision": manifests["e"].get("decision", ""),
        "upstream_source_caveat_status": f"recorded:{upstream_source_caveat_status}",
        "g_selected_grid_rule_id": manifests["g"].get("selected_grid_rule_id", ""),
        "upstream_decisions": {
            "G": manifests["g"].get("decision", ""),
            "H": manifests["h"].get("decision", ""),
            "D": manifests["d"].get("decision", ""),
            "E": manifests["e"].get("decision", ""),
        },
        "selected_grid_rule_id": manifests["g"].get("selected_grid_rule_id", ""),
        "selected_threshold_id": selected.get("threshold_id", ""),
        "selected_keep_fraction": selected.get("selected_keep_fraction", np.nan),
        "selected_threshold_value": selected.get("threshold_value", np.nan),
        "feature_columns_hash": stable_hash(feature_sets),
        "feature_sets": feature_sets,
        "preprocessing_hashes": preprocessing_hashes,
        "previous_regime_context_feature_list": CONTEXT_MODEL_FEATURES,
        "context_collinearity_policy": "previous_non_transition_regime=audit_only",
        "train_unique_segment_n": train_row.get("unique_transition_segment_n", np.nan),
        "train_effective_segment_n": train_row.get("effective_transition_segment_n", np.nan),
        "grouped_purged_stability_summary": stability.to_dict("records") if not stability.empty else [],
        "forbidden_future_outcome_feature_check": "pass"
        if not failures or not any("future" in reason for reason in failures)
        else "fail",
        "selected_model_arm": "transition_cost_rejector_prev_context",
        "output_paths": {key: str(path) for key, path in OUTPUT_PATHS.items()},
        "output_hashes": output_hashes,
        "output_row_counts": output_rows,
        "event_level_outputs": {
            key: {
                "path": str(OUTPUT_PATHS[key]),
                "sha256": path_hash(OUTPUT_PATHS[key]),
                "row_count": int(len(frames.get(key, pd.DataFrame()))),
                "schema_fingerprint": dataframe_schema_fingerprint(frames.get(key, pd.DataFrame())),
            }
            for key in [
                "transition_context_ablation_event_scores",
                "transition_context_ablation_selected_events",
                "transition_context_ablation_rejected_events",
            ]
        },
    }


def empty_frames(input_frame: pd.DataFrame, upstream: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    frames = {
        key: pd.DataFrame()
        for key in OUTPUT_PATHS
        if key.startswith("transition_context_ablation_")
    }
    frames["transition_context_ablation_input_audit"] = input_frame
    if upstream is not None:
        frames["transition_context_ablation_upstream_binding_audit"] = upstream
    return frames


def write_outputs(
    decision: str,
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    input_paths: dict[str, Path],
    manifests: dict[str, dict[str, Any]],
    feature_sets: dict[str, list[str]] | None = None,
    preprocessing_hashes: dict[str, str] | None = None,
    schema_fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    ensure_dirs()
    feature_sets = feature_sets or {}
    preprocessing_hashes = preprocessing_hashes or {}
    schema_fingerprints = schema_fingerprints or {}
    frames["transition_context_ablation_decision_tiers"] = build_decision_tiers(
        decision,
        failures,
        frames.get("transition_context_ablation_selected_threshold_readout", pd.DataFrame()),
    )
    for key, frame in frames.items():
        if key in OUTPUT_PATHS and isinstance(frame, pd.DataFrame):
            write_df(OUTPUT_PATHS[key], frame)
    write_text(OUTPUT_PATHS["transition_previous_regime_context_cost_rejector_ablation_contract"], build_contract())
    write_text(
        OUTPUT_PATHS["transition_previous_regime_context_cost_rejector_ablation_report"],
        build_report(decision, failures, frames, manifests),
    )
    manifest = build_manifest(
        decision,
        failures,
        input_paths,
        frames,
        manifests,
        feature_sets,
        preprocessing_hashes,
        schema_fingerprints,
    )
    write_json(OUTPUT_PATHS["transition_previous_regime_context_cost_rejector_ablation_manifest"], manifest)
    return {
        "decision": decision,
        "blocked_reasons": failures,
        "manifest_path": str(OUTPUT_PATHS["transition_previous_regime_context_cost_rejector_ablation_manifest"]),
        "report_path": str(OUTPUT_PATHS["transition_previous_regime_context_cost_rejector_ablation_report"]),
    }


def run(mode: str = "full") -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_failures, input_paths = input_audit()
    if mode == "check-inputs":
        write_df(OUTPUT_PATHS["transition_context_ablation_input_audit"], input_frame)
        return {"decision": "transition_previous_regime_context_inputs_checked", "input_failures": input_failures}
    g_manifest = read_json(input_paths["g_manifest"])
    h_manifest = read_json(input_paths["h_manifest"])
    d_manifest = read_json(input_paths["d_manifest"])
    e_manifest = read_json(input_paths["e_manifest"])
    manifests = {"g": g_manifest, "h": h_manifest, "d": d_manifest, "e": e_manifest}
    upstream, upstream_failures, _ = build_upstream_binding_audit(g_manifest, h_manifest, d_manifest, e_manifest)
    if input_failures:
        frames = empty_frames(input_frame, upstream)
        return write_outputs(FINAL_INPUT_BLOCKED, input_failures, frames, input_paths, manifests)
    g_hash_failures = [x for x in upstream_failures if x.startswith("G_artifact")]
    h_hash_failures = [x for x in upstream_failures if x.startswith("H_artifact")]
    if g_hash_failures:
        frames = empty_frames(input_frame, upstream)
        return write_outputs(FINAL_G_HASH_BLOCKED, g_hash_failures, frames, input_paths, manifests)
    if h_hash_failures:
        frames = empty_frames(input_frame, upstream)
        return write_outputs(FINAL_H_HASH_BLOCKED, h_hash_failures, frames, input_paths, manifests)

    assignments = read_csv(input_paths["g_event_assignment"])
    selected_grid = str(g_manifest.get("selected_grid_rule_id", ""))
    if not selected_grid or assignments.loc[assignments["grid_rule_id"].astype(str).eq(selected_grid)].empty:
        frames = empty_frames(input_frame, upstream)
        return write_outputs(FINAL_GRID_BLOCKED, ["selected_grid_rule_id_missing_or_not_found"], frames, input_paths, manifests)

    g_segment_catalog = read_csv(input_paths["g_segment_catalog"])
    g_universe_binding_audit = read_csv(input_paths["g_universe_binding_audit"])
    g_leakage_audit = read_csv(input_paths["g_leakage_audit"])
    g_label_join_audit = read_csv(input_paths["g_label_join_audit"])
    g_segment_matrix = read_csv(input_paths["g_segment_matrix"])
    g_cost_quality_matrix = read_csv(input_paths["g_cost_quality_matrix"])
    g_recall_retention_matrix = read_csv(input_paths["g_recall_retention_matrix"])
    g_e1_missed_capture = read_csv(input_paths["g_e1_missed_capture"])
    h_contract = read_csv(input_paths["h_feature_contract"])
    h_feature_delta = read_csv(input_paths["h_feature_delta_from_e"])
    h_asof_join_audit = read_csv(input_paths["h_asof_join_audit"])
    h_model_registry = read_csv(input_paths["h_model_registry"])
    canonical = read_csv(input_paths["canonical_events"])
    event_instances = read_csv(input_paths["event_instances"])
    labels = pd.read_parquet(input_paths["event_labels"])
    panel = pd.read_parquet(input_paths["cross_section_feature_panel"])
    membership = pd.read_parquet(input_paths["d_membership"])
    d_scope_retention = read_csv(input_paths["d_scope_retention"])
    d_label_leakage_source = read_csv(input_paths["d_label_leakage_audit"])
    loaded_input_frames = {
        "g_event_assignment": assignments,
        "g_segment_catalog": g_segment_catalog,
        "g_universe_binding_audit": g_universe_binding_audit,
        "g_leakage_audit": g_leakage_audit,
        "g_label_join_audit": g_label_join_audit,
        "g_segment_matrix": g_segment_matrix,
        "g_cost_quality_matrix": g_cost_quality_matrix,
        "g_recall_retention_matrix": g_recall_retention_matrix,
        "g_e1_missed_capture": g_e1_missed_capture,
        "h_feature_contract": h_contract,
        "h_feature_delta_from_e": h_feature_delta,
        "h_asof_join_audit": h_asof_join_audit,
        "h_model_registry": h_model_registry,
        "canonical_events": canonical,
        "event_instances": event_instances,
        "event_labels": labels,
        "cross_section_feature_panel": panel,
        "d_membership": membership,
        "d_scope_retention": d_scope_retention,
        "d_label_leakage_audit": d_label_leakage_source,
    }
    input_frame = record_loaded_input_metadata(input_frame, loaded_input_frames)
    schema_fingerprints = build_schema_fingerprints(loaded_input_frames)
    d_leakage, d_leakage_failures = label_leakage_pass(d_label_leakage_source)
    if d_leakage_failures:
        frames = empty_frames(input_frame, upstream)
        frames["transition_context_ablation_leakage_audit"] = d_leakage
        return write_outputs(
            FINAL_INPUT_BLOCKED,
            d_leakage_failures,
            frames,
            input_paths,
            manifests,
            schema_fingerprints=schema_fingerprints,
        )

    events, label_audit, label_failures = prepare_primary_events(
        assignments, canonical, labels, membership, g_segment_catalog, selected_grid
    )
    if "multiple_grid_ids" in ";".join(label_failures):
        frames = empty_frames(input_frame, upstream)
        return write_outputs(
            FINAL_GRID_BLOCKED,
            label_failures,
            frames,
            input_paths,
            manifests,
            schema_fingerprints=schema_fingerprints,
        )
    if label_failures:
        frames = empty_frames(input_frame, upstream)
        frames["transition_context_ablation_label_join_audit"] = label_audit
        return write_outputs(
            FINAL_LABEL_BLOCKED,
            label_failures,
            frames,
            input_paths,
            manifests,
            schema_fingerprints=schema_fingerprints,
        )

    events, asof_meta = e_runner.asof_join_panel(events, panel)
    feature_contract, feature_sets = build_feature_contract(
        events,
        h_contract,
        path_hash(input_paths["g_event_assignment"]),
        path_hash(input_paths["cross_section_feature_panel"]),
    )
    leakage_audit, leakage_failures = build_leakage_audit(feature_contract, feature_sets)
    if asof_meta.get("future_join_row_count", 0):
        leakage_failures.append("daily_panel_asof_join_future_rows")
    if leakage_failures:
        frames = empty_frames(input_frame, upstream)
        frames.update(
            {
                "transition_context_ablation_feature_contract": feature_contract,
                "transition_context_ablation_leakage_audit": leakage_audit,
                "transition_context_ablation_label_join_audit": label_audit,
            }
        )
        future_failures = [
            reason
            for reason in leakage_failures
            if reason.startswith("future_feature_used:") or reason.startswith("forbidden_future_feature_used:")
        ]
        blocked_decision = FINAL_FUTURE_BLOCKED if future_failures else FINAL_LEAKAGE_BLOCKED
        return write_outputs(
            blocked_decision,
            leakage_failures,
            frames,
            input_paths,
            manifests,
            feature_sets,
            schema_fingerprints=schema_fingerprints,
        )

    training = build_training_universe_audit(events)
    scores_list: list[pd.DataFrame] = []
    registry_list: list[pd.DataFrame] = []
    oos_list: list[pd.DataFrame] = []
    preprocessing_hashes: dict[str, str] = {}
    for model_id, feature_cols in arm_feature_map(feature_sets).items():
        score, registry, oos, preprocessing = fit_model_arm(events, model_id, feature_cols, training)
        scores_list.append(score)
        registry_list.append(registry)
        oos_list.append(oos)
        preprocessing_hashes[model_id] = stable_hash(preprocessing)
    scores = pd.concat(scores_list, ignore_index=True, sort=False)
    registry = pd.concat(registry_list, ignore_index=True, sort=False)
    oos = pd.concat(oos_list, ignore_index=True, sort=False)
    stability, cv_uplift = run_segment_cv(events, feature_sets)
    frontier, selected = build_threshold_frontier(events, scores, membership)
    if not frontier.empty:
        selected_ids = set(selected.loc[selected["selection_status"].eq("train_selected"), "threshold_id"].astype(str))
        frontier["selected_model_threshold_flag"] = frontier["threshold_id"].astype(str).isin(selected_ids)
    selected_events, rejected_events = build_selected_event_tables(events, scores, selected)
    cost = build_cost_quality_readout(events, scores, selected)
    recall = build_recall_retention_readout(events, membership, scores, selected)
    density = build_density_overlap_readout(events, scores, selected)
    concentration = build_segment_concentration_audit(events, membership, scores, selected)
    outcome = build_outcome_readout(events, scores, selected)
    uplift = build_uplift_comparison(oos, selected, cost, recall, concentration, stability)
    decision, failures = decide(selected, oos, uplift, training, concentration, outcome, stability)
    frames = {
        "transition_context_ablation_input_audit": input_frame,
        "transition_context_ablation_upstream_binding_audit": upstream,
        "transition_context_ablation_feature_contract": feature_contract,
        "transition_context_ablation_leakage_audit": leakage_audit,
        "transition_context_ablation_label_join_audit": label_audit,
        "transition_context_ablation_training_universe_audit": training,
        "transition_context_ablation_model_registry": registry,
        "transition_context_ablation_segment_grouped_stability": stability,
        "transition_context_ablation_segment_grouped_uplift": cv_uplift,
        "transition_context_ablation_oos_separability": oos,
        "transition_context_ablation_threshold_frontier": frontier,
        "transition_context_ablation_selected_threshold_readout": selected,
        "transition_context_ablation_cost_quality_readout": cost,
        "transition_context_ablation_recall_retention_readout": recall,
        "transition_context_ablation_density_overlap_readout": density,
        "transition_context_ablation_segment_concentration_audit": concentration,
        "transition_context_ablation_outcome_readout": outcome,
        "transition_context_ablation_uplift_comparison": uplift,
        "transition_context_ablation_event_scores": scores,
        "transition_context_ablation_selected_events": selected_events,
        "transition_context_ablation_rejected_events": rejected_events,
    }
    return write_outputs(
        decision,
        failures,
        frames,
        input_paths,
        manifests,
        feature_sets,
        preprocessing_hashes,
        schema_fingerprints,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
