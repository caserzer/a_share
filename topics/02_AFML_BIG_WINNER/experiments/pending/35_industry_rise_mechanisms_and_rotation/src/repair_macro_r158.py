"""Replay frozen macro state interactions with corrected monthly baskets."""
import shutil
import pandas as pd
import macro_r13,verify_r13
from common import *

def run():
 out=ROOT/'outputs/r158';root=out/'evaluation'
 sources={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet','data/l1_monthly_panel.parquet':ROOT/'data/l1_monthly_panel.parquet','data/r11_macro_observations.parquet':ROOT/'data/r11_macro_observations.parquet','protocols/r13.json':ROOT/'protocols/r13.json'}
 for rel,p in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 (root/'outputs/r13').mkdir(parents=True,exist_ok=True)
 for mod in [macro_r13,verify_r13]:mod.ROOT=root;mod.run()
 summary={}
 for name,rel,keys,values in [('sensitivities','data/r13_sensitivities.parquet',KEY+['date','lag'],['exposure','conditioned','n_fit']),('selections','outputs/r13/selections.parquet',KEY+['date','lag','method'],[])]:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');g=p[p._merge.eq('both')];changes={}
  for c in values:
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  summary[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 for name,keys in [('coverage',['era','level','date']),('date_metrics',['era','level','date','lag','method','horizon']),('increments',['era','level','lag','horizon','baseline'])]:
  rel=f'outputs/r13/{name}.csv';a=pd.read_csv(ROOT/rel);b=pd.read_csv(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_csv(out/f'{name}_comparison.csv',index=False);g=p[p._merge.eq('both')];changes={}
  for c in a.select_dtypes(['number','bool']).columns:
   if c in keys:continue
   x=g[c+'_old'].astype(float);y=g[c+'_new'].astype(float);changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  summary[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 js(out/'comparison.json',summary);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in list(sources.values())+[ROOT/'protocols/r158.json',Path(__file__),ROOT/'src/macro_r13.py',ROOT/'src/verify_r13.py']},quality='Historical-proxy, original protocol unchanged'))
 print(json.dumps(summary,default=str,indent=2))
if __name__=='__main__':run()
