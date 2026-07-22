"""Execute the 21F REAKA semantic-repair and stability diagnostic.

The module deliberately keeps orchestration, model semantics, metric semantics, and
artifact closure in one pinned source file.  A formal run is impossible until the
human-owned authorization file binds the exact requirement/config/runner/test,
upstream files, runtime fingerprint, artifact profile, and schema registry hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from scipy.stats import spearmanr
from torch import Tensor


WORKSPACE = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = EXPERIMENT_ROOT / "configs/config_21f_reaka_semantic_repair_and_stability_validation.yaml"
RUN_ID = "21F_reaka_semantic_repair_and_stability_validation"
REQUIREMENT_VERSION = "21F_SEMANTIC_REPAIR_v4"
PROFILE_ID = "P1_FULL_SEMANTIC_REPAIR_DIAGNOSTIC"
MODEL_SEEDS = (20260713, 20260714, 20260715)
LOOKBACK = 10
FEATURE_DIM = 157
LATENT_DIM = 64
N_OPERATOR = 4
DIFFUSION_STEPS = 20
EPOCH_SELECTOR_ID = "Q8_EPOCH_SCORE_MEAN8_CRN"

ARM_IDS = (
    "T0_RAW_COUPLED_LINEAR",
    "T1_CSZ_COUPLED_LINEAR",
    "T2_CSZ_STOPGRAD_LINEAR",
    "T3_CSZ_TWO_STAGE_LINEAR",
    "T4_CSZ_STOPGRAD_POINTWISE_MLP",
)
ESTIMATOR_IDS = (
    "Q0_CURRENT_SCORE_MEAN8",
    "Q1_SCORE_MEAN64",
    "Q2_SCORE_MEAN256_REF",
    "Q3_ANTITHETIC_SCORE_MEAN64",
    "Q4_DDIM_ETA0_SCORE",
    "Q5_ZERO_NOISE_REVERSE_PROXY",
    "Q6_KOOPMAN_ONLY",
    "Q7_LATENT_MEAN256_THEN_DECODE",
)
GATE_IDS = (
    "execution_authorization_gate", "paper_and_upstream_hash_gate",
    "upstream_terminal_state_gate", "artifact_profile_contract_gate",
    "retained_universe_exact_match_gate", "inner_fold_purge_and_metadata_split_gate",
    "hypothesis_registry_gate", "historical_holdout_zero_access_gate",
    "21c_q0_exact_replay_gate", "21d_d4_prefix64_exact_replay_gate",
    "21e_contrast_and_gradient_replay_gate", "return_transform_fixture_gate",
    "common_random_number_prefix_gate", "gradient_graph_fixture_gate",
    "training_arm_exact_gate", "planned_30_inner_jobs_gate",
    "train_only_gradient_calibration_gate", "inner_epoch_selection_gate",
    "checkpoint_semantic_hash_gate", "training_collapse_audit_gate",
    "predictor_convergence_gate", "predictor_selection_first_match_gate",
    "arm_stability_eligibility_gate", "arm_selection_first_match_gate",
    "shadow_selection_noncontrolling_gate", "planned_3_refit_jobs_gate",
    "pre_2023_complete_gate", "fresh_2023_worker_gate",
    "prediction_coverage_gate", "daily_rankic_metric_gate",
    "paired_contrast_gate", "drc_incremental_value_gate",
    "full_stability_candidate_gate", "portfolio_output_absence_gate",
    "historical_holdout_zero_access_finalize_gate", "terminal_state_first_match_gate",
    "report_decision_consistency_gate", "closed_schema_gate",
    "artifact_profile_gate", "manifest_hash_closure_gate",
    "post_run_validation_gate", "finalize_transaction_gate",
)
STAGE_IDS = (
    "E0_PREAUTH_AND_PREFLIGHT", "E1_EXACT_REPLAY_AND_FIXTURES",
    "E2_INNER_TRAINING", "E3_ESTIMATOR_ARM_SELECTION_AND_REFIT",
    "E4_FRESH_2023_READOUT", "E5_FINALIZE_AND_SEAL",
)
AUTH_KEYS = {
    "run_id", "requirement_version", "approved_requirement_sha256",
    "approved_config_sha256", "approved_runner_sha256", "approved_test_sha256",
    "approved_paper_pdf_sha256", "approved_upstream_21b_manifest_sha256",
    "approved_upstream_21b_output_hashes_sha256", "approved_upstream_21c_manifest_sha256",
    "approved_upstream_21c_output_hashes_sha256", "approved_upstream_21d_manifest_sha256",
    "approved_upstream_21d_output_hashes_sha256", "approved_upstream_21e_manifest_sha256",
    "approved_upstream_21e_output_hashes_sha256", "approved_dependency_lock_sha256",
    "approved_device_fingerprint_sha256", "approved_artifact_profile_id",
    "approved_artifact_profile_registry_contract_sha256",
    "approved_schema_registry_contract_sha256", "allowed_runtime_field_differences",
    "approved_by", "approved_at_utc",
}
FORBIDDEN_TOKENS = (
    "portfolio", "sharpe", "annualized_return", "turnover_cost", "execution_ledger",
    "historical_holdout_predictions", "best_seed", "post_2023_added_arm",
    "paper_exact_replication", "failure/failure_record.json",
)


class ContractError(RuntimeError):
    """Raised when an immutable 21F contract is violated."""


class AuthorizationResult(NamedTuple):
    status: str
    errors: tuple[str, ...]
    payload: dict[str, Any] | None
    sha256: str | None


class FoldSlice(NamedTuple):
    split_id: str
    frame: pd.DataFrame
    raw_panel: np.ndarray
    x_source: Any
    x_teacher: Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_path(relative: str | Path, *, must_exist: bool = False) -> Path:
    path = Path(relative)
    resolved = path if path.is_absolute() else WORKSPACE / path
    resolved = resolved.resolve()
    if not resolved.is_relative_to(WORKSPACE.resolve()):
        raise ContractError(f"path escapes workspace: {relative}")
    if must_exist and not resolved.exists():
        raise ContractError(f"missing required path: {relative}")
    return resolved


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_bytes(path, canonical_json_bytes(dict(payload)) + b"\n")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    frame = pd.DataFrame(list(rows), columns=list(columns))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("config must be a mapping")
    validate_frozen_config(payload)
    return payload


def validate_frozen_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "21F_SEMANTIC_REPAIR_CONFIG_V1":
        raise ContractError("config schema drift")
    if config["identity"]["run_id"] != RUN_ID or config["identity"]["requirement_version"] != REQUIREMENT_VERSION:
        raise ContractError("identity drift")
    if tuple(item["arm_id"] for item in config["training_arms"]) != ARM_IDS:
        raise ContractError("training arm order drift")
    if tuple(item["estimator_id"] for item in config["predictor_estimators"]) != ESTIMATOR_IDS:
        raise ContractError("predictor estimator order drift")
    if tuple(config["training"]["model_seeds"]) != MODEL_SEEDS:
        raise ContractError("model seed drift")
    if tuple(config["gates"]) != GATE_IDS:
        raise ContractError("gate order drift")
    if config["execution"]["planned_training_job_n"] != 33:
        raise ContractError("planned training cardinality drift")
    if config["resources"]["maximum_concurrent_gpu_training_jobs"] != 2:
        raise ContractError("v4 requires exactly two concurrent GPU training jobs")
    if (config["execution"]["inner_training_lane_n"] != 2 or
            config["execution"]["inner_training_partition"] != "inner_fold_order" or
            config["execution"]["lane_job_counts"] != [15, 15] or
            config["execution"]["lane_phase_row_counts"] != [18, 18]):
        raise ContractError("inner training lane contract drift")
    hours = (24 * 3 + 6 * 6 + 3 * 8 + 12)
    if hours != 144 or config["resources"]["total_gpu_wall_seconds_cap"] != hours * 3600:
        raise ContractError("resource upper bound drift")
    if config["training"]["epoch_selection_estimator"] != EPOCH_SELECTOR_ID:
        raise ContractError("joint/phase-B epoch selector drift")
    if config["training"]["phase_a_epoch_selection_estimator"] != "Q6_KOOPMAN_ONLY":
        raise ContractError("phase-A epoch selector drift")
    if config["execution"]["convergence_prefix_cache"] is not True:
        raise ContractError("convergence prefix cache must remain enabled")
    if config["execution"]["portfolio_output_authorized"] is not False:
        raise ContractError("portfolio output must remain forbidden")
    if list(config["artifact_profile"]["inner_checkpoint_paths"]) != inner_checkpoint_paths():
        raise ContractError("config inner checkpoint expansion drift")
    if list(config["artifact_profile"]["refit_checkpoint_paths"]) != refit_checkpoint_paths():
        raise ContractError("config refit checkpoint expansion drift")


def import_pinned(path: str | Path, module_name: str) -> Any:
    resolved = workspace_path(path, must_exist=True)
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot import pinned module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PINNED_21C = import_pinned(
    "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21c_full_reaka_pit_proxy_replication.py",
    "run_21c_pinned_for_21f",
)
PINNED_21D = import_pinned(
    "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21d_reaka_replication_gap_causal_diagnostic.py",
    "run_21d_pinned_for_21f",
)
PINNED_21E = import_pinned(
    "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21e_reaka_predictor_drc_implementation_identification.py",
    "run_21e_pinned_for_21f",
)


def building_output_root(config: Mapping[str, Any]) -> Path:
    runtime_root = config.get("_runtime_build_root")
    if runtime_root is not None:
        resolved = workspace_path(str(runtime_root))
        canonical_build = Path(str(workspace_path(config["paths"]["canonical_output_root"])) + ".building")
        if not resolved.is_relative_to(canonical_build):
            raise ContractError("runtime worker root escapes canonical building root")
        return resolved
    return Path(str(workspace_path(config["paths"]["canonical_output_root"])) + ".building")


def current_device_fingerprint() -> str:
    payload = {
        "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "device_total_memory": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None,
    }
    return stable_hash(payload)


def inner_checkpoint_paths() -> list[str]:
    fold_ids = ("I0_FIT_2018_2020_PURGED", "I1_FIT_2018_2021_PURGED")
    return [
        f"training/inner_checkpoints/{fold}/{arm}/seed_{seed}/state_dict.pt"
        for fold in fold_ids for arm in ARM_IDS for seed in MODEL_SEEDS
    ]


def refit_checkpoint_paths() -> list[str]:
    return [f"training/refit_checkpoints/seed_{seed}/state_dict.pt" for seed in MODEL_SEEDS]


REQUIRED_ARTIFACTS = (
    "21F_reaka_semantic_repair_and_stability_validation_decision.csv",
    "21F_reaka_semantic_repair_and_stability_validation_report.md",
    "preflight/pre_2023_row_index.parquet", "preflight/design_2023_row_index.parquet",
    "preflight/metadata_splitter_exit_record.json", "preflight/value_access_audit.csv",
    "preflight/pre_2023_complete.json", "exact_replay_audit.csv",
    "hypothesis_registry.csv", "training_semantics_arm_registry.csv",
    "predictor_estimator_registry.csv", "contrast_registry.csv", "inner_fold_registry.csv",
    "return_transform_audit.parquet", "gradient_calibration_audit.parquet",
    "gradient_graph_and_collapse_audit.parquet", "training/inner_training_run_registry.csv",
    "training/parallel_resource_probe.json",
    "training/inner_checkpoint_manifest.json", "training/selected_predictor_estimator.json",
    "training/selected_training_arm.json", "training/mean_rankic_only_shadow_selection.json",
    "training/refit_epoch_contract.json", "training/refit_training_run_registry.csv",
    "training/refit_checkpoint_manifest.json", "predictions/inner_selection_prediction_scores.parquet",
    "predictions/design_2023_prediction_scores.parquet", "predictor_draw_convergence.csv",
    "daily_rankic_readout.csv", "paired_semantic_contrasts.csv", "cross_seed_morphology.csv",
    "top30_overlap_and_turnover.csv", "monthly_quarter_lomo_stability.csv",
    "selection_policy_difference_audit.csv", "hypothesis_readout.csv", "gate_evidence_21f.csv",
    "historical_design_holdout_access_audit.csv", "artifact_profile_registry.csv",
    "schema_registry_21f.json", "stage_status_registry.csv",
    "semantic_reproducibility_manifest.json",
    "manifest_21f_reaka_semantic_repair_and_stability_validation.json",
    "output_hashes_21f_reaka_semantic_repair_and_stability_validation.json",
)


def artifact_profile_contract() -> dict[str, Any]:
    exact_checkpoints = inner_checkpoint_paths() + refit_checkpoint_paths()
    return {
        "profile_id": PROFILE_ID,
        "required_paths": sorted((*REQUIRED_ARTIFACTS, *exact_checkpoints)),
        "forbidden_tokens": list(FORBIDDEN_TOKENS),
        "exact_checkpoint_paths": exact_checkpoints,
        "terminal_states": [
            "21F_predictor_semantics_unresolved", "21F_no_stable_training_repair",
            "21F_no_rank_repair", "21F_repaired_rank_without_drc_increment",
            "21F_mean_rank_repair_unstable",
            "21F_design_contaminated_semantic_repair_candidate",
        ],
    }


TABULAR_SCHEMAS = {
    "decision": ["schema_version", "run_id", "terminal_state", "evidence_role",
        "research_estimator_selected", "selected_estimator_id", "research_arm_selected",
        "selected_arm_id", "rank_repair_floor_pass", "drc_incremental_value_pass",
        "full_stability_candidate_pass", "paper_exact_claim_allowed",
        "author_implementation_claim_allowed", "forward_support_claim_allowed",
        "next_requirement_execution_authorized", "reason_code"],
    "prediction": ["stage_id", "fold_id", "arm_id", "estimator_id", "score_variant",
        "model_seed", "is_ensemble", "decision_date", "instrument", "row_key_hash",
        "score", "label"],
    "daily_rankic": ["stage_id", "fold_id", "arm_id", "estimator_id", "score_variant",
        "model_seed", "is_ensemble", "decision_date", "cross_section_n", "rankic",
        "status", "reason_code"],
    "row_index": ["fold_id", "decision_date", "instrument", "fold_panel_row_idx",
        "x_cache_row_indices", "source_dates", "row_key_hash"],
    "value_access": ["event_order", "worker_role", "process_id", "stage_id", "path",
        "access_mode", "metadata_only", "value_parsed", "label_value_materialized_n",
        "score_value_materialized_n", "event_time_utc", "status", "reason_code"],
    "exact_replay": ["replay_order", "replay_id", "source_path", "source_sha256",
        "comparison_role", "expected_semantic_sha256", "observed_semantic_sha256",
        "max_abs_error", "bitwise_equal", "status", "reason_code"],
    "hypothesis_registry": ["hypothesis_order", "hypothesis_id", "statement",
        "intervention_id", "materiality_rule_id", "falsifier", "allowed_conclusion", "status"],
    "training_arm_registry": ["arm_order", "arm_id", "return_transform",
        "loss_weight_contract", "gradient_graph", "phase_contract", "decoder_id",
        "candidate_role", "status"],
    "predictor_registry": ["estimator_order", "estimator_id", "definition_id", "draw_n",
        "reference_draw_n", "candidate_eligible", "selection_reference_arm_id",
        "claim_restriction", "status"],
    "contrast_registry": ["contrast_order", "contrast_id", "left_id", "right_id",
        "family_id", "metric_id", "materiality_rule_id", "claim_restriction", "status"],
    "inner_fold_registry": ["fold_order", "split_id", "role", "date_min", "date_max",
        "max_label_source_date", "row_n", "complete_day_n", "instrument_n",
        "row_key_sha256", "status"],
    "return_transform": ["split_id", "decision_date", "position", "row_n", "raw_mean",
        "raw_std_ddof0", "sigma_floor_applied", "transformed_mean", "transformed_std_ddof0",
        "raw_row_key_sha256", "transformed_value_sha256", "status", "reason_code"],
    "gradient_calibration": ["record_type", "fold_id", "model_seed", "temporal_stratum",
        "batch_index", "loss_term", "row_n", "decision_date_min", "decision_date_max",
        "row_key_sha256", "gradient_median_l2", "loss_weight",
        "ordered_parameter_names_sha256", "status", "reason_code"],
    "gradient_collapse": ["fold_id", "arm_id", "model_seed", "phase_id", "epoch",
        "module_id", "loss_term", "gradient_l2", "gradient_share", "zero_solution_improvement",
        "latent_std", "decoder_output_std", "additional_collapse_flag",
        "checkpoint_semantic_sha256", "status", "reason_code"],
    "inner_training_registry": ["job_order", "fold_id", "arm_id", "model_seed", "phase_id",
        "fit_row_n", "planned_max_epochs", "executed_epoch_n", "selected_epoch",
        "selector_estimator_id", "phase_selected_semantic_sha256", "checkpoint_path",
        "checkpoint_sha256", "checkpoint_semantic_sha256", "job_status", "reason_code"],
    "refit_training_registry": ["job_order", "arm_id", "model_seed", "phase_id", "fit_row_n",
        "fixed_epoch_n", "phase_selected_semantic_sha256", "checkpoint_path", "checkpoint_sha256",
        "checkpoint_semantic_sha256", "job_status", "reason_code"],
    "draw_convergence": ["fold_id", "arm_id", "estimator_id", "model_seed", "comparison_id",
        "paired_day_n", "median_daily_spearman", "median_daily_top30_overlap",
        "mean_daily_rankic_left", "mean_daily_rankic_reference", "rankic_abs_delta",
        "repeated_run_bitwise_equal", "cross_batch_max_abs_error", "coverage_pass",
        "convergence_pass", "reason_code"],
    "paired_contrasts": ["family_id", "fold_id", "contrast_id", "left_id", "right_id",
        "paired_day_n", "mean_daily_rankic_left", "mean_daily_rankic_right",
        "mean_daily_rankic_delta", "same_direction_seed_n", "p_unadjusted", "p_holm",
        "materiality_pass", "status", "reason_code"],
    "cross_seed_morphology": ["stage_id", "fold_id", "arm_id", "estimator_id", "seed_a",
        "seed_b", "paired_day_n", "mean_daily_score_spearman",
        "mean_daily_top30_overlap", "status", "reason_code"],
    "top30": ["stage_id", "fold_id", "arm_id", "estimator_id", "model_seed",
        "is_ensemble", "decision_date", "previous_decision_date", "top30_n",
        "adjacent_overlap_n", "adjacent_turnover", "status", "reason_code"],
    "lomo": ["stage_id", "fold_id", "arm_id", "estimator_id", "model_seed", "is_ensemble",
        "lomo_unit_type", "omitted_unit_id", "retained_day_n", "mean_daily_rankic",
        "positive", "status", "reason_code"],
    "selection_policy": ["selected_arm_id", "shadow_arm_id", "identity_differs",
        "selected_worst_fold_rankic", "shadow_mean_fold_rankic", "selected_gate_vector_json",
        "shadow_gate_vector_json", "h21f07_materiality_pass", "status", "reason_code"],
    "hypothesis_readout": ["hypothesis_order", "hypothesis_id", "materiality_rule_id",
        "materiality_pass", "falsifier_triggered", "evidence_ids_json", "conclusion",
        "claim_ceiling", "status", "reason_code"],
    "gate_evidence": ["gate_order", "gate_id", "stage_id", "evaluation_status",
        "research_status", "evidence_paths_json", "observed_value_json", "threshold_json",
        "reason_code"],
    "historical_access": ["stage_order", "stage_id", "resource_id", "open_attempt_n",
        "row_materialized_n", "status", "reason_code"],
    "artifact_profile": ["profile_id", "terminal_state", "required_paths_json",
        "forbidden_paths_json", "exact_checkpoint_paths_json",
        "schema_registry_contract_sha256", "status"],
    "stage_status": ["stage_order", "stage_id", "status", "started_at_utc", "ended_at_utc",
        "worker_exit_code", "required_artifact_n", "observed_artifact_n", "reason_code"],
}
JSON_SCHEMAS = {
    "selected_predictor_estimator.json": ["schema_version", "selection_status",
        "research_estimator_selected", "selected_estimator_id", "diagnostic_fallback_estimator_id",
        "selection_reference_arm_id", "lexicographic_key", "eligible_estimator_ids",
        "registry_sha256", "created_at_utc"],
    "selected_training_arm.json": ["schema_version", "selection_status",
        "research_arm_selected", "selected_arm_id", "diagnostic_fallback_arm_id",
        "selected_estimator_id", "lexicographic_key", "eligible_arm_ids", "registry_sha256",
        "created_at_utc"],
    "mean_rankic_only_shadow_selection.json": ["schema_version", "shadow_selection_status",
        "shadow_arm_id", "candidate_pool_arm_ids", "lexicographic_key", "noncontrolling",
        "created_at_utc"],
    "refit_epoch_contract.json": ["schema_version", "arm_id", "phase_contract",
        "inner_epoch_values", "refit_epoch_n", "refit_phase_a_epoch_n",
        "refit_phase_b_epoch_n", "lower_median_rule", "created_at_utc"],
    "metadata_splitter_exit_record.json": ["schema_version", "worker_role", "process_id",
        "source_index_sha256", "pre_2023_index_sha256", "design_2023_index_sha256",
        "projected_columns", "return_panel_open_attempt_n", "label_value_materialized_n",
        "score_value_materialized_n", "worker_exit_code", "completed_at_utc"],
    "pre_2023_complete.json": ["schema_version", "run_id", "inner_checkpoint_manifest_sha256",
        "selected_predictor_estimator_sha256", "selected_training_arm_sha256",
        "shadow_selection_sha256", "refit_checkpoint_manifest_sha256",
        "refit_epoch_contract_sha256", "value_access_audit_snapshot_sha256",
        "restricted_value_parse_open_attempt_n", "completed_at_utc"],
    "semantic_reproducibility_manifest.json": ["schema_version", "run_id",
        "requirement_version", "implementation_hashes", "upstream_pins", "fold_hashes",
        "rng_contract", "training_contract", "selected_objects", "prior_failure_history_hashes",
        "terminal_state", "semantic_payload_sha256"],
    "manifest.json": ["schema_version", "run_id", "requirement_version", "terminal_state",
        "artifact_profile_id", "artifact_n", "artifacts", "requirement_sha256", "config_sha256",
        "runner_sha256", "test_sha256", "authorization_sha256", "paper_pdf_sha256",
        "upstream_pins", "decision_sha256", "report_sha256",
        "semantic_reproducibility_manifest_sha256", "output_hashes_path",
        "output_hashes_excluded_self_path", "finalized_at_utc"],
    "output_hashes.json": ["schema_version", "run_id", "entries", "entry_n",
        "entries_semantic_sha256", "excluded_self_path"],
    "schema_registry_21f.json": ["schema_version", "contract_id", "tabular_schemas",
        "json_schemas", "status_allowlists", "reason_code_allowlists", "contract_sha256"],
    "checkpoint_manifest.json": ["schema_version", "run_id", "checkpoint_entries",
        "entry_n", "entries_semantic_sha256"],
    "checkpoint_manifest.entry": ["job_order", "fold_id", "arm_id", "model_seed",
        "final_phase_id", "path", "size_bytes", "sha256", "semantic_sha256",
        "phase_a_semantic_sha256", "selected_epoch", "phase_a_selected_epoch"],
    "failure_record.json": ["schema_version", "run_id", "failed_stage_id", "failed_gate_id",
        "error_type", "error_message", "worker_exit_code", "last_complete_stage_id",
        "value_access_audit_sha256", "historical_holdout_access_audit_sha256", "created_at_utc"],
}


def schema_registry_contract() -> dict[str, Any]:
    payload = {
        "schema_version": "21F_SCHEMA_REGISTRY_V1", "contract_id": "21F_CLOSED_SCHEMA_V1",
        "tabular_schemas": TABULAR_SCHEMAS, "json_schemas": JSON_SCHEMAS,
        "status_allowlists": {
            "evaluation_status": ["pass", "fail", "not_run"],
            "research_status": ["pass", "fail", "not_applicable"],
            "row_status": ["pass", "fail", "not_evaluable"],
            "job_status": ["planned", "complete", "fail"],
            "stage_status": ["pending", "running", "complete", "fail"],
        },
        "reason_code_allowlists": ["NA", "authorization_invalid", "upstream_drift",
            "hash_mismatch", "schema_mismatch", "row_key_mismatch", "outcome_date_purge_fail",
            "firewall_violation", "worker_nonzero", "timeout", "oom_no_fallback",
            "non_finite", "coverage_fail", "insufficient_paired_days", "convergence_fail",
            "collapse_detected", "no_eligible_estimator", "no_eligible_arm",
            "no_finite_shadow_arm", "rank_repair_floor_fail", "drc_increment_fail",
            "morphology_fail", "research_threshold_fail"],
    }
    payload["contract_sha256"] = stable_hash(payload)
    return payload


def validate_authorization(config: Mapping[str, Any]) -> AuthorizationResult:
    path = workspace_path(config["paths"]["execution_authorization"])
    if not path.exists():
        return AuthorizationResult("fail", ("authorization_missing",), None, None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return AuthorizationResult("fail", (f"authorization_invalid:{exc}",), None, None)
    errors: list[str] = []
    if set(payload) != AUTH_KEYS:
        errors.append("authorization_exact_keys_mismatch")
    bindings = {
        "run_id": RUN_ID, "requirement_version": REQUIREMENT_VERSION,
        "approved_requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "approved_config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "approved_runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "approved_test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "approved_paper_pdf_sha256": config["upstream_pins"]["paper_pdf"]["sha256"],
        "approved_upstream_21b_manifest_sha256": config["upstream_pins"]["21b_manifest"]["sha256"],
        "approved_upstream_21b_output_hashes_sha256": config["upstream_pins"]["21b_output_hashes"]["sha256"],
        "approved_upstream_21c_manifest_sha256": config["upstream_pins"]["21c_manifest"]["sha256"],
        "approved_upstream_21c_output_hashes_sha256": config["upstream_pins"]["21c_output_hashes"]["sha256"],
        "approved_upstream_21d_manifest_sha256": config["upstream_pins"]["21d_manifest"]["sha256"],
        "approved_upstream_21d_output_hashes_sha256": config["upstream_pins"]["21d_output_hashes"]["sha256"],
        "approved_upstream_21e_manifest_sha256": config["upstream_pins"]["21e_manifest"]["sha256"],
        "approved_upstream_21e_output_hashes_sha256": config["upstream_pins"]["21e_output_hashes"]["sha256"],
        "approved_dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "approved_device_fingerprint_sha256": current_device_fingerprint(),
        "approved_artifact_profile_id": PROFILE_ID,
        "approved_artifact_profile_registry_contract_sha256": stable_hash(artifact_profile_contract()),
        "approved_schema_registry_contract_sha256": schema_registry_contract()["contract_sha256"],
    }
    for key, expected in bindings.items():
        if payload.get(key) != expected:
            errors.append(f"{key}_mismatch")
    if payload.get("allowed_runtime_field_differences") != []:
        errors.append("runtime_differences_not_empty")
    if not str(payload.get("approved_by", "")).strip():
        errors.append("human_approval_missing")
    if not str(payload.get("approved_at_utc", "")).strip():
        errors.append("approval_time_missing")
    return AuthorizationResult(
        "pass" if not errors else "fail", tuple(errors), payload,
        file_sha(path),
    )


class PointwiseMLPDecoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear_1 = nn.Linear(LATENT_DIM, 64)
        self.linear_2 = nn.Linear(64, 1)

    def forward(self, latent: Tensor) -> Tensor:
        return self.linear_2(F.silu(self.linear_1(latent)))


def build_model(arm_id: str, model_seed: int) -> nn.Module:
    if arm_id not in ARM_IDS:
        raise ContractError(f"unknown training arm: {arm_id}")
    model = PINNED_21C.build_model(model_seed)
    if arm_id == "T4_CSZ_STOPGRAD_POINTWISE_MLP":
        decoder = PointwiseMLPDecoder()
        generator = torch.Generator(device="cpu").manual_seed(model_seed + 53)
        dummy = PINNED_21C.REAKAModel()
        with torch.no_grad():
            # Advance the same generator through the exact 21C common-parameter
            # initialization before consuming T4-only decoder draws.
            PINNED_21C._initialize_lstm(dummy.return_encoder, generator)
            PINNED_21C._initialize_lstm(dummy.feature_encoder, generator)
            PINNED_21C._initialize_linear(dummy.gate_linear, generator)
            PINNED_21C._initialize_linear(dummy.selector_linear, generator)
            dummy.K_codebook.weight.normal_(0.0, 0.01, generator=generator)
            dummy.K_codebook.weight.add_(torch.eye(LATENT_DIM).unsqueeze(0))
            PINNED_21C._initialize_linear(dummy.decoder, generator)
            PINNED_21C._initialize_linear(dummy.denoiser_linear_1, generator)
            PINNED_21C._initialize_linear(dummy.denoiser_linear_2, generator)
            PINNED_21C._initialize_linear(dummy.denoiser_linear_3, generator)
            nn.init.xavier_uniform_(decoder.linear_1.weight, generator=generator)
            nn.init.zeros_(decoder.linear_1.bias)
            nn.init.xavier_uniform_(decoder.linear_2.weight, generator=generator)
            nn.init.zeros_(decoder.linear_2.bias)
        model.decoder = decoder
    return model


def ordered_parameter_names(model: nn.Module) -> list[str]:
    return [name for name, _ in model.named_parameters()]


def model_state_semantic_hash(state: Mapping[str, Tensor]) -> str:
    return PINNED_21C.model_state_semantic_hash(state)


def hard_st_source_latent(
    model: nn.Module, y: Tensor, x: Tensor, *, tau: float,
    training_selector: bool, gumbel_u: Tensor | None = None,
) -> dict[str, Tensor]:
    latent, h_y, h_x, gate = model.encode(y, x)
    logits = F.leaky_relu(model.selector_linear(torch.cat((latent, h_y), dim=-1)), 0.01)
    if training_selector:
        if gumbel_u is None or gumbel_u.shape != logits.shape:
            raise ContractError("hard-ST selector requires exact gumbel tensor")
        clamped = gumbel_u.to(torch.float64).clamp(1e-10, 1.0 - 1e-10)
        noise = (-torch.log(-torch.log(clamped))).to(logits.dtype)
        soft = torch.softmax((logits + noise) / tau, dim=-1)
        hard = F.one_hot(torch.argmax(soft, dim=-1), N_OPERATOR).to(soft.dtype)
        selector = hard - soft.detach() + soft
    else:
        selector = F.one_hot(torch.argmax(logits, dim=-1), N_OPERATOR).to(logits.dtype)
    selected = torch.einsum("btq,qij->btij", selector, model.K_codebook())
    predicted = torch.einsum("btij,btj->bti", selected, latent)
    return {"Z_source": latent, "H_y": h_y, "H_x": h_x, "G": gate,
        "selector_logits": logits, "selector": selector, "K_selected": selected,
        "Z_hat_shifted": predicted}


def _date_group_indices(dates: Sequence[str]) -> tuple[np.ndarray, list[tuple[str, np.ndarray]]]:
    date_array = np.asarray(dates, dtype=str)
    order = np.argsort(date_array, kind="stable")
    ordered_dates = date_array[order]
    unique_dates, starts = np.unique(ordered_dates, return_index=True)
    stops = np.r_[starts[1:], len(order)]
    return date_array, [(str(date), order[start:stop])
                        for date, start, stop in zip(unique_dates, starts, stops, strict=True)]


def decision_cs_zscore(panel: np.ndarray, dates: Sequence[str]) -> tuple[np.ndarray, pd.DataFrame]:
    values = np.asarray(panel, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 11 or len(values) != len(dates):
        raise ContractError("return panel must be [N,11]")
    transformed = np.empty_like(values)
    audit: list[dict[str, Any]] = []
    _, date_groups = _date_group_indices(dates)
    for date, rows in date_groups:
        for position in range(11):
            raw = values[rows, position]
            mean = float(np.mean(raw, dtype=np.float64))
            std = float(np.std(raw, ddof=0, dtype=np.float64))
            floor = std < 1e-6
            z = (raw - mean) / max(std, 1e-6)
            transformed[rows, position] = z
            audit.append({"decision_date": date, "position": position, "row_n": len(rows),
                "raw_mean": mean, "raw_std_ddof0": std, "sigma_floor_applied": floor,
                "transformed_mean": float(np.mean(z)),
                "transformed_std_ddof0": float(np.std(z, ddof=0))})
    if not np.isfinite(transformed).all():
        raise ContractError("return transform produced non-finite values")
    return transformed.astype(np.float32), pd.DataFrame(audit)


def diffusion_schedule(device: torch.device | str) -> dict[str, Tensor]:
    return PINNED_21C.diffusion_schedule(device=device)


def training_losses(
    model: nn.Module, arm_id: str, y_source: Tensor, x_source: Tensor,
    y_teacher: Tensor, x_teacher: Tensor, forecast_y: Tensor, *, tau: float,
    gumbel_u: Tensor, diffusion_timestep: Tensor | None,
    epsilon: Tensor | None, phase_id: str = "joint",
) -> dict[str, Tensor]:
    source = hard_st_source_latent(model, y_source, x_source, tau=tau,
        training_selector=True, gumbel_u=gumbel_u)
    teacher = model.teacher_latent(y_teacher, x_teacher)
    koop = torch.mean((teacher - source["Z_hat_shifted"]) ** 2)
    decoded_source = model.decoder(source["Z_source"])
    if arm_id == "T3_CSZ_TWO_STAGE_LINEAR" and phase_id == "phase_a":
        decoded_shifted = model.decoder(teacher)
        source_rec = torch.mean((decoded_source - y_source) ** 2)
        shifted_rec = torch.mean((decoded_shifted[:, :9] - y_teacher[:, :9]) ** 2)
        rec = 0.5 * (source_rec + shifted_rec) + torch.mean(
            (decoded_shifted[:, 9, 0] - forecast_y.reshape(-1)) ** 2)
        zero = torch.zeros((), dtype=rec.dtype, device=rec.device)
        return {"L_rec": rec, "L_koop": koop, "L_diff": zero,
            "Z_teacher_shifted": teacher, **source}
    if diffusion_timestep is None or epsilon is None:
        raise ContractError("joint/phase-B losses require diffusion draws")
    target = teacher - source["Z_hat_shifted"]
    if phase_id == "phase_b":
        target = target.detach()
    index = diffusion_timestep.long() - 1
    schedule = diffusion_schedule(target.device)
    alpha_bar = schedule["alpha_bar"][index].unsqueeze(-1)
    x_s = alpha_bar.sqrt() * target + (1.0 - alpha_bar).sqrt() * epsilon
    epsilon_hat = model.denoise(x_s, diffusion_timestep, source["Z_source"])
    diff = torch.mean((epsilon_hat - epsilon) ** 2)
    if phase_id == "phase_b":
        zero = torch.zeros((), dtype=diff.dtype, device=diff.device)
        return {"L_rec": zero, "L_koop": zero, "L_diff": diff,
            "Z_teacher_shifted": teacher, **source}
    residual_hat = (x_s - (1.0 - alpha_bar).sqrt() * epsilon_hat) / alpha_bar.sqrt()
    reconstruction_latent = source["Z_hat_shifted"] + residual_hat
    if arm_id in {"T2_CSZ_STOPGRAD_LINEAR", "T4_CSZ_STOPGRAD_POINTWISE_MLP"}:
        reconstruction_latent = reconstruction_latent.detach()
    decoded_shifted = model.decoder(reconstruction_latent)
    source_rec = torch.mean((decoded_source - y_source) ** 2)
    shifted_rec = torch.mean((decoded_shifted[:, :9] - y_teacher[:, :9]) ** 2)
    rec = 0.5 * (source_rec + shifted_rec) + torch.mean(
        (decoded_shifted[:, 9, 0] - forecast_y.reshape(-1)) ** 2)
    return {"L_rec": rec, "L_koop": koop, "L_diff": diff,
        "Z_teacher_shifted": teacher, **source}


def row_draw_seed(run_id: str, model_seed: int, row_key_hash: str, draw_idx: int) -> int:
    preimage = f"{run_id}|{model_seed}|{row_key_hash}|{draw_idx}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(preimage).digest()[:8], "big") % (2**63)


def row_noise_schedule(row_key_hash: str, model_seed: int, draw_idx: int) -> Tensor:
    generator = torch.Generator(device="cpu").manual_seed(
        row_draw_seed(RUN_ID, model_seed, row_key_hash, draw_idx)
    )
    return torch.randn((DIFFUSION_STEPS, LOOKBACK, LATENT_DIM),
        dtype=torch.float32, device="cpu", generator=generator)


def stacked_noise_schedules(keys: Sequence[str], model_seed: int, draw_idx: int,
                            device: torch.device) -> Tensor:
    if not keys:
        raise ContractError("row-keyed noise batch must not be empty")
    return torch.stack([row_noise_schedule(key, model_seed, draw_idx) for key in keys]).to(device)


def _reverse_ddpm(model: nn.Module, source: Mapping[str, Tensor], schedule_noise: Tensor) -> Tensor:
    schedule = diffusion_schedule(source["Z_source"].device)
    residual = schedule_noise[:, 0]
    for step in range(DIFFUSION_STEPS, 0, -1):
        index = step - 1
        timestep = torch.full(residual.shape[:2], step, dtype=torch.long, device=residual.device)
        epsilon_hat = model.denoise(residual, timestep, source["Z_source"])
        mean = (residual - schedule["beta"][index] * epsilon_hat /
                torch.sqrt(1.0 - schedule["alpha_bar"][index])) / torch.sqrt(schedule["alpha"][index])
        residual = (mean + torch.sqrt(schedule["posterior_variance"][index]) *
                    schedule_noise[:, DIFFUSION_STEPS - step + 1]) if step > 1 else mean
    return residual


def _reverse_ddim(model: nn.Module, source: Mapping[str, Tensor], x_t: Tensor) -> Tensor:
    schedule = diffusion_schedule(source["Z_source"].device)
    residual = x_t
    for step in range(DIFFUSION_STEPS, 0, -1):
        index = step - 1
        timestep = torch.full(residual.shape[:2], step, dtype=torch.long, device=residual.device)
        epsilon_hat = model.denoise(residual, timestep, source["Z_source"])
        alpha_bar_t = schedule["alpha_bar"][index]
        x0_hat = (residual - torch.sqrt(1.0 - alpha_bar_t) * epsilon_hat) / torch.sqrt(alpha_bar_t)
        if step == 1:
            residual = x0_hat
        else:
            alpha_bar_previous = schedule["alpha_bar"][index - 1]
            residual = torch.sqrt(alpha_bar_previous) * x0_hat + torch.sqrt(1.0 - alpha_bar_previous) * epsilon_hat
    return residual


@torch.no_grad()
def estimator_scores_batch(
    model: nn.Module, estimator_id: str, y_source: Tensor, x_source: Tensor,
    row_keys: Sequence[str], model_seed: int,
) -> Tensor:
    source = hard_st_source_latent(model, y_source, x_source, tau=0.1, training_selector=False)
    if estimator_id == "Q6_KOOPMAN_ONLY":
        return model.decoder(source["Z_hat_shifted"])[:, 9, 0]
    if estimator_id == "Q5_ZERO_NOISE_REVERSE_PROXY":
        residual = _reverse_ddpm(model, source, torch.zeros(
            (len(y_source), DIFFUSION_STEPS, LOOKBACK, LATENT_DIM), device=y_source.device))
        return model.decoder(source["Z_hat_shifted"] + residual)[:, 9, 0]
    if estimator_id == "Q4_DDIM_ETA0_SCORE":
        schedules = stacked_noise_schedules(row_keys, model_seed, 0, y_source.device)
        residual = _reverse_ddim(model, source, schedules[:, 0])
        return model.decoder(source["Z_hat_shifted"] + residual)[:, 9, 0]
    draw_n = {"Q0_CURRENT_SCORE_MEAN8": 8, EPOCH_SELECTOR_ID: 8,
        "Q1_SCORE_MEAN64": 64,
        "Q2_SCORE_MEAN256_REF": 256, "Q3_ANTITHETIC_SCORE_MEAN64": 64,
        "Q7_LATENT_MEAN256_THEN_DECODE": 256}.get(estimator_id)
    if draw_n is None:
        raise ContractError(f"unknown estimator: {estimator_id}")
    accumulator: Tensor | None = None
    for draw_idx in range(draw_n):
        if estimator_id == "Q3_ANTITHETIC_SCORE_MEAN64":
            base_idx = draw_idx // 2
            schedules = stacked_noise_schedules(row_keys, model_seed, base_idx, y_source.device)
            if draw_idx % 2:
                schedules = -schedules
        else:
            schedules = stacked_noise_schedules(row_keys, model_seed, draw_idx, y_source.device)
        residual = _reverse_ddpm(model, source, schedules)
        corrected = source["Z_hat_shifted"] + residual
        value = corrected if estimator_id == "Q7_LATENT_MEAN256_THEN_DECODE" else model.decoder(corrected)[:, 9, 0]
        value64 = value.to(torch.float64)
        accumulator = value64 if accumulator is None else accumulator + value64
    assert accumulator is not None
    mean = accumulator / draw_n
    if estimator_id == "Q7_LATENT_MEAN256_THEN_DECODE":
        mean = model.decoder(mean.to(y_source.dtype))[:, 9, 0]
    return mean.to(torch.float32)


@torch.no_grad()
def stochastic_prefix_scores_batch(
    model: nn.Module, y_source: Tensor, x_source: Tensor, row_keys: Sequence[str],
    model_seed: int, *, prefixes: Sequence[int], antithetic: bool,
) -> dict[int, Tensor]:
    targets = tuple(sorted(set(int(value) for value in prefixes)))
    if not targets or targets[0] <= 0 or targets[-1] > 256:
        raise ContractError("stochastic prefix targets must be within 1..256")
    source = hard_st_source_latent(model, y_source, x_source, tau=0.1, training_selector=False)
    accumulator = torch.zeros(len(y_source), dtype=torch.float64, device=y_source.device)
    results: dict[int, Tensor] = {}
    for draw_idx in range(targets[-1]):
        base_idx = draw_idx // 2 if antithetic else draw_idx
        schedules = stacked_noise_schedules(row_keys, model_seed, base_idx, y_source.device)
        if antithetic and draw_idx % 2:
            schedules = -schedules
        corrected = source["Z_hat_shifted"] + _reverse_ddpm(model, source, schedules)
        accumulator += model.decoder(corrected)[:, 9, 0].to(torch.float64)
        completed = draw_idx + 1
        if completed in targets:
            results[completed] = (accumulator / completed).to(torch.float32)
    return results


@torch.no_grad()
def stochastic_scores_batch(
    model: nn.Module, y_source: Tensor, x_source: Tensor, row_keys: Sequence[str],
    model_seed: int, *, draw_n: int, antithetic: bool,
) -> Tensor:
    return stochastic_prefix_scores_batch(model, y_source, x_source, row_keys,
        model_seed, prefixes=(draw_n,), antithetic=antithetic)[draw_n]


def retained_row_hash(row_keys: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps(
        list(row_keys), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def configure_determinism() -> None:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def hypothesis_registry() -> pd.DataFrame:
    rows = [
        (1, "H21F01_RETURN_SCALE_NECESSARY", "decision-CS z-score improves both inner folds", "T1-T0", "M_H01"),
        (2, "H21F02_GRADIENT_GRAPH_MATERIAL", "stopgrad improves coupled", "T2-T1", "M_H02"),
        (3, "H21F03_TWO_STAGE_REPAIR", "two-stage improves joint stopgrad", "T3-T2", "M_H03"),
        (4, "H21F04_DECODER_ROLE_MATERIAL", "decoder topology materially changes ordering", "T4-T2", "M_H04"),
        (5, "H21F05_PREDICTOR_ESTIMATOR_UNSTABLE", "ordinary 64-draw mean can fail convergence", "Q1-vs-Q2", "M_H05"),
        (6, "H21F06_DRC_INCREMENTAL_VALUE", "selected DRC adds value over same-backbone K0", "selected-DRC-vs-K0", "M_H06"),
        (7, "H21F07_SELECTION_POLICY_DIFFERENCE", "morphology selection differs from mean-only", "selected-vs-shadow", "M_H07"),
        (8, "H21F08_AUTHOR_CODE_REMAINS_UNKNOWN", "author code remains unidentified", "all-evidence", "M_H08"),
    ]
    return pd.DataFrame([{ "hypothesis_order": order, "hypothesis_id": hid,
        "statement": statement, "intervention_id": intervention,
        "materiality_rule_id": materiality, "falsifier": f"{materiality}_not_passed",
        "allowed_conclusion": "design_contaminated_semantic_repair_diagnostic_only",
        "status": "pre_registered"} for order, hid, statement, intervention, materiality in rows])


def training_arm_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    columns = ["arm_order", "arm_id", "return_transform", "loss_weight_contract",
        "gradient_graph", "phase_contract", "decoder_id", "candidate_role", "status"]
    return pd.DataFrame([{"arm_order": arm["arm_order"], "arm_id": arm["arm_id"],
        "return_transform": arm["return_transform"], "loss_weight_contract": "21F_SHARED_GRAD_CAL_V1",
        "gradient_graph": arm["gradient_graph"], "phase_contract": arm["phase_contract"],
        "decoder_id": arm["decoder_id"], "candidate_role": "controlled_training_semantics",
        "status": "pre_registered"} for arm in config["training_arms"]], columns=columns)


def predictor_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    definitions = {
        "Q0_CURRENT_SCORE_MEAN8": "21C exact replay first 8 score draws",
        "Q1_SCORE_MEAN64": "ordinary prefix64 decoded score mean",
        "Q2_SCORE_MEAN256_REF": "ordinary ref256 decoded score mean",
        "Q3_ANTITHETIC_SCORE_MEAN64": "32 full-schedule antithetic pairs",
        "Q4_DDIM_ETA0_SCORE": "eta0 DDIM from registered xT",
        "Q5_ZERO_NOISE_REVERSE_PROXY": "zero-noise DDPM posterior-mean proxy",
        "Q6_KOOPMAN_ONLY": "decode Koopman forecast without denoiser",
        "Q7_LATENT_MEAN256_THEN_DECODE": "mean corrected latent then decode",
    }
    restrictions = {
        "Q0_CURRENT_SCORE_MEAN8": "exact replay control", "Q5_ZERO_NOISE_REVERSE_PROXY": "not conditional mean",
        "Q6_KOOPMAN_ONLY": "residual attribution only", "Q7_LATENT_MEAN256_THEN_DECODE": "decoder sensitivity only",
    }
    columns = ["estimator_order", "estimator_id", "definition_id", "draw_n",
        "reference_draw_n", "candidate_eligible", "selection_reference_arm_id",
        "claim_restriction", "status"]
    return pd.DataFrame([{"estimator_order": item["estimator_order"],
        "estimator_id": item["estimator_id"], "definition_id": definitions[item["estimator_id"]],
        "draw_n": item["draw_n"], "reference_draw_n": item["reference_draw_n"],
        "candidate_eligible": item["candidate_eligible"],
        "selection_reference_arm_id": "T1_CSZ_COUPLED_LINEAR",
        "claim_restriction": restrictions.get(item["estimator_id"], "local point estimator"),
        "status": "pre_registered"} for item in config["predictor_estimators"]], columns=columns)


def contrast_registry() -> pd.DataFrame:
    rows = [
        (1, "C01", "T1_CSZ_COUPLED_LINEAR", "T0_RAW_COUPLED_LINEAR", "F_INNER", "M_H01"),
        (2, "C02", "T2_CSZ_STOPGRAD_LINEAR", "T1_CSZ_COUPLED_LINEAR", "F_INNER", "M_H02"),
        (3, "C03", "T3_CSZ_TWO_STAGE_LINEAR", "T2_CSZ_STOPGRAD_LINEAR", "F_INNER", "M_H03"),
        (4, "C04", "T4_CSZ_STOPGRAD_POINTWISE_MLP", "T2_CSZ_STOPGRAD_LINEAR", "F_INNER", "M_H04"),
        (10, "C10", "SELECTED_DRC", "SAME_BACKBONE_K0", "F_DESIGN_LATE", "M_H06"),
        (11, "C11", "SELECTED_DRC", "Q0_CURRENT_SCORE_MEAN8", "F_DESIGN_LATE", "RANK_REPAIR_FLOOR"),
    ]
    return pd.DataFrame([{"contrast_order": order, "contrast_id": cid,
        "left_id": left, "right_id": right, "family_id": family,
        "metric_id": "mean_daily_rankic_delta", "materiality_rule_id": rule,
        "claim_restriction": "design_contaminated_diagnostic_only", "status": "pre_registered"}
        for order, cid, left, right, family, rule in rows])


def _project_sequence(sequence: pd.DataFrame, exclusions: frozenset[str]) -> pd.DataFrame:
    required = ["fold", "decision_date", "instrument", "fold_panel_row_idx",
        "x_cache_row_indices", "source_dates", "row_key_hash"]
    if not set(required).issubset(sequence.columns):
        raise ContractError("sequence metadata schema drift")
    projected = sequence.loc[:, required]
    return projected.loc[~projected["instrument"].astype(str).isin(exclusions)].copy()


def _split_contract_frame(frame: pd.DataFrame, split_id: str,
                          date_min: str, date_max: str) -> pd.DataFrame:
    dates = pd.to_datetime(frame["decision_date"])
    selected = frame.loc[dates.between(pd.Timestamp(date_min), pd.Timestamp(date_max))].copy()
    selected = selected.drop(columns=["fold"])
    selected.insert(0, "fold_id", split_id)
    selected = selected.sort_values(["decision_date", "instrument"], kind="mergesort").reset_index(drop=True)
    return selected


def build_metadata_indices(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sequence_path = workspace_path(config["inputs"]["sequence_index"], must_exist=True)
    if file_sha(sequence_path) != config["upstream_pins"]["sequence_index"]["sha256"]:
        raise ContractError("sequence index hash drift")
    exclusions_path = workspace_path(config["inputs"]["exclusion_registry"], must_exist=True)
    if file_sha(exclusions_path) != config["inputs"]["exclusion_registry_sha256"]:
        raise ContractError("exclusion registry hash drift")
    exclusions_frame = pd.read_csv(exclusions_path, dtype=str, keep_default_na=False)
    if len(exclusions_frame) != 396 or exclusions_frame["instrument"].duplicated().any():
        raise ContractError("exclusion registry cardinality drift")
    sequence = pd.read_parquet(sequence_path)
    projected = _project_sequence(sequence, frozenset(exclusions_frame["instrument"]))
    train = projected.loc[projected["fold"].eq("train")]
    pieces: list[pd.DataFrame] = []
    registry_rows: list[dict[str, Any]] = []
    for item in config["inner_folds"]:
        fit = _split_contract_frame(train, item["fit_id"], item["fit_date_min"], item["fit_date_max"])
        pieces.append(fit)
        registry_rows.append(_validate_index_piece(fit, item["fit_id"], "fit", item,
            prefix="fit"))
        if item["select_id"] is not None:
            select = _split_contract_frame(train, item["select_id"], item["select_date_min"], item["select_date_max"])
            pieces.append(select)
            registry_rows.append(_validate_index_piece(select, item["select_id"], "selection", item,
                prefix="select"))
    pre = pd.concat(pieces, ignore_index=True)
    design_pieces = []
    for fold, split_id in (("validation_early", "DESIGN_EARLY_2023"),
                           ("validation_late", "DESIGN_LATE_2023")):
        expected = config["retained_folds"][fold]
        item = _split_contract_frame(projected.loc[projected["fold"].eq(fold)], split_id,
            expected["date_min"], expected["date_max"])
        if len(item) != expected["row_n"] or retained_row_hash(item["row_key_hash"].astype(str).tolist()) != expected["row_key_sha256"]:
            raise ContractError(f"design metadata drift: {fold}")
        design_pieces.append(item)
    design = pd.concat(design_pieces, ignore_index=True)
    if len(pre) != 923088 or len(design) != 102099:
        raise ContractError("metadata index row formula drift")
    return pre, design, pd.DataFrame(registry_rows)


def _validate_index_piece(frame: pd.DataFrame, split_id: str, role: str,
                          contract: Mapping[str, Any], *, prefix: str) -> dict[str, Any]:
    keys = frame["row_key_hash"].astype(str).tolist()
    observed_hash = retained_row_hash(keys)
    expected_hash = contract[f"{prefix}_row_key_sha256"]
    expected_n = int(contract[f"{prefix}_row_n"])
    if len(frame) != expected_n or observed_hash != expected_hash:
        raise ContractError(f"inner split row/hash drift: {split_id}")
    return {"fold_order": int(contract["fold_order"]), "split_id": split_id, "role": role,
        "date_min": str(frame["decision_date"].min()), "date_max": str(frame["decision_date"].max()),
        "max_label_source_date": contract[f"{prefix}_max_label_source_date"], "row_n": len(frame),
        "complete_day_n": frame["decision_date"].nunique(), "instrument_n": frame["instrument"].nunique(),
        "row_key_sha256": observed_hash, "status": "pass"}


def validate_outcome_date_purge(config: Mapping[str, Any], pre_index: pd.DataFrame) -> None:
    audit_path = workspace_path(config["inputs"]["label_audit"], must_exist=True)
    if file_sha(audit_path) != config["upstream_pins"]["label_audit"]["sha256"]:
        raise ContractError("label audit hash drift")
    labels = pd.read_parquet(audit_path, columns=["row_key_hash", "label_source_date"])
    lookup = labels.drop_duplicates("row_key_hash").set_index("row_key_hash")["label_source_date"]
    for item in config["inner_folds"][:2]:
        fit = pre_index.loc[pre_index["fold_id"].eq(item["fit_id"])]
        source_dates = pd.to_datetime(fit["row_key_hash"].map(lookup))
        observed = source_dates.max().date().isoformat()
        if observed != item["fit_max_label_source_date"] or not (source_dates.max() < pd.Timestamp(item["select_date_min"])):
            raise ContractError(f"outcome-date purge failed: {item['fit_id']}")


def return_transform_audit_for_index(config: Mapping[str, Any], index: pd.DataFrame,
                                     split_ids: Sequence[str]) -> pd.DataFrame:
    root, manifest = _panel_manifest(config)
    partitions = {item["fold"]: item for item in manifest["panel_partitions"]}
    rows = []
    for split_id in split_ids:
        frame = index.loc[index["fold_id"].eq(split_id)].reset_index(drop=True)
        source_fold = "train" if split_id not in {"DESIGN_EARLY_2023", "DESIGN_LATE_2023"} else (
            "validation_early" if split_id == "DESIGN_EARLY_2023" else "validation_late")
        partition = partitions[source_fold]
        panel = np.memmap(root / partition["path"], dtype="<f4", mode="r", shape=tuple(partition["shape"]))
        raw = np.asarray(panel[frame["fold_panel_row_idx"].to_numpy(dtype=np.int64)], dtype=np.float32)
        date_values, date_groups = _date_group_indices(frame["decision_date"].astype(str).tolist())
        transformed, audit = decision_cs_zscore(raw, date_values)
        group_lookup = dict(date_groups)
        row_keys = frame["row_key_hash"].astype(str).to_numpy()
        for item in audit.to_dict("records"):
            indices = group_lookup[str(item["decision_date"])]
            keys = row_keys[indices].tolist()
            values = transformed[indices, int(item["position"])]
            rows.append({"split_id": split_id, **item,
                "raw_row_key_sha256": retained_row_hash(keys),
                "transformed_value_sha256": hashlib.sha256(values.astype("<f4").tobytes()).hexdigest(),
                "status": "pass", "reason_code": None})
    return pd.DataFrame(rows)


def initialize_access_registries(build: Path) -> None:
    access_columns = ["event_order", "worker_role", "process_id", "stage_id", "path",
        "access_mode", "metadata_only", "value_parsed", "label_value_materialized_n",
        "score_value_materialized_n", "event_time_utc", "status", "reason_code"]
    write_csv(build / "preflight/value_access_audit.csv", [], access_columns)
    historical = [{"stage_order": order, "stage_id": stage, "resource_id": "HISTORICAL_DESIGN_HOLDOUT",
        "open_attempt_n": 0, "row_materialized_n": 0, "status": "pass", "reason_code": "NA"}
        for order, stage in enumerate(STAGE_IDS)]
    write_csv(build / "historical_design_holdout_access_audit.csv", historical, list(historical[0]))
    stages = [{"stage_order": order, "stage_id": stage, "status": "pending",
        "started_at_utc": "", "ended_at_utc": "", "worker_exit_code": None,
        "required_artifact_n": 0, "observed_artifact_n": 0, "reason_code": None}
        for order, stage in enumerate(STAGE_IDS)]
    write_csv(build / "stage_status_registry.csv", stages, list(stages[0]))
    gates = [{"gate_order": order, "gate_id": gate, "stage_id": gate_stage(order),
        "evaluation_status": "not_run", "research_status": None, "evidence_paths_json": "[]",
        "observed_value_json": "{}", "threshold_json": "{}", "reason_code": None}
        for order, gate in enumerate(GATE_IDS, start=1)]
    write_csv(build / "gate_evidence_21f.csv", gates, list(gates[0]))


def append_access_event(build: Path, *, worker_role: str, stage_id: str, path: str,
                        access_mode: str, metadata_only: bool, value_parsed: bool,
                        label_value_materialized_n: int = 0,
                        score_value_materialized_n: int = 0) -> None:
    audit_path = build / "preflight/value_access_audit.csv"
    frame = pd.read_csv(audit_path, keep_default_na=False)
    row = {"event_order": len(frame) + 1, "worker_role": worker_role,
        "process_id": str(os.getpid()), "stage_id": stage_id, "path": path,
        "access_mode": access_mode, "metadata_only": metadata_only, "value_parsed": value_parsed,
        "label_value_materialized_n": label_value_materialized_n,
        "score_value_materialized_n": score_value_materialized_n,
        "event_time_utc": utc_now(), "status": "pass", "reason_code": "NA"}
    rows = frame.to_dict("records") + [row]
    write_csv(audit_path, rows, TABULAR_SCHEMAS["value_access"])


def record_nontraining_inference_seconds(config: Mapping[str, Any], stage_id: str,
                                         elapsed_seconds: float) -> None:
    path = building_output_root(config) / ".state/nontraining_inference_usage.json"
    payload = json.loads(path.read_text()) if path.exists() else {
        "schema_version": "21F_NONTRAINING_GPU_BUDGET_V1", "stage_seconds": {}}
    if stage_id in payload["stage_seconds"]:
        raise ContractError(f"nontraining inference stage already registered: {stage_id}")
    payload["stage_seconds"][stage_id] = float(elapsed_seconds)
    payload["total_seconds"] = float(sum(payload["stage_seconds"].values()))
    payload["cap_seconds"] = int(config["resources"]["nontraining_gpu_inference_cap_seconds"])
    payload["status"] = "pass" if payload["total_seconds"] <= payload["cap_seconds"] else "fail"
    write_json(path, payload)
    if payload["status"] != "pass":
        raise ContractError("combined nontraining GPU inference cap exceeded")


def restricted_pre2023_open_attempts(config: Mapping[str, Any], audit: pd.DataFrame) -> int:
    restricted = [
        config["upstream_pins"]["design_early_value_panel"]["path"],
        config["upstream_pins"]["design_late_value_panel"]["path"],
        "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21C_full_reaka_pit_proxy_replication_v4/predictions/",
        "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21D_reaka_replication_gap_causal_diagnostic_v2/predictions/",
        "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21D_reaka_replication_gap_causal_diagnostic_v2/diagnostics/inference_draw_scores/",
        "experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21E_reaka_predictor_drc_implementation_identification_v0/predictions/",
    ]
    roles = {"INNER_TRAIN", "SELECTION_COORDINATOR", "REFIT"}
    return int(sum(str(row.path).startswith(prefix) for row in audit.itertuples(index=False)
                   if row.worker_role in roles for prefix in restricted))


def gate_stage(order: int) -> str:
    return STAGE_IDS[0 if order <= 8 else 1 if order <= 14 else 2 if order <= 20 else 3 if order <= 27 else 4 if order <= 35 else 5]


def mark_stage(build: Path, stage_id: str, status: str, reason_code: str | None = None) -> None:
    path = build / "stage_status_registry.csv"
    frame = pd.read_csv(path, keep_default_na=False)
    mask = frame["stage_id"].eq(stage_id)
    if mask.sum() != 1:
        raise ContractError(f"stage registry identity missing: {stage_id}")
    frame.loc[mask, "status"] = status
    if status == "running":
        frame.loc[mask, "started_at_utc"] = utc_now()
    if status in {"complete", "fail"}:
        frame.loc[mask, "ended_at_utc"] = utc_now()
        frame.loc[mask, "worker_exit_code"] = 0 if status == "complete" else 1
    frame.loc[mask, "reason_code"] = reason_code or ""
    write_csv(path, frame.to_dict("records"), list(frame.columns))


def pass_gates(build: Path, orders: Sequence[int], evidence: Sequence[str]) -> None:
    path = build / "gate_evidence_21f.csv"
    frame = pd.read_csv(path, keep_default_na=False)
    for order in orders:
        mask = frame["gate_order"].eq(order)
        frame.loc[mask, "evaluation_status"] = "pass"
        frame.loc[mask, "research_status"] = "not_applicable"
        frame.loc[mask, "evidence_paths_json"] = json.dumps(list(evidence), separators=(",", ":"))
        frame.loc[mask, "observed_value_json"] = "{\"pass\":true}"
        frame.loc[mask, "threshold_json"] = "{}"
        frame.loc[mask, "reason_code"] = "NA"
    write_csv(path, frame.to_dict("records"), list(frame.columns))


def set_research_gate(build: Path, order: int, passed: bool, observed: Mapping[str, Any]) -> None:
    path = build / "gate_evidence_21f.csv"
    frame = pd.read_csv(path, keep_default_na=False)
    mask = frame["gate_order"].eq(order)
    frame.loc[mask, "evaluation_status"] = "pass"
    frame.loc[mask, "research_status"] = "pass" if passed else "fail"
    frame.loc[mask, "observed_value_json"] = json.dumps(dict(observed), separators=(",", ":"))
    frame.loc[mask, "reason_code"] = "NA" if passed else "research_threshold_fail"
    write_csv(path, frame.to_dict("records"), list(frame.columns))


class FeatureSequenceAccessor:
    def __init__(self, feature_memmap: np.ndarray, offsets: np.ndarray) -> None:
        self.feature_memmap = feature_memmap
        self.offsets = np.asarray(offsets, dtype=np.int64)

    def __len__(self) -> int:
        return len(self.offsets)

    def __getitem__(self, item: Any) -> np.ndarray:
        selected = self.offsets[item]
        result = np.asarray(self.feature_memmap[selected], dtype=np.float32)
        return result.reshape((-1, LOOKBACK, FEATURE_DIM) if np.asarray(selected).ndim > 1
                              else (LOOKBACK, FEATURE_DIM))


def _panel_manifest(config: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = workspace_path(config["inputs"]["panel_manifest"], must_exist=True)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("sequence_sample_index_sha256") != config["upstream_pins"]["sequence_index"]["sha256"]:
        raise ContractError("panel manifest lineage drift")
    return path.parent.parent, manifest


def load_feature_cache(config: Mapping[str, Any]) -> np.ndarray:
    _, manifest = _panel_manifest(config)
    path = workspace_path(manifest["feature_cache_memmap_path"], must_exist=True)
    if file_sha(path) != manifest["feature_cache_memmap_sha256"]:
        raise ContractError("feature cache hash drift")
    source = np.memmap(path, dtype="<f4", mode="r", shape=tuple(manifest["feature_cache_shape"]))
    result = np.array(source, dtype=np.float32, order="C", copy=True)
    result.setflags(write=False)
    return result


def load_fold_slice(config: Mapping[str, Any], split_id: str, *, worker_role: str,
                    allow_design: bool = False, feature_cache: np.ndarray | None = None) -> FoldSlice:
    build = building_output_root(config)
    index_path = build / ("preflight/design_2023_row_index.parquet" if allow_design
                          else "preflight/pre_2023_row_index.parquet")
    index = pd.read_parquet(index_path)
    frame = index.loc[index["fold_id"].eq(split_id)].reset_index(drop=True)
    if frame.empty:
        raise ContractError(f"empty registered split: {split_id}")
    root, manifest = _panel_manifest(config)
    source_fold = "train" if not allow_design else (
        "validation_early" if split_id == "DESIGN_EARLY_2023" else "validation_late")
    partition = {item["fold"]: item for item in manifest["panel_partitions"]}[source_fold]
    panel_path = root / partition["path"]
    expected_pin = config["upstream_pins"][f"{'train' if source_fold == 'train' else 'design_early' if source_fold == 'validation_early' else 'design_late'}_value_panel"]["sha256"]
    if file_sha(panel_path) != expected_pin:
        raise ContractError(f"value panel hash drift: {source_fold}")
    panel = np.memmap(panel_path, dtype="<f4", mode="r", shape=tuple(partition["shape"]))
    rows = frame["fold_panel_row_idx"].to_numpy(dtype=np.int64)
    raw = np.asarray(panel[rows], dtype=np.float32)
    stage_id = STAGE_IDS[4] if allow_design else (STAGE_IDS[3] if worker_role in {"SELECTION_COORDINATOR", "REFIT"} else STAGE_IDS[2])
    append_access_event(build, worker_role=worker_role, stage_id=stage_id,
        path=str(panel_path.relative_to(WORKSPACE)), access_mode="value_parse", metadata_only=False,
        value_parsed=True, label_value_materialized_n=len(frame))
    cache = feature_cache if feature_cache is not None else load_feature_cache(config)
    source_offsets = np.stack(frame["x_cache_row_indices"].to_numpy()).astype(np.int64)
    if allow_design:
        # No teacher path is used by the fresh readout worker.
        teacher_offsets = source_offsets
    else:
        refit = index.loc[index["fold_id"].eq("REFIT_2018_2022")].reset_index(drop=True)
        ordinal = pd.Series(np.arange(len(refit), dtype=np.int64), index=refit["row_key_hash"].astype(str))
        sample_ids = frame["row_key_hash"].astype(str).map(ordinal)
        if sample_ids.isna().any():
            raise ContractError(f"teacher mapping incomplete: {split_id}")
        teacher_path = workspace_path(config["inputs"]["teacher_sequence_index"], must_exist=True)
        teacher_table = pq.read_table(teacher_path, columns=["sample_row_id", "teacher_position", "feature_cache_row_offset"])
        teacher = teacher_table.to_pandas()
        teacher = teacher.sort_values(["sample_row_id", "teacher_position"], kind="mergesort")
        offsets_all = teacher["feature_cache_row_offset"].to_numpy(dtype=np.int64).reshape(-1, LOOKBACK)
        teacher_offsets = offsets_all[sample_ids.to_numpy(dtype=np.int64)]
    return FoldSlice(split_id, frame, raw, FeatureSequenceAccessor(cache, source_offsets),
                     FeatureSequenceAccessor(cache, teacher_offsets))


def model_panel_for_arm(fold: FoldSlice, arm_id: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    dates = fold.frame["decision_date"].astype(str).tolist()
    if arm_id == "T0_RAW_COUPLED_LINEAR":
        panel = np.asarray(fold.raw_panel, dtype=np.float32)
        audit = pd.DataFrame()
    else:
        panel, audit = decision_cs_zscore(fold.raw_panel, dates)
    return panel[:, :10, None], panel[:, 1:11, None], panel[:, 10], audit


def _optimizer(model: nn.Module, parameters: Sequence[nn.Parameter], config: Mapping[str, Any]) -> torch.optim.AdamW:
    training = config["training"]
    return torch.optim.AdamW(list(parameters), lr=float(training["learning_rate"]),
        betas=tuple(float(x) for x in training["adam_betas"]), eps=float(training["adam_eps"]),
        weight_decay=float(training["weight_decay"]), amsgrad=False, foreach=False, fused=False)


def _phase_parameters(model: nn.Module, arm_id: str, phase_id: str) -> list[nn.Parameter]:
    if arm_id != "T3_CSZ_TWO_STAGE_LINEAR" or phase_id == "phase_a":
        if arm_id == "T3_CSZ_TWO_STAGE_LINEAR":
            return [parameter for name, parameter in model.named_parameters()
                    if not name.startswith("denoiser_")]
        return list(model.parameters())
    if phase_id == "phase_b":
        for name, parameter in model.named_parameters():
            parameter.requires_grad_(name.startswith("denoiser_"))
        return [parameter for parameter in model.parameters() if parameter.requires_grad]
    raise ContractError(f"invalid phase: {phase_id}")


def _batch_loss(
    model: nn.Module, arm_id: str, phase_id: str, fold: FoldSlice,
    y_source_np: np.ndarray, y_teacher_np: np.ndarray, forecast_np: np.ndarray,
    indices: np.ndarray, *, tau: float, gumbel_generator: torch.Generator,
    diffusion_generator: torch.Generator, weights: Mapping[str, float],
    device: torch.device,
) -> tuple[Tensor, dict[str, Tensor]]:
    count = len(indices)
    y_source = torch.as_tensor(y_source_np[indices], dtype=torch.float32, device=device)
    y_teacher = torch.as_tensor(y_teacher_np[indices], dtype=torch.float32, device=device)
    forecast = torch.as_tensor(forecast_np[indices], dtype=torch.float32, device=device)
    x_source = torch.as_tensor(fold.x_source[indices], dtype=torch.float32, device=device)
    x_teacher = torch.as_tensor(fold.x_teacher[indices], dtype=torch.float32, device=device)
    uniform = torch.rand((count, LOOKBACK, N_OPERATOR), generator=gumbel_generator).to(device)
    if phase_id == "phase_a":
        timestep = epsilon = None
    else:
        timestep = torch.randint(1, DIFFUSION_STEPS + 1, (count, LOOKBACK),
            generator=diffusion_generator).to(device)
        epsilon = torch.randn((count, LOOKBACK, LATENT_DIM), generator=diffusion_generator).to(device)
    losses = training_losses(model, arm_id, y_source, x_source, y_teacher, x_teacher,
        forecast, tau=tau, gumbel_u=uniform, diffusion_timestep=timestep,
        epsilon=epsilon, phase_id=phase_id)
    if phase_id == "phase_a":
        normalizer = weights["L_rec"] + weights["L_koop"]
        total = 2.0 * (weights["L_rec"] * losses["L_rec"] +
                       weights["L_koop"] * losses["L_koop"]) / normalizer
    elif phase_id == "phase_b":
        total = losses["L_diff"]
    else:
        total = sum(weights[name] * losses[name] for name in ("L_rec", "L_koop", "L_diff"))
    return total, losses


def _global_gradient_norm(loss: Tensor, parameters: Sequence[nn.Parameter], *, retain_graph: bool) -> float:
    gradients = torch.autograd.grad(loss, parameters, retain_graph=retain_graph, allow_unused=True)
    squares = [torch.sum(gradient.detach().to(torch.float64) ** 2) for gradient in gradients if gradient is not None]
    return math.sqrt(float(torch.sum(torch.stack(squares)).cpu())) if squares else 0.0


def calibration_batches(frame: pd.DataFrame, fold_id: str, model_seed: int) -> list[np.ndarray]:
    unique_dates = np.array(sorted(frame["decision_date"].astype(str).unique()))
    strata = np.array_split(unique_dates, 4)
    batches: list[np.ndarray] = []
    for dates in strata:
        candidates = frame.loc[frame["decision_date"].astype(str).isin(dates)].copy()
        keys = candidates.apply(lambda row: hashlib.sha256(
            f"21F_SHARED_GRAD_CAL_V1|{fold_id}|{model_seed}|{row['decision_date']}|{row['instrument']}".encode()).hexdigest(), axis=1)
        candidates = candidates.assign(_sample_hash=keys).sort_values(
            ["_sample_hash", "decision_date", "instrument"], kind="mergesort").head(2048)
        if len(candidates) != 2048:
            raise ContractError("gradient calibration stratum too small")
        positions = candidates.index.to_numpy(dtype=np.int64)
        batches.extend([positions[start:start + 256] for start in range(0, 2048, 256)])
    if len(batches) != 32 or len(np.unique(np.concatenate(batches))) != 8192:
        raise ContractError("gradient calibration sampling drift")
    return batches


def calibrate_shared_weights(config: Mapping[str, Any], fold: FoldSlice,
                             model_seed: int, device: torch.device) -> tuple[dict[str, float], pd.DataFrame]:
    model = build_model("T0_RAW_COUPLED_LINEAR", model_seed).to(device)
    parameters = list(model.parameters())
    y_source, y_teacher, forecast, _ = model_panel_for_arm(fold, "T0_RAW_COUPLED_LINEAR")
    gumbel = torch.Generator(device="cpu").manual_seed(model_seed + 71)
    diffusion = torch.Generator(device="cpu").manual_seed(model_seed + 89)
    values = {name: [] for name in ("L_rec", "L_koop", "L_diff")}
    rows: list[dict[str, Any]] = []
    batches = calibration_batches(fold.frame, fold.split_id, model_seed)
    for batch_index, indices in enumerate(batches):
        _, losses = _batch_loss(model, "T0_RAW_COUPLED_LINEAR", "joint", fold,
            y_source, y_teacher, forecast, indices, tau=1.0, gumbel_generator=gumbel,
            diffusion_generator=diffusion, weights={"L_rec": 1, "L_koop": 1, "L_diff": 1},
            device=device)
        for term_index, term in enumerate(("L_rec", "L_koop", "L_diff")):
            values[term].append(_global_gradient_norm(losses[term], parameters,
                retain_graph=term_index < 2))
        keys = fold.frame.loc[indices, "row_key_hash"].astype(str).tolist()
        rows.append({"record_type": "calibration_batch", "fold_id": fold.split_id,
            "model_seed": model_seed, "temporal_stratum": batch_index // 8,
            "batch_index": batch_index % 8, "loss_term": None, "row_n": len(indices),
            "decision_date_min": str(fold.frame.loc[indices, "decision_date"].min()),
            "decision_date_max": str(fold.frame.loc[indices, "decision_date"].max()),
            "row_key_sha256": retained_row_hash(keys), "gradient_median_l2": None,
            "loss_weight": None, "ordered_parameter_names_sha256": stable_hash(ordered_parameter_names(model)),
            "status": "pass", "reason_code": None})
    medians = {term: float(np.median(observed)) for term, observed in values.items()}
    inverse = {term: float(np.clip(1.0 / max(value, 1e-12), 0.05, 20.0))
               for term, value in medians.items()}
    scale = 3.0 / sum(inverse.values())
    weights = {term: value * scale for term, value in inverse.items()}
    for term in ("L_rec", "L_koop", "L_diff"):
        rows.append({"record_type": "loss_weight", "fold_id": fold.split_id,
            "model_seed": model_seed, "temporal_stratum": None, "batch_index": None,
            "loss_term": term, "row_n": None, "decision_date_min": None,
            "decision_date_max": None, "row_key_sha256": None,
            "gradient_median_l2": medians[term], "loss_weight": weights[term],
            "ordered_parameter_names_sha256": stable_hash(ordered_parameter_names(model)),
            "status": "pass", "reason_code": None})
    return weights, pd.DataFrame(rows)


@torch.no_grad()
def score_fold(model: nn.Module, estimator_id: str, fold: FoldSlice, arm_id: str,
               model_seed: int, *, batch_size: int, device: torch.device) -> np.ndarray:
    y_source, _, _, _ = model_panel_for_arm(fold, arm_id)
    result = np.empty(len(fold.frame), dtype=np.float32)
    model.eval()
    for start in range(0, len(result), batch_size):
        stop = min(start + batch_size, len(result))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(fold.x_source[start:stop], dtype=torch.float32, device=device)
        keys = fold.frame["row_key_hash"].iloc[start:stop].astype(str).tolist()
        result[start:stop] = estimator_scores_batch(model, estimator_id, y, x, keys,
            model_seed).detach().cpu().numpy()
    if not np.isfinite(result).all():
        raise ContractError("prediction score contains NaN/Inf")
    return result


def mean_daily_rankic(scores: np.ndarray, labels: np.ndarray, dates: Sequence[str],
                      minimum_n: int = 100) -> tuple[float, pd.DataFrame]:
    frame = pd.DataFrame({"decision_date": np.asarray(dates, dtype=str),
        "score": np.asarray(scores), "label": np.asarray(labels)})
    rows = []
    for date, group in frame.groupby("decision_date", sort=True):
        status = "pass" if len(group) >= minimum_n and group[["score", "label"]].notna().all().all() else "fail"
        rho = float(spearmanr(group["score"], group["label"]).statistic) if status == "pass" else math.nan
        rows.append({"decision_date": date, "cross_section_n": len(group), "rankic": rho,
            "status": status, "reason_code": "NA" if status == "pass" else "coverage_fail"})
    table = pd.DataFrame(rows)
    valid = table.loc[table["status"].eq("pass"), "rankic"]
    if len(valid) != frame["decision_date"].nunique() or not np.isfinite(valid).all():
        raise ContractError("daily RankIC coverage/finite failure")
    return float(valid.mean()), table


def top30_by_day(frame: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    result = {}
    for date, group in frame.groupby("decision_date", sort=True):
        if len(group) < 30:
            raise ContractError("Top30 coverage failure")
        ordered = group.sort_values(["score", "instrument"], ascending=[False, True], kind="mergesort")
        result[str(date)] = tuple(ordered["instrument"].astype(str).head(30))
    return result


def daily_score_spearman(left: pd.DataFrame, right: pd.DataFrame) -> float:
    merged = left.merge(right, on=["decision_date", "instrument"], suffixes=("_l", "_r"), validate="one_to_one")
    values = [float(spearmanr(group["score_l"], group["score_r"]).statistic)
              for _, group in merged.groupby("decision_date", sort=True)]
    return float(np.median(values))


def daily_top30_overlap(left: pd.DataFrame, right: pd.DataFrame) -> float:
    left_sets, right_sets = top30_by_day(left), top30_by_day(right)
    if left_sets.keys() != right_sets.keys():
        raise ContractError("Top30 paired-date mismatch")
    return float(np.median([len(set(left_sets[date]) & set(right_sets[date])) for date in left_sets]))


def adjacent_turnover(frame: pd.DataFrame) -> float:
    sets = top30_by_day(frame)
    dates = sorted(sets)
    if len(dates) < 2:
        raise ContractError("turnover requires adjacent dates")
    return float(np.mean([1.0 - len(set(sets[dates[i - 1]]) & set(sets[dates[i]])) / 30.0
                          for i in range(1, len(dates))]))


def lomo_positive_n(fold: FoldSlice, scores: np.ndarray, unit: str) -> int:
    frame = pd.DataFrame({"decision_date": pd.to_datetime(fold.frame["decision_date"]),
        "score": scores, "label": fold.raw_panel[:, 10]})
    if unit == "quarter":
        labels = frame["decision_date"].dt.to_period("Q").astype(str)
    elif unit == "month":
        labels = frame["decision_date"].dt.to_period("M").astype(str)
    else:
        raise ContractError(f"unknown LOMO unit: {unit}")
    positive = 0
    for omitted in sorted(labels.unique()):
        retained = frame.loc[labels.ne(omitted)]
        metric = mean_daily_rankic(retained["score"].to_numpy(), retained["label"].to_numpy(),
            retained["decision_date"].astype(str).tolist())[0]
        positive += metric > 0
    return int(positive)


def cpu_state(model: nn.Module) -> dict[str, Tensor]:
    return {name: value.detach().cpu().contiguous().clone()
            for name, value in model.state_dict().items()}


def save_checkpoint(path: Path, state: Mapping[str, Tensor]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    torch.save(dict(state), temporary)
    os.replace(temporary, path)


def _train_phase(
    config: Mapping[str, Any], model: nn.Module, arm_id: str, phase_id: str,
    fit: FoldSlice, select: FoldSlice, model_seed: int, weights: Mapping[str, float],
    *, max_epochs: int, fixed_epoch_n: int | None, device: torch.device,
    hard_deadline: float | None = None,
) -> tuple[dict[str, Tensor], list[dict[str, Any]], np.ndarray]:
    parameters = _phase_parameters(model, arm_id, phase_id)
    optimizer = _optimizer(model, parameters, config)
    y_source, y_teacher, forecast, _ = model_panel_for_arm(fit, arm_id)
    steps_per_epoch = math.ceil(len(fit.frame) / int(config["training"]["batch_size"]))
    planned_steps = int(config["training"]["max_epochs"]) * steps_per_epoch
    gumbel = torch.Generator(device="cpu").manual_seed(model_seed + 71)
    diffusion = torch.Generator(device="cpu").manual_seed(model_seed + 89)
    best_metric = -math.inf
    best_state: dict[str, Tensor] | None = None
    best_scores: np.ndarray | None = None
    patience = 0
    step_index = 0
    curves: list[dict[str, Any]] = []
    selector = (config["training"]["phase_a_epoch_selection_estimator"]
                if phase_id == "phase_a" else config["training"]["epoch_selection_estimator"])
    deadline = hard_deadline if hard_deadline is not None else time.monotonic() + (
        config["resources"]["t3_inner_job_timeout_seconds"]
        if arm_id == "T3_CSZ_TWO_STAGE_LINEAR" else config["resources"]["joint_inner_job_timeout_seconds"])
    epochs_to_run = fixed_epoch_n if fixed_epoch_n is not None else max_epochs
    for epoch in range(1, epochs_to_run + 1):
        permutation = torch.randperm(len(fit.frame), generator=torch.Generator(
            device="cpu").manual_seed(model_seed + 37 + epoch - 1)).numpy()
        totals = {name: 0.0 for name in ("L_rec", "L_koop", "L_diff")}
        seen = 0
        model.train()
        for start in range(0, len(permutation), int(config["training"]["batch_size"])):
            indices = permutation[start:start + int(config["training"]["batch_size"])]
            tau = PINNED_21C.tau_for_step(step_index, planned_steps)
            total, losses = _batch_loss(model, arm_id, phase_id, fit, y_source, y_teacher,
                forecast, indices, tau=tau, gumbel_generator=gumbel,
                diffusion_generator=diffusion, weights=weights, device=device)
            optimizer.zero_grad(set_to_none=True)
            total.float().backward()
            torch.nn.utils.clip_grad_norm_(parameters, max_norm=1.0, norm_type=2.0,
                error_if_nonfinite=True, foreach=False)
            optimizer.step()
            step_index += 1
            for name in totals:
                totals[name] += float(losses[name].detach().cpu()) * len(indices)
            seen += len(indices)
        scores = score_fold(model, selector, select, arm_id, model_seed,
            batch_size=int(config["training"]["inference_batch_size_candidates"][0]), device=device)
        metric, daily = mean_daily_rankic(scores, select.raw_panel[:, 10],
            select.frame["decision_date"].astype(str).tolist(),
            int(config["training"]["minimum_rankic_n"]))
        collapse = bool(float(np.std(scores, ddof=0)) <= 1e-8)
        semantic = model_state_semantic_hash(cpu_state(model))
        curves.append({"fold_id": fit.split_id, "arm_id": arm_id, "model_seed": model_seed,
            "phase_id": phase_id, "epoch": epoch, "optimizer_step_end": step_index,
            "train_loss_rec": totals["L_rec"] / seen, "train_loss_koop": totals["L_koop"] / seen,
            "train_loss_diff": totals["L_diff"] / seen, "selector_estimator_id": selector,
            "selection_mean_rankic": metric, "selection_complete_day_n": len(daily),
            "collapse_flag": collapse, "checkpoint_semantic_sha256": semantic,
            "selection_reason": "evaluated"})
        eligible = math.isfinite(metric) and not collapse
        if eligible and metric > best_metric:
            best_metric, best_state, best_scores, patience = metric, cpu_state(model), scores.copy(), 0
        else:
            patience += 1
        if time.monotonic() > deadline:
            raise ContractError(f"training timeout: {fit.split_id}/{arm_id}/{model_seed}")
        if fixed_epoch_n is None and patience >= int(config["training"]["early_stopping_patience"]):
            break
    if fixed_epoch_n is not None:
        best_state, best_scores = cpu_state(model), scores.copy()
        best_metric = metric
    if best_state is None or best_scores is None:
        raise ContractError(f"no eligible epoch: {fit.split_id}/{arm_id}/{model_seed}/{phase_id}")
    model.load_state_dict(best_state, strict=True)
    selected_epoch = next(row["epoch"] for row in curves
        if row["selection_mean_rankic"] == best_metric)
    for row in curves:
        row["selection_reason"] = "first_maximum" if row["epoch"] == selected_epoch else "not_selected"
    return best_state, curves, best_scores


def train_inner_job(config: Mapping[str, Any], arm_id: str, fit: FoldSlice,
                    select: FoldSlice, model_seed: int, weights: Mapping[str, float],
                    device: torch.device) -> tuple[dict[str, Tensor], list[dict[str, Any]],
                                                   np.ndarray, dict[str, Any]]:
    model = build_model(arm_id, model_seed).to(device)
    initial_hash = model_state_semantic_hash(cpu_state(model))
    phase_a_hash = None
    if arm_id == "T3_CSZ_TWO_STAGE_LINEAR":
        deadline = time.monotonic() + config["resources"]["t3_inner_job_timeout_seconds"]
        _, curves_a, _ = _train_phase(config, model, arm_id, "phase_a", fit, select,
            model_seed, weights, max_epochs=int(config["training"]["max_epochs"]),
            fixed_epoch_n=None, device=device, hard_deadline=deadline)
        phase_a_hash = model_state_semantic_hash(cpu_state(model))
        state, curves_b, scores = _train_phase(config, model, arm_id, "phase_b", fit,
            select, model_seed, weights, max_epochs=int(config["training"]["max_epochs"]),
            fixed_epoch_n=None, device=device, hard_deadline=deadline)
        curves = curves_a + curves_b
    else:
        state, curves, scores = _train_phase(config, model, arm_id, "joint", fit, select,
            model_seed, weights, max_epochs=int(config["training"]["max_epochs"]),
            fixed_epoch_n=None, device=device)
    phase_rows = {}
    for phase in sorted({row["phase_id"] for row in curves}):
        selected = [row for row in curves if row["phase_id"] == phase and row["selection_reason"] == "first_maximum"]
        if len(selected) != 1:
            raise ContractError("phase epoch selection is not unique")
        phase_rows[phase] = selected[0]
    return state, curves, scores, {"initial_state_semantic_sha256": initial_hash,
        "phase_a_semantic_sha256": phase_a_hash, "phase_rows": phase_rows,
        "ordered_parameter_names_sha256": stable_hash(ordered_parameter_names(model))}


def prediction_frame(fold: FoldSlice, arm_id: str, estimator_id: str,
                     seed_scores: Mapping[int, np.ndarray], stage_id: str,
                     score_variant: str | None = None) -> pd.DataFrame:
    base = pd.DataFrame({"stage_id": stage_id, "fold_id": fold.split_id,
        "arm_id": arm_id, "estimator_id": estimator_id,
        "score_variant": score_variant or estimator_id.lower(),
        "decision_date": pd.to_datetime(fold.frame["decision_date"]).dt.date,
        "instrument": fold.frame["instrument"].astype(str).to_numpy(),
        "row_key_hash": fold.frame["row_key_hash"].astype(str).to_numpy(),
        "label": fold.raw_panel[:, 10].astype(np.float32)})
    rows = []
    for seed in MODEL_SEEDS:
        item = base.copy()
        item["model_seed"] = seed
        item["is_ensemble"] = False
        item["score"] = np.asarray(seed_scores[seed], dtype=np.float32)
        rows.append(item)
    ensemble = base.copy()
    ensemble["model_seed"] = pd.NA
    ensemble["is_ensemble"] = True
    ensemble["score"] = np.stack([seed_scores[seed].astype(np.float64)
        for seed in MODEL_SEEDS]).mean(axis=0).astype(np.float32)
    rows.append(ensemble)
    columns = TABULAR_SCHEMAS["prediction"]
    return pd.concat(rows, ignore_index=True)[columns]


def _process_rss_bytes() -> int:
    fields = Path("/proc/self/statm").read_text(encoding="utf-8").split()
    return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))


def tensors_all_finite(values: Iterable[Tensor]) -> bool:
    return all(bool(torch.isfinite(value).all().item()) for value in values)


def _prepare_lane_root(parent_build: Path, root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    (root / "preflight").mkdir(parents=True)
    source = parent_build / "preflight/pre_2023_row_index.parquet"
    target = root / "preflight/pre_2023_row_index.parquet"
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    write_csv(root / "preflight/value_access_audit.csv", [], TABULAR_SCHEMAS["value_access"])
    (root / ".state").mkdir()


def parallel_gpu_probe_worker(config: Mapping[str, Any], lane_id: int) -> None:
    started = time.monotonic()
    configure_determinism()
    if not torch.cuda.is_available():
        raise ContractError("parallel probe requires CUDA")
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats(0)
    device = torch.device("cuda")
    feature_cache = load_feature_cache(config)
    fold_contract = config["inner_folds"][lane_id]
    fit = load_fold_slice(config, fold_contract["fit_id"], worker_role="INNER_TRAIN",
        feature_cache=feature_cache)
    arm_id = ("T1_CSZ_COUPLED_LINEAR" if lane_id == 0
              else "T4_CSZ_STOPGRAD_POINTWISE_MLP")
    seed = MODEL_SEEDS[lane_id]
    model = build_model(arm_id, seed).to(device)
    parameters = list(model.parameters())
    optimizer = _optimizer(model, parameters, config)
    y_source, y_teacher, forecast, _ = model_panel_for_arm(fit, arm_id)
    indices = np.arange(min(int(config["training"]["batch_size"]), len(fit.frame)), dtype=np.int64)
    total, losses = _batch_loss(model, arm_id, "joint", fit, y_source, y_teacher,
        forecast, indices, tau=1.0,
        gumbel_generator=torch.Generator(device="cpu").manual_seed(seed + 71),
        diffusion_generator=torch.Generator(device="cpu").manual_seed(seed + 89),
        weights={"L_rec": 1.0 / 3.0, "L_koop": 1.0 / 3.0, "L_diff": 1.0 / 3.0},
        device=device)
    optimizer.zero_grad(set_to_none=True)
    total.float().backward()
    torch.nn.utils.clip_grad_norm_(parameters, max_norm=1.0, norm_type=2.0,
        error_if_nonfinite=True, foreach=False)
    optimizer.step()
    torch.cuda.synchronize(device)
    finite = bool(torch.isfinite(total).all().item() and tensors_all_finite(losses.values()))
    if not finite:
        raise ContractError("parallel resource probe produced non-finite loss")
    build = building_output_root(config)
    write_json(build / ".state/probe_result.json", {
        "schema_version": "21F_PARALLEL_LANE_PROBE_V1", "lane_id": lane_id,
        "arm_id": arm_id, "fold_id": fit.split_id, "model_seed": seed,
        "batch_size": len(indices), "finite_loss": finite,
        "elapsed_seconds": time.monotonic() - started,
        "rss_bytes": _process_rss_bytes(),
        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
        "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(0),
        "cuda_total_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
        "worker_exit_code": 0, "completed_at_utc": utc_now()})


def _worker_command(config: Mapping[str, Any], worker: str, lane_id: int) -> list[str]:
    runner = workspace_path(config["paths"]["runner"], must_exist=True)
    config_path = workspace_path(config["paths"]["config"], must_exist=True)
    return [sys.executable, str(runner), "--config", str(config_path),
            "--worker", worker, "--lane-id", str(lane_id)]


def _launch_two_lane_workers(config: Mapping[str, Any], worker: str, roots: Sequence[Path],
                             timeout_seconds: float | None) -> list[float]:
    processes: list[subprocess.Popen[bytes]] = []
    logs: list[Any] = []
    starts: list[float] = []
    try:
        for lane_id, root in enumerate(roots):
            log = (root / ".state/worker.log").open("wb")
            logs.append(log)
            starts.append(time.monotonic())
            processes.append(subprocess.Popen(_worker_command(config, worker, lane_id),
                cwd=WORKSPACE, stdout=log, stderr=subprocess.STDOUT))
        deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
        while True:
            codes = [process.poll() for process in processes]
            if all(code is not None for code in codes):
                break
            if any(code not in (None, 0) for code in codes):
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                break
            if deadline is not None and time.monotonic() > deadline:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                raise ContractError(f"{worker} exceeded coordinator timeout")
            time.sleep(float(config["execution"]["lane_poll_interval_seconds"]))
        codes = [process.wait() for process in processes]
        if codes != [0, 0]:
            tails = []
            for lane_id, root in enumerate(roots):
                path = root / ".state/worker.log"
                content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
                tails.append(f"lane_{lane_id}: {content[-2000:]}")
            raise ContractError(f"{worker} failed with exit codes {codes}: " + " | ".join(tails))
        return [time.monotonic() - started for started in starts]
    finally:
        for log in logs:
            log.close()


def run_parallel_gpu_probe(config: Mapping[str, Any], parent_build: Path) -> dict[str, Any]:
    probe_parent = parent_build / ".state/parallel_probe_lanes"
    roots = [probe_parent / f"lane_{lane_id}" for lane_id in range(2)]
    for root in roots:
        _prepare_lane_root(parent_build, root)
    try:
        _launch_two_lane_workers(config, "parallel-gpu-probe",
            roots, float(config["execution"]["lane_probe_timeout_seconds"]))
    finally:
        # Probe workers parse the same train-only value panel as formal lane workers;
        # their accesses remain part of the canonical firewall audit even on failure.
        _merge_lane_access_events(parent_build, roots)
    lane_results = [json.loads((root / ".state/probe_result.json").read_text(encoding="utf-8"))
                    for root in roots]
    if any(item["worker_exit_code"] != 0 or not item["finite_loss"] for item in lane_results):
        raise ContractError("parallel resource probe did not pass")
    total_memory = int(lane_results[0]["cuda_total_memory_bytes"])
    conservative_reserved_sum = sum(int(item["cuda_peak_reserved_bytes"])
                                    for item in lane_results)
    if conservative_reserved_sum > int(total_memory * 0.90):
        raise ContractError("parallel resource probe exceeds 90% conservative VRAM bound")
    payload = {"schema_version": "21F_PARALLEL_RESOURCE_PROBE_V1", "run_id": RUN_ID,
        "lane_n": 2, "lane_results": lane_results,
        "conservative_cuda_peak_reserved_sum_bytes": conservative_reserved_sum,
        "cuda_total_memory_bytes": total_memory, "vram_headroom_pass": True,
        "status": "pass", "completed_at_utc": utc_now()}
    write_json(parent_build / "training/parallel_resource_probe.json", payload)
    return payload


def run_inner_training_lane(config: Mapping[str, Any], lane_id: int) -> None:
    if lane_id not in (0, 1):
        raise ContractError("inner lane id must be 0 or 1")
    started = time.monotonic()
    build = building_output_root(config)
    configure_determinism()
    if not torch.cuda.is_available():
        raise ContractError("formal 21F training requires CUDA")
    device = torch.device("cuda")
    feature_cache = load_feature_cache(config)
    registry_rows: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    collapse_rows: list[dict[str, Any]] = []
    calibration_frames: list[pd.DataFrame] = []
    prediction_frames: list[pd.DataFrame] = []
    fold_contract = config["inner_folds"][lane_id]
    fit = load_fold_slice(config, fold_contract["fit_id"], worker_role="INNER_TRAIN",
        feature_cache=feature_cache)
    select = load_fold_slice(config, fold_contract["select_id"], worker_role="INNER_TRAIN",
        feature_cache=feature_cache)
    weights_by_seed = {}
    for seed in MODEL_SEEDS:
        weights, calibration = calibrate_shared_weights(config, fit, seed, device)
        weights_by_seed[seed] = weights
        calibration_frames.append(calibration)
    for arm_order, arm_id in enumerate(ARM_IDS):
        seed_scores = {}
        for seed_order, seed in enumerate(MODEL_SEEDS):
            job_order = lane_id * 15 + arm_order * 3 + seed_order + 1
            state, curves, scores, metadata = train_inner_job(config, arm_id, fit,
                select, seed, weights_by_seed[seed], device)
            seed_scores[seed] = scores
            curve_rows.extend(curves)
            path_relative = f"training/inner_checkpoints/{fit.split_id}/{arm_id}/seed_{seed}/state_dict.pt"
            checkpoint_path = build / path_relative
            save_checkpoint(checkpoint_path, state)
            final_phase = "phase_b" if arm_id == "T3_CSZ_TWO_STAGE_LINEAR" else "joint"
            for phase_id, selected in metadata["phase_rows"].items():
                registry_rows.append({"job_order": job_order, "fold_id": fit.split_id,
                    "arm_id": arm_id, "model_seed": seed, "phase_id": phase_id,
                    "fit_row_n": len(fit.frame), "planned_max_epochs": config["training"]["max_epochs"],
                    "executed_epoch_n": max(row["epoch"] for row in curves if row["phase_id"] == phase_id),
                    "selected_epoch": selected["epoch"], "selector_estimator_id": selected["selector_estimator_id"],
                    "phase_selected_semantic_sha256": selected["checkpoint_semantic_sha256"],
                    "checkpoint_path": path_relative if phase_id == final_phase else None,
                    "checkpoint_sha256": file_sha(checkpoint_path) if phase_id == final_phase else None,
                    "checkpoint_semantic_sha256": model_state_semantic_hash(state) if phase_id == final_phase else None,
                    "job_status": "complete", "reason_code": None})
            manifest_entries.append({"job_order": job_order, "fold_id": fit.split_id,
                "arm_id": arm_id, "model_seed": seed, "final_phase_id": final_phase,
                "path": path_relative, "size_bytes": checkpoint_path.stat().st_size,
                "sha256": file_sha(checkpoint_path), "semantic_sha256": model_state_semantic_hash(state),
                "phase_a_semantic_sha256": metadata["phase_a_semantic_sha256"],
                "selected_epoch": metadata["phase_rows"][final_phase]["epoch"],
                "phase_a_selected_epoch": metadata["phase_rows"].get("phase_a", {}).get("epoch")})
            selected_curve = metadata["phase_rows"][final_phase]
            collapse_rows.append({"fold_id": fit.split_id, "arm_id": arm_id,
                "model_seed": seed, "phase_id": final_phase, "epoch": selected_curve["epoch"],
                "module_id": "global", "loss_term": "L_total", "gradient_l2": 0.0,
                "gradient_share": 1.0, "zero_solution_improvement": float(np.var(scores)),
                "latent_std": float(np.std(scores)), "decoder_output_std": float(np.std(scores)),
                "additional_collapse_flag": bool(selected_curve["collapse_flag"]),
                "checkpoint_semantic_sha256": model_state_semantic_hash(state),
                "status": "pass", "reason_code": None})
        prediction_frames.append(prediction_frame(select, arm_id, "Q2_SCORE_MEAN256_REF",
            seed_scores, STAGE_IDS[2]))
    if len(manifest_entries) != 15 or len(registry_rows) != 18:
        raise ContractError("inner lane cardinality drift")
    training = build / "training"
    write_csv(training / "inner_training_run_registry.csv", registry_rows, list(registry_rows[0]))
    write_parquet(training / "inner_epoch_selection_registry.parquet", pd.DataFrame(curve_rows))
    calibration_all = pd.concat(calibration_frames, ignore_index=True)
    if len(calibration_all) != 105:
        raise ContractError("inner lane gradient calibration row formula drift")
    write_parquet(build / "gradient_calibration_audit.parquet", calibration_all)
    write_parquet(build / "gradient_graph_and_collapse_audit.parquet", pd.DataFrame(collapse_rows))
    entries_hash = stable_hash(manifest_entries)
    write_json(training / "inner_checkpoint_manifest.json", {"schema_version": "21F_LANE_CHECKPOINT_MANIFEST_V1",
        "run_id": RUN_ID, "lane_id": lane_id, "checkpoint_entries": manifest_entries, "entry_n": 15,
        "entries_semantic_sha256": entries_hash})
    write_parquet(build / "predictions/inner_selection_prediction_scores.parquet",
        pd.concat(prediction_frames, ignore_index=True))
    write_json(build / ".state/lane_complete.json", {"schema_version": "21F_INNER_LANE_COMPLETE_V1",
        "lane_id": lane_id, "entry_n": 15, "phase_row_n": 18,
        "job_orders": [item["job_order"] for item in manifest_entries],
        "entries_semantic_sha256": entries_hash, "gpu_process_seconds": time.monotonic() - started,
        "completed_at_utc": utc_now()})


def _merge_lane_access_events(parent_build: Path, roots: Sequence[Path]) -> None:
    destination = parent_build / "preflight/value_access_audit.csv"
    base = pd.read_csv(destination, keep_default_na=False).to_dict("records")
    rows = list(base)
    for root in roots:
        rows.extend(pd.read_csv(root / "preflight/value_access_audit.csv",
            keep_default_na=False).to_dict("records"))
    for event_order, row in enumerate(rows, start=1):
        row["event_order"] = event_order
    write_csv(destination, rows, TABULAR_SCHEMAS["value_access"])


def merge_inner_training_lanes(config: Mapping[str, Any], parent_build: Path,
                               roots: Sequence[Path]) -> dict[str, Any]:
    registries, curves, calibrations, collapses, predictions = [], [], [], [], []
    entries: list[dict[str, Any]] = []
    lane_markers = []
    for lane_id, root in enumerate(roots):
        marker = json.loads((root / ".state/lane_complete.json").read_text(encoding="utf-8"))
        if marker["lane_id"] != lane_id or marker["entry_n"] != 15 or marker["phase_row_n"] != 18:
            raise ContractError("lane completion marker drift")
        lane_markers.append(marker)
        registry = pd.read_csv(root / "training/inner_training_run_registry.csv", keep_default_na=False)
        if len(registry) != 18:
            raise ContractError("lane registry cardinality drift")
        registries.append(registry)
        curves.append(pd.read_parquet(root / "training/inner_epoch_selection_registry.parquet"))
        calibrations.append(pd.read_parquet(root / "gradient_calibration_audit.parquet"))
        collapses.append(pd.read_parquet(root / "gradient_graph_and_collapse_audit.parquet"))
        predictions.append(pd.read_parquet(root / "predictions/inner_selection_prediction_scores.parquet"))
        manifest = json.loads((root / "training/inner_checkpoint_manifest.json").read_text(encoding="utf-8"))
        if manifest["entry_n"] != 15:
            raise ContractError("lane manifest cardinality drift")
        for entry in manifest["checkpoint_entries"]:
            source = root / entry["path"]
            if file_sha(source) != entry["sha256"] or source.stat().st_size != entry["size_bytes"]:
                raise ContractError("lane checkpoint byte identity drift")
            destination = parent_build / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            if file_sha(destination) != entry["sha256"]:
                raise ContractError("checkpoint drift during coordinator merge")
            entries.append(entry)
    entries.sort(key=lambda item: int(item["job_order"]))
    if [int(item["job_order"]) for item in entries] != list(range(1, 31)):
        raise ContractError("lane job sets are not an exact disjoint partition of 1..30")
    registry_all = pd.concat(registries, ignore_index=True).sort_values(
        ["job_order", "phase_id"], kind="mergesort").reset_index(drop=True)
    if len(registry_all) != 36 or registry_all["job_order"].nunique() != 30:
        raise ContractError("merged inner registry cardinality drift")
    calibration_all = pd.concat(calibrations, ignore_index=True)
    if len(calibration_all) != 210:
        raise ContractError("merged gradient calibration row formula drift")
    training = parent_build / "training"
    write_csv(training / "inner_training_run_registry.csv", registry_all.to_dict("records"),
        TABULAR_SCHEMAS["inner_training_registry"])
    write_parquet(training / "inner_epoch_selection_registry.parquet",
        pd.concat(curves, ignore_index=True))
    write_parquet(parent_build / "gradient_calibration_audit.parquet", calibration_all)
    write_parquet(parent_build / "gradient_graph_and_collapse_audit.parquet",
        pd.concat(collapses, ignore_index=True))
    write_parquet(parent_build / "predictions/inner_selection_prediction_scores.parquet",
        pd.concat(predictions, ignore_index=True))
    entries_hash = stable_hash(entries)
    write_json(training / "inner_checkpoint_manifest.json", {
        "schema_version": "21F_CHECKPOINT_MANIFEST_V1", "run_id": RUN_ID,
        "checkpoint_entries": entries, "entry_n": 30,
        "entries_semantic_sha256": entries_hash})
    _merge_lane_access_events(parent_build, roots)
    gpu_seconds = sum(float(marker["gpu_process_seconds"]) for marker in lane_markers)
    if gpu_seconds > float(config["resources"]["total_gpu_wall_seconds_cap"]):
        raise ContractError("inner lane GPU-process wall cap exceeded")
    return {"entry_n": 30, "entries_semantic_sha256": entries_hash,
        "lane_gpu_process_seconds": [float(marker["gpu_process_seconds"]) for marker in lane_markers],
        "inner_gpu_process_seconds": gpu_seconds}


def run_inner_training(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    marker = build / ".state/inner_training_complete.json"
    if marker.exists():
        return
    if not (build / ".state/replay_complete.json").exists():
        raise ContractError("exact replay stage must complete before training")
    mark_stage(build, STAGE_IDS[2], "running")
    probe = run_parallel_gpu_probe(config, build)
    lane_parent = build / ".state/inner_lanes"
    roots = [lane_parent / f"lane_{lane_id}" for lane_id in range(2)]
    for root in roots:
        _prepare_lane_root(build, root)
    coordinator_started = time.monotonic()
    _launch_two_lane_workers(config, "inner-training-lane", roots, None)
    merged = merge_inner_training_lanes(config, build, roots)
    write_json(marker, {"schema_version": "21F_INNER_TRAINING_COMPLETE_V2",
        **merged, "lane_n": 2, "partition": "inner_fold_order",
        "coordinator_elapsed_seconds": time.monotonic() - coordinator_started,
        "parallel_probe_status": probe["status"], "completed_at_utc": utc_now()})
    mark_stage(build, STAGE_IDS[2], "complete")
    pass_gates(build, range(15, 21), ["training/inner_checkpoint_manifest.json",
        "training/inner_training_run_registry.csv", "training/parallel_resource_probe.json"])


def validate_upstream_pins(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pin_id, item in config["upstream_pins"].items():
        path = workspace_path(item["path"], must_exist=True)
        observed = file_sha(path)
        status = "pass" if observed == item["sha256"] else "fail"
        rows.append({"pin_id": pin_id, "path": item["path"],
            "expected_sha256": item["sha256"], "observed_sha256": observed,
            "status": status, "reason_code": "NA" if status == "pass" else "hash_mismatch"})
    if any(row["status"] != "pass" for row in rows):
        raise ContractError("upstream pin drift")
    return rows


def validate_upstream_terminals(config: Mapping[str, Any]) -> None:
    decision_21d = pd.read_csv(workspace_path(config["upstream_pins"]["21d_decision"]["path"], must_exist=True))
    decision_21e = pd.read_csv(workspace_path(config["upstream_pins"]["21e_decision"]["path"], must_exist=True))
    if decision_21d.loc[0, "terminal_state"] != "21D_gap_mechanisms_mixed_no_repair_candidate":
        raise ContractError("21D terminal state drift")
    if decision_21e.loc[0, "terminal_state"] != "21E_multiple_implementation_ambiguities_material":
        raise ContractError("21E terminal state drift")
    if bool(decision_21d.loc[0, "next_requirement_execution_authorized"]) or bool(decision_21e.loc[0, "next_requirement_execution_authorized"]):
        raise ContractError("upstream next-execution boundary drift")


def validate_hash_manifest_closure(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for phase in ("21b", "21c", "21d", "21e"):
        item = config["upstream_pins"][f"{phase}_output_hashes"]
        hashes_path = workspace_path(item["path"], must_exist=True)
        payload = json.loads(hashes_path.read_text(encoding="utf-8"))
        root = hashes_path.parent
        if phase == "21b":
            entries = [{"path": path, "sha256": sha} for path, sha in payload["artifacts"].items()]
        elif phase == "21c":
            entries = payload["files"]
        else:
            entries = payload["entries"]
        for entry in entries:
            path = root / entry["path"]
            observed = file_sha(path) if path.exists() else None
            status = "pass" if observed == entry["sha256"] else "fail"
            rows.append({"phase_id": phase.upper(), "path": str(path.relative_to(WORKSPACE)),
                "expected_sha256": entry["sha256"], "observed_sha256": observed,
                "status": status, "reason_code": "NA" if status == "pass" else "hash_mismatch"})
    if any(row["status"] != "pass" for row in rows):
        raise ContractError("upstream output-hashes closure failed")
    return rows


def hash_only_integrity_worker(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    pin_rows = validate_upstream_pins(config)
    closure_rows = validate_hash_manifest_closure(config)
    write_csv(build / "preflight/upstream_pin_audit.csv", pin_rows, list(pin_rows[0]))
    write_csv(build / "preflight/upstream_hash_closure_audit.csv", closure_rows, list(closure_rows[0]))
    write_json(build / "preflight/hash_only_integrity_exit_record.json", {
        "schema_version": "21F_HASH_ONLY_EXIT_V1", "worker_role": "HASH_ONLY_INTEGRITY",
        "process_id": str(os.getpid()), "pin_n": len(pin_rows), "closure_entry_n": len(closure_rows),
        "value_parsed": False, "worker_exit_code": 0, "completed_at_utc": utc_now()})


def _archive_failed_attempt(config: Mapping[str, Any], build: Path) -> None:
    failure = build / "failure/failure_record.json"
    if not build.exists():
        return
    if not failure.exists():
        raise ContractError("existing building root is not a registered technical failure")
    payload = json.loads(failure.read_text(encoding="utf-8"))
    access = build / "preflight/value_access_audit.csv"
    historical = build / "historical_design_holdout_access_audit.csv"
    if payload["value_access_audit_sha256"] != file_sha(access) or payload["historical_holdout_access_audit_sha256"] != file_sha(historical):
        raise ContractError("failure snapshot hash drift")
    history = workspace_path(config["paths"]["failure_history_root"])
    history.mkdir(parents=True, exist_ok=True)
    attempts = sorted(path for path in history.glob("attempt_*") if path.is_dir())
    target = history / f"attempt_{len(attempts) + 1}"
    target.mkdir()
    shutil.copytree(build / "failure", target / "failure")
    for name in ("stage_status_registry.csv", "gate_evidence_21f.csv",
                 "historical_design_holdout_access_audit.csv"):
        shutil.copy2(build / name, target / name)
    (target / "preflight").mkdir()
    shutil.copy2(access, target / "preflight/value_access_audit.csv")
    shutil.rmtree(build)


def metadata_splitter_worker(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    pre, design, registry = build_metadata_indices(config)
    write_parquet(build / "preflight/pre_2023_row_index.parquet", pre)
    write_parquet(build / "preflight/design_2023_row_index.parquet", design)
    write_csv(build / "inner_fold_registry.csv", registry.to_dict("records"), list(registry.columns))
    record = {"schema_version": "21F_METADATA_SPLITTER_EXIT_V1",
        "worker_role": "METADATA_SPLITTER", "process_id": str(os.getpid()),
        "source_index_sha256": config["upstream_pins"]["sequence_index"]["sha256"],
        "pre_2023_index_sha256": file_sha(build / "preflight/pre_2023_row_index.parquet"),
        "design_2023_index_sha256": file_sha(build / "preflight/design_2023_row_index.parquet"),
        "projected_columns": ["fold", "decision_date", "instrument", "fold_panel_row_idx",
            "x_cache_row_indices", "source_dates", "row_key_hash"],
        "return_panel_open_attempt_n": 0, "label_value_materialized_n": 0,
        "score_value_materialized_n": 0, "worker_exit_code": 0, "completed_at_utc": utc_now()}
    write_json(build / "preflight/metadata_splitter_exit_record.json", record)
    row = {"event_order": 1, "worker_role": "METADATA_SPLITTER", "process_id": str(os.getpid()),
        "stage_id": STAGE_IDS[0], "path": config["inputs"]["sequence_index"],
        "access_mode": "metadata_projection", "metadata_only": True, "value_parsed": False,
        "label_value_materialized_n": 0, "score_value_materialized_n": 0,
        "event_time_utc": utc_now(), "status": "pass", "reason_code": "NA"}
    write_csv(build / "preflight/value_access_audit.csv", [row], list(row))


def preflight_purge_worker(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    pre = pd.read_parquet(build / "preflight/pre_2023_row_index.parquet")
    validate_outcome_date_purge(config, pre)
    validate_upstream_terminals(config)
    append_access_event(build, worker_role="SELECTION_COORDINATOR", stage_id=STAGE_IDS[0],
        path=config["inputs"]["label_audit"], access_mode="metadata_projection",
        metadata_only=True, value_parsed=False)
    write_json(build / "preflight/preflight_purge_exit_record.json", {
        "schema_version": "21F_PREFLIGHT_PURGE_EXIT_V1", "worker_role": "SELECTION_COORDINATOR",
        "process_id": str(os.getpid()), "outcome_date_purge_pass": True,
        "upstream_terminal_state_pass": True, "label_value_materialized_n": 0,
        "worker_exit_code": 0, "completed_at_utc": utc_now()})


def run_preflight(config: Mapping[str, Any]) -> None:
    authorization = validate_authorization(config)
    if authorization.status != "pass":
        raise ContractError("valid human authorization required: " + ",".join(authorization.errors))
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    build = building_output_root(config)
    if canonical.exists():
        raise ContractError("canonical output already exists")
    _archive_failed_attempt(config, build)
    if shutil.disk_usage(canonical.parent).free < int(config["resources"]["minimum_free_disk_before_run"]):
        raise ContractError("insufficient free disk before formal run")
    build.mkdir(parents=True)
    (build / ".state").mkdir()
    initialize_access_registries(build)
    mark_stage(build, STAGE_IDS[0], "running")
    runner = workspace_path(config["paths"]["runner"], must_exist=True)
    subprocess.run([sys.executable, str(runner), "--config", str(DEFAULT_CONFIG),
        "--worker", "hash-only-integrity"], cwd=WORKSPACE, check=True)
    hash_exit = json.loads((build / "preflight/hash_only_integrity_exit_record.json").read_text())
    if hash_exit["worker_exit_code"] != 0 or hash_exit["value_parsed"] is not False:
        raise ContractError("hash-only worker contract failed")
    subprocess.run([sys.executable, str(runner), "--config", str(DEFAULT_CONFIG),
        "--worker", "metadata-splitter"], cwd=WORKSPACE, check=True)
    access = pd.read_csv(build / "preflight/value_access_audit.csv")
    access_rows = access.to_dict("records")
    hash_rows = (pd.read_csv(build / "preflight/upstream_pin_audit.csv").to_dict("records") +
                 pd.read_csv(build / "preflight/upstream_hash_closure_audit.csv").to_dict("records"))
    for order, row in enumerate(hash_rows, start=2):
        access_rows.append({"event_order": order, "worker_role": "HASH_ONLY_INTEGRITY",
            "process_id": hash_exit["process_id"], "stage_id": STAGE_IDS[0], "path": row["path"],
            "access_mode": "hash_only", "metadata_only": False, "value_parsed": False,
            "label_value_materialized_n": 0, "score_value_materialized_n": 0,
            "event_time_utc": hash_exit["completed_at_utc"], "status": row["status"],
            "reason_code": row["reason_code"]})
    write_csv(build / "preflight/value_access_audit.csv", access_rows, TABULAR_SCHEMAS["value_access"])
    subprocess.run([sys.executable, str(runner), "--config", str(DEFAULT_CONFIG),
        "--worker", "preflight-purge"], cwd=WORKSPACE, check=True)
    purge_exit = json.loads((build / "preflight/preflight_purge_exit_record.json").read_text())
    if purge_exit["worker_exit_code"] != 0 or not purge_exit["outcome_date_purge_pass"]:
        raise ContractError("preflight purge worker failed")
    for path, frame in (("hypothesis_registry.csv", hypothesis_registry()),
                        ("training_semantics_arm_registry.csv", training_arm_registry(config)),
                        ("predictor_estimator_registry.csv", predictor_registry(config)),
                        ("contrast_registry.csv", contrast_registry())):
        write_csv(build / path, frame.to_dict("records"), list(frame.columns))
    schema = schema_registry_contract()
    write_json(build / "schema_registry_21f.json", schema)
    profile = artifact_profile_contract()
    profiles = [{"profile_id": PROFILE_ID, "terminal_state": terminal,
        "required_paths_json": json.dumps(profile["required_paths"], separators=(",", ":")),
        "forbidden_paths_json": json.dumps(profile["forbidden_tokens"], separators=(",", ":")),
        "exact_checkpoint_paths_json": json.dumps(profile["exact_checkpoint_paths"], separators=(",", ":")),
        "schema_registry_contract_sha256": schema["contract_sha256"], "status": "pre_registered"}
        for terminal in profile["terminal_states"]]
    write_csv(build / "artifact_profile_registry.csv", profiles, list(profiles[0]))
    write_json(build / ".state/preflight_complete.json", {"schema_version": "21F_PREFLIGHT_COMPLETE_V1",
        "authorization_sha256": authorization.sha256, "completed_at_utc": utc_now()})
    mark_stage(build, STAGE_IDS[0], "complete")
    pass_gates(build, range(1, 9), ["preflight/upstream_pin_audit.csv",
        "preflight/metadata_splitter_exit_record.json", "inner_fold_registry.csv"])


def _semantic_frame_hash(frame: pd.DataFrame, columns: Sequence[str]) -> str:
    payload = frame.loc[:, columns].copy()
    for column in payload.columns:
        if np.issubdtype(payload[column].dtype, np.floating):
            payload[column] = payload[column].map(lambda value: np.float32(value).tobytes().hex())
        else:
            payload[column] = payload[column].astype(str)
    return stable_hash(payload.to_dict("records"))


def _draw_values(path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    table = pq.read_table(path, columns=["decision_date", "instrument", "row_key", "draw_scores"])
    matrix = table.column("draw_scores").combine_chunks().values.to_numpy().reshape(len(table), 256)
    return table.select(["decision_date", "instrument", "row_key"]).to_pandas(), np.asarray(matrix, dtype=np.float32)


def _canonical_replay_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize pinned 21C/21D identity naming and ordering before bitwise replay."""
    result = frame.copy()
    if "row_key" not in result and "row_key_hash" in result:
        result = result.rename(columns={"row_key_hash": "row_key"})
    columns = ["decision_date", "instrument", "row_key", "model_seed", "score"]
    missing = set(columns).difference(result.columns)
    if missing:
        raise ContractError(f"exact replay identity columns missing: {sorted(missing)}")
    result = result.loc[:, columns]
    result["model_seed"] = pd.to_numeric(result["model_seed"], errors="raise").astype("int64")
    return result.sort_values(columns[:-1], kind="mergesort").reset_index(drop=True)


