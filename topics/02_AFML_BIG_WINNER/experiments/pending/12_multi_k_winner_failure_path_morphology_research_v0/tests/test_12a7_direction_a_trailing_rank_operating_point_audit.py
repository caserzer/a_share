from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7_direction_a_trailing_rank_operating_point_audit.py"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A7_direction_a_trailing_rank_operating_point_audit"
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "trailing_rank_operating_point_validation_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A7_direction_a_trailing_rank_operating_point_audit_manifest.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7_trailing_rank", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def base_config() -> dict:
    return {
        "history_min_n": {
            "stage_1_global_min_history_n": 1,
            "stage_1_board_min_history_n": 99,
            "stage_2_global_min_history_n": 1,
            "stage_2_board_min_history_n": 99,
        },
        "primary_X_stage_1": 0.5,
        "primary_X_stage_2": 0.5,
        "models": {
            "primary_stage_1_model_id": "logistic_regression_l2",
            "primary_stage_2_model_id": "logistic_regression_l2",
        },
        "random_baseline": {
            "retention_rank_columns": [
                "replacement_draw_index",
                "sample_draw_id",
                "instrument",
                "random_trade_open_date",
                "path_key",
            ]
        },
        "single_feature_challenger": {"common_denominator_min_coverage": 0.95},
    }


def test_rolling_percentile_uses_prior_rows_inside_window_and_excludes_same_pos():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "meta_event_id": ["a", "b", "c", "d", "e"],
            "instrument": ["AAA"] * 5,
            "event_t0_date": ["2020-01-01"] * 5,
            "event_t0_pos": [1, 2, 5, 5, 6],
            "board_bucket": ["main"] * 5,
            "score": [0.1, 0.2, 0.4, 0.8, 0.6],
        }
    )
    policy = runner.HistoryPolicy("test_rolling_3", "rolling_sessions", 3, False)

    ranked = runner.rolling_percentiles(
        frame,
        score_col="score",
        pos_col="event_t0_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=1,
        board_min_history_n=99,
    ).set_index("meta_event_id")

    assert ranked.loc["a", "rank_status"] == "rank_not_evaluable"
    assert ranked.loc["c", "history_n"] == 1
    assert ranked.loc["c", "rank_percentile"] == 1.0
    assert ranked.loc["d", "history_n"] == 1
    assert ranked.loc["e", "history_n"] == 2
    assert ranked.loc["e", "rank_percentile"] == 0.5


def test_stage2_random_baseline_applies_random_stage1_keep_before_survivor_denominator():
    runner = load_runner()
    config = base_config()
    random = pd.DataFrame(
        [
            {
                "seed": 1,
                "split": "train",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "path_key": f"p{i}",
                "replacement_draw_index": i,
                "sample_draw_id": i,
                "instrument": "AAA",
                "random_trade_open_date": "2020-01-02",
                "sample_weight": 1.0,
                "random_stage_1_evaluable": True,
                "random_stage_1_fast_fail_target": False,
                "random_stage_2_evaluable": True,
                "random_stage_2_continuation_target": i == 0,
            }
            for i in range(4)
        ]
    )
    stage1_selection = pd.DataFrame(
        {
            "split": ["train"] * 4,
            "board_bucket": ["main"] * 4,
            "calendar_month": ["2020-01"] * 4,
            "selected_flag": [True, True, False, False],
        }
    )
    stage2_selection = pd.DataFrame(
        {
            "split": ["train", "train"],
            "board_bucket": ["main", "main"],
            "calendar_month": ["2020-01", "2020-01"],
            "selected_flag": [True, False],
            "history_policy_id": ["board_then_global_rolling_504_sessions"] * 2,
            "history_window_mode": ["rolling_sessions"] * 2,
            "trailing_history_window_sessions": [504] * 2,
            "stage1_budget_X": [0.5] * 2,
            "stage2_budget_X": [0.5] * 2,
        }
    )

    selected, audit, quant = runner.stage2_random_baseline(random, stage1_selection, stage2_selection, config)

    assert int(audit["random_stage1_keep_n"].iloc[0]) == 2
    assert int(audit["random_denominator_n"].iloc[0]) == 2
    assert int(audit["random_selected_n"].iloc[0]) == 1
    assert int(audit["model_rank_evaluable_n"].iloc[0]) == 2
    assert int(audit["random_positive_n"].iloc[0]) == 1
    assert len(selected) == 1
    assert not quant.empty


