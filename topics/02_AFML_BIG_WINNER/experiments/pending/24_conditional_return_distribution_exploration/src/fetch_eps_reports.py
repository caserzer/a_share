"""Select latest known original report per stock/date, then cache original HTML.

The pilot is for extraction validation only; it is not a smaller test population.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import gzip
import hashlib
import json
import threading
import time
import numpy as np
import pandas as pd
import requests
from prepare_panel import OUT
from fetch_historical_reports import CACHE as METADATA
from build_improvement_features import FEATURE_PANEL
from parse_eps_forecasts import parse_report

DEST=OUT/'r19_eps_expectations'
CACHE=OUT/'local_cache/r19_eps_html'
PAUSE_UNTIL=0.
PAUSE_LOCK=threading.Lock()
THREAD_LOCAL=threading.local()


def select_reports():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    metadata=pd.concat([pd.read_parquet(METADATA/f'{y}.parquet') for y in range(2018,2027)],ignore_index=True)
    panel=pd.read_parquet(FEATURE_PANEL,columns=['date','instrument','common_eligible'])
    panel=panel[panel.common_eligible]
    mapped=[]
    for stock,g in panel.groupby('instrument',sort=True):
        r=metadata[metadata.stockCode.eq(stock[2:])].sort_values(['publishDate','infoCode']).drop_duplicates('publishDate',keep='last')
        positions=r.publishDate.searchsorted(g.date,side='left')-1
        for date,position in zip(g.date,positions):
            row=dict(date=date,instrument=stock,infoCode=None)
            if position>=0 and (date-r.iloc[position].publishDate).days<=180:
                row['infoCode']=r.iloc[position].infoCode
            mapped.append(row)
    mapping=pd.DataFrame(mapped)
    selected=metadata[metadata.infoCode.isin(mapping.infoCode.dropna())].drop_duplicates('infoCode').copy()
    selected['sample_hash']=selected.infoCode.map(lambda x:hashlib.sha256(x.encode()).hexdigest())
    selected=selected.sort_values(['publishDate','infoCode']).reset_index(drop=True)
    mapping.to_parquet(DEST/'decision_report_map.parquet',index=False)
    selected.to_parquet(DEST/'selected_reports.parquet',index=False)
    (DEST/'selection.json').write_text(json.dumps(dict(stock_dates=len(mapping),selected_reports=len(selected),
        mapped_stock_dates=int(mapping.infoCode.notna().sum()),
        rule='latest report strictly before each original eligible stock-date, max age 180 days; no outcome inputs',
        earnings='single latest report, not a multi-broker consensus'),indent=2)+'\n')
    return selected


def pause(seconds):
    global PAUSE_UNTIL
    with PAUSE_LOCK:PAUSE_UNTIL=max(PAUSE_UNTIL,time.monotonic()+seconds)


def fetch_one(row,delay):
    prefix=CACHE/row.infoCode
    rawfile=prefix.with_suffix('.html.gz');receiptfile=prefix.with_suffix('.receipt.json')
    receipt={};raw=None
    if rawfile.exists() and receiptfile.exists():
        receipt=json.loads(receiptfile.read_text());raw=gzip.decompress(rawfile.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==receipt['sha256']
    else:
        if not hasattr(THREAD_LOCAL,'session'):
            THREAD_LOCAL.session=requests.Session();THREAD_LOCAL.session.trust_env=False
        session=THREAD_LOCAL.session
        url=f'https://data.eastmoney.com/report/info/{row.infoCode}.html'
        for attempt in range(3):
            while time.monotonic()<PAUSE_UNTIL:time.sleep(max(0,min(1,PAUSE_UNTIL-time.monotonic())))
            try:
                response=session.get(url,timeout=25)
                response.raise_for_status();raw=response.content
                if b'ctx-content' not in raw:
                    raise ValueError('Original report body missing; may be an access challenge')
                receipt=dict(url=url,fetched_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),status=response.status_code)
                rawfile.write_bytes(gzip.compress(raw,mtime=0));receiptfile.write_text(json.dumps(receipt,indent=2)+'\n')
                break
            except Exception as exc:
                if attempt==2:
                    return dict(infoCode=row.infoCode,stockCode=row.stockCode,publishDate=str(row.publishDate),status='fetch_failed',error=str(exc)[:250],forecasts='{}')
                pause(60*(attempt+1))
            finally:
                time.sleep(delay)
    result=parse_report(raw.decode('utf-8'),row.publishDate,row.stockCode)
    return dict(infoCode=row.infoCode,stockCode=row.stockCode,publishDate=str(row.publishDate),
                **{k:v for k,v in result.items() if k not in ['forecasts','profit_forecasts']},forecasts=json.dumps(result['forecasts']),
                profit_forecasts=json.dumps(result.get('profit_forecasts',{})),
                raw_sha256=receipt['sha256'])


def run(pilot,workers,delay):
    selected=select_reports()
    if pilot:
        selected=selected.assign(year=selected.publishDate.dt.year).sort_values('sample_hash').groupby('year',group_keys=False).head(pilot)
    else:
        selected=selected.sort_values('sample_hash')
    label='pilot' if pilot else 'full'
    results=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(fetch_one,row,delay) for row in selected.itertuples(index=False)]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results)%(25 if pilot else 100)==0 or len(results)==len(selected):
                frame=pd.DataFrame(results)
                frame.to_parquet(DEST/f'{label}_extractions.parquet',index=False)
                status=dict(scope=label,completed=len(results),selected=len(selected),counts=frame.status.value_counts().to_dict())
                (DEST/f'{label}_progress.json').write_text(json.dumps(status,indent=2)+'\n')
                print(json.dumps(status),flush=True)
    if any(r['status']=='fetch_failed' for r in results):
        raise RuntimeError('Some originals not retrieved; do not treat retrieval failures as no EPS')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',type=int,default=0,help='Reports per year, fixed hash sample, extraction validation only');p.add_argument('--workers',type=int,default=2);p.add_argument('--delay',type=float,default=.5)
    a=p.parse_args();run(a.pilot,a.workers,a.delay)
