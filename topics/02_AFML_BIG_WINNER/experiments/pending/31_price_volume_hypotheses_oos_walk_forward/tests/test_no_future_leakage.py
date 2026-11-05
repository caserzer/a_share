import numpy as np
import pandas as pd
import pytest

from baselines import Transform
from volume_price_features import build_features
from walk_forward import predict_pair


def test_future_market_tampering_preserves_old_features(bars):
    original = build_features(bars, bars.date)
    changed = bars.copy()
    future = changed.index > 350
    for col in ["open", "high", "low", "close", "qfq_open", "qfq_high", "qfq_low", "qfq_close", "volume", "turnover_rate"]:
        changed.loc[future, col] *= 17
    new = build_features(changed, changed.date)
    pd.testing.assert_frame_equal(original.iloc[:351], new.iloc[:351])


def test_label_column_injection_is_ignored(bars):
    original = build_features(bars, bars.date)
    bars["winner_120"] = 999999
    bars["future_return"] = np.arange(len(bars))*100
    pd.testing.assert_frame_equal(original, build_features(bars, bars.date))


def test_preprocessing_ignores_test_distribution():
    train = pd.DataFrame({"x": np.arange(100, dtype=float)})
    transform = Transform().fit(train)
    frozen = transform.record()
    transform.apply(pd.DataFrame({"x": [1e99, -1e99, np.nan]}))
    assert frozen == transform.record()
    assert transform.high[0] < 100


def test_outer_prediction_rejects_labels():
    with pytest.raises(ValueError, match="outer labels"):
        predict_pair({}, pd.DataFrame({"value": [1]}), "H01")


def test_no_suspension_price_forward_fill(bars):
    days = bars.date.copy()
    bars = bars.drop(index=300)
    f = build_features(bars, days)
    assert not f.loc[300, "observed"]
    assert pd.isna(f.loc[301, "daily_log_return"])
