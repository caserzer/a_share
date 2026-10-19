"""R44 bounded-rank MLP, matched input and mixture ablations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
import sklearn.neural_network._multilayer_perceptron as mlp_source
from prepare_panel import EP,OUT
from build_joint_information import PANEL,FULL,CONTROL
from build_margin_information import digest
from regularized_information import WeightedRankDesign,month_weights
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_direct_probability import classes
from run_joint_information import score,frame_digest
from run_regularized_information import array_digest
from run_prequential_search import load_distribution
from recover_baseline_precision import RECOVERED
from neural_probability_models import PARAMS,fit_network,forward

DEST=OUT/'r44_neural_probability_models'
CACHE=OUT/'local_cache/r44_neural_probability_models'
PLAN=EP/'notes/r44_neural_probability_models.md'
GROUPS={'control':CONTROL,'full':FULL}
MODELS={f'{g}_{mode}':(g,fraction) for g in GROUPS for mode,fraction in [('raw',1.),('mixed',.5)]}
SOURCE=OUT/'r35_regularized_information'
REFERENCES={f'linear_{g}_{mode}':f'{g}_c1_{mode}' for g in GROUPS for mode in ['raw','mixed']}


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(),'Do not overwrite a started frozen experiment'
    fa=json.loads((OUT/'r34_joint_information/feature_audit.json').read_text());assert digest(PANEL)==fa['feature_sha256']
    audit=json.loads((SOURCE/'research_integrity_audit.json').read_text());assert audit['technical_integrity_passed']
    panel=pd.read_parquet(PANEL)
    spec=dict(models=MODELS,groups=GROUPS,parameters=PARAMS,feature_sha256=digest(PANEL),plan_sha256=digest(PLAN),
        reference_receipts=audit['receipts'],references=REFERENCES,sklearn_version=sklearn.__version__,
        mlp_source_path=mlp_source.__file__,mlp_source_sha256=digest(Path(mlp_source.__file__)),
        weighting='Fit: equal month mass with mean row weight 1; rank design: original R35 month total 1',
        optimization='60 fixed epochs, no validation-based stopping; iteration-limit warning recorded, not convergence claim')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');fits=[]
    for h in [1,3,6]:
        rp=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in audit['receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256']
        old=pd.read_parquet(rp);rows=[old[old.model.eq(v)].assign(model=k) for k,v in REFERENCES.items()]
        b=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet');base=b[b.model.eq('B')]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);template=base[base.date.eq(date)].reset_index(drop=True);keys=test[['date','instrument']];stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(template[['date','instrument']],keys);np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False);ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            train=select_training(panel,h,date,None);assert len(train)>=1000 and train.date.nunique()>=18
            w=observation_weights(train,date,True,None);dw=month_weights(train);y=train[f'y_{h}'].to_numpy();labels=classes(y)
            atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),w)
            for group,cols in GROUPS.items():
                design=WeightedRankDesign().fit(train[cols],dw);x,z=design.transform(train[cols]),design.transform(test[cols])
                model,warnings_count=fit_network(x,labels,w)
                p=forward(z,model.coefs_,model.intercepts_,model.classes_)
                np.testing.assert_allclose(p,model.predict_proba(z),atol=1e-12,rtol=1e-12)
                payload=dict(class_atoms=atoms[0],probabilities=p,classes=model.classes_,names=np.asarray(design.names),loss_curve=np.asarray(model.loss_curve_))
                payload.update({f'w{j}':v for j,v in enumerate(model.coefs_)})
                payload.update({f'b{j}':v for j,v in enumerate(model.intercepts_)})
                cache=CACHE/f'{stem}_{group}.npz';np.savez_compressed(cache,**payload)
                fits.append(dict(months=h,date=str(date.date()),group=group,training_rows=len(train),training_months=train.date.nunique(),
                    last_training_label=str(train[f'end_{h}'].max()),test_rows=len(test),total_weight=float(w.sum()),n_iter=model.n_iter_,
                    iteration_limit_warnings=warnings_count,loss_initial=model.loss_curve_[0],loss_final=model.loss_curve_[-1],design_columns=x.shape[1],
                    train_features_sha256=frame_digest(train[cols]),test_features_sha256=frame_digest(test[cols]),weights_sha256=array_digest(w),
                    train_design_sha256=array_digest(x),test_design_sha256=array_digest(z),cache_sha256=digest(cache)))
                for mode,fraction in [('raw',1.),('mixed',.5)]:
                    stats=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),p,fraction)
                    pred=template.copy();pred['model']=f'{group}_{mode}';pred[stats.columns]=stats.to_numpy();rows.append(pred)
            pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)
            print(h,date.date(),'both networks finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)


if __name__=='__main__':run()
