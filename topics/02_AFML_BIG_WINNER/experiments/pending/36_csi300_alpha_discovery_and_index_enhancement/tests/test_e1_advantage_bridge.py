import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pandas as pd
from e1_advantage_bridge import quotas,choose,risk_only,STYLES,standard

def frame():
 rng=np.random.default_rng(5);g=pd.DataFrame({'instrument':[f'S{i:03}' for i in range(120)],'industry':['A']*51+['B']*39+['C']*30,'E1':rng.normal(size=120)})
 for s in STYLES:g[s]=rng.normal(size=120)
 return g

def test_exact_slot_conservation_and_stable_ties():
 g=frame();g['E1']=1
 for k in [24,60]:
  q=quotas(g,k);assert q.sum()==k;mask=choose(g,k,True)
  for a,n in q.items():assert g.loc[(g.industry==a)&(mask==1),'instrument'].tolist()==g.loc[g.industry==a,'instrument'].tolist()[:n]

def test_pool_count_and_no_outcome_selection():
 g=frame();mask=choose(g,60);changed=g.assign(future_return=1000,future_tradeable=False)
 np.testing.assert_array_equal(mask,choose(changed,60));assert choose(g,24).sum()==24
 assert np.all(choose(g,24)<=mask)

def test_reverse_risk_contract_without_industry_constraint():
 g=frame();base=choose(g,24,True);mask,info=risk_only(g,24,base)
 assert mask.sum()==24 and info['gap']<=.01+1e-8
 assert np.max(abs(standard(g[STYLES]).T@(mask-base)/24))<=.2500001
