from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
source=here.parent/"72_passive_weighting/results/targets.parquet"
signal=here.parent/"75_profitability/results/targets.parquet"
t=pd.concat([pd.read_parquet(source,filters=[("model","in",["drift_group","snapshot"])]),pd.read_parquet(signal,filters=[("model","=","margin")])],ignore_index=True)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date"]
board=t.pivot(index=keys,columns="model",values="weight").reset_index()
indfile=PRIVATE/"industry.parquet";ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
rows=[];audit=[]
for day,h in board.groupby("signal_date"):
    stamp=day.strftime("%Y%m%d")
    eligible=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))]
    h=h.sort_values(["snapshot","instrument"]).copy()
    h["bucket"]=np.arange(len(h))*5//len(h)
    for key,col in [("broad","l1_name"),("sector","l3_code")]:
        code=eligible[["instrument",col]].drop_duplicates()
        code=code[~code.instrument.duplicated(False)].set_index("instrument")[col]
        h[key]=h.instrument.map(code).fillna("未知")
    groups=h.groupby(["bucket","broad","sector"]);a=groups.drift_group.transform("sum");b=groups.margin.transform("sum")
    for model,w in [("sector_budget",h.drift_group*b/a),("stock_weight",h.margin*a/b)]:
        assert abs(w.sum()-1)<1e-12
        np.testing.assert_allclose(w.groupby(h.bucket).sum(),h.margin.groupby(h.bucket).sum(),atol=1e-12)
        rows.append(h[keys].assign(weight=w,model=model))
    audit.append(dict(day=day,unknown=h.sector.eq("未知").sum(),stocks=len(h),unknown_weight=h.margin[h.sector.eq("未知")].sum()))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False);pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,signal,indfile,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"targets.parquet"]})
