from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_16b_sequential_continuation_label_design_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16b_for_tests", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m = load_runner()


def config(horizons: list[int] | None = None) -> dict:
    return {
        "label_design": {
            "selected_threshold_id": "up50pct",
            "threshold_sensitivity_grid": ["up50pct", "up100pct", "up150pct"],
            "horizon_grid_sessions": horizons or [5, 8, 13, 15, 20],
            "horizon_sensitivity_grid": [5, 8, 13, 15],
            "primary_horizon_sessions": 20,
            "eligible_split_buckets": ["train", "validation", "robustness"],
            "stability_gate_split_buckets": ["train", "robustness"],
            "stress_test_split_buckets": ["validation"],
            "validation_usage": "stress_test_readout_only",
            "primary_label_id": m.PRIMARY_LABEL_ID,
            "secondary_label_id": m.SECONDARY_LABEL_ID,
            "stress_label_id": m.STRESS_LABEL_ID,
            "drawdown_threshold": -0.10,
            "step_end_price_ratio_threshold": 0.0,
            "soft_membership_high_threshold": 0.30,
            "hard_projection_anchor_coverage_min": 0.95,
            "soft_overlap_coverage_caveat_min": 0.95,
            "step_generation_lineage_sane_min": 0.999,
            "positive_rate_train_min": 0.20,
            "positive_rate_train_max": 0.80,
            "negative_rate_train_min": 0.05,
            "negative_rate_train_max": 0.60,
            "positive_effective_sample_size_train_min": 500,
            "negative_effective_sample_size_train_min": 200,
            "labelable_step_n_train_min": 2000,
            "negative_effective_sample_size_robustness_min": 50,
            "base_rate_abs_delta_max": 0.15,
            "validation_labelable_step_n_caveat_min": 100,
            "known_failed_positive_share_max": 0.50,
            "known_failed_share_delta_max": 0.20,
            "startup_authorization_basis": m.UPSTREAM_READY,
        }
    }


def interval(**overrides: object) -> dict:
    row = {
        "threshold_id": "up50pct",
        "cluster_split_bucket": "train",
        "instrument": "S1",
        "episode_cluster_id": "C1",
        "cluster_start_pos": 10,
        "cluster_end_pos": 54,
        "episode_length_sessions": 45,
        "anchor_n": 3,
        "eligible_episode_cluster": True,
    }
    row.update(overrides)
    return row


def step(**overrides: object) -> dict:
    row = {
        "step_id": "s1",
        "threshold_id": "up50pct",
        "cluster_split_bucket": "train",
        "instrument": "S1",
        "episode_cluster_id": "C1",
        "horizon_sessions": 20,
        "step_index": 0,
        "step_start_pos": 0,
        "step_end_pos": 2,
        "cluster_start_pos": 0,
        "cluster_end_pos": 8,
        "episode_length_sessions": 9,
        "anchor_n": 2,
        "full_horizon_nonoverlap_step": True,
        "partial_tail_step": False,
    }
    row.update(overrides)
    return row


def member(row_id: int, cluster_id: str = "C1") -> dict:
    return {
        "source_row_key": f"S1|2020-01-{row_id:02d}|{row_id}|up50pct",
        "threshold_id": "up50pct",
        "instrument": "S1",
        "episode_cluster_id": cluster_id,
        "cluster_split_bucket": "train",
    }


def taxonomy_rows(rows: list[tuple[str, str]]) -> pd.DataFrame:
    payload = [
        {"source_row_key": key, "threshold_id": "up50pct", "episode_cluster_id": "C1", "path_type": path_type, "assignment_unit": "anchor_path"}
        for key, path_type in rows
    ]
    for idx, family in enumerate(m.KNOWN_FAILED_FAMILIES):
        payload.append(
            {
                "source_row_key": f"dummy-{idx}",
                "threshold_id": "up50pct",
                "episode_cluster_id": "dummy",
                "path_type": family,
                "assignment_unit": "anchor_path",
            }
        )
    return pd.DataFrame(payload)


