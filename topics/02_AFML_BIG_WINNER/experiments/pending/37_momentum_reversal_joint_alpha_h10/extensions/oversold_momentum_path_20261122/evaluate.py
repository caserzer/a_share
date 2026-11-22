"""Evaluate frozen candidates on the existing H10 execution calendar."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from freeze import OUT, EP, PRIVATE, FIELDS, sha, dump
from core import bootstrap, holm, clean
import accounts

MAIN=pd.Timestamp('2025-03-03')
END=pd.Timestamp('2026-10-12')


def basket(m,g,weights=None):
    return accounts.event(m,g.assign(weight=1/len(g) if weights is None else weights),.001,.002)[0]['net_return']


def partial_ic(g,model):
    cols=['E1_78']+FIELDS['B']+(['RANK_MSE_78'] if model=='both' else [])
    v=g.dropna(subset=cols+['B','industry','quoted'])
    v=v[v.groupby('industry').instrument.transform('size')>=2]
    if v.empty:
        return np.nan
    ranks=v[['B','quoted']+cols].rank()
    within=ranks-ranks.groupby(v.industry).transform('mean')
    X,Y=within[cols].to_numpy(),within[['B','quoted']].to_numpy()
    coef,_,rank,_=np.linalg.lstsq(X,Y,rcond=None)
    res=Y-X@coef
    if len(v)-v.industry.nunique()-rank<12 or res.std(axis=0).min()<1e-10:
        return np.nan
    return np.corrcoef(res.T)[0,1]


def fit_slope(p,dates,ycol):
    v=p[['signal_date','breadth',ycol]].dropna().copy()
    v['x2']=v.breadth**2
    v['xy']=v.breadth*v[ycol]
    moments=v.groupby('signal_date')[['breadth',ycol,'x2','xy']].mean().reindex(dates).to_numpy()
    n=len(moments)
    def compute(a):
        count=np.isfinite(a[...,0]).sum(axis=-1)
        avg=np.nansum(a,axis=-2)/np.maximum(count[...,None],1)
        x,y,xx,xy=avg.T
        denom=xx-x*x
        return np.divide(.1*(xy-x*y),denom,out=np.full_like(x,np.nan),where=denom>1e-12)
    mean=compute(moments[None])[0]
    valid=np.isfinite(moments[:,0]).sum()
    result=dict(mean=mean,n=valid,calendar_n=n,low=np.nan,high=np.nan,p=np.nan)
    if valid<12 or not np.isfinite(mean):
        return result
    rng=np.random.default_rng(20261118)
    starts=rng.integers(0,n,size=(2000,int(np.ceil(n/6))))
    idx=((starts[:,:,None]+np.arange(6))%n).reshape(2000,-1)[:,:n]
    slopes=compute(moments[idx])
    slopes=slopes[np.isfinite(slopes)]
    result.update(low=np.quantile(slopes,.025),high=np.quantile(slopes,.975),
                  p=(1+(np.abs(slopes-mean)>=abs(mean)).sum())/(1+len(slopes)))
    return result


def distribution(z):
    rows=[]
    for key,v in z.groupby(['period','leg','regime']):
        good=v.dropna(subset=['net'])
        if good.empty:
            continue
        # Equal date weight, equal weight per stock inside date. Fractional mass at ES boundary.
        w=1/good.groupby('signal_date').net.transform('size').to_numpy()/good.signal_date.nunique()
        order=np.argsort(good.net.to_numpy())
        a=good.net.to_numpy()[order]
        w=w[order]
        cum=np.cumsum(w)
        bottom=np.minimum(w,np.maximum(.1-(cum-w),0))
        rows.append(dict(zip(['period','leg','regime'],key),dates=good.signal_date.nunique(),
            observations=len(good),unknown=len(v)-len(good),mean=w@a,median=a[np.searchsorted(cum,.5)],
            loss_fraction=w@(a<0),worst_tenth=(bottom@a)/.1))
    return pd.DataFrame(rows)


def evaluate():
    sealed=json.loads((OUT/'selection.json').read_text())
    assert all(sha(EP.parent/path)==value for path,value in sealed.items())
    with TemporaryDirectory() as tmp:
        accounts.OUT=Path(tmp)
        m=accounts.Market()
    index_open=pd.read_parquet(PRIVATE/'market.parquet').open.reindex(m.days)
    f=pd.read_parquet(OUT/'signals.parquet')
    p=pd.read_parquet(OUT/'pairs.parquet')
    keys=['signal_date','signal','model','scope']
    pairmap=dict(tuple(p.groupby(keys)))
    cov=pd.read_csv(OUT/'coverage.csv',parse_dates=['signal_date'])
    dates=dict(tuple(cov.groupby('signal_date')))
    event_rows,details,tail,baseline,positions=[],[],[],[],[]
    for date,g in f.groupby('signal_date'):
        g=g.set_index('instrument',drop=False).copy()
        e,x=int(g.entry_idx.iloc[0]),int(g.exit_idx.iloc[0])
        if x>=len(m.days) or m.days[x]>END:
            continue
        assert m.days[e-1]==date and x-e==10 and (g.fit_cutoff<date).all()
        per='main' if m.days[x]<=MAIN else 'later'
        idx=m.symbols.get_indexer(g.instrument)
        assert (idx>=0).all()
        buy=m.buy[e,idx]&m.members[e-1,idx]
        sell=m.sell[x,idx]
        g['quoted']=m.o[x,idx]/m.o[e,idx]-1
        g['net']=np.where(~buy,0,np.where(sell,(1+g.quoted)*.998/1.001-1,np.nan))
        top=g[g.decile==10]
        base=basket(m,top)
        over=g[g.oversold]
        stock=over[['signal_date','instrument','breadth','net']].copy()
        stock['leg']='all_oversold'
        stock['period']=per
        tail.append(stock)
        baseline.append(dict(signal_date=date,exit_date=m.days[x],period=per,e1=base,oversold=basket(m,over),
           oversold_n=len(over),index_return=index_open.iloc[x]/index_open.iloc[e]-1,
           blocked_buy=int((~buy[g.oversold]).sum()),blocked_exit=int((buy & ~sell)[g.oversold].sum())))
        for row in dates[date].itertuples():
            s,model,scope=row.signal,row.model,row.scope
            pm=pairmap.get((date,s,model,scope))
            rec=dict(signal_date=date,period=per,signal=s,model=model,scope=scope,pairs=row.pairs,
                     eligible=row.eligible,high=np.nan,low=np.nan,spread=np.nan,ic=np.nan,
                     tilt_net=np.nan,tilt_delta=np.nan,tilt_budget=np.nan)
            if s=='B' and scope=='pool':
                rec['ic']=partial_ic(g,model)
            if pm is not None:
                h,l=g.loc[pm.high],g.loc[pm.low]
                rec['high'],rec['low']=basket(m,h),basket(m,l)
                rec['spread']=rec['high']-rec['low']
                d=pm.copy()
                d['period']=per
                d['high_net'],d['low_net']=h.net.to_numpy(),l.net.to_numpy()
                d['diff']=d.high_net-d.low_net
                details.append(d)
                if (s,model,scope)==('A','both','pool'):
                    for label,leg in [('common',h),('specific',l)]:
                        z=leg[['signal_date','instrument','breadth','net']].copy()
                        z['net']=z.net.where(d['diff'].notna().to_numpy())
                        z['leg']=label
                        z['period']=per
                        tail.append(z)
            if s=='B' and scope=='D10':
                w=pd.Series(1/len(top),index=top.index)
                if pm is not None:
                    w.loc[pm.high]+=.5/len(top)
                    w.loc[pm.low]-=.5/len(top)
                assert np.isclose(w.sum(),1)
                industry_weights=w.groupby(top.industry.fillna('UNKNOWN')).sum()
                original=(w*0+1/len(w)).groupby(top.industry.fillna('UNKNOWN')).sum()
                assert np.allclose(industry_weights,original)
                alt=basket(m,top,w)
                rec.update(tilt_net=alt,tilt_delta=alt-base,tilt_budget=.5*row.pairs/len(top))
                if model=='both':
                    positions.append(top[['signal_date','instrument','industry']].assign(
                        e1_weight=1/len(top),tilt_weight=w))
            event_rows.append(rec)
    ev=pd.DataFrame(event_rows)
    ds=pd.concat(details,ignore_index=True)
    base=pd.DataFrame(baseline)
    tails=pd.concat(tail,ignore_index=True)
    regimes=np.select([tails.breadth<=.5,tails.breadth>.5],['narrow','broad'],default='unknown')
    distribution(pd.concat([tails.assign(regime='all'),tails.assign(regime=regimes)])).to_csv(OUT/'tail_summary.csv',index=False)
    tails.assign(regime=regimes).to_parquet(OUT/'oversold_stock_outcomes.parquet',index=False)
    pd.concat(positions).to_csv(OUT/'d10_holdings.csv.gz',index=False)
    ds.to_parquet(OUT/'pair_outcomes.parquet',index=False)
    ev.to_csv(OUT/'events.csv',index=False)
    base.to_csv(OUT/'baseline.csv',index=False)
    stats=[]
    for (per,s,model,scope),v in ev.groupby(['period','signal','model','scope']):
        key=dict(period=per,signal=s,model=model,scope=scope)
        metrics=['spread']
        if s=='B' and scope=='pool':
            metrics+=['ic']
        if s=='B' and scope=='D10':
            metrics+=['tilt_delta']
        for metric in metrics:
            stats.append(dict(**key,metric=metric,**bootstrap(v[metric])))
        if s=='A' and scope=='pool':
            group=ds[(ds.period==per)&(ds.signal==s)&(ds.model==model)&(ds.scope==scope)].dropna(subset=['diff'])
            for col in ['diff','high_net','low_net']:
                stats.append(dict(**key,metric='slope_'+col,**fit_slope(group,v.signal_date,col)))
    stats=pd.DataFrame(stats)
    main=(stats.period=='main')&(stats.model=='both')&(stats.scope=='pool')
    primary=main&(((stats.signal=='A')&(stats.metric=='slope_diff'))|((stats.signal=='B')&(stats.metric=='spread')))
    assert primary.sum()==2
    stats.loc[primary,'holm_p']=holm(stats.loc[primary,'p'])
    stats.to_csv(OUT/'statistics.csv',index=False)


if __name__=='__main__':
    evaluate()
