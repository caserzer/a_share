from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13f_early_path_confirmation_delayed_entry_train_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_13f_early_path_confirmation_delayed_entry_train_diagnostic",
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
        "early_path": {
            "k_grid": [2, 3],
            "primary_k": 3,
            "horizon_modes": ["horizon_mode_from_entry", "horizon_mode_calendar_t0"],
            "primary_horizon_mode": "horizon_mode_from_entry",
            "primary_arm": "arm_model_delayed",
            "delayed_entry_not_executable_max_fraction": 0.5,
            "min_early_path_evaluable_fraction": 0.8,
            "max_forward_shift_sessions": 2,
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
            "top_fraction": 0.5,
            "include_t0_context_features": False,
            "logistic_l2": {"C": 0.5, "penalty": "l2", "solver": "liblinear", "max_iter": 100},
        },
        "thresholds": {
            "min_train_event_n": 1,
            "cost_buffer_grid": [0.0, 0.005, 0.01],
            "reference_cost_buffer_return": 0.01,
        },
        "feature_clusters": {
            "cluster_drawdown_morphology": ["max_drawdown_20d", "ret_20d", "ret_60d", "rebound_from_20d_low"],
            "cluster_denominator_controls": ["board_bucket", "calendar_year", "liquidity_bucket", "volatility_bucket"],
            "cluster_compression": ["volatility_20d", "volatility_60d", "range_width_20d"],
            "cluster_position_strength": ["distance_from_20d_low", "close_vs_sma20", "close_position_20d"],
            "cluster_participation": ["turnover_zscore_20d", "amount_ratio_5d_20d", "volume_up_price_not_down_5d"],
        },
    }
    cfg.update(overrides)
    return cfg


