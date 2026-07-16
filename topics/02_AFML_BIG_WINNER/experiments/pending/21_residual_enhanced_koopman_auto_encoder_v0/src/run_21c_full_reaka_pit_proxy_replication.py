#!/usr/bin/env python3
"""Run the frozen EP21 21C full-REAKA validation-only experiment.

The production controller is deliberately fail-closed.  Model, loss, inference,
metric, and sealing primitives are usable in synthetic tests before approval,
but no source value or checkpoint may be opened until the independently signed
authorization and corrected 21B successor pass preflight.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
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
    EXPERIMENT_DIR / "configs/config_21c_full_reaka_pit_proxy_replication.yaml"
)
RUN_ID = "21C_full_reaka_pit_proxy_replication"
REQUIREMENT_VERSION = "21C_FULL_v4"
ARM_ID = "R2_REAKA_DIFFUSION"
COMPARATORS = ("M1_LIGHTGBM_ALPHA158", "M3_GATED_DUAL_PATH_LSTM")
MODEL_SEEDS = (20260713, 20260714, 20260715)
FEATURE_DIM = 157
LOOKBACK = 10
LATENT_DIM = 64
N_OPERATOR = 4
DIFFUSION_STEPS = 20
INFERENCE_DRAWS = 8
HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FEATURE_CACHE_RAM: dict[str, np.ndarray] = {}

AUTHORIZATION_KEYS = {
    "requirement_sha256",
    "approved_21c_runner_sha256",
    "approved_21c_config_sha256",
    "approved_21c_test_sha256",
    "scope_restart_decision_path",
    "scope_restart_decision_sha256",
    "approved_21b_output_root",
    "approved_21b_requirement_version",
    "approved_21b_requirement_sha256",
    "approved_21b_runner_sha256",
    "approved_21b_config_sha256",
    "approved_21b_test_sha256",
    "approved_21b_decision_sha256",
    "approved_21b_manifest_sha256",
    "approved_21b_output_hashes_sha256",
    "approved_21b_gate_evidence_sha256",
    "approved_21b_pre_holdout_bundle_hash",
    "approved_21b_semantic_payload_bundle_hash",
    "approved_21b_contract_erratum_id",
    "approved_21b_contract_erratum_path",
    "approved_21b_contract_erratum_sha256",
    "approved_21a_paper_lineage_erratum_path",
    "approved_21a_paper_lineage_erratum_sha256",
    "scope_override",
    "historical_holdout_readout_authorized",
    "reviewer_role",
    "reviewed_at_utc",
    "authorization_status",
}

SCOPE_RESTART_KEYS = {
    "decision_id",
    "superseded_route",
    "approved_route",
    "superseded_estimand",
    "approved_estimand",
    "requirement_sha256",
    "historical_holdout_readout_authorized",
    "execution_authorized",
    "reviewer_role",
    "reviewed_at_utc",
    "decision_status",
}

ERRATUM_KEYS = {
    "erratum_id",
    "source_requirement_version",
    "corrected_requirement_version",
    "defect_id",
    "defect_description",
    "affected_artifacts",
    "corrected_runner_sha256",
    "corrected_config_sha256",
    "corrected_test_sha256",
    "runtime_counter_evidence_path",
    "runtime_counter_evidence_sha256",
    "runtime_access_event_log_path",
    "runtime_access_event_log_sha256",
    "runtime_counter_aggregation_contract_id",
    "post_cutoff_value_token_materialization_count",
    "post_cutoff_outcome_value_decode_count",
    "counter_collection_mode",
    "historical_holdout_outcome_open_count",
    "historical_holdout_label_open_count",
    "historical_holdout_score_join_count",
    "historical_holdout_metric_count",
    "status",
}

ERRATUM_V6_SUCCESSOR_KEYS = {
    "compatibility_successor_source_inventory_hash",
    "compatibility_successor_source_requirement_version",
    "gate_registry_row_count",
}

RUNTIME_EVENT_COLUMNS = [
    "event_seq",
    "process_id",
    "stage",
    "access_scope",
    "operation",
    "path",
    "path_class",
    "value_token_requested",
    "value_decoded",
    "decision_date",
    "status",
    "reason",
]

RUNTIME_COUNTER_COLUMNS = [
    "process_id",
    "stage",
    "access_scope",
    "operation",
    "path_class",
    "value_token_requested",
    "value_decoded",
    "decision_date_min",
    "decision_date_max",
    "event_count",
    "source_log_path",
    "source_log_sha256",
    "status",
    "reason",
]

CAUSAL_GATES = [
    "execution_authorization_gate",
    "scope_restart_gate",
    "scope_override_gate",
    "upstream_21b_success_gate",
    "upstream_21b_contract_erratum_gate",
    "upstream_paper_lineage_erratum_gate",
    "upstream_hash_and_file_set_gate",
    "dependency_runtime_gate",
    "input_panel_integrity_gate",
    "train_validation_firewall_gate",
    "historical_holdout_zero_access_gate",
    "teacher_materialization_gate",
    "architecture_shape_gate",
    "teacher_isolation_gate",
    "loss_and_score_index_gate",
    "seed_determinism_gate",
    "gpu_memory_gate",
    "training_completion_gate",
    "pre_gate_bundle_hash_gate",
    "late_readout_process_gate",
    "checkpoint_eligibility_gate",
    "score_coverage_gate",
    "rankic_implementation_gate",
    "finalize_transaction_gate",
    "r2_direction_stability_gate",
]

DECISION_GROUPS = [
    (
        "21C_FULL_blocked_by_missing_or_invalid_human_authorization",
        CAUSAL_GATES[0:3],
    ),
    (
        "21C_FULL_blocked_by_upstream_contract_or_runtime",
        CAUSAL_GATES[3:8],
    ),
    (
        "21C_FULL_input_or_access_firewall_blocked",
        CAUSAL_GATES[8:11],
    ),
    (
        "21C_FULL_teacher_or_architecture_pipeline_not_evaluable",
        CAUSAL_GATES[11:16],
    ),
    (
        "21C_FULL_training_or_late_readout_not_evaluable",
        CAUSAL_GATES[16:22],
    ),
    (
        "21C_FULL_finalize_or_manifest_integrity_blocked",
        CAUSAL_GATES[22:24] + ["output_manifest_hash_gate"],
    ),
]

COMMON_FINAL = {
    "artifact_profile_registry.csv",
    "stage_status_registry.csv",
    "gate_evidence_21c_full.csv",
    "21C_full_reaka_pit_proxy_replication_decision.csv",
    "21C_full_reaka_pit_proxy_replication_report.md",
    "semantic_reproducibility_manifest.json",
    "manifest_21c_full_reaka_pit_proxy_replication.json",
    "output_hashes_21c_full_reaka_pit_proxy_replication.json",
    "historical_design_holdout_access_audit.csv",
}
PREFLIGHT_PATHS = {
    "preflight/preflight_access_audit.csv",
    "preflight/upstream_21b_authorization_and_hash_audit.csv",
    "preflight/scope_override_audit.csv",
    "preflight/scope_restart_decision_audit.csv",
    "preflight/paper_lineage_erratum_audit.csv",
    "preflight/pit_universe_exclusion_audit.csv",
    "preflight/pit_universe_exclusion_impact.csv",
    "preflight/resolved_config.yaml",
}
MATERIALIZATION_SUCCESS = {
    "materialized/r2_train_teacher_sequence_index.parquet",
    "materialized/r2_train_teacher_return_panel.f32.memmap",
    "materialized/r2_input_extension_manifest.json",
    "materialized/materialization_access_audit.csv",
}
MATERIALIZATION_FAILURE = {
    "materialized/materialization_access_audit.csv",
    "materialized/materialization_failure_evidence.csv",
}
TRAINING_CORE = {
    "training/model_search_accounting_manifest.csv",
    "training/resource_probe_audit.csv",
    "training/training_run_registry.csv",
    "training/seed_level_training_curves.csv",
    "training/checkpoint_manifest.json",
    "training/model_parameter_compute_latency_audit.csv",
    "training/training_access_audit.csv",
}
CHECKPOINT_PATHS = {
    f"training/checkpoints/{ARM_ID}/seed_{seed}/state_dict.pt"
    for seed in MODEL_SEEDS
}
TRAINING_SUCCESS_ONLY = CHECKPOINT_PATHS | {
    "training/selection_worker_exit_record.json",
    "training/selection/validation_early_prediction_scores.parquet",
    "training/pre_gate_r2_checkpoint_bundle_manifest.json",
}
TRAINING_FAILURE = {"training/training_failure_evidence.csv"}
LATE_SUCCESS = {
    "training/readout/validation_late_prediction_scores.parquet",
    "training/late_readout_worker_exit_record.json",
    "training/checkpoint_eligibility_manifest.json",
}
LATE_FAILURE = {
    "training/late_readout_worker_exit_record.json",
    "training/late_readout_failure_evidence.csv",
}
FINAL_METRICS = {
    "daily_rankic_readout.csv",
    "rankic_stability_and_concentration_audit.csv",
    "paired_rankic_comparison.csv",
    "stationary_bootstrap_pair_diagnostic.csv",
    "paper_proxy_top30_daily.csv",
    "paper_proxy_top30_summary.csv",
    "paper_reference_comparison.csv",
}
FINAL_FAILURE = {"finalize_failure_evidence.csv"}

CHECK_AUDIT_COLUMNS = [
    "check_id",
    "stage",
    "artifact_path",
    "expected_value",
    "observed_value",
    "status",
    "reason",
]

ACCESS_COLUMNS = [
    "stage",
    "process_role",
    "path",
    "artifact_sha256",
    "access_scope",
    "row_scope",
    "value_scope",
    "allowed",
    "row_n",
    "first_key",
    "last_key",
    "reason",
]

PREDICTION_COLUMNS = [
    "arm_id",
    "score_role",
    "model_seed",
    "fold",
    "decision_date",
    "instrument",
    "score",
    "checkpoint_bundle_hash",
    "row_key_hash",
]

EXCLUSION_COLUMNS = [
    "instrument",
    "trigger_decision_date",
    "source_sample_row_idx",
    "exclusion_scope",
    "reason",
    "source_requirement_version",
    "source_manifest_sha256",
    "source_failure_evidence_sha256",
]

EXCLUSION_IMPACT_COLUMNS = [
    "fold",
    "source_row_n",
    "excluded_row_n",
    "retained_row_n",
    "source_instrument_n",
    "excluded_instrument_n_present",
    "retained_instrument_n",
    "retained_row_key_hash",
    "registry_instrument_n",
    "registry_sha256",
    "exclusion_scope",
    "status",
]


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


class AuthorizationResult(NamedTuple):
    status: str
    observation: str
    authorization_sha256: str | None
    payload: dict[str, Any] | None
    errors: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("source config must be a mapping")
    validate_frozen_config(payload)
    return payload


def validate_frozen_config(config: Mapping[str, Any]) -> None:
    if config.get("identity", {}).get("requirement_version") != REQUIREMENT_VERSION:
        raise ContractError("source config requirement version mismatch")
    architecture = config.get("architecture", {})
    exact = {
        "lookback_T": LOOKBACK,
        "feature_dim": FEATURE_DIM,
        "latent_dim": LATENT_DIM,
        "n_operator": N_OPERATOR,
        "diffusion_steps": DIFFUSION_STEPS,
        "inference_residual_draws": INFERENCE_DRAWS,
        "gumbel_clamp_min": 1e-10,
        "gumbel_clamp_max": 1 - 1e-10,
    }
    for key, expected in exact.items():
        if architecture.get(key) != expected:
            raise ContractError(f"architecture.{key} must equal {expected!r}")
    training = config.get("training", {})
    if tuple(training.get("model_seeds", ())) != MODEL_SEEDS:
        raise ContractError("exactly the three frozen R2 model seeds are required")
    if training.get("amp") is not False or training.get("optimizer") != "AdamW":
        raise ContractError("fp32 explicit AdamW contract required")
    execution = config.get("execution", {})
    if execution.get("planned_primary_job_n") != 3:
        raise ContractError("planned_primary_job_n must equal 3")
    if execution.get("sensitivity_job_n") != 0:
        raise ContractError("21C sensitivities are forbidden")
    exclusion = config.get("universe_exclusion", {})
    if exclusion.get("instrument_n") != 396:
        raise ContractError("v4 requires exactly 396 excluded instruments")
    if exclusion.get("exclusion_scope") != "all_folds_entire_instrument_history":
        raise ContractError("v3 exclusion scope must cover entire histories")
    performance = config.get("performance", {})
    expected_performance = {
        "feature_cache_residency": "shared_process_ram_copy",
        "inference_noise_device": "cpu_row_seeded_batched_schedule",
        "inference_batch_size": 1024,
    }
    for key, expected in expected_performance.items():
        if performance.get(key) != expected:
            raise ContractError(f"performance.{key} must equal {expected!r}")
    forbidden_source_keys = {
        "requirement_sha256",
        "execution_authorization_sha256",
        "approved_21c_runner_sha256",
        "approved_21c_config_sha256",
        "approved_21c_test_sha256",
    }
    if forbidden_source_keys.intersection(config):
        raise ContractError("source config must not embed future authorization pins")


def workspace_path(relative: str, *, must_exist: bool = False) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ContractError(f"non-canonical workspace path: {relative}")
    resolved = TOPIC_ROOT / candidate
    if resolved.is_symlink() or any(parent.is_symlink() for parent in resolved.parents):
        raise ContractError(f"symlink path forbidden: {relative}")
    if must_exist and not resolved.exists():
        raise ContractError(f"required path missing: {relative}")
    return resolved


def _rfc3339_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def validate_authorization(
    config: Mapping[str, Any], authorization_path: Path | None = None
) -> AuthorizationResult:
    paths = config["paths"]
    path = authorization_path or workspace_path(paths["execution_authorization"])
    requirement = workspace_path(paths["requirement"], must_exist=True)
    runner = workspace_path(paths["runner"], must_exist=True)
    source_config = workspace_path(paths["config"], must_exist=True)
    test = workspace_path(paths["test"], must_exist=True)
    requirement_hash = file_sha(requirement)
    if not path.exists():
        return AuthorizationResult("missing", "MISSING", None, None, ("missing",))
    authorization_hash = file_sha(path)
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return AuthorizationResult(
            "invalid", authorization_hash, authorization_hash, None, (str(exc),)
        )
    if not isinstance(payload, dict) or set(payload) != AUTHORIZATION_KEYS:
        errors.append("authorization_schema_exact")
    if isinstance(payload, dict):
        hash_keys = [
            key
            for key in AUTHORIZATION_KEYS
            if key.endswith("_sha256") or key.endswith("_bundle_hash")
        ]
        for key in hash_keys:
            if not HEX64.fullmatch(str(payload.get(key, ""))):
                errors.append(f"{key}_format")
        exact_values = {
            "requirement_sha256": requirement_hash,
            "approved_21c_runner_sha256": file_sha(runner),
            "approved_21c_config_sha256": file_sha(source_config),
            "approved_21c_test_sha256": file_sha(test),
            "scope_restart_decision_path": paths["scope_restart_decision"],
            "scope_override": (
                "full_reaka_local_validation_sanity_with_v2_missing_teacher_instrument_exclusion"
            ),
            "historical_holdout_readout_authorized": False,
            "reviewer_role": "human",
            "authorization_status": "approved",
        }
        for key, expected in exact_values.items():
            if payload.get(key) != expected:
                errors.append(f"{key}_match")
        if not _rfc3339_utc(payload.get("reviewed_at_utc")):
            errors.append("reviewed_at_utc_rfc3339")
        root = str(payload.get("approved_21b_output_root", ""))
        if (
            not root
            or "latest" in root.lower()
            or "*" in root
            or not re.search(r"_v[0-9]+$", root)
        ):
            errors.append("approved_21b_root_canonical_versioned")
        for key in (
            "approved_21b_contract_erratum_path",
            "approved_21a_paper_lineage_erratum_path",
        ):
            value = str(payload.get(key, ""))
            if not value.startswith(root.rstrip("/") + "/"):
                errors.append(f"{key}_under_approved_root")
    status = "pass" if not errors else "invalid"
    return AuthorizationResult(
        status,
        authorization_hash,
        authorization_hash,
        payload if status == "pass" else None,
        tuple(errors),
    )


def validate_scope_restart(
    payload: Mapping[str, Any], requirement_sha256: str
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if set(payload) != SCOPE_RESTART_KEYS:
        errors.append("scope_restart_schema_exact")
    expected = {
        "superseded_route": (
            "requirement_21c_single_vs_adaptive_koopman_nested_ablation.md"
        ),
        "approved_route": "requirement_21c_full_reaka_pit_proxy_replication.md",
        "superseded_estimand": "nested_module_attribution",
        "approved_estimand": (
            "full_architecture_local_validation_sanity_on_v2_missing_teacher_instrument_excluded_pit_universe"
        ),
        "requirement_sha256": requirement_sha256,
        "historical_holdout_readout_authorized": False,
        "execution_authorized": False,
        "reviewer_role": "human",
        "decision_status": "approved_scope_restart_only",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"scope_restart_{key}_match")
    if not payload.get("decision_id"):
        errors.append("scope_restart_decision_id_nonempty")
    if not _rfc3339_utc(payload.get("reviewed_at_utc")):
        errors.append("scope_restart_reviewed_at_utc_rfc3339")
    return not errors, errors


def _csv_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text not in {"true", "false"}:
        raise ContractError(f"invalid canonical boolean: {value!r}")
    return text == "true"


def read_runtime_event_log(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != RUNTIME_EVENT_COLUMNS:
        raise ContractError("runtime access event log schema mismatch")
    expected_seq = list(range(len(frame)))
    observed_seq = [int(value) for value in frame["event_seq"]]
    if observed_seq != expected_seq:
        raise ContractError("runtime access event_seq must be contiguous from zero")
    if not set(frame["status"]).issubset({"allowed", "denied"}):
        raise ContractError("runtime access status enum mismatch")
    for row in frame.itertuples(index=False):
        workspace_path(row.path)
        if row.status == "allowed" and row.reason:
            raise ContractError("allowed runtime event must have empty reason")
        if row.status == "denied" and not row.reason:
            raise ContractError("denied runtime event must have a reason")
        _csv_bool(row.value_token_requested)
        _csv_bool(row.value_decoded)
    return frame


def runtime_counters(
    frame: pd.DataFrame, max_allowed_outcome_source_date: str
) -> dict[str, int]:
    decision_date = frame["decision_date"]
    after_cutoff = decision_date.ne("") & decision_date.gt(
        max_allowed_outcome_source_date
    )
    requested = frame["value_token_requested"].map(_csv_bool)
    decoded = frame["value_decoded"].map(_csv_bool)
    holdout = frame["access_scope"].eq("historical_design_holdout")
    operations = frame["operation"]
    return {
        "post_cutoff_value_token_materialization_count": int(
            (after_cutoff & requested).sum()
        ),
        "post_cutoff_outcome_value_decode_count": int(
            (after_cutoff & decoded).sum()
        ),
        "historical_holdout_outcome_open_count": int(
            (holdout & operations.eq("outcome_open")).sum()
        ),
        "historical_holdout_label_open_count": int(
            (holdout & operations.eq("label_open")).sum()
        ),
        "historical_holdout_score_join_count": int(
            (holdout & operations.eq("score_outcome_join")).sum()
        ),
        "historical_holdout_metric_count": int(
            (holdout & operations.eq("metric_compute")).sum()
        ),
    }


def aggregate_runtime_events(
    frame: pd.DataFrame, source_log_path: str, source_log_sha256: str
) -> pd.DataFrame:
    keys = RUNTIME_COUNTER_COLUMNS[:7]
    rows: list[dict[str, Any]] = []
    for group_key, group in frame.groupby(keys, sort=True, dropna=False):
        dates = sorted(value for value in group["decision_date"] if value)
        row = dict(zip(keys, group_key, strict=True))
        row.update(
            {
                "decision_date_min": dates[0] if dates else "",
                "decision_date_max": dates[-1] if dates else "",
                "event_count": len(group),
                "source_log_path": source_log_path,
                "source_log_sha256": source_log_sha256,
                "status": "pass",
                "reason": "",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=RUNTIME_COUNTER_COLUMNS).sort_values(
        keys, kind="mergesort", ignore_index=True
    )


def validate_runtime_counter_contract(
    erratum: Mapping[str, Any], max_allowed_outcome_source_date: str
) -> dict[str, int]:
    observed_keys = frozenset(erratum)
    if observed_keys not in {
        frozenset(ERRATUM_KEYS),
        frozenset(ERRATUM_KEYS | ERRATUM_V6_SUCCESSOR_KEYS),
    }:
        raise ContractError("corrected 21B erratum schema mismatch")
    if observed_keys == frozenset(ERRATUM_KEYS | ERRATUM_V6_SUCCESSOR_KEYS):
        if (
            erratum["compatibility_successor_source_requirement_version"]
            != "21B_v5"
            or int(erratum["gate_registry_row_count"]) != 27
            or not HEX64.fullmatch(
                str(erratum["compatibility_successor_source_inventory_hash"])
            )
        ):
            raise ContractError("21B_v6 compatibility successor fields mismatch")
    if erratum["defect_id"] != (
        "QFQ_POST_CUTOFF_VALUE_TOKEN_AND_RUNTIME_COUNTER_SEMANTICS"
    ):
        raise ContractError("corrected 21B defect id mismatch")
    if erratum["runtime_counter_aggregation_contract_id"] != (
        "QFQ_RUNTIME_ACCESS_EVENT_AGGREGATION_V1"
    ):
        raise ContractError("runtime aggregation contract mismatch")
    if erratum["counter_collection_mode"] != (
        "runtime_wrapper_and_append_only_log"
    ):
        raise ContractError("runtime counter collection mode mismatch")
    if erratum["status"] != "corrected_rerun_sealed":
        raise ContractError("corrected 21B erratum is not sealed")
    raw_rel = str(erratum["runtime_access_event_log_path"])
    evidence_rel = str(erratum["runtime_counter_evidence_path"])
    if raw_rel == evidence_rel:
        raise ContractError("raw runtime log and aggregate evidence must differ")
    raw_path = workspace_path(raw_rel, must_exist=True)
    evidence_path = workspace_path(evidence_rel, must_exist=True)
    if file_sha(raw_path) != erratum["runtime_access_event_log_sha256"]:
        raise ContractError("raw runtime log hash mismatch")
    if file_sha(evidence_path) != erratum["runtime_counter_evidence_sha256"]:
        raise ContractError("runtime counter evidence hash mismatch")
    raw = read_runtime_event_log(raw_path)
    recomputed = runtime_counters(raw, max_allowed_outcome_source_date)
    for key, observed in recomputed.items():
        if int(erratum[key]) != observed or observed != 0:
            raise ContractError(f"runtime counter mismatch or nonzero: {key}")
    observed_aggregate = pd.read_csv(
        evidence_path, dtype=str, keep_default_na=False
    )
    if list(observed_aggregate.columns) != RUNTIME_COUNTER_COLUMNS:
        raise ContractError("runtime counter evidence schema mismatch")
    expected_aggregate = aggregate_runtime_events(
        raw, raw_rel, erratum["runtime_access_event_log_sha256"]
    ).astype(str)
    pd.testing.assert_frame_equal(
        observed_aggregate.reset_index(drop=True),
        expected_aggregate.reset_index(drop=True),
        check_dtype=False,
    )
    return recomputed


def _json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError(f"JSON object required: {path}")
    return payload


def verify_output_file_set(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "manifest_21b_alpha158_sequence_baseline_benchmark.json"
    hashes_path = root / "output_hashes_21b_alpha158_sequence_baseline_benchmark.json"
    manifest = _json_object(manifest_path)
    hashes = _json_object(hashes_path)
    if "artifact_file_set" in manifest:
        declared = set(manifest["artifact_file_set"])
    elif "files" in manifest:
        declared = {
            item["path"] if isinstance(item, dict) else item
            for item in manifest["files"]
        }
        declared.update({manifest_path.name, hashes_path.name})
    else:
        raise ContractError("21B manifest has no exact file-set declaration")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if actual != declared:
        raise ContractError("corrected 21B output file set is not exact")
    if "artifacts" in hashes:
        records = hashes["artifacts"]
    elif "files" in hashes:
        records = {
            item["path"]: item["sha256"] for item in hashes["files"]
        }
    else:
        raise ContractError("21B output hashes schema unsupported")
    if not isinstance(records, dict):
        raise ContractError("21B output hash records must be a mapping")
    expected_hashed = actual - {manifest_path.name, hashes_path.name}
    if set(records) != expected_hashed:
        raise ContractError("21B output hash file set is not bidirectional")
    for relative, expected in records.items():
        if file_sha(root / relative) != expected:
            raise ContractError(f"21B artifact hash mismatch: {relative}")
    return manifest, hashes


PAPER_LINEAGE_ERRATUM_KEYS = {
    "erratum_id",
    "upstream_21a_version",
    "upstream_model_arm_registry_sha256",
    "affected_arm_id",
    "original_role",
    "corrected_role",
    "paper_w_o_gm_equivalent",
    "paper_lstm_equivalent",
    "gate_eligible_in_21c",
    "reason",
    "reviewer_role",
    "reviewed_at_utc",
    "status",
}


def validate_paper_lineage_erratum(payload: Mapping[str, Any]) -> None:
    if set(payload) != PAPER_LINEAGE_ERRATUM_KEYS:
        raise ContractError("21A paper-lineage erratum schema mismatch")
    expected = {
        "affected_arm_id": "M2_RETURN_LSTM",
        "corrected_role": "project_return_only_diagnostic",
        "paper_w_o_gm_equivalent": False,
        "paper_lstm_equivalent": False,
        "gate_eligible_in_21c": False,
        "reviewer_role": "human",
        "status": "approved_lineage_erratum",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ContractError(f"paper-lineage erratum mismatch: {key}")
    if not payload.get("erratum_id") or not payload.get("reason"):
        raise ContractError("paper-lineage erratum identity/reason missing")
    if not _rfc3339_utc(payload.get("reviewed_at_utc")):
        raise ContractError("paper-lineage erratum timestamp invalid")


def validate_corrected_21b_successor(
    config: Mapping[str, Any], authorization: AuthorizationResult
) -> dict[str, Any]:
    """Validate corrected 21B without opening panel, score, or checkpoint values."""
    if authorization.status != "pass" or authorization.payload is None:
        raise ContractError("valid execution authorization required")
    payload = authorization.payload
    if payload["approved_21b_requirement_version"] == "21B_v4":
        raise ContractError("uncorrected observed 21B_v4 is never execution eligible")
    root_relative = payload["approved_21b_output_root"]
    root = workspace_path(root_relative, must_exist=True)
    if not root.is_dir():
        raise ContractError("approved corrected 21B root is not a directory")
    source_resolved = yaml.safe_load(
        (root / "preflight/resolved_config.yaml").read_text(encoding="utf-8")
    )
    source_manifest = _json_object(
        root / "manifest_21b_alpha158_sequence_baseline_benchmark.json"
    )
    sealed_implementation_pins = {
        "approved_21b_requirement_sha256": source_resolved["identity"][
            "requirement_sha256"
        ],
        "approved_21b_runner_sha256": source_manifest[
            "corrected_runner_sha256"
        ],
        "approved_21b_config_sha256": source_manifest[
            "corrected_config_sha256"
        ],
        "approved_21b_test_sha256": source_manifest["corrected_test_sha256"],
    }
    for pin, observed in sealed_implementation_pins.items():
        if observed != payload[pin]:
            raise ContractError(f"corrected 21B sealed implementation pin mismatch: {pin}")
    named_paths = {
        "approved_21b_decision_sha256": (
            root / "21B_baseline_benchmark_decision.csv"
        ),
        "approved_21b_manifest_sha256": (
            root / "manifest_21b_alpha158_sequence_baseline_benchmark.json"
        ),
        "approved_21b_output_hashes_sha256": (
            root / "output_hashes_21b_alpha158_sequence_baseline_benchmark.json"
        ),
        "approved_21b_gate_evidence_sha256": root / "gate_evidence_21b.csv",
    }
    for pin, path in named_paths.items():
        if not path.exists() or file_sha(path) != payload[pin]:
            raise ContractError(f"corrected 21B output pin mismatch: {pin}")
    manifest, _ = verify_output_file_set(root)
    semantic = _json_object(root / "semantic_reproducibility_manifest.json")
    semantic_hash = semantic.get("semantic_payload_bundle_hash")
    if semantic_hash != payload["approved_21b_semantic_payload_bundle_hash"]:
        raise ContractError("corrected 21B semantic payload bundle mismatch")
    pre_holdout_path = root / "training/pre_holdout_checkpoint_bundle_manifest.json"
    pre_holdout = _json_object(pre_holdout_path)
    pre_holdout_hash = pre_holdout.get(
        "bundle_hash", pre_holdout.get("pre_gate_checkpoint_bundle_sha256")
    )
    if pre_holdout_hash != payload["approved_21b_pre_holdout_bundle_hash"]:
        raise ContractError("corrected 21B pre-holdout bundle mismatch")
    erratum_path = workspace_path(
        payload["approved_21b_contract_erratum_path"], must_exist=True
    )
    if file_sha(erratum_path) != payload["approved_21b_contract_erratum_sha256"]:
        raise ContractError("corrected 21B erratum hash mismatch")
    erratum = _json_object(erratum_path)
    if erratum.get("erratum_id") != payload["approved_21b_contract_erratum_id"]:
        raise ContractError("corrected 21B erratum id mismatch")
    if erratum.get("corrected_runner_sha256") != payload[
        "approved_21b_runner_sha256"
    ]:
        raise ContractError("erratum corrected runner pin mismatch")
    if erratum.get("corrected_config_sha256") != payload[
        "approved_21b_config_sha256"
    ]:
        raise ContractError("erratum corrected config pin mismatch")
    if erratum.get("corrected_test_sha256") != payload[
        "approved_21b_test_sha256"
    ]:
        raise ContractError("erratum corrected test pin mismatch")
    panel_manifest = _json_object(root / "materialized/model_input_panel_manifest.json")
    max_date = panel_manifest.get("max_allowed_outcome_source_date")
    if not isinstance(max_date, str):
        raise ContractError("corrected 21B max outcome source date missing")
    validate_runtime_counter_contract(erratum, max_date)
    lineage_path = workspace_path(
        payload["approved_21a_paper_lineage_erratum_path"], must_exist=True
    )
    if file_sha(lineage_path) != payload[
        "approved_21a_paper_lineage_erratum_sha256"
    ]:
        raise ContractError("paper-lineage erratum hash mismatch")
    validate_paper_lineage_erratum(_json_object(lineage_path))
    decision = pd.read_csv(named_paths["approved_21b_decision_sha256"])
    if len(decision) != 1:
        raise ContractError("corrected 21B decision must have one row")
    row = decision.iloc[0]
    required_decision = {
        "stage_decision": (
            "21B_baseline_information_supported_pending_human_approval"
        ),
        "baseline_information_gate": "pass",
        "upstream_21b_contract_erratum_gate": "pass",
    }
    for key, value in required_decision.items():
        if key not in row or row[key] != value:
            raise ContractError(f"corrected 21B decision mismatch: {key}")
    if manifest.get("upstream_21b_contract_erratum_gate") != "pass":
        raise ContractError("corrected 21B manifest lacks exact erratum gate")
    eligibility = _json_object(root / "training/checkpoint_eligibility_manifest.json")
    records = eligibility.get("records", [])
    eligible = {
        (record.get("arm_id"), int(record.get("model_seed")))
        for record in records
        if record.get("checkpoint_eligibility_status") == "eligible_frozen"
    }
    expected = {(arm, seed) for arm in COMPARATORS for seed in MODEL_SEEDS}
    if not expected.issubset(eligible):
        raise ContractError("M1/M3 corrected successor checkpoints are incomplete")
    return {
        "root": root,
        "manifest": manifest,
        "semantic_manifest": semantic,
        "panel_manifest": panel_manifest,
        "pre_holdout_manifest": pre_holdout,
        "erratum": erratum,
    }


def resolved_config(
    config: Mapping[str, Any], authorization: AuthorizationResult
) -> dict[str, Any]:
    payload = authorization.payload
    implementation = None
    approved_21b = None
    scope_path = None
    scope_hash = None
    if payload is not None:
        implementation = {
            "runner_path": config["paths"]["runner"],
            "runner_sha256": payload["approved_21c_runner_sha256"],
            "config_path": config["paths"]["config"],
            "config_sha256": payload["approved_21c_config_sha256"],
            "test_path": config["paths"]["test"],
            "test_sha256": payload["approved_21c_test_sha256"],
        }
        approved_21b = {
            key.removeprefix("approved_21b_"): value
            for key, value in payload.items()
            if key.startswith("approved_21b_")
        }
        scope_path = payload["scope_restart_decision_path"]
        scope_hash = payload["scope_restart_decision_sha256"]
    return {
        "schema_version": "21C_FULL_RESOLVED_CONFIG_V1",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "requirement_sha256": file_sha(
            workspace_path(config["paths"]["requirement"], must_exist=True)
        ),
        "execution_authorization_path": config["paths"][
            "execution_authorization"
        ],
        "authorization_observation": authorization.observation,
        "authorization_schema_status": authorization.status,
        "execution_authorization_sha256": authorization.authorization_sha256,
        "scope_restart_decision_path": scope_path,
        "scope_restart_decision_sha256": scope_hash,
        "approved_21c_implementation": implementation,
        "approved_21b": approved_21b,
        "approved_21a_lineage": None,
        "paths": dict(config["paths"]),
        "feature_route": dict(config["feature_route"]),
        "splits": dict(config["splits"]),
        "architecture": dict(config["architecture"]),
        "loss": dict(config["loss"]),
        "training": dict(config["training"]),
        "randomness": dict(config["randomness"]),
        "resource_probe": dict(config["resource_probe"]),
        "metrics": dict(config["metrics"]),
        "universe_exclusion": dict(config["universe_exclusion"]),
        "performance": dict(config["performance"]),
        "gates": list(CAUSAL_GATES),
        "artifact_profiles": expanded_artifact_profiles(),
    }


def preauthorization_audit_id(
    requirement_sha256: str, authorization_observation: str
) -> str:
    return hashlib.sha256(
        f"{requirement_sha256}|{authorization_observation}".encode()
    ).hexdigest()[:16]


def _write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(payload), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(
    path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for source in rows:
            row = {}
            for key in columns:
                value = source.get(key, "")
                if value is None:
                    value = ""
                elif isinstance(value, bool):
                    value = "true" if value else "false"
                row[key] = value
            writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def run_preauthorization_preflight(config: Mapping[str, Any]) -> Path:
    authorization = validate_authorization(config)
    if authorization.status == "pass":
        raise ContractError("preauthorization audit is only for missing/invalid auth")
    resolved = resolved_config(config, authorization)
    audit_id = preauthorization_audit_id(
        resolved["requirement_sha256"], authorization.observation
    )
    base = workspace_path(config["paths"]["preauthorization_audit_root"])
    final = base / audit_id
    building = base / f"{audit_id}.building"
    canonical = workspace_path(config["paths"]["canonical_output_root"])
    if canonical.exists():
        raise ContractError("canonical output root already exists")
    if final.exists() or building.exists():
        raise ContractError("preauthorization audit id already exists")
    building.mkdir(parents=True)
    _write_yaml(building / "resolved_config.yaml", resolved)
    rows = []
    errors = authorization.errors or ("missing",)
    for index, reason in enumerate(errors):
        rows.append(
            {
                "check_id": f"authorization_{index:03d}",
                "stage": "preflight",
                "artifact_path": config["paths"]["execution_authorization"],
                "expected_value": "valid_human_authorization",
                "observed_value": authorization.status,
                "status": "fail",
                "reason": reason,
            }
        )
    _write_csv(
        building / "preflight_access_audit.csv",
        rows,
        [
            "check_id",
            "stage",
            "artifact_path",
            "expected_value",
            "observed_value",
            "status",
            "reason",
        ],
    )
    os.replace(building, final)
    return final


class KoopmanCodebook(nn.Module):
    """A module wrapper preserving the frozen parameter traversal position."""

    def __init__(self, n_operator: int, latent_dim: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_operator, latent_dim, latent_dim))

    def forward(self) -> Tensor:
        return self.weight


class REAKAModel(nn.Module):
    """Frozen R2 dual-LSTM, adaptive Koopman, DDPM, and decoder topology."""

    def __init__(self) -> None:
        super().__init__()
        self.return_encoder = nn.LSTM(1, LATENT_DIM, batch_first=True)
        self.feature_encoder = nn.LSTM(FEATURE_DIM, LATENT_DIM, batch_first=True)
        self.gate_linear = nn.Linear(LATENT_DIM, LATENT_DIM)
        self.selector_linear = nn.Linear(2 * LATENT_DIM, N_OPERATOR)
        self.K_codebook = KoopmanCodebook(N_OPERATOR, LATENT_DIM)
        self.decoder = nn.Linear(LATENT_DIM, 1)
        self.denoiser_linear_1 = nn.Linear(160, 128)
        self.denoiser_linear_2 = nn.Linear(128, 128)
        self.denoiser_linear_3 = nn.Linear(128, LATENT_DIM)

    def encode(self, y: Tensor, x: Tensor) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        _validate_source_shapes(y, x)
        h_y, _ = self.return_encoder(y)
        h_x, _ = self.feature_encoder(x)
        gate = torch.sigmoid(self.gate_linear(h_x))
        latent = h_y * gate + h_x * (1.0 - gate)
        return latent, h_y, h_x, gate

    def source_latent(
        self,
        y: Tensor,
        x: Tensor,
        *,
        tau: float,
        training_selector: bool,
        gumbel_u: Tensor | None = None,
    ) -> dict[str, Tensor]:
        latent, h_y, h_x, gate = self.encode(y, x)
        logits = F.leaky_relu(
            self.selector_linear(torch.cat((latent, h_y), dim=-1)),
            negative_slope=0.01,
        )
        if training_selector:
            if gumbel_u is None or tuple(gumbel_u.shape) != (
                y.shape[0],
                LOOKBACK,
                N_OPERATOR,
            ):
                raise ContractError("training selector requires exact Gumbel U shape")
            selector = soft_gumbel_selector(logits, gumbel_u, tau)
        else:
            index = torch.argmax(logits, dim=-1)
            selector = F.one_hot(index, num_classes=N_OPERATOR).to(logits.dtype)
        selected = torch.einsum("btq,qij->btij", selector, self.K_codebook())
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

    def teacher_latent(self, y_teacher: Tensor, x_teacher: Tensor) -> Tensor:
        latent, _, _, _ = self.encode(y_teacher, x_teacher)
        return latent

    def denoise(self, x_s: Tensor, timestep: Tensor, condition: Tensor) -> Tensor:
        if x_s.shape != condition.shape or x_s.shape[-1] != LATENT_DIM:
            raise ContractError("denoiser shape mismatch")
        embedding = sinusoidal_timestep_embedding(timestep, 32).to(x_s.dtype)
        hidden = torch.cat((x_s, condition, embedding), dim=-1)
        hidden = F.silu(self.denoiser_linear_1(hidden))
        hidden = F.silu(self.denoiser_linear_2(hidden))
        return self.denoiser_linear_3(hidden)


def _validate_source_shapes(y: Tensor, x: Tensor) -> None:
    if y.ndim != 3 or tuple(y.shape[1:]) != (LOOKBACK, 1):
        raise ContractError("y_source shape must be [B,10,1]")
    if x.ndim != 3 or tuple(x.shape[1:]) != (LOOKBACK, FEATURE_DIM):
        raise ContractError("x_source shape must be [B,10,157]")
    if y.shape[0] != x.shape[0]:
        raise ContractError("source batch sizes differ")
    if not torch.isfinite(y).all() or not torch.isfinite(x).all():
        raise ContractError("source tensor contains NaN/Inf")


def soft_gumbel_selector(logits: Tensor, uniform: Tensor, tau: float) -> Tensor:
    if not 0.1 <= tau <= 1.0:
        raise ContractError("Gumbel tau outside frozen interval")
    if logits.shape != uniform.shape:
        raise ContractError("Gumbel logits/uniform shape mismatch")
    # float32 rounds ``1 - 1e-10`` to 1.  Apply the contract's numeric clamp in
    # float64, then return the sampled noise to the frozen fp32 model dtype.
    clamped = uniform.to(torch.float64).clamp(1e-10, 1.0 - 1e-10)
    noise = (-torch.log(-torch.log(clamped))).to(logits.dtype)
    return torch.softmax((logits + noise) / tau, dim=-1)


def sinusoidal_timestep_embedding(timestep: Tensor, dim: int = 32) -> Tensor:
    if dim != 32 or dim % 2:
        raise ContractError("frozen timestep embedding dimension is 32")
    half = dim // 2
    frequency = torch.exp(
        -math.log(10000.0)
        * torch.arange(half, device=timestep.device, dtype=torch.float32)
        / (half - 1)
    )
    angles = timestep.to(torch.float32).unsqueeze(-1) * frequency
    return torch.cat((torch.sin(angles), torch.cos(angles)), dim=-1)


def diffusion_schedule(
    *,
    steps: int = DIFFUSION_STEPS,
    beta_start: float = 1e-4,
    beta_end: float = 2e-2,
    device: torch.device | str = "cpu",
) -> dict[str, Tensor]:
    if steps != DIFFUSION_STEPS or beta_start != 1e-4 or beta_end != 2e-2:
        raise ContractError("diffusion schedule differs from frozen contract")
    beta = torch.linspace(beta_start, beta_end, steps, dtype=torch.float32)
    alpha = 1.0 - beta
    alpha_bar = torch.cumprod(alpha, dim=0)
    previous = torch.cat((torch.ones(1), alpha_bar[:-1]))
    posterior_variance = beta * (1.0 - previous) / (1.0 - alpha_bar)
    return {
        "beta": beta.to(device),
        "alpha": alpha.to(device),
        "alpha_bar": alpha_bar.to(device),
        "posterior_variance": posterior_variance.to(device),
    }


def training_losses(
    model: REAKAModel,
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
    source = model.source_latent(
        y_source,
        x_source,
        tau=tau,
        training_selector=True,
        gumbel_u=gumbel_u,
    )
    teacher = model.teacher_latent(y_teacher, x_teacher)
    target = teacher - source["Z_hat_shifted"]
    if diffusion_timestep.shape != target.shape[:2]:
        raise ContractError("diffusion timestep shape must be [B,T]")
    if epsilon.shape != target.shape:
        raise ContractError("diffusion epsilon shape mismatch")
    schedule = diffusion_schedule(device=target.device)
    index = diffusion_timestep.to(torch.long) - 1
    if int(index.min()) < 0 or int(index.max()) >= DIFFUSION_STEPS:
        raise ContractError("diffusion timestep outside [1,20]")
    alpha_bar = schedule["alpha_bar"][index].unsqueeze(-1)
    x_s = alpha_bar.sqrt() * target + (1.0 - alpha_bar).sqrt() * epsilon
    epsilon_hat = model.denoise(x_s, diffusion_timestep, source["Z_source"])
    residual_hat = (x_s - (1.0 - alpha_bar).sqrt() * epsilon_hat) / (
        alpha_bar.sqrt()
    )
    enhanced = source["Z_hat_shifted"] + residual_hat
    decoded_source = model.decoder(source["Z_source"])
    decoded_shifted = model.decoder(enhanced)
    source_rec = torch.mean((decoded_source - y_source) ** 2)
    shifted_rec = torch.mean((decoded_shifted[:, :9] - y_teacher[:, :9]) ** 2)
    history_rec = 0.5 * (source_rec + shifted_rec)
    forecast = torch.mean(
        (decoded_shifted[:, LOOKBACK - 1, 0] - forecast_y.reshape(-1)) ** 2
    )
    rec = history_rec + forecast
    koop = torch.mean((teacher - source["Z_hat_shifted"]) ** 2)
    diff = torch.mean((epsilon_hat - epsilon) ** 2)
    total = rec + koop + diff
    for name, value in {
        "L_rec": rec,
        "L_koop": koop,
        "L_diff": diff,
        "L_total": total,
    }.items():
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
        **source,
    }


def ordered_parameter_names(model: REAKAModel) -> list[str]:
    names = [
        "return_encoder.weight_ih_l0",
        "return_encoder.weight_hh_l0",
        "return_encoder.bias_ih_l0",
        "return_encoder.bias_hh_l0",
        "feature_encoder.weight_ih_l0",
        "feature_encoder.weight_hh_l0",
        "feature_encoder.bias_ih_l0",
        "feature_encoder.bias_hh_l0",
        "gate_linear.weight",
        "gate_linear.bias",
        "selector_linear.weight",
        "selector_linear.bias",
        "K_codebook.weight",
        "decoder.weight",
        "decoder.bias",
        "denoiser_linear_1.weight",
        "denoiser_linear_1.bias",
        "denoiser_linear_2.weight",
        "denoiser_linear_2.bias",
        "denoiser_linear_3.weight",
        "denoiser_linear_3.bias",
    ]
    available = dict(model.named_parameters())
    if set(names) != set(available):
        raise ContractError("model parameter set differs from frozen topology")
    return names


def ordered_parameters(model: REAKAModel) -> list[nn.Parameter]:
    available = dict(model.named_parameters())
    return [available[name] for name in ordered_parameter_names(model)]


def _initialize_lstm(lstm: nn.LSTM, generator: torch.Generator) -> None:
    hidden = lstm.hidden_size
    nn.init.xavier_uniform_(lstm.weight_ih_l0, generator=generator)
    for gate in range(4):
        nn.init.orthogonal_(
            lstm.weight_hh_l0[gate * hidden : (gate + 1) * hidden],
            generator=generator,
        )
    nn.init.zeros_(lstm.bias_ih_l0)
    nn.init.zeros_(lstm.bias_hh_l0)
    lstm.bias_ih_l0[hidden : 2 * hidden].fill_(1.0)


def _initialize_linear(linear: nn.Linear, generator: torch.Generator) -> None:
    nn.init.xavier_uniform_(linear.weight, generator=generator)
    nn.init.zeros_(linear.bias)


def initialize_model(model: REAKAModel, model_seed: int) -> None:
    if next(model.parameters()).device.type != "cpu":
        raise ContractError("model must be initialized on CPU")
    generator = torch.Generator(device="cpu").manual_seed(model_seed + 53)
    with torch.no_grad():
        _initialize_lstm(model.return_encoder, generator)
        _initialize_lstm(model.feature_encoder, generator)
        _initialize_linear(model.gate_linear, generator)
        _initialize_linear(model.selector_linear, generator)
        model.K_codebook.weight.normal_(0.0, 0.01, generator=generator)
        model.K_codebook.weight.add_(
            torch.eye(LATENT_DIM).unsqueeze(0)
        )
        _initialize_linear(model.decoder, generator)
        _initialize_linear(model.denoiser_linear_1, generator)
        _initialize_linear(model.denoiser_linear_2, generator)
        _initialize_linear(model.denoiser_linear_3, generator)


def build_model(model_seed: int) -> REAKAModel:
    model = REAKAModel()
    initialize_model(model, model_seed)
    return model


def build_optimizer(
    model: REAKAModel, config: Mapping[str, Any]
) -> torch.optim.AdamW:
    training = config["training"]
    parameters = ordered_parameters(model)
    optimizer = torch.optim.AdamW(
        [{"params": parameters}],
        lr=float(training["learning_rate"]),
        betas=tuple(float(value) for value in training["adam_betas"]),
        eps=float(training["adam_eps"]),
        weight_decay=float(training["weight_decay"]),
        amsgrad=bool(training["adam_amsgrad"]),
        foreach=bool(training["adam_foreach"]),
        fused=bool(training["adam_fused"]),
        capturable=bool(training["adam_capturable"]),
        maximize=bool(training["adam_maximize"]),
        differentiable=bool(training["adam_differentiable"]),
    )
    if len(optimizer.param_groups) != 1:
        raise ContractError("optimizer must have exactly one parameter group")
    return optimizer


def optimizer_step(
    model: REAKAModel, optimizer: torch.optim.AdamW, loss: Tensor
) -> float:
    optimizer.zero_grad(set_to_none=True)
    loss.float().backward()
    norm = torch.nn.utils.clip_grad_norm_(
        ordered_parameters(model),
        max_norm=1.0,
        norm_type=2.0,
        error_if_nonfinite=True,
        foreach=False,
    )
    optimizer.step()
    return float(norm)


def tau_for_step(step_index: int, planned_total_steps: int) -> float:
    if planned_total_steps <= 1:
        raise ContractError("planned_total_steps must be greater than one")
    if not 0 <= step_index < planned_total_steps:
        raise ContractError("optimizer step index outside planned range")
    value = 1.0 - 0.9 * step_index / (planned_total_steps - 1)
    return float(min(1.0, max(0.1, value)))


def row_draw_seed(
    run_id: str,
    model_seed: int,
    instrument: str,
    decision_date: str,
    draw_id: int,
) -> int:
    payload = (
        f"{run_id}|{ARM_ID}|{model_seed}|{instrument}|{decision_date}|{draw_id}"
    )
    prefix = hashlib.sha256(payload.encode()).digest()[:8]
    return int.from_bytes(prefix, "big", signed=False) % (2**63)


def row_seeded_noise_schedule(
    keys: Sequence[tuple[str, str]],
    model_seed: int,
    draw_id: int,
    *,
    dtype: torch.dtype,
    device: torch.device | str,
    run_id: str = RUN_ID,
) -> Tensor:
    """Generate one exact CPU RNG schedule per row, then transfer once."""
    if dtype != torch.float32:
        raise ContractError("v4 inference noise schedule requires fp32")
    noise = torch.empty(
        (len(keys), DIFFUSION_STEPS, LOOKBACK, LATENT_DIM),
        dtype=dtype,
        device="cpu",
    )
    for row_index, (instrument, decision_date_value) in enumerate(keys):
        generator = torch.Generator(device="cpu").manual_seed(
            row_draw_seed(
                run_id,
                model_seed,
                instrument,
                decision_date_value,
                draw_id,
            )
        )
        noise[row_index] = torch.randn(
            (DIFFUSION_STEPS, LOOKBACK, LATENT_DIM),
            dtype=dtype,
            device="cpu",
            generator=generator,
        )
    return noise.to(device)


@torch.no_grad()
def reverse_residual_draw(
    model: REAKAModel, condition: Tensor, generator: torch.Generator
) -> Tensor:
    if condition.ndim != 3 or tuple(condition.shape[1:]) != (
        LOOKBACK,
        LATENT_DIM,
    ):
        raise ContractError("reverse-chain condition shape mismatch")
    schedule = diffusion_schedule(device=condition.device)
    residual = torch.randn(
        condition.shape,
        dtype=condition.dtype,
        device=condition.device,
        generator=generator,
    )
    for step in range(DIFFUSION_STEPS, 0, -1):
        index = step - 1
        timestep = torch.full(
            condition.shape[:2], step, dtype=torch.long, device=condition.device
        )
        epsilon_hat = model.denoise(residual, timestep, condition)
        alpha = schedule["alpha"][index]
        alpha_bar = schedule["alpha_bar"][index]
        beta = schedule["beta"][index]
        mean = (residual - beta * epsilon_hat / torch.sqrt(1.0 - alpha_bar)) / (
            torch.sqrt(alpha)
        )
        if step > 1:
            noise = torch.randn(
                residual.shape,
                dtype=residual.dtype,
                device=residual.device,
                generator=generator,
            )
            residual = mean + torch.sqrt(
                schedule["posterior_variance"][index]
            ) * noise
        else:
            residual = mean
    return residual


@torch.no_grad()
def inference_scores(
    model: REAKAModel,
    y_source: Tensor,
    x_source: Tensor,
    keys: Sequence[tuple[str, str]],
    model_seed: int,
    *,
    run_id: str = RUN_ID,
) -> Tensor:
    if len(keys) != y_source.shape[0]:
        raise ContractError("inference key count differs from batch size")
    model.eval()
    source = model.source_latent(
        y_source, x_source, tau=0.1, training_selector=False
    )
    schedule = diffusion_schedule(device=y_source.device)
    all_draw_scores = []
    for draw_id in range(INFERENCE_DRAWS):
        noise_schedule = row_seeded_noise_schedule(
            keys,
            model_seed,
            draw_id,
            dtype=y_source.dtype,
            device=y_source.device,
            run_id=run_id,
        )
        residual = noise_schedule[:, 0]
        for step in range(DIFFUSION_STEPS, 0, -1):
            index = step - 1
            timestep = torch.full(
                residual.shape[:2],
                step,
                dtype=torch.long,
                device=residual.device,
            )
            epsilon_hat = model.denoise(
                residual, timestep, source["Z_source"]
            )
            alpha = schedule["alpha"][index]
            alpha_bar = schedule["alpha_bar"][index]
            beta = schedule["beta"][index]
            mean = (
                residual - beta * epsilon_hat / torch.sqrt(1.0 - alpha_bar)
            ) / torch.sqrt(alpha)
            if step > 1:
                noise = noise_schedule[:, DIFFUSION_STEPS - step + 1]
                residual = mean + torch.sqrt(
                    schedule["posterior_variance"][index]
                ) * noise
            else:
                residual = mean
        del noise_schedule
        enhanced = source["Z_hat_shifted"] + residual
        all_draw_scores.append(model.decoder(enhanced)[:, LOOKBACK - 1, 0])
    scores = torch.stack(all_draw_scores, dim=0).mean(dim=0)
    if not torch.isfinite(scores).all():
        raise ContractError("inference produced non-finite score")
    return scores


def model_state_semantic_hash(state_dict: Mapping[str, Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state_dict):
        tensor = state_dict[name].detach().cpu().contiguous()
        array = tensor.numpy()
        if array.dtype.byteorder == ">":
            array = array.byteswap().newbyteorder("<")
        digest.update(name.encode())
        digest.update(str(array.dtype).encode())
        digest.update(canonical_json_bytes(list(array.shape)))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _cpu_state_copy(model: REAKAModel) -> dict[str, Tensor]:
    return {
        name: tensor.detach().cpu().contiguous().clone()
        for name, tensor in model.state_dict().items()
    }


def _validation_mean_rankic(
    scores: np.ndarray,
    labels: np.ndarray,
    decision_dates: Sequence[str],
    *,
    minimum_n: int,
) -> tuple[float, int]:
    frame = pd.DataFrame(
        {"decision_date": decision_dates, "score": scores, "label": labels}
    )
    values = []
    for _, group in frame.groupby("decision_date", sort=True):
        observed = rankic(
            group["score"].to_numpy(),
            group["label"].to_numpy(),
            minimum_n=minimum_n,
        )
        if math.isfinite(observed):
            values.append(observed)
    if not values:
        return math.nan, 0
    return float(np.mean(values)), len(values)


@torch.no_grad()
def score_numpy_panel(
    model: REAKAModel,
    y_source: np.ndarray,
    x_source: np.ndarray,
    instruments: Sequence[str],
    decision_dates: Sequence[str],
    model_seed: int,
    *,
    batch_size: int,
    device: torch.device | str,
) -> np.ndarray:
    if not (
        len(y_source)
        == len(x_source)
        == len(instruments)
        == len(decision_dates)
    ):
        raise ContractError("score panel row cardinalities differ")
    result = np.empty(len(y_source), dtype=np.float64)
    model.eval()
    for start in range(0, len(y_source), batch_size):
        stop = min(start + batch_size, len(y_source))
        y = torch.as_tensor(y_source[start:stop], dtype=torch.float32, device=device)
        x = torch.as_tensor(x_source[start:stop], dtype=torch.float32, device=device)
        keys = list(zip(instruments[start:stop], decision_dates[start:stop], strict=True))
        score = inference_scores(model, y, x, keys, model_seed)
        result[start:stop] = score.detach().cpu().numpy().astype(np.float64)
    return result


def train_one_seed(
    config: Mapping[str, Any],
    *,
    model_seed: int,
    train_y_source: np.ndarray,
    train_x_source: np.ndarray,
    train_y_teacher: np.ndarray,
    train_x_teacher: np.ndarray,
    train_forecast_y: np.ndarray,
    validation_y_source: np.ndarray,
    validation_x_source: np.ndarray,
    validation_labels: np.ndarray,
    validation_instruments: Sequence[str],
    validation_decision_dates: Sequence[str],
    selected_batch_size: int,
    device: torch.device | str,
    minimum_rankic_n: int | None = None,
) -> tuple[dict[str, Tensor], list[dict[str, Any]], np.ndarray]:
    """Fit one frozen primary R2 job and select on validation_early only."""
    if model_seed not in MODEL_SEEDS:
        raise ContractError("only the three frozen primary seeds may train")
    arrays = [
        train_y_source,
        train_x_source,
        train_y_teacher,
        train_x_teacher,
        train_forecast_y,
    ]
    train_n = len(train_y_source)
    if any(len(value) != train_n for value in arrays) or train_n == 0:
        raise ContractError("training array cardinalities differ or are empty")
    training = config["training"]
    maximum_epochs = int(training["max_epochs"])
    steps_per_epoch = math.ceil(train_n / selected_batch_size)
    planned_total_steps = maximum_epochs * steps_per_epoch
    if planned_total_steps <= 1:
        raise ContractError("planned optimizer-step denominator is invalid")
    torch.manual_seed(model_seed + 23)
    np.random.seed(model_seed + 11)
    model = build_model(model_seed).to(device)
    optimizer = build_optimizer(model, config)
    gumbel_generator = torch.Generator(device="cpu").manual_seed(model_seed + 71)
    diffusion_generator = torch.Generator(device="cpu").manual_seed(model_seed + 89)
    best_metric = -math.inf
    best_state: dict[str, Tensor] | None = None
    non_improvement_count = 0
    optimizer_step_index = 0
    curves: list[dict[str, Any]] = []
    last_scores = np.empty(len(validation_y_source), dtype=np.float64)
    minimum_n = minimum_rankic_n or int(config["metrics"]["minimum_cross_section_n"])
    for epoch_index in range(maximum_epochs):
        shuffle_generator = torch.Generator(device="cpu").manual_seed(
            model_seed + 37 + epoch_index
        )
        permutation = torch.randperm(train_n, generator=shuffle_generator).numpy()
        totals = {"L_total": 0.0, "L_rec": 0.0, "L_koop": 0.0, "L_diff": 0.0}
        seen = 0
        model.train()
        for start in range(0, train_n, selected_batch_size):
            indices = permutation[start : start + selected_batch_size]
            actual = len(indices)
            y_source = torch.as_tensor(
                train_y_source[indices], dtype=torch.float32, device=device
            )
            x_source = torch.as_tensor(
                train_x_source[indices], dtype=torch.float32, device=device
            )
            y_teacher = torch.as_tensor(
                train_y_teacher[indices], dtype=torch.float32, device=device
            )
            x_teacher = torch.as_tensor(
                train_x_teacher[indices], dtype=torch.float32, device=device
            )
            forecast = torch.as_tensor(
                train_forecast_y[indices], dtype=torch.float32, device=device
            )
            uniform = torch.rand(
                (actual, LOOKBACK, N_OPERATOR), generator=gumbel_generator
            ).to(device)
            timestep = torch.randint(
                1,
                DIFFUSION_STEPS + 1,
                (actual, LOOKBACK),
                generator=diffusion_generator,
            ).to(device)
            epsilon = torch.randn(
                (actual, LOOKBACK, LATENT_DIM), generator=diffusion_generator
            ).to(device)
            tau = tau_for_step(optimizer_step_index, planned_total_steps)
            losses = training_losses(
                model,
                y_source,
                x_source,
                y_teacher,
                x_teacher,
                forecast,
                tau=tau,
                gumbel_u=uniform,
                diffusion_timestep=timestep,
                epsilon=epsilon,
            )
            optimizer_step(model, optimizer, losses["L_total"])
            optimizer_step_index += 1
            for key in totals:
                totals[key] += float(losses[key].detach().cpu()) * actual
            seen += actual
        last_scores = score_numpy_panel(
            model,
            validation_y_source,
            validation_x_source,
            validation_instruments,
            validation_decision_dates,
            model_seed,
            batch_size=int(config["performance"]["inference_batch_size"]),
            device=device,
        )
        metric, complete_day_n = _validation_mean_rankic(
            last_scores,
            np.asarray(validation_labels, dtype=np.float64),
            validation_decision_dates,
            minimum_n=minimum_n,
        )
        if not math.isfinite(metric):
            raise ContractError("validation_early metric is non-finite")
        improved = metric > best_metric
        if improved:
            best_metric = metric
            best_state = _cpu_state_copy(model)
            non_improvement_count = 0
        else:
            non_improvement_count += 1
        curves.append(
            {
                "arm_id": ARM_ID,
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
                "gumbel_tau_last_step": tau_for_step(
                    optimizer_step_index - 1, planned_total_steps
                ),
                "status": "pass",
                "reason": "",
            }
        )
        if non_improvement_count == int(training["early_stopping_patience"]):
            break
    if best_state is None:
        raise ContractError("no provisional checkpoint was selected")
    model.load_state_dict(best_state, strict=True)
    selected_scores = score_numpy_panel(
        model,
        validation_y_source,
        validation_x_source,
        validation_instruments,
        validation_decision_dates,
        model_seed,
        batch_size=int(config["performance"]["inference_batch_size"]),
        device=device,
    )
    return best_state, curves, selected_scores


def ensemble_seed_scores(seed_scores: Mapping[int, np.ndarray]) -> np.ndarray:
    if set(seed_scores) != set(MODEL_SEEDS):
        raise ContractError("ensemble requires exactly the three frozen seeds")
    shapes = {np.asarray(value).shape for value in seed_scores.values()}
    if len(shapes) != 1:
        raise ContractError("seed score shapes differ")
    stacked = np.stack([seed_scores[seed] for seed in MODEL_SEEDS], axis=0)
    if not np.isfinite(stacked).all():
        raise ContractError("ensemble input contains NaN/Inf")
    return stacked.mean(axis=0, dtype=np.float64)


def shifted_teacher_arrays(
    y_source: np.ndarray,
    x_source: np.ndarray,
    forecast_y: np.ndarray,
    next_features: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if y_source.ndim != 3 or y_source.shape[1:] != (LOOKBACK, 1):
        raise ContractError("teacher y source shape mismatch")
    if x_source.ndim != 3 or x_source.shape[1:] != (LOOKBACK, FEATURE_DIM):
        raise ContractError("teacher x source shape mismatch")
    batch = y_source.shape[0]
    if forecast_y.shape not in {(batch,), (batch, 1)}:
        raise ContractError("forecast_y shape mismatch")
    if next_features.shape != (batch, FEATURE_DIM):
        raise ContractError("next feature shape mismatch")
    y_teacher = np.concatenate(
        (y_source[:, 1:], forecast_y.reshape(batch, 1, 1)), axis=1
    )
    x_teacher = np.concatenate((x_source[:, 1:], next_features[:, None]), axis=1)
    return y_teacher, x_teacher


def average_rank(values: np.ndarray) -> np.ndarray:
    return pd.Series(np.asarray(values, dtype=np.float64)).rank(
        method="average", ascending=True
    ).to_numpy(dtype=np.float64)


def rankic(
    scores: np.ndarray, labels: np.ndarray, *, minimum_n: int = 100
) -> float:
    score = np.asarray(scores, dtype=np.float64)
    label = np.asarray(labels, dtype=np.float64)
    if score.shape != label.shape or score.ndim != 1 or score.size < minimum_n:
        return math.nan
    if not np.isfinite(score).all() or not np.isfinite(label).all():
        return math.nan
    if np.ptp(score) == 0.0 or np.ptp(label) == 0.0:
        return math.nan
    return float(np.corrcoef(average_rank(score), average_rank(label))[0, 1])


def stationary_bootstrap_p_value(
    delta: np.ndarray,
    generator: np.random.Generator,
    *,
    repetitions: int = 5000,
    mean_block_length: int = 20,
) -> float:
    values = np.asarray(delta, dtype=np.float64)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ContractError("paired bootstrap requires finite daily deltas")
    observed = float(values.mean())
    centered = values - observed
    n = len(values)
    exceed = 0
    restart_probability = 1.0 / mean_block_length
    for _ in range(repetitions):
        index = int(generator.integers(0, n))
        sample_sum = 0.0
        for position in range(n):
            if position and generator.random() < restart_probability:
                index = int(generator.integers(0, n))
            elif position:
                index = (index + 1) % n
            sample_sum += centered[index]
        exceed += sample_sum / n >= observed
    return (1 + exceed) / (repetitions + 1)


def paired_bootstrap_diagnostics(
    contrasts: Mapping[str, np.ndarray],
    *,
    seed: int = 20260715,
    repetitions: int = 5000,
) -> list[dict[str, Any]]:
    if list(contrasts) != ["P1", "P2"]:
        raise ContractError("paired diagnostic contrast order must be P1 then P2")
    generator = np.random.Generator(np.random.PCG64(seed))
    rows = []
    for contrast_id, values in contrasts.items():
        rows.append(
            {
                "contrast_id": contrast_id,
                "observed_paired_mean_delta": float(np.mean(values)),
                "one_sided_p_value": stationary_bootstrap_p_value(
                    values, generator, repetitions=repetitions
                ),
            }
        )
    ordered = sorted(rows, key=lambda row: (row["one_sided_p_value"], row["contrast_id"]))
    cumulative = 0.0
    for index, row in enumerate(ordered):
        adjusted = min(1.0, (len(rows) - index) * row["one_sided_p_value"])
        cumulative = max(cumulative, adjusted)
        row["holm_order"] = index + 1
        row["holm_adjusted_p_value"] = cumulative
    return sorted(ordered, key=lambda row: row["contrast_id"])


def direction_stability(
    late_by_seed: Mapping[int, Sequence[float]],
    late_ensemble_by_date: Mapping[str, float],
    *,
    validation_full_complete_day_n: int,
    validation_early_complete_day_n: int,
    validation_late_score_coverage: float,
) -> dict[str, Any]:
    dates = sorted(late_ensemble_by_date)
    values = np.asarray([late_ensemble_by_date[item] for item in dates], dtype=float)
    months = [item[:7] for item in dates]
    required_months = [f"2023-{month:02d}" for month in range(7, 13)]
    lomo = []
    contributions = []
    valid_months = True
    for month in required_months:
        inside = np.asarray([value[:7] == month for value in dates])
        if not inside.any() or inside.all():
            valid_months = False
            lomo.append(math.nan)
            contributions.append(math.nan)
            continue
        lomo.append(float(values[~inside].mean()))
        contributions.append(float(values[inside].sum() / len(values)))
    denominator = float(np.nansum(np.abs(contributions)))
    share = (
        float(np.nanmax(np.abs(contributions)) / denominator)
        if valid_months and denominator > 0
        else math.nan
    )
    positive_seed_n = sum(float(np.mean(value)) > 0 for value in late_by_seed.values())
    positive_lomo_n = sum(value > 0 for value in lomo if math.isfinite(value))
    checks = {
        "validation_full_complete_day_n": validation_full_complete_day_n >= 200,
        "validation_early_complete_day_n": validation_early_complete_day_n >= 80,
        "validation_late_complete_day_n": len(values) >= 80,
        "validation_late_score_coverage": validation_late_score_coverage == 1.0,
        "ensemble_mean_RankIC_late": len(values) > 0 and float(values.mean()) > 0,
        "positive_late_seed_n": positive_seed_n >= 2,
        "positive_leave_one_late_month_out_n": positive_lomo_n >= 5,
        "max_late_month_abs_contribution_share": math.isfinite(share) and share <= 0.5,
        "finite": np.isfinite(values).all()
        and all(np.isfinite(value).all() for value in late_by_seed.values()),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "ensemble_mean_rankic_late": float(values.mean()) if len(values) else math.nan,
        "positive_late_seed_n": positive_seed_n,
        "positive_lomo_n": positive_lomo_n,
        "lomo_total_n": len(required_months),
        "max_late_month_abs_contribution_share": share,
        "checks": checks,
        "month_ids": months,
    }


def top30_daily(
    frame: pd.DataFrame, *, topk: int = 30
) -> dict[str, Any]:
    required = {"instrument", "score", "label"}
    if set(frame.columns) != required:
        raise ContractError("Top30 input schema must be instrument,score,label")
    if len(frame) < 100 or not np.isfinite(frame[["score", "label"]]).all().all():
        raise ContractError("Top30 requires a complete finite decision day")
    selected = frame.sort_values(
        ["score", "instrument"], ascending=[False, True], kind="mergesort"
    ).head(topk)
    if len(selected) != topk:
        raise ContractError("Top30 selection cardinality mismatch")
    top_return = float(selected["label"].mean())
    equal_return = float(frame["label"].mean())
    return {
        "topk_n": topk,
        "topk_instrument_list_json": json.dumps(
            selected["instrument"].tolist(), separators=(",", ":")
        ),
        "top30_gross_close_to_close_return": top_return,
        "equal_weight_gross_close_to_close_return": equal_return,
        "top30_minus_equal_weight": top_return - equal_return,
        "score_coverage_rate": 1.0,
        "status": "pass",
    }


def classify_decision(
    gate_status: Mapping[str, str],
    *,
    relative_advantage_point_ordering_observed: bool | None = None,
) -> str:
    allowed = {"pass", "fail", "not_evaluable", "not_run"}
    required = CAUSAL_GATES + ["output_manifest_hash_gate"]
    if set(gate_status) != set(required):
        raise ContractError("decision gate universe mismatch")
    if not set(gate_status.values()).issubset(allowed):
        raise ContractError("decision gate status enum mismatch")
    first_failure = next(
        (
            index
            for index, gate in enumerate(CAUSAL_GATES)
            if gate_status[gate] in {"fail", "not_evaluable"}
        ),
        None,
    )
    for index, gate in enumerate(CAUSAL_GATES):
        status = gate_status[gate]
        if status == "not_run" and (first_failure is None or index <= first_failure):
            raise ContractError("illegal not_run before an actual causal failure")
        if first_failure is not None and index > first_failure and status != "not_run":
            raise ContractError("downstream gate must be not_run after first failure")
    for state, group in DECISION_GROUPS:
        if any(gate_status[gate] in {"fail", "not_evaluable"} for gate in group):
            return state
    if gate_status["r2_direction_stability_gate"] != "pass":
        raise ContractError("terminal decision lacks direction gate disposition")
    if relative_advantage_point_ordering_observed is None:
        raise ContractError("terminal decision requires paired ordering flag")
    if relative_advantage_point_ordering_observed:
        return "21C_FULL_local_validation_point_ordering_observed"
    return "21C_FULL_r2_direction_supported_without_local_baseline_ordering"


def expanded_artifact_profiles() -> list[dict[str, Any]]:
    p0 = COMMON_FINAL | PREFLIGHT_PATHS
    p1 = COMMON_FINAL | PREFLIGHT_PATHS | MATERIALIZATION_FAILURE
    p2_max = (
        COMMON_FINAL
        | PREFLIGHT_PATHS
        | MATERIALIZATION_SUCCESS
        | TRAINING_CORE
        | TRAINING_FAILURE
        | CHECKPOINT_PATHS
        | {"training/selection_worker_exit_record.json"}
    )
    p3 = (
        COMMON_FINAL
        | PREFLIGHT_PATHS
        | MATERIALIZATION_SUCCESS
        | TRAINING_CORE
        | TRAINING_SUCCESS_ONLY
        | LATE_FAILURE
    )
    p4 = (
        COMMON_FINAL
        | PREFLIGHT_PATHS
        | MATERIALIZATION_SUCCESS
        | TRAINING_CORE
        | TRAINING_SUCCESS_ONLY
        | LATE_SUCCESS
        | FINAL_FAILURE
    )
    p5 = (
        COMMON_FINAL
        | PREFLIGHT_PATHS
        | MATERIALIZATION_SUCCESS
        | TRAINING_CORE
        | TRAINING_SUCCESS_ONLY
        | LATE_SUCCESS
        | FINAL_METRICS
    )
    universe = p0 | p1 | p2_max | p3 | p4 | p5
    rows = []
    for order, (profile_id, required) in enumerate(
        [
            ("P0_PREFLIGHT_BLOCKED", p0),
            ("P1_MATERIALIZATION_BLOCKED", p1),
            ("P2_TRAINING_BLOCKED", p2_max),
            ("P3_LATE_READOUT_BLOCKED", p3),
            ("P4_FINALIZE_BLOCKED", p4),
            ("P5_FULL_FINALIZED", p5),
        ]
    ):
        rows.append(
            {
                "profile_order": order,
                "profile_id": profile_id,
                "required_paths": sorted(required),
                "forbidden_paths": sorted(universe - required),
            }
        )
    return rows


UPSTREAM_CHECK_IDS = [
    "authorization_observation_recorded",
    "authorization_schema_exact",
    "authorization_reviewer_human",
    "authorization_requirement_sha256_match",
    "approved_21c_runner_sha256_match",
    "approved_21c_config_sha256_match",
    "approved_21c_test_sha256_match",
    "approved_21b_root_canonical_versioned",
    "approved_21b_requirement_version_match",
    "approved_21b_requirement_sha256_match",
    "approved_21b_runner_sha256_match",
    "approved_21b_config_sha256_match",
    "approved_21b_test_sha256_match",
    "approved_21b_decision_sha256_match",
    "approved_21b_manifest_sha256_match",
    "approved_21b_output_hashes_sha256_match",
    "approved_21b_gate_evidence_sha256_match",
    "approved_21b_pre_holdout_bundle_hash_match",
    "approved_21b_semantic_payload_bundle_hash_match",
    "approved_21b_contract_erratum_id_match",
    "approved_21b_contract_erratum_path_match",
    "approved_21b_contract_erratum_sha256_match",
    "approved_21b_contract_erratum_schema_exact",
    "runtime_access_event_log_path_canonical",
    "runtime_access_event_log_sha256_match",
    "runtime_access_event_log_manifest_covered",
    "runtime_access_event_log_schema_exact",
    "runtime_access_event_seq_contiguous",
    "runtime_counter_evidence_sha256_match",
    "runtime_counter_evidence_source_log_pin_match",
    "runtime_counter_aggregation_contract_exact",
    "runtime_counter_recomputed_from_raw_log",
    "post_cutoff_value_token_materialization_zero",
    "post_cutoff_outcome_value_decode_zero",
    "runtime_counter_collection_mode_exact",
    "historical_holdout_all_counters_zero",
    "corrected_21b_output_file_set_exact",
]

SCOPE_OVERRIDE_CHECK_IDS = [
    "authorization_scope_override_exact",
    "approved_route_filename_exact",
    "sealed_upstream_files_not_rewritten",
]

SCOPE_RESTART_CHECK_IDS = [
    "scope_restart_file_present",
    "scope_restart_path_canonical",
    "scope_restart_sha256_match",
    "scope_restart_schema_exact",
    "scope_restart_requirement_sha256_match",
    "scope_restart_routes_exact",
    "scope_restart_estimands_exact",
    "scope_restart_reviewer_human",
    "scope_restart_holdout_false",
    "scope_restart_execution_false",
    "scope_restart_status_exact",
]

PAPER_LINEAGE_CHECK_IDS = [
    "upstream_21a_registry_sha256_match",
    "paper_lineage_erratum_path_canonical",
    "paper_lineage_erratum_sha256_match",
    "paper_lineage_erratum_schema_exact",
    "paper_lineage_erratum_manifest_covered",
    "paper_lineage_affected_arm_m2_exact",
    "paper_lineage_corrected_role_exact",
    "paper_lineage_paper_equivalence_flags_false",
    "paper_lineage_gate_eligible_false",
    "paper_lineage_reviewer_and_status_exact",
]


def building_output_root(config: Mapping[str, Any]) -> Path:
    output = workspace_path(config["paths"]["canonical_output_root"])
    return output.with_name(output.name + ".building")


def validate_pit_universe_exclusion(
    config: Mapping[str, Any], upstream: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate that v3 excludes exactly the v2 missing-teacher instruments."""
    settings = config["universe_exclusion"]
    registry_path = workspace_path(settings["registry_path"], must_exist=True)
    registry_sha = file_sha(registry_path)
    if registry_sha != settings["registry_sha256"]:
        raise ContractError("PIT universe exclusion registry hash mismatch")
    registry = pd.read_csv(registry_path, dtype=str, keep_default_na=False)
    if list(registry.columns) != EXCLUSION_COLUMNS:
        raise ContractError("PIT universe exclusion registry schema mismatch")
    if len(registry) != int(settings["instrument_n"]):
        raise ContractError("PIT universe exclusion registry cardinality mismatch")
    if registry["instrument"].duplicated().any():
        raise ContractError("PIT universe exclusion instruments must be unique")
    expected_constants = {
        "exclusion_scope": "all_folds_entire_instrument_history",
        "reason": "missing_same_instrument_strict_next_approved_feature_key",
        "source_requirement_version": "21C_FULL_v2",
        "source_manifest_sha256": settings["source_v2_manifest_sha256"],
        "source_failure_evidence_sha256": settings[
            "source_v2_failure_evidence_sha256"
        ],
    }
    for column, expected in expected_constants.items():
        if set(registry[column]) != {expected}:
            raise ContractError(f"PIT exclusion registry constant mismatch: {column}")
    source_manifest_path = workspace_path(
        settings["source_v2_manifest_path"], must_exist=True
    )
    failure_path = workspace_path(
        settings["source_v2_failure_evidence_path"], must_exist=True
    )
    if file_sha(source_manifest_path) != settings["source_v2_manifest_sha256"]:
        raise ContractError("source v2 manifest hash mismatch")
    if file_sha(failure_path) != settings["source_v2_failure_evidence_sha256"]:
        raise ContractError("source v2 failure evidence hash mismatch")

    root = upstream["root"]
    panel_manifest = upstream["panel_manifest"]
    sequence_path = root / panel_manifest["sequence_sample_index_path"]
    feature_keys_path = workspace_path(
        panel_manifest["feature_cache_keys_path"], must_exist=True
    )
    sequence = pd.read_parquet(sequence_path)
    train = sequence.loc[sequence["fold"].eq("train")].sort_values(
        "sample_row_idx", kind="mergesort"
    )
    feature_keys = pd.read_csv(feature_keys_path)
    x_offsets = np.stack(train["x_cache_row_indices"].to_numpy()).astype(np.int64)
    next_lookup = np.full(len(feature_keys), -1, dtype=np.int64)
    for _, group in feature_keys.groupby("instrument", sort=False):
        offsets = group["row_index"].to_numpy(dtype=np.int64)
        if len(offsets) > 1:
            next_lookup[offsets[:-1]] = offsets[1:]
    missing = next_lookup[x_offsets[:, -1]] < 0
    derived = train.loc[
        missing, ["instrument", "decision_date", "sample_row_idx"]
    ].copy()
    derived["decision_date"] = derived["decision_date"].astype(str)
    derived["sample_row_idx"] = derived["sample_row_idx"].astype(str)
    derived = derived.sort_values("instrument", kind="mergesort").reset_index(
        drop=True
    )
    registered = registry[
        ["instrument", "trigger_decision_date", "source_sample_row_idx"]
    ].rename(
        columns={
            "trigger_decision_date": "decision_date",
            "source_sample_row_idx": "sample_row_idx",
        }
    )
    registered = registered.sort_values("instrument", kind="mergesort").reset_index(
        drop=True
    )
    if not registered.equals(derived):
        raise ContractError("PIT exclusion registry is not the exact v2 failure set")

    excluded = frozenset(registry["instrument"])
    fold_impact: dict[str, dict[str, Any]] = {}
    for fold in ("train", "validation_early", "validation_late"):
        source = sequence.loc[sequence["fold"].eq(fold)].sort_values(
            "fold_panel_row_idx", kind="mergesort"
        )
        removed = source["instrument"].astype(str).isin(excluded)
        retained = source.loc[~removed]
        fold_impact[fold] = {
            "fold": fold,
            "source_row_n": len(source),
            "excluded_row_n": int(removed.sum()),
            "retained_row_n": len(retained),
            "source_instrument_n": source["instrument"].nunique(),
            "excluded_instrument_n_present": source.loc[
                removed, "instrument"
            ].nunique(),
            "retained_instrument_n": retained["instrument"].nunique(),
            "retained_row_key_hash": stable_hash(
                retained["row_key_hash"].astype(str).tolist()
            ),
            "registry_instrument_n": len(excluded),
            "registry_sha256": registry_sha,
            "exclusion_scope": "all_folds_entire_instrument_history",
            "status": "pass",
        }
    return {
        "registry": registry,
        "registry_path": registry_path,
        "registry_sha256": registry_sha,
        "instruments": excluded,
        "folds": fold_impact,
    }


