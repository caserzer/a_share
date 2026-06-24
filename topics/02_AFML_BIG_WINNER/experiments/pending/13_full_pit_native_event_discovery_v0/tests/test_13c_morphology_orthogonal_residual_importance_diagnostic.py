from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13c_morphology_orthogonal_residual_importance_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_13c_morphology_orthogonal_residual_importance_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_config(**overrides):
    cfg = {
        "selected_state_id": "s",
        "feature_clusters": {
            "cluster_drawdown_morphology": ["max_drawdown_20d", "ret_20d", "ret_60d", "rebound_from_20d_low"],
            "cluster_denominator_controls": ["board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket"],
            "cluster_compression": ["volatility_20d", "volatility_60d"],
            "cluster_position_strength": ["distance_from_20d_low", "close_vs_sma20", "close_position_20d"],
            "cluster_participation": ["turnover_zscore_20d", "amount_ratio_5d_20d", "volume_up_price_not_down_5d"],
        },
        "thresholds": {},
        "model": {"permutation_n": 3, "random_seed": 1},
    }
    cfg.update(overrides)
    return cfg


def decision_frames(
    residual_gate: str = "pass",
    mda_status: str = "pass",
    incremental_status: str = "pass",
    uniqueness_status: str = "pass_with_downstream_exact_t1_requirement",
    calibration_status: str = "calibration_pass",
    badside_lower_positive: bool = False,
):
    winner = 0.01 if residual_gate != "fail" else -0.01
    utility = 0.01 if residual_gate == "pass" else -0.01
    readout = pd.DataFrame(
        {
            "state_id": ["s", "s"],
            "split_bucket": ["validation", "robustness"],
            "residual_winner_diff": [winner, winner],
            "residual_utility_per_entry": [utility, utility],
            "residual_lower_first_diff": [0.01 if badside_lower_positive else -0.01, -0.01],
            "residual_fast_fail_diff": [0.0, 0.0],
        }
    )
    mda_rows = []
    if mda_status == "pass":
        for cluster in ["cluster_position_strength"]:
            for target in ["winner_positive", "utility_positive_50bps"]:
                for split in ["validation", "robustness"]:
                    mda_rows.append({"cluster_id": cluster, "target_id": target, "split_bucket": split, "mda_importance_ci_low": 0.01, "mda_importance": 0.01})
    elif mda_status == "morphology_only_importance":
        for split in ["validation", "robustness"]:
            mda_rows.append({"cluster_id": "cluster_drawdown_morphology", "target_id": "winner_positive", "split_bucket": split, "mda_importance_ci_low": 0.01, "mda_importance": 0.01})
    elif mda_status == "no_utility":
        for split in ["validation", "robustness"]:
            mda_rows.append({"cluster_id": "cluster_position_strength", "target_id": "winner_positive", "split_bucket": split, "mda_importance_ci_low": 0.01, "mda_importance": 0.01})
            mda_rows.append({"cluster_id": "cluster_position_strength", "target_id": "utility_positive_50bps", "split_bucket": split, "mda_importance_ci_low": -0.01, "mda_importance": -0.01})
    mda = pd.DataFrame(mda_rows)
    if mda.empty:
        mda = pd.DataFrame(columns=["cluster_id", "target_id", "split_bucket", "mda_importance_ci_low", "mda_importance"])

    if incremental_status == "pass":
        auc_delta, utility_delta = 0.01, 0.01
    elif incremental_status == "auc_only":
        auc_delta, utility_delta = 0.01, -0.01
    else:
        auc_delta, utility_delta = -0.01, -0.01
    incremental = pd.DataFrame(
        {
            "target_id": ["winner_positive", "winner_positive"],
            "split_bucket": ["validation", "robustness"],
            "auc_delta": [auc_delta, auc_delta],
            "utility_delta": [utility_delta, utility_delta],
        }
    )
    uniqueness = pd.DataFrame(
        {
            "state_id": ["s", "s"],
            "split_bucket": ["validation", "robustness"],
            "sample_uniqueness_gate_status": [uniqueness_status, uniqueness_status],
            "downstream_requirement_requires_exact_t1_rebuild": [uniqueness_status == "pass_with_downstream_exact_t1_requirement"] * 2,
        }
    )
    calibration = pd.DataFrame(
        {
            "target_id": ["winner_positive", "winner_positive"],
            "split_bucket": ["validation", "robustness"],
            "calibration_status": [calibration_status, calibration_status],
        }
    )
    search = pd.DataFrame({"search_accounting_status": ["diagnostic_posthoc_not_confirmatory"]})
    return readout, calibration, mda, incremental, uniqueness, search


