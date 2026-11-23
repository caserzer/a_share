from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"106_close_vwap/results/signals.parquet"
h=pd.read_parquet(source)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date","weight","model"]
base=h[keys].copy()
fields={n:PRIVATE/(n+".parquet") for n in ["qfq_close","money","daily_members","industry"]}
c=pd.read_parquet(fields["qfq_close"])
money=pd.read_parquet(fields["money"]).reindex_like(c)
members=pd.read_parquet(fields["daily_members"]).reindex_like(c)
adv=money.where(money>0).rolling(20,min_periods=20).mean().shift(5)
ret=np.log(c.where(c>0)).diff(5).where(money.gt(0).rolling(6).sum().eq(6))
ind=pd.read_parquet(fields["industry"])
ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
panels=[]
for day,g in h.groupby("signal_date"):
    stamp=day.strftime("%Y%m%d")
    mapping=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l2_name"]].dropna().drop_duplicates()
    mapping=mapping[~mapping.instrument.duplicated(False)].set_index("instrument").l2_name
    peer=pd.concat([mapping.rename("sub"),adv.loc[day].rename("adv"),ret.loc[day].rename("r")],axis=1).dropna()
    pool=members.loc[day].eq(1)
    peer=peer[peer.index.isin(pool.index[pool]) & ~peer.index.isin(g.instrument)].rename_axis("ticker").reset_index()
    peer=peer.sort_values(["sub","adv","ticker"])
    groups=peer.groupby("sub")
    first=groups.first();last=groups.last()
    distinct=last.adv>first.adv
    g=g.copy();sub=g.instrument.map(mapping)
    g["reversal"]=-g.instrument.map(ret.loc[day])
    for name,data in [("leader",last),("slow",first)]:
        g[name+"_peer"]=sub.map(data.ticker.where(distinct))
        g[name]=sub.map(data.r.where(distinct))+g.reversal
    panels.append(g)
h=pd.concat(panels,ignore_index=True)
signals=["leader","slow","reversal"]
e=h.dropna(subset=["sector",*signals]).sort_values(["signal_date","sector",R,"instrument"],ascending=[True,True,False,True]).copy()
group=["signal_date","sector"]
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
    if name=="leader":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*fields.values(),Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
