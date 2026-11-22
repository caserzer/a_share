"""Independently reconcile main ledgers and explain the equal-weight to index-weight bridge."""
import json
import numpy as np
import pandas as pd

from select_weights import D, MODELS, MAIN, PRIVATE, accounts, sha, dump

def run():
    for n,v in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/n)==v
    p=pd.read_parquet(D/"targets.parquet")
    s=pd.read_csv(D/"schedule.csv",parse_dates=["entry_date","exit_date","signal_date","snapshot"]).set_index("signal_date")
    assert s.snapshot.lt(s.index).all()
    accounts.OUT=D
    m=accounts.Market()
    om,cm=m.marks["flat"]
    bridge=[]
    overlap=[]
    for date,h in p.groupby("signal_date"):
        assert h.instrument.is_unique and np.isclose(h.base.sum(),1)
        budget=s.at[date,"shift"]
        moves={}
        amounts={}
        for name in MODELS:
            d=h[name+"_target"]-h.base
            assert np.isclose(d.abs().sum()/2,budget)
            assert (d.abs()<=.5*h.base+1e-12).all()
            assert (d[~h[name+"_low"]]>=-1e-12).all() and (d[h[name+"_low"]]<=1e-12).all()
            assert np.allclose(d[h[MODELS].isna().any(axis=1)|h.industry.eq("UNKNOWN")],0)
            assert np.allclose(d.groupby(h.industry).sum(),0)
            moves[name]=d.clip(upper=0).groupby(h.industry).sum()
            amounts[name]=-d.clip(upper=0)
        for other in ["REV","RANK"]:
            np.testing.assert_allclose(moves["E1"],moves[other],atol=1e-12)
            overlap.append(dict(signal_date=date,other=other,shared_donor_budget=np.minimum(amounts["E1"],amounts[other]).sum()/budget))
        names=m.symbols.get_indexer(h.instrument)
        r=s.loc[date]
        with np.errstate(invalid="ignore",divide="ignore"):
            ret=om[m.days.get_loc(r.exit_date),names]/om[m.days.get_loc(r.entry_date),names]-1
        common=h[MODELS].notna().all(axis=1).to_numpy()
        # Same security universe/endpoint marks for all four idealized alternatives.
        if not np.isfinite(ret[common]).all():
            continue
        b=h.base.to_numpy()
        low=h.E1_low.to_numpy()
        top=common & ~low
        equal=ret[top].mean()-ret[common].mean()
        unit_spread=ret[top].mean()-ret[low].mean()
        weighted=np.average(ret[top],weights=b[top])-np.average(ret[low],weights=b[low])
        active=(h.E1_target-h.base).to_numpy()
        industry=active[common]@ret[common]
        bridge.append(dict(signal_date=date,exit_date=r.exit_date,budget=budget,
            equal_exclude_20=equal,equal_same_budget=budget*unit_spread,
            index_same_budget_unconstrained=budget*weighted,sealed_industry_tilt=industry))
    pd.DataFrame(bridge).to_csv(D/"bridge.csv",index=False)
    pd.DataFrame(overlap).to_csv(D/"overlap.csv",index=False)
    daily=pd.read_parquet(D/"daily.parquet")
    orders=pd.read_parquet(D/"orders.parquet")
    holdings=pd.read_parquet(D/"holdings.parquet")
    cycles=pd.read_csv(D/"cycles.csv",parse_dates=["signal_date","entry_date","exit_date"])
    accounts_table=pd.read_csv(D/"accounts.csv",parse_dates=["start","end","planned_end"])
    audit=[]
    activity=[]
    for (scope,ep,name),g in daily.query("cost=='main'").groupby(["scope","episode","model"]):
        subset=orders[(orders.scope==scope)&(orders.episode==ep)&(orders.model==name)]
        trades=dict(tuple(subset.groupby("date")))
        h=holdings[(holdings.scope==scope)&(holdings.episode==ep)&(holdings.model==name)]
        snapshots=dict(tuple(h.groupby("date")))
        ac=accounts_table.query("scope==@scope and episode==@ep and model==@name and cost=='main'").iloc[0]
        u=np.zeros(m.n)
        cash=1.
        err=0.
        for r in g.itertuples():
            i=m.days.get_loc(r.date)
            if r.date in trades:
                o=trades[r.date]
                j=m.symbols.get_indexer(o.instrument)
                assert min(j)>=0 and o.instrument.is_unique
                np.testing.assert_allclose(o.units_delta*o.price,o.notional,atol=1e-12)
                assert m.buy[i,j[o.notional>0]].all() and m.sell[i,j[o.notional<0]].all()
                fee=o.notional.clip(lower=0).sum()*.001-o.notional.clip(upper=0).sum()*.002
                cash-=o.notional.sum()+fee
                u[j]+=o.units_delta
            if r.date in snapshots:
                held=snapshots[r.date].set_index("instrument").units.reindex(m.symbols,fill_value=0)
                np.testing.assert_allclose(held,u,atol=1e-11)
            mark=om[i] if r.date==ac.planned_end else cm[i]
            owned=u>1e-11
            assert np.isfinite(mark[owned]).all()
            err=max(err,abs(cash+u[owned]@mark[owned]-r.nav),abs(cash-r.cash))
        assert err<1e-9
        audit.append(dict(scope=scope,episode=ep,model=name,days=len(g),orders=len(subset),error=err))
        if scope=="continuous":
            init=g[g.placed].iloc[0]
            rebalances=g[g.placed & g.date.ne(init.date)]
            activity.append(dict(section=ep,model=name,fees=g.fee.sum(),post_initial_orders=len(rebalances),
                cap_binding=rebalances.cap_scale.lt(1).sum(),mean_rebalance_turnover=(rebalances.buy+rebalances.sell).mean()/2,
                annual_oneway_ex_initial=((g.buy+g.sell).sum()-init.buy-init.sell)*.5*252/(len(g)-1)))
    # Realized post-fill active share includes cash, with drift and trade gates intact.
    led=daily.query("scope=='continuous' and episode=='primary' and cost=='main' and placed").copy()
    led["opening_after_fees"]=led.nav_open-led.fee
    amounts=holdings.query("scope=='continuous' and episode=='primary'").loc[:,["date","model","instrument","marked_value"]]
    cash=led[["date","model","cash"]].rename(columns={"cash":"marked_value"}).assign(instrument="CASH")
    weights=pd.concat([amounts,cash],ignore_index=True).merge(led[["date","model","opening_after_fees"]],on=["date","model"],validate="m:1")
    weights["weight"]=weights.marked_value/weights.opening_after_fees
    wide=weights.pivot(index=["date","instrument"],columns="model",values="weight").fillna(0)
    np.testing.assert_allclose(wide.groupby(level="date").sum(),1,atol=1e-11)
    active=wide[MODELS].sub(wide.base,axis=0).abs().groupby(level="date").sum()/2
    active.to_csv(D/"actual_active_share.csv")
    pd.DataFrame(activity).to_csv(D/"turnover.csv",index=False)
    pd.DataFrame(audit).to_csv(D/"ledger_checks.csv",index=False)
    wide=cycles[(cycles.scope=="continuous")&(cycles.episode=="primary")&(cycles.cost=="main")].pivot(
        index="signal_date",columns="model",values="net")
    yr=[]
    for year,g in wide.groupby(wide.index.year):
        cum=(1+g).prod()-1
        yr.append(dict(year=year,windows=len(g),**cum.to_dict(),mean_e1_minus_base=(g.E1-g.base).mean()))
    pd.DataFrame(yr).to_csv(D/"yearly.csv",index=False)
    dump(D/"validation.json",dict(positive_weight_targets=len(p),validated_rebalance_dates=p.signal_date.nunique(),
        primary_common_cycles=len(wide.dropna()),max_independent_nav_error=float(pd.DataFrame(audit).error.max()),
        ledger_branches=len(audit),fees_buy=.001,fees_sell=.002))


if __name__=="__main__":
    run()
