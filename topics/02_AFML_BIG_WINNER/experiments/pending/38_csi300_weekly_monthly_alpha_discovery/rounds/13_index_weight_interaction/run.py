from pathlib import Path
import sys,json
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True)
src=HERE.parent/"12_index_event_budget/results/events.csv"
z=pd.read_csv(src,parse_dates=["weight_date","exit_date","signal_date"]).query("status=='closed'").copy()
w=[]
for f in sorted((PRIVATE/"weights").glob("????-??.json")):
    q=json.loads(f.read_text()).get("data")
    if q and q["items"]:w.append(pd.DataFrame(q["items"],columns=q["fields"]))
w=pd.concat(w).drop_duplicates();w["weight_date"]=pd.to_datetime(w.trade_date)
assert not w.duplicated(["weight_date","con_code"]).any()
med=(w.groupby("weight_date").weight.median()/100)
z["median_weight"]=z.weight_date.map(med)
assert z.median_weight.notna().all() and (z.weight_date<z.signal_date).all()
z["group"]=(2*z.requested<=z.median_weight).map({True:"low",False:"high"})
z["month"]=z.exit_date.dt.to_period("M")
s=[]
for (scope,group),g in z.groupby(["scope","group"]):
    mo=g.groupby("month").base.sum()
    s.append(dict(scope=scope,group=group,n=len(g),budget=g.budget.sum(),paired=g.base.sum(),per_deployed=g.base.sum()/g.budget.sum(),
                  double=g.double.sum()/g.budget.sum(),ex3=mo.drop(mo.nlargest(3).index).sum()))
s=pd.DataFrame(s);s.to_csv(OUT/"summary.csv",index=False);z.to_csv(OUT/"attribution.csv",index=False);print(s.round(6).to_string(index=False))
dump(OUT/"receipt.json",{str(f):sha(f) for f in [src,Path(__file__),HERE/"PROTOCOL.md",OUT/"attribution.csv"]})
