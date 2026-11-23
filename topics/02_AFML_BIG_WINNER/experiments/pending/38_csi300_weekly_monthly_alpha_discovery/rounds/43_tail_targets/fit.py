from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,EP,PRIVATE
from core import sha,dump
old=EP/"extensions/original78_rankic_20261118"
sys.path[:0]=[str(old),str(PRIVATE.parent/"src")]
from model import ridge,predict
from features import compute
out=here/"results";out.mkdir(exist_ok=True)
previous=here.parent/"38_all_phases/results"
colsfile=old/"outputs/original_78_features.csv";cols=pd.read_csv(colsfile).feature.tolist()
wf=PRIVATE/"features.parquet";lab=PRIVATE/"labels.parquet"
weekly=pd.read_parquet(wf,columns=["signal_date","instrument","score_eligible",*cols])
labels=pd.read_parquet(lab,columns=["signal_date","instrument","h10","target_z","h10_mature"])
data=weekly.merge(labels,on=["signal_date","instrument"],validate="one_to_one")
data=data[data.score_eligible & data.target_z.notna()].copy()
targetfile=previous/"targets.parquet";scorefile=previous/"scores.parquet"
top=pd.read_parquet(targetfile).query("model==@R").merge(pd.read_parquet(scorefile)[["signal_date","instrument",R,E]],on=["signal_date","instrument"],validate="1:1")
fields=["qfq_close","qfq_open","qfq_high","qfq_low","volume","money","turnover_rate","daily_members"]
files=[PRIVATE/(k+".parquet") for k in fields];market=PRIVATE/"market.parquet"
raw=[pd.read_parquet(f) for f in files]
i=raw[0].index.get_indexer(top.signal_date);j=raw[0].columns.get_indexer(top.instrument)
assert min(i)>=0 and min(j)>=0
feat=compute(*raw,pd.read_parquet(market).close);del raw
for col in cols:top[col]=feat.pop(col).to_numpy()[i,j]
del feat
foldfile=old/"outputs/folds.csv";ref=pd.read_csv(foldfile).query("model==@R").set_index("fold")
audit=[];records={}
for quarter,z in top.groupby(top.signal_date.dt.to_period("Q")):
    h=data[(data.h10_mature<quarter.start_time)&(data.signal_date<quarter.start_time)].copy()
    rr=h.groupby("signal_date").h10.transform(lambda y:y.rank()/(y.count()+1))
    h["target_rank"]=rr-.5;h["avoid_left"]=-rr.le(.1).astype(float);h["seek_right"]=rr.ge(.9).astype(float)
    assert len(h)==ref.loc[str(quarter),"train_rows"] and h.h10_mature.max()<z.signal_date.min()
    pred=predict(z[cols],ridge(h,cols,"target_rank"));err=float(abs(pred-z[R]).max());assert err<1e-10
    for label in ["avoid_left","seek_right"]:
        fit=ridge(h,cols,label);records[str(quarter)+"_"+label]=fit
        top.loc[z.index,label]=predict(z[cols],fit)
    audit.append(dict(quarter=str(quarter),rows=len(h),latest_mature=h.h10_mature.max(),first_decision=z.signal_date.min(),max_frozen_error=err))
top[["signal_date","instrument","avoid_left","seek_right"]].to_parquet(out/"scores.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"folds.csv",index=False);dump(out/"models.json",records)
dump(out/"training_receipt.json",{str(f):sha(f) for f in [targetfile,scorefile,wf,lab,colsfile,foldfile,market,*files,old/"model.py",here/"PROTOCOL.md",Path(__file__),out/"scores.parquet",out/"models.json",out/"folds.csv"]})
