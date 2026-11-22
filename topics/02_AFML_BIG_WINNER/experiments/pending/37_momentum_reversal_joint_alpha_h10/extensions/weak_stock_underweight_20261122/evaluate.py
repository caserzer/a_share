"""Trade only net differences from drifted holdings, with a common turnover ceiling."""
import json
import sys
import numpy as np
import pandas as pd

from select_weights import D, EP, SOURCE, MODELS, MAIN, accounts, dump, sha
from core import bootstrap, holm
sys.path.append(str(SOURCE/"src"))
from portfolio import trade

NAMES=["base"]+MODELS


def simulate(m, h, plans, name, cost, scope, episode):
    om,cm=m.marks["flat"]
    fees={"main":(.001,.002),"zero":(0.,0.)}[cost]
    start=h.entry_date.min()
    end=h.exit_date.max()
    reb={r.entry_date:r.signal_date for r in h.itertuples()}
    units=np.zeros(m.n)
    cash=1.
    initialized=False
    openings={}
    logs=[]
    orders=[]
    checkpoints=[]
    failure=None
    meta=dict(scope=scope,episode=episode,model=name,cost=cost)
    for i in range(m.days.get_loc(start),m.days.get_loc(end)+1):
        day=m.days[i]
        held=units>0
        buy=sell=fee=blocked_buy=blocked_sell=0.
        cash_before=cash
        before=units
        nav_open=np.nan
        cap_scale=np.nan
        placed=False
        if day in reb or day==end:
            missing=held & ~np.isfinite(om[i])
            if missing.any():
                failure=(day,"open",m.symbols[missing].tolist())
                break
            value=units*np.nan_to_num(om[i])
            nav_open=cash+value.sum()
            openings[day]=nav_open
            date=reb.get(day)
            if date in plans:
                weights=plans[date][name]
                drift=value/nav_open
                delta=weights-drift
                gross_side=max(delta.clip(min=0).sum(),(-delta).clip(min=0).sum())
                cap_scale=min(1.,.05/gross_side) if initialized and gross_side>0 else 1.
                target=drift+cap_scale*delta
                # Only the same deterministic delta budget is capped; blocked holdings remain.
                units,cash,record=trade(units,cash,om[i],np.r_[target,1-target.sum()],
                    m.buy[i]&m.members[i-1],m.sell[i],*fees)
                buy,sell,fee,blocked_buy,blocked_sell=(record[k] for k in ["buy","sell","fees","unfilled_buy","unfilled_sell"])
                assert not initialized or max(buy,sell)<=.05+1e-12
                assert abs(fee-nav_open*(buy*fees[0]+sell*fees[1]))<1e-12
                initialized=True
                placed=True
        mark=om[i] if day==end else cm[i]
        amounts=units*np.nan_to_num(mark)
        missing=(units>0)&~np.isfinite(mark)
        if missing.any():
            failure=(day,"mark",m.symbols[missing].tolist())
            break
        nav=cash+amounts.sum()
        change=units-before
        notional=change*np.nan_to_num(om[i])
        assert abs(cash-cash_before+notional.sum()+fee)<1e-10
        if placed:
            assert abs(np.maximum(notional,0).sum()/nav_open-buy)<1e-10
            assert abs(np.maximum(-notional,0).sum()/nav_open-sell)<1e-10
            if cost=="main":
                for j in np.flatnonzero(np.abs(notional)>1e-14):
                    orders.append(meta|dict(date=day,instrument=m.symbols[j],price=om[i,j],units_delta=change[j],notional=notional[j]))
                for j in np.flatnonzero(units>0):
                    checkpoints.append(meta|dict(date=day,instrument=m.symbols[j],units=units[j],marked_value=units[j]*om[i,j]))
        logs.append(meta|dict(date=day,nav=nav,cash=cash,fee=fee,buy=buy,sell=sell,blocked_buy=blocked_buy,
                              blocked_sell=blocked_sell,placed=placed,cap_scale=cap_scale,nav_open=nav_open))
    daily=pd.DataFrame(logs)
    cycles=[]
    for r in h.itertuples():
        a,b=r.entry_date,r.exit_date
        success=a in openings and b in openings
        cycles.append(meta|dict(signal_date=r.signal_date,entry_date=a,exit_date=b,selection_status=r.status,
            net=openings[b]/openings[a]-1 if success else np.nan))
    complete=failure is None
    summary=meta|dict(start=start,planned_end=end,complete=complete,
        end=daily.date.iloc[-1] if len(daily) else None,failure_day=failure[0] if failure else None,
        failure_mark=failure[1] if failure else None,failure_names="|".join(failure[2]) if failure else "",
        nav=daily.nav.iloc[-1] if len(daily) else np.nan,
        cagr=daily.nav.iloc[-1]**(252/(len(daily)-1))-1 if complete else np.nan,
        max_drawdown=(daily.nav/np.maximum.accumulate(np.r_[1.,daily.nav])[1:]-1).min() if len(daily) else np.nan,
        filled_cycles=sum(np.isfinite(c["net"]) for c in cycles))
    if complete:
        assert np.isclose(np.prod([1+c["net"] for c in cycles]),summary["nav"])
    return summary,logs,cycles,orders,checkpoints


