from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_sequential_continuation_utility_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_16e_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


def base_config():
    return {
        "policy": {
            "selected_threshold_id": "up50pct",
            "primary_horizon_sessions": 20,
            "primary_label_id": "continuation_survival_h20_no_deep_drawdown",
            "primary_model_id": "ridge_logistic_bar_state_v1",
            "primary_policy_id": "defense_bottom_30pct_continuation_score_v1",
            "next_allowed_requirement": "requirement_16f_chained_action_transition_freeze.md",
        },
        "action_semantics": {
            "primary_action_semantics_id": "full_avoidance_cash_h20_close_to_close_v1",
            "decision_time": "step_start_date close",
            "baseline_action": "blind_continue_next_h20",
            "continue_exposure": 1.0,
            "defend_exposure": 0.0,
            "defend_cash_return_h20": 0.0,
            "round_trip_defense_cost_bps_grid": [0, 50],
            "primary_round_trip_defense_cost_bps": 50,
            "delay_stress_id": "one_session_delay_close_to_close_v1",
            "validation_used_for_action_semantics_selection": False,
            "robustness_used_for_action_semantics_selection": False,
            "return_metric_used_for_action_semantics_selection": False,
            "cost_metric_used_for_action_semantics_selection": False,
        },
        "power_gates": {
            "train_labelable_step_n_min": 1,
            "train_defended_labelable_step_n_min": 1,
            "train_defended_positive_n_min": 1,
            "train_defended_negative_n_min": 1,
            "train_defended_neutral_n_min": 1,
            "train_episode_cluster_n_min": 1,
            "robustness_labelable_step_n_min": 1,
            "robustness_defended_labelable_step_n_min": 1,
            "robustness_defended_positive_n_min": 1,
            "robustness_defended_negative_n_min": 1,
            "robustness_defended_neutral_n_min": 1,
            "robustness_episode_cluster_n_min": 1,
            "validation_labelable_step_n_min": 999,
            "validation_defended_labelable_step_n_min": 999,
        },
        "context_gates": {
            "non_known_failed_train_labelable_step_n_min": 1,
            "non_known_failed_train_defended_labelable_step_n_min": 1,
            "non_known_failed_robustness_labelable_step_n_min": 1,
            "non_known_failed_robustness_defended_labelable_step_n_min": 1,
        },
        "utility_gates": {
            "defended_negative_drawdown_avoided_abs_mean_min": 0.08,
            "primary_cost_bps": 50,
            "zero_cost_bps": 0,
        },
    }


def base_action_rows(split: str = "train") -> pd.DataFrame:
    specs = [
        ("dp", "defend_next_h20", True, False, False, 0.10, -0.02, -0.01),
        ("dn", "defend_next_h20", False, True, False, -0.20, -0.25, -0.03),
        ("du", "defend_next_h20", False, False, True, 0.02, -0.05, 0.01),
        ("cp", "continue_next_h20", True, False, False, 0.08, -0.03, 0.01),
        ("cn", "continue_next_h20", False, True, False, -0.15, -0.18, -0.02),
        ("cu", "continue_next_h20", False, False, True, 0.01, -0.01, 0.00),
    ]
    rows = []
    for i, (suffix, action, pos, neg, neutral, ret, dd, first) in enumerate(specs):
        rows.append(
            {
                "step_id": f"{split}-{suffix}",
                "policy_id": "defense_bottom_30pct_continuation_score_v1",
                "label_id": "continuation_survival_h20_no_deep_drawdown",
                "threshold_id": "up50pct",
                "cluster_split_bucket": split,
                "instrument": "SH600000",
                "episode_cluster_id": f"{split}-cluster-{i}",
                "horizon_sessions": 20,
                "step_index": i,
                "step_start_pos": i * 20,
                "step_end_pos": i * 20 + 19,
                "step_start_date": "2020-01-01",
                "step_end_date": "2020-01-28",
                "step_start_qfq_close": 10.0,
                "step_end_qfq_close": 10.0 * (1 + ret),
                "max_drawdown_from_step_start": dd,
                "continuation_positive": pos,
                "continuation_negative": neg,
                "continuation_neutral": neutral,
                "is_binary_target": pos or neg,
                "candidate_action": action,
                "known_failed_context_any": suffix in {"dn", "cn"},
                "late_rescue_context": False,
                "non_known_failed_context": suffix not in {"dn", "cn"},
                "non_late_rescue_context": True,
                "label_class": "positive" if pos else "negative" if neg else "neutral",
                "continue_return_h20": ret,
                "continue_max_drawdown_h20": dd,
                "first_session_return": first,
            }
        )
    return pd.DataFrame(rows)


