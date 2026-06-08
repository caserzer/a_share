from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from pipeline import (  # noqa: E402
    SourceAuditRow,
    _audit_historical_st_category,
    board_bucket,
    blocking_audit_issues,
    build_qlib_daily,
    count_dated_st_name_change_rows,
    has_any_st_name_marker,
    compress_executable_intervals,
    expand_share_asof,
    normalize_daily_bars,
    normalize_share_history,
    shift_membership_to_executable,
    suspension_sample_matches_requested_date,
)


def test_board_bucket_classification() -> None:
    assert board_bucket("600519") == "main_board"
    assert board_bucket("SZ000001") == "main_board"
    assert board_bucket("300750.SZ") == "chinext"
    assert board_bucket("688001") is None
    assert board_bucket("430001") is None


def test_normalize_daily_bars_and_build_qlib_daily() -> None:
    raw_source = pd.DataFrame(
        {
            "日期": ["2024-05-06", "2024-05-07"],
            "开盘": [10.0, 10.5],
            "最高": [11.0, 11.5],
            "最低": [9.5, 10.0],
            "收盘": [10.0, 11.0],
            "成交量": [10, 20],
            "成交额": [1000.0, 2200.0],
            "换手率": [1.5, 2.0],
        }
    )
    qfq_source = raw_source.copy()
    qfq_source["开盘"] = [11.0, 11.55]
    qfq_source["最高"] = [12.1, 12.65]
    qfq_source["最低"] = [10.45, 11.0]
    qfq_source["收盘"] = [11.0, 12.1]

    raw = normalize_daily_bars(
        raw_source,
        instrument="600519",
        source_function="stock_zh_a_hist",
        volume_unit="hands",
        turnover_unit="percent",
    )
    qfq = normalize_daily_bars(
        qfq_source,
        instrument="600519",
        source_function="stock_zh_a_hist",
        volume_unit="hands",
        turnover_unit="percent",
    )
    qlib = build_qlib_daily(raw, qfq)

    assert list(qlib["date"]) == ["2024-05-06", "2024-05-07"]
    assert qlib.loc[0, "volume"] == 1000.0
    assert qlib.loc[0, "money"] == 1000.0
    assert qlib.loc[0, "turnover_rate"] == pytest.approx(0.015)
    assert qlib.loc[0, "factor"] == pytest.approx(1.1)
    assert qlib.loc[0, "raw_close"] == 10.0


def test_expand_share_asof_uses_latest_prior_share_change() -> None:
    source = pd.DataFrame(
        {
            "变更日期": ["2020-01-01", "2020-01-03"],
            "总股本": ["100", "200"],
            "已上市流通A股": ["90", "180"],
        }
    )
    shares = normalize_share_history(source, source_function="stock_zh_a_gbjg_em")
    expanded = expand_share_asof(shares, ["2020-01-01", "2020-01-02", "2020-01-03"])

    assert list(expanded["total_share_asof"]) == [100, 100, 200]
    assert list(expanded["share_source_date"]) == [
        "2020-01-01",
        "2020-01-01",
        "2020-01-03",
    ]


def test_shift_membership_and_compress_reentry_intervals() -> None:
    calendar = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05"]
    raw = pd.DataFrame(
        {
            "membership_date": ["2020-01-01", "2020-01-02", "2020-01-04"],
            "instrument": ["SH600519", "SH600519", "SH600519"],
        }
    )

    executable = shift_membership_to_executable(raw, calendar)
    assert list(executable["usable_trade_date"]) == [
        "2020-01-02",
        "2020-01-03",
        "2020-01-05",
    ]

    intervals = compress_executable_intervals(executable, calendar)
    assert intervals.to_dict("records") == [
        {
            "instrument": "SH600519",
            "start_datetime": "2020-01-02",
            "end_datetime": "2020-01-03",
            "session_count": 2,
        },
        {
            "instrument": "SH600519",
            "start_datetime": "2020-01-05",
            "end_datetime": "2020-01-05",
            "session_count": 1,
        },
    ]


def test_suspension_source_rejects_latest_only_sample() -> None:
    sample = pd.DataFrame(
        {
            "代码": ["600608"],
            "停牌时间": ["2026-06-08"],
            "停牌截止时间": ["2026-06-08"],
        }
    )

    assert not suspension_sample_matches_requested_date(sample, "2024-05-06")


def test_dated_st_name_change_counter() -> None:
    sample = pd.DataFrame(
        {
            "变更日期": ["2020-01-01", "2020-01-02", None],
            "证券简称": ["ST星源", "平安银行", "*ST国华"],
            "变更前简称": ["深星源A", "平安银行", "国华"],
            "变更后简称": ["ST星源", "平安银行", "*ST国华"],
        }
    )

    assert count_dated_st_name_change_rows(sample) == 1
    assert has_any_st_name_marker(pd.DataFrame({"name": ["G浦发", "*ST沪科"]}))


def test_historical_st_audit_invokes_sources_without_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAk:
        def stock_info_sz_change_name(self, symbol: str) -> pd.DataFrame:
            assert symbol == "简称变更"
            assert os.environ.get("HTTP_PROXY") is None
            return pd.DataFrame(
                {
                    "变更日期": ["2020-01-01"],
                    "证券代码": ["000005"],
                    "证券简称": ["ST星源"],
                    "变更前简称": ["深星源A"],
                    "变更后简称": ["ST星源"],
                }
            )

        def stock_info_change_name(self, symbol: str) -> pd.DataFrame:
            assert os.environ.get("HTTP_PROXY") is None
            if symbol == "600519":
                return pd.DataFrame({"index": [1, 2], "name": ["G茅台", "贵州茅台"]})
            assert symbol == "600003"
            return pd.DataFrame({"index": [1, 2, 3], "name": ["S东北高", "东北高速", "ST东北高"]})

        def stock_zh_a_st_em(self) -> pd.DataFrame:
            assert os.environ.get("HTTP_PROXY") is None
            return pd.DataFrame({"代码": ["000005"], "名称": ["ST星源"]})

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9999")
    row = _audit_historical_st_category(
        FakeAk(),
        sample_symbol="600519",
        live=True,
        retry_without_proxy=True,
    )

    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:9999"
    assert row.support_state == "supported"
    assert row.fallback_state == "supported_with_sh_lifetime_st_exclusion"
    assert "1 dated Shenzhen ST-name-change rows" in row.notes


def test_not_evaluated_audit_rows_only_block_full_runs() -> None:
    rows = [
        SourceAuditRow(
            category="historical_st_status",
            support_state="not_evaluated",
            function_name="stock_info_change_name",
        )
    ]

    assert blocking_audit_issues(rows, require_evaluated=False) == []
    assert blocking_audit_issues(rows, require_evaluated=True) == rows
