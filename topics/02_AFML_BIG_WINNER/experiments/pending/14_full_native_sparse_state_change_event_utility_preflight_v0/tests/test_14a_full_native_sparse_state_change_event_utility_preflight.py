from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_14a_full_native_sparse_state_change_event_utility_preflight.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_14a_full_native_sparse_state_change_event_utility_preflight", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_native_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": ["r1", "r2", "r3"],
            "instrument": ["S1", "S1", "S2"],
            "reference_date": ["2020-01-02", "2020-01-03", "2020-01-02"],
            "split": ["train", "train", "validation"],
            "native_scope": [True, True, True],
            "upper_barrier": [0.10, 0.10, 0.20],
            "lower_barrier": [-0.05, -0.05, -0.08],
            "winner_positive": [True, False, False],
            "upper_first": [True, False, False],
            "lower_first": [False, True, False],
            "same_bar_conflict": [False, False, True],
            "horizon_close_return": [0.04, -0.03, 0.01],
            "entry_date": ["2020-01-03", "2020-01-06", "2020-01-03"],
            "entry_pos": [1, 2, 1],
            "entry_price": [10.0, 10.2, 20.0],
            "horizon_complete": [True, True, True],
            "max_high_return": [0.12, 0.03, 0.02],
            "min_low_return": [-0.01, -0.06, -0.09],
        }
    )


def test_adapter_uses_native_source_and_derives_fast_fail():
    runner = load_runner()
    native = base_native_panel()
    label = native[
        [
            "row_id",
            "instrument",
            "reference_date",
            "split",
            "upper_barrier",
            "lower_barrier",
            "winner_positive",
            "upper_first",
            "lower_first",
            "same_bar_conflict",
            "horizon_complete",
        ]
    ].copy()

    adapted, audit, status = runner.adapt_native_panel(native, label)

    assert status == "pass"
    assert adapted["split_bucket"].tolist() == ["train", "train", "validation"]
    assert adapted["upper_barrier_return"].tolist() == [0.10, 0.10, 0.20]
    assert adapted["terminal_return_20d"].tolist() == [0.04, -0.03, 0.01]
    assert adapted["fast_fail"].tolist() == [False, True, True]
    assert "native_label_panel" in set(audit["source_artifact_id"])
    checked = set(audit.loc[audit["source_artifact_id"].eq("native_label_panel"), "source_column"])
    assert {"split", "upper_first", "horizon_complete"} <= checked
    assert audit.loc[audit["target_column"].eq("fast_fail"), "adapter_rule"].iloc[0] == "or_derive"


def test_adapter_cross_check_fails_on_label_drift():
    runner = load_runner()
    native = base_native_panel()
    label = native[
        [
            "row_id",
            "instrument",
            "reference_date",
            "split",
            "upper_barrier",
            "lower_barrier",
            "winner_positive",
            "upper_first",
            "lower_first",
            "same_bar_conflict",
            "horizon_complete",
        ]
    ].copy()
    label.loc[0, "upper_barrier"] = 0.11

    _adapted, audit, status = runner.adapt_native_panel(native, label)

    assert status == "fail"
    upper_check = audit.loc[
        audit["source_artifact_id"].eq("native_label_panel") & audit["source_column"].eq("upper_barrier")
    ].iloc[0]
    assert upper_check["value_match_status"] == "mismatch"


def test_adapter_requires_full_cross_check_key():
    runner = load_runner()
    native = base_native_panel()
    label = native[
        [
            "row_id",
            "instrument",
            "split",
            "upper_barrier",
            "lower_barrier",
            "winner_positive",
            "upper_first",
            "lower_first",
            "same_bar_conflict",
            "horizon_complete",
        ]
    ].copy()

    _adapted, audit, status = runner.adapt_native_panel(native, label)

    assert status == "fail"
    key_check = audit.loc[audit["target_column"].eq("native_universe_panel.__cross_check_key__")].iloc[0]
    assert "reference_date" in key_check["value_match_status"]


