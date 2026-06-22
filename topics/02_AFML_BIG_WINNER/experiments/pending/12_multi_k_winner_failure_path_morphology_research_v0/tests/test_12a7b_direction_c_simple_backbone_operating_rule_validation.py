from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7b_direction_c_simple_backbone_operating_rule_validation.py"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A7b_direction_c_simple_backbone_operating_rule_validation"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "12A7b_direction_c_simple_backbone_operating_rule_validation"
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "simple_backbone_operating_rule_validation_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A7b_direction_c_simple_backbone_operating_rule_validation_manifest.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7b_direction_c", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def base_config() -> dict:
    return {
        "random_baseline": {
            "min_random_seed_n": 2,
            "retention_rank_columns": ["replacement_draw_index", "sample_draw_id", "instrument", "random_trade_open_date", "path_key"],
        },
        "bootstrap": {
            "seed": 7,
            "n_resamples": 20,
            "ci_low_q": 0.025,
            "ci_high_q": 0.975,
            "bootstrap_min_valid_replicates": 10,
        },
        "gates": {
            "train_selected_n_min": 2,
            "train_rank_evaluable_n_min": 3,
            "train_denominator_positive_n_min": 1,
            "train_delta_vs_random_p50_max": -0.02,
            "selected_n_min": 2,
            "denominator_positive_n_min": 1,
            "delta_vs_random_p50_max": -0.02,
            "selected_budget_total_max": 0.60,
            "budget_abs_delta_rank_evaluable_vs_X_max": 0.10,
            "rank_not_evaluable_rate_max": 0.05,
            "low_capacity_delta_vs_simple_backbone_max": -0.01,
            "complex_delta_near_miss_guard": 0.005,
        },
    }


def test_train_selection_keeps_random_uplift_as_hard_gate():
    runner = load_runner()
    config = base_config()
    curve = pd.DataFrame(
        [
            {
                "split": "train",
                "rule_id": "a",
                "feature_list": "volatility_20d",
                "stage1_budget_X": 0.3,
                "selected_n": 10,
                "rank_evaluable_n": 20,
                "denominator_positive_n": 5,
                "selected_fast_fail_rate": 0.10,
                "delta_vs_random_p50": -0.01,
            },
            {
                "split": "train",
                "rule_id": "b",
                "feature_list": "volatility_60d",
                "stage1_budget_X": 0.4,
                "selected_n": 10,
                "rank_evaluable_n": 20,
                "denominator_positive_n": 5,
                "selected_fast_fail_rate": 0.12,
                "delta_vs_random_p50": -0.03,
            },
        ]
    )

    selected = runner.train_selection(curve, config).iloc[0]

    assert selected["rule_id"] == "b"
    assert selected["selection_status"] == "selected_train_frozen"


def test_random_replay_requires_exact_cell_counts_for_valid_seeds():
    runner = load_runner()
    config = base_config()
    selection = pd.DataFrame(
        {
            "split": ["train", "train", "validation"],
            "board_bucket": ["main", "main", "main"],
            "calendar_month": ["2020-01", "2020-01", "2020-02"],
            "selected_flag": [True, True, True],
            "rule_id": ["rule"] * 3,
            "rule_family": ["single_feature_backbone"] * 3,
            "validation_phase": ["phase_1_single_feature_backbone"] * 3,
            "feature_list": ["volatility_20d"] * 3,
            "stage1_budget_X": [0.3] * 3,
        }
    )
    random = pd.DataFrame(
        [
            {
                "seed": seed,
                "split": split,
                "board_bucket": "main",
                "calendar_month": month,
                "path_key": f"{seed}_{split}_{i}",
                "instrument": "AAA",
                "random_trade_open_date": "2020-01-02",
                "replacement_draw_index": i,
                "sample_draw_id": i,
                "sample_weight": 1.0,
                "random_fast_fail_read_status": "pass",
                "random_fast_fail_target": i == 0,
            }
            for seed in [1, 2]
            for split, month, n in [("train", "2020-01", 3), ("validation", "2020-02", 2)]
            for i in range(n)
        ]
    )

    selected, audit, quant, status = runner.random_replay(selection, random, config)

    assert status == "pass"
    assert audit["sampled_random_n"].min() >= 1
    assert set(quant["split"]) == {"all", "train", "validation", "robustness"}
    assert len(selected) == 6


def test_phase1_support_gate_includes_rank_evaluable_budget_drift():
    runner = load_runner()
    config = base_config()
    row = pd.Series(
        {
            "selected_n": 300,
            "denominator_positive_n": 30,
            "bootstrap_replicate_valid_n": 20,
            "delta_vs_random_p50": -0.05,
            "delta_vs_random_p50_ci95_high": -0.01,
            "selected_budget_total": 0.35,
            "selected_fast_fail_rate": 0.10,
            "base_fast_fail_rate": 0.20,
            "random_p50": 0.18,
        }
    )
    drift = pd.Series({"budget_abs_delta_rank_evaluable_vs_X": 0.20, "rank_not_evaluable_rate": 0.01})

    reasons = runner.phase1_support_reasons(row, drift, config)

    assert "budget_abs_delta_rank_evaluable_vs_X_above_max" in reasons


