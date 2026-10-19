"""Inspect public financial history and actual date/version fields."""
import json
import requests
import pandas as pd
from probe_public_data import OUT


def probe(code='600000.SH'):
    params = {'type': 'RPT_F10_FINANCE_MAINFINADATA', 'sty': 'APP_F10_MAINFINADATA',
              'filter': f'(SECUCODE="{code}")', 'p': '1', 'ps': '200', 'sr': '-1',
              'st': 'REPORT_DATE', 'source': 'HSF10', 'client': 'PC'}
    result = {'source': 'eastmoney_financials', 'code': code}
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.get('https://datacenter.eastmoney.com/securities/api/data/get', params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        frame = pd.DataFrame((payload.get('result') or {}).get('data') or [])
        result.update(status='ok' if len(frame) else 'empty', rows=len(frame), columns=list(frame.columns))
        if len(frame):
            folder = OUT / 'local_cache/public_financials'
            folder.mkdir(exist_ok=True, parents=True)
            frame.to_parquet(folder / f'{code}.parquet', index=False)
            result['date_examples'] = frame[[c for c in frame if 'DATE' in c]].head(3).to_dict('records')
            result['report_start'] = str(frame.REPORT_DATE.min())
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:350])
    return result


if __name__ == '__main__':
    result = probe()
    (OUT / 'financial_data_probe.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
