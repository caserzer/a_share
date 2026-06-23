from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7g_vol_scaled_label_panel_c0_separability_triage.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7g_vol_scaled_label_panel_c0_separability_triage", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_barrier_traversal_same_bar_conflict_is_lower_first(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "open": [10.0, 10.0, 10.0],
            "high": [12.0, 10.0, 10.0],
            "low": [9.0, 10.0, 10.0],
            "close": [10.0, 10.0, 10.0],
            "money": [1.0, 1.0, 1.0],
            "turnover_rate": [0.1, 0.1, 0.1],
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    cache = runner.StockDailyCache(qfq_dir)
    frame = pd.DataFrame({"instrument": ["S1"], "reference_pos": [0], "reference_price": [10.0]})
    spec = {"label_id": "fixed_U20_L10_H2", "label_type": "fixed_anchor", "upper_barrier": 0.20, "lower_barrier": -0.10, "horizon_sessions": 2}

    label = runner.compute_label(frame, spec, cache, "reference_pos", "reference_price")

    assert bool(label.iloc[0]["horizon_complete"])
    assert bool(label.iloc[0]["same_bar_conflict"])
    assert bool(label.iloc[0]["lower_first"])
    assert not bool(label.iloc[0]["upper_first"])
    assert not bool(label.iloc[0]["winner_positive"])


def test_split_boundary_assigns_gap_rows_outside_model_splits():
    runner = load_runner()
    boundary = pd.DataFrame(
        {
            "eval_split": ["validation", "robustness"],
            "train_max_event_t0_date": ["2021-12-31", "2021-12-31"],
            "eval_min_event_t0_date": ["2022-01-04", "2024-03-01"],
            "split_time_boundary_gate_pass": [True, True],
        }
    )
    _info, assign = runner.split_boundary_info(boundary)

    assert assign("2021-12-31") == "train"
    assert assign("2022-01-03") == "boundary_gap_excluded"
    assert assign("2022-01-04") == "validation"
    assert assign("2024-03-01") == "robustness"


def test_stage1_reconstruction_requires_row_level_rank_match():
    runner = load_runner()
    c0 = pd.DataFrame({"meta_event_id": ["a", "b", "c"], "split": ["train", "train", "validation"]})
    score = pd.DataFrame(
        {
            "meta_event_id": ["a", "b", "c"],
            "volatility_20d__rank_percentile": [0.10, 0.40, 0.20],
            "volatility_20d__rank_status": ["rank_evaluable", "rank_evaluable", "rank_evaluable"],
        }
    )
    upstream = pd.DataFrame(
        {
            "stage1_X": [0.30, 0.30, 0.30, 0.30],
            "split": ["all", "train", "validation", "robustness"],
            "stage1_selected_n": [2, 1, 1, 0],
            "stage1_rank_evaluable_n": [3, 2, 1, 0],
        }
    )

    audit, selected = runner.stage1_reconstruction(c0, score, upstream)

    assert selected.tolist() == [True, False, True]
    assert audit["stage1_anchor_reconstruction_status"].eq("pass").all()


def test_label_selection_prefers_fixed_when_vol_scaled_is_worse():
    runner = load_runner()
    summary = pd.DataFrame(
        [
            {
                "label_id": "vol20_kup1p0_kdn1p0_H20",
                "label_type": "vol_scaled",
                "label_eligibility_status": "eligible",
                "label_stability_score": 0.70,
                "label_base_rate_dispersion": 0.09,
                "train_same_bar_conflict_rate": 0.02,
            },
            {
                "label_id": "fixed_U20_L10_H20",
                "label_type": "fixed_anchor",
                "label_eligibility_status": "eligible",
                "label_stability_score": 0.80,
                "label_base_rate_dispersion": 0.02,
                "train_same_bar_conflict_rate": 0.01,
            },
        ]
    )
    thresholds = {
        "max_label_stability_score_tolerance": 0.02,
        "max_label_base_rate_dispersion_tolerance": 0.02,
        "max_same_bar_conflict_rate_tolerance": 0.005,
    }

    selected, audit = runner.choose_label(summary, thresholds)

    assert selected["label_id"] == "fixed_U20_L10_H20"
    assert audit.loc[audit["selected_label_flag"], "selection_reason"].iloc[0] == "fixed_anchor_more_stable"


def test_fast_label_summary_matches_compute_label_summary(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            "open": [10.0, 10.0, 10.0, 10.0],
            "high": [10.5, 12.0, 10.2, 10.1],
            "low": [9.8, 9.5, 9.9, 9.7],
            "close": [10.0, 11.0, 10.0, 9.8],
            "money": [1.0, 1.0, 1.0, 1.0],
            "turnover_rate": [0.1, 0.1, 0.1, 0.1],
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    cache = runner.StockDailyCache(qfq_dir)
    frame = pd.DataFrame(
        {
            "instrument": ["S1", "S1"],
            "split": ["train", "train"],
            "label_selection_scope": [True, True],
            "entry_pos": [0, 1],
            "entry_price": [10.0, 10.0],
            "calendar_year": [2020, 2020],
            "board_bucket": ["main_board", "main_board"],
            "market_regime_bucket": ["risk_on", "risk_on"],
        }
    )
    spec = {
        "label_id": "fixed_U15_L10_H2",
        "label_type": "fixed_anchor",
        "upper_barrier": 0.15,
        "lower_barrier": -0.10,
        "horizon_sessions": 2,
    }
    thresholds = {
        "target_label_base_rate": 0.15,
        "min_train_positive_n": 1,
        "min_label_base_rate": 0.0,
        "max_label_base_rate": 1.0,
        "max_same_bar_conflict_rate": 1.0,
        "max_label_base_rate_dispersion": 1.0,
        "min_label_stability_slice_n": 1,
        "min_label_stability_slice_positive_n": 1,
    }

    slow = runner.label_summary_for_spec(frame, runner.compute_label(frame, spec, cache, "entry_pos", "entry_price"), spec, thresholds)
    fast = runner.label_summary_grid_fast(frame, [spec], cache, thresholds, "entry_pos", "entry_price").iloc[0].to_dict()

    for key in [
        "train_denominator_n",
        "train_horizon_complete_n",
        "train_winner_positive_n",
        "train_winner_base_rate",
        "train_same_bar_conflict_rate",
        "label_base_rate_dispersion",
        "label_eligibility_status",
    ]:
        assert fast[key] == slow[key]
