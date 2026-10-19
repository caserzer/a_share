"""R04: fixed-size historical peer distributions, no tree fitting or tuning."""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from run_price_pilot import OUT, ALPHAS, TECH, score


def run():
    dest = OUT / 'r04_peer_probe'
    dest.mkdir(exist_ok=True)
    panel = pd.read_parquet(OUT / 'local_cache/enriched_panel.parquet')
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    # Same common sample as R03. Robust scaling fit only on matured training rows.
    variants = {'peers_risk_size': ['vol63', 'log_cap'],
                'peers_valuation': ['vol63', 'log_cap', 'earnings_yield', 'book_yield'],
                'peers_fundamental': ['vol63', 'log_cap', 'earnings_yield', 'book_yield', 'roe', 'profit_growth'],
                'peers_macro': ['vol63', 'log_cap', 'earnings_yield', 'book_yield', 'credit_spread_3y', 'gov_3y']}
    frames, audits = [], []
    for h in [126, 252]:
        ycol, endcol = f'return{h}', f'label_end{h}'
        p = panel.dropna(subset=TECH + ['earnings_yield', 'book_yield', ycol, endcol])
        for quarter in pd.period_range('2021Q1', '2023Q4', freq='Q'):
            cutoff = quarter.start_time
            train = p[(p[endcol] < cutoff) & (p.date < cutoff)]
            test = p[p.date.dt.to_period('Q') == quarter]
            ytrain = train[ycol].to_numpy()
            globalq = np.quantile(ytrain, ALPHAS)
            predictions = {'expanding_empirical': np.tile(globalq, (len(test), 1))}
            for name, columns in variants.items():
                median = train[columns].median()
                scale = (train[columns].quantile(.75) - train[columns].quantile(.25)).replace(0, 1).fillna(1)
                x = ((train[columns].fillna(median).fillna(0) - median.fillna(0)) / scale).clip(-5, 5)
                z = ((test[columns].fillna(median).fillna(0) - median.fillna(0)) / scale).clip(-5, 5)
                nn = NearestNeighbors(n_neighbors=min(1000, len(train)), n_jobs=4).fit(x)
                indices = nn.kneighbors(z, return_distance=False)
                peer_q = np.quantile(ytrain[indices], ALPHAS, axis=1).T
                # Quantile shrinkage defines a new quantile function, NOT a CDF mixture.
                predictions[name] = .75 * peer_q + .25 * globalq
                months = train.date.to_numpy()[indices]
                counts = [len(np.unique(row)) for row in months]
                audits.append({'horizon': h, 'quarter': str(quarter), 'model': name,
                    'train_months': train.date.nunique(), 'median_peer_months': np.median(counts),
                    'min_peer_months': np.min(counts), 'train_rows': len(train), 'test_rows': len(test)})
            for name, q in predictions.items():
                r = test[['date', 'instrument', ycol]].rename(columns={ycol: 'actual'}).copy()
                r['horizon'], r['model'] = h, name
                r['quantile_loss'] = score(r.actual.to_numpy(), q)
                r['below_q05'] = r.actual.to_numpy() < q[:, 0]
                r['coverage90'] = (r.actual.to_numpy() >= q[:, 0]) & (r.actual.to_numpy() <= q[:, -1])
                r['width90'] = q[:, -1] - q[:, 0]
                for j, a in enumerate(ALPHAS):
                    r[f'q{int(a*100):02}'] = q[:, j]
                frames.append(r)
            print(f'{h} {quarter}', flush=True)
    predictions = pd.concat(frames, ignore_index=True)
    predictions.to_parquet(dest / 'predictions.parquet', index=False)
    metrics = ['quantile_loss', 'below_q05', 'coverage90', 'width90']
    monthly = predictions.groupby(['horizon', 'model', 'date'])[metrics].mean().reset_index()
    monthly.to_csv(dest / 'monthly_scores.csv', index=False)
    summary = monthly.groupby(['horizon', 'model'])[metrics].mean()
    summary.to_csv(dest / 'summary.csv')
    monthly.groupby(['horizon', 'model', monthly.date.dt.year])[metrics].mean().to_csv(dest / 'annual_scores.csv')
    pd.DataFrame(audits).to_csv(dest / 'peer_time_diversity.csv', index=False)
    (dest / 'run_spec.json').write_text(json.dumps({'variants': variants, 'neighbors': 1000,
        'quantile_shrinkage_to_unconditional': .25, 'scaling': 'training median and IQR, clip [-5,5]',
        'hypothesis': 'simple peers separate information value from flexible tree overfitting',
        'scope': '2021-2023 exploratory; same sample as R03; no parameter grid',
        'limitations': '1000 stock-month neighbors are NOT 1000 independent market states'}, indent=2) + '\n')
    print(summary.to_string())


if __name__ == '__main__':
    run()
