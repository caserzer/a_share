from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
SPEC = importlib.util.spec_from_file_location(
    "high_recall_repair_pipeline", CODE_DIR / "pipeline.py"
)
assert SPEC is not None and SPEC.loader is not None
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


def test_canonical_union_uses_earliest_event_not_earliest_executable() -> None:
    raw = pd.DataFrame(
        [
            {
                "instrument": "SH600000",
                "event_id": "early_non_exec",
                "event_family": "E0_seed_low_setup",
                "event_family_priority": 0,
                "event_t0_pos": 10,
                "event_t0_date": "2024-01-10",
                "non_executable_next_open": True,
                "canonical_event_scope": pipeline.RAW_SCOPE,
                "union_family": "raw_family",
                "union_density_kept": False,
            },
            {
                "instrument": "SH600000",
                "event_id": "later_exec",
                "event_family": "E1_first_ema60_reclaim",
                "event_family_priority": 1,
                "event_t0_pos": 12,
                "event_t0_date": "2024-01-12",
                "non_executable_next_open": False,
                "canonical_event_scope": pipeline.RAW_SCOPE,
                "union_family": "raw_family",
                "union_density_kept": False,
            },
        ]
    )

    union_events = pipeline.build_canonical_union_events(
        raw,
        union_family=pipeline.SETUP_UNION,
        density_window=20,
    )
    canonical = union_events.loc[
        union_events["canonical_event_scope"] == pipeline.CANONICAL_SCOPE
    ]

    assert len(canonical) == 1
    assert canonical.iloc[0]["event_t0_pos"] == 10
    assert bool(canonical.iloc[0]["non_executable_next_open"])


def test_decision_short_circuit_prefers_density_before_actionability_late() -> None:
    gates = {
        "min_total_target_episode_count": 1,
        "min_validation_target_episode_count": 1,
        "min_robustness_target_episode_count": 1,
        "min_total_episode_recall_low_to_plus_30d": 0.7,
        "min_validation_episode_recall_low_to_plus_30d": 0.6,
        "min_robustness_episode_recall_low_to_plus_30d": 0.6,
        "min_total_episode_recall_low_to_plus_20d": 0.6,
        "min_validation_episode_recall_low_to_plus_20d": 0.5,
        "min_robustness_episode_recall_low_to_plus_20d": 0.5,
        "min_total_episode_recall_before_first_50pct": 0.7,
        "min_validation_episode_recall_before_first_50pct": 0.6,
        "min_robustness_episode_recall_before_first_50pct": 0.6,
        "max_setup_inclusive_events_per_instrument_year_p95": 18,
        "max_setup_inclusive_events_per_instrument_year_mean": 8,
        "max_reclaim_based_events_per_instrument_year_p95": 12,
        "max_reclaim_based_events_per_instrument_year_mean": 6,
        "min_executable_rate": 0.8,
        "min_main_label_complete_rate": 0.7,
        "min_120d_outcome_complete_rate_for_precision_readout": 0.6,
    }
    summary = {
        "gates": gates,
        "target_episode_count_total": 10,
        "target_episode_count_validation": 2,
        "target_episode_count_robustness": 2,
        "executable_rate": 1.0,
        "main_label_complete_rate": 1.0,
        "total_recall_low_to_plus_30d": 1.0,
        "validation_recall_low_to_plus_30d": 1.0,
        "robustness_recall_low_to_plus_30d": 1.0,
        "total_recall_low_to_plus_20d": 1.0,
        "validation_recall_low_to_plus_20d": 1.0,
        "robustness_recall_low_to_plus_20d": 1.0,
        "setup_inclusive_events_per_instrument_year_p95": 30.0,
        "setup_inclusive_events_per_instrument_year_mean": 10.0,
        "reclaim_based_events_per_instrument_year_p95": 4.0,
        "reclaim_based_events_per_instrument_year_mean": 2.0,
        "total_recall_before_first_50pct": 0.0,
        "validation_recall_before_first_50pct": 0.0,
        "robustness_recall_before_first_50pct": 0.0,
        "outcome_complete_120d_rate": 1.0,
    }

    assert (
        pipeline.decide(summary)
        == "candidate_generator_recall_supported_density_blocked"
    )


def test_low30_late_capture_does_not_count_before_first() -> None:
    capture = pd.DataFrame(
        {
            "episode_split": ["train"],
            "duration_bucket": ["fast"],
            "captured_by_setup_inclusive_density_kept_low_to_plus_30d": [True],
            "captured_by_setup_inclusive_density_kept_before_first_50pct": [False],
            "late_after_first_50pct_capture_flag": [True],
        }
    )

    duration = pipeline.build_duration_bucket_actionable_recall(capture)

    assert duration.iloc[0]["recall_low_to_plus_30d"] == 1.0
    assert duration.iloc[0]["recall_before_first_50pct"] == 0.0
    assert duration.iloc[0]["late_after_first_50pct_capture_share"] == 1.0


def test_afml_uniqueness_uses_overlapping_label_spans() -> None:
    labels = pd.DataFrame(
        {
            "event_id": ["a", "b"],
            "non_executable_next_open": [False, False],
            "trade_open_pos": [0, 1],
            "confirm_20_touch_pos": [2, 3],
            "confirm_20_complete": [True, True],
        }
    )

    metrics = pipeline.concurrency_uniqueness(labels, 20)

    assert metrics["event_concurrency_p95"] > 1.0
    assert metrics["average_uniqueness_mean"] < 1.0
