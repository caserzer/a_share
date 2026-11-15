"""Describe changes using existing metrics, not new acceptance criteria."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r142';root=out/'evaluation';rows=[]
 for family in ['r31','r32']:
  p=pd.read_csv(out/f'{family}_increment_comparison.csv');assert p._merge.eq('both').all();metric='mean' if family=='r31' else 'brier_reduction';primary=p[p.horizon.eq(20)];d=primary[primary.comparison.eq('diffusion_with_size')]
  rows.append(dict(family=family,comparisons=len(p),primary_comparisons=len(primary),max_metric_change=float((p[metric+'_new']-p[metric+'_old']).abs().max()),primary_diffusion_intervals_include_zero=int((d.low99_new.le(0)&d.high99_new.ge(0)).sum()) if family=='r31' else None,primary_diffusion_rows=len(d),classification_supported=int(primary.result_new.eq('historical_support').sum()) if family=='r32' else None,models=len(json.loads((root/f'outputs/{family}/model_parameters.json').read_text()))))
 k=KEY+['date','horizon','method'];a=pd.read_parquet(ROOT/'data/r33_exit_origins.parquet');b=pd.read_parquet(root/'data/r33_exit_origins.parquet');pair=a.merge(b,on=k,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');changed=pair[pair._merge.eq('both')&pair.alert_old.ne(pair.alert_new)];changed[k+['alert_old','alert_new','prediction_old','prediction_new']].to_csv(out/'exit_alert_changes.csv',index=False);p=pd.read_csv(out/'exit_policy_comparison.csv');assert p._merge.eq('both').all();change=(p.mean_delta_new-p.mean_delta_old).abs();sign=np.sign(p.mean_delta_new).ne(np.sign(p.mean_delta_old));js(out/'impact.json',dict(model_evaluation=rows,exit=dict(old_rows=len(a),new_rows=len(b),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changed_common_alerts=len(changed),policies=len(p),changed_policy_values=int(change.gt(1e-12).sum()),max_policy_change=float(change.max()),policy_sign_changes=p.loc[sign,['era','level','horizon','cost','metric','comparison','mean_delta_old','mean_delta_new']].to_dict('records')),code_sha256=sha(__file__)))
 print(rows,'exit alerts',len(changed),flush=True)
if __name__=='__main__':run()
