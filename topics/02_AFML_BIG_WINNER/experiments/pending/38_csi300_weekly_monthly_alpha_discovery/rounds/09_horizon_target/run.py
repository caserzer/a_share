from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"08_same_close"))
from measure import R6,R,measure
from evaluate import EP,PRIVATE,accounts
from core import assign_deciles,sha,dump
OLD=EP/"extensions/original78_rankic_20261118"
sys.path.insert(0,str(OLD))
from model import ridge,predict
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market()
t=pd.read_parquet(R6/"results/targets.parquet")
d=pd.read_csv(R6/"results/dates.csv",parse_dates=["signal_date","mid_signal_date"])
d=d[(d.model==R+"_refresh")&d.age.eq(0)&d.new].copy()
assert len(d)==46
keys=["signal_date","instrument"]
cols=pd.read_csv(OLD/"outputs/original_78_features.csv").feature.to_list()
assert len(cols)==78
wf=PRIVATE/"features.parquet";lf=PRIVATE/"labels.parquet"
features=pd.read_parquet(wf,columns=keys+["score_eligible"]+cols).query("score_eligible").copy()
labels=pd.read_parquet(lf,columns=keys+["h5","h10","h5_mature","h10_mature","target_z"])
data=features.merge(labels,on=keys,validate="1:1")
sealed=[];fits=[];models={}
for q,g in d.groupby(d.mid_signal_date.dt.to_period("Q")):
    train=data[data.target_z.notna()&data.h5.notna()&data.h10.notna()&(data.h5_mature<q.start_time)&(data.h10_mature<q.start_time)].copy()
    assert train.signal_date.max()<q.start_time
    use=features[features.signal_date.isin(g.mid_signal_date)]
    result=use[keys].copy()
    for target in ["h5","h10"]:
        train["target_rank"]=train.groupby("signal_date")[target].transform(lambda s:s.rank()/(s.size+1)-.5)
        fit=ridge(train,cols,"target_rank")
        result[target+"_score"]=predict(use[cols],fit)
        models[str(q)+"_"+target]=fit
    fits.append(dict(quarter=str(q),rows=len(train),dates=train.signal_date.nunique(),cutoff=q.start_time,
        max_h5=train.h5_mature.max(),max_h10=train.h10_mature.max()))
    sealed.append(result)
p=pd.concat(sealed)
p.to_parquet(OUT/"scores.parquet",index=False)
pd.DataFrame(fits).to_csv(OUT/"folds.csv",index=False);dump(OUT/"models.json",models)
for target in ["h5","h10"]:
    dest=OUT/target;dest.mkdir(exist_ok=True)
    fresh=set(d.signal_date)
    parts=[t[(t.model==R+"_original")&~t.parent_date.isin(fresh)].copy()]
    for row in d.itertuples():
        g=t[(t.model==R+"_refresh")&t.parent_date.eq(row.signal_date)]
        first=g[g.signal_date==row.signal_date]
        mid=g[g.signal_date==row.mid_signal_date].iloc[0]
        h=p[p.signal_date.eq(row.mid_signal_date)].copy()
        j=m.symbols.get_indexer(h.instrument)
        assert min(j)>=0
        h=h[m.members[mid.entry_idx-1,j]]
        sel=h[assign_deciles(h,target+"_score")==10].copy()
        assert len(sel)==sum(g.signal_date==row.mid_signal_date)
        parts.extend([first,sel.assign(weight=1/len(sel),entry_idx=mid.entry_idx,entry_date=mid.entry_date,
                     exit_idx=mid.exit_idx,exit_date=mid.exit_date,parent_date=row.signal_date)])
    z=pd.concat(parts,ignore_index=True).assign(model=target)
    z.to_parquet(dest/"targets.parquet",index=False)
    dump(dest/"selection.json",{str(f):sha(f) for f in [wf,lf,OLD/"model.py",OLD/"outputs/original_78_features.csv",R6/"results/targets.parquet",HERE/"PROTOCOL.md",Path(__file__),OUT/"scores.parquet",dest/"targets.parquet"]})
    measure(z,t,m,dest)
