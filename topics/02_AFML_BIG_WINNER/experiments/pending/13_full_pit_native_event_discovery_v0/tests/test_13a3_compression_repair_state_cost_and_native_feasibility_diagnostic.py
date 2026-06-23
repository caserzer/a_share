from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def tiny_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "split": ["train", "train", "train", "train"],
            "native_scope": [True, True, True, True],
            "upper_first": [True, False, False, False],
            "lower_first": [False, True, False, False],
            "time_to_lower": [99.0, 2.0, 99.0, 99.0],
            "upper_barrier": [0.10, 0.10, 0.10, 0.10],
            "lower_barrier": [-0.05, -0.05, -0.05, -0.05],
            "winner_positive": [True, False, False, False],
            "board_bucket": ["main_board", "main_board", "chinext", "chinext"],
            "calendar_year": [2020, 2020, 2020, 2020],
            "market_regime_bucket": ["risk_on", "risk_on", "risk_on", "risk_on"],
            "money_median_20d": [1.0, 1.0, 1.0, 1.0],
            "volatility_20d": [0.01, 0.01, 0.02, 0.02],
        }
    )


def test_cost_sensitivity_changes_only_cost_term():
    runner = load_runner()
    panel = tiny_panel()
    mask = pd.Series([True, False, False, False], index=panel.index)

    zero = runner.cost_sensitivity_row("scope", "x", "13A3_composite_state", "train", panel, mask, 0.0)
    cost = runner.cost_sensitivity_row("scope", "x", "13A3_composite_state", "train", panel, mask, 0.01)

    assert zero["treated_n"] == cost["treated_n"]
    assert zero["winner_rate"] == cost["winner_rate"]
    assert round(zero["self_utility_proxy_per_entry"] - cost["self_utility_proxy_per_entry"], 6) == 0.01
    assert "utility_margin_vs_native" not in zero


def test_composite_state_thresholds_loaded_from_dictionary_then_freeze(tmp_path):
    runner = load_runner()
    filter_dict = tmp_path / "dict.csv"
    threshold = tmp_path / "threshold.csv"
    pd.DataFrame(
        {
            "filter_id": ["p1__top_30pct__AND__p2__top_30pct"],
            "primitive_id_1": ["p1"],
            "primitive_id_2": ["p2"],
            "threshold_rule_1": ["top_30pct"],
            "threshold_rule_2": ["top_30pct"],
            "threshold_value_1": [1.0],
            "threshold_value_2": [2.0],
        }
    ).to_csv(filter_dict, index=False)
    pd.DataFrame(
        {
            "primitive_id": ["p1", "p2"],
            "threshold_rule": ["top_30pct", "top_30pct"],
            "threshold_value": [1.0, 2.0],
            "threshold_freeze_status": ["pass", "pass"],
        }
    ).to_csv(threshold, index=False)
    config = {
        "composite_states": [
            {
                "state_id": "s",
                "state_priority": 1,
                "source_13a2_filter_id": "p1__top_30pct__AND__p2__top_30pct",
                "component_family": "x+y",
                "directional_component_class": "position_strength_component",
                "morphology_risk": "normal",
            }
        ]
    }

    dictionary, status, _reason = runner.build_composite_dictionary(
        config,
        {"upstream_13a2_filter_dictionary": filter_dict, "upstream_13a2_threshold_freeze": threshold},
        0.01,
    )

    assert status == "pass"
    assert dictionary.iloc[0]["state_reproduction_status"] == "pass"
    assert dictionary.iloc[0]["component_1_threshold_value"] == 1.0


def test_missing_threshold_fails_closed(tmp_path):
    runner = load_runner()
    filter_dict = tmp_path / "dict.csv"
    threshold = tmp_path / "threshold.csv"
    pd.DataFrame(
        {
            "filter_id": ["p1__top_30pct__AND__p2__top_30pct"],
            "primitive_id_1": ["p1"],
            "primitive_id_2": ["p2"],
            "threshold_rule_1": ["top_30pct"],
            "threshold_rule_2": ["top_30pct"],
            "threshold_value_1": [1.0],
            "threshold_value_2": [2.0],
        }
    ).to_csv(filter_dict, index=False)
    pd.DataFrame({"primitive_id": ["p1"], "threshold_rule": ["top_30pct"], "threshold_value": [1.0], "threshold_freeze_status": ["pass"]}).to_csv(threshold, index=False)
    config = {"composite_states": [{"state_id": "s", "state_priority": 1, "source_13a2_filter_id": "p1__top_30pct__AND__p2__top_30pct", "component_family": "x+y", "directional_component_class": "position_strength_component", "morphology_risk": "normal"}]}

    dictionary, status, reason = runner.build_composite_dictionary(config, {"upstream_13a2_filter_dictionary": filter_dict, "upstream_13a2_threshold_freeze": threshold}, 0.01)

    assert status == "fail"
    assert dictionary.iloc[0]["state_reproduction_status"] == "fail_threshold_mismatch"
    assert "p2" in reason


