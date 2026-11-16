"""Quarterly mature-only fits. Prediction function accepts no outer labels."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import sys,json,pickle,hashlib
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from common import *
sys.path.insert(0,str(PRIVATE/'vendor'))
import lightgbm as lgb

class TrainTransform:
 def fit(self,x):
  a=x.to_numpy(float);self.median=np.nanmedian(a,axis=0);self.median=np.nan_to_num(self.median,nan=0)
  a=np.where(np.isnan(a),self.median,a);self.mean=a.mean(axis=0);self.sd=a.std(axis=0);self.sd[self.sd<1e-12]=1
  return self
 def transform(self,x):
  a=x.to_numpy(float);a=np.where(np.isnan(a),self.median,a);return (a-self.mean)/self.sd

def split_fit(data,cutoff,scheme):
 mature=data.loc[data.score_eligible & data.target_z.notna() & (data.h10_mature<=cutoff)].copy()
 if scheme=='rolling36':mature=mature.loc[mature.signal_date>=cutoff-pd.DateOffset(months=36)]
 valid=mature.loc[mature.signal_date>=cutoff-pd.DateOffset(months=6)]
 inner=mature.loc[(mature.signal_date<cutoff-pd.DateOffset(months=6)) & (mature.h10_mature<valid.entry_date.min())]
 assert len(valid)>100 and len(inner)>100 and inner.h10_mature.max()<valid.entry_date.min()
 return mature,inner,valid

def predict_only(features,columns,model,transform=None):
 assert 'target_z' not in features and 'h10' not in features
 x=features[columns]
 return model.predict(transform.transform(x) if transform else x)

def run(scheme):
 f=pd.read_parquet(PRIVATE/'features.parquet')
 dd=pd.read_csv(EP/'configs/feature_dictionary.csv');core=dd.loc[dd.group.eq('core'),'feature'].tolist();extended=dd.feature.tolist()
 cfg=protocol();manifest=json.loads((OUT/'manifests/data_snapshot.json').read_text());snapshot=sha(OUT/'manifests/data_snapshot.json')
 root=PRIVATE/'models'/scheme;root.mkdir(parents=True,exist_ok=True);dest=OUT/'fold_predictions'/scheme;dest.mkdir(parents=True,exist_ok=True)
 params=cfg['lightgbm'].copy();early=params.pop('early_stopping_rounds');seeds=cfg['seeds']
 quarters=sorted(f.loc[f.signal_date>='2021-01-01','signal_date'].dt.to_period('Q').unique());receipts=[]
 for quarter in quarters:
  p=dest/(str(quarter)+'.parquet');rp=OUT/'manifests'/f'{scheme}_{quarter}.json'
  if p.exists() and rp.exists():
   r=json.loads(rp.read_text());assert sha(p)==r['prediction_sha256'];assert r['feature_sha256']==manifest['features_sha256'];receipts.append(r);continue
  cutoff=quarter.start_time-pd.Timedelta(nanoseconds=1)
  labels=pd.read_parquet(PRIVATE/'labels.parquet',columns=['signal_date','instrument','h10_mature','entry_date','target_z'],filters=[('h10_mature','<=',cutoff)])
  data=f.loc[f.signal_date<quarter.start_time].merge(labels,on=['signal_date','instrument'],validate='one_to_one')
  mature,inner,valid=split_fit(data,cutoff,scheme)
  test=f.loc[f.signal_date.dt.to_period('Q').eq(quarter)].copy();eligible=test.score_eligible
  pred=test[['signal_date','instrument','score_eligible','missing_reason']].copy()
  pred['E0-RES']=test.residual_score.where(eligible);pred['E0-MOM']=test.mom20.where(eligible);pred['E0-REV']=-test.ret_lag0.where(eligible)
  temp=pred.groupby('signal_date')[['E0-MOM','E0-REV']].transform(lambda s:zscore(s))
  pred['E0-MIX']=temp.mean(axis=1).where(temp.notna().all(axis=1))
  t=TrainTransform().fit(mature[core]);ridge=Ridge(alpha=10).fit(t.transform(mature[core]),mature.target_z)
  pred.loc[eligible,'E1']=predict_only(test.loc[eligible],core,ridge,t)
  model_path=root/(str(quarter)+'_E1.pkl');model_path.write_bytes(pickle.dumps((t,ridge)));models=[dict(model='E1',path=str(model_path),sha256=sha(model_path))]
  for model_id,cols in [('E2',core),('E3',extended)]:
   for seed in seeds:
    model=lgb.LGBMRegressor(**params,random_state=seed)
    model.fit(inner[cols],inner.target_z,eval_set=[(valid[cols],valid.target_z)],callbacks=[lgb.early_stopping(early,verbose=False)])
    rounds=model.best_iteration_;assert 1<=rounds<=1000
    final=lgb.LGBMRegressor(**dict(params,n_estimators=rounds),random_state=seed).fit(mature[cols],mature.target_z)
    assert final.get_params()['subsample_freq']==1 and final.booster_.params['subsample_freq']==1
    key=f'{model_id}_seed{seed}';pred.loc[eligible,key]=predict_only(test.loc[eligible],cols,final)
    mp=root/(str(quarter)+'_'+key+'.txt');final.booster_.save_model(str(mp))
    models.append(dict(model=model_id,seed=seed,rounds=rounds,path=str(mp),sha256=sha(mp)))
   pred[model_id]=pred[[f'{model_id}_seed{s}' for s in seeds]].mean(axis=1)
  pred['universe_id']='CSI300_BaoStock_historical_weekly_proxy';pred['fold_id']=str(quarter);pred['feature_cutoff']=pred.signal_date+pd.Timedelta(hours=18)
  pred['model_fit_cutoff']=cutoff;pred['feature_version']=sha(EP/'configs/feature_dictionary.csv');pred['data_snapshot_id']=snapshot;pred['scheme']=scheme
  # Wide score table is normalized to required long prediction schema.
  keys=[c for c in pred if not c.startswith('E')];scorecols=[c for c in pred if c.startswith('E')]
  pred=pred.melt(id_vars=keys,value_vars=scorecols,var_name='model_id',value_name='score')
  pred['seed_or_ensemble']=pred.model_id.map(lambda s:s.split('_seed')[1] if '_seed' in s else 'equal_seed_ensemble' if s in ['E2','E3'] else 'fixed')
  pred['model_id']=pred.model_id.str.split('_seed').str[0]
  pred.loc[pred.score.isna(),'missing_reason']='INSUFFICIENT_PAST_HISTORY_OR_FEATURES_OR_RESIDUAL_WARMUP'
  pred['score_eligible']=pred.score.notna()
  pred.to_parquet(p,index=False)
  r=dict(scheme=scheme,fold=str(quarter),model_fit_cutoff=cutoff,train_rows=len(mature),train_start=mature.signal_date.min(),train_end=mature.signal_date.max(),max_label_maturity=mature.h10_mature.max(),inner_max_exit=inner.h10_mature.max(),validation_min_entry=valid.entry_date.min(),validation_rows=len(valid),prediction_path=str(p),prediction_sha256=sha(p),feature_sha256=manifest['features_sha256'],models=models,outer_labels_passed_to_prediction=False)
  save_json(rp,r);receipts.append(r);print('trained',scheme,quarter,'rows',len(mature),'rounds',[m.get('rounds') for m in models[1:]],flush=True)
 save_json(OUT/'manifests'/f'{scheme}_predictions.json',receipts)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'expanding')