def test_missing_13a_cache_inputs_are_optional_for_rebuild():
    runner = load_runner()
    audit = pd.DataFrame(
        {
            "artifact_id": [
                "upstream_13a_native_universe_cache",
                "upstream_13a_native_label_cache",
                "upstream_13a_native_token_matrix_cache",
                "pit_topn_400_100_executable_daily",
            ],
            "read_status": ["missing", "missing", "missing", "pass"],
            "schema_status": ["missing_columns:row_id", "missing_columns:row_id", "missing_columns:row_id", "pass"],
            "required_flag": [False, False, False, True],
            "lineage_role": ["upstream_13a_lineage", "upstream_13a_lineage", "upstream_13a_lineage", "raw_local_data_input"],
        }
    )

    status, reason = runner.input_gate_status(audit)

    assert status == "pass"
    assert reason == ""


def test_parameter_grid_is_frozen_at_16_specs():
    runner = load_runner()
    config = runner.r13a.load_yaml(runner.CONFIG_PATH)

    specs = runner.parameter_specs(config)
    counts = pd.Series([spec.family_id for spec in specs]).value_counts().to_dict()

    assert len(specs) == 16
    assert counts == {
        "F1_residual_cusum_break": 4,
        "F2_compression_to_directional_expansion": 2,
        "F3_controlled_damage_first_reclaim": 2,
        "F4_board_relative_strength_rank_jump": 4,
        "F5_participation_ignition_with_price_control": 2,
        "F6_low_volatility_range_expansion_first_trigger": 2,
    }


def test_first_trigger_reset_and_cooldown_duplicate_suppression():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "row_id": [f"r{i}" for i in range(6)],
            "instrument": ["S1"] * 6,
            "reference_date": pd.date_range("2020-01-01", periods=6).strftime("%Y-%m-%d"),
            "split_bucket": ["train"] * 6,
            "board_bucket": ["main_board"] * 6,
            "calendar_year": [2020] * 6,
            "instrument_year": ["S1_2020"] * 6,
        }
    )
    spec = runner.ArmSpec("F5_participation_ignition_with_price_control", "synthetic", 3, {})
    raw = pd.Series([False, True, False, True, False, True])
    reset = pd.Series([True, False, True, False, True, False])
    intensity = pd.Series([0.0, 1.1, 0.0, 1.2, 0.0, 1.3])

    events, audit = runner.generate_events_for_spec(panel, spec, raw, intensity, reset, "pass")

    assert events["reference_date"].tolist() == ["2020-01-02", "2020-01-06"]
    assert audit["raw_transition_n"] == 3
    assert audit["duplicate_suppressed_n"] == 1


def test_f4_requires_same_date_board_rank_pit_columns():
    runner = load_runner()
    spec = runner.ArmSpec("F4_board_relative_strength_rank_jump", "ret20_jump2", 15, {"window": 20, "jump": 2})
    panel = pd.DataFrame(
        {
            "row_id": ["r1", "r2"],
            "reference_date": ["2020-01-01", "2020-01-02"],
            "board_bucket": ["main_board", "main_board"],
            "split_bucket": ["train", "train"],
            "ret_20d": [0.01, 0.02],
            "volatility_20d": [0.01, 0.02],
        }
    )

    _raw, _intensity, _reset, status = runner.state_for_spec(panel, spec, {"volatility_20d_p20": 0.02})

    assert status == "blocked_pit_availability"


