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


def test_config_declares_explicit_source_aliases_and_runner_does_not_walk_arbitrary_dirs():
    config = load_config()
    aliases = config["source_aliases"]
    assert aliases["pit_price_path_panel"] == ["stock_daily_qfq_dir"]
    assert aliases["pit_money_flow_proxy_panel"] == ["stock_daily_qfq_dir"]
    assert "sixteen_b_label_step_panel" in aliases["episode_geometry_panel"]
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
    reconciled = panel.loc[panel["qfq_path_status"].eq("pass")]
    assert (reconciled["qfq_reconciled_step_start_date"].astype(str) == reconciled["step_start_date"].astype(str)).all()
    assert (pd.to_numeric(reconciled["qfq_reconciled_step_start_close"]) - pd.to_numeric(reconciled["step_start_qfq_close"])).abs().max() <= 1e-9


def test_reclaim_features_missing_when_reclaim_pos_t0_unavailable():
    result = context()
    lineage = result["lineage"]
    reclaim = lineage.loc[lineage["candidate_feature_id"].eq("m5_bars_since_reclaim")].iloc[0]
    assert reclaim["candidate_appendix_only"]
    assert reclaim["blocking_reason"] == "candidate_finite_rate_below_floor"


def test_entropy_windows_bins_log_base_and_epsilon_are_deterministic():
    result = context()
    panel = result["feature_panel"]
    entropy_cols = ["m1_return_sign_entropy_trailing20", "m1_path_transition_entropy_episode"]
    for col in entropy_cols:
        values = pd.to_numeric(panel[col], errors="coerce").dropna()
        assert not values.empty
        assert values.between(0.0, 1.0).all()
    config = load_config()
    assert config["entropy_params"]["close_location_bins"] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    assert float(config["entropy_params"]["probability_epsilon"]) == 1e-12


def test_money_flow_proxy_uses_amount_priority_and_turnover_only_is_not_labeled_money_flow():
    result = context()
    config = load_config()
    floor = float(config["expected"]["candidate_min_finite_rate"])
    panel = result["feature_panel"]
    for col in [
        "m2_net_signed_money_flow_trailing20",
        "m2_positive_money_flow_share_trailing20",
        "m2_money_flow_persistence_trailing20",
    ]:
        assert pd.to_numeric(panel[col], errors="coerce").notna().mean() >= floor
    inventory = result["inventory"]
    turnover = inventory.loc[inventory["candidate_feature_id"].eq("m2_turnover_compression_20_vs_60")].iloc[0]
    assert "turnover_rate" in turnover["source_columns"]
    assert "money-flow proxy" not in turnover["candidate_feature_name"].lower()


def test_capacity_probe_reuses_grouped_cv_comparator_and_blocks_when_caveat_true():
    result = context()
    cap = result["capacity"]
    cv = cap.loc[cap["split_bucket"].eq("train_grouped_cv")]
    primary = cv.loc[cv["model_id"].eq("ridge_payoff_rank_h20_v1")].iloc[0]
    for _, row in cv.iterrows():
        assert np.isclose(row["cv_rank_ic_delta_vs_primary"], row["cv_mean_rank_ic_spearman"] - primary["primary_cv_rank_ic"])
    assert not bool(primary["medium_capacity_probe_caveat"])
    gates = {gate: "pass" for gate in r.HARD_GATES}
    synthetic = {"capacity_bottleneck_flag": True}
    decision = r.decision_from_gates(gates, synthetic, ["M1"], [], []).iloc[0]
    assert decision["decision_state"] == "18D_capacity_bottleneck_on_existing_features"
    assert decision["next_allowed_requirement"] == "none"


def test_morphology_readout_includes_evidence_role_and_validation_cannot_recommend():
    result = context()
    morph = result["morphology"]
    assert {"target_evidence_role", "residual_retention", "orthogonal_payoff_candidate"}.issubset(morph.columns)
    assert not morph.loc[morph["target_evidence_role"].ne("train_priority_prior"), "orthogonal_payoff_candidate"].astype(bool).any()
    prio = result["prioritization"]
    assert prio["priority_source"].eq("lineage_then_train_prior_only").all()
    assert set(prio.loc[prio["recommended_for_refresh"].astype(bool), "candidate_family_id"]) >= {"M1", "M3", "M5"}


def test_search_accounting_blocks_policy_backtest_deployment_signal_and_trading():
    result = context()
    search = result["search"]
    expected = {
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