def utility_panel() -> pd.DataFrame:
    return r.expand_utility_panel(base_action_rows(), base_config())


def decision_action_panel() -> pd.DataFrame:
    return pd.concat([base_action_rows("train"), base_action_rows("robustness")], ignore_index=True)


def decision_frames(
    primary_50_pass: bool = True,
    zero_pass: bool = True,
    delay_pass: bool = True,
    non_known_pass: bool = True,
    known_pass: bool = True,
    leakage_caveat: str = "",
):
    split_rows = []
    for split in ["train", "robustness"]:
        for cost in [0, 50]:
            mean = 0.02 if (cost == 0 and zero_pass) or (cost == 50 and primary_50_pass) else -0.01
            split_rows.append(
                {
                    "split_bucket": split,
                    "cost_bps": cost,
                    "full_denominator_mean_incremental_return": mean,
                    "full_denominator_sum_incremental_return": mean * 10,
                    "drawdown_avoidance_gate": "pass",
                }
            )
    context_rows = []
    for split in ["train", "robustness"]:
        for context, passes in [("non_known_failed_context", non_known_pass), ("known_failed_context_any", known_pass)]:
            context_rows.append(
                {
                    "split_bucket": split,
                    "cost_bps": 50,
                    "context_stratum": context,
                    "labelable_step_n": 3,
                    "defended_labelable_step_n": 1,
                    "full_denominator_mean_incremental_return": 0.02 if passes else -0.01,
                    "full_denominator_mean_drawdown_avoided_abs": 0.01 if passes else 0.0,
                    "primary_return_utility_gate": "pass" if passes else "fail",
                    "drawdown_avoidance_gate": "pass" if passes else "fail",
                    "valid_context_power": True,
                    "context_utility_status": "pass" if passes else "fail",
                }
            )
    delay_rows = []
    for split in ["train", "robustness"]:
        delay_rows.append(
            {
                "split_bucket": split,
                "cost_bps": 50,
                "delay_stress_mean_incremental_return": 0.01 if delay_pass else -0.01,
            }
        )
    leakage = pd.DataFrame(
        [
            {
                "split_bucket": "robustness",
                "context_stratum": "all_steps",
                "cost_bps": 50,
                "continued_negative_leakage_caveat": leakage_caveat,
            }
        ]
    )
    return pd.DataFrame(split_rows), pd.DataFrame(context_rows), pd.DataFrame(delay_rows), leakage


def all_pass_gates():
    return {
        "input_artifact_gate": "pass",
        "upstream_16d_authorization_gate": "pass",
        "full_action_panel_rebuild_gate": "pass",
        "utility_price_path_gate": "pass",
        "action_semantics_gate": "pass",
        "policy_utility_binding_gate": "pass",
        "six_cell_reconciliation_gate": "pass",
        "neutral_utility_gate": "pass",
        "context_utility_rebuild_gate": "pass",
        "search_accounting_gate": "pass",
    }


