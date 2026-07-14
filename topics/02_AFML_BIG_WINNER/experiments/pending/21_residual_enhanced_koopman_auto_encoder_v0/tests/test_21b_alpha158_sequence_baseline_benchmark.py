from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


EPISODE = Path(__file__).resolve().parents[1]
RUNNER_PATH = EPISODE / "src/run_21b_alpha158_sequence_baseline_benchmark.py"
SPEC = importlib.util.spec_from_file_location("ep21b_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_requirement_and_authorization_are_exactly_bound() -> None:
    config = runner.load_config()
    requirement = runner.resolve_paths(config)["requirement"]
    authorization = json.loads(
        runner.resolve_paths(config)["authorization"].read_text(encoding="utf-8")
    )
    assert runner.file_sha(requirement) == config["identity"]["requirement_sha256"]
    assert authorization["requirement_sha256"] == config["identity"]["requirement_sha256"]
    assert authorization["reviewer_role"] == "human"
    assert authorization["authorization_status"] == "approved"


def test_planned_job_registry_is_exact() -> None:
    jobs = runner.planned_jobs()
    assert len(jobs) == 13
    assert sum(row["arm_id"] == runner.M0 for row in jobs) == 1
    assert {(row["arm_id"], row["model_seed"]) for row in jobs[1:]} == {
        (arm, seed) for arm in runner.LEARNED_ARMS for seed in runner.MODEL_SEEDS
    }


def test_artifact_profiles_are_ordered_and_p5_exact() -> None:
    profiles = runner.expanded_artifact_profiles()
    assert [row["profile_id"] for row in profiles] == [
        "P0_PREFLIGHT_BLOCKED",
        "P1_MATERIALIZATION_BLOCKED",
        "P2_SELECTION_BLOCKED",
        "P3_GATE_READOUT_BLOCKED",
        "P4_FINALIZE_BLOCKED",
        "P5_FULL_FINALIZED",
    ]
    p5 = profiles[-1]
    assert p5["required_paths"] == sorted(
        set(runner.ALL_STAGE_PATHS)
        - {"materialized/materialization_failure_evidence.csv", "finalize_failure_evidence.csv"}
    )
    assert p5["forbidden_paths"] == [
        "finalize_failure_evidence.csv",
        "materialized/materialization_failure_evidence.csv",
    ]


def test_m0_is_key_only_deterministic_and_order_invariant() -> None:
    keys = [("000001", "2023-01-03"), ("600000", "2023-01-04")]
    first = [runner.m0_score(*key) for key in keys]
    second = [runner.m0_score(*key) for key in reversed(keys)][::-1]
    assert first == second
    assert all(0.0 <= value < 1.0 for value in first)


def test_average_rank_uses_average_ties() -> None:
    observed = runner.average_rank(np.asarray([4.0, 1.0, 1.0, 3.0]))
    np.testing.assert_array_equal(observed, [4.0, 1.5, 1.5, 3.0])


@pytest.mark.parametrize(
    ("scores", "labels", "expected"),
    [
        ([1, 2, 3, 4], [1, 2, 3, 4], 1.0),
        ([1, 2, 3, 4], [4, 3, 2, 1], -1.0),
        ([1, 2, 3, 4], [4, 1, 3, 2], -0.4),
    ],
)
def test_rankic_fixture(scores: list[int], labels: list[int], expected: float) -> None:
    assert runner.rankic(np.asarray(scores), np.asarray(labels), minimum_n=2) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("scores", "labels"),
    [
        ([1.0], [1.0]),
        ([1.0, 1.0], [1.0, 2.0]),
        ([1.0, 2.0], [1.0, 1.0]),
        ([1.0, math.nan], [1.0, 2.0]),
    ],
)
def test_rankic_undefined_cases(scores: list[float], labels: list[float]) -> None:
    assert math.isnan(runner.rankic(np.asarray(scores), np.asarray(labels), minimum_n=2))


def test_cyclic_null_fixture_has_exact_zero_mean() -> None:
    ranks = np.arange(100, dtype=np.float64)
    values = [
        runner.rankic(ranks, np.roll(ranks, shift), minimum_n=100)
        for shift in range(100)
    ]
    assert abs(float(np.mean(values))) <= 1e-12


def test_leave_one_rankic_matches_brute_force_with_ties() -> None:
    score = np.asarray([1.0, 2.0, 2.0, 4.0, 5.0])
    label = np.asarray([5.0, 4.0, 3.0, 3.0, 1.0])
    observed = runner._leave_one_rankic_all(score, label)
    expected = []
    for index in range(len(score)):
        keep = np.arange(len(score)) != index
        expected.append(runner.rankic(score[keep], label[keep], minimum_n=2))
    np.testing.assert_allclose(observed, expected, atol=1e-15)


