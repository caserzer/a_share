"""Replay the EP37 expiry and netting contract, recording pretrade NAV at each decision."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import accounts,PRIVATE,split
from core import sha,dump
from accounts import buy_amounts
out=here/"results";accounts.OUT=out
def setup(mode):
    m=accounts.Market();op,cl=m.marks["flat"];actions=[]
    rawo=pd.read_parquet(PRIVATE/"open.parquet");rawc=pd.read_parquet(PRIVATE/"close.parquet")
    for old,new,start,listing,ratio in [("SH600837","SH601211","2025-03-04","2025-03-17",.62),("SH601989","SH600150","2025-09-05","2025-09-16",.1339)]:
        a,b=m.symbols.get_indexer([old,new]);i,j=m.days.get_indexer([start,listing])
        last=rawc[old].iloc[:i].last_valid_index()
        factor=m.c[m.days.get_loc(last),a]/rawc.at[last,old]
        conversion=ratio*factor*rawo.at[m.days[j],new]/m.o[j,b]
        assert not (m.buy[i:,a]|m.sell[i:,a]).any()
        for mat,raw in [(op,rawo),(cl,rawc)]:
            mat[i:j,a]=raw[new].iloc[i:j].to_numpy()*ratio*factor
            assert np.isfinite(mat[i:j,a]).all()
            mat[j:,a]=mat[j:,b]*conversion
        m.sell[j:,a]=m.sell[j:,b];actions.append((a,b,j))
    j=m.symbols.get_loc("SH600816")
    halt=m.days[(m.days>="2020-03-24")&(m.days<"2020-06-01")]
    log=pd.read_parquet(PRIVATE/"suspensions/daily.parquet").query('ts_code=="600816.SH" and suspend_type=="S"')
    log=log[log.suspend_timing.isna()|log.suspend_timing.eq("")]
    assert len(halt)==45 and halt.isin(pd.to_datetime(log.trade_date)).all()
    ix=m.days.get_indexer(halt)
    assert not (m.buy[ix,j]|m.sell[ix,j]).any()
    for mat in [op,cl]:
        assert np.isnan(mat[ix[20:],j]).all()
        mat[ix[20:],j]=m.c[ix[0]-1,j]*(.5 if mode=="half" else 1.)
    return m,actions
def replay(m,actions,g,bf,sf):
    plans={e:h for e,h in g.groupby("entry_idx")};end=int(g.exit_idx.max())
    u=np.zeros(m.n);due=np.full(m.n,-1);cash=1.;daily=[];opening={};fail=None
    op,cl=m.marks["flat"]
    for i in range(min(plans),end+1):
        held=u>0;expired=held&(due<=i)
        fees=buy=sell=0.
        if expired.any() or i in plans or i==end:
            bad=held&~np.isfinite(op[i])
            if bad.any():
                fail=(str(m.days[i].date()),"open",",".join(m.symbols[bad]));break
            price=np.nan_to_num(op[i]);opening[i]=cash+u@price
            sold=expired&m.sell[i];sales=np.where(sold,u*price,0.)
            retained=held&~sold;purchases=np.zeros(m.n)
            if i in plans:
                h=plans[i];w=np.zeros(m.n);w[m.symbols.get_indexer(h.instrument)]=h.weight
                purchases=buy_amounts(w*(m.buy[i]&m.members[i-1]&~retained),cash+sales.sum()*(1-sf),u[retained]@price[retained],bf)
            # The successor is the traded security; combine orders before charging fees.
            for a,b,listing in actions:
                if i>=listing and sales[a]:
                    sales[b]+=sales[a];sales[a]=0.
            diff=purchases-sales;buy=diff.clip(min=0).sum();sell=(-diff).clip(min=0).sum()
            fees=buy*bf+sell*sf;cash+=sell-buy-fees
            if abs(cash)<1e-12:cash=0.
            assert cash>=-1e-10
            u[sold]=0;due[sold]=-1;new=purchases>0;u[new]=purchases[new]/price[new];due[new]=i+10
            np.testing.assert_allclose(cash+u@price,opening[i]-fees,atol=1e-10)
        mark=op[i] if i==end else cl[i];held=u>0;bad=held&~np.isfinite(mark)
        if bad.any():
            fail=(str(m.days[i].date()),"close",",".join(m.symbols[bad]));break
        daily.append((i,m.days[i],cash+u[held]@mark[held],cash,fees,buy,sell))
    d=pd.DataFrame(daily,columns=["idx","date","nav","cash","fee","buy","sell"])
    rows=[]
    for e,h in plans.items():
        x=int(h.exit_idx.iloc[0])
        if x>d.idx.iloc[-1] or x not in opening:continue
        finish=d.nav.iloc[-1] if x==end else opening[x]
        a=d[d.idx.between(e,x if x==end else x-1)]
        rows.append(dict(signal_date=h.signal_date.iloc[0],net=finish/opening[e]-1,fee=a.fee.sum()/opening[e],traded=(a.buy+a.sell).sum()/opening[e]))
    if fail is None:np.testing.assert_allclose(np.prod([1+v["net"] for v in rows]),d.nav.iloc[-1],atol=1e-10)
    return pd.DataFrame(rows),d,fail
def run_scope(scope,out):
    accounts.OUT=out
    mode="half" if scope=="2020_half" else "flat"
    m,actions=setup(mode);t=pd.read_parquet(out/"targets.parquet")
    t=t[t.year.eq(2019 if scope=="2019" else 2020)] if scope[:1]=="2" else t[(t.year>=2021)&(t.entry_date.ge(split)==(scope=="later"))]
    rows=[];daily=[];status=[]
    for (ph,name),g in t.groupby(["phase","model"]):
        for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
            w,d,fail=replay(m,actions,g,bf,sf);meta=dict(phase=ph,model=name,cost=cost,scope=scope)
            rows.append(w.assign(**meta))
            if cost=="base":daily.append(d.assign(**meta))
            status.append(dict(**meta,failure=fail,end=d.date.iloc[-1],nav=d.nav.iloc[-1],windows=len(w)))
    for data,name in [(pd.concat(rows),"windows"),(pd.concat(daily),"daily"),(pd.DataFrame(status),"accounts")]:
        data.to_parquet(out/(scope+"_"+name+".parquet"),index=False) if name!="accounts" else data.to_csv(out/(scope+"_accounts.csv"),index=False)
    print(scope,pd.DataFrame(status).failure.value_counts(dropna=False).to_string())

if __name__=="__main__":
    run_scope(sys.argv[1],out)
