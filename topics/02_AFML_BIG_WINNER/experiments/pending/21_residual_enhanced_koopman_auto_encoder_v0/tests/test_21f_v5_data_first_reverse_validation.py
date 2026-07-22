from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/run_21f_v5_data_first_reverse_validation.py"
SPEC = importlib.util.spec_from_file_location("run_21f_v5", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_data_first_contract_is_provisional_and_two_lane() -> None:
    config = MODULE.load_config()
    assert config["identity"]["requirement_version"] == MODULE.REQUIREMENT_VERSION
    assert config["data_first"]["estimator_id"] == "Q1_SCORE_MEAN64"
    assert config["data_first"]["draw_n"] == 64
    assert config["resources"]["maximum_concurrent_gpu_jobs"] == 2
    assert config["execution"]["seal_authorized"] is False
    assert config["execution"]["next_requirement_execution_authorized"] is False


def test_source_e2_is_complete_and_byte_pinned() -> None:
    config = MODULE.load_config()
    observed = MODULE.validate_source_e2(config)
    assert observed["entry_n"] == 30
    assert observed["manifest_sha256"] == config["pins"]["source_inner_manifest_sha256"]


def test_authorization_record_exact_lifecycle() -> None:
    config = MODULE.load_config()
    path = MODULE.workspace_path(config["paths"]["authorization"])
    if not path.exists():
        valid, errors = MODULE.validate_authorization(config)
        assert valid is False
        assert errors == ["authorization_missing"]
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == MODULE.AUTH_KEYS
    valid, errors = MODULE.validate_authorization(config)
    if payload["approved_by"]:
        assert valid, errors
    else:
        assert not valid
        assert "human_approval_missing" in errors


def test_score_record_requires_checkpoint_estimator_shape_and_hash(tmp_path: Path) -> None:
    score_path = tmp_path / "score.npy"
    record_path = tmp_path / "score.json"
    MODULE.write_npy(score_path, np.asarray([1.0, 2.0], dtype=np.float32))
    MODULE.write_json(record_path, {
        "checkpoint_sha256": "checkpoint",
        "estimator_id": "Q1_SCORE_MEAN64",
        "score_file_sha256": MODULE.file_sha(score_path),
    })
    assert MODULE.score_record_valid(score_path, record_path, 2,
        "checkpoint", "Q1_SCORE_MEAN64")
    assert not MODULE.score_record_valid(score_path, record_path, 3,
        "checkpoint", "Q1_SCORE_MEAN64")
    assert not MODULE.score_record_valid(score_path, record_path, 2,
        "other", "Q1_SCORE_MEAN64")


def test_reverse_lane_mounts_inner_and_design_indexes() -> None:
    source = inspect.getsource(MODULE.prepare_lane_root)
    assert 'index_names = ["pre_2023_row_index.parquet"]' in source
    assert 'index_names.append("design_2023_row_index.parquet")' in source


def test_runtime_worker_root_is_rebound_to_v5_canonical_boundary(tmp_path: Path) -> None:
    config = MODULE.load_config()
    runtime = MODULE.runtime_base_config(config, tmp_path)
    assert runtime["paths"]["canonical_output_root"] == config["paths"]["output_root"]
    assert runtime["_runtime_build_root"] == str(tmp_path)


def test_refit_defers_noncontrolling_fixed_epoch_readout() -> None:
    source = inspect.getsource(MODULE.train_fixed_phase)
    assert "score_fold" not in source
    assert '"fixed_epoch_readout_status": "deferred_not_controlling"' in source


def test_workers_persist_before_coordinator_merge() -> None:
    arm_source = inspect.getsource(MODULE.arm_readout_lane)
    design_source = inspect.getsource(MODULE.design_readout_lane)
    assert "write_npy(score_path, score)" in arm_source
    assert "score_record_valid" in arm_source
    assert "write_npy(score_path, score)" in design_source
    assert "score_record_valid" in design_source
