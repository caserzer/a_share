import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from e1_mechanism import state_scores,base_mask,solve,STYLES,bootstrap,conditional,standard

def fixture(n=120):
 rng=np.random.default_rng(7)
 g=pd.DataFrame({'instrument':[f'S{i:03}' for i in range(n)],'industry':np.repeat(['A','B','C'],n//3),'T':rng.normal(size=n),'P':rng.normal(size=n),'E1':rng.normal(size=n)})
 for s in STYLES:g[s]=rng.normal(size=n)
 return state_scores(g)

def test_signal_functions_ignore_outcomes():
 a=fixture();b=a.copy();b['future_return']=10000.;b['future_can_buy']=False
 pd.testing.assert_frame_equal(state_scores(a),state_scores(b).drop(columns=['future_return','future_can_buy']))
 np.testing.assert_array_equal(base_mask(a)[0],base_mask(b)[0])

def test_industry_counts_and_constraint():
 a=fixture();base,k=base_mask(a);assert k==24
 assert all(base[a.industry==i].sum()==8 for i in ['A','B','C'])
 pick,info=solve(a,base,k,'J');assert pick is not None and info['accepted'];assert pick.sum()==k
 assert np.max(abs(standard(a[STYLES]).T@(pick-base)/k))<=.2500001
 assert all(pick[a.industry==i].sum()==8 for i in ['A','B','C'])

def test_tie_order():
 a=fixture();a['B']=.5;mask,k=base_mask(a)
 for i in ['A','B','C']:assert a.loc[(a.industry==i)&(mask==1),'instrument'].tolist()==a.loc[a.industry==i,'instrument'].tolist()[:8]

def test_calendar_gaps_not_compressed():
 ix=pd.date_range('2020-01-01',periods=40,freq='MS');s=pd.Series(np.arange(40.),index=ix);s.iloc[10:20]=np.nan
 out=bootstrap(s,'M',3,100);assert out['periods']==40 and out['n']==30
 assert bootstrap(s*0+2,'M',3,100)['ci_low']==2

def test_conditioning_does_not_create_missing_outcomes():
 a=fixture();z=standard(a[STYLES])
 for j,s in enumerate(STYLES):a['z_'+s]=z[:,j]
 a['std_J']=standard(a.J);a['std_E1']=standard(a.E1);a['y']=3*a.std_J
 r=conditional(a);assert abs(r['P1']['value']-3)<1e-8
 a['std_J']=0;assert np.isnan(conditional(a)['P1']['value'])
