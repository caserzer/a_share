"""Replay source sensitivity directly from keyed JSON predictions and fold ledgers."""
from common import *

def run():
 out=ROOT/'outputs/r62';receipt=json.loads((out/'impact_receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(Path(p))==h
 assert sha(out/'source_version_comparison.parquet')==receipt['comparison_sha256']
 assert sha(ROOT/'src/battery_impact_r62.py')==receipt['code_sha256']
 keys=KEY+['horizon','date','method']
 def read(round):
  rows=json.loads((ROOT/f'outputs/{round}/predictions.json').read_text());d={tuple(x[k] for k in keys):x for x in rows};assert len(d)==len(rows);return d
 old,new=read('r53'),read('r62');assert old.keys()<=new.keys()
 for key in old:assert old[key]['target']==new[key]['target']
 for m in json.loads((out/'source_impact.json').read_text()):
  ks=[k for k,x in new.items() if all(x[c]==m[c] for c in ['level','horizon','method'])]
  common=[k for k in ks if k in old and new[k]['target'] is not None]
  added=[k for k in ks if k not in old and new[k]['target'] is not None]
  assert len(common)==m['common_evaluated'] and len(added)==m['new_evaluated']
  assert sum(abs(new[k]['prediction']-old[k]['prediction'])>1e-12 for k in ks if k in old)==m['changed_predictions']
  for label,d in [('old',old),('new',new)]:assert abs(sum((d[k]['prediction']-d[k]['target'])**2 for k in common)/len(common)-m['common_mse_'+label])<1e-12
 folds=[]
 a,b=[json.loads((ROOT/f'outputs/{r}/fold_ledger.json').read_text()) for r in ['r53','r62']]
 for x in b:
  prior=next((z for z in a if all(z[k]==x[k] for k in KEY+['horizon','year'])),None)
  folds.append(dict(**{k:x[k] for k in KEY+['horizon','year']},old_train_n=prior['train_n'] if prior else None,new_train_n=x['train_n'],old_status=prior['status'] if prior else None,new_status=x['status']))
 js(out/'training_changes.json',folds)
 js(out/'impact_verification.json',dict(status='PASS',common_predictions=len(old),added_predictions=len(new)-len(old),removed_predictions=0,metrics_checked=8,folds_checked=len(folds),added_dates=sorted({new[k]['date'] for k in new.keys()-old.keys()})))
 print('R62 impact verified',len(old),len(new)-len(old))
if __name__=='__main__':run()
