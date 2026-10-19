"""Fetch ChinaBond published history in bounded annual requests."""
from io import StringIO
import json
import requests
import pandas as pd
from probe_public_data import OUT


if __name__ == '__main__':
    folder = OUT / 'local_cache/public_yields'
    folder.mkdir(exist_ok=True, parents=True)
    session = requests.Session()
    session.trust_env = False
    audit = []
    for year in range(2017, 2027):
        path = folder / f'{year}.parquet'
        try:
            if path.exists():
                frame = pd.read_parquet(path)
            else:
                end = f'{year}-12-31' if year < 2026 else '2026-05-29'
                response = session.get('https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery',
                    params={'startDate': f'{year}-01-01', 'endDate': end, 'gjqx': '0', 'qxId': 'ycqx', 'locale': 'cn_ZH'},
                    headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
                response.raise_for_status()
                tables = pd.read_html(StringIO(response.text.replace('&nbsp', '')), header=0)
                candidates = [t for t in tables if '日期' in t.columns]
                if not candidates:
                    raise ValueError('No dated yield table returned')
                frame = max(candidates, key=len)
                frame.to_parquet(path, index=False)
            names = frame.iloc[:, 0].drop_duplicates().tolist()
            audit.append({'year': year, 'rows': len(frame), 'columns': list(frame.columns), 'curves': names, 'status': 'ok'})
            print(year, len(frame), names, flush=True)
        except Exception as exc:
            audit.append({'year': year, 'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)[:250]})
            print(year, type(exc).__name__, flush=True)
    (OUT / 'yield_fetch_audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
