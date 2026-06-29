from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_postmortem_continuation_utility_failure_decomposition.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16e_postmortem_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def base_config():
    return {
        "expected_16e": {
            "decision_state": "16E_utility_diagnostic_not_supported",
            "next_allowed_requirement": "none",
            "utility_interpretation": "drawdown_reduction_only_return_not_supported",
            "primary_label_id": "continuation_survival_h20_no_deep_drawdown",
            "selected_threshold_id": "up50pct",
            "primary_horizon_sessions": 20,
            "primary_model_id": "ridge_logistic_bar_state_v1",
            "primary_policy_id": "defense_bottom_30pct_continuation_score_v1",
            "primary_action_semantics_id": "full_avoidance_cash_h20_close_to_close_v1",
            "primary_round_trip_defense_cost_bps": 50,
            "threshold_value": 0.457071,
            "primary_return_utility_gate": "fail",
            "drawdown_avoidance_gate": "pass",
            "delay_stress_gate": "fail",
            "context_power_gate": "pass",
            "context_utility_gate": "fail",
            "six_cell_reconciliation_gate": "pass",
            "search_accounting_gate": "pass",
        },
        "diagnostic": {
            "primary_cost_bps": 50,
            "epsilon": 1e-12,
            "replay_tolerance": 1e-9,
            "score_decile_count": 10,
            "candidate_defend_region_deciles": [1, 2, 3],
            "monotone_spearman_min": 0.6,
            "non_monotone_abs_spearman_max": 0.3,
            "inverted_spearman_max": -0.6,
            "robustness_unstable_spearman_min": 0.3,
            "defended_positive_upside_mean_ratio_min": 0.80,
            "defended_positive_upside_q75_ratio_min": 0.80,
            "loss_avoidance_efficiency_min": 1.0,
            "defended_negative_drawdown_median_min": 0.10,
            "defended_positive_upside_median_max": 0.08,
            "drawdown_to_upside_median_ratio_min": 1.50,
        },
        "power_gates": {
            "min_rows_per_score_decile_train": 1,
            "min_rows_per_score_decile_robustness": 1,
        },
    }


def make_panel(split_trends: dict[str, list[float]] | None = None) -> pd.DataFrame:
    split_trends = split_trends or {
        "train": [i / 100.0 for i in range(1, 11)],
        "robustness": [i / 100.0 for i in range(1, 11)],
        "validation": [i / 100.0 for i in range(1, 11)],
    }
    rows = []
    for split, trend in split_trends.items():
        for decile, base_ret in enumerate(trend, start=1):
            specs = [
                ("defended_positive", "defend_next_h20", "positive", max(base_ret + 0.05, 0.01), -0.04, -max(base_ret + 0.05, 0.01), 0.04),
                ("defended_negative", "defend_next_h20", "negative", base_ret - 0.20, -0.18, -(base_ret - 0.20), 0.18),
                ("defended_neutral", "defend_next_h20", "neutral", base_ret - 0.02, -0.05, -(base_ret - 0.02), 0.05),
                ("continued_positive", "continue_next_h20", "positive", base_ret + 0.04, -0.02, 0.0, 0.0),
                ("continued_negative", "continue_next_h20", "negative", base_ret - 0.15, -0.14, 0.0, 0.0),
                ("continued_neutral", "continue_next_h20", "neutral", base_ret, -0.03, 0.0, 0.0),
            ]
            for i, (cell, action, label, ret, dd, inc, avoided) in enumerate(specs):
                rows.append(
                    {
                        "step_id": f"{split}-{decile}-{i}",
                        "policy_id": "defense_bottom_30pct_continuation_score_v1",
                        "threshold_value": 0.457071,
                        "cluster_split_bucket": split,
                        "split_bucket": split,
                        "cost_bps": 50,
                        "score": float(decile),
                        "model_id": "ridge_logistic_bar_state_v1",
                        "candidate_action": action,
                        "continue_return_h20": ret,
                        "continue_max_drawdown_h20": dd,
                        "policy_net_return_h20": ret + inc,
                        "incremental_net_return_h20": inc,
                        "drawdown_avoided_abs": avoided,
                        "cell_id": cell,
                        "label_class": label,
                        "known_failed_context_any": decile <= 2,
                        "late_rescue_context": False,
                        "non_known_failed_context": decile > 2,
                        "non_late_rescue_context": True,
                    }
                )
    return pd.DataFrame(rows)


