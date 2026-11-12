import sys,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'src'));from pool_evaluation import block_ci
O=R/'p61';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
pf=R/'p19/predictions.parquet';of=R/'p19/targets.parquet';nf=R/'p59/daily.csv'
p=pd.read_parquet(pf);old=pd.read_parquet(of);new=pd.read_csv(nf,parse_dates=['date']);new['joint']=new.success;new['absolute']=1-new.nonpositive;new.loc[new.known/new.total<.95,['joint','absolute']]=np.nan
old=old[['date','horizon','joint','absolute']].melt(id_vars=['date','horizon'],var_name='target',value_name='old_actual');new=new[['date','horizon','joint','absolute']].melt(id_vars=['date','horizon'],var_name='target',value_name='new_actual')
q=p.merge(old,on=['date','horizon','target'],how='left',validate='many_to_one').merge(new,on=['date','horizon','target'],how='left',validate='many_to_one');q.to_parquet(O/'evaluated.parquet',index=False);axis=pd.DatetimeIndex(sorted(p.date.unique()));assert len(axis)==194
metrics=[];comp=[];annual=[]
for (h,t),g in q.groupby(['horizon','target']):
 for version in ['old','new']:
  g=g.copy();g['loss']=(g.prediction-g[version+'_actual'])**2
  v=g.pivot(index='date',columns='model',values='loss').reindex(axis)
  for model,z in g.groupby('model'):
   metrics.append(dict(horizon=h,target=t,version=version,model=model,dates=int(z.loss.notna().sum()),mse=z.loss.mean()))
   for yr,b in z.groupby(z.date.dt.year):annual.append(dict(horizon=h,target=t,version=version,model=model,year=yr,dates=int(b.loss.notna().sum()),mse=b.loss.mean(),actual=b.loc[b.loss.notna(),version+'_actual'].mean()))
  for ctrl in ['H','M']:
   d=v.MB-v[ctrl];lo,hi=block_ci(d,26);comp.append(dict(horizon=h,target=t,version=version,control=ctrl,delta=d.mean(),lo=lo,hi=hi))
a=pd.DataFrame(metrics);c=pd.DataFrame(comp);a.to_csv(O/'metrics.csv',index=False);c.to_csv(O/'comparisons.csv',index=False);pd.DataFrame(annual).to_csv(O/'annual.csv',index=False)
d=q[q.model.eq('H')].copy();d['delta']=d.new_actual-d.old_actual;d.groupby(['horizon','target']).agg(dates=('delta','count'),mean_delta=('delta','mean'),mean_abs_delta=('delta',lambda x:x.abs().mean()),max_abs_delta=('delta',lambda x:x.abs().max())).to_csv(O/'target_changes.csv')
orig=pd.read_csv(R/'p19/comparisons.csv');checks=0
for _,v in c[c.version.eq('old')].iterrows():
 b=orig[(orig.horizon==v.horizon)&(orig.target==v.target)&(orig.control==v.control)].iloc[0]
 for col in ['delta','lo','hi']:assert np.isclose(v[col],b[col]);checks+=1
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=[pf,of,nf,R/'p19/comparisons.csv',R/'P61_market_target_version_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',old_statistics_reproduced=checks,inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.iterdir() if p.is_file()}),indent=2)+'\n');print(a.query('horizon==126').to_string(index=False));print(c.query('horizon==126 and version=="new"').to_string(index=False))
