import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from industry_valuation_r114 import aggregate

def fixture():
    r=np.array([1.,-.5,0,0,0]);x=np.log1p(r)
    return pd.DataFrame(dict(unresolved=[0]*5,status=['raw_identity_ready']*5,log_raw=x,log_pe=x,log_implied_eps=[0.]*5))

def test_mean_log_is_not_equal_weight_arithmetic_return():
    a=aggregate(fixture(),'raw')
    assert a['strict_complete'] and np.isclose(a['covered_geometric_growth'],0)
    assert np.isclose(a['full_basket_arithmetic'],.1) and np.isclose(a['jensen_gap'],np.log(1.1))

def test_missing_and_unresolved_preserve_full_denominator():
    g=fixture();g.loc[0,'status']='nonpositive_or_missing_pe';a=aggregate(g,'raw')
    assert a['known']==4 and a['members']==5 and a['status']=='eligible_subset' and not a['strict_complete'] and np.isnan(a['full_basket_arithmetic'])
    g['unresolved']=1;a=aggregate(g,'raw');assert a['members']==6 and a['status']=='insufficient_positive_basis_coverage' and np.isnan(a['covered_arithmetic_growth'])
    g['unresolved']=np.nan;a=aggregate(g,'raw');assert a['status']=='unknown_member_denominator'
