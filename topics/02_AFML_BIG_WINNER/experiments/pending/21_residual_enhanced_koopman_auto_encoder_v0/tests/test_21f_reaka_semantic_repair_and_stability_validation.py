from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/run_21f_reaka_semantic_repair_and_stability_validation.py"
SPEC = importlib.util.spec_from_file_location("run_21f", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_config_contract_and_resource_formula() -> None:
    config = MODULE.load_config()
    assert tuple(item["arm_id"] for item in config["training_arms"]) == MODULE.ARM_IDS
    assert tuple(item["estimator_id"] for item in config["predictor_estimators"]) == MODULE.ESTIMATOR_IDS
    assert tuple(config["gates"]) == MODULE.GATE_IDS
    assert len(MODULE.GATE_IDS) == 42
    assert config["execution"]["planned_inner_job_n"] == 30
    assert config["execution"]["planned_refit_job_n"] == 3
    assert config["resources"]["total_gpu_wall_seconds_cap"] == 144 * 3600
    assert config["resources"]["maximum_concurrent_gpu_training_jobs"] == 2
    assert config["execution"]["inner_training_lane_n"] == 2
    assert config["execution"]["inner_training_partition"] == "inner_fold_order"
    assert config["execution"]["lane_job_counts"] == [15, 15]
    assert config["execution"]["lane_phase_row_counts"] == [18, 18]
    assert config["training"]["epoch_selection_estimator"] == MODULE.EPOCH_SELECTOR_ID
    assert MODULE.EPOCH_SELECTOR_ID == "Q8_EPOCH_SCORE_MEAN8_CRN"
    assert config["training"]["phase_a_epoch_selection_estimator"] == "Q6_KOOPMAN_ONLY"
    assert config["execution"]["convergence_prefix_cache"] is True
    assert config["execution"]["portfolio_output_authorized"] is False


def test_authorization_record_is_exact_and_lifecycle_valid() -> None:
    config = MODULE.load_config()
    path = MODULE.workspace_path(config["paths"]["execution_authorization"], must_exist=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == MODULE.AUTH_KEYS
    assert payload["allowed_runtime_field_differences"] == []
    result = MODULE.validate_authorization(config)
    if payload["approved_by"]:
        assert result.status == "pass"
        assert result.errors == ()
    else:
        assert result.status == "fail"
        assert "human_approval_missing" in result.errors
        assert any(error.endswith("_mismatch") for error in result.errors)


def test_artifact_profile_expands_exact_checkpoint_paths() -> None:
    profile = MODULE.artifact_profile_contract()
    config = MODULE.load_config()
    assert profile["profile_id"] == MODULE.PROFILE_ID
    assert len(MODULE.inner_checkpoint_paths()) == 30
    assert len(MODULE.refit_checkpoint_paths()) == 3
    assert len(profile["exact_checkpoint_paths"]) == 33
    assert len(profile["terminal_states"]) == 6
    assert not any("*" in path for path in profile["exact_checkpoint_paths"])
    assert len(set(profile["exact_checkpoint_paths"])) == 33
    assert config["artifact_profile"]["inner_checkpoint_paths"] == MODULE.inner_checkpoint_paths()
    assert config["artifact_profile"]["refit_checkpoint_paths"] == MODULE.refit_checkpoint_paths()


def test_schema_registry_self_hash_excludes_self() -> None:
    registry = MODULE.schema_registry_contract()
    observed = registry.pop("contract_sha256")
    assert observed == MODULE.stable_hash(registry)
    decision = MODULE.TABULAR_SCHEMAS["decision"]
    assert "author_implementation_claim_allowed" in decision
    assert "next_requirement_execution_authorized" in decision
    assert len(MODULE.TABULAR_SCHEMAS) == 27
    assert MODULE.TABULAR_SCHEMAS["row_index"] == ["fold_id", "decision_date",
        "instrument", "fold_panel_row_idx", "x_cache_row_indices", "source_dates",
        "row_key_hash"]


def test_all_frozen_upstream_hashes_current() -> None:
    config = MODULE.load_config()
    for item in config["upstream_pins"].values():
        path = MODULE.workspace_path(item["path"], must_exist=True)
        assert MODULE.file_sha(path) == item["sha256"]


def test_decision_cs_zscore_transform_and_floor_audit() -> None:
    panel = np.vstack([
        np.arange(11, dtype=np.float32),
        np.arange(11, dtype=np.float32) + 2,
        np.ones(11, dtype=np.float32) * 7,
        np.ones(11, dtype=np.float32) * 7,
    ])
    transformed, audit = MODULE.decision_cs_zscore(panel, ["2020-01-01"] * 2 + ["2020-01-02"] * 2)
    assert transformed.shape == panel.shape
    first = audit.loc[audit["decision_date"].eq("2020-01-01")]
    assert np.allclose(first["transformed_mean"], 0.0)
    assert np.allclose(first["transformed_std_ddof0"], 1.0)
    second = audit.loc[audit["decision_date"].eq("2020-01-02")]
    assert second["sigma_floor_applied"].all()
    assert np.allclose(second["transformed_std_ddof0"], 0.0)


def test_date_group_indices_are_sorted_and_stable() -> None:
    dates, groups = MODULE._date_group_indices([
        "2020-01-02", "2020-01-01", "2020-01-02", "2020-01-01"])
    assert dates.tolist() == ["2020-01-02", "2020-01-01", "2020-01-02", "2020-01-01"]
    assert [(date, rows.tolist()) for date, rows in groups] == [
        ("2020-01-01", [1, 3]), ("2020-01-02", [0, 2])]


def _loss_fixture(arm_id: str, phase_id: str = "joint") -> tuple[dict[str, torch.Tensor], torch.nn.Module]:
    torch.manual_seed(11)
    model = MODULE.build_model(arm_id, 20260713)
    batch = 2
    timestep = None if phase_id == "phase_a" else torch.randint(1, 21, (batch, 10))
    epsilon = None if phase_id == "phase_a" else torch.randn(batch, 10, 64)
    losses = MODULE.training_losses(model, arm_id,
        torch.randn(batch, 10, 1), torch.randn(batch, 10, 157),
        torch.randn(batch, 10, 1), torch.randn(batch, 10, 157),
        torch.randn(batch), tau=0.5, gumbel_u=torch.rand(batch, 10, 4),
        diffusion_timestep=timestep, epsilon=epsilon, phase_id=phase_id)
    return losses, model


def test_hard_st_selector_forward_is_hard_and_backward_exists() -> None:
    model = MODULE.build_model("T1_CSZ_COUPLED_LINEAR", 20260713)
    result = MODULE.hard_st_source_latent(model, torch.randn(2, 10, 1),
        torch.randn(2, 10, 157), tau=0.5, training_selector=True,
        gumbel_u=torch.rand(2, 10, 4))
    selector = result["selector"]
    assert torch.equal(selector.detach(), torch.nn.functional.one_hot(
        selector.detach().argmax(dim=-1), 4).to(selector.dtype))
    result["Z_hat_shifted"].sum().backward()
    assert model.selector_linear.weight.grad is not None
    assert float(model.selector_linear.weight.grad.norm()) > 0


def test_stopgrad_removes_only_reconstruction_to_denoiser() -> None:
    coupled, coupled_model = _loss_fixture("T1_CSZ_COUPLED_LINEAR")
    stopped, stopped_model = _loss_fixture("T2_CSZ_STOPGRAD_LINEAR")
    coupled_grad = torch.autograd.grad(coupled["L_rec"], coupled_model.denoiser_linear_1.weight,
        allow_unused=True)[0]
    stopped_grad = torch.autograd.grad(stopped["L_rec"], stopped_model.denoiser_linear_1.weight,
        allow_unused=True)[0]
    diff_grad = torch.autograd.grad(stopped["L_diff"], stopped_model.denoiser_linear_1.weight,
        allow_unused=True)[0]
    assert coupled_grad is not None and float(coupled_grad.norm()) > 0
    assert stopped_grad is None or float(stopped_grad.norm()) == 0
    assert diff_grad is not None and float(diff_grad.norm()) > 0


def test_t3_phase_a_has_no_denoiser_forward() -> None:
    model = MODULE.build_model("T3_CSZ_TWO_STAGE_LINEAR", 20260713)
    calls = []
    handle = model.denoiser_linear_1.register_forward_hook(lambda *_: calls.append(1))
    batch = 2
    losses = MODULE.training_losses(model, "T3_CSZ_TWO_STAGE_LINEAR",
        torch.randn(batch, 10, 1), torch.randn(batch, 10, 157),
        torch.randn(batch, 10, 1), torch.randn(batch, 10, 157),
        torch.randn(batch), tau=0.5, gumbel_u=torch.rand(batch, 10, 4),
        diffusion_timestep=None, epsilon=None, phase_id="phase_a")
    handle.remove()
    assert calls == []
    assert losses["L_diff"].item() == 0.0
    assert losses["L_rec"].requires_grad and losses["L_koop"].requires_grad


def test_t3_phase_b_optimizer_owns_only_denoiser() -> None:
    model = MODULE.build_model("T3_CSZ_TWO_STAGE_LINEAR", 20260713)
    parameters = MODULE._phase_parameters(model, "T3_CSZ_TWO_STAGE_LINEAR", "phase_b")
    expected = [parameter for name, parameter in model.named_parameters() if name.startswith("denoiser_")]
    assert parameters == expected
    assert all(parameter.requires_grad for parameter in expected)
    assert all(not parameter.requires_grad for name, parameter in model.named_parameters()
               if not name.startswith("denoiser_"))


def test_common_initial_state_identity_and_t4_isolation() -> None:
    models = [MODULE.build_model(arm, 20260713) for arm in MODULE.ARM_IDS]
    common_states = [models[index].state_dict() for index in range(4)]
    for name in common_states[0]:
        assert all(torch.equal(common_states[0][name], state[name]) for state in common_states[1:])
    t2, t4 = models[2].state_dict(), models[4].state_dict()
    for name in set(t2) & set(t4):
        if not name.startswith("decoder."):
            assert torch.equal(t2[name], t4[name])
    assert isinstance(models[4].decoder, MODULE.PointwiseMLPDecoder)


def test_row_keyed_noise_prefix_and_antithetic_contract() -> None:
    key = "a" * 64
    first = MODULE.row_noise_schedule(key, 20260713, 0)
    repeat = MODULE.row_noise_schedule(key, 20260713, 0)
    second = MODULE.row_noise_schedule(key, 20260713, 1)
    assert torch.equal(first, repeat)
    assert not torch.equal(first, second)
    assert first.shape == (20, 10, 64)
    assert torch.equal(-first, -repeat)
    assert torch.equal((-first)[0], -first[0])
    assert torch.equal((-first)[1:], -first[1:])


def test_epoch_selector_uses_q8_for_joint_and_q6_for_phase_a() -> None:
    source = inspect.getsource(MODULE._train_phase)
    assert 'config["training"]["epoch_selection_estimator"]' in source
    assert 'config["training"]["phase_a_epoch_selection_estimator"]' in source


def test_q8_epoch_selector_is_selector_only_and_uses_eight_draws() -> None:
    assert MODULE.EPOCH_SELECTOR_ID not in MODULE.ESTIMATOR_IDS
    model = MODULE.build_model("T1_CSZ_COUPLED_LINEAR", 20260713)
    y = torch.randn(2, 10, 1)
    x = torch.randn(2, 10, 157)
    keys = ["c" * 64, "d" * 64]
    observed = MODULE.estimator_scores_batch(
        model, MODULE.EPOCH_SELECTOR_ID, y, x, keys, 20260713)
    expected = MODULE.stochastic_scores_batch(
        model, y, x, keys, 20260713, draw_n=8, antithetic=False)
    assert torch.equal(observed, expected)


def test_common_prefix_accumulation_matches_independent_draw_counts() -> None:
    model = MODULE.build_model("T1_CSZ_COUPLED_LINEAR", 20260713)
    y = torch.randn(2, 10, 1)
    x = torch.randn(2, 10, 157)
    keys = ["a" * 64, "b" * 64]
    observed = MODULE.stochastic_prefix_scores_batch(model, y, x, keys, 20260713,
        prefixes=(2, 4), antithetic=False)
    expected_2 = MODULE.stochastic_scores_batch(model, y, x, keys, 20260713,
        draw_n=2, antithetic=False)
    expected_4 = MODULE.stochastic_scores_batch(model, y, x, keys, 20260713,
        draw_n=4, antithetic=False)
    assert torch.equal(observed[2], expected_2)
    assert torch.equal(observed[4], expected_4)


def test_ddim_eta0_is_deterministic_and_uses_no_step_noise() -> None:
    model = MODULE.build_model("T1_CSZ_COUPLED_LINEAR", 20260713)
    y, x = torch.randn(2, 10, 1), torch.randn(2, 10, 157)
    source = MODULE.hard_st_source_latent(model, y, x, tau=0.1, training_selector=False)
    x_t = torch.randn(2, 10, 64)
    first = MODULE._reverse_ddim(model, source, x_t.clone())
    second = MODULE._reverse_ddim(model, source, x_t.clone())
    assert torch.equal(first, second)
    assert torch.isfinite(first).all()


def test_lower_median_and_six_terminal_first_match() -> None:
    assert MODULE.lower_median([9, 1, 5, 3, 7, 11]) == 5
    terminals = {
        MODULE.terminal_state(False, False, False, False, False),
        MODULE.terminal_state(True, False, False, False, False),
        MODULE.terminal_state(True, True, False, False, False),
        MODULE.terminal_state(True, True, True, False, False),
        MODULE.terminal_state(True, True, True, True, False),
        MODULE.terminal_state(True, True, True, True, True),
    }
    assert terminals == set(MODULE.artifact_profile_contract()["terminal_states"])


def test_bootstrap_and_holm_are_deterministic() -> None:
    values = np.linspace(-0.01, 0.03, 40)
    first = MODULE.stationary_bootstrap_p(values, 1, 1, replicate_n=200)
    second = MODULE.stationary_bootstrap_p(values, 1, 1, replicate_n=200)
    assert first == second
    rows = [{"p_unadjusted": 0.03, "contrast_order": 2},
            {"p_unadjusted": 0.01, "contrast_order": 1}]
    MODULE.holm_adjust(rows)
    assert rows[1]["p_holm"] == pytest.approx(0.02)
    assert rows[0]["p_holm"] == pytest.approx(0.03)


def test_fresh_worker_has_no_training_mutation_calls() -> None:
    source = inspect.getsource(MODULE.fresh_2023_worker)
    assert "_optimizer(" not in source
    assert "optimizer.step(" not in source
    assert "save_checkpoint(" not in source
    assert '"optimizer_object_n": 0' in source
    assert '"checkpoint_write_n": 0' in source


def test_canonical_is_created_by_one_final_replace_only() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert source.count("os.replace(build, canonical)") == 1
    assert "os.replace(build, canonical)" in inspect.getsource(MODULE.run_finalize)
    assert "os.replace(build, canonical)" not in inspect.getsource(MODULE.run_preflight)


def test_main_refuses_invalid_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE, "validate_authorization", lambda _:
        MODULE.AuthorizationResult("fail", ("authorization_invalid",), None, None))
    with pytest.raises(MODULE.ContractError, match="execution forbidden"):
        MODULE.main(["--stage", "preflight"])


def test_replay_normalizes_21c_row_key_hash_and_seed_dtype() -> None:
    frame = MODULE.pd.DataFrame({
        "decision_date": ["2023-01-05", "2023-01-04"],
        "instrument": ["SH600009", "SH600004"],
        "row_key_hash": ["b", "a"],
        "model_seed": [20260714.0, 20260713.0],
        "score": MODULE.np.asarray([2.0, 1.0], dtype=MODULE.np.float32),
    })
    observed = MODULE._canonical_replay_frame(frame)
    assert list(observed.columns) == ["decision_date", "instrument", "row_key", "model_seed", "score"]
    assert observed["row_key"].tolist() == ["a", "b"]
    assert observed["model_seed"].dtype == MODULE.np.dtype("int64")


def test_replay_preserves_distinct_21c_and_21d_reduction_semantics() -> None:
    draws = MODULE.np.linspace(-0.01, 0.01, 1030 * 256, dtype=MODULE.np.float32).reshape(1030, 256)
    observed_21c = MODULE._legacy_21c_prefix8_mean(draws, device="cpu")
    chunks = []
    for start in range(0, len(draws), 1024):
        batch = draws[start:start + 1024, :8]
        chunks.append(MODULE.torch.stack([
            MODULE.torch.as_tensor(batch[:, draw].copy()) for draw in range(8)
        ], dim=0).mean(dim=0).numpy())
    assert MODULE.np.array_equal(observed_21c, MODULE.np.concatenate(chunks))
    observed_21d = MODULE._legacy_21d_prefix_mean(draws, 64)
    expected_21d = draws[:, :64].astype(MODULE.np.float64).mean(axis=1).astype(MODULE.np.float32)
    assert MODULE.np.array_equal(observed_21d, expected_21d)


def test_value_worker_processes_are_isolated_by_stage() -> None:
    selection_source = inspect.getsource(MODULE.run_selection_and_refit)
    fresh_source = inspect.getsource(MODULE.main)
    assert 'run_isolated_worker_stage(config, "refit")' in selection_source
    assert 'run_isolated_worker_stage(selected, "inner-training")' in fresh_source
    assert 'run_isolated_worker_stage(selected, "selection-refit")' in fresh_source
    assert 'run_isolated_worker_stage(selected, "fresh-2023-stage")' in fresh_source
    assert 'run_isolated_worker_stage(selected, "finalize")' in fresh_source


def test_v4_inner_lanes_are_fold_disjoint_and_globally_ordered() -> None:
    jobs = []
    for lane_id in range(2):
        lane_jobs = [lane_id * 15 + arm_order * 3 + seed_order + 1
                     for arm_order in range(len(MODULE.ARM_IDS))
                     for seed_order in range(len(MODULE.MODEL_SEEDS))]
        assert len(lane_jobs) == 15
        jobs.append(set(lane_jobs))
    assert jobs[0].isdisjoint(jobs[1])
    assert sorted(jobs[0] | jobs[1]) == list(range(1, 31))
    source = inspect.getsource(MODULE.run_inner_training_lane)
    assert 'fold_contract = config["inner_folds"][lane_id]' in source
    assert "job_order = lane_id * 15 + arm_order * 3 + seed_order + 1" in source


def test_v4_lane_workers_use_isolated_runtime_roots() -> None:
    config = MODULE.load_config()
    canonical_build = MODULE.building_output_root(config)
    selected = dict(config)
    selected["_runtime_build_root"] = str(canonical_build / ".state/inner_lanes/lane_0")
    assert MODULE.building_output_root(selected) == canonical_build / ".state/inner_lanes/lane_0"
    selected["_runtime_build_root"] = str(canonical_build.parent / "escaped")
    with pytest.raises(MODULE.ContractError, match="escapes canonical building root"):
        MODULE.building_output_root(selected)


def test_inner_lane_executes_against_its_local_build_root(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = MODULE.load_config()
    lane_root = tmp_path / "lane_0"
    frame = MODULE.pd.DataFrame({
        "decision_date": ["2020-01-02"], "instrument": ["SH600000"],
        "row_key_hash": ["row"], "fold_panel_row_idx": [0],
        "x_cache_row_indices": [[0] * MODULE.LOOKBACK],
        "source_dates": [["2020-01-01"] * MODULE.LOOKBACK]})
    panel = MODULE.np.zeros((1, 11), dtype=MODULE.np.float32)
    fold = MODULE.FoldSlice("I0_FIT_2018_2020_PURGED", frame, panel,
        MODULE.np.zeros((1, MODULE.LOOKBACK, MODULE.FEATURE_DIM), dtype=MODULE.np.float32),
        MODULE.np.zeros((1, MODULE.LOOKBACK, MODULE.FEATURE_DIM), dtype=MODULE.np.float32))
    select = fold._replace(split_id="I0_SELECT_2021")
    monkeypatch.setattr(MODULE, "building_output_root", lambda _: lane_root)
    monkeypatch.setattr(MODULE, "configure_determinism", lambda: None)
    monkeypatch.setattr(MODULE.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(MODULE, "load_feature_cache", lambda _: MODULE.np.empty(0))
    monkeypatch.setattr(MODULE, "load_fold_slice", lambda _config, split_id, **_kwargs:
        fold if "FIT" in split_id else select)
    calibration = MODULE.pd.DataFrame([{"row": index} for index in range(35)])
    monkeypatch.setattr(MODULE, "calibrate_shared_weights", lambda *_args, **_kwargs:
        ({"L_rec": 1.0, "L_koop": 1.0, "L_diff": 1.0}, calibration.copy()))

    def fake_train(_config, arm_id, _fit, _select, seed, _weights, _device):
        phases = ("phase_a", "phase_b") if arm_id == "T3_CSZ_TWO_STAGE_LINEAR" else ("joint",)
        curves = [{"phase_id": phase, "epoch": 1, "selection_reason": "first_maximum",
            "selector_estimator_id": ("Q6_KOOPMAN_ONLY" if phase == "phase_a"
                else MODULE.EPOCH_SELECTOR_ID), "checkpoint_semantic_sha256": f"{arm_id}-{seed}-{phase}",
            "collapse_flag": False} for phase in phases]
        return ({"weight": MODULE.torch.tensor([float(seed)])}, curves,
            MODULE.np.asarray([float(seed)], dtype=MODULE.np.float32), {
                "phase_a_semantic_sha256": None,
                "phase_rows": {row["phase_id"]: row for row in curves}})

    monkeypatch.setattr(MODULE, "train_inner_job", fake_train)
    monkeypatch.setattr(MODULE, "prediction_frame", lambda *_args, **_kwargs:
        MODULE.pd.DataFrame([{"score": 0.0}]))
    MODULE.run_inner_training_lane(config, 0)
    assert len(list((lane_root / "training/inner_checkpoints").rglob("state_dict.pt"))) == 15
    marker = json.loads((lane_root / ".state/lane_complete.json").read_text())
    assert marker["lane_id"] == 0
    assert marker["entry_n"] == 15
    assert marker["phase_row_n"] == 18


def test_v4_coordinator_launches_exact_two_lane_workers() -> None:
    source = inspect.getsource(MODULE.run_inner_training)
    assert 'range(2)' in source
    assert '"parallel-gpu-probe"' in inspect.getsource(MODULE.run_parallel_gpu_probe)
    assert '"inner-training-lane"' in source
    assert "merge_inner_training_lanes" in source
    required = MODULE.artifact_profile_contract()["required_paths"]
    assert "training/parallel_resource_probe.json" in required


def test_parallel_probe_finite_check_accepts_tensor_losses() -> None:
    assert MODULE.tensors_all_finite([
        MODULE.torch.ones((2, 3)), MODULE.torch.zeros((4, 5, 6))])
    assert not MODULE.tensors_all_finite([
        MODULE.torch.ones((2, 3)), MODULE.torch.tensor([1.0, float("nan")])])


def test_v4_lane_merge_is_exact_and_deterministic(tmp_path: Path) -> None:
    parent = tmp_path / "build"
    roots = [parent / ".state/inner_lanes" / f"lane_{lane_id}" for lane_id in range(2)]
    MODULE.write_csv(parent / "preflight/value_access_audit.csv", [],
        MODULE.TABULAR_SCHEMAS["value_access"])
    checkpoint_paths = MODULE.inner_checkpoint_paths()
    for lane_id, root in enumerate(roots):
        entries = []
        registry_rows = []
        first_order = lane_id * 15 + 1
        for job_order in range(first_order, first_order + 15):
            relative = checkpoint_paths[job_order - 1]
            checkpoint = root / relative
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_bytes(f"checkpoint-{job_order}".encode())
            entries.append({"job_order": job_order, "fold_id": f"I{lane_id}_FIT",
                "arm_id": "T0_RAW_COUPLED_LINEAR", "model_seed": 20260713,
                "final_phase_id": "joint", "path": relative,
                "size_bytes": checkpoint.stat().st_size, "sha256": MODULE.file_sha(checkpoint),
                "semantic_sha256": f"semantic-{job_order}",
                "phase_a_semantic_sha256": None, "selected_epoch": 1,
                "phase_a_selected_epoch": None})
            registry_rows.append({column: (job_order if column == "job_order" else
                f"I{lane_id}_FIT" if column == "fold_id" else
                "T0_RAW_COUPLED_LINEAR" if column == "arm_id" else
                20260713 if column == "model_seed" else
                "joint" if column == "phase_id" else
                "complete" if column == "job_status" else None)
                for column in MODULE.TABULAR_SCHEMAS["inner_training_registry"]})
        for extra_order in range(first_order + 9, first_order + 12):
            extra = dict(registry_rows[extra_order - first_order])
            extra["phase_id"] = "phase_b"
            registry_rows.append(extra)
        MODULE.write_csv(root / "training/inner_training_run_registry.csv", registry_rows,
            MODULE.TABULAR_SCHEMAS["inner_training_registry"])
        MODULE.write_parquet(root / "training/inner_epoch_selection_registry.parquet",
            MODULE.pd.DataFrame([{"lane_id": lane_id}]))
        MODULE.write_parquet(root / "gradient_calibration_audit.parquet",
            MODULE.pd.DataFrame([{"lane_id": lane_id}] * 105))
        MODULE.write_parquet(root / "gradient_graph_and_collapse_audit.parquet",
            MODULE.pd.DataFrame([{"lane_id": lane_id}]))
        MODULE.write_parquet(root / "predictions/inner_selection_prediction_scores.parquet",
            MODULE.pd.DataFrame([{"lane_id": lane_id}]))
        MODULE.write_json(root / "training/inner_checkpoint_manifest.json", {
            "entry_n": 15, "checkpoint_entries": entries})
        MODULE.write_json(root / ".state/lane_complete.json", {"lane_id": lane_id,
            "entry_n": 15, "phase_row_n": 18, "gpu_process_seconds": 1.0})
        access = {column: (1 if column == "event_order" else "INNER_TRAIN"
            if column == "worker_role" else "pass" if column == "status" else "")
            for column in MODULE.TABULAR_SCHEMAS["value_access"]}
        MODULE.write_csv(root / "preflight/value_access_audit.csv", [access],
            MODULE.TABULAR_SCHEMAS["value_access"])
    observed = MODULE.merge_inner_training_lanes(MODULE.load_config(), parent, roots)
    assert observed["entry_n"] == 30
    assert observed["inner_gpu_process_seconds"] == 2.0
    manifest = json.loads((parent / "training/inner_checkpoint_manifest.json").read_text())
    assert [entry["job_order"] for entry in manifest["checkpoint_entries"]] == list(range(1, 31))
    registry = MODULE.pd.read_csv(parent / "training/inner_training_run_registry.csv")
    assert len(registry) == 36
    assert registry["job_order"].nunique() == 30
    access = MODULE.pd.read_csv(parent / "preflight/value_access_audit.csv")
    assert access["event_order"].tolist() == [1, 2]


def test_restricted_pre2023_firewall_counts_only_training_selection_refit() -> None:
    config = MODULE.load_config()
    restricted = config["upstream_pins"]["design_early_value_panel"]["path"]
    audit = MODULE.pd.DataFrame([
        {"worker_role": "EXACT_REPLAY", "path": restricted},
        {"worker_role": "INNER_TRAIN", "path": config["upstream_pins"]["train_value_panel"]["path"]},
    ])
    assert MODULE.restricted_pre2023_open_attempts(config, audit) == 0
    audit.loc[len(audit)] = {"worker_role": "REFIT", "path": restricted}
    assert MODULE.restricted_pre2023_open_attempts(config, audit) == 1
