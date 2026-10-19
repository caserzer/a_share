"""R02: diagnose stale distributions using only matured past outcomes."""
import json
import numpy as np
import pandas as pd
from run_price_pilot import OUT, ALPHAS, TECH, score


def run():
    dest = OUT / 'r02_calibration_probe'
    dest.mkdir(exist_ok=True)
    panel = pd.read_parquet(OUT / 'local_cache/monthly_panel.parquet')
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    old = pd.read_parquet(OUT / 'r01_price_pilot/predictions.parquet')
    qcols = [f'q{int(a*100):02}' for a in ALPHAS]
    rows, audit = [], []
    for horizon in (126, 252):
        endcol, ycol = f'label_end{horizon}', f'return{horizon}'
        p = panel.replace([np.inf, -np.inf], np.nan).dropna(subset=TECH + [endcol, ycol])
        predicted = old[(old.horizon == horizon) & (old.model == 'catboost_technical')].merge(
            p[['date', 'instrument', endcol]], on=['date', 'instrument'], validate='one_to_one')
        for date, target in predicted.groupby('date'):
            calibration = predicted[(predicted[endcol] < date) & (predicted.date < date)].copy()
            dates = sorted(calibration.date.unique())[-12:]
            if len(dates) < 6:
                continue
            calibration = calibration[calibration.date.isin(dates)]
            assert calibration[endcol].max() < date
            adjustment = np.array([np.quantile(calibration.actual - calibration[col], a)
                                   for col, a in zip(qcols, ALPHAS)])
            corrected = np.sort(target[qcols].to_numpy() + adjustment, axis=1)
            # The only physically imposed bound is -100% for unlevered price returns.
            corrected = np.maximum(corrected, -1)
            mature = p[(p[endcol] < date) & (p.date < date)]
            recent = mature[mature.date >= mature.date.max() - pd.DateOffset(months=24)]
            predictions = {'calibrated_technical': corrected,
                           'recent24m_empirical': np.tile(np.quantile(recent[ycol], ALPHAS), (len(target), 1)),
                           'expanding_empirical_monthly': np.tile(np.quantile(mature[ycol], ALPHAS), (len(target), 1)),
                           'technical_original': target[qcols].to_numpy()}
            audit.append({'horizon': horizon, 'date': str(date.date()), 'calibration_months': len(dates),
                          'calibration_rows': len(calibration), 'last_mature_label': str(calibration[endcol].max().date()),
                          'recent_train_rows': len(recent), 'q05_adjustment': adjustment[0]})
            for name, q in predictions.items():
                r = target[['date', 'instrument', 'actual']].copy()
                r['model'], r['horizon'] = name, horizon
                r['quantile_loss'] = score(r.actual.to_numpy(), q)
                r['below_q05'] = r.actual.to_numpy() < q[:, 0]
                r['coverage90'] = (r.actual.to_numpy() >= q[:, 0]) & (r.actual.to_numpy() <= q[:, -1])
                r['width90'] = q[:, -1] - q[:, 0]
                for j, col in enumerate(qcols):
                    r[col] = q[:, j]
                rows.append(r)
    predictions = pd.concat(rows, ignore_index=True)
    predictions.to_parquet(dest / 'predictions.parquet', index=False)
    metrics = ['quantile_loss', 'below_q05', 'coverage90', 'width90']
    monthly = predictions.groupby(['horizon', 'model', 'date'])[metrics].mean().reset_index()
    monthly.to_csv(dest / 'monthly_scores.csv', index=False)
    summary = monthly.groupby(['horizon', 'model'])[metrics].mean()
    summary.to_csv(dest / 'summary.csv')
    pd.DataFrame(audit).to_csv(dest / 'calibration_audit.csv', index=False)
    (dest / 'run_spec.json').write_text(json.dumps({
        'hypothesis': 'past out-of-sample residual calibration or recent history repairs downside undercoverage',
        'calibration': 'last up to 12 prediction months with matured labels; minimum 6 distinct months',
        'comparison': 'identical eligible targets for all four variants; no 2024+ evaluation',
        'limitation': 'stock-level residual quantiles do not grant independent observations or formal coverage guarantees',
        'status': 'post-R01 exploratory diagnostic, not independent confirmation',
    }, indent=2) + '\n')
    print(summary.to_string())


if __name__ == '__main__':
    run()
