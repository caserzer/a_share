from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18d_payoff_state_feature_representation_diagnostic.py"
CONFIG = EXP / "configs/config_18d_payoff_state_feature_representation_diagnostic.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18d_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def load_config():
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def expected_candidate_ids() -> set[str]:
    return set(r.EXPECTED_CANDIDATE_FEATURE_IDS)


def test_config_declares_explicit_source_aliases():
    config = load_config()
    aliases = config["source_aliases"]
    assert aliases["pit_price_path_panel"] == ["stock_daily_qfq_dir"]
    assert aliases["pit_money_flow_proxy_panel"] == ["stock_daily_qfq_dir"]
    assert "sixteen_b_label_step_panel" in aliases["episode_geometry_panel"]


def test_runner_does_not_walk_arbitrary_candidate_source_directories():
    source = SCRIPT.read_text(encoding="utf-8")
    assert ".rglob(" not in source
    assert "os.walk" not in source


def test_legacy_18c_config_expected_next_is_audit_only_when_decision_manifest_next_is_none():
    result = context()
    upstream = result["upstream"]
    legacy = upstream.loc[upstream["source_table"].eq("config_18c_expected_block")]
    assert not legacy.empty
    observed = dict(zip(legacy["source_metric"], legacy["observed_value"], strict=False))
    assert observed["legacy_config_expected_next_mismatch"] == "true"
    assert observed["legacy_config_expected_next_status"] == "audit_only_not_authoritative"
    assert result["gates"]["upstream_18c_contract_gate"] == "pass"


def test_input_artifact_audit_records_config_key_resolver_priority_and_affected_family():
    result = context()
    audit = result["input_audit"]
    required = {
        "artifact_path",
        "source_artifact_alias",
        "config_path_key",
        "resolver_priority",
        "required_for_primary_candidate",
        "affected_family_ids",
        "resolved_source_status",
    }
    assert required.issubset(audit.columns)
    qfq_aliases = audit.loc[audit["config_path_key"].eq("stock_daily_qfq_dir"), "source_artifact_alias"].tolist()
    assert "pit_price_path_panel" in qfq_aliases
    assert "pit_money_flow_proxy_panel" in qfq_aliases
    assert audit.loc[audit["required"].astype(bool), "resolved_source_status"].eq("pass").all()


def test_candidate_inventory_materializes_exact_required_41_feature_universe():
    result = context()
    inv = result["inventory"]
    assert len(inv) == 41
    assert set(inv["candidate_feature_id"]) == expected_candidate_ids()
    assert inv["candidate_inventory_completeness_gate"].eq("pass").all()
    assert inv.groupby("candidate_family_id").size().to_dict() == {"M1": 11, "M2": 12, "M3": 8, "M4": 1, "M5": 9}


def test_candidate_inventory_completeness_gate_blocks_legacy_candidate_subset():
    config = load_config()
    inv = r.candidate_inventory(config)
    legacy_subset = inv.head(17).copy()
    summary = r.candidate_inventory_summary(legacy_subset, config["expected"]["total_required_candidate_feature_n"])
    assert summary["candidate_inventory_completeness_gate"] == "fail"
    assert summary["candidate_inventory_missing_feature_n"] > 0


def test_candidate_inventory_blocks_target_driven_added_or_removed_candidates():
    config = load_config()
    inv = r.candidate_inventory(config)
    changed = pd.concat(
        [
            inv.loc[~inv["candidate_feature_id"].eq("m1_episode_drawdown_pre_t0")],
            inv.iloc[[0]].assign(candidate_feature_id="target_driven_post_readout_feature", extra_feature_role="primary"),
        ],
        ignore_index=True,
    )
    summary = r.candidate_inventory_summary(changed, config["expected"]["total_required_candidate_feature_n"])
    assert summary["candidate_inventory_completeness_gate"] == "fail"
    assert summary["candidate_inventory_missing_feature_n"] == 1
    assert summary["candidate_inventory_extra_feature_n"] == 1


