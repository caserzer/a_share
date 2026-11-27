from disclosures import *
def main():
    s=Study();m=s.m
    sources={};o=pd.read_parquet(OUT/'all_sue_events.parquet')
    for label,kind in [('guidance','guidance'),('annual_profit','formal'),('annual_eps','formal_eps'),('flash_eps_proxy','flash_eps_proxy')]:
        for first in [True,False]:
            z=o[(o.kind==kind)&(o['first']==first)&(o.quarter==4)&(o.sue>0)]
            sources[label+('' if first else '_later')]=z
    for quarter in (1,2,3):
        sources['quarter'+str(quarter)]=o[(o.quarter==quarter)&o['first']&(o.sue>0)]
    z=pd.read_parquet(OUT/'acceleration.parquet')
    for metric,g in z.groupby('metric'):
        g=g.dropna(subset='acceleration')
        sources[metric+'_accel']=g[g.acceleration>0]
        sources[metric+'_growth']=g[g.growth>0]
    eps=pd.read_parquet(EP41/'sources/n2/eps_events.parquet').rename(columns={'publication_proxy_date':'ann_date'})
    eps=eps[eps.fiscal_year>=eps.ann_date.dt.year]
    pct=(eps.value-eps.previous)/eps.previous.where(eps.previous>0)
    sources['eps_large']=eps[pct>=.2-1e-12];sources['eps_small']=eps[(pct>0)&(pct<.2-1e-12)]
    keys=['instrument','ann_date']
    big_index=pd.MultiIndex.from_frame(sources['eps_large'][keys])
    small=sources['eps_small'];sources['eps_small']=small[~pd.MultiIndex.from_frame(small[keys]).isin(big_index)]
    sources['eps_large_current_fy']=eps[(pct>=.2-1e-12)&(eps.fiscal_year==eps.ann_date.dt.year)]
    sources['eps_recovery']=eps[(eps.previous<=0)&(eps.value>0)]
    plans={'original_ridge':s.top};dens={};pairs=[];coverage=[]
    for label,source in sources.items():
        d=source[['instrument','ann_date']].drop_duplicates()
        d['entry_idx']=m.days.searchsorted(d.ann_date,side='right')+1
        universe=defaultdict(set)
        for row in d.itertuples():universe[row.entry_idx].add(row.instrument)
        for name in [label,label+'_match']:plans[name]={};dens[name]={}
        for e,pool in s.pool.items():
            available=m.symbols.get_indexer(list(universe[e]));selected=np.intersect1d(pool,available)
            a,b=s.pair(e,selected)
            for name,ids in [(label,a),(label+'_match',b)]:
                plans[name][e]=ids;dens[name][e]=len(selected)
            coverage.append((label,e,len(universe[e]),len(selected),len(a),len(pool)))
            pairs.extend((label,e,int(i),int(j),float(abs(s.cap[e][i]-s.cap[e][j])),s.sector(e-1)[i]) for i,j in zip(a,b))
    p=OUT/'event_details';p.mkdir(exist_ok=True)
    pd.DataFrame(pairs,columns='arm entry_idx event_security comparator_security cap_rank_difference industry'.split()).to_parquet(p/'pairs.parquet',index=False)
    pd.DataFrame(coverage,columns='arm entry_idx disclosed eligible matched pool'.split()).to_parquet(p/'support.parquet',index=False)
    # Direct comparison on shared daily event funds for differing positive filters.
    direct=[]
    for a,b in [('eps_large','eps_small'),('revenue_accel','revenue_growth'),('deducted_accel','deducted_growth')]:
        for name in [a+'_direct',b+'_direct']:plans[name]={};dens[name]={}
        for e,pool in s.pool.items():
            left=list(plans[a][e]);right=list(plans[b][e]);k=min(len(left),len(right))
            for nm,arr in [(a,left),(b,right)]:
                ids=np.asarray(sorted(arr,key=lambda j:(-s.r[e][j],j))[:k],int)
                plans[nm+'_direct'][e]=ids;dens[nm+'_direct'][e]=max(len(left),len(right))
        direct.append((a+'_direct',b+'_direct'))
    comp=[(a,a+'_match') for a in sources]+direct
    for h in [10,20]:s.run('events_h'+str(h),plans,comp,h,dens)
if __name__=='__main__':main()
