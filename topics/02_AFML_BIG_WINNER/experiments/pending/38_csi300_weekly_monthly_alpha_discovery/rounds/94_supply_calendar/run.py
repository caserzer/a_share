from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
prior=here.parent/"93_float_supply_step/results"
target=prior/"targets.parquet"
baseline=here.parent/"72_passive_weighting/results/targets.parquet"
p=pd.read_parquet(target,filters=[("model","=","contract")])
b=pd.read_parquet(baseline,filters=[("model","=","drift_group")])
keys=["signal_date","instrument"]
b=b.set_index(keys).weight
p["base"]=b.reindex(pd.MultiIndex.from_frame(p[keys])).to_numpy()
assert p.base.notna().all()
cp=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(cp,columns=[]).index
def quarter_end(dates):
    ix=days.get_indexer(dates)
    assert ix.min()>=1
    return days[ix-1].to_period("Q")!=days[ix].to_period("Q")
q=quarter_end(p.signal_date)
p["is_quarter"]=q
targets=pd.concat([p.assign(weight=p.weight.where(mask,p.base),model=name) for mask,name in [(q,"quarter"),(~q,"other")]])
targets.drop(columns=["base","is_quarter"]).to_parquet(out/"targets.parquet",index=False)
e_file=prior/"event_returns.csv"
e=pd.read_csv(e_file,parse_dates=["day"]).query('sleeve=="contract"').copy()
e["quarter"]=quarter_end(e.day)
e.to_csv(out/"events.csv",index=False)
summ=[]
for (scope,quarter),g in e.groupby(["scope","quarter"]):
    valid=g[g.complete].groupby("day").net.mean()*1e4
    summ.append(dict(scope=scope,quarter=quarter,matched=len(g),complete=g.complete.sum(),dates=len(valid),net_bp=valid.mean(),budget_sum=g.budget.sum()))
pd.DataFrame(summ).to_csv(out/"event_summary.csv",index=False)
assert np.allclose(targets.groupby("model").weight.sum(),p.base.sum())
dump(out/"target_receipt.json",{str(f):sha(f) for f in [baseline,target,cp,e_file,prior/"receipt.json",here/"PROTOCOL.md",Path(__file__),out/"targets.parquet",out/"events.csv",out/"event_summary.csv"]})
