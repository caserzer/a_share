"""R03: same-sample information-group comparisons on exploration dates only."""
import json
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from run_price_pilot import OUT, ALPHAS, TECH, score
from enrich_panel import VALUATION, FINANCIAL, CREDIT


def run():
    dest = OUT / 'r03_information_probe'
    dest.mkdir(exist_ok=True)
    panel = pd.read_parquet(OUT / 'local_cache/enriched_panel.parquet')
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    # Availability can itself identify time/stock groups; give controls to every model.
    panel['financial_available'] = panel.roe.notna().astype(int)
    panel['valuation_available'] = panel.earnings_yield.notna().astype(int)
    control = TECH + ['financial_available', 'valuation_available']
    variants = {'technical': control, 'valuation': control + VALUATION,
                'financial': control + VALUATION + FINANCIAL,
                'full': control + VALUATION + FINANCIAL + CREDIT,
                'macro_only_increment': control + CREDIT}
    frames, audit = [], []
    for h in (126, 252):
        ycol, endcol = f'return{h}', f'label_end{h}'
        p = panel.dropna(subset=TECH + ['earnings_yield', 'book_yield', ycol, endcol]).copy()
        for quarter in pd.period_range('2021Q1', '2023Q4', freq='Q'):
            cutoff = quarter.start_time
            train = p[(p[endcol] < cutoff) & (p.date < cutoff)]
            test = p[p.date.dt.to_period('Q') == quarter]
            if len(train) < 2000 or test.empty:
                continue
            assert train[endcol].max() < cutoff
            record = {'horizon': h, 'quarter': str(quarter), 'train_rows': len(train), 'test_rows': len(test),
                      'last_training_label': str(train[endcol].max().date()),
                      'train_financial_fraction': float(train.financial_available.mean())}
            recent = train[train.date >= train.date.max() - pd.DateOffset(months=24)]
            predictions = {'expanding_empirical': np.tile(np.quantile(train[ycol], ALPHAS), (len(test), 1)),
                           'recent24m_empirical': np.tile(np.quantile(recent[ycol], ALPHAS), (len(test), 1))}
            for name, features in variants.items():
                model = CatBoostRegressor(loss_function='MultiQuantile:alpha=' + ','.join(map(str, ALPHAS)),
                    iterations=200, depth=4, learning_rate=.04, random_seed=24,
                    thread_count=4, verbose=False, allow_writing_files=False)
                model.fit(train[features], train[ycol])
                q = model.predict(test[features])
                record[name + '_crossing'] = float((np.diff(q, axis=1) < 0).any(axis=1).mean())
                predictions[name] = np.sort(q, axis=1)
            audit.append(record)
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
            print(f'{h} {quarter} train={len(train)} test={len(test)}', flush=True)
    predictions = pd.concat(frames, ignore_index=True)
    predictions.to_parquet(dest / 'predictions.parquet', index=False)
    metrics = ['quantile_loss', 'below_q05', 'coverage90', 'width90']
    monthly = predictions.groupby(['horizon', 'model', 'date'])[metrics].mean().reset_index()
    monthly.to_csv(dest / 'monthly_scores.csv', index=False)
    summary = monthly.groupby(['horizon', 'model'])[metrics].mean()
    summary.to_csv(dest / 'summary.csv')
    monthly.groupby(['horizon', 'model', monthly.date.dt.year])[metrics].mean().to_csv(dest / 'annual_scores.csv')
    pd.DataFrame(audit).to_csv(dest / 'fit_audit.csv', index=False)
    (dest / 'run_spec.json').write_text(json.dumps({'variants': variants,
        'scope': '2021-2023 exploratory; 2024+ unscored',
        'same_sample': 'all TECH plus earnings/book yield and mature outcome required for every variant',
        'financial_timing': 'strictly after max notice/update', 'catboost': {'iterations': 200, 'depth': 4, 'seed': 24},
        'limitations': ['legacy stock selection bias', 'qfq return proxy', 'no PIT industry controls',
                        'vendor valuation original vintage unverified', 'conservatively stale financials']}, indent=2) + '\n')
    print(summary.to_string())


if __name__ == '__main__':
    run()
