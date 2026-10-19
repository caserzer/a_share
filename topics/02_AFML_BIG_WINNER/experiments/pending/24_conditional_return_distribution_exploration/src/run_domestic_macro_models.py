"""R33 fixed domestic-macro ablations on two previously frozen algorithms."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_domestic_macro import DEST,PANEL,GROUPS
from recover_baseline_precision import RECOVERED
from run_historical_peer_models import CONTROL
from run_conditional_forests import PARAMS as FOREST_PARAMS
from conditional_forests import training_impute
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats

CACHE=OUT/'local_cache/r33_class_distributions'
ADDITIONS=GROUPS
MODELS={f'{family}_{group}':(family,added) for family in ['catboost','extra'] for group,added in ADDITIONS.items()}
REFERENCES={'catboost_reference':(OUT/'r31_financial_quality','catboost_reference'),
            'extra_reference':(OUT/'r31_financial_quality','extra_reference')}


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    fa=json.loads((DEST/'feature_audit.json').read_text())
    assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']
    assert digest(EP/'notes/r33_domestic_macro.md')==fa['plan_sha256']
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
    fits=[]
    for h in [1,3,6]:
        rows=[]
        for name,(folder,model_name) in REFERENCES.items():
            path=folder/f'predictions_{h}m.parquet'
            receipt=next(r for r in sources[name] if r['path'].endswith(f'predictions_{h}m.parquet'))
            assert digest(path)==receipt['sha256']
            frame=pd.read_parquet(path);rows.append(frame[frame.model.eq(model_name)].assign(model=name))
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=base[base.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']]
            template=base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date','instrument']],keys)
            np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet',index=False)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
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


if __name__=='__main__':run()