def decision_base() -> pd.DataFrame:
    rows = [
        {
            "label_id": m.PRIMARY_LABEL_ID,
            "threshold_id": "up50pct",
            "cluster_split_bucket": "train",
            "horizon_sessions": 20,
            "labelable_step_n": 3000,
            "positive_step_n": 1500,
            "negative_step_n": 600,
            "neutral_step_n": 900,
            "positive_rate": 0.50,
            "negative_rate": 0.20,
            "neutral_rate": 0.30,
            "effective_sample_size_nonoverlap": 3000,
            "positive_effective_sample_size": 1500,
            "negative_effective_sample_size": 600,
            "episode_cluster_n": 200,
            "anchor_n_reference_only": 1000,
            "base_rate_status": "pass",
        },
        {
            "label_id": m.PRIMARY_LABEL_ID,
            "threshold_id": "up50pct",
            "cluster_split_bucket": "robustness",
            "horizon_sessions": 20,
            "labelable_step_n": 1000,
            "positive_step_n": 460,
            "negative_step_n": 180,
            "neutral_step_n": 360,
            "positive_rate": 0.46,
            "negative_rate": 0.18,
            "neutral_rate": 0.36,
            "effective_sample_size_nonoverlap": 1000,
            "positive_effective_sample_size": 460,
            "negative_effective_sample_size": 180,
            "episode_cluster_n": 100,
            "anchor_n_reference_only": 500,
            "base_rate_status": "pass",
        },
        {
            "label_id": m.PRIMARY_LABEL_ID,
            "threshold_id": "up50pct",
            "cluster_split_bucket": "validation",
            "horizon_sessions": 20,
            "labelable_step_n": 100,
            "positive_step_n": 40,
            "negative_step_n": 20,
            "neutral_step_n": 40,
            "positive_rate": 0.40,
            "negative_rate": 0.20,
            "neutral_rate": 0.40,
            "effective_sample_size_nonoverlap": 100,
            "positive_effective_sample_size": 40,
            "negative_effective_sample_size": 20,
            "episode_cluster_n": 10,
            "anchor_n_reference_only": 100,
            "base_rate_status": "pass",
        },
    ]
    return pd.DataFrame(rows, columns=m.BASE_RATE_COLUMNS)


def pass_hard_gates() -> dict[str, str]:
    return {
        "input_artifact": "pass",
        "upstream_16a_authorization": "pass",
        "step_lineage_adapter": "pass",
        "label_rule_definition": "pass",
        "step_materialization": "pass",
        "qfq_price_source": "pass",
        "price_path_completeness": "pass",
        "known_failed_overlap_evaluability": "pass",
        "search_accounting": "pass",
    }


def valid_16a_decision(**overrides: object) -> pd.DataFrame:
    row = {
        "decision_state": m.UPSTREAM_READY,
        "next_allowed_requirement": m.UPSTREAM_NEXT,
        "selected_threshold_id": "up50pct",
        "primary_horizon_sessions": 20,
        "recommended_sampling_unit": "non_overlapping_time_blocked_sampling_geometry_step",
        "stability_gate_split_buckets": "train;robustness",
        "stress_test_split_buckets": "validation",
        "input_artifact_gate": "pass",
        "upstream_lineage_gate": "pass",
        "price_path_completeness_gate": "pass",
        "cluster_interval_adapter_gate": "pass",
        "cluster_interval_rebuild_gate": "pass",
        "episode_cluster_non_overlap_gate": "pass",
        "geometry_consistency_gate": "pass",
        "search_accounting_gate": "pass",
        "anchor_n_train": 57524,
        "episode_cluster_n_train": 667,
        "episode_cluster_n_validation": 45,
        "episode_cluster_n_robustness": 218,
        "nonoverlap_step_n_train_primary_horizon": 20871,
        "full_horizon_nonoverlap_step_n_train_primary_horizon": 20245,
        "partial_tail_step_n_train_primary_horizon": 626,
        "effective_sample_size_train_primary_horizon": 20245,
        "anchor_overcount_ratio_train_primary_horizon": 2.756169,
        "effective_to_anchor_ratio_abs_range": 0.131094,
        "geometry_stable_across_splits": True,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def pass_overlap(failed_share: float = 0.05, share_delta: float = 0.01) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "label_id": m.PRIMARY_LABEL_ID,
                "threshold_id": "up50pct",
                "known_failed_family": family,
                "overlap_source": "hard_15b_taxonomy",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "positive_step_n": 1500,
                "failed_family_positive_step_n": int(1500 * failed_share),
                "failed_family_positive_share": failed_share,
                "all_step_failed_family_share": max(failed_share - share_delta, 0.0),
                "share_delta": share_delta,
                "hard_projection_coverage": 1.0,
                "soft_overlap_coverage": 1.0,
                "soft_overlap_status": "pass",
                "overlap_status": "pass",
                "blocking_reason": "",
            }
            for family in m.KNOWN_FAILED_FAMILIES
        ],
        columns=m.OVERLAP_COLUMNS,
    )


