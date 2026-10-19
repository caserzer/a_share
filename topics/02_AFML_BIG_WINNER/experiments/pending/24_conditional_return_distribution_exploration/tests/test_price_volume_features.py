import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from build_price_volume_features import daily_features, ACTIVITY, PATH


def bars():
    dates=pd.bdate_range('2020-01-01',periods=120);rng=np.random.default_rng(24)
    close=10*np.exp(np.cumsum(rng.normal(0,.01,len(dates))))
    opening=close/np.exp(rng.normal(0,.005,len(dates)))
    high=np.maximum(close,opening)*1.01;low=np.minimum(close,opening)*.99
    volume=rng.integers(100000,1000000,len(dates)).astype(float)
    raw=pd.DataFrame(dict(open=opening,high=high,low=low,close=close,volume=volume,
        money=volume*(high+low)/2,turnover_rate=volume/1e8,source_volume_unit='shares',source_turnover_unit='ratio'),index=dates)
    return raw,pd.DataFrame(dict(close=close/2),index=dates),dates


def test_later_bars_and_events_do_not_change_earlier_features():
    raw,qfq,dates=bars();full,_=daily_features(raw,qfq,dates)
    prefix,_=daily_features(raw.iloc[:85],qfq.iloc[:85],dates[:85])
    pd.testing.assert_frame_equal(full.iloc[:85],prefix)
    raw.loc[dates[85]:,['open','high','low','close','money']]*=3
    qfq.loc[dates[85]:,'close']*=3
    changed,_=daily_features(raw,qfq,dates,[dates[100]])
    pd.testing.assert_frame_equal(full.iloc[:85],changed.iloc[:85])


def test_bad_units_remove_activity_features_without_inventing_price_gaps():
    raw,qfq,dates=bars();raw.loc[dates[80],'source_volume_unit']='hands'
    features,audit=daily_features(raw,qfq,dates)
    assert audit['unit_or_vwap_rejected_rows']==1
    assert features.loc[dates[80],'activity_support63']==62
    assert pd.isna(features.loc[dates[80],'pv_money_accel5_63'])
    assert pd.notna(features.loc[dates[80],'path_intraday_mean21'])


def test_unexplained_factor_event_only_masks_dependent_return_features():
    raw,qfq,dates=bars();base,_=daily_features(raw,qfq,dates)
    flagged,_=daily_features(raw,qfq,dates,[dates[80]])
    pd.testing.assert_frame_equal(base.iloc[:80],flagged.iloc[:80])
    assert pd.isna(flagged.loc[dates[80],'path_overnight_mean21'])
    np.testing.assert_allclose(flagged.path_intraday_mean21,base.path_intraday_mean21,equal_nan=True)


def test_valid_flat_bars_have_explicit_neutral_location_and_indicator():
    raw,qfq,dates=bars();date=dates[80];price=raw.loc[date,'close']
    raw.loc[date,['open','high','low']]=price;raw.loc[date,'money']=price*raw.loc[date,'volume']
    features,_=daily_features(raw,qfq,dates)
    np.testing.assert_allclose(features.loc[date,'path_flat_bar_fraction21'],1/21)
    assert -1<=features.loc[date,'path_close_location21']<=1
    assert not np.isinf(features[ACTIVITY+PATH].to_numpy()).any()
