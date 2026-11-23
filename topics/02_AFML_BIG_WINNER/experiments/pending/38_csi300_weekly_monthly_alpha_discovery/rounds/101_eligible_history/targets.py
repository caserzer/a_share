from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import assign_deciles,sha,dump
src=here.parent/"98_d10_frequency/results"
pairs_file=src/"pairs.parquet"
tfile=src/"targets.parquet"
p=pd.read_parquet(pairs_file)
base=pd.read_parquet(tfile,filters=[("model","=","original")]).set_index(["signal_date","instrument"]).sort_index()
early=here.parent/"71_2018_concentration/results/scores.parquet"
recent=here.parent/"57_recent_industry_labels/results/scores.parquet"
scores=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument",R]) for f in [early,recent]],ignore_index=True)
scores["top"]=False
for _,g in scores.groupby("signal_date"):
    scores.loc[g.index,"top"]=assign_deciles(g,R).eq(10).to_numpy()
cal=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(cal,columns=[]).index
hist=scores.pivot(index="signal_date",columns="instrument",values="top").astype(float).reindex(days)
month=hist.shift(1).rolling(20,min_periods=20).sum()
quarter=hist.shift(21).rolling(60,min_periods=60).sum()
price=pd.read_parquet(cal).reindex(columns=hist.columns)
member_file=PRIVATE/"daily_members.parquet"
members=pd.read_parquet(member_file).reindex(index=days,columns=hist.columns)
valid_price=(price.gt(0)&np.isfinite(price)).rolling(61).sum().eq(61)
price_screen=valid_price&(price.shift(5)/price.shift(60)).ne(1)&(price/price.shift(5)).ne(1)
certified=hist.isna()&members.eq(True)&~price_screen
certified.loc[~hist.notna().any(axis=1)]=False
quarter_full=hist.mask(certified,0).shift(21).rolling(60,min_periods=60).sum()
i=days.get_indexer(p.day)
assert min(i)>=0
for side in ["high","low"]:
    j=hist.columns.get_indexer(p[side])
    assert min(j)>=0
    np.testing.assert_allclose(month.to_numpy()[i,j],p[side+"_count"])
    p[side+"_old_quarter"]=quarter.to_numpy()[i,j]
    p[side+"_quarter"]=quarter_full.to_numpy()[i,j]
p["month_diff"]=p.high_count-p.low_count
p["quarter_diff"]=p.high_quarter-p.low_quarter
p["growth_diff"]=3*p.month_diff-p.quarter_diff
p["eligible"]=p.quarter_diff.notna()&p.quarter_diff.ne(0)&p.growth_diff.ne(0)
old_file=here.parent/"100_selection_acceleration/results/pairs.parquet"
old=pd.read_parquet(old_file)
assert p[["day","high","low"]].equals(old[["day","high","low"]])
for side in ["high","low"]:
    np.testing.assert_allclose(p[side+"_old_quarter"],old[side+"_quarter"],equal_nan=True)
    known=old[side+"_quarter"].notna()
    np.testing.assert_allclose(p.loc[known,side+"_quarter"],old.loc[known,side+"_quarter"])
p["added"]=p.eligible&~old.eligible
assert old.eligible.le(p.eligible).all()
p.to_parquet(out/"pairs.parquet",index=False)
z=p[p.eligible]
rows=[base.reset_index()]
active=None
for name,field,added_only in [("overlay","growth_diff",False),("frequency","month_diff",False),("added_growth","growth_diff",True),("added_freq","month_diff",True)]:
    z=p[p.added if added_only else p.eligible]
    amount=z.budget*np.sign(z[field])
    a=z.assign(delta=amount).set_index(["day","high"]).delta
    b=z.assign(delta=-amount).set_index(["day","low"]).delta
    delta=pd.concat([a,b])
    delta.index.names=base.index.names
    delta=delta.reindex(base.index,fill_value=0.)
    assert delta.groupby(level=0).sum().abs().max()<1e-12
    funds=delta.abs().groupby(level=0).sum()/2
    if name in ["frequency","added_freq"]:np.testing.assert_allclose(active,funds,atol=1e-12)
    active=funds
    rows.append(base.assign(weight=base.weight+delta,model=name).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.concat([p[p.eligible].groupby("day").budget.sum().rename("all"),active.rename("added")],axis=1).fillna(0).to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [old_file,member_file,pairs_file,tfile,early,recent,cal,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"targets.parquet",out/"pairs.parquet"]})