def test_16a_authorization_requires_ready_decision_and_named_16b_next_requirement():
    audit = m.build_upstream_16a_authorization_audit(valid_16a_decision(), config())
    assert audit.iloc[0]["authorization_status"] == "pass"

    audit = m.build_upstream_16a_authorization_audit(valid_16a_decision(next_allowed_requirement="wrong.md"), config())
    assert audit.iloc[0]["authorization_status"] == "fail"


def test_16a_authorization_requires_all_hard_gates_pass():
    audit = m.build_upstream_16a_authorization_audit(valid_16a_decision(price_path_completeness_gate="fail"), config())
    assert audit.iloc[0]["authorization_status"] == "fail"
    assert "all_16a_hard_gates_passed" in audit.iloc[0]["blocking_reason"]


def test_sampling_unit_inherits_nonoverlap_full_horizon_steps_only():
    steps = m.materialize_steps(pd.DataFrame([interval()]), config([20]))
    assert steps["full_horizon_nonoverlap_step"].all()
    assert not steps["partial_tail_step"].any()
    assert steps["step_id"].str.contains("|h20|", regex=False).all()


def test_step_materialization_rebuilds_row_level_steps_from_episode_intervals():
    steps = m.materialize_steps(pd.DataFrame([interval()]), config([20]))
    assert steps[["instrument", "episode_cluster_id", "step_index"]].to_dict("records") == [
        {"instrument": "S1", "episode_cluster_id": "C1", "step_index": 0},
        {"instrument": "S1", "episode_cluster_id": "C1", "step_index": 1},
    ]


def test_step_materialization_counts_match_16a_horizon_grid_readout():
    test_step_materialization_reconciles_16a_counts_and_catches_mismatch()


def test_16a_step_geometry_panel_is_not_treated_as_row_level_step_source():
    search = m.build_search_accounting_audit(config())
    assert search.iloc[0]["step_materialization_source"] == "16A_episode_interval_panel_formula"


def test_partial_tail_steps_are_excluded_from_labelable_population():
    steps = m.materialize_steps(pd.DataFrame([interval(episode_length_sessions=39, cluster_end_pos=48)]), config([20]))
    assert len(steps) == 1
    assert int(steps.iloc[0]["step_end_pos"]) == 29


def test_qfq_price_source_is_required_for_label_construction(tmp_path):
    steps = pd.DataFrame([step()])
    price = pd.DataFrame({"instrument": ["S1"], "qfq_row_n": [3], "price_path_status": ["pass"]})
    audit, cache = m.build_qfq_price_source_audit(steps, tmp_path, price, price)
    assert audit.iloc[0]["qfq_price_source_status"] == "fail"
    assert "missing_qfq_file" in audit.iloc[0]["blocking_reason"]
    assert cache == {}


def test_validation_is_stress_readout_and_not_primary_gate():
    base = decision_base()
    base.loc[base["cluster_split_bucket"].eq("validation"), "labelable_step_n"] = 0
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        base,
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    assert decision.iloc[0]["decision_state"] == m.DECISION_READY
    assert not bool(decision.iloc[0]["validation_stress_evaluable"])


def test_primary_horizon_frozen_at_20():
    assert config()["label_design"]["primary_horizon_sessions"] == 20
    assert m.build_search_accounting_audit(config()).iloc[0]["primary_horizon_sessions"] == 20


def test_horizon_5_8_13_15_are_sensitivity_only():
    search = m.build_search_accounting_audit(config())
    assert search.iloc[0]["horizon_sensitivity_grid"] == "5;8;13;15"
    assert search.iloc[0]["primary_horizon_sessions"] == 20


def test_label_rule_primary_uses_drawdown_and_nonnegative_end_condition():
    qfq = pd.DataFrame({"date": ["d1", "d2", "d3"], "close": [100.0, 95.0, 99.0]})
    labels = m.compute_continuation_labels(pd.DataFrame([step()]), {"S1": qfq}, config([3]))
    row = labels.iloc[0]
    assert not bool(row["continuation_positive"])
    assert not bool(row["continuation_negative"])
    assert bool(row["continuation_neutral"])


