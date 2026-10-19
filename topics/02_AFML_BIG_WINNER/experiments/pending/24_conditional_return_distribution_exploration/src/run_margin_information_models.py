"""R27 three fixed margin-information ablations against frozen own-momentum control."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import EP, OUT
from build_margin_information import DEST, PANEL, INDIVIDUAL, MARKET
SOURCE = OUT/'r25_historical_peers'
from run_price_volume_models import CONTROL as OLD_CONTROL
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats

CACHE = OUT/'local_cache/r27_class_distributions'
CONTROL = OLD_CONTROL+['mom21', 'mom63', 'mom126']
REFERENCE = 'own_momentum_reference'
MODELS = {'individual_margin': INDIVIDUAL, 'market_margin': MARKET, 'both_margin': INDIVIDUAL+MARKET}


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    fa = json.loads((DEST/'feature_audit.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == fa['feature_sha256']
    assert hashlib.sha256((EP/'notes/r27_margin_information.md').read_bytes()).hexdigest() == fa['plan_sha256']
    panel = pd.read_parquet(PANEL)
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    assert source_audit['technical_integrity_passed']
    spec = dict(control_features=CONTROL, models=MODELS, feature_sha256=fa['feature_sha256'], plan_sha256=fa['plan_sha256'],
        iterations=100, depth=2, learning_rate=.03, l2_leaf_reg=20, random_seed=24, month_balanced=True,
        min_training_rows=1000, min_training_months=18, candidate_weight=.5,
        reference=REFERENCE, reference_source_model='own_momentum_control', source_receipts=source_audit['receipts'],
        population='Same original 27600 stock-dates and mature training rows; no missing-margin filtering or outcome-dependent selection',
        evidence='Three fixed additions to frozen own-momentum control; features fixed before scoring')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []
    for h in [1, 3, 6]:
        source_path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == receipt['sha256']
        original = pd.read_parquet(source_path)
        reference = original[original.model.eq('own_momentum_control')].assign(model=REFERENCE)
        rows = [reference]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date', 'instrument']]
            template = base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date', 'instrument']], keys)
            np.testing.assert_allclose(template.actual, test[f'y_{h}'], equal_nan=True)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet', index=False)
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', keys)
            train = select_training(panel, h, date, None)
            weights = observation_weights(train, date, True, None)
            y = train[f'y_{h}'].to_numpy(); labels = classes(y)
            active = len(train) >= 1000 and train.date.nunique() >= 18
            for name, added in MODELS.items():
                prediction = template.copy(); prediction['model'] = name
                if active:
                    cols = CONTROL+added
                    model = CatBoostClassifier(loss_function='MultiClass', depth=2, iterations=100,
                        learning_rate=.03, l2_leaf_reg=20, random_seed=24, thread_count=4,
                        verbose=False, allow_writing_files=False)
                    model.fit(train[cols].astype(float), labels, sample_weight=weights)
                    p = np.zeros((len(test), 7)); p[:, model.classes_.astype(int)] = model.predict_proba(test[cols].astype(float))
                    a, w = weighted_class_distribution(y, labels, p, weights)
                    np.savez_compressed(CACHE/f'{h}_{date.date()}_{name}.npz', class_atoms=a[0], probabilities=p)
                    a, w = combine_distributions([(ba, bw), (a, w)], [.5, .5])
                    stats = weighted_stats(a, w, template.actual); prediction[stats.columns] = stats.to_numpy()
                rows.append(prediction)
                audits.append(dict(months=h, date=str(date.date()), model=name, training_rows=len(train),
                    training_months=train.date.nunique(), last_training_label=str(train[f'end_{h}'].max()),
                    total_weight=float(weights.sum()), test_rows=len(test), adjusted_rows=len(test) if active else 0))
            print(h, date.date(), 'finished', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)


if __name__ == '__main__':
    run()
