from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"03_cost_basis"))
from run import premium,tilt,ROOT as CHECK_ROOT
from evaluate import PRIVATE,accounts,R,E,evaluate
from core import sha,dump
OUT=HERE/"results"
OUT.mkdir(exist_ok=True)
accounts.OUT=OUT
market=accounts.Market()
days=market.days
cp=PRIVATE/"qfq_close.parquet"
tp=PRIVATE/"turnover_rate.parquet"
ip=PRIVATE/"industry.parquet"
turn=pd.read_parquet(tp).reindex(index=days,columns=market.symbols).to_numpy()
industries=pd.read_parquet(ip)
industries["instrument"]=industries.ts_code.str[-2:]+industries.ts_code.str[:6]
scores=pd.read_parquet(ROOT/"results/targets.parquet")
anchor=days.get_loc(scores.signal_date.min())
period=[];cohorts=[]
for i in range(anchor%10,len(days)-11,10):
    if i<119: continue
    idx=np.flatnonzero(market.members[i])
    if len(idx)<100:continue
    px=market.c[i-119:i+1,idx]
    rt=np.clip(turn[i-119:i+1,idx],0,1)
    with np.errstate(divide="ignore",invalid="ignore"):
        actual=premium(px,rt)
        fixed=premium(px,np.broadcast_to(rt.mean(axis=0),rt.shape))
        g=pd.DataFrame(dict(signal=fixed-actual,m20=px[-1]/px[-21],m60=px[-1]/px[-61],
               vol=np.std(px[-20:]/px[-21:-1]-1,axis=0),turnover=rt[-20:].mean(axis=0)),index=market.symbols[idx])
    date=days[i]
    key=date.strftime("%Y%m%d")
    active=industries[industries.in_date.le(key)&(industries.out_date.isna()|industries.out_date.gt(key))]
    names=active[["instrument","l1_name"]].drop_duplicates()
    g["sector"]=names[~names.instrument.duplicated(False)].set_index("instrument").l1_name.reindex(g.index)
    g=g.replace([np.inf,-np.inf],np.nan).dropna()
    if len(g)<100:continue
    entry,exit=i+1,i+11
    j=market.symbols.get_indexer(g.index)
    valid=market.buy[entry,j]&market.sell[exit,j]
    ret=np.where(valid,market.o[exit,j]/market.o[entry,j]-1,np.nan)
    x=np.column_stack([pd.get_dummies(g.sector).to_numpy(),g[["m20","m60","vol","turnover"]].rank(pct=True).to_numpy()])
    def residual(x,y):
        return y-x@np.linalg.lstsq(x,y,rcond=None)[0]
    g["resid"]=residual(x,g.signal.rank(pct=True).to_numpy())
    g["ret"]=ret
    a=g.loc[valid]
    ic=np.corrcoef(residual(x[valid],a.signal.rank(pct=True).to_numpy()),residual(x[valid],a.ret.rank(pct=True).to_numpy()))[0,1]
    spreads=[];sizes=[]
    for sector,h in g.groupby("sector"):
        h=h.sort_values(["resid"],kind="stable")
        n=len(h)//4
        if not n:continue
        hi,lo=h.tail(n),h.head(n)
        ok=hi.ret.notna().all() and lo.ret.notna().all()
        spread=hi.ret.mean()-lo.ret.mean() if ok else np.nan
        cohorts.append(dict(signal_date=date,sector=sector,n=n,high="|".join(hi.index),low="|".join(lo.index),
                            known_high=hi.ret.count(),known_low=lo.ret.count(),spread=spread))
        if ok:spreads.append(spread);sizes.append(len(h))
    period.append(dict(signal_date=date,exit_date=days[exit],members=len(idx),eligible=len(g),tradable=sum(valid),rho=ic,
            spread=np.average(spreads,weights=sizes) if sizes else np.nan,complete_sectors=len(sizes)))
p=pd.DataFrame(period)
p["scope"]=np.select([p.exit_date<days[anchor],p.signal_date<days[anchor],p.exit_date<=pd.Timestamp("2025-03-03")],["early","boundary","primary"],default="later")
p.to_csv(OUT/"windows.csv",index=False)
pd.DataFrame(cohorts).to_parquet(OUT/"cohorts.parquet",index=False)
print(p.groupby("scope").agg({"rho":["size","mean"],"spread":"mean","members":"mean","eligible":"mean","tradable":"mean"}))
early=p[p.scope=="early"]
passed=len(early)>0 and early.rho.mean()>0 and early.spread.mean()>0
dump(OUT/"decision.json",dict(early_direction_passed=bool(passed),earliest=p.signal_date.min(),early_n=len(early),
    input_hashes={str(f.relative_to(ROOT.parent)):sha(f) for f in [cp,tp,ip,PRIVATE/"daily_members.parquet",HERE/"PROTOCOL.md",Path(__file__),HERE.parent/"03_cost_basis/run.py"]}))
if passed:
    g=scores[scores.model.isin([R,E])]
    f=pd.read_parquet(HERE.parent/"03_cost_basis/results/signals.parquet").query("model=='volume_location'")
    h=g[g.model==R].merge(f[["signal_date","instrument","signal"]],on=["signal_date","instrument"],validate="1:1")
    parts=[tilt(z,-z.signal).assign(model="high_cost_location") for _,z in h.groupby("signal_date")]
    sub=OUT/"account";sub.mkdir(exist_ok=True)
    pd.concat([g,*parts],ignore_index=True).to_parquet(sub/"targets.parquet",index=False)
    evaluate(sub,10)
