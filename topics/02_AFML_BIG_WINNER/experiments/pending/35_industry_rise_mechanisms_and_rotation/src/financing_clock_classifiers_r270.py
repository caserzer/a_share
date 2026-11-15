from common import *
import pandas as pd
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from train_r02 import target,train_masks,sample_weights
from financing_components_model_r262 import METHODS,COMPS
from regime_core_r196 import arrays

def run():
 import sys
 clock=sys.argv[1];assert clock in ['signal','snapshot'];out=ROOT/'outputs/r270'/clock;out.mkdir(parents=True,exist_ok=True);p=pd.read_parquet(ROOT/f'outputs/r269/{clock}/panel.parquet');ledger=[];models=[];preds=[]
 for (era,level),g in p.groupby(['era','level']):
  ranks=g.groupby('date')[METHODS['FSECB']].transform(centered_rank)
  for task in ['onset','reversal']:
   for h in [20,60]:
    y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
    for year in range(2020,2027):
     fit,cal,test=train_masks(q,year,h,task)
     if not test.any():continue
     tr=q[fit];ca=q[cal];te=q[test];tc=tr.y.value_counts().reindex([0.,1.],fill_value=0);cc=ca.y.value_counts().reindex([0.,1.],fill_value=0)
     failures=[]
     if len(tr)<300 or tr.date.nunique()<18:failures.append('train_history')
     if tc.min()<30:failures.append('train_classes')
     if len(ca)<100 or ca.date.nunique()<4 or cc.min()<10:failures.append('calibration')
     rec=dict(era=era,level=level,task=task,horizon=h,year=year,fit_rows=len(tr),fit_dates=tr.date.nunique(),cal_rows=len(ca),cal_dates=ca.date.nunique(),fit_classes=tc.tolist(),cal_classes=cc.tolist(),test_rows=len(te),status='skip' if failures else 'fit',failures=failures)
     ledger.append(rec)
     if failures:continue
     assert tr[f'maturity{h}'].max()<pd.Timestamp(year-1,7,1) and ca[f'maturity{h}'].max()<pd.Timestamp(year,1,1)
     for method,cols in METHODS.items():
      scale=StandardScaler().fit(ranks.loc[tr.index,cols]);xx=arrays(scale.transform(ranks.loc[tr.index,cols]),tr.regime);xc=arrays(scale.transform(ranks.loc[ca.index,cols]),ca.regime);xt=arrays(scale.transform(ranks.loc[te.index,cols]),te.regime)
      for variant in ['base','state','interaction']:
       with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always',ConvergenceWarning)
        model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(xx[variant],tr.y,sample_weight=sample_weights(tr));platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(model.decision_function(xc[variant]).reshape(-1,1),ca.y,sample_weight=sample_weights(ca));score=model.decision_function(xt[variant]);pred=platt.predict_proba(score.reshape(-1,1))[:,1]
       ident=dict(era=era,level=level,task=task,horizon=h,year=year,method=method,variant=variant);converged=not any(issubclass(w.category,ConvergenceWarning) for w in ws)
       models.append(dict(ident,columns=cols,mean=scale.mean_.tolist(),scale=scale.scale_.tolist(),coef=model.coef_.ravel().tolist(),intercept=float(model.intercept_[0]),cal_coef=float(platt.coef_[0,0]),cal_intercept=float(platt.intercept_[0]),converged=converged))
       z=te[KEY+['date','y',f'maturity{h}']].rename(columns={f'maturity{h}':'maturity'}).copy();z=z.assign(**{k:v for k,v in ident.items() if k not in KEY},prediction=pred,raw_score=score);preds.append(z)
 js(out/'fold_ledger.json',ledger);js(out/'models.json',models)
 pred=pd.concat(preds,ignore_index=True) if preds else pd.DataFrame();pred.to_parquet(out/'predictions.parquet',index=False)
 metrics=[]
 if len(pred):
  for key,g in pred.groupby(['era','level','task','horizon','method','variant','date']):
   v=g[g.y.notna()];metrics.append(dict(zip(['era','level','task','horizon','method','variant','date'],key),brier=((v.prediction-v.y)**2).mean(),known=len(v),unknown=len(g)-len(v)))
 d=pd.DataFrame(metrics);d.to_csv(out/'date_metrics.csv',index=False);summary=[]
 for (era,level),g in p.groupby(['era','level']):
  for task in ['onset','reversal']:
   for h in [20,60]:
    for variant in ['base','state','interaction']:
     z=d[d.era.eq(era)&d.level.eq(level)&d.task.eq(task)&d.horizon.eq(h)&d.variant.eq(variant)] if len(d) else pd.DataFrame()
     for a,b in COMPS:
      ident=dict(era=era,level=level,task=task,horizon=h,variant=variant,comparison=a+'-'+b)
      if z.empty:summary.append(dict(ident,status='no_fit'));continue
      w=z.pivot(index='date',columns='method',values='brier');delta=(w[b]-w[a]).dropna();summary.append(dict(ident,status='descriptive_only',months=len(delta),years=delta.index.year.nunique(),brier_improvement=delta.mean()))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
 js(out/'receipt.json',dict(models=len(models),predictions=len(pred),fitted_folds=sum(x['status']=='fit' for x in ledger),nonconverged=sum(not m['converged'] for m in models),inputs={s:sha(ROOT/s) for s in ['protocols/r270.json',f'outputs/r269/{clock}/panel.parquet','src/train_r02.py','src/financing_clock_classifiers_r270.py','src/financing_components_model_r262.py','src/regime_core_r196.py']},adoption=False));print('DONE',len(models),len(pred),flush=True)
if __name__=='__main__':run()
