from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump

pairs_file=here.parent/"113_exit_session/results/orders.parquet"
ledger=here.parent/"103_frequency_orders/results/attribution/stock_days.parquet"
p=pd.read_parquet(pairs_file)
keys=["scope","phase","date"]
orders=pd.read_parquet(ledger,filters=[("model","=","original")])
orders["net"]=orders.purchased-orders.sold
buys=orders[orders.net>0].copy()
fields={k:PRIVATE/(k+".parquet") for k in ["qfq_open","qfq_close","close","volume","limits/daily"]}
frames={k:pd.read_parquet(f) for k,f in fields.items()}
lim=frames.pop("limits/daily")
lim["instrument"]=lim.ts_code.str[-2:]+lim.ts_code.str[:6]
lim["date"]=pd.to_datetime(lim.trade_date)
frames["upper"]=lim.pivot(index="date",columns="instrument",values="up_limit")
for k,f in frames.items():
    i=f.index.get_indexer(buys.date);j=f.columns.get_indexer(buys.instrument)
    assert min(i.min(),j.min())>=0
    buys[k]=f.to_numpy()[i,j]
assert np.isfinite(buys[list(frames)]).all().all() and buys[list(frames)].gt(0).all().all()
buys["closing_block"]=buys.close>=buys.upper-1e-6
buys["open_mark"]=buys.net*buys.qfq_close/buys.qfq_open
buys["close_mark"]=buys.net*np.where(buys.closing_block,1.,1/1.001)
b=buys.groupby(keys)[["net","open_mark","close_mark"]].sum()
# An actual purchase budget includes its fee. At the close, unspent cash keeps its full value.
b["base_value"]=b.open_mark/b.net/1.001
b["late_value"]=b.close_mark/b.net
g=p.groupby(keys).budget.sum().to_frame("sell_plan").join(b,how="left").fillna(0)
g["scale"]=np.minimum(1,g.net*1.001/(g.sell_plan*.998))
q=p.merge(g.reset_index(),on=keys,validate="m:1")
assert q.valid_a.all() and q.valid_b.all()
for name,side_a in [("overnight",q.daytime_diff<0),("daytime",q.daytime_diff>0)]:
    delta=np.where(side_a,q.delay_a,q.delay_b)
    blocked=np.where(side_a,q.blocked_a,q.blocked_b)
    # The exit diagnostic stores the marked/realized close value less opening sale proceeds.
    late=(.998+delta)*np.where(blocked,1.,q.late_value)
    q[name]=1e4*q.budget*q.scale*(late-.998*q.base_value)
q["diff"]=q.overnight-q.daytime
q.to_parquet(out/"events.parquet",index=False)
calendar=here.parent/"113_exit_session/results/months.csv"
c=pd.read_csv(calendar)[["scope","month"]].set_index(["scope","month"])
months=c.join(q.groupby(["scope","month"])[["overnight","daytime","diff"]].sum()/10).fillna(0)
months.to_csv(out/"months.csv")
s=months.groupby("scope").mean()
s["ex3"]=months.groupby("scope").overnight.apply(lambda x:x.sort_values().iloc[:-3].mean())
s.to_csv(out/"summary.csv");print(s.round(3));print("cash-constrained events",sum(g.scale<1-1e-10),"of",len(g))
files=[ledger,pairs_file,calendar,*fields.values(),here/"PROTOCOL.md",Path(__file__),out/"events.parquet",out/"months.csv",out/"summary.csv"]
dump(out/"receipt.json",{str(f):sha(f) for f in files})
