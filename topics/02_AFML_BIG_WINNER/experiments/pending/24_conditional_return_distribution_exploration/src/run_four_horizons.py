"""R10: calendar-month probability prediction; no portfolio metrics."""
import json
import hashlib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.neighbors import NearestNeighbors
from prepare_panel import DATA, OUT, EP
from run_price_pilot import TECH
from enrich_panel import VALUATION, FINANCIAL, CREDIT
from run_holdout import GRID, TREE_ALPHA, distribution_stats
DEST = OUT / 'r10_four_horizons'
CACHE = OUT / 'local_cache/r10_distributions'
BINS = np.array([-.20, -.05, .05, .20])
BIN_NAMES = ['loss_over20', 'loss5_20', 'near_flat', 'gain5_20', 'gain_over20']


def calendar_targets(dates, months, calendar):
    targets = pd.DatetimeIndex([d + pd.DateOffset(months=months) for d in dates])
    idx = calendar.searchsorted(targets)
    ends = pd.Series(pd.NaT, index=np.arange(len(dates)), dtype='datetime64[ns]')
    ok = idx < len(calendar)
    ends.loc[ok] = calendar[idx[ok]].to_numpy()
    return targets, ends


def build_panel():
    panel = pd.read_parquet(OUT / 'local_cache/enriched_panel.parquet')
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA / 'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    parts = []
    for stock, g in panel.groupby('instrument', sort=True):
        g = g.copy().reset_index(drop=True)
        bars = pd.read_csv(DATA / f'raw/akshare/day/qfq/{stock}.csv', parse_dates=['date']).set_index('date')
        assert not bars.index.duplicated().any()
        price = bars.close.where(bars.close > 0)
        start = price.reindex(g.date).to_numpy()
        for h in [1, 3, 6, 12]:
            target, end = calendar_targets(g.date, h, calendar)
            g[f'target_{h}'], g[f'end_{h}'] = target, end
            g[f'y_{h}'] = price.reindex(pd.DatetimeIndex(end)).to_numpy() / start - 1
        parts.append(g)
    panel = pd.concat(parts, ignore_index=True).sort_values(['date', 'instrument'])
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    panel['financial_available'] = panel.roe.notna().astype(int)
    panel['valuation_available'] = panel.earnings_yield.notna().astype(int)
    panel = panel.replace([np.inf, -np.inf], np.nan)
    panel.to_parquet(OUT / 'local_cache/four_horizon_panel.parquet', index=False)
    return panel


def probability_stats(atoms, actual):
    s, y = np.asarray(atoms), np.asarray(actual)
    result = distribution_stats(s, y)
    result['p_down'], result['p_zero'] = (s < 0).mean(axis=1), (s == 0).mean(axis=1)
    classes = np.searchsorted(BINS, s, side='right')
    probs = np.stack([(classes == i).mean(axis=1) for i in range(5)], axis=1)
    for i, name in enumerate(BIN_NAMES):
        result[f'p_{name}'] = probs[:, i]
    labels = np.searchsorted(BINS, y, side='right')
    result['multiclass_brier'] = ((probs - np.eye(5)[labels])**2).sum(axis=1)
    result.loc[~np.isfinite(y), 'multiclass_brier'] = np.nan
    return result