def test_daily_readout_rejects_partial_score_coverage() -> None:
    scores = pd.DataFrame(
        {
            "arm_id": [runner.M0] * 2,
            "score_role": ["null"] * 2,
            "model_seed": [None] * 2,
            "fold": ["validation_early"] * 2,
            "decision_date": ["2023-01-03"] * 2,
            "instrument": ["A", "B"],
            "row_key_hash": ["a", "b"],
            "score": [0.1, 0.2],
            "U_t_decision_n": [3, 3],
        }
    )
    labels = pd.DataFrame(
        {
            "decision_date": ["2023-01-03"] * 2,
            "instrument": ["A", "B"],
            "row_key_hash": ["a", "b"],
            "label_value": [0.01, 0.02],
            "U_t_resolved_n": [3, 3],
        }
    )
    result = runner.calculate_daily_readout(scores, labels).iloc[0]
    assert result["rankic_status"] == "not_evaluable"
    assert result["not_evaluable_reason"] == "incomplete_score_coverage"


@pytest.mark.parametrize(
    "arm_id",
    ["M2_RETURN_LSTM", "M3_GATED_DUAL_PATH_LSTM", "A0_VANILLA_AUTOENCODER"],
)
def test_torch_model_output_shapes(arm_id: str) -> None:
    import torch

    model = runner.build_torch_model(arm_id)
    y = torch.zeros((3, 10, 1))
    x = None if arm_id == "M2_RETURN_LSTM" else torch.zeros((3, 10, runner.FEATURE_COUNT))
    score, decoded = model(y, x)
    assert tuple(score.shape) == (3,)
    if arm_id == "A0_VANILLA_AUTOENCODER":
        assert tuple(decoded.shape) == (3, 10)
    else:
        assert decoded is None


@pytest.mark.parametrize(
    "arm_id",
    ["M2_RETURN_LSTM", "M3_GATED_DUAL_PATH_LSTM", "A0_VANILLA_AUTOENCODER"],
)
def test_initialization_and_state_hash_are_repeatable(arm_id: str) -> None:
    first = runner.build_torch_model(arm_id)
    second = runner.build_torch_model(arm_id)
    runner.initialize_torch_model(first, arm_id, runner.MODEL_SEEDS[0])
    runner.initialize_torch_model(second, arm_id, runner.MODEL_SEEDS[0])
    assert runner.model_state_semantic_hash(first.state_dict()) == runner.model_state_semantic_hash(second.state_dict())


def test_canonical_json_distinguishes_float_from_string() -> None:
    float_payload = runner.canonical_json_bytes({"value": 1.0})
    string_payload = runner.canonical_json_bytes({"value": "1.0"})
    assert float_payload != string_payload
    assert b"f64le:" in float_payload


