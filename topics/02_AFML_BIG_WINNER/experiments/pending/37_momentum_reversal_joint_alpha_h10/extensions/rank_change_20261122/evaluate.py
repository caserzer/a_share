"""Read frozen matched sets, evaluate both basket legs and self-financing accounts."""
import json
import numpy as np
import pandas as pd
from select_targets import D, EP, PREV, PRIVATE, SCORE, MAIN, END, KEY, sha, dump
from core import clean, bootstrap, holm
from execution import net_account
import accounts


def leg(m,g):
    if g.empty:
        return dict(net=np.nan,filled=False,status="EMPTY",n=0)
    r,_=accounts.event(m,g.assign(weight=1/len(g)),.001,.002)
    ok=r["any_entry"] and r["complete_exit"]
    return dict(net=r["net_return"] if ok else np.nan,filled=r["full_entry"],n=len(g),
                status="OK" if ok else ("EXIT_BLOCKED" if r["any_entry"] else "NO_BUYS"))


def conditional(g):
    q=g[g[SCORE+"_d"].ge(9)&g.industry.ne("UNKNOWN")].dropna(subset=["delta","h10",SCORE,"mom5","mom20"])
    controls=np.column_stack([pd.get_dummies(q.industry,dtype=float),q[[SCORE,"mom5","mom20"]].rank()])
    rank=np.linalg.matrix_rank(controls) if len(q) else 0
    if len(q)-rank<10:
        return np.nan,len(q),len(q)-rank
    y=q[["delta","h10"]].rank().to_numpy()
    residual=y-controls@np.linalg.lstsq(controls,y,rcond=None)[0]
    corr=np.corrcoef(residual.T)[0,1] if min(residual.std(axis=0))>1e-9 else np.nan
    return corr,len(q),len(q)-rank


def events(p,m,cal,matched):
    lab=pd.read_parquet(EP/"outputs/local_cache/labels.parquet",columns=KEY+["offset","h10"])
    p=p.merge(lab[lab.offset.eq(0)],on=KEY,validate="1:1")
    rows=[]
    prev=None
    for date,g in p[p.exit_date.le(END)].groupby("signal_date"):
        cur=g[g.base>0]
        s=matched[matched.signal_date.eq(date)]
        groups={"matched_enter":cur[cur.instrument.isin(s.entrant)],"matched_stay":cur[cur.instrument.isin(s.stayer)],
                "known_enter":cur[cur.role=="enter"],"all_stay":cur[cur.role=="stay"]}
        if prev is not None:
            groups["any_new"]=cur[~cur.instrument.isin(prev)]
            gone=sorted(prev-set(cur.instrument))
            groups["out"]=pd.DataFrame(dict(instrument=gone,entry_idx=g.entry_idx.iloc[0],exit_idx=g.exit_idx.iloc[0],state="unknown"),index=range(len(gone)))
        row=dict(signal_date=date)
        for name,basket in groups.items():
            row.update({name+"_"+k:v for k,v in leg(m,basket).items()})
        row["partial_ic"],row["partial_n"],row["partial_df"]=conditional(g)
        rows.append(row)
        prev=set(cur.instrument)
    frame=cal.merge(pd.DataFrame(rows),on="signal_date",how="left",validate="1:1")
    frame["matched_gap"]=frame.matched_enter_net-frame.matched_stay_net
    frame["full_entry_gap"]=frame.matched_gap.where(frame.matched_enter_filled.eq(True)&frame.matched_stay_filled.eq(True))
    frame["same_fold_gap"]=frame.matched_gap.where(~frame.new_fold)
    frame["unmatched_gap"]=frame.known_enter_net-frame.all_stay_net
    frame["prior_comparison"]=frame.any_new_net-frame.out_net
    return frame


def replay(m,dates,daily,orders,stop,mode,bf,sf):
    # Derive the NAV just before rebalance fees independently from signed net orders.
    grouped={day:g for day,g in orders.groupby("date")}
    om,cm=m.marks[mode]
    cash=1.
    units=np.zeros(m.n)
    opening={}
    error=0.
    for r in daily.itertuples():
        i=m.days.get_loc(r.date)
        held=units>1e-11
        if r.date in dates:
            assert np.isfinite(om[i,held]).all()
            opening[r.date]=cash+units[held]@om[i,held]
        if r.date in grouped:
            g=grouped[r.date]
            j=m.symbols.get_indexer(g.instrument)
            assert g.instrument.is_unique and (g.buy*g.sell).abs().max()<1e-10
            assert m.buy[i,j[g.buy>0]].all() and m.sell[i,j[g.sell>0]].all()
            assert np.allclose(g.fee,g.buy*bf+g.sell*sf)
            np.add.at(units,j,(g.buy-g.sell)/g.price)
            cash+=(g.sell-g.buy-g.fee).sum()
        held=units>1e-11
        mark=om[i] if r.date==stop else cm[i]
        value=cash+units[held]@mark[held]
        error=max(error,abs(value-r.nav),abs(cash-r.cash))
        assert np.isfinite(value) and units.min()>-1e-9 and error<1e-9
    last=daily.iloc[-1]
    j=m.days.get_loc(last.date)
    close_nav=cash+units[held]@cm[j,held]
    return opening,error,close_nav


