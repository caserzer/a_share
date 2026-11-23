from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"02_adaptive_revision"),str(HERE.parent/"06_midwindow_refresh")]
from evaluate import R,split
from scheduled_execution import net_account
R6=HERE.parent/"06_midwindow_refresh"

def measure(z,t,m,OUT):
    w=[];a=[];months=[];orders=[]
    for late,g in z.groupby(z.parent_date.isin(t[(t.model==R+"_original")&(t.entry_date>=split)].parent_date)):
        end=int(g.exit_idx.max());scope="later" if late else "primary"
        for cost,bf,sf in [("base",.001,.002),("zero",0,0),("double",.002,.004)]:
            d,o,st=net_account(m,g,end,"flat",bf,sf)
            meta=dict(scope=scope,cost=cost)
            d=d.set_index("date");idx=m.days.get_indexer(d.index)
            o["units"]=(o.buy-o.sell)/o.price
            def matrix(col):
                return o.pivot(index="date",columns="instrument",values=col).reindex(index=d.index,columns=m.symbols).fillna(0.)
            u=matrix("units").cumsum();u=u.mask(u.abs()<1e-12,0.)
            op=pd.DataFrame(m.marks["flat"][0][idx],index=d.index,columns=m.symbols)
            close=pd.DataFrame(m.marks["flat"][1][idx],index=d.index,columns=m.symbols)
            if st["valuation_complete"]:close.iloc[-1]=op.iloc[-1]
            value=(u*close).mask(u==0,0.)
            assert value.notna().all().all()
            np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
            prior=u.shift().fillna(0.)
            before=(prior*op).mask(prior==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
            if cost=="base":
                orders.append(o.assign(**meta))
                prof=value-value.shift().fillna(0.)+matrix("sell")-matrix("buy")-matrix("fee")
                per=d.index.to_period("M")
                pnl=prof.groupby(per).sum().div(d.nav.shift().fillna(1.).groupby(per).first(),axis=0)
                months.append(pnl.stack().loc[lambda v:v!=0].rename("pnl").reset_index().set_axis(["month","instrument","pnl"],axis=1).assign(**meta))
            for date,h in g.groupby("parent_date"):
                e,x=h.entry_date.min(),h.exit_date.max()
                if x>d.index[-1]:continue
                stop=d.nav.iloc[-1] if x==m.days[end] else before.at[x]
                w.append(dict(**meta,signal_date=date,net=stop/before.at[e]-1))
            a.append(dict(**meta,**st,nav=d.nav.iloc[-1],cagr=d.nav.iloc[-1]**(252/(end-idx[0]))-1 if st["valuation_complete"] else np.nan,
                          mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min()))
    w=pd.DataFrame(w);keys=["scope","cost","signal_date"]
    orig=pd.read_csv(R6/"results/windows.csv",parse_dates=["signal_date"])
    for model in [R+"_original",R+"_reset",R+"_refresh","E1_78_original"]:
        ref=orig[orig.model==model].set_index(keys)
        order=pd.MultiIndex.from_frame(w[keys])
        w["vs_"+model]=w.net-ref.net.reindex(order).to_numpy()
        w["excess"]=w.net-(ref.net-ref.excess).reindex(order).to_numpy()
    w.to_csv(OUT/"windows.csv",index=False)
    pd.DataFrame(a).to_csv(OUT/"accounts.csv",index=False)
    pd.concat(months).to_parquet(OUT/"stock_month.parquet",index=False)
    pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
    print((w.groupby(["scope","cost"]).mean(numeric_only=True)*1e4).round(2).to_string())
