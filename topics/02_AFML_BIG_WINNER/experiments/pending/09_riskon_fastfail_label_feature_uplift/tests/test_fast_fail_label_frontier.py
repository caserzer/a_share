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

import run_fast_fail_label_frontier as frontier  # noqa: E402


def test_winner_censoring_status_maps_upstream_status() -> None:
    assert frontier.map_winner_censoring_status("not_missing") == "complete"
    assert (
        frontier.map_winner_censoring_status("censored_incomplete_horizon")
        == "incomplete_120d"
    )
    assert frontier.map_winner_censoring_status("non_executable_next_open") == "non_executable"
    assert frontier.map_winner_censoring_status(None) == "not_evaluable"


def test_sample_id_prefers_canonical_event_id() -> None:
    frame = pd.DataFrame(
        [
            {
                "canonical_event_id": "canon_a",
                "instrument": "SH600000",
                "event_t0_date": "2024-01-01",
                "trade_open_date": "2024-01-02",
                "event_id": "raw_a",
            },
            {
                "canonical_event_id": "",
                "instrument": "SH600001",
                "event_t0_date": "2024-01-01",
                "trade_open_date": "2024-01-02",
                "event_id": "raw_b",
            },
        ]
    )

    ids = frontier.canonical_sample_id(frame)

    assert ids.iloc[0] == "canon_a"
    assert ids.iloc[1]
    assert ids.iloc[1] != "raw_b"


def test_rebuild_e1_uses_triggered_channel_and_regime_alias() -> None:
    canonical = pd.DataFrame(
        [
            {
                "event_id": "a",
                "canonical_event_id": "a",
                "triggered_channels": "E1_early_ema60_repair;E2",
                "market_regime_bucket": "risk_off",
                "event_t0_pos": 1,
                "trade_open_pos": 2,
                "non_executable_next_open": False,
            },
            {
                "event_id": "b",
                "canonical_event_id": "b",
                "triggered_channels": "E6_continuation_discriminator",
                "market_regime_bucket": "risk_on",
                "event_t0_pos": 1,
                "trade_open_pos": 2,
                "non_executable_next_open": False,
            },
        ]
    )

    out = frontier.rebuild_e1(canonical)

    assert out["event_id"].tolist() == ["a"]
    assert out["event_regime_bucket"].tolist() == ["risk_off"]


def test_touch_offset_sessions_is_relative_to_trade_open_pos() -> None:
    out = frontier.touch_offset_sessions(
        pd.Series([102, 110, -1, 99]),
        pd.Series([100, 108, 120, 100]),
        pd.Series([True, True, False, True]),
    )

    assert out.tolist() == [2, 2, -1, -1]


def test_frontier_uses_explicit_10d_and_120d_completeness_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "denominator_id": "risk_on_r_core_horizon_complete",
                "event_split": "train",
                "horizon_complete_10d": True,
                "horizon_complete_20d": True,
                "horizon_complete_120d": True,
                "candidate_outcome_120d_status": "not_missing",
                "event_big_winner_120d_label": True,
                "event_false_repair_20d_label": False,
                "failure_10_label": False,
                "target_episode_id": "ep1",
                "incumbent_failure_10_label_label": False,
                "incumbent_failure_10_label_evaluable": True,
                "fixed_mae10_neg_05_label": False,
                "fixed_mae10_neg_05_evaluable": True,
                "non_executable_next_open": False,
            }
        ]
    )
    candidate_eval = pd.DataFrame(
        [{"candidate_label_id": "fixed_mae10_neg_05", "candidate_label_status": "evaluable"}]
    )
    config = {"candidate_labels": {"fixed_mae10_neg_05": {}}}

    out = frontier.build_frontier(frame, candidate_eval, config)

    assert "horizon_complete_10d_n" in out.columns
    assert "winner_120_complete_n" in out.columns
    assert "horizon_complete_n" not in out.columns


def test_only_primary_selected_label_is_09c_supported() -> None:
    frame = pd.DataFrame(
        [
            {
                "denominator_id": "risk_on_r_core_horizon_complete",
                "split": "train",
                "candidate_label_id": "break_swing_low_20",
                "not_evaluable_share": 0.0,
                "positive_rate": 0.08,
                "episode_winner_recall_retention": 1.0,
                "kill_wrong_rate": 0.08,
                "winner_injury_rate": 0.03,
            },
            {
                "denominator_id": "risk_on_r_core_horizon_complete",
                "split": "train",
                "candidate_label_id": "fixed_mae10_neg_12",
                "not_evaluable_share": 0.0,
                "positive_rate": 0.20,
                "episode_winner_recall_retention": 0.97,
                "kill_wrong_rate": 0.10,
                "winner_injury_rate": 0.11,
            },
        ]
    )
    candidate_eval = pd.DataFrame(
        [
            {
                "candidate_label_id": "break_swing_low_20",
                "candidate_label_status": "evaluable",
            },
            {
                "candidate_label_id": "fixed_mae10_neg_12",
                "candidate_label_status": "evaluable",
            },
        ]
    )
    config = {
        "selection": {
            "primary_denominator_id": "risk_on_r_core_horizon_complete",
            "train_not_evaluable_share_max": 0.005,
            "train_positive_rate_min": 0.05,
            "train_positive_rate_max": 0.45,
            "train_episode_winner_recall_retention_min": 0.85,
            "selected_label_max_count": 2,
        },
        "candidate_labels": {
            "break_swing_low_20": {
                "mechanism_family": "structural",
                "selected_allowed": True,
            },
            "fixed_mae10_neg_12": {
                "mechanism_family": "fixed_mae10",
                "selected_allowed": True,
            },
        },
    }

    selected = frontier.select_labels(frame, candidate_eval, config)

    selected_rows = selected.loc[selected["selection_status"].eq("selected")].sort_values(
        "selection_rank"
    )
    assert selected_rows["selected_fast_fail_label_id"].tolist() == [
        "break_swing_low_20",
        "fixed_mae10_neg_12",
    ]
    assert selected_rows["usable_for_09C_supported_gate"].tolist() == [True, False]
    assert selected_rows["selection_reason"].tolist() == [
        "train_pareto_selected_primary_binding",
        "train_pareto_selected_sensitivity_only",
    ]
