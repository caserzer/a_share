from functools import lru_cache
from shared import *

class Experiment:
    def __init__(self):
        self.m,self.actions=market()
        self.open,self.close=self.m.marks['flat']
        p=pd.read_parquet(OUT/'contributions.parquet').sort_values(KEY)
        self.panel=p
        self.groups=list(p.groupby('entry_idx',sort=True))
        self.entries=np.array([e for e,_ in self.groups])
        assert (np.diff(self.entries)==10).all()
        self.ids=[self.m.symbols.get_indexer(g.instrument) for _,g in self.groups]
        assert min(map(min,self.ids))>=0
        self.parts=[g[[f'g{k}' for k in range(6)]].to_numpy() for _,g in self.groups]
        self.y=[g.h10.to_numpy() for _,g in self.groups]

    @lru_cache(maxsize=256)
    def calibration(self,weights):
        # Pooled least squares of known H10 on within-day score percentile.
        # The intercept is common to all equal seats and cancels in selection.
        moment=np.zeros(4); last=0; history=[]; outputs=[]; cum_xx=[]
        for t,(e,g) in enumerate(self.groups):
            while last<t and self.entries[last]+10<=e-1:
                moment+=history[last]; last+=1
            n,sx,sy,sxy=moment
            # Store sum of squares alongside the other moments to allow missing labels.
            xx=0 if last==0 else cum_xx[last-1]
            slope=max(0,(sxy-sx*sy/n)/max(xx-sx*sx/n,1e-12)) if n else 0
            score=self.parts[t][:,:5]@weights+self.parts[t][:,5]
            rank=pd.Series(score).rank(pct=True).to_numpy()
            outputs.append((score,slope*rank,slope,last))
            y=self.y[t]; known=np.isfinite(y); v=rank[known]; y=y[known]
            history.append(np.array([len(v),v.sum(),y.sum(),v@y]))
            cum_xx.append(float(v@v)+(cum_xx[-1] if cum_xx else 0))
        return outputs

    def run(self,first,stop,rule,weights,bf=.001,sf=.002,detail=False,books=None,initial=None,uniform=None,liquidate=True):
        # first and stop address contiguous H10 entries, stop exclusive.
        m=self.m; u=np.zeros(m.n); cash=1.; due=np.full(m.n,-1)
        if initial is not None: u,cash,due=initial[0].copy(),initial[1],initial[2].copy()
        t=first; terminal=self.entries[stop-1]+10
        days=[]; windows=[]; picks=[]; rankings=[]; orders=[]
        opening=1.; fees=traded=0.; objective=0.
        for i in range(self.entries[first],terminal+1):
            signal=t<stop and i==self.entries[t]
            if signal:
                if books is not None: books[t]=(u.copy(),cash,due.copy())
                names=self.ids[t]; e,g=self.groups[t]
                quarter=str(g.signal_date.iloc[0].to_period('Q'))
                w=weights[quarter] if isinstance(weights,dict) else weights
                score,expected,slope,history=self.calibration(w)[t]
                if rule=='pruned': score=g.pruned.to_numpy()
                seats=len(names)//10
                if rule in ['original','pruned']:
                    pick=np.argsort(score,kind='stable')[-seats:]
                else:
                    held=u>0
                    assert np.isfinite(self.close[i-1,held]).all()
                    holdings=u*np.nan_to_num(self.close[i-1])
                    # Make the successor's delivered position visible at the signal close.
                    for a,b,listing in self.actions:
                        if i-1>=listing: holdings[b]+=holdings[a]; holdings[a]=0.
                    seat=(cash+holdings.sum())/seats
                    bonus=.003*np.minimum(holdings[names]/seat,1.)
                    pick=np.lexsort((names,score,expected+bonus))[-seats:]
                chosen=names[pick]
                target=np.zeros(m.n); target[chosen]=1/seats
                if uniform is not None: target=uniform; chosen=np.flatnonzero(target>0)
                if detail:
                    ranks=g[KEY].assign(score=score,h10=self.y[t],selected=np.isin(names,chosen))
                    rankings.append(ranks)
                    picks.append(dict(entry=i,selected=chosen.copy(),signal_date=g.signal_date.iloc[0],slope=slope,calibration_dates=history))
            expired=(u>0)&(due<=i)
            buy=sell=fee=0.
            if (signal or expired.any() or i==terminal) and (i!=terminal or liquidate):
                held=u>0
                if not np.isfinite(self.open[i,held]).all():
                    raise ValueError(('open',m.days[i],m.symbols[held&~np.isfinite(self.open[i])]))
                price=np.nan_to_num(self.open[i]); before=cash+u@price
                if signal and t>first:
                    net=before/opening-1
                    windows.append((self.entries[t-1],net,fees/opening,traded/opening))
                    objective+=np.log1p(net+fees/opening)
                if signal: opening=before;fees=traded=0.
                sold=expired&m.sell[i]; sales=np.where(sold,u*price,0.)
                retained=held&~sold; purchases=np.zeros(m.n)
                if signal:
                    allowed=chosen[m.buy[i,chosen]&m.members[i-1,chosen]&~retained[chosen]]
                    total=target[allowed].sum()
                    available=cash+sales.sum()*(1-sf)
                    scale=min((available+u[retained]@price[retained])/(1+bf*total),available/(max(total,1e-12)*(1+bf)))
                    purchases[allowed]=scale*target[allowed]
                for a,b,listing in self.actions:
                    if i>=listing and sales[a]: sales[b]+=sales[a];sales[a]=0.
                delta=purchases-sales
                buy=delta.clip(min=0).sum(); sell=(-delta).clip(min=0).sum()
                fee=bf*buy+sf*sell;fees+=fee;traded+=buy+sell
                cash+=sell-buy-fee
                if abs(cash)<1e-12: cash=0.
                assert cash>=-1e-10
                u[sold]=0.;due[sold]=-1
                new=purchases>0;u[new]=purchases[new]/price[new];due[new]=i+10
                if detail:
                    for j in np.flatnonzero(delta): orders.append((i,m.symbols[j],delta[j],before))
                if signal:t+=1
            held=u>0; mark=self.open[i] if i==terminal else self.close[i]
            if not np.isfinite(mark[held]).all(): raise ValueError(('valuation',m.days[i],m.symbols[held&~np.isfinite(mark)]))
            nav=cash+u[held]@mark[held]
            if detail:days.append((i,m.days[i],nav,cash,buy,sell,fee))
        net=nav/opening-1;windows.append((self.entries[stop-1],net,fees/opening,traded/opening))
        objective+=np.log1p(net+fees/opening)
        if detail:
            np.testing.assert_allclose(np.prod(1+np.array(windows)[:,1]),nav/(1. if initial is None else opening),atol=1e-10)
            return windows,days,picks,pd.concat(rankings),orders
        return (np.log(nav),objective)

