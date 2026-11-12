"""R17 contextual event probability, fixed three features and unchanged gate."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import logit,expit
from scipy.optimize import minimize
import probability_pool as engine
from event_probability_pool import PARENT,MODELS,mature_sets,apply_admission_policy
from market_calibration_pool import fit_mapping,apply_mapping
from pool_evaluation import EP,sha
OUT=EP/'outputs/r17'
FEATURES=['delay_fraction','relative_move','market126']

def event_features(g,p):
    events=g[g.candidate_event];anchor=p.loc[events.anchor_row_id.astype(int)].copy();current=p.loc[events.row_id].copy()
    assert (anchor.date.to_numpy()<=current.date.to_numpy()).all()
    for field in ['era','industry_code','block']:assert (anchor[field].to_numpy()==current[field].to_numpy()).all()
    return pd.DataFrame({'delay_fraction':(current.day_i.to_numpy()-anchor.day_i.to_numpy())/126,
        'relative_move':current.x.to_numpy()-anchor.x.to_numpy(),'market126':current.market126.to_numpy()},index=events.index)

def fit_context(raw,y,global_params,features):
    x=logit(np.clip(raw,1e-6,1-1e-6));v=np.asarray(features,float);assert np.isfinite(v).all()
    mean=v.mean(axis=0);scale=v.std(axis=0);scale=np.where(scale>1e-8,scale,1.)
    X=np.column_stack([x,np.ones(len(x)),np.clip((v-mean)/scale,-3,3)]);prior=np.r_[global_params['theta'],np.zeros(v.shape[1])];y=np.asarray(y,float)
    def objective(theta):
        z=X@theta;delta=theta-prior
        return np.mean(np.logaddexp(0,z)-y*z)+.05*np.sum(delta**2),X.T@(expit(z)-y)/len(y)+.1*delta
    result=minimize(objective,prior,jac=True,bounds=[(0,None)]+[(None,None)]*(len(prior)-1),method='L-BFGS-B')
    if not result.success:raise RuntimeError(result.message)
    return {'theta':result.x.tolist(),'mean':mean.tolist(),'scale':scale.tolist(),'loss':float(result.fun),'lambda':.05,'features':FEATURES}

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R17 already sealed')
    OUT.mkdir(parents=True,exist_ok=True)
    p=engine.data();parent=pd.read_parquet(PARENT);parent=parent[parent.model.isin(MODELS)].copy()
    parent['candidate_event']=parent.entry;parent['parent_admitted']=parent.admitted
    context=event_features(parent,p);history=parent.merge(p[['win126','end126']],left_on='row_id',right_index=True,validate='many_to_one')
    parameters=[];records=[];folds=[];indices=[]
    for model,g in history.groupby('model'):
        for cut in pd.date_range('2024-01-01','2026-10-01',freq='QS'):
            fold=cut.strftime('%YQ')+str(cut.quarter);ev,st,ok=mature_sets(g,cut)
            z=parent[parent.model.eq(model)&parent.date.ge(cut)&parent.date.lt(cut+pd.DateOffset(months=3))].copy()
            folds.append(dict(base_model=model,fold=fold,cutoff=cut,event_n=len(ev),event_dates=ev.date.nunique(),state_n=len(st),max_event_label_end=ev.end126.max(),max_state_label_end=st.end126.max(),supported=ok))
            for role,a in [('event',ev),('state',st)]:indices.append(pd.DataFrame({'base_model':model,'fold':fold,'role':role,'row_id':a.row_id}))
            gp=ep=None;outside=np.zeros(len(z),bool)
            if ok:
                gp=fit_mapping(st.raw_probability,st.win126,engine.date_weights(st))
                ep=fit_context(ev.raw_probability,ev.win126,gp,context.loc[ev.index])
                prob,_=apply_mapping(z.raw_probability.to_numpy(),gp)
                mask=z.candidate_event.to_numpy();prob[mask],outside[mask]=apply_mapping(z.loc[z.candidate_event,'raw_probability'].to_numpy(),ep,context.loc[z.index[z.candidate_event]])
            else:prob=np.full(len(z),np.nan)
            name=model.replace('__identity','')+'__event_context';z['model']=name;z['calibration_supported']=ok;z['probability']=prob;z['score']=100*prob
            z['event_context_outside_range']=outside;z['score_domain']=np.where(z.candidate_event,'UNIQUE_CANDIDATE_EVENT','INDUSTRY_WEEK_STATE')
            records.append(z);parameters.append(dict(base_model=model,model=name,fold=fold,supported=ok,global_mapping=gp,event_mapping=ep))
    result=pd.concat(records,ignore_index=True);result['reference_probability']=result.groupby(['model','date']).probability.transform('mean');result['predicted_uplift']=result.probability-result.reference_probability
    result=pd.concat([apply_admission_policy(g) for _,g in result.groupby('model')],ignore_index=True)
    result.to_parquet(OUT/'sealed_predictions.parquet',index=False)
    context.assign(row_id=parent.loc[context.index,'row_id'],base_model=parent.loc[context.index,'model']).to_parquet(OUT/'event_features.parquet',index=False)
    pd.DataFrame(folds).to_csv(OUT/'calibration_folds.csv',index=False);pd.concat(indices,ignore_index=True).to_csv(OUT/'calibration_rows.csv.gz',index=False)
    (OUT/'mapping_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
    inputs=[PARENT,engine.SOURCE,Path(__file__),EP/'src/event_probability_pool.py',EP/'src/market_calibration_pool.py',Path(engine.__file__),EP/'rounds/r17_event_context_plan.md',EP/'rounds/r16_reflection.md',EP/'configs/pool_metric_v1.json']
    (OUT/'prediction_seal.json').write_text(json.dumps({'stage':'EVENT_CONTEXT_PROBABILITIES_SEALED_BEFORE_EVALUATION','inputs':{str(f):sha(f) for f in inputs},'artifacts':{str(f.relative_to(OUT)):sha(f) for f in OUT.iterdir() if f.is_file()},'adaptive_historical_exploration':True},indent=2)+'\n')
    print('R17 two contextual event models sealed.')

def evaluate():
    original=engine.block_interval;engine.block_interval=lambda z,dates,block=26:original(z,dates,26 if block==25 else block)
    engine.OUT=OUT;engine.admission_events=lambda g:g.sort_values(engine.KEY+['date']).copy();engine.evaluate()
    path=OUT/'evaluation_receipt.json';r=json.loads(path.read_text());r.update(evaluation_wrapper=str(Path(__file__).resolve()),wrapper_sha256=sha(__file__),primary_bootstrap_weeks=26);path.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['predict','evaluate']);args=a.parse_args();predict() if args.stage=='predict' else evaluate()
