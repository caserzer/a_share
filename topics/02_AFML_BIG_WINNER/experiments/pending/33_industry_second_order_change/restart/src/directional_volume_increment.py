import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
from sklearn.base import clone
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p64';OUT.mkdir(exist_ok=True);assert not (OUT/'prediction_seal.json').exists()
(OUT/'models').mkdir(exist_ok=True)
ids=['era','industry_code','date'];source=EP/'restart/p30/training_panel.parquet';pf=EP/'restart/p63/features.parquet';bf=EP/'restart/p05/models/2024-01-01_B.joblib'
p=pd.read_parquet(source);f=pd.read_parquet(pf);extra=['volume_mean60','volume_std60','up_fraction60','directional_volume60']
p=p.merge(f[ids+extra+['supported']],on=ids,how='left',validate='one_to_one');full=p[p.eligible&p.date.ge('2023-01-01')].copy();p=p[p.eligible&p.supported.eq(True)].copy();assert np.isfinite(p[extra]).all().all()
bundle=joblib.load(bf);features={'B':bundle['features'],'M':bundle['features']+extra[:3],'P':bundle['features']+extra}
folds=[]
for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
 tr=p[p.new_win126.notna()&p.new_end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 folds.append(dict(cutoff=str(cut),rows=len(tr),dates=tr.date.nunique(),test_rows=len(te),last_end=str(tr.new_end126.max()),supported=len(tr)>=500 and tr.date.nunique()>=26 and tr.new_win126.nunique()==2))
pd.DataFrame(folds).to_csv(OUT/'feasibility.csv',index=False);assert all(r['supported'] for r in folds)
pd.DataFrame([dict(horizon=h,full_success=full[f'new_win{h}'].sum(),supported_success=p.loc[p.date.ge('2023-01-01'),f'new_win{h}'].sum()) for h in [63,126,252]]).to_csv(OUT/'coverage_upper.csv',index=False)
assert p.loc[p.date.ge('2023-01-01'),'new_win126'].sum()/full.new_win126.sum()>=.1
pred=[]
for row in folds:
 cut=pd.Timestamp(row['cutoff']);tr=p[p.new_win126.notna()&p.new_end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 weight=1/tr.groupby('date').date.transform('size').to_numpy();weight/=weight.mean();z=te[ids].copy();z['cutoff']=cut
 for name,cols in features.items():
  model=clone(bundle['model']);model.fit(tr[cols],tr.new_win126.astype(int),sample_weight=weight);z[name]=model.predict_proba(te[cols])[:,1];joblib.dump(dict(model=model,features=cols),OUT/'models'/f'{cut.date()}_{name}.joblib',compress=3)
 pred.append(z);print('completed',cut.date(),flush=True)
q=pd.concat(pred,ignore_index=True);q.to_parquet(OUT/'predictions.parquet',index=False)
inputs=[source,pf,bf,Path(__file__),EP/'restart/P64_directional_volume_increment_plan.md']
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in inputs},prediction_sha256=sha(OUT/'predictions.parquet')),indent=2)+'\n')
q=q.merge(p[ids+['block','rate20','rate60','history_proxy60']+[f'new_win{h}' for h in [63,126,252]]],on=ids,validate='one_to_one');axis=pd.DatetimeIndex(sorted(full.date.unique()));q['week']=q.date.map({d:i for i,d in enumerate(axis)});q=q.sort_values(['era','industry_code','block','date']).reset_index(drop=True)
daily=[];events=[];coverage=[]
for method,score in [('B','B'),('M','M'),('P','P'),('momentum','rate60')]:
 a=q.sort_values(['date',score,'era','industry_code'],ascending=[True,False,True,True]);q[method+'_selected']=False;q.loc[a.index,method+'_selected']=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
 g=q.groupby(['era','industry_code','block']);continuous=q.week.sub(g.week.shift()).eq(1);q[method+'_edge']=q[method+'_selected']&g[method+'_selected'].shift().eq(False)&continuous
 for h in [63,126,252]:
  label=f'new_win{h}';base=q.groupby('date')[label].mean();allbase=full.groupby('date')[label].mean();z=q[q[method+'_selected']]
  for date,b in z.groupby('date'):
   daily.append(dict(date=date,year=date.year,horizon=h,method=method,win=b[label].mean(),uplift=b[label].mean()-base.loc[date],uplift_full=b[label].mean()-allbase.loc[date],not_positive_fraction=b.rate20.le(0).mean()))
  e=q[q[method+'_edge']];k=e[e[label].notna()]
  events.append(dict(method=method,horizon=h,edges=len(e),known=len(k),win=k[label].mean(),uplift=(k[label]-k.date.map(allbase)).mean()))
  coverage.append(dict(method=method,horizon=h,full_success_coverage=z[label].sum()/full[label].sum(),supported_success_coverage=z[label].sum()/q[label].sum()))
d=pd.DataFrame(daily);d.to_csv(OUT/'daily.csv',index=False);d.groupby(['year','method','horizon'])[['win','uplift','uplift_full','not_positive_fraction']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(events).to_csv(OUT/'events.csv',index=False);pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False);q.to_parquet(OUT/'evaluated.parquet',index=False)
comparisons=[]
for h,b in d.groupby('horizon'):
 a=b.pivot(index='date',columns='method',values='win').reindex(axis)
 for control in ['M','B','momentum']:
  delta=a.P-a[control];lo,hi=block_ci(delta,26);comparisons.append(dict(horizon=h,control=control,delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
# Saved-model replays; selections identical capacity on every date.
checks=0
for row in folds:
 cut=pd.Timestamp(row['cutoff']);sample=q[q.cutoff.eq(cut)].sample(min(5,len(q[q.cutoff.eq(cut)])),random_state=3336)
 x=sample[ids].merge(p,on=ids,validate='one_to_one')
 for name in features:
  b=joblib.load(OUT/'models'/f'{cut.date()}_{name}.joblib');assert np.allclose(b['model'].predict_proba(x[b['features']])[:,1],sample[name]);checks+=len(sample)
for _,b in q.groupby('date'):
 assert len({int(b[m+'_selected'].sum()) for m in ['B','M','P','momentum']})==1
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',prediction_replays=checks,folds=len(folds),same_capacity=True,artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n')
print(pd.DataFrame(comparisons).to_string(index=False));print(pd.DataFrame(events).query('horizon==126').to_string(index=False))