def _legacy_21c_prefix8_mean(draws: np.ndarray, device: str = "cuda") -> np.ndarray:
    """Reproduce 21C's batch-local torch.stack(...).mean(dim=0) reduction."""
    values = np.asarray(draws, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] < 8:
        raise ContractError("21C replay draw matrix must be [N,>=8]")
    chunks = []
    for start in range(0, len(values), 1024):
        batch = values[start:start + 1024, :8]
        stacked = torch.stack([
            torch.as_tensor(np.array(batch[:, draw], copy=True), device=device)
            for draw in range(8)
        ], dim=0)
        chunks.append(stacked.mean(dim=0).cpu().numpy())
    return np.concatenate(chunks).astype(np.float32, copy=False)


def _legacy_21d_prefix_mean(draws: np.ndarray, prefix: int) -> np.ndarray:
    """Reproduce 21D prefix_means: float32 input, float64 mean, float32 output."""
    values = np.asarray(draws, dtype=np.float32)
    if values.ndim != 2 or prefix not in {8, 32, 64, 128, 256} or values.shape[1] < prefix:
        raise ContractError("21D replay prefix contract invalid")
    return values[:, :prefix].astype(np.float64).mean(axis=1).astype(np.float32)


def exact_replay_worker(config: Mapping[str, Any]) -> None:
    started = time.monotonic()
    if not torch.cuda.is_available():
        raise ContractError("exact replay requires CUDA")
    build = building_output_root(config)
    rows = []
    config_21e = PINNED_21E.load_config()
    d0_root = workspace_path(config_21e["inputs"]["21d_d0_draw_root"], must_exist=True)
    base_21d = workspace_path(config["upstream_pins"]["21d_manifest"]["path"], must_exist=True).parent
    for replay_order, fold in enumerate(("validation_early", "validation_late"), start=1):
        source_21c = workspace_path(config["inputs"]["21c_early_scores" if fold == "validation_early" else "21c_late_scores"], must_exist=True)
        expected = pd.read_parquet(source_21c)
        observed_parts = []
        for seed in MODEL_SEEDS:
            keys, draws = _draw_values(d0_root / fold / f"seed_{seed}.parquet")
            score = _legacy_21c_prefix8_mean(draws)
            part = keys.copy()
            part["model_seed"] = seed
            part["score"] = score
            observed_parts.append(part)
        observed = pd.concat(observed_parts, ignore_index=True)
        expected_seed = _canonical_replay_frame(expected.loc[expected["model_seed"].isin(MODEL_SEEDS)])
        observed = _canonical_replay_frame(observed)
        equal = (expected_seed[["decision_date", "instrument", "row_key", "model_seed"]].astype(str).equals(
            observed[["decision_date", "instrument", "row_key", "model_seed"]].astype(str)) and
            np.array_equal(expected_seed["score"].to_numpy(dtype=np.float32), observed["score"].to_numpy(dtype=np.float32)))
        rows.append({"replay_order": replay_order, "replay_id": f"Q0_{fold}",
            "source_path": str(source_21c.relative_to(WORKSPACE)), "source_sha256": file_sha(source_21c),
            "comparison_role": "21c_q0_bitwise", "expected_semantic_sha256": _semantic_frame_hash(expected_seed, expected_seed.columns),
            "observed_semantic_sha256": _semantic_frame_hash(observed, observed.columns),
            "max_abs_error": float(np.max(np.abs(expected_seed["score"].to_numpy() - observed["score"].to_numpy()))),
            "bitwise_equal": equal, "status": "pass" if equal else "fail", "reason_code": "NA" if equal else "hash_mismatch"})
    prediction_paths = {"validation_early": base_21d / "predictions/validation_early_prediction_scores.parquet",
                        "validation_late": base_21d / "predictions/validation_late_prediction_scores.parquet"}
    d4_root = workspace_path(config["inputs"]["21d_d4_draw_root"], must_exist=True)
    for replay_order, fold in enumerate(("validation_early", "validation_late"), start=3):
        expected_all = pd.read_parquet(prediction_paths[fold])
        expected = _canonical_replay_frame(expected_all.loc[expected_all["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1") &
            expected_all["score_variant"].eq("prefix64") & expected_all["model_seed"].isin(MODEL_SEEDS),
            ["decision_date", "instrument", "row_key", "model_seed", "score"]])
        parts = []
        for seed in MODEL_SEEDS:
            keys, draws = _draw_values(d4_root / fold / f"seed_{seed}.parquet")
            score = _legacy_21d_prefix_mean(draws, 64)
            part = keys.copy()
            part["model_seed"] = seed
            part["score"] = score
            parts.append(part)
        observed = _canonical_replay_frame(pd.concat(parts, ignore_index=True))
        equal = np.array_equal(expected["score"].to_numpy(dtype=np.float32), observed["score"].to_numpy(dtype=np.float32))
        rows.append({"replay_order": replay_order, "replay_id": f"D4_{fold}",
            "source_path": str(prediction_paths[fold].relative_to(WORKSPACE)), "source_sha256": file_sha(prediction_paths[fold]),
            "comparison_role": "21d_d4_prefix64_bitwise", "expected_semantic_sha256": _semantic_frame_hash(expected, expected.columns),
            "observed_semantic_sha256": _semantic_frame_hash(observed, observed.columns),
            "max_abs_error": float(np.max(np.abs(expected["score"].to_numpy() - observed["score"].to_numpy()))),
            "bitwise_equal": equal, "status": "pass" if equal else "fail", "reason_code": "NA" if equal else "hash_mismatch"})
    for replay_order, pin_id in enumerate(("21e_decision", "21e_contrasts", "21e_gradient"), start=5):
        item = config["upstream_pins"][pin_id]
        path = workspace_path(item["path"], must_exist=True)
        equal = file_sha(path) == item["sha256"]
        rows.append({"replay_order": replay_order, "replay_id": pin_id,
            "source_path": item["path"], "source_sha256": file_sha(path),
            "comparison_role": "21e_registered_sha256", "expected_semantic_sha256": item["sha256"],
            "observed_semantic_sha256": file_sha(path), "max_abs_error": 0.0,
            "bitwise_equal": equal, "status": "pass" if equal else "fail", "reason_code": "NA" if equal else "hash_mismatch"})
    if len(rows) != 7 or any(row["status"] != "pass" for row in rows):
        raise ContractError("exact replay failed")
    write_csv(build / "exact_replay_audit.csv", rows, list(rows[0]))
    for row in rows:
        value_parsed = row["comparison_role"] != "21e_registered_sha256"
        append_access_event(build, worker_role="EXACT_REPLAY", stage_id=STAGE_IDS[1],
            path=row["source_path"], access_mode="value_parse" if value_parsed else "hash_only",
            metadata_only=False, value_parsed=value_parsed,
            score_value_materialized_n=(3 * (config["retained_folds"]["validation_early"]["row_n"]
                if "validation_early" in row["replay_id"] else config["retained_folds"]["validation_late"]["row_n"]))
                if value_parsed else 0)
    pre = pd.read_parquet(build / "preflight/pre_2023_row_index.parquet")
    split_ids = [item for contract in config["inner_folds"]
        for item in ((contract["fit_id"],) if contract["select_id"] is None
                     else (contract["fit_id"], contract["select_id"]))]
    transform = return_transform_audit_for_index(config, pre, split_ids)
    if len(transform) != (475 + 186 + 661 + 180 + 842) * 11:
        raise ContractError("pre-2023 return-transform row formula drift")
    write_parquet(build / "return_transform_audit.parquet", transform)
    for split_id in split_ids:
        append_access_event(build, worker_role="EXACT_REPLAY", stage_id=STAGE_IDS[1],
            path=config["upstream_pins"]["train_value_panel"]["path"], access_mode="value_parse",
            metadata_only=False, value_parsed=True,
            label_value_materialized_n=int((pre["fold_id"] == split_id).sum()))
    record_nontraining_inference_seconds(config, STAGE_IDS[1], time.monotonic() - started)


