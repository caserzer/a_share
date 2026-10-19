"""R46 anchor frozen neural distributions to the contemporaneous frozen B cohort."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from recover_baseline_precision import RECOVERED
from run_prequential_search import load_distribution,combine_distributions
from run_joint_information import score as neural_score,frame_digest
from run_four_horizons import probability_stats
from cohort_probability_anchor import class_mass,anchor,score,TOL,MAX_ITER

DEST=OUT/'r46_cohort_probability_anchor'
CACHE=OUT/'local_cache/r46_cohort_probability_anchor'
PLAN=EP/'notes/r46_cohort_probability_anchor.md'
SOURCE=OUT/'r45_neural_regularization'
NEURAL=OUT/'local_cache/r45_neural_regularization'
REFERENCES={f'{source}_reference':f'alpha16_{source}' for source in ['raw','mixed']}
MODELS={f'{source}_{mode}':(source,mode) for source in ['raw','mixed'] for mode in ['sign','bins']}


def distributions(h,date,base,reference,fits):
    template=base[base.date.eq(date)].reset_index(drop=True);keys=template[['date','instrument']];stem=f'{h}_{date.date()}'
    ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
    stats=probability_stats(ba,template.actual);np.testing.assert_allclose(stats,template[stats.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
    oldfit=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits['group'].eq('alpha16')];assert len(oldfit)==1;oldfit=oldfit.iloc[0]
    assert pd.Timestamp(oldfit.last_training_label)<date
    cp=NEURAL/f'{stem}_alpha16.npz';kp=NEURAL/f'{stem}_keys.parquet'
    assert digest(cp)==oldfit.cache_sha256;pd.testing.assert_frame_equal(pd.read_parquet(kp),keys)
    with np.load(cp) as payload:
        a=np.tile(payload['class_atoms'],(len(keys),1));p=payload['probabilities'];w=np.repeat(p/32,32,axis=1)
    result={}
    for source,fraction in [('raw',1.),('mixed',.5)]:
        prior=reference[reference.date.eq(date)&reference.model.eq('alpha16_'+source)].reset_index(drop=True)
        pd.testing.assert_frame_equal(prior[['date','instrument']],keys)
        expected=neural_score(template,ba,bw,a,p,fraction)
        np.testing.assert_allclose(expected,prior[expected.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
        assert np.array_equal(expected.p_up.gt(expected.p_down),prior.p_up.gt(prior.p_down))
        aa,ww=(a,w) if source=='raw' else combine_distributions([(ba,bw),(a,w)],[.5,.5])
        result[source]=(prior,aa,ww,class_mass(aa,ww))
    paths=[cp,kp,RECOVERED/f'{stem}_B.npz',RECOVERED/f'{stem}_keys.parquet']
    receipts=[dict(path=str(q),sha256=digest(q)) for q in paths]
    return keys,class_mass(ba,bw),result,receipts


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(),'Do not overwrite a started frozen experiment'
    previous=json.loads((SOURCE/'research_integrity_audit.json').read_text());assert previous['technical_integrity_passed']
    spec=dict(models=MODELS,references=REFERENCES,plan_sha256=digest(PLAN),reference_receipts=previous['receipts'],
        source_fit_sha256=digest(SOURCE/'fit_audit.csv'),tolerance=TOL,max_bin_iterations=MAX_ITER,
        anchor='Same origin same complete cohort frozen-B predictions only; no actual outcome input')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');checks=[];sources=[]
    fits=pd.read_csv(SOURCE/'fit_audit.csv')
    for h in [1,3,6]:
        rp=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in previous['receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256']
        reference=pd.read_parquet(rp)
        bp=OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet';base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        sources.append(dict(path=str(bp),sha256=digest(bp)))
        rows=[reference[reference.model.eq(v)].assign(model=k) for k,v in REFERENCES.items()]
        for date in sorted(base.date.unique()):
            date=pd.Timestamp(date);keys,bp,inputs,receipts=distributions(h,date,base,reference,fits);sources.extend(receipts)
            stem=f'{h}_{date.date()}';keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False)
            for name,(source,mode) in MODELS.items():
                prior,a,w,p=inputs[source];q,parameters,target,iterations,residual=anchor(p,bp,mode)
                cp=CACHE/f'{stem}_{name}.npz';np.savez_compressed(cp,before=p,after=q,parameters=parameters,target=target,baseline=bp)
                checks.append(dict(months=h,date=str(date.date()),model=name,source=source,mode=mode,rows=len(keys),iterations=iterations,
                    residual=residual,cache_sha256=digest(cp),keys_sha256=frame_digest(keys)))
                expected=score(prior,a,w,p,q);pred=prior.copy();pred['model']=name;pred[expected.columns]=expected.to_numpy();rows.append(pred)
            print(h,date.date(),'anchored four distributions',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(checks).to_csv(DEST/'calibration_audit.csv',index=False)
        (DEST/'source_receipts.json').write_text(json.dumps(sources,indent=2)+'\n')


if __name__=='__main__':run()
