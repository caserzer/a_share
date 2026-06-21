from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.py"
TABLE_DIR = (
    EXPERIMENT_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "12A6c_two_stage_fast_fail_rejector_continuation_feasibility"
)
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "two_stage_fast_fail_rejector_continuation_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a6c_two_stage", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStockDailyCache:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames

    def get(self, instrument: str) -> pd.DataFrame | None:
        return self.frames.get(str(instrument))


def base_config() -> dict:
    return {
        "stage_2": {
            "horizon_grid_h2": [20],
            "upper_barrier_grid": [0.20],
            "lower_barrier_grid": [-0.10],
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
    }


def test_stage2_horizon_is_reference_pos_through_reference_plus_h2_inclusive():
    runner = load_runner()
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=42).strftime("%Y-%m-%d"),
            "open": [10.0] * 42,
            "high": [10.0] * 41 + [12.1],
            "low": [9.8] * 42,
            "close": [10.0] * 42,
            "volume": [1000.0] * 42,
            "turnover_rate": [0.01] * 42,
        }
    )
    paths = pd.DataFrame([{"path_key": "p1", "instrument": "AAA", "entry_pos": 0, "entry_price": 10.0}])

    out = runner.build_stage2_path_cache(paths, FakeStockDailyCache({"AAA": daily}), base_config(), include_realized=False)

    assert bool(out.iloc[0]["stage_2_horizon_complete_20d"])
    assert bool(out.iloc[0]["continuation_U20_L10_H2_20"])

    missing_terminal = daily.iloc[:-1].copy()
    blocked = runner.build_stage2_path_cache(paths, FakeStockDailyCache({"AAA": missing_terminal}), base_config(), include_realized=False)
    assert not bool(blocked.iloc[0]["stage_2_horizon_complete_20d"])


def test_stage2_same_bar_lower_first_blocks_continuation():
    runner = load_runner()
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=42).strftime("%Y-%m-%d"),
            "open": [10.0] * 42,
            "high": [10.0] * 42,
            "low": [9.8] * 42,
            "close": [10.0] * 42,
        }
    )
    daily.loc[23, "high"] = 12.1
    daily.loc[23, "low"] = 8.9
    paths = pd.DataFrame([{"path_key": "p1", "instrument": "AAA", "entry_pos": 0, "entry_price": 10.0}])

    out = runner.build_stage2_path_cache(paths, FakeStockDailyCache({"AAA": daily}), base_config(), include_realized=False)

    assert bool(out.iloc[0]["stage_2_horizon_complete_20d"])
    assert not bool(out.iloc[0]["continuation_U20_L10_H2_20"])


def test_fixed_budget_selection_uses_train_frozen_threshold_and_does_not_reselect_oos_budget():
    runner = load_runner()
    frame = pd.DataFrame(
        {
            "model_id": ["m"] * 20,
            "split": ["train"] * 10 + ["robustness"] * 10,
            "score": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] + [0.9] * 10,
            "instrument": [f"S{i}" for i in range(20, 0, -1)],
            "event_t0_date": ["2020-01-01"] * 20,
            "entry_date": ["2020-01-02"] * 20,
            "meta_event_id": [f"e{i}" for i in range(20)],
            "path_key": [f"p{i}" for i in range(20)],
        }
    )

    selected, health = runner.assign_fixed_budget_flags(
        frame,
        score_col="score",
        flag_col="keep",
        budget=0.5,
        lower_is_better=True,
    )

    assert int(selected.loc[selected["split"].eq("train"), "keep"].sum()) == 5
    assert int(selected.loc[selected["split"].eq("robustness"), "keep"].sum()) == 0
    assert health.loc[health["split"].eq("train"), "budget_health"].iloc[0] == "pass"
    assert health.loc[health["split"].eq("robustness"), "budget_health"].iloc[0] == "fail"


