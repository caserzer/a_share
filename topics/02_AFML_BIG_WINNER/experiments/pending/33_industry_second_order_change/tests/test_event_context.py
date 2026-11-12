import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from event_context_pool import event_features,fit_context
from market_calibration_pool import apply_mapping

def test_event_features_use_only_anchor_and_current_observation():
    p=pd.DataFrame({'date':pd.date_range('2024-01-01',periods=3),'era':['x']*3,'industry_code':['a']*3,'block':[1]*3,'day_i':[0,1,2],'x':[.1,.2,99.],'market126':[.1,.2,99.]})
    g=pd.DataFrame({'candidate_event':[True],'anchor_row_id':[0],'row_id':[1]})
    a=event_features(g,p);b=event_features(g,p.iloc[:2])
    pd.testing.assert_frame_equal(a,b);assert np.isclose(a.relative_move.iloc[0],.1)

def test_event_context_model_monotonic_at_fixed_context():
    raw=np.linspace(.1,.9,100);f=np.column_stack([np.sin(np.arange(100)),np.cos(np.arange(100)),np.arange(100)/100])
    params=fit_context(raw,(raw>.6).astype(float),{'theta':[1,0]},f)
    pred,_=apply_mapping(raw,params,np.zeros((100,3)))
    assert params['theta'][0]>=0 and (np.diff(pred)>=0).all()
