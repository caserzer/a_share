import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from pool_evaluation import joint_label,controls,block_ci

def test_joint_outcome_not_relative_defensive_or_market_beta():
    ret=pd.Series([.1,-.1,.1,0,.1,np.nan,.1])
    excess=pd.Series([.05,.05,-.05,.05,0,.05,np.nan])
    y=joint_label(ret,excess)
    assert y.iloc[:5].tolist()==[1,0,0,0,0]
    assert y.iloc[5:].isna().all()

def test_same_date_capacity_control_does_not_read_future():
    p=pd.DataFrame({'date':[1,1,1,2,2],'eligible':[True]*5,'rate20':[.1,.3,.2,.1,.2],
                    'era':['x']*5,'industry_code':list('abcde'),'win63':[1,0,1,0,1]})
    b,m=controls(p,[0,3]);assert m.tolist()==[1,4];assert len(b)==5
    p.win63=1-p.win63
    assert controls(p,[0,3])[1].tolist()==m.tolist()

def test_block_interval_preserves_constant_and_handles_missing():
    lo,hi=block_ci([np.nan]+[.12]*30,13)
    assert np.isclose(lo,.12) and np.isclose(hi,.12)
