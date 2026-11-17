import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from e1_excluded_holdings import replacement

def fixture():
 orig=pd.DataFrame({'instrument':['A','B','U'],'industry':['I','J','UNKNOWN'],'weight':[.3,.5,.2]})
 panel=pd.DataFrame({'instrument':['A','B','U','C','D','E'],'industry':['I','J','UNKNOWN','I','I','J'],'E1':[5,4,8,2,1,2],'exclusion_reason':['SMALL','IN_C','INDUSTRY_UNKNOWN','SMALL','MISSING','IN_C']})
 return orig,panel

def test_same_sector_disjoint_budget_and_unknown_retention():
 o,g=fixture();w,m,p,a=replacement(o,g,'P')
 assert w=={'B':.5,'U':.2,'C':.15,'D':.15}
 assert m=={'A':.3} and sum(p.values())==.3
 assert a[-1]['status']=='INDUSTRY_UNKNOWN'

def test_reason_matching_not_relaxed():
 o,g=fixture();w,m,p,a=replacement(o,g,'PR');assert p=={'C':.3}
 g.loc[g.instrument=='C','exclusion_reason']='MISSING'
 w,m,p,a=replacement(o,g,'PR');assert not m and w==o.set_index('instrument').weight.to_dict()

def test_outcomes_do_not_change_target_and_original_immutable():
 o,g=fixture();before=o.copy(deep=True);w,*_=replacement(o,g,'P')
 g['h10']=1e10;g['future_return']=-1e10
 assert replacement(o,g,'P')[0]==w
 pd.testing.assert_frame_equal(o,before)

def test_industry_disagreement_not_silently_matched():
 o,g=fixture();g.loc[g.instrument=='A','industry']='J'
 w,m,p,a=replacement(o,g,'P');assert not m and a[0]['status']=='INDUSTRY_SOURCE_DISAGREEMENT'
