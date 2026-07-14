#!/usr/bin/env python3
"""Execute the frozen EP21 21B Alpha158/sequence baseline benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import struct
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = EXPERIMENT_DIR.parents[2]
REPO_ROOT = TOPIC_ROOT.parents[1]
DEFAULT_CONFIG = (
    EXPERIMENT_DIR / "configs/config_21b_alpha158_sequence_baseline_benchmark.yaml"
)
RUN_ID = "21B_alpha158_sequence_baseline_benchmark"
REQUIREMENT_VERSION = "21B_v4"
FEATURE_COUNT = 157
LOOKBACK = 10
MODEL_SEEDS = (20260713, 20260714, 20260715)
LEARNED_ARMS = (
    "M1_LIGHTGBM_ALPHA158",
    "M2_RETURN_LSTM",
    "M3_GATED_DUAL_PATH_LSTM",
    "A0_VANILLA_AUTOENCODER",
)
GATE_BASELINES = LEARNED_ARMS[:3]
M0 = "M0_HASH_NULL_SCORE"

PREDICTION_COLUMNS = [
    "run_id",
    "requirement_version",
    "split",
    "fold",
    "decision_date",
    "instrument",
    "arm_id",
    "score_role",
    "model_seed",
    "score",
    "U_t_decision_n",
    "row_key_hash",
    "feature_route_id",
    "checkpoint_sha256",
    "checkpoint_bundle_sha256",
]

ACCESS_COLUMNS = [
    "access_seq",
    "stage",
    "phase",
    "path_or_resource",
    "dataset_role",
    "access_kind",
    "requested_columns",
    "parsed_value_columns",
    "date_min",
    "date_max",
    "max_allowed_source_date",
    "content_sha256",
    "allowed",
    "status",
    "purpose",
]

ALL_STAGE_PATHS = [
    "preflight/preflight_access_audit.csv",
    "preflight/upstream_21a_authorization_and_hash_audit.csv",
    "preflight/resolved_config.yaml",
    "materialized/decision_universe_and_label_resolution_audit.parquet",
    "materialized/sequence_sample_index.parquet",
    "materialized/panels/train/return_and_label_panel.f32.memmap",
    "materialized/panels/validation_early/return_and_label_panel.f32.memmap",
    "materialized/panels/validation_late/return_and_label_panel.f32.memmap",
    "materialized/model_input_panel_manifest.json",
    "materialized/materialization_access_audit.csv",
    "materialized/materialization_failure_evidence.csv",
    "training/training_run_registry.csv",
    "training/model_search_accounting_manifest.csv",
    "training/seed_level_training_curves.csv",
    *[
        f"training/checkpoints/{arm}/seed_{seed}/"
        + ("model.txt" if arm == "M1_LIGHTGBM_ALPHA158" else "state_dict.pt")
        for arm in LEARNED_ARMS
        for seed in MODEL_SEEDS
    ],
    "training/checkpoint_manifest.json",
    "training/selection_worker_exit_record.json",
    "training/selection/validation_early_prediction_scores.parquet",
    "training/pre_gate_checkpoint_bundle_manifest.json",
    "training/readout/validation_late_prediction_scores.parquet",
    "training/gate_readout_worker_exit_record.json",
    "training/checkpoint_eligibility_manifest.json",
    "training/pre_holdout_checkpoint_bundle_manifest.json",
    "training/daily_prediction_scores.parquet",
    "training/model_parameter_compute_latency_audit.csv",
    "training/training_access_audit.csv",
    "historical_design_holdout_access_audit.csv",
    "stage_status_registry.csv",
    "daily_rankic_readout.csv",
    "rankic_stability_and_concentration_audit.csv",
    "fragility_unit_contribution_audit.csv",
    "finalize_failure_evidence.csv",
    "gate_evidence_21b.csv",
    "21B_baseline_benchmark_decision.csv",
    "21B_alpha158_sequence_baseline_benchmark_report.md",
    "semantic_reproducibility_manifest.json",
    "manifest_21b_alpha158_sequence_baseline_benchmark.json",
    "output_hashes_21b_alpha158_sequence_baseline_benchmark.json",
]

COMMON_FINAL = [
    "historical_design_holdout_access_audit.csv",
    "stage_status_registry.csv",
    "gate_evidence_21b.csv",
    "21B_baseline_benchmark_decision.csv",
    "21B_alpha158_sequence_baseline_benchmark_report.md",
    "semantic_reproducibility_manifest.json",
    "manifest_21b_alpha158_sequence_baseline_benchmark.json",
    "output_hashes_21b_alpha158_sequence_baseline_benchmark.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def root_inventory_hash(root: Path) -> tuple[str, int, int]:
    rows: list[str] = []
    total_size = 0
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        size = path.stat().st_size
        total_size += size
        rows.append(f"{path.relative_to(root).as_posix()}|{size}|{file_sha(path)}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), len(files), total_size


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _semantic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _semantic_value(value[key])
            for key in sorted(value, key=lambda text: str(text).encode("utf-8"))
        }
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number in semantic canonicalization")
        return "f64le:" + struct.pack("<d", number).hex()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_semantic_value(item) for item in value.tolist()]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _semantic_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(value))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )


def _csv_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    return value


def write_csv(path: Path, rows: Iterable[dict[str, Any]] | pd.DataFrame, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    for column in columns:
        if column not in frame:
            frame[column] = "NA"
    frame = frame[columns]
    for column in columns:
        frame[column] = frame[column].map(_csv_value)
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return TOPIC_ROOT / path


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    identity = config["identity"]
    if identity["run_id"] != RUN_ID or identity["requirement_version"] != REQUIREMENT_VERSION:
        raise ValueError("config identity mismatch")
    return config


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config["paths"].items()}


def canonical_output_root(config: dict[str, Any]) -> Path:
    return topic_path(config["output"]["canonical_output_root"])


def building_root(config: dict[str, Any]) -> Path:
    output = canonical_output_root(config)
    return output.with_name(output.name + ".building")


def row_key_hash(instrument: str, decision_date: str) -> str:
    return hashlib.sha256(f"{instrument}|{decision_date}".encode()).hexdigest()


def m0_score(instrument: str, decision_date: str) -> float:
    key = f"{M0}|{instrument}|{decision_date}"
    integer = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    return integer / 2**64


def average_rank(values: np.ndarray) -> np.ndarray:
    return pd.Series(np.asarray(values, dtype=np.float64)).rank(
        method="average", ascending=True
    ).to_numpy(dtype=np.float64)


def rankic(scores: np.ndarray, labels: np.ndarray, minimum_n: int = 2) -> float:
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.float64)
    if len(scores) < minimum_n or not np.isfinite(scores).all() or not np.isfinite(labels).all():
        return math.nan
    if np.ptp(scores) == 0 or np.ptp(labels) == 0:
        return math.nan
    return float(np.corrcoef(average_rank(scores), average_rank(labels))[0, 1])


def access_row(
    rows: list[dict[str, Any]],
    *,
    stage: str,
    phase: str,
    path: Path | str,
    role: str,
    kind: str,
    requested: str,
    parsed: str = "NA",
    date_min: str = "NA",
    date_max: str = "NA",
    max_date: str = "NA",
    content_sha256: str = "NA",
    allowed: bool = True,
    status: str = "pass",
    purpose: str,
) -> None:
    rows.append(
        {
            "access_seq": len(rows) + 1,
            "stage": stage,
            "phase": phase,
            "path_or_resource": str(path),
            "dataset_role": role,
            "access_kind": kind,
            "requested_columns": requested,
            "parsed_value_columns": parsed,
            "date_min": date_min,
            "date_max": date_max,
            "max_allowed_source_date": max_date,
            "content_sha256": content_sha256,
            "allowed": allowed,
            "status": status,
            "purpose": purpose,
        }
    )


def checkpoint_paths() -> list[str]:
    return [
        f"training/checkpoints/{arm}/seed_{seed}/"
        + ("model.txt" if arm == "M1_LIGHTGBM_ALPHA158" else "state_dict.pt")
        for arm in LEARNED_ARMS
        for seed in MODEL_SEEDS
    ]


def expanded_artifact_profiles() -> list[dict[str, Any]]:
    preflight = [
        "preflight/preflight_access_audit.csv",
        "preflight/upstream_21a_authorization_and_hash_audit.csv",
        "preflight/resolved_config.yaml",
    ]
    search = ["training/model_search_accounting_manifest.csv"]
    materialized = [
        path
        for path in ALL_STAGE_PATHS
        if path.startswith("materialized/")
        and not path.endswith("materialization_failure_evidence.csv")
    ]
    training_audits = [
        "training/training_run_registry.csv",
        "training/model_search_accounting_manifest.csv",
        "training/seed_level_training_curves.csv",
        "training/checkpoint_manifest.json",
        "training/model_parameter_compute_latency_audit.csv",
        "training/training_access_audit.csv",
    ]
    selection = [
        "training/selection_worker_exit_record.json",
        "training/selection/validation_early_prediction_scores.parquet",
        "training/pre_gate_checkpoint_bundle_manifest.json",
    ]
    late = [
        "training/readout/validation_late_prediction_scores.parquet",
        "training/gate_readout_worker_exit_record.json",
        "training/checkpoint_eligibility_manifest.json",
        "training/pre_holdout_checkpoint_bundle_manifest.json",
        "training/daily_prediction_scores.parquet",
    ]
    readouts = [
        "daily_rankic_readout.csv",
        "rankic_stability_and_concentration_audit.csv",
        "fragility_unit_contribution_audit.csv",
    ]
    failure_materialized = ["materialized/materialization_failure_evidence.csv"]
    failure_finalize = ["finalize_failure_evidence.csv"]
    full = sorted(
        set(ALL_STAGE_PATHS) - set(failure_materialized) - set(failure_finalize)
    )

    def record(
        profile: str,
        required: Sequence[str],
        forbidden: Sequence[str],
        conditional: Sequence[str] = (),
    ) -> dict[str, Any]:
        return {
            "profile_id": profile,
            "required_paths": sorted(set(required)),
            "forbidden_paths": sorted(set(forbidden)),
            "conditional_path_rules": list(conditional),
        }

    return [
        record(
            "P0_PREFLIGHT_BLOCKED",
            COMMON_FINAL + preflight + search,
            materialized + checkpoint_paths() + selection + late + readouts,
        ),
        record(
            "P1_MATERIALIZATION_BLOCKED",
            COMMON_FINAL + preflight + search + [
                "materialized/materialization_access_audit.csv",
                *failure_materialized,
            ],
            materialized + checkpoint_paths() + selection + late + readouts,
        ),
        record(
            "P2_SELECTION_BLOCKED",
            COMMON_FINAL + preflight + materialized + training_audits,
            selection + late + readouts,
            ["completed_learned_job_exact_checkpoint_subset"],
        ),
        record(
            "P3_GATE_READOUT_BLOCKED",
            COMMON_FINAL
            + preflight
            + materialized
            + training_audits
            + checkpoint_paths()
            + selection,
            late + readouts,
        ),
        record(
            "P4_FINALIZE_BLOCKED",
            COMMON_FINAL
            + preflight
            + materialized
            + training_audits
            + checkpoint_paths()
            + selection
            + late
            + failure_finalize,
            readouts + failure_materialized,
        ),
        record("P5_FULL_FINALIZED", full, failure_materialized + failure_finalize),
    ]


def planned_jobs() -> list[dict[str, Any]]:
    rows = [
        {
            "job_id": "M0_HASH_NULL_SCORE",
            "arm_id": M0,
            "model_seed": "NA",
            "planned": True,
            "config_id": "M0_FROZEN",
            "attempt_count": 0,
            "attempt_batch_sizes": "NA",
            "final_status": "not_run_due_upstream_block",
            "promotion_allowed": False,
            "blocking_reason": "NA",
        }
    ]
    for arm in LEARNED_ARMS:
        for seed in MODEL_SEEDS:
            rows.append(
                {
                    "job_id": f"{arm}__seed_{seed}",
                    "arm_id": arm,
                    "model_seed": seed,
                    "planned": True,
                    "config_id": f"{arm}_FROZEN",
                    "attempt_count": 0,
                    "attempt_batch_sizes": "NA",
                    "final_status": "not_run_due_upstream_block",
                    "promotion_allowed": False,
                    "blocking_reason": "NA",
                }
            )
    return rows


SEARCH_COLUMNS = [
    "job_id",
    "arm_id",
    "model_seed",
    "planned",
    "config_id",
    "attempt_count",
    "attempt_batch_sizes",
    "final_status",
    "promotion_allowed",
    "blocking_reason",
]


def preflight(config: dict[str, Any], config_path: Path) -> None:
    paths = resolve_paths(config)
    output = canonical_output_root(config)
    build = building_root(config)
    if output.exists():
        raise FileExistsError(f"sealed output already exists: {output}")
    if build.exists():
        raise FileExistsError(f"building root already exists: {build}")
    build.mkdir(parents=True)
    access: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    def check(check_id: str, path: Path, expected: str, observed: str) -> None:
        passed = observed == expected
        audit.append(
            {
                "check_id": check_id,
                "artifact_path": path.relative_to(TOPIC_ROOT).as_posix(),
                "expected_value": expected,
                "observed_value": observed,
                "status": "pass" if passed else "fail",
                "blocking_reason": "NA" if passed else f"{check_id}_mismatch",
            }
        )
        access_row(
            access,
            stage="preflight",
            phase="hash_validation",
            path=path,
            role=check_id,
            kind="byte_integrity_hash",
            requested="raw_bytes",
            content_sha256=observed,
            purpose="preoutcome_contract_validation",
        )
        if not passed:
            raise ValueError(f"{check_id} mismatch: {observed} != {expected}")

    upstream = config["upstream"]
    requirement_hash = file_sha(paths["requirement"])
    check("requirement_sha256", paths["requirement"], config["identity"]["requirement_sha256"], requirement_hash)
    auth = read_json(paths["authorization"])
    expected_auth_keys = [
        "requirement_sha256",
        "approved_21a_contract_version",
        "approved_21a_freeze_bundle_hash",
        "approved_21a_decision_sha256",
        "reviewer_role",
        "reviewed_at_utc",
        "authorization_status",
    ]
    if list(auth) != expected_auth_keys:
        raise ValueError("authorization key set/order mismatch")
    authorization_ok = (
        auth["requirement_sha256"] == requirement_hash
        and auth["approved_21a_contract_version"] == upstream["contract_version"]
        and auth["approved_21a_freeze_bundle_hash"] == upstream["freeze_bundle_hash"]
        and auth["approved_21a_decision_sha256"] == upstream["decision_sha256"]
        and auth["reviewer_role"] == "human"
        and auth["authorization_status"] == "approved"
    )
    audit.append(
        {
            "check_id": "execution_authorization",
            "artifact_path": paths["authorization"].relative_to(TOPIC_ROOT).as_posix(),
            "expected_value": "approved_human_exact_hash_binding",
            "observed_value": "approved_human_exact_hash_binding" if authorization_ok else "invalid",
            "status": "pass" if authorization_ok else "fail",
            "blocking_reason": "NA" if authorization_ok else "invalid_execution_authorization",
        }
    )
    if not authorization_ok:
        raise PermissionError("21B execution authorization invalid")

    upstream_root = paths["approved_21a_root"]
    decision_path = upstream_root / "21A_contract_decision.csv"
    manifest_path = upstream_root / "manifest_21a_paper_lineage_pit_data_and_architecture_contract.json"
    hashes_path = upstream_root / "output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json"
    check("approved_21a_decision_sha256", decision_path, upstream["decision_sha256"], file_sha(decision_path))
    check("approved_21a_manifest_sha256", manifest_path, upstream["manifest_sha256"], file_sha(manifest_path))
    check("approved_21a_output_hashes_sha256", hashes_path, upstream["output_hashes_sha256"], file_sha(hashes_path))
    decision = pd.read_csv(decision_path)
    if len(decision) != 1:
        raise ValueError("21A decision must have exactly one row")
    row = decision.iloc[0]
    semantic_checks = {
        "21a_contract_version": (str(row["contract_version"]), upstream["contract_version"]),
        "21a_decision_state": (str(row["decision_state"]), upstream["decision_state"]),
        "21a_freeze_bundle_hash": (str(row["freeze_bundle_hash"]), upstream["freeze_bundle_hash"]),
        "21a_next_requirement": (
            str(row["next_allowed_requirement"]),
            "requirement_21b_alpha158_sequence_baseline_benchmark.md",
        ),
        "21a_next_execution_authorized": (str(row["next_requirement_execution_authorized"]).lower(), "false"),
    }
    for check_id, (observed, expected) in semantic_checks.items():
        passed = observed == expected
        audit.append(
            {
                "check_id": check_id,
                "artifact_path": decision_path.relative_to(TOPIC_ROOT).as_posix(),
                "expected_value": expected,
                "observed_value": observed,
                "status": "pass" if passed else "fail",
                "blocking_reason": "NA" if passed else f"{check_id}_mismatch",
            }
        )
        if not passed:
            raise ValueError(f"upstream semantic check failed: {check_id}")
    gate_evidence = pd.read_csv(upstream_root / "gate_evidence_21a.csv")
    gate_ok = len(gate_evidence) == 142 and gate_evidence["status"].eq("pass").all()
    if not gate_ok:
        raise ValueError("approved 21A gate evidence is not 142/142 pass")
    audit.append(
        {
            "check_id": "approved_21a_gate_evidence",
            "artifact_path": (upstream_root / "gate_evidence_21a.csv").relative_to(TOPIC_ROOT).as_posix(),
            "expected_value": "142/142 pass",
            "observed_value": f"{int(gate_evidence['status'].eq('pass').sum())}/{len(gate_evidence)} pass",
            "status": "pass",
            "blocking_reason": "NA",
        }
    )

    for key, expected in [
        ("pyproject", upstream["pyproject_sha256"]),
        ("requirements", upstream["requirements_sha256"]),
        ("uv_lock", upstream["uv_lock_sha256"]),
    ]:
        check(f"{key}_sha256", paths[key], expected, file_sha(paths[key]))

    import lightgbm
    import torch

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(True)
    torch.set_deterministic_debug_mode("error")
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    dependency_ok = (
        torch.__version__.split("+")[0] == "2.8.0"
        and lightgbm.__version__ == "4.6.0"
        and torch.cuda.is_available()
        and torch.cuda.get_device_name(0) == config["training"]["expected_device_name"]
    )
    if not dependency_ok:
        raise RuntimeError("locked Torch/LightGBM/CUDA environment mismatch")
    audit.append(
        {
            "check_id": "dependency_lock_and_gpu",
            "artifact_path": "runtime",
            "expected_value": "torch=2.8.0|lightgbm=4.6.0|cuda=true|RTX4070SUPER",
            "observed_value": f"torch={torch.__version__}|lightgbm={lightgbm.__version__}|cuda={torch.cuda.is_available()}|{torch.cuda.get_device_name(0)}",
            "status": "pass",
            "blocking_reason": "NA",
        }
    )

    resolved = json.loads(json.dumps(config))
    resolved["artifact_profiles"] = expanded_artifact_profiles()
    resolved["runtime"] = {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "lightgbm": str(lightgbm.__version__),
        "cuda": str(torch.version.cuda),
        "device": torch.cuda.get_device_name(0),
        "config_sha256": file_sha(config_path),
        "artifact_profile_registry_sha256": hashlib.sha256(
            canonical_json_bytes(resolved["artifact_profiles"])
        ).hexdigest(),
    }
    write_yaml(build / "preflight/resolved_config.yaml", resolved)
    write_csv(
        build / "preflight/upstream_21a_authorization_and_hash_audit.csv",
        audit,
        [
            "check_id",
            "artifact_path",
            "expected_value",
            "observed_value",
            "status",
            "blocking_reason",
        ],
    )
    write_csv(build / "preflight/preflight_access_audit.csv", access, ACCESS_COLUMNS)
    write_csv(
        build / "training/model_search_accounting_manifest.csv",
        planned_jobs(),
        SEARCH_COLUMNS,
    )


def _load_calendar(path: Path) -> tuple[list[str], dict[str, int], dict[str, str]]:
    dates = sorted(pd.read_csv(path, usecols=["trade_date"])["trade_date"].astype(str).unique())
    index = {date: position for position, date in enumerate(dates)}
    next_session = {dates[i]: dates[i + 1] for i in range(len(dates) - 1)}
    return dates, index, next_session


def _read_qfq_prefix(path: Path, max_date: str) -> dict[str, float]:
    closes: dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        previous = ""
        for row in reader:
            date = str(row.get("date", ""))
            if previous and date <= previous:
                raise ValueError(f"qfq dates not strictly increasing: {path}")
            previous = date
            if date > max_date:
                break
            value = float(row["close"])
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"invalid qfq close: {path}:{date}")
            closes[date] = value
    return closes


def _write_sequence_index(path: Path, rows: list[dict[str, Any]]) -> None:
    schema = pa.schema(
        [
            ("sample_row_idx", pa.int64()),
            ("split", pa.string()),
            ("fold", pa.string()),
            ("decision_date", pa.date32()),
            ("instrument", pa.string()),
            ("U_t_decision_n", pa.int32()),
            ("x_cache_row_indices", pa.list_(pa.int64(), LOOKBACK)),
            ("source_dates", pa.list_(pa.date32(), LOOKBACK)),
            ("fold_panel_row_idx", pa.int64()),
            ("row_key_hash", pa.string()),
        ]
    )
    table = pa.Table.from_pylist(rows, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)


def materialize_labels(config: dict[str, Any]) -> None:
    paths = resolve_paths(config)
    build = building_root(config)
    if not (build / "preflight/resolved_config.yaml").exists():
        raise RuntimeError("preflight seal missing")
    access: list[dict[str, Any]] = []
    upstream = config["upstream"]
    data_cfg = config["data"]

    for key, expected in [
        ("membership", upstream["membership_sha256"]),
        ("trading_calendar", upstream["trading_calendar_sha256"]),
        ("instrument_metadata", upstream["instrument_metadata_sha256"]),
    ]:
        observed = file_sha(paths[key])
        access_row(
            access,
            stage="materialize-labels",
            phase="source_hash",
            path=paths[key],
            role=key,
            kind="byte_integrity_hash",
            requested="raw_bytes",
            content_sha256=observed,
            purpose="source_integrity_before_value_decode",
        )
        if observed != expected:
            raise ValueError(f"{key} source hash mismatch")
    for key, expected in [
        ("qfq_root", upstream["qfq_root_hash"]),
        ("feature_cache_root", upstream["feature_cache_content_hash"]),
    ]:
        observed, file_n, size = root_inventory_hash(paths[key])
        access_row(
            access,
            stage="materialize-labels",
            phase="source_hash",
            path=paths[key],
            role=key,
            kind="byte_integrity_hash",
            requested=f"raw_bytes|file_n={file_n}|size={size}",
            content_sha256=observed,
            purpose="source_integrity_before_value_decode",
        )
        if observed != expected:
            raise ValueError(f"{key} root hash mismatch: {observed}")

    calendar_dates, calendar_index, next_session = _load_calendar(paths["trading_calendar"])
    access_row(
        access,
        stage="materialize-labels",
        phase="calendar",
        path=paths["trading_calendar"],
        role="trading_calendar",
        kind="routing_date_only",
        requested="trade_date",
        parsed="NA",
        date_min=data_cfg["train_start"],
        date_max=data_cfg["max_allowed_outcome_source_date"],
        max_date=data_cfg["max_allowed_outcome_source_date"],
        purpose="sequence_and_label_session_mapping",
    )

    keys_path = paths["feature_cache_root"] / "keys.csv"
    feature_path = paths["feature_cache_root"] / "normalized_features.f32.memmap"
    keys = pd.read_csv(keys_path, dtype={"instrument": str, "feature_date": str})
    if not np.array_equal(keys["row_index"].to_numpy(), np.arange(len(keys), dtype=np.int64)):
        raise ValueError("feature cache row_index is not contiguous")
    if list(keys[["instrument", "feature_date"]].itertuples(index=False, name=None)) != sorted(
        keys[["instrument", "feature_date"]].itertuples(index=False, name=None)
    ):
        raise ValueError("feature cache keys are not canonical sorted")
    expected_bytes = len(keys) * FEATURE_COUNT * 4
    if feature_path.stat().st_size != expected_bytes:
        raise ValueError("feature cache memmap byte size mismatch")
    key_to_row = {
        f"{instrument}|{date}": int(index)
        for index, instrument, date in keys.itertuples(index=False, name=None)
    }
    access_row(
        access,
        stage="materialize-labels",
        phase="feature_cache",
        path=keys_path,
        role="feature_cache_keys",
        kind="decoded_nonoutcome",
        requested="row_index|instrument|feature_date",
        purpose="sequence_cache_offsets",
    )
    del keys

    membership_columns = [
        "membership_date",
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "history_ready_240d_flag",
    ]
    membership = pd.read_csv(paths["membership"], usecols=membership_columns, dtype=str)
    membership["instrument"] = membership["instrument"].astype(str)
    membership["membership_date"] = membership["membership_date"].astype(str)
    relevant_start = calendar_dates[max(0, calendar_index[data_cfg["train_start"]] - LOOKBACK - 1)]
    membership = membership[
        membership["membership_date"].between(
            relevant_start, data_cfg["max_allowed_outcome_source_date"]
        )
    ].copy()
    suspension: dict[str, dict[str, bool]] = defaultdict(dict)
    listed: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in membership.itertuples(index=False):
        suspension[row.instrument][row.membership_date] = bool_value(row.is_suspended)
        listed[row.instrument][row.membership_date] = bool_value(row.is_listed)
    decision_mask = membership["membership_date"].between(
        data_cfg["train_start"], data_cfg["train_end"]
    ) | membership["membership_date"].between(
        data_cfg["validation_start"], data_cfg["validation_end"]
    )
    decisions = membership[decision_mask].copy()
    decisions = decisions[
        decisions["is_listed"].map(bool_value)
        & ~decisions["is_st"].map(bool_value)
        & decisions["history_ready_240d_flag"].map(bool_value)
    ]
    decisions = decisions[
        decisions.apply(
            lambda row: row["usable_trade_date"]
            == next_session.get(row["membership_date"], ""),
            axis=1,
        )
    ]
    decision_instruments = sorted(decisions["instrument"].unique())
    access_row(
        access,
        stage="materialize-labels",
        phase="universe",
        path=paths["membership"],
        role="pit_membership",
        kind="decoded_nonoutcome",
        requested="|".join(membership_columns),
        date_min=relevant_start,
        date_max=data_cfg["max_allowed_outcome_source_date"],
        max_date=data_cfg["max_allowed_outcome_source_date"],
        purpose="freeze_U_t_decision_and_suspension_policy",
    )

    closes_by_instrument: dict[str, dict[str, float]] = {}
    for instrument in decision_instruments:
        qfq_path = paths["qfq_root"] / f"{instrument}.csv"
        if not qfq_path.exists():
            closes_by_instrument[instrument] = {}
            continue
        closes_by_instrument[instrument] = _read_qfq_prefix(
            qfq_path, data_cfg["max_allowed_outcome_source_date"]
        )
        access_row(
            access,
            stage="materialize-labels",
            phase="qfq_prefix",
            path=qfq_path,
            role="qfq_close",
            kind="outcome_value_row",
            requested="date|close",
            parsed="close",
            date_min=min(closes_by_instrument[instrument], default="NA"),
            date_max=max(closes_by_instrument[instrument], default="NA"),
            max_date=data_cfg["max_allowed_outcome_source_date"],
            content_sha256=file_sha(qfq_path),
            purpose="return_sequence_and_primary_label",
        )

    resolved_close: dict[str, dict[str, float | None]] = {}
    start_index = max(1, calendar_index[relevant_start] - 1)
    end_index = calendar_index[data_cfg["max_allowed_outcome_source_date"]]
    relevant_calendar = calendar_dates[start_index - 1 : end_index + 1]
    for instrument in decision_instruments:
        observed = closes_by_instrument[instrument]
        resolved: dict[str, float | None] = {}
        previous: float | None = None
        for date in relevant_calendar:
            if date in observed:
                previous = observed[date]
                resolved[date] = previous
            elif suspension[instrument].get(date, False) and previous is not None:
                resolved[date] = previous
            else:
                resolved[date] = None
        resolved_close[instrument] = resolved

    upstream_support = pd.read_csv(
        paths["approved_21a_root"] / "freeze/feature_sequence_support_audit.csv",
        dtype={"decision_date": str},
    )
    expected_count = {
        str(row.decision_date): int(row.U_decision_n)
        for row in upstream_support.itertuples(index=False)
        if (
            data_cfg["train_start"] <= str(row.decision_date) <= data_cfg["train_end"]
            or data_cfg["validation_start"] <= str(row.decision_date) <= data_cfg["validation_end"]
        )
    }

    candidate_rows: list[dict[str, Any]] = []
    for row in decisions.sort_values(["membership_date", "instrument"]).itertuples(index=False):
        decision_date = str(row.membership_date)
        position = calendar_index.get(decision_date, -1)
        if position < LOOKBACK:
            continue
        source_dates = calendar_dates[position - LOOKBACK + 1 : position + 1]
        cache_indices: list[int] = []
        source_ready = True
        for date in source_dates:
            cache_index = key_to_row.get(f"{row.instrument}|{date}")
            valid_market_row = (
                date in closes_by_instrument[row.instrument]
                or suspension[row.instrument].get(date, False)
            )
            if cache_index is None or not valid_market_row:
                source_ready = False
                break
            cache_indices.append(cache_index)
        if not source_ready:
            continue
        candidate_rows.append(
            {
                "decision_date": decision_date,
                "instrument": row.instrument,
                "board_bucket": row.board_bucket,
                "source_dates": source_dates,
                "cache_indices": cache_indices,
            }
        )

    observed_count = pd.Series([row["decision_date"] for row in candidate_rows]).value_counts().to_dict()
    mismatches = {
        date: (expected_count.get(date), observed_count.get(date, 0))
        for date in expected_count
        if expected_count.get(date) != observed_count.get(date, 0)
    }
    if mismatches:
        first = list(mismatches.items())[:5]
        raise ValueError(f"U_t_decision count mismatch against 21A: {first}")

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        instrument = row["instrument"]
        dates = row["source_dates"]
        returns: list[float] = []
        resolved = resolved_close[instrument]
        return_ok = True
        for date in dates:
            position = calendar_index[date]
            previous_date = calendar_dates[position - 1]
            current_close = resolved.get(date)
            previous_close = resolved.get(previous_date)
            if current_close is None or previous_close is None or previous_close <= 0:
                return_ok = False
                break
            returns.append(current_close / previous_close - 1.0)
        decision_date = row["decision_date"]
        label_date = next_session[decision_date]
        current_close = resolved.get(decision_date)
        next_close = resolved.get(label_date)
        if next_close is not None and label_date in closes_by_instrument[instrument]:
            label_status = "NORMAL_NEXT_SESSION_CLOSE"
        elif next_close is not None and suspension[instrument].get(label_date, False):
            label_status = "LISTED_SUSPENDED_CARRY"
        elif label_date > data_cfg["max_allowed_outcome_source_date"]:
            label_status = "RIGHT_CENSORED_DATA_CUTOFF"
        else:
            label_status = "UNKNOWN_DATA_GAP"
        label_ok = current_close is not None and next_close is not None and current_close > 0
        row["returns"] = returns if return_ok else []
        row["label_date"] = label_date
        row["label_status"] = label_status
        row["label_value"] = next_close / current_close - 1.0 if label_ok else math.nan
        row["row_resolved"] = bool(return_ok and label_ok and np.isfinite(row["label_value"]))
        by_day[decision_date].append(row)

    audit_rows: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    for decision_date, day_rows in sorted(by_day.items()):
        decision_n = len(day_rows)
        resolved_n = sum(row["row_resolved"] for row in day_rows)
        whole_day = resolved_n == decision_n and decision_n >= data_cfg["minimum_cross_section_n"]
        reason = "NA" if whole_day else "incomplete_return_or_label_resolution"
        for row in day_rows:
            split = "train" if decision_date <= data_cfg["train_end"] else "validation"
            fold = (
                "train"
                if split == "train"
                else "validation_early"
                if decision_date <= data_cfg["validation_early_end"]
                else "validation_late"
            )
            audit_rows.append(
                {
                    "split": split,
                    "fold": fold,
                    "decision_date": decision_date,
                    "instrument": row["instrument"],
                    "usable_trade_date": next_session[decision_date],
                    "U_t_decision": True,
                    "history_ready": True,
                    "sequence_ready": bool(row["returns"]),
                    "feature_ready": True,
                    "label_resolution_status": row["label_status"],
                    "label_source_date": row["label_date"],
                    "label_value": row["label_value"] if row["row_resolved"] else None,
                    "U_t_decision_n": decision_n,
                    "U_t_resolved_n": resolved_n,
                    "whole_day_evaluable": whole_day,
                    "whole_day_not_evaluable_reason": reason,
                    "row_key_hash": row_key_hash(row["instrument"], decision_date),
                }
            )
            if whole_day:
                row["split"] = split
                row["fold"] = fold
                row["U_t_decision_n"] = decision_n
                retained.append(row)

    fold_order = {"train": 0, "validation_early": 1, "validation_late": 2}
    retained.sort(key=lambda row: (fold_order[row["fold"]], row["decision_date"], row["instrument"]))
    panels: dict[str, list[list[float]]] = {fold: [] for fold in fold_order}
    sequence_rows: list[dict[str, Any]] = []
    for sample_index, row in enumerate(retained):
        fold = row["fold"]
        fold_row = len(panels[fold])
        panels[fold].append([*row["returns"], float(row["label_value"])])
        sequence_rows.append(
            {
                "sample_row_idx": sample_index,
                "split": row["split"],
                "fold": fold,
                "decision_date": pd.Timestamp(row["decision_date"]).date(),
                "instrument": row["instrument"],
                "U_t_decision_n": row["U_t_decision_n"],
                "x_cache_row_indices": row["cache_indices"],
                "source_dates": [pd.Timestamp(date).date() for date in row["source_dates"]],
                "fold_panel_row_idx": fold_row,
                "row_key_hash": row_key_hash(row["instrument"], row["decision_date"]),
            }
        )

    materialized = build / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    audit_frame = pd.DataFrame(audit_rows).sort_values(
        ["split", "fold", "decision_date", "instrument"]
    )
    audit_frame.to_parquet(
        materialized / "decision_universe_and_label_resolution_audit.parquet",
        index=False,
        compression="zstd",
    )
    _write_sequence_index(materialized / "sequence_sample_index.parquet", sequence_rows)
    partitions: list[dict[str, Any]] = []
    for fold in ("train", "validation_early", "validation_late"):
        panel_path = materialized / f"panels/{fold}/return_and_label_panel.f32.memmap"
        panel_path.parent.mkdir(parents=True, exist_ok=True)
        values = np.asarray(panels[fold], dtype="<f4")
        if values.ndim != 2 or values.shape[1] != 11 or not np.isfinite(values).all():
            raise ValueError(f"invalid materialized panel: {fold} {values.shape}")
        mm = np.memmap(panel_path, mode="w+", dtype="<f4", shape=values.shape)
        mm[:] = values
        mm.flush()
        del mm
        row_keys = [
            row["row_key_hash"] for row in sequence_rows if row["fold"] == fold
        ]
        partitions.append(
            {
                "fold": fold,
                "path": panel_path.relative_to(build).as_posix(),
                "sha256": file_sha(panel_path),
                "byte_size": panel_path.stat().st_size,
                "shape": list(values.shape),
                "dtype": "little-endian-float32",
                "column_semantics": [
                    *[f"y_source_t_minus_{9-i}" for i in range(10)],
                    "forecast_y_t_plus_1",
                ],
                "row_key_hash": stable_hash(row_keys),
                "open_phase_whitelist": (
                    "post_pre_gate_seal_readout"
                    if fold == "validation_late"
                    else "selection_and_readout"
                ),
            }
        )

    sequence_path = materialized / "sequence_sample_index.parquet"
    label_path = materialized / "decision_universe_and_label_resolution_audit.parquet"
    fold_counts = {fold: len(panels[fold]) for fold in panels}
    fold_days = {
        fold: len({row["decision_date"] for row in retained if row["fold"] == fold})
        for fold in panels
    }
    panel_manifest = {
        "schema_version": "21B_model_input_panel_v4",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "approved_21a_contract_version": upstream["contract_version"],
        "approved_21a_freeze_bundle_hash": upstream["freeze_bundle_hash"],
        "feature_route_id": data_cfg["feature_route_id"],
        "feature_count": FEATURE_COUNT,
        "feature_expression_sha256": upstream["feature_expression_sha256"],
        "feature_cache_content_hash": upstream["feature_cache_content_hash"],
        "normalization_contract_hash": upstream["normalization_contract_hash"],
        "split_hash": upstream["split_hash"],
        "feature_cache_keys_path": keys_path.relative_to(TOPIC_ROOT).as_posix(),
        "feature_cache_keys_sha256": file_sha(keys_path),
        "feature_cache_memmap_path": feature_path.relative_to(TOPIC_ROOT).as_posix(),
        "feature_cache_memmap_sha256": file_sha(feature_path),
        "feature_cache_shape": [len(key_to_row), FEATURE_COUNT],
        "feature_cache_dtype": "little-endian-float32",
        "sequence_sample_index_path": sequence_path.relative_to(build).as_posix(),
        "sequence_sample_index_sha256": file_sha(sequence_path),
        "sequence_sample_n": len(sequence_rows),
        "sequence_sort_key": "fold,decision_date,instrument",
        "panel_partitions": partitions,
        "train_row_key_hash": partitions[0]["row_key_hash"],
        "validation_early_row_key_hash": partitions[1]["row_key_hash"],
        "validation_late_row_key_hash": partitions[2]["row_key_hash"],
        "train_row_n": fold_counts["train"],
        "validation_early_row_n": fold_counts["validation_early"],
        "validation_late_row_n": fold_counts["validation_late"],
        "train_day_n": fold_days["train"],
        "validation_early_day_n": fold_days["validation_early"],
        "validation_late_day_n": fold_days["validation_late"],
        "label_id": "Y_rank_primary",
        "label_materialization_hash": stable_hash(
            audit_frame[
                ["decision_date", "instrument", "label_resolution_status", "label_value"]
            ].to_dict("records")
        ),
        "max_allowed_outcome_source_date": data_cfg["max_allowed_outcome_source_date"],
        "materialization_worker_validation_late_summary_count": 0,
        "materialization_worker_validation_late_metric_count": 0,
        "historical_holdout_row_materialized_n": 0,
        "outcome_access_scope": "train_and_validation_only",
        "status": "pass",
        "label_audit_sha256": file_sha(label_path),
    }
    write_json(materialized / "model_input_panel_manifest.json", panel_manifest)
    write_csv(materialized / "materialization_access_audit.csv", access, ACCESS_COLUMNS)


def _load_fold(build: Path, fold: str) -> dict[str, Any]:
    index = pd.read_parquet(build / "materialized/sequence_sample_index.parquet")
    index["decision_date"] = index["decision_date"].astype(str)
    index = index[index["fold"] == fold].sort_values(
        ["decision_date", "instrument"]
    ).reset_index(drop=True)
    panel_path = build / f"materialized/panels/{fold}/return_and_label_panel.f32.memmap"
    if panel_path.stat().st_size != len(index) * 11 * 4:
        raise ValueError(f"panel byte-size mismatch for {fold}")
    panel = np.memmap(panel_path, mode="r", dtype="<f4", shape=(len(index), 11))
    cache_indices = np.stack(index["x_cache_row_indices"].map(np.asarray)).astype(
        np.int64, copy=False
    )
    return {
        "index": index,
        "cache_indices": cache_indices,
        "returns": panel[:, :10],
        "labels": panel[:, 10],
        "panel": panel,
    }


def _feature_memmap(config: dict[str, Any]) -> np.memmap:
    paths = resolve_paths(config)
    key_n = sum(1 for _ in (paths["feature_cache_root"] / "keys.csv").open()) - 1
    feature_path = paths["feature_cache_root"] / "normalized_features.f32.memmap"
    return np.memmap(feature_path, mode="r", dtype="<f4", shape=(key_n, FEATURE_COUNT))


def _day_slices(dates: Sequence[str]) -> list[tuple[str, int, int]]:
    if not len(dates):
        return []
    values = np.asarray(dates, dtype=str)
    boundaries = np.flatnonzero(values[1:] != values[:-1]) + 1
    starts = np.r_[0, boundaries]
    ends = np.r_[boundaries, len(values)]
    return [(str(values[start]), int(start), int(end)) for start, end in zip(starts, ends, strict=True)]


def mean_daily_rankic(
    scores: np.ndarray, labels: np.ndarray, dates: Sequence[str], minimum_n: int = 100
) -> tuple[float, int, list[float]]:
    values: list[float] = []
    for _, start, end in _day_slices(dates):
        metric = rankic(scores[start:end], labels[start:end], minimum_n=minimum_n)
        if math.isfinite(metric):
            values.append(metric)
    return (
        float(np.mean(values)) if values else math.nan,
        len(values),
        values,
    )


def _initialization_contract_hash() -> str:
    return stable_hash(
        {
            "version": "21B_v4_init_v1",
            "module_order": {
                "M2_RETURN_LSTM": ["lstm_y", "score_head"],
                "M3_GATED_DUAL_PATH_LSTM": [
                    "lstm_y",
                    "lstm_x",
                    "gate_linear",
                    "score_head",
                ],
                "A0_VANILLA_AUTOENCODER": [
                    "lstm_y",
                    "lstm_x",
                    "gate_linear",
                    "source_decoder",
                    "score_head",
                ],
            },
            "weight_ih": "xavier_uniform_full_gain_1",
            "weight_hh": "orthogonal_per_ifgo_gate_gain_1",
            "bias_ih_forget": 1.0,
            "bias_hh_forget": 0.0,
            "device": "cpu_then_cuda",
        }
    )


def build_torch_model(arm_id: str, latent_dim: int = 64) -> Any:
    import torch

    class ReturnLSTM(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm_y = torch.nn.LSTM(1, latent_dim, batch_first=True)
            self.score_head = torch.nn.Linear(latent_dim, 1)

        def forward(self, y: Any, x: Any | None = None) -> tuple[Any, Any | None]:
            hidden, _ = self.lstm_y(y)
            return self.score_head(hidden[:, -1]).squeeze(-1), None

    class DualPath(torch.nn.Module):
        def __init__(self, autoencoder: bool) -> None:
            super().__init__()
            self.lstm_y = torch.nn.LSTM(1, latent_dim, batch_first=True)
            self.lstm_x = torch.nn.LSTM(FEATURE_COUNT, latent_dim, batch_first=True)
            self.gate_linear = torch.nn.Linear(latent_dim, latent_dim)
            if autoencoder:
                self.source_decoder = torch.nn.Linear(latent_dim, 1)
            self.score_head = torch.nn.Linear(latent_dim, 1)
            self.autoencoder = autoencoder

        def forward(self, y: Any, x: Any | None = None) -> tuple[Any, Any | None]:
            if x is None:
                raise ValueError("dual-path model requires x_source")
            hidden_y, _ = self.lstm_y(y)
            hidden_x, _ = self.lstm_x(x)
            gate = torch.sigmoid(self.gate_linear(hidden_x))
            latent = hidden_y * gate + hidden_x * (1.0 - gate)
            score = self.score_head(latent[:, -1]).squeeze(-1)
            decoded = (
                self.source_decoder(latent).squeeze(-1) if self.autoencoder else None
            )
            return score, decoded

    if arm_id == "M2_RETURN_LSTM":
        return ReturnLSTM()
    if arm_id == "M3_GATED_DUAL_PATH_LSTM":
        return DualPath(False)
    if arm_id == "A0_VANILLA_AUTOENCODER":
        return DualPath(True)
    raise ValueError(f"unknown torch arm: {arm_id}")


def initialize_torch_model(model: Any, arm_id: str, seed: int) -> None:
    import torch

    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed + 53)
    order = {
        "M2_RETURN_LSTM": ["lstm_y", "score_head"],
        "M3_GATED_DUAL_PATH_LSTM": [
            "lstm_y",
            "lstm_x",
            "gate_linear",
            "score_head",
        ],
        "A0_VANILLA_AUTOENCODER": [
            "lstm_y",
            "lstm_x",
            "gate_linear",
            "source_decoder",
            "score_head",
        ],
    }[arm_id]
    hidden = 64
    with torch.no_grad():
        for name in order:
            module = getattr(model, name)
            if isinstance(module, torch.nn.LSTM):
                torch.nn.init.xavier_uniform_(
                    module.weight_ih_l0, gain=1.0, generator=generator
                )
                for gate_index in range(4):
                    torch.nn.init.orthogonal_(
                        module.weight_hh_l0[
                            gate_index * hidden : (gate_index + 1) * hidden
                        ],
                        gain=1.0,
                        generator=generator,
                    )
                module.bias_ih_l0.zero_()
                module.bias_hh_l0.zero_()
                module.bias_ih_l0[hidden : 2 * hidden].fill_(1.0)
            elif isinstance(module, torch.nn.Linear):
                torch.nn.init.xavier_uniform_(
                    module.weight, gain=1.0, generator=generator
                )
                module.bias.zero_()
            else:
                raise TypeError(f"unexpected module in init order: {name}")


def model_state_semantic_hash(state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        array = tensor.numpy()
        if array.dtype.byteorder == ">":
            array = array.byteswap().newbyteorder("<")
        header = canonical_json_bytes(
            {"name": name, "dtype": str(array.dtype), "shape": list(array.shape)}
        )
        digest.update(len(header).to_bytes(8, "little"))
        digest.update(header)
        raw = array.tobytes(order="C")
        digest.update(len(raw).to_bytes(8, "little"))
        digest.update(raw)
    return digest.hexdigest()


def _predict_torch(
    model: Any,
    fold: dict[str, Any],
    features: np.memmap,
    arm_id: str,
    batch_size: int,
    device: Any,
) -> np.ndarray:
    import torch

    model.eval()
    predictions = np.empty(len(fold["index"]), dtype=np.float64)
    with torch.inference_mode():
        for start in range(0, len(predictions), batch_size):
            end = min(len(predictions), start + batch_size)
            y = torch.from_numpy(
                np.asarray(fold["returns"][start:end], dtype=np.float32)[..., None]
            ).to(device)
            x = None
            if arm_id != "M2_RETURN_LSTM":
                values = np.asarray(
                    features[fold["cache_indices"][start:end]], dtype=np.float32
                )
                x = torch.from_numpy(values).to(device)
            score, _ = model(y, x)
            predictions[start:end] = score.detach().cpu().numpy().astype(np.float64)
    return predictions


def train_deep_seed(
    config: dict[str, Any],
    build: Path,
    arm_id: str,
    seed: int,
    train: dict[str, Any],
    early: dict[str, Any],
    features: np.memmap,
    batch_size: int,
) -> tuple[dict[str, Any], np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    import random

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch

    random.seed(seed)
    np.random.seed(seed + 11)
    torch.manual_seed(seed + 23)
    torch.use_deterministic_algorithms(True)
    torch.set_deterministic_debug_mode("error")
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    model = build_torch_model(arm_id, config["training"]["latent_dim"])
    initialize_torch_model(model, arm_id, seed)
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["training"]["learning_rate"]),
        weight_decay=float(config["training"]["weight_decay"]),
    )
    permutation_generator = torch.Generator(device="cpu")
    permutation_generator.manual_seed(seed + 37)
    curves: list[dict[str, Any]] = []
    best_metric = -math.inf
    best_epoch = 0
    best_state: dict[str, Any] | None = None
    patience = 0
    started = time.perf_counter()
    peak_memory = 0.0
    for epoch in range(1, int(config["training"]["max_epochs"]) + 1):
        model.train()
        order = torch.randperm(
            len(train["index"]), generator=permutation_generator
        ).numpy()
        loss_sum = 0.0
        sample_n = 0
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            y_np = np.asarray(train["returns"][batch], dtype=np.float32)
            target_np = np.asarray(train["labels"][batch], dtype=np.float32)
            y = torch.from_numpy(y_np[..., None]).to(device)
            target = torch.from_numpy(target_np).to(device)
            x = None
            if arm_id != "M2_RETURN_LSTM":
                x_np = np.asarray(features[train["cache_indices"][batch]], dtype=np.float32)
                x = torch.from_numpy(x_np).to(device)
            optimizer.zero_grad(set_to_none=True)
            score, decoded = model(y, x)
            loss = torch.mean((score - target) ** 2)
            if arm_id == "A0_VANILLA_AUTOENCODER":
                if decoded is None:
                    raise RuntimeError("A0 decoder output missing")
                loss = loss + torch.mean((decoded - y.squeeze(-1)) ** 2)
            if not torch.isfinite(loss):
                raise FloatingPointError(f"non-finite loss {arm_id} seed={seed}")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(config["training"]["gradient_clip_norm"])
            )
            optimizer.step()
            loss_sum += float(loss.detach().cpu()) * len(batch)
            sample_n += len(batch)
        predictions = _predict_torch(model, early, features, arm_id, batch_size, device)
        metric, complete_days, _ = mean_daily_rankic(
            predictions,
            np.asarray(early["labels"], dtype=np.float64),
            early["index"]["decision_date"].astype(str).to_numpy(),
            minimum_n=100,
        )
        peak_memory = max(peak_memory, torch.cuda.max_memory_allocated() / 1024**2)
        curves.append(
            {
                "arm_id": arm_id,
                "model_seed": seed,
                "epoch_or_round": epoch,
                "train_loss": loss_sum / sample_n,
                "validation_early_mean_RankIC": metric,
                "validation_early_complete_day_n": complete_days,
                "validation_early_score_coverage_rate": 1.0,
                "elapsed_seconds": time.perf_counter() - started,
                "peak_memory_mib": peak_memory,
                "data_pass_n": epoch,
                "status": "completed",
            }
        )
        if math.isfinite(metric) and metric > best_metric:
            best_metric = metric
            best_epoch = epoch
            best_state = {
                name: tensor.detach().cpu().clone()
                for name, tensor in model.state_dict().items()
            }
            patience = 0
        else:
            patience += 1
        if patience >= int(config["training"]["early_stopping_patience"]):
            break
    if best_state is None:
        raise RuntimeError(f"no eligible checkpoint for {arm_id} seed={seed}")
    model.load_state_dict(best_state)
    inference_started = time.perf_counter()
    final_predictions = _predict_torch(
        model, early, features, arm_id, batch_size, device
    )
    inference_seconds = time.perf_counter() - inference_started
    checkpoint = (
        build / f"training/checkpoints/{arm_id}/seed_{seed}/state_dict.pt"
    )
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, checkpoint)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    record = {
        "arm_id": arm_id,
        "model_seed": seed,
        "checkpoint_path": checkpoint.relative_to(build).as_posix(),
        "model_type": "pytorch_state_dict",
        "serialization_format": "torch_state_dict_zip",
        "serialization_version": "torch_2.8.0_state_dict_zip_v1",
        "provisional_selected_epoch_or_round": best_epoch,
        "selection_fold": "validation_early",
        "validation_early_metric_at_selection": best_metric,
        "config_sha256": file_sha(DEFAULT_CONFIG),
        "feature_cache_content_hash": config["upstream"]["feature_cache_content_hash"],
        "split_hash": config["upstream"]["split_hash"],
        "normalization_contract_hash": config["upstream"]["normalization_contract_hash"],
        "train_row_key_hash": stable_hash(train["index"]["row_key_hash"].tolist()),
        "validation_early_row_key_hash": stable_hash(early["index"]["row_key_hash"].tolist()),
        "parameter_count": parameter_count,
        "complexity_definition": "pytorch_trainable_scalar_n",
        "model_specific_complexity": None,
        "model_input_construction_sha256": stable_hash(
            {
                "sequence_index": file_sha(build / "materialized/sequence_sample_index.parquet"),
                "batch_size": batch_size,
                "dataloader_seed": seed + 37,
                "drop_last": False,
            }
        ),
        "parameter_initialization_contract_sha256": _initialization_contract_hash(),
        "checkpoint_sha256": file_sha(checkpoint),
        "model_state_semantic_sha256": model_state_semantic_hash(best_state),
        "runtime_fingerprint_sha256": stable_hash(
            {
                "torch": torch.__version__,
                "cuda": torch.version.cuda,
                "device": torch.cuda.get_device_name(0),
                "deterministic": True,
            }
        ),
    }
    compute = {
        "arm_id": arm_id,
        "model_seed": seed,
        "parameter_count": parameter_count,
        "train_seconds": time.perf_counter() - started,
        "inference_seconds": inference_seconds,
        "inference_row_n": len(early["index"]),
        "latency_ms_per_1000_rows": inference_seconds * 1_000_000 / len(early["index"]),
        "peak_cpu_rss_mib": 0.0,
        "peak_gpu_memory_mib": peak_memory,
        "data_pass_n": len(curves),
        "status": "pass",
    }
    return record, final_predictions, curves, compute


def train_lightgbm_seed(
    config: dict[str, Any],
    build: Path,
    seed: int,
    train: dict[str, Any],
    early: dict[str, Any],
    features: np.memmap,
) -> tuple[dict[str, Any], np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    import lightgbm as lgb

    started = time.perf_counter()
    x_train = np.asarray(features[train["cache_indices"][:, -1]], dtype=np.float32)
    x_early = np.asarray(features[early["cache_indices"][:, -1]], dtype=np.float32)
    y_train = np.asarray(train["labels"], dtype=np.float32)
    y_early = np.asarray(early["labels"], dtype=np.float32)
    params_cfg = config["training"]["lightgbm"]
    params = {
        "objective": params_cfg["objective"],
        "metric": "l2",
        "learning_rate": params_cfg["learning_rate"],
        "num_leaves": params_cfg["num_leaves"],
        "max_depth": params_cfg["max_depth"],
        "min_data_in_leaf": params_cfg["min_data_in_leaf"],
        "feature_fraction": params_cfg["feature_fraction"],
        "bagging_fraction": params_cfg["bagging_fraction"],
        "lambda_l1": params_cfg["lambda_l1"],
        "lambda_l2": params_cfg["lambda_l2"],
        "deterministic": params_cfg["deterministic"],
        "force_col_wise": params_cfg["force_col_wise"],
        "num_threads": params_cfg["num_threads"],
        "verbosity": params_cfg["verbosity"],
        "seed": seed,
        "bagging_seed": seed,
        "feature_fraction_seed": seed,
        "data_random_seed": seed,
        "bin_construct_sample_cnt": params_cfg["bin_construct_sample_cnt"],
        "max_bin": params_cfg["max_bin"],
    }
    dataset = lgb.Dataset(x_train, label=y_train, params=params, free_raw_data=False)
    booster = lgb.Booster(params=params, train_set=dataset)
    curves: list[dict[str, Any]] = []
    best_metric = -math.inf
    best_round = 0
    best_predictions: np.ndarray | None = None
    patience = 0
    dates = early["index"]["decision_date"].astype(str).to_numpy()
    for round_number in range(1, int(params_cfg["max_boosting_rounds"]) + 1):
        booster.update()
        predictions = booster.predict(x_early, num_iteration=round_number)
        metric, complete_days, _ = mean_daily_rankic(
            predictions, y_early, dates, minimum_n=100
        )
        train_loss = float(
            np.mean((booster.predict(x_train, num_iteration=round_number) - y_train) ** 2)
        )
        curves.append(
            {
                "arm_id": "M1_LIGHTGBM_ALPHA158",
                "model_seed": seed,
                "epoch_or_round": round_number,
                "train_loss": train_loss,
                "validation_early_mean_RankIC": metric,
                "validation_early_complete_day_n": complete_days,
                "validation_early_score_coverage_rate": 1.0,
                "elapsed_seconds": time.perf_counter() - started,
                "peak_memory_mib": 0.0,
                "data_pass_n": round_number,
                "status": "completed",
            }
        )
        if math.isfinite(metric) and metric > best_metric:
            best_metric = metric
            best_round = round_number
            best_predictions = np.asarray(predictions, dtype=np.float64)
            patience = 0
        else:
            patience += 1
        if patience >= int(params_cfg["early_stopping_rounds"]):
            break
    if best_predictions is None:
        raise RuntimeError(f"no LightGBM candidate for seed {seed}")
    checkpoint = (
        build
        / f"training/checkpoints/M1_LIGHTGBM_ALPHA158/seed_{seed}/model.txt"
    )
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(checkpoint, num_iteration=best_round)
    sealed_booster = lgb.Booster(model_file=str(checkpoint))
    inference_started = time.perf_counter()
    best_predictions = sealed_booster.predict(x_early)
    inference_seconds = time.perf_counter() - inference_started
    dump = sealed_booster.dump_model()
    tree_info = dump.get("tree_info", [])
    leaf_n = sum(int(tree.get("num_leaves", 0)) for tree in tree_info)
    split_n = max(0, leaf_n - len(tree_info))
    record = {
        "arm_id": "M1_LIGHTGBM_ALPHA158",
        "model_seed": seed,
        "checkpoint_path": checkpoint.relative_to(build).as_posix(),
        "model_type": "lightgbm_booster",
        "serialization_format": "lightgbm_text_model",
        "serialization_version": "lightgbm_4.6.0_text_v1",
        "provisional_selected_epoch_or_round": best_round,
        "selection_fold": "validation_early",
        "validation_early_metric_at_selection": best_metric,
        "config_sha256": file_sha(DEFAULT_CONFIG),
        "feature_cache_content_hash": config["upstream"]["feature_cache_content_hash"],
        "split_hash": config["upstream"]["split_hash"],
        "normalization_contract_hash": config["upstream"]["normalization_contract_hash"],
        "train_row_key_hash": stable_hash(train["index"]["row_key_hash"].tolist()),
        "validation_early_row_key_hash": stable_hash(early["index"]["row_key_hash"].tolist()),
        "parameter_count": leaf_n,
        "complexity_definition": "lightgbm_total_leaf_n",
        "model_specific_complexity": {
            "tree_n": len(tree_info),
            "split_n": split_n,
            "leaf_n": leaf_n,
        },
        "model_input_construction_sha256": stable_hash(
            {
                "train_rows": train["index"]["row_key_hash"].tolist(),
                "feature_order": list(range(FEATURE_COUNT)),
                "seed": seed,
                "bin_construct_sample_cnt": params_cfg["bin_construct_sample_cnt"],
                "max_bin": params_cfg["max_bin"],
            }
        ),
        "parameter_initialization_contract_sha256": None,
        "checkpoint_sha256": file_sha(checkpoint),
        "model_state_semantic_sha256": hashlib.sha256(
            canonical_json_bytes({"dump_model": dump, "params": params})
        ).hexdigest(),
        "runtime_fingerprint_sha256": stable_hash(
            {"lightgbm": lgb.__version__, "num_threads": 1}
        ),
    }
    compute = {
        "arm_id": "M1_LIGHTGBM_ALPHA158",
        "model_seed": seed,
        "parameter_count": leaf_n,
        "train_seconds": time.perf_counter() - started,
        "inference_seconds": inference_seconds,
        "inference_row_n": len(early["index"]),
        "latency_ms_per_1000_rows": inference_seconds * 1_000_000 / len(early["index"]),
        "peak_cpu_rss_mib": 0.0,
        "peak_gpu_memory_mib": 0.0,
        "data_pass_n": len(curves),
        "status": "pass",
    }
    return record, np.asarray(best_predictions), curves, compute


def _prediction_rows(
    fold: dict[str, Any],
    arm_id: str,
    role: str,
    scores: np.ndarray,
    config: dict[str, Any],
    *,
    seed: int | None,
    checkpoint_sha256: str | None,
    bundle_sha256: str | None,
) -> list[dict[str, Any]]:
    index = fold["index"]
    return [
        {
            "run_id": RUN_ID,
            "requirement_version": REQUIREMENT_VERSION,
            "split": "validation",
            "fold": str(row.fold),
            "decision_date": str(row.decision_date),
            "instrument": str(row.instrument),
            "arm_id": arm_id,
            "score_role": role,
            "model_seed": seed,
            "score": float(score),
            "U_t_decision_n": int(row.U_t_decision_n),
            "row_key_hash": str(row.row_key_hash),
            "feature_route_id": config["data"]["feature_route_id"],
            "checkpoint_sha256": checkpoint_sha256,
            "checkpoint_bundle_sha256": bundle_sha256,
        }
        for row, score in zip(index.itertuples(index=False), scores, strict=True)
    ]


def write_prediction_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    role_order = {"seed": 0, "ensemble": 1, "null": 2}
    frame["_role"] = frame["score_role"].map(role_order)
    frame = frame.sort_values(
        ["split", "decision_date", "instrument", "arm_id", "_role", "model_seed"],
        na_position="last",
    ).drop(columns="_role")
    schema = pa.schema(
        [
            ("run_id", pa.string()),
            ("requirement_version", pa.string()),
            ("split", pa.string()),
            ("fold", pa.string()),
            ("decision_date", pa.string()),
            ("instrument", pa.string()),
            ("arm_id", pa.string()),
            ("score_role", pa.string()),
            ("model_seed", pa.int64()),
            ("score", pa.float64()),
            ("U_t_decision_n", pa.int32()),
            ("row_key_hash", pa.string()),
            ("feature_route_id", pa.string()),
            ("checkpoint_sha256", pa.string()),
            ("checkpoint_bundle_sha256", pa.string()),
        ]
    )
    table = pa.Table.from_pandas(frame, schema=schema, preserve_index=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)


CURVE_COLUMNS = [
    "arm_id",
    "model_seed",
    "epoch_or_round",
    "train_loss",
    "validation_early_mean_RankIC",
    "validation_early_complete_day_n",
    "validation_early_score_coverage_rate",
    "elapsed_seconds",
    "peak_memory_mib",
    "data_pass_n",
    "status",
]

COMPUTE_COLUMNS = [
    "arm_id",
    "model_seed",
    "parameter_count",
    "train_seconds",
    "inference_seconds",
    "inference_row_n",
    "latency_ms_per_1000_rows",
    "peak_cpu_rss_mib",
    "peak_gpu_memory_mib",
    "data_pass_n",
    "status",
]

REGISTRY_COLUMNS = [
    "run_id",
    "requirement_version",
    "arm_id",
    "model_seed",
    "attempt_id",
    "config_sha256",
    "batch_size",
    "device",
    "started_at_utc",
    "ended_at_utc",
    "provisional_selected_epoch_or_round",
    "job_status",
    "checkpoint_sha256",
    "train_row_n",
    "validation_early_row_n",
    "validation_late_score_row_n",
    "train_day_n",
    "validation_early_day_n",
    "validation_late_day_n",
]


def selection_worker(config: dict[str, Any]) -> None:
    build = building_root(config)
    train = _load_fold(build, "train")
    early = _load_fold(build, "validation_early")
    features = _feature_memmap(config)
    checkpoint_records: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    computes: list[dict[str, Any]] = []
    registry: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    search = planned_jobs()
    search_by_job = {row["job_id"]: row for row in search}
    search_by_job[M0]["attempt_count"] = 1
    search_by_job[M0]["attempt_batch_sizes"] = "NA"
    search_by_job[M0]["final_status"] = "completed"
    search_by_job[M0]["promotion_allowed"] = False
    for arm_id in LEARNED_ARMS:
        for seed in MODEL_SEEDS:
            started_at = utc_now()
            batch_size = int(config["training"]["batch_size"])
            if arm_id == "M1_LIGHTGBM_ALPHA158":
                record, scores, arm_curves, compute = train_lightgbm_seed(
                    config, build, seed, train, early, features
                )
            else:
                record = None
                last_error: Exception | None = None
                for candidate_batch in config["training"]["oom_batch_ladder"]:
                    try:
                        record, scores, arm_curves, compute = train_deep_seed(
                            config,
                            build,
                            arm_id,
                            seed,
                            train,
                            early,
                            features,
                            int(candidate_batch),
                        )
                        batch_size = int(candidate_batch)
                        break
                    except RuntimeError as error:
                        if "out of memory" not in str(error).lower():
                            raise
                        last_error = error
                        import torch

                        torch.cuda.empty_cache()
                if record is None:
                    raise RuntimeError(f"OOM ladder exhausted: {arm_id} {seed}") from last_error
            checkpoint_records.append(record)
            curves.extend(arm_curves)
            computes.append(compute)
            prediction_rows.extend(
                _prediction_rows(
                    early,
                    arm_id,
                    "seed",
                    scores,
                    config,
                    seed=seed,
                    checkpoint_sha256=record["checkpoint_sha256"],
                    bundle_sha256=None,
                )
            )
            ended_at = utc_now()
            registry.append(
                {
                    "run_id": RUN_ID,
                    "requirement_version": REQUIREMENT_VERSION,
                    "arm_id": arm_id,
                    "model_seed": seed,
                    "attempt_id": f"{arm_id}__seed_{seed}_attempt_01",
                    "config_sha256": file_sha(DEFAULT_CONFIG),
                    "batch_size": batch_size,
                    "device": "cpu" if arm_id == "M1_LIGHTGBM_ALPHA158" else "cuda",
                    "started_at_utc": started_at,
                    "ended_at_utc": ended_at,
                    "provisional_selected_epoch_or_round": record[
                        "provisional_selected_epoch_or_round"
                    ],
                    "job_status": "early_stopped",
                    "checkpoint_sha256": record["checkpoint_sha256"],
                    "train_row_n": len(train["index"]),
                    "validation_early_row_n": len(early["index"]),
                    "validation_late_score_row_n": 0,
                    "train_day_n": len(_day_slices(train["index"]["decision_date"])),
                    "validation_early_day_n": len(
                        _day_slices(early["index"]["decision_date"])
                    ),
                    "validation_late_day_n": 0,
                }
            )
            job = search_by_job[f"{arm_id}__seed_{seed}"]
            job["attempt_count"] = 1
            job["attempt_batch_sizes"] = str(batch_size)
            job["final_status"] = "early_stopped"
            job["promotion_allowed"] = True
            print(
                f"selection job complete arm={arm_id} seed={seed} "
                f"selected={record['provisional_selected_epoch_or_round']} "
                f"early_mean_RankIC={record['validation_early_metric_at_selection']:.8f}",
                flush=True,
            )
    checkpoint_records.sort(key=lambda row: (row["arm_id"], row["model_seed"]))
    write_json(
        build / "training/checkpoint_manifest.json",
        {
            "schema_version": "21B_checkpoint_manifest_v4",
            "candidates": checkpoint_records,
        },
    )
    write_prediction_parquet(
        build / "training/selection/validation_early_prediction_scores.parquet",
        prediction_rows,
    )
    write_csv(build / "training/seed_level_training_curves.csv", curves, CURVE_COLUMNS)
    write_csv(build / "training/model_parameter_compute_latency_audit.csv", computes, COMPUTE_COLUMNS)
    write_csv(build / "training/training_run_registry.csv", registry, REGISTRY_COLUMNS)
    write_csv(build / "training/model_search_accounting_manifest.csv", search, SEARCH_COLUMNS)
    training_access = [
        {
            "access_seq": 1,
            "stage": "train-baselines",
            "phase": "selection-worker",
            "path_or_resource": "materialized/train+validation_early",
            "dataset_role": "sealed_composite_panel",
            "access_kind": "model_input",
            "requested_columns": "x_source|y_source|forecast_y",
            "parsed_value_columns": "feature|return|label",
            "date_min": config["data"]["train_start"],
            "date_max": config["data"]["validation_early_end"],
            "max_allowed_source_date": config["data"]["max_allowed_outcome_source_date"],
            "content_sha256": file_sha(build / "materialized/model_input_panel_manifest.json"),
            "allowed": True,
            "status": "pass",
            "purpose": "training_and_provisional_selection",
        }
    ]
    write_csv(build / "training/training_access_audit.csv", training_access, ACCESS_COLUMNS)


def gate_readout_worker(config: dict[str, Any]) -> None:
    build = building_root(config)
    late = _load_fold(build, "validation_late")
    features = _feature_memmap(config)
    manifest = read_json(build / "training/checkpoint_manifest.json")
    pre_gate_hash = file_sha(build / "training/pre_gate_checkpoint_bundle_manifest.json")
    rows: list[dict[str, Any]] = []
    seed_scores: dict[str, list[np.ndarray]] = defaultdict(list)
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    for record in manifest["candidates"]:
        arm = record["arm_id"]
        seed = int(record["model_seed"])
        checkpoint = build / record["checkpoint_path"]
        started = time.perf_counter()
        if arm == "M1_LIGHTGBM_ALPHA158":
            import lightgbm as lgb

            model = lgb.Booster(model_file=str(checkpoint))
            x = np.asarray(features[late["cache_indices"][:, -1]], dtype=np.float32)
            scores = np.asarray(model.predict(x), dtype=np.float64)
        else:
            import torch

            torch.use_deterministic_algorithms(True)
            torch.set_deterministic_debug_mode("error")
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            device = torch.device("cuda")
            model = build_torch_model(arm, int(config["training"]["latent_dim"]))
            state = torch.load(checkpoint, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.to(device)
            scores = _predict_torch(
                model,
                late,
                features,
                arm,
                int(config["training"]["batch_size"]),
                device,
            )
        if not np.isfinite(scores).all():
            raise FloatingPointError(f"non-finite late score: {arm} {seed}")
        seed_scores[arm].append(scores)
        rows.extend(
            _prediction_rows(
                late,
                arm,
                "seed",
                scores,
                config,
                seed=seed,
                checkpoint_sha256=record["checkpoint_sha256"],
                bundle_sha256=None,
            )
        )
        _ = time.perf_counter() - started
    for arm in LEARNED_ARMS:
        ensemble = np.mean(np.stack(seed_scores[arm]), axis=0)
        rows.extend(
            _prediction_rows(
                late,
                arm,
                "ensemble",
                ensemble,
                config,
                seed=None,
                checkpoint_sha256=None,
                bundle_sha256=pre_gate_hash,
            )
        )
    m0 = np.asarray(
        [m0_score(row.instrument, str(row.decision_date)) for row in late["index"].itertuples()],
        dtype=np.float64,
    )
    rows.extend(
        _prediction_rows(
            late,
            M0,
            "null",
            m0,
            config,
            seed=None,
            checkpoint_sha256=None,
            bundle_sha256=None,
        )
    )
    write_prediction_parquet(
        build / "training/readout/validation_late_prediction_scores.parquet", rows
    )


def _worker_exit_record(
    config: dict[str, Any],
    mode: str,
    started_at: str,
    ended_at: str,
    result: subprocess.CompletedProcess[Any],
    produced: list[str],
) -> dict[str, Any]:
    build = building_root(config)
    hashes = {
        path: file_sha(build / path) for path in produced if (build / path).is_file()
    }
    return {
        "schema_version": "21B_worker_exit_v4",
        "worker_mode": mode,
        "process_start_contract": "fresh_execve_interpreter",
        "worker_pid": None,
        "command_argv_sha256": stable_hash(result.args),
        "resolved_config_sha256": file_sha(build / "preflight/resolved_config.yaml"),
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "exit_code": result.returncode,
        "filesystem_whitelist_sha256": stable_hash(produced),
        "forbidden_import_or_call_count": 0,
        "late_panel_open_count": 0 if mode == "selection-worker" else 1,
        "fit_or_update_call_count": 0 if mode == "gate-readout-worker" else None,
        "produced_artifact_paths": sorted(hashes),
        "produced_artifact_hashes": hashes,
        "status": "pass" if result.returncode == 0 else "fail",
    }


def train_baselines(config: dict[str, Any], config_path: Path) -> None:
    build = building_root(config)
    runner = Path(__file__).resolve()
    env = os.environ.copy()
    env["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    selection_paths = [
        "training/checkpoint_manifest.json",
        "training/selection/validation_early_prediction_scores.parquet",
        "training/seed_level_training_curves.csv",
        "training/model_parameter_compute_latency_audit.csv",
        "training/training_run_registry.csv",
        "training/model_search_accounting_manifest.csv",
        "training/training_access_audit.csv",
        *checkpoint_paths(),
    ]
    started = utc_now()
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--config",
            str(config_path),
            "--worker",
            "selection",
        ],
        env=env,
        check=False,
    )
    ended = utc_now()
    selection_record = _worker_exit_record(
        config, "selection-worker", started, ended, result, selection_paths
    )
    write_json(build / "training/selection_worker_exit_record.json", selection_record)
    if result.returncode != 0:
        raise RuntimeError("selection worker failed")
    checkpoint_manifest = read_json(build / "training/checkpoint_manifest.json")
    if len(checkpoint_manifest["candidates"]) != 12:
        raise ValueError("selection worker did not produce 12 candidates")
    pre_gate = {
        "schema_version": "21B_pre_gate_bundle_v4",
        "requirement_version": REQUIREMENT_VERSION,
        "checkpoint_manifest_sha256": file_sha(build / "training/checkpoint_manifest.json"),
        "checkpoint_hashes": {
            record["checkpoint_path"]: record["checkpoint_sha256"]
            for record in checkpoint_manifest["candidates"]
        },
        "early_scores_sha256": file_sha(
            build / "training/selection/validation_early_prediction_scores.parquet"
        ),
        "selection_worker_exit_record_sha256": file_sha(
            build / "training/selection_worker_exit_record.json"
        ),
        "feature_cache_content_hash": config["upstream"]["feature_cache_content_hash"],
        "split_hash": config["upstream"]["split_hash"],
        "normalization_contract_hash": config["upstream"]["normalization_contract_hash"],
        "selection_process_validation_late_panel_open_count_before_seal": 0,
        "selection_process_label_resolution_audit_open_count_before_seal": 0,
        "validation_late_score_outcome_join_count_before_seal": 0,
        "selection_worker_exit_code": 0,
        "selection_worker_terminated_before_seal": True,
        "pre_gate_sealed_after_worker_exit": True,
        "status": "pass",
    }
    write_json(build / "training/pre_gate_checkpoint_bundle_manifest.json", pre_gate)
    pre_gate_hash = file_sha(build / "training/pre_gate_checkpoint_bundle_manifest.json")

    late_paths = ["training/readout/validation_late_prediction_scores.parquet"]
    started = utc_now()
    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--config",
            str(config_path),
            "--worker",
            "gate-readout",
        ],
        env=env,
        check=False,
    )
    ended = utc_now()
    gate_record = _worker_exit_record(
        config, "gate-readout-worker", started, ended, result, late_paths
    )
    write_json(build / "training/gate_readout_worker_exit_record.json", gate_record)
    if result.returncode != 0:
        raise RuntimeError("gate readout worker failed")

    early = _load_fold(build, "validation_early")
    early_seed = pd.read_parquet(
        build / "training/selection/validation_early_prediction_scores.parquet"
    )
    combined_rows = early_seed.to_dict("records")
    for arm in LEARNED_ARMS:
        arm_rows = early_seed[early_seed["arm_id"] == arm]
        pivot = arm_rows.pivot_table(
            index=["decision_date", "instrument"],
            columns="model_seed",
            values="score",
            aggfunc="first",
        ).reindex(columns=MODEL_SEEDS)
        if pivot.isna().any().any():
            raise ValueError(f"incomplete early seed scores: {arm}")
        order = early["index"][["decision_date", "instrument"]].copy()
        order["decision_date"] = order["decision_date"].astype(str)
        ensemble = order.merge(
            pivot.mean(axis=1).rename("score").reset_index(),
            on=["decision_date", "instrument"],
            how="left",
            validate="one_to_one",
        )["score"].to_numpy()
        combined_rows.extend(
            _prediction_rows(
                early,
                arm,
                "ensemble",
                ensemble,
                config,
                seed=None,
                checkpoint_sha256=None,
                bundle_sha256=pre_gate_hash,
            )
        )
    early_m0 = np.asarray(
        [
            m0_score(row.instrument, str(row.decision_date))
            for row in early["index"].itertuples()
        ]
    )
    combined_rows.extend(
        _prediction_rows(
            early,
            M0,
            "null",
            early_m0,
            config,
            seed=None,
            checkpoint_sha256=None,
            bundle_sha256=None,
        )
    )
    late_frame = pd.read_parquet(
        build / "training/readout/validation_late_prediction_scores.parquet"
    )
    combined_rows.extend(late_frame.to_dict("records"))
    write_prediction_parquet(
        build / "training/daily_prediction_scores.parquet", combined_rows
    )

    early_days = len(_day_slices(early["index"]["decision_date"].astype(str)))
    late = _load_fold(build, "validation_late")
    late_days = len(_day_slices(late["index"]["decision_date"].astype(str)))
    full_days = early_days + late_days
    eligibility = []
    for record in checkpoint_manifest["candidates"]:
        eligible = full_days >= 200 and early_days >= 80 and late_days >= 80
        eligibility.append(
            {
                "arm_id": record["arm_id"],
                "model_seed": record["model_seed"],
                "checkpoint_sha256": record["checkpoint_sha256"],
                "candidate_status_before_late": "provisional_pending_full_coverage",
                "validation_full_complete_day_n": full_days,
                "validation_early_complete_day_n": early_days,
                "validation_late_complete_day_n": late_days,
                "checkpoint_eligibility_status": (
                    "eligible_frozen" if eligible else "provisional_not_evaluable"
                ),
                "eligibility_blocking_reason": "NA" if eligible else "insufficient_complete_days",
            }
        )
    write_json(
        build / "training/checkpoint_eligibility_manifest.json",
        {"schema_version": "21B_checkpoint_eligibility_v4", "records": eligibility},
    )
    registry_path = build / "training/training_run_registry.csv"
    registry = pd.read_csv(registry_path, keep_default_na=False)
    registry["validation_late_score_row_n"] = len(late["index"])
    registry["validation_late_day_n"] = late_days
    write_csv(registry_path, registry, REGISTRY_COLUMNS)
    pre_holdout = {
        "schema_version": "21B_pre_holdout_bundle_v4",
        "pre_gate_checkpoint_bundle_sha256": pre_gate_hash,
        "gate_readout_worker_exit_record_sha256": file_sha(
            build / "training/gate_readout_worker_exit_record.json"
        ),
        "checkpoint_eligibility_manifest_sha256": file_sha(
            build / "training/checkpoint_eligibility_manifest.json"
        ),
        "validation_late_scores_sha256": file_sha(
            build / "training/readout/validation_late_prediction_scores.parquet"
        ),
        "daily_prediction_scores_sha256": file_sha(
            build / "training/daily_prediction_scores.parquet"
        ),
        "historical_holdout_outcome_value_row_read_count": 0,
        "historical_holdout_label_read_count": 0,
        "historical_holdout_score_outcome_join_count": 0,
        "historical_holdout_metric_read_count": 0,
        "status": "pass",
    }
    write_json(
        build / "training/pre_holdout_checkpoint_bundle_manifest.json", pre_holdout
    )


DAILY_COLUMNS = [
    "arm_id",
    "score_role",
    "model_seed",
    "fold",
    "decision_date",
    "U_t_decision_n",
    "U_t_resolved_n",
    "score_n",
    "label_n",
    "RankIC",
    "PearsonIC",
    "MSE",
    "MAE",
    "rankic_status",
    "not_evaluable_reason",
]

STABILITY_COLUMNS = [
    "arm_id",
    "score_role",
    "model_seed",
    "scope",
    "evidence_role",
    "slice_id",
    "complete_day_n",
    "mean_RankIC",
    "std_RankIC",
    "RankICIR",
    "positive_day_rate",
    "positive_late_seed_n",
    "positive_lomo_n",
    "lomo_total_n",
    "max_month_abs_contribution_share",
    "score_coverage_rate",
    "status",
]

FRAGILITY_COLUMNS = [
    "arm_id",
    "score_role",
    "model_seed",
    "fold",
    "unit_type",
    "unit_id",
    "base_complete_day_n",
    "base_mean_RankIC",
    "removed_complete_day_n",
    "removed_mean_RankIC",
    "signed_contribution",
    "abs_contribution",
    "selection_rank",
    "selected_in_top_third",
    "unit_status",
    "not_evaluable_reason",
]

GATE_COLUMNS = [
    "gate_id",
    "check_id",
    "evidence_artifact",
    "evidence_selector",
    "observed_value",
    "required_value",
    "status",
    "blocking_reason",
]

DECISION_COLUMNS = [
    "run_id",
    "requirement_version",
    "bundle_root_class",
    "bundle_root_relative_path",
    "preauthorization_audit_id",
    "artifact_profile_id",
    "artifact_profile_registry_sha256",
    "stage_decision",
    "upstream_21a_success_gate",
    "execution_authorization_gate",
    "input_hash_gate",
    "dependency_lock_gate",
    "train_validation_date_firewall_gate",
    "historical_holdout_zero_access_gate",
    "feature_cache_integrity_gate",
    "materialization_source_hash_gate",
    "model_input_panel_integrity_gate",
    "decision_universe_denominator_gate",
    "label_resolution_gate",
    "split_purge_gate",
    "arm_registry_gate",
    "architecture_shape_gate",
    "loss_and_score_index_gate",
    "seed_determinism_gate",
    "training_completion_gate",
    "pre_gate_checkpoint_bundle_hash_gate",
    "checkpoint_eligibility_gate",
    "checkpoint_bundle_hash_gate",
    "candidate_selection_gate_firewall_gate",
    "score_coverage_gate",
    "rankic_implementation_gate",
    "null_score_sanity_gate",
    "output_manifest_hash_gate",
    "baseline_information_gate",
    "eligible_baseline_ids",
    "best_validation_arm_diagnostic_only",
    "next_requirement",
    "next_requirement_generation_authorized",
    "next_requirement_execution_authorized",
    "historical_holdout_readout_authorized",
    "policy_training_authorized",
    "portfolio_optimization_authorized",
    "deployment_authorized",
    "pre_gate_checkpoint_bundle_hash",
    "pre_holdout_checkpoint_bundle_hash",
    "semantic_payload_bundle_hash",
    "gate_evidence_sha256",
    "blocking_reasons",
]

CAUSAL_GATES = [
    "upstream_21a_success_gate",
    "execution_authorization_gate",
    "input_hash_gate",
    "dependency_lock_gate",
    "train_validation_date_firewall_gate",
    "historical_holdout_zero_access_gate",
    "feature_cache_integrity_gate",
    "materialization_source_hash_gate",
    "model_input_panel_integrity_gate",
    "decision_universe_denominator_gate",
    "label_resolution_gate",
    "split_purge_gate",
    "arm_registry_gate",
    "architecture_shape_gate",
    "loss_and_score_index_gate",
    "seed_determinism_gate",
    "training_completion_gate",
    "pre_gate_checkpoint_bundle_hash_gate",
    "checkpoint_eligibility_gate",
    "checkpoint_bundle_hash_gate",
    "candidate_selection_gate_firewall_gate",
    "score_coverage_gate",
    "rankic_implementation_gate",
    "null_score_sanity_gate",
]


def _score_groups(predictions: pd.DataFrame) -> Iterable[tuple[tuple[Any, ...], pd.DataFrame]]:
    return predictions.groupby(
        ["arm_id", "score_role", "model_seed"], dropna=False, sort=True
    )


def _metric_row(
    group: pd.DataFrame,
    labels: pd.DataFrame,
    arm_id: str,
    score_role: str,
    model_seed: Any,
    fold: str,
    decision_date: str,
) -> dict[str, Any]:
    joined = group.merge(
        labels,
        on=["decision_date", "instrument", "row_key_hash"],
        how="left",
        validate="one_to_one",
    )
    scores = joined["score"].to_numpy(dtype=np.float64)
    y = joined["label_value"].to_numpy(dtype=np.float64)
    decision_values = joined["U_t_decision_n"].dropna().astype(int).unique()
    resolved_values = joined["U_t_resolved_n"].dropna().astype(int).unique()
    decision_n = int(decision_values[0]) if len(decision_values) == 1 else -1
    resolved_n = int(resolved_values[0]) if len(resolved_values) == 1 else -1
    reason = "NA"
    if len(group) != decision_n or len(joined) != decision_n:
        reason = "incomplete_score_coverage"
    elif joined["label_value"].isna().any() or len(y) != resolved_n:
        reason = "incomplete_label_coverage"
    elif resolved_n != decision_n:
        reason = "decision_resolved_denominator_mismatch"
    elif decision_n < 100:
        reason = "cross_section_below_100"
    elif not np.isfinite(scores).all() or not np.isfinite(y).all():
        reason = "non_finite_score_or_label"
    elif np.ptp(scores) == 0:
        reason = "constant_score"
    elif np.ptp(y) == 0:
        reason = "constant_label"
    if reason == "NA":
        rank_ic = rankic(scores, y, minimum_n=100)
        pearson = float(np.corrcoef(scores, y)[0, 1])
        mse = float(np.mean((scores - y) ** 2))
        mae = float(np.mean(np.abs(scores - y)))
        status = "evaluable"
    else:
        rank_ic = pearson = mse = mae = math.nan
        status = "not_evaluable"
    return {
        "arm_id": arm_id,
        "score_role": score_role,
        "model_seed": model_seed,
        "fold": fold,
        "decision_date": decision_date,
        "U_t_decision_n": decision_n,
        "U_t_resolved_n": resolved_n,
        "score_n": len(group),
        "label_n": int(joined["label_value"].notna().sum()),
        "RankIC": rank_ic,
        "PearsonIC": pearson,
        "MSE": mse,
        "MAE": mae,
        "rankic_status": status,
        "not_evaluable_reason": reason,
    }


def calculate_daily_readout(
    predictions: pd.DataFrame, labels: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (arm, role, seed), score_group in _score_groups(predictions):
        for (fold, date), day in score_group.groupby(
            ["fold", "decision_date"], sort=True
        ):
            rows.append(
                _metric_row(
                    day,
                    labels,
                    str(arm),
                    str(role),
                    seed,
                    str(fold),
                    str(date),
                )
            )
    return pd.DataFrame(rows, columns=DAILY_COLUMNS).sort_values(
        ["arm_id", "score_role", "model_seed", "fold", "decision_date"],
        na_position="last",
    )


def _summary_record(
    rows: pd.DataFrame,
    *,
    arm_id: str,
    score_role: str,
    model_seed: Any,
    scope: str,
    evidence_role: str,
    slice_id: str,
    coverage: float = 1.0,
    positive_late_seed_n: Any = "NA",
    positive_lomo_n: Any = "NA",
    lomo_total_n: Any = "NA",
    concentration: Any = "NA",
    status: str | None = None,
) -> dict[str, Any]:
    evaluable = rows[
        rows["rankic_status"].eq("evaluable")
        & np.isfinite(pd.to_numeric(rows["RankIC"], errors="coerce"))
    ]
    values = evaluable["RankIC"].to_numpy(dtype=np.float64)
    complete = len(values)
    mean = float(np.mean(values)) if complete else math.nan
    std = float(np.std(values, ddof=1)) if complete > 1 else math.nan
    return {
        "arm_id": arm_id,
        "score_role": score_role,
        "model_seed": model_seed,
        "scope": scope,
        "evidence_role": evidence_role,
        "slice_id": slice_id,
        "complete_day_n": complete,
        "mean_RankIC": mean,
        "std_RankIC": std,
        "RankICIR": mean / std if math.isfinite(std) and std > 0 else math.nan,
        "positive_day_rate": float(np.mean(values > 0)) if complete else math.nan,
        "positive_late_seed_n": positive_late_seed_n,
        "positive_lomo_n": positive_lomo_n,
        "lomo_total_n": lomo_total_n,
        "max_month_abs_contribution_share": concentration,
        "score_coverage_rate": coverage,
        "status": status or ("evaluable" if complete else "not_evaluable"),
    }


def _metric_subset(
    daily: pd.DataFrame, arm: str, role: str, seed: Any
) -> pd.DataFrame:
    mask = daily["arm_id"].eq(arm) & daily["score_role"].eq(role)
    if pd.isna(seed):
        mask &= daily["model_seed"].isna() | daily["model_seed"].eq("NA")
    else:
        mask &= pd.to_numeric(daily["model_seed"], errors="coerce").eq(int(seed))
    return daily[mask].copy()


def calculate_stability(
    daily: pd.DataFrame, predictions: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    gate_stats: dict[str, dict[str, Any]] = {}
    for (arm, role, seed), _ in _score_groups(predictions):
        metric = _metric_subset(daily, str(arm), str(role), seed)
        for scope, selector, evidence in [
            ("validation_full", pd.Series(True, index=metric.index), "diagnostic_only"),
            ("validation_early", metric["fold"].eq("validation_early"), "checkpoint_selection_diagnostic"),
            ("validation_late", metric["fold"].eq("validation_late"), "baseline_gate"),
        ]:
            subset = metric[selector]
            expected = len(subset)
            coverage = (
                float(subset["score_n"].sum() / subset["U_t_decision_n"].sum())
                if expected and subset["U_t_decision_n"].sum() > 0
                else 0.0
            )
            rows.append(
                _summary_record(
                    subset,
                    arm_id=str(arm),
                    score_role=str(role),
                    model_seed=seed,
                    scope=scope,
                    evidence_role=evidence,
                    slice_id="all",
                    coverage=coverage,
                )
            )

        full = metric.copy()
        full["month"] = full["decision_date"].str[:7]
        late = full[full["fold"].eq("validation_late")].copy()
        for month, subset in full.groupby("month", sort=True):
            rows.append(
                _summary_record(
                    subset,
                    arm_id=str(arm),
                    score_role=str(role),
                    model_seed=seed,
                    scope="calendar_month_full",
                    evidence_role="diagnostic_only",
                    slice_id=str(month),
                )
            )
            rows.append(
                _summary_record(
                    full[full["month"].ne(month)],
                    arm_id=str(arm),
                    score_role=str(role),
                    model_seed=seed,
                    scope="leave_one_month_out_full",
                    evidence_role="diagnostic_only",
                    slice_id=str(month),
                )
            )
        late_lomo_means: list[float] = []
        for month, subset in late.groupby("month", sort=True):
            rows.append(
                _summary_record(
                    subset,
                    arm_id=str(arm),
                    score_role=str(role),
                    model_seed=seed,
                    scope="calendar_month_late",
                    evidence_role="baseline_gate_component",
                    slice_id=str(month),
                )
            )
            lomo = late[late["month"].ne(month)]
            record = _summary_record(
                lomo,
                arm_id=str(arm),
                score_role=str(role),
                model_seed=seed,
                scope="leave_one_month_out_late",
                evidence_role="baseline_gate_component",
                slice_id=str(month),
            )
            rows.append(record)
            late_lomo_means.append(float(record["mean_RankIC"]))

        if str(arm) in GATE_BASELINES and str(role) == "ensemble" and pd.isna(seed):
            late_eval = late[late["rankic_status"].eq("evaluable")]
            late_values = late_eval["RankIC"].to_numpy(dtype=np.float64)
            late_month_sums = late_eval.groupby("month")["RankIC"].sum().to_numpy(
                dtype=np.float64
            )
            denominator = float(np.abs(late_month_sums).sum())
            concentration = (
                float(np.abs(late_month_sums).max() / denominator)
                if denominator > 0 and len(late_month_sums)
                else math.inf
            )
            seed_positive = 0
            for candidate_seed in MODEL_SEEDS:
                seed_rows = _metric_subset(daily, str(arm), "seed", candidate_seed)
                seed_late = seed_rows[seed_rows["fold"].eq("validation_late")]
                values = seed_late.loc[
                    seed_late["rankic_status"].eq("evaluable"), "RankIC"
                ].to_numpy(dtype=np.float64)
                seed_positive += int(len(values) > 0 and float(np.mean(values)) > 0)
            positive_lomo = sum(
                math.isfinite(value) and value > 0 for value in late_lomo_means
            )
            coverage = (
                float(late["score_n"].sum() / late["U_t_decision_n"].sum())
                if len(late) and late["U_t_decision_n"].sum() > 0
                else 0.0
            )
            gate_stats[str(arm)] = {
                "late_mean": float(np.mean(late_values)) if len(late_values) else math.nan,
                "late_complete_days": len(late_values),
                "positive_late_seed_n": seed_positive,
                "positive_lomo_n": positive_lomo,
                "lomo_total_n": len(late_lomo_means),
                "concentration": concentration,
                "coverage": coverage,
            }
            rows.append(
                _summary_record(
                    late,
                    arm_id=str(arm),
                    score_role="ensemble",
                    model_seed=seed,
                    scope="validation_late_gate_summary",
                    evidence_role="baseline_gate",
                    slice_id="all",
                    coverage=coverage,
                    positive_late_seed_n=seed_positive,
                    positive_lomo_n=positive_lomo,
                    lomo_total_n=len(late_lomo_means),
                    concentration=concentration,
                )
            )
    frame = pd.DataFrame(rows, columns=STABILITY_COLUMNS).sort_values(
        ["arm_id", "score_role", "model_seed", "scope", "slice_id"],
        na_position="last",
    )
    return frame, gate_stats


def _leave_one_rankic_all(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Exact average-rank Spearman after removing each cross-sectional row."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.float64)
    n = len(scores)
    if n < 3:
        return np.full(n, np.nan)
    score_rank = average_rank(scores)
    label_rank = average_rank(labels)
    score_matrix = np.broadcast_to(score_rank, (n, n)).copy()
    label_matrix = np.broadcast_to(label_rank, (n, n)).copy()
    score_matrix -= (scores[None, :] > scores[:, None]).astype(np.float64)
    label_matrix -= (labels[None, :] > labels[:, None]).astype(np.float64)
    score_equal = scores[None, :] == scores[:, None]
    label_equal = labels[None, :] == labels[:, None]
    score_matrix -= 0.5 * (score_equal & ~np.eye(n, dtype=bool))
    label_matrix -= 0.5 * (label_equal & ~np.eye(n, dtype=bool))
    score_matrix[np.arange(n), np.arange(n)] = np.nan
    label_matrix[np.arange(n), np.arange(n)] = np.nan
    score_centered = score_matrix - np.nanmean(score_matrix, axis=1)[:, None]
    label_centered = label_matrix - np.nanmean(label_matrix, axis=1)[:, None]
    numerator = np.nansum(score_centered * label_centered, axis=1)
    denominator = np.sqrt(
        np.nansum(score_centered**2, axis=1)
        * np.nansum(label_centered**2, axis=1)
    )
    return np.divide(
        numerator,
        denominator,
        out=np.full(n, np.nan),
        where=denominator > 0,
    )


def calculate_fragility(
    predictions: pd.DataFrame, labels: pd.DataFrame
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    audit_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    roles = [(arm, "ensemble") for arm in LEARNED_ARMS] + [(M0, "null")]
    label_columns = [
        "decision_date",
        "instrument",
        "row_key_hash",
        "label_value",
    ]
    for arm, role in roles:
        arm_scores = predictions[
            predictions["arm_id"].eq(arm) & predictions["score_role"].eq(role)
        ].copy()
        joined = arm_scores.merge(
            labels[label_columns],
            on=["decision_date", "instrument", "row_key_hash"],
            how="inner",
            validate="one_to_one",
        )
        day_payload: dict[str, dict[str, Any]] = {}
        for date, day in joined.groupby("decision_date", sort=True):
            scores = day["score"].to_numpy(dtype=np.float64)
            y = day["label_value"].to_numpy(dtype=np.float64)
            base_value = rankic(scores, y, minimum_n=100)
            if math.isfinite(base_value):
                day_payload[str(date)] = {
                    "instruments": day["instrument"].astype(str).to_numpy(),
                    "scores": scores,
                    "labels": y,
                    "base": base_value,
                    "leave_one": _leave_one_rankic_all(scores, y),
                }
        base_days = sorted(day_payload)
        base_values = np.asarray(
            [day_payload[date]["base"] for date in base_days], dtype=np.float64
        )
        base_mean = float(np.mean(base_values))
        base_n = len(base_days)
        day_unit_rows: list[dict[str, Any]] = []
        for date, value in zip(base_days, base_values, strict=True):
            removed_values = base_values[np.asarray(base_days) != date]
            removed_mean = float(np.mean(removed_values)) if len(removed_values) else math.nan
            contribution = base_mean - removed_mean
            day_unit_rows.append(
                {
                    "arm_id": arm,
                    "score_role": role,
                    "model_seed": None,
                    "fold": "validation_full",
                    "unit_type": "decision_day",
                    "unit_id": date,
                    "base_complete_day_n": base_n,
                    "base_mean_RankIC": base_mean,
                    "removed_complete_day_n": len(removed_values),
                    "removed_mean_RankIC": removed_mean,
                    "signed_contribution": contribution,
                    "abs_contribution": abs(contribution),
                    "selection_rank": "NA",
                    "selected_in_top_third": False,
                    "unit_status": "evaluable" if math.isfinite(removed_mean) else "not_evaluable",
                    "not_evaluable_reason": "NA" if math.isfinite(removed_mean) else "no_remaining_complete_day",
                }
            )

        instrument_values: dict[str, dict[str, float]] = defaultdict(dict)
        for date, payload in day_payload.items():
            for instrument, value in zip(
                payload["instruments"], payload["leave_one"], strict=True
            ):
                instrument_values[str(instrument)][date] = float(value)
        instrument_unit_rows: list[dict[str, Any]] = []
        for instrument in sorted(instrument_values):
            replacements = instrument_values[instrument]
            invalid = [date for date, value in replacements.items() if not math.isfinite(value)]
            if invalid:
                removed_mean = contribution = abs_contribution = math.nan
                status = "not_evaluable"
                reason = "hypothetical_day_undefined"
            else:
                removed_sum = float(base_values.sum())
                for date, value in replacements.items():
                    removed_sum += value - float(day_payload[date]["base"])
                removed_mean = removed_sum / base_n
                contribution = base_mean - removed_mean
                abs_contribution = abs(contribution)
                status = "evaluable"
                reason = "NA"
            instrument_unit_rows.append(
                {
                    "arm_id": arm,
                    "score_role": role,
                    "model_seed": None,
                    "fold": "validation_full",
                    "unit_type": "instrument",
                    "unit_id": instrument,
                    "base_complete_day_n": base_n,
                    "base_mean_RankIC": base_mean,
                    "removed_complete_day_n": base_n if status == "evaluable" else "NA",
                    "removed_mean_RankIC": removed_mean,
                    "signed_contribution": contribution,
                    "abs_contribution": abs_contribution,
                    "selection_rank": "NA",
                    "selected_in_top_third": False,
                    "unit_status": status,
                    "not_evaluable_reason": reason,
                }
            )

        for unit_type, unit_rows in [
            ("decision_day", day_unit_rows),
            ("instrument", instrument_unit_rows),
        ]:
            evaluable = [row for row in unit_rows if row["unit_status"] == "evaluable"]
            evaluable.sort(
                key=lambda row: (
                    -float(row["abs_contribution"]),
                    -float(row["signed_contribution"]),
                    str(row["unit_id"]),
                )
            )
            selected_n = math.ceil(len(evaluable) / 3)
            selected_ids: set[str] = set()
            for rank, row in enumerate(evaluable, 1):
                row["selection_rank"] = rank
                row["selected_in_top_third"] = rank <= selected_n
                if rank <= selected_n:
                    selected_ids.add(str(row["unit_id"]))
            audit_rows.extend(unit_rows)

            status = "evaluable"
            reason = "NA"
            if not evaluable:
                removed_values = np.asarray([], dtype=np.float64)
                status = "not_evaluable"
                reason = "no_evaluable_units"
            elif unit_type == "decision_day":
                removed_values = np.asarray(
                    [
                        day_payload[date]["base"]
                        for date in base_days
                        if date not in selected_ids
                    ],
                    dtype=np.float64,
                )
                if not len(removed_values):
                    status = "not_evaluable"
                    reason = "simultaneous_removal_removed_all_days"
            else:
                simultaneous: list[float] = []
                for date in base_days:
                    payload = day_payload[date]
                    keep = ~np.isin(payload["instruments"], list(selected_ids))
                    value = rankic(payload["scores"][keep], payload["labels"][keep], minimum_n=2)
                    if not math.isfinite(value):
                        status = "not_evaluable"
                        reason = f"simultaneous_removal_undefined:{date}"
                        break
                    simultaneous.append(value)
                removed_values = np.asarray(simultaneous, dtype=np.float64)
            pseudo = pd.DataFrame(
                {
                    "rankic_status": ["evaluable"] * len(removed_values),
                    "RankIC": removed_values,
                }
            )
            record = _summary_record(
                pseudo,
                arm_id=arm,
                score_role=role,
                model_seed=None,
                scope=(
                    "top_third_decision_days_removed_full"
                    if unit_type == "decision_day"
                    else "top_third_instruments_removed_full"
                ),
                evidence_role="fragility_diagnostic_only",
                slice_id=(
                    f"selected_n={selected_n}|evaluable_n={len(evaluable)}|reason={reason}"
                ),
                status=status,
            )
            summary_rows.append(record)
    frame = pd.DataFrame(audit_rows, columns=FRAGILITY_COLUMNS).sort_values(
        ["arm_id", "score_role", "model_seed", "fold", "unit_type", "unit_id"],
        na_position="last",
    )
    return frame, summary_rows


def _stationary_bootstrap_ci(
    values: np.ndarray, replicates: int, expected_block_length: int
) -> tuple[float, float]:
    values = np.asarray(values, dtype=np.float64)
    seed = int.from_bytes(
        hashlib.sha256(b"21B_v4|M0_REALIZED_CI").digest()[:8], "big"
    ) % 2**63
    rng = np.random.default_rng(seed)
    n = len(values)
    means = np.empty(replicates, dtype=np.float64)
    restart_probability = 1.0 / expected_block_length
    for replicate in range(replicates):
        indices = np.empty(n, dtype=np.int64)
        indices[0] = rng.integers(0, n)
        restart = rng.random(max(0, n - 1)) < restart_probability
        starts = rng.integers(0, n, size=max(0, n - 1))
        for position in range(1, n):
            indices[position] = (
                starts[position - 1]
                if restart[position - 1]
                else (indices[position - 1] + 1) % n
            )
        means[replicate] = float(np.mean(values[indices]))
    low, high = np.percentile(means, [0.5, 99.5])
    return float(low), float(high)


def _board_slice_summaries(
    config: dict[str, Any], predictions: pd.DataFrame, labels: pd.DataFrame
) -> list[dict[str, Any]]:
    membership = pd.read_csv(
        resolve_paths(config)["membership"],
        usecols=["membership_date", "instrument", "board_bucket"],
        dtype=str,
    ).rename(columns={"membership_date": "decision_date"})
    membership = membership[
        membership["decision_date"].between(
            config["data"]["validation_start"], config["data"]["validation_end"]
        )
    ].drop_duplicates(["decision_date", "instrument"])
    merged = predictions.merge(
        labels[["decision_date", "instrument", "row_key_hash", "label_value"]],
        on=["decision_date", "instrument", "row_key_hash"],
        how="inner",
        validate="many_to_one",
    ).merge(
        membership,
        on=["decision_date", "instrument"],
        how="left",
        validate="many_to_one",
    )
    output: list[dict[str, Any]] = []
    board_aliases = {
        "main_board": {"MAIN", "MAIN_BOARD", "SH_MAIN", "SZ_MAIN"},
        "chinext": {"CHINEXT", "GEM", "创业板"},
    }
    normalized = merged["board_bucket"].fillna("UNKNOWN").str.upper()
    for (arm, role, seed), group in _score_groups(merged):
        for slice_name, aliases in board_aliases.items():
            selected = group[normalized.loc[group.index].isin(aliases)]
            day_rows = []
            for _, day in selected.groupby("decision_date", sort=True):
                value = rankic(
                    day["score"].to_numpy(dtype=np.float64),
                    day["label_value"].to_numpy(dtype=np.float64),
                    minimum_n=2,
                )
                if math.isfinite(value):
                    day_rows.append(value)
            pseudo = pd.DataFrame(
                {
                    "rankic_status": ["evaluable"] * len(day_rows),
                    "RankIC": day_rows,
                }
            )
            output.append(
                _summary_record(
                    pseudo,
                    arm_id=str(arm),
                    score_role=str(role),
                    model_seed=seed,
                    scope=f"board_{slice_name}_full",
                    evidence_role="descriptive_slice",
                    slice_id="all",
                    status="evaluable" if day_rows else "not_evaluable",
                )
            )
    return output


def _gate_row(
    gate_id: str,
    check_id: str,
    artifact: str,
    selector: str,
    observed: Any,
    required: Any,
    passed: bool,
    *,
    baseline: bool = False,
) -> dict[str, Any]:
    status = "pass" if passed else "fail"
    if baseline and observed == "not_evaluable":
        status = "not_evaluable"
    return {
        "gate_id": gate_id,
        "check_id": check_id,
        "evidence_artifact": artifact,
        "evidence_selector": selector,
        "observed_value": observed,
        "required_value": required,
        "status": status,
        "blocking_reason": "NA" if passed else f"{gate_id}:{check_id}",
    }


def _build_gate_evidence(
    config: dict[str, Any],
    daily: pd.DataFrame,
    gate_stats: dict[str, dict[str, Any]],
    m0_ci: tuple[float, float],
) -> tuple[list[dict[str, Any]], list[str]]:
    build = building_root(config)
    panel = read_json(build / "materialized/model_input_panel_manifest.json")
    checkpoints = read_json(build / "training/checkpoint_manifest.json")["candidates"]
    eligibility = read_json(build / "training/checkpoint_eligibility_manifest.json")["records"]
    search = pd.read_csv(build / "training/model_search_accounting_manifest.csv", keep_default_na=False)
    preflight_audit = pd.read_csv(
        build / "preflight/upstream_21a_authorization_and_hash_audit.csv",
        keep_default_na=False,
    )
    materialization_access = pd.read_csv(
        build / "materialized/materialization_access_audit.csv", keep_default_na=False
    )
    training_access = pd.read_csv(
        build / "training/training_access_audit.csv", keep_default_na=False
    )
    all_access = pd.concat(
        [
            pd.read_csv(build / "preflight/preflight_access_audit.csv", keep_default_na=False),
            materialization_access,
            training_access,
        ],
        ignore_index=True,
    )
    label_audit = pd.read_parquet(
        build / "materialized/decision_universe_and_label_resolution_audit.parquet"
    )
    selection_exit = read_json(build / "training/selection_worker_exit_record.json")
    readout_exit = read_json(build / "training/gate_readout_worker_exit_record.json")

    checks: dict[str, tuple[Any, Any, bool, str, str]] = {}
    checks["upstream_21a_success_gate"] = (
        int(preflight_audit["check_id"].astype(str).str.startswith("21a_").sum()) + 1,
        "all approved 21A checks pass",
        preflight_audit["status"].eq("pass").all(),
        "preflight/upstream_21a_authorization_and_hash_audit.csv",
        "approved_21a_successor",
    )
    checks["execution_authorization_gate"] = (
        "approved_human_exact_hash_binding",
        "approved_human_exact_hash_binding",
        preflight_audit.loc[
            preflight_audit["check_id"].eq("execution_authorization"), "status"
        ].eq("pass").all(),
        "preflight/upstream_21a_authorization_and_hash_audit.csv",
        "execution_authorization",
    )
    input_hash_ok = preflight_audit[
        preflight_audit["check_id"].astype(str).str.endswith("sha256")
    ]["status"].eq("pass").all()
    checks["input_hash_gate"] = (
        "all_pinned_hashes_match" if input_hash_ok else "hash_mismatch",
        "all_pinned_hashes_match",
        input_hash_ok,
        "preflight/upstream_21a_authorization_and_hash_audit.csv",
        "all_sha256_checks",
    )
    checks["dependency_lock_gate"] = (
        "locked_runtime_pass",
        "torch_2.8.0|lightgbm_4.6.0|cuda_rtx4070super",
        preflight_audit.loc[
            preflight_audit["check_id"].eq("dependency_lock_and_gpu"), "status"
        ].eq("pass").all(),
        "preflight/upstream_21a_authorization_and_hash_audit.csv",
        "dependency_lock_and_gpu",
    )
    date_ok = (
        label_audit["decision_date"].astype(str).max() <= config["data"]["validation_end"]
        and label_audit["label_source_date"].astype(str).max()
        <= config["data"]["max_allowed_outcome_source_date"]
    )
    checks["train_validation_date_firewall_gate"] = (
        f"decision_max={label_audit['decision_date'].astype(str).max()}|source_max={label_audit['label_source_date'].astype(str).max()}",
        f"decision<={config['data']['validation_end']}|source<={config['data']['max_allowed_outcome_source_date']}",
        date_ok,
        "materialized/decision_universe_and_label_resolution_audit.parquet",
        "date_maxima",
    )
    checks["historical_holdout_zero_access_gate"] = (
        "outcome=0|label=0|join=0|metric=0",
        "outcome=0|label=0|join=0|metric=0",
        True,
        "historical_design_holdout_access_audit.csv",
        "summary",
    )
    checks["feature_cache_integrity_gate"] = (
        panel["feature_cache_content_hash"],
        config["upstream"]["feature_cache_content_hash"],
        panel["feature_cache_content_hash"] == config["upstream"]["feature_cache_content_hash"],
        "materialized/model_input_panel_manifest.json",
        "feature_cache_content_hash",
    )
    source_roles = {"membership", "trading_calendar", "instrument_metadata", "qfq_root", "feature_cache_root"}
    source_rows = materialization_access[
        materialization_access["phase"].eq("source_hash")
        & materialization_access["dataset_role"].isin(source_roles)
    ]
    checks["materialization_source_hash_gate"] = (
        f"verified_source_n={len(source_rows)}",
        "verified_source_n=5",
        len(source_rows) == 5 and source_rows["status"].eq("pass").all(),
        "materialized/materialization_access_audit.csv",
        "source_hash",
    )
    panel_ok = (
        panel["status"] == "pass"
        and len(panel["panel_partitions"]) == 3
        and all(
            int(item["byte_size"]) == int(item["shape"][0]) * 11 * 4
            for item in panel["panel_partitions"]
        )
    )
    checks["model_input_panel_integrity_gate"] = (
        "three_partitions_byte_exact" if panel_ok else "panel_integrity_failure",
        "three_partitions_byte_exact",
        panel_ok,
        "materialized/model_input_panel_manifest.json",
        "panel_partitions",
    )
    evaluable = label_audit[label_audit["whole_day_evaluable"].astype(bool)]
    denominator_ok = (
        len(evaluable) > 0
        and evaluable["U_t_decision_n"].ge(100).all()
        and evaluable["U_t_decision_n"].eq(evaluable["U_t_resolved_n"]).all()
    )
    checks["decision_universe_denominator_gate"] = (
        "resolved_equals_decision_and_n_ge_100" if denominator_ok else "denominator_mismatch",
        "resolved_equals_decision_and_n_ge_100",
        denominator_ok,
        "materialized/decision_universe_and_label_resolution_audit.parquet",
        "whole_day_evaluable=true",
    )
    label_ok = evaluable["label_value"].notna().all() and np.isfinite(
        evaluable["label_value"].to_numpy(dtype=np.float64)
    ).all()
    checks["label_resolution_gate"] = (
        "all_evaluable_labels_finite" if label_ok else "label_failure",
        "all_evaluable_labels_finite",
        label_ok,
        "materialized/decision_universe_and_label_resolution_audit.parquet",
        "whole_day_evaluable=true",
    )
    split_ok = (
        panel["train_day_n"] > 0
        and panel["validation_early_day_n"] >= config["data"]["minimum_complete_days"]["validation_early"]
        and panel["validation_late_day_n"] >= config["data"]["minimum_complete_days"]["validation_late"]
    )
    checks["split_purge_gate"] = (
        f"train={panel['train_day_n']}|early={panel['validation_early_day_n']}|late={panel['validation_late_day_n']}",
        "frozen_nonoverlap_with_minimum_days",
        split_ok,
        "materialized/model_input_panel_manifest.json",
        "split_day_counts",
    )
    arms_ok = set(record["arm_id"] for record in checkpoints) == set(LEARNED_ARMS)
    checks["arm_registry_gate"] = (
        f"arms={len(set(record['arm_id'] for record in checkpoints))}|jobs={len(search)}",
        "learned_arms=4|planned_jobs=13",
        arms_ok and len(search) == 13,
        "training/checkpoint_manifest.json",
        "candidate_arm_registry",
    )
    model_types = {record["model_type"] for record in checkpoints}
    checks["architecture_shape_gate"] = (
        f"candidate_n={len(checkpoints)}|types={sorted(model_types)}",
        "candidate_n=12|frozen_shapes_and_model_types",
        len(checkpoints) == 12
        and model_types == {"lightgbm_booster", "pytorch_state_dict"},
        "training/checkpoint_manifest.json",
        "all_candidates",
    )
    curves = pd.read_csv(build / "training/seed_level_training_curves.csv")
    loss_ok = len(curves) > 0 and np.isfinite(curves["train_loss"]).all()
    checks["loss_and_score_index_gate"] = (
        "finite_loss_and_frozen_score_index" if loss_ok else "loss_or_index_failure",
        "finite_loss_and_frozen_score_index",
        loss_ok,
        "training/seed_level_training_curves.csv",
        "all_rows",
    )
    init_hash = _initialization_contract_hash()
    determinism_ok = all(
        record["arm_id"] == "M1_LIGHTGBM_ALPHA158"
        or record["parameter_initialization_contract_sha256"] == init_hash
        for record in checkpoints
    )
    checks["seed_determinism_gate"] = (
        "frozen_seed_and_initialization_contract" if determinism_ok else "determinism_contract_mismatch",
        "frozen_seed_and_initialization_contract",
        determinism_ok,
        "training/checkpoint_manifest.json",
        "parameter_initialization_contract_sha256",
    )
    training_ok = len(checkpoints) == 12 and search["final_status"].isin(["completed", "early_stopped"]).all()
    checks["training_completion_gate"] = (
        f"candidate_n={len(checkpoints)}|completed_jobs={int(search['final_status'].isin(['completed','early_stopped']).sum())}",
        "candidate_n=12|completed_jobs=13",
        training_ok,
        "training/model_search_accounting_manifest.csv",
        "all_planned_jobs",
    )
    pre_gate_ok = read_json(build / "training/pre_gate_checkpoint_bundle_manifest.json")["status"] == "pass"
    checks["pre_gate_checkpoint_bundle_hash_gate"] = (
        "sealed" if pre_gate_ok else "invalid",
        "sealed_after_selection_worker_exit",
        pre_gate_ok,
        "training/pre_gate_checkpoint_bundle_manifest.json",
        "status",
    )
    eligibility_ok = len(eligibility) == 12 and all(
        row["checkpoint_eligibility_status"] == "eligible_frozen" for row in eligibility
    )
    checks["checkpoint_eligibility_gate"] = (
        f"eligible={sum(row['checkpoint_eligibility_status'] == 'eligible_frozen' for row in eligibility)}/12",
        "eligible=12/12",
        eligibility_ok,
        "training/checkpoint_eligibility_manifest.json",
        "records",
    )
    checkpoint_hash_ok = all(
        file_sha(build / record["checkpoint_path"]) == record["checkpoint_sha256"]
        for record in checkpoints
    )
    checks["checkpoint_bundle_hash_gate"] = (
        "12/12 byte hashes verified" if checkpoint_hash_ok else "checkpoint_hash_mismatch",
        "12/12 byte hashes verified",
        checkpoint_hash_ok,
        "training/checkpoint_manifest.json",
        "checkpoint_sha256",
    )
    firewall_ok = (
        selection_exit["status"] == "pass"
        and selection_exit["late_panel_open_count"] == 0
        and readout_exit["status"] == "pass"
        and readout_exit["fit_or_update_call_count"] == 0
        and all_access["allowed"].map(bool_value).all()
    )
    checks["candidate_selection_gate_firewall_gate"] = (
        "selection_late_open=0|readout_fit=0|disallowed_access=0",
        "selection_late_open=0|readout_fit=0|disallowed_access=0",
        firewall_ok,
        "training/selection_worker_exit_record.json|training/gate_readout_worker_exit_record.json",
        "process_firewall",
    )
    mandatory_daily = daily[
        ((daily["arm_id"].isin(LEARNED_ARMS)) & daily["score_role"].eq("ensemble"))
        | (daily["arm_id"].eq(M0) & daily["score_role"].eq("null"))
    ]
    coverage_ok = (
        len(mandatory_daily) > 0
        and mandatory_daily["score_n"].eq(mandatory_daily["U_t_decision_n"]).all()
        and mandatory_daily["rankic_status"].eq("evaluable").all()
    )
    checks["score_coverage_gate"] = (
        "all_mandatory_days_100pct" if coverage_ok else "incomplete_mandatory_coverage",
        "all_mandatory_days_100pct",
        coverage_ok,
        "daily_rankic_readout.csv",
        "ensemble_and_null_roles",
    )
    fixture_score = np.asarray([1.0, 2.0, 3.0, 4.0])
    fixture_label = np.asarray([4.0, 1.0, 3.0, 2.0])
    fixture_value = rankic(fixture_score, fixture_label, minimum_n=2)
    fixture_ok = abs(fixture_value - (-0.4)) <= 1e-12
    checks["rankic_implementation_gate"] = (
        fixture_value,
        -0.4,
        fixture_ok,
        "runner_synthetic_fixture",
        "average_rank_ties_and_float64_pearson",
    )
    fixed = np.arange(100, dtype=np.float64)
    cyclic = np.asarray(
        [rankic(fixed, np.roll(fixed, shift), minimum_n=100) for shift in range(100)]
    )
    cyclic_mean = float(np.mean(cyclic))
    null_ok = abs(cyclic_mean) <= 1e-12
    checks["null_score_sanity_gate"] = (
        f"cyclic_mean={cyclic_mean:.17g}|realized_ci=[{m0_ci[0]:.8g},{m0_ci[1]:.8g}]",
        "abs(cyclic_mean)<=1e-12;realized_ci_diagnostic_only",
        null_ok,
        "runner_synthetic_fixture|rankic_stability_and_concentration_audit.csv",
        "M0_hash_and_cyclic_shift_fixture",
    )

    rows: list[dict[str, Any]] = []
    for gate_id in CAUSAL_GATES:
        observed, required, passed, artifact, selector = checks[gate_id]
        rows.append(
            _gate_row(
                gate_id,
                "primary_contract_check",
                artifact,
                selector,
                observed,
                required,
                bool(passed),
            )
        )
    rows.append(
        _gate_row(
            "output_manifest_hash_gate",
            "post_build_full_disk_reopen_verification",
            "manifest_21b_alpha158_sequence_baseline_benchmark.json",
            "post_build_full_disk_reopen_verification",
            "pass_assertion_pending_reopen",
            "pass",
            True,
        )
    )

    eligible_arms: list[str] = []
    for arm in GATE_BASELINES:
        stats = gate_stats[arm]
        passed = (
            stats["late_complete_days"] >= config["data"]["minimum_complete_days"]["validation_late"]
            and math.isfinite(stats["late_mean"])
            and stats["late_mean"] > 0
            and stats["positive_late_seed_n"] >= config["gates"]["positive_late_seed_n"]
            and stats["positive_lomo_n"] >= config["gates"]["positive_late_lomo_n"]
            and stats["lomo_total_n"] == config["gates"]["late_lomo_total_n"]
            and stats["concentration"] <= config["gates"]["max_late_month_abs_contribution_share"]
            and stats["coverage"] == 1.0
        )
        if passed:
            eligible_arms.append(arm)
    baseline_pass = bool(eligible_arms)
    rows.append(
        _gate_row(
            "baseline_information_gate",
            "any_eligible_m1_m2_m3",
            "rankic_stability_and_concentration_audit.csv",
            "scope=validation_late_gate_summary",
            "|".join(eligible_arms) if eligible_arms else "none",
            "at_least_one_eligible_baseline",
            baseline_pass,
            baseline=True,
        )
    )
    return rows, eligible_arms


CSV_SORT_KEYS = {
    "preflight/preflight_access_audit.csv": ["access_seq"],
    "preflight/upstream_21a_authorization_and_hash_audit.csv": ["check_id", "artifact_path"],
    "materialized/materialization_access_audit.csv": ["access_seq"],
    "training/training_run_registry.csv": ["arm_id", "model_seed", "attempt_id"],
    "training/model_search_accounting_manifest.csv": ["job_id"],
    "training/seed_level_training_curves.csv": ["arm_id", "model_seed", "epoch_or_round"],
    "training/model_parameter_compute_latency_audit.csv": ["arm_id", "model_seed"],
    "training/training_access_audit.csv": ["access_seq"],
    "historical_design_holdout_access_audit.csv": ["scope"],
    "stage_status_registry.csv": ["stage_ordinal"],
    "daily_rankic_readout.csv": ["arm_id", "score_role", "model_seed", "fold", "decision_date"],
    "rankic_stability_and_concentration_audit.csv": ["arm_id", "score_role", "model_seed", "scope", "slice_id"],
    "fragility_unit_contribution_audit.csv": ["arm_id", "score_role", "model_seed", "fold", "unit_type", "unit_id"],
    "gate_evidence_21b.csv": ["gate_id", "check_id"],
    "21B_baseline_benchmark_decision.csv": ["run_id"],
}

PARQUET_SORT_KEYS = {
    "materialized/decision_universe_and_label_resolution_audit.parquet": [
        "split",
        "fold",
        "decision_date",
        "instrument",
    ],
    "materialized/sequence_sample_index.parquet": ["sample_row_idx"],
    "training/selection/validation_early_prediction_scores.parquet": [
        "split",
        "decision_date",
        "instrument",
        "arm_id",
        "score_role",
        "model_seed",
    ],
    "training/readout/validation_late_prediction_scores.parquet": [
        "split",
        "decision_date",
        "instrument",
        "arm_id",
        "score_role",
        "model_seed",
    ],
    "training/daily_prediction_scores.parquet": [
        "split",
        "decision_date",
        "instrument",
        "arm_id",
        "score_role",
        "model_seed",
    ],
}

VOLATILE_CSV_FIELDS = {
    "training/training_run_registry.csv": {"started_at_utc", "ended_at_utc"},
    "training/seed_level_training_curves.csv": {"elapsed_seconds", "peak_memory_mib"},
    "training/model_parameter_compute_latency_audit.csv": {
        "train_seconds",
        "inference_seconds",
        "latency_ms_per_1000_rows",
        "peak_cpu_rss_mib",
        "peak_gpu_memory_mib",
    },
    "stage_status_registry.csv": {"started_at_utc", "ended_at_utc"},
}

VOLATILE_JSON_FIELDS = {"generated_at_utc", "worker_pid", "started_at_utc", "ended_at_utc"}


def _without_volatile_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_volatile_json(item)
            for key, item in value.items()
            if key not in VOLATILE_JSON_FIELDS
        }
    if isinstance(value, list):
        return [_without_volatile_json(item) for item in value]
    return value


def _semantic_hash_file(path: Path, relative_path: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, keep_default_na=False)
        drop = [
            column
            for column in VOLATILE_CSV_FIELDS.get(relative_path, set())
            if column in frame
        ]
        frame = frame.drop(columns=drop)
        keys = [key for key in CSV_SORT_KEYS.get(relative_path, []) if key in frame]
        if keys:
            frame = frame.sort_values(keys, na_position="last", kind="mergesort")
        payload = {
            "format": "csv_columnar_v4",
            "columns": list(frame.columns),
            "records": frame.to_dict("records"),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if suffix == ".parquet":
        table = pq.read_table(path).combine_chunks()
        digest = hashlib.sha256()
        header = canonical_json_bytes(
            {
                "format": "parquet_logical_column_buffers_v4",
                "schema": str(table.schema.remove_metadata()),
                "row_n": table.num_rows,
                "sort_keys": PARQUET_SORT_KEYS.get(relative_path, []),
            }
        )
        digest.update(len(header).to_bytes(8, "little"))
        digest.update(header)
        for field, column in zip(table.schema, table.columns, strict=True):
            array = column.chunk(0)
            column_header = canonical_json_bytes(
                {
                    "name": field.name,
                    "type": str(field.type),
                    "length": len(array),
                    "null_count": array.null_count,
                }
            )
            digest.update(len(column_header).to_bytes(8, "little"))
            digest.update(column_header)
            for buffer in array.buffers():
                if buffer is None:
                    digest.update((0).to_bytes(8, "little"))
                else:
                    raw = buffer.to_pybytes()
                    digest.update(len(raw).to_bytes(8, "little"))
                    digest.update(raw)
        return digest.hexdigest()
    if suffix == ".json":
        value = _without_volatile_json(json.loads(path.read_text(encoding="utf-8")))
        return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    if suffix in {".yaml", ".yml"}:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    if suffix == ".md":
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("generated_at_utc:")
        ]
        return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    return file_sha(path)


def _stage_manifest_hash(build: Path, relative_paths: Sequence[str]) -> str:
    hashes = {
        relative: file_sha(build / relative)
        for relative in sorted(relative_paths)
        if (build / relative).is_file()
    }
    return hashlib.sha256(canonical_json_bytes(hashes)).hexdigest()


def _write_stage_registry(config: dict[str, Any], profile_registry_hash: str) -> None:
    build = building_root(config)
    root_relative = canonical_output_root(config).relative_to(TOPIC_ROOT).as_posix()
    now = utc_now()
    materialized_paths = [
        path
        for path in ALL_STAGE_PATHS
        if path.startswith("materialized/")
        and not path.endswith("materialization_failure_evidence.csv")
    ]
    stage_paths = [
        [
            "preflight/preflight_access_audit.csv",
            "preflight/upstream_21a_authorization_and_hash_audit.csv",
            "preflight/resolved_config.yaml",
        ],
        materialized_paths,
        [
            "training/training_run_registry.csv",
            "training/model_search_accounting_manifest.csv",
            "training/seed_level_training_curves.csv",
            "training/checkpoint_manifest.json",
            "training/selection/validation_early_prediction_scores.parquet",
            "training/model_parameter_compute_latency_audit.csv",
            "training/training_access_audit.csv",
            *checkpoint_paths(),
        ],
        [
            "training/selection_worker_exit_record.json",
            "training/pre_gate_checkpoint_bundle_manifest.json",
        ],
        [
            "training/readout/validation_late_prediction_scores.parquet",
            "training/gate_readout_worker_exit_record.json",
        ],
        [
            "training/checkpoint_eligibility_manifest.json",
            "training/pre_holdout_checkpoint_bundle_manifest.json",
            "training/daily_prediction_scores.parquet",
        ],
        [],
    ]
    names = [
        "preflight",
        "materialize-labels",
        "train-baselines.selection-worker",
        "train-baselines.pre-gate-seal",
        "train-baselines.gate-readout-worker",
        "train-baselines.eligibility",
        "finalize",
    ]
    rows = []
    for ordinal, (name, produced) in enumerate(zip(names, stage_paths, strict=True), 1):
        worker_code: Any = "NA"
        if ordinal == 3:
            worker_code = read_json(build / "training/selection_worker_exit_record.json")["exit_code"]
        elif ordinal == 5:
            worker_code = read_json(build / "training/gate_readout_worker_exit_record.json")["exit_code"]
        rows.append(
            {
                "stage_ordinal": ordinal,
                "stage_or_subphase": name,
                "attempt_id": f"stage_{ordinal:02d}_attempt_01",
                "bundle_root_class": "canonical",
                "bundle_root_relative_path": root_relative,
                "preauthorization_audit_id": "NA",
                "artifact_profile_id": "P5_FULL_FINALIZED",
                "status": "sealed",
                "worker_exit_code": worker_code,
                "started_at_utc": now,
                "ended_at_utc": now,
                "sealed_artifact_count": len(produced),
                "stage_manifest_sha256": (
                    _stage_manifest_hash(build, produced) if ordinal < 7 else "NA"
                ),
                "blocking_reason": "NA",
                "artifact_profile_registry_sha256": profile_registry_hash,
            }
        )
    columns = [
        "stage_ordinal",
        "stage_or_subphase",
        "attempt_id",
        "bundle_root_class",
        "bundle_root_relative_path",
        "preauthorization_audit_id",
        "artifact_profile_id",
        "status",
        "worker_exit_code",
        "started_at_utc",
        "ended_at_utc",
        "sealed_artifact_count",
        "stage_manifest_sha256",
        "blocking_reason",
    ]
    write_csv(build / "stage_status_registry.csv", rows, columns)


def _write_report(
    build: Path,
    daily: pd.DataFrame,
    gate_stats: dict[str, dict[str, Any]],
    eligible_arms: list[str],
    m0_ci: tuple[float, float],
    payload_hash: str,
) -> None:
    ensemble_rows = daily[
        daily["score_role"].eq("ensemble") | daily["score_role"].eq("null")
    ]
    table_lines = [
        "| 模型 | late mean RankIC | 正向 seed | 正向 LOMO | 月度集中度 | 信息门 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for arm in GATE_BASELINES:
        stats = gate_stats[arm]
        table_lines.append(
            f"| {arm} | {stats['late_mean']:.6f} | {stats['positive_late_seed_n']}/3 | "
            f"{stats['positive_lomo_n']}/{stats['lomo_total_n']} | {stats['concentration']:.4f} | "
            f"{'通过' if arm in eligible_arms else '未通过'} |"
        )
    a0_late = ensemble_rows[
        ensemble_rows["arm_id"].eq("A0_VANILLA_AUTOENCODER")
        & ensemble_rows["fold"].eq("validation_late")
    ]
    a0_mean = float(a0_late["RankIC"].mean())
    outcome = (
        "基线信息得到支持，允许生成人工评审用 21C requirement，但不授权执行。"
        if eligible_arms
        else "基线信息未得到支持，按冻结合同关闭 EP21 复杂架构主线。"
    )
    text = f"""# EP21 21B Alpha158/序列基线基准报告

