from pathlib import Path
import sys

import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump,assign_deciles
from evaluate import R
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
score_file=here.parent/"57_recent_industry_labels/results/scores.parquet"
early_file=here.parent/"71_2018_concentration/results/baseline.parquet"
scores=pd.read_parquet(score_file)
picks=[pd.read_parquet(early_file).query("model==@R")[keys]]
for day,g in scores.groupby("signal_date"):
    chosen=g[assign_deciles(g,R)==10]
    picks.append(chosen.assign(year=day.year)[keys])
selected=pd.concat(picks).set_index("signal_date")
assert not selected.reset_index().duplicated(["signal_date","instrument"]).any()
assert set(selected.index)==set(board.signal_date)
rows=[];covers=[]
for day,g in board.groupby("signal_date"):
    asof=days[days.get_loc(day)-1];stamp=day.strftime("%Y%m%d")
    valid=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sector=valid[~valid.instrument.duplicated(False)].set_index("instrument").l1_name
    h=g.sort_values(["snapshot","instrument"]).set_index("instrument").copy();h["group"]=np.arange(len(h))*5//len(h)
    buckets=h.group
    h=selected.loc[[day]].reset_index().set_index("instrument").copy()
    h["group"]=h.index.map(buckets)
    h["sector"]=h.index.map(sector)
    h["weight"]=1/len(h)
    v=vals.loc[asof] if asof in vals.index.levels[0] else pd.DataFrame(columns=["PB_MRQ","PS_TTM","PE_TTM"])
    h=h.join(v[["PB_MRQ","PS_TTM","PE_TTM"]]);cols=["PB_MRQ","PS_TTM","PE_TTM"];h[cols]=h[cols].apply(pd.to_numeric,errors="coerce")
    ok=h.sector.notna()&~h.sector.isin(["银行","非银金融"])&np.isfinite(h[cols]).all(axis=1)&h.PB_MRQ.gt(0)&h.PS_TTM.gt(0)&h.PE_TTM.ne(0)
    lag=days[days.year==day.year-1][-1]
    assert lag<=asof
    old=vals.loc[lag].reindex(h.index) if lag in vals.index.levels[0] else pd.DataFrame(index=h.index,columns=cols)
    old=old[cols].apply(pd.to_numeric,errors="coerce")
    ok=ok&np.isfinite(old).all(axis=1)&old.PB_MRQ.gt(0)&old.PS_TTM.gt(0)&old.PE_TTM.ne(0)
    h["current"]=np.rint(10000*h.PS_TTM/h.PE_TTM)
    h["old"]=np.rint(10000*old.PS_TTM/old.PE_TTM)
    h["change"]=h.current-h.old
    groups=["group","sector"]
    eligible=h[ok & h.group.notna()].copy()
    size=eligible.groupby(groups).weight.transform("size")
    eligible=eligible[size>=2].copy()
    size=size.loc[eligible.index]
    rank=eligible.groupby(groups).change.rank()
    shift=((rank-1)/(size-1)-.5)*eligible.weight
    for name,direction in [("overlay",1),("reverse",-1),("original",0)]:
        wt=h.weight.copy()
        wt.loc[eligible.index]+=direction*shift
        assert wt.gt(0).all() and abs(wt.sum()-1)<1e-12
        np.testing.assert_allclose(wt.groupby([h.group,h.sector],dropna=False).sum(),h.weight.groupby([h.group,h.sector],dropna=False).sum(),atol=1e-12)
        rows.append(h.reset_index()[keys].assign(model=name,weight=wt.to_numpy()))
        covers.append(dict(day=day,model=name,picks=len(h),covered=len(eligible),active=(wt-h.weight).abs().sum()/2))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False);pd.DataFrame(covers).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [score_file,early_file,tfile,ip,cp,*files,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv"]})
