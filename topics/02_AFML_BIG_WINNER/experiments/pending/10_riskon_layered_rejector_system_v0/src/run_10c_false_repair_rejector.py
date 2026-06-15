#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = TOPIC_ROOT / "src"

for import_path in (SRC_DIR, Path(__file__).resolve().parent):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_10c.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_10c_false_repair_rejector.md"

OUTPUT_TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "10C_false_repair_rejector"
OUTPUT_REPORT = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "10C_false_repair_rejector_report.md"
OUTPUT_LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "10C_false_repair_rejector"
OUTPUT_MANIFEST = EXPERIMENT_DIR / "outputs" / "manifests" / "10C_false_repair_rejector_manifest.json"

DECISION_SUPPORTED = "10C_false_repair_rejector_supported"
DECISION_SOURCE_CAVEATED_SUPPORTED = "10C_false_repair_rejector_source_caveated_supported"
DECISION_FEATURE_SOURCE_SUPPORTED = "10C_false_repair_feature_source_supported"
DECISION_DIAGNOSTIC = "10C_false_repair_diagnostic_only"
DECISION_INPUT_BLOCKED = "10C_false_repair_input_blocked"

SPLIT_ORDER = ["train", "validation", "robustness"]
META_FEATURE_COLUMNS = {
    "sample_id",
    "selected_target_id",
    "denominator_id",
    "canonical_event_id",
    "instrument",
    "event_t0_date",
    "event_split",
    "feature_as_of_date",
}
FORBIDDEN_FEATURE_COLUMNS = META_FEATURE_COLUMNS | {
    "final_sample_weight",
    "active_interval_start",
    "active_interval_end",
    "active_interval_calendar_day_n",
}

INPUT_AUDIT_COLUMNS = [
    "artifact_id",
    "relative_path",
    "resolved_path",
    "required_flag",
    "exists_flag",
    "content_hash",
    "schema_status",
    "row_count",
    "failure_reason",
]
OPTIONAL_INPUT_ARTIFACTS = {"upstream_08_run_manifest"}
SUPPORTED_ONLY_INPUT_ARTIFACTS = {"upstream_10b_manifest", "upstream_10b_scores"}
SCHEMA_ARTIFACT_TO_INPUT_ARTIFACT = {
    "post_dedup_false_repair_power_audit": "upstream_10a_false_repair_power_audit",
    "power_audit_config": "upstream_10a_power_audit_config",
    "post_dedup_event_bindings": "upstream_10a_event_bindings",
    "feature_contract": "upstream_09b_feature_contract",
    "feature_matrix": "upstream_09b_feature_matrix",
    "sample_uniqueness_weights": "upstream_09b_sample_weights",
    "candidate_family_event_labels": "upstream_08_event_labels",
    "post_replay_event_episode_membership": "upstream_08_episode_membership",
    "post_dedup_fast_fail_scores": "upstream_10b_scores",
}
MODEL_REGISTRY_COLUMNS = [
    "model_id",
    "ablation_id",
    "selected_flag",
    "feature_count",
    "dropped_constant_feature_count",
    "dropped_missing_feature_count",
    "train_fit_rows",
    "train_positive_n",
    "train_weight_sum",
    "solver",
    "penalty",
    "C",
    "random_state",
    "preprocess_fit_split",
    "model_status",
]
POWER_GATE_COLUMNS = [
    "model_id",
    "ablation_id",
    "population_id",
    "denominator_id",
    "split",
    "capacity_id",
    "threshold_id",
    "sample_n",
    "reject_n",
    "reject_fraction_actual",
    "false_repair_positive_n",
    "winner_n",
    "e1_missed_winner_n",
    "bridge_winner_n",
    "candidate_rejected_false_repair_positive_n",
    "candidate_rejected_false_repair_non_winner_n",
    "candidate_rejected_winner_n",
    "candidate_rejected_e1_missed_winner_n",
    "candidate_rejected_bridge_winner_n",
    "random_rejected_false_repair_positive_n",
    "random_rejected_false_repair_non_winner_n",
    "random_rejected_winner_n",
    "false_repair_capture_rate",
    "random_false_repair_capture_rate",
    "false_repair_capture_lift_vs_random",
    "candidate_precision",
    "winner_retention",
    "wrong_kill_rate",
    "e1_missed_retention",
    "e1_missed_wrong_kill_rate",
    "bridge_retention",
    "bridge_wrong_kill_rate",
    "bridge_gate_binding_flag",
    "train_selection_utility",
    "supported_row_flag",
    "row_block_reason",
]
FRONTIER_COLUMNS = [
    "model_id",
    "ablation_id",
    "capacity_id",
    "threshold_id",
    "selected_flag",
    "selection_rank",
    "train_selection_utility",
    "selected_train_constrained_utility",
    "train_false_repair_capture_lift_vs_random",
    "train_exposure_days_lift_vs_random",
    "train_winner_retention",
    "train_e1_missed_retention",
    "train_bridge_retention",
    "validation_false_repair_capture_lift_vs_random",
    "validation_winner_retention",
    "robustness_false_repair_capture_lift_vs_random",
    "robustness_winner_retention",
    "oos_rejected_fraction_spread",
    "train_cv_selected_reject_fraction_std",
    "decision_block_reason",
]
EXPOSURE_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "false_repair_non_winner_exposure_days_before",
    "false_repair_non_winner_exposure_days_rejected",
    "false_repair_non_winner_exposure_days_reduction",
    "random_false_repair_non_winner_exposure_days_reduction",
    "exposure_days_lift_vs_random",
    "all_rejected_exposure_days",
    "winner_rejected_exposure_days",
    "exposure_interval_invalid_n",
    "exposure_interval_invalid_rate",
]
RETENTION_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "winner_n",
    "candidate_rejected_winner_n",
    "winner_retention",
    "e1_missed_winner_n",
    "candidate_rejected_e1_missed_winner_n",
    "e1_missed_retention",
    "e1_missed_wrong_kill_rate",
    "bridge_winner_n",
    "candidate_rejected_bridge_winner_n",
    "bridge_retention",
    "bridge_wrong_kill_rate",
    "bridge_gate_binding_flag",
    "bridge_membership_missing_n",
    "bridge_membership_missing_rate",
    "retention_status",
]
MFE_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "bucket",
    "row_n",
    "confirm_20_positive_n",
    "confirm_20_positive_rate",
    "mfe_20d_mean",
    "mfe_20d_median",
    "mfe_20d_p25",
    "mfe_20d_p75",
    "label_consistency_mismatch_n",
    "label_consistency_mismatch_rate",
]
INSTABILITY_COLUMNS = [
    "fold_id",
    "fold_start_date",
    "fold_end_date",
    "fit_rows",
    "holdout_rows",
    "holdout_false_repair_positive_n",
    "holdout_winner_n",
    "selected_capacity_id",
    "selected_reject_fraction",
    "fold_train_selection_utility",
    "fold_status",
]
CASCADE_COLUMNS = [
    "split",
    "cascade_bucket",
    "row_n",
    "false_repair_positive_n",
    "false_repair_non_winner_n",
    "fast_fail_positive_n",
    "winner_n",
    "e1_missed_winner_n",
    "bridge_winner_n",
    "false_repair_non_winner_exposure_days",
    "winner_retention_contribution",
    "notes",
]
DIAGNOSTIC_COLUMNS = ["diagnostic_source", "split", "metric_id", "metric_value", "comparison_note"]
SCORE_COLUMNS = [
    "model_id",
    "ablation_id",
    "capacity_id",
    "threshold_id",
    "reject_fraction",
    "population_id",
    "denominator_id",
    "split",
    "input_event_key",
    "sample_id",
    "selected_target_id",
    "binding_canonical_event_id",
    "instrument",
    "event_t0_date",
    "admitted_event_id",
    "frozen_false_repair_20d_label",
    "false_repair_non_winner_flag",
    "selected_fast_fail_10_label",
    "winner_120",
    "E1_missed_winner_flag",
    "bridge_positive_flag",
    "confirm_20_label",
    "mfe_20d",
    "final_sample_weight",
    "active_interval_calendar_day_n",
    "candidate_false_repair_score",
    "candidate_rank",
    "random_baseline_rank",
    "candidate_rejected_flag",
    "random_baseline_rejected_flag",
    "fast_fail_rejected_flag",
    "cascade_bucket",
]


@dataclass(frozen=True)
class ModelResult:
    model_id: str
    ablation_id: str
    feature_cols: tuple[str, ...]
    feature_count_input: int
    dropped_constant_count: int
    dropped_missing_count: int
    scores: pd.Series
    status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 10C false-repair rejector.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def git_revision(cwd: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if pd.isna(value) else float(value)
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("../"):
        return (EXPERIMENT_DIR / path).resolve()
    return (EXPERIMENT_DIR / path).resolve()


def relative_to_experiment(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(EXPERIMENT_DIR.resolve()))
    except ValueError:
        try:
            return str(path.resolve().relative_to(REPO_ROOT.resolve()))
        except ValueError:
            return str(path)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def manifest_source_caveated(manifest: dict[str, Any] | None) -> bool:
    if not manifest:
        return False
    statuses = manifest.get("statuses", {}) if isinstance(manifest.get("statuses", {}), dict) else {}
    if boolish(manifest.get("source_caveated")) or boolish(statuses.get("source_caveated")):
        return True
    if boolish(manifest.get("homogeneous_signal_caveat")) or boolish(statuses.get("homogeneous_signal_caveat")):
        return True
    decision_fields = [
        manifest.get("decision"),
        manifest.get("decision_reason"),
        statuses.get("decision"),
        statuses.get("decision_reason"),
        statuses.get("source_caveat_status"),
    ]
    return any("source_caveated" in str(value).lower() for value in decision_fields if value is not None)


def upstream_source_caveated(*manifests: dict[str, Any] | None) -> bool:
    return any(manifest_source_caveated(manifest) for manifest in manifests)


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return np.nan
    return float(numerator) / float(denominator)


def is_finite_number(value: Any) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric)


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def hash_or_empty(path: Path) -> str:
    return file_sha256(path) if path.is_file() else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def random_key(input_event_key: str, capacity_id: str, seed: int) -> str:
    return hashlib.sha256(f"{input_event_key}|{capacity_id}|{seed}".encode("utf-8")).hexdigest()


def read_row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        if path.suffix == ".parquet":
            return int(pd.read_parquet(path).shape[0])
        if path.suffix in {".csv", ".gz"} or path.name.endswith(".csv.gz"):
            return int(pd.read_csv(path).shape[0])
        if path.suffix == ".json":
            return 1
        if path.suffix == ".md":
            return len(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0
    return 0


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_TABLE_DIR / "input_artifact_audit.csv",
        "model_registry": OUTPUT_TABLE_DIR / "model_registry.csv",
        "false_repair_power_gate_readout": OUTPUT_TABLE_DIR / "false_repair_power_gate_readout.csv",
        "false_repair_threshold_frontier": OUTPUT_TABLE_DIR / "false_repair_threshold_frontier.csv",
        "exposure_efficiency_readout": OUTPUT_TABLE_DIR / "exposure_efficiency_readout.csv",
        "winner_retention_audit": OUTPUT_TABLE_DIR / "winner_retention_audit.csv",
        "mfe_confirm_relation_readout": OUTPUT_TABLE_DIR / "mfe_confirm_relation_readout.csv",
        "train_only_threshold_instability": OUTPUT_TABLE_DIR / "train_only_threshold_instability.csv",
        "cascade_overlap_attribution": OUTPUT_TABLE_DIR / "cascade_overlap_attribution.csv",
        "pre_dedup_09c_diagnostic_comparison": OUTPUT_TABLE_DIR / "pre_dedup_09c_diagnostic_comparison.csv",
        "post_dedup_false_repair_scores": OUTPUT_LOCAL_CACHE_DIR / "post_dedup_false_repair_scores.parquet",
        "report": OUTPUT_REPORT,
        "manifest": OUTPUT_MANIFEST,
    }