def test_badside_primary_uses_compression_base_not_native():
    runner = load_runner()
    panel = tiny_panel()
    panel["split"] = "validation"
    state_mask = pd.Series([True, False, False, False], index=panel.index)
    base_mask = pd.Series([True, True, False, False], index=panel.index)
    panel.loc[0, "lower_first"] = True
    panel.loc[1, "lower_first"] = True
    panel.loc[2:, "lower_first"] = False

    row = runner.badside_utility_row("s", "validation", panel, state_mask, base_mask, 0.0)

    assert row["lower_first_uplift_vs_native"] > 0
    assert row["lower_first_uplift_vs_compression_base"] == 0
    assert row["badside_status"] == "pass"


def decision_inputs():
    readout = pd.DataFrame(
        {
            "state_id": ["s", "s", "s"],
            "split_bucket": ["train", "validation", "robustness"],
            "treated_n": [1000, 600, 600],
            "treated_positive_n": [100, 60, 60],
            "winner_rate_diff_vs_native": [0.01, 0.02, 0.02],
        }
    )
    dictionary = pd.DataFrame({"state_id": ["s"], "state_priority": [1]})
    cost_summary = pd.DataFrame({"filter_id_or_state_id": ["s"], "cost_sensitivity_status": ["cost_viable_50bps"]})
    drift = pd.DataFrame({"state_id": ["s"], "drift_status": ["primary_pass"]})
    return readout, dictionary, cost_summary, drift


def build_decision_ok(runner, cost_summary, readout, badside, drift, morphology, dictionary, config=None, **overrides):
    args = {
        "input_status": "pass",
        "upstream_13a_status": "pass",
        "upstream_13a2_status": "pass",
        "upstream_13a2_reason": "",
        "label_status": "pass",
        "cost_lineage_status": "pass",
        "cache_status": "pass",
        "composite_status": "pass",
        "composite_reason": "",
    }
    args.update(overrides)
    return runner.build_decision(
        args["input_status"],
        args["upstream_13a_status"],
        args["upstream_13a2_status"],
        args["upstream_13a2_reason"],
        args["label_status"],
        args["cost_lineage_status"],
        args["cache_status"],
        args["composite_status"],
        args["composite_reason"],
        cost_summary,
        readout,
        badside,
        drift,
        morphology,
        dictionary,
        config or {"thresholds": {}},
    )


def make_badside(cost_100_pass: bool = False, cost_50_pass: bool = True) -> pd.DataFrame:
    rows = []
    for split in ["train", "validation", "robustness"]:
        for cost, route_pass in [(0.005, cost_50_pass), (0.01, cost_100_pass), (0.0025, True)]:
            rows.append(
                {
                    "state_id": "s",
                    "split_bucket": split,
                    "cost_buffer_return": cost,
                    "lower_first_uplift_vs_compression_base": -0.01,
                    "fast_fail_uplift_vs_compression_base": 0.0,
                    "badside_status": "pass",
                    "utility_proxy_per_entry": 0.01 if route_pass else -0.01,
                    "utility_margin_vs_native": 0.01 if route_pass else -0.01,
                }
            )
    return pd.DataFrame(rows)


def make_morphology(cost_100_pass: bool = False, cost_50_pass: bool = True) -> pd.DataFrame:
    rows = []
    for split in ["validation", "robustness"]:
        for cost, route_pass in [(0.005, cost_50_pass), (0.01, cost_100_pass)]:
            rows.append({"state_id": "s", "split_bucket": split, "cost_buffer_return": cost, "independent_evidence_status": "pass" if route_pass else "morphology_rediscovery_without_independent_utility"})
    return pd.DataFrame(rows)


