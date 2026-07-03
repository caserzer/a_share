from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18f_payoff_state_oracle_gap_bridge.py"
CONFIG = EXP / "configs/config_18f_payoff_state_oracle_gap_bridge.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18f_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def test_18f_requires_supported_18c_refresh_handoff():
    result = context()
    decision = result["decision"].iloc[0]
    upstream = result["upstream"]
    assert upstream["upstream_18c_refresh_contract_gate"].eq("pass").all()
    assert decision["upstream_18c_refresh_contract_gate"] == "pass"

    config = r.load_config(CONFIG)
    gates = {gate: "pass" for gate in r.HARD_GATES}
    gates["upstream_18c_refresh_contract_gate"] = "fail"
    blocked = r.build_decision(config, gates, {}).iloc[0]
    assert blocked["decision_state"] == "18F_upstream_18c_refresh_contract_blocked"
    assert blocked["next_allowed_requirement"] == "none"


def test_18f_rejects_mixed_o4_o5_denominator_subtraction():
    result = context()
    oracle = result["oracle_reference_replay_audit"]
    assert oracle["oracle_denominator_contract_gate"].eq("pass").all()
    binary = result["binary_denominator_bridge"]
    assert binary["binary_bridge_used_as_primary_gate"].eq(False).all()
    assert binary["binary_bridge_role"].eq("appendix_sanity_only").all()

    config = r.load_config(CONFIG)
    gates = {gate: "pass" for gate in r.HARD_GATES}
    gates["binary_boundary_gate"] = "fail"
    blocked = r.build_decision(config, gates, {}).iloc[0]
    assert blocked["decision_state"] == "18F_oracle_gap_contract_blocked"


def test_18f_score_panel_joins_exactly_to_18e_matrix():
    result = context()
    audit = result["score_matrix_join_audit"]
    checks = dict(zip(audit["check_id"], audit["observed_value"], strict=False))
    assert checks["primary_identity_key_columns"] == "step_id|label_id"
    assert checks["full_lineage_key_columns"] == "step_id|label_id|threshold_id|horizon_sessions|instrument|episode_cluster_id|step_index|step_start_date|step_end_date"
    assert checks["score_panel_to_18e_matrix_join_type"] == "one_to_one"
    assert int(checks["joined_row_n"]) == 23405
    assert int(checks["unmatched_score_panel_row_n"]) == 0
    assert int(checks["unmatched_matrix_row_n"]) == 0
    assert int(checks["target_value_mismatch_n"]) == 0
    assert int(checks["model_ready_feature_mismatch_n"]) == 0


def test_18f_replays_o5_incremental_identity():
    result = context()
    audit = result["score_matrix_join_audit"]
    checks = dict(zip(audit["check_id"], audit["observed_value"], strict=False))
    assert float(checks["joined_o5_incremental_max_abs_diff"]) <= 1e-9
    assert int(checks["joined_o5_incremental_formula_mismatch_n"]) == 0
    assert result["decision"].iloc[0]["o5_identity_replay_gate"] == "pass"


def test_18f_blocks_learned_utility_above_o5_upper_bound():
    config = r.load_config(CONFIG)
    gates = {gate: "pass" for gate in r.HARD_GATES}
    gates["o5_upper_bound_contract_gate"] = "fail"
    decision = r.build_decision(config, gates, {"o5_upper_bound_violation": True}).iloc[0]
    assert decision["decision_state"] == "18F_oracle_gap_contract_blocked"


def test_18f_operating_points_are_train_frozen():
    result = context()
    freeze = result["score_operating_point_freeze"]
    assert freeze["cutoff_source_split"].eq("train").all()
    assert freeze["split_local_threshold_recompute_used"].eq(False).all()
    assert set(freeze["operating_point_id"]) >= {
        "defend_bottom30_continue_rest",
        "continue_top10_defend_rest",
    }


def test_18f_primary_utility_uses_labelable_full_denominator():
    result = context()
    utility = result["learned_payoff_state_utility_bridge"]
    primary = utility.loc[
        utility["split_bucket"].eq("robustness")
        & utility["operating_point_id"].eq("defend_bottom30_continue_rest")
    ].iloc[0]
    assert primary["denominator_type"] == "labelable_full"
    assert int(primary["row_n"]) == 2496
    assert int(primary["neutral_row_n"]) == 624
    assert result["decision"].iloc[0]["decision_state"] == "18F_utility_bridge_not_supported"


def test_18f_utility_decomposition_residual_is_exact():
    result = context()
    utility = result["learned_payoff_state_utility_bridge"]
    assert utility["utility_bridge_status"].eq("pass").all()
    assert utility["residual_reconciliation_term"].abs().max() <= 1e-12


def test_18f_replays_18c_topk_removed_feature_sets():
    result = context()
    outputs = r.output_paths()
    source = pd.read_csv(
        EXP / "outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/topk_removal_sensitivity.csv"
    )
    bridge = result["topk_bootstrap_utility_bridge"]
    for sid in ["top1_abs_coefficient_removed", "top3_abs_coefficient_removed", "top5_abs_coefficient_removed"]:
        expected = source.loc[source["split_bucket"].eq("robustness") & source["sensitivity_id"].eq(sid), "removed_feature_names"].iloc[0]
        observed = bridge.loc[bridge["sensitivity_id"].eq(sid), "removed_feature_names"].iloc[0]
        assert observed == expected
    assert outputs["manifest"].exists()


