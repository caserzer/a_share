import sys,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.base import clone
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p30';OUT.mkdir(exist_ok=True);assert not (OUT/'prediction_seal.json').exists();(OUT/'models').mkdir(exist_ok=True)
ids=['era','industry_code','date'];nf=EP/'restart/p29/daily_industries.parquet';lf=EP/'restart/p30/weekly_labels.parquet';oldf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');mf=oldf.parent/'CSI_ALL.parquet';modelpath=EP/'restart/p05/models/2024-01-01_B.joblib';op=EP/'restart/p13/predictions.parquet'
d=pd.read_parquet(nf);m=pd.read_parquet(mf).close.sort_index();cal=pd.DatetimeIndex(m.index);parts=[]
for _,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();x=np.log(g.nav/g.date.map(m))
 for h in [5,20,60]:g[f'rate{h}']=(x-x.shift(h))*5/h
 g['vol60']=x.diff().rolling(60).std();g['market126']=g.date.map(m/m.shift(126)-1);g['coverage']=g.anchor_coverage;parts.append(g[ids+['rate5','rate20','rate60','vol60','market126','coverage','members']])
f=pd.concat(parts,ignore_index=True);old=pd.read_parquet(oldf);old=old[old.level.eq('L3')];f=f.merge(old[ids+['volume_ratio']],on=ids,how='left',validate='one_to_one')
p=pd.read_parquet(lf).merge(f,on=ids,how='left',validate='one_to_one',suffixes=('','_feature'));bundle=joblib.load(modelpath);features=bundle['features'];p['eligible']=p.history60&np.isfinite(p[['rate5','rate20','rate60','vol60','market126','coverage','members']]).all(axis=1)
# Rebuilt known-price inputs versus old same-date complete-window features.
a=p[p.eligible].merge(pd.read_parquet(EP/'restart/p13/training_panel.parquet')[ids+features],on=ids,suffixes=('_new','_old'),validate='one_to_one');diff=[]
for c in features:
 n=a[c+'_new'] if c+'_new' in a else a[c];o=a[c+'_old'];same=np.isclose(n,o,equal_nan=True,atol=1e-10,rtol=1e-10);diff.append(dict(feature=c,rows=len(a),different=int((~same).sum()),max_abs_difference=float((n-o).abs().max())))
pd.DataFrame(diff).to_csv(OUT/'feature_reconciliation.csv',index=False);p.to_parquet(OUT/'training_panel.parquet',index=False)
pred=[];folds=[]
for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
 tr=p[p.eligible&p.new_win126.notna()&p.new_end126.lt(cut)];te=p[p.eligible&p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))];ok=len(tr)>=500 and tr.date.nunique()>=26 and tr.new_win126.nunique()==2
 folds.append(dict(cutoff=str(cut),train_rows=len(tr),train_dates=tr.date.nunique(),last_end=str(tr.new_end126.max()),test_rows=len(te),supported=ok,train_path_proxy=int(tr.path_proxy126.eq(1).sum()),train_endpoint_stale=int((tr.entry_stale126.eq(True)|tr.end_stale126.eq(True)).sum())))
 if not ok:continue
 model=clone(bundle['model']);weight=1/tr.groupby('date').date.transform('size').to_numpy();weight/=weight.mean();model.fit(tr[features],tr.new_win126.astype(int),sample_weight=weight);z=te[ids].copy();z['raw_score']=model.predict_proba(te[features])[:,1];z['fit_cutoff']=cut;pred.append(z);joblib.dump(dict(model=model,features=features),OUT/'models'/f'{cut.date()}.joblib',compress=3)
q=pd.concat(pred,ignore_index=True);q.to_parquet(OUT/'predictions.parquet',index=False);pd.DataFrame(folds).to_csv(OUT/'folds.csv',index=False)
inputs=[nf,lf,oldf,mf,modelpath,op,Path(__file__),EP/'restart/P30_proxy_baseline_plan.md']
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in inputs},artifacts={str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()}),indent=2)+'\n')
test=p[p.date.ge('2023-01-01')].copy();q=q.merge(test[ids+['block','day_i','rate60']+[f'new_win{h}' for h in [63,126,252]]],on=ids,validate='one_to_one')
axis=pd.DatetimeIndex(sorted(test.date.unique()));weekmap={x:i for i,x in enumerate(axis)};q['week_i']=q.date.map(weekmap);q=q.sort_values(['era','industry_code','block','date']).reset_index(drop=True);methods={'rebuilt':'raw_score','momentum':'rate60'};daily=[];events=[];rows=[]
for name,col in methods.items():
 a=q.sort_values(['date',col,'era','industry_code'],ascending=[True,False,True,True]);q[name]=False;q.loc[a.index,name]=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2));g=q.groupby(['era','industry_code','block']);continuous=q.week_i.sub(g.week_i.shift()).eq(1);prev=g[name].shift();q[name+'_edge']=q[name]&prev.eq(False)&continuous;q[name+'_boundary']=q[name]&~continuous
 for h in [63,126,252]:
  label=f'new_win{h}';base=q.groupby('date')[label].mean()
  for date,b in q[q[name]].groupby('date'):daily.append(dict(date=date,year=date.year,method=name,horizon=h,win=b[label].mean(),uplift=b[label].mean()-base.loc[date]))
  z=q[q[name+'_edge']];k=z[z[label].notna()];rows.append(dict(method=name,horizon=h,state_rows=int(q[name].sum()),edge_total=len(z),edge_known=len(k),edge_win=k[label].mean(),edge_uplift=(k[label]-k.date.map(base)).mean(),boundary=int(q[name+'_boundary'].sum()),known_success_week_coverage=q.loc[q[name],label].sum()/test[label].sum()))
  for year,b in k.groupby(k.date.dt.year):events.append(dict(method=name,horizon=h,year=year,known=len(b),win=b[label].mean(),uplift=(b[label]-b.date.map(base)).mean()))
a=pd.DataFrame(daily);a.to_csv(OUT/'daily.csv',index=False);a.groupby(['year','method','horizon'])[['win','uplift']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(events).to_csv(OUT/'annual_events.csv',index=False);q.to_parquet(OUT/'evaluated.parquet',index=False)
comparisons=[]
for h,g in a.groupby('horizon'):
 b=g.pivot(index='date',columns='method',values='win').reindex(axis)
 for control in ['momentum']:
  delta=b.rebuilt-b[control];lo,hi=block_ci(delta,26);comparisons.append(dict(horizon=h,control=control,delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
status=test[ids+['eligible']].merge(q[ids+['raw_score','rebuilt','rebuilt_edge','rebuilt_boundary']],on=ids,how='left',validate='one_to_one');status['status']=np.where(status.raw_score.notna(),'RESEARCH_SCORE_NOT_APPROVED','DATA_INSUFFICIENT');status.to_parquet(OUT/'catalog_status.parquet',index=False)
print(pd.DataFrame(diff).to_string(index=False));print(pd.DataFrame(folds).head(1).to_string(index=False));print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print(pd.DataFrame(comparisons).query('horizon==126').to_string(index=False))
