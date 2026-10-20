"""D0 preservation and separate D1 quote-recovery/label-coverage audit; no scoring."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
TOPIC = EP.parents[2]
EP27 = EP.parent / '27_hierarchical_tail_risk_attribution'
OUT = EP / 'outputs'
CACHE = OUT / 'local_cache'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write(path, record):
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str, allow_nan=False) + '\n')


def bounds(frame):
    mature = frame[frame.label_end.notna()]
    known = mature.actual.notna()
    events = int(mature.loc[known, 'actual'].lt(-.2).sum())
    n = len(mature)
    missing = int((~known).sum())
    return dict(origins=len(frame), mature=n, known=int(known.sum()), missing=missing, events=events,
                known_rate=events / known.sum() if known.any() else None,
                rate_lower=events / n if n else None, rate_upper=(events + missing) / n if n else None)


def main():
    assert not (OUT / 'manifests/preregistration.json').exists(), 'audit precedes frozen model scoring'
    prior = json.loads((OUT / 'manifests/prior_preservation.json').read_text())
    assert all(sha(EP.parent / k) == v for k, v in prior.items())
    source = []
    def register(path):
        source.append(dict(path=str(path.relative_to(TOPIC)), sha256=sha(path), bytes=path.stat().st_size))
    path = EP27 / 'outputs/local_cache/panel.parquet'
    register(path)
    d0 = pd.read_parquet(path).sort_values(['date', 'instrument']).reset_index(drop=True)
    d0.to_parquet(CACHE / 'd0_panel.parquet', index=False)
    calpath = TOPIC / 'data/qlib/cn_data_pit_largecap/calendars/day.txt'
    register(calpath)
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calpath, header=None)[0]))
    # Include the 2017 history used for feature formation, even though D0 eligibility starts in 2018.
    dates = pd.DatetimeIndex(pd.Series(calendar).groupby(calendar.to_period('M')).max())
    dates = dates[dates <= d0.date.max()]
    meta_path = TOPIC / 'data/raw/akshare/status/instrument_metadata_target_universe.csv'
    register(meta_path)
    meta = pd.read_csv(meta_path, parse_dates=['listing_date', 'delist_date'])
    meta = meta[(meta.listing_date <= dates.max()) & (meta.delist_date.isna() | (meta.delist_date > dates.min()))].copy()
    meta = meta.sort_values('instrument').reset_index(drop=True)
    stocks = meta.instrument.tolist()
    close = np.full((len(calendar), len(stocks)), np.nan)
    turnover = np.full_like(close, np.nan)
    rows, quality = [], []
    target = dates + pd.DateOffset(months=6)
    idx = calendar.searchsorted(target)
    ends = np.full(len(dates), np.datetime64('NaT'), dtype='datetime64[ns]')
    ends[idx < len(calendar)] = calendar[idx[idx < len(calendar)]]
    start_ix = calendar.get_indexer(dates)
    for j, row in enumerate(meta.itertuples()):
        old = TOPIC / f'data/raw/akshare/day/qfq/{row.instrument}.csv'
        recovered = CACHE / f'recovered_prices/{row.instrument}_qfq.parquet'
        kind, invalid = 'missing', 0
        if old.exists():
            register(old)
            f = pd.read_csv(old, usecols=['date', 'close', 'turnover_rate'], parse_dates=['date'])
            kind = 'EP27_quote_source'
        elif recovered.exists():
            register(recovered)
            f = pd.read_parquet(recovered)[['date', 'qfq_close']].rename(columns={'qfq_close': 'close'})
            f['turnover_rate'] = np.nan
            kind = 'recovered_retrospective_quote'
        else:
            f = pd.DataFrame(columns=['date', 'close', 'turnover_rate'])
        assert not f.date.duplicated().any()
        invalid = int((~f.date.isin(calendar)).sum())
        f = f[f.date.isin(calendar)].set_index('date').sort_index()
        listed_daily = (calendar >= row.listing_date) & (True if pd.isna(row.delist_date) else calendar < row.delist_date)
        values = pd.to_numeric(f.close).reindex(calendar).to_numpy(float)
        values[(values <= 0) | ~listed_daily] = np.nan
        close[:, j] = values
        turn = pd.to_numeric(f.turnover_rate).reindex(calendar).to_numpy(float)
        turn[(turn < 0) | ~listed_daily] = np.nan
        turnover[:, j] = turn
        start = values[start_ix]
        finish = np.full(len(dates), np.nan)
        finish[idx < len(calendar)] = values[idx[idx < len(calendar)]]
        outcome = finish / start - 1
        listed_month = (dates >= row.listing_date) & (True if pd.isna(row.delist_date) else dates < row.delist_date)
        for k in np.flatnonzero(listed_month):
            rows.append(dict(date=dates[k], instrument=row.instrument, label_end=ends[k], actual=outcome[k],
                             start_quote=bool(np.isfinite(start[k])), source=kind,
                             is_delisted=bool(row.is_delisted), exchange=row.exchange))
        quality.append(dict(instrument=row.instrument, source=kind, is_delisted=bool(row.is_delisted),
                            invalid_calendar_rows_quarantined=invalid, valid_daily_quotes=int(np.isfinite(values).sum()),
                            listed_origins=int(listed_month.sum()), quoted_origins=int(np.isfinite(start[listed_month]).sum())))
        if j % 600 == 0:
            print(f'quote audit {j}/{len(meta)}', flush=True)
    np.savez_compressed(CACHE / 'daily_prices.npz', close=close, turnover=turnover)
    write(CACHE / 'daily_axes.json', dict(dates=[str(d.date()) for d in calendar], instruments=stocks))
    d1 = pd.DataFrame(rows)
    d1.to_parquet(CACHE / 'd1_label_census.parquet', index=False)
    quality = pd.DataFrame(quality)
    quality.to_csv(OUT / 'audits/quote_coverage.csv', index=False)
    test = d1[d1.date >= '2021-01-01']
    subsets = {'D1_all_listed_in_metadata': test, 'D1_quoted_origin': test[test.start_quote],
               'D1_recovered_quoted': test[test.start_quote & test.source.eq('recovered_retrospective_quote')],
               'D1_old_source_quoted': test[test.start_quote & test.source.eq('EP27_quote_source')],
               'D1_delisted_quoted': test[test.start_quote & test.is_delisted]}
    records = [dict(population=k, **bounds(v)) for k, v in subsets.items()]
    d0test = d0[d0.date >= '2021-01-01'].rename(columns={'end_6': 'label_end', 'y_6': 'actual'})
    records.append(dict(population='D0_fixed_EP27', **bounds(d0test)))
    pd.DataFrame(records).to_csv(OUT / 'audits/population_event_bounds.csv', index=False)
    months = []
    for name, frame in subsets.items():
        for date, g in frame.groupby('date'):
            months.append(dict(population=name, date=date, **bounds(g)))
    pd.DataFrame(months).to_csv(OUT / 'audits/population_monthly_bounds.csv', index=False)
    fin = d0.financial_available_date.notna()
    assert (d0.loc[fin, 'financial_available_date'] < d0.loc[fin, 'date']).all()
    known = d0.industry_id.ne('UNKNOWN')
    assert (d0.loc[known, 'industry_published'] < d0.loc[known, 'date']).all()
    assert (d0.yield_observation_date < d0.date).all()
    for name in ['source_receipts.csv', 'label_sensitivity_coverage.csv', 'p0_audit.json']:
        register(EP27 / 'outputs' / name)
    pd.DataFrame(source).drop_duplicates('path').to_csv(OUT / 'manifests/data_sources.csv', index=False)
    write(OUT / 'audits/data_gate.json', dict(
        stage='P1', status='D0_observed_sample_proxy_research_only',
        D0_rows=len(d0), D0_test_rows=len(d0test), D0_labels_unchanged=True,
        metadata_stocks=len(stocks), recovered_delisted_files=int(quality.source.eq('recovered_retrospective_quote').sum()),
        quarantined_rows=int(quality.invalid_calendar_rows_quarantined.sum()),
        D1_quoted_label_audit_available=True, D1_complete_PIT_pool_certified=False,
        D1_model_gate='blocked: consistent total market cap history and settlement/corporate-action closure not certified',
        original_financial_vintages_certified=False, L3_real_data_gate='stopped',
        original_valuation_vintages_certified=False, valuation_interactions_gate='stopped',
        original_text_vintages_and_training_corpus_available=False, text_gate='stopped',
        disclosure_date_checks_passed=True, prior_files_unchanged=len(prior),
        settlement_repaired=False, quote_recovery_is_not_total_return_repair=True,
        allowed_next_step='pre-register simple D0 mechanisms; no broad-market or executable strategy confirmation'))
    print(pd.DataFrame(records).to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
