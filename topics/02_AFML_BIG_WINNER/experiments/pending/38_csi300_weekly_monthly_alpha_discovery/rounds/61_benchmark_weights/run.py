from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE
from core import dump,sha
out=here/"results"
recent=here.parent/"57_recent_industry_labels/results";fs=recent/"scores.parquet"
prev=here.parent/"60_benchmark_bridge/results/windows.csv";price=PRIVATE/"qfq_open.parquet"
weights=sorted((PRIVATE/"weights").glob("????-??.json"));parts=[]
for f in weights:
    q=json.loads(f.read_text()).get("data")
    if q and q["items"]:parts.append(pd.DataFrame(q["items"],columns=q["fields"]))
w=pd.concat(parts).drop_duplicates();w["date"]=pd.to_datetime(w.trade_date)
w["instrument"]=w.con_code.str[-2:]+w.con_code.str[:6]
assert not w.duplicated(["date","instrument"]).any()
snap={d:h.set_index("instrument").weight/100 for d,h in w.groupby("date") if .99<=h.weight.sum()/100<=1.01}
dates=pd.DatetimeIndex(sorted(snap))
p=pd.read_parquet(price);s=pd.read_parquet(fs,columns=["signal_date","entry_date","exit_date","instrument"])
base=pd.read_csv(prev,parse_dates=["signal_date"]).query("model==@R and complete")
rows=[]
for dt,h in s.groupby("signal_date"):
    z=base[base.signal_date==dt]
    if z.empty:continue
    i=dates.searchsorted(dt)-1
    if i<0 or (dt-dates[i]).days>45:continue
    a=snap[dates[i]];r=(p.loc[h.exit_date.iloc[0]]/p.loc[h.entry_date.iloc[0]]-1).replace([np.inf,-np.inf],np.nan).dropna()
    all_names=a.index.intersection(r.index);pool=h.instrument[h.instrument.isin(r.index)]
    names=all_names.intersection(pool);assert len(names)>0
    full=np.average(r[all_names],weights=a[all_names]);weighted=np.average(r[names],weights=a[names])
    eq=r[pool].mean();common=r[names].mean()
    np.testing.assert_allclose(eq,z.pool,atol=1e-12)
    for v in z.itertuples():
        rows.append(dict(scope=v.scope,phase=v.phase,date=dt,snapshot=dates[i],age=(dt-dates[i]).days,matched_weight=a[names].sum(),priced_weight=a[all_names].sum(),unmatched=eq-common,sizing=common-weighted,eligibility=weighted-full,tracking=full-v.benchmark,total=eq-v.benchmark))
t=pd.DataFrame(rows);cols=["unmatched","sizing","eligibility","tracking"];np.testing.assert_allclose(t[cols].sum(axis=1),t.total,atol=1e-12)
t.to_csv(out/"windows.csv",index=False)
stats=[]
for scope,g in t.groupby("scope"):
    avg=g.groupby("phase")[cols+["total"]].mean().mean()*1e4
    stats.append(dict(scope=scope,usable=len(g),planned=(base.scope==scope).sum(),age_median=g.age.median(),age_max=g.age.max(),matched=g.matched_weight.mean(),priced=g.priced_weight.mean(),**avg.to_dict()))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [fs,prev,price,*weights,here/"PROTOCOL.md",Path(__file__),out/"summary.csv",out/"windows.csv"]})
