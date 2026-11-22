"""Freeze both hypotheses' observable signals and matches before reading outcomes."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EP = ROOT.parents[1]
PREV = EP/'extensions/e1_peer_alpha_20261122'
sys.path.insert(0, str(PREV))
from signals import PRED, PRIVATE, sectors, panels, regress
from matching import pair
from core import assign_deciles, dump, sha

OUT = ROOT/'results'
FIELDS = {'A': ['mom5','pre20','prevol'], 'B':['mom5','relative20','vol']}


def features():
    close=pd.read_parquet(PRIVATE/'qfq_close.parquet')
    days,symbols=close.index,close.columns
    returns=close.pct_change(fill_method=None).to_numpy()
    members=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex_like(close).eq(True).to_numpy()
    ind,codes=sectors(days,symbols)
    peer,_,_=panels(returns,ind,members,np.full_like(returns,np.nan))
    market=np.log(pd.read_parquet(PRIVATE/'market.parquet').close.reindex(days)).diff().to_numpy()
    logstock,logpeer=np.log1p(returns),np.log1p(peer)
    five=close.pct_change(5,fill_method=None).to_numpy()
    pred=pd.read_parquet(PRED).sort_values(['signal_date','instrument'])
    batches=[]
    for date,g in pred.groupby('signal_date'):
        t=days.get_loc(date)
        g=g.copy()
        g['decile']=assign_deciles(g,'E1_78')
        g['mom5']=five[t,symbols.get_indexer(g.instrument)]
        ok=g.dropna(subset=['mom5'])
        g['oversold']=g.index.isin(ok.index[(assign_deciles(ok,'mom5')==1) & (ok.mom5<0)])
        hist=np.arange(t-124,t-4)
        obs=np.arange(t-4,t+1)
        past=np.arange(t-24,t-4)
        days20=np.arange(t-19,t+1)
        known=members[t] & (ind[t]>=0) & np.isfinite(five[t])
        breadth={}
        for k in np.unique(ind[t,known]):
            other=known & (ind[t]!=k)
            breadth[k]=(five[t,other]<0).mean() if other.any() else np.nan
        props=[]
        for s in g.instrument:
            j=symbols.get_loc(s)
            k=ind[t,j]
            y=logstock[:,j]
            d={}
            props.append(d)
            if np.isfinite(y[past]).all():
                d.update(pre20=np.expm1(y[past].sum()),prevol=returns[past,j].std(ddof=1))
            if np.isfinite(y[days20]).all():
                d['vol']=returns[days20,j].std(ddof=1)
            if k<0 or not members[t,j]:
                continue
            same=(ind[:,j]==k)&members[:,j]
            d.update(industry=codes[k],breadth=breadth.get(k,np.nan))
            if same[days20].all() and np.isfinite(y[days20]-logpeer[days20,j]).all():
                diff=y[days20]-logpeer[days20,j]
                d.update(B=int((diff>0).sum()),relative20=diff.sum())
            if not same[obs].all() or not np.isfinite(y[obs]-logpeer[obs,j]-market[obs]).all():
                continue
            X=np.column_stack([np.ones(len(hist)),market[hist],logpeer[hist,j]-market[hist]])
            b=regress(X,y[hist],same[hist])
            if b is not None:
                bm=b[1]*market[obs].sum()
                bi=b[2]*(logpeer[obs,j]-market[obs]).sum()
                drift=5*b[0]
                d.update(A=-bm-bi,market_part=bm,industry_part=bi,drift=drift,
                         residual=y[obs].sum()-bm-bi-drift)
        batches.append(pd.concat([g.reset_index(drop=True),pd.DataFrame(props)],axis=1))
    return pd.concat(batches,ignore_index=True)


def build():
    f=features()
    f.to_parquet(OUT/'signals.parquet',index=False)
    pairs,coverage=[],[]
    for date,g in f.groupby('signal_date'):
        g=g.reset_index(drop=True)
        groups=g.groupby('industry').indices
        for name in FIELDS:
            for model in ['E1','both']:
                limits={'E1_78':.25,**dict.fromkeys(FIELDS[name],.5)}
                if model=='both':
                    limits['RANK_MSE_78']=.5
                data=g[list(limits)]
                scaled=(data/(data.std(ddof=0)*pd.Series(limits))).to_numpy()
                val=g[name].to_numpy()
                ok=np.isfinite(scaled).all(axis=1)&np.isfinite(val)
                if name=='A':
                    ok &= g.oversold & g.breadth.notna()
                for scope in (['pool','D10'] if name=='A' else ['pool','positive','D10']):
                    eligible=ok.copy()
                    if scope=='positive':
                        eligible &= g.relative20.gt(0)
                    if scope=='D10':
                        eligible &= g.decile.eq(10)
                    n=0
                    for industry,idx in groups.items():
                        idx=idx[np.asarray(eligible)[idx]]
                        if len(idx)<2:
                            continue
                        med=np.median(val[idx])
                        for hi,lo,dist in pair(idx[val[idx]>med],idx[val[idx]<med],scaled):
                            n+=1
                            pairs.append(dict(signal_date=date,signal=name,model=model,scope=scope,
                                industry=industry,high=g.instrument.iat[hi],low=g.instrument.iat[lo],
                                breadth=g.breadth.iat[hi],distance=dist))
                    coverage.append(dict(signal_date=date,signal=name,model=model,scope=scope,
                                         eligible=int(eligible.sum()),pairs=n))
    pd.DataFrame(pairs).to_parquet(OUT/'pairs.parquet',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
    files=[OUT/'signals.parquet',OUT/'pairs.parquet',OUT/'coverage.csv',PRED,Path(__file__),ROOT/'PROTOCOL.md',
           ROOT/'evaluate.py',PREV/'signals.py',PREV/'matching.py',EP/'code/core.py',EP/'code/accounts.py',EP/'config.yaml']
    files.extend(PRIVATE/(s+'.parquet') for s in ['qfq_close','industry','daily_members','market','open','qfq_open',
                                                  'opening_trade_status_v2','limits/daily','suspensions/daily'])
    dump(OUT/'selection.json',{str(p.relative_to(EP.parent)):sha(p) for p in files})


if __name__=='__main__':
    build()
