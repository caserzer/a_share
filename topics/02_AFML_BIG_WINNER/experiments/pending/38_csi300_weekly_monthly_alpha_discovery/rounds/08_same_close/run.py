from pathlib import Path
import sys
import pandas as pd
HERE=Path(__file__).resolve().parent
from measure import R6,R,measure
from evaluate import accounts,E
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
t=pd.read_parquet(R6/"results/targets.parquet")
dfile=R6/"results/dates.csv"
d=pd.read_csv(dfile,parse_dates=["signal_date"])
m=accounts.Market()
for ref in [R,E]:
    dest=OUT/ref;dest.mkdir(exist_ok=True)
    fresh=set(d[(d.model==ref+"_refresh")&d.age.eq(0)&d.new].signal_date)
    z=t[((t.model==ref+"_refresh")&t.parent_date.isin(fresh))|((t.model==ref+"_original")&~t.parent_date.isin(fresh))].copy()
    z["model"]="same_close_"+ref
    z.to_parquet(dest/"targets.parquet",index=False)
    dump(dest/"selection.json",{str(f):sha(f) for f in [HERE/"PROTOCOL.md",Path(__file__),HERE/"measure.py",dfile,R6/"results/targets.parquet",dest/"targets.parquet"]})
    measure(z,t,m,dest)
