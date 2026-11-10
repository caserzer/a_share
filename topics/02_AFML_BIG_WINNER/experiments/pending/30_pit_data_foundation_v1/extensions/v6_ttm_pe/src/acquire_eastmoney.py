"""Independent public valuation source, sequential requests and full pagination.

The provider caps pages at 10,000 records. Every page is archived, total count and
unique security/date keys must reconcile before a monthly partition is admitted.
Empty API results are recorded as missing coverage, never zero valuations.
"""
import json
import time
import pandas as pd
from pe_common import CACHE, OUT, archive_bytes, write_json, utc_now, verified, sha

URL = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

def main():
    import backfill_http as http
    http.PUBLIC = CACHE / 'logs/eastmoney'
    http.archive_bytes = lambda body: archive_bytes(body, root=CACHE)
    client = http.CapturedHTTP()
    client.session.trust_env = False
    stop = CACHE / 'EASTMONEY_ACCESS_STOP.json'
    if stop.exists():
        raise PermissionError('Provider access-stop latch set')
    periods = list(pd.period_range('2017-01', '2026-10', freq='M'))
    periods.sort(key=lambda p: (not (2021 <= p.year <= 2024), p))
    progress = []
    for period in periods:
        key = str(period)
        path = CACHE / f'acquired/eastmoney/{key}.parquet'
        empty = path.with_suffix('.empty.json')
        if verified(path):
            progress.append(dict(month=key, status='ACQUIRED', reused=True))
            continue
        if empty.exists():
            progress.append(dict(month=key, status='NO_PROVIDER_DATA', reused=True))
            continue
        start = max(period.start_time, pd.Timestamp('2017-01-03')).strftime('%Y-%m-%d')
        end = min(period.end_time, pd.Timestamp('2026-10-21')).strftime('%Y-%m-%d')
        pages, records, receipts, expected = 1, [], [], None
        try:
            number = 1
            while number <= pages:
                params = dict(reportName='RPT_VALUEANALYSIS_DET',
                    columns='SECURITY_CODE,SECUCODE,TRADE_DATE,PE_TTM',
                    pageSize=10000, pageNumber=number,
                    sortColumns='TRADE_DATE,SECURITY_CODE', sortTypes='1,1',
                    source='WEB', client='WEB',
                    filter=f"(TRADE_DATE>='{start}')(TRADE_DATE<='{end}')")
                # Page cache is append-only and recoverable independently of month completion.
                page = CACHE / f'acquired/eastmoney/pages/{key}-{number:03d}.json'
                receipt_path = page.with_suffix('.receipt.json')
                if page.exists() and receipt_path.exists():
                    rec = json.loads(receipt_path.read_text())
                    if sha(page) != rec['sha256']:
                        raise ValueError('Cached response hash changed')
                    payload = json.loads(page.read_bytes())
                else:
                    last_error = None
                    for attempt in range(3):
                        try:
                            body, rec = client.fetch('eastmoney_ttm_pe', URL, params=params)
                            payload = json.loads(body)
                            break
                        except PermissionError:
                            raise
                        except Exception as exc:
                            last_error = exc
                            if attempt == 2:
                                raise
                            time.sleep([5, 15][attempt])
                    page.parent.mkdir(parents=True, exist_ok=True)
                    page.write_bytes(body)
                    write_json(receipt_path, rec)
                receipts.append(rec)
                result = payload.get('result') or {}
                if payload.get('code') == 9201 and number == 1:
                    write_json(empty, dict(month=key, status='NO_PROVIDER_DATA', receipt=rec,
                                           reason=payload.get('message'), known_at=None))
                    break
                if not payload.get('success'):
                    raise PermissionError('Provider rejected query: ' + str(payload.get('message')))
                if expected is None:
                    expected, pages = result['count'], result['pages']
                if result['count'] != expected or result['pages'] != pages:
                    raise ValueError('Pagination population changed during acquisition')
                records.extend(result['data'])
                number += 1
            if expected is not None:
                f = pd.DataFrame(records)
                if len(f) != expected or f.duplicated(['SECUCODE', 'TRADE_DATE']).any():
                    raise ValueError('Incomplete or duplicated paginated population')
                if not pd.to_datetime(f.TRADE_DATE).between(start, end).all():
                    raise ValueError('Out-of-window source rows')
                path.parent.mkdir(parents=True, exist_ok=True)
                f.to_parquet(path, index=False)
                write_json(str(path)+'.receipt.json', dict(provider='Eastmoney_public',
                    rows=len(f), pages=pages, parquet_sha256=sha(path),
                    response_sha256=[r['sha256'] for r in receipts],
                    observed_at=receipts[0]['source_observed_at'],
                    ingested_at=receipts[-1]['ingested_at'],
                    page_receipts=receipts, known_at=None, quality_tier='Historical-proxy'))
                progress.append(dict(month=key, status='ACQUIRED', rows=len(f), pages=pages))
            else:
                progress.append(dict(month=key, status='NO_PROVIDER_DATA', rows=0))
        except PermissionError as exc:
            write_json(stop, dict(status='BLOCKED_ACCESS', reason=str(exc), at=utc_now()))
            progress.append(dict(month=key, status='BLOCKED_ACCESS', reason=str(exc)))
            write_json(OUT/'eastmoney_acquisition.json', dict(status='BLOCKED_ACCESS', progress=progress))
            raise
        except Exception as exc:
            progress.append(dict(month=key, status='UNRESOLVED', reason=str(exc)[:250]))
            write_json(OUT/'eastmoney_acquisition.json', dict(status='PARTIAL', progress=progress))
            raise
        write_json(OUT/'eastmoney_acquisition.json', dict(status='RUNNING', progress=progress,updated_at=utc_now()))
        print(json.dumps(progress[-1]), flush=True)
    write_json(OUT/'eastmoney_acquisition.json', dict(status='COMPLETE_WITH_PROVIDER_GAPS',
        progress=progress, updated_at=utc_now(), periods=len(periods)))

if __name__ == '__main__':
    main()
