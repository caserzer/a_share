from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True)
prev=here.parent/"38_all_phases/results"
complete=prev/"monthly_complete.csv"
idxfile=PRIVATE/"net_excess_20261116/H00300.CSI.json"
b=json.loads(idxfile.read_text())["data"]
frame=pd.DataFrame(b["items"],columns=b["fields"])
benchmark=frame.set_index(pd.to_datetime(frame.trade_date)).close.sort_index()
benchmark=benchmark.groupby(benchmark.index.to_period("M")).last()
inputs=[complete,idxfile,Path(__file__),here/"PROTOCOL.md"]
common=pd.read_csv(complete)
sleeves=[];orders=[]
for phase in range(10):
    d=prev/str(phase)
    inputs.extend([d/"months.csv",d/"accounts.csv",d/"orders.parquet"])
    mon=pd.read_csv(d/"months.csv").sort_values("month")
    end=pd.read_csv(d/"accounts.csv").query('cost=="base"').set_index(["scope","model"]).nav
    mon["capital"]=mon.groupby(["scope","model"]).pnl.transform(lambda x:.1*(1+x).cumprod())
    np.testing.assert_allclose(mon.groupby(["scope","model"]).capital.last().sort_index(),.1*end.sort_index(),atol=1e-11)
    sleeves.append(mon.assign(phase=phase))
    o=pd.read_parquet(d/"orders.parquet");o=o[(o.buy+o.sell)>0].copy()
    assert o.cost.eq("base").all() and not ((o.buy>0)&(o.sell>0)).any()
    # After delivery this lot is sold as SH600150; put the order on successor price basis.
    conversion=(o.instrument=="SH601989")&(o.date>=pd.Timestamp("2025-09-16"))
    if conversion.any():
        assert o.loc[conversion,"sell"].gt(0).all()
        successor=PRIVATE/"qfq_open.parquet"
        inputs.append(successor)
        o.loc[conversion,"price"]=o.loc[conversion,"date"].map(pd.read_parquet(successor,columns=["SH600150"]).iloc[:,0])
        o.loc[conversion,"instrument"]="SH600150"
    orders.append(o.assign(phase=phase))
all_orders=pd.concat(orders)
all_orders[["buy","sell","fee"]]*=.1
keys=["scope","model","date","instrument"]
price=all_orders.groupby(keys).price.agg(["min","max"])
np.testing.assert_allclose(price["min"],price["max"],rtol=1e-10)
by=all_orders.groupby(keys).agg(buy=("buy","sum"),sell=("sell","sum"),fee=("fee","sum"),phases=("phase","nunique"))
by["crossed"]=by[["buy","sell"]].min(axis=1)
by["saved"]=by.crossed*.003
assert (by.loc[by.crossed.gt(0),"phases"]>1).all()
np.testing.assert_allclose(by.fee-by.saved,(by.buy-by.sell).clip(lower=0)*.001+(by.sell-by.buy).clip(lower=0)*.002,atol=1e-13)
by[by.crossed.gt(0)].to_csv(out/"crossed_orders.csv")
by=by.reset_index();by["month"]=by.date.dt.to_period("M").astype(str)
money=by.groupby(["scope","model","month"])[["buy","sell","fee","crossed","saved"]].sum()
sleeves=pd.concat(sleeves)
rows=[];months=[]
for scope,g in common.groupby("scope"):
    full=g.pivot(index="month",columns="phase",values="delta").dropna().index
    assert len(full)>0
    for model,z in sleeves[sleeves.scope==scope].groupby("model"):
        caps=z.pivot(index="month",columns="phase",values="capital").sort_index()
        before=str(pd.Period(full[0],freq="M")-1)
        # A sleeve awaiting first entry is still worth its original allocation.
        period=[before,*full];nav=caps.reindex(period).ffill().fillna(.1).sum(axis=1)
        t=money.loc[(scope,model)].sort_index()
        cum=t.saved.cumsum().reindex(period,method="ffill").fillna(0)
        merged=nav+cum
        idx=benchmark.loc[pd.PeriodIndex(period,freq="M")].to_numpy()
        idxreturns=idx[1:]/idx[:-1]-1
        months.append(pd.DataFrame(dict(scope=scope,model=model,month=full,net=merged.pct_change().iloc[1:].to_numpy(),
                    unmerged=nav.pct_change().iloc[1:].to_numpy(),index=idxreturns)))
        f=t.reindex(full,fill_value=0).sum()
        rows.append(dict(scope=scope,model=model,months=len(full),start=full[0],end=full[-1],start_capital=merged.iloc[0],end_capital=merged.iloc[-1],
            net_return=merged.iloc[-1]/merged.iloc[0]-1,index_return=idx[-1]/idx[0]-1,
            fee=f.fee,turnover=f.buy+f.sell,crossed=f.crossed,saved_bp=f.saved/merged.iloc[0]*1e4))
z=pd.concat(months);keys=["scope","month"]
for ref in [R,E,"momentum"]:
    z["vs_"+ref]=z.net-z[z.model==ref].set_index(keys).net.reindex(pd.MultiIndex.from_frame(z[keys])).to_numpy()
z.to_csv(out/"months.csv",index=False)
s=pd.DataFrame(rows);s.to_csv(out/"accounts.csv",index=False)
print(s[["scope","model","months","net_return","crossed","saved_bp"]].round(6).to_string(index=False))
print(z[z.model=="early_model"].groupby("scope")[["vs_"+R,"vs_"+E]].mean()*1e4)
dump(out/"receipt.json",{str(p):sha(p) for p in [*inputs,out/"accounts.csv",out/"months.csv",out/"crossed_orders.csv"]})