def test_label_rebuild_audit_recomputes_and_detects_entry_anchor_drift(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    dates = pd.bdate_range("2020-01-01", periods=40).strftime("%Y-%m-%d")
    pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 40,
            "high": [10.05] * 40,
            "low": [9.95] * 40,
            "close": [10.0] * 40,
            "volume": [1000.0] * 40,
            "money": [100000.0] * 40,
            "turnover_rate": [0.01] * 40,
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    panel = pd.DataFrame(
        {
            "row_id": ["r1"],
            "instrument": ["S1"],
            "entry_pos": [1],
            "entry_price": [10.0],
            "volatility_20d": [0.01],
        }
    )
    label = runner.r13a.compute_label(
        panel,
        runner.r13a.StockDailyCache(qfq_dir),
        k_up=2.0,
        k_dn=1.0,
        horizon_sessions=20,
        vol_reference_unit="daily_return_std",
    )
    cache_panel = pd.concat([panel, label], axis=1)
    cache_panel["winner_positive"] = ~cache_panel["winner_positive"]

    audit = runner.build_row_rebuild_audit(
        cache_panel,
        "pass",
        {"selected_label": {"k_up": 2.0, "k_dn": 1.0, "horizon_sessions": 20}, "label_rebuild_audit": {"minimum_audited_rows": 1}},
        {"stock_daily_qfq_dir": qfq_dir},
    )

    overall = audit.loc[audit["field_name"].eq("__overall__")].iloc[0]
    assert overall["rebuild_status"] == "fail"
    assert int(overall["mismatch_n"]) > 0


def test_f1_uses_positive_cusum_z_not_plain_residual_z():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "instrument": ["S1", "S1"],
            "residual_cusum_z_60d": [0.0, 3.1],
            "residual_z_60d": [0.0, 0.1],
            "residual_return_1d": [0.01, 0.02],
        }
    )
    spec = runner.ArmSpec("F1_residual_cusum_break", "lookback60_z2p5", 20, {"lookback": 60, "z": 2.5})

    raw, intensity, _reset, status = runner.state_for_spec(panel, spec, {"volatility_20d_p20": 0.01})

    assert status == "pass"
    assert raw.tolist() == [False, True]
    assert intensity.tolist() == [0.0, 3.1]


def test_family_reset_requires_five_consecutive_sessions():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "instrument": ["S1"] * 6,
            "participation_ratio_20d": [0.5, 0.5, 0.5, 0.5, 0.5, 1.2],
            "daily_return_1d": [0.01] * 6,
        }
    )
    spec = runner.ArmSpec("F5_participation_ignition_with_price_control", "window20_ratio1p5", 15, {"window": 20, "ratio": 1.5})

    _raw, _intensity, reset, _status = runner.state_for_spec(panel, spec, {"volatility_20d_p20": 0.01})

    assert reset.tolist() == [False, False, False, False, True, False]


def test_raw_opportunity_uses_native_baseline_and_train_intensity_delta():
    runner = load_runner()
    native = pd.DataFrame(
        {
            "split_bucket": ["train"] * 5,
            "winner": [False, False, False, True, True],
            "fast_fail": [False] * 5,
            "lower_first": [False] * 5,
            "same_bar_conflict": [False] * 5,
            "max_high_return": [0.01, 0.01, 0.02, 0.02, 0.02],
            "min_low_return": [-0.01] * 5,
            "instrument_year": [f"S{i}_2020" for i in range(5)],
        }
    )
    events = pd.DataFrame(
        {
            "raw_event_arm_id": ["F1__x"] * 5,
            "family_id": ["F1_residual_cusum_break"] * 5,
            "parameter_set_id": ["x"] * 5,
            "split_bucket": ["train"] * 5,
            "instrument": [f"S{i}" for i in range(5)],
            "instrument_year": [f"S{i}_2020" for i in range(5)],
            "winner": [False, False, True, True, True],
            "fast_fail": [False] * 5,
            "lower_first": [False] * 5,
            "same_bar_conflict": [False] * 5,
            "upper_barrier_return": [0.10] * 5,
            "lower_barrier_return": [-0.05] * 5,
            "terminal_return_20d": [0.03] * 5,
            "max_high_return": [0.03] * 5,
            "min_low_return": [-0.01] * 5,
            "event_intensity_score": [1, 2, 3, 4, 5],
            "path_utility_component_0bps": [0.01] * 5,
            "path_utility_component_50bps": [0.005] * 5,
            "path_utility_component_100bps": [0.0] * 5,
        }
    )
    config = {
        "thresholds": {
            "raw_intensity_side_min_n": 1,
            "raw_winner_rate_lift": 0.5,
            "raw_intensity_top_bottom_delta": 0.5,
        }
    }

    readout = runner.raw_readout(events, native, config)
    row = readout.iloc[0]

    assert math.isclose(row["native_baseline_winner_rate"], 0.4)
    assert math.isclose(row["winner_rate"], 0.6)
    assert row["raw_intensity_status"] == "pass"
    assert math.isclose(row["raw_intensity_top_bottom_winner_rate_delta"], 1.0)
    assert row["raw_opportunity_surface_status"] == "pass"


