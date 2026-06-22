from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_12a7d_stage2_random_baseline_support_triage.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a7d_stage2_random_baseline_support_triage", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def base_config() -> dict:
    return {
        "random_baseline": {
            "min_random_seed_n": 1,
            "pooled_min_supported_weight_share": 0.50,
            "pooled_min_effective_seed_n": 1,
            "replacement_effective_n_floor_fraction": 0.50,
            "retention_rank_columns": ["sample_draw_id"],
        },
        "bootstrap": {
            "seed": 7,
            "n_resamples": 20,
            "ci_low_q": 0.025,
            "ci_high_q": 0.975,
            "bootstrap_min_valid_replicates": 10,
        },
        "gates": {
            "selected_n_min": 1,
            "selected_positive_n_min": 1,
            "delta_vs_random_p50_min": 0.02,
        },
    }


def test_upstream_gate_accepts_documented_gate_failure_reasons():
    runner = load_runner()
    decision = pd.DataFrame(
        [
            {
                "stage1_anchor_reconstruction_status": "pass",
                "selected_chained_deployable_at_stage_2_decision_time": True,
                "selected_chained_candidate_id": "complex_stage2_score",
                "selected_chained_X": 0.3,
                "gate_failure_reasons": "decoupled_random_replay_failed;chained_random_replay_failed",
            }
        ]
    )

    ok, reason, source = runner.upstream_random_failure_gate(decision, pd.DataFrame(), pd.DataFrame())

    assert ok
    assert reason == ""
    assert source == "gate_failure_reasons"


def test_upstream_gate_legacy_fallback_requires_selected_random_replay_failures():
    runner = load_runner()
    decision = pd.DataFrame(
        [
            {
                "decision_state": "12A7c_blocked_input_or_stage1_anchor_failure",
                "stage1_anchor_reconstruction_status": "pass",
                "stage2_decoupled_signal_status": "blocked",
                "stage2_chained_operating_status": "blocked",
                "selected_decoupled_candidate_id": "dec",
                "selected_decoupled_X": 0.2,
                "selected_chained_candidate_id": "chain",
                "selected_chained_X": 0.3,
                "selected_chained_deployable_at_stage_2_decision_time": True,
            }
        ]
    )
    dec_readout = pd.DataFrame(
        [{"candidate_id": "dec", "stage2_budget_X": 0.2, "readout_status": "random_replay_failed"}]
    )
    chain_readout = pd.DataFrame(
        [{"candidate_id": "chain", "stage2_budget_X": 0.3, "readout_status": "random_replay_failed"}]
    )

    ok, reason, source = runner.upstream_random_failure_gate(decision, dec_readout, chain_readout)

    assert ok
    assert reason == ""
    assert source == "inferred_legacy_12A7c_artifact"


def test_hierarchical_fallback_never_reuses_random_rows_across_overlapping_quarter_cells():
    runner = load_runner()
    pool = pd.DataFrame(
        [
            {
                "seed": 1,
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-03",
                "calendar_quarter": "2020Q1",
                "random_row_uid": f"uid_{idx}",
                "sample_draw_id": idx,
            }
            for idx in range(4)
        ]
    )
    counts = pd.DataFrame(
        [
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "calendar_quarter": "2020Q1",
                "requested_selected_n": 2,
            },
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-02",
                "calendar_quarter": "2020Q1",
                "requested_selected_n": 2,
            },
        ]
    )

    selected, audit = runner.draw_for_counts(
        pool,
        counts,
        "hierarchical_split_board_fallback_replay",
        "stage2_select",
        ["sample_draw_id"],
        "requested_selected_n",
    )

    assert len(selected) == 4
    assert selected["random_row_uid"].nunique() == 4
    assert audit["cell_support_status"].eq("pass").all()
    assert audit["fallback_used_flag"].all()


def test_pooled_readout_uses_supported_cell_candidate_denominator():
    runner = load_runner()
    config = base_config()
    selection = pd.DataFrame(
        [
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "candidate_id": "complex_stage2_score",
                "candidate_family": "complex_model",
                "stage2_budget_X": 0.5,
                "stage1_anchor_rule_id": "anchor",
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "selected_flag": True,
                "stage_2_continuation_target": True,
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "candidate_id": "complex_stage2_score",
                "candidate_family": "complex_model",
                "stage2_budget_X": 0.5,
                "stage1_anchor_rule_id": "anchor",
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-02",
                "selected_flag": True,
                "stage_2_continuation_target": False,
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {
                "baseline_id": "pooled_cell_weighted_replay",
                "replay_step": "stage2_select",
                "seed": 1,
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "realized_cell_grain": "month",
                "requested_selected_n": 1,
                "available_random_n": 1,
                "sampled_random_n": 1,
                "shortfall_n": 0,
                "replacement_used_flag": False,
                "duplicate_rate": 0.0,
            },
            {
                "baseline_id": "pooled_cell_weighted_replay",
                "replay_step": "stage2_select",
                "seed": 1,
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-02",
                "realized_cell_grain": "month",
                "requested_selected_n": 1,
                "available_random_n": 0,
                "sampled_random_n": 0,
                "shortfall_n": 1,
                "replacement_used_flag": False,
                "duplicate_rate": 0.0,
            },
        ]
    )
    seed_dist = pd.DataFrame(
        [
            {
                "baseline_id": "pooled_cell_weighted_replay",
                "denominator_type": "stage1_anchor_chained_survivor",
                "candidate_id": "complex_stage2_score",
                "candidate_family": "complex_model",
                "stage2_budget_X": 0.5,
                "seed": 1,
                "split": "robustness",
                "seed_valid_flag": True,
                "random_rate": 0.25,
                "seed_effective_n": 1,
                "candidate_supported_cell_selected_n": 1,
                "candidate_supported_cell_positive_n": 1,
                "candidate_supported_cell_continuation_rate": 1.0,
            }
        ]
    )

    readout, _, _ = runner.variant_readout(
        selection,
        "pooled_cell_weighted_replay",
        pd.DataFrame(),
        audit,
        seed_dist,
        config,
    )
    robust = readout.loc[readout["split"].eq("robustness")].iloc[0]

    assert robust["candidate_supported_cell_selected_n"] == 1
    assert robust["candidate_supported_cell_continuation_rate"] == 1.0
    assert robust["full_candidate_continuation_rate"] == 0.5
    assert robust["delta_vs_random_p50"] == 0.75


