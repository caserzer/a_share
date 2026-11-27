"""Retrospective search for publication clocks at every head-target opening suspension."""
from pathlib import Path
import pandas as pd
import requests,json,hashlib
from datetime import datetime,timezone
from dotenv import dotenv_values
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
ROOT=next(p for p in HERE.parents if (p/'topics').is_dir())
MARKET=Path.home()/'.cache/a_share/ep38_three_track/market'
def main():
    t=pd.read_parquet(OUT/'targets.parquet').query("arm=='baseline'").explode('targets')
    days=pd.read_parquet(MARKET/'close.parquet',columns=[]).index
    t['execution_date']=days[t.entry_idx]
    t['signal_date']=days[t.entry_idx-1]
    v=pd.read_parquet(MARKET/'suspensions/daily.parquet').query('suspend_type=="S"')
    v['targets']=v.ts_code.str[-2:]+v.ts_code.str[:6];v['execution_date']=pd.to_datetime(v.trade_date)
    events=t.merge(v,on=['execution_date','targets'])
    events[['signal_date','execution_date','targets','suspend_timing']].to_csv(OUT/'observed_suspensions.csv',index=False)
    token=dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    http=requests.Session();http.trust_env=False
    log=[];rows=[]
    for e in events.itertuples():
        q=dict(ts_code=e.ts_code,start_date=(e.signal_date-pd.Timedelta(days=14)).strftime('%Y%m%d'),end_date=e.execution_date.strftime('%Y%m%d'))
        r=http.post('https://api.tushare.pro',json=dict(api_name='anns_d',token=token,params=q,fields='ann_date,ts_code,title,url,rec_time'),timeout=(8,30))
        r.raise_for_status();raw=r.json();p=raw.get('data') or {}
        records=p.get('items',[])
        log.append(dict(api='anns_d',params=q,status=raw.get('code'),message=(raw.get('msg') or '').replace(token,'[redacted]'),
                        rows=len(records),fields=p.get('fields'),observed_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(r.content).hexdigest()))
        if records:rows.append(pd.DataFrame(records,columns=p['fields']).assign(execution_date=e.execution_date,signal_date=e.signal_date))
    if rows:pd.concat(rows).to_csv(OUT/'issuer_announcements.csv',index=False)
    (OUT/'announcement_queries.json').write_text(json.dumps(log,indent=2,ensure_ascii=False)+'\n')
    print(pd.DataFrame(log).groupby('status').rows.agg(['size','sum']))
if __name__=='__main__':main()
