from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_15a_winner_episode_label_censoring_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_15a_winner_episode_label_censoring_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_qfq(path: Path, highs: list[float], closes: list[float] | None = None) -> None:
    closes = closes or [10.0] * len(highs)
    pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=len(highs)).strftime("%Y-%m-%d"),
            "open": [10.0] * len(highs),
            "high": highs,
            "low": [9.5] * len(highs),
            "close": closes,
            "volume": [1000.0] * len(highs),
            "money": [10000.0] * len(highs),
            "turnover_rate": [0.01] * len(highs),
        }
    ).to_csv(path, index=False)


def base_anchor() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": ["r1", "r2"],
            "instrument": ["S1", "S2"],
            "reference_date": ["2020-01-01", "2020-01-02"],
            "split_bucket": ["train", "train"],
            "board_bucket": ["main_board", "main_board"],
            "calendar_year": ["2020", "2020"],
            "reference_pos": [0, 1],
            "entry_date": ["2020-01-02", "2020-01-03"],
            "entry_pos": [1, 2],
            "entry_price": [10.0, 10.0],
            "winner_positive": [False, False],
            "horizon_complete": [True, True],
            "label_id": ["vol20d_kup2p0_kdn1p0_H20", "vol20d_kup2p0_kdn1p0_H20"],
            "volatility_20d": [0.01, 0.02],
            "volatility_60d": [0.02, 0.03],
            "max_drawdown_20d": [-0.05, -0.08],
            "max_drawdown_60d": [-0.10, -0.12],
            "ret_20d": [0.01, 0.02],
            "ret_60d": [0.03, 0.04],
            "distance_to_20d_high": [-0.01, -0.02],
            "distance_to_60d_high": [-0.03, -0.04],
            "distance_to_20d_low": [0.10, 0.11],
            "trend_ma_20_60_spread": [0.01, 0.02],
            "vol_compression_20d_60d": [0.20, 0.30],
            "rebound_from_20d_low": [0.10, 0.11],
        }
    )


def test_path_defined_label_keeps_slow_winner_and_censored_separate(tmp_path):
    runner = load_runner()
    qfq = tmp_path / "qfq"
    qfq.mkdir()
    highs = [10.1] * 320
    highs[151] = 15.2
    write_qfq(qfq / "S1.csv", highs)
    write_qfq(qfq / "S2.csv", [10.1] * 320)

    label = runner.build_path_defined_label_panel(base_anchor(), qfq)
    up50 = label.loc[label["threshold_id"].eq("up50pct")].set_index("row_id")

    assert bool(up50.loc["r1", "path_winner"])
    assert int(up50.loc["r1", "time_to_threshold_sessions"]) == 150
    assert bool(up50.loc["r1", "slow_winner_flag"])
    assert not bool(up50.loc["r1", "fixed120_winner"])
    assert not bool(up50.loc["r1", "confirmed_non_winner"])

    assert not bool(up50.loc["r2", "path_winner"])
    assert bool(up50.loc["r2", "is_censored"])
    assert bool(up50.loc["r2", "observed_non_hit_control_flag"])
    assert up50.loc["r2", "observed_non_hit_control_role"] == "readout_only_censored_control_not_negative"


def test_fixed120_only_without_valid_explanation_fails_rebuild_gate():
    runner = load_runner()
    label = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "split_bucket": ["train"],
            "path_winner": [False],
            "is_censored": [True],
            "confirmed_non_winner": [False],
            "observed_non_hit_control_flag": [False],
            "fixed120_horizon_complete": [True],
            "fixed120_winner": [True],
            "fixed120_only_winner_explanation_code": ["none"],
            "close_based_first_passage_offset": [pd.NA],
        }
    )

    audit = runner.label_rebuild_audit(label)
    row = audit.loc[audit["threshold_id"].eq("up50pct") & audit["split_bucket"].eq("train")].iloc[0]

    assert row["rebuild_status"] == "fail"
    assert int(row["fixed120_only_winner_n"]) == 1


def test_winner_set_uses_anchor_denominators_and_fixed120_complete_denominator():
    runner = load_runner()
    label = pd.DataFrame(
        {
            "threshold_id": ["up50pct", "up50pct", "up50pct"],
            "split_bucket": ["train", "train", "train"],
            "path_winner": [True, True, False],
            "is_censored": [False, False, True],
            "confirmed_non_winner": [False, False, False],
            "observed_non_hit_control_flag": [False, False, True],
            "fixed120_horizon_complete": [True, True, False],
            "fixed120_winner": [True, False, False],
            "volscaled_h20_horizon_complete": [True, True, True],
            "volscaled_h20_winner": [False, True, False],
            "slow_winner_flag": [False, True, False],
            "fast_winner_flag": [True, False, False],
        }
    )

    readout = runner.winner_set_difference(label)
    row = readout.loc[readout["threshold_id"].eq("up50pct") & readout["split_bucket"].eq("train")].iloc[0]

    assert int(row["record_n"]) == 3
    assert int(row["path_winner_n"]) == 2
    assert int(row["fixed120_horizon_complete_n"]) == 2
    assert row["fixed120_winner_rate"] == 0.5
    assert row["winner_set_difference_status"] == "pass"


def test_episode_overlap_uses_transitive_interval_merge():
    runner = load_runner()
    label = pd.DataFrame(
        {
            "threshold_id": ["up50pct"] * 4,
            "split_bucket": ["train"] * 4,
            "instrument": ["S1"] * 4,
            "path_winner": [True] * 4,
            "slow_winner_flag": [False, True, False, False],
            "episode_start_pos": [1, 5, 9, 30],
            "episode_threshold_pos": [6, 10, 12, 35],
        }
    )

    audit = runner.episode_overlap_density_audit(label)
    row = audit.loc[audit["threshold_id"].eq("up50pct") & audit["split_bucket"].eq("train")].iloc[0]

    assert int(row["approx_episode_cluster_n"]) == 2
    assert int(row["max_anchor_rows_per_episode_cluster"]) == 3


def test_native_adapter_consistency_fails_on_derived_field_drift():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "split": ["train"],
            "split_bucket": ["train"],
            "upper_barrier": [0.10],
            "upper_barrier_return": [0.11],
            "lower_barrier": [-0.05],
            "lower_barrier_return": [-0.05],
            "winner_positive": [True],
            "winner": [True],
            "horizon_close_return": [0.03],
            "terminal_return_20d": [0.03],
        }
    )

    status = runner.native_adapter_consistency_status(panel)

    assert status["status"] == "fail"
    assert status["mismatch_n"] == 1


def test_cache_position_rebuild_fails_on_entry_price_drift(tmp_path):
    runner = load_runner()
    qfq = tmp_path / "qfq"
    qfq.mkdir()
    write_qfq(qfq / "S1.csv", [10.1] * 5)
    panel = pd.DataFrame(
        {
            "instrument": ["S1"],
            "reference_date": ["2020-01-01"],
            "reference_pos": [0],
            "entry_date": ["2020-01-02"],
            "entry_pos": [1],
            "entry_price": [10.5],
        }
    )

    status = runner.cache_position_rebuild_status(panel, qfq)

    assert status["status"] == "fail"
    assert status["mismatch_n"] == 1
