"""R43 remove B shrinkage from already audited R42 distributions; no new fits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_scaled_horizon_models import DEST as SOURCE,CACHE,PANEL,PLAN as SOURCE_PLAN,MODELS as COMPONENTS,training_sets
from scaled_horizon_models import restore_atoms
from run_market_time_models import weighted_class_distribution
from run_direct_probability import classes
from run_joint_information import score
from run_prequential_search import load_distribution
from run_four_horizons import probability_stats,BIN_NAMES
from recover_baseline_precision import RECOVERED
from diagnose_prediction_target import DEST as TARGET

DEST=OUT/'r43_scaled_unmixed'
PLAN=EP/'notes/r43_scaled_unmixed.md'
MODELS={name+'_raw':name for name in COMPONENTS}
PROBS=['p_down','p_zero','p_up']+['p_'+name for name in BIN_NAMES]


def build():
    DEST.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(),'Do not overwrite a started experiment'
    audit=json.loads((SOURCE/'research_integrity_audit.json').read_text());assert audit['technical_integrity_passed']
    source_spec=json.loads((SOURCE/'spec.json').read_text())
    assert digest(PANEL)==source_spec['panel_sha256'] and digest(SOURCE_PLAN)==source_spec['plan_sha256']
    panel=pd.read_parquet(PANEL);fits=pd.read_csv(SOURCE/'fit_audit.csv');assert len(fits)==512
    inherited=[SOURCE/'research_integrity_audit.json',SOURCE/'spec.json',SOURCE/'fit_audit.csv',SOURCE_PLAN,PANEL]
    receipts={str(p):digest(p) for p in inherited}
    for r in json.loads((SOURCE/'source_receipts.json').read_text()):
        p=Path(r['path']);assert digest(p)==r['sha256'];receipts[str(p)]=r['sha256']
    for _,r in fits.iterrows():
        p=CACHE/f'{r.component_horizon}_{r.date}_{r.model}.npz'
        assert digest(p)==r.cache_sha256;receipts[str(p)]=r.cache_sha256
    spec=dict(models=MODELS,plan_sha256=digest(PLAN),source_audit_sha256=digest(SOURCE/'research_integrity_audit.json'),
        source_spec_sha256=digest(SOURCE/'spec.json'),source_plan_sha256=digest(SOURCE_PLAN),panel_sha256=digest(PANEL),
        source_prediction_receipts=audit['receipts'],new_fits=0,raw_fraction=1.,matched_reference_fraction=.5)
    (DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    contract=json.loads((TARGET/'target_contract.json').read_text());reconstructed=0;newrows=0;max_prob_error=0.;max_brier_error=0.;pred_receipts=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        oldpath=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in audit['receipts'] if r['path'].endswith(oldpath.name))
        assert digest(oldpath)==r['sha256'];receipts[str(oldpath)]=r['sha256'];old=pd.read_parquet(oldpath)
        rows=[old[old.model.eq(name)].assign(model=name+'_mixed') for name in COMPONENTS]
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']];stamp=str(date.date())
            kp=CACHE/f'{stamp}_keys.parquet';pd.testing.assert_frame_equal(pd.read_parquet(kp),keys);receipts[str(kp)]=digest(kp)
            own,weights,_,_=training_sets(panel,date);u=own[h].normalized_label.to_numpy()
            proto,_=weighted_class_distribution(u,classes(u),np.full((1,7),1/7),weights[h])
            ap=CACHE/f'{stamp}_atoms.npz'
            with np.load(ap) as payload:np.testing.assert_array_equal(proto[0],payload[f'atoms_{h}'])
            receipts[str(ap)]=digest(ap);atoms=restore_atoms(proto[0],test.vol63,h)
            template=base[base.date.eq(date)].reset_index(drop=True);pd.testing.assert_frame_equal(template[['date','instrument']],keys)
            np.testing.assert_allclose(template.actual,test[f'y_{h}'],equal_nan=True)
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            bs=probability_stats(ba,template.actual);np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            for rawname,component in MODELS.items():
                mode=COMPONENTS[component][1];ch=0 if mode=='shared' else h
                with np.load(CACHE/f'{ch}_{stamp}_{component}.npz') as payload:p=payload['probabilities']
                if ch==0:
                    j=[1,3,6].index(h);p=p[j*len(test):(j+1)*len(test)]
                mixed=score(template,ba,bw,atoms,p,.5);frozen=old[old.date.eq(date)&old.model.eq(component)].reset_index(drop=True)
                pd.testing.assert_frame_equal(frozen[['date','instrument']],keys)
                np.testing.assert_allclose(mixed,frozen[mixed.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
                assert np.array_equal(mixed.p_up.gt(mixed.p_down),frozen.p_up.gt(frozen.p_down));reconstructed+=len(test)
                raw=score(template,ba,bw,atoms,p,1.)
                avg=(template[PROBS].to_numpy()+raw[PROBS].to_numpy())/2
                np.testing.assert_allclose(mixed[PROBS],avg,atol=1e-12,rtol=1e-12)
                max_prob_error=max(max_prob_error,float(np.max(np.abs(mixed[PROBS].to_numpy()-avg))))
                for metric,columns in [('brier',['p_up']),('multiclass_brier',PROBS[3:])]:
                    squared=((template[columns].to_numpy()-raw[columns].to_numpy())**2).sum(axis=1)
                    expected=.5*(template[metric].to_numpy()+raw[metric].to_numpy())-.25*squared
                    np.testing.assert_allclose(mixed[metric],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                    err=np.abs(mixed[metric].to_numpy()-expected);err=err[np.isfinite(err)]
                    if len(err):max_brier_error=max(max_brier_error,float(err.max()))
                pred=template.copy();pred['model']=rawname;pred[raw.columns]=raw.to_numpy();rows.append(pred);newrows+=len(test)
        path=DEST/f'predictions_{h}m.parquet';pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        pred_receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'raw and frozen mixed rebuilt',flush=True)
    assert reconstructed==newrows==331200
    result=dict(reconstruction_passed=True,new_fits=0,source_fit_cache_hashes_checked=len(fits),frozen_mixed_rows_reconstructed=reconstructed,
        new_raw_rows_reconstructed=newrows,max_probability_mixture_error=max_prob_error,max_brier_identity_error=max_brier_error,receipts=pred_receipts)
    (DEST/'reconstruction_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (DEST/'reused_source_receipts.json').write_text(json.dumps([dict(path=p,sha256=s) for p,s in receipts.items()],indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='receipts'},indent=2))


if __name__=='__main__':build()
