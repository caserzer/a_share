from __future__ import annotations

import importlib.util
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = EXPERIMENT_ROOT / "src/run_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.py"
CONFIG = EXPERIMENT_ROOT / "configs/config_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.yaml"
spec = importlib.util.spec_from_file_location("turnctl", RUNNER)
assert spec and spec.loader
turnctl = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = turnctl
spec.loader.exec_module(turnctl)


def _policy(policy_id: str) -> pd.Series:
    registry = turnctl.build_policy_registry().set_index("policy_id")
    return registry.loc[policy_id]


def _assignment() -> pd.DataFrame:
    rows = []
    named = {
        6: ["D6_OLD"],
        7: ["D7_OLD"],
        8: ["D8_A", "D8_B"] + [f"D8_{index:02d}" for index in range(2, 34)],
        9: ["D9_A", "D9_B"] + [f"D9_{index:02d}" for index in range(2, 34)],
        10: ["D10_A", "D10_B"] + [f"D10_{index:02d}" for index in range(2, 34)],
    }
    for bucket, names in named.items():
        for offset, name in enumerate(names):
            rows.append(
                {
                    "instrument_id": name,
                    "bucket_id": bucket,
                    "model_score": bucket + (1 - offset) / 100,
                    "model_score_rank": len(rows) + 1,
                }
            )
    return pd.DataFrame(rows)


def test_policy_registry_is_exact_and_flags_are_unique() -> None:
    registry = turnctl.build_policy_registry()
    assert len(registry) == registry["policy_id"].nunique() == 75
    assert (registry["policy_role"] == "factorial").sum() == 72
    assert (registry["policy_role"] == "comparator").sum() == 3
    assert registry.loc[registry["primary_gate_eligible"], "policy_id"].tolist() == [turnctl.PRIMARY_POLICY_ID]
    assert registry.loc[registry["secondary_readout"], "policy_id"].tolist() == [turnctl.SECONDARY_POLICY_ID]
    assert "F_MIX333_XD8_R025_CNONE" in set(registry["policy_id"])
    assert "C_D8_ONLY_XD8_R100_CNONE" in set(registry["policy_id"])


