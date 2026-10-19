"""Past-only OHLC/activity interactions; no new outcomes or universe filtering."""
import hashlib
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA, OUT
from run_market_time_models import load_panel, SOURCE_PANEL, MARKET_PANEL

DEST = OUT/'r23_price_volume_features'
PANEL = OUT/'local_cache/price_volume_panel.parquet'
EVENTS = OUT/'r09_total_return_sensitivity/unexplained_factor_events.csv'
ACTIVITY = ['pv_turnover_accel21_63', 'pv_money_accel5_63', 'pv_volume_cv21',
    'pv_return_activity_corr63', 'pv_absret_activity_corr63', 'pv_signed_money21',
    'pv_log_illiquidity63', 'pv_activity_price_divergence21']
PATH = ['path_intraday_mean21', 'path_overnight_mean21', 'path_close_location21',
    'path_range_mean21', 'path_range_accel5_63', 'path_return_autocorr63',
    'path_max_positive_share21', 'path_flat_bar_fraction21']


def daily_features(raw, qfq, calendar, bad_events=()):
    assert raw.index.is_unique and qfq.index.is_unique
    raw = raw.reindex(calendar); qfq = qfq.reindex(calendar)
    price = raw[['open', 'high', 'low', 'close']]
    valid_price = price.gt(0).all(axis=1) & raw.high.ge(price.max(axis=1)-1e-8) & raw.low.le(price.min(axis=1)+1e-8)
    units = raw.source_volume_unit.eq('shares') & raw.source_turnover_unit.eq('ratio')
    positive_activity = raw.volume.gt(0) & raw.money.gt(0)
    vwap = raw.money/raw.volume.where(raw.volume > 0)
    plausible = vwap.between(raw.low*.98, raw.high*1.02)
    valid_activity = valid_price & units & positive_activity & plausible
    volume = raw.volume.where(valid_activity); money = raw.money.where(valid_activity)
    turnover = raw.turnover_rate.where(valid_activity & raw.turnover_rate.ge(0))
    close = qfq.close.where(qfq.close > 0)
    returns = np.log(close/close.shift(1)).where(valid_price & valid_price.shift(1, fill_value=False))
    returns.loc[returns.index.isin(pd.DatetimeIndex(bad_events))] = np.nan
    intraday = np.log(raw.close/raw.open).where(valid_price)
    overnight = returns-intraday
    spread = raw.high-raw.low
    location = ((2*raw.close-raw.high-raw.low)/spread.where(spread > 0)).where(valid_price)
    # A valid one-price bar has neutral location plus its own explicit indicator.
    location = location.mask(valid_price & spread.eq(0), 0.)
    day_range = np.log(raw.high/raw.low).where(valid_price)
    f = pd.DataFrame(index=calendar)
    f['pv_turnover_accel21_63'] = np.log(turnover.rolling(21).mean()/turnover.rolling(63).mean())
    f['pv_money_accel5_63'] = np.log(money.rolling(5).mean()/money.rolling(63).mean())
    f['pv_volume_cv21'] = volume.rolling(21).std()/volume.rolling(21).mean()
    f['pv_return_activity_corr63'] = returns.rolling(63).corr(np.log1p(turnover))
    f['pv_absret_activity_corr63'] = returns.abs().rolling(63).corr(np.log1p(turnover))
    f['pv_signed_money21'] = (np.sign(returns)*money).rolling(21).sum()/money.rolling(21).sum()
    f['pv_log_illiquidity63'] = np.log1p((np.expm1(returns).abs()/money*1e8).rolling(63).mean())
    f['pv_activity_price_divergence21'] = (intraday*money).rolling(21).sum()/money.rolling(21).sum()-intraday.rolling(21).mean()
    f['path_intraday_mean21'] = intraday.rolling(21).mean()
    f['path_overnight_mean21'] = overnight.rolling(21).mean()
    f['path_close_location21'] = location.rolling(21).mean()
    f['path_range_mean21'] = day_range.rolling(21).mean()
    f['path_range_accel5_63'] = np.log(day_range.rolling(5).mean()/day_range.rolling(63).mean())
    f['path_return_autocorr63'] = returns.rolling(63).corr(returns.shift(1))
    f['path_max_positive_share21'] = returns.clip(lower=0).rolling(21).max()/returns.abs().rolling(21).sum()
    f['path_flat_bar_fraction21'] = spread.eq(0).astype(float).where(valid_price & positive_activity).rolling(21).mean()
    f['activity_support63'] = valid_activity.astype(float).rolling(63).sum()
    f['price_support63'] = valid_price.astype(float).rolling(63).sum()
    f = f.replace([np.inf, -np.inf], np.nan)
    audit = dict(raw_rows=int(raw.close.notna().sum()), invalid_price_rows=int((raw.close.notna() & ~valid_price).sum()),
        nonpositive_activity_rows=int((valid_price & ~positive_activity).sum()),
        unit_or_vwap_rejected_rows=int((valid_price & positive_activity & (~units | ~plausible)).sum()),
        known_factor_events_masked=int(returns.index.isin(pd.DatetimeIndex(bad_events)).sum()))
    return f, audit


