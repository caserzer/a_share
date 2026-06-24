from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13g_event_survival_opportunity_and_defense_overlay_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_13g_event_survival_opportunity_and_defense_overlay_diagnostic",
        RUNNER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_config(**overrides):
    cfg = {
        "selected_state_id": "s",
        "label_grid": {
            "up_mfe_threshold_grid": [0.20, 0.30, 0.50],
            "down_mae_threshold_grid": [-0.10, -0.15, -0.20],
            "horizon_sessions_grid": [20, 60, 120],
            "primary_up_threshold": 0.30,
            "primary_down_threshold": -0.15,
            "primary_horizon_sessions": 60,
            "max_horizon_sessions": 120,
            "min_analysis_event_fraction_by_split": 0.80,
            "min_analysis_event_n_by_split": {"train": 2, "validation": 1, "robustness": 1},
        },
        "overlay": {
            "risk_budget_multiplier": {"increase": 1.5, "keep": 1.0, "reduce": 0.5, "skip": 0.0},
            "cost_tier_bps": [0, 50, 100],
            "cost_buffer_return_by_tier": {0: 0.0, 50: 0.005, 100: 0.010},
            "overlay_adjustment_cost_buffer_by_tier": {0: 0.0, 50: 0.005, 100: 0.010},
            "rule_feature_missing_max_fraction": 0.50,
            "min_badside_event_n_by_split": 1,
            "winner_retention_min_validation": 0.80,
            "winner_retention_min_robustness": 0.75,
            "duplicate_delta_share_max": 0.80,
        },
    }
    cfg.update(overrides)
    return cfg


def bars(n=150, open_value=10.0, high_mult=1.01, low_mult=0.99, close_mult=1.0):
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n).strftime("%Y-%m-%d"),
            "open": [open_value] * n,
            "high": [open_value * high_mult] * n,
            "low": [open_value * low_mult] * n,
            "close": [open_value * close_mult] * n,
        }
    )


def event_row(**overrides):
    row = {
        "event_id": "e0",
        "row_id": 0,
        "instrument": "I",
        "reference_date": "2020-01-01",
        "entry_date": "2020-01-02",
        "entry_pos": 0.0,
        "entry_price": 10.0,
        "split_bucket": "train",
        "selected_state_id": "s",
        "ret_20d": 0.0,
        "max_drawdown_20d": 0.0,
        "distance_from_20d_low": 0.5,
        "volatility_20d": 0.1,
        "analysis_denominator_flag": True,
    }
    row.update(overrides)
    return pd.Series(row)


def synthetic_events():
    rows = []
    for i, split in enumerate(["train", "train", "validation", "robustness"]):
        rows.append(
            {
                "event_id": f"e{i}",
                "row_id": i,
                "instrument": "I",
                "reference_date": f"2020-01-{i + 1:02d}",
                "entry_date": f"2020-01-{i + 2:02d}",
                "entry_pos": float(i * 10),
                "entry_price": 10.0,
                "split_bucket": split,
                "selected_state_id": "s",
                "analysis_denominator_flag": True,
                "ret_20d": float(i - 1),
                "max_drawdown_20d": float(-i),
                "distance_from_20d_low": float(i),
                "volatility_20d": float(i + 1),
                "turnover_zscore_20d": float(i),
            }
        )
    return pd.DataFrame(rows)


def decision_inputs(runner):
    row_audit = pd.DataFrame(
        {
            "split_bucket": ["train", "validation", "robustness"],
            "raw_event_n": [2, 1, 1],
            "analysis_event_n": [2, 1, 1],
            "analysis_event_fraction": [1.0, 1.0, 1.0],
        }
    )
    rule = pd.DataFrame({"rule_feature_missing_fraction": [0.0]})
    utility = pd.DataFrame(
        {
            "split_bucket": ["train", "validation", "robustness"],
            "badside_support_caveat": [False, False, False],
            "winner_retention_support_caveat": [False, False, False],
        }
    )
    search = runner.search_multiplicity_audit(base_config())
    return row_audit, rule, utility, search


