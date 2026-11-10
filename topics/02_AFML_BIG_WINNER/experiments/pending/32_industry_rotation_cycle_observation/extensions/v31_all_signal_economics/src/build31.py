"""Freeze all observations and calculate forward outcomes independently of labels."""
import json
import numpy as np
import pandas as pd
from common31 import *


def build():
    freeze()
    features = pd.read_parquet(OLD / 'features.parquet')
    features = features[features.features_ready & features.date.between(START, END)].copy()
    daily = pd.read_parquet(OLD / 'daily_industries.parquet')
    indexes = {bm: pd.read_parquet(OLD / f'{bm}.parquet').close.sort_index() for bm in ['CSI300', 'CSI_ALL']}
    calendar = indexes['CSI_ALL'].index
    assert calendar.equals(indexes['CSI300'].index)
    calendar = pd.DatetimeIndex(calendar)
    paths = {key: g.sort_values('date') for key, g in daily.groupby(KEY)}
    rows = []
    checks = []
    for n, (key, obs) in enumerate(features.groupby(KEY)):
        path = paths[key]
        dates = pd.DatetimeIndex(path.date)
        nav = path.nav.to_numpy(float)
        market_i = calendar.get_indexer(dates)
        assert (market_i >= 0).all()
        local_lookup = {date: i for i, date in enumerate(dates)}
        lognav = pd.Series(np.log(nav), index=dates).diff()
        betas = {}
        for bm, index in indexes.items():
            market_r = np.log(index).diff().reindex(dates)
            betas[bm] = (lognav.rolling(252, min_periods=252).cov(market_r) /
                         market_r.rolling(252, min_periods=252).var()).replace([np.inf, -np.inf], np.nan)
        for date, at in obs.groupby('date'):
            signal_i = calendar.get_loc(date)
            entry_i = signal_i + 1
            entry_date = calendar[entry_i] if entry_i < len(calendar) else pd.NaT
            for months in [3, 6, 12]:
                target = entry_date + pd.DateOffset(months=months)
                terminal_i = calendar.searchsorted(target) if pd.notna(target) else len(calendar)
                terminal = calendar[terminal_i] if terminal_i < len(calendar) else pd.NaT
                why = 'OK'
                if pd.isna(terminal):
                    why = 'FUTURE_NOT_AVAILABLE'
                elif entry_date not in local_lookup or terminal not in local_lookup:
                    why = 'PRICE_BLOCK_OR_CLASSIFICATION_GAP'
                else:
                    lo, hi = local_lookup[entry_date], local_lookup[terminal]
                    if not np.array_equal(market_i[lo:hi+1], np.arange(entry_i, terminal_i+1)):
                        why = 'MISSING_INTERMEDIATE_PRICES'
                ret = mdd = np.nan
                if why == 'OK':
                    values = nav[lo:hi+1]
                    ret = values[-1] / values[0] - 1
                    mdd = np.min(values / np.maximum.accumulate(values) - 1)
                for bm, index in indexes.items():
                    market_ret = index.loc[terminal] / index.loc[entry_date] - 1 if pd.notna(terminal) and pd.notna(entry_date) else np.nan
                    beta = betas[bm].loc[date]
                    residual = np.log1p(ret) - beta * np.log1p(market_ret) if why == 'OK' and pd.notna(beta) else np.nan
                    for row_id in at.row_id:
                        rows.append(dict(row_id=row_id, months=months, benchmark=bm,
                            entry_date=entry_date, end_date=terminal, outcome_status=why,
                            industry_return=ret, benchmark_return=market_ret, excess_return=ret-market_ret,
                            max_drawdown=mdd, beta252=beta, beta_adjusted_log_return=residual))
        if n % 100 == 0:
            print('forward paths', n, 'outcome rows', len(rows), flush=True)
    outcomes = pd.DataFrame(rows)
    assert not outcomes.duplicated(['row_id', 'months', 'benchmark']).any()
    outcomes.to_parquet(CACHE / 'outcomes.parquet', index=False)
    features.to_parquet(CACHE / 'observations.parquet', index=False)
    outcomes.groupby(['months', 'benchmark', 'outcome_status']).size().rename('records').reset_index().to_csv(OUT / 'outcome_coverage.csv', index=False)
    refs = json.loads((EXT / 'v27_regime_threshold_review/outputs/frozen_policy.json').read_text())
    audit = json.loads((EXT / 'v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text())
    assert sha(OLD / 'daily_industries.parquet') == audit['daily_sha256']
    assert sha(OLD / 'stage_b_labels.parquet') == refs['labels_sha256']
    assert sha(OLD / 'daily_phases.parquet') == refs['phases_sha256']
    js(OUT / 'input_receipt.json', dict(
        source_hashes={str(p): sha(p) for p in [OLD / 'features.parquet', OLD / 'daily_industries.parquet',
            OLD / 'stage_b_labels.parquet', OLD / 'daily_phases.parquet', OLD / 'CSI300.parquet', OLD / 'CSI_ALL.parquet']},
        observations=len(features), outcomes=len(outcomes), latest_input=str(calendar.max()),
        outcomes_sha256=sha(CACHE / 'outcomes.parquet'), observations_sha256=sha(CACHE / 'observations.parquet')))
    print('forward outcomes complete', len(outcomes), flush=True)


if __name__ == '__main__':
    build()