def test_semantic_json_hash_excludes_only_registered_volatile_fields(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('{"generated_at_utc":"a","value":1}\n', encoding="utf-8")
    second.write_text('{"generated_at_utc":"b","value":1}\n', encoding="utf-8")
    assert runner._semantic_hash_file(first, "x.json") == runner._semantic_hash_file(second, "x.json")
    second.write_text('{"generated_at_utc":"b","value":2}\n', encoding="utf-8")
    assert runner._semantic_hash_file(first, "x.json") != runner._semantic_hash_file(second, "x.json")


def test_decision_schema_contains_all_causal_gates_once() -> None:
    assert len(runner.CAUSAL_GATES) == 24
    assert len(set(runner.CAUSAL_GATES)) == 24
    assert all(gate in runner.DECISION_COLUMNS for gate in runner.CAUSAL_GATES)
    assert runner.DECISION_COLUMNS.count("output_manifest_hash_gate") == 1
    assert runner.DECISION_COLUMNS.count("baseline_information_gate") == 1


def test_cli_default_is_all() -> None:
    args = runner.parse_args([])
    assert args.stage == "all"
    assert args.worker is None


def test_prediction_schema_is_exact() -> None:
    assert runner.PREDICTION_COLUMNS == [
        "run_id", "requirement_version", "split", "fold", "decision_date",
        "instrument", "arm_id", "score_role", "model_seed", "score",
        "U_t_decision_n", "row_key_hash", "feature_route_id",
        "checkpoint_sha256", "checkpoint_bundle_sha256",
    ]


def test_access_schema_is_exact() -> None:
    assert len(runner.ACCESS_COLUMNS) == 15
    assert runner.ACCESS_COLUMNS[0] == "access_seq"
    assert runner.ACCESS_COLUMNS[-1] == "purpose"


def test_daily_schema_is_exact() -> None:
    assert len(runner.DAILY_COLUMNS) == 15
    assert runner.DAILY_COLUMNS[9:13] == ["RankIC", "PearsonIC", "MSE", "MAE"]


def test_stability_schema_is_exact() -> None:
    assert len(runner.STABILITY_COLUMNS) == 17
    assert "positive_lomo_n" in runner.STABILITY_COLUMNS
    assert "max_month_abs_contribution_share" in runner.STABILITY_COLUMNS


def test_fragility_schema_is_exact() -> None:
    assert len(runner.FRAGILITY_COLUMNS) == 16
    assert runner.FRAGILITY_COLUMNS[4:6] == ["unit_type", "unit_id"]
    assert "selected_in_top_third" in runner.FRAGILITY_COLUMNS


def test_gate_schema_is_exact() -> None:
    assert runner.GATE_COLUMNS == [
        "gate_id", "check_id", "evidence_artifact", "evidence_selector",
        "observed_value", "required_value", "status", "blocking_reason",
    ]


def test_decision_schema_has_no_duplicate_columns() -> None:
    assert len(runner.DECISION_COLUMNS) == len(set(runner.DECISION_COLUMNS))
    assert runner.DECISION_COLUMNS[0:2] == ["run_id", "requirement_version"]
    assert runner.DECISION_COLUMNS[-1] == "blocking_reasons"


def test_checkpoint_path_universe_is_exact() -> None:
    paths = runner.checkpoint_paths()
    assert len(paths) == 12
    assert len(set(paths)) == 12
    assert sum(path.endswith("model.txt") for path in paths) == 3
    assert sum(path.endswith("state_dict.pt") for path in paths) == 9


def test_p2_is_only_conditional_profile() -> None:
    profiles = runner.expanded_artifact_profiles()
    conditionals = {
        row["profile_id"]: row["conditional_path_rules"] for row in profiles
    }
    assert conditionals["P2_SELECTION_BLOCKED"] == [
        "completed_learned_job_exact_checkpoint_subset"
    ]
    assert all(
        not value for key, value in conditionals.items() if key != "P2_SELECTION_BLOCKED"
    )


def test_success_profile_forbids_both_failure_evidence_files() -> None:
    p5 = runner.expanded_artifact_profiles()[-1]
    assert set(p5["forbidden_paths"]) == {
        "materialized/materialization_failure_evidence.csv",
        "finalize_failure_evidence.csv",
    }


def test_volatile_exclusions_are_narrow() -> None:
    assert runner.VOLATILE_JSON_FIELDS == {
        "generated_at_utc", "worker_pid", "started_at_utc", "ended_at_utc"
    }
    assert runner.VOLATILE_CSV_FIELDS["stage_status_registry.csv"] == {
        "started_at_utc", "ended_at_utc"
    }


def test_day_slices_require_canonical_contiguity() -> None:
    assert runner._day_slices(["a", "a", "b", "c", "c"]) == [
        ("a", 0, 2), ("b", 2, 3), ("c", 3, 5)
    ]


def test_unknown_torch_arm_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown torch arm"):
        runner.build_torch_model("UNKNOWN")


def test_m0_changes_when_either_key_component_changes() -> None:
    base = runner.m0_score("000001", "2023-01-03")
    assert base != runner.m0_score("000002", "2023-01-03")
    assert base != runner.m0_score("000001", "2023-01-04")


def test_stationary_bootstrap_is_repeatable() -> None:
    values = np.linspace(-0.1, 0.1, 30)
    first = runner._stationary_bootstrap_ci(values, 100, 5)
    second = runner._stationary_bootstrap_ci(values, 100, 5)
    assert first == second


def test_sealed_bundle_matches_p5_profile_when_present() -> None:
    root = runner.canonical_output_root(runner.load_config())
    if not root.exists():
        pytest.skip("sealed integration bundle not present")
    manifest = json.loads(
        (root / "manifest_21b_alpha158_sequence_baseline_benchmark.json").read_text()
    )
    observed = sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    )
    assert manifest["artifact_profile_id"] == "P5_FULL_FINALIZED"
    assert observed == sorted(manifest["artifact_file_set"])


def test_sealed_decision_keeps_execution_boundaries_when_present() -> None:
    root = runner.canonical_output_root(runner.load_config())
    if not root.exists():
        pytest.skip("sealed integration bundle not present")
    decision = pd.read_csv(root / "21B_baseline_benchmark_decision.csv").iloc[0]
    assert bool(decision["next_requirement_execution_authorized"]) is False
    assert bool(decision["historical_holdout_readout_authorized"]) is False
    assert bool(decision["deployment_authorized"]) is False


def test_sealed_holdout_counts_are_zero_when_present() -> None:
    root = runner.canonical_output_root(runner.load_config())
    if not root.exists():
        pytest.skip("sealed integration bundle not present")
    row = pd.read_csv(root / "historical_design_holdout_access_audit.csv").iloc[0]
    for column in [
        "outcome_value_row_read_count", "label_read_count",
        "score_outcome_join_count", "metric_read_count",
    ]:
        assert int(row[column]) == 0


def test_sealed_gate_registry_is_complete_when_present() -> None:
    root = runner.canonical_output_root(runner.load_config())
    if not root.exists():
        pytest.skip("sealed integration bundle not present")
    gates = pd.read_csv(root / "gate_evidence_21b.csv")
    assert len(gates) == 26
    assert set(runner.CAUSAL_GATES).issubset(set(gates["gate_id"]))
    assert set(gates["status"]) == {"pass"}
