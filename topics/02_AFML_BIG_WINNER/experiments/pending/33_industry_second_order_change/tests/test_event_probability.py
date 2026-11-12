import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from event_probability_pool import mature_sets,fit_event,apply_admission_policy
from market_calibration_pool import apply_mapping

def test_maturity_filter_excludes_future_event_labels():
    g=pd.DataFrame({'date':pd.to_datetime(['2024-01-01','2024-07-01','2024-08-01']),
       'end126':pd.to_datetime(['2024-07-01','2025-01-01','2025-02-01']),'win126':[1,0,1],'candidate_event':[True,True,False]})
    ev,st,ok=mature_sets(g,pd.Timestamp('2025-01-01'))
    assert ev.index.tolist()==[0] and st.empty and not ok

def test_event_mapping_monotone_and_offset_is_constant_in_logit():
    from scipy.special import logit
    raw=np.linspace(.2,.9,120);prior={'theta':[.8,.1],'mean':[],'scale':[]};y=(raw>.6).astype(int)
    for variant in ['event_offset','event_platt']:
        params=fit_event(raw,y,prior,variant);prob,_=apply_mapping(raw,params)
        assert (np.diff(prob)>=0).all()
        if variant=='event_offset':assert np.std(logit(prob)-(.8*logit(raw)+.1))<1e-10

def test_admission_only_at_candidate_and_no_future_backfill():
    g=pd.DataFrame({'era':['x']*4,'industry_code':['a']*4,'block':[1]*4,'date':pd.date_range('2025-01-01',periods=4,freq='W'),
       'week_i':range(4),'day_i':[0,5,10,15],'fold':['2025Q1']*4,'opportunity_id':['a']*4,'probability':[.7]*4,
       'reference_probability':[.5]*4,'candidate_event':[False,False,True,False],'calibration_supported':[True]*4,'parent_admitted':[True]*4})
    z=apply_admission_policy(g);assert z.entry.tolist()==[False,False,True,False]
    assert z.admitted.tolist()==[False,False,True,True]
    before=apply_admission_policy(g.iloc[:2]);assert not before.admitted.any()
    g.loc[2,'probability']=.5;assert not apply_admission_policy(g).admitted.any()
