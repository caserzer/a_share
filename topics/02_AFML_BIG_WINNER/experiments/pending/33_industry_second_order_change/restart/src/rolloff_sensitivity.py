import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p42';q=pd.read_parquet(OUT/'evaluated.parquet');axis=pd.DatetimeIndex(sorted(q.date.unique()));z=q[q.history_proxy60.eq(0)].copy();daily=[];rows=[]
for method,score in [('B','B'),('P','P'),('momentum','rate60'),('recent','rate5')]:
 a=z.sort_values(['date',score,'era','industry_code'],ascending=[True,False,True,True]);keep=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2));b=a[keep]
 for h in [63,126,252]:
  label=f'new_win{h}';base=z.groupby('date')[label].mean()
  for date,g in b.groupby('date'):daily.append(dict(date=date,year=date.year,method=method,horizon=h,win=g[label].mean(),uplift=g[label].mean()-base.loc[date],selected=len(g)))
 d=b.groupby('date').size();assert (d==np.ceil(z.groupby('date').size()*.2)).all()
d=pd.DataFrame(daily);d.to_csv(OUT/'clean_history_daily.csv',index=False);d.groupby(['year','method','horizon'])[['win','uplift']].mean().to_csv(OUT/'clean_history_annual.csv')
for h,g in d.groupby('horizon'):
 a=g.pivot(index='date',columns='method',values='win').reindex(axis)
 for c in ['B','momentum','recent']:
  delta=a.P-a[c];lo,hi=block_ci(delta,26);rows.append(dict(horizon=h,control=c,delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(rows).to_csv(OUT/'clean_history_comparisons.csv',index=False)
# Check edge/boundary convention directly, without group-shift implementation.
checks=0;boundaries={m:0 for m in ['B','P','momentum','recent']}
for _,g in q.groupby(['era','industry_code','block']):
 prev=None
 for r in g.sort_values('date').to_dict('records'):
  continuous=prev is not None and r['week']==prev['week']+1
  for method in boundaries:
   selected=bool(r[method+'_selected']);edge=selected and continuous and not bool(prev[method+'_selected'])
   assert bool(r[method+'_edge'])==edge
   boundaries[method]+=int(selected and not continuous);checks+=1
  prev=r
folds=pd.read_csv(OUT/'feasibility.csv');assert (pd.to_datetime(folds.last_end)<pd.to_datetime(folds.cutoff)).all()
(OUT/'sensitivity_validation.json').write_text(json.dumps(dict(status='PASS',clean_rows=len(z),clean_dates=z.date.nunique(),edge_checks=checks,boundaries=boundaries,mature_fold_checks=len(folds),training_contains_proxies=True,inputs={str(p):sha(p) for p in [OUT/'evaluated.parquet',Path(__file__)]}),indent=2)+'\n')
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print(boundaries)
print(pd.read_csv(OUT/'annual.csv').query('horizon==126').to_string(index=False))
