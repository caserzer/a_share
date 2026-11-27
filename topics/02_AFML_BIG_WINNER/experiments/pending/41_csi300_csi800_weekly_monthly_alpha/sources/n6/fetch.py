"""Audit PCF availability on the first frozen signal of each quarter, both exchanges."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import time
import pandas as pd
import requests
from dotenv import dotenv_values

HERE=Path(__file__).resolve().parent
REG=HERE.parents[1]
ROOT=next(p for p in REG.parents if (p/'topics').is_dir())
OUT=HERE/'results'
FUNDS={'510300.SH':'sh','159919.SZ':'sz'}
def main():
    sf=next(REG.parent.glob('40_*/lightgbm/followup/csi800_69/results/scores.parquet'))
    days=pd.DatetimeIndex(pd.read_parquet(sf,columns=['signal_date']).signal_date.unique()).sort_values()
    dates=pd.Series(days).groupby(days.to_period('Q')).first().tolist()
    token=dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    http=requests.Session()
    http.trust_env=False
    receipts=[];data={}
    def request(api,params):
        for attempt in range(3):
            try:
                r=http.post('https://api.tushare.pro',json=dict(api_name=api,token=token,params=params),timeout=(8,25))
                r.raise_for_status()
                raw=r.json();break
            except (requests.RequestException,ValueError):
                if attempt==2:raise
                time.sleep(1+attempt)
        payload=raw.get('data') or {}
        items=payload.get('items') or []
        cols=payload.get('fields') or []
        receipts.append(dict(api=api,params=params,request_id=raw.get('request_id'),observed_at=datetime.now(timezone.utc).isoformat(),
                             status=raw.get('code'),message=str(raw.get('msg') or '').replace(token,'[redacted]'),rows=len(items),fields=cols,
                             response_sha256=hashlib.sha256(r.content).hexdigest()))
        if items:data.setdefault(api,[]).append(pd.DataFrame(items,columns=cols))
    for fund,market in FUNDS.items():
        for api in ['fund_share','fund_nav']:
            for year in range(2020,2027):
                request(api,dict(ts_code=fund,start_date=f'{year}0101',end_date=f'{year}1231' if year<2026 else '20261012'))
        for d in dates:
            params=dict(ts_code=fund,trade_date=d.strftime('%Y%m%d'))
            request(f'etf_{market}_cons',params)
            request(f'etf_bs_{market}_detail',params)
    for api,parts in data.items():
        pd.concat(parts,ignore_index=True).drop_duplicates().to_parquet(OUT/(api+'.parquet'),index=False)
    (OUT/'query_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(receipts).groupby(['api','status']).rows.agg(['count','sum']))
if __name__=='__main__':main()
