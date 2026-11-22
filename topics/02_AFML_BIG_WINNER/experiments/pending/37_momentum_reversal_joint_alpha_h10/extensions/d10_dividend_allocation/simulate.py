"""H10 allocation using one cash account and the existing net-order execution contract."""
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from prepare import OUT, RANK, ROOT, TARGETS, MAIN, BENCH, accounts, dividend, sha, dump
from execution import net_account

RED="CSI_DIV_PRICE"


def market_with_index(m):
    idx=dividend(m.days)
    def join(a,s):
        return np.column_stack((a,s))
    valid=idx.open.notna().to_numpy()
    marks={mode:(join(o,idx.open),join(c,idx.close)) for mode,(o,c) in m.marks.items() if mode!="haircut20"}
    return SimpleNamespace(n=m.n+1,symbols=m.symbols.append(pd.Index([RED])),days=m.days,
        marks=marks,buy=join(m.buy,valid),sell=join(m.sell,valid),members=join(m.members,np.ones_like(valid)))


def index_free(m,g,end,mode):
    """Replicate the EP37 full-sale funding convention with a separate fee for each leg."""
    plans={e:h for e,h in g.groupby("entry_idx") if e<end}
    om,cm=m.marks[mode]
    units=np.zeros(m.n)
    due=np.full(m.n,-1)
    buy_fee=np.r_[np.full(m.n-1,.001),0.]
    sell_fee=np.r_[np.full(m.n-1,.002),0.]
    cash=1.
    daily,orders=[],[]
    for i in range(min(plans),end+1):
        expired=(units>0)&(due<=i)
        buys=np.zeros(m.n)
        sales=np.zeros(m.n)
        overlap=np.zeros(m.n)
        if expired.any() or i in plans or i==end:
            assert np.isfinite(om[i,units>0]).all()
            price=np.nan_to_num(om[i])
            sold=expired&m.sell[i]
            unlock=np.where(sold,units*price,0.)
            left=(units>0)&~sold
            after=cash+(unlock*(1-sell_fee)).sum()
            wants=np.zeros(m.n)
            if i in plans:
                h=plans[i]
                wants[m.symbols.get_indexer(h.instrument)]=h.weight
                wants*=m.buy[i]&m.members[i-1]&~left
                needed=wants@(1+buy_fee)
                if needed>0:
                    wants*=min((after+units[left]@price[left])/(1+wants@buy_fee),after/needed)
            overlap=np.minimum(unlock,wants)
            buys=wants-overlap
            sales=unlock-overlap
            cash+=sales@(1-sell_fee)-buys@(1+buy_fee)
            if abs(cash)<1e-12:
                cash=0.
            assert cash>=-1e-10
            units[sold]=0.
            new=wants>0
            units[new]=wants[new]/price[new]
            due[new]=i+10
            for j in np.flatnonzero((unlock+wants)>0):
                orders.append(dict(date=m.days[i],instrument=m.symbols[j],price=price[j],buy=buys[j],
                    sell=sales[j],overlap=overlap[j],fee=buys[j]*buy_fee[j]+sales[j]*sell_fee[j]))
        mark=(om if i==end else cm)[i]
        held=units>0
        assert np.isfinite(mark[held]).all()
        daily.append(dict(date=m.days[i],nav=cash+units[held]@mark[held],cash=cash,
                          fees=buys@buy_fee+sales@sell_fee,buy=buys.sum(),sell=sales.sum(),
                          direct_saving=overlap@(buy_fee+sell_fee)))
    return pd.DataFrame(daily),pd.DataFrame(orders),dict(valuation_complete=True,terminal_liquidated=not held.any(),failure=None)


def positions(p,weights):
    g=p.loc[p.signal_date.isin(weights.index)&p.base.gt(0),["signal_date","entry_idx","instrument","base"]].copy()
    g["weight"]=g.base*g.signal_date.map(weights)
    index=g[["signal_date","entry_idx"]].drop_duplicates()
    index["instrument"]=RED
    index["weight"]=1-index.signal_date.map(weights)
    targets=pd.concat([g.drop(columns="base"),index],ignore_index=True)
    assert np.allclose(targets.groupby("entry_idx").weight.sum(),1)
    return targets[targets.weight.gt(0)]


