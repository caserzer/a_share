from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
ref=HERE.parent/"26_merger_continuity/results"
files=[ref/(name+".parquet") for name in ["orders","daily"]]+[ref/"windows.csv",PRIVATE/"money.parquet"]
orders=pd.read_parquet(files[0]);daily=pd.read_parquet(files[1])
win=pd.read_csv(files[2],parse_dates=["signal_date"]).query("cost=='base'").copy()
money=pd.read_parquet(files[3])
adv=money.rolling(20,min_periods=20).mean().shift()
orders["amount"]=orders.buy+orders.sell
orders=orders.loc[orders.amount>0].copy()
assert not orders.duplicated(["model","date","instrument"]).any()
assert np.allclose(orders.buy*orders.sell,0.) and (orders.amount>0).all()
np.testing.assert_allclose(orders.fee,orders.buy*.001+orders.sell*.002,atol=1e-14)
fee=orders.groupby(["model","date"]).fee.sum()
d=daily.set_index(["model","date"])
np.testing.assert_allclose(fee.reindex(d.index,fill_value=0.),d.fees,atol=1e-12)
i=adv.index.get_indexer(orders.date);j=adv.columns.get_indexer(orders.instrument)
assert min(i)>=20 and min(j)>=0
orders["adv"]=adv.to_numpy()[i,j]
orders["adv"]=orders.adv.where(orders.adv>0)
orders["initial_limit_1pct"]=.01*orders.adv/orders.amount
out=[];summary=[];limits=[]
for model,g in orders.groupby("model"):
    g=g.copy()
    w=win[win.model==model].sort_values("signal_date").reset_index(drop=True)
    assert len(w)==139
    entries=money.index[money.index.get_indexer(w.signal_date)+1]
    k=entries.searchsorted(g.date,side="right")-1
    assert min(k)>=0
    pre=(1+w.net).cumprod().shift().fillna(1.)
    g["window"]=k;g["start_nav"]=pre.to_numpy()[k]
    known=g.adv.notna()
    worst=g.loc[g.initial_limit_1pct.idxmin()]
    for threshold in [.001,.01,.05]:
        limits.append(dict(model=model,adv_fraction=threshold,known_order_ceiling=worst.initial_limit_1pct*threshold/.01,
                           date=worst.date,stock=worst.instrument,side="buy" if worst.buy else "sell",adv=worst.adv,
                           normalized_order=worst.amount,unknown=(~known).sum()))
    for capital in [1e6,1e7,1e8,1e9]:
        part=g.amount*capital/g.adv
        rate=.001*np.sqrt(part/.01).clip(upper=10.)
        expense=g.amount/g.start_nav*rate
        low=expense.fillna(0.).groupby(k).sum().reindex(w.index,fill_value=0.)
        high=expense.fillna(g.amount/g.start_nav*.01).groupby(k).sum().reindex(w.index,fill_value=0.)
        breach=part>.01
        assert (high>=low).all()
        summary.append(dict(model=model,capital=capital,orders=len(g),unknown=(~known).sum(),
            unknown_amount_share=g.loc[~known,"amount"].sum()/g.amount.sum(),
            breaches=breach.sum(),breach_amount_share=g.loc[breach,"amount"].sum()/g.amount.sum(),
            max_known_part=part.max(),low_cost_bp=low.mean()*1e4,high_cost_bp=high.mean()*1e4))
        out.append(pd.DataFrame(dict(model=model,capital=capital,date=w.signal_date,net=w.net,low=low,high=high)))
x=pd.concat(out,ignore_index=True)
paired=[]
for c,g in x.groupby("capital"):
    p=g[g.model=="early_model"].merge(g[g.model==R],on="date",suffixes=("_c","_r"),validate="1:1")
    base=p.net_c-p.net_r
    assert abs(base.mean()*1e4-2.91635)<.0001
    paired.append(dict(capital=c,base_bp=base.mean()*1e4,
        stressed_low_bp=(base-p.high_c+p.low_r).mean()*1e4,stressed_high_bp=(base-p.low_c+p.high_r).mean()*1e4,
        known_cost_only_bp=(base-p.low_c+p.low_r).mean()*1e4))
z=pd.DataFrame(summary);l=pd.DataFrame(limits);a=pd.DataFrame(paired)
z.to_csv(OUT/"scale.csv",index=False);l.to_csv(OUT/"limiting_orders.csv",index=False)
a.to_csv(OUT/"paired.csv",index=False);x.to_parquet(OUT/"windows.parquet",index=False)
orders.to_parquet(OUT/"order_liquidity.parquet",index=False)
print(z[z.model=="early_model"].round(5).to_string(index=False));print(a.round(3).to_string(index=False))
print(l.query('adv_fraction==.01').round(3).to_string(index=False))
dump(OUT/"receipt.json",{str(f):sha(f) for f in [*files,HERE/"PROTOCOL.md",Path(__file__),OUT/"paired.csv",OUT/"limiting_orders.csv"]})
