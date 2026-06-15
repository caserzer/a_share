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
from datetime import datetime, timezone
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


CONFIG_PATH = EXPERIMENT_DIR / "config_10b.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_10b_fast_fail_structural_gate.md"

OUTPUT_TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "10B_fast_fail_structural_gate"
OUTPUT_REPORT = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "10B_fast_fail_structural_gate_report.md"
OUTPUT_LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "10B_fast_fail_structural_gate"
OUTPUT_MANIFEST = EXPERIMENT_DIR / "outputs" / "manifests" / "10B_fast_fail_structural_gate_manifest.json"

DECISION_SUPPORTED = "10B_fast_fail_structural_gate_supported"
DECISION_SOURCE_CAVEATED_SUPPORTED = "10B_fast_fail_structural_gate_source_caveated_supported"
DECISION_DIAGNOSTIC = "10B_fast_fail_rule_based_structural_stop_diagnostic"
DECISION_PRE_DEDUP_ONLY = "10B_fast_fail_pre_dedup_diagnostic_only"
DECISION_INPUT_BLOCKED = "10B_fast_fail_input_blocked"

FULL_ABLATION_ID = "full"
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

INPUT_ARTIFACT_AUDIT_COLUMNS = [
    "artifact_id",
    "path",
    "required_flag",
    "exists_flag",
    "hash",
    "expected_hash",
    "status",
    "note",
]
POWER_GATE_COLUMNS = [
    "population_id",
    "denominator_id",
    "split",
    "capacity_id",
    "threshold_id",
    "readout_only_flag",
    "post_dedup_sample_n",
    "post_dedup_fast_fail_positive_n",
    "post_dedup_fast_fail_winner_n",
    "post_dedup_winner_n",
    "rule_baseline_status",
    "capture_lift_power_status",
    "winner_injury_power_status",
    "fast_fail_ml_supported_gate_allowed",
    "tenb_supported_row_allowed",
    "tenb_supported_row_block_reason",
]
FRONTIER_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "threshold_id",
    "reject_fraction",
    "reject_n",
    "accepted_n",
    "candidate_capture_rate",
    "rule_baseline_capture_rate",
    "random_baseline_capture_rate",
    "capacity_matched_capture_lift_over_rule_baseline",
    "capacity_matched_capture_lift_over_random",
    "winner_retention",
    "wrong_kill_rate",
    "candidate_accepted_mean_MAE_10",
    "rule_baseline_accepted_mean_MAE_10",
    "random_baseline_accepted_mean_MAE_10",
    "accepted_MAE_10_improves",
    "fast_fail_benefit",
    "winner_injury_excess",
    "mae_worse_excess",
    "density_excess",
    "utility_weight_profile_id",
    "random_lift_weight",
    "winner_injury_excess_weight",
    "mae_worse_excess_weight",
    "density_excess_weight",
    "oos_threshold_instability_weight",
    "train_constrained_utility",
    "oos_threshold_instability",
    "supported_constrained_utility",
    "selected_operating_point_flag",
    "supported_pass_flag",
    "status",
]
LIFT_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "baseline_id",
    "post_dedup_sample_n",
    "reject_n",
    "candidate_rejected_fast_fail_positive_n",
    "baseline_rejected_fast_fail_positive_n",
    "candidate_capture_rate",
    "baseline_capture_rate",
    "capture_lift",
]
INJURY_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "post_dedup_winner_n",
    "candidate_rejected_winner_n",
    "rule_baseline_rejected_winner_n",
    "random_baseline_rejected_winner_n",
    "winner_retention",
    "wrong_kill_rate",
    "winner_injury_status",
]
MAE_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "candidate_accepted_mean_MAE_10",
    "rule_baseline_accepted_mean_MAE_10",
    "random_baseline_accepted_mean_MAE_10",
    "accepted_MAE_10_improves",
    "mae10_joined_n",
    "mae10_missing_n",
    "mae10_status",
]
ABLATION_COLUMNS = [
    "model_id",
    "ablation_id",
    "split",
    "capacity_id",
    "dropped_feature_n",
    "retained_feature_n",
    "candidate_capture_rate",
    "capacity_matched_capture_lift_over_rule_baseline",
    "capacity_matched_capture_lift_over_random",
    "winner_retention",
    "wrong_kill_rate",
    "accepted_MAE_10_improves",
    "ablation_status",
    "conclusion_effect",
]
PREDEDUP_COLUMNS = [
    "score_source",
    "model_id_09c",
    "threshold_id_09c",
    "split",
    "joined_post_dedup_admitted_n",
    "diagnostic_rejected_n",
    "diagnostic_rejected_fast_fail_positive_n",
    "diagnostic_capture_rate",
    "overlap_with_10b_selected_rejected_n",
    "diagnostic_status",
    "note",
]
MODEL_REGISTRY_COLUMNS = [
    "model_id",
    "ablation_id",
    "estimator",
    "target",
    "fit_split",
    "train_row_n",
    "train_positive_n",
    "feature_n_input",
    "feature_n_used",
    "feature_n_dropped_constant",
    "feature_list_hash",
    "preprocessing_fit_scope",
    "sample_weight_column",
    "random_state",
    "model_status",
    "sklearn_version",
    "numpy_version",
    "pandas_version",
]
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
    "selected_fast_fail_10_label",
    "winner_120",
    "mae_10d",
    "adverse_excursion_10",
    "final_sample_weight",
    "candidate_fast_fail_score",
    "candidate_rank",
    "rule_baseline_rank",
    "random_baseline_rank",
    "candidate_rejected_flag",
    "rule_baseline_rejected_flag",
    "random_baseline_rejected_flag",
]


@dataclass(frozen=True)
class ModelResult:
    model_id: str
    ablation_id: str
    feature_cols: tuple[str, ...]
    dropped_constant_n: int
    scores: pd.Series
    status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 10B fast-fail structural gate.")
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


def empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


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


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


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


def stable_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def hash_or_empty(path: Path) -> str:
    return file_sha256(path) if path.is_file() else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def required_column_failures(frame: pd.DataFrame, artifact_id: str, required: set[str]) -> list[str]:
    missing = sorted(required - set(frame.columns))
    return [f"schema_missing_columns:{artifact_id}:{';'.join(missing)}"] if missing else []


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
    if "canonical_event_id" in out.columns:
        valid &= out["canonical_event_id"].astype(str).eq(out["binding_canonical_event_id"].astype(str))
    out["binding_key_status"] = np.where(valid, "pass", "input_event_key_component_mismatch")
    return out


def random_key(input_event_key: str, capacity_id: str, seed: int) -> str:
    return hashlib.sha256(f"{input_event_key}|{capacity_id}|{seed}".encode("utf-8")).hexdigest()


def input_audit(paths: dict[str, Path], manifest_10a: dict[str, Any] | None) -> pd.DataFrame:
    expected: dict[str, str] = {}
    required = {key: True for key in paths}
    required["upstream_09c_manifest"] = False
    required["upstream_09c_event_scores"] = False
    if manifest_10a:
        output_hashes = manifest_10a.get("output_hashes", {})
        input_hashes = manifest_10a.get("input_hashes", {})
        expected.update(
            {
                "upstream_10a_population_contract": output_hashes.get("post_dedup_population_contract", ""),
                "upstream_10a_sample_count_by_split": output_hashes.get("post_dedup_sample_count_by_split", ""),
                "upstream_10a_fast_fail_power_audit": output_hashes.get("post_dedup_fast_fail_power_audit", ""),
                "upstream_10a_power_audit_config": output_hashes.get("power_audit_config", ""),
                "upstream_10a_event_bindings": output_hashes.get("post_dedup_event_bindings", ""),
                "upstream_09b_feature_contract": input_hashes.get("upstream_09b_feature_contract", ""),
                "upstream_09b_feature_matrix": input_hashes.get("upstream_09b_feature_matrix", ""),
                "upstream_09b_sample_weights": input_hashes.get("upstream_09b_sample_weights", ""),
            }
        )
    rows = []
    for artifact_id, path in paths.items():
        exists = path.is_file()
        actual_hash = hash_or_empty(path)
        expected_hash = expected.get(artifact_id, "")
        status = "pass"
        if required.get(artifact_id, True) and not exists:
            status = "missing_required"
        elif exists and expected_hash and actual_hash != expected_hash:
            status = "hash_mismatch"
        elif not exists:
            status = "optional_missing"
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": str(path),
                "required_flag": bool(required.get(artifact_id, True)),
                "exists_flag": bool(exists),
                "hash": actual_hash,
                "expected_hash": expected_hash,
                "status": status,
                "note": "",
            }
        )
    return pd.DataFrame(rows)


