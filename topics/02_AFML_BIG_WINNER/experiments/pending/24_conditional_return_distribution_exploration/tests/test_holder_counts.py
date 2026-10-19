import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from build_holder_counts import at_date,FEATURES,restrict_price_history


def history(rows):
    result=pd.DataFrame(rows,columns=['END_DATE','HOLD_NOTICE_DATE','HOLDER_NUM'])
    for c in ['END_DATE','HOLD_NOTICE_DATE']:result[c]=pd.to_datetime(result[c])
    return result


def test_same_day_announcement_and_future_comparison_not_used():
    h=history([('2020-12-31','2021-04-28',100),('2021-03-31','2021-04-30',80),('2020-09-30','2021-05-01',120)])
    r=at_date(h,pd.Timestamp('2021-04-30'))
    assert r['hc_current_count']==100 and np.isnan(r['hc_log_change'])
    next_r=at_date(h,pd.Timestamp('2021-05-01'))
    np.testing.assert_allclose(next_r['hc_log_change'],np.log(.8))
    assert next_r['hc_previous_count']==100


def test_stale_count_and_no_history_are_not_zero_features():
    h=history([('2021-01-01','2021-01-02',100)])
    at180=at_date(h,pd.Timestamp('2021-01-01')+pd.Timedelta(days=180))
    at181=at_date(h,pd.Timestamp('2021-01-01')+pd.Timedelta(days=181))
    assert np.isfinite(at180['hc_log_count'])
    assert all(np.isnan(at181[c]) for c in FEATURES) and at181['hc_current_count']==100
    none=at_date(h,pd.Timestamp('2021-01-02'))
    assert all(np.isnan(none[c]) for c in FEATURES)


def test_year_comparison_uses_nearest_available_period_and_ignores_early_notice():
    h=history([('2020-12-31','2021-01-15',200),('2021-01-31','2021-02-10',180),
               ('2021-09-30','2021-10-15',120),('2021-12-31','2022-01-20',100),
               ('2022-01-31','2022-01-15',50)])
    r=at_date(h,pd.Timestamp('2022-01-25'))
    assert r['hc_current_count']==100 and r['hc_previous_count']==120 and r['hc_year_count']==200
    assert r['hc_year_gap']==365
    np.testing.assert_allclose(r['hc_year_change'],np.log(.5))


def test_appending_unpublished_history_does_not_change_features():
    h=history([('2020-12-31','2021-02-01',100),('2021-03-31','2021-04-20',90)])
    future=history([('2021-06-30','2021-08-01',10),('2020-09-30','2021-05-30',999)])
    date=pd.Timestamp('2021-04-30')
    pd.testing.assert_series_equal(pd.Series(at_date(h,date)),pd.Series(at_date(pd.concat([h,future]),date)))


def test_pre_listing_private_count_cannot_be_year_comparison():
    h=history([('2019-05-05','2019-05-21',3),('2019-09-30','2019-10-20',300000),('2020-06-30','2020-08-20',340334)])
    h['SECURITY_CODE']='003816'
    restricted=restrict_price_history(h,{'003816':pd.Timestamp('2019-08-26')})
    r=at_date(restricted,pd.Timestamp('2020-09-30'))
    assert r['hc_current_count']==340334 and r['hc_previous_count']==300000
    assert np.isnan(r['hc_year_change'])
