import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from market_calibration_pool import fit_mapping,apply_mapping
from opportunity_episode_audit import episodes

def test_conditional_calibration_is_monotone_at_fixed_market_state():
    raw=np.linspace(.1,.9,100);m=np.column_stack([np.sin(np.arange(100)),np.cos(np.arange(100))]);y=(raw>.55).astype(float)
    params=fit_mapping(raw,y,np.ones(100),m)
    prob,_=apply_mapping(raw,params,np.zeros((100,2)))
    assert params['theta'][0]>=0 and (np.diff(prob)>=0).all()
    assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()

def test_market_extrapolation_flag_uses_only_fitted_scaling():
    raw=np.linspace(.1,.9,20);m=np.arange(20).reshape(-1,1)
    params=fit_mapping(raw,(raw>.5).astype(float),np.ones(20),m)
    old=repr(params);prob,outside=apply_mapping([.5,.5],params,[[1],[10000]])
    assert outside.tolist()==[False,True] and repr(params)==old

def test_rearm_and_cluster_ignore_short_exit_and_unknown_gap():
    flags=[False,True,False,True,False,False,False,False,True,False,True]
    frame=pd.DataFrame({'era':['x']*11,'industry_code':['a']*11,'block':[1]*11,'week_i':[0,1,2,3,4,5,6,7,8,10,11],
       'day_i':[x*5 for x in [0,1,2,3,4,5,6,7,8,10,11]],'date':pd.date_range('2024-01-01',periods=11,freq='W'),
       'admitted':flags,'entry':[False,True,False,True,False,False,False,False,True,False,True]})
    z=episodes(frame)
    assert z.index[z.rearm4].tolist()==[1,8]
    assert z.cluster_first126.sum()==1 and z.repeat_within126.sum()==3
    assert z.loc[z.entry,'opportunity_id'].nunique()==1
