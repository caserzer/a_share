"""Read public dated broker-report metadata; preserve raw pages and response hashes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import json
import time
import requests
import pandas as pd
from prepare_panel import OUT

DEST = OUT / 'r18_analyst_expectations'
CACHE = OUT / 'local_cache/r18_reports'
FIELDS = ['title', 'stockCode', 'orgCode', 'orgSName', 'publishDate', 'infoCode',
          'emRatingName', 'emRatingValue', 'lastEmRatingName', 'ratingChange',
          'indvAimPriceT', 'indvAimPriceL', 'sRatingName', 'attachType', 'attachPages']


def fetch_year(year, delay):
    session = requests.Session(); session.trust_env = False
    folder = CACHE / str(year); folder.mkdir(parents=True, exist_ok=True)
    page, pages = 1, 1
    records, receipts = [], []
    while page <= pages:
        rawfile = folder / f'{page:04d}.json.gz'
        receiptfile = folder / f'{page:04d}.receipt.json'
        if rawfile.exists() and receiptfile.exists():
            raw = gzip.decompress(rawfile.read_bytes())
            receipt = json.loads(receiptfile.read_text())
            assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
        else:
            params = dict(industryCode='*', pageSize=100, industry='*', rating='*', ratingChange='*',
                beginTime=f'{year}-01-01', endTime=f'{year}-12-31' if year < 2026 else '2026-05-29',
                pageNo=page, fields='', qType=0, orgCode='', code='', rcode='',
                p=page, pageNum=page, pageNumber=page)
            for attempt in range(3):
                try:
                    response = session.get('https://reportapi.eastmoney.com/report/list', params=params, timeout=25)
                    response.raise_for_status(); raw = response.content
                    check = json.loads(raw)
                    if 'data' not in check or 'TotalPage' not in check:
                        raise ValueError('No paginated report data')
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    # The provider can reject bursts with status 567. Back off;
                    # do not switch identities, bypass challenges, or hammer it.
                    print(year, page, 'request failed; backing off', 60 * (attempt + 1), flush=True)
                    time.sleep(60 * (attempt + 1))
            receipt = dict(url=response.url, fetched_at=datetime.now(timezone.utc).isoformat(),
                           sha256=hashlib.sha256(raw).hexdigest())
            rawfile.write_bytes(gzip.compress(raw, mtime=0))
            receiptfile.write_text(json.dumps(receipt, indent=2) + '\n')
            time.sleep(delay)
        payload = json.loads(raw); pages = payload['TotalPage']
        records.extend(payload['data']); receipts.append(receipt)
        if page % 25 == 0 or page == pages:
            print(year, page, '/', pages, 'rows', len(records), flush=True)
        page += 1
    frame = pd.DataFrame(records)
    assert len(frame) == payload['hits'], (year, len(frame), payload['hits'])
    assert not frame.duplicated(['stockCode', 'infoCode']).any()
    frame = frame.reindex(columns=FIELDS)
    # Vendor mixes JSON numeric values with empty strings in metadata fields.
    for column in frame:
        frame[column] = frame[column].fillna('').astype(str)
    frame['publishDate'] = pd.to_datetime(frame.publishDate)
    assert frame.publishDate.dt.year.eq(year).all()
    frame.to_parquet(CACHE / f'{year}.parquet', index=False)
    return dict(year=year, rows=len(frame), pages=pages, status='complete',
        raw_response_hashes=[r['sha256'] for r in receipts],
        target_rows=int((frame.indvAimPriceT.fillna('').ne('') | frame.indvAimPriceL.fillna('').ne('')).sum()))


def run(start, end, workers, delay):
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_year, year, delay): year for year in range(start, end + 1)}
        for future in as_completed(futures):
            year = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = dict(year=year, status='failed', error=str(exc)[:400])
            results.append(result)
            (DEST / 'fetch_audit.json').write_text(json.dumps(sorted(results, key=lambda x:x['year']), indent=2) + '\n')
            print({k:v for k,v in result.items() if k != 'raw_response_hashes'}, flush=True)
    if any(r['status'] != 'complete' for r in results):
        raise RuntimeError('Some years incomplete; resume stored pages, do not score incomplete data')


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--start',type=int,default=2018);p.add_argument('--end',type=int,default=2026);p.add_argument('--workers',type=int,default=1);p.add_argument('--delay',type=float,default=.8)
    args = p.parse_args();run(args.start,args.end,args.workers,args.delay)