def main():
    ex=Experiment(); dates=ex.m.days[ex.entries-1]; quarters=dates.to_period('Q')
    first=np.flatnonzero(dates.year>=2020)[0]
    unit=(1.,)*5
    learned={arm:{} for arm in ['net','gross']}; trials=[]
    for q in quarters[dates.year>=2021].unique():
        stop=np.searchsorted(ex.m.days[ex.entries+10],q.start_time)
        cache={}
        for arm in learned:
            w=list(unit)
            for k in range(5):
                best=-np.inf
                for value in [1.,.8,1.2]:
                    candidate=w.copy();candidate[k]=value;key=tuple(candidate)
                    if key not in cache:cache[key]=ex.run(first,stop,'cost',key)
                    score=cache[key][int(arm=='gross')]
                    trials.append((str(q),arm,k,value,key,first,stop,dates[first],ex.m.days[ex.entries[stop-1]+10],score))
                    if score>best+1e-12:best=score;chosen=value
                w[k]=chosen
            learned[arm][str(q)]=tuple(w)
        print(q,learned['net'][str(q)],learned['gross'][str(q)],flush=True)
    pd.DataFrame(trials,columns=['quarter','objective','group','candidate','weights','first','stop','first_signal','last_exit','log_growth']).to_parquet(OUT/'search.parquet',index=False)
    (OUT/'weights.json').write_text(json.dumps(learned,indent=2))
    windows=[];daily=[];ranks=[];fills=[];cal=[]
    for name,w in [('original',unit),('pruned',unit),('selection',unit),*learned.items()]:
        for scope,mask in [('primary',(dates.year>=2021)&(ex.m.days[ex.entries+10]<=pd.Timestamp('2025-03-03'))),('later',ex.m.days[ex.entries]>=pd.Timestamp('2025-03-03'))]:
            ix=np.flatnonzero(mask); assert len(ix)==(100 if scope=='primary' else 39)
            for cost,mul in [('base',1),('zero',0),('double',2)]:
                win,d,p,r,o=ex.run(ix[0],ix[-1]+1,name,w,bf=.001*mul,sf=.002*mul,detail=True)
                meta=dict(model=name,scope=scope,cost=cost)
                windows.append(pd.DataFrame(win,columns=['entry_idx','net','fee','turnover']).assign(**meta))
                daily.append(pd.DataFrame(d,columns=['idx','date','nav','cash','buy','sell','fees']).assign(**meta))
                fills.append(pd.DataFrame(o,columns=['idx','instrument','net_amount','pretrade_nav']).assign(**meta))
                ranks.append(r.assign(**meta))
                cal.extend(dict(**meta,signal_date=row['signal_date'],slope=row['slope'],dates=row['calibration_dates']) for row in p)
    for items,path in [(windows,'windows'),(daily,'daily'),(ranks,'rankings'),(fills,'orders')]:
        pd.concat(items,ignore_index=True).to_parquet(OUT/(path+'.parquet'),index=False)
    pd.DataFrame(cal).to_csv(OUT/'calibration.csv',index=False)

if __name__=='__main__': main()
