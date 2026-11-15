"""Fixed state augmentation of the corrected battery time-series experiment."""
from common import *
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from regime_core_r196 import arrays
from train_r02 import target,train_masks

def run():
 out=ROOT/'outputs/r198';out.mkdir(exist_ok=True)
 p=pd.read_parquet(ROOT/'outputs/r140/cohort_new.parquet');states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;p['regime']=p.date.map(states)
 protocol=json.loads((ROOT/'protocols/r64.json').read_text());limits=json.loads((ROOT/'protocols/r65.json').read_text())['gates']
 methods={k:v for k,v in protocol['methods'].items() if k!='mean'};ledger=[];models=[];parts=[];classes=[];maxerr=0.;manualerr=0.
 for identity,g in p.groupby(KEY):
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    boundary=pd.Timestamp(int(year),1,1);fit=g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna();test=g.date.dt.year.eq(year)
    tr=g[fit&g.regime.notna()];te=g[test&g.regime.notna()];ready=tr.date.nunique()>=protocol['minimum_train_months'] and len(te)>0
    rec=dict(zip(KEY,identity));rec.update(horizon=h,year=int(year),train_n=len(tr),test_n=len(te),removed_fit_unknown=int((fit&g.regime.isna()).sum()),removed_test_unknown=int((test&g.regime.isna()).sum()),state_fit_dates=tr.groupby('regime').date.nunique().to_dict(),status='fit' if ready else 'skip');ledger.append(rec)
    if not ready:continue
    assert (pd.to_datetime(tr.growth_available_at)<=tr.date).all() and (pd.to_datetime(te.growth_available_at)<=te.date).all()
    for name,cols in methods.items():
     scaler=StandardScaler().fit(tr[cols]);xx=arrays(scaler.transform(tr[cols]),tr.regime);xt=arrays(scaler.transform(te[cols]),te.regime);y=tr[f'excess{h}'].to_numpy()
     for variant,x in xx.items():
      model=Ridge(alpha=10).fit(x,y);pred=model.predict(xt[variant]);design=np.column_stack([np.ones(len(x)),x]);coef=np.linalg.solve(design.T@design+np.diag([0.]+[10.]*x.shape[1]),design.T@y);err=float(np.max(np.abs(np.column_stack([np.ones(len(te)),xt[variant]])@coef-pred)));assert err<1e-10;maxerr=max(maxerr,err)
      m=dict(rec,method=name,variant=variant,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_));models.append(m)
      # Independently construct state dummy and interactions from scalar row values.
      checks=[]
      for _,row in te.iterrows():
       z=(row[cols].to_numpy(float)-np.array(m['mean']))/np.array(m['scale']);u=[float(row.regime==s) for s in ['down_high','up_low','up_high']];a=list(z)
       if variant!='base':a+=u
       if variant=='interaction':a+=[float(value*flag) for flag in u for value in z]
       checks.append(float(np.dot(a,m['coef'])+m['intercept']))
      err=float(np.max(np.abs(np.array(checks)-pred)));assert err<1e-12;manualerr=max(manualerr,err)
      z=te[KEY+['date','regime','economic_month','growth_available_at',f'maturity{h}',f'excess{h}']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'target'}).copy();z=z.assign(horizon=h,year=int(year),method=name,variant=variant,prediction=pred,regime_seen_in_fit=te.regime.isin(tr.regime.unique()));parts.append(z)
   for task in ['onset','reversal']:
    y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
    for year in range(2020,2027):
     fit,cal,test=train_masks(q,year,h,task)
     if not test.any():continue
     tr=q[fit&q.regime.notna()];ca=q[cal&q.regime.notna()];te=q[test&q.regime.notna()]
     counts=dict(train_rows=len(tr),train_months=tr.date.nunique(),train_each_class=int(tr.y.value_counts().reindex([0.,1.],fill_value=0).min()),cal_rows=len(ca),cal_months=ca.date.nunique(),cal_each_class=int(ca.y.value_counts().reindex([0.,1.],fill_value=0).min()))
     failures=[k for k,v in limits.items() if counts[k]<v];classes.append(dict(zip(KEY,identity),task=task,horizon=h,year=year,**counts,test_rows=len(te),failed_gates=failures,status='skip' if failures else 'eligible'))
 # No classifier eligible in original data; filtering cannot create additional support.
 assert all(x['status']=='skip' for x in classes)
 prediction=pd.concat(parts,ignore_index=True);prediction.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',models);js(out/'fold_ledger.json',ledger);js(out/'classification_ledger.json',classes)
 old=pd.DataFrame(json.loads((ROOT/'outputs/r140/evaluation/outputs/r64/predictions.json').read_text()));old['date']=pd.to_datetime(old.date);keys=KEY+['date','horizon','year','method'];base=prediction[prediction.variant.eq('base')];paired=base.merge(old,on=keys,validate='one_to_one',suffixes=('_new','_old'));assert len(paired)==len(old)==len(base);controlerr=float((paired.prediction_new-paired.prediction_old).abs().max());assert controlerr<1e-12
 metrics=[]
 for key,g in prediction.groupby(KEY+['horizon']):
  wide=g.pivot(index=['date','year','regime'],columns=['method','variant'],values='prediction');labels=g.drop_duplicates('date').set_index('date').target;wide['target']=wide.index.get_level_values('date').map(labels)
  comparisons=[((m,a),(m,b)) for m in methods for a,b in [('state','base'),('interaction','base'),('interaction','state')]]+[((a,v),(b,v)) for a,b in [('FSB','FS'),('FSMB','FSM')] for v in ['base','state','interaction']]
  partitions=[('all',wide)]+[(f'year:{y}',wide[wide.index.get_level_values('year')==y]) for y in sorted(g.year.unique())]+[(f'state:{s}',wide[wide.index.get_level_values('regime')==s]) for s in sorted(g.regime.unique())]
  for period,d in partitions:
   for a,b in comparisons:
    z=d[d['target'].notna()];target_values=z['target'];improvement=((z[b]-target_values)**2-(z[a]-target_values)**2).mean();years=z.index.get_level_values('year').nunique()
    metrics.append(dict(zip(KEY+['horizon'],key),period=period,first='/'.join(a),second='/'.join(b),n=len(z),years=years,mse_improvement=improvement,mae_improvement=((z[b]-target_values).abs()-(z[a]-target_values).abs()).mean(),stability_sample_gate=bool(len(z)>=24 and years>=3)))
 pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
 reads=['outputs/r140/cohort_new.parquet','outputs/r140/evaluation/outputs/r64/predictions.json','outputs/r195/market_regimes.parquet','protocols/r64.json','protocols/r65.json','protocols/r198.json','src/regime_battery_r198.py','src/train_r02.py','src/regime_core_r196.py','src/common.py']
 js(out/'verification.json',dict(status='PASS',models=len(models),predictions=len(prediction),fit_folds=sum(x['status']=='fit' for x in ledger),skip_folds=sum(x['status']=='skip' for x in ledger),classification_folds=len(classes),classification_eligible=sum(x['status']=='eligible' for x in classes),normal_equation_error=maxerr,manual_prediction_error=manualerr,original_control_rows=len(paired),original_control_error=controlerr,adoption=False,inputs={x:sha(ROOT/x) for x in reads},outputs={x:sha(out/x) for x in ['predictions.parquet','models.json','fold_ledger.json','classification_ledger.json','metrics.csv']}))
 print('models',len(models),'predictions',len(prediction),'classifier eligible',sum(x['status']=='eligible' for x in classes))
if __name__=='__main__':run()
