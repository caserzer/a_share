import numpy as np
import pandas as pd
import pytest
from issuer_calibration import add_buckets, peer_probabilities, estimate, calibrate_weights, score
from run_direct_probability import weighted_stats


def fixture():
    dates = pd.to_datetime(['2020-01-31']*12+['2020-02-28']*12)
    return add_buckets(pd.DataFrame(dict(date=dates, instrument=[f'S{i}' for i in range(12)]*2,
        vol63=.2, log_cap=20., y_1=[.1]*6+[-.1]*6+[.1]*12,
        end_1=pd.to_datetime(['2020-03-01']*12+['2020-04-01']*12))))


def test_peer_excludes_own_outcome_and_has_expected_counts():
    d, o, e, fallback = peer_probabilities(fixture().iloc[:12], 1, 'sign')
    assert not fallback.any()
    np.testing.assert_allclose(e[0], [6/11, 5/11])
    changed = fixture().iloc[:12].copy(); changed.loc[0, 'y_1'] = -.1
    _, _, after, _ = peer_probabilities(changed, 1, 'sign')
    np.testing.assert_array_equal(e[0], after[0])


def test_small_bucket_falls_back_to_same_month_and_zero_excluded():
    d = fixture().iloc[:12].copy(); d.loc[0, 'vol63_bucket'] = -1; d.loc[1, 'y_1'] = 0
    rows, o, e, fallback = peer_probabilities(d, 1, 'sign')
    assert len(rows) == 11 and fallback[0]
    np.testing.assert_allclose(e[0], [6/10, 4/10])


def test_future_labels_and_unknown_issuer_cannot_enter_calibration():
    p = fixture(); date = pd.Timestamp('2020-03-15'); instruments = ['S0', 'NEW']
    f, n, info = estimate(p, 1, date, instruments, 'bins')
    assert n.tolist() == [1, 0] and info['training_rows'] == 12
    np.testing.assert_array_equal(f[1], np.ones(7))
    p.loc[p.end_1.ge(date), 'y_1'] = -100
    f2, n2, _ = estimate(p, 1, date, instruments, 'bins')
    np.testing.assert_array_equal(f, f2); np.testing.assert_array_equal(n, n2)
    prefix = p[p.date.lt('2020-02-01')]
    np.testing.assert_array_equal(f, estimate(prefix, 1, date, instruments, 'bins')[0])


def test_sign_preserves_zero_mass_and_exact_identity():
    a = np.tile([-.3, -.1, 0, .1, .3], (2, 1)); w = np.full_like(a, .2)
    factors = np.array([[.5, 2], [1, 1]])
    adjusted = calibrate_weights(a, w, factors, 'sign')
    np.testing.assert_array_equal(adjusted[:, 2], w[:, 2])
    prior = weighted_stats(a, w, [.2, np.nan]); prior['actual'] = [.2, np.nan]
    result = score(prior, a, w, factors, np.array([5, 0]), 'sign')
    assert result.loc[0, 'p_up'] == pytest.approx(.64)
    pd.testing.assert_series_equal(result.iloc[1], prior[result.columns].iloc[1])
    allzero = np.zeros((1, 3)); zw = np.full((1, 3), 1/3)
    np.testing.assert_array_equal(calibrate_weights(allzero, zw, factors[:1], 'sign'), zw)


def test_full_bins_normalizes_and_buckets_ignore_future_dates():
    a = np.array([[-.3, -.1, -.01, 0, .01, .1, .3]])
    w = np.full((1, 7), 1/7); f = np.array([[1, 1, 1, 1, 1, 1, 2]])
    np.testing.assert_allclose(calibrate_weights(a, w, f, 'bins'), f/8)
    p = fixture().drop(columns=['vol63_bucket', 'log_cap_bucket'])
    full = add_buckets(p); prefix = add_buckets(p.iloc[:12])
    pd.testing.assert_frame_equal(full.iloc[:12], prefix)
    with pytest.raises(ValueError): add_buckets(pd.concat([p, p.iloc[:1]]))
