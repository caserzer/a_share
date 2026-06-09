from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
SPEC = importlib.util.spec_from_file_location(
    "reverse_lifecycle_pipeline", CODE_DIR / "pipeline.py"
)
assert SPEC is not None and SPEC.loader is not None
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)

ExtractionParams = pipeline.ExtractionParams
MatchConfig = pipeline.MatchConfig
SplitConfig = pipeline.SplitConfig
cluster_non_chain_direct_overlap = pipeline.cluster_non_chain_direct_overlap
compute_stock_features = pipeline.compute_stock_features
build_aligned_panel = pipeline.build_aligned_panel
evaluate_sequence = pipeline.evaluate_sequence
extract_candidate_lows = pipeline.extract_candidate_lows
false_repair_metrics = pipeline.false_repair_metrics
first_moving_average_reclaim = pipeline.first_moving_average_reclaim
market_regime_bucket = pipeline.market_regime_bucket
match_controls = pipeline.match_controls
summarize_continuous_dominance = pipeline.summarize_continuous_dominance
split_for_date = pipeline.split_for_date


def test_non_chain_direct_overlap_keeps_abc_boundary_separate() -> None:
    intervals = pd.DataFrame(
        {
            "start_pos": [0, 8, 11],
            "end_pos": [10, 12, 13],
        }
    )

    clusters = cluster_non_chain_direct_overlap(intervals)

    assert list(clusters) == [0, 0, 1]


def test_candidate_extraction_marks_high_at_horizon_boundary() -> None:
    dates = pd.date_range("2024-01-01", periods=12, freq="D").strftime("%Y-%m-%d")
    features = pd.DataFrame(
        {
            "date": dates,
            "low": [10, 9, 8, 7, 5, 6, 7, 8, 9, 10, 9, 8],
            "high": [10, 9, 8, 7, 5.5, 6, 7, 8, 10, 9, 9, 8],
        }
    )
    params = ExtractionParams(
        local_low_window_sessions=1,
        prior_lookback_sessions=3,
        forward_horizon_sessions=4,
        big_winner_mfe_threshold=0.50,
    )

    candidates = extract_candidate_lows(
        features, membership_dates=set(dates), params=params
    )

    low = candidates.loc[candidates["candidate_low_date"] == "2024-01-05"].iloc[0]
    assert low["mfe_120"] == pytest.approx(1.0)
    assert bool(low["high_at_horizon_boundary"])


def test_first_ema60_reclaim_uses_asof_close_only_and_bounds() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=6, freq="D").strftime("%Y-%m-%d"),
            "close": [10.0, 9.0, 8.0, 7.0, 8.1, 9.0],
            "ema60": [np.nan, np.nan, 9.0, 8.0, 8.0, 8.5],
        }
    )

    pos, reason = first_moving_average_reclaim(
        frame, start_pos=2, end_pos=4, ma_column="ema60"
    )
    assert pos == 4
    assert reason == "not_missing"

    bounded_pos, bounded_reason = first_moving_average_reclaim(
        frame, start_pos=2, end_pos=3, ma_column="ema60"
    )
    assert bounded_pos is None
    assert bounded_reason == "missing_event_absent"


def test_vwap_qfq_adjustment_and_unavailability_are_separate() -> None:
    dates = pd.date_range("2024-01-01", periods=25, freq="D").strftime("%Y-%m-%d")
    daily = pd.DataFrame(
        {
            "date": dates,
            "open": [21.0] * 25,
            "high": [23.0] * 25,
            "low": [20.0] * 25,
            "close": [22.0] * 25,
            "volume": [100.0] * 25,
            "money": [1000.0] * 25,
            "turnover_rate": [0.01] * 25,
            "factor": [2.0] * 25,
        }
    )
    daily.loc[24, "volume"] = 0.0

    features = compute_stock_features(daily)

    assert features.loc[20, "qfq_daily_vwap"] == pytest.approx(20.0)
    assert features.loc[20, "close_to_derived_daily_vwap"] == pytest.approx(0.10)
    assert bool(features.loc[20, "derived_daily_vwap_available"])
    assert features.loc[20, "derived_daily_vwap_missing_reason"] == "not_missing"
    assert not bool(features.loc[24, "derived_daily_vwap_available"])
    assert pd.isna(features.loc[24, "close_to_derived_daily_vwap"])
    assert features.loc[24, "derived_daily_vwap_missing_reason"] == "missing_source_field"

    blocked = compute_stock_features(daily, vwap_source_units_compatible=False)
    assert not bool(blocked.loc[20, "derived_daily_vwap_available"])
    assert pd.isna(blocked.loc[20, "close_to_derived_daily_vwap"])
    assert blocked.loc[20, "derived_daily_vwap_missing_reason"] == "missing_unit_incompatible"