def test_config_rejects_unknown_nested_key(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["execution"]["unregistered_override"] = True
    candidate = tmp_path / "config.yaml"
    candidate.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(turnctl.ContractError, match="config section execution keys mismatch"):
        turnctl.load_config(candidate)


def test_d7_incumbent_displaces_low_priority_d8_without_expanding_quota() -> None:
    assignment = _assignment()
    target = turnctl.form_hard_target(
        assignment,
        _policy(turnctl.PRIMARY_POLICY_ID),
        {"D7_OLD": 100.0, "D8_B": 100.0},
        {"D7_OLD": 0.01, "D8_B": 0.01},
    ).set_index("instrument_id")
    d8_sleeve = target.loc[target["sleeve_id"] == "D8"]
    assert len(d8_sleeve) == 34
    assert "D7_OLD" in d8_sleeve.index
    assert "D8_B" in d8_sleeve.index
    assert target.loc["D7_OLD", "buffer_eligible"]
    excluded_current_d8 = target.loc[(target["bucket_id"] == 8) & ~target["selected"]]
    assert len(excluded_current_d8) == 1
    assert not excluded_current_d8.iloc[0]["incumbent"]
    assert math.isclose(float(target["hard_target_weight"].sum()), 1.0)


def test_exit_floor_d8_has_no_buffer() -> None:
    target = turnctl.form_hard_target(
        _assignment(),
        _policy("F_MIX403030_XD8_R050_C040"),
        {"D7_OLD": 100.0},
        {"D7_OLD": 0.02},
    ).set_index("instrument_id")
    assert not target.loc["D7_OLD", "selected"]
    assert target.loc["D7_OLD", "exit_target"]
    assert len(target.loc[target["sleeve_id"] == "D8"]) == 34
    assert "D8_A" in set(target.loc[target["sleeve_id"] == "D8"].index)
    assert "D8_B" in set(target.loc[target["sleeve_id"] == "D8"].index)


def test_partial_rebalance_uses_cash_inclusive_one_way_cap() -> None:
    plan = turnctl.plan_partial_rebalance(
        {"A": 0.60, "B": 0.20},
        {"A": 0.20, "B": 0.60},
        rho=0.50,
        turnover_cap=0.10,
    )
    assert plan.planned_buy_before_cap == pytest.approx(0.20)
    assert plan.planned_sell_before_cap == pytest.approx(0.20)
    assert plan.cap_scale == pytest.approx(0.50)
    assert plan.planned_one_way_after_cap == pytest.approx(0.10)
    assert plan.execution_weights == pytest.approx({"A": 0.50, "B": 0.30})


def test_cash_launch_is_one_hundred_percent_not_half() -> None:
    plan = turnctl.plan_partial_rebalance({}, {"A": 0.40, "B": 0.60}, rho=0.25, turnover_cap=0.20, launch_month=True)
    assert plan.cap_scale == 1.0
    assert plan.planned_buy_after_cap == pytest.approx(1.0)
    assert plan.planned_one_way_after_cap == pytest.approx(1.0)


def test_admission_uses_realized_post_sell_slots_and_priority() -> None:
    state = pd.DataFrame(
        [
            {"instrument_id": "OLD", "hard_target_weight": 0.1, "sleeve_id": "D8", "model_score": 1.0},
            {"instrument_id": "NEW_D8", "hard_target_weight": 0.1, "sleeve_id": "D8", "model_score": 99.0},
            {"instrument_id": "NEW_D9", "hard_target_weight": 0.1, "sleeve_id": "D9", "model_score": 2.0},
            {"instrument_id": "NEW_D10", "hard_target_weight": 0.1, "sleeve_id": "D10", "model_score": 1.0},
        ]
    )
    admitted = turnctl.admit_new_entries(state, {"OLD": 10.0}, actual_holding_cap=2).set_index("instrument_id")
    assert admitted.loc["OLD", "entry_authorized"]
    assert admitted.loc["NEW_D10", "entry_authorized"]
    assert admitted.loc["NEW_D9", "entry_queue_status"] == "queued_no_realized_holding_slot"
    assert admitted.loc["NEW_D8", "entry_queue_status"] == "queued_no_realized_holding_slot"


def test_policy_summary_excludes_prelaunch_month_from_label_minimum() -> None:
    daily = pd.DataFrame(
        [
            {"policy_id": "P", "return_path": "reference_net", "trade_date": "2024-07-31", "NAV": 100.0, "marked_position_value": 0.0, "maximum_single_instrument_weight": 0.0, "actual_holding_n": 0},
            {"policy_id": "P", "return_path": "reference_net", "trade_date": "2024-08-01", "NAV": 100.0, "marked_position_value": 90.0, "maximum_single_instrument_weight": 0.02, "actual_holding_n": 45},
        ]
    )
    monthly = pd.DataFrame(
        [{"policy_id": "P", "return_path": "reference_net", "label_month": "2024-08", "monthly_return": 0.0, "event_month": False}]
    )
    turnover = pd.DataFrame(
        [{"policy_id": "P", "launch_month": False, "planned_stateful_one_way_turnover": 0.1, "realized_one_way_turnover": 0.1}]
    )
    summary = turnctl.build_policy_summary(monthly, daily, turnover).iloc[0]
    assert summary["minimum_label_month_average_invested_weight"] == pytest.approx(0.90)


def test_live_static_preflight_matches_sealed_inputs() -> None:
    config, _ = turnctl.load_config(CONFIG)
    audit, assignment = turnctl.run_static_preflight(config)
    assert audit["hash_match"].all()
    assert len(audit) == 15
    assert len(assignment) == 9300
    assert assignment["decision_date"].nunique() == 21
    assert assignment["instrument_id"].nunique() == 674


def test_cli_refuses_before_creating_output_or_scratch(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["authorization"]["historical_outcome_execution_authorized"] = False
    config["authorization"]["portfolio_replay_authorized"] = False
    configured_output = tmp_path / "locked_output"
    scratch_a = tmp_path / "locked_replay_a"
    config["paths"]["output_root"] = str(configured_output)
    config["paths"]["replay_a_scratch_root"] = str(scratch_a)
    locked_config = tmp_path / "locked_config.yaml"
    locked_config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    assert not configured_output.exists()
    assert not scratch_a.exists()
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--config", str(locked_config), "--output-root", str(configured_output), "--replay-id", "replay_a"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "formal historical replay is locked" in completed.stderr
    assert not configured_output.exists()
    assert not scratch_a.exists()