def paired(cycles):
    tests=[]
    for (scope,cost),h in cycles.groupby(["scope","cost"]):
        table=h.pivot(index="signal_date",columns="model",values="net").sort_index()
        exits=h.drop_duplicates("signal_date").set_index("signal_date").exit_date
        for section,sub in [("primary",table.loc[exits.reindex(table.index).le(MAIN)]),
                            ("later",table.loc[exits.reindex(table.index).gt(MAIN)])]:
            if sub.empty:
                continue
            common=sub.where(sub.notna().all(axis=1),np.nan)
            for name,base in [("E1","base"),("E1","REV"),("E1","RANK"),("REV","base"),("RANK","base")]:
                tests.append(dict(scope=scope,cost=cost,section=section,model=name,vs=base,
                               **bootstrap((common[name]-common[base]).to_numpy())))
    out=pd.DataFrame(tests)
    out["holm_p"]=np.nan
    for _,grp in out[out.model.eq("E1")].groupby(["scope","cost","section"]):
        if grp.p.notna().any():
            out.loc[grp.index,"holm_p"]=holm(grp.p.to_numpy())
    return out


def run():
    for name,h in json.loads((D/"inputs.json").read_text()).items():
        assert sha(name)==h,name
    for name,h in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/name)==h,name
    accounts.OUT=D
    m=accounts.Market()
    sch=pd.read_csv(D/"schedule.csv",parse_dates=["signal_date","entry_date","exit_date"])
    p=pd.read_parquet(D/"targets.parquet")
    plans={}
    for date,g in p.groupby("signal_date"):
        g=g.set_index("instrument")
        plans[date]={model:g["base" if model=="base" else model+"_target"].reindex(m.symbols,fill_value=0).to_numpy()
                     for model in NAMES}
    summaries,days,cycles,orders,positions=[],[],[],[],[]
    for section,h in sch.groupby(sch.exit_date.le(MAIN),sort=False):
        label="primary" if section else "later"
        quarters=list(h.groupby(h.signal_date.dt.to_period("Q")))
        for scope,k,g in [("continuous",label,h)]+[("quarter",label+"_"+str(q),a) for q,a in quarters]:
            for model in NAMES:
                for cost in ["main","zero"]:
                    s,d,c,o,hs=simulate(m,g,plans,model,cost,scope,k)
                    summaries.append(s)
                    days.extend(d)
                    cycles.extend(c)
                    orders.extend(o)
                    positions.extend(hs)
    out=pd.DataFrame(cycles)
    pd.DataFrame(summaries).to_csv(D/"accounts.csv",index=False)
    out.to_csv(D/"cycles.csv",index=False)
    paired(out).to_csv(D/"tests.csv",index=False)
    for name,rows in [("daily",days),("orders",orders),("holdings",positions)]:
        pd.DataFrame(rows).to_parquet(D/(name+".parquet"),index=False)
    print(pd.DataFrame(summaries).query("model=='E1' and scope=='continuous' and cost=='main'").to_string(index=False),flush=True)
    print(pd.read_csv(D/"tests.csv").query("model=='E1' and cost=='main'").to_string(index=False),flush=True)


if __name__=="__main__":
    run()
