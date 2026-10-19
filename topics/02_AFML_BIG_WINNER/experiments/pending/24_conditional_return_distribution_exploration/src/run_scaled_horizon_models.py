"""R42 four fixed scaled class-distribution candidates, separate versus shared."""
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_shared_horizon_models import CONTROL,CAT,FOREST_PARAMS,array_digest
from shared_horizon_models import stack_training,pooled_weights,queries
from scaled_horizon_models import normalize_training,restore_atoms
from run_market_time_models import observation_weights,weighted_class_distribution
from conditional_forests import training_impute
from run_direct_probability import classes
from run_prequential_search import load_distribution
from recover_baseline_precision import RECOVERED
from run_joint_information import score,frame_digest

DEST=OUT/'r42_scaled_horizon_models'
CACHE=OUT/'local_cache/r42_scaled_horizon_models'
PANEL=OUT/'local_cache/historical_peer_panel.parquet'
PLAN=EP/'notes/r42_scaled_horizon_models.md'
MODELS={f'{family}_{mode}':(family,mode) for family in ['catboost','extra'] for mode in ['separate','shared']}
REFERENCES={f'{family}_{mode}_reference':(OUT/('r31_financial_quality' if mode=='separate' else 'r41_shared_horizon_models'),
    family+('_reference' if mode=='separate' else '_h136')) for family in ['catboost','extra'] for mode in ['separate','shared']}


def training_sets(panel,date):
    own={h:normalize_training(stack_training(panel,date,[h],CONTROL)) for h in [1,3,6]}
    for t in own.values():assert len(t)>=1000 and t.date.nunique()>=18
    weights={h:observation_weights(t,date,True,None) for h,t in own.items()}
    shared=normalize_training(stack_training(panel,date,[1,3,6],CONTROL))
    sw=pooled_weights(shared,len(own[3]))
    return own,weights,shared,sw


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(),'Do not overwrite a started experiment'
    panel=pd.read_parquet(PANEL);fa=json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text())
    assert digest(PANEL)==fa['feature_sha256'] and panel.vol63.notna().all() and panel.vol63.gt(0).all()
    refs={}
    for name,(folder,model) in REFERENCES.items():
        audit=json.loads((folder/'research_integrity_audit.json').read_text());assert audit['technical_integrity_passed']
        refs[name]=dict(folder=str(folder),model=model,receipts=audit['receipts'])
    spec=dict(models=MODELS,control_features=CONTROL,catboost=CAT,extra=FOREST_PARAMS,references=refs,
        panel_sha256=digest(PANEL),plan_sha256=digest(PLAN),normalization='log1p(y) / (max(annualized_vol63,.001) * sqrt(h/12)) / 10',
        class_atoms='Own-horizon mature normalized labels, same for separate and shared',candidate_fraction=.5)
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');rows={};bases={};fits=[];sources=[]
    for h in [1,3,6]:
        bp=OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet';b=pd.read_parquet(bp);bases[h]=b[b.model.eq('B')];rows[h]=[]
        sources.append(dict(path=str(bp),sha256=digest(bp)))
        for name,(folder,oldname) in REFERENCES.items():
            path=folder/f'predictions_{h}m.parquet';r=next(r for r in refs[name]['receipts'] if r['path'].endswith(path.name));assert digest(path)==r['sha256']
            d=pd.read_parquet(path);rows[h].append(d[d.model.eq(oldname)].assign(model=name));sources.append(dict(path=str(path),sha256=digest(path)))
    for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
        test=test.reset_index(drop=True);keys=test[['date','instrument']];stamp=str(date.date())
        keys.to_parquet(CACHE/f'{stamp}_keys.parquet',index=False)
        own,weights,shared,sw=training_sets(panel,date);prototypes={};restored={};templates={};base_distributions={}
        for h in [1,3,6]:
            u=own[h].normalized_label.to_numpy()
            prototypes[h],_=weighted_class_distribution(u,classes(u),np.full((1,7),1/7),weights[h])
            restored[h]=restore_atoms(prototypes[h][0],test.vol63,h)
            template=bases[h][bases[h].date.eq(date)].reset_index(drop=True);templates[h]=template
            pd.testing.assert_frame_equal(template[['date','instrument']],keys);np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            base_distributions[h]=load_distribution(RECOVERED,h,date,'B',keys)
            for suffix in ['B.npz','keys.parquet']:
                path=RECOVERED/f'{h}_{stamp}_{suffix}';sources.append(dict(path=str(path),sha256=digest(path)))
        np.savez_compressed(CACHE/f'{stamp}_atoms.npz',**{f'atoms_{h}':a[0] for h,a in prototypes.items()})
        for name,(family,mode) in MODELS.items():
            components=[0] if mode=='shared' else [1,3,6]
            for component in components:
                train,w=(shared,sw) if component==0 else (own[component],weights[component])
                cols=CONTROL+(['horizon_months'] if component==0 else [])
                query=queries(test,CONTROL) if component==0 else test[CONTROL].reset_index(drop=True)
                labels=classes(train.normalized_label.to_numpy());med=np.array([]);th='native_missing';qh='native_missing'
                if family=='catboost':
                    tx=train[cols].astype(float);qx=query[cols].astype(float)
                    model=CatBoostClassifier(**CAT,loss_function='MultiClass',thread_count=4,verbose=False,allow_writing_files=False)
                else:
                    tx,qx,med=training_impute(train[cols],query[cols]);th=array_digest(tx);qh=array_digest(qx)
                    model=ExtraTreesClassifier(**FOREST_PARAMS,bootstrap=False)
                model.fit(tx,labels,sample_weight=w)
                p=np.zeros((len(query),7));p[:,model.classes_.astype(int)]=model.predict_proba(qx)
                path=CACHE/f'{component}_{stamp}_{name}.npz';np.savez_compressed(path,probabilities=p,medians=med)
                fits.append(dict(date=stamp,model=name,component_horizon=component,training_rows=len(train),last_label_end=str(train.label_end.max()),
                    total_weight=float(w.sum()),training_digest=frame_digest(train),weights_sha256=array_digest(w),query_digest=frame_digest(query),
                    imputed_train_sha256=th,imputed_test_sha256=qh,cache_sha256=digest(path),test_rows=len(test)))
                targets=[1,3,6] if component==0 else [component]
                for j,h in enumerate(targets):
                    probability=p[j*len(test):(j+1)*len(test)]
                    result=score(templates[h],*base_distributions[h],restored[h],probability,.5)
                    pred=templates[h].copy();pred['model']=name;pred[result.columns]=result.to_numpy();rows[h].append(pred)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)
        print(stamp,'all scaled models finished',flush=True)
    for h,data in rows.items():pd.concat(data,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
    (DEST/'source_receipts.json').write_text(json.dumps(sources,indent=2)+'\n')


if __name__=='__main__':run()
