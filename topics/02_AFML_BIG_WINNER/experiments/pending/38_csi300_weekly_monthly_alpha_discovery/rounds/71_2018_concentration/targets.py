from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump,assign_deciles
out=here/"results"
fs=out/"scores.parquet"
cols=["signal_date","entry_date","exit_date","entry_idx","exit_idx","phase","instrument"]
baseline=out/"baseline.parquet"
prior=pd.read_parquet(baseline)
meta=prior[cols[:-1]].drop_duplicates()
scores=pd.read_parquet(fs).merge(meta,on=["signal_date","phase"],validate="many_to_one")
files=sorted((PRIVATE/"weights").glob("????-??.json"));parts=[]
for f in files:
    q=json.loads(f.read_text()).get("data")
    if q and q["items"]:parts.append(pd.DataFrame(q["items"],columns=q["fields"]))
v=pd.concat(parts).drop_duplicates();v["date"]=pd.to_datetime(v.trade_date);v["instrument"]=v.con_code.str[-2:]+v.con_code.str[:6]
assert not v.duplicated(["date","instrument"]).any()
snap={day:h.set_index("instrument").weight/100 for day,h in v.groupby("date") if .99<=h.weight.sum()/100<=1.01}
dates=pd.DatetimeIndex(sorted(snap));rows=[];audit=[]
for day,g in scores.groupby("signal_date"):
    i=dates.searchsorted(day)-1
    assert i>=0 and (day-dates[i]).days<=45
    h=g.assign(index_weight=g.instrument.map(snap[dates[i]])).dropna(subset=["index_weight"])
    h=h[h.index_weight.gt(0)].sort_values(["index_weight","instrument"]).copy()
    h["group"]=1+np.arange(len(h))*5//len(h)
    group_budget=h.groupby("group").index_weight.sum()/h.index_weight.sum()
    for group,z in h.groupby("group"):
        z=z.sort_values([R,"instrument"]);n=len(z);budget=group_budget[group]
        top=assign_deciles(z,R).eq(10)
        w=pd.DataFrame({"passive":np.full(n,budget/n),"active":budget*top.to_numpy()/top.sum()})
        rank=np.arange(1,n+1);linear=budget*2*rank/(n*(n+1))
        distance=np.abs(linear-w.passive.to_numpy()).sum()/2
        fraction=distance/(abs(w.active-w.passive).sum()/2)
        matched=w.passive.to_numpy()+fraction*(w.active-w.passive).to_numpy()
        assert 0<fraction<1
        np.testing.assert_allclose(np.abs(matched-w.passive.to_numpy()).sum()/2,distance,atol=1e-12)
        for model,wt in [("linear",linear),("matched",matched),("passive",w.passive.to_numpy())]:
            rows.append(z[cols].assign(weight=wt,model=model,year=day.year))
        audit.append(dict(day=day,group=group,distance=distance,fraction=fraction,budget=budget))
t=pd.concat([*rows,prior],ignore_index=True)
np.testing.assert_allclose(t.groupby(["signal_date","model"]).weight.sum(),1.,atol=1e-12)
t.to_parquet(out/"targets.parquet",index=False);pd.DataFrame(audit).to_csv(out/"budget.csv",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*files,fs,baseline,here/"PROTOCOL.md",Path(__file__),out/"targets.parquet",out/"budget.csv"]})