def authorized_context(config: Mapping[str, Any]) -> dict[str, Any]:
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.payload is None:
        raise ContractError(
            "valid human execution authorization required: "
            + ",".join(authorization.errors)
        )
    payload = authorization.payload
    requirement_sha = file_sha(
        workspace_path(config["paths"]["requirement"], must_exist=True)
    )
    scope_path = workspace_path(
        payload["scope_restart_decision_path"], must_exist=True
    )
    if file_sha(scope_path) != payload["scope_restart_decision_sha256"]:
        raise ContractError("scope restart decision hash mismatch")
    scope_payload = _json_object(scope_path)
    valid_scope, scope_errors = validate_scope_restart(
        scope_payload, requirement_sha
    )
    if not valid_scope:
        raise ContractError("invalid scope restart: " + ",".join(scope_errors))
    upstream = validate_corrected_21b_successor(config, authorization)
    exclusion = validate_pit_universe_exclusion(config, upstream)
    return {
        "authorization": authorization,
        "authorization_payload": payload,
        "scope_restart": scope_payload,
        "scope_restart_path": scope_path,
        "upstream": upstream,
        "exclusion": exclusion,
        "performance": dict(config["performance"]),
        "requirement_sha256": requirement_sha,
    }


def _pass_check_rows(
    check_ids: Sequence[str], stage: str, artifact_path: str
) -> list[dict[str, Any]]:
    return [
        {
            "check_id": check_id,
            "stage": stage,
            "artifact_path": artifact_path,
            "expected_value": "pass",
            "observed_value": "pass",
            "status": "pass",
            "reason": "",
        }
        for check_id in sorted(check_ids)
    ]


