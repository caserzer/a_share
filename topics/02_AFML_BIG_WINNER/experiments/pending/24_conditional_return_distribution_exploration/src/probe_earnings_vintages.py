"""Read-only public probe: can an earnings table reconstruct pre-revision forecasts?"""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import requests
from build_market_breadth import DEST
from prepare_panel import OUT


def run():
    cache = OUT / 'local_cache/r17_earnings_probe'
    cache.mkdir(parents=True, exist_ok=True)
    url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
    receipts = []
    session = requests.Session(); session.trust_env = False
    for name, period in [('RPT_PUBLIC_OP_NEWPREDICT', 'REPORT_DATE'), ('RPT_PUBLIC_OP_PREDICT', 'REPORTDATE')]:
        params = dict(reportName=name, columns='ALL', pageSize=100, pageNumber=1,
                      sortColumns='NOTICE_DATE', sortTypes='1',
                      filter=f'(SECURITY_CODE="603313")({period}=\'2025-12-31\')')
        raw_path = cache / f'{name}.json.gz'
        metadata = cache / f'{name}.receipt.json'
        if raw_path.exists() and metadata.exists():
            raw = gzip.decompress(raw_path.read_bytes())
            receipt = json.loads(metadata.read_text())
            assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
        else:
            response = session.get(url, params=params, timeout=20)
            response.raise_for_status(); raw = response.content
            raw_path.write_bytes(gzip.compress(raw, mtime=0))
            receipt = dict(url=response.url, fetched_at=datetime.now(timezone.utc).isoformat(),
                           sha256=hashlib.sha256(raw).hexdigest())
            metadata.write_text(json.dumps(receipt, indent=2) + '\n')
        payload = json.loads(raw)
        if not payload.get('success') or not payload.get('result'):
            raise RuntimeError(payload.get('message'))
        result = payload['result']; rows = result['data']
        assert len(rows) == result['count'] and result['pages'] == 1
        dates = sorted({r['NOTICE_DATE'] for r in rows})
        reason_text = ' '.join(str(v) for row in rows for k, v in row.items() if 'REASON' in k)
        receipts.append(dict(table=name, count=result['count'], notice_dates=dates,
            initial_notice_20260131_mentioned=('2026年1月31日' in reason_text),
            original_notice_row_present=any(d.startswith('2026-01-31') for d in dates),
            **receipt))
    audit = dict(stock='603313', report_period='2025-12-31', probes=receipts,
        conclusion='The sampled tables do not reconstruct the original forecast before the April revision. No claim that every company or every endpoint has the same limitation.',
        model_usage='Excluded from R17 model features. Public current historical tables are not assumed immutable announcement vintages.')
    (DEST / 'earnings_vintage_probe.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    run()
