from pathlib import Path
import sys
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import dump,sha
base=here.parent/"72_passive_weighting/results/targets.parquet";board=pd.read_parquet(base,columns=["instrument","signal_date"],filters=[("model","=","passive")]);calendar=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(calendar,columns=[]).index
src=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_financials"
fields=["SECUCODE","REPORT_DATE","NOTICE_DATE","UPDATE_DATE","CURRENCY","TOTALOPERATEREVE","PARENTNETPROFIT"]
records=[];files=[];missing=[]
for code,g in board.groupby("instrument"):
    f=src/(code[2:]+"."+code[:2]+".parquet")
    if not f.exists() or not set(fields)<=set(pq.read_schema(f).names):
        missing.append(code);continue
    files.append(f);h=pd.read_parquet(f,columns=fields)
    assert h.SECUCODE.dropna().eq(f.stem).all()
    for col in fields[1:4]:h[col]=pd.to_datetime(h[col],errors="coerce").dt.normalize()
    for col in fields[-2:]:h[col]=pd.to_numeric(h[col],errors="coerce")
    h=h.dropna(subset=fields[1:4]).copy()
    h["known"]=h[["NOTICE_DATE","UPDATE_DATE"]].max(axis=1)
    h=h[(h.known>=h.REPORT_DATE)&h.REPORT_DATE.dt.is_quarter_end]
    h=h.drop_duplicates(["REPORT_DATE","known","CURRENCY",*fields[-2:]])
    # Competing copies at the same known date invalidate that version.
    conflict=h.duplicated(["REPORT_DATE","known"],keep=False)
    h.loc[conflict,fields[-2:]]=np.nan
    h=h.drop_duplicates(["REPORT_DATE","known"]).sort_values(["known","REPORT_DATE"])
    latest={};events=[]
    for known,arr in h.groupby("known"):
        for v in arr.itertuples():latest[v.REPORT_DATE]=v
        q=max(latest);srcq=[q] if q.month==12 else [q,pd.Timestamp(q.year-1,12,31),q-pd.DateOffset(years=1)]
        vals=[latest[x] for x in srcq if x in latest];margin=np.nan
        if len(vals)==len(srcq) and all(v.CURRENCY==vals[0].CURRENCY for v in vals) and pd.notna(vals[0].CURRENCY):
            weights=np.array([1] if len(vals)==1 else [1,1,-1])
            rev=weights@np.array([v.TOTALOPERATEREVE for v in vals]);profit=weights@np.array([v.PARENTNETPROFIT for v in vals])
            if rev>0 and np.isfinite(profit) and np.isfinite(rev):margin=profit/rev
        events.append(dict(known=known,period=q,reported=margin))
    if not events:continue
    g=g.sort_values("signal_date").copy();g["asof"]=days[days.get_indexer(g.signal_date)-1]
    joined=pd.merge_asof(g,pd.DataFrame(events),left_on="asof",right_on="known")
    joined["age"]=(joined.signal_date-joined.period).dt.days
    joined.loc[joined.age.gt(365),"reported"]=np.nan
    assert (joined.known.dropna()<=joined.loc[joined.known.notna(),"asof"]).all()
    records.append(joined)
data=pd.concat(records,ignore_index=True);data.to_parquet(out/"reported.parquet",index=False)
dump(out/"report_receipt.json",{"missing_files_or_fields":missing,"hashes":{str(f):sha(f) for f in [base,calendar,*files,Path(__file__),here/"PROTOCOL.md",out/"reported.parquet"]}})
print(data.reported.notna().sum(),len(board))
