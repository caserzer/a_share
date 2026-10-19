"""R41 pooled-horizon learning, fixed four candidates on the original population."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier
from prepare_panel import EP, OUT
from build_margin_information import digest
from recover_baseline_precision import RECOVERED
from run_historical_peer_models import CONTROL
from run_conditional_forests import PARAMS as FOREST_PARAMS
from conditional_forests import training_impute
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution
from run_direct_probability import classes
from run_joint_information import frame_digest, score
from shared_horizon_models import stack_training, pooled_weights, queries

DEST = OUT/'r41_shared_horizon_models'
CACHE = OUT/'local_cache/r41_shared_horizon_models'
PANEL = OUT/'local_cache/historical_peer_panel.parquet'
PLAN = EP/'notes/r41_shared_horizon_models.md'
REFERENCE = OUT/'r31_financial_quality'
POOLS = {'h136': [1, 3, 6], 'h13612': [1, 3, 6, 12]}
MODELS = {f'{family}_{pool}': (family, pool) for family in ['catboost', 'extra'] for pool in POOLS}
CAT = dict(depth=2, iterations=100, learning_rate=.03, l2_leaf_reg=20, random_seed=24)
FEATURES = CONTROL+['horizon_months']


def array_digest(value):
    return hashlib.sha256(np.asarray(value).tobytes()).hexdigest()


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(), 'Do not overwrite a frozen started experiment'
    panel = pd.read_parquet(PANEL)
    fa = json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text()); assert digest(PANEL) == fa['feature_sha256']
    ra = json.loads((REFERENCE/'research_integrity_audit.json').read_text()); assert ra['technical_integrity_passed']
    spec = dict(models=MODELS, pools=POOLS, features=FEATURES, catboost=CAT, extra=FOREST_PARAMS,
        panel_sha256=digest(PANEL), plan_sha256=digest(PLAN), reference_receipts=ra['receipts'],
        total_training_weight='Original mature 3-month row count at this prediction origin; equal horizon mass and equal months within horizon')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    bases={}; rows={}; fits=[]; slices=[]; sources=[]
    for h in [1, 3, 6]:
        bp = OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'; rp = REFERENCE/f'predictions_{h}m.parquet'
        r = next(r for r in ra['receipts'] if r['path'].endswith(rp.name)); assert digest(rp) == r['sha256']
        base = pd.read_parquet(bp); bases[h] = base[base.model.eq('B')]
        ref = pd.read_parquet(rp); rows[h] = [ref[ref.model.isin(['catboost_reference', 'extra_reference'])]]
        sources.extend([dict(path=str(p), sha256=digest(p)) for p in [bp, rp]])
    for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
        test = test.reset_index(drop=True); keys = test[['date', 'instrument']]; stem=str(date.date())
        keys.to_parquet(CACHE/f'{stem}_keys.parquet', index=False)
        query = queries(test, CONTROL); single={}; atoms={}; templates={}; baseline={}
        for h in [1, 3, 6]:
            single[h] = select_training(panel, h, date, None)
            assert len(single[h]) >= 1000 and single[h].date.nunique() >= 18
            template = bases[h][bases[h].date.eq(date)].reset_index(drop=True); templates[h] = template
            pd.testing.assert_frame_equal(template[['date', 'instrument']], keys)
            np.testing.assert_allclose(template.actual, test[f'y_{h}'], equal_nan=True)
            baseline[h] = load_distribution(RECOVERED, h, date, 'B', keys)
            y = single[h][f'y_{h}'].to_numpy(); w = observation_weights(single[h], date, True, None)
            atoms[h], _ = weighted_class_distribution(y, classes(y), np.full((1, 7), 1/7), w)
            for suffix in ['B.npz', 'keys.parquet']:
                path = RECOVERED/f'{h}_{stem}_{suffix}'; sources.append(dict(path=str(path), sha256=digest(path)))
        np.savez_compressed(CACHE/f'{stem}_atoms.npz', **{f'atoms_{h}':a[0] for h, a in atoms.items()})
        for pool, horizons in POOLS.items():
            train = stack_training(panel, date, horizons, CONTROL); weights = pooled_weights(train, len(single[3]))
            labels = classes(train.label)
            for h, group in train.groupby('horizon_months'):
                assert group.date.nunique() >= (12 if h == 12 else 18)
                slices.append(dict(date=stem, pool=pool, horizon=h, rows=len(group), origin_months=group.date.nunique(),
                    last_label_end=str(group.label_end.max()), total_weight=float(weights[group.index].sum())))
            for family in ['catboost', 'extra']:
                name = f'{family}_{pool}'; medians=np.array([]); th='native_missing'; qh='native_missing'
                if family == 'catboost':
                    tx = train[FEATURES].astype(float); qx = query[FEATURES].astype(float)
                    model = CatBoostClassifier(**CAT, loss_function='MultiClass', thread_count=4, verbose=False, allow_writing_files=False)
                else:
                    tx, qx, medians = training_impute(train[FEATURES], query[FEATURES]); th=array_digest(tx); qh=array_digest(qx)
                    model = ExtraTreesClassifier(**FOREST_PARAMS, bootstrap=False)
                model.fit(tx, labels, sample_weight=weights)
                probabilities = np.zeros((len(query), 7)); probabilities[:, model.classes_.astype(int)] = model.predict_proba(qx)
                probabilities = probabilities.reshape(3, len(test), 7)
                path = CACHE/f'{stem}_{name}.npz'; np.savez_compressed(path, probabilities=probabilities, medians=medians)
                fits.append(dict(date=stem, model=name, training_rows=len(train), total_weight=float(weights.sum()),
                    training_digest=frame_digest(train), weights_sha256=array_digest(weights), test_features_sha256=frame_digest(query),
                    imputed_train_sha256=th, imputed_test_sha256=qh, cache_sha256=digest(path), test_rows=len(test)))
                for index, h in enumerate([1, 3, 6]):
                    result = score(templates[h], *baseline[h], np.tile(atoms[h][0], (len(test), 1)), probabilities[index], .5)
                    pred = templates[h].copy(); pred['model'] = name; pred[result.columns] = result.to_numpy(); rows[h].append(pred)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv', index=False)
        pd.DataFrame(slices).to_csv(DEST/'training_slices.csv', index=False)
        print(stem, 'all four pooled models finished', flush=True)
    for h, result in rows.items(): pd.concat(result, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
    (DEST/'source_receipts.json').write_text(json.dumps(sources, indent=2)+'\n')


if __name__ == '__main__': run()
