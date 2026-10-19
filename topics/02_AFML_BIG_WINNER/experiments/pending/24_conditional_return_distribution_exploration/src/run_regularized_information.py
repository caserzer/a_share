"""R35 fixed regularization and matched input ablations, raw and exact-B mixture."""
import hashlib,json,warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from prepare_panel import EP,OUT
from build_joint_information import PANEL,FULL,CONTROL
from build_margin_information import digest
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution
from run_direct_probability import classes
from run_joint_information import score,frame_digest
from regularized_information import WeightedRankDesign,month_weights,probabilities
from recover_baseline_precision import RECOVERED
DEST=OUT/'r35_regularized_information'
CACHE=OUT/'local_cache/r35_class_distributions'
CONFIGS={f'{group}_c{c}':(cols,float(c)) for group,cols in [('control',CONTROL),('full',FULL)] for c in [1,10]}
MODELS={component+'_'+suffix:(component,fraction) for component in CONFIGS for suffix,fraction in [('raw',1.),('mixed',.5)]}
REFERENCES={'shallow_control_reference':'reference','shallow_full_reference':'shallow_full_mixed'}


def array_digest(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    source_audit=OUT/'r34_joint_information/research_integrity_audit.json'
    audit=json.loads(source_audit.read_text());assert audit['technical_integrity_passed']
    feature_audit=OUT/'r34_joint_information/feature_audit.json';fa=json.loads(feature_audit.read_text())
    assert digest(PANEL)==fa['feature_sha256'];panel=pd.read_parquet(PANEL)
    spec=dict(configs={k:dict(columns=c,C=v) for k,(c,v) in CONFIGS.items()},models=MODELS,references=REFERENCES,
        feature_sha256=digest(PANEL),source_audit_sha256=digest(source_audit),feature_audit_sha256=digest(feature_audit),
        plan_sha256=digest(EP/'notes/r35_regularized_information.md'),tol=1e-6,max_iter=1000,
        reference_receipts=audit['receipts'],sample_weight='Each mature origin-month total equals one')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');fits=[]
    for h in [1,3,6]:
        rp=OUT/f'r34_joint_information/predictions_{h}m.parquet';receipt=next(r for r in audit['receipts'] if r['path'].endswith(rp.name))
        assert digest(rp)==receipt['sha256'];reference=pd.read_parquet(rp)
        rows=[reference[reference.model.eq(old)].assign(model=new) for new,old in REFERENCES.items()]
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=base[base.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);template=base[base.date.eq(date)].reset_index(drop=True);keys=test[['date','instrument']]
            pd.testing.assert_frame_equal(template[['date','instrument']],keys);np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            stem=f'{h}_{date.date()}';keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            train=select_training(panel,h,date,None);weights=month_weights(train);y=train[f'y_{h}'].to_numpy();labels=classes(y)
            assert set(labels)==set(range(7))
            # Keep the exact existing class amplitudes; logistic weights differ only by a common scalar.
            atom_weights=observation_weights(train,date,True,None)
            atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),atom_weights)
            components={};designs={}
            for component,(cols,c) in CONFIGS.items():
                group=component.split('_')[0]
                if group not in designs:
                    design=WeightedRankDesign().fit(train[cols],weights)
                    x,z=design.transform(train[cols]),design.transform(test[cols]);designs[group]=(design,x,z)
                design,x,z=designs[group]
                model=LogisticRegression(C=c,solver='lbfgs',max_iter=1000,tol=1e-6)
                with warnings.catch_warnings():
                    warnings.simplefilter('error',ConvergenceWarning);model.fit(x,labels,sample_weight=weights)
                assert model.n_iter_.max()<1000
                p=probabilities(z,model.coef_,model.intercept_,model.classes_)
                np.testing.assert_allclose(p,model.predict_proba(z),atol=1e-12,rtol=1e-12)
                components[component]=p
                cache=CACHE/f'{stem}_{component}.npz'
                np.savez_compressed(cache,class_atoms=atoms[0],probabilities=p,coef=model.coef_,intercept=model.intercept_,classes=model.classes_,names=np.asarray(design.names))
                fits.append(dict(months=h,date=str(date.date()),component=component,C=c,training_rows=len(train),training_months=train.date.nunique(),
                    last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(weights.sum()),n_iter=int(model.n_iter_.max()),
                    design_columns=x.shape[1],coef_l2=float(np.linalg.norm(model.coef_)),cache_sha256=digest(cache),
                    train_features_sha256=frame_digest(train[cols]),test_features_sha256=frame_digest(test[cols]),
                    train_design_sha256=array_digest(x),test_design_sha256=array_digest(z)))
            for name,(component,fraction) in MODELS.items():
                stats=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),components[component],fraction)
                pred=template.copy();pred['model']=name;pred[stats.columns]=stats.to_numpy();rows.append(pred)
            print(h,date.date(),'finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)


if __name__=='__main__':run()
