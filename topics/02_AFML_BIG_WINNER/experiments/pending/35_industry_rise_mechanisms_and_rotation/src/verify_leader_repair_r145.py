"""Verify original independent arithmetic on isolated repaired inputs and compare results."""
import pandas as pd
from common import *
import verify_leader_r108,verify_leader_models_r109,verify_leader_metrics_r109,verify_catchup_r110,verify_catchup_models_r111

def run():
 out=ROOT/'outputs/r145';root=out/'evaluation';rec=json.loads((out/'summary.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 mods=[verify_leader_r108,verify_leader_models_r109,verify_leader_metrics_r109,verify_catchup_r110,verify_catchup_models_r111]
 for mod in mods:mod.ROOT=root;mod.run()
 results=[]
 for n,keys in [(109,['era','level','cohort','task','horizon']),(110,['era','level','cohort','stratum']),(111,['era','level','cohort','metric'])]:
  a=pd.read_csv(ROOT/f'outputs/r{n}/summary.csv');b=pd.read_csv(root/f'outputs/r{n}/summary.csv');p=a.merge(b,on=keys,suffixes=('_old','_new'),how='outer',indicator=True,validate='one_to_one');p.to_csv(out/f'r{n}_summary_comparison.csv',index=False);g=p[p._merge.eq('both')];changes={}
  for c in a.select_dtypes(include='number').columns:
   if c in keys:continue
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  results.append(dict(round=n,old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes,support_changes=int(g.historical_support_old.ne(g.historical_support_new).sum()) if 'historical_support' in a else None,new_support=int(b.historical_support.sum()) if 'historical_support' in b else None))
 js(out/'verification.json',dict(status='PASS',metric_comparisons=results,subchecks={str(p.relative_to(root)):sha(p) for p in root.glob('outputs/*/*verification.json')},verifier_sha256=sha(__file__)))
 print(json.dumps(results,default=str))
if __name__=='__main__':run()
