from common import *
import re,math
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from regime_core_r196 import arrays

def run():
 out=ROOT/'outputs/r281';out.mkdir(exist_ok=True)
 records=json.loads((ROOT/'outputs/r276/export_registry.json').read_text());lookup={r['month']:r for r in records};p=pd.read_parquet(ROOT/'outputs/r276/panel.parquet')
 p['log_installation']=p.economic_month.map({k:math.log(v['installation_gwh']) for k,v in lookup.items()});p['log_export']=p.economic_month.map({k:math.log(v['export_gwh']) if v['export_gwh'] else np.nan for k,v in lookup.items()});valid=p.export_eligible
 assert np.allclose((p.log_export-p.log_installation)[valid],p.export_log_ratio[valid],atol=1e-14)
 phase=2*np.pi*(p.economic_month.str[-2:].astype(int)-1)/12;p['annual_sin']=np.sin(phase);p['annual_cos']=np.cos(phase)
 p.to_parquet(out/'panel.parquet',index=False)
 original=json.loads((ROOT/'protocols/r64.json').read_text())['methods'];methods={'FS':original['FSM'],'FSB':original['FSMB'],'FSX':original['FSM']+['export_log_ratio'],'FSBX':original['FSMB']+['export_log_ratio']};methods.update(D=original['FSMB']+['log_installation'],DX=original['FSMB']+['log_installation','log_export'],DR=original['FSMB']+['log_installation','export_log_ratio']);methods.update({k+'C':methods[k]+['annual_sin','annual_cos'] for k in ['D','DX','DR']});ledger=[];models=[];predictions=[];error=0.
 for identity,g in p.groupby(KEY):
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    boundary=pd.Timestamp(int(year),1,1);fit=g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()&g.regime.notna();test=g.date.dt.year.eq(year)&g.regime.notna();tr=g[fit&g.export_eligible];te=g[test&g.export_eligible];ready=tr.date.nunique()>=24 and len(te)>0
    rec=dict(zip(KEY,identity),horizon=h,year=int(year),train_n=len(tr),test_n=len(te),original_train_n=int(fit.sum()),original_test_n=int(test.sum()),status='fit' if ready else 'skip');ledger.append(rec)
    if not ready:continue
    for name,cols in methods.items():
     scaler=StandardScaler().fit(tr[cols]);xs=arrays(scaler.transform(tr[cols]),tr.regime);xt=arrays(scaler.transform(te[cols]),te.regime)
     for variant,x in xs.items():
      model=Ridge(alpha=10).fit(x,tr[f'excess{h}']);pred=model.predict(xt[variant]);d=np.column_stack([np.ones(len(x)),x]);beta=np.linalg.solve(d.T@d+np.diag([0]+[10]*x.shape[1]),d.T@tr[f'excess{h}'].to_numpy());e=float(np.max(abs(np.column_stack([np.ones(len(te)),xt[variant]])@beta-pred)));assert e<1e-10;error=max(error,e)
      models.append(dict(rec,method=name,variant=variant,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
      z=te[KEY+['date','economic_month','regime',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'target',f'maturity{h}':'maturity'});z=z.assign(horizon=h,year=int(year),method=name,variant=variant,prediction=pred);predictions.append(z)
 js(out/'fold_ledger.json',ledger);js(out/'models.json',models);metrics=[]
 if predictions:
  pred=pd.concat(predictions,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False)
  for identity,g in pred.groupby(KEY+['horizon']):
   wide=g.pivot(index=['date','year','regime'],columns=['method','variant'],values='prediction');target=g.drop_duplicates('date').set_index('date').target;comparisons=[((a,v),(b,v)) for a,b in [('FSBX','FSB'),('FSX','FS'),('DX','D'),('DR','D'),('D','FSB'),('DR','DX'),('DXC','DC'),('DRC','DC'),('DC','D'),('DXC','DX'),('DRC','DR')] for v in ['base','state','interaction']]+[((m,v),(m,'base')) for m in methods for v in ['state','interaction']]
   for period,w in [('all',wide)]+[(f'year:{y}',wide[wide.index.get_level_values('year')==y]) for y in sorted(g.year.unique())]+[(f'state:{s}',wide[wide.index.get_level_values('regime')==s]) for s in sorted(g.regime.unique())]:
    y=w.index.get_level_values('date').map(target).to_numpy();good=np.isfinite(y);y=y[good];w=w[good]
    for a,b in comparisons:metrics.append(dict(zip(KEY+['horizon'],identity),period=period,first='/'.join(a),second='/'.join(b),n=len(w),years=w.index.get_level_values('year').nunique(),mse_improvement=float(np.mean((w[b].to_numpy()-y)**2-(w[a].to_numpy()-y)**2)) if len(w) else None,mae_improvement=float(np.mean(abs(w[b].to_numpy()-y)-abs(w[a].to_numpy()-y))) if len(w) else None,stability_sample_gate=bool(len(w)>=24 and w.index.get_level_values('year').nunique()>=3)))
 pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
 oldclass=json.loads((ROOT/'outputs/r198/classification_ledger.json').read_text());assert all(r['status']=='skip' for r in oldclass)
 summary=dict(status='PASS',direct_export_months=sum(r['export_gwh'] is not None for r in records),fit_folds=sum(r['status']=='fit' for r in ledger),models=len(models),predictions=sum(len(z) for z in predictions),normal_equation_max_error=error,classification_eligible=0,classification_reason='Strict row filtering of original R198 sample; no original fold eligible',stable_comparisons=sum(r['stability_sample_gate'] for r in metrics),adoption=False)
 js(out/'summary.json',summary);reads=['protocols/r281.json','src/battery_seasonal_r281.py','outputs/r277/predictions.parquet','outputs/r277/fold_ledger.json','outputs/r276/panel.parquet','outputs/r276/export_registry.json','outputs/r276/predictions.parquet','outputs/r276/fold_ledger.json','outputs/r198/classification_ledger.json','protocols/r64.json','src/regime_core_r196.py'];js(out/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in reads},outputs={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
