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

import run_fast_fail_structural_gate as gate  # noqa: E402


def test_binding_canonical_event_id_is_parsed_from_input_event_key() -> None:
    frame = pd.DataFrame(
        [
            {
                "sample_id": "sample_a",
                "selected_target_id": "target_a",
                "input_denominator_id": "risk_on_r_core_horizon_complete",
                "input_event_key": "sample_a|target_a|risk_on_r_core_horizon_complete|canonical_42",
            }
        ]
    )

    out = gate.derive_binding_canonical_event_id(frame)

    assert out.loc[0, "binding_canonical_event_id"] == "canonical_42"
    assert out.loc[0, "binding_key_status"] == "pass"


def test_constrained_utility_uses_configured_weights() -> None:
    row = {
        "capacity_matched_capture_lift_over_rule_baseline": 0.08,
        "capacity_matched_capture_lift_over_random": 0.04,
        "wrong_kill_rate": 0.08,
        "candidate_accepted_mean_MAE_10": 0.35,
        "rule_baseline_accepted_mean_MAE_10": 0.30,
        "random_baseline_accepted_mean_MAE_10": 0.32,
        "rolling_10d_executable_event_day_density": 0.12,
        "rolling_20d_executable_event_day_density": 0.11,
    }
    weights = {
        "random_lift_weight": 0.5,
        "winner_injury_excess_weight": 10.0,
        "mae_worse_excess_weight": 1.0,
        "density_excess_weight": 100.0,
    }
    gates = {
        "wrong_kill_rate_cap": 0.06,
        "rolling_10d_density_cap": 0.10,
        "rolling_20d_density_cap": 0.10,
    }

    out = gate.compute_constrained_utility(row, weights, gates)

    assert round(out["fast_fail_benefit"], 6) == 0.10
    assert round(out["winner_injury_excess"], 6) == 0.02
    assert round(out["mae_worse_excess"], 6) == 0.05
    assert round(out["density_excess"], 6) == 0.03
    assert round(out["train_constrained_utility"], 6) == -3.15


def test_select_operating_point_is_train_only_and_capacity_gated() -> None:
    frontier = pd.DataFrame(
        [
            {
                "model_id": "regularized_logistic_fast_fail_10d_l2_v1",
                "ablation_id": "full",
                "split": "train",
                "capacity_id": "keep_9250",
                "train_constrained_utility": 0.20,
                "capacity_matched_capture_lift_over_rule_baseline": 0.03,
                "capacity_matched_capture_lift_over_random": 0.03,
                "winner_retention": 0.96,
                "reject_fraction": 0.075,
            },
            {
                "model_id": "regularized_logistic_fast_fail_10d_l2_v1",
                "ablation_id": "full",
                "split": "train",
                "capacity_id": "keep_9300",
                "train_constrained_utility": 0.50,
                "capacity_matched_capture_lift_over_rule_baseline": 0.01,
                "capacity_matched_capture_lift_over_random": 0.01,
                "winner_retention": 0.99,
                "reject_fraction": 0.070,
            },
            {
                "model_id": "regularized_logistic_fast_fail_10d_l2_v1",
                "ablation_id": "full",
                "split": "validation",
                "capacity_id": "keep_9400",
                "train_constrained_utility": 2.00,
                "capacity_matched_capture_lift_over_rule_baseline": 0.30,
                "capacity_matched_capture_lift_over_random": 0.30,
                "winner_retention": 0.99,
                "reject_fraction": 0.060,
            },
        ]
    )
    power_gate = pd.DataFrame(
        [
            {"split": "train", "capacity_id": "keep_9250", "tenb_supported_row_allowed": True},
            {"split": "train", "capacity_id": "keep_9300", "tenb_supported_row_allowed": False},
            {"split": "validation", "capacity_id": "keep_9400", "tenb_supported_row_allowed": True},
        ]
    )
    config = {
        "defaults": {
            "fit_split": "train",
            "selected_model_id": "regularized_logistic_fast_fail_10d_l2_v1",
            "selectable_capacity_ids": ["keep_9250", "keep_9300", "keep_9400"],
        }
    }

    selected = gate.select_operating_point(frontier, power_gate, config)

    assert selected["selected"]
    assert selected["capacity_id"] == "keep_9250"


def test_supported_pass_blocks_winner_injury() -> None:
    selected = {
        "selected": True,
        "capacity_matched_capture_lift_over_rule_baseline": 0.05,
        "capacity_matched_capture_lift_over_random": 0.05,
        "accepted_MAE_10_improves": True,
        "winner_retention": 0.90,
        "wrong_kill_rate": 0.10,
        "density_excess": 0.0,
        "train_constrained_utility": 0.10,
        "oos_threshold_instability": 0.0,
        "supported_constrained_utility": 0.10,
    }
    config = {
        "gates": {
            "capture_lift_margin": 0.02,
            "winner_retention_floor": 0.94,
            "wrong_kill_rate_cap": 0.06,
        }
    }

    passed, reasons = gate.supported_pass(selected, config)

    assert not passed
    assert "winner_retention_below_floor" in reasons
    assert "wrong_kill_rate_above_cap" in reasons


