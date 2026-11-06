from pathlib import Path
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMRanker
from context15 import ROOT,V13,CACHE,OUT,FEATURES,KEY,engine,sha,js,freeze
from rank15 import redistribute


def run():
    freeze()
    source=json.loads((V13/'outputs/prediction_receipt.json').read_text())
    path=CACHE.parent/'history_v13/history_features.parquet';assert sha(path)==source['feature_sha256']
    assert all(sha(r['path'])==r['sha256'] for r in source['tasks'])
    js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features=FEATURES,rank_code_sha256=sha(ROOT/'src/rank15.py'),source_features_sha256=sha(path),
        previous_prediction_receipt_sha256=sha(V13/'outputs/prediction_receipt.json'),strengths=[.5,1.],
        candidates=['rank_half','rank_one','rank_hedged']))
    features=pd.read_parquet(path);identity=KEY+['date','threshold','benchmark'];labels=[]
    for _,g in engine.task_frames('b'):labels.append(g[identity+['y','label_available_at','reason','event_or_witness_id']])
    labels=pd.concat(labels,ignore_index=True).drop_duplicates(identity)
    g=features.merge(labels,on=identity,validate='one_to_one');training=g[g.state_eligible.eq(1)]
    groups=['date','level','threshold','benchmark'];predictions=[];folds=[]
    for q in pd.date_range('2021-01-01','2026-10-01',freq='QS'):
        train=training[training.date.lt(q)&training.label_available_at.lt(q)&training.y.notna()].sort_values(groups)
        test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
        if test.empty:continue
        eligible=test.state_eligible.eq(1).to_numpy();size=train.groupby(groups,sort=False).size().to_numpy()
        assert size.sum()==len(train) and train.label_available_at.max()<q
        model=LGBMRanker(objective='lambdarank',lambdarank_truncation_level=31,n_estimators=90,num_leaves=7,max_depth=3,
            min_child_samples=500,learning_rate=.03,reg_lambda=25,n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
        model.fit(train[FEATURES],train.y.astype(int),group=size,sample_weight=engine.date_weights(train))
        r=test[identity].copy();r['rank_score']=np.nan;r.loc[eligible,'rank_score']=model.predict(test.loc[eligible,FEATURES])
        predictions.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positive=int(train.y.sum()),groups=len(size),
            test=len(test),latest_training_label=str(train.label_available_at.max())))
        print('V15 ranker quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True);scores.to_parquet(CACHE/'rank_scores.parquet',index=False)
    tasks=[]
    for artifact in source['tasks']:
        old=pd.read_parquet(artifact['path']);base=old[old.model.eq('risk_prior_blend')].drop(columns='model').reset_index(drop=True)
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base) and np.array_equal(joined.row_id,base.row_id)
        joined['rank_half']=0.;joined['rank_one']=0.
        for _,ix in joined[joined.state_eligible.eq(1)].groupby(['date','level']).groups.items():
            sub=joined.loc[ix];anchor=float(sub.prob.mean())
            for name,strength in [('rank_half',.5),('rank_one',1.)]:joined.loc[ix,name]=redistribute(sub.rank_score,anchor,strength)
        joined['rank_hedged']=.5*joined.rank_half+.5*joined.prob
        rows=[old]
        for name in ['rank_half','rank_one','rank_hedged']:
            r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
        path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256'],frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),scores_sha256=sha(CACHE/'rank_scores.parquet')))
    print('V15 all predictions frozen',flush=True)


if __name__=='__main__':run()
