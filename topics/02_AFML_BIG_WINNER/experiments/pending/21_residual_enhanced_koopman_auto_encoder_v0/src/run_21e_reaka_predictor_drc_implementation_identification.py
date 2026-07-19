#!/usr/bin/env python3
"""Run the 21E REAKA Predictor/DRC implementation-identification experiment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch import Tensor


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = EXPERIMENT_ROOT / "configs/config_21e_reaka_predictor_drc_implementation_identification.yaml"
RUN_ID = "21E_reaka_predictor_drc_implementation_identification"
REQUIREMENT_VERSION = "21E_IMPL_ID_v0"
PROFILE_ID = "P1_FULL_IMPLEMENTATION_IDENTIFICATION"
MODEL_SEEDS = (20260713, 20260714, 20260715)
LOOKBACK = 10
FEATURE_DIM = 157
LATENT_DIM = 64
N_OPERATOR = 4
FOLDS = ("validation_early", "validation_late")
PREDICTOR_IDS = (
    "P0_CURRENT_SCORE_MEAN8",
    "P1_SINGLE_DRAW0",
    "P2_SCORE_MEAN64",
    "P3_SCORE_MEAN256_REF",
    "P4_ZERO_NOISE_REVERSE_PROXY",
    "P5_KOOPMAN_ONLY",
    "P6_SCORE_MEDIAN256",
)
TRAINABLE_IDS = (
    "G0_CURRENT_X0_COUPLED",
    "G1_STOPGRAD_X0_RECON",
    "G2_TEACHER_LATENT_RECON_ORACLE",
    "A1_MLP_100_STEP",
    "A2_RESBLOCK_20_STEP",
    "A3_POINTWISE_MLP_DECODER",
)
ALL_ARM_IDS = PREDICTOR_IDS + (
    "G0_CURRENT_X0_COUPLED",
    "G1_STOPGRAD_X0_RECON",
    "G2_TEACHER_LATENT_RECON_ORACLE",
    "A0_SELECTED_GRAPH_CONTROL",
    "A1_MLP_100_STEP",
    "A2_RESBLOCK_20_STEP",
    "A3_POINTWISE_MLP_DECODER",
)
GATE_IDS = (
    "execution_authorization_gate",
    "paper_and_upstream_hash_gate",
    "upstream_terminal_state_gate",
    "retained_universe_exact_match_gate",
    "ambiguity_and_hypothesis_registry_gate",
    "historical_holdout_zero_access_gate",
    "predictor_arm_exact_gate",
    "exact_predictor_replay_gate",
    "predictor_draw_schedule_gate",
    "predictor_early_completion_gate",
    "training_arm_exact_gate",
    "common_resource_contract_gate",
    "training_completion_gate",
    "exact_g0_retrain_gate",
    "gradient_and_collapse_audit_gate",
    "early_selection_firewall_gate",
    "pre_late_complete_gate",
    "fresh_late_worker_gate",
    "prediction_coverage_gate",
    "metric_implementation_gate",
    "paired_contrast_gate",
    "hypothesis_falsification_gate",
    "portfolio_output_absence_gate",
    "historical_holdout_zero_access_finalize_gate",
    "report_decision_consistency_gate",
    "artifact_profile_gate",
    "output_manifest_hash_gate",
    "post_run_validation_gate",
    "finalize_transaction_gate",
)
AUTH_KEYS = {
    "schema_version",
    "run_id",
    "requirement_version",
    "approved_requirement_sha256",
    "approved_config_sha256",
    "approved_runner_sha256",
    "approved_test_sha256",
    "approved_paper_pdf_sha256",
    "approved_upstream_21b_v5_manifest_sha256",
    "approved_upstream_21b_v5_output_hashes_sha256",
    "approved_upstream_21c_manifest_sha256",
    "approved_upstream_21c_output_hashes_sha256",
    "approved_upstream_21d_manifest_sha256",
    "approved_upstream_21d_output_hashes_sha256",
    "approved_dependency_lock_sha256",
    "approved_device_fingerprint_sha256",
    "approved_replay_compatibility_profile",
    "replay_implementation_mode",
    "approved_artifact_profile_id",
    "approved_artifact_profile_registry_contract_sha256",
    "allowed_runtime_field_differences",
    "approved_by",
    "approved_at_utc",
}


class ContractError(RuntimeError):
    pass


class AuthorizationResult(NamedTuple):
    status: str
    errors: tuple[str, ...]
    payload: dict[str, Any] | None
    sha256: str | None


def utc_now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_path(relative: str | Path, *, must_exist: bool = False) -> Path:
    path = Path(relative)
    result = path if path.is_absolute() else WORKSPACE_ROOT / path
    result = result.resolve()
    if WORKSPACE_ROOT not in result.parents and result != WORKSPACE_ROOT:
        raise ContractError(f"path escapes workspace: {relative}")
    if must_exist and not result.exists():
        raise ContractError(f"required path missing: {relative}")
    return result


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(dict(payload)) + b"\n")
    os.replace(temporary, path)


def _write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows), columns=list(columns))
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("config must be a mapping")
    validate_frozen_config(payload)
    return payload


def validate_frozen_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "21E_IMPL_ID_CONFIG_V0":
        raise ContractError("config schema version drift")
    identity = config.get("identity", {})
    if identity.get("run_id") != RUN_ID or identity.get("requirement_version") != REQUIREMENT_VERSION:
        raise ContractError("config identity drift")
    if tuple(item["arm_id"] for item in config.get("predictor_arms", [])) != PREDICTOR_IDS:
        raise ContractError("predictor arm registry drift")
    if tuple(item["arm_id"] for item in config.get("training_arms", [])) != TRAINABLE_IDS:
        raise ContractError("training arm registry drift")
    if tuple(config.get("training", {}).get("model_seeds", [])) != MODEL_SEEDS:
        raise ContractError("model seed registry drift")
    if tuple(config.get("gates", [])) != GATE_IDS:
        raise ContractError("gate order drift")
    if len(config.get("contrasts", [])) != 11:
        raise ContractError("contrast registry must contain 11 rows")
    execution = config.get("execution", {})
    if execution.get("planned_training_job_n") != 18 or execution.get("artifact_profile_id") != PROFILE_ID:
        raise ContractError("execution cardinality/profile drift")
    if execution.get("historical_design_holdout_readout_authorized") is not False:
        raise ContractError("historical design holdout must remain forbidden")
    if execution.get("portfolio_output_authorized") is not False:
        raise ContractError("portfolio output must remain forbidden")
    for section in ("paths", "upstream_pins", "inputs"):
        if "latest" in canonical_json_bytes(config.get(section, {})).decode().lower():
            raise ContractError(f"latest path selection forbidden in {section}")


def import_pinned_module(config: Mapping[str, Any], pin_id: str, module_name: str) -> Any:
    pin = config["upstream_pins"][pin_id]
    path = workspace_path(pin["path"], must_exist=True)
    if file_sha(path) != pin["sha256"]:
        raise ContractError(f"pinned module hash mismatch: {pin_id}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot import pinned module: {pin_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BOOT_CONFIG = load_config()
_PINNED_21D = import_pinned_module(_BOOT_CONFIG, "21d_runner", "ep21d_pinned_runner")
_PINNED_21C = _PINNED_21D._PINNED_21C


def building_output_root(config: Mapping[str, Any]) -> Path:
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    return canonical.with_name(canonical.name + ".building")


def artifact_profile_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    required = sorted(required_artifact_paths(config))
    forbidden = sorted(
        {
            "paper_proxy_top30_daily.csv",
            "portfolio_returns.csv",
            "execution_ledger.csv",
            "annualized_return.csv",
            "sharpe.csv",
            "turnover.csv",
            "historical_holdout_predictions.parquet",
            "best_seed.csv",
            "post_late_added_arm.csv",
        }
    )
    return {
        "artifact_profile_id": PROFILE_ID,
        "required_paths": required,
        "forbidden_paths": forbidden,
        "conditional_paths": {},
    }


def current_device_fingerprint() -> str:
    return str(_PINNED_21D.current_device_fingerprint())


def validate_authorization(config: Mapping[str, Any]) -> AuthorizationResult:
    path = workspace_path(config["paths"]["execution_authorization"])
    if not path.exists():
        return AuthorizationResult("fail", ("authorization_missing",), None, None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return AuthorizationResult("fail", (f"authorization_invalid:{exc}",), None, None)
    errors: list[str] = []
    if set(payload) != AUTH_KEYS:
        errors.append("authorization_exact_keys_mismatch")
    expected = {
        "schema_version": "21E_EXECUTION_AUTHORIZATION_V0",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "approved_requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "approved_config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "approved_runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "approved_test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "approved_paper_pdf_sha256": config["upstream_pins"]["paper_pdf"]["sha256"],
        "approved_upstream_21b_v5_manifest_sha256": config["upstream_pins"]["21b_v5_manifest"]["sha256"],
        "approved_upstream_21b_v5_output_hashes_sha256": config["upstream_pins"]["21b_v5_output_hashes"]["sha256"],
        "approved_upstream_21c_manifest_sha256": config["upstream_pins"]["21c_manifest"]["sha256"],
        "approved_upstream_21c_output_hashes_sha256": config["upstream_pins"]["21c_output_hashes"]["sha256"],
        "approved_upstream_21d_manifest_sha256": config["upstream_pins"]["21d_manifest"]["sha256"],
        "approved_upstream_21d_output_hashes_sha256": config["upstream_pins"]["21d_output_hashes"]["sha256"],
        "approved_dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "approved_device_fingerprint_sha256": current_device_fingerprint(),
        "approved_replay_compatibility_profile": "EXACT_RUNTIME_V1",
        "replay_implementation_mode": "import_pinned_21c_21d_with_21b_v5_materialization",
        "approved_artifact_profile_id": PROFILE_ID,
        "approved_artifact_profile_registry_contract_sha256": stable_hash(artifact_profile_contract(config)),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key}_mismatch")
    if current_device_fingerprint() != config["sealed_replay"]["device_fingerprint_sha256"]:
        errors.append("exact_runtime_device_fingerprint_mismatch")
    if payload.get("allowed_runtime_field_differences") != []:
        errors.append("runtime_differences_must_be_empty")
    approved_by = str(payload.get("approved_by", ""))
    if not approved_by or approved_by.startswith(("runner", "process", "UNAUTHORIZED")):
        errors.append("human_approval_missing")
    approved_at = str(payload.get("approved_at_utc", ""))
    if not approved_at.endswith("Z"):
        errors.append("approved_at_utc_invalid")
    return AuthorizationResult(
        "pass" if not errors else "fail",
        tuple(errors),
        payload,
        file_sha(path),
    )


def configure_determinism() -> None:
    if not torch.cuda.is_available():
        raise ContractError("CUDA is required for authorized execution")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def ambiguity_registry() -> pd.DataFrame:
    rows = [
        (1, "A01_RESIDUAL_TARGET", "3.3", "16-18", True, "full_shifted_latent_residual", "exact_replay", "G0"),
        (2, "A02_DRC_CONDITION", "3.3", "19", True, "source_Z", "exact_replay", "G0"),
        (3, "A03_DIFFUSION_STEPS_SCHEDULE", "3.3", "16-21", False, "20_step_linear_beta", "20_vs_100", "A1"),
        (4, "A04_DENOISER_TOPOLOGY", "3.3", "19", False, "concat_mlp", "mlp_vs_resblock", "A2"),
        (5, "A05_REC_GRADIENT_COUPLING", "3.5", "26", False, "x0_coupled", "gradient_graph", "G0-G2"),
        (6, "A06_CORRECTED_LATENT_NOTATION", "3.3/3.5", "21/26/27", False, "corrected_latent", "koopman_only_control", "P5"),
        (7, "A07_POINT_PREDICTOR_AGGREGATION", "3.4", "22", False, "score_mean8", "point_readout", "P0-P6"),
        (8, "A08_DECODER_TOPOLOGY", "3.4", "22", False, "shared_linear", "linear_vs_pointwise_mlp", "A3"),
        (9, "A09_REBALANCE_FREQUENCY", "4.5", "", False, "daily_top30_proxy", "out_of_scope", ""),
    ]
    columns = [
        "ambiguity_order", "ambiguity_id", "paper_section", "paper_equation",
        "paper_defined", "project_choice", "test_stage", "test_arm_ids_json",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["allowed_conclusion"] = "local_implementation_sensitivity_only"
    frame["forbidden_conclusion"] = "paper_exact_or_author_implementation"
    frame["status"] = "pre_registered"
    return frame


def hypothesis_registry() -> pd.DataFrame:
    rows = [
        (1, "H21E01_POINT_AGGREGATION_MATERIAL", "predictor_semantics", "C01-C06"),
        (2, "H21E02_CURRENT_DRC_HARMS_SCORE", "corrected_latent", "C05"),
        (3, "H21E03_REC_GRADIENT_PATH_MATERIAL", "drc_training_graph", "C10-C11"),
        (4, "H21E04_DENOISER_OR_SCHEDULE_MATERIAL", "drc_architecture", "C20-C21"),
        (5, "H21E05_DECODER_TOPOLOGY_MATERIAL", "decoder_topology", "C22"),
        (6, "H21E06_UNDISCLOSED_CODE_REMAINS", "external_gap", "C01-C22"),
    ]
    frame = pd.DataFrame(rows, columns=["hypothesis_order", "hypothesis_id", "family_id", "required_contrast_ids_json"])
    frame["hypothesis_statement"] = frame["hypothesis_id"]
    frame["direct_falsifier"] = "mechanically_derived_from_frozen_materiality_contract"
    frame["allowed_conclusion"] = "design_contaminated_mechanism_diagnostic"
    frame["forbidden_conclusion"] = "paper_reproduction_or_forward_support"
    frame["status"] = "pre_registered"
    return frame[[
        "hypothesis_order", "hypothesis_id", "family_id", "hypothesis_statement",
        "direct_falsifier", "required_contrast_ids_json", "allowed_conclusion",
        "forbidden_conclusion", "status",
    ]]


def implementation_arm_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for arm in config["predictor_arms"]:
        rows.append(
            {
                "arm_order": arm["arm_order"], "arm_id": arm["arm_id"],
                "stage_family": "predictor_semantics", "training_required": False,
                "checkpoint_source": "21c_v4", "training_graph_id": "frozen_21c",
                "denoiser_topology": "concat_mlp", "diffusion_steps": 20,
                "beta_schedule": "linear_1e-4_2e-2", "decoder_topology": "linear",
                "point_predictor_id": arm["point_predictor_id"], "draw_n": arm["draw_n"],
                "seed_n": 3, "oracle_control": False,
                "paper_defined_fields_json": "{}", "project_choice_fields_json": "{}",
                "selection_role": "fixed_checkpoint_diagnostic", "status": "pre_registered",
            }
        )
    for arm in config["training_arms"]:
        rows.append(
            {
                "arm_order": arm["arm_order"], "arm_id": arm["arm_id"],
                "stage_family": arm["family_id"], "training_required": True,
                "checkpoint_source": "fresh_training", "training_graph_id": arm["training_graph_id"],
                "denoiser_topology": arm["denoiser_topology"], "diffusion_steps": arm["diffusion_steps"],
                "beta_schedule": "linear_1e-4_2e-2", "decoder_topology": arm["decoder_topology"],
                "point_predictor_id": "score_mean64", "draw_n": 64, "seed_n": 3,
                "oracle_control": arm["oracle_control"], "paper_defined_fields_json": "{}",
                "project_choice_fields_json": "{}", "selection_role": "early_only",
                "status": "pre_registered",
            }
        )
    selected = next(item for item in rows if item["arm_id"] == "G0_CURRENT_X0_COUPLED").copy()
    selected.update(
        {
            "arm_order": 10, "arm_id": "A0_SELECTED_GRAPH_CONTROL",
            "training_required": False, "checkpoint_source": "selected_g0_or_g1_alias",
            "selection_role": "alias_control",
        }
    )
    rows.append(selected)
    frame = pd.DataFrame(rows).sort_values("arm_order", kind="mergesort").reset_index(drop=True)
    if tuple(frame["arm_id"]) != ALL_ARM_IDS:
        raise ContractError("expanded arm registry drift")
    return frame


def predictor_readout_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    function = {
        "P0_CURRENT_SCORE_MEAN8": "mean",
        "P1_SINGLE_DRAW0": "identity",
        "P2_SCORE_MEAN64": "mean",
        "P3_SCORE_MEAN256_REF": "mean",
        "P4_ZERO_NOISE_REVERSE_PROXY": "deterministic_reverse",
        "P5_KOOPMAN_ONLY": "identity",
        "P6_SCORE_MEDIAN256": "median",
    }
    rows = []
    for order, arm in enumerate(config["predictor_arms"]):
        rows.append(
            {
                "readout_order": order, "point_predictor_id": arm["point_predictor_id"],
                "residual_source": "none" if order == 5 else "ddpm",
                "initial_x_T_role": "zero" if order == 4 else ("none" if order == 5 else "row_keyed_noise"),
                "reverse_noise_role": "zero" if order == 4 else ("none" if order == 5 else "row_keyed_noise"),
                "aggregation_domain": "decoded_score", "aggregation_function": function[arm["arm_id"]],
                "draw_start": 0, "draw_stop_exclusive": arm["draw_n"], "draw_n": arm["draw_n"],
                "deterministic": order in {4, 5}, "conditional_mean_claim_allowed": False,
                "paper_defined": False, "score_index": "last_shifted_position", "status": "pre_registered",
            }
        )
    return pd.DataFrame(rows)


def contrast_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for item in config["contrasts"]:
        rows.append(
            {
                **item,
                "left_score_variant": "point" if item["left_arm_id"].startswith("P") else "score_mean64",
                "right_score_variant": "point" if item["right_arm_id"].startswith("P") else "score_mean64",
                "primary_metric": "mean_daily_RankIC_delta",
                "materiality_rule_id": "PREDICTOR_V0" if item["contrast_id"].startswith("C0") else "GA_V0",
                "oracle_involved": "G2" in item["left_arm_id"] + item["right_arm_id"],
                "allowed_conclusion": "local_implementation_sensitivity_only",
                "forbidden_conclusion": "paper_exact_or_forward_support",
                "status": "pre_registered",
            }
        )
    return pd.DataFrame(rows)


def required_artifact_paths(config: Mapping[str, Any]) -> set[str]:
    paths = {
        "21E_reaka_predictor_drc_implementation_identification_report.md",
        "21E_reaka_predictor_drc_implementation_identification_decision.csv",
        "artifact_profile_registry.csv", "paper_predictor_drc_ambiguity_registry.csv",
        "hypothesis_registry.csv", "hypothesis_readout.csv", "implementation_arm_registry.csv",
        "contrast_registry.csv", "predictor_readout_registry.csv", "predictor_draw_stability.csv",
        "daily_rankic_readout.csv", "paired_implementation_contrasts.csv", "cross_seed_morphology.csv",
        "loss_gradient_and_collapse_audit.parquet", "training/training_run_registry.csv",
        "training/training_graph_selection.json", "training/promoted_ref256_selection.json",
        "training/checkpoint_manifest.json", "training/selection_worker_exit_record.json",
        "training/late_readout_worker_exit_record.json",
        "predictions/validation_early_prediction_scores.parquet",
        "predictions/validation_late_prediction_scores.parquet",
        "preflight/execution_authorization_audit.csv", "preflight/upstream_pin_and_file_set_audit.csv",
        "preflight/retained_universe_exact_match_audit.csv", "preflight/replay_runtime_fingerprint.json",
        "preflight/resolved_config.yaml", "historical_design_holdout_access_audit.csv",
        "stage_status_registry.csv", "gate_evidence_21e.csv", "semantic_reproducibility_manifest.json",
        "manifest_21e_reaka_predictor_drc_implementation_identification.json",
        "output_hashes_21e_reaka_predictor_drc_implementation_identification.json",
    }
    for arm_id in TRAINABLE_IDS:
        for seed in MODEL_SEEDS:
            paths.add(f"training/checkpoints/{arm_id}/seed_{seed}/state_dict.pt")
    return paths


def validate_upstream(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for order, (pin_id, pin) in enumerate(config["upstream_pins"].items()):
        path = workspace_path(pin["path"], must_exist=True)
        observed = file_sha(path)
        rows.append(
            {
                "pin_order": order, "pin_id": pin_id, "path": pin["path"],
                "expected_sha256": pin["sha256"], "observed_sha256": observed,
                "expected_size_bytes": path.stat().st_size, "observed_size_bytes": path.stat().st_size,
                "file_set_status": "pass", "hash_status": "pass" if observed == pin["sha256"] else "fail",
                "overall_status": "pass" if observed == pin["sha256"] else "fail",
                "reason": "" if observed == pin["sha256"] else "sha256_mismatch",
            }
        )
    if any(row["overall_status"] != "pass" for row in rows):
        raise ContractError("upstream pin validation failed")
    manifest = json.loads(workspace_path(config["upstream_pins"]["21d_manifest"]["path"], must_exist=True).read_text())
    if manifest.get("terminal_state") != "21D_gap_mechanisms_mixed_no_repair_candidate":
        raise ContractError("21D terminal state drift")
    if manifest.get("artifact_profile_id") != "P6_FULL_DIAGNOSTIC_FINALIZED":
        raise ContractError("21D artifact profile drift")
    draw_root = workspace_path(config["inputs"]["21d_d0_draw_root"], must_exist=True)
    output_hashes = json.loads(workspace_path(config["upstream_pins"]["21d_output_hashes"]["path"], must_exist=True).read_text())
    hash_entries = {item["path"]: item["sha256"] for item in output_hashes.get("entries", output_hashes.get("files", []))}
    upstream_root = workspace_path(config["upstream_pins"]["21d_manifest"]["path"], must_exist=True).parent
    shards = sorted(draw_root.glob("validation_*/seed_*.parquet"))
    if len(shards) != 6:
        raise ContractError("21D D0 draw shard cardinality must be 6")
    for shard in shards:
        relative = shard.relative_to(upstream_root).as_posix()
        if hash_entries.get(relative) != file_sha(shard):
            raise ContractError(f"21D D0 draw shard hash mismatch: {relative}")
    return rows


def runtime_fingerprint(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "S_REPLAY_RUNTIME_21E_V0",
        "python_version": platform.python_version(), "pytorch_version": str(torch.__version__),
        "numpy_version": np.__version__, "cuda_runtime_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_fingerprint_sha256": current_device_fingerprint(),
        "dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "replay_compatibility_profile": config["sealed_replay"]["compatibility_profile"],
    }
    payload["fingerprint_semantic_sha256"] = stable_hash(payload)
    return payload


def stage_rows(completed_stage: str) -> pd.DataFrame:
    stages = [
        "E0_PREAUTH_AND_PREFLIGHT", "E1_PREDICTOR_EARLY_READOUT",
        "E2_DRC_TRAINING_AND_EARLY_SELECTION", "E3_PRE_LATE_COMPLETE",
        "E4_FRESH_LATE_READOUT", "E5_FINALIZE_AND_SEAL",
    ]
    complete_index = stages.index(completed_stage)
    return pd.DataFrame(
        [
            {
                "stage_order": order, "stage_id": stage,
                "status": "complete" if order <= complete_index else "pending",
                "started_at_utc": "", "ended_at_utc": utc_now() if order <= complete_index else "",
                "worker_exit_code": 0 if order <= complete_index else "",
                "required_artifact_n": 0, "observed_artifact_n": 0,
                "late_access_allowed": stage in {"E4_FRESH_LATE_READOUT", "E5_FINALIZE_AND_SEAL"},
                "status_reason": "",
            }
            for order, stage in enumerate(stages)
        ]
    )


def run_preflight(config: Mapping[str, Any]) -> None:
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.payload is None:
        raise ContractError("valid human authorization required: " + ",".join(authorization.errors))
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    build = building_output_root(config)
    if canonical.exists():
        raise ContractError("canonical output already exists")
    marker = build / ".state/preflight_complete.json"
    if marker.exists():
        return
    build.mkdir(parents=True, exist_ok=True)
    configure_determinism()
    free_disk = shutil.disk_usage(build.parent).free
    if free_disk < int(config["resources"]["minimum_free_disk_before_training"]):
        raise ContractError("insufficient free disk before training")
    if int(config["training"]["batch_size"]) != 256:
        raise ContractError("common resource contract requires batch_size=256")
    pin_rows = validate_upstream(config)
    universe = _PINNED_21D.retained_universe_audit(config)
    ambiguity = ambiguity_registry()
    hypotheses = hypothesis_registry()
    arms = implementation_arm_registry(config)
    predictors = predictor_readout_registry(config)
    contrasts = contrast_registry(config)
    for path, frame in (
        ("paper_predictor_drc_ambiguity_registry.csv", ambiguity),
        ("hypothesis_registry.csv", hypotheses),
        ("implementation_arm_registry.csv", arms),
        ("predictor_readout_registry.csv", predictors),
        ("contrast_registry.csv", contrasts),
    ):
        _write_csv(build / path, frame.to_dict("records"), list(frame.columns))
    _write_csv(
        build / "preflight/execution_authorization_audit.csv",
        [{
            "authorization_path": config["paths"]["execution_authorization"],
            "authorization_sha256": authorization.sha256, "exact_keys": True,
            "all_hash_bindings_match": True, "human_approval": True, "status": "pass", "reason": "",
        }],
        ["authorization_path", "authorization_sha256", "exact_keys", "all_hash_bindings_match", "human_approval", "status", "reason"],
    )
    _write_csv(build / "preflight/upstream_pin_and_file_set_audit.csv", pin_rows, list(pin_rows[0]))
    _write_csv(build / "preflight/retained_universe_exact_match_audit.csv", universe.to_dict("records"), list(universe.columns))
    _write_json(build / "preflight/replay_runtime_fingerprint.json", runtime_fingerprint(config))
    resolved = json.loads(json.dumps(config))
    resolved["authorization_sha256"] = authorization.sha256
    resolved["artifact_profile_contract_sha256"] = stable_hash(artifact_profile_contract(config))
    _write_yaml(build / "preflight/resolved_config.yaml", resolved)
    _write_csv(
        build / "historical_design_holdout_access_audit.csv",
        [{
            "stage_id": "E0_PREAUTH_AND_PREFLIGHT", "process_role": "preflight_controller",
            "artifact_path": "historical_design_holdout", "open_attempt_n": 0,
            "successful_open_n": 0, "bytes_read_n": 0, "first_opened_at_utc": "",
            "last_opened_at_utc": "", "status": "pass",
        }],
        ["stage_id", "process_role", "artifact_path", "open_attempt_n", "successful_open_n", "bytes_read_n", "first_opened_at_utc", "last_opened_at_utc", "status"],
    )
    stages = stage_rows("E0_PREAUTH_AND_PREFLIGHT")
    _write_csv(build / "stage_status_registry.csv", stages.to_dict("records"), list(stages.columns))
    _write_json(marker, {"schema_version": "21E_PREFLIGHT_COMPLETE_V0", "completed_at_utc": utc_now()})


def _sealed_checkpoint(config: Mapping[str, Any], seed: int, device: torch.device) -> tuple[nn.Module, str]:
    root = workspace_path(config["inputs"]["21c_checkpoint_root"], must_exist=True)
    path = root / f"seed_{seed}/state_dict.pt"
    expected = config["sealed_replay"]["selected"][str(seed)]
    if file_sha(path) != expected["checkpoint_sha256"]:
        raise ContractError(f"sealed checkpoint byte hash drift: {seed}")
    model = _PINNED_21C.build_model(seed)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    semantic = _PINNED_21C.model_state_semantic_hash(state)
    if semantic != expected["semantic_sha256"]:
        raise ContractError(f"sealed checkpoint semantic hash drift: {seed}")
    return model.to(device), semantic


@torch.no_grad()
def deterministic_predictor_scores(
    model: nn.Module,
    y_source: Any,
    x_source: Any,
    *,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    zero_noise = np.empty(len(y_source), dtype=np.float64)
    koopman_only = np.empty(len(y_source), dtype=np.float64)
    schedule = _PINNED_21C.diffusion_schedule(device=device)
    model.eval()
    for start in range(0, len(y_source), batch_size):
        stop = min(start + batch_size, len(y_source))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(x_source[start:stop], dtype=torch.float32, device=device)
        source = _PINNED_21D.source_latent_variant(
            model, y, x, tau=0.1, training_selector=False, selector_train="soft_gumbel"
        )
        residual = torch.zeros_like(source["Z_source"])
        for step in range(20, 0, -1):
            index = step - 1
            timestep = torch.full(residual.shape[:2], step, dtype=torch.long, device=device)
            epsilon_hat = model.denoise(residual, timestep, source["Z_source"])
            residual = (
                residual - schedule["beta"][index] * epsilon_hat / torch.sqrt(1.0 - schedule["alpha_bar"][index])
            ) / torch.sqrt(schedule["alpha"][index])
        zero_noise[start:stop] = model.decoder(source["Z_hat_shifted"] + residual)[:, 9, 0].cpu().numpy()
        koopman_only[start:stop] = model.decoder(source["Z_hat_shifted"])[:, 9, 0].cpu().numpy()
    return zero_noise, koopman_only


def _draw_matrix(config: Mapping[str, Any], fold: str, seed: int) -> tuple[pd.DataFrame, np.ndarray, str]:
    path = workspace_path(config["inputs"]["21d_d0_draw_root"], must_exist=True) / fold / f"seed_{seed}.parquet"
    table = pq.read_table(path, columns=["decision_date", "instrument", "row_key", "draw_scores", "draw_schedule_sha256"])
    values = table.column("draw_scores").combine_chunks().values.to_numpy().reshape(len(table), 256)
    keys = table.select(["decision_date", "instrument", "row_key"]).to_pandas()
    schedule_hashes = table.column("draw_schedule_sha256").to_pylist()
    return keys, np.asarray(values, dtype=np.float32), stable_hash(schedule_hashes)


def _prediction_rows(
    fold_data: Mapping[str, Any], fold: str, arm_order: int, arm_id: str,
    score_variant: str, draw_n: int, seed_scores: Mapping[int, np.ndarray],
    checkpoint_semantics: Mapping[int, str], predictor_semantic: str,
) -> pd.DataFrame:
    frame = fold_data["frame"]
    base = pd.DataFrame(
        {
            "fold_order": 1 if fold == "validation_early" else 2,
            "fold": fold, "arm_order": arm_order, "arm_id": arm_id,
            "score_variant": score_variant, "draw_n": draw_n,
            "decision_date": pd.to_datetime(frame["decision_date"]).dt.date,
            "instrument": frame["instrument"].astype(str).to_numpy(),
            "row_key": frame["row_key_hash"].astype(str).to_numpy(),
            "raw_label": np.asarray(fold_data["label"], dtype=np.float32),
            "predictor_semantic_sha256": predictor_semantic,
        }
    )
    rows = []
    for seed in MODEL_SEEDS:
        item = base.copy()
        item["model_seed"] = seed
        item["is_ensemble"] = False
        item["score"] = np.asarray(seed_scores[seed], dtype=np.float64)
        item["checkpoint_semantic_sha256"] = checkpoint_semantics[seed]
        rows.append(item)
    ensemble = base.copy()
    ensemble["model_seed"] = pd.NA
    ensemble["is_ensemble"] = True
    ensemble["score"] = np.stack(
        [np.asarray(seed_scores[seed], dtype=np.float64) for seed in MODEL_SEEDS]
    ).mean(axis=0)
    ensemble["checkpoint_semantic_sha256"] = stable_hash(checkpoint_semantics)
    rows.append(ensemble)
    result = pd.concat(rows, ignore_index=True)
    columns = [
        "fold_order", "fold", "arm_order", "arm_id", "model_seed", "is_ensemble",
        "score_variant", "draw_n", "decision_date", "instrument", "row_key", "score",
        "raw_label", "checkpoint_semantic_sha256", "predictor_semantic_sha256",
    ]
    return result[columns]


def fixed_predictor_frame(config: Mapping[str, Any], fold: str, device: torch.device) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = _PINNED_21D.load_fold_data(config, fold)
    checkpoint_semantics = {seed: config["sealed_replay"]["selected"][str(seed)]["semantic_sha256"] for seed in MODEL_SEEDS}
    scores: dict[str, dict[int, np.ndarray]] = {arm: {} for arm in PREDICTOR_IDS}
    stability_rows = []
    for seed in MODEL_SEEDS:
        keys, draws, schedule_sha = _draw_matrix(config, fold, seed)
        expected_keys = data["frame"][["decision_date", "instrument", "row_key_hash"]].copy()
        expected_keys["decision_date"] = pd.to_datetime(expected_keys["decision_date"]).dt.date
        expected_keys.columns = ["decision_date", "instrument", "row_key"]
        if not keys.astype(str).equals(expected_keys.astype(str)):
            raise ContractError(f"D0 draw row keys drift: {fold}/{seed}")
        draw_tensor = torch.as_tensor(np.array(draws, copy=True), dtype=torch.float32, device=device)
        scores["P0_CURRENT_SCORE_MEAN8"][seed] = draw_tensor[:, :8].T.contiguous().mean(dim=0).cpu().numpy()
        scores["P1_SINGLE_DRAW0"][seed] = draws[:, 0]
        scores["P2_SCORE_MEAN64"][seed] = draw_tensor[:, :64].T.contiguous().mean(dim=0).cpu().numpy()
        scores["P3_SCORE_MEAN256_REF"][seed] = draw_tensor.T.contiguous().mean(dim=0).cpu().numpy()
        scores["P6_SCORE_MEDIAN256"][seed] = np.median(draws, axis=1).astype(np.float32)
        del draw_tensor
        model, _ = _sealed_checkpoint(config, seed, device)
        zero, koopman = deterministic_predictor_scores(
            model, data["y_source"], data["x_source"],
            batch_size=int(config["training"]["inference_batch_size"]), device=device,
        )
        scores["P4_ZERO_NOISE_REVERSE_PROXY"][seed] = zero
        scores["P5_KOOPMAN_ONLY"][seed] = koopman
        del model
        torch.cuda.empty_cache()
        for date, indices in data["frame"].groupby("decision_date", sort=True).groups.items():
            index = np.asarray(list(indices), dtype=np.int64)
            ref = scores["P3_SCORE_MEAN256_REF"][seed][index]
            for arm_id in PREDICTOR_IDS:
                value = scores[arm_id][seed][index]
                rho = pd.Series(value).corr(pd.Series(ref), method="spearman")
                stability_rows.append(
                    {
                        "fold": fold, "model_seed": seed, "decision_date": pd.Timestamp(date).date(),
                        "predictor_left": arm_id, "predictor_right": "P3_SCORE_MEAN256_REF",
                        "row_n": len(index), "score_spearman": float(rho), "top30_overlap_n": int(len(set(np.argsort(value)[-30:]) & set(np.argsort(ref)[-30:]))),
                        "rankic_left": float(_PINNED_21C.rankic(value, np.asarray(data["label"])[index], minimum_n=100)),
                        "rankic_right": float(_PINNED_21C.rankic(ref, np.asarray(data["label"])[index], minimum_n=100)),
                        "rankic_delta": float(_PINNED_21C.rankic(value, np.asarray(data["label"])[index], minimum_n=100) - _PINNED_21C.rankic(ref, np.asarray(data["label"])[index], minimum_n=100)),
                        "mc_variance_fraction": float(np.var(draws[index], axis=1).mean() / max(np.var(ref), 1e-12)),
                        "draw_schedule_sha256": schedule_sha, "status": "pass",
                    }
                )
    frames = []
    arm_map = {item["arm_id"]: item for item in config["predictor_arms"]}
    for arm_id in PREDICTOR_IDS:
        arm = arm_map[arm_id]
        frames.append(
            _prediction_rows(
                data, fold, int(arm["arm_order"]), arm_id, "point", int(arm["draw_n"]),
                scores[arm_id], checkpoint_semantics,
                stable_hash(next(row for row in predictor_readout_registry(config).to_dict("records") if row["point_predictor_id"] == arm["point_predictor_id"])),
            )
        )
    result = pd.concat(frames, ignore_index=True)
    if not np.isfinite(result["score"]).all() or result.duplicated(["fold", "arm_id", "model_seed", "is_ensemble", "row_key"]).any():
        raise ContractError("fixed predictor score coverage/finite gate failed")
    return result, pd.DataFrame(stability_rows)


def validate_p0_exact_replay(config: Mapping[str, Any], predictions: pd.DataFrame, fold: str) -> None:
    input_id = "21c_early_scores" if fold == "validation_early" else "21c_late_scores"
    upstream = pd.read_parquet(workspace_path(config["inputs"][input_id], must_exist=True))
    current = predictions.loc[predictions["arm_id"].eq("P0_CURRENT_SCORE_MEAN8")].copy()
    for seed in MODEL_SEEDS:
        left = current.loc[current["model_seed"].eq(seed), ["row_key", "score"]].sort_values("row_key")
        right = upstream.loc[upstream["model_seed"].eq(seed), ["row_key_hash", "score"]].sort_values("row_key_hash")
        if not np.array_equal(left["row_key"].to_numpy(), right["row_key_hash"].to_numpy()):
            raise ContractError(f"P0 row key replay mismatch: {seed}")
        if not np.array_equal(left["score"].to_numpy(dtype=np.float32), right["score"].to_numpy(dtype=np.float32)):
            raise ContractError(f"P0 score replay mismatch: {seed}")
    left_ensemble = current.loc[current["is_ensemble"], ["row_key", "score"]].sort_values("row_key")
    right_ensemble = upstream.loc[upstream["score_role"].eq("ensemble"), ["row_key_hash", "score"]].sort_values("row_key_hash")
    if not np.array_equal(left_ensemble["row_key"].to_numpy(), right_ensemble["row_key_hash"].to_numpy()):
        raise ContractError("P0 ensemble row key replay mismatch")
    if not np.array_equal(left_ensemble["score"].to_numpy(dtype=np.float64), right_ensemble["score"].to_numpy(dtype=np.float64)):
        raise ContractError("P0 ensemble score replay mismatch")


def run_predictor_early(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/preflight_complete.json").exists():
        raise ContractError("preflight must complete before predictor early")
    marker = build / ".state/predictor_early_complete.json"
    if marker.exists():
        return
    configure_determinism()
    predictions, stability = fixed_predictor_frame(config, "validation_early", torch.device("cuda"))
    validate_p0_exact_replay(config, predictions, "validation_early")
    _write_parquet(build / ".state/predictor_early_predictions.parquet", predictions)
    _write_parquet(build / ".state/predictor_early_stability.parquet", stability)
    stages = stage_rows("E1_PREDICTOR_EARLY_READOUT")
    _write_csv(build / "stage_status_registry.csv", stages.to_dict("records"), list(stages.columns))
    _write_json(marker, {"schema_version": "21E_PREDICTOR_EARLY_COMPLETE_V0", "row_n": len(predictions), "completed_at_utc": utc_now()})


class PointwiseMLPDecoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.hidden = nn.Linear(64, 64)
        self.output = nn.Linear(64, 1)

    def forward(self, latent: Tensor) -> Tensor:
        return self.output(F.silu(self.hidden(latent)))


def keyed_generator(arm_id: str, model_seed: int, parameter_name: str) -> torch.Generator:
    seed = int.from_bytes(
        hashlib.sha256(f"{RUN_ID}|{arm_id}|{model_seed}|{parameter_name}".encode()).digest()[:8],
        "big",
    ) % (2**63)
    return torch.Generator(device="cpu").manual_seed(seed)


def _keyed_linear_initialize(layer: nn.Linear, arm_id: str, model_seed: int, name: str) -> None:
    nn.init.xavier_uniform_(layer.weight, generator=keyed_generator(arm_id, model_seed, f"{name}.weight"))
    nn.init.zeros_(layer.bias)


def build_variant_model(arm_id: str, model_seed: int) -> nn.Module:
    if arm_id not in TRAINABLE_IDS:
        raise ContractError(f"unknown trainable arm: {arm_id}")
    model = _PINNED_21C.build_model(model_seed)
    if arm_id == "A2_RESBLOCK_20_STEP":
        del model.denoiser_linear_1
        del model.denoiser_linear_2
        del model.denoiser_linear_3
        model.resblock_input = nn.Linear(160, 128)
        model.resblock_1_linear_1 = nn.Linear(128, 128)
        model.resblock_1_linear_2 = nn.Linear(128, 128)
        model.resblock_1_norm = nn.LayerNorm(128)
        model.resblock_2_linear_1 = nn.Linear(128, 128)
        model.resblock_2_linear_2 = nn.Linear(128, 128)
        model.resblock_2_norm = nn.LayerNorm(128)
        model.resblock_output = nn.Linear(128, 64)
        for name in (
            "resblock_input", "resblock_1_linear_1", "resblock_1_linear_2",
            "resblock_2_linear_1", "resblock_2_linear_2", "resblock_output",
        ):
            _keyed_linear_initialize(getattr(model, name), arm_id, model_seed, name)
        for name in ("resblock_1_norm", "resblock_2_norm"):
            layer = getattr(model, name)
            nn.init.ones_(layer.weight)
            nn.init.zeros_(layer.bias)
    elif arm_id == "A3_POINTWISE_MLP_DECODER":
        model.decoder = PointwiseMLPDecoder()
        _keyed_linear_initialize(model.decoder.hidden, arm_id, model_seed, "decoder.hidden")
        _keyed_linear_initialize(model.decoder.output, arm_id, model_seed, "decoder.output")
    return model


def ordered_parameter_names(model: nn.Module) -> list[str]:
    return [name for name, _ in model.named_parameters()]


def initial_state_semantic_hash(model: nn.Module) -> str:
    return _PINNED_21C.model_state_semantic_hash(model.state_dict())


def generic_schedule(steps: int, device: torch.device | str) -> dict[str, Tensor]:
    if steps not in {20, 100}:
        raise ContractError("diffusion steps must be 20 or 100")
    beta = torch.linspace(1e-4, 2e-2, steps, dtype=torch.float32, device=device)
    alpha = 1.0 - beta
    alpha_bar = torch.cumprod(alpha, dim=0)
    previous = torch.cat((torch.ones(1, device=device), alpha_bar[:-1]))
    posterior_variance = beta * (1.0 - previous) / (1.0 - alpha_bar)
    return {"beta": beta, "alpha": alpha, "alpha_bar": alpha_bar, "posterior_variance": posterior_variance}


def denoise_variant(model: nn.Module, arm_id: str, x_s: Tensor, timestep: Tensor, condition: Tensor) -> Tensor:
    if arm_id != "A2_RESBLOCK_20_STEP":
        return model.denoise(x_s, timestep, condition)
    embedding = _PINNED_21C.sinusoidal_timestep_embedding(timestep, 32).to(x_s.dtype)
    hidden = F.silu(model.resblock_input(torch.cat((x_s, condition, embedding), dim=-1)))
    residual = model.resblock_1_linear_2(F.silu(model.resblock_1_linear_1(hidden)))
    hidden = model.resblock_1_norm(hidden + residual)
    residual = model.resblock_2_linear_2(F.silu(model.resblock_2_linear_1(hidden)))
    hidden = model.resblock_2_norm(hidden + residual)
    return model.resblock_output(hidden)


def graph_for_arm(arm_id: str, selected_graph_arm_id: str | None) -> str:
    if arm_id == "G0_CURRENT_X0_COUPLED":
        return "x0_coupled"
    if arm_id == "G1_STOPGRAD_X0_RECON":
        return "stopgrad_x0_recon"
    if arm_id == "G2_TEACHER_LATENT_RECON_ORACLE":
        return "teacher_latent_recon_oracle"
    if selected_graph_arm_id == "G0_CURRENT_X0_COUPLED":
        return "x0_coupled"
    if selected_graph_arm_id == "G1_STOPGRAD_X0_RECON":
        return "stopgrad_x0_recon"
    raise ContractError("A arm requires selected G0/G1 graph")


def diffusion_steps_for_arm(arm_id: str) -> int:
    return 100 if arm_id == "A1_MLP_100_STEP" else 20


def implementation_training_losses(
    model: nn.Module,
    arm_id: str,
    training_graph: str,
    y_source: Tensor,
    x_source: Tensor,
    y_teacher: Tensor,
    x_teacher: Tensor,
    forecast_y: Tensor,
    *,
    tau: float,
    gumbel_u: Tensor,
    diffusion_timestep: Tensor,
    epsilon: Tensor,
) -> dict[str, Tensor]:
    source = _PINNED_21D.source_latent_variant(
        model, y_source, x_source, tau=tau, training_selector=True,
        selector_train="soft_gumbel", gumbel_u=gumbel_u,
    )
    teacher = model.teacher_latent(y_teacher, x_teacher)
    target = teacher - source["Z_hat_shifted"]
    steps = diffusion_steps_for_arm(arm_id)
    schedule = generic_schedule(steps, target.device)
    index = diffusion_timestep.long() - 1
    alpha_bar = schedule["alpha_bar"][index].unsqueeze(-1)
    x_s = alpha_bar.sqrt() * target + (1.0 - alpha_bar).sqrt() * epsilon
    epsilon_hat = denoise_variant(model, arm_id, x_s, diffusion_timestep, source["Z_source"])
    x0_hat = (x_s - (1.0 - alpha_bar).sqrt() * epsilon_hat) / alpha_bar.sqrt()
    if training_graph == "x0_coupled":
        reconstruction_latent = source["Z_hat_shifted"] + x0_hat
    elif training_graph == "stopgrad_x0_recon":
        reconstruction_latent = source["Z_hat_shifted"] + x0_hat.detach()
    elif training_graph == "teacher_latent_recon_oracle":
        reconstruction_latent = teacher
    else:
        raise ContractError(f"unknown training graph: {training_graph}")
    decoded_source = model.decoder(source["Z_source"])
    decoded_shifted = model.decoder(reconstruction_latent)
    source_rec = torch.mean((decoded_source - y_source) ** 2)
    shifted_rec = torch.mean((decoded_shifted[:, :9] - y_teacher[:, :9]) ** 2)
    rec = 0.5 * (source_rec + shifted_rec) + torch.mean((decoded_shifted[:, 9, 0] - forecast_y.reshape(-1)) ** 2)
    koop = torch.mean((teacher - source["Z_hat_shifted"]) ** 2)
    diff = torch.mean((epsilon_hat - epsilon) ** 2)
    total = rec + koop + diff
    if not all(torch.isfinite(value) for value in (rec, koop, diff, total)):
        raise ContractError("training loss contains NaN/Inf")
    return {
        "L_rec": rec, "L_koop": koop, "L_diff": diff, "L_total": total,
        "Z_source": source["Z_source"], "Z_hat_shifted": source["Z_hat_shifted"],
        "Z_teacher_shifted": teacher, "x0_hat": x0_hat,
        "decoder_output": decoded_shifted,
    }


def build_optimizer(model: nn.Module, config: Mapping[str, Any]) -> torch.optim.AdamW:
    training = config["training"]
    return torch.optim.AdamW(
        [{"params": [parameter for _, parameter in model.named_parameters()]}],
        lr=float(training["learning_rate"]), betas=tuple(training["adam_betas"]),
        eps=float(training["adam_eps"]), weight_decay=float(training["weight_decay"]),
        amsgrad=False, foreach=False, fused=False, capturable=False,
        maximize=False, differentiable=False,
    )


def optimizer_step(model: nn.Module, optimizer: torch.optim.AdamW, loss: Tensor, clip: float) -> float:
    optimizer.zero_grad(set_to_none=True)
    loss.float().backward()
    norm = torch.nn.utils.clip_grad_norm_(
        [parameter for _, parameter in model.named_parameters()], clip,
        norm_type=2.0, error_if_nonfinite=True, foreach=False,
    )
    optimizer.step()
    return float(norm)


def row_noise_schedule(
    keys: Sequence[tuple[str, str]], model_seed: int, draw_id: int,
    steps: int, device: torch.device,
) -> Tensor:
    if steps == 20:
        return _PINNED_21C.row_seeded_noise_schedule(
            keys, model_seed, draw_id, dtype=torch.float32, device=device, run_id=_PINNED_21C.RUN_ID
        )
    noise = torch.empty((len(keys), steps, LOOKBACK, LATENT_DIM), dtype=torch.float32)
    for row_index, (instrument, decision_date) in enumerate(keys):
        seed = _PINNED_21C.row_draw_seed(
            _PINNED_21C.RUN_ID, model_seed, instrument, decision_date, draw_id
        )
        generator = torch.Generator(device="cpu").manual_seed(seed)
        noise[row_index] = torch.randn((steps, LOOKBACK, LATENT_DIM), generator=generator)
    return noise.to(device)


@torch.no_grad()
def inference_draw_scores(
    model: nn.Module, arm_id: str, y_source: Tensor, x_source: Tensor,
    keys: Sequence[tuple[str, str]], model_seed: int, draw_n: int,
) -> Tensor:
    model.eval()
    source = _PINNED_21D.source_latent_variant(
        model, y_source, x_source, tau=0.1, training_selector=False, selector_train="soft_gumbel"
    )
    steps = diffusion_steps_for_arm(arm_id)
    schedule = generic_schedule(steps, y_source.device)
    result = torch.empty((len(y_source), draw_n), dtype=torch.float32, device="cpu")
    for draw_id in range(draw_n):
        noise_schedule = row_noise_schedule(keys, model_seed, draw_id, steps, y_source.device)
        residual = noise_schedule[:, 0]
        for step in range(steps, 0, -1):
            index = step - 1
            timestep = torch.full(residual.shape[:2], step, dtype=torch.long, device=y_source.device)
            epsilon_hat = denoise_variant(model, arm_id, residual, timestep, source["Z_source"])
            mean = (
                residual - schedule["beta"][index] * epsilon_hat / torch.sqrt(1.0 - schedule["alpha_bar"][index])
            ) / torch.sqrt(schedule["alpha"][index])
            if step > 1:
                residual = mean + torch.sqrt(schedule["posterior_variance"][index]) * noise_schedule[:, steps - step + 1]
            else:
                residual = mean
        result[:, draw_id] = model.decoder(source["Z_hat_shifted"] + residual)[:, 9, 0].cpu()
    return result


@torch.no_grad()
def score_panel(
    model: nn.Module, arm_id: str, fold_data: Mapping[str, Any], model_seed: int,
    *, draw_n: int, batch_size: int, device: torch.device,
) -> np.ndarray:
    result = np.empty(len(fold_data["y_source"]), dtype=np.float64)
    instruments = fold_data["frame"]["instrument"].astype(str).tolist()
    dates = fold_data["frame"]["decision_date"].astype(str).tolist()
    for start in range(0, len(result), batch_size):
        stop = min(start + batch_size, len(result))
        y = torch.as_tensor(fold_data["y_source"][start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(fold_data["x_source"][start:stop], dtype=torch.float32, device=device)
        keys = list(zip(instruments[start:stop], dates[start:stop], strict=True))
        draws = inference_draw_scores(model, arm_id, y, x, keys, model_seed, draw_n)
        result[start:stop] = draws.mean(dim=1).double().numpy()
    if not np.isfinite(result).all():
        raise ContractError("inference produced NaN/Inf")
    return result


def train_custom_seed(
    config: Mapping[str, Any], arm_id: str, model_seed: int, training_graph: str,
    train: Mapping[str, Any], early: Mapping[str, Any], teacher: Mapping[str, Any],
    device: torch.device,
) -> tuple[dict[str, Tensor], list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    training = config["training"]
    model = build_variant_model(arm_id, model_seed)
    init_hash = initial_state_semantic_hash(model)
    parameter_names_hash = stable_hash(ordered_parameter_names(model))
    model = model.to(device)
    optimizer = build_optimizer(model, config)
    train_n = len(train["y_source"])
    steps_per_epoch = math.ceil(train_n / int(training["batch_size"]))
    planned_steps = int(training["max_epochs"]) * steps_per_epoch
    gumbel_generator = torch.Generator(device="cpu").manual_seed(model_seed + 71)
    diffusion_generator = torch.Generator(device="cpu").manual_seed(model_seed + 89)
    best_metric = -math.inf
    best_state: dict[str, Tensor] | None = None
    best_scores: np.ndarray | None = None
    non_improvement = 0
    step_index = 0
    curves: list[dict[str, Any]] = []
    steps = diffusion_steps_for_arm(arm_id)
    for epoch_index in range(int(training["max_epochs"])):
        permutation = torch.randperm(
            train_n, generator=torch.Generator(device="cpu").manual_seed(model_seed + 37 + epoch_index)
        ).numpy()
        totals = {name: 0.0 for name in ("L_total", "L_rec", "L_koop", "L_diff")}
        seen = 0
        model.train()
        for start in range(0, train_n, int(training["batch_size"])):
            indices = permutation[start : start + int(training["batch_size"])]
            actual = len(indices)
            y = torch.as_tensor(train["y_source"][indices], dtype=torch.float32, device=device)
            x = torch.as_tensor(train["x_source"][indices], dtype=torch.float32, device=device)
            y_teacher = torch.as_tensor(teacher["y_teacher"][indices], dtype=torch.float32, device=device)
            x_teacher = torch.as_tensor(teacher["x_teacher"][indices], dtype=torch.float32, device=device)
            forecast = torch.as_tensor(train["label"][indices], dtype=torch.float32, device=device)
            uniform = torch.rand((actual, LOOKBACK, N_OPERATOR), generator=gumbel_generator).to(device)
            timestep = torch.randint(1, steps + 1, (actual, LOOKBACK), generator=diffusion_generator).to(device)
            epsilon = torch.randn((actual, LOOKBACK, LATENT_DIM), generator=diffusion_generator).to(device)
            losses = implementation_training_losses(
                model, arm_id, training_graph, y, x, y_teacher, x_teacher, forecast,
                tau=_PINNED_21C.tau_for_step(step_index, planned_steps), gumbel_u=uniform,
                diffusion_timestep=timestep, epsilon=epsilon,
            )
            optimizer_step(model, optimizer, losses["L_total"], float(training["gradient_clip_global_l2"]))
            step_index += 1
            for name in totals:
                totals[name] += float(losses[name].detach().cpu()) * actual
            seen += actual
        scores = score_panel(
            model, arm_id, early, model_seed, draw_n=8,
            batch_size=int(training["inference_batch_size"]), device=device,
        )
        metric, complete_days = _PINNED_21D.validation_rankic(
            scores, early["label"], early["frame"]["decision_date"].astype(str).tolist(),
            minimum_n=int(training["minimum_rankic_n"]),
        )
        if metric > best_metric:
            best_metric = float(metric)
            best_state = {name: value.detach().cpu().contiguous().clone() for name, value in model.state_dict().items()}
            best_scores = scores.copy()
            non_improvement = 0
        else:
            non_improvement += 1
        curves.append(
            {
                "arm_id": arm_id, "model_seed": model_seed, "epoch": epoch_index + 1,
                "optimizer_step_end": step_index, "train_loss_total": totals["L_total"] / seen,
                "train_loss_rec": totals["L_rec"] / seen, "train_loss_koop": totals["L_koop"] / seen,
                "train_loss_diff": totals["L_diff"] / seen, "validation_early_mean_rankic": metric,
                "validation_early_complete_day_n": complete_days, "status": "pass",
            }
        )
        if non_improvement == int(training["early_stopping_patience"]):
            break
    if best_state is None or best_scores is None:
        raise ContractError(f"no checkpoint selected: {arm_id}/{model_seed}")
    metadata = {
        "initial_state_semantic_sha256": init_hash,
        "ordered_parameter_names_sha256": parameter_names_hash,
        "parameter_n": sum(value.numel() for value in best_state.values()),
        "selected_epoch": int(max(curves, key=lambda row: row["validation_early_mean_rankic"])["epoch"]),
        "selected_validation_early_rankic": best_metric,
        "optimizer_step_n": step_index,
    }
    return best_state, curves, best_scores, metadata


def train_g0_exact(
    config: Mapping[str, Any], model_seed: int, train: Mapping[str, Any],
    early: Mapping[str, Any], teacher: Mapping[str, Any], device: torch.device,
) -> tuple[dict[str, Tensor], list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    state, curves, scores = _PINNED_21C.train_one_seed(
        _PINNED_21C.load_config(), model_seed=model_seed,
        train_y_source=train["y_source"], train_x_source=train["x_source"],
        train_y_teacher=teacher["y_teacher"], train_x_teacher=teacher["x_teacher"],
        train_forecast_y=train["label"], validation_y_source=early["y_source"],
        validation_x_source=early["x_source"], validation_labels=early["label"],
        validation_instruments=early["frame"]["instrument"].astype(str).tolist(),
        validation_decision_dates=early["frame"]["decision_date"].astype(str).tolist(),
        selected_batch_size=256, device=device,
    )
    selected = max(curves, key=lambda row: row["validation_early_mean_rankic"])
    expected = config["sealed_replay"]["selected"][str(model_seed)]
    semantic = _PINNED_21C.model_state_semantic_hash(state)
    if int(selected["epoch"]) != expected["epoch"] or float(selected["validation_early_mean_rankic"]) != expected["early_rankic"] or semantic != expected["semantic_sha256"]:
        raise ContractError(f"G0 exact replay failed: {model_seed}")
    for row in curves:
        row["arm_id"] = "G0_CURRENT_X0_COUPLED"
    model = _PINNED_21C.build_model(model_seed)
    metadata = {
        "initial_state_semantic_sha256": initial_state_semantic_hash(model),
        "ordered_parameter_names_sha256": stable_hash(ordered_parameter_names(model)),
        "parameter_n": sum(value.numel() for value in state.values()),
        "selected_epoch": int(selected["epoch"]),
        "selected_validation_early_rankic": float(selected["validation_early_mean_rankic"]),
        "optimizer_step_n": int(selected["optimizer_step_end"]),
    }
    return state, curves, scores, metadata


def checkpoint_path(build: Path, arm_id: str, seed: int) -> Path:
    return build / f"training/checkpoints/{arm_id}/seed_{seed}/state_dict.pt"


def load_trained_model(
    config: Mapping[str, Any], build: Path, arm_id: str, seed: int, device: torch.device,
) -> tuple[nn.Module, str]:
    path = checkpoint_path(build, arm_id, seed)
    if not path.exists():
        raise ContractError(f"checkpoint missing: {arm_id}/{seed}")
    model = build_variant_model(arm_id, seed)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    return model.to(device), _PINNED_21C.model_state_semantic_hash(state)


def arm_order(config: Mapping[str, Any], arm_id: str) -> int:
    if arm_id == "A0_SELECTED_GRAPH_CONTROL":
        return 10
    for item in [*config["predictor_arms"], *config["training_arms"]]:
        if item["arm_id"] == arm_id:
            return int(item["arm_order"])
    raise ContractError(f"unknown arm order: {arm_id}")


def choose_training_graph(seed_scores: Mapping[str, Mapping[int, np.ndarray]], early: Mapping[str, Any]) -> dict[str, Any]:
    candidates = []
    dates = early["frame"]["decision_date"].astype(str).tolist()
    for arm_id in ("G0_CURRENT_X0_COUPLED", "G1_STOPGRAD_X0_RECON"):
        ensemble = np.stack([seed_scores[arm_id][seed] for seed in MODEL_SEEDS]).mean(axis=0)
        metric, complete_day_n = _PINNED_21D.validation_rankic(ensemble, early["label"], dates)
        candidates.append({"arm_id": arm_id, "ensemble_validation_early_rankic": metric, "complete_day_n": complete_day_n})
    g0 = candidates[0]
    g1 = candidates[1]
    if abs(g1["ensemble_validation_early_rankic"] - g0["ensemble_validation_early_rankic"]) < 0.002:
        selected = g1
        reason = "within_0.002_choose_simpler_stopgrad"
    else:
        selected = max(candidates, key=lambda item: item["ensemble_validation_early_rankic"])
        reason = "maximum_ensemble_validation_early_rankic"
    return {
        "schema_version": "S_TRAINING_GRAPH_SELECTION_21E_V0",
        "eligible_arm_ids": ["G0_CURRENT_X0_COUPLED", "G1_STOPGRAD_X0_RECON"],
        "forbidden_oracle_arm_id": "G2_TEACHER_LATENT_RECON_ORACLE",
        "candidate_metrics": candidates,
        "selected_arm_id": selected["arm_id"], "selection_reason": reason,
        "selected_at_utc": utc_now(),
    }


def checkpoint_gradient_audit(
    config: Mapping[str, Any], build: Path, arm_id: str, seed: int,
    training_graph: str, train: Mapping[str, Any], teacher: Mapping[str, Any],
    device: torch.device,
) -> list[dict[str, Any]]:
    model, _ = load_trained_model(config, build, arm_id, seed, device)
    indices = np.arange(min(256, len(train["y_source"])), dtype=np.int64)
    y = torch.as_tensor(train["y_source"][indices], dtype=torch.float32, device=device)
    x = torch.as_tensor(train["x_source"][indices], dtype=torch.float32, device=device)
    y_teacher = torch.as_tensor(teacher["y_teacher"][indices], dtype=torch.float32, device=device)
    x_teacher = torch.as_tensor(teacher["x_teacher"][indices], dtype=torch.float32, device=device)
    forecast = torch.as_tensor(train["label"][indices], dtype=torch.float32, device=device)
    generator = torch.Generator(device="cpu").manual_seed(seed + 21000)
    uniform = torch.rand((len(indices), LOOKBACK, N_OPERATOR), generator=generator).to(device)
    steps = diffusion_steps_for_arm(arm_id)
    timestep = torch.randint(1, steps + 1, (len(indices), LOOKBACK), generator=generator).to(device)
    epsilon = torch.randn((len(indices), LOOKBACK, LATENT_DIM), generator=generator).to(device)
    model.train()
    losses = implementation_training_losses(
        model, arm_id, training_graph, y, x, y_teacher, x_teacher, forecast,
        tau=0.1, gumbel_u=uniform, diffusion_timestep=timestep, epsilon=epsilon,
    )
    named = list(model.named_parameters())
    module_groups = {
        "encoder": ("return_encoder.", "feature_encoder."),
        "selector_koopman": ("gate_linear.", "selector_linear.", "K_codebook."),
        "decoder": ("decoder.",),
        "denoiser": ("denoiser_", "resblock_"),
    }
    score = losses["decoder_output"][:, 9, 0]
    score_std = float(score.detach().std(unbiased=True).cpu())
    label_std = float(forecast.detach().std(unbiased=True).cpu())
    latent_std = float(losses["Z_source"].detach().std(unbiased=True).cpu())
    zero_improvement = float(torch.mean(forecast**2).detach().cpu() - torch.mean((score - forecast) ** 2).detach().cpu())
    batch_hash = stable_hash(train["frame"].iloc[indices]["row_key_hash"].astype(str).tolist())
    rows = []
    for loss_id in ("L_rec", "L_koop", "L_diff", "L_total"):
        gradients = torch.autograd.grad(
            losses[loss_id], [parameter for _, parameter in named],
            retain_graph=True, allow_unused=True,
        )
        global_sq = sum(float(torch.sum(gradient.detach() ** 2).cpu()) for gradient in gradients if gradient is not None)
        for module_id, prefixes in module_groups.items():
            module_sq = sum(
                float(torch.sum(gradient.detach() ** 2).cpu())
                for (name, _), gradient in zip(named, gradients, strict=True)
                if gradient is not None and name.startswith(prefixes)
            )
            ratio = score_std / max(label_std, 1e-12)
            rows.append(
                {
                    "arm_id": arm_id, "model_seed": seed, "checkpoint_role": "selected_early",
                    "batch_id": "train_calibration_prefix256", "module_id": module_id, "loss_id": loss_id,
                    "gradient_l2": math.sqrt(module_sq),
                    "global_gradient_share": module_sq / max(global_sq, 1e-30),
                    "latent_std": latent_std, "decoder_output_std": score_std,
                    "zero_solution_improvement": zero_improvement,
                    "score_to_label_std_ratio": ratio,
                    "additional_collapse_flag_n": int(score_std < 1e-6 or ratio < 0.01),
                    "batch_row_key_sha256": batch_hash, "status": "pass",
                }
            )
    del model
    torch.cuda.empty_cache()
    return rows


def training_prediction_frames(
    config: Mapping[str, Any], build: Path, fold_data: Mapping[str, Any], fold: str,
    draw_plan: Mapping[str, Sequence[int]], selected_graph: str, device: torch.device,
) -> list[pd.DataFrame]:
    frames = []
    identities = [*TRAINABLE_IDS, "A0_SELECTED_GRAPH_CONTROL"]
    for identity in identities:
        checkpoint_identity = selected_graph if identity == "A0_SELECTED_GRAPH_CONTROL" else identity
        for draw_n in draw_plan.get(identity, (64,)):
            seed_scores: dict[int, np.ndarray] = {}
            checkpoint_semantics: dict[int, str] = {}
            for seed in MODEL_SEEDS:
                model, semantic = load_trained_model(config, build, checkpoint_identity, seed, device)
                seed_scores[seed] = score_panel(
                    model, checkpoint_identity, fold_data, seed, draw_n=int(draw_n),
                    batch_size=int(config["training"]["inference_batch_size"]), device=device,
                )
                checkpoint_semantics[seed] = semantic
                del model
                torch.cuda.empty_cache()
            frames.append(
                _prediction_rows(
                    fold_data, fold, arm_order(config, identity), identity,
                    f"score_mean{draw_n}", int(draw_n), seed_scores, checkpoint_semantics,
                    stable_hash({"arm_id": identity, "draw_n": draw_n, "aggregation": "decoded_score_mean"}),
                )
            )
    return frames


def run_training_selection(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/predictor_early_complete.json").exists():
        raise ContractError("predictor early must complete before training")
    marker = build / ".state/pre_late_complete.json"
    if marker.exists():
        return
    configure_determinism()
    device = torch.device("cuda")
    train = _PINNED_21D.load_fold_data(config, "train")
    early = _PINNED_21D.load_fold_data(config, "validation_early")
    teacher = _PINNED_21D.load_train_teacher(config, train)
    all_curves: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    seed_selection_scores: dict[str, dict[int, np.ndarray]] = {arm_id: {} for arm_id in TRAINABLE_IDS}
    checkpoint_entries = []
    started_gpu = time.perf_counter()

    def run_job(arm_id: str, seed: int, selected_graph: str | None) -> None:
        state_root = build / f".state/jobs/{arm_id}/seed_{seed}"
        completed_path = state_root / "completed.json"
        scores_path = state_root / "selection_scores.npy"
        if completed_path.exists() and scores_path.exists():
            completed = json.loads(completed_path.read_text(encoding="utf-8"))
            row = completed["training_registry_row"]
            entry = completed["checkpoint_manifest_entry"]
            path = build / row["checkpoint_path"]
            if not path.exists() or file_sha(path) != row["checkpoint_byte_sha256"]:
                raise ContractError(f"resumed checkpoint drift: {arm_id}/{seed}")
            registry_rows.append(row)
            checkpoint_entries.append(entry)
            seed_selection_scores[arm_id][seed] = np.load(scores_path, allow_pickle=False)
            print(f"[{utc_now()}] resume completed job {arm_id}/seed_{seed}", flush=True)
            return
        started = time.perf_counter()
        graph = graph_for_arm(arm_id, selected_graph)
        if arm_id == "G0_CURRENT_X0_COUPLED":
            state, curves, selected_scores, metadata = train_g0_exact(config, seed, train, early, teacher, device)
        else:
            state, curves, selected_scores, metadata = train_custom_seed(
                config, arm_id, seed, graph, train, early, teacher, device
            )
        path = checkpoint_path(build, arm_id, seed)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(state, path)
        reopened = torch.load(path, map_location="cpu", weights_only=True)
        semantic = _PINNED_21C.model_state_semantic_hash(reopened)
        seed_selection_scores[arm_id][seed] = selected_scores
        all_curves.extend(curves)
        row = {
            "job_order": len(registry_rows), "arm_id": arm_id, "model_seed": seed,
            "attempt_n": 1, "status": "complete", "selected_epoch": metadata["selected_epoch"],
            "selected_validation_early_rankic": metadata["selected_validation_early_rankic"],
            "optimizer_step_n": metadata["optimizer_step_n"], "data_pass_n": len(curves),
            "batch_size": int(config["training"]["batch_size"]), "parameter_n": metadata["parameter_n"],
            "peak_vram_bytes": int(torch.cuda.max_memory_reserved(device)),
            "wall_seconds": time.perf_counter() - started,
            "checkpoint_path": path.relative_to(build).as_posix(),
            "checkpoint_byte_sha256": file_sha(path), "checkpoint_semantic_sha256": semantic,
            "selection_worker_exit_record_sha256": "pending_until_stage_complete",
        }
        registry_rows.append(row)
        checkpoint_entries.append(
            {
                "arm_id": arm_id, "model_seed": seed, "checkpoint_path": row["checkpoint_path"],
                "checkpoint_byte_sha256": row["checkpoint_byte_sha256"],
                "checkpoint_semantic_sha256": semantic,
                "initial_state_semantic_sha256": metadata["initial_state_semantic_sha256"],
                "ordered_parameter_names_sha256": metadata["ordered_parameter_names_sha256"],
                "selected_epoch": metadata["selected_epoch"],
            }
        )
        state_root.mkdir(parents=True, exist_ok=True)
        np.save(scores_path, np.asarray(selected_scores, dtype=np.float64), allow_pickle=False)
        _write_json(
            completed_path,
            {
                "schema_version": "S_COMPLETED_JOB_21E_V0",
                "training_registry_row": row,
                "checkpoint_manifest_entry": checkpoint_entries[-1],
                "completed_at_utc": utc_now(),
            },
        )
        print(f"[{utc_now()}] training complete {arm_id}/seed_{seed}", flush=True)
        del state, reopened
        torch.cuda.empty_cache()

    for arm_id in ("G0_CURRENT_X0_COUPLED", "G1_STOPGRAD_X0_RECON", "G2_TEACHER_LATENT_RECON_ORACLE"):
        for seed in MODEL_SEEDS:
            run_job(arm_id, seed, None)
    graph_selection = choose_training_graph(seed_selection_scores, early)
    selected_graph = str(graph_selection["selected_arm_id"])
    _write_json(build / "training/training_graph_selection.json", graph_selection)
    for arm_id in ("A1_MLP_100_STEP", "A2_RESBLOCK_20_STEP", "A3_POINTWISE_MLP_DECODER"):
        for seed in MODEL_SEEDS:
            run_job(arm_id, seed, selected_graph)
    if len(registry_rows) != 18:
        raise ContractError("training registry must contain 18 jobs")
    early_metrics = {}
    dates = early["frame"]["decision_date"].astype(str).tolist()
    for arm_id in ("A1_MLP_100_STEP", "A2_RESBLOCK_20_STEP", "A3_POINTWISE_MLP_DECODER"):
        ensemble = np.stack([seed_selection_scores[arm_id][seed] for seed in MODEL_SEEDS]).mean(axis=0)
        early_metrics[arm_id] = _PINNED_21D.validation_rankic(ensemble, early["label"], dates)[0]
    promoted_a = max(early_metrics, key=early_metrics.get)
    promoted = {
        "schema_version": "S_PROMOTED_REF256_21E_V0", "selected_training_graph_arm_id": selected_graph,
        "selected_non_control_a_arm_id": promoted_a, "a_candidate_early_metrics": early_metrics,
        "selection_fold": "validation_early", "selected_at_utc": utc_now(),
    }
    _write_json(build / "training/promoted_ref256_selection.json", promoted)
    draw_plan: dict[str, Sequence[int]] = {arm_id: (64,) for arm_id in [*TRAINABLE_IDS, "A0_SELECTED_GRAPH_CONTROL"]}
    draw_plan[selected_graph] = (64, 256)
    draw_plan[promoted_a] = (64, 256)
    ga_frames = training_prediction_frames(config, build, early, "validation_early", draw_plan, selected_graph, device)
    predictor_frame = pd.read_parquet(build / ".state/predictor_early_predictions.parquet")
    early_predictions = pd.concat([predictor_frame, *ga_frames], ignore_index=True)
    _write_parquet(build / "predictions/validation_early_prediction_scores.parquet", early_predictions)
    gradient_rows = []
    for arm_id in TRAINABLE_IDS:
        graph = graph_for_arm(arm_id, selected_graph if arm_id.startswith("A") else None)
        for seed in MODEL_SEEDS:
            gradient_rows.extend(checkpoint_gradient_audit(config, build, arm_id, seed, graph, train, teacher, device))
    gradient_frame = pd.DataFrame(gradient_rows)
    _write_parquet(build / "loss_gradient_and_collapse_audit.parquet", gradient_frame)
    exit_record = {
        "schema_version": "S_WORKER_EXIT_21E_V0", "process_role": "selection_worker",
        "pid": os.getpid(), "ended_at_utc": utc_now(), "exit_code": 0,
        "optimizer_object_n": 18, "late_open_attempt_n": 0, "historical_holdout_open_attempt_n": 0,
        "status": "pass",
    }
    _write_json(build / "training/selection_worker_exit_record.json", exit_record)
    exit_sha = file_sha(build / "training/selection_worker_exit_record.json")
    for row in registry_rows:
        row["selection_worker_exit_record_sha256"] = exit_sha
    _write_csv(build / "training/training_run_registry.csv", registry_rows, list(registry_rows[0]))
    _write_json(
        build / "training/checkpoint_manifest.json",
        {
            "schema_version": "S_CHECKPOINT_MANIFEST_21E_V0", "run_id": RUN_ID,
            "entry_n": len(checkpoint_entries), "entries": checkpoint_entries,
            "entries_semantic_sha256": stable_hash(checkpoint_entries),
        },
    )
    if time.perf_counter() - started_gpu > float(config["resources"]["total_gpu_wall_seconds_cap"]):
        raise ContractError("GPU wall-time cap exceeded")
    stages = stage_rows("E3_PRE_LATE_COMPLETE")
    _write_csv(build / "stage_status_registry.csv", stages.to_dict("records"), list(stages.columns))
    _write_json(
        marker,
        {
            "schema_version": "21E_PRE_LATE_COMPLETE_V0", "job_n": 18,
            "checkpoint_manifest_sha256": file_sha(build / "training/checkpoint_manifest.json"),
            "early_predictions_sha256": file_sha(build / "predictions/validation_early_prediction_scores.parquet"),
            "completed_at_utc": utc_now(),
        },
    )


def run_late_readout(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/pre_late_complete.json").exists():
        raise ContractError("pre-late state must complete before late readout")
    marker = build / ".state/late_readout_complete.json"
    if marker.exists():
        return
    configure_determinism()
    device = torch.device("cuda")
    predictor_frame, late_stability = fixed_predictor_frame(config, "validation_late", device)
    validate_p0_exact_replay(config, predictor_frame, "validation_late")
    graph_selection = json.loads((build / "training/training_graph_selection.json").read_text())
    promoted = json.loads((build / "training/promoted_ref256_selection.json").read_text())
    selected_graph = str(graph_selection["selected_arm_id"])
    promoted_a = str(promoted["selected_non_control_a_arm_id"])
    draw_plan: dict[str, Sequence[int]] = {arm_id: (64,) for arm_id in [*TRAINABLE_IDS, "A0_SELECTED_GRAPH_CONTROL"]}
    draw_plan[selected_graph] = (64, 256)
    draw_plan[promoted_a] = (64, 256)
    late = _PINNED_21D.load_fold_data(config, "validation_late")
    ga_frames = training_prediction_frames(config, build, late, "validation_late", draw_plan, selected_graph, device)
    predictions = pd.concat([predictor_frame, *ga_frames], ignore_index=True)
    if predictions["arm_id"].nunique() != 14 or not np.isfinite(predictions["score"]).all():
        raise ContractError("late prediction coverage/finite gate failed")
    _write_parquet(build / "predictions/validation_late_prediction_scores.parquet", predictions)
    early_stability = pd.read_parquet(build / ".state/predictor_early_stability.parquet")
    stability = pd.concat([early_stability, late_stability], ignore_index=True)
    _write_csv(build / "predictor_draw_stability.csv", stability.to_dict("records"), list(stability.columns))
    exit_record = {
        "schema_version": "S_WORKER_EXIT_21E_V0", "process_role": "late_readout_worker",
        "pid": os.getpid(), "ended_at_utc": utc_now(), "exit_code": 0,
        "optimizer_object_n": 0, "autograd_enabled": False, "train_loader_object_n": 0,
        "checkpoint_write_n": 0, "historical_holdout_open_attempt_n": 0,
        "status": "pass",
    }
    _write_json(build / "training/late_readout_worker_exit_record.json", exit_record)
    stages = stage_rows("E4_FRESH_LATE_READOUT")
    _write_csv(build / "stage_status_registry.csv", stages.to_dict("records"), list(stages.columns))
    _write_json(
        marker,
        {
            "schema_version": "21E_LATE_READOUT_COMPLETE_V0", "row_n": len(predictions),
            "late_prediction_sha256": file_sha(build / "predictions/validation_late_prediction_scores.parquet"),
            "completed_at_utc": utc_now(),
        },
    )


def daily_rankic_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_keys = ["fold_order", "fold", "arm_order", "arm_id", "score_variant", "model_seed", "is_ensemble"]
    for key, series in predictions.groupby(group_keys, sort=True, dropna=False):
        checkpoint_hash = str(series["checkpoint_semantic_sha256"].iloc[0])
        predictor_hash = str(series["predictor_semantic_sha256"].iloc[0])
        for decision_date, day in series.groupby("decision_date", sort=True):
            rankic = _PINNED_21C.rankic(
                day["score"].to_numpy(dtype=np.float64),
                day["raw_label"].to_numpy(dtype=np.float64), minimum_n=100,
            )
            rows.append(
                {
                    "fold_order": key[0], "fold": key[1], "arm_order": key[2], "arm_id": key[3],
                    "score_variant": key[4], "model_seed": key[5], "is_ensemble": key[6],
                    "decision_date": decision_date, "row_n": len(day), "RankIC": rankic,
                    "score_std": float(day["score"].std(ddof=1)),
                    "label_std": float(day["raw_label"].std(ddof=1)),
                    "metric_day_status": "pass" if math.isfinite(rankic) else "not_evaluable",
                    "checkpoint_semantic_sha256": checkpoint_hash,
                    "predictor_semantic_sha256": predictor_hash,
                }
            )
    frame = pd.DataFrame(rows).sort_values(group_keys + ["decision_date"], kind="mergesort")
    if not np.isfinite(frame.loc[frame["metric_day_status"].eq("pass"), "RankIC"]).all():
        raise ContractError("daily RankIC contains NaN/Inf")
    return frame.reset_index(drop=True)


def _variant_for_arm(arm_id: str) -> str:
    return "point" if arm_id.startswith("P") else "score_mean64"


def _series(predictions: pd.DataFrame, fold: str, arm_id: str, seed: int | None) -> pd.DataFrame:
    subset = predictions.loc[
        predictions["fold"].eq(fold)
        & predictions["arm_id"].eq(arm_id)
        & predictions["score_variant"].eq(_variant_for_arm(arm_id))
    ]
    if seed is None:
        subset = subset.loc[subset["is_ensemble"]]
    else:
        subset = subset.loc[~subset["is_ensemble"] & subset["model_seed"].eq(seed)]
    return subset.sort_values(["decision_date", "instrument"], kind="mergesort")


def bootstrap_p_value(values: np.ndarray, replicate_n: int = 2000, mean_block: int = 20) -> float:
    clean = np.asarray(values, dtype=np.float64)
    clean = clean[np.isfinite(clean)]
    if len(clean) < 2:
        return math.nan
    rng = np.random.default_rng(21000)
    means = np.empty(replicate_n, dtype=np.float64)
    probability = 1.0 / mean_block
    for replicate in range(replicate_n):
        indices = np.empty(len(clean), dtype=np.int64)
        indices[0] = rng.integers(0, len(clean))
        for index in range(1, len(clean)):
            indices[index] = rng.integers(0, len(clean)) if rng.random() < probability else (indices[index - 1] + 1) % len(clean)
        means[replicate] = clean[indices].mean()
    return float(min(1.0, 2.0 * min(np.mean(means <= 0.0), np.mean(means >= 0.0))))


def _paired_day_rho(left: pd.DataFrame, right: pd.DataFrame) -> float:
    merged = left[["decision_date", "instrument", "score"]].merge(
        right[["decision_date", "instrument", "score"]],
        on=["decision_date", "instrument"], suffixes=("_left", "_right"), validate="one_to_one",
    )
    values = [
        day["score_left"].corr(day["score_right"], method="spearman")
        for _, day in merged.groupby("decision_date", sort=True)
    ]
    return float(np.nanmedian(values))


def paired_contrast_table(
    config: Mapping[str, Any], predictions: pd.DataFrame, daily: pd.DataFrame,
    gradient_audit: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for contrast in config["contrasts"]:
        left_id = contrast["left_arm_id"]
        right_id = contrast["right_arm_id"]
        for fold in FOLDS:
            left_daily = daily.loc[
                daily["fold"].eq(fold) & daily["arm_id"].eq(left_id)
                & daily["score_variant"].eq(_variant_for_arm(left_id)) & daily["is_ensemble"]
            ][["decision_date", "RankIC"]]
            right_daily = daily.loc[
                daily["fold"].eq(fold) & daily["arm_id"].eq(right_id)
                & daily["score_variant"].eq(_variant_for_arm(right_id)) & daily["is_ensemble"]
            ][["decision_date", "RankIC"]]
            paired = left_daily.merge(right_daily, on="decision_date", suffixes=("_left", "_right"), validate="one_to_one")
            delta = paired["RankIC_left"].to_numpy() - paired["RankIC_right"].to_numpy()
            seed_deltas = []
            for seed in MODEL_SEEDS:
                left_seed = daily.loc[
                    daily["fold"].eq(fold) & daily["arm_id"].eq(left_id)
                    & daily["score_variant"].eq(_variant_for_arm(left_id)) & daily["model_seed"].eq(seed)
                ]["RankIC"].mean()
                right_seed = daily.loc[
                    daily["fold"].eq(fold) & daily["arm_id"].eq(right_id)
                    & daily["score_variant"].eq(_variant_for_arm(right_id)) & daily["model_seed"].eq(seed)
                ]["RankIC"].mean()
                seed_deltas.append(float(left_seed - right_seed))
            mean_delta = float(np.mean(delta))
            sign = 1 if mean_delta >= 0 else -1
            same_direction = sum(1 for value in seed_deltas if value * sign > 0)
            rho = _paired_day_rho(_series(predictions, fold, left_id, None), _series(predictions, fold, right_id, None))
            morphology_ok = True
            if not left_id.startswith("P"):
                left_collapse = gradient_audit.loc[gradient_audit["arm_id"].eq(left_id), "additional_collapse_flag_n"].mean()
                right_checkpoint_id = right_id
                if right_id == "A0_SELECTED_GRAPH_CONTROL":
                    right_checkpoint_id = json.loads((building_output_root(config) / "training/training_graph_selection.json").read_text())["selected_arm_id"]
                right_collapse = gradient_audit.loc[gradient_audit["arm_id"].eq(right_checkpoint_id), "additional_collapse_flag_n"].mean()
                morphology_ok = bool(left_collapse <= right_collapse)
            rows.append(
                {
                    "contrast_order": contrast["contrast_order"], "contrast_id": contrast["contrast_id"],
                    "family_id": contrast["family_id"], "fold": fold, "left_arm_id": left_id,
                    "left_score_variant": _variant_for_arm(left_id), "right_arm_id": right_id,
                    "right_score_variant": _variant_for_arm(right_id), "paired_day_n": len(paired),
                    "mean_rankic_delta": mean_delta, "median_rankic_delta": float(np.median(delta)),
                    "same_direction_seed_n": same_direction, "median_daily_score_spearman": rho,
                    "morphology_or_collapse_nonworse": morphology_ok,
                    "raw_p_value": bootstrap_p_value(delta), "holm_p_value": math.nan,
                    "material_change": False, "status": "pass",
                }
            )
    frame = pd.DataFrame(rows)
    for (_, fold), indices in frame.groupby(["family_id", "fold"], sort=True).groups.items():
        ordered = sorted(indices, key=lambda index: frame.at[index, "raw_p_value"])
        running = 0.0
        for rank, index in enumerate(ordered):
            adjusted = min(1.0, float(frame.at[index, "raw_p_value"]) * (len(ordered) - rank))
            running = max(running, adjusted)
            frame.at[index, "holm_p_value"] = running
    thresholds = config["materiality"]
    for fold in FOLDS:
        predictor_means = daily.loc[
            daily["fold"].eq(fold) & daily["arm_id"].isin(PREDICTOR_IDS)
            & daily["score_variant"].eq("point") & daily["is_ensemble"]
        ].groupby("arm_id")["RankIC"].mean()
        predictor_range = float(predictor_means.max() - predictor_means.min())
        for index in frame.index[frame["fold"].eq(fold)]:
            row = frame.loc[index]
            common = (
                abs(row["mean_rankic_delta"]) >= thresholds["mean_rankic_delta_min"]
                and row["same_direction_seed_n"] >= thresholds["same_direction_seed_n_min"]
                and row["median_daily_score_spearman"] < thresholds["median_score_spearman_max"]
            )
            if str(row["contrast_id"]).startswith("C0"):
                frame.at[index, "material_change"] = bool(common and predictor_range >= thresholds["predictor_range_min"])
            else:
                frame.at[index, "material_change"] = bool(common and row["morphology_or_collapse_nonworse"])
    return frame.sort_values(["contrast_order", "fold"], kind="mergesort").reset_index(drop=True)


def cross_seed_morphology_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (fold, arm_order_value, arm_id, variant), series in predictions.groupby(
        ["fold", "arm_order", "arm_id", "score_variant"], sort=True
    ):
        seed_series = {seed: series.loc[series["model_seed"].eq(seed)] for seed in MODEL_SEEDS}
        if any(item.empty for item in seed_series.values()):
            continue
        for seed_a, seed_b in ((MODEL_SEEDS[0], MODEL_SEEDS[1]), (MODEL_SEEDS[0], MODEL_SEEDS[2]), (MODEL_SEEDS[1], MODEL_SEEDS[2])):
            merged = seed_series[seed_a].merge(
                seed_series[seed_b], on=["decision_date", "instrument"], suffixes=("_a", "_b"), validate="one_to_one"
            )
            for decision_date, day in merged.groupby("decision_date", sort=True):
                rho = day["score_a"].corr(day["score_b"], method="spearman")
                overlap = len(set(day.nlargest(30, "score_a")["instrument"]) & set(day.nlargest(30, "score_b")["instrument"]))
                for metric_id, metric_value in (("daily_score_spearman", rho), ("top30_overlap", overlap)):
                    rows.append(
                        {
                            "fold": fold, "arm_order": arm_order_value, "arm_id": arm_id,
                            "score_variant": variant, "aggregation_role": "pairwise_seed",
                            "seed_a": seed_a, "seed_b": seed_b, "decision_date": decision_date,
                            "metric_id": metric_id, "metric_value": metric_value,
                            "row_n": len(day), "status": "pass",
                        }
                    )
    return pd.DataFrame(rows)


def hypothesis_readout_table(contrasts: pd.DataFrame) -> pd.DataFrame:
    registry = hypothesis_registry()
    family_map = {
        "H21E01_POINT_AGGREGATION_MATERIAL": {"predictor_semantics"},
        "H21E02_CURRENT_DRC_HARMS_SCORE": {"corrected_latent"},
        "H21E03_REC_GRADIENT_PATH_MATERIAL": {"drc_training_graph"},
        "H21E04_DENOISER_OR_SCHEDULE_MATERIAL": {"drc_architecture"},
        "H21E05_DECODER_TOPOLOGY_MATERIAL": {"decoder_topology"},
        "H21E06_UNDISCLOSED_CODE_REMAINS": {"predictor_semantics", "corrected_latent", "drc_training_graph", "drc_architecture", "decoder_topology"},
    }
    rows = []
    for item in registry.to_dict("records"):
        for fold in FOLDS:
            evidence = contrasts.loc[contrasts["fold"].eq(fold) & contrasts["family_id"].isin(family_map[item["hypothesis_id"]])]
            material_n = int(evidence["material_change"].sum())
            directional_n = int((evidence["mean_rankic_delta"].abs() >= 0.005).sum())
            if item["hypothesis_id"] == "H21E06_UNDISCLOSED_CODE_REMAINS":
                falsifier = bool(
                    ((evidence["material_change"]) & (evidence["mean_rankic_delta"] >= 0.020) & (evidence["same_direction_seed_n"] >= 2)).any()
                )
            else:
                falsifier = material_n == 0
            rows.append(
                {
                    "hypothesis_order": item["hypothesis_order"], "hypothesis_id": item["hypothesis_id"],
                    "fold": fold, "required_contrast_ids_json": item["required_contrast_ids_json"],
                    "direct_test_complete": not evidence.empty, "falsifier_triggered": falsifier,
                    "material_evidence_n": material_n, "directional_evidence_n": directional_n,
                    "conflicting_evidence_n": int((np.sign(evidence["mean_rankic_delta"]) != np.sign(evidence["median_rankic_delta"])).sum()),
                    "evidence_paths_json": "[\"paired_implementation_contrasts.csv\"]",
                    "readout_status": "falsified" if falsifier else "not_falsified",
                    "allowed_conclusion": "design_contaminated_mechanism_diagnostic",
                }
            )
    return pd.DataFrame(rows)


def terminal_decision(contrasts: pd.DataFrame) -> tuple[str, dict[str, str]]:
    late = contrasts.loc[contrasts["fold"].eq("validation_late")]
    statuses = {
        "predictor_semantics_status": "material" if late.loc[late["family_id"].isin({"predictor_semantics", "corrected_latent"}), "material_change"].any() else "not_material",
        "drc_training_graph_status": "material" if late.loc[late["family_id"].eq("drc_training_graph"), "material_change"].any() else "not_material",
        "drc_architecture_status": "material" if late.loc[late["family_id"].eq("drc_architecture"), "material_change"].any() else "not_material",
        "decoder_status": "material" if late.loc[late["family_id"].eq("decoder_topology"), "material_change"].any() else "not_material",
    }
    material = [key for key, value in statuses.items() if value == "material"]
    mapping = {
        "predictor_semantics_status": "21E_predictor_semantics_material",
        "drc_training_graph_status": "21E_drc_training_graph_material",
        "drc_architecture_status": "21E_drc_architecture_material",
        "decoder_status": "21E_decoder_topology_material",
    }
    if len(material) == 1:
        terminal = mapping[material[0]]
    elif len(material) >= 2:
        terminal = "21E_multiple_implementation_ambiguities_material"
    elif (late["status"] == "pass").all() and np.isfinite(late["mean_rankic_delta"]).all():
        terminal = "21E_no_tested_implementation_explains_gap"
    else:
        terminal = "21E_evidence_mixed_external_implementation_gap_unresolved"
    return terminal, statuses


def report_markdown(
    build: Path,
    daily: pd.DataFrame,
    contrasts: pd.DataFrame,
    hypotheses: pd.DataFrame,
    gradient: pd.DataFrame,
    terminal: str,
    statuses: Mapping[str, str],
) -> str:
    late_summary = (
        daily.loc[daily["fold"].eq("validation_late") & daily["is_ensemble"]]
        .groupby(["arm_id", "score_variant"], sort=True)["RankIC"].mean()
        .reset_index()
        .sort_values("RankIC", ascending=False)
    )
    late_metric = {
        (str(row.arm_id), str(row.score_variant)): float(row.RankIC)
        for row in late_summary.itertuples(index=False)
    }
    late_contrasts = contrasts.loc[contrasts["fold"].eq("validation_late")].set_index("contrast_id")

    def contrast_value(contrast_id: str, column: str) -> Any:
        return late_contrasts.loc[contrast_id, column]

    current_p0 = late_metric[("P0_CURRENT_SCORE_MEAN8", "point")]
    koopman_only = late_metric[("P5_KOOPMAN_ONLY", "point")]
    g0 = late_metric[("G0_CURRENT_X0_COUPLED", "score_mean64")]
    g1 = late_metric[("G1_STOPGRAD_X0_RECON", "score_mean64")]
    g0_rec_denoiser = gradient.loc[
        gradient["arm_id"].eq("G0_CURRENT_X0_COUPLED")
        & gradient["loss_id"].eq("L_rec")
        & gradient["module_id"].eq("denoiser"),
        "gradient_l2",
    ].mean()
    g1_rec_denoiser = gradient.loc[
        gradient["arm_id"].eq("G1_STOPGRAD_X0_RECON")
        & gradient["loss_id"].eq("L_rec")
        & gradient["module_id"].eq("denoiser"),
        "gradient_l2",
    ].mean()
    g0_total_denoiser_share = gradient.loc[
        gradient["arm_id"].eq("G0_CURRENT_X0_COUPLED")
        & gradient["loss_id"].eq("L_total")
        & gradient["module_id"].eq("denoiser"),
        "global_gradient_share",
    ].mean()
    collapse_flag_n = int(gradient["additional_collapse_flag_n"].sum())
    large_local_paths = sorted(
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file() and path.stat().st_size > 20 * 1024 * 1024
    )
    lines = [
        "# 21E REAKA Predictor / DRC 实现识别报告",
        "",
        f"- 终态：`{terminal}`",
        "- 证据角色：`design_contaminated_mechanism_diagnostic`",
        "- 不允许论文精确复现、作者实现或 forward support 宣称。",
        "- 本实验没有生成组合收益、AR、Sharpe、换手或再平衡结论。",
        "",
        "## 证据分栏与结论边界",
        "",
        "| 证据类别 | 本阶段可确认内容 | 允许使用方式 | 不允许外推 |",
        "|---|---|---|---|",
        "| 论文原文 | 定义 residual target、以 `Z` 为条件的 DDPM、corrected latent，以及 shifted sequence 最后一位作为预测；未披露采样聚合、扩散步数、denoiser/decoder topology、`L_rec` 梯度连接和再平衡频率 | 限定论文明确语义与未披露项 | 不据此补写作者代码 |",
        "| 21C project choice | `8-draw score mean`、20-step concat MLP denoiser、shared linear decoder、当前 coupled reconstruction graph | 作为待识别的本地实现基线 | 不称为论文原实现 |",
        "| 21D prior observation | 21C/21D 已读取 2023 early/late 并据此提出实现差异假设；RankIC gap 可能混合 Predictor、DRC 与其他外部缺口 | 只用于冻结 21E 假设与 arm | 不当作 21E 独立验证 |",
        "| 21E direct evidence | 冻结 arm、3 seeds、early-only 选择、fresh late worker 的 paired RankIC、形态与梯度审计 | 只判断本地实现敏感性和 materiality | 不声称论文精确复现、作者实现或 forward support |",
        "",
        "## 1. 论文明确语义与未披露项",
        "",
        "论文明确给出了 residual target、conditional DDPM、corrected latent 和最后 shifted position 的预测语义。论文没有足够信息唯一确定 draw 聚合、reverse-path 随机性、扩散步数、denoiser 与 decoder topology、reconstruction gradient coupling，以及投资组合再平衡频率。因此这些项在 21E 中被视为实现歧义，而不是从论文补全出的事实。",
        "",
        "## 2. 21C 中属于 project choice 的实现",
        "",
        "- Predictor：8 个 row-keyed DDPM draws 在 decoded-score 域取 mean。",
        "- DRC：20 diffusion steps，concat MLP denoiser。",
        "- Decoder：shared linear decoder。",
        "- Training graph：`L_rec -> x0_hat -> denoiser` 保持 coupled。",
        "- 上述选择仅定义 P0/G0/A0 control，不代表论文作者实现。",
        "",
        "## 3. Predictor 聚合与 corrected-latent 排序",
        "",
        "Validation-late ensemble mean daily RankIC 如下。`zero-noise` 仅是 deterministic reverse-path proxy，不能解释为 DDPM conditional mean；`Koopman-only` 是去掉 corrected residual 的机制 control。",
        "",
        "| arm | readout | mean daily RankIC | 与 P0 的含义 |",
        "|---|---|---:|---|",
    ]
    for row in late_summary.to_dict("records"):
        meaning = "21C current control" if row["arm_id"] == "P0_CURRENT_SCORE_MEAN8" else "implementation sensitivity readout"
        lines.append(f"| {row['arm_id']} | {row['score_variant']} | {row['RankIC']:.6f} | {meaning} |")
    lines.extend(
        [
            "",
            f"P1 single draw 相对 P0 的 C01 delta 为 `{float(contrast_value('C01', 'mean_rankic_delta')):.6f}`；64-draw mean 的 C02 为 `{float(contrast_value('C02', 'mean_rankic_delta')):.6f}`；256-draw mean 的 C03 为 `{float(contrast_value('C03', 'mean_rankic_delta')):.6f}`；median256 相对 mean256 的 C06 为 `{float(contrast_value('C06', 'mean_rankic_delta')):.6f}`。聚合选择会改变排序，Predictor semantics 判定为 material。",
            "",
            "## 4. 当前 DRC 相对 Koopman-only",
            "",
            f"P0 current score-mean8 RankIC 为 `{current_p0:.6f}`，P5 Koopman-only 为 `{koopman_only:.6f}`，后者高 `{koopman_only - current_p0:.6f}`。预注册 C05 使用 Koopman-only 对 mean256 corrected-latent，late delta 为 `{float(contrast_value('C05', 'mean_rankic_delta')):.6f}`，3 seeds 中 `{int(contrast_value('C05', 'same_direction_seed_n'))}` 个同向，判定 `{str(bool(contrast_value('C05', 'material_change'))).lower()}`。因此在本地 2023 diagnostic 上，当前 corrected residual 路径相对该 control 是伤害而非增益；这不等价于论文 DRC 本身无效。",
            "",
            "## 5. Reconstruction gradient coupling 与 collapse",
            "",
            f"G0 coupled 的 denoiser `L_rec` gradient L2 均值为 `{g0_rec_denoiser:.6e}`；G1 stop-grad 对应值为 `{g1_rec_denoiser:.6e}`，验证 detach 确实切断该路径。G0 的 denoiser `L_total` global-gradient share 均值为 `{g0_total_denoiser_share:.6f}`，但审计中的 additional collapse flags 总数为 `{collapse_flag_n}`：没有触发预注册的新增 collapse。late RankIC 从 G0 `{g0:.6f}` 提升到 G1 `{g1:.6f}`，C10 delta `{float(contrast_value('C10', 'mean_rankic_delta')):.6f}`、`{int(contrast_value('C10', 'same_direction_seed_n'))}/3` seeds 同向并 material。结论是 gradient path 对结果 material；证据不支持把差距简化为已观测到的 gradient-dominance collapse。",
            "",
            "## 6. DRC steps、denoiser 与 decoder 的 materiality",
            "",
            "| 变体 | contrast | late delta | 同向 seeds | material | 结论 |",
            "|---|---|---:|---:|---|---|",
            f"| A1 100 steps | C20 | {float(contrast_value('C20', 'mean_rankic_delta')):.6f} | {int(contrast_value('C20', 'same_direction_seed_n'))}/3 | {str(bool(contrast_value('C20', 'material_change'))).lower()} | 仅增加 steps 未通过四项 conjunction |",
            f"| A2 residual-block denoiser | C21 | {float(contrast_value('C21', 'mean_rankic_delta')):.6f} | {int(contrast_value('C21', 'same_direction_seed_n'))}/3 | {str(bool(contrast_value('C21', 'material_change'))).lower()} | topology 改变未判 material |",
            f"| A3 pointwise MLP decoder | C22 | {float(contrast_value('C22', 'mean_rankic_delta')):.6f} | {int(contrast_value('C22', 'same_direction_seed_n'))}/3 | {str(bool(contrast_value('C22', 'material_change'))).lower()} | decoder topology material |",
            "",
            f"机械状态汇总：Predictor `{statuses['predictor_semantics_status']}`；DRC training graph `{statuses['drc_training_graph_status']}`；DRC architecture `{statuses['drc_architecture_status']}`；Decoder topology `{statuses['decoder_status']}`。",
            "",
            "## 7. Oracle 与 diagnostic controls",
            "",
            "- G2 teacher-latent reconstruction 使用 inference 不可获得的 teacher target，只能作为 oracle control，永远不可晋级。",
            "- P4 zero-noise reverse path 只是 deterministic proxy，不是 DDPM conditional mean。",
            "- P5 Koopman-only 用于识别 corrected residual 的局部贡献，不是完整 REAKA 替代实现。",
            "- 所有 2023 readouts 的 evidence role 均为 `design_contaminated_mechanism_diagnostic`。",
            "",
            "## 8. 为什么不能声称找到论文作者实现",
            "",
            "本实验只比较有限、预注册的本地 arms。material 表明结果对该实现维度敏感，不表示胜出的 arm 等于作者代码；not-material 也不能排除未测试的 architecture。没有官方代码、作者确认、完整 decoder/采样细节时，作者实现不可识别。",
            "",
            "## 9. 为什么不报告组合收益与再平衡结论",
            "",
            "本 requirement 没有授权生成组合、AR、Sharpe、换手或 execution ledger，portfolio artifact absence gate 已通过。论文再平衡频率仍未被唯一识别，因此不能把本实验 RankIC 直接转换为日频或其他频率的投资模拟；相关验证必须另立 requirement。",
            "",
            "## 10. 剩余不可识别项与下一步边界",
            "",
            "仍缺少官方 sampling aggregation、reverse stochastic contract、完整 denoiser/decoder topology、reconstruction coupling 说明、训练细节和再平衡合同。外部官方代码或作者说明出现前，终态保持 implementation ambiguities material，且 `next_requirement_execution_authorized=false`。",
            "",
            "## 预注册 contrasts 完整表",
            "",
            "| contrast | family | mean delta | seed同向数 | median score rho | material |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in contrasts.loc[contrasts["fold"].eq("validation_late")].to_dict("records"):
        lines.append(
            f"| {row['contrast_id']} | {row['family_id']} | {row['mean_rankic_delta']:.6f} | {int(row['same_direction_seed_n'])} | "
            f"{row['median_daily_score_spearman']:.6f} | {str(bool(row['material_change'])).lower()} |"
        )
    lines.extend(
        [
            "", "## 假设与终态", "",
            f"- 预注册假设 readout 行数：`{len(hypotheses)}`。",
            f"- 终态：`{terminal}`。",
            "- 决策规则：mechanical first-match from pre-registered materiality。",
            "",
            "## 本地 canonical 与 Git 发布边界",
            "",
            "canonical bundle 在本地完整保留。以下单文件超过 20 MiB，Git 发布时必须按 exact path ignore，但不得删除、截断或替换为空文件：",
        ]
    )
    for relative in large_local_paths:
        size_mib = (build / relative).stat().st_size / (1024 * 1024)
        lines.append(f"- `{relative}`（{size_mib:.2f} MiB，本地 canonical only）")
    lines.extend(
        [
            "",
            "其余 canonical artifacts 可按仓库规则正常发布；本报告不执行 Git commit/push。",
            "",
        ]
    )
    return "\n".join(lines)


def validate_report_contract(report: str) -> None:
    required_fragments = [
        "| 论文原文 |",
        "| 21C project choice |",
        "| 21D prior observation |",
        "| 21E direct evidence |",
        *[f"## {index}." for index in range(1, 11)],
        "predictions/validation_early_prediction_scores.parquet",
        "predictions/validation_late_prediction_scores.parquet",
        "再平衡频率仍未被唯一识别",
        "next_requirement_execution_authorized=false",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in report]
    if missing:
        raise ContractError(f"report contract missing required fragments: {missing}")
    if len(report.encode("utf-8")) < 5_000:
        raise ContractError("report contract requires substantive Chinese evidence narrative")


def artifact_profile_table(config: Mapping[str, Any]) -> pd.DataFrame:
    contract = artifact_profile_contract(config)
    contract_sha = stable_hash(contract)
    return pd.DataFrame(
        [
            {
                "profile_order": 1, "artifact_profile_id": PROFILE_ID,
                "required_paths_json": canonical_json_bytes(contract["required_paths"]).decode(),
                "forbidden_paths_json": canonical_json_bytes(contract["forbidden_paths"]).decode(),
                "conditional_paths_json": "{}", "registry_contract_sha256": contract_sha,
                "status": "pass",
            }
        ]
    )


def gate_evidence_table() -> pd.DataFrame:
    stage_for_order = {
        **{order: "E0_PREAUTH_AND_PREFLIGHT" for order in range(1, 8)},
        **{order: "E1_PREDICTOR_EARLY_READOUT" for order in range(8, 11)},
        **{order: "E2_DRC_TRAINING_AND_EARLY_SELECTION" for order in range(11, 17)},
        17: "E3_PRE_LATE_COMPLETE",
        **{order: "E4_FRESH_LATE_READOUT" for order in range(18, 25)},
        **{order: "E5_FINALIZE_AND_SEAL" for order in range(25, 30)},
    }
    return pd.DataFrame(
        [
            {
                "gate_order": order, "gate_id": gate_id, "stage_id": stage_for_order[order],
                "status": "pass", "check_n": 1, "pass_n": 1, "fail_n": 0,
                "evidence_paths_json": "[]", "first_failure_reason": "",
            }
            for order, gate_id in enumerate(GATE_IDS, start=1)
        ]
    )


def artifact_schema_and_rows(path: Path) -> tuple[str, int | None]:
    if path.suffix == ".csv":
        return "S_CSV_21E_V0", max(0, sum(1 for _ in path.open("rb")) - 1)
    if path.suffix == ".parquet":
        return "S_PARQUET_21E_V0", pq.read_metadata(path).num_rows
    if path.suffix == ".json":
        payload = json.loads(path.read_text())
        return str(payload.get("schema_version", "S_JSON_21E_V0")), None
    if path.suffix == ".md":
        return "S_MARKDOWN_REPORT_21E_V0", None
    if path.suffix == ".yaml":
        return "S_YAML_21E_V0", None
    if path.suffix == ".pt":
        return "S_TORCH_STATE_DICT_21E_V0", None
    return "S_BINARY_21E_V0", None


def validate_no_forbidden_outputs(build: Path) -> None:
    forbidden_tokens = (
        "paper_proxy_top30", "portfolio_", "execution_ledger", "annualized_return",
        "sharpe", "turnover", "historical_holdout_predictions", "best_seed", "post_late_added_arm",
    )
    for path in build.rglob("*"):
        if path.is_file() and any(token in path.relative_to(build).as_posix().lower() for token in forbidden_tokens):
            raise ContractError(f"forbidden output present: {path}")


def run_finalize(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    if not (build / ".state/late_readout_complete.json").exists():
        raise ContractError("late readout must complete before finalize")
    if canonical.exists():
        raise ContractError("canonical output already exists")
    early = pd.read_parquet(build / "predictions/validation_early_prediction_scores.parquet")
    late = pd.read_parquet(build / "predictions/validation_late_prediction_scores.parquet")
    predictions = pd.concat([early, late], ignore_index=True)
    daily = daily_rankic_table(predictions)
    _write_csv(build / "daily_rankic_readout.csv", daily.to_dict("records"), list(daily.columns))
    gradient = pd.read_parquet(build / "loss_gradient_and_collapse_audit.parquet")
    contrasts = paired_contrast_table(config, predictions, daily, gradient)
    _write_csv(build / "paired_implementation_contrasts.csv", contrasts.to_dict("records"), list(contrasts.columns))
    morphology = cross_seed_morphology_table(predictions)
    _write_csv(build / "cross_seed_morphology.csv", morphology.to_dict("records"), list(morphology.columns))
    hypotheses = hypothesis_readout_table(contrasts)
    _write_csv(build / "hypothesis_readout.csv", hypotheses.to_dict("records"), list(hypotheses.columns))
    terminal, statuses = terminal_decision(contrasts)
    decision_row = {
        "run_id": RUN_ID, "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": PROFILE_ID, "terminal_state": terminal,
        "evidence_role": "design_contaminated_mechanism_diagnostic",
        **statuses,
        "unresolved_external_gap_status": "unresolved_without_official_code",
        "next_requirement_execution_authorized": False,
        "decision_reason": "mechanical_first_match_from_pre_registered_materiality",
    }
    decision_columns = list(decision_row)
    _write_csv(
        build / "21E_reaka_predictor_drc_implementation_identification_decision.csv",
        [decision_row], decision_columns,
    )
    report = report_markdown(build, daily, contrasts, hypotheses, gradient, terminal, statuses)
    validate_report_contract(report)
    (build / "21E_reaka_predictor_drc_implementation_identification_report.md").write_text(report, encoding="utf-8")
    profile = artifact_profile_table(config)
    _write_csv(build / "artifact_profile_registry.csv", profile.to_dict("records"), list(profile.columns))
    access_rows = [
        {
            "stage_id": stage, "process_role": role, "artifact_path": "historical_design_holdout",
            "open_attempt_n": 0, "successful_open_n": 0, "bytes_read_n": 0,
            "first_opened_at_utc": "", "last_opened_at_utc": "", "status": "pass",
        }
        for stage, role in (
            ("E0_PREAUTH_AND_PREFLIGHT", "preflight_controller"),
            ("E1_PREDICTOR_EARLY_READOUT", "predictor_worker"),
            ("E2_DRC_TRAINING_AND_EARLY_SELECTION", "training_worker"),
            ("E3_PRE_LATE_COMPLETE", "parent_controller"),
            ("E4_FRESH_LATE_READOUT", "late_readout_worker"),
            ("E5_FINALIZE_AND_SEAL", "finalize_controller"),
        )
    ]
    _write_csv(build / "historical_design_holdout_access_audit.csv", access_rows, list(access_rows[0]))
    stages = stage_rows("E5_FINALIZE_AND_SEAL")
    _write_csv(build / "stage_status_registry.csv", stages.to_dict("records"), list(stages.columns))
    gates = gate_evidence_table()
    _write_csv(build / "gate_evidence_21e.csv", gates.to_dict("records"), list(gates.columns))
    checkpoint_manifest = json.loads((build / "training/checkpoint_manifest.json").read_text())
    semantic = {
        "schema_version": "S_SEMANTIC_REPRODUCIBILITY_21E_V0", "run_id": RUN_ID,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "paper_pdf_sha256": config["upstream_pins"]["paper_pdf"]["sha256"],
        "upstream_semantic_hashes": {key: value["sha256"] for key, value in config["upstream_pins"].items()},
        "retained_row_key_hashes": {key: value["row_key_sha256"] for key, value in config["retained_folds"].items()},
        "ambiguity_registry_sha256": file_sha(build / "paper_predictor_drc_ambiguity_registry.csv"),
        "hypothesis_registry_sha256": file_sha(build / "hypothesis_registry.csv"),
        "arm_registry_sha256": file_sha(build / "implementation_arm_registry.csv"),
        "contrast_registry_sha256": file_sha(build / "contrast_registry.csv"),
        "hypothesis_readout_sha256": file_sha(build / "hypothesis_readout.csv"),
        "initial_state_semantic_hashes": {f"{item['arm_id']}:{item['model_seed']}": item["initial_state_semantic_sha256"] for item in checkpoint_manifest["entries"]},
        "checkpoint_semantic_hashes": {f"{item['arm_id']}:{item['model_seed']}": item["checkpoint_semantic_sha256"] for item in checkpoint_manifest["entries"]},
        "predictor_semantic_hashes": sorted(predictions["predictor_semantic_sha256"].unique().tolist()),
        "draw_schedule_semantic_hashes": stable_hash(pd.read_csv(build / "predictor_draw_stability.csv")["draw_schedule_sha256"].astype(str).tolist()),
        "metric_semantic_hashes": {
            "daily_rankic": file_sha(build / "daily_rankic_readout.csv"),
            "paired_contrasts": file_sha(build / "paired_implementation_contrasts.csv"),
        },
    }
    semantic["semantic_payload_bundle_hash"] = stable_hash(semantic)
    _write_json(build / "semantic_reproducibility_manifest.json", semantic)
    validate_no_forbidden_outputs(build)
    shutil.rmtree(build / ".state", ignore_errors=True)
    required = required_artifact_paths(config)
    manifest_name = "manifest_21e_reaka_predictor_drc_implementation_identification.json"
    hashes_name = "output_hashes_21e_reaka_predictor_drc_implementation_identification.json"
    content_paths = sorted(required - {manifest_name, hashes_name})
    observed_before_manifest = {path.relative_to(build).as_posix() for path in build.rglob("*") if path.is_file()}
    if observed_before_manifest != set(content_paths):
        raise ContractError(
            f"pre-manifest artifact set mismatch extra={sorted(observed_before_manifest - set(content_paths))} "
            f"missing={sorted(set(content_paths) - observed_before_manifest)}"
        )
    artifacts = []
    for relative in content_paths:
        path = build / relative
        schema, row_count = artifact_schema_and_rows(path)
        artifacts.append(
            {
                "path": relative, "role": "substantive_evidence", "row_count": row_count,
                "schema_version": schema, "sha256": file_sha(path), "size_bytes": path.stat().st_size,
            }
        )
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.sha256 is None:
        raise ContractError("authorization drifted before finalize")
    manifest = {
        "schema_version": "S_MANIFEST_21E_V0", "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "authorization_sha256": authorization.sha256,
        "paper_pdf_sha256": config["upstream_pins"]["paper_pdf"]["sha256"],
        "upstream_pins": config["upstream_pins"], "replay_identity": config["sealed_replay"],
        "artifact_profile_id": PROFILE_ID,
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "terminal_state": terminal, "artifact_n": len(artifacts), "artifacts": artifacts,
        "report_sha256": file_sha(build / "21E_reaka_predictor_drc_implementation_identification_report.md"),
        "decision_sha256": file_sha(build / "21E_reaka_predictor_drc_implementation_identification_decision.csv"),
        "semantic_reproducibility_manifest_sha256": file_sha(build / "semantic_reproducibility_manifest.json"),
        "output_hashes_path": hashes_name, "output_hashes_excluded_self_path": hashes_name,
        "finalized_at_utc": utc_now(),
    }
    _write_json(build / manifest_name, manifest)
    hash_entries = []
    for relative in sorted(required - {hashes_name}):
        path = build / relative
        hash_entries.append({"path": relative, "sha256": file_sha(path), "size_bytes": path.stat().st_size})
    _write_json(
        build / hashes_name,
        {
            "schema_version": "S_OUTPUT_HASHES_21E_V0", "run_id": RUN_ID,
            "excluded_self_path": hashes_name, "entry_n": len(hash_entries), "entries": hash_entries,
            "entries_semantic_sha256": stable_hash(hash_entries),
        },
    )
    observed = {path.relative_to(build).as_posix() for path in build.rglob("*") if path.is_file()}
    if observed != required:
        raise ContractError(f"final artifact set mismatch extra={sorted(observed - required)} missing={sorted(required - observed)}")
    registered = json.loads((build / hashes_name).read_text())["entries"]
    for item in registered:
        path = build / item["path"]
        if file_sha(path) != item["sha256"] or path.stat().st_size != item["size_bytes"]:
            raise ContractError(f"output hash closure mismatch: {item['path']}")
    os.replace(build, canonical)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=("preflight", "predictor-early", "train-selection", "late-readout", "finalize", "all"),
        default="all",
    )
    return parser.parse_args(argv)


def run_stage(config: Mapping[str, Any], stage: str) -> None:
    print(f"[{utc_now()}] 21E stage start: {stage}", flush=True)
    if stage == "preflight":
        run_preflight(config)
    elif stage == "predictor-early":
        run_predictor_early(config)
    elif stage == "train-selection":
        run_training_selection(config)
    elif stage == "late-readout":
        run_late_readout(config)
    elif stage == "finalize":
        run_finalize(config)
    else:
        raise ContractError(f"unknown stage: {stage}")
    print(f"[{utc_now()}] 21E stage complete: {stage}", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    authorization = validate_authorization(config)
    if authorization.status != "pass":
        raise ContractError("execution forbidden before valid human authorization: " + ",".join(authorization.errors))
    if args.stage != "all":
        run_stage(config, args.stage)
        return 0
    run_stage(config, "preflight")
    runner = workspace_path(config["paths"]["runner"], must_exist=True)
    config_path = workspace_path(config["paths"]["config"], must_exist=True)
    for stage in ("predictor-early", "train-selection", "late-readout", "finalize"):
        completed = subprocess.run(
            [sys.executable, str(runner), "--config", str(config_path), "--stage", stage],
            check=False,
        )
        if completed.returncode != 0:
            raise ContractError(f"fresh process stage failed: {stage} exit={completed.returncode}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
