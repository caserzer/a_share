from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,accounts,PRIVATE,split
from core import sha,dump
accounts.OUT=OUT;m=accounts.Market()
raw=pd.read_parquet(PRIVATE/"industry.parquet")
raw["instrument"]=raw.ts_code.str[-2:]+raw.ts_code.str[:6]
rows=[];date_stats=[];monthly=[];checks=[]
for phase,path in [(0,HERE.parent/"16_industry_pool/results"),(5,HERE.parent/"17_calendar_challenge/results")]:
    targets=pd.read_parquet(path/"targets.parquet")
    w=pd.read_csv(path/"windows.csv",parse_dates=["signal_date"])
    stock=pd.read_parquet(path/"stock_month.parquet")
    val="contribution" if phase==0 else "pnl"
    for scope in ["primary","later"]:
        part=stock[stock.scope==scope].pivot_table(index=["month","instrument"],columns="model",values=val,aggfunc="sum").fillna(0.)
        active=part.early_model-part[R]
        monthly.append(active.rename("paired").reset_index().assign(phase=phase,scope=scope))
        z=w[(w.scope==scope)&(w.model=="early_model")&(w.cost=="base")].sort_values("signal_date")
        v=z["vs_"+R].to_numpy();n=len(v)
        starts=np.random.default_rng(38).integers(n,size=(10000,(n+2)//3))
        ids=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
        lo,hi=np.quantile(v[ids].mean(axis=1),[.025/28,1-.025/28])
        mon=active.groupby("month").sum()
        for dt,g in targets[targets.signal_date.isin(z.signal_date)].groupby("signal_date"):
            a=g[g.model=="early_model"];b=g[g.model==R]
            ins=set(a.instrument)-set(b.instrument);outs=set(b.instrument)-set(a.instrument)
            assert len(ins)==len(outs)
            e,x=int(a.entry_idx.iloc[0]),int(a.exit_idx.iloc[0])
            key=dt.strftime("%Y%m%d")
            maps=raw[raw.in_date.le(key)&(raw.out_date.isna()|raw.out_date.gt(key))][["instrument","l1_name","l3_code"]].drop_duplicates()
            maps=maps[~maps.instrument.duplicated(False)].set_index("instrument")
            j=np.flatnonzero(m.members[e-1])
            h=maps.reindex(m.symbols[j]).copy()
            ok=m.buy[e,j]&m.sell[x,j]
            h["ret"]=np.where(ok,m.o[x,j]/m.o[e,j]*(1-.002)/(1+.001)-1,np.nan)
            other=h[~h.index.isin(ins|outs)].groupby("l3_code").ret.agg(["mean","count","size"])
            rank=pd.concat([a,b]).drop_duplicates("instrument").set_index("instrument")[R]
            h["rank"]=rank.reindex(h.index)
            for sector,entered in h[h.index.isin(ins)].groupby("l1_name"):
                left=h[h.index.isin(outs)&h.l1_name.eq(sector)]
                assert len(left)==len(entered)
                for (one,first),(two,second) in zip(entered.sort_values("rank",ascending=False).iterrows(),left.sort_values("rank",ascending=False).iterrows()):
                    inpeer=other.reindex([first.l3_code]).iloc[0]
                    outpeer=other.reindex([second.l3_code]).iloc[0]
                    delta=first.ret-second.ret; industry=inpeer["mean"]-outpeer["mean"]
                    rows.append(dict(phase=phase,scope=scope,signal_date=dt,sector=sector,incoming=one,outgoing=two,
                        n_peer_in=inpeer["count"],n_peer_out=outpeer["count"],weight=1/len(a),delta=delta,industry=industry,
                        specific=delta-industry))
            date_stats.append(dict(phase=phase,scope=scope,signal_date=dt,active=len(ins)/len(a)))
        checks.append(dict(phase=phase,scope=scope,n=n,net=v.mean(),lo=lo,hi=hi,ex3=mon.drop(mon.nlargest(3).index).mean(),
               top_month=str(mon.idxmax()),top_value=mon.max(),bottom_month=str(mon.idxmin()),bottom_value=mon.min()))
z=pd.DataFrame(rows)
known=z.dropna(subset=["delta","industry"])
np.testing.assert_allclose(known.delta,known.industry+known.specific,atol=1e-14)
z.to_csv(OUT/"swaps.csv",index=False)
pd.concat(monthly).to_parquet(OUT/"monthly_stock_contributions.parquet",index=False)
pd.DataFrame(date_stats).to_csv(OUT/"active_capital.csv",index=False)
s=pd.DataFrame(checks)
stats=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    k=g.dropna(subset=["delta","industry"]);n=int(s[(s.phase==phase)&(s.scope==scope)].n.iloc[0])
    stats.append(dict(phase=phase,scope=scope,swaps=len(g),priced=g.delta.count(),identified=len(k),budget_coverage=k.weight.sum()/g.weight.sum(),
        industry_known=(k.weight*k.industry).sum()/n,specific_known=(k.weight*k.specific).sum()/n))
s=s.merge(pd.DataFrame(stats),on=["phase","scope"])
s.to_csv(OUT/"summary.csv",index=False);print(s.round(6).to_string(index=False))
dump(OUT/"verification.json",dict(decomposition_checked=len(known),inputs={str(f):sha(f) for f in [HERE/"PROTOCOL.md",Path(__file__),OUT/"swaps.csv",OUT/"summary.csv",PRIVATE/"industry.parquet"]}))
