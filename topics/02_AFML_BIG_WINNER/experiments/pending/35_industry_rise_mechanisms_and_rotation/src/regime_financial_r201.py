"""Pooled state conditioning; no state-specific model selection."""
from common import *
import pandas as pd
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from train_r02 import target
from train_r02 import train_masks,sample_weights
from financial_folds_r121 import BASE
STATES=['down_high','up_low','up_high'];KEYS=['family','era','level','cohort','method','task','horizon','year','objective']

def arrays(x,state):
 u=np.column_stack([state.eq(s).to_numpy(float) for s in STATES])
 return {'base':x,'state':np.column_stack([x,u]),'interaction':np.column_stack([x,u,*[x*u[:,j:j+1] for j in range(3)]])}

READS=['outputs/r146/evaluation/outputs/r121/joined_panel.parquet','outputs/r146/evaluation/outputs/r123/common_panel.parquet']
def methods_for(family):
 return {'controls':BASE,'notice_model':BASE+['notice_mean_change'],'update_model':BASE+['update_mean_change']} if family.startswith('common') else {'controls':BASE,'with_financial':BASE+['mean_change']}
def panels():
 for source,path in zip(['separate','common'],READS):
  p=pd.read_parquet(ROOT/path)
  for clock in (['notice','update'] if source=='separate' else ['common']):
   z=p[p.clock.eq(clock)] if source=='separate' else p
   for cohort in ['main80','strict100']:
    family=clock+'_'+cohort;methods=methods_for(family);cols=list(dict.fromkeys(c for cs in methods.values() for c in cs));q=z[z[cohort]].copy();q.attrs['identities']=list(z.groupby(['era','level']).groups)
    yield family,q,methods,cols

def prepare(panel,era,level,cohort,task,h):
 g=panel[panel.era.eq(era)&panel.level.eq(level)].copy();cols=list(dict.fromkeys(c for cs in methods_for(cohort).values() for c in cs));ranks=g[cols].copy() if g.empty else g.groupby('date')[cols].transform(centered_rank)
 y,ok=target(g,task,h);q=g[ok].copy();q['y']=y[ok]
 return q,ranks