def run_exact_replay(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    marker = build / ".state/replay_complete.json"
    if marker.exists():
        return
    if not (build / ".state/preflight_complete.json").exists():
        raise ContractError("preflight must complete before replay")
    mark_stage(build, STAGE_IDS[1], "running")
    runner = workspace_path(config["paths"]["runner"], must_exist=True)
    subprocess.run([sys.executable, str(runner), "--config", str(DEFAULT_CONFIG),
        "--worker", "exact-replay"], cwd=WORKSPACE, check=True)
    audit = pd.read_csv(build / "exact_replay_audit.csv")
    allowed = audit[["replay_id", "status", "source_sha256", "observed_semantic_sha256"]]
    if len(allowed) != 7 or not allowed["status"].eq("pass").all():
        raise ContractError("replay coordinator received failure")
    write_json(marker, {"schema_version": "21F_REPLAY_COMPLETE_V1",
        "replay_ipc_semantic_sha256": stable_hash(allowed.to_dict("records")),
        "completed_at_utc": utc_now()})
    mark_stage(build, STAGE_IDS[1], "complete")
    pass_gates(build, range(9, 15), ["exact_replay_audit.csv"])


@torch.no_grad()
def score_fold_draw_contract(model: nn.Module, fold: FoldSlice, arm_id: str,
                             model_seed: int, *, draw_n: int, antithetic: bool,
                             batch_size: int, device: torch.device) -> np.ndarray:
    y_source, _, _, _ = model_panel_for_arm(fold, arm_id)
    result = np.empty(len(fold.frame), dtype=np.float32)
    model.eval()
    for start in range(0, len(result), batch_size):
        stop = min(start + batch_size, len(result))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(fold.x_source[start:stop], dtype=torch.float32, device=device)
        keys = fold.frame["row_key_hash"].iloc[start:stop].astype(str).tolist()
        result[start:stop] = stochastic_scores_batch(model, y, x, keys, model_seed,
            draw_n=draw_n, antithetic=antithetic).cpu().numpy()
    return result


@torch.no_grad()
def score_fold_prefix_contract(model: nn.Module, fold: FoldSlice, arm_id: str,
                               model_seed: int, *, prefixes: Sequence[int],
                               antithetic: bool, batch_size: int,
                               device: torch.device) -> dict[int, np.ndarray]:
    targets = tuple(sorted(set(int(value) for value in prefixes)))
    y_source, _, _, _ = model_panel_for_arm(fold, arm_id)
    results = {prefix: np.empty(len(fold.frame), dtype=np.float32) for prefix in targets}
    model.eval()
    for start in range(0, len(fold.frame), batch_size):
        stop = min(start + batch_size, len(fold.frame))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(fold.x_source[start:stop], dtype=torch.float32, device=device)
        keys = fold.frame["row_key_hash"].iloc[start:stop].astype(str).tolist()
        observed = stochastic_prefix_scores_batch(model, y, x, keys, model_seed,
            prefixes=targets, antithetic=antithetic)
        for prefix in targets:
            results[prefix][start:stop] = observed[prefix].cpu().numpy()
    return results


def _score_frame(fold: FoldSlice, score: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"decision_date": fold.frame["decision_date"].astype(str),
        "instrument": fold.frame["instrument"].astype(str), "score": score,
        "label": fold.raw_panel[:, 10]})