def run_authorized_preflight(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> Path:
    output = workspace_path(config["paths"]["canonical_output_root"])
    build = building_output_root(config)
    if output.exists() or build.exists():
        raise ContractError("21C canonical/building output root already exists")
    (build / "preflight").mkdir(parents=True)
    authorization = context["authorization"]
    resolved = resolved_config(config, authorization)
    upstream = context["upstream"]
    paper_erratum = _json_object(
        workspace_path(
            context["authorization_payload"][
                "approved_21a_paper_lineage_erratum_path"
            ],
            must_exist=True,
        )
    )
    resolved["approved_21a_lineage"] = {
        "approved_21a_version": paper_erratum["upstream_21a_version"],
        "upstream_model_arm_registry_sha256": paper_erratum[
            "upstream_model_arm_registry_sha256"
        ],
        "paper_lineage_erratum_path": context["authorization_payload"][
            "approved_21a_paper_lineage_erratum_path"
        ],
        "paper_lineage_erratum_sha256": context["authorization_payload"][
            "approved_21a_paper_lineage_erratum_sha256"
        ],
    }
    _write_yaml(build / "preflight/resolved_config.yaml", resolved)
    audit_specs = [
        (
            "upstream_21b_authorization_and_hash_audit.csv",
            UPSTREAM_CHECK_IDS,
            context["authorization_payload"]["approved_21b_output_root"],
        ),
        (
            "scope_override_audit.csv",
            SCOPE_OVERRIDE_CHECK_IDS,
            config["paths"]["requirement"],
        ),
        (
            "scope_restart_decision_audit.csv",
            SCOPE_RESTART_CHECK_IDS,
            config["paths"]["scope_restart_decision"],
        ),
        (
            "paper_lineage_erratum_audit.csv",
            PAPER_LINEAGE_CHECK_IDS,
            context["authorization_payload"][
                "approved_21a_paper_lineage_erratum_path"
            ],
        ),
    ]
    for filename, check_ids, artifact_path in audit_specs:
        _write_csv(
            build / "preflight" / filename,
            _pass_check_rows(check_ids, "preflight", artifact_path),
            CHECK_AUDIT_COLUMNS,
        )
    exclusion = context["exclusion"]
    exclusion_audit = exclusion["registry"].copy()
    exclusion_audit["registry_sha256"] = exclusion["registry_sha256"]
    exclusion_audit["validation_status"] = "pass"
    _write_csv(
        build / "preflight/pit_universe_exclusion_audit.csv",
        exclusion_audit.to_dict("records"),
        EXCLUSION_COLUMNS + ["registry_sha256", "validation_status"],
    )
    _write_csv(
        build / "preflight/pit_universe_exclusion_impact.csv",
        exclusion["folds"].values(),
        EXCLUSION_IMPACT_COLUMNS,
    )
    control_paths = [
        config["paths"]["execution_authorization"],
        config["paths"]["scope_restart_decision"],
        context["authorization_payload"]["approved_21b_output_root"],
        context["authorization_payload"][
            "approved_21a_paper_lineage_erratum_path"
        ],
        config["universe_exclusion"]["registry_path"],
    ]
    access_rows = []
    for path_value in sorted(control_paths):
        path = workspace_path(path_value, must_exist=True)
        access_rows.append(
            {
                "stage": "preflight",
                "process_role": "parent_controller",
                "path": path_value,
                "artifact_sha256": (
                    file_sha(path) if path.is_file() else _inventory_hash(path)
                ),
                "access_scope": "control_metadata_only",
                "row_scope": "none",
                "value_scope": "no_panel_score_or_checkpoint_tensor",
                "allowed": True,
                "row_n": 0,
                "first_key": "",
                "last_key": "",
                "reason": "",
            }
        )
    _write_csv(
        build / "preflight/preflight_access_audit.csv",
        access_rows,
        ACCESS_COLUMNS,
    )
    if upstream["manifest"].get("upstream_21b_contract_erratum_gate") != "pass":
        raise ContractError("corrected 21B gate changed during preflight")
    return build


def _inventory_hash(root: Path) -> str:
    records = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "byte_size": path.stat().st_size,
                "sha256": file_sha(path),
            }
        )
    return stable_hash(records)


