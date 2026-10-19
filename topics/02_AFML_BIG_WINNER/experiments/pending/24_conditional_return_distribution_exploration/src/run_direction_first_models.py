"""R26 fixed sign head plus frozen or separately learned conditional magnitudes."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import EP, OUT
from build_historical_peers import PANEL, DEST as SOURCE
from run_historical_peer_models import CONTROL, CACHE as SOURCE_CACHE
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from hierarchical_probabilities import sign_classes, conditional_magnitudes, assemble_classes, stable_sign_scores

DEST = OUT/'r26_direction_first'
CACHE = OUT/'local_cache/r26_sign_distributions'
REFERENCE = 'r25_own_momentum_reference'
MODELS = {f'{kind}_{suffix}': (kind, fraction) for kind in ['sign_reweight', 'sign_hierarchy']
          for suffix, fraction in [('mixed', .5), ('unmixed', 1.)]}


def fit_head(train, labels, query, weights, minimum):
    labels = np.asarray(labels, dtype=int); weights = np.asarray(weights, dtype=float)
    counts = np.bincount(labels, weights=weights, minlength=3)
    if len(train) < minimum or len(np.unique(labels)) < 2:
        prior = counts/counts.sum() if counts.sum() > 0 else np.full(3, 1/3)
        return np.tile(prior, (len(query), 1)), 'mature_weighted_frequency'
    model = CatBoostClassifier(loss_function='MultiClass', depth=2, iterations=100,
        learning_rate=.03, l2_leaf_reg=20, random_seed=24, thread_count=4,
        verbose=False, allow_writing_files=False)
    model.fit(train[CONTROL].astype(float), labels, sample_weight=weights)
    p = np.zeros((len(query), 3)); p[:, model.classes_.astype(int)] = model.predict_proba(query[CONTROL].astype(float))
    return p, 'classifier'


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    panel = pd.read_parquet(PANEL)
    fa = json.loads((SOURCE/'feature_audit.json').read_text())
    old_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    assert old_audit['technical_integrity_passed']
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == fa['feature_sha256']
    spec = dict(models=MODELS, features=CONTROL, feature_sha256=fa['feature_sha256'],
        plan_sha256=hashlib.sha256((EP/'notes/r26_direction_first.md').read_bytes()).hexdigest(),
        iterations=100, depth=2, learning_rate=.03, l2_leaf_reg=20, random_seed=24,
        month_balanced=True, min_training_rows=1000, min_training_months=18, min_conditional_rows=300,
        source_receipts=old_audit['receipts'], reference=REFERENCE, reference_source_model='own_momentum_control',
        sign_order=['down', 'zero', 'up'], conditional_order=['negative_3_bins', 'positive_3_bins'],
        evidence='Four predefined candidates; no threshold selection; same sign head across magnitude variants; differing architectures do not have identical total model capacity')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []; cache_receipts = []
    for h in [1, 3, 6]:
        path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in old_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
        old = pd.read_parquet(path); old = old[old.model.eq('own_momentum_control')].assign(model=REFERENCE)
        rows = [old]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, query in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            query = query.reset_index(drop=True); keys = query[['date', 'instrument']]
            template = base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date', 'instrument']], keys)
            np.testing.assert_allclose(template.actual, query[f'y_{h}'], equal_nan=True)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet', index=False)
            train = select_training(panel, h, date, None); weights = observation_weights(train, date, True, None)
            y = train[f'y_{h}'].to_numpy(); c = classes(y); sign_y = sign_classes(y)
            active = len(train) >= 1000 and train.date.nunique() >= 18
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', keys)
            baseline_sign = np.column_stack([(bw*(ba < 0)).sum(axis=1), (bw*(ba == 0)).sum(axis=1), (bw*(ba > 0)).sum(axis=1)])
            modes = {}; prior = np.bincount(c, weights=weights, minlength=7)/weights.sum()
            if active:
                source_path = SOURCE_CACHE/f'{h}_{date.date()}_own_momentum_control.npz'
                source_keys = SOURCE_CACHE/f'{h}_{date.date()}_keys.parquet'
                pd.testing.assert_frame_equal(pd.read_parquet(source_keys), keys)
                with np.load(source_path) as payload:
                    atoms, flat = payload['class_atoms'], payload['probabilities']
                expected, _ = weighted_class_distribution(y, c, np.full((1, 7), 1/7), weights)
                np.testing.assert_array_equal(atoms, expected[0])
                cache_receipts.extend([dict(path=str(source_path), sha256=hashlib.sha256(source_path.read_bytes()).hexdigest()),
                    dict(path=str(source_keys), sha256=hashlib.sha256(source_keys.read_bytes()).hexdigest())])
                sign, modes['sign'] = fit_head(train, sign_y, query, weights, 1000)
                negative = y < 0; positive = y > 0
                neg, modes['negative'] = fit_head(train[negative], c[negative], query, weights[negative], 300)
                pos, modes['positive'] = fit_head(train[positive], c[positive]-4, query, weights[positive], 300)
                old_neg, old_pos = conditional_magnitudes(flat, prior)
                p7 = {'sign_reweight': assemble_classes(sign, old_neg, old_pos), 'sign_hierarchy': assemble_classes(sign, neg, pos)}
                np.savez_compressed(CACHE/f'{h}_{date.date()}.npz', sign=sign, negative=neg, positive=pos, prior=prior, class_atoms=atoms)
            for name, (kind, fraction) in MODELS.items():
                prediction = template.copy(); prediction['model'] = name
                if active:
                    a = np.tile(atoms, (len(query), 1)); w = np.repeat(p7[kind]/32, 32, axis=1)
                    aa, ww = combine_distributions([(ba, bw), (a, w)], [1-fraction, fraction]) if fraction < 1 else (a, w)
                    stats = stable_sign_scores(weighted_stats(aa, ww, template.actual), sign, baseline_sign, fraction, template.actual)
                    prediction[stats.columns] = stats.to_numpy()
                rows.append(prediction)
            audits.append(dict(months=h, date=str(date.date()), training_rows=len(train), training_months=train.date.nunique(),
                last_training_label=str(train[f'end_{h}'].max()), test_rows=len(query), adjusted_rows=len(query) if active else 0,
                negative_rows=int((y < 0).sum()), zero_rows=int((y == 0).sum()), positive_rows=int((y > 0).sum()),
                total_weight=float(weights.sum()), negative_weight=float(weights[y < 0].sum()), positive_weight=float(weights[y > 0].sum()),
                sign_mode=modes.get('sign', 'baseline'), negative_mode=modes.get('negative', 'baseline'), positive_mode=modes.get('positive', 'baseline')))
            print(h, date.date(), 'finished', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)
        pd.DataFrame(cache_receipts).to_csv(DEST/'source_cache_receipts.csv', index=False)


if __name__ == '__main__':
    run()
