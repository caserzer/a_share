"""Independent source, match, outcome and influence checks on the sealed design."""
import json
import numpy as np
import pandas as pd
from freeze import EP, OUT, PRIVATE, PRED, FIELDS, sha, dump
from core import clean, bootstrap, assign_deciles


def weighted_slope(d,controls=()):
    w=1/d.groupby('signal_date')['high'].transform('size').to_numpy()
    X=np.column_stack([np.ones(len(d)),d.breadth,*[d[c] for c in controls]])
    b,_,rank,_=np.linalg.lstsq(X*np.sqrt(w[:,None]),d['diff']*np.sqrt(w),rcond=None)
    return .1*b[1] if rank==X.shape[1] else np.nan


def verify():
    sealed=json.loads((OUT/'selection.json').read_text())
    assert all(sha(EP.parent/path)==v for path,v in sealed.items())
    f=pd.read_parquet(OUT/'signals.parquet')
    keys=['signal_date','instrument']
    pred=pd.read_parquet(PRED).set_index(keys).sort_index()
    indexed=f.set_index(keys).sort_index()
    pd.testing.assert_frame_equal(pred,indexed[pred.columns])
    ok=f.A.notna()
    assert np.allclose(f.loc[ok,['market_part','industry_part','drift','residual']].sum(axis=1),np.log1p(f.loc[ok,'mom5']))
    assert np.allclose(f.loc[ok,'A'],-f.loc[ok,['market_part','industry_part']].sum(axis=1))
    assert f.B.dropna().between(0,20).all() and f.breadth.dropna().between(0,1).all()
    pairs=pd.read_parquet(OUT/'pairs.parquet')
    events=pd.read_csv(OUT/'events.csv',parse_dates=['signal_date'])
    stats=pd.read_csv(OUT/'statistics.csv')
    coverage=pd.read_csv(OUT/'coverage.csv',parse_dates=['signal_date'])
    cols=['signal_date','signal','model','scope']
    counts=pairs.groupby(cols).size().reindex(coverage.set_index(cols).index,fill_value=0)
    assert np.array_equal(counts,coverage.pairs)
    for _,m in pairs.groupby(cols):
        assert m.high.is_unique and m.low.is_unique and not set(m.high)&set(m.low)
    h=indexed.reindex(pd.MultiIndex.from_arrays([pairs.signal_date,pairs.high],names=keys)).reset_index(drop=True)
    l=indexed.reindex(pd.MultiIndex.from_arrays([pairs.signal_date,pairs.low],names=keys)).reset_index(drop=True)
    assert (h.industry==l.industry).all() and (h.industry==pairs.industry).all()
    scale=f.groupby('signal_date').std(numeric_only=True,ddof=0).reindex(pairs.signal_date).reset_index(drop=True)
    for (s,model,scope),g in pairs.groupby(['signal','model','scope']):
        ix=g.index
        assert (h.loc[ix,s]>l.loc[ix,s]).all()
        if s=='A':
            assert h.loc[ix,'oversold'].all() and l.loc[ix,'oversold'].all()
        if scope=='D10':
            assert h.loc[ix,'decile'].eq(10).all() and l.loc[ix,'decile'].eq(10).all()
        if scope=='positive':
            assert (h.loc[ix,'relative20']>0).all() and (l.loc[ix,'relative20']>0).all()
        for field in ['E1_78']+FIELDS[s]+(['RANK_MSE_78'] if model=='both' else []):
            assert ((h.loc[ix,field]-l.loc[ix,field]).abs()<=scale.loc[ix,field]*(.25 if field=='E1_78' else .5)+1e-12).all()
    dates=sorted(f.signal_date.unique())
    # Independent checks at three dates using scalar returns and direct peer lists.
    close=pd.read_parquet(PRIVATE/'qfq_close.parquet')
    members=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex_like(close).eq(True)
    sectors=pd.read_parquet(PRIVATE/'industry.parquet')
    sectors['instrument']=sectors.ts_code.str[-2:]+sectors.ts_code.str[:6]
    start=pd.to_datetime(sectors.in_date)
    end=pd.to_datetime(sectors.out_date)
    checked=0
    for date in [dates[0],dates[len(dates)//2],dates[-1]]:
        t=close.index.get_loc(date)
        z=f[f.signal_date==date].set_index('instrument')
        def industries(d):
            a=sectors[(start<=d)&(end.isna()|(end>d))]
            return a.groupby('instrument').l1_code.agg(lambda v:v.iloc[0] if v.notna().all() and v.nunique()==1 else None).reindex(close.columns)
        current=industries(date)
        daily=close.pct_change(fill_method=None).iloc[t-19:t+1]
        histories=[industries(d) for d in daily.index]
        r5=close.iloc[t]/close.iloc[t-5]-1
        for s in z[z.B.notna() & z.A.notna()].index[::53]:
            k=current[s]
            other=(current!=k)&current.notna()&members.loc[date]&r5.notna()
            assert np.isclose((r5[other]<0).mean(),z.at[s,'breadth'])
            diffs=[]
            for (day,rr),industry in zip(daily.iterrows(),histories):
                peers=rr[(industry==k)&members.loc[day]].drop(s).dropna()
                assert len(peers)>=4
                diffs.append(np.log1p(rr[s])-np.log1p(peers.mean()))
            assert (np.array(diffs)>0).sum()==z.at[s,'B']
            assert np.isclose(np.sum(diffs),z.at[s,'relative20'])
            checked+=1
    outcomes=pd.read_parquet(OUT/'pair_outcomes.parquet')
    A=outcomes[(outcomes.signal=='A')&(outcomes.scope=='pool')&(outcomes.model=='both')].dropna(subset=['diff']).copy()
    for field in ['mom5','pre20','prevol','E1_78','RANK_MSE_78']:
        def values(side):
            return indexed[field].reindex(pd.MultiIndex.from_arrays([A.signal_date,A[side]],names=keys)).to_numpy()
        A[field]=(values('high')-values('low'))/f.groupby('signal_date')[field].std(ddof=0).reindex(A.signal_date).to_numpy()
    results=[]
    for per,z in A.groupby('period'):
        slope=weighted_slope(z)
        orig=stats[(stats.period==per)&(stats.signal=='A')&(stats.model=='both')&(stats.metric=='slope_diff')].iloc[0]
        assert np.isclose(orig['mean'],slope)
        for date in z.signal_date.unique():
            results.append(dict(period=per,check='leave_date_out',omitted=pd.Timestamp(date).strftime('%Y-%m-%d'),
                                slope=weighted_slope(z[z.signal_date!=date])))
        for year in sorted(z.signal_date.dt.year.unique()):
            results.append(dict(period=per,check='leave_year_out',omitted=str(year),
                                slope=weighted_slope(z[z.signal_date.dt.year!=year])))
        results.append(dict(period=per,check='adjust_remaining_gaps',omitted='none',
            slope=weighted_slope(z,['mom5','pre20','prevol','E1_78','RANK_MSE_78'])))
    pd.DataFrame(results).to_csv(OUT/'influence.csv',index=False)
    holdings=pd.read_csv(OUT/'d10_holdings.csv.gz',parse_dates=['signal_date'])
    held=holdings.groupby('signal_date')
    assert np.allclose(held.tilt_weight.sum(),1) and np.allclose(held.e1_weight.sum(),1)
    assert holdings.groupby(['signal_date','industry'],dropna=False)[['tilt_weight','e1_weight']].sum().diff(axis=1).e1_weight.abs().max()<1e-10
    baseline=pd.read_csv(OUT/'baseline.csv')
    assert len(baseline)==139 and events.groupby(['signal','model','scope']).size().eq(139).all()
    summary=[]
    for per,z in baseline.groupby('period'):
        for key in ['oversold','index_return','excess']:
            v=z.oversold-z.index_return if key=='excess' else z[key].where(z.oversold.notna())
            summary.append(dict(period=per,metric=key,**bootstrap(v)))
    pd.DataFrame(summary).to_csv(OUT/'baseline_summary.csv',index=False)
    dump(OUT/'verification.json',clean(dict(signal_rows=len(f),signal_dates=len(dates),mature_dates=len(baseline),
        frozen_predictions_verified=True,decomposition_rows=int(ok.sum()),pair_rows_checked=len(pairs),
        independent_stock_date_replays=checked,independent_slope_replays=2,
        result_sha256={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.name!='verification.json'})))


if __name__=='__main__':
    verify()
