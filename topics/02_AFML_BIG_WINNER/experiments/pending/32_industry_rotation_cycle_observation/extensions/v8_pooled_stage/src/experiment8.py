import json
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from lightgbm import LGBMClassifier
from context8 import ROOT,V5,V7,CACHE,STATECACHE,OUT,FEATURES,KEY,engine,sha,js,freeze


def run():
    freeze()
    sr=json.loads((V7/'outputs/state_receipt.json').read_text())
    assert sha(sr['path'])==sr['sha256']
    previous=json.loads((V7/'outputs/prediction_receipt.json').read_text())
    source={r['task']:r for r in previous['tasks']}
    assert all(sha(r['path'])==r['sha256'] for r in source.values())
    protocol=dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),features=FEATURES,
        logistic_C=.01,blend_weight=.5,state_sha256=sr['sha256'],baseline_receipt_sha256=sha(V7/'outputs/prediction_receipt.json'),
        models=['prior','logistic','static_tree','rd_selected','rd_gate','rd_state','rd_conditional','pool_logistic','pool_tree','pool_blend'])
    js(OUT/'frozen_candidates.json',protocol)
    state=pd.read_parquet(sr['path']);frames=[]
    for key,g in engine.task_frames('b'):
        s=state[state.threshold.eq(key[1])].drop(columns=['threshold','date','era','level','industry_code','block'])
        g=g.merge(s,on='row_id',validate='one_to_one')
        g['state_excess']=g.state_drawup-g['state_market_'+key[2]]
        g['benchmark_code']=int(key[2]=='CSI_ALL');frames.append(g)
    full=pd.concat(frames,ignore_index=True)
    identity=KEY+['date','threshold','benchmark']
    unique=full.drop_duplicates(identity)
    duplicates=full[full.duplicated(identity,keep=False)]
    assert duplicates.groupby(identity)[FEATURES].nunique(dropna=False).le(1).all().all()
    assert duplicates.groupby(identity)[['y','label_available_at']].nunique(dropna=False).le(1).all().all()
    trainframe=unique[unique.state_eligible.eq(1)].copy()
    foldrows=[];predictions=[]
    for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
        train=trainframe[trainframe.date.lt(q)&trainframe.label_available_at.lt(q)&trainframe.y.notna()]
        test=unique[unique.date.ge(q)&unique.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
        if test.empty:continue
        eligible=test.state_eligible.eq(1).to_numpy();weights=engine.date_weights(train)
        assert train.label_available_at.max()<q
        x=train[FEATURES];z=test.loc[eligible,FEATURES]
        lr=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),
            LogisticRegression(C=.01,max_iter=1200,random_state=32))
        lr.fit(x,train.y,logisticregression__sample_weight=weights)
        tree=LGBMClassifier(n_estimators=90,num_leaves=7,max_depth=3,min_child_samples=500,learning_rate=.03,reg_lambda=25,
            n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
        tree.fit(x,train.y,sample_weight=weights)
        r=test[identity].copy();r['pool_logistic']=0.;r['pool_tree']=0.
        r.loc[eligible,'pool_logistic']=np.clip(lr.predict_proba(z)[:,1],1e-6,1-1e-6)
        r.loc[eligible,'pool_tree']=np.clip(tree.predict_proba(z)[:,1],1e-6,1-1e-6)
        predictions.append(r)
        foldrows.append(dict(quarter=str(q.date()),train=len(train),positive=int(train.y.sum()),test=len(test),
            latest_training_label=str(train.label_available_at.max())))
        print('V8 pooled quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True)
    assert not scores.duplicated(identity).any()
    scores.to_parquet(CACHE/'pooled_scores.parquet',index=False)
    tasks=[]
    for name,artifact in source.items():
        old=pd.read_parquet(artifact['path'])
        base=old[old.model.eq('rd_gate')].drop(columns='model')
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base)
        assert np.array_equal(joined.row_id.to_numpy(),base.row_id.to_numpy())
        joined['pool_blend']=.5*joined.pool_logistic+.5*joined.prob
        rows=[old]
        for model in ['pool_logistic','pool_tree','pool_blend']:
            r=base.copy();r['model']=model;r['prob']=joined[model].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1)
            rows.append(r)
        dest=CACHE/'predictions'/f'{name}.parquet';dest.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(dest,index=False)
        tasks.append(dict(task=name,path=str(dest),sha256=sha(dest),source_sha256=artifact['sha256'],
            frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=foldrows,frozen_sha256=sha(OUT/'frozen_candidates.json'),
        original_frequency_rows=len(full),deduplicated_rows=len(unique),pooled_scores_sha256=sha(CACHE/'pooled_scores.parquet')))
    print('V8 all predictions frozen',flush=True)


if __name__=='__main__':run()
