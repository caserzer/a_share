"""Frozen quarterly ablation: PE, three joint models, three missingness controls."""
from concurrent.futures import ThreadPoolExecutor
from lightgbm import LGBMClassifier
from common35 import *

def run():
    receipt=json.loads((OUT/'feature_receipt.json').read_text())
    assert sha(CACHE/'features.parquet')==receipt['features_sha256']
    cfg=json.loads((EXT/'v18_conditional_diffusion/outputs/frozen_candidates.json').read_text())
    oldreceipt=json.loads((EXT/'v18_conditional_diffusion/outputs/prediction_receipt.json').read_text())
    original=OLD.parent/'diffusion_v18/features.parquet';assert sha(original)==oldreceipt['features_sha256']
    g=pd.read_parquet(original);g=g[g.date.lt('2024-10-01')].reset_index(drop=True)
    new=pd.read_parquet(CACHE/'features.parquet');join=['era','level','industry_code','date','threshold']
    added=list(dict.fromkeys(sum(ACTIVITY.values(),[])+PE+MISSING))
    extras=[k+'_joint_complete' for k in ACTIVITY]+['pe_known_fraction','pe_positive_fraction']
    assert not new.groupby(join)[added+extras].nunique(dropna=False).gt(1).any().any()
    g=g.merge(new[join+added+extras].drop_duplicates(join),on=join,how='left',validate='many_to_one')
    observations=pd.read_parquet(OLD/'features.parquet');labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    lab=observations[['row_id','era','level','industry_code','date']].merge(labels,on='row_id',validate='one_to_many')
    lab=lab[IDENTITY+['y','label_available_at']].drop_duplicates(IDENTITY)
    g=g.merge(lab,on=IDENTITY,validate='one_to_one')
    base_features=cfg['base_features']+cfg['added']
    old_scores=pd.read_parquet(OLD.parent/'diffusion_v18/scores.parquet')
    v34receipt=json.loads((EXT/'v34_multiscale_expansion/outputs/prediction_receipt.json').read_text())
    assert sha(V34/'scores.parquet')==v34receipt['scores_sha256']
    old34=pd.read_parquet(V34/'scores.parquet')
    js(OUT/'model_freeze.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),
        features_sha256=sha(CACHE/'features.parquet'),original_features_sha256=sha(original),
        base_features=base_features,models=MODELS,params=cfg['params'],pe_source='eastmoney',
        labels_sha256=sha(OLD/'stage_b_labels.parquet'),v34_scores_sha256=sha(V34/'scores.parquet')))
    (CACHE/'quarters').mkdir(exist_ok=True)
    rows=[];folds=[];importance=[];replays=[]
    for q in pd.date_range('2021-01-01','2024-07-01',freq='QS'):
        train=g[g.state_eligible.eq(1)&g.date.lt(q)&g.label_available_at.lt(q)&g.y.notna()]
        test=g[g.date.ge(q)&g.date.lt(q+pd.DateOffset(months=3))]
        if test.empty:folds.append(dict(quarter=str(q.date()),test=0,status='EMPTY_CLASSIFICATION_QUARTER'));continue
        assert train.label_available_at.max()<q
        weights=1/train.groupby(['date','level']).date.transform('size').to_numpy(float);weights/=weights.mean()
        eligible=test.state_eligible.eq(1)
        r=test[IDENTITY+extras+['pe_change21','turn_short']].copy()
        r=r.merge(old34[IDENTITY+list(ACTIVITY)],on=IDENTITY,validate='one_to_one')
        assert r[list(ACTIVITY)].notna().all().all()
        if q==pd.Timestamp('2021-01-01'):
            for name,cols in dict(baseline=[],**ACTIVITY).items():
                model=LGBMClassifier(**cfg['params']);model.fit(train[base_features+cols],train.y,sample_weight=weights)
                predicted=np.zeros(len(test))
                predicted[eligible.to_numpy()]=np.clip(model.predict_proba(test.loc[eligible,base_features+cols])[:,1],1e-6,1-1e-6)
                source=old_scores if name=='baseline' else old34
                column='diffusion_tree' if name=='baseline' else name
                ref=test[IDENTITY].merge(source[IDENTITY+[column]],on=IDENTITY,validate='one_to_one')
                assert np.allclose(predicted,ref[column],atol=1e-12,rtol=1e-12),name
                replays.append(name)
        def fit(item):
            name,cols=item;features=base_features+cols
            model=LGBMClassifier(**cfg['params']);model.fit(train[features],train.y,sample_weight=weights)
            predicted=np.zeros(len(test))
            if eligible.any():predicted[eligible.to_numpy()]=np.clip(model.predict_proba(test.loc[eligible,features])[:,1],1e-6,1-1e-6)
            model.booster_.save_model(str(CACHE/'quarters'/f'{q.date()}_{name}.txt'))
            gains=[dict(quarter=str(q.date()),model=name,feature=c,gain=float(v)) for c,v in zip(features,model.booster_.feature_importance(importance_type='gain'))]
            return name,predicted,gains
        # Independent deterministic single-thread models overlap; no larger model capacity.
        with ThreadPoolExecutor(max_workers=3) as pool:
            for name,predicted,gains in pool.map(fit,MODELS.items()):
                r[name]=predicted;importance.extend(gains)
        r.to_parquet(CACHE/'quarters'/f'{q.date()}_scores.parquet',index=False)
        rows.append(r);folds.append(dict(quarter=str(q.date()),training=len(train),positive=int(train.y.sum()),
            latest_training_label=str(train.label_available_at.max()),test=len(test),eligible=int(eligible.sum())))
        print('seven frozen PE ablations',q.date(),'train',len(train),flush=True)
    scores=pd.concat(rows,ignore_index=True);scores.to_parquet(CACHE/'scores.parquet',index=False)
    pd.DataFrame(importance).to_csv(OUT/'feature_importance.csv',index=False)
    js(OUT/'prediction_receipt.json',dict(folds=folds,rows=len(scores),scores_sha256=sha(CACHE/'scores.parquet'),
        q1_exact_replays=replays,model_freeze_sha256=sha(OUT/'model_freeze.json')))
    print('PREDICTIONS COMPLETE',len(scores),flush=True)

if __name__=='__main__':run()
