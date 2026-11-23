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
for day,g in scores.groupby("signal_date"):
    i=dates.searchsorted(day)-1
    valid=i>=0 and (day-dates[i]).days<=45
    if valid:
        g=g.assign(index_weight=g.instrument.map(snap[dates[i]]))
        h=g[g.index_weight.gt(0)].sort_values(["index_weight","instrument"]).copy()
        h["group"]=np.arange(len(h))*5//len(h)
        groups=h.groupby("group");budget=groups.index_weight.sum()/h.index_weight.sum()
        picked=pd.concat([z[assign_deciles(z,R)==10] for _,z in groups])
        assert picked.group.nunique()==5
        n=picked.groupby("group").instrument.transform("size")
        w={"capital":picked.group.map(budget)/n,"groups":.2/n,"equal":np.repeat(1/len(picked),len(picked))}
    else:
        h=g.iloc[:0];picked=g[assign_deciles(g,R)==10];w={k:np.repeat(1/len(picked),len(picked)) for k in ["capital","groups","equal"]}
    for name,wt in w.items():
        assert abs(np.sum(wt)-1)<1e-10
        rows.append(picked[cols].assign(weight=wt,model=name,year=day.year))
    audit.append(dict(day=day,valid=valid,snapshot=dates[i] if valid else None,n=len(g),matched=len(h),picks=len(picked),max_weight=max(w["capital"])))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
dump(out/"fit_receipt.json",{str(f):sha(f) for f in [*files,fs,here/"PROTOCOL.md",Path(__file__),out/"coverage.csv",out/"targets.parquet"]})
