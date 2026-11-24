from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib, json, time
import pandas as pd
import requests
from dotenv import dotenv_values
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
CACHE=Path.home()/'.cache/a_share/ep38_three_track'
CACHE.mkdir(parents=True,exist_ok=True)
repo=next(p for p in HERE.parents if (p/'topics/01_askhare_qlib/.env').is_file())
token=dotenv_values(repo/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']

def fetch(job):
    api,tag,params=job
    path=CACHE/(tag+'.json')
    if not path.exists():
        for retry in range(4):
            try:
                r=requests.post('https://api.tushare.pro',json=dict(api_name=api,params=params,token=token,fields=''),timeout=(10,45))
                r.raise_for_status();data=r.json()
                if data['code']!=0: raise ValueError((api,tag,data['code']))
                path.write_bytes(r.content);break
            except (requests.RequestException,ValueError):
                if retry==3:raise
                time.sleep(2+retry*2)
    raw=path.read_bytes()
    d=json.loads(raw)['data'];f=pd.DataFrame(d['items'],columns=d['fields'])
    assert len(f)<5000 or api=='stk_limit'
    return f,dict(api=api,tag=tag,params=params,rows=len(f),sha256=hashlib.sha256(raw).hexdigest())

def acquire(jobs,name):
    with ThreadPoolExecutor(4) as pool: data=list(pool.map(fetch,jobs))
    (OUT/(name+'_receipts.json')).write_text(json.dumps([r for _,r in data],indent=2))
    rows=pd.concat([d for d,_ in data],ignore_index=True).drop_duplicates()
    rows.to_parquet(OUT/(name+'.parquet'),index=False)
    return rows

if __name__=='__main__':
    jobs=[('index_weight','800_'+str(m),dict(index_code='000906.SH',start_date=m.start_time.strftime('%Y%m%d'),end_date=m.end_time.strftime('%Y%m%d'))) for m in pd.period_range('2016-12','2026-11',freq='M')]
    wt=acquire(jobs,'weights800')
    acquire([('index_daily','H00906',dict(ts_code='H00906.CSI',start_date='20210101',end_date='20261012'))],'index800')
    private=next(HERE.parents[1].glob('36_*'))/'private'
    old=pd.read_parquet(private/'limits/daily.parquet',columns=['ts_code'])
    missing=sorted(set(wt.con_code)-set(old.ts_code))
    acquire([('stk_limit','limit_'+s,dict(ts_code=s,start_date='20170101',end_date='20261021')) for s in missing],'limits800')