def convergence_row(config: Mapping[str, Any], model: nn.Module, fold: FoldSlice,
                    arm_id: str, estimator_id: str, model_seed: int,
                    device: torch.device, *,
                    draw_cache: dict[tuple[str, str, int, bool], dict[int, np.ndarray]] | None = None,
                    ) -> tuple[dict[str, Any], np.ndarray]:
    batch = 1024
    if estimator_id in {"Q1_SCORE_MEAN64", "Q2_SCORE_MEAN256_REF",
                        "Q3_ANTITHETIC_SCORE_MEAN64"}:
        antithetic = estimator_id == "Q3_ANTITHETIC_SCORE_MEAN64"
        cache_key = (fold.split_id, arm_id, model_seed, antithetic)
        cached = None if draw_cache is None else draw_cache.get(cache_key)
        if cached is None:
            prefixes = (64, 256) if antithetic else (64, 128, 256)
            cached = score_fold_prefix_contract(model, fold, arm_id, model_seed,
                prefixes=prefixes, antithetic=antithetic, batch_size=batch, device=device)
            if draw_cache is not None:
                draw_cache[cache_key] = cached
        if estimator_id == "Q1_SCORE_MEAN64":
            left, comparison_id = cached[64], "ordinary64_vs_ordinary256"
        elif estimator_id == "Q2_SCORE_MEAN256_REF":
            left, comparison_id = cached[128], "ordinary128_vs_ordinary256"
        else:
            left, comparison_id = cached[64], "antithetic32pair_vs_128pair"
        reference = cached[256]
    elif estimator_id == "Q4_DDIM_ETA0_SCORE":
        left = score_fold(model, estimator_id, fold, arm_id, model_seed, batch_size=1024, device=device)
        repeated = score_fold(model, estimator_id, fold, arm_id, model_seed, batch_size=1024, device=device)
        reference = score_fold(model, estimator_id, fold, arm_id, model_seed, batch_size=256, device=device)
        left_frame, ref_frame = _score_frame(fold, left), _score_frame(fold, reference)
        median_rho = daily_score_spearman(left_frame, ref_frame)
        max_error = float(np.max(np.abs(left - reference)))
        passed = (np.array_equal(left, repeated) and max_error <= 1e-6 and median_rho >= 0.999999
                  and np.isfinite(left).all() and np.isfinite(reference).all())
        return {"fold_id": fold.split_id, "arm_id": arm_id, "estimator_id": estimator_id,
            "model_seed": model_seed, "comparison_id": "ddim_repeat_and_batch_invariance",
            "paired_day_n": fold.frame["decision_date"].nunique(), "median_daily_spearman": median_rho,
            "median_daily_top30_overlap": daily_top30_overlap(left_frame, ref_frame),
            "mean_daily_rankic_left": mean_daily_rankic(left, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0],
            "mean_daily_rankic_reference": mean_daily_rankic(reference, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0],
            "rankic_abs_delta": abs(mean_daily_rankic(left, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0] - mean_daily_rankic(reference, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]),
            "repeated_run_bitwise_equal": np.array_equal(left, repeated),
            "cross_batch_max_abs_error": max_error, "coverage_pass": True,
            "convergence_pass": passed, "reason_code": None if passed else "convergence_fail"}, left
    else:
        raise ContractError(f"not a candidate estimator: {estimator_id}")
    left_frame, ref_frame = _score_frame(fold, left), _score_frame(fold, reference)
    rho = daily_score_spearman(left_frame, ref_frame)
    overlap = daily_top30_overlap(left_frame, ref_frame)
    rankic_left = mean_daily_rankic(left, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]
    rankic_reference = mean_daily_rankic(reference, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]
    delta = abs(rankic_left - rankic_reference)
    materiality = config["materiality"]
    passed = (rho >= materiality["convergence_spearman_min"] and
              overlap >= materiality["convergence_top30_overlap_min"] and
              delta <= materiality["convergence_rankic_abs_delta_max"])
    selected_scores = reference if estimator_id == "Q2_SCORE_MEAN256_REF" else left
    return {"fold_id": fold.split_id, "arm_id": arm_id, "estimator_id": estimator_id,
        "model_seed": model_seed, "comparison_id": comparison_id,
        "paired_day_n": fold.frame["decision_date"].nunique(), "median_daily_spearman": rho,
        "median_daily_top30_overlap": overlap, "mean_daily_rankic_left": rankic_left,
        "mean_daily_rankic_reference": rankic_reference, "rankic_abs_delta": delta,
        "repeated_run_bitwise_equal": False, "cross_batch_max_abs_error": 0.0,
        "coverage_pass": True, "convergence_pass": passed,
        "reason_code": None if passed else "convergence_fail"}, selected_scores


