import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,block_ci
OUT=EP/'restart/p19';OUT.mkdir(exist_ok=True);assert not (OUT/'prediction_seal.json').exists(),'sealed';(OUT/'models').mkdir(exist_ok=True)
cache=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5');raw=cache/'daily_industries.parquet';mf=cache/'CSI_ALL.parquet';oldfile=EP/'restart/p13/training_panel.parquet';bf=EP/'restart/p18/date_features.parquet'
m=pd.read_parquet(mf).close.sort_index();cal=pd.DatetimeIndex(m.index);s=pd.Series(cal,index=cal);weeks=s.groupby(s.index.to_period('W-FRI')).max();weeks=weeks[[x.end_time.normalize()<=cal.max() for x in weeks.index]]
d=pd.read_parquet(raw);d=d[d.level.eq('L3')];chunks=[];full=[]
for _,g in d.groupby(KEY):
 g=g.sort_values('date').copy();assert np.all(np.diff(cal.get_indexer(g.date))==1)
 ok=g.coverage.ge(.8)&g.members.ge(5)&g.nav.shift(60).notna();r=g.nav/g.nav.shift(21)-1
 g['eligible']=ok;g['common']=ok&ok.shift(21,fill_value=False)&r.notna()&r.shift(21).notna();g['now']=r.gt(0);g['before']=r.shift(21).gt(0)
 full.append(g.loc[g.date.isin(weeks),['date','eligible','common','now','before']]);bm=g.date.map(m)
 for h in [63,126,252]:
  ret=g.nav.shift(-h-1)/g.nav.shift(-1)-1;mr=bm.shift(-h-1)/bm.shift(-1)-1;end=g.date.shift(-h-1)
  g[f'end{h}']=end;g[f'joint{h}']=(ret.gt(0)&ret.gt(mr)).astype(float).where(end.notna());g[f'absolute{h}']=ret.gt(0).astype(float).where(end.notna())
 chunks.append(g.loc[ok&g.date.isin(weeks),ID+[c for h in [63,126,252] for c in [f'end{h}',f'joint{h}',f'absolute{h}']]])
p=pd.concat(chunks,ignore_index=True);old=pd.read_parquet(oldfile);v=p.merge(old[ID+['win126','end126']],on=ID,how='outer',indicator=True,suffixes=('','_old'),validate='one_to_one');assert v._merge.eq('both').all();assert np.allclose(v.joint126,v.win126,equal_nan=True);assert (v.end126.eq(v.end126_old)|(v.end126.isna()&v.end126_old.isna())).all()
f=pd.concat(full,ignore_index=True);b=f[f.common].groupby('date').agg(breadth_now=('now','mean'),breadth_before=('before','mean'),n_common=('date','size'));b['change']=b.breadth_now-b.breadth_before
x=pd.DataFrame(index=pd.DatetimeIndex(weeks.to_numpy(),name='date'));x['market21']=(m/m.shift(21)-1).reindex(x.index);x['market126']=(m/m.shift(126)-1).reindex(x.index);x['vol21']=np.log(m).diff().rolling(21).std().reindex(x.index);x=x.join(b)
prev=pd.read_parquet(bf).set_index('date');assert np.allclose(x.loc[prev.index,['breadth_now','change','n_common']],prev[['breadth_now','change','n_common']])
x.to_parquet(OUT/'features.parquet');targets=[]
for h in [63,126,252]:
 t=p.groupby('date').agg(total=('date','size'),known=(f'joint{h}','count'),joint=(f'joint{h}','mean'),absolute=(f'absolute{h}','mean'));t['coverage']=t.known/t.total;t['end']=pd.Series(cal,index=cal).shift(-h-1).reindex(t.index);t.loc[t.coverage.lt(.95)|t.end.isna(),['joint','absolute']]=np.nan;t['horizon']=h;targets.append(t.reset_index())
