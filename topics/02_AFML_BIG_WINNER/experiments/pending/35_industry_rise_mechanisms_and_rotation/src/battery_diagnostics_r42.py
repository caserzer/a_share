"""Descriptive lead/lag associations and frozen classifier compatibility audit."""
import pandas as pd
from common import *
from battery_pilot_r41 import panel
from train_r02 import target,train_masks

def run():
 out=ROOT/'outputs/r42';out.mkdir(exist_ok=True);p=panel();associations=[];folds=[];prevalence=[];paired=[]
 protocol=json.loads((ROOT/'protocols/r42.json').read_text());gates=protocol['gates']
 for identity,g in p.groupby(KEY):
  base=dict(zip(KEY,identity))
  for h in [20,60]:
   q=g.dropna(subset=['log_yoy',f'past_excess{h}',f'excess{h}'])
   for _,x in q.iterrows():paired.append(dict(**base,horizon=h,date=x.date.isoformat(),log_yoy=float(x.log_yoy),past=float(x[f'past_excess{h}']),future=float(x[f'excess{h}'])))
   for period,z in [('all',q)]+[(str(y),q[q.date.dt.year.eq(y)]) for y in sorted(q.date.dt.year.unique())]:
    rhos=[]
    for v in [f'past_excess{h}',f'excess{h}']:
     rho=z.log_yoy.corr(z[v],method='spearman') if len(z)>=3 and z.log_yoy.nunique()>1 and z[v].nunique()>1 else np.nan
     rhos.append(float(rho) if np.isfinite(rho) else None)
    associations.append(dict(**base,horizon=h,period=period,n=len(z),rho_past=rhos[0],rho_future=rhos[1],interpretation='descriptive paired association, not causal or incremental prediction'))
   for task in ['onset','reversal']:
    y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
    known=q.y.dropna();prevalence.append(dict(**base,horizon=h,task=task,eligible=len(q),known=len(known),positive=int(known.eq(1).sum()),negative=int(known.eq(0).sum()),unknown=int(q.y.isna().sum())))
    for year in sorted(g.date.dt.year.unique()):
     fit,cal,test=train_masks(q,int(year),h,task);tr=q[fit];ca=q[cal];te=q[test]
     if te.empty:continue
     counts=dict(train_rows=len(tr),train_months=tr.date.nunique(),train_each_class=int(tr.y.value_counts().reindex([0.,1.],fill_value=0).min()),cal_rows=len(ca),cal_months=ca.date.nunique(),cal_each_class=int(ca.y.value_counts().reindex([0.,1.],fill_value=0).min()))
     failed=[k for k,v in gates.items() if counts[k]<v]
     folds.append(dict(**base,horizon=h,task=task,year=int(year),**counts,train_positive=int(tr.y.eq(1).sum()),cal_positive=int(ca.y.eq(1).sum()),test_rows=len(te),failed_gates=failed,qualified=not failed,train_dates=[x.isoformat() for x in tr.date],cal_dates=[x.isoformat() for x in ca.date]))
 js(out/'paired_observations.json',paired);js(out/'associations.json',associations);js(out/'class_prevalence.json',prevalence);js(out/'classifier_gates.json',folds)
 paths=[ROOT/'protocols/r42.json',ROOT/'outputs/r40/signal_coverage.json',ROOT/'data/monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'src/battery_pilot_r41.py',ROOT/'src/train_r02.py',Path(__file__)]
 summary=dict(inputs={str(x):sha(x) for x in paths},association_groups=len(associations),classifier_folds=len(folds),qualified=sum(x['qualified'] for x in folds),max_train_rows=max(x['train_rows'] for x in folds),max_cal_rows=max(x['cal_rows'] for x in folds),structural_calibration_cap_per_industry=6,required_calibration_rows=gates['cal_rows'],prediction_rows=0,limitation='compatibility audit; cannot conclude no industry predictive information from unmet framework gates')
 assert summary['qualified']==0,'Implement preregistered fit before claiming completion if a gate unexpectedly passes'
 js(out/'receipt.json',summary);print(json.dumps(summary,ensure_ascii=False));print(json.dumps([x for x in associations if x['period']=='all'],ensure_ascii=False));print(json.dumps(prevalence,ensure_ascii=False))

if __name__=='__main__':run()
