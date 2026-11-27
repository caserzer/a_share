"""Archive vendor responses with query clock, response hashes and declared field names."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
import requests
import pandas as pd
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'topics/01_askhare_qlib').exists())
RAW = HERE / 'results' / 'raw'
FUNDS = ['510300.SH','159919.SZ','510500.SH','512100.SH','588000.SH','512800.SH','512880.SH','512010.SH']

def query(api, params, fields=''):
    RAW.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps([api,params,fields],sort_keys=True).encode()).hexdigest()[:22]
    path = RAW / f'{api}-{key}.json.gz'
    if path.exists():
        saved=json.loads(gzip.decompress(path.read_bytes()))
        if "频率超限" not in saved["message"]:
            return saved
    token = dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    sess = requests.Session()
    sess.trust_env = False
    for attempt in range(4):
        resp = sess.post('https://api.tushare.pro',json={'api_name':api,'params':params,'fields':fields,'token':token},timeout=(6,60))
        resp.raise_for_status()
        result = resp.json()
        if '频率超限' in str(result.get('msg') or '') and api.startswith('etf_'):
            time.sleep(62)
            continue
        if result.get('code') in (0,-2001,40203): break
        time.sleep(2+attempt)
    rec=dict(api=api,params=params,fields=fields,observed_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(resp.content).hexdigest(),code=result.get('code'),message=str(result.get('msg') or '').replace(token,'[redacted]'),data=result.get('data') or {})
    if rec['code']==0 or rec['code'] in (-2001,40203):
        tmp=path.with_suffix('.tmp')
        tmp.write_bytes(gzip.compress(json.dumps(rec,ensure_ascii=False).encode(),mtime=0))
        tmp.replace(path)
    return rec

def get_frame(rec):
    data=rec['data']
    return pd.DataFrame(data.get('items') or [], columns=data.get('fields') or [])

def collect(api,prefix,queries,fields='',limit=1000):
    dest=HERE/'results'/f'{prefix}.parquet'
    frames=[]; rows=[]
    for j,p in enumerate(queries):
        for off in range(0,100000,limit):
            rec=query(api,p | dict(offset=off,limit=limit),fields)
            d=get_frame(rec)
            rows.append({k:v for k,v in rec.items() if k!='data'} | dict(rows=len(d)))
            if rec['code']!=0: break
            if len(d): frames.append(d)
            if len(d)<limit: break
        if rec['code'] in (-2001,40203):break
        if j%20==0: print(prefix,j,rec['code'],len(rows),flush=True)
    if frames: pd.concat(frames,ignore_index=True).drop_duplicates().to_parquet(dest,index=False)
    pd.DataFrame(rows).to_json(dest.with_suffix('.jsonl'),orient='records',lines=True,force_ascii=False)

def main(mode):
    mon=pd.date_range('2017-01-01','2026-10-01',freq='MS')
    if mode=='probe':
        for api,params in [('report_rc',dict(report_date='20250605')),('etf_basic',dict(ts_code='510500.SH')),('etf_share_size',dict(ts_code='510500.SH',trade_date='20250605')),('etf_sh_cons',dict(ts_code='510500.SH',trade_date='20250605',limit=2)),('stk_surv',dict(ts_code='300750.SZ',limit=1))]:
            r=query(api,params); print(api,r['code'],get_frame(r).shape,list(get_frame(r)),flush=True)
    if mode=='research':
        collect('report_rc','vendor_analyst',[dict(start_date=t.strftime('%Y%m%d'),end_date=min(t+pd.offsets.MonthEnd(0),pd.Timestamp('2026-10-12')).strftime('%Y%m%d')) for t in mon],fields='ts_code,name,report_date,report_title,org_name,quarter,eps,max_price,min_price',limit=1000)
    if mode=='basis':
        collect('income_vip','accounting_basis',[dict(period=t.strftime('%Y%m%d')) for t in pd.date_range('2016-03-31','2026-09-30',freq='QE')],'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type',limit=2000)
    if mode=='financial':
        for api,cols in [('fina_indicator_vip','ts_code,ann_date,end_date,profit_dedt,update_flag'),('income_vip','ts_code,ann_date,f_ann_date,end_date,report_type,basic_eps,revenue,n_income_attr_p,update_flag'),('forecast_vip','ts_code,ann_date,first_ann_date,end_date,net_profit_min,net_profit_max,type'),('express_vip','ts_code,ann_date,end_date,diluted_eps,n_income,revenue')]:
            periods=[dict(period=t.strftime('%Y%m%d')) for t in pd.date_range('2016-03-31','2026-09-30',freq='QE')]
            collect(api,api,periods,cols,limit=2000)
    if mode=='units':
        for fund in FUNDS:
            collect('etf_bs_'+fund[-2:].lower()+'_detail',f'unit_{fund[:6]}',[dict(ts_code=fund,start_date='20200101',end_date='20261012')],fields='ann_date,trade_date,ts_code,creation_redemption_unit,navpercu,nav',limit=2000)
    if mode=='industry_compact':
        for code in ['512010','512880','512800']:
            fund=code+'.SH'
            for tag,start,end in [('later','2025-02-01','2026-10-12'),('early','2021-01-01','2025-01-31')]:
                months=pd.date_range(start,end,freq='MS')
                collect('etf_sh_cons','compact_'+code+'_'+tag,[dict(ts_code=fund,start_date=t.strftime('%Y%m%d'),end_date=min(t+pd.offsets.MonthEnd(0),pd.Timestamp(end)).strftime('%Y%m%d')) for t in months],limit=2000)
    if mode=='repair1000':
        source=next(HERE.parents[1].glob('36_*/private/market.parquet'))
        dates=pd.read_parquet(source,columns=[]).index
        for tag,start,end in [('later','2025-02-01','2026-10-12'),('early','2021-01-01','2025-01-31')]:
            ds=dates[(dates>=start)&(dates<=end)]
            collect('etf_sh_cons','complete_512100_'+tag,[dict(ts_code='512100.SH',start_date=ds[k].strftime('%Y%m%d'),end_date=ds[min(k+1,len(ds)-1)].strftime('%Y%m%d')) for k in range(0,len(ds),2)],limit=2000)
    if mode=='etfs':
        collect('etf_basic','fund_inventory',[{}],limit=2000)
        for fund in FUNDS:
            code=fund[:6]
            collect('etf_basic',f'basic_{code}',[dict(ts_code=fund)])
            collect('fund_share',f'shares_{code}',[dict(ts_code=fund,start_date='20200101',end_date='20261012')],limit=1000)
            collect('fund_nav',f'nav_{code}',[dict(ts_code=fund,start_date='20200101',end_date='20261012')],limit=1000)
            # Later first to secure a contiguous window representative of each index.
            source=next(HERE.parents[1].glob('36_*/private/market.parquet'))
            dates=pd.read_parquet(source,columns=[]).index
            for year,start,end in [('later','2025-02-01','2026-10-12'),('early','2021-01-01','2025-01-31')]:
                ds=dates[(dates>=start)&(dates<=end)]
                api='etf_'+fund[-2:].lower()+'_cons'
                collect(api,f'basket_{code}_{year}',[dict(ts_code=fund,start_date=ds[k].strftime('%Y%m%d'),end_date=ds[min(len(ds)-1,k+3)].strftime('%Y%m%d')) for k in range(0,len(ds),4)],limit=5000)
if __name__=='__main__':
    import sys
    main(sys.argv[1])
