from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,PRIVATE,accounts,R,E,evaluate
from core import sha,dump
OLD=EP/"extensions/original78_rankic_20261118"
sys.path.insert(0,str(OLD))
from model import ridge,predict
OUT=HERE/"results";OUT.mkdir(exist_ok=True)
cols=pd.read_csv(OLD/"outputs/original_78_features.csv").feature.to_list()
keys=["signal_date","instrument"]
wf=PRIVATE/"features.parquet";lf=PRIVATE/"labels.parquet";ip=PRIVATE/"industry.parquet"
weekly=pd.read_parquet(wf,columns=keys+["score_eligible"]+cols).query("score_eligible")
data=weekly.merge(pd.read_parquet(lf,columns=keys+["h10","target_z","h10_mature"]),on=keys,validate="1:1").dropna(subset=["h10","target_z"])
hf=OLD/"local_cache/h10_features.parquet"
ht=pd.read_parquet(hf).dropna(subset=["exit_date"])
industry=pd.read_parquet(ip);industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
def sectors(frame):
    mappings=[]
    for date,g in frame[keys].groupby("signal_date"):
        k=date.strftime("%Y%m%d")
        active=industry[industry.in_date.le(k)&(industry.out_date.isna()|industry.out_date.gt(k))]
        mapping=active[["instrument","l1_name"]].drop_duplicates()
        mappings.append(g.merge(mapping[~mapping.instrument.duplicated(False)],how="left",on="instrument",validate="1:1"))
    return frame.merge(pd.concat(mappings),on=keys,validate="1:1")
data=sectors(data);ht=sectors(ht)
counts=data.groupby(["signal_date","l1_name"]).h10.transform("size")
data=data[counts>=5].copy()
for target,groupkeys in [("peer",["signal_date","l1_name"]),("global",["signal_date"])]:
    grouped=data.groupby(groupkeys).h10
    data[target]=grouped.rank()/(grouped.transform("size")+1)-.5
scored=[];folds=[];models={}
for q,g in ht.groupby(ht.signal_date.dt.to_period("Q")):
    past=data[(data.h10_mature<q.start_time)&(data.signal_date<q.start_time)]
    z=g[keys+["l1_name","state","entry_idx","exit_idx","entry_date","exit_date"]].copy()
    for target in ["peer","global"]:
        fit=ridge(past,cols,target)
        models[str(q)+target]=fit
        z[target]=predict(g[cols],fit)
    scored.append(z);folds.append(dict(q=str(q),n=len(past),mature=past.h10_mature.max(),cutoff=q.start_time))
p=pd.concat(scored,ignore_index=True)
p.to_parquet(OUT/"scores.parquet",index=False)
pd.DataFrame(folds).to_csv(OUT/"folds.csv",index=False)
dump(OUT/"models.json",models)
base=pd.read_parquet(ROOT/"results/targets.parquet").query("model in [@R,@E]")
targets=[base]
for date,g in p.groupby("signal_date"):
    ref=base[(base.model==R)&(base.signal_date==date)]
    orig=g[g.instrument.isin(ref.instrument)]
    assert len(orig)==len(ref)
    for target in ["peer","global"]:
        pieces=[orig[orig.l1_name.isna()]]
        for name,k in orig.l1_name.value_counts().items():
            pieces.append(g[g.l1_name==name].sort_values([target,"instrument"]).tail(k))
        h=pd.concat(pieces)
        assert h.l1_name.value_counts().to_dict()==orig.l1_name.value_counts().to_dict()
        targets.append(h.assign(model=target,weight=1/len(h)))
pd.concat(targets,ignore_index=True).to_parquet(OUT/"targets.parquet",index=False)
dump(OUT/"selection.json",{str(f):sha(f) for f in [wf,lf,ip,hf,OLD/"model.py",HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet"]})
evaluate(OUT,26)
