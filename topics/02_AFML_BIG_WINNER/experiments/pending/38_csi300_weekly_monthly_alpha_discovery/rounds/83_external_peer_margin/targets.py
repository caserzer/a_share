from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import dump,sha
source=here.parent/"72_passive_weighting/results/targets.parquet";t=pd.read_parquet(source,filters=[("model","in",["snapshot","drift_group"])])
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date"];h=t.pivot(index=keys,columns="model",values="weight").reset_index()
ip=PRIVATE/"industry.parquet";ind=pd.read_parquet(ip);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
cp=PRIVATE/"qfq_close.parquet";days=pd.read_parquet(cp,columns=[]).index
src=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_valuation";parts=[];files=[]
for code in sorted(h.instrument.unique()):
    f=src/(code[2:]+".parquet")
    if not f.exists():continue
    a=pd.read_parquet(f,columns=["TRADE_DATE","SECUCODE","PB_MRQ","PS_TTM","PE_TTM"]);assert a.SECUCODE.dropna().eq(code[2:]+"."+code[:2]).all()
    a["asof"]=pd.to_datetime(a.TRADE_DATE);a=a[~a["asof"].duplicated(False)].copy()
    cols=["PB_MRQ","PS_TTM","PE_TTM"];nums=a[cols].apply(pd.to_numeric,errors="coerce");ok=np.isfinite(nums).all(axis=1)&nums.PB_MRQ.gt(0)&nums.PS_TTM.gt(0)&nums.PE_TTM.ne(0)
    parts.append(a[["asof"]].assign(instrument=code,margin=(nums.PS_TTM/nums.PE_TTM).where(ok)));files.append(f)
values=pd.concat(parts).set_index(["asof","instrument"]).margin
# Compute a distinct median for each excluded size bucket, using only securities outside it.
rows=[];coverage=[]
for day,g in h.groupby("signal_date"):
    z=g.sort_values(["snapshot","instrument"]).copy();z["bucket"]=np.arange(len(z))*5//len(z)
    asof=days[days.get_loc(day)-1];stamp=day.strftime("%Y%m%d")
    v=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name","l3_code"]].drop_duplicates()
    v=v[~v.instrument.duplicated(False)];z=z.merge(v,on="instrument",how="left",validate="1:1")
    z["margin"]=z.instrument.map(values.loc[asof]) if asof in values.index.levels[0] else np.nan
    eligible=z.dropna(subset=["l1_name","l3_code","margin"]);eligible=eligible[~eligible.l1_name.isin(["银行","非银金融"])]
    cells=["bucket","l1_name","l3_code"]
    own=eligible.groupby(cells).agg(budget=("drift_group","sum"),own=("margin","median"))
    peers=[]
    for k in range(5):
        other=eligible[eligible.bucket.ne(k)].groupby(["l1_name","l3_code"]).margin.agg(["median","count"])
        peers.append(other[other["count"]>=2][["median"]].rename(columns={"median":"outside"}).assign(bucket=k).reset_index())
    sec=own.join(pd.concat(peers).set_index(cells),how="inner").reset_index()
    groups=["bucket","l1_name"];sec=sec[sec.groupby(groups).budget.transform("size")>=2].copy();base=sec.budget
    fac=["own","outside"];ranks=sec.groupby(groups)[fac].rank()
    mult=.5+(ranks-1).div(sec.groupby(groups).budget.transform("size")-1,axis=0)
    groupers=[sec[k] for k in groups];raw=mult.mul(base,axis=0)
    dw=raw.div(raw.groupby(groupers).transform("sum")).mul(base.groupby(groupers).transform("sum"),axis=0).sub(base,axis=0)
    dist=dw.abs().groupby(groupers).transform("sum")/2;target=dist.min(axis=1).where(dist.min(axis=1)>1e-12,0.)
    delta=dw.div(dist.where(dist>1e-12)).fillna(0.).mul(target,axis=0)
    for name in fac:
        adj=sec[cells].assign(scale=1+delta[name]/base)
        u=z.merge(adj,on=cells,how="left",validate="m:1")
        wt=u.drift_group*u.scale.where(u.margin.notna(),1.).fillna(1.)
        np.testing.assert_allclose(wt.groupby([u.bucket,u.l1_name.fillna("未知")]).sum(),u.drift_group.groupby([u.bucket,u.l1_name.fillna("未知")]).sum(),atol=1e-12)
        rows.append(u[keys].assign(model=name,weight=wt))
        coverage.append(dict(day=day,model=name,asof=asof,cell_count=len(sec),covered=base.sum(),active=(wt-u.drift_group).abs().sum()/2))
t=pd.concat(rows,ignore_index=True);t.to_parquet(out/"targets.parquet",index=False)
c=pd.DataFrame(coverage);cs=c.pivot(index="day",columns="model",values="active");np.testing.assert_allclose(cs.own,cs.outside,atol=1e-12)
c.to_csv(out/"coverage.csv",index=False);print(c.groupby("model").mean(numeric_only=True))
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,cp,ip,*files,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"targets.parquet"]})
