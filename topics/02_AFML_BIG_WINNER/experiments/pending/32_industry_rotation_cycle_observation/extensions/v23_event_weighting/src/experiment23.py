from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/events_v23')
sys.path.insert(0,str(E/'v12_duration_risk/src'))
from context12 import KEY,engine,sha,js
IDENTITY=KEY+['date','threshold','benchmark']
PARAMS=dict(n_estimators=240,num_leaves=15,max_depth=4,min_child_samples=200,learning_rate=.03,reg_lambda=25,n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)

def event_weights(train,early=False):
 base=engine.date_weights(train);positive=train.y.eq(1).to_numpy();d=train.loc[positive,['event_or_witness_id','benchmark','date','event_start']].copy()
 assert d.event_or_witness_id.notna().all() and d.event_start.notna().all()
 age=(d.date-d.event_start).dt.days.to_numpy();assert ((age>=0)&(age<=92)).all()
 d['within']=base[positive]*(2-np.clip(age/90,0,1) if early else 1.)
 d['weight']=d.within/d.groupby(['event_or_witness_id','benchmark']).within.transform('sum')
 d['weight']*=base[positive].sum()/d.weight.sum()
 weights=base.copy();weights[positive]=d.weight.to_numpy()
 sums=d.groupby(['event_or_witness_id','benchmark']).weight.sum()
 assert np.isfinite(weights).all() and (weights>0).all()
 assert np.allclose(sums,sums.iloc[0]) and np.isclose(weights[positive].sum(),base[positive].sum())
 assert np.array_equal(weights[~positive],base[~positive])
 return weights,dict(events=len(sums),positive_weight=float(weights[positive].sum()),original_positive_weight=float(base[positive].sum()),min_event_weight=float(sums.min()),max_event_weight=float(sums.max()))

def run():
 CACHE.mkdir(exist_ok=True,parents=True);prevroot=E/'v22_precision_goal_audit';v18=E/'v18_conditional_diffusion'
 previous=json.loads((prevroot/'outputs/predecessors.json').read_text());m=json.loads((prevroot/'outputs/manifest.json').read_text())
 previous.update({str(prevroot/f['path']):f['sha256'] for f in m['files']});previous[str(prevroot/'outputs/manifest.json')]=sha(prevroot/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 source=json.loads((v18/'outputs/prediction_receipt.json').read_text());cfg=json.loads((v18/'outputs/frozen_candidates.json').read_text())
 features=cfg['base_features']+cfg['added'];path=CACHE.parent/'diffusion_v18/features.parquet';assert sha(path)==source['features_sha256']
 phases_path=CACHE.parent/'forecast_v5/daily_phases.parquet';phases=pd.read_parquet(phases_path).set_index('phase_id').start_date
 assert sha(phases_path)==json.loads((E/'v17_precision_recall_frontier/outputs/frozen_policy.json').read_text())['phases_sha256']
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),features=features,params=PARAMS,source_features_sha256=sha(path),phases_sha256=sha(phases_path),models=['event_equal','event_early','event_blend']))
 g=pd.read_parquet(path);labels=[]
 for _,f in engine.task_frames('b'):labels.append(f[IDENTITY+['y','label_available_at','event_or_witness_id']])
 labels=pd.concat(labels,ignore_index=True).drop_duplicates(IDENTITY);g=g.merge(labels,on=IDENTITY,validate='one_to_one')
 g['event_start']=g.event_or_witness_id.map(phases);training=g[g.state_eligible.eq(1)];pred=[];folds=[];weight_audit=[]
 assert not set(features)&{'y','label_available_at','event_or_witness_id','event_start'}
 for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
  train=training[training.date.lt(q)&training.label_available_at.lt(q)&training.y.notna()]
  test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','event_or_witness_id','event_start'])
  if test.empty:continue
  assert train.label_available_at.max()<q;eligible=test.state_eligible.eq(1);r=test[IDENTITY].copy()
  for name,early in [('event_equal',False),('event_early',True)]:
   weights,audit=event_weights(train,early);weight_audit.append(dict(quarter=str(q.date()),model=name,**audit))
   model=LGBMClassifier(**PARAMS);model.fit(train[features],train.y,sample_weight=weights)
   r[name]=0.;r.loc[eligible,name]=np.clip(model.predict_proba(test.loc[eligible,features])[:,1],1e-6,1-1e-6)
  pred.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positives=int(train.y.sum()),test=len(test),latest_training_label=str(train.label_available_at.max())))
  pd.DataFrame(weight_audit).to_csv(OUT/'training_weight_audit.csv',index=False)
  print('V23 quarter frozen',q.date(),flush=True)
 scores=pd.concat(pred,ignore_index=True);scores.to_parquet(CACHE/'scores.parquet',index=False);tasks=[]
 for artifact in source['tasks']:
  assert sha(artifact['path'])==artifact['sha256'];old=pd.read_parquet(artifact['path']);base=old[old.model.eq('diffusion_tree')].drop(columns='model').reset_index(drop=True)
  joined=base.merge(scores,on=IDENTITY,validate='many_to_one');assert np.array_equal(joined.row_id,base.row_id)
  joined['event_blend']=.5*joined.event_equal+.5*joined.prob;rows=[old]
  for name in ['event_equal','event_early','event_blend']:
   r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy();rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
   r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
  path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(path,index=False);tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256']))
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),scores_sha256=sha(CACHE/'scores.parquet')))
 print('V23 all predictions frozen',flush=True)

if __name__=='__main__':run()
