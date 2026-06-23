from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_13a_full_pit_native_token_cartography_preflight", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_selected_label_uses_horizon_scaled_vol_and_lower_first(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "open": [10.0, 10.0, 10.0],
            "high": [10.30, 10.00, 10.00],
            "low": [9.80, 10.00, 10.00],
            "close": [10.0, 10.0, 10.0],
            "money": [1.0, 1.0, 1.0],
            "turnover_rate": [0.1, 0.1, 0.1],
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    cache = runner.StockDailyCache(qfq_dir)
    frame = pd.DataFrame(
        {
            "instrument": ["S1"],
            "entry_pos": [0],
            "entry_price": [10.0],
            "volatility_20d": [0.01],
        }
    )

    label = runner.compute_label(
        frame,
        cache,
        k_up=2.0,
        k_dn=1.0,
        horizon_sessions=2,
        vol_reference_unit="daily_return_std",
    )

    assert math.isclose(label.iloc[0]["upper_barrier"], 2.0 * 0.01 * math.sqrt(2), rel_tol=1e-12)
    assert bool(label.iloc[0]["same_bar_conflict"])
    assert bool(label.iloc[0]["lower_first"])
    assert not bool(label.iloc[0]["winner_positive"])


def test_duplicate_qfq_dates_are_auditable_not_silent(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-01"],
            "open": [10.0, 10.0],
            "high": [10.0, 10.0],
            "low": [10.0, 10.0],
            "close": [10.0, 10.0],
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)

    daily = runner.StockDailyCache(qfq_dir).get("S1")

    assert daily.status == "duplicate_qfq_date"
    assert daily.duplicate_date_n == 1


