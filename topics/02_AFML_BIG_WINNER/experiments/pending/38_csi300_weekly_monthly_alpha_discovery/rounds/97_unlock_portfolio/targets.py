from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
source=here.parent/"72_passive_weighting/results/targets.parquet"
base=pd.read_parquet(source,filters=[("model","=","drift_group")])
calfile=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(calfile,columns=[]).index
previous=here.parent/"96_april_unlock_rebound/results"
files=[previous/"january_windows.csv",previous/"windows.csv"]
events=pd.concat([pd.read_csv(f,parse_dates=["notice","unlock"]).assign(month=m) for m,f in zip(["january","april"],files)])
assert not events.duplicated(["issuer","unlock","month"]).any()
records=[]; accepted=[]
for row in events.itertuples():
    i=days.get_indexer([row.unlock])[0]
    signal=days[i-1] if i>0 else pd.NaT
    status="eligible"
    if pd.isna(signal):status="nontrading_listing"
    elif row.notice>signal:status="not_known_previous_close"
    elif pd.isna(row.peer):status="no_announced_peer"
    elif signal not in set(base.signal_date.unique()):status="no_scheduled_target"
    record=dict(month=row.month,document=row.document,issuer=row.issuer,peer=row.peer,notice=row.notice,unlock=row.unlock,signal=signal,status=status)
    records.append(record)
    if status=="eligible":accepted.append(record)
targets=[];audit=[]
by_day={d:g for d,g in pd.DataFrame(accepted).groupby("signal")}
for day,g in base.groupby("signal_date"):
    w=g.set_index("instrument").weight
    changes={name:pd.Series(0.,index=w.index) for name in ["january","april"]}
    if day in by_day:
        z=by_day[day].copy()
        z["budget"]=np.minimum(z.issuer.map(w),z.peer.map(w))/2
        z["budget"]*=np.minimum(1.,z.peer.map(w)/2/z.groupby("peer").budget.transform("sum"))
        for pair in z.itertuples():
            for rec in records:
                if rec["document"]==pair.document:
                    rec["status"]="allocated" if np.isfinite(pair.budget) else "no_common_base_weight"
                    rec["budget"]=pair.budget
            if np.isfinite(pair.budget):
                changes[pair.month][pair.peer]-=pair.budget
                changes[pair.month][pair.issuer]+=pair.budget
    changes["combined"]=changes["january"]+changes["april"]
    for name,delta in changes.items():
        wt=w+delta
        assert wt.gt(0).all() and abs(wt.sum()-1)<1e-12
        targets.append(g.assign(model=name,weight=g.instrument.map(wt)))
        audit.append(dict(day=day,model=name,active=delta.abs().sum()/2,phase=g.phase.iloc[0]))
pd.concat(targets).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(records).to_csv(out/"admissions.csv",index=False)
pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,calfile,*files,previous/"receipt.json",previous/"january_receipt.json",Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"admissions.csv",out/"coverage.csv"]})