y=pd.concat(targets,ignore_index=True);y.to_parquet(OUT/'targets.parquet',index=False)
features={'M':['market21','market126','vol21'],'MB':['market21','market126','vol21','breadth_now','change']};pred=[];folds=[]
for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
 for h in [63,126,252]:
  t=y[y.horizon.eq(h)].set_index('date').join(x);te=x[(x.index>=cut)&(x.index<cut+pd.DateOffset(months=3))]
  for target in ['joint','absolute']:
   tr=t[t.end.lt(cut)&t[target].notna()].dropna(subset=features['MB']);supported=len(tr)>=104
   folds.append(dict(cutoff=str(cut),horizon=h,target=target,train_dates=len(tr),last_end=str(tr.end.max()),supported=supported,test_dates=len(te)))
   if not supported:continue
   for name in ['H','M','MB']:
    valid=te.dropna(subset=features['MB']);cols=features.get(name,[])
    if name=='H':model=float(tr[target].mean());values=np.repeat(model,len(valid))
    else:model=make_pipeline(StandardScaler(),Ridge(alpha=10));model.fit(tr[cols],tr[target]);values=np.clip(model.predict(valid[cols]),0,1)
    filename=f'{cut.date()}_{h}_{target}_{name}.joblib';joblib.dump(dict(model=model,features=cols,cutoff=cut,horizon=h,target=target),OUT/'models'/filename)
    for date,value in zip(valid.index,values):pred.append(dict(date=date,cutoff=cut,horizon=h,target=target,model=name,prediction=value,model_file=filename))
q=pd.DataFrame(pred);q.to_parquet(OUT/'predictions.parquet',index=False);pd.DataFrame(folds).to_csv(OUT/'folds.csv',index=False)
inputs=[raw,mf,oldfile,bf,Path(__file__),EP/'restart/P19_date_opportunity_plan.md']
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in inputs},artifacts={str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()}),indent=2)+'\n')
long=y.melt(id_vars=['date','horizon','coverage','end'],value_vars=['joint','absolute'],var_name='target',value_name='actual');q=q.merge(long,on=['date','horizon','target'],validate='many_to_one');q['squared_error']=(q.prediction-q.actual)**2;q['year']=q.date.dt.year;q.to_parquet(OUT/'evaluated.parquet',index=False)
q.groupby(['year','horizon','target','model']).agg(dates=('date','size'),mature=('actual','count'),actual=('actual','mean'),prediction=('prediction','mean'),mse=('squared_error','mean')).to_csv(OUT/'annual.csv')
rows=[];axis=x.index[x.index>=pd.Timestamp('2023-01-01')]
for (h,target),g in q.groupby(['horizon','target']):
 v=g.pivot(index='date',columns='model',values='squared_error').reindex(axis)
 for control in ['M','H']:
  delta=v.MB-v[control];lo,hi=block_ci(delta,26)
  rows.append(dict(horizon=h,target=target,control=control,dates=int(delta.notna().sum()),mse_mb=v.MB.mean(),mse_control=v[control].mean(),delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(rows).to_csv(OUT/'comparisons.csv',index=False)
# Saved-model replay and maturity verification, using each fold's own raw target dates.
for _,row in q.drop_duplicates('model_file').iterrows():
 bundle=joblib.load(OUT/'models'/row.model_file);cols=bundle['features'];model=bundle['model'];value=model if not cols else float(np.clip(model.predict(x.loc[[row.date],cols])[0],0,1));assert np.isclose(value,row.prediction)
for fold in folds:
 if fold['supported']:assert pd.Timestamp(fold['last_end'])<pd.Timestamp(fold['cutoff'])
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',industry_label_rows=len(p),p13_identity_and_label_match=True,p18_feature_dates=len(prev),model_replays=q.model_file.nunique(),fold_maturity_checks=len(folds)),indent=2)+'\n')
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print(q.query('horizon==126 and target=="joint"').groupby(['year','model']).agg(actual=('actual','mean'),prediction=('prediction','mean'),mse=('squared_error','mean')).to_string())
