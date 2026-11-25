"""EP40 staggered book with the certified prefix returned on a missing held mark."""
from inputs import *

class MissingMark(Exception):
    def __init__(self, day, side, names, prefix):
        self.day,self.side,self.names,self.prefix=day,side,names,prefix
        super().__init__(day,side,list(names))

def simulate(m,actions,plans,start,end,netting,attribution=None):
    u=np.zeros((10,m.n)); due=np.full_like(u,-1,dtype=int);cash=np.full(10,.1)
    op,cl=m.marks['flat'];rows=[]
    previous_mark=np.zeros(m.n);previous_nav=1.
    columns="date nav cash fee crossed".split()
    for i in range(start,end+1):
        old=u.sum(axis=0)
        # Each decision has one phase. All sleeves can sell overdue blocked holdings.
        orders=np.zeros_like(u)
        for phase in range(10):
            expired=(u[phase]>0)&(due[phase]<=i)
            if not expired.any() and (i-start)%10!=phase:continue
            chosen=plans.get(i) if (i-start)%10==phase and i+10<=end else None
            if chosen is None and not expired.any():continue
            held=u[phase]>0
            missing=held&~np.isfinite(op[i])
            if missing.any():
                raise MissingMark(i,'open',m.symbols[missing],pd.DataFrame(rows,columns=columns))
            price=np.nan_to_num(op[i])
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
        mark=op[i] if i==end else cl[i]
        missing=(u.sum(axis=0)>0)&~np.isfinite(mark)
        if missing.any():
            raise MissingMark(i,'terminal_open' if i==end else 'close',m.symbols[missing],pd.DataFrame(rows,columns=columns))
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
