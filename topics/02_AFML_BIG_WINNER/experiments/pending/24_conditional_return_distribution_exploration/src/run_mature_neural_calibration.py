"""R47 mature-history-only calibration of frozen neural probabilities."""
import json
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_cohort_probability_anchor import distributions,REFERENCES,SOURCE
from run_joint_information import frame_digest
from run_regularized_information import array_digest
from probability_recalibration import class_probabilities,PENALTY
from mature_neural_calibration import history_for,fit_history,apply,WINDOW,MIN_MONTHS,BOUND
from cohort_probability_anchor import score
from run_direct_probability import classes

DEST=OUT/'r47_mature_neural_calibration'
CACHE=OUT/'local_cache/r47_mature_neural_calibration'
PLAN=EP/'notes/r47_mature_neural_calibration.md'
ANCHOR_SOURCE=OUT/'r46_cohort_probability_anchor'
MODELS={f'{source}_{mode}':(source,mode) for source in ['raw','mixed'] for mode in ['sign','bins']}
COHORT_REFERENCES={'cohort_'+name:name for name in MODELS}
HISTORY_COLUMNS=['date','instrument','label_end','actual','p_up','p_down','p_zero','p_loss_over20','p_loss5_20','p_gain5_20','p_gain_over20']


def history_digest(history,mode):
    p=class_probabilities(history) if len(history) else np.empty((0,7))
    y=(history.actual.gt(0).to_numpy() if mode=='sign' else classes(history.actual.to_numpy()))
    return dict(history_sha256=frame_digest(history[HISTORY_COLUMNS]),history_probabilities_sha256=array_digest(p),history_labels_sha256=array_digest(y))


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(),'Do not overwrite a started frozen experiment'
    previous=json.loads((SOURCE/'research_integrity_audit.json').read_text());anchor_audit=json.loads((ANCHOR_SOURCE/'research_integrity_audit.json').read_text())
    assert previous['technical_integrity_passed'] and anchor_audit['technical_integrity_passed']
    spec=dict(models=MODELS,references=REFERENCES,cohort_references=COHORT_REFERENCES,plan_sha256=digest(PLAN),reference_receipts=previous['receipts'],
        cohort_receipts=anchor_audit['receipts'],source_fit_sha256=digest(SOURCE/'fit_audit.csv'),window=WINDOW,minimum_mature_months=MIN_MONTHS,penalty=PENALTY,sign_intercept_bound=BOUND,
        calibration='Only origin<date and label_end<date known outcomes; exact unmodified original during burn-in')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');checks=[];sources=[]
    fits=pd.read_csv(SOURCE/'fit_audit.csv')
    for h in [1,3,6]:
        rp=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in previous['receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256'];reference=pd.read_parquet(rp)
        ap=ANCHOR_SOURCE/f'predictions_{h}m.parquet';r=next(r for r in anchor_audit['receipts'] if r['path'].endswith(ap.name));assert digest(ap)==r['sha256'];cohort=pd.read_parquet(ap)
        bp=OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet';base=pd.read_parquet(bp);base=base[base.model.eq('B')];sources.append(dict(path=str(bp),sha256=digest(bp)))
        rows=[reference[reference.model.eq(v)].assign(model=k) for k,v in REFERENCES.items()]
        rows.extend(cohort[cohort.model.eq(v)].assign(model=k) for k,v in COHORT_REFERENCES.items())
        originals={source:reference[reference.model.eq('alpha16_'+source)] for source in ['raw','mixed']}
        for date in sorted(base.date.unique()):
            date=pd.Timestamp(date);keys,_,inputs,receipts=distributions(h,date,base,reference,fits);sources.extend(receipts)
            stem=f'{h}_{date.date()}';keys.to_parquet(CACHE/f'{stem}_keys.parquet',index=False)
            for name,(source,mode) in MODELS.items():
                prior,a,w,p=inputs[source];np.testing.assert_allclose(class_probabilities(prior),p,atol=1e-12,rtol=1e-12)
                history=history_for(originals[source],date,mode)
                parameters,active,info=fit_history(history,mode);q=apply(p,parameters,mode) if active else p.copy()
                cp=CACHE/f'{stem}_{name}.npz';np.savez_compressed(cp,before=p,after=q,parameters=parameters)
                checks.append(dict(months=h,date=str(date.date()),model=name,source=source,mode=mode,test_rows=len(keys),active=active,
                    history_rows=len(history),history_months=history.date.nunique(),first_origin=str(history.date.min()),last_origin=str(history.date.max()),
                    last_history_label=str(history.label_end.max()),**history_digest(history,mode),**info,cache_sha256=digest(cp),keys_sha256=frame_digest(keys)))
                pred=prior.copy();pred['model']=name
                if active:
                    expected=score(prior,a,w,p,q);pred[expected.columns]=expected.to_numpy()
                rows.append(pred)
            print(h,date.date(),'four chronological calibrations complete',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(checks).to_csv(DEST/'fit_audit.csv',index=False)
        (DEST/'source_receipts.json').write_text(json.dumps(sources,indent=2)+'\n')


if __name__=='__main__':run()
