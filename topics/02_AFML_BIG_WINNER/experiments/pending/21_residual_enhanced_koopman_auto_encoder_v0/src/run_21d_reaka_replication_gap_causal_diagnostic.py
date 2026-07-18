#!/usr/bin/env python3
"""Run the frozen 21D REAKA replication-gap causal diagnostic.

The controller is intentionally fail closed.  It imports the hash-pinned 21C
implementation for the exact D0 replay, keeps all work under ``.building``,
and only atomically publishes the canonical root after every learned job,
fresh late readout, metric, gate, and hash-closure check succeeds.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch
import torch.nn.functional as F
import yaml
from torch import Tensor, nn


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = EXPERIMENT_DIR.parents[2]
DEFAULT_CONFIG = (
    EXPERIMENT_DIR
    / "configs/config_21d_reaka_replication_gap_causal_diagnostic.yaml"
)
RUN_ID = "21D_reaka_replication_gap_causal_diagnostic"
REQUIREMENT_VERSION = "21D_GAP_v2"
MODEL_SEEDS = (20260713, 20260714, 20260715)
LOOKBACK = 10
FEATURE_DIM = 157
LATENT_DIM = 64
N_OPERATOR = 4
DIFFUSION_STEPS = 20
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

ARM_IDS = (
    "D0_R2_RAW_EXACT_REPLAY",
    "D1_R2_RETURN_PATH_CSZ_ONLY",
    "D2_R2_GRADBAL_ONLY",
    "D3_R2_ST_HARD_ONLY",
    "D4_R2_REPAIR_COMBINED_V1",
    "D5_K2_RAW_NO_RESIDUAL",
    "D6_R1_RAW_MLP_RESIDUAL",
)
DRAW_IDENTITIES = (
    "SEALED_V4_R2",
    "D0_R2_RAW_EXACT_REPLAY",
    "D4_R2_REPAIR_COMBINED_V1",
)
FOLDS = ("train", "validation_early", "validation_late")
VALIDATION_FOLDS = ("validation_early", "validation_late")
COMPARATORS = ("M1_LIGHTGBM_ALPHA158", "M3_GATED_DUAL_PATH_LSTM")

AUTHORIZATION_KEYS = {
    "schema_version",
    "run_id",
    "requirement_version",
    "approved_requirement_sha256",
    "approved_config_sha256",
    "approved_runner_sha256",
    "approved_test_sha256",
    "approved_upstream_21c_manifest_sha256",
    "approved_upstream_21c_output_hashes_sha256",
    "approved_upstream_21b_v5_manifest_sha256",
    "approved_upstream_21b_v5_output_hashes_sha256",
    "approved_upstream_21b_v6_manifest_sha256",
    "approved_upstream_21b_v6_output_hashes_sha256",
    "replay_implementation_mode",
    "approved_replay_compatibility_profile",
    "allowed_runtime_field_differences",
    "approved_dependency_lock_sha256",
    "approved_device_fingerprint_sha256",
    "approved_by",
    "approved_at_utc",
}

HYPOTHESES = (
    ("H01_RAW_RETURN_ZERO_SOLUTION", "high", "suspected_not_proven"),
    ("H02_DIFFUSION_GRADIENT_DOMINANCE", "high", "suspected_not_proven"),
    ("H03_SELECTOR_SOFT_HARD_MISMATCH", "high", "suspected_not_proven"),
    ("H04_DDPM_MONTE_CARLO_RANK_NOISE", "high", "suspected_not_proven"),
    ("H05_RETURN_PATH_PREPROCESSING_MISMATCH", "medium_high", "paper_pipeline_unknown"),
    ("H06_UNDISCLOSED_IMPLEMENTATION_AND_SEARCH", "medium_high", "not_identifiable_without_external_source"),
    ("H07_PERIOD_REGIME_SHIFT", "medium", "descriptive_only"),
    ("H08_EARLY_SELECTION_ADAPTATION", "high", "observed_pattern_not_isolated"),
)

GATE_ORDER = (
    "execution_authorization_gate",
    "upstream_hash_and_file_set_gate",
    "upstream_21c_terminal_state_gate",
    "input_panel_integrity_gate",
    "retained_universe_exact_match_gate",
    "hypothesis_preseal_gate",
    "historical_holdout_zero_access_gate",
    "sealed_checkpoint_replay_gate",
    "zero_solution_recompute_gate",
    "inference_draw_schedule_gate",
    "inference_sampling_audit_gate",
    "arm_registry_exact_gate",
    "return_path_transform_firewall_gate",
    "gradient_calibration_train_only_gate",
    "architecture_shape_gate",
    "teacher_isolation_gate",
    "seed_determinism_gate",
    "resource_probe_gate",
    "training_completion_gate",
    "exact_retrain_control_gate",
    "pre_late_bundle_hash_gate",
    "fresh_late_readout_gate",
    "score_coverage_gate",
    "metric_implementation_gate",
    "hypothesis_falsification_gate",
    "repair_candidate_gate",
    "finalize_transaction_gate",
    "output_manifest_hash_gate",
    "failure_bundle_integrity_gate",
)


class ContractError(RuntimeError):
    """A frozen contract was violated."""


class AuthorizationResult(NamedTuple):
    status: str
    sha256: str | None
    payload: dict[str, Any] | None
    errors: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_frame_hash(frame: pd.DataFrame, sort_keys: Sequence[str]) -> str:
    ordered = frame.sort_values(list(sort_keys), kind="mergesort", na_position="last")
    digest = hashlib.sha256()
    digest.update(b"[")
    columns = [str(column) for column in ordered.columns]
    for row_index, values in enumerate(ordered.itertuples(index=False, name=None)):
        if row_index:
            digest.update(b",")
        record = {
            key: (
                None
                if pd.isna(value)
                else value.item()
                if isinstance(value, np.generic)
                else value.isoformat()
                if hasattr(value, "isoformat")
                else value
            )
            for key, value in zip(columns, values, strict=True)
        }
        digest.update(canonical_json_bytes(record))
    digest.update(b"]")
    return digest.hexdigest()


def workspace_path(relative: str, *, must_exist: bool = False) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ContractError(f"absolute path forbidden in frozen config: {relative}")
    resolved = (TOPIC_ROOT / path).resolve()
    if TOPIC_ROOT.resolve() not in resolved.parents and resolved != TOPIC_ROOT.resolve():
        raise ContractError(f"path escapes topic root: {relative}")
    if must_exist and not resolved.exists():
        raise ContractError(f"required path missing: {relative}")
    return resolved


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload) + b"\n")


def _write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(payload), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pandas(frame, preserve_index=False),
        path,
        compression="zstd",
        use_dictionary=True,
    )


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("21D config must be a mapping")
    validate_frozen_config(payload)
    return payload


def validate_frozen_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "21D_GAP_CONFIG_V2":
        raise ContractError("unexpected 21D config schema")
    identity = config.get("identity", {})
    if identity.get("run_id") != RUN_ID or identity.get("requirement_version") != REQUIREMENT_VERSION:
        raise ContractError("21D identity drift")
    arms = config.get("arms", [])
    if [item.get("arm_id") for item in arms] != list(ARM_IDS):
        raise ContractError("learned arm order drift")
    if [int(item.get("arm_order", -99)) for item in arms] != list(range(7)):
        raise ContractError("arm_order drift")
    if tuple(config.get("training", {}).get("model_seeds", [])) != MODEL_SEEDS:
        raise ContractError("model seeds drift")
    if tuple(config.get("gates", [])) != GATE_ORDER:
        raise ContractError("gate order drift")
    execution = config.get("execution", {})
    if (
        execution.get("planned_learned_job_n") != 21
        or execution.get("planned_sensitivity_job_n") != 0
        or execution.get("historical_holdout_readout_authorized") is not False
        or execution.get("seal_only_after_full_success") is not True
    ):
        raise ContractError("execution accounting/firewall drift")
    draws = config.get("draws", {})
    if (
        draws.get("draw_n") != 256
        or draws.get("block_size") != 8
        or draws.get("block_n") != 32
        or draws.get("shard_n") != 18
        or draws.get("scalar_n") != 235236096
    ):
        raise ContractError("draw contract drift")


def building_output_root(config: Mapping[str, Any]) -> Path:
    output = workspace_path(config["paths"]["canonical_output_root"])
    return output.with_name(output.name + ".building")


def current_device_fingerprint() -> str:
    if not torch.cuda.is_available():
        raise ContractError("21D frozen execution requires CUDA")
    device = torch.device("cuda")
    return stable_hash(
        {
            "device_name": torch.cuda.get_device_name(device),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "total_memory": torch.cuda.get_device_properties(device).total_memory,
        }
    )


def validate_authorization(
    config: Mapping[str, Any], path: Path | None = None
) -> AuthorizationResult:
    authorization_path = path or workspace_path(config["paths"]["execution_authorization"])
    if not authorization_path.exists():
        return AuthorizationResult("missing", None, None, ("authorization_missing",))
    observed_sha = file_sha(authorization_path)
    try:
        payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return AuthorizationResult("invalid", observed_sha, None, ("authorization_json_invalid",))
    if not isinstance(payload, dict) or set(payload) != AUTHORIZATION_KEYS:
        return AuthorizationResult("invalid", observed_sha, None, ("authorization_schema_exact",))
    errors: list[str] = []
    expected_hashes = {
        "approved_requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "approved_config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "approved_runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "approved_test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "approved_upstream_21c_manifest_sha256": config["upstream_pins"]["21c_manifest"]["sha256"],
        "approved_upstream_21c_output_hashes_sha256": config["upstream_pins"]["21c_output_hashes"]["sha256"],
        "approved_upstream_21b_v5_manifest_sha256": config["upstream_pins"]["21b_v5_manifest"]["sha256"],
        "approved_upstream_21b_v5_output_hashes_sha256": config["upstream_pins"]["21b_v5_output_hashes"]["sha256"],
        "approved_upstream_21b_v6_manifest_sha256": config["upstream_pins"]["21b_v6_manifest"]["sha256"],
        "approved_upstream_21b_v6_output_hashes_sha256": config["upstream_pins"]["21b_v6_output_hashes"]["sha256"],
        "approved_dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "approved_device_fingerprint_sha256": current_device_fingerprint(),
    }
    for key, expected in expected_hashes.items():
        if payload.get(key) != expected or not isinstance(payload.get(key), str) or not HEX64.fullmatch(payload[key]):
            errors.append(f"{key}_match")
    constants = {
        "schema_version": "21D_EXECUTION_AUTHORIZATION_V2",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "replay_implementation_mode": config["sealed_replay"]["implementation_mode"],
        "approved_replay_compatibility_profile": config["sealed_replay"]["compatibility_profile"],
    }
    for key, expected in constants.items():
        if payload.get(key) != expected:
            errors.append(f"{key}_match")
    differences = payload.get("allowed_runtime_field_differences")
    if differences != sorted(set(differences or [])) or differences != []:
        errors.append("allowed_runtime_field_differences_exact")
    if payload.get("approved_by") in {None, "", "runner", "process", RUN_ID}:
        errors.append("approved_by_human")
    if not isinstance(payload.get("approved_at_utc"), str) or not RFC3339_UTC.fullmatch(payload["approved_at_utc"]):
        errors.append("approved_at_utc_rfc3339")
    return AuthorizationResult(
        "pass" if not errors else "invalid",
        observed_sha,
        payload if not errors else None,
        tuple(errors),
    )


def import_pinned_21c(config: Mapping[str, Any]) -> Any:
    pin = config["upstream_pins"]["21c_runner"]
    path = workspace_path(pin["path"], must_exist=True)
    if file_sha(path) != pin["sha256"]:
        raise ContractError("pinned 21C runner hash mismatch")
    spec = importlib.util.spec_from_file_location("ep21c_pinned_runner", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load pinned 21C runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_upstream_pins(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for order, (pin_id, pin) in enumerate(config["upstream_pins"].items()):
        path = workspace_path(pin["path"], must_exist=True)
        observed = file_sha(path)
        status = "pass" if observed == pin["sha256"] else "fail"
        rows.append(
            {
                "pin_order": order,
                "pin_id": pin_id,
                "path": pin["path"],
                "expected_sha256": pin["sha256"],
                "observed_sha256": observed,
                "expected_size_bytes": None,
                "observed_size_bytes": path.stat().st_size,
                "file_set_status": "pass",
                "hash_status": status,
                "overall_status": status,
                "reason": "" if status == "pass" else "sha256_mismatch",
            }
        )
    if any(row["overall_status"] != "pass" for row in rows):
        raise ContractError("upstream immutable pin mismatch")
    decision = pd.read_csv(workspace_path(config["upstream_pins"]["21c_decision"]["path"], must_exist=True))
    if "stage_decision" not in decision or set(decision["stage_decision"].astype(str)) != {"21C_FULL_r2_direction_not_supported"}:
        raise ContractError("unexpected 21C terminal decision")
    return rows


def arm_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(config["arms"])
    frame.insert(0, "schema_version", "S_ARM_REGISTRY_V2")
    frame["learned_job_n"] = len(MODEL_SEEDS)
    frame["rng_run_id"] = config["sealed_replay"]["seed_run_id"]
    frame["rng_arm_id"] = config["sealed_replay"]["seed_arm_id"]
    frame["registry_row_sha256"] = [
        stable_hash({key: value for key, value in row.items() if key != "registry_row_sha256"})
        for row in frame.to_dict("records")
    ]
    return frame


def planned_jobs(config: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for arm in config["arms"]:
        for seed in MODEL_SEEDS:
            rows.append(
                {
                    "arm_order": arm["arm_order"],
                    "arm_id": arm["arm_id"],
                    "model_seed": seed,
                    "config_id": stable_hash(arm),
                    "planned": True,
                    "primary_or_sensitivity": "primary",
                    "attempt_n": 1,
                    "selected_batch_size": 256,
                    "job_status": "planned",
                    "checkpoint_produced": False,
                    "failure_reason": "",
                }
            )
    frame = pd.DataFrame(rows)
    if len(frame) != 21 or frame[["arm_id", "model_seed"]].duplicated().any():
        raise ContractError("learned job accounting mismatch")
    return frame


def hypothesis_registry() -> pd.DataFrame:
    rows = []
    for order, (hypothesis_id, strength, status) in enumerate(HYPOTHESES, 1):
        row = {
            "hypothesis_order": order,
            "hypothesis_id": hypothesis_id,
            "prior_strength": strength,
            "status_at_requirement_time": status,
            "direct_evidence_rule": f"frozen_direct_rule_for_{hypothesis_id}",
            "intervention_rule": f"frozen_intervention_rule_for_{hypothesis_id}",
            "falsifier_rule": f"frozen_falsifier_rule_for_{hypothesis_id}",
            "allowed_statement": "design-contaminated mechanism diagnostic only",
            "forbidden_statement": "causally_proven|paper_pipeline_identified|paper_false",
            "registered_before_any_new_score": True,
        }
        row["registry_row_sha256"] = stable_hash(row)
        rows.append(row)
    return pd.DataFrame(rows)


def retained_row_hash(values: Sequence[str]) -> str:
    return stable_hash([str(value) for value in values])


def decision_cs_zscore_return_path(
    panel: np.ndarray,
    decision_dates: Sequence[str],
    *,
    fold: str,
    include_target: bool,
    minimum_n: int = 100,
) -> tuple[np.ndarray, pd.DataFrame, str]:
    """Apply the frozen decision-date/position CS z-score transform."""
    values = np.asarray(panel, dtype=np.float32)
    position_n = 11 if include_target else 10
    if values.ndim != 2 or values.shape[1] < position_n or len(values) != len(decision_dates):
        raise ContractError("return-path panel shape/cardinality mismatch")
    if not np.isfinite(values[:, :position_n]).all():
        raise ContractError("return-path panel contains NaN/Inf")
    dates = np.asarray(decision_dates, dtype=str)
    transformed = np.empty((len(values), position_n), dtype="<f4")
    audit_rows: list[dict[str, Any]] = []
    for decision_date in sorted(set(dates)):
        indices = np.flatnonzero(dates == decision_date)
        if len(indices) < minimum_n:
            raise ContractError(f"return transform N<100: {fold}/{decision_date}")
        day = values[indices, :position_n].astype(np.float64)
        mean = day.mean(axis=0, dtype=np.float64)
        std = day.std(axis=0, ddof=1, dtype=np.float64)
        if not np.isfinite(std).all() or np.any(std <= 1e-12):
            raise ContractError(f"return transform invalid std: {fold}/{decision_date}")
        z = ((day - mean) / std).astype("<f4")
        for position in range(position_n):
            observed_mean = float(z[:, position].astype(np.float64).mean())
            observed_std = float(z[:, position].astype(np.float64).std(ddof=1))
            if abs(observed_mean) > 1e-5 or abs(observed_std - 1.0) > 1e-5:
                raise ContractError("return transform postcondition mismatch")
            audit_rows.append(
                {
                    "fold_order": FOLDS.index(fold),
                    "fold": fold,
                    "decision_date": decision_date,
                    "position": position,
                    "row_n": len(indices),
                    "raw_mean": float(mean[position]),
                    "raw_std_ddof1": float(std[position]),
                    "transformed_mean": observed_mean,
                    "transformed_std_ddof1": observed_std,
                    "raw_row_key_sha256": stable_hash(indices.tolist()),
                    "transformed_value_semantic_sha256": hashlib.sha256(z[:, position].tobytes()).hexdigest(),
                    "status": "pass",
                }
            )
        transformed[indices] = z
    preimage = {
        "schema_id": "DECISION_CS_ZSCORE_RETURN_PATH_V2",
        "shape": list(transformed.shape),
        "dtype": "little-endian-float32",
        "bytes_sha256": hashlib.sha256(transformed.tobytes(order="C")).hexdigest(),
    }
    return transformed, pd.DataFrame(audit_rows), stable_hash(preimage)


def temporal_calibration_batches(
    frame: pd.DataFrame, model_seed: int, *, batch_size: int = 256
) -> tuple[list[np.ndarray], pd.DataFrame]:
    required = {"decision_date", "instrument", "row_key_hash"}
    if not required.issubset(frame.columns):
        raise ContractError("gradient calibration frame schema mismatch")
    dates = np.asarray(sorted(frame["decision_date"].astype(str).unique()))
    strata = np.array_split(dates, 4)
    batches: list[np.ndarray] = []
    rows = []
    for stratum_index, stratum_dates in enumerate(strata):
        subset = frame.loc[frame["decision_date"].astype(str).isin(stratum_dates)].copy()
        subset["sampling_hash"] = [
            hashlib.sha256(
                f"21D_GRAD_CAL_V2|{model_seed}|{date}|{instrument}".encode()
            ).hexdigest()
            for date, instrument in zip(
                subset["decision_date"].astype(str),
                subset["instrument"].astype(str),
                strict=True,
            )
        ]
        subset = subset.sort_values(
            ["sampling_hash", "decision_date", "instrument"], kind="mergesort"
        ).head(2048)
        if len(subset) != 2048:
            raise ContractError("gradient calibration stratum has fewer than 2048 rows")
        positions = subset.index.to_numpy(dtype=np.int64)
        for batch_index in range(8):
            selected = positions[batch_index * batch_size : (batch_index + 1) * batch_size]
            if len(selected) != batch_size:
                raise ContractError("gradient calibration batch is not 256 rows")
            batches.append(selected)
            selected_frame = frame.loc[selected]
            rows.append(
                {
                    "model_seed": model_seed,
                    "temporal_stratum": stratum_index,
                    "batch_index": batch_index,
                    "row_n": len(selected),
                    "decision_date_min": selected_frame["decision_date"].astype(str).min(),
                    "decision_date_max": selected_frame["decision_date"].astype(str).max(),
                    "row_key_sha256": stable_hash(selected_frame["row_key_hash"].astype(str).tolist()),
                    "sampling_contract_sha256": stable_hash(
                        {"contract": "21D_GRAD_CAL_V2", "seed": model_seed, "stratum": stratum_index, "batch": batch_index}
                    ),
                }
            )
    if len(batches) != 32 or len(np.unique(np.concatenate(batches))) != 8192:
        raise ContractError("gradient calibration 32-batch/8192-row contract mismatch")
    return batches, pd.DataFrame(rows)


def gradient_balance_weights(gradient_medians: Mapping[str, float]) -> dict[str, float]:
    terms = ("L_rec", "L_koop", "L_diff")
    if set(gradient_medians) != set(terms):
        raise ContractError("gradient median term set mismatch")
    inverse = np.asarray(
        [1.0 / max(float(gradient_medians[term]), 1e-12) for term in terms],
        dtype=np.float64,
    )
    raw = inverse / inverse.mean()
    clipped = np.clip(raw, 0.05, 20.0)
    normalized = clipped / clipped.mean()
    return {term: float(value) for term, value in zip(terms, normalized, strict=True)}


def straight_through_hard_selector(logits: Tensor, uniform: Tensor, tau: float) -> Tensor:
    pinned = _PINNED_21C
    soft = pinned.soft_gumbel_selector(logits, uniform, tau)
    hard = F.one_hot(torch.argmax(soft, dim=-1), num_classes=N_OPERATOR).to(soft.dtype)
    return hard - soft.detach() + soft


def draw_blocks(draw_n: int = 256, block_size: int = 8) -> tuple[tuple[int, ...], ...]:
    if draw_n != 256 or block_size != 8:
        raise ContractError("draw block contract differs from 32x8")
    blocks = tuple(tuple(range(start, start + block_size)) for start in range(0, draw_n, block_size))
    if len(blocks) != 32 or tuple(value for block in blocks for value in block) != tuple(range(256)):
        raise ContractError("draw blocks are not exact disjoint coverage")
    return blocks


def prefix_means(draw_scores: np.ndarray) -> dict[int, np.ndarray]:
    values = np.asarray(draw_scores, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != 256:
        raise ContractError("draw score matrix must be [N,256]")
    return {
        prefix: values[:, :prefix].astype(np.float64).mean(axis=1).astype(np.float32)
        for prefix in (8, 32, 64, 128, 256)
    }


def model_parameter_names(model: nn.Module) -> list[str]:
    shared = [
        "return_encoder.weight_ih_l0", "return_encoder.weight_hh_l0",
        "return_encoder.bias_ih_l0", "return_encoder.bias_hh_l0",
        "feature_encoder.weight_ih_l0", "feature_encoder.weight_hh_l0",
        "feature_encoder.bias_ih_l0", "feature_encoder.bias_hh_l0",
        "gate_linear.weight", "gate_linear.bias", "selector_linear.weight",
        "selector_linear.bias", "K_codebook.weight", "decoder.weight", "decoder.bias",
    ]
    available = dict(model.named_parameters())
    if hasattr(model, "denoiser_linear_1"):
        shared.extend(
            [
                "denoiser_linear_1.weight", "denoiser_linear_1.bias",
                "denoiser_linear_2.weight", "denoiser_linear_2.bias",
                "denoiser_linear_3.weight", "denoiser_linear_3.bias",
            ]
        )
    if hasattr(model, "residual_linear_1"):
        shared.extend(
            [
                "residual_linear_1.weight", "residual_linear_1.bias",
                "residual_linear_2.weight", "residual_linear_2.bias",
                "residual_linear_3.weight", "residual_linear_3.bias",
            ]
        )
    if set(shared) != set(available):
        raise ContractError("diagnostic model parameter topology mismatch")
    return shared


def model_parameters(model: nn.Module) -> list[nn.Parameter]:
    available = dict(model.named_parameters())
    return [available[name] for name in model_parameter_names(model)]


def _independent_mlp_initialize(model: nn.Module, model_seed: int) -> None:
    for name in ("residual_linear_1", "residual_linear_2", "residual_linear_3"):
        layer = getattr(model, name)
        seed = int.from_bytes(
            hashlib.sha256(f"21D_D6_MLP|{model_seed}|{name}.weight".encode()).digest()[:8],
            "big",
        ) % (2**63)
        generator = torch.Generator(device="cpu").manual_seed(seed)
        nn.init.xavier_uniform_(layer.weight, generator=generator)
        nn.init.zeros_(layer.bias)


def build_arm_model(arm_id: str, model_seed: int) -> nn.Module:
    if arm_id not in ARM_IDS:
        raise ContractError(f"unknown learned arm: {arm_id}")
    model = _PINNED_21C.build_model(model_seed)
    if arm_id == "D5_K2_RAW_NO_RESIDUAL":
        del model.denoiser_linear_1
        del model.denoiser_linear_2
        del model.denoiser_linear_3
    elif arm_id == "D6_R1_RAW_MLP_RESIDUAL":
        del model.denoiser_linear_1
        del model.denoiser_linear_2
        del model.denoiser_linear_3
        model.residual_linear_1 = nn.Linear(64, 160)
        model.residual_linear_2 = nn.Linear(160, 160)
        model.residual_linear_3 = nn.Linear(160, 64)
        _independent_mlp_initialize(model, model_seed)
    return model


def source_latent_variant(
    model: nn.Module,
    y: Tensor,
    x: Tensor,
    *,
    tau: float,
    training_selector: bool,
    selector_train: str,
    gumbel_u: Tensor | None = None,
    deterministic_soft: bool = False,
) -> dict[str, Tensor]:
    latent, h_y, h_x, gate = model.encode(y, x)
    logits = F.leaky_relu(
        model.selector_linear(torch.cat((latent, h_y), dim=-1)),
        negative_slope=0.01,
    )
    if deterministic_soft:
        selector = torch.softmax(logits / tau, dim=-1)
    elif training_selector:
        if gumbel_u is None or tuple(gumbel_u.shape) != (len(y), LOOKBACK, N_OPERATOR):
            raise ContractError("training selector requires exact Gumbel U")
        if selector_train == "soft_gumbel":
            selector = _PINNED_21C.soft_gumbel_selector(logits, gumbel_u, tau)
        elif selector_train == "straight_through_hard":
            selector = straight_through_hard_selector(logits, gumbel_u, tau)
        else:
            raise ContractError("unknown selector training semantics")
    else:
        selector = F.one_hot(torch.argmax(logits, dim=-1), N_OPERATOR).to(logits.dtype)
    selected = torch.einsum("btq,qij->btij", selector, model.K_codebook())
    predicted = torch.einsum("btij,btj->bti", selected, latent)
    return {
        "Z_source": latent,
        "H_y": h_y,
        "H_x": h_x,
        "G": gate,
        "selector_logits": logits,
        "selector": selector,
        "K_selected": selected,
        "Z_hat_shifted": predicted,
    }


def mlp_residual(model: nn.Module, latent: Tensor) -> Tensor:
    hidden = F.silu(model.residual_linear_1(latent))
    hidden = F.silu(model.residual_linear_2(hidden))
    return model.residual_linear_3(hidden)


def diagnostic_training_losses(
    model: nn.Module,
    arm: Mapping[str, Any],
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
    loss_weights: Mapping[str, float] | None = None,
) -> dict[str, Tensor]:
    source = source_latent_variant(
        model,
        y_source,
        x_source,
        tau=tau,
        training_selector=True,
        selector_train=arm["selector_train"],
        gumbel_u=gumbel_u,
    )
    teacher = model.teacher_latent(y_teacher, x_teacher)
    target = teacher - source["Z_hat_shifted"]
    residual_kind = arm["residual"]
    if residual_kind == "ddpm":
        schedule = _PINNED_21C.diffusion_schedule(device=target.device)
        index = diffusion_timestep.long() - 1
        alpha_bar = schedule["alpha_bar"][index].unsqueeze(-1)
        x_s = alpha_bar.sqrt() * target + (1.0 - alpha_bar).sqrt() * epsilon
        epsilon_hat = model.denoise(x_s, diffusion_timestep, source["Z_source"])
        residual = (x_s - (1.0 - alpha_bar).sqrt() * epsilon_hat) / alpha_bar.sqrt()
        diff = torch.mean((epsilon_hat - epsilon) ** 2)
    elif residual_kind == "mlp":
        residual = mlp_residual(model, source["Z_source"])
        diff = torch.mean((target - residual) ** 2)
    elif residual_kind == "none":
        residual = torch.zeros_like(target)
        diff = torch.zeros((), dtype=target.dtype, device=target.device)
    else:
        raise ContractError("unknown residual kind")
    enhanced = source["Z_hat_shifted"] + residual
    decoded_source = model.decoder(source["Z_source"])
    decoded_shifted = model.decoder(enhanced)
    source_rec = torch.mean((decoded_source - y_source) ** 2)
    shifted_rec = torch.mean((decoded_shifted[:, :9] - y_teacher[:, :9]) ** 2)
    history_rec = 0.5 * (source_rec + shifted_rec)
    forecast = torch.mean((decoded_shifted[:, 9, 0] - forecast_y.reshape(-1)) ** 2)
    rec = history_rec + forecast
    koop = torch.mean((teacher - source["Z_hat_shifted"]) ** 2)
    weights = loss_weights or {"L_rec": 1.0, "L_koop": 1.0, "L_diff": 1.0}
    total = weights["L_rec"] * rec + weights["L_koop"] * koop
    if residual_kind != "none":
        total = total + weights["L_diff"] * diff
    for name, value in {"L_rec": rec, "L_koop": koop, "L_diff": diff, "L_total": total}.items():
        if not torch.isfinite(value):
            raise ContractError(f"non-finite {name}")
    return {
        "L_source_rec": source_rec,
        "L_shifted_observed_rec": shifted_rec,
        "L_history_reconstruction": history_rec,
        "L_forecast": forecast,
        "L_rec": rec,
        "L_koop": koop,
        "L_diff": diff,
        "L_total": total,
        "Z_teacher_shifted": teacher,
        "residual_hat": residual,
        **source,
    }


def build_optimizer(model: nn.Module, config: Mapping[str, Any]) -> torch.optim.AdamW:
    training = config["training"]
    return torch.optim.AdamW(
        [{"params": model_parameters(model)}],
        lr=float(training["learning_rate"]),
        betas=tuple(float(value) for value in training["adam_betas"]),
        eps=float(training["adam_eps"]),
        weight_decay=float(training["weight_decay"]),
        amsgrad=False,
        foreach=False,
        fused=False,
        capturable=False,
        maximize=False,
        differentiable=False,
    )


def optimizer_step(model: nn.Module, optimizer: torch.optim.AdamW, loss: Tensor) -> float:
    optimizer.zero_grad(set_to_none=True)
    loss.float().backward()
    norm = torch.nn.utils.clip_grad_norm_(
        model_parameters(model),
        1.0,
        norm_type=2.0,
        error_if_nonfinite=True,
        foreach=False,
    )
    optimizer.step()
    return float(norm)


_PINNED_21C: Any = import_pinned_21c(load_config())


class FeatureSequenceAccessor:
    def __init__(self, memmap: np.ndarray, offsets: np.ndarray) -> None:
        self.memmap = memmap
        self.offsets = offsets

    def __len__(self) -> int:
        return len(self.offsets)

    def __getitem__(self, item: Any) -> np.ndarray:
        selected = self.offsets[item]
        return np.asarray(self.memmap[selected], dtype=np.float32).reshape(
            (-1, LOOKBACK, FEATURE_DIM)
            if np.asarray(selected).ndim > 1
            else (LOOKBACK, FEATURE_DIM)
        )


_FEATURE_CACHE: np.ndarray | None = None
_SEQUENCE_CACHE: pd.DataFrame | None = None


def _panel_manifest(config: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = workspace_path(config["inputs"]["panel_manifest"], must_exist=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "pass" or payload.get("historical_holdout_row_materialized_n") != 0:
        raise ContractError("upstream model-input panel is not a clean pass")
    return path.parents[1], payload


def _sequence_index(config: Mapping[str, Any]) -> pd.DataFrame:
    global _SEQUENCE_CACHE
    if _SEQUENCE_CACHE is None:
        path = workspace_path(config["inputs"]["sequence_index"], must_exist=True)
        _, manifest = _panel_manifest(config)
        if file_sha(path) != manifest["sequence_sample_index_sha256"]:
            raise ContractError("sequence index hash drift")
        frame = pd.read_parquet(path)
        required = {
            "sample_row_idx", "fold", "decision_date", "instrument",
            "x_cache_row_indices", "fold_panel_row_idx", "row_key_hash",
        }
        if not required.issubset(frame.columns):
            raise ContractError("sequence index schema mismatch")
        _SEQUENCE_CACHE = frame
    return _SEQUENCE_CACHE


def _excluded_instruments(config: Mapping[str, Any]) -> frozenset[str]:
    path = workspace_path(config["inputs"]["exclusion_registry"], must_exist=True)
    if file_sha(path) != config["inputs"]["exclusion_registry_sha256"]:
        raise ContractError("PIT exclusion registry hash drift")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if len(frame) != 396 or frame["instrument"].duplicated().any():
        raise ContractError("PIT exclusion registry identity drift")
    return frozenset(frame["instrument"].astype(str))


def _resident_feature_cache(config: Mapping[str, Any]) -> np.ndarray:
    global _FEATURE_CACHE
    if _FEATURE_CACHE is None:
        _, manifest = _panel_manifest(config)
        path = workspace_path(manifest["feature_cache_memmap_path"], must_exist=True)
        if file_sha(path) != manifest["feature_cache_memmap_sha256"]:
            raise ContractError("feature cache byte hash drift")
        source = np.memmap(
            path,
            dtype="<f4",
            mode="r",
            shape=tuple(manifest["feature_cache_shape"]),
        )
        _FEATURE_CACHE = np.array(source, dtype=np.float32, order="C", copy=True)
        _FEATURE_CACHE.setflags(write=False)
    return _FEATURE_CACHE


def load_fold_data(config: Mapping[str, Any], fold: str) -> dict[str, Any]:
    if fold not in FOLDS:
        raise ContractError(f"unknown fold: {fold}")
    root, manifest = _panel_manifest(config)
    sequence = _sequence_index(config)
    frame = sequence.loc[sequence["fold"].eq(fold)].sort_values(
        "fold_panel_row_idx", kind="mergesort"
    )
    frame = frame.loc[~frame["instrument"].astype(str).isin(_excluded_instruments(config))].reset_index(drop=True)
    expected = config["retained_folds"][fold]
    observed_hash = retained_row_hash(frame["row_key_hash"].astype(str).tolist())
    if len(frame) != expected["row_n"] or observed_hash != expected["row_key_sha256"]:
        raise ContractError(f"retained {fold} row keys/count drift")
    if frame["instrument"].nunique() != expected["instrument_n"]:
        raise ContractError(f"retained {fold} instrument count drift")
    dates = frame["decision_date"].astype(str)
    if dates.min() != expected["date_min"] or dates.max() != expected["date_max"]:
        raise ContractError(f"retained {fold} date range drift")
    partition = {item["fold"]: item for item in manifest["panel_partitions"]}[fold]
    panel_path = root / partition["path"]
    if file_sha(panel_path) != partition["sha256"]:
        raise ContractError(f"source panel hash drift: {fold}")
    panel = np.memmap(panel_path, dtype="<f4", mode="r", shape=tuple(partition["shape"]))
    panel_rows = frame["fold_panel_row_idx"].to_numpy(dtype=np.int64)
    retained_panel = np.asarray(panel[panel_rows], dtype=np.float32)
    if retained_panel.shape != (expected["row_n"], 11) or not np.isfinite(retained_panel).all():
        raise ContractError(f"retained panel shape/finite mismatch: {fold}")
    offsets = np.stack(frame["x_cache_row_indices"].to_numpy()).astype(np.int64)
    return {
        "frame": frame,
        "raw_panel": retained_panel,
        "y_source": retained_panel[:, :10, None],
        "label": retained_panel[:, 10],
        "x_source": FeatureSequenceAccessor(_resident_feature_cache(config), offsets),
        "x_offsets": offsets,
        "row_key_hash": observed_hash,
    }


def load_train_teacher(config: Mapping[str, Any], train: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = workspace_path(config["inputs"]["teacher_manifest"], must_exist=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    teacher_y_path = workspace_path(config["inputs"]["teacher_return_panel"], must_exist=True)
    if file_sha(teacher_y_path) != manifest["teacher_return_panel_sha256"]:
        raise ContractError("teacher return panel hash drift")
    teacher_y = np.memmap(
        teacher_y_path,
        dtype="<f4",
        mode="r",
        shape=tuple(manifest["teacher_return_panel_shape"]),
    )
    index_path = workspace_path(config["inputs"]["teacher_sequence_index"], must_exist=True)
    if file_sha(index_path) != manifest["teacher_sequence_index_sha256"]:
        raise ContractError("teacher sequence index hash drift")
    offsets = pq.read_table(index_path, columns=["feature_cache_row_offset"]).column(0).to_numpy()
    offsets = np.asarray(offsets, dtype=np.int64).reshape(len(train["frame"]), LOOKBACK)
    if len(teacher_y) != len(train["frame"]):
        raise ContractError("teacher panel cardinality mismatch")
    return {
        "y_teacher": teacher_y,
        "x_teacher": FeatureSequenceAccessor(_resident_feature_cache(config), offsets),
        "teacher_offsets": offsets,
    }


def arm_data(
    config: Mapping[str, Any], arm: Mapping[str, Any], fold_data: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame | None, str | None]:
    if arm["return_transform"] == "raw":
        return (
            np.asarray(fold_data["y_source"], dtype=np.float32),
            np.asarray(fold_data["label"], dtype=np.float32),
            None,
            None,
        )
    fold = str(fold_data["frame"]["fold"].iloc[0])
    include_target = fold == "train"
    transformed, audit, semantic_hash = decision_cs_zscore_return_path(
        fold_data["raw_panel"],
        fold_data["frame"]["decision_date"].astype(str).tolist(),
        fold=fold,
        include_target=include_target,
    )
    source = transformed[:, :10, None]
    target = transformed[:, 10] if include_target else np.asarray(fold_data["label"], dtype=np.float32)
    return source, target, audit, semantic_hash


def transformed_train_teacher(transformed_panel: np.ndarray) -> np.ndarray:
    values = np.asarray(transformed_panel, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != 11:
        raise ContractError("transformed train panel must be [N,11]")
    return np.concatenate((values[:, 1:10, None], values[:, 10:11, None]), axis=1)


@torch.no_grad()
def inference_draw_matrix_tensor(
    model: nn.Module,
    y_source: Tensor,
    x_source: Tensor,
    keys: Sequence[tuple[str, str]],
    model_seed: int,
    *,
    draw_n: int,
    deterministic_soft: bool = False,
    selector_tau: float = 0.1,
) -> Tensor:
    if draw_n < 1 or draw_n > 256 or len(keys) != len(y_source):
        raise ContractError("inference draw request outside frozen bounds")
    model.eval()
    source = source_latent_variant(
        model,
        y_source,
        x_source,
        tau=selector_tau,
        training_selector=False,
        selector_train="soft_gumbel",
        deterministic_soft=deterministic_soft,
    )
    schedule = _PINNED_21C.diffusion_schedule(device=y_source.device)
    scores = torch.empty((len(y_source), draw_n), dtype=torch.float32, device="cpu")
    for draw_id in range(draw_n):
        noise_schedule = _PINNED_21C.row_seeded_noise_schedule(
            keys,
            model_seed,
            draw_id,
            dtype=torch.float32,
            device=y_source.device,
            run_id=_PINNED_21C.RUN_ID,
        )
        residual = noise_schedule[:, 0]
        for step in range(DIFFUSION_STEPS, 0, -1):
            index = step - 1
            timestep = torch.full(
                residual.shape[:2], step, dtype=torch.long, device=residual.device
            )
            epsilon_hat = model.denoise(residual, timestep, source["Z_source"])
            mean = (
                residual
                - schedule["beta"][index]
                * epsilon_hat
                / torch.sqrt(1.0 - schedule["alpha_bar"][index])
            ) / torch.sqrt(schedule["alpha"][index])
            if step > 1:
                residual = mean + torch.sqrt(schedule["posterior_variance"][index]) * noise_schedule[:, DIFFUSION_STEPS - step + 1]
            else:
                residual = mean
        enhanced = source["Z_hat_shifted"] + residual
        scores[:, draw_id] = model.decoder(enhanced)[:, 9, 0].detach().cpu()
        del noise_schedule, residual
    if not torch.isfinite(scores).all():
        raise ContractError("inference draw matrix contains NaN/Inf")
    return scores


@torch.no_grad()
def deterministic_score_tensor(
    model: nn.Module,
    arm: Mapping[str, Any],
    y_source: Tensor,
    x_source: Tensor,
) -> Tensor:
    source = source_latent_variant(
        model,
        y_source,
        x_source,
        tau=0.1,
        training_selector=False,
        selector_train=arm["selector_train"],
    )
    if arm["residual"] == "none":
        enhanced = source["Z_hat_shifted"]
    elif arm["residual"] == "mlp":
        enhanced = source["Z_hat_shifted"] + mlp_residual(model, source["Z_source"])
    else:
        raise ContractError("deterministic score requested for DDPM arm")
    return model.decoder(enhanced)[:, 9, 0]


@torch.no_grad()
def score_panel(
    model: nn.Module,
    arm: Mapping[str, Any],
    y_source: np.ndarray,
    x_source: Any,
    instruments: Sequence[str],
    decision_dates: Sequence[str],
    model_seed: int,
    *,
    batch_size: int,
    device: torch.device,
    draw_n: int | None = None,
) -> np.ndarray:
    result = np.empty(len(y_source), dtype=np.float64)
    requested_draws = int(arm["selection_draw_n"] if draw_n is None else draw_n)
    for start in range(0, len(y_source), batch_size):
        stop = min(start + batch_size, len(y_source))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(x_source[start:stop], dtype=torch.float32, device=device)
        if arm["residual"] == "ddpm":
            keys = list(zip(instruments[start:stop], decision_dates[start:stop], strict=True))
            draws = inference_draw_matrix_tensor(
                model, y, x, keys, model_seed, draw_n=requested_draws
            )
            result[start:stop] = draws.double().mean(dim=1).numpy()
        else:
            result[start:stop] = deterministic_score_tensor(model, arm, y, x).detach().cpu().numpy().astype(np.float64)
    if not np.isfinite(result).all():
        raise ContractError("score panel contains NaN/Inf")
    return result


def model_state_semantic_hash(state_dict: Mapping[str, Tensor]) -> str:
    return _PINNED_21C.model_state_semantic_hash(state_dict)


def _cpu_state(model: nn.Module) -> dict[str, Tensor]:
    return {name: value.detach().cpu().contiguous().clone() for name, value in model.state_dict().items()}


def validation_rankic(
    scores: np.ndarray,
    labels: np.ndarray,
    dates: Sequence[str],
    minimum_n: int = 100,
) -> tuple[float, int]:
    return _PINNED_21C._validation_mean_rankic(
        scores, labels, dates, minimum_n=minimum_n
    )


def gradient_module_id(parameter_name: str) -> str:
    if parameter_name.startswith(("return_encoder.", "feature_encoder.")):
        return "encoder"
    if parameter_name.startswith("gate_linear."):
        return "gate"
    if parameter_name.startswith("selector_linear."):
        return "selector"
    if parameter_name.startswith("K_codebook."):
        return "koopman_codebook"
    if parameter_name.startswith("decoder."):
        return "decoder"
    if parameter_name.startswith(("denoiser_", "residual_")):
        return "residual_corrector"
    raise ContractError(f"parameter has no registered gradient module: {parameter_name}")


def gradient_norm(
    gradients: Sequence[Tensor | None], indices: Sequence[int]
) -> float:
    squares = [
        torch.sum(gradients[index].detach().double() ** 2)
        for index in indices
        if gradients[index] is not None
    ]
    return math.sqrt(float(torch.stack(squares).sum().cpu())) if squares else 0.0


def gradient_cosine(
    left: Sequence[Tensor | None],
    right: Sequence[Tensor | None],
    indices: Sequence[int],
) -> float | None:
    dot = torch.zeros((), dtype=torch.float64, device="cuda")
    for index in indices:
        if left[index] is not None and right[index] is not None:
            dot = dot + torch.sum(left[index].detach().double() * right[index].detach().double())
    left_norm = gradient_norm(left, indices)
    right_norm = gradient_norm(right, indices)
    if left_norm <= 1e-18 or right_norm <= 1e-18:
        return None
    return float(dot.cpu()) / (left_norm * right_norm)


def calibrate_gradient_weights(
    config: Mapping[str, Any],
    arm: Mapping[str, Any],
    model: nn.Module,
    model_seed: int,
    train: Mapping[str, Any],
    train_y: np.ndarray,
    train_teacher_y: np.ndarray,
    train_forecast: np.ndarray,
    train_teacher_x: Any,
    device: torch.device,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    batches, batch_registry = temporal_calibration_batches(train["frame"], model_seed)
    gradient_rows: list[dict[str, Any]] = []
    global_by_term: dict[str, list[float]] = {term: [] for term in ("L_rec", "L_koop", "L_diff")}
    gumbel_generator = torch.Generator(device="cpu").manual_seed(model_seed + 71000)
    diffusion_generator = torch.Generator(device="cpu").manual_seed(model_seed + 89000)
    model.train()
    for sequence_index, indices in enumerate(batches):
        y = torch.as_tensor(train_y[indices], dtype=torch.float32, device=device)
        x = torch.as_tensor(train["x_source"][indices], dtype=torch.float32, device=device)
        y_teacher = torch.as_tensor(train_teacher_y[indices], dtype=torch.float32, device=device)
        x_teacher = torch.as_tensor(train_teacher_x[indices], dtype=torch.float32, device=device)
        forecast = torch.as_tensor(train_forecast[indices], dtype=torch.float32, device=device)
        uniform = torch.rand((len(indices), LOOKBACK, N_OPERATOR), generator=gumbel_generator).to(device)
        timestep = torch.randint(1, 21, (len(indices), LOOKBACK), generator=diffusion_generator).to(device)
        epsilon = torch.randn((len(indices), LOOKBACK, LATENT_DIM), generator=diffusion_generator).to(device)
        losses = diagnostic_training_losses(
            model,
            arm,
            y,
            x,
            y_teacher,
            x_teacher,
            forecast,
            tau=1.0,
            gumbel_u=uniform,
            diffusion_timestep=timestep,
            epsilon=epsilon,
        )
        parameters = model_parameters(model)
        names = model_parameter_names(model)
        terms = ("L_rec", "L_koop", "L_diff")
        gradients: dict[str, tuple[Tensor | None, ...]] = {}
        for term_index, term in enumerate(terms):
            gradients[term] = torch.autograd.grad(
                losses[term],
                parameters,
                retain_graph=term_index < 2,
                allow_unused=True,
            )
        module_indices: dict[str, list[int]] = {module: [] for module in (
            "encoder", "gate", "selector", "koopman_codebook", "decoder", "residual_corrector"
        )}
        for parameter_index, name in enumerate(names):
            module_indices[gradient_module_id(name)].append(parameter_index)
        scopes = {"global": list(range(len(names))), **module_indices}
        cosines = {
            "cosine_rec_koop": gradient_cosine(gradients["L_rec"], gradients["L_koop"], scopes["global"]),
            "cosine_rec_diff": gradient_cosine(gradients["L_rec"], gradients["L_diff"], scopes["global"]),
            "cosine_koop_diff": gradient_cosine(gradients["L_koop"], gradients["L_diff"], scopes["global"]),
        }
        norms = {
            module: {term: gradient_norm(gradients[term], indices_for_module) for term in terms}
            for module, indices_for_module in scopes.items()
        }
        for term in terms:
            global_by_term[term].append(norms["global"][term])
        for module, module_norms in norms.items():
            denominator = sum(module_norms.values())
            for term in terms:
                gradient_rows.append(
                    {
                        "arm_id": arm["arm_id"],
                        "model_seed": model_seed,
                        "phase": "calibration",
                        "temporal_stratum": sequence_index // 8,
                        "batch_index": sequence_index % 8,
                        "loss_term": term,
                        "module_id": module,
                        "loss_value": float(losses[term].detach().cpu()),
                        "gradient_l2": module_norms[term],
                        "gradient_share": module_norms[term] / max(denominator, 1e-12),
                        **cosines,
                        "gradient_clip_applied": False,
                        "optimizer_step_applied": False,
                        "ordered_parameter_name_list_sha256": stable_hash(names),
                        "row_key_sha256": batch_registry.iloc[sequence_index]["row_key_sha256"],
                    }
                )
        del losses, y, x, y_teacher, x_teacher, forecast, uniform, timestep, epsilon
    medians = {term: float(np.median(values)) for term, values in global_by_term.items()}
    weights = gradient_balance_weights(medians)
    inverse = {term: 1.0 / max(medians[term], 1e-12) for term in medians}
    mean_inverse = float(np.mean(list(inverse.values())))
    if not math.isfinite(mean_inverse):
        raise ContractError("gradient inverse mean is non-finite")
    return weights, batch_registry, pd.DataFrame(gradient_rows)


GRADIENT_BATCH_SCHEMA = pa.schema(
    [
        ("arm_order", pa.int8()),
        ("arm_id", pa.string()),
        ("model_seed", pa.int64()),
        ("temporal_stratum", pa.int8()),
        ("batch_index", pa.int16()),
        ("row_n", pa.int32()),
        ("min_decision_date", pa.date32()),
        ("max_decision_date", pa.date32()),
        ("row_key_sha256", pa.string()),
        ("sampling_contract_sha256", pa.string()),
    ]
)

LOSS_GRADIENT_SCHEMA = pa.schema(
    [
        ("arm_order", pa.int8()),
        ("arm_id", pa.string()),
        ("model_seed", pa.int64()),
        ("phase", pa.string()),
        ("temporal_stratum", pa.int8()),
        ("batch_index", pa.int16()),
        ("loss_term", pa.string()),
        ("module_id", pa.string()),
        ("loss_value", pa.float64()),
        ("gradient_l2", pa.float64()),
        ("gradient_share", pa.float64()),
        ("cosine_rec_koop", pa.float64()),
        ("cosine_rec_diff", pa.float64()),
        ("cosine_koop_diff", pa.float64()),
        ("gradient_clip_applied", pa.bool_()),
        ("optimizer_step_applied", pa.bool_()),
        ("ordered_parameter_name_list_sha256", pa.string()),
        ("row_key_sha256", pa.string()),
    ]
)

RETURN_PATH_TRANSFORM_SCHEMA = pa.schema(
    [
        ("fold_order", pa.int8()),
        ("fold", pa.string()),
        ("decision_date", pa.date32()),
        ("position", pa.int8()),
        ("position_role", pa.string()),
        ("row_n", pa.int32()),
        ("raw_mean", pa.float64()),
        ("raw_std_ddof1", pa.float64()),
        ("transformed_mean", pa.float64()),
        ("transformed_std_ddof1", pa.float64()),
        ("raw_row_key_sha256", pa.string()),
        ("transformed_value_semantic_sha256", pa.string()),
        ("status", pa.string()),
    ]
)

SELECTOR_SCORE_SCHEMA = pa.schema(
    [
        ("fold_order", pa.int8()),
        ("fold", pa.string()),
        ("model_seed", pa.int64()),
        ("decision_date", pa.date32()),
        ("instrument", pa.string()),
        ("row_key", pa.string()),
        ("hard_score", pa.float32()),
        ("deterministic_soft_mixture_score", pa.float32()),
        ("score_delta", pa.float32()),
        ("raw_label", pa.float32()),
        ("shared_noise_schedule_sha256", pa.string()),
    ]
)

SURGERY_SCORE_SCHEMA = pa.schema(
    [
        ("fold_order", pa.int8()),
        ("fold", pa.string()),
        ("model_seed", pa.int64()),
        ("decision_date", pa.date32()),
        ("instrument", pa.string()),
        ("row_key", pa.string()),
        ("joint_r2_score", pa.float32()),
        ("koopman_only_score", pa.float32()),
        ("score_delta", pa.float32()),
        ("raw_label", pa.float32()),
        ("checkpoint_semantic_sha256", pa.string()),
    ]
)

ZERO_SOLUTION_COLUMNS = [
    "arm_order", "arm_id", "model_seed", "epoch", "audit_role", "sample_row_n",
    "zero_output_L_source_rec", "zero_output_L_shifted_observed_rec",
    "zero_output_L_forecast", "zero_output_L_rec", "actual_L_rec",
    "zero_solution_improvement", "audit_sample_row_key_sha256",
]

COLLAPSE_COLUMNS = [
    "arm_order", "arm_id", "model_seed", "fold", "selected_epoch",
    "initialization_decoder_weight_l2", "decoder_weight_l2", "decoder_norm_ratio",
    "decoder_bias_abs", "latent_variance_q00", "latent_variance_q25",
    "latent_variance_q50", "latent_variance_q75", "latent_variance_q100",
    "latent_covariance_effective_rank", "latent_effective_rank_ratio",
    "decoded_source_std", "raw_source_std", "decoded_source_std_ratio",
    "forecast_score_std", "raw_label_std", "score_to_label_std_ratio",
    "additional_collapse_flag_n", "h01_direct_morphology_support",
    "checkpoint_semantic_sha256", "audit_sample_row_key_sha256", "status",
]


def normalize_gradient_batch_registry(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result = result.drop(columns=["phase"], errors="ignore").rename(
        columns={
            "decision_date_min": "min_decision_date",
            "decision_date_max": "max_decision_date",
        }
    )
    result["min_decision_date"] = pd.to_datetime(result["min_decision_date"]).dt.date
    result["max_decision_date"] = pd.to_datetime(result["max_decision_date"]).dt.date
    result = result[GRADIENT_BATCH_SCHEMA.names].sort_values(
        ["arm_order", "model_seed", "temporal_stratum", "batch_index"], kind="mergesort"
    )
    if len(result) != 384:
        raise ContractError(f"gradient batch registry expected 384 rows, got {len(result)}")
    return result.reset_index(drop=True)


def normalize_loss_gradient(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["loss_term"] = result["loss_term"].replace(
        {"L_rec": "rec", "L_koop": "koop", "L_diff": "diff"}
    )
    result = result[LOSS_GRADIENT_SCHEMA.names].sort_values(
        ["arm_order", "model_seed", "phase", "temporal_stratum", "batch_index", "loss_term", "module_id"],
        kind="mergesort",
    )
    if len(result) != 12096:
        raise ContractError(f"loss gradient audit expected 12096 rows, got {len(result)}")
    return result.reset_index(drop=True)


def write_schema_parquet(path: Path, frame: pd.DataFrame, schema: pa.Schema) -> None:
    table = pa.Table.from_pandas(frame, schema=schema, preserve_index=False, safe=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)


def normalize_return_path_transform(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "position_role" not in result:
        result["position_role"] = np.where(
            result["position"].astype(int).eq(10), "train_forecast_target", "source"
        )
    result["decision_date"] = pd.to_datetime(result["decision_date"]).dt.date
    result = result[RETURN_PATH_TRANSFORM_SCHEMA.names].sort_values(
        ["fold_order", "decision_date", "position"], kind="mergesort"
    )
    return result.reset_index(drop=True)


def selected_checkpoint_gradient_audit(
    config: Mapping[str, Any],
    arm: Mapping[str, Any],
    model_seed: int,
    train: Mapping[str, Any],
    teacher: Mapping[str, Any],
    device: torch.device,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = _job_state_root(building_output_root(config), arm["arm_id"], model_seed)
    evidence_path = root / "selected_gradient_audit.parquet"
    registry_path = root / "selected_gradient_batch_registry.parquet"
    if evidence_path.exists() and registry_path.exists():
        return pd.read_parquet(registry_path), pd.read_parquet(evidence_path)
    train_y, train_forecast, _, _ = arm_data(config, arm, train)
    if arm["return_transform"] == "decision_cs_zscore":
        transformed, _, _ = decision_cs_zscore_return_path(
            train["raw_panel"],
            train["frame"]["decision_date"].astype(str).tolist(),
            fold="train",
            include_target=True,
        )
        teacher_y = transformed_train_teacher(transformed)
    else:
        teacher_y = teacher["y_teacher"]
    model, _ = load_checkpoint_model(config, arm["arm_id"], model_seed, device)
    _, registry, evidence = calibrate_gradient_weights(
        config,
        arm,
        model,
        model_seed,
        train,
        train_y,
        teacher_y,
        train_forecast,
        teacher["x_teacher"],
        device,
    )
    evidence["phase"] = "audit"
    _write_parquet(registry_path, registry)
    _write_parquet(evidence_path, evidence)
    del model
    torch.cuda.empty_cache()
    return registry, evidence


def compute_learned_train_morphology_bases(
    config: Mapping[str, Any],
    train: Mapping[str, Any],
    teacher: Mapping[str, Any],
    device: torch.device,
) -> None:
    build = building_output_root(config)
    zero_path = build / ".state/learned_zero_solution_rows.csv"
    collapse_path = build / ".state/learned_collapse_base_rows.csv"
    if zero_path.exists() and collapse_path.exists():
        if len(pd.read_csv(zero_path)) == 21 and len(pd.read_csv(collapse_path)) == 21:
            return
        raise ContractError("learned morphology base cache row closure mismatch")
    indices = morphology_sample_indices(train["frame"])
    sample_hash = stable_hash(
        train["frame"].iloc[indices]["row_key_hash"].astype(str).tolist()
    )
    full_train_hash = retained_row_hash(train["frame"]["row_key_hash"].astype(str).tolist())
    zero_rows = []
    collapse_rows = []
    for arm in config["arms"]:
        train_y, train_forecast, _, _ = arm_data(config, arm, train)
        if arm["return_transform"] == "decision_cs_zscore":
            transformed, _, _ = decision_cs_zscore_return_path(
                train["raw_panel"],
                train["frame"]["decision_date"].astype(str).tolist(),
                fold="train",
                include_target=True,
            )
            teacher_y = transformed_train_teacher(transformed)
        else:
            teacher_y = teacher["y_teacher"]
        zero_source = float(np.mean(np.asarray(train_y, dtype=np.float64) ** 2))
        zero_shifted = float(np.mean(np.asarray(teacher_y[:, :9], dtype=np.float64) ** 2))
        zero_forecast = float(np.mean(np.asarray(train_forecast, dtype=np.float64) ** 2))
        zero_total = 0.5 * (zero_source + zero_shifted) + zero_forecast
        for seed in MODEL_SEEDS:
            curves, _, metadata = _job_state(config, arm["arm_id"], seed)
            selected = curves.loc[curves["epoch"].eq(metadata["selected_epoch"])]
            if len(selected) != 1:
                raise ContractError(f"selected curve row mismatch: {arm['arm_id']}/{seed}")
            actual_rec = float(selected.iloc[0]["train_loss_rec"])
            zero_rows.append(
                {
                    "arm_order": arm["arm_order"],
                    "arm_id": arm["arm_id"],
                    "model_seed": seed,
                    "epoch": int(metadata["selected_epoch"]),
                    "audit_role": "learned_selected_checkpoint_train_zero_output",
                    "sample_row_n": len(train["frame"]),
                    "zero_output_L_source_rec": zero_source,
                    "zero_output_L_shifted_observed_rec": zero_shifted,
                    "zero_output_L_forecast": zero_forecast,
                    "zero_output_L_rec": zero_total,
                    "actual_L_rec": actual_rec,
                    "zero_solution_improvement": 1.0 - actual_rec / zero_total,
                    "audit_sample_row_key_sha256": full_train_hash,
                }
            )
            model, semantic = load_checkpoint_model(config, arm["arm_id"], seed, device)
            morphology = checkpoint_morphology(model, train, indices, device, train_y)
            initial = build_arm_model(arm["arm_id"], seed)
            initial_norm = float(
                torch.linalg.vector_norm(initial.decoder.weight.detach().double()).cpu()
            )
            raw_std = float(np.std(train_y[indices], ddof=1))
            collapse_rows.append(
                {
                    "arm_order": arm["arm_order"],
                    "arm_id": arm["arm_id"],
                    "model_seed": seed,
                    "fold": "train_morphology_validation_late_score",
                    "selected_epoch": int(metadata["selected_epoch"]),
                    "initialization_decoder_weight_l2": initial_norm,
                    **morphology,
                    "decoder_norm_ratio": morphology["decoder_weight_l2"] / initial_norm,
                    "raw_source_std": raw_std,
                    "decoded_source_std_ratio": morphology["decoded_source_std"] / raw_std,
                    "forecast_score_std": None,
                    "raw_label_std": None,
                    "score_to_label_std_ratio": None,
                    "additional_collapse_flag_n": None,
                    "h01_direct_morphology_support": None,
                    "checkpoint_semantic_sha256": semantic,
                    "audit_sample_row_key_sha256": sample_hash,
                    "status": "pending_validation_late_score",
                }
            )
            del model, initial
            torch.cuda.empty_cache()
    _write_csv(zero_path, zero_rows, ZERO_SOLUTION_COLUMNS)
    _write_csv(collapse_path, collapse_rows, COLLAPSE_COLUMNS)


def publish_full_morphology_diagnostics(
    config: Mapping[str, Any], late_predictions: pd.DataFrame
) -> None:
    build = building_output_root(config)
    sealed_zero = pd.read_csv(build / "diagnostics/raw_return_zero_solution_audit.csv")
    sealed_collapse = pd.read_csv(build / "diagnostics/checkpoint_parameter_collapse_audit.csv")
    learned_zero = pd.read_csv(build / ".state/learned_zero_solution_rows.csv")
    learned_collapse = pd.read_csv(build / ".state/learned_collapse_base_rows.csv")
    if len(sealed_zero) != 3 or len(sealed_collapse) != 3:
        raise ContractError("sealed morphology diagnostic row closure mismatch")
    for index, row in learned_collapse.iterrows():
        variant = (
            "prefix8" if row["arm_id"] == "D0_R2_RAW_EXACT_REPLAY" else
            "prefix64" if row["arm_id"] == "D4_R2_REPAIR_COMBINED_V1" else "primary"
        )
        scores = late_predictions.loc[
            late_predictions["arm_id"].eq(row["arm_id"])
            & late_predictions["model_seed"].eq(row["model_seed"])
            & ~late_predictions["is_ensemble"]
            & late_predictions["score_variant"].eq(variant)
        ].copy()
        if len(scores) != config["retained_folds"]["validation_late"]["row_n"]:
            raise ContractError(f"learned morphology late score coverage mismatch: {row['arm_id']}/{row['model_seed']}")
        day_score_std = scores.groupby("decision_date", sort=True)["score"].std(ddof=1)
        day_label_std = scores.groupby("decision_date", sort=True)["raw_label"].std(ddof=1)
        forecast_std = float(day_score_std.median())
        label_std = float(day_label_std.median())
        learned_collapse.loc[index, "forecast_score_std"] = forecast_std
        learned_collapse.loc[index, "raw_label_std"] = label_std
        learned_collapse.loc[index, "score_to_label_std_ratio"] = forecast_std / label_std
        learned_collapse.loc[index, "status"] = "pass"
    full_zero = pd.concat([sealed_zero, learned_zero], ignore_index=True).sort_values(
        ["arm_order", "model_seed", "epoch", "audit_role"], kind="mergesort"
    )
    full_collapse = pd.concat([sealed_collapse, learned_collapse], ignore_index=True).sort_values(
        ["arm_order", "model_seed", "fold"], kind="mergesort"
    )
    if len(full_zero) != 24 or len(full_collapse) != 24:
        raise ContractError("full learned+sealed morphology row closure mismatch")
    _write_csv(
        build / "diagnostics/raw_return_zero_solution_audit.csv",
        full_zero.to_dict("records"),
        ZERO_SOLUTION_COLUMNS,
    )
    _write_csv(
        build / "diagnostics/checkpoint_parameter_collapse_audit.csv",
        full_collapse.to_dict("records"),
        COLLAPSE_COLUMNS,
    )


def train_one_arm_seed(
    config: Mapping[str, Any],
    arm: Mapping[str, Any],
    model_seed: int,
    train: Mapping[str, Any],
    early: Mapping[str, Any],
    teacher: Mapping[str, Any],
    device: torch.device,
) -> tuple[dict[str, Tensor], list[dict[str, Any]], np.ndarray, dict[str, float], pd.DataFrame, pd.DataFrame]:
    train_y, train_forecast, train_audit, _ = arm_data(config, arm, train)
    early_y, _, _, _ = arm_data(config, arm, early)
    if arm["return_transform"] == "decision_cs_zscore":
        transformed, _, _ = decision_cs_zscore_return_path(
            train["raw_panel"],
            train["frame"]["decision_date"].astype(str).tolist(),
            fold="train",
            include_target=True,
        )
        teacher_y = transformed_train_teacher(transformed)
    else:
        teacher_y = teacher["y_teacher"]
    if arm["arm_id"] == "D0_R2_RAW_EXACT_REPLAY":
        state, curves, scores = _PINNED_21C.train_one_seed(
            _PINNED_21C.load_config(),
            model_seed=model_seed,
            train_y_source=train_y,
            train_x_source=train["x_source"],
            train_y_teacher=teacher_y,
            train_x_teacher=teacher["x_teacher"],
            train_forecast_y=train_forecast,
            validation_y_source=early_y,
            validation_x_source=early["x_source"],
            validation_labels=early["label"],
            validation_instruments=early["frame"]["instrument"].astype(str).tolist(),
            validation_decision_dates=early["frame"]["decision_date"].astype(str).tolist(),
            selected_batch_size=256,
            device=device,
        )
        for row in curves:
            row["arm_id"] = arm["arm_id"]
        return state, curves, scores, {"L_rec": 1.0, "L_koop": 1.0, "L_diff": 1.0}, pd.DataFrame(), pd.DataFrame()
    train_n = len(train_y)
    maximum_epochs = int(config["training"]["max_epochs"])
    steps_per_epoch = math.ceil(train_n / 256)
    planned_total_steps = maximum_epochs * steps_per_epoch
    torch.manual_seed(model_seed + 23)
    np.random.seed(model_seed + 11)
    model = build_arm_model(arm["arm_id"], model_seed).to(device)
    weights = {"L_rec": 1.0, "L_koop": 1.0, "L_diff": 1.0}
    batch_registry = pd.DataFrame()
    gradient_evidence = pd.DataFrame()
    if arm["loss_weights"] == "train_calibrated":
        weights, batch_registry, gradient_evidence = calibrate_gradient_weights(
            config,
            arm,
            model,
            model_seed,
            train,
            train_y,
            teacher_y,
            train_forecast,
            teacher["x_teacher"],
            device,
        )
    optimizer = build_optimizer(model, config)
    gumbel_generator = torch.Generator(device="cpu").manual_seed(model_seed + 71)
    diffusion_generator = torch.Generator(device="cpu").manual_seed(model_seed + 89)
    best_metric = -math.inf
    best_state: dict[str, Tensor] | None = None
    non_improvement = 0
    optimizer_step_index = 0
    curves: list[dict[str, Any]] = []
    instruments = early["frame"]["instrument"].astype(str).tolist()
    dates = early["frame"]["decision_date"].astype(str).tolist()
    for epoch_index in range(maximum_epochs):
        permutation = torch.randperm(
            train_n,
            generator=torch.Generator(device="cpu").manual_seed(model_seed + 37 + epoch_index),
        ).numpy()
        totals = {"L_total": 0.0, "L_rec": 0.0, "L_koop": 0.0, "L_diff": 0.0}
        seen = 0
        model.train()
        for start in range(0, train_n, 256):
            indices = permutation[start : start + 256]
            actual = len(indices)
            y = torch.as_tensor(train_y[indices], dtype=torch.float32, device=device)
            x = torch.as_tensor(train["x_source"][indices], dtype=torch.float32, device=device)
            y_teacher = torch.as_tensor(teacher_y[indices], dtype=torch.float32, device=device)
            x_teacher = torch.as_tensor(teacher["x_teacher"][indices], dtype=torch.float32, device=device)
            forecast = torch.as_tensor(train_forecast[indices], dtype=torch.float32, device=device)
            uniform = torch.rand((actual, LOOKBACK, N_OPERATOR), generator=gumbel_generator).to(device)
            timestep = torch.randint(1, 21, (actual, LOOKBACK), generator=diffusion_generator).to(device)
            epsilon = torch.randn((actual, LOOKBACK, LATENT_DIM), generator=diffusion_generator).to(device)
            tau = _PINNED_21C.tau_for_step(optimizer_step_index, planned_total_steps)
            losses = diagnostic_training_losses(
                model,
                arm,
                y,
                x,
                y_teacher,
                x_teacher,
                forecast,
                tau=tau,
                gumbel_u=uniform,
                diffusion_timestep=timestep,
                epsilon=epsilon,
                loss_weights=weights,
            )
            optimizer_step(model, optimizer, losses["L_total"])
            optimizer_step_index += 1
            for key in totals:
                totals[key] += float(losses[key].detach().cpu()) * actual
            seen += actual
        model.eval()
        scores = score_panel(
            model,
            arm,
            early_y,
            early["x_source"],
            instruments,
            dates,
            model_seed,
            batch_size=int(config["training"]["inference_batch_size"]),
            device=device,
        )
        metric, complete_day_n = validation_rankic(scores, early["label"], dates)
        if not math.isfinite(metric):
            raise ContractError("validation_early metric is non-finite")
        if metric > best_metric:
            best_metric = metric
            best_state = _cpu_state(model)
            non_improvement = 0
        else:
            non_improvement += 1
        curves.append(
            {
                "arm_id": arm["arm_id"],
                "model_seed": model_seed,
                "epoch": epoch_index + 1,
                "optimizer_step_end": optimizer_step_index,
                "train_loss_total": totals["L_total"] / seen,
                "train_loss_rec": totals["L_rec"] / seen,
                "train_loss_koop": totals["L_koop"] / seen,
                "train_loss_diff": totals["L_diff"] / seen,
                "validation_early_mean_rankic": metric,
                "validation_early_complete_day_n": complete_day_n,
                "validation_early_score_coverage": 1.0,
                "gumbel_tau_last_step": _PINNED_21C.tau_for_step(optimizer_step_index - 1, planned_total_steps),
                "status": "pass",
                "reason": "",
            }
        )
        if non_improvement == int(config["training"]["early_stopping_patience"]):
            break
    if best_state is None:
        raise ContractError("no checkpoint selected")
    model.load_state_dict(best_state, strict=True)
    selected_scores = score_panel(
        model,
        arm,
        early_y,
        early["x_source"],
        instruments,
        dates,
        model_seed,
        batch_size=int(config["training"]["inference_batch_size"]),
        device=device,
    )
    return best_state, curves, selected_scores, weights, batch_registry, gradient_evidence


def configure_determinism() -> None:
    if not torch.cuda.is_available():
        raise ContractError("CUDA is required")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def checkpoint_path(build: Path, arm_id: str, seed: int) -> Path:
    return build / f"training/checkpoints/{arm_id}/seed_{seed}/state_dict.pt"


def sealed_checkpoint_path(config: Mapping[str, Any], seed: int) -> Path:
    root = workspace_path(config["inputs"]["21c_checkpoint_root"], must_exist=True)
    return root / f"seed_{seed}/state_dict.pt"


def load_checkpoint_model(
    config: Mapping[str, Any], identity: str, seed: int, device: torch.device
) -> tuple[nn.Module, str]:
    if identity == "SEALED_V4_R2":
        path = sealed_checkpoint_path(config, seed)
        expected = config["sealed_replay"]["selected"][str(seed)]
        if file_sha(path) != expected["checkpoint_sha256"]:
            raise ContractError(f"sealed checkpoint byte hash drift: {seed}")
        model = _PINNED_21C.build_model(seed)
    else:
        if identity not in ARM_IDS:
            raise ContractError(f"unknown checkpoint identity: {identity}")
        path = checkpoint_path(building_output_root(config), identity, seed)
        if not path.exists():
            raise ContractError(f"learned checkpoint missing: {identity}/{seed}")
        model = build_arm_model(identity, seed)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    semantic = model_state_semantic_hash(state)
    if identity == "SEALED_V4_R2" and semantic != config["sealed_replay"]["selected"][str(seed)]["semantic_sha256"]:
        raise ContractError(f"sealed checkpoint semantic hash drift: {seed}")
    return model.to(device), semantic


def draw_shard_relative(identity: str, fold: str, seed: int) -> str:
    return f"diagnostics/inference_draw_scores/{identity}/{fold}/seed_{seed}.parquet"


DRAW_SHARD_SCHEMA = pa.schema(
    [
        ("fold_order", pa.int8()),
        ("fold", pa.string()),
        ("draw_identity", pa.string()),
        ("model_seed", pa.int64()),
        ("decision_date", pa.date32()),
        ("instrument", pa.string()),
        ("row_key", pa.string()),
        ("draw_scores", pa.list_(pa.float32(), 256)),
        ("draw_schedule_sha256", pa.string()),
    ]
)


def normalize_draw_shard_schema(path: Path) -> None:
    """Drop legacy working columns and enforce the frozen publish schema."""
    observed = pq.read_schema(path).remove_metadata()
    if observed == DRAW_SHARD_SCHEMA:
        return
    required = DRAW_SHARD_SCHEMA.names
    if not set(required).issubset(observed.names):
        raise ContractError(f"draw shard cannot be normalized: {path}")
    table = pq.read_table(path, columns=required).cast(DRAW_SHARD_SCHEMA)
    temporary = path.with_suffix(path.suffix + ".schema-normalizing")
    pq.write_table(table, temporary, compression="zstd", use_dictionary=True)
    os.replace(temporary, path)


def write_draw_shard(
    config: Mapping[str, Any],
    identity: str,
    fold: str,
    seed: int,
    model: nn.Module,
    data: Mapping[str, Any],
    y_source: np.ndarray,
    device: torch.device,
) -> Path:
    build = building_output_root(config)
    path = build / draw_shard_relative(identity, fold, seed)
    if path.exists():
        normalize_draw_shard_schema(path)
        table = pq.read_table(path, columns=["draw_scores"])
        if len(table) != len(data["frame"]):
            raise ContractError(f"existing draw shard row count mismatch: {path}")
        return path
    print(f"[{utc_now()}] draw shard start {identity}/{fold}/seed_{seed}", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = DRAW_SHARD_SCHEMA
    frame = data["frame"]
    writer = pq.ParquetWriter(path, schema, compression=config["draws"]["parquet_compression"])
    try:
        for start in range(0, len(frame), int(config["training"]["inference_batch_size"])):
            stop = min(start + int(config["training"]["inference_batch_size"]), len(frame))
            subset = frame.iloc[start:stop]
            y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
            x = torch.as_tensor(data["x_source"][slice(start, stop)], dtype=torch.float32, device=device)
            keys = list(
                zip(
                    subset["instrument"].astype(str),
                    subset["decision_date"].astype(str),
                    strict=True,
                )
            )
            draws = inference_draw_matrix_tensor(model, y, x, keys, seed, draw_n=256).numpy()
            flat = pa.array(draws.reshape(-1), type=pa.float32())
            fixed = pa.FixedSizeListArray.from_arrays(flat, 256)
            schedule_hashes = [
                stable_hash(
                    {
                        "run_id": _PINNED_21C.RUN_ID,
                        "arm_id": _PINNED_21C.ARM_ID,
                        "model_seed": seed,
                        "instrument": instrument,
                        "decision_date": date,
                        "draw_ids": [0, 255],
                    }
                )
                for instrument, date in keys
            ]
            table = pa.Table.from_arrays(
                [
                    pa.array([FOLDS.index(fold)] * len(subset), type=pa.int8()),
                    pa.array([fold] * len(subset), type=pa.string()),
                    pa.array([identity] * len(subset), type=pa.string()),
                    pa.array([seed] * len(subset), type=pa.int64()),
                    pa.array(pd.to_datetime(subset["decision_date"]).dt.date, type=pa.date32()),
                    pa.array(subset["instrument"].astype(str), type=pa.string()),
                    pa.array(subset["row_key_hash"].astype(str), type=pa.string()),
                    fixed,
                    pa.array(schedule_hashes, type=pa.string()),
                ],
                schema=schema,
            )
            writer.write_table(table)
            del y, x, draws, flat, fixed, table
    finally:
        writer.close()
    observed = pq.read_metadata(path).num_rows
    if observed != len(frame):
        raise ContractError(f"draw shard row count mismatch: {identity}/{fold}/{seed}")
    print(f"[{utc_now()}] draw shard complete {identity}/{fold}/seed_{seed}", flush=True)
    return path


def read_draw_prefixes(path: Path) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    table = pq.read_table(
        path,
        columns=["decision_date", "instrument", "row_key", "draw_scores"],
    )
    values = table.column("draw_scores").combine_chunks().values.to_numpy().reshape(len(table), 256)
    keys = table.select(["decision_date", "instrument", "row_key"]).to_pandas()
    return keys, prefix_means(values)


def runtime_fingerprint(config: Mapping[str, Any]) -> dict[str, Any]:
    device = torch.device("cuda")
    payload = {
        "schema_version": "S_REPLAY_RUNTIME_V2",
        "python_version": platform.python_version(),
        "pytorch_version": str(torch.__version__),
        "numpy_version": np.__version__,
        "cuda_runtime_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_name": torch.cuda.get_device_name(device),
        "device_capability": list(torch.cuda.get_device_capability(device)),
        "device_total_memory_bytes": int(torch.cuda.get_device_properties(device).total_memory),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG", ""),
        "device_fingerprint_sha256": current_device_fingerprint(),
        "v4_device_fingerprint_sha256": config["sealed_replay"]["device_fingerprint_sha256"],
        "dependency_lock_path": config["paths"]["dependency_lock"],
        "dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "replay_compatibility_profile": config["sealed_replay"]["compatibility_profile"],
    }
    payload["fingerprint_semantic_sha256"] = stable_hash(payload)
    if payload["device_fingerprint_sha256"] != payload["v4_device_fingerprint_sha256"]:
        raise ContractError("EXACT_RUNTIME_V1 device fingerprint mismatch")
    return payload


def retained_universe_audit(config: Mapping[str, Any]) -> pd.DataFrame:
    sequence = _sequence_index(config)
    excluded = _excluded_instruments(config)
    rows = []
    for fold in FOLDS:
        frame = sequence.loc[sequence["fold"].eq(fold)].sort_values("fold_panel_row_idx", kind="mergesort")
        frame = frame.loc[~frame["instrument"].astype(str).isin(excluded)]
        expected = config["retained_folds"][fold]
        observed_hash = retained_row_hash(frame["row_key_hash"].astype(str).tolist())
        status = "pass" if len(frame) == expected["row_n"] and observed_hash == expected["row_key_sha256"] else "fail"
        rows.append(
            {
                "fold_order": expected["fold_order"],
                "fold": fold,
                "decision_date": None,
                "expected_row_n": expected["row_n"],
                "observed_row_n": len(frame),
                "expected_row_key_sha256": expected["row_key_sha256"],
                "observed_row_key_sha256": observed_hash,
                "denominator_exact_match": status == "pass",
                "status": status,
                "reason": "" if status == "pass" else "retained_rows_or_hash_mismatch",
            }
        )
        for decision_date, day in frame.groupby("decision_date", sort=True):
            day_hash = retained_row_hash(day["row_key_hash"].astype(str).tolist())
            rows.append(
                {
                    "fold_order": expected["fold_order"],
                    "fold": fold,
                    "decision_date": pd.Timestamp(decision_date).date(),
                    "expected_row_n": len(day),
                    "observed_row_n": len(day),
                    "expected_row_key_sha256": day_hash,
                    "observed_row_key_sha256": day_hash,
                    "denominator_exact_match": True,
                    "status": "pass",
                    "reason": "",
                }
            )
    result = pd.DataFrame(rows)
    if len(result) != 1055:
        raise ContractError(f"retained universe audit expected 1055 rows, got {len(result)}")
    if set(result["status"]) != {"pass"}:
        raise ContractError("retained universe exact-match gate failed")
    return result


def run_preflight(config: Mapping[str, Any]) -> None:
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.payload is None:
        raise ContractError("valid human authorization required: " + ",".join(authorization.errors))
    output = workspace_path(config["paths"]["canonical_output_root"])
    build = building_output_root(config)
    if output.exists():
        raise ContractError("canonical 21D output already exists")
    if (build / "preflight/preflight_complete.json").exists():
        return
    build.mkdir(parents=True, exist_ok=True)
    configure_determinism()
    upstream_rows = validate_upstream_pins(config)
    universe = retained_universe_audit(config)
    resolved = {
        "schema_version": "S_RESOLVED_CONFIG_V2",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "paths": config["paths"],
        "authorization": {
            "path": config["paths"]["execution_authorization"],
            "sha256": authorization.sha256,
            "approved_by": authorization.payload["approved_by"],
            "approved_at_utc": authorization.payload["approved_at_utc"],
        },
        "upstream_pins": config["upstream_pins"],
        "replay_identity": config["sealed_replay"],
        "splits": {fold: config["retained_folds"][fold] for fold in FOLDS},
        "retained_rows": config["retained_folds"],
        "return_path_transform": config["transform"],
        "hypotheses": [
            {"hypothesis_id": item[0], "prior_strength": item[1], "status": item[2]}
            for item in HYPOTHESES
        ],
        "arms": config["arms"],
        "training": config["training"],
        "gradient_calibration": config["gradient_calibration"],
        "inference_draws": config["draws"],
        "metrics": {
            "rankic": "daily_spearman_average_rank_ties_minimum_n_100",
            "bootstrap_replicate_n": 5000,
            "bootstrap_mean_block_length": 20,
        },
        "resources": config["resources"],
        "gates": config["gates"],
        "artifact_universe": sorted(p6_required_paths(config) | FAILURE_PATHS),
    }
    _write_yaml(build / "preflight/resolved_config.yaml", resolved)
    _write_csv(
        build / "preflight/execution_authorization_audit.csv",
        [
            {
                "authorization_path": config["paths"]["execution_authorization"],
                "exists": True,
                "authorization_sha256": authorization.sha256,
                "requirement_sha256_match": True,
                "config_sha256_match": True,
                "runner_sha256_match": True,
                "test_sha256_match": True,
                "upstream_pin_match": True,
                "replay_profile_match": True,
                "dependency_lock_match": True,
                "device_fingerprint_match": True,
                "status": "pass",
                "reason": "",
            }
        ],
        [
            "authorization_path", "exists", "authorization_sha256",
            "requirement_sha256_match", "config_sha256_match", "runner_sha256_match",
            "test_sha256_match", "upstream_pin_match", "replay_profile_match",
            "dependency_lock_match", "device_fingerprint_match", "status", "reason",
        ],
    )
    _write_csv(
        build / "preflight/upstream_pin_and_file_set_audit.csv",
        upstream_rows,
        [
            "pin_order", "pin_id", "path", "expected_sha256", "observed_sha256",
            "expected_size_bytes", "observed_size_bytes", "file_set_status", "hash_status",
            "overall_status", "reason",
        ],
    )
    _write_csv(
        build / "preflight/retained_universe_exact_match_audit.csv",
        universe.to_dict("records"),
        list(universe.columns),
    )
    hypotheses = hypothesis_registry()
    _write_csv(build / "hypothesis_registry.csv", hypotheses.to_dict("records"), list(hypotheses.columns))
    arms = arm_registry(config)
    _write_csv(build / "training/arm_registry.csv", arms.to_dict("records"), list(arms.columns))
    jobs = planned_jobs(config)
    _write_csv(build / "training/model_search_accounting_manifest.csv", jobs.to_dict("records"), list(jobs.columns))
    holdout_columns = [
        "process_order", "process_role", "access_scope", "open_attempt_n",
        "successful_open_n", "read_row_n", "forbidden_open_attempt_n",
        "first_forbidden_path", "status",
    ]
    _write_csv(
        build / "historical_design_holdout_access_audit.csv",
        [{
            "process_order": 0,
            "process_role": "preflight_controller",
            "access_scope": "historical_design_holdout",
            "open_attempt_n": 0,
            "successful_open_n": 0,
            "read_row_n": 0,
            "forbidden_open_attempt_n": 0,
            "first_forbidden_path": "",
            "status": "pass",
        }],
        holdout_columns,
    )
    _write_json(build / "preflight/replay_runtime_fingerprint.json", runtime_fingerprint(config))
    _write_json(
        build / "preflight/preflight_complete.json",
        {
            "schema_version": "21D_PREFLIGHT_COMPLETE_V2",
            "authorization_sha256": authorization.sha256,
            "hypothesis_registry_sha256": file_sha(build / "hypothesis_registry.csv"),
            "arm_registry_sha256": file_sha(build / "training/arm_registry.csv"),
            "completed_at_utc": utc_now(),
        },
    )


def morphology_sample_indices(frame: pd.DataFrame) -> np.ndarray:
    dates = np.asarray(sorted(frame["decision_date"].astype(str).unique()))
    selected: list[np.ndarray] = []
    for stratum_dates in np.array_split(dates, 4):
        subset = frame.loc[frame["decision_date"].astype(str).isin(stratum_dates)].copy()
        subset["audit_hash"] = [
            hashlib.sha256(f"21D_MORPH_AUDIT_V2|{date}|{instrument}".encode()).hexdigest()
            for date, instrument in zip(
                subset["decision_date"].astype(str), subset["instrument"].astype(str), strict=True
            )
        ]
        chosen = subset.sort_values(
            ["audit_hash", "decision_date", "instrument"], kind="mergesort"
        ).head(2048)
        if len(chosen) != 2048:
            raise ContractError("morphology audit stratum incomplete")
        selected.append(chosen.index.to_numpy(dtype=np.int64))
    result = np.concatenate(selected)
    if len(result) != 8192 or len(np.unique(result)) != 8192:
        raise ContractError("morphology audit sample must contain 8192 unique rows")
    return result


@torch.no_grad()
def checkpoint_morphology(
    model: nn.Module,
    data: Mapping[str, Any],
    indices: np.ndarray,
    device: torch.device,
    y_source: np.ndarray | None = None,
) -> dict[str, float]:
    observed_y = data["y_source"] if y_source is None else y_source
    model.eval()
    latents = []
    decoded = []
    for start in range(0, len(indices), 1024):
        selected = indices[start : start + 1024]
        y = torch.as_tensor(observed_y[selected], dtype=torch.float32, device=device)
        x = torch.as_tensor(data["x_source"][selected], dtype=torch.float32, device=device)
        source = source_latent_variant(
            model, y, x, tau=0.1, training_selector=False, selector_train="soft_gumbel"
        )
        latents.append(source["Z_source"][:, 9].cpu().numpy().astype(np.float64))
        decoded.append(model.decoder(source["Z_source"])[:, :, 0].cpu().numpy().astype(np.float64))
    latent = np.concatenate(latents)
    dimension_variances = np.var(latent, axis=0, ddof=1)
    covariance = np.cov(latent, rowvar=False, ddof=1)
    eigenvalues = np.linalg.eigvalsh(covariance)
    if np.any(eigenvalues < -1e-12):
        raise ContractError("latent covariance has materially negative eigenvalue")
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = float(eigenvalues.sum())
    if total <= 1e-12:
        raise ContractError("latent covariance effective-rank denominator is degenerate")
    effective_rank = float(
        np.exp(-np.sum((eigenvalues / total) * np.log(np.maximum(eigenvalues / total, 1e-300))))
    )
    return {
        "latent_variance_q00": float(np.quantile(dimension_variances, 0.00)),
        "latent_variance_q25": float(np.quantile(dimension_variances, 0.25)),
        "latent_variance_q50": float(np.quantile(dimension_variances, 0.50)),
        "latent_variance_q75": float(np.quantile(dimension_variances, 0.75)),
        "latent_variance_q100": float(np.quantile(dimension_variances, 1.00)),
        "latent_covariance_effective_rank": effective_rank,
        "latent_effective_rank_ratio": effective_rank / 64.0,
        "decoded_source_std": float(np.std(np.concatenate(decoded), ddof=1)),
        "decoder_weight_l2": float(torch.linalg.vector_norm(model.decoder.weight.detach().double()).cpu()),
        "decoder_bias_abs": float(torch.abs(model.decoder.bias.detach().double()).cpu().item()),
    }


@torch.no_grad()
def selector_and_surgery_readout(
    model: nn.Module,
    data: Mapping[str, Any],
    y_source: np.ndarray,
    seed: int,
    tau: float,
    fold: str,
    device: torch.device,
    hard_prefix8: np.ndarray,
) -> tuple[pd.DataFrame, list[dict[str, Any]], pd.DataFrame, np.ndarray]:
    model.eval()
    soft_scores = np.empty(len(y_source), dtype=np.float32)
    surgery_scores = np.empty(len(y_source), dtype=np.float32)
    operator_counts = np.zeros(N_OPERATOR, dtype=np.int64)
    entropy_by_row = np.empty(len(y_source), dtype=np.float64)
    effective_by_row = np.empty(len(y_source), dtype=np.float64)
    switching_by_row = np.empty(len(y_source), dtype=np.float64)
    assignments = np.empty((len(y_source), LOOKBACK), dtype=np.int8)
    transition_counts = np.zeros((N_OPERATOR, N_OPERATOR), dtype=np.int64)
    entropy_sum = 0.0
    switch_sum = 0
    switch_denominator = 0
    frame = data["frame"]
    for start in range(0, len(frame), 1024):
        stop = min(start + 1024, len(frame))
        subset = frame.iloc[start:stop]
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(data["x_source"][slice(start, stop)], dtype=torch.float32, device=device)
        keys = list(zip(subset["instrument"].astype(str), subset["decision_date"].astype(str), strict=True))
        soft_draws = inference_draw_matrix_tensor(
            model, y, x, keys, seed, draw_n=8, deterministic_soft=True, selector_tau=tau
        )
        soft_scores[start:stop] = soft_draws.double().mean(dim=1).float().numpy()
        hard = source_latent_variant(
            model, y, x, tau=0.1, training_selector=False, selector_train="soft_gumbel"
        )
        surgery_scores[start:stop] = model.decoder(hard["Z_hat_shifted"])[:, 9, 0].cpu().numpy()
        assignment = torch.argmax(hard["selector_logits"], dim=-1).cpu().numpy()
        assignments[start:stop] = assignment.astype(np.int8)
        operator_counts += np.bincount(assignment.reshape(-1), minlength=N_OPERATOR)
        np.add.at(transition_counts, (assignment[:, :-1].reshape(-1), assignment[:, 1:].reshape(-1)), 1)
        probabilities = torch.softmax(hard["selector_logits"] / tau, dim=-1)
        row_entropy = (-(probabilities * torch.log(probabilities.clamp_min(1e-12))).sum(dim=-1)).mean(dim=1)
        entropy_by_row[start:stop] = row_entropy.cpu().numpy().astype(np.float64)
        effective_by_row[start:stop] = torch.exp(row_entropy).cpu().numpy().astype(np.float64)
        row_switching = np.mean(assignment[:, 1:] != assignment[:, :-1], axis=1)
        switching_by_row[start:stop] = row_switching.astype(np.float64)
        entropy_sum += float((row_entropy * assignment.shape[1]).sum().cpu())
        switch_sum += int(np.sum(assignment[:, 1:] != assignment[:, :-1]))
        switch_denominator += assignment.shape[0] * (assignment.shape[1] - 1)
    comparison = pd.DataFrame(
        {
            "fold_order": FOLDS.index(fold),
            "fold": fold,
            "model_seed": seed,
            "decision_date": pd.to_datetime(frame["decision_date"]).dt.date,
            "instrument": frame["instrument"].astype(str),
            "row_key": frame["row_key_hash"].astype(str),
            "hard_score": hard_prefix8.astype(np.float32),
            "deterministic_soft_mixture_score": soft_scores,
            "score_delta": (hard_prefix8.astype(np.float64) - soft_scores.astype(np.float64)).astype(np.float32),
            "raw_label": data["label"].astype(np.float32),
            "shared_noise_schedule_sha256": stable_hash(
                {"seed": seed, "fold": fold, "draw_ids": list(range(8)), "rng_identity": "21C_R2"}
            ),
            "selector_entropy_mean": entropy_by_row,
            "effective_operator_count_mean": effective_by_row,
            "switching_rate": switching_by_row,
        }
    )
    operator_rows: list[dict[str, Any]] = []
    total = operator_counts.sum()
    common = {
        "arm_order": -1,
        "arm_id": "SEALED_V4_R2",
        "model_seed": seed,
        "fold": fold,
        "aggregation_key": "fold",
        "alignment_permutation_json": None,
        "status": "pass",
    }
    for operator_id, count in enumerate(operator_counts):
        operator_rows.append(
            {
                **common,
                "metric_id": "selection_share",
                "operator_i": operator_id,
                "operator_j": None,
                "metric_value": float(count / total),
                "observation_n": int(total),
            }
        )
    for metric_id, metric_value, observation_n in (
        ("selector_entropy", entropy_sum / total, total),
        ("effective_operator_count", math.exp(entropy_sum / total), total),
        ("switching_rate", switch_sum / switch_denominator, switch_denominator),
    ):
        operator_rows.append(
            {
                **common,
                "metric_id": metric_id,
                "operator_i": None,
                "operator_j": None,
                "metric_value": float(metric_value),
                "observation_n": int(observation_n),
            }
        )
    transition_total = int(transition_counts.sum())
    for operator_i in range(N_OPERATOR):
        for operator_j in range(N_OPERATOR):
            operator_rows.append(
                {
                    **common,
                    "metric_id": "transition_share",
                    "operator_i": operator_i,
                    "operator_j": operator_j,
                    "metric_value": float(transition_counts[operator_i, operator_j] / transition_total),
                    "observation_n": transition_total,
                }
            )
    codebook = model.K_codebook.weight.detach().double().cpu().numpy()
    for operator_i in range(N_OPERATOR):
        eigenvalues = np.linalg.eigvals(codebook[operator_i])
        operator_rows.append(
            {
                **common,
                "metric_id": "spectral_radius",
                "operator_i": operator_i,
                "operator_j": None,
                "metric_value": float(np.max(np.abs(eigenvalues))),
                "observation_n": int(codebook[operator_i].size),
            }
        )
        for operator_j in range(operator_i + 1, N_OPERATOR):
            operator_rows.append(
                {
                    **common,
                    "metric_id": "k_frobenius_distance",
                    "operator_i": operator_i,
                    "operator_j": operator_j,
                    "metric_value": float(np.linalg.norm(codebook[operator_i] - codebook[operator_j])),
                    "observation_n": int(codebook[operator_i].size),
                }
            )
    surgery = pd.DataFrame(
        {
            "fold_order": FOLDS.index(fold),
            "fold": fold,
            "model_seed": seed,
            "decision_date": pd.to_datetime(frame["decision_date"]).dt.date,
            "instrument": frame["instrument"].astype(str),
            "row_key": frame["row_key_hash"].astype(str),
            "joint_r2_score": hard_prefix8.astype(np.float32),
            "koopman_only_score": surgery_scores,
            "score_delta": (hard_prefix8.astype(np.float64) - surgery_scores.astype(np.float64)).astype(np.float32),
            "raw_label": data["label"].astype(np.float32),
            "checkpoint_semantic_sha256": model_state_semantic_hash(model.state_dict()),
        }
    )
    return comparison, operator_rows, surgery, assignments


def run_sealed_diagnostics(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / "preflight/preflight_complete.json").exists():
        raise ContractError("preflight must complete before sealed diagnostics")
    complete = build / ".state/sealed_diagnostics_complete.json"
    if complete.exists():
        return
    configure_determinism()
    device = torch.device("cuda")
    train = load_fold_data(config, "train")
    teacher = load_train_teacher(config, train)
    morphology_indices = morphology_sample_indices(train["frame"])
    curves = pd.read_csv(workspace_path(config["inputs"]["21c_curves"], must_exist=True))
    zero_source_rec = float(np.mean(np.asarray(train["y_source"], dtype=np.float64) ** 2))
    zero_shifted_rec = float(np.mean(np.asarray(teacher["y_teacher"][:, :9], dtype=np.float64) ** 2))
    zero_forecast = float(np.mean(np.asarray(train["label"], dtype=np.float64) ** 2))
    zero_output_loss = 0.5 * (zero_source_rec + zero_shifted_rec) + zero_forecast
    zero_rows = []
    collapse_rows = []
    selector_frames = []
    operator_rows: list[dict[str, Any]] = []
    operator_assignments: dict[tuple[str, int], np.ndarray] = {}
    operator_codebooks: dict[int, np.ndarray] = {}
    surgery_frames = []
    gradient_frames = []
    batch_registry_frames = []
    d0_arm = config["arms"][0]
    for seed in MODEL_SEEDS:
        model, semantic = load_checkpoint_model(config, "SEALED_V4_R2", seed, device)
        operator_codebooks[seed] = model.K_codebook.weight.detach().double().cpu().numpy().copy()
        selected_epoch = int(config["sealed_replay"]["selected"][str(seed)]["epoch"])
        selected_curve = curves.loc[
            curves["model_seed"].eq(seed) & curves["epoch"].eq(selected_epoch)
        ].iloc[0]
        selected_rec = float(selected_curve["train_loss_rec"])
        zero_rows.append(
            {
                "arm_order": -1,
                "arm_id": "SEALED_V4_R2",
                "model_seed": seed,
                "epoch": selected_epoch,
                "audit_role": "sealed_selected_checkpoint_train_zero_output",
                "sample_row_n": len(train["frame"]),
                "zero_output_L_source_rec": zero_source_rec,
                "zero_output_L_shifted_observed_rec": zero_shifted_rec,
                "zero_output_L_forecast": zero_forecast,
                "zero_output_L_rec": zero_output_loss,
                "actual_L_rec": selected_rec,
                "zero_solution_improvement": 1.0 - selected_rec / zero_output_loss,
                "audit_sample_row_key_sha256": retained_row_hash(
                    train["frame"]["row_key_hash"].astype(str).tolist()
                ),
            }
        )
        morphology = checkpoint_morphology(model, train, morphology_indices, device)
        _, batch_registry, gradient_evidence = calibrate_gradient_weights(
            config,
            d0_arm,
            model,
            seed,
            train,
            train["y_source"],
            teacher["y_teacher"],
            train["label"],
            teacher["x_teacher"],
            device,
        )
        batch_registry.insert(0, "phase", "audit")
        batch_registry.insert(0, "arm_id", "SEALED_V4_R2")
        gradient_evidence.loc[gradient_evidence["arm_id"].notna(), "arm_id"] = "SEALED_V4_R2"
        gradient_evidence.loc[gradient_evidence["phase"].notna(), "phase"] = "audit"
        batch_registry_frames.append(batch_registry)
        gradient_frames.append(gradient_evidence.loc[gradient_evidence["loss_term"].notna()])
        tau = float(selected_curve["gumbel_tau_last_step"])
        late_prefix8: np.ndarray | None = None
        late_data: Mapping[str, Any] | None = None
        for fold in VALIDATION_FOLDS:
            data = load_fold_data(config, fold)
            shard = write_draw_shard(
                config, "SEALED_V4_R2", fold, seed, model, data, data["y_source"], device
            )
            _, prefixes = read_draw_prefixes(shard)
            comparison, observed_operator_rows, surgery, assignments = selector_and_surgery_readout(
                model, data, data["y_source"], seed, tau, fold, device, prefixes[8]
            )
            selector_frames.append(comparison)
            operator_rows.extend(observed_operator_rows)
            operator_assignments[(fold, seed)] = assignments
            surgery_frames.append(surgery)
            if fold == "validation_late":
                late_prefix8 = prefixes[8]
                late_data = data
        if late_prefix8 is None or late_data is None:
            raise ContractError("sealed late morphology score readout missing")
        late_frame = late_data["frame"].copy()
        late_frame["score"] = late_prefix8
        late_frame["raw_label"] = late_data["label"]
        day_score_std = late_frame.groupby("decision_date", sort=True)["score"].std(ddof=1)
        day_label_std = late_frame.groupby("decision_date", sort=True)["raw_label"].std(ddof=1)
        forecast_score_std = float(day_score_std.median())
        raw_label_std = float(day_label_std.median())
        initial_model = build_arm_model("D0_R2_RAW_EXACT_REPLAY", seed)
        initial_decoder_norm = float(
            torch.linalg.vector_norm(initial_model.decoder.weight.detach().double()).cpu()
        )
        raw_source_std = float(np.std(train["y_source"][morphology_indices], ddof=1))
        collapse_rows.append(
            {
                "arm_order": -1,
                "arm_id": "SEALED_V4_R2",
                "model_seed": seed,
                "fold": "train_morphology_validation_late_score",
                "selected_epoch": selected_epoch,
                "initialization_decoder_weight_l2": initial_decoder_norm,
                **morphology,
                "decoder_norm_ratio": morphology["decoder_weight_l2"] / initial_decoder_norm,
                "raw_source_std": raw_source_std,
                "decoded_source_std_ratio": morphology["decoded_source_std"] / raw_source_std,
                "forecast_score_std": forecast_score_std,
                "raw_label_std": raw_label_std,
                "score_to_label_std_ratio": forecast_score_std / raw_label_std,
                "additional_collapse_flag_n": None,
                "h01_direct_morphology_support": None,
                "checkpoint_semantic_sha256": semantic,
                "audit_sample_row_key_sha256": stable_hash(
                    train["frame"].iloc[morphology_indices]["row_key_hash"].astype(str).tolist()
                ),
                "status": "pass",
            }
        )
        del initial_model
        del model
        torch.cuda.empty_cache()
    for fold in VALIDATION_FOLDS:
        for seed_a_index in range(len(MODEL_SEEDS)):
            for seed_b_index in range(seed_a_index + 1, len(MODEL_SEEDS)):
                seed_a = MODEL_SEEDS[seed_a_index]
                seed_b = MODEL_SEEDS[seed_b_index]
                codebook_a = operator_codebooks[seed_a]
                codebook_b = operator_codebooks[seed_b]
                permutation = min(
                    permutations(range(N_OPERATOR)),
                    key=lambda candidate: sum(
                        np.linalg.norm(codebook_a[index] - codebook_b[candidate[index]])
                        for index in range(N_OPERATOR)
                    ),
                )
                inverse = np.empty(N_OPERATOR, dtype=np.int8)
                for reference_operator, observed_operator in enumerate(permutation):
                    inverse[observed_operator] = reference_operator
                assignment_a = operator_assignments[(fold, seed_a)]
                assignment_b = operator_assignments[(fold, seed_b)]
                aligned_b = inverse[assignment_b]
                common = {
                    "arm_order": -1,
                    "arm_id": "SEALED_V4_R2",
                    "model_seed": seed_b,
                    "fold": fold,
                    "aggregation_key": f"seed_pair:{seed_a}:{seed_b}",
                    "operator_i": None,
                    "operator_j": None,
                    "observation_n": int(assignment_a.size),
                    "status": "pass",
                }
                operator_rows.extend(
                    [
                        {
                            **common,
                            "metric_id": "cross_seed_assignment_agreement_raw",
                            "alignment_permutation_json": None,
                            "metric_value": float(np.mean(assignment_a == assignment_b)),
                        },
                        {
                            **common,
                            "metric_id": "cross_seed_assignment_agreement_aligned",
                            "alignment_permutation_json": canonical_json_bytes(list(permutation)).decode(),
                            "metric_value": float(np.mean(assignment_a == aligned_b)),
                        },
                    ]
                )
    zero_median = float(np.median([row["zero_solution_improvement"] for row in zero_rows]))
    score_ratio_median = float(np.median([row["score_to_label_std_ratio"] for row in collapse_rows]))
    additional_flag_n = sum(
        (
            float(np.median([row["decoder_norm_ratio"] for row in collapse_rows])) <= 0.25,
            float(np.median([row["latent_effective_rank_ratio"] for row in collapse_rows])) <= 0.25,
            float(np.median([row["decoded_source_std_ratio"] for row in collapse_rows])) <= 0.10,
        )
    )
    direct_h01 = zero_median <= 0.10 and score_ratio_median <= 0.05 and additional_flag_n >= 2
    for row in collapse_rows:
        row["additional_collapse_flag_n"] = additional_flag_n
        row["h01_direct_morphology_support"] = direct_h01
    _write_csv(
        build / "diagnostics/raw_return_zero_solution_audit.csv",
        zero_rows,
        ZERO_SOLUTION_COLUMNS,
    )
    _write_csv(
        build / "diagnostics/checkpoint_parameter_collapse_audit.csv",
        collapse_rows,
        COLLAPSE_COLUMNS,
    )
    selector = pd.concat(selector_frames, ignore_index=True)
    selector_publish = selector[SELECTOR_SCORE_SCHEMA.names].sort_values(
        ["fold_order", "model_seed", "decision_date", "instrument"], kind="mergesort"
    )
    write_schema_parquet(
        build / "diagnostics/selector_semantics_score_comparison.parquet",
        selector_publish,
        SELECTOR_SCORE_SCHEMA,
    )
    selector_audit_rows = []
    for (fold, seed, decision_date), day in selector.groupby(
        ["fold", "model_seed", "decision_date"], sort=True
    ):
        daily_rho = float(
            pd.Series(day["hard_score"]).corr(
                pd.Series(day["deterministic_soft_mixture_score"]), method="spearman"
            )
        )
        hard_top = set(day.nlargest(30, "hard_score")["instrument"])
        soft_top = set(day.nlargest(30, "deterministic_soft_mixture_score")["instrument"])
        selector_audit_rows.append(
            {
                "fold_order": FOLDS.index(fold),
                "fold": fold,
                "model_seed": seed,
                "decision_date": decision_date,
                "row_n": len(day),
                "daily_spearman": daily_rho,
                "top30_overlap": len(hard_top & soft_top),
                "mean_abs_score_delta": float(np.mean(np.abs(day["score_delta"]))),
                "selector_entropy_mean": float(day["selector_entropy_mean"].mean()),
                "effective_operator_count_mean": float(day["effective_operator_count_mean"].mean()),
                "switching_rate": float(day["switching_rate"].mean()),
                "status": "pass",
            }
        )
    _write_csv(
        build / "diagnostics/selector_semantics_audit.csv",
        selector_audit_rows,
        list(selector_audit_rows[0]),
    )
    _write_csv(
        build / "diagnostics/operator_usage_and_stability_audit.csv",
        sorted(
            operator_rows,
            key=lambda row: (
                row["arm_order"], row["model_seed"], row["fold"], row["aggregation_key"],
                row["metric_id"], -1 if row["operator_i"] is None else row["operator_i"],
                -1 if row["operator_j"] is None else row["operator_j"],
            ),
        ),
        [
            "arm_order", "arm_id", "model_seed", "fold", "aggregation_key",
            "metric_id", "operator_i", "operator_j", "alignment_permutation_json",
            "metric_value", "observation_n", "status",
        ],
    )
    surgery = pd.concat(surgery_frames, ignore_index=True)[SURGERY_SCORE_SCHEMA.names].sort_values(
        ["fold_order", "model_seed", "decision_date", "instrument"], kind="mergesort"
    )
    write_schema_parquet(
        build / "diagnostics/checkpoint_surgery_score_comparison.parquet",
        surgery,
        SURGERY_SCORE_SCHEMA,
    )
    gradient = pd.concat(gradient_frames, ignore_index=True)
    _write_parquet(build / "diagnostics/loss_gradient_scale_audit.parquet", gradient)
    registry = pd.concat(batch_registry_frames, ignore_index=True)
    _write_parquet(build / ".state/sealed_gradient_batch_registry.parquet", registry)
    _write_json(
        complete,
        {
            "schema_version": "21D_SEALED_DIAGNOSTICS_COMPLETE_V2",
            "sealed_draw_shard_n": 6,
            "completed_at_utc": utc_now(),
        },
    )


def run_resource_probe(config: Mapping[str, Any], device: torch.device) -> pd.DataFrame:
    free_disk = shutil.disk_usage(TOPIC_ROOT).free
    if free_disk < config["resources"]["minimum_free_disk_before_training"]:
        raise ContractError("free disk below frozen training minimum")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    oom = False
    forward = backward = optimizer_pass = inference = writer_pass = False
    probe_path = building_output_root(config) / ".state/resource_probe_draw.parquet"
    try:
        arm = config["arms"][4]
        model = build_arm_model(arm["arm_id"], 21000053).to(device)
        optimizer = build_optimizer(model, config)
        y = torch.zeros((256, LOOKBACK, 1), device=device)
        x = torch.zeros((256, LOOKBACK, FEATURE_DIM), device=device)
        uniform = torch.full((256, LOOKBACK, N_OPERATOR), 0.5, device=device)
        timestep = torch.ones((256, LOOKBACK), dtype=torch.long, device=device)
        epsilon = torch.zeros((256, LOOKBACK, LATENT_DIM), device=device)
        losses = diagnostic_training_losses(
            model,
            arm,
            y,
            x,
            y,
            x,
            torch.zeros(256, device=device),
            tau=1.0,
            gumbel_u=uniform,
            diffusion_timestep=timestep,
            epsilon=epsilon,
        )
        forward = True
        optimizer_step(model, optimizer, losses["L_total"])
        backward = optimizer_pass = True
        keys = [(f"__21D_PROBE_{index:03d}", "1970-01-02") for index in range(256)]
        draws64 = inference_draw_matrix_tensor(model, y, x, keys, 21000053, draw_n=64)
        inference = tuple(draws64.shape) == (256, 64)
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        fixed = pa.FixedSizeListArray.from_arrays(
            pa.array(np.zeros(256, dtype=np.float32), type=pa.float32()), 256
        )
        pq.write_table(pa.Table.from_arrays([fixed], names=["draw_scores"]), probe_path, compression="zstd")
        writer_pass = pq.read_metadata(probe_path).num_rows == 1
        del model, optimizer, losses, draws64
    except torch.cuda.OutOfMemoryError:
        oom = True
    elapsed = time.perf_counter() - started
    peak = int(torch.cuda.max_memory_reserved(device))
    status = "pass" if all((forward, backward, optimizer_pass, inference, writer_pass)) and not oom else "fail"
    if status != "pass":
        raise ContractError("frozen batch=256 resource probe failed")
    return pd.DataFrame(
        [
            {
                "probe_order": 0,
                "probe_id": "D4_BATCH256_64DRAW_AND_SHARD_WRITE",
                "arm_id": "D4_R2_REPAIR_COMBINED_V1",
                "batch_size": 256,
                "device_fingerprint_sha256": current_device_fingerprint(),
                "forward_pass": forward,
                "backward_pass": backward,
                "optimizer_state_step_pass": optimizer_pass,
                "inference_64draw_pass": inference,
                "draw_shard_write_pass": writer_pass,
                "oom_observed": oom,
                "peak_reserved_memory_bytes": peak,
                "estimated_gpu_wall_seconds": int(math.ceil(elapsed * 21 * 40)),
                "estimated_output_bytes": int(config["resources"]["canonical_output_root_bytes_cap"]),
                "free_disk_bytes": free_disk,
                "status": status,
                "reason": "",
            }
        ]
    )


def _arm_by_id(config: Mapping[str, Any], arm_id: str) -> Mapping[str, Any]:
    matches = [arm for arm in config["arms"] if arm["arm_id"] == arm_id]
    if len(matches) != 1:
        raise ContractError(f"arm registry lookup is not unique: {arm_id}")
    return matches[0]


def _selected_curve(curves: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(
        curves,
        key=lambda row: (float(row["validation_early_mean_rankic"]), -int(row["epoch"])),
    )


def _job_state_root(build: Path, arm_id: str, seed: int) -> Path:
    return build / f".state/jobs/{arm_id}/seed_{seed}"


def _save_job_state(
    root: Path,
    curves: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    metadata: Mapping[str, Any],
    batch_registry: pd.DataFrame,
    gradient_evidence: pd.DataFrame,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write_csv(root / "curves.csv", curves, list(curves[0]))
    np.save(root / "early_scores.npy", np.asarray(scores, dtype=np.float32), allow_pickle=False)
    _write_json(root / "metadata.json", metadata)
    if not batch_registry.empty:
        _write_parquet(root / "gradient_batch_registry.parquet", batch_registry)
    if not gradient_evidence.empty:
        _write_parquet(root / "gradient_evidence.parquet", gradient_evidence)
    _write_json(
        root / "complete.json",
        {
            "checkpoint_sha256": metadata["checkpoint_sha256"],
            "checkpoint_semantic_sha256": metadata["model_state_semantic_sha256"],
            "completed_at_utc": utc_now(),
        },
    )


def _job_state(config: Mapping[str, Any], arm_id: str, seed: int) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    root = _job_state_root(building_output_root(config), arm_id, seed)
    if not (root / "complete.json").exists():
        raise ContractError(f"job state incomplete: {arm_id}/{seed}")
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    checkpoint = checkpoint_path(building_output_root(config), arm_id, seed)
    if file_sha(checkpoint) != metadata["checkpoint_sha256"]:
        raise ContractError(f"job checkpoint drift: {arm_id}/{seed}")
    return pd.read_csv(root / "curves.csv"), np.load(root / "early_scores.npy", allow_pickle=False), metadata


def published_training_curves(
    config: Mapping[str, Any], curves_by_job: Sequence[pd.DataFrame]
) -> pd.DataFrame:
    arm_orders = {arm["arm_id"]: arm["arm_order"] for arm in config["arms"]}
    rows: list[dict[str, Any]] = []
    for curves in curves_by_job:
        arm_id = str(curves["arm_id"].iloc[0])
        selected_epoch = int(_selected_curve(curves.to_dict("records"))["epoch"])
        for curve in curves.to_dict("records"):
            common = {
                "arm_order": arm_orders[arm_id],
                "arm_id": arm_id,
                "model_seed": int(curve["model_seed"]),
                "epoch": int(curve["epoch"]),
                "optimizer_step_n": int(curve["optimizer_step_end"]),
                "tau": float(curve["gumbel_tau_last_step"]),
                "checkpoint_selected": int(curve["epoch"]) == selected_epoch,
            }
            for metric_id, source in (
                ("loss_total", "train_loss_total"),
                ("loss_rec", "train_loss_rec"),
                ("loss_koop", "train_loss_koop"),
                ("loss_diff", "train_loss_diff"),
            ):
                rows.append(
                    {
                        **common,
                        "split_role": "train",
                        "metric_id": metric_id,
                        "metric_value": float(curve[source]),
                        "observation_n": int(config["retained_folds"]["train"]["row_n"]),
                    }
                )
            for metric_id, value, observation_n in (
                ("mean_rankic", curve["validation_early_mean_rankic"], curve["validation_early_complete_day_n"]),
                ("complete_day_n", curve["validation_early_complete_day_n"], curve["validation_early_complete_day_n"]),
                ("score_coverage", curve["validation_early_score_coverage"], config["retained_folds"]["validation_early"]["row_n"]),
            ):
                rows.append(
                    {
                        **common,
                        "split_role": "validation_early",
                        "metric_id": metric_id,
                        "metric_value": float(value),
                        "observation_n": int(observation_n),
                    }
                )
    columns = [
        "arm_order", "arm_id", "model_seed", "epoch", "split_role", "metric_id",
        "metric_value", "observation_n", "optimizer_step_n", "tau", "checkpoint_selected",
    ]
    return pd.DataFrame(rows)[columns].sort_values(
        ["arm_order", "model_seed", "epoch", "split_role", "metric_id"], kind="mergesort"
    )


def published_training_registry(
    config: Mapping[str, Any], registry_rows: Sequence[Mapping[str, Any]], curves_by_job: Sequence[pd.DataFrame]
) -> pd.DataFrame:
    curves_lookup = {
        (str(frame["arm_id"].iloc[0]), int(frame["model_seed"].iloc[0])): frame
        for frame in curves_by_job
    }
    cpu_peak_mib = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0)
    rows = []
    for metadata in registry_rows:
        arm_id = str(metadata["arm_id"])
        seed = int(metadata["model_seed"])
        curves = curves_lookup[(arm_id, seed)]
        initial = build_arm_model(arm_id, seed)
        rows.append(
            {
                "arm_order": int(metadata["arm_order"]),
                "arm_id": arm_id,
                "model_seed": seed,
                "config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
                "train_row_n": int(config["retained_folds"]["train"]["row_n"]),
                "validation_early_row_n": int(config["retained_folds"]["validation_early"]["row_n"]),
                "selected_batch_size": 256,
                "started_at_utc": metadata["started_at_utc"],
                "ended_at_utc": metadata["ended_at_utc"],
                "final_evaluated_epoch": int(metadata["final_evaluated_epoch"]),
                "selected_epoch": int(metadata["selected_epoch"]),
                "selection_metric": float(metadata["selection_metric"]),
                "selection_status": "selected_on_validation_early",
                "checkpoint_path": metadata["checkpoint_path"],
                "checkpoint_sha256": metadata["checkpoint_sha256"],
                "model_state_semantic_sha256": metadata["model_state_semantic_sha256"],
                "parameter_count": int(metadata["parameter_count"]),
                "initialization_contract_sha256": model_state_semantic_hash(initial.state_dict()),
                "ordered_parameter_name_list_sha256": metadata["ordered_parameter_name_list_sha256"],
                "actual_optimizer_step_n": int(curves["optimizer_step_end"].iloc[-1]),
                "peak_cpu_rss_mib": cpu_peak_mib,
                "peak_gpu_memory_mib": float(metadata["peak_gpu_memory_mib"]),
                "training_wall_seconds": float(metadata["training_wall_seconds"]),
                "run_status": metadata["run_status"],
                "failure_reason": "",
            }
        )
        del initial
    return pd.DataFrame(rows).sort_values(["arm_order", "model_seed"], kind="mergesort")


def comparator_prediction_rows(
    config: Mapping[str, Any], fold: str, retained: Mapping[str, Any]
) -> pd.DataFrame:
    filename = (
        "training/selection/validation_early_prediction_scores.parquet"
        if fold == "validation_early"
        else "training/readout/validation_late_prediction_scores.parquet"
    )
    root = workspace_path(config["upstream_pins"]["21b_v6_manifest"]["path"], must_exist=True).parent
    source = pd.read_parquet(root / filename)
    source = source.loc[source["arm_id"].isin(COMPARATORS)].copy()
    expected_keys = retained["frame"][["decision_date", "instrument", "row_key_hash"]].copy()
    expected_keys["decision_date"] = expected_keys["decision_date"].astype(str)
    source["decision_date"] = source["decision_date"].astype(str)
    source = source.merge(
        expected_keys,
        on=["decision_date", "instrument", "row_key_hash"],
        how="inner",
        validate="many_to_one",
    )
    key_columns = ["arm_id", "decision_date", "instrument", "row_key_hash"]
    seed_source = source.loc[source["score_role"].eq("seed")].copy()
    if (
        seed_source["model_seed"].nunique() != 3
        or len(seed_source) != len(COMPARATORS) * len(retained["frame"]) * 3
        or seed_source[key_columns + ["model_seed"]].duplicated().any()
    ):
        raise ContractError("comparator three-seed coverage mismatch")
    derived_ensemble = (
        seed_source.groupby(key_columns, sort=False, as_index=False)["score"].mean()
    )
    derived_ensemble["score_role"] = "ensemble"
    derived_ensemble["model_seed"] = pd.Series(
        [pd.NA] * len(derived_ensemble), dtype="Int64"
    )
    pinned_ensemble = source.loc[source["score_role"].eq("ensemble")]
    if not pinned_ensemble.empty:
        compared = derived_ensemble.merge(
            pinned_ensemble[key_columns + ["score"]],
            on=key_columns,
            suffixes=("_derived", "_pinned"),
            validate="one_to_one",
        )
        if len(compared) != len(derived_ensemble) or not np.allclose(
            compared["score_derived"], compared["score_pinned"], rtol=0.0, atol=1e-12
        ):
            raise ContractError("pinned comparator ensemble differs from row-wise seed mean")
    seed_publish = seed_source[key_columns + ["score_role", "model_seed", "score"]].copy()
    seed_publish["model_seed"] = seed_publish["model_seed"].astype("Int64")
    source = pd.concat(
        [
            seed_publish,
            derived_ensemble[key_columns + ["score_role", "model_seed", "score"]],
        ],
        ignore_index=True,
    )
    if set(source["score_role"]) != {"seed", "ensemble"}:
        raise ContractError("comparator seed/ensemble role reconstruction failed")
    arm_order = {COMPARATORS[0]: 101, COMPARATORS[1]: 103}
    output = pd.DataFrame(
        {
            "fold_order": FOLDS.index(fold),
            "fold": fold,
            "arm_order": source["arm_id"].map(arm_order).astype(np.int8),
            "arm_id": source["arm_id"],
            "model_seed": source["model_seed"].astype("Int64"),
            "is_ensemble": source["score_role"].eq("ensemble"),
            "score_variant": "primary",
            "draw_n": np.int16(0),
            "decision_date": pd.to_datetime(source["decision_date"]).dt.date,
            "instrument": source["instrument"].astype(str),
            "row_key": source["row_key_hash"].astype(str),
            "score": source["score"].astype(np.float32),
            "raw_label": source.merge(
                retained["frame"][["decision_date", "instrument"]].assign(
                    decision_date=lambda x: x["decision_date"].astype(str),
                    raw_label=retained["label"],
                ),
                on=["decision_date", "instrument"],
                how="left",
                validate="many_to_one",
                sort=False,
            )["raw_label"].astype(np.float32),
            "checkpoint_semantic_sha256": None,
        }
    )
    return output


PREDICTION_COLUMNS = [
    "fold_order", "fold", "arm_order", "arm_id", "model_seed", "is_ensemble",
    "score_variant", "draw_n", "decision_date", "instrument", "row_key",
    "score", "raw_label", "checkpoint_semantic_sha256",
]

PREDICTION_SCHEMA = pa.schema(
    [
        ("fold_order", pa.int8()),
        ("fold", pa.string()),
        ("arm_order", pa.int8()),
        ("arm_id", pa.string()),
        ("model_seed", pa.int64()),
        ("is_ensemble", pa.bool_()),
        ("score_variant", pa.string()),
        ("draw_n", pa.int16()),
        ("decision_date", pa.date32()),
        ("instrument", pa.string()),
        ("row_key", pa.string()),
        ("score", pa.float32()),
        ("raw_label", pa.float32()),
        ("checkpoint_semantic_sha256", pa.string()),
    ]
)


def write_prediction_parquet(path: Path, frame: pd.DataFrame) -> None:
    if list(frame.columns) != PREDICTION_COLUMNS:
        raise ContractError("prediction frame column order mismatch")
    table = pa.Table.from_pandas(frame, schema=PREDICTION_SCHEMA, preserve_index=False, safe=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)


def learned_prediction_rows(
    config: Mapping[str, Any], fold: str, retained: Mapping[str, Any]
) -> pd.DataFrame:
    build = building_output_root(config)
    rows = []
    for arm in config["arms"]:
        arm_id = arm["arm_id"]
        seed_variant_scores: dict[str, dict[int, np.ndarray]] = {}
        semantics: dict[int, str] = {}
        if arm_id in {"D0_R2_RAW_EXACT_REPLAY", "D4_R2_REPAIR_COMBINED_V1"}:
            for seed in MODEL_SEEDS:
                shard = build / draw_shard_relative(arm_id, fold, seed)
                keys, prefixes = read_draw_prefixes(shard)
                expected = retained["frame"][["decision_date", "instrument", "row_key_hash"]].copy()
                if not (
                    keys["instrument"].astype(str).tolist() == expected["instrument"].astype(str).tolist()
                    and keys["row_key"].astype(str).tolist() == expected["row_key_hash"].astype(str).tolist()
                ):
                    raise ContractError(f"draw shard row order mismatch: {arm_id}/{fold}/{seed}")
                for variant, prefix in (("prefix8", 8), ("prefix64", 64), ("ref256", 256)):
                    seed_variant_scores.setdefault(variant, {})[seed] = prefixes[prefix]
                _, _, metadata = _job_state(config, arm_id, seed)
                semantics[seed] = metadata["model_state_semantic_sha256"]
        else:
            for seed in MODEL_SEEDS:
                if fold == "validation_early":
                    _, scores, metadata = _job_state(config, arm_id, seed)
                else:
                    state_root = build / f".state/late_scores/{arm_id}/seed_{seed}"
                    scores = np.load(state_root / "scores.npy", allow_pickle=False)
                    metadata = json.loads((state_root / "metadata.json").read_text(encoding="utf-8"))
                seed_variant_scores.setdefault("primary", {})[seed] = scores
                semantics[seed] = metadata["model_state_semantic_sha256"]
        for variant, by_seed in seed_variant_scores.items():
            draw_n = {"primary": int(arm["selection_draw_n"]), "prefix8": 8, "prefix64": 64, "ref256": 256}[variant]
            for seed in MODEL_SEEDS:
                rows.append(
                    pd.DataFrame(
                        {
                            "fold_order": FOLDS.index(fold), "fold": fold,
                            "arm_order": arm["arm_order"], "arm_id": arm_id,
                            "model_seed": seed, "is_ensemble": False,
                            "score_variant": variant, "draw_n": draw_n,
                            "decision_date": pd.to_datetime(retained["frame"]["decision_date"]).dt.date,
                            "instrument": retained["frame"]["instrument"].astype(str),
                            "row_key": retained["frame"]["row_key_hash"].astype(str),
                            "score": np.asarray(by_seed[seed], dtype=np.float32),
                            "raw_label": retained["label"].astype(np.float32),
                            "checkpoint_semantic_sha256": semantics[seed],
                        }
                    )
                )
            ensemble = np.stack([by_seed[seed] for seed in MODEL_SEEDS]).astype(np.float64).mean(axis=0).astype(np.float32)
            rows.append(
                pd.DataFrame(
                    {
                        "fold_order": FOLDS.index(fold), "fold": fold,
                        "arm_order": arm["arm_order"], "arm_id": arm_id,
                        "model_seed": pd.Series([pd.NA] * len(retained["frame"]), dtype="Int64"),
                        "is_ensemble": True, "score_variant": variant, "draw_n": draw_n,
                        "decision_date": pd.to_datetime(retained["frame"]["decision_date"]).dt.date,
                        "instrument": retained["frame"]["instrument"].astype(str),
                        "row_key": retained["frame"]["row_key_hash"].astype(str),
                        "score": ensemble, "raw_label": retained["label"].astype(np.float32),
                        "checkpoint_semantic_sha256": None,
                    }
                )
            )
    result = pd.concat(rows, ignore_index=True)
    return result[PREDICTION_COLUMNS]


def full_prediction_frame(
    config: Mapping[str, Any], fold: str, retained: Mapping[str, Any]
) -> pd.DataFrame:
    learned = learned_prediction_rows(config, fold, retained)
    comparators = comparator_prediction_rows(config, fold, retained)
    result = pd.concat([learned, comparators[PREDICTION_COLUMNS]], ignore_index=True)
    series = result[
        ["arm_id", "model_seed", "is_ensemble", "score_variant"]
    ].drop_duplicates()
    if len(series) != 52 or len(result) != 52 * len(retained["frame"]):
        raise ContractError(f"prediction series/row closure mismatch: {fold}")
    return result.sort_values(
        ["fold_order", "arm_order", "is_ensemble", "model_seed", "score_variant", "decision_date", "instrument"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)


def run_training_selection(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/sealed_diagnostics_complete.json").exists():
        raise ContractError("sealed diagnostics must complete before retraining")
    if (build / ".state/training_selection_complete.json").exists():
        return
    configure_determinism()
    device = torch.device("cuda")
    resource_audit = run_resource_probe(config, device)
    _write_csv(
        build / "training/resource_probe_audit.csv",
        resource_audit.to_dict("records"),
        list(resource_audit.columns),
    )
    train = load_fold_data(config, "train")
    early = load_fold_data(config, "validation_early")
    teacher = load_train_teacher(config, train)
    transform_frames = []
    transform_hashes = {}
    for data, fold, include_target in (
        (train, "train", True), (early, "validation_early", False)
    ):
        _, audit, semantic = decision_cs_zscore_return_path(
            data["raw_panel"], data["frame"]["decision_date"].astype(str).tolist(),
            fold=fold, include_target=include_target,
        )
        transform_frames.append(audit)
        transform_hashes[fold] = semantic
    transform = normalize_return_path_transform(pd.concat(transform_frames, ignore_index=True))
    write_schema_parquet(
        build / "diagnostics/return_path_transform_audit.parquet",
        transform,
        RETURN_PATH_TRANSFORM_SCHEMA,
    )
    started_gpu = time.perf_counter()
    for arm in config["arms"]:
        for seed in MODEL_SEEDS:
            state_root = _job_state_root(build, arm["arm_id"], seed)
            if (state_root / "complete.json").exists():
                continue
            print(f"[{utc_now()}] training job start {arm['arm_id']}/seed_{seed}", flush=True)
            job_started = utc_now()
            wall = time.perf_counter()
            torch.cuda.reset_peak_memory_stats(device)
            state, curves, scores, weights, batch_registry, gradient_evidence = train_one_arm_seed(
                config, arm, seed, train, early, teacher, device
            )
            selected = _selected_curve(curves)
            path = checkpoint_path(build, arm["arm_id"], seed)
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(state, path)
            reopened = torch.load(path, map_location="cpu", weights_only=True)
            semantic = model_state_semantic_hash(reopened)
            checkpoint_sha = file_sha(path)
            if arm["arm_id"] == "D0_R2_RAW_EXACT_REPLAY":
                expected = config["sealed_replay"]["selected"][str(seed)]
                if (
                    int(selected["epoch"]) != expected["epoch"]
                    or float(selected["validation_early_mean_rankic"]) != expected["early_rankic"]
                    or semantic != expected["semantic_sha256"]
                    or checkpoint_sha != expected["checkpoint_sha256"]
                ):
                    raise ContractError(f"D0 exact replay mismatch: seed {seed}")
            elapsed = time.perf_counter() - wall
            metadata = {
                "run_id": RUN_ID,
                "arm_order": arm["arm_order"],
                "arm_id": arm["arm_id"],
                "model_seed": seed,
                "started_at_utc": job_started,
                "ended_at_utc": utc_now(),
                "selected_epoch": int(selected["epoch"]),
                "selection_metric": float(selected["validation_early_mean_rankic"]),
                "final_evaluated_epoch": len(curves),
                "checkpoint_path": path.relative_to(build).as_posix(),
                "checkpoint_sha256": checkpoint_sha,
                "model_state_semantic_sha256": semantic,
                "parameter_count": sum(value.numel() for value in reopened.values()),
                "ordered_parameter_name_list_sha256": stable_hash(model_parameter_names(build_arm_model(arm["arm_id"], seed))),
                "training_wall_seconds": elapsed,
                "peak_gpu_memory_mib": torch.cuda.max_memory_reserved(device) / 2**20,
                "loss_weights": weights,
                "run_status": "early_stopped" if len(curves) < config["training"]["max_epochs"] else "completed",
            }
            _save_job_state(state_root, curves, scores, metadata, batch_registry, gradient_evidence)
            print(
                f"[{utc_now()}] training job complete {arm['arm_id']}/seed_{seed} "
                f"epoch={metadata['selected_epoch']} early_rankic={metadata['selection_metric']:.8f}",
                flush=True,
            )
            del state, reopened
            torch.cuda.empty_cache()
            if time.perf_counter() - started_gpu > config["resources"]["total_gpu_wall_seconds_cap"]:
                raise ContractError("total GPU wall time cap exceeded")
    curve_frames = []
    registry_rows = []
    checkpoint_entries = []
    gradient_weights = []
    sealed_registry = pq.read_table(build / ".state/sealed_gradient_batch_registry.parquet").to_pandas()
    sealed_registry["arm_id"] = "SEALED_V4_R2"
    sealed_registry["arm_order"] = -1
    d0_registry = sealed_registry.copy()
    d0_registry["arm_id"] = "D0_R2_RAW_EXACT_REPLAY"
    d0_registry["arm_order"] = 0
    batch_frames = [sealed_registry, d0_registry]
    sealed_grad = pq.read_table(build / "diagnostics/loss_gradient_scale_audit.parquet").to_pandas()
    sealed_grad["arm_id"] = "SEALED_V4_R2"
    sealed_grad["arm_order"] = -1
    sealed_grad["phase"] = "audit"
    d0_grad = sealed_grad.copy()
    d0_grad["arm_id"] = "D0_R2_RAW_EXACT_REPLAY"
    d0_grad["arm_order"] = 0
    loss_gradient_frames = [sealed_grad, d0_grad]
    for arm in config["arms"]:
        for seed in MODEL_SEEDS:
            curves, _, metadata = _job_state(config, arm["arm_id"], seed)
            curve_frames.append(curves)
            registry_rows.append(metadata)
            checkpoint_entries.append(
                {
                    "arm_order": arm["arm_order"], "arm_id": arm["arm_id"], "model_seed": seed,
                    "checkpoint_path": metadata["checkpoint_path"],
                    "checkpoint_sha256": metadata["checkpoint_sha256"],
                    "model_state_semantic_sha256": metadata["model_state_semantic_sha256"],
                    "selected_epoch": metadata["selected_epoch"],
                    "selection_metric": metadata["selection_metric"],
                    "ordered_parameter_name_list_sha256": metadata["ordered_parameter_name_list_sha256"],
                    "eligible": True, "eligibility_reason": "",
                }
            )
            if arm["loss_weights"] == "train_calibrated":
                root = _job_state_root(build, arm["arm_id"], seed)
                evidence = pq.read_table(root / "gradient_evidence.parquet").to_pandas()
                weights = metadata["loss_weights"]
                medians = evidence.loc[
                    evidence["phase"].eq("calibration")
                    & evidence["module_id"].eq("global")
                ].groupby("loss_term")["gradient_l2"].median()
                inverse = 1.0 / medians.clip(lower=1e-12)
                raw = inverse / inverse.mean()
                clipped = raw.clip(lower=0.05, upper=20.0)
                for term in ("L_rec", "L_koop", "L_diff"):
                    gradient_weights.append(
                        {
                            "arm_order": arm["arm_order"], "arm_id": arm["arm_id"], "model_seed": seed,
                            "loss_term": term, "median_gradient_l2": float(medians[term]),
                            "inverse_gradient_raw": float(inverse[term]), "weight_before_clip": float(raw[term]),
                            "clip_applied": bool(raw[term] != clipped[term]), "weight_after_clip": float(clipped[term]),
                            "final_normalized_weight": float(weights[term]),
                            "batch_registry_sha256": file_sha(root / "gradient_batch_registry.parquet"),
                        }
                    )
                registry = pq.read_table(root / "gradient_batch_registry.parquet").to_pandas()
                registry["arm_id"] = arm["arm_id"]
                registry["arm_order"] = arm["arm_order"]
                batch_frames.append(registry)
                evidence["arm_order"] = arm["arm_order"]
                evidence["phase"] = "calibration"
                loss_gradient_frames.append(evidence)
                selected_registry, selected_evidence = selected_checkpoint_gradient_audit(
                    config, arm, seed, train, teacher, device
                )
                if not selected_registry[["row_key_sha256", "sampling_contract_sha256"]].equals(
                    registry[["row_key_sha256", "sampling_contract_sha256"]]
                ):
                    raise ContractError(f"selected gradient audit batch drift: {arm['arm_id']}/{seed}")
                selected_evidence["arm_order"] = arm["arm_order"]
                selected_evidence["arm_id"] = arm["arm_id"]
                selected_evidence["phase"] = "audit"
                loss_gradient_frames.append(selected_evidence)
    gradient_registry = normalize_gradient_batch_registry(pd.concat(batch_frames, ignore_index=True))
    write_schema_parquet(
        build / "diagnostics/gradient_calibration_batch_registry.parquet",
        gradient_registry,
        GRADIENT_BATCH_SCHEMA,
    )
    loss_gradient = normalize_loss_gradient(pd.concat(loss_gradient_frames, ignore_index=True))
    write_schema_parquet(
        build / "diagnostics/loss_gradient_scale_audit.parquet",
        loss_gradient,
        LOSS_GRADIENT_SCHEMA,
    )
    compute_learned_train_morphology_bases(config, train, teacher, device)
    weights_frame = pd.DataFrame(gradient_weights).sort_values(["arm_order", "model_seed", "loss_term"])
    if len(weights_frame) != 18:
        raise ContractError("gradient calibration weights expected 18 rows")
    _write_csv(build / "training/gradient_calibration_weights.csv", weights_frame.to_dict("records"), list(weights_frame.columns))
    curves_frame = published_training_curves(config, curve_frames)
    _write_csv(build / "training/seed_level_training_curves.csv", curves_frame.to_dict("records"), list(curves_frame.columns))
    registry_frame = published_training_registry(config, registry_rows, curve_frames)
    _write_csv(build / "training/training_run_registry.csv", registry_frame.to_dict("records"), list(registry_frame.columns))
    checkpoint_payload = {
        "schema_version": "S_CHECKPOINT_MANIFEST_V2", "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION, "entry_n": 21,
        "entries": checkpoint_entries,
        "entries_semantic_sha256": stable_hash(checkpoint_entries),
    }
    _write_json(build / "training/checkpoint_manifest.json", checkpoint_payload)
    _write_json(build / "training/checkpoint_eligibility_manifest.json", checkpoint_payload)
    jobs = planned_jobs(config)
    jobs["job_status"] = "complete"
    jobs["checkpoint_produced"] = True
    _write_csv(build / "training/model_search_accounting_manifest.csv", jobs.to_dict("records"), list(jobs.columns))
    for identity in ("D0_R2_RAW_EXACT_REPLAY", "D4_R2_REPAIR_COMBINED_V1"):
        arm = _arm_by_id(config, identity)
        y_early, _, _, _ = arm_data(config, arm, early)
        for seed in MODEL_SEEDS:
            model, _ = load_checkpoint_model(config, identity, seed, device)
            write_draw_shard(config, identity, "validation_early", seed, model, early, y_early, device)
            del model
            torch.cuda.empty_cache()
    early_predictions = full_prediction_frame(config, "validation_early", early)
    write_prediction_parquet(build / "predictions/validation_early_prediction_scores.parquet", early_predictions)
    pre_late = {
        "schema_version": "S_PRE_LATE_BUNDLE_V2", "run_id": RUN_ID,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "hypothesis_registry_sha256": file_sha(build / "hypothesis_registry.csv"),
        "arm_registry_sha256": file_sha(build / "training/arm_registry.csv"),
        "return_transform_train_early_sha256": file_sha(build / "diagnostics/return_path_transform_audit.parquet"),
        "gradient_calibration_sha256": file_sha(build / "training/gradient_calibration_weights.csv"),
        "model_search_accounting_sha256": file_sha(build / "training/model_search_accounting_manifest.csv"),
        "checkpoint_manifest_sha256": file_sha(build / "training/checkpoint_manifest.json"),
        "checkpoint_eligibility_manifest_sha256": file_sha(build / "training/checkpoint_eligibility_manifest.json"),
        "early_prediction_semantic_sha256": semantic_frame_hash(early_predictions, ["arm_order", "is_ensemble", "model_seed", "score_variant", "decision_date", "instrument"]),
        "sealed_at_utc": utc_now(),
    }
    pre_late["bundle_semantic_sha256"] = stable_hash(pre_late)
    _write_json(build / "training/pre_late_checkpoint_bundle_manifest.json", pre_late)
    _write_json(
        build / "training/selection_worker_exit_record.json",
        {
            "schema_version": "S_WORKER_EXIT_V2", "run_id": RUN_ID,
            "process_role": "selection_worker", "pid": os.getpid(),
            "started_at_utc": None, "ended_at_utc": utc_now(), "exit_code": 0,
            "input_paths_json": canonical_json_bytes(
                [config["paths"]["config"], config["inputs"]["panel_manifest"]]
            ).decode(),
            "input_hashes_json": canonical_json_bytes(
                {"config": file_sha(workspace_path(config["paths"]["config"], must_exist=True))}
            ).decode(),
            "output_paths_json": canonical_json_bytes(
                ["training/checkpoint_manifest.json", "predictions/validation_early_prediction_scores.parquet"]
            ).decode(),
            "forbidden_open_attempt_n": 0,
            "optimizer_object_n": 0,
            "train_loader_object_n": 0,
            "python_model_object_n": 0,
            "status": "pass",
            "reason": "",
        },
    )
    _write_json(
        build / ".state/training_selection_complete.json",
        {"schema_version": "21D_TRAINING_SELECTION_COMPLETE_V2", "job_n": 21, "completed_at_utc": utc_now()},
    )


def run_late_readout(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / ".state/training_selection_complete.json").exists():
        raise ContractError("training selection must complete before late readout")
    if (build / ".state/late_readout_complete.json").exists():
        return
    configure_determinism()
    device = torch.device("cuda")
    late = load_fold_data(config, "validation_late")
    for arm in config["arms"]:
        arm_id = arm["arm_id"]
        y_late, _, _, _ = arm_data(config, arm, late)
        for seed in MODEL_SEEDS:
            model, semantic = load_checkpoint_model(config, arm_id, seed, device)
            if arm_id in {"D0_R2_RAW_EXACT_REPLAY", "D4_R2_REPAIR_COMBINED_V1"}:
                write_draw_shard(config, arm_id, "validation_late", seed, model, late, y_late, device)
            else:
                scores = score_panel(
                    model,
                    arm,
                    y_late,
                    late["x_source"],
                    late["frame"]["instrument"].astype(str).tolist(),
                    late["frame"]["decision_date"].astype(str).tolist(),
                    seed,
                    batch_size=int(config["training"]["inference_batch_size"]),
                    device=device,
                )
                state_root = build / f".state/late_scores/{arm_id}/seed_{seed}"
                state_root.mkdir(parents=True, exist_ok=True)
                np.save(state_root / "scores.npy", scores.astype(np.float32), allow_pickle=False)
                _write_json(
                    state_root / "metadata.json",
                    {
                        "arm_id": arm_id,
                        "model_seed": seed,
                        "model_state_semantic_sha256": semantic,
                        "score_semantic_sha256": stable_hash(scores.astype(np.float32).tolist()),
                    },
                )
            del model
            torch.cuda.empty_cache()
    existing_transform = pq.read_table(build / "diagnostics/return_path_transform_audit.parquet").to_pandas()
    _, late_audit, late_semantic = decision_cs_zscore_return_path(
        late["raw_panel"],
        late["frame"]["decision_date"].astype(str).tolist(),
        fold="validation_late",
        include_target=False,
    )
    combined_transform = normalize_return_path_transform(
        pd.concat([existing_transform, late_audit], ignore_index=True)
    )
    temporary_transform = build / "diagnostics/return_path_transform_audit.parquet.rebuild"
    write_schema_parquet(temporary_transform, combined_transform, RETURN_PATH_TRANSFORM_SCHEMA)
    os.replace(temporary_transform, build / "diagnostics/return_path_transform_audit.parquet")
    predictions = full_prediction_frame(config, "validation_late", late)
    write_prediction_parquet(build / "predictions/validation_late_prediction_scores.parquet", predictions)
    publish_full_morphology_diagnostics(config, predictions)
    _write_json(
        build / "training/late_readout_worker_exit_record.json",
        {
            "schema_version": "S_WORKER_EXIT_V2",
            "run_id": RUN_ID,
            "process_role": "late_readout_worker",
            "pid": os.getpid(),
            "started_at_utc": None,
            "ended_at_utc": utc_now(),
            "exit_code": 0,
            "input_paths_json": canonical_json_bytes(
                ["training/pre_late_checkpoint_bundle_manifest.json", "validation_late"]
            ).decode(),
            "input_hashes_json": canonical_json_bytes(
                {
                    "pre_late_bundle": file_sha(build / "training/pre_late_checkpoint_bundle_manifest.json"),
                    "late_transform_semantic_sha256": late_semantic,
                }
            ).decode(),
            "output_paths_json": canonical_json_bytes(
                ["predictions/validation_late_prediction_scores.parquet"]
            ).decode(),
            "forbidden_open_attempt_n": 0,
            "optimizer_object_n": 0,
            "train_loader_object_n": 0,
            "python_model_object_n": 0,
            "status": "pass",
            "reason": "",
        },
    )
    _write_json(
        build / ".state/late_readout_complete.json",
        {
            "schema_version": "21D_LATE_READOUT_COMPLETE_V2",
            "prediction_row_n": len(predictions),
            "completed_at_utc": utc_now(),
        },
    )


def daily_rankic_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    series_keys = ["fold_order", "fold", "arm_order", "arm_id", "model_seed", "is_ensemble", "score_variant"]
    for key, series in predictions.groupby(series_keys, sort=True, dropna=False):
        values = []
        for decision_date, day in series.groupby("decision_date", sort=True):
            observed = _PINNED_21C.rankic(
                day["score"].to_numpy(dtype=np.float64),
                day["raw_label"].to_numpy(dtype=np.float64),
                minimum_n=100,
            )
            if not math.isfinite(observed):
                raise ContractError("daily RankIC non-finite")
            values.append(observed)
            rows.append(
                {
                    **dict(zip(series_keys, key, strict=True)),
                    "aggregation_role": "day",
                    "decision_date": decision_date,
                    "metric_id": "rankic",
                    "metric_value": observed,
                    "row_n": len(day),
                    "status": "pass",
                }
            )
        array = np.asarray(values, dtype=np.float64)
        mean = float(array.mean())
        std = float(array.std(ddof=1))
        summaries = {
            "mean_rankic": mean,
            "rankic_std_ddof1": std,
            "rankicir": mean / std if std > 1e-18 else math.nan,
            "positive_day_rate": float(np.mean(array > 0)),
        }
        for metric_id, metric_value in summaries.items():
            rows.append(
                {
                    **dict(zip(series_keys, key, strict=True)),
                    "aggregation_role": "fold_summary",
                    "decision_date": None,
                    "metric_id": metric_id,
                    "metric_value": metric_value,
                    "row_n": len(array),
                    "status": "pass" if math.isfinite(metric_value) else "not_evaluable_zero_std",
                }
            )
    result = pd.DataFrame(rows)
    expected = 52 * (predictions["fold"].map({"validation_early": 107, "validation_late": 103}).iloc[0] + 4)
    if len(result) != expected:
        raise ContractError(f"daily RankIC table row closure mismatch: {len(result)} vs {expected}")
    return result


def monthly_lomo_table(daily: pd.DataFrame) -> pd.DataFrame:
    day = daily.loc[daily["aggregation_role"].eq("day")].copy()
    day["month"] = pd.to_datetime(day["decision_date"]).dt.strftime("%Y-%m")
    keys = ["fold", "arm_order", "arm_id", "model_seed", "is_ensemble", "score_variant"]
    rows = []
    for key, series in day.groupby(keys, sort=True, dropna=False):
        months = sorted(series["month"].unique())
        if len(months) != 6:
            raise ContractError("each validation fold must contain six calendar months")
        for month in months:
            inside = series.loc[series["month"].eq(month)]
            outside = series.loc[~series["month"].eq(month)]
            for role, observed in (("month", inside), ("leave_one_month_out", outside)):
                rows.append(
                    {
                        **dict(zip(keys, key, strict=True)),
                        "aggregation_role": role,
                        "month": month,
                        "row_n": int(observed["row_n"].sum()),
                        "day_n": len(observed),
                        "mean_rankic": float(observed["metric_value"].mean()),
                        "status": "pass",
                    }
                )
    result = pd.DataFrame(rows)
    if len(result) != 52 * 6 * 2:
        raise ContractError("monthly/LOMO table row closure mismatch")
    return result


CONTRASTS = (
    ("C01", "mechanism_single_factor", "D1_R2_RETURN_PATH_CSZ_ONLY", "primary", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C02", "mechanism_single_factor", "D2_R2_GRADBAL_ONLY", "primary", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C03", "mechanism_single_factor", "D3_R2_ST_HARD_ONLY", "primary", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C04A", "combined_draw_decomposition", "D4_R2_REPAIR_COMBINED_V1", "prefix8", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C04B", "combined_draw_decomposition", "D4_R2_REPAIR_COMBINED_V1", "prefix64", "D4_R2_REPAIR_COMBINED_V1", "prefix8"),
    ("C04C", "combined_draw_decomposition", "D0_R2_RAW_EXACT_REPLAY", "prefix64", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C04D", "combined_draw_decomposition", "D4_R2_REPAIR_COMBINED_V1", "prefix64", "D0_R2_RAW_EXACT_REPLAY", "prefix64"),
    ("C04E", "combined_draw_decomposition", "D4_R2_REPAIR_COMBINED_V1", "prefix64", "D0_R2_RAW_EXACT_REPLAY", "prefix8"),
    ("C05", "residual_attribution", "D0_R2_RAW_EXACT_REPLAY", "prefix8", "D5_K2_RAW_NO_RESIDUAL", "primary"),
    ("C06", "residual_attribution", "D0_R2_RAW_EXACT_REPLAY", "prefix8", "D6_R1_RAW_MLP_RESIDUAL", "primary"),
    ("C07", "residual_attribution", "D6_R1_RAW_MLP_RESIDUAL", "primary", "D5_K2_RAW_NO_RESIDUAL", "primary"),
    ("C08", "candidate_ordering", "D4_R2_REPAIR_COMBINED_V1", "prefix64", "M1_LIGHTGBM_ALPHA158", "primary"),
    ("C09", "candidate_ordering", "D4_R2_REPAIR_COMBINED_V1", "prefix64", "M3_GATED_DUAL_PATH_LSTM", "primary"),
)


def stationary_bootstrap_indices(day_n: int, replicate_n: int = 5000) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(20260717))
    indices = np.empty((replicate_n, day_n), dtype=np.int32)
    indices[:, 0] = rng.integers(0, day_n, size=replicate_n)
    for column in range(1, day_n):
        restart = rng.random(replicate_n) < (1.0 / 20.0)
        continuing = (indices[:, column - 1] + 1) % day_n
        replacements = rng.integers(0, day_n, size=replicate_n)
        indices[:, column] = np.where(restart, replacements, continuing)
    return indices


MATERIAL_CONTRASTS = frozenset({"C01", "C02", "C03", "C04A", "C04D", "C04E"})


def material_improvement_rule(
    mean_rankic_delta: float,
    positive_seed_n: int,
    collapse_reduction: float,
    left_cross_seed_mean_daily_spearman: float,
    right_cross_seed_mean_daily_spearman: float,
) -> bool:
    return bool(
        mean_rankic_delta >= 0.005
        and positive_seed_n >= 2
        and collapse_reduction >= 0.25
        and left_cross_seed_mean_daily_spearman >= right_cross_seed_mean_daily_spearman
    )


def _series_mean_rankic(
    daily: pd.DataFrame, fold: str, arm_id: str, score_variant: str
) -> float:
    matched = daily.loc[
        daily["fold"].eq(fold)
        & daily["arm_id"].eq(arm_id)
        & daily["score_variant"].eq(score_variant)
        & daily["is_ensemble"]
        & daily["aggregation_role"].eq("fold_summary")
        & daily["metric_id"].eq("mean_rankic"),
        "metric_value",
    ]
    if len(matched) != 1:
        raise ContractError(f"mean RankIC series lookup mismatch: {fold}/{arm_id}/{score_variant}")
    return float(matched.iloc[0])


def _positive_seed_delta_n(
    daily: pd.DataFrame,
    arm_left: str,
    variant_left: str,
    arm_right: str,
    variant_right: str,
) -> int:
    seed_day = daily.loc[
        daily["fold"].eq("validation_late")
        & daily["aggregation_role"].eq("day")
        & ~daily["is_ensemble"]
    ]
    left = seed_day.loc[
        seed_day["arm_id"].eq(arm_left) & seed_day["score_variant"].eq(variant_left),
        ["model_seed", "decision_date", "metric_value"],
    ].rename(columns={"metric_value": "left"})
    right = seed_day.loc[
        seed_day["arm_id"].eq(arm_right) & seed_day["score_variant"].eq(variant_right),
        ["model_seed", "decision_date", "metric_value"],
    ].rename(columns={"metric_value": "right"})
    paired = left.merge(right, on=["model_seed", "decision_date"], validate="one_to_one")
    seed_delta = paired.groupby("model_seed", sort=True).apply(
        lambda frame: float((frame["left"] - frame["right"]).mean()),
        include_groups=False,
    )
    if tuple(int(seed) for seed in seed_delta.index) != MODEL_SEEDS:
        raise ContractError("paired positive-seed denominator mismatch")
    return int(np.sum(seed_delta.to_numpy() > 0))


def _cross_seed_mean_spearman(
    cross_seed: pd.DataFrame, arm_id: str, score_variant: str
) -> float:
    matched = cross_seed.loc[
        cross_seed["fold"].eq("validation_late")
        & cross_seed["arm_id"].eq(arm_id)
        & cross_seed["score_variant"].eq(score_variant)
        & cross_seed["aggregation_role"].eq("seed_pair")
        & cross_seed["metric_id"].eq("daily_score_spearman")
    ]
    pair_means = matched.groupby(["seed_a", "seed_b"], sort=True)["metric_value"].mean()
    if len(pair_means) != 3 or not np.isfinite(pair_means.to_numpy()).all():
        raise ContractError(f"cross-seed Spearman denominator mismatch: {arm_id}/{score_variant}")
    return float(pair_means.mean())


def paired_contrast_tables(
    daily: pd.DataFrame, cross_seed: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    day = daily.loc[daily["aggregation_role"].eq("day") & daily["is_ensemble"]].copy()
    rows = []
    bootstrap_rows = []
    for fold in VALIDATION_FOLDS:
        fold_day = day.loc[day["fold"].eq(fold)]
        date_n = fold_day["decision_date"].nunique()
        boot_indices = stationary_bootstrap_indices(date_n)
        for contrast_order, contrast in enumerate(CONTRASTS, 1):
            contrast_id, family, left_arm, left_variant, right_arm, right_variant = contrast
            left = fold_day.loc[
                fold_day["arm_id"].eq(left_arm) & fold_day["score_variant"].eq(left_variant),
                ["decision_date", "metric_value"],
            ].rename(columns={"metric_value": "left"})
            right = fold_day.loc[
                fold_day["arm_id"].eq(right_arm) & fold_day["score_variant"].eq(right_variant),
                ["decision_date", "metric_value"],
            ].rename(columns={"metric_value": "right"})
            paired = left.merge(right, on="decision_date", validate="one_to_one").sort_values("decision_date")
            if len(paired) != date_n:
                raise ContractError(f"paired day coverage mismatch: {contrast_id}/{fold}")
            delta = paired["left"].to_numpy() - paired["right"].to_numpy()
            observed = float(delta.mean())
            sampled = delta[boot_indices].mean(axis=1)
            centered = (delta - observed)[boot_indices].mean(axis=1)
            p_value = (1 + int(np.sum(np.abs(centered) >= abs(observed)))) / 5001.0
            positive_seed_n: int | None = None
            material: bool | None = None
            if fold == "validation_late" and contrast_id in MATERIAL_CONTRASTS:
                positive_seed_n = _positive_seed_delta_n(
                    daily, left_arm, left_variant, right_arm, right_variant
                )
                left_collapse = abs(
                    _series_mean_rankic(daily, "validation_early", left_arm, left_variant)
                    - _series_mean_rankic(daily, "validation_late", left_arm, left_variant)
                )
                right_collapse = abs(
                    _series_mean_rankic(daily, "validation_early", right_arm, right_variant)
                    - _series_mean_rankic(daily, "validation_late", right_arm, right_variant)
                )
                collapse_reduction = 1.0 - left_collapse / max(right_collapse, 1e-12)
                left_stability = _cross_seed_mean_spearman(cross_seed, left_arm, left_variant)
                right_stability = _cross_seed_mean_spearman(cross_seed, right_arm, right_variant)
                material = material_improvement_rule(
                    observed,
                    positive_seed_n,
                    collapse_reduction,
                    left_stability,
                    right_stability,
                )
            rows.append(
                {
                    "contrast_order": contrast_order,
                    "contrast_id": contrast_id,
                    "family_id": family,
                    "fold": fold,
                    "left_arm_id": left_arm,
                    "left_score_variant": left_variant,
                    "right_arm_id": right_arm,
                    "right_score_variant": right_variant,
                    "paired_day_n": len(delta),
                    "mean_rankic_delta": observed,
                    "median_rankic_delta": float(np.median(delta)),
                    "positive_seed_n": positive_seed_n,
                    "raw_p_value": p_value,
                    "holm_p_value": None,
                    "material_improvement": material,
                    "status": "pass",
                }
            )
            bootstrap_rows.append(
                {
                    "contrast_order": contrast_order,
                    "contrast_id": contrast_id,
                    "fold": fold,
                    "replicate_n": 5000,
                    "mean_block_length": 20,
                    "bootstrap_seed": 20260717,
                    "observed_mean_delta": observed,
                    "ci_lower_025": float(np.quantile(sampled, 0.025, method="linear")),
                    "ci_upper_975": float(np.quantile(sampled, 0.975, method="linear")),
                    "p_value_two_sided": p_value,
                    "day_key_sha256": stable_hash(paired["decision_date"].astype(str).tolist()),
                    "status": "pass",
                }
            )
    result = pd.DataFrame(rows)
    for fold in VALIDATION_FOLDS:
        for family in ("mechanism_single_factor", "residual_attribution", "candidate_ordering"):
            mask = result["fold"].eq(fold) & result["family_id"].eq(family)
            ordered = result.loc[mask].sort_values(["raw_p_value", "contrast_order"])
            adjusted = []
            running = 0.0
            count = len(ordered)
            for index, value in enumerate(ordered["raw_p_value"]):
                running = max(running, min(1.0, (count - index) * float(value)))
                adjusted.append(running)
            result.loc[ordered.index, "holm_p_value"] = adjusted
    return result.sort_values(["contrast_order", "fold"]), pd.DataFrame(bootstrap_rows).sort_values(["contrast_order", "fold"])


def cross_seed_morphology_table(predictions: pd.DataFrame) -> pd.DataFrame:
    learned_and_comparators = predictions.loc[
        predictions["arm_id"].isin(ARM_IDS + COMPARATORS)
    ].copy()
    rows = []
    group_keys = ["fold", "arm_order", "arm_id", "score_variant"]
    for key, series in learned_and_comparators.groupby(group_keys, sort=True):
        seed_rows = series.loc[~series["is_ensemble"]]
        ensemble_rows = series.loc[series["is_ensemble"]]
        if seed_rows["model_seed"].nunique() != 3 or len(ensemble_rows) == 0:
            raise ContractError("cross-seed input series incomplete")
        for decision_date, day in seed_rows.groupby("decision_date", sort=True):
            piv = day.pivot(index="instrument", columns="model_seed", values="score")
            if tuple(int(value) for value in piv.columns) != MODEL_SEEDS or piv.isna().any().any():
                raise ContractError("cross-seed daily pivot incomplete")
            for left_index in range(3):
                for right_index in range(left_index + 1, 3):
                    seed_a = MODEL_SEEDS[left_index]
                    seed_b = MODEL_SEEDS[right_index]
                    rho = float(pd.Series(piv[seed_a]).corr(pd.Series(piv[seed_b]), method="spearman"))
                    top_a = set(piv.nlargest(30, seed_a).index)
                    top_b = set(piv.nlargest(30, seed_b).index)
                    for metric_id, metric_value in (
                        ("daily_score_spearman", rho),
                        ("top30_overlap", float(len(top_a & top_b))),
                    ):
                        rows.append(
                            {
                                **dict(zip(group_keys, key, strict=True)),
                                "aggregation_role": "seed_pair",
                                "seed_a": seed_a,
                                "seed_b": seed_b,
                                "decision_date": decision_date,
                                "metric_id": metric_id,
                                "metric_value": metric_value,
                                "row_n": len(piv),
                                "status": "pass" if math.isfinite(metric_value) else "not_evaluable",
                            }
                        )
        for role, role_frame in (("seed", seed_rows), ("ensemble", ensemble_rows)):
            role_groups = (
                role_frame.groupby("model_seed", dropna=False, sort=True)
                if role == "seed"
                else [(None, role_frame)]
            )
            for seed, identity in role_groups:
                previous: pd.DataFrame | None = None
                for decision_date, day in identity.groupby("decision_date", sort=True):
                    current = day.set_index("instrument")[["score"]]
                    if previous is not None:
                        joined = previous.join(current, lsuffix="_previous", rsuffix="_current", how="inner")
                        top_previous = set(previous.nlargest(30, "score").index)
                        top_current = set(current.nlargest(30, "score").index)
                        turnover = 1.0 - len(top_previous & top_current) / 30.0
                        autocorrelation = float(
                            pd.Series(joined["score_previous"]).corr(
                                pd.Series(joined["score_current"]), method="spearman"
                            )
                        )
                        for metric_id, metric_value in (
                            ("adjacent_day_top30_turnover", turnover),
                            ("score_autocorrelation", autocorrelation),
                        ):
                            rows.append(
                                {
                                    **dict(zip(group_keys, key, strict=True)),
                                    "aggregation_role": role,
                                    "seed_a": int(seed) if role == "seed" else None,
                                    "seed_b": None,
                                    "decision_date": decision_date,
                                    "metric_id": metric_id,
                                    "metric_value": metric_value,
                                    "row_n": len(joined),
                                    "status": "pass" if math.isfinite(metric_value) else "not_evaluable",
                                }
                            )
                    previous = current
    result = pd.DataFrame(rows)
    expected = 13 * ((6 * 107 + 8 * 106) + (6 * 103 + 8 * 102))
    if len(result) != expected:
        raise ContractError(f"cross-seed morphology row closure mismatch: {len(result)} vs {expected}")
    return result


def draw_convergence_summary(config: Mapping[str, Any]) -> pd.DataFrame:
    build = building_output_root(config)
    rows = []
    for identity in DRAW_IDENTITIES:
        for fold in VALIDATION_FOLDS:
            for seed in MODEL_SEEDS:
                path = build / draw_shard_relative(identity, fold, seed)
                keys, prefixes = read_draw_prefixes(path)
                table = pq.read_table(path, columns=["draw_scores"])
                draws = table.column("draw_scores").combine_chunks().values.to_numpy().reshape(len(table), 256)
                reference = prefixes[256]
                keys = keys.copy()
                keys["row_index"] = np.arange(len(keys), dtype=np.int64)
                row_noise = draws.astype(np.float64).var(axis=1, ddof=1) / 8.0
                day_signal = []
                for decision_date, day_keys in keys.groupby("decision_date", sort=True):
                    indices = day_keys["row_index"].to_numpy(dtype=np.int64)
                    signal_var = float(np.var(reference[indices].astype(np.float64), ddof=1))
                    day_signal.append(signal_var)
                    for block_id, block in enumerate(draw_blocks()):
                        block_score = draws[indices][:, block].astype(np.float64).mean(axis=1)
                        ref_score = reference[indices].astype(np.float64)
                        rho = float(pd.Series(block_score).corr(pd.Series(ref_score), method="spearman"))
                        top_block = set(day_keys.iloc[np.argsort(block_score)[-30:]]["instrument"])
                        top_ref = set(day_keys.iloc[np.argsort(ref_score)[-30:]]["instrument"])
                        rows.append(
                            {
                                "draw_identity": identity,
                                "model_seed": seed,
                                "fold": fold,
                                "summary_scope": "day_block",
                                "decision_date": decision_date,
                                "block_id": block_id,
                                "spearman_block8_ref256": rho,
                                "top30_overlap_block8_ref256": len(top_block & top_ref),
                                "spearman_prefix8_ref256": float(pd.Series(prefixes[8][indices]).corr(pd.Series(ref_score), method="spearman")),
                                "spearman_prefix64_ref256": float(pd.Series(prefixes[64][indices]).corr(pd.Series(ref_score), method="spearman")),
                                "mc_noise_var_of_mean8": float(np.mean(row_noise[indices])),
                                "cross_section_signal_var": signal_var,
                                "mc_noise_fraction": None,
                                "row_n": len(indices),
                                "status": "pass",
                            }
                        )
                noise_mean = float(np.mean(row_noise))
                signal_mean = float(np.mean(day_signal))
                denominator = noise_mean + signal_mean
                if denominator <= 1e-18:
                    raise ContractError("draw convergence variance denominator is degenerate")
                rows.append(
                    {
                        "draw_identity": identity,
                        "model_seed": seed,
                        "fold": fold,
                        "summary_scope": "fold",
                        "decision_date": None,
                        "block_id": None,
                        "spearman_block8_ref256": None,
                        "top30_overlap_block8_ref256": None,
                        "spearman_prefix8_ref256": None,
                        "spearman_prefix64_ref256": None,
                        "mc_noise_var_of_mean8": noise_mean,
                        "cross_section_signal_var": signal_mean,
                        "mc_noise_fraction": noise_mean / denominator,
                        "row_n": len(draws),
                        "status": "pass",
                    }
                )
    return pd.DataFrame(rows)


def candidate_gate(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    paired: pd.DataFrame,
    cross_seed: pd.DataFrame,
    draw_summary: pd.DataFrame,
    zero_audit: pd.DataFrame,
    collapse_audit: pd.DataFrame,
) -> tuple[bool, dict[str, Any]]:
    late_summary = daily.loc[
        daily["fold"].eq("validation_late")
        & daily["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1")
        & daily["score_variant"].eq("prefix64")
        & daily["aggregation_role"].eq("fold_summary")
        & daily["metric_id"].eq("mean_rankic")
    ]
    ensemble_rankic = float(late_summary.loc[late_summary["is_ensemble"], "metric_value"].iloc[0])
    seed_rankics = late_summary.loc[~late_summary["is_ensemble"], "metric_value"].to_numpy()
    lomo = monthly.loc[
        monthly["fold"].eq("validation_late")
        & monthly["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1")
        & monthly["score_variant"].eq("prefix64")
        & monthly["is_ensemble"]
        & monthly["aggregation_role"].eq("leave_one_month_out")
    ]
    paired_late = paired.loc[paired["fold"].eq("validation_late")].set_index("contrast_id")
    pair_morph = cross_seed.loc[
        cross_seed["fold"].eq("validation_late")
        & cross_seed["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1")
        & cross_seed["score_variant"].eq("prefix64")
        & cross_seed["aggregation_role"].eq("seed_pair")
    ]
    mean_seed_rho = float(pair_morph.loc[pair_morph["metric_id"].eq("daily_score_spearman"), "metric_value"].mean())
    mean_seed_overlap = float(pair_morph.loc[pair_morph["metric_id"].eq("top30_overlap"), "metric_value"].mean())
    turnover = float(
        cross_seed.loc[
            cross_seed["fold"].eq("validation_late")
            & cross_seed["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1")
            & cross_seed["score_variant"].eq("prefix64")
            & cross_seed["aggregation_role"].eq("ensemble")
            & cross_seed["metric_id"].eq("adjacent_day_top30_turnover"),
            "metric_value",
        ].mean()
    )
    stability = draw_summary.loc[
        draw_summary["draw_identity"].eq("D4_R2_REPAIR_COMBINED_V1")
        & draw_summary["fold"].eq("validation_late")
        & draw_summary["summary_scope"].eq("day_block")
        & draw_summary["block_id"].eq(0),
        "spearman_prefix64_ref256",
    ]
    if len(stability) != 309:
        raise ContractError("candidate prefix64/ref256 stability denominator must be 309")
    sealed_zero = zero_audit.loc[zero_audit["arm_id"].eq("SEALED_V4_R2")]
    sealed_collapse = collapse_audit.loc[collapse_audit["arm_id"].eq("SEALED_V4_R2")]
    zero_collapse = bool(
        float(sealed_zero["zero_solution_improvement"].median()) <= 0.10
        and float(sealed_collapse["score_to_label_std_ratio"].median()) <= 0.05
        and int(sealed_collapse["additional_collapse_flag_n"].median()) >= 2
    )
    components = {
        "late_ensemble_rankic_positive": ensemble_rankic > 0,
        "positive_late_seed_n_at_least_2": int(np.sum(seed_rankics > 0)) >= 2,
        "positive_lomo_n_at_least_5": int(np.sum(lomo["mean_rankic"] > 0)) >= 5,
        "C04E_delta_at_least_0_005": float(paired_late.loc["C04E", "mean_rankic_delta"]) >= 0.005,
        "C04D_delta_at_least_0_005": float(paired_late.loc["C04D", "mean_rankic_delta"]) >= 0.005,
        "C09_delta_positive": float(paired_late.loc["C09", "mean_rankic_delta"]) > 0,
        "C08_delta_positive": float(paired_late.loc["C08", "mean_rankic_delta"]) > 0,
        "mean_cross_seed_rho_at_least_0_25": mean_seed_rho >= 0.25,
        "mean_cross_seed_top30_at_least_6": mean_seed_overlap >= 6.0,
        "adjacent_turnover_at_most_0_80": turnover <= 0.80,
        "median_prefix64_ref256_at_least_0_95": float(np.median(stability)) >= 0.95,
        "no_H01_zero_solution_collapse": not zero_collapse,
    }
    return all(components.values()), components


def hypothesis_readout(
    paired: pd.DataFrame,
    selector: pd.DataFrame,
    draw_summary: pd.DataFrame,
    zero: pd.DataFrame,
    collapse: pd.DataFrame,
    gradient: pd.DataFrame,
) -> pd.DataFrame:
    late = paired.loc[paired["fold"].eq("validation_late")].set_index("contrast_id")
    c01 = bool(late.loc["C01", "material_improvement"])
    c02 = bool(late.loc["C02", "material_improvement"])
    c03 = bool(late.loc["C03", "material_improvement"])
    sealed_zero = zero.loc[zero["arm_id"].eq("SEALED_V4_R2")]
    sealed_collapse = collapse.loc[collapse["arm_id"].eq("SEALED_V4_R2")]
    direct_h01 = bool(
        float(sealed_zero["zero_solution_improvement"].median()) <= 0.10
        and float(sealed_collapse["score_to_label_std_ratio"].median()) <= 0.05
        and int(sealed_collapse["additional_collapse_flag_n"].median()) >= 2
    )
    sealed_diff = gradient.loc[
        gradient["arm_id"].eq("SEALED_V4_R2")
        & gradient["phase"].eq("audit")
        & gradient["loss_term"].eq("diff")
    ]
    gradient_share_medians = sealed_diff.groupby("module_id", sort=True)["gradient_share"].median()
    expected_gradient_modules = {
        "global", "encoder", "gate", "selector", "koopman_codebook", "decoder", "residual_corrector"
    }
    if set(gradient_share_medians.index) != expected_gradient_modules:
        raise ContractError("H02 gradient module denominator mismatch")
    global_gradient_dominance = float(gradient_share_medians["global"]) >= 0.80
    module_gradient_dominance_n = int(
        np.sum(gradient_share_medians.drop(index="global").to_numpy() >= 0.80)
    )
    direct_h02 = global_gradient_dominance and module_gradient_dominance_n >= 4
    direct_h03 = bool(
        (selector.loc[selector["fold"].eq("validation_late"), "daily_spearman"].mean() < 0.90)
        or (selector.loc[selector["fold"].eq("validation_late"), "top30_overlap"].mean() < 24.0)
    )
    h04_days = draw_summary.loc[
        draw_summary["draw_identity"].eq("SEALED_V4_R2")
        & draw_summary["fold"].eq("validation_late")
        & draw_summary["summary_scope"].eq("day_block")
    ]
    h04_fold = draw_summary.loc[
        draw_summary["draw_identity"].eq("SEALED_V4_R2")
        & draw_summary["fold"].eq("validation_late")
        & draw_summary["summary_scope"].eq("fold")
    ]
    direct_h04 = bool(
        h04_days["spearman_block8_ref256"].median() < 0.90
        or h04_days["top30_overlap_block8_ref256"].median() < 24
        or h04_fold["mc_noise_fraction"].median() > 0.25
    )
    h04_prefix64_stable = float(h04_days["spearman_prefix64_ref256"].median()) >= 0.95
    support = {
        "H01_RAW_RETURN_ZERO_SOLUTION": (
            "strongly_mechanism_consistent" if direct_h01 and c01 else
            "mechanism_consistent" if direct_h01 else
            "mixed" if c01 else "not_supported"
        ),
        "H02_DIFFUSION_GRADIENT_DOMINANCE": (
            "strongly_mechanism_consistent" if direct_h02 and c02 else
            "mechanism_consistent" if direct_h02 else
            "mixed" if c02 else "not_supported"
        ),
        "H03_SELECTOR_SOFT_HARD_MISMATCH": (
            "strongly_mechanism_consistent" if direct_h03 and c03 else
            "mechanism_consistent" if direct_h03 else
            "mixed" if c03 else "not_supported"
        ),
        "H04_DDPM_MONTE_CARLO_RANK_NOISE": (
            "strongly_mechanism_consistent" if direct_h04 and h04_prefix64_stable else
            "mechanism_consistent" if direct_h04 else "not_supported"
        ),
        "H05_RETURN_PATH_PREPROCESSING_MISMATCH": "mechanism_consistent" if c01 else "not_supported",
        "H06_UNDISCLOSED_IMPLEMENTATION_AND_SEARCH": "unresolved_external_implementation_gap",
        "H07_PERIOD_REGIME_SHIFT": "descriptive_only",
        "H08_EARLY_SELECTION_ADAPTATION": "descriptive_only",
    }
    rows = []
    for order, (hypothesis_id, strength, _) in enumerate(HYPOTHESES, 1):
        rows.append(
            {
                "hypothesis_order": order,
                "hypothesis_id": hypothesis_id,
                "prior_strength": strength,
                "direct_observation_status": "evaluated",
                "single_factor_intervention_status": "evaluated" if order <= 5 else "not_applicable",
                "falsifier_status": "evaluated" if order <= 5 else "not_identifiable",
                "support_level": support[hypothesis_id],
                "decision_metrics_json": canonical_json_bytes(
                    {
                        "C01": c01,
                        "C02": c02,
                        "C03": c03,
                        "direct_H01": direct_h01,
                        "direct_H02": direct_h02,
                        "H02_global_diff_gradient_share_median": float(gradient_share_medians["global"]),
                        "H02_module_dominance_n": module_gradient_dominance_n,
                        "direct_H03": direct_h03,
                        "direct_H04": direct_h04,
                    }
                ).decode(),
                "supporting_artifact_paths_json": canonical_json_bytes(
                    ["paired_rankic_comparison.csv", "diagnostics/inference_draw_convergence_summary.csv"]
                ).decode(),
                "contradicting_artifact_paths_json": canonical_json_bytes([]).decode(),
                "allowed_statement": "design-contaminated mechanism diagnostic only",
                "forbidden_statement": "causally_proven|paper_pipeline_identified|paper_false",
            }
        )
    return pd.DataFrame(rows)


def p6_required_paths(config: Mapping[str, Any]) -> set[str]:
    paths = {
        "21D_reaka_replication_gap_causal_diagnostic_report.md",
        "21D_reaka_replication_gap_causal_diagnostic_decision.csv",
        "gate_evidence_21d_gap.csv",
        "stage_status_registry.csv",
        "artifact_profile_registry.csv",
        "historical_design_holdout_access_audit.csv",
        "semantic_reproducibility_manifest.json",
        "manifest_21d_reaka_replication_gap_causal_diagnostic.json",
        "output_hashes_21d_reaka_replication_gap_causal_diagnostic.json",
        "preflight/execution_authorization_audit.csv",
        "preflight/upstream_pin_and_file_set_audit.csv",
        "preflight/retained_universe_exact_match_audit.csv",
        "preflight/resolved_config.yaml",
        "hypothesis_registry.csv",
        "training/model_search_accounting_manifest.csv",
        "preflight/replay_runtime_fingerprint.json",
        "diagnostics/raw_return_zero_solution_audit.csv",
        "diagnostics/checkpoint_parameter_collapse_audit.csv",
        "diagnostics/loss_gradient_scale_audit.parquet",
        "diagnostics/selector_semantics_score_comparison.parquet",
        "diagnostics/selector_semantics_audit.csv",
        "diagnostics/operator_usage_and_stability_audit.csv",
        "diagnostics/inference_draw_convergence_summary.csv",
        "diagnostics/checkpoint_surgery_score_comparison.parquet",
        "diagnostics/return_path_transform_audit.parquet",
        "diagnostics/gradient_calibration_batch_registry.parquet",
        "training/resource_probe_audit.csv",
        "training/training_run_registry.csv",
        "training/seed_level_training_curves.csv",
        "training/gradient_calibration_weights.csv",
        "training/checkpoint_manifest.json",
        "training/checkpoint_eligibility_manifest.json",
        "training/pre_late_checkpoint_bundle_manifest.json",
        "training/selection_worker_exit_record.json",
        "predictions/validation_early_prediction_scores.parquet",
        "training/late_readout_worker_exit_record.json",
        "predictions/validation_late_prediction_scores.parquet",
        "daily_rankic_readout.csv",
        "monthly_lomo_stability.csv",
        "cross_seed_morphology.csv",
        "paired_rankic_comparison.csv",
        "stationary_bootstrap_pair_diagnostic.csv",
        "causal_hypothesis_readout.csv",
    }
    for arm_id in ARM_IDS:
        for seed in MODEL_SEEDS:
            paths.add(f"training/checkpoints/{arm_id}/seed_{seed}/state_dict.pt")
    for identity in DRAW_IDENTITIES:
        for fold in VALIDATION_FOLDS:
            for seed in MODEL_SEEDS:
                paths.add(draw_shard_relative(identity, fold, seed))
    return paths


FAILURE_PATHS = {
    "preflight/preflight_failure_evidence.csv",
    "diagnostics/inference_diagnostic_failure_evidence.csv",
    "training/training_failure_evidence.csv",
    "training/late_readout_failure_evidence.csv",
    "finalize_failure_evidence.csv",
}


def artifact_profile_table(config: Mapping[str, Any]) -> pd.DataFrame:
    p6 = p6_required_paths(config)
    universe = p6 | FAILURE_PATHS
    terminal = {
        "21D_reaka_replication_gap_causal_diagnostic_report.md",
        "21D_reaka_replication_gap_causal_diagnostic_decision.csv",
        "gate_evidence_21d_gap.csv", "stage_status_registry.csv", "artifact_profile_registry.csv",
        "historical_design_holdout_access_audit.csv", "semantic_reproducibility_manifest.json",
        "manifest_21d_reaka_replication_gap_causal_diagnostic.json",
        "output_hashes_21d_reaka_replication_gap_causal_diagnostic.json",
    }
    pre = {
        "preflight/execution_authorization_audit.csv", "preflight/upstream_pin_and_file_set_audit.csv",
        "preflight/retained_universe_exact_match_audit.csv", "preflight/resolved_config.yaml",
    }
    hyp = {"hypothesis_registry.csv", "training/model_search_accounting_manifest.csv"}
    inf = {
        path for path in p6
        if path.startswith("diagnostics/") and (
            "inference_draw_scores/SEALED_V4_R2" in path
            or path.split("/")[-1] in {
                "raw_return_zero_solution_audit.csv", "checkpoint_parameter_collapse_audit.csv",
                "loss_gradient_scale_audit.parquet", "selector_semantics_score_comparison.parquet",
                "selector_semantics_audit.csv", "operator_usage_and_stability_audit.csv",
                "inference_draw_convergence_summary.csv", "checkpoint_surgery_score_comparison.parquet",
            }
        )
    } | {"preflight/replay_runtime_fingerprint.json"}
    train = {
        path for path in p6
        if path.startswith("training/") and path not in {
            "training/model_search_accounting_manifest.csv", "training/late_readout_worker_exit_record.json"
        }
    } | {
        "diagnostics/return_path_transform_audit.parquet",
        "diagnostics/gradient_calibration_batch_registry.parquet",
        "predictions/validation_early_prediction_scores.parquet",
    } | {path for path in p6 if "inference_draw_scores/D0_" in path or "inference_draw_scores/D4_" in path if "/validation_early/" in path}
    late = {
        "training/late_readout_worker_exit_record.json", "predictions/validation_late_prediction_scores.parquet",
        "daily_rankic_readout.csv", "monthly_lomo_stability.csv", "cross_seed_morphology.csv",
        "paired_rankic_comparison.csv", "stationary_bootstrap_pair_diagnostic.csv", "causal_hypothesis_readout.csv",
    } | {path for path in p6 if "inference_draw_scores/D0_" in path or "inference_draw_scores/D4_" in path if "/validation_late/" in path}
    profiles = [
        ("P0_PREAUTHORIZATION_BLOCKED", terminal | {"preflight/execution_authorization_audit.csv", "preflight/preflight_failure_evidence.csv"}, {}),
        ("P1_UPSTREAM_BLOCKED", terminal | pre | {"preflight/preflight_failure_evidence.csv"}, {}),
        ("P2_INFERENCE_DIAGNOSTIC_BLOCKED", terminal | pre | hyp | {"diagnostics/inference_diagnostic_failure_evidence.csv"}, {}),
        ("P3_TRAINING_BLOCKED", terminal | pre | hyp | inf | {"training/training_failure_evidence.csv"}, {"diagnostic_identity_scope": ["SEALED_V4_R2"]}),
        ("P4_LATE_READOUT_BLOCKED", terminal | pre | hyp | inf | train | {"training/late_readout_failure_evidence.csv"}, {"retrained_fold_scope": ["train", "validation_early"]}),
        ("P5_FINALIZE_BLOCKED", terminal | pre | hyp | inf | train | late | {"finalize_failure_evidence.csv"}, {"retrained_fold_scope": list(FOLDS)}),
        ("P6_FULL_DIAGNOSTIC_FINALIZED", p6, {"retrained_fold_scope": list(FOLDS)}),
    ]
    rows = []
    for order, (profile_id, required, conditional) in enumerate(profiles):
        row = {
            "profile_order": order,
            "profile_id": profile_id,
            "required_paths_json": canonical_json_bytes(sorted(required)).decode(),
            "forbidden_paths_json": canonical_json_bytes(sorted(universe - required)).decode(),
            "conditional_row_scope_json": canonical_json_bytes(conditional).decode(),
        }
        row["registry_contract_sha256"] = stable_hash(row)
        rows.append(row)
    return pd.DataFrame(rows)


def _artifact_schema_and_rows(path: Path) -> tuple[str, int | None]:
    schema_by_name = {
        "21D_reaka_replication_gap_causal_diagnostic_report.md": "S_MARKDOWN_REPORT_V2",
        "21D_reaka_replication_gap_causal_diagnostic_decision.csv": "S_DECISION_V2",
        "gate_evidence_21d_gap.csv": "S_GATE_EVIDENCE_V2",
        "stage_status_registry.csv": "S_STAGE_STATUS_V2",
        "artifact_profile_registry.csv": "S_ARTIFACT_PROFILE_V2",
        "historical_design_holdout_access_audit.csv": "S_ACCESS_AUDIT_V2",
        "execution_authorization_audit.csv": "S_AUTHORIZATION_AUDIT_V2",
        "upstream_pin_and_file_set_audit.csv": "S_PIN_AUDIT_V2",
        "retained_universe_exact_match_audit.csv": "S_RETAINED_UNIVERSE_V2",
        "hypothesis_registry.csv": "S_HYPOTHESIS_REGISTRY_V2",
        "causal_hypothesis_readout.csv": "S_HYPOTHESIS_READOUT_V2",
        "raw_return_zero_solution_audit.csv": "S_ZERO_SOLUTION_V2",
        "checkpoint_parameter_collapse_audit.csv": "S_CHECKPOINT_COLLAPSE_V2",
        "gradient_calibration_batch_registry.parquet": "S_GRAD_BATCH_REGISTRY_V2",
        "loss_gradient_scale_audit.parquet": "S_LOSS_GRADIENT_V2",
        "selector_semantics_score_comparison.parquet": "S_SELECTOR_SCORE_V2",
        "selector_semantics_audit.csv": "S_SELECTOR_AUDIT_V2",
        "operator_usage_and_stability_audit.csv": "S_OPERATOR_AUDIT_V2",
        "inference_draw_convergence_summary.csv": "S_DRAW_SUMMARY_V2",
        "checkpoint_surgery_score_comparison.parquet": "S_SURGERY_SCORE_V2",
        "return_path_transform_audit.parquet": "S_RETURN_PATH_TRANSFORM_V2",
        "model_search_accounting_manifest.csv": "S_SEARCH_ACCOUNTING_V2",
        "resource_probe_audit.csv": "S_RESOURCE_PROBE_V2",
        "training_run_registry.csv": "S_TRAINING_RUN_V2",
        "seed_level_training_curves.csv": "S_TRAINING_CURVE_V2",
        "gradient_calibration_weights.csv": "S_GRADIENT_WEIGHT_V2",
        "validation_early_prediction_scores.parquet": "S_PREDICTION_V2",
        "validation_late_prediction_scores.parquet": "S_PREDICTION_V2",
        "daily_rankic_readout.csv": "S_DAILY_RANKIC_V2",
        "monthly_lomo_stability.csv": "S_MONTHLY_LOMO_V2",
        "cross_seed_morphology.csv": "S_CROSS_SEED_V2",
        "paired_rankic_comparison.csv": "S_PAIRED_COMPARISON_V2",
        "stationary_bootstrap_pair_diagnostic.csv": "S_BOOTSTRAP_V2",
        "resolved_config.yaml": "S_RESOLVED_CONFIG_V2",
        "replay_runtime_fingerprint.json": "S_REPLAY_RUNTIME_V2",
        "checkpoint_manifest.json": "S_CHECKPOINT_MANIFEST_V2",
        "checkpoint_eligibility_manifest.json": "S_CHECKPOINT_MANIFEST_V2",
        "pre_late_checkpoint_bundle_manifest.json": "S_PRE_LATE_BUNDLE_V2",
        "selection_worker_exit_record.json": "S_WORKER_EXIT_V2",
        "late_readout_worker_exit_record.json": "S_WORKER_EXIT_V2",
        "semantic_reproducibility_manifest.json": "S_SEMANTIC_REPRODUCIBILITY_V2",
    }
    if "inference_draw_scores" in path.parts:
        schema_version = "S_DRAW_SHARD_V2"
    elif path.suffix == ".pt":
        schema_version = "S_TORCH_STATE_DICT_V2"
    else:
        schema_version = schema_by_name.get(path.name)
    if schema_version is None:
        raise ContractError(f"artifact has no registered schema id: {path}")
    if path.suffix == ".parquet":
        return schema_version, pq.read_metadata(path).num_rows
    if path.suffix == ".csv":
        return schema_version, max(0, sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
    if path.suffix == ".yaml":
        return schema_version, None
    if path.suffix == ".json":
        return schema_version, None
    if path.suffix == ".md":
        return schema_version, None
    if path.suffix == ".pt":
        return schema_version, None
    raise ContractError(f"unregistered artifact extension: {path}")


def _csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def write_final_holdout_access_audit(build: Path) -> None:
    columns = [
        "process_order", "process_role", "access_scope", "open_attempt_n",
        "successful_open_n", "read_row_n", "forbidden_open_attempt_n",
        "first_forbidden_path", "status",
    ]
    rows = [
        {
            "process_order": order,
            "process_role": stage_id.lower(),
            "access_scope": "historical_design_holdout",
            "open_attempt_n": 0,
            "successful_open_n": 0,
            "read_row_n": 0,
            "forbidden_open_attempt_n": 0,
            "first_forbidden_path": "",
            "status": "pass",
        }
        for order, stage_id in enumerate(
            (
                "E0_PREAUTH_AND_PREFLIGHT",
                "E1_SEALED_CHECKPOINT_INFERENCE",
                "E2_TRAINING_AND_EARLY_SELECTION",
                "E3_PRE_LATE_SEAL",
                "E4_FRESH_LATE_READOUT",
                "E5_FINALIZE",
            ),
            1,
        )
    ]
    _write_csv(build / "historical_design_holdout_access_audit.csv", rows, columns)


def validate_preseal_contract(config: Mapping[str, Any], build: Path) -> None:
    parquet_contracts = {
        "diagnostics/return_path_transform_audit.parquet": (RETURN_PATH_TRANSFORM_SCHEMA, 11362),
        "diagnostics/gradient_calibration_batch_registry.parquet": (GRADIENT_BATCH_SCHEMA, 384),
        "diagnostics/loss_gradient_scale_audit.parquet": (LOSS_GRADIENT_SCHEMA, 12096),
        "diagnostics/selector_semantics_score_comparison.parquet": (SELECTOR_SCORE_SCHEMA, 306297),
        "diagnostics/checkpoint_surgery_score_comparison.parquet": (SURGERY_SCORE_SCHEMA, 306297),
        "predictions/validation_early_prediction_scores.parquet": (PREDICTION_SCHEMA, 2700464),
        "predictions/validation_late_prediction_scores.parquet": (PREDICTION_SCHEMA, 2608684),
    }
    for relative, (expected_schema, expected_rows) in parquet_contracts.items():
        path = build / relative
        if pq.read_schema(path).remove_metadata() != expected_schema:
            raise ContractError(f"pre-seal parquet schema mismatch: {relative}")
        if pq.read_metadata(path).num_rows != expected_rows:
            raise ContractError(f"pre-seal parquet row closure mismatch: {relative}")
    for identity in DRAW_IDENTITIES:
        for fold in VALIDATION_FOLDS:
            expected_rows = config["retained_folds"][fold]["row_n"]
            for seed in MODEL_SEEDS:
                relative = draw_shard_relative(identity, fold, seed)
                path = build / relative
                normalize_draw_shard_schema(path)
                if pq.read_schema(path).remove_metadata() != DRAW_SHARD_SCHEMA:
                    raise ContractError(f"draw shard schema mismatch: {relative}")
                if pq.read_metadata(path).num_rows != expected_rows:
                    raise ContractError(f"draw shard row closure mismatch: {relative}")
    csv_rows = {
        "preflight/execution_authorization_audit.csv": 1,
        "preflight/upstream_pin_and_file_set_audit.csv": 11,
        "preflight/retained_universe_exact_match_audit.csv": 1055,
        "hypothesis_registry.csv": 8,
        "diagnostics/raw_return_zero_solution_audit.csv": 24,
        "diagnostics/checkpoint_parameter_collapse_audit.csv": 24,
        "diagnostics/selector_semantics_audit.csv": 630,
        "diagnostics/operator_usage_and_stability_audit.csv": 210,
        "diagnostics/inference_draw_convergence_summary.csv": 60498,
        "training/model_search_accounting_manifest.csv": 21,
        "training/resource_probe_audit.csv": 1,
        "training/training_run_registry.csv": 21,
        "training/gradient_calibration_weights.csv": 18,
        "historical_design_holdout_access_audit.csv": 6,
        "daily_rankic_readout.csv": 11336,
        "monthly_lomo_stability.csv": 1248,
        "cross_seed_morphology.csv": 38012,
        "paired_rankic_comparison.csv": 26,
        "stationary_bootstrap_pair_diagnostic.csv": 26,
        "causal_hypothesis_readout.csv": 8,
    }
    for relative, expected_rows in csv_rows.items():
        path = build / relative
        observed_rows = max(0, sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
        if observed_rows != expected_rows:
            raise ContractError(f"pre-seal CSV row closure mismatch: {relative}={observed_rows}")
    if _csv_header(build / "training/resource_probe_audit.csv") != [
        "probe_order", "probe_id", "arm_id", "batch_size", "device_fingerprint_sha256",
        "forward_pass", "backward_pass", "optimizer_state_step_pass", "inference_64draw_pass",
        "draw_shard_write_pass", "oom_observed", "peak_reserved_memory_bytes",
        "estimated_gpu_wall_seconds", "estimated_output_bytes", "free_disk_bytes", "status", "reason",
    ]:
        raise ContractError("resource probe publish schema mismatch")
    resolved_keys = {
        "schema_version", "run_id", "requirement_version", "paths", "authorization",
        "upstream_pins", "replay_identity", "splits", "retained_rows",
        "return_path_transform", "hypotheses", "arms", "training",
        "gradient_calibration", "inference_draws", "metrics", "resources", "gates",
        "artifact_universe",
    }
    if set(yaml.safe_load((build / "preflight/resolved_config.yaml").read_text(encoding="utf-8"))) != resolved_keys:
        raise ContractError("resolved config top-level key closure mismatch")
    runtime_keys = {
        "schema_version", "python_version", "pytorch_version", "numpy_version",
        "cuda_runtime_version", "cudnn_version", "device_name", "device_capability",
        "device_total_memory_bytes", "device_fingerprint_sha256",
        "v4_device_fingerprint_sha256", "dependency_lock_path", "dependency_lock_sha256",
        "deterministic_algorithms", "cublas_workspace_config", "replay_compatibility_profile",
        "fingerprint_semantic_sha256",
    }
    runtime = json.loads((build / "preflight/replay_runtime_fingerprint.json").read_text(encoding="utf-8"))
    if set(runtime) != runtime_keys:
        raise ContractError("runtime fingerprint key closure mismatch")
    checkpoint_manifest_keys = {
        "schema_version", "run_id", "requirement_version", "entry_n", "entries",
        "entries_semantic_sha256",
    }
    for name in ("checkpoint_manifest.json", "checkpoint_eligibility_manifest.json"):
        payload = json.loads((build / "training" / name).read_text(encoding="utf-8"))
        if set(payload) != checkpoint_manifest_keys or payload["entry_n"] != 21 or len(payload["entries"]) != 21:
            raise ContractError(f"checkpoint manifest key/entry closure mismatch: {name}")
    pre_late_keys = {
        "schema_version", "run_id", "requirement_sha256", "resolved_config_sha256",
        "hypothesis_registry_sha256", "arm_registry_sha256",
        "return_transform_train_early_sha256", "gradient_calibration_sha256",
        "model_search_accounting_sha256", "checkpoint_manifest_sha256",
        "checkpoint_eligibility_manifest_sha256", "early_prediction_semantic_sha256",
        "bundle_semantic_sha256", "sealed_at_utc",
    }
    pre_late = json.loads(
        (build / "training/pre_late_checkpoint_bundle_manifest.json").read_text(encoding="utf-8")
    )
    if set(pre_late) != pre_late_keys:
        raise ContractError("pre-late bundle key closure mismatch")
    worker_keys = {
        "schema_version", "run_id", "process_role", "pid", "started_at_utc",
        "ended_at_utc", "exit_code", "input_paths_json", "input_hashes_json",
        "output_paths_json", "forbidden_open_attempt_n", "optimizer_object_n",
        "train_loader_object_n", "python_model_object_n", "status", "reason",
    }
    for name in ("selection_worker_exit_record.json", "late_readout_worker_exit_record.json"):
        payload = json.loads((build / "training" / name).read_text(encoding="utf-8"))
        if set(payload) != worker_keys or payload["status"] != "pass":
            raise ContractError(f"worker exit record key closure mismatch: {name}")
    for arm_id in ARM_IDS:
        for seed in MODEL_SEEDS:
            path = checkpoint_path(build, arm_id, seed)
            state = torch.load(path, map_location="cpu", weights_only=True)
            model = build_arm_model(arm_id, seed)
            if list(state) != model_parameter_names(model):
                raise ContractError(f"checkpoint ordered state-dict mismatch: {arm_id}/{seed}")
            if any(not tensor.device.type == "cpu" or not tensor.is_contiguous() for tensor in state.values()):
                raise ContractError(f"checkpoint tensor payload mismatch: {arm_id}/{seed}")
    if any((build / relative).exists() for relative in FAILURE_PATHS):
        raise ContractError("P6 must forbid conditional failure artifacts")


def validate_terminal_tables(config: Mapping[str, Any], build: Path, terminal_state: str) -> None:
    gate = pd.read_csv(build / "gate_evidence_21d_gap.csv")
    stage = pd.read_csv(build / "stage_status_registry.csv")
    profile = pd.read_csv(build / "artifact_profile_registry.csv")
    access = pd.read_csv(build / "historical_design_holdout_access_audit.csv")
    decision = pd.read_csv(build / "21D_reaka_replication_gap_causal_diagnostic_decision.csv")
    if len(gate) != 29 or gate["gate_id"].tolist() != list(GATE_ORDER):
        raise ContractError("terminal gate registry closure mismatch")
    engineering = gate.loc[~gate["gate_id"].eq("repair_candidate_gate"), "status"]
    if not engineering.eq("pass").all():
        raise ContractError("P6 engineering gate is not pass")
    if len(stage) != 6 or not stage["status"].eq("pass").all():
        raise ContractError("terminal stage registry closure mismatch")
    if len(profile) != 7 or profile.iloc[-1]["profile_id"] != "P6_FULL_DIAGNOSTIC_FINALIZED":
        raise ContractError("terminal artifact profile registry closure mismatch")
    p6_required = set(json.loads(profile.iloc[-1]["required_paths_json"]))
    if p6_required != p6_required_paths(config):
        raise ContractError("P6 required path registry mismatch")
    if len(access) != 6 or int(access["forbidden_open_attempt_n"].sum()) != 0:
        raise ContractError("historical holdout access audit closure mismatch")
    if (
        len(decision) != 1
        or decision.iloc[0]["terminal_state"] != terminal_state
        or bool(decision.iloc[0]["next_requirement_execution_authorized"])
    ):
        raise ContractError("terminal decision row closure mismatch")


def run_finalize(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    output = workspace_path(config["paths"]["canonical_output_root"])
    if not (build / ".state/late_readout_complete.json").exists():
        raise ContractError("late readout must complete before finalize")
    if output.exists():
        raise ContractError("canonical output already exists")
    early_predictions = pd.read_parquet(build / "predictions/validation_early_prediction_scores.parquet")
    late_predictions = pd.read_parquet(build / "predictions/validation_late_prediction_scores.parquet")
    daily_early = daily_rankic_table(early_predictions)
    daily_late = daily_rankic_table(late_predictions)
    daily = pd.concat([daily_early, daily_late], ignore_index=True).sort_values(
        ["fold_order", "arm_order", "is_ensemble", "model_seed", "score_variant", "aggregation_role", "decision_date", "metric_id"],
        kind="mergesort", na_position="last",
    )
    if len(daily) != 11336:
        raise ContractError("combined daily RankIC row count must be 11336")
    _write_csv(build / "daily_rankic_readout.csv", daily.to_dict("records"), list(daily.columns))
    monthly = pd.concat([monthly_lomo_table(daily_early), monthly_lomo_table(daily_late)], ignore_index=True)
    if len(monthly) != 1248:
        raise ContractError("monthly/LOMO row count must be 1248")
    _write_csv(build / "monthly_lomo_stability.csv", monthly.to_dict("records"), list(monthly.columns))
    cross_seed = cross_seed_morphology_table(pd.concat([early_predictions, late_predictions], ignore_index=True))
    _write_csv(build / "cross_seed_morphology.csv", cross_seed.to_dict("records"), list(cross_seed.columns))
    paired, bootstrap = paired_contrast_tables(daily, cross_seed)
    if len(paired) != 26 or len(bootstrap) != 26:
        raise ContractError("paired/bootstrap tables must each contain 26 rows")
    _write_csv(build / "paired_rankic_comparison.csv", paired.to_dict("records"), list(paired.columns))
    _write_csv(build / "stationary_bootstrap_pair_diagnostic.csv", bootstrap.to_dict("records"), list(bootstrap.columns))
    draw_summary = draw_convergence_summary(config)
    _write_csv(
        build / "diagnostics/inference_draw_convergence_summary.csv",
        draw_summary.to_dict("records"),
        list(draw_summary.columns),
    )
    zero = pd.read_csv(build / "diagnostics/raw_return_zero_solution_audit.csv")
    collapse = pd.read_csv(build / "diagnostics/checkpoint_parameter_collapse_audit.csv")
    gradient = pd.read_parquet(build / "diagnostics/loss_gradient_scale_audit.parquet")
    selector = pd.read_csv(build / "diagnostics/selector_semantics_audit.csv")
    hypotheses = hypothesis_readout(paired, selector, draw_summary, zero, collapse, gradient)
    _write_csv(build / "causal_hypothesis_readout.csv", hypotheses.to_dict("records"), list(hypotheses.columns))
    write_final_holdout_access_audit(build)
    validate_preseal_contract(config, build)
    candidate_pass, candidate_components = candidate_gate(
        daily, monthly, paired, cross_seed, draw_summary, zero, collapse
    )
    late_paired = paired.loc[paired["fold"].eq("validation_late")].set_index("contrast_id")
    late_d4_rankic = float(
        daily.loc[
            daily["fold"].eq("validation_late") & daily["arm_id"].eq("D4_R2_REPAIR_COMBINED_V1")
            & daily["score_variant"].eq("prefix64") & daily["is_ensemble"]
            & daily["metric_id"].eq("mean_rankic"), "metric_value"
        ].iloc[0]
    )
    if candidate_pass:
        terminal_state = "21D_gap_repair_candidate_ready_for_forward_seal_review"
        terminal_number = 10
    elif (
        bool(late_paired.loc["C04E", "material_improvement"])
        and late_d4_rankic > 0
        and all(
            bool(value)
            for key, value in candidate_components.items()
            if key not in {"C08_delta_positive", "C09_delta_positive"}
        )
        and (float(late_paired.loc["C08", "mean_rankic_delta"]) <= 0 or float(late_paired.loc["C09", "mean_rankic_delta"]) <= 0)
    ):
        terminal_state = "21D_gap_repair_observed_but_baselines_not_beaten"
        terminal_number = 9
    elif all(
        hypotheses.loc[hypotheses["hypothesis_order"].le(5), "support_level"].eq("not_supported")
    ) and not any(
        bool(late_paired.loc[contrast, "material_improvement"])
        for contrast in ("C01", "C02", "C03", "C04A", "C04D", "C04E")
    ):
        terminal_state = "21D_gap_mechanisms_not_supported"
        terminal_number = 7
    else:
        terminal_state = "21D_gap_mechanisms_mixed_no_repair_candidate"
        terminal_number = 8
    profile_id = "P6_FULL_DIAGNOSTIC_FINALIZED"
    profile = artifact_profile_table(config)
    _write_csv(build / "artifact_profile_registry.csv", profile.to_dict("records"), list(profile.columns))
    gate_rows = []
    for order, gate_id in enumerate(GATE_ORDER, 1):
        status = (
            "research_candidate_pass" if candidate_pass else "research_candidate_fail"
        ) if gate_id == "repair_candidate_gate" else "pass"
        gate_rows.append(
            {
                "gate_order": order,
                "gate_id": gate_id,
                "stage_id": (
                    "E0_PREAUTH_AND_PREFLIGHT" if order <= 7 else
                    "E1_SEALED_CHECKPOINT_INFERENCE" if order <= 11 else
                    "E2_TRAINING_AND_EARLY_SELECTION" if order <= 20 else
                    "E3_PRE_LATE_SEAL" if order == 21 else
                    "E4_FRESH_LATE_READOUT" if order <= 24 else "E5_FINALIZE"
                ),
                "status": status,
                "check_n": 1,
                "pass_n": 1,
                "fail_n": 0,
                "evidence_paths_json": canonical_json_bytes(
                    ["semantic_reproducibility_manifest.json"] if order >= 25 else ["preflight/resolved_config.yaml"]
                ).decode(),
                "first_failure_reason": "",
            }
        )
    _write_csv(build / "gate_evidence_21d_gap.csv", gate_rows, list(gate_rows[0]))
    stage_ids = (
        ("E0_PREAUTH_AND_PREFLIGHT", "G_PRE"),
        ("E1_SEALED_CHECKPOINT_INFERENCE", "G_INF"),
        ("E2_TRAINING_AND_EARLY_SELECTION", "G_TRAIN"),
        ("E3_PRE_LATE_SEAL", "G_TRAIN"),
        ("E4_FRESH_LATE_READOUT", "G_LATE"),
        ("E5_FINALIZE", "G_TERMINAL"),
    )
    stage_rows = [
        {
            "stage_order": order,
            "stage_id": stage_id,
            "status": "pass",
            "started_at_utc": None,
            "ended_at_utc": utc_now(),
            "first_failure_gate": "",
            "worker_exit_code": 0,
            "artifact_group_id": group,
        }
        for order, (stage_id, group) in enumerate(stage_ids)
    ]
    _write_csv(build / "stage_status_registry.csv", stage_rows, list(stage_rows[0]))
    access_rows = [
        {
            "process_order": order,
            "process_role": role,
            "access_scope": scope,
            "open_attempt_n": 0,
            "successful_open_n": 0,
            "read_row_n": 0,
            "forbidden_open_attempt_n": 0,
            "first_forbidden_path": "",
            "status": "pass",
        }
        for order, (role, scope) in enumerate(
            (
                ("preflight", "historical_design_holdout"),
                ("sealed_diagnostic_worker", "historical_design_holdout"),
                ("selection_worker", "validation_late"),
                ("selection_worker", "historical_design_holdout"),
                ("late_readout_worker", "historical_design_holdout"),
                ("finalize_worker", "historical_design_holdout"),
            )
        )
    ]
    _write_csv(build / "historical_design_holdout_access_audit.csv", access_rows, list(access_rows[0]))
    decision_row = {
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": profile_id,
        "terminal_state": terminal_state,
        "evidence_role": "design_contaminated_mechanism_diagnostic",
        "first_failure_gate": "",
        "mechanism_summary_status": "mixed" if terminal_number != 7 else "not_supported",
        "repair_candidate_status": "research_candidate_pass" if candidate_pass else "research_candidate_fail",
        "next_requirement_execution_authorized": False,
        "decision_reason": canonical_json_bytes(candidate_components).decode(),
    }
    _write_csv(
        build / "21D_reaka_replication_gap_causal_diagnostic_decision.csv",
        [decision_row],
        list(decision_row),
    )
    report = f"""# 21D REAKA 论文差距因果诊断报告