def test_primary_label_negative_uses_deep_drawdown_threshold():
    qfq = pd.DataFrame({"date": ["d1", "d2", "d3"], "close": [100.0, 90.0, 101.0]})
    labels = m.compute_continuation_labels(pd.DataFrame([step()]), {"S1": qfq}, config([3]))
    assert bool(labels.iloc[0]["continuation_negative"])


def test_primary_label_neutral_is_neither_positive_nor_negative():
    qfq = pd.DataFrame({"date": ["d1", "d2", "d3"], "close": [100.0, 95.0, 99.0]})
    labels = m.compute_continuation_labels(pd.DataFrame([step()]), {"S1": qfq}, config([3]))
    row = labels.iloc[0]
    assert bool(row["continuation_neutral"])
    assert not bool(row["continuation_positive"])
    assert not bool(row["continuation_negative"])


def test_label_base_rates_use_step_denominator_not_anchor_denominator():
    test_base_rate_counts_use_materialized_step_denominator()


def test_effective_sample_support_uses_nonoverlap_full_step_counts():
    support = m.build_effective_sample_label_support_readout(decision_base(), config())
    train = support.loc[support["cluster_split_bucket"].eq("train")].iloc[0]
    assert int(train["labelable_step_n"]) == 3000
    assert int(train["positive_effective_sample_size"]) == 1500


def test_effective_sample_support_requires_robustness_negative_sample_floor():
    test_decision_effective_sample_too_small_when_robustness_negative_floor_fails()


def test_train_robustness_stability_uses_absolute_base_rate_deltas():
    base = decision_base()
    base.loc[base["cluster_split_bucket"].eq("robustness"), "positive_rate"] = 0.80
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        base,
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    assert decision.iloc[0]["decision_state"] == "16B_continuation_label_unstable_train_robustness"


def test_validation_sparse_adds_caveat_without_blocking_primary_decision():
    test_validation_is_stress_readout_and_not_primary_gate()


def test_known_failed_context_exposure_caveat_does_not_block_ready_decision():
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        pass_overlap(failed_share=0.60, share_delta=0.01),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    row = decision.iloc[0]
    assert row["decision_state"] == m.DECISION_READY
    assert row["known_failed_overlap_gate"] == "pass"
    assert bool(row["known_failed_context_exposure_caveat"])


