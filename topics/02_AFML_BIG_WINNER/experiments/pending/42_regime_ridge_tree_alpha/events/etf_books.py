from event_account import *
from fetch_sources import FUNDS
def main():
    s=Study();m=s.m
    directory=OUT/'etf';directory.mkdir(exist_ok=True)
    raw=pd.read_parquet(engine.LOCAL/'close.parquet').reindex(index=m.days,columns=m.symbols).to_numpy()
    codes=[f[:6] for f in FUNDS]
    units=pd.read_csv(HERE/'unit_history.csv',dtype={'code':str})
    coupons={'512100':['2022-09-02'],'510500':['2022-08-26'],'512800':['2025-07-04'],'512010':['2021-06-25']}
    navs=[];signals={};support=[];all_weights={}
    for code in codes:
        parts=[]
        for tag in ('early','later'):
            candidates=[OUT/(prefix+'_'+code+'_'+tag+'.parquet') for prefix in ['complete','compact','basket']]
            parts.append(next(f for f in candidates if f.exists()))
        d=pd.concat([pd.read_parquet(f) for f in parts],ignore_index=True).drop_duplicates()
        d['instrument']=d.con_code.str[-2:]+d.con_code.str[:6];d['j']=m.symbols.get_indexer(d.instrument)
        d['date']=pd.to_datetime(d.trade_date,format='%Y%m%d');grp=d.groupby('date')
        def series(metric,id_col,value):
            data=pd.read_parquet(OUT/(metric+'_'+code+'.parquet'))
            data['dt']=pd.to_datetime(data[id_col],format='%Y%m%d')
            return data.drop_duplicates('dt',keep='first').set_index('dt')[value].reindex(m.days)
        shares=series('shares','trade_date','fd_share');nav=series('nav','nav_date','unit_nav')
        drift=(shares.pct_change(fill_method=None).abs()>.2)&(nav.pct_change(fill_method=None).abs()>.2)&(shares.diff()*nav.diff()<0)
        drift.loc[drift.index.isin(pd.to_datetime(coupons.get(code,[])))]=True
        flow=(shares.diff(5)*1e4).mask(drift.astype(int).rolling(5,min_periods=1).max()>0).shift(1)
        unit=pd.Series(np.nan,index=m.days)
        for u in units[units.code==code].itertuples():unit.loc[unit.index>=u.start]=u.unit
        mats={a:np.full((len(m.days),m.n),np.nan,np.float32) for a in ['allowed','refund','weight']}
        for date,g in grp:
            i=m.days.get_indexer([date])[0]
            if i<1:continue
            partial=code=='512100' and len(g)<900
            known=np.isfinite(flow.iloc[i]) and np.isfinite(unit.iloc[i]) and not partial
            rows=len(g);priced=g[g.j>=0].copy()
            if len(priced):
                priced['value']=priced.qty*raw[i-1,priced.j]/unit.iloc[i]
            else:priced['value']=[]
            valued=priced.value.notna()&priced.qty.gt(0)
            permitted=priced.sub_flag.eq('允许')|priced.sub_flag.eq('禁止')
            refund=priced.sub_flag.str.contains('允许|禁止|退补',na=False)
            if known:
                for a,mask in [('allowed',permitted),('refund',refund),('weight',refund)]:
                    z=priced[valued&mask];j=z.j.to_numpy();values=z.value.to_numpy()
                    mats[a][i,j]=values*flow.iloc[i]/s.adv[i,j] if a!='weight' else values/nav.iloc[i-1]
            support.append((code,date,rows,len(priced),int(valued.sum()),int((valued&permitted).sum()),int((valued&refund).sum()),known,partial,float(unit.iloc[i]),float(flow.iloc[i]),float(priced.loc[valued&~permitted,'value'].sum()*abs(flow.iloc[i])) if known else np.nan))
        signals[code]=mats
        navs.extend((code,dt,str(dt.date()) in coupons.get(code,[])) for dt in drift[drift].index)
    pd.DataFrame(navs,columns=['fund','split_warning_date','dated_corporate_action']).to_csv(directory/'splits.csv',index=False)
    support=pd.DataFrame(support,columns='fund date basket_rows seen_in_price_cache valued allowed refund known partial unit share_change estimated_excluded_abs_yuan'.split())
    calendar=pd.MultiIndex.from_product([codes,m.days[min(s.pool)-1:max(s.pool)]],names=['fund','date'])
    support.set_index(['fund','date']).reindex(calendar).reset_index().to_parquet(directory/'source_coverage.parquet',index=False)
    valid_days={c:set(g.loc[g.known,'date']) for c,g in support.groupby('fund')}
    sets={'two':codes[:2],'expanded':codes,'only500':[codes[2]],'only1000':[codes[3]],'only_star':[codes[4]],'industry':codes[5:],'expanded_common300':codes,'two_common300':codes[:2],'two_refund':codes[:2],'expanded_refund':codes,'native500':[codes[2]],'native1000':[codes[3]],'nativestar':[codes[4]],'nativeindustry':codes[5:]}
    plans={'ridge':s.top};pairs=[];coverage=[];comp=[]
    for group,funds in sets.items():
        for a in ['flow','reverse','weight','hash']:plans[group+'_'+a]={}
        if group.startswith('native'):plans[group+'_ridge']={}
        key='refund' if group.endswith('refund') else 'allowed'
        def total(index,key):
            a=np.vstack([signals[f][key][index] for f in funds]);mask=np.isfinite(a).any(axis=0)
            v=np.nansum(a,axis=0);v[~mask]=np.nan;return v
        for e,pool in s.pool.items():
            i=e-1;dt=m.days[i];top=s.top[e]
            is_native=group.startswith('native')
            if is_native:top=np.empty(0,int)
            arms=[top.copy() for z in range(4)];hit=0;covered=0
            if all(dt in valid_days.get(f,set()) for f in funds) and (not group.endswith('common300') or all(dt in valid_days.get(f,set()) for f in codes)):
                flow=total(i,key)
                if group.endswith('common300'):
                    original=np.isfinite(signals[codes[0]][key][i])|np.isfinite(signals[codes[1]][key][i])
                    flow[~original]=np.nan
                weight=total(i-1,'weight')-total(i-6,'weight')
                cap=s.cap[e];sec=s.sector(i)
                cov=np.isfinite(flow)&np.isfinite(cap)&np.isfinite(weight)&(sec!='未知')
                covered=int(cov[pool].sum())
                if is_native:
                    elig=pool[cov[pool]]
                    k=min(len(s.top[e]),max(1,len(elig)//10)) if len(elig) else 0
                    top=elig[np.lexsort((elig,-s.r[e][elig]))[:k]]
                    arms=[top.copy() for z in range(4)]
                cand=np.setdiff1d(pool[cov[pool]],top)
                # Shared bidirectional opportunity and size-matched sector rule. Keep the
                # candidate sets separate for each alternative book; each book has unique names.
                used=[set() for arm in arms]
                for h,b in enumerate(top):
                    if not cov[b]:continue
                    p=cand[(sec[cand]==sec[b])&(abs(cap[cand]-cap[b])<=.1)]
                    alt=[np.array([j for j in p if j not in uu],int) for uu in used]
                    positive=alt[0][flow[alt[0]]>flow[b]];negative=alt[1][flow[alt[1]]<flow[b]]
                    if not len(positive) or not len(negative) or any(len(q)==0 for q in alt[2:]):continue
                    rng=matching.tiekeys(1,int(dt.strftime('%Y%m%d')),alt[3],salt=int(b))
                    selected=[positive[np.lexsort((positive,-s.r[e][positive],-flow[positive]))[0]],negative[np.lexsort((negative,-s.r[e][negative],flow[negative]))[0]],alt[2][np.lexsort((alt[2],-s.r[e][alt[2]],-weight[alt[2]]))[0]],alt[3][rng.argmin()]]
                    for arr,uu,j in zip(arms,used,selected):arr[h]=j;uu.add(j)
                    hit+=1;pairs.append((group,e,int(b),*selected,flow[b],flow[selected[0]],flow[selected[1]]))
            if is_native:plans[group+'_ridge'][e]=top
            for a,arr in zip(['flow','reverse','weight','hash'],arms):plans[group+'_'+a][e]=arr
            coverage.append((group,e,len(pool),covered,len(top),hit))
        comp+= [(group+'_'+a,group+'_ridge' if group.startswith('native') else 'ridge') for a in ['flow','reverse','weight','hash']]+[(group+'_flow',group+'_reverse'),(group+'_flow',group+'_weight')]
    for e,top in s.top.items():
        ap=plans['expanded_common300_flow'][e]!=top
        bp=plans['two_common300_flow'][e]!=top
        joint=ap&bp
        for group in ['expanded_common300','two_common300']:
            for a in ['flow','reverse','weight','hash']:
                arr=plans[group+'_'+a][e];arr[~joint]=top[~joint]
        coverage.append(('both_common300_final',e,len(s.pool[e]),-1,len(top),int(joint.sum())))
    comp += [('expanded_common300_'+a,'two_common300_'+a) for a in ['flow','reverse']]
    pd.DataFrame(coverage,columns='group entry_idx pool covered head exchanged'.split()).to_parquet(directory/'opportunities.parquet',index=False)
    pd.DataFrame(pairs,columns='group entry_idx old flow reverse weight hash score_old score_flow score_reverse'.split()).to_parquet(directory/'choices.parquet',index=False)
    s.run('etf',plans,comp)
if __name__=='__main__':main()
