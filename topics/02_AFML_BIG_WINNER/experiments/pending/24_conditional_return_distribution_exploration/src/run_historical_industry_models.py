"""R32 fixed industry identity, peer-state and class-conditional magnitude ablations."""
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import EP,OUT
from build_historical_industry import DEST,PANEL,IDENTITY,STATE
from build_margin_information import digest
from run_historical_peer_models import CONTROL
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats
from hierarchical_probabilities import stable_sign_scores
from recover_baseline_precision import RECOVERED
CACHE=OUT/'local_cache/r32_class_distributions'
MODELS=['industry_identity','industry_state','industry_conditional']
PARAMS=dict(depth=2,iterations=100,learning_rate=.03,l2_leaf_reg=20,random_seed=24)

def conditional_atoms(y,labels,weights,train_groups,test_groups,global_atoms,min_count=30):
    output=np.tile(global_atoms,(len(test_groups),1));counts=np.zeros((len(test_groups),7),dtype=int);used=np.zeros_like(counts,dtype=bool)
    train_groups=np.asarray(train_groups);test_groups=np.asarray(test_groups)
    for group in np.unique(test_groups):
        if group=='unknown':continue
        mask=train_groups==group;rows=np.flatnonzero(test_groups==group)
        if not mask.any():continue
        local,_=weighted_class_distribution(y[mask],labels[mask],np.full((1,7),1/7),weights[mask])
        for k in range(7):
            n=int((mask&(labels==k)).sum());counts[rows,k]=n
            if n>=min_count:output[rows,k*32:(k+1)*32]=local[0,k*32:(k+1)*32];used[rows,k]=True
    return output,counts,used

def score(template,ba,bw,atoms,p):
    a,w=combine_distributions([(ba,bw),(atoms,np.repeat(p/32,32,axis=1))],[.5,.5])
    stats=weighted_stats(a,w,template.actual)
    sign=np.column_stack([p[:,:3].sum(axis=1),p[:,3],p[:,4:].sum(axis=1)])
    return stable_sign_scores(stats,sign,template[['p_down','p_zero','p_up']].to_numpy(),.5,template.actual)

def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    fa=json.loads((DEST/'feature_audit.json').read_text());assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']
    assert digest(EP/'notes/r32_historical_industry.md')==fa['plan_sha256'];panel=pd.read_parquet(PANEL)
    refdir=OUT/'r31_financial_quality';ra=json.loads((refdir/'research_integrity_audit.json').read_text());assert ra['technical_integrity_passed']
    spec=dict(params=PARAMS,models=MODELS,control=CONTROL,identity=IDENTITY,state=STATE,feature_sha256=fa['feature_sha256'],plan_sha256=fa['plan_sha256'],
        reference_receipts=ra['receipts'],reference_model='catboost_reference',reference_folder=str(refdir),min_class_count=30,
        distribution='Same global seven-class probabilities; 32 weighted atoms/class; exact B mixed 50%; local atoms fall back class by class.')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');fits=[]
    for h in [1,3,6]:
        path=refdir/f'predictions_{h}m.parquet';receipt=next(r for r in ra['receipts'] if r['path'].endswith(path.name));assert digest(path)==receipt['sha256']
        ref=pd.read_parquet(path);rows=[ref[ref.model.eq('catboost_reference')].assign(model='reference')]
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=base[base.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);template=base[base.date.eq(date)].reset_index(drop=True);keys=test[['date','instrument']]
            pd.testing.assert_frame_equal(template[['date','instrument']],keys);np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            stem=f'{h}_{date.date()}';keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            train=select_training(panel,h,date,None);weights=observation_weights(train,date,True,None);y=train[f'y_{h}'].to_numpy();labels=classes(y)
            for name,added in [('industry_identity',IDENTITY),('industry_state',IDENTITY+STATE)]:
                cols=CONTROL+added;tx=train[cols].copy();qx=test[cols].copy()
                model=CatBoostClassifier(**PARAMS,loss_function='MultiClass',thread_count=4,verbose=False,allow_writing_files=False,cat_features=['industry_id'])
                model.fit(tx,labels,sample_weight=weights);p=np.zeros((len(test),7));p[:,model.classes_.astype(int)]=model.predict_proba(qx)
                atoms,_=weighted_class_distribution(y,labels,p,weights)
                cache=CACHE/f'{stem}_{name}.npz';np.savez_compressed(cache,class_atoms=atoms[0],probabilities=p)
                stats=score(template,ba,bw,atoms,p);pred=template.copy();pred['model']=name;pred[stats.columns]=stats.to_numpy();rows.append(pred)
                fits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(train),training_months=train.date.nunique(),
                    last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(weights.sum()),cache_sha256=digest(cache)))
                if name=='industry_state':
                    local,counts,used=conditional_atoms(y,labels,weights,train.industry_id,test.industry_id,atoms[0]);cache=CACHE/f'{stem}_industry_conditional.npz'
                    np.savez_compressed(cache,atoms=local,probabilities=p,counts=counts,used=used)
                    stats_local=score(template,ba,bw,local,p)
                    np.testing.assert_array_equal(stats[['p_up','p_down','brier']],stats_local[['p_up','p_down','brier']])
                    pred=template.copy();pred['model']='industry_conditional';pred[stats_local.columns]=stats_local.to_numpy();rows.append(pred)
                    fits.append(dict(months=h,date=str(date.date()),model='industry_conditional',training_rows=len(train),training_months=train.date.nunique(),
                        last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(weights.sum()),cache_sha256=digest(cache)))
            print(h,date.date(),'finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False);pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)

if __name__=='__main__':run()
