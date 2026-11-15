import numpy as np
import pandas as pd
import pytest
from cutoff_features_r102 import regenerate

def fixture():
    dates=pd.bdate_range('2025-12-01','2026-04-15')
    market=pd.Series(100+np.arange(len(dates))*.1,index=dates,name='close')
    d=pd.DataFrame(dict(era='SW2021',level='L1',industry_code='TEST',date=dates,block=1,nav=1+np.arange(len(dates))*.002,coverage=1.,members=10,breadth21=.5,breadth63=.5))
    return d,market

def test_future_changes_isolated():
    d,b=fixture();expected=regenerate(d,b,'2026-03-31')
    d.loc[d.date.gt('2026-03-31'),'nav']=999
    b.loc[b.index>'2026-03-31']=.1
    pd.testing.assert_frame_equal(regenerate(d,b,'2026-03-31'),expected)

def test_weekend_completion_and_break():
    d,b=fixture()
    friday=regenerate(d,b,'2026-01-30')
    assert not friday.date.eq('2026-01-30').any()
    saturday=regenerate(d,b,'2026-01-31')
    assert saturday.date.eq('2026-01-30').any()
    d.loc[d.date.ge('2026-03-20'),'block']=2
    result=regenerate(d,b,'2026-03-31').iloc[-1]
    assert pd.isna(result.mom20) and pd.isna(result.past_excess20) and not result.price_ready

def test_duplicate_identity_rejected():
    d,b=fixture()
    with pytest.raises(ValueError,match='duplicate daily'):regenerate(pd.concat([d,d.iloc[:1]]),b,'2026-03-31')
    with pytest.raises(ValueError,match='duplicate benchmark'):regenerate(d,pd.concat([b,b.iloc[:1]]),'2026-03-31')