def test_cohort_same_event_denominator_keeps_skipped_events_as_zero():
    runner = load_runner()
    raw_arm = "F1__x"
    panel = pd.DataFrame(
        {
            "row_id": [f"r{i}" for i in range(4)],
            "reference_date": ["2020-01-02"] * 4,
            "board_bucket": ["main_board"] * 4,
        }
    )
    events = pd.DataFrame(
        {
            "row_id": [f"r{i}" for i in range(4)],
            "raw_event_arm_id": [raw_arm] * 4,
            "family_id": ["F1_residual_cusum_break"] * 4,
            "parameter_set_id": ["x"] * 4,
            "split_bucket": ["train"] * 4,
            "instrument": [f"S{i}" for i in range(4)],
            "reference_date": ["2020-01-02"] * 4,
            "board_bucket": ["main_board"] * 4,
            "instrument_year": [f"S{i}_2020" for i in range(4)],
            "event_intensity_score": [1.0, 2.0, 3.0, 4.0],
            "path_utility_component_50bps": [0.0, 0.0, 0.0, 0.4],
            "winner": [False, False, False, True],
            "fast_fail": [False] * 4,
            "lower_first": [False] * 4,
            "same_bar_conflict": [False] * 4,
        }
    )
    raw = pd.DataFrame(
        {
            "raw_event_arm_id": [raw_arm],
            "split_bucket": ["train"],
            "raw_opportunity_surface_status": ["pass"],
            "utility_per_event_mean_50bps": [0.0],
            "winner_rate_lift": [0.1],
        }
    )
    density = pd.DataFrame({"raw_event_arm_id": [raw_arm], "split_bucket": ["train"], "density_gate_status": ["pass"]})
    config = {
        "thresholds": {
            "min_train_selected_event_n": 1,
            "selected_event_fraction_min": 0.0,
            "selected_event_fraction_max": 1.0,
        },
        "cohort_arms": {
            "rank_cutoffs": {"top25pct": 0.75},
            "minimum_cohort_finite_n": {"C1": 1, "C2": 1, "C3": 99, "C4": 99, "C5": 99, "C6": 99},
            "rolling_prior_sessions": 252,
        },
        "search_accounting": {"maximum_train_selected_raw_arms_into_cohort": 1, "maximum_operating_arms_allowed_into_validation": 1},
    }
    state_cache = {raw_arm: (pd.Series([True] * 4), pd.Series([1.0, 2.0, 3.0, 4.0]))}

    _availability, readout, _transport, normalized = runner.build_cohort_readouts(panel, events, state_cache, raw, density, config)

    c1 = readout.loc[readout["cohort_arm_id"].eq("C1") & readout["rank_cutoff_id"].eq("top25pct")].iloc[0]
    assert int(c1["same_event_denominator_n"]) == 4
    assert int(c1["selected_event_n"]) == 1
    assert int(c1["skipped_event_n"]) == 3
    assert math.isclose(c1["same_event_utility_mean_50bps"], 0.1)
    assert math.isclose(c1["selected_entry_diagnostic_utility_mean_50bps"], 0.4)
    assert int(normalized.loc[normalized["cohort_arm_id"].eq("C1"), "skipped_event_flag"].sum()) == 3


def test_partial_event_cohort_marks_first_event_degenerate():
    runner = load_runner()
    events = pd.DataFrame(
        {
            "raw_event_arm_id": ["F3__x", "F3__x"],
            "reference_date": ["2020-01-02", "2020-01-03"],
            "instrument": ["S1", "S2"],
            "board_bucket": ["main_board", "main_board"],
            "event_intensity_score": [1.0, 2.0],
        }
    )

    ranked = runner.compute_event_cohort_ranks(events, "F3__x", "C5", min_n=2, rolling_prior_n=252)

    assert ranked["cohort_rank_status"].tolist() == ["degenerate_partial_cohort", "pass"]
    assert math.isclose(ranked.iloc[1]["cohort_percentile_rank"], 0.75)