def synthetic_bars(n=300, open_value=10.0):
    rows = []
    for i in range(n):
        px = open_value + 0.01 * i
        rows.append(
            {
                "date": (pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": px,
                "high": px * 1.005,
                "low": px * 0.995,
                "close": px * (1.001 if i % 2 == 0 else 0.999),
                "volume": 1000 + i,
                "money": 10000 + i,
                "turnover_rate": 0.01,
            }
        )
    return pd.DataFrame(rows)


def synthetic_panel(n=30, include_oos=False):
    rows = []
    for i in range(n):
        winner = i % 3 == 0
        entry_pos = i * 20 + 5
        rows.append(
            {
                "row_id": i,
                "instrument": "I",
                "reference_date": (pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                "entry_date": (pd.Timestamp("2020-01-02") + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                "reference_pos": float(entry_pos - 1),
                "entry_pos": float(entry_pos),
                "entry_price": 10.0 + entry_pos * 0.01,
                "split_bucket": "train",
                "split": "train",
                "native_scope": True,
                "s": True,
                "winner_positive": winner,
                "upper_first": winner,
                "lower_first": not winner,
                "fast_fail": not winner,
                "horizon_complete": True,
                "same_bar_conflict": False,
                "upper_barrier": 0.02,
                "lower_barrier": -0.01,
                "time_to_upper": 2.0 if winner else np.nan,
                "time_to_lower": np.nan if winner else 2.0,
                "horizon_sessions": 5,
                "label_id": "vol20d_kup2p0_kdn1p0_H20",
                "row_utility_component_0bps": 0.02 if winner else -0.01,
                "row_utility_component_50bps": 0.015 if winner else -0.015,
                "row_utility_component_100bps": 0.010 if winner else -0.020,
                "board_bucket": "main",
                "calendar_year": 2020,
                "calendar_month": 1,
                "market_regime_bucket": "r",
                "max_drawdown_20d": float(i),
                "ret_20d": float(i % 5),
                "ret_60d": float(i % 7),
                "rebound_from_20d_low": float(i % 4),
                "liquidity_bucket": "l",
                "volatility_bucket": "v",
                "volatility_20d": 0.01,
                "volatility_60d": 0.02,
                "range_width_20d": 0.03,
                "distance_from_20d_low": 0.04,
                "close_vs_sma20": 0.05,
                "close_position_20d": 0.06,
                "turnover_zscore_20d": 0.07,
                "amount_ratio_5d_20d": 0.08,
                "volume_up_price_not_down_5d": 0.09,
            }
        )
    if include_oos:
        rows.append({**rows[0], "row_id": 999, "split_bucket": "validation", "split": "validation"})
    return pd.DataFrame(rows)


def positive_search(runner):
    return runner.build_search_audit(base_config())


def primary_comparison(model_mean=0.02, model_std=0.005, model_delta=0.02, model_gate_delta=0.01, gate_mean=0.01):
    return pd.DataFrame(
        [
            {
                "early_path_k": 3,
                "horizon_mode": "horizon_mode_from_entry",
                "arm": "arm_gate_delayed",
                "fold_mean_utility_per_event_mean_50bps": gate_mean,
                "fold_std_utility_per_event_mean_50bps": 0.002,
                "delta_utility_per_event_mean_50bps_vs_t0": gate_mean,
                "delta_utility_per_event_mean_50bps_vs_gate": 0.0,
                "delta_sign_consistency_folds": 3,
            },
            {
                "early_path_k": 3,
                "horizon_mode": "horizon_mode_from_entry",
                "arm": "arm_model_delayed",
                "fold_mean_utility_per_event_mean_50bps": model_mean,
                "fold_std_utility_per_event_mean_50bps": model_std,
                "delta_utility_per_event_mean_50bps_vs_t0": model_delta,
                "delta_utility_per_event_mean_50bps_vs_gate": model_gate_delta,
                "delta_sign_consistency_folds": 3,
            },
        ]
    )


def empty_missed():
    return pd.DataFrame(
        columns=[
            "early_path_k",
            "horizon_mode",
            "arm",
            "selected_entry_only_delta_utility_50bps_vs_t0",
            "same_event_delta_utility_50bps_vs_t0",
        ]
    )


def decision(runner, comparison=None, missed=None, **overrides):
    params = {
        "input_status": "pass",
        "upstream_status": "pass",
        "label_status": "pass",
        "row_status": "pass",
        "early_path_status": "pass",
        "executable_status": "pass",
        "purged_status": "pass",
        "uniqueness_status": "pass_with_exact_t1",
        "comparison": comparison if comparison is not None else primary_comparison(),
        "missed": missed if missed is not None else empty_missed(),
        "search": positive_search(runner),
        "config": base_config(),
        "primary_failure_reason": "",
    }
    params.update(overrides)
    return runner.build_decision(**params).iloc[0]


def test_path_resolution_contract():
    runner = load_runner()
    assert runner.topic_path("topics/02_AFML_BIG_WINNER/x").is_relative_to(runner.REPO_ROOT)
    assert runner.topic_path("data/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("experiments/x").is_relative_to(runner.TOPIC_ROOT)
    assert runner.topic_path("outputs/x").is_relative_to(runner.EXPERIMENT_DIR)


def test_upstream_13c_13e_stop_required():
    runner = load_runner()
    dec = decision(runner, upstream_status="fail")
    assert dec["decision_state"] == "13F_blocked_upstream_lineage_failure"


def test_train_only_no_oos_access():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(include_oos=True), base_config())
    assert set(events["split_bucket"].astype(str)) == {"train"}
    dec = decision(runner)
    assert not bool(dec["validation_used_in_13f"])
    assert not bool(dec["robustness_used_in_13f"])


def test_early_path_no_lookahead():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(3), base_config())
    events, path = runner.reconstruct_event_paths(events, base_config(), Path("."), {"I": synthetic_bars(200)})
    row = path.loc[path["early_path_k"].eq(3)].iloc[0]
    assert row["early_path_window_end_pos"] == row["entry_pos"] + 2
    audit, status, _ = runner.build_early_path_rebuild_audit(path, base_config())
    assert status == "pass"
    assert int(audit["lookahead_column_count"].max()) == 0


def test_early_path_label_window_disjoint():
    runner = load_runner()
    path = pd.DataFrame(
        {
            "early_path_k": [3],
            "row_id": [1],
            "early_path_evaluable": [True],
            "early_path_window_start_pos": [10],
            "early_path_window_end_pos": [12],
            "delayed_entry_target_pos": [13],
            "entry_pos": [10],
            "label_window_disjoint": [False],
        }
    )
    _audit, status, _ = runner.build_early_path_rebuild_audit(path, base_config())
    assert status == "fail"


def test_barrier_uses_t0_volatility():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(1), base_config())
    events.loc[events.index[0], "upper_barrier"] = 0.20
    bars = synthetic_bars(80)
    bars.loc[int(events.iloc[0]["entry_pos"]) + 3, "high"] = bars.loc[int(events.iloc[0]["entry_pos"]) + 3, "open"] * 1.05
    _events, path = runner.reconstruct_event_paths(events, base_config(), Path("."), {"I": bars})
    assert not bool(path.loc[path["early_path_k"].eq(3), "delayed_upper_first"].iloc[0])
    audit, _status, _ = runner.build_early_path_rebuild_audit(path, base_config())
    assert set(audit["barrier_uses_t0_volatility_status"]) == {"pass"}


def test_delayed_entry_executability():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(1), base_config())
    bars = synthetic_bars(80)
    target = int(events.iloc[0]["entry_pos"]) + 3
    pit_dates = {"I": {str(bars.loc[target + 1, "date"])[:10]}}
    _events, path = runner.reconstruct_event_paths(
        events,
        base_config(),
        Path("."),
        {"I": bars},
        executable_dates_by_instrument=pit_dates,
    )
    row = path.loc[(path["early_path_k"].eq(3)) & (path["horizon_mode"].eq("horizon_mode_from_entry"))].iloc[0]
    assert bool(row["delayed_entry_executable"])
    assert row["delayed_entry_forward_shift"] == 1


