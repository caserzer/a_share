from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_13e_nonlinear_winner_train_kfold_feasibility_diagnostic",
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
        "selected_label": {
            "label_id": "vol20d_kup2p0_kdn1p0_H20",
            "horizon_sessions": 5,
            "same_bar_priority": "lower_first",
        },
        "fold_protocol": {
            "fold_n": 3,
            "embargo_sessions": 0,
            "min_effective_train_event_n_per_fold": 1,
            "min_effective_test_event_n_per_fold": 1,
            "purge_group_unit": "instrument",
            "embargo_scope": "global_calendar_session",
        },
        "model": {
            "top_fraction": 0.3,
            "logistic_l2": {"C": 0.5, "penalty": "l2", "solver": "liblinear", "max_iter": 100},
            "sklearn_hgb_low_capacity": {
                "loss": "log_loss",
                "max_iter": 5,
                "learning_rate": 0.1,
                "max_leaf_nodes": 7,
                "max_depth": 3,
                "min_samples_leaf": 2,
                "l2_regularization": 0.0,
                "random_state": 7,
                "early_stopping": False,
            },
        },
        "thresholds": {"min_train_event_n": 1, "auc_improvement_min": 0.005},
        "feature_clusters": {
            "cluster_drawdown_morphology": [
                "max_drawdown_20d",
                "ret_20d",
                "ret_60d",
                "rebound_from_20d_low",
            ],
            "cluster_denominator_controls": [
                "board_bucket",
                "calendar_year",
                "liquidity_bucket",
                "volatility_bucket",
            ],
            "cluster_compression": ["volatility_20d", "volatility_60d", "range_width_20d"],
            "cluster_position_strength": [
                "distance_from_20d_low",
                "close_vs_sma20",
                "close_position_20d",
            ],
            "cluster_participation": [
                "turnover_zscore_20d",
                "amount_ratio_5d_20d",
                "volume_up_price_not_down_5d",
            ],
        },
    }
    cfg.update(overrides)
    return cfg


def synthetic_panel(n=30, include_oos=False):
    rows = []
    for i in range(n):
        winner = i % 3 == 0
        reference_date = pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)
        entry_date = reference_date + pd.Timedelta(days=1)
        rows.append(
            {
                "row_id": i,
                "instrument": f"inst_{i:03d}",
                "reference_date": reference_date.strftime("%Y-%m-%d"),
                "split_bucket": "train",
                "split": "train",
                "native_scope": True,
                "s": i % 2 == 0,
                "board_bucket": "main",
                "calendar_year": 2020,
                "calendar_month": 1,
                "market_regime_bucket": "r",
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "entry_price": 10.0,
                "entry_pos": float(i * 10),
                "winner_positive": winner,
                "upper_first": winner,
                "lower_first": not winner,
                "fast_fail": False,
                "neutral": False,
                "censored": False,
                "same_bar_conflict": False,
                "horizon_complete": True,
                "upper_barrier": 0.02,
                "lower_barrier": -0.01,
                "time_to_upper": 1.0 if winner else np.nan,
                "time_to_lower": np.nan if winner else 1.0,
                "horizon_sessions": 5,
                "row_utility_component_0bps": 0.02 if winner else -0.01,
                "row_utility_component_50bps": 0.015 if winner else -0.015,
                "row_utility_component_100bps": 0.010 if winner else -0.020,
                "utility_positive_50bps": winner,
                "label_id": "vol20d_kup2p0_kdn1p0_H20",
                "max_drawdown_20d": float(i),
                "ret_20d": float(i % 5),
                "ret_60d": float(i % 7),
                "rebound_from_20d_low": float(i % 4),
                "liquidity_bucket": "l",
                "volatility_bucket": "v",
                "volatility_20d": float(i % 6),
                "volatility_60d": float(i % 8),
                "range_width_20d": float(i % 9),
                "distance_from_20d_low": float(i % 10),
                "close_vs_sma20": float(i % 11),
                "close_position_20d": float(i % 12),
                "turnover_zscore_20d": float(i % 13),
                "amount_ratio_5d_20d": float(i % 14),
                "volume_up_price_not_down_5d": float(i % 15),
            }
        )
    if include_oos:
        rows.append({**rows[0], "row_id": 999, "split_bucket": "validation", "split": "validation"})
    return pd.DataFrame(rows)


