"""Audit all classification feasibility gates, without training on inadequate samples."""
import pandas as pd
from common import *
from battery_pilot_r64 import panel
from train_r02 import target,train_masks

def run():
 out=ROOT/'outputs/r65';out.mkdir(exist_ok=True);p=panel();protocol=json.loads((ROOT/'protocols/r65.json').read_text());limits=protocol['gates'];rows=[];labels=[]
 for identity,g in p.groupby(KEY):
  for task in ['onset','reversal']:
   for h in [20,60]:
    y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
    for _,z in q.iterrows():labels.append(dict(**dict(zip(KEY,identity)),task=task,horizon=h,date=z.date,maturity=z[f'maturity{h}'],label=z.y))
    for year in range(2020,2027):
     fit,cal,test=train_masks(q,year,h,task)
     if not test.any():continue
     tr,ca,te=q[fit],q[cal],q[test]
     counts=dict(train_rows=len(tr),train_months=tr.date.nunique(),train_each_class=int(tr.y.value_counts().reindex([0.,1.],fill_value=0).min()),cal_rows=len(ca),cal_months=ca.date.nunique(),cal_each_class=int(ca.y.value_counts().reindex([0.,1.],fill_value=0).min()))
     failures=[k for k,v in limits.items() if counts[k]<v]
     rows.append(dict(**dict(zip(KEY,identity)),task=task,horizon=h,year=year,**counts,train_positive=int(tr.y.eq(1).sum()),cal_positive=int(ca.y.eq(1).sum()),test_rows=len(te),test_unknown=int(te.y.isna().sum()),failed_gates=failures,status='eligible' if not failures else 'skip'))
 js(out/'fold_ledger.json',rows);js(out/'eligible_labels.json',labels)
 paths=[ROOT/'protocols/r65.json',ROOT/'src/train_r02.py',ROOT/'src/battery_pilot_r64.py',ROOT/'outputs/r64/receipt.json',Path(__file__)]
 js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},folds=len(rows),eligible=sum(x['status']=='eligible' for x in rows),skipped=sum(x['status']=='skip' for x in rows),prediction_rows=0,interpretation='sample and calibration feasibility only; no predictive efficacy conclusion'))
 print('R65',len(rows),'folds;',sum(x['status']=='eligible' for x in rows),'eligible')
if __name__=='__main__':run()
