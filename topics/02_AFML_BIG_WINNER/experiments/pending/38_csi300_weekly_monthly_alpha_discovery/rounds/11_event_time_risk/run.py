from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE,accounts
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market();days=m.days
e=pd.read_csv(HERE.parent/"10_guidance_reaction/results/matched_events.csv",usecols=["signal_date","exit_date","stock","control","relative"],parse_dates=["signal_date"])
# The control was selected on the announcement reaction date before either exit was checked.
e=e[e.relative.lt(0)&e.control.notna()].sort_values(["signal_date","stock"])
targets=pd.read_parquet(ROOT/"results/targets.parquet").query("model==@R")
cal=targets.drop_duplicates("signal_date").sort_values("entry_date")
hold=pd.read_parquet(ROOT/"results/holdings.parquet").query("model==@R")
daily=pd.read_parquet(ROOT/"results/daily.parquet").query("model==@R and cost=='base' and scope!='whole'").set_index(["scope","date"])
w=pd.read_csv(ROOT/"results/windows.csv",parse_dates=["signal_date"]).query("model==@R and cost=='base' and scope!='whole'")
baseline={k:(1+g.set_index("signal_date").sort_index().open_net).cumprod().shift().fillna(1.) for k,g in w.groupby("scope")}
active={};rec=[]
for ev in e.itertuples():
    # Event close must lie strictly before the next original target's entry.
    date=ev.signal_date
    j=cal.entry_date.searchsorted(date,side="right")-1
    if j<0:continue
    row=cal.iloc[j]
    entry=days.get_loc(date)+1
    if entry>=row.exit_idx:continue
    scope="primary" if row.exit_date<=pd.Timestamp("2025-03-03") else "later"
    dayhold=hold[(hold.scope==scope)&(hold.date==date)]
    pos=dayhold[dayhold.instrument==ev.stock]
    if pos.empty:continue
    meta=dict(scope=scope,signal_date=row.signal_date,event_date=date,exit_date=row.exit_date,stock=ev.stock,peer=ev.control)
    key=(row.signal_date,ev.stock)
    if key in active:rec.append(meta|dict(status="already_replaced"));continue
    src,dst=m.symbols.get_indexer([ev.stock,ev.control])
    om=m.marks["flat"][0]
    jj=m.symbols.get_indexer(dayhold.instrument)
    prices=om[entry,jj]
    nav=daily.at[(scope,date),"cash"]+np.dot(dayhold.units,prices)
    budget=pos.units.iloc[0]*om[entry,src]
    preweight=budget/nav
    meta.update(weight=preweight)
    if not (m.sell[entry,src] and m.buy[entry,dst] and m.members[entry-1,dst]):
        rec.append(meta|dict(status="blocked_entry",contribution=0.,stress=0.));continue
    active[key]=True
    x=row.exit_idx
    if not (m.sell[x,src] and m.sell[x,dst] and np.isfinite(nav)):
        rec.append(meta|dict(status="unknown_exit"));continue
    # Normalize to pre-rebalance open NAV of the parent H10 for summing disjoint lots.
    parent=cal.iloc[j]
    assert np.isfinite(preweight)
    # Compute parent start NAV by compounding the previously reconciled H10s.
    start_nav=baseline[scope].loc[parent.signal_date]
    held_ret=m.o[x,src]/m.o[entry,src]*(1-.002)
    alt_ret=(1-.002)/(1+.001)*m.o[x,dst]/m.o[entry,dst]*(1-.002)
    rec.append(meta|dict(status="ok",capital=budget/start_nav,contribution=budget/start_nav*(alt_ret-held_ret),
                         stress=budget/start_nav*(alt_ret-held_ret-.003)))
z=pd.DataFrame(rec);z.to_csv(OUT/"events.csv",index=False)
print(z.groupby(["scope","status"]).agg(n=("stock","size"),capital=("weight","sum"),edge=("contribution","sum")))
dump(OUT/"receipt.json",{str(f):sha(f) for f in [HERE/"PROTOCOL.md",Path(__file__),OUT/"events.csv",ROOT/"results/holdings.parquet",HERE.parent/"10_guidance_reaction/results/matched_events.csv"]})
