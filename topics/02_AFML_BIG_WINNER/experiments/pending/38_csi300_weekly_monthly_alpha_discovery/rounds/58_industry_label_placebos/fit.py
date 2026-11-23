from pathlib import Path
import sys
import hashlib
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,EP,PRIVATE
from core import assign_deciles,sha,dump
old=EP/"extensions/original78_rankic_20261118"
sys.path[:0]=[str(old),str(PRIVATE.parent/"src")]
from model import ridge,predict
from features import compute
out=here/"results"
cf=old/"outputs/original_78_features.csv";cols=pd.read_csv(cf).feature.tolist()
files=[PRIVATE/(key+".parquet") for key in ["qfq_close","qfq_open","qfq_high","qfq_low","volume","money","turnover_rate","daily_members"]]
raw=[pd.read_parquet(f) for f in files];days=raw[0].index;symbols=raw[0].columns
market=PRIVATE/"market.parquet";feat=compute(*raw,pd.read_parquet(market).close);del raw
wf=PRIVATE/"features.parquet";lf=PRIVATE/"labels.parquet";indfile=PRIVATE/"industry.parquet"
h=pd.read_parquet(wf,columns=["signal_date","instrument","score_eligible",*cols])
lab=pd.read_parquet(lf,columns=["signal_date","instrument","h10","target_z","h10_mature","h20_mature"])
h=h.merge(lab,on=["signal_date","instrument"],validate="1:1").query("score_eligible and target_z==target_z").copy()
h["original"]=h.groupby("signal_date").h10.transform(lambda y:y.rank()/(len(y)+1)-.5)
assert h.h10.notna().all()
ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
parts=[];files.extend([cf,wf,lf,indfile,market,old/"model.py",Path(__file__),here/"PROTOCOL.md"])
for folder in ["51_earlier_replication","38_all_phases"]:
    root=here.parent/folder/"results";fs=root/"scores.parquet";ft=root/"targets.parquet";files.extend([fs,ft])
    v=pd.read_parquet(fs,columns=["phase","signal_date","instrument",R])
    meta=pd.read_parquet(ft,columns=["phase","signal_date","entry_idx","exit_idx","entry_date","exit_date"]).drop_duplicates()
    parts.append(v.merge(meta,on=["phase","signal_date"],validate="many_to_one"))
top=pd.concat(parts,ignore_index=True)
i=days.get_indexer(top.signal_date);j=symbols.get_indexer(top.instrument);assert min(i)>=0 and min(j)>=0
for col in cols:top[col]=feat.pop(col).to_numpy()[i,j]
del feat
names=["shuffle1","shuffle2","shuffle3"];audit=[];records={}
for q,z in top.groupby(top.signal_date.dt.to_period("Q")):
    tr=h[h.h10_mature<q.start_time].copy()
    recent=~tr.h20_mature.lt(q.start_time)
    assert tr.signal_date.max()<q.start_time
    for name in names:tr[name]=tr.original
    missing=0
    for day,g in tr[recent].groupby("signal_date"):
        stamp=day.strftime("%Y%m%d")
        v=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
        v=v[~v.instrument.duplicated(False)].set_index("instrument").l1_name
        group=g.instrument.map(v);missing+=int(group.isna().sum())
        labels=group.dropna()
        for number,name in enumerate(names,1):
            seed=385800+number
            order=g.loc[labels.index,"instrument"].map(lambda code:hashlib.sha256(f"{seed}-{code}".encode()).digest()).sort_values()
            shuffled=pd.Series(sorted(labels),index=order.index)
            assert shuffled.value_counts().sort_index().equals(labels.value_counts().sort_index())
            group_mean=g.original.groupby(shuffled).transform("mean").fillna(0.)
            tr.loc[g.index,name]=g.original-group_mean
    baseline=predict(z[cols],ridge(tr,cols,"original"))
    err=np.max(abs(baseline-z[R]));assert err<1e-10
    for name in names:
        fit=ridge(tr,cols,name);records[str(q)+"_"+name]=fit
        top.loc[z.index,name]=predict(z[cols],fit)
    audit.append(dict(quarter=str(q),rows=len(tr),recent=recent.sum(),weeks=tr[recent].signal_date.nunique(),missing_sector=missing,baseline_error=err))
top=top.drop(columns=cols);top.to_parquet(out/"scores.parquet",index=False)
targets=[]
for day,g in top.groupby("signal_date"):
    for name in names:
        v=g[assign_deciles(g,name)==10].drop(columns=[R,*names])
        targets.append(v.assign(model=name,weight=1/len(v),year=day.year))
pd.concat(targets,ignore_index=True).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"folds.csv",index=False);dump(out/"models.json",records)
dump(out/"fit_receipt.json",{str(f):sha(f) for f in [*files,*[out/n for n in ["targets.parquet","scores.parquet","models.json","folds.csv"]]]})