def test_candidate_dedup_groups_are_predeclared_before_target_readout():
    inv = context()["inventory"]
    assert inv["candidate_primary_dedup_group_id"].notna().all()
    m1_group = inv.loc[inv["candidate_primary_dedup_group_id"].eq("m1_range_location_group"), "candidate_feature_id"].tolist()
    m3_group = inv.loc[inv["candidate_primary_dedup_group_id"].eq("m3_downside_room_group"), "candidate_feature_id"].tolist()
    assert set(m1_group) == {"m1_close_location_episode_range", "m1_episode_recovery_ratio_to_high_t0"}
    assert set(m3_group) == {"m3_downside_crowding_to_episode_low", "m3_downside_room_to_episode_low_t0"}


def test_candidate_priority_score_uses_dedup_representatives_not_raw_alias_sum():
    prio = context()["prioritization"]
    assert (prio["raw_candidate_priority_score"] >= prio["candidate_priority_score"]).all()
    assert prio["priority_score_method"].eq("dedup_representative_abs_train_residual_ic").all()
    assert prio.loc[prio["candidate_family_id"].eq("M1"), "raw_candidate_priority_score"].iloc[0] > prio.loc[prio["candidate_family_id"].eq("M1"), "candidate_priority_score"].iloc[0]


def test_formula_missingness_rules_cover_zero_range_zero_close_and_insufficient_windows():
    assert np.isnan(r.safe_div(1.0, 0.0, 1e-12))
    assert np.isnan(r.safe_div(1.0, 1e-13, 1e-12))
    assert np.isnan(r.linear_r2(np.array([1.0, 1.0, 1.0, 1.0, 1.0]), 1e-12))
    assert r.money_flow_stats(pd.DataFrame({"close": [1, 2, 3], "amount_proxy": [1, 1, 1]}), 1e-12, 5)["net"] != r.money_flow_stats(pd.DataFrame({"close": [1, 2, 3], "amount_proxy": [1, 1, 1]}), 1e-12, 5)["net"]


def test_episode_geometry_derives_low_high_only_from_positions_lte_step_start_pos():
    result = context()
    config = load_config()
    floor = float(config["expected"]["candidate_min_finite_rate"])
    panel = result["feature_panel"]
    finite_low = panel["episode_low_pos_t0"].notna()
    finite_high = panel["episode_high_pos_t0"].notna()
    assert finite_low.mean() >= floor
    assert finite_high.mean() >= floor
    assert (panel.loc[finite_low, "episode_low_pos_t0"] <= panel.loc[finite_low, "step_start_pos"]).all()
    assert (panel.loc[finite_high, "episode_high_pos_t0"] <= panel.loc[finite_high, "step_start_pos"]).all()


def test_full_episode_cluster_end_after_t0_blocks_lifecycle_progress_primary_candidate():
    result = context()
    lineage = result["lineage"]
    row = lineage.loc[lineage["candidate_feature_id"].eq("m5_lifecycle_progress_to_t0")].iloc[0]
    assert bool(row["uses_full_episode_boundary_after_t0"])
    assert row["future_source_dependency_row_n"] > 0
    assert not bool(row["candidate_primary_allowed_after_lineage"])
    assert row["blocking_reason"] == "full_episode_boundary_after_t0"


def test_lineage_source_pos_replays_formula_dependencies_not_hardcoded_zero():
    lineage = context()["lineage"]
    lifecycle = lineage.loc[lineage["candidate_feature_id"].eq("m5_lifecycle_progress_to_t0")].iloc[0]
    assert lifecycle["source_pos_max_minus_step_start_pos"] == lifecycle["max_source_pos_minus_step_start_pos"]
    assert lifecycle["source_pos_max_minus_step_start_pos"] > 0
    primary = lineage.loc[lineage["candidate_primary_allowed_after_lineage"].astype(bool)]
    assert primary["source_pos_max_minus_step_start_pos"].le(0).all()


def test_lineage_audit_rolls_up_row_level_future_dependency_counts():
    lineage = context()["lineage"]
    required = {
        "row_n",
        "finite_candidate_value_row_n",
        "source_dependency_row_n",
        "future_source_dependency_row_n",
        "normalizer_dependency_row_n",
        "future_normalizer_dependency_row_n",
    }
    assert required.issubset(lineage.columns)
    assert lineage.loc[lineage["candidate_primary_allowed_after_lineage"].astype(bool), "future_source_dependency_row_n"].eq(0).all()


