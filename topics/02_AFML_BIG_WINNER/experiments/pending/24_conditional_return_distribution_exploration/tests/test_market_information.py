import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from build_market_breadth import fraction_positive
from run_market_information import month_class_frequencies, forecast_market_classes, reweight_market
from run_direct_probability import weighted_stats


def test_breadth_does_not_count_missing_as_down():
    assert fraction_positive(pd.Series([1, -1, np.nan])) == .5
    assert np.isnan(fraction_positive(pd.Series([np.nan])))


def test_months_have_equal_weight_despite_number_of_stocks():
    d = pd.DataFrame({'date': [1, 1, 2], 'y_1': [-.1, .1, .3]})
    f = month_class_frequencies(d, 1)
    np.testing.assert_allclose(f.sum(axis=1), 1)
    assert f.loc[1, 1] == .5 and f.loc[2, 6] == 1


def test_future_market_feature_rows_do_not_change_forecast():
    features = pd.DataFrame({'known': [1., 2., 3., 4.]}, index=[1, 2, 3, 4])
    f = pd.DataFrame([[.1, .1, .1, 0, .2, .2, .3], [.3, .2, .1, 0, .1, .1, .2]], index=[1, 2])
    first = forecast_market_classes(features, f, 3, ['known'])
    features.loc[4, 'known'] = -99999
    second = forecast_market_classes(features, f, 3, ['known'])
    np.testing.assert_array_equal(first, second)


def test_reweighting_coherent_distribution_and_identity():
    a = np.array([[-.3, -.1, -.01, 0, .01, .1, .3]])
    w = np.ones_like(a) / 7
    target = np.array([.05, .05, .05, .05, .2, .3, .3])
    new = reweight_market(a, w, target, 0)
    np.testing.assert_allclose(new[0], target)
    s = weighted_stats(a, new, [.1])
    np.testing.assert_allclose(s.p_up, .8)
    np.testing.assert_allclose(reweight_market(a, w, np.ones(7)/7, .5), w)
    assert s.crps.iloc[0] >= 0