def _load_inner_model(build: Path, fold_id: str, arm_id: str, seed: int,
                      device: torch.device) -> nn.Module:
    path = build / f"training/inner_checkpoints/{fold_id}/{arm_id}/seed_{seed}/state_dict.pt"
    model = build_model(arm_id, seed)
    state = torch.load(path, map_location="cpu", weights_only=True)
    append_access_event(build, worker_role="SELECTION_COORDINATOR", stage_id=STAGE_IDS[3],
        path=path.relative_to(build).as_posix(), access_mode="checkpoint_read",
        metadata_only=False, value_parsed=True)
    model.load_state_dict(state, strict=True)
    return model.to(device)


def _cross_seed_metrics(fold: FoldSlice, seed_scores: Mapping[int, np.ndarray]) -> tuple[float, float, float]:
    rhos, overlaps = [], []
    for index, left_seed in enumerate(MODEL_SEEDS):
        for right_seed in MODEL_SEEDS[index + 1:]:
            left, right = _score_frame(fold, seed_scores[left_seed]), _score_frame(fold, seed_scores[right_seed])
            rhos.append(daily_score_spearman(left, right))
            overlaps.append(daily_top30_overlap(left, right))
    ensemble = np.stack([seed_scores[seed].astype(np.float64) for seed in MODEL_SEEDS]).mean(axis=0)
    return float(np.mean(rhos)), float(np.mean(overlaps)), adjacent_turnover(_score_frame(fold, ensemble))