def test_reclaim_features_missing_when_reclaim_pos_t0_unavailable():
    result = context()
    lineage = result["lineage"]
    reclaim = lineage.loc[lineage["candidate_feature_id"].eq("m5_bars_since_reclaim")].iloc[0]
    assert reclaim["candidate_appendix_only"]
    assert reclaim["blocking_reason"] == "candidate_finite_rate_below_floor"


def test_m5_expanded_position_features_use_only_t0_known_denominators():
    result = context()
    panel = result["feature_panel"]
    for col in ["m5_low_to_t0_age_ratio", "m5_high_to_t0_age_ratio", "m5_low_before_high_t0", "m5_bars_since_episode_high_t0"]:
        assert col in panel.columns
        assert pd.to_numeric(panel[col], errors="coerce").notna().mean() >= 0.80
    lineage = result["lineage"]
    m5 = lineage.loc[lineage["candidate_family_id"].eq("M5") & lineage["candidate_primary_allowed_after_lineage"].astype(bool)]
    assert m5["future_normalizer_dependency_row_n"].eq(0).all()


def test_m5_lifecycle_progress_inventory_row_is_blocked_without_t0_endpoint_proof():
    result = context()
    inv = result["inventory"]
    pit = result["pit"]
    lifecycle_inv = inv.loc[inv["candidate_feature_id"].eq("m5_lifecycle_progress_to_t0")].iloc[0]
    lifecycle_pit = pit.loc[pit["candidate_feature_id"].eq("m5_lifecycle_progress_to_t0")].iloc[0]
    assert not bool(lifecycle_inv["primary_candidate_allowed_before_lineage"])
    assert lifecycle_inv["t0_frozen_endpoint_proof_status"] == "missing_or_not_proven"
    assert lifecycle_pit["t0_frozen_endpoint_proof_status"] == "missing_or_not_proven"
    assert not bool(lifecycle_pit["primary_allowed"])


def test_qfq_step_start_reconciliation_blocks_affected_primary_candidates_on_mismatch():
    panel = context()["feature_panel"]
    reconciled = panel.loc[panel["qfq_path_status"].eq("pass")]
    assert (reconciled["qfq_reconciled_step_start_date"].astype(str) == reconciled["step_start_date"].astype(str)).all()
    assert (pd.to_numeric(reconciled["qfq_reconciled_step_start_close"]) - pd.to_numeric(reconciled["step_start_qfq_close"])).abs().max() <= 1e-9


def test_entropy_windows_bins_log_base_and_epsilon_are_deterministic():
    result = context()
    panel = result["feature_panel"]
    for col in ["m1_return_sign_entropy_trailing20", "m1_path_transition_entropy_episode"]:
        values = pd.to_numeric(panel[col], errors="coerce").dropna()
        assert not values.empty
        assert values.between(0.0, 1.0).all()
    config = load_config()
    assert config["entropy_params"]["close_location_bins"] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    assert float(config["entropy_params"]["probability_epsilon"]) == 1e-12


def test_m1_expanded_morphology_features_use_episode_low_to_t0_or_trailing_windows():
    panel = context()["feature_panel"]
    cols = [
        "m1_episode_drawdown_pre_t0",
        "m1_episode_recovery_ratio_to_high_t0",
        "m1_pullback_from_episode_high_t0",
        "m1_close_location_trailing60_range",
        "m1_path_linearity_r2_low_to_t0",
        "m1_up_down_run_imbalance_20",
    ]
    for col in cols:
        assert col in panel.columns
        assert pd.to_numeric(panel[col], errors="coerce").notna().mean() >= 0.80


def test_m1_failed_repair_count_uses_only_complete_pre_t0_followup_windows():
    result = context()
    panel = result["feature_panel"]
    lineage = result["lineage"]
    assert pd.to_numeric(panel["m1_failed_repair_count_low_to_t0"], errors="coerce").notna().mean() >= 0.80
    row = lineage.loc[lineage["candidate_feature_id"].eq("m1_failed_repair_count_low_to_t0")].iloc[0]
    assert row["future_source_dependency_row_n"] == 0
    assert row["future_normalizer_dependency_row_n"] == 0


def test_m3_expanded_asymmetry_features_use_only_pre_t0_high_low_and_shadow_paths():
    panel = context()["feature_panel"]
    cols = [
        "m3_downside_room_to_episode_low_t0",
        "m3_upside_downside_room_ratio_t0",
        "m3_asymmetric_range_position_t0",
        "m3_upper_shadow_pressure_share_20",
    ]
    for col in cols:
        assert col in panel.columns
        assert pd.to_numeric(panel[col], errors="coerce").notna().mean() >= 0.80


