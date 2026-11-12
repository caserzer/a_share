import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,block_ci
OUT=EP/'restart/p32';OUT.mkdir(exist_ok=True);assert not (OUT/'selection_seal.json').exists()
source=EP/'restart/p31/cv2_feature_panel.parquet';q=pd.read_parquet(source);axis=pd.DatetimeIndex(sorted(q.date.unique()));q=q[q.candidate].copy();q['residual']=np.nan;fit=[]
for date,g in q.groupby('date'):
 if len(g)<30:continue
 x=np.column_stack([np.log(g.valid_members),g.breadth,g.mean21,g.rate60]);sd=x.std(axis=0);sd[sd==0]=1;x=(x-x.mean(axis=0))/sd;x=np.column_stack([np.ones(len(g)),x]);y=np.log1p(g.positive_gain_cv2);beta=np.linalg.lstsq(x,y,rcond=None)[0];res=y-x@beta;q.loc[g.index,'residual']=res;assert np.max(np.abs(x.T@res))<1e-8;fit.append(dict(date=date,rows=len(g),rank=int(np.linalg.matrix_rank(x))))
q=q[q.residual.notna()].copy();methods={'low_residual':('residual',True),'high_residual':('residual',False),'raw_low':('positive_gain_cv2',True),'momentum':('rate60',False)}
for name,(col,asc) in methods.items():
 a=q.sort_values(['date',col,'era','industry_code'],ascending=[True,asc,True,True]);q[name]=False;q.loc[a.index,name]=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
assert not (q.low_residual&q.high_residual).any();q.to_parquet(OUT/'selected_features.parquet',index=False);pd.DataFrame(fit).to_csv(OUT/'feature_fits.csv',index=False)
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,Path(__file__),EP/'restart/P32_dispersion_test_plan.md']},selection_sha256=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
ids=['era','industry_code','date'];labelsource=EP/'restart/p30/weekly_labels.parquet';labels=pd.read_parquet(labelsource);allfeatures=pd.read_parquet(EP/'restart/p30/training_panel.parquet',columns=ids+['eligible']);labels=labels.merge(allfeatures,on=ids,validate='one_to_one');strictsource=EP/'restart/p25/weekly_labels.parquet';strict=pd.read_parquet(strictsource);q=q.merge(labels[ids+[f'new_win{h}' for h in [63,126,252]]],on=ids,validate='one_to_one');q=q.merge(strict[ids+[f'new_win{h}' for h in [63,126,252]]],on=ids,how='left',validate='one_to_one',suffixes=('','_strict'));daily=[];summary=[]
for h in [63,126,252]:
 col=f'new_win{h}';base=labels[labels.eligible].groupby('date')[col].mean();candidate=q.groupby('date')[col].mean()
 for name in methods:
  z=q[q[name]]
  summary.append(dict(method=name,horizon=h,total=len(z),valued=int(z[col].notna().sum()),pooled_win=z[col].mean(),candidate_success_coverage=z[col].sum()/q[col].sum(),all_scored_success_coverage=z[col].sum()/labels.loc[labels.eligible&labels.date.isin(axis),col].sum(),median_observed_mean21=z.mean21.median()))
  for date,g in z.groupby('date'):
   good=g[f'{col}_strict'].notna()&g[col].notna();daily.append(dict(date=date,year=date.year,method=name,horizon=h,win=g[col].mean(),uplift_all=g[col].mean()-base.loc[date],uplift_candidate=g[col].mean()-candidate.loc[date],strict_common_win=g.loc[good,col].mean(),strict_common_rows=int(good.sum())))
a=pd.DataFrame(daily);a.to_csv(OUT/'daily.csv',index=False);a.groupby(['year','method','horizon'])[['win','uplift_all','uplift_candidate','strict_common_win']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False)
comp=[]
for h,g in a.groupby('horizon'):
 for metric in ['win','strict_common_win']:
  v=g.pivot(index='date',columns='method',values=metric).reindex(axis)
  for control in ['high_residual','raw_low','momentum']:
   delta=v.low_residual-v[control];lo,hi=block_ci(delta,26);comp.append(dict(horizon=h,metric=metric,control=control,dates=int(delta.notna().sum()),delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(comp).to_csv(OUT/'comparisons.csv',index=False);q.to_parquet(OUT/'evaluated.parquet',index=False)
for name in methods:assert q.groupby('date')[name].sum().equals(q.groupby('date').low_residual.sum())
assert sha(OUT/'selected_features.parquet')==json.loads((OUT/'selection_seal.json').read_text())['selection_sha256']
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',fit_dates=len(fit),selected_universe=len(q),equal_capacity=True,orthogonality_verified=True,label_hash=sha(labelsource),strict_label_hash=sha(strictsource)),indent=2)+'\n');print(pd.DataFrame(comp).query('horizon==126').to_string(index=False));print(a[a.horizon.eq(126)].groupby(['year','method'])[['win','uplift_all']].mean().to_string())