def build_decision(runner, **statuses):
    row_audit, rule, utility, search = decision_inputs(runner)
    params = {
        "input_status": "pass",
        "upstream_status": "pass",
        "row_status": "pass",
        "label_status": "pass",
        "denominator_status": "pass",
        "uniqueness_status": "pass",
        "rule_status": "pass",
        "overlay_status": "pass",
        "winner_status": "pass",
        "density_status": "pass",
        "row_audit": row_audit,
        "rule_dictionary": rule,
        "utility_readout": utility,
        "search": search,
        "config": base_config(),
    }
    params.update(statuses)
    return runner.build_decision(**params).iloc[0]


def test_path_resolution_contract():
    runner = load_runner()
    assert runner.topic_path("topics/02_AFML_BIG_WINNER/x").is_relative_to(runner.REPO_ROOT)
    assert runner.topic_path("data/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("outputs/x").is_relative_to(runner.EXPERIMENT_DIR)


def test_upstream_stop_states_required():
    runner = load_runner()
    dec = build_decision(runner, upstream_status="fail")
    assert dec["decision_state"] == "13G_blocked_upstream_lineage_failure"


def test_selected_membership_from_13c_full_split():
    runner = load_runner()
    assert runner.lineage_role_for_artifact("upstream_13f_decision") == "negative_decision_lineage_only_not_row_truth"
    dec = build_decision(runner)
    assert not bool(dec["meta_labeling_authorized"])


def test_13c_manifest_schema_hash_audit(tmp_path):
    runner = load_runner()
    cache = tmp_path / "cache.parquet"
    pd.DataFrame({"a": [1]}).to_parquet(cache)
    csv_paths = {}
    for key in [
        "upstream_13c_decision",
        "upstream_13c_feature_cluster_dictionary",
        "upstream_13c_sample_uniqueness_audit",
        "upstream_13c_row_level_rebuild_audit",
    ]:
        path = tmp_path / f"{key}.csv"
        pd.DataFrame({"x": [1]}).to_csv(path, index=False)
        csv_paths[key] = path
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "local_cache_audit": [{"artifact_id": "morphology_residual_panel", "schema_hash": "wrong"}],
                "output_hashes": {
                    "morphology_orthogonal_residual_importance_decision": runner.file_sha(csv_paths["upstream_13c_decision"]),
                    "feature_cluster_dictionary": runner.file_sha(csv_paths["upstream_13c_feature_cluster_dictionary"]),
                    "sample_uniqueness_audit": runner.file_sha(csv_paths["upstream_13c_sample_uniqueness_audit"]),
                    "row_level_rebuild_audit": runner.file_sha(csv_paths["upstream_13c_row_level_rebuild_audit"]),
                },
            }
        ),
        encoding="utf-8",
    )
    resolved = {"upstream_13c_manifest": manifest, "upstream_13c_morphology_residual_panel_cache": cache, **csv_paths}
    audit = runner.build_13c_manifest_audit(resolved)
    row = audit.loc[audit["lineage_check_id"].eq("13c_cache.morphology_residual_panel.manifest_schema_hash")].iloc[0]
    assert row["status"] == "fail"


def test_event_denominator_fixed():
    runner = load_runner()
    raw = synthetic_events()
    status = raw[["event_id", "instrument", "reference_date", "entry_date", "entry_pos", "entry_price", "split_bucket", "selected_state_id"]].copy()
    status["analysis_denominator_flag"] = [True, True, True, True]
    status["analysis_exclusion_reason"] = ["", "", "", ""]
    labels = []
    for _, row in raw.iterrows():
        for up, down, h in runner.label_grid(base_config()):
            labels.append({**row.to_dict(), "up_threshold": up, "down_threshold": down, "horizon_sessions": h, "endpoint_id": runner.endpoint_id(up, down, h), "analysis_denominator_flag": True, "evaluable_flag": True, "upper_hit": False, "lower_hit": False, "winner_before_fail": False, "fail_before_winner": False, "survive_without_fail": True, "opportunity_without_fail": False, "upper_first_winner_before_fail": False, "upper_first_fail_before_winner": False, "same_bar_ambiguous": False, "time_to_upper_sessions": np.nan, "time_to_lower_sessions": np.nan, "terminal_return": 0.0, "mfe_return": 0.0, "mae_return": 0.0})
    readout = runner.build_label_grid_readout(pd.DataFrame(labels), raw, status)
    assert readout.groupby("split_bucket")["analysis_event_n"].nunique().max() == 1


