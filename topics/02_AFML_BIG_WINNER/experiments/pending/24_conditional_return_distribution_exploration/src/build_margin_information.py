"""R27 official monthly margin snapshots, explicit units and conservative availability."""
import hashlib
import io
import json
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from prepare_panel import DATA, EP, OUT

DEST = OUT/'r27_margin_information'
CACHE = OUT/'local_cache/r27_margin_snapshots'
PANEL = OUT/'local_cache/margin_information_panel.parquet'
SOURCE = OUT/'local_cache/historical_peer_panel.parquet'
INDIVIDUAL = ['margin_observed', 'margin_financing_cap', 'margin_financing_change_cap',
              'margin_buy_balance', 'margin_lending_cap']
MARKET = ['margin_market_financing_change', 'margin_market_buy_balance', 'margin_market_lending_share']
SZ_FIELDS = {'jrrzmr': ('融资买入额(元)', 1e8), 'jrrzye': ('融资余额(元)', 1e8),
             'jrrjmc': ('融券卖出量(股/份)', 1e4), 'jrrjyl': ('融券余量(股/份)', 1e4),
             'jrrjye': ('融券余额(元)', 1e4), 'jrrzrjye': ('融资融券余额(元)', 1e8)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(name, date, url, params, referer):
    CACHE.mkdir(exist_ok=True); path = CACHE/f'{name}_{date}.body'; receipt = path.with_suffix('.receipt.json')
    if path.exists() and receipt.exists():
        r = json.loads(receipt.read_text())
        assert r['sha256'] == digest(path) and r['status'] == 200
        assert r['requested_date'] == date and r['params'] == params
        return path.read_bytes()
    for attempt in range(3):
        try:
            response = requests.get(url, params=params,
                headers={'User-Agent': 'Mozilla/5.0', 'Referer': referer}, timeout=25)
            response.raise_for_status()
            body = response.content
            # Reject HTML errors masquerading as a successful data response.
            if name == 'szse_excel':
                assert body.startswith(b'PK')
            else:
                json.loads(body)
            path.write_bytes(body)
            receipt.write_text(json.dumps(dict(requested_date=date, url=response.url, params=params,
                status=response.status_code, fetched_at=datetime.now(timezone.utc).isoformat(),
                bytes=len(body), sha256=digest(path)), indent=2)+'\n')
            time.sleep(.5)
            return body
        except (requests.RequestException, ValueError, AssertionError):
            if attempt == 2:
                raise RuntimeError(f'Public data fetch failed: {name} {date}') from None
            time.sleep(2*(attempt+1))


def number(value):
    return float(str(value).replace(',', ''))


def parse_szse(metadata_body, excel_body, date):
    tables = json.loads(metadata_body)
    detail = next(t for t in tables if t['metadata']['tabkey'] == 'tab2')
    summary = next(t for t in tables if t['metadata']['tabkey'] == 'tab1')
    for t in [detail, summary]:
        assert t['metadata']['subname'] == str(pd.Timestamp(date).date())
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Workbook contains no default style')
        frame = pd.read_excel(io.BytesIO(excel_body), dtype=str)
    assert len(frame) == int(detail['metadata']['recordcount']) > 0
    assert not frame['证券代码'].duplicated().any()
    frame['证券代码'] = frame['证券代码'].str.zfill(6)
    for field, (column, scale) in SZ_FIELDS.items():
        label = detail['metadata']['cols'][field]
        unit = '亿元' if scale == 1e8 else ('万元' if field == 'jrrjye' else '万股/万份')
        assert unit in label
        frame[column] = frame[column].map(number)
        assert frame[column].ge(0).all()
        indexed = frame.set_index('证券代码')
        for row in detail['data']:
            # The exchange display truncates precision; Excel retains exact units.
            assert abs(indexed.loc[row['zqdm'], column] - number(row[field])*scale) <= .010001*scale
    np.testing.assert_allclose(frame['融资融券余额(元)'], frame['融资余额(元)']+frame['融券余额(元)'], atol=2, rtol=0)
    result = pd.DataFrame(dict(instrument='SZ'+frame['证券代码'], financing=frame['融资余额(元)'],
        buy=frame['融资买入额(元)'], lending_quantity=frame['融券余量(股/份)'], lending_value=frame['融券余额(元)']))
    assert len(summary['data']) == 1
    row = summary['data'][0]
    for k in ['jrrzmr', 'jrrzye', 'jrrjye']:
        assert '亿元' in summary['metadata']['cols'][k]
    market = dict(financing=number(row['jrrzye'])*1e8, buy=number(row['jrrzmr'])*1e8,
                  lending_value=number(row['jrrjye'])*1e8)
    return result, market


def snapshot(date):
    sse_url = 'https://query.sse.com.cn/marketdata/tradedata/queryMargin.do'
    params = {'isPagination':'true', 'tabType':'mxtype', 'detailsDate':date, 'stockCode':'',
              'beginDate':'', 'endDate':'', 'pageHelp.pageSize':'5000', 'pageHelp.pageNo':'1'}
    first = json.loads(fetch('sse_detail', date, sse_url, params, 'https://www.sse.com.cn/'))
    rows = first['result']; total = int(first['pageHelp']['total'])
    page = 1
    while len(rows) < total:
        page += 1
        assert page < 20
        page_params = dict(params, **{'pageHelp.pageNo':str(page)})
        data = json.loads(fetch(f'sse_detail_page{page}', date, sse_url, page_params, 'https://www.sse.com.cn/'))
        assert int(data['pageHelp']['total']) == total and data['result']
        rows += data['result']
    assert len(rows) == total > 0
    raw = pd.DataFrame(rows)
    assert raw.opDate.eq(date).all() and not raw.stockCode.duplicated().any()
    sh = pd.DataFrame(dict(instrument='SH'+raw.stockCode, financing=raw.rzye, buy=raw.rzmre,
                           lending_quantity=raw.rqyl, lending_value=np.nan))
    for c in ['financing', 'buy', 'lending_quantity']:
        sh[c] = pd.to_numeric(sh[c]); assert sh[c].ge(0).all()
    sp = {'isPagination':'true', 'tabType':'', 'beginDate':date, 'endDate':date,
          'pageHelp.pageSize':'5000', 'pageHelp.pageNo':'1'}
    summary = json.loads(fetch('sse_summary', date, sse_url, sp, 'https://www.sse.com.cn/'))['result']
    assert len(summary) == 1 and summary[0]['opDate'] == date
    sr = summary[0]
    zp = {'SHOWTYPE':'JSON', 'CATALOGID':'1837_xxpl', 'txtDate':str(pd.Timestamp(date).date()),
          'tab1PAGENO':'1', 'tab2PAGENO':'1'}
    ref = 'https://www.szse.cn/disclosure/margin/margin/index.html'
    zb = fetch('szse_metadata', date, 'https://www.szse.cn/api/report/ShowReport/data', zp, ref)
    xp = {'SHOWTYPE':'xlsx', 'CATALOGID':'1837_xxpl', 'txtDate':zp['txtDate'], 'TABKEY':'tab2'}
    xb = fetch('szse_excel', date, 'https://www.szse.cn/api/report/ShowReport', xp, ref)
    sz, sm = parse_szse(zb, xb, date)
    market = {k: sm[k]+float(sr[v]) for k, v in [('financing','rzye'), ('buy','rzmre'), ('lending_value','rqylje')]}
    result = pd.concat([sh, sz], ignore_index=True)
    result['snapshot_date'] = pd.Timestamp(date)
    return result, market


def dates_and_panel():
    panel = pd.read_parquet(SOURCE)
    all_dates = sorted(pd.read_parquet(OUT/'local_cache/improvement_panel.parquet', columns=['date']).date.unique())
    first = all_dates.index(panel.date.min())
    origins = all_dates[first-1:]
    calendar = pd.DatetimeIndex(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0])
    snapshots = {pd.Timestamp(d): calendar[calendar.get_loc(d)-2] for d in origins}
    return panel, snapshots


