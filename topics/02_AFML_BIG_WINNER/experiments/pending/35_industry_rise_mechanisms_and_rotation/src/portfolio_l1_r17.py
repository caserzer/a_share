"""Monthly synthetic-basket portfolios; refuse missing-path compounding."""
import pandas as pd
from common import *
from evaluate_r01 import scores


def turnover(target,drifted):
    names=set(target)|set(drifted)
    return sum(abs(target.get(k,0)-drifted.get(k,0)) for k in names)


def path_for(g,dates):
    p=g.reindex(dates)
    if p.nav.isna().any() or p.block.nunique()!=1 or p.day_i.diff().dropna().ne(1).any():return None
    return p.nav.to_numpy()/p.nav.iloc[0]


def run():
    out=ROOT/'outputs/r17'; panel=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')
    d=pd.read_parquet(ROOT/'data/l1_daily.parquet')
    b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;calendar=pd.DatetimeIndex(b.index)
    ends=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max()
    # Complete-month schedule is based on benchmark calendar, not industry survival.
    ends=ends[[p.end_time.normalize()<=calendar.max() for p in ends.index]]
    schedule={origin:calendar[calendar.get_loc(origin)+1] for origin in ends if calendar.get_loc(origin)+1<len(calendar)}
    dates_order=sorted(schedule)
    next_origin=dict(zip(dates_order[:-1],dates_order[1:]))
    lookup={key:g.set_index('date').sort_index() for key,g in d.groupby(KEY)}
    intervals=[];daily=[];holdings=[];summary=[]
    methods=['equal','momentum','F','FD']
    for (era,level),univ in panel.groupby(['era','level']):
        for method in methods:
            drift={};invalid=False;ledger=[];returns=[]
            for origin,full in univ.groupby('date',sort=True):
                if origin not in next_origin:continue
                entry=schedule[origin];exit=schedule[next_origin[origin]]
                if era=='SW2014' and exit>pd.Timestamp('2021-11-30'):continue
                if era=='SW2021' and entry<pd.Timestamp('2022-01-01'):continue
                g=full[full.price_ready].dropna(subset=['breadth21','breadth63'])
                if len(g)<20:
                    # No signal yet; do not silently pretend later holes were continuous portfolios.
                    if ledger:invalid=True
                    intervals.append(dict(era=era,level=level,method=method,origin=origin,entry=entry,exit=exit,status='insufficient_signal_universe',universe=len(g)))
                    continue
                if method=='equal':selected=g.sort_values('industry_code')
                else:
                    s=scores(g)[method];selected=g.assign(score=s).sort_values(['score','industry_code'],ascending=[False,True]).head(6)
                target={c:1/len(selected) for c in selected.industry_code}
                days=calendar[(calendar>=entry)&(calendar<=exit)]
                paths=[];bad=[]
                for c in selected.industry_code:
                    p=path_for(lookup[(era,level,c)],days)
                    if p is None:bad.append(c)
                    else:paths.append(p)
                    holdings.append(dict(era=era,level=level,method=method,origin=origin,entry=entry,industry_code=c,weight=target[c]))
                rec=dict(era=era,level=level,method=method,origin=origin,entry=entry,exit=exit,universe=len(g),selected=len(selected))
                if bad:
                    invalid=True;drift={}
                    intervals.append(dict(rec,status='missing_selected_path',missing_codes=';'.join(bad)));continue
                a=np.column_stack(paths);wealth=a.mean(axis=1);t=turnover(target,drift)
                drift={c:target[c]*a[-1,j]/wealth[-1] for j,c in enumerate(selected.industry_code)}
                bm=b.loc[exit]/b.loc[entry]-1
                rec.update(status='valid',turnover=t,max_weight=max(target.values()),gross_return=wealth[-1]-1,benchmark_return=bm,
                    net20=(1-.002*t)*wealth[-1]-1,net50=(1-.005*t)*wealth[-1]-1)
                intervals.append(rec);ledger.append(rec)
                # Entry fees belong to the rebalance instant; multiplicative aggregation handles shared exits.
                returns.append(dict(date=entry,gross=0.,net20=-.002*t,net50=-.005*t,benchmark=0.))
                for j in range(1,len(days)):
                    ret=wealth[j]/wealth[j-1]-1
                    returns.append(dict(date=days[j],gross=ret,net20=ret,net50=ret,benchmark=b.loc[days[j]]/b.loc[days[j-1]]-1))
            if not ledger:continue
            # Final liquidation cost, never omitted from accepted compounded figures.
            returns.append(dict(date=ledger[-1]['exit'],gross=0.,net20=-.002,net50=-.005,benchmark=0.))
            rr=pd.DataFrame(returns).groupby('date')[['gross','net20','net50','benchmark']].agg(lambda s:(1+s).prod()-1)
            rr['era']=era;rr['level']=level;rr['method']=method;rr['whole_path_valid']=not invalid;daily.append(rr.reset_index())
            for c in ['gross','net20','net50']:
                record=dict(era=era,level=level,method=method,cost=c,valid_intervals=len(ledger),whole_path_valid=not invalid,
                    monthly_turnover_mean=np.mean([x['turnover'] for x in ledger]),total_turnover_with_final_exit=sum(x['turnover'] for x in ledger)+1,
                    mean_valid_interval_return=np.mean([x['gross_return' if c=='gross' else c] for x in ledger]),
                    max_target_industry_weight=max(x['max_weight'] for x in ledger))
                if not invalid:
                    wealth=(1+rr[c]).cumprod();years=(rr.index.max()-rr.index.min()).days/365.25
                    record.update(cagr=wealth.iloc[-1]**(1/years)-1,drawdown=(wealth/wealth.cummax().clip(lower=1)-1).min(),
                        vol=rr[c].std()*np.sqrt(252),beta=rr[c].cov(rr.benchmark)/rr.benchmark.var(),
                        benchmark_cagr=(1+rr.benchmark).prod()**(1/years)-1,
                        total_return=wealth.iloc[-1]-1)
                summary.append(record)
    pd.DataFrame(intervals).to_csv(out/'intervals.csv',index=False)
    pd.DataFrame(holdings).to_parquet(out/'holdings.parquet',index=False)
    pd.concat(daily,ignore_index=True).to_parquet(out/'daily_returns.parquet',index=False)
    pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r17.json'),code_sha256=sha(__file__),
        panel_sha256=sha(ROOT/'data/l1_monthly_panel.parquet'),price_sha256=sha(ROOT/'data/l1_daily.parquet'),
        quality='synthetic research baskets; not tradable portfolio',withheld_if_any_invalid=True))
    print(pd.DataFrame(summary).query("cost=='net20'").to_string(index=False))

if __name__=='__main__':run()
