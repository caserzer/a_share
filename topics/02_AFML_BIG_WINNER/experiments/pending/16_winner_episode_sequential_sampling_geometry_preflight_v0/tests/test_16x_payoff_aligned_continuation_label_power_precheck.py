from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16x_payoff_aligned_continuation_label_power_precheck.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16x_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def base_config():
    return {
        "expected_postmortem": {
            "decision_state": "16E_postmortem_mainline_closed_no_path_supported",
            "next_allowed_requirement": "none",
            "continuation_as_action_mainline_closed": True,
            "selected_path_id": "none",
            "directionality_gate": "fail",
            "train_monotonicity_spearman": 0.903030,
            "robustness_monotonicity_spearman": 0.030303,
            "robustness_non_monotone_flag": True,
            "thick_tail_mismatch_flag": True,
            "no_new_computation_gate": "pass",
            "tolerance": 1e-6,
        },
        "expected_16c": {
            "decision_state": "16C_sequential_continuation_separability_ready_for_policy_preflight",
            "primary_model_id": "ridge_logistic_bar_state_v1",
            "primary_model_feature_n": 2,
        },
        "target": {
            "payoff_target_id": "realized_h20_payoff_severity_v1",
            "payoff_base_column": "step_end_price_ratio_minus_one_for_label_rule",
            "close_ratio_tolerance": 1e-10,
            "primary_probe_universe": "binary_positive_negative_rows_only",
        },
        "probe": {
            "survival_probe_id": "survival_logistic_probe_v1",
            "payoff_probe_id": "payoff_rank_probe_v1",
            "survival_family": "ridge_logistic",
            "payoff_family": "ridge_regression",
            "logistic_c": 1.0,
            "ridge_alpha": 1.0,
            "random_seed": 20260629,
            "train_cv_fold_column": "episode_cluster_grouped_cv_fold",
            "cv_min_valid_fold_n": 2,
        },
        "bootstrap": {
            "cluster_key": "episode_cluster_id",
            "resample_n": 20,
            "ci_level": 0.95,
            "random_seed": 20260629,
            "min_valid_resample_rate": 0.90,
        },
        "power_gates": {
            "train_primary_probe_step_n_min": 4,
            "train_episode_cluster_n_min": 2,
            "robustness_primary_probe_step_n_min": 4,
            "robustness_episode_cluster_n_min": 2,
            "robustness_payoff_finite_rate_min": 0.99,
            "validation_primary_probe_step_n_min": 1,
        },
        "separability_gates": {
            "robustness_payoff_probe_rank_ic_spearman_min": 0.06,
            "payoff_decile_monotonicity_spearman_min": 0.6,
            "payoff_minus_survival_rank_ic_margin_min": 0.03,
            "cv_payoff_rank_ic_median_min": 0.06,
        },
    }


def make_contract():
    return pd.DataFrame(
        [
            {"feature_name": "f1", "allowed_primary_model_feature": True, "forbidden_as_model_feature": False},
            {"feature_name": "f2", "allowed_primary_model_feature": True, "forbidden_as_model_feature": False},
            {"feature_name": "step_end_price_ratio_minus_one_for_label_rule", "allowed_primary_model_feature": False, "forbidden_as_model_feature": True},
            {"feature_name": "target_binary", "allowed_primary_model_feature": False, "forbidden_as_model_feature": True},
        ]
    )


def make_panel():
    rows = []
    for split in ["train", "robustness", "validation"]:
        n = 8 if split != "validation" else 3
        for i in range(n):
            positive = i % 3 != 0
            negative = i % 3 == 0
            neutral = split == "validation" and i == 2
            if neutral:
                positive = negative = False
            start = 10.0
            payoff = 0.01 * (i + 1)
            rows.append(
                {
                    "step_id": f"{split}-{i}",
                    "cluster_split_bucket": split,
                    "instrument": f"S{i % 2}",
                    "episode_cluster_id": f"{split}-c{i // 2}",
                    "step_index": i,
                    "step_start_qfq_close": start,
                    "step_end_qfq_close": start * (1.0 + payoff),
                    "step_end_price_ratio_minus_one_for_label_rule": payoff,
                    "continuation_positive": positive,
                    "continuation_negative": negative,
                    "continuation_neutral": neutral,
                    "is_binary_target": not neutral,
                    "target_binary": 1.0 if positive else 0.0 if negative else np.nan,
                    "f1": float(i),
                    "f2": float(i % 2),
                }
            )
    return pd.DataFrame(rows)