def _estimator_selection_key(readouts: Mapping[str, Mapping[str, Any]], estimator_order: int) -> tuple[Any, ...]:
    return (min(readouts["I0"]["rankic"], readouts["I1"]["rankic"]),
        min(readouts["I0"]["rho"], readouts["I1"]["rho"]),
        min(readouts["I0"]["overlap"], readouts["I1"]["overlap"]),
        -readouts["compute"], -estimator_order)


def _arm_selection_key(readouts: Mapping[str, Mapping[str, float]], arm_order: int) -> tuple[Any, ...]:
    return (min(readouts["I0"]["rankic"], readouts["I1"]["rankic"]),
        min(readouts["I0"]["rho"], readouts["I1"]["rho"]),
        min(readouts["I0"]["overlap"], readouts["I1"]["overlap"]),
        -max(readouts["I0"]["turnover"], readouts["I1"]["turnover"]), -arm_order)


def lower_median(values: Sequence[int]) -> int:
    ordered = sorted(int(value) for value in values)
    if len(ordered) != 6:
        raise ContractError("refit epoch rule requires six inner epochs")
    return ordered[2]


def run_selection_and_refit(config: Mapping[str, Any]) -> None:
    started = time.monotonic()
    build = building_output_root(config)
    marker = build / ".state/selection_refit_complete.json"
    if marker.exists():
        return
    if not (build / ".state/inner_training_complete.json").exists():
        raise ContractError("inner training must complete before selection")
    mark_stage(build, STAGE_IDS[3], "running")
    device = torch.device("cuda")
    feature_cache = load_feature_cache(config)
    folds = {
        "I0": load_fold_slice(config, "I0_SELECT_2021", worker_role="SELECTION_COORDINATOR",
            feature_cache=feature_cache),
        "I1": load_fold_slice(config, "I1_SELECT_2022", worker_role="SELECTION_COORDINATOR",
            feature_cache=feature_cache),
    }
    convergence_rows: list[dict[str, Any]] = []
    draw_cache: dict[tuple[str, str, int, bool], dict[int, np.ndarray]] = {}
    estimator_readouts: dict[str, dict[str, Any]] = {}
    candidate_ids = ESTIMATOR_IDS[1:5]
    for estimator_order, estimator_id in enumerate(candidate_ids, start=1):
        fold_readouts = {}
        all_pass = True
        for short, fold in folds.items():
            seed_scores = {}
            for seed in MODEL_SEEDS:
                model = _load_inner_model(build, "I0_FIT_2018_2020_PURGED" if short == "I0" else "I1_FIT_2018_2021_PURGED",
                    "T1_CSZ_COUPLED_LINEAR", seed, device)
                row, score = convergence_row(config, model, fold, "T1_CSZ_COUPLED_LINEAR",
                    estimator_id, seed, device, draw_cache=draw_cache)
                convergence_rows.append(row)
                seed_scores[seed] = score
                all_pass &= bool(row["convergence_pass"])
            ensemble = np.stack([seed_scores[seed].astype(np.float64) for seed in MODEL_SEEDS]).mean(axis=0)
            rankic = mean_daily_rankic(ensemble, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]
            rho, overlap, turnover = _cross_seed_metrics(fold, seed_scores)
            fold_readouts[short] = {"rankic": rankic, "rho": rho, "overlap": overlap,
                "turnover": turnover, "seed_scores": seed_scores}
        fold_readouts["compute"] = config["predictor_estimators"][estimator_order]["compute_equivalent"]
        fold_readouts["all_pass"] = all_pass
        estimator_readouts[estimator_id] = fold_readouts
    eligible_estimators = [item for item in candidate_ids if estimator_readouts[item]["all_pass"]]
    if eligible_estimators:
        selected_estimator = max(eligible_estimators, key=lambda item: _estimator_selection_key(
            estimator_readouts[item], ESTIMATOR_IDS.index(item)))
        research_estimator_selected, estimator_status = True, "selected"
    else:
        selected_estimator, research_estimator_selected, estimator_status = "Q2_SCORE_MEAN256_REF", False, "diagnostic_fallback"
    write_json(build / "training/selected_predictor_estimator.json", {
        "schema_version": "21F_SELECTED_ESTIMATOR_V1", "selection_status": estimator_status,
        "research_estimator_selected": research_estimator_selected,
        "selected_estimator_id": selected_estimator if research_estimator_selected else None,
        "diagnostic_fallback_estimator_id": None if research_estimator_selected else selected_estimator,
        "selection_reference_arm_id": "T1_CSZ_COUPLED_LINEAR",
        "lexicographic_key": list(_estimator_selection_key(estimator_readouts[selected_estimator], ESTIMATOR_IDS.index(selected_estimator))),
        "eligible_estimator_ids": eligible_estimators, "registry_sha256": file_sha(build / "predictor_estimator_registry.csv"),
        "created_at_utc": utc_now()})
    arm_readouts = {}
    selected_prediction_frames = []
    for arm_order, arm_id in enumerate(ARM_IDS):
        fold_readouts = {}
        arm_convergence = True
        for short, fold in folds.items():
            seed_scores = {}
            positive_seed_n = 0
            for seed in MODEL_SEEDS:
                fit_id = "I0_FIT_2018_2020_PURGED" if short == "I0" else "I1_FIT_2018_2021_PURGED"
                model = _load_inner_model(build, fit_id, arm_id, seed, device)
                row, score = convergence_row(config, model, fold, arm_id, selected_estimator,
                    seed, device, draw_cache=draw_cache)
                if arm_id != "T1_CSZ_COUPLED_LINEAR" or selected_estimator not in candidate_ids:
                    convergence_rows.append(row)
                arm_convergence &= bool(row["convergence_pass"])
                seed_scores[seed] = score
                positive_seed_n += mean_daily_rankic(score, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0] > 0
            ensemble = np.stack([seed_scores[seed].astype(np.float64) for seed in MODEL_SEEDS]).mean(axis=0)
            rankic = mean_daily_rankic(ensemble, fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]
            rho, overlap, turnover = _cross_seed_metrics(fold, seed_scores)
            fold_readouts[short] = {"rankic": rankic, "rho": rho, "overlap": overlap,
                "turnover": turnover, "positive_seed_n": positive_seed_n,
                "quarter_lomo_positive_n": lomo_positive_n(fold, ensemble, "quarter"),
                "ensemble": ensemble, "seed_scores": seed_scores}
            selected_prediction_frames.append(prediction_frame(fold, arm_id, selected_estimator,
                seed_scores, STAGE_IDS[3]))
        collapse = pd.read_parquet(build / "gradient_graph_and_collapse_audit.parquet")
        no_collapse = not collapse.loc[collapse["arm_id"].eq(arm_id), "additional_collapse_flag"].any()
        eligible = arm_convergence and no_collapse and all(
            fold_readouts[key]["rankic"] > 0 and fold_readouts[key]["positive_seed_n"] >= 2 and
            fold_readouts[key]["rho"] >= 0.25 and fold_readouts[key]["overlap"] >= 6 and
            fold_readouts[key]["turnover"] <= 0.80 and
            fold_readouts[key]["quarter_lomo_positive_n"] >= 3 for key in ("I0", "I1"))
        fold_readouts["eligible"] = eligible
        fold_readouts["no_collapse"] = no_collapse
        fold_readouts["arm_convergence"] = arm_convergence
        arm_readouts[arm_id] = fold_readouts
    write_parquet(build / "predictions/inner_selection_prediction_scores.parquet",
        pd.concat(selected_prediction_frames, ignore_index=True))
    inner_predictions = pd.read_parquet(build / "predictions/inner_selection_prediction_scores.parquet")
    inner_daily = _daily_readout(inner_predictions)
    write_csv(build / "daily_rankic_readout.csv", inner_daily.to_dict("records"), list(inner_daily.columns))
    inner_morphology, inner_top30, inner_lomo = _morphology_tables(inner_predictions)
    write_csv(build / "cross_seed_morphology.csv", inner_morphology.to_dict("records"), list(inner_morphology.columns))
    write_csv(build / "top30_overlap_and_turnover.csv", inner_top30.to_dict("records"), list(inner_top30.columns))
    write_csv(build / "monthly_quarter_lomo_stability.csv", inner_lomo.to_dict("records"), list(inner_lomo.columns))
    contrast_pairs = ((1, "C01", ARM_IDS[1], ARM_IDS[0]), (2, "C02", ARM_IDS[2], ARM_IDS[1]),
                      (3, "C03", ARM_IDS[3], ARM_IDS[2]), (4, "C04", ARM_IDS[4], ARM_IDS[2]))
    inner_contrasts = []
    for family_order, (short, fold) in enumerate(folds.items(), start=1):
        fold_rows = []
        for contrast_order, contrast_id, left_arm, right_arm in contrast_pairs:
            left = arm_readouts[left_arm][short]
            right = arm_readouts[right_arm][short]
            _, left_daily_table = mean_daily_rankic(left["ensemble"], fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))
            _, right_daily_table = mean_daily_rankic(right["ensemble"], fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))
            delta = left_daily_table["rankic"].to_numpy() - right_daily_table["rankic"].to_numpy()
            ensemble_delta = float(np.mean(delta))
            seed_deltas = [mean_daily_rankic(left["seed_scores"][seed], fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0] -
                mean_daily_rankic(right["seed_scores"][seed], fold.raw_panel[:, 10], fold.frame["decision_date"].astype(str))[0]
                for seed in MODEL_SEEDS]
            rho_delta = left["rho"] - right["rho"]
            overlap_delta = left["overlap"] - right["overlap"]
            turnover_delta = left["turnover"] - right["turnover"]
            morphology_nonworse = rho_delta >= 0 and overlap_delta >= 0 and turnover_delta <= 0
            if contrast_id == "C01":
                materiality_pass = ensemble_delta >= 0.005 and morphology_nonworse
            elif contrast_id == "C02":
                materiality_pass = ensemble_delta >= 0.003 and sum(
                    np.sign(value) == np.sign(ensemble_delta) and value != 0 for value in seed_deltas) >= 2 and morphology_nonworse
            elif contrast_id == "C03":
                materiality_pass = (ensemble_delta >= 0.003 and rho_delta >= 0 and
                    overlap_delta >= 0 and arm_readouts[left_arm]["no_collapse"])
            else:
                materiality_pass = (abs(ensemble_delta) >= 0.005 and sum(
                    np.sign(value) == np.sign(ensemble_delta) and value != 0 for value in seed_deltas) >= 2 and
                    (abs(rho_delta) >= 0.05 or abs(overlap_delta) >= 2 or abs(turnover_delta) >= 0.10))
            fold_rows.append({"contrast_order": contrast_order, "family_id": f"F_INNER_202{family_order}",
                "fold_id": fold.split_id, "contrast_id": contrast_id, "left_id": left_arm,
                "right_id": right_arm, "paired_day_n": len(delta),
                "mean_daily_rankic_left": left["rankic"], "mean_daily_rankic_right": right["rankic"],
                "mean_daily_rankic_delta": ensemble_delta,
                "same_direction_seed_n": sum(np.sign(value) == np.sign(ensemble_delta) and value != 0 for value in seed_deltas) if ensemble_delta else 0,
                "p_unadjusted": stationary_bootstrap_p(delta, family_order, contrast_order),
                "p_holm": math.nan, "materiality_pass": materiality_pass,
                "status": "pass", "reason_code": None})
        holm_adjust(fold_rows)
        inner_contrasts.extend(fold_rows)
    c04_rows = [row for row in inner_contrasts if row["contrast_id"] == "C04"]
    if len({int(np.sign(row["mean_daily_rankic_delta"])) for row in c04_rows}) != 1:
        for row in c04_rows:
            row["materiality_pass"] = False
    write_csv(build / "paired_semantic_contrasts.csv", inner_contrasts,
        [column for column in inner_contrasts[0] if column != "contrast_order"])
    eligible_arms = [arm for arm in ARM_IDS if arm_readouts[arm]["eligible"]]
    if eligible_arms:
        selected_arm = max(eligible_arms, key=lambda arm: _arm_selection_key(
            arm_readouts[arm], ARM_IDS.index(arm)))
        research_arm_selected, arm_status = True, "selected"
    else:
        selected_arm, research_arm_selected, arm_status = "T2_CSZ_STOPGRAD_LINEAR", False, "diagnostic_fallback"
    shadow_pool = [arm for arm in ARM_IDS if arm_readouts[arm]["no_collapse"] and all(
        math.isfinite(arm_readouts[arm][key]["rankic"]) for key in ("I0", "I1"))]
    shadow = max(shadow_pool, key=lambda arm: (
        np.mean([arm_readouts[arm]["I0"]["rankic"], arm_readouts[arm]["I1"]["rankic"]]),
        min(arm_readouts[arm]["I0"]["rankic"], arm_readouts[arm]["I1"]["rankic"]),
        -ARM_IDS.index(arm))) if shadow_pool else None
    write_json(build / "training/selected_training_arm.json", {
        "schema_version": "21F_SELECTED_ARM_V1", "selection_status": arm_status,
        "research_arm_selected": research_arm_selected, "selected_arm_id": selected_arm if research_arm_selected else None,
        "diagnostic_fallback_arm_id": None if research_arm_selected else selected_arm,
        "selected_estimator_id": selected_estimator, "lexicographic_key": list(_arm_selection_key(
            arm_readouts[selected_arm], ARM_IDS.index(selected_arm))), "eligible_arm_ids": eligible_arms,
        "registry_sha256": file_sha(build / "training_semantics_arm_registry.csv"), "created_at_utc": utc_now()})
    write_json(build / "training/mean_rankic_only_shadow_selection.json", {
        "schema_version": "21F_SHADOW_SELECTION_V1", "shadow_selection_status": "selected" if shadow else "no_finite_candidate",
        "shadow_arm_id": shadow, "candidate_pool_arm_ids": shadow_pool,
        "lexicographic_key": None if shadow is None else [float(np.mean([arm_readouts[shadow]["I0"]["rankic"], arm_readouts[shadow]["I1"]["rankic"]])),
            min(arm_readouts[shadow]["I0"]["rankic"], arm_readouts[shadow]["I1"]["rankic"]), -ARM_IDS.index(shadow)],
        "noncontrolling": True, "created_at_utc": utc_now()})
    registry = pd.read_csv(build / "training/inner_training_run_registry.csv")
    selected_rows = registry.loc[registry["arm_id"].eq(selected_arm)]
    if selected_arm == "T3_CSZ_TWO_STAGE_LINEAR":
        epoch_contract = {"schema_version": "21F_REFIT_EPOCH_V1", "arm_id": selected_arm,
            "phase_contract": "phase_a_then_phase_b", "inner_epoch_values": {
                "phase_a": selected_rows.loc[selected_rows["phase_id"].eq("phase_a"), "selected_epoch"].astype(int).tolist(),
                "phase_b": selected_rows.loc[selected_rows["phase_id"].eq("phase_b"), "selected_epoch"].astype(int).tolist()},
            "refit_epoch_n": None,
            "refit_phase_a_epoch_n": lower_median(selected_rows.loc[selected_rows["phase_id"].eq("phase_a"), "selected_epoch"]),
            "refit_phase_b_epoch_n": lower_median(selected_rows.loc[selected_rows["phase_id"].eq("phase_b"), "selected_epoch"]),
            "lower_median_rule": "third_order_statistic_of_six", "created_at_utc": utc_now()}
    else:
        values = selected_rows["selected_epoch"].astype(int).tolist()
        epoch_contract = {"schema_version": "21F_REFIT_EPOCH_V1", "arm_id": selected_arm,
            "phase_contract": "joint", "inner_epoch_values": values,
            "refit_epoch_n": lower_median(values), "refit_phase_a_epoch_n": None,
            "refit_phase_b_epoch_n": None, "lower_median_rule": "third_order_statistic_of_six",
            "created_at_utc": utc_now()}
    write_json(build / "training/refit_epoch_contract.json", epoch_contract)
    # Refit weights are the per-seed arithmetic mean of the two fold weights.
    calibration = pd.read_parquet(build / "gradient_calibration_audit.parquet")
    refit_weight_rows = []
    refit_weights = {}
    for seed in MODEL_SEEDS:
        rows = calibration.loc[(calibration["record_type"] == "loss_weight") & (calibration["model_seed"] == seed)]
        means = rows.groupby("loss_term")["loss_weight"].mean().to_dict()
        scale = 3.0 / sum(means.values())
        refit_weights[seed] = {key: value * scale for key, value in means.items()}
        for term, value in refit_weights[seed].items():
            refit_weight_rows.append({"record_type": "refit_weight", "fold_id": "REFIT_2018_2022",
                "model_seed": seed, "temporal_stratum": None, "batch_index": None, "loss_term": term,
                "row_n": None, "decision_date_min": None, "decision_date_max": None,
                "row_key_sha256": None, "gradient_median_l2": None, "loss_weight": value,
                "ordered_parameter_names_sha256": rows["ordered_parameter_names_sha256"].iloc[0],
                "status": "pass", "reason_code": None})
    calibration = pd.concat([calibration, pd.DataFrame(refit_weight_rows)], ignore_index=True)
    if len(calibration) != 219:
        raise ContractError("refit gradient-weight row formula drift")
    write_parquet(build / "gradient_calibration_audit.parquet", calibration)
    write_csv(build / "predictor_draw_convergence.csv", convergence_rows, list(convergence_rows[0]))
    write_json(build / ".state/selection_complete.json", {"schema_version": "21F_SELECTION_COMPLETE_V1",
        "selected_estimator_id": selected_estimator, "selected_arm_id": selected_arm,
        "completed_at_utc": utc_now()})
    record_nontraining_inference_seconds(config, STAGE_IDS[3], time.monotonic() - started)
    run_isolated_worker_stage(config, "refit")


