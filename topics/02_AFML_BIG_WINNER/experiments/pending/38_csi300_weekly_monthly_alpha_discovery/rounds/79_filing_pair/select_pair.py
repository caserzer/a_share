from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
f=here.parent/"72_passive_weighting/results/targets.parquet";t=pd.read_parquet(f,filters=[("model","in",["snapshot","drift_group"])])
day=t.loc[t.signal_date.ge("2019-05-01"),"signal_date"].min()
h=t[t.signal_date.eq(day)].pivot(index="instrument",columns="model",values="weight").reset_index().sort_values(["snapshot","instrument"])
h["group"]=np.arange(len(h))*5//len(h)
ip=PRIVATE/"industry.parquet";ind=pd.read_parquet(ip);stamp=day.strftime("%Y%m%d")
i=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["ts_code","l1_name"]].drop_duplicates()
i=i[~i.ts_code.duplicated(False)].copy();i["instrument"]=i.ts_code.str[-2:]+i.ts_code.str[:6]
h=h.merge(i,on="instrument");h=h[~h.l1_name.isin(["银行","非银金融"])];groups=h.groupby(["group","l1_name"]).drift_group.agg(["size","sum"])
grp=groups[groups["size"]>=2]["sum"].idxmax();picked=h[(h.group==grp[0])&(h.l1_name==grp[1])].nlargest(2,"drift_group").copy()
picked["signal_date"]=day;p=here/"results/selected.csv";picked.to_csv(p,index=False);print(picked.to_string(index=False))
dump(here/"results/selection_receipt.json",{str(x):sha(x) for x in [f,ip,Path(__file__),here/"PROTOCOL.md",p]})