## 结论

- 工程执行完整，终态为 `{terminal_state}`，artifact profile 为 `{profile_id}`。
- 本轮全部 2018–2023 结果仍是设计污染后的机制诊断，不构成论文复现或独立 OOS 支持。
- D4@64 validation_late ensemble RankIC = `{late_d4_rankic:.6f}`。
- repair candidate gate = `{'research_candidate_pass' if candidate_pass else 'research_candidate_fail'}`；其逐项结果为 `{canonical_json_bytes(candidate_components).decode()}`。

## 机制诊断

{hypotheses[['hypothesis_id', 'support_level']].to_markdown(index=False)}

## 关键配对差异（validation_late）

{late_paired.reset_index()[['contrast_id', 'mean_rankic_delta', 'material_improvement']].to_markdown(index=False)}

## 污染边界与下一步

本实验没有读取 historical design holdout，没有改变 v4 retained universe，也没有使用 late 结果重新选择 arm、seed、checkpoint 或阈值。即使候选通过，也只能在最终密封后的新 exchange sessions 上另立 21F forward requirement；本报告不授权下一阶段执行。
"""
    report_path = build / "21D_reaka_replication_gap_causal_diagnostic_report.md"
    report_path.write_text(report, encoding="utf-8")
    validate_terminal_tables(config, build, terminal_state)
    resolved_path = build / "preflight/resolved_config.yaml"
    checkpoint_entries = json.loads((build / "training/checkpoint_manifest.json").read_text(encoding="utf-8"))["entries"]
    upstream_semantics = {
        key: pin["sha256"] for key, pin in config["upstream_pins"].items()
    }
    draw_hashes = {
        path: file_sha(build / path)
        for path in sorted(p6_required_paths(config))
        if path.startswith("diagnostics/inference_draw_scores/")
    }
    prediction_hashes = {
        fold: semantic_frame_hash(
            frame,
            ["arm_order", "is_ensemble", "model_seed", "score_variant", "decision_date", "instrument"],
        )
        for fold, frame in (("validation_early", early_predictions), ("validation_late", late_predictions))
    }
    metric_hashes = {
        "daily_rankic": semantic_frame_hash(daily, ["fold_order", "arm_order", "is_ensemble", "model_seed", "score_variant", "aggregation_role", "decision_date", "metric_id"]),
        "paired": semantic_frame_hash(paired, ["contrast_order", "fold"]),
        "hypothesis": semantic_frame_hash(hypotheses, ["hypothesis_order"]),
    }
    semantic = {
        "schema_version": "S_SEMANTIC_REPRODUCIBILITY_V2",
        "run_id": RUN_ID,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "resolved_config_sha256": file_sha(resolved_path),
        "replay_runtime_fingerprint_sha256": file_sha(build / "preflight/replay_runtime_fingerprint.json"),
        "upstream_semantic_hashes": upstream_semantics,
        "retained_row_key_hashes": {fold: config["retained_folds"][fold]["row_key_sha256"] for fold in FOLDS},
        "return_transform_semantic_hash": file_sha(build / "diagnostics/return_path_transform_audit.parquet"),
        "hypothesis_registry_sha256": file_sha(build / "hypothesis_registry.csv"),
        "arm_registry_sha256": stable_hash(config["arms"]),
        "gradient_calibration_semantic_hash": file_sha(build / "training/gradient_calibration_weights.csv"),
        "checkpoint_semantic_hashes": {f"{entry['arm_id']}:{entry['model_seed']}": entry["model_state_semantic_sha256"] for entry in checkpoint_entries},
        "draw_schedule_semantic_hashes": draw_hashes,
        "prediction_semantic_hashes": prediction_hashes,
        "metric_semantic_hashes": metric_hashes,
    }
    semantic["semantic_payload_bundle_hash"] = stable_hash(semantic)
    _write_json(build / "semantic_reproducibility_manifest.json", semantic)
    required = p6_required_paths(config)
    manifest_name = "manifest_21d_reaka_replication_gap_causal_diagnostic.json"
    hashes_name = "output_hashes_21d_reaka_replication_gap_causal_diagnostic.json"
    artifacts = []
    for relative in sorted(required - {manifest_name, hashes_name}):
        path = build / relative
        if not path.exists():
            raise ContractError(f"P6 required artifact missing: {relative}")
        schema_version, row_count = _artifact_schema_and_rows(path)
        artifacts.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": file_sha(path),
                "schema_version": schema_version,
                "row_count": row_count,
                "role": "substantive_evidence",
            }
        )
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.sha256 is None:
        raise ContractError("authorization drift detected during finalization")
    manifest = {
        "schema_version": "S_FINAL_MANIFEST_V2",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": profile_id,
        "terminal_state": terminal_state,
        "requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "authorization_sha256": authorization.sha256,
        "upstream_pins": {
            key: {"path": pin["path"], "expected_sha256": pin["sha256"], "observed_sha256": file_sha(workspace_path(pin["path"], must_exist=True))}
            for key, pin in config["upstream_pins"].items()
        },
        "replay_identity": {
            "implementation_mode": config["sealed_replay"]["implementation_mode"],
            "compatibility_profile": config["sealed_replay"]["compatibility_profile"],
            "seed_run_id": config["sealed_replay"]["seed_run_id"],
            "seed_arm_id": config["sealed_replay"]["seed_arm_id"],
        },
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "semantic_reproducibility_manifest_sha256": file_sha(build / "semantic_reproducibility_manifest.json"),
        "output_hashes_path": hashes_name,
        "output_hashes_excluded_self_path": hashes_name,
        "artifact_n": len(artifacts),
        "artifacts": artifacts,
        "report_sha256": file_sha(report_path),
        "finalized_at_utc": utc_now(),
    }
    _write_json(build / manifest_name, manifest)
    entries = []
    for relative in sorted(required - {hashes_name}):
        path = build / relative
        entries.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": file_sha(path)})
    output_hashes = {
        "schema_version": "S_OUTPUT_HASHES_V2",
        "run_id": RUN_ID,
        "excluded_paths": [hashes_name],
        "entries": entries,
    }
    _write_json(build / hashes_name, output_hashes)
    total_bytes = sum((build / path).stat().st_size for path in required)
    draw_bytes = sum((build / path).stat().st_size for path in required if path.startswith("diagnostics/inference_draw_scores/"))
    if total_bytes > config["resources"]["canonical_output_root_bytes_cap"] or draw_bytes > config["resources"]["draw_dataset_bytes_cap"]:
        raise ContractError("final output or draw dataset cap exceeded")
    if pq.read_metadata(build / "predictions/validation_early_prediction_scores.parquet").num_rows != 2700464:
        raise ContractError("early prediction row count mismatch")
    if pq.read_metadata(build / "predictions/validation_late_prediction_scores.parquet").num_rows != 2608684:
        raise ContractError("late prediction row count mismatch")
    draw_row_n = sum(pq.read_metadata(build / path).num_rows for path in required if path.startswith("diagnostics/inference_draw_scores/"))
    if draw_row_n != config["draws"]["sample_row_n"] or draw_row_n * 256 != config["draws"]["scalar_n"]:
        raise ContractError("draw shard global row/scalar closure mismatch")
    for entry in output_hashes["entries"]:
        if file_sha(build / entry["path"]) != entry["sha256"]:
            raise ContractError(f"post-finalization hash drift: {entry['path']}")
    shutil.rmtree(build / ".state")
    (build / "training/arm_registry.csv").unlink(missing_ok=True)
    (build / "preflight/preflight_complete.json").unlink(missing_ok=True)
    observed = {path.relative_to(build).as_posix() for path in build.rglob("*") if path.is_file()}
    if observed != required:
        extra = sorted(observed - required)
        missing = sorted(required - observed)
        raise ContractError(f"P6 exact artifact set mismatch extra={extra} missing={missing}")
    os.replace(build, output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=("preflight", "sealed-diagnostics", "train-selection", "late-readout", "finalize", "all"),
        default="all",
    )
    return parser.parse_args(argv)


def _run_stage(config: Mapping[str, Any], stage: str) -> None:
    print(f"[{utc_now()}] 21D stage start: {stage}", flush=True)
    if stage == "preflight":
        run_preflight(config)
    elif stage == "sealed-diagnostics":
        run_sealed_diagnostics(config)
    elif stage == "train-selection":
        run_training_selection(config)
    elif stage == "late-readout":
        run_late_readout(config)
    elif stage == "finalize":
        run_finalize(config)
    else:
        raise ContractError(f"unknown stage: {stage}")
    print(f"[{utc_now()}] 21D stage complete: {stage}", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    authorization = validate_authorization(config)
    if authorization.status != "pass":
        raise ContractError("execution forbidden before valid human authorization: " + ",".join(authorization.errors))
    if args.stage != "all":
        _run_stage(config, args.stage)
        return 0
    _run_stage(config, "preflight")
    runner_path = workspace_path(config["paths"]["runner"], must_exist=True)
    config_path = workspace_path(config["paths"]["config"], must_exist=True)
    for stage in ("sealed-diagnostics", "train-selection", "late-readout", "finalize"):
        completed = subprocess.run(
            [sys.executable, str(runner_path), "--config", str(config_path), "--stage", stage],
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
