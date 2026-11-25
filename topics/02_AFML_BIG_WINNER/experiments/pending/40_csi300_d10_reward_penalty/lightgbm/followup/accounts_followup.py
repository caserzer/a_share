"""Daily open execution and close marks, with per-window gross P&L in start-NAV units."""
from common_inputs import *
from hashlib import sha256
from collections import defaultdict

def industries(dates):
    hist=pd.read_parquet(PRIVATE/'industry.parquet')
    hist['instrument']=hist.ts_code.str[-2:]+hist.ts_code.str[:6]
    out={}
    for day in dates:
        key=pd.Timestamp(day).strftime('%Y%m%d')
        active=hist[hist.in_date.le(key)&(hist.out_date.isna()|hist.out_date.gt(key))][['instrument','l1_name']].drop_duplicates()
        out[day]=active[~active.instrument.duplicated(False)].set_index('instrument').l1_name
    return out

def picks(g,extra=False):
    # Descending score and descending security code reproduce stable argsort's last K.
    g=g.sort_values('instrument',ascending=False).set_index('instrument')
    k=len(g)//10
    r=g.R.sort_values(ascending=False,kind='stable').index
    t=g['T'].sort_values(ascending=False,kind='stable').index
    pool=r[:2*k]; top=r[:k]; second=r[k:2*k]
    b=t[t.isin(pool)][:k]
    out=dict(R=top,T=t[:k],B=b,A=(g.R.rank()+g['T'].rank()).nlargest(k).index)
    m=k//5
    remove=t[t.isin(top)][-m:]
    out["X11"]=top[~top.isin(remove)].append(t[t.isin(second)][:m])
    if not extra:return out
    def ordered(candidates,rank):return rank[rank.isin(candidates)]
    m=k//5
    out.update(C=ordered(t[:2*k],r)[:k],E=g.E.nlargest(k).index,T20=g.T20.nlargest(k).index,U=r)
    for name,c in [('V','vol20'),('J','mom5')]:out[name]=g.loc[pool,c].sort_values(kind='stable').index[:k]
    for i,remove in enumerate([top[-m:],ordered(top,t)[-m:]]):
        for j,add in enumerate([second[:m],ordered(second,t)[:m]]):
            out[f'X{i}{j}']=top[~top.isin(remove)].append(add)
    for model,candidates,target in [('B',pool,b),('T',r,t[:k])]:
        for vol in [False,True]:
            group=g.industry.astype(str)
            if vol:group=group+'|'+g.vol20.rank(pct=True).mul(3).apply(np.ceil).astype(str)
            counts=group.loc[target].value_counts()
            out[model+('IV' if vol else 'I')]=pd.Index([s for cat,n in counts.items() for s in candidates[group.loc[candidates].eq(cat)][:n]])
    common=top[top.isin(b)]
    ds=str(g.signal_date.iloc[0].date())
    for seed in range(1,201):
        lottery=sorted(second,key=lambda s:sha256(f'{ds}|{seed}|{s}'.encode()).digest())
        out[f'P{seed:03}']=common.append(pd.Index(lottery[:k-len(common)]))
    for col in g.columns.intersection(['T69','R69','no_dd','no_amp','no_path','G1','G2','F00','F01','F10','leaf100','l2_5']):
        out[col]=g[col].nlargest(k).index
    return out

def replay(m,actions,plans,h,fee_scale,detail=False):
    op,cl=m.marks['flat']
    u=np.zeros(m.n);due=np.full(m.n,-1);cash=1.
    windows=[];daily=[];positions=[];orders=[]
    entries=sorted(plans);end=entries[-1]+h
    assert np.all(np.diff(entries)==h)
    net_fees=np.zeros(m.n); gross=np.zeros(m.n);weight=np.zeros(m.n);last=np.zeros(m.n)
    def finish(nav):
        net=nav/start-1
        np.testing.assert_allclose(net,(gross-net_fees).sum()/start,atol=1e-9,rtol=0)
        windows.append((e,net,net_fees.sum()/start,turn/start))
        if detail:
            for j in np.union1d(chosen,np.flatnonzero(abs(gross)+net_fees+abs(weight)>1e-14)):
                positions.append((e,m.symbols[j],j in chosen,weight[j],gross[j]/start,net_fees[j]/start))
    for i in range(entries[0],end+1):
        held=u>0
        expired=held&(due<=i)
        trade=i in plans or expired.any() or i==end
        fee=buy=sell=0.
        if trade:
            if not np.isfinite(op[i,held]).all():raise ValueError(('open',m.days[i],m.symbols[held&~np.isfinite(op[i])]))
            price=np.nan_to_num(op[i])
            gross+=u*(price-last);last=price
            pre=cash+u@price
            if i in plans:
                if i!=entries[0]:finish(pre)
                start=pre;e=i;turn=0.;gross=np.zeros(m.n);net_fees=np.zeros(m.n)
                chosen=plans[i]
            sold=expired&m.sell[i];sales=np.where(sold,u*price,0.)
            retained=held&~sold;purchase=np.zeros(m.n)
            bf=.001*fee_scale;sf=.002*fee_scale
            if i in plans:
                allowed=chosen[m.buy[i,chosen]&m.members[i-1,chosen]&~retained[chosen]]
                total=len(allowed)/len(chosen);available=cash+sales.sum()*(1-sf)
                scale=min((available+u[retained]@price[retained])/(1+bf*total),available/(max(total,1e-12)*(1+bf)))
                purchase[allowed]=scale/len(chosen)
            for a,b,listing in actions:
                if i>=listing and sales[a]:sales[b]+=sales[a];sales[a]=0
            delta=purchase-sales
            f=bf*delta.clip(min=0)-sf*delta.clip(max=0)
            fee=f.sum();buy=delta.clip(min=0).sum();sell=-delta.clip(max=0).sum()
            cash+=sell-buy-fee
            if abs(cash)<1e-12:cash=0.
            assert cash>=-1e-10
            net_fees+=f;turn+=buy+sell;u[sold]=0.;due[sold]=-1
            new=purchase>0;u[new]=purchase[new]/price[new];due[new]=i+h
            if detail:
                orders.extend((i,m.symbols[j],delta[j],pre) for j in np.flatnonzero(delta))
            if i in plans:weight=u*price/start
        mark=op[i] if i==end else cl[i]
        if not np.isfinite(mark[u>0]).all():raise ValueError(('mark',m.days[i],m.symbols[(u>0)&~np.isfinite(mark)]))
        nav=cash+u[u>0]@mark[u>0]
        daily.append((i,m.days[i],nav,cash,buy,sell,fee))
    finish(nav)
    np.testing.assert_allclose(np.prod(1+np.array(windows)[:,1]),nav,atol=1e-10)
    return windows,daily,positions,orders
