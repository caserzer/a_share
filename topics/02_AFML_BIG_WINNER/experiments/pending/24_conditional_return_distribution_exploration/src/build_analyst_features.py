"""Dated broker expectations with explicit coverage and conservative price units."""
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA, OUT
from fetch_historical_reports import CACHE, DEST
from build_improvement_features import FEATURE_PANEL

PANEL = OUT / 'local_cache/analyst_panel.parquet'
RATING = {'买入': 1., '增持': .5, '中性': 0., '减持': -.5, '卖出': -1.}
FACTORS = ['target_upside', 'target_dispersion', 'target_revision', 'target_age',
           'analyst_rating', 'analyst_attention', 'analyst_coverage', 'target_coverage']


def target_anchors(reports, raw, adjusted):
    """An original nominal target expressed in the adjusted-price units of this file.

    Only ratios of this anchor to an as-of adjusted price, or another anchor,
    are used; uniform future adjustment scaling therefore cancels.
    """
    r = reports.copy()
    price = pd.concat([raw.rename('raw'), adjusted.rename('adjusted')], axis=1).dropna()
    price = price[(price.raw > 0) & (price.adjusted > 0)].sort_index()
    low = pd.to_numeric(r.indvAimPriceL, errors='coerce').where(lambda x:x>0)
    high = pd.to_numeric(r.indvAimPriceT, errors='coerce').where(lambda x:x>0)
    target = pd.concat([low, high], axis=1).mean(axis=1)
    ix = price.index.searchsorted(pd.DatetimeIndex(r.publishDate), side='left') - 1
    valid = ix >= 0
    ref = pd.Series(pd.NaT, index=r.index, dtype='datetime64[ns]')
    ref.loc[valid] = price.index[ix[valid]].to_numpy()
    lag = (r.publishDate - ref).dt.days
    valid &= lag.between(1, 10).to_numpy()
    anchor = pd.Series(np.nan, index=r.index)
    anchor.loc[valid] = (target.loc[valid].to_numpy() * price.adjusted.iloc[ix[valid]].to_numpy() /
                         price.raw.iloc[ix[valid]].to_numpy())
    r['target_anchor'] = anchor
    r['price_reference_date'] = ref
    r['rating_score'] = r.emRatingName.map(RATING)
    r = r.sort_values(['orgCode', 'publishDate', 'infoCode']).drop_duplicates(['orgCode', 'publishDate'], keep='last')
    previous = r.groupby('orgCode').target_anchor.shift(1)
    previous_date = r.groupby('orgCode').publishDate.shift(1)
    r['previous_price_reference_date'] = r.groupby('orgCode').price_reference_date.shift(1)
    r['revision'] = np.log(r.target_anchor / previous).where((r.publishDate - previous_date).dt.days <= 365)
    return r


def features_at_date(reports, date, adjusted_close, unexplained=()):
    history = reports[(reports.publishDate < date) & (reports.publishDate >= date - pd.Timedelta(days=180))]
    latest = history.sort_values(['publishDate', 'infoCode']).drop_duplicates('orgCode', keep='last')
    valid = latest.target_anchor.notna() & (adjusted_close > 0)
    if len(unexplained):
        events = pd.DatetimeIndex(unexplained)
        for idx, row in latest.iterrows():
            if ((events > row.price_reference_date) & (events <= date)).any():
                valid.loc[idx] = False
    selected = latest[valid].copy()
    if len(unexplained):
        # A current target may be usable even if its comparison with an older
        # target crosses an unexplained adjustment. Suppress only that revision.
        for idx,row in selected.iterrows():
            if ((events > row.previous_price_reference_date) & (events <= date)).any():
                selected.loc[idx,'revision'] = np.nan
    upside = np.log(selected.target_anchor / adjusted_close)
    recent = int((history.publishDate >= date - pd.Timedelta(days=90)).sum())
    older = len(history) - recent
    return dict(
        target_upside=float(upside.median()) if len(upside) else np.nan,
        target_dispersion=float(upside.quantile(.75) - upside.quantile(.25)) if len(upside) else np.nan,
        target_revision=float(selected.revision.median()) if selected.revision.notna().any() else np.nan,
        target_age=float((date - selected.publishDate).dt.days.median()) if len(selected) else np.nan,
        analyst_rating=float(latest.rating_score.mean()) if latest.rating_score.notna().any() else np.nan,
        analyst_attention=float(np.log1p(recent) - np.log1p(older)),
        analyst_coverage=float(np.log1p(len(latest))), target_coverage=float(np.log1p(len(selected))),
        analyst_available=bool(len(latest)), target_available=bool(len(selected)),
        latest_analyst_date=latest.publishDate.max(), latest_target_date=selected.publishDate.max(),
        target_brokers=len(selected), analyst_brokers=len(latest),
    )


