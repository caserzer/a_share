from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a6b_c0_risk_on_fast_fail_survival_uplift_audit.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a6b_fast_fail", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStockDailyCache:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames
        self.schema_failures = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        return self.frames.get(str(instrument))


def test_global_regime_calendar_filters_reconciliation_row_and_blocks_conflicts(tmp_path):
    runner = load_runner()
    path = tmp_path / "regime.csv"
    pd.DataFrame(
        [
            {"date": "2020-01-02", "daily_regime_bucket": "risk_on", "daily_regime_conflict_n": 0, "daily_regime_conflict_flag": False},
            {"date": "__calendar_reconciliation__", "daily_regime_bucket": "pass", "daily_regime_conflict_n": 0, "daily_regime_conflict_flag": False},
        ]
    ).to_csv(path, index=False)

    calendar = runner.load_global_regime_calendar(path)

    assert calendar.status == "pass"
    assert calendar.non_date_row_n == 1
    assert calendar.calendar == {"2020-01-02": "risk_on"}

    pd.DataFrame(
        [
            {"date": "2020-01-02", "daily_regime_bucket": "risk_on", "daily_regime_conflict_n": 1, "daily_regime_conflict_flag": True},
        ]
    ).to_csv(path, index=False)
    blocked = runner.load_global_regime_calendar(path)
    assert blocked.status == "blocked_regime_conflict_date"


def test_entry_bar_lower_touch_counts_as_fast_fail_with_time_zero():
    runner = load_runner()
    events = pd.DataFrame(
        [
            {
                "instrument": "AAA",
                "entry_date": "2020-01-02",
                "entry_pos": 0,
                "entry_price": 10.0,
                "entry_blocked": False,
                "path_key": runner.path_key("AAA", "2020-01-02", 0, 10.0),
            }
        ]
    )
    stock = FakeStockDailyCache(
        {
            "AAA": pd.DataFrame(
                {
                    "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
                    "open": [10.0, 10.2, 10.3],
                    "high": [10.1, 11.0, 11.5],
                    "low": [8.9, 10.0, 10.1],
                    "close": [9.5, 10.5, 11.0],
                }
            )
        }
    )

    cache = runner.build_path_cache(events, stock, [2], [-0.10], [0.10])

    assert bool(cache.iloc[0]["horizon_complete_2d"])
    assert int(cache.iloc[0]["time_to_lower_minus_10_2d"]) == 0


def test_random_sampling_preserves_replacement_draws_and_fallback_status():
    runner = load_runner()
    c0 = pd.DataFrame(
        [
            {"split": "train", "board_bucket": "main_board", "calendar_month": "2020-01", "calendar_quarter": "2020Q1"},
            {"split": "train", "board_bucket": "main_board", "calendar_month": "2020-01", "calendar_quarter": "2020Q1"},
            {"split": "train", "board_bucket": "main_board", "calendar_month": "2020-01", "calendar_quarter": "2020Q1"},
            {"split": "train", "board_bucket": "main_board", "calendar_month": "2020-01", "calendar_quarter": "2020Q1"},
        ]
    )
    candidates = pd.DataFrame(
        [
            {
                "split": "train",
                "board_bucket": "main_board",
                "calendar_month": "2020-01",
                "calendar_quarter": "2020Q1",
                "event_date": "2020-01-02",
                "entry_date": "2020-01-03",
                "instrument": "AAA",
                "entry_pos": 1,
                "entry_price": 10.0,
                "path_key": "p1",
                "candidate_row_id": 0,
                "exact_c0_key_excluded_flag": False,
            }
        ]
    )
    exact = pd.DataFrame(columns=["split", "board_bucket", "calendar_month", "exact_c0_key_excluded_n"])

    sampled, audit = runner.sample_random_entries(
        c0,
        candidates,
        exact,
        base_seed=1,
        random_seed_n=1,
        replacement_threshold=0.25,
        fallback_merge=False,
    )

    assert len(sampled) == 4
    assert sampled["replacement_used_flag"].all()
    assert sampled["sample_weight"].sum() == 4
    assert audit.iloc[0]["cell_status"] == "degraded_high_replacement"