def test_primary_action_semantics_full_avoidance_cash_formula():
    panel = utility_panel()
    defended_negative = panel.loc[panel["step_id"].eq("train-dn") & panel["cost_bps"].eq(50)].iloc[0]
    assert defended_negative["policy_net_return_h20"] == -0.005
    assert np.isclose(defended_negative["incremental_net_return_h20"], -0.005 - (-0.20))
    assert np.isclose(defended_negative["drawdown_avoided_abs"], 0.25)
    continued_positive = panel.loc[panel["step_id"].eq("train-cp") & panel["cost_bps"].eq(50)].iloc[0]
    assert np.isclose(continued_positive["policy_net_return_h20"], continued_positive["continue_return_h20"])
    assert continued_positive["incremental_net_return_h20"] == 0.0


def test_one_session_delay_stress_formula():
    panel = utility_panel()
    row = panel.loc[panel["step_id"].eq("train-dn") & panel["cost_bps"].eq(50)].iloc[0]
    assert np.isclose(row["delayed_policy_net_return_h20"], -0.03 - 0.005)
    assert np.isclose(row["delayed_incremental_net_return_h20"], (-0.03 - 0.005) - (-0.20))


def test_six_cell_reconciliation_uses_long_cost_schema_and_reconciles():
    panel = utility_panel()
    six, gate = r.build_six_cell_utility_reconciliation(panel)
    assert gate == "pass"
    assert {"split_bucket", "context_stratum", "cost_bps", "cell_id", "incremental_return_sum"}.issubset(six.columns)
    assert "incremental_return_sum_50bps" not in six.columns
    expected = panel.loc[panel["cluster_split_bucket"].eq("train") & panel["cost_bps"].eq(50), "incremental_net_return_h20"].sum()
    actual = six.loc[
        six["split_bucket"].eq("train")
        & six["context_stratum"].eq("all_steps")
        & six["cost_bps"].eq(50),
        "incremental_return_sum",
    ].sum()
    assert np.isclose(actual, expected)


def test_neutral_rows_remain_in_full_denominator():
    split = r.build_utility_by_split_readout(utility_panel(), base_config())
    row = split.loc[split["split_bucket"].eq("train") & split["cost_bps"].eq(50)].iloc[0]
    assert row["labelable_step_n"] == 6
    assert row["positive_n"] == 2
    assert row["negative_n"] == 2
    assert row["neutral_n"] == 2


def test_context_readout_includes_declared_core_gate_schema():
    panel = utility_panel()
    split = r.build_utility_by_split_readout(panel, base_config())
    context = r.build_utility_by_context_readout(panel, base_config())
    required = {"primary_return_utility_gate", "drawdown_avoidance_gate", "context_utility_status"}
    assert required.issubset(context.columns)
    context_all = context.loc[
        context["split_bucket"].eq("train")
        & context["context_stratum"].eq("all_steps")
        & context["cost_bps"].eq(50)
    ].iloc[0]
    split_row = split.loc[split["split_bucket"].eq("train") & split["cost_bps"].eq(50)].iloc[0]
    assert context_all["primary_return_utility_gate"] == split_row["primary_return_utility_gate"]
    assert context_all["drawdown_avoidance_gate"] == split_row["drawdown_avoidance_gate"]


