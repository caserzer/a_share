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

import pipeline  # noqa: E402


def _input_status() -> pipeline.InputStatus:
    return pipeline.InputStatus(
        input_gate_status="pass",
        input_gate_failure_reason="",
        upstream_05_decision="topn_universe_candidate_panel_blocked",
        upstream_06_decision="topn_reverse_lifecycle_sequence_supported_universal_dominance",
        topn_candidate_gap_accepted=True,
        universe_precision_status="available_source_topn_candidate_gap",
        latest_label_complete_low_date="2025-11-26",
        source_gap_count=318,
        active_source_gap_count=229,
        old_04_density_baseline_source="04_manifest_gate_summary",
        old_04_setup_inclusive_events_per_instrument_year_mean=3.33,
        old_04_setup_inclusive_events_per_instrument_year_p95=3.33,
        old_04_reclaim_based_events_per_instrument_year_mean=1.72,
        old_04_reclaim_based_events_per_instrument_year_p95=1.72,
    )


def _gate_config() -> dict:
    return {
        "gates": {
            "min_capture_any_event_before_first_50pct_all": 0.55,
            "min_capture_any_event_before_first_50pct_validation": 0.45,
            "min_capture_any_event_before_first_50pct_robustness": 0.45,
            "min_non_e0_positive_unique_recall_channels": 2,
            "min_next_open_executable_rate": 0.95,
            "min_event_precision_label_complete_rate": 0.70,
            "min_capture_label_complete_rate": 0.90,
            "max_recommended_union_canonical_events_per_instrument_year_mean": 6.0,
            "max_recommended_union_canonical_events_per_instrument_year_p95": 12.0,
            "max_single_channel_density_share": 0.75,
            "max_density_drag_channel_share": 0.25,
            "density_drag_incremental_recall_threshold": 0.02,
        }
    }


def _passing_recall() -> pd.DataFrame:
    rows = []
    for split, recall in [("all", 0.60), ("validation", 0.50), ("robustness", 0.50)]:
        rows.append(
            {
                "episode_split": split,
                "market_regime_bucket": "all",
                "board_bucket": "all",
                "window": "before_first_50pct",
                "recall": recall,
            }
        )
    return pd.DataFrame(rows)


def _channel_contrib() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"channel_id": pipeline.CHANNEL_E1, "unique_recall": 0.01},
            {"channel_id": pipeline.CHANNEL_E2, "unique_recall": 0.02},
            {"channel_id": pipeline.CHANNEL_E3, "unique_recall": 0.00},
        ]
    )


def _density(mean: float = 5.0, p95: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scope": "recommended_union",
                "channel_id": pipeline.UNION_EVENT_FAMILY,
                "events_per_instrument_year_mean": mean,
                "events_per_instrument_year_p95": p95,
                "density_share": 1.0,
                "density_drag_flag": False,
            },
            {
                "scope": "channel_instance",
                "channel_id": pipeline.CHANNEL_E1,
                "events_per_instrument_year_mean": 2.0,
                "events_per_instrument_year_p95": 4.0,
                "density_share": 0.50,
                "density_drag_flag": False,
            },
            {
                "scope": "channel_instance",
                "channel_id": pipeline.CHANNEL_E2,
                "events_per_instrument_year_mean": 2.0,
                "events_per_instrument_year_p95": 4.0,
                "density_share": 0.50,
                "density_drag_flag": False,
            },
        ]
    )


def _execution(next_open: float = 1.0, event_label: float = 1.0, capture_label: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scope": "all",
                "split": "all",
                "next_open_executable_rate": next_open,
                "event_precision_label_complete_rate": event_label,
                "capture_label_complete_rate": capture_label,
            }
        ]
    )


def test_decision_density_blocked_is_reachable_after_recall_passes() -> None:
    decision, summary = pipeline.decide(
        input_status=_input_status(),
        any_recall=_passing_recall(),
        density=_density(mean=7.0, p95=13.0),
        channel_contrib=_channel_contrib(),
        execution=_execution(),
        config=_gate_config(),
    )

    assert decision == pipeline.DECISION_DENSITY_BLOCKED
    assert summary["capture_any_event_before_first_50pct_validation"] >= 0.45
    assert summary["capture_any_event_before_first_50pct_robustness"] >= 0.45


def test_decision_execution_label_blocked_has_legal_state() -> None:
    decision, summary = pipeline.decide(
        input_status=_input_status(),
        any_recall=_passing_recall(),
        density=_density(),
        channel_contrib=_channel_contrib(),
        execution=_execution(next_open=0.92),
        config=_gate_config(),
    )

    assert decision == pipeline.DECISION_EXECUTION_LABEL_BLOCKED
    assert summary["next_open_executable_rate"] == 0.92


