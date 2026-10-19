"""R30 reconstruct seven frozen streams and their exact finite-CDF distances."""
import json
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import weighted_stats
from hierarchical_probabilities import assemble_classes
from diverse_ensemble import cdf_distance,mixed_crps
from run_four_horizons import BIN_NAMES,probability_stats
from recover_baseline_precision import RECOVERED

DEST=OUT/'r30_diverse_ensemble'
CACHE=OUT/'local_cache/r30_diverse_sources'
NAMES=['B','catboost','rf','extra','sign','margin','global']
SOURCE_MODELS={'catboost':('r25_historical_peers','own_momentum_control',.5),
 'rf':('r28_conditional_forests','rf_local_unmixed',1.),'extra':('r28_conditional_forests','extra_local_unmixed',1.),
 'sign':('r26_direction_first','sign_hierarchy_unmixed',1.),'margin':('r27_margin_information','both_margin',.5),
 'global':('r29_global_risk','extra_both',.5)}
CLASS_CACHES={'catboost':('r25_class_distributions','own_momentum_control'),
              'margin':('r27_class_distributions','both_margin'),'global':('r29_class_distributions','extra_both')}


def load_components(h,date,keys):
    stem=f'{h}_{date.date()}';paths=[]
    base_cache=RECOVERED
    distributions={'B':load_distribution(base_cache,h,date,'B',keys)}
    paths.extend([base_cache/f'{stem}_keys.parquet',base_cache/f'{stem}_B.npz'])
    for name,(folder,model) in CLASS_CACHES.items():
        directory=OUT/'local_cache'/folder;kp=directory/f'{stem}_keys.parquet';path=directory/f'{stem}_{model}.npz'
        pd.testing.assert_frame_equal(pd.read_parquet(kp),keys);paths.extend([kp,path])
        with np.load(path) as x:q=x['class_atoms'];p=x['probabilities']
        distributions[name]=(np.tile(q,(len(keys),1)),np.repeat(p/32,32,axis=1))
    directory=OUT/'local_cache/r28_forest_distributions';kp=directory/f'{stem}_keys.parquet'
    pd.testing.assert_frame_equal(pd.read_parquet(kp),keys);paths.append(kp)
    for name in ['rf','extra']:
        path=directory/f'{stem}_{name}.npz';paths.append(path)
        with np.load(path) as x:a=x['local_atoms'];p=x['probabilities']
        distributions[name]=(a,np.repeat(p/32,32,axis=1))
    directory=OUT/'local_cache/r26_sign_distributions';kp=directory/f'{stem}_keys.parquet';path=directory/f'{stem}.npz'
    pd.testing.assert_frame_equal(pd.read_parquet(kp),keys);paths.extend([kp,path])
    with np.load(path) as x:
        p=assemble_classes(x['sign'],x['negative'],x['positive']);q=x['class_atoms']
    distributions['sign']=(np.tile(q,(len(keys),1)),np.repeat(p/32,32,axis=1))
    return [distributions[n] for n in NAMES],paths


