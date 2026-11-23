"""Evaluate saved targets for any EP38 round with the two sealed baselines."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EP=ROOT.parent/"37_momentum_reversal_joint_alpha_h10"
sys.path[:0]=[str(EP/"code"),str(EP/"extensions/intraday_reversal_20261122")]
from execution import net_account
from core import PRIVATE, dump
import accounts
R,E="RANK_MSE_78","E1_78"
split=pd.Timestamp("2025-03-03")

def evaluate(out, comparisons):
    accounts.OUT=out
    m=accounts.Market()
    t=pd.read_parquet(out/"targets.parquet")
    bench=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
    b=pd.DataFrame(bench["items"],columns=bench["fields"])
    index=b.set_index(pd.to_datetime(b.trade_date)).close
    windows=[]; months=[]; stock=[]; orders=[]; summaries=[]; failures=[]
    for (model,late),g in t.groupby(["model",t.entry_date.ge(split)]):
        scope="later" if late else "primary"
        end=int(g.exit_idx.max())
        for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0,0)]:
            d,o,status=net_account(m,g,end,"flat",bf,sf)
            meta=dict(scope=scope,model=model,cost=cost)
            failures.append(meta|status)
            d=d.set_index("date")
            o["units"]=(o.buy-o.sell)/o.price
            def mat(col):
                return o.pivot(index="date",columns="instrument",values=col).reindex(index=d.index,columns=m.symbols).fillna(0.)
            units=mat("units").cumsum()
            units=units.mask(units.abs()<1e-12,0.)
            days=m.days.get_indexer(d.index)
            op=pd.DataFrame(m.marks["flat"][0][days],index=d.index,columns=m.symbols)
            close=pd.DataFrame(m.marks["flat"][1][days],index=d.index,columns=m.symbols)
            if status["valuation_complete"]:
                close.iloc[-1]=op.iloc[-1]
            value=(units*close).mask(units==0,0.)
            assert value.notna().all().all()
            np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
            prev=units.shift().fillna(0.)
            pre=(prev*op).mask(prev==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
            if cost=="base":
                orders.append(o.assign(**meta))
                prof=value-value.shift().fillna(0.)+mat("sell")-mat("buy")-mat("fee")
                prior=d.nav.shift().fillna(1.)
                np.testing.assert_allclose(prof.sum(axis=1),d.nav-prior,atol=1e-9)
                per=d.index.to_period("M")
                month=prof.groupby(per).sum().div(prior.groupby(per).first(),axis=0)
                stock.append(month.stack().loc[lambda x:x!=0].rename("contribution").reset_index().set_axis(["month","instrument","contribution"],axis=1).assign(**meta))
                months.extend(dict(**meta,month=str(k),net=v) for k,v in month.sum(axis=1).items())
            for dt,h in g.groupby("signal_date"):
                first,last=h.entry_date.iloc[0],h.exit_date.iloc[0]
                if last>d.index[-1]:continue
                stop=d.nav.iloc[-1] if last==m.days[end] else pre.at[last]
                ret=stop/pre.at[first]-1
                period=d.loc[first:last] if last==m.days[end] else d[(d.index>=first)&(d.index<last)]
                windows.append(dict(**meta,signal_date=dt,net=ret,index=index.at[last]/index.at[first]-1,
                    fees=period.fees.sum()/pre.at[first],turnover=(period.buy+period.sell).sum()/pre.at[first]))
            summaries.append(dict(**meta,complete=status["valuation_complete"],nav=d.nav.iloc[-1],
                cagr=d.nav.iloc[-1]**(252/(end-days[0]))-1 if status["valuation_complete"] else np.nan,
                mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min()))
    w=pd.DataFrame(windows)
    monthly=pd.DataFrame(months)
    for table,keys in [(w,["signal_date","cost","scope"]),(monthly,["month","cost","scope"])]:
        for ref in [R,E]:
            base=table[table.model==ref].set_index(keys).net
            table["vs_"+ref]=table.net-base.reindex(pd.MultiIndex.from_frame(table[keys])).to_numpy()
    w["excess"]=w.net-w["index"]
    w.to_csv(out/"windows.csv",index=False)
    monthly.to_csv(out/"monthly.csv",index=False)
    pd.concat(stock).to_parquet(out/"stock_month.parquet",index=False)
    pd.concat(orders).to_parquet(out/"orders.parquet",index=False)
    a=pd.DataFrame(summaries)
    records=[]
    for (model,scope),g in w[w.cost=="base"].groupby(["model","scope"]):
        v=g["vs_"+R].to_numpy()
        rng=np.random.default_rng(38)
        n=len(v)
        start=rng.integers(n,size=(10000,(n+2)//3))
        samp=v[((start[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]].mean(axis=1)
        lo,hi=np.quantile(samp,[.025/comparisons,1-.025/comparisons])
        mon=monthly[(monthly.model==model)&(monthly.scope==scope)]["vs_"+R]
        wt=t[(t.model==model)&t.signal_date.isin(g.signal_date)].pivot(index="signal_date",columns="instrument",values="weight")
        rb=t[(t.model==R)&t.signal_date.isin(g.signal_date)].pivot(index="signal_date",columns="instrument",values="weight")
        active=wt.fillna(0.).sub(rb.fillna(0.),fill_value=0.).abs().sum(axis=1)/2
        vcost=w[(w.model==model)&(w.scope==scope)].groupby("cost")["vs_"+R].mean()
        rec=a[(a.model==model)&(a.scope==scope)&(a.cost=="base")].iloc[0]
        if rec.complete:
            assert abs((1+g.net).prod()-rec.nav)<1e-9
        records.append(dict(model=model,scope=scope,n=n,mean=v.mean(),lo=lo,hi=hi,vs_e1=g["vs_"+E].mean(),
          excess=g.excess.mean(),cagr=rec.cagr,mdd=rec.mdd,trigger=int((active>1e-10).sum()),capital=active.mean(),
          ex3=mon.drop(mon.nlargest(3).index).mean(),double=vcost["double"],zero=vcost["zero"]))
    pd.DataFrame(records).to_csv(out/"summary.csv",index=False)
    a.to_csv(out/"accounts.csv",index=False)
    dump(out/"valuation.json",failures)
    old=pd.read_csv(ROOT/"results/windows.csv",parse_dates=["signal_date"])
    for ref in [R,E]:
        z=w[w.model==ref].merge(old[(old.model==ref)&(old.scope!="whole")],on=["signal_date","cost","scope"],validate="1:1")
        assert len(z)==417
        np.testing.assert_allclose(z.net_x,z.open_net,atol=1e-12)
    print(pd.DataFrame(records).round(5).to_string(index=False))

if __name__=="__main__":
    evaluate(HERE/"results",6)