def verify(m,d,o,end,mode,schedule,cost):
    orders={day:h for day,h in o.groupby("date")}
    om,cm=m.marks[mode]
    dates=set(schedule.entry_date)|{end}
    units=np.zeros(m.n)
    cash=1.
    snapshots=[]
    holdings=[]
    worst=0.
    for row in d.itertuples():
        day=row.date
        i=m.days.get_loc(day)
        held=units>1e-12
        if day in dates:
            opening=cash+units[held]@om[i,held]
        if day in orders:
            h=orders[day]
            idx=m.symbols.get_indexer(h.instrument)
            assert h.instrument.is_unique and (h.buy*h.sell).abs().max()<1e-10
            assert m.buy[i,idx[h.buy.gt(0)]].all() and m.sell[i,idx[h.sell.gt(0)]].all()
            expected=(h.buy*.001+h.sell*.002) if cost!="zero" else h.fee*0
            if cost=="index_free":
                expected=expected.where(h.instrument.ne(RED),0)
            assert np.allclose(expected,h.fee,atol=1e-13)
            units[idx]+=(h.buy-h.sell)/h.price
            cash+=(h.sell-h.buy-h.fee).sum()
        held=units>1e-12
        mark=(om if day==end else cm)[i]
        nav=cash+units[held]@mark[held]
        assert np.isfinite(nav)
        worst=max(worst,abs(nav-row.nav),abs(cash-row.cash))
        assert worst<1e-9 and units.min()>-1e-10
        if day in dates:
            amounts=np.zeros(m.n)
            amounts[held]=units[held]*om[i,held]
            total=cash+amounts.sum()
            snapshots.append(dict(date=day,opening=opening,actual_d10=amounts[:-1].sum()/total,
                                  actual_red=amounts[-1]/total,actual_cash=cash/total))
            for j in np.flatnonzero(held):
                holdings.append(dict(date=day,instrument=m.symbols[j],units=units[j],open_weight=amounts[j]/total))
    i=m.days.get_loc(d.date.iloc[-1])
    close_nav=cash+units[held]@cm[i,held]
    return pd.DataFrame(snapshots).set_index("date"),pd.DataFrame(holdings),worst,close_nav


def drawdown(nav):
    values=np.r_[1.,nav]
    dd=values/np.maximum.accumulate(values)-1
    trough=int(np.argmin(dd))
    peak=int(np.flatnonzero(values[:trough+1]==values[:trough+1].max())[-1])
    recovery=np.flatnonzero(values[trough:]>=values[peak])
    return dd[trough],trough-peak,(int(recovery[0]) if len(recovery) else np.nan),len(values)-1-trough


