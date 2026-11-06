"""Online turning-state computation: no labels, future prices or ex-post phases."""
import numpy as np
import pandas as pd
from context7 import ROOT,CACHE,OLD,OUT,KEY,THRESHOLDS,BENCHMARKS,sha,js,freeze


def trace(prices,dates,threshold):
    p=np.asarray(prices,float);dates=pd.DatetimeIndex(dates)
    assert np.isfinite(p).all() and (p>0).all() and 0<threshold<1
    cutoff=dates-pd.DateOffset(months=3)
    direction=0;low=high=previous_high=0;start=confirmed=None;left=True;rows=[]
    for i in range(len(p)):
        if i:
            if direction==0:
                if p[i]<p[low]:low=i
                if p[i]>p[high]:high=i
                if p[i]/p[low]-1>=threshold-1e-12:
                    direction=1;start=low;confirmed=i;high=i;left=True
                elif 1-p[i]/p[high]>=threshold-1e-12:
                    direction=-1;previous_high=high;low=i;left=False
            elif direction==-1:
                if p[i]<p[low]:low=i
                if p[i]/p[low]-1>=threshold-1e-12:
                    direction=1;start=low;confirmed=i;high=i;left=False
            else:
                if p[i]>p[high]:high=i
                if 1-p[i]/p[high]>=threshold-1e-12:
                    direction=-1;previous_high=high;low=i;left=False
        a=start if direction==1 else low
        age=(dates[i]-dates[a]).days
        eligible=direction!=0 and not(direction==1 and left) and dates[a]>cutoff[i]
        rows.append(dict(date=dates[i],candidate_low_date=dates[a],state_direction=direction,
            state_left=int(left),state_age=age/90.,
            state_confirm_age=(dates[i]-dates[confirmed]).days/90. if direction==1 else -1.,
            state_drawup=p[i]/p[a]-1,state_drawdown=p[i]/p[high]-1,
            state_previous_decline=p[a]/p[previous_high]-1,state_eligible=int(eligible),
            start_confirmed_at=dates[confirmed] if direction==1 else pd.NaT))
    return pd.DataFrame(rows)


def build():
    freeze()
    daily=pd.read_parquet(OLD/'daily_industries.parquet')
    f=pd.read_parquet(OLD/'features.parquet');f=f[f.features_ready]
    groups={k:g for k,g in f.groupby(KEY+['block'])}
    rows=[]
    for key,g in daily.groupby(KEY+['block'],sort=False):
        if key not in groups:continue
        g=g.sort_values('date');obs=groups[key][['row_id','date']]
        for threshold in THRESHOLDS:
            r=trace(g.nav,g.date,threshold).merge(obs,on='date',validate='one_to_many')
            r['threshold']=threshold
            for c,v in zip(KEY+['block'],key):r[c]=v
            rows.append(r)
    s=pd.concat(rows,ignore_index=True)
    for bm in BENCHMARKS:
        close=pd.read_parquet(OLD/f'{bm}.parquet').close
        s['state_market_'+bm]=s.date.map(close)/s.candidate_low_date.map(close)-1
    assert not s.duplicated(['row_id','threshold']).any()
    path=CACHE/'state_features.parquet';s.to_parquet(path,index=False)
    inputs=[OLD/'daily_industries.parquet',OLD/'features.parquet',OLD/'stage_b_labels.parquet']+[OLD/f'{bm}.parquet' for bm in BENCHMARKS]
    js(OUT/'state_receipt.json',dict(path=str(path),sha256=sha(path),rows=len(s),
        code_sha256=sha(__file__),inputs={str(p):sha(p) for p in inputs},
        excludes=['future prices','ex-post phases','label values'],features=s.columns.tolist()))
    print('Online state features',len(s),flush=True)


if __name__=='__main__':build()
