"""Bounded public endpoint probes, without authentication or unbounded retry."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import requests
import pandas as pd

EP = Path(__file__).resolve().parents[1]
OUT = EP / 'outputs'


def probe(code):
    params = {'sortColumns': 'TRADE_DATE', 'sortTypes': '-1', 'pageSize': '5000',
              'pageNumber': '1', 'reportName': 'RPT_VALUEANALYSIS_DET', 'columns': 'ALL',
              'source': 'WEB', 'client': 'WEB', 'filter': f'(SECURITY_CODE="{code}")'}
    result = {'source': 'eastmoney_valuation', 'code': code}
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        records = (payload.get('result') or {}).get('data') or []
        frame = pd.DataFrame(records)
        result.update(status='ok' if len(frame) else 'empty', rows=len(frame), columns=list(frame.columns))
        if len(frame):
            folder = OUT / 'local_cache/public_valuation'
            folder.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(folder / f'{code}.parquet', index=False)
            result.update(start=str(frame.TRADE_DATE.min()), end=str(frame.TRADE_DATE.max()),
                          pages=(payload.get('result') or {}).get('pages'))
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:350])
    return result


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(probe, ['600000', '000001', '300750']))
    (OUT / 'public_data_probe.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    for r in results:
        print({k: v for k, v in r.items() if k != 'columns'})