def build():
    DEST.mkdir(exist_ok=True); panel = load_panel()
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    events = pd.read_csv(EVENTS, parse_dates=['date'])
    pieces = []; quality = []; receipts = []
    for n, (stock, group) in enumerate(panel.groupby('instrument', sort=True), 1):
        paths = {kind: DATA/f'raw/akshare/day/{kind}/{stock}.csv' for kind in ['raw', 'qfq']}
        bars = {kind: pd.read_csv(path, parse_dates=['date']).set_index('date').sort_index() for kind, path in paths.items()}
        features, audit = daily_features(bars['raw'], bars['qfq'], calendar, events.loc[events.instrument.eq(stock), 'date'])
        features = features.reindex(pd.DatetimeIndex(group.date)); features.index.name = 'date'
        pieces.append(group.merge(features.reset_index(), on='date', validate='one_to_one'))
        quality.append(dict(instrument=stock, **audit))
        receipts.extend(dict(instrument=stock, kind=kind, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for kind, path in paths.items())
        if n % 200 == 0: print('feature stocks', n, flush=True)
    result = pd.concat(pieces, ignore_index=True)
    assert len(result) == len(panel) and not result.duplicated(['date', 'instrument']).any()
    result.to_parquet(PANEL, index=False)
    test = result[result.date >= '2021-01-01']; assert len(test) == 27600
    pd.DataFrame(quality).to_csv(DEST/'daily_quality.csv', index=False)
    pd.DataFrame(receipts).to_csv(DEST/'source_receipts.csv', index=False)
    pd.DataFrame([dict(year=year, feature=c, rows=len(g), available=int(g[c].notna().sum()))
        for year, g in test.groupby(test.date.dt.year) for c in ACTIVITY+PATH]).to_csv(DEST/'feature_coverage.csv', index=False)
    audit = dict(training_and_test_rows=len(result), prediction_rows=len(test), stocks=len(quality),
        feature_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        original_panel_sha256=hashlib.sha256(SOURCE_PANEL.read_bytes()).hexdigest(),
        market_panel_sha256=hashlib.sha256(MARKET_PANEL.read_bytes()).hexdigest(),
        events_sha256=hashlib.sha256(EVENTS.read_bytes()).hexdigest(),
        missing_test_rows=test[ACTIVITY+PATH].isna().sum().to_dict(),
        quality_totals=pd.DataFrame(quality).drop(columns='instrument').sum().to_dict(),
        timing='Features use only bars through the decision close, full 21/63-session windows; no future shifts or filling missing market values.',
        semantics='Signed turnover is a statistical price-activity proxy, not identified investor flows. Neutral location on a valid flat bar is explicitly defined; flat bars also have a separate indicator.',
        limitations='Uses existing raw/qfq price proxies and original pool; historical provider revisions and known pool bias remain. Unexplained factor days affect return-based predictors only; labels and population remain frozen.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    build()