def test_known_failed_overlap_missing_artifact_fails_closed():
    gates = pass_hard_gates()
    gates["known_failed_overlap_evaluability"] = "fail_not_evaluable"
    decision = m.build_sequential_continuation_label_decision(
        config(),
        gates,
        decision_base(),
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    assert decision.iloc[0]["decision_state"] == m.DECISION_BLOCKED


def test_known_failed_family_names_must_match_15b_path_type_enum():
    membership = pd.DataFrame([member(1)])
    taxonomy = pd.DataFrame(
        [{"source_row_key": membership.iloc[0]["source_row_key"], "threshold_id": "up50pct", "episode_cluster_id": "C1", "path_type": "unknown", "assignment_unit": "anchor_path"}]
    )
    _projection, status, reason = m.build_known_failed_cluster_projection(membership, taxonomy, None, config())
    assert status == "fail_unknown_known_failed_family_enum"
    assert reason == "required_15b_known_failed_path_types_missing"


def test_known_failed_projection_required_columns_must_exist_before_scoring():
    membership = pd.DataFrame([member(1)])
    taxonomy = taxonomy_rows([(membership.iloc[0]["source_row_key"], "choppy_reversal_winner")]).drop(columns=["assignment_unit"])
    _projection, status, reason = m.build_known_failed_cluster_projection(membership, taxonomy, None, config())
    assert status == "fail_missing_known_failed_projection_column"
    assert reason == "15b_taxonomy_required_columns_missing"


def test_primary_known_failed_projection_uses_15b_path_type_only():
    membership = pd.DataFrame([member(1), member(2)])
    taxonomy = taxonomy_rows(
        [
            (membership.iloc[0]["source_row_key"], "late_rescue_winner"),
            (membership.iloc[1]["source_row_key"], "late_rescue_winner"),
        ]
    )
    soft = pd.DataFrame(
        [
            {"source_row_key": key, "threshold_id": "up50pct", "hard_path_type_15b": "late_rescue_winner", "membership_choppy_reversal_winner": 0.99}
            for key in membership["source_row_key"]
        ]
    )
    projection, status, _reason = m.build_known_failed_cluster_projection(membership, taxonomy, soft, config())
    choppy = projection.loc[projection["known_failed_family"].eq("choppy_reversal_winner")].iloc[0]
    assert status == "pass"
    assert choppy["cluster_failed_anchor_share"] == 0.0
    assert not bool(choppy["known_failed_step_flag"])
    assert choppy["cluster_soft_failed_anchor_share"] == 1.0


def test_15c2_soft_membership_partial_coverage_adds_caveat_without_hard_fail():
    test_known_failed_projection_uses_15b_hard_and_soft_partial_coverage_is_caveat()


def test_secondary_label_does_not_enter_any_gate_or_decision_field():
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    assert m.SECONDARY_LABEL_ID not in decision.to_string()
    assert decision.iloc[0]["decision_state"] == m.DECISION_READY


def test_known_failed_projection_uses_cluster_descriptor_and_step_denominator():
    labels = pd.DataFrame(
        [
            {"step_id": "s1", "label_id": m.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "C1", "horizon_sessions": 20, "continuation_positive": True},
            {"step_id": "s2", "label_id": m.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "C1", "horizon_sessions": 20, "continuation_positive": False},
            {"step_id": "s3", "label_id": m.PRIMARY_LABEL_ID, "threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "C2", "horizon_sessions": 20, "continuation_positive": True},
        ]
    )
    projection = pd.DataFrame(
        [
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "C1", "known_failed_family": "late_rescue_winner", "known_failed_step_flag": True, "hard_projection_coverage": 1.0, "soft_overlap_coverage": 1.0, "soft_overlap_status": "pass"},
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "instrument": "S1", "episode_cluster_id": "C2", "known_failed_family": "late_rescue_winner", "known_failed_step_flag": False, "hard_projection_coverage": 1.0, "soft_overlap_coverage": 1.0, "soft_overlap_status": "pass"},
        ]
    )
    overlap, _panel = m.build_known_failed_overlap_readout(labels, projection)
    row = overlap.iloc[0]
    assert int(row["positive_step_n"]) == 2
    assert int(row["failed_family_positive_step_n"]) == 1
    assert row["failed_family_positive_share"] == 0.5


def test_cluster_descriptor_projection_is_not_step_local_morphology_gate():
    overlap = pass_overlap(failed_share=0.95, share_delta=0.0)
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        overlap,
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    row = decision.iloc[0]

    assert row["known_failed_overlap_gate"] == "pass"
    assert bool(row["known_failed_context_exposure_caveat"])
    assert row["decision_state"] == m.DECISION_READY


def test_14a_aggregate_context_cannot_drive_primary_overlap_gate():
    assert m.artifact_required_flag("upstream_14a_morphology_rediscovery_audit") == "optional_appendix"
    assert m.lineage_role_for_artifact("upstream_14a_sparse_event_raw_readout") == "upstream_14a_appendix_context"


def test_stress_label_generation_lineage_sanity_threshold():
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [0.998]}),
    )
    assert not bool(decision.iloc[0]["step_generation_lineage_sane"])
    assert decision.iloc[0]["step_materialization_gate"] == "fail"
    assert decision.iloc[0]["decision_state"] == m.DECISION_BLOCKED