def test_random_budget_selection_preserves_seed_cell_budget_and_rank_rule():
    runner = load_runner()
    c0 = pd.DataFrame(
        {
            "split": ["train"] * 4,
            "board_bucket": ["main"] * 4,
            "calendar_month": ["2020-01"] * 4,
            "keep": [True, True, False, False],
        }
    )
    random_rows = []
    for seed in [1, 2]:
        for draw in range(4):
            random_rows.append(
                {
                    "seed": seed,
                    "split": "train",
                    "board_bucket": "main",
                    "calendar_month": "2020-01",
                    "path_key": f"{seed}-{draw}",
                    "replacement_draw_index": draw,
                    "sample_draw_id": draw,
                    "instrument": "AAA",
                    "random_trade_open_date": "2020-01-02",
                    "sample_weight": 1.0,
                    "den": True,
                    "target": draw < 2,
                }
            )
    selected, audit = runner.random_budget_selection(
        pd.DataFrame(random_rows),
        c0,
        c0_flag_col="keep",
        random_denominator_col="den",
        target_col="target",
        config=base_config(),
    )

    assert len(selected) == 4
    assert selected.groupby("seed").size().to_dict() == {1: 2, 2: 2}
    assert set(audit["random_selected_n"]) == {2}
    assert audit["retention_rank_rule"].str.contains("replacement_draw_index").all()


def test_lightgbm_only_readout_cannot_produce_two_stage_supported():
    runner = load_runner()
    config = runner.load_yaml(EXPERIMENT_DIR / "configs" / "config_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.yaml")
    stage1 = pd.DataFrame(
        [
            {
                "model_id": "lightgbm_challenger_diagnostic_only",
                "split": "train",
                "stage1_keep_n": 1000,
                "fast_fail_abs_delta_vs_random_p50": -0.20,
                "fast_fail_abs_delta_vs_c0_baseline": -0.20,
                "stage1_keep_retention": 0.5,
                "model_minus_best_single_feature": -0.1,
            }
        ]
    )
    stage2 = pd.DataFrame()

    decision = runner.evaluate_decision(stage1, stage2, config, input_gate_pass=True)

    assert decision.iloc[0]["decision_state"] != "12A6c_two_stage_supported"


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "read_status", "schema_status", "sha256"},
        "two_stage_event_universe.csv.gz": {"meta_event_id", "instrument", "event_t0_date", "stage_1_fast_fail_target"},
        "two_stage_event_targets.csv.gz": {"meta_event_id", "stage_1_fast_fail_target", "stage_2_continuation_target"},
        "two_stage_feature_dictionary.csv": {"feature_name", "availability_time", "allowed_for_stage_1", "allowed_for_stage_2"},
        "two_stage_feature_pit_audit.csv": {"feature_name", "pit_status", "coverage_rate"},
        "realized_path_feature_redundancy_audit.csv": {"feature_name", "max_abs_redundancy_corr", "allowed_for_stage_2_after_audit"},
        "stage_threshold_health.csv": {"stage", "split", "model_id", "budget_health"},
        "stage_1_model_card.csv": {"stage", "model_id", "model_family", "feature_list_hash", "hyperparameter_json"},
        "stage_2_model_card.csv": {"stage", "model_id", "model_family", "feature_list_hash", "hyperparameter_json"},
        "stage_1_random_same_budget_audit.csv": {"stage", "seed", "model_budget", "random_selected_n"},
        "stage_2_random_same_budget_audit.csv": {"stage", "seed", "model_budget", "random_selected_n"},
        "stage_1_rejector_readout.csv": {"model_id", "split", "stage1_keep_fast_fail_rate", "stage_1_random_keep_fast_fail_rate_p50"},
        "stage_2_continuation_readout.csv": {"model_id", "split", "stage2_continue_continuation_rate", "stage_2_random_continuation_rate_given_survivor_p50"},
        "stage_2_ablation_readout.csv": {"model_id", "feature_group", "continuation_rate"},
        "two_stage_decision.csv": {"decision_state", "stage_1_status", "stage_2_status", "next_allowed_requirement"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    feature_matrix = pd.read_parquet(
        EXPERIMENT_DIR / "outputs" / "local_cache" / "12A6c_two_stage_fast_fail_rejector_continuation_feasibility" / "two_stage_feature_matrix.parquet"
    )
    assert not {
        "stage_1_fast_fail_target",
        "stage_2_continuation_target",
        "stage_2_evaluable",
        "stage_2_path_evaluable",
        "no_fast_fail_L10_H20",
    }.intersection(feature_matrix.columns)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "input_hashes" in manifest
    assert "fast_fail_decision" in manifest["input_hashes"]
    assert REPORT_PATH.exists()
    assert MANIFEST_PATH.exists()
