from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump,assign_deciles
out=here/"results"
fs=here.parent/"57_recent_industry_labels/results/scores.parquet"
cols=["signal_date","entry_date","exit_date","entry_idx","exit_idx","phase","instrument"]
scores=pd.read_parquet(fs,columns=cols+[R])
files=sorted((PRIVATE/"weights").glob("????-??.json"));parts=[]
for f in files:
    q=json.loads(f.read_text()).get("data")
    if q and q["items"]:parts.append(pd.DataFrame(q["items"],columns=q["fields"]))
v=pd.concat(parts).drop_duplicates();v["date"]=pd.to_datetime(v.trade_date);v["instrument"]=v.con_code.str[-2:]+v.con_code.str[:6]
assert not v.duplicated(["date","instrument"]).any()
snap={day:h.set_index("instrument").weight/100 for day,h in v.groupby("date") if .99<=h.weight.sum()/100<=1.01}
dates=pd.DatetimeIndex(sorted(snap));rows=[];audit=[]
f=out/"signals.parquet";decision=pd.read_parquet(f).set_index(["signal_date","group"]).active
for day,g in scores.groupby("signal_date"):
    i=dates.searchsorted(day)-1
    assert i>=0 and (day-dates[i]).days<=45
    h=g.assign(index_weight=g.instrument.map(snap[dates[i]])).dropna(subset=["index_weight"])
    h=h[h.index_weight.gt(0)].sort_values(["index_weight","instrument"]).copy()
    h["group"]=1+np.arange(len(h))*5//len(h)
    budget=h.groupby("group").index_weight.sum()/h.index_weight.sum()
    for group,z in h.groupby("group"):
        chosen=z[assign_deciles(z,R)==10]
        for name,board in [("active",chosen),("passive",z),("switch",chosen if decision[day,group] else z)]:
            rows.append(board[cols].assign(weight=budget[group]/len(board),model=name,year=day.year))
t=pd.concat(rows,ignore_index=True)
np.testing.assert_allclose(t.groupby(["signal_date","model"]).weight.sum(),1.,atol=1e-12)
ref=here.parent/"62_weight_matched_selection/results/targets.parquet"
orig=pd.read_parquet(ref).query('model=="capital"').set_index(["signal_date","instrument"]).weight.sort_index()
pd.testing.assert_series_equal(orig,t.query('model=="active"').set_index(["signal_date","instrument"]).weight.sort_index())
t.to_parquet(out/"targets.parquet",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*files,fs,ref,f,Path(__file__),out/"targets.parquet"]})
