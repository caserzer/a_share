from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"118_shareholder_counts/results/signals.parquet"
h=pd.read_parquet(source)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date"]
original=h[keys+["weight"]].assign(model="original").set_index(["signal_date","instrument"]).sort_index()
prev=h[["phase","exit_idx","instrument"]].rename(columns={"exit_idx":"entry_idx"}).assign(retained=True)
clock=prev[["phase","entry_idx"]].drop_duplicates()
eligible=h.dropna(subset=["recent","previous","sector","period"]).merge(clock,on=["phase","entry_idx"],validate="m:1").merge(prev,on=["phase","entry_idx","instrument"],how="left",validate="1:1")
eligible["retained"]=eligible.retained.eq(True)
gcols=["signal_date","sector","period","retained"]
price_file=PRIVATE/"qfq_close.parquet"
volume_file=PRIVATE/"volume.parquet"
prices=pd.read_parquet(price_file)
vol=pd.read_parquet(volume_file).reindex_like(prices)
eligible=eligible[~eligible.retained].copy()
def quarter_close(ends):
    i=prices.index.searchsorted(ends,side="right")-1
    j=prices.columns.get_indexer(eligible.instrument)
    assert j.min()>=0
    px=prices.to_numpy()[i,j]
    valid=(i>=0)&(vol.to_numpy()[i,j]>0)&(px>0)&(prices.index[i].to_period("Q")==ends.dt.to_period("Q"))
    return np.where(valid,px,np.nan)
eligible["quarter_return"]=np.log(quarter_close(eligible.period)/quarter_close(eligible.period1))
e=eligible.dropna(subset=["quarter_return"]).sort_values(gcols+["quarter_return","instrument"])
e[["signal_date","instrument","quarter_return"]].to_parquet(out/"prices.parquet",index=False)
n=e.groupby(gcols).cumcount();e=e.assign(pair=n//2)
q=e[n.mod(2).eq(0)].merge(e[n.mod(2).eq(1)],on=gcols+["pair"],suffixes=("_a","_b"),validate="1:1")
q=q[((q.recent_a-q.recent_b).abs()>1e-12)&((q.quarter_return_a-q.quarter_return_b).abs()>1e-12)].copy()
# A larger negative log change indicates a stronger contraction.
q["up_a"]=q.recent_a>q.recent_b
q["budget"]=q.weight_a/2
rows=[original.reset_index()];audit=[]
for name,direction in [("holder",q.up_a),("momentum",q.quarter_return_a>q.quarter_return_b),("reversal",q.quarter_return_a<q.quarter_return_b)]:
    z=q
    a=z.assign(delta=z.budget*np.where(direction,1,-1)).set_index(["signal_date","instrument_a"]).delta
    b=z.assign(delta=-a.to_numpy()).set_index(["signal_date","instrument_b"]).delta
    delta=pd.concat([a,b]);delta.index.names=original.index.names;delta=delta.reindex(original.index,fill_value=0.)
    w=original.weight+delta
    assert w.gt(0).all() and delta.groupby(level=0).sum().abs().max()<1e-12
    rows.append(original.assign(weight=w,model=name).reset_index())
    audit.append((delta.abs().groupby(level=0).sum()/2).rename(name))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
q.to_parquet(out/"pairs.parquet",index=False);pd.concat(audit,axis=1).to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,price_file,volume_file,here/"PROTOCOL.md",Path(__file__),out/"coverage.csv",out/"prices.parquet",out/"pairs.parquet",out/"targets.parquet"]})
