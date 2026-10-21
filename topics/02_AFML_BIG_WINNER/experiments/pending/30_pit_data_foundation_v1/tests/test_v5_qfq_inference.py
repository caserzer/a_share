import json

import numpy as np
import pandas as pd
import pytest

from v5_factors import apply_factors, parse_factors
from v5_labels import infer_labels
from v5_prices import build_security, compatible_scale
from v5_dataset import D2PriceInferenceDataset


def factors(dates=("1900-01-01", "2026-01-06"), values=(2.0, 1.0)):
    return pd.DataFrame(dict(date=pd.to_datetime(dates), qfq_divisor=values))


def bars():
    dates = pd.bdate_range("2026-01-01", periods=30)
    f = pd.DataFrame(dict(date=dates, open=100.0, high=101.0, low=99.0, close=100.0,
                          volume=1000.0, open_conflict=False, close_conflict=False,
                          factor_chain_id="same", factor_source_sha256="a"*64))
    f.loc[f.date.ge("2026-01-06"), ["open", "high", "low", "close"]] /= 2
    f = apply_factors(f, factors())
    return f


def test_parse_one_json_assignment_with_optional_comment_no_execution():
    obj = {"total": 2, "data": [{"d": "2026-01-06", "f": "1"}, {"d": "1900-01-01", "f": "2"}]}
    body = ("var sh600000qfq="+json.dumps(obj)+";\n/* opaque checksum */").encode()
    assert parse_factors(body, "SH600000").qfq_divisor.tolist() == [2, 1]
    with pytest.raises(ValueError):
        parse_factors(body.replace(b"sh600000", b"sz000001"), "SH600000")
    with pytest.raises(ValueError):
        parse_factors(body + b";alert(1)", "SH600000")


@pytest.mark.parametrize("values", [(0, 1), (-1, 1), (np.nan, 1)])
def test_nonpositive_or_nonfinite_factor_rejected(values):
    obj = {"total": 2, "data": [{"d": d, "f": v} for d, v in zip(["1900-01-01", "2026-01-06"], values)]}
    with pytest.raises(ValueError):
        parse_factors(("var sh600000qfq="+json.dumps(obj)).encode(), "SH600000")


def test_factor_is_backward_effective_and_never_backfilled():
    b = bars()[["date", "open", "high", "low", "close"]]
    a = apply_factors(b, factors(("2026-01-06",), (1.0,)))
    assert a.loc[a.date.lt("2026-01-06"), "qfq_open"].isna().all()
    assert a.loc[a.date.ge("2026-01-06"), "qfq_open"].notna().all()


def test_qfq_removes_mechanical_split_and_keeps_raw_comparison():
    b = bars()
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.status == "KNOWN_INFERRED"
    assert row.value == 0
    assert row.raw_price_return == -0.5
    assert not row.loss_below_minus20
    assert row.mfe == 0 and row.mae == 0


def test_future_global_factor_rescaling_does_not_change_return_or_path():
    b = bars()
    a = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    for c in ["qfq_open", "qfq_close"]:
        b[c] /= 1.73
    r = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert r.value == pytest.approx(a.value)
    assert r.mfe == pytest.approx(a.mfe) and r.mae == pytest.approx(a.mae)


def test_observed_open_is_inferred_without_execution_flags_and_skips_zero_volume():
    b = bars()
    b["can_buy"] = b["can_sell"] = None
    b.loc[1, "volume"] = 0
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.entry_date == b.date.iloc[2]
    assert row.entry_delay_sessions == 1
    assert row.status == "KNOWN_INFERRED"


def test_first_trade_with_missing_factor_is_unknown_not_later_cherry_picked():
    b = bars()
    b.loc[1, "qfq_open"] = np.nan
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.entry_date == b.date.iloc[1]
    assert row.reason == "MISSING_QFQ_ENDPOINT_FACTOR" and np.isnan(row.value)
    assert row.raw_price_return == -0.5


