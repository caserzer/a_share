from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7c_direction_e_stage2_decoupling_chained_readouts.py"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "12A7c_direction_e_stage2_decoupling_chained_readouts"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "12A7c_direction_e_stage2_decoupling_chained_readouts"
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "stage2_decoupling_chained_readouts_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "manifests" / "12A7c_direction_e_stage2_decoupling_chained_readouts_manifest.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7c_direction_e", RUNNER_PATH)
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
            "selected_n_min": 2,
            "denominator_positive_n_min": 1,
            "delta_vs_random_p50_min": 0.02,
            "delta_vs_single_feature_min": 0.01,
            "rank_not_evaluable_rate_max": 0.05,
            "budget_abs_delta_rank_evaluable_vs_X_max": 0.10,
        },
    }


def test_descending_rank_keeps_top_budget():
    runner = load_runner()
    out = runner.keep_mask_from_rank(
        pd.Series(["rank_evaluable", "rank_evaluable", "rank_evaluable"]),
        pd.Series([0.10, 0.72, 0.91]),
        "desc",
        0.30,
    )

    assert out.tolist() == [False, True, True]


def test_decision_guard_demotes_chained_pass_when_decoupled_not_supported():
    runner = load_runner()
    config = base_config()
    anchor = pd.DataFrame(
        [
            {
                "stage1_anchor_rule_id": "simple_a",
                "stage1_anchor_feature": "volatility_20d",
                "stage1_anchor_orientation": "asc",
                "stage1_anchor_X": 0.30,
            }
        ]
    )
    dec_sel = pd.DataFrame([{"candidate_id": "single_a", "candidate_family": "single_feature_stage2", "stage2_budget_X": 0.3}])
    chain_sel = pd.DataFrame([{"candidate_id": "single_b", "candidate_family": "single_feature_stage2", "stage2_budget_X": 0.3}])
    readout = pd.DataFrame(
        [
            {
                "denominator_type": "ground_truth_no_fast_fail_survivor",
                "candidate_id": "single_a",
                "stage2_budget_X": 0.3,
                "split": "robustness",
                "candidate_family": "single_feature_stage2",
                "selected_n": 10,
                "denominator_positive_n": 5,
                "bootstrap_replicate_valid_n": 20,
                "delta_vs_random_p50": -0.01,
                "delta_vs_random_p50_ci95_low": -0.02,
                "rank_not_evaluable_rate": 0.0,
                "readout_status": "ok",
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "candidate_id": "single_b",
                "stage2_budget_X": 0.3,
                "split": "robustness",
                "candidate_family": "single_feature_stage2",
                "selected_n": 10,
                "denominator_positive_n": 5,
                "bootstrap_replicate_valid_n": 20,
                "delta_vs_random_p50": 0.05,
                "delta_vs_random_p50_ci95_low": 0.01,
                "rank_not_evaluable_rate": 0.0,
                "budget_abs_delta_rank_evaluable_vs_X": 0.0,
                "readout_status": "ok",
            },
        ]
    )
    opp = pd.DataFrame([{"split": "robustness", "stage1_defense_opportunity_cost_status": "no_material_continuation_cost"}])

    decision = runner.decision_row(True, "", True, anchor, dec_sel, chain_sel, readout, opp, config).iloc[0]

    assert decision["decision_state"] == "12A7c_stage2_diagnostic_only"
    assert decision["stage2_decoupled_signal_status"] == "not_supported"
    assert decision["stage2_chained_operating_status"] == "partial"


def test_selected_random_replay_failure_blocks_decision():
    runner = load_runner()
    config = base_config()
    anchor = pd.DataFrame(
        [
            {
                "stage1_anchor_rule_id": "simple_a",
                "stage1_anchor_feature": "volatility_20d",
                "stage1_anchor_orientation": "asc",
                "stage1_anchor_X": 0.30,
            }
        ]
    )
    dec_sel = pd.DataFrame([{"candidate_id": "single_a", "candidate_family": "single_feature_stage2", "stage2_budget_X": 0.3}])
    chain_sel = pd.DataFrame([{"candidate_id": "single_b", "candidate_family": "single_feature_stage2", "stage2_budget_X": 0.3}])
    readout = pd.DataFrame(
        [
            {
                "denominator_type": "ground_truth_no_fast_fail_survivor",
                "candidate_id": "single_a",
                "stage2_budget_X": 0.3,
                "split": "robustness",
                "candidate_family": "single_feature_stage2",
                "selected_n": 10,
                "denominator_positive_n": 5,
                "bootstrap_replicate_valid_n": 20,
                "delta_vs_random_p50": 0.05,
                "delta_vs_random_p50_ci95_low": 0.01,
                "rank_not_evaluable_rate": 0.0,
                "readout_status": "ok",
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "candidate_id": "single_b",
                "stage2_budget_X": 0.3,
                "split": "robustness",
                "candidate_family": "single_feature_stage2",
                "selected_n": 10,
                "denominator_positive_n": 5,
                "bootstrap_replicate_valid_n": 20,
                "delta_vs_random_p50": 0.05,
                "delta_vs_random_p50_ci95_low": 0.01,
                "rank_not_evaluable_rate": 0.0,
                "budget_abs_delta_rank_evaluable_vs_X": 0.0,
                "readout_status": "random_replay_failed",
            },
        ]
    )
    opp = pd.DataFrame([{"split": "robustness", "stage1_defense_opportunity_cost_status": "no_material_continuation_cost"}])

    decision = runner.decision_row(True, "", True, anchor, dec_sel, chain_sel, readout, opp, config).iloc[0]

    assert decision["decision_state"] == "12A7c_blocked_input_or_stage1_anchor_failure"
    assert decision["stage2_chained_operating_status"] == "blocked"
    assert "chained_random_replay_failed" in decision["gate_failure_reasons"]


