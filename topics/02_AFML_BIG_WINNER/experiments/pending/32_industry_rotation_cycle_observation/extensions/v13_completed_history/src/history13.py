import numpy as np
import pandas as pd
from context13 import KEY


def prepare(phases):
    p=phases[phases.status.eq('CONFIRMED')&~phases.left_censored].copy()
    p['short']=p.end_date.lt(p.start_date+pd.DateOffset(months=6)).astype(float)
    p['log_duration']=np.log1p(p.duration_days)
    return p


def cumulative(p,dates,bm):
    p=p.sort_values('end_confirmed_at')
    times=p.end_confirmed_at.to_numpy(dtype='datetime64[ns]')
    dates=pd.DatetimeIndex(dates).to_numpy(dtype='datetime64[ns]')
    n=np.searchsorted(times,dates,side='right')
    values={}
    for name,col in [('short','short'),('qualified','qualified_'+bm),('duration','log_duration')]:
        sums=np.r_[0,np.cumsum(p[col].to_numpy(float))]
        values[name]=sums[n]
    values['n']=n
    last_duration=np.full(len(n),np.nan);last_return=last_duration.copy();since=last_duration.copy()
    available=n>0
    if available.any():
        ix=n[available]-1
        last_duration[available]=p.log_duration.to_numpy()[ix]
        last_return[available]=p.industry_return.to_numpy()[ix]
        since[available]=np.log1p((dates[available]-times[ix])/np.timedelta64(1,'D'))
    values.update(last_duration=last_duration,last_return=last_return,since_end=since)
    return values


def add_history(features,phases):
    p=prepare(phases)
    own={k:g for k,g in p.groupby(KEY+['threshold'])}
    globalgroups={k:g for k,g in p.groupby(['level','threshold'])}
    empty=p.iloc[:0];rows=[]
    keys=KEY+['threshold','benchmark']
    for key,g in features.groupby(keys,sort=False):
        bm=key[-1];a=cumulative(own.get(key[:-1],empty),g.date,bm)
        b=cumulative(globalgroups.get((key[1],key[3]),empty),g.date,bm)
        r=g.copy();r['hist_count']=np.log1p(a['n'])
        for name in ['short','qualified','duration']:
            mean=np.divide(b[name],b['n'],out=np.full(len(g),np.nan),where=b['n']>0)
            r['hist_'+name]=(a[name]+10*mean)/(a['n']+10)
        for name in ['last_duration','last_return','since_end']:r['hist_'+name]=a[name]
        rows.append(r)
    return pd.concat(rows,ignore_index=True)