OUTPUT_SCHEMA_BY_KEY = {
    "input_artifact_audit": INPUT_AUDIT_COLUMNS,
    "model_registry": MODEL_REGISTRY_COLUMNS,
    "false_repair_power_gate_readout": POWER_GATE_COLUMNS,
    "false_repair_threshold_frontier": FRONTIER_COLUMNS,
    "exposure_efficiency_readout": EXPOSURE_COLUMNS,
    "winner_retention_audit": RETENTION_COLUMNS,
    "mfe_confirm_relation_readout": MFE_COLUMNS,
    "train_only_threshold_instability": INSTABILITY_COLUMNS,
    "cascade_overlap_attribution": CASCADE_COLUMNS,
    "pre_dedup_09c_diagnostic_comparison": DIAGNOSTIC_COLUMNS,
    "post_dedup_false_repair_scores": SCORE_COLUMNS,
}


def expected_hash_map(manifest_10a: dict[str, Any] | None, manifest_10b: dict[str, Any] | None) -> dict[str, str]:
    expected: dict[str, str] = {}
    if manifest_10a:
        output_hashes = manifest_10a.get("output_hashes", {})
        input_hashes = manifest_10a.get("input_hashes", {})
        expected.update(
            {
                "upstream_10a_population_contract": output_hashes.get("post_dedup_population_contract", ""),
                "upstream_10a_false_repair_power_audit": output_hashes.get("post_dedup_false_repair_power_audit", ""),
                "upstream_10a_power_audit_config": output_hashes.get("power_audit_config", ""),
                "upstream_10a_event_bindings": output_hashes.get("post_dedup_event_bindings", ""),
                "upstream_09b_feature_contract": input_hashes.get("upstream_09b_feature_contract", ""),
                "upstream_09b_feature_matrix": input_hashes.get("upstream_09b_feature_matrix", ""),
                "upstream_09b_sample_weights": input_hashes.get("upstream_09b_sample_weights", ""),
            }
        )
    if manifest_10b:
        expected["upstream_10b_scores"] = manifest_10b.get("output_hashes", {}).get("post_dedup_fast_fail_scores", "")
    return expected


def input_audit(paths: dict[str, Path], expected: dict[str, str]) -> pd.DataFrame:
    optional = OPTIONAL_INPUT_ARTIFACTS | SUPPORTED_ONLY_INPUT_ARTIFACTS
    required = {key: key not in optional for key in paths}
    rows = []
    for artifact_id, path in paths.items():
        exists = path.is_file()
        content_hash = hash_or_empty(path)
        expected_hash = expected.get(artifact_id, "")
        schema_status = "pending_schema_check" if exists else "optional_missing"
        failure_reason = ""
        if required.get(artifact_id, True) and not exists:
            schema_status = "missing_required"
            failure_reason = "missing_required"
        elif artifact_id in SUPPORTED_ONLY_INPUT_ARTIFACTS and not exists:
            schema_status = "supported_only_missing"
            failure_reason = "required_for_supported_decision"
        elif not exists:
            schema_status = "optional_missing"
        elif expected_hash and content_hash != expected_hash:
            schema_status = "hash_mismatch"
            failure_reason = f"expected_hash={expected_hash}"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": relative_to_experiment(path),
                "resolved_path": str(path),
                "required_flag": bool(required.get(artifact_id, True)),
                "exists_flag": bool(exists),
                "content_hash": content_hash,
                "schema_status": schema_status,
                "row_count": read_row_count(path) if exists else 0,
                "failure_reason": failure_reason,
            }
        )
    return pd.DataFrame(rows, columns=INPUT_AUDIT_COLUMNS)


def hard_input_failures(audit: pd.DataFrame) -> list[str]:
    failures = audit.loc[
        audit["required_flag"] & audit["schema_status"].isin(["missing_required", "hash_mismatch", "schema_missing_columns"]),
        ["artifact_id", "schema_status"],
    ]
    return [f"{row.artifact_id}:{row.schema_status}" for row in failures.itertuples()]


def parse_schema_failure(failure: str) -> tuple[str, str] | None:
    parts = failure.split(":", 2)
    if len(parts) != 3 or parts[0] != "schema_missing_columns":
        return None
    return parts[1], parts[2]


def apply_schema_audit(audit: pd.DataFrame, schema_failures: list[str]) -> pd.DataFrame:
    out = audit.copy()
    pass_mask = out["exists_flag"].map(boolish) & out["schema_status"].eq("pending_schema_check")
    out.loc[pass_mask, "schema_status"] = "pass"
    for failure in schema_failures:
        parsed = parse_schema_failure(failure)
        if parsed is None:
            continue
        schema_artifact_id, detail = parsed
        input_artifact_id = SCHEMA_ARTIFACT_TO_INPUT_ARTIFACT.get(schema_artifact_id)
        if input_artifact_id is None:
            continue
        mask = out["artifact_id"].astype(str).eq(input_artifact_id)
        out.loc[mask, "schema_status"] = "schema_missing_columns"
        out.loc[mask, "failure_reason"] = detail
    return out[INPUT_AUDIT_COLUMNS]


def supported_only_input_failures(audit: pd.DataFrame) -> list[str]:
    statuses = {"supported_only_missing", "hash_mismatch", "schema_missing_columns"}
    rows = audit.loc[
        audit["artifact_id"].isin(SUPPORTED_ONLY_INPUT_ARTIFACTS) & audit["schema_status"].isin(statuses),
        ["artifact_id", "schema_status"],
    ]
    return [f"{row.artifact_id}:{row.schema_status}" for row in rows.itertuples()]


def is_supported_only_schema_failure(failure: str) -> bool:
    parsed = parse_schema_failure(failure)
    return parsed is not None and parsed[0] == "post_dedup_fast_fail_scores"


def required_column_failures(frame: pd.DataFrame, artifact_id: str, required: set[str]) -> list[str]:
    missing = sorted(required - set(frame.columns))
    return [f"schema_missing_columns:{artifact_id}:{';'.join(missing)}"] if missing else []


BINDING_REQUIRED_COLUMNS = {
    "population_id",
    "rule_arm_id",
    "input_event_key",
    "sample_id",
    "selected_target_id",
    "input_denominator_id",
    "denominator_id",
    "split",
    "instrument",
    "event_t0_date",
    "admission_status",
    "readout_only_flag",
    "admitted_event_id",
    "selected_fast_fail_10_label",
    "frozen_false_repair_20d_label",
    "selected_cost_bad_10_20_target",
    "winner_120",
    "E1_missed_winner_flag",
    "feature_matrix_join_key",
}
POWER_REQUIRED_COLUMNS = {
    "population_id",
    "rule_arm_id",
    "input_denominator_id",
    "denominator_id",
    "split",
    "readout_only_flag",
    "capacity_id",
    "threshold_id",
    "post_dedup_sample_n",
    "post_dedup_false_repair_positive_n",
    "post_dedup_winner_n",
    "post_dedup_E1_missed_winner_n",
    "e1_missed_proxy_status",
    "false_repair_ml_supported_gate_allowed",
}
POWER_CONFIG_REQUIRED_COLUMNS = {"component_id", "capacity_id", "threshold_id", "reject_fraction", "random_seed"}
FEATURE_CONTRACT_REQUIRED_COLUMNS = {
    "feature_id",
    "allowed_for_09C_flag",
    "t0_visible_flag",
    "feature_dtype",
    "feature_family",
    "label_mechanism_overlap_type",
}
FEATURE_MATRIX_REQUIRED_COLUMNS = {
    "sample_id",
    "selected_target_id",
    "denominator_id",
    "canonical_event_id",
    "event_split",
}
WEIGHT_REQUIRED_COLUMNS = {
    "sample_id",
    "selected_target_id",
    "denominator_id",
    "canonical_event_id",
    "weight_horizon_id",
    "active_interval_start",
    "active_interval_end",
    "final_sample_weight",
    "weight_status",
}
LABEL_REQUIRED_COLUMNS = {
    "event_id",
    "confirm_20_label",
    "confirm_20_complete",
    "mfe_20d",
    "horizon_complete_20d",
    "event_false_repair_20d_label",
    "label_scope",
}
MEMBERSHIP_REQUIRED_COLUMNS = {
    "canonical_event_id",
    "target_episode_id",
    "bridge_positive_denominator_included",
    "membership_basis",
}
TENB_SCORE_REQUIRED_COLUMNS = {
    "model_id",
    "ablation_id",
    "population_id",
    "denominator_id",
    "capacity_id",
    "threshold_id",
    "input_event_key",
    "sample_id",
    "selected_target_id",
    "binding_canonical_event_id",
    "split",
    "candidate_rejected_flag",
}


def validate_loaded_schemas(
    power: pd.DataFrame,
    power_config: pd.DataFrame,
    bindings: pd.DataFrame,
    feature_contract: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    weights: pd.DataFrame,
    labels: pd.DataFrame,
    membership: pd.DataFrame,
    tenb_scores: pd.DataFrame | None,
) -> list[str]:
    checks = [
        (power, "post_dedup_false_repair_power_audit", POWER_REQUIRED_COLUMNS),
        (power_config, "power_audit_config", POWER_CONFIG_REQUIRED_COLUMNS),
        (bindings, "post_dedup_event_bindings", BINDING_REQUIRED_COLUMNS),
        (feature_contract, "feature_contract", FEATURE_CONTRACT_REQUIRED_COLUMNS),
        (feature_matrix, "feature_matrix", FEATURE_MATRIX_REQUIRED_COLUMNS),
        (weights, "sample_uniqueness_weights", WEIGHT_REQUIRED_COLUMNS),
        (labels, "candidate_family_event_labels", LABEL_REQUIRED_COLUMNS),
        (membership, "post_replay_event_episode_membership", MEMBERSHIP_REQUIRED_COLUMNS),
    ]
    if tenb_scores is not None:
        checks.append((tenb_scores, "post_dedup_fast_fail_scores", TENB_SCORE_REQUIRED_COLUMNS))
    failures: list[str] = []
    for frame, artifact_id, required in checks:
        failures.extend(required_column_failures(frame, artifact_id, required))
    return failures


def derive_binding_canonical_event_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    parts = out["input_event_key"].astype(str).str.split("|", regex=False, expand=True)
    if parts.shape[1] != 4:
        out["binding_canonical_event_id"] = np.nan
        out["binding_key_status"] = "input_event_key_component_count_mismatch"
        return out
    out["binding_canonical_event_id"] = parts[3]
    valid = (
        parts[0].astype(str).eq(out["sample_id"].astype(str))
        & parts[1].astype(str).eq(out["selected_target_id"].astype(str))
        & parts[2].astype(str).eq(out["input_denominator_id"].astype(str))
        & out["binding_canonical_event_id"].notna()
        & out["binding_canonical_event_id"].astype(str).ne("")
    )
    out["binding_key_status"] = np.where(valid, "pass", "input_event_key_component_mismatch")
    return out


def dedupe_labels(labels: pd.DataFrame) -> pd.DataFrame:
    out = labels.copy()
    out["_label_scope_rank"] = np.where(out["label_scope"].astype(str).eq("all_new_candidate_union"), 0, 1)
    sort_cols = ["event_id", "_label_scope_rank"]
    if "canonical_event_scope" in out.columns:
        sort_cols.append("canonical_event_scope")
    if "event_family" in out.columns:
        sort_cols.append("event_family")
    out = out.sort_values(sort_cols, kind="mergesort").drop_duplicates("event_id")
    return out.drop(columns=["_label_scope_rank"])


def prepare_membership(membership: pd.DataFrame) -> pd.DataFrame:
    if membership.empty:
        return pd.DataFrame(columns=["canonical_event_id", "bridge_positive_flag", "bridge_membership_row_n"])
    return (
        membership.groupby("canonical_event_id", dropna=False)
        .agg(
            bridge_positive_flag=("bridge_positive_denominator_included", lambda s: bool(pd.Series(s).map(boolish).any())),
            bridge_membership_row_n=("bridge_positive_denominator_included", "size"),
        )
        .reset_index()
    )


def active_interval_days(start: pd.Series, end: pd.Series) -> pd.Series:
    start_dt = pd.to_datetime(start, errors="coerce")
    end_dt = pd.to_datetime(end, errors="coerce")
    return (end_dt - start_dt).dt.days + 1