def test_c3_rolling_prior_excludes_future_rows_by_global_date_rank():
    runner = load_runner()
    events = pd.DataFrame(
        {
            "raw_event_arm_id": ["F3__x", "F3__x"],
            "reference_date": ["2020-01-10", "2020-01-03"],
            "reference_date_rank": [5, 1],
            "instrument": ["S1", "S2"],
            "board_bucket": ["main_board", "main_board"],
            "event_intensity_score": [10.0, 1.0],
        }
    )

    ranked = runner.compute_event_cohort_ranks(events, "F3__x", "C3", min_n=1, rolling_prior_n=252)
    by_date = ranked.set_index("reference_date")

    assert by_date.loc["2020-01-03", "cohort_rank_status"] == "insufficient_cohort"
    assert by_date.loc["2020-01-10", "cohort_rank_status"] == "pass"


def test_sparse_event_panel_carries_event_t0_and_reset_metadata():
    runner = load_runner()
    panel = pd.DataFrame(
        {
            "row_id": ["r1", "r2"],
            "instrument": ["S1", "S1"],
            "reference_date": ["2020-01-01", "2020-01-02"],
            "reference_pos": [10, 11],
            "reference_date_rank": [0, 1],
            "split_bucket": ["train", "train"],
            "board_bucket": ["main_board", "main_board"],
            "calendar_year": [2020, 2020],
            "instrument_year": ["S1_2020", "S1_2020"],
        }
    )
    spec = runner.ArmSpec("F1_residual_cusum_break", "synthetic", 1, {})

    events, _audit = runner.generate_events_for_spec(
        panel,
        spec,
        pd.Series([True, False]),
        pd.Series([3.0, 0.0]),
        pd.Series([True, True]),
        "pass",
    )

    assert events.iloc[0]["event_t0_pos"] == 10
    assert events.iloc[0]["reference_date_rank"] == 0
    assert events.iloc[0]["reset_state_id"] == "F1_residual_cusum_break__synthetic__reset"


def test_density_failure_in_any_split_excludes_raw_arm_from_cohort():
    runner = load_runner()
    raw_arm = "F1__x"
    events = pd.DataFrame(
        {
            "row_id": ["r1", "r2"],
            "raw_event_arm_id": [raw_arm, raw_arm],
            "family_id": ["F1_residual_cusum_break", "F1_residual_cusum_break"],
            "parameter_set_id": ["x", "x"],
            "split_bucket": ["train", "validation"],
            "instrument": ["S1", "S1"],
            "reference_date": ["2020-01-01", "2020-01-02"],
            "board_bucket": ["main_board", "main_board"],
            "event_intensity_score": [1.0, 2.0],
            "path_utility_component_50bps": [0.1, 0.1],
            "winner": [True, True],
            "fast_fail": [False, False],
            "lower_first": [False, False],
            "same_bar_conflict": [False, False],
        }
    )
    raw = pd.DataFrame(
        {
            "raw_event_arm_id": [raw_arm],
            "split_bucket": ["train"],
            "raw_opportunity_surface_status": ["pass"],
            "utility_per_event_mean_50bps": [0.1],
            "winner_rate": [1.0],
            "fast_fail_rate": [0.0],
            "lower_first_rate": [0.0],
            "winner_rate_lift": [0.1],
        }
    )
    density = pd.DataFrame(
        {
            "raw_event_arm_id": [raw_arm, raw_arm],
            "split_bucket": ["train", "validation"],
            "density_gate_status": ["pass", "fail_duplicate_fraction"],
            "event_density_per_instrument_year": [1.0, 1.0],
            "duplicate_episode_fraction": [0.0, 0.9],
        }
    )
    state_cache = {raw_arm: (pd.Series([True, True]), pd.Series([1.0, 2.0]))}

    _availability, readout, _transport, _normalized = runner.build_cohort_readouts(
        pd.DataFrame({"row_id": ["r1", "r2"], "reference_date": ["2020-01-01", "2020-01-02"], "board_bucket": ["main_board", "main_board"]}),
        events,
        state_cache,
        raw,
        density,
        {"cohort_arms": {"minimum_cohort_finite_n": {"C1": 1}, "rank_cutoffs": {"top20pct": 0.8}}, "thresholds": {"min_train_selected_event_n": 1}},
    )

    assert readout.empty


