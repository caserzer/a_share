import sys,json
from pathlib import Path
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'src'));from pool_evaluation import block_ci,sha
O=R/'p64';q=pd.read_parquet(O/'evaluated.parquet');axis=pd.DatetimeIndex(sorted(q.date.unique()));methods=['B','M','P','momentum'];checks=0
for _,g in q.groupby(['era','industry_code','block']):
 g=g.sort_values('week');prev=None
 for _,row in g.iterrows():
  for method in methods:
   expected=prev is not None and row.week-prev.week==1 and row[method+'_selected'] and not prev[method+'_selected'];assert bool(row[method+'_edge'])==bool(expected);checks+=1
  prev=row
# Conditional clean-input sensitivity: same scores, re-rank same capacity on common clean subset.
z=q[q.history_proxy60.eq(0)].copy();daily=[]
for method,score in [('B','B'),('M','M'),('P','P'),('momentum','rate60')]:
 a=z.sort_values(['date',score,'era','industry_code'],ascending=[True,False,True,True]);sel=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2));t=a[sel]
 for h in [63,126,252]:
  for date,value in t.groupby('date')[f'new_win{h}'].mean().items():daily.append(dict(date=date,horizon=h,method=method,win=value))
d=pd.DataFrame(daily);out=[]
for h,g in d.groupby('horizon'):
 a=g.pivot(index='date',columns='method',values='win').reindex(axis)
 for c in ['M','B','momentum']:
  delta=a.P-a[c];lo,hi=block_ci(delta,26);out.append(dict(horizon=h,control=c,delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(out).to_csv(O/'clean_sensitivity.csv',index=False)
s=pd.read_parquet(R/'p57/rebuilt_states.parquet',columns=['era','industry_code','date','state_age','state_drawup']);z=q.merge(s,on=['era','industry_code','date'],how='left',validate='one_to_one');rows=[]
for m in methods:
 t=z[z[m+'_selected']];g=q.groupby(['era','industry_code','block']);cont=q.week.sub(g.week.shift()).eq(1)
 rows.append(dict(method=m,selected=len(t),state_missing=int(t.state_age.isna().sum()),median_age_days=t.state_age.median()*90,median_drawup=t.state_drawup.median(),unknown126=int(q.loc[q[m+'_edge'],'new_win126'].isna().sum()),boundary=int((q[m+'_selected']&~cont).sum())))
pd.DataFrame(rows).to_csv(O/'timing_unknown.csv',index=False)
pd.DataFrame([dict(year=y,delta_P_M=b.P-b.M,delta_P_B=b.P-b.B) for y,b in pd.read_csv(O/'annual.csv').query('horizon==126').pivot(index='year',columns='method',values='win').iterrows()]).to_csv(O/'annual_deltas.csv',index=False)
(O/'additional_validation.json').write_text(json.dumps(dict(status='PASS',direct_event_checks=checks,artifacts={n:sha(O/n) for n in ['clean_sensitivity.csv','timing_unknown.csv','annual_deltas.csv']}),indent=2)+'\n');print(pd.DataFrame(out).query('horizon==126').to_string(index=False));print(pd.DataFrame(rows).to_string(index=False));print(pd.read_csv(O/'annual_deltas.csv').to_string(index=False));print(pd.read_csv(O/'feasibility.csv').head(1).to_string(index=False));print(pd.read_csv(O/'coverage.csv').query('horizon==126').to_string(index=False))
