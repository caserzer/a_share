from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R,E,accounts
from core import sha,dump
r71=here.parent/"71_2018_concentration/results";r64=here.parent/"64_mature_group_switch/results"
files=[out/"target_receipt.json",here/"account.py",here.parent/"64_mature_group_switch/account.py",r71/"receipt.json",r64/"receipt.json",Path(__file__),Path(accounts.__file__)]
ref62=here.parent/"62_weight_matched_selection/results/windows.csv";ref60=here.parent/"60_benchmark_bridge/results/windows.csv";files.extend([ref62,ref60])
rows=[];risk=[];periods=[]
for scope in ["2018","2018_half","2019","2020_flat","2020_half","primary","later"]:
    wfile=out/(scope+"_windows.parquet");dfile=out/(scope+"_daily.parquet");afile=out/(scope+"_accounts.csv");files.extend([wfile,dfile,afile])
    old72=here.parent/"72_passive_weighting/results";w72=old72/(scope+"_windows.parquet");d72=old72/(scope+"_daily.parquet");files.extend([w72,d72])
    old75=here.parent/"75_profitability/results";w75=old75/(scope+"_windows.parquet");d75=old75/(scope+"_daily.parquet");files.extend([w75,d75])
    keys=["phase","cost","signal_date"];w=pd.concat([pd.read_parquet(wfile),pd.read_parquet(w72).query('model in ["passive","drift_group"]'),pd.read_parquet(w75).query('model=="margin"')]);v=w.pivot(index=keys,columns="model",values="net")
    assert pd.read_csv(afile).failure.isna().all()
    if scope.startswith("2018"):
        mode="flat_archive" if scope=="2018" else "half_archive";ref=r71/mode/"windows.parquet";files.extend([ref,r71/(mode+"_prices.csv"),r71/mode/"suspensions.parquet"])
        old=pd.read_parquet(ref);baseline=old.pivot(index=keys,columns="model",values="net");index=old.groupby(keys).benchmark.first()
    else:
        ref=r64/(scope+"_windows.parquet");files.append(ref)
        old=pd.read_parquet(ref);baseline=old.pivot(index=keys,columns="model",values="net")
        label="2019_original" if scope=="2019" else scope
        baseline=baseline.join(pd.read_csv(ref62,parse_dates=["signal_date"]).query('scope==@label').set_index(keys)[[R,E]])
        index=pd.read_csv(ref60,parse_dates=["signal_date"]).query('scope==@label and model==@R').set_index(["phase","signal_date"]).benchmark
        index=pd.Series(index.reindex(v.index.droplevel("cost")).to_numpy(),index=v.index)
    np.testing.assert_allclose(baseline.passive.reindex(v.index),v.passive,atol=1e-12,rtol=0)
    v=v.join(baseline[[R,E]]);v["benchmark"]=index.reindex(v.index);assert v.notna().all().all()
    periods.append(v.reset_index().assign(scope=scope))
    months=[];daily=pd.concat([pd.read_parquet(dfile),pd.read_parquet(d72).query('model in ["passive","drift_group"]'),pd.read_parquet(d75).query('model=="margin"')])
    for (ph,model),g in daily.groupby(["phase","model"]):
        g=g.sort_values("date");nav=g.nav.to_numpy();b=(1+g.nav.pct_change().fillna(nav[0]-1)).groupby(g.date.dt.to_period("M")).prod().iloc[1:-1]-1
        months.append(b.rename("net").rename_axis("month").reset_index().assign(phase=ph,model=model))
        h=w.query('phase==@ph and model==@model and cost=="base"');p=v.xs((ph,"base"),level=("phase","cost"))
        risk.append(dict(scope=scope,model=model,phase=ph,nav=nav[-1],cagr=nav[-1]**(252/(len(g)-1))-1,mdd=(nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1).min(),turnover=h.traded.mean(),fees_bp=h.fee.mean()*1e4,tracking=(p[model]-p.benchmark).std()*np.sqrt(25.2)))
    mon=pd.concat(months).pivot(index=["phase","month"],columns="model",values="net")
    for tbl in [v,mon]:
        tbl["sector_share"]=(tbl.sector_budget-tbl.drift_group+tbl.margin-tbl.stock_weight)/2
        tbl["stock_share"]=(tbl.stock_weight-tbl.drift_group+tbl.margin-tbl.sector_budget)/2
        tbl["none"]=0.
        np.testing.assert_allclose(tbl.sector_share+tbl.stock_share,tbl.margin-tbl.drift_group,atol=1e-12)
    for model,other in [(k,o) for k in ["stock_weight","sector_budget"] for o in ["drift_group","margin",R,E,"benchmark"]]+[("sector_share","none"),("stock_share","none")]:
        p=(v[model]-v[other]).groupby(level=["phase","cost"]).mean().unstack()*1e4
        st=dict(scope=scope,model=model,ref=other,base=p.base.mean(),zero=p.zero.mean(),double=p.double.mean(),positive=p.base.gt(0).sum())
        if other in mon:
            b=(mon[model]-mon[other]).unstack(0).dropna().mean(axis=1)*1e4
            n=len(b);idx=np.random.default_rng(3872).integers(n,size=(12000,(n+2)//3));idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
            lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975]);st.update(monthly=b.mean(),lo=lo,hi=hi,ex3=b.drop(b.nlargest(3).index).mean())
        rows.append(st)
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);pd.DataFrame(risk).to_csv(out/"risk.csv",index=False);pd.concat(periods).to_parquet(out/"windows.parquet",index=False)
print(s[s.ref.isin(["drift_group","none"])].pivot(index="scope",columns="model",values="base").round(2))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,*[PRIVATE/(k+".parquet") for k in ["qfq_close","qfq_open","open","close","daily_members","limits/daily","opening_trade_status_v2","suspensions/daily"]],out/"summary.csv",out/"risk.csv",out/"windows.parquet"]})
