from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,accounts,PRIVATE
from execution import net_account
from core import dump,sha
out=here/"results";src=here.parent/"51_earlier_replication/results"
files=[out/"targets.parquet",src/"targets.parquet",out/"fit_receipt.json",Path(__file__),here/"PROTOCOL.md",src/"suspension_marks.csv",PRIVATE/"suspensions/daily.parquet"]
t=pd.concat([pd.read_parquet(files[0]),pd.read_parquet(files[1]).query('model in [@R,"embargo"]')])
rows=[];mon=[];stats=[]
for year,mode in [(2019,"original"),(2020,"flat"),(2020,"half")]:
    m=accounts.Market()
    ref=src if year==2019 else src/("sensitivity_"+mode)
    f=ref/"windows.csv";files.append(f)
    old=pd.read_csv(f,parse_dates=["signal_date"]).query('year==@year and model in [@R,"embargo"]')
    if year==2020:
        j=m.symbols.get_loc("SH600816")
        halt=m.days[(m.days>="2020-03-24")&(m.days<"2020-06-01")]
        log=pd.read_parquet(PRIVATE/"suspensions/daily.parquet")
        log=log.query('ts_code=="600816.SH" and suspend_type=="S"')
        log=log[log.suspend_timing.isna()|log.suspend_timing.eq("")]
        assert len(halt)==45 and halt.isin(pd.to_datetime(log.trade_date)).all()
        ix=m.days.get_indexer(halt)
        assert not (m.buy[ix,j]|m.sell[ix,j]).any()
        for mat in m.marks["flat"]:
            assert np.isnan(mat[ix[20:],j]).all()
            mat[ix[20:],j]=m.c[ix[0]-1,j]*(.5 if mode=="half" else 1.)
    for (phase,name),g in t[t.year==year].groupby(["phase","model"]):
        plans=g.drop_duplicates("signal_date").sort_values("signal_date")
        end=g.exit_idx.max()
        for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
            daily,orders,st=net_account(m,g,end,"flat",bf,sf)
            assert st["valuation_complete"]
            d=daily.set_index("date")
            units=orders.assign(units=(orders.buy-orders.sell)/orders.price).pivot(index="date",columns="instrument",values="units").reindex(index=d.index).fillna(0).cumsum()
            units=units.mask(units.abs()<1e-12,0)
            marks=pd.DataFrame(m.marks["flat"][0][np.ix_(m.days.get_indexer(d.index),m.symbols.get_indexer(units.columns))],index=d.index,columns=units.columns)
            prior=units.shift().fillna(0)
            pre=(marks*prior).mask(prior==0,0).sum(axis=1,skipna=False)+d.cash.shift().fillna(1)
            endnav=pre.copy();endnav.iloc[-1]=d.nav.iloc[-1]
            ret=endnav.loc[plans.exit_date].to_numpy()/pre.loc[plans.entry_date].to_numpy()-1
            np.testing.assert_allclose((1+ret).prod(),d.nav.iloc[-1],atol=1e-10)
            meta=dict(year=year,mode=mode,phase=phase,model=name,cost=cost)
            rows.append(pd.DataFrame(dict(signal_date=plans.signal_date.to_numpy(),net=ret,**meta)))
            if cost=="base":
                by=d.nav.pct_change().fillna(d.nav.iloc[0]-1)
                b=(1+by).groupby(d.index.to_period("M")).prod()-1
                mon.append(b.iloc[1:-1].rename("net").reset_index().rename(columns={"date":"month"}).assign(**meta))
    w=pd.concat(rows).query('year==@year and mode==@mode')
    keys=["phase","model","cost","signal_date"]
    pd.testing.assert_series_equal(w[w.model.isin([R,"embargo"])].set_index(keys).net.sort_index(),old.set_index(keys).net.sort_index(),atol=1e-12,rtol=0)
    v=w.pivot(index=["phase","cost","signal_date"],columns="model",values="net")
    b=pd.concat(mon).query('year==@year and mode==@mode').pivot(index=["phase","month"],columns="model",values="net")
    for name in ["shuffle1","shuffle2","shuffle3","embargo"]:
        p=(v[name]-v[R]).groupby(level=["phase","cost"]).mean().unstack()*1e4
        months=(b[name]-b[R]).unstack(0).dropna().mean(axis=1)*1e4
        stats.append(dict(year=year,mode=mode,model=name,base=p.base.mean(),double=p.double.mean(),zero=p.zero.mean(),positive=(p.base>0).sum(),n_months=len(months),monthly=months.mean(),ex3=months.drop(months.nlargest(3).index).mean()))
    print(year,mode,flush=True)
for data,name in [(pd.concat(rows),"windows"),(pd.concat(mon),"months"),(pd.DataFrame(stats),"summary")]:
    f=out/("early_"+name+".csv");data.to_csv(f,index=False);files.append(f)
dump(out/"early_receipt.json",{str(f):sha(f) for f in files})
