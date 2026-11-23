from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R,E
from core import sha,dump,assign_deciles
out=here/"results"
fs=here.parent/"57_recent_industry_labels/results/scores.parquet"
cols=["signal_date","entry_date","exit_date","entry_idx","exit_idx","phase","instrument"]
scores=pd.read_parquet(fs,columns=cols+[R])
score_sources=[here.parent/k/"results/scores.parquet" for k in ["51_earlier_replication","38_all_phases"]]
e1=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument",E]) for f in score_sources])
scores=scores.merge(e1,on=["signal_date","instrument"],validate="1:1",how="left")
assert scores[E].notna().all()
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
ef=here.parent/"69_limit_close/results/events.parquet";events=pd.read_parquet(ef,columns=["signal_date","instrument"])
touched=events.groupby("signal_date").instrument.agg(set).to_dict()
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
        alt=z.sort_values([E,"instrument"]).instrument
        common=set(z.instrument.iloc[:k])&set(alt.iloc[:k]);m=len(common)
        distance=budget*m/n
        spared=common & touched.get(day,set())
        order=z.assign(avg=(z[R].rank(pct=True)+z[E].rank(pct=True))/2).sort_values(["avg","instrument"])
        location={code:i for i,code in enumerate(order.instrument)}
        unused=common-spared;sham=set()
        for code in sorted(spared,key=location.get):
            if not unused:break
            alt_code=min(unused,key=lambda v:(abs(location[v]-location[code]),v));sham.add(alt_code);unused.remove(alt_code)
        if len(sham)<len(spared):
            sham.update(sorted(spared,key=location.get)[:len(spared)-len(sham)])
        assert len(sham)==len(spared)
        for model,excluded in [("retain",common-spared),("sham",common-sham),("all_low",common)]:
            wt=np.where(z.instrument.isin(excluded),0.,budget/(n-len(excluded)))
            board=z[cols].assign(weight=wt,model=model,year=day.year)
            rows.append(board[board.weight.gt(0)])
        audit.append(dict(day=day,group=group,k=k,m=m,spared=len(spared),shared=len(sham&spared),budget=budget))
t=pd.concat(rows,ignore_index=True)
np.testing.assert_allclose(t.groupby(["signal_date","model"]).weight.sum(),1.,atol=1e-12)
t.to_parquet(out/"targets.parquet",index=False);pd.DataFrame(audit).to_csv(out/"budget.csv",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*files,*score_sources,fs,reference,ef,here/"PROTOCOL.md",Path(__file__),out/"targets.parquet",out/"budget.csv"]})
