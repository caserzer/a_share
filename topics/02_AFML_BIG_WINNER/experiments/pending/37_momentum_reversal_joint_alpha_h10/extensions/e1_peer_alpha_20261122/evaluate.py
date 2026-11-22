"""Strict H10 event comparisons for frozen pairs and E1 D10 substitutions."""
import json
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from matching import NAMES
from signals import OUT, EP, ROOT, sha, dump
import accounts
from core import bootstrap, holm

MAIN = pd.Timestamp('2025-03-03')
END = pd.Timestamp('2026-10-12')


def leg(m,g):
    return accounts.event(m,g.assign(weight=1/len(g)),.001,.002)[0]


def evaluate():
    sealed=json.loads((OUT/'selection.json').read_text())
    assert all(sha(OUT/n)==digest for n,digest in sealed.items())
    with TemporaryDirectory() as tmp:
        accounts.OUT=ROOT.__class__(tmp)
        m=accounts.Market()
    signals=pd.read_parquet(OUT/'signals.parquet')
    pairs=pd.read_parquet(OUT/'pairs.parquet')
    lookup={key:g for key,g in pairs.groupby(['signal_date','signal','model','scope'])}
    coverage=pd.read_csv(OUT/'coverage.csv',parse_dates=['signal_date'])
    cov_dates=dict(tuple(coverage.groupby('signal_date')))
    events=[]
    for date,g in signals.groupby('signal_date'):
        e,x=int(g.entry_idx.iloc[0]),int(g.exit_idx.iloc[0])
        if x>=len(m.days) or m.days[x]>END:
            continue
        assert m.days[e-1]==date and x-e==10 and m.days[x]==g.exit_date.iloc[0]
        top=g[g.decile==10]
        base=leg(m,top)
        g=g.set_index('instrument',drop=False)
        for row in cov_dates[date].itertuples():
            key=date,row.signal,row.model,row.scope
            p=lookup.get(key)
            rec=dict(signal_date=date,exit_date=m.days[x],period='main' if m.days[x]<=MAIN else 'later',
                     signal=row.signal,model=row.model,scope=row.scope,eligible=row.eligible,pairs=row.n_pairs,
                     top=len(top),high_net=np.nan,low_net=np.nan,spread=np.nan,portfolio=np.nan,base=base['net_return'],
                     delta=np.nan,stress=np.nan,weight=0.,blocked_buys=0,blocked_exits=0)
            if p is not None:
                hi,lo=g.loc[p.high],g.loc[p.low]
                assert len(hi)==row.n_pairs and hi.index.is_unique and lo.index.is_unique
                assert (hi.industry.to_numpy()==lo.industry.to_numpy()).all()
                h,l=leg(m,hi),leg(m,lo)
                rec.update(high_net=h['net_return'],low_net=l['net_return'],spread=h['net_return']-l['net_return'],
                           blocked_buys=2*len(p)-h['bought']-l['bought'],
                           blocked_exits=h['blocked_exit_count']+l['blocked_exit_count'])
            if row.scope=='boundary':
                alt=top
                if p is not None:
                    assert hi.decile.eq(9).all() and lo.decile.eq(10).all()
                    alt=pd.concat([top[~top.instrument.isin(p.low)],hi])
                    assert len(alt)==len(top) and alt.instrument.is_unique
                value=leg(m,alt)['net_return'] if p is not None else base['net_return']
                weight=row.n_pairs/len(top)
                delta=value-base['net_return']
                rec.update(portfolio=value,weight=weight,delta=delta,stress=delta-.006*weight)
            events.append(rec)
    events=pd.DataFrame(events)
    events.to_csv(OUT/'events.csv',index=False)
    rows=[]
    for (period,signal,model,scope),z in events.groupby(['period','signal','model','scope']):
        for metric in (['spread'] if scope=='pool' else ['spread','delta','stress']):
            v=bootstrap(z[metric].to_numpy())
            rows.append(dict(period=period,signal=signal,model=model,scope=scope,metric=metric,
                             eligible_mean=z.eligible.mean(),pairs_total=z.pairs.sum(),matched_dates=(z.pairs>0).sum(),
                             mean_budget=z.weight.mean(),blocked_buys=z.blocked_buys.sum(),blocked_exits=z.blocked_exits.sum(),**v))
    stats=pd.DataFrame(rows)
    primary=(stats.period=='main')&(stats.model=='controlled')&(stats.scope=='pool')
    assert primary.sum()==3
    stats.loc[primary,'holm_p']=holm(stats.loc[primary,'p'].to_numpy())
    stats.to_csv(OUT/'summary.csv',index=False)
    for s in NAMES[:3]:
        f=stats[(stats.signal==s)&(stats.model=='controlled')]
        print(s, f[['period','scope','metric','pairs_total','matched_dates','n','mean','low','high','holm_p']].to_string(index=False),flush=True)


if __name__=='__main__':
    evaluate()
