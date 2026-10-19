"""Resumeable public financial history retrieval; no claim of original PIT vintages."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pandas as pd
from probe_financials import OUT, probe


def fetch(instrument):
    code = instrument[2:] + '.' + instrument[:2]
    path = OUT / f'local_cache/public_financials/{code}.parquet'
    if path.exists():
        f = pd.read_parquet(path)
        return {'code': code, 'status': 'cached', 'rows': len(f)}
    result = probe(code)
    time.sleep(.25)
    return {k: v for k, v in result.items() if k not in ('columns', 'date_examples')}


if __name__ == '__main__':
    panel = pd.read_parquet(OUT / 'local_cache/monthly_panel.parquet', columns=['instrument'])
    codes = sorted(panel.instrument.unique())
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch, code) for code in codes]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results) % 50 == 0:
                pd.DataFrame(results).to_csv(OUT / 'financial_fetch_progress.csv', index=False)
                print(f'{len(results)}/{len(codes)} completed', flush=True)
    pd.DataFrame(results).to_csv(OUT / 'financial_fetch_progress.csv', index=False)
    print(pd.DataFrame(results).status.value_counts().to_dict())
