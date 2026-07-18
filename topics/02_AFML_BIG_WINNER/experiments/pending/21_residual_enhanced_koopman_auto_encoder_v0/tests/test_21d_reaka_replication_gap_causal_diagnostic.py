from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch


EPISODE = Path(__file__).resolve().parents[1]
RUNNER_PATH = EPISODE / "src/run_21d_reaka_replication_gap_causal_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("ep21d_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def synthetic_batch(batch: int = 2) -> tuple[torch.Tensor, ...]:
    generator = torch.Generator().manual_seed(7)
    y = torch.randn((batch, 10, 1), generator=generator)
    x = torch.randn((batch, 10, 157), generator=generator)
    forecast = torch.randn((batch,), generator=generator)
    y_teacher = torch.randn((batch, 10, 1), generator=generator)
    x_teacher = torch.randn((batch, 10, 157), generator=generator)
    uniform = torch.rand((batch, 10, 4), generator=generator)
    timestep = torch.randint(1, 21, (batch, 10), generator=generator)
    epsilon = torch.randn((batch, 10, 64), generator=generator)
    return y, x, y_teacher, x_teacher, forecast, uniform, timestep, epsilon


def test_config_freezes_seven_arms_twenty_one_jobs_and_no_holdout() -> None:
    config = runner.load_config()
    assert config["identity"]["requirement_version"] == "21D_GAP_v2"
    assert [arm["arm_id"] for arm in config["arms"]] == list(runner.ARM_IDS)
    jobs = runner.planned_jobs(config)
    assert len(jobs) == 21
    assert jobs[["arm_id", "model_seed"]].duplicated().sum() == 0
    assert jobs["attempt_n"].eq(1).all()
    assert config["execution"]["planned_sensitivity_job_n"] == 0
    assert config["execution"]["historical_holdout_readout_authorized"] is False


def test_all_upstream_pins_and_pinned_21c_implementation_match() -> None:
    config = runner.load_config()
    rows = runner.validate_upstream_pins(config)
    assert len(rows) == 11
    assert {row["overall_status"] for row in rows} == {"pass"}
    assert runner.file_sha(RUNNER_PATH.parents[0] / "run_21c_full_reaka_pit_proxy_replication.py") == config["upstream_pins"]["21c_runner"]["sha256"]


def test_authorization_is_exact_fail_closed_and_human_bound(tmp_path: Path) -> None:
    config = runner.load_config()
    assert runner.validate_authorization(config, tmp_path / "missing.json").status == "missing"
    payload = {
        "schema_version": "21D_EXECUTION_AUTHORIZATION_V2",
        "run_id": runner.RUN_ID,
        "requirement_version": runner.REQUIREMENT_VERSION,
        "approved_requirement_sha256": runner.file_sha(runner.workspace_path(config["paths"]["requirement"], must_exist=True)),
        "approved_config_sha256": runner.file_sha(runner.workspace_path(config["paths"]["config"], must_exist=True)),
        "approved_runner_sha256": runner.file_sha(runner.workspace_path(config["paths"]["runner"], must_exist=True)),
        "approved_test_sha256": runner.file_sha(Path(__file__)),
        "approved_upstream_21c_manifest_sha256": config["upstream_pins"]["21c_manifest"]["sha256"],
        "approved_upstream_21c_output_hashes_sha256": config["upstream_pins"]["21c_output_hashes"]["sha256"],
        "approved_upstream_21b_v5_manifest_sha256": config["upstream_pins"]["21b_v5_manifest"]["sha256"],
        "approved_upstream_21b_v5_output_hashes_sha256": config["upstream_pins"]["21b_v5_output_hashes"]["sha256"],
        "approved_upstream_21b_v6_manifest_sha256": config["upstream_pins"]["21b_v6_manifest"]["sha256"],
        "approved_upstream_21b_v6_output_hashes_sha256": config["upstream_pins"]["21b_v6_output_hashes"]["sha256"],
        "replay_implementation_mode": "import_pinned_21c",
        "approved_replay_compatibility_profile": "EXACT_RUNTIME_V1",
        "allowed_runtime_field_differences": [],
        "approved_dependency_lock_sha256": runner.file_sha(runner.workspace_path(config["paths"]["dependency_lock"], must_exist=True)),
        "approved_device_fingerprint_sha256": runner.current_device_fingerprint(),
        "approved_by": "human:xiaolv",
        "approved_at_utc": "2026-07-17T00:00:00Z",
    }
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert runner.validate_authorization(config, path).status == "pass"
    payload["extra"] = "forbidden"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = runner.validate_authorization(config, path)
    assert result.status == "invalid"
    assert result.errors == ("authorization_schema_exact",)