def test_badside_veto_fails_closed_on_missing_uplift():
    runner = load_runner()
    selected = pd.DataFrame(
        {
            "raw_event_arm_id": ["F1__x", "F1__x", "F1__x"],
            "family_id": ["F1", "F1", "F1"],
            "parameter_set_id": ["x", "x", "x"],
            "cohort_arm_id": ["C1", "C1", "C1"],
            "rank_cutoff_id": ["top20pct", "top20pct", "top20pct"],
            "split_bucket": ["train", "validation", "robustness"],
            "same_event_utility_mean_50bps": [0.01, 0.01, 0.01],
            "same_event_utility_delta_50bps": [0.01, 0.01, 0.01],
            "selected_event_n": [50, 50, 50],
            "cohort_availability_gate_status": ["pass", "pass", "pass"],
            "fast_fail_uplift": [np.nan, np.nan, np.nan],
            "lower_first_uplift": [0.0, 0.0, 0.0],
            "operating_arm_selected": [True, True, True],
        }
    )

    decision = runner.decision_row(
        "pass",
        "",
        pd.DataFrame({"lineage_status": ["pass"]}),
        "pass",
        pd.DataFrame({"label_portability_status": ["pass"]}),
        pd.DataFrame({"native_scope": [True]}),
        pd.DataFrame({"accepted_event_n": [1]}),
        pd.DataFrame({"raw_event_arm_id": ["F1__x"], "density_gate_status": ["pass"]}),
        pd.DataFrame({"raw_opportunity_surface_status": ["pass"]}),
        selected,
        pd.DataFrame({"raw_event_arm_id": ["F1__x"], "cohort_arm_id": ["C1"], "rank_cutoff_id": ["top20pct"], "morphology_independent_evidence_status": ["pass"]}),
        pd.DataFrame({"validation_stress_status": ["stress_interval"]}),
        pd.DataFrame({"search_accounting_gate_status": ["pass"]}),
        {"thresholds": {}},
    )

    row = decision.iloc[0]
    assert row["badside_veto_gate_status"] == "fail"
    assert row["gate_failure"] == "badside_veto_gate_failed"


def test_f2_morphology_gate_fails_on_compression_rediscovery(tmp_path):
    runner = load_runner()
    token_matrix_path = tmp_path / "native_token_matrix.csv"
    token_dict_path = tmp_path / "native_token_dictionary.csv"
    pd.DataFrame({"row_id": ["r1", "r2"], "compression_token": [True, True]}).to_csv(token_matrix_path, index=False)
    pd.DataFrame({"token_id": ["compression_token"], "family_id": ["volatility_range"], "primitive_id": ["range_compression"]}).to_csv(token_dict_path, index=False)
    events = pd.DataFrame({"raw_event_arm_id": ["F2__x", "F2__x"], "row_id": ["r1", "r2"]})
    cohort_readout = pd.DataFrame(
        {
            "raw_event_arm_id": ["F2__x"],
            "cohort_arm_id": ["C1"],
            "rank_cutoff_id": ["top20pct"],
            "operating_arm_selected": [True],
        }
    )
    normalized = pd.DataFrame(
        {
            "raw_event_arm_id": ["F2__x", "F2__x"],
            "cohort_arm_id": ["C1", "C1"],
            "rank_cutoff_id": ["top20pct", "top20pct"],
            "family_id": ["F2_compression_to_directional_expansion"] * 2,
            "split_bucket": ["train", "train"],
            "row_id": ["r1", "r2"],
            "selected_event_flag": [True, True],
            "path_utility_component_50bps": [-0.01, -0.02],
            "winner": [False, False],
        }
    )
    resolved = {
        "upstream_13a_native_token_matrix_cache": token_matrix_path,
        "upstream_13a_token_dictionary": token_dict_path,
    }
    config = {"thresholds": {"morphology_overlap_fail_threshold": 0.70, "morphology_strict_overlap_threshold": 0.50}}

    morphology = runner.build_morphology(events, cohort_readout, normalized, resolved, config)

    assert "fail_compression_low_vol_rediscovery" in set(morphology["morphology_independent_evidence_status"])