def test_threshold_sensitivity_does_not_change_primary_decision():
    base = pd.concat(
        [
            decision_base(),
            pd.DataFrame(
                [
                    {
                        "label_id": m.PRIMARY_LABEL_ID,
                        "threshold_id": "up100pct",
                        "cluster_split_bucket": "train",
                        "horizon_sessions": 20,
                        "labelable_step_n": 3000,
                        "positive_step_n": 2999,
                        "negative_step_n": 1,
                        "neutral_step_n": 0,
                        "positive_rate": 0.999,
                        "negative_rate": 0.001,
                        "neutral_rate": 0.0,
                        "effective_sample_size_nonoverlap": 3000,
                        "positive_effective_sample_size": 2999,
                        "negative_effective_sample_size": 1,
                        "episode_cluster_n": 200,
                        "anchor_n_reference_only": 1000,
                        "base_rate_status": "pass",
                    }
                ],
                columns=m.BASE_RATE_COLUMNS,
            ),
        ],
        ignore_index=True,
    )
    overlap = pd.concat(
        [
            pass_overlap(),
            pd.DataFrame(
                [
                    {
                        "label_id": m.PRIMARY_LABEL_ID,
                        "threshold_id": "up100pct",
                        "known_failed_family": "late_rescue_winner",
                        "overlap_source": "hard_15b_taxonomy",
                        "cluster_split_bucket": "train",
                        "horizon_sessions": 20,
                        "positive_step_n": 2999,
                        "failed_family_positive_step_n": 2999,
                        "failed_family_positive_share": 1.0,
                        "all_step_failed_family_share": 1.0,
                        "share_delta": 0.0,
                        "hard_projection_coverage": 1.0,
                        "soft_overlap_coverage": 1.0,
                        "soft_overlap_status": "pass",
                        "overlap_status": "episode_context_exposure_caveat",
                        "blocking_reason": "nonblocking_episode_context_exposure_caveat",
                    }
                ],
                columns=m.OVERLAP_COLUMNS,
            ),
        ],
        ignore_index=True,
    )
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        base,
        overlap,
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    assert decision.iloc[0]["decision_state"] == m.DECISION_READY
    assert decision.iloc[0]["selected_threshold_id"] == "up50pct"


def test_no_entry_exit_holding_cost_or_portfolio_columns_are_emitted():
    forbidden = ("entry_price", "exit", "holding", "cost", "portfolio", "alpha", "forward_return")
    emitted_columns = set(m.LABEL_PANEL_COLUMNS + m.BASE_RATE_COLUMNS + m.OVERLAP_COLUMNS)
    assert not [column for column in emitted_columns if any(token in column for token in forbidden)]


def test_search_accounting_never_authorizes_signal_model_or_deployment():
    search = m.build_search_accounting_audit(config())
    row = search.iloc[0]
    assert row["search_accounting_status"] == "pass"
    assert not bool(row["entry_search_authorized"])
    assert not bool(row["signal_search_authorized"])
    assert not bool(row["model_training_authorized"])
    assert not bool(row["separability_search_authorized"])
    assert not bool(row["label_deployment_authorized"])


def test_ready_decision_only_authorizes_16c_separability_diagnostic():
    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        pass_overlap(),
        pd.DataFrame({"continuation_survival_positive_rate": [1.0]}),
    )
    row = decision.iloc[0]
    assert row["decision_state"] == m.DECISION_READY
    assert row["next_allowed_requirement"] == m.NEXT_16C
    assert not bool(row["separability_search_authorized"])
    assert not bool(row["label_deployment_authorized"])


def test_materialize_steps_uses_full_horizon_only_and_excludes_partial_tail():
    intervals = pd.DataFrame([interval()])
    steps = m.materialize_steps(intervals, config([20]))

    assert len(steps) == 2
    assert steps["step_start_pos"].tolist() == [10, 30]
    assert steps["step_end_pos"].tolist() == [29, 49]
    assert not steps["partial_tail_step"].any()


def test_step_materialization_reconciles_16a_counts_and_catches_mismatch():
    steps = m.materialize_steps(pd.DataFrame([interval()]), config([20]))
    expected = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "labelable_step_n_for_future_16B": 2,
            }
        ]
    )
    audit = m.build_step_materialization_audit(steps, expected)
    assert audit.iloc[0]["adapter_status"] == "pass"

    expected.loc[0, "labelable_step_n_for_future_16B"] = 3
    audit = m.build_step_materialization_audit(steps, expected)
    assert audit.iloc[0]["adapter_status"] == "fail"


def test_step_materialization_audit_fails_bad_bounds_and_cluster_count_mismatch():
    steps = pd.DataFrame(
        [
            step(
                step_id="bad",
                cluster_start_pos=10,
                cluster_end_pos=29,
                step_start_pos=10,
                step_end_pos=35,
                horizon_sessions=20,
                episode_length_sessions=20,
            )
        ]
    )
    expected = pd.DataFrame(
        [
            {
                "threshold_id": "up50pct",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "labelable_step_n_for_future_16B": 1,
            }
        ]
    )

    audit = m.build_step_materialization_audit(steps, expected)

    assert audit.iloc[0]["adapter_status"] == "fail"
    assert int(audit.iloc[0]["bad_step_bounds_n"]) == 1
    assert int(audit.iloc[0]["cluster_count_mismatch_n"]) == 0


