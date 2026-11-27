"""Signal-close budget tests on the historical CSI300 book."""
from pathlib import Path
import sys
import hashlib
import json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'p2'))
from inputs import market,targets,SEGMENTS,OUT,PRIVATE,pd,np
from book import funded
DEST=HERE/'results'

def slopes(m,s):
    """Rolling pooled within-date least squares. y is centered on eligible labeled peers."""
    i=s.entry_idx.to_numpy()
    j=m.symbols.get_indexer(s.instrument)
    s=s.copy()
    s['y']=m.o[i+10,j]/m.o[i,j]-1
    s['y']=s.y.where(np.isfinite(s.y))
    s=s[s.y.notna()].copy()
    moments=pd.DataFrame(index=np.sort(s.entry_idx.unique()))
    for arm,column in [('hold','R'),('tree','T')]:
        xc=s[column]-s.groupby('entry_idx')[column].transform('mean')
        yc=s.y-s.groupby('entry_idx').y.transform('mean')
        xy=(xc*yc).groupby(s.entry_idx).sum().rolling(252,min_periods=1).sum()
        xx=(xc**2).groupby(s.entry_idx).sum().rolling(252,min_periods=1).sum()
        moments[arm]=xy/xx.replace(0,np.nan)
    # Entry e is set at signal close e-1. An older label is known if its
    # exit open (entry+10) is no later than e-1.
    moments.index+=11
    moments.rename_axis('first_usable_entry_idx').to_csv(DEST/'calibration.csv')
    return moments

def key(date,name):
    return hashlib.sha256(f'4101|{date}|{name}'.encode()).digest()

def run():
    m,actions=market()
    plans,books=targets(m)
    s=pd.read_parquet(OUT/'scores.parquet')
    s=s[s.entry_idx+10<len(m.days)]
    fit=slopes(m,s)
    scores={}
    for e,g in s.groupby('entry_idx'):
        j=m.symbols.get_indexer(g.instrument)
        scores[e]={}
        for a,col in [('hold','R'),('tree','T')]:
            v=np.full(m.n,np.nan);v[j]=g[col];scores[e][a]=v
    days=[];audit=[];orders=[];details=[]
    for scope,begin,finish in SEGMENTS:
        lo,hi=m.days.get_indexer([begin,finish])
        original_holdings={}
        for experiment,arm,gate,control in [
              ('baseline','hold',None,False),('baseline','tree',None,False),
              ('E2','hold',None,False),('E2','hold',None,True),
              *[('E1',a,h,c) for a in ['hold','tree'] for h in [0,.001] for c in [False,True]]]:
            label=f'{experiment}_{arm}'+('' if gate is None else f'_{int(gate*10000)}')+('_mechanical' if control else '')
            # Same-date accepted count from the corresponding measured arm sets
            # the mechanical seat budget. Account-specific fills remain observable.
            counts={r['entry_idx']:r['n'] for r in audit if r['scope']==scope and r['arm']==label.replace('_mechanical','')}
            def policy(i,ph,base,state):
                if experiment=='baseline':
                    if arm=='hold':original_holdings[i]=(state.units[ph]>0).copy()
                    return base
                ids,top,pool,removed,adds,torder=books[i]
                at=state.units[ph]>0
                date=m.days[i-1]
                mark=np.nan_to_num(m.marks['flat'][1][i-1])
                pre=state.cash[ph]+state.units[ph]@mark
                ticket=pre/len(base)
                # Decisions know existing quantities, signal-close prices/status
                # and intended other-sleeve expiries; no opening fills from i.
                other=((state.units>0)&(state.due<=i)&m.sell[i-1])
                other[ph]=False
                other_sales=(state.units*other).sum(axis=0)*mark
                plan=base.copy()
                new=base[~at[base]]
                if experiment=='E2':
                    new=base[~original_holdings[i][base] & ~at[base]]
                    ranked_new=[j for j in reversed(torder) if j in new]
                    available=[j for j in torder if j in pool and not at[j] and not original_holdings[i][j]]
                    n=min(len(ranked_new),len(available),len(base)//5)
                    if control:
                        n=min(n,counts[i])
                        ranked_new=sorted(new,key=lambda j:key(date,m.symbols[j]))
                        available=sorted(available,key=lambda j:key(date,m.symbols[j]))
                    for old,buy in zip(ranked_new[:n],available[:n]):
                        plan[plan==old]=buy
                        details.append((scope,label,i,ph,m.symbols[old],m.symbols[buy],ticket,np.nan,np.nan,True))
                else:
                    sc=scores[i][arm]
                    old=np.flatnonzero(at & np.isfinite(sc) & ~np.isin(np.arange(m.n),base) & m.members[i-1])
                    old=sorted(old,key=lambda j:(sc[j],m.symbols[j]))
                    new=sorted(new,key=lambda j:(sc[j],m.symbols[j]),reverse=True)
                    pairs=list(zip(old,new))
                    slope=fit.at[i,arm] if i in fit.index else np.nan
                    n=0
                    if control:
                        pairs=sorted(pairs,key=lambda p:key(date,m.symbols[p[0]]+m.symbols[p[1]]))
                    for k,(old,buy) in enumerate(pairs):
                        # Compare fees on the original rebalance to the counterfactual
                        # with one old name retained; both legs use signal-close value.
                        oldval=state.units[ph,old]*mark[old]
                        def fee(x):return max(x,0)*.001+max(-x,0)*.002
                        sell_other=-other_sales[old]
                        buy_other=-other_sales[buy]
                        deltafee=fee(sell_other-oldval)+fee(buy_other+ticket)-fee(sell_other+ticket-oldval)-fee(buy_other)
                        expected=ticket*slope*(sc[buy]-sc[old])
                        # On pre-calibration dates the ungated plan is the fallback.
                        accept=(k<counts[i] if control else (not np.isfinite(slope) or expected>=deltafee+ticket*gate))
                        if accept:n+=1
                        else:plan[plan==buy]=old
                        details.append((scope,label,i,ph,m.symbols[old],m.symbols[buy],ticket,expected,deltafee,accept))
                assert len(np.unique(plan))==len(plan)
                audit.append(dict(scope=scope,arm=label,entry_idx=i,n=n,natural_buys=len(new),seat=ticket,
                                  turnover_budget=n*ticket,matched_arm_count=counts.get(i) if control else None))
                return plan
            d,od,_,_=funded(m,actions,plans[arm],lo,hi,arm=label,books=books,policy=policy)
            days.append(d.assign(scope=scope,arm=label))
            orders.append(pd.DataFrame(od,columns='idx phase instrument order fee'.split()).assign(scope=scope,arm=label))
            print(scope,label,flush=True)
    pd.concat(days).to_parquet(DEST/'daily.parquet',index=False)
    pd.DataFrame(audit).to_parquet(DEST/'decisions.parquet',index=False)
    pd.DataFrame(details,columns='scope arm entry_idx sleeve old new planned_ticket expected_gain estimated_fee accepted'.split()).to_parquet(DEST/'pairs.parquet',index=False)
    pd.concat(orders).to_parquet(DEST/'orders.parquet',index=False)
if __name__=='__main__':run()