def test_18f_replays_18c_family_removed_feature_sets_from_family_table():
    result = context()
    source = pd.read_csv(
        EXP / "outputs/publishable/tables/18C_refresh_payoff_state_separability_diagnostic/family_removal_sensitivity.csv"
    )
    bridge = result["topk_bootstrap_utility_bridge"]
    for sid in ["family_F4_removed", "family_M1_removed", "family_M2_removed", "family_M3_removed", "family_M5_removed"]:
        expected = source.loc[source["split_bucket"].eq("robustness") & source["sensitivity_id"].eq(sid), "removed_feature_names"].iloc[0]
        observed = bridge.loc[bridge["sensitivity_id"].eq(sid), "removed_feature_names"].iloc[0]
        assert observed == expected


def test_18f_binary_bridge_is_appendix_only():
    result = context()
    binary = result["binary_denominator_bridge"]
    assert binary["binary_bridge_used_as_primary_gate"].eq(False).all()
    assert binary["binary_bridge_status"].eq("appendix_sanity_only").all()
    assert result["decision"].iloc[0]["binary_boundary_gate"] == "pass"


def test_18f_positive_sacrifice_and_retention_gates_block_over_narrow_bridge():
    result = context()
    decision = result["decision"].iloc[0]
    assert decision["positive_sacrifice_gate"] == "fail"
    assert decision["payoff_retention_gate"] == "fail"
    assert float(decision["primary_positive_sacrifice_to_avoidance_ratio"]) > 1.0
    assert float(decision["primary_top30_payoff_retention_rate"]) < 0.70


def test_18f_bootstrap_uses_episode_cluster_id_and_2000_resamples():
    result = context()
    primary = result["cluster_bootstrap_utility_bridge"].iloc[0]
    assert primary["cluster_key"] == "episode_cluster_id"
    assert primary["metric_id"] == "learned_mean_incremental_return"
    assert int(primary["bootstrap_resample_n"]) == 2000
    assert int(primary["valid_bootstrap_resample_n"]) == 2000
    assert result["decision"].iloc[0]["primary_cluster_bootstrap_valid_resample_n"] == 2000
    bridge = result["topk_bootstrap_utility_bridge"]
    assert bridge["bootstrap_resample_n"].eq(2000).all()
    assert bridge["valid_bootstrap_resample_n"].eq(2000).all()
    assert result["decision"].iloc[0]["cluster_bootstrap_utility_gate"] == "fail"


def test_18f_validation_stress_cannot_tune_thresholds():
    result = context()
    validation = result["validation_stress_utility_bridge"].iloc[0]
    search = result["search_accounting_audit"].iloc[0]
    assert validation["validation_stress_role"] == "stress_readout_only"
    assert bool(search["validation_stress_readout_only"]) is True
    assert bool(search["no_threshold_tuning_on_validation"]) is True
    assert result["decision"].iloc[0]["validation_stress_gate"] == "fail"


def test_18f_search_accounting_blocks_policy_backtest_deployment_signal_and_trading():
    result = context()
    decision = result["decision"].iloc[0]
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False
    search = result["search_accounting_audit"].iloc[0]
    for col in [
        "no_entry_policy_authorized",
        "no_exit_policy_authorized",
        "no_holding_policy_authorized",
        "no_portfolio_backtest_authorized",
        "no_model_deployment_authorized",
        "no_production_signal_authorized",
        "no_live_trading_authorized",
    ]:
        assert bool(search[col]) is True


def test_18f_positive_decision_only_allows_requirement_19_policy_preflight():
    config = r.load_config(CONFIG)
    gates = {gate: "pass" for gate in r.HARD_GATES}
    metrics = {
        "learned_mean": 0.01,
        "o5_approximation_ratio": 0.34,
        "o2_approximation_ratio": 0.54,
        "o5_gap_remaining": 0.019,
        "o5_upper_bound_violation": False,
        "positive_sacrifice_to_avoidance_ratio": 0.5,
        "top30_payoff_retention_rate": 0.80,
        "top20_payoff_retention_rate": 0.85,
    }
    decision = r.build_decision(config, gates, metrics).iloc[0]
    assert decision["decision_state"] == "18F_payoff_state_policy_preflight_allowed"
    assert decision["next_allowed_requirement"] == "requirement_19_payoff_state_policy_preflight.md"
    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False


def test_18f_report_includes_required_oracle_gap_and_decomposition_sections():
    context()
    report = (EXP / "outputs/publishable/reports/payoff_state_oracle_gap_bridge_report.md").read_text(encoding="utf-8")
    for heading in [
        "## Policy Authorization Flags",
        "## Train-Frozen Operating Points",
        "## O5 And O2 Oracle Gap",
        "## Direct Incremental-Return Decomposition",
        "## Cluster Bootstrap Utility CI",
    ]:
        assert heading in report
    assert "O5_perfect_utility_primary" in report
    assert "positive_opportunity_cost" in report
