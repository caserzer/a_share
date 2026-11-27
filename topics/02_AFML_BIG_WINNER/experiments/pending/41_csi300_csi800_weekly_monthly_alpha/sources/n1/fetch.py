"""Fetch historical minute bars for the CSI300 reserve on three predetermined intervals."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import pandas as pd
import requests
from dotenv import dotenv_values

HERE=Path(__file__).resolve().parent
EP=HERE.parents[1];PENDING=EP.parent;ROOT=EP.parents[4]
EP40=next(PENDING.glob('40_*'))
CAL=next(PENDING.glob('36_*/private/close.parquet'))
# Earliest 3 full calendar months after each registered strict P1 segment starts.
RANGES=[('2021-02-01','2021-04-30'),('2023-07-03','2023-09-28'),('2025-04-01','2025-06-30')]
CACHE=HERE/'cache'
def queries():
    d=pd.read_parquet(EP40/'lightgbm/followup/results/daily_scores.parquet',columns=['entry_idx','instrument','R'])
    days=pd.read_parquet(CAL,columns=[]).index
    needs={}
    for start,end in RANGES:
        i,j=days.get_indexer([start,end]);assert min(i,j)>=0
        for e,g in d[d.entry_idx.between(i,j-10)].groupby('entry_idx'):
            r=g.sort_values(['R','instrument'],ascending=False);k=len(r)//10
            for sym in r.instrument.iloc[k:2*k]:
                needs.setdefault(sym,set()).update(range(e-20,e))
    todo=[]
    for sym,dates in needs.items():
        dates=sorted(dates)
        while dates:
            a=dates[0];last=np.searchsorted(dates,a+28)
            b=dates[last-1];dates=dates[last:]
            todo.append((sym,days[a].strftime('%Y-%m-%d'),days[b].strftime('%Y-%m-%d')))
    return sorted(todo)

def pilot_queries():
    days=pd.read_parquet(CAL,columns=[]).index
    adv=pd.read_parquet(CAL.with_name("money.parquet")).rolling(20,min_periods=20).mean()
    d=pd.read_parquet(EP40/"lightgbm/followup/results/daily_scores.parquet",columns=["instrument","R","entry_idx","vol20","mom5"])
    picks=[]
    for start,end in RANGES:
        e=days.get_loc(pd.Timestamp(start));g=d[d.entry_idx==e].sort_values(["R","instrument"],ascending=False).copy()
        g["adv"]=adv.iloc[e-1].reindex(g.instrument).to_numpy()
        f=["adv","vol20","mom5"];g[f]=g[f].rank(pct=True)
        k=len(g)//10;n=k//5;p=g.iloc[k:2*k]
        options=[]
        for slot in range(n):
            diff=abs(p.iloc[n:][f]-p.iloc[slot][f])
            valid=diff[(diff<=.20).all(axis=1)]
            for idx,dist in valid.sum(axis=1).items():
                options.append((slot,dist,p.instrument.iloc[slot],p.loc[idx,"instrument"]))
        slot,dist,first,other=min(options)
        picks.append(dict(start=start,end=end,entry_idx=e,buy_slot=slot+1,original=first,alternative=other,style_distance=dist))
    pd.DataFrame(picks).to_csv(HERE/"pilot_design.csv",index=False)
    # Each request covers the 20-session lookback and the first eight subsequent
    # signals, up to 28*241 observations, below the API's 8000 limit.
    return [(s,days[e-20].strftime("%Y-%m-%d"),days[e+7].strftime("%Y-%m-%d")) for r in picks for e in [r["entry_idx"]] for s in [r["original"],r["alternative"]]]

def main():
    import sys
    dates=queries() if "--full" in sys.argv else pilot_queries()
    if "--one" in sys.argv:dates=dates[:1]
    print('requests',len(dates),flush=True)
    CACHE.mkdir(exist_ok=True)
    token=dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    session=requests.Session();session.trust_env=False
    last_request=None
    def fetch(q):
        nonlocal last_request
        sym,a,b=q;print(sym,a,b,flush=True);key=f'{sym}_{a}_{b}'
        rec=CACHE/(key+'.json');packed=CACHE/(key+'.parquet')
        if rec.exists() and packed.exists():
            meta=json.loads(rec.read_text())
            if hashlib.sha256(packed.read_bytes()).hexdigest()==meta['normalized_sha256']:return meta
        if last_request is not None:
            time.sleep(max(0.,62-(time.monotonic()-last_request)))
        params=dict(ts_code=sym[2:]+'.'+sym[:2],freq='1min',start_date=a+' 09:00:00',end_date=b+' 16:00:00')
        for attempt in range(10):
            try:
                last_request=time.monotonic()
                response=session.post('https://api.tushare.pro',json=dict(api_name='stk_mins',token=token,params=params,fields='ts_code,trade_time,open,close,vol,amount'),timeout=(10,40))
                response.raise_for_status();raw=response.json()
                if raw['code']!=0:
                    message=str(raw.get('msg','')).replace(token,'REDACTED')
                    print(message,flush=True)
                    with (CACHE/'provider_errors.jsonl').open('a') as log:
                        log.write(json.dumps(dict(query=params,utc=pd.Timestamp.now(tz='UTC').isoformat(),code=raw['code'],message=message),ensure_ascii=False)+'\n')
                    if '--one' in sys.argv:raise RuntimeError('sample denied')
                    if '分钟' in str(raw.get('msg')) and '次' in str(raw.get('msg')):time.sleep(60);continue
                    raise RuntimeError('provider code '+str(raw['code']))
                break
            except requests.RequestException:
                if attempt==9:raise
                time.sleep(min(2**attempt,20))
        else:raise RuntimeError('provider frequency limit persisted')
        f=pd.DataFrame(raw['data']['items'],columns=raw['data']['fields'])
        assert len(f)<8000 and not f.trade_time.duplicated().any() and (f.ts_code==params['ts_code']).all()
        daily=[]
        for dt,g in f.groupby(f.trade_time.str[:10]):
            g=g.sort_values('trade_time')
            hhmm=g.trade_time.str.slice(11,16)
            rows=g[((hhmm>'09:30')&(hhmm<='11:30'))|((hhmm>'13:00')&(hhmm<='15:00'))]
            if len(rows)!=240 or rows.iloc[-1].trade_time[11:16]!='15:00' or (rows[['open','close']]<=0).any().any():continue
            px=rows.close.to_numpy(float);amount=rows.amount.to_numpy(float);volume=rows.vol.to_numpy(float)
            if amount.sum()<=0 or volume.sum()<=0:continue
            # Start afternoon at its own opening, omit lunch/overnight jumps; zero-volume bars have no return.
            ret=np.diff(np.log(px),prepend=np.log(rows.open.iloc[0]));ret[120]=np.log(px[120]/rows.open.iloc[120])
            ret[volume==0]=0.
            daily.append(dict(instrument=sym,date=dt,negative_ss=(np.minimum(ret,0)**2).sum(),sum_ss=(ret**2).sum(),
                sum_r=ret.sum(),sum_cube=(ret**3).sum(),n=len(ret),up_amount=amount[ret>0].sum(),amount=amount.sum(),
                vwap_gap=px[-1]/(amount.sum()/volume.sum())-1,open30=px[29]/rows.open.iloc[0]-1,
                ret_volume_corr=np.corrcoef(ret,volume)[0,1] if ret.std()>0 and volume.std()>0 else np.nan))
        pd.DataFrame(daily,columns='instrument date negative_ss sum_ss sum_r sum_cube n up_amount amount vwap_gap open30 ret_volume_corr'.split()).to_parquet(packed,index=False)
        meta=dict(params=params,raw_rows=len(f),verified_days=len(daily),raw_sha256=hashlib.sha256(response.content).hexdigest(),normalized_sha256=hashlib.sha256(packed.read_bytes()).hexdigest(),
            acquired_at=pd.Timestamp.now(tz='UTC').isoformat())
        rec.write_text(json.dumps(meta,indent=2)+'\n')
        return meta
    results=[]
    for i,q in enumerate(dates,1):
        row=fetch(q);results.append(row)
        print(i,len(dates),row['raw_rows'],row['verified_days'],flush=True)
    pd.DataFrame(results).to_json(HERE/'receipts.jsonl',orient='records',lines=True)
if __name__=='__main__':main()
