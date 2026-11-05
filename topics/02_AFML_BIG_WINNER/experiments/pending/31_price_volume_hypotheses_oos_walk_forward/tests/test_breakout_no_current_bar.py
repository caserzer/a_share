import numpy as np

from episode_builder import cooling_mask, observation_masks
from volume_price_features import build_features


def test_breakout_excludes_current_close(bars):
    bars.loc[300, "qfq_close"] = bars.qfq_close.iloc[180:300].max()*1.1
    f = build_features(bars, bars.date)
    assert f.breakout.iloc[300]
    assert f.breakthrough_strength.iloc[300] > 0.09


def test_episode_cooling_does_not_use_future_events():
    a = np.ones(65, bool)
    selected = cooling_mask(a)
    assert np.flatnonzero(selected).tolist() == [0, 20, 40, 60]
    np.testing.assert_array_equal(selected[:31], cooling_mask(a[:31]))


def test_incomplete_week_never_called_week_end(bars):
    bars = bars.iloc[:302]
    f = build_features(bars, bars.date)
    mask = observation_masks(f, np.ones(len(f), bool))["weekly"]
    if bars.date.iloc[-1].dayofweek < 4:
        assert not mask[-1]


def test_future_listing_cannot_enter_cohort(bars):
    f = build_features(bars, bars.date)
    eligible = bars.date.ge(bars.date.iloc[400]).to_numpy()
    masks = observation_masks(f, eligible)
    assert not any(np.asarray(m)[:400].any() for m in masks.values())


def test_st_is_contemporaneous_no_lifetime_exclusion(bars):
    bars.loc[500:, "vendor_is_st"] = "1"
    f = build_features(bars, bars.date)
    assert f.vendor_st.iloc[300] == 0
    assert f.observed.iloc[300]
