from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = EXPERIMENT_DIR / "src"

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import run_10c_false_repair_rejector as rejector  # noqa: E402


def minimal_config() -> dict:
    return {
        "run": {
            "target_label_column": "frozen_false_repair_20d_label",
            "random_seed": 20260615,
        },
        "utility": {
            "false_repair_capture_weight": 1.0,
            "exposure_days_reduction_weight": 0.5,
            "winner_injury_excess_weight": 10.0,
            "e1_missed_injury_excess_weight": 5.0,
            "bridge_injury_excess_weight": 2.0,
            "wrong_kill_rate_cap": 0.15,
            "e1_missed_wrong_kill_rate_cap": 0.15,
            "bridge_wrong_kill_rate_cap": 0.15,
            "winner_retention_floor": 0.85,
            "e1_missed_retention_floor": 0.85,
            "bridge_retention_floor": 0.85,
        },
        "diagnostics": {
            "bridge_membership_missing_rate_cap_for_binding_gate": 0.5,
            "bridge_winner_min_for_binding_gate": 100,
        },
    }


def test_binding_canonical_event_id_uses_input_event_key_not_feature_join_key() -> None:
    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample_a",
                "selected_target_id": "target_a",
                "input_denominator_id": "risk_on_r_core_horizon_complete",
                "input_event_key": "sample_a|target_a|risk_on_r_core_horizon_complete|canonical_a",
                "feature_matrix_join_key": {"logical": "tuple_not_pipe_string"},
            }
        ]
    )

    out = rejector.derive_binding_canonical_event_id(frame)

    assert out.loc[0, "binding_canonical_event_id"] == "canonical_a"
    assert out.loc[0, "binding_key_status"] == "pass"


def test_10b_selected_gate_is_manifest_authoritative_and_expected_checked() -> None:
    manifest = {
        "selected_model_id": "regularized_logistic_fast_fail_10d_l2_v1",
        "selected_population_id": "10A__same_instrument_cooldown_10d",
        "selected_denominator_id": "post_dedup_risk_on_r_core",
        "selected_capacity_id": "keep_9300",
        "selected_threshold_id": "keep_9300",
        "selected_operating_point": {"ablation_id": "full", "reject_fraction": 0.07},
    }
    config = {
        "cascade": {
            "expected_10b_model_id": "regularized_logistic_fast_fail_10d_l2_v1",
            "expected_10b_ablation_id": "full",
            "expected_10b_capacity_id": "keep_9400",
            "expected_10b_threshold_id": "keep_9400",
            "expected_10b_reject_fraction": 0.06,
        }
    }

    gate = rejector.selected_10b_gate(manifest, config)

    assert gate["capacity_id"] == "keep_9300"
    assert gate["match_flag"] is False


def test_10b_inputs_are_supported_only_not_hard_required(tmp_path: Path) -> None:
    paths = {
        "upstream_10b_manifest": tmp_path / "missing_10b_manifest.json",
        "upstream_10b_scores": tmp_path / "missing_10b_scores.parquet",
        "upstream_10a_manifest": tmp_path / "missing_10a_manifest.json",
    }

    audit = rejector.input_audit(paths, expected={})

    tenb_rows = audit.loc[audit["artifact_id"].isin({"upstream_10b_manifest", "upstream_10b_scores"})]
    assert set(tenb_rows["required_flag"]) == {False}
    assert set(tenb_rows["schema_status"]) == {"supported_only_missing"}
    assert rejector.hard_input_failures(audit) == ["upstream_10a_manifest:missing_required"]
    assert sorted(rejector.supported_only_input_failures(audit)) == [
        "upstream_10b_manifest:supported_only_missing",
        "upstream_10b_scores:supported_only_missing",
    ]


def test_source_caveat_is_inferred_from_08_10a_10b_manifests() -> None:
    manifest_08 = {"decision": "risk_on_transition_source_caveated_readout"}
    manifest_10a = {"statuses": {"source_caveated": False}}
    manifest_10b = {"source_caveated": False}

    assert rejector.upstream_source_caveated(manifest_08, manifest_10a, manifest_10b) is True


def test_missing_10b_scores_make_cascade_unavailable_not_input_blocked() -> None:
    score_long = pd.DataFrame(
        {
            "input_event_key": ["k1"],
            "sample_id": ["s1"],
            "selected_target_id": ["t1"],
            "binding_canonical_event_id": ["e1"],
            "split": ["train"],
            "candidate_rejected_flag": [True],
        }
    )
    gate = {
        "available_flag": True,
        "model_id": "m",
        "ablation_id": "full",
        "population_id": "p",
        "denominator_id": "d",
        "capacity_id": "keep",
        "threshold_id": "keep",
    }

    merged, failures = rejector.merge_10b_flags(score_long, None, gate)

    assert failures == ["10B_scores_missing_supported_only"]
    assert bool(merged.loc[0, "fast_fail_rejected_flag"]) is False
    assert merged.loc[0, "cascade_bucket"] == "10B_unavailable"


def test_feature_source_signal_requires_positive_exposure_lift() -> None:
    config = {"run": {"fit_split": "train"}}
    frontier = pd.DataFrame(
        {
            "train_false_repair_capture_lift_vs_random": [0.10, 0.10],
            "train_exposure_days_lift_vs_random": [0.00, -0.01],
            "train_selection_utility": [0.05, 0.05],
        }
    )

    assert rejector.has_positive_train_feature_source_signal(frontier, config) is False
    frontier.loc[0, "train_exposure_days_lift_vs_random"] = 0.01
    assert rejector.has_positive_train_feature_source_signal(frontier, config) is True


def test_exposure_days_lift_vs_random_is_computed_from_reduction_gap() -> None:
    part = pd.DataFrame(
        {
            "population_id": ["p"] * 4,
            "denominator_id": ["d"] * 4,
            "split": ["train"] * 4,
            "frozen_false_repair_20d_label": [True, True, True, False],
            "false_repair_non_winner_flag": [True, True, False, False],
            "winner_120": [False, False, True, False],
            "E1_missed_winner_flag": [False, False, True, False],
            "bridge_positive_flag": [False, False, False, False],
            "bridge_membership_missing_flag": [False, False, False, False],
            "active_interval_calendar_day_n": [10, 10, 10, 10],
        }
    )
    candidate_rejected = pd.Series([True, False, False, False], index=part.index)
    random_rejected = pd.Series([False, True, False, False], index=part.index)

    metrics, exposure, _retention, _aux = rejector.compute_split_capacity_metrics(
        part,
        candidate_rejected,
        random_rejected,
        "m",
        "full",
        "keep_x",
        "keep_x",
        0.25,
        {("train", "keep_x"): {"false_repair_ml_supported_gate_allowed": True}},
        minimal_config(),
    )

    assert exposure["false_repair_non_winner_exposure_days_reduction"] == 0.5
    assert exposure["random_false_repair_non_winner_exposure_days_reduction"] == 0.5
    assert exposure["exposure_days_lift_vs_random"] == 0.0
    assert metrics["false_repair_capture_lift_vs_random"] == 0.0