def build_decision(runner, **kwargs):
    readout, calibration, mda, incremental, uniqueness, search = decision_frames(**kwargs)
    return runner.build_decision("pass", "pass", "", "pass", "pass", "pass", readout, calibration, mda, incremental, uniqueness, search, base_config()).iloc[0]


def test_path_resolution_contract():
    runner = load_runner()
    assert runner.topic_path("topics/02_AFML_BIG_WINNER/x").is_relative_to(runner.REPO_ROOT)
    assert runner.topic_path("data/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("experiments/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("outputs/x").is_relative_to(runner.EXPERIMENT_DIR)


def test_upstream_13a3_negative_decision_required():
    runner = load_runner()
    readout, calibration, mda, incremental, uniqueness, search = decision_frames()
    decision = runner.build_decision("pass", "fail_already_authorized", "upstream_13a3_already_authorized", "pass", "pass", "pass", readout, calibration, mda, incremental, uniqueness, search, base_config()).iloc[0]
    assert decision["decision_state"] == "13C_blocked_upstream_13a3_already_authorized"


def test_no_report_text_reconstruction():
    runner = load_runner()
    assert runner.REPORT_INPUT_KEYS == {"upstream_report_13a", "upstream_report_13a2", "upstream_report_13a3"}
    assert all(runner.lineage_role_for_artifact(k) == "lineage_report_only_not_row_truth" for k in runner.REPORT_INPUT_KEYS)


def test_required_composite_state_membership_reproduction():
    runner = load_runner()
    native = pd.DataFrame({"row_id": [1, 2, 3]})
    filters = pd.DataFrame({"row_id": [1, 2, 3], "f": [True, False, True]})
    dictionary = pd.DataFrame({"state_id": ["s"], "source_13a2_filter_id": ["f"], "state_reproduction_status": ["pass"]})
    matrix = runner.r13a3.build_composite_state_matrix(native, filters, dictionary)
    assert matrix["s"].tolist() == [True, False, True]


def test_train_frozen_bucket_thresholds():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "split": ["train"] * 10 + ["validation"] * 10,
            "native_scope": [True] * 20,
            "money_median_20d": list(range(10)) + list(range(100, 110)),
            "volatility_20d": list(range(10)) + list(range(100, 110)),
            "max_drawdown_20d": list(range(10)) + list(range(100, 110)),
        }
    )
    out, edges = runner.fit_train_frozen_buckets(panel, base_threshold=4, config={"residualization": {"quantile_bucket_n": 5, "decile_bucket_n": 10}})
    assert max(edges["liquidity_bucket"]) < 10
    assert out.loc[out["split"].eq("validation"), "liquidity_bucket"].nunique() == 1


def morphology_panel_for_residual_test():
    rows = []
    row_id = 1
    for cell, p in [("A", 0.8), ("B", 0.2)]:
        for treated in [True, False]:
            for i in range(50):
                y = i < int(50 * p)
                rows.append(
                    {
                        "row_id": row_id,
                        "native_scope": True,
                        "split_bucket": "train",
                        "split": "train",
                        "board_bucket": cell,
                        "calendar_year": 2020,
                        "liquidity_bucket": "l",
                        "volatility_bucket": "v",
                        "max_drawdown_20d_decile": cell,
                        "compression_severity_bucket": "c",
                        "max_drawdown_20d_quintile": cell,
                        "winner_positive": y,
                        "lower_first": False,
                        "fast_fail": False,
                        "row_utility_component_50bps": -0.01,
                        "s": treated if cell == "A" else False,
                    }
                )
                row_id += 1
    return pd.DataFrame(rows)


