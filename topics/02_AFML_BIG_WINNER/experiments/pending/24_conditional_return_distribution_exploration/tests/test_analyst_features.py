import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from build_analyst_features import target_anchors,features_at_date


def fixture():
    return pd.DataFrame(dict(publishDate=pd.to_datetime(['2020-01-03','2020-02-03','2020-04-03']),
        orgCode=['a','a','a'],infoCode=['1','2','3'],emRatingName=['买入']*3,
        indvAimPriceL=['120','70','100'],indvAimPriceT=['120','70','100']))


def test_original_target_units_and_uniform_future_adjustment_cancel():
    dates=pd.to_datetime(['2020-01-02','2020-02-02','2020-04-02'])
    raw=pd.Series([100.,50.,50.],index=dates);qfq=pd.Series([50.,50.,50.],index=dates)
    a=target_anchors(fixture(),raw,qfq)
    # First target 120 old shares becomes 60 after 2-for-1 split.
    np.testing.assert_allclose(a.target_anchor,[60,70,100])
    first=features_at_date(a,pd.Timestamp('2020-01-31'),50.)
    scaled=target_anchors(fixture(),raw,qfq*.3)
    second=features_at_date(scaled,pd.Timestamp('2020-01-31'),15.)
    np.testing.assert_allclose(first['target_upside'],np.log(1.2))
    np.testing.assert_allclose(first['target_upside'],second['target_upside'])


def test_announcements_on_or_after_prediction_date_excluded():
    dates=pd.to_datetime(['2020-01-02','2020-02-02','2020-04-02'])
    price=pd.Series([100.,100.,100.],index=dates)
    a=target_anchors(fixture(),price,price)
    d=pd.Timestamp('2020-02-03')
    first=features_at_date(a,d,100.)
    a.loc[a.publishDate>=d,'target_anchor']=999999
    second=features_at_date(a,d,100.)
    assert first==second
    assert first['latest_target_date']==pd.Timestamp('2020-01-03')


def test_unexplained_actions_and_expired_reports_stay_missing():
    dates=pd.to_datetime(['2020-01-02','2020-02-02','2020-04-02'])
    price=pd.Series([100.,100.,100.],index=dates)
    a=target_anchors(fixture(),price,price)
    result=features_at_date(a,pd.Timestamp('2020-01-31'),100.,pd.to_datetime(['2020-01-10']))
    assert not result['target_available'] and result['analyst_available']
    late=features_at_date(a,pd.Timestamp('2021-01-01'),100.)
    assert not late['target_available'] and not late['analyst_available']
    after=features_at_date(a,pd.Timestamp('2020-02-28'),100.,pd.to_datetime(['2020-01-10']))
    assert after['target_available'] and np.isnan(after['target_revision'])