def test_pooled_random_rate_uses_requested_cell_weights_not_sampled_row_mean():
    runner = load_runner()
    selected = pd.DataFrame(
        [
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "random_stage_2_continuation_target": True,
            },
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-02",
                "random_stage_2_continuation_target": False,
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-01",
                "requested_selected_n": 3,
                "sampled_random_n": 1,
            },
            {
                "split": "robustness",
                "board_bucket": "main",
                "calendar_month": "2020-02",
                "requested_selected_n": 1,
                "sampled_random_n": 1,
            },
        ]
    )

    assert selected["random_stage_2_continuation_target"].mean() == 0.5
    assert runner.weighted_random_rate(selected, audit) == 0.75


def test_input_schema_audit_freezes_gate_and_score_matrix_dependencies():
    runner = load_runner()

    decision_required = set(runner.EXPECTED_INPUT_COLUMNS["a7c_direction_e_decision"])
    score_required = set(runner.EXPECTED_INPUT_COLUMNS["a7c_stage2_decoupling_score_matrix"])

    assert "gate_failure_reasons" in decision_required
    assert "selected_chained_deployable_at_stage_2_decision_time" in decision_required
    assert "stage1_anchor_feature" in decision_required
    assert "event_t0_date" in score_required
    assert "stage1_anchor_rank_status" in score_required
    assert "source_arm_is_c0" in score_required
    assert "market_regime_bucket" in score_required


def test_decision_not_supported_requires_near_strict_constructible_null():
    runner = load_runner()
    config = base_config()
    readout = pd.DataFrame(
        [
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "split": "robustness",
                "baseline_id": "strict_exact_cell_replay",
                "null_strength_rank": 1,
                "baseline_construction_status": "insufficient",
                "delta_vs_random_p50": float("nan"),
                "candidate_selected_n": 2,
                "candidate_selected_positive_n": 1,
                "bootstrap_replicate_valid_n": 0,
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "split": "robustness",
                "baseline_id": "hierarchical_month_quarter_replay",
                "null_strength_rank": 2,
                "baseline_construction_status": "insufficient",
                "delta_vs_random_p50": float("nan"),
                "candidate_selected_n": 2,
                "candidate_selected_positive_n": 1,
                "bootstrap_replicate_valid_n": 0,
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "split": "robustness",
                "baseline_id": "pooled_cell_weighted_replay",
                "null_strength_rank": 4,
                "baseline_construction_status": "pass",
                "delta_vs_random_p50": -0.01,
                "delta_vs_random_p50_ci95_low": -0.02,
                "candidate_selected_n": 2,
                "candidate_selected_positive_n": 1,
                "bootstrap_replicate_valid_n": 20,
            },
        ]
    )

    decision = runner.decision_from_readout(
        readout,
        "pass",
        "pass",
        "pass",
        "gate_failure_reasons",
        {"candidate_id": "complex_stage2_score", "candidate_family": "complex_model", "stage2_budget_X": 0.5},
        config,
    ).iloc[0]

    assert decision["decision_state"] == "12A7d_random_baseline_support_insufficient"


def test_diagnostic_only_null_does_not_populate_supporting_claim_field():
    runner = load_runner()
    config = base_config()
    readout = pd.DataFrame(
        [
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "split": "robustness",
                "baseline_id": "strict_exact_cell_replay",
                "null_strength_rank": 1,
                "baseline_construction_status": "insufficient",
                "delta_vs_random_p50": float("nan"),
                "candidate_selected_n": 2,
                "candidate_selected_positive_n": 1,
                "bootstrap_replicate_valid_n": 0,
                "diagnostic_only_flag": False,
            },
            {
                "denominator_type": "stage1_anchor_chained_survivor",
                "split": "robustness",
                "baseline_id": "pooled_cell_weighted_replay",
                "null_strength_rank": 4,
                "baseline_construction_status": "pass",
                "delta_vs_random_p50": 0.05,
                "delta_vs_random_p50_ci95_low": 0.02,
                "candidate_selected_n": 2,
                "candidate_selected_positive_n": 1,
                "bootstrap_replicate_valid_n": 20,
                "diagnostic_only_flag": True,
            },
        ]
    )

    decision = runner.decision_from_readout(
        readout,
        "pass",
        "pass",
        "pass",
        "gate_failure_reasons",
        {"candidate_id": "complex_stage2_score", "candidate_family": "complex_model", "stage2_budget_X": 0.5},
        config,
    ).iloc[0]

    assert decision["decision_state"] == "12A7d_stage2_signal_diagnostic_only"
    assert decision["weakest_accepted_null_that_supports_claim"] == ""
