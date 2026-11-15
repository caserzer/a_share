"""Frozen financial-change chain on repaired price/control inputs."""
import shutil
import pandas as pd
from common import *
import financial_change_r120,financial_folds_r121,financial_models_r122,common_clock_r123

def run():
 out=ROOT/'outputs/r146';root=out/'evaluation';root.mkdir(parents=True,exist_ok=True)
 paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet','data/r54_market_controls.parquet':ROOT/'outputs/r133/market_controls.parquet'}
 for name in ['member_ledger.parquet','industry_features.parquet']:paths['outputs/r108/'+name]=ROOT/('outputs/r145/evaluation/outputs/r108/'+name)
 for rel in ['data/l1_monthly_panel.parquet','data/r30_size_control.parquet','outputs/r117/linked_monthly.parquet']+[f'protocols/r{x}.json' for x in [120,121,122,123]]+[f'src/{s}.py' for s in ['common','train_r02','financial_folds_r121','versioned_observations']]:paths[rel]=ROOT/rel
 for rel,src in paths.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 mods=[financial_change_r120,financial_folds_r121,financial_models_r122,common_clock_r123]
 for mod in mods:mod.ROOT=root;mod.run()
 comparisons={}
 for name,rel,keys,cols in [('features','outputs/r120/industry_changes.parquet',KEY+['date','clock'],['mean_change','coverage','known']),('separate_clocks','outputs/r122/paired_predictions.parquet',KEY+['date','clock','cohort','horizon','year'],['controls','with_financial','y']),('common_clocks','outputs/r123/predictions.parquet',KEY+['date','cohort','horizon','year'],['controls','notice_model','update_model','y'])]:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_parquet(out/f'{name}_pairs.parquet',index=False);g=p[p._merge.eq('both')];changes={}
  for c in cols:
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  comparisons[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 for n in [121,123]:
  keys=['era','level','cohort','horizon','year']+(['clock','task'] if n==121 else []);a=pd.read_csv(ROOT/f'outputs/r{n}/fold_ledger.csv');b=pd.read_csv(root/f'outputs/r{n}/fold_ledger.csv');p=a.merge(b,on=keys,suffixes=('_old','_new'),how='outer',indicator=True,validate='one_to_one');p.to_csv(out/f'r{n}_fold_pairs.csv',index=False);comparisons[f'r{n}_folds']=dict(old=len(a),new=len(b),reason_changes=int(p.reason_old.ne(p.reason_new).sum()))
 js(out/'summary.json',dict(comparisons=comparisons,reads={str(x):sha(x) for x in list(paths.values())+[Path(__file__),ROOT/'protocols/r146.json']+[Path(m.__file__) for m in mods]},quality='Historical-proxy; no adoption'))
 print(json.dumps(comparisons,default=str))
if __name__=='__main__':run()
