import numpy as np
import pandas as pd
import pytest
from labels import LabelBuilder, missing_price_reason
from pit import Calendar


@pytest.fixture
def data():
    dates = pd.bdate_range(
        "2023-01-02", periods=180
    )  # synthetic, not a real exchange calendar
    f = pd.DataFrame(
        dict(
            date=dates,
            security_id="s",
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.0,
            can_buy=True,
            can_sell=True,
        )
    )
    coverage = pd.DataFrame(
        [
            dict(
                security_id="s",
                start=dates[0],
                end=dates[-1],
                complete=True,
                source_sha256="fixture",
            )
        ]
    )
    return dates, f, coverage


def build(data, actions=None, coverage=True):
    d, f, c = data
    return LabelBuilder(Calendar(d), f, actions, c if coverage else None)


def test_next_open_not_same_close_and_strict_threshold(data):
    d, f, c = data
    f.loc[0, "open"] = 1
    f.loc[20, "open"] = 8
    r = build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
    assert (
        r.status == "KNOWN"
        and r.entry == str(d[1].date())
        and r.exit == str(d[20].date())
    )
    assert r.value == pytest.approx(-0.2) and r.loss_below_minus20 is False
    f.loc[20, "open"] = 7.99
    assert (
        build(data)
        .build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
        .loss_below_minus20
        is True
    )


def test_limit_suspension_and_delay(data):
    d, f, c = data
    f.loc[1:2, "can_buy"] = False
    f.loc[20:21, "can_sell"] = False
    r = build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
    assert r.entry == str(d[3].date()) and r.exit == str(d[22].date())


def test_unknown_execution_not_skipped(data):
    d, f, c = data
    f["can_buy"] = f.can_buy.astype("boolean")
    f.loc[1, "can_buy"] = None
    assert (
        build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price").reason
        == "UNKNOWN_BUY_EXECUTION"
    )


def test_unmatured_labels_never_available(data):
    d, _, _ = data
    b = build(data)
    r = b.build_labels(
        "s",
        str(d[0].date()) + " 15:00",
        60,
        "total",
        asof_time=str(d[30].date()) + " 15:00",
    )
    assert r.status == "CENSORED" and r.value is None
    assert b.build_labels("s", str(d[150].date()) + " 15:00", 120).status == "CENSORED"


def test_intraday_does_not_see_future_exit_open(data):
    d, _, _ = data
    r = build(data).build_labels(
        "s",
        str(d[0].date()) + " 15:00",
        20,
        "price",
        asof_time=str(d[20].date()) + " 08:00",
    )
    assert r.value is None


def test_price_not_total_and_unknown_cash_ledger(data):
    d, _, _ = data
    assert (
        build(data, coverage=False)
        .build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
        .status
        == "KNOWN"
    )
    r = build(data, coverage=False).build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "total"
    )
    assert r.value is None and r.reason == "INCOMPLETE_ACTION_AND_SETTLEMENT_LEDGER"


def dividend(data, pay=None):
    d, _, _ = data
    return pd.DataFrame(
        [
            dict(
                security_id="s",
                kind="cash_dividend",
                effective_date=d[10],
                record_date=d[9],
                payment_date=pay if pay is not None else d[11],
                cash_per_share=1.0,
                share_multiplier=None,
                verified=True,
                source_sha256="fixture",
            )
        ]
    )


def test_cash_dividend_not_adjusted_price_shortcut(data):
    d, f, c = data
    f.loc[10:, "open"] = 9
    f.loc[10:, "close"] = 9
    a = dividend(data)
    b = build(data, a)
    r = b.build_labels("s", str(d[0].date()) + " 15:00", 20, "total")
    assert r.value == pytest.approx(0)
    assert b.build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "price"
    ).value == pytest.approx(-0.1)
    assert b.build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "executable", cost_bps=10
    ).value == pytest.approx(-0.001)


def test_unpaid_cash_not_executable_at_exit(data):
    d, _, _ = data
    b = build(data, dividend(data, pay=d[30]))
    assert b.build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "total"
    ).value == pytest.approx(0.1)
    r = b.build_labels(
        "s",
        str(d[0].date()) + " 15:00",
        20,
        "executable",
        cost_bps=0,
        asof_time=str(d[20].date()) + " 15:00",
    )
    assert (
        r.value is None
        and r.status == "CENSORED"
        and r.reason == "CASH_SETTLEMENT_NOT_OBSERVED"
    )
    paid = b.build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "executable", cost_bps=0
    )
    assert paid.value == pytest.approx(0.1)
    assert pd.Timestamp(paid.mature_at).date() == d[30].date()


def test_split_and_complex_rights(data):
    d, f, c = data
    f.loc[10:, "open"] = 5
    f.loc[10:, "close"] = 5
    a = dividend(data)
    a["kind"] = "split"
    a["share_multiplier"] = 2
    a["payment_date"] = d[10]
    assert build(data, a).build_labels(
        "s", str(d[0].date()) + " 15:00", 20, "total"
    ).value == pytest.approx(0)
    a["kind"] = "rights_issue"
    assert (
        build(data, a).build_labels("s", str(d[0].date()) + " 15:00", 20, "total").value
        is None
    )


def test_delist_terminal_never_default_total_loss(data):
    d, f, c = data
    f.loc[10:, "can_sell"] = False
    r = build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "total")
    assert r.status == "UNKNOWN" and r.value is None and "TERMINAL" in r.reason


def test_source_gap_and_complete_path(data):
    d, f, c = data
    f.loc[8, "close"] = np.nan
    r = build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
    assert r.value is None and r.reason == "INCOMPLETE_MFE_MAE_PRICE_PATH"
    f["missing_reason"] = None
    f.loc[8, "missing_reason"] = "SUSPENDED"
    assert (
        build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price").status
        == "KNOWN"
    )


def test_six_calendar_months_not_120_sessions(data):
    d, _, _ = data
    b = build(data)
    o = str(d[0].date()) + " 15:00"
    r = b.build_labels("s", o, "6_calendar_months", "price")
    assert pd.Timestamp(r.target) >= d[0] + pd.DateOffset(months=6)
    assert r.target != b.build_labels("s", o, 120, "price").target


@pytest.mark.parametrize(
    "date,delist,suspended,failed,expected",
    [
        ("2016-01-01", None, None, False, "NOT_LISTED"),
        ("2024-01-01", "2023-01-01", None, False, "DELISTED"),
        ("2020-01-01", None, True, False, "SUSPENDED"),
        ("2020-01-01", None, None, True, "SOURCE_FAILURE"),
        ("2020-01-01", None, None, False, "UNKNOWN"),
    ],
)
def test_missing_classification(date, delist, suspended, failed, expected):
    assert (
        missing_price_reason(date, "2017-01-01", delist, suspended, failed) == expected
    )


def test_decimal_loss_boundary_not_float_artifact(data):
    d, f, _ = data
    f["open"] = 0.1
    f["close"] = 0.1
    f.loc[20, "open"] = 0.08
    r = build(data).build_labels("s", str(d[0].date()) + " 15:00", 20, "price")
    assert r.value == -0.2 and r.loss_below_minus20 is False
