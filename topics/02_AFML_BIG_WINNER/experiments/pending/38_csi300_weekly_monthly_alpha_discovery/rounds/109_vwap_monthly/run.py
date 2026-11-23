from pathlib import Path
import sys
import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
out = here / "results"
source = here.parent / "107_vwap_early_challenge/results/pairs.csv"
sys.path.insert(0, str(here.parent / "02_adaptive_revision"))
from evaluate import PRIVATE, accounts
from core import sha, dump

accounts.OUT = out
market = accounts.Market()
pairs = pd.read_csv(source, parse_dates=["day", "entry", "exit"])
anchor = market.days.get_loc("2021-01-08")
idx = market.days.get_indexer(pairs.day)
maturity = market.days[idx + 21]
pairs = pairs.loc[((idx-anchor) % 20 == 0) & (maturity.year == 2017)].copy()
en = market.days.get_indexer(pairs.entry)
ex = en + 20
j = market.symbols.get_indexer(pairs.high)
k = market.symbols.get_indexer(pairs.low)
assert min(en.min(), j.min(), k.min()) >= 0
h = market.o[ex,j] / market.o[en,j]
l = market.o[ex,k] / market.o[en,k]
can = (np.isfinite(h) & np.isfinite(l) & (h > 0) & (l > 0)
       & market.buy[en,j] & market.sell[en,k] & market.sell[ex,j] & market.buy[ex,k])
pairs["exit20"] = market.days[ex]
pairs["complete20"] = can
pairs["gross20"] = np.where(can, h-l, np.nan)
pairs["net20"] = np.where(can, h-l-(.003+.002*h+.001*l), np.nan)
pairs.to_csv(out / "pairs.csv", index=False)
common = pairs[pairs.complete & pairs.complete20].copy()
common["known20"] = common.budget * common.net20
groups = common.groupby("day")
dates = groups[["gross", "net", "gross20", "net20"]].mean().mul(1e4)
dates["known20"] = groups.known20.sum()*1e4
dates["active"] = groups.budget.sum()
dates.to_csv(out / "dates.csv")
print(len(pairs),pairs.complete.sum(),can.sum(),len(common), len(dates))
print(dates.mean(), dates.net20.gt(0).sum(), dates.net20.sort_values().iloc[:-3].mean())
files = [source, here/"PROTOCOL.md", Path(__file__), out/"pairs.csv", out/"dates.csv",
         Path(accounts.__file__), *[PRIVATE/(name+".parquet") for name in
         ["qfq_open","open","limits/daily","opening_trade_status_v2","suspensions/daily"]]]
dump(out/"receipt.json", {str(f):sha(f) for f in files})
