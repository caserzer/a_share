import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p56';O.mkdir(exist_ok=True)
assert not (O/'receipt.json').exists()
s=pd.read_csv(R/'p55/daily.csv',parse_dates=['date']);s=s[s.status.eq('OK') & s.date.ge('2023-01-01')]
assert s.date.is_unique
m=pd.read_csv(R/'p35/asof_states.csv',parse_dates=['date']).set_index('date');axis=m.index
# Feasibility is recorded before loading outcome statistics.
f=s.assign(year=s.date.dt.year).groupby('year').agg(observed_dates=('date','size'),min_common=('common','min'))
f.to_csv(O/'feasibility.csv');print('As-of support:\n',f.to_string())
d=pd.read_csv(R/'p35/daily.csv',parse_dates=['date'])
q=d.merge(s[['date','rho']],on='date',how='left',validate='many_to_one').merge(m[['market21','market126']],on='date',validate='many_to_one')
q.to_csv(O/'joined.csv',index=False)
def slope(a,controlled=False):
 cols=['rho','market21','market126'] if controlled else ['rho']
 z=a[['uplift']+cols].dropna()
 if len(z)<8:return np.nan
 x=np.column_stack([np.ones(len(z)),z[cols].values]);y=z.uplift.values
 if np.linalg.matrix_rank(x)<x.shape[1]:return np.nan
 b=np.linalg.lstsq(x,y,rcond=None)[0]
 return b[1]*10 # unit: percentage points per 0.1 rho
rows=[];annual=[]
for (h,method),g in q.groupby(['horizon','method']):
 a=g.set_index('date').reindex(axis)
 for year,t in a.groupby(a.index.year):
  annual.append(dict(horizon=h,method=method,year=year,dates=len(t[['rho','uplift']].dropna()),slope_pp=slope(t)))
 for controlled in [False,True]:
  rng=np.random.default_rng(3309);v=[];n=len(a)
  for _ in range(500):
   ix=((rng.integers(0,n,size=int(np.ceil(n/26)))[:,None]+np.arange(26))%n).ravel()[:n]
   v.append(slope(a.iloc[ix],controlled))
  lo,hi=np.nanquantile(v,[.025,.975])
  rows.append(dict(horizon=h,method=method,controlled=controlled,dates=len(a[['rho','uplift','market21','market126']].dropna()),slope_pp=slope(a,controlled),lo=lo,hi=hi,valid_bootstraps=int(np.isfinite(v).sum())))
pd.DataFrame(rows).to_csv(O/'summary.csv',index=False);pd.DataFrame(annual).to_csv(O/'annual.csv',index=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[R/'p55/daily.csv',R/'p35/daily.csv',R/'p35/asof_states.csv',R/'P56_rank_stability_increment_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.glob('*.csv')},axis_dates=len(axis),scope='descriptive association; no fitted predictor or new selection'),indent=2)+'\n')
print(pd.DataFrame(rows).to_string(index=False));print(pd.DataFrame(annual).query('horizon==126').to_string(index=False))