def decision_components(payoff_ic=0.10, survival_ic=0.02, mono=True, power_gate="pass", search_gate="pass"):
    cfg = base_config()
    upstream = pd.DataFrame([{"observed_decision_state": "16E_postmortem_mainline_closed_no_path_supported", "upstream_postmortem_authorization_gate": "pass"}])
    feature = pd.DataFrame([{"feature_contract_n_actual": 2, "feature_contract_gate": "pass"}])
    lineage = pd.DataFrame(
        [
            {
                "train_primary_probe_step_n": 10,
                "robustness_primary_probe_step_n": 8,
                "validation_primary_probe_step_n": 3,
                "payoff_target_lineage_gate": "pass",
            }
        ]
    )
    no_new = pd.DataFrame([{"no_new_computation_gate": "pass"}])
    probe_spec = pd.DataFrame([{"fold_assignment_join_gate": "pass"}])
    rank = pd.DataFrame(
        [
            {"split_bucket": "train", "probe_id": cfg["probe"]["payoff_probe_id"], "rank_ic_spearman": 0.2, "cv_rank_ic_median": 0.12},
            {"split_bucket": "robustness", "probe_id": cfg["probe"]["payoff_probe_id"], "rank_ic_spearman": payoff_ic, "cv_rank_ic_median": 0.12},
            {"split_bucket": "robustness", "probe_id": cfg["probe"]["survival_probe_id"], "rank_ic_spearman": survival_ic, "cv_rank_ic_median": 0.05},
        ]
    )
    monotonicity = pd.DataFrame([{"split_bucket": "robustness", "payoff_decile_monotonicity_spearman": 1.0 if mono else 0.0, "payoff_monotone_flag": mono}])
    bootstrap = pd.DataFrame([{"cluster_bootstrap_rank_ic_ci_low": 0.01, "cluster_bootstrap_rank_ic_ci_high": 0.2, "ci_excludes_zero_flag": True, "bootstrap_resample_n": 20, "valid_bootstrap_resample_n": 20}])
    power = pd.DataFrame([{"power_gate": power_gate, "low_power_reason": "" if power_gate == "pass" else "low_power"}])
    search = pd.DataFrame([{"search_accounting_gate": search_gate}])
    return cfg, upstream, feature, lineage, no_new, probe_spec, rank, monotonicity, bootstrap, power, search


def test_all_required_publishable_outputs_have_declared_schema():
    outputs = r.output_paths()
    required = {
        "input_artifact_audit",
        "upstream_postmortem_authorization_audit",
        "feature_contract_audit",
        "payoff_target_lineage_audit",
        "no_new_computation_audit",
        "probe_spec_audit",
        "survival_vs_payoff_rank_ic_readout",
        "payoff_decile_monotonicity_readout",
        "cluster_bootstrap_rank_ic_readout",
        "power_gate_audit",
        "search_accounting_audit",
        "decision",
        "report",
        "manifest",
    }
    assert required.issubset(outputs)


def test_feature_contract_audit_excludes_forbidden_and_payoff_columns():
    cfg = base_config()
    decision = pd.DataFrame([{"primary_model_feature_n": 2}])
    audit = r.build_feature_contract_audit(make_contract(), make_panel(), decision, cfg)
    row = audit.iloc[0]
    assert row["feature_contract_gate"] == "pass"
    assert row["allowed_primary_model_feature_n"] == 2
    assert not bool(row["payoff_base_column_used_as_feature"])
    assert row["forbidden_feature_used_n"] == 0


def test_primary_probe_universe_binary_rows_only_and_neutral_stress_only():
    cfg = base_config()
    panel = r.prepare_panel(make_panel(), cfg)
    primary = r.split_primary_probe_universe(panel)
    assert set(primary["label_class"].unique()).issubset({"positive", "negative"})
    assert not primary["continuation_neutral"].astype(bool).any()
    lineage = r.build_payoff_target_lineage_audit(panel, cfg)
    assert bool(lineage.loc[0, "neutral_rows_excluded_from_primary_gate"])


