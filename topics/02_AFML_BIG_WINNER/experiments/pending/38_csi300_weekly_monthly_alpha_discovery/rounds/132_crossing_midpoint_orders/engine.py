import numpy as np
import pandas as pd
from accounts import buy_amounts
def replay(m,actions,g,bf,sf,switches):
    plans={e:h for e,h in g.groupby("entry_idx")};end=int(g.exit_idx.max())
    u=np.zeros(m.n);due=np.full(m.n,-1);cash=1.;counts=[];daily=[];opening={};fail=None
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
            u[sold]=0;due[sold]=-1;new=purchases>0;u[new]=purchases[new]/price[new];
            if new.any():due[new]=int(plans[i].exit_idx.iloc[0])
            np.testing.assert_allclose(cash+u@price,opening[i]-fees,atol=1e-10)
        if i in switches:
            old,new=switches[i]
            ok=(u[old]>0)&(due[old]==i+5)&(u[new]==0)&m.sell[i,old]&m.buy[i,new]&m.members[i-1,new]
            old,new=old[ok],new[ok]
            if len(old):
                sold_value=u[old]*op[i,old]
                bought_value=sold_value*(1-sf)/(1+bf)
                u[old]=0;due[old]=-1
                u[new]=bought_value/op[i,new];due[new]=i+5
                sell+=sold_value.sum();buy+=bought_value.sum()
                fees+=sold_value.sum()*sf+bought_value.sum()*bf
                np.testing.assert_allclose(sold_value.sum()*(1-sf),bought_value.sum()*(1+bf),atol=1e-12)
            counts.append((i,len(ok),len(old)))
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
    return pd.DataFrame(rows),d,fail,counts
