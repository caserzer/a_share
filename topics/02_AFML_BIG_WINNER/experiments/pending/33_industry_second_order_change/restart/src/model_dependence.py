import sys,json,warnings
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
warnings.simplefilter('error',ConvergenceWarning)
OUT=EP/'restart/p39';OUT.mkdir(exist_ok=True);assert not (OUT/'prediction_seal.json').exists();(OUT/'models').mkdir(exist_ok=True)
source=EP/'restart/p30/training_panel.parquet';treefile=EP/'restart/p30/predictions.parquet';bundlefile=EP/'restart/p05/models/2024-01-01_B.joblib';p=pd.read_parquet(source);p=p[p.eligible].copy();features=joblib.load(bundlefile)['features'];ids=['era','industry_code','date'];folds=[]
for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
 tr=p[p.new_win126.notna()&p.new_end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 assert len(tr)>=500 and tr.date.nunique()>=26 and tr.new_win126.nunique()==2
 folds.append(dict(cutoff=str(cut),rows=len(tr),dates=tr.date.nunique(),test_rows=len(te),max_end=str(tr.new_end126.max())))
pd.DataFrame(folds).to_csv(OUT/'feasibility.csv',index=False);pred=[];checks=0
for f in folds:
 cut=pd.Timestamp(f['cutoff']);tr=p[p.new_win126.notna()&p.new_end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),StandardScaler(),LogisticRegression(C=.1,max_iter=2000,random_state=3312))
 w=1/tr.groupby('date').date.transform('size').to_numpy();w/=w.mean();model.fit(tr[features],tr.new_win126.astype(int),logisticregression__sample_weight=w)
 path=OUT/'models'/f'{cut.date()}.joblib';joblib.dump(dict(model=model,features=features),path,compress=3);z=te[ids].copy();z['linear']=model.predict_proba(te[features])[:,1];z['cutoff']=cut
 saved=joblib.load(path);assert np.allclose(saved['model'].predict_proba(te[features].iloc[:10])[:,1],z.linear.iloc[:10]);checks+=min(10,len(te));pred.append(z)
q=pd.concat(pred,ignore_index=True);q.to_parquet(OUT/'predictions.parquet',index=False)
inputs=[source,treefile,bundlefile,Path(__file__),EP/'restart/P39_model_dependence_plan.md']
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in inputs},prediction_sha256=sha(OUT/'predictions.parquet')),indent=2)+'\n')
tree=pd.read_parquet(treefile);q=q.merge(tree[ids+['raw_score']],on=ids,validate='one_to_one').rename(columns={'raw_score':'tree'});assert len(q)==len(tree)
q=q.merge(p[ids+['block','rate60','rate20']+[f'new_win{h}' for h in [63,126,252]]],on=ids,validate='one_to_one');axis=pd.DatetimeIndex(sorted(q.date.unique()));q['week']=q.date.map({x:i for i,x in enumerate(axis)});q=q.sort_values(['era','industry_code','block','date']).reset_index(drop=True)
daily=[];events=[];comparisons=[]
for method,score in [('linear','linear'),('tree','tree'),('momentum','rate60')]:
 a=q.sort_values(['date',score,'era','industry_code'],ascending=[True,False,True,True]);q[method+'_selected']=False;q.loc[a.index,method+'_selected']=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
 g=q.groupby(['era','industry_code','block']);continuous=q.week.sub(g.week.shift()).eq(1);q[method+'_edge']=q[method+'_selected']&g[method+'_selected'].shift().eq(False)&continuous;q[method+'_boundary']=q[method+'_selected']&~continuous
 for h in [63,126,252]:
  label=f'new_win{h}';base=q.groupby('date')[label].mean();z=q[q[method+'_selected']];e=q[q[method+'_edge']];k=e[e[label].notna()]
  events.append(dict(method=method,horizon=h,edges=len(e),known=len(k),win=k[label].mean(),uplift=(k[label]-k.date.map(base)).mean(),boundary=int(q[method+'_boundary'].sum()),coverage=z[label].sum()/q[label].sum()))
  for date,b in z.groupby('date'):daily.append(dict(date=date,year=date.year,method=method,horizon=h,win=b[label].mean(),uplift=b[label].mean()-base.loc[date],not_positive_fraction=b.rate20.le(0).mean()))
d=pd.DataFrame(daily);d.to_csv(OUT/'daily.csv',index=False);d.groupby(['year','method','horizon'])[['win','uplift','not_positive_fraction']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(events).to_csv(OUT/'events.csv',index=False);q.to_parquet(OUT/'evaluated.parquet',index=False)
for h,b in d.groupby('horizon'):
 a=b.pivot(index='date',columns='method',values='win').reindex(axis)
 for c in ['tree','momentum']:
  delta=a.linear-a[c];lo,hi=block_ci(delta,26);comparisons.append(dict(horizon=h,control=c,delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
old=pd.read_parquet(EP/'restart/p30/evaluated.parquet');a=q.merge(old[ids+['rebuilt','rebuilt_edge']],on=ids,validate='one_to_one');assert a.tree_selected.eq(a.rebuilt).all() and a.tree_edge.eq(a.rebuilt_edge).all()
for _,b in q.groupby('date'):assert len({int(b[m+'_selected'].sum()) for m in ['linear','tree','momentum']})==1
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',saved_model_checks=checks,tree_selection_reconciled=len(q),folds=len(folds),artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n')
print(pd.DataFrame(comparisons).to_string(index=False));print(pd.DataFrame(events).query('horizon==126').to_string(index=False))