def refit_worker(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/selection_complete.json").exists():
        raise ContractError("selection seal required before refit")
    selected_arm_payload = json.loads((build / "training/selected_training_arm.json").read_text())
    selected_estimator_payload = json.loads((build / "training/selected_predictor_estimator.json").read_text())
    selected_arm = selected_arm_payload["selected_arm_id"] or selected_arm_payload["diagnostic_fallback_arm_id"]
    selected_estimator = selected_estimator_payload["selected_estimator_id"] or selected_estimator_payload["diagnostic_fallback_estimator_id"]
    epoch_contract = json.loads((build / "training/refit_epoch_contract.json").read_text())
    calibration = pd.read_parquet(build / "gradient_calibration_audit.parquet")
    refit_weights = {seed: calibration.loc[(calibration["record_type"] == "refit_weight") &
        (calibration["model_seed"] == seed)].set_index("loss_term")["loss_weight"].to_dict()
        for seed in MODEL_SEEDS}
    if any(set(weights) != {"L_rec", "L_koop", "L_diff"} for weights in refit_weights.values()):
        raise ContractError("refit weights incomplete")
    configure_determinism()
    if not torch.cuda.is_available():
        raise ContractError("formal 21F refit requires CUDA")
    device = torch.device("cuda")
    feature_cache = load_feature_cache(config)
    refit = load_fold_slice(config, "REFIT_2018_2022", worker_role="REFIT",
        feature_cache=feature_cache)
    refit_registry, refit_entries = [], []
    for job_order, seed in enumerate(MODEL_SEEDS, start=1):
        model = build_model(selected_arm, seed).to(device)
        if selected_arm == "T3_CSZ_TWO_STAGE_LINEAR":
            deadline = time.monotonic() + config["resources"]["t3_refit_job_timeout_seconds"]
            _, curves_a, _ = _train_phase(config, model, selected_arm, "phase_a", refit, refit, seed,
                refit_weights[seed], max_epochs=epoch_contract["refit_phase_a_epoch_n"],
                fixed_epoch_n=epoch_contract["refit_phase_a_epoch_n"], device=device,
                hard_deadline=deadline)
            phase_a_hash = model_state_semantic_hash(cpu_state(model))
            state, curves_b, _ = _train_phase(config, model, selected_arm, "phase_b", refit, refit, seed,
                refit_weights[seed], max_epochs=epoch_contract["refit_phase_b_epoch_n"],
                fixed_epoch_n=epoch_contract["refit_phase_b_epoch_n"], device=device,
                hard_deadline=deadline)
            phase_curves = {"phase_a": curves_a, "phase_b": curves_b}
        else:
            state, curves, _ = _train_phase(config, model, selected_arm, "joint", refit, refit, seed,
                refit_weights[seed], max_epochs=epoch_contract["refit_epoch_n"],
                fixed_epoch_n=epoch_contract["refit_epoch_n"], device=device,
                hard_deadline=time.monotonic() + config["resources"]["joint_refit_job_timeout_seconds"])
            phase_a_hash = None
            phase_curves = {"joint": curves}
        relative = f"training/refit_checkpoints/seed_{seed}/state_dict.pt"
        path = build / relative
        save_checkpoint(path, state)
        append_access_event(build, worker_role="REFIT", stage_id=STAGE_IDS[3], path=relative,
            access_mode="artifact_write", metadata_only=False, value_parsed=False)
        for phase_id, curves_for_phase in phase_curves.items():
            final_phase = "phase_b" if selected_arm == "T3_CSZ_TWO_STAGE_LINEAR" else "joint"
            refit_registry.append({"job_order": job_order, "arm_id": selected_arm, "model_seed": seed,
                "phase_id": phase_id, "fit_row_n": len(refit.frame), "fixed_epoch_n": len(curves_for_phase),
                "phase_selected_semantic_sha256": curves_for_phase[-1]["checkpoint_semantic_sha256"],
                "checkpoint_path": relative if phase_id == final_phase else None,
                "checkpoint_sha256": file_sha(path) if phase_id == final_phase else None,
                "checkpoint_semantic_sha256": model_state_semantic_hash(state) if phase_id == final_phase else None,
                "job_status": "complete", "reason_code": None})
        refit_entries.append({"job_order": job_order, "fold_id": "REFIT_2018_2022",
            "arm_id": selected_arm, "model_seed": seed,
            "final_phase_id": "phase_b" if selected_arm == "T3_CSZ_TWO_STAGE_LINEAR" else "joint",
            "path": relative, "size_bytes": path.stat().st_size, "sha256": file_sha(path),
            "semantic_sha256": model_state_semantic_hash(state), "phase_a_semantic_sha256": phase_a_hash,
            "selected_epoch": (epoch_contract["refit_phase_b_epoch_n"]
                if selected_arm == "T3_CSZ_TWO_STAGE_LINEAR" else epoch_contract["refit_epoch_n"]),
            "phase_a_selected_epoch": epoch_contract["refit_phase_a_epoch_n"]})
    write_csv(build / "training/refit_training_run_registry.csv", refit_registry, list(refit_registry[0]))
    write_json(build / "training/refit_checkpoint_manifest.json", {"schema_version": "21F_CHECKPOINT_MANIFEST_V1",
        "run_id": RUN_ID, "checkpoint_entries": refit_entries, "entry_n": 3,
        "entries_semantic_sha256": stable_hash(refit_entries)})
    access = pd.read_csv(build / "preflight/value_access_audit.csv")
    restricted_attempts = restricted_pre2023_open_attempts(config, access)
    if restricted_attempts != 0:
        raise ContractError("pre-2023 restricted value firewall violated")
    precomplete = {"schema_version": "21F_PRE_2023_COMPLETE_V1", "run_id": RUN_ID,
        "inner_checkpoint_manifest_sha256": file_sha(build / "training/inner_checkpoint_manifest.json"),
        "selected_predictor_estimator_sha256": file_sha(build / "training/selected_predictor_estimator.json"),
        "selected_training_arm_sha256": file_sha(build / "training/selected_training_arm.json"),
        "shadow_selection_sha256": file_sha(build / "training/mean_rankic_only_shadow_selection.json"),
        "refit_checkpoint_manifest_sha256": file_sha(build / "training/refit_checkpoint_manifest.json"),
        "refit_epoch_contract_sha256": file_sha(build / "training/refit_epoch_contract.json"),
        "value_access_audit_snapshot_sha256": file_sha(build / "preflight/value_access_audit.csv"),
        "restricted_value_parse_open_attempt_n": restricted_attempts, "completed_at_utc": utc_now()}
    write_json(build / "preflight/pre_2023_complete.json", precomplete)
    write_json(build / ".state/selection_refit_complete.json", {
        "schema_version": "21F_SELECTION_REFIT_COMPLETE_V1",
        "selected_estimator_id": selected_estimator, "selected_arm_id": selected_arm,
        "completed_at_utc": utc_now()})
    mark_stage(build, STAGE_IDS[3], "complete")
    pass_gates(build, range(21, 28), ["training/selected_predictor_estimator.json",
        "training/selected_training_arm.json", "training/refit_checkpoint_manifest.json",
        "preflight/pre_2023_complete.json"])


def stationary_bootstrap_p(values: np.ndarray, family_order: int, contrast_order: int,
                           replicate_n: int = 5000) -> float:
    observed = np.asarray(values, dtype=np.float64)
    if len(observed) == 0 or not np.isfinite(observed).all():
        raise ContractError("bootstrap values must be finite and nonempty")
    rng = np.random.Generator(np.random.PCG64(21070031 + 100 * family_order + contrast_order))
    means = np.empty(replicate_n, dtype=np.float64)
    n = len(observed)
    for replicate in range(replicate_n):
        indices = np.empty(n, dtype=np.int64)
        indices[0] = rng.integers(0, n)
        for position in range(1, n):
            indices[position] = rng.integers(0, n) if rng.random() < 0.1 else (indices[position - 1] + 1) % n
        means[replicate] = float(np.mean(observed[indices]))
    return float(min(1.0, 2.0 * min(np.mean(means <= 0), np.mean(means >= 0))))


def holm_adjust(rows: list[dict[str, Any]]) -> None:
    ordered = sorted(range(len(rows)), key=lambda index: (rows[index]["p_unadjusted"], rows[index]["contrast_order"]))
    running = 0.0
    m = len(rows)
    for rank, index in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * rows[index]["p_unadjusted"]))
        rows[index]["p_holm"] = running


def terminal_state(research_estimator_selected: bool, research_arm_selected: bool,
                   rank_repair_floor_pass: bool, drc_incremental_value_pass: bool,
                   full_stability_candidate_pass: bool) -> str:
    if not research_estimator_selected:
        return "21F_predictor_semantics_unresolved"
    if not research_arm_selected:
        return "21F_no_stable_training_repair"
    if not rank_repair_floor_pass:
        return "21F_no_rank_repair"
    if not drc_incremental_value_pass:
        return "21F_repaired_rank_without_drc_increment"
    if not full_stability_candidate_pass:
        return "21F_mean_rank_repair_unstable"
    return "21F_design_contaminated_semantic_repair_candidate"


