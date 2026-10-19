"""Resumeable bounded public valuation fetch for the existing exploratory pool."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import pandas as pd
from probe_public_data import OUT, probe


def fetch(code):
    path = OUT / f'local_cache/public_valuation/{code}.parquet'
    if path.exists():
        f = pd.read_parquet(path)
        return {'code': code, 'status': 'cached', 'rows': len(f),
                'start': str(f.TRADE_DATE.min()), 'end': str(f.TRADE_DATE.max())}
    result = probe(code)
    time.sleep(.25)
    return result


if __name__ == '__main__':
    panel = pd.read_parquet(OUT / 'local_cache/monthly_panel.parquet', columns=['instrument'])
    codes = sorted(panel.instrument.str[2:].unique())
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch, code) for code in codes]
        for future in as_completed(futures):
            result = future.result()
            results.append({k: v for k, v in result.items() if k != 'columns'})
            if len(results) % 50 == 0:
                pd.DataFrame(results).to_csv(OUT / 'valuation_fetch_progress.csv', index=False)
                print(f'{len(results)}/{len(codes)} completed; usable={sum(x["status"] in ("ok", "cached") for x in results)}', flush=True)
    pd.DataFrame(results).to_csv(OUT / 'valuation_fetch_progress.csv', index=False)
    print(json.dumps({'requested': len(codes), 'usable': sum(x['status'] in ('ok', 'cached') for x in results)}))
