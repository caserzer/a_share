from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
import json
source=here.parent/"106_close_vwap/results/signals.parquet"
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date","weight","model"]
h=pd.read_parquet(source,columns=keys+["sector",R])
base=h[keys].copy()
ep24=next(here.parents[2].glob("24_conditional_return_distribution_exploration"))
archive=ep24/"outputs/r36_holder_counts"
manifest=archive/"source_manifest.json"
boundary=archive/"price_history_boundaries.json"
bounds={r["code"]:pd.Timestamp(r["first_price_date"]) for r in json.loads(boundary.read_text())["receipts"]}
universe=set(h.instrument.str[2:])
rows=[]
for receipt in json.loads(manifest.read_text())["results"]:
    code=receipt["code"]
    if code not in universe or receipt["status"]!="complete":continue
    for page in receipt["pages"]:
        f=Path(page["path"]);assert sha(f)==page["sha256"]
        for r in json.loads(f.read_text())["result"]["data"]:
            assert r["SECURITY_CODE"]==code
            end=pd.Timestamp(r["END_DATE"]);notice=pd.Timestamp(r["HOLD_NOTICE_DATE"])
            if end.is_quarter_end and end>=bounds[code] and end<=notice and r["HOLDER_NUM"]>0:
                rows.append(dict(code=code,period=end,notice=notice,count=r["HOLDER_NUM"]))
raw=pd.DataFrame(rows)
assert not raw.duplicated(["code","period"]).any()
raw.to_parquet(out/"quarter_records.parquet",index=False)
raw["ord"]=raw.period.dt.to_period("Q").astype(int)
history=raw.copy()
for lag in [1,2]:
    shifted=raw.assign(ord=raw.ord+lag).rename(columns={"notice":f"notice{lag}","count":f"count{lag}","period":f"period{lag}"})
    history=history.merge(shifted,on=["code","ord"],how="left",validate="1:1")
history["known"]=history[["notice","notice1","notice2"]].max(axis=1)
history["recent"]=-np.log(history["count"]/history.count1)
history["previous"]=-np.log(history.count1/history.count2)
history["acceleration"]=history.recent-history.previous
signals=["recent","previous","acceleration"]
# Select latest disclosed quarter first; incomplete prior quarters keep that observation missing.
groups={k:g for k,g in history.groupby("code")}
frames=[]
for ticker,g in h.groupby("instrument"):
    records=groups.get(ticker[2:])
    if records is None:
        frames.append(g);continue
    records=records.sort_values(["notice","period"])
    records=records[records.ord.eq(records.ord.cummax())]
    g=pd.merge_asof(g.sort_values("signal_date"),records,on=None,left_on="signal_date",right_on="notice",allow_exact_matches=False)
    ok=(g.known<g.signal_date)&((g.signal_date-g.period).dt.days<=180)
    g.loc[~ok,signals]=np.nan
    frames.append(g)
h=pd.concat(frames,ignore_index=True)
group=["signal_date","sector","period"]
e=h.dropna(subset=["sector",*signals]).sort_values(group+[R,"instrument"]).copy()
e["n"]=e.groupby(group).cumcount()
e["pair"]=e.n//2
pairs=e[e.n.mod(2)==0].merge(e[e.n.mod(2)==1],on=group+["pair"],suffixes=("_a","_b"),validate="1:1")

for name in signals:pairs[name+"_diff"]=pairs[name+"_a"]-pairs[name+"_b"]
pairs=pairs[(pairs[[n+"_diff" for n in signals]].abs()>1e-12).all(axis=1)].copy()
pairs.to_parquet(out/"pairs.parquet",index=False)
h.to_parquet(out/"signals.parquet",index=False)
b=base.set_index(["signal_date","instrument"]).sort_index()
rows=[b.reset_index()]
for name in signals:
    amount=np.sign(pairs[name+"_diff"])*pairs.weight_a/2
    a=pairs.assign(delta=amount).set_index(["signal_date","instrument_a"]).delta
    z=pairs.assign(delta=-amount).set_index(["signal_date","instrument_b"]).delta
    delta=pd.concat([a,z]);delta.index.names=b.index.names;delta=delta.reindex(b.index,fill_value=0)
    wt=b.weight+delta;assert wt.gt(0).all()
    np.testing.assert_allclose(wt.groupby(level=0).sum(),1.,atol=1e-12)
    active=delta.abs().groupby(level=0).sum()/2
    if name=="recent":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,manifest,boundary,out/"quarter_records.parquet",Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
