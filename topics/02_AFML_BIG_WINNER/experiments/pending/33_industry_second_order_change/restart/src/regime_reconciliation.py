import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p35';OUT.mkdir(exist_ok=True)
assert not (OUT/'receipt.json').exists()
source=EP/'restart/p30/evaluated.parquet'
market=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
q=pd.read_parquet(source);m=pd.read_parquet(market).close.sort_index()
assert m.index.is_unique and q.date.notna().all()
axis=pd.DatetimeIndex(sorted(q.date.unique()))
s=pd.DataFrame({'market21':(m/m.shift(21)-1).reindex(axis),'market126':(m/m.shift(126)-1).reindex(axis)})
assert s.notna().all().all()
s['regime']=pd.Series(np.where(s.market126.gt(0),'UP','NONUP'),index=s.index)+'/'+pd.Series(np.where(s.market21.gt(0),'RISING','FALLING'),index=s.index)
s.index.name='date';s.reset_index().to_csv(OUT/'asof_states.csv',index=False)
for date,r in s.iterrows():
 i=m.index.get_loc(date)
 for h in [21,126]:assert np.isclose(r[f'market{h}'],m.iloc[i]/m.iloc[i-h]-1)
q=q.merge(s,on='date',validate='many_to_one');daily=[];edges=[]
for h in [63,126,252]:
 label=f'new_win{h}';base=q.groupby('date')[label].mean()
 for method in ['momentum','rebuilt']:
  a=q[q[method]].groupby('date')[label].agg(['mean','count']).rename(columns={'mean':'win','count':'valued'})
  a['base']=base;a['uplift']=a.win-a.base;a['method']=method;a['horizon']=h
  a=a.join(s.regime);daily.append(a.reset_index())
  z=q[q[method+'_edge']&q[label].notna()].copy();z['uplift']=z[label]-z.date.map(base)
  for (year,regime),b in z.groupby([z.date.dt.year,'regime']):
   edges.append(dict(year=year,regime=regime,method=method,horizon=h,events=len(b),win=b[label].mean(),uplift=b.uplift.mean()))
d=pd.concat(daily,ignore_index=True);d['year']=d.date.dt.year
d.to_csv(OUT/'daily.csv',index=False);pd.DataFrame(edges).to_csv(OUT/'annual_edges.csv',index=False)
rows=[]
for (h,method,regime),b in d.groupby(['horizon','method','regime']):
 for year in ['ALL',2023,2024,2025,2026]:
  g=b if year=='ALL' else b[b.year.eq(year)]
  fullaxis=axis if year=='ALL' else axis[axis.year==year]
  if len(g)==0:continue
  lo,hi=block_ci(g.set_index('date').uplift.reindex(fullaxis),26)
  n=int(g.win.notna().sum())
  rows.append(dict(horizon=h,method=method,regime=regime,year=year,dates=len(g),valued_dates=n,base=g.base.mean(),win=g.win.mean(),uplift=g.uplift.mean(),lo=lo,hi=hi,basic_year_support=year in [2023,2024,2025] and n>=26))
r=pd.DataFrame(rows);r.to_csv(OUT/'summary.csv',index=False)
# Reconcile pooled original edge results independently of state summaries.
old=pd.read_csv(EP/'restart/p30/annual_events.csv');checks=0
for _,r0 in old.iterrows():
 z=q[q[r0.method+'_edge']&q.date.dt.year.eq(r0.year)]
 y=z[f'new_win{int(r0.horizon)}'];assert int(y.notna().sum())==r0.known
 assert np.isclose(y.mean(),r0.win,equal_nan=True);checks+=1
assert q.groupby('date').regime.nunique().eq(1).all()
inputs=[source,market,EP/'restart/P35_regime_reconciliation_plan.md',Path(__file__)]
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',annual_edge_checks=checks,market_lookback_checks=len(s)*2,inputs={str(f):sha(f) for f in inputs},artifacts={f.name:sha(f) for f in OUT.iterdir() if f.is_file()},scope='historical descriptive reconciliation; no admission rule or probability calibration'),indent=2)+'\n')
print(r.query('horizon==126')[['method','regime','year','valued_dates','base','win','uplift','lo','hi','basic_year_support']].to_string(index=False))
