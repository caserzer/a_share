from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,accounts,split
from core import sha,dump
from execution import net_account as legacy
from engine import net_account
accounts.OUT=OUT;m=accounts.Market()
old,new=m.symbols.get_indexer(["SH600837","SH601211"])
assert min(old,new)>=0
d=m.days;start=d.get_loc("2025-03-04");listing=d.get_loc("2025-03-17")
raw_open=pd.read_parquet(PRIVATE/"open.parquet");raw_close=pd.read_parquet(PRIVATE/"close.parquet")
old_raw=raw_close.iloc[:start,old].dropna().iloc[-1] if raw_close.columns.equals(m.symbols) else raw_close["SH600837"].iloc[:start].dropna().iloc[-1]
last=raw_close["SH600837"].iloc[:start].last_valid_index()
old_factor=m.c[d.get_loc(last),old]/old_raw
rate=.62*old_factor*raw_open.at[d[listing],"SH601211"]/m.o[listing,new]
action=dict(listing=listing,old=old,new=new,units_per_old=rate,old_factor=old_factor)
om,cm=m.marks["flat"]
assert not m.buy[start:listing,old].any() and not m.sell[start:listing,old].any()
for name in ["claim","last_close"]:
    o,c=om.copy(),cm.copy()
    for mat,raw in [(o,raw_open),(c,raw_close)]:
        mat[start:listing,old]=raw["SH601211"].iloc[start:listing].to_numpy()*old_factor*.62 if name=="claim" else old_raw*old_factor
        assert np.isfinite(mat[start:listing,old]).all()
    m.marks[name]=(o,c)
path=HERE.parent/"16_industry_pool/results/targets.parquet";targets=pd.read_parquet(path)
b=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
idx=pd.DataFrame(b["items"],columns=b["fields"]);tr=idx.set_index(pd.to_datetime(idx.trade_date)).close
windows=[];ac=[];trades=[];days=[];conversion=[]
for model,g in targets.groupby("model"):
    end=int(g.exit_idx.max());entry=int(g.entry_idx.min())
    for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
        full,orders,status=net_account(m,g,end,"claim",bf,sf,action)
        assert status["valuation_complete"],status
        check,_,old_status=legacy(m,g,end,"flat",bf,sf)
        assert check.date.iloc[-1]==d[start-1] and not old_status["valuation_complete"]
        np.testing.assert_allclose(full.iloc[:len(check)].nav,check.nav,atol=1e-12,rtol=0)
        alt,_,audit=net_account(m,g,end,"last_close",bf,sf,action)
        assert audit["valuation_complete"]
        np.testing.assert_allclose(alt.nav.iloc[-1],full.nav.iloc[-1],atol=1e-12,rtol=0)
        meta=dict(model=model,cost=cost)
        conv=status["conversion"];conversion.append(meta|conv|dict(max_mark_effect=(alt.nav-full.nav).abs().max()))
        full=full.set_index("date");ix=d.get_indexer(full.index)
        orders["units"]=(orders.buy-orders.sell)/orders.price
        changes=orders.pivot(index="date",columns="instrument",values="units").reindex(index=full.index,columns=m.symbols).fillna(0.)
        changes.loc[d[listing],"SH600837"]-=conv["old_units"]
        changes.loc[d[listing],"SH601211"]+=conv["credited"]
        u=changes.cumsum();u=u.mask(u.abs()<1e-12,0)
        opening=pd.DataFrame(m.marks["claim"][0][ix],index=full.index,columns=m.symbols)
        close=pd.DataFrame(m.marks["claim"][1][ix],index=full.index,columns=m.symbols);close.iloc[-1]=opening.iloc[-1]
        value=(u*close).mask(u==0,0)
        assert value.notna().all().all()
        np.testing.assert_allclose(value.sum(axis=1)+full.cash,full.nav,atol=1e-10)
        flow=orders.assign(flow=orders.sell-orders.buy-orders.fee).groupby("date").flow.sum()
        np.testing.assert_allclose(1+flow.reindex(full.index,fill_value=0.).cumsum(),full.cash,atol=1e-10)
        before=u.shift().fillna(0.)
        before.loc[d[listing],"SH600837"]=0.
        before.loc[d[listing],"SH601211"]+=conv["credited"]
        pre=(before*opening).mask(before==0,0).sum(axis=1,skipna=False)+full.cash.shift().fillna(1.)
        for h in g.drop_duplicates("signal_date").itertuples():
            finish=full.nav.iloc[-1] if h.exit_idx==end else pre.at[h.exit_date]
            windows.append(meta|dict(signal_date=h.signal_date,net=finish/pre.at[h.entry_date]-1,index=tr.at[h.exit_date]/tr.at[h.entry_date]-1))
        n=end-entry
        ac.append(meta|dict(nav=full.nav.iloc[-1],cagr=full.nav.iloc[-1]**(252/n)-1,
            mdd=(full.nav/np.maximum.accumulate(np.r_[1.,full.nav])[1:]-1).min(),liquidated=status["terminal_liquidated"]))
        if cost=="base":
            days.append(full.reset_index().assign(**meta));trades.append(orders.assign(**meta))
w=pd.DataFrame(windows);a=pd.DataFrame(ac)
for (model,cost),g in w.groupby(["model","cost"]):
    sel=a[(a.model==model)&(a.cost==cost)]
    assert len(g)==139 and abs((1+g.net).prod()-sel.nav.iloc[0])<1e-10
for ref in [R,E]:
    b=w[w.model==ref].set_index(["cost","signal_date"]).net
    w["delta_"+ref]=w.net-b.reindex(pd.MultiIndex.from_frame(w[["cost","signal_date"]])).to_numpy()
pd.concat(days).to_parquet(OUT/"daily.parquet",index=False);pd.concat(trades).to_parquet(OUT/"orders.parquet",index=False)
w.to_csv(OUT/"windows.csv",index=False);a.to_csv(OUT/"accounts.csv",index=False)
pd.DataFrame(conversion).to_csv(OUT/"conversion.csv",index=False)
dump(OUT/"verification.json",dict(prior_prefix_equal=True,whole_period_returns_reconciled=True,all_cash_and_marked_holdings_reconciled=True,
     last_quote=last,locked_days=listing-start,raw_open_0317=raw_open.at[d[listing],"SH601211"],old_factor=old_factor,
     sha256={str(f):sha(f) for f in [path,PRIVATE/"open.parquet",PRIVATE/"close.parquet",PRIVATE/"qfq_open.parquet",PRIVATE/"qfq_close.parquet",Path(__file__),HERE/"engine.py",HERE/"PROTOCOL.md"]}))
print(a.query("cost=='base'").to_string(index=False))
print((w[w.model=="early_model"].groupby("cost")["delta_"+R].mean()*1e4).to_string())
