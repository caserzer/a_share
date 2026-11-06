from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/regime_v26')
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import KEY,sha,js
BASES={'event_equal':'v23_event_weighting','risk_diffusion_min':'v20_persistent_confirmation'}
GATES=['market63','market126','market_both','market_breadth126']

def run():
 CACHE.mkdir(exist_ok=True,parents=True);parent=E/'v25_event_threshold_extension'
 previous=json.loads((parent/'outputs/predecessors.json').read_text());m=json.loads((parent/'outputs/manifest.json').read_text())
 previous.update({str(parent/f['path']):f['sha256'] for f in m['files']});previous[str(parent/'outputs/manifest.json')]=sha(parent/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 index=CACHE.parent/'forecast_v5/CSI_ALL.parquet';sr=json.loads((E/'v7_online_stage/outputs/state_receipt.json').read_text());assert sha(index)==sr['inputs'][str(index)]
 breadth_path=CACHE.parent/'long_v21/features.parquet';assert sha(breadth_path)==json.loads((E/'v21_long_context/outputs/prediction_receipt.json').read_text())['features_sha256']
 models=list(BASES)+[f'{base}__{gate}' for base in BASES for gate in GATES]
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),models=models,controls=list(BASES),gates=GATES,index_sha256=sha(index),breadth_sha256=sha(breadth_path),source_versions=BASES))
 b=pd.read_parquet(index).close;returns=pd.DataFrame({f'r{h}':b/b.shift(h)-1 for h in [63,126]})
 bp=b.iloc[:len(b)//2];prefix=pd.DataFrame({f'r{h}':bp/bp.shift(h)-1 for h in [63,126]});assert np.allclose(returns.loc[prefix.index],prefix,equal_nan=True)
 peers=pd.read_parquet(breadth_path,columns=KEY+['date','peer_up126']);identity=KEY+['date']
 assert not peers.groupby(identity).peer_up126.nunique(dropna=False).gt(1).any();peers=peers.drop_duplicates(identity)
 receipts={base:{a['task']:a for a in json.loads((E/version/'outputs/prediction_receipt.json').read_text())['tasks']} for base,version in BASES.items()}
 assert set(receipts['event_equal'])==set(receipts['risk_diffusion_min'])
 tasks=[];coverage=[]
 for task in receipts['event_equal']:
  rows=[];input_hashes={}
  for base in BASES:
   artifact=receipts[base][task];assert sha(artifact['path'])==artifact['sha256'];input_hashes[base]=artifact['sha256']
   old=pd.read_parquet(artifact['path'],filters=[('model','==',base)]);rows.append(old)
   f=old.merge(peers,on=identity,validate='many_to_one');assert np.array_equal(f.row_id,old.row_id)
   r63=f.date.map(returns.r63);r126=f.date.map(returns.r126)
   masks={'market63':r63.gt(0),'market126':r126.gt(0),'market_both':r63.gt(0)&r126.gt(0),'market_breadth126':r126.gt(0)&f.peer_up126.gt(.5)}
   for gate,mask in masks.items():
    r=old.copy();r['model']=f'{base}__{gate}';r['prob']=np.where(mask,r.prob,0.)
    rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False);r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
    diag=f.assign(year=f.date.dt.year,gate_open=mask.to_numpy()).groupby(['year','level']).gate_open.agg(['count','sum','mean']).reset_index()
    for v in diag.to_dict('records'):coverage.append(dict(task=task,base=base,gate=gate,**v))
  path=CACHE/'predictions'/f'{task}.parquet';path.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(path,index=False);tasks.append(dict(task=task,path=str(path),sha256=sha(path),source_sha256=input_hashes))
 pd.DataFrame(coverage).to_csv(OUT/'gate_coverage.csv',index=False)
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,frozen_sha256=sha(OUT/'frozen_candidates.json'),market_prefix_pass=True,all_original_observations_retained=True))
 print('V26 all predictions frozen',len(tasks),flush=True)

if __name__=='__main__':run()
