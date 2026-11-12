import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from probability_pool import split,calibrate,calibrated,gate,date_weights,admission_events

def test_temporal_split_excludes_unmatured_and_purges_label_overlap():
    p=pd.DataFrame({'date':pd.to_datetime(['2021-01-01','2022-03-01','2022-07-01','2023-10-01','2024-01-05']),
        'end126':pd.to_datetime(['2021-07-01','2022-09-01','2023-01-01','2024-04-01','2024-07-01']),
        'eligible':[True]*5,'win126':[1,0,1,0,1]})
    tr,ca,te,start=split(p,pd.Timestamp('2024-01-01'))
    assert tr.index.tolist()==[0] and ca.index.tolist()==[2] and te.index.tolist()==[4]
    altered=p.copy();altered.loc[[3,4],'win126']=[1,0]
    a,b,_,_=split(altered,pd.Timestamp('2024-01-01'))
    pd.testing.assert_frame_equal(a,tr);pd.testing.assert_frame_equal(b,ca)

def test_monotone_calibration_cannot_invert_probability_order():
    raw=np.linspace(.05,.95,100);params=calibrate(raw,(raw>.5).astype(int),np.ones(100))
    result=calibrated(raw,params)
    assert params['slope']>=0 and (np.diff(result)>=0).all()
    assert ((result>=0)&(result<=1)).all()

def test_gate_requires_absolute_and_relative_threshold():
    assert gate(np.array([.59,.61,.7]),np.array([.3,.6,.6])).tolist()==[False,False,True]

def test_date_weights_preserve_equal_date_mass():
    p=pd.DataFrame({'date':[1,1,2]});w=date_weights(p)
    assert np.isclose(w[:2].sum(),w[2]) and np.isclose(w.mean(),1)

def test_first_admission_does_not_repeat_state_or_treat_gap_as_known():
    p=pd.DataFrame({'date':pd.date_range('2024-01-01',periods=6,freq='W'),'era':['x']*6,'industry_code':['a']*6,'block':[1]*6,
        'week_i':[0,1,2,4,5,6],'day_i':[0,5,10,20,25,30],'admitted':[True,False,True,True,False,True],'fold':['a']*5+['b']})
    z=admission_events(p)
    assert z.entry.tolist()==[False,False,True,False,False,True]
    assert z.boundary_unknown.tolist()==[True,False,False,True,False,False]
    assert z.cooldown126.sum()==1 and z.refit_entry.sum()==1