def test_aligned_panel_retains_feature_missing_reasons_and_out_of_coverage() -> None:
    dates = pd.date_range("2024-01-01", periods=3, freq="D").strftime("%Y-%m-%d")
    daily = pd.DataFrame(
        {
            "date": dates,
            "close_to_ema20": [np.nan, 0.01, 0.02],
            "derived_daily_vwap_available": [False, True, True],
            "derived_daily_vwap_price_basis": ["", "qfq", "qfq"],
            "derived_daily_vwap_missing_reason": [
                "missing_source_field",
                "not_missing",
                "not_missing",
            ],
            "qfq_adjustment_factor_available": [True, True, True],
            "close_to_derived_daily_vwap": [np.nan, 0.01, 0.02],
        }
    )
    entities = pd.DataFrame(
        {
            "entity_id": ["e1"],
            "instrument": ["SH600000"],
            "group": ["winner"],
            "axis_date": ["2024-01-01"],
            "split": ["train"],
            "duration_bucket": ["fast"],
            "market_regime_bucket": ["risk_on"],
        }
    )

    panel = build_aligned_panel(
        entities,
        {"SH600000": daily},
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        shared_axis="shared_axis_low",
        relative_start=-1,
        relative_end=1,
    )

    minus_one = panel.loc[panel["relative_day"] == -1].iloc[0]
    zero = panel.loc[panel["relative_day"] == 0].iloc[0]
    assert minus_one["close_to_ema20_missing_reason"] == "missing_out_of_coverage"
    assert zero["close_to_derived_daily_vwap_missing_reason"] == "missing_source_field"
    assert zero["axis_regime_bucket"] == "risk_on"


def test_market_regime_bucket_rules() -> None:
    assert market_regime_bucket(0.01, -0.05) == "risk_on"
    assert market_regime_bucket(-0.01, -0.12) == "risk_off"
    assert market_regime_bucket(0.01, -0.12) == "transition"
    assert market_regime_bucket(np.nan, -0.12) == "missing_insufficient_lookback"


def _sequence_frame() -> pd.DataFrame:
    rows = 140
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows, freq="D").strftime("%Y-%m-%d"),
            "close": np.linspace(10.0, 20.0, rows),
            "low": np.linspace(9.8, 19.8, rows),
            "high": np.linspace(10.2, 20.2, rows),
            "ema60": np.linspace(10.5, 18.0, rows),
            "amount_ratio_20d": [1.0] * rows,
            "close_to_derived_daily_vwap": [np.nan] * rows,
            "close_position_in_range": [0.4] * rows,
            "stock_vs_market_20d": [0.0] * rows,
            "atr_20_pct": [0.03] * rows,
            "gap_fade_flag": [0.0] * rows,
            "upper_shadow_pct": [0.02] * rows,
            "market_regime_bucket": ["risk_on"] * rows,
        }
    )
    frame.loc[9, "close"] = 9.0
    frame.loc[9, "ema60"] = 10.0
    frame.loc[10, "close"] = 10.5
    frame.loc[10, "ema60"] = 10.0
    frame.loc[11, "amount_ratio_20d"] = 1.6
    frame.loc[11, "close_position_in_range"] = 0.7
    return frame


def test_sequence_order_constraints_use_post_repair_confirmation() -> None:
    frame = _sequence_frame()

    passed, completion_date, reason = evaluate_sequence(
        "S2_repair_money_vwap_v0", frame, axis_pos=8, horizon_pos=60
    )

    assert passed
    assert completion_date == "2024-01-12"
    assert reason == "not_missing"


def test_sequence_forbidden_distribution_blocks_s5_variant() -> None:
    frame = _sequence_frame()
    frame["amount_ratio_20d"] = 1.0
    frame.loc[8, "amount_ratio_20d"] = 1.6
    frame.loc[10, "gap_fade_flag"] = 1.0

    passed, _, reason = evaluate_sequence(
        "S5_money_no_distribution_v0", frame.iloc[:20].copy(), axis_pos=8, horizon_pos=15
    )

    assert not passed
    assert reason == "missing_event_absent"


