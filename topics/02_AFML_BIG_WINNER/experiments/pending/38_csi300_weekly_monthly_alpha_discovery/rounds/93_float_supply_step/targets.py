from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
source=here.parent/"72_passive_weighting/results/targets.parquet"
board=pd.read_parquet(source,filters=[("model","in",["drift_group","snapshot"])])
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date"]
board=board.pivot(index=keys,columns="model",values="weight").reset_index()
paths={k:PRIVATE/(k+".parquet") for k in ["volume","turnover_rate","close","qfq_close","industry"]}
vol=pd.read_parquet(paths["volume"])
turn=pd.read_parquet(paths["turnover_rate"])
shares=(vol/turn.where(turn.gt(0))).where(vol.gt(0)).round()
raw=pd.read_parquet(paths["close"])
price=pd.read_parquet(paths["qfq_close"])
factor=raw/price.where(price.gt(0))
clean=(factor.rolling(7).max()/factor.rolling(7).min()).le(1.000001)
old=shares.shift(2).rolling(5)
new=shares.rolling(2)
stable=clean&(shares.rolling(7).max()-shares.rolling(7).min()).le(2)
valid=clean&(old.max()-old.min()).le(2)&(new.max()-new.min()).le(2)
diff=new.mean()-old.mean()
step=(diff/old.mean()).where(valid&diff.abs().ge(100))
returns=price/price.shift(20)-1
ind=pd.read_parquet(paths["industry"])
ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
rows=[];matches=[];covers=[];events=[]
for day,g in board.groupby("signal_date"):
    h=g.sort_values(["snapshot","instrument"]).set_index("instrument").copy()
    h["bucket"]=np.arange(len(h))*5//len(h)
    stamp=day.strftime("%Y%m%d")
    s=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    h["sector"]=h.index.map(s[~s.instrument.duplicated(False)].set_index("instrument").l1_name)
    h["step"]=step.loc[day].reindex(h.index)
    h["stable"]=stable.loc[day].reindex(h.index).eq(True)
    h["ret"]=returns.loc[day].reindex(h.index)
    e=h[h.step.notna()].assign(magnitude=lambda z:z.step.abs()).reset_index().sort_values(["magnitude","instrument"],ascending=[False,True])
    deltas={k:pd.Series(0.,index=h.index) for k in ["expand","contract","combined"]}
    used=set()
    for event in e.itertuples():
        code=event.instrument
        peer=h[h.stable & h.bucket.eq(event.bucket)&h.sector.eq(event.sector)&~h.index.isin(used)].dropna(subset=["ret"])
        ok=np.isfinite(event.ret) and len(peer)>0
        events.append(dict(day=day,instrument=code,relative_step=event.step,before=shares.loc[shares.index[shares.index.get_loc(day)-2],code],after=shares.at[day,code],matched=ok))
        if not ok:continue
        peer=peer.assign(distance=(peer.ret-event.ret).abs()).reset_index().sort_values(["distance","instrument"]).iloc[0]
        other=peer.instrument
        used.add(other)
        sleeve="expand" if event.step>0 else "contract"
        buy,sell=(other,code) if event.step>0 else (code,other)
        budget=.5*min(h.at[buy,"drift_group"],h.at[sell,"drift_group"])
        for model in [sleeve,"combined"]:
            deltas[model][buy]+=budget
            deltas[model][sell]-=budget
        matches.append(dict(day=day,entry=event.entry_idx,exit=event.exit_idx,event=code,peer=other,buy=buy,sell=sell,sleeve=sleeve,relative_step=event.step,distance=peer.distance,budget=budget))
    for model,delta in deltas.items():
        w=h.drift_group+delta
        assert w.gt(0).all() and abs(w.sum()-1)<1e-12
        assert delta.groupby([h.bucket,h.sector],dropna=False).sum().abs().max()<1e-12
        rows.append(h.reset_index()[keys].assign(weight=w.to_numpy(),model=model))
        covers.append(dict(day=day,model=model,active=delta.abs().sum()/2,stable=int(h.stable.sum()),events=len(e)))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(matches).to_csv(out/"pairs.csv",index=False)
pd.DataFrame(covers).to_csv(out/"coverage.csv",index=False)
pd.DataFrame(events).to_csv(out/"events.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*paths.values(),Path(__file__),here/"PROTOCOL.md",*[out/k for k in ["targets.parquet","pairs.csv","coverage.csv","events.csv"]]]})
