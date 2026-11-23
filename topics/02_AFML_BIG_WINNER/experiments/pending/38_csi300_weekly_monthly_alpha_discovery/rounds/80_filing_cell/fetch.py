from pathlib import Path
import csv,requests,concurrent.futures
here=Path(__file__).resolve().parent
def fetch(r):
    p=here/f'results/originals/{r["instrument"]}_{r["period"]}.pdf'
    if p.exists():return
    z=requests.get(r["url"],timeout=30);z.raise_for_status();assert z.content.startswith(b"%PDF")
    tmp=p.with_suffix(".tmp");tmp.write_bytes(z.content);tmp.replace(p)
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    list(pool.map(fetch,csv.DictReader((here/"results/sources.csv").open())))
