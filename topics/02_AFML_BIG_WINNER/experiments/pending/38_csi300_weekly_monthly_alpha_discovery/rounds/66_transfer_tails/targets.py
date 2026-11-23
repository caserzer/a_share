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
reference=here.parent/"64_mature_group_switch/results/targets.parquet"
prior=pd.read_parquet(reference);prior=prior[prior.model.isin(["active","passive"])]
by_day=dict(tuple(prior.groupby("signal_date")))
for day,g in scores.groupby("signal_date"):
    i=dates.searchsorted(day)-1
    assert i>=0 and (day-dates[i]).days<=45
    h=g.assign(index_weight=g.instrument.map(snap[dates[i]])).dropna(subset=["index_weight"])
    h=h[h.index_weight.gt(0)].sort_values(["index_weight","instrument"]).copy()
    h["group"]=1+np.arange(len(h))*5//len(h)
    ref=by_day[day].pivot(index="instrument",columns="model",values="weight").fillna(0.)
    assert set(ref.index)==set(h.instrument)
    for group,z in h.groupby("group"):
        z=z.sort_values([R,"instrument"]);n=len(z);w=ref.loc[z.instrument]
        budget=w.passive.sum();np.testing.assert_allclose(w.active.sum(),budget,atol=1e-12)
        k=int(w.active.gt(0).sum());assert 0<2*k<n
        base=w.passive.to_numpy();distance=base[:k].sum()
        assert set(z.instrument.iloc[-k:])==set(w.index[w.active.gt(0)])
        pair=base.copy();pair[:k]=0.;pair[-k:]+=distance/k
        avoid=base.copy();avoid[:k]=0.;avoid[k:]+=distance/(n-k)
        prefer=base.copy();prefer[:-k]-=distance/(n-k);prefer[-k:]+=distance/k
        for model,wt in [("pair",pair),("prefer",prefer),("avoid",avoid)]:
            assert min(wt)>=0
            np.testing.assert_allclose(np.abs(wt-base).sum()/2,distance,atol=1e-12)
            board=z[cols].assign(weight=wt,model=model,year=day.year)
            rows.append(board[board.weight.gt(0)])
        audit.append(dict(day=day,group=group,distance=distance,k=k,budget=budget))
t=pd.concat(rows,ignore_index=True)
np.testing.assert_allclose(t.groupby(["signal_date","model"]).weight.sum(),1.,atol=1e-12)
t.to_parquet(out/"targets.parquet",index=False);pd.DataFrame(audit).to_csv(out/"budget.csv",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*files,fs,reference,here/"PROTOCOL.md",Path(__file__),out/"targets.parquet",out/"budget.csv"]})