def test_utility_50bps_cannot_authorize_13b():
    runner = load_runner()
    readout, dictionary, cost_summary, drift = decision_inputs()
    decision = build_decision_ok(runner, cost_summary, readout, make_badside(cost_100_pass=False, cost_50_pass=True), drift, make_morphology(cost_100_pass=False, cost_50_pass=True), dictionary)

    row = decision.iloc[0]
    assert row["decision_state"] == "13A3_cost_caveat_repair_state_supported_requires_cost_model_calibration"
    assert row["next_allowed_requirement"] == "requirement_13a4_cost_model_calibration_for_compression_repair_state.md"
    assert not bool(row["sequence_mining_authorized"])


def test_utility_100bps_requires_confirmatory_preflight_not_13b():
    runner = load_runner()
    readout, dictionary, cost_summary, drift = decision_inputs()
    cost_summary["cost_sensitivity_status"] = "cost_robust_100bps"
    decision = build_decision_ok(runner, cost_summary, readout, make_badside(cost_100_pass=True, cost_50_pass=True), drift, make_morphology(cost_100_pass=True, cost_50_pass=True), dictionary)

    row = decision.iloc[0]
    assert row["decision_state"] == "13A3_reference_cost_repair_state_diagnostic_supported_requires_confirmatory_preflight"
    assert row["next_allowed_requirement"] == "requirement_13a4_compression_repair_state_confirmatory_preflight.md"
    assert row["effect_interpretation"] == "total_native_effect_only"
    assert bool(row["distribution_vs_state_edge_disentanglement_required"])
    assert not bool(row["sequence_mining_authorized"])


def test_morphology_margin_uses_route_cost_tier():
    runner = load_runner()
    morph = make_morphology(cost_100_pass=False, cost_50_pass=True)

    assert runner.morphology_route_pass(morph, "s", 0.005)
    assert not runner.morphology_route_pass(morph, "s", 0.01)


def test_validation_not_used_for_state_selection():
    runner = load_runner()
    readout = pd.DataFrame(
        {
            "state_id": ["train_ok", "train_ok", "train_ok", "val_only", "val_only", "val_only"],
            "split_bucket": ["train", "validation", "robustness"] * 2,
            "treated_n": [1000, 600, 600, 10, 600, 600],
            "treated_positive_n": [100, 60, 60, 1, 60, 60],
            "winner_rate_diff_vs_native": [0.01, 0.01, 0.01, 0.50, 0.50, 0.50],
        }
    )
    badside = pd.DataFrame(
        {
            "state_id": ["train_ok", "val_only"],
            "split_bucket": ["train", "train"],
            "cost_buffer_return": [0.01, 0.01],
            "lower_first_uplift_vs_compression_base": [-0.01, -0.01],
            "utility_proxy_per_entry": [0.01, 0.10],
        }
    )
    dictionary = pd.DataFrame({"state_id": ["train_ok", "val_only"], "state_priority": [1, 2]})

    selected, _cost = runner.select_train_state(readout, badside, dictionary, {"thresholds": {}})

    assert selected == "train_ok"


def test_full_native_frame_does_not_apply_compression_control_smd_fail():
    runner = load_runner()
    panel = tiny_panel()
    panel["split"] = ["validation", "validation", "validation", "validation"]
    state_matrix = pd.DataFrame({"row_id": panel["row_id"], "s": [True, False, False, False]})

    readout = runner.build_composite_native_readout(panel, state_matrix, {"composite_states": [{"state_id": "s"}], "thresholds": {"min_eval_treated_n": 1, "min_eval_positive_n": 1}})
    drift = runner.build_denominator_drift(panel, state_matrix, {"composite_states": [{"state_id": "s"}], "thresholds": {}})

    assert "max_standardized_diff" not in readout.columns
    assert len(drift) > 0


def test_relative_board_drift_not_absolute_60pct_rule():
    runner = load_runner()
    panel = tiny_panel().iloc[:3].copy()
    panel["split"] = "validation"
    panel["board_bucket"] = "main_board"
    state_matrix = pd.DataFrame({"row_id": panel["row_id"], "s": [True, True, False]})

    drift = runner.build_denominator_drift(panel, state_matrix, {"composite_states": [{"state_id": "s"}], "thresholds": {}})
    board = drift.loc[drift["drift_axis"].eq("board")]

    assert board["treated_share"].max() == 1.0
    assert board["drift_status"].astype(str).eq("primary_pass").all()