def test_payoff_target_derived_from_existing_columns_only():
    cfg = base_config()
    panel = r.prepare_panel(make_panel(), cfg)
    lineage = r.build_payoff_target_lineage_audit(panel, cfg)
    no_new = r.build_no_new_computation_audit(cfg)
    assert lineage.loc[0, "payoff_target_lineage_gate"] == "pass"
    assert lineage.loc[0, "payoff_raw_vs_close_ratio_abs_diff_max"] < 1e-12
    assert no_new["no_new_computation_gate"].eq("pass").all()
    assert not no_new["creates_new_price_or_return_cost_or_drawdown"].astype(bool).any()


def test_fold_assignment_join_matches_train_primary_probe_universe():
    cfg = base_config()
    panel = r.prepare_panel(make_panel(), cfg)
    primary = r.split_primary_probe_universe(panel)
    train = primary.loc[primary["split_bucket"].eq("train")]
    fold = pd.DataFrame({"step_id": train["step_id"], "episode_cluster_grouped_cv_fold": [i % 2 for i in range(len(train))]})
    joined, gate, reason = r.join_train_folds(primary, fold, cfg)
    assert gate == "pass", reason
    assert len(joined) == len(train)
    assert joined["episode_cluster_grouped_cv_fold"].notna().all()


def test_bootstrap_spec_seed_ci_and_resample_count_frozen():
    cfg = base_config()
    scored = pd.DataFrame(
        {
            "split_bucket": ["robustness"] * 8,
            "episode_cluster_id": [f"c{i // 2}" for i in range(8)],
            "payoff_probe_score": np.arange(8, dtype=float),
            "payoff_raw": np.arange(8, dtype=float),
        }
    )
    boot = r.build_cluster_bootstrap_rank_ic_readout(scored, cfg)
    assert boot.loc[0, "bootstrap_resample_n"] == cfg["bootstrap"]["resample_n"]
    assert boot.loc[0, "bootstrap_ci_level"] == cfg["bootstrap"]["ci_level"]
    assert boot.loc[0, "bootstrap_random_seed"] == cfg["bootstrap"]["random_seed"]
    assert boot.loc[0, "valid_bootstrap_resample_n"] == cfg["bootstrap"]["resample_n"]


def test_decision_map_not_supported_mainline_stays_closed():
    args = decision_components(payoff_ic=0.05, survival_ic=0.04, mono=False)
    decision = r.decision_from_components(*args)
    assert decision.loc[0, "decision_state"] == r.DECISION_NOT_SUPPORTED
    assert decision.loc[0, "next_allowed_requirement"] == "none"
    assert bool(decision.loc[0, "continuation_as_action_mainline_closed"])


def test_decision_map_redo_authorized_only_label_start():
    args = decision_components(payoff_ic=0.12, survival_ic=0.02, mono=True)
    decision = r.decision_from_components(*args)
    assert decision.loc[0, "decision_state"] == r.DECISION_AUTHORIZED
    assert decision.loc[0, "next_allowed_requirement"] == r.NEXT_16B2
    assert bool(decision.loc[0, "payoff_aligned_label_redo_authorized"])
    assert bool(decision.loc[0, "continuation_as_action_mainline_closed"])


def test_decision_map_low_power_and_search_or_leakage():
    low_power_args = decision_components(power_gate="fail")
    low_power = r.decision_from_components(*low_power_args)
    assert low_power.loc[0, "decision_state"] == r.DECISION_LOW_POWER

    leakage_args = decision_components(search_gate="fail")
    leakage = r.decision_from_components(*leakage_args)
    assert leakage.loc[0, "decision_state"] == r.DECISION_LEAKAGE


def test_all_trading_utility_and_deployment_authorizations_false():
    decision = r.decision_from_components(*decision_components(payoff_ic=0.12, survival_ic=0.02, mono=True))
    for col in [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "chained_simulation_authorized",
        "portfolio_backtest_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
        "live_trading_authorized",
    ]:
        assert not bool(decision.loc[0, col])
