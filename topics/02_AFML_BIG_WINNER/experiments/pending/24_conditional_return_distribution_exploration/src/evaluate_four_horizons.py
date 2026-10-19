"""Probability-only evaluation, with time-block uncertainty and missing-label bounds."""
import json
import numpy as np
import pandas as pd
from run_four_horizons import DEST, BINS, BIN_NAMES
METRICS = ['brier','multiclass_brier','crps','below_q05','coverage90']


def block_interval(values, block, seed=24):
    a = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(a)
    starts = rng.integers(0, n, size=(2000, int(np.ceil(n/block))))
    indices = ((starts[:,:,None] + np.arange(block)) % n).reshape(2000,-1)[:,:n]
    return np.quantile(a[indices].mean(axis=1), [.025, .975])


def evaluate():
    files = [DEST / f'predictions_{h}m.parquet' for h in [1,3,6,12]]
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise RuntimeError('Incomplete horizons: ' + str(missing))
    predictions = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    scored = predictions[predictions.actual.notna()].copy()
    scored['observed_up'] = (scored.actual > 0).astype(float)
    scored['class'] = np.searchsorted(BINS, scored.actual, side='right')
    monthly = scored.groupby(['months','model','date'])[METRICS].mean().reset_index()
    monthly.to_csv(DEST / 'monthly_scores.csv', index=False)
    monthly.groupby(['months','model'])[METRICS].mean().to_csv(DEST / 'summary.csv')
    monthly.groupby(['months','model',monthly.date.dt.year])[METRICS].mean().to_csv(DEST / 'annual_scores.csv')
    comparisons = []
    for h, g in monthly.groupby('months'):
        for metric in ['brier','multiclass_brier','crps']:
            wide = g.pivot(index='date', columns='model', values=metric)
            for baseline in ['expanding_empirical','recent24_empirical']:
                for name in wide.columns:
                    if name == baseline:
                        continue
                    paired = (wide[name]-wide[baseline]).dropna()
                    lo, hi = block_interval(paired, h)
                    comparisons.append(dict(months=h, model=name, baseline=baseline, metric=metric,
                        difference=paired.mean(), lower95=lo, upper95=hi, months_scored=len(paired), block_months=h))
    pd.DataFrame(comparisons).to_csv(DEST / 'baseline_comparisons.csv', index=False)
    calibration = []
    for h, hdata in scored.groupby('months'):
        for model, g in hdata.groupby('model'):
            for event, pcol in [('up','p_up')] + [(name, f'p_{name}') for name in BIN_NAMES]:
                observed = g.observed_up if event == 'up' else (g['class'] == BIN_NAMES.index(event)).astype(float)
                work = g[['date',pcol]].assign(observed=observed, bucket=np.floor(g[pcol]*10).clip(upper=9))
                for bucket, b in work.groupby('bucket'):
                    # Ratio bootstrap by blocks of calendar months; missing-bin months remain zero weight.
                    all_dates = pd.DatetimeIndex(sorted(g.date.unique()))
                    agg = b.groupby('date').agg(n=(pcol,'size'), p=(pcol,'sum'), o=('observed','sum')).reindex(all_dates, fill_value=0)
                    rng = np.random.default_rng(24)
                    n = len(agg)
                    starts = rng.integers(0,n,size=(2000,int(np.ceil(n/h))))
                    idx = ((starts[:,:,None]+np.arange(h))%n).reshape(2000,-1)[:,:n]
                    den = agg.n.to_numpy()[idx].sum(axis=1)
                    obs = agg.o.to_numpy()[idx].sum(axis=1)
                    pred = agg.p.to_numpy()[idx].sum(axis=1)
                    valid = den > 0
                    lo, hi = np.quantile((obs[valid]-pred[valid])/den[valid],[.025,.975])
                    calibration.append(dict(months=h,model=model,event=event,bin=int(bucket),rows=len(b),
                        distinct_months=b.date.nunique(), predicted=b[pcol].mean(),observed=b.observed.mean(),
                        calibration_gap_lower95=lo,calibration_gap_upper95=hi,
                        evidence='sparse' if b.date.nunique()<max(12,2*h) or len(b)<200 else 'retrospective'))
    pd.DataFrame(calibration).to_csv(DEST / 'probability_calibration.csv', index=False)
    bounds=[]
    for (h,model),g in predictions[predictions.label_end.notna()].groupby(['months','model']):
        known=g.actual.notna()
        up=(g.actual[known]>0).sum()
        bounds.append(dict(months=h,model=model,mature_rows=len(g),missing_outcomes=int((~known).sum()),
            predicted_up=g.p_up.mean(),observed_up_lower=up/len(g),observed_up_upper=(up+(~known).sum())/len(g)))
    pd.DataFrame(bounds).to_csv(DEST/'missing_outcome_bounds.csv',index=False)
    stock = 'SH600000'
    latest = predictions.date.max()
    example = predictions[(predictions.instrument==stock)&(predictions.date==latest)]
    cols=['date','instrument','months','model','p_up','p_down','p_zero']+[f'p_{n}' for n in BIN_NAMES]+['q05','q50','q95']
    example[cols].to_json(DEST/'historical_probability_example.json',orient='records',date_format='iso',indent=2)
    print(monthly.groupby(['months','model'])[METRICS].mean().to_string())


if __name__ == '__main__':
    evaluate()