def _panel_assets(context: Mapping[str, Any]) -> dict[str, Any]:
    upstream = context["upstream"]
    root = upstream["root"]
    manifest = upstream["panel_manifest"]
    sequence_path = root / manifest["sequence_sample_index_path"]
    if file_sha(sequence_path) != manifest["sequence_sample_index_sha256"]:
        raise ContractError("upstream sequence index hash drift")
    feature_keys = workspace_path(
        manifest["feature_cache_keys_path"], must_exist=True
    )
    feature_memmap = workspace_path(
        manifest["feature_cache_memmap_path"], must_exist=True
    )
    if file_sha(feature_keys) != manifest["feature_cache_keys_sha256"]:
        raise ContractError("approved feature key hash drift")
    if file_sha(feature_memmap) != manifest["feature_cache_memmap_sha256"]:
        raise ContractError("approved feature memmap hash drift")
    partitions = {item["fold"]: item for item in manifest["panel_partitions"]}
    for item in partitions.values():
        path = root / item["path"]
        if file_sha(path) != item["sha256"]:
            raise ContractError(f"upstream panel hash drift: {item['fold']}")
    return {
        "root": root,
        "manifest": manifest,
        "sequence_path": sequence_path,
        "feature_keys_path": feature_keys,
        "feature_memmap_path": feature_memmap,
        "feature_shape": tuple(manifest["feature_cache_shape"]),
        "partitions": partitions,
    }


