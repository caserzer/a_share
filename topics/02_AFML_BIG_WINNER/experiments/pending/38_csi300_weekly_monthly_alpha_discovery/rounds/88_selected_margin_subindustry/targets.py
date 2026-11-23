from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
source=here.parent/"72_passive_weighting/results/targets.parquet"
signal=here.parent/"87_selected_margin_change/results/targets.parquet"
t=pd.read_parquet(signal,filters=[("model","in",["original","overlay"])])
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date"]
board=t.pivot(index=keys,columns="model",values="weight").reset_index()
universe=pd.read_parquet(source,filters=[("model","=","snapshot")]).sort_values(["signal_date","weight","instrument"])
by_day=universe.groupby("signal_date")
universe["bucket"]=5*by_day.cumcount()//by_day.weight.transform("size")
board=board.merge(universe[["signal_date","instrument","bucket"]],on=["signal_date","instrument"],how="left",validate="1:1")
board["bucket"]=board.bucket.fillna(-1)
indfile=PRIVATE/"industry.parquet";ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
rows=[];audit=[]
for day,h in board.groupby("signal_date"):
    stamp=day.strftime("%Y%m%d")
    eligible=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))]
    h=h.copy()
    for key,col in [("broad","l1_name"),("sector","l3_code")]:
        code=eligible[["instrument",col]].drop_duplicates()
        code=code[~code.instrument.duplicated(False)].set_index("instrument")[col]
        h[key]=h.instrument.map(code).fillna("未知")
    h["changed"]=abs(h.original-h.overlay)>1e-12
    groups=h.groupby(["bucket","broad","sector","changed"])
    before=groups.original.transform("sum")
    after=groups.overlay.transform("sum")
    for model,w in [("sector_budget",h.original*after/before),("stock_weight",h.overlay*before/after),("original",h.original),("overlay",h.overlay)]:
        assert abs(w.sum()-1)<1e-12 and w.gt(0).all()
        np.testing.assert_allclose(w[~h.changed],h.original[~h.changed],atol=1e-12)
        np.testing.assert_allclose(w.groupby([h.bucket,h.broad]).sum(),h.original.groupby([h.bucket,h.broad]).sum(),atol=1e-12)
        rows.append(h[keys].assign(weight=w,model=model))
        audit.append(dict(day=day,model=model,unknown=h.sector.eq("未知").sum(),stocks=len(h),active=(w-h.original).abs().sum()/2))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False);pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,signal,indfile,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"targets.parquet"]})