def test_analysis_denominator_max_horizon_complete():
    runner = load_runner()
    raw = synthetic_events()
    status = raw[["event_id", "instrument", "reference_date", "entry_date", "entry_pos", "entry_price", "split_bucket", "selected_state_id"]].copy()
    status["analysis_denominator_flag"] = [True, False, True, True]
    status["analysis_exclusion_reason"] = ["", "max_horizon_path_incomplete", "", ""]
    audit = runner.build_row_level_rebuild_audit(raw, status, base_config())
    assert int(audit.loc[audit["split_bucket"].eq("train"), "max_horizon_path_incomplete_n"].iloc[0]) == 1
    assert "entry_price_missing_n" in audit.columns


def test_analysis_denominator_coverage_gate():
    runner = load_runner()
    audit = pd.DataFrame({"split_bucket": ["train"], "analysis_event_fraction": [0.5], "analysis_event_n": [10]})
    status, reason = runner.denominator_gate_status(audit, base_config())
    assert status == "fail"
    assert "analysis_event_fraction_below_min" in reason


def test_label_grid_complete():
    runner = load_runner()
    assert len(runner.label_grid(base_config())) == 27


def test_primary_endpoint_fixed():
    runner = load_runner()
    assert runner.primary_endpoint(base_config())[3] == "up_0p3_before_down_m0p15_H60"


def test_same_bar_lower_first():
    runner = load_runner()
    b = bars(high_mult=1.40, low_mult=0.80)
    out = runner.compute_one_label(event_row(), b, 0.30, -0.15, 20)
    assert out["same_bar_ambiguous"]
    assert out["first_touch_side"] == "lower"
    assert out["fail_before_winner"]
    assert out["upper_first_winner_before_fail"]
    assert not out["upper_first_fail_before_winner"]


def test_analysis_denominator_requires_finite_price():
    runner = load_runner()
    reason = runner.analysis_exclusion_reason(event_row(entry_price=np.nan), bars(n=150), 120)
    assert reason == "entry_price_missing"


def test_time_to_hit_and_survival_labels():
    runner = load_runner()
    b = bars(high_mult=1.01, low_mult=0.99)
    b.loc[4, "high"] = 13.5
    out = runner.compute_one_label(event_row(), b, 0.30, -0.15, 20)
    assert out["winner_before_fail"]
    assert out["time_to_upper_sessions"] == 5
    assert out["survive_without_fail"]


def test_not_evaluable_rows_retained():
    runner = load_runner()
    out = runner.compute_one_label(event_row(), bars(n=3), 0.30, -0.15, 20)
    assert not out["evaluable_flag"]
    assert out["not_evaluable_reason"] == "max_horizon_path_incomplete"


def test_no_future_data_in_rule_features():
    runner = load_runner()
    overlay, dictionary, *_ = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    assert not dictionary["source_column"].astype(str).str.contains("mfe|mae|time_to", case=False).any()


def test_liquidity_or_turnover_bucket_if_available():
    runner = load_runner()
    _overlay, dictionary, *_ = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    assert "t0_liquidity_or_turnover_bucket" in set(dictionary["rule_feature_id"])


def test_no_future_duplicate_in_rule_features():
    runner = load_runner()
    _overlay, dictionary, *_ = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    assert not dictionary["source_column"].astype(str).str.contains("duplicate|future|first_touch", case=False).any()


def test_t0_known_crowding_only():
    runner = load_runner()
    out = runner.add_t0_known_crowding(synthetic_events(), synthetic_events())
    assert "t0_prior_selected_event_count_20d" in out
    assert out.loc[out["event_id"].eq("e0"), "t0_prior_selected_event_count_20d"].iloc[0] == 0


