from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch


EPISODE = Path(__file__).resolve().parents[1]
RUNNER_PATH = EPISODE / "src/run_21c_full_reaka_pit_proxy_replication.py"
SPEC = importlib.util.spec_from_file_location("ep21c_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def synthetic_batch(batch: int = 2) -> tuple[torch.Tensor, ...]:
    generator = torch.Generator().manual_seed(7)
    y = torch.randn((batch, 10, 1), generator=generator)
    x = torch.randn((batch, 10, 157), generator=generator)
    forecast = torch.randn((batch,), generator=generator)
    next_x = torch.randn((batch, 157), generator=generator)
    y_teacher_np, x_teacher_np = runner.shifted_teacher_arrays(
        y.numpy(), x.numpy(), forecast.numpy(), next_x.numpy()
    )
    y_teacher = torch.from_numpy(y_teacher_np)
    x_teacher = torch.from_numpy(x_teacher_np)
    uniform = torch.rand((batch, 10, 4), generator=generator)
    timestep = torch.randint(1, 21, (batch, 10), generator=generator)
    epsilon = torch.randn((batch, 10, 64), generator=generator)
    return y, x, y_teacher, x_teacher, forecast, uniform, timestep, epsilon


def test_source_config_is_static_and_frozen() -> None:
    config = runner.load_config()
    assert config["identity"]["requirement_version"] == "21C_FULL_v4"
    assert config["architecture"]["gumbel_clamp_min"] == 1e-10
    assert config["architecture"]["gumbel_clamp_max"] == 1 - 1e-10
    serialized = json.dumps(config)
    assert "approved_21c_runner_sha256" not in serialized
    assert config["training"]["model_seeds"] == list(runner.MODEL_SEEDS)
    assert config["performance"] == {
        "successor_of": "21C_FULL_v3",
        "feature_cache_residency": "shared_process_ram_copy",
        "inference_noise_device": "cpu_row_seeded_batched_schedule",
        "inference_batch_size": 1024,
        "training_batch_semantics": "unchanged_resource_probe_selected_256",
        "inference_noise_seed_contract": (
            "unchanged_sha256_row_key_uint64_prefix_mod_2_63"
        ),
    }


def test_v3_exclusion_registry_is_frozen_and_entire_instrument_scope() -> None:
    config = runner.load_config()
    settings = config["universe_exclusion"]
    path = runner.workspace_path(settings["registry_path"], must_exist=True)
    assert runner.file_sha(path) == settings["registry_sha256"]
    registry = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert list(registry.columns) == runner.EXCLUSION_COLUMNS
    assert len(registry) == registry["instrument"].nunique() == 396
    assert set(registry["exclusion_scope"]) == {
        "all_folds_entire_instrument_history"
    }
    assert set(registry["source_requirement_version"]) == {"21C_FULL_v2"}


def test_missing_authorization_is_canonical_and_value_free(tmp_path: Path) -> None:
    config = runner.load_config()
    result = runner.validate_authorization(config, tmp_path / "missing.json")
    assert result.status == "missing"
    assert result.observation == "MISSING"
    resolved = runner.resolved_config(config, result)
    assert resolved["execution_authorization_sha256"] is None
    assert resolved["approved_21c_implementation"] is None
    assert resolved["approved_21b"] is None
    assert resolved["approved_21a_lineage"] is None
    assert resolved["scope_restart_decision_path"] is None
    assert resolved["scope_restart_decision_sha256"] is None


def test_authorization_rejects_extra_key_before_any_value_open(
    tmp_path: Path,
) -> None:
    config = runner.load_config()
    payload = {key: "0" * 64 for key in runner.AUTHORIZATION_KEYS}
    payload.update(
        {
            "scope_restart_decision_path": config["paths"][
                "scope_restart_decision"
            ],
            "approved_21b_output_root": "outputs/corrected_v5",
            "approved_21b_requirement_version": "21B_v5",
            "approved_21b_contract_erratum_id": "erratum-1",
            "approved_21b_contract_erratum_path": (
                "outputs/corrected_v5/contract_erratum.json"
            ),
            "approved_21a_paper_lineage_erratum_path": (
                "outputs/corrected_v5/paper_lineage_erratum.json"
            ),
            "scope_override": (
                "full_reaka_local_validation_sanity_with_v2_missing_teacher_instrument_exclusion"
            ),
            "historical_holdout_readout_authorized": False,
            "reviewer_role": "human",
            "reviewed_at_utc": "2026-07-16T00:00:00Z",
            "authorization_status": "approved",
            "extra": "forbidden",
        }
    )
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = runner.validate_authorization(config, path)
    assert result.status == "invalid"
    assert "authorization_schema_exact" in result.errors
    assert result.payload is None


def test_scope_restart_is_independent_and_nonexecuting() -> None:
    requirement_hash = "a" * 64
    payload = {
        "decision_id": "restart-21c-full",
        "superseded_route": (
            "requirement_21c_single_vs_adaptive_koopman_nested_ablation.md"
        ),
        "approved_route": "requirement_21c_full_reaka_pit_proxy_replication.md",
        "superseded_estimand": "nested_module_attribution",
        "approved_estimand": (
            "full_architecture_local_validation_sanity_on_v2_missing_teacher_instrument_excluded_pit_universe"
        ),
        "requirement_sha256": requirement_hash,
        "historical_holdout_readout_authorized": False,
        "execution_authorized": False,
        "reviewer_role": "human",
        "reviewed_at_utc": "2026-07-16T00:00:00Z",
        "decision_status": "approved_scope_restart_only",
    }
    assert runner.validate_scope_restart(payload, requirement_hash) == (True, [])
    payload["execution_authorized"] = True
    valid, errors = runner.validate_scope_restart(payload, requirement_hash)
    assert valid is False
    assert "scope_restart_execution_authorized_match" in errors


def test_current_uncorrected_21b_v4_is_rejected_before_panel_open() -> None:
    authorization = runner.AuthorizationResult(
        "pass",
        "a" * 64,
        "a" * 64,
        {"approved_21b_requirement_version": "21B_v4"},
        (),
    )
    with pytest.raises(runner.ContractError, match="uncorrected observed 21B_v4"):
        runner.validate_corrected_21b_successor(runner.load_config(), authorization)


def test_runtime_event_aggregation_is_derived_not_a_zero_constant() -> None:
    frame = pd.DataFrame(
        [
            {
                "event_seq": "0",
                "process_id": "selection-worker",
                "stage": "train-r2",
                "access_scope": "train",
                "operation": "panel_open",
                "path": "experiments/example/panel.bin",
                "path_class": "source_panel",
                "value_token_requested": "true",
                "value_decoded": "true",
                "decision_date": "2023-12-14",
                "status": "allowed",
                "reason": "",
            },
            {
                "event_seq": "1",
                "process_id": "selection-worker",
                "stage": "train-r2",
                "access_scope": "historical_design_holdout",
                "operation": "metric_compute",
                "path": "experiments/example/holdout.bin",
                "path_class": "outcome",
                "value_token_requested": "false",
                "value_decoded": "false",
                "decision_date": "",
                "status": "denied",
                "reason": "firewall",
            },
        ],
        columns=runner.RUNTIME_EVENT_COLUMNS,
    )
    counters = runner.runtime_counters(frame, "2023-12-13")
    assert counters["post_cutoff_value_token_materialization_count"] == 1
    assert counters["post_cutoff_outcome_value_decode_count"] == 1
    assert counters["historical_holdout_metric_count"] == 1
    aggregate = runner.aggregate_runtime_events(frame, "log.csv", "a" * 64)
    assert aggregate["event_count"].sum() == 2
    assert set(aggregate["source_log_path"]) == {"log.csv"}


def test_model_topology_shapes_and_parameter_order_are_exact() -> None:
    model = runner.build_model(runner.MODEL_SEEDS[0])
    y, x, *_ = synthetic_batch(3)
    source = model.source_latent(
        y, x, tau=0.1, training_selector=False
    )
    assert source["Z_source"].shape == (3, 10, 64)
    assert source["selector"].shape == (3, 10, 4)
    assert source["K_selected"].shape == (3, 10, 64, 64)
    assert source["Z_hat_shifted"].shape == (3, 10, 64)
    assert runner.ordered_parameter_names(model)[12] == "K_codebook.weight"
    assert len(runner.ordered_parameter_names(model)) == 21


def test_koopman_orientation_is_left_matrix_multiply() -> None:
    codebook = torch.zeros((1, 2, 2))
    codebook[0] = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    selector = torch.ones((1, 1, 1))
    latent = torch.tensor([[[5.0, 7.0]]])
    selected = torch.einsum("btq,qij->btij", selector, codebook)
    observed = torch.einsum("btij,btj->bti", selected, latent)
    assert observed.tolist() == [[[19.0, 43.0]]]


def test_gumbel_soft_training_clamp_and_hard_tie_rule() -> None:
    logits = torch.zeros((1, 1, 4))
    uniform = torch.tensor([[[0.0, 1.0, 0.5, 0.25]]])
    selector = runner.soft_gumbel_selector(logits, uniform, 1.0)
    manual = torch.softmax(
        (-torch.log(-torch.log(uniform.double().clamp(1e-10, 1 - 1e-10)))).float(),
        dim=-1,
    )
    torch.testing.assert_close(selector, manual)
    assert torch.isfinite(selector).all()
    model = runner.build_model(runner.MODEL_SEEDS[0])
    for parameter in model.parameters():
        parameter.data.zero_()
    y, x, *_ = synthetic_batch(1)
    source = model.source_latent(y, x, tau=0.1, training_selector=False)
    assert torch.argmax(source["selector"], dim=-1).unique().item() == 0


def test_diffusion_schedule_and_reverse_variance_are_exact() -> None:
    schedule = runner.diffusion_schedule()
    assert len(schedule["beta"]) == 20
    assert schedule["beta"][0].item() == pytest.approx(1e-4)
    assert schedule["beta"][-1].item() == pytest.approx(2e-2)
    torch.testing.assert_close(
        schedule["alpha_bar"], torch.cumprod(1 - schedule["beta"], dim=0)
    )
    assert schedule["posterior_variance"][0].item() == pytest.approx(0.0)


def test_training_loss_uses_shared_teacher_branch_and_gradients() -> None:
    model = runner.build_model(runner.MODEL_SEEDS[0])
    batch = synthetic_batch(2)
    losses = runner.training_losses(
        model,
        *batch[:5],
        tau=0.7,
        gumbel_u=batch[5],
        diffusion_timestep=batch[6],
        epsilon=batch[7],
    )
    torch.testing.assert_close(
        losses["L_total"],
        losses["L_rec"] + losses["L_koop"] + losses["L_diff"],
    )
    losses["L_total"].backward()
    for module in (
        model.return_encoder,
        model.feature_encoder,
        model.gate_linear,
    ):
        assert all(parameter.grad is not None for parameter in module.parameters())


def test_training_loss_is_batch_duplication_invariant() -> None:
    model = runner.build_model(runner.MODEL_SEEDS[0])
    batch = synthetic_batch(1)
    single = runner.training_losses(
        model,
        *batch[:5],
        tau=0.5,
        gumbel_u=batch[5],
        diffusion_timestep=batch[6],
        epsilon=batch[7],
    )
    duplicate_batch = tuple(value.repeat((2,) + (1,) * (value.ndim - 1)) for value in batch)
    duplicate = runner.training_losses(
        model,
        *duplicate_batch[:5],
        tau=0.5,
        gumbel_u=duplicate_batch[5],
        diffusion_timestep=duplicate_batch[6],
        epsilon=duplicate_batch[7],
    )
    for key in ("L_rec", "L_koop", "L_diff", "L_total"):
        torch.testing.assert_close(single[key], duplicate[key])


def test_teacher_shift_is_exact_and_validation_has_no_materializer_route() -> None:
    y = np.arange(20, dtype=np.float32).reshape(2, 10, 1)
    x = np.arange(2 * 10 * 157, dtype=np.float32).reshape(2, 10, 157)
    forecast = np.asarray([20.0, 21.0], dtype=np.float32)
    next_x = np.full((2, 157), 99.0, dtype=np.float32)
    y_teacher, x_teacher = runner.shifted_teacher_arrays(y, x, forecast, next_x)
    np.testing.assert_array_equal(y_teacher[:, :9], y[:, 1:])
    np.testing.assert_array_equal(y_teacher[:, 9, 0], forecast)
    np.testing.assert_array_equal(x_teacher[:, :9], x[:, 1:])
    np.testing.assert_array_equal(x_teacher[:, 9], next_x)


def test_teacher_perturbation_cannot_enter_inference_signature() -> None:
    model = runner.build_model(runner.MODEL_SEEDS[0])
    y, x, y_teacher, x_teacher, *_ = synthetic_batch(1)
    keys = [("000001", "2023-07-03")]
    first = runner.inference_scores(model, y, x, keys, runner.MODEL_SEEDS[0])
    model.teacher_latent(y_teacher + 1000, x_teacher - 1000)
    second = runner.inference_scores(model, y, x, keys, runner.MODEL_SEEDS[0])
    torch.testing.assert_close(first, second, rtol=0, atol=0)


def test_inference_score_is_batch_and_order_invariant() -> None:
    model = runner.build_model(runner.MODEL_SEEDS[0])
    y, x, *_ = synthetic_batch(2)
    keys = [("000001", "2023-07-03"), ("600000", "2023-07-03")]
    forward = runner.inference_scores(model, y, x, keys, runner.MODEL_SEEDS[0])
    reverse = runner.inference_scores(
        model, y.flip(0), x.flip(0), list(reversed(keys)), runner.MODEL_SEEDS[0]
    ).flip(0)
    torch.testing.assert_close(forward, reverse, rtol=0, atol=0)


def test_v4_cpu_noise_schedule_preserves_per_row_sequential_rng_order() -> None:
    keys = [("SH600000", "2023-07-03"), ("SZ000001", "2023-07-04")]
    seed = runner.MODEL_SEEDS[0]
    draw_id = 3
    observed = runner.row_seeded_noise_schedule(
        keys, seed, draw_id, dtype=torch.float32, device="cpu"
    )
    assert observed.shape == (2, 20, 10, 64)
    for row_index, (instrument, decision_date) in enumerate(keys):
        generator = torch.Generator(device="cpu").manual_seed(
            runner.row_draw_seed(
                runner.RUN_ID,
                seed,
                instrument,
                decision_date,
                draw_id,
            )
        )
        sequential = torch.cat(
            [
                torch.randn((1, 10, 64), generator=generator)
                for _ in range(20)
            ]
        )
        torch.testing.assert_close(observed[row_index], sequential, rtol=0, atol=0)


def test_initialization_and_semantic_hash_are_repeatable() -> None:
    first = runner.build_model(runner.MODEL_SEEDS[0])
    second = runner.build_model(runner.MODEL_SEEDS[0])
    assert runner.model_state_semantic_hash(first.state_dict()) == (
        runner.model_state_semantic_hash(second.state_dict())
    )
    hidden = first.return_encoder.hidden_size
    assert torch.count_nonzero(first.return_encoder.bias_hh_l0) == 0
    assert torch.all(first.return_encoder.bias_ih_l0[hidden : 2 * hidden] == 1)
    assert torch.count_nonzero(first.return_encoder.bias_ih_l0[:hidden]) == 0
    assert torch.count_nonzero(first.return_encoder.bias_ih_l0[2 * hidden :]) == 0
    assert not torch.equal(
        first.K_codebook.weight[0], first.K_codebook.weight[1]
    )


def test_optimizer_is_explicit_single_group_and_tau_is_closed_form() -> None:
    config = runner.load_config()
    model = runner.build_model(runner.MODEL_SEEDS[0])
    optimizer = runner.build_optimizer(model, config)
    assert len(optimizer.param_groups) == 1
    group = optimizer.param_groups[0]
    assert group["amsgrad"] is False
    assert group["foreach"] is False
    assert group["fused"] is False
    assert group["capturable"] is False
    assert runner.tau_for_step(0, 100) == 1.0
    assert runner.tau_for_step(99, 100) == pytest.approx(0.1)


def test_one_seed_training_selects_only_validation_early_checkpoint() -> None:
    config = runner.load_config()
    config["training"]["max_epochs"] = 1
    config["training"]["early_stopping_patience"] = 1
    batch = synthetic_batch(4)
    labels = np.asarray([0.1, 0.2, -0.2, -0.1], dtype=np.float32)
    state, curves, scores = runner.train_one_seed(
        config,
        model_seed=runner.MODEL_SEEDS[0],
        train_y_source=batch[0].numpy(),
        train_x_source=batch[1].numpy(),
        train_y_teacher=batch[2].numpy(),
        train_x_teacher=batch[3].numpy(),
        train_forecast_y=batch[4].numpy(),
        validation_y_source=batch[0].numpy(),
        validation_x_source=batch[1].numpy(),
        validation_labels=labels,
        validation_instruments=["A", "B", "A", "B"],
        validation_decision_dates=[
            "2023-01-03",
            "2023-01-03",
            "2023-01-04",
            "2023-01-04",
        ],
        selected_batch_size=2,
        device="cpu",
        minimum_rankic_n=2,
    )
    assert len(curves) == 1
    assert curves[0]["optimizer_step_end"] == 2
    assert curves[0]["validation_early_complete_day_n"] == 2
    assert len(state) == len(runner.build_model(runner.MODEL_SEEDS[0]).state_dict())
    assert scores.shape == (4,)


def test_ensemble_is_three_seed_arithmetic_mean_not_best_seed() -> None:
    observed = runner.ensemble_seed_scores(
        {
            runner.MODEL_SEEDS[0]: np.asarray([1.0, 4.0]),
            runner.MODEL_SEEDS[1]: np.asarray([2.0, 5.0]),
            runner.MODEL_SEEDS[2]: np.asarray([6.0, 9.0]),
        }
    )
    np.testing.assert_array_equal(observed, [3.0, 6.0])


@pytest.mark.parametrize(
    ("scores", "labels", "expected"),
    [
        ([1, 2, 3, 4], [1, 2, 3, 4], 1.0),
        ([1, 2, 3, 4], [4, 3, 2, 1], -1.0),
        ([1, 2, 3, 4], [4, 1, 3, 2], -0.4),
    ],
)
def test_rankic_average_rank_fixture(
    scores: list[int], labels: list[int], expected: float
) -> None:
    observed = runner.rankic(np.asarray(scores), np.asarray(labels), minimum_n=2)
    assert observed == pytest.approx(expected)


def test_rankic_rejects_constant_nan_and_partial_denominator() -> None:
    assert math.isnan(runner.rankic(np.ones(100), np.arange(100)))
    assert math.isnan(runner.rankic(np.arange(100), np.ones(100)))
    values = np.arange(100, dtype=float)
    values[0] = math.nan
    assert math.isnan(runner.rankic(values, np.arange(100)))
    assert math.isnan(runner.rankic(np.arange(99), np.arange(99)))


def test_stationary_bootstrap_order_and_holm_are_exactly_registered() -> None:
    contrasts = {
        "P1": np.asarray([0.1, 0.2, -0.1, 0.3]),
        "P2": np.asarray([0.05, 0.1, 0.0, 0.2]),
    }
    first = runner.paired_bootstrap_diagnostics(
        contrasts, seed=20260715, repetitions=100
    )
    second = runner.paired_bootstrap_diagnostics(
        contrasts, seed=20260715, repetitions=100
    )
    assert first == second
    assert [row["contrast_id"] for row in first] == ["P1", "P2"]
    assert all(0 < row["one_sided_p_value"] <= 1 for row in first)
    assert all(row["holm_adjusted_p_value"] >= row["one_sided_p_value"] for row in first)


def test_top30_score_tie_break_is_instrument_ascending() -> None:
    frame = pd.DataFrame(
        {
            "instrument": [f"S{index:03d}" for index in range(100)],
            "score": [1.0] * 31 + [0.0] * 69,
            "label": np.arange(100, dtype=float) / 100,
        }
    )
    observed = runner.top30_daily(frame)
    selected = json.loads(observed["topk_instrument_list_json"])
    assert selected == [f"S{index:03d}" for index in range(30)]
    assert observed["topk_n"] == 30


def test_direction_gate_checks_every_boundary() -> None:
    dates = {}
    for month in range(7, 13):
        for day in range(1, 15):
            dates[f"2023-{month:02d}-{day:02d}"] = 0.01
    by_seed = {
        runner.MODEL_SEEDS[0]: [0.01] * len(dates),
        runner.MODEL_SEEDS[1]: [0.02] * len(dates),
        runner.MODEL_SEEDS[2]: [-0.001] * len(dates),
    }
    passed = runner.direction_stability(
        by_seed,
        dates,
        validation_full_complete_day_n=200,
        validation_early_complete_day_n=116,
        validation_late_score_coverage=1.0,
    )
    assert passed["status"] == "pass"
    failed = runner.direction_stability(
        by_seed,
        dates,
        validation_full_complete_day_n=199,
        validation_early_complete_day_n=116,
        validation_late_score_coverage=1.0,
    )
    assert failed["status"] == "fail"


def passing_gate_map() -> dict[str, str]:
    return {
        gate: "pass"
        for gate in runner.CAUSAL_GATES + ["output_manifest_hash_gate"]
    }


@pytest.mark.parametrize(
    ("failed_gate", "expected_state"),
    [
        (
            "execution_authorization_gate",
            "21C_FULL_blocked_by_missing_or_invalid_human_authorization",
        ),
        (
            "upstream_21b_contract_erratum_gate",
            "21C_FULL_blocked_by_upstream_contract_or_runtime",
        ),
        (
            "historical_holdout_zero_access_gate",
            "21C_FULL_input_or_access_firewall_blocked",
        ),
        (
            "teacher_isolation_gate",
            "21C_FULL_teacher_or_architecture_pipeline_not_evaluable",
        ),
        (
            "late_readout_process_gate",
            "21C_FULL_training_or_late_readout_not_evaluable",
        ),
        (
            "finalize_transaction_gate",
            "21C_FULL_finalize_or_manifest_integrity_blocked",
        ),
    ],
)
def test_decision_first_match_profiles(
    failed_gate: str, expected_state: str
) -> None:
    gates = passing_gate_map()
    index = runner.CAUSAL_GATES.index(failed_gate)
    gates[failed_gate] = "fail"
    for gate in runner.CAUSAL_GATES[index + 1 :]:
        gates[gate] = "not_run"
    if failed_gate != "finalize_transaction_gate":
        gates["output_manifest_hash_gate"] = "not_run"
    assert runner.classify_decision(gates) == expected_state


def test_not_run_cannot_mask_or_precede_actual_failure() -> None:
    gates = passing_gate_map()
    gates["scope_restart_gate"] = "not_run"
    with pytest.raises(runner.ContractError, match="illegal not_run"):
        runner.classify_decision(gates)


def test_terminal_decisions_are_validation_only() -> None:
    gates = passing_gate_map()
    assert runner.classify_decision(
        gates, relative_advantage_point_ordering_observed=False
    ) == "21C_FULL_r2_direction_supported_without_local_baseline_ordering"
    assert runner.classify_decision(
        gates, relative_advantage_point_ordering_observed=True
    ) == "21C_FULL_local_validation_point_ordering_observed"


def test_artifact_profile_universe_and_p5_are_exact() -> None:
    profiles = runner.expanded_artifact_profiles()
    assert [row["profile_id"] for row in profiles] == [
        "P0_PREFLIGHT_BLOCKED",
        "P1_MATERIALIZATION_BLOCKED",
        "P2_TRAINING_BLOCKED",
        "P3_LATE_READOUT_BLOCKED",
        "P4_FINALIZE_BLOCKED",
        "P5_FULL_FINALIZED",
    ]
    universe = set(profiles[0]["required_paths"]) | set(
        profiles[0]["forbidden_paths"]
    )
    assert len(universe) == 48
    for profile in profiles:
        required = set(profile["required_paths"])
        forbidden = set(profile["forbidden_paths"])
        assert required.isdisjoint(forbidden)
        assert required | forbidden == universe
    assert not any("failure_evidence" in path for path in profiles[-1]["required_paths"])


def test_cli_defaults_to_full_authorized_stage_chain() -> None:
    args = runner.parse_args([])
    assert args.stage == "all"
    assert args.worker is None
