"""Frozen state conditioning of all fixed-FY EPS/profit prediction branches."""
from common import *
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from train_r02 import F,sample_weights
from expectation_r29 import eligible_training
from regime_core_r196 import arrays
GROUP=['family','era','level','fy_offset','population','horizon']

def run():
 out=ROOT/'outputs/r197';out.mkdir(exist_ok=True)
 states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
 panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet')
 l1=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')
 parts=[];models=[];ledger=[];maxerr=0.;original_error=0.;original_rows=0
 sources=[('eps_'+v,f'data/r29_{v}_coverage.parquet',f'outputs/r141/evaluation/outputs/r29/{v}/predictions.parquet') for v in ['raw_proxy','share_context_guard']]+[('profit_expectations','data/r25_revision_coverage.parquet','outputs/r162/evaluation/outputs/r25/predictions.parquet')]
 for family,covpath,oldpath in sources:
  p=pd.concat([panel,l1],ignore_index=True) if family.startswith('eps_') else panel.copy()
  p['log_members']=np.log(p.members)
  cov=pd.read_parquet(ROOT/covpath);merged=cov.merge(p,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one')
  assert merged.members_coverage.gt(0).all()
  base=merged[merged.price_ready].dropna(subset=F+['covered_member_median'])
  for (era,level,offset),v in base.groupby(['era','level','fy_offset']):
   for population,mask in [('strict',v.eligible),('partial_diagnostic',v.known.ge(5)&~v.eligible)]:
    g=v[mask].copy();g['expectation']=g.covered_member_median;g=g[g.groupby('date').date.transform('size').ge(2)]
    if g.empty:continue
    ranks=g.groupby('date')[F+['expectation']].transform(centered_rank);g['regime']=g.date.map(states)
    for h in [20,60]:
     for year in range(2021,2027):
      fit=eligible_training(g,year,h);test=g.date.dt.year.eq(year)
      if not test.any():continue
      tr=g[fit&g.regime.notna()];te=g[test&g.regime.notna()]
      reason='insufficient_train_rows_or_months' if len(tr)<300 or tr.date.nunique()<18 else 'no_known_test_state' if te.empty else None
      ident=dict(family=family,era=era,level=level,fy_offset=offset,population=population,horizon=h,year=year)
      rec=dict(ident,train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),removed_fit_unknown=int((fit&g.regime.isna()).sum()),removed_test_unknown=int((test&g.regime.isna()).sum()),state_fit_dates=tr.groupby('regime').date.nunique().to_dict(),status='skip' if reason else 'fit',reason=reason)
      ledger.append(rec)
      if reason:continue
      assert tr[f'maturity{h}'].max()<pd.Timestamp(year,1,1)
      for method,cols in {'price_only':F,'expectation_only':['expectation'],'price_plus_expectation':F+['expectation']}.items():
       scaler=StandardScaler().fit(ranks.loc[tr.index,cols]);xx=arrays(scaler.transform(ranks.loc[tr.index,cols]),tr.regime);xt=arrays(scaler.transform(ranks.loc[te.index,cols]),te.regime)
       y=tr[f'excess{h}'].to_numpy();w=sample_weights(tr).to_numpy()
       for variant,x in xx.items():
        model=Ridge(alpha=10).fit(x,y,sample_weight=w);pred=model.predict(xt[variant])
        a=np.column_stack([np.ones(len(x)),x]);b=np.column_stack([np.ones(len(te)),xt[variant]])
        coef=np.linalg.solve(a.T@(w[:,None]*a)+np.diag([0.]+[10.]*x.shape[1]),a.T@(w*y))
        err=float(np.max(np.abs(b@coef-pred)));assert err<1e-10;maxerr=max(err,maxerr)
        z=te[KEY+['date','regime',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'target',f'maturity{h}':'maturity'}).copy()
        z=z.assign(**{k:v for k,v in ident.items() if k not in KEY},method=method,variant=variant,prediction=pred,regime_seen_in_fit=te.regime.isin(tr.regime.unique()));parts.append(z)
        models.append(dict(rec,method=method,variant=variant,columns=cols,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
  current=pd.concat([x for x in parts if x.family.iloc[0]==family]);old=pd.read_parquet(ROOT/oldpath)
  keys=KEY+['date','fy_offset','population','horizon','year','method']
  paired=current[current.variant.eq('base')].merge(old,on=keys,suffixes=('_new','_old'),validate='one_to_one')
  # This equality is required only when state filtering removes no original fitted rows.
  if not any(x['removed_fit_unknown'] or x['removed_test_unknown'] for x in ledger if x['family']==family and x['status']=='fit'):
   assert len(paired)==len(old)
   err=float((paired.prediction_new-paired.prediction_old).abs().max());assert err<1e-10;original_error=max(original_error,err);original_rows+=len(paired)
  print(family,len(current),flush=True)
 p=pd.concat(parts,ignore_index=True);p.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',models);js(out/'fold_ledger.json',ledger)
 metrics=[]
 for key,g in p.groupby(GROUP+['method','variant','date','regime']):
  q=g.dropna(subset=['target']);ic=q.prediction.corr(q.target,method='spearman') if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan
  metrics.append(dict(zip(GROUP+['method','variant','date','regime'],key),n=len(g),known=len(q),mse=((q.prediction-q.target)**2).mean(),ic=ic))
 d=pd.DataFrame(metrics);d.to_csv(out/'date_metrics.csv',index=False);summary=[]
 for key,g in d.groupby(GROUP):
  for metric in ['mse','ic']:
   wide=g.pivot(index='date',columns=['method','variant'],values=metric)
   comparisons=[((m,a),(m,b)) for m in ['price_only','expectation_only','price_plus_expectation'] for a,b in [('state','base'),('interaction','base'),('interaction','state')]]+[(('price_plus_expectation',v),('price_only',v)) for v in ['base','state','interaction']]
   for a,b in comparisons:
    q=wide[[a,b]].dropna();delta=(q[a]-q[b])*(-1 if metric=='mse' else 1)
    summary.append(dict(zip(GROUP,key),metric=metric,first='/'.join(a),second='/'.join(b),dates=len(q),improvement=delta.mean()))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
 reads=['outputs/r130/monthly_panel.parquet','data/l1_monthly_panel.parquet','outputs/r195/market_regimes.parquet','protocols/r197.json','src/regime_expectations_r197.py','src/regime_core_r196.py','src/expectation_r29.py','src/train_r02.py','src/common.py']+[x for _,c,o in sources for x in [c,o]]
 js(out/'verification.json',dict(status='PASS',models=len(models),predictions=len(p),fit_folds=sum(x['status']=='fit' for x in ledger),skip_folds=sum(x['status']=='skip' for x in ledger),normal_equation_error=maxerr,original_control_rows=original_rows,original_control_error=original_error,adoption=False,all_families_complete=False,inputs={x:sha(ROOT/x) for x in reads},outputs={x:sha(out/x) for x in ['predictions.parquet','models.json','fold_ledger.json','date_metrics.csv','summary.csv']}))
if __name__=='__main__':run()