def test_retained_row_contract_matches_all_three_folds_without_feature_open() -> None:
    audit = runner.retained_universe_audit(runner.load_config())
    assert len(audit) == 1055
    summaries = audit.loc[audit["decision_date"].isna()].sort_values("fold_order")
    assert summaries["observed_row_n"].tolist() == [335393, 51932, 50167]
    assert audit.loc[audit["decision_date"].notna(), "decision_date"].nunique() == 1052
    assert audit["denominator_exact_match"].all()
    assert audit["status"].eq("pass").all()


def test_decision_cs_zscore_uses_complete_date_position_ddof1() -> None:
    dates = ["2023-01-03"] * 100 + ["2023-01-04"] * 100
    panel = np.arange(200 * 11, dtype=np.float32).reshape(200, 11)
    transformed, audit, semantic = runner.decision_cs_zscore_return_path(
        panel, dates, fold="train", include_target=True
    )
    assert transformed.dtype == np.dtype("<f4")
    assert transformed.shape == (200, 11)
    assert len(audit) == 22
    assert audit["row_n"].eq(100).all()
    for start in (0, 100):
        np.testing.assert_allclose(transformed[start : start + 100].mean(axis=0), 0.0, atol=1e-5)
        np.testing.assert_allclose(transformed[start : start + 100].std(axis=0, ddof=1), 1.0, atol=1e-5)
    assert len(semantic) == 64


def test_validation_transform_never_materializes_target_position() -> None:
    panel = np.arange(100 * 11, dtype=np.float32).reshape(100, 11)
    transformed, audit, _ = runner.decision_cs_zscore_return_path(
        panel, ["2023-07-03"] * 100, fold="validation_late", include_target=False
    )
    assert transformed.shape == (100, 10)
    assert set(audit["position"]) == set(range(10))
    assert 10 not in set(audit["position"])


def test_transform_fails_closed_for_small_or_constant_cross_section() -> None:
    with pytest.raises(runner.ContractError, match="N<100"):
        runner.decision_cs_zscore_return_path(
            np.ones((99, 11), dtype=np.float32), ["2023-01-03"] * 99,
            fold="train", include_target=True,
        )
    with pytest.raises(runner.ContractError, match="invalid std"):
        runner.decision_cs_zscore_return_path(
            np.ones((100, 11), dtype=np.float32), ["2023-01-03"] * 100,
            fold="train", include_target=True,
        )


def test_gradient_calibration_sampling_is_4x8x256_unique_and_deterministic() -> None:
    row_n = 8192
    frame = pd.DataFrame(
        {
            "decision_date": np.repeat(["2018-01-02", "2019-01-02", "2020-01-02", "2021-01-04"], 2048),
            "instrument": [f"S{index:06d}" for index in range(row_n)],
            "row_key_hash": [f"{index:064x}" for index in range(row_n)],
        }
    )
    batches_a, registry_a = runner.temporal_calibration_batches(frame, 20260713)
    batches_b, registry_b = runner.temporal_calibration_batches(frame, 20260713)
    assert len(batches_a) == 32
    assert len(np.unique(np.concatenate(batches_a))) == 8192
    assert registry_a["row_n"].eq(256).all()
    pd.testing.assert_frame_equal(registry_a, registry_b)


def test_gradient_weight_formula_clips_then_renormalizes() -> None:
    weights = runner.gradient_balance_weights({"L_rec": 1e-8, "L_koop": 1.0, "L_diff": 100.0})
    assert set(weights) == {"L_rec", "L_koop", "L_diff"}
    assert np.mean(list(weights.values())) == pytest.approx(1.0)
    assert all(value > 0 for value in weights.values())
    equal = runner.gradient_balance_weights({"L_rec": 2.0, "L_koop": 2.0, "L_diff": 2.0})
    assert equal == {"L_rec": 1.0, "L_koop": 1.0, "L_diff": 1.0}


def test_st_hard_forward_is_one_hot_and_backward_is_finite() -> None:
    logits = torch.randn((3, 10, 4), requires_grad=True)
    uniform = torch.rand((3, 10, 4))
    selector = runner.straight_through_hard_selector(logits, uniform, 0.7)
    assert torch.equal(selector.detach().sum(dim=-1), torch.ones((3, 10)))
    assert set(selector.detach().unique().tolist()) <= {0.0, 1.0}
    (selector * torch.arange(4.0)).sum().backward()
    assert logits.grad is not None and torch.isfinite(logits.grad).all()


