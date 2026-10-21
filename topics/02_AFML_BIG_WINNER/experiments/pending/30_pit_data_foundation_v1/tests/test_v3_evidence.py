import pandas as pd
import pytest

from v3_evidence import (
    extract_status,
    named_dates,
    printed_security,
    retirement_codes,
    distribution_amounts,
)
from v3_bridge import entry_blockers, target_indices
from v3_rights import retired_link, ledger_value
from v3_financial import classify_report
from v3_parse_financial import parse_page, cover_report_year


def test_explicit_termination_does_not_mean_wealth_zero():
    events = extract_status(
        ["证券代码：600005 终止上市日期：2017年2月14日"], "股票终止上市公告"
    )
    assert events[0]["field"] == "listed" and events[0]["value"] is False
    assert events[0]["effective_date"] == "2017-02-14"
    assert "terminal_value" not in str(events)


def test_conflicting_dates_and_application_are_not_promoted():
    text = "终止上市日期：2020年1月3日。终止上市日期：2020年1月4日。"
    assert extract_status([text], "股票终止上市公告") == []
    assert extract_status([text], "申请终止上市公告") == []
    assert extract_status(["停牌日期：2020年1月3日"], "可转债停牌公告") == []
    assert (
        extract_status(["摘牌日期：2020年1月3日"], "关于参股公司股票终止上市暨摘牌公告")
        == []
    )


def test_termination_decision_never_removes_delisting_period_population():
    rows = extract_status(
        ["终止上市时间：2020年5月14日。公司股票进入退市整理期。"],
        "公司股票终止上市公告",
    )
    assert all(r["field"] != "listed" for r in rows)
    assert rows[0]["field"] == "termination_decision"
    rows = extract_status(
        ["终止上市日期：2020年5月14日", "公司股票将进入退市整理期。"],
        "公司股票终止上市公告",
    )
    assert all(r["field"] != "listed" for r in rows)
    rows = extract_status(
        ["终止上市决定日期：2022年5月24日。摘牌日期：2022年6月23日。"],
        "终止上市暨摘牌公告",
    )
    assert [r["effective_date"] for r in rows if r["field"] == "listed"] == [
        "2022-06-23"
    ]
    assert extract_status(["预计2020年7月21日摘牌"], "股票终止上市公告") == []


def test_intraday_halt_never_becomes_a_morning_halt():
    rows = extract_status(["停牌时间：2020年1月3日13:30"], "股票停牌公告")
    assert rows[0]["effective_date"] == "2020-01-03 13:30:00"
    rows = extract_status(["停牌日期：2020年1月3日"], "股票停牌公告")
    assert rows[0]["effective_date"] == "2020-01-03 23:59:59"


def test_remove_delisting_warning_does_not_remove_other_st():
    events = extract_status(
        ["撤销退市风险警示起始日：2020年1月3日"], "撤销退市风险警示公告"
    )
    assert events and events[0]["field"] == "delisting_risk_warning"
    assert all(r["field"] != "is_st" for r in events)


def test_payment_schedule_not_receipt_and_ambiguous_ab_dates_blocked():
    rows = named_dates(["现金红利发放日：2020年6月2日"])
    assert rows[0]["field"] == "scheduled_cash_payment_date"
    assert rows[0]["evidence_type"] == "CONTRACT_SCHEDULE_NOT_ACTUAL_RECEIPT"
    assert (
        named_dates(["现金红利发放日：2020年6月2日 B股现金红利发放日：2020年6月5日"])
        == []
    )


def test_original_dividend_gross_units_and_conflicts():
    rows = distribution_amounts(
        ["每10股派人民币现金0.30元（含税），扣税后每10股派0.27元。"]
    )
    assert rows[0]["value"] == "0.03"
    assert (
        distribution_amounts(
            ["每10股派现金1.00元（含税）。每10股派现金2.00元（含税）。"]
        )
        == []
    )
    rows = distribution_amounts(["每10股转增5股"])
    assert (
        rows[0]["value"] == "0.5"
        and rows[0]["field"] == "capitalization_shares_per_share"
    )


def test_issuer_and_retired_codes_fail_on_ambiguity():
    mapping = {"000001": {"a"}, "600000": {"b"}}
    assert printed_security(["证券代码：000001"], mapping) == "a"
    assert printed_security(["证券代码：000001 股票代码：600000"], mapping) is None
    assert retirement_codes(["股票转让代码：400220"])[0]["not_zero_terminal_wealth"]
    assert retirement_codes(["证券代码：400220 股票代码：400221"]) == []


