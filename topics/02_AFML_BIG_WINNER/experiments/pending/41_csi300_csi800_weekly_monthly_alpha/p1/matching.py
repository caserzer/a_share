"""Pair on same-date sector, trailing traded value, and latest known-date free shares."""
from engine import *
from scipy.optimize import linear_sum_assignment
import json

def covariates(m):
    rawclose=pd.read_parquet(LOCAL/'close.parquet').reindex(index=m.days,columns=m.symbols)
    adv=pd.read_parquet(LOCAL/'money.parquet').reindex_like(rawclose).rolling(20,min_periods=20).mean()
    volatility=pd.read_parquet(LOCAL/'qfq_close.parquet').reindex_like(rawclose).pct_change(fill_method=None).rolling(20,min_periods=20).std()
    floats=pd.DataFrame(np.nan,index=m.days,columns=m.symbols)
    for receipt in sorted((PRIVATE/'style_caps_20261117').glob('*.receipt.json')):
        rec=json.loads(receipt.read_text())
        f=receipt.with_name(receipt.name.replace('.receipt',''));data=f.read_bytes()
        assert rec['sha256']==hashlib.sha256(data).hexdigest()
        raw=json.loads(data)['data']
        g=pd.DataFrame(raw['items'],columns=raw['fields'])
        assert not g.ts_code.duplicated().any()
        dt=pd.Timestamp(f.stem)
        if dt not in m.days:continue
        g.index=g.ts_code.str[-2:]+g.ts_code.str[:6]
        floats.loc[dt]=g.free_share.reindex(m.symbols)
    # Pick a snapshot date first; never silently borrow an older stock observation.
    source=pd.Series(np.arange(len(m.days)),index=m.days).where(floats.notna().any(axis=1)).shift().ffill(limit=7)
    cap=np.full_like(floats,np.nan)
    ok=source.notna()
    cap[ok]=floats.iloc[source[ok].astype(int)].to_numpy()*rawclose.loc[ok].to_numpy()
    cap[cap<=0]=np.nan
    sector=pd.read_parquet(PRIVATE/'industry.parquet')
    sector['instrument']=sector.ts_code.str[-2:]+sector.ts_code.str[:6]
    start=sector.in_date.astype(str).to_numpy(); end=sector.out_date.fillna('99999999').astype(str).to_numpy()
    windows=sorted(set(start)|set(end))
    cache={}
    def industry(i):
        d=m.days[i].strftime('%Y%m%d');k=np.searchsorted(windows,d,side='right')
        if k not in cache:
            names=sector.loc[(start<=d)&(end>d),['instrument','l1_name']].drop_duplicates()
            cache[k]=names.loc[~names.instrument.duplicated(False)].set_index('instrument').l1_name.reindex(m.symbols).fillna('未知').to_numpy()
        return cache[k]
    return cap,adv.to_numpy(),volatility.to_numpy(),industry,source

def tiekeys(seed, date, ids, salt=0):
    """SplitMix64 deterministic priorities bound to date, seed and stable security identifiers."""
    x=np.asarray(ids,dtype=np.uint64)+np.uint64(date*1000003+seed*1009+salt)
    with np.errstate(over='ignore'):
        x=x+np.uint64(0x9e3779b97f4a7c15)
        x=(x^(x>>np.uint64(30)))*np.uint64(0xbf58476d1ce4e5b9)
        x=(x^(x>>np.uint64(27)))*np.uint64(0x94d049bb133111eb)
        x=x^(x>>np.uint64(31))
    return (x>>np.uint64(11)).astype(float)/(2**53)

def assign(mask,weights):
    # A dummy pays more than the maximum possible total edge cost.
    n=len(mask);bad=2*n+2.
    objective=np.hstack([np.where(mask,weights,bad*2),np.full((n,n),bad)])
    a,b=linear_sum_assignment(objective)
    keep=b<mask.shape[1]
    return a[keep],b[keep]