def split_readout_from_panel(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, cost), sub in panel.groupby(["split_bucket", "cost_bps"], sort=False):
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": cost,
                "full_denominator_sum_incremental_return": sub["incremental_net_return_h20"].sum(),
            }
        )
    return pd.DataFrame(rows)


def six_cell_from_panel(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, cost, cell), sub in panel.groupby(["split_bucket", "cost_bps", "cell_id"], sort=False):
        rows.append(
            {
                "split_bucket": split,
                "context_stratum": "all_steps",
                "cost_bps": cost,
                "cell_id": cell,
                "cell_step_n": len(sub),
                "continue_return_sum": sub["continue_return_h20"].sum(),
                "policy_net_return_sum": sub["policy_net_return_h20"].sum(),
                "incremental_return_sum": sub["incremental_net_return_h20"].sum(),
                "drawdown_avoided_abs_sum": sub["drawdown_avoided_abs"].sum(),
            }
        )
    return pd.DataFrame(rows)


def write_replay_inputs(tmp_path: Path, panel: pd.DataFrame):
    split_path = tmp_path / "utility_by_split_readout.csv"
    six_path = tmp_path / "six_cell_utility_reconciliation.csv"
    split_readout_from_panel(panel).to_csv(split_path, index=False)
    six_cell_from_panel(panel).to_csv(six_path, index=False)
    return {
        "upstream_16e_utility_by_split_readout": split_path,
        "upstream_16e_six_cell_utility_reconciliation": six_path,
    }


def all_pass_upstream():
    return pd.DataFrame(
        [
            {
                "drawdown_avoidance_gate": "pass",
                "upstream_16e_authorization_gate": "pass",
                "upstream_16e_decision_state": "16E_utility_diagnostic_not_supported",
                "upstream_16e_utility_interpretation": "drawdown_reduction_only_return_not_supported",
            }
        ]
    )


def test_panel_cluster_split_bucket_renamed_to_split_bucket_with_lineage(tmp_path):
    panel = make_panel()
    panel = panel.drop(columns=["split_bucket"])
    panel_path = tmp_path / "utility_panel.parquet"
    panel.to_parquet(panel_path, index=False)
    loaded, gate, reason = r.load_and_validate_panel(base_config(), {"upstream_16e_utility_panel": panel_path})
    lineage = r.build_derived_metric_lineage_audit()
    rename = lineage.loc[lineage["derived_metric_id"].eq("split_bucket_normalization")].iloc[0]
    assert gate == "pass", reason
    assert "split_bucket" in loaded.columns
    assert rename["allowed_transform_type"] == "column_rename"
    assert rename["source_columns"] == "cluster_split_bucket"


def test_score_column_is_16d_passthrough_not_recomputed():
    lineage = r.build_derived_metric_lineage_audit()
    row = lineage.loc[lineage["derived_metric_id"].eq("score_passthrough")].iloc[0]
    assert "score" in row["source_columns"]
    assert row["allowed_transform_type"] == "pass_through"
    assert not bool(row["creates_new_return_cost_or_drawdown"])


def test_panel_incremental_net_return_replay_matches_16e_split_readout(tmp_path):
    panel = make_panel()
    resolved = write_replay_inputs(tmp_path, panel)
    replay = r.build_panel_aggregate_replay_audit(panel, resolved, tolerance=1e-9)
    split_replay = replay.loc[replay["source_value_column"].eq("full_denominator_sum_incremental_return")]
    assert not split_replay.empty
    assert split_replay["panel_value_column"].eq("incremental_net_return_h20").all()
    assert split_replay["replay_status"].eq("pass").all()


