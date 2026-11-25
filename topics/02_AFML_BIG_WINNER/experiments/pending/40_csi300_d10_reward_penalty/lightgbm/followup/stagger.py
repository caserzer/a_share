"""Unit capital, ten sleeves. Internally crossed buys and sells pay no fee."""
from accounts_followup import *

def simulate(m,actions,plans,start,end,netting,attribution=None):
    u=np.zeros((10,m.n)); due=np.full_like(u,-1,dtype=int);cash=np.full(10,.1)
    op,cl=m.marks['flat'];rows=[]
    previous_mark=np.zeros(m.n);previous_nav=1.
    for i in range(start,end+1):
        old=u.sum(axis=0)
        # Each decision has one phase. All sleeves can sell overdue blocked holdings.
        orders=np.zeros_like(u)
        for phase in range(10):
            expired=(u[phase]>0)&(due[phase]<=i)
            if not expired.any() and (i-start)%10!=phase:continue
            chosen=plans.get(i) if (i-start)%10==phase and i+10<=end else None
            if chosen is None and not expired.any():continue
            held=u[phase]>0;assert np.isfinite(op[i,held]).all();price=np.nan_to_num(op[i])
            sold=expired&m.sell[i];retained=held&~sold
            sales=np.where(sold,u[phase]*price,0.);buy=np.zeros(m.n)
            if chosen is not None:
                allowed=chosen[m.buy[i,chosen]&m.members[i-1,chosen]&~retained[chosen]]
                total=len(allowed)/len(chosen);avail=cash[phase]+sales.sum()*.998
                scale=min((avail+u[phase,retained]@price[retained])/(1+.001*total),avail/(max(total,1e-12)*1.001))
                buy[allowed]=scale/len(chosen)
            for a,b,listing in actions:
                if i>=listing:sales[b]+=sales[a];sales[a]=0
            orders[phase]=buy-sales
            u[phase,sold]=0.;due[phase,sold]=-1
            new=buy>0;u[phase,new]=buy[new]/price[new];due[phase,new]=i+10
        buys=orders.clip(min=0);sells=(-orders).clip(min=0)
        bs=buys.sum(axis=0);ss=sells.sum(axis=0)
        crossed=np.minimum(bs,ss) if netting else np.zeros(m.n)
        fee=.001*(buys*(1-crossed/np.maximum(bs,1e-30)))+.002*(sells*(1-crossed/np.maximum(ss,1e-30)))
        cash+=-orders.sum(axis=1)-fee.sum(axis=1)
        assert cash.min()>-1e-10
        mark=op[i] if i==end else cl[i];assert np.isfinite(mark[u.sum(axis=0)>0]).all()
        nav=cash.sum()+u.sum(axis=0)@np.nan_to_num(mark)
        if attribution is not None:
            units=u.sum(axis=0)
            price=np.nan_to_num(op[i]);endprice=np.nan_to_num(mark)
            gross=old*(endprice-previous_mark)+(units-old)*(endprice-price)
            fees=fee.sum(axis=0)
            np.testing.assert_allclose(gross.sum()-fees.sum(),nav-previous_nav,atol=1e-10,rtol=0)
            ids=np.flatnonzero(abs(gross)+fees>0)
            attribution.append(pd.DataFrame(dict(date=m.days[i],instrument=m.symbols[ids],gross=gross[ids],fee=fees[ids],opening=previous_nav)))
            previous_mark=endprice;previous_nav=nav
        rows.append((m.days[i],nav,cash.sum(),fee.sum(),crossed.sum()))
    return pd.DataFrame(rows,columns='date nav cash fee crossed'.split())

def main():
    ledger.accounts.OUT=DEST
    m,actions=ledger.setup('flat')
    scores=pd.read_parquet(DEST/'daily_scores.parquet')
    arms=['R','T','B','X11','A'];plans={a:{} for a in arms}
    for e,g in scores.groupby('entry_idx'):
        target=picks(g)
        for a in arms:plans[a][e]=m.symbols.get_indexer(target[a])
    rows=[]
    for scope,start,end in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
        for a in arms:
            for netting in [False,True]:
                detail=[] if a=="R" and netting else None
                frame=simulate(m,actions,plans[a],m.days.get_loc(start),m.days.get_loc(end),netting,detail)
                if detail:pd.concat(detail).to_parquet(DEST/(scope+"_R_funded_pnl.parquet"),index=False)
                rows.append(frame.assign(scope=scope,arm=a,netting=netting))
    pd.concat(rows).to_parquet(DEST/'stagger.parquet',index=False)
if __name__=='__main__':main()
