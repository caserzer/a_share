"""R28 fixed forest architectures and global-versus-local magnitude ablations."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
import sklearn.ensemble._forest as forest_source
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from prepare_panel import EP, OUT
from build_margin_information import digest
from run_historical_peer_models import CONTROL
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from hierarchical_probabilities import stable_sign_scores
from conditional_forests import training_impute, forest_weights, local_class_distribution

DEST = OUT/'r28_conditional_forests'
CACHE = OUT/'local_cache/r28_forest_distributions'
PANEL = OUT/'local_cache/historical_peer_panel.parquet'
SOURCE = OUT/'r25_historical_peers'
REFERENCE = 'own_momentum_reference'
KINDS = {'rf':RandomForestClassifier, 'extra':ExtraTreesClassifier}
MODES = {'global_mixed':('global',.5), 'local_mixed':('local',.5), 'local_unmixed':('local',1.)}
MODELS = {f'{kind}_{mode}': (kind, shape, fraction) for kind in KINDS for mode,(shape,fraction) in MODES.items()}
PARAMS = dict(n_estimators=96, max_depth=6, min_samples_leaf=150, max_features=.7,
              criterion='gini', random_state=24, n_jobs=4, class_weight=None)


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    fa = json.loads((SOURCE/'feature_audit.json').read_text())
    assert source_audit['technical_integrity_passed'] and digest(PANEL) == fa['feature_sha256']
    panel = pd.read_parquet(PANEL)
    assert not any(c.startswith(('y_', 'end_', 'target_')) for c in CONTROL)
    spec = dict(models=MODELS, features=CONTROL, parameters=PARAMS, sklearn_version=sklearn.__version__,
        sklearn_forest_source=str(Path(forest_source.__file__)), sklearn_forest_source_sha256=digest(Path(forest_source.__file__)),
        panel_sha256=digest(PANEL), plan_sha256=digest(EP/'notes/r28_conditional_forests.md'),
        source_receipts=source_audit['receipts'], training='Mature rows only; expanding; equal month weight; train-only medians and missing indicators',
        bootstrap='sklearn 1.9: weighted sampling, effective leaf weights equal bootstrap counts; no second multiplication',
        evidence='Six fixed candidates, repeated exploration; same original population and 12 gates')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []
    for h in [1,3,6]:
        source = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert digest(source) == receipt['sha256']
        old = pd.read_parquet(source)
        rows = [old[old.model.eq('own_momentum_control')].assign(model=REFERENCE)]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date','instrument']]
            template = base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date','instrument']], keys)
            np.testing.assert_allclose(template.actual, test[f'y_{h}'], equal_nan=True)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet', index=False)
            train = select_training(panel,h,date,None); weights = observation_weights(train,date,True,None)
            y = train[f'y_{h}'].to_numpy(); labels = classes(y)
            assert len(train) >= 1000 and train.date.nunique() >= 18
            tx, qx, medians = training_impute(train[CONTROL], test[CONTROL])
            ba,bw = load_distribution(OUT/'local_cache/r15_distributions',h,date,'B',keys)
            baseline_sign = np.column_stack([(bw*(ba<0)).sum(axis=1),(bw*(ba==0)).sum(axis=1),(bw*(ba>0)).sum(axis=1)])
            for kind, cls in KINDS.items():
                model = cls(**PARAMS, bootstrap=kind=='rf').fit(tx, labels, sample_weight=weights)
                p = np.zeros((len(test),7)); p[:,model.classes_.astype(int)] = model.predict_proba(qx)
                conditional = forest_weights(model,tx,qx,weights)
                empirical = np.column_stack([conditional[:,labels==k].sum(axis=1) for k in range(7)])
                error = float(np.max(np.abs(empirical-p)))
                np.testing.assert_allclose(empirical,p,atol=1e-12,rtol=1e-12)
                local, _ = local_class_distribution(y,conditional,p)
                global_atoms, w = weighted_class_distribution(y,labels,p,weights)
                effective_n = 1/np.square(conditional).sum(axis=1)
                del conditional
                cache = CACHE/f'{h}_{date.date()}_{kind}.npz'
                np.savez_compressed(cache, local_atoms=local, global_atoms=global_atoms[0], probabilities=p,
                    medians=medians, effective_n=effective_n)
                sign = np.column_stack([p[:,:3].sum(axis=1),p[:,3],p[:,4:].sum(axis=1)])
                for mode,(shape,fraction) in MODES.items():
                    a = local if shape=='local' else global_atoms
                    aa,ww = combine_distributions([(ba,bw),(a,w)],[1-fraction,fraction]) if fraction<1 else (a,w)
                    stats = stable_sign_scores(weighted_stats(aa,ww,template.actual),sign,baseline_sign,fraction,template.actual)
                    pred = template.copy(); pred['model'] = f'{kind}_{mode}'; pred[stats.columns] = stats.to_numpy(); rows.append(pred)
                audits.append(dict(months=h,date=str(date.date()),kind=kind,training_rows=len(train),
                    training_months=train.date.nunique(),last_training_label=str(train[f'end_{h}'].max()),
                    test_rows=len(test),total_weight=float(weights.sum()),leaf_probability_max_error=error,
                    mean_effective_samples=float(effective_n.mean()),cache_sha256=digest(cache),
                    imputed_train_sha256=hashlib.sha256(tx.tobytes()).hexdigest(),
                    imputed_test_sha256=hashlib.sha256(qx.tobytes()).hexdigest()))
            print(h,date.date(),'finished',flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv',index=False)


if __name__ == '__main__':
    run()
