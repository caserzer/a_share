from event_account import *
from collections import defaultdict
def main():
    s=Study();m=s.m
    old=pd.read_csv(EP41/'sources/n5/relationships.csv')
    new=pd.read_csv(HERE/'additional_edges.csv')
    all_edges=pd.concat([old.assign(origin='EP41'),new.assign(origin='EP42')],ignore_index=True)
    all_edges['known_idx']=m.days.searchsorted(pd.to_datetime(all_edges.disclosure_date),side='right')
    all_edges['start_idx']=m.days.searchsorted(pd.to_datetime(all_edges.active_start))
    all_edges['end_idx']=m.days.searchsorted(pd.to_datetime(all_edges.active_end),side='right')
    all_edges.to_csv(OUT/'named_contracts.csv',index=False)
    paths={};support=[];comparisons=[];targets=[]
    prices=pd.read_parquet(engine.LOCAL/'qfq_close.parquet').reindex(index=m.days,columns=m.symbols)
    ret=prices.pct_change(5,fill_method=None).to_numpy()
    for group,edges in [('original',all_edges[all_edges.origin=='EP41']),('expanded',all_edges)]:
        for target,partner in [('supplier','buyer'),('buyer','supplier')]:
            names=[group+'_'+target+'_'+a for a in ['partner','industry','pseudo','ridge']]
            for a in names:paths[a]={}
            forbidden=defaultdict(set)
            for _,r in all_edges.iterrows():
                x=m.symbols.get_indexer([r[target],r[partner]])
                forbidden[x[0]].add((int(x[1]),int(r.known_idx)))
            for e,pool in s.pool.items():
                i=e-1
                active=edges[(edges.known_idx<=i)&(edges.start_idx<=i)&(edges.end_idx>i)]
                g=defaultdict(list)
                for _,r in active.iterrows():
                    j,k=m.symbols.get_indexer([r[target],r[partner]])
                    if j>=0 and k>=0 and j in pool and np.isfinite(ret[i,k]):g[j].append(k)
                scores=[];secs=s.sector(i)
                for j,links in g.items():
                    real=np.mean(ret[i,links]);industry=pool[(secs[pool]==secs[j])&(pool!=j)&np.isfinite(ret[i,pool])]
                    ps=[]
                    dated_forbidden={v for v,known in forbidden[j] if known<=i}
                    for k in links:
                        eligible=[v for v in pool[(secs[pool]==secs[k])&np.isfinite(ret[i,pool])] if v!=j and v not in dated_forbidden and v not in ps]
                        if not eligible:break
                        def digest(v):return hashlib.sha256(f'{m.symbols[j]}|{m.symbols[k]}|{m.symbols[v]}'.encode()).digest()
                        ps.append(min(eligible,key=digest))
                    if len(ps)!=len(links) or not len(industry) or secs[j]=='未知':continue
                    scores.append((int(j),real,float(np.mean(ret[i,industry])),float(np.mean(ret[i,ps])),s.r[e][j]))
                    targets.append((group,target,e,int(j),'|'.join(m.symbols[links]),'|'.join(m.symbols[ps]),*scores[-1][1:]))
                # Compare one equal-capital event per active date; disclosed edges with one
                # eligible name have identical ranking decisions in every arm.
                for n,name in enumerate(names,1):
                    paths[name][e]=np.asarray([max(scores,key=lambda t:(t[n],s.r[e][t[0]],t[0]))[0]] if scores else [],int)
                support.append((group,target,e,len(active),len(g),len(scores),len(set(int(paths[a][e][0]) for a in names)) if scores else 0))
            comparisons.extend((names[0],b) for b in names[1:])
    p=OUT/'supply';p.mkdir(exist_ok=True)
    pd.DataFrame(support,columns='history direction entry_idx active_edges active_target covered alternative_choices'.split()).to_parquet(p/'support.parquet',index=False)
    pd.DataFrame(targets,columns='history direction entry_idx target partners pseudo_partners return5 industry5 pseudo5 ridge'.split()).to_parquet(p/'signals.parquet',index=False)
    s.run('supply',paths,comparisons)
if __name__=='__main__':main()