def prepare_default_frame(
    bindings: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    weights: pd.DataFrame,
    labels: pd.DataFrame,
    membership: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    run_cfg = config["run"]
    failures: list[str] = []
    diagnostics: dict[str, Any] = {}
    frame = bindings.loc[
        (bindings["population_id"] == run_cfg["selected_population_id"])
        & (bindings["rule_arm_id"] == run_cfg["selected_rule_arm_id"])
        & (bindings["input_denominator_id"] == run_cfg["input_denominator_id"])
        & (bindings["denominator_id"] == run_cfg["denominator_id"])
        & (~bindings["readout_only_flag"].map(boolish))
        & (bindings["admission_status"] == "admitted")
        & (bindings["split"].isin(run_cfg["readout_splits"]))
    ].copy()
    frame = derive_binding_canonical_event_id(frame)
    bad_binding = int(frame["binding_key_status"].ne("pass").sum())
    if bad_binding:
        failures.append(f"binding_key_status_fail:{bad_binding}")

    feature_keys = ["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"]
    feature_dups = int(feature_matrix.duplicated(feature_keys).sum())
    if feature_dups:
        failures.append(f"feature_join_duplicate_rows:{feature_dups}")
    frame = frame.merge(
        feature_matrix,
        left_on=["sample_id", "selected_target_id", "input_denominator_id", "binding_canonical_event_id"],
        right_on=["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"],
        how="left",
        suffixes=("", "_feature"),
        indicator="feature_join_indicator",
    )
    feature_missing = int(frame["feature_join_indicator"].ne("both").sum())
    if feature_missing:
        failures.append(f"feature_join_missing:{feature_missing}")
    split_mismatch = int(frame["split"].astype(str).ne(frame["event_split"].astype(str)).sum())
    if split_mismatch:
        failures.append(f"feature_split_mismatch:{split_mismatch}")

    weight = weights.loc[weights["weight_horizon_id"].astype(str).eq(run_cfg["weight_horizon_id"])].copy()
    weight_keys = ["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"]
    weight_dups = int(weight.duplicated(weight_keys).sum())
    if weight_dups:
        failures.append(f"weight_join_duplicate_rows:{weight_dups}")
    weight_cols = weight_keys + [
        "final_sample_weight",
        "weight_status",
        "active_interval_start",
        "active_interval_end",
    ]
    frame = frame.merge(
        weight[weight_cols],
        left_on=["sample_id", "selected_target_id", "input_denominator_id", "binding_canonical_event_id"],
        right_on=weight_keys,
        how="left",
        suffixes=("", "_weight"),
        indicator="weight_join_indicator",
    )
    weight_missing = int(frame["weight_join_indicator"].ne("both").sum())
    bad_weight = int(
        (
            frame["final_sample_weight"].isna()
            | pd.to_numeric(frame["final_sample_weight"], errors="coerce").le(0)
            | frame["weight_status"].astype(str).ne("complete")
        ).sum()
    )
    if weight_missing:
        failures.append(f"weight_join_missing:{weight_missing}")
    if bad_weight:
        failures.append(f"bad_cost_weight:{bad_weight}")
    frame["active_interval_calendar_day_n"] = active_interval_days(
        frame["active_interval_start"], frame["active_interval_end"]
    )
    invalid_interval = frame["active_interval_calendar_day_n"].isna() | frame["active_interval_calendar_day_n"].le(0)
    invalid_rate = safe_div(int(invalid_interval.sum()), len(frame))
    diagnostics["exposure_interval_invalid_n"] = int(invalid_interval.sum())
    diagnostics["exposure_interval_invalid_rate"] = invalid_rate
    if invalid_rate > float(config["diagnostics"]["exposure_interval_invalid_rate_cap"]):
        failures.append(f"exposure_interval_invalid_rate:{invalid_rate:.6f}")

    label = dedupe_labels(labels)
    label_cols = [
        "event_id",
        "confirm_20_label",
        "confirm_20_complete",
        "mfe_20d",
        "horizon_complete_20d",
        "event_false_repair_20d_label",
        "label_scope",
    ]
    frame = frame.merge(
        label[label_cols],
        left_on="binding_canonical_event_id",
        right_on="event_id",
        how="left",
        indicator="label_join_indicator",
    )
    label_missing = int(frame["label_join_indicator"].ne("both").sum())
    if label_missing:
        failures.append(f"label_join_missing:{label_missing}")
    joined_label = frame["label_join_indicator"].eq("both")
    mismatch = (
        frame.loc[joined_label, "event_false_repair_20d_label"].map(boolish).to_numpy()
        != frame.loc[joined_label, run_cfg["target_label_column"]].map(boolish).to_numpy()
    )
    mismatch_n = int(mismatch.sum())
    mismatch_rate = safe_div(mismatch_n, int(joined_label.sum()))
    diagnostics["label_consistency_mismatch_n"] = mismatch_n
    diagnostics["label_consistency_mismatch_rate"] = mismatch_rate
    if mismatch_rate > float(config["diagnostics"]["label_mismatch_rate_cap"]):
        failures.append(f"label_consistency_mismatch_rate:{mismatch_rate:.6f}")

    membership_agg = prepare_membership(membership)
    frame = frame.merge(
        membership_agg,
        left_on="binding_canonical_event_id",
        right_on="canonical_event_id",
        how="left",
        suffixes=("", "_membership"),
    )
    frame["bridge_membership_missing_flag"] = frame["bridge_membership_row_n"].isna()
    frame["bridge_membership_row_n"] = frame["bridge_membership_row_n"].fillna(0).astype(int)
    frame["bridge_positive_flag"] = frame["bridge_positive_flag"].map(boolish)

    bool_cols = [
        "selected_fast_fail_10_label",
        run_cfg["target_label_column"],
        "selected_cost_bad_10_20_target",
        "winner_120",
        "E1_missed_winner_flag",
        "bridge_positive_flag",
        "event_false_repair_20d_label",
    ]
    for col in bool_cols:
        if col in frame.columns:
            frame[col] = frame[col].map(boolish)
    frame["final_sample_weight"] = pd.to_numeric(frame["final_sample_weight"], errors="coerce")
    frame["mfe_20d"] = pd.to_numeric(frame["mfe_20d"], errors="coerce")
    frame["confirm_20_label"] = pd.to_numeric(frame["confirm_20_label"], errors="coerce")
    frame["false_repair_non_winner_flag"] = frame[run_cfg["target_label_column"]] & ~frame["winner_120"]
    return frame, failures, diagnostics


def feature_columns(feature_contract: pd.DataFrame, feature_matrix: pd.DataFrame) -> tuple[list[str], list[str]]:
    contract = feature_contract.copy()
    dtype = contract["feature_dtype"].astype(str).str.lower()
    numeric_dtype = dtype.str.contains("float|int|bool|numeric", regex=True)
    allowed = contract.loc[
        contract["allowed_for_09C_flag"].map(boolish) & contract["t0_visible_flag"].map(boolish) & numeric_dtype
    ].copy()
    cols = [
        str(feature)
        for feature in allowed["feature_id"].astype(str).tolist()
        if str(feature) in feature_matrix.columns and str(feature) not in FORBIDDEN_FEATURE_COLUMNS
    ]
    missing = sorted(set(allowed["feature_id"].astype(str)) - set(cols) - FORBIDDEN_FEATURE_COLUMNS)
    return cols, missing


def no_overlap_feature_columns(feature_cols: list[str], feature_contract: pd.DataFrame) -> tuple[list[str], list[str]]:
    contract = feature_contract.set_index("feature_id", drop=False)
    kept: list[str] = []
    dropped: list[str] = []
    for col in feature_cols:
        if col not in contract.index:
            continue
        value = contract.loc[col, "label_mechanism_overlap_type"]
        if pd.isna(value) or str(value).strip().lower() in {"", "none", "null", "nan"}:
            kept.append(col)
        else:
            dropped.append(col)
    return kept, dropped


def fit_preprocess(train: pd.DataFrame, feature_cols: list[str]) -> tuple[list[str], dict[str, float], dict[str, float], int, int]:
    used: list[str] = []
    medians: dict[str, float] = {}
    iqrs: dict[str, float] = {}
    missing_drop = 0
    constant_drop = 0
    for col in feature_cols:
        values = pd.to_numeric(train[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        clean = values.dropna()
        if clean.empty:
            missing_drop += 1
            continue
        median = float(clean.median())
        iqr = float(clean.quantile(0.75) - clean.quantile(0.25))
        if not np.isfinite(iqr) or iqr == 0:
            constant_drop += 1
            continue
        used.append(col)
        medians[col] = median
        iqrs[col] = iqr
    return used, medians, iqrs, missing_drop, constant_drop


def transform_features(frame: pd.DataFrame, feature_cols: list[str], medians: dict[str, float], iqrs: dict[str, float]) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for col in feature_cols:
        values = pd.to_numeric(frame[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        out[col] = (values.fillna(medians[col]) - medians[col]) / iqrs[col]
    return out


def fit_score_model(
    frame: pd.DataFrame,
    feature_cols: list[str],
    config: dict[str, Any],
    ablation_id: str,
    fit_mask: pd.Series | None = None,
    score_mask: pd.Series | None = None,
) -> tuple[ModelResult, dict[str, Any]]:
    run_cfg = config["run"]
    model_cfg = config["model"]
    if fit_mask is None:
        fit_mask = frame["split"].eq(run_cfg["fit_split"])
    if score_mask is None:
        score_mask = pd.Series(True, index=frame.index)
    train = frame.loc[fit_mask].copy()
    used, medians, iqrs, missing_drop, constant_drop = fit_preprocess(train, feature_cols)
    model_id = model_cfg["model_id"]
    empty_scores = pd.Series(np.nan, index=frame.index)
    if not used:
        return (
            ModelResult(model_id, ablation_id, tuple(), len(feature_cols), constant_drop, missing_drop, empty_scores, "input_blocked_no_features"),
            {"feature_n_input": len(feature_cols), "feature_n_used": 0},
        )
    y = train[run_cfg["target_label_column"]].astype(int)
    weights = train["final_sample_weight"].astype(float)
    valid = weights.gt(0) & y.notna()
    if y.loc[valid].nunique() < 2:
        return (
            ModelResult(model_id, ablation_id, tuple(used), len(feature_cols), constant_drop, missing_drop, empty_scores, "input_blocked_single_class"),
            {"feature_n_input": len(feature_cols), "feature_n_used": len(used)},
        )
    model = LogisticRegression(
        penalty=str(model_cfg["penalty"]),
        C=float(model_cfg["C"]),
        solver=str(model_cfg["solver"]),
        max_iter=int(model_cfg["max_iter"]),
        random_state=int(model_cfg["random_state"]),
        class_weight=model_cfg.get("class_weight"),
    )
    model.fit(transform_features(train.loc[valid], used, medians, iqrs), y.loc[valid], sample_weight=weights.loc[valid])
    scores = empty_scores.copy()
    scores.loc[score_mask] = model.predict_proba(transform_features(frame.loc[score_mask], used, medians, iqrs))[:, 1]
    return (
        ModelResult(model_id, ablation_id, tuple(used), len(feature_cols), constant_drop, missing_drop, scores, "pass"),
        {"feature_n_input": len(feature_cols), "feature_n_used": len(used)},
    )


def rank_series(order: pd.Index) -> pd.Series:
    return pd.Series(np.arange(1, len(order) + 1), index=order)


def selected_capacities(power_config: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    component = config["run"]["target_component"]
    capacities = power_config.loc[power_config["component_id"].astype(str).eq(component)].copy()
    capacities["reject_fraction"] = capacities["reject_fraction"].astype(float)
    return capacities.sort_values(["reject_fraction", "capacity_id"], ascending=[False, True], kind="mergesort")


def bridge_gate_binding(part: pd.DataFrame, bridge_winner_n: int, config: dict[str, Any]) -> tuple[bool, int, float]:
    missing_n = int(part["bridge_membership_missing_flag"].map(boolish).sum())
    missing_rate = safe_div(missing_n, len(part))
    diag = config["diagnostics"]
    binding = (
        bridge_winner_n >= int(diag["bridge_winner_min_for_binding_gate"])
        and missing_rate <= float(diag["bridge_membership_missing_rate_cap_for_binding_gate"])
    )
    return bool(binding), missing_n, missing_rate


def compute_split_capacity_metrics(
    part: pd.DataFrame,
    candidate_rej: pd.Series,
    random_rej: pd.Series,
    model_id: str,
    ablation_id: str,
    capacity_id: str,
    threshold_id: str,
    reject_fraction: float,
    power_lookup: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    run_cfg = config["run"]
    utility = config["utility"]
    target = part[run_cfg["target_label_column"]].map(boolish)
    false_non_winner = part["false_repair_non_winner_flag"].map(boolish)
    winner = part["winner_120"].map(boolish)
    e1 = part["E1_missed_winner_flag"].map(boolish)
    bridge_winner = winner & part["bridge_positive_flag"].map(boolish)
    candidate_rej = candidate_rej.reindex(part.index).fillna(False).astype(bool)
    random_rej = random_rej.reindex(part.index).fillna(False).astype(bool)
    sample_n = int(len(part))
    reject_n = int(candidate_rej.sum())
    false_positive_n = int(target.sum())
    winner_n = int(winner.sum())
    e1_n = int(e1.sum())
    bridge_n = int(bridge_winner.sum())
    bridge_binding, bridge_missing_n, bridge_missing_rate = bridge_gate_binding(part, bridge_n, config)

    cand_false = int((candidate_rej & target).sum())
    cand_false_non_winner = int((candidate_rej & false_non_winner).sum())
    cand_winner = int((candidate_rej & winner).sum())
    cand_e1 = int((candidate_rej & e1).sum())
    cand_bridge = int((candidate_rej & bridge_winner).sum())
    rand_false = int((random_rej & target).sum())
    rand_false_non_winner = int((random_rej & false_non_winner).sum())
    rand_winner = int((random_rej & winner).sum())
    capture_rate = safe_div(cand_false, false_positive_n)
    random_capture = safe_div(rand_false, false_positive_n)
    capture_lift = capture_rate - random_capture
    precision = safe_div(cand_false, reject_n)
    wrong_kill = safe_div(cand_winner, winner_n)
    winner_retention = 1 - wrong_kill if not pd.isna(wrong_kill) else np.nan
    e1_wrong = safe_div(cand_e1, e1_n)
    e1_retention = 1 - e1_wrong if not pd.isna(e1_wrong) else np.nan
    bridge_wrong = safe_div(cand_bridge, bridge_n)
    bridge_retention = 1 - bridge_wrong if not pd.isna(bridge_wrong) else np.nan

    valid_exposure = part["active_interval_calendar_day_n"].notna() & part["active_interval_calendar_day_n"].gt(0)
    exposure_before = float(part.loc[false_non_winner & valid_exposure, "active_interval_calendar_day_n"].sum())
    exposure_rejected = float(part.loc[false_non_winner & candidate_rej & valid_exposure, "active_interval_calendar_day_n"].sum())
    random_exposure_rejected = float(part.loc[false_non_winner & random_rej & valid_exposure, "active_interval_calendar_day_n"].sum())
    exposure_reduction = safe_div(exposure_rejected, exposure_before)
    random_exposure_reduction = safe_div(random_exposure_rejected, exposure_before)
    exposure_lift = exposure_reduction - random_exposure_reduction
    all_rejected_exposure = float(part.loc[candidate_rej & valid_exposure, "active_interval_calendar_day_n"].sum())
    winner_rejected_exposure = float(part.loc[candidate_rej & winner & valid_exposure, "active_interval_calendar_day_n"].sum())
    invalid_n = int((~valid_exposure).sum())
    invalid_rate = safe_div(invalid_n, sample_n)

    winner_excess = max(0.0, wrong_kill - float(utility["wrong_kill_rate_cap"])) if not pd.isna(wrong_kill) else np.nan
    e1_excess = (
        max(0.0, e1_wrong - float(utility["e1_missed_wrong_kill_rate_cap"])) if not pd.isna(e1_wrong) else np.nan
    )
    bridge_excess = 0.0
    if bridge_binding:
        bridge_excess = (
            max(0.0, bridge_wrong - float(utility["bridge_wrong_kill_rate_cap"])) if not pd.isna(bridge_wrong) else np.nan
        )
    train_selection_utility = (
        float(utility["false_repair_capture_weight"]) * capture_lift
        + float(utility["exposure_days_reduction_weight"]) * exposure_lift
        - float(utility["winner_injury_excess_weight"]) * winner_excess
        - float(utility["e1_missed_injury_excess_weight"]) * e1_excess
        - float(utility["bridge_injury_excess_weight"]) * bridge_excess
    )

    power_row = power_lookup.get((str(part["split"].iloc[0]), capacity_id), {})
    reasons: list[str] = []
    if not boolish(power_row.get("false_repair_ml_supported_gate_allowed", False)):
        reasons.append("false_repair_ml_supported_gate_allowed")
    if int(power_row.get("post_dedup_false_repair_positive_n", false_positive_n)) < 300:
        reasons.append("post_dedup_false_repair_positive_n")
    if int(power_row.get("post_dedup_winner_n", winner_n)) < 100:
        reasons.append("post_dedup_winner_n")
    if str(power_row.get("e1_missed_proxy_status", "")) == "episode_membership_proxy_input_blocked":
        reasons.append("e1_missed_proxy_status")
    if winner_retention < float(utility["winner_retention_floor"]):
        reasons.append("winner_retention")
    if wrong_kill > float(utility["wrong_kill_rate_cap"]):
        reasons.append("wrong_kill_rate")
    if e1_retention < float(utility["e1_missed_retention_floor"]):
        reasons.append("e1_missed_retention")
    if bridge_binding and bridge_retention < float(utility["bridge_retention_floor"]):
        reasons.append("bridge_retention")
    if capture_lift <= 0:
        reasons.append("false_repair_capture_lift_vs_random")
    if exposure_lift < 0:
        reasons.append("exposure_days_lift_vs_random")
    if train_selection_utility <= 0:
        reasons.append("train_selection_utility")

    power_metrics = {
        "model_id": model_id,
        "ablation_id": ablation_id,
        "population_id": part["population_id"].iloc[0],
        "denominator_id": part["denominator_id"].iloc[0],
        "split": part["split"].iloc[0],
        "capacity_id": capacity_id,
        "threshold_id": threshold_id,
        "sample_n": sample_n,
        "reject_n": reject_n,
        "reject_fraction_actual": safe_div(reject_n, sample_n),
        "false_repair_positive_n": false_positive_n,
        "winner_n": winner_n,
        "e1_missed_winner_n": e1_n,
        "bridge_winner_n": bridge_n,
        "candidate_rejected_false_repair_positive_n": cand_false,
        "candidate_rejected_false_repair_non_winner_n": cand_false_non_winner,
        "candidate_rejected_winner_n": cand_winner,
        "candidate_rejected_e1_missed_winner_n": cand_e1,
        "candidate_rejected_bridge_winner_n": cand_bridge,
        "random_rejected_false_repair_positive_n": rand_false,
        "random_rejected_false_repair_non_winner_n": rand_false_non_winner,
        "random_rejected_winner_n": rand_winner,
        "false_repair_capture_rate": capture_rate,
        "random_false_repair_capture_rate": random_capture,
        "false_repair_capture_lift_vs_random": capture_lift,
        "candidate_precision": precision,
        "winner_retention": winner_retention,
        "wrong_kill_rate": wrong_kill,
        "e1_missed_retention": e1_retention,
        "e1_missed_wrong_kill_rate": e1_wrong,
        "bridge_retention": bridge_retention,
        "bridge_wrong_kill_rate": bridge_wrong,
        "bridge_gate_binding_flag": bridge_binding,
        "train_selection_utility": train_selection_utility,
        "supported_row_flag": not reasons,
        "row_block_reason": ";".join(reasons) if reasons else "pass",
    }
    exposure_metrics = {
        "model_id": model_id,
        "ablation_id": ablation_id,
        "split": part["split"].iloc[0],
        "capacity_id": capacity_id,
        "false_repair_non_winner_exposure_days_before": exposure_before,
        "false_repair_non_winner_exposure_days_rejected": exposure_rejected,
        "false_repair_non_winner_exposure_days_reduction": exposure_reduction,
        "random_false_repair_non_winner_exposure_days_reduction": random_exposure_reduction,
        "exposure_days_lift_vs_random": exposure_lift,
        "all_rejected_exposure_days": all_rejected_exposure,
        "winner_rejected_exposure_days": winner_rejected_exposure,
        "exposure_interval_invalid_n": invalid_n,
        "exposure_interval_invalid_rate": invalid_rate,
    }
    retention_metrics = {
        "model_id": model_id,
        "ablation_id": ablation_id,
        "split": part["split"].iloc[0],
        "capacity_id": capacity_id,
        "winner_n": winner_n,
        "candidate_rejected_winner_n": cand_winner,
        "winner_retention": winner_retention,
        "e1_missed_winner_n": e1_n,
        "candidate_rejected_e1_missed_winner_n": cand_e1,
        "e1_missed_retention": e1_retention,
        "e1_missed_wrong_kill_rate": e1_wrong,
        "bridge_winner_n": bridge_n,
        "candidate_rejected_bridge_winner_n": cand_bridge,
        "bridge_retention": bridge_retention,
        "bridge_wrong_kill_rate": bridge_wrong,
        "bridge_gate_binding_flag": bridge_binding,
        "bridge_membership_missing_n": bridge_missing_n,
        "bridge_membership_missing_rate": bridge_missing_rate,
        "retention_status": "pass" if not reasons or all(r not in reasons for r in ["winner_retention", "wrong_kill_rate", "e1_missed_retention", "bridge_retention"]) else "fail",
    }
    aux = {
        "candidate_rejected_flag": candidate_rej,
        "random_baseline_rejected_flag": random_rej,
        "reject_n": reject_n,
    }
    return power_metrics, exposure_metrics, retention_metrics, aux


def build_mfe_rows(
    part: pd.DataFrame,
    flags: dict[str, pd.Series],
    model_id: str,
    ablation_id: str,
    capacity_id: str,
    label_mismatch_n: int,
    label_mismatch_rate: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket, flag in flags.items():
        mask = flag.reindex(part.index).fillna(False).astype(bool)
        sub = part.loc[mask]
        confirm = pd.to_numeric(sub["confirm_20_label"], errors="coerce")
        mfe = pd.to_numeric(sub["mfe_20d"], errors="coerce")
        rows.append(
            {
                "model_id": model_id,
                "ablation_id": ablation_id,
                "split": part["split"].iloc[0] if not part.empty else "",
                "capacity_id": capacity_id,
                "bucket": bucket,
                "row_n": int(len(sub)),
                "confirm_20_positive_n": int(confirm.fillna(0).gt(0).sum()),
                "confirm_20_positive_rate": safe_div(int(confirm.fillna(0).gt(0).sum()), len(sub)),
                "mfe_20d_mean": float(mfe.mean()) if len(sub) else np.nan,
                "mfe_20d_median": float(mfe.median()) if len(sub) else np.nan,
                "mfe_20d_p25": float(mfe.quantile(0.25)) if len(sub) else np.nan,
                "mfe_20d_p75": float(mfe.quantile(0.75)) if len(sub) else np.nan,
                "label_consistency_mismatch_n": label_mismatch_n,
                "label_consistency_mismatch_rate": label_mismatch_rate,
            }
        )
    return rows


def build_power_lookup(power: pd.DataFrame, config: dict[str, Any]) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    run_cfg = config["run"]
    subset = power.loc[
        (power["population_id"].astype(str).eq(run_cfg["selected_population_id"]))
        & (power["rule_arm_id"].astype(str).eq(run_cfg["selected_rule_arm_id"]))
        & (power["input_denominator_id"].astype(str).eq(run_cfg["input_denominator_id"]))
        & (power["denominator_id"].astype(str).eq(run_cfg["denominator_id"]))
        & (~power["readout_only_flag"].map(boolish))
    ].copy()
    failures: list[str] = []
    if subset.duplicated(["split", "capacity_id", "threshold_id"]).any():
        failures.append("false_repair_power_audit_duplicate_rows")
    return subset.set_index(["split", "capacity_id"]).to_dict("index"), failures


def validate_power_counts(frame: pd.DataFrame, power: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    run_cfg = config["run"]
    subset = power.loc[
        (power["population_id"].astype(str).eq(run_cfg["selected_population_id"]))
        & (power["rule_arm_id"].astype(str).eq(run_cfg["selected_rule_arm_id"]))
        & (power["input_denominator_id"].astype(str).eq(run_cfg["input_denominator_id"]))
        & (power["denominator_id"].astype(str).eq(run_cfg["denominator_id"]))
        & (~power["readout_only_flag"].map(boolish))
    ].copy()
    failures: list[str] = []
    for split in run_cfg["readout_splits"]:
        part = frame.loc[frame["split"].eq(split)]
        rows = subset.loc[subset["split"].eq(split)]
        if rows.empty:
            failures.append(f"false_repair_power_missing_split:{split}")
            continue
        expected = {
            "post_dedup_sample_n": int(len(part)),
            "post_dedup_false_repair_positive_n": int(part[run_cfg["target_label_column"]].map(boolish).sum()),
            "post_dedup_winner_n": int(part["winner_120"].map(boolish).sum()),
            "post_dedup_E1_missed_winner_n": int(part["E1_missed_winner_flag"].map(boolish).sum()),
        }
        for col, value in expected.items():
            if not rows[col].astype(int).eq(value).all():
                failures.append(f"false_repair_power_count_mismatch:{split}:{col}")
    return failures


def build_frontiers(
    frame: pd.DataFrame,
    model_results: list[ModelResult],
    capacities: pd.DataFrame,
    power_lookup: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
    diagnostics: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seed = int(config["run"]["random_seed"])
    run_cfg = config["run"]
    power_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    retention_rows: list[dict[str, Any]] = []
    mfe_rows: list[dict[str, Any]] = []
    score_frames: list[pd.DataFrame] = []

    for result in model_results:
        scored = frame.copy()
        scored["candidate_false_repair_score"] = result.scores
        for capacity in capacities.to_dict("records"):
            capacity_id = str(capacity["capacity_id"])
            threshold_id = str(capacity["threshold_id"])
            reject_fraction = float(capacity["reject_fraction"])
            for split in SPLIT_ORDER:
                part = scored.loc[scored["split"].eq(split)].copy()
                if part.empty:
                    continue
                reject_n = int(math.ceil(len(part) * reject_fraction))
                candidate_order = part.sort_values(
                    ["candidate_false_repair_score", "input_event_key"],
                    ascending=[False, True],
                    kind="mergesort",
                ).index
                random_order = (
                    part.assign(random_key=part["input_event_key"].map(lambda key: random_key(str(key), capacity_id, seed)))
                    .sort_values(["random_key", "input_event_key"], ascending=[True, True], kind="mergesort")
                    .index
                )
                candidate_rank = rank_series(candidate_order)
                random_rank = rank_series(random_order)
                candidate_rej = candidate_rank.le(reject_n)
                random_rej = random_rank.le(reject_n)
                power_metrics, exposure_metrics, retention_metrics, aux = compute_split_capacity_metrics(
                    part,
                    candidate_rej,
                    random_rej,
                    result.model_id,
                    result.ablation_id,
                    capacity_id,
                    threshold_id,
                    reject_fraction,
                    power_lookup,
                    config,
                )
                power_rows.append(power_metrics)
                exposure_rows.append(exposure_metrics)
                retention_rows.append(retention_metrics)
                mfe_rows.extend(
                    build_mfe_rows(
                        part,
                        {
                            "candidate_rejected": candidate_rej,
                            "candidate_accepted": ~candidate_rej,
                            "random_rejected": random_rej,
                        },
                        result.model_id,
                        result.ablation_id,
                        capacity_id,
                        int(diagnostics.get("label_consistency_mismatch_n", 0)),
                        float(diagnostics.get("label_consistency_mismatch_rate", np.nan)),
                    )
                )
                score_part = part[
                    [
                        "population_id",
                        "denominator_id",
                        "split",
                        "input_event_key",
                        "sample_id",
                        "selected_target_id",
                        "binding_canonical_event_id",
                        "instrument",
                        "event_t0_date",
                        "admitted_event_id",
                        run_cfg["target_label_column"],
                        "false_repair_non_winner_flag",
                        "selected_fast_fail_10_label",
                        "winner_120",
                        "E1_missed_winner_flag",
                        "bridge_positive_flag",
                        "confirm_20_label",
                        "mfe_20d",
                        "final_sample_weight",
                        "active_interval_calendar_day_n",
                        "candidate_false_repair_score",
                    ]
                ].copy()
                score_part.insert(0, "reject_fraction", reject_fraction)
                score_part.insert(0, "threshold_id", threshold_id)
                score_part.insert(0, "capacity_id", capacity_id)
                score_part.insert(0, "ablation_id", result.ablation_id)
                score_part.insert(0, "model_id", result.model_id)
                score_part["candidate_rank"] = candidate_rank.reindex(part.index).astype(int).to_numpy()
                score_part["random_baseline_rank"] = random_rank.reindex(part.index).astype(int).to_numpy()
                score_part["candidate_rejected_flag"] = candidate_rej.reindex(part.index).astype(bool).to_numpy()
                score_part["random_baseline_rejected_flag"] = random_rej.reindex(part.index).astype(bool).to_numpy()
                score_part["fast_fail_rejected_flag"] = False
                score_part["cascade_bucket"] = "not_evaluated"
                score_frames.append(score_part.rename(columns={run_cfg["target_label_column"]: "frozen_false_repair_20d_label"}))

    power_gate = pd.DataFrame(power_rows, columns=POWER_GATE_COLUMNS)
    exposure = pd.DataFrame(exposure_rows, columns=EXPOSURE_COLUMNS)
    retention = pd.DataFrame(retention_rows, columns=RETENTION_COLUMNS)
    mfe = pd.DataFrame(mfe_rows, columns=MFE_COLUMNS)
    scores = pd.concat(score_frames, ignore_index=True) if score_frames else empty_frame(SCORE_COLUMNS)
    frontier = build_threshold_frontier(power_gate, exposure)
    return power_gate, frontier, exposure, retention, mfe, scores


def build_threshold_frontier(power_gate: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    merged = power_gate.merge(
        exposure[["model_id", "ablation_id", "split", "capacity_id", "exposure_days_lift_vs_random"]],
        on=["model_id", "ablation_id", "split", "capacity_id"],
        how="left",
    )
    for (model_id, ablation_id, capacity_id, threshold_id), group in merged.groupby(
        ["model_id", "ablation_id", "capacity_id", "threshold_id"], dropna=False
    ):
        by_split = group.set_index("split")
        validation_reject = by_split.loc["validation", "reject_fraction_actual"] if "validation" in by_split.index else np.nan
        robustness_reject = by_split.loc["robustness", "reject_fraction_actual"] if "robustness" in by_split.index else np.nan
        if pd.isna(validation_reject) or pd.isna(robustness_reject):
            oos_spread = np.nan
        else:
            oos_spread = abs(float(validation_reject) - float(robustness_reject))
        rows.append(
            {
                "model_id": model_id,
                "ablation_id": ablation_id,
                "capacity_id": capacity_id,
                "threshold_id": threshold_id,
                "selected_flag": False,
                "selection_rank": np.nan,
                "train_selection_utility": by_split.loc["train", "train_selection_utility"] if "train" in by_split.index else np.nan,
                "selected_train_constrained_utility": np.nan,
                "train_false_repair_capture_lift_vs_random": by_split.loc["train", "false_repair_capture_lift_vs_random"] if "train" in by_split.index else np.nan,
                "train_exposure_days_lift_vs_random": by_split.loc["train", "exposure_days_lift_vs_random"] if "train" in by_split.index else np.nan,
                "train_winner_retention": by_split.loc["train", "winner_retention"] if "train" in by_split.index else np.nan,
                "train_e1_missed_retention": by_split.loc["train", "e1_missed_retention"] if "train" in by_split.index else np.nan,
                "train_bridge_retention": by_split.loc["train", "bridge_retention"] if "train" in by_split.index else np.nan,
                "validation_false_repair_capture_lift_vs_random": by_split.loc["validation", "false_repair_capture_lift_vs_random"] if "validation" in by_split.index else np.nan,
                "validation_winner_retention": by_split.loc["validation", "winner_retention"] if "validation" in by_split.index else np.nan,
                "robustness_false_repair_capture_lift_vs_random": by_split.loc["robustness", "false_repair_capture_lift_vs_random"] if "robustness" in by_split.index else np.nan,
                "robustness_winner_retention": by_split.loc["robustness", "winner_retention"] if "robustness" in by_split.index else np.nan,
                "oos_rejected_fraction_spread": oos_spread,
                "train_cv_selected_reject_fraction_std": np.nan,
                "decision_block_reason": "",
            }
        )
    return pd.DataFrame(rows, columns=FRONTIER_COLUMNS)


def select_operating_point(power_gate: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    train = power_gate.loc[power_gate["split"].eq(config["run"]["fit_split"]) & power_gate["supported_row_flag"]].copy()
    if train.empty:
        return {"selected": False, "reason": "no_train_supported_capacity"}
    train = train.sort_values(
        [
            "train_selection_utility",
            "wrong_kill_rate",
            "false_repair_capture_lift_vs_random",
            "reject_fraction_actual",
            "capacity_id",
            "ablation_id",
            "model_id",
        ],
        ascending=[False, True, False, True, True, True, True],
        kind="mergesort",
    )
    selected = train.iloc[0].to_dict()
    selected["selected"] = True
    selected["reason"] = "selected_by_train_selection_utility"
    return selected


def compute_train_cv_instability(
    frame: pd.DataFrame,
    selected: dict[str, Any],
    feature_cols_by_ablation: dict[str, list[str]],
    capacities: pd.DataFrame,
    power_lookup: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
) -> pd.DataFrame:
    if not selected.get("selected"):
        return pd.DataFrame(
            [
                {
                    "fold_id": "summary",
                    "fold_start_date": "",
                    "fold_end_date": "",
                    "fit_rows": 0,
                    "holdout_rows": 0,
                    "holdout_false_repair_positive_n": 0,
                    "holdout_winner_n": 0,
                    "selected_capacity_id": "",
                    "selected_reject_fraction": np.nan,
                    "fold_train_selection_utility": np.nan,
                    "fold_status": "not_selected",
                }
            ],
            columns=INSTABILITY_COLUMNS,
        )
    train = frame.loc[frame["split"].eq(config["run"]["fit_split"])].copy()
    train = train.sort_values(["event_t0_date", "input_event_key"], kind="mergesort").reset_index(drop=False)
    fold_count = int(config["diagnostics"]["train_cv_fold_count"])
    embargo_days = int(config["diagnostics"]["train_cv_embargo_calendar_days"])
    folds = np.array_split(train.index.to_numpy(), fold_count)
    rows: list[dict[str, Any]] = []
    selected_fractions: list[float] = []
    powered_fold_n = 0
    feature_cols = feature_cols_by_ablation[str(selected["ablation_id"])]
    for fold_i, fold_idx in enumerate(folds, start=1):
        holdout = train.loc[fold_idx].copy()
        if holdout.empty:
            continue
        start_date = pd.to_datetime(holdout["event_t0_date"]).min()
        end_date = pd.to_datetime(holdout["event_t0_date"]).max()
        embargo_start = start_date - timedelta(days=embargo_days)
        embargo_end = end_date + timedelta(days=embargo_days)
        event_dates = pd.to_datetime(train["event_t0_date"])
        fit = train.loc[(event_dates < embargo_start) | (event_dates > embargo_end)].copy()
        fit_mask = frame.index.isin(fit["index"])
        score_mask = frame.index.isin(holdout["index"])
        pos_n = int(holdout[config["run"]["target_label_column"]].map(boolish).sum())
        winner_n = int(holdout["winner_120"].map(boolish).sum())
        status = "pass"
        selected_capacity_id = ""
        selected_fraction = np.nan
        utility_value = np.nan
        if len(fit) == 0 or pos_n == 0 or winner_n == 0:
            status = "insufficient_fold_power"
        else:
            result, _ = fit_score_model(frame, feature_cols, config, str(selected["ablation_id"]), fit_mask=fit_mask, score_mask=score_mask)
            if result.status != "pass":
                status = result.status
            else:
                scored = frame.loc[score_mask].copy()
                scored["candidate_false_repair_score"] = result.scores.loc[score_mask]
                fold_rows = []
                for capacity in capacities.to_dict("records"):
                    capacity_id = str(capacity["capacity_id"])
                    reject_fraction = float(capacity["reject_fraction"])
                    reject_n = int(math.ceil(len(scored) * reject_fraction))
                    order = scored.sort_values(
                        ["candidate_false_repair_score", "input_event_key"],
                        ascending=[False, True],
                        kind="mergesort",
                    ).index
                    random_order = (
                        scored.assign(
                            random_key=scored["input_event_key"].map(
                                lambda key: random_key(str(key), capacity_id, int(config["run"]["random_seed"]))
                            )
                        )
                        .sort_values(["random_key", "input_event_key"], ascending=[True, True], kind="mergesort")
                        .index
                    )
                    metrics, _, _, _ = compute_split_capacity_metrics(
                        scored,
                        rank_series(order).le(reject_n),
                        rank_series(random_order).le(reject_n),
                        result.model_id,
                        result.ablation_id,
                        capacity_id,
                        str(capacity["threshold_id"]),
                        reject_fraction,
                        power_lookup,
                        config,
                    )
                    fold_rows.append(metrics)
                fold_frame = pd.DataFrame(fold_rows)
                supported = fold_frame.loc[fold_frame["supported_row_flag"]].copy()
                if supported.empty:
                    status = "no_supported_capacity"
                else:
                    chosen = supported.sort_values(
                        [
                            "train_selection_utility",
                            "wrong_kill_rate",
                            "false_repair_capture_lift_vs_random",
                            "reject_fraction_actual",
                            "capacity_id",
                        ],
                        ascending=[False, True, False, True, True],
                        kind="mergesort",
                    ).iloc[0]
                    selected_capacity_id = str(chosen["capacity_id"])
                    selected_fraction = float(chosen["reject_fraction_actual"])
                    utility_value = float(chosen["train_selection_utility"])
                    selected_fractions.append(selected_fraction)
                    powered_fold_n += 1
        rows.append(
            {
                "fold_id": f"fold_{fold_i}",
                "fold_start_date": start_date.date().isoformat(),
                "fold_end_date": end_date.date().isoformat(),
                "fit_rows": int(len(fit)) if "fit" in locals() else 0,
                "holdout_rows": int(len(holdout)),
                "holdout_false_repair_positive_n": pos_n,
                "holdout_winner_n": winner_n,
                "selected_capacity_id": selected_capacity_id,
                "selected_reject_fraction": selected_fraction,
                "fold_train_selection_utility": utility_value,
                "fold_status": status,
            }
        )
    std = float(np.std(selected_fractions, ddof=0)) if selected_fractions else np.nan
    summary_status = "pass" if powered_fold_n >= 4 else "insufficient_train_cv_power"
    rows.append(
        {
            "fold_id": "summary",
            "fold_start_date": "",
            "fold_end_date": "",
            "fit_rows": int(sum(row["fit_rows"] for row in rows)),
            "holdout_rows": int(sum(row["holdout_rows"] for row in rows)),
            "holdout_false_repair_positive_n": int(sum(row["holdout_false_repair_positive_n"] for row in rows)),
            "holdout_winner_n": int(sum(row["holdout_winner_n"] for row in rows)),
            "selected_capacity_id": "",
            "selected_reject_fraction": std,
            "fold_train_selection_utility": np.nan,
            "fold_status": summary_status,
        }
    )
    return pd.DataFrame(rows, columns=INSTABILITY_COLUMNS)


def selected_10b_gate(manifest_10b: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    cascade = config["cascade"]
    expected = {
        "model_id": cascade["expected_10b_model_id"],
        "ablation_id": cascade["expected_10b_ablation_id"],
        "capacity_id": cascade["expected_10b_capacity_id"],
        "threshold_id": cascade["expected_10b_threshold_id"],
        "reject_fraction": float(cascade["expected_10b_reject_fraction"]),
    }
    if not manifest_10b:
        actual = {
            "model_id": None,
            "ablation_id": None,
            "population_id": None,
            "denominator_id": None,
            "capacity_id": None,
            "threshold_id": None,
            "reject_fraction": None,
        }
        actual["expected"] = expected
        actual["match_flag"] = False
        actual["available_flag"] = False
        actual["failure_reason"] = "10B_manifest_missing_supported_only"
        return actual

    op = manifest_10b.get("selected_operating_point", {}) or {}
    actual = {
        "model_id": manifest_10b.get("selected_model_id"),
        "ablation_id": op.get("ablation_id", "full"),
        "population_id": manifest_10b.get("selected_population_id"),
        "denominator_id": manifest_10b.get("selected_denominator_id"),
        "capacity_id": manifest_10b.get("selected_capacity_id"),
        "threshold_id": manifest_10b.get("selected_threshold_id"),
        "reject_fraction": op.get("reject_fraction"),
    }
    actual_complete = all(actual.get(key) is not None for key in ["model_id", "population_id", "denominator_id", "capacity_id", "threshold_id"])
    reject_fraction_match = (
        is_finite_number(actual.get("reject_fraction"))
        and abs(float(actual["reject_fraction"]) - float(expected["reject_fraction"])) < 1e-12
    )
    match = (
        actual_complete
        and str(actual["model_id"]) == str(expected["model_id"])
        and str(actual["ablation_id"]) == str(expected["ablation_id"])
        and str(actual["capacity_id"]) == str(expected["capacity_id"])
        and str(actual["threshold_id"]) == str(expected["threshold_id"])
        and reject_fraction_match
    )
    actual["expected"] = expected
    actual["match_flag"] = bool(match)
    actual["available_flag"] = bool(actual_complete)
    actual["failure_reason"] = "" if actual_complete else "10B_manifest_selected_gate_incomplete"
    return actual


def merge_10b_flags(
    score_long: pd.DataFrame,
    tenb_scores: pd.DataFrame | None,
    gate: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    failures: list[str] = []
    if not gate.get("available_flag", False):
        failure = str(gate.get("failure_reason") or "10B_manifest_selected_gate_unavailable")
        failures.append(failure)
    if tenb_scores is None:
        failures.append("10B_scores_missing_supported_only")
    if failures:
        merged = score_long.copy()
        merged["fast_fail_rejected_flag"] = False
        merged["cascade_bucket"] = "10B_unavailable"
        return merged, sorted(set(failures))

    filtered = tenb_scores.loc[
        (tenb_scores["model_id"].astype(str).eq(str(gate["model_id"])))
        & (tenb_scores["ablation_id"].astype(str).eq(str(gate["ablation_id"])))
        & (tenb_scores["population_id"].astype(str).eq(str(gate["population_id"])))
        & (tenb_scores["denominator_id"].astype(str).eq(str(gate["denominator_id"])))
        & (tenb_scores["capacity_id"].astype(str).eq(str(gate["capacity_id"])))
        & (tenb_scores["threshold_id"].astype(str).eq(str(gate["threshold_id"])))
    ].copy()
    keys = ["input_event_key", "sample_id", "selected_target_id", "binding_canonical_event_id", "split"]
    if filtered.duplicated(keys).any():
        failures.append("10B_selected_scores_duplicate_rows")
    merged = score_long.merge(
        filtered[keys + ["candidate_rejected_flag"]].rename(
            columns={"candidate_rejected_flag": "fast_fail_rejected_flag_10b"}
        ),
        on=keys,
        how="left",
        indicator="tenb_join_indicator",
    )
    missing = int(merged["tenb_join_indicator"].ne("both").sum())
    if missing:
        failures.append(f"10B_selected_scores_join_missing:{missing}")
    merged["fast_fail_rejected_flag"] = merged["fast_fail_rejected_flag_10b"].fillna(False).map(boolish)
    false_repair_rej = merged["candidate_rejected_flag"].map(boolish)
    fast_fail_rej = merged["fast_fail_rejected_flag"].map(boolish)
    merged["cascade_bucket"] = np.select(
        [
            fast_fail_rej & false_repair_rej,
            fast_fail_rej & ~false_repair_rej,
            ~fast_fail_rej & false_repair_rej,
        ],
        ["both_rejected", "fast_fail_only_rejected", "false_repair_only_rejected"],
        default="accepted_by_cascade",
    )
    return merged.drop(columns=["fast_fail_rejected_flag_10b", "tenb_join_indicator"]), failures


def build_cascade_attribution(
    selected_scores: pd.DataFrame,
    note: str = "selected_10b_gate_plus_selected_10c_gate",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    for split, part in selected_scores.groupby("split", dropna=False):
        total_winner = int(part["winner_120"].map(boolish).sum())
        total_false_non_winner_exposure = float(
            part.loc[part["false_repair_non_winner_flag"].map(boolish), "active_interval_calendar_day_n"].sum()
        )
        for bucket, bucket_part in part.groupby("cascade_bucket", dropna=False):
            winner_n = int(bucket_part["winner_120"].map(boolish).sum())
            rows.append(
                {
                    "split": split,
                    "cascade_bucket": bucket,
                    "row_n": int(len(bucket_part)),
                    "false_repair_positive_n": int(bucket_part["frozen_false_repair_20d_label"].map(boolish).sum()),
                    "false_repair_non_winner_n": int(bucket_part["false_repair_non_winner_flag"].map(boolish).sum()),
                    "fast_fail_positive_n": int(bucket_part["selected_fast_fail_10_label"].map(boolish).sum()),
                    "winner_n": winner_n,
                    "e1_missed_winner_n": int(bucket_part["E1_missed_winner_flag"].map(boolish).sum()),
                    "bridge_winner_n": int(
                        (bucket_part["winner_120"].map(boolish) & bucket_part["bridge_positive_flag"].map(boolish)).sum()
                    ),
                    "false_repair_non_winner_exposure_days": float(
                        bucket_part.loc[
                            bucket_part["false_repair_non_winner_flag"].map(boolish),
                            "active_interval_calendar_day_n",
                        ].sum()
                    ),
                    "winner_retention_contribution": safe_div(total_winner - winner_n, total_winner),
                    "notes": note,
                }
            )
        cascade_rejected = part["cascade_bucket"].isin(
            ["both_rejected", "fast_fail_only_rejected", "false_repair_only_rejected"]
        )
        false_repair_only = part["cascade_bucket"].eq("false_repair_only_rejected")
        cascade_winner_retention = 1 - safe_div(int((cascade_rejected & part["winner_120"].map(boolish)).sum()), total_winner)
        false_only_exposure = float(
            part.loc[false_repair_only & part["false_repair_non_winner_flag"].map(boolish), "active_interval_calendar_day_n"].sum()
        )
        rows.append(
            {
                "split": split,
                "cascade_bucket": "total",
                "row_n": int(len(part)),
                "false_repair_positive_n": int(part["frozen_false_repair_20d_label"].map(boolish).sum()),
                "false_repair_non_winner_n": int(part["false_repair_non_winner_flag"].map(boolish).sum()),
                "fast_fail_positive_n": int(part["selected_fast_fail_10_label"].map(boolish).sum()),
                "winner_n": total_winner,
                "e1_missed_winner_n": int(part["E1_missed_winner_flag"].map(boolish).sum()),
                "bridge_winner_n": int((part["winner_120"].map(boolish) & part["bridge_positive_flag"].map(boolish)).sum()),
                "false_repair_non_winner_exposure_days": total_false_non_winner_exposure,
                "winner_retention_contribution": cascade_winner_retention,
                "notes": "total_pre_cascade_population",
            }
        )
        metrics[f"{split}_cascade_false_repair_positive_incremental_to_10b_n"] = int(
            (false_repair_only & part["frozen_false_repair_20d_label"].map(boolish)).sum()
        )
        metrics[f"{split}_cascade_false_repair_non_winner_exposure_days_reduction"] = safe_div(
            false_only_exposure, total_false_non_winner_exposure
        )
        metrics[f"{split}_cascade_winner_retention"] = cascade_winner_retention
    return pd.DataFrame(rows, columns=CASCADE_COLUMNS), metrics


def build_10b_only_cascade_base(score_long: pd.DataFrame) -> pd.DataFrame:
    keys = ["input_event_key", "sample_id", "selected_target_id", "binding_canonical_event_id", "split"]
    base = score_long.sort_values(["model_id", "ablation_id", "capacity_id", "input_event_key"], kind="mergesort")
    base = base.drop_duplicates(keys).copy()
    base["candidate_rejected_flag"] = False
    if "cascade_bucket" in base.columns and base["cascade_bucket"].astype(str).eq("10B_unavailable").any():
        base["cascade_bucket"] = "10B_unavailable"
    else:
        base["cascade_bucket"] = np.where(
            base["fast_fail_rejected_flag"].map(boolish),
            "fast_fail_only_rejected",
            "accepted_by_cascade",
        )
    return base


def append_cascade_mfe_rows(
    mfe: pd.DataFrame,
    cascade_scores: pd.DataFrame,
    selected: dict[str, Any],
    diagnostics: dict[str, Any],
) -> pd.DataFrame:
    if cascade_scores.empty:
        return mfe
    model_id = str(selected.get("model_id", "10B_only_cascade"))
    ablation_id = str(selected.get("ablation_id", "none"))
    capacity_id = str(selected.get("capacity_id", "10B_only"))
    extra_rows: list[dict[str, Any]] = []
    for _, part in cascade_scores.groupby("split", dropna=False):
        rejected = part["cascade_bucket"].isin(
            ["both_rejected", "fast_fail_only_rejected", "false_repair_only_rejected"]
        )
        extra_rows.extend(
            build_mfe_rows(
                part,
                {
                    "cascade_rejected": rejected,
                    "cascade_accepted": ~rejected,
                },
                model_id,
                ablation_id,
                capacity_id,
                int(diagnostics.get("label_consistency_mismatch_n", 0)),
                float(diagnostics.get("label_consistency_mismatch_rate", np.nan)),
            )
        )
    if not extra_rows:
        return mfe
    return pd.concat([mfe, pd.DataFrame(extra_rows, columns=MFE_COLUMNS)], ignore_index=True)


def build_09c_diagnostic(manifest_path: Path, report_path: Path) -> pd.DataFrame:
    rows = [
        {
            "diagnostic_source": "09C_manifest",
            "split": "all",
            "metric_id": "manifest_exists",
            "metric_value": float(manifest_path.is_file()),
            "comparison_note": "09C is diagnostic only for 10C",
        },
        {
            "diagnostic_source": "09C_report",
            "split": "all",
            "metric_id": "report_exists",
            "metric_value": float(report_path.is_file()),
            "comparison_note": "09C hybrid result must not feed 10C supported decision",
        },
    ]
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        rows.append(
            {
                "diagnostic_source": "09C_manifest",
                "split": "all",
                "metric_id": "decision_is_diagnostic_prior",
                "metric_value": 1.0 if "diagnostic" in str(manifest.get("decision", "")).lower() else 0.0,
                "comparison_note": str(manifest.get("decision", "")),
            }
        )
    return pd.DataFrame(rows, columns=DIAGNOSTIC_COLUMNS)


def mark_selected_frontier(
    frontier: pd.DataFrame,
    selected: dict[str, Any],
    cv_std: float,
    selected_constrained: float,
    block_reasons: list[str],
) -> pd.DataFrame:
    out = frontier.copy()
    if not selected.get("selected"):
        out["decision_block_reason"] = "not_selected"
        return out
    selected_mask = (
        out["model_id"].astype(str).eq(str(selected["model_id"]))
        & out["ablation_id"].astype(str).eq(str(selected["ablation_id"]))
        & out["capacity_id"].astype(str).eq(str(selected["capacity_id"]))
    )
    out = out.sort_values(["train_selection_utility", "capacity_id"], ascending=[False, True], kind="mergesort")
    out["selection_rank"] = np.arange(1, len(out) + 1)
    out["selected_flag"] = selected_mask
    out.loc[selected_mask, "selected_train_constrained_utility"] = selected_constrained
    out.loc[selected_mask, "train_cv_selected_reject_fraction_std"] = cv_std
    out.loc[selected_mask, "decision_block_reason"] = ";".join(block_reasons) if block_reasons else "pass"
    out.loc[~selected_mask, "decision_block_reason"] = "not_selected"
    return out[FRONTIER_COLUMNS]


def supported_gate_reasons(
    selected: dict[str, Any],
    selected_constrained_utility: float,
    cv_std: float,
    frontier: pd.DataFrame,
    cascade_metrics: dict[str, Any],
    cascade_failures: list[str],
    tenb_gate: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    if not selected.get("selected"):
        return [str(selected.get("reason", "not_selected"))]
    reasons: list[str] = []
    utility = config["utility"]
    if not is_finite_number(selected_constrained_utility) or selected_constrained_utility <= 0:
        reasons.append("selected_train_constrained_utility_non_positive")
    if not is_finite_number(cv_std) or cv_std > float(utility["train_cv_selected_reject_fraction_std_cap"]):
        reasons.append("train_cv_selected_reject_fraction_std")
    row = frontier.loc[
        (frontier["model_id"].astype(str).eq(str(selected["model_id"])))
        & (frontier["ablation_id"].astype(str).eq(str(selected["ablation_id"])))
        & (frontier["capacity_id"].astype(str).eq(str(selected["capacity_id"])))
    ]
    if not row.empty:
        one = row.iloc[0]
        if one["oos_rejected_fraction_spread"] > float(utility["oos_rejected_fraction_spread_cap"]):
            reasons.append("oos_rejected_fraction_spread")
        if one["validation_false_repair_capture_lift_vs_random"] < float(utility["oos_capture_lift_severe_reversal_floor"]):
            reasons.append("validation_false_repair_capture_lift_vs_random")
        if one["robustness_false_repair_capture_lift_vs_random"] < float(utility["oos_capture_lift_severe_reversal_floor"]):
            reasons.append("robustness_false_repair_capture_lift_vs_random")
        if one["validation_winner_retention"] < float(utility["oos_winner_retention_floor"]):
            reasons.append("validation_winner_retention")
        if one["robustness_winner_retention"] < float(utility["oos_winner_retention_floor"]):
            reasons.append("robustness_winner_retention")
    if not tenb_gate.get("match_flag", False):
        reasons.append("10B_selected_gate_mismatch")
    reasons.extend(cascade_failures)
    if config["cascade"]["require_10b_for_supported_decision"]:
        if cascade_metrics.get("train_cascade_false_repair_positive_incremental_to_10b_n", 0) <= 0:
            reasons.append("cascade_false_repair_positive_incremental_to_10b_n")
        exposure_reduction = cascade_metrics.get("train_cascade_false_repair_non_winner_exposure_days_reduction", np.nan)
        if not is_finite_number(exposure_reduction) or exposure_reduction <= 0:
            reasons.append("cascade_false_repair_non_winner_exposure_days_reduction")
        if cascade_metrics.get("train_cascade_winner_retention", 0) < float(utility["winner_retention_floor"]):
            reasons.append("cascade_winner_retention")
    return sorted(set(reasons))


def build_model_registry(
    frame: pd.DataFrame,
    model_results: list[ModelResult],
    selected: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    train = frame.loc[frame["split"].eq(config["run"]["fit_split"])]
    rows = []
    for result in model_results:
        rows.append(
            {
                "model_id": result.model_id,
                "ablation_id": result.ablation_id,
                "selected_flag": bool(
                    selected.get("selected")
                    and result.model_id == selected.get("model_id")
                    and result.ablation_id == selected.get("ablation_id")
                ),
                "feature_count": len(result.feature_cols),
                "dropped_constant_feature_count": result.dropped_constant_count,
                "dropped_missing_feature_count": result.dropped_missing_count,
                "train_fit_rows": int(len(train)),
                "train_positive_n": int(train[config["run"]["target_label_column"]].map(boolish).sum()),
                "train_weight_sum": float(train["final_sample_weight"].sum()),
                "solver": config["model"]["solver"],
                "penalty": config["model"]["penalty"],
                "C": float(config["model"]["C"]),
                "random_state": int(config["model"]["random_state"]),
                "preprocess_fit_split": config["run"]["fit_split"],
                "model_status": result.status,
            }
        )
    return pd.DataFrame(rows, columns=MODEL_REGISTRY_COLUMNS)


def build_report(
    decision: str,
    selected: dict[str, Any],
    block_reasons: list[str],
    power_gate: pd.DataFrame,
    frontier: pd.DataFrame,
    exposure: pd.DataFrame,
    cascade: pd.DataFrame,
    input_failures: list[str],
    config: dict[str, Any],
) -> str:
    lines = [
        "# 10C False-Repair Rejector Report",
        "",
        "## 结论",
        "",
        f"- decision: `{decision}`",
        f"- selected_population_id: `{config['run']['selected_population_id']}`",
        f"- selected_denominator_id: `{config['run']['denominator_id']}`",
    ]
    if input_failures:
        lines.extend(["", "## Input Blockers", "", *[f"- `{failure}`" for failure in input_failures]])
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            f"- selected_model_id: `{selected.get('model_id', '')}`",
            f"- selected_ablation_id: `{selected.get('ablation_id', '')}`",
            f"- selected_capacity_id: `{selected.get('capacity_id', '')}`",
            f"- selected_threshold_id: `{selected.get('threshold_id', '')}`",
            f"- train_selection_utility: `{selected.get('train_selection_utility', np.nan)}`",
        ]
    )
    if block_reasons:
        lines.extend(["", "## Blocking Reasons", "", *[f"- `{reason}`" for reason in block_reasons]])
    selected_power = power_gate.loc[
        (power_gate["model_id"].astype(str).eq(str(selected.get("model_id", ""))))
        & (power_gate["ablation_id"].astype(str).eq(str(selected.get("ablation_id", ""))))
        & (power_gate["capacity_id"].astype(str).eq(str(selected.get("capacity_id", ""))))
    ].copy()
    if not selected_power.empty:
        cols = [
            "split",
            "sample_n",
            "reject_n",
            "false_repair_capture_lift_vs_random",
            "candidate_precision",
            "winner_retention",
            "e1_missed_retention",
            "bridge_gate_binding_flag",
            "train_selection_utility",
        ]
        lines.extend(["", "## Selected Gate Readout", "", selected_power[cols].to_markdown(index=False)])
    selected_exposure = exposure.loc[
        (exposure["model_id"].astype(str).eq(str(selected.get("model_id", ""))))
        & (exposure["ablation_id"].astype(str).eq(str(selected.get("ablation_id", ""))))
        & (exposure["capacity_id"].astype(str).eq(str(selected.get("capacity_id", ""))))
    ].copy()
    if not selected_exposure.empty:
        cols = [
            "split",
            "false_repair_non_winner_exposure_days_before",
            "false_repair_non_winner_exposure_days_rejected",
            "exposure_days_lift_vs_random",
        ]
        lines.extend(["", "## Exposure Efficiency", "", selected_exposure[cols].to_markdown(index=False)])
    if not frontier.empty:
        lines.extend(["", "## Threshold Frontier", "", frontier.to_markdown(index=False)])
    if not cascade.empty:
        lines.extend(
            [
                "",
                "## Cascade Attribution",
                "",
                cascade.loc[cascade["cascade_bucket"].ne("total")].to_markdown(index=False),
            ]
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "1. 10C 只训练 false-repair-only target，09C hybrid 与 10B fast-fail score 均未进入训练特征。",
            "2. threshold 选择使用 train-only Stage 1 utility；CV instability 与 OOS spread 只作为选后阻断。",
            "3. cascade readout 使用 10B manifest selected gate，避免把历史报告中的具体 capacity 硬编码成事实来源。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manifest(
    config_path: Path,
    config: dict[str, Any],
    input_paths: dict[str, Path],
    outputs: dict[str, Path],
    decision: str,
    selected: dict[str, Any],
    tenb_gate: dict[str, Any],
    input_failures: list[str],
    block_reasons: list[str],
    source_caveated: bool,
) -> dict[str, Any]:
    publishable_keys = {
        key: path
        for key, path in outputs.items()
        if key not in {"manifest", "post_dedup_false_repair_scores"} and path.is_file()
    }
    local_cache_keys = {
        key: path
        for key, path in outputs.items()
        if key in {"post_dedup_false_repair_scores"} and path.is_file()
    }
    expected = tenb_gate.get("expected", {})
    return {
        "component_id": "10C_false_repair_rejector",
        "decision": decision,
        "source_caveated": bool(source_caveated),
        "selected_population_id": config["run"]["selected_population_id"],
        "selected_denominator_id": config["run"]["denominator_id"],
        "selected_model_id": selected.get("model_id", config["model"]["model_id"]),
        "selected_ablation_id": selected.get("ablation_id"),
        "selected_capacity_id": selected.get("capacity_id"),
        "selected_threshold_id": selected.get("threshold_id"),
        "selected_train_selection_utility": selected.get("train_selection_utility"),
        "selected_train_constrained_utility": selected.get("selected_train_constrained_utility"),
        "actual_10b_selected_model_id": tenb_gate.get("model_id"),
        "actual_10b_selected_ablation_id": tenb_gate.get("ablation_id"),
        "actual_10b_selected_capacity_id": tenb_gate.get("capacity_id"),
        "actual_10b_selected_threshold_id": tenb_gate.get("threshold_id"),
        "actual_10b_selected_reject_fraction": tenb_gate.get("reject_fraction"),
        "expected_10b_selected_model_id": expected.get("model_id"),
        "expected_10b_selected_ablation_id": expected.get("ablation_id"),
        "expected_10b_selected_capacity_id": expected.get("capacity_id"),
        "expected_10b_selected_threshold_id": expected.get("threshold_id"),
        "expected_10b_selected_reject_fraction": expected.get("reject_fraction"),
        "tenb_selected_gate_match_flag": tenb_gate.get("match_flag"),
        "selected_cascade_status": "pass" if not block_reasons else "blocked",
        "input_hashes": {key: hash_or_empty(path) for key, path in input_paths.items()},
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "feature_contract_hash": hash_or_empty(input_paths.get("upstream_09b_feature_contract", Path())),
        "model_registry_hash": file_sha256(outputs["model_registry"]) if outputs["model_registry"].is_file() else "",
        "publishable_table_hashes": {key: file_sha256(path) for key, path in publishable_keys.items()},
        "local_cache_hashes": {key: file_sha256(path) for key, path in local_cache_keys.items()},
        "output_hashes": {
            **{key: file_sha256(path) for key, path in publishable_keys.items()},
            **{key: file_sha256(path) for key, path in local_cache_keys.items()},
        },
        "input_failures": input_failures,
        "decision_block_reasons": block_reasons,
        "input_paths": {key: str(path) for key, path in input_paths.items()},
        "outputs": {key: str(path) for key, path in outputs.items()},
        "utility_hash": canonical_json_hash(config["utility"]),
        "requirement_hash": file_sha256(REQUIREMENT_PATH),
        "git_revision": git_revision(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }


def write_blocked_outputs(
    config_path: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    audit: pd.DataFrame,
    failures: list[str],
    source_caveated: bool = True,
) -> dict[str, Any]:
    outputs = output_paths()
    write_df(outputs["input_artifact_audit"], audit)
    for key, columns in OUTPUT_SCHEMA_BY_KEY.items():
        if key == "input_artifact_audit":
            continue
        write_df(outputs[key], empty_frame(columns))
    selected: dict[str, Any] = {}
    tenb_gate: dict[str, Any] = {"expected": {}, "match_flag": False}
    write_text(
        outputs["report"],
        build_report(
            DECISION_INPUT_BLOCKED,
            selected,
            failures,
            empty_frame(POWER_GATE_COLUMNS),
            empty_frame(FRONTIER_COLUMNS),
            empty_frame(EXPOSURE_COLUMNS),
            empty_frame(CASCADE_COLUMNS),
            failures,
            config,
        ),
    )
    manifest = build_manifest(
        config_path,
        config,
        paths,
        outputs,
        DECISION_INPUT_BLOCKED,
        selected,
        tenb_gate,
        failures,
        failures,
        source_caveated,
    )
    write_json(outputs["manifest"], manifest)
    return manifest


def update_frontier_selection(
    frontier: pd.DataFrame,
    selected: dict[str, Any],
    instability: pd.DataFrame,
    block_reasons: list[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    summary = instability.loc[instability["fold_id"].eq("summary")]
    cv_std = float(summary.iloc[0]["selected_reject_fraction"]) if not summary.empty else np.nan
    excess = max(0.0, cv_std - float(config["utility"]["train_cv_selected_reject_fraction_std_cap"])) if not pd.isna(cv_std) else np.nan
    selected_constrained = (
        float(selected.get("train_selection_utility", np.nan))
        - float(config["utility"]["threshold_instability_weight"]) * excess
        if selected.get("selected") and not pd.isna(excess)
        else np.nan
    )
    selected["train_cv_selected_reject_fraction_std"] = cv_std
    selected["selected_train_constrained_utility"] = selected_constrained
    return mark_selected_frontier(frontier, selected, cv_std, selected_constrained, block_reasons), selected


def has_positive_train_feature_source_signal(frontier: pd.DataFrame, config: dict[str, Any]) -> bool:
    if frontier.empty:
        return False
    train = frontier.loc[frontier["train_selection_utility"].notna()].copy()
    if train.empty:
        return False
    return bool(
        (
            train["train_false_repair_capture_lift_vs_random"].gt(0)
            & train["train_exposure_days_lift_vs_random"].gt(0)
            & train["train_selection_utility"].gt(0)
        ).any()
    )


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_yaml(config_path)
    paths = {key: resolve_path(value) for key, value in config["paths"].items()}
    manifest_08 = load_json(paths["upstream_08_run_manifest"]) if paths["upstream_08_run_manifest"].is_file() else None
    manifest_10a = load_json(paths["upstream_10a_manifest"]) if paths["upstream_10a_manifest"].is_file() else None
    manifest_10b = load_json(paths["upstream_10b_manifest"]) if paths["upstream_10b_manifest"].is_file() else None
    source_caveated = upstream_source_caveated(manifest_08, manifest_10a, manifest_10b)
    audit = input_audit(paths, expected_hash_map(manifest_10a, manifest_10b))
    failures = hard_input_failures(audit)
    if mode == "check-inputs":
        outputs = output_paths()
        write_df(outputs["input_artifact_audit"], audit)
        return {"input_failures": failures}
    if failures:
        return write_blocked_outputs(config_path, config, paths, audit, failures, source_caveated)

    power = pd.read_csv(paths["upstream_10a_false_repair_power_audit"])
    power_config = pd.read_csv(paths["upstream_10a_power_audit_config"])
    bindings = pd.read_parquet(paths["upstream_10a_event_bindings"])
    feature_contract = pd.read_csv(paths["upstream_09b_feature_contract"])
    feature_matrix = pd.read_parquet(paths["upstream_09b_feature_matrix"])
    weights = pd.read_parquet(paths["upstream_09b_sample_weights"])
    labels = pd.read_parquet(paths["upstream_08_event_labels"])
    membership = pd.read_parquet(paths["upstream_08_episode_membership"])
    tenb_scores = pd.read_parquet(paths["upstream_10b_scores"]) if paths["upstream_10b_scores"].is_file() else None

    schema_failures = validate_loaded_schemas(
        power,
        power_config,
        bindings,
        feature_contract,
        feature_matrix,
        weights,
        labels,
        membership,
        tenb_scores,
    )
    audit = apply_schema_audit(audit, schema_failures)
    failures.extend([failure for failure in schema_failures if not is_supported_only_schema_failure(failure)])
    if failures:
        return write_blocked_outputs(config_path, config, paths, audit, failures, source_caveated)

    frame, prep_failures, diagnostics = prepare_default_frame(
        bindings, feature_matrix, weights, labels, membership, config
    )
    failures.extend(prep_failures)
    failures.extend(validate_power_counts(frame, power, config))
    power_lookup, power_failures = build_power_lookup(power, config)
    failures.extend(power_failures)
    feature_cols, _missing_allowed_features = feature_columns(feature_contract, feature_matrix)
    no_overlap_cols, overlap_dropped = no_overlap_feature_columns(feature_cols, feature_contract)
    if not overlap_dropped:
        failures.append("no_label_mechanism_overlap_no_features_dropped")
    capacities = selected_capacities(power_config, config)
    if capacities.empty:
        failures.append("false_repair_capacity_grid_empty")
    if failures:
        return write_blocked_outputs(config_path, config, paths, audit, failures, source_caveated)

    full_ablation_id = config["ablation"]["full_ablation_id"]
    no_overlap_id = config["ablation"]["no_label_mechanism_overlap_ablation_id"]
    full_result, _ = fit_score_model(frame, feature_cols, config, full_ablation_id)
    no_overlap_result, _ = fit_score_model(frame, no_overlap_cols, config, no_overlap_id)
    model_results = [full_result, no_overlap_result]
    model_failures = [f"model_status:{r.ablation_id}:{r.status}" for r in model_results if r.status != "pass"]
    if model_failures:
        return write_blocked_outputs(config_path, config, paths, audit, model_failures, source_caveated)

    power_gate, frontier, exposure, retention, mfe, score_long = build_frontiers(
        frame, model_results, capacities, power_lookup, config, diagnostics
    )
    selected = select_operating_point(power_gate, config)
    feature_cols_by_ablation = {full_ablation_id: feature_cols, no_overlap_id: no_overlap_cols}
    instability = compute_train_cv_instability(
        frame, selected, feature_cols_by_ablation, capacities, power_lookup, config
    )

    tenb_gate = selected_10b_gate(manifest_10b or {}, config)
    supported_input_failures = supported_only_input_failures(audit)
    score_tenb_failures = [failure for failure in supported_input_failures if failure.startswith("upstream_10b_scores:")]
    tenb_scores_for_cascade = None if score_tenb_failures else tenb_scores
    score_long, cascade_failures = merge_10b_flags(score_long, tenb_scores_for_cascade, tenb_gate)
    cascade_failures = sorted(set(cascade_failures + supported_input_failures))
    selected_scores = score_long.loc[
        selected.get("selected", False)
        & score_long["model_id"].astype(str).eq(str(selected.get("model_id", "")))
        & score_long["ablation_id"].astype(str).eq(str(selected.get("ablation_id", "")))
        & score_long["capacity_id"].astype(str).eq(str(selected.get("capacity_id", "")))
    ].copy()
    if selected_scores.empty:
        selected_scores = build_10b_only_cascade_base(score_long)
        cascade_note = "10B_only_baseline_no_10C_supported_gate"
    else:
        cascade_note = "selected_10b_gate_plus_selected_10c_gate"
    cascade, cascade_metrics = build_cascade_attribution(selected_scores, cascade_note) if not selected_scores.empty else (
        empty_frame(CASCADE_COLUMNS),
        {},
    )
    mfe = append_cascade_mfe_rows(mfe, selected_scores, selected, diagnostics)
    frontier, selected = update_frontier_selection(frontier, selected, instability, [], config)
    block_reasons = supported_gate_reasons(
        selected,
        float(selected.get("selected_train_constrained_utility", np.nan)),
        float(selected.get("train_cv_selected_reject_fraction_std", np.nan)),
        frontier,
        cascade_metrics,
        cascade_failures,
        tenb_gate,
        config,
    )
    frontier, selected = update_frontier_selection(frontier, selected, instability, block_reasons, config)
    registry = build_model_registry(frame, model_results, selected, config)
    diagnostic = build_09c_diagnostic(paths["upstream_09c_manifest"], paths["upstream_09c_report"])

    positive_train_signal = has_positive_train_feature_source_signal(frontier, config)
    if not block_reasons and selected.get("selected"):
        decision = DECISION_SOURCE_CAVEATED_SUPPORTED if source_caveated else DECISION_SUPPORTED
    elif positive_train_signal:
        decision = DECISION_FEATURE_SOURCE_SUPPORTED
    else:
        decision = DECISION_DIAGNOSTIC

    outputs = output_paths()
    write_df(outputs["input_artifact_audit"], audit)
    write_df(outputs["model_registry"], registry)
    write_df(outputs["false_repair_power_gate_readout"], power_gate)
    write_df(outputs["false_repair_threshold_frontier"], frontier)
    write_df(outputs["exposure_efficiency_readout"], exposure)
    write_df(outputs["winner_retention_audit"], retention)
    write_df(outputs["mfe_confirm_relation_readout"], mfe)
    write_df(outputs["train_only_threshold_instability"], instability)
    write_df(outputs["cascade_overlap_attribution"], cascade)
    write_df(outputs["pre_dedup_09c_diagnostic_comparison"], diagnostic)
    write_df(outputs["post_dedup_false_repair_scores"], score_long[SCORE_COLUMNS])
    write_text(outputs["report"], build_report(decision, selected, block_reasons, power_gate, frontier, exposure, cascade, [], config))
    manifest = build_manifest(
        config_path,
        config,
        paths,
        outputs,
        decision,
        selected,
        tenb_gate,
        [],
        block_reasons,
        source_caveated,
    )
    write_json(outputs["manifest"], manifest)
    return manifest


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    manifest = run(Path(args.config), args.mode)
    if args.mode == "check-inputs":
        failures = manifest.get("input_failures", [])
        print(json.dumps({"input_failures": failures}, sort_keys=True))
        if failures:
            raise SystemExit(1)
        return
    print(json.dumps({"decision": manifest["decision"], "manifest": str(OUTPUT_MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