def test_missed_winner_accounting():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(1), base_config())
    bars = synthetic_bars(80)
    entry = int(events.iloc[0]["entry_pos"])
    bars.loc[entry : entry + 2, "high"] = float(events.iloc[0]["entry_price"]) * 1.05
    _events, path = runner.reconstruct_event_paths(events, base_config(), Path("."), {"I": bars})
    sub = path.loc[path["early_path_k"].eq(3)]
    assert bool(sub["early_path_touched_upper_barrier_flag"].any())
    metrics = runner.arm_metrics(sub.head(1), "arm_gate_delayed", pd.Series(False, index=sub.head(1).index))
    assert metrics["missed_upper_in_window_n"] == 1
    assert metrics["utility_per_event_mean_50bps"] == 0.0


def test_utility_same_event_basis():
    runner = load_runner()
    path = pd.DataFrame(
        {
            "delayed_row_utility_component_0bps": [0.1, 0.1],
            "delayed_row_utility_component_50bps": [0.1, 0.1],
            "delayed_row_utility_component_100bps": [0.1, 0.1],
            "delayed_winner_positive": [True, True],
            "delayed_fast_fail": [False, False],
            "early_path_touched_upper_barrier_flag": [False, False],
            "early_path_touched_lower_barrier_flag": [False, False],
            "row_utility_component_50bps": [0.0, 0.0],
        }
    )
    selected = pd.Series([True, False], index=path.index)
    metrics = runner.arm_metrics(path, "arm_gate_delayed", selected)
    assert metrics["utility_per_event_mean_50bps"] == 0.05
    assert metrics["utility_per_selected_entry_mean_50bps"] == 0.1


def test_same_event_same_fold():
    runner = load_runner()
    events = runner.prepare_train_event_panel(synthetic_panel(12), base_config())
    folded = runner.r13e.assign_chronological_folds(events, 3)
    assert folded.groupby("row_id")["fold_id"].nunique().max() == 1


def test_purged_embargo_and_min_support():
    runner = load_runner()
    cfg = base_config(fold_protocol={**base_config()["fold_protocol"], "embargo_sessions": 0})
    events = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "instrument": ["a", "a", "b"],
            "entry_pos": [10.0, 40.0, 100.0],
            "event_start_pos": [10.0, 40.0, 100.0],
            "event_end_pos": [50.0, 45.0, 101.0],
            "reference_date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "entry_date": ["2020-01-02", "2020-01-03", "2020-01-04"],
            "fold_id": [0, 1, 1],
        }
    )
    train, _test, purged_n, _embargoed_n = runner.r13e.purged_train_for_fold(events, 0, cfg)
    assert purged_n == 1
    assert 2 not in set(train["row_id"])


def test_no_hyperparameter_search():
    runner = load_runner()
    search = runner.build_search_audit(base_config()).iloc[0]
    assert not bool(search["hyperparameter_search_used"])
    assert not bool(search["oos_used_for_selection"])


