"""R30 expanding/recent causal mixtures and sign stacking; fixed uniform warmup."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP
from build_margin_information import digest
from prepare_diverse_sources import DEST,CACHE,NAMES,load_components
from diverse_ensemble import fit_joint_mixture,fit_sign_stack,sign_transform,replace_sign_mass,mixed_crps,PENALTY
from probability_recalibration import calibration_history
from run_prequential_search import combine_distributions
from run_direct_probability import weighted_stats
from hierarchical_probabilities import stable_sign_scores

MODELS={'joint_expanding':('joint',None),'joint_recent24':('joint',24),
        'sign_expanding':('sign',None),'sign_recent24':('sign',24)}
ALL_MODELS=['uniform_diverse']+list(MODELS)
MIN_MONTHS=12


def run():
    audit=json.loads((DEST/'source_audit.json').read_text());assert audit['technical_source_integrity_passed']
    assert digest(EP/'notes/r30_diverse_ensemble.md')==audit['plan_sha256']
    for r in audit['prepared_receipts']:assert digest(Path(r['path']))==r['sha256']
    spec=dict(models=MODELS,source_names=NAMES,minimum_mature_months=MIN_MONTHS,penalty=PENALTY,
        source_audit_sha256=digest(DEST/'source_audit.json'),plan_sha256=audit['plan_sha256'],
        warmup='Exact uniform seven-source distribution; no row deletion',
        numerical_marginals='Analytic component/sign-transform margins, verified against atoms; same strict p_up>p_down rule',
        training='Only earlier origins with observed label_end strictly before prediction; equal origin-month weight',
        evidence='Five fixed candidates; repeated historical exploration; unchanged 12 gates')
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');fits=[];parameters=[]
    for h in [1,3,6]:
        base=pd.read_parquet(CACHE/f'keys_{h}m.parquet');uniform=pd.read_parquet(CACHE/f'uniform_{h}m.parquet')
        with np.load(CACHE/f'sources_{h}m.npz') as p:data={k:p[k] for k in p.files}
        results=[uniform]
        for date,template in base.groupby('date',sort=True):
            current_index=template.index.to_numpy();template=template.reset_index(drop=True);keys=template[['date','instrument']]
            components,_=load_components(h,date,keys);prior=np.full(len(NAMES),1/len(NAMES));ua,uw=combine_distributions(components,prior)
            fallback=uniform[uniform.date.eq(date)].reset_index(drop=True)
            current_sign=data['sign'][current_index]
            for name,(kind,window) in MODELS.items():
                history=calibration_history(base,date,window);active=history.date.nunique()>=MIN_MONTHS
                prediction=fallback.copy();prediction['model']=name
                coefficients=prior.copy();pars=np.zeros((len(NAMES)+1)*3);fit_info={}
                if active:
                    ix=history.index.to_numpy();y=history.actual.to_numpy()
                    if kind=='joint':
                        coefficients,fit_info=fit_joint_mixture(data['sign'][ix],data['five_bin'][ix],data['crps'][ix],data['distance'][ix],y,history.date,
                            history[['brier','multiclass_brier','crps']].to_numpy())
                        a,w=combine_distributions(components,coefficients)
                        stats=weighted_stats(a,w,template.actual)
                        np.testing.assert_allclose(stats.crps,mixed_crps(data['crps'][current_index],data['distance'][current_index],coefficients),atol=1e-12,rtol=1e-12,equal_nan=True)
                        target=np.einsum('nsc,s->nc',current_sign,coefficients)
                    else:
                        pars,fit_info=fit_sign_stack(data['sign'][ix],y,history.date)
                        target=sign_transform(current_sign,pars);a,w=replace_sign_mass(ua,uw,target);stats=weighted_stats(a,w,template.actual)
                        np.testing.assert_allclose(stats[['p_down','p_zero','p_up']],target,atol=1e-12)
                    stats=stable_sign_scores(stats,target,target,1.,template.actual)
                    prediction[stats.columns]=stats.to_numpy()
                results.append(prediction)
                fits.append(dict(months=h,date=str(date.date()),model=name,active=active,history_rows=len(history),history_months=history.date.nunique(),
                    first_origin=str(history.date.min()),last_origin=str(history.date.max()),latest_history_label=str(history.label_end.max()),test_rows=len(template)))
                parameters.append(dict(months=h,date=str(date.date()),model=name,active=active,kind=kind,
                    coefficients=coefficients.tolist(),sign_parameters=pars.tolist(),**fit_info))
            print('ensemble',h,date.date(),flush=True)
        pd.concat(results,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv',index=False)
        (DEST/'parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')


if __name__=='__main__':run()