def test_supported_pass_fail_closed_on_nonfinite_metric() -> None:
    selected = {
        "selected": True,
        "capacity_matched_capture_lift_over_rule_baseline": float("nan"),
        "capacity_matched_capture_lift_over_random": 0.05,
        "accepted_MAE_10_improves": True,
        "winner_retention": 0.95,
        "wrong_kill_rate": 0.05,
        "density_excess": 0.0,
        "train_constrained_utility": 0.10,
        "oos_threshold_instability": 0.0,
        "supported_constrained_utility": 0.10,
    }
    config = {
        "gates": {
            "capture_lift_margin": 0.02,
            "winner_retention_floor": 0.94,
            "wrong_kill_rate_cap": 0.06,
        }
    }

    passed, reasons = gate.supported_pass(selected, config)

    assert not passed
    assert reasons == ["capacity_matched_capture_lift_over_rule_baseline_nonfinite"]


def test_ablation_drop_columns_uses_non_none_overlap_policy() -> None:
    feature_cols = ["fs2_feature", "direct_overlap_feature", "clean_feature"]
    contract = pd.DataFrame(
        [
            {
                "feature_id": "fs2_feature",
                "feature_family": "FS2_basis_path_quality",
                "label_mechanism_overlap_type": "none",
            },
            {
                "feature_id": "direct_overlap_feature",
                "feature_family": "FS1_event_intrinsic",
                "label_mechanism_overlap_type": "direct",
            },
            {
                "feature_id": "clean_feature",
                "feature_family": "FS1_event_intrinsic",
                "label_mechanism_overlap_type": "none",
            },
        ]
    )
    config = {
        "ablation": {
            "drop_feature_families": ["FS2_basis_path_quality", "FS3_vol_range_stop_distance"],
            "drop_overlap_policy": "non_none",
            "drop_overlap_types": ["related"],
        }
    }

    dropped = gate.ablation_drop_columns(feature_cols, contract, config)

    assert dropped == ["fs2_feature", "direct_overlap_feature"]


def test_ablation_readout_reports_feature_removal_not_constant_drop() -> None:
    frontier = pd.DataFrame(
        [
            {
                "model_id": "m",
                "ablation_id": "full",
                "split": "train",
                "capacity_id": "keep_9400",
                "candidate_capture_rate": 0.2,
                "capacity_matched_capture_lift_over_rule_baseline": 0.1,
                "capacity_matched_capture_lift_over_random": 0.1,
                "winner_retention": 0.95,
                "wrong_kill_rate": 0.05,
                "accepted_MAE_10_improves": True,
            },
            {
                "model_id": "m",
                "ablation_id": "drop_fs2_fs3_mechanism_overlap",
                "split": "train",
                "capacity_id": "keep_9400",
                "candidate_capture_rate": 0.18,
                "capacity_matched_capture_lift_over_rule_baseline": 0.08,
                "capacity_matched_capture_lift_over_random": 0.08,
                "winner_retention": 0.96,
                "wrong_kill_rate": 0.04,
                "accepted_MAE_10_improves": True,
            },
        ]
    )
    registry = pd.DataFrame(
        [
            {"model_id": "m", "ablation_id": "full", "feature_n_input": 48, "feature_n_used": 46},
            {
                "model_id": "m",
                "ablation_id": "drop_fs2_fs3_mechanism_overlap",
                "feature_n_input": 27,
                "feature_n_used": 25,
            },
        ]
    )
    selected = {"selected": True, "capacity_id": "keep_9400", "split": "train"}

    out = gate.build_ablation_readout(
        frontier,
        registry,
        selected,
        {"full": 0, "drop_fs2_fs3_mechanism_overlap": 21},
    )

    full = out.loc[out["ablation_id"] == "full"].iloc[0]
    ablation = out.loc[out["ablation_id"] == "drop_fs2_fs3_mechanism_overlap"].iloc[0]
    assert int(full["dropped_feature_n"]) == 0
    assert int(full["retained_feature_n"]) == 48
    assert full["ablation_status"] == "reference"
    assert int(ablation["dropped_feature_n"]) == 21
    assert int(ablation["retained_feature_n"]) == 27
    assert ablation["ablation_status"] == "pass"


def test_pre_dedup_only_requires_explicit_config_flag(tmp_path: Path) -> None:
    paths = {"upstream_09c_event_scores": tmp_path / "event_scores.csv.gz"}
    paths["upstream_09c_event_scores"].write_text("score\n", encoding="utf-8")
    failures = ["upstream_10a_event_bindings:missing_required"]

    disabled = {"diagnostics": {"enable_pre_dedup_replay_without_10a_cache": False}}
    enabled = {"diagnostics": {"enable_pre_dedup_replay_without_10a_cache": True}}

    assert not gate.can_run_pre_dedup_only(disabled, paths, failures)
    assert gate.can_run_pre_dedup_only(enabled, paths, failures)
    assert not gate.can_run_pre_dedup_only(
        enabled,
        paths,
        failures + ["upstream_09b_feature_matrix:missing_required"],
    )