def test_s6_continuation_uses_axis_low_price_basis() -> None:
    frame = _sequence_frame()
    frame.loc[8, "low"] = 8.0
    frame.loc[8, "close"] = 10.0
    frame.loc[12, "close"] = 9.7
    frame.loc[32, "amount_ratio_20d"] = 1.3

    passed, completion_date, reason = evaluate_sequence(
        "S6_continuation_discriminator_v0", frame, axis_pos=8, horizon_pos=60
    )

    assert passed
    assert completion_date == "2024-02-02"
    assert reason == "not_missing"


def test_factor_dominance_emits_regime_and_duration_conditioned_rows() -> None:
    panel = pd.DataFrame(
        {
            "group": ["winner", "winner", "control", "control"],
            "shared_axis": ["shared_axis_low"] * 4,
            "relative_day": [0] * 4,
            "split": ["train", "validation", "train", "validation"],
            "axis_regime_bucket": ["risk_on", "risk_off", "risk_on", "risk_off"],
            "duration_bucket": ["fast", "long", "fast", "long"],
            "return_20d": [0.2, 0.1, 0.0, -0.1],
        }
    )

    dominance = summarize_continuous_dominance(
        panel,
        shared_axis="shared_axis_low",
        relative_days=[0],
        thresholds={
            "min_feature_non_missing_coverage_for_claim": 0.0,
            "standardized_mean_difference_gate": 0.25,
            "lift_gate": 1.25,
            "absolute_rate_difference_gate": 0.05,
        },
    )

    rows = dominance.loc[dominance["feature"] == "return_20d"]
    assert ((rows["regime_bucket"] == "risk_on") & (rows["duration_bucket"] == "all")).any()
    assert ((rows["regime_bucket"] == "all") & (rows["duration_bucket"] == "fast")).any()
    assert (
        (rows["split"] == "validation")
        & (rows["regime_bucket"] == "risk_off")
        & (rows["duration_bucket"] == "all")
    ).any()


def test_false_repair_metrics_report_10d_and_20d_failure_windows() -> None:
    dates = pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d")
    frame = pd.DataFrame(
        {
            "date": dates,
            "low": [10.0] * 40,
            "high": [10.5] * 40,
            "close": [10.0] * 40,
        }
    )
    frame.loc[12, "close"] = 12.0
    frame.loc[15, "low"] = 10.7

    metrics = false_repair_metrics(frame, "2024-01-06", "2024-01-13")

    assert metrics["control_is_false_repair_10d"]
    assert metrics["control_is_false_repair_20d"]
    assert metrics["false_repair_drawdown_anchor_to_plus_10d"] <= -0.10
    assert metrics["false_repair_missing_reason"] == "not_missing"


def test_same_week_matching_marks_cross_split_boundary_unusable() -> None:
    winners = pd.DataFrame(
        {
            "episode_id": ["w1"],
            "instrument": ["SH600000"],
            "episode_low_date": ["2021-12-31"],
            "split": ["train"],
            "board_bucket": ["main_board"],
            "market_cap_bucket": ["q3"],
            "liquidity_bucket": ["q3"],
            "prior_return_20d_bucket": ["q3"],
            "prior_return_60d_bucket": ["q3"],
            "prior_drawdown_bucket": ["q3"],
            "volatility_bucket": ["q3"],
        }
    )
    controls = pd.DataFrame(
        {
            "control_candidate_id": ["c1"],
            "instrument": ["SH600001"],
            "candidate_low_date": ["2022-01-01"],
            "split": ["validation"],
            "board_bucket": ["main_board"],
            "market_cap_bucket": ["q3"],
            "liquidity_bucket": ["q3"],
            "prior_return_20d_bucket": ["q3"],
            "prior_return_60d_bucket": ["q3"],
            "prior_drawdown_bucket": ["q3"],
            "volatility_bucket": ["q3"],
        }
    )

    matches, audit = match_controls(
        winners,
        controls,
        winner_id_col="episode_id",
        control_id_col="control_candidate_id",
        winner_date_col="episode_low_date",
        control_date_col="candidate_low_date",
        match_axis="shared_axis_low",
        config=MatchConfig(),
    )

    assert matches.empty
    assert audit.loc[0, "unmatched_reason"] == "cross_split_boundary_unusable"
    assert audit.loc[0, "cross_split_boundary_unusable_count"] == 1


def test_split_assignment_uses_episode_low_date_and_latest_complete_date() -> None:
    split_config = SplitConfig(latest_label_complete_low_date="2025-12-31")

    assert split_for_date("2021-12-31", split_config) == "train"
    assert split_for_date("2022-01-01", split_config) == "validation"
    assert split_for_date("2024-01-02", split_config) == "robustness"
    assert split_for_date("2026-01-02", split_config) == "outside_split"
