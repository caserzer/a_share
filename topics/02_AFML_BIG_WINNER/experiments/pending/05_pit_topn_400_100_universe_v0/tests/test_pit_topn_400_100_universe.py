from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
SPEC = importlib.util.spec_from_file_location(
    "pit_topn_400_100_pipeline", CODE_DIR / "pipeline.py"
)
assert SPEC and SPEC.loader
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)

TopNUniverseBlocked = pipeline.TopNUniverseBlocked
build_fixed_cap_overlap_audit = pipeline.build_fixed_cap_overlap_audit
build_yearly_summary = pipeline.build_yearly_summary
guard_candidate_source = pipeline.guard_candidate_source
next_trade_date_map = pipeline.next_trade_date_map
select_topn_membership = pipeline.select_topn_membership
shift_membership_to_executable = pipeline.shift_membership_to_executable
validate_outputs = pipeline.validate_outputs


def make_candidate() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "membership_date": ["2024-01-02"] * 5,
            "available_time": ["2024-01-02 close"] * 5,
            "membership_available_time": ["2024-01-02 close"] * 5,
            "usable_trade_date": ["2024-01-03"] * 5,
            "instrument": ["SH600003", "SH600001", "SH600002", "SZ300001", "SZ300002"],
            "ts_code": ["600003", "600001", "600002", "300001", "300002"],
            "board_bucket": ["main_board", "main_board", "main_board", "chinext", "chinext"],
            "is_listed": [True, True, True, True, True],
            "is_st": [False, False, False, False, False],
            "is_suspended": [False, False, False, False, False],
            "raw_unadjusted_close": [10.0, 10.0, 10.0, 20.0, 21.0],
            "total_share_asof": [30.0, 30.0, 20.0, 10.0, 10.0],
            "total_market_cap_cny": [300.0, 300.0, 200.0, 200.0, 210.0],
            "market_cap_source": ["raw_close_times_total_share_asof"] * 5,
            "price_source": ["raw_close"] * 5,
            "share_source": ["stock_zh_a_gbjg_em"] * 5,
            "status_source": ["daily_bar_presence"] * 5,
            "source_trade_date": ["2024-01-02"] * 5,
            "source_asof_date": ["2024-01-01"] * 5,
            "candidate_universe_source": ["full_board_candidate_panel"] * 5,
            "membership_rule_version": ["pit_topn_400_100_universe_v0"] * 5,
            "_observed_sessions_before_usable": [10, 300, 300, 300, 300],
        }
    )


def test_topn_sorting_is_deterministic_and_applies_bucket_quota() -> None:
    membership, quota = select_topn_membership(
        make_candidate(),
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )

    assert list(membership["instrument"]) == ["SH600001", "SH600003", "SZ300002"]
    assert membership.loc[membership["instrument"] == "SH600001", "board_rank_by_market_cap"].item() == 1
    assert membership.loc[membership["instrument"] == "SH600003", "board_rank_by_market_cap"].item() == 2
    assert membership.groupby("board_bucket")["instrument"].nunique().to_dict() == {
        "chinext": 1,
        "main_board": 2,
    }
    main = quota[quota["board_bucket"] == "main_board"].iloc[0]
    assert main["quota_fill_rate"] == 1.0


def test_pit_clock_shifts_to_next_trade_date_and_preserves_source() -> None:
    candidate = make_candidate()
    mapping = next_trade_date_map(["2024-01-02", "2024-01-03", "2024-01-04"])
    assert mapping["2024-01-02"] == "2024-01-03"
    membership, _ = select_topn_membership(
        candidate,
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )
    executable = shift_membership_to_executable(membership)

    assert set(executable["usable_trade_date"]) == {"2024-01-03"}
    assert set(executable["source_membership_date"]) == {"2024-01-02"}
    assert (
        pd.to_datetime(executable["source_membership_date"])
        < pd.to_datetime(executable["usable_trade_date"])
    ).all()


def test_eligibility_excludes_st_suspended_unlisted_and_missing_cap() -> None:
    candidate = make_candidate()
    candidate.loc[candidate["instrument"] == "SH600001", "is_st"] = True
    candidate.loc[candidate["instrument"] == "SH600002", "is_suspended"] = True
    candidate.loc[candidate["instrument"] == "SZ300001", "is_listed"] = False
    candidate.loc[candidate["instrument"] == "SZ300002", "total_market_cap_cny"] = pd.NA
    membership, _ = select_topn_membership(
        candidate,
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )

    assert list(membership["instrument"]) == ["SH600003"]


