from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
out=here/"results"
sources=[here.parent/k/"results/targets.parquet" for k in ["71_2018_concentration","64_mature_group_switch"]]
t=pd.concat([pd.read_parquet(p).query('model=="passive"') for p in sources])
weights=sorted((PRIVATE/"weights").glob("????-??.json"));parts=[]
for f in weights:
    q=json.loads(f.read_text()).get("data")
    if q and q["items"]:parts.append(pd.DataFrame(q["items"],columns=q["fields"]))
w=pd.concat(parts).drop_duplicates();w["date"]=pd.to_datetime(w.trade_date);w["instrument"]=w.con_code.str[-2:]+w.con_code.str[:6]
assert not w.duplicated(["date","instrument"]).any()
snap={day:h.set_index("instrument").weight for day,h in w.groupby("date") if 99<=h.weight.sum()<=101}
days=pd.DatetimeIndex(sorted(snap));price=PRIVATE/"qfq_close.parquet";close=pd.read_parquet(price)
rows=[t];audit=[]
for day,h in t.groupby("signal_date"):
    i=days.searchsorted(day)-1;sd=days[i];assert i>=0 and (day-sd).days<=45
    h=h.set_index("instrument").copy()
    h["raw"]=snap[sd].reindex(h.index)
    h=h.reset_index().sort_values(["raw","instrument"]).set_index("instrument");assert h.raw.gt(0).all()
    h["bucket"]=np.arange(len(h))*5//len(h);raw=h.raw/h.raw.sum()
    factor=close.loc[day,h.index]/close.loc[sd,h.index] if sd in close.index else pd.Series(np.nan,index=h.index)
    valid=np.isfinite(factor)&factor.gt(0)
    drift=raw*factor.where(valid,1.)
    group_budget=raw.groupby(h.bucket).transform("sum")
    np.testing.assert_allclose(h.weight,group_budget/h.groupby("bucket").weight.transform("size"),atol=1e-12)
    for name,wt in [("snapshot",raw),("drift_group",drift/drift.groupby(h.bucket).transform("sum")*group_budget),("drift_full",drift/drift.sum())]:
        assert abs(wt.sum()-1)<1e-12
        audit.append(dict(day=day,snapshot=sd,model=name,fallback_weight=raw[~valid].sum(),active=(wt-h.weight).abs().sum()/2))
        rows.append(h.drop(columns=["bucket","raw"]).assign(weight=wt,model=name).reset_index())
pd.concat(rows,ignore_index=True).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"exposure.csv",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*sources,*weights,price,here/"PROTOCOL.md",Path(__file__),out/"targets.parquet",out/"exposure.csv"]})
