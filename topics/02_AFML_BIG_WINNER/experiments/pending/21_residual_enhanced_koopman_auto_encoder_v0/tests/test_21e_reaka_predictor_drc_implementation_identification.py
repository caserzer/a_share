from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/run_21e_reaka_predictor_drc_implementation_identification.py"
SPEC = importlib.util.spec_from_file_location("run_21e", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_config_cardinalities_and_firewalls() -> None:
    config = MODULE.load_config()
    assert tuple(item["arm_id"] for item in config["predictor_arms"]) == MODULE.PREDICTOR_IDS
    assert tuple(item["arm_id"] for item in config["training_arms"]) == MODULE.TRAINABLE_IDS
    assert len(config["contrasts"]) == 11
    assert tuple(config["gates"]) == MODULE.GATE_IDS
    assert config["execution"]["planned_training_job_n"] == 18
    assert config["execution"]["historical_design_holdout_readout_authorized"] is False
    assert config["execution"]["portfolio_output_authorized"] is False
    assert config["execution"]["seal_only_after_full_success"] is True


def test_authorization_template_is_not_executable() -> None:
    result = MODULE.validate_authorization(MODULE.load_config())
    assert result.status == "fail"
    assert "human_approval_missing" in result.errors
    assert any(error.endswith("_mismatch") for error in result.errors)


def test_authorization_exact_key_contract() -> None:
    path = MODULE.workspace_path(MODULE.load_config()["paths"]["execution_authorization"], must_exist=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == MODULE.AUTH_KEYS
    assert payload["allowed_runtime_field_differences"] == []


def test_artifact_profile_expands_exact_18_checkpoint_paths() -> None:
    config = MODULE.load_config()
    contract = MODULE.artifact_profile_contract(config)
    checkpoints = [path for path in contract["required_paths"] if path.endswith("/state_dict.pt")]
    assert len(checkpoints) == 18
    assert contract["artifact_profile_id"] == MODULE.PROFILE_ID
    assert contract["conditional_paths"] == {}
    assert not any("*" in path for path in contract["required_paths"])


def test_registry_closure() -> None:
    config = MODULE.load_config()
    arms = MODULE.implementation_arm_registry(config)
    predictors = MODULE.predictor_readout_registry(config)
    hypotheses = MODULE.hypothesis_registry()
    ambiguity = MODULE.ambiguity_registry()
    assert tuple(arms["arm_id"]) == MODULE.ALL_ARM_IDS
    assert len(arms) == 14
    assert len(predictors) == 7
    assert predictors.loc[predictors["point_predictor_id"].eq("zero_noise_reverse_path_proxy"), "conditional_mean_claim_allowed"].item() is False
    assert len(hypotheses) == 6
    assert len(ambiguity) == 9


def test_variant_topologies_are_exact_and_deterministic() -> None:
    a2_first = MODULE.build_variant_model("A2_RESBLOCK_20_STEP", 20260713)
    a2_second = MODULE.build_variant_model("A2_RESBLOCK_20_STEP", 20260713)
    names = set(dict(a2_first.named_parameters()))
    assert "denoiser_linear_1.weight" not in names
    assert "resblock_input.weight" in names
    assert "resblock_2_norm.weight" in names
    assert torch.equal(a2_first.resblock_input.weight, a2_second.resblock_input.weight)
    assert torch.equal(a2_first.resblock_1_norm.weight, torch.ones_like(a2_first.resblock_1_norm.weight))
    a3 = MODULE.build_variant_model("A3_POINTWISE_MLP_DECODER", 20260713)
    assert isinstance(a3.decoder, MODULE.PointwiseMLPDecoder)
    sample = torch.zeros((2, 10, 64))
    assert a3.decoder(sample).shape == (2, 10, 1)


def _losses_for_graph(graph: str) -> tuple[dict[str, torch.Tensor], torch.nn.Module]:
    torch.manual_seed(7)
    model = MODULE.build_variant_model("G1_STOPGRAD_X0_RECON", 20260713)
    batch = 2
    losses = MODULE.implementation_training_losses(
        model,
        "G1_STOPGRAD_X0_RECON",
        graph,
        torch.randn(batch, 10, 1),
        torch.randn(batch, 10, 157),
        torch.randn(batch, 10, 1),
        torch.randn(batch, 10, 157),
        torch.randn(batch),
        tau=0.5,
        gumbel_u=torch.rand(batch, 10, 4),
        diffusion_timestep=torch.randint(1, 21, (batch, 10)),
        epsilon=torch.randn(batch, 10, 64),
    )
    return losses, model


def test_stopgrad_removes_only_rec_to_denoiser_gradient() -> None:
    coupled, coupled_model = _losses_for_graph("x0_coupled")
    stopped, stopped_model = _losses_for_graph("stopgrad_x0_recon")
    coupled_grad = torch.autograd.grad(coupled["L_rec"], coupled_model.denoiser_linear_1.weight, allow_unused=True)[0]
    stopped_grad = torch.autograd.grad(stopped["L_rec"], stopped_model.denoiser_linear_1.weight, allow_unused=True)[0]
    diff_grad = torch.autograd.grad(stopped["L_diff"], stopped_model.denoiser_linear_1.weight, allow_unused=True)[0]
    assert coupled_grad is not None and float(coupled_grad.norm()) > 0
    assert stopped_grad is None or float(stopped_grad.norm()) == 0
    assert diff_grad is not None and float(diff_grad.norm()) > 0


def test_teacher_oracle_never_promotes() -> None:
    rng = np.random.default_rng(3)
    early = {
        "label": rng.normal(size=300),
        "frame": pd.DataFrame({"decision_date": np.repeat(["2023-01-03", "2023-01-04", "2023-01-05"], 100)}),
    }
    scores = {
        arm: {seed: rng.normal(size=300) for seed in MODULE.MODEL_SEEDS}
        for arm in ("G0_CURRENT_X0_COUPLED", "G1_STOPGRAD_X0_RECON", "G2_TEACHER_LATENT_RECON_ORACLE")
    }
    selected = MODULE.choose_training_graph(scores, early)
    assert selected["selected_arm_id"] in {"G0_CURRENT_X0_COUPLED", "G1_STOPGRAD_X0_RECON"}
    assert selected["forbidden_oracle_arm_id"] == "G2_TEACHER_LATENT_RECON_ORACLE"


def test_diffusion_schedule_and_arm_isolation() -> None:
    schedule20 = MODULE.generic_schedule(20, "cpu")
    schedule100 = MODULE.generic_schedule(100, "cpu")
    assert len(schedule20["beta"]) == 20
    assert len(schedule100["beta"]) == 100
    assert schedule20["beta"][0] == schedule100["beta"][0]
    assert schedule20["beta"][-1] == schedule100["beta"][-1]
    assert MODULE.diffusion_steps_for_arm("A1_MLP_100_STEP") == 100
    assert MODULE.diffusion_steps_for_arm("A2_RESBLOCK_20_STEP") == 20


def test_late_worker_has_no_training_or_checkpoint_write() -> None:
    source = inspect.getsource(MODULE.run_late_readout)
    assert "build_optimizer(" not in source
    assert "optimizer_step(" not in source
    assert "torch.save(" not in source
    assert '"optimizer_object_n": 0' in source
    assert '"checkpoint_write_n": 0' in source


def test_canonical_root_only_created_by_finalize_rename() -> None:
    whole_source = RUNNER.read_text(encoding="utf-8")
    assert "os.replace(build, canonical)" in inspect.getsource(MODULE.run_finalize)
    assert "os.replace(build, canonical)" not in inspect.getsource(MODULE.run_preflight)
    assert whole_source.count("os.replace(build, canonical)") == 1


def test_no_portfolio_artifacts_in_success_profile() -> None:
    required = MODULE.required_artifact_paths(MODULE.load_config())
    forbidden = ("portfolio", "sharpe", "turnover", "annualized_return", "top30_daily")
    assert not any(any(token in path.lower() for token in forbidden) for path in required)


def test_p0_prefix8_matches_21c_for_first_rows() -> None:
    if not torch.cuda.is_available():
        pytest.skip("exact 21C replay requires the authorized CUDA reduction route")
    config = MODULE.load_config()
    seed_scores = []
    for seed in MODULE.MODEL_SEEDS:
        _, draws, _ = MODULE._draw_matrix(config, "validation_early", seed)
        seed_scores.append(torch.as_tensor(np.array(draws[:32, :8], copy=True), device="cuda").T.contiguous().mean(dim=0).cpu().numpy())
    p0 = seed_scores[0]
    upstream = pd.read_parquet(MODULE.workspace_path(config["inputs"]["21c_early_scores"], must_exist=True))
    expected = upstream.loc[upstream["model_seed"].eq(20260713), "score"].head(32).to_numpy(dtype=np.float32)
    assert np.array_equal(p0, expected)
    ensemble = np.stack([values.astype(np.float64) for values in seed_scores]).mean(axis=0)
    expected_ensemble = upstream.loc[upstream["score_role"].eq("ensemble"), "score"].head(32).to_numpy(dtype=np.float64)
    assert np.array_equal(ensemble, expected_ensemble)


def test_main_refuses_execution_before_authorization() -> None:
    with pytest.raises(MODULE.ContractError, match="execution forbidden"):
        MODULE.main(["--stage", "preflight"])