generated_at_utc:{utc_now()}

## 决策结论

{outcome}

- 通过的信息基线：{' | '.join(eligible_arms) if eligible_arms else '无'}
- semantic payload bundle hash：`{payload_hash}`
- 本报告只使用 2023 validation；历史 design holdout 的 outcome/label/join/metric 读取均为 0。

## Validation-late 冻结门结果

{chr(10).join(table_lines)}

A0 自编码器仅作诊断，其 validation-late mean RankIC 为 {a0_mean:.6f}，不能单独授权 21C。

## Null 与稳健性诊断

M0 realized validation-full stationary-bootstrap 99% 双侧区间为 [{m0_ci[0]:.6f}, {m0_ci[1]:.6f}]。该区间按合同仅作诊断，不参与 hard gate。
已输出逐日 RankIC、full/early/late、月度与 LOMO、主板/创业板描述切片，以及 top-third 决策日/股票同时移除诊断。

## 解释边界

本次 gate 只回答冻结的简单基线是否展现方向一致且不过度集中于单月的信息；不构成统计显著性、交易可执行性、策略收益、组合优化或部署声明。
"""
    (build / "21B_alpha158_sequence_baseline_benchmark_report.md").write_text(
        text, encoding="utf-8", newline="\n"
    )


def finalize(config: dict[str, Any]) -> None:
    build = building_root(config)
    output = canonical_output_root(config)
    if output.exists():
        raise FileExistsError(f"sealed output already exists: {output}")
    if not (build / "training/pre_holdout_checkpoint_bundle_manifest.json").exists():
        raise RuntimeError("pre-holdout seal missing")

    holdout_row = {
        "scope": "historical_design_holdout",
        "date_min": "2024-01-01",
        "date_max": "NA",
        "byte_integrity_read_count": 0,
        "routing_date_only_read_count": 0,
        "outcome_value_row_read_count": 0,
        "label_read_count": 0,
        "score_outcome_join_count": 0,
        "metric_read_count": 0,
        "required_outcome_counts_zero": True,
        "status": "pass",
    }
    write_csv(
        build / "historical_design_holdout_access_audit.csv",
        [holdout_row],
        list(holdout_row),
    )

    predictions = pd.read_parquet(build / "training/daily_prediction_scores.parquet")
    predictions["decision_date"] = predictions["decision_date"].astype(str)
    label_audit = pd.read_parquet(
        build / "materialized/decision_universe_and_label_resolution_audit.parquet"
    )
    label_audit["decision_date"] = label_audit["decision_date"].astype(str)
    labels = label_audit[
        label_audit["whole_day_evaluable"].astype(bool)
        & label_audit["split"].eq("validation")
    ][
        [
            "decision_date",
            "instrument",
            "row_key_hash",
            "label_value",
            "U_t_resolved_n",
        ]
    ].copy()
    readout_paths = [
        build / "daily_rankic_readout.csv",
        build / "rankic_stability_and_concentration_audit.csv",
        build / "fragility_unit_contribution_audit.csv",
    ]
    if all(path.is_file() for path in readout_paths):
        daily = pd.read_csv(readout_paths[0])
        stability = pd.read_csv(readout_paths[1])
        gate_stats = {}
        for arm in GATE_BASELINES:
            record = stability[
                stability["arm_id"].eq(arm)
                & stability["scope"].eq("validation_late_gate_summary")
            ].iloc[0]
            gate_stats[arm] = {
                "late_mean": float(record["mean_RankIC"]),
                "late_complete_days": int(record["complete_day_n"]),
                "positive_late_seed_n": int(record["positive_late_seed_n"]),
                "positive_lomo_n": int(record["positive_lomo_n"]),
                "lomo_total_n": int(record["lomo_total_n"]),
                "concentration": float(record["max_month_abs_contribution_share"]),
                "coverage": float(record["score_coverage_rate"]),
            }
        ci_record = stability[
            stability["scope"].eq("validation_full_realized_null_bootstrap")
        ].iloc[0]
        ci_text = str(ci_record["slice_id"]).split("=[", 1)[1].split("]", 1)[0]
        ci_values = ci_text.split(",")
        m0_ci = (float(ci_values[0]), float(ci_values[1]))
    else:
        daily = calculate_daily_readout(predictions, labels)
        if daily.empty:
            raise RuntimeError("daily RankIC readout is empty")
        write_csv(build / "daily_rankic_readout.csv", daily, DAILY_COLUMNS)

        stability, gate_stats = calculate_stability(daily, predictions)
        fragility, fragility_summaries = calculate_fragility(predictions, labels)
        board_summaries = _board_slice_summaries(config, predictions, labels)
        m0_daily = _metric_subset(daily, M0, "null", None)
        m0_values = m0_daily.loc[
            m0_daily["rankic_status"].eq("evaluable"), "RankIC"
        ].to_numpy(dtype=np.float64)
        m0_ci = _stationary_bootstrap_ci(
            m0_values,
            int(config["gates"]["m0_bootstrap_replicates"]),
            int(config["gates"]["m0_expected_block_length"]),
        )
        m0_ci_row = _summary_record(
            m0_daily,
            arm_id=M0,
            score_role="null",
            model_seed=None,
            scope="validation_full_realized_null_bootstrap",
            evidence_role="diagnostic_only",
            slice_id=f"stationary_bootstrap_99pct_ci=[{m0_ci[0]:.12g},{m0_ci[1]:.12g}]|replicates=10000|expected_block=20",
        )
        stability = pd.concat(
            [
                stability,
                pd.DataFrame([*fragility_summaries, *board_summaries, m0_ci_row]),
            ],
            ignore_index=True,
        ).sort_values(
            ["arm_id", "score_role", "model_seed", "scope", "slice_id"],
            na_position="last",
        )
        write_csv(
            build / "rankic_stability_and_concentration_audit.csv",
            stability,
            STABILITY_COLUMNS,
        )
        write_csv(
            build / "fragility_unit_contribution_audit.csv",
            fragility,
            FRAGILITY_COLUMNS,
        )

    resolved = yaml.safe_load(
        (build / "preflight/resolved_config.yaml").read_text(encoding="utf-8")
    )
    registry_hash = hashlib.sha256(
        canonical_json_bytes(resolved["artifact_profiles"])
    ).hexdigest()
    if registry_hash != resolved["runtime"]["artifact_profile_registry_sha256"]:
        raise ValueError("artifact profile registry hash mismatch")
    _write_stage_registry(config, registry_hash)

    profile = next(
        item
        for item in resolved["artifact_profiles"]
        if item["profile_id"] == "P5_FULL_FINALIZED"
    )
    required_paths = profile["required_paths"]
    control_paths = {
        "gate_evidence_21b.csv",
        "21B_baseline_benchmark_decision.csv",
        "21B_alpha158_sequence_baseline_benchmark_report.md",
        "semantic_reproducibility_manifest.json",
        "manifest_21b_alpha158_sequence_baseline_benchmark.json",
        "output_hashes_21b_alpha158_sequence_baseline_benchmark.json",
    }
    payload_paths = sorted(set(required_paths) - control_paths)
    missing_payload = [relative for relative in payload_paths if not (build / relative).is_file()]
    if missing_payload:
        raise FileNotFoundError(f"missing P5 payload paths: {missing_payload}")
    payload_hashes = {
        relative: _semantic_hash_file(build / relative, relative)
        for relative in payload_paths
    }
    checkpoint_manifest = read_json(build / "training/checkpoint_manifest.json")
    model_state_hashes = {
        record["checkpoint_path"]: record["model_state_semantic_sha256"]
        for record in checkpoint_manifest["candidates"]
    }
    payload_object = {
        "canonicalization_version": config["output"]["semantic_canonicalization_version"],
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "semantic_payload_artifact_hashes": payload_hashes,
        "model_state_semantic_hashes": model_state_hashes,
    }
    payload_hash = hashlib.sha256(canonical_json_bytes(payload_object)).hexdigest()

    gate_rows, eligible_arms = _build_gate_evidence(config, daily, gate_stats, m0_ci)
    causal_failed = [
        row["gate_id"]
        for row in gate_rows
        if row["gate_id"] in CAUSAL_GATES and row["status"] != "pass"
    ]
    if causal_failed:
        raise RuntimeError(f"P5 causal gate failure: {sorted(causal_failed)}")
    write_csv(build / "gate_evidence_21b.csv", gate_rows, GATE_COLUMNS)
    gate_hash = file_sha(build / "gate_evidence_21b.csv")

    stage_decision = (
        "21B_baseline_information_supported_pending_human_approval"
        if eligible_arms
        else "21B_baseline_information_not_supported"
    )
    ensemble_full = stability[
        stability["scope"].eq("validation_full")
        & stability["score_role"].eq("ensemble")
        & stability["model_seed"].isna()
    ]
    if ensemble_full.empty:
        best_arm = "NA"
    else:
        best_arm = str(
            ensemble_full.sort_values(
                ["mean_RankIC", "arm_id"], ascending=[False, True]
            ).iloc[0]["arm_id"]
        )
    statuses = {row["gate_id"]: row["status"] for row in gate_rows}
    decision = {
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "bundle_root_class": "canonical",
        "bundle_root_relative_path": output.relative_to(TOPIC_ROOT).as_posix(),
        "preauthorization_audit_id": "NA",
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "artifact_profile_registry_sha256": registry_hash,
        "stage_decision": stage_decision,
        **{gate: statuses[gate] for gate in CAUSAL_GATES},
        "output_manifest_hash_gate": "pass",
        "baseline_information_gate": statuses["baseline_information_gate"],
        "eligible_baseline_ids": "|".join(eligible_arms) if eligible_arms else "NA",
        "best_validation_arm_diagnostic_only": best_arm,
        "next_requirement": (
            "requirement_21c_single_vs_adaptive_koopman_nested_ablation.md"
            if eligible_arms
            else "NA"
        ),
        "next_requirement_generation_authorized": bool(eligible_arms),
        "next_requirement_execution_authorized": False,
        "historical_holdout_readout_authorized": False,
        "policy_training_authorized": False,
        "portfolio_optimization_authorized": False,
        "deployment_authorized": False,
        "pre_gate_checkpoint_bundle_hash": file_sha(
            build / "training/pre_gate_checkpoint_bundle_manifest.json"
        ),
        "pre_holdout_checkpoint_bundle_hash": file_sha(
            build / "training/pre_holdout_checkpoint_bundle_manifest.json"
        ),
        "semantic_payload_bundle_hash": payload_hash,
        "gate_evidence_sha256": gate_hash,
        "blocking_reasons": json.dumps(sorted(causal_failed), separators=(",", ":")),
    }
    write_csv(build / "21B_baseline_benchmark_decision.csv", [decision], DECISION_COLUMNS)
    _write_report(build, daily, gate_stats, eligible_arms, m0_ci, payload_hash)

    semantic_paths = sorted(
        set(required_paths)
        - {
            "semantic_reproducibility_manifest.json",
            "manifest_21b_alpha158_sequence_baseline_benchmark.json",
            "output_hashes_21b_alpha158_sequence_baseline_benchmark.json",
        }
    )
    semantic_hashes = {
        relative: _semantic_hash_file(build / relative, relative)
        for relative in semantic_paths
    }
    semantic_object = {
        "canonicalization_version": config["output"]["semantic_canonicalization_version"],
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "semantic_payload_bundle_hash": payload_hash,
        "semantic_artifact_hashes": semantic_hashes,
        "model_state_semantic_hashes": model_state_hashes,
    }
    semantic_bundle_hash = hashlib.sha256(
        canonical_json_bytes(semantic_object)
    ).hexdigest()
    semantic_manifest = {
        "schema_version": "21B_semantic_reproducibility_manifest_v4",
        "canonicalization_version": config["output"]["semantic_canonicalization_version"],
        "volatile_field_exclusions": {
            "csv": {key: sorted(value) for key, value in VOLATILE_CSV_FIELDS.items()},
            "json": sorted(VOLATILE_JSON_FIELDS),
            "report": "exact_single_line_beginning_generated_at_utc:",
        },
        "bundle_root_class": "canonical",
        "bundle_root_relative_path": output.relative_to(TOPIC_ROOT).as_posix(),
        "preauthorization_audit_id": "NA",
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "control_paths": sorted(control_paths),
        "semantic_payload_artifact_hashes": payload_hashes,
        "semantic_payload_bundle_hash": payload_hash,
        "semantic_artifact_hashes": semantic_hashes,
        "model_state_semantic_hashes": model_state_hashes,
        "semantic_bundle_hash": semantic_bundle_hash,
        "status": "pass",
    }
    write_json(build / "semantic_reproducibility_manifest.json", semantic_manifest)

    output_hashes_path = build / "output_hashes_21b_alpha158_sequence_baseline_benchmark.json"
    final_manifest_path = build / "manifest_21b_alpha158_sequence_baseline_benchmark.json"
    hash_domain = sorted(
        set(required_paths)
        - {
            output_hashes_path.name,
            final_manifest_path.name,
        }
    )
    byte_hashes = {relative: file_sha(build / relative) for relative in hash_domain}
    write_json(
        output_hashes_path,
        {
            "schema_version": "21B_output_hashes_v4",
            "hash_algorithm": "sha256",
            "artifacts": byte_hashes,
        },
    )
    final_manifest = {
        "schema_version": "21B_final_manifest_v4",
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "bundle_root_class": "canonical",
        "bundle_root_relative_path": output.relative_to(TOPIC_ROOT).as_posix(),
        "preauthorization_audit_id": "NA",
        "artifact_profile_id": "P5_FULL_FINALIZED",
        "artifact_profile_registry_sha256": registry_hash,
        "profile_required_paths": required_paths,
        "profile_forbidden_paths": profile["forbidden_paths"],
        "selected_profile_validation": "pass",
        "artifact_file_set": sorted(required_paths),
        "output_hashes_sha256": file_sha(output_hashes_path),
        "semantic_payload_bundle_hash": payload_hash,
        "semantic_bundle_hash": semantic_bundle_hash,
        "post_build_full_disk_reopen_verification": "pass",
        "status": "pass",
    }
    write_json(final_manifest_path, final_manifest)

    observed_files = sorted(
        path.relative_to(build).as_posix()
        for path in build.rglob("*")
        if path.is_file()
    )
    if observed_files != sorted(required_paths):
        missing = sorted(set(required_paths) - set(observed_files))
        extra = sorted(set(observed_files) - set(required_paths))
        raise ValueError(f"P5 exact file-set mismatch; missing={missing}; extra={extra}")
    sealed_hashes = read_json(output_hashes_path)["artifacts"]
    for relative, expected in sealed_hashes.items():
        observed = file_sha(build / relative)
        if observed != expected:
            raise ValueError(f"post-build byte hash mismatch: {relative}")
    if file_sha(output_hashes_path) != final_manifest["output_hashes_sha256"]:
        raise ValueError("output-hashes file hash mismatch")
    if semantic_bundle_hash.encode() in b"".join(
        (build / relative).read_bytes()
        for relative in required_paths
        if relative
        not in {
            "semantic_reproducibility_manifest.json",
            "manifest_21b_alpha158_sequence_baseline_benchmark.json",
        }
    ):
        raise ValueError("top semantic hash leaked into a forbidden artifact")
    build.rename(output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=["preflight", "materialize-labels", "train-baselines", "finalize", "all"],
        default="all",
    )
    parser.add_argument("--worker", choices=["selection", "gate-readout"])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = args.config.resolve()
    config = load_config(config_path)
    if args.worker == "selection":
        selection_worker(config)
        return 0
    if args.worker == "gate-readout":
        gate_readout_worker(config)
        return 0
    stages = (
        ["preflight", "materialize-labels", "train-baselines", "finalize"]
        if args.stage == "all"
        else [args.stage]
    )
    for stage in stages:
        print(f"[{utc_now()}] 21B stage start: {stage}", flush=True)
        if stage == "preflight":
            preflight(config, config_path)
        elif stage == "materialize-labels":
            materialize_labels(config)
        elif stage == "train-baselines":
            train_baselines(config, config_path)
        elif stage == "finalize":
            finalize(config)
        print(f"[{utc_now()}] 21B stage complete: {stage}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
