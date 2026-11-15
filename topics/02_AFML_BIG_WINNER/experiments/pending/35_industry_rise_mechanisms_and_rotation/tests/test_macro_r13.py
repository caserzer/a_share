import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from macro_r13 import macro_states,estimate_history

def macro_fixture():
    rows=[]
    for metric in ['manufacturing_pmi','m2_yoy']:
        for i,period in enumerate(pd.period_range('2020-01','2020-08',freq='M')):
            rows.append(dict(metric=metric,economic_month=str(period),value=50+i if metric=='manufacturing_pmi' else 10+i))
    return pd.DataFrame(rows)

def test_macro_availability_strict_and_three_calendar_month_difference():
    raw=macro_fixture();available=pd.Timestamp('2020-04-30')+pd.Timedelta(days=45)
    got=macro_states(raw,[available,available+pd.Timedelta(days=1)],45)
    assert got.economic_month.tolist()==['2020-03','2020-04']
    assert np.isnan(got.money.iloc[0])
    assert np.isclose(got.money.iloc[1],.03)

def test_macro_missing_month_is_not_compressed_or_zero_filled():
    raw=macro_fixture();raw=raw[~((raw.metric=='m2_yoy')&(raw.economic_month=='2020-02'))]
    date=pd.Timestamp('2020-05-31')+pd.Timedelta(days=46)
    got=macro_states(raw,[date],45)
    assert got.money.isna().all()

def test_future_macro_revisions_outside_prefix_do_not_change_alignment():
    raw=macro_fixture();date=pd.Timestamp('2020-06-15')
    before=macro_states(raw,[date],45)
    raw.loc[raw.economic_month>='2020-05','value']=9999
    pd.testing.assert_frame_equal(before,macro_states(raw,[date],45))

def test_sensitivity_needs_24_nonconstant_complete_observations():
    n=24;h=pd.DataFrame(dict(date=pd.date_range('2020-01-31',periods=n,freq='ME'),
        lag_pmi=np.arange(n)/100,lag_money=np.sin(np.arange(n)),past_excess20=np.arange(n)/1000))
    assert estimate_history(h.iloc[:23],[.1,.2]) is None
    assert estimate_history(h,[.1,.2])['n_fit']==24
    h['lag_money']=0
    assert estimate_history(h,[.1,.2]) is None