def run():
    for name,h in json.loads((OUT/"inputs.json").read_text()).items():
        assert sha(name)==h,name
    accounts.OUT=OUT
    m=market_with_index(accounts.Market())
    p=pd.read_parquet(TARGETS)
    f=pd.read_csv(OUT/"signals.csv",parse_dates=["signal_date","entry_date","exit_date"]).set_index("signal_date")
    f.index.name="signal_date"
    primary=f[(f.phase=="test")&f.exit_date.le(MAIN)]
    warm=f[f.phase=="warmup"]
    last=f.loc[f.red.notna(),"exit_date"].max()
    ext=f[(f.phase=="test")&f.exit_date.le(last)]
    idx_data=json.loads(BENCH.read_text())["data"]
    bench=pd.DataFrame(idx_data["items"],columns=idx_data["fields"])
    bench.index=pd.to_datetime(bench.trade_date)
    summaries,ledgers,order_frames,hist,cycles,target_frames,statuses=[],[],[],[],[],[],[]
    wmean=primary.allocation.mean()
    def models(h):
        return dict(d10=pd.Series(1.,index=h.index),dividend=pd.Series(0.,index=h.index),
            balanced=pd.Series(.5,index=h.index),rule=h.rule,dynamic=h.allocation,matched=pd.Series(wmean,index=h.index))
    for scope,h,weights in [("primary",primary,models(primary)),("warmup",warm,{"balanced":pd.Series(.5,index=warm.index)}),
                ("extended",ext,models(ext)),("baseline_replay",f[f.exit_date.le(MAIN)],{"d10":pd.Series(1.,index=f[f.exit_date.le(MAIN)].index)})]:
        end=h.exit_date.max()
        end_idx=m.days.get_loc(end)
        for name,w in weights.items():
            g=positions(p,w)
            if scope=="primary":
                target_frames.append(g.assign(strategy=name))
            cases=[("main","flat",.001,.002)]
            if scope=="primary":
                cases.extend([("zero","flat",0.,0.),("index_free","flat",.001,.002),("main","strict",.001,.002)])
            for cost,mode,bf,sf in cases:
                d,o,info=index_free(m,g,end_idx,mode) if cost=="index_free" else net_account(m,g,end_idx,mode,bf,sf)
                meta=dict(scope=scope,strategy=name,cost=cost,mode=mode)
                statuses.append(meta|info)
                snapshots,held,err,closing=verify(m,d,o,end,mode,h,cost)
                first,lastday=d.date.iloc[0],d.date.iloc[-1]
                complete=bool(info["valuation_complete"])
                dd,down,recover,after=drawdown(d.nav.to_numpy())
                edge=m.days[m.days.get_loc(first)-1]
                cagr=lambda value,n: value**(252/n)-1
                excess=np.nan
                if complete and end in bench.index and edge in bench.index:
                    excess=cagr(closing,len(d))-cagr(float(bench.at[end,"close"])/float(bench.at[edge,"close"]),len(d))
                red=o.instrument.eq(RED)
                summaries.append(meta|dict(start=first,end=lastday,planned_end=end,complete=complete,
                    liquidated=info["terminal_liquidated"],days=len(d),nav=d.nav.iloc[-1],cagr=cagr(d.nav.iloc[-1],len(d)-1) if complete else np.nan,
                    drawdown=dd,peak_to_trough_sessions=down,trough_to_recovery_sessions=recover,observed_sessions_after_trough=after,
                    fees=d.fees.sum(),red_fees=o.loc[red,"fee"].sum(),red_rebalance_fees=o.loc[red&~o.date.isin([first,end]),"fee"].sum(),
                    gross_turnover=(d.buy+d.sell).sum(),annual_oneway_turnover=((d.buy+d.sell)/d.nav).sum()*.5*252/(len(d)-1),
                    excess_close_cagr=excess,ledger_error=err))
                if scope=="baseline_replay":
                    old=pd.read_parquet(RANK/"results/daily.parquet").query("model=='base' and scope=='primary' and mode=='flat' and cost=='main'")
                    np.testing.assert_array_equal(d.date.to_numpy(),old.date.to_numpy())
                    np.testing.assert_allclose(d.nav,old.nav,atol=1e-12,rtol=0)
                if scope in ("primary","warmup") and mode=="flat":
                    obs=[]
                    for day,r in h.iterrows():
                        a,b=r.entry_date,r.exit_date
                        if a not in snapshots.index or b not in snapshots.index:
                            continue
                        terminal=d.nav.iloc[-1] if b==end else snapshots.at[b,"opening"]
                        obs.append(meta|dict(signal_date=day,entry_date=a,exit_date=b,target_d10=w.at[day],
                            actual_d10=snapshots.at[a,"actual_d10"],actual_red=snapshots.at[a,"actual_red"],
                            actual_cash=snapshots.at[a,"actual_cash"],cycle_return=terminal/snapshots.at[a,"opening"]-1))
                    assert np.isclose(np.prod([1+r["cycle_return"] for r in obs]),d.nav.iloc[-1])
                    cycles.extend(obs)
                if scope!="baseline_replay" and cost=="main" and mode=="flat":
                    ledgers.append(d.assign(**meta))
                    order_frames.append(o.assign(**meta))
                    if scope=="primary":
                        hist.append(held.assign(**meta))
    pd.DataFrame(summaries).to_csv(OUT/"accounts.csv",index=False)
    pd.DataFrame(cycles).to_csv(OUT/"cycles.csv",index=False)
    for file,frames in [("daily",ledgers),("orders",order_frames),("holdings_at_open",hist),("targets",target_frames)]:
        pd.concat(frames,ignore_index=True).to_parquet(OUT/(file+".parquet"),index=False)
    dump(OUT/"status.json",statuses)
    print("accounts completed",len(summaries),flush=True)


if __name__=="__main__":
    run()
