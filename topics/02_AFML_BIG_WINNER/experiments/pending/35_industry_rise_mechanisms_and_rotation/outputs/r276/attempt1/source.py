from common import *
import re,math
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from regime_core_r196 import arrays

def run():
 out=ROOT/'outputs/r276';out.mkdir(exist_ok=True);sources=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());records=[]
 for x in sources:
  month=x['month'];m=int(month[-2:]);body=(ROOT/f'outputs/r275/bodies/{month}.txt').read_text();sentences=re.split('[。；]',re.sub(r'\s+','',body));matches=[];rejected=[]
  for i,s in enumerate(sentences):
   if '出口' not in s or 'GWh' not in s:continue
   cumulative=bool(re.search(r'累计|全年|\d+[-—–至到]\d+月份?',s))
   directmonth=bool(re.search(rf'(?<![\d—–至到-]){m}月份?',s));previous=sentences[i-1] if i else ''
   context=bool(s.startswith(('其中','其中，')) and re.search(rf'(?<![\d—–至到-]){m}月份?',previous) and '我国动力和' in previous and '出口' in previous and not re.search(r'累计|全年|\d+[-—–至到]\d+月',previous))
   hit=re.search(r'动力电池出口(?:销量|量)?(?:共计|为)?([\d.]+)GWh',s)
   if hit and not cumulative and (directmonth or context):matches.append(dict(sentence_index=i,sentence=s,context=previous if context else None,export_gwh=float(hit.group(1))))
   else:rejected.append(dict(sentence_index=i,sentence=s,reason='not_explicit_current_month_power_export'))
  vals=set(a['export_gwh'] for a in matches);v=next(iter(vals)) if len(vals)==1 else None
  records.append(dict(month=month,export_gwh=v,installation_gwh=x['value_gwh'],export_log_ratio=math.log(v/x['value_gwh']) if v and x['value_gwh']>0 else None,status='direct_power_export' if v is not None else 'missing_or_ambiguous',matches=matches,rejected=rejected,raw_sha256=x['raw_sha256'],available_at=x['available_at'],page_date=x['page_date'],url=x['url'],body_sha256=sha(ROOT/f'outputs/r275/bodies/{month}.txt')))
 js(out/'export_registry.json',records);flat=pd.DataFrame([{k:v for k,v in r.items() if k not in ['matches','rejected']} for r in records]);flat.to_csv(out/'export_registry.csv',index=False)
 p=pd.read_parquet(ROOT/'outputs/r140/cohort_new.parquet');p=p.merge(flat[['month','export_log_ratio','available_at']].rename(columns={'month':'economic_month','available_at':'export_available_at'}),on='economic_month',how='left',validate='many_to_one');p['regime']=p.date.map(pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime);p['export_eligible']=p.export_log_ratio.notna()&pd.to_datetime(p.export_available_at).le(p.date)&p.regime.notna();p.to_parquet(out/'panel.parquet',index=False)
 original=json.loads((ROOT/'protocols/r64.json').read_text())['methods'];methods={'FS':original['FSM'],'FSB':original['FSMB'],'FSX':original['FSM']+['export_log_ratio'],'FSBX':original['FSMB']+['export_log_ratio']};ledger=[];models=[];predictions=[];error=0.
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
   wide=g.pivot(index=['date','year','regime'],columns=['method','variant'],values='prediction');target=g.drop_duplicates('date').set_index('date').target;comparisons=[((a,v),(b,v)) for a,b in [('FSBX','FSB'),('FSX','FS')] for v in ['base','state','interaction']]+[((m,v),(m,'base')) for m in methods for v in ['state','interaction']]
   for period,w in [('all',wide)]+[(f'year:{y}',wide[wide.index.get_level_values('year')==y]) for y in sorted(g.year.unique())]+[(f'state:{s}',wide[wide.index.get_level_values('regime')==s]) for s in sorted(g.regime.unique())]:
    y=w.index.get_level_values('date').map(target).to_numpy();good=np.isfinite(y);y=y[good];w=w[good]
    for a,b in comparisons:metrics.append(dict(zip(KEY+['horizon'],identity),period=period,first='/'.join(a),second='/'.join(b),n=len(w),years=w.index.get_level_values('year').nunique(),mse_improvement=float(np.mean((w[b].to_numpy()-y)**2-(w[a].to_numpy()-y)**2)) if len(w) else None,mae_improvement=float(np.mean(abs(w[b].to_numpy()-y)-abs(w[a].to_numpy()-y))) if len(w) else None,stability_sample_gate=bool(len(w)>=24 and w.index.get_level_values('year').nunique()>=3)))
 pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
 oldclass=json.loads((ROOT/'outputs/r198/classification_ledger.json').read_text());assert all(r['status']=='skip' for r in oldclass)
 summary=dict(status='PASS',direct_export_months=sum(r['export_gwh'] is not None for r in records),fit_folds=sum(r['status']=='fit' for r in ledger),models=len(models),predictions=sum(len(z) for z in predictions),normal_equation_max_error=error,classification_eligible=0,classification_reason='Strict row filtering of original R198 sample; no original fold eligible',stable_comparisons=sum(r['stability_sample_gate'] for r in metrics),adoption=False)
 js(out/'summary.json',summary);reads=['protocols/r276.json','src/battery_export_r276.py','outputs/r60/frozen_monthly_series.json','outputs/r140/cohort_new.parquet','outputs/r195/market_regimes.parquet','outputs/r198/classification_ledger.json','protocols/r64.json','src/regime_core_r196.py']+[str(f.relative_to(ROOT)) for f in (ROOT/'outputs/r275/bodies').glob('*.txt')];js(out/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in reads},outputs={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
