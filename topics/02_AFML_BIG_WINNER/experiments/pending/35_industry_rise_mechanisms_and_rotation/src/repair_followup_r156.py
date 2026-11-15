"""Replay frozen R10 followup on corrected baskets, alerts and predictions."""
import shutil
import pandas as pd
import followup_r10,verify_r10
from common import *

def run():
 out=ROOT/'outputs/r156';root=out/'evaluation';cache=root/'cache';prior=ROOT/'outputs/r155/evaluation'
 sources={'cache/forecast_v5/daily_industries.parquet':prior/'cache/forecast_v5/daily_industries.parquet','cache/forecast_v5/CSI_ALL.parquet':prior/'cache/forecast_v5/CSI_ALL.parquet','outputs/r09/alerts.parquet':prior/'outputs/r09/alerts.parquet','outputs/r02/predictions.parquet':ROOT/'outputs/r131/predictions.parquet','protocols/r10.json':ROOT/'protocols/r10.json'}
 for rel,p in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 (root/'data').mkdir(exist_ok=True);(root/'outputs/r10').mkdir(exist_ok=True)
 for mod in [followup_r10,verify_r10]:mod.ROOT=root;mod.CACHE=cache;mod.run()
 comparisons={}
 for name,keys,cols in [('alert',KEY+['date','strategy'],['return5','return20','return60','drawdown20','continuation_excess20_60','breadth_change20']),('risk',KEY+['date','horizon'],['alert','return20','return60','excess20','excess60'])]:
  rel=f'data/r10_{name}_followup.parquet';a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');g=p[p._merge.eq('both')];changes={}
  for c in cols:
   x=g[c+'_old'].astype(float);y=g[c+'_new'].astype(float);changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),known_to_unknown=int((x.notna()&y.isna()).sum()),unknown_to_known=int((x.isna()&y.notna()).sum()),max_abs=float((x-y).abs().max()))
  comparisons[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 summaries={}
 for name,keys in [('followup_summary',['era','level','strategy','horizon']),('followup_annual',['era','level','strategy','year','horizon']),('continuation',['era','level','strategy','cohort']),('exit_summary_dates',['era','level','horizon','cohort','cost']),('exit_summary_rows',['era','level','horizon','cohort','cost'])]:
  rel=f'outputs/r10/{name}.csv';a=pd.read_csv(ROOT/rel);b=pd.read_csv(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert p._merge.eq('both').all();p.to_csv(out/f'{name}_comparison.csv',index=False);cc={}
  for c in a.select_dtypes('number').columns:
   if c in keys:continue
   x=p[c+'_old'];y=p[c+'_new'];cc[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()),sign_flips=int(((x*y)<0).sum()))
  summaries[name]=cc
 js(out/'comparison.json',dict(rows=comparisons,metrics=summaries))
 js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in list(sources.values())+[ROOT/'protocols/r156.json',Path(__file__),ROOT/'src/followup_r10.py',ROOT/'src/verify_r10.py']},quality='Historical-proxy; no adoption or economic stage certification'))
 print(json.dumps(comparisons,default=str,indent=2))
if __name__=='__main__':run()
