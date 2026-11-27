"""Frozen-tree score interventions and support bounds for S3 and S4."""
from scale_common import *
from scipy.spatial import cKDTree

VOLS=['vol5','vol20','vol60']

def nearest_other_day(tree,train_x,groups):
    result=np.full(len(train_x),np.inf)
    rows=np.arange(len(train_x));k=8
    while len(rows):
        distances,indices=tree.query(train_x[rows],k=min(k,len(train_x)))
        good=groups[indices]!=groups[rows,None]
        solved=good.any(axis=1)
        result[rows[solved]]=np.min(np.where(good,distances,np.inf),axis=1)[solved]
        rows=rows[~solved];k*=2
        if k>2*len(train_x) and len(rows):raise ValueError('no second date')
    return result

def main():
    frame=data(STOCK)
    scal=pd.read_parquet(RES/'scale_clock.parquet')
    ref=pd.read_parquet(EP41/'models/results/quarterly_scores.parquet',columns=KEY+['M1_raw'])
    outall=[];support_rows=[];clocks=[]
    for q,train,test in outer_folds(frame):
        med=train[STOCK].median().fillna(0.)
        file=MODELS/f'{q}_raw.txt'
        model=lgb.Booster(model_file=str(file)) if file.exists() else fit_tree(train[STOCK].fillna(med),train.y10)
        test_days=pd.DatetimeIndex(sorted(test.signal_date.unique()))
        days=test_days.get_indexer(test.signal_date)
        cols=[v+suffix for v in VOLS for suffix in ['_m','_s']]
        scale=scal.loc[test_days,cols].to_numpy()
        # The weekly training rows may include sparse/censored labels. Recover cross-section metrics
        # from the whole eligible pool on these historical training dates, with equal date weights.
        center=scal.loc[train.signal_date.unique(),cols].median().to_numpy()
        common=np.tile(center,(len(test_days),1))
        lag=scal.shift(20).loc[test_days,cols].to_numpy()
        prev=scal.loc[scal.index<q.start_time,cols]
        starts=np.flatnonzero(prev.notna().all(axis=1).rolling(20).sum().eq(20).to_numpy())-19
        hrs=np.arange(len(test_days))//20
        variants={'live':scale,'fixed':common,'loc':np.where(np.arange(6)%2==0,scale,common),'width':np.where(np.arange(6)%2==0,common,scale),'lag20':lag}
        for seed in range(1,21):
            rng=np.random.default_rng(np.random.SeedSequence([42,q.ordinal,seed]))
            chosen=rng.choice(starts,size=hrs[-1]+1)
            indices=chosen[hrs]+np.arange(len(test_days))%20
            variants[f'block{seed:02d}']=prev.to_numpy()[indices]
            clocks.extend([(str(q),seed,dt,prev.index[idx]) for dt,idx in zip(test_days,indices)])
        raw=test[VOLS].to_numpy()
        log=np.full_like(raw,np.nan);np.log(raw,out=log,where=raw>0)
        um=np.divide(log-scale[days,::2],scale[days,1::2],out=np.full_like(log,np.nan),where=scale[days,1::2]>0)
        train_raw=train[VOLS].to_numpy()
        train_ok=np.isfinite(train_raw).all(axis=1)&(train_raw>0).all(axis=1)
        logs=np.log(train_raw[train_ok])
        middle=np.median(logs,axis=0)
        spread=np.quantile(logs,.75,axis=0)-np.quantile(logs,.25,axis=0)
        joint=(logs-middle)/spread
        tree=cKDTree(joint)
        threshold=np.quantile(nearest_other_day(tree,joint,train.signal_date.to_numpy()[train_ok]),.99)
        x=test[STOCK].fillna(med).to_numpy(copy=True);vidx=[STOCK.index(v) for v in VOLS]
        lower=np.nanmin(train_raw,axis=0);upper=np.nanmax(train_raw,axis=0)
        out=test[KEY+['entry_idx']].copy()
        all_support=np.ones(len(out),bool);main_support=all_support.copy()
        for arm,clock in variants.items():
            vals=np.exp(clock[days,::2]+clock[days,1::2]*um)
            vals=np.where(np.isfinite(vals) & (clock[days,1::2]>0),vals,raw)
            if arm=='live':
                np.testing.assert_allclose(vals,raw,rtol=1e-12,atol=0,equal_nan=True)
                vals=raw
            x[:,vidx]=np.where(np.isfinite(vals),vals,med[VOLS].to_numpy())
            out['vol_'+arm]=model.predict(x,num_threads=1)
            ok=np.isfinite(vals).all(axis=1)&(vals>0).all(axis=1)
            marginal=np.all((vals>=lower)&(vals<=upper),axis=1)
            inside=np.zeros(len(vals),bool)
            inside[ok]=tree.query((np.log(vals[ok])-middle)/spread)[0]<=threshold
            inside &= marginal
            all_support &= inside
            if arm in ['live','lag20','fixed']:main_support&=inside
            for d,n,unknown,known,ex in zip(test_days,np.bincount(days),np.bincount(days,weights=~ok),np.bincount(days,weights=inside),np.bincount(days,weights=ok & ~marginal)):
                support_rows.append((str(q),d,arm,int(n),int(unknown),int(known),int(ex),threshold))
        check=out.merge(ref,on=KEY,validate='1:1')
        np.testing.assert_allclose(check.vol_live,check.M1_raw,atol=1e-10,rtol=0)
        out['all_support']=all_support;out['main_support']=main_support
        outall.append(out)
        print(q,'scale',threshold,all_support.mean(),flush=True)
    atomic_parquet(pd.concat(outall),RES/'scale_scores.parquet')
    atomic_parquet(pd.DataFrame(support_rows,columns='quarter signal_date arm total unknown supported outside_marginal threshold'.split()),RES/'S4_support.parquet')
    atomic_parquet(pd.DataFrame(clocks,columns='quarter seed signal_date source_date'.split()),RES/'S4_placebo_dates.parquet')
if __name__=='__main__':main()