def test_conditional_continuation_uses_primary_no_fast_fail_cohort_only():
    runner = load_runner()
    events = pd.DataFrame(
        [
            {
                "population_id": "c0_risk_on",
                "baseline_role": "c0_candidate",
                "scope_id": "unused",
                "split": "train",
                "board_bucket": "main_board",
                "primary_family_id": "B1",
                "calendar_year": "2020",
                "sample_weight": 1.0,
                "entry_blocked": False,
                "horizon_complete_20d": True,
                "time_to_lower_minus_10_20d": pd.NA,
                "time_to_upper_plus_10_20d": 5,
            },
            {
                "population_id": "c0_risk_on",
                "baseline_role": "c0_candidate",
                "scope_id": "unused",
                "split": "train",
                "board_bucket": "main_board",
                "primary_family_id": "B1",
                "calendar_year": "2020",
                "sample_weight": 1.0,
                "entry_blocked": False,
                "horizon_complete_20d": True,
                "time_to_lower_minus_10_20d": 0,
                "time_to_upper_plus_10_20d": 1,
            },
        ]
    )

    out = runner.aggregate_conditional(
        events,
        population_id="c0_risk_on",
        baseline_role="c0_candidate",
        lowers=[-0.10],
        uppers=[0.10],
        condition_lower=-0.10,
        condition_horizon=20,
        upper_horizon=20,
        include_family=False,
        diagnostic_family=False,
    )
    train = out.loc[out["scope_id"].eq(runner.SPLIT_SCOPE)].iloc[0]

    assert int(train["complete_executable_event_n"]) == 2
    assert int(train["no_fast_fail_n"]) == 1
    assert float(train["upper_touch_rate_total"]) == 1.0
    assert float(train["upper_touch_rate_given_no_fast_fail"]) == 1.0


def test_decision_treats_lower_fast_fail_rate_as_better():
    runner = load_runner()
    config = {
        "primary_label": {"lower_barrier_pct": -0.10, "horizon_sessions": 20},
        "gates": {
            "min_complete_executable_event_n": 500,
            "train_fast_fail_delta_vs_random_p50": -0.03,
            "train_fast_fail_delta_vs_r_core": -0.02,
            "robustness_fast_fail_delta_vs_random_p50": -0.02,
            "robustness_fast_fail_delta_vs_r_core": 0.0,
            "min_no_fast_fail_rate": 0.50,
        },
    }
    uplift = pd.DataFrame(
        [
            {
                "scope_id": runner.SPLIT_SCOPE,
                "split": "train",
                "horizon_sessions": 20,
                "lower_barrier_pct": -0.10,
                "c0_complete_executable_event_n": 1000,
                "c0_fast_fail_rate": 0.20,
                "random_fast_fail_rate_p50": 0.25,
                "random_fast_fail_rate_p95": 0.30,
                "r_core_fast_fail_rate": 0.23,
                "fast_fail_abs_delta_vs_random_p50": -0.05,
                "fast_fail_abs_delta_vs_r_core": -0.03,
            },
            {
                "scope_id": runner.SPLIT_SCOPE,
                "split": "robustness",
                "horizon_sessions": 20,
                "lower_barrier_pct": -0.10,
                "c0_complete_executable_event_n": 1000,
                "c0_fast_fail_rate": 0.20,
                "random_fast_fail_rate_p50": 0.24,
                "random_fast_fail_rate_p95": 0.30,
                "r_core_fast_fail_rate": 0.21,
                "fast_fail_abs_delta_vs_random_p50": -0.04,
                "fast_fail_abs_delta_vs_r_core": -0.01,
            },
            {
                "scope_id": runner.SPLIT_SCOPE,
                "split": "validation",
                "horizon_sessions": 20,
                "lower_barrier_pct": -0.10,
                "c0_complete_executable_event_n": 1000,
                "c0_fast_fail_rate": 0.20,
                "random_fast_fail_rate_p50": 0.24,
                "random_fast_fail_rate_p95": 0.30,
                "r_core_fast_fail_rate": 0.21,
                "fast_fail_abs_delta_vs_random_p50": -0.04,
                "fast_fail_abs_delta_vs_r_core": -0.01,
            },
        ]
    )
    conditional = pd.DataFrame(
        [
            {
                "population_id": "c0_risk_on",
                "scope_id": runner.SPLIT_SCOPE,
                "split": split,
                "upper_barrier_pct": upper,
                "upper_touch_rate_given_no_fast_fail": 0.4,
                "random_upper_touch_rate_given_no_fast_fail_p05": 0.2,
                "random_upper_touch_rate_given_no_fast_fail_p50": 0.3,
            }
            for split in ("train", "robustness", "validation")
            for upper in (0.10, 0.15)
        ]
    )
    sampling = pd.DataFrame([{"cell_status": "ok", "seed": 1}])
    entry = pd.DataFrame(
        [
            {"population_id": "c0_risk_on", "entry_parity_gate_pass": True},
            {"population_id": "r_core_risk_on", "entry_parity_gate_pass": True},
        ]
    )
    membership = pd.DataFrame([{"global_regime_calendar_status": "pass"}])

    decision = runner.evaluate_decision(uplift, conditional, sampling, entry, membership, config)

    assert decision.iloc[0]["decision_state"] == "12A6b_c0_fast_fail_survival_uplift_supported"