def test_primary_comparison_fixed():
    runner = load_runner()
    nonprimary = primary_comparison(model_mean=-0.01, model_delta=-0.01, model_gate_delta=-0.01, gate_mean=-0.01)
    extra = pd.DataFrame(
        [
            {
                "early_path_k": 2,
                "horizon_mode": "horizon_mode_from_entry",
                "arm": "arm_model_delayed",
                "fold_mean_utility_per_event_mean_50bps": 1.0,
                "fold_std_utility_per_event_mean_50bps": 0.0,
                "delta_utility_per_event_mean_50bps_vs_t0": 1.0,
                "delta_utility_per_event_mean_50bps_vs_gate": 1.0,
                "delta_sign_consistency_folds": 5,
            }
        ]
    )
    dec = decision(runner, comparison=pd.concat([nonprimary, extra], ignore_index=True))
    assert dec["decision_state"] == "13F_stop_no_delayed_utility_improvement"


def test_no_delayed_improvement_stop():
    runner = load_runner()
    comp = primary_comparison(model_mean=-0.01, model_delta=-0.01, model_gate_delta=-0.01, gate_mean=-0.01)
    dec = decision(runner, comparison=comp)
    assert dec["decision_state"] == "13F_stop_no_delayed_utility_improvement"
    assert dec["delayed_entry_capacity_readout"] == "delayed_entry_no_utility_signal"


def test_missed_winner_offset_stop():
    runner = load_runner()
    missed = pd.DataFrame(
        [
            {
                "early_path_k": 3,
                "horizon_mode": "horizon_mode_from_entry",
                "arm": "arm_model_delayed",
                "selected_entry_only_delta_utility_50bps_vs_t0": 0.1,
                "same_event_delta_utility_50bps_vs_t0": -0.1,
            }
        ]
    )
    dec = decision(runner, missed=missed)
    assert dec["decision_state"] == "13F_stop_delayed_improvement_offset_by_missed_winners"


def test_gate_effect_only_readout():
    runner = load_runner()
    comp = primary_comparison(model_mean=0.005, model_std=0.01, model_delta=0.005, model_gate_delta=-0.005, gate_mean=0.02)
    dec = decision(runner, comparison=comp)
    assert dec["decision_state"] == "13F_diagnostic_delayed_gate_effect_only"
    assert dec["delayed_entry_capacity_readout"] == "delayed_entry_gate_effect_only"


def test_utility_gate_requires_mean_minus_std_positive():
    runner = load_runner()
    comp = primary_comparison(model_mean=0.01, model_std=0.02, model_delta=0.01, model_gate_delta=0.01)
    assert not runner.utility_gate_pass(comp, "arm_model_delayed", base_config())


def test_decision_precedence():
    runner = load_runner()
    dec = decision(runner, input_status="fail")
    assert dec["decision_state"] == "13F_blocked_input_or_lineage_failure"
    comp = primary_comparison(model_mean=-0.01, model_delta=-0.01, model_gate_delta=-0.01, gate_mean=-0.01)
    missed = pd.DataFrame(
        [
            {
                "early_path_k": 3,
                "horizon_mode": "horizon_mode_from_entry",
                "arm": "arm_model_delayed",
                "selected_entry_only_delta_utility_50bps_vs_t0": 0.1,
                "same_event_delta_utility_50bps_vs_t0": -0.1,
            }
        ]
    )
    dec = decision(runner, comparison=comp, missed=missed)
    assert dec["decision_state"] == "13F_stop_no_delayed_utility_improvement"


def test_no_authorization_invariants():
    runner = load_runner()
    dec = decision(runner)
    assert dec["next_allowed_requirement"] == "none"
    assert not bool(dec["sequence_mining_authorized"])
    assert not bool(dec["meta_labeling_authorized"])
    assert not bool(dec["bet_sizing_authorized"])


def test_sensitivity_cannot_override_primary():
    runner = load_runner()
    search = runner.build_search_audit(base_config()).iloc[0]
    assert search["primary_k"] == 3
    assert search["effective_search_space_n"] == 12


def test_diagnostic_positive_readout():
    runner = load_runner()
    dec = decision(runner)
    assert dec["decision_state"] == "13F_diagnostic_delayed_entry_utility_signal_present"
    assert dec["delayed_entry_capacity_readout"] == "delayed_entry_model_utility_signal_present"
    assert dec["next_allowed_requirement"] == "none"


def test_search_accounting_non_confirmatory():
    runner = load_runner()
    search = runner.build_search_audit(base_config()).iloc[0]
    assert search["search_accounting_status"] == "diagnostic_train_only_not_confirmatory"
    assert not bool(search["confirmatory_status"])