def test_d0_generalized_loss_is_exact_pinned_21c_loss() -> None:
    arm = runner.load_config()["arms"][0]
    model = runner.build_arm_model(arm["arm_id"], runner.MODEL_SEEDS[0])
    batch = synthetic_batch()
    observed = runner.diagnostic_training_losses(
        model, arm, *batch[:5], tau=0.6, gumbel_u=batch[5],
        diffusion_timestep=batch[6], epsilon=batch[7],
    )
    expected = runner._PINNED_21C.training_losses(
        model, *batch[:5], tau=0.6, gumbel_u=batch[5],
        diffusion_timestep=batch[6], epsilon=batch[7],
    )
    for key in ("L_rec", "L_koop", "L_diff", "L_total"):
        torch.testing.assert_close(observed[key], expected[key])


def test_k2_r1_r2_parameter_sets_and_parameter_match_are_exact() -> None:
    d0 = runner.build_arm_model("D0_R2_RAW_EXACT_REPLAY", runner.MODEL_SEEDS[0])
    d5 = runner.build_arm_model("D5_K2_RAW_NO_RESIDUAL", runner.MODEL_SEEDS[0])
    d6 = runner.build_arm_model("D6_R1_RAW_MLP_RESIDUAL", runner.MODEL_SEEDS[0])
    assert len(runner.model_parameter_names(d0)) == 21
    assert len(runner.model_parameter_names(d5)) == 15
    assert len(runner.model_parameter_names(d6)) == 21
    r2_n = sum(parameter.numel() for name, parameter in d0.named_parameters() if name.startswith("denoiser_"))
    r1_n = sum(parameter.numel() for name, parameter in d6.named_parameters() if name.startswith("residual_"))
    assert r2_n == 45376
    assert r1_n == 46464
    assert r1_n / r2_n - 1 == pytest.approx(0.0239774321)


def test_shared_initialization_is_byte_equal_and_d6_extra_is_independent() -> None:
    models = [runner.build_arm_model(arm_id, runner.MODEL_SEEDS[0]) for arm_id in runner.ARM_IDS]
    reference = dict(models[0].named_parameters())
    shared_names = [name for name in runner.model_parameter_names(models[5])]
    for model in models[1:]:
        observed = dict(model.named_parameters())
        for name in shared_names:
            torch.testing.assert_close(observed[name], reference[name], rtol=0, atol=0)
    d6_again = runner.build_arm_model("D6_R1_RAW_MLP_RESIDUAL", runner.MODEL_SEEDS[0])
    for name, value in models[6].named_parameters():
        if name.startswith("residual_"):
            torch.testing.assert_close(value, dict(d6_again.named_parameters())[name], rtol=0, atol=0)


def test_draw_seed_blocks_and_prefixes_are_batch_order_independent() -> None:
    key = ("SH600004", "2023-07-03")
    seed_a = runner._PINNED_21C.row_draw_seed(
        runner._PINNED_21C.RUN_ID, runner.MODEL_SEEDS[0], *key, 255
    )
    seed_b = runner._PINNED_21C.row_draw_seed(
        runner._PINNED_21C.RUN_ID, runner.MODEL_SEEDS[0], *key, 255
    )
    assert seed_a == seed_b
    blocks = runner.draw_blocks()
    assert len(blocks) == 32
    assert [value for block in blocks for value in block] == list(range(256))
    draws = np.arange(2 * 256, dtype=np.float32).reshape(2, 256)
    prefixes = runner.prefix_means(draws)
    for prefix in (8, 32, 64, 128, 256):
        np.testing.assert_array_equal(prefixes[prefix], draws[:, :prefix].mean(axis=1))


def test_prediction_draw_and_artifact_path_closures_are_exact() -> None:
    config = runner.load_config()
    required = runner.p6_required_paths(config)
    checkpoints = [path for path in required if path.endswith("state_dict.pt")]
    shards = [path for path in required if path.startswith("diagnostics/inference_draw_scores/")]
    assert len(checkpoints) == 21
    assert len(shards) == 18
    assert config["draws"]["sample_row_n"] == 918891
    assert config["draws"]["sample_row_n"] * 256 == 235236096
    assert 52 * 51932 == 2700464
    assert 52 * 50167 == 2608684
    assert runner.DRAW_SHARD_SCHEMA.names == [
        "fold_order", "fold", "draw_identity", "model_seed", "decision_date",
        "instrument", "row_key", "draw_scores", "draw_schedule_sha256",
    ]
    assert runner.PREDICTION_SCHEMA.names == runner.PREDICTION_COLUMNS


