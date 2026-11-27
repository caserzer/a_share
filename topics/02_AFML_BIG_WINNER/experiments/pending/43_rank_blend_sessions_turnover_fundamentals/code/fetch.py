"""Add historical statement and daily capitalization observations to the local proxy archive."""
from pathlib import Path
import sys,os,time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
ep42=next(ROOT.parent.glob('42_*'))
sys.path.insert(0,str(ep42/'events'))
import fetch_sources as vendor
dest=ROOT/'outputs'/'sources'
dest.mkdir(parents=True,exist_ok=True)
vendor.RAW=dest/'raw'
def collect(task):
    api,key,params,cols=task
    file=dest/(key+'.parquet')
    if file.exists():return
    frames=[]
    for off in range(0,24000,2000):
        for attempt in range(8):
            result=vendor.query(api,{**params,'offset':off,'limit':2000},cols)
            if result['code']==0:break
            if result['code']!=40203:break
            time.sleep(62)
        if result['code']!=0:raise RuntimeError((api,result['code'],result['message']))
        df=vendor.get_frame(result)
        frames.append(df)
        if len(df)<2000:break
    df=pd.concat(frames,ignore_index=True)
    tmp=file.with_suffix('.tmp')
    df.to_parquet(tmp,index=False);tmp.replace(file)
if __name__=='__main__':
    tasks=[]
    for q in pd.period_range('2013Q1','2026Q3',freq='Q'):
        for api,fields in [('income_vip','revenue,oper_cost,n_income_attr_p'),('balancesheet_vip','total_hldr_eqy_exc_min_int'),('cashflow_vip','n_cashflow_act')]:
            tasks.append((api,api+'_'+str(q),dict(period=q.end_time.strftime('%Y%m%d')),'ts_code,end_date,ann_date,f_ann_date,report_type,comp_type,update_flag,'+fields))
    names=pd.read_parquet(Path.home()/'.cache/a_share/ep38_three_track/market/close.parquet',columns=[]).index
    # Per security, 3 chronological pages at most; include exited constituents.
    import pyarrow.parquet as pq
    syms=pq.ParquetFile(Path.home()/'.cache/a_share/ep38_three_track/market/close.parquet').schema_arrow.names
    for j in syms:
        if j[:2] not in ('SH','SZ','BJ'):continue
        tasks.append(('daily_basic','cap_'+j,dict(ts_code=j[2:]+'.'+j[:2],start_date='20170101',end_date='20261012'),'ts_code,trade_date,total_mv'))
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i,_ in enumerate(ex.map(collect,tasks)):
            if i%100==0:print(i,len(tasks),flush=True)
