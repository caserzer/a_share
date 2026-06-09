from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
SPEC = importlib.util.spec_from_file_location(
    "observable_anchor_pipeline", CODE_DIR / "pipeline.py"
)
assert SPEC is not None and SPEC.loader is not None
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


def test_candidate_seed_low_uses_trailing_window_only() -> None:
    dates = pd.date_range("2024-01-01", periods=8, freq="D").strftime("%Y-%m-%d")
    frame = pd.DataFrame(
        {
            "date": dates,
            "instrument": ["SH600000"] * 8,
            "low": [10.0, 9.0, 8.0, 8.5, 8.2, 7.9, 8.1, 7.8],
        }
    )
    params = pipeline.EventParams(
        prior_lookback_sessions=2,
        seed_low_lookback_sessions=2,
        anchor_search_horizon_sessions=5,
        rank_jump_threshold=0.05,
        rank_jump_window=2,
        persistence_window=2,
        persistence_floor=0.0,
        persistence_coverage=0.5,
        amount_ratio_20d_gate=1.5,
        plus20_threshold=0.2,
        continuation_window=2,
        continuation_rank_floor=0.0,
        continuation_rank_coverage=0.5,
        continuation_amount_floor=1.2,
        continuation_amount_coverage=0.5,
    )

    seeds = pipeline.extract_candidate_seed_lows(
        frame,
        membership_dates=set(dates),
        params=params,
    )

    assert list(seeds["candidate_seed_low_date"]) == [
        "2024-01-03",
        "2024-01-06",
        "2024-01-08",
    ]


def test_false_repair_asof_does_not_use_future_diagnostic_window() -> None:
    dates = pd.date_range("2024-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
    frame = pd.DataFrame(
        {
            "date": dates,
            "close": [10.0] * 30,
            "high": [10.1] * 30,
            "low": [9.9] * 30,
        }
    )
    frame.loc[8, "close"] = 8.9
    params = pipeline.FalseRepairParams(
        drawdown_floor=-0.10,
        insufficient_runup_floor=0.05,
    )

    asof = pipeline.false_repair_metrics_asof(
        frame,
        reclaim_pos=5,
        t0_pos=7,
        params=params,
    )
    after = pipeline.false_repair_metrics_asof(
        frame,
        reclaim_pos=5,
        t0_pos=10,
        params=params,
    )

    assert not asof["false_repair_observed_asof_t0"]
    assert asof["false_repair_10d_diagnostic"]
    assert after["false_repair_observed_asof_t0"]
    assert after["false_repair_drawdown_trigger_date"] == "2024-01-09"


def test_baseline_family_excludes_false_repair_variant_only() -> None:
    baselines = pd.DataFrame(
        {
            "baseline_id": ["b1", "b2"],
            "false_repair_observed_asof_baseline_t0": [True, False],
        }
    )

    duplicated = pipeline.duplicate_baseline_families(baselines)

    raw = duplicated.loc[duplicated["baseline_family"] == "baseline_raw"]
    excluded = duplicated.loc[
        duplicated["baseline_family"] == "baseline_false_repair_excluded"
    ]
    assert set(raw["source_baseline_id"]) == {"b1", "b2"}
    assert set(excluded["source_baseline_id"]) == {"b2"}
    assert set(raw["baseline_id"]) == {"b1__baseline_raw", "b2__baseline_raw"}
    assert set(excluded["baseline_id"]) == {"b2__baseline_false_repair_excluded"}


def test_60d_continuous_readout_censors_independently_from_20d_label() -> None:
    dates = pd.date_range("2024-01-01", periods=35, freq="D").strftime("%Y-%m-%d")
    frame = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 35,
            "high": [10.5] * 35,
            "low": [9.9] * 35,
            "close": [10.2] * 35,
        }
    )
    trade = {
        "trade_open_pos": 1,
        "trade_open_date": "2024-01-02",
        "trade_open_price": 10.0,
        "non_executable_next_open": False,
        "non_executable_reason": "",
        "limit_threshold_status": "main_board_10pct",
    }
    labels = pipeline.LabelParams(
        confirm_horizon=20,
        confirm_upper=0.12,
        confirm_lower=-0.08,
        failure_horizon=10,
        failure_lower=-0.10,
        continuous_horizons=(10, 20, 60),
        near_winner_horizon=120,
        near_winner_mfe_lower=0.30,
        near_winner_mfe_upper=0.50,
    )

    row = pipeline.label_row(
        entity_id="e1",
        event_type="E_S3",
        split="train",
        regime_bucket="risk_on",
        daily=frame,
        trade=trade,
        label_params=labels,
    )

    assert row["confirm_20_complete"]
    assert row["failure_10_complete"]
    assert not row["horizon_complete_60d"]
    assert row["forward_return_60d_status"] == "censored_incomplete_horizon"


def test_baseline_split_uses_baseline_t0_date() -> None:
    split = pipeline.SplitConfig(
        train_start="2017-01-03",
        train_end="2021-12-31",
        validation_start="2022-01-01",
        validation_end="2023-12-31",
        robustness_start="2024-01-01",
        latest_label_complete_t0_date="2025-12-31",
    )

    assert pipeline.split_for_t0("2022-01-03", split) == "validation"
    assert pipeline.split_for_t0("2024-01-02", split) == "robustness"