def test_missing_upstream_cache_rebuilds_from_raw_pit_and_qfq(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    dates = pd.bdate_range("2020-01-01", periods=90).strftime("%Y-%m-%d").tolist()
    close = [10.0 + i * 0.03 + (0.04 if i % 2 else -0.04) for i in range(90)]
    pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": [x + 0.15 for x in close],
            "low": [x - 0.15 for x in close],
            "close": close,
            "volume": [1000.0] * 90,
            "money": [100000.0] * 90,
            "turnover_rate": [0.01] * 90,
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    ref_date = dates[65]
    pit_path = tmp_path / "pit.csv"
    pd.DataFrame(
        {
            "usable_trade_date": [ref_date],
            "instrument": ["S1"],
            "board_bucket": ["main_board"],
            "is_listed": [True],
            "is_st": [False],
            "is_suspended": [False],
        }
    ).to_csv(pit_path, index=False)
    regime_path = tmp_path / "regime.csv"
    pd.DataFrame(
        {
            "date": [ref_date],
            "daily_regime_bucket": ["risk_on"],
            "daily_regime_conflict_n": [0],
            "daily_regime_conflict_flag": [False],
        }
    ).to_csv(regime_path, index=False)
    table_dir = tmp_path / "tables"
    table_dir.mkdir()
    pd.DataFrame(
        {
            "split": ["train", "validation", "robustness"],
            "start_date": ["2020-01-01", "2021-01-01", "2022-01-01"],
            "end_date": ["2020-12-31", "2021-12-31", "2022-12-31"],
            "boundary_assignment_status": ["pass", "pass", "pass"],
        }
    ).to_csv(table_dir / "full_universe_split_boundary_audit.csv", index=False)
    pd.DataFrame(
        {
            "label_id": [runner.SELECTED_LABEL_ID],
            "vol_reference_unit": ["daily_return_std"],
            "k_up": [2.0],
            "k_dn": [1.0],
            "horizon_sessions": [20],
            "formula_status": ["pass"],
        }
    ).to_csv(table_dir / "label_formula_audit.csv", index=False)
    upstream_config = tmp_path / "config_12a7g.yaml"
    upstream_config.write_text("supported_boards:\n  - main_board\n", encoding="utf-8")
    resolved = {
        "pit_topn_400_100_executable_daily": pit_path,
        "stock_daily_qfq_dir": qfq_dir,
        "global_regime_calendar": regime_path,
        "upstream_12a7g_table_dir": table_dir,
        "upstream_config_12a7g": upstream_config,
        "upstream_full_pit_label_panel_cache": tmp_path / "missing_cache.parquet",
        "upstream_12a7g_manifest": tmp_path / "missing_manifest.json",
    }

    panel, cache_used, status = runner.load_base_panel(resolved)
    input_audit = runner.build_input_audit({"upstream_full_pit_label_panel_cache": resolved["upstream_full_pit_label_panel_cache"]})

    assert not cache_used
    assert status.startswith("raw_rebuild_after_cache_unusable")
    assert not bool(input_audit.iloc[0]["required_flag"])
    assert len(panel) == 1
    assert panel.iloc[0]["split"] == "train"
    assert panel.iloc[0]["label_id"] == runner.SELECTED_LABEL_ID
    assert bool(panel.iloc[0]["horizon_complete"])
    assert bool(panel.iloc[0]["primary_scope"])


def test_label_cache_mismatch_audit_detects_drift():
    runner = load_runner()
    cache_panel = pd.DataFrame(
        {
            "upper_first": [True, False],
            "lower_first": [False, True],
            "winner_positive": [True, False],
            "same_bar_conflict": [False, False],
            "horizon_complete": [True, True],
            "upper_barrier": [0.10, 0.20],
            "lower_barrier": [-0.05, -0.10],
        }
    )
    recomputed = cache_panel.copy()
    recomputed.loc[0, "winner_positive"] = False
    recomputed.loc[1, "upper_barrier"] = 0.25

    audit = runner.compare_label_cache_to_recomputed(cache_panel, recomputed, tolerance=1e-12)

    overall = audit.loc[audit["field_name"].eq("__overall__")].iloc[0]
    assert overall["mismatch_status"] == "fail"
    assert int(overall["mismatch_n"]) == 2


def test_missing_regime_uses_contract_bucket(tmp_path):
    runner = load_runner()
    regime = tmp_path / "regime.csv"
    regime.write_text("date,daily_regime_bucket,daily_regime_conflict_n,daily_regime_conflict_flag\n2020-01-01,risk_on,0,False\n", encoding="utf-8")
    panel = pd.DataFrame({"reference_date": ["2020-01-02"], "instrument": ["S1"]})

    out = runner.attach_regime(panel, {"global_regime_calendar": regime})

    assert not bool(out.iloc[0]["regime_calendar_available"])
    assert bool(out.iloc[0]["regime_missing_date_bypassed"])
    assert out.iloc[0]["market_regime_bucket"] == "missing_regime_calendar"


def test_native_threshold_freeze_does_not_use_label_outcome():
    runner = load_runner()
    config = {
        "native_universe": {
            "liquidity_quantile": 0.5,
            "continuity_threshold": 0.95,
            "volatility_floor_quantile": 0.0,
            "volatility_cap_quantile": 1.0,
        }
    }
    base = pd.DataFrame(
        {
            "split": ["train", "train", "train", "validation"],
            "money_median_20d": [10.0, 20.0, 30.0, 40.0],
            "turnover_rate_median_20d": [1.0, 2.0, 3.0, 4.0],
            "trading_continuity_20d": [1.0, 1.0, 1.0, 1.0],
            "volatility_20d": [0.01, 0.02, 0.03, 0.04],
            "winner_positive": [False, False, False, False],
        }
    )
    changed = base.copy()
    changed["winner_positive"] = [True, False, True, False]

    thresholds_a, audit_a = runner.freeze_native_thresholds(base, config)
    thresholds_b, audit_b = runner.freeze_native_thresholds(changed, config)

    assert thresholds_a == thresholds_b
    assert not audit_a["outcome_used_for_freeze"].any()
    assert audit_a["threshold_value"].tolist() == audit_b["threshold_value"].tolist()
    assert audit_a["tie_break_source"].astype(str).str.startswith("label_free").all()
    assert int(audit_a["candidate_count"].iloc[0]) > 1


def test_search_audit_counts_universe_floor_cap_grid():
    runner = load_runner()
    tokens = pd.DataFrame({"token_id": ["a"], "family_id": ["x"]})
    readout = pd.DataFrame({"token_id": ["a"], "split_bucket": ["validation"], "auc_one_vs_rest": [0.60], "treated_n": [100], "control_n": [300]})
    config = {
        "tokens": {"quantile_rules": [1, 2]},
        "native_universe": {
            "liquidity_quantile_candidates": [0.01, 0.05],
            "continuity_threshold_candidates": [0.90, 0.95],
            "volatility_floor_quantile_candidates": [0.01],
            "volatility_cap_quantile_candidates": [0.99, 0.98],
        },
        "thresholds": {},
    }

    audit = runner.build_search_audit(tokens, "a", readout, config)

    assert int(audit.iloc[0]["universe_floor_cap_candidate_n"]) == 8


def test_token_aware_matching_excludes_current_family_keys():
    runner = load_runner()
    vol_token = pd.Series({"family_id": "volatility_range", "primitive_id": "volatility_20d"})
    liq_token = pd.Series({"family_id": "liquidity_attention", "primitive_id": "money_median_20d"})
    trend_token = pd.Series({"family_id": "breakout_trend", "primitive_id": "ret_20d"})

    assert "volatility_20d_decile" in runner.exclude_match_keys(vol_token)
    assert "liquidity_metric_decile" in runner.exclude_match_keys(liq_token)
    assert runner.exclude_match_keys(trend_token) == []


def test_search_audit_uses_effective_search_space():
    runner = load_runner()
    tokens = pd.DataFrame(
        {
            "token_id": ["a", "b"],
            "family_id": ["x", "y"],
        }
    )
    readout = pd.DataFrame(
        {
            "token_id": ["a"],
            "split_bucket": ["validation"],
            "auc_one_vs_rest": [0.60],
            "treated_n": [100],
            "control_n": [300],
        }
    )
    config = {"tokens": {"quantile_rules": [1, 2, 3, 4]}, "thresholds": {}}

    audit = runner.build_search_audit(tokens, "a", readout, config)

    assert int(audit.iloc[0]["effective_search_space_n"]) > len(tokens)
    assert int(audit.iloc[0]["effective_search_space_n"]) >= int(audit.iloc[0]["token_grid_size"])


def test_utility_gate_distinguishes_per_entry_pass():
    runner = load_runner()
    treated = pd.DataFrame(
        {
            "upper_first": [True, True, False, False],
            "lower_first": [False, False, True, False],
            "same_bar_conflict": [False, False, False, False],
            "upper_barrier": [0.20, 0.20, 0.20, 0.20],
            "lower_barrier": [-0.05, -0.05, -0.05, -0.05],
        }
    )
    control = treated.head(0).copy()
    native = treated.copy()

    row = runner.badside_row("tok", "validation", treated, control, native, cost=0.001)

    assert row["utility_proxy_per_entry"] > 0
    assert row["utility_gate_status"] == "utility_pass_per_entry"


def test_utility_total_indexed_does_not_rescue_negative_per_entry():
    runner = load_runner()
    treated = pd.DataFrame(
        {
            "upper_first": [False, False, True],
            "lower_first": [True, False, False],
            "same_bar_conflict": [False, False, False],
            "upper_barrier": [0.10, 0.10, 0.10],
            "lower_barrier": [-0.20, -0.20, -0.20],
        }
    )
    native = treated.copy()

    row = runner.badside_row("tok", "validation", treated, treated.head(0), native, cost=0.01)

    assert row["utility_proxy_per_entry"] < 0
    assert row["utility_gate_status"] == "utility_fail"


def test_manifest_publishable_outputs_exclude_local_cache():
    runner = load_runner()
    publishable = runner.REPORT_DIR / "unit_publishable_marker.txt"
    local_cache = runner.LOCAL_CACHE_DIR / "unit_local_cache_marker.parquet"
    publishable.parent.mkdir(parents=True, exist_ok=True)
    local_cache.parent.mkdir(parents=True, exist_ok=True)
    publishable.write_text("x", encoding="utf-8")
    local_cache.write_text("x", encoding="utf-8")
    try:
        outputs = {"report": publishable, "native_universe_panel": local_cache, "manifest": runner.MANIFEST_DIR / "unit_manifest.json"}

        filtered = runner.publishable_manifest_outputs(outputs)

        assert "report" in filtered
        assert "native_universe_panel" not in filtered
    finally:
        publishable.unlink(missing_ok=True)
        local_cache.unlink(missing_ok=True)


def test_morphology_suspect_failed_independent_evidence_blocks_authorization():
    runner = load_runner()
    tokens = pd.DataFrame({"token_id": ["tok"], "family_id": ["reversal_drawdown"]})
    gates = {
        "label_portability_gate_status": "pass",
        "winner_uplift_gate_status": "pass",
        "badside_gate_status": "pass",
        "stability_gate_status": "pass",
        "search_control_gate_status": "pass",
        "deployability_gate_status": "pass",
        "selected_token_morphology_flag": "morphology_rediscovery_suspect",
        "selected_token_morphology_suspect_independent_evidence_status": "fail",
        "selected_token_control_match_quality": "primary_comparable",
    }

    decision = runner.decision_row("tok", tokens, "pass", "pass", "pass", gates)

    assert decision.iloc[0]["decision_state"] == "13A_native_token_diagnostic_only_badside_or_utility_fail"
    assert not bool(decision.iloc[0]["sequence_mining_authorized"])


def test_report_contains_required_contract_sections():
    runner = load_runner()
    decision = pd.DataFrame(
        [
            {
                "decision_state": "13A_no_native_token_survives_stop_event_mining",
                "next_allowed_requirement": "none",
                "selected_token_id": "tok",
                "selected_token_family_id": "fam",
                "sequence_mining_authorized": False,
                "decision_reason": "test",
            }
        ]
    )
    native = pd.DataFrame(
        {
            "split": ["train"],
            "native_scope": [True],
            "instrument": ["S1"],
            "regime_calendar_available": [True],
        }
    )
    label = pd.DataFrame(
        {
            "split_bucket": ["train"],
            "denominator_n": [1],
            "winner_positive_n": [1],
            "winner_base_rate": [1.0],
            "label_base_rate_dispersion": [0.0],
            "label_stability_status": ["pass"],
        }
    )
    tokens = pd.DataFrame({"token_id": ["tok"], "family_id": ["fam"], "primitive_id": ["p"]})
    readout = pd.DataFrame(
        {
            "token_id": ["tok"],
            "split_bucket": ["train"],
            "treated_n": [1],
            "treated_winner_rate": [1.0],
            "control_winner_rate": [0.0],
            "winner_rate_diff_vs_control": [1.0],
            "auc_one_vs_rest": [1.0],
            "top_decile_lift": [1.0],
        }
    )
    badside = pd.DataFrame({"token_id": ["tok"], "split_bucket": ["train"], "fast_fail_uplift": [0.0], "lower_first_uplift": [0.0], "utility_proxy_per_entry": [0.1], "utility_gate_status": ["utility_pass_per_entry"]})
    morphology = pd.DataFrame({"morphology_flag": ["morphology_distinct_or_low_collinearity"], "max_abs_rank_corr_with_reversal_anchor": [0.1], "morphology_suspect_independent_evidence_status": ["pass"]})
    stability = pd.DataFrame({"token_id": ["tok"], "slice_type": ["calendar_year"], "slice_value": ["2020"], "treated_n": [1], "control_n": [3], "winner_rate_diff_vs_control": [0.1], "stability_status": ["pass"]})
    search = pd.DataFrame({"selected_token_rank_train": [1], "effective_search_space_n": [10], "deflated_auc_validation": [0.6], "search_control_status": ["pass"]})
    deploy = pd.DataFrame({"token_id": ["tok"], "split_bucket": ["train"], "coverage_share": [0.1], "captured_positive_n": [1], "captured_positive_share": [1.0], "utility_proxy_total_indexed": [0.01], "deployability_status": ["pass"]})
    mismatch = pd.DataFrame({"field_name": ["__overall__"], "cache_used": [True], "mismatch_status": ["pass"], "compared_row_n": [1], "mismatch_n": [0]})

    report = runner.render_report(decision, native, label, tokens, readout, badside, morphology, stability, search, deploy, mismatch)

    assert "Native Opportunity Universe" in report
    assert "Len-1 Token Family 总览" in report
    assert "Stability / Search Control" in report
    assert "Deployability" in report
