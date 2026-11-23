from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
prior=here.parent/"128_rank_crossing/results"
pairs=prior/"pairs.parquet";target=prior/"targets.parquet"
files=[here.parent/n/"results/scores.parquet" for n in ["71_2018_concentration","57_recent_industry_labels"]]
q=pd.read_parquet(pairs)
q=q[q["median"].le(0)]
ref=pd.read_parquet(target,filters=[("model","=","original")])[["signal_date","entry_idx","phase"]].drop_duplicates()
q=q.merge(ref,on="signal_date",validate="m:1")
member=PRIVATE/"daily_members.parquet";m=pd.read_parquet(member)
scores=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument",R]) for f in files]).pivot(index="signal_date",columns="instrument",values=R)
r=scores.reindex_like(m).where(m.eq(1)).rank(axis=1,pct=True)
i=q.entry_idx.to_numpy();j=r.columns.get_indexer(q.entrant);k=r.columns.get_indexer(q.leaver)
assert min(j.min(),k.min())>=0 and (r.index[i-1]==q.signal_date).all()
a=r.to_numpy()[i[:,None]+np.arange(5),j[:,None]]-r.to_numpy()[i[:,None]+np.arange(5),k[:,None]]
q["fresh_median"]=np.median(a,axis=1);q["fresh_last"]=a[:,-1]
q["switch"]=(q.fresh_median>0)&(q.fresh_last>0)
q["mid_idx"]=i+5
q.to_parquet(out/"signals.parquet",index=False)
dump(out/"signal_receipt.json",{str(f):sha(f) for f in [*files,pairs,target,member,here/"PROTOCOL.md",Path(__file__),out/"signals.parquet"]})
