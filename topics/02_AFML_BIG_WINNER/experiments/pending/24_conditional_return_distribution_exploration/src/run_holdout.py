"""R05 preregistered historical validation with explicit finite distributions."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.neighbors import NearestNeighbors
from run_price_pilot import OUT, TECH
from enrich_panel import VALUATION, FINANCIAL, CREDIT

GRID = (np.arange(200) + .5) / 200
TREE_ALPHA = np.unique(np.r_[.01, .025, .05, np.arange(.10, .91, .05), .95, .975, .99])
VARIANTS = {
    'peers_risk_size': ['vol63', 'log_cap'],
    'peers_valuation': ['vol63', 'log_cap', 'earnings_yield', 'book_yield'],
    'peers_fundamental': ['vol63', 'log_cap', 'earnings_yield', 'book_yield', 'roe', 'profit_growth'],
    'peers_macro': ['vol63', 'log_cap', 'earnings_yield', 'book_yield', 'credit_spread_3y', 'gov_3y'],
}


def distribution_stats(samples, actual):
    """Exact metrics for equally weighted finite atoms; missing actual stays missing."""
    s = np.sort(np.asarray(samples), axis=1)
    n = s.shape[1]
    y = np.asarray(actual, dtype=float)
    crps = np.abs(s - y[:, None]).mean(axis=1) - (s * (2 * np.arange(1, n+1) - n - 1)).sum(axis=1) / n**2
    p = (s > 0).mean(axis=1)
    q05, q50, q95 = np.quantile(s, [.05, .5, .95], axis=1)
    missing = ~np.isfinite(y)
    stats = dict(mean=s.mean(axis=1), p_up=p, q05=q05, q50=q50, q95=q95,
                 es05=s[:, :max(1, int(n*.05))].mean(axis=1), crps=crps,
                 brier=(p - (y > 0))**2,
                 pit=((s < y[:, None]).mean(axis=1) + (s <= y[:, None]).mean(axis=1)) / 2,
                 below_q05=(y < q05).astype(float), coverage90=((y >= q05) & (y <= q95)).astype(float))
    for name in ['crps', 'brier', 'pit', 'below_q05', 'coverage90']:
        stats[name][missing] = np.nan
    return pd.DataFrame(stats)


def run(target='total'):
    excess = target == 'excess'
    dest = OUT / ('r08_excess_probe' if excess else 'r05_holdout')
    cache = OUT / 'local_cache' / ('r08_distributions' if excess else 'r05_distributions')
    dest.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    spec = OUT.parent / ('notes/r08_excess_return_probe.md' if excess else 'notes/r05_preregistered_validation.md')
    spec_hash = hashlib.sha256(spec.read_bytes()).hexdigest()
    panel = pd.read_parquet(OUT / 'local_cache/enriched_panel.parquet')
    if excess:
        for h in [126, 252]:
            panel[f'return{h}'] = panel[f'return{h}'] - panel[f'benchmark{h}']
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    panel['financial_available'] = panel.roe.notna().astype(int)
    panel['valuation_available'] = panel.earnings_yield.notna().astype(int)
    required = TECH + ['earnings_yield', 'book_yield']
    predictors = panel.dropna(subset=required).copy()
    treefeatures = TECH + ['financial_available', 'valuation_available'] + VALUATION + FINANCIAL + CREDIT
    rows, audits, missing = [], [], []
    cutoff = pd.Timestamp('2026-05-29')
    for h in [126, 252]:
        ycol, endcol = f'return{h}', f'label_end{h}'
        for quarter in pd.period_range('2021Q1' if excess else '2024Q1', '2026Q2', freq='Q'):
            train = predictors[(predictors[endcol] < quarter.start_time) & predictors[ycol].notna()]
            test = predictors[predictors.date.dt.to_period('Q') == quarter].copy().reset_index(drop=True)
            if test.empty:
                continue
            assert train[endcol].max() < quarter.start_time
            ytrain = train[ycol].to_numpy()
            globalq = np.quantile(ytrain, GRID)
            preds = {'expanding_empirical': np.tile(globalq, (len(test), 1))}
            for name, columns in VARIANTS.items():
                median = train[columns].median().fillna(0)
                scale = (train[columns].quantile(.75) - train[columns].quantile(.25)).replace(0, 1).fillna(1)
                x = ((train[columns].fillna(median) - median) / scale).clip(-5, 5)
                z = ((test[columns].fillna(median) - median) / scale).clip(-5, 5)
                indices = NearestNeighbors(n_neighbors=1000, n_jobs=4).fit(x).kneighbors(z, return_distance=False)
                preds[name] = .75 * np.quantile(ytrain[indices], GRID, axis=1).T + .25 * globalq
            model = CatBoostRegressor(loss_function='MultiQuantile:alpha=' + ','.join(map(str, TREE_ALPHA)),
                iterations=200, depth=4, learning_rate=.04, random_seed=24, thread_count=4,
                verbose=False, allow_writing_files=False)
            model.fit(train[treefeatures], train[ycol])
            raw = model.predict(test[treefeatures])
            sortedq = np.sort(raw, axis=1)
            tree_atoms = np.stack([np.interp(GRID, TREE_ALPHA, q) for q in sortedq])
            preds['catboost_full'] = tree_atoms if excess else np.maximum(tree_atoms, -1)
            audits.append({'horizon': h, 'quarter': str(quarter), 'training_rows': len(train),
                'training_months': train.date.nunique(), 'last_mature_label': str(train[endcol].max().date()),
                'predicted_rows': len(test), 'crossing_fraction': float((np.diff(raw, axis=1) < 0).any(axis=1).mean())})
            test[['date', 'instrument']].to_parquet(cache / f'{h}_{quarter}_keys.parquet', index=False)
            for name, s in preds.items():
                np.savez_compressed(cache / f'{h}_{quarter}_{name}.npz', atoms=s.astype(np.float32))
                r = test[['date', 'instrument', ycol, endcol, 'vol63', 'financial_report_date']].rename(
                    columns={ycol: 'actual', endcol: 'label_end'})
                r = pd.concat([r.reset_index(drop=True), distribution_stats(s, test[ycol])], axis=1)
                r['model'], r['horizon'] = name, h
                r['mature'] = r.label_end.notna() & (r.label_end <= cutoff)
                rows.append(r)
            for date, g in test.groupby('date'):
                mature = g[endcol].notna() & (g[endcol] <= cutoff)
                missing.append({'horizon': h, 'date': str(date.date()), 'prediction_rows': len(g),
                    'mature_rows': int(mature.sum()), 'mature_missing_outcomes': int((mature & g[ycol].isna()).sum()),
                    'immature_rows': int((~mature).sum())})
            print(f'{h} {quarter} predicted={len(test)} mature_train={len(train)}', flush=True)
    predictions = pd.concat(rows, ignore_index=True)
    predictions.to_parquet(dest / 'predictions.parquet', index=False)
    scored = predictions[predictions.mature & predictions.actual.notna()].copy()
    metrics = ['crps', 'brier', 'below_q05', 'coverage90']
    monthly = scored.groupby(['horizon', 'model', 'date'])[metrics].mean().reset_index()
    monthly.to_csv(dest / 'monthly_scores.csv', index=False)
    summary = monthly.groupby(['horizon', 'model'])[metrics].mean()
    summary.to_csv(dest / 'summary.csv')
    if excess:
        monthly['phase'] = np.where(monthly.date < '2024-01-01', 'exploration_2021_2023', 'posthoc_2024_plus')
        monthly.groupby(['phase', 'horizon', 'model'])[metrics].mean().to_csv(dest / 'phase_summary.csv')
    monthly.groupby(['horizon', 'model', monthly.date.dt.year])[metrics].mean().to_csv(dest / 'annual_scores.csv')
    scored['exchange'] = scored.instrument.str[:2]
    scored.groupby(['horizon', 'model', 'exchange', 'date'])[metrics].mean().groupby(
        ['horizon', 'model', 'exchange']).mean().to_csv(dest / 'exchange_scores.csv')
    calibration = scored.assign(probability_bin=np.floor(scored.p_up * 10).clip(upper=9),
                                observed_up=(scored.actual > 0).astype(float))
    calibration.groupby(['horizon', 'model', 'probability_bin']).agg(
        rows=('actual', 'size'), predicted_up=('p_up', 'mean'), observed_up=('observed_up', 'mean')).to_csv(dest / 'up_calibration.csv')
    pd.DataFrame(audits).to_csv(dest / 'fit_audit.csv', index=False)
    pd.DataFrame(missing).to_csv(dest / 'outcome_coverage.csv', index=False)
    (dest / 'run_spec.json').write_text(json.dumps({'preregistered_spec_sha256': spec_hash,
        'target': 'stock return minus CSI300 return; p_up means probability of outperformance' if excess else 'stock absolute price-proxy return',
        'evidence_class': 'post-holdout exploratory diagnostic' if excess else 'preregistered historical holdout',
        'grid': GRID.tolist(), 'tree_alpha': TREE_ALPHA.tolist(), 'variants': VARIANTS,
        'cutoff': str(cutoff.date()), 'representation': '200 equally weighted atoms; CRPS exact for this finite approximation',
        'tail_limit': 'empirical historical tails; tree endpoint-constant interpolation; ES model-dependent',
        'prediction_selection': 'current required features only; future outcome not used to select predictions'}, indent=2) + '\n')
    print(summary.to_string())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=['total', 'excess'], default='total')
    run(parser.parse_args().target)
