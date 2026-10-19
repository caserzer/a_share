"""R01 exploratory 2021-2023 only. Keeps 2024+ unread by model evaluation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

EP = Path(__file__).resolve().parents[1]
OUT = EP / 'outputs'
ALPHAS = np.array([.05, .10, .25, .50, .75, .90, .95])
BASE = ['log_cap', 'vol63', 'market_mom126', 'market_vol63', 'board']
TECH = BASE + ['mom21', 'mom63', 'mom126', 'mom252', 'vol21', 'turnover21', 'log_money21', 'drawdown252']


def score(y, q):
    errors = y[:, None] - q
    loss = np.maximum(ALPHAS * errors, (ALPHAS - 1) * errors)
    # Finite-quantile score only: does NOT integrate or invent unobserved tails.
    return loss.mean(axis=1)


def run():
    dest = OUT / 'r01_price_pilot'
    dest.mkdir(exist_ok=True)
    panel = pd.read_parquet(OUT / 'local_cache/monthly_panel.parquet')
    panel['board'] = (panel.board_bucket == 'chinext').astype(int)
    # Source uses chinext or chinext_board? Derive from exchange code, unambiguous.
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    panel = panel.replace([np.inf, -np.inf], np.nan)
    records, fits = [], []
    for horizon in (126, 252):
        ycol, endcol = f'return{horizon}', f'label_end{horizon}'
        eligible = panel.dropna(subset=TECH + [ycol, endcol])
        for quarter in pd.period_range('2021Q1', '2023Q4', freq='Q'):
            cutoff = quarter.start_time
            train = eligible[(eligible[endcol] < cutoff) & (eligible.date < cutoff)]
            test = eligible[eligible.date.dt.to_period('Q') == quarter]
            if train.empty or test.empty:
                continue
            assert train[endcol].max() < test.date.min()
            fits.append({'horizon': horizon, 'quarter': str(quarter), 'train_rows': len(train),
                         'train_last_label': str(train[endcol].max().date()), 'test_rows': len(test)})
            predictions = {'unconditional': np.tile(np.quantile(train[ycol], ALPHAS), (len(test), 1))}
            edges = np.quantile(train.vol63, [1/3, 2/3])
            trainbucket = np.searchsorted(edges, train.vol63) + 3 * (train.market_mom126.to_numpy() > 0)
            testbucket = np.searchsorted(edges, test.vol63) + 3 * (test.market_mom126.to_numpy() > 0)
            conditional = predictions['unconditional'].copy()
            for bucket in range(6):
                sample = train.loc[trainbucket == bucket, ycol]
                if len(sample) >= 200:
                    conditional[testbucket == bucket] = np.quantile(sample, ALPHAS)
            predictions['conditional_empirical'] = conditional
            for name, features in [('catboost_base', BASE), ('catboost_technical', TECH)]:
                model = CatBoostRegressor(loss_function='MultiQuantile:alpha=' + ','.join(map(str, ALPHAS)),
                    iterations=200, depth=4, learning_rate=.04, random_seed=24,
                    thread_count=4, verbose=False, allow_writing_files=False)
                model.fit(train[features], train[ycol])
                raw = model.predict(test[features])
                fits[-1][name + '_crossing_fraction'] = float((np.diff(raw, axis=1) < 0).any(axis=1).mean())
                predictions[name] = np.sort(raw, axis=1)
            for name, q in predictions.items():
                r = test[['date', 'instrument', ycol]].rename(columns={ycol: 'actual'}).copy()
                r['horizon'], r['model'] = horizon, name
                r['quantile_loss'] = score(r.actual.to_numpy(), q)
                r['below_q05'] = r.actual.to_numpy() < q[:, 0]
                r['below_q50'] = r.actual.to_numpy() < q[:, 3]
                r['coverage90'] = (r.actual.to_numpy() >= q[:, 0]) & (r.actual.to_numpy() <= q[:, -1])
                r['width90'] = q[:, -1] - q[:, 0]
                for j, a in enumerate(ALPHAS):
                    r[f'q{int(a*100):02}'] = q[:, j]
                records.append(r)
            print(f'{horizon} {quarter} train={len(train)} test={len(test)}', flush=True)
    predictions = pd.concat(records, ignore_index=True)
    predictions.to_parquet(dest / 'predictions.parquet', index=False)
    metrics = ['quantile_loss', 'below_q05', 'below_q50', 'coverage90', 'width90']
    monthly = predictions.groupby(['horizon', 'model', 'date'])[metrics].mean().reset_index()
    monthly.to_csv(dest / 'monthly_scores.csv', index=False)
    annual = monthly.groupby(['horizon', 'model', monthly.date.dt.year])[metrics].mean()
    annual.to_csv(dest / 'annual_scores.csv')
    summary = monthly.groupby(['horizon', 'model'])[metrics].mean()
    summary.to_csv(dest / 'summary.csv')
    pd.DataFrame(fits).to_csv(dest / 'fit_audit.csv', index=False)
    (dest / 'run_spec.json').write_text(json.dumps({
        'scope': 'price proxy diagnostic; no valuation/fundamentals/credit; biased legacy universe',
        'evaluation': '2021-2023 exploration only; quarterly refit, month-end predictions',
        'label_maturity': 'strictly before quarter start', 'alphas': ALPHAS.tolist(),
        'base_features': BASE, 'technical_features': TECH, 'iterations': 200,
        'depth': 4, 'learning_rate': .04, 'seed': 24,
        'metric': 'mean seven-quantile pinball loss, month equally weighted; NOT full CRPS',
        'crossing_correction': 'sort predicted quantiles',
    }, indent=2) + '\n')
    print(summary.to_string())


if __name__ == '__main__':
    run()
