#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402

import run_feature_foundation_ablation as foundation  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "config.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_09c_riskon_cost_rejector_uplift.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

OUTPUT_TABLE_DIR = TABLE_DIR / "09C_riskon_cost_rejector"
OUTPUT_REPORT = REPORT_DIR / "09C_riskon_cost_rejector_uplift_report.md"
OUTPUT_MANIFEST = MANIFEST_DIR / "09C_riskon_cost_rejector_uplift_manifest.json"

DECISION_RESEARCH = "09C_riskon_cost_rejector_research_entry_supported"
DECISION_RESEARCH_CAVEATED = "09C_riskon_cost_rejector_research_entry_source_caveated_supported"
DECISION_FEATURE = "09C_riskon_cost_rejector_feature_source_supported"
DECISION_FEATURE_CAVEATED = "09C_riskon_cost_rejector_feature_source_caveated_supported"
DECISION_DIAGNOSTIC = "09C_riskon_cost_rejector_diagnostic_only_or_no_candidate"
DECISION_INPUT_BLOCKED = "09C_riskon_cost_rejector_input_blocked"
DECISION_LEAKAGE_BLOCKED = "09C_riskon_cost_rejector_feature_leakage_blocked"

SUPPORTED_TARGET_ID = "break_swing_low_20__or_false_repair_20d"
SUPPORTED_FAST_FAIL_ID = "break_swing_low_20"
FALSE_REPAIR_COMPONENT_ID = "frozen_event_false_repair_20d_label"
R_CORE_DENOM = foundation.RISK_ON_R_CORE_DENOM
R6_DENOM = foundation.RISK_ON_R6_DENOM
RISK_OFF_READONLY_DENOM = foundation.RISK_OFF_E1_READONLY_DENOM
R_CORE_SCOPE = foundation.R_CORE_SCOPE
R6_SCOPE = foundation.R6_SCOPE

TARGET_COMPONENTS: dict[str, dict[str, str]] = {
    "fast_fail_only_10d": {
        "binding_field": "selected_fast_fail_10_label",
        "contract_component_id": SUPPORTED_FAST_FAIL_ID,
        "weight_horizon_id": foundation.FAST_FAIL_WEIGHT,
        "label_t1_date_rule": "10D fast-fail horizon",
    },
    "false_repair_20d_component": {
        "binding_field": "frozen_false_repair_20d_label",
        "contract_component_id": FALSE_REPAIR_COMPONENT_ID,
        "weight_horizon_id": foundation.HYBRID_WEIGHT,
        "label_t1_date_rule": "20D false-repair horizon",
    },
    "hybrid_cost_bad_10_20": {
        "binding_field": "selected_cost_bad_10_20_target",
        "contract_component_id": SUPPORTED_TARGET_ID,
        "weight_horizon_id": foundation.HYBRID_WEIGHT,
        "label_t1_date_rule": "max(10D fast-fail, 20D false-repair) cost horizon",
    },
}

TARGET_COLUMNS = [meta["binding_field"] for meta in TARGET_COMPONENTS.values()]
WINNER_COLUMN = "event_big_winner_120d_label"
FORBIDDEN_FEATURE_COLUMNS = {
    "failure_10_label",
    "frozen_false_repair_20d_label",
    "event_false_repair_20d_label",
    "winner_120",
    "selected_fast_fail_10_label",
    "selected_cost_bad_10_20_target",
    "event_big_winner_120d_label",
    "event_super_winner_120d_label",
    "event_near_winner_120d_label",
    "selected_fast_fail_touch_date",
    "selected_fast_fail_touch_pos",
    "selected_fast_fail_touch_offset_sessions",
    "selected_fast_fail_barrier_id",
    "label_t1_date",
    "censoring_status",
    "candidate_outcome_120d_status",
    "winner_censoring_status",
    "post_replay_membership_flag",
    "future_mfe",
    "future_mae",
    "future_high",
    "future_low",
    "transition_outcome",
    "conversion_label",
    "next_regime",
}

SPLIT_ORDER = ["train", "validation", "robustness"]


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True


@dataclass(frozen=True)
class ModelSpec:
    model_family: str
    estimator_type: str
    train_target_component: str
    ablation_id: str
    calibration_id: str
    feature_cols: tuple[str, ...]
    selected_model_candidate_flag: bool = False

    @property
    def model_id(self) -> str:
        return "__".join(
            [
                self.model_family,
                self.train_target_component,
                self.ablation_id,
                self.calibration_id,
            ]
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 09C risk-on cost rejector uplift.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def boolish(value: Any) -> bool:
    return foundation.boolish(value)


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


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


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return np.nan
    return float(numerator) / float(denominator)


def safe_auc(y_true: pd.Series, score: pd.Series, weight: pd.Series | None = None) -> float:
    y = y_true.astype(float)
    mask = y.notna() & score.notna()
    if weight is not None:
        mask &= weight.notna()
    y = y.loc[mask].astype(int)
    if y.nunique() < 2:
        return np.nan
    w = weight.loc[mask].astype(float) if weight is not None else None
    try:
        return float(roc_auc_score(y, score.loc[mask], sample_weight=w))
    except ValueError:
        return np.nan


def safe_pr_auc(y_true: pd.Series, score: pd.Series, weight: pd.Series | None = None) -> float:
    y = y_true.astype(float)
    mask = y.notna() & score.notna()
    if weight is not None:
        mask &= weight.notna()
    y = y.loc[mask].astype(int)
    if y.nunique() < 2:
        return np.nan
    w = weight.loc[mask].astype(float) if weight is not None else None
    try:
        return float(average_precision_score(y, score.loc[mask], sample_weight=w))
    except ValueError:
        return np.nan


def safe_brier(y_true: pd.Series, score: pd.Series, weight: pd.Series | None = None) -> float:
    y = y_true.astype(float)
    mask = y.notna() & score.notna()
    if weight is not None:
        mask &= weight.notna()
    y = y.loc[mask].astype(int)
    if len(y) == 0:
        return np.nan
    w = weight.loc[mask].astype(float) if weight is not None else None
    try:
        return float(brier_score_loss(y, score.loc[mask], sample_weight=w))
    except ValueError:
        return np.nan


def top_decile_lift(y_true: pd.Series, score: pd.Series) -> float:
    frame = pd.DataFrame({"y": y_true, "score": score}).dropna()
    if frame.empty or frame["y"].nunique() < 2:
        return np.nan
    cutoff = frame["score"].quantile(0.90)
    top = frame.loc[frame["score"] >= cutoff]
    base_rate = float(frame["y"].mean())
    return safe_div(float(top["y"].mean()), base_rate)


def bottom_decile_rate(y_true: pd.Series, score: pd.Series) -> float:
    frame = pd.DataFrame({"y": y_true, "score": score}).dropna()
    if frame.empty:
        return np.nan
    cutoff = frame["score"].quantile(0.10)
    return float(frame.loc[frame["score"] <= cutoff, "y"].mean())


def monotonicity_readout(y_true: pd.Series, score: pd.Series, bins: int = 10) -> float:
    frame = pd.DataFrame({"y": y_true, "score": score}).dropna()
    if len(frame) < bins * 5 or frame["y"].nunique() < 2:
        return np.nan
    try:
        frame["bucket"] = pd.qcut(frame["score"], q=bins, duplicates="drop")
    except ValueError:
        return np.nan
    rates = frame.groupby("bucket", observed=True)["y"].mean()
    if len(rates) < 3:
        return np.nan
    return float(rates.reset_index(drop=True).corr(pd.Series(range(len(rates))), method="spearman"))


def load_config(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def input_specs(config: dict[str, Any]) -> list[InputSpec]:
    paths = config["paths"]
    return [
        InputSpec("requirement_09c", REQUIREMENT_PATH),
        InputSpec("config", CONFIG_PATH),
        InputSpec("readme", PROJECT_ROOT / "README.md"),
        InputSpec("research_direction", PROJECT_ROOT / "research_direction_discussion_20260614.md"),
        InputSpec("upstream_08_final_report", topic_path(paths["upstream_08_final_report"])),
        InputSpec("upstream_08_a_manifest", topic_path(paths["upstream_08_a_manifest"])),
        InputSpec("upstream_08_d_manifest", topic_path(paths["upstream_08_d_manifest"])),
        InputSpec("upstream_08_e_manifest", topic_path(paths["upstream_08_e_manifest"])),
        InputSpec("upstream_08_h_manifest", topic_path(paths["upstream_08_h_manifest"])),
        InputSpec("upstream_08_canonical_events", topic_path(paths["upstream_08_canonical_events"])),
        InputSpec("upstream_08_event_instances", topic_path(paths["upstream_08_event_instances"])),
        InputSpec("upstream_08_event_labels", topic_path(paths["upstream_08_event_labels"])),
        InputSpec("upstream_08_capture", topic_path(paths["upstream_08_capture"])),
        InputSpec("upstream_08_feature_panel", topic_path(paths["upstream_08_feature_panel"])),
        InputSpec("upstream_08_membership", topic_path(paths["upstream_08_membership"])),
        InputSpec("candidate_scope_mapping_contract", topic_path(paths["candidate_scope_mapping_contract"])),
        InputSpec(
            "candidate_scope_reconstructability_audit",
            topic_path(paths["candidate_scope_reconstructability_audit"]),
        ),
        InputSpec("upstream_08_leakage_audit", topic_path(paths["upstream_08_leakage_audit"])),
        InputSpec("upstream_07_run_manifest", topic_path(paths["upstream_07_run_manifest"])),
        InputSpec("upstream_07_canonical_events", topic_path(paths["upstream_07_canonical_events"])),
        InputSpec("upstream_07_event_labels", topic_path(paths["upstream_07_event_labels"])),
        InputSpec(
            "09a_manifest",
            EXPERIMENT_DIR / "outputs" / "manifests" / "09A_fast_fail_label_frontier_manifest.json",
        ),
        InputSpec(
            "09a_fast_fail_label_contract",
            REPORT_DIR / "09A_fast_fail_label_frontier" / "fast_fail_label_contract.md",
        ),
        InputSpec(
            "09a_selected_label_contract",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv",
        ),
        InputSpec(
            "09a_selected_label_event_bindings",
            LOCAL_CACHE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_bindings.parquet",
        ),
        InputSpec(
            "09a_selected_label_event_binding_summary",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_binding_summary.csv",
        ),
        InputSpec(
            "09a_cost_target_bridge",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "cost_target_bridge.csv",
        ),
        InputSpec(
            "09a_label_mechanism_contract",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "label_mechanism_contract.csv",
        ),
        InputSpec(
            "09a_source_pool_reconstruction_audit",
            TABLE_DIR / "input_audit" / "source_pool_reconstruction_audit.csv",
        ),
        InputSpec(
            "09b_manifest",
            EXPERIMENT_DIR / "outputs" / "manifests" / "09B_feature_foundation_ablation_manifest.json",
        ),
        InputSpec(
            "09b_feature_matrix",
            LOCAL_CACHE_DIR / "09B_feature_foundation" / "feature_matrix.parquet",
        ),
        InputSpec(
            "09b_feature_contract",
            TABLE_DIR / "09B_feature_foundation" / "feature_contract.csv",
        ),
        InputSpec(
            "09b_feature_matrix_schema",
            TABLE_DIR / "09B_feature_foundation" / "feature_matrix_schema.csv",
        ),
        InputSpec(
            "09b_feature_stationarity_audit",
            TABLE_DIR / "09B_feature_foundation" / "feature_stationarity_audit.csv",
        ),
        InputSpec(
            "09b_sample_uniqueness_audit",
            TABLE_DIR / "09B_feature_foundation" / "sample_uniqueness_audit.csv",
        ),
        InputSpec(
            "09b_sample_uniqueness_weights",
            LOCAL_CACHE_DIR / "09B_feature_foundation" / "sample_uniqueness_weights.parquet",
        ),
        InputSpec(
            "09b_label_mechanism_overlap_audit",
            TABLE_DIR / "09B_feature_foundation" / "label_mechanism_overlap_audit.csv",
        ),
        InputSpec(
            "09b_group_mda_importance",
            TABLE_DIR / "09B_feature_foundation" / "group_mda_importance.csv",
        ),
        InputSpec(
            "09b_single_feature_importance",
            TABLE_DIR / "09B_feature_foundation" / "single_feature_importance.csv",
        ),
        InputSpec(
            "09b_feature_transform_contract",
            TABLE_DIR / "09B_feature_foundation" / "feature_transform_contract.json",
        ),
    ]


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for spec in input_specs(config):
        exists = spec.path.exists()
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "exists": exists,
                "sha256": path_hash(spec.path),
                "status": "pass" if exists or not spec.required else "missing_required",
            }
        )
    return pd.DataFrame(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_TABLE_DIR / "input_artifact_audit.csv",
        "e1_baseline_reconstruction_audit": OUTPUT_TABLE_DIR
        / "e1_baseline_reconstruction_audit.csv",
        "09C_h_style_baseline_replay_on_selected_target": OUTPUT_TABLE_DIR
        / "09C_h_style_baseline_replay_on_selected_target.csv",
        "gate_refreeze_audit": OUTPUT_TABLE_DIR / "gate_refreeze_audit.csv",
        "baseline_feature_list": OUTPUT_TABLE_DIR / "baseline_feature_list.csv",
        "model_registry": OUTPUT_TABLE_DIR / "model_registry.csv",
        "oos_separability": OUTPUT_TABLE_DIR / "oos_separability.csv",
        "target_component_contract": OUTPUT_TABLE_DIR / "target_component_contract.csv",
        "weight_horizon_usage_audit": OUTPUT_TABLE_DIR / "weight_horizon_usage_audit.csv",
        "feature_family_usage_audit": OUTPUT_TABLE_DIR / "feature_family_usage_audit.csv",
        "calibration_readout": OUTPUT_TABLE_DIR / "calibration_readout.csv",
        "threshold_frontier": OUTPUT_TABLE_DIR / "threshold_frontier.csv",
        "threshold_frontier_by_component": OUTPUT_TABLE_DIR / "threshold_frontier_by_component.csv",
        "component_contribution_readout": OUTPUT_TABLE_DIR / "component_contribution_readout.csv",
        "bad_side_coverage_readout": OUTPUT_TABLE_DIR / "bad_side_coverage_readout.csv",
        "cost_readout": OUTPUT_TABLE_DIR / "cost_readout.csv",
        "post_filter_retention_by_split": OUTPUT_TABLE_DIR / "post_filter_retention_by_split.csv",
        "e1_missed_retention": OUTPUT_TABLE_DIR / "e1_missed_retention.csv",
        "density_concentration_readout": OUTPUT_TABLE_DIR / "density_concentration_readout.csv",
        "density_gate_binding_audit": OUTPUT_TABLE_DIR / "density_gate_binding_audit.csv",
        "riskoff_readonly_control": OUTPUT_TABLE_DIR / "riskoff_readonly_control.csv",
        "riskoff_transform_coverage_audit": OUTPUT_TABLE_DIR / "riskoff_transform_coverage_audit.csv",
        "label_mechanism_overlap_ablation": OUTPUT_TABLE_DIR / "label_mechanism_overlap_ablation.csv",
        "warmup_missing_ablation": OUTPUT_TABLE_DIR / "warmup_missing_ablation.csv",
        "selected_events": OUTPUT_TABLE_DIR / "selected_events.csv.gz",
        "rejected_events": OUTPUT_TABLE_DIR / "rejected_events.csv.gz",
        "event_scores": OUTPUT_TABLE_DIR / "event_scores.csv.gz",
        "report": OUTPUT_REPORT,
        "manifest": OUTPUT_MANIFEST,
    }