def test_panel_six_cell_replay_uses_cell_id_and_matches_16e_six_cell_readout(tmp_path):
    panel = make_panel()
    resolved = write_replay_inputs(tmp_path, panel)
    replay = r.build_panel_aggregate_replay_audit(panel, resolved, tolerance=1e-9)
    six = replay.loc[replay["source_table"].eq("six_cell_utility_reconciliation.csv")]
    assert not six.empty
    assert six["panel_groupby_columns"].str.contains("cell_id").all()
    assert six["replay_status"].eq("pass").all()


def test_attribution_identity_six_cells_sum_to_net_utility_total(tmp_path):
    panel = make_panel()
    resolved = write_replay_inputs(tmp_path, panel)
    attribution = r.build_failure_arithmetic_attribution(panel, resolved, tolerance=1e-9)
    assert attribution["attribution_identity_status"].eq("pass").all()


def test_continued_cells_incremental_sum_zero_within_tolerance(tmp_path):
    panel = make_panel()
    resolved = write_replay_inputs(tmp_path, panel)
    attribution = r.build_failure_arithmetic_attribution(panel, resolved, tolerance=1e-9)
    assert attribution["continued_incremental_zero_abs_max"].max() == 0.0
    assert attribution["continued_incremental_zero_status"].eq("pass").all()


def test_thick_tail_readout_uses_existing_continue_return_only():
    panel = make_panel()
    thick = r.build_thick_tail_readout(panel, base_config())
    assert {"all_positive", "defended_positive"} == set(thick["population"])
    assert "continue_return_h20" in r.build_derived_metric_lineage_audit().loc[
        lambda x: x["derived_metric_id"].eq("thick_tail_distribution"), "source_columns"
    ].iloc[0]


def test_score_bucket_monotonicity_spearman_and_flags():
    panel = make_panel()
    grouping = r.assign_score_deciles(panel, base_config())
    score = r.build_score_bucket_monotonicity_readout(grouping, base_config())
    train = score.loc[score["split_bucket"].eq("train")].iloc[0]
    assert train["monotonicity_spearman"] >= 0.99
    assert bool(train["monotone_increasing_flag"])
    assert not bool(train["non_monotone_flag"])


def test_robustness_monotonicity_unstable_caveat_when_spearman_between_0_3_and_0_6():
    cfg = base_config()
    panel = make_panel(
        {
            "train": [i / 100.0 for i in range(1, 11)],
            "robustness": [0.01, 0.02, 0.03, 0.01, 0.02, 0.01, 0.03, 0.02, 0.04, 0.03],
            "validation": [i / 100.0 for i in range(1, 11)],
        }
    )
    grouping = r.assign_score_deciles(panel, cfg)
    score = r.build_score_bucket_monotonicity_readout(grouping, cfg)
    rob = score.loc[score["split_bucket"].eq("robustness")].iloc[0]
    assert 0.3 <= rob["monotonicity_spearman"] < 0.6
    assert bool(rob["robustness_monotonicity_unstable_caveat"])


def test_inverted_orientation_maps_to_lineage_failure():
    flags = {
        "directionality_gate": "fail",
        "train_monotonicity_spearman": -1.0,
        "robustness_monotonicity_spearman": 1.0,
        "robustness_monotonicity_unstable_caveat": False,
        "train_monotone_increasing_flag": False,
        "robustness_monotone_increasing_flag": True,
        "train_non_monotone_flag": False,
        "robustness_non_monotone_flag": False,
        "train_inverted_flag": True,
        "robustness_inverted_flag": False,
        "thick_tail_mismatch_flag": False,
        "efficiency_above_one_in_any_bucket_flag": False,
        "partial_exposure_feasibility_hint": False,
        "path_a_supported": False,
        "path_b_supported": False,
        "path_c_supported": False,
        "continuation_as_action_mainline_closed": True,
        "score_monotonicity_estimated": True,
    }
    gates = {
        "input_artifact_gate": "pass",
        "upstream_16e_authorization_gate": "pass",
        "row_level_panel_gate": "pass",
        "panel_aggregate_replay_gate": "pass",
        "no_new_computation_gate": "pass",
        "attribution_identity_gate": "pass",
        "score_orientation_consistency_gate": "fail",
        "search_accounting_gate": "pass",
    }
    decision = r.decision_from_flags(base_config(), all_pass_upstream(), flags, gates)
    assert decision.loc[0, "decision_state"] == r.DECISION_LINEAGE