def test_qfq_price_source_audit_fails_missing_bad_close_or_bounds(tmp_path):
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame({"date": ["2020-01-01", "2020-01-02", "2020-01-03"], "close": [10.0, 0.0, 11.0]}).to_csv(qfq_dir / "S1.csv", index=False)
    steps = pd.DataFrame([step(step_end_pos=4)])
    price = pd.DataFrame({"instrument": ["S1"], "qfq_row_n": [3], "price_path_status": ["pass"]})

    audit, _cache = m.build_qfq_price_source_audit(steps, qfq_dir, price, price)

    assert audit.iloc[0]["qfq_price_source_status"] == "fail"
    assert "bad_close_values" in audit.iloc[0]["blocking_reason"]
    assert "step_bounds_out_of_qfq" in audit.iloc[0]["blocking_reason"]


def test_primary_label_rule_boundaries_positive_negative_and_neutral():
    qfq = pd.DataFrame(
        {
            "date": [f"2020-01-{day:02d}" for day in range(1, 10)],
            "close": [100.0, 95.0, 101.0, 100.0, 90.0, 101.0, 100.0, 95.0, 99.0],
        }
    )
    steps = pd.DataFrame(
        [
            step(step_id="positive", step_start_pos=0, step_end_pos=2, step_index=0),
            step(step_id="negative_boundary", step_start_pos=3, step_end_pos=5, step_index=1),
            step(step_id="neutral", step_start_pos=6, step_end_pos=8, step_index=2),
        ]
    )

    labels = m.compute_continuation_labels(steps, {"S1": qfq}, config([3]))
    by_id = labels.set_index("step_id")

    assert bool(by_id.loc["positive", "continuation_positive"])
    assert bool(by_id.loc["negative_boundary", "continuation_negative"])
    assert bool(by_id.loc["neutral", "continuation_neutral"])


def test_base_rate_counts_use_materialized_step_denominator():
    labels = pd.DataFrame(
        [
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "horizon_sessions": 20, "step_id": "s1", "episode_cluster_id": "C1", "continuation_positive": True, "continuation_negative": False, "continuation_neutral": False, "continuation_progress_positive": True, "continuation_survival_positive": True, "anchor_n": 2},
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "horizon_sessions": 20, "step_id": "s2", "episode_cluster_id": "C1", "continuation_positive": False, "continuation_negative": True, "continuation_neutral": False, "continuation_progress_positive": False, "continuation_survival_positive": True, "anchor_n": 2},
            {"threshold_id": "up50pct", "cluster_split_bucket": "train", "horizon_sessions": 20, "step_id": "s3", "episode_cluster_id": "C2", "continuation_positive": False, "continuation_negative": False, "continuation_neutral": True, "continuation_progress_positive": False, "continuation_survival_positive": True, "anchor_n": 1},
        ]
    )

    base = m.build_continuation_label_base_rate_readout(labels)
    row = base.loc[base["label_id"].eq(m.PRIMARY_LABEL_ID)].iloc[0]

    assert int(row["labelable_step_n"]) == 3
    assert int(row["positive_step_n"]) == 1
    assert int(row["negative_step_n"]) == 1
    assert row["positive_rate"] == 1 / 3


def test_known_failed_projection_uses_15b_hard_and_soft_partial_coverage_is_caveat():
    membership = pd.DataFrame([member(1), member(2)])
    taxonomy = taxonomy_rows(
        [
            (membership.iloc[0]["source_row_key"], "choppy_reversal_winner"),
            (membership.iloc[1]["source_row_key"], "late_rescue_winner"),
        ]
    )
    soft = pd.DataFrame(
        [
            {
                "source_row_key": membership.iloc[0]["source_row_key"],
                "threshold_id": "up50pct",
                "hard_path_type_15b": "choppy_reversal_winner",
                "membership_choppy_reversal_winner": 0.80,
            }
        ]
    )

    projection, status, reason = m.build_known_failed_cluster_projection(membership, taxonomy, soft, config())

    assert status == "pass"
    assert reason == ""
    assert projection["hard_projection_coverage"].min() == 1.0
    assert set(projection["soft_overlap_status"]) == {"soft_overlap_partial_coverage_caveat"}


