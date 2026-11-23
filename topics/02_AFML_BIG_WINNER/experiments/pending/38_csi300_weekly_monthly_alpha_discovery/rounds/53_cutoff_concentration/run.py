from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True)
src=here.parent/"50_training_support/results"
calfile=src/"monthly.csv";cal=pd.read_csv(calfile).query('comparison=="delay"').pivot(index=["scope","month"],columns="phase",values="delta").dropna()
indfile=PRIVATE/"industry.parquet";ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
price=PRIVATE/"qfq_close.parquet";days=pd.read_parquet(price,columns=[]).index
inputs=[calfile,indfile,price,Path(__file__),here/"PROTOCOL.md"]
stocks=[]
for phase in range(10):
    p=src/str(phase)/"stock_month.parquet";inputs.append(p)
    h=pd.read_parquet(p)
    h=h[h.model.isin([R,"embargo"])].copy();h["month"]=h.month.astype(str)
    h["delta"]=np.where(h.model==R,-h.pnl,h.pnl)
    amounts=h.groupby(["scope","month","instrument"]).delta.sum()
    np.testing.assert_allclose(amounts.groupby(level=[0,1]).sum().reindex(cal.index),cal[phase],atol=1e-12)
    stocks.append(amounts.rename(phase))
z=pd.concat(stocks,axis=1).fillna(0).mean(axis=1).rename("delta").reset_index()
z=z[z.set_index(["scope","month"]).index.isin(cal.index)].copy()
# Industry dates bound both endpoints and any intervening conflicting interval.
parts=[]
for month,g in z.groupby("month"):
    during=days[days.to_period("M")==pd.Period(month)]
    start,end=during[0].strftime("%Y%m%d"),during[-1].strftime("%Y%m%d")
    overlap=ind[ind.in_date.le(end)&(ind.out_date.isna()|ind.out_date.gt(start))]
    whole=overlap[overlap.in_date.le(start)&(overlap.out_date.isna()|overlap.out_date.gt(end))]
    names=whole[["instrument","l1_name"]].drop_duplicates()
    names=names[names.instrument.map(overlap.groupby("instrument").l1_name.nunique()).eq(1)]
    parts.append(g.assign(sector=g.instrument.map(names.set_index("instrument").l1_name).fillna("未知")))
z=pd.concat(parts);z["quarter"]=pd.PeriodIndex(z.month,freq="M").asfreq("Q").astype(str)
np.testing.assert_allclose(z.groupby(["scope","month"]).delta.sum().reindex(cal.index),cal.mean(axis=1),atol=1e-12)
z.to_parquet(out/"stock_month.parquet",index=False)
rows=[]
for scope,h in z.groupby("scope"):
    n=h.month.nunique()
    for dim in ["instrument","sector","quarter"]:
        total=h.groupby(dim).delta.sum().mul(1e4).sort_values(ascending=False)
        table=total.rename("sum_bp").reset_index();table["months"]=table[dim].map(h.groupby(dim).month.nunique())
        table.to_csv(out/f"{scope}_{dim}.csv",index=False)
        for k in [1,3]:
            leaders=total.head(k)
            rem=h[~h[dim].isin(leaders.index)]
            denom=rem.month.nunique() if dim=="quarter" else n
            rows.append(dict(scope=scope,dimension=dim,k=k,positive=int(total.gt(0).sum()),negative=int(total.lt(0).sum()),groups=len(total),
                total_bp_per_month=total.sum()/n,excluded=",".join(leaders.index),remaining_bp_per_month=rem.delta.sum()*1e4/denom))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);print(s.round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"stock_month.parquet",*sorted(out.glob("*.csv"))]})
