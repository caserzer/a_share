import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pandas as pd
from e1_style_channels import STYLES,GROUPS,fixed_pick,solve,standard,quotas

def data():
 rng=np.random.default_rng(91);g=pd.DataFrame({'instrument':[f'X{i:03}' for i in range(120)],'industry':['A']*40+['B']*40+['C']*40,'E1':rng.normal(size=120)})
 for s in STYLES:g[s]=rng.normal(size=120)
 return g

def test_groups_cover_exactly_once():
 flat=[v for cols in GROUPS.values() for v in cols];assert len(flat)==len(set(flat))==13;assert set(flat)==set(STYLES)

def test_fixed_selection_no_future_inputs_and_ties():
 g=data();a=fixed_pick(g,24,np.ones(len(g)));b=fixed_pick(g.assign(future_return=1000),24,np.ones(len(g)));np.testing.assert_array_equal(a,b)
 for ind in ['A','B','C']:assert g.loc[(a==1)&g.industry.eq(ind),'instrument'].tolist()==g.loc[g.industry.eq(ind),'instrument'].tolist()[:8]

def test_each_group_bound_and_industry_slots():
 g=data();base=fixed_pick(g,24,g.E1)
 for cols in GROUPS.values():
  mask,info=solve(g,24,base,cols);assert info['accepted'] and mask.sum()==24
  z=standard(g[STYLES]);idx=[STYLES.index(c) for c in cols];assert np.max(abs(z[:,idx].T@(mask-base)/24))<=.2500001
  for ind in ['A','B','C']:assert mask[g.industry==ind].sum()==8
