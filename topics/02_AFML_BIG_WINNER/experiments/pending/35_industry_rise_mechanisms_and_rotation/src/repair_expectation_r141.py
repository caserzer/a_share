"""Isolated fixed-fiscal-year EPS experiment with corrected market inputs."""
import shutil
import pandas as pd
from common import *
from train_r02 import F
import expectation_r29

def run():
 out=ROOT/'outputs/r141';sandbox=out/'evaluation';paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet'}
 for path in ['data/l1_monthly_panel.parquet','data/l1_assignments.parquet','outputs/r28/training_gates.csv','outputs/r29/data_receipt.json','protocols/r29.json']+[f'data/r29_{v}_coverage.parquet' for v in ['raw_proxy','share_context_guard']]+[f'data/r28_{v}_eps_monthly.parquet' for v in ['raw_proxy','share_context_guard']]:paths[path]=ROOT/path
 for dest,source in paths.items():
  p=sandbox/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 panels={}
 for side,mp in [('old',ROOT/'data/monthly_panel.parquet'),('new',ROOT/'outputs/r130/monthly_panel.parquet')]:
  p=pd.concat([pd.read_parquet(mp),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);p['log_members']=np.log(p.members);panels[side]=p
 summaries=[]
 for variant in ['raw_proxy','share_context_guard']:
  cov=pd.read_parquet(ROOT/f'data/r29_{variant}_coverage.parquet')
  for side,p in panels.items():
   merged=cov.merge(p,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one');base=merged[merged.price_ready].dropna(subset=F+['covered_member_median']).copy();base.to_parquet(out/f'{variant}_{side}_base.parquet',index=False)
  expectation_r29.ROOT=sandbox;expectation_r29.run(variant)
  for name in ['cohorts.csv','fold_ledger.csv','model_parameters.json','lead_lag_by_date.csv','metrics_by_date.csv','summary.csv','annual.csv']:
   a=ROOT/f'outputs/r29/{variant}/{name}';b=sandbox/f'outputs/r29/{variant}/{name}';summaries.append(dict(variant=variant,artifact=name,bytes_equal=a.read_bytes()==b.read_bytes(),old_sha256=sha(a),new_sha256=sha(b)))
  a=pd.read_parquet(ROOT/f'outputs/r29/{variant}/predictions.parquet');b=pd.read_parquet(sandbox/f'outputs/r29/{variant}/predictions.parquet');keys=KEY+['date','fy_offset','population','horizon','year','method'];pair=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),validate='one_to_one',indicator=True);pair.to_parquet(out/f'{variant}_prediction_pairs.parquet',index=False)
  summaries.append(dict(variant=variant,artifact='prediction_payload',old_rows=len(a),new_rows=len(b),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changed_common_predictions=int((pair.prediction_new-pair.prediction_old).abs().gt(1e-12).sum()),max_prediction_change=float((pair.prediction_new-pair.prediction_old).abs().max())))
 js(out/'comparison.json',dict(artifacts=summaries,reads={str(p):sha(p) for p in list(paths.values())+[ROOT/'data/monthly_panel.parquet',Path(__file__),ROOT/'src/expectation_r29.py',ROOT/'protocols/r141.json']},quality='Historical-proxy fixed protocol replay'))
 print(summaries,flush=True)
if __name__=='__main__':run()
