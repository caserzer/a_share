from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7e_defense_participation_frontier.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7e_defense_participation_frontier", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def base_config() -> dict:
    return {
        "history_policy": {
            "history_policy_id": "board_then_global_rolling_504_sessions",
            "history_window_mode": "rolling_sessions",
            "trailing_history_window_sessions": 504,
        },
        "history_min_n": {
            "stage_2_global_min_history_n": 1,
            "stage_2_board_min_history_n": 1,
        },
        "stage2": {"x": 0.5},
        "random_baseline": {"min_random_seed_n": 1},
        "frontier": {
            "fast_fail_improvement_min_vs_x100": 0.02,
            "stage2_selected_n_min": 1,
            "stage2_selected_positive_n_min": 1,
            "chained_survivor_share_guard_threshold": 0.50,
            "survivor_share_material_lift_min": 0.10,
            "positive_capture_material_lift_min": 0.05,
            "budget_drift_tolerance": 0.02,
        },
    }


def frontier_frame(preferred_x: float | None = None, wider_material: bool = False) -> pd.DataFrame:
    rows = []
    for split in ["train", "validation", "robustness"]:
        for x in [0.2, 0.3, 0.4, 1.0]:
            share = 0.30
            capture = 0.30
            if x == 0.4 and wider_material:
                share = 0.45
                capture = 0.38
            rows.append(
                {
                    "split": split,
                    "stage1_X": x,
                    "stage1_fast_fail_rate": 0.18 if x <= 0.3 else 0.22,
                    "stage1_delta_vs_random_p50_ci95_high": -0.01,
                    "chained_survivor_share_of_ground_truth": share,
                    "continuation_positive_capture_rate": capture,
                    "stage2_selected_positive_capture_rate": 0.04,
                    "nominal_barrier_expectancy_proxy": 0.01 + (0.01 if x == preferred_x and split == "train" else 0.0),
                    "frontier_rank_by_proxy": 1 if x == preferred_x else 2,
                }
            )
    return pd.DataFrame(rows)


def selection_audit(preferred_x: float | None) -> pd.DataFrame:
    if preferred_x is None:
        return pd.DataFrame(
            [
                {
                    "stage1_X": 0.3,
                    "selected_flag": False,
                    "robustness_frontier_rank_for_selected_X": pd.NA,
                }
            ]
        )
    return pd.DataFrame(
        [
            {
                "stage1_X": preferred_x,
                "selected_flag": True,
                "robustness_frontier_rank_for_selected_X": 1,
            }
        ]
    )


def test_stage1_x100_keeps_all_stage1_evaluable_rows():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "stage_1_evaluable": [True, True, False],
            "stage1_anchor_rank_status": ["rank_not_evaluable", "rank_evaluable", "rank_evaluable"],
            "stage1_anchor_rank_percentile": [pd.NA, 0.9, 0.1],
        }
    )

    mask = runner.stage1_selected_mask(frame, 1.0)

    assert mask.tolist() == [True, True, False]


def test_stage2_rank_history_is_recomputed_inside_each_x_denominator():
    runner = load_runner()
    config = base_config()
    frame = pd.DataFrame(
        {
            "meta_event_id": ["a", "b", "c", "d"],
            "instrument": ["S1"] * 4,
            "split": ["train"] * 4,
            "board_bucket": ["main"] * 4,
            "calendar_month": ["2020-01"] * 4,
            "calendar_quarter": ["2020Q1"] * 4,
            "stage_2_decision_pos": [1, 2, 3, 4],
            "stage2_continuation_score": [0.1, 0.2, 0.3, 0.4],
            "stage_2_continuation_target": [False, False, True, True],
        }
    )
    narrow = frame.iloc[[2, 3]].copy()
    wide = frame.copy()

    ranked_narrow = runner.rank_stage2_for_x(narrow, 0.5, config, "anchor")
    ranked_wide = runner.rank_stage2_for_x(wide, 1.0, config, "anchor")

    assert set(ranked_narrow["meta_event_id"]) == {"c", "d"}
    assert len(ranked_wide) == 4


def test_train_selection_does_not_hard_gate_low_survivor_share():
    runner = load_runner()
    config = base_config()
    frontier = pd.DataFrame(
        [
            {
                "split": "train",
                "stage1_X": 0.3,
                "frontier_readout_status": "ok",
                "stage1_random_valid_seed_n": 1,
                "stage1_delta_vs_random_p50_ci95_high": -0.01,
                "stage1_fast_fail_rate": 0.10,
                "chained_survivor_share_of_ground_truth": 0.20,
                "continuation_positive_capture_rate": 0.20,
                "stage2_selected_n": 5,
                "stage2_selected_continuation_positive_n": 2,
                "nominal_barrier_expectancy_proxy": 0.01,
                "frontier_rank_by_proxy": 1,
                "chained_survivor_share_guard_status": "below_diagnostic_threshold",
            },
            {
                "split": "train",
                "stage1_X": 1.0,
                "frontier_readout_status": "ok",
                "stage1_random_valid_seed_n": 1,
                "stage1_delta_vs_random_p50_ci95_high": -0.01,
                "stage1_fast_fail_rate": 0.20,
                "chained_survivor_share_of_ground_truth": 1.0,
                "continuation_positive_capture_rate": 1.0,
                "stage2_selected_n": 5,
                "stage2_selected_continuation_positive_n": 2,
                "nominal_barrier_expectancy_proxy": 0.0,
                "frontier_rank_by_proxy": 2,
                "chained_survivor_share_guard_status": "pass",
            },
        ]
    )

    audit = runner.train_selection_audit(frontier, config)
    row = audit.loc[audit["stage1_X"].eq(0.3)].iloc[0]

    assert row["train_eligible_flag"]
    assert row["chained_survivor_share_guard_status"] == "below_diagnostic_threshold"


def test_decision_map_distinguishes_x030_confirmed_from_x030_objective_conflict():
    runner = load_runner()
    config = base_config()
    identity = {"candidate_id": "complex_stage2_score", "candidate_family": "complex_stage2_score", "stage2_budget_X": 0.3}

    confirmed = runner.decision_from_frontier(
        frontier_frame(preferred_x=0.3, wider_material=False),
        selection_audit(0.3),
        "pass",
        "pass",
        "pass",
        identity,
        config,
    )
    conflict = runner.decision_from_frontier(
        frontier_frame(preferred_x=0.3, wider_material=True),
        selection_audit(0.3),
        "pass",
        "pass",
        "pass",
        identity,
        config,
    )

    assert confirmed.iloc[0]["decision_state"] == "12A7e_x030_frontier_preferred_confirmed"
    assert conflict.iloc[0]["decision_state"] == "12A7e_x030_defense_optimal_for_downside_not_winner"


def test_decision_map_handles_preferred_tighter_than_x030():
    runner = load_runner()
    config = base_config()
    identity = {"candidate_id": "complex_stage2_score", "candidate_family": "complex_stage2_score", "stage2_budget_X": 0.3}

    decision = runner.decision_from_frontier(
        frontier_frame(preferred_x=0.2, wider_material=False),
        selection_audit(0.2),
        "pass",
        "pass",
        "pass",
        identity,
        config,
    )

    assert decision.iloc[0]["decision_state"] == "12A7e_tighter_stage1_frontier_preferred_for_downside_defense"