def test_selection_from_rank_respects_descending_orientation():
    runner = load_runner()
    ranked = pd.DataFrame(
        {
            "meta_event_id": ["a", "b", "c"],
            "rank_status": ["rank_evaluable", "rank_evaluable", "rank_evaluable"],
            "rank_percentile": [0.1, 0.7, 0.9],
        }
    )

    selected = runner.selection_from_rank(
        ranked,
        rule_id="desc_rule",
        rule_family="single_feature_backbone",
        validation_phase="unit_test",
        feature_list=["distance_to_120d_low"],
        orientation={"distance_to_120d_low": "desc"},
        x=0.3,
        score_col="distance_to_120d_low",
    )

    assert selected["selected_flag"].tolist() == [False, True, True]


def test_stability_slices_reports_random_p50_and_weak_status():
    runner = load_runner()
    config = base_config()
    selection = pd.DataFrame(
        {
            "split": ["robustness"] * 110,
            "calendar_year": ["2024"] * 110,
            "board_bucket": ["main"] * 110,
            "primary_family_id": ["C0"] * 110,
            "calendar_month": ["2024-01"] * 110,
            "rank_status": ["rank_evaluable"] * 110,
            "selected_flag": [True] * 100 + [False] * 10,
            "stage_1_fast_fail_target": [True] * 20 + [False] * 80 + [True] * 10,
            "instrument": [f"AAA{i:03d}" for i in range(110)],
            "event_t0_date": ["2024-01-02"] * 110,
            "meta_event_id": [f"e{i:03d}" for i in range(110)],
        }
    )

    stability = runner.stability_slices(selection, config)
    split_row = stability.loc[stability["slice_type"].eq("split")].iloc[0]

    assert pd.notna(split_row["random_p50"])
    assert pd.notna(split_row["delta_vs_random_p50"])
    assert split_row["direction_status"] in {"pass", "weak", "fail"}


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "resolved_path", "row_count", "sha256", "schema_status", "read_status"},
        "scope_universe_audit.csv": {"scope_id", "included_event_n", "source_arm_is_c0_rate", "market_regime_risk_on_rate"},
        "simple_backbone_train_selection.csv": {"selection_status", "phase_1_selected_tuple_frozen", "tie_break_path"},
        "simple_backbone_candidate_curve.csv": {"rule_id", "feature_list", "stage1_budget_X", "delta_vs_random_p50"},
        "simple_backbone_operating_point_readout.csv": {
            "rule_id",
            "complex_model_matched_rate",
            "delta_vs_random_p50_ci95_high",
            "delta_vs_complex_model_ci95_high",
        },
        "simple_backbone_budget_drift_audit.csv": {"rule_id", "budget_abs_delta_rank_evaluable_vs_X", "rank_not_evaluable_rate"},
        "simple_backbone_random_same_budget_audit.csv": {
            "rule_id",
            "requested_selected_n",
            "sampled_random_n",
            "path_label_join_status",
            "cache_key_unique_status",
        },
        "complex_model_matched_comparator.csv": {
            "complex_model_matched_rate",
            "complex_score_source_caveat",
            "complex_comparator_status",
        },
        "low_capacity_monotone_model_card.csv": {"rule_id", "weight_json", "all_monotone_additive_score_constraints_satisfied"},
        "low_capacity_monotone_readout.csv": {
            "rule_id",
            "simple_backbone_matched_rate",
            "delta_vs_simple_backbone_ci95_high",
        },
        "backbone_stability_slice_audit.csv": {"slice_type", "selected_fast_fail_rate", "random_p50", "direction_status"},
        "stage2_diagnostic_backbone_readout.csv": {
            "diagnostic_readout",
            "stage_2_diagnostic_only",
            "not_allowed_for_12A7b_decision_state",
            "delta_vs_complex_stage2_ci95_high",
        },
        "direction_c_decision.csv": {"decision_state", "phase_2_execution_policy", "robustness_budget_abs_delta_rank_evaluable_vs_X"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    assert (LOCAL_CACHE_DIR / "simple_backbone_score_matrix.parquet").exists()
    assert (LOCAL_CACHE_DIR / "bootstrap_replicates.parquet").exists()
    assert REPORT_PATH.exists()
    assert MANIFEST_PATH.exists()

    decision = pd.read_csv(TABLE_DIR / "direction_c_decision.csv").iloc[0]
    assert decision["phase_2_execution_policy"] == "mandatory_after_phase_1_pass"
    assert decision["phase_2_enabled"] in {True, "True", "true", 1}
    stage2 = pd.read_csv(TABLE_DIR / "stage2_diagnostic_backbone_readout.csv")
    assert {
        "ground_truth_no_fast_fail_survivor_readout",
        "stage1_simple_backbone_chained_survivor_readout",
        "matched_random_same_budget_readout",
        "simple_stage2_backbone_vs_complex_stage2_readout",
    }.issubset(set(stage2["diagnostic_readout"]))
