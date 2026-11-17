"""Exact frozen E1 score explanation by existing price-state classes; no outcomes."""
import __main__,pickle,json
from pathlib import Path
import numpy as np
import pandas as pd
from train import TrainTransform
from common import EP,OUT,PRIVATE,sha,save_json
__main__.TrainTransform=TrainTransform
D=OUT/'diagnostics/e1_selection_explanation_20261117';D.mkdir(exist_ok=True)
statepath=PRIVATE/'e1_timing_mechanism_20261117/states.parquet'
fpath=PRIVATE/'features.parquet';dictpath=OUT/'diagnostics/e1_alpha_mechanism_20261117/feature_groups.csv';mpath=OUT/'manifests/expanding_predictions.json'
s=pd.read_parquet(statepath);s=s[s.E1.notna()].copy();f=pd.read_parquet(fpath);dd=pd.read_csv(dictpath);cols=dd.feature.tolist();rows=[];co=[];receipts=[]
for rec in json.loads(mpath.read_text()):
 dates=s.loc[s.signal_date.dt.to_period('Q').astype(str).eq(rec['fold']),'signal_date'].unique()
 if not len(dates):continue
 m=next(m for m in rec['models'] if m['model']=='E1');assert sha(m['path'])==m['sha256'];receipts.append(m)
 tr,model=pickle.loads(Path(m['path']).read_bytes());a=f[f.signal_date.isin(dates)&f.score_eligible].copy();v=tr.transform(a[cols])*model.coef_
 q=a[['signal_date','instrument']].merge(s[['signal_date','instrument','E1','state','industry','target_weight']],on=['signal_date','instrument'],validate='one_to_one')
 assert len(q)==len(a) and np.allclose(v.sum(axis=1)+model.intercept_,q.E1,atol=1e-10)
 for j,c in enumerate(cols):q['c_'+c]=v[:,j];q['raw_'+c]=a[c].to_numpy();co.append(dict(fold=rec['fold'],feature=c,coef=model.coef_[j]))
 for group,g in dd.groupby('mechanism_group'):q[group]=v[:,dd.mechanism_group.eq(group)].sum(axis=1)
 rows.append(q)
a=pd.concat(rows,ignore_index=True);groups=dd.mechanism_group.unique().tolist();contrast=[];coverage=[];removal=[]
for date,g in a.groupby('signal_date'):
 selected=g.target_weight>0;k=int(selected.sum())
 for group in groups:
  # Centering preserves the date-common score level; only removes cross-stock variation.
  counter=g.E1-g[group]+g[group].mean();order=np.lexsort((g.instrument.to_numpy(),-counter.to_numpy()));picked=set(g.iloc[order[:k]].instrument)
  for st,h in g[selected].groupby('state'):removal.append(dict(signal_date=date,state=st,group=group,selected=len(h),lost=int((~h.instrument.isin(picked)).sum())))
 for (st,industry),h in g.groupby(['state','industry']):
  sel=h[h.target_weight>0];peer=h[h.target_weight.eq(0)]
  if not len(sel):continue
  supported=len(peer)>0 and industry!='UNKNOWN';coverage.append(dict(signal_date=date,state=st,industry=industry,budget=sel.target_weight.sum(),supported=supported,selected=len(sel),peers=len(peer)))
  if not supported:continue
  for name in ['E1']+groups+['c_'+c for c in cols]+['raw_'+c for c in cols]:contrast.append(dict(signal_date=date,state=st,industry=industry,metric=name,difference=sel[name].mean()-peer[name].mean(),budget=sel.target_weight.sum()))
c=pd.DataFrame(contrast);cv=pd.DataFrame(coverage);out=[]
for (st,metric),h in c.groupby(['state','metric']):
 out.append(dict(state=st,metric=metric,weighted_difference=np.average(h.difference,weights=h.budget),groups=len(h),budget=h.budget.sum()))
z=pd.DataFrame(out);z.to_csv(D/'conditional_score_difference.csv',index=False);c.to_csv(D/'conditional_score_detail.csv',index=False);cv.to_csv(D/'coverage.csv',index=False)
pd.DataFrame(co).to_csv(D/'coefficients.csv',index=False);rem=pd.DataFrame(removal);rem.to_csv(D/'group_removal.csv',index=False)
r=rem.groupby(['state','group'],as_index=False)[['selected','lost']].sum();r['lost_fraction']=r.lost/r.selected;r.to_csv(D/'group_removal_summary.csv',index=False)
# Original score decomposition exactly adds in each conditional comparison.
p=z[z.metric.isin(groups)].groupby('state').weighted_difference.sum();baseline=z[z.metric.eq('E1')].set_index('state').weighted_difference;assert np.allclose(p.reindex(baseline.index),baseline,atol=1e-10)
save_json(D/'receipt.json',dict(status='PASS',scope='50 original monthly signals; known industry and same frozen price state, selected minus unselected; capital-weighted across date-industry-state cells',no_future_returns_read=True,score_units='original target standardized-score units, not expected return percent',attribution='correlated features; exact score arithmetic not unique economic causation; group removal fixed coefficients, no retraining, no return evaluation',files=[dict(path=str(x),sha256=sha(x)) for x in [statepath,fpath,dictpath,mpath,Path(__file__)]],models=receipts,rows=len(a),selected=int(a.target_weight.gt(0).sum())))
print(z[z.metric.isin(['E1']+groups)].pivot(index='state',columns='metric',values='weighted_difference').round(5).to_string())
for st in ['DOWN_DOWN','UP_DOWN','DOWN_UP','UP_UP']:
 h=z[z.state.eq(st)&z.metric.str.startswith('c_')];print('\n',st);print(h.nlargest(5,'weighted_difference')[['metric','weighted_difference']].to_string(index=False));print('negative');print(h.nsmallest(3,'weighted_difference')[['metric','weighted_difference']].to_string(index=False))
print('REMOVAL');print(r[r.state.isin(['DOWN_DOWN','UP_DOWN','DOWN_UP','UP_UP'])].pivot(index='state',columns='group',values='lost_fraction').round(3).to_string())
