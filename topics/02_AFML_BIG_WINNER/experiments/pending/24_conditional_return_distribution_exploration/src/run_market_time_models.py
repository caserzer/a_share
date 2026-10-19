"""R21 market context and origin-month weighting, fixed before scoring."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import OUT
from build_earnings_revisions import PANEL as SOURCE_PANEL, DEST as SOURCE
from build_market_breadth import FEATURES as MARKET_PANEL, PRICE, MACRO, BREADTH
from run_earnings_revisions import ALL_EARNINGS, REVISION_COLS
from run_improvement_round1 import class_distribution
from run_direct_probability import classes, weighted_stats
from run_prequential_search import load_distribution, combine_distributions

DEST = OUT/'r21_market_time_models'
CACHE = OUT/'local_cache/r21_class_distributions'
STOCK = ALL_EARNINGS + REVISION_COLS
MARKET_SOURCE_COLS = PRICE + MACRO[2:] + BREADTH
MARKET = ['state_'+c for c in MARKET_SOURCE_COLS]
REFERENCE = 'r20_full_revision_reference'
# features, training window in origin months, month balance, decay half-life, new weight
MODELS = {
    'market_rows': (True, None, False, None, .5),
    'market_month_balanced': (True, None, True, None, .5),
    'market_window36': (True, 36, True, None, .5),
    'market_decay24': (True, None, True, 24, .5),
    'market_decay24_unmixed': (True, None, True, 24, 1.),
    'window36_without_market': (False, 36, True, None, .5),
}


def month_age(dates, date):
    return (date.year*12+date.month) - (dates.dt.year*12+dates.dt.month)


def select_training(panel, horizon, date, window):
    valid = panel[f'y_{horizon}'].notna() & (panel[f'end_{horizon}'] < date) & (panel.date < date)
    if window is not None:
        valid &= month_age(panel.date, date).le(window)
    return panel[valid]


def observation_weights(train, date, balanced, half_life):
    if not balanced:
        assert half_life is None
        return np.ones(len(train))
    counts = train.groupby('date').date.transform('size').to_numpy()
    weight = 1/counts
    if half_life is not None:
        weight *= np.exp2(-month_age(train.date, date).to_numpy()/half_life)
    # Common scale preserves the classifier's regularization relative to row baseline.
    return weight * (len(weight)/weight.sum())


def weighted_class_distribution(y, labels, probabilities, weights):
    grid = (np.arange(32)+.5)/32
    placeholders = [-.3, -.1, -.025, 0., .025, .1, .3]
    atoms = []
    for k in range(7):
        mask = labels == k; values = y[mask]; w = weights[mask]
        if len(values):
            order = np.argsort(values, kind='stable'); values = values[order]; w = w[order]
            centers = (np.cumsum(w)-.5*w)/w.sum()
            atoms.append(np.interp(grid, centers, values))
        else:
            atoms.append(np.full(32, placeholders[k]))
    return np.tile(np.concatenate(atoms), (len(probabilities), 1)), np.repeat(probabilities/32, 32, axis=1)


def load_panel():
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    assert hashlib.sha256(SOURCE_PANEL.read_bytes()).hexdigest() == source_audit['feature_sha256']
    panel = pd.read_parquet(SOURCE_PANEL); panel = panel[panel.common_eligible]
    market = pd.read_parquet(MARKET_PANEL)[MARKET_SOURCE_COLS].rename(columns=lambda x: 'state_'+x)
    assert market.index.is_unique and set(panel.date).issubset(set(market.index))
    panel = panel.join(market, on='date', validate='many_to_one')
    assert not any(c.startswith(('y_', 'end_', 'target_')) for c in STOCK+MARKET)
    return panel


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    panel = load_panel()
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    spec = dict(models={k: dict(market=v[0], window=v[1], month_balanced=v[2], half_life=v[3], candidate_weight=v[4]) for k, v in MODELS.items()},
        stock_features=STOCK, market_features=MARKET, min_training_rows=1000, min_training_months=18,
        source_panel_sha256=hashlib.sha256(SOURCE_PANEL.read_bytes()).hexdigest(),
        market_panel_sha256=hashlib.sha256(MARKET_PANEL.read_bytes()).hexdigest(),
        source_prediction_receipts=source_audit['receipts'], reference=REFERENCE,
        model=dict(iterations=100, depth=2, learning_rate=.03, l2_leaf_reg=20, random_seed=24),
        weighting='origin month totals equal or decay with a fixed 24-month half-life; mean row weight normalized to one; same weights used within outcome classes',
        market_population='historical 500-stock research pool, not full A-share breadth',
        evidence='fixed candidates before scoring; repeated retrospective exploration on original population, not independent validation')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    ref_fit = pd.read_csv(SOURCE/'fit_audit.csv'); ref_fit = ref_fit[ref_fit.model.eq('all_with_revisions')].copy()
    ref_fit['model'] = REFERENCE; audits = ref_fit.to_dict('records')
    for h in [1, 3, 6]:
        ref_path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(ref_path.read_bytes()).hexdigest() == receipt['sha256']
        reference = pd.read_parquet(ref_path); reference = reference[reference.model.eq('all_with_revisions')].copy(); reference['model'] = REFERENCE
        results = [reference]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            test = test.reset_index(drop=True); template = base[base.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(template[['date', 'instrument']], test[['date', 'instrument']])
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', test[['date', 'instrument']])
            fitted = {}; stamp = str(date.date())
            test[['date', 'instrument']].to_parquet(CACHE/f'{h}_{stamp}_keys.parquet', index=False)
            for name, (market, window, balanced, half_life, alpha) in MODELS.items():
                train = select_training(panel, h, date, window)
                months = train.date.nunique(); active = len(train) >= 1000 and months >= 18
                prediction = template.copy(); prediction['model'] = name
                weights = observation_weights(train, date, balanced, half_life)
                month_weight = pd.Series(weights, index=train.date).groupby(level=0).sum()
                effective_months = month_weight.sum()**2/(month_weight**2).sum()
                if active:
                    key = (market, window, balanced, half_life)
                    cols = STOCK + MARKET if market else STOCK
                    if key not in fitted:
                        labels = classes(train[f'y_{h}'].to_numpy())
                        model = CatBoostClassifier(loss_function='MultiClass', iterations=100, depth=2, learning_rate=.03,
                            l2_leaf_reg=20, random_seed=24, thread_count=4, verbose=False, allow_writing_files=False)
                        kwargs = dict(sample_weight=weights) if balanced else {}
                        model.fit(train[cols].astype(float), labels, **kwargs)
                        probabilities = np.zeros((len(test), 7))
                        probabilities[:, model.classes_.astype(int)] = model.predict_proba(test[cols].astype(float))
                        args = (train[f'y_{h}'].to_numpy(), labels, probabilities)
                        fitted[key] = weighted_class_distribution(*args, weights) if balanced else class_distribution(*args)
                        np.savez_compressed(CACHE/f'{h}_{stamp}_{name}.npz', class_atoms=fitted[key][0][0], probabilities=probabilities)
                    a, w = fitted[key]
                    if alpha < 1:
                        a, w = combine_distributions([(ba, bw), (a, w)], [1-alpha, alpha])
                    stats = weighted_stats(a, w, template.actual); prediction[stats.columns] = stats.to_numpy()
                results.append(prediction)
                audits.append(dict(months=h, date=stamp, model=name, training_rows=len(train), training_months=months,
                    first_training_origin=str(train.date.min()), last_training_origin=str(train.date.max()),
                    last_training_label=str(train[f'end_{h}'].max()), effective_market_months=effective_months,
                    min_row_weight=float(weights.min()), max_row_weight=float(weights.max()), total_weight=float(weights.sum()),
                    test_rows=len(test), adjusted_rows=len(test) if active else 0))
            print(h, stamp, 'finished', flush=True)
        pd.concat(results, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)


if __name__ == '__main__':
    run()