def continuous(p,m,cal):
    targets=p[p.base.gt(0)]
    dates=set(pd.to_datetime(cal.entry_date.dropna()))
    metrics,ledgers,orders,receipts=[],[],[],[]
    cycles=[]
    for name in ["base","tilt"]:
        g=targets.assign(weight=targets[name])
        for scope,end in [("primary",MAIN),("extended",END)]:
            end_i=m.days.get_loc(end)
            for mode,bf,sf,cost in [("flat",.001,.002,"main"),("strict",.001,.002,"main"),("flat",0.,0.,"zero")]:
                d,o,status=net_account(m,g,end_i,mode,bf,sf)
                meta=dict(model=name,scope=scope,mode=mode,cost=cost)
                opening,err,close=replay(m,dates,d,o,end,mode,bf,sf)
                v=d.nav.to_numpy()
                stop=d.date.iloc[-1]
                metrics.append(meta|dict(start=d.date.iloc[0],end=stop,complete=status["valuation_complete"],liquidated=status["terminal_liquidated"],
                    days=len(v),terminal_nav=v[-1],cagr=v[-1]**(252/(len(v)-1))-1 if stop==end else np.nan,max_drawdown=(v/np.maximum.accumulate(np.r_[1.,v])[1:]-1).min(),
                    fees=d.fees.sum(),buy=d.buy.sum(),sell=d.sell.sum(),closing_nav=close,ledger_error=err))
                receipts.append(meta|status)
                ledgers.append(d.assign(**meta))
                if cost=="main" and mode=="flat":
                    orders.append(o.assign(**meta))
                    for r in cal.itertuples():
                        if r.entry_date not in opening or pd.isna(r.exit_date) or r.exit_date>end:
                            continue
                        value=v[-1] if r.exit_date==end and stop==end else opening.get(r.exit_date,np.nan)
                        cycles.append(meta|dict(signal_date=r.signal_date,cycle_return=value/opening[r.entry_date]-1))
    for file,frames in [("daily",ledgers),("orders",orders)]:
        pd.concat(frames,ignore_index=True).to_parquet(D/(file+".parquet"),index=False)
    dump(D/"account_status.json",clean(receipts))
    a=pd.DataFrame(metrics)
    a.to_csv(D/"accounts.csv",index=False)
    cy=pd.DataFrame(cycles)
    cy.to_csv(D/"account_cycles.csv",index=False)
    complete=cy.query("scope=='primary'").pivot(index="signal_date",columns="model",values="cycle_return")
    for name in ["base","tilt"]:
        assert np.isclose((1+complete[name]).prod(),a.query("model==@name and scope=='primary' and cost=='main' and mode=='flat'").iloc[0].terminal_nav)
    return complete.tilt-complete.base


def run():
    for f,h in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/f)==h
    accounts.OUT=D
    market=accounts.Market()
    p=pd.read_parquet(D/"ranks_targets.parquet")
    cal=pd.read_csv(D/"schedule.csv",parse_dates=["signal_date","entry_date","exit_date"])
    matched=pd.read_csv(D/"matches.csv",parse_dates=["signal_date"])
    frame=events(p,market,cal,matched)
    gap=continuous(p,market,cal)
    frame["account_gap"]=frame.signal_date.map(gap)
    frame.to_csv(D/"windows.csv",index=False)
    stats=[]
    cohorts=[("primary",frame[frame.exit_date.le(MAIN)]),("later",frame[frame.entry_date.ge(MAIN)&frame.exit_date.le(END)]),
             ("extended",frame[frame.exit_date.le(END)])]
    cohorts += [(str(y),g) for y,g in frame[frame.exit_date.le(END)].groupby(frame.signal_date.dt.year)]
    for scope,g in cohorts:
        for name in ["matched_gap","full_entry_gap","same_fold_gap","partial_ic","unmatched_gap","prior_comparison","account_gap"]:
            if name=="account_gap" and scope!="primary":
                continue
            stats.append(dict(scope=scope,metric=name,**bootstrap(g[name].to_numpy())))
    s=pd.DataFrame(stats)
    family=s.scope.eq("primary")&s.metric.isin(["matched_gap","account_gap"])
    s.loc[family,"holm_p"]=holm(s.loc[family,"p"].to_numpy())
    s.to_csv(D/"tests.csv",index=False)
    print(s[family].to_string(index=False),flush=True)


if __name__=="__main__":
    run()