def build():
    audit = json.loads((DEST / 'fetch_audit.json').read_text())
    if {r['year'] for r in audit if r['status'] == 'complete'} != set(range(2018, 2027)):
        raise RuntimeError('Incomplete source years; missing requests cannot be treated as no coverage')
    reports = pd.concat([pd.read_parquet(CACHE / f'{year}.parquet') for year in range(2018, 2027)], ignore_index=True)
    assert not reports.duplicated(['stockCode', 'infoCode']).any()
    panel = pd.read_parquet(FEATURE_PANEL)
    problems = pd.read_csv(OUT / 'r09_total_return_sensitivity/unexplained_factor_events.csv', parse_dates=['date'])
    rows = []
    for n, (stock, g) in enumerate(panel.groupby('instrument', sort=True), 1):
        source = reports[reports.stockCode == stock[2:]].copy()
        raw = pd.read_csv(DATA / f'raw/akshare/day/raw/{stock}.csv', parse_dates=['date']).set_index('date').close
        qfq = pd.read_csv(DATA / f'raw/akshare/day/qfq/{stock}.csv', parse_dates=['date']).set_index('date').close
        anchored = target_anchors(source, raw, qfq)
        bad = problems.loc[problems.instrument == stock, 'date']
        for date in g.date:
            rows.append(dict(date=date, instrument=stock,
                **features_at_date(anchored, date, qfq.get(date, np.nan), bad)))
        if n % 200 == 0:
            print(n, stock, flush=True)
    features = pd.DataFrame(rows)
    for field in ['latest_analyst_date', 'latest_target_date']:
        assert (features[field].isna() | (features[field] < features.date)).all()
    result = panel.merge(features, on=['date', 'instrument'], validate='one_to_one')
    result.to_parquet(PANEL, index=False)
    test = result[result.common_eligible & (result.date >= '2021-01-01')]
    coverage = test.groupby(test.date.dt.year).agg(rows=('instrument', 'size'),
        analyst_available=('analyst_available', 'sum'), target_available=('target_available', 'sum'))
    coverage.to_csv(DEST / 'feature_coverage.csv')
    details = dict(source_reports=len(reports), prediction_rows=len(test),
        covered_analyst_rows=int(test.analyst_available.sum()), covered_target_rows=int(test.target_available.sum()),
        target_age_days=test.loc[test.target_available, 'target_age'].quantile([.1,.5,.9]).to_dict(),
        target_log_upside=test.target_upside.quantile([.01,.5,.99]).to_dict(),
        temporal_check='all contributing publication dates strictly before decision; 180-day limit; latest report per broker',
        adjustment='target / raw prior-publication close * adjusted prior-publication close / adjusted as-of close',
        source_limit='public dated report metadata, not immutable vendor vintages or complete broker consensus',
        missing_policy='retain every original stock-date; forecast uses frozen B where feature unavailable')
    (DEST / 'feature_audit.json').write_text(json.dumps(details, indent=2) + '\n')
    print(json.dumps(details, indent=2))


if __name__ == '__main__':
    build()
