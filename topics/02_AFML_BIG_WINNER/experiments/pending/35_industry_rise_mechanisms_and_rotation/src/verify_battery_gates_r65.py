"""Independent scalar-label and calendar-boundary replay; no training helpers."""
import pandas as pd
from common import *
from battery_pilot_r64 import panel

def run():
 out=ROOT/'outputs/r65';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 source=json.loads((ROOT/'outputs/r64/receipt.json').read_text())
 for p,h in source['inputs'].items():assert sha(p)==h
 p=panel();actual=[]
 for z in p.to_dict('records'):
  for task in ['onset','reversal']:
   if not (z['past_excess20']<=0 if task=='onset' else z['past_excess60']>0 and z['mom60']>0):continue
   for h in [20,60]:
    known=pd.notna(z[f'excess{h}']) and (task=='onset' or pd.notna(z[f'rel_trough{h}']))
    label=(z[f'return{h}']>=(.05 if h==20 else .10) and z[f'excess{h}']>=(.03 if h==20 else .05)) if task=='onset' else z[f'rel_trough{h}']<=(-.08 if h==20 else -.12)
    actual.append(dict(**{k:z[k] for k in KEY},date=z['date'],maturity=z[f'maturity{h}'],task=task,horizon=h,label=float(label) if known else None))
 saved=json.loads((out/'eligible_labels.json').read_text());keys=KEY+['date','task','horizon']
 def key(x):return tuple(str(pd.Timestamp(x[k])) if k=='date' else x[k] for k in keys)
 a={key(x):x for x in actual};b={key(x):x for x in saved};assert a.keys()==b.keys()
 for k in a:assert a[k]['label']==b[k]['label']
 limits=json.loads((ROOT/'protocols/r65.json').read_text())['gates'];folds=json.loads((out/'fold_ledger.json').read_text())
 for f in folds:
  g=[x for x in actual if all(x[k]==f[k] for k in KEY+['task','horizon'])];jan=pd.Timestamp(f['year'],1,1);jul=pd.Timestamp(f['year']-1,7,1)
  tr=[x for x in g if x['label'] is not None and x['date']<jul and x['maturity']<jul]
  ca=[x for x in g if x['label'] is not None and jul<=x['date']<jan and x['maturity']<jan]
  te=[x for x in g if x['date'].year==f['year']]
  counts={}
  for prefix,rows in [('train',tr),('cal',ca)]:
   counts[prefix+'_rows']=len(rows);counts[prefix+'_months']=len({x['date'] for x in rows});counts[prefix+'_each_class']=min(sum(x['label']==v for x in rows) for v in [0,1])
  assert all(f[k]==v for k,v in counts.items());assert f['test_rows']==len(te) and f['test_unknown']==sum(x['label'] is None for x in te)
  assert f['failed_gates']==[k for k,v in limits.items() if counts[k]<v]
  assert f['status']==('skip' if f['failed_gates'] else 'eligible')
 assert len(folds)==rec['folds'] and rec['eligible']==0
 js(out/'verification.json',dict(status='PASS',labels_checked=len(actual),folds_checked=len(folds),independent_label_calendar_and_class_counts=True,no_classifier_predictions=True))
 print('R65 VERIFIED',len(actual),'labels',len(folds),'folds')
if __name__=='__main__':run()
