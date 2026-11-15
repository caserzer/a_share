"""Run original size-control models/evaluations/exits on corrected inputs."""
import shutil
import pandas as pd
from common import *
import size_models_r31,classifiers_size_r32,evaluate_size_r31,evaluate_classifiers_r32,exits_size_r33

def run():
 out=ROOT/'outputs/r142';root=out/'evaluation';paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet'}
 for p in ['data/l1_monthly_panel.parquet','data/r30_size_control.parquet']+[f'protocols/r{x}.json' for x in [31,32,33]]+[f'src/{s}.py' for s in ['common','train_r02','followup_r10']]:paths[p]=ROOT/p
 for dest,source in paths.items():
  p=root/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 (root/'outputs').mkdir(exist_ok=True)
 for module in [size_models_r31,classifiers_size_r32,evaluate_size_r31,evaluate_classifiers_r32,exits_size_r33]:module.ROOT=root;module.run()
 summary=[]
 for family in ['r31','r32']:
  keys=KEY+['date','horizon','year','method']+(['task'] if family=='r32' else []);a=pd.read_parquet(ROOT/f'outputs/{family}/predictions.parquet');b=pd.read_parquet(root/f'outputs/{family}/predictions.parquet');pair=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_parquet(out/f'{family}_prediction_pairs.parquet',index=False);shared=pair[pair._merge.eq('both')]
  fk=['era','level','horizon','year']+(['task'] if family=='r32' else []);fa=pd.read_csv(ROOT/f'outputs/{family}/fold_ledger.csv');fb=pd.read_csv(root/f'outputs/{family}/fold_ledger.csv');fp=fa.merge(fb,on=fk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');fp.to_csv(out/f'{family}_fold_comparison.csv',index=False)
  mk=['era','level','horizon','comparison']+(['metric'] if family=='r31' else ['task']);ma=pd.read_csv(ROOT/f'outputs/{family}/increments.csv');mb=pd.read_csv(root/f'outputs/{family}/increments.csv');mp=ma.merge(mb,on=mk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');mp.to_csv(out/f'{family}_increment_comparison.csv',index=False)
  summary.append(dict(family=family,old_rows=len(a),new_rows=len(b),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changed_common=int((shared.prediction_new-shared.prediction_old).abs().gt(1e-12).sum()),max_change=float((shared.prediction_new-shared.prediction_old).abs().max()),fold_status_changes=int(fp.status_new.ne(fp.status_old).sum()),classification_conclusion_changes=int(mp.result_new.ne(mp.result_old).sum()) if family=='r32' else None))
 a=pd.read_csv(ROOT/'outputs/r33/paired_policy.csv');b=pd.read_csv(root/'outputs/r33/paired_policy.csv');keys=['era','level','horizon','cost','metric','comparison'];a.merge(b,on=keys,suffixes=('_old','_new'),validate='one_to_one',how='outer',indicator=True).to_csv(out/'exit_policy_comparison.csv',index=False)
 js(out/'summary.json',dict(results=summary,reads={str(p):sha(p) for p in list(paths.values())+[Path(__file__),ROOT/'protocols/r142.json']+[ROOT/f'src/{s}.py' for s in ['size_models_r31','classifiers_size_r32','evaluate_size_r31','evaluate_classifiers_r32','exits_size_r33']]},quality='Historical-proxy fixed original methods'))
 print(summary,flush=True)
if __name__=='__main__':run()