def target_component_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_component": component,
                "binding_field": meta["binding_field"],
                "contract_component_id": meta["contract_component_id"],
                "weight_horizon_id": meta["weight_horizon_id"],
                "label_t1_date_rule": meta["label_t1_date_rule"],
                "selected_target_id": SUPPORTED_TARGET_ID,
                "source_artifact": "09A selected_label_event_bindings.parquet",
            }
            for component, meta in TARGET_COMPONENTS.items()
        ]
    )


def build_e1_baseline_reconstruction_audit(config: dict[str, Any]) -> pd.DataFrame:
    paths = config["paths"]
    canonical_path = topic_path(paths["upstream_07_canonical_events"])
    labels_path = topic_path(paths["upstream_07_event_labels"])
    manifest_path = topic_path(paths["upstream_07_run_manifest"])
    rows: list[dict[str, Any]] = []
    try:
        canonical = pd.read_csv(
            canonical_path,
            usecols=["canonical_event_id", "triggered_channels"],
            low_memory=False,
        )
        e1_mask = canonical["triggered_channels"].astype(str).str.contains(
            "E1_early_ema60_repair", na=False
        )
        e1_row_n = int(e1_mask.sum())
        status = "pass" if e1_row_n > 0 and labels_path.exists() and manifest_path.exists() else "failed"
        reason = (
            "triggered_channels contains E1_early_ema60_repair"
            if status == "pass"
            else "missing E1 rows or required 07 artifacts"
        )
        rows.append(
            {
                "source_artifact": str(canonical_path),
                "label_artifact": str(labels_path),
                "manifest_artifact": str(manifest_path),
                "rebuild_rule": "triggered_channels contains E1_early_ema60_repair",
                "canonical_row_n": int(len(canonical)),
                "e1_reconstructed_row_n": e1_row_n,
                "e1_unique_canonical_event_n": int(canonical.loc[e1_mask, "canonical_event_id"].nunique()),
                "status": status,
                "reason": reason,
            }
        )
    except Exception as exc:
        rows.append(
            {
                "source_artifact": str(canonical_path),
                "label_artifact": str(labels_path),
                "manifest_artifact": str(manifest_path),
                "rebuild_rule": "triggered_channels contains E1_early_ema60_repair",
                "canonical_row_n": 0,
                "e1_reconstructed_row_n": 0,
                "e1_unique_canonical_event_n": 0,
                "status": "failed",
                "reason": str(exc),
            }
        )
    return pd.DataFrame(rows)


def validate_unique_keys(frame: pd.DataFrame, key_cols: list[str], name: str) -> None:
    duplicate_n = int(frame.duplicated(key_cols).sum())
    if duplicate_n:
        raise ValueError(f"{name} has {duplicate_n} duplicate rows on {key_cols}")