def prepare():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    recovery=json.loads((DEST/'baseline_precision_audit.json').read_text());assert recovery['recovery_matches_all_frozen_baseline_scores']
    all_receipts=[];pred_receipts=[];prepared=[];max_identity_error=0.;checked=0;max_baseline_cache_error=0.
    for h in [1,3,6]:
        path=OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'
        base=pd.read_parquet(path);base=base[base.model.eq('B')].reset_index(drop=True)
        pred_receipts.append(dict(path=str(path),sha256=digest(path)))
        references={}
        for name,(folder,model,fraction) in SOURCE_MODELS.items():
            path=OUT/folder/f'predictions_{h}m.parquet'
            audit=json.loads((OUT/folder/'research_integrity_audit.json').read_text());assert audit['technical_integrity_passed']
            receipt=next(r for r in audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
            assert digest(path)==receipt['sha256'];pred_receipts.append(dict(path=str(path),sha256=digest(path)))
            frame=pd.read_parquet(path);references[name]=frame[frame.model.eq(model)]
        chunks=[];signs=[];bins=[];scores=[];distances=[];uniforms=[]
        for date,template in base.groupby('date',sort=True):
            template=template.reset_index(drop=True);keys=template[['date','instrument']]
            distributions,paths=load_components(h,date,keys)
            old_base=load_distribution(OUT/'local_cache/r15_distributions',h,date,'B',keys)
            paths.extend([OUT/f'local_cache/r15_distributions/{h}_{date.date()}_B.npz',
                          OUT/f'local_cache/r15_distributions/{h}_{date.date()}_keys.parquet'])
            all_receipts.extend([dict(path=str(p),sha256=digest(p)) for p in paths])
            stats=[weighted_stats(a,w,template.actual) for a,w in distributions]
            for i,name in enumerate(NAMES):
                if name=='B':
                    expected=template;current=probability_stats(distributions[0][0],template.actual)
                    np.testing.assert_allclose(current,expected[current.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
                    max_baseline_cache_error=max(max_baseline_cache_error,float((current-expected[current.columns]).abs().max().max()))
                else:
                    expected=references[name][references[name].date.eq(date)].reset_index(drop=True)
                    pd.testing.assert_frame_equal(expected[['date','instrument']],keys)
                    np.testing.assert_allclose(expected.actual,template.actual,equal_nan=True)
                    for c in ['label_end','target_date']:pd.testing.assert_series_equal(expected[c],template[c],check_names=False)
                    fraction=SOURCE_MODELS[name][2]
                    current=stats[i] if fraction==1 else weighted_stats(*combine_distributions([old_base,distributions[i]],[.5,.5]),template.actual)
                if name!='B':np.testing.assert_allclose(current,expected[current.columns],atol=1e-10,rtol=1e-10,equal_nan=True)
                checked+=len(template)
            sign=np.stack([s[['p_down','p_zero','p_up']].to_numpy() for s in stats],axis=1)
            p5=np.stack([s[['p_'+n for n in BIN_NAMES]].to_numpy() for s in stats],axis=1)
            crps=np.column_stack([s.crps for s in stats]);distance=np.zeros((len(template),len(NAMES),len(NAMES)))
            for i in range(len(NAMES)):
                for j in range(i):
                    d=cdf_distance(*distributions[i],*distributions[j]);distance[:,i,j]=distance[:,j,i]=d
            uniform=np.full(len(NAMES),1/len(NAMES));ua,uw=combine_distributions(distributions,uniform)
            ustats=weighted_stats(ua,uw,template.actual)
            predicted=mixed_crps(crps,distance,uniform)
            np.testing.assert_allclose(predicted,ustats.crps,atol=1e-12,rtol=1e-12,equal_nan=True)
            finite=np.isfinite(predicted)
            if finite.any():max_identity_error=max(max_identity_error,float(np.max(np.abs(predicted[finite]-ustats.crps.to_numpy()[finite]))))
            prediction=template.copy();prediction['model']='uniform_diverse';prediction[ustats.columns]=ustats.to_numpy()
            chunks.append(template);uniforms.append(prediction);signs.append(sign);bins.append(p5);scores.append(crps);distances.append(distance)
            print('sources',h,date.date(),flush=True)
        metadata=pd.concat(chunks,ignore_index=True);npz=CACHE/f'sources_{h}m.npz';keypath=CACHE/f'keys_{h}m.parquet';upath=CACHE/f'uniform_{h}m.parquet'
        metadata.to_parquet(keypath,index=False);pd.concat(uniforms,ignore_index=True).to_parquet(upath,index=False)
        np.savez_compressed(npz,sign=np.concatenate(signs),five_bin=np.concatenate(bins),crps=np.concatenate(scores),distance=np.concatenate(distances))
        prepared.extend([dict(path=str(p),sha256=digest(p)) for p in [npz,keypath,upath]])
    pd.DataFrame(all_receipts).drop_duplicates('path').to_csv(DEST/'input_cache_receipts.csv',index=False)
    audit=dict(technical_source_integrity_passed=True,source_names=NAMES,source_predictions_reconstructed=checked,
        max_crps_mixture_identity_error=max_identity_error,max_recovered_baseline_score_error=max_baseline_cache_error,
        baseline_cache_note='B float64 atoms recovered and original scores matched. Older mixed-source references retain their original float32 B component for provenance checks only.',
        baseline_recovery_audit_sha256=digest(DEST/'baseline_precision_audit.json'),
        plan_sha256=digest(EP/'notes/r30_diverse_ensemble.md'),
        input_cache_receipts_sha256=digest(DEST/'input_cache_receipts.csv'),prediction_receipts=pred_receipts,prepared_receipts=prepared)
    (DEST/'source_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k not in ['prediction_receipts','prepared_receipts']},indent=2))


if __name__=='__main__':prepare()