def test_15c2_soft_membership_schema_gap_adds_schema_caveat_without_hard_fail():
    membership = pd.DataFrame([member(1), member(2)])
    taxonomy = taxonomy_rows(
        [
            (membership.iloc[0]["source_row_key"], "choppy_reversal_winner"),
            (membership.iloc[1]["source_row_key"], "late_rescue_winner"),
        ]
    )
    soft = pd.DataFrame(
        [
            {
                "source_row_key": membership.iloc[0]["source_row_key"],
                "threshold_id": "up50pct",
                "membership_choppy_reversal_winner": 0.80,
            }
        ]
    )

    projection, status, reason = m.build_known_failed_cluster_projection(membership, taxonomy, soft, config())

    assert status == "pass"
    assert reason == ""
    assert set(projection["soft_overlap_status"]) == {"soft_overlap_schema_caveat"}


def test_15b_hard_projection_low_anchor_coverage_fails_closed():
    membership = pd.DataFrame([member(1), member(2)])
    taxonomy = taxonomy_rows([(membership.iloc[0]["source_row_key"], "choppy_reversal_winner")])

    projection, status, reason = m.build_known_failed_cluster_projection(membership, taxonomy, None, config())

    assert not projection.empty
    assert status == "fail_insufficient_15b_hard_projection_coverage"
    assert reason == "15b_hard_projection_coverage_below_min"


def test_decision_ready_allows_soft_caveat_and_does_not_authorize_downstream_work():
    overlap = pd.DataFrame(
        [
            {
                "label_id": m.PRIMARY_LABEL_ID,
                "threshold_id": "up50pct",
                "known_failed_family": family,
                "overlap_source": "hard_15b_taxonomy",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "positive_step_n": 1500,
                "failed_family_positive_step_n": 100,
                "failed_family_positive_share": 0.066,
                "all_step_failed_family_share": 0.050,
                "share_delta": 0.016,
                "hard_projection_coverage": 1.0,
                "soft_overlap_coverage": 0.50,
                "soft_overlap_status": "soft_overlap_partial_coverage_caveat",
                "overlap_status": "pass",
                "blocking_reason": "",
            }
            for family in m.KNOWN_FAILED_FAMILIES
        ],
        columns=m.OVERLAP_COLUMNS,
    )
    validation_stress = pd.DataFrame({"continuation_survival_positive_rate": [1.0]})

    decision = m.build_sequential_continuation_label_decision(
        config(),
        pass_hard_gates(),
        decision_base(),
        overlap,
        validation_stress,
    )
    row = decision.iloc[0]

    assert row["decision_state"] == m.DECISION_READY
    assert row["next_allowed_requirement"] == m.NEXT_16C
    assert bool(row["soft_overlap_partial_coverage_caveat"])
    assert not bool(row["known_failed_context_exposure_caveat"])
    assert not bool(row["label_deployment_authorized"])
    assert not bool(row["signal_search_authorized"])
    assert not bool(row["model_training_authorized"])
    assert not bool(row["entry_policy_authorized"])
    assert not bool(row["separability_search_authorized"])


def test_decision_effective_sample_too_small_when_robustness_negative_floor_fails():
    base = decision_base()
    base.loc[base["cluster_split_bucket"].eq("robustness"), "negative_effective_sample_size"] = 49
    overlap = pd.DataFrame(
        [
            {
                "label_id": m.PRIMARY_LABEL_ID,
                "threshold_id": "up50pct",
                "known_failed_family": "choppy_reversal_winner",
                "overlap_source": "hard_15b_taxonomy",
                "cluster_split_bucket": "train",
                "horizon_sessions": 20,
                "positive_step_n": 1500,
                "failed_family_positive_step_n": 10,
                "failed_family_positive_share": 0.006,
                "all_step_failed_family_share": 0.005,
                "share_delta": 0.001,
                "hard_projection_coverage": 1.0,
                "soft_overlap_coverage": 1.0,
                "soft_overlap_status": "pass",
                "overlap_status": "pass",
                "blocking_reason": "",
            }
        ],
        columns=m.OVERLAP_COLUMNS,
    )

    decision = m.build_sequential_continuation_label_decision(config(), pass_hard_gates(), base, overlap, pd.DataFrame({"continuation_survival_positive_rate": [1.0]}))

    assert decision.iloc[0]["decision_state"] == "16B_continuation_label_effective_sample_too_small"


def test_label_panel_schema_contains_no_forward_return_fields():
    assert not [column for column in m.LABEL_PANEL_COLUMNS if "forward_return" in column or column == "return"]
