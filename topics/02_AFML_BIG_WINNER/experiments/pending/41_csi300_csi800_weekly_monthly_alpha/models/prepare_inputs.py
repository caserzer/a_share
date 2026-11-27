import hashlib
import sys
from ep41inputs import *
sys.path.append(str(ep.PRIVATE.parent / 'src'))
from features import compute

def main():
    CACHE.mkdir(exist_ok=True)
    fields = 'qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()
    raw = [read(f) for f in fields]
    c,o,h,l,v,amt,tr,mem = raw
    f = compute(*raw,read('market').close)
    r = c.pct_change(fill_method=None)
    eligible = mem & c.gt(0).rolling(61).sum().eq(61) & c.shift(5).ne(c.shift(60)) & c.ne(c.shift(5))
    dates = read('features')
    weeks = dates.loc[dates.score_eligible, KEY+COLS]
    scored = pd.read_parquet(ep.DEST/'daily_scores.parquet')
    keys = pd.concat([weeks[KEY],scored[KEY]]).drop_duplicates().sort_values(KEY).reset_index(drop=True)
    i,j = c.index.get_indexer(keys.signal_date), c.columns.get_indexer(keys.instrument)
    assert min(i.min(), j.min())>=0
    def take(mat): return mat.to_numpy()[i,j]
    data = keys.join(pd.DataFrame({k:take(f[k]) for k in COLS}))
    parity = data.merge(weeks,on=KEY,suffixes=('','_f'),validate='1:1')
    np.testing.assert_allclose(parity[COLS],parity[[k+'_f' for k in COLS]],atol=1e-12,rtol=0,equal_nan=True)
    ok=np.zeros_like(eligible,dtype=np.int16)
    for col in COLS: ok+=f[col].notna().to_numpy()
    eligible &= ok >= .8*len(COLS)
    rel = r.sub(r.where(eligible).median(axis=1),axis=0)
    data['sigma'] = take(rel.rolling(20).std()*np.sqrt(10))
    # Center observations at their window mean for both semivariances.
    mean=rel.rolling(20).mean()
    nd=mean*0
    down_sq=mean*0
    total_sq=rel.pow(2).rolling(20).sum()
    for lag in range(20):
        obs=rel.shift(lag)
        below=obs.lt(mean)
        nd+=below
        down_sq+=obs.pow(2).where(below,0)
    ratio=(down_sq/(nd-1))/((total_sq-down_sq)/(19-nd))
    data['ncskew20']=take(-rel.rolling(20).skew())
    data['duvol20']=take(np.log(ratio.where(nd.ge(2) & nd.le(18) & ratio.gt(0))))
    data['down_gap']=take((o/c.shift()-1).clip(upper=0))
    data['down_amount20']=take(amt.where(r<0,0).rolling(20).sum()/amt.rolling(20).sum())
    data['amihud20']=take((r.abs()/amt.where(amt>0)).rolling(20).mean())
    data['entry_idx']=i+1
    hist=read('industry').copy()
    hist['instrument']=hist.ts_code.str[-2:]+hist.ts_code.str[:6]
    hist.in_date=pd.to_datetime(hist.in_date);hist.out_date=pd.to_datetime(hist.out_date)
    for col in ['l1_name','l2_code']:
        vals=pd.Series('未知',index=data.index)
        for code,group in hist[hist.instrument.isin(keys.instrument.unique())].groupby('instrument'):
            ix=data.index[data.instrument==code]
            dates=data.loc[ix,'signal_date']
            mapping={}
            for row in group.itertuples():
                valid=dates.ge(row.in_date)&(dates.lt(row.out_date)|pd.isna(row.out_date))
                for idx in ix[valid]: mapping.setdefault(idx,set()).add(getattr(row,col))
            kept={idx:next(iter(ss)) for idx,ss in mapping.items() if len(ss)==1}
            vals.loc[list(kept)]=list(kept.values())
        data[col]=vals
    data['pseudo']=data.l1_name.copy()
    for day,group in data.groupby('signal_date',sort=False):
        order=sorted(group.index,key=lambda idx:hashlib.sha256(data.at[idx,'instrument'].encode()).digest())
        data.loc[order,'pseudo']=group.l1_name.to_numpy()
    for n in [5,10,20]:
        data['h'+str(n)] = take(o.shift(-n-1)/o.shift(-1)-1)
        data['m'+str(n)] = pd.Series(c.index).reindex(i+n+1).to_numpy()
    labels=read('labels')
    # EP36 weekly labels include endpoint restrictions and censoring. Preserve their masks.
    train_keys=weeks[KEY].merge(labels,on=KEY,validate='1:1').set_index(KEY)
    d=data.set_index(KEY)
    for n in [5,10,20]:
        col='h'+str(n)
        d.loc[train_keys.index,col]=train_keys[col]
        d.loc[train_keys.index,'m'+str(n)]=train_keys[col+'_mature']
    data=d.reset_index()
    data['weekly']=pd.MultiIndex.from_frame(data[KEY]).isin(train_keys.index)
    data['outer']=pd.MultiIndex.from_frame(data[KEY]).isin(pd.MultiIndex.from_frame(scored[KEY]))
    data=data.merge(scored[KEY+['R','T']],how='left',on=KEY,validate='1:1')
    for n in [5,10,20]:
        data['y'+str(n)]=pct(data['h'+str(n)],data.signal_date)
    for a in ['l1_name','pseudo','l2_code']:
        data['y_'+a]=pct(data.h10,[data.signal_date,data[a]])
    data['event']=(data.h10-data.groupby('signal_date').h10.transform('median') < -2*data.sigma).where(data.h10.notna() & data.sigma.gt(0)).astype(float)
    data['event_direct']=(data.h10-data.groupby('signal_date').h10.transform('median') < -2*take((c/c.shift(10)-1).sub((c/c.shift(10)-1).where(eligible).median(axis=1),axis=0).rolling(20).std())).where(data.h10.notna())
    data.to_parquet(CACHE/'panel.parquet',index=False)
    g=pct(data[STOCK],data.signal_date)
    g.to_parquet(CACHE/'global.parquet',index=False)
    groups=data[STOCK].groupby([data.signal_date,data.l1_name])
    counts=groups.transform('count')
    fallback=counts.lt(5) | np.repeat(data.l1_name.eq('未知').to_numpy()[:,None],len(STOCK),axis=1)
    sect=(groups.rank().div(counts+1)-.5).where(~fallback,g)
    sect.to_parquet(CACHE/'industry.parquet',index=False)
    counts.groupby(data.signal_date).mean().to_parquet(OUT/'industry_effective_counts.parquet')
    fallback.groupby(data.signal_date).mean().to_parquet(OUT/'industry_fallback.parquet')
    data.loc[data.outer].groupby('signal_date').vol20.median().groupby(lambda day:day.year).median().to_csv(OUT/'annual_vol20.csv')
    print(len(data),data.weekly.sum(),data.outer.sum(),flush=True)
if __name__=='__main__':main()
