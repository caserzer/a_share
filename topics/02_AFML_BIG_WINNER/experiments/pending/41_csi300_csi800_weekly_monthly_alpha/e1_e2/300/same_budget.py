"""Equal-ticket single-window mechanical controls on the identical opening state."""
from run import *
from runpy import run_path
trial=run_path(str(HERE.parents[1]/'p2/run.py'))['trial']

def main():
    m,actions=market();base,books=targets(m)
    pairs=pd.read_parquet(DEST/'pairs.parquet')
    daily=pd.read_parquet(DEST/'daily.parquet')
    rows=[]
    for scope,begin,enddate in SEGMENTS:
        lo,hi=m.days.get_indexer([begin,enddate])
        _,_,_,hold_states=funded(m,actions,base['hold'],lo,hi,snapshots=True)
        for arm,g in pairs[(pairs.scope==scope)&~pairs.arm.str.endswith('mechanical')].groupby('arm'):
            original=arm.split('_')[1]
            e2=arm.startswith('E2')
            grouped=dict(list(g.groupby('entry_idx')))
            plan={e:v.copy() for e,v in base[original].items()}
            for e,f in grouped.items():
                for r in f.itertuples():
                    old,new=m.symbols.get_indexer([r.old,r.new])
                    if e2:plan[e][plan[e]==old]=new
                    elif not r.accepted:plan[e][plan[e]==new]=old
            d,_,_,states=funded(m,actions,plan,lo,hi,snapshots=True)
            actual=daily[(daily.scope==scope)&(daily.arm==arm)]
            np.testing.assert_allclose(d.nav,actual.nav,rtol=0,atol=1e-11)
            for e in range(lo,hi-9,10):
                snapshot=states[e];date=m.days[e-1]
                planned=base[original][e].copy()
                mechanical=planned.copy()
                f=grouped.get(e)
                n=int(f.accepted.sum()) if f is not None else 0
                if e2:
                    hold=hold_states[e].units[0]>0
                    own=snapshot.units[0]>0
                    ids,r,pool,_,_,_=books[e]
                    cancel=sorted(planned[~hold[planned]&~own[planned]],key=lambda j:key(date,m.symbols[j]))
                    buy=sorted(pool[~hold[pool]&~own[pool]],key=lambda j:key(date,m.symbols[j]))
                    assert n<=min(len(cancel),len(buy))
                    for a,b in zip(cancel[:n],buy[:n]):mechanical[mechanical==a]=b
                elif f is not None:
                    ordered=sorted(f.itertuples(),key=lambda s:key(date,s.old+s.new))
                    for v in ordered[n:]:
                        a,b=m.symbols.get_indexer([v.old,v.new]);mechanical[mechanical==b]=a
                pre=snapshot.cash[0]+snapshot.units[0]@np.nan_to_num(m.marks['flat'][0][e])
                ticket=pre*(1-.002)/1.001/len(planned)
                for rule,target in [('measured',plan[e]),('mechanical',mechanical)]:
                    result,_=trial(m,actions,snapshot,e,lo,hi,plan,target,ticket)
                    rows.append(dict(scope=scope,arm=arm,e=e,rule=rule,replaced=n,
                                  fixed_ticket=ticket,named_budget=n*ticket,**result))
    z=pd.DataFrame(rows);z.to_parquet(DEST/'same_budget.parquet',index=False)
    t=z.pivot(index=['scope','arm','e'],columns='rule',values=['gross','fee','net','named_budget'])
    np.testing.assert_equal(t.named_budget.measured.values,t.named_budget.mechanical.values)
    a=pd.DataFrame({c:(t[c].measured-t[c].mechanical)*1e4 for c in ['gross','fee','net']})
    a.groupby(['scope','arm']).mean().to_csv(DEST/'same_budget_summary.csv')
if __name__=='__main__':main()
