from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/long_v21')
sys.path.insert(0,str(E/'v12_duration_risk/src'))
from context12 import FEATURES,KEY,engine,sha,js
ADDED=['mom5','mom126','mom252','dd21','dd63','dd126','dd252','vol21','excess126','excess252','market126','market252','market_dd126','market_dd252','market_vol63','peer_up126','peer_excess126_median']
PARAMS=dict(n_estimators=240,num_leaves=15,max_depth=4,min_child_samples=200,learning_rate=.03,reg_lambda=25,n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
IDENTITY=KEY+['date','threshold','benchmark']

def market_features(b):
 return pd.DataFrame(dict(market252=b/b.shift(252)-1,market_dd126=b/b.rolling(126,min_periods=126).max()-1,market_dd252=b/b.rolling(252,min_periods=252).max()-1,market_vol63=b.pct_change(fill_method=None).rolling(63,min_periods=63).std()*np.sqrt(252)))

def run():
 CACHE.mkdir(exist_ok=True,parents=True);v18=E/'v18_conditional_diffusion'
 prev=json.loads((v18/'outputs/predecessors.json').read_text());m=json.loads((v18/'outputs/manifest.json').read_text())
 prev.update({str(v18/f['path']):f['sha256'] for f in m['files']});prev[str(v18/'outputs/manifest.json')]=sha(v18/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in prev.items());js(OUT/'predecessors.json',prev)
 risk=CACHE.parent/'duration_v12/risk_features.parquet';assert sha(risk)==json.loads((E/'v12_duration_risk/outputs/prediction_receipt.json').read_text())['feature_sha256']
 source=json.loads((v18/'outputs/prediction_receipt.json').read_text())
 hashes={str(risk):sha(risk)}
 for bm in ['CSI300','CSI_ALL']:hashes[str(CACHE.parent/'forecast_v5'/f'{bm}.parquet')]=sha(CACHE.parent/'forecast_v5'/f'{bm}.parquet')
 js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),base_features=FEATURES,added_features=ADDED,params=PARAMS,inputs=hashes,models=['long_tree','long_blend']))
 base=pd.read_parquet(risk);frames=[]
 for _,f in engine.task_frames('b'):frames.append(f[IDENTITY+ADDED[:11]+['y','label_available_at']])
 f=pd.concat(frames,ignore_index=True).drop_duplicates(IDENTITY);g=base.merge(f,on=IDENTITY,validate='one_to_one')
 for bm in ['CSI300','CSI_ALL']:
  b=pd.read_parquet(CACHE.parent/'forecast_v5'/f'{bm}.parquet').close
  feat=market_features(b);prefix=market_features(b.iloc[:len(b)//2]);assert np.allclose(feat.loc[prefix.index],prefix,equal_nan=True)
  for c in feat:g.loc[g.benchmark.eq(bm),c]=g.loc[g.benchmark.eq(bm),'date'].map(feat[c])
 peer=g.drop_duplicates(KEY+['date','benchmark']).copy();peer['up126']=peer.mom126.gt(0).where(peer.mom126.notna())
 peer=peer.groupby(['era','level','date','benchmark']).agg(peer_up126=('up126','mean'),peer_excess126_median=('excess126','median')).reset_index()
 g=g.merge(peer,on=['era','level','date','benchmark'],validate='many_to_one');assert len(g)==len(base)
 features=FEATURES+ADDED;assert len(features)==len(set(features))
 g[IDENTITY+features+['state_eligible']].to_parquet(CACHE/'features.parquet',index=False)
 training=g[g.state_eligible.eq(1)];pred=[];folds=[];importance=[]
 for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
  train=training[training.date.lt(q)&training.label_available_at.lt(q)&training.y.notna()]
  test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at'])
  if test.empty:continue
  assert train.label_available_at.max()<q;eligible=test.state_eligible.eq(1)
  model=LGBMClassifier(**PARAMS);model.fit(train[features],train.y,sample_weight=engine.date_weights(train))
  r=test[IDENTITY].copy();r['long_tree']=0.;r.loc[eligible,'long_tree']=np.clip(model.predict_proba(test.loc[eligible,features])[:,1],1e-6,1-1e-6)
  pred.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positives=int(train.y.sum()),test=len(test),latest_training_label=str(train.label_available_at.max())))
  importance.extend([dict(quarter=str(q.date()),feature=c,gain=float(v)) for c,v in zip(features,model.booster_.feature_importance(importance_type='gain'))])
  print('V21 quarter frozen',q.date(),flush=True)
 scores=pd.concat(pred,ignore_index=True);scores.to_parquet(CACHE/'scores.parquet',index=False);pd.DataFrame(importance).to_csv(OUT/'feature_importance.csv',index=False)
 tasks=[]
 for artifact in source['tasks']:
  assert sha(artifact['path'])==artifact['sha256'];old=pd.read_parquet(artifact['path']);base=old[old.model.eq('diffusion_tree')].drop(columns='model').reset_index(drop=True)
  joined=base.merge(scores,on=IDENTITY,validate='many_to_one');assert np.array_equal(joined.row_id,base.row_id)
  joined['long_blend']=.5*joined.long_tree+.5*joined.prob;rows=[old]
  for name in ['long_tree','long_blend']:
   r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy();rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
   r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
  path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
  pd.concat(rows,ignore_index=True).to_parquet(path,index=False);tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256']))
 js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),features_sha256=sha(CACHE/'features.parquet'),scores_sha256=sha(CACHE/'scores.parquet')))
 print('V21 all predictions frozen',flush=True)

if __name__=='__main__':run()