def build(download_only=False):
    DEST.mkdir(exist_ok=True)
    panel, dates = dates_and_panel(); frames = []; markets = []
    for origin, asof in dates.items():
        frame, market = snapshot(asof.strftime('%Y%m%d'))
        frame['date'] = origin; frames.append(frame)
        markets.append(dict(date=origin, snapshot_date=asof, **market))
        print(origin.date(), 'snapshot', asof.date(), 'rows', len(frame), flush=True)
    detail = pd.concat(frames, ignore_index=True); market = pd.DataFrame(markets).sort_values('date')
    detail.to_parquet(CACHE/'normalized_detail.parquet', index=False)
    market.to_parquet(CACHE/'normalized_market.parquet', index=False)
    if download_only:
        return
    prior_dates = dict(zip(list(dates)[1:], list(dates)[:-1]))
    prior = detail[['date','instrument','financing']].rename(columns={'date':'previous_origin', 'financing':'prior_financing'})
    detail['previous_origin'] = detail.date.map(prior_dates)
    detail = detail.merge(prior, on=['previous_origin','instrument'], how='left', validate='many_to_one')
    # SSE quantities are priced using the exact unadjusted snapshot close, never qfq prices.
    price_receipts = []; price_matches = 0
    for instrument, group in detail[detail.instrument.isin(panel.instrument.unique()) & detail.instrument.str.startswith('SH')].groupby('instrument'):
        path = DATA/f'raw/akshare/day/raw/{instrument}.csv'
        if not path.exists():
            continue
        raw = pd.read_csv(path, usecols=['date','close']); raw['date'] = pd.to_datetime(raw.date)
        assert not raw.date.duplicated().any()
        prices = group.snapshot_date.map(raw.set_index('date').close)
        values = group.lending_quantity*prices
        values = values.mask(group.lending_quantity.eq(0), 0)
        detail.loc[group.index, 'lending_value'] = values
        price_matches += int(prices.notna().sum())
        price_receipts.append(dict(path=str(path), sha256=digest(path)))
    merged = panel.merge(detail[['date','instrument','snapshot_date','financing','prior_financing','buy','lending_value']],
                         on=['date','instrument'], how='left', validate='one_to_one', sort=False)
    cap = merged.total_market_cap_cny.where(merged.total_market_cap_cny.gt(0))
    balance = merged.financing.where(merged.financing.gt(0))
    merged['margin_observed'] = merged.financing.notna().astype(float)
    merged['margin_financing_cap'] = merged.financing/cap
    merged['margin_financing_change_cap'] = (merged.financing-merged.prior_financing)/cap
    merged['margin_buy_balance'] = merged.buy/balance
    merged['margin_lending_cap'] = merged.lending_value/cap
    market['margin_market_financing_change'] = np.log(market.financing/market.financing.shift(1))
    market['margin_market_buy_balance'] = market.buy/market.financing
    market['margin_market_lending_share'] = market.lending_value/(market.financing+market.lending_value)
    merged = merged.merge(market[['date']+MARKET], on='date', how='left', validate='many_to_one', sort=False)
    pd.testing.assert_frame_equal(merged[panel.columns], panel)
    assert len(merged) == len(panel) and np.isfinite(merged[MARKET]).all().all()
    assert not np.isinf(merged[INDIVIDUAL]).any().any()
    assert merged.loc[merged.margin_observed.eq(1),'snapshot_date'].lt(merged.loc[merged.margin_observed.eq(1),'date']).all()
    merged.to_parquet(PANEL, index=False)
    coverage = merged.assign(period=np.where(merged.date.ge('2021-01-01'),'evaluation','training')).groupby('period')[INDIVIDUAL].agg(['count','mean'])
    coverage.to_csv(DEST/'coverage.csv')
    audit = dict(technical_feature_integrity_passed=True, rows=len(merged), origins=len(dates),
        source_sha256=digest(SOURCE), feature_sha256=digest(PANEL), plan_sha256=digest(EP/'notes/r27_margin_information.md'),
        normalized_detail_sha256=digest(CACHE/'normalized_detail.parquet'), normalized_market_sha256=digest(CACHE/'normalized_market.parquet'),
        price_matches=price_matches, price_receipts=price_receipts,
        raw_receipts=[dict(path=str(p), receipt_sha256=digest(p), **json.loads(p.read_text())) for p in sorted(CACHE.glob('*.receipt.json'))],
        limitation='Public historical revisions not vintage-certified; absent detail stays missing; SZ market aggregates have 0.01 billion CNY display precision.',
        source_lag_trading_sessions=2)
    (DEST/'feature_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(coverage.to_string(), flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--download-only', action='store_true')
    build(parser.parse_args().download_only)
