import json
import pandas as pd
import numpy as np
from evaluate import accounts, PRIVATE, R, E, split
from execution import net_account

def replay(t,OUT):
    m=accounts.Market();w=[];months=[];ac=[];orders=[]
    idxraw=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
    bench=pd.DataFrame(idxraw["items"],columns=idxraw["fields"]);tr=bench.set_index(pd.to_datetime(bench.trade_date)).close
    for (model,late),g in t.groupby(["model",t.entry_date>=split]):
        end=int(g.exit_idx.max());scope="later" if late else "primary"
        for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
            d,o,st=net_account(m,g,end,"flat",bf,sf)
            meta=dict(model=model,scope=scope,cost=cost)
            d=d.set_index("date")
            idx=m.days.get_indexer(d.index)
            o["units"]=(o.buy-o.sell)/o.price
            def mat(col):
                return o.pivot(index="date",columns="instrument",values=col).reindex(index=d.index,columns=m.symbols).fillna(0.)
            u=mat("units").cumsum();u=u.mask(u.abs()<1e-12,0.)
            op=pd.DataFrame(m.marks["flat"][0][idx],index=d.index,columns=m.symbols)
            cm=pd.DataFrame(m.marks["flat"][1][idx],index=d.index,columns=m.symbols)
            if st["valuation_complete"]:cm.iloc[-1]=op.iloc[-1]
            value=(u*cm).mask(u==0,0.)
            assert value.notna().all().all()
            np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
            prev=u.shift().fillna(0.)
            pre=(prev*op).mask(prev==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
            if cost=="base":
                orders.append(o.assign(**meta))
                profit=value-value.shift().fillna(0.)+mat("sell")-mat("buy")-mat("fee")
                per=d.index.to_period("M")
                pn=profit.groupby(per).sum().div(d.nav.shift().fillna(1.).groupby(per).first(),axis=0)
                months.append(pn.stack().loc[lambda v:v!=0].rename("pnl").reset_index().set_axis(["month","instrument","pnl"],axis=1).assign(**meta))
            for dt,h in g.groupby("signal_date"):
                entry,exit=h.entry_date.iloc[0],h.exit_date.iloc[0]
                if exit>d.index[-1]:continue
                v=d.nav.iloc[-1] if exit==m.days[end] else pre.at[exit]
                w.append(dict(**meta,signal_date=dt,net=v/pre.at[entry]-1,index=tr.at[exit]/tr.at[entry]-1))
            ac.append(dict(**meta,**st,end=d.index[-1],nav=d.nav.iloc[-1],mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min(),
                        cagr=d.nav.iloc[-1]**(252/(end-idx[0]))-1 if st["valuation_complete"] else np.nan))
    w=pd.DataFrame(w);keys=["scope","cost","signal_date"]
    for ref in [R,E]:
        rr=w[w.model==ref].set_index(keys).net
        w["vs_"+ref]=w.net-rr.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
    w.to_csv(OUT/"windows.csv",index=False)
    pd.DataFrame(ac).to_csv(OUT/"accounts.csv",index=False)
    pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
    mo=pd.concat(months);mo.to_parquet(OUT/"stock_month.parquet",index=False)
    mon=mo.groupby(["scope","model","month"]).pnl.sum().reset_index()
    mon["delta"]=mon.pnl-mon[mon.model==R].set_index(["scope","month"]).pnl.reindex(pd.MultiIndex.from_frame(mon[["scope","month"]])).to_numpy()
    mon.to_csv(OUT/"months.csv",index=False)
