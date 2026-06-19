from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "run_12a3_episode_precision_recall_frontier.py"
)
TABLE_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "publishable"
    / "tables"
    / "12A3_episode_precision_recall_frontier"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_12a3_frontier", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_false_repair_recompute_uses_event_t0_close_anchor():
    runner = load_runner()
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=130).strftime("%Y-%m-%d"),
            "open": [100.0] * 130,
            "high": [100.0] * 120 + [160.0] + [100.0] * 9,
            "low": [100.0, 96.0, 89.0] + [100.0] * 127,
            "close": [100.0, 98.0, 89.0] + [100.0] * 127,
        }
    )
    labels = runner.compute_label_row(
        daily,
        event_pos=0,
        trade_pos=0,
        trade_price=100.0,
        label_cfg={
            "failure_horizon": 10,
            "failure_lower": -0.10,
            "false_repair_horizon": 20,
            "false_repair_drawdown": -0.10,
            "winner_horizon": 120,
            "winner_mfe": 0.50,
        },
    )

    assert labels["false_repair_20d_label"] is True
    assert labels["horizon_complete_20d"] is True
    assert labels["fast_fail_10d_label"] is True
    assert labels["winner_120_label"] is True


def test_recanonicalize_instances_recomputes_b3_before_b1_and_union_cooldown():
    runner = load_runner()
    config = runner.load_yaml(runner.CONFIG_PATH)
    base = {
        "instrument": "SZ000001",
        "event_t0_date": "2020-01-10",
        "event_t0_pos": 10,
        "event_signal_time": "t0_close",
        "trade_open_date": "2020-01-13",
        "trade_open_pos": 11,
        "trade_open_price": 10.0,
        "event_split": "train",
        "board_bucket": "main_board",
        "market_regime_bucket": "risk_on",
        "raw_event_status": "triggered",
        "family_input_status": "runnable_existing_data",
        "non_executable_next_open": False,
        "event_t0_pit_status": "pass",
        "trade_open_pit_status": "pass",
        "first_trigger_status": "first_observed_in_sample",
        "allowed_for_primary_canonical_flag": True,
    }
    rows = [
        {**base, "event_instance_id": "b1", "family_id": "B1", "variant_id": "B1a", "family_variant_id": "B1_B1a"},
        {**base, "event_instance_id": "b3", "family_id": "B3", "variant_id": "B3a", "family_variant_id": "B3_B3a"},
        {
            **base,
            "event_instance_id": "b1_late_blocked",
            "family_id": "B1",
            "variant_id": "B1a",
            "family_variant_id": "B1_B1a",
            "event_t0_date": "2020-01-15",
            "event_t0_pos": 15,
        },
        {
            **base,
            "event_instance_id": "b1_late_kept",
            "family_id": "B1",
            "variant_id": "B1a",
            "family_variant_id": "B1_B1a",
            "event_t0_date": "2020-02-03",
            "event_t0_pos": 21,
        },
    ]

    out = runner.recanonicalize_instances(pd.DataFrame(rows), config)

    assert out["primary_family_id"].tolist() == ["B3", "B1"]
    assert out.iloc[0]["triggered_family_variants"] == "B1_B1a;B3_B3a"
    assert len(out) == 2


def test_recanonicalize_instances_filters_nonexecutable_and_non_triggered_rows():
    runner = load_runner()
    config = runner.load_yaml(runner.CONFIG_PATH)
    base = {
        "instrument": "SZ000001",
        "event_t0_date": "2020-01-10",
        "event_t0_pos": 10,
        "trade_open_date": "2020-01-13",
        "trade_open_pos": 11,
        "trade_open_price": 10.0,
        "event_split": "train",
        "board_bucket": "main_board",
        "market_regime_bucket": "risk_on",
        "event_t0_pit_status": "pass",
        "trade_open_pit_status": "pass",
        "first_trigger_status": "first_observed_in_sample",
        "allowed_for_primary_canonical_flag": True,
        "family_id": "B1",
        "variant_id": "B1a",
        "family_variant_id": "B1_B1a",
    }
    rows = [
        {
            **base,
            "event_instance_id": "ok",
            "raw_event_status": "triggered",
            "family_input_status": "runnable_existing_data",
            "non_executable_next_open": False,
        },
        {
            **base,
            "event_instance_id": "raw_blocked",
            "raw_event_status": "not_triggered",
            "family_input_status": "runnable_existing_data",
            "non_executable_next_open": False,
            "event_t0_date": "2020-01-20",
            "event_t0_pos": 20,
        },
        {
            **base,
            "event_instance_id": "non_exec",
            "raw_event_status": "triggered",
            "family_input_status": "runnable_existing_data",
            "non_executable_next_open": True,
            "event_t0_date": "2020-02-10",
            "event_t0_pos": 40,
        },
    ]

    out = runner.recanonicalize_instances(pd.DataFrame(rows), config)

    assert out["primary_event_instance_id"].tolist() == ["ok"]


