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
early_file=here.parent/"71_2018_concentration/results/scores.parquet"
scores=pd.concat([pd.read_parquet(score_file),pd.read_parquet(early_file)],ignore_index=True)
predictions={day:g[["instrument",R]].assign(decile=assign_deciles(g,R)).set_index("instrument") for day,g in scores.groupby("signal_date")}
assert set(predictions)==set(board.signal_date)
rows=[];covers=[]
for day,g in board.groupby("signal_date"):
    asof=days[days.get_loc(day)-1];stamp=day.strftime("%Y%m%d")
    valid=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name","l3_code"]].drop_duplicates()
    valid=valid[~valid.instrument.duplicated(False)].set_index("instrument")
    ranked=g.sort_values(["snapshot","instrument"]).set_index("instrument")
    buckets=pd.Series(np.arange(len(ranked))*5//len(ranked),index=ranked.index)
    h=predictions[day].query("decile>=9").copy()
    h["group"]=h.index.map(buckets)
    h["sector"]=h.index.map(valid.l1_name)
    h["fine"]=h.index.map(valid.l3_code)
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
    groups=["group","sector","fine"]
    eligible=h[ok & h.group.notna() & h.fine.notna()].reset_index().sort_values([R,"instrument"])
    inside=eligible[eligible.decile.eq(10)].drop_duplicates(groups,keep="first")
    outside=eligible[eligible.decile.eq(9)].drop_duplicates(groups,keep="last")
    pairs=inside.merge(outside,on=groups,suffixes=("_in","_out"),validate="1:1")
    original=h.index[h.decile.eq(10)].to_list()
    meta=g.iloc[0][[k for k in keys if k!="instrument"]].to_dict()
    pick=None
    if len(pairs):
        pairs["gap"]=pairs[R+"_in"]-pairs[R+"_out"]
        assert pairs.gap.min()>=-1e-12
        pick=pairs.sort_values(["gap","instrument_in","instrument_out"]).iloc[0]
    direction=0 if pick is None else np.sign(pick.change_out-pick.change_in)
    for model,swap in [("overlay",direction>0),("reverse",direction<0),("always",pick is not None),("original",False)]:
        names=list(original)
        if swap:names[names.index(pick.instrument_in)]=pick.instrument_out
        assert len(set(names))==len(original)
        rows.append(pd.DataFrame(dict(instrument=names,**meta,model=model,weight=1/len(names))))
        covers.append(dict(day=day,model=model,picks=len(names),pairs=len(pairs),swap=swap,active=swap/len(names),
                           removed=None if pick is None else pick.instrument_in,candidate=None if pick is None else pick.instrument_out,
                           signal_difference=np.nan if pick is None else pick.change_out-pick.change_in))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False);pd.DataFrame(covers).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [score_file,early_file,tfile,ip,cp,*files,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv"]})
