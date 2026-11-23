from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import assign_deciles,sha,dump
early=here.parent/"71_2018_concentration/results/scores.parquet"
recent=here.parent/"57_recent_industry_labels/results/scores.parquet"
stockfile=here.parent/"87_selected_margin_change/results/targets.parquet"
base=pd.read_parquet(stockfile,filters=[("model","=","original")])
price=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(price,columns=[]).index
cols=["signal_date","instrument",R]
scores=pd.concat([pd.read_parquet(f,columns=cols) for f in [early,recent]])
assert not scores.duplicated(cols[:2]).any()
scores["top"]=False
scores=scores.reset_index(drop=True)
for _,g in scores.groupby("signal_date"):
    scores.loc[g.index,"top"]=assign_deciles(g,R).eq(10).to_numpy()
top=scores.pivot(index="signal_date",columns="instrument",values="top").astype(float)
freq=top.reindex(days).shift(1).rolling(20,min_periods=20).sum()
board=base.merge(scores,on=["signal_date","instrument"],how="left",validate="1:1")
assert board.top.eq(True).all() and len(board)==scores.top.sum()
industry=PRIVATE/"industry.parquet"
ind=pd.read_parquet(industry)
ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
rows=[];pairs=[];coverage=[]
for day,g in board.groupby("signal_date"):
    stamp=day.strftime("%Y%m%d")
    active=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sector=active[~active.instrument.duplicated(False)].set_index("instrument").l1_name
    h=g.set_index("instrument").copy()
    h["freq"]=freq.loc[day].reindex(h.index)
    h["sector"]=h.index.map(sector)
    e=h.dropna(subset=["sector","freq"]).reset_index().sort_values(["sector",R,"instrument"],ascending=[True,False,True])
    e["order"]=e.groupby("sector").cumcount()
    e["pair"]=e.order//2
    z=e[e.order.mod(2)==0].merge(e[e.order.mod(2)==1],on=["sector","pair"],suffixes=("_a","_b"),validate="1:1")
    delta=pd.Series(0.,index=h.index)
    for p in z[z.freq_a.ne(z.freq_b)].itertuples():
        high,low=(p.instrument_a,p.instrument_b) if p.freq_a>p.freq_b else (p.instrument_b,p.instrument_a)
        move=h.at[high,"weight"]/2
        delta[high]+=move
        delta[low]-=move
        pairs.append(dict(day=day,high=high,low=low,sector=p.sector,high_count=h.at[high,"freq"],low_count=h.at[low,"freq"],score_gap=h.at[high,R]-h.at[low,R],budget=move))
    for name,sign in [("overlay",1),("reverse",-1),("original",0)]:
        w=h.weight+sign*delta
        assert w.gt(0).all() and abs(w.sum()-1)<1e-12
        np.testing.assert_allclose(w.groupby(h.sector,dropna=False).sum(),h.weight.groupby(h.sector,dropna=False).sum(),atol=1e-12)
        rows.append(g[base.columns].assign(model=name,weight=g.instrument.map(w)))
    coverage.append(dict(day=day,eligible=len(e),holdings=len(g),active=delta.abs().sum()/2))
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(pairs).to_parquet(out/"pairs.parquet",index=False)
pd.DataFrame(coverage).to_csv(out/"coverage.csv",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [early,recent,stockfile,price,industry,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"pairs.parquet",out/"coverage.csv"]})