def test_baseline_timing_audit_includes_deterministic_diagnostic_policy() -> None:
    dates = pd.date_range("2021-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
    daily = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 30,
            "high": [10.4] * 30,
            "low": [9.8] * 30,
            "close": [10.1] * 30,
            "volume": [1000.0] * 30,
            "money": [10000.0] * 30,
            "factor": [1.0] * 30,
        }
    )
    baselines = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "baseline_id": ["b1__baseline_raw", "b1__baseline_false_repair_excluded"],
            "baseline_family": ["baseline_raw", "baseline_false_repair_excluded"],
            "anchor_pos": [1, 1],
            "anchor_date": ["2021-01-02", "2021-01-02"],
            "baseline_t0_pos": [3, 3],
            "baseline_t0_date": ["2021-01-04", "2021-01-04"],
            "split": ["train", "train"],
            "board_bucket": ["main_board", "main_board"],
            "is_st": [False, False],
            "market_regime_bucket": ["risk_on", "risk_on"],
            "false_repair_observed_asof_baseline_t0": [False, False],
        }
    )
    observed_labels = pd.DataFrame(
        {
            "event_id": baselines["baseline_id"],
            "non_executable_next_open": [False, False],
            "confirm_20_complete": [True, True],
            "failure_10_complete": [True, True],
            "confirm_20_label": [0, 0],
            "failure_10_label": [0, 0],
            "forward_return_20d": [0.01, 0.01],
            "main_label_complete": [True, True],
        }
    )
    event_params = pipeline.EventParams(
        prior_lookback_sessions=2,
        seed_low_lookback_sessions=2,
        anchor_search_horizon_sessions=10,
        rank_jump_threshold=0.05,
        rank_jump_window=2,
        persistence_window=2,
        persistence_floor=0.0,
        persistence_coverage=0.5,
        amount_ratio_20d_gate=1.5,
        plus20_threshold=0.2,
        continuation_window=2,
        continuation_rank_floor=0.0,
        continuation_rank_coverage=0.5,
        continuation_amount_floor=1.2,
        continuation_amount_coverage=0.5,
    )
    label_params = pipeline.LabelParams(
        confirm_horizon=20,
        confirm_upper=0.12,
        confirm_lower=-0.08,
        failure_horizon=10,
        failure_lower=-0.10,
        continuous_horizons=(10, 20, 60),
        near_winner_horizon=120,
        near_winner_mfe_lower=0.30,
        near_winner_mfe_upper=0.50,
    )
    split = pipeline.SplitConfig(
        train_start="2017-01-03",
        train_end="2021-12-31",
        validation_start="2022-01-01",
        validation_end="2023-12-31",
        robustness_start="2024-01-01",
        latest_label_complete_t0_date="2025-12-31",
    )

    audit = pipeline.build_baseline_timing_audit(
        baselines,
        observed_labels,
        daily_by_instrument={"SH600000": daily},
        event_params=event_params,
        false_params=pipeline.FalseRepairParams(-0.10, 0.05),
        label_params=label_params,
        split_config=split,
    )

    assert set(audit["baseline_t0_policy"]) == {
        "observed_failure_decision_date",
        "deterministic_max_horizon",
    }
    deterministic = audit.loc[
        (audit["baseline_t0_policy"] == "deterministic_max_horizon")
        & (audit["split"] == "all")
    ]
    assert not deterministic["policy_used_for_main_claim"].any()


def test_executability_audit_reports_year_and_limit_rule_counts() -> None:
    events = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "event_t0_date": ["2024-01-03", "2025-01-03"],
            "split": ["robustness", "robustness"],
            "board_bucket": ["main_board", "unknown"],
            "non_executable_next_open": [False, True],
            "limit_threshold_status": ["main_board_10pct", "limit_rule_unavailable"],
        }
    )
    labels = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "main_label_complete": [True, False],
        }
    )

    audit = pipeline.build_executability_audit(events, labels)

    assert "limit_rule_unavailable_count" in audit.columns
    assert {"2024", "2025"}.issubset(set(audit["year"].astype(str)))
    all_row = audit.loc[
        (audit["split"] == "all")
        & (audit["year"] == "all")
        & (audit["board_proxy"] == "all")
    ].iloc[0]
    assert all_row["executable_rate_denominator_count"] == 2
    assert all_row["executable_rate_numerator_count"] == 1
    assert all_row["limit_rule_unavailable_count"] == 1


def test_stats_row_exposes_executability_denominators() -> None:
    labels = pd.DataFrame(
        {
            "non_executable_next_open": [False, True],
            "confirm_20_complete": [True, False],
            "failure_10_complete": [True, False],
            "confirm_20_label": [1, pd.NA],
            "failure_10_label": [0, pd.NA],
            "forward_return_20d": [0.02, pd.NA],
            "main_label_complete": [True, False],
        }
    )

    row = pipeline.stats_row(labels, labels.iloc[:1], event_count=2, baseline_count=1)

    assert row["executable_rate_denominator_count"] == 2
    assert row["executable_rate_numerator_count"] == 1
