"""Replay original exit diagnostic against repaired classifier and outcomes."""
import shutil
import pandas as pd
from common import *
import exits_style_r57

def run():
 out=ROOT/'outputs/r136';sandbox=out/'evaluation';paths={'outputs/r56/predictions.parquet':ROOT/'outputs/r135/r56/predictions.parquet','data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet','data/l1_monthly_panel.parquet':ROOT/'data/l1_monthly_panel.parquet','protocols/r57.json':ROOT/'protocols/r57.json','src/followup_r10.py':ROOT/'src/followup_r10.py'}
 for dest,source in paths.items():
  p=sandbox/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 (sandbox/'outputs').mkdir(exist_ok=True);exits_style_r57.ROOT=sandbox;exits_style_r57.run()
 keys=['era','level','horizon','cost','metric','comparison'];old=pd.read_csv(ROOT/'outputs/r57/paired_policy.csv');new=pd.read_csv(sandbox/'outputs/r57/paired_policy.csv');pair=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair['change']=pair.mean_delta_new-pair.mean_delta_old;pair.to_csv(out/'policy_comparison.csv',index=False)
 oldo=pd.read_parquet(ROOT/'data/r57_exit_origins.parquet');newo=pd.read_parquet(sandbox/'data/r57_exit_origins.parquet');ik=KEY+['date','horizon','method'];op=oldo.set_index(ik);np_=newo.set_index(ik).reindex(op.index);assert len(op)==len(np_) and set(op.index)==set(newo.set_index(ik).index);flips=op.alert.ne(np_.alert);fliprows=op.loc[flips,['prediction','alert']].join(np_.loc[flips,['prediction','alert']],lsuffix='_old',rsuffix='_new').reset_index();fliprows.to_csv(out/'alert_changes.csv',index=False)
 js(out/'summary.json',dict(reads={str(p):sha(p) for p in list(paths.values())+[ROOT/'src/exits_style_r57.py',Path(__file__),ROOT/'protocols/r136.json']},origin_rows=len(newo),alert_changes=int(flips.sum()),paired_policies=len(pair),changed_policy_rows=int(pair.change.abs().gt(1e-12).sum()),max_policy_delta_change=float(pair.change.abs().max()),sign_changes=int((np.sign(pair.mean_delta_old)!=np.sign(pair.mean_delta_new)).sum()),quality='Historical-proxy terminal diagnostic only'))
 print('EXITS',len(newo),'alert changes',int(flips.sum()),flush=True)
if __name__=='__main__':run()
