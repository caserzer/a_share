import numpy as np
import pandas as pd
import pytest
from build_option_activity import feature_series
from download_option_activity import parse


def row(date='2018-12-28',code='510050'):
    return dict(SECURITY_CODE=code,TRADE_DATE=date,CALL_VOLUME='100',PUT_VOLUME='50',TOTAL_VOLUME='150',
                LEAVES_CALL_QTY='200',LEAVES_PUT_QTY='100',LEAVES_QTY='300',CP_RATE='50.00')


def test_ratios_use_counts_and_percent_is_only_validation():
    result=parse({'result':[row()]},pd.Timestamp('2018-12-28'))
    assert result[0]['put_volume']/result[0]['call_volume']==.5
    bad=row();bad['CP_RATE']='.5'
    with pytest.raises(AssertionError):parse({'result':[bad]},pd.Timestamp('2018-12-28'))


def test_missing_launched_underlying_is_an_error():
    with pytest.raises(AssertionError):parse({'result':[row(date='2021-04-01')]},pd.Timestamp('2021-04-01'))
    with pytest.raises(AssertionError):parse({'result':[]},pd.Timestamp('2018-12-28'))


def test_wrong_date_or_totals_are_rejected():
    with pytest.raises(AssertionError):parse({'result':[row()]},pd.Timestamp('2018-12-27'))
    bad=row();bad['TOTAL_VOLUME']='200'
    with pytest.raises(AssertionError):parse({'result':[bad]},pd.Timestamp('2018-12-28'))


def test_prelaunch_and_lagged_differences_stay_missing():
    dates=pd.date_range('2019-10-31',periods=5,freq='ME');rows=[]
    for i,date in enumerate(dates):
        rows.append(dict(date=date,code='510050',call_volume=100,put_volume=50+i*10,call_oi=200,put_oi=100+i*20))
        if i>=2:rows.append(dict(date=date,code='510300',call_volume=100,put_volume=60,call_oi=200,put_oi=150))
    result=feature_series(dates,pd.DataFrame(rows))
    assert np.isnan(result.loc[0,'opt300_volume_pcr']) and np.isnan(result.loc[2,'opt300_volume_pcr_change1'])
    assert result.opt300_volume_pcr_change3.isna().all()
    assert result.loc[3,'opt50_volume_pcr_change3']==pytest.approx(np.log(.8)-np.log(.5))
    pd.testing.assert_frame_equal(result.iloc[:3],feature_series(dates[:3],pd.DataFrame(rows[:4])))
