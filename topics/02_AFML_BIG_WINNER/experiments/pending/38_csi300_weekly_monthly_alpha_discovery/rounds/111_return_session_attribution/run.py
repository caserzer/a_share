from pathlib import Path
import sys
import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
out = here / "results"
sys.path.insert(0, str(here.parent / "02_adaptive_revision"))
from evaluate import accounts, PRIVATE
from core import sha, dump

accounts.OUT = out
market = accounts.Market()
src = here.parent / "110_overnight_composition/results/pairs.parquet"
pairs = pd.read_parquet(src)
fields = {n: PRIVATE/(n+".parquet") for n in ["qfq_close","qfq_open","volume"]}
close, opening, vol = [pd.read_parquet(f).reindex(index=market.days,columns=market.symbols).to_numpy() for f in fields.values()]
en = pairs.entry_idx_a.to_numpy()
ex = pairs.exit_idx_a.to_numpy()
assert (ex-en == 10).all() and (market.days[en] == pairs.entry_date_a).all()
prefer = pairs.daytime_diff.gt(0)
high = market.symbols.get_indexer(pairs.instrument_a.where(prefer,pairs.instrument_b))
low = market.symbols.get_indexer(pairs.instrument_b.where(prefer,pairs.instrument_a))
assert min(high.min(),low.min()) >= 0
complete = market.buy[en,high] & market.sell[en,low] & market.sell[ex,high] & market.buy[ex,low]
parts = []
for symbol in [high,low]:
    i = en[:,None]+np.arange(10)
    a = opening[i,symbol[:,None]]
    b = close[i,symbol[:,None]]
    c = opening[i+1,symbol[:,None]]
    mask = np.isfinite(a+b+c) & (a>0) & (b>0) & (c>0) & (vol[i,symbol[:,None]]>0)
    complete &= mask.all(axis=1)
    parts.append(np.stack([(b-a).sum(axis=1),(c-b).sum(axis=1),c[:,-1]-a[:,0]],axis=1)/a[:,0,None])
v = parts[0]-parts[1]
np.testing.assert_allclose(v[complete,0]+v[complete,1],v[complete,2],atol=1e-11)
p = pairs[["signal_date","instrument_a","instrument_b"]].copy()
p["prefer_a"]=prefer
p["complete"]=complete
p["budget"]=pairs.weight_a/2
for j,k in enumerate(["intraday","overnight","total"]):
    p[k]=np.where(complete,v[:,j],np.nan)
p.to_parquet(out/"pairs.parquet",index=False)
daily=p.assign(active=p.budget.where(complete)).groupby("signal_date").agg(planned=("budget","size"),observed=("complete","sum"),active=("active","sum"))
for k in ["intraday","overnight","total"]:
    daily[k]=(p[k]*p.budget*1e4).groupby(p.signal_date).sum(min_count=1)
daily.to_csv(out/"dates.csv")
files=[src,*fields.values(),Path(accounts.__file__),Path(__file__),here/"PROTOCOL.md",out/"pairs.parquet",out/"dates.csv",
       *[PRIVATE/(n+".parquet") for n in ["open","limits/daily","opening_trade_status_v2","suspensions/daily"]]]
dump(out/"receipt.json",{str(f):sha(f) for f in files})
