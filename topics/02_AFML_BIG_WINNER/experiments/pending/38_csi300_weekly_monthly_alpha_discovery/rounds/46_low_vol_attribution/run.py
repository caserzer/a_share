from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE
from core import dump,sha
out=here/"results";out.mkdir(exist_ok=True)
src=here.parent/"45_volatility_control/results"
idxfile=PRIVATE/"net_excess_20261116/H00300.CSI.json"
r=json.loads(idxfile.read_text())["data"];b=pd.DataFrame(r["items"],columns=r["fields"])
bench=b.set_index(pd.to_datetime(b.trade_date)).close.sort_index();bench=bench.groupby(bench.index.to_period("M")).last().pct_change()
# Verify all 10 sleeves actually cover each retained month.
full_for_phase=here.parent/"38_all_phases/results/monthly_complete.csv"
calendar=pd.read_csv(full_for_phase).pivot_table(index=["scope","month"],columns="phase",values="delta").dropna().index
inputs=[here/"PROTOCOL.md",Path(__file__),idxfile,full_for_phase]
months=[];stocks=[];periods=[]
for phase in range(10):
    d=src/str(phase);inputs.extend([d/n for n in ["windows.csv","months.csv","stock_month.parquet","accounts.csv"]])
    w=pd.read_csv(d/"windows.csv");m=pd.read_csv(d/"months.csv")
    a=pd.read_csv(d/"accounts.csv").query('cost=="base"').pivot(index="scope",columns="model",values="mdd")
    h=pd.read_parquet(d/"stock_month.parquet")
    h=h[h.model.isin([R,"low_vol"])].copy()
    h["month"]=h.month.astype(str)
    h["delta"]=np.where(h.model.eq(R),-h.pnl,h.pnl)
    stock=h.groupby(["scope","month","instrument"]).delta.sum()
    measured=m[m.model=="low_vol"].set_index(["scope","month"]).delta
    np.testing.assert_allclose(stock.groupby(level=[0,1]).sum().reindex(measured.index),measured,atol=1e-11)
    stocks.append(stock.reset_index().assign(phase=phase))
    months.append(measured.rename(phase))
    for scope,g in w[w.model=="low_vol"].groupby("scope"):
        net=g.groupby("cost")["vs_"+R].mean()*1e4
        periods.append(dict(phase=phase,scope=scope,base=net.base,double=net.double,zero=net.zero,
            vs_e=g[g.cost=="base"]["vs_"+E].mean()*1e4,mdd_pp=(a.loc[scope,"low_vol"]-a.loc[scope,R])*100))
s=pd.DataFrame(periods);s.to_csv(out/"phase.csv",index=False)
active=pd.concat(months,axis=1).loc[calendar].mean(axis=1).rename("active").reset_index()
active["index_return"]=pd.PeriodIndex(active.month,freq="M").map(bench);assert active.index_return.notna().all()
active.to_csv(out/"months.csv",index=False)
stock=pd.concat(stocks).set_index(["scope","month"])
stock=stock[stock.index.isin(calendar)].reset_index()
stock=stock.groupby(["scope","month","instrument"]).delta.sum()/10
np.testing.assert_allclose(stock.groupby(level=[0,1]).sum().reindex(calendar),active.active.to_numpy(),atol=1e-10)
stock.groupby(level=[0,2]).sum().rename("sum_monthly_contributions").to_csv(out/"stock.csv")
rows=[]
for scope,h in active.groupby("scope"):
    v=h.active.to_numpy()*1e4;x=h.index_return.to_numpy()
    intercept,beta=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),v,rcond=None)[0]
    n=len(v);ids=np.random.default_rng(3846).integers(n,size=(20000,(n+2)//3))
    ids=((ids[:,:,None]+np.arange(3))%n).reshape(len(ids),-1)[:,:n]
    lo,hi=np.quantile(v[ids].mean(axis=1),[.025,.975])
    g=s[s.scope==scope];idx=np.argsort(v)[-3:]
    rows.append(dict(scope=scope,positive=int(g.base.gt(0).sum()),months=n,base=g.base.mean(),double=g.double.mean(),zero=g.zero.mean(),mdd_pp=g.mdd_pp.mean(),
        monthly=v.mean(),low=lo,high=hi,ex3=np.delete(v,idx).mean(),best_months=",".join(h.month.iloc[idx]),up_months=int((x>0).sum()),
        up=v[x>0].mean(),down=v[x<=0].mean(),index_beta=beta/1e4,intercept_bp=intercept))
z=pd.DataFrame(rows);z.to_csv(out/"summary.csv",index=False);print(z.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"months.csv",out/"phase.csv",out/"stock.csv"]})