def test_latest_only_or_fixed_cap_ranking_source_is_rejected() -> None:
    candidate = make_candidate()
    candidate["candidate_universe_source"] = "fixed_cap_membership"
    with pytest.raises(TopNUniverseBlocked, match="full_board_candidate_panel"):
        guard_candidate_source(candidate)


def test_duplicate_executable_keys_are_rejected() -> None:
    membership, _ = select_topn_membership(
        make_candidate(),
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )
    duplicate = pd.concat([membership, membership.iloc[[0]]], ignore_index=True)
    with pytest.raises(TopNUniverseBlocked, match="duplicate executable key"):
        shift_membership_to_executable(duplicate)


def test_duplicate_membership_keys_and_latest_source_are_validation_failures() -> None:
    membership, _ = select_topn_membership(
        make_candidate(),
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )
    membership = pd.concat([membership, membership.iloc[[0]]], ignore_index=True)
    membership.loc[0, "market_cap_source"] = "latest_spot_market_cap"
    executable = membership.drop_duplicates(["usable_trade_date", "instrument"]).copy()
    executable["source_membership_date"] = executable["membership_date"]
    executable = executable.rename(columns={})
    gates = validate_outputs(
        membership=membership,
        executable=executable,
        gate_summary={
            "candidate_panel_source": "full_board_candidate_panel",
            "active_source_gap_count": 0,
        },
        validation={
            "max_total_daily_members": 500,
            "max_main_board_daily_members": 400,
            "max_chinext_daily_members": 100,
            "block_on_active_source_gaps": True,
            "disallowed_market_cap_sources": ["latest_spot_market_cap"],
        },
    )

    assert "duplicate_membership_key" in gates["validation_failures"]
    assert "disallowed_market_cap_source:latest_spot_market_cap" in gates["validation_failures"]


def test_overlap_audit_identity() -> None:
    topn = pd.DataFrame(
        {
            "membership_date": ["2024-01-02", "2024-01-02"],
            "instrument": ["SH600001", "SH600002"],
            "board_bucket": ["main_board", "main_board"],
        }
    )
    fixed = pd.DataFrame(
        {
            "membership_date": ["2024-01-02", "2024-01-02"],
            "instrument": ["SH600002", "SH600003"],
            "board_bucket": ["main_board", "main_board"],
        }
    )
    overlap, _ = build_fixed_cap_overlap_audit(topn, fixed)
    row = overlap.iloc[0]

    assert row["topn_count"] == row["intersection_count"] + row["topn_only_count"]
    assert row["fixed_cap_count"] == row["intersection_count"] + row["fixed_cap_only_count"]
    assert row["jaccard_overlap"] == pytest.approx(1 / 3)


def test_universe_years_252_uses_instrument_days_sum() -> None:
    daily = pd.DataFrame(
        {
            "membership_date": ["2024-01-02", "2024-01-03"],
            "usable_trade_date": ["2024-01-03", "2024-01-04"],
            "member_count": [10, 20],
            "main_board_count": [7, 15],
            "chinext_count": [3, 5],
        }
    )
    quota = pd.DataFrame(
        {
            "membership_date": ["2024-01-02", "2024-01-02"],
            "board_bucket": ["main_board", "chinext"],
            "quota_fill_rate": [0.5, 0.8],
        }
    )
    history = pd.DataFrame(
        {
            "year": [2024],
            "board_bucket": ["main_board"],
            "history_ready_240d_count": [15],
            "member_rows": [30],
        }
    )
    yearly = build_yearly_summary(daily, quota, history)

    assert yearly.loc[0, "instrument_days"] == 30
    assert yearly.loc[0, "universe_years_252"] == pytest.approx(30 / 252)


def test_history_readiness_diagnostic_does_not_filter_membership() -> None:
    membership, _ = select_topn_membership(
        make_candidate(),
        quotas={"main_board": 2, "chinext": 1},
        minimum_history_sessions=240,
        rank_rule_version="rank_v0",
    )
    early = membership[membership["instrument"] == "SH600003"].iloc[0]

    assert early["history_ready_240d_flag"] == False
    assert early["history_ready_missing_reason"] == "insufficient_history"