def test_continued_negative_leakage_caveat_requires_split_primary_utility_pass():
    rows = base_action_rows()
    rows.loc[rows["step_id"].eq("train-cn"), "continue_return_h20"] = -0.50
    pass_panel = r.expand_utility_panel(rows, base_config())
    pass_split = r.build_utility_by_split_readout(pass_panel, base_config())
    pass_leakage = r.build_continued_negative_leakage_readout(pass_panel, pass_split)
    pass_row = pass_leakage.loc[
        pass_leakage["split_bucket"].eq("train")
        & pass_leakage["context_stratum"].eq("all_steps")
        & pass_leakage["cost_bps"].eq(50)
    ].iloc[0]
    assert pass_split.loc[pass_split["split_bucket"].eq("train") & pass_split["cost_bps"].eq(50), "primary_return_utility_gate"].iloc[0] == "pass"
    assert pass_row["continued_negative_residual_loss_share"] > 1.0
    assert pass_row["continued_negative_leakage_caveat"] == "utility_positive_but_leaky"

    fail_rows = rows.copy()
    fail_rows.loc[fail_rows["step_id"].eq("train-dp"), "continue_return_h20"] = 1.00
    fail_panel = r.expand_utility_panel(fail_rows, base_config())
    fail_split = r.build_utility_by_split_readout(fail_panel, base_config())
    fail_leakage = r.build_continued_negative_leakage_readout(fail_panel, fail_split)
    fail_row = fail_leakage.loc[
        fail_leakage["split_bucket"].eq("train")
        & fail_leakage["context_stratum"].eq("all_steps")
        & fail_leakage["cost_bps"].eq(50)
    ].iloc[0]
    assert fail_split.loc[fail_split["split_bucket"].eq("train") & fail_split["cost_bps"].eq(50), "primary_return_utility_gate"].iloc[0] == "fail"
    assert fail_row["continued_negative_residual_loss_share"] > 1.0
    assert fail_row["continued_negative_leakage_caveat"] == ""


def test_action_semantics_selection_flags_fail_closed():
    cfg = base_config()
    cfg["action_semantics"]["return_metric_used_for_action_semantics_selection"] = True
    audit = r.build_single_step_action_semantics_audit(cfg)
    assert audit.loc[0, "action_semantics_gate"] == "fail"


def test_action_semantics_cannot_be_selected_on_robustness_or_validation():
    for key in ["validation_used_for_action_semantics_selection", "robustness_used_for_action_semantics_selection"]:
        cfg = base_config()
        cfg["action_semantics"][key] = True
        audit = r.build_single_step_action_semantics_audit(cfg)
        assert audit.loc[0, "action_semantics_gate"] == "fail"
        assert key.split("_", 1)[0] in audit.loc[0, "blocking_reason"]


def test_decision_ready_only_allows_16f_requirement_despite_validation_low_power():
    split, context, delay, leakage = decision_frames()
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_READY
    assert decision.loc[0, "next_allowed_requirement"] == "requirement_16f_chained_action_transition_freeze.md"
    assert decision.loc[0, "validation_stress_low_power_caveat"]
    assert not decision.loc[0, "entry_policy_authorized"]
    assert not decision.loc[0, "chained_simulation_authorized"]


def test_decision_cost_fragility_when_0bps_passes_50bps_fails():
    split, context, delay, leakage = decision_frames(primary_50_pass=False, zero_pass=True)
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_FRAGILE


def test_decision_leakage_caveat_requires_primary_utility_pass():
    split, context, delay, leakage = decision_frames(primary_50_pass=False, zero_pass=False, leakage_caveat="utility_positive_but_leaky")
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "primary_return_utility_gate"] == "fail"
    assert decision.loc[0, "continued_negative_leakage_caveat"] == ""

    split, context, delay, leakage = decision_frames(primary_50_pass=True, leakage_caveat="utility_positive_but_leaky")
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "primary_return_utility_gate"] == "pass"
    assert decision.loc[0, "continued_negative_leakage_caveat"] == "utility_positive_but_leaky"


def test_decision_delay_fragility_when_primary_passes_delay_fails():
    split, context, delay, leakage = decision_frames(delay_pass=False)
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_FRAGILE


def test_context_power_failure_maps_to_low_power_not_context_concentrated():
    split, context, delay, leakage = decision_frames(non_known_pass=False, known_pass=True)
    context.loc[
        context["context_stratum"].eq("non_known_failed_context") & context["split_bucket"].eq("robustness"),
        "valid_context_power",
    ] = False
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_LOW_POWER


def test_decision_context_concentrated_only_when_non_known_fails_known_passes():
    split, context, delay, leakage = decision_frames(non_known_pass=False, known_pass=True)
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_CONTEXT


