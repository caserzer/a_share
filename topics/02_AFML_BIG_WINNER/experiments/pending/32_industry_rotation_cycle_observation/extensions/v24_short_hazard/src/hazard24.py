from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/hazard_v24')
sys.path.insert(0,str(E/'v12_duration_risk/src'))
from context12 import FEATURES,KEY,engine,sha,js
sys.path.insert(0,str(E/'v7_online_stage/src'))
from state7 import trace
IDENTITY=KEY+['date','threshold','benchmark'];STATE_KEY=KEY+['date','threshold']
PARAMS=dict(n_estimators=90,num_leaves=7,max_depth=3,min_child_samples=500,learning_rate=.03,reg_lambda=25,n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
NEW=['hazard21_gate','hazard63_gate','survival6_gate'];CONTROLS=['risk_blend','diffusion_tree','risk_diffusion_min']

def make_targets():
 old=CACHE.parent/'forecast_v5';sr=json.loads((E/'v7_online_stage/outputs/state_receipt.json').read_text())
 for p in [old/'daily_industries.parquet',old/'features.parquet']:assert sha(p)==sr['inputs'][str(p)]
 assert sha(E/'v7_online_stage/src/state7.py')==sr['code_sha256']
 daily=pd.read_parquet(old/'daily_industries.parquet');f=pd.read_parquet(old/'features.parquet');f=f[f.features_ready]
 groups={k:g[['date']].drop_duplicates() for k,g in f.groupby(KEY+['block'])};rows=[];prefix_count=0;block_count=0
 for key,g in daily.groupby(KEY+['block'],sort=False):
  if key not in groups:continue
  g=g.sort_values('date');dates=pd.DatetimeIndex(g.date);block_count+=1
  for threshold in [.1,.15,.2]:
   s=trace(g.nav,dates,threshold);assert s.candidate_low_date.is_monotonic_increasing
   for h in [21,63]:
    future=s.candidate_low_date.shift(-h);s[f'invalidate{h}']=future.ne(s.candidate_low_date).astype(float).where(future.notna())
    s[f'available{h}']=s.date.shift(-h)
    assert s.loc[s[f'invalidate{h}'].notna(),f'available{h}'].gt(s.loc[s[f'invalidate{h}'].notna(),'date']).all()
   if len(g)>126:
    n=len(g)//2;p=trace(g.nav.iloc[:n],dates[:n],threshold)
    assert np.array_equal(p.candidate_low_date.to_numpy(),s.candidate_low_date.iloc[:n].to_numpy())
    for h in [21,63]:
     if n>h:assert np.array_equal(p.candidate_low_date.shift(-h).ne(p.candidate_low_date).iloc[:n-h].to_numpy(),s[f'invalidate{h}'].iloc[:n-h].to_numpy())
    prefix_count+=1
   s=s[['date','invalidate21','available21','invalidate63','available63']].merge(groups[key],on='date',validate='one_to_one')
   for c,v in zip(KEY+['block'],key):s[c]=v
   s['threshold']=threshold;rows.append(s)
 targets=pd.concat(rows,ignore_index=True);assert not targets.duplicated(STATE_KEY).any()
 path=CACHE/'auxiliary_targets.parquet';targets.to_parquet(path,index=False)
 js(OUT/'auxiliary_target_audit.json',dict(target_rows=len(targets),blocks=block_count,prefix_checks=prefix_count,path=str(path),sha256=sha(path),unknown21=int(targets.invalidate21.isna().sum()),unknown63=int(targets.invalidate63.isna().sum()),positive_negative_same_maturity=True,source_hashes=sr['inputs'],state_code_sha256=sr['code_sha256']))
 print('V24 targets frozen',len(targets),'prefix checks',prefix_count,flush=True)
 return targets

def run():
 CACHE.mkdir(exist_ok=True,parents=True);v22=E/'v22_precision_goal_audit';prev=json.loads((v22/'outputs/predecessors.json').read_text());m=json.loads((v22/'outputs/manifest.json').read_text())
 prev.update({str(v22/f['path']):f['sha256'] for f in m['files']});prev[str(v22/'outputs/manifest.json')]=sha(v22/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in prev.items());js(OUT/'predecessors.json',prev)
 path=CACHE.parent/'duration_v12/risk_features.parquet';assert sha(path)==json.loads((E/'v12_duration_risk/outputs/prediction_receipt.json').read_text())['feature_sha256']
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),features=FEATURES,params=PARAMS,models=NEW,controls=CONTROLS,risk_features_sha256=sha(path),auxiliary_horizons=[21,63]))
 targets=make_targets();g=pd.read_parquet(path).merge(targets.drop(columns='block'),on=STATE_KEY,validate='many_to_one')
 training=g[g.state_eligible.eq(1)];pred=[];folds=[]
 for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
  test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['invalidate21','invalidate63','available21','available63'])
  if test.empty:continue
  eligible=test.state_eligible.eq(1);r=test[IDENTITY+['state_age','state_eligible']].copy()
  for h in [21,63]:
   train=training[training.date.lt(q)&training[f'available{h}'].lt(q)&training[f'invalidate{h}'].notna()]
   assert train[f'available{h}'].max()<q and train[f'invalidate{h}'].nunique()==2
   model=LGBMClassifier(**PARAMS);model.fit(train[FEATURES],train[f'invalidate{h}'],sample_weight=engine.date_weights(train))
   r[f'hazard{h}']=np.nan;r.loc[eligible,f'hazard{h}']=np.clip(model.predict_proba(test.loc[eligible,FEATURES])[:,1],1e-6,1-1e-6)
   folds.append(dict(quarter=str(q.date()),horizon=h,train=len(train),positives=int(train[f'invalidate{h}'].sum()),test=len(test),latest_training_label=str(train[f'available{h}'].max())))
  pred.append(r);print('V24 auxiliary quarter frozen',q.date(),flush=True)
 scores=pd.concat(pred,ignore_index=True);scores.to_parquet(CACHE/'auxiliary_scores.parquet',index=False)
 source=json.loads((E/'v20_persistent_confirmation/outputs/prediction_receipt.json').read_text());tasks=[]
 for artifact in source['tasks']:
  assert sha(artifact['path'])==artifact['sha256'];old=pd.read_parquet(artifact['path'],filters=[('model','in',CONTROLS)])
  base=old[old.model.eq('risk_diffusion_min')].drop(columns='model').reset_index(drop=True)
  joined=base.merge(scores.drop(columns='state_eligible'),on=IDENTITY,validate='many_to_one');assert np.array_equal(joined.row_id,base.row_id)
  joined['hazard21_gate']=joined.prob*(1-joined.hazard21);joined['hazard63_gate']=joined.prob*(1-joined.hazard63)
  power=np.clip((126-joined.state_age*90*252/365)/21,0,6);joined['survival6_gate']=joined.prob*(1-joined.hazard21)**power
  joined.loc[joined.state_eligible.eq(0),NEW]=0.;assert joined[NEW].notna().all().all()
  rows=[old]
  for name in NEW:
   r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy();rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
   r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
  dest=CACHE/'predictions'/Path(artifact['path']).name;dest.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(dest,index=False);tasks.append(dict(task=artifact['task'],path=str(dest),sha256=sha(dest),source_sha256=artifact['sha256']))
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),scores_sha256=sha(CACHE/'auxiliary_scores.parquet'),targets_sha256=sha(CACHE/'auxiliary_targets.parquet')))
 print('V24 all predictions frozen',flush=True)

if __name__=='__main__':run()
