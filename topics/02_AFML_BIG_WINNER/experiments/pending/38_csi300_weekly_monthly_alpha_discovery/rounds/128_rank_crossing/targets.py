from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R,split
from core import sha,dump
src=here.parent/"98_d10_frequency/results/targets.parquet"
base=pd.read_parquet(src,filters=[("model","=","original")])
scorefiles=[here.parent/n/"results/scores.parquet" for n in ["71_2018_concentration","57_recent_industry_labels"]]
scores=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument",R]) for f in scorefiles])
mat=scores.pivot(index="signal_date",columns="instrument",values=R)
members_file=PRIVATE/"daily_members.parquet"
members=pd.read_parquet(members_file)
mat=mat.reindex(index=members.index,columns=members.columns).where(members.eq(1))
pct=mat.rank(axis=1,pct=True)
industry_file=PRIVATE/"industry.parquet"
ind=pd.read_parquet(industry_file)
ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
plans={int(e):g for e,g in base.groupby("entry_idx")}
rows=[]
for e,g in plans.items():
    prev=plans.get(e-10)
    if prev is None:continue
    t=g.iloc[0];old=prev.iloc[0]
    if (t.year<2021 or old.year<2021) and t.year!=old.year:continue
    if (t.entry_date>=split)!=(old.entry_date>=split):continue
    day=t.signal_date;stamp=day.strftime("%Y%m%d")
    mapping=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    mapping=mapping[~mapping.instrument.duplicated(False)].set_index("instrument").l1_name
    cur=set(g.instrument);last=set(prev.instrument)
    def candidates(names,ascending):
        ss=mat.loc[day].reindex(sorted(names)).dropna().rename("score").to_frame()
        ss["sector"]=ss.index.map(mapping)
        return ss.dropna().rename_axis("ticker").reset_index().sort_values(["score","ticker"],ascending=[ascending,True]).drop_duplicates("sector").set_index("sector")
    entrant=candidates(cur-last,True);leaver=candidates(last-cur,False)
    i=pct.index.get_loc(day)
    for sector in entrant.index.intersection(leaver.index):
        a,b=entrant.at[sector,"ticker"],leaver.at[sector,"ticker"]
        gap=(pct.iloc[i-4:i+1][a]-pct.iloc[i-4:i+1][b])
        if len(gap)!=5 or gap.isna().any() or gap.iloc[-1]<=0:continue
        rows.append(dict(signal_date=day,sector=sector,entrant=a,leaver=b,gap=gap.iloc[-1],median=gap.median(),weight=t.weight))
q=pd.DataFrame(rows);q.to_parquet(out/"pairs.parquet",index=False)
targets=[base]
for model,mask in [("unconfirmed",q["median"]<=0),("confirmed",q["median"]>0),("all_pairs",q["median"].notna())]:
    z=q[mask][["signal_date","entrant","leaver"]]
    t=base.merge(z,left_on=["signal_date","instrument"],right_on=["signal_date","entrant"],how="left",validate="1:1")
    t["instrument"]=t.leaver.fillna(t.instrument)
    assert not t.duplicated(["signal_date","instrument"]).any()
    targets.append(t[base.columns].assign(model=model))
pd.concat(targets).to_parquet(out/"targets.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,*scorefiles,members_file,industry_file,Path(__file__),here/"PROTOCOL.md",out/"pairs.parquet",out/"targets.parquet"]})
