from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


EXPERIMENT = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT / "src/run_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.py"
OUTPUT = EXPERIMENT / "outputs/20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_v0"
SPEC = importlib.util.spec_from_file_location("p4cap", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def signal_fixture() -> pd.DataFrame:
    rows = []
    for idx, instrument in enumerate(["B", "A", "C", "D", "E", "F"]):
        rows.append({
            "instrument_id": instrument,
            "decision_date": pd.Timestamp("2025-01-31"),
            "raw_signal": 10.0 if instrument in {"A", "B"} else float(6 - idx),
            "outcome_resolution": runner.UNKNOWN if instrument in {"C", "F"} else "valid_mark",
            "project_resolved_next_month_return": np.nan if instrument in {"C", "F"} else idx / 100.0,
        })
    return pd.DataFrame(rows)


def test_capacity_tie_break_is_instrument_ascending() -> None:
    assignment = runner.assign_capacity_membership(signal_fixture(), [2])
    top = assignment[assignment["membership_role"].eq("favorable_top_n")].sort_values("rank_desc")
    assert top["instrument_id"].tolist() == ["A", "B"]


def test_middle_unknown_does_not_invalidate_top() -> None:
    assignment = runner.assign_capacity_membership(signal_fixture(), [2])
    monthly = runner.build_monthly_returns(assignment, pd.DataFrame())
    row = monthly.iloc[0]
    assert row["top_evaluable"]
    assert row["middle_ignored_unknown_n"] == 1


def test_bottom_unknown_is_deleted_and_renormalized() -> None:
    assignment = runner.assign_capacity_membership(signal_fixture(), [2])
    bottom = assignment[assignment["membership_role"].eq("unfavorable_bottom_n")]
    assert bottom["outcome_resolution"].eq(runner.UNKNOWN).sum() == 1
    monthly = runner.build_monthly_returns(assignment, pd.DataFrame())
    row = monthly.iloc[0]
    assert row["bottom_deleted_unknown_n"] == 1
    assert row["bottom_effective_n"] == 1
    known = bottom.loc[~bottom["outcome_resolution"].eq(runner.UNKNOWN), "project_resolved_next_month_return"].iloc[0]
    assert row["bottom_comparator_return"] == pytest.approx(known)


def test_top_unknown_requires_deferred_exit() -> None:
    frame = signal_fixture()
    frame.loc[frame["instrument_id"].eq("A"), ["outcome_resolution", "project_resolved_next_month_return"]] = [runner.UNKNOWN, np.nan]
    assignment = runner.assign_capacity_membership(frame, [2])
    unresolved = runner.build_monthly_returns(assignment, pd.DataFrame())
    assert not unresolved.iloc[0]["top_evaluable"]
    deferred = pd.DataFrame([{
        "instrument_id": "A",
        "decision_date": pd.Timestamp("2025-01-31"),
        "deferred_gross_return": 0.20,
        "holding_calendar_days": 35,
        "deferred_resolution": "resolved_first_mark_in_t_plus_2",
    }])
    resolved = runner.build_monthly_returns(assignment, deferred)
    assert resolved.iloc[0]["top_evaluable"]
    assert resolved.iloc[0]["top_deferred_exit_n"] == 1


def test_deferred_exit_uses_first_mark_in_t_plus_2() -> None:
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-31", "2025-02-20", "2025-03-05", "2025-03-07"]),
        "close": [10.0, 11.0, 12.0, 13.0],
    })
    result = runner.resolve_deferred_exit_from_prices("X", pd.Timestamp("2025-01-31"), prices)
    assert result["forced_exit_date"] == pd.Timestamp("2025-03-05")
    assert result["deferred_gross_return"] == pytest.approx(0.20)


def test_deferred_exit_without_t_plus_2_mark_fails_closed() -> None:
    prices = pd.DataFrame({"date": pd.to_datetime(["2025-01-31", "2025-02-20"]), "close": [10.0, 11.0]})
    result = runner.resolve_deferred_exit_from_prices("X", pd.Timestamp("2025-01-31"), prices)
    assert result["deferred_resolution"] == "deferred_exit_unresolved"
    assert result["failure_reason"] == "no_mark_in_t_plus_2_natural_month"


def test_frozen_capacity_set_in_config() -> None:
    config_path = EXPERIMENT / "configs/config_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.yaml"
    config = __import__("yaml").safe_load(config_path.read_text(encoding="utf-8"))
    assert config["sorting"]["bucket_capacity_n"] == [5, 10, 20, 30, 40, 50]
    assert config["sorting"]["primary_weighting"] == "EW"


def test_n10_paired_delta_is_zero() -> None:
    monthly = pd.DataFrame({
        "decision_date": pd.to_datetime(["2025-01-31", "2025-02-28"] * 2),
        "bucket_capacity_n": [5, 5, 10, 10],
        "top_cohort_return": [0.1, 0.2, 0.1, 0.2],
        "top_minus_bottom_spread": [0.2, 0.3, 0.2, 0.3],
    })
    result = runner.paired_delta_vs_10(monthly)
    n10 = result[result["bucket_capacity_n"].eq(10)].iloc[0]
    assert n10["top_delta_mean"] == pytest.approx(0.0)
    assert n10["spread_delta_mean"] == pytest.approx(0.0)


def test_output_manifest_hashes_when_materialized() -> None:
    if not OUTPUT.exists():
        pytest.skip("run output has not been materialized")
    hashes = json.loads((OUTPUT / "output_hashes_20b_p4_capacity.json").read_text(encoding="utf-8"))
    for relative, expected in hashes.items():
        assert runner.sha256_file(OUTPUT / relative) == expected
