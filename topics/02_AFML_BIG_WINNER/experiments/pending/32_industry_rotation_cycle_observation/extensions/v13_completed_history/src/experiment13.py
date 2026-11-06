from pathlib import Path
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context13 import ROOT,V5,V12,CACHE,OLD,OUT,FEATURES,KEY,engine,sha,js,freeze
from history13 import add_history


def run():
    freeze()
    prior=json.loads((V12/'outputs/prediction_receipt.json').read_text())
    risk_path=CACHE.parent/'duration_v12/risk_features.parquet'
    phase_path=OLD/'daily_phases.parquet'
    assert sha(risk_path)==prior['feature_sha256']
    assert sha(phase_path)==json.loads((V5/'outputs/label_audit.json').read_text())['phases_sha256']
    assert all(sha(r['path'])==r['sha256'] for r in prior['tasks'])
    js(OUT/'frozen_candidates.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features=FEATURES,history_code_sha256=sha(ROOT/'src/history13.py'),phase_sha256=sha(phase_path),
        risk_features_sha256=sha(risk_path),previous_prediction_receipt_sha256=sha(V12/'outputs/prediction_receipt.json'),
        prior_strength=10,candidates=['history_tree','history_blend','history_prior_blend']))
    f=add_history(pd.read_parquet(risk_path),pd.read_parquet(phase_path))
    feature_path=CACHE/'history_features.parquet';f.to_parquet(feature_path,index=False)
    identity=KEY+['date','threshold','benchmark'];labels=[]
    for _,g in engine.task_frames('b'):labels.append(g[identity+['y','label_available_at','reason','event_or_witness_id']])
    labels=pd.concat(labels,ignore_index=True).drop_duplicates(identity)
    g=f.merge(labels,on=identity,validate='one_to_one');assert len(g)==len(f)
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
        r=test[identity].copy();r['history_tree']=0.
        r.loc[eligible,'history_tree']=np.clip(model.predict_proba(test.loc[eligible,FEATURES])[:,1],1e-6,1-1e-6)
        predictions.append(r);folds.append(dict(quarter=str(q.date()),train=len(train),positive=int(train.y.sum()),
            test=len(test),latest_training_label=str(train.label_available_at.max())))
        print('V13 quarter frozen',str(q.date()),flush=True)
    scores=pd.concat(predictions,ignore_index=True);scores.to_parquet(CACHE/'history_scores.parquet',index=False)
    tasks=[]
    for artifact in prior['tasks']:
        old=pd.read_parquet(artifact['path']);base=old[old.model.eq('rd_gate')].drop(columns='model')
        joined=base.merge(scores,on=identity,validate='many_to_one')
        assert len(joined)==len(base) and np.array_equal(joined.row_id,base.row_id)
        joined['history_blend']=.5*joined.history_tree+.5*joined.prob
        joined['history_prior_blend']=.5*joined.history_tree+.25*joined.prob+.25*joined.prior*joined.state_eligible
        rows=[old]
        for name in ['history_tree','history_blend','history_prior_blend']:
            r=base.copy();r['model']=name;r['prob']=joined[name].to_numpy()
            rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
            r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1);rows.append(r)
        path=CACHE/'predictions'/Path(artifact['path']).name;path.parent.mkdir(exist_ok=True)
        pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        tasks.append(dict(task=artifact['task'],path=str(path),sha256=sha(path),source_sha256=artifact['sha256'],frozen_sha256=sha(OUT/'frozen_candidates.json')))
    js(OUT/'prediction_receipt.json',dict(tasks=tasks,folds=folds,frozen_sha256=sha(OUT/'frozen_candidates.json'),
        feature_sha256=sha(feature_path),scores_sha256=sha(CACHE/'history_scores.parquet')))
    print('V13 all predictions frozen',flush=True)


if __name__=='__main__':run()
