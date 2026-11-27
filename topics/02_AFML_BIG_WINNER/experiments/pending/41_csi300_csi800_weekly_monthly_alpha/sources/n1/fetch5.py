"""Download BaoStock 5-minute bars for every historical reserve in each fixed pilot interval."""
from pathlib import Path
import json,socket,hashlib,time
import numpy as np
import pandas as pd
import baostock as bs
from fetch import CAL,EP40,HERE,RANGES

def aggregate(f,sym):
    if f.empty:return pd.DataFrame()
    assert not f.time.duplicated().any() and f.code.eq(sym[:2].lower()+'.'+sym[2:]).all()
    f=f.sort_values('time').copy()
    f[['open','close','volume','amount']]=f[['open','close','volume','amount']].apply(pd.to_numeric,errors='coerce')
    hh=f.time.str.slice(8,12)
    grid={d.strftime('%H%M') for a,b in [('09:35','11:30'),('13:05','15:00')] for d in pd.date_range('2000-01-01 '+a,'2000-01-01 '+b,freq='5min')}
    assert len(grid)==48
    f=f[hh.isin(grid)&f.open.gt(0)&f.close.gt(0)&f.amount.notna()&f.volume.notna()].copy()
    valid=f.groupby('date').size().eq(48)
    f=f[f.date.isin(valid[valid].index)]
    if f.empty:return pd.DataFrame()
    g=f.groupby('date',sort=False);prev=g.close.shift()
    first=f.time.str[8:12].isin(['0935','1305'])
    ret=np.log(f.close/prev.where(~first,f.open)).where(f.volume>0,0.)
    f['r']=ret;f['sum_ss']=ret**2;f['negative_ss']=ret.clip(upper=0)**2;f['sum_cube']=ret**3
    f['up_amount']=f.amount.where(ret>0,0);f['rv']=ret*f.volume;f['vv']=f.volume**2
    a=g.agg(negative_ss=('negative_ss','sum'),sum_ss=('sum_ss','sum'),sum_r=('r','sum'),sum_cube=('sum_cube','sum'),n=('r','size'),
        amount=('amount','sum'),up_amount=('up_amount','sum'),volume=('volume','sum'),vv=('vv','sum'),rv=('rv','sum'),last=('close','last'),opening=('open','first'))
    a['open30']=f[f.time.str[8:12]=='1000'].set_index('date').close/a.opening-1
    a['vwap_gap']=a['last']/(a.amount/a.volume)-1
    a['ret_volume_corr']=(a.rv-a.sum_r*a.volume/a.n)/np.sqrt((a.sum_ss-a.sum_r**2/a.n)*(a.vv-a.volume**2/a.n)).replace(0,np.nan)
    return a[a.amount.gt(0)&a.volume.gt(0)].reset_index().assign(instrument=sym)

def main():
    dates=pd.read_parquet(CAL,columns=[]).index
    d=pd.read_parquet(EP40/'lightgbm/followup/results/daily_scores.parquet',columns=['instrument','R','entry_idx'])
    todo=[]
    import sys
    segments=RANGES if len(sys.argv)==1 else [RANGES[int(sys.argv[1])-1]]
    for a,b in segments:
        i,j=dates.get_indexer([a,b]);needs={}
        for e,g in d[d.entry_idx.between(i,j-10)].groupby('entry_idx'):
            k=len(g)//10
            for sym in g.sort_values(['R','instrument'],ascending=False).instrument.iloc[k:2*k]:
                needs.setdefault(sym,[]).append(e)
        for sym,e in sorted(needs.items()):
            todo.append((sym,str(dates[min(e)-20].date()),str(dates[max(e)-1].date())))
    print('5min requests',len(todo),flush=True)
    store=HERE/'five_minute_parts';store.mkdir(exist_ok=True)
    socket.setdefaulttimeout(30)
    login=bs.login();assert login.error_code=='0',login.error_msg
    recs=[];frames=[]
    try:
        for num,(sym,a,b) in enumerate(todo,1):
            key=sym+'_'+a+'_'+b
            receipt=store/(key+'.json');out=store/(key+'.parquet')
            if not(receipt.exists() and out.exists()):
                args=dict(start_date=a,end_date=b,frequency='5',adjustflag='3')
                for attempt in range(3):
                    q=bs.query_history_k_data_plus(sym[:2].lower()+'.'+sym[2:],'date,time,code,open,close,volume,amount',**args)
                    rows=[]
                    while q.error_code=='0' and q.next():rows.append(q.get_row_data())
                    if q.error_code=='0':break
                    if attempt==2:raise RuntimeError((sym,a,b,q.error_code,q.error_msg))
                    time.sleep(2);login=bs.login();assert login.error_code=='0',login.error_msg
                raw=pd.DataFrame(rows,columns=q.fields)
                f=aggregate(raw,sym); f.to_parquet(out,index=False)
                record=dict(instrument=sym,query=args,rows=len(raw),days=len(f),raw_fields=q.fields,raw_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),normalized_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),acquired_at=pd.Timestamp.now(tz='UTC').isoformat())
                receipt.write_text(json.dumps(record)+'\n')
            rec=json.loads(receipt.read_text());assert rec['normalized_sha256']==hashlib.sha256(out.read_bytes()).hexdigest()
            recs.append(rec);frames.append(pd.read_parquet(out))
            if num%50==0:print(num,'/',len(todo),flush=True)
    finally:bs.logout()
    if len(sys.argv)>1:return
    agg=pd.concat(frames,ignore_index=True)
    assert not agg.duplicated(['date','instrument']).any()
    agg.to_parquet(HERE/'five_minute_daily.parquet',index=False)
    pd.DataFrame(recs).to_json(HERE/'five_minute_receipts.jsonl',orient='records',lines=True)
if __name__=='__main__':main()