def test_input_gate_routes_low_capacity_anchor_to_blocked_followup():
    runner = load_runner()
    audit = pd.DataFrame(
        {
            "artifact_id": ["required"],
            "required_flag": [True],
            "read_status": ["pass"],
            "schema_status": ["pass"],
        }
    )
    decision = pd.DataFrame([{"decision_state": "12A7b_low_capacity_monotone_supported_over_backbone"}])

    ok, reason = runner.input_gate_pass(audit, decision)

    assert not ok
    assert "low_capacity_monotone_anchor_not_supported" in reason

    blocked = runner.decision_row(
        False,
        reason,
        False,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(
            columns=[
                "denominator_type",
                "candidate_id",
                "stage2_budget_X",
                "split",
            ]
        ),
        pd.DataFrame(columns=["split", "stage1_defense_opportunity_cost_status"]),
        base_config(),
    ).iloc[0]
    assert blocked["decision_state"] == "12A7c_blocked_input_or_stage1_anchor_failure"
    assert blocked["next_allowed_requirement"] == "none"
    assert blocked["recommended_internal_followup"] == "low_capacity_backbone_chained_stage2_validation"


def test_blocked_output_bundle_writes_low_capacity_decision_artifacts(tmp_path):
    runner = load_runner()
    paths = {}
    for key in runner.output_paths():
        if key in {"score_matrix", "bootstrap_replicates", "random_stage2_selected"}:
            paths[key] = tmp_path / f"{key}.parquet"
        elif key == "report":
            paths[key] = tmp_path / f"{key}.md"
        elif key == "manifest":
            paths[key] = tmp_path / f"{key}.json"
        else:
            paths[key] = tmp_path / f"{key}.csv"
    input_audit = pd.DataFrame(
        {
            "artifact_id": ["a7b_direction_c_decision"],
            "resolved_path": ["mock"],
            "row_count": [1],
            "sha256": [""],
            "schema_status": ["pass"],
            "read_status": ["pass"],
            "required_flag": [True],
        }
    )

    decision = runner.write_blocked_outputs(
        paths,
        input_audit,
        "a7b_low_capacity_monotone_anchor_not_supported_by_12a7c",
        RUNNER_PATH,
        RUNNER_PATH,
        base_config(),
    )

    row = pd.read_csv(paths["direction_e_decision"]).iloc[0]
    assert decision.iloc[0]["decision_state"] == "12A7c_blocked_input_or_stage1_anchor_failure"
    assert row["next_allowed_requirement"] == "none"
    assert row["recommended_internal_followup"] == "low_capacity_backbone_chained_stage2_validation"
    assert paths["report"].exists()
    assert paths["manifest"].exists()


def test_required_outputs_exist_and_schema_after_full_run():
    required = {
        "input_artifact_audit.csv": {"artifact_id", "resolved_path", "schema_status", "read_status", "required_flag"},
        "scope_universe_audit.csv": {"split", "primary_scope_n", "ground_truth_survivor_n", "stage1_anchor_chained_survivor_n"},
        "stage1_anchor_rule_card.csv": {"stage1_anchor_reconstruction_status", "stage1_anchor_rule_id", "publishable_count_reconciliation_status"},
        "stage2_candidate_card.csv": {"candidate_id", "candidate_family", "candidate_status"},
        "stage2_train_selection.csv": {"denominator_type", "selection_status", "candidate_id", "tie_break_path"},
        "stage2_ground_truth_survivor_readout.csv": {"denominator_type", "candidate_id", "delta_vs_random_p50_ci95_low"},
        "stage2_chained_trailing_rank_readout.csv": {"denominator_type", "candidate_id", "budget_abs_delta_rank_evaluable_vs_X"},
        "stage2_random_same_budget_audit.csv": {"candidate_id", "requested_selected_n", "sampled_random_n", "retention_rank_rule"},
        "stage2_single_feature_challenger.csv": {"single_feature_matched_rate", "delta_vs_single_feature_ci95_low"},
        "stage2_complex_model_matched_comparator.csv": {"complex_model_matched_rate", "delta_vs_complex_model_ci95_low"},
        "stage2_budget_drift_audit.csv": {"candidate_id", "budget_abs_delta_rank_evaluable_vs_X", "rank_not_evaluable_rate"},
        "stage2_opportunity_cost_audit.csv": {"stage1_defense_opportunity_cost_status", "continuation_rate_delta_chained_vs_ground_truth"},
        "stage2_stability_slice_audit.csv": {"slice_type", "direction_status", "random_p50"},
        "direction_e_decision.csv": {"decision_state", "stage2_decoupled_signal_status", "stage2_chained_operating_status", "next_allowed_requirement"},
    }
    for file_name, columns in required.items():
        path = TABLE_DIR / file_name
        assert path.exists(), file_name
        frame = pd.read_csv(path, nrows=5, low_memory=False)
        assert columns.issubset(frame.columns), file_name
    assert (LOCAL_CACHE_DIR / "stage2_decoupling_score_matrix.parquet").exists()
    assert (LOCAL_CACHE_DIR / "bootstrap_replicates.parquet").exists()
    assert (LOCAL_CACHE_DIR / "random_stage2_selected.parquet").exists()
    random_selected = pd.read_parquet(LOCAL_CACHE_DIR / "random_stage2_selected.parquet")
    assert {
        "denominator_type",
        "candidate_id",
        "candidate_family",
        "stage2_budget_X",
        "retention_rank_rule",
    }.issubset(random_selected.columns)
    assert REPORT_PATH.exists()
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    assert "validation stress warning" in report_text
    assert "single-feature challenger result" in report_text
    assert "complex-vs-single-feature paired result" in report_text
    assert MANIFEST_PATH.exists()