def test_residualization_controls_remove_morphology():
    runner = load_runner()
    panel, _design = runner.add_residuals(morphology_panel_for_residual_test())
    readout = runner.build_residual_state_effect_readout(panel, pd.DataFrame({"state_id": ["s"]}), base_config())
    row = readout.loc[readout["state_id"].eq("s") & readout["split_bucket"].eq("train")].iloc[0]
    full_native_raw = panel.loc[panel["s"], "winner_positive"].mean() - panel.loc[~panel["s"], "winner_positive"].mean()
    assert full_native_raw > 0
    assert abs(row["residual_winner_diff"]) < 1e-12


def test_residual_support_thresholds_are_hard_gates():
    runner = load_runner()
    panel, _design = runner.add_residuals(morphology_panel_for_residual_test())
    readout = runner.build_residual_state_effect_readout(
        panel,
        pd.DataFrame({"state_id": ["s"]}),
        base_config(residualization={"min_treated_per_cell": 20, "min_control_per_cell": 50, "min_positive_per_split": 45}),
    )
    row = readout.loc[readout["state_id"].eq("s") & readout["split_bucket"].eq("train")].iloc[0]
    assert row["cell_support_status"] == "insufficient_support"

    decision_readout, calibration, mda, incremental, uniqueness, search = decision_frames()
    decision_readout["cell_support_status"] = ["insufficient_support", "pass"]
    decision_readout["residual_winner_gate_status"] = ["insufficient_support", "pass"]
    decision = runner.build_decision("pass", "pass", "", "pass", "pass", "pass", decision_readout, calibration, mda, incremental, uniqueness, search, base_config()).iloc[0]
    assert decision["decision_state"] == "13C_stop_no_morphology_orthogonal_residual_effect"
    assert decision["primary_failure_reason"] == "residual_support_insufficient"


def test_required_feature_missing_fails_closed_but_optional_missing_passes():
    runner = load_runner()
    feature_clusters = pd.DataFrame(
        [
            {"feature_id": "close_vs_sma20", "required_flag": True, "feature_status": "missing_required"},
            {"feature_id": "range_width_20d", "required_flag": False, "feature_status": "optional_missing"},
        ]
    )
    status, reason = runner.feature_cluster_gate_status(feature_clusters)
    assert status == "fail"
    assert "close_vs_sma20" in reason

    optional_only = feature_clusters.loc[feature_clusters["feature_id"].eq("range_width_20d")]
    assert runner.feature_cluster_gate_status(optional_only) == ("pass", "")


def test_probability_only_no_utility_fails():
    runner = load_runner()
    decision = build_decision(runner, residual_gate="probability_only")
    assert decision["decision_state"] == "13C_stop_residual_probability_only_no_utility"


def test_clustered_mda_group_permutation():
    runner = load_runner()
    frame = pd.DataFrame({"g": ["x"] * 5, "a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
    out = runner.grouped_permute_cluster(frame, ["a", "b"], ["g"], np.random.default_rng(1))
    assert sorted(zip(out["a"], out["b"])) == sorted(zip(frame["a"], frame["b"]))


def test_morphology_only_importance_fails():
    runner = load_runner()
    decision = build_decision(runner, mda_status="morphology_only_importance")
    assert decision["decision_state"] == "13C_stop_morphology_only_importance"


def test_auc_only_incremental_gain_cannot_authorize():
    runner = load_runner()
    decision = build_decision(runner, incremental_status="auc_only")
    assert decision["decision_state"] == "13C_stop_residual_importance_no_utility_translation"


def test_purged_embargo_config_required():
    runner = load_runner()
    _panel, design = runner.add_residuals(morphology_panel_for_residual_test())
    assert design["purge_window_sessions"].eq(20).all()
    assert design["embargo_sessions"].eq(20).all()


def test_uniqueness_exact_or_downstream_requirement():
    runner = load_runner()
    decision = build_decision(runner)
    assert decision["decision_state"] == "13C_authorize_meta_labeling_feasibility_preflight"
    assert bool(decision["downstream_requirement_requires_exact_t1_rebuild"])
    decision2 = build_decision(runner, uniqueness_status="exact_uniqueness_unavailable")
    assert decision2["decision_state"] == "13C_stop_uniqueness_unavailable_for_downstream"


def test_sample_uniqueness_reconstructs_exact_t1_spans():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "native_scope": [True, True],
            "split_bucket": ["validation", "validation"],
            "s": [True, True],
            "instrument": ["000001", "000001"],
            "reference_date": ["2020-01-02", "2020-01-03"],
            "entry_pos": [10, 11],
            "horizon_sessions": [20, 20],
            "upper_first": [True, False],
            "lower_first": [False, True],
            "same_bar_conflict": [False, False],
            "time_to_upper": [2.0, np.nan],
            "time_to_lower": [np.nan, 2.0],
        }
    )
    uniqueness = runner.build_sample_uniqueness(panel, pd.DataFrame({"state_id": ["s"]}), base_config())
    row = uniqueness.loc[uniqueness["state_id"].eq("s") & uniqueness["split_bucket"].eq("validation")].iloc[0]
    assert row["t1_reconstruction_status"] == "exact_t1_reconstructed"
    assert row["sample_uniqueness_gate_status"] == "pass_with_exact_t1"
    assert not bool(row["downstream_requirement_requires_exact_t1_rebuild"])
    assert abs(row["mean_average_uniqueness"] - (2.0 / 3.0)) < 1e-12
    assert abs(row["mean_concurrency"] - (10.0 / 6.0)) < 1e-12