def positive_search(runner):
    return runner.build_search_audit(base_config())


def test_path_resolution_contract():
    runner = load_runner()
    assert runner.topic_path("topics/02_AFML_BIG_WINNER/x").is_relative_to(runner.REPO_ROOT)
    assert runner.topic_path("data/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("experiments/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("outputs/x").is_relative_to(runner.EXPERIMENT_DIR)


def test_upstream_13c_stop_decision_required():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "fail_already_authorized",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_blocked_upstream_13c_already_authorized"


def test_train_only_no_oos_access():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(include_oos=True), base_config())
    assert set(events["split_bucket"].astype(str)) == {"train"}
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert not bool(decision["validation_used_in_13e"])
    assert not bool(decision["robustness_used_in_13e"])


def test_no_report_text_reconstruction():
    runner = load_runner()
    assert runner.lineage_role_for_artifact("upstream_report_13c") == "lineage_report_only_not_row_truth"


def test_selected_state_membership_reproduction():
    runner = load_runner()
    panel = synthetic_panel()
    events = runner.prepare_train_event_panel(panel, base_config())
    assert events["s"].astype(bool).all()
    assert len(events) == int(panel["s"].sum())


def test_frozen_buckets_not_refit():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(), base_config())
    audit, status, _reason = runner.build_row_level_rebuild_audit(events, base_config())
    assert status == "pass"
    assert not bool(audit.iloc[0]["bucket_refit_in_13e"])


def test_purged_kfold_removes_overlap():
    runner = load_runner()
    cfg = base_config(fold_protocol={**base_config()["fold_protocol"], "embargo_sessions": 0})
    events = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "instrument": ["a", "a", "b"],
            "entry_pos": [10.0, 11.0, 100.0],
            "event_start_pos": [10.0, 11.0, 100.0],
            "event_end_pos": [12.0, 13.0, 101.0],
            "reference_date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "entry_date": ["2020-01-02", "2020-01-03", "2020-01-04"],
            "fold_id": [0, 1, 1],
        }
    )
    train, _test, purged_n, _embargoed_n = runner.purged_train_for_fold(events, 0, cfg)
    assert purged_n == 1
    assert 2 not in set(train["row_id"])
    assert 3 in set(train["row_id"])


def test_embargo_applied():
    runner = load_runner()
    cfg = base_config(fold_protocol={**base_config()["fold_protocol"], "embargo_sessions": 5})
    events = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "instrument": ["a", "b", "c"],
            "entry_pos": [10.0, 10000.0, 12.0],
            "event_start_pos": [10.0, 10000.0, 12.0],
            "event_end_pos": [10.0, 10000.0, 12.0],
            "reference_date": ["2020-01-09", "2020-01-13", "2020-02-28"],
            "entry_date": ["2020-01-10", "2020-01-14", "2020-03-01"],
            "fold_id": [0, 1, 1],
        }
    )
    train, _test, _purged_n, embargoed_n = runner.purged_train_for_fold(events, 0, cfg)
    assert embargoed_n == 1
    assert 2 not in set(train["row_id"])
    assert 3 in set(train["row_id"])


def test_chronological_folds_do_not_split_reference_dates():
    runner = load_runner()
    events = pd.DataFrame(
        {
            "row_id": list(range(12)),
            "reference_date": ["2020-01-01"] * 4 + ["2020-01-02"] * 4 + ["2020-01-03"] * 4,
        }
    )
    folded = runner.assign_chronological_folds(events, 2)
    assert folded.groupby("reference_date")["fold_id"].nunique().max() == 1


def test_fold_local_uniqueness_sample_weight_applied():
    runner = load_runner()
    cfg = base_config()
    events = runner.prepare_train_event_panel(synthetic_panel(60), cfg)
    metrics, uniqueness = runner.build_train_kfold_outputs(events, cfg)
    assert metrics["sample_weight_source"].eq("fold_local_exact_event_span_average_uniqueness").all()
    assert uniqueness["sample_uniqueness_gate_status"].eq("pass_with_exact_t1").all()