def test_unmatured_labels_are_censored_and_delisting_is_not_zero_or_stale_fill():
    b = bars()
    row = infer_labels(b, b.date, [b.date.iloc[25]], "20_sessions").iloc[0]
    assert row.status == "CENSORED" and np.isnan(row.value)
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions", b.date.iloc[10]).iloc[0]
    assert row.reason == "DELISTING_TERMINAL_VALUE_UNOBSERVED" and np.isnan(row.value)


def test_endpoint_conflict_not_cherry_picked_and_missing_path_does_not_erase_endpoint_return():
    b = bars()
    b.loc[20, "open_conflict"] = True
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.reason == "UNRESOLVED_ENDPOINT_OPEN_CONFLICT" and np.isnan(row.value)
    b.loc[20, "open_conflict"] = False
    b.loc[5, "qfq_close"] = np.nan
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.status == "KNOWN_INFERRED" and row.value == 0
    assert row.path_missing_sessions == 1 and np.isnan(row.mfe)


def test_exit_day_close_is_after_exit_and_must_not_enter_mfe():
    b = bars()
    b.loc[20, "qfq_close"] = 100000
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.mfe == 0


def test_code_change_requires_entire_shared_step_curve_not_one_anchor():
    a = factors()
    b = a.copy()
    b.qfq_divisor *= 3
    assert compatible_scale(a, b, "2026-01-01", "2026-01-30") == pytest.approx(1/3)
    b.loc[0, "qfq_divisor"] *= 1.2
    assert compatible_scale(a, b, "2026-01-01", "2026-01-30") is None


def test_unmatched_code_factor_chains_block_cross_code_return():
    b = bars()
    b.loc[20:, "factor_chain_id"] = "different"
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.reason == "UNRECONCILED_CODE_CHANGE_FACTOR_SCALE" and np.isnan(row.value)


def test_entry_after_horizon_is_not_a_shorter_known_label():
    b = bars()
    b.loc[:20, "volume"] = 0
    row = infer_labels(b, b.date, [b.date.iloc[0]], "20_sessions").iloc[0]
    assert row.reason == "ENTRY_NOT_BEFORE_TARGET" and np.isnan(row.value)


def test_empty_source_partition_remains_missing_with_valid_schema():
    b = bars().iloc[:0].drop(columns=["qfq_open", "qfq_close", "qfq_high", "qfq_low", "qfq_divisor", "factor_effective_date"])
    out, links = build_security(b, "SH600000", pd.DataFrame())
    assert out.empty and not links and "qfq_open" in out and "factor_chain_id" in out
    row = infer_labels(out, pd.bdate_range("2026-01-01", periods=30), ["2026-01-01"], "20_sessions").iloc[0]
    assert row.status == "UNKNOWN" and np.isnan(row.value)


def test_asof_reader_hides_future_raw_comparator_even_when_qfq_factor_is_unknown():
    obj = D2PriceInferenceDataset.__new__(D2PriceInferenceDataset)
    obj._sid = lambda security: "sid"
    obj._read = lambda name: pd.DataFrame([dict(security_id="sid", date=pd.Timestamp("2026-01-30"),
        target_session=pd.Timestamp("2026-03-02"), entry_date=pd.Timestamp("2026-02-02"), exit_date=pd.Timestamp("2026-03-02"),
        status="UNKNOWN", value=np.nan, raw_price_return=0.99, mature_at=pd.NaT)])
    row = obj.build_labels("SH600000", "2026-01-30", 20, asof_time="2026-02-01 15:00+08:00")
    assert row["status"] == "CENSORED" and row["value"] is None
    assert "raw_price_return" not in row and "exit_date" not in row


def test_qfq_path_reader_uses_qfq_in_standard_ohlc_and_explicit_raw_comparator():
    obj = D2PriceInferenceDataset.__new__(D2PriceInferenceDataset)
    obj._sid = lambda security: "sid"
    obj._read = lambda name: bars()
    f = obj.price_and_corporate_action_path("SH600000", "2026-01-01", "2026-01-30")
    assert f.open.eq(f.qfq_open).all() and f.close.eq(f.qfq_close).all()
    assert f.iloc[0].raw_open == 100 and f.iloc[0].open == 50
    assert f.attrs["standard_ohlc_basis"] == "qfq"