def test_morphology_auc_margin_without_utility_margin_fails():
    runner = load_runner()
    morph = pd.DataFrame(
        {
            "state_id": ["s", "s"],
            "split_bucket": ["validation", "robustness"],
            "cost_buffer_return": [0.005, 0.005],
            "auc_margin_vs_broad": [0.10, 0.10],
            "utility_margin_vs_broad": [-0.01, -0.01],
            "independent_evidence_status": ["morphology_rediscovery_without_independent_utility", "morphology_rediscovery_without_independent_utility"],
        }
    )

    assert not runner.morphology_route_pass(morph, "s", 0.005)


def test_cost_scan_self_utility_not_margin():
    runner = load_runner()
    panel = tiny_panel()
    mask = pd.Series([True, False, False, False], index=panel.index)

    row = runner.cost_sensitivity_row("scope", "x", "13A3_composite_state", "train", panel, mask, 0.0, {"bootstrap": {"n_resamples": 5, "min_valid_replicates": 1}})

    assert "self_utility_proxy_per_entry" in row
    assert "utility_margin_vs_native" not in row
    assert "utility_margin_vs_compression_base" not in row


def test_positive_decision_requires_distribution_edge_handoff():
    runner = load_runner()
    readout, dictionary, cost_summary, drift = decision_inputs()
    cost_summary["cost_sensitivity_status"] = "cost_robust_100bps"

    decision = build_decision_ok(runner, cost_summary, readout, make_badside(cost_100_pass=True, cost_50_pass=True), drift, make_morphology(cost_100_pass=True, cost_50_pass=True), dictionary)
    row = decision.iloc[0]

    assert row["effect_interpretation"] == "total_native_effect_only"
    assert bool(row["distribution_vs_state_edge_disentanglement_required"])


def test_decision_precedence():
    runner = load_runner()
    readout, dictionary, cost_summary, drift = decision_inputs()
    badside = make_badside(cost_100_pass=True, cost_50_pass=True)
    morphology = make_morphology(cost_100_pass=False, cost_50_pass=False)
    drift_fail = pd.DataFrame({"state_id": ["s"], "drift_status": ["fail_extreme_drift"]})

    input_fail = build_decision_ok(runner, cost_summary, readout, badside, drift_fail, morphology, dictionary, input_status="fail").iloc[0]
    morph_fail = build_decision_ok(runner, cost_summary, readout, badside, drift_fail, morphology, dictionary).iloc[0]

    assert input_fail["decision_state"] == "13A3_blocked_input_or_lineage_failure"
    assert morph_fail["decision_state"] == "13A3_stop_morphology_rediscovery_without_independent_utility"


def test_13a2_already_authorized_gets_specific_state():
    runner = load_runner()
    readout, dictionary, cost_summary, drift = decision_inputs()

    decision = build_decision_ok(
        runner,
        cost_summary,
        readout,
        make_badside(cost_100_pass=True, cost_50_pass=True),
        drift,
        make_morphology(cost_100_pass=True, cost_50_pass=True),
        dictionary,
        upstream_13a2_status="fail",
        upstream_13a2_reason="already_authorized",
    )

    assert decision.iloc[0]["decision_state"] == "13A3_blocked_upstream_13a2_already_authorized"


def test_row_level_cache_audit_detects_bad_filter_coverage():
    runner = load_runner()
    panel = tiny_panel()
    filter_matrix = pd.DataFrame({"row_id": [1, 2, 3], "f": [True, False, False]})
    token_matrix = pd.DataFrame({"row_id": [1, 2, 3, 4]})
    base_panel = pd.DataFrame({"row_id": [1], "split": ["train"]})
    dictionary = pd.DataFrame({"state_id": ["s"], "source_13a2_filter_id": ["f"], "state_reproduction_status": ["pass"]})

    audit = runner.build_row_level_cache_audit(panel, filter_matrix, token_matrix, base_panel, dictionary, 0.01, {"upstream_13a2_manifest": Path("/no/such/file")})

    row = audit.loc[audit["cache_check_id"].eq("filter_matrix.coverage_equals_native")].iloc[0]
    assert row["cache_status"] == "fail"
