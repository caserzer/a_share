from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/confirmation_v20')
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import KEY,sha,js
NEW=['diffusion_confirmed','diffusion_median14','diffusion_median28','diffusion_median42','diffusion_up_median28','risk_diffusion_min','risk_diffusion_geomean']
IDENTITY=KEY+['date','threshold','benchmark']

def transform(g):
 g=g.sort_values('date').copy();g['diffusion_confirmed']=g.diffusion_tree.where(g.state_direction.eq(1),0.)
 for days,n in [(14,2),(28,3),(42,4)]:
  rolling=g.set_index('date').diffusion_tree.rolling(f'{days}D',min_periods=n,closed='right').median()
  g[f'diffusion_median{days}']=np.minimum(g.diffusion_tree,rolling.to_numpy()).fillna(0.)
 g['diffusion_up_median28']=g.diffusion_median28.where(g.state_direction.eq(1),0.)
 g['risk_diffusion_min']=np.minimum(g.risk_tree,g.diffusion_tree)
 g['risk_diffusion_geomean']=np.sqrt(g.risk_tree*g.diffusion_tree)
 g.loc[g.state_eligible.eq(0),NEW]=0.
 return g

def run():
 CACHE.mkdir(exist_ok=True,parents=True);v18=E/'v18_conditional_diffusion'
 previous=json.loads((v18/'outputs/predecessors.json').read_text());m=json.loads((v18/'outputs/manifest.json').read_text())
 previous.update({str(v18/f['path']):f['sha256'] for f in m['files']});previous[str(v18/'outputs/manifest.json')]=sha(v18/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 source=json.loads((v18/'outputs/prediction_receipt.json').read_text());p18=CACHE.parent/'diffusion_v18/scores.parquet';p12=CACHE.parent/'duration_v12/risk_scores.parquet'
 sr=json.loads((E/'v7_online_stage/outputs/state_receipt.json').read_text())
 assert sha(sr['path'])==sr['sha256'];assert sha(p18)==source['scores_sha256'];assert sha(p12)==json.loads((E/'v12_duration_risk/outputs/prediction_receipt.json').read_text())['scores_sha256']
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),models=NEW,source_score_sha256=sha(p18),risk_score_sha256=sha(p12),state_sha256=sr['sha256'],forward_looking_features=False))
 g=pd.read_parquet(p18).merge(pd.read_parquet(p12),on=IDENTITY,validate='one_to_one')
 state=pd.read_parquet(sr['path'],columns=KEY+['date','threshold','state_direction','state_eligible']).drop_duplicates(KEY+['date','threshold'])
 g=g.merge(state,on=KEY+['date','threshold'],validate='many_to_one');assert g.state_eligible.notna().all()
 parts=[];checks=0
 for _,sub in g.groupby(KEY+['threshold','benchmark'],sort=False):
  full=transform(sub);parts.append(full)
  if len(sub)>8:
   prefix=transform(sub.sort_values('date').iloc[:len(sub)//2]);matched=full.set_index('date').loc[prefix.date,NEW]
   assert np.allclose(matched.to_numpy(),prefix[NEW].to_numpy());checks+=1
 scores=pd.concat(parts,ignore_index=True);assert not scores[NEW].isna().any().any()
 assert scores.loc[scores.state_eligible.eq(0),NEW].eq(0).all().all()
 scores.to_parquet(CACHE/'scores.parquet',index=False);tasks=[]
 for artifact in source['tasks']:
  assert sha(artifact['path'])==artifact['sha256'];old=pd.read_parquet(artifact['path']);base=old[old.model.eq('diffusion_tree')].drop(columns='model').reset_index(drop=True)
  joined=base.merge(scores[IDENTITY+NEW],on=IDENTITY,validate='many_to_one');assert np.array_equal(base.row_id,joined.row_id)
  rows=[old]
  for name in NEW:
   r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy()
   rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
   r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
  path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(path,index=False);tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256']))
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,frozen_sha256=sha(OUT/'frozen_candidates.json'),scores_sha256=sha(CACHE/'scores.parquet'),prefix_checks=checks))
 print('V20 saved',len(tasks),'tasks;',checks,'prefix causality checks',flush=True)

if __name__=='__main__':run()
