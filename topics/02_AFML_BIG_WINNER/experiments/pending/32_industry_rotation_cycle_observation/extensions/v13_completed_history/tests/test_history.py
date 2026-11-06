import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from history13 import add_history
from context13 import ADDED


def inputs():
    p=pd.DataFrame(dict(era=['A','A'],level=['L2','L2'],industry_code=['X','X'],threshold=[.1,.1],
        start_date=pd.to_datetime(['2018-01-01','2019-01-01']),end_date=pd.to_datetime(['2018-09-01','2019-04-01']),
        end_confirmed_at=pd.to_datetime(['2018-10-01','2019-05-01']),status=['CONFIRMED']*2,left_censored=[False]*2,
        duration_days=[243,90],industry_return=[.4,.15],qualified_CSI300=[True,False]))
    f=pd.DataFrame(dict(era=['A']*3,level=['L2']*3,industry_code=['X']*3,threshold=[.1]*3,benchmark=['CSI300']*3,
        date=pd.to_datetime(['2018-09-30','2018-10-01','2019-02-01'])))
    return f,p


def test_confirmation_time_boundary_and_missing_history():
    f,p=inputs();g=add_history(f,p)
    assert g.hist_count.iloc[0]==0 and np.isnan(g.hist_qualified.iloc[0]) and np.isnan(g.hist_last_return.iloc[0])
    assert np.isclose(g.hist_count.iloc[1],np.log(2)) and g.hist_qualified.iloc[1]==1


def test_future_completed_phase_does_not_change_past_features():
    f,p=inputs()
    a=add_history(f,p.iloc[:1]);b=add_history(f,p)
    pd.testing.assert_frame_equal(a[ADDED],b[ADDED])


def test_left_censored_phases_not_used_and_no_cross_era_own_history():
    f,p=inputs();p.loc[0,'left_censored']=True
    assert add_history(f,p).hist_count.eq(0).all()
    f,p=inputs();f['era']='B';g=add_history(f,p)
    assert g.hist_count.eq(0).all() and g.hist_last_return.isna().all()
    assert g.hist_qualified.iloc[-1]==1