def test_non_monotone_maps_to_mainline_closed():
    flags = {
        "directionality_gate": "fail",
        "train_monotonicity_spearman": 0.0,
        "robustness_monotonicity_spearman": 0.0,
        "robustness_monotonicity_unstable_caveat": False,
        "train_monotone_increasing_flag": False,
        "robustness_monotone_increasing_flag": False,
        "train_non_monotone_flag": True,
        "robustness_non_monotone_flag": True,
        "train_inverted_flag": False,
        "robustness_inverted_flag": False,
        "thick_tail_mismatch_flag": False,
        "efficiency_above_one_in_any_bucket_flag": False,
        "partial_exposure_feasibility_hint": False,
        "path_a_supported": False,
        "path_b_supported": False,
        "path_c_supported": False,
        "continuation_as_action_mainline_closed": True,
        "score_monotonicity_estimated": True,
    }
    gates = {name: "pass" for name in [
        "input_artifact_gate", "upstream_16e_authorization_gate", "row_level_panel_gate",
        "panel_aggregate_replay_gate", "no_new_computation_gate", "attribution_identity_gate",
        "score_orientation_consistency_gate", "search_accounting_gate"
    ]}
    decision = r.decision_from_flags(base_config(), all_pass_upstream(), flags, gates)
    assert decision.loc[0, "decision_state"] == r.DECISION_CLOSED
    assert decision.loc[0, "next_allowed_requirement"] == "none"


def test_loss_avoidance_efficiency_by_bucket():
    panel = make_panel()
    grouping = r.assign_score_deciles(panel, base_config())
    score = r.build_score_bucket_monotonicity_readout(grouping, base_config())
    efficiency = r.build_loss_avoidance_efficiency(grouping, score, base_config())
    candidates = efficiency.loc[efficiency["candidate_defend_region_flag"].astype(bool)]
    assert not candidates.empty
    assert (candidates["loss_avoidance_efficiency"] > 1.0).any()


def test_drawdown_residual_feasibility_is_readout_only_no_partial_utility():
    drawdown = r.build_drawdown_residual_feasibility_readout(make_panel(), base_config())
    assert "partial_exposure_feasibility_hint" in drawdown.columns
    assert not any("partial_incremental" in col for col in drawdown.columns)
    assert drawdown["feasibility_note"].eq("readout_only_no_partial_exposure_utility_computed").all()


def test_path_priority_a_gt_b_gt_c_when_multiple_supported():
    flags = {
        "directionality_gate": "pass",
        "path_a_supported": True,
        "path_b_supported": True,
        "path_c_supported": True,
    }
    path = r.build_path_support_decision(flags)
    assert path.loc[path["path_id"].eq("A"), "selected_path_flag"].iloc[0]
    assert not path.loc[path["path_id"].eq("B"), "selected_path_flag"].iloc[0]


def test_path_c_support_condition_only_when_a_and_b_false():
    score = pd.DataFrame(
        [
            {"split_bucket": "train", "monotonicity_spearman": 1.0, "monotone_increasing_flag": True, "non_monotone_flag": False, "inverted_flag": False, "robustness_monotonicity_unstable_caveat": False},
            {"split_bucket": "robustness", "monotonicity_spearman": 1.0, "monotone_increasing_flag": True, "non_monotone_flag": False, "inverted_flag": False, "robustness_monotonicity_unstable_caveat": False},
        ]
    )
    thick = pd.DataFrame([{"split_bucket": "train", "thick_tail_mismatch_flag": False}, {"split_bucket": "robustness", "thick_tail_mismatch_flag": False}])
    efficiency = pd.DataFrame(columns=["split_bucket", "candidate_defend_region_flag", "decile_low_power", "efficiency_above_one_flag"])
    drawdown = pd.DataFrame([{"split_bucket": "train", "partial_exposure_feasibility_hint": False}, {"split_bucket": "robustness", "partial_exposure_feasibility_hint": False}])
    flags = r.aggregate_flags(score, thick, efficiency, drawdown, all_pass_upstream())
    assert flags["path_c_supported"]
    assert not flags["path_a_supported"]
    assert not flags["path_b_supported"]


