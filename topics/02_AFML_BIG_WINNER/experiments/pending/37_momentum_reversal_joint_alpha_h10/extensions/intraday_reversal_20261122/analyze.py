"""Paired H10 tests, retained-name cost reconciliation and input/ledger checks."""
import json
import numpy as np
import pandas as pd
from prepare import D, OLD, ROOT, PRIVATE, MODELS, MAIN, END, sha, dump
from core import bootstrap, holm, clean, assign_deciles
import accounts


def read(name):
    return pd.read_csv(D/(name+".csv"),parse_dates=["signal_date","entry_date","exit_date"])


def main():
    dec=read("deciles")
    ev=read("events")
    co=read("cohorts")
    ic=read("rankic")
    panel=dec[["signal_date","entry_date","exit_date"]].drop_duplicates().set_index("signal_date").sort_index()
    for n,table,field in [("gross",dec,"gross"),("net",ev,"net")]:
        for group in [1,2,9,10]:
            q=table[(table.decile==group)&(table.model=="RANK_MSE_78")&(table["sample"]=="all")].set_index("signal_date")
            panel[n+"_D"+str(group)]=q[field]
        panel[n+"_head"]=panel[n+"_D10"]-panel[n+"_D9"]
        panel[n+"_tail"]=panel[n+"_D2"]-panel[n+"_D1"]
    for k,g in co.groupby("cohort"):
        q=g.set_index("signal_date")
        for col in ["net","n","reason","flagged"]:
            panel[k+"_"+col]=q[col]
    panel["new_minus_out"]=panel.new_net-panel.out_net
    for k in ["split","joint","joint_vs_base"]:
        panel[k+"_switch"]=panel[k+"_in_net"]-panel[k+"_out_net"]
    for scope in ["all","clean"]:
        ds=ev[(ev.decile==10)&(ev["sample"]==scope)].pivot(index="signal_date",columns="model",values="net")
        ir=ic[ic["sample"]==scope].pivot(index="signal_date",columns="model",values="rank_ic")
        for m in MODELS:
            panel[m+"_d10_"+scope]=ds[m]
            panel[m+"_ic_"+scope]=ir[m]
        for a,b in [("split","RANK_MSE_78"),("joint","split"),("joint","RANK_MSE_78")]:
            for metric in ["d10","ic"]:
                panel[a+"_minus_"+b+"_"+metric+"_"+scope]=panel[a+"_"+metric+"_"+scope]-panel[b+"_"+metric+"_"+scope]
    # Same-stock executed crossover charges from the sealed original ledger.
    orders=pd.read_parquet(OLD/"local_cache/ledgers/RANK_MSE_78_D10_primary_main_flat_orders.parquet")
    check=pd.read_parquet(D/"baseline_orders_primary.parquet")
    pd.testing.assert_frame_equal(check,orders,rtol=1e-11,atol=1e-13)
    actual=orders[orders.side.isin(["SELL","BUY"])].pivot_table(index=["date","instrument"],columns="side",values="value",aggfunc="sum",fill_value=0)
    cross=actual.min(axis=1).groupby(level="date").sum()
    ledger=pd.read_parquet(D/"nav.parquet")
    base=ledger.query("model=='RANK_MSE_78' and scope=='primary' and mode=='flat' and cost=='main' and style=='full'").set_index("date")
    p=panel[panel.exit_date<=MAIN].copy()
    p["overlap_traded"]=p.entry_date.map(cross).fillna(0.)
    p["overlap_fee"]=p.overlap_traded*.003
    assert len(p)==100
    p.to_csv(D/"primary_100_windows.csv")
    panel.to_csv(D/"all_windows.csv")
    records=[]
    metrics=["gross_head","gross_tail","net_head","net_tail","new_minus_out","stay_net","new_net","out_net",
             "split_switch","joint_switch","joint_vs_base_switch"]
    metrics += [c for c in panel if "_minus_" in c and (c.endswith("_all") or c.endswith("_clean"))]
    primary_names=["split_minus_RANK_MSE_78_d10_all","joint_minus_split_d10_all"]
    def collect(name,sub):
        family=[]
        for k in metrics:
            r=dict(scope=name,metric=k,**bootstrap(sub[k].to_numpy()))
            if name=="primary" and k in primary_names:
                family.append(r)
            records.append(r)
        for r,adj in zip(family,holm([r["p"] for r in family])):
            r["holm_p"]=adj
    for name,sub in [("primary",p),("later",panel[panel.entry_date>=MAIN]),("extended",panel)]:
        collect(name,sub)
    for yr,sub in panel.groupby(panel.index.year):
        collect(str(yr),sub)
    pd.DataFrame(records).to_csv(D/"paired_tests.csv",index=False)
    for t,col,key in [(dec,"gross","decile"),(ic,"rank_ic",None)]:
        rows=[]
        for name,sub in [("primary",t[t.exit_date<=MAIN]),("later",t[t.entry_date>=MAIN]),("extended",t)]:
            cols=["sample","model"]+([key] if key else [])
            rows.append(sub.groupby(cols)[col].agg(["count","mean"]).reset_index().assign(scope=name))
        pd.concat(rows).to_csv(D/(col+"_summary.csv"),index=False)
    a=pd.read_csv(D/"accounts.csv",parse_dates=["start","end"])
    a=a.query("scope=='primary' and mode=='flat' and cost=='main'").copy()
    market=pd.read_parquet(PRIVATE/"market.parquet")
    idx=market.index
    e=idx.get_loc(MAIN)
    start=idx.get_loc(pd.Timestamp("2021-01-11"))
    index_price=market.open.iloc[e]/market.open.iloc[start]
    raw=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
    b=pd.DataFrame(raw["items"],columns=raw["fields"])
    b.index=pd.to_datetime(b.trade_date)
    total_index=float(b.loc[MAIN,"close"])/float(b.loc[idx[start-1],"close"])
    scores=pd.read_parquet(D/"scores.parquet")
    accounts.OUT=D
    m=accounts.Market()
    bm=[]
    maxzero=0.
    reconstruction=[]
    for (sample,cost),q in ledger.query("model=='RANK_MSE_78' and mode=='flat'").groupby(["scope","cost"]):
        wide=q.pivot(index="date",columns="style",values="nav")
        if cost=="zero":
            assert wide.notna().all().all()
            err=(wide.full-wide.net).abs().max()
            assert err<1e-10
            maxzero=max(maxzero,err)
        else:
            o=pd.read_parquet(D/"net_orders.parquet").query("scope==@sample")
            # Independent reconstruction from only the net orders on the market grid.
            units=np.zeros(m.n)
            cash=1.
            final=MAIN if sample=="primary" else END
            os={day:g for day,g in o.groupby("date")}
            mx=0.
            for date,row in q[q["style"]=="net"].set_index("date").sort_index().iterrows():
                if date in os:
                    g=os[date]
                    j=m.symbols.get_indexer(g.instrument)
                    assert len(set(j))==len(j) and ((g.buy*g.sell).abs()<1e-12).all()
                    i=m.days.get_loc(date)
                    assert m.buy[i,j[g.buy>0]].all() and m.sell[i,j[g.sell>0]].all()
                    np.add.at(units,j,(g.buy-g.sell)/g.price)
                    cash+=float((g.sell-g.buy-g.fee).sum())
                vector=m.marks["flat"][int(date!=final)][m.days.get_loc(date)]
                held=units>1e-10
                assert np.isfinite(vector[held]).all()
                observed=cash+np.dot(units[held],vector[held])
                mx=max(mx,abs(observed-row.nav),abs(cash-row.cash))
            assert mx<1e-9
            reconstruction.append(dict(scope=sample,days=len(q[q["style"]=="net"]),max_error=mx))
            if sample=="primary":
                net_terminal_units=units.copy()
    for r in a.itertuples():
        if not r.complete:continue
        if r.style=="net":
            units=net_terminal_units
        else:
            t=scores[scores[r.model+"_d"].eq(10)].copy()
            t["weight"]=1/t.groupby("signal_date").instrument.transform("size")
            daily,_,holds,_=accounts.account(m,t,e,"flat",.001,.002,r.model,True)
            assert np.isclose(daily[-1]["nav"],r.terminal_nav)
            units=np.zeros(m.n)
            for day,sym,u,*_ in reversed(holds):
                if day!=MAIN:break
                units[m.symbols.get_loc(sym)]=u
        held=units>1e-10
        move=np.dot(units[held],(m.marks["flat"][1][e,held]-m.marks["flat"][0][e,held]))
        close_nav=r.terminal_nav+move
        bm.append(dict(model=r.model,style=r.style,open_cagr=r.cagr,open_price_index_cagr=index_price**(252/(e-start))-1,
                       close_nav=close_nav,close_cagr=close_nav**(252/(e-start+1))-1,tr_index_cagr=total_index**(252/(e-start+1))-1,
                       cagr_minus_tr=close_nav**(252/(e-start+1))-total_index**(252/(e-start+1))))
    pd.DataFrame(bm).to_csv(D/"benchmark.csv",index=False)
    original=pd.read_parquet(OLD/"local_cache/daily_accounts.parquet")
    for name in MODELS[:2]:
        ref=original.query("model==@name and portfolio=='D10' and scope=='primary' and cost=='main' and valuation=='flat'").set_index("date").nav
        cur=ledger.query("model==@name and scope=='primary' and cost=='main' and mode=='flat' and style=='full'").set_index("date").nav
        assert cur.index.equals(ref.index) and np.allclose(cur,ref,rtol=0,atol=1e-11)
    for f,h in json.loads((D/"inputs.json").read_text()).items():
        assert sha(f)==h,f
    dump(D/"validation.json",dict(original_sources_unchanged=True,primary_periods=len(p),all_periods=len(panel),
         original_main_accounts_replayed=2,original_order_rows=len(orders),max_zero_cost_netting_error=maxzero,
         ledger_reconstruction=reconstruction,folds_replayed=len(pd.read_csv(D/"replay.csv")),
         max_baseline_score_error=pd.read_csv(D/"replay.csv").max_error.max(),five_day_max_identity_error=scores.identity_err.max(),
         primary_original_fees=base.fees.sum(),primary_direct_overlap_fee=p.overlap_fee.sum()))
    print(pd.DataFrame(records).query("scope=='primary'")[["metric","n","mean","low","high","holm_p"]].to_string(index=False))
    print(a[["model","style","cagr","mdd"]].to_string(index=False))


if __name__=="__main__":
    main()
