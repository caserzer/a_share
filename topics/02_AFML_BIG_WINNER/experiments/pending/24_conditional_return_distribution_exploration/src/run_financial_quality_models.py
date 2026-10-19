"""R31 nested financial-quality ablations on two previously frozen algorithms."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_financial_quality import DEST,PANEL,GROUPS
from recover_baseline_precision import RECOVERED
from run_historical_peer_models import CONTROL
from run_conditional_forests import PARAMS as FOREST_PARAMS
from conditional_forests import training_impute
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats

CACHE=OUT/'local_cache/r31_class_distributions'
ADDITIONS=GROUPS
MODELS={f'{family}_{group}':(family,added) for family in ['catboost','extra'] for group,added in ADDITIONS.items()}
REFERENCES={'catboost_reference':(OUT/'r25_historical_peers','own_momentum_control'),
            'extra_reference':(OUT/'r28_conditional_forests','extra_global_mixed')}


def raw_reference(name,h,date,keys):
    stem=f'{h}_{date.date()}'
    if name=='catboost_reference':
        folder=OUT/'local_cache/r25_class_distributions';path=folder/f'{stem}_own_momentum_control.npz';field='class_atoms'
    else:
        folder=OUT/'local_cache/r28_forest_distributions';path=folder/f'{stem}_extra.npz';field='global_atoms'
    kp=folder/f'{stem}_keys.parquet';pd.testing.assert_frame_equal(pd.read_parquet(kp),keys)
    with np.load(path) as x:atoms=x[field];p=x['probabilities']
    assert atoms.ndim==1
    return atoms,p,[dict(path=str(q),sha256=digest(q)) for q in [path,kp]]


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    fa=json.loads((DEST/'feature_audit.json').read_text())
    assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']
    assert digest(EP/'notes/r31_financial_quality.md')==fa['plan_sha256']
    panel=pd.read_parquet(PANEL);sources={}
    for name,(folder,_) in REFERENCES.items():
        audit=json.loads((folder/'research_integrity_audit.json').read_text());assert audit['technical_integrity_passed']
        sources[name]=audit['receipts']
    spec=dict(models=MODELS,control_features=CONTROL,feature_sha256=fa['feature_sha256'],plan_sha256=fa['plan_sha256'],
        catboost=dict(depth=2,iterations=100,learning_rate=.03,l2_leaf_reg=20,random_seed=24),extra=FOREST_PARAMS,
        references={k:dict(folder=str(v[0]),model=v[1],receipts=sources[k]) for k,v in REFERENCES.items()},
        weighting='Month-balanced mature training rows; each candidate mixed 50% with B; same global 32 atoms per class',
        evidence='Six fixed input additions; no change to original 27600 stock-dates; repeated exploration')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    fits=[];precision=[];raw_receipts=[]
    for h in [1,3,6]:
        rows=[];old_references={}
        for name,(folder,model_name) in REFERENCES.items():
            path=folder/f'predictions_{h}m.parquet'
            receipt=next(r for r in sources[name] if r['path'].endswith(f'predictions_{h}m.parquet'))
            assert digest(path)==receipt['sha256']
            frame=pd.read_parquet(path);old_references[name]=frame[frame.model.eq(model_name)]
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=base[base.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']]
            template=base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date','instrument']],keys)
            np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet',index=False)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            old_base=load_distribution(OUT/'local_cache/r15_distributions',h,date,'B',keys)
            for name in REFERENCES:
                atoms,p,receipts=raw_reference(name,h,date,keys);raw_receipts.extend(receipts)
                raw=(np.tile(atoms,(len(keys),1)),np.repeat(p/32,32,axis=1))
                old=old_references[name];old=old[old.date.eq(date)].reset_index(drop=True)
                pd.testing.assert_frame_equal(old[['date','instrument']],keys)
                np.testing.assert_allclose(old.actual,template.actual,equal_nan=True)
                before=weighted_stats(*combine_distributions([old_base,raw],[.5,.5]),template.actual)
                np.testing.assert_allclose(before,old[before.columns],atol=1e-10,rtol=1e-10,equal_nan=True)
                after=weighted_stats(*combine_distributions([(ba,bw),raw],[.5,.5]),template.actual)
                pred=template.copy();pred['model']=name;pred[after.columns]=after.to_numpy();rows.append(pred)
                np.savez_compressed(CACHE/f'{h}_{date.date()}_{name}.npz',class_atoms=atoms,probabilities=p)
                precision.append(dict(months=h,date=str(date.date()),model=name,
                    max_absolute_change=float((after-old[after.columns]).abs().max().max()),
                    directional_changes=int(((after.p_up>after.p_down)!=(old.p_up>old.p_down)).sum())))
            train=select_training(panel,h,date,None);weights=observation_weights(train,date,True,None)
            assert len(train)>=1000 and train.date.nunique()>=18
            y=train[f'y_{h}'].to_numpy();labels=classes(y)
            for name,(family,added) in MODELS.items():
                cols=CONTROL+added;medians=np.array([]);train_hash='native_missing';test_hash='native_missing'
                if family=='catboost':
                    model=CatBoostClassifier(**spec['catboost'],loss_function='MultiClass',thread_count=4,verbose=False,allow_writing_files=False)
                    tx=train[cols].astype(float);qx=test[cols].astype(float)
                else:
                    tx,qx,medians=training_impute(train[cols],test[cols]);model=ExtraTreesClassifier(**FOREST_PARAMS,bootstrap=False)
                    train_hash=hashlib.sha256(tx.tobytes()).hexdigest();test_hash=hashlib.sha256(qx.tobytes()).hexdigest()
                model.fit(tx,labels,sample_weight=weights)
                p=np.zeros((len(test),7));p[:,model.classes_.astype(int)]=model.predict_proba(qx)
                a,w=weighted_class_distribution(y,labels,p,weights)
                cache=CACHE/f'{h}_{date.date()}_{name}.npz'
                np.savez_compressed(cache,class_atoms=a[0],probabilities=p,medians=medians)
                aa,ww=combine_distributions([(ba,bw),(a,w)],[.5,.5])
                stats=weighted_stats(aa,ww,template.actual);pred=template.copy();pred['model']=name;pred[stats.columns]=stats.to_numpy();rows.append(pred)
                fits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(train),training_months=train.date.nunique(),
                    last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(weights.sum()),
                    cache_sha256=digest(cache),imputed_train_sha256=train_hash,imputed_test_sha256=test_hash))
            print(h,date.date(),'finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)
        pd.DataFrame(precision).to_csv(DEST/'reference_precision_changes.csv',index=False)
        (DEST/'reference_raw_receipts.json').write_text(json.dumps(raw_receipts,indent=2)+'\n')


if __name__=='__main__':run()
