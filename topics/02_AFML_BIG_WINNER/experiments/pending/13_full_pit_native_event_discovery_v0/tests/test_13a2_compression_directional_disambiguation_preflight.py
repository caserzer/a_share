from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13a2_compression_directional_disambiguation_preflight.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_13a2_compression_directional_disambiguation_preflight", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_distance_to_high_is_contract_direction_and_close_position_is_derived():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "distance_to_20d_high": [-0.20],
            "distance_to_20d_low": [0.25],
        }
    )

    out, availability = runner.derive_directional_features(panel)

    assert round(float(out.loc[0, "distance_to_20d_high"]), 6) == 0.25
    assert round(float(out.loc[0, "distance_from_20d_low"]), 6) == 0.25
    assert 0.0 <= float(out.loc[0, "close_position_20d"]) <= 1.0
    assert "close_position_20d" in availability["primitive_id"].tolist()


def test_threshold_freeze_uses_train_base_only_not_validation_outcome():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "split": ["train", "train", "train", "validation"],
            "ret_20d": [0.01, 0.02, 0.03, 10.0],
            "native_scope": [True, True, True, True],
            "volatility_20d": [0.01, 0.01, 0.01, 0.01],
        }
    )
    base_mask = panel["native_scope"]
    config = {"directional_filters": {"quantile_rules": [{"threshold_rule": "top_50pct", "quantile": 0.5}]}}
    availability = pd.DataFrame(
        [
            {
                "primitive_id": "ret_20d",
                "filter_family_id": "relative_strength",
                "raw_feature_formula": "ret_20d",
                "bullish_score_formula": "ret_20d",
                "feature_availability_status": "available",
            }
        ]
    )

    frozen = runner.freeze_thresholds(panel, base_mask, config, availability)

    assert float(frozen.iloc[0]["threshold_value"]) == 0.02
    assert frozen.iloc[0]["threshold_source_split"] == "train"
    assert frozen.iloc[0]["threshold_source_scope"] == "base_compression_cohort"


def test_directional_match_deciles_exclude_candidate_families():
    runner = load_runner()
    availability = pd.DataFrame(
        {
            "primitive_id": ["stock_vs_board_20d", "close_position_20d", "max_drawdown_20d", "turnover_zscore_20d"],
            "feature_availability_status": ["available", "available", "available", "available"],
        }
    )
    candidate = pd.Series(
        {
            "primitive_id_1": "stock_vs_board_20d",
            "primitive_id_2": "close_position_20d",
        }
    )

    included = runner.included_directional_deciles(candidate, availability)
    excluded = runner.excluded_match_deciles(candidate)

    assert "stock_vs_board_20d_directional_decile" not in included
    assert "close_position_20d_directional_decile" not in included
    assert "max_drawdown_20d_directional_decile" in included
    assert "turnover_zscore_20d_directional_decile" in included
    assert "stock_vs_board_20d_directional_decile" in excluded
    assert "close_position_20d_directional_decile" in excluded


def test_no_selected_filter_is_local_compression_route_not_global_episode_stop():
    runner = load_runner()
    decision = runner.decision_row(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        pd.DataFrame({"filter_id": ["x"], "candidate_grid_status": ["pass"]}),
        None,
        {
            "winner_uplift_gate_status": "fail",
            "direction_readout_gate_status": "fail",
            "control_quality_gate_status": "not_applicable_no_selected_filter",
            "badside_utility_gate_status": "fail",
            "morphology_gate_status": "not_applicable_no_selected_filter",
            "morphology_independent_evidence_gate_status": "not_applicable_no_selected_filter",
            "stability_gate_status": "not_applicable_no_selected_filter",
            "search_control_gate_status": "not_applicable_no_selected_filter",
            "deployability_gate_status": "not_applicable_no_selected_filter",
        },
        pd.DataFrame(),
    )

    row = decision.iloc[0]
    assert row["decision_state"] == "13A2_no_directional_filter_survives_stop_event_mining"
    assert row["scope_boundary"] == "failure_only_rejects_compression_conditional_directional_route_not_full_episode_13"
    assert row["next_allowed_requirement"] == "none"
