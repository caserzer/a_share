from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R,E,EP,evaluate
from core import sha,dump
OUT=HERE/"results"; OUT.mkdir(exist_ok=True)
basefile=ROOT/"results/targets.parquet"
oldfile=EP/"extensions/original78_rankic_20261118/local_cache/weekly_predictions.parquet"
newfile=EP/"extensions/intraday_reversal_20261122/results/scores.parquet"
base=pd.read_parquet(basefile).query("model in [@R,@E]")
dates=pd.read_parquet(PRIVATE/"qfq_close.parquet",columns=[]).index
old=pd.read_parquet(oldfile)
new=pd.read_parquet(newfile).dropna(subset=["exit_date"])
history={d:g.set_index("instrument")[R].rank(pct=True) for d,g in old.groupby("signal_date")}
obs=pd.DatetimeIndex(sorted(history))
portfolios=[base]; audit=[]
for d,g in new.groupby("signal_date"):
    i=dates.get_loc(d)
    j=obs.searchsorted(dates[i-5],side="right")-1
    g=g.copy()
    g["current"]=g[R].rank(pct=True)
    past=obs[j] if j>=0 else pd.NaT
    age=i-dates.get_loc(past) if j>=0 else np.nan
    g["prior"]=g.instrument.map(history[past]) if j>=0 and age<=10 else np.nan
    if g.prior.notna().any(): assert 5<=age<=10
    audit.append(dict(signal_date=d,prior_date=past,trading_days=age,available=g.prior.count(),eligible=len(g)))
    g["delayed"]=g.prior.fillna(g.current)
    g["smooth"]=(g.current+g.delayed)/2
    n=g[R+"_d"].eq(10).sum()
    for name in ["smooth","delayed"]:
        h=g.sort_values([name,"instrument"]).tail(n).copy()
        portfolios.append(h.assign(model=name,weight=1/n))
pd.concat(portfolios).to_parquet(OUT/"targets.parquet",index=False)
pd.DataFrame(audit).to_csv(OUT/"signal_dates.csv",index=False)
dump(OUT/"selection.json",{str(p.relative_to(ROOT.parent)):sha(p) for p in [oldfile,newfile,basefile,HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet"]})
evaluate(OUT,12)
