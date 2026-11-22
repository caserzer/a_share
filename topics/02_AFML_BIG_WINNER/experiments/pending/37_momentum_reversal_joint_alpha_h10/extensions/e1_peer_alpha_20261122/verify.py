"""Independent pair audits, boundary holding lists, and descriptive partial rank IC."""
import json
import numpy as np
import pandas as pd
from signals import EP, OUT, PRIVATE, ROOT, PRED, sha, dump
from matching import EXTRA
from evaluate import MAIN, END
from core import bootstrap, clean


def partial(g, signal):
    fields=['E1_78','RANK_MSE_78','mom5','mom20','vol',EXTRA[signal]]
    if signal=='H3':
        fields += ['ret10','turn5']
    v=g.dropna(subset=[signal,'return10','industry']+fields)
    v=v[v.groupby('industry').instrument.transform('size')>=2]
    if len(v)<12:
        return np.nan
    ranks=v[[signal,'return10']+fields].rank()
    within=ranks-ranks.groupby(v.industry).transform('mean')
    X=within[fields].to_numpy()
    Y=within[[signal,'return10']].to_numpy()
    coef,_,rank,_=np.linalg.lstsq(X,Y,rcond=None)
    residual=Y-X@coef
    if len(v)-v.industry.nunique()-rank<12 or residual.std(axis=0).min()<1e-9:
        return np.nan
    return np.corrcoef(residual.T)[0,1]


def verify():
    for path,digest in json.loads((OUT/'inputs.json').read_text()).items():
        assert sha(EP.parent/path)==digest,path
    for path,digest in json.loads((OUT/'selection.json').read_text()).items():
        assert sha(OUT/path)==digest,path
    signals=pd.read_parquet(OUT/'signals.parquet')
    p=pd.read_parquet(OUT/'pairs.parquet')
    cov=pd.read_csv(OUT/'coverage.csv',parse_dates=['signal_date'])
    keys=['signal_date','signal','model','scope']
    expected=cov.set_index(keys).n_pairs.sort_index()
    actual=p.groupby(keys).size().reindex(expected.index,fill_value=0)
    assert expected.equals(actual.rename('n_pairs'))
    assert not p.duplicated(keys+['high']).any() and not p.duplicated(keys+['low']).any()
    idx=['signal_date','instrument']
    dated=signals.set_index(idx)
    def aligned(side):
        index=pd.MultiIndex.from_arrays([p.signal_date,p[side]],names=idx)
        return dated.reindex(index).reset_index(drop=True)
    high,low=aligned('high'),aligned('low')
    std=signals.groupby('signal_date').std(numeric_only=True,ddof=0).reindex(p.signal_date).reset_index(drop=True)
    assert (high.industry==low.industry).all() and (high.industry==p.industry).all()
    for signal,g in p.groupby('signal'):
        ix=g.index
        assert (high.loc[ix,signal]>low.loc[ix,signal]).all()
        fields=dict(E1_78=.25,mom5=.5,mom20=.5,vol=.5)
        if signal=='H3':
            fields.update(ret10=.5,turn5=.5)
        for field,cap in fields.items():
            assert ((high.loc[ix,field]-low.loc[ix,field]).abs()<=std.loc[ix,field]*cap+1e-12).all()
        if signal in EXTRA:
            ix=g[g.model=='controlled'].index
            for field in ['RANK_MSE_78',EXTRA[signal]]:
                assert ((high.loc[ix,field]-low.loc[ix,field]).abs()<=std.loc[ix,field]*.5+1e-12).all()
    ix=p.scope=='boundary'
    assert high.loc[ix,'decile'].eq(9).all() and low.loc[ix,'decile'].eq(10).all()
    pred=pd.read_parquet(PRED).set_index(idx)
    pd.testing.assert_frame_equal(dated[pred.columns].sort_index(),pred.sort_index())
    prices=pd.read_parquet(PRIVATE/'qfq_open.parquet')
    swaps=p[ix & (p.model=='controlled')].groupby(['signal_date','signal'])
    swaps=dict(tuple(swaps))
    holdings,ics=[],[]
    for date,g in signals.groupby('signal_date'):
        x=int(g.exit_idx.iloc[0])
        if x>=len(prices) or prices.index[x]>END:
            continue
        e=int(g.entry_idx.iloc[0])
        assert prices.index[e-1]==date and x-e==10 and (g.fit_cutoff<date).all()
        g=g.copy()
        g['return10']=(prices.iloc[x]/prices.iloc[e]-1).reindex(g.instrument).to_numpy()
        period='main' if prices.index[x]<=MAIN else 'later'
        top=set(g[g.decile==10].instrument)
        inds=g.set_index('instrument').industry.fillna('UNKNOWN')
        for s in EXTRA:
            ics.append(dict(signal_date=date,period=period,signal=s,ic=partial(g,s)))
            pair=swaps.get((date,s))
            added=set() if pair is None else set(pair.high)
            removed=set() if pair is None else set(pair.low)
            new=top.difference(removed).union(added)
            assert len(new)==len(top)
            assert inds.loc[sorted(top)].value_counts().sort_index().equals(inds.loc[sorted(new)].value_counts().sort_index())
            for symbol in sorted(new | top):
                holdings.append(dict(signal_date=date,signal=s,instrument=symbol,
                                     e1_weight=(symbol in top)/len(top),new_weight=(symbol in new)/len(new)))
    pd.DataFrame(holdings).to_csv(OUT/'boundary_targets.csv.gz',index=False)
    ic=pd.DataFrame(ics)
    ic.to_csv(OUT/'partial_rank_ic.csv',index=False)
    summary=[dict(period=period,signal=signal,**bootstrap(z.ic))
             for (period,signal),z in ic.groupby(['period','signal'])]
    pd.DataFrame(summary).to_csv(OUT/'partial_rank_ic_summary.csv',index=False)
    events=pd.read_csv(OUT/'events.csv')
    assert events.groupby(keys[1:]).size().eq(139).all()
    assert events[events.scope.eq('boundary') & events.pairs.eq(0)].delta.dropna().eq(0).all()
    dump(OUT/'verification.json',clean(dict(input_hashes_verified=True,frozen_predictions_verified=len(pred),
         pair_rows_verified=len(p),signals=signals.signal_date.nunique(),mature_dates=events.signal_date.nunique(),
         primary_dates=events[events.period=='main'].signal_date.nunique(),later_dates=events[events.period=='later'].signal_date.nunique(),
         boundary_holdings_industry_and_budget_verified=True,
         sha256={f.name:sha(f) for f in sorted(OUT.iterdir()) if f.name!='verification.json'})))


if __name__=='__main__':
    verify()
