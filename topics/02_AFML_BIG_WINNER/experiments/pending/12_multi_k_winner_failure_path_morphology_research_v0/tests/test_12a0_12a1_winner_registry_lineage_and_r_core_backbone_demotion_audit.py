from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "run_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a0_12a1_audit", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_canonical_from_input_event_key_uses_component_4():
    runner = load_runner()

    canonical, source = runner.parse_canonical_from_input_event_key("scope|split|rank|canon-123|extra")

    assert canonical == "canon-123"
    assert source == "input_event_key_component_4"


def test_pit_candidate_registry_keeps_frozen_winners_with_basis_mismatch():
    runner = load_runner()
    mfe = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "instrument": ["A", "B", "C"],
            "event_t0_date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "mfe_120d_frozen": [0.51, 0.60, 0.49],
            "mfe_120_recomputed": [0.51, 0.10, 0.49],
            "mfe_120_rel_diff": [0.0, 0.83, 0.0],
            "basis_status": ["ok", "mfe_basis_mismatch", "ok"],
        }
    )

    registry = runner.build_pit_candidate_winner_registry(mfe, runner.REPO_ROOT / "dummy.csv")

    assert registry["row_id"].tolist() == [1, 2]
    assert registry.loc[registry["row_id"].eq(1), "lineage_status"].iloc[0] == "basis_ok"
    assert (
        registry.loc[registry["row_id"].eq(2), "lineage_status"].iloc[0]
        == "basis_mismatch_kept_for_frozen_label_consistency"
    )


def test_vectorized_window_matching_counts_episode_recall_and_event_precision():
    runner = load_runner()
    events = pd.DataFrame(
        {
            "event_key": ["e1", "e2", "e3", "e4"],
            "instrument": ["A", "A", "B", "C"],
            "event_signal_date": ["2020-01-10", "2019-12-15", "2020-01-10", "2020-01-10"],
        }
    )
    episodes = pd.DataFrame(
        {
            "episode_id": ["epA", "epB"],
            "instrument": ["A", "B"],
            "episode_low_date": ["2020-01-01", "2020-03-01"],
            "episode_high_date": ["2020-02-01", "2020-04-01"],
            "first_50pct_date": ["2020-01-20", "2020-03-15"],
            "pre120_calendar_start_date": ["2019-09-03", "2019-11-02"],
        }
    )

    pairs = runner.pair_events_episodes(events, episodes)
    captured_pre120, event_counts_pre120, episode_counts, first_offsets, multi = runner.event_match_details_from_pairs(
        events,
        pairs,
        "pre120_calendar_to_high",
    )
    captured_low_high, event_counts_low_high, _, _, _ = runner.event_match_details_from_pairs(
        events,
        pairs,
        "low_to_high",
    )
    timing = runner.nearest_timing_categories_from_pairs(events, pairs)

    assert captured_pre120 == {"epA", "epB"}
    assert event_counts_pre120 == {"e1": 1, "e2": 1, "e3": 1, "e4": 0}
    assert episode_counts == {"epA": 2, "epB": 1}
    assert first_offsets == [-17.0, -51.0]
    assert multi == 0
    assert captured_low_high == {"epA"}
    assert event_counts_low_high == {"e1": 1, "e2": 0, "e3": 0, "e4": 0}
    assert dict(zip(timing["event_key"], timing["category"])) == {
        "e1": "inside_low_to_high",
        "e2": "pre120_before_episode_low",
        "e3": "pre120_before_episode_low",
        "e4": "no_same_instrument_episode",
    }
