import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
from sklearn.metrics import roc_auc_score
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p45';OUT.mkdir(exist_ok=True);assert not (OUT/'prediction_seal.json').exists()
base=EP/'restart/p30';mf=base/'models/2023-01-01.joblib';tf=base/'training_panel.parquet';pf=base/'predictions.parquet';bundle=joblib.load(mf);ids=['era','industry_code','date'];p=pd.read_parquet(tf,columns=ids+['eligible']+bundle['features']);p=p[p.eligible&p.date.ge('2023-01-01')].copy();q=p[ids+['rate60']].copy();q['fixed']=bundle['model'].predict_proba(p[bundle['features']])[:,1];old=pd.read_parquet(pf);q=q.merge(old[ids+['raw_score']],on=ids,validate='one_to_one').rename(columns={'raw_score':'updated'});assert len(q)==len(old)
first=q.date.lt('2023-04-01');assert np.allclose(q.loc[first,'fixed'],q.loc[first,'updated'],atol=1e-12,rtol=0)
fold=pd.read_csv(base/'folds.csv').iloc[0];assert pd.Timestamp(fold.last_end)<pd.Timestamp('2023-01-01')
q.to_parquet(OUT/'scores.parquet',index=False);inputs=[mf,tf,pf,base/'folds.csv',Path(__file__),EP/'restart/P45_fixed_ruler_plan.md'];(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in inputs},scores_sha256=sha(OUT/'scores.parquet'),q1_prediction_checks=int(first.sum())),indent=2)+'\n')
labels=[f'new_win{h}' for h in [63,126,252]];y=pd.read_parquet(tf,columns=ids+labels);q=q.merge(y,on=ids,validate='one_to_one');axis=pd.DatetimeIndex(sorted(q.date.unique()));daily=[]
for date,g in q.groupby('date'):
 k=int(np.ceil(len(g)*.2))
 for method,score in [('fixed','fixed'),('updated','updated'),('momentum','rate60')]:
  selected=g.sort_values([score,'era','industry_code'],ascending=[False,True,True]).head(k)
  for h in [63,126,252]:
   label=f'new_win{h}';v=g[g[label].notna()];both=v[label].nunique()==2;auc=roc_auc_score(v[label],v[score]) if both else np.nan
   daily.append(dict(date=date,year=date.year,method=method,horizon=h,known=len(v),both_classes=both,auc=auc,win=selected[label].mean(),base=g[label].mean(),uplift=selected[label].mean()-g[label].mean()))
d=pd.DataFrame(daily);d.to_csv(OUT/'daily.csv',index=False);rows=[]
for (method,h),b in d.groupby(['method','horizon']):
 for year in ['ALL',2023,2024,2025,2026]:
  a=b if year=='ALL' else b[b.year.eq(year)];ax=axis if year=='ALL' else axis[axis.year==year];lo,hi=block_ci(a.set_index('date').uplift.reindex(ax),26);al,ah=block_ci((a.set_index('date').auc-.5).reindex(ax),26)
  rows.append(dict(year=year,method=method,horizon=h,valued_dates=int(a.known.gt(0).sum()),auc_dates=int(a.both_classes.sum()),auc=a.auc.mean(),auc_lo=al+.5,auc_hi=ah+.5,win=a.win.mean(),base=a.base.mean(),uplift=a.uplift.mean(),lo=lo,hi=hi))
r=pd.DataFrame(rows);r.to_csv(OUT/'summary.csv',index=False)
# Tie-aware Mann-Whitney rank identity, independent of sklearn implementation.
checks=0
for date,g in q.groupby('date'):
 v=g[g.new_win126.notna()]
 if v.new_win126.nunique()!=2:continue
 for method in ['fixed','updated']:
  ranks=v[method].rank(method='average');n1=int(v.new_win126.sum());n0=len(v)-n1;auc=(ranks[v.new_win126.eq(1)].sum()-n1*(n1+1)/2)/(n1*n0)
  z=d[d.date.eq(date)&d.method.eq(method)&d.horizon.eq(126)];assert np.isclose(auc,z.auc.iloc[0]);checks+=1
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',auc_identity_checks=checks,test_rows=len(q),artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n');print(r[r.horizon.eq(126)].to_string(index=False))
