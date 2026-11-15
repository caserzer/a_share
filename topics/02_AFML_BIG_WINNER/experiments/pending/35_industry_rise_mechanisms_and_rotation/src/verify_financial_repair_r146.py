"""Independent original financial verifiers, plus exact cohort and result comparisons."""
import pandas as pd
from common import *
import verify_financial_change_r120,verify_financial_folds_r121,verify_financial_models_r122,verify_common_clock_r123
from financial_folds_r121 import BASE

def run():
 out=ROOT/'outputs/r146';root=out/'evaluation';rec=json.loads((out/'summary.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 mods=[verify_financial_change_r120,verify_financial_folds_r121,verify_financial_models_r122,verify_common_clock_r123]
 for mod in mods:mod.ROOT=root;mod.run()
 k=KEY+['date','clock'];a=pd.read_parquet(ROOT/'outputs/r121/joined_panel.parquet');b=pd.read_parquet(root/'outputs/r121/joined_panel.parquet');cohorts=[]
 for name in ['main80','strict100']:
  x=a[a[name]].sort_values(k).reset_index(drop=True);y=b[b[name]].sort_values(k).reset_index(drop=True)
  pair=x.merge(y,on=k,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_parquet(out/f'{name}_cohort_pairs.parquet',index=False);g=pair[pair._merge.eq('both')];changes={c:int((~np.isclose(g[c+'_old'],g[c+'_new'],equal_nan=True,atol=1e-12,rtol=1e-10)).sum()) for c in BASE+['mean_change','excess20','excess60']};cohorts.append(dict(cohort=name,old=len(x),new=len(y),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changes=changes))
 comparisons=[]
 for n,keys in [(122,['era','level','clock','cohort','horizon','metric']),(123,['era','level','cohort','horizon','contrast','metric'])]:
  a=pd.read_csv(ROOT/f'outputs/r{n}/summary.csv');b=pd.read_csv(root/f'outputs/r{n}/summary.csv');p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_csv(out/f'r{n}_metric_comparison.csv',index=False);assert p._merge.eq('both').all();changes={}
  for c in a.select_dtypes(include='number').columns:
   if c in keys:continue
   changes[c]=int((~np.isclose(p[c+'_old'],p[c+'_new'],equal_nan=True,atol=1e-12,rtol=1e-10)).sum())
  comparisons.append(dict(round=n,rows=len(p),numeric_changes=changes,support_changes=int(p.historical_support_old.ne(p.historical_support_new).sum()),new_support=int(b.historical_support.sum())))
 js(out/'verification.json',dict(status='PASS',cohorts=cohorts,metric_comparisons=comparisons,subchecks={str(p.relative_to(root)):sha(p) for p in root.glob('outputs/*/verification.json')},summary_sha256=sha(out/'summary.json'),verifier_sha256=sha(__file__)))
 print(json.dumps(cohorts+comparisons,default=str))
if __name__=='__main__':run()
