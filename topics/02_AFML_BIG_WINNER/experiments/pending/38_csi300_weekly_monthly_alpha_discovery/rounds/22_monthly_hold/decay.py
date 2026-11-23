"""Score the same eligible, priced stocks at two ages against the same second-leg outcome."""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,E,accounts
from core import sha,dump
out=HERE/"results";accounts.OUT=out;m=accounts.Market()
src=HERE.parent/"17_calendar_challenge/results/point_in_time_scores.parquet"
p=pd.read_parquet(src)
w=pd.read_csv(out/"windows.csv",parse_dates=["date","middle_hold","exit_hold"])
rows=[]
for row in w[(w.model==R)&(w.cost=="base")].itertuples():
    phase=row.phase
    e=m.days.get_loc(row.middle_hold);x=m.days.get_loc(row.exit_hold)
    s=p[p.offset==phase].set_index(["signal_date","instrument"])
    old=s.loc[row.date,[E,R]]
    current=s.loc[m.days[e-1],[E,R]]
    both=current.join(old,how="inner",lsuffix="_new",rsuffix="_old")
    j=m.symbols.get_indexer(both.index);assert min(j)>=0
    ok=m.buy[e,j]&m.sell[x,j]
    g=both.loc[ok].copy()
    g["ret"]=m.o[x,j[ok]]/m.o[e,j[ok]]-1
    for model in [E,R]:
        corr=g[[model+"_old",model+"_new","ret"]].corr(method="spearman").ret
        rows.append(dict(phase=phase,scope=row.scope,date=row.date,model=model,common=len(both),known=len(g),
                  old_ic=corr[model+"_old"],new_ic=corr[model+"_new"]))
z=pd.DataFrame(rows);z["new_minus_old"]=z.new_ic-z.old_ic
z.to_csv(out/"second_leg_date_ic.csv",index=False)
agg=z.groupby(["phase","scope","model"]).agg(n=("date","size"),common=("common","sum"),known=("known","sum"),old_ic=("old_ic","mean"),new_ic=("new_ic","mean"),gain=("new_minus_old","mean"))
agg.to_csv(out/"second_leg_summary.csv");print(agg.round(4))
dump(out/"decay_receipt.json",{str(f):sha(f) for f in [src,Path(__file__),out/"windows.csv",out/"second_leg_summary.csv"]})