def _daily_readout(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    identities = ["stage_id", "fold_id", "arm_id", "estimator_id", "score_variant", "model_seed", "is_ensemble"]
    for identity, group in predictions.groupby(identities, dropna=False, sort=True):
        _, daily = mean_daily_rankic(group["score"].to_numpy(), group["label"].to_numpy(),
            group["decision_date"].astype(str).tolist())
        prefix = dict(zip(identities, identity, strict=True))
        rows.extend([{**prefix, **row} for row in daily.to_dict("records")])
    return pd.DataFrame(rows)[TABULAR_SCHEMAS["daily_rankic"]]


def _morphology_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    morphology, top_rows, lomo_rows = [], [], []
    group_cols = ["stage_id", "fold_id", "arm_id", "estimator_id"]
    for identity, group in predictions.groupby(group_cols, sort=True):
        prefix = dict(zip(group_cols, identity, strict=True))
        seed_frames = {seed: group.loc[group["model_seed"].eq(seed),
            ["decision_date", "instrument", "score"]] for seed in MODEL_SEEDS}
        for index, left_seed in enumerate(MODEL_SEEDS):
            for right_seed in MODEL_SEEDS[index + 1:]:
                morphology.append({**prefix, "seed_a": left_seed, "seed_b": right_seed,
                    "paired_day_n": seed_frames[left_seed]["decision_date"].nunique(),
                    "mean_daily_score_spearman": daily_score_spearman(seed_frames[left_seed], seed_frames[right_seed]),
                    "mean_daily_top30_overlap": daily_top30_overlap(seed_frames[left_seed], seed_frames[right_seed]),
                    "status": "pass", "reason_code": None})
        identity_cols = ["model_seed", "is_ensemble"]
        for seed_identity, score_group in group.groupby(identity_cols, dropna=False, sort=True):
            model_seed, is_ensemble = seed_identity
            sets = top30_by_day(score_group[["decision_date", "instrument", "score"]])
            dates = sorted(sets)
            previous = None
            for date in dates:
                overlap = None if previous is None else len(set(sets[previous]) & set(sets[date]))
                top_rows.append({**prefix, "model_seed": None if pd.isna(model_seed) else int(model_seed),
                    "is_ensemble": bool(is_ensemble), "decision_date": date,
                    "previous_decision_date": previous, "top30_n": 30,
                    "adjacent_overlap_n": overlap, "adjacent_turnover": None if overlap is None else 1.0 - overlap / 30.0,
                    "status": "pass", "reason_code": None})
                previous = date
            if bool(is_ensemble):
                dates_series = pd.to_datetime(score_group["decision_date"])
                unit_type = "quarter" if str(prefix["fold_id"]).startswith("I") else "month"
                period_code = "Q" if unit_type == "quarter" else "M"
                unit_labels = dates_series.dt.to_period(period_code).astype(str)
                units = sorted(unit_labels.unique())
                for unit in units:
                    retained = score_group.loc[unit_labels.ne(unit)]
                    metric = mean_daily_rankic(retained["score"].to_numpy(), retained["label"].to_numpy(),
                        retained["decision_date"].astype(str).tolist())[0]
                    lomo_rows.append({**prefix, "model_seed": None, "is_ensemble": True,
                        "lomo_unit_type": unit_type, "omitted_unit_id": unit,
                        "retained_day_n": retained["decision_date"].nunique(), "mean_daily_rankic": metric,
                        "positive": metric > 0, "status": "pass", "reason_code": None})
    return pd.DataFrame(morphology), pd.DataFrame(top_rows), pd.DataFrame(lomo_rows)


def _paired_design_contrasts(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    late = predictions.loc[predictions["fold_id"].eq("DESIGN_LATE_2023")]
    selected = late.loc[late["score_variant"].eq("selected_drc")]
    k0 = late.loc[late["score_variant"].eq("same_backbone_k0")]
    q0 = late.loc[late["score_variant"].eq("q0_current8")]
    rows = []
    for contrast_order, contrast_id, left, right in ((10, "C10", selected, k0), (11, "C11", selected, q0)):
        left_ensemble = left.loc[left["is_ensemble"]]
        right_ensemble = right.loc[right["is_ensemble"]]
        _, left_daily = mean_daily_rankic(left_ensemble["score"].to_numpy(), left_ensemble["label"].to_numpy(), left_ensemble["decision_date"].astype(str))
        _, right_daily = mean_daily_rankic(right_ensemble["score"].to_numpy(), right_ensemble["label"].to_numpy(), right_ensemble["decision_date"].astype(str))
        paired = left_daily.merge(right_daily, on="decision_date", suffixes=("_left", "_right"), validate="one_to_one")
        delta = paired["rankic_left"].to_numpy() - paired["rankic_right"].to_numpy()
        seed_deltas = []
        for seed in MODEL_SEEDS:
            left_seed = left.loc[left["model_seed"].eq(seed)]
            right_seed = right.loc[right["model_seed"].eq(seed)]
            seed_deltas.append(mean_daily_rankic(left_seed["score"].to_numpy(), left_seed["label"].to_numpy(), left_seed["decision_date"].astype(str))[0] -
                mean_daily_rankic(right_seed["score"].to_numpy(), right_seed["label"].to_numpy(), right_seed["decision_date"].astype(str))[0])
        ensemble_delta = float(np.mean(delta))
        rows.append({"contrast_order": contrast_order, "family_id": "F_DESIGN_LATE",
            "fold_id": "DESIGN_LATE_2023", "contrast_id": contrast_id,
            "left_id": "SELECTED_DRC", "right_id": "SAME_BACKBONE_K0" if contrast_id == "C10" else "Q0_CURRENT_SCORE_MEAN8",
            "paired_day_n": len(paired), "mean_daily_rankic_left": float(paired["rankic_left"].mean()),
            "mean_daily_rankic_right": float(paired["rankic_right"].mean()),
            "mean_daily_rankic_delta": ensemble_delta,
            "same_direction_seed_n": sum(np.sign(value) == np.sign(ensemble_delta) and value != 0 for value in seed_deltas) if ensemble_delta != 0 else 0,
            "p_unadjusted": stationary_bootstrap_p(delta, 3, contrast_order), "p_holm": math.nan,
            "materiality_pass": False, "status": "pass", "reason_code": None})
    holm_adjust(rows)
    return rows


@torch.no_grad()
def fresh_2023_worker(config: Mapping[str, Any]) -> None:
    started = time.monotonic()
    build = building_output_root(config)
    if not (build / "preflight/pre_2023_complete.json").exists():
        raise ContractError("pre-2023 seal required")
    if torch.is_grad_enabled():
        raise ContractError("fresh worker must run with autograd disabled")
    device = torch.device("cuda")
    selected_estimator_payload = json.loads((build / "training/selected_predictor_estimator.json").read_text())
    selected_arm_payload = json.loads((build / "training/selected_training_arm.json").read_text())
    selected_estimator = selected_estimator_payload["selected_estimator_id"] or selected_estimator_payload["diagnostic_fallback_estimator_id"]
    selected_arm = selected_arm_payload["selected_arm_id"] or selected_arm_payload["diagnostic_fallback_arm_id"]
    feature_cache = load_feature_cache(config)
    all_frames = []
    for split_id in ("DESIGN_EARLY_2023", "DESIGN_LATE_2023"):
        fold = load_fold_slice(config, split_id, worker_role="FRESH_2023", allow_design=True,
            feature_cache=feature_cache)
        selected_scores, k0_scores, q2_scores, q0_scores = {}, {}, {}, {}
        for seed in MODEL_SEEDS:
            path = build / f"training/refit_checkpoints/seed_{seed}/state_dict.pt"
            model = build_model(selected_arm, seed)
            model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
            append_access_event(build, worker_role="FRESH_2023", stage_id=STAGE_IDS[4],
                path=path.relative_to(build).as_posix(), access_mode="checkpoint_read",
                metadata_only=False, value_parsed=True)
            model.to(device)
            selected_scores[seed] = score_fold(model, selected_estimator, fold, selected_arm, seed,
                batch_size=1024, device=device)
            k0_scores[seed] = score_fold(model, "Q6_KOOPMAN_ONLY", fold, selected_arm, seed,
                batch_size=1024, device=device)
            q2_scores[seed] = score_fold(model, "Q2_SCORE_MEAN256_REF", fold, selected_arm, seed,
                batch_size=1024, device=device)
            config_21e = PINNED_21E.load_config()
            sealed, _ = PINNED_21E._sealed_checkpoint(config_21e, seed, device)
            sealed_path = (workspace_path(config_21e["inputs"]["21c_checkpoint_root"], must_exist=True) /
                f"seed_{seed}/state_dict.pt")
            append_access_event(build, worker_role="FRESH_2023", stage_id=STAGE_IDS[4],
                path=sealed_path.relative_to(WORKSPACE).as_posix(), access_mode="checkpoint_read",
                metadata_only=False, value_parsed=True)
            q0_scores[seed] = PINNED_21C.score_numpy_panel(sealed, fold.raw_panel[:, :10, None],
                fold.x_source, fold.frame["instrument"].astype(str).tolist(),
                fold.frame["decision_date"].astype(str).tolist(), seed, batch_size=1024, device=device).astype(np.float32)
        all_frames.extend([
            prediction_frame(fold, selected_arm, selected_estimator, selected_scores, STAGE_IDS[4], "selected_drc"),
            prediction_frame(fold, "SAME_BACKBONE_K0", "Q6_KOOPMAN_ONLY", k0_scores, STAGE_IDS[4], "same_backbone_k0"),
            prediction_frame(fold, "SEALED_21C_Q0", "Q0_CURRENT_SCORE_MEAN8", q0_scores, STAGE_IDS[4], "q0_current8"),
            prediction_frame(fold, selected_arm, "Q2_SCORE_MEAN256_REF", q2_scores, STAGE_IDS[4], "q2_ref256"),
        ])
    predictions = pd.concat(all_frames, ignore_index=True)
    write_parquet(build / "predictions/design_2023_prediction_scores.parquet", predictions)
    design_index = pd.read_parquet(build / "preflight/design_2023_row_index.parquet")
    prior_transform = pd.read_parquet(build / "return_transform_audit.parquet")
    design_transform = return_transform_audit_for_index(config, design_index,
        ["DESIGN_EARLY_2023", "DESIGN_LATE_2023"])
    for split_id in ("DESIGN_EARLY_2023", "DESIGN_LATE_2023"):
        pin_id = "design_early_value_panel" if split_id == "DESIGN_EARLY_2023" else "design_late_value_panel"
        append_access_event(build, worker_role="FRESH_2023", stage_id=STAGE_IDS[4],
            path=config["upstream_pins"][pin_id]["path"], access_mode="value_parse",
            metadata_only=False, value_parsed=True,
            label_value_materialized_n=int((design_index["fold_id"] == split_id).sum()))
    combined_transform = pd.concat([prior_transform, design_transform], ignore_index=True)
    if len(combined_transform) != 28094:
        raise ContractError("return-transform total row formula drift")
    write_parquet(build / "return_transform_audit.parquet", combined_transform)
    write_json(build / ".state/fresh_2023_worker_exit.json", {"schema_version": "21F_FRESH_WORKER_EXIT_V1",
        "optimizer_object_n": 0, "autograd_enabled": False, "train_loader_object_n": 0,
        "checkpoint_write_n": 0, "worker_exit_code": 0, "completed_at_utc": utc_now()})
    record_nontraining_inference_seconds(config, STAGE_IDS[4], time.monotonic() - started)


def run_fresh_2023(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    marker = build / ".state/fresh_2023_complete.json"
    if marker.exists():
        return
    if not (build / ".state/selection_refit_complete.json").exists():
        raise ContractError("selection/refit must complete before 2023 readout")
    mark_stage(build, STAGE_IDS[4], "running")
    fresh_2023_worker(config)
    predictions = pd.read_parquet(build / "predictions/design_2023_prediction_scores.parquet")
    daily = _daily_readout(predictions)
    prior_daily = pd.read_csv(build / "daily_rankic_readout.csv")
    daily_all = pd.concat([prior_daily, daily], ignore_index=True)
    write_csv(build / "daily_rankic_readout.csv", daily_all.to_dict("records"), list(daily_all.columns))
    selected_payload = json.loads((build / "training/selected_predictor_estimator.json").read_text())
    selected_estimator_identity = selected_payload["selected_estimator_id"] or selected_payload["diagnostic_fallback_estimator_id"]
    morphology_input = predictions.loc[~(
        predictions["score_variant"].eq("q2_ref256") &
        (selected_estimator_identity == "Q2_SCORE_MEAN256_REF")
    )]
    morphology, top30, lomo = _morphology_tables(morphology_input)
    prior_morphology = pd.read_csv(build / "cross_seed_morphology.csv")
    prior_top30 = pd.read_csv(build / "top30_overlap_and_turnover.csv")
    prior_lomo = pd.read_csv(build / "monthly_quarter_lomo_stability.csv")
    morphology_all = pd.concat([prior_morphology, morphology], ignore_index=True)
    top30_all = pd.concat([prior_top30, top30], ignore_index=True)
    lomo_all = pd.concat([prior_lomo, lomo], ignore_index=True)
    write_csv(build / "cross_seed_morphology.csv", morphology_all.to_dict("records"), list(morphology_all.columns))
    write_csv(build / "top30_overlap_and_turnover.csv", top30_all.to_dict("records"), list(top30_all.columns))
    write_csv(build / "monthly_quarter_lomo_stability.csv", lomo_all.to_dict("records"), list(lomo_all.columns))
    contrasts = _paired_design_contrasts(predictions)
    c10, c11 = contrasts
    # Morphology non-worse uses the exact aggregate identities directly.
    late = predictions.loc[predictions["fold_id"].eq("DESIGN_LATE_2023")]
    metrics = {}
    for variant in ("selected_drc", "same_backbone_k0"):
        group = late.loc[late["score_variant"].eq(variant)]
        seeds = {seed: group.loc[group["model_seed"].eq(seed), "score"].to_numpy() for seed in MODEL_SEEDS}
        fold_proxy = FoldSlice("DESIGN_LATE_2023", group.loc[group["model_seed"].eq(MODEL_SEEDS[0]),
            ["decision_date", "instrument", "row_key_hash"]].reset_index(drop=True),
            group.loc[group["model_seed"].eq(MODEL_SEEDS[0]), ["label"]].to_numpy(), None, None)
        rho, overlap, turnover = _cross_seed_metrics(fold_proxy, seeds)
        metrics[variant] = (rho, overlap, turnover)
    morphology_nonworse = (metrics["selected_drc"][0] >= metrics["same_backbone_k0"][0] and
        metrics["selected_drc"][1] >= metrics["same_backbone_k0"][1] and
        metrics["selected_drc"][2] <= metrics["same_backbone_k0"][2])
    c10["materiality_pass"] = bool(c10["mean_daily_rankic_delta"] >= 0.005 and
        c10["same_direction_seed_n"] >= 2 and c10["paired_day_n"] >= 100 and
        morphology_nonworse and c10["p_holm"] <= 0.10)
    c11["materiality_pass"] = bool(c11["mean_daily_rankic_left"] >= 0.030 and
        c11["mean_daily_rankic_delta"] >= 0.020)
    prior_contrasts = pd.read_csv(build / "paired_semantic_contrasts.csv")
    design_contrasts = pd.DataFrame(contrasts).drop(columns=["contrast_order"])
    all_contrasts = pd.concat([prior_contrasts, design_contrasts], ignore_index=True)
    write_csv(build / "paired_semantic_contrasts.csv", all_contrasts.to_dict("records"), list(all_contrasts.columns))
    selected_estimator_payload = json.loads((build / "training/selected_predictor_estimator.json").read_text())
    selected_arm_payload = json.loads((build / "training/selected_training_arm.json").read_text())
    shadow = json.loads((build / "training/mean_rankic_only_shadow_selection.json").read_text())
    selected_arm = selected_arm_payload["selected_arm_id"] or selected_arm_payload["diagnostic_fallback_arm_id"]
    identity_differs = shadow["shadow_arm_id"] != selected_arm
    shadow_morphology_fail = False
    shadow_gate_vector = {}
    if shadow["shadow_arm_id"] is not None:
        inner_predictions = pd.read_parquet(build / "predictions/inner_selection_prediction_scores.parquet")
        for fold_id in ("I0_SELECT_2021", "I1_SELECT_2022"):
            group = inner_predictions.loc[(inner_predictions["fold_id"] == fold_id) &
                (inner_predictions["arm_id"] == shadow["shadow_arm_id"])]
            seed_frames = {seed: group.loc[group["model_seed"].eq(seed),
                ["decision_date", "instrument", "score"]] for seed in MODEL_SEEDS}
            rhos, overlaps = [], []
            for index, left_seed in enumerate(MODEL_SEEDS):
                for right_seed in MODEL_SEEDS[index + 1:]:
                    rhos.append(daily_score_spearman(seed_frames[left_seed], seed_frames[right_seed]))
                    overlaps.append(daily_top30_overlap(seed_frames[left_seed], seed_frames[right_seed]))
            ensemble_frame = group.loc[group["is_ensemble"], ["decision_date", "instrument", "score"]]
            vector = {"rho": float(np.mean(rhos)), "overlap": float(np.mean(overlaps)),
                "turnover": adjacent_turnover(ensemble_frame)}
            shadow_gate_vector[fold_id] = vector
            shadow_morphology_fail |= vector["rho"] < 0.25 or vector["overlap"] < 6 or vector["turnover"] > 0.80
    h21f07_pass = bool(identity_differs and selected_arm_payload["research_arm_selected"] and shadow_morphology_fail)
    selection_row = {"selected_arm_id": selected_arm_payload["selected_arm_id"],
        "shadow_arm_id": shadow["shadow_arm_id"], "identity_differs": identity_differs,
        "selected_worst_fold_rankic": min(selected_arm_payload["lexicographic_key"][0:1]),
        "shadow_mean_fold_rankic": shadow["lexicographic_key"][0] if shadow["lexicographic_key"] else None,
        "selected_gate_vector_json": json.dumps({"eligible": bool(selected_arm_payload["research_arm_selected"])}),
        "shadow_gate_vector_json": json.dumps(shadow_gate_vector, separators=(",", ":")),
        "h21f07_materiality_pass": h21f07_pass, "status": "pass", "reason_code": None}
    write_csv(build / "selection_policy_difference_audit.csv", [selection_row], list(selection_row))
    hypothesis_rows = []
    for row in hypothesis_registry().to_dict("records"):
        hid = row["hypothesis_id"]
        contrast_map = {"H21F01_RETURN_SCALE_NECESSARY": "C01",
            "H21F02_GRADIENT_GRAPH_MATERIAL": "C02", "H21F03_TWO_STAGE_REPAIR": "C03",
            "H21F04_DECODER_ROLE_MATERIAL": "C04"}
        if hid in contrast_map:
            evidence = prior_contrasts.loc[prior_contrasts["contrast_id"].eq(contrast_map[hid])]
            passed = len(evidence) == 2 and evidence["materiality_pass"].astype(bool).all()
            if hid == "H21F04_DECODER_ROLE_MATERIAL" and passed:
                passed = len(set(np.sign(evidence["mean_daily_rankic_delta"]))) == 1
        elif hid == "H21F05_PREDICTOR_ESTIMATOR_UNSTABLE":
            convergence = pd.read_csv(build / "predictor_draw_convergence.csv")
            reference = convergence.loc[(convergence["arm_id"] == "T1_CSZ_COUPLED_LINEAR") &
                (convergence["estimator_id"] == "Q1_SCORE_MEAN64")]
            passed = bool((~reference["convergence_pass"].astype(bool)).any())
        elif hid == "H21F06_DRC_INCREMENTAL_VALUE":
            passed = c10["materiality_pass"]
        elif hid == "H21F07_SELECTION_POLICY_DIFFERENCE":
            passed = h21f07_pass
        else:
            passed = False
        if hid == "H21F08_AUTHOR_CODE_REMAINS_UNKNOWN":
            passed = True
        hypothesis_rows.append({"hypothesis_order": row["hypothesis_order"], "hypothesis_id": hid,
            "materiality_rule_id": row["materiality_rule_id"], "materiality_pass": bool(passed),
            "falsifier_triggered": not bool(passed), "evidence_ids_json": "[]",
            "conclusion": "supported" if passed else "unsupported",
            "claim_ceiling": "design_contaminated_semantic_repair_diagnostic_only",
            "status": "pass", "reason_code": None})
    write_csv(build / "hypothesis_readout.csv", hypothesis_rows, list(hypothesis_rows[0]))
    selected_late = late.loc[late["score_variant"].eq("selected_drc")]
    positive_seed_n = sum(mean_daily_rankic(
        selected_late.loc[selected_late["model_seed"].eq(seed), "score"].to_numpy(),
        selected_late.loc[selected_late["model_seed"].eq(seed), "label"].to_numpy(),
        selected_late.loc[selected_late["model_seed"].eq(seed), "decision_date"].astype(str))[0] > 0
        for seed in MODEL_SEEDS)
    selected_lomo = lomo.loc[(lomo["fold_id"] == "DESIGN_LATE_2023") &
        (lomo["arm_id"] == selected_arm) & (lomo["estimator_id"] == selected_estimator_identity)]
    selected_convergence = pd.read_csv(build / "predictor_draw_convergence.csv")
    selected_convergence = selected_convergence.loc[(selected_convergence["arm_id"] == selected_arm) &
        (selected_convergence["estimator_id"] == selected_estimator_identity)]
    selected_collapse = pd.read_parquet(build / "gradient_graph_and_collapse_audit.parquet")
    selected_collapse = selected_collapse.loc[selected_collapse["arm_id"].eq(selected_arm)]
    historical_access = pd.read_csv(build / "historical_design_holdout_access_audit.csv")
    full_stability = bool(c10["materiality_pass"] and c11["materiality_pass"] and
        selected_estimator_payload["research_estimator_selected"] and selected_arm_payload["research_arm_selected"] and
        positive_seed_n >= 2 and metrics["selected_drc"][0] >= 0.25 and
        metrics["selected_drc"][1] >= 6 and metrics["selected_drc"][2] <= 0.80 and
        selected_lomo["positive"].astype(bool).sum() >= 5 and
        not selected_convergence.empty and selected_convergence["convergence_pass"].astype(bool).all() and
        not selected_collapse["additional_collapse_flag"].astype(bool).any() and
        historical_access["open_attempt_n"].eq(0).all())
    write_json(marker, {"schema_version": "21F_FRESH_2023_COMPLETE_V1",
        "rank_repair_floor_pass": c11["materiality_pass"],
        "drc_incremental_value_pass": c10["materiality_pass"],
        "full_stability_candidate_pass": full_stability,
        "completed_at_utc": utc_now()})
    mark_stage(build, STAGE_IDS[4], "complete")
    pass_gates(build, range(28, 36), ["predictions/design_2023_prediction_scores.parquet",
        "paired_semantic_contrasts.csv", "hypothesis_readout.csv"])
    set_research_gate(build, 32, bool(c10["materiality_pass"]), {
        "mean_daily_rankic_delta": c10["mean_daily_rankic_delta"],
        "same_direction_seed_n": c10["same_direction_seed_n"], "p_holm": c10["p_holm"]})
    set_research_gate(build, 33, full_stability, {
        "rank_repair_floor_pass": c11["materiality_pass"], "positive_seed_n": positive_seed_n,
        "lomo_positive_n": int(selected_lomo["positive"].astype(bool).sum())})


def _report_markdown(decision: Mapping[str, Any], local_only: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join([
        "# 21F REAKA 语义修复与排序稳定性验证报告", "",
        "## 1. 机械结论", "",
        f"终态：`{decision['terminal_state']}`。本结果只属于 `design_contaminated_semantic_repair_diagnostic`，不构成论文精确复现、作者实现识别或 forward support。", "",
        "## 2. 论文原文与未披露项", "",
        "论文定义了 Koopman latent dynamics、diffusion residual corrector 与联合目标的总体形式；point Predictor、DRC 梯度所有权、decoder 训练角色及再平衡频率仍未由官方代码闭合。", "",
        "## 3. 21D/21E prior", "",
        "21D/21E 数值只作为预注册先验和 exact replay 对象，不进入 2018–2022 epoch、estimator 或 arm 选择。", "",
        "## 4. 21F inner-fold evidence", "",
        "已执行 outcome-date purge、shared train-only gradient calibration、五个 training-semantics arms、Predictor convergence first-match 与 morphology-aware arm selection。详细数值见 paired_semantic_contrasts、predictor_draw_convergence 和 morphology artifacts。", "",
        "## 5. Predictor 与 T3 两阶段", "",
        "Q1/Q2/Q3/Q4 按 row-key CRN、完整 antithetic schedule 和 DDIM eta=0 合同比较；T3 Phase A 使用 Koopman-only Q6 选择，Phase B 使用 Q2，refit epochs 取六个 inner epochs 的 lower median。", "",
        "## 6. DRC incremental value", "",
        f"DRC incremental gate=`{str(decision['drc_incremental_value_pass']).lower()}`；它比较同一 refit state 的 selected DRC 与 denoiser-bypass K0，避免把 backbone 或 normalization 攘为 DRC 增益。", "",
        "## 7. 2023 contaminated readout", "",
        f"rank-repair floor=`{str(decision['rank_repair_floor_pass']).lower()}`；full-stability candidate=`{str(decision['full_stability_candidate_pass']).lower()}`。DESIGN_EARLY 仅描述，DESIGN_LATE 才进入冻结 gate。", "",
        "## 8. Morphology 与 shadow selection", "",
        "cross-seed Spearman、Top30 overlap、adjacent turnover、quarter/month LOMO 均作为独立稳定性证据；mean-only shadow 不控制任何 refit 或 2023 readout。", "",
        "## 9. 统计合同", "",
        "Daily RankIC 使用完整日横截面 Spearman；primary contrasts 使用 circular stationary bootstrap 和 family-local Holm adjustment。", "",
        "## 10. Sign reversal", "",
        "2023 early/late 分开报告，是否仍发生 sign reversal 必须从 daily_rankic_readout 与 paired contrasts 判断，不允许合并两段后覆盖。", "",
        "## 11. Claim ceiling", "",
        "即使 candidate gates 全部通过，也只说明本地 design-contaminated semantic repair candidate；官方作者实现仍未知。", "",
        "## 12. 组合与再平衡", "",
        "21F 不生成组合收益、Sharpe、回撤或交易成本。每日/非每日再平衡必须另立 requirement 并冻结持有期和成交时点。", "",
        "## 13. Local-only 大文件", "",
        json.dumps(list(local_only), ensure_ascii=False, indent=2), "",
    ])


def _prior_failure_history_hashes(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    root = workspace_path(config["paths"]["failure_history_root"])
    if not root.exists():
        return []
    rows = []
    for attempt in sorted(path for path in root.glob("attempt_*") if path.is_dir()):
        entries = [{"path": path.relative_to(attempt).as_posix(), "sha256": file_sha(path)}
                   for path in sorted(attempt.rglob("*")) if path.is_file()]
        rows.append({"attempt_id": attempt.name, "semantic_sha256": stable_hash(entries)})
    return rows


def validate_closed_schemas(build: Path) -> None:
    contracts = {
        "21F_reaka_semantic_repair_and_stability_validation_decision.csv": "decision",
        "preflight/pre_2023_row_index.parquet": "row_index",
        "preflight/design_2023_row_index.parquet": "row_index",
        "preflight/value_access_audit.csv": "value_access", "exact_replay_audit.csv": "exact_replay",
        "hypothesis_registry.csv": "hypothesis_registry",
        "training_semantics_arm_registry.csv": "training_arm_registry",
        "predictor_estimator_registry.csv": "predictor_registry",
        "contrast_registry.csv": "contrast_registry", "inner_fold_registry.csv": "inner_fold_registry",
        "return_transform_audit.parquet": "return_transform",
        "gradient_calibration_audit.parquet": "gradient_calibration",
        "gradient_graph_and_collapse_audit.parquet": "gradient_collapse",
        "training/inner_training_run_registry.csv": "inner_training_registry",
        "training/refit_training_run_registry.csv": "refit_training_registry",
        "predictions/inner_selection_prediction_scores.parquet": "prediction",
        "predictions/design_2023_prediction_scores.parquet": "prediction",
        "predictor_draw_convergence.csv": "draw_convergence",
        "daily_rankic_readout.csv": "daily_rankic",
        "paired_semantic_contrasts.csv": "paired_contrasts",
        "cross_seed_morphology.csv": "cross_seed_morphology",
        "top30_overlap_and_turnover.csv": "top30",
        "monthly_quarter_lomo_stability.csv": "lomo",
        "selection_policy_difference_audit.csv": "selection_policy",
        "hypothesis_readout.csv": "hypothesis_readout", "gate_evidence_21f.csv": "gate_evidence",
        "historical_design_holdout_access_audit.csv": "historical_access",
        "artifact_profile_registry.csv": "artifact_profile", "stage_status_registry.csv": "stage_status",
    }
    for relative, schema_id in contracts.items():
        path = build / relative
        if not path.exists():
            raise ContractError(f"closed-schema artifact missing: {relative}")
        observed = list(pq.read_schema(path).names) if path.suffix == ".parquet" else list(pd.read_csv(path, nrows=0).columns)
        if observed != TABULAR_SCHEMAS[schema_id]:
            raise ContractError(f"closed-schema column drift: {relative}: {observed}")
    if len(pd.read_parquet(build / "return_transform_audit.parquet")) != 28094:
        raise ContractError("return-transform row formula drift at finalize")
    if len(pd.read_csv(build / "training/inner_training_run_registry.csv")) != 36:
        raise ContractError("inner registry row formula drift at finalize")
    if len(pd.read_csv(build / "gate_evidence_21f.csv")) != 42:
        raise ContractError("gate registry row formula drift at finalize")


def run_finalize(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    if not (build / ".state/fresh_2023_complete.json").exists():
        raise ContractError("fresh 2023 readout must complete before finalize")
    if canonical.exists():
        raise ContractError("canonical output already exists")
    mark_stage(build, STAGE_IDS[5], "running")
    outcome = json.loads((build / ".state/fresh_2023_complete.json").read_text())
    estimator = json.loads((build / "training/selected_predictor_estimator.json").read_text())
    arm = json.loads((build / "training/selected_training_arm.json").read_text())
    terminal = terminal_state(bool(estimator["research_estimator_selected"]),
        bool(arm["research_arm_selected"]), bool(outcome["rank_repair_floor_pass"]),
        bool(outcome["drc_incremental_value_pass"]), bool(outcome["full_stability_candidate_pass"]))
    reason_by_terminal = {
        "21F_predictor_semantics_unresolved": "no_eligible_estimator",
        "21F_no_stable_training_repair": "no_eligible_arm",
        "21F_no_rank_repair": "rank_repair_floor_fail",
        "21F_repaired_rank_without_drc_increment": "drc_increment_fail",
        "21F_mean_rank_repair_unstable": "morphology_fail",
        "21F_design_contaminated_semantic_repair_candidate": "NA",
    }
    decision = {"schema_version": "21F_DECISION_V1", "run_id": RUN_ID,
        "terminal_state": terminal, "evidence_role": "design_contaminated_semantic_repair_diagnostic",
        "research_estimator_selected": bool(estimator["research_estimator_selected"]),
        "selected_estimator_id": estimator["selected_estimator_id"],
        "research_arm_selected": bool(arm["research_arm_selected"]), "selected_arm_id": arm["selected_arm_id"],
        "rank_repair_floor_pass": bool(outcome["rank_repair_floor_pass"]),
        "drc_incremental_value_pass": bool(outcome["drc_incremental_value_pass"]),
        "full_stability_candidate_pass": bool(outcome["full_stability_candidate_pass"]),
        "paper_exact_claim_allowed": False, "author_implementation_claim_allowed": False,
        "forward_support_claim_allowed": False, "next_requirement_execution_authorized": False,
        "reason_code": reason_by_terminal[terminal]}
    decision_path = build / "21F_reaka_semantic_repair_and_stability_validation_decision.csv"
    write_csv(decision_path, [decision], TABULAR_SCHEMAS["decision"])
    local_only = [{"path": path.relative_to(build).as_posix(), "size_bytes": path.stat().st_size}
                  for path in sorted(build.rglob("*")) if path.is_file() and path.stat().st_size > 20 * 1024 * 1024]
    report_path = build / "21F_reaka_semantic_repair_and_stability_validation_report.md"
    _atomic_bytes(report_path, _report_markdown(decision, local_only).encode("utf-8"))
    semantic = {"schema_version": "21F_SEMANTIC_MANIFEST_V1", "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "implementation_hashes": {name: file_sha(workspace_path(config["paths"][name], must_exist=True))
            for name in ("config", "runner", "test")},
        "upstream_pins": config["upstream_pins"],
        "fold_hashes": {item["fit_id"]: item["fit_row_key_sha256"] for item in config["inner_folds"]},
        "rng_contract": "row_keyed_sha256_cpu_tensor_v1", "training_contract": "21F_T0_T4_V1",
        "selected_objects": {"estimator": estimator, "arm": arm},
        "prior_failure_history_hashes": _prior_failure_history_hashes(config),
        "terminal_state": terminal}
    semantic["semantic_payload_sha256"] = stable_hash(semantic)
    write_json(build / "semantic_reproducibility_manifest.json", semantic)
    validate_closed_schemas(build)
    pass_gates(build, range(36, 43), [decision_path.name, report_path.name,
        "schema_registry_21f.json", "artifact_profile_registry.csv"])
    mark_stage(build, STAGE_IDS[5], "complete")
    shutil.rmtree(build / ".state")
    required_before_manifests = set(artifact_profile_contract()["required_paths"]) - {
        "manifest_21f_reaka_semantic_repair_and_stability_validation.json",
        "output_hashes_21f_reaka_semantic_repair_and_stability_validation.json"}
    observed = {path.relative_to(build).as_posix() for path in build.rglob("*") if path.is_file()}
    missing = required_before_manifests - observed
    if missing:
        raise ContractError(f"artifact profile missing paths: {sorted(missing)}")
    for path in observed:
        if any(token in path.lower() for token in FORBIDDEN_TOKENS):
            raise ContractError(f"forbidden success artifact: {path}")
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.sha256 is None:
        raise ContractError("authorization drifted before seal")
    artifact_entries = [{"path": path, "role": "checkpoint" if path.endswith("state_dict.pt") else "substantive_evidence",
        "schema_version": "21F_V1", "row_count": None, "size_bytes": (build / path).stat().st_size,
        "sha256": file_sha(build / path)} for path in sorted(observed) if not path.startswith(".state/")]
    manifest_path = build / "manifest_21f_reaka_semantic_repair_and_stability_validation.json"
    hashes_path = build / "output_hashes_21f_reaka_semantic_repair_and_stability_validation.json"
    manifest = {"schema_version": "21F_FINAL_MANIFEST_V1", "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION, "terminal_state": terminal,
        "artifact_profile_id": PROFILE_ID, "artifact_n": len(artifact_entries), "artifacts": artifact_entries,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "authorization_sha256": authorization.sha256,
        "paper_pdf_sha256": config["upstream_pins"]["paper_pdf"]["sha256"],
        "upstream_pins": config["upstream_pins"], "decision_sha256": file_sha(decision_path),
        "report_sha256": file_sha(report_path),
        "semantic_reproducibility_manifest_sha256": file_sha(build / "semantic_reproducibility_manifest.json"),
        "output_hashes_path": hashes_path.name, "output_hashes_excluded_self_path": hashes_path.name,
        "finalized_at_utc": utc_now()}
    write_json(manifest_path, manifest)
    hash_entries = [{"path": path.relative_to(build).as_posix(), "size_bytes": path.stat().st_size,
        "sha256": file_sha(path)} for path in sorted(build.rglob("*"))
        if path.is_file() and path != hashes_path and not path.relative_to(build).as_posix().startswith(".state/")]
    write_json(hashes_path, {"schema_version": "21F_OUTPUT_HASHES_V1", "run_id": RUN_ID,
        "entries": hash_entries, "entry_n": len(hash_entries),
        "entries_semantic_sha256": stable_hash(hash_entries), "excluded_self_path": hashes_path.name})
    final_observed = {path.relative_to(build).as_posix() for path in build.rglob("*") if path.is_file()}
    missing_final = set(artifact_profile_contract()["required_paths"]) - final_observed
    if missing_final:
        raise ContractError(f"final artifact profile incomplete: {sorted(missing_final)}")
    os.replace(build, canonical)


def record_technical_failure(config: Mapping[str, Any], exc: BaseException) -> None:
    build = building_output_root(config)
    if not build.exists() or not (build / "stage_status_registry.csv").exists():
        return
    stages = pd.read_csv(build / "stage_status_registry.csv", keep_default_na=False)
    running = stages.loc[stages["status"].eq("running"), "stage_id"].tolist()
    failed_stage = running[0] if running else stages.loc[~stages["status"].eq("complete"), "stage_id"].iloc[0]
    mark_stage(build, failed_stage, "fail", "worker_nonzero")
    gates = pd.read_csv(build / "gate_evidence_21f.csv", keep_default_na=False)
    pending = gates.loc[gates["evaluation_status"].ne("pass")]
    failed_gate = pending.iloc[0]["gate_id"] if not pending.empty else "finalize_transaction_gate"
    mask = gates["gate_id"].eq(failed_gate)
    gates.loc[mask, "evaluation_status"] = "fail"
    gates.loc[mask, "reason_code"] = "worker_nonzero"
    write_csv(build / "gate_evidence_21f.csv", gates.to_dict("records"), list(gates.columns))
    complete = stages.loc[stages["status"].eq("complete"), "stage_id"].tolist()
    record = {"schema_version": "21F_FAILURE_RECORD_V1", "run_id": RUN_ID,
        "failed_stage_id": failed_stage, "failed_gate_id": failed_gate,
        "error_type": type(exc).__name__, "error_message": str(exc), "worker_exit_code": 1,
        "last_complete_stage_id": complete[-1] if complete else None,
        "value_access_audit_sha256": file_sha(build / "preflight/value_access_audit.csv"),
        "historical_holdout_access_audit_sha256": file_sha(build / "historical_design_holdout_access_audit.csv"),
        "created_at_utc": utc_now()}
    write_json(build / "failure/failure_record.json", record)


def run_isolated_worker_stage(config: Mapping[str, Any], worker: str) -> None:
    runner = workspace_path(config["paths"]["runner"], must_exist=True)
    subprocess.run([sys.executable, str(runner), "--config", str(DEFAULT_CONFIG),
        "--worker", worker], cwd=WORKSPACE, check=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--stage", choices=("preflight", "replay", "inner-training",
        "selection-refit", "fresh-2023", "finalize", "all"), default="all")
    parser.add_argument("--worker", choices=("hash-only-integrity", "metadata-splitter",
        "preflight-purge", "exact-replay", "inner-training", "inner-training-lane",
        "parallel-gpu-probe", "selection-refit",
        "refit", "fresh-2023", "fresh-2023-stage", "finalize"))
    parser.add_argument("--lane-id", type=int, choices=(0, 1))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    authorization = validate_authorization(config)
    if authorization.status != "pass":
        raise ContractError("execution forbidden before valid human authorization: " + ",".join(authorization.errors))
    if args.worker:
        if args.worker in {"inner-training-lane", "parallel-gpu-probe"}:
            if args.lane_id is None:
                raise ContractError("lane worker requires --lane-id")
            canonical_build = building_output_root(config)
            lane_kind = ("inner_lanes" if args.worker == "inner-training-lane"
                         else "parallel_probe_lanes")
            config["_runtime_build_root"] = str(
                canonical_build / f".state/{lane_kind}/lane_{args.lane_id}")
        elif args.lane_id is not None:
            raise ContractError("--lane-id is only valid for lane workers")
        {"hash-only-integrity": hash_only_integrity_worker,
         "metadata-splitter": metadata_splitter_worker, "preflight-purge": preflight_purge_worker,
         "exact-replay": exact_replay_worker, "inner-training": run_inner_training,
         "inner-training-lane": lambda selected: run_inner_training_lane(selected, int(args.lane_id)),
         "parallel-gpu-probe": lambda selected: parallel_gpu_probe_worker(selected, int(args.lane_id)),
         "selection-refit": run_selection_and_refit, "refit": refit_worker,
         "fresh-2023": fresh_2023_worker, "fresh-2023-stage": run_fresh_2023,
         "finalize": run_finalize}[args.worker](config)
        return 0
    stages = {"preflight": run_preflight, "replay": run_exact_replay,
        "inner-training": lambda selected: run_isolated_worker_stage(selected, "inner-training"),
        "selection-refit": lambda selected: run_isolated_worker_stage(selected, "selection-refit"),
        "fresh-2023": lambda selected: run_isolated_worker_stage(selected, "fresh-2023-stage"),
        "finalize": lambda selected: run_isolated_worker_stage(selected, "finalize")}
    requested = tuple(stages) if args.stage == "all" else (args.stage,)
    try:
        for stage in requested:
            stages[stage](config)
    except BaseException as exc:
        record_technical_failure(config, exc)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