def run(horizons):
    DEST.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    path = OUT / 'local_cache/four_horizon_panel.parquet'
    panel = pd.read_parquet(path) if path.exists() else build_panel()
    predictors = panel.dropna(subset=TECH + ['earnings_yield', 'book_yield']).copy()
    treecols = TECH + ['financial_available', 'valuation_available'] + VALUATION + FINANCIAL + CREDIT
    variants = {'peers_risk_size': ['vol63', 'log_cap'], 'peers_full': ['vol63', 'log_cap'] + VALUATION + FINANCIAL + CREDIT}
    for h in horizons:
        rows, audits, coverage = [], [], []
        for quarter in pd.period_range('2021Q1', '2026Q2', freq='Q'):
            train = predictors[(predictors[f'end_{h}'] < quarter.start_time) & predictors[f'y_{h}'].notna()]
            test = predictors[predictors.date.dt.to_period('Q') == quarter].copy().reset_index(drop=True)
            if test.empty:
                continue
            assert train[f'end_{h}'].max() < quarter.start_time
            yt = train[f'y_{h}'].to_numpy()
            glob = np.quantile(yt, GRID)
            recent = train[train.date >= quarter.start_time - pd.DateOffset(months=24)][f'y_{h}']
            preds = {'expanding_empirical': np.tile(glob, (len(test), 1)), 'recent24_empirical': np.tile(np.quantile(recent, GRID), (len(test), 1))}
            for name, cols in variants.items():
                median = train[cols].median().fillna(0)
                scale = (train[cols].quantile(.75) - train[cols].quantile(.25)).replace(0, 1).fillna(1)
                x = ((train[cols].fillna(median) - median) / scale).clip(-5, 5)
                z = ((test[cols].fillna(median) - median) / scale).clip(-5, 5)
                idx = NearestNeighbors(n_neighbors=min(1000, len(train)), n_jobs=4).fit(x).kneighbors(z, return_distance=False)
                preds[name] = .75 * np.quantile(yt[idx], GRID, axis=1).T + .25 * glob
            model = CatBoostRegressor(loss_function='MultiQuantile:alpha=' + ','.join(map(str, TREE_ALPHA)), iterations=200, depth=4, learning_rate=.04, random_seed=24, thread_count=4, verbose=False, allow_writing_files=False)
            model.fit(train[treecols], train[f'y_{h}'])
            raw = model.predict(test[treecols])
            preds['catboost_full'] = np.maximum(np.stack([np.interp(GRID, TREE_ALPHA, q) for q in np.sort(raw, axis=1)]), -1)
            audits.append(dict(months=h, quarter=str(quarter), training_rows=len(train), last_training_label=str(train[f'end_{h}'].max().date()), first_prediction=str(test.date.min().date()), predicted_rows=len(test), recent_rows=len(recent)))
            test[['date', 'instrument']].to_parquet(CACHE / f'{h}_{quarter}_keys.parquet', index=False)
            for name, atoms in preds.items():
                np.savez_compressed(CACHE / f'{h}_{quarter}_{name}.npz', atoms=atoms.astype(np.float32))
                r = test[['date', 'instrument', f'y_{h}', f'end_{h}', f'target_{h}']].rename(columns={f'y_{h}':'actual', f'end_{h}':'label_end', f'target_{h}':'target_date'})
                r = pd.concat([r, probability_stats(atoms, test[f'y_{h}'])], axis=1)
                r['model'], r['months'] = name, h
                rows.append(r)
            for date, g in test.groupby('date'):
                mature = g[f'end_{h}'].notna()
                coverage.append(dict(months=h, date=str(date.date()), predicted=len(g), mature=int(mature.sum()), missing_outcome=int((mature & g[f'y_{h}'].isna()).sum()), immature=int((~mature).sum())))
            print(f'R10 {h}m {quarter} train={len(train)} predicted={len(test)}', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST / f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST / f'fit_audit_{h}m.csv', index=False)
        pd.DataFrame(coverage).to_csv(DEST / f'coverage_{h}m.csv', index=False)
    (DEST / 'run_spec.json').write_text(json.dumps(dict(plan_sha256=hashlib.sha256((EP / 'notes/r10_probability_goal.md').read_bytes()).hexdigest(), horizons=[1,3,6,12], data_cutoff='2026-05-29', latest_prediction='2026-04-30', target='decision close to first market session on/after calendar-month target; qfq price proxy', bin_edges=BINS.tolist(), bin_boundary='left inclusive, right exclusive', evidence='retrospective walk-forward; not new untouched holdout', representation='200 equal-weight atoms'), indent=2)+'\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--months', type=int, nargs='+', default=[1,3,6,12], choices=[1,3,6,12])
    run(parser.parse_args().months)
