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
dates=pd.DatetimeIndex(sorted(snap));rows=[];attrib=[]
targetfile=here.parent/"62_weight_matched_selection/results/targets.parquet"
t=pd.read_parquet(targetfile);t=t[t.model=="capital"]
picked_by_day=dict(tuple(t.groupby("signal_date")))
price=PRIVATE/"qfq_open.parquet";op=pd.read_parquet(price)
from evaluate import split
for day,g in scores.groupby("signal_date"):
    i=dates.searchsorted(day)-1
    picked=picked_by_day[day].set_index("instrument")
    assert i>=0 and (day-dates[i]).days<=45
    g=g.assign(index_weight=g.instrument.map(snap[dates[i]]))
    h=g[g.index_weight.gt(0)].sort_values(["index_weight","instrument"]).copy()
    h["group"]=np.arange(len(h))*5//len(h)
    entry=h.entry_date.iloc[0];end=h.exit_date.iloc[0]
    y=(op.loc[end]/op.loc[entry]-1).replace([np.inf,-np.inf],np.nan)
    meta=dict(signal_date=day,phase=g.phase.iloc[0],scope=str(day.year) if day.year<2021 else ("later" if entry>=split else "primary"))
    complete=y.reindex(picked.index).notna().all()
    components=[]
    for group,z in h.groupby("group"):
        winners=z[assign_deciles(z,R)==10].instrument
        assert winners.isin(picked.index).all()
        capital=picked.loc[winners,"weight"].sum()
        equal=len(winners)/len(picked)
        peer=y.reindex(z.instrument)
        chosen=y.reindex(winners).mean(skipna=False)
        skill=chosen-peer.mean()
        rows.append(dict(**meta,group=group+1,complete=complete,capital=capital,equal=equal,skill=skill,chosen=chosen,pool=peer.mean(),quoted=peer.notna().sum(),n=len(peer)))
        components.append(((capital-equal)*peer.mean(),(capital-equal)*skill,(capital-equal)*chosen))
    if complete:
        x=np.sum(components,axis=0)
        actual=(picked.weight-1/len(picked)).dot(y.reindex(picked.index))
        np.testing.assert_allclose([x[0]+x[1],x[2]],actual,atol=1e-12)
        attrib.append(dict(**meta,pool=x[0],selection=x[1],total=actual))
r=pd.DataFrame(rows);r.to_csv(out/"group_windows.csv",index=False)
r=r[r.complete]
s=r.groupby(["scope","group","phase"])[["skill","capital"]].mean().groupby(level=[0,1]).mean()
s.skill*=1e4
s["dates"]=r.groupby(["scope","group"]).size();s.to_csv(out/"summary.csv")
a=pd.DataFrame(attrib);a.to_csv(out/"budget_windows.csv",index=False)
b=a.groupby(["scope","phase"])[["pool","selection","total"]].mean().groupby(level=0).mean()*1e4;b.to_csv(out/"budget_summary.csv")
print(s.round(2));print(b.round(2))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,fs,targetfile,price,here/"PROTOCOL.md",Path(__file__),*[out/n for n in ["group_windows.csv","summary.csv","budget_windows.csv","budget_summary.csv"]]]})
