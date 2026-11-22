"""Seal same-date matches without using future returns or trade flags."""
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from signals import OUT, dump, sha

EXTRA = {'H1':'ordinary','H2':'lag_gap','H3':'plain'}
NAMES = ['H1','H2','H3','ordinary']


def pair(a,b,scaled):
    if not len(a) or not len(b):
        return []
    gaps = scaled[a,None,:] - scaled[b,:]
    ok = (np.abs(gaps) <= 1).all(axis=2)
    dist = np.square(gaps).sum(axis=2)
    penalty = (len(a)+1)*(scaled.shape[1]+1)
    cost = np.column_stack((np.where(ok,dist,2*penalty),np.full((len(a),len(a)),penalty)))
    row,col = linear_sum_assignment(cost)
    return [(a[i],b[j],dist[i,j]) for i,j in zip(row,col) if j < len(b) and ok[i,j]]


def select():
    targets = pd.read_parquet(OUT/'signals.parquet')
    records,coverage = [],[]
    for date,g in targets.groupby('signal_date'):
        g = g.reset_index(drop=True)
        groups = list(g.groupby('industry').indices.values())
        for signal in NAMES:
            vals = g[signal].to_numpy()
            for model in (['base'] if signal=='ordinary' else ['base','controlled']):
                limits = dict(E1_78=.25,mom5=.5,mom20=.5,vol=.5)
                if signal=='H3':
                    limits.update(ret10=.5,turn5=.5)
                if model=='controlled':
                    limits.update(RANK_MSE_78=.5)
                    limits[EXTRA[signal]]=.5
                fields = list(limits)
                scaled = (g[fields]/(g[fields].std(ddof=0)*pd.Series(limits))).to_numpy()
                valid = np.isfinite(scaled).all(axis=1) & np.isfinite(vals)
                buckets = {'pool':[],'boundary':[]}
                dec = g.decile.to_numpy()
                for idx in groups:
                    idx = idx[valid[idx]]
                    if len(idx)<2:
                        continue
                    med = np.median(vals[idx])
                    hi,lo = idx[vals[idx]>med],idx[vals[idx]<med]
                    buckets['pool'].extend(pair(hi,lo,scaled))
                    buckets['boundary'].extend(pair(hi[dec[hi]==9],lo[dec[lo]==10],scaled))
                for scope,matches in buckets.items():
                    coverage.append(dict(signal_date=date,signal=signal,model=model,scope=scope,
                                         eligible=int(valid.sum()),n_pairs=len(matches),top=int(sum(dec==10))))
                    for i,j,dist in matches:
                        records.append(dict(signal_date=date,signal=signal,model=model,scope=scope,
                                            high=g.instrument.iat[i],low=g.instrument.iat[j],
                                            industry=g.industry.iat[i],distance=dist))
    matches = pd.DataFrame(records)
    matches.to_parquet(OUT/'pairs.parquet',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
    dump(OUT/'selection.json',{n:sha(OUT/n) for n in ['signals.parquet','pairs.parquet','coverage.csv','inputs.json']})


if __name__=='__main__':
    select()