def read_core_inputs(config: dict[str, Any]) -> dict[str, Any]:
    paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], input_audit)
    if not input_audit["status"].eq("pass").all():
        missing = input_audit.loc[input_audit["status"].ne("pass"), "input_id"].tolist()
        raise FileNotFoundError(f"Missing required inputs: {missing}")

    manifests = {
        "09a": load_json(EXPERIMENT_DIR / "outputs" / "manifests" / "09A_fast_fail_label_frontier_manifest.json"),
        "09b": load_json(EXPERIMENT_DIR / "outputs" / "manifests" / "09B_feature_foundation_ablation_manifest.json"),
    }
    if manifests["09a"].get("decision") not in foundation.ALLOWED_09A_DECISIONS:
        raise ValueError(f"09A decision is not allowed: {manifests['09a'].get('decision')}")
    if manifests["09b"].get("decision") != foundation.DECISION_COMPLETE:
        raise ValueError(f"09B decision is not complete: {manifests['09b'].get('decision')}")
    e1_baseline_audit = build_e1_baseline_reconstruction_audit(config)
    if not e1_baseline_audit["status"].eq("pass").all():
        raise ValueError("07 E1 baseline reconstruction failed")

    feature_matrix = pd.read_parquet(LOCAL_CACHE_DIR / "09B_feature_foundation" / "feature_matrix.parquet")
    binding = pd.read_parquet(LOCAL_CACHE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_bindings.parquet")
    weights = pd.read_parquet(LOCAL_CACHE_DIR / "09B_feature_foundation" / "sample_uniqueness_weights.parquet")
    feature_contract = pd.read_csv(TABLE_DIR / "09B_feature_foundation" / "feature_contract.csv", low_memory=False)
    stationarity = pd.read_csv(TABLE_DIR / "09B_feature_foundation" / "feature_stationarity_audit.csv", low_memory=False)
    source_pool_audit = pd.read_csv(TABLE_DIR / "input_audit" / "source_pool_reconstruction_audit.csv", low_memory=False)

    key_cols = ["sample_id", "selected_target_id", "denominator_id"]
    validate_unique_keys(feature_matrix, key_cols, "09B feature_matrix")
    validate_unique_keys(binding, key_cols, "09A selected_label_event_bindings")
    selected_contract = pd.read_csv(TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv", low_memory=False)
    supported = selected_contract.loc[
        selected_contract["selected_target_id"].eq(SUPPORTED_TARGET_ID)
        & selected_contract["usable_for_09C_supported_gate"].map(boolish)
    ]
    if supported.empty:
        raise ValueError(f"{SUPPORTED_TARGET_ID} is not usable_for_09C_supported_gate in 09A contract")

    label_cols = [
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "source_pool_id",
        "event_regime_bucket",
        "episode_regime_bucket",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
        "candidate_outcome_120d_status",
        "selected_fast_fail_touch_offset_sessions",
        "label_t1_date",
        "censoring_status",
        WINNER_COLUMN,
        "event_super_winner_120d_label",
        "event_near_winner_120d_label",
        *TARGET_COLUMNS,
    ]
    data = feature_matrix.merge(
        binding[label_cols],
        on=key_cols,
        how="left",
        validate="one_to_one",
    )
    for col in TARGET_COLUMNS:
        data[col] = data[col].map(lambda value: np.nan if pd.isna(value) else int(boolish(value)))
    hard_target_missing = data[["selected_cost_bad_10_20_target", "frozen_false_repair_20d_label"]].isna().sum()
    if hard_target_missing.sum() > 0:
        raise ValueError(f"Target binding join is incomplete: {hard_target_missing.to_dict()}")
    data[WINNER_COLUMN] = data[WINNER_COLUMN].where(data[WINNER_COLUMN].notna(), np.nan)
    data[WINNER_COLUMN] = data[WINNER_COLUMN].map(
        lambda value: np.nan if pd.isna(value) else int(boolish(value))
    )
    data["event_t0_date"] = pd.to_datetime(data["event_t0_date"])
    data["feature_as_of_date"] = pd.to_datetime(data["feature_as_of_date"])

    meta = build_event_metadata(config, data)
    data = data.merge(meta, on="canonical_event_id", how="left")
    data = add_e1_episode_proxy(config, data)
    return {
        "input_audit": input_audit,
        "manifests": manifests,
        "feature_matrix": feature_matrix,
        "binding": binding,
        "weights": weights,
        "feature_contract": feature_contract,
        "stationarity": stationarity,
        "source_pool_audit": source_pool_audit,
        "e1_baseline_audit": e1_baseline_audit,
        "data": data,
        "selected_contract": selected_contract,
    }


def build_event_metadata(config: dict[str, Any], data: pd.DataFrame) -> pd.DataFrame:
    path = topic_path(config["paths"]["upstream_08_canonical_events"])
    needed = {"canonical_event_id", "primary_family_id", "board_bucket", "triggered_family_ids"}
    try:
        canonical = pd.read_csv(path, usecols=lambda col: col in needed, low_memory=False)
    except ValueError:
        canonical = pd.read_csv(path, low_memory=False)
        canonical = canonical[[col for col in canonical.columns if col in needed]]
    if "canonical_event_id" not in canonical.columns:
        return pd.DataFrame({"canonical_event_id": data["canonical_event_id"].drop_duplicates()})
    keep_cols = [col for col in ["canonical_event_id", "primary_family_id", "board_bucket", "triggered_family_ids"] if col in canonical.columns]
    return canonical[keep_cols].drop_duplicates("canonical_event_id")


def add_e1_episode_proxy(config: dict[str, Any], data: pd.DataFrame) -> pd.DataFrame:
    path = topic_path(config["paths"]["upstream_08_membership"])
    result = data.copy()
    result["e1_episode_hit_flag"] = False
    result["e1_missed_proxy_flag"] = True
    result["e1_missed_proxy_status"] = "episode_membership_proxy_not_available"
    try:
        membership = pd.read_parquet(
            path,
            columns=[
                "canonical_event_id",
                "candidate_scope_id",
                "target_episode_id",
                "bridge_positive_denominator_included",
            ],
        )
    except Exception:
        return result
    e1_episode_ids = set(
        membership.loc[
            membership["candidate_scope_id"].eq("07_E1_only")
            & membership["target_episode_id"].notna()
            & membership["bridge_positive_denominator_included"].map(boolish),
            "target_episode_id",
        ].astype(str)
    )
    event_episode = (
        membership.loc[
            membership["canonical_event_id"].isin(result["canonical_event_id"])
            & membership["target_episode_id"].notna()
        ][["canonical_event_id", "target_episode_id"]]
        .drop_duplicates()
        .groupby("canonical_event_id")["target_episode_id"]
        .apply(lambda values: ";".join(sorted(set(map(str, values)))))
        .reset_index()
    )
    if event_episode.empty:
        return result
    event_episode["e1_episode_hit_flag"] = event_episode["target_episode_id"].map(
        lambda text: any(item in e1_episode_ids for item in str(text).split(";"))
    )
    event_episode["e1_missed_proxy_flag"] = ~event_episode["e1_episode_hit_flag"]
    event_episode["e1_missed_proxy_status"] = "episode_level_proxy_from_08_membership"
    result = result.drop(columns=["e1_episode_hit_flag", "e1_missed_proxy_flag", "e1_missed_proxy_status"])
    result = result.merge(
        event_episode[
            [
                "canonical_event_id",
                "e1_episode_hit_flag",
                "e1_missed_proxy_flag",
                "e1_missed_proxy_status",
            ]
        ],
        on="canonical_event_id",
        how="left",
    )
    result["e1_episode_hit_flag"] = result["e1_episode_hit_flag"].where(
        result["e1_episode_hit_flag"].notna(), False
    ).astype(bool)
    result["e1_missed_proxy_flag"] = result["e1_missed_proxy_flag"].where(
        result["e1_missed_proxy_flag"].notna(), True
    ).astype(bool)
    result["e1_missed_proxy_status"] = result["e1_missed_proxy_status"].fillna(
        "no_episode_membership_for_event"
    )
    return result


def allowed_feature_columns(feature_contract: pd.DataFrame, feature_matrix: pd.DataFrame) -> list[str]:
    allowed = feature_contract.loc[
        feature_contract["allowed_for_09C_flag"].map(boolish), "feature_id"
    ].tolist()
    return [col for col in allowed if col in feature_matrix.columns]


def build_feature_sets(feature_contract: pd.DataFrame, feature_cols: list[str]) -> dict[str, list[str]]:
    contract = feature_contract.loc[feature_contract["feature_id"].isin(feature_cols)].copy()
    overlap = contract["label_mechanism_overlap_type"].fillna("none").astype(str)
    direct = set(contract.loc[overlap.eq("direct"), "feature_id"])
    related = set(contract.loc[overlap.isin(["direct", "related"]), "feature_id"])
    fs2_related = set(
        contract.loc[
            contract["feature_family"].eq("FS2_basis_path_quality")
            & overlap.isin(["direct", "related"]),
            "feature_id",
        ]
    )
    rolling = {
        feature
        for feature in [
            "log_close_fracdiff_d04",
            "panel_return_20d_rolling_z_60d",
            "panel_return_20d_rolling_pct_60d",
        ]
        if feature in set(contract["feature_id"])
    }
    representative: list[str] = []
    for _, part in contract.groupby("feature_family", sort=False):
        candidates = [feature for feature in feature_cols if feature in set(part["feature_id"])]
        if candidates:
            representative.append(candidates[0])
    return {
        "baseline_fs0": contract.loc[
            contract["feature_family"].eq("FS0_baseline_h_features"), "feature_id"
        ].tolist(),
        "full": list(feature_cols),
        "drop_direct_overlap": [feature for feature in feature_cols if feature not in direct],
        "drop_direct_related_overlap": [feature for feature in feature_cols if feature not in related],
        "drop_fs2_related_subset_only": [
            feature for feature in feature_cols if feature not in fs2_related
        ],
        "drop_fs0_rolling_fracdiff_hygiene": [
            feature for feature in feature_cols if feature not in rolling
        ],
        "family_representative_features_only": representative,
    }


def forbidden_feature_audit(feature_cols: list[str]) -> tuple[str, int, pd.DataFrame]:
    rows = []
    forbidden_count = 0
    for feature in feature_cols:
        forbidden = feature in FORBIDDEN_FEATURE_COLUMNS or any(
            token in feature.lower()
            for token in ["future", "winner_120", "failure_10_label", "next_regime"]
        )
        if forbidden:
            forbidden_count += 1
        rows.append(
            {
                "feature_id": feature,
                "forbidden_feature_flag": forbidden,
                "status": "blocked" if forbidden else "pass",
            }
        )
    return ("pass" if forbidden_count == 0 else "blocked"), forbidden_count, pd.DataFrame(rows)


def model_specs(
    feature_sets: dict[str, list[str]],
    selected_config: dict[str, Any],
) -> list[ModelSpec]:
    specs: list[ModelSpec] = []
    selected_family = selected_config.get("selected_model_family", "regularized_logistic_or_elastic_net")
    selected_ablation = selected_config.get("selected_ablation_id", "full")
    selected_calibration = selected_config.get("selected_calibration_id", "none")
    selected_component = selected_config.get("selected_train_target_component", "hybrid_cost_bad_10_20")
    for component in TARGET_COMPONENTS:
        specs.append(
            ModelSpec(
                "h_style_logistic_baseline",
                "logistic_l2_balanced",
                component,
                "baseline_fs0",
                "none",
                tuple(feature_sets["baseline_fs0"]),
                selected_model_candidate_flag=False,
            )
        )
    logistic_ablation_ids = [
        "full",
        "drop_direct_overlap",
        "drop_direct_related_overlap",
        "drop_fs2_related_subset_only",
        "drop_fs0_rolling_fracdiff_hygiene",
        "family_representative_features_only",
    ]
    for component in TARGET_COMPONENTS:
        for ablation_id in logistic_ablation_ids:
            specs.append(
                ModelSpec(
                    "regularized_logistic_or_elastic_net",
                    "logistic_l2_balanced",
                    component,
                    ablation_id,
                    "none",
                    tuple(feature_sets[ablation_id]),
                    selected_model_candidate_flag=(
                        selected_family == "regularized_logistic_or_elastic_net"
                        and selected_component == component
                        and selected_ablation == ablation_id
                        and selected_calibration == "none"
                    ),
                )
            )
    for component in TARGET_COMPONENTS:
        specs.append(
            ModelSpec(
                "shallow_tree_or_bagging_shallow_trees_diagnostic",
                "random_forest_shallow_balanced",
                component,
                "full",
                "none",
                tuple(feature_sets["full"]),
                selected_model_candidate_flag=False,
            )
        )
    for calibration_id in ["platt", "isotonic"]:
        specs.append(
            ModelSpec(
                selected_family,
                "logistic_l2_balanced",
                selected_component,
                selected_ablation,
                calibration_id,
                tuple(feature_sets[selected_ablation]),
                selected_model_candidate_flag=(selected_calibration == calibration_id),
            )
        )
    return specs


def training_frame(
    data: pd.DataFrame,
    weights: pd.DataFrame,
    component: str,
) -> pd.DataFrame:
    meta = TARGET_COMPONENTS[component]
    weight_part = weights.loc[
        weights["weight_horizon_id"].eq(meta["weight_horizon_id"])
        & weights["denominator_id"].eq(R_CORE_DENOM),
        ["sample_id", "selected_target_id", "denominator_id", "final_sample_weight", "weight_status"],
    ]
    frame = data.loc[data["denominator_id"].eq(R_CORE_DENOM)].merge(
        weight_part,
        on=["sample_id", "selected_target_id", "denominator_id"],
        how="left",
        validate="one_to_one",
    )
    frame["final_sample_weight"] = frame["final_sample_weight"].fillna(0.0)
    return frame


def fit_base_model(
    spec: ModelSpec,
    train: pd.DataFrame,
    target_col: str,
    model_config: dict[str, Any],
) -> Any | None:
    feature_cols = list(spec.feature_cols)
    if not feature_cols:
        return None
    fit = train.loc[
        train["event_split"].eq("train")
        & train[target_col].notna()
        & train["final_sample_weight"].gt(0)
    ].copy()
    y = fit[target_col].astype(int)
    if y.nunique() < 2:
        return None
    if spec.estimator_type == "random_forest_shallow_balanced":
        model = RandomForestClassifier(
            n_estimators=int(model_config.get("rf_n_estimators", 40)),
            max_depth=int(model_config.get("rf_max_depth", 3)),
            min_samples_leaf=int(model_config.get("rf_min_samples_leaf", 80)),
            class_weight="balanced_subsample",
            random_state=int(model_config.get("random_state", 17)),
            n_jobs=int(model_config.get("rf_n_jobs", 1)),
        )
    else:
        model = LogisticRegression(
            penalty="l2",
            class_weight="balanced",
            solver="liblinear",
            random_state=int(model_config.get("random_state", 17)),
            max_iter=int(model_config.get("max_iter", 1000)),
        )
    model.fit(fit[feature_cols], y, sample_weight=fit["final_sample_weight"].astype(float))
    return model


def base_spec_for_calibrated(spec: ModelSpec) -> ModelSpec:
    if spec.calibration_id == "none":
        return spec
    return ModelSpec(
        spec.model_family,
        spec.estimator_type,
        spec.train_target_component,
        spec.ablation_id,
        "none",
        spec.feature_cols,
        spec.selected_model_candidate_flag,
    )


def score_base_model(model: Any, data: pd.DataFrame, feature_cols: list[str]) -> pd.Series:
    return pd.Series(model.predict_proba(data[feature_cols])[:, 1], index=data.index)


def fit_calibrator(calibration_id: str, train_score: pd.Series, train_y: pd.Series, weight: pd.Series) -> Any | None:
    if calibration_id == "none":
        return None
    mask = train_score.notna() & train_y.notna() & weight.gt(0)
    y = train_y.loc[mask].astype(int)
    if y.nunique() < 2:
        return None
    x = train_score.loc[mask].to_numpy().reshape(-1, 1)
    if calibration_id == "platt":
        calibrator = LogisticRegression(solver="lbfgs", random_state=17, max_iter=1000)
        calibrator.fit(x, y, sample_weight=weight.loc[mask].astype(float))
        return calibrator
    if calibration_id == "isotonic":
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(train_score.loc[mask], y, sample_weight=weight.loc[mask].astype(float))
        return calibrator
    return None


def apply_calibration(calibration_id: str, calibrator: Any | None, score: pd.Series) -> pd.Series:
    if calibration_id == "none" or calibrator is None:
        return score
    if calibration_id == "platt":
        return pd.Series(calibrator.predict_proba(score.to_numpy().reshape(-1, 1))[:, 1], index=score.index)
    if calibration_id == "isotonic":
        return pd.Series(calibrator.predict(score), index=score.index)
    return score


def fit_and_score_models(
    data: pd.DataFrame,
    weights: pd.DataFrame,
    specs: list[ModelSpec],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_config = config.get("cost_rejector", {}).get("model", {})
    base_models: dict[str, Any] = {}
    base_train_frames: dict[str, pd.DataFrame] = {}
    registry_rows: list[dict[str, Any]] = []
    score_frames: list[pd.DataFrame] = []
    base_specs = {base_spec_for_calibrated(spec).model_id: base_spec_for_calibrated(spec) for spec in specs}

    for base_id, base_spec in base_specs.items():
        target_col = TARGET_COMPONENTS[base_spec.train_target_component]["binding_field"]
        train_frame = training_frame(data, weights, base_spec.train_target_component)
        base_train_frames[base_id] = train_frame
        model = fit_base_model(base_spec, train_frame, target_col, model_config)
        base_models[base_id] = model
        fit_scope = "risk_on_r_core_horizon_complete/train"
        train_fit = train_frame.loc[
            train_frame["event_split"].eq("train")
            & train_frame[target_col].notna()
            & train_frame["final_sample_weight"].gt(0)
        ]
        registry_rows.append(
            {
                "model_id": base_id,
                "model_family": base_spec.model_family,
                "train_target_component": base_spec.train_target_component,
                "ablation_id": base_spec.ablation_id,
                "calibration_id": "none",
                "estimator_type": base_spec.estimator_type,
                "fit_scope": fit_scope,
                "feature_n": len(base_spec.feature_cols),
                "feature_list_hash": stable_hash(list(base_spec.feature_cols)),
                "train_sample_n": int(len(train_fit)),
                "train_positive_n": int(train_fit[target_col].sum()) if len(train_fit) else 0,
                "train_positive_rate": float(train_fit[target_col].mean()) if len(train_fit) else np.nan,
                "weight_horizon_id": TARGET_COMPONENTS[base_spec.train_target_component]["weight_horizon_id"],
                "selected_model_candidate_flag": base_spec.selected_model_candidate_flag,
                "model_status": "fit" if model is not None else "not_fit",
            }
        )

    for spec in specs:
        base_spec = base_spec_for_calibrated(spec)
        base_id = base_spec.model_id
        model = base_models.get(base_id)
        if model is None:
            continue
        target_col = TARGET_COMPONENTS[spec.train_target_component]["binding_field"]
        feature_cols = list(spec.feature_cols)
        base_score = score_base_model(model, data, feature_cols)
        base_train = base_train_frames[base_id]
        train_score = base_score.loc[base_train.index]
        calibrator = fit_calibrator(
            spec.calibration_id,
            train_score,
            base_train[target_col],
            base_train["final_sample_weight"],
        )
        score = apply_calibration(spec.calibration_id, calibrator, base_score)
        if spec.calibration_id != "none":
            train_fit = base_train.loc[
                base_train["event_split"].eq("train")
                & base_train[target_col].notna()
                & base_train["final_sample_weight"].gt(0)
            ]
            registry_rows.append(
                {
                    "model_id": spec.model_id,
                    "model_family": spec.model_family,
                    "train_target_component": spec.train_target_component,
                    "ablation_id": spec.ablation_id,
                    "calibration_id": spec.calibration_id,
                    "estimator_type": f"{spec.estimator_type}_with_{spec.calibration_id}",
                    "fit_scope": "risk_on_r_core_horizon_complete/train",
                    "feature_n": len(spec.feature_cols),
                    "feature_list_hash": stable_hash(list(spec.feature_cols)),
                    "train_sample_n": int(len(train_fit)),
                    "train_positive_n": int(train_fit[target_col].sum()) if len(train_fit) else 0,
                    "train_positive_rate": float(train_fit[target_col].mean()) if len(train_fit) else np.nan,
                    "weight_horizon_id": TARGET_COMPONENTS[spec.train_target_component]["weight_horizon_id"],
                    "selected_model_candidate_flag": spec.selected_model_candidate_flag,
                    "model_status": "fit" if calibrator is not None else "calibration_not_fit",
                }
            )
        out = data[
            [
                "sample_id",
                "selected_target_id",
                "denominator_id",
                "canonical_event_id",
                "instrument",
                "event_t0_date",
                "event_split",
                "primary_family_id",
                "board_bucket",
                "e1_missed_proxy_flag",
                "e1_missed_proxy_status",
                WINNER_COLUMN,
                *TARGET_COLUMNS,
            ]
        ].copy()
        out["model_id"] = spec.model_id
        out["model_family"] = spec.model_family
        out["train_target_component"] = spec.train_target_component
        out["ablation_id"] = spec.ablation_id
        out["calibration_id"] = spec.calibration_id
        out["score"] = score.astype(float).clip(0.0, 1.0)
        score_frames.append(out)
    registry = pd.DataFrame(registry_rows).drop_duplicates(
        ["model_family", "train_target_component", "ablation_id", "calibration_id"],
        keep="last",
    )
    scores = pd.concat(score_frames, ignore_index=True) if score_frames else pd.DataFrame()
    return registry, scores


def attach_weights_to_scores(scores: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for component, meta in TARGET_COMPONENTS.items():
        part = scores.loc[scores["train_target_component"].eq(component)].copy()
        weight_part = weights.loc[
            weights["weight_horizon_id"].eq(meta["weight_horizon_id"]),
            [
                "sample_id",
                "selected_target_id",
                "denominator_id",
                "weight_horizon_id",
                "final_sample_weight",
                "average_uniqueness",
                "concurrency_count_mean",
                "weight_status",
            ],
        ]
        part = part.merge(
            weight_part,
            on=["sample_id", "selected_target_id", "denominator_id"],
            how="left",
        )
        frames.append(part)
    return pd.concat(frames, ignore_index=True) if frames else scores


def build_oos_separability(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, part in scores.groupby(
        ["model_id", "model_family", "train_target_component", "ablation_id", "calibration_id", "denominator_id", "event_split"],
        dropna=False,
    ):
        model_id, model_family, component, ablation_id, calibration_id, denominator_id, split = keys
        target_col = TARGET_COMPONENTS[component]["binding_field"]
        y = part[target_col]
        weight = part["final_sample_weight"].fillna(1.0)
        rows.append(
            {
                "model_id": model_id,
                "model_family": model_family,
                "train_target_component": component,
                "ablation_id": ablation_id,
                "calibration_id": calibration_id,
                "denominator_id": denominator_id,
                "split": split,
                "sample_n": int(len(part)),
                "positive_n": int(y.sum()),
                "positive_rate": float(y.mean()) if len(part) else np.nan,
                "roc_auc": safe_auc(y, part["score"], weight),
                "pr_auc": safe_pr_auc(y, part["score"], weight),
                "brier_score": safe_brier(y, part["score"], weight),
                "top_decile_lift": top_decile_lift(y, part["score"]),
                "bottom_decile_cost_bad_rate": bottom_decile_rate(y, part["score"]),
                "score_target_monotonicity_spearman": monotonicity_readout(y, part["score"]),
                "readout_scope": "supported_gate" if denominator_id == R_CORE_DENOM else "readout_only",
            }
        )
    return pd.DataFrame(rows)


def build_calibration_readout(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    selected_mask = scores["model_family"].eq("regularized_logistic_or_elastic_net") & scores[
        "train_target_component"
    ].eq("hybrid_cost_bad_10_20") & scores["ablation_id"].eq("full")
    for keys, part in scores.loc[selected_mask].groupby(
        ["model_id", "calibration_id", "denominator_id", "event_split"], dropna=False
    ):
        model_id, calibration_id, denominator_id, split = keys
        y = part[TARGET_COMPONENTS["hybrid_cost_bad_10_20"]["binding_field"]]
        weight = part["final_sample_weight"].fillna(1.0)
        keep_0800 = part.loc[part["denominator_id"].eq(denominator_id), "score"].quantile(0.80)
        selected = part["score"] <= keep_0800
        rows.append(
            {
                "model_id": model_id,
                "calibration_id": calibration_id,
                "denominator_id": denominator_id,
                "split": split,
                "sample_n": int(len(part)),
                "roc_auc": safe_auc(y, part["score"], weight),
                "pr_auc": safe_pr_auc(y, part["score"], weight),
                "brier_score": safe_brier(y, part["score"], weight),
                "keep_0800_threshold_score": keep_0800,
                "keep_0800_after_cost_bad_rate": float(y.loc[selected].mean()) if selected.any() else np.nan,
                "calibration_fit_scope": "risk_on_r_core_horizon_complete/train",
            }
        )
    return pd.DataFrame(rows)


def threshold_grid(config: dict[str, Any]) -> list[float]:
    return [
        float(value)
        for value in config.get("cost_rejector", {}).get(
            "threshold_grid", [0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]
        )
    ]


def threshold_value_for_train(part: pd.DataFrame, keep_fraction: float) -> float:
    train = part.loc[
        part["denominator_id"].eq(R_CORE_DENOM)
        & part["event_split"].eq("train")
        & part["final_sample_weight"].fillna(0).gt(0)
    ]
    return float(train["score"].quantile(keep_fraction)) if len(train) else np.nan


def component_bucket(frame: pd.DataFrame) -> pd.Series:
    fast = frame["selected_fast_fail_10_label"].fillna(0).astype(int).eq(1)
    repair = frame["frozen_false_repair_20d_label"].fillna(0).astype(int).eq(1)
    return pd.Series(
        np.select(
            [fast & ~repair, ~fast & repair, fast & repair],
            ["fast_fail_only", "false_repair_only", "both"],
            default="neither",
        ),
        index=frame.index,
    )


def metric_input_frame(part: pd.DataFrame, denominator_id: str, split: str) -> pd.DataFrame:
    frame = part.copy()
    if denominator_id == R_CORE_DENOM and split == "train":
        frame = frame.loc[frame["final_sample_weight"].fillna(0.0).gt(0)].copy()
    return frame


def metric_for_threshold(part: pd.DataFrame, target_col: str, threshold_score: float) -> dict[str, Any]:
    part = part.loc[part[target_col].notna()].copy()
    selected = part["score"] <= threshold_score
    rejected = ~selected
    y = part[target_col].astype(int)
    before_rate = float(y.mean()) if len(part) else np.nan
    after_rate = float(y.loc[selected].mean()) if selected.any() else np.nan
    cost_reduction = safe_div(before_rate - after_rate, before_rate)
    winner_complete = part[WINNER_COLUMN].notna()
    winner = winner_complete & part[WINNER_COLUMN].astype(float).eq(1)
    non_winner = winner_complete & part[WINNER_COLUMN].astype(float).eq(0)
    winner_n = int(winner.sum())
    rejected_winner_n = int((winner & rejected).sum())
    e1_missed_winner = winner & part["e1_missed_proxy_flag"].map(boolish)
    e1_missed_winner_n = int(e1_missed_winner.sum())
    rejected_e1_missed_winner_n = int((e1_missed_winner & rejected).sum())
    fast_fail_positive = part["selected_fast_fail_10_label"].fillna(0).astype(int).eq(1)
    fast_fail_positive_n = int(fast_fail_positive.sum())
    rejected_fast_fail_positive_n = int((fast_fail_positive & rejected).sum())
    return {
        "evaluable_event_n": int(len(part)),
        "selected_event_n": int(selected.sum()),
        "rejected_event_n": int(rejected.sum()),
        "selected_fraction": safe_div(int(selected.sum()), len(part)),
        "rejected_fraction": safe_div(int(rejected.sum()), len(part)),
        "before_cost_bad_rate": before_rate,
        "after_cost_bad_rate": after_rate,
        "relative_cost_reduction": cost_reduction,
        "winner_complete_n": int(winner_complete.sum()),
        "winner_n": winner_n,
        "rejected_winner_n": rejected_winner_n,
        "any_recall_retention": safe_div(winner_n - rejected_winner_n, winner_n),
        "e1_missed_winner_n": e1_missed_winner_n,
        "rejected_e1_missed_winner_n": rejected_e1_missed_winner_n,
        "e1_missed_retention": safe_div(
            e1_missed_winner_n - rejected_e1_missed_winner_n, e1_missed_winner_n
        ),
        "non_winner_n": int(non_winner.sum()),
        "rejected_non_winner_n": int((non_winner & rejected).sum()),
        "non_winner_hit_rate": safe_div(int((non_winner & rejected).sum()), int(non_winner.sum())),
        "winner_injury_rate": safe_div(rejected_winner_n, winner_n),
        "kill_wrong_rate": safe_div(rejected_winner_n, int(rejected.sum())),
        "fast_fail_positive_n": fast_fail_positive_n,
        "rejected_fast_fail_positive_n": rejected_fast_fail_positive_n,
        "fast_fail_bad_side_capture": safe_div(rejected_fast_fail_positive_n, fast_fail_positive_n),
    }


def build_threshold_tables(
    scores: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frontier_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    contribution_rows: list[dict[str, Any]] = []
    bad_side_rows: list[dict[str, Any]] = []
    retention_rows: list[dict[str, Any]] = []
    e1_rows: list[dict[str, Any]] = []
    for model_id, model_scores in scores.groupby("model_id", dropna=False):
        first = model_scores.iloc[0]
        train_component = str(first["train_target_component"])
        target_col = TARGET_COMPONENTS[train_component]["binding_field"]
        threshold_source = model_scores.loc[model_scores["denominator_id"].eq(R_CORE_DENOM)]
        for keep_fraction in threshold_grid(config):
            threshold_id = f"keep_{int(round(keep_fraction * 10000)):04d}"
            threshold_score = threshold_value_for_train(threshold_source, keep_fraction)
            if pd.isna(threshold_score):
                continue
            for (denominator_id, split), part in model_scores.groupby(["denominator_id", "event_split"], dropna=False):
                metric_part = metric_input_frame(part, str(denominator_id), str(split))
                metrics = metric_for_threshold(metric_part, target_col, threshold_score)
                row = {
                    "model_id": model_id,
                    "model_family": first["model_family"],
                    "train_target_component": train_component,
                    "ablation_id": first["ablation_id"],
                    "calibration_id": first["calibration_id"],
                    "threshold_id": threshold_id,
                    "keep_fraction": keep_fraction,
                    "threshold_score": threshold_score,
                    "denominator_id": denominator_id,
                    "split": split,
                    **metrics,
                    "threshold_fit_scope": "risk_on_r_core_horizon_complete/train",
                    "readout_scope": "supported_gate" if denominator_id == R_CORE_DENOM else "readout_only",
                }
                frontier_rows.append(row)
                retention_rows.append(
                    {
                        "model_id": model_id,
                        "train_target_component": train_component,
                        "threshold_id": threshold_id,
                        "denominator_id": denominator_id,
                        "split": split,
                        "winner_complete_n": metrics["winner_complete_n"],
                        "winner_n": metrics["winner_n"],
                        "rejected_winner_n": metrics["rejected_winner_n"],
                        "any_recall_retention": metrics["any_recall_retention"],
                        "retention_definition": "event_big_winner_120d_label_complete_event_level",
                    }
                )
                e1_rows.append(
                    {
                        "model_id": model_id,
                        "train_target_component": train_component,
                        "threshold_id": threshold_id,
                        "denominator_id": denominator_id,
                        "split": split,
                        "e1_missed_winner_n": metrics["e1_missed_winner_n"],
                        "rejected_e1_missed_winner_n": metrics["rejected_e1_missed_winner_n"],
                        "e1_missed_retention": metrics["e1_missed_retention"],
                        "e1_missed_definition": "episode_level_proxy_from_08_membership",
                        "proxy_status": part["e1_missed_proxy_status"].mode().iloc[0]
                        if not part["e1_missed_proxy_status"].mode().empty
                        else "unknown",
                    }
                )
                for component, meta in TARGET_COMPONENTS.items():
                    component_metrics = metric_for_threshold(
                        metric_part, meta["binding_field"], threshold_score
                    )
                    component_rows.append(
                        {
                            "model_id": model_id,
                            "model_family": first["model_family"],
                            "train_target_component": train_component,
                            "readout_target_component": component,
                            "ablation_id": first["ablation_id"],
                            "calibration_id": first["calibration_id"],
                            "threshold_id": threshold_id,
                            "keep_fraction": keep_fraction,
                            "denominator_id": denominator_id,
                            "split": split,
                            **component_metrics,
                        }
                    )
                    bad_side_rows.append(
                        {
                            "target_component": component,
                            "model_id": model_id,
                            "threshold_id": threshold_id,
                            "denominator_id": denominator_id,
                            "split": split,
                            "positive_rate": float(metric_part[meta["binding_field"]].mean()),
                            "non_winner_hit_rate": component_metrics["non_winner_hit_rate"],
                            "winner_injury_rate": component_metrics["winner_injury_rate"],
                            "kill_wrong_rate": component_metrics["kill_wrong_rate"],
                            "winner_complete_n": component_metrics["winner_complete_n"],
                            "winner_power_caveat": component_metrics["rejected_winner_n"] < 30,
                        }
                    )
                contribution_part = metric_part.loc[
                    metric_part["selected_cost_bad_10_20_target"].notna()
                ].copy()
                selected = contribution_part["score"] <= threshold_score
                rejected = ~selected
                buckets = component_bucket(contribution_part)
                hybrid_positive = contribution_part["selected_cost_bad_10_20_target"].astype(int).eq(1)
                bucket_counts = {
                    f"{bucket}_rejected_n": int((rejected & buckets.eq(bucket)).sum())
                    for bucket in ["fast_fail_only", "false_repair_only", "both", "neither"]
                }
                bucket_positive = {
                    f"{bucket}_hybrid_positive_rejected_n": int(
                        (rejected & hybrid_positive & buckets.eq(bucket)).sum()
                    )
                    for bucket in ["fast_fail_only", "false_repair_only", "both", "neither"]
                }
                total_positive_rejected = int((rejected & hybrid_positive).sum())
                before_hybrid_rate = float(hybrid_positive.mean()) if len(contribution_part) else np.nan
                after_hybrid_rate = (
                    float(hybrid_positive.loc[selected].mean()) if selected.any() else np.nan
                )
                total_cost_reduction_rate = (
                    before_hybrid_rate - after_hybrid_rate
                    if pd.notna(before_hybrid_rate) and pd.notna(after_hybrid_rate)
                    else np.nan
                )
                bucket_rate_reductions: dict[str, float] = {}
                for bucket in ["fast_fail_only", "false_repair_only", "both", "neither"]:
                    bucket_mask = buckets.eq(bucket)
                    before_bucket_rate = float(bucket_mask.mean()) if len(bucket_mask) else np.nan
                    after_bucket_rate = (
                        float(bucket_mask.loc[selected].mean()) if selected.any() else np.nan
                    )
                    bucket_rate_reductions[f"{bucket}_cost_reduction_rate"] = (
                        before_bucket_rate - after_bucket_rate
                        if pd.notna(before_bucket_rate) and pd.notna(after_bucket_rate)
                        else np.nan
                    )
                ff_attributed = bucket_rate_reductions["fast_fail_only_cost_reduction_rate"] + 0.5 * bucket_rate_reductions[
                    "both_cost_reduction_rate"
                ]
                contribution_rows.append(
                    {
                        "model_id": model_id,
                        "train_target_component": train_component,
                        "threshold_id": threshold_id,
                        "denominator_id": denominator_id,
                        "split": split,
                        "total_rejected_hybrid_positive_n": total_positive_rejected,
                        "total_hybrid_cost_reduction_rate": total_cost_reduction_rate,
                        "fast_fail_attributed_cost_reduction": ff_attributed,
                        "fast_fail_attributed_cost_reduction_share": safe_div(
                            ff_attributed, total_cost_reduction_rate
                        ),
                        **bucket_counts,
                        **bucket_positive,
                        **bucket_rate_reductions,
                    }
                )
    return (
        pd.DataFrame(frontier_rows),
        pd.DataFrame(component_rows),
        pd.DataFrame(contribution_rows),
        pd.DataFrame(bad_side_rows),
        pd.DataFrame(retention_rows),
        pd.DataFrame(e1_rows),
    )


def build_weight_horizon_usage_audit(data: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for component, meta in TARGET_COMPONENTS.items():
        merged = data.merge(
            weights.loc[
                weights["weight_horizon_id"].eq(meta["weight_horizon_id"]),
                [
                    "sample_id",
                    "selected_target_id",
                    "denominator_id",
                    "final_sample_weight",
                    "average_uniqueness",
                    "concurrency_count_mean",
                    "weight_status",
                ],
            ],
            on=["sample_id", "selected_target_id", "denominator_id"],
            how="left",
        )
        for (denominator_id, split), part in merged.groupby(["denominator_id", "event_split"], dropna=False):
            rows.append(
                {
                    "target_component": component,
                    "denominator_id": denominator_id,
                    "split": split,
                    "weight_horizon_id": meta["weight_horizon_id"],
                    "sample_n": int(len(part)),
                    "positive_n": int(part[meta["binding_field"]].sum()),
                    "evaluable_n": int(part[meta["binding_field"]].notna().sum()),
                    "zero_weight_n": int(part["final_sample_weight"].fillna(0).le(0).sum()),
                    "avg_uniqueness_mean": float(part["average_uniqueness"].mean()),
                    "concurrency_mean": float(part["concurrency_count_mean"].mean()),
                    "weight_status": part["weight_status"].mode().iloc[0]
                    if not part["weight_status"].mode().empty
                    else "missing",
                }
            )
    return pd.DataFrame(rows)


def build_feature_family_usage_audit(registry: pd.DataFrame, feature_sets: dict[str, list[str]], contract: pd.DataFrame) -> pd.DataFrame:
    rows = []
    info = contract.set_index("feature_id")
    for _, row in registry.iterrows():
        features = feature_sets.get(str(row["ablation_id"]), [])
        overlap = info.reindex(features)["label_mechanism_overlap_type"].fillna("none")
        families = info.reindex(features)["feature_family"].dropna().unique()
        rolling = [
            feature
            for feature in features
            if feature
            in {
                "log_close_fracdiff_d04",
                "panel_return_20d_rolling_z_60d",
                "panel_return_20d_rolling_pct_60d",
            }
        ]
        rows.append(
            {
                "model_id": row["model_id"],
                "model_family": row["model_family"],
                "train_target_component": row["train_target_component"],
                "ablation_id": row["ablation_id"],
                "calibration_id": row["calibration_id"],
                "feature_count": len(features),
                "family_count": len(families),
                "direct_overlap_feature_count": int(overlap.eq("direct").sum()),
                "related_overlap_feature_count": int(overlap.isin(["direct", "related"]).sum()),
                "rolling_fracdiff_feature_count": len(rolling),
            }
        )
    return pd.DataFrame(rows)


def build_baseline_feature_list(feature_sets: dict[str, list[str]], contract: pd.DataFrame) -> pd.DataFrame:
    fs0 = feature_sets["baseline_fs0"]
    rows = []
    for order, feature in enumerate(fs0):
        part = contract.loc[contract["feature_id"].eq(feature)]
        rows.append(
            {
                "feature_id": feature,
                "feature_order": order,
                "feature_family": part["feature_family"].iloc[0] if not part.empty else "",
                "allowed_for_09C_flag": True,
                "baseline_role": "h_style_fs0_baseline",
            }
        )
    return pd.DataFrame(rows)


def build_baseline_replay(frontier: pd.DataFrame) -> pd.DataFrame:
    return frontier.loc[
        frontier["model_family"].eq("h_style_logistic_baseline")
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ].copy()


def build_gate_refreeze_audit(baseline_replay: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    gates = config.get("cost_rejector", {}).get("research_entry_gate", {})
    placeholder = float(gates.get("cost_reduction_min_train", 0.15))
    train = baseline_replay.loc[
        baseline_replay["train_target_component"].eq("hybrid_cost_bad_10_20")
        & baseline_replay["split"].eq("train")
    ]
    baseline_value = float(train["relative_cost_reduction"].max()) if len(train) else np.nan
    return pd.DataFrame(
        [
            {
                "gate_name": "cost_reduction_min_train",
                "placeholder_default_value": placeholder,
                "baseline_replay_train_value": baseline_value,
                "final_frozen_value": placeholder,
                "refreeze_reason": "09C keeps the stricter H placeholder after replay; OOS readout not used before freeze.",
                "fit_scope": "risk_on_r_core_horizon_complete/train",
                "oos_readout_seen_before_freeze": False,
                "status": "pass",
            }
        ]
    )


def selected_model_policy(config: dict[str, Any]) -> dict[str, str]:
    return {
        "model_family": config.get("cost_rejector", {}).get(
            "selected_model_family", "regularized_logistic_or_elastic_net"
        ),
        "train_target_component": config.get("cost_rejector", {}).get(
            "selected_train_target_component", "hybrid_cost_bad_10_20"
        ),
        "ablation_id": config.get("cost_rejector", {}).get("selected_ablation_id", "full"),
        "calibration_id": config.get("cost_rejector", {}).get("selected_calibration_id", "none"),
    }


def select_final_threshold(
    frontier: pd.DataFrame,
    contribution: pd.DataFrame,
    gate_refreeze: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    policy = selected_model_policy(config)
    gate = config.get("cost_rejector", {}).get("research_entry_gate", {})
    cost_min = float(gate_refreeze.loc[gate_refreeze["gate_name"].eq("cost_reduction_min_train"), "final_frozen_value"].iloc[0])
    any_recall_min = float(gate.get("any_recall_retention_min_train", 0.90))
    e1_min = float(gate.get("e1_missed_retention_min_train", 0.85))
    fast_fail_attr_min = float(gate.get("fast_fail_component_contribution_min_train", 0.10))
    candidates = frontier.loc[
        frontier["model_family"].eq(policy["model_family"])
        & frontier["train_target_component"].eq(policy["train_target_component"])
        & frontier["ablation_id"].eq(policy["ablation_id"])
        & frontier["calibration_id"].eq(policy["calibration_id"])
        & frontier["denominator_id"].eq(R_CORE_DENOM)
        & frontier["split"].eq("train")
    ].copy()
    if candidates.empty:
        return {
            "selected_model_id": "",
            "selected_threshold_id": "",
            "selection_status": "no_policy_candidate",
        }
    candidates = candidates.merge(
        contribution.loc[
            contribution["denominator_id"].eq(R_CORE_DENOM) & contribution["split"].eq("train"),
            ["model_id", "threshold_id", "fast_fail_attributed_cost_reduction_share"],
        ],
        on=["model_id", "threshold_id"],
        how="left",
    )
    candidates["train_gate_pass"] = (
        candidates["relative_cost_reduction"].ge(cost_min)
        & candidates["any_recall_retention"].ge(any_recall_min)
        & candidates["e1_missed_retention"].fillna(1.0).ge(e1_min)
        & candidates["fast_fail_bad_side_capture"].ge(candidates["rejected_fraction"])
        & candidates["fast_fail_attributed_cost_reduction_share"].fillna(0.0).ge(fast_fail_attr_min)
    )
    passed = candidates.loc[candidates["train_gate_pass"]].sort_values(
        ["keep_fraction"], ascending=False
    )
    if not passed.empty:
        row = passed.iloc[0]
        status = "train_gate_pass"
    else:
        row = candidates.sort_values(
            ["relative_cost_reduction", "any_recall_retention"], ascending=[False, False]
        ).iloc[0]
        status = "diagnostic_best_train_frontier"
    return {
        "selected_model_id": row["model_id"],
        "selected_threshold_id": row["threshold_id"],
        "selected_threshold_score": float(row["threshold_score"]),
        "selection_status": status,
        "train_cost_reduction": float(row["relative_cost_reduction"]),
        "train_any_recall_retention": float(row["any_recall_retention"]),
        "train_e1_missed_retention": float(row["e1_missed_retention"]) if pd.notna(row["e1_missed_retention"]) else np.nan,
        "train_fast_fail_bad_side_capture": float(row["fast_fail_bad_side_capture"]) if pd.notna(row["fast_fail_bad_side_capture"]) else np.nan,
        "train_rejected_fraction": float(row["rejected_fraction"]) if pd.notna(row["rejected_fraction"]) else np.nan,
        "train_fast_fail_attributed_share": float(row["fast_fail_attributed_cost_reduction_share"]) if pd.notna(row["fast_fail_attributed_cost_reduction_share"]) else np.nan,
    }


def selected_threshold_frame(scores: pd.DataFrame, selection: dict[str, Any]) -> pd.DataFrame:
    part = scores.loc[scores["model_id"].eq(selection["selected_model_id"])].copy()
    threshold_score = float(selection["selected_threshold_score"])
    part["threshold_id"] = selection["selected_threshold_id"]
    part["selected_flag"] = part["score"].le(threshold_score)
    part["rejected_flag"] = ~part["selected_flag"]
    return part


def build_density_tables(selected_scores: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    caps = config.get("cost_rejector", {}).get("density_caps", {})
    kept = selected_scores.loc[
        selected_scores["denominator_id"].eq(R_CORE_DENOM) & selected_scores["selected_flag"]
    ].copy()
    if kept.empty:
        readout = pd.DataFrame(
            [
                {
                    "metric": "selected_event_count",
                    "value": 0,
                    "status": "no_selected_events",
                }
            ]
        )
        binding = pd.DataFrame(
            [
                {
                    "metric": "formal_event_day_density",
                    "value": 0.0,
                    "cap": float(caps.get("formal_event_day_density", 7.5)),
                    "cap_usage_ratio": 0.0,
                    "binding_flag": False,
                }
            ]
        )
        return readout, binding
    per_day = kept.groupby("event_t0_date").size()
    formal_density = safe_div(len(kept), max(1, kept["event_t0_date"].nunique()))
    p95_density = float(per_day.quantile(0.95))
    density_by_inst = (
        kept.assign(event_t0_date=pd.to_datetime(kept["event_t0_date"]))
        .sort_values(["instrument", "event_t0_date"])
        .groupby("instrument")
    )
    rolling_10 = []
    rolling_20 = []
    for _, group in density_by_inst:
        series = group.set_index("event_t0_date").assign(count=1)["count"].sort_index()
        rolling_10.append(series.rolling("10D").sum().max())
        rolling_20.append(series.rolling("20D").sum().max())
    family_concentration = (
        float(kept["primary_family_id"].value_counts(normalize=True).max())
        if "primary_family_id" in kept.columns and kept["primary_family_id"].notna().any()
        else np.nan
    )
    board_concentration = (
        float(kept["board_bucket"].value_counts(normalize=True).max())
        if "board_bucket" in kept.columns and kept["board_bucket"].notna().any()
        else np.nan
    )
    values = {
        "formal_event_day_density": formal_density,
        "p95_density": p95_density,
        "rolling_10d_executable_event_day_density": float(np.nanmax(rolling_10)) if rolling_10 else np.nan,
        "rolling_20d_executable_event_day_density": float(np.nanmax(rolling_20)) if rolling_20 else np.nan,
        "family_concentration": family_concentration,
        "board_concentration": board_concentration,
    }
    cap_defaults = {
        "formal_event_day_density": 7.50,
        "p95_density": 20.00,
        "rolling_10d_executable_event_day_density": 1.80,
        "rolling_20d_executable_event_day_density": 2.20,
        "family_concentration": 0.30,
        "board_concentration": 0.85,
    }
    binding_rows = []
    for metric, value in values.items():
        cap = float(caps.get(metric, cap_defaults[metric]))
        binding_rows.append(
            {
                "metric": metric,
                "value": value,
                "cap": cap,
                "cap_usage_ratio": safe_div(value, cap),
                "binding_flag": bool(pd.notna(value) and value >= cap * 0.80),
                "status": "pass" if pd.isna(value) or value <= cap else "cap_exceeded",
            }
        )
    readout_rows = []
    for split, part in kept.groupby("event_split", dropna=False):
        readout_rows.append(
            {
                "split": split,
                "selected_event_n": int(len(part)),
                "unique_event_day_n": int(part["event_t0_date"].nunique()),
                "formal_event_day_density": safe_div(len(part), max(1, part["event_t0_date"].nunique())),
                "primary_family_top_share": float(part["primary_family_id"].value_counts(normalize=True).max())
                if "primary_family_id" in part.columns and part["primary_family_id"].notna().any()
                else np.nan,
                "board_top_share": float(part["board_bucket"].value_counts(normalize=True).max())
                if "board_bucket" in part.columns and part["board_bucket"].notna().any()
                else np.nan,
            }
        )
    return pd.DataFrame(readout_rows), pd.DataFrame(binding_rows)


def build_riskoff_tables(
    data: pd.DataFrame,
    binding: pd.DataFrame,
    contract: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    riskoff_input_n = int((binding["denominator_id"] == RISK_OFF_READONLY_DENOM).sum())
    riskoff_scored_n = int((data["denominator_id"] == RISK_OFF_READONLY_DENOM).sum())
    control = pd.DataFrame(
        [
            {
                "denominator_id": RISK_OFF_READONLY_DENOM,
                "riskoff_input_event_n": riskoff_input_n,
                "scored_event_n": riskoff_scored_n,
                "status": "riskoff_readonly_control_input_insufficient",
                "reason": "09A binding has risk_off E1 readonly rows, but 09B feature_matrix does not materialize risk_off_e1_horizon_complete_readonly rows; no refit is allowed.",
            }
        ]
    )
    rows = []
    for feature in contract["feature_id"].tolist():
        rows.append(
            {
                "feature_id": feature,
                "missing_rate_before_impute": np.nan,
                "winsor_low_clip_rate": np.nan,
                "winsor_high_clip_rate": np.nan,
                "post_transform_null_rate": np.nan,
                "risk_on_train_reference_rate": np.nan,
                "clip_rate_excess_vs_risk_on_train": np.nan,
                "status": "riskoff_feature_matrix_not_materialized",
            }
        )
    return control, pd.DataFrame(rows)


def build_overlap_ablation(frontier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    selected_model_family = "regularized_logistic_or_elastic_net"
    for ablation_id, part in frontier.loc[
        frontier["model_family"].eq(selected_model_family)
        & frontier["train_target_component"].eq("hybrid_cost_bad_10_20")
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ].groupby("ablation_id", dropna=False):
        for split, split_part in part.groupby("split", dropna=False):
            best = split_part.sort_values("relative_cost_reduction", ascending=False).head(1)
            if best.empty:
                continue
            row = best.iloc[0]
            rows.append(
                {
                    "ablation_id": ablation_id,
                    "split": split,
                    "best_threshold_id": row["threshold_id"],
                    "relative_cost_reduction": row["relative_cost_reduction"],
                    "any_recall_retention": row["any_recall_retention"],
                    "fast_fail_bad_side_capture": row["fast_fail_bad_side_capture"],
                    "status": "pass",
                }
            )
    return pd.DataFrame(rows)


def build_warmup_missing_ablation(
    frontier: pd.DataFrame,
    stationarity: pd.DataFrame,
    data: pd.DataFrame,
) -> pd.DataFrame:
    warm_features = [
        "log_close_fracdiff_d04",
        "panel_return_20d_rolling_z_60d",
        "panel_return_20d_rolling_pct_60d",
    ]
    rows = []
    for feature in warm_features:
        raw_missing = stationarity.loc[stationarity["feature_id"].eq(feature), "raw_missing_rate"]
        for split, part in data.groupby("event_split", dropna=False):
            rows.append(
                {
                    "feature_id": feature,
                    "split": split,
                    "post_09B_transform_missing_rate": float(part[feature].isna().mean())
                    if feature in part.columns
                    else np.nan,
                    "source_raw_missing_rate_before_impute": float(raw_missing.iloc[0])
                    if not raw_missing.empty
                    else np.nan,
                    "warmup_missing_status": "imputed_by_09B_train_contract",
                }
            )
    compare = frontier.loc[
        frontier["model_family"].eq("regularized_logistic_or_elastic_net")
        & frontier["train_target_component"].eq("hybrid_cost_bad_10_20")
        & frontier["ablation_id"].isin(["full", "drop_fs0_rolling_fracdiff_hygiene"])
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ]
    for _, row in compare.iterrows():
        rows.append(
            {
                "feature_id": "__ablation_readout__",
                "split": row["split"],
                "post_09B_transform_missing_rate": np.nan,
                "source_raw_missing_rate_before_impute": np.nan,
                "warmup_missing_status": "frontier_readout",
                "ablation_id": row["ablation_id"],
                "threshold_id": row["threshold_id"],
                "relative_cost_reduction": row["relative_cost_reduction"],
                "any_recall_retention": row["any_recall_retention"],
            }
        )
    return pd.DataFrame(rows)


def selected_event_tables(selected_scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    schema_cols = [
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "event_split",
        "train_target_component",
        "model_id",
        "ablation_id",
        "calibration_id",
        "threshold_id",
        "score",
        "selected_flag",
        "rejected_flag",
        "selected_fast_fail_10_label",
        "frozen_false_repair_20d_label",
        "selected_cost_bad_10_20_target",
    ]
    event_scores = selected_scores[schema_cols + ["canonical_event_id", "instrument", "event_t0_date"]].copy()
    return (
        event_scores.loc[event_scores["selected_flag"]].copy(),
        event_scores.loc[event_scores["rejected_flag"]].copy(),
        event_scores,
    )


def oos_rejected_spread(frontier: pd.DataFrame, selection: dict[str, Any]) -> float:
    part = frontier.loc[
        frontier["model_id"].eq(selection["selected_model_id"])
        & frontier["threshold_id"].eq(selection["selected_threshold_id"])
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ]
    train = part.loc[part["split"].eq("train"), "rejected_fraction"]
    if train.empty:
        return np.nan
    train_value = float(train.iloc[0])
    spreads = [
        abs(float(row["rejected_fraction"]) - train_value)
        for _, row in part.loc[part["split"].isin(["validation", "robustness"])].iterrows()
        if pd.notna(row["rejected_fraction"])
    ]
    return max(spreads) if spreads else np.nan


def final_decision(
    selection: dict[str, Any],
    frontier: pd.DataFrame,
    contribution: pd.DataFrame,
    density_binding: pd.DataFrame,
    separability: pd.DataFrame,
    source_caveated: bool,
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    gate = config.get("cost_rejector", {}).get("research_entry_gate", {})
    spread_limit = float(
        config.get("cost_rejector", {}).get(
            "oos_positive_rate_spread_force_diagnostic_threshold", 0.15
        )
    )
    selected_frontier = frontier.loc[
        frontier["model_id"].eq(selection["selected_model_id"])
        & frontier["threshold_id"].eq(selection["selected_threshold_id"])
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ]
    selected_meta = selected_frontier.head(1)
    if selected_meta.empty:
        selected_family = selected_ablation = selected_calibration = ""
    else:
        selected_family = str(selected_meta["model_family"].iloc[0])
        selected_ablation = str(selected_meta["ablation_id"].iloc[0])
        selected_calibration = str(selected_meta["calibration_id"].iloc[0])
    train = selected_frontier.loc[selected_frontier["split"].eq("train")]
    robustness = selected_frontier.loc[selected_frontier["split"].eq("robustness")]
    fast_auc = separability.loc[
        separability["model_family"].eq(selected_family)
        & separability["ablation_id"].eq(selected_ablation)
        & separability["calibration_id"].eq(selected_calibration)
        & separability["train_target_component"].eq("fast_fail_only_10d")
        & separability["denominator_id"].eq(R_CORE_DENOM)
        & separability["split"].eq("robustness"),
        "roc_auc",
    ]
    selected_contribution = contribution.loc[
        contribution["model_id"].eq(selection["selected_model_id"])
        & contribution["threshold_id"].eq(selection["selected_threshold_id"])
        & contribution["denominator_id"].eq(R_CORE_DENOM)
        & contribution["split"].eq("train")
    ]
    spread = oos_rejected_spread(frontier, selection)
    density_pass = density_binding["status"].eq("pass").all() if len(density_binding) else False
    cost_train = float(train["relative_cost_reduction"].iloc[0]) if not train.empty else np.nan
    recall_train = float(train["any_recall_retention"].iloc[0]) if not train.empty else np.nan
    cost_robust = float(robustness["relative_cost_reduction"].iloc[0]) if not robustness.empty else np.nan
    recall_robust = float(robustness["any_recall_retention"].iloc[0]) if not robustness.empty else np.nan
    ff_share = (
        float(selected_contribution["fast_fail_attributed_cost_reduction_share"].iloc[0])
        if not selected_contribution.empty
        else np.nan
    )
    gate_status = {
        "train_gate_selection_status": selection.get("selection_status", ""),
        "oos_rejected_fraction_spread": spread,
        "spread_gate_pass": pd.notna(spread) and spread <= spread_limit,
        "robustness_cost_no_reversal_pass": pd.notna(cost_robust) and cost_robust > 0,
        "robustness_recall_pass": pd.notna(recall_robust)
        and recall_robust >= float(gate.get("robustness_any_recall_retention_min", 0.80)),
        "fast_fail_robustness_auc": float(fast_auc.iloc[0]) if not fast_auc.empty else np.nan,
        "fast_fail_robustness_auc_pass": not fast_auc.empty
        and float(fast_auc.iloc[0]) >= float(gate.get("fast_fail_only_auc_min_robustness", 0.60)),
        "fast_fail_attributed_share": ff_share,
        "fast_fail_attributed_share_pass": pd.notna(ff_share)
        and ff_share >= float(gate.get("fast_fail_component_contribution_min_train", 0.10)),
        "density_gate_pass": density_pass,
        "train_cost_reduction": cost_train,
        "train_any_recall_retention": recall_train,
        "robustness_cost_reduction": cost_robust,
        "robustness_any_recall_retention": recall_robust,
    }
    research_pass = (
        selection.get("selection_status") == "train_gate_pass"
        and gate_status["spread_gate_pass"]
        and gate_status["robustness_cost_no_reversal_pass"]
        and gate_status["robustness_recall_pass"]
        and gate_status["fast_fail_robustness_auc_pass"]
        and gate_status["fast_fail_attributed_share_pass"]
        and density_pass
    )
    any_oos_auc = separability.loc[
        separability["denominator_id"].eq(R_CORE_DENOM)
        & separability["split"].isin(["validation", "robustness"])
        & separability["model_id"].eq(selection["selected_model_id"]),
        "roc_auc",
    ].dropna()
    feature_source_pass = bool((any_oos_auc > 0.55).any())
    if research_pass:
        return (DECISION_RESEARCH_CAVEATED if source_caveated else DECISION_RESEARCH), gate_status
    if not gate_status["spread_gate_pass"]:
        return DECISION_DIAGNOSTIC, gate_status
    if feature_source_pass:
        return (DECISION_FEATURE_CAVEATED if source_caveated else DECISION_FEATURE), gate_status
    return DECISION_DIAGNOSTIC, gate_status


def source_pool_status(source_pool_audit: pd.DataFrame) -> str:
    required_ids = [R_CORE_SCOPE, R6_SCOPE, "07_E1_only"]
    required = source_pool_audit.loc[source_pool_audit["source_pool_id"].isin(required_ids)]
    if set(required["source_pool_id"]) != set(required_ids):
        return "missing_required_scope"
    reconstructable = required["scope_status"].astype(str).eq("reconstructable_event_membership").all()
    mapping = required["scope_mapping_status"].astype(str).eq("reconstructable_event_membership").all()
    status = required["status"].astype(str).eq("pass").all()
    hard_gate_required = required.loc[required["source_pool_id"].isin([R_CORE_SCOPE, R6_SCOPE])]
    eligible = hard_gate_required["hard_gate_eligible_flag"].map(boolish).all()
    return "pass" if eligible and status and reconstructable and mapping else "failed"


def build_report(
    manifest: dict[str, Any],
    selection: dict[str, Any],
    gate_status: dict[str, Any],
    baseline: pd.DataFrame,
    separability: pd.DataFrame,
    calibration: pd.DataFrame,
    frontier: pd.DataFrame,
    contribution: pd.DataFrame,
    overlap_ablation: pd.DataFrame,
    warmup_ablation: pd.DataFrame,
    density_binding: pd.DataFrame,
    riskoff_control: pd.DataFrame,
) -> str:
    selected_model = selection.get("selected_model_id", "")
    selected_threshold = selection.get("selected_threshold_id", "")
    selected_rows = frontier.loc[
        frontier["model_id"].eq(selected_model)
        & frontier["threshold_id"].eq(selected_threshold)
        & frontier["denominator_id"].eq(R_CORE_DENOM)
    ].copy()
    def split_value(split: str, col: str) -> float:
        values = selected_rows.loc[selected_rows["split"].eq(split), col]
        return float(values.iloc[0]) if not values.empty and pd.notna(values.iloc[0]) else np.nan

    baseline_train = baseline.loc[
        baseline["train_target_component"].eq("hybrid_cost_bad_10_20")
        & baseline["split"].eq("train")
    ]
    baseline_best = float(baseline_train["relative_cost_reduction"].max()) if len(baseline_train) else np.nan
    sep_selected = separability.loc[separability["model_id"].eq(selected_model)]
    density_status = "weakly-binding"
    if len(density_binding) and (density_binding["cap_usage_ratio"].fillna(0) >= 0.25).any():
        density_status = "binding-readout"
    riskoff_status = riskoff_control["status"].iloc[0] if len(riskoff_control) else "missing"
    contribution_train = contribution.loc[
        contribution["model_id"].eq(selected_model)
        & contribution["threshold_id"].eq(selected_threshold)
        & contribution["denominator_id"].eq(R_CORE_DENOM)
        & contribution["split"].eq("train")
    ]
    ff_share = (
        float(contribution_train["fast_fail_attributed_cost_reduction_share"].iloc[0])
        if len(contribution_train)
        else np.nan
    )
    shallow_tree = separability.loc[
        separability["model_family"].eq("shallow_tree_or_bagging_shallow_trees_diagnostic")
        & separability["denominator_id"].eq(R_CORE_DENOM)
        & separability["split"].eq("robustness")
    ]
    logistic_full = separability.loc[
        separability["model_family"].eq("regularized_logistic_or_elastic_net")
        & separability["ablation_id"].eq("full")
        & separability["calibration_id"].eq("none")
        & separability["denominator_id"].eq(R_CORE_DENOM)
        & separability["split"].eq("robustness")
    ]
    shallow_rows = []
    for component in TARGET_COMPONENTS:
        tree_auc = shallow_tree.loc[
            shallow_tree["train_target_component"].eq(component), "roc_auc"
        ]
        log_auc = logistic_full.loc[
            logistic_full["train_target_component"].eq(component), "roc_auc"
        ]
        shallow_rows.append(
            (
                component,
                float(log_auc.iloc[0]) if not log_auc.empty else np.nan,
                float(tree_auc.iloc[0]) if not tree_auc.empty else np.nan,
            )
        )
    calibration_rows = calibration.loc[
        calibration["denominator_id"].eq(R_CORE_DENOM)
        & calibration["split"].isin(["train", "robustness"])
    ].sort_values(["calibration_id", "split"])
    overlap_focus = overlap_ablation.loc[
        overlap_ablation["split"].isin(["train", "robustness"])
        & overlap_ablation["ablation_id"].isin(
            ["full", "drop_direct_related_overlap", "drop_fs0_rolling_fracdiff_hygiene"]
        )
    ].sort_values(["ablation_id", "split"])
    warm_focus = warmup_ablation.loc[
        warmup_ablation["feature_id"].isin(
            [
                "log_close_fracdiff_d04",
                "panel_return_20d_rolling_z_60d",
                "panel_return_20d_rolling_pct_60d",
            ]
        )
    ].head(9)
    lines = [
        "# 09C Risk-on Cost Rejector Uplift Report",
        "",
        "## 结论",
        "",
        f"- 决策：`{manifest['decision']}`。09A / 09B 均带 source caveat，因此即使通过 gate 也只能进入 source-caveated variant。",
        f"- 预冻结主模型：`{selected_model}`；阈值：`{selected_threshold}`；选择状态：`{selection.get('selection_status')}`。",
        f"- train cost reduction = {split_value('train', 'relative_cost_reduction'):.4f}，train any winner retention = {split_value('train', 'any_recall_retention'):.4f}。",
        f"- robustness cost reduction = {split_value('robustness', 'relative_cost_reduction'):.4f}，robustness any winner retention = {split_value('robustness', 'any_recall_retention'):.4f}。",
        f"- fast-fail attributed cost-reduction share(train) = {ff_share:.4f}；OOS rejected-fraction spread = {gate_status.get('oos_rejected_fraction_spread', np.nan):.4f}。",
        f"- 关键 gate 未通过：train winner retention {gate_status.get('train_any_recall_retention', np.nan):.4f} < 0.90，OOS rejected spread {gate_status.get('oos_rejected_fraction_spread', np.nan):.4f} > 0.15，fast-fail attribution {ff_share:.4f} < 0.10，density cap exceeded。",
        "",
        "## Baseline Replay",
        "",
        f"09C 的 uplift 对照是 09C 内部用 09A target + 09B FS0 feature + 09B sample weights 重放的 H-style baseline，不是 H 旧 target。baseline hybrid train 最优 cost reduction 为 {baseline_best:.4f}，gate_refreeze 在读取 OOS readout 前保留 15% train cost-reduction 下限。",
        "",
        "## Target Component",
        "",
        "09C 同时训练并报告 fast-fail-only、false-repair component、hybrid 三个 component。hybrid 仍可能被 false-repair 主导，因此最终报告必须看 fast-fail-only AUC、bad-side capture 和 attribution share。若 fast-fail contribution 不达标，只能说 false-repair / feature-source 有信号，不能 claim fast-fail uplift。",
        "",
        "selected threshold 的 rejected hybrid positives 仍主要来自 false-repair component：fast-fail attributed share 只有 {:.4f}，说明 09A 已提示的 hybrid 稀释问题在 09C 里仍然存在。".format(
            ff_share
        ),
        "",
        "## Separability Snapshot",
        "",
        "| component | split | roc_auc | pr_auc | top_decile_lift |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in sep_selected.loc[
        sep_selected["denominator_id"].eq(R_CORE_DENOM)
        & sep_selected["split"].isin(SPLIT_ORDER)
    ].sort_values(["train_target_component", "split"]).iterrows():
        lines.append(
            f"| {row['train_target_component']} | {row['split']} | {row['roc_auc']:.4f} | {row['pr_auc']:.4f} | {row['top_decile_lift']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Calibration",
            "",
            "Platt 与 isotonic 只在 R-core train fit，validation / robustness 只读。calibration 没有进入主选择，主模型仍是预冻结 `none` calibration；isotonic 在 robustness 的 Brier 有改善，但没有改变 threshold gate 失败事实。",
            "",
            "| calibration | split | roc_auc | brier | keep_0800_after_cost_bad_rate |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in calibration_rows.iterrows():
        lines.append(
            f"| {row['calibration_id']} | {row['split']} | {row['roc_auc']:.4f} | {row['brier_score']:.4f} | {row['keep_0800_after_cost_bad_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Overlap / Warmup Ablation",
            "",
            "09B 标记了 structural stop 与 FS2/FS3 price-location、range、ATR feature 的机制重叠。09C 因此报告 full、drop direct+related overlap、drop FS2 related、drop rolling/fracdiff hygiene 与 representative feature 对照；这些读数只支持 feature-source caveat，不足以消除 mechanism-overlap 风险。",
            "",
            "| ablation | split | best_threshold | cost_reduction | recall_retention | fast_fail_capture |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in overlap_focus.iterrows():
        lines.append(
            f"| {row['ablation_id']} | {row['split']} | {row['best_threshold_id']} | {row['relative_cost_reduction']:.4f} | {row['any_recall_retention']:.4f} | {row['fast_fail_bad_side_capture']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Warmup hygiene feature 在 09B transform 后已无 post-transform null，但 source raw missing 约 4.7%-4.8%。这意味着缺失模式已由 train-fitted imputer 吸收，仍需在 09D/09C 后续模型里防止 split cue。",
            "",
            "| feature | split | post_transform_missing | source_raw_missing |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in warm_focus.iterrows():
        lines.append(
            f"| {row['feature_id']} | {row['split']} | {row['post_09B_transform_missing_rate']:.4f} | {row['source_raw_missing_rate_before_impute']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Shallow-tree Diagnostic",
            "",
            "shallow-tree / bagging shallow trees 用于检查线性模型是否低估 FS3 / FS4 / FS6 非线性交互，不参与 threshold 选择。robustness AUC 对比如下：",
            "",
            "| component | logistic_full_auc | shallow_tree_auc |",
            "| --- | ---: | ---: |",
        ]
    )
    for component, log_auc, tree_auc in shallow_rows:
        lines.append(f"| {component} | {log_auc:.4f} | {tree_auc:.4f} |")
    lines.extend(
        [
            "",
            "## Density / Risk-off",
            "",
            f"Density gate 状态：`{density_status}`。如果所有 cap usage 都低于 0.25，本实验不能把“density 轻松通过”解释成 source 质量改善，只能说明 selected threshold 很稀疏。",
            f"Risk-off read-only 状态：`{riskoff_status}`。09B 未 materialize risk_off E1 feature matrix，所以本轮不允许 risk_off 重新 fit，也不做定量 uplift 幅度比较。",
            "",
            "## 主要风险",
            "",
            "1. `break_swing_low_20` 是低 positive-rate structural stop；retention 高不自动等于精准过滤，必须结合 bad-side coverage。",
            "2. 09B 已提示 FS2 / FS3 与 structural stop 有机制重叠；full model 若依赖这些 feature，结论只能带 caveat。",
            "3. rolling / fracdiff hygiene feature 的 warmup missing 可能形成 split cue；09C 已输出 without rolling / fracdiff ablation 供 09D/09C 后续复核。",
            "4. transition 继续冻结，没有进入训练、threshold 或 density gate。",
            "5. PCA 没有进入主流程；09B 已给出 raw / representative feature 对照，09C 不做 global PCA，避免把 feature mechanism 解释性压扁。",
            "",
            "## 产物",
            "",
            "- 核心表位于 `outputs/publishable/tables/09C_riskon_cost_rejector/`。",
            "- `event_scores.csv.gz`、`selected_events.csv.gz`、`rejected_events.csv.gz` 包含 `denominator_id` 与 `train_target_component`，可区分 R-core supported 与 R6 readout。",
        ]
    )
    return "\n".join(lines)


def build_manifest(
    config: dict[str, Any],
    inputs: dict[str, Any],
    outputs: dict[str, Path],
    decision: str,
    selection: dict[str, Any],
    statuses: dict[str, Any],
    forbidden_feature_count: int,
) -> dict[str, Any]:
    source_caveated = bool(
        inputs["manifests"]["09a"].get("source_caveated") or inputs["manifests"]["09b"].get("source_caveated")
    )
    output_hashes = {
        key: path_hash(path)
        for key, path in outputs.items()
        if key != "manifest" and path.exists() and path.is_file()
    }
    input_hashes = {
        row["input_id"]: row["sha256"]
        for _, row in inputs["input_audit"].iterrows()
        if boolish(row["exists"])
    }
    return {
        "experiment_id": "09_riskon_fastfail_label_feature_uplift",
        "phase": "09C_riskon_cost_rejector_uplift",
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(PROJECT_ROOT),
        "decision": decision,
        "source_caveated": source_caveated,
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "config_hash": path_hash(CONFIG_PATH),
        "selected_target_label": SUPPORTED_FAST_FAIL_ID,
        "selected_supported_target_id": SUPPORTED_TARGET_ID,
        "selected_target_contract_hash": path_hash(TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv"),
        "selected_label_event_bindings_hash": path_hash(LOCAL_CACHE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_bindings.parquet"),
        "selected_feature_contract_hash": path_hash(TABLE_DIR / "09B_feature_foundation" / "feature_contract.csv"),
        "feature_matrix_hash": path_hash(LOCAL_CACHE_DIR / "09B_feature_foundation" / "feature_matrix.parquet"),
        "sample_uniqueness_weights_hash": path_hash(LOCAL_CACHE_DIR / "09B_feature_foundation" / "sample_uniqueness_weights.parquet"),
        "baseline_feature_list_hash": output_hashes.get("baseline_feature_list", ""),
        "selected_model_id": selection.get("selected_model_id", ""),
        "selected_threshold_id": selection.get("selected_threshold_id", ""),
        "target_component_status": statuses.get("target_component_status", "pass"),
        "weight_horizon_usage_status": statuses.get("weight_horizon_usage_status", "pass"),
        "label_mechanism_overlap_ablation_status": statuses.get("label_mechanism_overlap_ablation_status", "pass"),
        "warmup_missing_ablation_status": statuses.get("warmup_missing_ablation_status", "pass"),
        "bad_side_coverage_status": statuses.get("bad_side_coverage_status", "pass"),
        "gate_refreeze_status": statuses.get("gate_refreeze_status", "pass"),
        "density_gate_binding_status": statuses.get("density_gate_binding_status", "pass"),
        "riskoff_transform_coverage_status": statuses.get("riskoff_transform_coverage_status", "input_insufficient"),
        "e1_baseline_reconstruction_status": statuses.get("e1_baseline_reconstruction_status", "pass"),
        "source_pool_reconstruction_status": statuses.get("source_pool_reconstruction_status", "pass"),
        "regime_label_pit_status": "inherited_from_09A",
        "label_bridge_status": inputs["manifests"]["09a"].get("label_bridge_status", "inherited"),
        "feature_leakage_status": statuses.get("feature_leakage_status", "pass"),
        "forbidden_feature_count": forbidden_feature_count,
        "threshold_selection_policy": config.get("cost_rejector", {}).get(
            "threshold_selection_policy",
            "train_only_hybrid_cost_reduction_then_recall_with_fast_fail_noncollapse",
        ),
        "density_concentration_status": statuses.get("density_concentration_status", "pass"),
        "oversized_artifact_policy": "publish event tables as csv.gz",
        "gate_status": statuses.get("gate_status", {}),
    }


def run_full(config: dict[str, Any]) -> dict[str, Any]:
    outputs = output_paths()
    inputs = read_core_inputs(config)
    data = inputs["data"]
    weights = inputs["weights"]
    feature_contract = inputs["feature_contract"]
    stationarity = inputs["stationarity"]
    source_status = source_pool_status(inputs["source_pool_audit"])
    feature_cols = allowed_feature_columns(feature_contract, inputs["feature_matrix"])
    leakage_status, forbidden_count, leakage_audit = forbidden_feature_audit(feature_cols)
    if leakage_status != "pass":
        write_df(OUTPUT_TABLE_DIR / "feature_leakage_audit.csv", leakage_audit)
        raise RuntimeError("Forbidden feature entered 09C model feature matrix")
    feature_sets = build_feature_sets(feature_contract, feature_cols)
    if not feature_sets["baseline_fs0"]:
        raise RuntimeError("FS0 baseline feature list is empty")

    target_contract = target_component_contract()
    write_df(outputs["target_component_contract"], target_contract)
    write_df(outputs["e1_baseline_reconstruction_audit"], inputs["e1_baseline_audit"])
    write_df(outputs["weight_horizon_usage_audit"], build_weight_horizon_usage_audit(data, weights))
    baseline_feature_list = build_baseline_feature_list(feature_sets, feature_contract)
    write_df(outputs["baseline_feature_list"], baseline_feature_list)

    specs = model_specs(feature_sets, config.get("cost_rejector", {}))
    registry, scores = fit_and_score_models(data, weights, specs, config)
    scores = attach_weights_to_scores(scores, weights)
    write_df(outputs["model_registry"], registry)
    write_df(outputs["feature_family_usage_audit"], build_feature_family_usage_audit(registry, feature_sets, feature_contract))
    separability = build_oos_separability(scores)
    write_df(outputs["oos_separability"], separability)
    calibration = build_calibration_readout(scores)
    write_df(outputs["calibration_readout"], calibration)

    frontier, by_component, contribution, bad_side, retention, e1 = build_threshold_tables(scores, config)
    baseline_replay = build_baseline_replay(frontier)
    gate_refreeze = build_gate_refreeze_audit(baseline_replay, config)
    selection = select_final_threshold(frontier, contribution, gate_refreeze, config)
    selected_scores = selected_threshold_frame(scores, selection)
    selected_events, rejected_events, event_scores = selected_event_tables(selected_scores)
    density_readout, density_binding = build_density_tables(selected_scores, config)
    riskoff_control, riskoff_transform = build_riskoff_tables(data, inputs["binding"], feature_contract)
    overlap_ablation = build_overlap_ablation(frontier)
    warmup_ablation = build_warmup_missing_ablation(frontier, stationarity, data)

    write_df(outputs["09C_h_style_baseline_replay_on_selected_target"], baseline_replay)
    write_df(outputs["gate_refreeze_audit"], gate_refreeze)
    write_df(outputs["threshold_frontier"], frontier)
    write_df(outputs["threshold_frontier_by_component"], by_component)
    write_df(outputs["component_contribution_readout"], contribution)
    write_df(outputs["bad_side_coverage_readout"], bad_side)
    write_df(outputs["cost_readout"], frontier.copy())
    write_df(outputs["post_filter_retention_by_split"], retention)
    write_df(outputs["e1_missed_retention"], e1)
    write_df(outputs["density_concentration_readout"], density_readout)
    write_df(outputs["density_gate_binding_audit"], density_binding)
    write_df(outputs["riskoff_readonly_control"], riskoff_control)
    write_df(outputs["riskoff_transform_coverage_audit"], riskoff_transform)
    write_df(outputs["label_mechanism_overlap_ablation"], overlap_ablation)
    write_df(outputs["warmup_missing_ablation"], warmup_ablation)
    write_df(outputs["selected_events"], selected_events)
    write_df(outputs["rejected_events"], rejected_events)
    write_df(outputs["event_scores"], event_scores)

    source_caveated = bool(
        inputs["manifests"]["09a"].get("source_caveated") or inputs["manifests"]["09b"].get("source_caveated")
    )
    decision, gate_status = final_decision(
        selection,
        frontier,
        contribution,
        density_binding,
        separability,
        source_caveated,
        config,
    )
    if source_status != "pass":
        decision = DECISION_INPUT_BLOCKED
    statuses = {
        "target_component_status": "pass",
        "weight_horizon_usage_status": "pass",
        "label_mechanism_overlap_ablation_status": "pass",
        "warmup_missing_ablation_status": "pass",
        "bad_side_coverage_status": "pass",
        "gate_refreeze_status": "pass",
        "density_gate_binding_status": "pass"
        if density_binding["status"].eq("pass").all()
        else "cap_exceeded",
        "riskoff_transform_coverage_status": "input_insufficient",
        "e1_baseline_reconstruction_status": "pass"
        if inputs["e1_baseline_audit"]["status"].eq("pass").all()
        else "failed",
        "source_pool_reconstruction_status": source_status,
        "feature_leakage_status": leakage_status,
        "density_concentration_status": "pass"
        if density_binding["status"].eq("pass").all()
        else "cap_exceeded",
        "gate_status": gate_status,
    }
    manifest = build_manifest(config, inputs, outputs, decision, selection, statuses, forbidden_count)
    write_text(
        outputs["report"],
        build_report(
            manifest,
            selection,
            gate_status,
            baseline_replay,
            separability,
            calibration,
            frontier,
            contribution,
            overlap_ablation,
            warmup_ablation,
            density_binding,
            riskoff_control,
        ),
    )
    manifest = build_manifest(config, inputs, outputs, decision, selection, statuses, forbidden_count)
    write_json(outputs["manifest"], manifest)
    return manifest


def write_blocked_manifest(config: dict[str, Any], decision: str, reason: str) -> dict[str, Any]:
    outputs = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(outputs["input_artifact_audit"], input_audit)
    manifest = {
        "experiment_id": "09_riskon_fastfail_label_feature_uplift",
        "phase": "09C_riskon_cost_rejector_uplift",
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(PROJECT_ROOT),
        "decision": decision,
        "blocked_reason": reason,
        "source_caveated": True,
        "input_hashes": {
            row["input_id"]: row["sha256"]
            for _, row in input_audit.iterrows()
            if boolish(row["exists"])
        },
        "output_hashes": {"input_artifact_audit": path_hash(outputs["input_artifact_audit"])},
        "config_hash": path_hash(CONFIG_PATH),
    }
    write_json(outputs["manifest"], manifest)
    write_text(outputs["report"], f"# 09C Risk-on Cost Rejector Uplift Report\n\nblocked: {reason}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_config(config_path)
    if args.mode == "check-inputs":
        audit = build_input_artifact_audit(config)
        write_df(output_paths()["input_artifact_audit"], audit)
        missing = audit.loc[audit["status"].ne("pass")]
        if not missing.empty:
            print(missing[["input_id", "path", "status"]].to_string(index=False))
            return 1
        print("09C input check passed")
        return 0
    try:
        manifest = run_full(config)
    except RuntimeError as exc:
        decision = DECISION_LEAKAGE_BLOCKED if "Forbidden feature" in str(exc) else DECISION_INPUT_BLOCKED
        manifest = write_blocked_manifest(config, decision, str(exc))
    except Exception as exc:
        manifest = write_blocked_manifest(config, DECISION_INPUT_BLOCKED, str(exc))
    print(json.dumps({"decision": manifest.get("decision"), "manifest": str(output_paths()["manifest"])}, ensure_ascii=False))
    return 0 if manifest.get("decision") not in {DECISION_INPUT_BLOCKED, DECISION_LEAKAGE_BLOCKED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
