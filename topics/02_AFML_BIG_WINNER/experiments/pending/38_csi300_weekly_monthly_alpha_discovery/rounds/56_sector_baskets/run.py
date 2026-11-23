from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE,split
from core import sha,dump
out=here/"results"
indfile=PRIVATE/"industry.parquet";price=PRIVATE/"qfq_open.parquet"
ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
op=pd.read_parquet(price)
rows=[]
files=[indfile,price,here/"PROTOCOL.md",Path(__file__)]
for old,cross,score in [("51_earlier_replication","55_earlier_seats","51_earlier_replication"),("50_training_support","54_industry_seats","38_all_phases")]:
    sr=here.parent/score/"results/scores.parquet";a=here.parent/old/"results/targets.parquet";b=here.parent/cross/"results/targets.parquet";files.extend([sr,a,b])
    pool=pd.read_parquet(sr,columns=["signal_date","instrument"])
    t=pd.concat([pd.read_parquet(a).query("model==@R"),pd.read_parquet(b).query('model=="seats_only"')])
    target=dict(tuple(t.groupby("signal_date")))
    for day,g in pool.groupby("signal_date"):
        h=target[day];entry=h.entry_date.iloc[0];end=h.exit_date.iloc[0]
        scope=str(entry.year) if old.startswith("51") else ("later" if entry>=split else "primary")
        stamp=day.strftime("%Y%m%d");m=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
        m=m[~m.instrument.duplicated(False)].set_index("instrument").l1_name
        idx=pd.Index(g.instrument)
        sector=m.reindex(idx).fillna("未知")
        ret=op.loc[end,idx]/op.loc[entry,idx]-1
        ret=ret.where(np.isfinite(ret))
        weight=h.pivot(index="instrument",columns="model",values="weight").fillna(0)
        change=(weight.seats_only-weight[R]).reindex(idx,fill_value=0)
        assert weight.index.isin(idx).all() and abs(change.sum())<1e-10
        sw=change.groupby(sector).sum();needed=sw[sw.abs()>1e-12]
        means=ret.groupby(sector).mean().reindex(needed.index)
        usable=ret.reindex(weight.index).notna().all() and means.notna().all()
        basket=(needed*means).sum() if usable else np.nan
        actual=(ret*change).sum() if usable else np.nan
        diff_ok=ret[change.abs()>1e-12].notna().all() and means.notna().all()
        eligible=sector.isin(needed.index)
        rows.append(dict(scope=scope,signal_date=day,phase=h.phase.iloc[0],usable=usable,basket=basket,actual=actual,residual=actual-basket,
                         difference_usable=diff_ok,difference_basket=(needed*means).sum() if diff_ok else np.nan,difference_actual=(ret*change).sum() if diff_ok else np.nan,
                         quoted=(ret.notna()&eligible).sum(),total=eligible.sum(),active=change.abs().sum()/2))
v=pd.DataFrame(rows);v.to_csv(out/"windows.csv",index=False)
stats=[]
for scope,g in v.groupby("scope"):
    h=g[g.usable]
    p=h.groupby("phase")[["actual","basket","residual"]].mean()*1e4
    stats.append(dict(scope=scope,n=len(g),usable=len(h),coverage=h.quoted.sum()/h.total.sum(),positive=(p.basket>0).sum(),sensitivity_n=g.difference_usable.sum(),sensitivity_basket=g.groupby("phase").difference_basket.mean().mean()*1e4,**p.mean().to_dict()))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"summary.csv",out/"windows.csv"]})
