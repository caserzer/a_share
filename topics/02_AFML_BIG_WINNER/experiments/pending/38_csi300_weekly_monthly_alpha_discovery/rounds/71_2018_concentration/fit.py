from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import E,R,EP,PRIVATE
from core import assign_deciles,dump,sha
old=EP/"extensions/original78_rankic_20261118"
sys.path[:0]=[str(old),str(PRIVATE.parent/"src")]
from model import ridge,predict
from features import compute
out=here/"results";out.mkdir(exist_ok=True)
cf=old/"outputs/original_78_features.csv";cols=pd.read_csv(cf).feature.tolist()
features_file=PRIVATE/"features.parquet";labels_file=PRIVATE/"labels.parquet"
weekly=pd.read_parquet(features_file,columns=["signal_date","instrument","score_eligible",*cols])
lab=pd.read_parquet(labels_file,columns=["signal_date","instrument","h10","h20","target_z","h10_mature","h20_mature"])
train=weekly.merge(lab,on=["signal_date","instrument"],validate="1:1").query("score_eligible and target_z==target_z").copy()
files=[PRIVATE/(key+".parquet") for key in ["qfq_close","qfq_open","qfq_high","qfq_low","volume","money","turnover_rate","daily_members"]]
raw=[pd.read_parquet(f) for f in files];c=raw[0];days=c.index
eligible=raw[-1]&(c.gt(0)&np.isfinite(c)).rolling(61).sum().eq(61)&(c.shift(5)/c.shift(60)).ne(1)&(c/c.shift(5)).ne(1)
mf=PRIVATE/"market.parquet";market=pd.read_parquet(mf).close
feats=compute(*raw,market);del raw
anchor=days.get_loc("2021-01-08")
specs=[(E,"full","target_z"),(R,"full","rank10"),]
audit=[];saved={};holdings=[];score_rows=[]
for q in pd.period_range("2018Q1","2019Q1",freq="Q"):
    cut=q.start_time
    full=train[train.h10_mature.lt(cut)].copy()
    groups=dict(full=full)
    fits={}
    for name,group,target in specs:
        h=groups[group]
        h["rank10"]=h.groupby("signal_date").h10.transform(lambda y:y.rank()/(y.count()+1)-.5)
        fit=ridge(h,cols,target);fits[name]=fit;saved[str(q)+"_"+name]=fit
        assert h.h10_mature.max()<cut
        audit.append(dict(quarter=str(q),model=name,rows=len(h),max_h10=h.h10_mature.max(),plan_h20=h.h20_mature.max()))
    for i in np.flatnonzero(days.to_period("Q")==q):
        day=days[i];e=i+1;x=e+10
        if days[x].year!=day.year:continue
        names=eligible.columns[eligible.iloc[i]]
        f=pd.DataFrame({k:feats[k].iloc[i].reindex(names) for k in cols});f=f[f.notna().mean(axis=1)>=.8]
        board=pd.DataFrame({"instrument":f.index});phase=(i-anchor)%10
        assert len(f)>=100
        for name,_,_ in specs:
            board[name]=predict(f, fits[name])
            picks=board[assign_deciles(board,name)==10]
            holdings.append(picks[["instrument"]].assign(model=name,weight=1/len(picks),signal_date=day,entry_idx=e,exit_idx=x,entry_date=days[e],exit_date=days[x],phase=phase,year=day.year))
        score_rows.append(board.assign(signal_date=day,phase=phase))
scores=pd.concat(score_rows,ignore_index=True)
ref=here.parent/"51_earlier_replication/results/scores.parquet";files.append(ref)
keys=["signal_date","instrument"]
prior=pd.read_parquet(ref).query('signal_date>="2019-01-01" and signal_date<"2019-04-01"').set_index(keys)
test=scores[scores.signal_date.dt.year==2019].set_index(keys)
pd.testing.assert_frame_equal(prior[[R,E]].sort_index(),test[[R,E]].sort_index(),rtol=0,atol=1e-12)
t=pd.concat(holdings,ignore_index=True);t[t.year==2018].to_parquet(out/"baseline.parquet",index=False)
scores[scores.signal_date.dt.year==2018].to_parquet(out/"scores.parquet",index=False)
dump(out/"models.json",saved);pd.DataFrame(audit).to_csv(out/"folds.csv",index=False)
dump(out/"fit_receipt.json",{str(f):sha(f) for f in [*files,mf,cf,features_file,labels_file,old/"model.py",here/"PROTOCOL.md",Path(__file__),out/"scores.parquet",out/"baseline.parquet",out/"models.json",out/"folds.csv"]})
