"""Three frozen feature-family increments; no parameter or window search."""
from lightgbm import LGBMClassifier
from common34 import *


def run():
    receipt=json.loads((OUT/'feature_receipt.json').read_text())
    assert sha(CACHE/'expansion_features.parquet')==receipt['features_sha256']
    cfg=json.loads((EXT/'v18_conditional_diffusion/outputs/frozen_candidates.json').read_text())
    oldreceipt=json.loads((EXT/'v18_conditional_diffusion/outputs/prediction_receipt.json').read_text())
    original_path=OLD.parent/'diffusion_v18/features.parquet'
    assert sha(original_path)==oldreceipt['features_sha256']
    g=pd.read_parquet(original_path);g=g[g.date.lt('2024-10-01')].reset_index(drop=True)
    new=pd.read_parquet(CACHE/'expansion_features.parquet')
    join=['era','level','industry_code','date','threshold']
    assert not new.groupby(join)[ADDED].nunique(dropna=False).gt(1).any().any()
    new=new[join+ADDED].drop_duplicates(join)
    g=g.merge(new,on=join,how='left',validate='many_to_one')
    for family,cols in GROUPS.items():g[family+'_complete']=g[cols].notna().all(axis=1)
    assert not np.isinf(g[ADDED].to_numpy()).any()
    observations=pd.read_parquet(OLD/'features.parquet')
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    lab=observations[['row_id','era','level','industry_code','date']].merge(labels,on='row_id',validate='one_to_many')
    lab=lab[IDENTITY+['y','label_available_at']].drop_duplicates(IDENTITY)
    g=g.merge(lab,on=IDENTITY,validate='one_to_one')
    base_features=cfg['base_features']+cfg['added']
    frozen=dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        original_features_sha256=sha(original_path),new_features_sha256=sha(CACHE/'expansion_features.parquet'),
        base_features=base_features,groups=GROUPS,params=cfg['params'],candidates=list(GROUPS),combinations_tested=0)
    js(OUT/'model_freeze.json',frozen)
    old_scores=pd.read_parquet(OLD.parent/'diffusion_v18/scores.parquet')
    rows=[];folds=[];importance=[]
    (CACHE/'quarters').mkdir(exist_ok=True)
    for q in pd.date_range('2021-01-01','2024-07-01',freq='QS'):
        train=g[g.state_eligible.eq(1)&g.date.lt(q)&g.label_available_at.lt(q)&g.y.notna()]
        test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))]
        if test.empty:
            folds.append(dict(quarter=str(q.date()),status='EMPTY_CLASSIFICATION_QUARTER',test=0));continue
        assert train.label_available_at.max()<q
        weights=1/train.groupby(['date','level']).date.transform('size').to_numpy(float);weights/=weights.mean()
        eligible=test.state_eligible.eq(1)
        r=test[IDENTITY+[family+'_complete' for family in GROUPS]].copy()
        if q==pd.Timestamp('2021-01-01'):
            base=LGBMClassifier(**cfg['params']);base.fit(train[base_features],train.y,sample_weight=weights)
            predicted=np.zeros(len(test))
            predicted[eligible.to_numpy()]=np.clip(base.predict_proba(test.loc[eligible,base_features])[:,1],1e-6,1-1e-6)
            ref=test[IDENTITY].merge(old_scores[IDENTITY+['diffusion_tree']],on=IDENTITY,validate='one_to_one')
            assert np.allclose(predicted,ref.diffusion_tree,atol=1e-12,rtol=1e-12)
        for family,cols in GROUPS.items():
            model=LGBMClassifier(**cfg['params'])
            features=base_features+cols
            model.fit(train[features],train.y,sample_weight=weights)
            r[family]=0.
            if eligible.any():r.loc[eligible,family]=np.clip(model.predict_proba(test.loc[eligible,features])[:,1],1e-6,1-1e-6)
            importance.extend(dict(quarter=str(q.date()),model=family,feature=c,gain=float(v)) for c,v in zip(features,model.booster_.feature_importance(importance_type='gain')))
            model.booster_.save_model(str(CACHE/'quarters'/f'{q.date()}_{family}.txt'))
        r.to_parquet(CACHE/'quarters'/f'{q.date()}_scores.parquet',index=False)
        rows.append(r);folds.append(dict(quarter=str(q.date()),training=len(train),positive=int(train.y.sum()),
            latest_training_label=str(train.label_available_at.max()),test=len(test),eligible=int(eligible.sum())))
        print('frozen three-family predictions',q.date(),'train',len(train),flush=True)
    scores=pd.concat(rows,ignore_index=True)
    scores.to_parquet(CACHE/'scores.parquet',index=False)
    pd.DataFrame(importance).to_csv(OUT/'feature_importance.csv',index=False)
    coverage=g.assign(year=g.date.dt.year).groupby(['year','level'])[[family+'_complete' for family in GROUPS]].mean().reset_index()
    coverage.to_csv(OUT/'model_feature_coverage.csv',index=False)
    js(OUT/'prediction_receipt.json',dict(folds=folds,rows=len(scores),scores_sha256=sha(CACHE/'scores.parquet'),
        baseline_q1_exact_replay='PASS',frozen_sha256=sha(OUT/'model_freeze.json')))
    print('THREE FAMILIES COMPLETE',len(scores),flush=True)


if __name__=='__main__':run()