def test_integrity_failure_blocks_model_metrics():
    runner = load_runner()
    cfg = base_config(
        fold_protocol={
            **base_config()["fold_protocol"],
            "min_effective_train_event_n_per_fold": 1000,
        }
    )
    events = runner.prepare_train_event_panel(synthetic_panel(60), cfg)
    metrics, uniqueness = runner.build_train_kfold_outputs(events, cfg)
    assert metrics.empty
    assert "purged_cv_integrity_caveat" in set(uniqueness["sample_uniqueness_gate_status"])


def test_sklearn_hgb_required_no_logistic_fallback(monkeypatch):
    runner = load_runner()
    monkeypatch.setattr(runner, "HistGradientBoostingClassifier", None)
    assert runner.nonlinear_model_availability_gate_status() == "fail"
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "fail",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_blocked_nonlinear_model_unavailable"


def test_no_hyperparameter_search():
    runner = load_runner()
    search = runner.build_search_audit(base_config()).iloc[0]
    assert not bool(search["hyperparameter_search_used"])
    assert not bool(search["fold_internal_tuning_used"])
    assert not bool(search["early_stopping_used"])


def test_auc_only_improvement_cannot_emit_positive_readout():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "probability_only_no_utility",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_stop_nonlinear_auc_improvement_no_utility"
    assert not bool(decision["meta_labeling_authorized"])


def test_utility_gate_requires_mean_minus_std_positive():
    runner = load_runner()
    comparison = pd.DataFrame(
        {
            "feature_set": ["augmented_feature_set"],
            "metric_id": ["utility_proxy_50bps"],
            "sklearn_hgb_fold_mean": [0.01],
            "sklearn_hgb_fold_std": [0.02],
            "nonlinear_minus_linear_delta": [0.01],
        }
    )
    assert runner.nonlinear_utility_gate_status(comparison, "pass", "pass") == "probability_only_no_utility"


def test_no_nonlinear_improvement_stop():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "fail",
        "fail",
        "fail",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_stop_no_nonlinear_auc_improvement"
    assert decision["train_kfold_capacity_readout"] == "nonlinear_capacity_signal_absent"


def test_no_uplift_improvement_stop():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "fail",
        "fail",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_stop_no_nonlinear_uplift_improvement"


def test_effective_fold_support_blocks_positive():
    runner = load_runner()
    uniqueness = pd.DataFrame({"sample_uniqueness_gate_status": ["purged_cv_integrity_caveat"]})
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        runner.purged_cv_integrity_gate_status(uniqueness),
        "pass",
        "pass",
        "pass",
        runner.sample_uniqueness_gate_status(uniqueness),
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_blocked_purged_cv_integrity_failure"


def test_decision_precedence():
    runner = load_runner()
    decision = runner.build_decision(
        "fail",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_blocked_input_or_lineage_failure"


def test_no_bet_sizing_authorization():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert not bool(decision["bet_sizing_authorized"])


def test_no_sequence_mining_authorization():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert not bool(decision["sequence_mining_authorized"])


def test_no_state_or_feature_swap():
    runner = load_runner()
    comparison = pd.DataFrame(
        {
            "feature_set": ["baseline_feature_set", "augmented_feature_set"],
            "metric_id": ["auc", "auc"],
            "nonlinear_minus_linear_delta": [0.1, 0.0],
        }
    )
    fold_metrics = pd.DataFrame(
        {
            "feature_set": ["augmented_feature_set"] * 3,
            "model_family": ["logistic_l2"] * 3,
            "fold_id": [0, 1, 2],
            "auc": [0.5, 0.5, 0.5],
        }
    )
    assert runner.nonlinear_auc_gate_status(comparison, fold_metrics, base_config()) == "fail"


def test_diagnostic_positive_readout():
    runner = load_runner()
    decision = runner.build_decision(
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass_with_exact_t1",
        positive_search(runner),
        base_config(),
    ).iloc[0]
    assert decision["decision_state"] == "13E_diagnostic_nonlinear_train_utility_signal_present"
    assert decision["next_allowed_requirement"] == "none"
    assert not bool(decision["meta_labeling_authorized"])


def test_search_accounting_non_confirmatory():
    runner = load_runner()
    search = runner.build_search_audit(base_config()).iloc[0]
    assert search["search_accounting_status"] == "diagnostic_train_only_not_confirmatory"
    assert not bool(search["confirmatory_status"])