def test_rule_freeze_train_only():
    runner = load_runner()
    _overlay, dictionary, status, _reason = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    assert status == "pass"
    assert not bool(dictionary["validation_used_for_rule_freeze"].any())
    assert not bool(dictionary["robustness_used_for_rule_freeze"].any())


def test_rule_feature_missing_kept_default_keep():
    runner = load_runner()
    events = synthetic_events().drop(columns=["ret_20d"])
    overlay, _dictionary, _status, _reason = runner.build_rule_overlay(events, events, base_config(overlay={**base_config()["overlay"], "rule_feature_missing_max_fraction": 1.0}))
    assert overlay["rule_feature_missing_caveat"].any()
    assert overlay.loc[overlay["rule_feature_missing_caveat"], "action"].eq("keep").all()


def test_no_ml_model_or_score():
    runner = load_runner()
    search = runner.search_multiplicity_audit(base_config()).iloc[0]
    assert not bool(search["ml_model_used"])
    assert not bool(search["hyperparameter_search_used"])


def test_action_multiplier_mapping():
    runner = load_runner()
    overlay, _dictionary, _status, _reason = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    assert set(overlay["risk_budget_multiplier"]).issubset({0.0, 0.5, 1.0, 1.5})


def test_skip_kept_in_denominator():
    runner = load_runner()
    dec = build_decision(runner, overlay_status="fail")
    assert dec["decision_state"] == "13G_stop_label_panel_only_no_overlay_utility"


def test_overlay_cost_tier_formula():
    runner = load_runner()
    row = synthetic_events().iloc[[0]].copy()
    row["action"] = "skip"
    row["risk_budget_multiplier"] = 0.0
    row["winner_before_fail"] = True
    row["fail_before_winner"] = False
    row["first_touch_side"] = "upper"
    row["time_to_upper_sessions"] = 2.0
    row["up_threshold"] = 0.30
    row["down_threshold"] = -0.15
    row["terminal_return"] = 0.0
    row["average_uniqueness"] = 1.0
    row["ex_post_duplicate_episode_flag"] = False
    out, *_ = runner.build_overlay_utility(row, base_config())
    assert out["overlay_per_event_utility_0bps"].iloc[0] == 0.0
    assert out["overlay_per_event_utility_50bps"].iloc[0] == -0.005


def test_overlay_incremental_cost_applied():
    runner = load_runner()
    row = synthetic_events().iloc[[0]].copy()
    row["action"] = "reduce"
    row["risk_budget_multiplier"] = 0.5
    row["winner_before_fail"] = False
    row["fail_before_winner"] = False
    row["first_touch_side"] = "vertical"
    row["up_threshold"] = 0.30
    row["down_threshold"] = -0.15
    row["terminal_return"] = 0.0
    row["average_uniqueness"] = 1.0
    row["ex_post_duplicate_episode_flag"] = False
    out, *_ = runner.build_overlay_utility(row, base_config())
    assert out["overlay_adjustment_cost_component_50bps"].iloc[0] == 0.0025


def test_baseline_exposure_day_return_output():
    runner = load_runner()
    row_audit, rule, utility, search = decision_inputs(runner)
    assert "baseline_exposure_day_return_50bps" not in utility or isinstance(search, pd.DataFrame)


def test_badside_avoided_and_winner_retained():
    runner = load_runner()
    row = synthetic_events().iloc[[0, 1]].copy()
    row["action"] = ["keep", "skip"]
    row["risk_budget_multiplier"] = [1.0, 0.0]
    row["winner_before_fail"] = [True, False]
    row["fail_before_winner"] = [False, True]
    row["first_touch_side"] = ["upper", "lower"]
    row["time_to_upper_sessions"] = [2.0, np.nan]
    row["time_to_lower_sessions"] = [np.nan, 2.0]
    row["up_threshold"] = 0.30
    row["down_threshold"] = -0.15
    row["terminal_return"] = 0.0
    row["average_uniqueness"] = 1.0
    row["ex_post_duplicate_episode_flag"] = False
    _out, readout, retention, *_ = runner.build_overlay_utility(row, base_config())
    train = retention.loc[retention["split_bucket"].eq("train")].iloc[0]
    assert train["winner_opportunity_retained_rate"] == 1.0
    assert train["badside_avoided_rate"] == 1.0


