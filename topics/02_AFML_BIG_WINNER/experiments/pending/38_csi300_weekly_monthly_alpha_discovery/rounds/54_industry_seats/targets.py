from pathlib import Path
import sys
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE
from core import dump,sha
early="--early" in sys.argv
dest=here.parent/"55_earlier_seats" if early else here
out=dest/"results"
if early:
    src=here.parent/"51_earlier_replication/results"
    files=[src/"scores.parquet",src/"targets.parquet",PRIVATE/"industry.parquet"]
    base=pd.read_parquet(files[1])
    dates=base.drop(columns=["instrument","weight","model"]).drop_duplicates()
    scores=pd.read_parquet(files[0]).merge(dates,on=["phase","signal_date"],validate="many_to_one")
else:
    src=here.parent/"50_training_support/results"
    files=[here.parent/"38_all_phases/results/scores.parquet",src/"scores.parquet",src/"targets.parquet",PRIVATE/"industry.parquet"]
    scores=pd.read_parquet(files[0]).merge(pd.read_parquet(files[1]),on=["signal_date","instrument"],validate="one_to_one")
    base=pd.read_parquet(files[2])
base=base[base.model.isin([R,"embargo"])]
industry=pd.read_parquet(files[-1])
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
rows=[];coverage=[]
lookup=base.groupby(["signal_date","model"]).instrument.agg(set)
for day,g in scores.groupby("signal_date"):
    stamp=day.strftime("%Y%m%d")
    h=industry[industry.in_date.le(stamp)&(industry.out_date.isna()|industry.out_date.gt(stamp))]
    h=h[["instrument","l1_name"]].drop_duplicates()
    mapping=h[~h.instrument.duplicated(False)].set_index("instrument").l1_name
    g=g.assign(sector=g.instrument.map(mapping).fillna("未知"))
    coverage.append((day,len(g),g.sector.eq("未知").sum()))
    for order in [R,"embargo"]:
        rank=g.sort_values([order,"instrument"],ascending=False).copy()
        rank["position"]=rank.groupby("sector").cumcount()+1
        for seats in [R,"embargo"]:
            ref=lookup[day,seats]
            counts=g[g.instrument.isin(ref)].sector.value_counts()
            chosen=rank[rank.position.le(rank.sector.map(counts))]
            assert len(chosen)==len(ref)
            if order==seats:
                assert set(chosen.instrument)==ref
                continue
            model="stock_only" if seats==R else "seats_only"
            rows.append(chosen.assign(model=model,weight=1/len(ref))[base.columns])
pd.concat(rows,ignore_index=True).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(coverage,columns=["signal_date","scored","unknown"]).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(p):sha(p) for p in [*files,Path(__file__),dest/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv"]})
