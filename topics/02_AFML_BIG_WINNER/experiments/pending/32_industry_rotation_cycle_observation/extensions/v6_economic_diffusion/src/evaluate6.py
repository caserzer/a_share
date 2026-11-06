"""Fixed mechanistic ablations on the frozen RD-Agent early-stage model."""
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from context6 import ROOT,V5,CACHE,OLD,OUT,KEY,GROUPS,old_engine,sha,js


def fit(train,test,spec,extras):
    x=old_engine.compile_features(train,spec);z=old_engine.compile_features(test,spec)
    for col in extras:x[col]=train[col].to_numpy();z[col]=test[col].to_numpy()
    model=LGBMClassifier(n_estimators=int(spec['trees']),num_leaves=int(spec['leaves']),max_depth=int(spec['max_depth']),
        min_child_samples=int(spec['min_child_samples']),learning_rate=spec['learning_rate'],reg_lambda=spec['reg_lambda'],
        n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
    weights=old_engine.date_weights(train)
    model.fit(x,train.y,sample_weight=weights)
    return np.clip(model.predict_proba(z)[:,1],1e-6,1-1e-6),float(np.average(train.y,weights=weights))


def predict():
    spec=json.loads((V5/'outputs/stage_b/frozen_selection.json').read_text())['winner']['spec']
    assert spec['model']=='lightgbm'
    additions=pd.read_parquet(CACHE/'mechanism_features.parquet')
    extra_cols=sum(GROUPS.values(),[])+['other_pos21','other_neg21','other_leader21','reverse_pos21','reverse_neg21','leader21','leader63',
        'common_complete','h3_complete']
    additions=additions[['row_id','benchmark']+list(dict.fromkeys(extra_cols))]
    variants={'base':[],'H1':GROUPS['H1'],'H2':GROUPS['H2'],'H3':GROUPS['H3'],
        'joint':sum(GROUPS.values(),[]),
        'other_leader':['other_pos21','other_neg21','peer21','peer63','other_gap21'],
        'reverse':['reverse_pos21','reverse_neg21','leader21','leader63','reverse_gap21']}
    js(OUT/'frozen_models.json',dict(spec=spec,variants=variants,plan_sha256=sha(ROOT/'research_plan.md'),
        evaluation_code_sha256=sha(__file__),source_feature_sha256=sha(CACHE/'mechanism_features.parquet'),
        scope='fixed ablation; no optimization against already viewed outer period'))
    quarters=pd.date_range('2024-01-01','2026-10-01',freq='QS');predictions=[];audit=[]
    for key,g in old_engine.task_frames('b'):
        g=g.merge(additions[additions.benchmark.eq(key[2])].drop(columns='benchmark'),on='row_id',validate='one_to_one')
        g['other_gap21']=g.other_leader21-g.peer21;g['reverse_gap21']=-g.leader_gap21
        for cohort,mask,names in [('common',g.common_complete,list(variants)),('h3_full',g.h3_complete,['base','H3'])]:
            h=g[mask].copy()
            for q in quarters:
                train=h[h.date.lt(q)&h.label_available_at.lt(q)&h.y.notna()]
                test=h[h.date.ge(q)&h.date.lt(q+pd.DateOffset(months=3))].drop(columns=['y','label_available_at','reason','event_or_witness_id'])
                if test.empty:continue
                assert len(train)>500 and train.y.sum()>=5 and train.label_available_at.max()<q
                for name in names:
                    p,prior=fit(train,test,spec,variants[name])
                    r=test[['row_id','date','era','level','industry_code','frequency','threshold','benchmark']].copy()
                    r['cohort']=cohort;r['model']=name;r['prob']=p;r['prior']=prior
                    rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
                    r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1)
                    predictions.append(r)
                audit.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],cohort=cohort,quarter=str(q.date()),
                    train=len(train),test=len(test),latest_training_label=str(train.label_available_at.max())))
        print('V6 predicted',key,flush=True)
    p=CACHE/'predictions.parquet';pd.concat(predictions,ignore_index=True).to_parquet(p,index=False)
    js(OUT/'prediction_receipt.json',dict(path=str(p),sha256=sha(p),frozen_models_sha256=sha(OUT/'frozen_models.json'),folds=audit))


def score():
    receipt=json.loads((OUT/'prediction_receipt.json').read_text());assert sha(receipt['path'])==receipt['sha256']
    p=pd.read_parquet(receipt['path'])
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    merged=p.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
    known=merged[merged.y.notna()].copy();known['year']=known.date.dt.year;known['loss']=(known.prob-known.y)**2
    keys=['cohort','model','frequency','threshold','benchmark']
    rows=[];years=[]
    from outer import evaluate_rows
    for key,g in known.groupby(keys):
        for r in evaluate_rows(g):r.update(zip(keys,key));rows.append(r)
    for key,g in known.groupby(keys+['year']):
        for r in evaluate_rows(g):r.update(zip(keys+['year'],key));years.append(r)
    pd.DataFrame(rows).to_csv(OUT/'ablation_metrics.csv',index=False)
    pd.DataFrame(years).to_csv(OUT/'annual_metrics.csv',index=False)
    coverage=merged.groupby(keys+['level']).agg(predictions=('row_id','size'),known=('y','count'),alerts=('alert','sum')).reset_index()
    coverage['unknown']=coverage.predictions-coverage.known;coverage.to_csv(OUT/'outcome_coverage.csv',index=False)
    losses=known.groupby(['cohort','frequency','threshold','benchmark','level','date','model']).loss.mean().unstack('model')
    differences=losses.drop(columns='base').rsub(losses['base'],axis=0).reset_index()
    differences['month']=differences.date.dt.to_period('M').astype(str)
    # First equal-date within each task/month, then equal-task across markets and levels.
    taskmonth=differences.groupby(['cohort','frequency','threshold','benchmark','level','month']).mean(numeric_only=True).reset_index()
    models=[x for x in losses.columns if x!='base']
    taskmonth.groupby(['cohort','month'])[models].mean().reset_index().to_csv(OUT/'monthly_brier_improvement.csv',index=False)
    print('V6 early-label scoring complete',flush=True)


if __name__=='__main__':
    import sys
    if '--score-only' not in sys.argv:predict()
    score()
