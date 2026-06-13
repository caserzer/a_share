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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402

import run_density_fast_fail_audit as density_audit  # noqa: E402
import run_risk_on_post_filter_cost_rejector as e_runner  # noqa: E402


REQUIREMENT_PATH = (
    EXPERIMENT_DIR / "requirement_experiment_h_risk_on_cost_rejector_research_entry_hardening.md"
)
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

A_TABLE_DIR = TABLE_DIR / "density_fast_fail_audit"
A_REPORT_DIR = REPORT_DIR / "density_fast_fail_audit"
A_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"
D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"
E_TABLE_DIR = TABLE_DIR / "risk_on_post_filter_cost_rejector"
E_MANIFEST_DIR = MANIFEST_DIR / "risk_on_post_filter_cost_rejector"

H_TABLE_DIR = TABLE_DIR / "risk_on_cost_rejector_research_entry_hardening"
H_REPORT_DIR = REPORT_DIR / "risk_on_cost_rejector_research_entry_hardening"
H_MANIFEST_DIR = MANIFEST_DIR / "risk_on_cost_rejector_research_entry_hardening"
H_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "risk_on_cost_rejector_research_entry_hardening"

FINAL_RESEARCH = "risk_on_cost_rejector_research_entry_candidate_supported"
FINAL_RESEARCH_CAVEATED = "risk_on_cost_rejector_research_entry_candidate_source_caveated_supported"
FINAL_FEATURE = "risk_on_cost_rejector_feature_source_supported"
FINAL_FEATURE_CAVEATED = "risk_on_cost_rejector_feature_source_caveated_supported"
FINAL_DIAGNOSTIC = "risk_on_cost_rejector_diagnostic_only_or_no_candidate"

BLOCKED_E_SOURCE = "risk_on_research_entry_hardening_e_source_blocked"
BLOCKED_E_HASH = "risk_on_research_entry_hardening_e_artifact_hash_blocked"
BLOCKED_REPLAY = "risk_on_research_entry_hardening_replay_binding_blocked"
BLOCKED_DENOMINATOR = "risk_on_research_entry_hardening_denominator_binding_blocked"
BLOCKED_DENSITY_CONFIG = "risk_on_research_entry_hardening_density_config_blocked"
BLOCKED_FEATURE_COVERAGE = "risk_on_research_entry_hardening_feature_coverage_blocked"
BLOCKED_ASOF = "risk_on_research_entry_hardening_feature_asof_leakage_blocked"
BLOCKED_TRANSITION = "risk_on_research_entry_hardening_transition_scope_leakage_blocked"
BLOCKED_CHERRYPICK = "risk_on_research_entry_hardening_threshold_cherrypick_blocked"
FAILURE_TRAIN_THRESHOLD = "risk_on_research_entry_hardening_train_threshold_not_found"
FAILURE_DENSITY_CAP = "density_or_concentration_cap_failed"

EXACT_E_DECISION = "risk_on_cost_rejector_feature_source_caveated_supported"
STRONGER_E_DECISIONS = {
    "risk_on_cost_rejector_research_entry_candidate_supported",
    "risk_on_cost_rejector_research_entry_candidate_source_caveated_supported",
}
PRIMARY_SOURCE_POOL = "08_R_core_event_regime_gated"
DIAGNOSTIC_SOURCE_POOLS = ("08_R6_event_regime_gated",)
H_SOURCE_POOLS = (PRIMARY_SOURCE_POOL, *DIAGNOSTIC_SOURCE_POOLS)
PRIMARY_MODEL_ID = "supervised_joint_cost_rejector"
PRIMARY_TARGET = "cost_bad_10_20"
PRIMARY_MODEL_TYPE = "logistic_regression_balanced_l2"
TARGET_REGIME = e_runner.TARGET_REGIME
HEADLINE_WINDOW = e_runner.HEADLINE_WINDOW
HEADLINE_POLICY = e_runner.HEADLINE_POLICY
SPLITS = e_runner.SPLITS