def test_decision_precedence_blocks_on_input_failure():
    runner = load_runner()

    decision = runner.decision_row(
        "fail",
        "required_local_data_artifact_missing",
        pd.DataFrame(),
        "fail",
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        {"thresholds": {}},
    )

    row = decision.iloc[0]
    assert row["decision_state"] == "14A_input_blocked"
    assert row["primary_failure_reason"] == "required_local_data_artifact_missing"


def test_same_event_failure_takes_precedence_over_stress_stop():
    runner = load_runner()
    selected = pd.DataFrame(
        {
            "raw_event_arm_id": ["F1__x", "F1__x", "F1__x"],
            "family_id": ["F1", "F1", "F1"],
            "parameter_set_id": ["x", "x", "x"],
            "cohort_arm_id": ["C1", "C1", "C1"],
            "rank_cutoff_id": ["top20pct", "top20pct", "top20pct"],
            "split_bucket": ["train", "validation", "robustness"],
            "same_event_utility_mean_50bps": [0.02, -0.01, 0.02],
            "same_event_utility_delta_50bps": [0.01, 0.01, 0.01],
            "selected_event_n": [50, 50, 50],
            "cohort_availability_gate_status": ["pass", "pass", "pass"],
            "fast_fail_uplift": [0.0, 0.0, 0.0],
            "lower_first_uplift": [0.0, 0.0, 0.0],
            "operating_arm_selected": [True, True, True],
        }
    )

    decision = runner.decision_row(
        "pass",
        "",
        pd.DataFrame({"lineage_status": ["pass"]}),
        "pass",
        pd.DataFrame({"label_portability_status": ["pass"]}),
        pd.DataFrame({"native_scope": [True]}),
        pd.DataFrame({"accepted_event_n": [1]}),
        pd.DataFrame({"raw_event_arm_id": ["F1__x"], "density_gate_status": ["pass"]}),
        pd.DataFrame({"raw_opportunity_surface_status": ["pass"]}),
        selected,
        pd.DataFrame({"raw_event_arm_id": ["F1__x"], "cohort_arm_id": ["C1"], "rank_cutoff_id": ["top20pct"], "morphology_independent_evidence_status": ["pass"]}),
        pd.DataFrame({"validation_stress_status": ["stress_interval"]}),
        pd.DataFrame({"search_accounting_gate_status": ["pass"]}),
        {"thresholds": {}},
    )

    row = decision.iloc[0]
    assert row["decision_state"] == "14A_diagnostic_cohort_signal_only_no_utility"
    assert row["gate_failure"] == "same_event_utility_50bps_failed"
    assert row["validation_stress_gate_status"] == "fail"


def test_manifest_includes_publishable_outputs_and_excludes_local_cache(tmp_path, monkeypatch):
    runner = load_runner()
    local_root = tmp_path / "local_cache"
    publishable = tmp_path / "publishable" / "table.csv"
    local = local_root / "panel.parquet"
    manifest_path = tmp_path / "manifest.json"
    publishable.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    publishable.write_text("a\n1\n", encoding="utf-8")
    local.write_text("not a real parquet for manifest hashing\n", encoding="utf-8")
    monkeypatch.setattr(runner, "LOCAL_CACHE_DIR", local_root)

    manifest = runner.build_manifest(
        tmp_path / "config.yaml",
        {"x": 1},
        {"publishable_table": publishable, "local_cache_panel": local, "manifest": manifest_path},
        pd.DataFrame({"artifact_id": ["x"], "read_status": ["pass"]}),
        "14A_check_inputs_pass",
    )

    assert "publishable_table" in manifest["outputs"]
    assert "local_cache_panel" not in manifest["outputs"]
    assert "publishable_table" in manifest["output_hashes"]
