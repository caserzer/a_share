import sys,json
from pathlib import Path
import pandas as pd,numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID
OUT=EP/'restart/p04';s=json.loads((OUT/'selection_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert sha(OUT/'pairs.csv')==s['pairs_sha256']
p=pd.read_parquet(EP/'restart/p03/selected_features.parquet').reset_index(drop=True);p['age']=(p.date-p.candidate_low_date).dt.days
r=pd.read_csv(OUT/'pairs.csv',parse_dates=['date']);e=pd.read_csv(OUT/'evaluated_pairs.csv',parse_dates=['date']);assert not r.left.duplicated().any() and not r.right.duplicated().any()
a=p.loc[r.left].reset_index(drop=True);b=p.loc[r.right].reset_index(drop=True)
assert (a.date==b.date).all() and (a.date==r.date).all();assert a.relative_up.all() and (~b.relative_up).all()
assert (a.early&a.state_direction.eq(-1)&a.age.gt(0)).all() and (b.early&b.state_direction.eq(-1)&b.age.gt(0)).all()
assert (a.age-b.age).abs().le(7).all();assert (a.state_drawup-b.state_drawup).abs().le(.02+1e-12).all()
assert np.allclose(a.age-b.age,r.age_diff);assert np.allclose(a.state_drawup-b.state_drawup,r.drawup_diff)
# Verify maximum feasible cardinality independently of the assignment cost.
checked=0
for date,g in p[p.early&p.state_direction.eq(-1)&p.age.gt(0)].groupby('date'):
 l=g[g.relative_up];q=g[~g.relative_up]
 if not len(l) or not len(q):continue
 edges=(np.abs(l.age.to_numpy()[:,None]-q.age.to_numpy())<=7)&(np.abs(l.state_drawup.to_numpy()[:,None]-q.state_drawup.to_numpy())<=.02+1e-12)
 matched=maximum_bipartite_matching(csr_matrix(edges),perm_type='column');assert (matched>=0).sum()==r.date.eq(date).sum();checked+=1
labels=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet');p=p.merge(labels[ID+['win63','win126','win252']],on=ID,how='left',validate='one_to_one')
for h in [63,126,252]:
 assert np.allclose(e[f'left{h}'],p.loc[r.left,f'win{h}'],equal_nan=True)
 assert np.allclose(e[f'right{h}'],p.loc[r.right,f'win{h}'],equal_nan=True)
 assert np.allclose(e[f'delta{h}'],e[f'left{h}']-e[f'right{h}'],equal_nan=True)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',pairs_checked=len(r),maximum_cardinality_dates=checked,horizons_checked=3,selection_seal_verified=True,efficacy_established=False),indent=2)+'\n');print('PASS',len(r),'pairs;',checked,'maximum-cardinality date checks')
