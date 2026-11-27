"""Store original leaf assignments, four intervention path changes and scale serial dependence."""
from scale_common import *
from transform_scale import VOLS

def main():
    f=data(STOCK)
    scales=pd.read_parquet(RES/'scale_clock.parquet')
    leavesdir=RES/'leaves'
    leavesdir.mkdir(exist_ok=True)
    placebo=pd.read_parquet(RES/'S4_placebo_dates.parquet')
    comparisons=[];moments=[];switch=[];saturations=[]
    for q,tr,x in outer_folds(f):
        tre=lgb.Booster(model_file=str(MODELS/f'{q}_raw.txt'))
        med=tr[STOCK].median().fillna(0)
        raw=x[STOCK].fillna(med).to_numpy(copy=True)
        leaf=tre.predict(raw,pred_leaf=True,num_threads=1)
        def store_leaves(frame,arr,cohort):
            # Leaf values are retained in the per-quarter model text, indexed by tree and leaf ID.
            key=frame[KEY].reset_index(drop=True).copy()
            key['observed']=frame.observed.to_numpy() if 'observed' in frame else True
            assert arr.max()<256
            key['leaf_ids']=[bytes(row) for row in arr.astype('uint8')]
            atomic_parquet(key,leavesdir/f'{q}_{cohort}.parquet')
            prev={}
            for d,group in key.groupby('signal_date',sort=True):
                a=group[group.observed]
                cur={r.instrument:arr[i] for i,r in zip(a.index,a.itertuples())};ids=cur.keys()&prev.keys()
                counts=sum(np.count_nonzero(cur[k]!=prev[k]) for k in ids)
                switch.append((str(q),cohort,d,len(ids),len(ids)*arr.shape[1],counts))
                prev=cur
        store_leaves(x,leaf,'eligible')
        fixed=pd.read_parquet(WORK/'fixed_cohort.parquet',filters=[('signal_date','>=',q.start_time),('signal_date','<=',q.end_time)])
        fixed=fixed.sort_values(KEY).reset_index(drop=True)
        store_leaves(fixed,tre.predict(fixed[STOCK].fillna(med),pred_leaf=True,num_threads=1),'fixed')
        days=pd.DatetimeIndex(sorted(x.signal_date.unique()));di=days.get_indexer(x.signal_date)
        live=scales.loc[days].to_numpy();center=scales.loc[tr.signal_date.unique()].median().to_numpy()
        lag=scales.shift(20).loc[days].to_numpy()
        clocks={'live':live,'fixed':np.broadcast_to(center,live.shape),'loc':np.where(np.arange(6)%2==0,live,center),'width':np.where(np.arange(6)%2,live,center),'lag20':lag}
        for seed,g in placebo[placebo.quarter.eq(str(q))].groupby('seed'):
            assert np.array_equal(g.signal_date.to_numpy(),days.to_numpy())
            clocks[f'block{seed:02d}']=scales.loc[g.source_date].to_numpy()
        v=x[VOLS].to_numpy();lg=np.full_like(v,np.nan);np.log(v,out=lg,where=v>0)
        u=np.divide(lg-live[di,::2],live[di,1::2],out=np.full_like(v,np.nan),where=live[di,1::2]>0)
        lower=tr[VOLS].min().to_numpy();upper=tr[VOLS].max().to_numpy();ids=[STOCK.index(c) for c in VOLS]
        for arm,clock in clocks.items():
            for j,feat in enumerate(scales):
                s=pd.Series(clock[:,j]);ac=s.autocorr() if s.nunique()>1 else np.nan
                moments.append((str(q),arm,feat,len(s),s.min(),s.quantile(.25),s.median(),s.quantile(.75),s.max(),ac))
            vv=np.exp(clock[di,::2]+clock[di,1::2]*u)
            vv=np.where(np.isfinite(vv)&(clock[di,1::2]>0),vv,v)
            if arm=='live':vv=v
            for j,feat in enumerate(VOLS):saturations.append((str(q),arm,feat,np.isfinite(vv[:,j]).sum(),np.sum(vv[:,j]<lower[j]),np.sum(vv[:,j]>upper[j]),np.sum(~(live[:,2*j+1]>0))))
            if arm not in ['live','fixed','width','loc','lag20']:continue
            raw[:,ids]=np.where(np.isfinite(vv),vv,med[VOLS].to_numpy())
            b=tre.predict(raw,pred_leaf=True,num_threads=1)
            count=(leaf!=b).sum(axis=1)
            for dd,g in pd.DataFrame({'day':x.signal_date.to_numpy(),'cnt':count}).groupby('day'):
                comparisons.append((str(q),arm,dd,len(g),int((g.cnt>0).sum()),int(g.cnt.sum()),b.shape[1]))
    pd.DataFrame(comparisons,columns='quarter arm signal_date stocks any_leaf_changed changed_trees trees'.split()).to_csv(RES/'S3_leaf_changes.csv',index=False)
    pd.DataFrame(moments,columns='quarter arm scale signals minimum q25 median q75 maximum lag1_autocorr'.split()).to_csv(RES/'S4_scale_distribution.csv',index=False)
    pd.DataFrame(switch,columns='quarter cohort signal_date shared_stocks common_trees changed_leaves'.split()).to_csv(RES/'S1_leaf_transitions.csv',index=False)
    pd.DataFrame(saturations,columns='quarter arm feature observed below above unchanged_days'.split()).to_csv(RES/'S4_column_support.csv',index=False)
if __name__=='__main__':main()