def test_m3_failed_breakout_count_uses_only_complete_pre_t0_followup_windows():
    result = context()
    panel = result["feature_panel"]
    lineage = result["lineage"]
    assert pd.to_numeric(panel["m3_failed_breakout_count_pre_t0"], errors="coerce").notna().mean() >= 0.80
    row = lineage.loc[lineage["candidate_feature_id"].eq("m3_failed_breakout_count_pre_t0")].iloc[0]
    assert row["future_source_dependency_row_n"] == 0
    assert row["future_normalizer_dependency_row_n"] == 0


def test_money_flow_proxy_uses_amount_priority_and_labels_volume_times_close_fallback(tmp_path):
    p1 = tmp_path / "amount_first.csv"
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02"],
            "open": [1.0, 1.0],
            "high": [1.1, 1.2],
            "low": [0.9, 0.95],
            "close": [1.0, 1.1],
            "volume": [100.0, 100.0],
            "money": [200.0, 200.0],
            "amount": [300.0, 300.0],
        }
    ).to_csv(p1, index=False)
    p2 = tmp_path / "fallback.csv"
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02"],
            "open": [1.0, 1.0],
            "high": [1.1, 1.2],
            "low": [0.9, 0.95],
            "close": [2.0, 3.0],
            "volume": [10.0, 20.0],
        }
    ).to_csv(p2, index=False)
    assert r.normalize_qfq(p1)["amount_proxy"].iloc[0] == 300.0
    fallback = r.normalize_qfq(p2)
    assert fallback["amount_proxy"].tolist() == [20.0, 60.0]


def test_turnover_only_source_cannot_be_labeled_money_flow_proxy():
    inv = context()["inventory"]
    turnover = inv.loc[inv["candidate_feature_id"].eq("m2_turnover_compression_20_vs_60")].iloc[0]
    assert "turnover_rate" in turnover["source_columns"]
    assert "money-flow proxy" not in turnover["candidate_feature_name"].lower()


def test_m2_second_order_money_flow_proxy_windows_end_at_step_start():
    result = context()
    panel = result["feature_panel"]
    cols = [
        "m2_net_signed_money_flow_accel_5v20",
        "m2_positive_money_flow_share_accel_5v20",
        "m2_money_flow_reversal_accel_5v20",
        "m2_net_signed_money_flow_curvature_5_10_20",
        "m2_flow_price_divergence_persistence_20",
        "m2_high_amount_negative_bar_share_20",
        "m2_signed_flow_volatility_20",
        "m2_flow_concentration_top3_share_20",
    ]
    for col in cols:
        assert col in panel.columns
        assert pd.to_numeric(panel[col], errors="coerce").notna().mean() >= 0.80
    m2_lineage = result["lineage"].loc[result["lineage"]["candidate_family_id"].eq("M2")]
    assert m2_lineage["future_source_dependency_row_n"].eq(0).all()


def test_m2_second_order_money_flow_proxy_uses_f2_extended_train_residualization():
    orth = context()["orthogonal"]
    m2 = orth.loc[orth["candidate_family_id"].eq("M2")]
    assert set(m2["residualization_control_set_id"]) == {r.BASE_RESIDUALIZATION_ID, r.M2_EXT_RESIDUALIZATION_ID}
    train = m2.loc[m2["target_evidence_role"].eq("train_priority_prior")]
    assert not train.loc[train["residualization_control_set_id"].eq(r.BASE_RESIDUALIZATION_ID), "orthogonal_payoff_candidate"].astype(bool).any()
    assert train.loc[train["residualization_control_set_id"].eq(r.M2_EXT_RESIDUALIZATION_ID), "recommendation_eligible_residualization"].astype(bool).all()


def test_orthogonal_readout_unique_key_includes_residualization_control_set():
    orth = context()["orthogonal"]
    assert orth.duplicated(["candidate_family_id", "candidate_feature_id", "split_bucket", "residualization_control_set_id"]).sum() == 0


