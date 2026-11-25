from inputs import *
from book import simulate,MissingMark
import account
from collections import defaultdict

def select(m):
    scores=pd.read_parquet(OUT800/'scores.parquet')
    small=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx']).groupby('entry_idx').size()//10
    plans=defaultdict(dict);targets=[];coverage=[]
    for e,g in scores.groupby('entry_idx'):
        ids=m.symbols.get_indexer(g.instrument)
        assert min(ids)>=0 and m.members[e-1,ids].all()
        for mode in ['transfer','refit']:
            rr=ids[np.lexsort((ids,g[mode+'_R']))[::-1]]
            tt=ids[np.lexsort((ids,g[mode+'_T']))[::-1]]
            for size,k,n in [('D10',len(g)//10,len(g)//10//5),('same300',small[e],small[e]//5),('D10_fixed5',len(g)//10,5)]:
                top=rr[:k];second=rr[k:2*k]
                remove=tt[np.isin(tt,top)][-n:];add=tt[np.isin(tt,second)][:n]
                swap=np.r_[top[~np.isin(top,remove)],add]
                assert len(np.unique(swap))==k and len(np.setdiff1d(swap,top))==n
                for arm,pick in [('R',top),('swap',swap)]:
                    plans[(size,mode,arm)][e]=pick
                coverage.append((e,m.days[e-1],mode,size,len(g),k,n))
                targets.append(pd.DataFrame(dict(entry_idx=e,mode=mode,size=size,instrument=m.symbols[np.r_[top,add]],ridge_target=np.r_[np.ones(k,bool),np.zeros(n,bool)],swap_target=np.isin(np.r_[top,add],swap))))
    pd.concat(targets).to_parquet(OUT800/'targets.parquet',index=False)
    pd.DataFrame(coverage,columns='entry_idx signal_date mode size eligible seats swaps'.split()).to_csv(OUT800/'coverage.csv',index=False)
    return plans
def main():
    account.PRIVATE=LOCAL;ledger.accounts.PRIVATE=LOCAL;ledger.accounts.OUT=OUT800
    m,actions=ledger.setup('flat')
    assert m.symbols.is_monotonic_increasing
    m.members=membership(m.days,m.symbols).to_numpy()
    plans=select(m)
    rows=[];errors=[]
    for scope,begin,stop in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
        i,j=m.days.get_indexer([begin,stop])
        assert all(set(range(i,j-9))<=set(plan) for plan in plans.values())
        for size in ['D10','same300','D10_fixed5']:
            arms={k:v for k,v in plans.items() if k[0]==size}
            start=i;seg=0
            while start+10<=j:
                books={};gaps=[]
                for (_,mode,a),plan in arms.items():
                    try:book=simulate(m,actions,plan,start,j,True)
                    except MissingMark as gap:
                        book=gap.prefix;gaps.append(gap.day)
                        errors.append(dict(scope=scope,size=size,segment=seg,mode=mode,arm=a,date=m.days[gap.day],side=gap.side,symbols=','.join(gap.names)))
                    if seg==0:
                        rows.append(book.assign(scope=scope,size=size,mode=mode,arm=a,path='original',segment=0))
                    books[mode,a]=book
                cut=min(gaps) if gaps else j+1
                for (mode,a),b in books.items():
                    rows.append(b[b.date<m.days[cut] if cut<=j else np.ones(len(b),bool)].assign(scope=scope,size=size,mode=mode,arm=a,path='common',segment=seg))
                start=cut+1;seg+=1
    results=pd.concat(rows,ignore_index=True)
    results.to_parquet(OUT800/'strict_daily.parquet',index=False)
    pd.DataFrame(errors,columns='scope size segment mode arm date side symbols'.split()).to_csv(OUT800/'gaps.csv',index=False)
    # Matched annual sensitivity to the value of unpriced held lots. Execution gates stay frozen.
    # An uncertified mark affects NAV and the blocked lot, never grants a sale.
    raw_op,raw_cl=m.marks['flat']
    prev=pd.DataFrame(raw_cl).ffill().shift().to_numpy()
    stress=[]
    for proxy,fraction in [('zero',0),('last',1)]:
        m.marks['flat']=(np.where(np.isfinite(raw_op),raw_op,prev*fraction),np.where(np.isfinite(raw_cl),raw_cl,prev*fraction))
        for (size,mode,a),plan in plans.items():
            for scope,start,end in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
                i,j=m.days.get_indexer([start,end])
                b=simulate(m,actions,plan,i,j,True)
                check=results.query('scope==@scope and mode==@mode and size==@size and arm==@a and path=="original"')
                z=b.merge(check,on='date')
                np.testing.assert_allclose(z.nav_x,z.nav_y,rtol=0,atol=1e-10)
                stress.append(b.assign(scope=scope,size=size,mode=mode,arm=a,proxy=proxy))
    pd.concat(stress).to_parquet(OUT800/'sensitivity_daily.parquet',index=False)
if __name__=='__main__':main()
