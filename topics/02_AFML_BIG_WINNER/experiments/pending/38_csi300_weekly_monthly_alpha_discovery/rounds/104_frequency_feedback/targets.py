from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R
from core import sha,dump
prev=here.parent/"98_d10_frequency/results"
source=prev/"targets.parquet"
t=pd.read_parquet(source,filters=[("model","in",["overlay","original"])])
keys=["phase","signal_date","instrument","entry_date","exit_date","entry_idx","exit_idx","year"]
target=t.pivot(index=keys,columns="model",values="weight").reset_index()
dates=target[["phase","signal_date","entry_date","exit_date"]].drop_duplicates()
files=[prev/(scope+"_windows.parquet") for scope in ["2018","2019","2020_flat","primary","later"]]
w=pd.concat([pd.read_parquet(f).query('cost=="base" and model in ["overlay","original"]') for f in files])
w=w.pivot(index=["phase","signal_date"],columns="model",values="net").reset_index()
dates=dates.merge(w,on=["phase","signal_date"],validate="1:1",how="left").sort_values(["phase","signal_date"])
assert dates[["original","overlay"]].notna().all().all()
decisions=[]
for phase,g in dates.groupby("phase"):
    g=g.sort_values("signal_date")
    assert (g.entry_date.iloc[1:].to_numpy()>=g.exit_date.iloc[:-1].to_numpy()).all()
    ready=hits=0
    for row in g.itertuples():
        hist=g[g.exit_date.le(row.signal_date)].tail(6)
        valid=len(hist)==6
        avg=(hist.overlay-hist.original).mean() if valid else np.nan
        gate=valid and avg>0
        decisions.append(dict(phase=phase,signal_date=row.signal_date,last_exit=hist.exit_date.max(),n=len(hist),gross_history_net_bp=avg*1e4,gate=int(gate),opposite=int(valid and not gate),slow=hits/ready if ready and valid else 0.,ready_prior=ready))
        ready+=valid;hits+=gate
d=pd.DataFrame(decisions)
h=target.merge(d,on=["phase","signal_date"],validate="m:1")
rows=[]
for model,scale in [("original",0.),("overlay",1.),("gate",h.gate),("opposite",h.opposite),("slow",h.slow)]:
    weight=h.original+scale*(h.overlay-h.original)
    assert weight.gt(0).all()
    np.testing.assert_allclose(weight.groupby(h.signal_date).sum(),1.,atol=1e-12)
    rows.append(h[keys].assign(model=model,weight=weight))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
d.to_csv(out/"decisions.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*files,prev/"receipt.json",here/"PROTOCOL.md",Path(__file__),out/"decisions.csv",out/"targets.parquet"]})
