import numpy as np
import pandas as pd
from shared_horizon_models import stack_training, pooled_weights, queries


def panel():
    d = pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31', '2020-01-31', '2020-02-28', '2020-05-29']),
        instrument=['A', 'B', 'A', 'A'], feature=[1., 2., 3., 4.]))
    for h in [1, 3, 6, 12]:
        d[f'y_{h}'] = h/100
        d[f'end_{h}'] = d.date+pd.DateOffset(months=h)
    return d


def test_each_label_needs_its_own_maturity_and_strict_origin():
    d = panel(); date=pd.Timestamp('2020-05-29')
    t = stack_training(d, date, [1, 3], ['feature'])
    assert len(t) == 6 and t.date.lt(date).all() and t.label_end.lt(date).all()
    # Labels exactly at cutoff are unavailable, even if a short label has matured.
    d.loc[2, 'end_3'] = date
    t = stack_training(d, date, [1, 3], ['feature'])
    assert len(t) == 5 and len(t[t.horizon_months.eq(1)]) == 3
    assert (t[t.horizon_months.eq(3)].date == pd.Timestamp('2020-01-31')).all()


def test_future_outcomes_cannot_change_a_historical_pool():
    d = panel(); date=pd.Timestamp('2020-05-29')
    first = stack_training(d, date, [1, 3], ['feature'])
    for h in [1, 3, 6, 12]: d.loc[d[f'end_{h}'].ge(date), f'y_{h}'] = -1000
    pd.testing.assert_frame_equal(first, stack_training(d, date, [1, 3], ['feature']))


def test_equal_horizon_month_mass_and_same_pool_total():
    d = panel(); date=pd.Timestamp('2021-06-30')
    totals=[]
    for horizons in [[1, 3, 6], [1, 3, 6, 12]]:
        t = stack_training(d, date, horizons, ['feature']); w = pooled_weights(t, 100.)
        t = t.assign(weight=w)
        np.testing.assert_allclose(t.groupby('horizon_months').weight.sum(), 100/len(horizons))
        within = t.groupby(['horizon_months','date']).weight.sum()
        for h in horizons: np.testing.assert_allclose(within.loc[h], within.loc[h].iloc[0])
        totals.append(w.sum())
    np.testing.assert_allclose(totals, [100, 100])


def test_query_order_and_missing_labels():
    d = panel(); q = queries(d.iloc[:2], ['feature'])
    assert q.horizon_months.tolist() == [1, 1, 3, 3, 6, 6]
    assert q.feature.tolist() == [1, 2]*3
    d.loc[0, 'y_3'] = np.nan
    t = stack_training(d, pd.Timestamp('2021-06-30'), [1, 3], ['feature'])
    assert len(t) == 7 and len(t[t.horizon_months.eq(1)]) == 4
