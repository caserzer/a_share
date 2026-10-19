"""R17: model market class frequencies without treating stocks as independent markets."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from build_market_breadth import DEST, FEATURES, PRICE, MACRO, BREADTH
from build_improvement_features import FEATURE_PANEL
from run_improvement_round1 import normalize_features
from run_four_horizons import GRID, probability_stats
from run_direct_probability import weighted_stats, classes
from run_prequential_search import load_distribution
from prepare_panel import OUT


def month_class_frequencies(train, h):
    d = train[['date', f'y_{h}']].copy()
    d['class'] = classes(d[f'y_{h}'].to_numpy())
    counts = pd.crosstab(d.date, d['class']).reindex(columns=range(7), fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0)


def forecast_market_classes(features, frequencies, date, columns):
    train = features.loc[frequencies.index]
    x, z = normalize_features(train, features.loc[[date]], columns)
    # Seven fractional observations per month; total sample weight of every month is one.
    xx = np.repeat(x.to_numpy(), 7, axis=0)
    yy = np.tile(np.arange(7), len(x))
    weight = frequencies.to_numpy().ravel()
    keep = weight > 0
    if len(np.unique(yy[keep])) < 2:
        return frequencies.mean().to_numpy()
    model = LogisticRegression(C=.3, max_iter=1000, solver='lbfgs')
    model.fit(xx[keep], yy[keep], sample_weight=weight[keep])
    if model.n_iter_.max() >= model.max_iter:
        raise RuntimeError('Market class fit did not converge')
    p = np.zeros(7)
    p[model.classes_.astype(int)] = model.predict_proba(z.to_numpy())[0]
    return p


def reweight_market(atoms, weights, target, shrink):
    c = classes(atoms)
    current = np.array([(weights * (c == k)).sum(axis=1).mean() for k in range(7)])
    ratios = np.divide(target, current, out=np.zeros(7), where=current > 0)
    updated = weights * ratios[c]
    sums = updated.sum(axis=1, keepdims=True)
    updated = np.divide(updated, sums, out=weights.copy(), where=sums > 0)
    return shrink * weights + (1 - shrink) * updated


def run():
    DEST.mkdir(exist_ok=True)
    panel = pd.read_parquet(FEATURE_PANEL)
    panel = panel[panel.common_eligible]
    market = pd.read_parquet(FEATURES)
    experiments = {'macro_price_adjustment': PRICE,
                   'macro_credit_valuation_adjustment': PRICE + MACRO,
                   'macro_breadth_adjustment': PRICE + MACRO + BREADTH}
    audits, macro_forecasts = [], []
    cache = OUT / 'local_cache/r15_distributions'
    for h in [1, 3, 6]:
        rows = []
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            train = panel[(panel[f'end_{h}'] < date) & panel[f'y_{h}'].notna()]
            freq = month_class_frequencies(train, h)
            atoms, weights = load_distribution(cache, h, date, 'B', test[['date', 'instrument']])
            template = test[['date', 'instrument', f'end_{h}', f'target_{h}', f'y_{h}']].rename(
                columns={f'end_{h}': 'label_end', f'target_{h}': 'target_date', f'y_{h}': 'actual'})
            for name, cols in experiments.items():
                target = forecast_market_classes(market, freq, date, cols)
                macro_forecasts.append(dict(months=h, date=str(date.date()), model=name,
                    **{f'prob{k}': float(p) for k, p in enumerate(target)}))
                cases = [(name, .5)]
                if name == 'macro_breadth_adjustment':
                    cases.append(('macro_breadth_full_adjustment', 0.))
                for model, shrink in cases:
                    w = reweight_market(atoms, weights, target, shrink)
                    r = pd.concat([template.copy(), weighted_stats(atoms, w, template.actual)], axis=1)
                    r['months'], r['model'] = h, model
                    rows.append(r)
            # Same risk/size peers, plus just the state features; same rows and labels.
            peercols = ['vol63', 'log_cap', 'breadth21', 'breadth63', 'above_ma20', 'dispersion21']
            x = train[['vol63', 'log_cap', 'date']].join(market[BREADTH], on='date')
            z = test[['vol63', 'log_cap', 'date']].join(market[BREADTH], on='date')
            xx, zz = normalize_features(x, z, peercols)
            ix = NearestNeighbors(n_neighbors=min(1000, len(train)), n_jobs=1).fit(xx).kneighbors(zz, return_distance=False)
            y = train[f'y_{h}'].to_numpy()
            peer_atoms = .75 * np.quantile(y[ix], GRID, axis=1).T + .25 * np.quantile(y, GRID)
            r = pd.concat([template.copy(), probability_stats(peer_atoms, template.actual)], axis=1)
            r['months'], r['model'] = h, 'breadth_peer_distribution'
            rows.append(r)
            assert train[f'end_{h}'].max() < date
            audits.append(dict(months=h, date=str(date.date()), training_rows=len(train), training_months=len(freq),
                               last_training_label=str(train[f'end_{h}'].max()), test_rows=len(test)))
            print(h, date.date(), len(freq), flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST / f'predictions_{h}m.parquet', index=False)
    pd.DataFrame(audits).to_csv(DEST / 'fit_audit.csv', index=False)
    pd.DataFrame(macro_forecasts).to_csv(DEST / 'market_class_forecasts.csv', index=False)
    (DEST / 'spec.json').write_text(json.dumps(dict(experiments=experiments, ridge_C=.3, horizons=[1, 3, 6],
        training='each matured origin month has total multinomial weight one',
        base_distribution='frozen R15 B, class likelihood reweighting, half baseline unless full_adjustment',
        support='reweighting preserves atom support; cannot create absent class mass',
        evidence='retrospective repeated exploration; unchanged frozen R16 target contract'), indent=2) + '\n')


if __name__ == '__main__':
    run()
