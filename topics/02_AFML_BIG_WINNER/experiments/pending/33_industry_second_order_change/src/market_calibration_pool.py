"""R14 fixed conditional probability calibration; original models remain sealed."""
import argparse,json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logit,expit
import probability_pool as base
from pool_evaluation import EP,sha
OUT=EP/'outputs/r14'
MARKET=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
FIELDS=['market21','market126','market_vol63','market_breadth_majority']
MODELS=['logit_levels','logit_second']

def market_features(p):
    close=pd.read_parquet(MARKET).close.sort_index()
    m=pd.DataFrame({'market21':close/close.shift(21)-1,'market126':close/close.shift(126)-1,
        'market_vol63':np.log(close).diff().rolling(63,min_periods=63).std()*np.sqrt(252)})
    broad=p[p.eligible].groupby('date').breadth21.apply(lambda x:x.ge(.5).mean())
    q=p[['date']].copy()
    for col in FIELDS[:3]:q[col]=q.date.map(m[col])
    q['market_breadth_majority']=q.date.map(broad)
    return q[FIELDS]

def fit_mapping(raw,y,w,market=None):
    w=np.asarray(w,float);w=w/w.sum();x=logit(np.clip(raw,1e-6,1-1e-6));y=np.asarray(y,float)
    if market is None:
        mean=np.array([]);scale=np.array([]);z=np.empty((len(x),0))
    else:
        v=np.asarray(market,float);assert np.isfinite(v).all()
        mean=np.sum(w[:,None]*v,axis=0);scale=np.sqrt(np.sum(w[:,None]*(v-mean)**2,axis=0));scale=np.where(scale>1e-8,scale,1.)
        z=np.clip((v-mean)/scale,-3,3)
    X=np.column_stack([x,np.ones(len(x)),z]);prior=np.zeros(X.shape[1]);prior[0]=1
    def objective(theta):
        logits=X@theta;diff=theta-prior
        loss=np.sum(w*(np.logaddexp(0,logits)-y*logits))+.05*np.sum(diff*diff)
        grad=X.T@(w*(expit(logits)-y))+.1*diff
        return loss,grad
    result=minimize(objective,prior,jac=True,bounds=[(0,None)]+[(None,None)]*(len(prior)-1),method='L-BFGS-B')
    if not result.success:raise RuntimeError(result.message)
    return {'theta':result.x.tolist(),'mean':mean.tolist(),'scale':scale.tolist(),'loss':float(result.fun),'lambda':.05}

def apply_mapping(raw,params,market=None):
    x=logit(np.clip(raw,1e-6,1-1e-6));theta=np.asarray(params['theta'])
    if len(params['mean']):
        z=(np.asarray(market,float)-params['mean'])/params['scale'];outside=np.any(abs(z)>3,axis=1);z=np.clip(z,-3,3)
    else:z=np.empty((len(x),0));outside=np.zeros(len(x),bool)
    X=np.column_stack([x,np.ones(len(x)),z]);return expit(X@theta),outside

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R14 already sealed; do not overwrite.')
    OUT.mkdir(parents=True,exist_ok=True)
    p=base.data();m=market_features(p);old=pd.read_parquet(EP/'outputs/r12/sealed_predictions.parquet')
    folds=pd.read_csv(EP/'outputs/r12/folds.csv',parse_dates=['cutoff','cal_start']);allpred=[];params=[];usedmodels=[]
    for _,f in folds.iterrows():
        train,cal,test,start=base.split(p,f.cutoff)
        assert cal.end126.lt(f.cutoff).all() and train.end126.lt(start).all()
        for model in MODELS:
            path=EP/f'outputs/r12/models/{f.fold}_{model}.joblib';usedmodels.append(path);bundle=joblib.load(path);features=bundle['metadata']['features']
            rawcal=bundle['model'].predict_proba(cal[features])[:,1]
            oldtest=old[old.fold.eq(f.fold)&old.model.eq(model)].copy()
            assert set(oldtest.row_id)==set(test.index)
            raw=oldtest.raw_probability.to_numpy();testm=m.loc[oldtest.row_id]
            for variant in ['identity','ridge_global','ridge_market']:
                if variant=='identity':prob=raw;outside=np.zeros(len(raw),bool);mapping=None
                else:
                    mapping=fit_mapping(rawcal,cal.win126,base.date_weights(cal),m.loc[cal.index] if variant=='ridge_market' else None)
                    prob,outside=apply_mapping(raw,mapping,testm if variant=='ridge_market' else None)
                z=oldtest.copy();z['model']=model+'__'+variant;z['probability']=prob;z['score']=prob*100;z['market_outside_cal_range']=outside
                allpred.append(z);params.append({'fold':f.fold,'model':model,'variant':variant,'mapping':mapping,'cal_n':len(cal),'cal_max_label_end':str(cal.end126.max())})
        print(f'{f.fold}: two frozen models x three mappings',flush=True)
    z=pd.concat(allpred,ignore_index=True)
    z['reference_probability']=z.groupby(['model','date']).probability.transform('mean');z['predicted_uplift']=z.probability-z.reference_probability
    z['admitted']=base.gate(z.probability,z.reference_probability)
    z.to_parquet(OUT/'sealed_predictions.parquet',index=False);m.to_parquet(OUT/'market_features.parquet',index=True)
    (OUT/'mapping_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    inputs=[Path(__file__),Path(base.__file__),base.SOURCE,MARKET,EP/'configs/pool_metric_v1.json',EP/'rounds/r14_conditional_calibration_plan.md',EP/'outputs/r12/sealed_predictions.parquet',EP/'outputs/r12/folds.csv']+usedmodels
    seal={'stage':'PREDICTIONS_SEALED_BEFORE_EVALUATION','inputs':{str(x):sha(x) for x in inputs},'artifacts':{str(x.relative_to(OUT)):sha(x) for x in OUT.iterdir() if x.is_file()},'adaptive_exploration':True,'future_labels_in_prediction_file':False}
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,indent=2)+'\n')

def evaluate():
    original=base.block_interval
    base.block_interval=lambda z,dates,block=26:original(z,dates,26 if block==25 else block)
    base.OUT=OUT;base.evaluate()
    f=OUT/'evaluation_receipt.json';receipt=json.loads(f.read_text());receipt.update(evaluation_wrapper=str(Path(__file__).resolve()),wrapper_sha256=sha(__file__),primary_bootstrap_weeks=26)
    f.write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['predict','evaluate']);args=a.parse_args();predict() if args.stage=='predict' else evaluate()
