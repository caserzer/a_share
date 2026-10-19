"""R34 fixed information/capacity experiment, independent and B-mixed distributions."""
import hashlib,json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import EP,OUT
from build_joint_information import DEST,PANEL,FULL,CONTROL
from build_margin_information import digest
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats
from hierarchical_probabilities import stable_sign_scores
from recover_baseline_precision import RECOVERED
CACHE=OUT/'local_cache/r34_class_distributions'
FIT_MODELS={'shallow_full':(FULL,2,100,20),'deep_control':(CONTROL,4,200,50),'deep_full':(FULL,4,200,50)}
MODELS={'shallow_control_raw':('shallow_control',1.)}
for component in FIT_MODELS:
    MODELS.update({component+'_raw':(component,1.),component+'_mixed':(component,.5)})


def frame_digest(frame):
    return hashlib.sha256(json.dumps(list(frame.columns)).encode()+pd.util.hash_pandas_object(frame,index=True).values.tobytes()).hexdigest()


def score(template,ba,bw,atoms,p,fraction):
    w=np.repeat(p/32,32,axis=1)
    if fraction==1:aa,ww=atoms,w
    else:aa,ww=combine_distributions([(ba,bw),(atoms,w)],[1-fraction,fraction])
    result=weighted_stats(aa,ww,template.actual)
    sign=np.column_stack([p[:,:3].sum(axis=1),p[:,3],p[:,4:].sum(axis=1)])
    return stable_sign_scores(result,sign,template[['p_down','p_zero','p_up']].to_numpy(),fraction,template.actual)


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    fa=json.loads((DEST/'feature_audit.json').read_text());assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']
    assert digest(EP/'notes/r34_joint_information.md')==fa['plan_sha256'];panel=pd.read_parquet(PANEL)
    refdir=OUT/'r31_financial_quality';ra=json.loads((refdir/'research_integrity_audit.json').read_text());assert ra['technical_integrity_passed']
    spec=dict(models=MODELS,fit_models={n:dict(features=c,depth=d,iterations=t,l2_leaf_reg=l2) for n,(c,d,t,l2) in FIT_MODELS.items()},
        learning_rate=.03,random_seed=24,feature_sha256=fa['feature_sha256'],plan_sha256=fa['plan_sha256'],
        reference_folder=str(refdir),reference_model='catboost_reference',reference_receipts=ra['receipts'],
        weighting='Same mature samples, equal origin-month total weights, global 32 atoms/class; independent or exact-B half mix',
        inherited_limitations=fa['limitation'])
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');fits=[];sources=[]
    for h in [1,3,6]:
        rp=refdir/f'predictions_{h}m.parquet';rr=next(r for r in ra['receipts'] if r['path'].endswith(rp.name));assert digest(rp)==rr['sha256']
        reference=pd.read_parquet(rp);reference=reference[reference.model.eq('catboost_reference')];rows=[reference.assign(model='reference')]
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=base[base.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);template=base[base.date.eq(date)].reset_index(drop=True);keys=test[['date','instrument']]
            pd.testing.assert_frame_equal(template[['date','instrument']],keys);np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            stem=f'{h}_{date.date()}';keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            train=select_training(panel,h,date,None);weights=observation_weights(train,date,True,None);y=train[f'y_{h}'].to_numpy();labels=classes(y)
            assert len(train)>=1000 and train.date.nunique()>=18
            global_atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),weights)
            components={}
            source=OUT/f'local_cache/r25_class_distributions/{stem}_own_momentum_control.npz';kp=source.parent/f'{stem}_keys.parquet'
            pd.testing.assert_frame_equal(pd.read_parquet(kp),keys)
            with np.load(source) as payload:
                np.testing.assert_array_equal(payload['class_atoms'],global_atoms[0]);components['shallow_control']=payload['probabilities']
            sources.extend([dict(path=str(q),sha256=digest(q)) for q in [source,kp]])
            expected=score(template,ba,bw,np.tile(global_atoms[0],(len(test),1)),components['shallow_control'],.5)
            old=reference[reference.date.eq(date)].reset_index(drop=True)
            np.testing.assert_allclose(expected,old[expected.columns],atol=1e-10,rtol=1e-10,equal_nan=True)
            assert np.array_equal(expected.p_up.gt(expected.p_down),old.p_up.gt(old.p_down))
            for component,(cols,depth,iterations,l2) in FIT_MODELS.items():
                cat=['industry_id'] if 'industry_id' in cols else []
                model=CatBoostClassifier(depth=depth,iterations=iterations,l2_leaf_reg=l2,learning_rate=.03,random_seed=24,
                    loss_function='MultiClass',thread_count=4,verbose=False,allow_writing_files=False,cat_features=cat)
                model.fit(train[cols],labels,sample_weight=weights)
                p=np.zeros((len(test),7));p[:,model.classes_.astype(int)]=model.predict_proba(test[cols]);components[component]=p
            for component,p in components.items():
                cache=CACHE/f'{stem}_{component}.npz';np.savez_compressed(cache,class_atoms=global_atoms[0],probabilities=p)
                cols=CONTROL if component=='shallow_control' else FIT_MODELS[component][0]
                fits.append(dict(months=h,date=str(date.date()),component=component,reused=component=='shallow_control',training_rows=len(train),
                    training_months=train.date.nunique(),last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(weights.sum()),
                    cache_sha256=digest(cache),train_features_sha256=frame_digest(train[cols]),test_features_sha256=frame_digest(test[cols])))
            for name,(component,fraction) in MODELS.items():
                stats=score(template,ba,bw,np.tile(global_atoms[0],(len(test),1)),components[component],fraction)
                pred=template.copy();pred['model']=name;pred[stats.columns]=stats.to_numpy();rows.append(pred)
            print(h,date.date(),'finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False);pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)
        (DEST/'reused_source_receipts.json').write_text(json.dumps(sources,indent=2)+'\n')

if __name__=='__main__':run()
