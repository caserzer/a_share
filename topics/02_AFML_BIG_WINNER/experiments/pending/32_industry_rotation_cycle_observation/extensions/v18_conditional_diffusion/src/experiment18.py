from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/diffusion_v18')
sys.path.insert(0,str(E/'v12_duration_risk/src'))
from context12 import FEATURES,KEY,engine,sha,js
ADDED=['leader_pos21','leader_neg21','peer21','peer63','leader_gap21','leader_gap_lag21','peer_breadth21','peer_breadth_change','diffusion_interaction','beta_residual21','down_resilience63']
PARAMS=dict(n_estimators=240,num_leaves=15,max_depth=4,min_child_samples=200,learning_rate=.03,reg_lambda=25,n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)

def run():
 CACHE.mkdir(exist_ok=True,parents=True)
 prev=E/'v17_precision_recall_frontier';previous=json.loads((prev/'outputs/predecessors.json').read_text());m=json.loads((prev/'outputs/manifest.json').read_text())
 previous.update({str(prev/f['path']):f['sha256'] for f in m['files']});previous[str(prev/'outputs/manifest.json')]=sha(prev/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 risk=CACHE.parent/'duration_v12/risk_features.parquet';eco=CACHE.parent/'economic_v6/mechanism_features.parquet'
 assert sha(risk)==json.loads((E/'v12_duration_risk/outputs/prediction_receipt.json').read_text())['feature_sha256']
 assert sha(eco)==json.loads((E/'v6_economic_diffusion/outputs/feature_audit.json').read_text())['features_sha256']
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),base_features=FEATURES,added=ADDED,params=PARAMS,risk_sha256=sha(risk),economic_sha256=sha(eco),models=['capacity_tree','diffusion_tree','diffusion_blend'],blend_weight=.5))
 identity=KEY+['date','threshold','benchmark'];ekey=KEY+['date','benchmark']
 f=pd.read_parquet(risk);e=pd.read_parquet(eco,columns=ekey+ADDED)
 assert not e.groupby(ekey)[ADDED].nunique(dropna=False).gt(1).any().any()
 e=e.drop_duplicates(ekey);g=f.merge(e,on=ekey,how='left',validate='many_to_one');assert len(g)==len(f)
 g['diffusion_complete']=g[ADDED].notna().all(axis=1)
 g.to_parquet(CACHE/'features.parquet',index=False)
 coverage=g.assign(year=g.date.dt.year).groupby(['year','level']).diffusion_complete.agg(['count','sum','mean']).reset_index();coverage.to_csv(OUT/'feature_coverage.csv',index=False)
 labels=[]
 for _,v in engine.task_frames('b'):labels.append(v[identity+['y','label_available_at']])
 labels=pd.concat(labels,ignore_index=True).drop_duplicates(identity);g=g.merge(labels,on=identity,validate='one_to_one')
 training=g[g.state_eligible.eq(1)];pred=[];folds=[];importance=[]
 for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
  train=training[training.date.lt(q)&training.label_available_at.lt(q)&training.y.notna()]
  test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at'])
  if test.empty:continue
  assert train.label_available_at.max()<q
  elig=test.state_eligible.eq(1);r=test[identity+['diffusion_complete']].copy()
  for name,features in [('capacity_tree',FEATURES),('diffusion_tree',FEATURES+ADDED)]:
   model=LGBMClassifier(**PARAMS);model.fit(train[features],train.y,sample_weight=engine.date_weights(train))
   r[name]=0.;r.loc[elig,name]=np.clip(model.predict_proba(test.loc[elig,features])[:,1],1e-6,1-1e-6)
   importance.extend([dict(quarter=str(q.date()),model=name,feature=c,gain=float(v)) for c,v in zip(features,model.booster_.feature_importance(importance_type='gain'))])
  pred.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positives=int(train.y.sum()),latest_training_label=str(train.label_available_at.max()),test=len(test)))
  print('V18 quarter frozen',q.date(),flush=True)
 scores=pd.concat(pred,ignore_index=True);scores.to_parquet(CACHE/'scores.parquet',index=False)
 pd.DataFrame(importance).to_csv(OUT/'feature_importance.csv',index=False)
 source=json.loads((E/'v15_rank_separation/outputs/prediction_receipt.json').read_text());tasks=[]
 for artifact in source['tasks']:
  assert sha(artifact['path'])==artifact['sha256']
  old=pd.read_parquet(artifact['path'],filters=[('model','in',['rd_selected','rd_gate','risk_tree','risk_blend','rank_hedged'])])
  base=old[old.model.eq('risk_blend')].drop(columns='model').reset_index(drop=True)
  joined=base.merge(scores,on=identity,validate='many_to_one');assert np.array_equal(joined.row_id,base.row_id)
  joined['diffusion_blend']=.5*joined.diffusion_tree+.5*joined.prob
  rows=[]
  for name in ['capacity_tree','diffusion_tree','diffusion_blend']:
   r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy();r['diffusion_complete']=joined.diffusion_complete.to_numpy()
   rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
   r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
  old=old.merge(scores[identity+['diffusion_complete']],on=identity,validate='many_to_one');rows.insert(0,old)
  path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
  tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256']))
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),features_sha256=sha(CACHE/'features.parquet'),scores_sha256=sha(CACHE/'scores.parquet')))
 print('V18 all predictions frozen',flush=True)

if __name__=='__main__':run()
