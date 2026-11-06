import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context9 import ROOT,V5,V7,V8,CACHE,OLD,OUT,FEATURES,MARKET,ADDED,KEY,engine,trace,sha,js,freeze


def add_context(unique):
    markets=[]
    for bm in ['CSI300','CSI_ALL']:
        close=pd.read_parquet(OLD/f'{bm}.parquet').close.dropna()
        for threshold in [.1,.15,.2]:
            m=trace(close.to_numpy(),close.index,threshold)
            m=m[['date','candidate_low_date']+MARKET].rename(columns={c:'market_'+c for c in ['candidate_low_date']+MARKET})
            m['benchmark']=bm;m['threshold']=threshold;markets.append(m)
    g=unique.merge(pd.concat(markets,ignore_index=True),on=['date','benchmark','threshold'],validate='many_to_one')
    g['relative_low_age']=(g.candidate_low_date-g.market_candidate_low_date).dt.days/90.
    groups=['date','level','benchmark','threshold']
    g['up']=g.state_direction.eq(1).astype(float);g['positive_excess']=g.excess21.gt(0).astype(float)
    for dest,source,op in [('cross_up','up','mean'),('cross_eligible','state_eligible','mean'),
        ('cross_positive_excess','positive_excess','mean'),('cross_breadth','breadth21','mean'),
        ('cross_excess_dispersion','excess21','std')]:g[dest]=g.groupby(groups)[source].transform(op)
    for c in ['excess21','excess63']:g[c+'_rank']=g.groupby(groups)[c].rank(pct=True)
    return g


def run():
    freeze()
    sr=json.loads((V7/'outputs/state_receipt.json').read_text());assert sha(sr['path'])==sr['sha256']
    state=pd.read_parquet(sr['path']);frames=[]
    source=json.loads((V8/'outputs/prediction_receipt.json').read_text())['tasks']
    assert all(sha(r['path'])==r['sha256'] for r in source)
    js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features=FEATURES,state_sha256=sr['sha256'],previous_prediction_receipt_sha256=sha(V8/'outputs/prediction_receipt.json'),
        blend_weight=.5,candidates=['context_tree','context_blend','context_cap']))
    for key,g in engine.task_frames('b'):
        s=state[state.threshold.eq(key[1])].drop(columns=['threshold','date','era','level','industry_code','block'])
        g=g.merge(s,on='row_id',validate='one_to_one');g['state_excess']=g.state_drawup-g['state_market_'+key[2]]
        g['benchmark_code']=int(key[2]=='CSI_ALL');frames.append(g)
    full=pd.concat(frames,ignore_index=True);identity=KEY+['date','threshold','benchmark']
    unique=full.drop_duplicates(identity)
    g=add_context(unique)
    assert g[ADDED].notna().all().all()
    feature_path=CACHE/'context_features.parquet';g[identity+FEATURES+['state_eligible']].loc[:,lambda d:~d.columns.duplicated()].to_parquet(feature_path,index=False)
    training=g[g.state_eligible.eq(1)];predictions=[];folds=[]
    for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
        train=training[training.date.lt(q)&training.label_available_at.lt(q)&training.y.notna()]
        test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
        if test.empty:continue
        eligible=test.state_eligible.eq(1).to_numpy();weights=engine.date_weights(train)
        assert train.label_available_at.max()<q
        model=LGBMClassifier(n_estimators=90,num_leaves=7,max_depth=3,min_child_samples=500,learning_rate=.03,reg_lambda=25,
            n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
        model.fit(train[FEATURES],train.y,sample_weight=weights)
        r=test[identity].copy();r['context_tree']=0.
        r.loc[eligible,'context_tree']=np.clip(model.predict_proba(test.loc[eligible,FEATURES])[:,1],1e-6,1-1e-6)
        predictions.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positive=int(train.y.sum()),
            test=len(test),latest_training_label=str(train.label_available_at.max())))
        print('V9 quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True);scores.to_parquet(CACHE/'context_scores.parquet',index=False)
    tasks=[]
    for artifact in source:
        old=pd.read_parquet(artifact['path']);base=old[old.model.eq('rd_gate')].drop(columns='model')
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base) and np.array_equal(joined.row_id,base.row_id)
        joined['context_blend']=.5*joined.context_tree+.5*joined.prob
        joined['context_cap']=np.minimum(joined.context_tree,joined.prob)
        rows=[old]
        for model in ['context_tree','context_blend','context_cap']:
            r=base.copy();r['model']=model;r['prob']=joined[model].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
        path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256'],frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),
        feature_sha256=sha(feature_path),scores_sha256=sha(CACHE/'context_scores.parquet')))
    print('V9 all predictions frozen',flush=True)


if __name__=='__main__':
    from pathlib import Path
    run()
