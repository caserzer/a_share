import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from run_distribution_shape_models import ALPHAS, GRID, risk_scale, training_target, quantile_atoms
from run_direct_probability import weighted_stats


def test_log_risk_transform_round_trip_and_known_scale_only():
    y = np.array([-.7, -.05, 0., .3, 2.])
    s = risk_scale([.01, .02, 0., .03, .05], 6)
    np.testing.assert_allclose(np.expm1(training_target(y, s)*s), y, atol=1e-14)
    np.testing.assert_allclose(s[2], .001*np.sqrt(126/252))
    with pytest.raises(ValueError): risk_scale([np.nan], 6)
    with pytest.raises(ValueError): training_target([-1.])


def test_annualized_input_has_correct_horizon_units():
    # Independent units: 12 calendar months approximate 252 trading days.
    np.testing.assert_allclose(risk_scale([.2], 12), [.2])
    np.testing.assert_allclose(risk_scale([.2], 3), [.1])
    daily_vol = .01
    np.testing.assert_allclose(risk_scale([daily_vol*np.sqrt(252)], 1), [daily_vol*np.sqrt(21)])


def test_quantile_rearrangement_and_constant_endpoint_tails():
    raw = (2*ALPHAS-1)[None, ::-1]
    a, w = quantile_atoms(raw)
    expected = np.interp(GRID, ALPHAS, 2*ALPHAS-1)
    np.testing.assert_allclose(a[0], expected)
    np.testing.assert_allclose(w.sum(axis=1), 1)
    assert a[0, 0] == -.96 and a[0, -1] == .96
    np.testing.assert_allclose(weighted_stats(a, w, [0.]).p_up, .5)


def test_coherent_probabilities_and_exact_crps_against_pairwise_formula():
    raw = np.stack([ALPHAS-.5, 2*ALPHAS-1])
    a, w = quantile_atoms(raw, [.2, .7]); actual = np.array([.1, -.2])
    s = weighted_stats(a, w, actual)
    independent = (w*np.abs(a-actual[:, None])).sum(axis=1)-.5*(w[:, :, None]*w[:, None, :]*np.abs(a[:, :, None]-a[:, None, :])).sum(axis=(1, 2))
    np.testing.assert_allclose(s.crps, independent, atol=1e-14)
    np.testing.assert_allclose(s[['p_up', 'p_down', 'p_zero']].sum(axis=1), 1)
    np.testing.assert_allclose(s[['p_loss_over20', 'p_loss5_20', 'p_near_flat', 'p_gain5_20', 'p_gain_over20']].sum(axis=1), 1)
    assert (a > -1).all()


def test_support_floor_missing_outcomes_and_nonfinite_rejection():
    a, w = quantile_atoms(np.full((1, len(ALPHAS)), -2.))
    assert (a == -1).all()
    s = weighted_stats(a, w, [np.nan])
    assert s[['crps', 'brier', 'multiclass_brier']].isna().all().all()
    with pytest.raises(ValueError): quantile_atoms(np.full((1, len(ALPHAS)), np.inf))


def test_reliability_weights_months_not_stock_counts_and_excludes_unknowns():
    from report_distribution_shape_models import probability_reliability
    frame = pd.DataFrame(dict(date=['2021-01-29']+['2021-02-26']*9+['2021-03-31'],
        p_up=[.75]*11, actual=[.1]+[-.1]*9+[np.nan]))
    cells, summary = probability_reliability(frame)
    assert summary['observed_rows'] == 10 and summary['origin_months'] == 2
    np.testing.assert_allclose(cells.observed, .5)
    np.testing.assert_allclose(summary['bin_ece'], .25)


def test_reliability_zero_and_one_boundaries_include_zero_return_as_not_up():
    from report_distribution_shape_models import probability_reliability
    frame = pd.DataFrame(dict(date=['2021-01-29']*2, p_up=[0., 1.], actual=[0., .1]))
    cells, summary = probability_reliability(frame)
    assert cells.bucket.tolist() == [0, 9] and summary['bin_ece'] == 0
    frame.loc[0, 'p_up'] = np.nan
    with pytest.raises(ValueError): probability_reliability(frame)
