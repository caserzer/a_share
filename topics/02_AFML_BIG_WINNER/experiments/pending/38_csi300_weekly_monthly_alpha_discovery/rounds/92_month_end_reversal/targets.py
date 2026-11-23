from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
source=here.parent/"72_passive_weighting/results/targets.parquet"
board=pd.read_parquet(source,filters=[("model","=","drift_group")])
files=sorted((PRIVATE/"weights").glob("????-??.json"))
parts=[]
for file in files:
    obj=json.loads(file.read_text()).get("data")
    if obj and obj["items"]:
        parts.append(pd.DataFrame(obj["items"],columns=obj["fields"]))
weights=pd.concat(parts).drop_duplicates()
assert weights.index_code.eq("000300.SH").all()
weights["instrument"]=weights.con_code.str[-2:]+weights.con_code.str[:6]
weights["date"]=pd.to_datetime(weights.trade_date)
assert not weights.duplicated(["date","instrument"]).any()
snap={d:g.set_index("instrument").weight for d,g in weights.groupby("date") if 99<=g.weight.sum()<=101}
days=pd.DatetimeIndex(sorted(snap))
price_file=PRIVATE/"qfq_close.parquet"
prices=pd.read_parquet(price_file)
ind_file=PRIVATE/"industry.parquet"
ind=pd.read_parquet(ind_file)
ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
inputs={}
for i in range(1,len(days)):
    prev,now=days[i-1:i+1]
    if now.to_period("M").ordinal-prev.to_period("M").ordinal!=1 or prev not in prices.index or now not in prices.index:continue
    h=pd.concat([snap[now].rename("new"),snap[prev].rename("old")],axis=1,join="inner")
    h["price"]=prices.loc[now].reindex(h.index)/prices.loc[prev].reindex(h.index)
    h=h[h.price.gt(0)&np.isfinite(h.price)&h.old.gt(.0005)&h.new.gt(.0005)].copy()
    h["low"]=(h.new-.0005)/(h.old+.0005)/h.price
    h["high"]=(h.new+.0005)/(h.old-.0005)/h.price
    inputs[now]=h
rows=[];audit=[];pair_rows=[]
for day,g in board.groupby("signal_date"):
    i=days.searchsorted(day)-1
    now=days[i]
    assert i>=1 and 0<(day-now).days<=45
    h=g.set_index("instrument").copy()
    h["snapshot"]=h.index.map(snap[now])
    assert h.snapshot.gt(0).all()
    h=h.reset_index().sort_values(["snapshot","instrument"]).set_index("instrument")
    h["bucket"]=np.arange(len(h))*5//len(h)
    stamp=day.strftime("%Y%m%d")
    active=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sector=active[~active.instrument.duplicated(False)].set_index("instrument").l1_name
    h["sector"]=h.index.map(sector)
    changes={m:pd.Series(0.,index=h.index) for m in ["inside","outside","combined"]}
    eligible=h.join(inputs.get(now,pd.DataFrame(columns=["low","high","price"])),how="inner").dropna(subset=["sector","low","high","price"])
    for (bucket,industry),z in eligible.groupby(["bucket","sector"]):
        donor,recipient=z.high.idxmin(),z.low.idxmax()
        lagger,leader=z.price.idxmin(),z.price.idxmax()
        if lagger==leader:continue
        matched=z.at[recipient,"low"]>z.at[donor,"high"]
        model="inside" if matched else "outside"
        budget=.5*z.loc[[donor,recipient,lagger,leader] if matched else [lagger,leader],"weight"].min()
        for sleeve in [model,"combined"]:
            changes[sleeve][leader]-=budget
            changes[sleeve][lagger]+=budget
        pair_rows.append(dict(day=day,snapshot=now,prior=days[i-1],bucket=bucket,industry=industry,model=model,lagger=lagger,leader=leader,budget=budget))
    for name,delta in changes.items():
        w=h.weight+delta
        assert w.gt(0).all() and abs(w.sum()-1)<1e-12
        assert delta.groupby([h.bucket,h.sector],dropna=False).sum().abs().max()<1e-12
        np.testing.assert_allclose(changes["combined"],changes["inside"]+changes["outside"],atol=1e-12)
        rows.append(h[g.columns.drop("instrument")].assign(weight=w,model=name).reset_index())
        audit.append(dict(day=day,model=name,snapshot=now,prior=days[i-1],eligible=len(eligible),eligible_weight=eligible.weight.sum(),active=delta.abs().sum()/2))
targets=pd.concat(rows)
prior_file=here.parent/"91_index_weight_residual/results/targets.parquet"
join_cols=["signal_date","instrument"]
prior=pd.read_parquet(prior_file,filters=[("model","=","price")]).set_index(join_cols).weight.sort_index()
base=board.set_index(join_cols).weight.sort_index()
mirror=targets.query('model=="inside"').set_index(join_cols).weight.sort_index()
assert mirror.index.equals(prior.index) and base.index.equals(prior.index)
np.testing.assert_allclose(mirror+prior,2*base,atol=1e-12)
targets.to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
pd.DataFrame(pair_rows).to_parquet(out/"pairs.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [prior_file,source,price_file,ind_file,*files,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv",out/"pairs.parquet"]})
