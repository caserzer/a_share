from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,accounts
from core import dump,sha
out=here/"results";r62=here.parent/"62_weight_matched_selection/results/windows.csv";r60=here.parent/"60_benchmark_bridge/results/windows.csv"
ref=pd.read_csv(r62,parse_dates=["signal_date"]).replace({"scope":{"2019_original":"2019"}})
bench=pd.read_csv(r60,parse_dates=["signal_date"]).query("model==@R").replace({"scope":{"2019_original":"2019"}})
key=["scope","phase","signal_date","cost"];files=[r62,r60,out/"target_receipt.json",out/"signal_receipt.json",Path(__file__),here/"account.py",here/"PROTOCOL.md"]
stats=[];risk=[]
for scope in ["2019","2020_flat","2020_half","primary","later"]:
    paths=[out/(scope+f) for f in ["_windows.parquet","_daily.parquet","_accounts.csv"]];files.extend(paths)
    w=pd.read_parquet(paths[0]);daily=pd.read_parquet(paths[1]);a=pd.read_csv(paths[2]);assert a.failure.isna().all()
    v=w.pivot(index=key,columns="model",values="net").join(ref.set_index(key)[[R,E,"capital"]],validate="1:1")
    np.testing.assert_allclose(v.active,v.capital,atol=1e-12,rtol=0)
    v=v.reset_index().merge(bench[["scope","phase","signal_date","benchmark"]],on=key[:3],validate="many_to_one")
    rs=[]
    for (ph,model),h in daily.groupby(["phase","model"]):
        h=h.sort_values("date");nav=h.nav.to_numpy()
        monthly=(1+h.nav.pct_change().fillna(h.nav.iloc[0]-1)).groupby(h.date.dt.to_period("M")).prod().iloc[1:-1]-1
        rs.append(monthly.rename("net").rename_axis("month").reset_index().assign(phase=ph,model=model))
        re=v[(v.phase==ph)&v.cost.eq("base")]
        risk.append(dict(scope=scope,phase=ph,model=model,nav=nav[-1],cagr=nav[-1]**(252/(len(h)-1))-1,mdd=(nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1).min(),turnover=w[(w.phase==ph)&w.cost.eq("base")&w.model.eq(model)].traded.mean(),fee_per_window=w[(w.phase==ph)&w.cost.eq("base")&w.model.eq(model)].fee.mean(),tracking=(re[model]-re.benchmark).std()*np.sqrt(25.2)))
    mon=pd.concat(rs).pivot(index=["phase","month"],columns="model",values="net")
    for name,other in [("switch","active"),("switch","passive"),("active","passive"),("switch",R),("switch",E),("switch","benchmark"),("passive","benchmark")]:
        p=(v[name]-v[other]).groupby([v.phase,v.cost]).mean().unstack()*1e4
        st=dict(scope=scope,model=name,ref=other,n=len(v[v.cost=="base"]),base=p.base.mean(),double=p.double.mean(),zero=p.zero.mean(),positive=p.base.gt(0).sum())
        if other in mon:
            b=(mon[name]-mon[other]).unstack(0).dropna().mean(axis=1)*1e4;n=len(b);idx=np.random.default_rng(3864).integers(n,size=(10000,(n+2)//3))
            idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
            lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975]);st.update(monthly=b.mean(),ex3=b.drop(b.nlargest(3).index).mean(),lo=lo,hi=hi)
        stats.append(st)
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);pd.DataFrame(risk).to_csv(out/"risk.csv",index=False)
market=[PRIVATE/(k+".parquet") for k in ["qfq_open","qfq_close","open","close","daily_members","opening_trade_status_v2","limits/daily"]]
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,*market,Path(accounts.__file__),PRIVATE/"suspensions/daily.parquet",out/"risk.csv",out/"summary.csv"]})
print(s[s.ref.isin(["active","passive","benchmark"])][["scope","model","ref","base","ex3"]].round(2).to_string(index=False))
