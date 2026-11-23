from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R
from core import dump,sha
root=here.parents[2]/"30_pit_data_foundation_v1/outputs"
files=[root/"backfill_v2/security_inventory.csv",root/"pit_v3/financial_cohort.csv"]
inventory=pd.concat([pd.read_csv(f,usecols=["security_id","instrument"]) for f in files]).drop_duplicates()
inventory=inventory[~inventory.security_id.duplicated(False)&~inventory.instrument.duplicated(False)]
raw=[];reviews=[]
for ver,file in [("pit_v3","financial_original_value_candidates.csv"),("pit_v4","financial_value_candidates.csv")]:
    f=root/ver/file;files.append(f);raw.append(pd.read_csv(f))
    f=root/ver/"financial_source_page_reviews.csv";files.append(f);reviews.append(pd.read_csv(f))
t=pd.concat(raw);v=pd.concat(reviews)
target=here.parent/"72_passive_weighting/results/targets.parquet";files.append(target)
portfolio=pd.read_parquet(target,columns=["instrument","signal_date","weight"],filters=[("model","=","passive")]);symbols=set(portfolio.instrument)
keys=["security_id","art_code","report_period","source_sha256"]
t=t[t.field.isin(["revenue","net_profit_parent"])].copy()
t["ready"]=pd.to_datetime(t.candidate_known_at,utc=True,errors="coerce").dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
t["ready"]=t[["ready"]].assign(notice=pd.to_datetime(t.notice_date).dt.normalize()).max(axis=1,skipna=False)
p=t.groupby(keys).agg(n_fields=("field","nunique"),ready=("ready","max"),tier=("quality_tier","first")).query("n_fields==2").reset_index()
conflict=t.groupby(keys+["field"]).candidate_value.nunique().groupby(level=[0,1,2,3]).max()
p=p[conflict.reindex(pd.MultiIndex.from_frame(p[keys])).to_numpy()==1]
p=p.merge(inventory,on="security_id",how="left",validate="many_to_one")
v["kind"]=v.field.str.extract("(net_profit_parent|revenue)",expand=False)
review=v.dropna(subset=["kind"]).groupby(["security_id","art_code","source_sha256"]).kind.nunique()
p["page_pair"]=review.reindex(pd.MultiIndex.from_frame(p[["security_id","art_code","source_sha256"]])).fillna(0).to_numpy()==2
p["ever_eligible"]=p.instrument.isin(symbols)
p.report_period=pd.to_datetime(p.report_period);p.to_csv(out/"paired_documents.csv",index=False)
# Optimistic upper bound: counts candidate pairs even when only annual, unreviewed or revised.
z=p[p.ever_eligible].dropna(subset=["ready"]).copy();rows=[]
for day,g in portfolio.groupby("signal_date"):
    records=z[(z.ready<day)&(z.report_period<day)&((day-z.report_period).dt.days<=365)]
    use=g.instrument.isin(records.instrument);reviewed=g.instrument.isin(records.loc[records.page_pair,"instrument"])
    rows.append(dict(day=day,eligible=len(g),candidate=int(use.sum()),candidate_weight=g.loc[use,"weight"].sum(),page_pair=int(reviewed.sum()),page_pair_weight=g.loc[reviewed,"weight"].sum()))
c=pd.DataFrame(rows);c.to_csv(out/"coverage.csv",index=False)
print(len(p),p.ever_eligible.sum(),p.page_pair.sum(),p[p.ever_eligible].page_pair.sum());print(c.groupby(c.day.dt.year)[["candidate","candidate_weight","page_pair_weight"]].mean().round(4))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"paired_documents.csv"]})
