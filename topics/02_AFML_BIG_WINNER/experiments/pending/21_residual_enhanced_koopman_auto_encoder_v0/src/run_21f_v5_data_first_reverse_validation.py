"""Run the resumable 21F v5 data-first and targeted reverse-validation pipeline."""

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
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml


WORKSPACE = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = EXPERIMENT_ROOT / "configs/config_21f_v5_data_first_reverse_validation.yaml"
RUN_ID = "21F_reaka_data_first_reverse_validation"
REQUIREMENT_VERSION = "21F_DATA_FIRST_REVERSE_VALIDATION_v5"
MODEL_SEEDS = (20260713, 20260714, 20260715)
ARM_IDS = (
    "T0_RAW_COUPLED_LINEAR", "T1_CSZ_COUPLED_LINEAR",
    "T2_CSZ_STOPGRAD_LINEAR", "T3_CSZ_TWO_STAGE_LINEAR",
    "T4_CSZ_STOPGRAD_POINTWISE_MLP",
)
AUTH_KEYS = {
    "run_id", "requirement_version", "approved_requirement_sha256",
    "approved_config_sha256", "approved_runner_sha256", "approved_test_sha256",
    "approved_base_config_sha256", "approved_base_runner_sha256",
    "approved_source_inner_manifest_sha256", "approved_source_inner_complete_sha256",
    "approved_dependency_lock_sha256", "approved_device_fingerprint_sha256",
    "approved_by", "approved_at_utc", "allowed_runtime_field_differences",
}


class ContractError(RuntimeError):
    pass