def run():
 out=ROOT/'outputs/r201';out.mkdir(exist_ok=True);states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
 parts=[];params=[];ledger=[];maxerr=0.
 for family,panel,methods,columns in panels():
  models=[dict(era=era,level=level,cohort=family,method=method,task=task,horizon=h,year=year,columns=cols) for era,level in panel.attrs['identities'] for task in (['return'] if family.startswith('common') else ['return','onset','reversal']) for h in [20,60] for year in range(2020,2027) for method,cols in methods.items()]
  seen=set()
  for m in models:
   ident={k:m[k] for k in ['era','level','cohort','method','task','horizon','year']};ident['family']=family;mk=tuple(ident.values())
   if mk in seen:continue
   seen.add(mk);h=m['horizon'];year=m['year'];task=m['task']
   q,ranks=prepare(panel,m['era'],m['level'],m['cohort'],task,h);q['regime']=q.date.map(states)
   fit,cal,test=train_masks(q,year,h,task)
   tr=q[fit&q.regime.notna()];ca=q[cal&q.regime.notna()];te=q[test&q.regime.notna()]
   reason='no_test_rows' if te.empty else None
   if not reason and (len(tr)<300 or tr.date.nunique()<18):reason='insufficient_train'
   if not reason and task!='return':
    if tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='insufficient_train_classes'
    elif len(ca)<100 or ca.date.nunique()<4 or ca.y.value_counts().reindex([0.,1.],fill_value=0).min()<10:reason='insufficient_calibration'
   rec=dict(ident,fit_rows=len(tr),fit_dates=tr.date.nunique(),cal_rows=len(ca),cal_dates=ca.date.nunique(),test_rows=len(te),unknown_test_state=int((test&q.regime.isna()).sum()),removed_fit_unknown_state=int((fit&q.regime.isna()).sum()),state_fit_dates=tr.groupby('regime').date.nunique().to_dict(),state_cal_dates=ca.groupby('regime').date.nunique().to_dict(),status='skip' if reason else 'fit',reason=reason)
   ledger.append(rec)
   if reason or te.empty:continue
   assert tr[f'maturity{h}'].max()<pd.Timestamp(year if task=='return' else year-1,1 if task=='return' else 7,1)
   if task!='return':assert ca[f'maturity{h}'].max()<pd.Timestamp(year,1,1)
   cols=m['columns'];scaler=StandardScaler().fit(ranks.loc[tr.index,cols]);xx=arrays(scaler.transform(ranks.loc[tr.index,cols]),tr.regime);xt=arrays(scaler.transform(ranks.loc[te.index,cols]),te.regime)
   xc=arrays(scaler.transform(ranks.loc[ca.index,cols]),ca.regime) if len(ca) else None
   w=sample_weights(tr).to_numpy()
   objectives=[task]
   for objective in objectives:
    y=tr.groupby('date').y.transform(centered_rank).to_numpy() if objective=='rank' else tr.y.to_numpy()
    for variant in ['base','state','interaction']:
     x=xx[variant]
     with warnings.catch_warnings(record=True) as ws:
      warnings.simplefilter('always',ConvergenceWarning)
      if task=='return':
       model=Ridge(alpha=10).fit(x,y,sample_weight=w);prediction=model.predict(xt[variant]);platt=None
       design=np.column_stack([np.ones(len(x)),x]);pen=np.diag([0.]+[10.]*x.shape[1]);coef=np.linalg.solve(design.T@(w[:,None]*design)+pen,design.T@(w*y));other=np.column_stack([np.ones(len(te)),xt[variant]])@coef;err=float(np.max(np.abs(other-prediction)));assert err<1e-10;maxerr=max(maxerr,err)
      else:
       model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(x,y,sample_weight=w)
       score=model.decision_function(xc[variant]).reshape(-1,1);platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(score,ca.y,sample_weight=sample_weights(ca));prediction=platt.predict_proba(model.decision_function(xt[variant]).reshape(-1,1))[:,1]
     converged=not any(issubclass(x.category,ConvergenceWarning) for x in ws)
     entry=dict(ident,objective=objective,variant=variant,converged=converged,coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),columns=cols,calibration_coefficient=platt.coef_.tolist() if platt is not None else None,calibration_intercept=platt.intercept_.tolist() if platt is not None else None)
     params.append(entry)
     a=te[KEY+['date','y','regime',f'maturity{h}']].rename(columns={f'maturity{h}':'maturity'}).copy();a=a.assign(**{k:v for k,v in ident.items() if k not in KEY},objective=objective,variant=variant,prediction=prediction,converged=converged,regime_seen_in_fit=te.regime.isin(set(tr.regime)))
     parts.append(a)
  print('FIT FAMILY',family,flush=True)
 p=pd.concat(parts,ignore_index=True);p.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',params);js(out/'fold_ledger.json',ledger)
 rows=[]
 for key,g in p.groupby(KEYS+['date','regime','variant']):
  rec=dict(zip(KEYS+['date','regime','variant'],key));v=g[g.y.notna()]
  metric=(v.prediction.corr(v.y,method='spearman') if len(v)>=20 and v.prediction.nunique()>1 and v.y.nunique()>1 else np.nan) if rec['task']=='return' else -float(np.mean((v.prediction-v.y)**2)) if len(v) else np.nan
  rows.append(dict(rec,utility=metric,negative_mse=-float(np.mean((v.prediction-v.y)**2)) if len(v) else np.nan,n=len(g),known=len(v),converged=bool(g.converged.all())))
 d=pd.DataFrame(rows);d.to_csv(out/'date_metrics.csv',index=False);comparisons=[]
 for key,g in d.groupby([x for x in KEYS if x!='year']):
  z=g.pivot(index='date',columns='variant',values='utility').dropna();ident=dict(zip([x for x in KEYS if x!='year'],key))
  for a,b in [('state','base'),('interaction','base'),('interaction','state')]:comparisons.append(dict(ident,comparison=a+'-'+b,dates=len(z),delta=(z[a]-z[b]).mean()))
 pd.DataFrame(comparisons).to_csv(out/'summary.csv',index=False)
 reads=READS+['outputs/r195/market_regimes.parquet','protocols/r201.json','src/regime_financial_r201.py','src/train_r02.py','src/common.py','src/financial_folds_r121.py','src/financial_models_r122.py','src/common_clock_r123.py']
 files=['predictions.parquet','models.json','fold_ledger.json','date_metrics.csv','summary.csv']
 js(out/'verification.json',dict(status='PASS',scope='Maturity, shared cohort and state-known gates; independent linear normal equations; nonlinear fitting not independently certified',models=len(params),skipped_folds=sum(x['status']=='skip' for x in ledger),nonconverged_models=sum(not x['converged'] for x in params),linear_max_prediction_error=maxerr,prediction_rows=len(p),all_independent_mechanisms_complete=False,adoption=False,inputs={x:sha(ROOT/x) for x in reads},outputs={x:sha(out/x) for x in files}))
 print('DONE',len(params),'models',len(p),'rows',flush=True)
if __name__=='__main__':run()
