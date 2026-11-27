"""Maximum-cardinality matched random buys, 200 stable date/security-bound lotteries."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from scipy.optimize import linear_sum_assignment
from inputs import *
from book import funded

def edges(m,books):
    raw=pd.read_parquet(PRIVATE/'close.parquet')
    adv=pd.read_parquet(PRIVATE/'money.parquet').rolling(20,min_periods=20).mean()
    hist=industries([m.days[e-1] for e in books])
    folder=PRIVATE/'style_caps_20261117'
    files=sorted(folder.glob('[0-9]'*8+'.json'))
    dates=pd.DatetimeIndex([pd.Timestamp(p.stem) for p in files])
    snapshots={}
    rows=[]
    graphs={}
    for e,(ids,r,pool,removed,adds,_) in books.items():
        date=m.days[e-1]
        q=dates.searchsorted(date)-1
        assert q>=0
        source=dates[q]
        age=e-1-m.days.get_loc(source)
        if source not in snapshots:
            path=files[q]
            rec=json.loads((folder/(path.stem+'.receipt.json')).read_text())
            assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
            data=json.loads(path.read_text())['data']
            g=pd.DataFrame(data['items'],columns=data['fields'])
            assert not g.ts_code.duplicated().any() and g.trade_date.astype(str).eq(path.stem).all()
            g.index=g.ts_code.str[-2:]+g.ts_code.str[:6]
            usable=g.free_share.gt(0)&g.free_share.le(g.float_share*1.0001)&g.float_share.le(g.total_share*1.0001)
            snapshots[source]=g.free_share.where(usable)
        names=m.symbols[ids]
        cap=snapshots[source].reindex(names)*raw.loc[date,names]
        if age>7:cap[:]=np.nan
        cap=cap.rank(pct=True)
        vol=adv.loc[date,names].where(lambda v:v>0).rank(pct=True)
        sector=hist[date].reindex(names).fillna('未知')
        a,b=m.symbols[adds],m.symbols[pool]
        dc=np.abs(cap[a].to_numpy()[:,None]-cap[b].to_numpy())
        dv=np.abs(vol[a].to_numpy()[:,None]-vol[b].to_numpy())
        ok=(dc<=.1)&(dv<=.1)&(sector[a].to_numpy()[:,None]==sector[b].to_numpy())
        # Self is available for every supported row, guaranteeing maximum cardinality
        # even when multiple rows compete for one alternative.
        assert (ok.any(axis=1)==(ok & (adds[:,None]==pool)).any(axis=1)).all()
        edges_=np.argwhere(ok)
        graphs[e]=(pool,adds,edges_,str(date.date()))
        for ii,j in enumerate(adds):
            rows.append(dict(entry_idx=e,date=date,instrument=m.symbols[j],source_date=source,
                       share_age=age,industry=sector[m.symbols[j]],alternatives=int(ok[ii].sum()),
                       k=len(r),share_rank=cap[m.symbols[j]],adv_rank=vol[m.symbols[j]]))
    pd.DataFrame(rows).to_parquet(OUT/'match_support.parquet',index=False)
    return graphs

def worker(seed):
    rows=[];support=[]
    for mode in ['matched','uniform']:
        local={}
        for e,(pool,adds,edges_,tag) in GRAPH.items():
            core=PLANS['tree'][e][:-len(adds)]
            a=M.symbols[adds];b=M.symbols[pool]
            if mode=='uniform':
                chosen=sorted(pool,key=lambda j:hashlib.sha256(f'{seed}|{tag}|{M.symbols[j]}'.encode()).digest())[:len(adds)]
            else:
                cost=np.full((len(adds),len(pool)+len(adds)),100.)
                cost[:,len(pool):]=10.
                for ii,jj in edges_:
                    raw=hashlib.sha256(f'{seed}|{tag}|{a[ii]}|{b[jj]}'.encode()).digest()
                    cost[ii,jj]=int.from_bytes(raw[:8],'big')/2**64
                ii,jj=linear_sum_assignment(cost)
                ok=jj<len(pool)
                assert ok.sum()==len(np.unique(edges_[:,0]))
                chosen=adds.copy()
                chosen[ii[ok]]=pool[jj[ok]]
                support.append((e,len(adds),ok.sum(),len(set(chosen)-set(adds))))
            local[e]=np.r_[core,chosen]
        for scope,beg,fin in SEGMENTS:
            lo,hi=M.days.get_indexer([beg,fin])
            d,*_=funded(M,A,local,lo,hi)
            d['period']=d.date.dt.to_period('M').astype(str)
            months=d.groupby('period').nav.last().pct_change()
            for month,net in months.iloc[1:-1].items():
                rows.append((seed,mode,scope,month,net,d.nav.iloc[-1]))
    return rows,[(seed,*r) for r in support]

if __name__=='__main__':
    M,A=market()
    PLANS,B=targets(M)
    GRAPH=edges(M,B)
    rows=[];support=[]
    with ProcessPoolExecutor(4,mp_context=mp.get_context('fork')) as pool:
        for r,s in pool.map(worker,range(1,201),chunksize=1):rows.extend(r);support.extend(s)
    pd.DataFrame(rows,columns=['seed','mode','scope','month','net','terminal_nav']).to_parquet(OUT/'random_paths.parquet',index=False)
    pd.DataFrame(support,columns=['seed','entry_idx','seats','supported','different']).to_parquet(OUT/'random_choices.parquet',index=False)