def test_m2_recommendation_uses_f2_extended_residualization_not_base_row():
    result = context()
    orth = result["orthogonal"]
    prio = result["prioritization"]
    m2_train = orth.loc[(orth["candidate_family_id"].eq("M2")) & orth["target_evidence_role"].eq("train_priority_prior")]
    assert m2_train.loc[m2_train["residualization_control_set_id"].eq(r.BASE_RESIDUALIZATION_ID), "orthogonal_payoff_candidate"].sum() == 0
    assert m2_train.loc[m2_train["residualization_control_set_id"].eq(r.M2_EXT_RESIDUALIZATION_ID), "orthogonal_payoff_candidate"].sum() > 0
    assert prio.loc[prio["candidate_family_id"].eq("M2"), "recommended_for_refresh"].astype(bool).iloc[0]


def test_m2_high_amount_negative_bar_threshold_is_t0_rolling_not_trainwide():
    result = context()
    panel = result["feature_panel"]
    lineage = result["lineage"]
    values = pd.to_numeric(panel["m2_high_amount_negative_bar_share_20"], errors="coerce").dropna()
    assert values.between(0, 1).all()
    row = lineage.loc[lineage["candidate_feature_id"].eq("m2_high_amount_negative_bar_share_20")].iloc[0]
    assert row["future_normalizer_dependency_row_n"] == 0


def test_capacity_probe_reuses_grouped_cv_leaf_rule_and_unweighted_mean_comparator():
    result = context()
    cap = result["capacity"]
    cv = cap.loc[cap["split_bucket"].eq("train_grouped_cv")]
    primary = cv.loc[cv["model_id"].eq("ridge_payoff_rank_h20_v1")].iloc[0]
    for _, row in cv.iterrows():
        assert np.isclose(row["cv_rank_ic_delta_vs_primary"], row["cv_mean_rank_ic_spearman"] - primary["primary_cv_rank_ic"])
    assert cv["cv_aggregation_method"].eq("unweighted_mean_across_pass_folds").all()


def test_medium_capacity_probe_caveat_blocks_positive_18e_handoff():
    gates = {gate: "pass" for gate in r.HARD_GATES}
    synthetic = {"capacity_bottleneck_flag": True}
    decision = r.decision_from_gates(gates, synthetic, ["M1"], [], []).iloc[0]
    assert decision["decision_state"] == "18D_capacity_bottleneck_on_existing_features"
    assert decision["next_allowed_requirement"] == "none"


def test_morphology_readout_includes_target_evidence_role_and_residual_retention():
    morph = context()["morphology"]
    required = {"target_evidence_role", "residual_retention", "orthogonal_payoff_candidate", "residualization_control_set_id"}
    assert required.issubset(morph.columns)
    assert not morph.loc[morph["target_evidence_role"].ne("train_priority_prior"), "orthogonal_payoff_candidate"].astype(bool).any()


def test_robustness_validation_rank_ic_cannot_change_recommended_for_refresh():
    result = context()
    orth = result["orthogonal"]
    prio = result["prioritization"]
    assert not orth.loc[orth["target_evidence_role"].ne("train_priority_prior"), "orthogonal_payoff_candidate"].astype(bool).any()
    assert prio["priority_source"].eq("lineage_then_train_prior_only").all()
    assert set(prio.loc[prio["recommended_for_refresh"].astype(bool), "candidate_family_id"]) >= {"M1", "M3", "M5"}


def test_search_accounting_blocks_policy_backtest_deployment_signal_and_trading():
    result = context()
    search = result["search"]
    expected = {
        "no_candidate_added_after_target_readout",
        "no_candidate_removed_after_target_readout",
        "candidate_inventory_completeness_verified_before_target_readout",
        "no_feature_selection_from_robustness",
        "no_feature_selection_from_validation",
        "no_final_model_training",
        "no_portfolio_backtest_authorized",
        "no_model_deployment_authorized",
        "no_production_signal_authorized",
        "no_live_trading_authorized",
    }
    assert expected.issubset(set(search["check_name"]))
    assert search["status"].eq("pass").all()
    decision = result["decision"].iloc[0]
    assert decision["decision_state"] == "18D_feature_representation_refresh_supported"
    assert decision["next_allowed_requirement"] == "requirement_18e_payoff_state_feature_matrix_refresh.md"
    for col in r.AUTH_FALSE_COLUMNS:
        assert not bool(decision[col])
