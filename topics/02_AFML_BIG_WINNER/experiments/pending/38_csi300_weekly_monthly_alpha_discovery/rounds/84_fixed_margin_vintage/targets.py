from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
tfile=here.parent/"72_passive_weighting/results/targets.parquet"
t=pd.read_parquet(tfile,filters=[("model","in",["drift_group","snapshot"])])
keys=["phase","signal_date","instrument","entry_date","exit_date","entry_idx","exit_idx","year"]
board=t.pivot(index=keys,columns="model",values="weight").reset_index()
ip=PRIVATE/"industry.parquet";ind=pd.read_parquet(ip);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
cp=PRIVATE/"qfq_close.parquet";days=pd.read_parquet(cp,columns=[]).index
src=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_valuation"
parts=[];files=[]
for code in sorted(board.instrument.unique()):
    f=src/(code[2:]+".parquet")
    if not f.is_file():continue
    a=pd.read_parquet(f,columns=["TRADE_DATE","SECUCODE","PB_MRQ","PS_TTM","PE_TTM"])
    assert a.SECUCODE.dropna().eq(code[2:]+"."+code[:2]).all()
    a["date"]=pd.to_datetime(a.TRADE_DATE);parts.append(a[~a.date.duplicated(False)].assign(instrument=code))
    files.append(f)
vals=pd.concat(parts).set_index(["date","instrument"]).sort_index()
rows=[];covers=[]
for day,g in board.groupby("signal_date"):
    asof=days[days.get_loc(day)-1];stamp=day.strftime("%Y%m%d")
    valid=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sector=valid[~valid.instrument.duplicated(False)].set_index("instrument").l1_name
    h=g.sort_values(["snapshot","instrument"]).set_index("instrument").copy();h["group"]=np.arange(len(h))*5//len(h)
    h["sector"]=h.index.map(sector)
    v=vals.loc[asof] if asof in vals.index.levels[0] else pd.DataFrame(columns=["PB_MRQ","PS_TTM","PE_TTM"])
    h=h.join(v[["PB_MRQ","PS_TTM","PE_TTM"]]);cols=["PB_MRQ","PS_TTM","PE_TTM"];h[cols]=h[cols].apply(pd.to_numeric,errors="coerce")
    ok=h.sector.notna()&~h.sector.isin(["银行","非银金融"])&np.isfinite(h[cols]).all(axis=1)&h.PB_MRQ.gt(0)&h.PS_TTM.gt(0)&h.PE_TTM.ne(0)
    lag=days[days.year==2017][-1]
    assert lag<=asof
    old=vals.loc[lag].reindex(h.index) if lag in vals.index.levels[0] else pd.DataFrame(index=h.index,columns=cols)
    old=old[cols].apply(pd.to_numeric,errors="coerce")
    ok=ok&np.isfinite(old).all(axis=1)&old.PB_MRQ.gt(0)&old.PS_TTM.gt(0)&old.PE_TTM.ne(0)
    h["current"]=np.rint(10000*h.PS_TTM/h.PE_TTM)
    h["old"]=np.rint(10000*old.PS_TTM/old.PE_TTM)
    h["change"]=h.current-h.old
    eligible=h[ok].copy();group=["group","sector"];grp=eligible.groupby(group)
    eligible=eligible[grp.drift_group.transform("size")>=2].copy()
    names=["current","old","change"]
    groups=[eligible[k] for k in group]
    ranks=eligible.groupby(group)[names].rank();size=eligible.groupby(group).drift_group.transform("size")
    multipliers=.5+(ranks-1).div(size-1,axis=0)
    raw=multipliers.mul(eligible.drift_group,axis=0)
    budget=eligible.groupby(group).drift_group.transform("sum")
    delta=raw.div(raw.groupby(groups).transform("sum")).mul(budget,axis=0).sub(eligible.drift_group,axis=0)
    dist=delta.abs().groupby(groups).transform("sum")/2
    target=dist.min(axis=1).where(dist.min(axis=1)>1e-12,0)
    changes=delta.div(dist.where(dist>1e-12)).fillna(0.).mul(target,axis=0)
    np.testing.assert_allclose(changes.abs().groupby(groups).transform("sum").to_numpy()/2,np.broadcast_to(target.to_numpy()[:,None],changes.shape),atol=1e-12)
    for name in names:
        wt=h.drift_group.copy();wt.loc[eligible.index]+=changes[name]
        np.testing.assert_allclose(wt.groupby([h.group,h.sector.fillna("未知")]).sum(),h.drift_group.groupby([h.group,h.sector.fillna("未知")]).sum(),atol=1e-12)
        assert wt.gt(0).all() and abs(wt.sum()-1)<1e-12
        rows.append(h.reset_index()[keys].assign(model=name,weight=wt.to_numpy()))
        covers.append(dict(day=day,valuation_date=asof,lag=lag,changed=int(eligible.change.ne(0).sum()),model=name,covered=len(eligible),negative=int(eligible.PE_TTM.lt(0).sum()),coverage_weight=eligible.drift_group.sum(),active=(wt-h.drift_group).abs().sum()/2,max_stock=wt.max()))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False);pd.DataFrame(covers).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [tfile,ip,cp,*files,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv"]})