def _import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _import_module(
    EXPERIMENT_ROOT / "src/run_21f_reaka_semantic_repair_and_stability_validation.py",
    "run_21f_v4_base_for_v5",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_path(value: str | Path, *, must_exist: bool = False) -> Path:
    path = Path(value)
    resolved = (path if path.is_absolute() else WORKSPACE / path).resolve()
    if not resolved.is_relative_to(WORKSPACE.resolve()):
        raise ContractError(f"path escapes workspace: {value}")
    if must_exist and not resolved.exists():
        raise ContractError(f"missing path: {value}")
    return resolved


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(canonical_json_bytes(dict(payload)) + b"\n")
    os.replace(temporary, path)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    pd.DataFrame(list(rows), columns=list(columns)).to_csv(
        temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def write_npy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, np.asarray(values, dtype=np.float32), allow_pickle=False)
    os.replace(temporary, path)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("config must be a mapping")
    if payload.get("schema_version") != "21F_DATA_FIRST_CONFIG_V1":
        raise ContractError("config schema drift")
    if payload["identity"]["run_id"] != RUN_ID:
        raise ContractError("run identity drift")
    if payload["identity"]["requirement_version"] != REQUIREMENT_VERSION:
        raise ContractError("requirement identity drift")
    if payload["data_first"]["estimator_id"] != "Q1_SCORE_MEAN64":
        raise ContractError("data-first estimator drift")
    if payload["resources"]["maximum_concurrent_gpu_jobs"] != 2:
        raise ContractError("v5 requires two GPU lanes")
    if payload["execution"]["seal_authorized"] is not False:
        raise ContractError("data-first sealing must remain forbidden")
    return payload


def build_root(config: Mapping[str, Any]) -> Path:
    return Path(str(workspace_path(config["paths"]["output_root"])) + ".building")


def source_root(config: Mapping[str, Any]) -> Path:
    return workspace_path(config["paths"]["source_e2_root"], must_exist=True)


def base_config(config: Mapping[str, Any]) -> dict[str, Any]:
    path = workspace_path(config["paths"]["base_config"], must_exist=True)
    if file_sha(path) != config["pins"]["base_config_sha256"]:
        raise ContractError("base config hash drift")
    runner = workspace_path(config["paths"]["base_runner"], must_exist=True)
    if file_sha(runner) != config["pins"]["base_runner_sha256"]:
        raise ContractError("base runner hash drift")
    return BASE.load_config(path)


def device_fingerprint() -> str:
    return BASE.current_device_fingerprint()


def authorization_bindings(config: Mapping[str, Any]) -> dict[str, str]:
    return {
        "run_id": RUN_ID,
        "requirement_version": REQUIREMENT_VERSION,
        "approved_requirement_sha256": file_sha(workspace_path(config["paths"]["requirement"], must_exist=True)),
        "approved_config_sha256": file_sha(workspace_path(config["paths"]["config"], must_exist=True)),
        "approved_runner_sha256": file_sha(workspace_path(config["paths"]["runner"], must_exist=True)),
        "approved_test_sha256": file_sha(workspace_path(config["paths"]["test"], must_exist=True)),
        "approved_base_config_sha256": config["pins"]["base_config_sha256"],
        "approved_base_runner_sha256": config["pins"]["base_runner_sha256"],
        "approved_source_inner_manifest_sha256": config["pins"]["source_inner_manifest_sha256"],
        "approved_source_inner_complete_sha256": config["pins"]["source_inner_complete_sha256"],
        "approved_dependency_lock_sha256": file_sha(workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "approved_device_fingerprint_sha256": device_fingerprint(),
    }


def validate_authorization(config: Mapping[str, Any]) -> tuple[bool, list[str]]:
    path = workspace_path(config["paths"]["authorization"])
    if not path.exists():
        return False, ["authorization_missing"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    if set(payload) != AUTH_KEYS:
        errors.append("authorization_exact_keys_mismatch")
    for key, expected in authorization_bindings(config).items():
        if payload.get(key) != expected:
            errors.append(f"{key}_mismatch")
    if payload.get("allowed_runtime_field_differences") != []:
        errors.append("runtime_differences_not_empty")
    if not str(payload.get("approved_by", "")).strip():
        errors.append("human_approval_missing")
    if not str(payload.get("approved_at_utc", "")).strip():
        errors.append("approval_time_missing")
    return not errors, errors


def validate_source_e2(config: Mapping[str, Any]) -> dict[str, Any]:
    root = source_root(config)
    manifest_path = root / "training/inner_checkpoint_manifest.json"
    complete_path = root / ".state/inner_training_complete.json"
    if file_sha(manifest_path) != config["pins"]["source_inner_manifest_sha256"]:
        raise ContractError("source E2 manifest hash drift")
    if file_sha(complete_path) != config["pins"]["source_inner_complete_sha256"]:
        raise ContractError("source E2 completion hash drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["checkpoint_entries"]
    if manifest["entry_n"] != 30 or [int(item["job_order"]) for item in entries] != list(range(1, 31)):
        raise ContractError("source checkpoint cardinality/order drift")
    for entry in entries:
        path = root / entry["path"]
        if (not path.exists() or path.stat().st_size != int(entry["size_bytes"]) or
                file_sha(path) != entry["sha256"]):
            raise ContractError(f"source checkpoint drift: {entry['path']}")
    if len(pd.read_csv(root / "training/inner_training_run_registry.csv")) != 36:
        raise ContractError("source inner registry drift")
    if len(pd.read_parquet(root / "gradient_calibration_audit.parquet")) != 210:
        raise ContractError("source calibration drift")
    if len(pd.read_parquet(root / "gradient_graph_and_collapse_audit.parquet")) != 30:
        raise ContractError("source collapse audit drift")
    return {"entry_n": 30, "manifest_sha256": file_sha(manifest_path),
        "entries_semantic_sha256": manifest["entries_semantic_sha256"]}


def hardlink_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def initialize_build(config: Mapping[str, Any]) -> Path:
    root = build_root(config)
    if shutil.disk_usage(root.parent).free < int(config["resources"]["minimum_free_disk_bytes"]):
        raise ContractError("insufficient disk for v5")
    root.mkdir(parents=True, exist_ok=True)
    (root / ".state").mkdir(exist_ok=True)
    validation = validate_source_e2(config)
    source = source_root(config)
    for relative in (
        "preflight/pre_2023_row_index.parquet", "preflight/design_2023_row_index.parquet",
        "training/inner_training_run_registry.csv", "training/inner_epoch_selection_registry.parquet",
        "training/inner_checkpoint_manifest.json", "gradient_calibration_audit.parquet",
        "gradient_graph_and_collapse_audit.parquet", "return_transform_audit.parquet",
    ):
        hardlink_or_copy(source / relative, root / "source_e2" / relative)
    write_json(root / "source_e2/resume_validation.json", {
        "schema_version": "21F_V5_E2_RESUME_VALIDATION_V1", **validation,
        "source_root": config["paths"]["source_e2_root"], "status": "pass",
        "validated_at_utc": utc_now()})
    status = root / "stage_status.json"
    if not status.exists():
        write_json(status, {"schema_version": "21F_V5_STAGE_STATUS_V1",
            "run_id": RUN_ID, "stage": "initialized", "status": "running",
            "seal_authorized": False, "updated_at_utc": utc_now()})
    return root


def prepare_lane_root(config: Mapping[str, Any], kind: str, lane_id: int,
                      *, design: bool = False) -> Path:
    root = build_root(config) / f".state/{kind}/lane_{lane_id}"
    root.mkdir(parents=True, exist_ok=True)
    index_names = ["pre_2023_row_index.parquet"]
    if design:
        index_names.append("design_2023_row_index.parquet")
    for index_name in index_names:
        source = source_root(config) / "preflight" / index_name
        hardlink_or_copy(source, root / "preflight" / index_name)
    audit = root / "preflight/value_access_audit.csv"
    if not audit.exists():
        write_csv(audit, [], BASE.TABULAR_SCHEMAS["value_access"])
    return root


def runtime_base_config(config: Mapping[str, Any], runtime_root: Path) -> dict[str, Any]:
    selected = base_config(config)
    # Reuse the v4 loaders inside the independently named v5 building root while
    # retaining their path-containment guard for every worker lane.
    selected["paths"]["canonical_output_root"] = config["paths"]["output_root"]
    selected["_runtime_build_root"] = str(runtime_root)
    return selected


def checkpoint_source_path(config: Mapping[str, Any], fold_id: str, arm_id: str,
                           seed: int) -> Path:
    return source_root(config) / f"training/inner_checkpoints/{fold_id}/{arm_id}/seed_{seed}/state_dict.pt"


def score_record_valid(score_path: Path, record_path: Path, expected_rows: int,
                       checkpoint_sha: str, estimator_id: str) -> bool:
    if not score_path.exists() or not record_path.exists():
        return False
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("checkpoint_sha256") != checkpoint_sha or record.get("estimator_id") != estimator_id:
        return False
    values = np.load(score_path, allow_pickle=False)
    return (values.shape == (expected_rows,) and np.isfinite(values).all() and
            file_sha(score_path) == record.get("score_file_sha256"))


def arm_readout_lane(config: Mapping[str, Any], lane_id: int) -> None:
    if lane_id not in (0, 1):
        raise ContractError("lane id drift")
    root = prepare_lane_root(config, "arm_readout_lanes", lane_id)
    base = runtime_base_config(config, root)
    BASE.configure_determinism()
    if not torch.cuda.is_available():
        raise ContractError("CUDA required")
    device = torch.device("cuda")
    feature_cache = BASE.load_feature_cache(base)
    fold_contract = base["inner_folds"][lane_id]
    fold = BASE.load_fold_slice(base, fold_contract["select_id"],
        worker_role="SELECTION_COORDINATOR", feature_cache=feature_cache)
    estimator_id = config["data_first"]["estimator_id"]
    prediction_files = []
    for arm_id in ARM_IDS:
        seed_scores = {}
        for seed in MODEL_SEEDS:
            checkpoint = checkpoint_source_path(config, fold_contract["fit_id"], arm_id, seed)
            checkpoint_sha = file_sha(checkpoint)
            score_path = root / f"scores/{arm_id}/seed_{seed}.npy"
            record_path = root / f"scores/{arm_id}/seed_{seed}.json"
            if not score_record_valid(score_path, record_path, len(fold.frame),
                                      checkpoint_sha, estimator_id):
                model = BASE.build_model(arm_id, seed)
                state = torch.load(checkpoint, map_location="cpu", weights_only=True)
                model.load_state_dict(state, strict=True)
                model.to(device)
                score = BASE.score_fold(model, estimator_id, fold, arm_id, seed,
                    batch_size=int(config["data_first"]["inference_batch_size"]), device=device)
                write_npy(score_path, score)
                write_json(record_path, {"schema_version": "21F_V5_SCORE_RECORD_V1",
                    "fold_id": fold.split_id, "arm_id": arm_id, "model_seed": seed,
                    "estimator_id": estimator_id, "checkpoint_sha256": checkpoint_sha,
                    "score_file_sha256": file_sha(score_path), "row_n": len(score),
                    "finite": True, "completed_at_utc": utc_now()})
                del model, state, score
                torch.cuda.empty_cache()
            seed_scores[seed] = np.load(score_path, allow_pickle=False)
        frame = BASE.prediction_frame(fold, arm_id, estimator_id, seed_scores,
            "E3_DATA_FIRST_ARM_READOUT", "provisional_q1")
        prediction_path = root / f"predictions/{arm_id}.parquet"
        write_parquet(prediction_path, frame)
        prediction_files.append(prediction_path.relative_to(root).as_posix())
    write_json(root / ".state/lane_complete.json", {
        "schema_version": "21F_V5_ARM_LANE_COMPLETE_V1", "lane_id": lane_id,
        "fold_id": fold.split_id, "checkpoint_score_n": 15,
        "prediction_files": prediction_files, "completed_at_utc": utc_now()})


def worker_command(config: Mapping[str, Any], worker: str, lane_id: int) -> list[str]:
    return [sys.executable, str(workspace_path(config["paths"]["runner"], must_exist=True)),
        "--config", str(workspace_path(config["paths"]["config"], must_exist=True)),
        "--worker", worker, "--lane-id", str(lane_id)]


def launch_lanes(config: Mapping[str, Any], worker: str, roots: Sequence[Path]) -> None:
    processes: list[subprocess.Popen[bytes]] = []
    logs = []
    try:
        for lane_id, root in enumerate(roots):
            log = (root / "worker.log").open("ab")
            logs.append(log)
            processes.append(subprocess.Popen(worker_command(config, worker, lane_id),
                cwd=WORKSPACE, stdout=log, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + float(config["resources"]["worker_timeout_seconds"])
        while any(process.poll() is None for process in processes):
            if any(process.poll() not in (None, 0) for process in processes):
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                break
            if time.monotonic() > deadline:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                raise ContractError(f"{worker} lane timeout")
            time.sleep(float(config["resources"]["worker_poll_seconds"]))
        codes = [process.wait() for process in processes]
        if codes != [0, 0]:
            tails = []
            for lane_id, root in enumerate(roots):
                text = (root / "worker.log").read_text(encoding="utf-8", errors="replace")
                tails.append(f"lane_{lane_id}:{text[-2000:]}")
            raise ContractError(f"{worker} failed {codes}: " + " | ".join(tails))
    finally:
        for log in logs:
            log.close()


def _metric_rows(predictions: pd.DataFrame, source: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    collapse = pd.read_parquet(source / "gradient_graph_and_collapse_audit.parquet")
    rows = []
    readouts: dict[str, Any] = {}
    for arm_order, arm_id in enumerate(ARM_IDS):
        arm_values = {}
        no_collapse = not collapse.loc[collapse["arm_id"].eq(arm_id),
            "additional_collapse_flag"].astype(bool).any()
        for fold_id in ("I0_SELECT_2021", "I1_SELECT_2022"):
            group = predictions.loc[(predictions["arm_id"] == arm_id) &
                                    (predictions["fold_id"] == fold_id)]
            seed_frames = {seed: group.loc[group["model_seed"].eq(seed),
                ["decision_date", "instrument", "score", "label"]].copy()
                for seed in MODEL_SEEDS}
            positive_seed_n = sum(BASE.mean_daily_rankic(frame["score"].to_numpy(),
                frame["label"].to_numpy(), frame["decision_date"].astype(str))[0] > 0
                for frame in seed_frames.values())
            ensemble = group.loc[group["is_ensemble"]].copy()
            rankic = BASE.mean_daily_rankic(ensemble["score"].to_numpy(),
                ensemble["label"].to_numpy(), ensemble["decision_date"].astype(str))[0]
            rhos, overlaps = [], []
            for index, left_seed in enumerate(MODEL_SEEDS):
                for right_seed in MODEL_SEEDS[index + 1:]:
                    rhos.append(BASE.daily_score_spearman(seed_frames[left_seed], seed_frames[right_seed]))
                    overlaps.append(BASE.daily_top30_overlap(seed_frames[left_seed], seed_frames[right_seed]))
            rho, overlap = float(np.mean(rhos)), float(np.mean(overlaps))
            turnover = BASE.adjacent_turnover(ensemble)
            dates = pd.to_datetime(ensemble["decision_date"])
            quarters = dates.dt.to_period("Q").astype(str)
            lomo_positive_n = 0
            for quarter in sorted(quarters.unique()):
                retained = ensemble.loc[quarters.ne(quarter)]
                lomo_positive_n += BASE.mean_daily_rankic(retained["score"].to_numpy(),
                    retained["label"].to_numpy(), retained["decision_date"].astype(str))[0] > 0
            eligible = (rankic > 0 and positive_seed_n >= 2 and rho >= 0.25 and
                overlap >= 6 and turnover <= 0.80 and lomo_positive_n >= 3 and no_collapse)
            row = {"arm_order": arm_order, "arm_id": arm_id, "fold_id": fold_id,
                "estimator_id": "Q1_SCORE_MEAN64", "ensemble_rankic": rankic,
                "positive_seed_n": int(positive_seed_n), "cross_seed_spearman": rho,
                "cross_seed_top30_overlap": overlap, "adjacent_turnover": turnover,
                "lomo_positive_n": int(lomo_positive_n), "no_collapse": no_collapse,
                "basic_eligibility_pass": eligible, "q2_convergence_status": "deferred",
                "status": "provisional"}
            rows.append(row)
            arm_values[fold_id] = row
        readouts[arm_id] = arm_values
    return rows, readouts


def selection_key(readouts: Mapping[str, Any], arm_id: str) -> tuple[Any, ...]:
    values = readouts[arm_id]
    return (min(values["I0_SELECT_2021"]["ensemble_rankic"],
                values["I1_SELECT_2022"]["ensemble_rankic"]),
        min(values["I0_SELECT_2021"]["cross_seed_spearman"],
            values["I1_SELECT_2022"]["cross_seed_spearman"]),
        min(values["I0_SELECT_2021"]["cross_seed_top30_overlap"],
            values["I1_SELECT_2022"]["cross_seed_top30_overlap"]),
        -max(values["I0_SELECT_2021"]["adjacent_turnover"],
             values["I1_SELECT_2022"]["adjacent_turnover"]),
        -ARM_IDS.index(arm_id))


def run_arm_readout(config: Mapping[str, Any]) -> None:
    root = initialize_build(config)
    marker = root / ".state/arm_readout_complete.json"
    if marker.exists():
        return
    write_json(root / "stage_status.json", {"schema_version": "21F_V5_STAGE_STATUS_V1",
        "run_id": RUN_ID, "stage": "data_first_arm_readout", "status": "running",
        "seal_authorized": False, "updated_at_utc": utc_now()})
    roots = [prepare_lane_root(config, "arm_readout_lanes", lane_id) for lane_id in range(2)]
    launch_lanes(config, "arm-readout-lane", roots)
    frames = []
    for lane_root in roots:
        for arm_id in ARM_IDS:
            frames.append(pd.read_parquet(lane_root / f"predictions/{arm_id}.parquet"))
    predictions = pd.concat(frames, ignore_index=True)
    write_parquet(root / "predictions/provisional_inner_q1_scores.parquet", predictions)
    rows, readouts = _metric_rows(predictions, source_root(config))
    write_csv(root / "provisional_arm_readout.csv", rows, list(rows[0]))
    eligible = [arm for arm in ARM_IDS if all(readouts[arm][fold]["basic_eligibility_pass"]
        for fold in ("I0_SELECT_2021", "I1_SELECT_2022"))]
    pool = eligible or list(ARM_IDS)
    ordered = sorted(pool, key=lambda arm: selection_key(readouts, arm), reverse=True)
    selected = ordered[0]
    all_ordered = sorted(ARM_IDS, key=lambda arm: selection_key(readouts, arm), reverse=True)
    write_json(root / "provisional_selection.json", {
        "schema_version": "21F_V5_PROVISIONAL_SELECTION_V1",
        "estimator_id": config["data_first"]["estimator_id"],
        "selected_arm_id": selected, "runner_up_arm_id": all_ordered[1],
        "basic_eligible_arm_ids": eligible, "ordered_arm_ids": all_ordered,
        "selection_key": list(selection_key(readouts, selected)),
        "q2_convergence_status": "deferred", "research_selection_allowed": False,
        "created_at_utc": utc_now()})
    write_json(marker, {"schema_version": "21F_V5_ARM_READOUT_COMPLETE_V1",
        "prediction_row_n": len(predictions), "selected_arm_id": selected,
        "completed_at_utc": utc_now()})


def refit_contract(config: Mapping[str, Any]) -> tuple[str, dict[str, Any], dict[int, dict[str, float]]]:
    root = build_root(config)
    source = source_root(config)
    selected = json.loads((root / "provisional_selection.json").read_text())["selected_arm_id"]
    registry = pd.read_csv(source / "training/inner_training_run_registry.csv")
    rows = registry.loc[registry["arm_id"].eq(selected)]
    if selected == "T3_CSZ_TWO_STAGE_LINEAR":
        epochs = {"phase_a": BASE.lower_median(rows.loc[rows["phase_id"].eq("phase_a"), "selected_epoch"]),
            "phase_b": BASE.lower_median(rows.loc[rows["phase_id"].eq("phase_b"), "selected_epoch"])}
    else:
        epochs = {"joint": BASE.lower_median(rows["selected_epoch"])}
    calibration = pd.read_parquet(source / "gradient_calibration_audit.parquet")
    weights = {}
    for seed in MODEL_SEEDS:
        selected_rows = calibration.loc[(calibration["record_type"] == "loss_weight") &
                                        (calibration["model_seed"] == seed)]
        means = selected_rows.groupby("loss_term")["loss_weight"].mean().to_dict()
        scale = 3.0 / sum(means.values())
        weights[seed] = {key: float(value * scale) for key, value in means.items()}
    return selected, epochs, weights


def train_fixed_phase(base: Mapping[str, Any], model: torch.nn.Module, arm_id: str,
                      phase_id: str, fold: Any, seed: int, weights: Mapping[str, float],
                      epoch_n: int, device: torch.device) -> tuple[dict[str, torch.Tensor], list[dict[str, Any]]]:
    parameters = BASE._phase_parameters(model, arm_id, phase_id)
    optimizer = BASE._optimizer(model, parameters, base)
    y_source, y_teacher, forecast, _ = BASE.model_panel_for_arm(fold, arm_id)
    steps_per_epoch = math.ceil(len(fold.frame) / int(base["training"]["batch_size"]))
    planned_steps = int(base["training"]["max_epochs"]) * steps_per_epoch
    gumbel = torch.Generator(device="cpu").manual_seed(seed + 71)
    diffusion = torch.Generator(device="cpu").manual_seed(seed + 89)
    step_index, curves = 0, []
    for epoch in range(1, int(epoch_n) + 1):
        permutation = torch.randperm(len(fold.frame), generator=torch.Generator(
            device="cpu").manual_seed(seed + 37 + epoch - 1)).numpy()
        totals = {name: 0.0 for name in ("L_rec", "L_koop", "L_diff")}
        seen = 0
        model.train()
        for start in range(0, len(permutation), int(base["training"]["batch_size"])):
            indices = permutation[start:start + int(base["training"]["batch_size"])]
            tau = BASE.PINNED_21C.tau_for_step(step_index, planned_steps)
            total, losses = BASE._batch_loss(model, arm_id, phase_id, fold,
                y_source, y_teacher, forecast, indices, tau=tau,
                gumbel_generator=gumbel, diffusion_generator=diffusion,
                weights=weights, device=device)
            optimizer.zero_grad(set_to_none=True)
            total.float().backward()
            torch.nn.utils.clip_grad_norm_(parameters, max_norm=1.0, norm_type=2.0,
                error_if_nonfinite=True, foreach=False)
            optimizer.step()
            step_index += 1
            for name in totals:
                totals[name] += float(losses[name].detach().mean().cpu()) * len(indices)
            seen += len(indices)
        curves.append({"phase_id": phase_id, "epoch": epoch,
            "optimizer_step_end": step_index, "train_loss_rec": totals["L_rec"] / seen,
            "train_loss_koop": totals["L_koop"] / seen,
            "train_loss_diff": totals["L_diff"] / seen,
            "checkpoint_semantic_sha256": BASE.model_state_semantic_hash(BASE.cpu_state(model)),
            "fixed_epoch_readout_status": "deferred_not_controlling"})
    return BASE.cpu_state(model), curves


def refit_lane(config: Mapping[str, Any], lane_id: int) -> None:
    root = prepare_lane_root(config, "refit_lanes", lane_id)
    base = runtime_base_config(config, root)
    selected, epochs, weights = refit_contract(config)
    BASE.configure_determinism()
    device = torch.device("cuda")
    feature_cache = BASE.load_feature_cache(base)
    fold = BASE.load_fold_slice(base, "REFIT_2018_2022", worker_role="REFIT",
        feature_cache=feature_cache)
    seeds = tuple(config["data_first"]["refit_lane_seeds"][lane_id])
    entries = []
    for seed in seeds:
        path = root / f"checkpoints/seed_{seed}/state_dict.pt"
        record_path = root / f"checkpoints/seed_{seed}/record.json"
        if path.exists() and record_path.exists() and file_sha(path) == json.loads(
                record_path.read_text())["checkpoint_sha256"]:
            entries.append(json.loads(record_path.read_text()))
            continue
        model = BASE.build_model(selected, int(seed)).to(device)
        all_curves = []
        if selected == "T3_CSZ_TWO_STAGE_LINEAR":
            _, curves = train_fixed_phase(base, model, selected, "phase_a", fold,
                int(seed), weights[int(seed)], epochs["phase_a"], device)
            all_curves.extend(curves)
            state, curves = train_fixed_phase(base, model, selected, "phase_b", fold,
                int(seed), weights[int(seed)], epochs["phase_b"], device)
            all_curves.extend(curves)
        else:
            state, curves = train_fixed_phase(base, model, selected, "joint", fold,
                int(seed), weights[int(seed)], epochs["joint"], device)
            all_curves.extend(curves)
        BASE.save_checkpoint(path, state)
        record = {"schema_version": "21F_V5_REFIT_RECORD_V1", "arm_id": selected,
            "model_seed": int(seed), "epochs": epochs, "checkpoint_path": str(path.relative_to(root)),
            "checkpoint_sha256": file_sha(path),
            "checkpoint_semantic_sha256": BASE.model_state_semantic_hash(state),
            "curve_semantic_sha256": stable_hash(all_curves),
            "fixed_epoch_readout_status": "deferred_not_controlling",
            "completed_at_utc": utc_now()}
        write_json(record_path, record)
        write_json(root / f"curves/seed_{seed}.json", {"rows": all_curves})
        entries.append(record)
        del model, state
        torch.cuda.empty_cache()
    write_json(root / ".state/lane_complete.json", {"schema_version": "21F_V5_REFIT_LANE_COMPLETE_V1",
        "lane_id": lane_id, "seeds": list(seeds), "entries": entries,
        "completed_at_utc": utc_now()})


def run_refit(config: Mapping[str, Any]) -> None:
    root = build_root(config)
    marker = root / ".state/refit_complete.json"
    if marker.exists():
        return
    if not (root / ".state/arm_readout_complete.json").exists():
        raise ContractError("arm readout must complete before refit")
    roots = [prepare_lane_root(config, "refit_lanes", lane_id) for lane_id in range(2)]
    launch_lanes(config, "refit-lane", roots)
    entries = []
    for lane_root in roots:
        entries.extend(json.loads((lane_root / ".state/lane_complete.json").read_text())["entries"])
    entries.sort(key=lambda item: MODEL_SEEDS.index(int(item["model_seed"])))
    if [int(item["model_seed"]) for item in entries] != list(MODEL_SEEDS):
        raise ContractError("refit seed closure drift")
    for entry, lane_root in [(item, roots[0] if int(item["model_seed"]) in
            config["data_first"]["refit_lane_seeds"][0] else roots[1]) for item in entries]:
        source = lane_root / entry["checkpoint_path"]
        destination = root / f"training/provisional_refit_checkpoints/seed_{entry['model_seed']}/state_dict.pt"
        hardlink_or_copy(source, destination)
    write_json(root / "training/provisional_refit_manifest.json", {
        "schema_version": "21F_V5_REFIT_MANIFEST_V1", "entry_n": 3,
        "entries": entries, "entries_semantic_sha256": stable_hash(entries)})
    write_json(marker, {"schema_version": "21F_V5_REFIT_COMPLETE_V1", "entry_n": 3,
        "completed_at_utc": utc_now()})


def design_readout_lane(config: Mapping[str, Any], lane_id: int) -> None:
    root = prepare_lane_root(config, "design_lanes", lane_id, design=True)
    base = runtime_base_config(config, root)
    selected = json.loads((build_root(config) / "provisional_selection.json").read_text())["selected_arm_id"]
    BASE.configure_determinism()
    device = torch.device("cuda")
    feature_cache = BASE.load_feature_cache(base)
    split_id = ("DESIGN_EARLY_2023", "DESIGN_LATE_2023")[lane_id]
    fold = BASE.load_fold_slice(base, split_id, worker_role="FRESH_2023", allow_design=True,
        feature_cache=feature_cache)
    variants: dict[str, dict[int, np.ndarray]] = {
        "selected_drc": {}, "same_backbone_k0": {}, "q0_current8": {}}
    for seed in MODEL_SEEDS:
        checkpoint = build_root(config) / f"training/provisional_refit_checkpoints/seed_{seed}/state_dict.pt"
        checkpoint_sha = file_sha(checkpoint)
        model = BASE.build_model(selected, seed)
        model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
        model.to(device)
        for variant, estimator in (("selected_drc", "Q1_SCORE_MEAN64"),
                                   ("same_backbone_k0", "Q6_KOOPMAN_ONLY")):
            score_path = root / f"scores/{variant}/seed_{seed}.npy"
            record_path = root / f"scores/{variant}/seed_{seed}.json"
            if not score_record_valid(score_path, record_path, len(fold.frame), checkpoint_sha, estimator):
                score = BASE.score_fold(model, estimator, fold, selected, seed,
                    batch_size=int(config["data_first"]["inference_batch_size"]), device=device)
                write_npy(score_path, score)
                write_json(record_path, {"checkpoint_sha256": checkpoint_sha,
                    "estimator_id": estimator, "score_file_sha256": file_sha(score_path),
                    "row_n": len(score), "completed_at_utc": utc_now()})
            variants[variant][seed] = np.load(score_path, allow_pickle=False)
        q0_path = root / f"scores/q0_current8/seed_{seed}.npy"
        q0_record = root / f"scores/q0_current8/seed_{seed}.json"
        base_21e = BASE.PINNED_21E.load_config()
        sealed, _ = BASE.PINNED_21E._sealed_checkpoint(base_21e, seed, device)
        sealed_path = workspace_path(base_21e["inputs"]["21c_checkpoint_root"], must_exist=True) / f"seed_{seed}/state_dict.pt"
        if not score_record_valid(q0_path, q0_record, len(fold.frame), file_sha(sealed_path),
                                  "Q0_CURRENT_SCORE_MEAN8"):
            q0 = BASE.PINNED_21C.score_numpy_panel(sealed, fold.raw_panel[:, :10, None],
                fold.x_source, fold.frame["instrument"].astype(str).tolist(),
                fold.frame["decision_date"].astype(str).tolist(), seed,
                batch_size=int(config["data_first"]["inference_batch_size"]), device=device).astype(np.float32)
            write_npy(q0_path, q0)
            write_json(q0_record, {"checkpoint_sha256": file_sha(sealed_path),
                "estimator_id": "Q0_CURRENT_SCORE_MEAN8", "score_file_sha256": file_sha(q0_path),
                "row_n": len(q0), "completed_at_utc": utc_now()})
        variants["q0_current8"][seed] = np.load(q0_path, allow_pickle=False)
        del model, sealed
        torch.cuda.empty_cache()
    frames = [
        BASE.prediction_frame(fold, selected, "Q1_SCORE_MEAN64", variants["selected_drc"],
            "E4_DATA_FIRST_2023", "selected_drc"),
        BASE.prediction_frame(fold, "SAME_BACKBONE_K0", "Q6_KOOPMAN_ONLY",
            variants["same_backbone_k0"], "E4_DATA_FIRST_2023", "same_backbone_k0"),
        BASE.prediction_frame(fold, "SEALED_21C_Q0", "Q0_CURRENT_SCORE_MEAN8",
            variants["q0_current8"], "E4_DATA_FIRST_2023", "q0_current8"),
    ]
    write_parquet(root / "predictions/design_predictions.parquet", pd.concat(frames, ignore_index=True))
    write_json(root / ".state/lane_complete.json", {"schema_version": "21F_V5_DESIGN_LANE_COMPLETE_V1",
        "lane_id": lane_id, "split_id": split_id, "variant_n": 3,
        "completed_at_utc": utc_now()})


def _provisional_report(selection: Mapping[str, Any], daily: pd.DataFrame,
                        contrasts: Sequence[Mapping[str, Any]]) -> str:
    ensemble = daily.loc[daily["is_ensemble"].astype(bool)]
    summary = ensemble.groupby(["fold_id", "score_variant"])["rankic"].mean().reset_index()
    return "\n".join([
        "# 21F v5 Data-first Provisional Report", "",
        "> 本报告先于 Q2 reverse validation 生成，不构成最终研究结论，禁止密封。", "",
        f"Provisional arm：`{selection['selected_arm_id']}`；runner-up：`{selection['runner_up_arm_id']}`。", "",
        "## 2023 ensemble mean daily RankIC", "", summary.to_markdown(index=False), "",
        "## Provisional contrasts", "", pd.DataFrame(contrasts).to_markdown(index=False), "",
        "## Deferred checks", "",
        "Q1-vs-Q2 convergence、top-two Q2 ranking、完整 estimator family、bootstrap/Holm 与 full 42 gates 均后置。", "",
    ])


def run_design_readout(config: Mapping[str, Any]) -> None:
    root = build_root(config)
    marker = root / ".state/data_first_complete.json"
    if marker.exists():
        return
    if not (root / ".state/refit_complete.json").exists():
        raise ContractError("refit must complete before design readout")
    roots = [prepare_lane_root(config, "design_lanes", lane_id, design=True) for lane_id in range(2)]
    launch_lanes(config, "design-readout-lane", roots)
    predictions = pd.concat([pd.read_parquet(lane_root / "predictions/design_predictions.parquet")
                             for lane_root in roots], ignore_index=True)
    write_parquet(root / "predictions/provisional_design_2023_scores.parquet", predictions)
    daily = BASE._daily_readout(predictions)
    write_csv(root / "provisional_daily_rankic.csv", daily.to_dict("records"), list(daily.columns))
    morphology, top30, lomo = BASE._morphology_tables(predictions)
    write_csv(root / "provisional_cross_seed_morphology.csv", morphology.to_dict("records"), list(morphology.columns))
    write_csv(root / "provisional_top30_turnover.csv", top30.to_dict("records"), list(top30.columns))
    write_csv(root / "provisional_lomo.csv", lomo.to_dict("records"), list(lomo.columns))
    contrasts = BASE._paired_design_contrasts(predictions)
    write_csv(root / "provisional_design_contrasts.csv", contrasts,
        [key for key in contrasts[0] if key != "contrast_order"])
    selection = json.loads((root / "provisional_selection.json").read_text())
    report = _provisional_report(selection, daily, contrasts)
    report_path = root / "21F_v5_data_first_provisional_report.md"
    report_path.write_text(report, encoding="utf-8")
    write_json(root / "provisional_decision.json", {
        "schema_version": "21F_V5_PROVISIONAL_DECISION_V1", "run_id": RUN_ID,
        "selected_arm_id": selection["selected_arm_id"],
        "estimator_id": "Q1_SCORE_MEAN64", "data_first_complete": True,
        "targeted_reverse_validation_status": "not_run",
        "full_reverse_validation_status": "not_run", "seal_authorized": False,
        "next_requirement_execution_authorized": False, "created_at_utc": utc_now()})
    write_json(marker, {"schema_version": "21F_V5_DATA_FIRST_COMPLETE_V1",
        "prediction_row_n": len(predictions), "report_sha256": file_sha(report_path),
        "seal_authorized": False, "completed_at_utc": utc_now()})
    write_json(root / "stage_status.json", {"schema_version": "21F_V5_STAGE_STATUS_V1",
        "run_id": RUN_ID, "stage": "data_first_complete", "status": "complete",
        "seal_authorized": False, "updated_at_utc": utc_now()})


def reverse_validation_lane(config: Mapping[str, Any], lane_id: int) -> None:
    root = prepare_lane_root(config, "reverse_lanes", lane_id, design=True)
    base = runtime_base_config(config, root)
    selection = json.loads((build_root(config) / "provisional_selection.json").read_text())
    arms = (selection["selected_arm_id"], selection["runner_up_arm_id"])
    BASE.configure_determinism()
    device = torch.device("cuda")
    feature_cache = BASE.load_feature_cache(base)
    fold_contract = base["inner_folds"][lane_id]
    inner_fold = BASE.load_fold_slice(base, fold_contract["select_id"],
        worker_role="SELECTION_COORDINATOR", feature_cache=feature_cache)
    design_id = ("DESIGN_EARLY_2023", "DESIGN_LATE_2023")[lane_id]
    design_fold = BASE.load_fold_slice(base, design_id, worker_role="FRESH_2023",
        allow_design=True, feature_cache=feature_cache)
    inner_frames = []
    for arm_id in arms:
        seed_scores = {}
        for seed in MODEL_SEEDS:
            checkpoint = checkpoint_source_path(config, fold_contract["fit_id"], arm_id, seed)
            score_path = root / f"inner_q2/{arm_id}/seed_{seed}.npy"
            record = root / f"inner_q2/{arm_id}/seed_{seed}.json"
            if not score_record_valid(score_path, record, len(inner_fold.frame),
                                      file_sha(checkpoint), "Q2_SCORE_MEAN256_REF"):
                model = BASE.build_model(arm_id, seed)
                model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
                model.to(device)
                score = BASE.score_fold(model, "Q2_SCORE_MEAN256_REF", inner_fold, arm_id,
                    seed, batch_size=1024, device=device)
                write_npy(score_path, score)
                write_json(record, {"checkpoint_sha256": file_sha(checkpoint),
                    "estimator_id": "Q2_SCORE_MEAN256_REF", "score_file_sha256": file_sha(score_path),
                    "row_n": len(score), "completed_at_utc": utc_now()})
                del model, score
                torch.cuda.empty_cache()
            seed_scores[seed] = np.load(score_path, allow_pickle=False)
        inner_frames.append(BASE.prediction_frame(inner_fold, arm_id, "Q2_SCORE_MEAN256_REF",
            seed_scores, "REVERSE_VALIDATION", "q2_ref256"))
    selected = selection["selected_arm_id"]
    design_scores = {}
    for seed in MODEL_SEEDS:
        checkpoint = build_root(config) / f"training/provisional_refit_checkpoints/seed_{seed}/state_dict.pt"
        score_path = root / f"design_q2/seed_{seed}.npy"
        record = root / f"design_q2/seed_{seed}.json"
        if not score_record_valid(score_path, record, len(design_fold.frame),
                                  file_sha(checkpoint), "Q2_SCORE_MEAN256_REF"):
            model = BASE.build_model(selected, seed)
            model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
            model.to(device)
            score = BASE.score_fold(model, "Q2_SCORE_MEAN256_REF", design_fold, selected,
                seed, batch_size=1024, device=device)
            write_npy(score_path, score)
            write_json(record, {"checkpoint_sha256": file_sha(checkpoint),
                "estimator_id": "Q2_SCORE_MEAN256_REF", "score_file_sha256": file_sha(score_path),
                "row_n": len(score), "completed_at_utc": utc_now()})
            del model, score
            torch.cuda.empty_cache()
        design_scores[seed] = np.load(score_path, allow_pickle=False)
    design_frame = BASE.prediction_frame(design_fold, selected, "Q2_SCORE_MEAN256_REF",
        design_scores, "REVERSE_VALIDATION", "q2_ref256")
    write_parquet(root / "predictions/inner_q2.parquet", pd.concat(inner_frames, ignore_index=True))
    write_parquet(root / "predictions/design_q2.parquet", design_frame)
    write_json(root / ".state/lane_complete.json", {"schema_version": "21F_V5_REVERSE_LANE_COMPLETE_V1",
        "lane_id": lane_id, "inner_arm_n": 2, "design_split_id": design_id,
        "completed_at_utc": utc_now()})


def run_reverse_validation(config: Mapping[str, Any]) -> None:
    root = build_root(config)
    if not (root / ".state/data_first_complete.json").exists():
        raise ContractError("data-first must complete before reverse validation")
    roots = [prepare_lane_root(config, "reverse_lanes", lane_id, design=True) for lane_id in range(2)]
    launch_lanes(config, "reverse-validation-lane", roots)
    inner_q2 = pd.concat([pd.read_parquet(item / "predictions/inner_q2.parquet") for item in roots],
        ignore_index=True)
    design_q2 = pd.concat([pd.read_parquet(item / "predictions/design_q2.parquet") for item in roots],
        ignore_index=True)
    write_parquet(root / "predictions/targeted_reverse_inner_q2.parquet", inner_q2)
    write_parquet(root / "predictions/targeted_reverse_design_q2.parquet", design_q2)
    q1 = pd.read_parquet(root / "predictions/provisional_inner_q1_scores.parquet")
    rows = []
    for identity, q2_group in inner_q2.groupby(["fold_id", "arm_id", "model_seed"], sort=True):
        fold_id, arm_id, seed = identity
        q1_group = q1.loc[(q1["fold_id"] == fold_id) & (q1["arm_id"] == arm_id) &
                          (q1["model_seed"] == seed)]
        left = q1_group[["decision_date", "instrument", "score", "label"]]
        right = q2_group[["decision_date", "instrument", "score", "label"]]
        rho = BASE.daily_score_spearman(left, right)
        overlap = BASE.daily_top30_overlap(left, right)
        rank1 = BASE.mean_daily_rankic(left["score"].to_numpy(), left["label"].to_numpy(),
            left["decision_date"].astype(str))[0]
        rank2 = BASE.mean_daily_rankic(right["score"].to_numpy(), right["label"].to_numpy(),
            right["decision_date"].astype(str))[0]
        passed = rho >= 0.95 and overlap >= 24 and abs(rank1 - rank2) <= 0.003
        rows.append({"fold_id": fold_id, "arm_id": arm_id, "model_seed": int(seed),
            "q1_q2_daily_spearman": rho, "q1_q2_top30_overlap": overlap,
            "q1_rankic": rank1, "q2_rankic": rank2, "rankic_abs_delta": abs(rank1-rank2),
            "convergence_pass": passed})
    write_csv(root / "targeted_reverse_convergence.csv", rows, list(rows[0]))
    selection = json.loads((root / "provisional_selection.json").read_text())
    arm_rank = {}
    for arm in (selection["selected_arm_id"], selection["runner_up_arm_id"]):
        values = []
        for fold in ("I0_SELECT_2021", "I1_SELECT_2022"):
            group = inner_q2.loc[(inner_q2["arm_id"] == arm) & (inner_q2["fold_id"] == fold) &
                                 (inner_q2["is_ensemble"])]
            values.append(BASE.mean_daily_rankic(group["score"].to_numpy(), group["label"].to_numpy(),
                group["decision_date"].astype(str))[0])
        arm_rank[arm] = min(values)
    ranking_stable = max(arm_rank, key=arm_rank.get) == selection["selected_arm_id"]
    selected_rows = [row for row in rows if row["arm_id"] == selection["selected_arm_id"]]
    supported = bool(ranking_stable and selected_rows and all(row["convergence_pass"] for row in selected_rows))
    decision_path = root / "provisional_decision.json"
    decision = json.loads(decision_path.read_text())
    decision["targeted_reverse_validation_status"] = (
        "targeted_reverse_supported" if supported else "targeted_reverse_not_supported")
    decision["targeted_ranking_stable"] = ranking_stable
    decision["full_reverse_validation_status"] = "not_run"
    decision["seal_authorized"] = False
    decision["updated_at_utc"] = utc_now()
    write_json(decision_path, decision)
    write_json(root / ".state/targeted_reverse_complete.json", {
        "schema_version": "21F_V5_TARGETED_REVERSE_COMPLETE_V1",
        "supported": supported, "ranking_stable": ranking_stable,
        "selected_convergence_pass": all(row["convergence_pass"] for row in selected_rows),
        "seal_authorized": False, "completed_at_utc": utc_now()})
    write_json(root / "stage_status.json", {"schema_version": "21F_V5_STAGE_STATUS_V1",
        "run_id": RUN_ID, "stage": "targeted_reverse_complete", "status": "complete",
        "seal_authorized": False, "updated_at_utc": utc_now()})


def run_data_first(config: Mapping[str, Any]) -> None:
    root = initialize_build(config)
    (root / "failure_record.json").unlink(missing_ok=True)
    run_arm_readout(config)
    run_refit(config)
    run_design_readout(config)


def record_failure(config: Mapping[str, Any], exc: BaseException) -> None:
    root = build_root(config)
    if not root.exists():
        return
    write_json(root / "failure_record.json", {"schema_version": "21F_V5_FAILURE_V1",
        "error_type": type(exc).__name__, "error_message": str(exc),
        "seal_authorized": False, "created_at_utc": utc_now()})
    write_json(root / "stage_status.json", {"schema_version": "21F_V5_STAGE_STATUS_V1",
        "run_id": RUN_ID, "stage": "technical_failure", "status": "fail",
        "seal_authorized": False, "updated_at_utc": utc_now()})


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--stage", choices=("data-first", "reverse-validation"),
        default="data-first")
    parser.add_argument("--worker", choices=("arm-readout-lane", "refit-lane",
        "design-readout-lane", "reverse-validation-lane"))
    parser.add_argument("--lane-id", type=int, choices=(0, 1))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    valid, errors = validate_authorization(config)
    if not valid:
        raise ContractError("execution forbidden before v5 authorization: " + ",".join(errors))
    if args.worker:
        if args.lane_id is None:
            raise ContractError("lane worker requires --lane-id")
        {"arm-readout-lane": arm_readout_lane, "refit-lane": refit_lane,
         "design-readout-lane": design_readout_lane,
         "reverse-validation-lane": reverse_validation_lane}[args.worker](config, args.lane_id)
        return 0
    try:
        if args.stage == "data-first":
            run_data_first(config)
        else:
            run_reverse_validation(config)
    except BaseException as exc:
        record_failure(config, exc)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