DROP_FEATURES = ("momentum_percentile_20d_lag20",)
H_EVENT_FEATURE_COLUMNS = [
    col for col in e_runner.EVENT_FEATURE_COLUMNS if col not in set(DROP_FEATURES)
]
H_PANEL_FEATURE_COLUMNS = list(e_runner.PANEL_FEATURE_COLUMNS)
H_KEEP_FRACTIONS = (0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70)
H_CONFIG: dict[str, Any] = {
    "experiment_id": "08_experiment_h_risk_on_cost_rejector_research_entry_hardening",
    "target_regime": TARGET_REGIME,
    "primary_source_pool": PRIMARY_SOURCE_POOL,
    "primary_model_id": PRIMARY_MODEL_ID,
    "primary_target_label": PRIMARY_TARGET,
    "feature_fix_policy": "drop_low_coverage_lag20",
    "threshold_grid": list(H_KEEP_FRACTIONS),
    "density_caps": {
        "formal_event_day_density_max": 7.50,
        "p95_density_max": 20.00,
        "rolling_10d_executable_event_day_density_max": 1.80,
        "rolling_20d_executable_event_day_density_max": 2.20,
        "family_concentration_max": 0.30,
        "board_concentration_max": 0.85,
    },
    "threshold_selection_policy": "train_constrained_lowest_keep_fraction_then_robustness_gate_replay",
    "validation_policy": "diagnostic_only_no_threshold_tuning",
}
DENSITY_CAP_METRIC_MAP = {
    "formal_event_day_density_max": "formal_event_day_density",
    "p95_density_max": "p95_density",
    "rolling_10d_executable_event_day_density_max": "rolling_10d_executable_event_day_density",
    "rolling_20d_executable_event_day_density_max": "rolling_20d_executable_event_day_density",
    "family_concentration_max": "family_concentration",
    "board_concentration_max": "board_concentration",
}
THRESHOLD_SUFFIX = {
    0.85: "keep_0850",
    0.825: "keep_0825",
    0.80: "keep_0800",
    0.775: "keep_0775",
    0.75: "keep_0750",
    0.725: "keep_0725",
    0.70: "keep_0700",
}
E_BASELINE_THRESHOLD_IDS = (
    "supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080",
    "supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_075",
)
REQUIRED_E_ARTIFACT_KEYS = (
    "risk_on_cost_rejector_feature_contract",
    "risk_on_cost_rejector_model_registry",
    "risk_on_cost_rejector_oos_separability",
    "risk_on_cost_rejector_threshold_frontier",
    "risk_on_cost_rejector_cost_readout",
    "risk_on_cost_rejector_post_filter_retention_by_split",
    "risk_on_cost_rejector_e1_missed_retention",
    "risk_on_cost_rejector_density_readout",
    "risk_on_cost_rejector_event_scores",
    "risk_on_cost_rejector_selected_events",
    "risk_on_cost_rejector_rejected_events",
)


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
    InputSpec("experiment_e_manifest", E_MANIFEST_DIR / "risk_on_post_filter_cost_rejector_manifest.json"),
    InputSpec("density_fast_fail_contract", A_REPORT_DIR / "density_fast_fail_caliber_contract.md"),
    InputSpec("candidate_scope_mapping_contract", A_TABLE_DIR / "candidate_scope_mapping_contract.csv"),
    InputSpec("candidate_scope_reconstructability_audit", A_TABLE_DIR / "candidate_scope_reconstructability_audit.csv"),
    InputSpec("candidate_10d_density_summary", A_TABLE_DIR / "candidate_10d_density_summary.csv"),
    InputSpec("candidate_family_canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("candidate_family_event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec("candidate_family_event_labels", LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet"),
    InputSpec("cross_section_feature_panel", LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet"),
    InputSpec("d_membership", D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet"),
    InputSpec("d_scope_retention", D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv"),
    InputSpec("d_label_leakage_audit", D_TABLE_DIR / "post_replay_label_leakage_audit.csv"),
    *[
        InputSpec(
            f"e_{key}",
            E_TABLE_DIR
            / {
                "risk_on_cost_rejector_event_scores": "risk_on_cost_rejector_event_scores.csv.gz",
                "risk_on_cost_rejector_selected_events": "risk_on_cost_rejector_selected_events.csv.gz",
                "risk_on_cost_rejector_rejected_events": "risk_on_cost_rejector_rejected_events.csv.gz",
            }.get(key, f"{key}.csv"),
        )
        for key in REQUIRED_E_ARTIFACT_KEYS
    ],
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment H risk-on cost rejector research-entry hardening."
    )
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (H_TABLE_DIR, H_REPORT_DIR, H_MANIFEST_DIR, H_LOCAL_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def row_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    if path.suffix == ".parquet":
        return int(len(pd.read_parquet(path)))
    if path.suffix in {".json", ".md"}:
        return 1
    if path.name.endswith(".csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    return max(sum(1 for _ in path.open("rb")) - 1, 0)


def dataframe_schema_fingerprint(frame: pd.DataFrame) -> str:
    return stable_hash(
        [
            {"column": str(column), "dtype": str(frame[column].dtype)}
            for column in frame.columns
        ]
    )


def table_schema_fingerprint(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix == ".parquet":
        return dataframe_schema_fingerprint(pd.read_parquet(path))
    if path.suffix == ".csv" or path.name.endswith(".csv.gz"):
        try:
            return dataframe_schema_fingerprint(pd.read_csv(path, nrows=1000, low_memory=False))
        except pd.errors.EmptyDataError:
            return stable_hash([])
    return stable_hash({"path_suffix": path.suffix, "schema": "non_tabular_artifact"})


def input_artifact_metadata(input_paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "path": str(path),
            "sha256": path_hash(path),
            "row_count": row_count(path),
            "schema_fingerprint": table_schema_fingerprint(path),
        }
        for key, path in sorted(input_paths.items())
    }


def event_level_output_metadata(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    event_keys = (
        "risk_on_hardening_event_scores",
        "risk_on_hardening_selected_events",
        "risk_on_hardening_rejected_events",
    )
    rows: dict[str, dict[str, Any]] = {}
    for key in event_keys:
        path = paths[key]
        rows[key] = {
            "path": str(path),
            "compressed_sha256": path_hash(path),
            "uncompressed_row_count": row_count(path),
            "schema_fingerprint": table_schema_fingerprint(path),
        }
    return rows


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return e_runner.bool_series(frame, column)


def safe_div(num: float | int, den: float | int) -> float:
    return e_runner.safe_div(num, den)


def relative_reduction(before: float, after: float) -> float:
    return e_runner.relative_reduction(before, after)


def output_paths() -> dict[str, Path]:
    return {
        "risk_on_hardening_input_audit": H_TABLE_DIR / "risk_on_hardening_input_audit.csv",
        "risk_on_hardening_config_contract": H_TABLE_DIR / "risk_on_hardening_config_contract.csv",
        "risk_on_hardening_e_source_binding_audit": H_TABLE_DIR / "risk_on_hardening_e_source_binding_audit.csv",
        "risk_on_hardening_e_artifact_hash_audit": H_TABLE_DIR / "risk_on_hardening_e_artifact_hash_audit.csv",
        "risk_on_hardening_scope_reconstruction_audit": H_TABLE_DIR / "risk_on_hardening_scope_reconstruction_audit.csv",
        "risk_on_hardening_label_reconciliation_audit": H_TABLE_DIR / "risk_on_hardening_label_reconciliation_audit.csv",
        "risk_on_hardening_asof_join_audit": H_TABLE_DIR / "risk_on_hardening_asof_join_audit.csv",
        "risk_on_hardening_feature_contract": H_TABLE_DIR / "risk_on_hardening_feature_contract.csv",
        "risk_on_hardening_feature_delta_from_e": H_TABLE_DIR / "risk_on_hardening_feature_delta_from_e.csv",
        "risk_on_hardening_model_registry": H_TABLE_DIR / "risk_on_hardening_model_registry.csv",
        "risk_on_hardening_oos_separability": H_TABLE_DIR / "risk_on_hardening_oos_separability.csv",
        "risk_on_hardening_threshold_frontier": H_TABLE_DIR / "risk_on_hardening_threshold_frontier.csv",
        "risk_on_hardening_selected_threshold_readout": H_TABLE_DIR / "risk_on_hardening_selected_threshold_readout.csv",
        "risk_on_hardening_metric_denominator_audit": H_TABLE_DIR / "risk_on_hardening_metric_denominator_audit.csv",
        "risk_on_hardening_cost_readout": H_TABLE_DIR / "risk_on_hardening_cost_readout.csv",
        "risk_on_hardening_post_filter_retention_by_split": H_TABLE_DIR / "risk_on_hardening_post_filter_retention_by_split.csv",
        "risk_on_hardening_e1_missed_retention": H_TABLE_DIR / "risk_on_hardening_e1_missed_retention.csv",
        "risk_on_hardening_density_readout": H_TABLE_DIR / "risk_on_hardening_density_readout.csv",
        "risk_on_hardening_oracle_gap_audit": H_TABLE_DIR / "risk_on_hardening_oracle_gap_audit.csv",
        "risk_on_hardening_research_entry_gate_replay": H_TABLE_DIR / "risk_on_hardening_research_entry_gate_replay.csv",
        "risk_on_hardening_decision_tiers": H_TABLE_DIR / "risk_on_hardening_decision_tiers.csv",
        "risk_on_hardening_event_scores": H_TABLE_DIR / "risk_on_hardening_event_scores.csv.gz",
        "risk_on_hardening_selected_events": H_TABLE_DIR / "risk_on_hardening_selected_events.csv.gz",
        "risk_on_hardening_rejected_events": H_TABLE_DIR / "risk_on_hardening_rejected_events.csv.gz",
        "risk_on_cost_rejector_research_entry_hardening_report": H_REPORT_DIR
        / "risk_on_cost_rejector_research_entry_hardening_report.md",
        "risk_on_cost_rejector_research_entry_hardening_contract": H_REPORT_DIR
        / "risk_on_cost_rejector_research_entry_hardening_contract.md",
        "risk_on_cost_rejector_research_entry_hardening_manifest": H_MANIFEST_DIR
        / "risk_on_cost_rejector_research_entry_hardening_manifest.json",
    }


def input_audit() -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    paths: dict[str, Path] = {}
    for spec in INPUT_SPECS:
        paths[spec.input_id] = spec.path
        exists = spec.path.exists()
        status = "available" if exists else "missing_required_input"
        if spec.required and not exists:
            failures.append(f"missing_required_input:{spec.input_id}:{spec.path}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "status": status,
                "sha256": path_hash(spec.path),
                "row_count": row_count(spec.path),
            }
        )
    return pd.DataFrame(rows), failures, paths


def build_config_contract() -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    caps = H_CONFIG.get("density_caps", {})
    for key, value in H_CONFIG.items():
        if key == "density_caps":
            continue
        rows.append(
            {
                "config_key": key,
                "config_value": json.dumps(value, ensure_ascii=False, sort_keys=True),
                "config_status": "declared",
            }
        )
    required_caps = set(DENSITY_CAP_METRIC_MAP)
    missing_caps = sorted(required_caps - set(caps))
    for cap_key in sorted(required_caps):
        rows.append(
            {
                "config_key": f"density_caps.{cap_key}",
                "metric_column": DENSITY_CAP_METRIC_MAP[cap_key],
                "config_value": "" if cap_key not in caps else str(caps[cap_key]),
                "config_status": "declared" if cap_key in caps else "missing_required_cap",
            }
        )
    if missing_caps:
        failures.extend(f"missing_density_cap:{cap}" for cap in missing_caps)
    rows.append(
        {
            "config_key": "h_config_hash",
            "config_value": stable_hash(H_CONFIG),
            "config_status": "hash_recorded",
        }
    )
    return pd.DataFrame(rows), failures


def validate_e_manifest(e_manifest: dict[str, Any]) -> tuple[pd.DataFrame, list[str], bool]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    source_caveated = bool(e_manifest.get("source_caveated", False))
    required = {
        "selected_candidate_tier": "research_entry",
        "selected_source_pool": PRIMARY_SOURCE_POOL,
        "selected_model_id": PRIMARY_MODEL_ID,
        "selected_threshold_id": "supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080",
        "source_caveated": True,
    }
    decision = str(e_manifest.get("decision", ""))
    if decision == EXACT_E_DECISION:
        decision_status = "required_exact_decision"
    elif decision in STRONGER_E_DECISIONS:
        decision_status = "stronger_than_required"
    else:
        decision_status = "unsupported_decision"
        failures.append(f"unsupported_e_decision:{decision}")
    rows.append(
        {
            "binding_name": "decision",
            "observed_value": decision,
            "required_value": EXACT_E_DECISION,
            "binding_status": decision_status,
        }
    )
    for field, value in required.items():
        observed = e_manifest.get(field)
        status = "pass" if observed == value else "fail"
        if status != "pass":
            failures.append(f"e_manifest_binding_mismatch:{field}:{observed}:{value}")
        rows.append(
            {
                "binding_name": field,
                "observed_value": observed,
                "required_value": value,
                "binding_status": status,
            }
        )
    rows.append(
        {
            "binding_name": "e_decision_binding_status",
            "observed_value": decision_status,
            "required_value": "required_exact_decision_or_stronger_than_required",
            "binding_status": "pass" if decision_status != "unsupported_decision" else "fail",
        }
    )
    return pd.DataFrame(rows), failures, source_caveated


def validate_e_artifact_hashes(e_manifest: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    output_hashes = e_manifest.get("output_hashes", {}) or {}
    output_path_map = e_manifest.get("output_paths", {}) or {}
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for key in REQUIRED_E_ARTIFACT_KEYS:
        expected_hash = str(output_hashes.get(key, ""))
        path = Path(str(output_path_map.get(key, "")))
        if not path.exists():
            fallback = E_TABLE_DIR / {
                "risk_on_cost_rejector_event_scores": "risk_on_cost_rejector_event_scores.csv.gz",
                "risk_on_cost_rejector_selected_events": "risk_on_cost_rejector_selected_events.csv.gz",
                "risk_on_cost_rejector_rejected_events": "risk_on_cost_rejector_rejected_events.csv.gz",
            }.get(key, f"{key}.csv")
            path = fallback
        actual_hash = path_hash(path)
        status = "pass" if expected_hash and actual_hash == expected_hash else "hash_mismatch_or_missing"
        if status != "pass":
            failures.append(f"e_artifact_hash_mismatch:{key}")
        rows.append(
            {
                "artifact_key": key,
                "path": str(path),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "hash_status": status,
            }
        )
    return pd.DataFrame(rows), failures


def validate_upstream_manifests() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    a, b, c, d, manifest_failures = e_runner.validate_manifests()
    e_manifest = read_json(E_MANIFEST_DIR / "risk_on_post_filter_cost_rejector_manifest.json")
    return a, b, c, d, e_manifest, manifest_failures


def reconstruct_h_scope_events(
    canonical08: pd.DataFrame,
    mapping: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    empty07 = pd.DataFrame()
    return {
        scope_id: e_runner.reconstruct_scope_events(scope_id, empty07, canonical08, mapping)
        for scope_id in H_SOURCE_POOLS
    }


def build_h_scope_reconstruction_audit(
    scope_events: dict[str, pd.DataFrame],
    mapping: pd.DataFrame,
    reconstruct: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for scope_id in H_SOURCE_POOLS:
        map_row = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
        rec_row = reconstruct.loc[reconstruct["candidate_scope_id"].astype(str).eq(scope_id)]
        frame = scope_events.get(scope_id, pd.DataFrame())
        source_row_count = int(rec_row.iloc[0].get("source_row_count", 0)) if not rec_row.empty else 0
        published_ref = int(rec_row.iloc[0].get("published_reference_event_count", 0)) if not rec_row.empty else 0
        diff = int(rec_row.iloc[0].get("reconstructed_vs_published_count_difference", 0)) if not rec_row.empty else 0
        status = "pass"
        accepted_reason = ""
        if rec_row.empty or map_row.empty:
            status = "scope_mapping_missing"
            failures.append(f"scope_mapping_missing:{scope_id}")
        elif len(frame) != source_row_count:
            status = "source_row_count_drift"
            failures.append(
                f"scope_binding_drift:{scope_id}:expected_source_row_count={source_row_count}:actual={len(frame)}"
            )
        elif scope_id == PRIMARY_SOURCE_POOL and source_row_count == 47914 and published_ref == 47929 and diff == -15:
            accepted_reason = "A_audit_accepted_R_core_minus_15_published_reference_difference"
        rows.append(
            {
                "source_pool": scope_id,
                "scope_mapping_status": "" if map_row.empty else str(map_row.iloc[0].get("scope_mapping_status", "")),
                "scope_status": "" if rec_row.empty else str(rec_row.iloc[0].get("scope_status", "")),
                "source_row_filter": "" if map_row.empty else str(map_row.iloc[0].get("source_row_filter", "")),
                "source_hash": "" if map_row.empty else str(map_row.iloc[0].get("source_artifact_hash", "")),
                "reconstructed_event_count": int(len(frame)),
                "source_row_count": source_row_count,
                "published_reference_event_count": published_ref,
                "reconstructed_vs_published_count_difference": diff,
                "accepted_difference_reason": accepted_reason,
                "scope_reconstruction_status": status,
            }
        )
    return pd.DataFrame(rows), failures


def label_leakage_pass(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = read_csv(path)
    failures: list[str] = []
    status_cols = [col for col in frame.columns if col.endswith("_status") or col.endswith("status")]
    if status_cols:
        failed = pd.Series(False, index=frame.index)
        for col in status_cols:
            failed |= frame[col].astype(str).str.contains("fail|blocked|leak", case=False, na=False)
        if bool(failed.any()):
            failures.append("d_label_leakage_audit_not_pass")
    return frame, failures


def asof_join_audit(events: pd.DataFrame, asof_meta: dict[str, Any], panel_hash: str) -> pd.DataFrame:
    max_lag = float(pd.to_numeric(events.get("feature_lag_days"), errors="coerce").max()) if "feature_lag_days" in events.columns else np.nan
    min_lag = float(pd.to_numeric(events.get("feature_lag_days"), errors="coerce").min()) if "feature_lag_days" in events.columns else np.nan
    return pd.DataFrame(
        [
            {
                "feature_join_policy": asof_meta.get("feature_join_policy", ""),
                "feature_join_key": asof_meta.get("feature_join_key", ""),
                "joined_row_count": asof_meta.get("joined_row_count", 0),
                "missing_row_count": asof_meta.get("missing_row_count", 0),
                "future_join_row_count": asof_meta.get("future_join_row_count", 0),
                "min_feature_lag_days": min_lag,
                "max_feature_lag_days": max_lag,
                "panel_feature_columns": ";".join(asof_meta.get("panel_feature_columns", [])),
                "source_panel_hash": panel_hash,
                "asof_join_status": "pass" if asof_meta.get("future_join_row_count", 0) == 0 else "future_join_blocked",
            }
        ]
    )


def feature_contract_row(
    feature_name: str,
    source_kind: str,
    join_key: str,
    asof_policy: str,
    source_hash: str,
    events: pd.DataFrame,
    *,
    allowed: bool = True,
    blocked_reason: str = "",
) -> dict[str, Any]:
    row = e_runner.feature_contract_row(feature_name, source_kind, join_key, asof_policy, source_hash, events)
    row["allowed_as_t0_feature"] = allowed
    row["blocked_reason"] = blocked_reason
    return row


def build_h_feature_contract(
    events: pd.DataFrame,
    event_source_hash: str,
    panel_hash: str,
    asof_meta: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for col in H_EVENT_FEATURE_COLUMNS:
        if col in events.columns:
            rows.append(feature_contract_row(col, "event_envelope", "event_id", "event_t0_date", event_source_hash, events))
    for col in DROP_FEATURES:
        if col in events.columns:
            rows.append(
                feature_contract_row(
                    col,
                    "event_envelope",
                    "event_id",
                    "event_t0_date",
                    event_source_hash,
                    events,
                    allowed=False,
                    blocked_reason="dropped_by_feature_fix_policy_low_coverage_lag20",
                )
            )
    for col in asof_meta.get("panel_feature_columns", []):
        feature_name = f"panel_{col}"
        rows.append(
            feature_contract_row(
                feature_name,
                "cross_section_feature_panel",
                "instrument",
                "latest_same_or_prior_event_t0_date",
                panel_hash,
                events,
            )
        )
    for col in e_runner.CATEGORICAL_FEATURE_COLUMNS:
        if col in events.columns:
            rows.append(feature_contract_row(col, "event_envelope", "event_id", "event_t0_date", event_source_hash, events))
    for col in ["failure_10_label", "event_false_repair_20d_label", "event_big_winner_120d_label", "target_episode_id"]:
        rows.append(
            {
                "feature_name": col,
                "source_artifact": "label_or_episode_source",
                "source_hash": "",
                "as_of_policy": "future_or_membership_field_not_t0_feature",
                "source_kind": "blocked",
                "feature_join_key": "",
                "feature_as_of_date_policy": "",
                "max_feature_as_of_date_minus_event_t0_date": np.nan,
                "uses_future_information": True,
                "allowed_as_t0_feature": False,
                "missing_rate_train": np.nan,
                "missing_rate_validation": np.nan,
                "missing_rate_robustness": np.nan,
                "blocked_reason": "not_allowed_as_t0_feature",
            }
        )
    return pd.DataFrame(rows)


def feature_input_columns(events: pd.DataFrame) -> list[str]:
    cols = [col for col in H_EVENT_FEATURE_COLUMNS if col in events.columns]
    cols += [f"panel_{col}" for col in H_PANEL_FEATURE_COLUMNS if f"panel_{col}" in events.columns]
    cols += [col for col in e_runner.CATEGORICAL_FEATURE_COLUMNS if col in events.columns]
    return cols


def numeric_feature_columns(events: pd.DataFrame) -> list[str]:
    cols = [col for col in H_EVENT_FEATURE_COLUMNS if col in events.columns]
    cols += [f"panel_{col}" for col in H_PANEL_FEATURE_COLUMNS if f"panel_{col}" in events.columns]
    return cols


def feature_missing_coverage(events: pd.DataFrame, mask: pd.Series) -> float:
    cols = feature_input_columns(events)
    if not cols or not bool(mask.any()):
        return np.nan
    missing_rate = events.loc[mask, cols].isna().mean().mean()
    return float(1.0 - missing_rate)


def build_design_matrix(events: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    numeric_cols = numeric_feature_columns(events)
    numeric_raw = events[numeric_cols].apply(pd.to_numeric, errors="coerce") if numeric_cols else pd.DataFrame(index=events.index)
    numeric, numeric_meta = e_runner.preprocess_numeric_features(numeric_raw, train_mask)
    categorical_cols = [col for col in e_runner.CATEGORICAL_FEATURE_COLUMNS if col in events.columns]
    cat, cat_meta = e_runner.build_categorical_matrix(events, categorical_cols, train_mask)
    train_columns = list(numeric.columns) + list(cat.columns)
    matrix = pd.concat([numeric, cat], axis=1)
    matrix = matrix.reindex(columns=train_columns, fill_value=0.0).astype(float)
    preprocessing = {
        "policy": e_runner.FEATURE_PREPROCESSING_POLICY,
        "feature_fix_policy": H_CONFIG["feature_fix_policy"],
        "dropped_features": list(DROP_FEATURES),
        "numeric": numeric_meta,
        "categorical": cat_meta,
    }
    return matrix, train_columns, preprocessing


def fit_primary_model(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group = events.loc[events["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)].copy().reset_index(drop=True)
    train_mask = group["event_split"].astype(str).eq("train") & group["horizon_complete"]
    matrix, feature_columns, preprocessing = build_design_matrix(group, train_mask)
    y_train = group.loc[train_mask, PRIMARY_TARGET].astype(int)
    status = "trained"
    if len(y_train) < 30 or y_train.nunique() < 2:
        status = "blocked_insufficient_train_label_variation"
        scores = np.full(len(group), np.nan)
    else:
        model = LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
        model.fit(matrix.loc[train_mask], y_train)
        scores = model.predict_proba(matrix)[:, 1]
    score = group[
        [
            "source_pool",
            "event_id",
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "event_regime_bucket",
            "board_bucket",
            "primary_family_id",
            "horizon_complete",
            "fast_fail_bad_10d",
            "false_repair_bad_20d",
            "cost_bad_10_20",
        ]
    ].copy()
    score["model_id"] = PRIMARY_MODEL_ID
    score["target_label"] = PRIMARY_TARGET
    score["cost_bad_score"] = scores
    model_registry = pd.DataFrame(
        [
            {
                "model_id": PRIMARY_MODEL_ID,
                "source_pool": PRIMARY_SOURCE_POOL,
                "target_label": PRIMARY_TARGET,
                "model_type": PRIMARY_MODEL_TYPE,
                "model_status": status,
                "train_sample_n": int(train_mask.sum()),
                "train_positive_n": int(y_train.sum()) if len(y_train) else 0,
                "feature_count": len(feature_columns),
                "feature_columns_hash": stable_hash(feature_columns),
                "feature_preprocessing_policy": e_runner.FEATURE_PREPROCESSING_POLICY,
                "feature_preprocessing_hash": stable_hash(preprocessing),
                "feature_fix_policy": H_CONFIG["feature_fix_policy"],
                "dropped_features": ";".join(DROP_FEATURES),
            }
        ]
    )
    oos_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_mask = group["event_split"].astype(str).eq(split) & group["horizon_complete"]
        y = group.loc[split_mask, PRIMARY_TARGET].astype(int)
        s = pd.Series(scores, index=group.index).loc[split_mask]
        oos_rows.append(
            e_runner.separability_row(
                PRIMARY_MODEL_ID,
                PRIMARY_SOURCE_POOL,
                PRIMARY_TARGET,
                split,
                y,
                s,
                feature_missing_coverage(group, split_mask),
            )
        )
    return score, model_registry, pd.DataFrame(oos_rows)


def threshold_id_for_keep_fraction(keep_fraction: float) -> str:
    suffix = THRESHOLD_SUFFIX.get(float(keep_fraction))
    if suffix is None:
        suffix = f"keep_{int(round(float(keep_fraction) * 1000)):04d}"
    return f"{PRIMARY_MODEL_ID}__{PRIMARY_SOURCE_POOL}__{suffix}"


def build_threshold_frontier(
    events: pd.DataFrame,
    scores: pd.DataFrame,
    membership: pd.DataFrame,
    d_scope: pd.DataFrame,
) -> pd.DataFrame:
    source_events = events.loc[events["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)].copy()
    score_group = scores.loc[
        scores["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)
        & scores["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
    ].copy()
    train_scores = score_group.loc[
        score_group["event_split"].astype(str).eq("train")
        & score_group["horizon_complete"]
        & score_group["cost_bad_score"].notna(),
        "cost_bad_score",
    ]
    rows: list[dict[str, Any]] = []
    if train_scores.empty:
        return pd.DataFrame()
    for keep_fraction in H_KEEP_FRACTIONS:
        threshold = float(train_scores.quantile(keep_fraction))
        selected_ids = set(score_group.loc[score_group["cost_bad_score"] <= threshold, "event_id"].astype(str))
        row = e_runner.threshold_metrics(
            source_pool=PRIMARY_SOURCE_POOL,
            model_id=PRIMARY_MODEL_ID,
            threshold_id=threshold_id_for_keep_fraction(keep_fraction),
            threshold_value=threshold,
            keep_fraction=float(keep_fraction),
            source_events=source_events,
            selected_ids=selected_ids,
            membership=membership,
            d_scope=d_scope,
        )
        row["threshold_selection_policy"] = H_CONFIG["threshold_selection_policy"]
        row["selected_model_threshold_flag"] = False
        rows.append(row)
    return pd.DataFrame(rows)


def train_threshold_eligible(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(False, index=frame.index)
    return (
        frame["train_cost_reduction_relative"].ge(0.15)
        & frame["train_fast_fail_rate_after"].le(frame["train_fast_fail_rate_before"])
        & frame["train_false_repair_rate_after"].le(frame["train_false_repair_rate_before"])
        & frame["train_any_recall_retention"].ge(0.90)
        & frame["train_e1_missed_capture_retention"].ge(0.85)
        & frame["train_post_filter_e1_missed_captured_episode_n"].ge(60)
        & frame["after_train_horizon_complete_event_n"].gt(0)
    )


def select_train_threshold(frontier: pd.DataFrame) -> tuple[dict[str, Any], str]:
    if frontier.empty:
        return {}, FAILURE_TRAIN_THRESHOLD
    primary = frontier.loc[
        frontier["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)
        & frontier["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
    ].copy()
    eligible = primary.loc[train_threshold_eligible(primary)].copy()
    if eligible.empty:
        return {}, FAILURE_TRAIN_THRESHOLD
    selected = eligible.sort_values(
        ["keep_fraction", "train_cost_reduction_relative", "threshold_id"],
        ascending=[True, False, True],
    ).iloc[0].to_dict()
    return selected, ""


def build_metric_denominator_audit(events: pd.DataFrame, scores: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if frontier.empty:
        return pd.DataFrame()
    source_events = events.loc[events["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)].copy()
    score_map = scores.loc[
        scores["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)
        & scores["model_id"].astype(str).eq(PRIMARY_MODEL_ID),
        ["event_id", "cost_bad_score"],
    ].drop_duplicates("event_id")
    event_scores = source_events.merge(score_map, on="event_id", how="left")
    for _, threshold in frontier.iterrows():
        threshold_value = float(threshold["threshold_value"])
        threshold_id = str(threshold["threshold_id"])
        selected_mask_all = event_scores["cost_bad_score"].le(threshold_value)
        for split in SPLITS:
            split_mask = event_scores["event_split"].astype(str).eq(split)
            raw = event_scores.loc[split_mask]
            selected = event_scores.loc[split_mask & selected_mask_all]
            rejected = event_scores.loc[split_mask & ~selected_mask_all]
            rows.append(
                {
                    "source_pool": PRIMARY_SOURCE_POOL,
                    "model_id": PRIMARY_MODEL_ID,
                    "threshold_id": threshold_id,
                    "keep_fraction": threshold["keep_fraction"],
                    "split": split,
                    "denominator_policy": "same_source_split_regime_horizon_complete_before_after",
                    "raw_event_n": int(len(raw)),
                    "raw_horizon_complete_n": int(bool_series(raw, "horizon_complete").sum()),
                    "selected_event_n": int(len(selected)),
                    "selected_horizon_complete_n": int(bool_series(selected, "horizon_complete").sum()),
                    "rejected_event_n": int(len(rejected)),
                    "rejected_horizon_complete_n": int(bool_series(rejected, "horizon_complete").sum()),
                    "raw_incomplete_or_censored_n": int((~bool_series(raw, "horizon_complete")).sum()),
                    "selected_incomplete_or_censored_n": int((~bool_series(selected, "horizon_complete")).sum()),
                    "excluded_reason_policy": "incomplete_or_censored_excluded_from_before_and_after_cost_rates",
                    "before_after_denominator_status": "pass",
                }
            )
    return pd.DataFrame(rows)


def build_feature_delta_from_e(e_contract: pd.DataFrame, h_contract: pd.DataFrame) -> pd.DataFrame:
    e_small = e_contract.copy()
    h_small = h_contract.copy()
    cols = ["feature_name", "allowed_as_t0_feature", "missing_rate_train", "missing_rate_validation", "missing_rate_robustness"]
    e_small = e_small[[col for col in cols if col in e_small.columns]].rename(
        columns={
            "allowed_as_t0_feature": "e_allowed_as_t0_feature",
            "missing_rate_train": "e_missing_rate_train",
            "missing_rate_validation": "e_missing_rate_validation",
            "missing_rate_robustness": "e_missing_rate_robustness",
        }
    )
    h_small = h_small[[col for col in cols + ["blocked_reason"] if col in h_small.columns]].rename(
        columns={
            "allowed_as_t0_feature": "h_allowed_as_t0_feature",
            "missing_rate_train": "h_missing_rate_train",
            "missing_rate_validation": "h_missing_rate_validation",
            "missing_rate_robustness": "h_missing_rate_robustness",
            "blocked_reason": "h_blocked_reason",
        }
    )
    out = e_small.merge(h_small, on="feature_name", how="outer")
    out["feature_delta_action"] = np.where(
        out["feature_name"].isin(DROP_FEATURES),
        "dropped_by_h_primary_policy",
        np.where(out["e_allowed_as_t0_feature"].isna(), "new_in_h", "retained"),
    )
    out["feature_delta_reason"] = np.where(
        out["feature_name"].isin(DROP_FEATURES),
        "E coverage below 95pct on train; H primary replay removes this feature before refit",
        "",
    )
    return out


def selected_feature_coverage_ok(feature_contract: pd.DataFrame) -> bool:
    allowed = feature_contract.loc[bool_series(feature_contract, "allowed_as_t0_feature")].copy()
    if allowed.empty:
        return False
    train_missing = pd.to_numeric(allowed["missing_rate_train"], errors="coerce").fillna(0)
    robust_missing = pd.to_numeric(allowed["missing_rate_robustness"], errors="coerce").fillna(0)
    return bool(train_missing.le(0.05).all() and robust_missing.le(0.05).all())


def build_selected_threshold_readout(selected: dict[str, Any], train_failure: str = "") -> pd.DataFrame:
    if not selected:
        return pd.DataFrame(
            [
                {
                    "source_pool": PRIMARY_SOURCE_POOL,
                    "model_id": PRIMARY_MODEL_ID,
                    "threshold_id": "",
                    "selected_keep_fraction": np.nan,
                    "threshold_selection_policy": H_CONFIG["threshold_selection_policy"],
                    "selection_status": "no_train_eligible_threshold",
                    "failure_reason": train_failure,
                }
            ]
        )
    row = dict(selected)
    row["selected_keep_fraction"] = row.get("keep_fraction", np.nan)
    row["selection_status"] = "train_selected"
    row["failure_reason"] = ""
    return pd.DataFrame([row])


def apply_density_caps(density_readout: pd.DataFrame, selected_events: pd.DataFrame, source_events: pd.DataFrame) -> pd.DataFrame:
    if density_readout.empty:
        return density_readout
    out = density_readout.copy()
    caps = H_CONFIG["density_caps"]
    out["rejected_event_count"] = max(int(len(source_events) - len(selected_events)), 0)
    failed: list[str] = []
    for cap_key, metric in DENSITY_CAP_METRIC_MAP.items():
        cap = caps[cap_key]
        value = pd.to_numeric(out.iloc[0].get(metric), errors="coerce")
        out[cap_key] = cap
        out[f"{metric}_cap"] = cap
        out[f"{metric}_cap_pass"] = bool(pd.notna(value) and value <= cap)
        if not bool(out[f"{metric}_cap_pass"].iloc[0]):
            failed.append(metric)
    out["density_readout_status"] = "predeclared_caps_pass" if not failed else "predeclared_caps_failed"
    out["density_cap_failure_metrics"] = ";".join(failed)
    out["density_contract_source_hash"] = path_hash(A_REPORT_DIR / "density_fast_fail_caliber_contract.md")
    return out


def density_caps_pass(density_readout: pd.DataFrame) -> bool:
    if density_readout.empty:
        return False
    pass_cols = [col for col in density_readout.columns if col.endswith("_cap_pass")]
    return bool(pass_cols and density_readout[pass_cols].iloc[0].astype(bool).all())


def empty_event_table_schema() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
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
            "event_regime_bucket",
            "board_bucket",
            "primary_family_id",
            "cost_bad_score",
            "fast_fail_bad_10d",
            "false_repair_bad_20d",
            "cost_bad_10_20",
            "horizon_complete",
        ]
    )


def no_selected_readouts(reason: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = {
        "source_pool": PRIMARY_SOURCE_POOL,
        "model_id": PRIMARY_MODEL_ID,
        "threshold_id": "",
        "readout_status": "not_evaluable_no_selected_threshold",
        "failure_reason": reason,
    }
    cost = pd.DataFrame(
        [
            {
                **base,
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "selected_event_count": 0,
                "rejected_event_count": np.nan,
                "reject_rate": np.nan,
                "before_horizon_complete_event_n": np.nan,
                "after_horizon_complete_event_n": np.nan,
                "cost_reduction_relative": np.nan,
                "denominator_policy": "same_source_split_regime_horizon_complete_before_after",
            }
            for split in SPLITS
        ]
    )
    retention = pd.DataFrame(
        [
            {
                **base,
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "window": HEADLINE_WINDOW,
                "replay_policy_id": HEADLINE_POLICY,
                "post_filter_any_recall_retention": np.nan,
                "post_filter_e1_missed_capture_retention": np.nan,
                "post_filter_e1_missed_captured_episode_n": 0,
            }
            for split in SPLITS
        ]
    )
    e1_missed = pd.DataFrame(
        [
            {
                **base,
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "e1_missed_capture_n_definition": "not_evaluable_no_selected_threshold",
                "post_filter_e1_missed_captured_episode_n": 0,
                "e1_missed_capture_retention": np.nan,
            }
            for split in SPLITS
        ]
    )
    density_row: dict[str, Any] = {
        **base,
        "selected_event_count": 0,
        "rejected_event_count": np.nan,
        "formal_event_day_density": np.nan,
        "p95_density": np.nan,
        "density_vs_e1": np.nan,
        "rolling_10d_executable_event_day_density": np.nan,
        "rolling_20d_executable_event_day_density": np.nan,
        "rolling_10d_duplicate_rate": np.nan,
        "rolling_20d_duplicate_rate": np.nan,
        "adjacent_gap_p10": np.nan,
        "adjacent_gap_median": np.nan,
        "adjacent_gap_p90": np.nan,
        "family_concentration": np.nan,
        "board_concentration": np.nan,
        "density_contract_source_hash": path_hash(A_REPORT_DIR / "density_fast_fail_caliber_contract.md"),
        "density_readout_status": "not_evaluable_no_selected_threshold",
        "density_cap_failure_metrics": "no_selected_threshold",
    }
    for cap_key, metric in DENSITY_CAP_METRIC_MAP.items():
        cap = H_CONFIG["density_caps"][cap_key]
        density_row[cap_key] = cap
        density_row[f"{metric}_cap"] = cap
        density_row[f"{metric}_cap_pass"] = False
    density = pd.DataFrame([density_row])
    return cost, retention, e1_missed, density


def rates_not_worse(selected: dict[str, Any], split: str) -> bool:
    return e_runner.rates_not_worse(selected, split)


def h_selected_oos_status(selected: dict[str, Any], oos: pd.DataFrame) -> dict[str, bool]:
    return e_runner.selected_oos_status(selected, oos)


def decision_from_selected(
    selected: dict[str, Any],
    source_caveated: bool,
    oos: pd.DataFrame,
    feature_contract: pd.DataFrame,
    density_readout: pd.DataFrame,
    train_failure: str = "",
) -> tuple[str, list[str]]:
    if not selected:
        return FINAL_DIAGNOSTIC, [train_failure or FAILURE_TRAIN_THRESHOLD]
    failures: list[str] = []
    train_cost = selected.get("train_cost_reduction_relative", np.nan)
    robust_cost = selected.get("robustness_cost_reduction_relative", np.nan)
    if not (pd.notna(train_cost) and train_cost >= 0.15 and pd.notna(robust_cost) and robust_cost >= 0.15):
        failures.append("cost_reduction_lt_15pct")
    if not rates_not_worse(selected, "train") or not rates_not_worse(selected, "robustness"):
        failures.append("fast_fail_or_false_repair_worse_than_raw")
    if selected.get("train_any_recall_retention", 0) < 0.90 or selected.get("robustness_any_recall_retention", 0) < 0.80:
        failures.append("any_recall_retention_gate_failed")
    if selected.get("train_e1_missed_capture_retention", 0) < 0.85 or selected.get("robustness_e1_missed_capture_retention", 0) < 0.75:
        failures.append("e1_missed_retention_gate_failed")
    if selected.get("robustness_post_filter_e1_missed_captured_episode_n", 0) < 60:
        failures.append("robustness_post_filter_e1_missed_capture_n_lt_60")
    if not h_selected_oos_status(selected, oos)["research_oos_pass"]:
        failures.append("research_oos_separability_gate_failed")
    if not selected_feature_coverage_ok(feature_contract):
        failures.append("feature_coverage_lt_95pct")
    if not density_caps_pass(density_readout):
        failures.append(FAILURE_DENSITY_CAP)
    if not failures:
        return (FINAL_RESEARCH_CAVEATED if source_caveated else FINAL_RESEARCH), []

    feature_failures: list[str] = []
    train_not_worse = pd.notna(train_cost) and train_cost >= 0
    robust_not_worse = pd.notna(robust_cost) and robust_cost >= 0
    feature_cost_pass = (
        (pd.notna(train_cost) and train_cost >= 0.10 and robust_not_worse)
        or (pd.notna(robust_cost) and robust_cost >= 0.10 and train_not_worse)
    )
    if not feature_cost_pass:
        feature_failures.append("feature_cost_reduction_lt_10pct_or_other_split_worse")
    if not h_selected_oos_status(selected, oos)["feature_oos_pass"]:
        feature_failures.append("feature_oos_separability_gate_failed")
    if selected.get("robustness_any_recall_retention", 0) < 0.70:
        feature_failures.append("feature_any_recall_retention_failed")
    if selected.get("robustness_e1_missed_capture_retention", 0) < 0.60:
        feature_failures.append("feature_e1_missed_retention_failed")
    if density_readout.empty:
        feature_failures.append("feature_density_readout_not_auditable")
    if not feature_failures:
        return (FINAL_FEATURE_CAVEATED if source_caveated else FINAL_FEATURE), failures
    return FINAL_DIAGNOSTIC, sorted(set(failures + feature_failures))


def build_gate_replay(selected: dict[str, Any], decision: str, failures: list[str], density_readout: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    gate_checks = {
        "selected_threshold_train_only": bool(selected),
        "train_cost_reduction_ge_15pct": bool(selected and selected.get("train_cost_reduction_relative", 0) >= 0.15),
        "robustness_cost_reduction_ge_15pct": bool(selected and selected.get("robustness_cost_reduction_relative", 0) >= 0.15),
        "train_any_recall_ge_90pct": bool(selected and selected.get("train_any_recall_retention", 0) >= 0.90),
        "robustness_any_recall_ge_80pct": bool(selected and selected.get("robustness_any_recall_retention", 0) >= 0.80),
        "train_e1_missed_retention_ge_85pct": bool(selected and selected.get("train_e1_missed_capture_retention", 0) >= 0.85),
        "robustness_e1_missed_retention_ge_75pct": bool(selected and selected.get("robustness_e1_missed_capture_retention", 0) >= 0.75),
        "robustness_e1_missed_capture_n_ge_60": bool(
            selected and selected.get("robustness_post_filter_e1_missed_captured_episode_n", 0) >= 60
        ),
        "density_caps_pass": density_caps_pass(density_readout),
    }
    for gate, passed in gate_checks.items():
        rows.append(
            {
                "gate_name": gate,
                "gate_status": "pass" if passed else "fail",
                "selected_model_id": selected.get("model_id", ""),
                "selected_threshold_id": selected.get("threshold_id", ""),
                "final_decision": decision,
                "failure_reason": ";".join(failures),
            }
        )
    return pd.DataFrame(rows)


def build_decision_tiers(selected: dict[str, Any], final_decision: str, failures: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_tier": "research_entry",
                "selected_model_id": selected.get("model_id", ""),
                "selected_threshold_id": selected.get("threshold_id", ""),
                "selected_source_pool": selected.get("source_pool", PRIMARY_SOURCE_POOL),
                "final_decision": final_decision,
                "selected_model_threshold_flag": bool(selected),
                "failure_reason": ";".join(failures),
                "supported_usage": "research_entry"
                if "research_entry" in final_decision
                else ("feature_source" if "feature_source" in final_decision else "diagnostic_only"),
            }
        ]
    )


def build_oracle_gap_audit(frontier: pd.DataFrame, selected: dict[str, Any]) -> pd.DataFrame:
    if frontier.empty:
        return pd.DataFrame()
    primary = frontier.copy()
    robust_gate = (
        primary["robustness_cost_reduction_relative"].ge(0.15)
        & primary["robustness_any_recall_retention"].ge(0.80)
        & primary["robustness_e1_missed_capture_retention"].ge(0.75)
        & primary["robustness_post_filter_e1_missed_captured_episode_n"].ge(60)
    )
    oracle_pool = primary.loc[robust_gate].copy()
    oracle_status = "robustness_gate_eligible"
    if oracle_pool.empty:
        oracle_pool = primary.copy()
        oracle_status = "no_robustness_gate_eligible_threshold_use_max_robust_cost_for_gap_only"
    oracle = oracle_pool.sort_values(
        ["robustness_cost_reduction_relative", "robustness_any_recall_retention"],
        ascending=[False, False],
    ).iloc[0]
    return pd.DataFrame(
        [
            {
                "train_selection_status": "train_selected" if selected else "no_train_eligible_threshold",
                "train_selected_threshold_id": selected.get("threshold_id", ""),
                "train_selected_keep_fraction": selected.get("keep_fraction", np.nan),
                "train_selected_train_cost_reduction_relative": selected.get("train_cost_reduction_relative", np.nan),
                "train_selected_robustness_cost_reduction_relative": selected.get("robustness_cost_reduction_relative", np.nan),
                "robustness_best_threshold_id": oracle.get("threshold_id", ""),
                "robustness_best_keep_fraction": oracle.get("keep_fraction", np.nan),
                "robustness_best_robustness_cost_reduction_relative": oracle.get("robustness_cost_reduction_relative", np.nan),
                "robustness_best_robustness_any_recall_retention": oracle.get("robustness_any_recall_retention", np.nan),
                "oracle_status": oracle_status,
                "oracle_allowed_for_final_decision": False,
                "thresholds_differ": (
                    bool(str(selected.get("threshold_id", "")) != str(oracle.get("threshold_id", "")))
                    if selected
                    else np.nan
                ),
            }
        ]
    )


def build_training_summary(events: pd.DataFrame) -> pd.DataFrame:
    primary = events.loc[events["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)].copy()
    rows: list[dict[str, Any]] = []
    for split, group in primary.groupby("event_split", dropna=False):
        complete = group.loc[group["horizon_complete"]]
        rows.append(
            {
                "source_pool": PRIMARY_SOURCE_POOL,
                "split": split,
                "event_n": int(len(group)),
                "cost_label_complete_n": int(len(complete)),
                "cost_label_complete_rate": safe_div(len(complete), len(group)),
                "cost_bad_10_20_rate": safe_div(int(complete["cost_bad_10_20"].sum()), len(complete)) if len(complete) else np.nan,
                "feature_coverage": feature_missing_coverage(group, pd.Series(True, index=group.index)),
            }
        )
    return pd.DataFrame(rows)


def build_report(
    final_decision: str,
    selected: dict[str, Any],
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    source_caveated: bool,
) -> str:
    lines = [
        "# Experiment H - Risk-on Cost Rejector Research-Entry Hardening 报告",
        "",
        f"最终决策：`{final_decision}`",
        "",
        "## 结论",
        "",
        "H 是对 Experiment E 的 research-entry hardening replay，不是新 family、不是 transition extension。"
        "本轮固定 `08_R_core_event_regime_gated + supervised_joint_cost_rejector`，删除 E 中低覆盖的 "
        "`momentum_percentile_20d_lag20` 后重新 fit preprocessing 与 logistic regression，并用预声明 grid 进行 train-only threshold selection。",
        "",
        "H 针对 E 距离 research-entry 最近但尚未完全闭合的三个 admission 缺口："
        "第一，density / concentration gate 必须在 H config 中预声明并写入 manifest；"
        "第二，`momentum_percentile_20d_lag20` 只能二选一处理，本轮选择剔除而不是未来填充；"
        "第三，`keep_0800` / `keep_0775` / `keep_0750` 等阈值必须在同一个 selected threshold 上同时读取 cost 与 recall，禁止从不同 frontier 点 cherry-pick。",
        "",
        f"- source_caveated propagation: `{source_caveated}`",
        f"- feature_fix_policy: `{H_CONFIG['feature_fix_policy']}`",
        f"- threshold_selection_policy: `{H_CONFIG['threshold_selection_policy']}`",
        "",
    ]
    if selected:
        lines.extend(
            [
                "## Selected Threshold",
                "",
                f"- source_pool: `{selected.get('source_pool')}`",
                f"- model_id: `{selected.get('model_id')}`",
                f"- threshold_id: `{selected.get('threshold_id')}`",
                f"- keep_fraction: `{selected.get('keep_fraction')}`",
                f"- train cost reduction: `{selected.get('train_cost_reduction_relative'):.4f}`",
                f"- robustness cost reduction: `{selected.get('robustness_cost_reduction_relative'):.4f}`",
                f"- train any recall retention: `{selected.get('train_any_recall_retention'):.4f}`",
                f"- robustness any recall retention: `{selected.get('robustness_any_recall_retention'):.4f}`",
                f"- robustness E1-missed captured n: `{selected.get('robustness_post_filter_e1_missed_captured_episode_n')}`",
                "",
            ]
        )
    if failures:
        lines.extend(["## Gate Failures", "", *[f"- `{reason}`" for reason in failures], ""])
    feature_delta = frames.get("risk_on_hardening_feature_delta_from_e", pd.DataFrame())
    if not feature_delta.empty:
        dropped = feature_delta.loc[feature_delta["feature_delta_action"].astype(str).eq("dropped_by_h_primary_policy")]
        lines.extend(["## Feature Processing", ""])
        for _, row in dropped.iterrows():
            lines.append(
                f"- dropped `{row['feature_name']}`: E train missing rate "
                f"`{row.get('e_missing_rate_train', np.nan):.4f}`; reason `{row.get('feature_delta_reason', '')}`"
            )
        lines.append("")
    oos = frames.get("risk_on_hardening_oos_separability", pd.DataFrame())
    if not oos.empty:
        lines.extend(["## OOS Separability", ""])
        for _, row in oos.iterrows():
            lines.append(
                f"- {row['split']}: sample `{row['sample_n']}`, prevalence `{row['label_prevalence']:.4f}`, "
                f"ROC-AUC `{row['roc_auc']:.4f}`, PR-AUC `{row['pr_auc']:.4f}`, top-decile lift `{row['top_decile_lift']:.4f}`"
            )
        validation = oos.loc[oos["split"].astype(str).eq("validation")]
        if not validation.empty:
            row = validation.iloc[0]
            lines.append(
                f"- validation 仅作 diagnostic，不参与阈值选择：ROC-AUC `{row['roc_auc']:.4f}`, "
                f"PR-AUC `{row['pr_auc']:.4f}`。"
            )
        lines.append("")
    frontier = frames.get("risk_on_hardening_threshold_frontier", pd.DataFrame())
    if not frontier.empty:
        lines.extend(["## Threshold Frontier", ""])
        for _, row in frontier.iterrows():
            lines.append(
                f"- keep `{row['keep_fraction']:.3f}`: train cost `{row['train_cost_reduction_relative']:.4f}`, "
                f"train any recall `{row['train_any_recall_retention']:.4f}`, "
                f"train E1-missed `{row['train_e1_missed_capture_retention']:.4f}`, "
                f"robustness cost `{row['robustness_cost_reduction_relative']:.4f}`, "
                f"robustness any recall `{row['robustness_any_recall_retention']:.4f}`"
            )
        lines.append("")
    cost = frames.get("risk_on_hardening_cost_readout", pd.DataFrame())
    retention = frames.get("risk_on_hardening_post_filter_retention_by_split", pd.DataFrame())
    if not cost.empty:
        lines.extend(["## Cost / Recall Readout", ""])
        for _, row in cost.iterrows():
            keep = retention.loc[retention["split"].astype(str).eq(str(row["split"]))] if not retention.empty else pd.DataFrame()
            any_ret = keep.iloc[0].get("post_filter_any_recall_retention", np.nan) if not keep.empty else np.nan
            e1_ret = keep.iloc[0].get("post_filter_e1_missed_capture_retention", np.nan) if not keep.empty else np.nan
            lines.append(
                f"- {row['split']}: cost reduction `{row['cost_reduction_relative']:.4f}`, "
                f"raw denominator `{row['before_horizon_complete_event_n']}`, selected denominator `{row['after_horizon_complete_event_n']}`, "
                f"any recall `{any_ret:.4f}`, E1-missed retention `{e1_ret:.4f}`"
            )
        lines.append("")
    denominator = frames.get("risk_on_hardening_metric_denominator_audit", pd.DataFrame())
    if not denominator.empty:
        status_counts = denominator["before_after_denominator_status"].astype(str).value_counts().to_dict()
        lines.extend(
            [
                "## Denominator Audit",
                "",
                "- cost before/after 使用同一 source/split/regime cell 内的 horizon-complete 事件分母；"
                "incomplete 或 censored 事件在 before 与 after 两侧按同一规则排除。",
                f"- audited threshold/split rows: `{len(denominator)}`；status counts: `{status_counts}`",
                "",
            ]
        )
    density = frames.get("risk_on_hardening_density_readout", pd.DataFrame())
    if not density.empty:
        row = density.iloc[0]
        lines.extend(
            [
                "## Density / Concentration",
                "",
                f"- status: `{row.get('density_readout_status', '')}`",
                f"- formal density: `{row.get('formal_event_day_density', np.nan):.4f}` <= `{H_CONFIG['density_caps']['formal_event_day_density_max']}`",
                f"- p95 density: `{row.get('p95_density', np.nan):.4f}` <= `{H_CONFIG['density_caps']['p95_density_max']}`",
                f"- rolling 10d density: `{row.get('rolling_10d_executable_event_day_density', np.nan):.4f}` <= `{H_CONFIG['density_caps']['rolling_10d_executable_event_day_density_max']}`",
                f"- rolling 20d density: `{row.get('rolling_20d_executable_event_day_density', np.nan):.4f}` <= `{H_CONFIG['density_caps']['rolling_20d_executable_event_day_density_max']}`",
                f"- rolling duplicate rate 10d/20d: `{row.get('rolling_10d_duplicate_rate', np.nan):.4f}` / `{row.get('rolling_20d_duplicate_rate', np.nan):.4f}`",
                f"- adjacent gap p10/median/p90: `{row.get('adjacent_gap_p10', np.nan):.4f}` / `{row.get('adjacent_gap_median', np.nan):.4f}` / `{row.get('adjacent_gap_p90', np.nan):.4f}`",
                f"- family concentration: `{row.get('family_concentration', np.nan):.4f}` <= `{H_CONFIG['density_caps']['family_concentration_max']}`",
                f"- board concentration: `{row.get('board_concentration', np.nan):.4f}` <= `{H_CONFIG['density_caps']['board_concentration_max']}`",
                f"- density contract source hash: `{row.get('density_contract_source_hash', '')}`",
                "",
            ]
        )
    oracle = frames.get("risk_on_hardening_oracle_gap_audit", pd.DataFrame())
    if not oracle.empty:
        row = oracle.iloc[0]
        lines.extend(
            [
                "## Oracle Gap Audit",
                "",
                f"- train selection status: `{row.get('train_selection_status', '')}`",
                f"- train-selected threshold: `{row.get('train_selected_threshold_id', '')}`",
                f"- robustness-best diagnostic threshold: `{row.get('robustness_best_threshold_id', '')}`",
                f"- thresholds differ: `{row.get('thresholds_differ', False)}`",
                "- robustness-best 只用于解释 tradeoff，不进入 final decision。",
                "",
            ]
        )
    lines.extend(
        [
            "## Artifact Row Counts",
            "",
            *[f"- `{key}`: {len(frame):,}" for key, frame in frames.items()],
            "",
            "## Non-Claims",
            "",
            "- 本结果不是 direct-entry support。",
            "- 本结果不是 production-ready gate。",
            "- 本结果不是交易策略或组合上线证据。",
            "- transition previous-regime context 未进入 H 的正式训练特征。",
            "",
        ]
    )
    return "\n".join(lines)


def build_contract() -> str:
    return "\n".join(
        [
            "# Risk-on Cost Rejector Research-Entry Hardening Contract",
            "",
            "- H replays E's primary `08_R_core_event_regime_gated + supervised_joint_cost_rejector` only.",
            "- `momentum_percentile_20d_lag20` is dropped before preprocessing and model fit.",
            "- Daily panel features use latest `panel.date <= event_t0_date` by instrument.",
            "- Cost before/after denominators use the same horizon-complete raw source cell.",
            "- Threshold selection is train-only over `[0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]`.",
            "- H threshold ids use four-digit keep suffixes such as `keep_0800`.",
            "- Robustness-best threshold is diagnostic only.",
            "- Density caps are predeclared in H config and are not tuned from H output.",
            "- R-core accepts A's recorded 47914 vs 47929 published-reference difference.",
            "",
        ]
    )


def build_manifest(
    final_decision: str,
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    input_paths: dict[str, Path],
    selected: dict[str, Any],
    upstream_manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    asof_meta: dict[str, Any],
    source_caveated: bool,
) -> dict[str, Any]:
    a, b, c, d, e_manifest = upstream_manifests
    manifest_path = paths["risk_on_cost_rejector_research_entry_hardening_manifest"]
    created_at = datetime.now(timezone.utc).isoformat()
    output_hashes = {
        key: path_hash(path)
        for key, path in sorted(paths.items())
        if path.exists() and path.is_file() and path != manifest_path
    }
    event_level_meta = event_level_output_metadata(paths)
    output_row_counts = {key: int(len(frame)) for key, frame in frames.items()}
    output_row_counts.update(
        {
            key: int(meta["uncompressed_row_count"])
            for key, meta in event_level_meta.items()
        }
    )
    return {
        "experiment_id": H_CONFIG["experiment_id"],
        "created_at": created_at,
        "run_id": stable_hash({"experiment": H_CONFIG["experiment_id"], "created_at": created_at}),
        "decision": final_decision,
        "blocked_reasons": [reason for reason in failures if reason.endswith("_blocked") or "blocked" in reason],
        "non_pass_failure_reasons": failures,
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "h_config_hash": stable_hash(H_CONFIG),
        "h_config": H_CONFIG,
        "experiment_a_decision": a.get("decision", ""),
        "experiment_b_decision": b.get("decision", ""),
        "experiment_c_decision": c.get("decision", ""),
        "experiment_d_decision": d.get("decision", ""),
        "experiment_e_decision": e_manifest.get("decision", ""),
        "source_caveated": source_caveated,
        "source_caveated_propagation_status": "propagated" if source_caveated else "not_required",
        "selected_source_pool": selected.get("source_pool", PRIMARY_SOURCE_POOL),
        "selected_model_id": selected.get("model_id", PRIMARY_MODEL_ID),
        "selected_threshold_id": selected.get("threshold_id", ""),
        "selected_keep_fraction": selected.get("keep_fraction", np.nan),
        "selected_candidate_tier": "research_entry" if selected else "not_selected",
        "threshold_selection_policy": H_CONFIG["threshold_selection_policy"],
        "density_caps": H_CONFIG["density_caps"],
        "density_cap_metric_map": DENSITY_CAP_METRIC_MAP,
        "density_contract_source_hash": path_hash(A_REPORT_DIR / "density_fast_fail_caliber_contract.md"),
        "feature_fix_policy": H_CONFIG["feature_fix_policy"],
        "dropped_feature_list": list(DROP_FEATURES),
        "feature_columns_hash": frames.get("risk_on_hardening_model_registry", pd.DataFrame()).get(
            "feature_columns_hash",
            pd.Series(dtype=str),
        ).iloc[0]
        if not frames.get("risk_on_hardening_model_registry", pd.DataFrame()).empty
        else "",
        "preprocessing_hash": frames.get("risk_on_hardening_model_registry", pd.DataFrame()).get(
            "feature_preprocessing_hash",
            pd.Series(dtype=str),
        ).iloc[0]
        if not frames.get("risk_on_hardening_model_registry", pd.DataFrame()).empty
        else "",
        "transition_scope_features_used": False,
        "e_baseline_threshold_ids": list(E_BASELINE_THRESHOLD_IDS),
        "h_threshold_id_mapping": {str(k): v for k, v in THRESHOLD_SUFFIX.items()},
        "feature_asof_join_policy": asof_meta.get("feature_join_policy", ""),
        "feature_asof_join_parameters": asof_meta,
        "feature_asof_join_parameter_hash": stable_hash(asof_meta),
        "source_panel_hash": path_hash(input_paths.get("cross_section_feature_panel", Path(""))),
        "max_observed_feature_lag": frames.get("risk_on_hardening_asof_join_audit", pd.DataFrame()).get(
            "max_feature_lag_days",
            pd.Series(dtype=float),
        ).iloc[0]
        if not frames.get("risk_on_hardening_asof_join_audit", pd.DataFrame()).empty
        else np.nan,
        "metric_denominator_policy_hash": stable_hash(
            "same_source_split_regime_horizon_complete_before_after"
        ),
        "metric_denominator_audit_hash": path_hash(paths["risk_on_hardening_metric_denominator_audit"]),
        "input_artifacts": input_artifact_metadata(input_paths),
        "output_paths": {key: str(path) for key, path in sorted(paths.items())},
        "output_hashes": output_hashes,
        "output_row_counts": output_row_counts,
        "event_level_outputs": event_level_meta,
        "runner_code_hash": path_hash(Path(__file__)),
    }


def empty_frames(input_frame: pd.DataFrame, config_contract: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    frames = {
        "risk_on_hardening_input_audit": input_frame,
        "risk_on_hardening_config_contract": config_contract if config_contract is not None else pd.DataFrame(),
        "risk_on_hardening_e_source_binding_audit": pd.DataFrame(),
        "risk_on_hardening_e_artifact_hash_audit": pd.DataFrame(),
        "risk_on_hardening_scope_reconstruction_audit": pd.DataFrame(),
        "risk_on_hardening_label_reconciliation_audit": pd.DataFrame(),
        "risk_on_hardening_asof_join_audit": pd.DataFrame(),
        "risk_on_hardening_feature_contract": pd.DataFrame(),
        "risk_on_hardening_feature_delta_from_e": pd.DataFrame(),
        "risk_on_hardening_model_registry": pd.DataFrame(),
        "risk_on_hardening_oos_separability": pd.DataFrame(),
        "risk_on_hardening_threshold_frontier": pd.DataFrame(),
        "risk_on_hardening_selected_threshold_readout": pd.DataFrame(),
        "risk_on_hardening_metric_denominator_audit": pd.DataFrame(),
        "risk_on_hardening_cost_readout": pd.DataFrame(),
        "risk_on_hardening_post_filter_retention_by_split": pd.DataFrame(),
        "risk_on_hardening_e1_missed_retention": pd.DataFrame(),
        "risk_on_hardening_density_readout": pd.DataFrame(),
        "risk_on_hardening_oracle_gap_audit": pd.DataFrame(),
        "risk_on_hardening_research_entry_gate_replay": pd.DataFrame(),
        "risk_on_hardening_decision_tiers": pd.DataFrame(),
    }
    return frames


def write_outputs(
    final_decision: str,
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    input_paths: dict[str, Path],
    upstream_manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    selected: dict[str, Any] | None = None,
    asof_meta: dict[str, Any] | None = None,
    source_caveated: bool = False,
    event_scores: pd.DataFrame | None = None,
    selected_events: pd.DataFrame | None = None,
    rejected_events: pd.DataFrame | None = None,
) -> dict[str, Any]:
    selected = selected or {}
    asof_meta = asof_meta or {}
    paths = output_paths()
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_df(paths["risk_on_hardening_event_scores"], event_scores if event_scores is not None else pd.DataFrame())
    write_df(paths["risk_on_hardening_selected_events"], selected_events if selected_events is not None else pd.DataFrame())
    write_df(paths["risk_on_hardening_rejected_events"], rejected_events if rejected_events is not None else pd.DataFrame())
    write_text(paths["risk_on_cost_rejector_research_entry_hardening_contract"], build_contract())
    write_text(
        paths["risk_on_cost_rejector_research_entry_hardening_report"],
        build_report(final_decision, selected, failures, frames, source_caveated),
    )
    write_json(
        paths["risk_on_cost_rejector_research_entry_hardening_manifest"],
        build_manifest(
            final_decision,
            failures,
            frames,
            paths,
            input_paths,
            selected,
            upstream_manifests,
            asof_meta,
            source_caveated,
        ),
    )
    return {
        "decision": final_decision,
        "failure_reasons": failures,
        "manifest_path": str(paths["risk_on_cost_rejector_research_entry_hardening_manifest"]),
        "report_path": str(paths["risk_on_cost_rejector_research_entry_hardening_report"]),
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def blocked_result(
    decision: str,
    failures: list[str],
    input_frame: pd.DataFrame,
    input_paths: dict[str, Path],
    upstream_manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    config_contract: pd.DataFrame | None = None,
    source_caveated: bool = False,
) -> dict[str, Any]:
    frames = empty_frames(input_frame, config_contract)
    frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, decision, failures)
    return write_outputs(decision, failures, frames, input_paths, upstream_manifests, source_caveated=source_caveated)


def run_experiment() -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_failures, input_paths = input_audit()
    config_contract, config_failures = build_config_contract()
    upstream = validate_upstream_manifests()
    a_manifest, b_manifest, c_manifest, d_manifest, e_manifest, manifest_failures = upstream
    upstream_tuple = (a_manifest, b_manifest, c_manifest, d_manifest, e_manifest)
    source_caveated = any(
        "source_caveated" in str(m.get("decision", "")) or "partial" in str(m.get("decision", ""))
        for m in upstream_tuple
    ) or bool(e_manifest.get("source_caveated", False))
    if input_failures or manifest_failures:
        return blocked_result(
            "risk_on_research_entry_hardening_input_blocked",
            input_failures + manifest_failures,
            input_frame,
            input_paths,
            upstream_tuple,
            config_contract,
            source_caveated,
        )
    if config_failures:
        return blocked_result(BLOCKED_DENSITY_CONFIG, config_failures, input_frame, input_paths, upstream_tuple, config_contract, source_caveated)

    e_binding_audit, e_binding_failures, e_source_caveated = validate_e_manifest(e_manifest)
    source_caveated = source_caveated or e_source_caveated
    if e_binding_failures:
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_e_source_binding_audit"] = e_binding_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_E_SOURCE, e_binding_failures)
        return write_outputs(BLOCKED_E_SOURCE, e_binding_failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)
    e_hash_audit, e_hash_failures = validate_e_artifact_hashes(e_manifest)
    if e_hash_failures:
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_e_source_binding_audit"] = e_binding_audit
        frames["risk_on_hardening_e_artifact_hash_audit"] = e_hash_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_E_HASH, e_hash_failures)
        return write_outputs(BLOCKED_E_HASH, e_hash_failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)

    canonical08 = read_csv(input_paths["candidate_family_canonical_events"])
    event_instances = read_csv(input_paths["candidate_family_event_instances"])
    input_frame["loaded_in_full_run"] = False
    input_frame["loaded_row_count"] = np.nan
    input_frame["loaded_column_count"] = np.nan
    input_frame["loaded_schema_fingerprint"] = ""
    event_instance_mask = input_frame["input_id"].astype(str).eq("candidate_family_event_instances")
    input_frame.loc[event_instance_mask, "loaded_in_full_run"] = True
    input_frame.loc[event_instance_mask, "loaded_row_count"] = int(len(event_instances))
    input_frame.loc[event_instance_mask, "loaded_column_count"] = int(len(event_instances.columns))
    input_frame.loc[event_instance_mask, "loaded_schema_fingerprint"] = dataframe_schema_fingerprint(event_instances)
    labels = pd.read_parquet(input_paths["candidate_family_event_labels"])
    panel = pd.read_parquet(input_paths["cross_section_feature_panel"])
    membership = pd.read_parquet(input_paths["d_membership"])
    d_scope = read_csv(input_paths["d_scope_retention"])
    mapping = read_csv(input_paths["candidate_scope_mapping_contract"])
    reconstruct = read_csv(input_paths["candidate_scope_reconstructability_audit"])
    density_summary = read_csv(input_paths["candidate_10d_density_summary"])
    _, leakage_failures = label_leakage_pass(input_paths["d_label_leakage_audit"])
    if leakage_failures:
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_e_source_binding_audit"] = e_binding_audit
        frames["risk_on_hardening_e_artifact_hash_audit"] = e_hash_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_REPLAY, leakage_failures)
        return write_outputs(BLOCKED_REPLAY, leakage_failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)

    scope_events = reconstruct_h_scope_events(canonical08, mapping)
    scope_audit, scope_failures = build_h_scope_reconstruction_audit(scope_events, mapping, reconstruct)
    if scope_failures:
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_e_source_binding_audit"] = e_binding_audit
        frames["risk_on_hardening_e_artifact_hash_audit"] = e_hash_audit
        frames["risk_on_hardening_scope_reconstruction_audit"] = scope_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_REPLAY, scope_failures)
        return write_outputs(BLOCKED_REPLAY, scope_failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)

    event_frames: list[pd.DataFrame] = []
    for source_pool in H_SOURCE_POOLS:
        frame = scope_events[source_pool].copy()
        if "primary_family_id" not in frame.columns:
            frame["primary_family_id"] = frame.get("family_id", frame.get("scope_family_id", "unknown"))
        event_frames.append(frame)
    all_events = pd.concat(event_frames, ignore_index=True, sort=False)
    all_events, label_audit, label_failures = e_runner.join_event_labels(all_events, labels, membership)
    primary_label_row = label_audit.loc[label_audit["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)]
    primary_label_complete = (
        float(primary_label_row.iloc[0].get("cost_label_complete_rate", np.nan)) if not primary_label_row.empty else np.nan
    )
    if label_failures or pd.isna(primary_label_complete) or primary_label_complete < 0.95:
        failures = label_failures or [f"primary_label_complete_rate_below_95pct:{primary_label_complete}"]
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_e_source_binding_audit"] = e_binding_audit
        frames["risk_on_hardening_e_artifact_hash_audit"] = e_hash_audit
        frames["risk_on_hardening_scope_reconstruction_audit"] = scope_audit
        frames["risk_on_hardening_label_reconciliation_audit"] = label_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_REPLAY, failures)
        return write_outputs(BLOCKED_REPLAY, failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)

    events = all_events.loc[all_events["event_regime_bucket"].astype(str).eq(TARGET_REGIME)].copy()
    forbidden_feature_tokens = ("transition_from", "next_regime", "transition_conversion")
    forbidden_cols = [
        col for col in feature_input_columns(events)
        if any(token in str(col) for token in forbidden_feature_tokens)
    ]
    if forbidden_cols:
        failures = [f"transition_scope_feature_used:{col}" for col in forbidden_cols]
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_TRANSITION, failures)
        return write_outputs(BLOCKED_TRANSITION, failures, frames, input_paths, upstream_tuple, source_caveated=source_caveated)

    events, asof_meta = e_runner.asof_join_panel(events, panel)
    events["feature_source_hash"] = path_hash(input_paths["cross_section_feature_panel"])
    asof_audit = asof_join_audit(events, asof_meta, path_hash(input_paths["cross_section_feature_panel"]))
    if asof_meta.get("future_join_row_count", 0):
        failures = ["feature_as_of_date_after_event_t0_date"]
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_asof_join_audit"] = asof_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_ASOF, failures)
        return write_outputs(BLOCKED_ASOF, failures, frames, input_paths, upstream_tuple, asof_meta=asof_meta, source_caveated=source_caveated)

    feature_contract = build_h_feature_contract(
        events,
        path_hash(input_paths["candidate_family_canonical_events"]),
        path_hash(input_paths["cross_section_feature_panel"]),
        asof_meta,
    )
    e_contract = read_csv(input_paths["e_risk_on_cost_rejector_feature_contract"])
    feature_delta = build_feature_delta_from_e(e_contract, feature_contract)
    if not selected_feature_coverage_ok(feature_contract):
        failures = ["allowed_feature_coverage_below_95pct_after_lag20_drop"]
        frames = empty_frames(input_frame, config_contract)
        frames.update(
            {
                "risk_on_hardening_e_source_binding_audit": e_binding_audit,
                "risk_on_hardening_e_artifact_hash_audit": e_hash_audit,
                "risk_on_hardening_scope_reconstruction_audit": scope_audit,
                "risk_on_hardening_label_reconciliation_audit": label_audit,
                "risk_on_hardening_asof_join_audit": asof_audit,
                "risk_on_hardening_feature_contract": feature_contract,
                "risk_on_hardening_feature_delta_from_e": feature_delta,
                "risk_on_hardening_decision_tiers": build_decision_tiers({}, BLOCKED_FEATURE_COVERAGE, failures),
            }
        )
        return write_outputs(BLOCKED_FEATURE_COVERAGE, failures, frames, input_paths, upstream_tuple, asof_meta=asof_meta, source_caveated=source_caveated)

    scores, model_registry, oos = fit_primary_model(events)
    frontier = build_threshold_frontier(events, scores, membership, d_scope)
    denominator_audit = build_metric_denominator_audit(events, scores, frontier)
    if not denominator_audit.empty and not denominator_audit["before_after_denominator_status"].astype(str).eq("pass").all():
        failures = denominator_audit.loc[
            ~denominator_audit["before_after_denominator_status"].astype(str).eq("pass"),
            "threshold_id",
        ].astype(str).tolist()
        frames = empty_frames(input_frame, config_contract)
        frames["risk_on_hardening_metric_denominator_audit"] = denominator_audit
        frames["risk_on_hardening_decision_tiers"] = build_decision_tiers({}, BLOCKED_DENOMINATOR, failures)
        return write_outputs(BLOCKED_DENOMINATOR, failures, frames, input_paths, upstream_tuple, asof_meta=asof_meta, source_caveated=source_caveated)

    selected, train_failure = select_train_threshold(frontier)
    if selected:
        frontier.loc[frontier["threshold_id"].astype(str).eq(str(selected["threshold_id"])), "selected_model_threshold_flag"] = True
    selected_readout = build_selected_threshold_readout(selected, train_failure)
    source_events = events.loc[events["source_pool"].astype(str).eq(PRIMARY_SOURCE_POOL)].copy()
    if selected:
        selected_events, rejected_events = e_runner.build_selected_event_tables(events, scores, selected)
        cost_readout = e_runner.build_cost_readout(events, selected_events, selected)
        retention, e1_missed = e_runner.build_retention_outputs(selected, selected_events, membership, d_scope)
        density_readout = apply_density_caps(
            e_runner.build_density_readout(selected_events, density_summary, selected),
            selected_events,
            source_events,
        )
    else:
        selected_events = empty_event_table_schema()
        rejected_events = empty_event_table_schema()
        cost_readout, retention, e1_missed, density_readout = no_selected_readouts(train_failure)
    oracle_gap = build_oracle_gap_audit(frontier, selected)
    final_decision, failures = decision_from_selected(
        selected,
        source_caveated,
        oos,
        feature_contract,
        density_readout,
        train_failure,
    )
    gate_replay = build_gate_replay(selected, final_decision, failures, density_readout)
    decision_tiers = build_decision_tiers(selected, final_decision, failures)
    frames = {
        "risk_on_hardening_input_audit": input_frame,
        "risk_on_hardening_config_contract": config_contract,
        "risk_on_hardening_e_source_binding_audit": e_binding_audit,
        "risk_on_hardening_e_artifact_hash_audit": e_hash_audit,
        "risk_on_hardening_scope_reconstruction_audit": scope_audit,
        "risk_on_hardening_label_reconciliation_audit": label_audit,
        "risk_on_hardening_asof_join_audit": asof_audit,
        "risk_on_hardening_feature_contract": feature_contract,
        "risk_on_hardening_feature_delta_from_e": feature_delta,
        "risk_on_hardening_model_registry": model_registry,
        "risk_on_hardening_oos_separability": oos,
        "risk_on_hardening_threshold_frontier": frontier,
        "risk_on_hardening_selected_threshold_readout": selected_readout,
        "risk_on_hardening_metric_denominator_audit": denominator_audit,
        "risk_on_hardening_cost_readout": cost_readout,
        "risk_on_hardening_post_filter_retention_by_split": retention,
        "risk_on_hardening_e1_missed_retention": e1_missed,
        "risk_on_hardening_density_readout": density_readout,
        "risk_on_hardening_oracle_gap_audit": oracle_gap,
        "risk_on_hardening_research_entry_gate_replay": gate_replay,
        "risk_on_hardening_decision_tiers": decision_tiers,
    }
    return write_outputs(
        final_decision,
        failures,
        frames,
        input_paths,
        upstream_tuple,
        selected=selected,
        asof_meta=asof_meta,
        source_caveated=source_caveated,
        event_scores=scores,
        selected_events=selected_events,
        rejected_events=rejected_events,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dirs()
    if args.mode == "check-inputs":
        input_frame, failures, _ = input_audit()
        config_contract, config_failures = build_config_contract()
        write_df(H_TABLE_DIR / "risk_on_hardening_input_audit.csv", input_frame)
        write_df(H_TABLE_DIR / "risk_on_hardening_config_contract.csv", config_contract)
        for failure in failures + config_failures:
            print(failure)
        print(f"input_failures={len(failures) + len(config_failures)}")
        return 1 if failures or config_failures else 0
    result = run_experiment()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if "blocked" not in str(result.get("decision", "")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
