"""R40 fixed split-loss experiment with the original features and capacity."""
import hashlib
import json
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import ExtraTreesRegressor
from prepare_panel import EP, OUT
from build_margin_information import digest
from run_historical_peer_models import CONTROL
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from conditional_forests import training_impute
from run_direct_probability import classes
from run_joint_information import frame_digest, score
from run_issuer_calibration import priors
from probability_loss_forests import loss_targets, leaf_means, leaf_probabilities

DEST = OUT/'r40_probability_loss_forests'
CACHE = OUT/'local_cache/r40_probability_loss_forests'
PANEL = OUT/'local_cache/historical_peer_panel.parquet'
PLAN = EP/'notes/r40_probability_loss_forests.md'
REFERENCE = OUT/'r31_financial_quality'
PARAMS = dict(n_estimators=96, max_depth=6, min_samples_leaf=150, max_features=.7,
    criterion='squared_error', random_state=24, n_jobs=4, bootstrap=False)
MODELS = {f'{kind}_{mix}': (kind, fraction) for kind in ['ordinal', 'joint'] for mix, fraction in [('raw', 1.), ('mixed', .5)]}


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(), 'A frozen started run must not be overwritten'
    audit = json.loads((REFERENCE/'research_integrity_audit.json').read_text()); assert audit['technical_integrity_passed']
    panel = pd.read_parquet(PANEL)
    feature_audit = json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text())
    assert digest(PANEL) == feature_audit['feature_sha256']
    spec = dict(models=MODELS, parameters=PARAMS, features=CONTROL, sklearn_version=sklearn.__version__,
        panel_sha256=digest(PANEL), plan_sha256=digest(PLAN), reference_receipts=audit['receipts'])
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n'); fits=[]; sources=[]
    for h in [1, 3, 6]:
        bp = OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'; rp = REFERENCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in audit['receipts'] if r['path'].endswith(rp.name)); assert digest(rp) == receipt['sha256']
        base = pd.read_parquet(bp); base = base[base.model.eq('B')]
        ref = pd.read_parquet(rp); ref = ref[ref.model.eq('extra_reference')]; rows=[ref]
        sources.extend([dict(path=str(p), sha256=digest(p)) for p in [bp, rp]])
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date', 'instrument']]; stem=f'{h}_{date.date()}'
            keys.to_parquet(CACHE/f'{stem}_keys.parquet', index=False)
            distributions, receipts = priors(h, date, base, ref, keys); sources.extend(receipts)
            template, ba, bw = distributions['base']
            train = select_training(panel, h, date, None); w = observation_weights(train, date, True, None)
            assert len(train) >= 1000 and train.date.nunique() >= 18
            y = train[f'y_{h}'].to_numpy(); labels = classes(y)
            atoms, _ = weighted_class_distribution(y, labels, np.full((1, 7), 1/7), w)
            tx, qx, medians = training_impute(train[CONTROL], test[CONTROL])
            for kind in ['ordinal', 'joint']:
                targets, metadata = loss_targets(y, w, kind)
                model = ExtraTreesRegressor(**PARAMS); model.fit(tx, targets, sample_weight=w)
                tl = model.apply(tx).astype(np.int16); ql = model.apply(qx).astype(np.int16)
                predicted = model.predict(qx)
                np.testing.assert_allclose(predicted, leaf_means(tl, ql, targets, w), atol=1e-11, rtol=1e-11)
                p = leaf_probabilities(tl, ql, y, w)
                cache = CACHE/f'{stem}_{kind}.npz'
                np.savez_compressed(cache, train_leaves=tl, test_leaves=ql, predicted_targets=predicted,
                    probabilities=p, class_atoms=atoms[0], medians=medians, **metadata)
                fits.append(dict(months=h, date=str(date.date()), kind=kind, training_rows=len(train),
                    training_months=train.date.nunique(), last_training_label=str(train[f'end_{h}'].max()),
                    test_rows=len(test), total_weight=float(w.sum()), target_dimensions=targets.shape[1],
                    cache_sha256=digest(cache), train_features_sha256=frame_digest(train[CONTROL]), test_features_sha256=frame_digest(test[CONTROL]),
                    imputed_train_sha256=hashlib.sha256(tx.tobytes()).hexdigest(), imputed_test_sha256=hashlib.sha256(qx.tobytes()).hexdigest(),
                    targets_sha256=hashlib.sha256(targets.tobytes()).hexdigest()))
                for mix, fraction in [('raw', 1.), ('mixed', .5)]:
                    result = score(template, ba, bw, np.tile(atoms[0], (len(test), 1)), p, fraction)
                    pred = template.copy(); pred['model'] = f'{kind}_{mix}'; pred[result.columns] = result.to_numpy(); rows.append(pred)
            print(h, date.date(), 'finished', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv', index=False)
        (DEST/'source_receipts.json').write_text(json.dumps(sources, indent=2)+'\n')


if __name__ == '__main__': run()
