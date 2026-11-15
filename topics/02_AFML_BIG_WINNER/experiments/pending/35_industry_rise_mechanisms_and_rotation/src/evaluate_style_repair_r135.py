"""Original R55/R56 evaluations against repaired predictions, isolated output root."""
import shutil
import pandas as pd
from common import *
import evaluate_style_r55,evaluate_classifiers_r56

def run():
 out=ROOT/'outputs/r135';sandbox=out/'evaluation';summaries=[]
 for family,module in [('r55',evaluate_style_r55),('r56',evaluate_classifiers_r56)]:
  dest=sandbox/f'outputs/{family}';dest.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/family/'predictions.parquet',dest/'predictions.parquet');module.ROOT=sandbox;module.run()
  keys=['era','level','horizon','comparison']+(['metric'] if family=='r55' else ['task']);old=pd.read_csv(ROOT/f'outputs/{family}/increments.csv');new=pd.read_csv(dest/'increments.csv');pair=old.merge(new,on=keys,suffixes=('_old','_new'),validate='one_to_one',how='outer',indicator=True);assert pair._merge.eq('both').all();pair.to_csv(out/f'{family}_increments_comparison.csv',index=False)
  primary=pair[pair.horizon.eq(20)];metric='mean' if family=='r55' else 'brier_reduction'
  if family=='r55':
   a=pd.DataFrame(json.loads((ROOT/f'outputs/{family}/stability_decisions.json').read_text()));b=pd.DataFrame(json.loads((dest/'stability_decisions.json').read_text()));d=a.merge(b,on=keys,suffixes=('_old','_new'),validate='one_to_one');d.to_csv(out/'r55_stability_comparison.csv',index=False);changes=d[d.stable_support_old.ne(d.stable_support_new)];supported_old=int(d.stable_support_old.sum());supported_new=int(d.stable_support_new.sum())
  else:changes=primary[primary.result_old.ne(primary.result_new)];supported_old=int(primary.result_old.eq('historical_support').sum());supported_new=int(primary.result_new.eq('historical_support').sum())
  summaries.append(dict(family=family,comparisons=len(pair),primary_comparisons=len(primary),conclusion_changes=changes[keys].to_dict('records'),supported_old=supported_old,supported_new=supported_new,max_primary_metric_change=float((primary[metric+'_new']-primary[metric+'_old']).abs().max())))
 js(out/'evaluation_summary.json',dict(summaries=summaries,reads={str(p):sha(p) for p in [Path(__file__),ROOT/'src/evaluate_style_r55.py',ROOT/'src/evaluate_classifiers_r56.py',ROOT/'src/evaluate_size_r31.py',ROOT/'src/evaluate_r02.py']},quality='Repeated-history Historical-proxy; original fixed evaluation'))
if __name__=='__main__':run()
