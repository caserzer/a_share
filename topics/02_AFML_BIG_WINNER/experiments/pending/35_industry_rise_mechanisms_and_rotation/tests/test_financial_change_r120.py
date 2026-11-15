import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from financial_change_r120 import bounded_change,aggregate

def test_losses_zero_and_scale():
    np.testing.assert_allclose(bounded_change([-50,10,0,0],[-100,-10,0,10]),[2/3,2,0,-2])
    np.testing.assert_allclose(bounded_change([5,-20],[10,-10]),bounded_change([500,-2000],[1000,-1000]))

def test_unknown_denominator_not_reweighted():
    g=pd.DataFrame(dict(unresolved=[1]*5,member_known=[True]*4+[False],change=[.2,.2,.2,.2,np.nan],transition=['advanced_report']*5,ttm_profit=[1]*5,prior_ttm_profit=[-1]*5))
    a=aggregate(g);assert a['members']==6 and a['known']==4 and a['status']=='insufficient_financial_coverage' and np.isnan(a['mean_change'])
    g.unresolved=0;a=aggregate(g)
    assert a['status']=='eligible_subset' and a['mean_change']==.2 and not a['strict_complete'] and np.isnan(a['full_population_mean'])

def test_known_unchanged_is_zero_not_missing():
    g=pd.DataFrame(dict(unresolved=[0]*5,member_known=[True]*5,change=[0.]*5,transition=['same_report']*5,ttm_profit=[-10]*5,prior_ttm_profit=[-10]*5))
    a=aggregate(g);assert a['strict_complete'] and a['full_population_mean']==0 and a['same_period']==5 and a['negative_endpoint']==5