def test_six_month_origin_anchor_and_positive_volume_cannot_open_fill():
    days = pd.bdate_range("2020-01-01", "2020-12-31")
    origins = pd.DatetimeIndex(["2020-01-31"])
    assert days[target_indices(days, origins, "6_calendar_months")[0]] == pd.Timestamp(
        "2020-07-31"
    )
    bars = pd.DataFrame(
        dict(date=days, open=10.0, volume=100000, can_buy=None, can_sell=None)
    )
    assert entry_blockers(days, origins, bars).tolist() == ["UNKNOWN_BUY_EXECUTION"]
    bars.loc[1, "can_buy"] = True
    with pytest.raises(ValueError, match="explicit execution"):
        entry_blockers(days, origins, bars)


def test_original_retired_mapping_requires_old_and_new_codes():
    p = ["上市公司阶段股票代码：002089 确权代码（即挂牌退市板块后的股票代码）：400209"]
    assert retired_link(p, {"002089": {"stable-id"}})[0]["security_id"] == "stable-id"
    assert (
        retired_link(
            [p[0].replace("确权代码", "确权证券代码")], {"002089": {"stable-id"}}
        )[0]["retired_code"]
        == "400209"
    )
    assert retired_link(["证券代码：400209"], {"002089": {"stable-id"}}) == []
    cross_page = [
        "一、股票终止上市的情况。终止上市股票种类：Ａ股 股票代码：300090",
        "二、确权证券代码：400089",
    ]
    assert retired_link(cross_page, {"300090": {"id"}})[0]["retired_code"] == "400089"
    assert (
        retired_link(
            cross_page + ["原股票代码：300091"], {"300090": {"id"}, "300091": {"other"}}
        )
        == []
    )


def test_rights_ledger_requires_delivery_receipt_fractional_policy_and_marks():
    e = dict(
        event_id="x",
        kind="share_exchange",
        effective_date="2017-02-14",
        record_date="2017-02-13",
        verified=True,
        source_sha256="evidence",
        new_shares_per_old_share="14/25",
        successor_instrument="SH600019",
    )
    assert (
        ledger_value(1, "2017-01-01", [e], {}, "total")["reason"]
        == "ACCOUNT_FRACTIONAL_SHARE_ALLOCATION_UNKNOWN"
    )
    assert (
        ledger_value(100, "2017-01-01", [e], {}, "total")["reason"]
        == "ACTUAL_SUCCESSOR_SHARE_DELIVERY_UNKNOWN"
    )
    e["actual_delivery_confirmed"] = True
    assert (
        ledger_value(100, "2017-01-01", [e], {}, "total")["reason"]
        == "MISSING_TERMINAL_EQUITY_MARK"
    )
    assert (
        ledger_value(100, "2017-01-01", [e], {"SH600019": 5}, "total")["value"] == 280
    )
    cash = dict(
        event_id="c",
        kind="cash_dividend",
        effective_date="2020-06-02",
        record_date="2020-06-01",
        verified=True,
        source_sha256="source",
        cash_per_share=1,
        scheduled_payment_date="2020-06-02",
    )
    assert (
        ledger_value(1, "2020-01-01", [cash], {"initial": 10}, "total")["receivable"]
        == 1
    )
    assert (
        ledger_value(1, "2020-01-01", [cash], {"initial": 10}, "executable", 0)[
            "reason"
        ]
        == "ACTUAL_CASH_RECEIPT_NOT_CONFIRMED"
    )
    assert ledger_value(1, "2020-01-01", [], {}, "total")["value"] is None


def test_financial_versions_keep_originals_amendments_and_periods_separate():
    assert classify_report("某公司:2022年年度报告(更新前)")["is_revision"] is False
    assert classify_report("某公司:2022年年度报告(更新后)")["is_revision"] is True
    assert (
        classify_report("关于2023年半年度报告的更正公告")["form"] == "amendment_notice"
    )
    assert classify_report("2023年半年度报告摘要")["form"] == "summary"
    assert classify_report("2023年半年度报告")["report_period"] == "2023-06-30"
    assert classify_report("关于2021年及2022年年度报告的更正公告") is None


def test_financial_table_requires_original_units_year_and_column_separation():
    text = "单位：元\n主要会计数据和财务指标\n2020年 2019年\n营业收入\n100.00 90.00\n"
    result = parse_page(text, 2020)
    assert result[0]["candidate_value"] == 100
    assert parse_page(text, 2019) == []
    assert parse_page(text.replace("单位：元", "单位：万元"), 2020) == []
    assert parse_page(text.replace("单位：元", ""), 2020) == []
    assert parse_page(text.replace("100.00 90.00", "100.0090.00"), 2020) == []
    current = text.replace("2020年 2019年", "本期 上年同期")
    assert parse_page(current, 2020) == []
    assert (
        parse_page(current, 2020, original_cover_year=2020)[0]["candidate_value"] == 100
    )
    assert cover_report_year(["2020\n公司名\n年度报告"]) == 2020
    assert cover_report_year(["2020\n年度报告", "2019年度报告"]) is None
