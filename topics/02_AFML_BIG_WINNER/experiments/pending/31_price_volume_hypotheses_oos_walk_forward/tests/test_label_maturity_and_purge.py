import numpy as np
import pandas as pd
import pytest

from labels_and_maturity import infer_labels, future_variance
from volume_price_features import build_features
from walk_forward import training_mask, inner_splits


def test_unmatured_labels_never_train():
    f = pd.DataFrame(dict(date=pd.to_datetime(["2020-01-01"]*3),
                          mature_at=pd.to_datetime(["2020-03-01", "2021-01-01", None]), y=[1, 2, 3]))
    assert training_mask(f, "2021-01-01").tolist() == [True, False, False]


def test_cross_security_overlap_purged():
    f = pd.DataFrame(dict(date=pd.to_datetime(["2019-01-01", "2020-01-01", "2020-08-01"]),
                          mature_at=pd.to_datetime(["2020-08-01", "2020-06-01", "2020-09-01"]), y=[1., 2., 3.]))
    start, train, _ = next(inner_splits(f, "2021-01-01", "expanding"))
    assert start == pd.Timestamp("2020-07-01")
    assert train.y.tolist() == [2.]


def test_signal_close_enters_next_open(bars):
    origin = bars.date.iloc[300]
    f = infer_labels(bars, bars.date, [origin], 20)
    assert f.entry_date.iloc[0] == bars.date.iloc[301]
    assert f.exit_date.iloc[0] == bars.date.iloc[320]
    assert f.mature_at.iloc[0] == bars.date.iloc[320]+pd.Timedelta(hours=9, minutes=30)
    expected = bars.qfq_open.iloc[320]/bars.qfq_open.iloc[301]-1
    assert f.value.iloc[0] == pytest.approx(expected)


def test_censored_endpoints_not_zero_filled(bars):
    f = infer_labels(bars, bars.date, [bars.date.iloc[-3]], 120)
    assert f.status.iloc[0] == "CENSORED"
    assert pd.isna(f.value.iloc[0])


def test_delisting_terminal_remains_unknown(bars):
    f = infer_labels(bars, bars.date, [bars.date.iloc[300]], 60, bars.date.iloc[330])
    assert f.status.iloc[0] == "UNKNOWN"
    assert pd.isna(f.value.iloc[0])


def test_delayed_entry_is_not_backdated(bars):
    bars.loc[301:303, "volume"] = 0
    f = infer_labels(bars, bars.date, [bars.date.iloc[300]], 20)
    assert f.entry_date.iloc[0] == bars.date.iloc[304]
    assert f.entry_delay_sessions.iloc[0] == 3


def test_conflicting_open_cannot_yield_return(bars):
    bars.loc[301, "open_conflict"] = True
    f = infer_labels(bars, bars.date, [bars.date.iloc[300]], 20)
    assert pd.isna(f.value.iloc[0])


def test_rv_target_is_future_variance(bars):
    f = build_features(bars, bars.date)
    value, maturity = future_variance(f, bars.date, [bars.date.iloc[300]])
    assert value[0] == pytest.approx(f.daily_log_return.iloc[301:321].pow(2).mean())
    assert pd.Timestamp(maturity[0]) == bars.date.iloc[320]+pd.Timedelta(hours=15)


def test_rv_missing_path_stays_unknown(bars):
    days = bars.date.copy()
    f = build_features(bars.drop(index=310), days)
    value, _ = future_variance(f, days, [days.iloc[300]])
    assert np.isnan(value[0])
