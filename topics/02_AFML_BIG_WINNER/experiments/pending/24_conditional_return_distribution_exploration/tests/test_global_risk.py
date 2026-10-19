import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from build_global_risk import align_available,observed_features,monthly_features,LAGS


def sources():
    dates=pd.bdate_range('2018-01-01',periods=400)
    t=np.arange(len(dates))
    return dict(vix=pd.DataFrame({'VIX':20+t*.01,'VIX3M':25+t*.01},index=dates),
        nasdaq=pd.DataFrame({'NASDAQ':1000*np.exp(t*.001)},index=dates),
        yields=pd.DataFrame({'US10Y':.03+t*.00001,'US2Y':.02+t*.00001},index=dates),
        fx=pd.DataFrame({'USDCNY':6*np.exp(t*.0001)},index=dates))


def test_observation_date_is_not_fx_availability_date():
    x=pd.DataFrame({'value':[1.,9.]},index=pd.to_datetime(['2020-01-01','2020-01-15']))
    result=align_available(x,pd.to_datetime(['2020-01-16']),14,'fx')
    assert result.value.iloc[0]==1 and result.fx_observation_date.iloc[0]==pd.Timestamp('2020-01-01')


def test_stale_values_are_not_unboundedly_carried():
    x=pd.DataFrame({'value':[1.]},index=pd.to_datetime(['2020-01-01']))
    with pytest.raises(ValueError):align_available(x,[pd.Timestamp('2020-01-30')],3,'test')


def test_future_shocks_cannot_change_past_features():
    raw=sources();date=raw['nasdaq'].index[260]
    expected=monthly_features(raw,[date]);shocked={k:v.copy() for k,v in raw.items()}
    for k,v in shocked.items():v.loc[v.index>date-pd.Timedelta(days=LAGS[k])]*=100
    pd.testing.assert_frame_equal(monthly_features(shocked,[date]),expected)


def test_rates_are_fractional_fx_positive_means_depreciation_and_vol_is_annualized():
    raw=sources();result=observed_features(raw)
    np.testing.assert_allclose(result['yields'].global_us_slope,.01)
    np.testing.assert_allclose(result['yields'].global_us10y_change63.dropna(),.00063)
    np.testing.assert_allclose(result['fx'].global_usdcny_mom21.dropna(),np.exp(.0021)-1)
    n=raw['nasdaq'].NASDAQ
    np.testing.assert_allclose(result['nasdaq'].global_nasdaq_vol63.dropna(),n.pct_change().rolling(63).std().dropna()*np.sqrt(252))
    assert result['vix'].global_vix_term.lt(0).all()
