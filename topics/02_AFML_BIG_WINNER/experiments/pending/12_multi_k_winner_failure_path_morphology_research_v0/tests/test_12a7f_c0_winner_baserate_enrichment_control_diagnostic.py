from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7f_c0_winner_baserate_enrichment_control_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7f_c0_winner_baserate_enrichment_control_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def base_config() -> dict:
    return {
        "control_matching": {
            "control_match_min_coverage": 0.90,
            "control_sample_seed": 120713,
            "control_sampling_mode": "without_replacement_fixed_canonical_sample",
        },
        "bootstrap": {
            "bootstrap_min_c0_denominator_n": 100,
            "bootstrap_min_winner_positive_n": 30,
            "bootstrap_min_valid_replicates": 1500,
        },
        "decision": {"min_winner_rate_diff": 0.02},
    }


def test_first_hit_treats_same_day_upper_lower_conflict_as_not_winner():
    runner = load_runner()
    daily = pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.0],
            "high": [12.0, 10.0, 10.0],
            "low": [9.0, 10.0, 10.0],
            "close": [10.0, 10.0, 10.0],
        }
    )

    complete, winner, fast_fail, upper_t, lower_t = runner.first_hit_label(daily, 0, 10.0, 2, 0.20, -0.10)

    assert complete
    assert not winner
    assert fast_fail
    assert upper_t == 0
    assert lower_t == 0


def test_split_mapper_uses_decision_date_boundaries():
    runner = load_runner()
    boundary = pd.DataFrame(
        {
            "eval_split": ["validation", "robustness"],
            "train_max_event_t0_date": ["2021-12-31", "2021-12-31"],
            "eval_min_event_t0_date": ["2022-01-04", "2024-03-01"],
            "split_time_boundary_gate_pass": [True, True],
        }
    )
    _info, assign = runner.split_mapper(boundary)

    assert assign("2021-12-31") == "train"
    assert assign("2022-01-04") == "validation"
    assert assign("2024-03-01") == "robustness"


def test_decision_requires_both_big_winner_horizons_for_strong_support():
    runner = load_runner()
    config = base_config()
    bootstrap = pd.DataFrame(
        [
            {
                "split": "robustness",
                "label_family": "direct_entry",
                "readout_view": "unconditional",
                "winner_barrier": "direct_entry_win_up_20_h20",
                "barrier_enrichment_status": "positive_for_barrier",
                "winner_rate_diff": 0.03,
                "winner_rate_diff_ci95_low": 0.01,
                "winner_rate_diff_ci95_high": 0.05,
            },
            {
                "split": "robustness",
                "label_family": "direct_entry",
                "readout_view": "unconditional",
                "winner_barrier": "direct_entry_win_up_20_h40",
                "barrier_enrichment_status": "uncertain_for_barrier",
                "winner_rate_diff": 0.01,
                "winner_rate_diff_ci95_low": -0.01,
                "winner_rate_diff_ci95_high": 0.03,
            },
        ]
    )
    readout = bootstrap.assign(fast_fail_rate_diff=-0.05)

    decision = runner.decision_from_readouts(readout, bootstrap, "pass", "pass", 1.0, config)

    assert decision.iloc[0]["decision_state"] == "12A7f_c0_winner_enrichment_weak_or_horizon_dependent"


def test_barrier_status_uses_denominator_not_entry_n():
    runner = load_runner()
    config = base_config()
    row = pd.Series(
        {
            "matched_c0_entry_coverage": 1.0,
            "c0_entry_n": 1000,
            "c0_denominator_n": 50,
            "c0_winner_positive_n": 40,
            "bootstrap_replicate_valid_n": 2000,
            "winner_rate_diff": 0.04,
            "winner_rate_diff_ci95_low": 0.01,
        }
    )

    assert runner.barrier_status(row, config) == "uncertain_for_barrier"
