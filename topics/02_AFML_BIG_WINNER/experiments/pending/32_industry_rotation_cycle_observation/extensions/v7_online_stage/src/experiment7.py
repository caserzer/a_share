"""Fixed candidates and baselines; prediction generation never scores outcomes."""
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context7 import ROOT,V5,CACHE,OLD,OUT,STATE,engine,sha,js,finite_json

MODELS=['prior','logistic','static_tree','rd_selected','rd_gate','rd_state','rd_conditional']


def state_predict(train,test,spec):
    w=engine.date_weights(train)
    prior=float(np.average(train.y,weights=w))
    if train.y.nunique()<2:return np.full(len(test),prior)
    x=engine.compile_features(train,spec);z=engine.compile_features(test,spec)
    for c in STATE:x[c]=train[c].to_numpy();z[c]=test[c].to_numpy()
    m=LGBMClassifier(n_estimators=int(spec['trees']),num_leaves=int(spec['leaves']),max_depth=int(spec['max_depth']),
        min_child_samples=int(spec['min_child_samples']),learning_rate=spec['learning_rate'],reg_lambda=spec['reg_lambda'],
        n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
    m.fit(x,train.y,sample_weight=w)
    return np.clip(m.predict_proba(z)[:,1],1e-6,1-1e-6)


def predict():
    spec=json.loads((V5/'outputs/stage_b/frozen_selection.json').read_text())['winner']['spec']
    sr=json.loads((OUT/'state_receipt.json').read_text());assert sha(sr['path'])==sr['sha256']
    prior_receipt=json.loads((V5/'outputs/stage_b/prediction_receipt.json').read_text())
    assert sha(prior_receipt['path'])==prior_receipt['sha256']
    protocol=dict(spec=spec,models=MODELS,state_features=STATE,plan_sha256=sha(ROOT/'research_plan.md'),
        code_sha256=sha(__file__),state_sha256=sr['sha256'],old_predictions_sha256=prior_receipt['sha256'],
        old_inputs=sr['inputs'],search=False)
    dest=OUT/'frozen_candidates.json'
    if dest.exists():assert json.loads(dest.read_text())==protocol
    else:js(dest,protocol)
    state=pd.read_parquet(sr['path']);old=pd.read_parquet(prior_receipt['path'])
    reuse={k:g for k,g in old.groupby(['frequency','threshold','benchmark','quarter'])}
    quarters=pd.date_range('2021-01-01','2026-10-01',freq='QS')
    artifacts=[]
    for key,g in engine.task_frames('b'):
        name=f'{key[0]}_{key[1]}_{key[2]}'
        path=CACHE/'predictions'/f'{name}.parquet';receipt=OUT/'tasks'/f'{name}.json'
        if receipt.exists():
            r=json.loads(receipt.read_text());assert sha(path)==r['sha256'] and r['frozen_sha256']==sha(dest)
            artifacts.append(r);continue
        s=state[state.threshold.eq(key[1])].drop(columns=['threshold','date','era','level','industry_code','block'])
        g=g.merge(s,on='row_id',validate='one_to_one')
        g['state_excess']=g.state_drawup-g['state_market_'+key[2]]
        assert g[STATE].notna().all().all()
        rows=[];folds=[]
        for q in quarters:
            train=g[g.date.lt(q)&g.label_available_at.lt(q)&g.y.notna()]
            test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
            if test.empty:continue
            assert len(train)>500 and train.y.sum()>=5 and train.label_available_at.max()<q
            weights=engine.date_weights(train);prior=float(np.average(train.y,weights=weights))
            reused=reuse.get((*key,str(q.date())))
            base=dict(engine.BASELINES);base['rd_selected']=spec;pred={}
            for model,config in base.items():
                if reused is not None:
                    r=reused[reused.model.eq(model)].set_index('row_id')
                    assert set(r.index)==set(test.row_id)
                    assert np.allclose(r.prior,prior)
                    pred[model]=r.prob.reindex(test.row_id).to_numpy()
                else:pred[model],_=engine.fit_predict(train,test,config)
            eligible=test.state_eligible.eq(1).to_numpy()
            pred['rd_gate']=np.where(eligible,pred['rd_selected'],0.)
            pred['rd_state']=np.where(eligible,state_predict(train,test,spec),0.)
            conditional=train[train.state_eligible.eq(1)]
            cp=np.zeros(len(test))
            if eligible.any():
                cp[eligible]=state_predict(conditional,test[eligible],spec) if len(conditional) else prior
            pred['rd_conditional']=cp
            for model,prob in pred.items():
                r=test[['row_id','date','era','level','industry_code','frequency','threshold','benchmark','state_eligible']].copy()
                r['quarter']=str(q.date());r['model']=model;r['prob']=prob;r['prior']=prior
                rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
                r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1)
                rows.append(r)
            folds.append(dict(quarter=str(q.date()),train=len(train),train_positive=int(train.y.sum()),
                conditional_train=len(conditional),conditional_positive=int(conditional.y.sum()),test=len(test),
                latest_training_label=str(train.label_available_at.max()),baseline_reused=reused is not None))
        path.parent.mkdir(parents=True,exist_ok=True);pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        r=dict(task=name,path=str(path),sha256=sha(path),frozen_sha256=sha(dest),folds=folds)
        js(receipt,r);artifacts.append(r)
        print('V7 predictions frozen',name,flush=True)
    js(OUT/'prediction_receipt.json',dict(tasks=artifacts,frozen_sha256=sha(dest),scoring_started=False))


if __name__=='__main__':predict()