def test_decision_precedence():
    runner = load_runner()
    readout, calibration, mda, incremental, uniqueness, search = decision_frames()
    decision = runner.build_decision("fail:missing", "pass", "", "pass", "pass", "pass", readout, calibration, mda, incremental, uniqueness, search, base_config()).iloc[0]
    assert decision["decision_state"] == "13C_blocked_input_or_lineage_failure"


def test_no_bet_sizing_authorization():
    runner = load_runner()
    decision = build_decision(runner)
    assert not bool(decision["bet_sizing_authorized"])


def test_no_sequence_mining_authorization():
    runner = load_runner()
    decision = build_decision(runner)
    assert not bool(decision["sequence_mining_authorized"])


def test_residual_lower_first_does_not_hard_block_winner():
    runner = load_runner()
    decision = build_decision(runner, badside_lower_positive=True)
    assert decision["decision_state"] == "13C_authorize_meta_labeling_feasibility_preflight"
    assert decision["residual_badside_readout_status"] == "caveat_left_tail_residual_positive"


def test_broad_morphology_baseline_uses_train_frozen_threshold():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "native_scope": [True] * 200,
            "split_bucket": ["train"] * 100 + ["validation"] * 100,
            "broad_morphology_score": list(range(100)) + list(range(1000, 1100)),
            "s": [False] * 90 + [True] * 10 + [False] * 100,
        }
    )
    threshold = runner.broad_threshold_for_state(panel, "s")
    assert 88 <= threshold <= 90


def test_model_utility_proxy_delta_only():
    runner = load_runner()
    decision = build_decision(runner, incremental_status="pass")
    assert decision["decision_state"] == "13C_authorize_meta_labeling_feasibility_preflight"


def test_residual_calibration_caveat_does_not_hard_fail():
    runner = load_runner()
    decision = build_decision(runner, calibration_status="residual_drift_caveat")
    assert decision["decision_state"] == "13C_authorize_meta_labeling_feasibility_preflight"
    assert decision["effect_interpretation"] == "morphology_orthogonal_residual_diagnostic_only_with_residual_drift_caveat"
    assert bool(decision["calibration_recheck_required"])


def test_residual_calibration_audit_uses_oos_realized_rates():
    runner = load_runner()
    panel = morphology_panel_for_residual_test()
    val = panel.iloc[:20].copy()
    val["split_bucket"] = "validation"
    val["split"] = "validation"
    val["winner_positive"] = True
    panel = pd.concat([panel, val], ignore_index=True)
    panel, _design = runner.add_residuals(panel)
    calibration = runner.build_residual_calibration(panel, {"thresholds": {"binary_calibration_weighted_abs_error": 0.02}})
    val_rows = calibration.loc[calibration["target_id"].eq("winner_positive") & calibration["split_bucket"].eq("validation")]
    assert val_rows["realized_mean_in_split"].max() == 1.0
    assert val_rows["weighted_abs_calibration_error"].max() > 0
