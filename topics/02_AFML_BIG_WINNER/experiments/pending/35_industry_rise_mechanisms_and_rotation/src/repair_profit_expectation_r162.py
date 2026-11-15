"""Complete the omitted fixed-FY profit revision price-panel repair."""
import shutil
import pandas as pd
import expectation_r25,verify_r25
from common import *

def run():
 out=ROOT/'outputs/r162';root=out/'evaluation';out.mkdir(parents=True,exist_ok=True)
 original=pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=['date']);fixed=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet',columns=['date']);assert set(original.date)==set(fixed.date)
 paths=['data/r25_revision_coverage.parquet','data/r25_company_pair_audit.parquet','data/r15_revision_coverage.parquet','protocols/r25.json','src/expectation_r15.py','src/expectation_r25.py']
 sources={p:ROOT/p for p in paths};sources['data/monthly_panel.parquet']=ROOT/'outputs/r130/monthly_panel.parquet'
 for rel,p in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 (root/'outputs/r25').mkdir(parents=True,exist_ok=True)
 for mod in [expectation_r25,verify_r25]:mod.ROOT=root;mod.run()
 rel='outputs/r25/predictions.parquet';a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);keys=KEY+['date','population','fy_offset','horizon','method','year'];p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');g=p[p._merge.eq('both')];changes={}
 for c in ['prediction','target']:
  x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()),known_to_unknown=int((x.notna()&y.isna()).sum()),unknown_to_known=int((x.isna()&y.notna()).sum()))
 summary=dict(predictions=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes));p.to_parquet(out/'prediction_pairs.parquet',index=False)
 for name,keys in [('fold_ledger',['era','level','fy_offset','population','horizon','year']),('cohorts',['era','level','fy_offset','population']),('metrics_by_date',['era','level','fy_offset','population','horizon','method','date']),('lead_lag_by_date',['era','level','fy_offset','population','date','target'])]:
  rel=f'outputs/r25/{name}.csv';a=pd.read_csv(ROOT/rel);b=pd.read_csv(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_csv(out/f'{name}_comparison.csv',index=False);g=p[p._merge.eq('both')];changes={}
  for c in a.select_dtypes(['number']).columns:
   if c in keys:continue
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  if name=='fold_ledger':changes['status_changes']=int(g.status_old.ne(g.status_new).sum())
  summary[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 js(out/'comparison.json',summary);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in list(sources.values())+[ROOT/'data/monthly_panel.parquet',ROOT/'protocols/r162.json',ROOT/'src/verify_r25.py',Path(__file__)]},same_monthly_dates=True,coverage_reused_reason='report clocks and fixed previous-month assignments independent of repaired price values; identical monthly calendar',accepted_increment=False));print(json.dumps(summary,default=str,indent=2))
if __name__=='__main__':run()
