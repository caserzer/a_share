from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
src=here.parent/"110_overnight_composition/results/pairs.parquet"
ledger=here.parent/"103_frequency_orders/results/attribution/stock_days.parquet"
q=pd.read_parquet(src).rename(columns={"exit_date_a":"date","phase_a":"phase"})
keys=["phase","date"]
orders=pd.read_parquet(ledger,filters=[("model","=","original")])
orders["net_sell"]=(orders.sold-orders.purchased).clip(lower=0)
# Rebalances from independent scopes can share a calendar date; match both legs within the same scope.
for side in ["a","b"]:
    ticker="instrument_"+side
    lookup=orders.loc[orders.net_sell.gt(0),keys+["scope","instrument","net_sell"]].rename(columns={"instrument":ticker,"net_sell":"buy_"+side})
    q=q.merge(lookup,on=keys+[ticker]+(["scope"] if side=="b" else []),how="inner",validate="m:1" if side=="b" else "1:m")
fields={k:PRIVATE/(k+".parquet") for k in ["open","close","volume","limits/daily","qfq_open","qfq_close"]}
frames={k:pd.read_parquet(f) for k,f in fields.items()}
lim=frames.pop("limits/daily")
lim["instrument"]=lim.ts_code.str[-2:]+lim.ts_code.str[:6]
lim["date"]=pd.to_datetime(lim.trade_date)
frames["limit"]=lim.pivot(index="date",columns="instrument",values="down_limit")
for side in ["a","b"]:
    values={}
    for name,frame in frames.items():
        ix=frame.index.get_indexer(q.date);jx=frame.columns.get_indexer(q["instrument_"+side])
        assert min(ix.min(),jx.min())>=0
        values[name]=frame.to_numpy()[ix,jx]
    c,o,limit,vol=[values[k] for k in ["close","open","limit","volume"]]
    ok=np.isfinite(c+o+limit+vol+values["qfq_close"]+values["qfq_open"])&(c>0)&(o>0)&(limit>0)&(vol>0)&(values["qfq_open"]>0)&(values["qfq_close"]>0)
    q["valid_"+side]=ok
    q["blocked_"+side]=ok&(c<=limit+1e-6)
    q["delay_"+side]=np.where(ok,(values["qfq_close"]/values["qfq_open"])*np.where(q["blocked_"+side],1.,.998)-.998,np.nan)
weight=q[["buy_a","buy_b"]].min(axis=1)
high_a=q.daytime_diff>0
q["rule"]=weight*np.where(high_a,q.delay_a,q.delay_b)*1e4
q["mirror"]=weight*np.where(high_a,q.delay_b,q.delay_a)*1e4
q["diff"]=q.rule-q.mirror
q["budget"]=weight
q["month"]=q.date.dt.to_period("M").astype(str)
q.to_parquet(out/"orders.parquet",index=False)
files=[src,ledger,*fields.values(),Path(__file__),here/"PROTOCOL.md",out/"orders.parquet"]
summary=[]
monthly=[]
for scope,g in q.groupby("scope"):
    source=here.parent/("103_frequency_orders/results/"+scope+"_daily.parquet")
    files.append(source)
    daily=pd.read_parquet(source,filters=[("model","=","original")])
    common=set.intersection(*[set(h.date.dt.to_period("M").sort_values().unique()[1:-1].astype(str)) for _,h in daily.groupby("phase")])
    mon=g[g.month.isin(common)].groupby("month")[["rule","mirror","diff"]].sum(min_count=1).reindex(sorted(common),fill_value=0)/10
    mon["scope"]=scope
    monthly.append(mon)
    summary.append(dict(scope=scope,pairs=len(g),unknown=(~(g.valid_a & g.valid_b)).sum(),blocked=(g.blocked_a|g.blocked_b).sum(),months=len(mon),rule=mon.rule.mean(),mirror=mon.mirror.mean(),diff=mon["diff"].mean(),ex3=mon.rule.sort_values().iloc[:-3].mean()))
pd.concat(monthly).to_csv(out/"months.csv")
s=pd.DataFrame(summary);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in files+[out/"months.csv",out/"summary.csv"]})