def main():
    m=load();plans,_=selections(m)
    cap,adv,vol,industry,source=covariates(m)
    cache={};pairs=[];support=[];denom={}
    ids=m.symbols.str[2:].astype(int).to_numpy(dtype='uint64')
    advrows=[]
    for e,pool in plans['refit','pool'].items():
        top=plans['refit','head'][e]; runner=plans['refit','runner'][e]
        denom[e]=len(top);i=e-1
        covs=pd.DataFrame(np.array([cap[i,pool],adv[i,pool],vol[i,pool]]).T,index=pool).rank(pct=True)
        a,b=covs.loc[top].to_numpy(),covs.loc[runner].to_numpy()
        s1,s2=industry(i)[top],industry(i)[runner]
        da=abs(a[:,None,:]-b[None,:,:]);ind=s1[:,None]==s2[None,:]
        d=int(m.days[i].strftime('%Y%m%d'))
        k10=None
        for tol in (.1,.2):
            mask=ind&(da[:,:,0]<=tol)&(da[:,:,1]<=tol)
            cost=da[:,:,:2].sum(axis=2)
            ia,ib=assign(mask,cost)
            for aidx,bidx in zip(ia,ib):
                pairs.append((e,tol,m.symbols[top[aidx]],m.symbols[runner[bidx]],s1[aidx],
                    *da[aidx,bidx],m.days[int(source.iloc[i])] if pd.notna(source.iloc[i]) else pd.NaT,
                    bool(m.buy[e,top[aidx]]),bool(m.buy[e,runner[bidx]])))
            for s in np.unique(s1):
                x=s1==s
                support.append((e,tol,s,x.sum(),len(top),mask[x].any(axis=0).sum(),(s1[ia]==s).sum(),np.sum(x & ~np.isfinite(a[:,:2]).all(axis=1))))
            for tag,selection in [('matched_head',top[ia]),('matched_runner',runner[ib])]:
                cache.setdefault((tol,tag),{})[e]=selection
            if tol==.1:k10=ia
            else:
                for label,h,r in [('shared',ia[np.isin(ia,k10)],ib[np.isin(ia,k10)]),('wide_only',ia[~np.isin(ia,k10)],ib[~np.isin(ia,k10)])]:
                    for tag,selection in [('head',top[h]),('runner',runner[r])]:
                        cache.setdefault((tol,label+'_'+tag),{})[e]=selection
                # Refine tight-side common support in case the wider assignment changes head seats.
                for tag,selection in [('head',top[k10][np.isin(k10,ia)]),('runner',cache[.1,'matched_runner'][e][np.isin(k10,ia)])]:
                    cache.setdefault((.1,'shared_'+tag),{})[e]=selection
            if tol==.1:
                cache.setdefault('match_inputs',{})[e]=(top,runner,mask,ids[top,None]*1000000+ids[None,runner],d)
    pd.DataFrame(pairs,columns='entry_idx caliper head runner industry cap_distance adv_distance vol_distance share_snapshot head_buy_allowed runner_buy_allowed'.split()).to_parquet(RESULT/'pairs.parquet',index=False)
    pd.DataFrame(support,columns='entry_idx caliper industry head_seats all_head_seats candidates matched missing_covariate'.split()).to_csv(RESULT/'support.csv',index=False)
    def record(plan,rows,**meta):
        packed=pack(m,plan,denom)
        for seg,span in enumerate(RANGES,1):
            b=simulate(m,packed,span)
            rows.append(b.assign(segment=seg,**meta))
    inputs=cache.pop('match_inputs')
    matched=[]
    for (tol,tag),plan in cache.items():
        record(plan,matched,caliper=tol,bucket=tag)
    pd.concat(matched).reset_index().to_parquet(RESULT/'matched_daily.parquet',index=False)
    for algo in ['uniform','matched','matched_head']:
        if len(sys.argv)>1 and algo!=sys.argv[1]:continue
        rows=[]
        for seed in range(1,201):
            plan={}
            for e,(top,runner,mask,edge,d) in inputs.items():
                if algo=='uniform':
                    g=np.argsort(tiekeys(seed,d,ids[runner]))[:len(top)]
                else:
                    h,g=assign(mask,tiekeys(seed,d,edge))
                plan[e]=top[h] if algo=='matched_head' else runner[g]
            record(plan,rows,seed=seed)
            if seed%25==0:print(algo,seed,flush=True)
        pd.concat(rows).reset_index().to_parquet(RESULT/(algo+'_paths.parquet'),index=False)
if __name__=='__main__':main()
