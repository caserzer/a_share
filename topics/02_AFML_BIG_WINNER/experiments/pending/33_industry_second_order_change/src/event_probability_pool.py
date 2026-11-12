"""R16 event-specific prequential calibration on strictly mature historical predictions."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from scipy.optimize import minimize
import probability_pool as engine
from market_calibration_pool import fit_mapping,apply_mapping
from pool_evaluation import EP,KEY,sha
OUT=EP/'outputs/r16'
PARENT=EP/'outputs/r15/sealed_predictions.parquet'
MODELS=['logit_levels__identity','logit_second__identity']
VARIANTS=['state_oof','event_offset','event_platt']

def mature_sets(g,cut):
    h=g[g.end126.lt(cut)&g.win126.notna()]
    events=h[h.candidate_event];state=h[~h.candidate_event]
    ok=len(events)>=100 and events.date.nunique()>=12 and len(state)>=500 and state.date.nunique()>=12 and events.win126.nunique()==2 and state.win126.nunique()==2
    return events,state,ok

def fit_event(raw,y,global_params,kind):
    x=logit(np.clip(raw,1e-6,1-1e-6));y=np.asarray(y,float);prior=np.asarray(global_params['theta'])
    if kind=='event_offset':
        offset=prior[0]*x+prior[1];X=np.ones((len(x),1));start=np.zeros(1);bounds=[(None,None)]
    else:offset=np.zeros(len(x));X=np.column_stack([x,np.ones(len(x))]);start=prior.copy();bounds=[(0,None),(None,None)]
    def objective(theta):
        z=offset+X@theta;d=theta-start
        return np.mean(np.logaddexp(0,z)-y*z)+.05*np.sum(d*d),X.T@(expit(z)-y)/len(y)+.1*d
    result=minimize(objective,start,jac=True,bounds=bounds,method='L-BFGS-B')
    if not result.success:raise RuntimeError(result.message)
    theta=prior+np.array([0,result.x[0]]) if kind=='event_offset' else result.x
    return {'theta':theta.tolist(),'mean':[],'scale':[],'loss':float(result.fun),'kind':kind,'lambda':.05}

def apply_admission_policy(g):
    g=g.sort_values(KEY+['date']).copy();g['entry']=False;g['admitted']=False
    g['candidate_pass']=g.candidate_event&g.calibration_supported&engine.gate(g.probability,g.reference_probability)
    accepted=set(g.loc[g.candidate_pass,'opportunity_id'].dropna())
    # Opportunity IDs already include era/code/block, and each model is processed separately.
    g['entry']=g.candidate_pass
    g['admitted']=g.opportunity_id.isin(accepted)&g.parent_admitted&g.calibration_supported&engine.gate(g.probability,g.reference_probability)
    # prefix constraint: accepted state may only start at or after its event decision.
    starts=g[g.entry].set_index('opportunity_id').date
    g['admitted']&=g.date.ge(g.opportunity_id.map(starts))
    g['formal_entry']=g.entry
    g['state_edge']=g.admitted&g.groupby(KEY).admitted.shift().eq(False)&g.week_i.sub(g.groupby(KEY).week_i.shift()).eq(1)
    g['refit_entry']=g.entry&g.fold.ne(g.groupby(KEY).fold.shift());g['cooldown126']=False
    for _,a in g[g.entry].groupby(KEY):
        last=-100000
        for ix,r in a.iterrows():
            if r.day_i-last>=126:g.loc[ix,'cooldown126']=True;last=r.day_i
    assert not g[g.entry].duplicated('opportunity_id').any()
    assert not (g.entry&~g.candidate_event).any()
    return g

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R16 already sealed')
    OUT.mkdir(parents=True,exist_ok=True)
    p=engine.data();parent=pd.read_parquet(PARENT);parent=parent[parent.model.isin(MODELS)].copy()
    parent['candidate_event']=parent.entry;parent['parent_admitted']=parent.admitted
    history=parent.merge(p[['win126','end126']],left_on='row_id',right_index=True,validate='many_to_one')
    records=[];parameters=[];folds=[];fitrows=[]
    for model,g in history.groupby('model'):
        for cut in pd.date_range('2024-01-01','2026-10-01',freq='QS'):
            fold=cut.strftime('%YQ')+str(cut.quarter);ev,st,ok=mature_sets(g,cut)
            current=parent[parent.model.eq(model)&parent.date.ge(cut)&parent.date.lt(cut+pd.DateOffset(months=3))].copy()
            folds.append(dict(base_model=model,fold=fold,cutoff=cut,event_n=len(ev),event_dates=ev.date.nunique(),state_n=len(st),max_event_label_end=ev.end126.max(),max_state_label_end=st.end126.max(),supported=ok))
            for role,z in [('event',ev),('state',st)]:fitrows.append(pd.DataFrame({'base_model':model,'fold':fold,'role':role,'row_id':z.row_id}))
            gp=fit_mapping(st.raw_probability,st.win126,engine.date_weights(st)) if ok else None
            for variant in VARIANTS:
                z=current.copy();z['model']=model.replace('__identity','')+'__'+variant
                z['calibration_supported']=ok;z['score_domain']=np.where(z.candidate_event,'UNIQUE_CANDIDATE_EVENT','INDUSTRY_WEEK_STATE')
                ep=None
                if ok:
                    prob,_=apply_mapping(z.raw_probability.to_numpy(),gp)
                    ep=gp if variant=='state_oof' else fit_event(ev.raw_probability,ev.win126,gp,variant)
                    mask=z.candidate_event.to_numpy();prob[mask],_=apply_mapping(z.loc[z.candidate_event,'raw_probability'].to_numpy(),ep)
                else:prob=np.full(len(z),np.nan)
                z['probability']=prob;z['score']=100*prob
                records.append(z);parameters.append(dict(base_model=model,model=z.model.iloc[0],fold=fold,supported=ok,global_mapping=gp,event_mapping=ep))
            print(model,fold,'mature events',len(ev),'supported',ok,flush=True)
    result=pd.concat(records,ignore_index=True)
    result['reference_probability']=result.groupby(['model','date']).probability.transform('mean');result['predicted_uplift']=result.probability-result.reference_probability
    result=pd.concat([apply_admission_policy(g) for _,g in result.groupby('model')],ignore_index=True)
    result.to_parquet(OUT/'sealed_predictions.parquet',index=False);pd.DataFrame(folds).to_csv(OUT/'calibration_folds.csv',index=False)
    pd.concat(fitrows,ignore_index=True).to_csv(OUT/'calibration_rows.csv.gz',index=False)
    (OUT/'mapping_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
    inputs=[PARENT,engine.SOURCE,Path(__file__),EP/'src/market_calibration_pool.py',Path(engine.__file__),EP/'rounds/r16_event_calibration_plan.md',EP/'configs/pool_metric_v1.json']
    (OUT/'prediction_seal.json').write_text(json.dumps({'stage':'EVENT_PROBABILITIES_SEALED_BEFORE_EVALUATION','inputs':{str(f):sha(f) for f in inputs},'artifacts':{str(f.relative_to(OUT)):sha(f) for f in OUT.iterdir() if f.is_file()},'adaptive_historical_exploration':True,'unsupported_fold_policy':'all probabilities UNKNOWN; retained in opportunity coverage denominator'},indent=2)+'\n')

def evaluate():
    original=engine.block_interval;engine.block_interval=lambda z,dates,block=26:original(z,dates,26 if block==25 else block)
    engine.OUT=OUT;engine.admission_events=lambda g:g.sort_values(KEY+['date']).copy();engine.evaluate()
    f=OUT/'evaluation_receipt.json';r=json.loads(f.read_text());r.update(evaluation_wrapper=str(Path(__file__).resolve()),wrapper_sha256=sha(__file__),primary_bootstrap_weeks=26);f.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['predict','evaluate']);args=a.parse_args();predict() if args.stage=='predict' else evaluate()
