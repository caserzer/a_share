"""Download the pre-sample HKEX issuer mapping and read-only daily adjusted HK closes."""
from pathlib import Path
import gzip
import re
import fitz
import hashlib
import datetime as dt
import json
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
RAW=HERE/'raw'
RAW.mkdir(exist_ok=True)
url='https://www.hkex.com.hk/eng/invest/misc/documents/ic_for_ah_shares.pdf'
headers={'User-Agent':'Mozilla/5.0'}
pdf=RAW/'hkex_mapping.pdf'
if not pdf.exists():
    r=requests.get(url,headers=headers,timeout=30)
    r.raise_for_status()
    pdf.write_bytes(r.content)
doc='\n'.join(page.get_text(sort=True) for page in fitz.open(pdf))
mapping=re.findall(r'^\s*\d+\s+(\d{5})\s+(\d{6})\s+(Shanghai|Shenzhen)\s+(.*?)\s{2,}',doc,re.M)
assert len(mapping)>=100 and len(set(row[1] for row in mapping))==len(mapping)
s=pd.DataFrame(mapping,columns=['hk','a','exchange','name'])
s['instrument']=s.exchange.map({'Shanghai':'SH','Shenzhen':'SZ'})+s.a
s['ticker']=s.hk.map(lambda v:str(int(v)).zfill(4)+'.HK')
s.to_csv(OUT/'mapping.csv',index=False)
u=pd.read_parquet(HERE.parents[1]/'p2/results/scores.parquet',columns=['instrument']).instrument.unique()
tickers=s.loc[s.instrument.isin(u),'ticker'].tolist()+['HKDCNY=X','^HSI']
def download(ticker):
    path=RAW/(ticker+'.json.gz')
    link='https://query1.finance.yahoo.com/v8/finance/chart/'+ticker
    params={'period1':int(pd.Timestamp('2020-12-01',tz='UTC').timestamp()),'period2':int(pd.Timestamp('2026-10-13',tz='UTC').timestamp()),'interval':'1d','events':'div,splits'}
    try:
        if path.exists():
            blob=gzip.decompress(path.read_bytes())
        else:
            for attempt in range(5):
                try:
                    url_used=link.replace('query1','query2') if attempt%2 else link
                    r=requests.get(url_used,headers=headers,params=params,timeout=25)
                    r.raise_for_status()
                    blob=r.content
                    break
                except requests.RequestException:
                    if attempt==4:raise
        d=json.loads(blob)['chart']['result'][0]
        if not path.exists():path.write_bytes(gzip.compress(blob,mtime=0))
        return dict(ticker=ticker,url=link,params=params,sha256=hashlib.sha256(blob).hexdigest(),rows=len(d['timestamp']),currency=d['meta']['currency'],observed_at=dt.datetime.fromtimestamp(path.stat().st_mtime,dt.timezone.utc).isoformat())
    except Exception as e:
        return dict(ticker=ticker,url=link,params=params,error=str(type(e).__name__)+':'+str(e)[:100])
with ThreadPoolExecutor(3) as pool:rows=list(pool.map(download,tickers))
(OUT/'source_receipts.json').write_text(json.dumps(dict(mapping_url=url,mapping_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),mapping_date_text=doc[-250:],bars=rows),ensure_ascii=False,indent=2))
print(len(mapping),len(rows),sum('rows' in r for r in rows),flush=True)
