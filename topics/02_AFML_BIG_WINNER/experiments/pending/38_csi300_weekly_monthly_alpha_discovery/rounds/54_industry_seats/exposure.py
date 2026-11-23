from pathlib import Path
import sys
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,split
from core import sha,dump
out=here/"results";src=here.parent/"50_training_support/results"
files=[src/"targets.parquet",out/"targets.parquet",Path(__file__)]
w=pd.concat([pd.read_parquet(f) for f in files[:2]])
w["scope"]=w.entry_date.ge(split).map({True:"later",False:"primary"})
w=w.pivot(index=["scope","phase","signal_date","instrument"],columns="model",values="weight").fillna(0.)
budget=(w.sub(w[R],axis=0).abs()/2).groupby(level=[0,1,2]).sum().stack().rename("active")
rows=[];refs=[]
for phase in range(10):
    d=out/str(phase);old=src/str(phase)
    for root in [d,old]:
        o=root/"orders.parquet";f=root/"windows.csv";files.extend([o,f])
        orders=pd.read_parquet(o)
        # Orders are in account units. Divide by the reconstructed NAV at entry.
        win=pd.read_csv(f,parse_dates=["signal_date"]).sort_values("signal_date").query('cost=="base"').copy()
        win["entry_nav"]=win.groupby(["scope","model"]).net.transform(lambda v:(1+v).cumprod().shift(fill_value=1.))
        sched=pd.read_parquet(out/"targets.parquet",columns=["phase","signal_date","entry_date"])
        dates=sched[sched.phase==phase].drop_duplicates().set_index("signal_date").entry_date
        win["entry"]=win.signal_date.map(dates)
        grouped=orders.query('cost=="base"').groupby(["scope","model"])
        for key,h in win.groupby(["scope","model"]):
            ix=pd.DatetimeIndex(h.entry)
            v=grouped.get_group(key).copy()
            pos=ix.searchsorted(v.date,side="right")-1
            assert min(pos)>=0
            v["signal_date"]=h.signal_date.to_numpy()[pos]
            turnover=v.assign(traded=v.buy+v.sell).groupby("signal_date")[["traded","fee"]].sum().reindex(h.signal_date,fill_value=0)
            for col in ["traded","fee"]:
                h=h.assign(**{col:turnover[col].to_numpy()/h.entry_nav.to_numpy()})
            rows.append(h.assign(phase=phase))
a=pd.concat(rows).set_index(["scope","phase","signal_date","model"]).sort_index()
a["active"]=budget.reindex(a.index)
for ref in [R,E]:
    a["vs_"+ref]=a.net-a.xs(ref,level="model").net.reindex(a.index.droplevel("model")).to_numpy()
a["vs_index"]=a.net-a["index"]
assert a[["active","vs_"+R,"vs_"+E,"vs_index"]].notna().all().all()
a.to_csv(out/"account_comparisons.csv")
dump(out/"exposure_receipt.json",{str(f):sha(f) for f in [*files,out/"account_comparisons.csv"]})
