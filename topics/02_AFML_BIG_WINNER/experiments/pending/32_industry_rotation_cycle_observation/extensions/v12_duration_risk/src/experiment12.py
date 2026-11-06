import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context12 import ROOT,V5,V7,V10,CACHE,OLD,OUT,FEATURES,ADDED,KEY,engine,sha,js,freeze
from risk12 import add_risk


def run():
    freeze()
    sr=json.loads((V7/'outputs/state_receipt.json').read_text());assert sha(sr['path'])==sr['sha256']
    state=pd.read_parquet(sr['path']);frames=[]
    source=json.loads((V10/'outputs/prediction_receipt.json').read_text())['tasks']
    assert all(sha(r['path'])==r['sha256'] for r in source)
    js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features=FEATURES,risk_code_sha256=sha(ROOT/'src/risk12.py'),state_sha256=sr['sha256'],previous_prediction_receipt_sha256=sha(V10/'outputs/prediction_receipt.json'),
        blend_weight=.5,candidates=['risk_tree','risk_blend','risk_prior_blend']))
    for key,g in engine.task_frames('b'):
        s=state[state.threshold.eq(key[1])].drop(columns=['threshold','date','era','level','industry_code','block'])
        g=g.merge(s,on='row_id',validate='one_to_one');g['state_excess']=g.state_drawup-g['state_market_'+key[2]]
        g['benchmark_code']=int(key[2]=='CSI_ALL');frames.append(g)
    full=pd.concat(frames,ignore_index=True);identity=KEY+['date','threshold','benchmark']
    unique=full.drop_duplicates(identity)
    g=add_risk(unique)
    assert g[ADDED].notna().all().all()
    feature_path=CACHE/'risk_features.parquet';g[identity+FEATURES+['state_eligible']].loc[:,lambda d:~d.columns.duplicated()].to_parquet(feature_path,index=False)
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
        r=test[identity].copy();r['risk_tree']=0.
        r.loc[eligible,'risk_tree']=np.clip(model.predict_proba(test.loc[eligible,FEATURES])[:,1],1e-6,1-1e-6)
        predictions.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positive=int(train.y.sum()),
            test=len(test),latest_training_label=str(train.label_available_at.max())))
        print('V12 quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True);scores.to_parquet(CACHE/'risk_scores.parquet',index=False)
    tasks=[]
    for artifact in source:
        old=pd.read_parquet(artifact['path']);base=old[old.model.eq('rd_gate')].drop(columns='model')
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base) and np.array_equal(joined.row_id,base.row_id)
        joined['risk_blend']=.5*joined.risk_tree+.5*joined.prob
        joined['risk_prior_blend']=.5*joined.risk_tree+.25*joined.prob+.25*joined.prior*joined.state_eligible
        rows=[old]
        for model in ['risk_tree','risk_blend','risk_prior_blend']:
            r=base.copy();r['model']=model;r['prob']=joined[model].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
        path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256'],frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),
        feature_sha256=sha(feature_path),scores_sha256=sha(CACHE/'risk_scores.parquet')))
    print('V12 all predictions frozen',flush=True)


if __name__=='__main__':
    from pathlib import Path
    run()
