"""Freeze prior forecasts, then fetch only stocks required for newly matured labels."""
import gzip
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import requests
from run_four_horizons import OUT
DEST=OUT/'r14_newly_matured'
CACHE=OUT/'local_cache/r14_public_extension'
URL='https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get'


def fetch(stock):
    path=CACHE/f'{stock}.parquet'; receipt=CACHE/f'{stock}.receipt.json'
    if path.exists() and receipt.exists():return json.loads(receipt.read_text())
    session=requests.Session();session.trust_env=False
    error=None
    for attempt in range(1,4):
        try:
            r=session.get(URL,params={'param':f'{stock.lower()},day,2025-06-01,2026-10-19,640,qfq'},timeout=20)
            r.raise_for_status();payload=r.json();data=payload['data'][stock.lower()]
            rows=data.get('qfqday',data.get('day'))
            if not rows:raise ValueError('No price rows')
            frame=pd.DataFrame([row[:6] for row in rows],columns=['date','open','close','high','low','volume'])
            frame['date']=pd.to_datetime(frame.date)
            for c in frame.columns[1:]:frame[c]=pd.to_numeric(frame[c],errors='coerce')
            frame=frame[frame.date<='2026-10-19'].sort_values('date')
            if frame.date.duplicated().any():raise ValueError('Duplicate price dates')
            raw=r.content
            with gzip.open(CACHE/f'{stock}.json.gz','wb') as f:f.write(raw)
            frame.to_parquet(path,index=False)
            result=dict(instrument=stock,status='ok',rows=len(frame),start=str(frame.date.min().date()),end=str(frame.date.max().date()),
                sha256=hashlib.sha256(raw).hexdigest(),url=r.url,retrieved_utc=datetime.now(timezone.utc).isoformat(),attempt=attempt)
            receipt.write_text(json.dumps(result,indent=2)+'\n');time.sleep(.15)
            return result
        except Exception as e:
            error=f'{type(e).__name__}: {str(e)[:220]}'
            if attempt<3:time.sleep(attempt)
    return dict(instrument=stock,status='failed',error=error)


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    stocks=set();manifest=[];rows=[]
    for h in [1,3,6]:
        p=OUT/f'r10_four_horizons/predictions_{h}m.parquet'
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.append(dict(months=h,path=str(p),sha256=digest))
        d=pd.read_parquet(p);d=d[d.model=='peers_risk_size']
        g=d[(d.target_date>'2026-05-29')&(d.target_date<='2026-10-19')]
        stocks.update(g.instrument);rows.append(dict(months=h,stock_dates=len(g),prediction_months=g.date.nunique()))
    freeze=DEST/'frozen_predictions.json'
    if freeze.exists():assert json.loads(freeze.read_text())['files']==manifest,'Frozen forecasts changed'
    else:freeze.write_text(json.dumps(dict(files=manifest,created_utc=datetime.now(timezone.utc).isoformat(),candidates=rows),indent=2)+'\n')
    calendar=fetch('SH000001')
    if calendar['status']!='ok':raise RuntimeError(calendar)
    results=[calendar]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(fetch,s) for s in sorted(stocks)]
        for i,f in enumerate(as_completed(futures),1):
            results.append(f.result())
            if i%25==0 or i==len(futures):
                pd.DataFrame(results).to_csv(DEST/'fetch_audit.csv',index=False)
                print(i,'/',len(futures),'ok',sum(r['status']=='ok' for r in results),flush=True)
    pd.DataFrame(results).to_csv(DEST/'fetch_audit.csv',index=False)


if __name__=='__main__':run()