def test_bridge_incomplete_event_is_excluded_not_counted_as_miss() -> None:
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=5, freq="D").strftime("%Y-%m-%d"),
            "high": [10.0, 10.5, 11.0, 15.5, 16.0],
        }
    )
    episodes = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "instrument": "000001.SZ",
                "episode_low_date": "2020-01-01",
                "episode_high_date": "2020-01-05",
                "effective_first_50pct_touch_date": "2020-01-04",
                "effective_first_50pct_touch_pos": 3,
                "split": "train",
                "board_bucket": "main",
                "market_regime_bucket": "mixed",
            }
        ]
    )
    canonical = pd.DataFrame(
        [
            {
                "event_id": "event1",
                "instrument": "000001.SZ",
                "event_t0_pos": 1,
                "event_t0_date": "2020-01-02",
                "event_family_priority": 1,
            }
        ]
    )
    labels = pd.DataFrame(
        [
            {
                "event_id": "event1",
                "horizon_complete_120d": False,
                "event_big_winner_120d_label": False,
            }
        ]
    )

    capture = pipeline.build_episode_capture_audit(
        episodes,
        canonical,
        labels,
        {"000001.SZ": daily},
    )
    row = capture.loc[capture["window"] == "before_first_50pct"].iloc[0]

    assert bool(row["any_event_captured"])
    assert not bool(row["bridge_positive_denominator_included"])
    assert row["bridge_positive_exclusion_reason"] == "bridge_forward_120_incomplete"


def test_debug_output_paths_do_not_publish_manifest() -> None:
    config = {
        "outputs": {
            "publishable_tables_dir": "experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables",
            "publishable_reports_dir": "experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/reports",
            "local_cache_dir": "experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache",
            "large_raw_dir": "experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/large_raw",
            "manifests_dir": "experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests",
        }
    }

    paths = pipeline.build_output_paths(config, debug=True)

    assert paths["manifest"].name == "debug_metadata.json"
    assert "local_cache/debug_subset" in paths["manifest"].as_posix()
    assert "outputs/manifests/run_manifest.json" not in paths["manifest"].as_posix()


def test_topn_evaluated_universe_flags_match_06_contract() -> None:
    split = pipeline.SplitConfig(
        train_start="2017-01-03",
        train_end="2021-12-31",
        validation_start="2022-01-01",
        validation_end="2023-12-31",
        robustness_start="2024-01-01",
        latest_main_label_complete_t0_date="2025-11-26",
        latest_120d_outcome_complete_t0_date="2025-11-26",
    )
    universe = pd.DataFrame(
        [
            {
                "usable_trade_date": "2021-12-31",
                "instrument": "000001.SZ",
                "source_membership_date": "2021-12-30",
                "membership_available_time": "2021-12-30 close",
                "history_observed_sessions_before_usable_date": 250,
            },
            {
                "usable_trade_date": "2026-01-04",
                "instrument": "000001.SZ",
                "source_membership_date": "2026-01-03",
                "membership_available_time": "2026-01-03 close",
                "history_observed_sessions_before_usable_date": 400,
            },
            {
                "usable_trade_date": "2024-01-03",
                "instrument": "000002.SZ",
                "source_membership_date": "2024-01-02",
                "membership_available_time": "2024-01-02 close",
                "history_observed_sessions_before_usable_date": 249,
            },
        ]
    )
    config = {"event_generation": {"prior_lookback_sessions": 250}}

    flagged = pipeline.add_topn_evaluated_universe_flags(universe, split, config)

    assert flagged["evaluated_flag"].tolist() == [True, False, False]
    assert flagged["split"].tolist() == ["train", "outside_split", "robustness"]


def test_density_drag_uses_canonical_triggered_share() -> None:
    instances = pd.DataFrame(
        [
            {"instrument": "000001.SZ", "event_t0_date": "2020-01-01", "channel_id": pipeline.CHANNEL_E1},
            {"instrument": "000001.SZ", "event_t0_date": "2020-01-02", "channel_id": pipeline.CHANNEL_E2},
        ]
    )
    canonical = pd.DataFrame(
        [
            {
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-01",
                "triggered_channels": pipeline.CHANNEL_E1,
            },
            {
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-02",
                "triggered_channels": pipeline.CHANNEL_E2,
            },
            {
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-03",
                "triggered_channels": pipeline.CHANNEL_E2,
            },
            {
                "instrument": "000001.SZ",
                "event_t0_date": "2020-01-04",
                "triggered_channels": pipeline.CHANNEL_E2,
            },
        ]
    )
    contrib = pd.DataFrame(
        [
            {"channel_id": pipeline.CHANNEL_E1, "incremental_recall": 0.50},
            {"channel_id": pipeline.CHANNEL_E2, "incremental_recall": 0.00},
        ]
    )
    config = {
        "channels": {"recommended": [pipeline.CHANNEL_E1, pipeline.CHANNEL_E2]},
        "gates": {
            "density_drag_incremental_recall_threshold": 0.02,
            "max_density_drag_channel_share": 0.25,
        },
    }

    density = pipeline.build_density_summary(
        instances, canonical, universe_years=1.0, channel_contrib=contrib, config=config
    )
    e2 = density.loc[density["channel_id"] == pipeline.CHANNEL_E2].iloc[0]

    assert e2["density_share"] == 0.75
    assert bool(e2["density_drag_flag"])
