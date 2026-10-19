"""R23 matched activity/path feature ablations and two fixed model capacities."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import OUT
from build_price_volume_features import DEST, PANEL, ACTIVITY, PATH
from run_market_time_models import DEST as SOURCE, STOCK, MARKET, select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats

CACHE = OUT/'local_cache/r23_class_distributions'
CONTROL = STOCK + MARKET + ['turnover21', 'log_money21']
REFERENCE = 'r21_month_reference'
MODELS = {
    'activity_means_control': ([], 2, 100, 20),
    'activity_interactions': (ACTIVITY, 2, 100, 20),
    'intraday_paths': (PATH, 2, 100, 20),
    'activity_and_paths': (ACTIVITY+PATH, 2, 100, 20),
    'activity_means_depth4': ([], 4, 200, 50),
    'activity_and_paths_depth4': (ACTIVITY+PATH, 4, 200, 50),
}


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    audit = json.loads((DEST/'feature_audit.json').read_text())
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == audit['feature_sha256']
    panel = pd.read_parquet(PANEL)
    original_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    spec = dict(control_features=CONTROL, models={k: dict(added_features=v[0], depth=v[1], iterations=v[2], l2_leaf_reg=v[3]) for k, v in MODELS.items()},
        learning_rate=.03, random_seed=24, month_balanced=True, candidate_weight=.5, min_training_rows=1000, min_training_months=18,
        feature_sha256=audit['feature_sha256'], reference=REFERENCE, source_receipts=original_audit['receipts'],
        population='same original 27600 stock-date predictions, same mature training rows for every new model; missing inputs remain NaN',
        source='historical daily bars through current close; no label or future-price input',
        evidence='fixed six candidates before scoring; deeper model changes capacity and regularization together; same-capacity feature contrasts provided')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []
    for h in [1, 3, 6]:
        source_path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in original_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == receipt['sha256']
        reference = pd.read_parquet(source_path); reference = reference[reference.model.eq('market_month_balanced')].copy(); reference['model'] = REFERENCE
        results = [reference]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            train = select_training(panel, h, date, None)
            weights = observation_weights(train, date, True, None)
            active = len(train) >= 1000 and train.date.nunique() >= 18
            template = base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date', 'instrument']], test[['date', 'instrument']])
            keys = test[['date', 'instrument']]; keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet', index=False)
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', keys)
            y = train[f'y_{h}'].to_numpy(); labels = classes(y)
            for name, (added, depth, iterations, regularization) in MODELS.items():
                prediction = template.copy(); prediction['model'] = name
                if active:
                    cols = CONTROL+added
                    model = CatBoostClassifier(loss_function='MultiClass', depth=depth, iterations=iterations,
                        learning_rate=.03, l2_leaf_reg=regularization, random_seed=24, thread_count=4,
                        verbose=False, allow_writing_files=False)
                    model.fit(train[cols].astype(float), labels, sample_weight=weights)
                    probabilities = np.zeros((len(test), 7))
                    probabilities[:, model.classes_.astype(int)] = model.predict_proba(test[cols].astype(float))
                    a, w = weighted_class_distribution(y, labels, probabilities, weights)
                    np.savez_compressed(CACHE/f'{h}_{date.date()}_{name}.npz', class_atoms=a[0], probabilities=probabilities)
                    a, w = combine_distributions([(ba, bw), (a, w)], [.5, .5])
                    stats = weighted_stats(a, w, template.actual); prediction[stats.columns] = stats.to_numpy()
                results.append(prediction)
                audits.append(dict(months=h, date=str(date.date()), model=name, training_rows=len(train),
                    training_months=train.date.nunique(), last_training_label=str(train[f'end_{h}'].max()),
                    total_weight=float(weights.sum()), test_rows=len(test), adjusted_rows=len(test) if active else 0))
            print(h, date.date(), 'finished', flush=True)
        pd.concat(results, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)


if __name__ == '__main__':
    run()
