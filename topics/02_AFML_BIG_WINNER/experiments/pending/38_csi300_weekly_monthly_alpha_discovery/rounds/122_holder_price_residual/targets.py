from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump

prior=here.parent/"121_holder_quarter_price/results"
pair_file=prior/"pairs.parquet"
target_file=prior/"targets.parquet"
import json
archive=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/r36_holder_counts"
manifest=archive/"source_manifest.json"
boundary=archive/"price_history_boundaries.json"
fields={k:PRIVATE/(k+".parquet") for k in ["qfq_close","volume","daily_members"]}
prices=pd.read_parquet(fields["qfq_close"])
vol=pd.read_parquet(fields["volume"]).reindex_like(prices)
members=pd.read_parquet(fields["daily_members"]).reindex_like(prices)
q=pd.read_parquet(pair_file)
base=pd.read_parquet(target_file,filters=[("model","=","original")])
d10=base.groupby("signal_date").instrument.agg(set)
bounds={r["code"]:pd.Timestamp(r["first_price_date"]) for r in json.loads(boundary.read_text())["receipts"]}
available={col[2:] for col in members.columns[members.eq(1).any()]}
records=[]
for receipt in json.loads(manifest.read_text())["results"]:
    code=receipt["code"]
    if code not in available or receipt["status"]!="complete":continue
    for page in receipt["pages"]:
        f=Path(page["path"]);assert sha(f)==page["sha256"]
        for row in json.loads(f.read_text())["result"]["data"]:
            assert row["SECURITY_CODE"]==code
            end=pd.Timestamp(row["END_DATE"]);notice=pd.Timestamp(row["HOLD_NOTICE_DATE"])
            if end.is_quarter_end and bounds[code]<=end<=notice and row["HOLDER_NUM"]>0:
                records.append(dict(code=code,period=end,notice=notice,count=row["HOLDER_NUM"]))
raw=pd.DataFrame(records)
assert not raw.duplicated(["code","period"]).any()
raw.to_parquet(out/"external_records.parquet",index=False)
raw["instrument"]=raw.code.map({s[2:]:s for s in prices.columns})
raw=raw.dropna(subset=["instrument"]).copy()
i=prices.index.searchsorted(raw.period,side="right")-1
j=prices.columns.get_indexer(raw.instrument)
ok=(i>=0)&(prices.index[i].to_period("Q")==raw.period.dt.to_period("Q"))&(vol.to_numpy()[i,j]>0)
raw["price"]=np.where(ok,prices.to_numpy()[i,j],np.nan)
raw=raw[raw.price.gt(0)].copy()
raw["ord"]=raw.period.dt.to_period("Q").astype(int)
prev=raw[["ord","instrument","count","price","notice"]].copy()
prev["ord"]+=1
hist=raw.merge(prev,on=["ord","instrument"],suffixes=("","_prior"),validate="1:1")
hist["contraction"]=-np.log(hist["count"]/hist.count_prior)
hist["price_return"]=np.log(hist.price/hist.price_prior)
hist["known"]=hist[["notice","notice_prior"]].max(axis=1)
periods={period:g.set_index("instrument") for period,g in hist.groupby("period")}
fits=[]
for day,period in q[["signal_date","period"]].drop_duplicates().itertuples(index=False):
    g=periods[period]
    pool=members.loc[day].eq(1)
    selected=g[g.known.lt(day)&g.index.isin(pool.index[pool])&~g.index.isin(d10[day])]
    if len(selected)<20:continue
    x=selected.price_return
    y=selected.contraction
    if x.var()<=0:continue
    slope=x.cov(y)/x.var()
    fits.append(dict(signal_date=day,period=period,n=len(x),slope=slope,intercept=y.mean()-slope*x.mean()))
fits=pd.DataFrame(fits)
fits.to_parquet(out/"fits.parquet",index=False)
q=q.merge(fits,on=["signal_date","period"],validate="m:1")
q["holder"]=q.recent_a-q.recent_b
q["explained"]=q.slope*(q.quarter_return_a-q.quarter_return_b)
q["residual"]=q.holder-q.explained
signals=["residual","holder","explained"]
q=q[q[signals].abs().gt(1e-12).all(axis=1)]
q.to_parquet(out/"pairs.parquet",index=False)
b=base.set_index(["signal_date","instrument"]).sort_index()
rows=[base]
for name in signals:
    amt=np.sign(q[name])*q.budget
    aa=q.assign(delta=amt).set_index(["signal_date","instrument_a"]).delta
    bb=q.assign(delta=-amt).set_index(["signal_date","instrument_b"]).delta
    delta=pd.concat([aa,bb]);delta.index.names=b.index.names
    delta=delta.reindex(b.index,fill_value=0)
    assert (b.weight+delta).gt(0).all() and delta.groupby(level=0).sum().abs().max()<1e-12
    rows.append(b.assign(model=name,weight=b.weight+delta).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [pair_file,target_file,manifest,boundary,out/"external_records.parquet",*fields.values(),Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["fits.parquet","pairs.parquet","targets.parquet"]]]})