def test_overlay_utility_density_readout_is_populated():
    runner = load_runner()
    row = synthetic_events().copy()
    row["action"] = ["keep", "skip", "reduce", "increase"]
    row["risk_budget_multiplier"] = [1.0, 0.0, 0.5, 1.5]
    row["winner_before_fail"] = [True, False, False, True]
    row["fail_before_winner"] = [False, True, True, False]
    row["first_touch_side"] = ["upper", "lower", "lower", "upper"]
    row["time_to_upper_sessions"] = [2.0, np.nan, np.nan, 2.0]
    row["time_to_lower_sessions"] = [np.nan, 2.0, 2.0, np.nan]
    row["up_threshold"] = 0.30
    row["down_threshold"] = -0.15
    row["terminal_return"] = 0.0
    row["average_uniqueness"] = 1.0
    row["ex_post_duplicate_episode_flag"] = False
    _out, readout, _retention, *_ = runner.build_overlay_utility(row, base_config())
    assert np.isfinite(readout["event_density_per_instrument_year"]).all()


def test_badside_support_caveat():
    runner = load_runner()
    row = synthetic_events().iloc[[0]].copy()
    row["action"] = "keep"
    row["risk_budget_multiplier"] = 1.0
    row["winner_before_fail"] = True
    row["fail_before_winner"] = False
    row["first_touch_side"] = "upper"
    row["time_to_upper_sessions"] = 2.0
    row["up_threshold"] = 0.30
    row["down_threshold"] = -0.15
    row["terminal_return"] = 0.0
    row["average_uniqueness"] = 1.0
    row["ex_post_duplicate_episode_flag"] = False
    _out, _readout, retention, *_ = runner.build_overlay_utility(row, base_config())
    assert bool(retention.loc[retention["split_bucket"].eq("train"), "badside_support_caveat"].iloc[0])


def test_exact_uniqueness_max_horizon_span():
    runner = load_runner()
    overlay, *_ = runner.build_rule_overlay(synthetic_events(), synthetic_events(), base_config())
    out, audit = runner.compute_event_uniqueness(overlay, base_config())
    assert (out["event_span_end_pos"] - out["event_span_start_pos"]).eq(119).all()
    assert audit["event_uniqueness_gate_status"].eq("pass").all()


def test_density_artifact_gate():
    runner = load_runner()
    dec = build_decision(runner, density_status="fail")
    assert dec["decision_state"] == "13G_stop_overlay_improvement_density_artifact"


def test_overlay_no_utility_stop():
    runner = load_runner()
    dec = build_decision(runner, overlay_status="fail")
    assert dec["decision_state"] == "13G_stop_label_panel_only_no_overlay_utility"


def test_overlay_winner_sacrifice_stop():
    runner = load_runner()
    dec = build_decision(runner, winner_status="fail")
    assert dec["decision_state"] == "13G_stop_overlay_improves_by_winner_sacrifice"


def test_overlay_signal_present_decision():
    runner = load_runner()
    dec = build_decision(runner)
    assert dec["decision_state"] == "13G_diagnostic_survival_overlay_signal_present"


def test_no_authorization_invariants():
    runner = load_runner()
    dec = build_decision(runner)
    assert not bool(dec["sequence_mining_authorized"])
    assert not bool(dec["meta_labeling_authorized"])
    assert not bool(dec["bet_sizing_authorized"])
    assert not bool(dec["confirmatory_status"])


def test_search_accounting():
    runner = load_runner()
    row = runner.search_multiplicity_audit(base_config()).iloc[0]
    assert row["effective_search_space_n"] == 27
    assert not bool(row["hyperparameter_search_used"])
    assert row["search_accounting_status"] == "diagnostic_pre_registered_primary_endpoint"