def test_gradient_publish_schemas_and_row_closures_are_frozen() -> None:
    assert runner.GRADIENT_BATCH_SCHEMA.names == [
        "arm_order", "arm_id", "model_seed", "temporal_stratum", "batch_index",
        "row_n", "min_decision_date", "max_decision_date", "row_key_sha256",
        "sampling_contract_sha256",
    ]
    assert runner.LOSS_GRADIENT_SCHEMA.names[:7] == [
        "arm_order", "arm_id", "model_seed", "phase", "temporal_stratum",
        "batch_index", "loss_term",
    ]
    assert 4 * 3 * 32 == 384
    assert (1 + 1 + 2 + 2) * 3 * 32 * 3 * 7 == 12096


def test_profile_registry_has_exact_terminal_mapping_and_p6_failure_forbidden() -> None:
    config = runner.load_config()
    profile = runner.artifact_profile_table(config)
    assert profile["profile_id"].tolist() == [
        "P0_PREAUTHORIZATION_BLOCKED", "P1_UPSTREAM_BLOCKED",
        "P2_INFERENCE_DIAGNOSTIC_BLOCKED", "P3_TRAINING_BLOCKED",
        "P4_LATE_READOUT_BLOCKED", "P5_FINALIZE_BLOCKED",
        "P6_FULL_DIAGNOSTIC_FINALIZED",
    ]
    forbidden = json.loads(profile.iloc[-1]["forbidden_paths_json"])
    assert set(forbidden) == runner.FAILURE_PATHS
    assert config["terminal_profiles"] == {
        "1": "P0_PREAUTHORIZATION_BLOCKED", "2": "P1_UPSTREAM_BLOCKED",
        "3": "P2_INFERENCE_DIAGNOSTIC_BLOCKED", "4": "P3_TRAINING_BLOCKED",
        "5": "P4_LATE_READOUT_BLOCKED", "6": "P5_FINALIZE_BLOCKED",
        "7": "P6_FULL_DIAGNOSTIC_FINALIZED", "8": "P6_FULL_DIAGNOSTIC_FINALIZED",
        "9": "P6_FULL_DIAGNOSTIC_FINALIZED", "10": "P6_FULL_DIAGNOSTIC_FINALIZED",
    }


def test_rankic_average_rank_tie_and_stationary_bootstrap_are_deterministic() -> None:
    score = np.arange(100, dtype=np.float64)
    label = score.copy()
    label[:2] = 0.5
    observed = runner._PINNED_21C.rankic(score, label, minimum_n=100)
    manual = pd.Series(score).rank(method="average").corr(pd.Series(label).rank(method="average"))
    assert observed == pytest.approx(manual)
    first = runner.stationary_bootstrap_indices(103)
    second = runner.stationary_bootstrap_indices(103)
    np.testing.assert_array_equal(first, second)
    assert first.shape == (5000, 103)
    assert first.min() >= 0 and first.max() < 103


def test_material_improvement_is_the_registered_four_way_conjunction() -> None:
    assert runner.material_improvement_rule(0.005, 2, 0.25, 0.30, 0.30)
    assert not runner.material_improvement_rule(0.004999, 3, 1.0, 1.0, 0.0)
    assert not runner.material_improvement_rule(0.010, 1, 1.0, 1.0, 0.0)
    assert not runner.material_improvement_rule(0.010, 3, 0.2499, 1.0, 0.0)
    assert not runner.material_improvement_rule(0.010, 3, 1.0, 0.29, 0.30)


def test_streaming_semantic_frame_hash_matches_canonical_record_list() -> None:
    frame = pd.DataFrame(
        {
            "key": [2, 1],
            "value": [np.float32(0.25), np.nan],
            "date": [pd.Timestamp("2023-01-04").date(), pd.Timestamp("2023-01-03").date()],
        }
    )
    expected = runner.stable_hash(
        [
            {"key": 1, "value": None, "date": "2023-01-03"},
            {"key": 2, "value": 0.25, "date": "2023-01-04"},
        ]
    )
    assert runner.semantic_frame_hash(frame, ["key"]) == expected


def test_markdown_fences_authorization_keys_and_gate_count_are_exact() -> None:
    requirement = runner.workspace_path(runner.load_config()["paths"]["requirement"], must_exist=True).read_text(encoding="utf-8")
    assert requirement.count("```") % 2 == 0
    assert len(runner.AUTHORIZATION_KEYS) == 20
    assert len(runner.GATE_ORDER) == 29
    assert len(set(runner.GATE_ORDER)) == 29
