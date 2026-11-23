from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts,split
from core import dump,sha
accounts.OUT=out
market=accounts.Market()
source=out/"pairs.csv"
p=pd.read_csv(source,parse_dates=["day"])
rows=[]
for row in p.itertuples():
    a,b=market.symbols.get_indexer([row.buy,row.sell])
    i,j=row.entry,row.exit
    assert min(a,b)>=0 and j-i==10
    quotes=market.o[[i,j]][:,[a,b]]
    can=market.buy[i,a] and market.sell[i,b] and market.sell[j,a] and market.buy[j,b]
    valid=np.isfinite(quotes).all() and (quotes>0).all() and can
    gross=fee=np.nan
    if valid:
        end_buy,end_sell=quotes[1]/quotes[0]
        gross=end_buy-end_sell
        fee=.003+.002*end_buy+.001*end_sell
    scope=str(row.day.year) if row.day.year<2021 else ("primary" if market.days[i]<split else "later")
    rows.append(dict(day=row.day,scope=scope,sleeve=row.sleeve,event=row.event,peer=row.peer,gross=gross,fee=fee,net=gross-fee,budget=row.budget,complete=valid))
r=pd.DataFrame(rows)
r.to_csv(out/"event_returns.csv",index=False)
summary=[]
for (scope,sleeve),g in r.groupby(["scope","sleeve"]):
    q=g[g.complete]
    daily=q.groupby("day")[["gross","net"]].mean()*1e4
    summary.append(dict(scope=scope,sleeve=sleeve,matched=len(g),complete=len(q),dates=len(daily),gross_bp=daily.gross.mean(),net_bp=daily.net.mean(),capital_coverage=q.budget.sum()/g.budget.sum()))
pd.DataFrame(summary).to_csv(out/"event_summary.csv",index=False)
dump(out/"event_receipt.json",{str(f):sha(f) for f in [Path(__file__),source,out/"event_summary.csv",out/"event_returns.csv",out/"target_receipt.json",Path(accounts.__file__),*[PRIVATE/(k+".parquet") for k in ["qfq_open","open","daily_members","limits/daily","opening_trade_status_v2"]]]})