def hard_input_failures(audit: pd.DataFrame) -> list[str]:
    failures = audit.loc[
        audit["required_flag"] & audit["status"].isin(["missing_required", "hash_mismatch"]),
        ["artifact_id", "status"],
    ]
    return [f"{row.artifact_id}:{row.status}" for row in failures.itertuples()]


def check_expected_sanity(config: dict[str, Any], sample_count: pd.DataFrame, population: pd.DataFrame) -> list[str]:
    defaults = config["defaults"]
    expected = config.get("expected_10a_sanity_counts", {})
    failures: list[str] = []
    sc = sample_count.loc[
        (sample_count["population_id"] == defaults["selected_population_id"])
        & (sample_count["denominator_id"] == defaults["selected_denominator_id"])
        & (~sample_count["readout_only_flag"].map(boolish))
    ].copy()
    pc = population.loc[
        (population["population_id"] == defaults["selected_population_id"])
        & (population["denominator_id"] == defaults["selected_denominator_id"])
        & (~population["readout_only_flag"].map(boolish))
    ].copy()
    for split, exp in expected.items():
        sc_row = sc.loc[sc["split"] == split]
        pc_row = pc.loc[pc["split"] == split]
        if len(sc_row) != 1 or len(pc_row) != 1:
            failures.append(f"sanity_missing_split:{split}")
            continue
        sc_one = sc_row.iloc[0]
        pc_one = pc_row.iloc[0]
        actual = {
            "input_row_n": int(sc_one["input_row_n"]),
            "admitted_event_n": int(sc_one["admitted_event_n"]),
            "suppressed_event_n": int(sc_one["suppressed_event_n"]),
            "non_executable_audit_only_n": int(sc_one["non_executable_audit_only_n"]),
            "winner_n": int(pc_one["winner_n"]),
            "fast_fail_positive_n": int(pc_one["fast_fail_positive_n"]),
            "fast_fail_winner_n": int(pc_one["fast_fail_winner_n"]),
            "false_repair_positive_n": int(pc_one["false_repair_positive_n"]),
        }
        for key, expected_value in exp.items():
            if int(actual[key]) != int(expected_value):
                failures.append(f"sanity_mismatch:{split}:{key}:{actual[key]}!={expected_value}")
    return failures


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
    "winner_120",
}
POPULATION_REQUIRED_COLUMNS = {
    "population_id",
    "denominator_id",
    "split",
    "readout_only_flag",
    "winner_n",
    "fast_fail_positive_n",
    "fast_fail_winner_n",
    "false_repair_positive_n",
    "rolling_10d_executable_event_day_density",
    "rolling_20d_executable_event_day_density",
}
SAMPLE_COUNT_REQUIRED_COLUMNS = {
    "population_id",
    "denominator_id",
    "split",
    "readout_only_flag",
    "input_row_n",
    "admitted_event_n",
    "suppressed_event_n",
    "non_executable_audit_only_n",
}
POWER_REQUIRED_COLUMNS = {
    "population_id",
    "denominator_id",
    "split",
    "capacity_id",
    "threshold_id",
    "readout_only_flag",
    "post_dedup_sample_n",
    "post_dedup_fast_fail_positive_n",
    "post_dedup_fast_fail_winner_n",
    "post_dedup_winner_n",
    "rule_baseline_status",
    "capture_lift_power_status",
    "winner_injury_power_status",
    "fast_fail_ml_supported_gate_allowed",
    "rule_baseline_rejected_fast_fail_positive_n",
    "rule_baseline_rejected_fast_fail_winner_n",
}
POWER_CONFIG_REQUIRED_COLUMNS = {"component_id", "capacity_id", "threshold_id", "reject_fraction"}
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
    "final_sample_weight",
    "weight_status",
    "supported_training_scope_flag",
}
LABEL_REQUIRED_COLUMNS = {"event_id", "label_scope", "horizon_complete_10d", "mae_10d"}


def validate_loaded_schemas(
    population: pd.DataFrame,
    sample_count: pd.DataFrame,
    power: pd.DataFrame,
    power_config: pd.DataFrame,
    bindings: pd.DataFrame,
    feature_contract: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    weights: pd.DataFrame,
    labels: pd.DataFrame,
) -> list[str]:
    failures: list[str] = []
    checks = [
        (population, "post_dedup_population_contract", POPULATION_REQUIRED_COLUMNS),
        (sample_count, "post_dedup_sample_count_by_split", SAMPLE_COUNT_REQUIRED_COLUMNS),
        (power, "post_dedup_fast_fail_power_audit", POWER_REQUIRED_COLUMNS),
        (power_config, "power_audit_config", POWER_CONFIG_REQUIRED_COLUMNS),
        (bindings, "post_dedup_event_bindings", BINDING_REQUIRED_COLUMNS),
        (feature_contract, "feature_contract", FEATURE_CONTRACT_REQUIRED_COLUMNS),
        (feature_matrix, "feature_matrix", FEATURE_MATRIX_REQUIRED_COLUMNS),
        (weights, "sample_uniqueness_weights", WEIGHT_REQUIRED_COLUMNS),
        (labels, "candidate_family_event_labels", LABEL_REQUIRED_COLUMNS),
    ]
    for frame, artifact_id, columns in checks:
        failures.extend(required_column_failures(frame, artifact_id, columns))
    return failures


