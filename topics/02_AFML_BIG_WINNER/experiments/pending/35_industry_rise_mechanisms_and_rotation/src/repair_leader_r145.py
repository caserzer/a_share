"""Original leader/catch-up chain replay with corrected monthly and market inputs."""
import shutil
import pandas as pd
from common import *
import leader_feature_r108,leader_models_r109,evaluate_leader_r109,leader_catchup_r110,catchup_models_r111

def run():
 out=ROOT/'outputs/r145';root=out/'evaluation';root.mkdir(parents=True,exist_ok=True)
 paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet','data/r54_market_controls.parquet':ROOT/'outputs/r133/market_controls.parquet'}
 for rel in ['data/l1_monthly_panel.parquet','data/l1_assignments.parquet','data/r30_size_control.parquet','outputs/universe_current.csv']+[f'protocols/r{x}.json' for x in [108,109,110,111]]+[f'src/{s}.py' for s in ['common','train_r02','evaluate_unique_r105','leader_models_r109']]:paths[rel]=ROOT/rel
 for rel,src in paths.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 modules=[leader_feature_r108,leader_models_r109,evaluate_leader_r109,leader_catchup_r110,catchup_models_r111]
 for mod in modules:mod.ROOT=root;mod.run()
 comparisons={}
 for name,rel,keys,cols in [('features','outputs/r108/industry_features.parquet',KEY+['date'],['leader_spread','leader_return','follower_return']),('three_task','outputs/r109/predictions.parquet',KEY+['date','cohort','task','horizon','year','method'],['prediction','decision','y']),('catchup','outputs/r111/paired_predictions.parquet',KEY+['date','cohort','year'],['controls','with_leader','catchup'])]:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_parquet(out/f'{name}_pairs.parquet',index=False);g=p[p._merge.eq('both')];changes={}
  for c in cols:
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,rtol=1e-10,atol=1e-12,equal_nan=True)).sum()),known_to_unknown=int((x.notna()&y.isna()).sum()),unknown_to_known=int((x.isna()&y.notna()).sum()),max_abs=float((x-y).abs().max()))
  comparisons[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 for round_ in [109,111]:
  keys=['era','level','cohort','year']+(['task','horizon'] if round_==109 else []);a=pd.read_csv(ROOT/f'outputs/r{round_}/fold_ledger.csv');b=pd.read_csv(root/f'outputs/r{round_}/fold_ledger.csv');p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_csv(out/f'r{round_}_fold_pairs.csv',index=False);comparisons[f'r{round_}_folds']=dict(old=len(a),new=len(b),changed_status=int(p.status_old.ne(p.status_new).sum()))
 js(out/'summary.json',dict(comparisons=comparisons,reads={str(x):sha(x) for x in list(paths.values())+[Path(__file__),ROOT/'protocols/r145.json']+[Path(m.__file__) for m in modules]},quality='Historical-proxy; original fixed leader/catch-up rules; not adopted'))
 print(json.dumps(comparisons,default=str))
if __name__=='__main__':run()