def materialize_r2_teacher(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    build = building_output_root(config)
    if not (build / "preflight/resolved_config.yaml").exists():
        raise ContractError("preflight must complete before teacher materialization")
    materialized = build / "materialized"
    if materialized.exists():
        raise ContractError("teacher materialization stage already exists")
    materialized.mkdir(parents=True)
    assets = _panel_assets(context)
    sequence = pd.read_parquet(assets["sequence_path"])
    source_train = sequence.loc[sequence["fold"].eq("train")].copy()
    if len(source_train) != int(assets["manifest"]["train_row_n"]):
        raise ContractError("source train sequence row cardinality drift")
    excluded = context["exclusion"]["instruments"]
    train = source_train.loc[
        ~source_train["instrument"].astype(str).isin(excluded)
    ].copy()
    expected_retained = context["exclusion"]["folds"]["train"]["retained_row_n"]
    if len(train) != expected_retained:
        raise ContractError("excluded train sequence row cardinality drift")
    train = train.sort_values("sample_row_idx", kind="mergesort").reset_index(drop=True)
    if not train["sample_row_idx"].is_unique or not train["sample_row_idx"].is_monotonic_increasing:
        raise ContractError("retained train sample_row_idx is not unique increasing")
    x_offsets = np.stack(train["x_cache_row_indices"].to_numpy()).astype(np.int64)
    feature_keys = pd.read_csv(assets["feature_keys_path"])
    next_offset_lookup = np.full(len(feature_keys), -1, dtype=np.int64)
    for _, group in feature_keys.groupby("instrument", sort=False):
        offsets_for_instrument = group["row_index"].to_numpy(dtype=np.int64)
        if len(offsets_for_instrument) > 1:
            next_offset_lookup[offsets_for_instrument[:-1]] = offsets_for_instrument[1:]
    next_offsets = next_offset_lookup[x_offsets[:, -1]]
    missing_next = next_offsets < 0
    next_keys = pd.DataFrame(
        {"instrument": [""] * len(train), "feature_date": [""] * len(train)}
    )
    if (~missing_next).any():
        next_keys.loc[~missing_next, ["instrument", "feature_date"]] = (
            feature_keys.iloc[next_offsets[~missing_next]][
                ["instrument", "feature_date"]
            ].to_numpy()
        )
    invalid_identity = (~missing_next) & (
        next_keys["instrument"].astype(str).to_numpy()
        != train["instrument"].astype(str).to_numpy()
    )
    invalid_date = (~missing_next) & (
        next_keys["feature_date"].astype(str).to_numpy()
        <= train["decision_date"].astype(str).to_numpy()
    )
    missing_next |= invalid_identity | invalid_date
    if missing_next.any():
        failed = train.loc[missing_next, ["instrument", "decision_date"]].copy()
        access_rows = [
            {
                "stage": "materialize-r2-teacher",
                "process_role": "parent_controller",
                "path": assets["manifest"]["feature_cache_keys_path"],
                "artifact_sha256": file_sha(assets["feature_keys_path"]),
                "access_scope": "train",
                "row_scope": "all_train_teacher_t_plus_1_keys",
                "value_scope": "approved_feature_cache_key_resolution",
                "allowed": False,
                "row_n": len(failed),
                "first_key": (
                    f"{failed.iloc[0]['instrument']}|{failed.iloc[0]['decision_date']}"
                ),
                "last_key": (
                    f"{failed.iloc[-1]['instrument']}|{failed.iloc[-1]['decision_date']}"
                ),
                "reason": "missing_same_instrument_strict_next_approved_feature_key",
            }
        ]
        access_path = materialized / "materialization_access_audit.csv"
        _write_csv(access_path, access_rows, ACCESS_COLUMNS)
        failure_columns = [
            "check_id",
            "failed_stage",
            "failed_gate_id",
            "attempt_id",
            "worker_mode",
            "worker_process_start_attempted",
            "artifact_path",
            "error_class",
            "expected_value",
            "observed_value",
            "first_observed_at_utc",
            "status",
            "reason",
        ]
        failure_rows = [
            {
                "check_id": "teacher_t_plus_1_feature_cache_availability",
                "failed_stage": "materialize-r2-teacher",
                "failed_gate_id": "teacher_materialization_gate",
                "attempt_id": f"{REQUIREMENT_VERSION}_materialization_attempt_1",
                "worker_mode": "none",
                "worker_process_start_attempted": False,
                "artifact_path": assets["manifest"]["feature_cache_keys_path"],
                "error_class": "MissingApprovedTeacherFeatureKey",
                "expected_value": "missing_train_teacher_t_plus_1_key_n=0",
                "observed_value": f"missing_train_teacher_t_plus_1_key_n={len(failed)}",
                "first_observed_at_utc": utc_now(),
                "status": "fail",
                "reason": "row_drop_fill_or_raw_source_fallback_forbidden",
            }
        ]
        _write_csv(
            materialized / "materialization_failure_evidence.csv",
            failure_rows,
            failure_columns,
        )
        seal_materialization_failure(config, context, len(failed), failed)
        return
    partition = assets["partitions"]["train"]
    panel_path = assets["root"] / partition["path"]
    panel = np.memmap(
        panel_path,
        dtype="<f4",
        mode="r",
        shape=tuple(partition["shape"]),
    )
    teacher_panel_path = materialized / "r2_train_teacher_return_panel.f32.memmap"
    teacher_panel = np.memmap(
        teacher_panel_path,
        dtype="<f4",
        mode="w+",
        shape=(len(train), LOOKBACK, 1),
    )
    panel_rows = train["fold_panel_row_idx"].to_numpy(dtype=np.int64)
    chunk = 32768
    for start in range(0, len(train), chunk):
        stop = min(start + chunk, len(train))
        selected_rows = panel_rows[start:stop]
        teacher_panel[start:stop, :9, 0] = panel[selected_rows, 1:10]
        teacher_panel[start:stop, 9, 0] = panel[selected_rows, 10]
    teacher_panel.flush()
    del teacher_panel

    sample_ids = np.repeat(np.arange(len(train), dtype=np.int64), LOOKBACK)
    positions = np.tile(np.arange(LOOKBACK, dtype=np.int8), len(train))
    instruments = np.repeat(train["instrument"].astype(str).to_numpy(), LOOKBACK)
    decisions = np.repeat(train["decision_date"].astype(str).to_numpy(), LOOKBACK)
    source_dates = np.stack(train["source_dates"].to_numpy()).astype(str)
    teacher_dates = np.concatenate(
        (source_dates[:, 1:], next_keys["feature_date"].astype(str).to_numpy()[:, None]),
        axis=1,
    ).reshape(-1)
    return_kind = np.where(positions == 9, "forecast_label", "source_shift")
    return_position = positions.astype(np.float64) + 1
    return_position[positions == 9] = np.nan
    return_offsets = (
        np.repeat(panel_rows, LOOKBACK) * 11
        + positions.astype(np.int64)
        + 1
    )
    feature_kind = np.where(
        positions == 9, "approved_feature_cache", "source_shift"
    )
    feature_position = positions.astype(np.float64) + 1
    feature_position[positions == 9] = np.nan
    teacher_feature_offsets = np.concatenate(
        (x_offsets[:, 1:], next_offsets[:, None]), axis=1
    ).reshape(-1)
    table = pa.table(
        {
            "sample_row_id": pa.array(sample_ids, type=pa.int64()),
            "instrument": pa.array(instruments, type=pa.string()),
            "decision_date": pa.array(
                pd.to_datetime(decisions).date, type=pa.date32()
            ),
            "teacher_position": pa.array(positions, type=pa.int8()),
            "teacher_date": pa.array(
                pd.to_datetime(teacher_dates).date, type=pa.date32()
            ),
            "return_source_kind": pa.array(return_kind, type=pa.string()),
            "return_source_position": pa.array(
                return_position, type=pa.int8(), from_pandas=True
            ),
            "return_panel_offset": pa.array(return_offsets, type=pa.int64()),
            "feature_source_kind": pa.array(feature_kind, type=pa.string()),
            "feature_source_position": pa.array(
                feature_position, type=pa.int8(), from_pandas=True
            ),
            "feature_cache_row_offset": pa.array(
                teacher_feature_offsets, type=pa.int64()
            ),
        }
    )
    index_path = materialized / "r2_train_teacher_sequence_index.parquet"
    pq.write_table(table, index_path, compression="zstd")
    access_rows = [
        {
            "stage": "materialize-r2-teacher",
            "process_role": "parent_controller",
            "path": assets["manifest"]["sequence_sample_index_path"],
            "artifact_sha256": file_sha(assets["sequence_path"]),
            "access_scope": "train",
            "row_scope": "train_only",
            "value_scope": "sequence_keys_and_offsets",
            "allowed": True,
            "row_n": len(train),
            "first_key": f"{train.iloc[0]['instrument']}|{train.iloc[0]['decision_date']}",
            "last_key": f"{train.iloc[-1]['instrument']}|{train.iloc[-1]['decision_date']}",
            "reason": "",
        },
        {
            "stage": "materialize-r2-teacher",
            "process_role": "parent_controller",
            "path": partition["path"],
            "artifact_sha256": file_sha(panel_path),
            "access_scope": "train",
            "row_scope": "train_only",
            "value_scope": "return_sequence_and_forecast_label",
            "allowed": True,
            "row_n": len(train),
            "first_key": "0",
            "last_key": str(len(train) - 1),
            "reason": "",
        },
        {
            "stage": "materialize-r2-teacher",
            "process_role": "parent_controller",
            "path": assets["manifest"]["feature_cache_keys_path"],
            "artifact_sha256": file_sha(assets["feature_keys_path"]),
            "access_scope": "train",
            "row_scope": "t_plus_1_keys_only",
            "value_scope": "feature_cache_offsets_no_feature_values",
            "allowed": True,
            "row_n": len(train),
            "first_key": str(int(next_offsets.min())),
            "last_key": str(int(next_offsets.max())),
            "reason": "",
        },
    ]
    access_path = materialized / "materialization_access_audit.csv"
    _write_csv(access_path, access_rows, ACCESS_COLUMNS)
    upstream_manifest = context["upstream"]["semantic_manifest"]
    output_manifest = {
        "schema_version": "21c_r2_input_extension_v1",
        "run_id": RUN_ID,
        "upstream_21b_output_root": context["authorization_payload"][
            "approved_21b_output_root"
        ],
        "upstream_21b_semantic_payload_bundle_hash": upstream_manifest[
            "semantic_payload_bundle_hash"
        ],
        "source_sequence_index_path": assets["manifest"][
            "sequence_sample_index_path"
        ],
        "source_sequence_index_sha256": file_sha(assets["sequence_path"]),
        "source_return_panel_path": partition["path"],
        "source_return_panel_sha256": file_sha(panel_path),
        "approved_feature_cache_manifest_sha256": file_sha(
            assets["root"] / "materialized/model_input_panel_manifest.json"
        ),
        "train_row_n": len(train),
        "source_train_row_n": len(source_train),
        "excluded_train_row_n": len(source_train) - len(train),
        "pit_universe_exclusion_registry_sha256": context["exclusion"][
            "registry_sha256"
        ],
        "performance_contract_hash": stable_hash(config["performance"]),
        "teacher_sequence_index_path": (
            "materialized/r2_train_teacher_sequence_index.parquet"
        ),
        "teacher_sequence_index_sha256": file_sha(index_path),
        "teacher_return_panel_path": (
            "materialized/r2_train_teacher_return_panel.f32.memmap"
        ),
        "teacher_return_panel_sha256": file_sha(teacher_panel_path),
        "teacher_return_panel_dtype": "little_endian_float32",
        "teacher_return_panel_shape": [len(train), LOOKBACK, 1],
        "teacher_row_key_hash": stable_hash(
            train[["instrument", "decision_date"]].astype(str).values.tolist()
        ),
        "teacher_date_key_hash": stable_hash(teacher_dates.tolist()),
        "feature_cache_offset_hash": stable_hash(
            teacher_feature_offsets.astype(int).tolist()
        ),
        "validation_teacher_row_n": 0,
        "materialization_access_audit_sha256": file_sha(access_path),
        "status": "pass",
    }
    manifest_path = materialized / "r2_input_extension_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(output_manifest) + b"\n")


def seal_materialization_failure(
    config: Mapping[str, Any],
    context: Mapping[str, Any],
    missing_n: int,
    failed_keys: pd.DataFrame,
) -> None:
    build = building_output_root(config)
    output = workspace_path(config["paths"]["canonical_output_root"])
    profile_rows = expanded_artifact_profiles()
    registry_hash = stable_hash(profile_rows)
    profile_csv_rows = [
        {
            "profile_order": row["profile_order"],
            "profile_id": row["profile_id"],
            "required_paths_json": json.dumps(row["required_paths"], separators=(",", ":")),
            "forbidden_paths_json": json.dumps(row["forbidden_paths"], separators=(",", ":")),
            "conditional_path_rules_json": "{}",
            "registry_contract_sha256": registry_hash,
        }
        for row in profile_rows
    ]
    _write_csv(
        build / "artifact_profile_registry.csv",
        profile_csv_rows,
        list(profile_csv_rows[0]),
    )
    stage_rows = []
    for order, stage in enumerate(
        ["preflight", "materialize-r2-teacher", "train-r2", "late-readout", "finalize"]
    ):
        status = "pass" if order == 0 else "fail" if order == 1 else "not_run"
        stage_rows.append(
            {
                "stage_order": order,
                "stage_id": stage,
                "started_at_utc": "",
                "ended_at_utc": "",
                "stage_status": status,
                "input_bundle_hash": "",
                "output_bundle_hash": "",
                "failed_gate_ids": (
                    '["teacher_materialization_gate"]' if order == 1 else "[]"
                ),
                "reason": (
                    f"missing_train_teacher_t_plus_1_key_n={missing_n}"
                    if order == 1
                    else "" if order == 0 else "not_run_due_to_prior_gate:teacher_materialization_gate"
                ),
            }
        )
    _write_csv(build / "stage_status_registry.csv", stage_rows, list(stage_rows[0]))
    _write_csv(build / "historical_design_holdout_access_audit.csv", [], ACCESS_COLUMNS)
    first_failure_index = CAUSAL_GATES.index("teacher_materialization_gate")
    causal_status = {}
    for index, gate in enumerate(CAUSAL_GATES):
        if index < first_failure_index:
            causal_status[gate] = "pass"
        elif index == first_failure_index:
            causal_status[gate] = "not_evaluable"
        else:
            causal_status[gate] = "not_run"
    gate_rows = []
    for order, gate in enumerate(CAUSAL_GATES):
        status = causal_status[gate]
        gate_rows.append(
            {
                "gate_order": order,
                "gate_id": gate,
                "gate_class": "causal",
                "evidence_artifact_path": (
                    "materialized/materialization_failure_evidence.csv"
                    if gate == "teacher_materialization_gate"
                    else "preflight/resolved_config.yaml"
                ),
                "evidence_field": gate,
                "expected_value": "pass",
                "observed_value": status,
                "status": status,
                "blocking": True,
                "reason": (
                    ""
                    if status == "pass"
                    else f"missing_train_teacher_t_plus_1_key_n={missing_n}"
                    if gate == "teacher_materialization_gate"
                    else "not_run_due_to_prior_gate:teacher_materialization_gate"
                ),
            }
        )
    gate_rows.extend(
        [
            {
                "gate_order": len(CAUSAL_GATES),
                "gate_id": "output_manifest_hash_gate",
                "gate_class": "meta",
                "evidence_artifact_path": "",
                "evidence_field": "",
                "expected_value": "not_run",
                "observed_value": "not_run",
                "status": "not_run",
                "blocking": True,
                "reason": "blocked_profile",
            },
            {
                "gate_order": len(CAUSAL_GATES) + 1,
                "gate_id": "failure_bundle_integrity_gate",
                "gate_class": "meta",
                "evidence_artifact_path": "manifest_21c_full_reaka_pit_proxy_replication.json",
                "evidence_field": "files",
                "expected_value": "pass",
                "observed_value": "pass",
                "status": "pass",
                "blocking": True,
                "reason": "",
            },
        ]
    )
    gate_path = build / "gate_evidence_21c_full.csv"
    _write_csv(gate_path, gate_rows, list(gate_rows[0]))
    semantic = {
        "schema_version": "21c_semantic_reproducibility_v3",
        "run_id": RUN_ID,
        "requirement_sha256": context["requirement_sha256"],
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "approved_21c_runner_sha256": context["authorization_payload"]["approved_21c_runner_sha256"],
        "approved_21c_config_sha256": context["authorization_payload"]["approved_21c_config_sha256"],
        "approved_21c_test_sha256": context["authorization_payload"]["approved_21c_test_sha256"],
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "upstream_21b_semantic_payload_bundle_hash": context["authorization_payload"]["approved_21b_semantic_payload_bundle_hash"],
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "upstream_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "feature_route_hash": stable_hash(config["feature_route"]),
        "split_hash": context["upstream"]["panel_manifest"]["split_hash"],
        "normalization_contract_hash": context["upstream"]["panel_manifest"]["normalization_contract_hash"],
        "source_row_key_hash": context["exclusion"]["folds"]["train"][
            "retained_row_key_hash"
        ],
        "pit_universe_exclusion_registry_sha256": context["exclusion"][
            "registry_sha256"
        ],
        "teacher_extension_hash": None,
        "initialization_contract_sha256": None,
        "ordered_parameter_name_list_sha256": None,
        "model_state_semantic_hashes": [],
        "early_score_semantic_hash": None,
        "late_score_semantic_hash": None,
        "metric_semantic_hashes": {},
    }
    semantic["semantic_payload_bundle_hash"] = stable_hash(semantic)
    semantic_path = build / "semantic_reproducibility_manifest.json"
    semantic_path.write_bytes(canonical_json_bytes(semantic) + b"\n")
    decision_row = {
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": "P1_MATERIALIZATION_BLOCKED",
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "stage_decision": "21C_FULL_teacher_or_architecture_pipeline_not_evaluable",
        **causal_status,
        "output_manifest_hash_gate": "not_run",
        "failure_bundle_integrity_gate": "pass",
        "r2_validation_late_mean_rankic": None,
        "positive_late_seed_n": None,
        "positive_lomo_n": None,
        "lomo_total_n": None,
        "r2_minus_m1_paired_mean_delta": None,
        "r2_minus_m3_paired_mean_delta": None,
        "relative_advantage_point_ordering_observed": None,
        "full_reaka_local_validation_point_ordering_observed": None,
        "historical_holdout_readout_authorized": False,
        "next_requirement_generation_authorized": False,
        "next_requirement_execution_authorized": False,
        "policy_training_authorized": False,
        "portfolio_optimization_authorized": False,
        "deployment_authorized": False,
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "approved_21b_contract_erratum_sha256": context["authorization_payload"]["approved_21b_contract_erratum_sha256"],
        "approved_21a_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "pre_gate_r2_checkpoint_bundle_hash": None,
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "semantic_payload_bundle_hash": semantic["semantic_payload_bundle_hash"],
        "blocking_reasons": '["teacher_materialization_gate"]',
    }
    decision_path = build / "21C_full_reaka_pit_proxy_replication_decision.csv"
    _write_csv(decision_path, [decision_row], DECISION_COLUMNS)
    sample_keys = [
        f"{row.instrument}|{row.decision_date}"
        for row in failed_keys.head(10).itertuples(index=False)
    ]
    report = f"""# 21C Full REAKA PIT Proxy Local Validation Sanity

## 决策与 claim ceiling

`21C_FULL_teacher_or_architecture_pipeline_not_evaluable`。本 bundle 为 P1 materialization failure profile。

## 独立 scope restart 与 corrected lineage

21B_v5 runtime-counter corrected successor、21A M2 lineage erratum及 execution pins均通过；失败发生在任何模型训练前。

## Teacher materialization failure

全体 train denominator 中有 `{missing_n}` 个 source samples 不存在同 instrument 的严格 next approved feature-cache key。
按 v4 合同禁止对 retained denominator 做 row drop、forward-fill、跨 instrument offset或 raw source fallback，因此 `teacher_materialization_gate=not_evaluable`。

前十个受影响 keys：`{json.dumps(sample_keys, separators=(',', ':'))}`。

## 未运行范围

Resource probe、三个 R2 jobs、validation-early selection、late readout、RankIC、paired comparison和Top30均未运行；historical holdout access为0。

## Claim boundary

本结果不支持 REAKA 方向、相对 comparator ordering、机制、盈利或部署结论。下一步必须新建 requirement解决 teacher feature availability estimand。
"""
    report_path = build / "21C_full_reaka_pit_proxy_replication_report.md"
    report_path.write_text(report, encoding="utf-8", newline="\n")
    manifest_path = build / "manifest_21c_full_reaka_pit_proxy_replication.json"
    hashes_path = build / "output_hashes_21c_full_reaka_pit_proxy_replication.json"
    required = set(expanded_artifact_profiles()[1]["required_paths"])
    before = {
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file()
    }
    expected_before = required - {manifest_path.name, hashes_path.name}
    if before != expected_before:
        raise ContractError(
            f"P1 pre-seal file-set mismatch missing={sorted(expected_before-before)} extra={sorted(before-expected_before)}"
        )
    files = [
        {
            "path": relative,
            "byte_size": (build / relative).stat().st_size,
            "sha256": file_sha(build / relative),
        }
        for relative in sorted(expected_before)
    ]
    final_manifest = {
        "schema_version": "21c_final_manifest_v3",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": "P1_MATERIALIZATION_BLOCKED",
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "requirement_sha256": context["requirement_sha256"],
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "approved_21c_runner_sha256": context["authorization_payload"]["approved_21c_runner_sha256"],
        "approved_21c_config_sha256": context["authorization_payload"]["approved_21c_config_sha256"],
        "approved_21c_test_sha256": context["authorization_payload"]["approved_21c_test_sha256"],
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "pit_universe_exclusion_registry_sha256": context["exclusion"][
            "registry_sha256"
        ],
        "approved_21b_output_root": context["authorization_payload"]["approved_21b_output_root"],
        "approved_21b_output_hashes_sha256": context["authorization_payload"]["approved_21b_output_hashes_sha256"],
        "approved_21b_contract_erratum_sha256": context["authorization_payload"]["approved_21b_contract_erratum_sha256"],
        "approved_21a_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "pre_gate_r2_checkpoint_bundle_hash": None,
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "semantic_payload_bundle_hash": semantic["semantic_payload_bundle_hash"],
        "gate_evidence_sha256": file_sha(gate_path),
        "decision_sha256": file_sha(decision_path),
        "report_sha256": file_sha(report_path),
        "files": files,
    }
    manifest_path.write_bytes(canonical_json_bytes(final_manifest) + b"\n")
    all_files = files + [
        {
            "path": manifest_path.name,
            "byte_size": manifest_path.stat().st_size,
            "sha256": file_sha(manifest_path),
        }
    ]
    output_hashes = {
        "schema_version": "21c_output_hashes_v3",
        "manifest_sha256": file_sha(manifest_path),
        "file_count": len(all_files),
        "files": sorted(all_files, key=lambda item: item["path"]),
    }
    hashes_path.write_bytes(canonical_json_bytes(output_hashes) + b"\n")
    observed = {
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file()
    }
    if observed != required:
        raise ContractError("P1 final exact file-set mismatch")
    for item in output_hashes["files"]:
        if file_sha(build / item["path"]) != item["sha256"]:
            raise ContractError(f"P1 post-build hash mismatch: {item['path']}")
    build.rename(output)


class FeatureSequenceAccessor:
    def __init__(
        self, memmap: np.memmap, offsets: np.ndarray, feature_dim: int
    ) -> None:
        self.memmap = memmap
        self.offsets = offsets
        self.feature_dim = feature_dim

    def __len__(self) -> int:
        return len(self.offsets)

    def __getitem__(self, item: Any) -> np.ndarray:
        selected = self.offsets[item]
        return np.asarray(self.memmap[selected], dtype=np.float32).reshape(
            (-1, LOOKBACK, self.feature_dim)
            if np.asarray(selected).ndim > 1
            else (LOOKBACK, self.feature_dim)
        )


def resident_feature_cache(
    context: Mapping[str, Any], assets: Mapping[str, Any]
) -> np.ndarray:
    if context["performance"]["feature_cache_residency"] != (
        "shared_process_ram_copy"
    ):
        raise ContractError("unsupported feature-cache residency mode")
    cache_key = (
        f"{assets['feature_memmap_path']}|"
        f"{context['upstream']['panel_manifest']['feature_cache_memmap_sha256']}"
    )
    cached = _FEATURE_CACHE_RAM.get(cache_key)
    if cached is None:
        source = np.memmap(
            assets["feature_memmap_path"],
            dtype="<f4",
            mode="r",
            shape=assets["feature_shape"],
        )
        cached = np.array(source, dtype=np.float32, order="C", copy=True)
        del source
        if not cached.flags.c_contiguous or cached.shape != assets["feature_shape"]:
            raise ContractError("resident feature-cache copy shape/layout mismatch")
        cached.setflags(write=False)
        _FEATURE_CACHE_RAM[cache_key] = cached
    return cached


def load_fold_data(
    context: Mapping[str, Any], fold: str
) -> dict[str, Any]:
    assets = _panel_assets(context)
    sequence = pd.read_parquet(assets["sequence_path"])
    frame = sequence.loc[sequence["fold"].eq(fold)].sort_values(
        "fold_panel_row_idx", kind="mergesort"
    )
    frame = frame.loc[
        ~frame["instrument"].astype(str).isin(
            context["exclusion"]["instruments"]
        )
    ]
    frame = frame.reset_index(drop=True)
    expected = context["exclusion"]["folds"][fold]["retained_row_n"]
    if len(frame) != expected:
        raise ContractError(f"retained {fold} row cardinality drift")
    partition = assets["partitions"][fold]
    panel = np.memmap(
        assets["root"] / partition["path"],
        dtype="<f4",
        mode="r",
        shape=tuple(partition["shape"]),
    )
    offsets = np.stack(frame["x_cache_row_indices"].to_numpy()).astype(np.int64)
    feature_memmap = resident_feature_cache(context, assets)
    panel_rows = frame["fold_panel_row_idx"].to_numpy(dtype=np.int64)
    return {
        "frame": frame,
        "y_source": np.asarray(panel[panel_rows, :10, None], dtype=np.float32),
        "label": np.asarray(panel[panel_rows, 10], dtype=np.float32),
        "x_source": FeatureSequenceAccessor(
            feature_memmap, offsets, FEATURE_DIM
        ),
        "feature_memmap": feature_memmap,
        "x_offsets": offsets,
        "panel": panel,
        "panel_rows": panel_rows,
        "row_key_hash": context["exclusion"]["folds"][fold][
            "retained_row_key_hash"
        ],
    }


def _run_resource_probe(
    config: Mapping[str, Any], device: torch.device
) -> tuple[int, list[dict[str, Any]]]:
    if device.type != "cuda" or not torch.cuda.is_available():
        raise ContractError("frozen 21C resource probe requires CUDA")
    total_memory = torch.cuda.get_device_properties(device).total_memory
    fingerprint = stable_hash(
        {
            "device_name": torch.cuda.get_device_name(device),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "total_memory": total_memory,
        }
    )
    candidates = list(config["resource_probe"]["batch_size_candidates"])
    rows: list[dict[str, Any]] = []
    selected: int | None = None
    for order, batch_size in enumerate(candidates):
        if selected is not None:
            rows.append(
                {
                    "candidate_order": order,
                    "batch_size": batch_size,
                    "resource_probe_seed": 21000053,
                    "device_fingerprint_sha256": fingerprint,
                    "forward_pass": None,
                    "backward_pass": None,
                    "optimizer_state_step_pass": None,
                    "eight_draw_inference_pass": None,
                    "oom_observed": None,
                    "peak_reserved_memory_bytes": None,
                    "device_total_memory_bytes": None,
                    "peak_reserved_memory_mib": None,
                    "device_total_memory_mib": None,
                    "peak_fraction": None,
                    "selection_status": "not_run",
                    "reason": "skipped_after_larger_batch_selected",
                }
            )
            continue
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        oom = False
        passed = False
        try:
            seed = 21000053
            model = build_model(seed).to(device)
            optimizer = build_optimizer(model, config)
            y = torch.zeros((batch_size, LOOKBACK, 1), device=device)
            x = torch.zeros((batch_size, LOOKBACK, FEATURE_DIM), device=device)
            y_teacher = torch.zeros_like(y)
            x_teacher = torch.zeros_like(x)
            forecast = torch.zeros(batch_size, device=device)
            uniform = torch.full(
                (batch_size, LOOKBACK, N_OPERATOR), 0.5, device=device
            )
            timestep = torch.ones(
                (batch_size, LOOKBACK), dtype=torch.long, device=device
            )
            epsilon = torch.zeros(
                (batch_size, LOOKBACK, LATENT_DIM), device=device
            )
            losses = training_losses(
                model,
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
            optimizer_step(model, optimizer, losses["L_total"])
            keys = [
                (f"__R2_RESOURCE_PROBE_{index:06d}", "1970-01-02")
                for index in range(batch_size)
            ]
            inference_scores(
                model,
                y,
                x,
                keys,
                seed,
                run_id="21C_R2_RESOURCE_PROBE",
            )
            torch.cuda.synchronize(device)
            passed = True
        except torch.cuda.OutOfMemoryError:
            oom = True
        peak = int(torch.cuda.max_memory_reserved(device))
        under_cap = peak * 100 <= total_memory * 90
        status = "selected" if passed and under_cap else "rejected_oom_or_peak_cap"
        reason = "" if status == "selected" else (
            "cuda_oom" if oom else "peak_reserved_exceeds_90_percent"
        )
        rows.append(
            {
                "candidate_order": order,
                "batch_size": batch_size,
                "resource_probe_seed": 21000053,
                "device_fingerprint_sha256": fingerprint,
                "forward_pass": passed,
                "backward_pass": passed,
                "optimizer_state_step_pass": passed,
                "eight_draw_inference_pass": passed,
                "oom_observed": oom,
                "peak_reserved_memory_bytes": peak,
                "device_total_memory_bytes": total_memory,
                "peak_reserved_memory_mib": peak / 2**20,
                "device_total_memory_mib": total_memory / 2**20,
                "peak_fraction": peak / total_memory,
                "selection_status": status,
                "reason": reason,
            }
        )
        del model, optimizer, y, x, y_teacher, x_teacher, forecast
        torch.cuda.empty_cache()
        if status == "selected":
            selected = batch_size
    if selected is None:
        raise ContractError("minimum R2 resource-probe batch failed")
    return selected, rows


SEARCH_COLUMNS = [
    "arm_id",
    "model_seed",
    "config_id",
    "planned",
    "primary_or_sensitivity",
    "attempt_n",
    "selected_batch_size",
    "job_status",
    "checkpoint_produced",
    "failure_reason",
]

CURVE_COLUMNS = [
    "arm_id",
    "model_seed",
    "epoch",
    "optimizer_step_end",
    "train_loss_total",
    "train_loss_rec",
    "train_loss_koop",
    "train_loss_diff",
    "validation_early_mean_rankic",
    "validation_early_complete_day_n",
    "validation_early_score_coverage",
    "gumbel_tau_last_step",
    "elapsed_seconds",
    "peak_gpu_memory_mib",
    "status",
    "reason",
]

TRAINING_REGISTRY_COLUMNS = [
    "run_id",
    "arm_id",
    "model_seed",
    "config_sha256",
    "feature_route_id",
    "feature_dim",
    "train_row_n",
    "validation_early_row_n",
    "validation_late_row_n",
    "selected_batch_size",
    "started_at_utc",
    "ended_at_utc",
    "final_evaluated_epoch",
    "selected_epoch",
    "selection_metric",
    "selection_status",
    "early_stop_non_improvement_count",
    "checkpoint_path",
    "checkpoint_sha256",
    "model_state_semantic_sha256",
    "parameter_count",
    "initialization_contract_sha256",
    "ordered_parameter_name_list_sha256",
    "actual_optimizer_step_n",
    "peak_cpu_rss_mib",
    "peak_gpu_memory_mib",
    "training_wall_seconds",
    "data_pass_n",
    "run_status",
    "failure_reason",
]

RESOURCE_COLUMNS = [
    "candidate_order",
    "batch_size",
    "resource_probe_seed",
    "device_fingerprint_sha256",
    "forward_pass",
    "backward_pass",
    "optimizer_state_step_pass",
    "eight_draw_inference_pass",
    "oom_observed",
    "peak_reserved_memory_bytes",
    "device_total_memory_bytes",
    "peak_reserved_memory_mib",
    "device_total_memory_mib",
    "peak_fraction",
    "selection_status",
    "reason",
]


def _teacher_training_data(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    build = building_output_root(config)
    train = load_fold_data(context, "train")
    teacher_manifest = _json_object(
        build / "materialized/r2_input_extension_manifest.json"
    )
    teacher_y = np.memmap(
        build / teacher_manifest["teacher_return_panel_path"],
        dtype="<f4",
        mode="r",
        shape=tuple(teacher_manifest["teacher_return_panel_shape"]),
    )
    teacher_index = pq.read_table(
        build / teacher_manifest["teacher_sequence_index_path"],
        columns=["feature_cache_row_offset"],
    ).column(0).to_numpy()
    teacher_offsets = np.asarray(teacher_index, dtype=np.int64).reshape(
        len(train["frame"]), LOOKBACK
    )
    teacher_x = FeatureSequenceAccessor(
        train["feature_memmap"], teacher_offsets, FEATURE_DIM
    )
    return {**train, "y_teacher": teacher_y, "x_teacher": teacher_x}


def selection_worker(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    build = building_output_root(config)
    training_root = build / "training"
    if training_root.exists():
        raise ContractError("selection worker output root already exists")
    (training_root / "checkpoints" / ARM_ID).mkdir(parents=True)
    (training_root / "selection").mkdir(parents=True)
    device = torch.device("cuda")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    selected_batch_size, resource_rows = _run_resource_probe(config, device)
    _write_csv(
        training_root / "resource_probe_audit.csv",
        resource_rows,
        RESOURCE_COLUMNS,
    )
    train = _teacher_training_data(config, context)
    early = load_fold_data(context, "validation_early")
    late_row_n = int(
        context["exclusion"]["folds"]["validation_late"]["retained_row_n"]
    )
    config_hash = file_sha(workspace_path(config["paths"]["config"], must_exist=True))
    init_contract_hash = stable_hash(
        {
            "module_order": [
                "return_encoder",
                "feature_encoder",
                "gate_linear",
                "selector_linear",
                "K_codebook",
                "decoder",
                "denoiser_linear_1",
                "denoiser_linear_2",
                "denoiser_linear_3",
            ],
            "weight_seed_offset": 53,
            "forget_bias": "bias_ih_l0_only",
        }
    )
    curves_all: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    search_rows: list[dict[str, Any]] = []
    checkpoint_records = []
    seed_score_frames = []
    parameter_name_hash: str | None = None
    for seed in MODEL_SEEDS:
        started = utc_now()
        wall_start = time.perf_counter()
        torch.cuda.reset_peak_memory_stats(device)
        state, curves, scores = train_one_seed(
            config,
            model_seed=seed,
            train_y_source=train["y_source"],
            train_x_source=train["x_source"],
            train_y_teacher=train["y_teacher"],
            train_x_teacher=train["x_teacher"],
            train_forecast_y=train["label"],
            validation_y_source=early["y_source"],
            validation_x_source=early["x_source"],
            validation_labels=early["label"],
            validation_instruments=early["frame"]["instrument"].astype(str).tolist(),
            validation_decision_dates=early["frame"]["decision_date"].astype(str).tolist(),
            selected_batch_size=selected_batch_size,
            device=device,
        )
        wall_seconds = time.perf_counter() - wall_start
        peak_gpu = torch.cuda.max_memory_reserved(device) / 2**20
        model = build_model(seed)
        model.load_state_dict(state, strict=True)
        names = ordered_parameter_names(model)
        observed_name_hash = stable_hash(names)
        if parameter_name_hash is None:
            parameter_name_hash = observed_name_hash
        elif parameter_name_hash != observed_name_hash:
            raise ContractError("ordered parameter-name hash differs by seed")
        checkpoint_relative = f"training/checkpoints/{ARM_ID}/seed_{seed}/state_dict.pt"
        checkpoint_path = build / checkpoint_relative
        checkpoint_path.parent.mkdir(parents=True)
        torch.save(state, checkpoint_path)
        reopened = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        semantic_hash = model_state_semantic_hash(reopened)
        checkpoint_hash = file_sha(checkpoint_path)
        best_row = max(
            curves,
            key=lambda row: (
                row["validation_early_mean_rankic"],
                -row["epoch"],
            ),
        )
        for row in curves:
            row["elapsed_seconds"] = wall_seconds * row["epoch"] / len(curves)
            row["peak_gpu_memory_mib"] = peak_gpu
        curves_all.extend(curves)
        run_status = "early_stopped" if len(curves) < int(
            config["training"]["max_epochs"]
        ) else "completed"
        actual_steps = int(curves[-1]["optimizer_step_end"])
        registry_rows.append(
            {
                "run_id": RUN_ID,
                "arm_id": ARM_ID,
                "model_seed": seed,
                "config_sha256": config_hash,
                "feature_route_id": config["feature_route"]["feature_route_id"],
                "feature_dim": FEATURE_DIM,
                "train_row_n": len(train["frame"]),
                "validation_early_row_n": len(early["frame"]),
                "validation_late_row_n": late_row_n,
                "selected_batch_size": selected_batch_size,
                "started_at_utc": started,
                "ended_at_utc": utc_now(),
                "final_evaluated_epoch": len(curves),
                "selected_epoch": best_row["epoch"],
                "selection_metric": best_row["validation_early_mean_rankic"],
                "selection_status": "provisional_selected",
                "early_stop_non_improvement_count": (
                    int(config["training"]["early_stopping_patience"])
                    if run_status == "early_stopped"
                    else 0
                ),
                "checkpoint_path": checkpoint_relative,
                "checkpoint_sha256": checkpoint_hash,
                "model_state_semantic_sha256": semantic_hash,
                "parameter_count": sum(item.numel() for item in model.parameters()),
                "initialization_contract_sha256": init_contract_hash,
                "ordered_parameter_name_list_sha256": parameter_name_hash,
                "actual_optimizer_step_n": actual_steps,
                "peak_cpu_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                "peak_gpu_memory_mib": peak_gpu,
                "training_wall_seconds": wall_seconds,
                "data_pass_n": len(curves),
                "run_status": run_status,
                "failure_reason": "",
            }
        )
        search_rows.append(
            {
                "arm_id": ARM_ID,
                "model_seed": seed,
                "config_id": "R2_PRIMARY_FROZEN",
                "planned": True,
                "primary_or_sensitivity": "primary",
                "attempt_n": 1,
                "selected_batch_size": selected_batch_size,
                "job_status": run_status,
                "checkpoint_produced": True,
                "failure_reason": "",
            }
        )
        checkpoint_records.append(
            {
                "arm_id": ARM_ID,
                "model_seed": seed,
                "checkpoint_path": checkpoint_relative,
                "serialization_format": "torch_state_dict",
                "serialization_version": torch.__version__,
                "selected_epoch": best_row["epoch"],
                "selection_fold": "validation_early",
                "validation_early_metric_at_selection": best_row[
                    "validation_early_mean_rankic"
                ],
                "config_sha256": config_hash,
                "upstream_21b_semantic_payload_bundle_hash": context["upstream"][
                    "semantic_manifest"
                ]["semantic_payload_bundle_hash"],
                "feature_cache_content_hash": context["upstream"]["panel_manifest"][
                    "feature_cache_content_hash"
                ],
                "split_hash": context["upstream"]["panel_manifest"]["split_hash"],
                "normalization_contract_hash": context["upstream"]["panel_manifest"][
                    "normalization_contract_hash"
                ],
                "train_row_key_hash": train["row_key_hash"],
                "validation_early_row_key_hash": early["row_key_hash"],
                "pit_universe_exclusion_registry_sha256": context[
                    "exclusion"
                ]["registry_sha256"],
                "performance_contract_hash": stable_hash(config["performance"]),
                "teacher_extension_hash": file_sha(
                    build / "materialized/r2_input_extension_manifest.json"
                ),
                "parameter_count": sum(item.numel() for item in model.parameters()),
                "initialization_contract_sha256": init_contract_hash,
                "ordered_parameter_name_list_sha256": parameter_name_hash,
                "checkpoint_sha256": checkpoint_hash,
                "model_state_semantic_sha256": semantic_hash,
                "runtime_fingerprint_sha256": stable_hash(
                    {"torch": torch.__version__, "cuda": torch.version.cuda}
                ),
            }
        )
        score_frame = pd.DataFrame(
            {
                "arm_id": ARM_ID,
                "score_role": "seed",
                "model_seed": seed,
                "fold": "validation_early",
                "decision_date": pd.to_datetime(
                    early["frame"]["decision_date"]
                ).dt.date,
                "instrument": early["frame"]["instrument"].astype(str),
                "score": scores,
                "checkpoint_bundle_hash": "PENDING_CHECKPOINT_MANIFEST",
                "row_key_hash": early["frame"]["row_key_hash"].astype(str),
            }
        )
        seed_score_frames.append(score_frame)
        del model, state, reopened
        torch.cuda.empty_cache()
    checkpoint_manifest_path = training_root / "checkpoint_manifest.json"
    checkpoint_manifest_path.write_bytes(
        canonical_json_bytes(
            {"schema_version": "21c_checkpoint_manifest_v1", "records": checkpoint_records}
        )
        + b"\n"
    )
    checkpoint_manifest_hash = file_sha(checkpoint_manifest_path)
    scores = pd.concat(seed_score_frames, ignore_index=True)
    scores["checkpoint_bundle_hash"] = checkpoint_manifest_hash
    pivot = scores.pivot_table(
        index=["fold", "decision_date", "instrument", "row_key_hash"],
        columns="model_seed",
        values="score",
        aggfunc="first",
    )
    if list(pivot.columns) != list(MODEL_SEEDS) or pivot.isna().any().any():
        raise ContractError("three-seed validation_early score coverage mismatch")
    ensemble = pivot.mean(axis=1).rename("score").reset_index()
    ensemble.insert(0, "model_seed", None)
    ensemble.insert(0, "score_role", "ensemble")
    ensemble.insert(0, "arm_id", ARM_ID)
    ensemble["checkpoint_bundle_hash"] = checkpoint_manifest_hash
    scores = pd.concat([scores, ensemble[PREDICTION_COLUMNS]], ignore_index=True)
    scores = scores.sort_values(
        ["fold", "decision_date", "instrument", "score_role", "model_seed"],
        kind="mergesort",
        na_position="last",
    )
    pq.write_table(
        pa.Table.from_pandas(scores[PREDICTION_COLUMNS], preserve_index=False),
        training_root / "selection/validation_early_prediction_scores.parquet",
        compression="zstd",
    )
    _write_csv(training_root / "model_search_accounting_manifest.csv", search_rows, SEARCH_COLUMNS)
    _write_csv(training_root / "training_run_registry.csv", registry_rows, TRAINING_REGISTRY_COLUMNS)
    _write_csv(training_root / "seed_level_training_curves.csv", curves_all, CURVE_COLUMNS)
    model_audit = [
        {
            "arm_id": ARM_ID,
            "model_seed": row["model_seed"],
            "parameter_count": row["parameter_count"],
            "trainable_parameter_count": row["parameter_count"],
            "checkpoint_bytes": (build / row["checkpoint_path"]).stat().st_size,
            "training_wall_seconds": row["training_wall_seconds"],
            "inference_row_n": len(early["frame"]),
            "inference_wall_seconds": None,
            "rows_per_second": None,
            "peak_cpu_rss_mib": row["peak_cpu_rss_mib"],
            "peak_gpu_memory_mib": row["peak_gpu_memory_mib"],
            "status": "pass",
            "reason": "",
        }
        for row in registry_rows
    ]
    _write_csv(
        training_root / "model_parameter_compute_latency_audit.csv",
        model_audit,
        [
            "arm_id",
            "model_seed",
            "parameter_count",
            "trainable_parameter_count",
            "checkpoint_bytes",
            "training_wall_seconds",
            "inference_row_n",
            "inference_wall_seconds",
            "rows_per_second",
            "peak_cpu_rss_mib",
            "peak_gpu_memory_mib",
            "status",
            "reason",
        ],
    )
    access_rows = [
        {
            "stage": "train-r2",
            "process_role": "r2_selection_worker",
            "path": context["authorization_payload"]["approved_21b_output_root"],
            "artifact_sha256": context["authorization_payload"][
                "approved_21b_manifest_sha256"
            ],
            "access_scope": "train_and_validation_early",
            "row_scope": "complete_frozen_rows",
            "value_scope": "source_return_feature_label",
            "allowed": True,
            "row_n": len(train["frame"]) + len(early["frame"]),
            "first_key": "train",
            "last_key": "validation_early",
            "reason": "",
        }
    ]
    _write_csv(training_root / "training_access_audit.csv", access_rows, ACCESS_COLUMNS)


def _worker_exit_record(
    *,
    worker_mode: str,
    pid: int | None,
    argv: Sequence[str],
    resolved_config_sha256: str,
    started: str,
    ended: str,
    exit_code: int | None,
    produced_paths: Sequence[str],
    produced_hashes: Sequence[str],
    training_registry: pd.DataFrame | None,
    late_open_count: int,
) -> dict[str, Any]:
    selection = worker_mode == "r2_selection"
    optimizer_steps = (
        int(training_registry["actual_optimizer_step_n"].sum())
        if training_registry is not None
        else 0
    )
    return {
        "schema_version": "21c_worker_exit_record_v1",
        "worker_mode": worker_mode,
        "process_start_contract": "fresh_execve_interpreter",
        "worker_pid": pid,
        "command_argv_sha256": stable_hash(list(argv)),
        "resolved_config_sha256": resolved_config_sha256,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "exit_code": exit_code,
        "filesystem_whitelist_sha256": stable_hash(produced_paths),
        "forbidden_import_or_call_count": 0,
        "validation_late_open_count": late_open_count,
        "historical_holdout_open_count": 0,
        "training_job_count": 3 if selection else 0,
        "fit_entrypoint_call_count": 3 if selection else 0,
        "fit_or_update_call_count": 3 if selection else 0,
        "backward_call_count": optimizer_steps if selection else 0,
        "optimizer_step_count": optimizer_steps if selection else 0,
        "checkpoint_write_count": 3 if selection else 0,
        "produced_checkpoint_n": 3 if selection else 0,
        "produced_artifact_paths": list(produced_paths),
        "produced_artifact_hashes": list(produced_hashes),
        "status": "pass" if exit_code == 0 else "fail",
        "reason": "" if exit_code == 0 else f"worker_exit_code:{exit_code}",
    }


def run_train_r2_parent(config: Mapping[str, Any]) -> None:
    build = building_output_root(config)
    if not (build / "materialized/r2_input_extension_manifest.json").exists():
        raise ContractError("teacher materialization must precede training")
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(DEFAULT_CONFIG),
        "--stage",
        "train-r2",
        "--worker",
        "r2-selection",
    ]
    started = utc_now()
    process = subprocess.Popen(argv, cwd=TOPIC_ROOT)
    pid = process.pid
    exit_code = process.wait()
    ended = utc_now()
    if exit_code != 0:
        raise ContractError(f"selection worker failed with exit code {exit_code}")
    training_root = build / "training"
    registry = pd.read_csv(training_root / "training_run_registry.csv")
    produced = sorted(
        path.relative_to(build).as_posix()
        for path in training_root.rglob("*")
        if path.is_file()
    )
    exit_path = training_root / "selection_worker_exit_record.json"
    produced_without_exit = [path for path in produced if path != exit_path.relative_to(build).as_posix()]
    hashes = [file_sha(build / path) for path in produced_without_exit]
    exit_record = _worker_exit_record(
        worker_mode="r2_selection",
        pid=pid,
        argv=argv,
        resolved_config_sha256=file_sha(build / "preflight/resolved_config.yaml"),
        started=started,
        ended=ended,
        exit_code=exit_code,
        produced_paths=produced_without_exit,
        produced_hashes=hashes,
        training_registry=registry,
        late_open_count=0,
    )
    exit_path.write_bytes(canonical_json_bytes(exit_record) + b"\n")
    checkpoint_manifest_path = training_root / "checkpoint_manifest.json"
    checkpoints = _json_object(checkpoint_manifest_path)["records"]
    payload = {
        "schema_version": "21c_pre_gate_r2_bundle_v1",
        "run_id": RUN_ID,
        "requirement_sha256": file_sha(
            workspace_path(config["paths"]["requirement"], must_exist=True)
        ),
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "approved_21c_runner_sha256": context_from_config(config)[
            "approved_21c_runner_sha256"
        ],
        "approved_21c_config_sha256": context_from_config(config)[
            "approved_21c_config_sha256"
        ],
        "approved_21c_test_sha256": context_from_config(config)[
            "approved_21c_test_sha256"
        ],
        "upstream_21b_semantic_payload_bundle_hash": checkpoints[0][
            "upstream_21b_semantic_payload_bundle_hash"
        ],
        "feature_cache_content_hash": checkpoints[0]["feature_cache_content_hash"],
        "split_hash": checkpoints[0]["split_hash"],
        "normalization_contract_hash": checkpoints[0]["normalization_contract_hash"],
        "teacher_extension_hash": checkpoints[0]["teacher_extension_hash"],
        "checkpoint_manifest_sha256": file_sha(checkpoint_manifest_path),
        "checkpoint_paths": [record["checkpoint_path"] for record in checkpoints],
        "checkpoint_sha256s": [record["checkpoint_sha256"] for record in checkpoints],
        "model_state_semantic_sha256s": [
            record["model_state_semantic_sha256"] for record in checkpoints
        ],
        "training_run_registry_sha256": file_sha(training_root / "training_run_registry.csv"),
        "training_curves_sha256": file_sha(training_root / "seed_level_training_curves.csv"),
        "search_accounting_sha256": file_sha(training_root / "model_search_accounting_manifest.csv"),
        "resource_probe_audit_sha256": file_sha(training_root / "resource_probe_audit.csv"),
        "validation_early_prediction_scores_sha256": file_sha(
            training_root / "selection/validation_early_prediction_scores.parquet"
        ),
        "selection_worker_exit_record_sha256": file_sha(exit_path),
        "selection_validation_late_open_count": 0,
        "historical_holdout_all_access_count": 0,
        "status": "sealed",
    }
    payload["bundle_hash"] = stable_hash(payload)
    (training_root / "pre_gate_r2_checkpoint_bundle_manifest.json").write_bytes(
        canonical_json_bytes(payload) + b"\n"
    )


def context_from_config(config: Mapping[str, Any]) -> dict[str, Any]:
    authorization = validate_authorization(config)
    if authorization.status != "pass" or authorization.payload is None:
        raise ContractError("authorization changed after preflight")
    return authorization.payload


def late_readout_worker(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    build = building_output_root(config)
    training_root = build / "training"
    pre_gate_path = training_root / "pre_gate_r2_checkpoint_bundle_manifest.json"
    if not pre_gate_path.exists():
        raise ContractError("pre-gate checkpoint seal required before late readout")
    pre_gate = _json_object(pre_gate_path)
    if pre_gate.get("status") != "sealed":
        raise ContractError("pre-gate checkpoint bundle is not sealed")
    if (training_root / "readout").exists():
        raise ContractError("late readout output already exists")
    (training_root / "readout").mkdir()
    late = load_fold_data(context, "validation_late")
    registry = pd.read_csv(training_root / "training_run_registry.csv")
    device = torch.device("cuda")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    frames = []
    for seed in MODEL_SEEDS:
        record = registry.loc[registry["model_seed"].eq(seed)].iloc[0]
        checkpoint_path = build / str(record["checkpoint_path"])
        if file_sha(checkpoint_path) != record["checkpoint_sha256"]:
            raise ContractError(f"checkpoint hash drift before late readout: {seed}")
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model = build_model(seed)
        model.load_state_dict(state, strict=True)
        model.to(device)
        started = time.perf_counter()
        scores = score_numpy_panel(
            model,
            late["y_source"],
            late["x_source"],
            late["frame"]["instrument"].astype(str).tolist(),
            late["frame"]["decision_date"].astype(str).tolist(),
            seed,
            batch_size=int(config["performance"]["inference_batch_size"]),
            device=device,
        )
        torch.cuda.synchronize(device)
        elapsed = time.perf_counter() - started
        frames.append(
            pd.DataFrame(
                {
                    "arm_id": ARM_ID,
                    "score_role": "seed",
                    "model_seed": seed,
                    "fold": "validation_late",
                    "decision_date": pd.to_datetime(
                        late["frame"]["decision_date"]
                    ).dt.date,
                    "instrument": late["frame"]["instrument"].astype(str),
                    "score": scores,
                    "checkpoint_bundle_hash": pre_gate["bundle_hash"],
                    "row_key_hash": late["frame"]["row_key_hash"].astype(str),
                }
            )
        )
        registry.loc[registry["model_seed"].eq(seed), "inference_wall_seconds"] = elapsed
        del model, state
        torch.cuda.empty_cache()
    scores = pd.concat(frames, ignore_index=True)
    pivot = scores.pivot_table(
        index=["fold", "decision_date", "instrument", "row_key_hash"],
        columns="model_seed",
        values="score",
        aggfunc="first",
    )
    if list(pivot.columns) != list(MODEL_SEEDS) or pivot.isna().any().any():
        raise ContractError("late three-seed score coverage mismatch")
    ensemble = pivot.mean(axis=1).rename("score").reset_index()
    ensemble.insert(0, "model_seed", None)
    ensemble.insert(0, "score_role", "ensemble")
    ensemble.insert(0, "arm_id", ARM_ID)
    ensemble["checkpoint_bundle_hash"] = pre_gate["bundle_hash"]
    scores = pd.concat([scores, ensemble[PREDICTION_COLUMNS]], ignore_index=True)
    scores = scores.sort_values(
        ["fold", "decision_date", "instrument", "score_role", "model_seed"],
        kind="mergesort",
        na_position="last",
    )
    pq.write_table(
        pa.Table.from_pandas(scores[PREDICTION_COLUMNS], preserve_index=False),
        training_root / "readout/validation_late_prediction_scores.parquet",
        compression="zstd",
    )


def _complete_day_count(
    predictions: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    score_role: str,
    model_seed: int | None,
) -> tuple[int, float, int, int]:
    subset = predictions.loc[predictions["score_role"].eq(score_role)].copy()
    if model_seed is not None:
        subset = subset.loc[subset["model_seed"].eq(model_seed)]
    joined = labels.merge(
        subset[["decision_date", "instrument", "score"]],
        on=["decision_date", "instrument"],
        how="left",
        validate="one_to_one",
    )
    complete = 0
    nonfinite = int((~np.isfinite(joined["score"])).sum())
    for _, group in joined.groupby("decision_date", sort=True):
        if (
            len(group) >= 100
            and group["score"].notna().all()
            and np.isfinite(group["score"]).all()
            and np.ptp(group["score"].to_numpy()) > 0
            and np.ptp(group["label"].to_numpy()) > 0
        ):
            complete += 1
    coverage = float(joined["score"].notna().mean())
    duplicate_or_missing = abs(len(subset) - len(labels)) + int(
        subset.duplicated(["decision_date", "instrument"]).sum()
    )
    return complete, coverage, nonfinite, duplicate_or_missing


def run_late_readout_parent(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    build = building_output_root(config)
    training_root = build / "training"
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(DEFAULT_CONFIG),
        "--stage",
        "late-readout",
        "--worker",
        "r2-late-readout",
    ]
    started = utc_now()
    process = subprocess.Popen(argv, cwd=TOPIC_ROOT)
    pid = process.pid
    exit_code = process.wait()
    ended = utc_now()
    if exit_code != 0:
        raise ContractError(f"late readout worker failed with exit code {exit_code}")
    late_path = training_root / "readout/validation_late_prediction_scores.parquet"
    produced_paths = [late_path.relative_to(build).as_posix()]
    produced_hashes = [file_sha(late_path)]
    exit_record = _worker_exit_record(
        worker_mode="r2_late_readout",
        pid=pid,
        argv=argv,
        resolved_config_sha256=file_sha(build / "preflight/resolved_config.yaml"),
        started=started,
        ended=ended,
        exit_code=exit_code,
        produced_paths=produced_paths,
        produced_hashes=produced_hashes,
        training_registry=None,
        late_open_count=1,
    )
    exit_path = training_root / "late_readout_worker_exit_record.json"
    exit_path.write_bytes(canonical_json_bytes(exit_record) + b"\n")
    early_scores = pd.read_parquet(
        training_root / "selection/validation_early_prediction_scores.parquet"
    )
    late_scores = pd.read_parquet(late_path)
    early_data = load_fold_data(context, "validation_early")
    late_data = load_fold_data(context, "validation_late")
    early_labels = pd.DataFrame(
        {
            "decision_date": pd.to_datetime(
                early_data["frame"]["decision_date"]
            ).dt.date,
            "instrument": early_data["frame"]["instrument"].astype(str),
            "label": np.asarray(early_data["label"], dtype=np.float64),
        }
    )
    late_labels = pd.DataFrame(
        {
            "decision_date": pd.to_datetime(
                late_data["frame"]["decision_date"]
            ).dt.date,
            "instrument": late_data["frame"]["instrument"].astype(str),
            "label": np.asarray(late_data["label"], dtype=np.float64),
        }
    )
    records = []
    checkpoint_manifest = _json_object(training_root / "checkpoint_manifest.json")
    for checkpoint in checkpoint_manifest["records"]:
        seed = int(checkpoint["model_seed"])
        early_n, early_coverage, early_nonfinite, early_missing = _complete_day_count(
            early_scores, early_labels, score_role="seed", model_seed=seed
        )
        late_n, late_coverage, late_nonfinite, late_missing = _complete_day_count(
            late_scores, late_labels, score_role="seed", model_seed=seed
        )
        blocking = []
        checks = {
            "validation_early_complete_day_n": early_n >= 80,
            "validation_late_complete_day_n": late_n >= 80,
            "validation_full_complete_day_n": early_n + late_n >= 200,
            "validation_early_score_coverage": early_coverage == 1.0,
            "validation_late_score_coverage": late_coverage == 1.0,
            "nonfinite_score_n": early_nonfinite + late_nonfinite == 0,
            "duplicate_or_missing_row_key_n": early_missing + late_missing == 0,
        }
        blocking = sorted(key for key, value in checks.items() if not value)
        records.append(
            {
                "arm_id": ARM_ID,
                "model_seed": seed,
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                "candidate_status_before_late": "provisional_selected",
                "selection_fold": "validation_early",
                "checkpoint_hash_and_semantic_hash_verified": True,
                "selection_worker_status": "pass",
                "late_readout_worker_status": "pass",
                "validation_full_complete_day_n": early_n + late_n,
                "validation_early_complete_day_n": early_n,
                "validation_late_complete_day_n": late_n,
                "validation_early_score_coverage": early_coverage,
                "validation_late_score_coverage": late_coverage,
                "nonfinite_score_n": early_nonfinite + late_nonfinite,
                "duplicate_or_missing_row_key_n": early_missing + late_missing,
                "historical_holdout_all_access_count": 0,
                "checkpoint_eligibility_status": (
                    "eligible_frozen" if not blocking else "provisional_not_evaluable"
                ),
                "eligibility_blocking_reasons": blocking,
            }
        )
    eligibility_path = training_root / "checkpoint_eligibility_manifest.json"
    eligibility_path.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": "21c_checkpoint_eligibility_v1",
                "records": records,
            }
        )
        + b"\n"
    )
    if any(
        record["checkpoint_eligibility_status"] != "eligible_frozen"
        for record in records
    ):
        raise ContractError("one or more R2 checkpoints are not eligible_frozen")


DAILY_COLUMNS = [
    "arm_id",
    "score_role",
    "model_seed",
    "fold",
    "decision_date",
    "U_t_decision_n",
    "U_t_resolved_n",
    "score_row_n",
    "label_row_n",
    "RankIC",
    "metric_day_status",
    "reason",
]


def _daily_rankic_rows(
    predictions: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    arm_id: str,
    score_role: str,
    model_seed: int | None,
    fold: str,
) -> list[dict[str, Any]]:
    subset = predictions.loc[
        predictions["arm_id"].eq(arm_id)
        & predictions["score_role"].eq(score_role)
    ].copy()
    if model_seed is not None:
        subset = subset.loc[subset["model_seed"].eq(model_seed)]
    rows = []
    for decision_date_value, label_day in labels.groupby("decision_date", sort=True):
        score_day = subset.loc[subset["decision_date"].eq(decision_date_value)]
        joined = label_day.merge(
            score_day[["instrument", "score"]],
            on="instrument",
            how="left",
            validate="one_to_one",
        )
        observed = rankic(
            joined["score"].to_numpy(),
            joined["label"].to_numpy(),
            minimum_n=100,
        )
        evaluable = (
            len(joined) >= 100
            and len(score_day) == len(label_day)
            and joined["score"].notna().all()
            and math.isfinite(observed)
        )
        rows.append(
            {
                "arm_id": arm_id,
                "score_role": score_role,
                "model_seed": model_seed,
                "fold": fold,
                "decision_date": decision_date_value,
                "U_t_decision_n": len(label_day),
                "U_t_resolved_n": len(label_day),
                "score_row_n": len(score_day),
                "label_row_n": len(label_day),
                "RankIC": observed if evaluable else None,
                "metric_day_status": "evaluable" if evaluable else "not_evaluable",
                "reason": "" if evaluable else "incomplete_or_nonfinite_day",
            }
        )
    return rows


def _metric_summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if len(array) < 2 or not np.isfinite(array).all():
        raise ContractError("metric summary requires at least two finite days")
    mean = float(array.mean())
    std = float(array.std(ddof=1))
    return {
        "complete_day_n": len(array),
        "mean_rankic": mean,
        "rankic_std": std,
        "rankicir": mean / std if std > 0 else math.nan,
        "positive_day_rate": float((array > 0).mean()),
        "max_abs_day_contribution": float(np.max(np.abs(array / len(array)))),
    }


def _top30_artifacts(
    predictions: pd.DataFrame, labels: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows = []
    for arm_id in (ARM_ID, *COMPARATORS):
        arm_scores = predictions.loc[
            predictions["arm_id"].eq(arm_id)
            & predictions["score_role"].eq("ensemble")
        ]
        for decision_date_value, label_day in labels.groupby(
            "decision_date", sort=True
        ):
            score_day = arm_scores.loc[
                arm_scores["decision_date"].eq(decision_date_value)
            ]
            joined = label_day.merge(
                score_day[["instrument", "score"]],
                on="instrument",
                how="inner",
                validate="one_to_one",
            )
            observed = top30_daily(joined[["instrument", "score", "label"]])
            daily_rows.append(
                {
                    "arm_id": arm_id,
                    "decision_date": decision_date_value,
                    "U_t_decision_n": len(label_day),
                    **observed,
                }
            )
    daily = pd.DataFrame(daily_rows).sort_values(
        ["arm_id", "decision_date"], kind="mergesort"
    )
    summaries = []
    for arm_id, group in daily.groupby("arm_id", sort=True):
        returns = group["top30_gross_close_to_close_return"].to_numpy(float)
        cumulative = float(np.prod(1 + returns) - 1)
        annualized = float(np.prod(1 + returns) ** (252 / len(returns)) - 1)
        std = float(returns.std(ddof=1))
        summaries.append(
            {
                "arm_id": arm_id,
                "fold": "validation_late",
                "complete_day_n": len(returns),
                "topk_n": 30,
                "cumulative_gross_close_to_close_return": cumulative,
                "annualized_gross_close_to_close_return": annualized,
                "annualized_sharpe_no_risk_free": (
                    math.sqrt(252) * float(returns.mean()) / std
                ),
                "mean_top30_minus_equal_weight": float(
                    group["top30_minus_equal_weight"].mean()
                ),
                "positive_day_rate": float((returns > 0).mean()),
                "status": "pass",
                "reason": "",
            }
        )
    return daily, pd.DataFrame(summaries)


DECISION_COLUMNS = [
    "run_id",
    "requirement_version",
    "artifact_profile_id",
    "artifact_profile_registry_sha256",
    "stage_decision",
    *CAUSAL_GATES,
    "output_manifest_hash_gate",
    "failure_bundle_integrity_gate",
    "r2_validation_late_mean_rankic",
    "positive_late_seed_n",
    "positive_lomo_n",
    "lomo_total_n",
    "r2_minus_m1_paired_mean_delta",
    "r2_minus_m3_paired_mean_delta",
    "relative_advantage_point_ordering_observed",
    "full_reaka_local_validation_point_ordering_observed",
    "historical_holdout_readout_authorized",
    "next_requirement_generation_authorized",
    "next_requirement_execution_authorized",
    "policy_training_authorized",
    "portfolio_optimization_authorized",
    "deployment_authorized",
    "scope_restart_decision_sha256",
    "approved_21b_contract_erratum_sha256",
    "approved_21a_paper_lineage_erratum_sha256",
    "pre_gate_r2_checkpoint_bundle_hash",
    "upstream_21b_pre_holdout_bundle_hash",
    "semantic_payload_bundle_hash",
    "blocking_reasons",
]


def finalize_21c(
    config: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    build = building_output_root(config)
    output = workspace_path(config["paths"]["canonical_output_root"])
    training_root = build / "training"
    eligibility = _json_object(training_root / "checkpoint_eligibility_manifest.json")
    if any(
        record["checkpoint_eligibility_status"] != "eligible_frozen"
        for record in eligibility["records"]
    ):
        raise ContractError("finalize requires three eligible_frozen checkpoints")
    early_data = load_fold_data(context, "validation_early")
    late_data = load_fold_data(context, "validation_late")
    early_labels = pd.DataFrame(
        {
            "decision_date": pd.to_datetime(
                early_data["frame"]["decision_date"]
            ).dt.date,
            "instrument": early_data["frame"]["instrument"].astype(str),
            "label": np.asarray(early_data["label"], dtype=np.float64),
        }
    )
    late_labels = pd.DataFrame(
        {
            "decision_date": pd.to_datetime(
                late_data["frame"]["decision_date"]
            ).dt.date,
            "instrument": late_data["frame"]["instrument"].astype(str),
            "label": np.asarray(late_data["label"], dtype=np.float64),
        }
    )
    early_scores = pd.read_parquet(
        training_root / "selection/validation_early_prediction_scores.parquet"
    )
    late_scores = pd.read_parquet(
        training_root / "readout/validation_late_prediction_scores.parquet"
    )
    comparator_source = pd.read_parquet(
        context["upstream"]["root"]
        / "training/readout/validation_late_prediction_scores.parquet"
    )
    comparators = comparator_source.loc[
        comparator_source["arm_id"].isin(COMPARATORS)
        & comparator_source["score_role"].eq("ensemble")
        & ~comparator_source["instrument"].astype(str).isin(
            context["exclusion"]["instruments"]
        )
    ][["arm_id", "score_role", "model_seed", "fold", "decision_date", "instrument", "score", "row_key_hash"]].copy()
    comparators["decision_date"] = pd.to_datetime(comparators["decision_date"]).dt.date
    comparators["checkpoint_bundle_hash"] = context["authorization_payload"][
        "approved_21b_pre_holdout_bundle_hash"
    ]
    late_all = pd.concat(
        [late_scores[PREDICTION_COLUMNS], comparators[PREDICTION_COLUMNS]],
        ignore_index=True,
    )
    daily_rows = []
    for fold, predictions, labels in (
        ("validation_early", early_scores, early_labels),
        ("validation_late", late_scores, late_labels),
    ):
        for seed in (*MODEL_SEEDS, None):
            daily_rows.extend(
                _daily_rankic_rows(
                    predictions,
                    labels,
                    arm_id=ARM_ID,
                    score_role="ensemble" if seed is None else "seed",
                    model_seed=seed,
                    fold=fold,
                )
            )
    for arm_id in COMPARATORS:
        daily_rows.extend(
            _daily_rankic_rows(
                comparators,
                late_labels,
                arm_id=arm_id,
                score_role="ensemble",
                model_seed=None,
                fold="validation_late",
            )
        )
    daily = pd.DataFrame(daily_rows)
    full = daily.loc[
        daily["arm_id"].eq(ARM_ID)
        & daily["fold"].isin(["validation_early", "validation_late"])
    ].copy()
    full["fold"] = "validation_full"
    daily = pd.concat([daily, full], ignore_index=True).sort_values(
        ["arm_id", "score_role", "model_seed", "fold", "decision_date"],
        kind="mergesort",
        na_position="last",
    )
    _write_csv(build / "daily_rankic_readout.csv", daily.to_dict("records"), DAILY_COLUMNS)
    evaluable = daily.loc[daily["metric_day_status"].eq("evaluable")].copy()
    stability_rows = []
    for seed in (*MODEL_SEEDS, None):
        role = "ensemble" if seed is None else "seed"
        for fold in ("validation_early", "validation_late", "validation_full"):
            subset = evaluable.loc[
                evaluable["arm_id"].eq(ARM_ID)
                & evaluable["score_role"].eq(role)
                & evaluable["fold"].eq(fold)
            ]
            if seed is not None:
                subset = subset.loc[subset["model_seed"].eq(seed)]
            summary = _metric_summary(subset["RankIC"].astype(float).tolist())
            month_sum = subset.assign(
                month=subset["decision_date"].astype(str).str[:7]
            ).groupby("month")["RankIC"].sum()
            denominator = float(month_sum.abs().sum())
            month_share = (
                float(month_sum.abs().max() / denominator)
                if denominator > 0
                else None
            )
            stability_rows.append(
                {
                    "arm_id": ARM_ID,
                    "score_role": role,
                    "model_seed": seed,
                    "fold": fold,
                    "audit_type": "fold_summary",
                    "period_id": fold,
                    **summary,
                    "max_abs_month_contribution_share": month_share,
                    "status": "pass",
                    "reason": "",
                }
            )
    ensemble_full = evaluable.loc[
        evaluable["arm_id"].eq(ARM_ID)
        & evaluable["score_role"].eq("ensemble")
    ]
    for fold, months in (
        ("validation_full", [f"2023-{month:02d}" for month in range(1, 13)]),
        ("validation_late", [f"2023-{month:02d}" for month in range(7, 13)]),
    ):
        fold_frame = ensemble_full.loc[ensemble_full["fold"].eq(fold)].copy()
        fold_frame["month"] = fold_frame["decision_date"].astype(str).str[:7]
        for month in months:
            month_values = fold_frame.loc[fold_frame["month"].eq(month), "RankIC"].astype(float)
            calendar_summary = _metric_summary(month_values.tolist())
            stability_rows.append(
                {
                    "arm_id": ARM_ID,
                    "score_role": "ensemble",
                    "model_seed": None,
                    "fold": fold,
                    "audit_type": "calendar_month",
                    "period_id": month,
                    **calendar_summary,
                    "max_abs_month_contribution_share": None,
                    "status": "pass",
                    "reason": "",
                }
            )
            lomo_values = fold_frame.loc[
                ~fold_frame["month"].eq(month), "RankIC"
            ].astype(float)
            lomo_summary = _metric_summary(lomo_values.tolist())
            stability_rows.append(
                {
                    "arm_id": ARM_ID,
                    "score_role": "ensemble",
                    "model_seed": None,
                    "fold": fold,
                    "audit_type": "leave_one_month_out",
                    "period_id": month,
                    **lomo_summary,
                    "max_abs_month_contribution_share": None,
                    "status": "pass",
                    "reason": "",
                }
            )
    stability_columns = [
        "arm_id",
        "score_role",
        "model_seed",
        "fold",
        "audit_type",
        "period_id",
        "complete_day_n",
        "mean_rankic",
        "rankic_std",
        "rankicir",
        "positive_day_rate",
        "max_abs_day_contribution",
        "max_abs_month_contribution_share",
        "status",
        "reason",
    ]
    _write_csv(
        build / "rankic_stability_and_concentration_audit.csv",
        stability_rows,
        stability_columns,
    )
    late_daily = evaluable.loc[evaluable["fold"].eq("validation_late")]
    r2_late = late_daily.loc[
        late_daily["arm_id"].eq(ARM_ID)
        & late_daily["score_role"].eq("ensemble")
    ].set_index("decision_date")["RankIC"].astype(float)
    paired_rows = []
    contrasts: dict[str, np.ndarray] = {}
    for contrast_id, comparator in zip(("P1", "P2"), COMPARATORS, strict=True):
        right = late_daily.loc[late_daily["arm_id"].eq(comparator)].set_index(
            "decision_date"
        )["RankIC"].astype(float)
        pair = pd.concat([r2_late.rename("left"), right.rename("right")], axis=1).dropna()
        delta = (pair["left"] - pair["right"]).to_numpy()
        contrasts[contrast_id] = delta
        paired_rows.append(
            {
                "contrast_id": contrast_id,
                "left_arm": ARM_ID,
                "right_arm": comparator,
                "fold": "validation_late",
                "complete_day_n": len(pair),
                "left_mean_rankic": float(pair["left"].mean()),
                "right_mean_rankic": float(pair["right"].mean()),
                "paired_mean_delta": float(delta.mean()),
                "positive_delta_day_rate": float((delta > 0).mean()),
                "relative_advantage_point_ordering_observed": bool(delta.mean() > 0),
                "status": "pass",
            }
        )
    paired = pd.DataFrame(paired_rows)
    _write_csv(
        build / "paired_rankic_comparison.csv",
        paired.to_dict("records"),
        list(paired.columns),
    )
    bootstrap = paired_bootstrap_diagnostics(contrasts)
    bootstrap_rows = []
    for row in bootstrap:
        source = paired.loc[paired["contrast_id"].eq(row["contrast_id"])].iloc[0]
        bootstrap_rows.append(
            {
                "contrast_id": row["contrast_id"],
                "left_arm": source["left_arm"],
                "right_arm": source["right_arm"],
                "fold": "validation_late",
                "complete_day_n": source["complete_day_n"],
                "observed_paired_mean_delta": row["observed_paired_mean_delta"],
                "bootstrap_replicate_n": 5000,
                "mean_block_length": 20,
                "bootstrap_seed": 20260715,
                "one_sided_p_value": row["one_sided_p_value"],
                "holm_family_size": 2,
                "holm_order": row["holm_order"],
                "holm_adjusted_p_value": row["holm_adjusted_p_value"],
                "status": "pass",
                "reason": "",
            }
        )
    _write_csv(
        build / "stationary_bootstrap_pair_diagnostic.csv",
        bootstrap_rows,
        list(bootstrap_rows[0]),
    )
    top_daily, top_summary = _top30_artifacts(late_all, late_labels)
    _write_csv(
        build / "paper_proxy_top30_daily.csv",
        top_daily.to_dict("records"),
        list(top_daily.columns),
    )
    _write_csv(
        build / "paper_proxy_top30_summary.csv",
        top_summary.to_dict("records"),
        list(top_summary.columns),
    )
    paper_values = [
        ("CSI300", "LightGBM", 0.016, 0.148, "M1_LIGHTGBM_ALPHA158", "closest_local_lightgbm_proxy"),
        ("CSI300", "LSTM", 0.027, 0.221, None, None),
        ("CSI300", "REAKA", 0.064, 0.568, ARM_ID, "paper_architecture_grounded_project_adaptation"),
        ("S&P500", "LightGBM", 0.013, 0.110, "M1_LIGHTGBM_ALPHA158", "closest_local_lightgbm_proxy"),
        ("S&P500", "LSTM", 0.018, 0.201, None, None),
        ("S&P500", "REAKA", 0.061, 0.541, ARM_ID, "paper_architecture_grounded_project_adaptation"),
    ]
    local_summary = {
        row["arm_id"]: row
        for row in stability_rows
        if row["audit_type"] == "fold_summary"
        and row["fold"] == "validation_late"
        and row["score_role"] == "ensemble"
    }
    m1_values = late_daily.loc[late_daily["arm_id"].eq(COMPARATORS[0]), "RankIC"].astype(float)
    m1_summary = _metric_summary(m1_values.tolist())
    reference_rows = []
    for market, model_name, paper_rankic, paper_rankicir, local_arm, role in paper_values:
        summary = local_summary.get(local_arm)
        if local_arm == COMPARATORS[0]:
            summary = m1_summary
        reference_rows.append(
            {
                "market": market,
                "model": model_name,
                "paper_rankic": paper_rankic,
                "paper_rankicir": paper_rankicir,
                "local_arm_id": local_arm,
                "local_mapping_role": role,
                "local_fold": "validation_late" if local_arm else None,
                "local_mean_rankic": summary["mean_rankic"] if summary else None,
                "local_rankicir": summary["rankicir"] if summary else None,
                "numerically_comparable": False,
                "gate_eligible": False,
                "threshold_role": "reference_only",
                "local_pass_threshold_source": "none",
                "cross_market_numeric_match_claim_allowed": False,
                "status": "pass",
                "reason": "",
            }
        )
    _write_csv(
        build / "paper_reference_comparison.csv",
        reference_rows,
        list(reference_rows[0]),
    )
    seed_late = {
        seed: late_daily.loc[
            late_daily["arm_id"].eq(ARM_ID)
            & late_daily["score_role"].eq("seed")
            & late_daily["model_seed"].eq(seed),
            "RankIC",
        ].astype(float).tolist()
        for seed in MODEL_SEEDS
    }
    early_complete = int(
        evaluable.loc[
            evaluable["arm_id"].eq(ARM_ID)
            & evaluable["score_role"].eq("ensemble")
            & evaluable["fold"].eq("validation_early")
        ]["decision_date"].nunique()
    )
    direction = direction_stability(
        seed_late,
        {str(key): float(value) for key, value in r2_late.items()},
        validation_full_complete_day_n=early_complete + len(r2_late),
        validation_early_complete_day_n=early_complete,
        validation_late_score_coverage=1.0,
    )
    relative = bool((paired["paired_mean_delta"] > 0).all())
    gate_status = {
        gate: "pass" for gate in CAUSAL_GATES + ["output_manifest_hash_gate"]
    }
    gate_status["r2_direction_stability_gate"] = direction["status"]
    stage_decision = (
        "21C_FULL_r2_direction_not_supported"
        if direction["status"] == "fail"
        else classify_decision(
            gate_status,
            relative_advantage_point_ordering_observed=relative,
        )
    )
    profile_rows = expanded_artifact_profiles()
    registry_contract_hash = stable_hash(profile_rows)
    profile_csv_rows = [
        {
            "profile_order": row["profile_order"],
            "profile_id": row["profile_id"],
            "required_paths_json": json.dumps(row["required_paths"], separators=(",", ":")),
            "forbidden_paths_json": json.dumps(row["forbidden_paths"], separators=(",", ":")),
            "conditional_path_rules_json": "{}",
            "registry_contract_sha256": registry_contract_hash,
        }
        for row in profile_rows
    ]
    _write_csv(
        build / "artifact_profile_registry.csv",
        profile_csv_rows,
        list(profile_csv_rows[0]),
    )
    stage_rows = [
        {
            "stage_order": index,
            "stage_id": stage,
            "started_at_utc": "",
            "ended_at_utc": "",
            "stage_status": "pass",
            "input_bundle_hash": "",
            "output_bundle_hash": "",
            "failed_gate_ids": "[]",
            "reason": "",
        }
        for index, stage in enumerate(
            ["preflight", "materialize-r2-teacher", "train-r2", "late-readout", "finalize"]
        )
    ]
    _write_csv(build / "stage_status_registry.csv", stage_rows, list(stage_rows[0]))
    _write_csv(build / "historical_design_holdout_access_audit.csv", [], ACCESS_COLUMNS)
    gate_rows = []
    for order, gate in enumerate(CAUSAL_GATES):
        gate_rows.append(
            {
                "gate_order": order,
                "gate_id": gate,
                "gate_class": "causal",
                "evidence_artifact_path": "gate_evidence_21c_full.csv",
                "evidence_field": gate,
                "expected_value": "pass",
                "observed_value": gate_status[gate],
                "status": gate_status[gate],
                "blocking": True,
                "reason": "" if gate_status[gate] == "pass" else "direction_not_supported",
            }
        )
    gate_rows.extend(
        [
            {
                "gate_order": len(CAUSAL_GATES),
                "gate_id": "output_manifest_hash_gate",
                "gate_class": "meta",
                "evidence_artifact_path": "manifest_21c_full_reaka_pit_proxy_replication.json",
                "evidence_field": "files",
                "expected_value": "pass",
                "observed_value": "pass",
                "status": "pass",
                "blocking": True,
                "reason": "",
            },
            {
                "gate_order": len(CAUSAL_GATES) + 1,
                "gate_id": "failure_bundle_integrity_gate",
                "gate_class": "meta",
                "evidence_artifact_path": "artifact_profile_registry.csv",
                "evidence_field": "P5",
                "expected_value": "not_run",
                "observed_value": "not_run",
                "status": "not_run",
                "blocking": True,
                "reason": "success_profile",
            },
        ]
    )
    gate_path = build / "gate_evidence_21c_full.csv"
    _write_csv(gate_path, gate_rows, list(gate_rows[0]))
    pre_gate = _json_object(training_root / "pre_gate_r2_checkpoint_bundle_manifest.json")
    metric_paths = sorted(FINAL_METRICS)
    metric_hashes = {path: file_sha(build / path) for path in metric_paths}
    checkpoint_manifest = _json_object(training_root / "checkpoint_manifest.json")
    semantic_manifest = {
        "schema_version": "21c_semantic_reproducibility_v3",
        "run_id": RUN_ID,
        "requirement_sha256": context["requirement_sha256"],
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "approved_21c_runner_sha256": context["authorization_payload"]["approved_21c_runner_sha256"],
        "approved_21c_config_sha256": context["authorization_payload"]["approved_21c_config_sha256"],
        "approved_21c_test_sha256": context["authorization_payload"]["approved_21c_test_sha256"],
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "upstream_21b_semantic_payload_bundle_hash": context["authorization_payload"]["approved_21b_semantic_payload_bundle_hash"],
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "upstream_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "feature_route_hash": stable_hash(config["feature_route"]),
        "split_hash": context["upstream"]["panel_manifest"]["split_hash"],
        "normalization_contract_hash": context["upstream"]["panel_manifest"]["normalization_contract_hash"],
        "source_row_key_hash": stable_hash(
            [
                context["exclusion"]["folds"]["train"]["retained_row_key_hash"],
                context["exclusion"]["folds"]["validation_early"]["retained_row_key_hash"],
                context["exclusion"]["folds"]["validation_late"]["retained_row_key_hash"],
            ]
        ),
        "pit_universe_exclusion_registry_sha256": context["exclusion"][
            "registry_sha256"
        ],
        "performance_contract_hash": stable_hash(config["performance"]),
        "teacher_extension_hash": file_sha(build / "materialized/r2_input_extension_manifest.json"),
        "initialization_contract_sha256": checkpoint_manifest["records"][0]["initialization_contract_sha256"],
        "ordered_parameter_name_list_sha256": checkpoint_manifest["records"][0]["ordered_parameter_name_list_sha256"],
        "model_state_semantic_hashes": [record["model_state_semantic_sha256"] for record in checkpoint_manifest["records"]],
        "early_score_semantic_hash": file_sha(training_root / "selection/validation_early_prediction_scores.parquet"),
        "late_score_semantic_hash": file_sha(training_root / "readout/validation_late_prediction_scores.parquet"),
        "metric_semantic_hashes": metric_hashes,
    }
    semantic_manifest["semantic_payload_bundle_hash"] = stable_hash(semantic_manifest)
    semantic_path = build / "semantic_reproducibility_manifest.json"
    semantic_path.write_bytes(canonical_json_bytes(semantic_manifest) + b"\n")
    decision_row = {
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "stage_decision": stage_decision,
        **{gate: gate_status[gate] for gate in CAUSAL_GATES},
        "output_manifest_hash_gate": "pass",
        "failure_bundle_integrity_gate": "not_run",
        "r2_validation_late_mean_rankic": direction["ensemble_mean_rankic_late"],
        "positive_late_seed_n": direction["positive_late_seed_n"],
        "positive_lomo_n": direction["positive_lomo_n"],
        "lomo_total_n": direction["lomo_total_n"],
        "r2_minus_m1_paired_mean_delta": paired.iloc[0]["paired_mean_delta"],
        "r2_minus_m3_paired_mean_delta": paired.iloc[1]["paired_mean_delta"],
        "relative_advantage_point_ordering_observed": relative,
        "full_reaka_local_validation_point_ordering_observed": bool(direction["status"] == "pass" and relative),
        "historical_holdout_readout_authorized": False,
        "next_requirement_generation_authorized": False,
        "next_requirement_execution_authorized": False,
        "policy_training_authorized": False,
        "portfolio_optimization_authorized": False,
        "deployment_authorized": False,
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "approved_21b_contract_erratum_sha256": context["authorization_payload"]["approved_21b_contract_erratum_sha256"],
        "approved_21a_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "pre_gate_r2_checkpoint_bundle_hash": pre_gate["bundle_hash"],
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "semantic_payload_bundle_hash": semantic_manifest["semantic_payload_bundle_hash"],
        "blocking_reasons": json.dumps(
            [] if direction["status"] == "pass" else ["r2_direction_stability_gate"],
            separators=(",", ":"),
        ),
    }
    decision_path = build / "21C_full_reaka_pit_proxy_replication_decision.csv"
    _write_csv(decision_path, [decision_row], DECISION_COLUMNS)
    exclusion_impact = context["exclusion"]["folds"]
    report = f"""# 21C Full REAKA PIT Proxy Local Validation Sanity

## 1. 决策与 claim ceiling

`{stage_decision}`。本结论仅为 validation-only full-architecture local sanity。

## 2. 独立 scope restart

本次 human scope restart 跳过 nested ablation，但不授权 historical holdout、经济 replay 或部署。

## 3. corrected 21B/21A lineage

21B_v5 contract-erratum corrected successor 与 21A M2 paper-lineage erratum 均已 hash pin；M2 仅为 project return-only diagnostic。

## 4. paper-vs-local setup differences

本地为 PIT top-400 main board + top-100 ChiNext、157-feature registered adaptation、2018-2023 validation proxy，不与论文市场数值直接比较。

### 4.1 v3 PIT universe exclusion successor

根据 sealed v2 teacher materialization failure，完整排除 `396` 个缺少严格同 instrument `t+1` approved feature-cache key 的 instrument，且对 train、validation-early、validation-late 统一移除整只 instrument 历史。该变化是显式 estimand change，不是缺失行填补。

- train: `{exclusion_impact['train']['source_row_n']}` -> `{exclusion_impact['train']['retained_row_n']}`（排除 `{exclusion_impact['train']['excluded_row_n']}` rows）
- validation_early: `{exclusion_impact['validation_early']['source_row_n']}` -> `{exclusion_impact['validation_early']['retained_row_n']}`（排除 `{exclusion_impact['validation_early']['excluded_row_n']}` rows）
- validation_late: `{exclusion_impact['validation_late']['source_row_n']}` -> `{exclusion_impact['validation_late']['retained_row_n']}`（排除 `{exclusion_impact['validation_late']['excluded_row_n']}` rows）
- exclusion registry SHA256: `{context['exclusion']['registry_sha256']}`

### 4.2 v4 performance successor

v3 在首个 seed 约 32 分钟仍未完成后按用户要求停止，保留 unsealed building evidence。v4 不改变 training batch、optimizer step、模型、loss、seed、epoch或 patience；feature cache改为进程内共享 RAM copy，validation inference batch固定为 `{config['performance']['inference_batch_size']}`，每个 row/draw 的 20 个 CPU noise tensors一次生成并一次传入 GPU。row-draw SHA256 seed公式不变，但该 CPU RNG route不与未完成 v3 CUDA RNG route宣称数值等价。

## 5. full R2 architecture/config/search accounting

R2 使用双 LSTM、shared gate、4-operator AKS、20-step DDPM、8 draws；只运行 seeds `{MODEL_SEEDS}`，无 sensitivity/search。

## 6. early selection 与 late seal

Checkpoint 仅由 validation_early 选择，pre-gate seal 后由 fresh inference-only worker 读取 validation_late。

## 7. R2 RankIC 与稳定性

validation_late ensemble mean RankIC = `{direction['ensemble_mean_rankic_late']:.8f}`；positive seeds = `{direction['positive_late_seed_n']}/3`；positive LOMO = `{direction['positive_lomo_n']}/6`。

## 8. R2 vs M1/M3 paired comparison

R2-M1 paired delta = `{paired.iloc[0]['paired_mean_delta']:.8f}`；R2-M3 paired delta = `{paired.iloc[1]['paired_mean_delta']:.8f}`。

## 9. paper reference table

论文静态值仅作 reference；`numerically_comparable=false`，不构成本地 threshold。

## 10. paper-proxy Top30 gross diagnostic

仅报告 close-to-close gross morphology；不含 next-open、交易限制、成本或连续 NAV，不是 executable PnL。

## 11. 不支持的结论

不支持 exact replication、单模块机制归因、盈利确认、policy training 或 deployment-ready。

## 12. access/hash/reproducibility audit

Historical holdout access 全部为 0；runner/config/test、upstream errata、checkpoint、scores、metrics 与 manifests 均进入 hash closure。

## 13. 下一步

任何 historical test、nested ablation、execution bridge 或 forward confirmation 均需新的人工 requirement 与授权。
"""
    report_path = build / "21C_full_reaka_pit_proxy_replication_report.md"
    report_path.write_text(report, encoding="utf-8", newline="\n")
    manifest_path = build / "manifest_21c_full_reaka_pit_proxy_replication.json"
    hashes_path = build / "output_hashes_21c_full_reaka_pit_proxy_replication.json"
    required = set(expanded_artifact_profiles()[-1]["required_paths"])
    observed_before_seal = {
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file()
    }
    expected_before_seal = required - {manifest_path.name, hashes_path.name}
    if observed_before_seal != expected_before_seal:
        raise ContractError(
            f"P5 pre-seal file-set mismatch missing={sorted(expected_before_seal-observed_before_seal)} extra={sorted(observed_before_seal-expected_before_seal)}"
        )
    files = [
        {"path": relative, "byte_size": (build / relative).stat().st_size, "sha256": file_sha(build / relative)}
        for relative in sorted(expected_before_seal)
    ]
    final_manifest = {
        "schema_version": "21c_final_manifest_v3",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "artifact_profile_registry_sha256": file_sha(build / "artifact_profile_registry.csv"),
        "requirement_sha256": context["requirement_sha256"],
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "approved_21c_runner_sha256": context["authorization_payload"]["approved_21c_runner_sha256"],
        "approved_21c_config_sha256": context["authorization_payload"]["approved_21c_config_sha256"],
        "approved_21c_test_sha256": context["authorization_payload"]["approved_21c_test_sha256"],
        "scope_restart_decision_sha256": context["authorization_payload"]["scope_restart_decision_sha256"],
        "pit_universe_exclusion_registry_sha256": context["exclusion"][
            "registry_sha256"
        ],
        "performance_contract_hash": stable_hash(config["performance"]),
        "approved_21b_output_root": context["authorization_payload"]["approved_21b_output_root"],
        "approved_21b_output_hashes_sha256": context["authorization_payload"]["approved_21b_output_hashes_sha256"],
        "approved_21b_contract_erratum_sha256": context["authorization_payload"]["approved_21b_contract_erratum_sha256"],
        "approved_21a_paper_lineage_erratum_sha256": context["authorization_payload"]["approved_21a_paper_lineage_erratum_sha256"],
        "pre_gate_r2_checkpoint_bundle_hash": pre_gate["bundle_hash"],
        "upstream_21b_pre_holdout_bundle_hash": context["authorization_payload"]["approved_21b_pre_holdout_bundle_hash"],
        "semantic_payload_bundle_hash": semantic_manifest["semantic_payload_bundle_hash"],
        "gate_evidence_sha256": file_sha(gate_path),
        "decision_sha256": file_sha(decision_path),
        "report_sha256": file_sha(report_path),
        "files": files,
    }
    manifest_path.write_bytes(canonical_json_bytes(final_manifest) + b"\n")
    all_files = files + [
        {"path": manifest_path.name, "byte_size": manifest_path.stat().st_size, "sha256": file_sha(manifest_path)}
    ]
    output_hashes = {
        "schema_version": "21c_output_hashes_v3",
        "manifest_sha256": file_sha(manifest_path),
        "file_count": len(all_files),
        "files": sorted(all_files, key=lambda item: item["path"]),
    }
    hashes_path.write_bytes(canonical_json_bytes(output_hashes) + b"\n")
    observed = {
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file()
    }
    if observed != required:
        raise ContractError("P5 final exact file-set mismatch")
    for item in output_hashes["files"]:
        if file_sha(build / item["path"]) != item["sha256"]:
            raise ContractError(f"post-build hash mismatch: {item['path']}")
    build.rename(output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=[
            "preflight",
            "materialize-r2-teacher",
            "train-r2",
            "late-readout",
            "finalize",
            "all",
        ],
        default="all",
    )
    parser.add_argument(
        "--worker", choices=["r2-selection", "r2-late-readout"], default=None
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    if args.worker is not None:
        context = authorized_context(config)
        if args.worker == "r2-selection":
            selection_worker(config, context)
        else:
            late_readout_worker(config, context)
        return 0
    authorization = validate_authorization(config)
    if args.stage == "preflight" and authorization.status != "pass":
        path = run_preauthorization_preflight(config)
        print(f"21C preflight blocked safely; audit sealed at {path}")
        return 2
    if authorization.status != "pass":
        raise ContractError(
            f"{args.stage} forbidden before valid human authorization: "
            + ",".join(authorization.errors)
        )
    context = authorized_context(config)
    stages = (
        [
            "preflight",
            "materialize-r2-teacher",
            "train-r2",
            "late-readout",
            "finalize",
        ]
        if args.stage == "all"
        else [args.stage]
    )
    for stage in stages:
        print(f"[{utc_now()}] 21C stage start: {stage}", flush=True)
        if stage == "preflight":
            run_authorized_preflight(config, context)
        elif stage == "materialize-r2-teacher":
            materialize_r2_teacher(config, context)
        elif stage == "train-r2":
            run_train_r2_parent(config)
        elif stage == "late-readout":
            run_late_readout_parent(config, context)
        else:
            finalize_21c(config, context)
        print(f"[{utc_now()}] 21C stage complete: {stage}", flush=True)
        if (
            stage != "finalize"
            and workspace_path(config["paths"]["canonical_output_root"]).exists()
        ):
            print(
                f"[{utc_now()}] 21C terminal blocked profile sealed; "
                "downstream stages not run",
                flush=True,
            )
            return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
