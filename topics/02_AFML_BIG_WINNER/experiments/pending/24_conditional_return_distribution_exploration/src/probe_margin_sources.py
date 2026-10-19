"""Small public-exchange history probe; no credentials, forecasting or writes upstream."""
import hashlib
import json
from datetime import datetime, timezone
import requests
from prepare_panel import OUT

DEST = OUT/'r27_margin_information'
CACHE = OUT/'local_cache/r27_margin_probe'


def probe(date='20210127'):
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    dashed = f'{date[:4]}-{date[4:6]}-{date[6:]}'
    calls = [
        ('sse', 'https://query.sse.com.cn/marketdata/tradedata/queryMargin.do',
         {'isPagination':'true', 'tabType':'mxtype', 'detailsDate':date, 'stockCode':'', 'beginDate':'', 'endDate':'',
          'pageHelp.pageSize':'5000', 'pageHelp.pageNo':'1'}, 'https://www.sse.com.cn/'),
        ('szse', 'https://www.szse.cn/api/report/ShowReport/data',
         {'SHOWTYPE':'JSON', 'CATALOGID':'1837_xxpl', 'txtDate':dashed, 'tab2PAGENO':'1', 'TABKEY':'tab2'},
         'https://www.szse.cn/disclosure/margin/margin/index.html'),
    ]
    summaries = []
    for name, url, params, referer in calls:
        body_path = CACHE/f'{name}_{date}.body'; receipt_path = CACHE/f'{name}_{date}.receipt.json'
        try:
            if receipt_path.exists() and body_path.exists():
                receipt = json.loads(receipt_path.read_text()); body = body_path.read_bytes()
                assert hashlib.sha256(body).hexdigest() == receipt['sha256']
            else:
                response = requests.get(url, params=params, headers={'User-Agent':'Mozilla/5.0', 'Referer':referer}, timeout=20)
                body = response.content; body_path.write_bytes(body)
                receipt = dict(source=name, requested_date=date, status=response.status_code, url=response.url,
                    fetched_at=datetime.now(timezone.utc).isoformat(), bytes=len(body), content_type=response.headers.get('Content-Type'),
                    sha256=hashlib.sha256(body).hexdigest())
                receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
            summary = dict(receipt)
            try:
                payload = json.loads(body)
                summary['payload_type'] = type(payload).__name__
                if isinstance(payload, dict):
                    summary['top_keys'] = list(payload)
                    summary['result_rows'] = len(payload.get('result', []))
                    summary['result_sample'] = payload.get('result', [])[:1]
                    summary['pageHelp'] = payload.get('pageHelp')
                    if summary['pageHelp']: summary['pageHelp'].pop('data', None)
                elif isinstance(payload, list):
                    summary['tables'] = [dict(metadata=t.get('metadata'), rows=len(t.get('data', [])), sample=t.get('data', [])[:1]) for t in payload]
            except (ValueError, TypeError):
                summary['payload_type'] = 'not_json'
            summaries.append(summary)
            print(json.dumps(summary, ensure_ascii=False)[:12000], flush=True)
        except requests.RequestException as exc:
            summary = dict(source=name, requested_date=date, error_type=type(exc).__name__)
            summaries.append(summary); print(json.dumps(summary), flush=True)
    (DEST/f'probe_{date}.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--date', default='20210127')
    probe(parser.parse_args().date)