def test_decision_not_supported_when_primary_return_fails_and_zero_cost_does_not_rescue():
    split, context, delay, leakage = decision_frames(primary_50_pass=False, zero_pass=False)
    decision = r.build_decision(base_config(), all_pass_gates(), decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_NOT_SUPPORTED
    assert decision.loc[0, "utility_interpretation"] == "drawdown_reduction_only_return_not_supported"


def test_search_accounting_blocks_decision_before_utility_interpretation():
    split, context, delay, leakage = decision_frames()
    gates = all_pass_gates()
    gates["search_accounting_gate"] = "fail"
    decision = r.build_decision(base_config(), gates, decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_SEARCH


def test_decision_map_lineage_failure_blocks_before_utility_interpretation():
    split, context, delay, leakage = decision_frames()
    gates = all_pass_gates()
    gates["utility_price_path_gate"] = "fail"
    decision = r.build_decision(base_config(), gates, decision_action_panel(), split, context, delay, leakage)
    assert decision.loc[0, "decision_state"] == r.DECISION_LINEAGE
    assert decision.loc[0, "next_allowed_requirement"] == "none"


def test_report_includes_validation_stress_caveat_section():
    panel = r.expand_utility_panel(
        pd.concat([base_action_rows(split) for split in ["train", "robustness", "validation"]], ignore_index=True),
        base_config(),
    )
    split = r.build_utility_by_split_readout(panel, base_config())
    context = r.build_utility_by_context_readout(panel, base_config())
    six, _gate = r.build_six_cell_utility_reconciliation(panel)
    positive = r.build_positive_sacrifice_readout(panel)
    negative = r.build_negative_avoidance_readout(panel)
    leakage = r.build_continued_negative_leakage_readout(panel, split)
    neutral = r.build_neutral_utility_readout(panel)
    delay = r.build_cost_delay_stress_readout(panel, base_config())
    validation = r.build_validation_stress_utility_readout(panel)
    decision = pd.DataFrame(
        [
            {
                "decision_state": r.DECISION_READY,
                "next_allowed_requirement": "requirement_16f_chained_action_transition_freeze.md",
                "primary_round_trip_defense_cost_bps": 50,
            }
        ]
    )
    upstream = pd.DataFrame([{col: "" for col in ["authorization_status", "upstream_decision_state", "upstream_next_allowed_requirement", "primary_policy_id", "train_binary_step_n", "train_defended_negative_n", "robustness_binary_step_n", "robustness_defended_negative_n", "robustness_positive_sacrifice_rate", "robustness_continue_negative_leakage_rate"]}])
    action_audit = pd.DataFrame([{col: "" for col in ["action_panel_source", "primary_policy_row_count", "binary_step_count", "neutral_step_count", "threshold_value_replayed", "split_label_count_replay_status", "known_failed_context_replay_status", "full_action_panel_rebuild_status"]}])
    semantics = pd.DataFrame([{col: "" for col in ["primary_action_semantics_id", "decision_time", "baseline_action", "primary_round_trip_defense_cost_bps", "delay_stress_id", "action_semantics_gate"]}])
    price = pd.DataFrame([{col: "" for col in ["split_bucket", "labelable_step_n", "price_path_valid_step_n", "step_start_close_mismatch_n", "step_end_close_mismatch_n", "max_drawdown_replay_abs_diff_max", "delay_row_missing_n", "utility_price_path_gate"]}])
    search = pd.DataFrame([{col: "" for col in ["search_family", "primary_policy_id", "primary_action_semantics_id", "primary_round_trip_defense_cost_bps", "validation_used_for_selection", "robustness_used_for_selection", "return_metric_used_for_selection", "cost_metric_used_for_selection", "context_filter_used_for_selection", "search_accounting_gate"]}])
    report = r.render_report(decision, upstream, action_audit, semantics, price, split, context, six, positive, negative, leakage, neutral, delay, validation, search)
    assert "Validation Stress Caveat" in report
    assert "validation_stress_caveat" in report
    assert "Validation stress 只作 out-of-sample stress readout" in report