def test_readout_base_rate_uses_rank_evaluable_denominator():
    runner = load_runner()
    config = base_config()
    selection = pd.DataFrame(
        {
            "split": ["train", "train", "train"],
            "board_bucket": ["main"] * 3,
            "calendar_month": ["2020-01"] * 3,
            "rank_status": ["rank_evaluable", "rank_evaluable", "rank_not_evaluable"],
            "selected_flag": [True, False, False],
            "target": [False, True, True],
            "history_policy_id": ["board_then_global_rolling_504_sessions"] * 3,
            "history_window_mode": ["rolling_sessions"] * 3,
            "trailing_history_window_sessions": [504] * 3,
            "stage1_budget_X": [0.5] * 3,
            "stage2_budget_X": [pd.NA] * 3,
            "diagnostic_only_flag": [False] * 3,
        }
    )

    readout = runner.readout_rows_for_selection(selection, "stage_1", "target", "score", config)
    train = readout.loc[readout["split"].eq("train")].iloc[0]

    assert train["base_rate"] == 0.5
    assert train["denominator_positive_n"] == 2
    assert train["rank_evaluable_positive_n"] == 1


def test_single_feature_matched_replay_uses_model_selected_n_per_cell():
    runner = load_runner()
    config = base_config()
    model = pd.DataFrame(
        {
            "meta_event_id": [f"m{i}" for i in range(4)],
            "instrument": ["AAA"] * 4,
            "event_t0_date": ["2020-01-01"] * 4,
            "split": ["train"] * 4,
            "board_bucket": ["main"] * 4,
            "calendar_month": ["2020-01"] * 4,
            "rank_status": ["rank_evaluable"] * 4,
            "selected_flag": [True, True, False, False],
            "feature": [4.0, 3.0, 2.0, 1.0],
            "target": [False, True, False, False],
            "history_policy_id": ["board_then_global_rolling_504_sessions"] * 4,
            "history_window_mode": ["rolling_sessions"] * 4,
            "trailing_history_window_sessions": [504] * 4,
            "stage1_budget_X": [0.5] * 4,
            "stage2_budget_X": [pd.NA] * 4,
        }
    )
    feature_frame = model.copy()

    selected, readout = runner.matched_single_feature_replay(model, feature_frame, "feature", "asc", "stage_1", "target", config)

    train = readout.loc[readout["split"].eq("train")].iloc[0]
    assert int(train["matched_selected_n"]) == 2
    assert set(selected["meta_event_id"]) == {"m2", "m3"}


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "read_status", "schema_status", "sha256"},
        "score_reproduction_audit.csv": {"stage", "score_reproduction_status", "score_source_caveat"},
        "random_path_label_audit.csv": {"seed", "random_stage_1_evaluable_n", "random_stage_2_positive_n"},
        "trailing_rank_score_quality_metrics.csv": {"stage", "history_policy_id", "auc", "spearman_rank_ic"},
        "trailing_rank_operating_point_readout.csv": {
            "stage",
            "selected_n",
            "random_p50",
            "delta_vs_single_feature",
            "bootstrap_random_ci95_low",
            "bootstrap_random_ci95_high",
            "bootstrap_single_feature_ci95_low",
            "bootstrap_single_feature_ci95_high",
        },
        "trailing_rank_budget_drift_audit.csv": {"stage", "actual_budget_total", "budget_drift_status"},
        "trailing_rank_random_same_budget_audit.csv": {
            "stage",
            "model_rank_evaluable_n",
            "random_stage1_keep_n",
            "random_selected_n",
            "random_positive_n",
        },
        "trailing_rank_single_feature_challenger.csv": {"stage", "common_denominator_n", "matched_selected_n"},
        "trailing_rank_decile_lift_readout.csv": {"stage", "score_decile", "target_rate"},
        "trailing_rank_budget_curve_readout.csv": {"stage", "budget_tuple_role", "selected_n"},
        "diagnostic_lookahead_rank_upper_bar.csv": {"rank_method_id", "lookahead_rank_upper_bar", "not_allowed_for_decision"},
        "trailing_rank_decision.csv": {"decision_state", "primary_history_policy_id", "next_allowed_requirement"},
        "split_time_boundary_audit.csv": {"eval_split", "split_time_boundary_gate_pass"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    score_matrix = pd.read_parquet(
        EXPERIMENT_DIR / "outputs" / "local_cache" / "12A7_direction_a_trailing_rank_operating_point_audit" / "trailing_rank_score_matrix.parquet"
    )
    assert {"stage1_fast_fail_score", "stage2_continuation_score", "score_source_caveat"}.issubset(score_matrix.columns)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["decision_state"]
    assert "output_hashes" in manifest
    assert manifest["entrypoint_hash"]
    assert "local_cache_hashes" in manifest
    assert "score_matrix" in manifest["local_cache_hashes"]
    assert REPORT_PATH.exists()