def prepare_default_frame(
    bindings: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    weights: pd.DataFrame,
    labels: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    defaults = config["defaults"]
    failures: list[str] = []
    missing = sorted(BINDING_REQUIRED_COLUMNS - set(bindings.columns))
    if missing:
        return pd.DataFrame(), [f"missing_binding_columns:{';'.join(missing)}"]

    frame = bindings.loc[
        (bindings["population_id"] == defaults["selected_population_id"])
        & (bindings["rule_arm_id"] == defaults["selected_rule_arm_id"])
        & (bindings["input_denominator_id"] == defaults["selected_input_denominator_id"])
        & (bindings["denominator_id"] == defaults["selected_denominator_id"])
        & (~bindings["readout_only_flag"].map(boolish))
        & (bindings["admission_status"] == "admitted")
        & (bindings["split"].isin(defaults["readout_splits"]))
    ].copy()
    frame = derive_binding_canonical_event_id(frame)
    bad_binding = int(frame["binding_key_status"].ne("pass").sum())
    if bad_binding:
        failures.append(f"binding_key_status_fail:{bad_binding}")

    feature_join_cols = ["sample_id", "selected_target_id", "denominator_id", "canonical_event_id", "event_split"]
    missing_feature = sorted(set(feature_join_cols) - set(feature_matrix.columns))
    if missing_feature:
        failures.append(f"missing_feature_join_columns:{';'.join(missing_feature)}")
    else:
        frame = frame.merge(
            feature_matrix,
            left_on=[
                "sample_id",
                "selected_target_id",
                "input_denominator_id",
                "binding_canonical_event_id",
            ],
            right_on=["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"],
            how="left",
            suffixes=("", "_feature"),
            indicator="feature_join_indicator",
        )
        miss = int(frame["feature_join_indicator"].ne("both").sum())
        if miss:
            failures.append(f"feature_join_missing:{miss}")
        split_mismatch = int(frame["split"].astype(str).ne(frame["event_split"].astype(str)).sum())
        if split_mismatch:
            failures.append(f"feature_split_mismatch:{split_mismatch}")

    weight = weights.loc[weights["weight_horizon_id"] == "fast_fail_10d"].copy()
    weight_cols = [
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "canonical_event_id",
        "final_sample_weight",
        "weight_status",
        "supported_training_scope_flag",
    ]
    missing_weight = sorted(set(weight_cols) - set(weight.columns))
    if missing_weight:
        failures.append(f"missing_weight_columns:{';'.join(missing_weight)}")
    else:
        frame = frame.merge(
            weight[weight_cols],
            left_on=[
                "sample_id",
                "selected_target_id",
                "input_denominator_id",
                "binding_canonical_event_id",
            ],
            right_on=["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"],
            how="left",
            suffixes=("", "_weight"),
            indicator="weight_join_indicator",
        )
        miss_weight = int(frame["weight_join_indicator"].ne("both").sum())
        bad_weight = int(
            (
                frame["final_sample_weight"].isna()
                | frame["final_sample_weight"].astype(float).le(0)
                | frame["weight_status"].astype(str).ne("complete")
            ).sum()
        )
        if miss_weight:
            failures.append(f"weight_join_missing:{miss_weight}")
        if bad_weight:
            failures.append(f"bad_fast_fail_weight:{bad_weight}")

    label = labels.loc[
        (labels["label_scope"] == "all_new_candidate_union") & labels["horizon_complete_10d"].map(boolish)
    ].copy()
    label_cols = ["event_id", "mae_10d"]
    missing_label = sorted(set(label_cols) - set(label.columns))
    if missing_label:
        failures.append(f"missing_label_columns:{';'.join(missing_label)}")
    else:
        frame = frame.merge(
            label[label_cols],
            left_on="binding_canonical_event_id",
            right_on="event_id",
            how="left",
            indicator="mae_join_indicator",
        )
        miss_mae = int(frame["mae_join_indicator"].ne("both").sum())
        pos_mae = int(frame["mae_10d"].astype(float).gt(0).sum())
        if miss_mae:
            failures.append(f"mae_join_missing:{miss_mae}")
        if pos_mae:
            failures.append(f"input_blocked_positive_mae_sign:{pos_mae}")
        frame["adverse_excursion_10"] = -1.0 * frame["mae_10d"].astype(float)

    for col in ["selected_fast_fail_10_label", "winner_120"]:
        frame[col] = frame[col].map(boolish)
    frame["final_sample_weight"] = frame["final_sample_weight"].astype(float)
    return frame, failures


def feature_columns(feature_contract: pd.DataFrame, feature_matrix: pd.DataFrame) -> tuple[list[str], list[str]]:
    contract = feature_contract.copy()
    allowed = contract.loc[
        contract["allowed_for_09C_flag"].map(boolish)
        & contract["t0_visible_flag"].map(boolish)
        & contract["feature_dtype"].astype(str).isin(["float64", "int64", "float32", "int32"])
    ].copy()
    cols = [
        str(feature)
        for feature in allowed["feature_id"].tolist()
        if str(feature) in feature_matrix.columns and str(feature) not in META_FEATURE_COLUMNS
    ]
    missing = sorted(set(allowed["feature_id"].astype(str)) - set(cols) - META_FEATURE_COLUMNS)
    return cols, missing


def rule_baseline_status(feature_contract: pd.DataFrame, frame: pd.DataFrame, required: list[str]) -> str:
    contract = feature_contract.set_index("feature_id", drop=False)
    for feature in required:
        if feature not in frame.columns:
            return "input_blocked"
        if feature not in contract.index:
            return "input_blocked"
        rows = contract.loc[[feature]]
        if len(rows) != 1 or not boolish(rows.iloc[0]["allowed_for_09C_flag"]):
            return "input_blocked"
    return "pass"


def ablation_drop_columns(feature_cols: list[str], feature_contract: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    drop_families = set(config["ablation"]["drop_feature_families"])
    overlap_policy = str(config["ablation"].get("drop_overlap_policy", "non_none"))
    configured_overlap = set(config["ablation"].get("drop_overlap_types", []))
    contract_by_feature = feature_contract.set_index("feature_id", drop=False)
    drop_cols = []
    for col in feature_cols:
        if col not in contract_by_feature.index:
            continue
        row = contract_by_feature.loc[col]
        family_drop = str(row["feature_family"]) in drop_families
        overlap_value = str(row["label_mechanism_overlap_type"])
        if overlap_policy == "non_none":
            overlap_drop = overlap_value != "none"
        else:
            overlap_drop = overlap_value in configured_overlap
        if family_drop or overlap_drop:
            drop_cols.append(col)
    return drop_cols


def fit_preprocess(train: pd.DataFrame, feature_cols: list[str]) -> tuple[list[str], dict[str, float], dict[str, float]]:
    used: list[str] = []
    medians: dict[str, float] = {}
    iqrs: dict[str, float] = {}
    for col in feature_cols:
        values = pd.to_numeric(train[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        clean = values.dropna()
        if clean.empty:
            continue
        median = float(clean.median())
        iqr = float(clean.quantile(0.75) - clean.quantile(0.25))
        if not np.isfinite(iqr) or iqr == 0:
            continue
        used.append(col)
        medians[col] = median
        iqrs[col] = iqr
    return used, medians, iqrs


def transform_features(frame: pd.DataFrame, feature_cols: list[str], medians: dict[str, float], iqrs: dict[str, float]) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for col in feature_cols:
        values = pd.to_numeric(frame[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        values = values.fillna(medians[col])
        out[col] = (values - medians[col]) / iqrs[col]
    return out


def train_model(
    frame: pd.DataFrame,
    feature_cols: list[str],
    config: dict[str, Any],
    ablation_id: str,
) -> tuple[ModelResult, dict[str, Any]]:
    defaults = config["defaults"]
    train = frame.loc[frame["split"] == defaults["fit_split"]].copy()
    used, medians, iqrs = fit_preprocess(train, feature_cols)
    model_id = defaults["selected_model_id"]
    if not used:
        return (
            ModelResult(model_id, ablation_id, tuple(), len(feature_cols), pd.Series(np.nan, index=frame.index), "input_blocked_no_features"),
            {"feature_n_input": len(feature_cols), "feature_n_used": 0, "feature_n_dropped_constant": len(feature_cols)},
        )
    y = train[defaults["target_column"]].astype(int)
    fit_mask = train["final_sample_weight"].astype(float).gt(0) & y.notna()
    if y.loc[fit_mask].nunique() < 2:
        return (
            ModelResult(model_id, ablation_id, tuple(used), len(feature_cols) - len(used), pd.Series(np.nan, index=frame.index), "input_blocked_single_class"),
            {"feature_n_input": len(feature_cols), "feature_n_used": len(used), "feature_n_dropped_constant": len(feature_cols) - len(used)},
        )
    x_train = transform_features(train.loc[fit_mask], used, medians, iqrs)
    model_cfg = config["model"]
    model = LogisticRegression(
        penalty=str(model_cfg["penalty"]),
        C=float(model_cfg["C"]),
        solver=str(model_cfg["solver"]),
        max_iter=int(model_cfg["max_iter"]),
        random_state=int(model_cfg["random_state"]),
        class_weight=model_cfg.get("class_weight"),
    )
    model.fit(x_train, y.loc[fit_mask].astype(int), sample_weight=train.loc[fit_mask, "final_sample_weight"].astype(float))
    x_all = transform_features(frame, used, medians, iqrs)
    scores = pd.Series(model.predict_proba(x_all)[:, 1], index=frame.index)
    return (
        ModelResult(model_id, ablation_id, tuple(used), len(feature_cols) - len(used), scores, "pass"),
        {"feature_n_input": len(feature_cols), "feature_n_used": len(used), "feature_n_dropped_constant": len(feature_cols) - len(used)},
    )


def rule_sorted_index(part: pd.DataFrame, required_features: list[str]) -> pd.Index:
    sort = pd.DataFrame(index=part.index)
    for feature in required_features:
        values = pd.to_numeric(part[feature], errors="coerce")
        sort[f"{feature}_isnull"] = values.isna().astype(int)
        sort[feature] = values
    sort["atr_20_pct_sort"] = -pd.to_numeric(part["atr_20_pct"], errors="coerce")
    sort["input_event_key"] = part["input_event_key"].astype(str)
    sort = sort.drop(columns=["atr_20_pct"])
    return sort.sort_values(
        [
            "close_to_ema60_isnull",
            "close_to_ema60",
            "ema60_slope_20d_isnull",
            "ema60_slope_20d",
            "return_20d_isnull",
            "return_20d",
            "stock_vs_market_20d_isnull",
            "stock_vs_market_20d",
            "atr_20_pct_isnull",
            "atr_20_pct_sort",
            "input_event_key",
        ],
        kind="mergesort",
    ).index


def rank_series(order: pd.Index) -> pd.Series:
    return pd.Series(np.arange(1, len(order) + 1), index=order)


def compute_constrained_utility(
    row: dict[str, Any],
    weights: dict[str, Any],
    gates: dict[str, Any],
) -> dict[str, float]:
    fast_fail_benefit = float(row["capacity_matched_capture_lift_over_rule_baseline"]) + float(
        weights["random_lift_weight"]
    ) * float(row["capacity_matched_capture_lift_over_random"])
    winner_injury_excess = max(0.0, float(row["wrong_kill_rate"]) - float(gates["wrong_kill_rate_cap"]))
    mae_worse_excess = max(
        0.0,
        float(row["candidate_accepted_mean_MAE_10"])
        - min(float(row["rule_baseline_accepted_mean_MAE_10"]), float(row["random_baseline_accepted_mean_MAE_10"])),
    )
    density_excess = max(
        0.0,
        float(row["rolling_10d_executable_event_day_density"]) - float(gates["rolling_10d_density_cap"]),
    ) + max(
        0.0,
        float(row["rolling_20d_executable_event_day_density"]) - float(gates["rolling_20d_density_cap"]),
    )
    train_utility = (
        fast_fail_benefit
        - float(weights["winner_injury_excess_weight"]) * winner_injury_excess
        - float(weights["mae_worse_excess_weight"]) * mae_worse_excess
        - float(weights["density_excess_weight"]) * density_excess
    )
    return {
        "fast_fail_benefit": fast_fail_benefit,
        "winner_injury_excess": winner_injury_excess,
        "mae_worse_excess": mae_worse_excess,
        "density_excess": density_excess,
        "train_constrained_utility": train_utility,
    }


def baseline_counts(part: pd.DataFrame, rejected_flag: pd.Series, target_col: str) -> dict[str, Any]:
    target = part[target_col].map(boolish)
    winner = part["winner_120"].map(boolish)
    rejected = rejected_flag.reindex(part.index).fillna(False).astype(bool)
    accepted = ~rejected
    return {
        "rejected_fast_fail_positive_n": int((rejected & target).sum()),
        "rejected_fast_fail_winner_n": int((rejected & target & winner).sum()),
        "rejected_fast_fail_non_winner_n": int((rejected & target & ~winner).sum()),
        "rejected_winner_n": int((rejected & winner).sum()),
        "accepted_fast_fail_positive_n": int((accepted & target).sum()),
        "accepted_winner_n": int((accepted & winner).sum()),
        "accepted_mean_MAE_10": float(part.loc[accepted, "adverse_excursion_10"].mean()),
    }


def build_power_gate_readout(power: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    defaults = config["defaults"]
    gates = config["gates"]
    rows = power.loc[
        (power["population_id"] == defaults["selected_population_id"])
        & (power["denominator_id"] == defaults["selected_denominator_id"])
        & (~power["readout_only_flag"].map(boolish))
    ].copy()
    out_rows = []
    for row in rows.to_dict("records"):
        reasons = []
        if str(row["rule_baseline_status"]) != "pass":
            reasons.append("rule_baseline_status")
        if str(row["capture_lift_power_status"]) != "pass":
            reasons.append("capture_lift_power_status")
        if str(row["winner_injury_power_status"]) != "pass":
            reasons.append("winner_injury_power_status")
        if not boolish(row["fast_fail_ml_supported_gate_allowed"]):
            reasons.append("fast_fail_ml_supported_gate_allowed")
        if int(row["post_dedup_fast_fail_positive_n"]) < int(gates["min_positive_count"]):
            reasons.append("post_dedup_fast_fail_positive_n")
        if int(row["post_dedup_fast_fail_winner_n"]) < int(gates["min_winner_count"]):
            reasons.append("post_dedup_fast_fail_winner_n")
        if int(row["rule_baseline_rejected_fast_fail_positive_n"]) < int(gates["min_rule_positive_count"]):
            reasons.append("rule_baseline_rejected_fast_fail_positive_n")
        if int(row["rule_baseline_rejected_fast_fail_winner_n"]) < int(gates["min_rule_winner_count"]):
            reasons.append("rule_baseline_rejected_fast_fail_winner_n")
        row["tenb_supported_row_allowed"] = not reasons
        row["tenb_supported_row_block_reason"] = ";".join(reasons) if reasons else "pass"
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def build_frontiers(
    frame: pd.DataFrame,
    model_results: list[ModelResult],
    power_config: pd.DataFrame,
    power_gate: pd.DataFrame,
    population: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    defaults = config["defaults"]
    weights = config["utility_weights"]
    gates = config["gates"]
    target_col = defaults["target_column"]
    capacities = power_config.loc[power_config["component_id"] == "fast_fail_10d"].copy()
    capacities["reject_fraction"] = capacities["reject_fraction"].astype(float)
    density_lookup = population.set_index(["split"])[
        ["rolling_10d_executable_event_day_density", "rolling_20d_executable_event_day_density"]
    ].to_dict("index")
    power_lookup = power_gate.set_index(["split", "capacity_id"]).to_dict("index")

    frontier_rows: list[dict[str, Any]] = []
    lift_rows: list[dict[str, Any]] = []
    injury_rows: list[dict[str, Any]] = []
    mae_rows: list[dict[str, Any]] = []
    score_rows: list[pd.DataFrame] = []

    rule_features = config["rule_baseline"]["required_features"]
    seed = int(defaults["random_seed"])

    for result in model_results:
        scored = frame.copy()
        scored["candidate_fast_fail_score"] = result.scores
        for capacity in capacities.to_dict("records"):
            capacity_id = str(capacity["capacity_id"])
            threshold_id = str(capacity["threshold_id"])
            reject_fraction = float(capacity["reject_fraction"])
            split_frames = []
            for split in SPLIT_ORDER:
                part = scored.loc[scored["split"] == split].copy()
                if part.empty:
                    continue
                reject_n = int(math.ceil(len(part) * reject_fraction))
                candidate_order = part.sort_values(
                    ["candidate_fast_fail_score", "input_event_key"],
                    ascending=[False, True],
                    kind="mergesort",
                ).index
                rule_order = rule_sorted_index(part, rule_features)
                random_order = (
                    part.assign(
                        random_key=part["input_event_key"].map(lambda key: random_key(str(key), capacity_id, seed))
                    )
                    .sort_values(["random_key", "input_event_key"], ascending=[True, True], kind="mergesort")
                    .index
                )
                candidate_rank = rank_series(candidate_order)
                rule_rank = rank_series(rule_order)
                random_rank = rank_series(random_order)
                cand_rej = candidate_rank.le(reject_n)
                rule_rej = rule_rank.le(reject_n)
                rand_rej = random_rank.le(reject_n)

                target = part[target_col].map(boolish)
                winner = part["winner_120"].map(boolish)
                post_pos = int(target.sum())
                post_ff_winner = int((target & winner).sum())
                post_winner = int(winner.sum())
                cand_counts = baseline_counts(part, cand_rej, target_col)
                rule_counts = baseline_counts(part, rule_rej, target_col)
                rand_counts = baseline_counts(part, rand_rej, target_col)

                cand_capture = safe_div(cand_counts["rejected_fast_fail_positive_n"], post_pos)
                rule_capture = safe_div(rule_counts["rejected_fast_fail_positive_n"], post_pos)
                rand_capture = safe_div(rand_counts["rejected_fast_fail_positive_n"], post_pos)
                wrong_kill = safe_div(cand_counts["rejected_winner_n"], post_winner)
                winner_retention = 1 - wrong_kill if not pd.isna(wrong_kill) else np.nan
                mae_improves = (
                    cand_counts["accepted_mean_MAE_10"] <= rule_counts["accepted_mean_MAE_10"]
                    and cand_counts["accepted_mean_MAE_10"] <= rand_counts["accepted_mean_MAE_10"]
                )
                density = density_lookup.get(split, {})
                base_row = {
                    "model_id": result.model_id,
                    "ablation_id": result.ablation_id,
                    "split": split,
                    "capacity_id": capacity_id,
                    "threshold_id": threshold_id,
                    "reject_fraction": reject_fraction,
                    "reject_n": reject_n,
                    "accepted_n": int(len(part) - reject_n),
                    "post_dedup_sample_n": int(len(part)),
                    "post_dedup_fast_fail_positive_n": post_pos,
                    "post_dedup_fast_fail_winner_n": post_ff_winner,
                    "post_dedup_winner_n": post_winner,
                    "candidate_rejected_fast_fail_positive_n": cand_counts["rejected_fast_fail_positive_n"],
                    "rule_baseline_rejected_fast_fail_positive_n": rule_counts["rejected_fast_fail_positive_n"],
                    "random_baseline_rejected_fast_fail_positive_n": rand_counts["rejected_fast_fail_positive_n"],
                    "candidate_capture_rate": cand_capture,
                    "rule_baseline_capture_rate": rule_capture,
                    "random_baseline_capture_rate": rand_capture,
                    "capacity_matched_capture_lift_over_rule_baseline": cand_capture - rule_capture,
                    "capacity_matched_capture_lift_over_random": cand_capture - rand_capture,
                    "winner_retention": winner_retention,
                    "wrong_kill_rate": wrong_kill,
                    "candidate_accepted_mean_MAE_10": cand_counts["accepted_mean_MAE_10"],
                    "rule_baseline_accepted_mean_MAE_10": rule_counts["accepted_mean_MAE_10"],
                    "random_baseline_accepted_mean_MAE_10": rand_counts["accepted_mean_MAE_10"],
                    "accepted_MAE_10_improves": bool(mae_improves),
                    "rolling_10d_executable_event_day_density": density.get("rolling_10d_executable_event_day_density", np.nan),
                    "rolling_20d_executable_event_day_density": density.get("rolling_20d_executable_event_day_density", np.nan),
                    "utility_weight_profile_id": weights["utility_weight_profile_id"],
                    "random_lift_weight": weights["random_lift_weight"],
                    "winner_injury_excess_weight": weights["winner_injury_excess_weight"],
                    "mae_worse_excess_weight": weights["mae_worse_excess_weight"],
                    "density_excess_weight": weights["density_excess_weight"],
                    "oos_threshold_instability_weight": weights["oos_threshold_instability_weight"],
                }
                base_row.update(compute_constrained_utility(base_row, weights, gates))
                base_row["oos_threshold_instability"] = np.nan
                base_row["supported_constrained_utility"] = np.nan
                power_row = power_lookup.get((split, capacity_id), {})
                base_row["tenb_supported_row_allowed"] = bool(power_row.get("tenb_supported_row_allowed", False))
                base_row["tenb_supported_row_block_reason"] = power_row.get(
                    "tenb_supported_row_block_reason", "missing_power_gate_row"
                )
                base_row["status"] = "candidate_readout" if result.status == "pass" else result.status
                frontier_rows.append(base_row)

                for baseline_id, counts, capture in [
                    ("rule_baseline", rule_counts, rule_capture),
                    ("random_baseline", rand_counts, rand_capture),
                ]:
                    baseline_rejected = (
                        rule_counts["rejected_fast_fail_positive_n"]
                        if baseline_id == "rule_baseline"
                        else rand_counts["rejected_fast_fail_positive_n"]
                    )
                    lift_rows.append(
                        {
                            "model_id": result.model_id,
                            "ablation_id": result.ablation_id,
                            "split": split,
                            "capacity_id": capacity_id,
                            "baseline_id": baseline_id,
                            "post_dedup_sample_n": int(len(part)),
                            "reject_n": reject_n,
                            "candidate_rejected_fast_fail_positive_n": cand_counts["rejected_fast_fail_positive_n"],
                            "baseline_rejected_fast_fail_positive_n": baseline_rejected,
                            "candidate_capture_rate": cand_capture,
                            "baseline_capture_rate": capture,
                            "capture_lift": cand_capture - capture,
                        }
                    )
                injury_rows.append(
                    {
                        "model_id": result.model_id,
                        "ablation_id": result.ablation_id,
                        "split": split,
                        "capacity_id": capacity_id,
                        "post_dedup_winner_n": post_winner,
                        "candidate_rejected_winner_n": cand_counts["rejected_winner_n"],
                        "rule_baseline_rejected_winner_n": rule_counts["rejected_winner_n"],
                        "random_baseline_rejected_winner_n": rand_counts["rejected_winner_n"],
                        "winner_retention": winner_retention,
                        "wrong_kill_rate": wrong_kill,
                        "winner_injury_status": "pass"
                        if winner_retention >= gates["winner_retention_floor"] and wrong_kill <= gates["wrong_kill_rate_cap"]
                        else "fail",
                    }
                )
                mae_rows.append(
                    {
                        "model_id": result.model_id,
                        "ablation_id": result.ablation_id,
                        "split": split,
                        "capacity_id": capacity_id,
                        "candidate_accepted_mean_MAE_10": cand_counts["accepted_mean_MAE_10"],
                        "rule_baseline_accepted_mean_MAE_10": rule_counts["accepted_mean_MAE_10"],
                        "random_baseline_accepted_mean_MAE_10": rand_counts["accepted_mean_MAE_10"],
                        "accepted_MAE_10_improves": bool(mae_improves),
                        "mae10_joined_n": int(part["mae_10d"].notna().sum()),
                        "mae10_missing_n": int(part["mae_10d"].isna().sum()),
                        "mae10_status": "pass" if part["mae_10d"].notna().all() else "missing_mae",
                    }
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
                        "selected_fast_fail_10_label",
                        "winner_120",
                        "mae_10d",
                        "adverse_excursion_10",
                        "final_sample_weight",
                        "candidate_fast_fail_score",
                    ]
                ].copy()
                score_part.insert(0, "reject_fraction", reject_fraction)
                score_part.insert(0, "threshold_id", threshold_id)
                score_part.insert(0, "capacity_id", capacity_id)
                score_part.insert(0, "ablation_id", result.ablation_id)
                score_part.insert(0, "model_id", result.model_id)
                score_part["candidate_rank"] = candidate_rank.reindex(part.index).astype(int).to_numpy()
                score_part["rule_baseline_rank"] = rule_rank.reindex(part.index).astype(int).to_numpy()
                score_part["random_baseline_rank"] = random_rank.reindex(part.index).astype(int).to_numpy()
                score_part["candidate_rejected_flag"] = cand_rej.reindex(part.index).astype(bool).to_numpy()
                score_part["rule_baseline_rejected_flag"] = rule_rej.reindex(part.index).astype(bool).to_numpy()
                score_part["random_baseline_rejected_flag"] = rand_rej.reindex(part.index).astype(bool).to_numpy()
                split_frames.append(score_part)
            if split_frames:
                score_rows.append(pd.concat(split_frames, ignore_index=True))

    frontier = pd.DataFrame(frontier_rows)
    if not frontier.empty:
        for (model_id, ablation_id, capacity_id), group in frontier.groupby(["model_id", "ablation_id", "capacity_id"]):
            readout = group.set_index("split")
            oos_values = []
            for split in ["validation", "robustness"]:
                if split in readout.index:
                    oos_values.extend(
                        [
                            readout.loc[split, "capacity_matched_capture_lift_over_rule_baseline"],
                            readout.loc[split, "capacity_matched_capture_lift_over_random"],
                        ]
                    )
            if oos_values:
                min_oos = min(float(value) for value in oos_values if not pd.isna(value))
                oos_instability = max(0.0, float(gates["oos_severe_reversal_floor"]) - min_oos)
            else:
                oos_instability = np.nan
            train_rows = frontier.index[
                (frontier["model_id"] == model_id)
                & (frontier["ablation_id"] == ablation_id)
                & (frontier["capacity_id"] == capacity_id)
                & (frontier["split"] == defaults["fit_split"])
            ]
            train_utility = float(frontier.loc[train_rows[0], "train_constrained_utility"]) if len(train_rows) else np.nan
            mask = (
                (frontier["model_id"] == model_id)
                & (frontier["ablation_id"] == ablation_id)
                & (frontier["capacity_id"] == capacity_id)
            )
            frontier.loc[mask, "oos_threshold_instability"] = oos_instability
            frontier.loc[mask, "supported_constrained_utility"] = train_utility - float(
                weights["oos_threshold_instability_weight"]
            ) * oos_instability

    score_long = pd.concat(score_rows, ignore_index=True) if score_rows else pd.DataFrame()
    return (
        frontier,
        pd.DataFrame(lift_rows),
        pd.DataFrame(injury_rows),
        pd.DataFrame(mae_rows),
        score_long,
        capacities,
    )


def select_operating_point(frontier: pd.DataFrame, power_gate: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    defaults = config["defaults"]
    selectable = set(defaults["selectable_capacity_ids"])
    allowed = set(
        power_gate.loc[
            (power_gate["split"] == defaults["fit_split"]) & power_gate["tenb_supported_row_allowed"],
            "capacity_id",
        ].astype(str)
    )
    candidates = frontier.loc[
        (frontier["model_id"] == defaults["selected_model_id"])
        & (frontier["ablation_id"] == FULL_ABLATION_ID)
        & (frontier["split"] == defaults["fit_split"])
        & (frontier["capacity_id"].isin(selectable & allowed))
    ].copy()
    if candidates.empty:
        return {"selected": False, "reason": "no_train_supported_non_sensitivity_capacity"}
    candidates = candidates.sort_values(
        [
            "train_constrained_utility",
            "capacity_matched_capture_lift_over_rule_baseline",
            "capacity_matched_capture_lift_over_random",
            "winner_retention",
            "reject_fraction",
            "capacity_id",
        ],
        ascending=[False, False, False, False, True, True],
        kind="mergesort",
    )
    row = candidates.iloc[0].to_dict()
    row["selected"] = True
    row["reason"] = "selected_by_train_constrained_utility"
    return row


def supported_pass(selected: dict[str, Any], config: dict[str, Any]) -> tuple[bool, list[str]]:
    if not selected.get("selected"):
        return False, [str(selected.get("reason", "not_selected"))]
    gates = config["gates"]
    reasons = []
    required_numeric = [
        "capacity_matched_capture_lift_over_rule_baseline",
        "capacity_matched_capture_lift_over_random",
        "winner_retention",
        "wrong_kill_rate",
        "density_excess",
        "train_constrained_utility",
        "oos_threshold_instability",
        "supported_constrained_utility",
    ]
    for key in required_numeric:
        if not is_finite_number(selected.get(key)):
            reasons.append(f"{key}_nonfinite")
    if reasons:
        return False, reasons
    if float(selected["capacity_matched_capture_lift_over_rule_baseline"]) < float(gates["capture_lift_margin"]):
        reasons.append("rule_lift_below_margin")
    if float(selected["capacity_matched_capture_lift_over_random"]) < float(gates["capture_lift_margin"]):
        reasons.append("random_lift_below_margin")
    if not boolish(selected["accepted_MAE_10_improves"]):
        reasons.append("accepted_mae10_not_improved")
    if float(selected["winner_retention"]) < float(gates["winner_retention_floor"]):
        reasons.append("winner_retention_below_floor")
    if float(selected["wrong_kill_rate"]) > float(gates["wrong_kill_rate_cap"]):
        reasons.append("wrong_kill_rate_above_cap")
    if float(selected["density_excess"]) != 0:
        reasons.append("density_excess")
    if float(selected["train_constrained_utility"]) <= 0:
        reasons.append("train_constrained_utility_non_positive")
    if float(selected["oos_threshold_instability"]) != 0:
        reasons.append("oos_threshold_instability")
    if float(selected["supported_constrained_utility"]) <= 0:
        reasons.append("supported_constrained_utility_non_positive")
    return not reasons, reasons


def build_ablation_readout(
    frontier: pd.DataFrame,
    model_registry: pd.DataFrame,
    selected: dict[str, Any],
    ablation_removed_counts: dict[str, int],
) -> pd.DataFrame:
    rows = []
    for _, row in frontier.iterrows():
        reg = model_registry.loc[
            (model_registry["model_id"] == row["model_id"]) & (model_registry["ablation_id"] == row["ablation_id"])
        ]
        feature_n_input = int(reg.iloc[0]["feature_n_input"]) if not reg.empty else 0
        dropped = int(ablation_removed_counts.get(str(row["ablation_id"]), 0))
        retained = max(0, feature_n_input)
        selected_match = (
            selected.get("selected")
            and row["capacity_id"] == selected.get("capacity_id")
            and row["split"] == selected.get("split")
            and row["ablation_id"] != FULL_ABLATION_ID
        )
        conclusion = "selected_capacity_readout" if selected_match else "readout"
        if row["ablation_id"] == FULL_ABLATION_ID:
            ablation_status = "reference"
        else:
            ablation_status = "pass" if dropped > 0 else "family_name_unmatched"
        rows.append(
            {
                "model_id": row["model_id"],
                "ablation_id": row["ablation_id"],
                "split": row["split"],
                "capacity_id": row["capacity_id"],
                "dropped_feature_n": dropped,
                "retained_feature_n": retained,
                "candidate_capture_rate": row["candidate_capture_rate"],
                "capacity_matched_capture_lift_over_rule_baseline": row[
                    "capacity_matched_capture_lift_over_rule_baseline"
                ],
                "capacity_matched_capture_lift_over_random": row["capacity_matched_capture_lift_over_random"],
                "winner_retention": row["winner_retention"],
                "wrong_kill_rate": row["wrong_kill_rate"],
                "accepted_MAE_10_improves": row["accepted_MAE_10_improves"],
                "ablation_status": ablation_status,
                "conclusion_effect": conclusion,
            }
        )
    return pd.DataFrame(rows)


def build_prededup_replay(score_long: pd.DataFrame, frame: pd.DataFrame, paths: dict[str, Path], selected: dict[str, Any]) -> pd.DataFrame:
    scores_path = paths["upstream_09c_event_scores"]
    manifest_path = paths["upstream_09c_manifest"]
    if not scores_path.is_file():
        return pd.DataFrame(
            [
                {
                    "score_source": "09C_hybrid_prededup_event_scores",
                    "model_id_09c": "",
                    "threshold_id_09c": "",
                    "split": "all",
                    "joined_post_dedup_admitted_n": 0,
                    "diagnostic_rejected_n": 0,
                    "diagnostic_rejected_fast_fail_positive_n": 0,
                    "diagnostic_capture_rate": np.nan,
                    "overlap_with_10b_selected_rejected_n": 0,
                    "diagnostic_status": "not_available",
                    "note": "09C event_scores.csv.gz missing",
                }
            ]
        )
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    selected_threshold = str(manifest.get("selected_threshold_id", ""))
    scores = pd.read_csv(scores_path)
    diag = frame.merge(
        scores,
        left_on=["sample_id", "selected_target_id", "input_denominator_id"],
        right_on=["sample_id", "selected_target_id", "denominator_id"],
        how="left",
        suffixes=("", "_09c"),
    )
    if selected_threshold:
        diag = diag.loc[diag["threshold_id"].astype(str).eq(selected_threshold) | diag["threshold_id"].isna()].copy()
    selected_rejected = pd.DataFrame()
    if selected.get("selected") and not score_long.empty:
        selected_rejected = score_long.loc[
            (score_long["model_id"] == selected["model_id"])
            & (score_long["ablation_id"] == FULL_ABLATION_ID)
            & (score_long["capacity_id"] == selected["capacity_id"])
            & score_long["candidate_rejected_flag"]
        ][["input_event_key"]].drop_duplicates()
    rows = []
    for split, part in diag.groupby("split", dropna=False):
        rejected = part["rejected_flag"].map(boolish).fillna(False) if "rejected_flag" in part else pd.Series(False, index=part.index)
        positives = part["selected_fast_fail_10_label"].map(boolish)
        overlap = 0
        if not selected_rejected.empty:
            overlap = int(part.loc[rejected, ["input_event_key"]].merge(selected_rejected, on="input_event_key").shape[0])
        rows.append(
            {
                "score_source": "09C_hybrid_prededup_event_scores",
                "model_id_09c": str(part["model_id"].dropna().iloc[0]) if "model_id" in part and part["model_id"].notna().any() else "",
                "threshold_id_09c": selected_threshold,
                "split": split,
                "joined_post_dedup_admitted_n": int(part["score"].notna().sum()) if "score" in part else 0,
                "diagnostic_rejected_n": int(rejected.sum()),
                "diagnostic_rejected_fast_fail_positive_n": int((rejected & positives).sum()),
                "diagnostic_capture_rate": safe_div(int((rejected & positives).sum()), int(positives.sum())),
                "overlap_with_10b_selected_rejected_n": overlap,
                "diagnostic_status": "pass" if part.get("score", pd.Series(dtype=float)).notna().any() else "not_joined",
                "note": "diagnostic_only_pre_dedup_hybrid_score",
            }
        )
    return pd.DataFrame(rows)


def build_report(
    decision: str,
    selected: dict[str, Any],
    pass_reasons: list[str],
    frontier: pd.DataFrame,
    power_gate: pd.DataFrame,
    input_failures: list[str],
    config: dict[str, Any],
) -> str:
    lines = [
        "# 10B Fast-Fail Structural Gate Report",
        "",
        f"- decision: `{decision}`",
        f"- source_caveated: `{selected.get('source_caveated', '')}`",
        f"- selected_population_id: `{config['defaults']['selected_population_id']}`",
        f"- selected_denominator_id: `{config['defaults']['selected_denominator_id']}`",
    ]
    if input_failures:
        lines.extend(["", "## Input Blockers", "", *[f"- `{failure}`" for failure in input_failures]])
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            f"- selected_capacity_id: `{selected.get('capacity_id', 'none')}`",
            f"- selected_threshold_id: `{selected.get('threshold_id', 'none')}`",
            f"- selected_status: `{selected.get('reason', 'none')}`",
        ]
    )
    if pass_reasons:
        lines.extend(["", "## Supported Gate Blockers", "", *[f"- `{reason}`" for reason in pass_reasons]])
    selected_rows = frontier.loc[
        (frontier["ablation_id"] == FULL_ABLATION_ID) & (frontier["capacity_id"].astype(str) == str(selected.get("capacity_id", "")))
    ].copy()
    if not selected_rows.empty:
        cols = [
            "split",
            "candidate_capture_rate",
            "capacity_matched_capture_lift_over_rule_baseline",
            "capacity_matched_capture_lift_over_random",
            "winner_retention",
            "wrong_kill_rate",
            "train_constrained_utility",
            "oos_threshold_instability",
            "supported_constrained_utility",
        ]
        lines.extend(["", "## Selected Capacity Readout", "", selected_rows[cols].to_markdown(index=False)])
    lines.extend(
        [
            "",
            "## Power Gate Rows",
            "",
            power_gate[
                [
                    "split",
                    "capacity_id",
                    "post_dedup_sample_n",
                    "post_dedup_fast_fail_positive_n",
                    "post_dedup_fast_fail_winner_n",
                    "tenb_supported_row_allowed",
                    "tenb_supported_row_block_reason",
                ]
            ].to_markdown(index=False),
            "",
            "This component trains only a fast-fail score. AUC-style ranking metrics are diagnostic only; the selected threshold is train-only constrained utility with winner, MAE, density, and OOS blocks.",
        ]
    )
    return "\n".join(lines) + "\n"


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_TABLE_DIR / "input_artifact_audit.csv",
        "fast_fail_power_gate_readout": OUTPUT_TABLE_DIR / "fast_fail_power_gate_readout.csv",
        "fast_fail_threshold_frontier": OUTPUT_TABLE_DIR / "fast_fail_threshold_frontier.csv",
        "capacity_matched_rule_lift": OUTPUT_TABLE_DIR / "capacity_matched_rule_lift.csv",
        "winner_injury_audit": OUTPUT_TABLE_DIR / "winner_injury_audit.csv",
        "accepted_mae10_audit": OUTPUT_TABLE_DIR / "accepted_mae10_audit.csv",
        "fast_fail_ablation_readout": OUTPUT_TABLE_DIR / "fast_fail_ablation_readout.csv",
        "pre_dedup_09c_replay_diagnostic": OUTPUT_TABLE_DIR / "pre_dedup_09c_replay_diagnostic.csv",
        "model_registry": OUTPUT_TABLE_DIR / "model_registry.csv",
        "post_dedup_fast_fail_scores": OUTPUT_LOCAL_CACHE_DIR / "post_dedup_fast_fail_scores.parquet",
        "report": OUTPUT_REPORT,
        "manifest": OUTPUT_MANIFEST,
    }


OUTPUT_SCHEMA_BY_KEY = {
    "input_artifact_audit": INPUT_ARTIFACT_AUDIT_COLUMNS,
    "fast_fail_power_gate_readout": POWER_GATE_COLUMNS,
    "fast_fail_threshold_frontier": FRONTIER_COLUMNS,
    "capacity_matched_rule_lift": LIFT_COLUMNS,
    "winner_injury_audit": INJURY_COLUMNS,
    "accepted_mae10_audit": MAE_COLUMNS,
    "fast_fail_ablation_readout": ABLATION_COLUMNS,
    "pre_dedup_09c_replay_diagnostic": PREDEDUP_COLUMNS,
    "model_registry": MODEL_REGISTRY_COLUMNS,
    "post_dedup_fast_fail_scores": SCORE_COLUMNS,
}


def pre_dedup_only_enabled(config: dict[str, Any]) -> bool:
    return boolish(config.get("diagnostics", {}).get("enable_pre_dedup_replay_without_10a_cache", False))


def can_run_pre_dedup_only(config: dict[str, Any], paths: dict[str, Path], failures: list[str]) -> bool:
    if not pre_dedup_only_enabled(config) or not paths["upstream_09c_event_scores"].is_file():
        return False
    if not failures:
        return False
    failure_artifacts = {failure.split(":", 1)[0] for failure in failures}
    return failure_artifacts == {"upstream_10a_event_bindings"}


def build_pre_dedup_only_replay(paths: dict[str, Path]) -> pd.DataFrame:
    scores_path = paths["upstream_09c_event_scores"]
    manifest_path = paths["upstream_09c_manifest"]
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    selected_threshold = str(manifest.get("selected_threshold_id", ""))
    scores = pd.read_csv(scores_path)
    required = {
        "event_split",
        "rejected_flag",
        "selected_fast_fail_10_label",
        "score",
        "model_id",
        "threshold_id",
    }
    missing = sorted(required - set(scores.columns))
    if missing:
        return pd.DataFrame(
            [
                {
                    "score_source": "09C_hybrid_prededup_event_scores",
                    "model_id_09c": "",
                    "threshold_id_09c": selected_threshold,
                    "split": "all",
                    "joined_post_dedup_admitted_n": 0,
                    "diagnostic_rejected_n": 0,
                    "diagnostic_rejected_fast_fail_positive_n": 0,
                    "diagnostic_capture_rate": np.nan,
                    "overlap_with_10b_selected_rejected_n": 0,
                    "diagnostic_status": "schema_missing",
                    "note": "missing_columns:" + ";".join(missing),
                }
            ],
            columns=PREDEDUP_COLUMNS,
        )
    if selected_threshold:
        scores = scores.loc[scores["threshold_id"].astype(str).eq(selected_threshold)].copy()
    rows = []
    for split, part in scores.groupby("event_split", dropna=False):
        rejected = part["rejected_flag"].map(boolish)
        positives = part["selected_fast_fail_10_label"].map(boolish)
        rows.append(
            {
                "score_source": "09C_hybrid_prededup_event_scores",
                "model_id_09c": str(part["model_id"].dropna().iloc[0]) if part["model_id"].notna().any() else "",
                "threshold_id_09c": selected_threshold,
                "split": split,
                "joined_post_dedup_admitted_n": 0,
                "diagnostic_rejected_n": int(rejected.sum()),
                "diagnostic_rejected_fast_fail_positive_n": int((rejected & positives).sum()),
                "diagnostic_capture_rate": safe_div(int((rejected & positives).sum()), int(positives.sum())),
                "overlap_with_10b_selected_rejected_n": 0,
                "diagnostic_status": "pre_dedup_only",
                "note": "10A_post_dedup_cache_unavailable_diagnostic_only",
            }
        )
    return pd.DataFrame(rows, columns=PREDEDUP_COLUMNS)


def write_blocked_outputs(
    config_path: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    audit: pd.DataFrame,
    failures: list[str],
    decision: str = DECISION_INPUT_BLOCKED,
) -> dict[str, Any]:
    outputs = output_paths(config)
    write_df(outputs["input_artifact_audit"], audit)
    for key, columns in OUTPUT_SCHEMA_BY_KEY.items():
        if key == "input_artifact_audit":
            continue
        write_df(outputs[key], empty_frame(columns))
    report = build_report(
        decision,
        {},
        failures,
        empty_frame(FRONTIER_COLUMNS),
        empty_frame(POWER_GATE_COLUMNS),
        failures,
        config,
    )
    write_text(outputs["report"], report)
    manifest = build_manifest(config_path, config, paths, outputs, decision, {}, failures)
    write_json(outputs["manifest"], manifest)
    return manifest


def write_pre_dedup_only_outputs(
    config_path: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    audit: pd.DataFrame,
    failures: list[str],
) -> dict[str, Any]:
    outputs = output_paths(config)
    selected = {"reason": "pre_dedup_replay_without_10a_post_dedup_cache", "source_caveated": False}
    write_df(outputs["input_artifact_audit"], audit)
    for key, columns in OUTPUT_SCHEMA_BY_KEY.items():
        if key in {"input_artifact_audit", "pre_dedup_09c_replay_diagnostic"}:
            continue
        write_df(outputs[key], empty_frame(columns))
    write_df(outputs["pre_dedup_09c_replay_diagnostic"], build_pre_dedup_only_replay(paths))
    report = build_report(
        DECISION_PRE_DEDUP_ONLY,
        selected,
        failures,
        empty_frame(FRONTIER_COLUMNS),
        empty_frame(POWER_GATE_COLUMNS),
        failures,
        config,
    )
    write_text(outputs["report"], report)
    manifest = build_manifest(config_path, config, paths, outputs, DECISION_PRE_DEDUP_ONLY, selected, failures)
    write_json(outputs["manifest"], manifest)
    return manifest


def build_manifest(
    config_path: Path,
    config: dict[str, Any],
    input_paths: dict[str, Path],
    outputs: dict[str, Path],
    decision: str,
    selected: dict[str, Any],
    failures: list[str],
) -> dict[str, Any]:
    existing_outputs = {key: path for key, path in outputs.items() if key != "manifest" and path.is_file()}
    return {
        "component_id": "10B_fast_fail_structural_gate",
        "decision": decision,
        "source_caveated": bool(selected.get("source_caveated", False)),
        "selected_population_id": config["defaults"]["selected_population_id"],
        "selected_denominator_id": config["defaults"]["selected_denominator_id"],
        "selected_model_id": selected.get("model_id", config["defaults"]["selected_model_id"]),
        "selected_capacity_id": selected.get("capacity_id"),
        "selected_threshold_id": selected.get("threshold_id"),
        "selected_operating_point": selected,
        "input_hashes": {key: hash_or_empty(path) for key, path in input_paths.items()},
        "output_hashes": {key: file_sha256(path) for key, path in existing_outputs.items()},
        "input_paths": {key: str(path) for key, path in input_paths.items()},
        "outputs": {key: str(path) for key, path in outputs.items()},
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "utility_weights_hash": canonical_json_hash(config["utility_weights"]),
        "requirement_hash": file_sha256(REQUIREMENT_PATH),
        "git_revision": git_revision(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "statuses": {
            "input_failures": failures,
            "selected_reason": selected.get("reason"),
            "supported_pass": bool(selected.get("supported_pass", False)),
            "gate_block_reasons": selected.get("gate_block_reasons", []),
        },
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_yaml(config_path)
    paths = {key: resolve_path(value) for key, value in config["paths"].items()}
    manifest_10a = load_json(paths["upstream_10a_manifest"]) if paths["upstream_10a_manifest"].is_file() else None
    audit = input_audit(paths, manifest_10a)
    failures = hard_input_failures(audit)
    if mode == "check-inputs":
        outputs = output_paths(config)
        write_df(outputs["input_artifact_audit"], audit)
        return {"input_failures": failures}
    if failures:
        if can_run_pre_dedup_only(config, paths, failures):
            return write_pre_dedup_only_outputs(config_path, config, paths, audit, failures)
        return write_blocked_outputs(config_path, config, paths, audit, failures)

    population = pd.read_csv(paths["upstream_10a_population_contract"])
    sample_count = pd.read_csv(paths["upstream_10a_sample_count_by_split"])
    power = pd.read_csv(paths["upstream_10a_fast_fail_power_audit"])
    power_config = pd.read_csv(paths["upstream_10a_power_audit_config"])
    bindings = pd.read_parquet(paths["upstream_10a_event_bindings"])
    feature_contract = pd.read_csv(paths["upstream_09b_feature_contract"])
    feature_matrix = pd.read_parquet(paths["upstream_09b_feature_matrix"])
    weights = pd.read_parquet(paths["upstream_09b_sample_weights"])
    labels = pd.read_parquet(paths["upstream_08_event_labels"])

    failures.extend(
        validate_loaded_schemas(
            population,
            sample_count,
            power,
            power_config,
            bindings,
            feature_contract,
            feature_matrix,
            weights,
            labels,
        )
    )
    if failures:
        return write_blocked_outputs(config_path, config, paths, audit, failures)

    failures.extend(check_expected_sanity(config, sample_count, population))
    frame, prep_failures = prepare_default_frame(bindings, feature_matrix, weights, labels, config)
    failures.extend(prep_failures)
    feature_cols, missing_contract_features = feature_columns(feature_contract, feature_matrix)
    if missing_contract_features:
        # Missing non-selected allowed features are not fatal because feature_contract can outlive feature_matrix;
        # model_registry records the actually used feature list.
        pass
    rule_status = rule_baseline_status(feature_contract, frame, config["rule_baseline"]["required_features"])
    if rule_status != "pass":
        failures.append("rule_baseline_status:input_blocked")
    ablation_drop_cols = ablation_drop_columns(feature_cols, feature_contract, config)
    if len(ablation_drop_cols) == 0:
        failures.append("ablation_status:family_name_unmatched")
    if failures:
        return write_blocked_outputs(config_path, config, paths, audit, failures)

    power_gate = build_power_gate_readout(power, config)
    full_result, full_meta = train_model(frame, feature_cols, config, FULL_ABLATION_ID)
    no_overlap_cols = [col for col in feature_cols if col not in ablation_drop_cols]
    ablation_result, ablation_meta = train_model(
        frame, no_overlap_cols, config, config["ablation"]["no_overlap_ablation_id"]
    )
    model_results = [full_result, ablation_result]
    registry = pd.DataFrame(
        [
            {
                "model_id": result.model_id,
                "ablation_id": result.ablation_id,
                "estimator": config["model"]["estimator"],
                "target": config["defaults"]["target_column"],
                "fit_split": config["defaults"]["fit_split"],
                "train_row_n": int((frame["split"] == config["defaults"]["fit_split"]).sum()),
                "train_positive_n": int(
                    frame.loc[frame["split"] == config["defaults"]["fit_split"], config["defaults"]["target_column"]]
                    .map(boolish)
                    .sum()
                ),
                "feature_n_input": meta["feature_n_input"],
                "feature_n_used": meta["feature_n_used"],
                "feature_n_dropped_constant": meta["feature_n_dropped_constant"],
                "feature_list_hash": stable_hash(list(result.feature_cols)),
                "preprocessing_fit_scope": "train",
                "sample_weight_column": "final_sample_weight",
                "random_state": config["model"]["random_state"],
                "model_status": result.status,
                "sklearn_version": sklearn.__version__,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
            }
            for result, meta in [(full_result, full_meta), (ablation_result, ablation_meta)]
        ]
    )
    if any(result.status != "pass" for result in model_results):
        failures.extend([f"model_status:{result.ablation_id}:{result.status}" for result in model_results if result.status != "pass"])
        return write_blocked_outputs(config_path, config, paths, audit, failures)

    selected_population = population.loc[
        (population["population_id"] == config["defaults"]["selected_population_id"])
        & (population["denominator_id"] == config["defaults"]["selected_denominator_id"])
        & (~population["readout_only_flag"].map(boolish))
    ].copy()
    frontier, lift, injury, mae, score_long, capacities = build_frontiers(
        frame, model_results, power_config, power_gate, selected_population, config
    )
    selected = select_operating_point(frontier, power_gate, config)
    is_pass, gate_reasons = supported_pass(selected, config)
    selected["supported_pass"] = is_pass
    selected["gate_block_reasons"] = gate_reasons
    selected["source_caveated"] = bool(manifest_10a.get("statuses", {}).get("source_caveated", False))

    if selected.get("selected"):
        selected_mask = (
            (frontier["model_id"] == selected["model_id"])
            & (frontier["ablation_id"] == selected["ablation_id"])
            & (frontier["capacity_id"] == selected["capacity_id"])
            & (frontier["split"] == config["defaults"]["fit_split"])
        )
        frontier["selected_operating_point_flag"] = selected_mask
        frontier["supported_pass_flag"] = bool(is_pass) & selected_mask
    else:
        frontier["selected_operating_point_flag"] = False
        frontier["supported_pass_flag"] = False

    ablation = build_ablation_readout(
        frontier,
        registry,
        selected,
        {FULL_ABLATION_ID: 0, config["ablation"]["no_overlap_ablation_id"]: len(ablation_drop_cols)},
    )
    if is_pass and selected.get("selected"):
        selected_ablation = frontier.loc[
            (frontier["ablation_id"] == config["ablation"]["no_overlap_ablation_id"])
            & (frontier["split"] == config["defaults"]["fit_split"])
            & (frontier["capacity_id"] == selected["capacity_id"])
        ]
        if not selected_ablation.empty:
            row = selected_ablation.iloc[0]
            if (
                row["capacity_matched_capture_lift_over_rule_baseline"] < 0
                and row["capacity_matched_capture_lift_over_random"] < 0
            ):
                is_pass = False
                gate_reasons.append("mechanism_overlap_dependent_ablation_collapse")
                selected["supported_pass"] = False
                selected["gate_block_reasons"] = gate_reasons
                frontier["supported_pass_flag"] = False

    prededup = build_prededup_replay(score_long, frame, paths, selected)
    if is_pass:
        decision = DECISION_SOURCE_CAVEATED_SUPPORTED if selected.get("source_caveated") else DECISION_SUPPORTED
    else:
        decision = DECISION_DIAGNOSTIC

    outputs = output_paths(config)
    write_df(outputs["input_artifact_audit"], audit)
    write_df(outputs["fast_fail_power_gate_readout"], power_gate)
    write_df(outputs["fast_fail_threshold_frontier"], frontier)
    write_df(outputs["capacity_matched_rule_lift"], lift)
    write_df(outputs["winner_injury_audit"], injury)
    write_df(outputs["accepted_mae10_audit"], mae)
    write_df(outputs["fast_fail_ablation_readout"], ablation)
    write_df(outputs["pre_dedup_09c_replay_diagnostic"], prededup)
    write_df(outputs["model_registry"], registry)
    write_df(outputs["post_dedup_fast_fail_scores"], score_long)
    write_text(outputs["report"], build_report(decision, selected, gate_reasons, frontier, power_gate, [], config))
    manifest = build_manifest(config_path, config, paths, outputs, decision, selected, [])
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