def test_low_power_when_monotonicity_unestimable():
    flags = {
        "directionality_gate": "fail",
        "train_monotonicity_spearman": np.nan,
        "robustness_monotonicity_spearman": np.nan,
        "robustness_monotonicity_unstable_caveat": False,
        "train_monotone_increasing_flag": False,
        "robustness_monotone_increasing_flag": False,
        "train_non_monotone_flag": False,
        "robustness_non_monotone_flag": False,
        "train_inverted_flag": False,
        "robustness_inverted_flag": False,
        "thick_tail_mismatch_flag": False,
        "efficiency_above_one_in_any_bucket_flag": False,
        "partial_exposure_feasibility_hint": False,
        "path_a_supported": False,
        "path_b_supported": False,
        "path_c_supported": False,
        "continuation_as_action_mainline_closed": True,
        "score_monotonicity_estimated": False,
    }
    gates = {name: "pass" for name in [
        "input_artifact_gate", "upstream_16e_authorization_gate", "row_level_panel_gate",
        "panel_aggregate_replay_gate", "no_new_computation_gate", "attribution_identity_gate",
        "score_orientation_consistency_gate", "search_accounting_gate"
    ]}
    decision = r.decision_from_flags(base_config(), all_pass_upstream(), flags, gates)
    assert decision.loc[0, "decision_state"] == r.DECISION_LOW_POWER


def test_validation_not_used_for_path_selection():
    search = r.build_search_accounting_audit(base_config())
    assert not bool(search.loc[0, "validation_used_for_path_selection"])
    assert bool(search.loc[0, "robustness_used_as_confirmatory_path_gate"])
    assert not bool(search.loc[0, "robustness_used_for_threshold_tuning"])


def test_all_trading_deployment_and_chained_sim_authorizations_false():
    flags = {
        "directionality_gate": "fail",
        "train_monotonicity_spearman": 0.0,
        "robustness_monotonicity_spearman": 0.0,
        "robustness_monotonicity_unstable_caveat": False,
        "train_monotone_increasing_flag": False,
        "robustness_monotone_increasing_flag": False,
        "train_non_monotone_flag": True,
        "robustness_non_monotone_flag": True,
        "train_inverted_flag": False,
        "robustness_inverted_flag": False,
        "thick_tail_mismatch_flag": False,
        "efficiency_above_one_in_any_bucket_flag": False,
        "partial_exposure_feasibility_hint": False,
        "path_a_supported": False,
        "path_b_supported": False,
        "path_c_supported": False,
        "continuation_as_action_mainline_closed": True,
        "score_monotonicity_estimated": True,
    }
    gates = {name: "pass" for name in [
        "input_artifact_gate", "upstream_16e_authorization_gate", "row_level_panel_gate",
        "panel_aggregate_replay_gate", "no_new_computation_gate", "attribution_identity_gate",
        "score_orientation_consistency_gate", "search_accounting_gate"
    ]}
    decision = r.decision_from_flags(base_config(), all_pass_upstream(), flags, gates)
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


def test_all_required_publishable_outputs_have_declared_schema():
    outputs = r.output_paths()
    required = {
        "input_artifact_audit",
        "upstream_16e_authorization_audit",
        "no_new_computation_audit",
        "derived_metric_lineage_audit",
        "panel_aggregate_replay_audit",
        "failure_arithmetic_attribution",
        "defended_positive_thick_tail_readout",
        "score_bucket_monotonicity_readout",
        "loss_avoidance_efficiency_by_bucket",
        "drawdown_residual_feasibility_readout",
        "path_support_decision",
        "search_accounting_audit",
        "decision",
        "report",
        "manifest",
    }
    assert required.issubset(outputs)
