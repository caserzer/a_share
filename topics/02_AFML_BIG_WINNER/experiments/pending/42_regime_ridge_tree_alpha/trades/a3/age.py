"""Trace each actual sleeve's share count through rebalancing and index membership changes."""
from pathlib import Path
import sys,tempfile
import pandas as pd, numpy as np
HERE=Path(__file__).resolve().parent; OLD=next(HERE.parents[2].glob('41_*'))
sys.path.insert(0,str(OLD/'p2'))
from inputs import targets,ledger,SEGMENTS,PRIVATE
from book import State,step

def main():
    with tempfile.TemporaryDirectory() as temp:
        ledger.accounts.OUT=Path(temp);m,actions=ledger.setup('flat')
    plans,books=targets(m); member=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex(index=m.days,columns=m.symbols)
    # Effect-date leave events require membership yesterday and nonmembership today.
    exited=member.shift(fill_value=False).to_numpy() & ~member.to_numpy()
    future=np.zeros((len(m.days),m.n),int)
    for e in range(len(m.days)):
        future[e]=exited[e:min(e+20,len(m.days))].any(axis=0)
    rows=[];events=[];pnl=[];checks=[]
    positions=pd.read_parquet(OLD/'p2/results/next_rebalance.parquet')
    sc=pd.read_parquet(OLD/'p2/results/scores.parquet',columns=['entry_idx','instrument']);eligible={e:set(z.instrument) for e,z in sc.groupby('entry_idx')}
    for scope,beg,end in SEGMENTS:
        lo,hi=m.days.get_indexer([beg,end])
        exit_scope=future.copy()
        for b in range(max(lo,hi-19),hi+1):exit_scope[b]=exited[b:hi+1].any(axis=0)
        next_status={}
        masks={e:np.isin(m.symbols,list(v)) for e,v in eligible.items() if lo<=e<=hi}
        for e in range(lo,hi-9):
            next_e=e+10
            next_status[e]=np.where(~member.iloc[next_e-1].to_numpy(),'index_exit',np.where(masks[next_e],'eligible','other_ineligible')) if next_e+10<=hi else np.full(m.n,'censored')
        for arm in ('tree','rank'):
            state=State.empty(m.n); previous=np.zeros(m.n);lastnav=1
            # Each positive holding is a list of (entry, uninterrupted rebalance count, units).
            owners=[{} for _ in range(10)]
            gross={};fees={}; init=lo
            for i in range(lo,hi+1):
                ph=(i-lo)%10; price=np.nan_to_num(m.marks['flat'][0][i])
                mark=np.nan_to_num(m.marks['flat'][0 if i==hi else 1][i])
                date=m.days[i]; month=date.strftime('%Y-%m')
                before=state.units.copy()
                pre=[{j:list(v) for j,v in sleeve.items()} for sleeve in owners]
                target=plans[arm][i] if i+10<=hi else None
                row,msg=step(m,actions,state,lo,hi,i,target,1,True)
                signed,paid,buy,_,_=msg
                ages_total=np.zeros((3,4))
                def account(legs,j,amt,kind):
                    total=sum(u for _,_,u in legs)
                    if total<=0:return
                    for born,period,u in legs:
                        age=min(period,3)
                        active='candidate' if j in books[born][4] and arm=='tree' else ('candidate' if j in (books[born][2][:len(books[born][4])] if arm=='rank' else ()) else 'core')
                        with20=born+19<=hi
                        reason='index_exit_in_20' if exit_scope[born,j] else ('no_exit_in_20' if with20 else 'right_censored')
                        key=(scope,arm,month,age,active,reason,str(next_status[born][j]),m.symbols[j])
                        field=[gross,fees][kind] if kind<2 else None
                        if field is not None:field[key]=field.get(key,0.)+amt*u/total
                        ages_total[age-1,kind]+=amt*u/total
                for p in range(10):
                    for j,leg in pre[p].items():
                        account(leg,j,before[p,j]*(price[j]-previous[j]),0)
                        account(leg,j,before[p,j]*price[j],2)
                        if state.units[p,j]<=0:owners[p].pop(j,None)
                    for j in np.flatnonzero(state.units[p]):
                        current=state.units[p,j];old=before[p,j];legs=pre[p].get(j,[])
                        factor=min(1.,current/old) if old>0 else 0.
                        # An unchanged blocked lot ages through the next same-sleeve decision as well.
                        newlegs=[(b,a+int(p==ph and target is not None),u*factor) for b,a,u in legs if u*factor>0]
                        if current>old:newlegs.append((i,1,current-old))
                        if not newlegs:raise ValueError(('unassigned units',scope,i,p,j))
                        owners[p][j]=newlegs
                        account(newlegs,j,current*(mark[j]-price[j]),0)
                        account(newlegs,j,current*mark[j],3)
                    for j in np.flatnonzero(paid[p]):
                        source=owners[p].get(j,[]) if signed[p,j]>0 else pre[p].get(j,[])
                        src=j
                        if not source:
                            for old,new,listing in actions:
                                if j==new and i>=listing and old in pre[p]:
                                    source=pre[p][old];src=old;break
                        if not source:raise ValueError(('unallocated fee',i,j,p))
                        account(source,src,paid[p,j],1)
                err=row['nav']-lastnav-ages_total[:,0].sum()+ages_total[:,1].sum()
                assert abs(err)<1e-10,(i,err)
                assert abs(ages_total[:,1].sum()-row['fee'])<1e-12
                rows.extend((scope,arm,date,k+1,*x,row['nav'],err) for k,x in enumerate(ages_total))
                previous=mark;lastnav=row['nav']
                if target is not None:
                    z=books[i];add=z[4] if arm=='tree' else z[2][:len(z[4])]
                    for j in add:
                        nextdate=i+10
                        valid=nextdate+10<=hi
                        ismember=bool(member.iloc[nextdate-1,j]) if valid else None
                        el=(m.symbols[j] in eligible[nextdate]) if valid else None
                        ev=np.flatnonzero(exited[i:min(i+20,hi+1),j])
                        exit_in_20=int(ev[0]) if len(ev) else (-1 if i+19<=hi else -2)
                        events.append((scope,arm,i,m.days[i-1],m.symbols[j],ismember,el,exit_in_20,buy[j],signed[ph,j],price[j],state.units[ph,j]))
            for key in set(gross)|set(fees):pnl.append((*key,gross.get(key,0),fees.get(key,0)))
            checks.append((scope,arm,lastnav))
    age=pd.DataFrame(rows,columns='scope arm date age gross fee pre_stock post_stock nav parity'.split())
    age.to_parquet(HERE/'age_daily.parquet',index=False)
    e=pd.DataFrame(events,columns='scope arm entry_idx signal_date instrument next_member next_eligible exit_day_0_to_19 bought net_order price units_after'.split())
    e.to_parquet(HERE/'qualification.parquet',index=False)
    pd.DataFrame(pnl,columns='scope arm month age role future_member next_status instrument gross fee'.split()).to_parquet(HERE/'age_roles.parquet',index=False)
    known=e[e.next_member.notna()].copy(); known['left_index']=~known.next_member.astype(bool); known['ineligible']=~known.next_eligible.astype(bool)
    x=known.groupby(['scope','arm']).agg(seats=('left_index','size'),distinct_stocks=('instrument','nunique'),index_exits=('left_index','sum'),ineligible=('ineligible','sum'),invested=('bought','sum'))
    x['exit20_observed']=known[known.exit_day_0_to_19.ge(0)].groupby(['scope','arm']).size()
    x['index_exit_capital']=known[known.left_index].groupby(['scope','arm']).bought.sum()
    x['ineligible_capital']=known[known.ineligible].groupby(['scope','arm']).bought.sum()
    x.to_csv(HERE/'qualification_summary.csv')
    print(x,flush=True)
if __name__=='__main__':main()