def test_frontier_split_precision_requires_event_split_episode_split_match():
    runner = load_runner()
    episodes = pd.DataFrame(
        [
            {
                "episode_id": "ep_validation",
                "instrument": "SZ000001",
                "split": "validation",
                "board_bucket": "main_board",
                "episode_low_date": "2020-01-10",
                "episode_high_date": "2020-01-20",
                "first_50pct_date": "2020-01-18",
                "pre120_calendar_start_date": "2019-09-12",
                "episode_low_pos": 10,
                "episode_high_pos": 20,
                "first_50pct_pos": 18,
            }
        ]
    )
    events = pd.DataFrame(
        [
            {
                "event_key": "ev_train_inside_validation_episode",
                "instrument": "SZ000001",
                "event_t0_date": "2020-01-12",
                "event_t0_pos": 12,
                "event_split": "train",
                "primary_family_id": "B1",
                "board_bucket": "main_board",
                "market_regime_bucket": "risk_on",
                "next_open_executable_flag": True,
                "horizon_complete_10d": True,
                "fast_fail_10d_label": False,
                "horizon_complete_20d": True,
                "false_repair_20d_label": False,
                "horizon_complete_120d": True,
                "winner_120_label": True,
            }
        ]
    )
    registry = pd.DataFrame(
        [{"frontier_arm_id": "unit_arm", "decision_role": "unit_test"}]
    )

    frontier, _, _, _ = runner.build_frontier_outputs(
        {"unit_arm": events},
        registry,
        episodes,
        denominator_years=1.0,
        r_core_mean_density=1.0,
    )
    all_row = frontier.loc[
        frontier["split"].eq("all") & frontier["window_id"].eq("low_to_high")
    ].iloc[0]
    validation_row = frontier.loc[
        frontier["split"].eq("validation") & frontier["window_id"].eq("low_to_high")
    ].iloc[0]

    assert all_row["captured_episode_n"] == 1
    assert validation_row["event_n"] == 0
    assert validation_row["captured_episode_n"] == 0


def test_publishable_outputs_match_required_contract_after_full_run():
    required_columns = {
        "input_artifact_audit.csv": {
            "artifact_id",
            "relative_path",
            "resolved_path",
            "required_flag",
            "read_status",
            "schema_status",
            "row_count",
            "sha256",
            "mtime_utc",
            "notes",
        },
        "frontier_arm_registry.csv": {
            "frontier_arm_id",
            "arm_role",
            "source_population",
            "source_path",
            "event_selection_rule",
            "priority_policy",
            "is_primary_decision_arm",
            "is_benchmark_arm",
            "is_sensitivity_arm",
            "is_family_slice",
        },
        "backbone_episode_recall_precision_frontier.csv": {
            "frontier_arm_id",
            "arm_role",
            "event_precision",
            "outside_event_rate",
            "r_core_event_precision",
            "recall_retention_vs_r_core",
            "precision_delta_vs_r_core",
            "bad_side_10_20_rate",
            "winner_120_rate",
            "frontier_status",
        },
        "backbone_event_timing_distribution.csv": {
            "timing_population",
            "matched_event_n",
            "captured_episode_n",
            "event_minus_low_trading_days_median",
            "first_event_minus_low_trading_days_median",
            "timing_denominator_status",
        },
        "backbone_b8_incremental_episode_recall.csv": {
            "b8_incremental_episode_n",
            "b8_incremental_event_precision",
            "b8_incremental_bad_side_10_20_rate",
            "incremental_status",
        },
        "backbone_frontier_decision.csv": {
            "decision",
            "decision_reason",
            "primary_candidate_arm_id",
            "supported_gate_pass",
            "partial_feature_source_gate_pass",
            "recommended_next_requirement",
            "block_reason",
        },
    }

    for file_name, columns in required_columns.items():
        frame = pd.read_csv(TABLE_DIR / file_name, nrows=1)
        assert columns.issubset(frame.columns), file_name


def test_required_arms_and_slice_types_are_materialized():
    arms = set(pd.read_csv(TABLE_DIR / "frontier_arm_registry.csv")["frontier_arm_id"])
    required_arms = {
        "08_R_core_event_regime_gated_raw",
        "08_R6_event_regime_gated_raw",
        "12A2_C0_primary_canonical_union",
        "12A2_B1_primary",
        "12A2_B2_primary",
        "12A2_B3_primary",
        "12A2_B4_primary",
        "12A2_B5_primary",
        "12A2_B6_primary",
        "12A2_B8_primary",
        "12A2_multi_family_trigger_ge2",
        "12A2_single_family_trigger",
        "12A2_B8_only_same_event_diagnostic",
        "12A2_B8_incremental_episode_recall_vs_B1_B3_B5",
        "12A2_B1_B3_collision_current_priority",
        "12A2_B3_before_B1_priority_sensitivity",
    }
    assert required_arms.issubset(arms)

    slice_types = set(pd.read_csv(TABLE_DIR / "backbone_frontier_slice_readout.csv")["slice_type"])
    assert {
        "board_bucket",
        "market_regime_bucket",
        "primary_family_id",
        "triggered_family_count_bucket",
    }.issubset(slice_types)


def test_decision_state_is_allowed_and_primary_arm_name_matches_requirement():
    decision = pd.read_csv(TABLE_DIR / "backbone_frontier_decision.csv").iloc[0]

    assert decision["decision"] in {
        "12A3_state_change_backbone_supported",
        "12A3_state_change_backbone_partial_feature_source",
        "12A3_no_backbone_improvement_over_r_core",
        "12A3_input_blocked",
        "12A3_frontier_incomplete",
    }
    assert decision["primary_candidate_arm_id"] == "12A2_C0_primary_canonical_union"
