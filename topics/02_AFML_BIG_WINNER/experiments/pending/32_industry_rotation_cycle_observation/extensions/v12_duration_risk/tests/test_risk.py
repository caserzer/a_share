import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from risk12 import add_risk
from context12 import ADDED


def frame():
    return pd.DataFrame(dict(threshold=[.1,.2],vol21=[.2,.2],vol63=[.2,.2],mom63=[.1,.1],
        state_drawdown=[-.03,-.03],state_direction=[1,1],state_drawup=[.1,.1],excess63=[.05,.05],state_age=[.5,.5]))


def test_annualized_volatility_converts_to_daily_scale():
    g=add_risk(frame());h=-np.log(.9)
    assert np.isclose(np.expm1(g.risk_clock63.iloc[0]),(h/(.2/np.sqrt(252)))**2)
    assert g.risk_clock63.iloc[1]>g.risk_clock63.iloc[0]


def test_higher_volatility_shortens_clock():
    f=frame().iloc[[0]].copy();a=add_risk(f)
    f[['vol21','vol63']]*=2;b=add_risk(f)
    assert np.isclose(np.expm1(b.risk_clock63.iloc[0]),np.expm1(a.risk_clock63.iloc[0])/4)


def test_future_rows_do_not_change_current_risk_features():
    f=frame();a=add_risk(f)
    future=f.copy();future[['vol21','vol63','mom63']]*=10
    b=add_risk(pd.concat([f,future],ignore_index=True)).iloc[:len(f)]
    pd.testing.assert_frame_equal(a[ADDED],b[ADDED])


def test_zero_vol_floor_and_direction_mask():
    f=frame();f[['vol21','vol63']]=0;f['state_direction']=-1
    r=add_risk(f)
    assert np.isfinite(r[ADDED]).all().all() and r.risk_distance.eq(0).all()
    assert r.risk_drift.between(-20,20).all()
