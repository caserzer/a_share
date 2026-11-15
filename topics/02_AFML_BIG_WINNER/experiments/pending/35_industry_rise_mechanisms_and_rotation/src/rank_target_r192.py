"""One fixed model contrast: magnitude versus cross-sectional rank target."""
from common import *
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from refit_r131 import prepare, predict_saved, FK
from train_r02 import train_masks,sample_weights
K=['era','level','cohort','method','horizon','year']

def run():
 out=ROOT/'outputs/r192';out.mkdir(exist_ok=True)
 panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');panel['log_members']=np.log(panel.members.where(panel.members.gt(0)))
 models=json.loads((ROOT/'outputs/r131/model_parameters.json').read_text());old=pd.read_parquet(ROOT/'outputs/r131/predictions.parquet');parts=[];params=[];ledger=[];maxerr=0.;maxsaved=0.
 for m in models:
  if m['task']!='return':continue
  ident={k:m[k] for k in K};h=m['horizon'];year=m['year']
  q,ranks=prepare(panel,m['era'],m['level'],m['cohort'],'return',h);fit,_,test=train_masks(q,year,h,'return');tr=q[fit];te=q[test]
  assert len(tr)>=300 and tr.date.nunique()>=18 and tr[f'maturity{h}'].max()<pd.Timestamp(year,1,1)
  y_rank=tr.groupby('date').y.transform(centered_rank)
  scaler=StandardScaler().fit(ranks.loc[tr.index,m['columns']]);x=scaler.transform(ranks.loc[tr.index,m['columns']]);xt=scaler.transform(ranks.loc[te.index,m['columns']]);w=sample_weights(tr).to_numpy()
  assert np.allclose(scaler.mean_,m['scaler_mean'],atol=1e-12) and np.allclose(scaler.scale_,m['scaler_scale'],atol=1e-12)
  pred={}
  design=np.column_stack([np.ones(len(x)),x]);testdesign=np.column_stack([np.ones(len(xt)),xt]);penalty=np.diag([0.]+[10.]*x.shape[1])
  for target,y in [('raw',tr.y.to_numpy()),('rank',y_rank.to_numpy())]:
   model=Ridge(alpha=10).fit(x,y,sample_weight=w);yp=model.predict(xt)
   coef=np.linalg.solve(design.T@(w[:,None]*design)+penalty,design.T@(w*y));check=testdesign@coef
   err=float(np.max(np.abs(check-yp)));assert err<1e-10;maxerr=max(maxerr,err)
   pred[target]=yp
   params.append(dict(ident,target=target,columns=m['columns'],coefficient=model.coef_.tolist(),intercept=float(model.intercept_),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist()))
  saved,_=predict_saved(m,ranks.loc[te.index,m['columns']]);err=float(np.max(np.abs(saved-pred['raw'])));assert err<1e-10;maxsaved=max(maxsaved,err)
  a=te[KEY+['date','y',f'maturity{h}']].rename(columns={f'maturity{h}':'maturity'}).copy();a=a.assign(**{k:v for k,v in ident.items() if k not in KEY},raw_score=pred['raw'],rank_score=pred['rank'],momentum_score=te.mom60)
  original=old[old.task.eq('return')]
  for k,v in ident.items():original=original[original[k].eq(v)]
  pair=a.merge(original,on=KEY+['date'],suffixes=('','_original'),validate='one_to_one');assert len(pair)==len(a)==len(original)
  assert np.allclose(pair.raw_score,pair.prediction,atol=1e-10) and np.allclose(pair.y,pair.y_original,equal_nan=True)
  parts.append(a);ledger.append(dict(ident,fit_rows=len(tr),fit_dates=tr.date.nunique(),test_rows=len(te),test_unknown=int(te.y.isna().sum()),fit_max_maturity=str(tr[f'maturity{h}'].max()),min_rank_training_cross_section=int(tr.groupby('date').size().min())))
 result=pd.concat(parts,ignore_index=True);result.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',params);pd.DataFrame(ledger).to_csv(out/'fold_ledger.csv',index=False)
 rows=[]
 for key,g in result.groupby(K+['date']):
  rec=dict(zip(K+['date'],key));v=g[g.y.notna()];n=max(1,int(np.ceil(len(g)*.2)))
  for method in ['raw','rank','momentum']:
   c=method+'_score';rec[method+'_ic']=v[c].corr(v.y,method='spearman') if len(v)>=20 and v[c].nunique()>1 and v.y.nunique()>1 else np.nan
   top=g.sort_values([c,'industry_code'],ascending=[False,True]).head(n);rec[method+'_top']=top.y.mean() if top.y.notna().all() else np.nan;rec[method+'_top_unknown']=int(top.y.isna().sum())
  rec.update(n_signal=len(g),n_mature=len(v),top_n=n);rows.append(rec)
 dates=pd.DataFrame(rows);dates.to_csv(out/'date_metrics.csv',index=False);summaries=[]
 for group in [K,K[:-1]]:
  for key,g in dates.groupby(group):
   ident=dict(zip(group,key));ident.setdefault('year','all')
   for baseline in ['raw','momentum']:
    z=g.dropna(subset=['rank_ic',baseline+'_ic']);top=g.dropna(subset=['rank_top',baseline+'_top'])
    summaries.append(dict(ident,baseline=baseline,dates=len(g),ic_dates=len(z),rank_ic=z.rank_ic.mean(),baseline_ic=z[baseline+'_ic'].mean(),delta_ic=(z.rank_ic-z[baseline+'_ic']).mean(),paired_top_dates=len(top),delta_top=(top.rank_top-top[baseline+'_top']).mean(),unknown_top_pairs=len(g)-len(top)))
 pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
 inputs=['outputs/r130/monthly_panel.parquet','outputs/r131/model_parameters.json','outputs/r131/predictions.parquet','protocols/r192.json','src/rank_target_r192.py','src/refit_r131.py','src/train_r02.py','src/common.py'];files=['predictions.parquet','models.json','fold_ledger.csv','date_metrics.csv','summary.csv']
 js(out/'verification.json',dict(status='PASS',scope='Same cohorts/maturity gates, scaler and original prediction reproduction, independent weighted normal equations both targets',new_rank_models=len(ledger),raw_control_refits=len(ledger),prediction_rows=len(result),max_normal_equation_prediction_error=maxerr,max_saved_raw_prediction_error=maxsaved,adoption=False,inputs={x:sha(ROOT/x) for x in inputs},outputs={x:sha(out/x) for x in files}))
 print('DONE',len(ledger),'rank models',len(result),'prediction rows',maxerr,maxsaved)
if __name__=='__main__':run()
