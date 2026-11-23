from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R
from core import dump,sha
out=here/"results";f=here.parent/"63_size_bucket_skill/results/group_windows.csv";s=here.parent/"57_recent_industry_labels/results/scores.parquet"
d=pd.read_csv(f,parse_dates=["signal_date"]);schedule=pd.read_parquet(s,columns=["signal_date","exit_date"]).drop_duplicates()
d=d.merge(schedule,on="signal_date",validate="many_to_one").sort_values("signal_date")
records=[]
for (phase,group),g in d.groupby(["phase","group"]):
    history=g[g.skill.notna()].sort_values("exit_date")
    for v in g.itertuples():
        n=history.exit_date.searchsorted(v.signal_date,side="right")
        sample=history.iloc[max(0,n-6):n]
        if len(sample):
            assert (sample.exit_date<=v.signal_date).all() and (sample.signal_date<v.signal_date).all()
        avg=sample.skill.mean() if len(sample)==6 else np.nan
        records.append(dict(phase=phase,group=group,signal_date=v.signal_date,n=len(sample),last=sample.exit_date.max(),avg=avg,active=bool(avg>0)))
decision=pd.DataFrame(records)
d=d.merge(decision,on=["phase","signal_date","group"],validate="one_to_one").sort_values(["signal_date","group"])
d.to_parquet(out/"signals.parquet",index=False)
w=d[d.complete].copy()
w["always"]=w.capital*w.skill
w["switch"]=w.always*w.active
for i in range(1,5):
    rotated=w.groupby("signal_date").active.transform(lambda x:np.roll(x,i))
    w["rot"+str(i)]=w.always*rotated
w["misassigned"]=w[["rot"+str(i) for i in range(1,5)]].mean(axis=1)
keys=["scope","phase","signal_date"];v=w.groupby(keys)[["always","switch","misassigned"]].sum()
v["vs_active"]=v.switch-v.always;v["vs_misassigned"]=v.switch-v.misassigned
v.to_csv(out/"gross_windows.csv")
stat=v.groupby(level=[0,1]).mean().groupby(level=0).mean()*1e4
stat["fraction_active"]=w.groupby(["scope","phase"]).active.mean().groupby(level=0).mean()
stat.to_csv(out/"gross_summary.csv");print(stat.round(3))
dump(out/"signal_receipt.json",{str(p):sha(p) for p in [f,s,here/"PROTOCOL.md",Path(__file__),out/"signals.parquet",out/"gross_windows.csv",out/"gross_summary.csv"]})
