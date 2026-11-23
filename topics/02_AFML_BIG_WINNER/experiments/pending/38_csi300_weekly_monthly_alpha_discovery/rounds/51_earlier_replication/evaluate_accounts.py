from pathlib import Path
import sys
import argparse
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,accounts
from execution import net_account
from core import dump,sha
parser=argparse.ArgumentParser()
parser.add_argument("--suspension",choices=["original","flat","half"],default="original")
mode=parser.parse_args().suspension
rootout=here/"results";out=rootout if mode=="original" else rootout/("sensitivity_"+mode)
out.mkdir(exist_ok=True);accounts.OUT=out;m=accounts.Market()
t=pd.read_parquet(rootout/"targets.parquet")
suspfile=PRIVATE/"suspensions/daily.parquet"
if mode!="original":
    name="SH600816";j=m.symbols.get_loc(name)
    halt=m.days[(m.days>=pd.Timestamp("2020-03-24"))&(m.days<pd.Timestamp("2020-06-01"))]
    logs=pd.read_parquet(suspfile).query('ts_code=="600816.SH" and suspend_type=="S"')
    verified=pd.DatetimeIndex(pd.to_datetime(logs[logs.suspend_timing.isna()|logs.suspend_timing.eq("")].trade_date))
    assert len(halt)==45 and halt.isin(verified).all()
    ix=m.days.get_indexer(halt);last=m.c[ix[0]-1,j]
    assert np.isfinite(last) and not (m.buy[ix,j]|m.sell[ix,j]).any()
    assert np.isfinite(m.o[ix[-1]+1,j]) and np.isnan(m.o[ix,j]).all()
    for mat in m.marks["flat"]:
        assert np.isfinite(mat[ix[:20],j]).all() and np.isnan(mat[ix[20:],j]).all()
        mat[ix[20:],j]=last*(1. if mode=="flat" else .5)
    t=t[t.year==2020]
pricefile=PRIVATE/"market.parquet";index=pd.read_parquet(pricefile).close
windows=[];months=[];accounts_rows=[];orders=[];exposure=[]
for (year,phase),g in t.groupby(["year","phase"]):
    end=int(g.exit_idx.max())
    plans=g.drop_duplicates("signal_date").sort_values("signal_date")
    weights=g.pivot(index=["signal_date","instrument"],columns="model",values="weight").fillna(0)
    exposure.append(((weights.embargo-weights[R]).abs().groupby(level=0).sum()/2).rename("active").reset_index().assign(year=year,phase=phase))
    for name,h in g.groupby("model"):
        for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
            d,o,status=net_account(m,h,end,"flat",bf,sf)
            meta=dict(year=year,phase=phase,model=name,cost=cost)
            d=d.set_index("date")
            accounts_rows.append(dict(**meta,complete=status["valuation_complete"],failure=str(status["failure"]),liquidated=status["terminal_liquidated"],end=d.index[-1],nav=d.nav.iloc[-1],mdd=(d.nav/d.nav.cummax().clip(lower=1)-1).min()))
            # Recover pretrade capital from the previous close and overnight inventory repricing.
            o["units"]=(o.buy-o.sell)/o.price
            u=o.pivot(index="date",columns="instrument",values="units").reindex(index=d.index,columns=m.symbols).fillna(0).cumsum()
            u=u.mask(u.abs()<1e-12,0.)
            ix=m.days.get_indexer(d.index)
            op=pd.DataFrame(m.marks["flat"][0][ix],index=d.index,columns=m.symbols)
            cl=pd.DataFrame(m.marks["flat"][1][ix],index=d.index,columns=m.symbols)
            if status["valuation_complete"]:cl.iloc[-1]=op.iloc[-1]
            total=(cl*u).mask(u==0,0).sum(axis=1,skipna=False)+d.cash
            np.testing.assert_allclose(total,d.nav,atol=1e-10)
            prior=u.shift().fillna(0.);pre=(prior*op).mask(prior==0,0).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
            flow=(o.sell-o.buy-o.fee).groupby(o.date).sum().reindex(d.index,fill_value=0)
            np.testing.assert_allclose(1+flow.cumsum(),d.cash,atol=1e-10)
            returns=[]
            for r in plans.itertuples():
                if r.exit_date>d.index[-1]:continue
                finish=d.nav.iloc[-1] if r.exit_idx==end else pre.at[r.exit_date]
                v=finish/pre.at[r.entry_date]-1
                windows.append(dict(**meta,signal_date=r.signal_date,net=v,price_index=index.at[r.exit_date]/index.at[r.entry_date]-1))
                returns.append(v)
            if status["valuation_complete"]:np.testing.assert_allclose(np.prod(1+np.array(returns)),d.nav.iloc[-1],atol=1e-10)
            if cost=="base":
                orders.append(o.assign(**meta))
                returns=d.nav.pct_change().fillna(d.nav.iloc[0]-1)
                for month,v in returns.groupby(d.index.to_period("M")):
                    if str(plans.entry_date.min().to_period("M"))<str(month)<str(d.index[-1].to_period("M")):
                        months.append(dict(**meta,month=str(month),net=(1+v).prod()-1))
    print("verified",year,phase,flush=True)
w=pd.DataFrame(windows);w.to_csv(out/"windows.csv",index=False)
a=pd.DataFrame(accounts_rows);a.to_csv(out/"accounts.csv",index=False)
pd.concat(orders).to_parquet(out/"orders.parquet",index=False)
u=pd.concat(exposure);u.to_csv(out/"active.csv",index=False)
monthly=pd.DataFrame(months);monthly.to_csv(out/"monthly.csv",index=False)
stats=[]
for year,h in w.groupby("year"):
    v=h.pivot(index=["phase","signal_date","cost"],columns="model",values="net").dropna()
    # Restrict comparisons to identical complete H10 observations across all four arms.
    dif=(v.embargo-v[R]).groupby(level=["phase","cost"]).mean().unstack()*1e4
    mon=monthly[monthly.year==year].pivot(index=["phase","month"],columns="model",values="net")
    series=(mon.embargo-mon[R]).unstack(0).dropna().mean(axis=1)*1e4
    base=v.xs("base",level="cost")
    stats.append(dict(year=year,complete_accounts=a[a.year==year].complete.sum(),total_accounts=(a.year==year).sum(),n=len(base),positive=int(dif.base.gt(0).sum()),
        active_pct=u[u.year==year].groupby("phase").active.mean().mean()*100,base=dif.base.mean(),double=dif.double.mean(),zero=dif.zero.mean(),
        vs_common=(base.embargo-base.common).groupby(level="phase").mean().mean()*1e4,vs_E=(base.embargo-base[E]).groupby(level="phase").mean().mean()*1e4,
        months=len(series),monthly=series.mean(),ex3=series.drop(series.nlargest(3).index).mean()))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [here/"PROTOCOL.md",Path(__file__),rootout/"fit_receipt.json",suspfile,pricefile,out/"summary.csv",out/"windows.csv",out/"accounts.csv",out/"orders.parquet",out/"monthly.csv",out/"active.csv"]})
