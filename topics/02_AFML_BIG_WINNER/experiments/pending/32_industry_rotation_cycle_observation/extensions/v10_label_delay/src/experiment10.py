from pathlib import Path
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context10 import ROOT,V7,V9,CACHE,OUT,FEATURES,KEY,engine,sha,js,freeze


def admitted(g,q,months):
    return g[g.date.lt(q-pd.DateOffset(months=months))&g.label_available_at.lt(q)&g.y.notna()
        &g.label_available_at.le(g.date+pd.DateOffset(months=24))].copy()


def inverse_delay_weights(train,reference,q):
    weights=np.ones(len(train));positions=pd.Series(np.arange(len(train)),index=train.index)
    for key,sub in train.groupby(['threshold','benchmark','y']):
        ref=reference[reference.threshold.eq(key[0])&reference.benchmark.eq(key[1])&reference.y.eq(key[2])]
        if len(ref)<20:ref=reference[reference.y.eq(key[2])]
        if not len(ref):continue
        lag=np.sort((ref.label_available_at-ref.date).dt.days.to_numpy())
        age=(q-sub.date).dt.days.to_numpy()
        probability=np.searchsorted(lag,age,side='right')/len(lag)
        weights[positions.loc[sub.index].to_numpy()]=1/np.maximum(probability,.2)
    return weights


def run():
    freeze()
    sr=json.loads((V7/'outputs/state_receipt.json').read_text());assert sha(sr['path'])==sr['sha256']
    source=json.loads((V9/'outputs/prediction_receipt.json').read_text())['tasks']
    assert all(sha(r['path'])==r['sha256'] for r in source)
    candidates=['lag12_tree','lag24_tree','delay_weighted_tree']
    js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features=FEATURES,candidates=candidates,minimum_delay_probability=.2,
        previous_prediction_receipt_sha256=sha(V9/'outputs/prediction_receipt.json'),state_sha256=sr['sha256']))
    s=pd.read_parquet(sr['path']);frames=[]
    for key,g in engine.task_frames('b'):
        state=s[s.threshold.eq(key[1])].drop(columns=['threshold','date','era','level','industry_code','block'])
        g=g.merge(state,on='row_id',validate='one_to_one');g['state_excess']=g.state_drawup-g['state_market_'+key[2]]
        g['benchmark_code']=int(key[2]=='CSI_ALL');frames.append(g)
    full=pd.concat(frames,ignore_index=True);identity=KEY+['date','threshold','benchmark']
    unique=full.drop_duplicates(identity);training=unique[unique.state_eligible.eq(1)]
    predictions=[];folds=[]
    for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
        test=unique[unique.date.ge(q)&unique.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
        if test.empty:continue
        eligible=test.state_eligible.eq(1).to_numpy();reference=admitted(training,q,24)
        r=test[identity].copy()
        for name in candidates:
            train=admitted(training,q,24 if name=='lag24_tree' else 12)
            assert train.label_available_at.max()<q and train.y.nunique()==2
            weights=engine.date_weights(train);delay=np.ones(len(train))
            if name=='delay_weighted_tree':delay=inverse_delay_weights(train,reference,q)
            weights=weights*delay
            group_sum=pd.Series(weights,index=train.index).groupby([train.date,train.level]).transform('sum').to_numpy()
            weights=weights/group_sum;weights/=weights.mean()
            model=LGBMClassifier(n_estimators=90,num_leaves=7,max_depth=3,min_child_samples=500,learning_rate=.03,reg_lambda=25,
                n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
            model.fit(train[FEATURES],train.y,sample_weight=weights)
            r[name]=0.;r.loc[eligible,name]=np.clip(model.predict_proba(test.loc[eligible,FEATURES])[:,1],1e-6,1-1e-6)
            folds.append(dict(quarter=str(q.date()),model=name,train=len(train),positive=int(train.y.sum()),
                latest_training_origin=str(train.date.max()),latest_training_label=str(train.label_available_at.max()),
                reference_rows=len(reference),latest_reference_origin=str(reference.date.max()),
                max_delay_weight=float(delay.max()),mean_delay_weight=float(delay.mean())))
        predictions.append(r);print('V10 quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True);scores.to_parquet(CACHE/'delay_scores.parquet',index=False)
    tasks=[]
    for artifact in source:
        old=pd.read_parquet(artifact['path']);base=old[old.model.eq('rd_gate')].drop(columns='model')
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base) and np.array_equal(joined.row_id,base.row_id)
        rows=[old]
        for name in candidates:
            r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
        path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256'],frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),scores_sha256=sha(CACHE/'delay_scores.parquet')))
    print('V10 all predictions frozen',flush=True)


if __name__=='__main__':run()
