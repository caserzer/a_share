"""Rebuild both historical domains using contemporaneous constituent-specific return z-scores."""
from core42 import *
from inputs42 import ci,compute,pct_history,CACHE
from engine import LOCAL,OUT800,PRIVATE,membership
import json
from pathlib import Path
import pyarrow.parquet as pq

WIDE_CACHE=CACHE/'wide'
WIDE_CACHE.mkdir(exist_ok=True)

def domain_xs(ret,inside,outside):
    groups=[]
    for mem in (inside,outside):
        r=ret.where(mem)
        mean=r.mean(axis=1);sd=r.std(axis=1,ddof=0).where(r.count(axis=1)>=100)
        groups.append(r.sub(mean,axis=0).div(sd,axis=0))
    return groups

def replace_xs(frame,days,names,xs):
    f=frame.copy()
    i=days.get_indexer(f.signal_date);j=names.get_indexer(f.instrument)
    assert min(i.min(),j.min())>=0
    dom=f.in300.to_numpy()
    for lag in range(20):
        f['xsret_lag'+str(lag)]=np.where(i>=lag,np.where(dom,xs[0].to_numpy()[i-lag,j],xs[1].to_numpy()[i-lag,j]),np.nan)
    return f

def main():
    fields='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate'.split()
    raw=[pd.read_parquet(LOCAL/(f+'.parquet')).loc[:'2026-10-12'] for f in fields]
    c=raw[0];days=c.index;names=c.columns
    mem=membership(days,names)
    nm=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex(index=days,columns=names,fill_value=False)
    m300=pd.read_parquet(PRIVATE/'market.parquet').close.reindex(days)
    ret=c.pct_change(fill_method=None);r300=ret.where(nm)
    mu=r300.mean(axis=1);sd=r300.std(axis=1,ddof=0).where(r300.count(axis=1)>=100)
    xs=domain_xs(ret,mem&nm,mem&~nm)
    raw_week=pd.read_parquet(LOCAL/'wide_features.parquet')
    wkdays=pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    raw_week=raw_week[raw_week.signal_date.isin(wkdays)&raw_week.h10.notna()].copy()
    keep60=c.notna().rolling(60).sum().ge(60)
    local=replace_xs(raw_week,days,names,xs)
    ok=keep60.to_numpy()[days.get_indexer(local.signal_date),names.get_indexer(local.instrument)]
    local=local[ok&(local[ci.COLS].notna().mean(axis=1)>=.8)].sort_values(ci.KEY)
    local.to_parquet(WIDE_CACHE/'domain_weeks.parquet',index=False)
    early_end=days.get_loc('2021-01-08')
    mask=mem & c.gt(0).rolling(61).sum().eq(61) &(c.shift(5)/c.shift(60)).ne(1)&(c/c.shift(5)).ne(1)
    valid=np.zeros(c.shape,bool)
    for k in range(0,len(names),120):
        ns=names[k:k+120]
        features=compute(*[x[ns] for x in raw],nm[ns],m300)
        i,j=np.where(mask[ns])
        full=pd.DataFrame({f:features[f].to_numpy()[i,j] for f in ci.COLS})
        old300=nm[ns].to_numpy();g300=old300[i,j]
        pooled=ret[ns].sub(mu,axis=0).div(sd,axis=0).to_numpy()
        for l in range(20):
            vals=pooled[i-l,j].copy()
            vals[(i<l)|(g300 & ~old300[i-l,j])]=np.nan
            full['xsret_lag'+str(l)]=vals
        full=full.assign(signal_date=days[i],entry_idx=i+1,instrument=ns[j],in300=g300)
        good=full[ci.COLS].notna().mean(axis=1)>=.8
        valid[i[good],j[good]+k]=True
        early=full[good & (full.signal_date>='2019-01-01')&(full.signal_date<'2021-01-08')]
        early.to_parquet(WIDE_CACHE/f'early_{k:04}.parquet',index=False)
        sel=(full.signal_date>='2021-01-08') & (i+11<=days.get_loc('2026-10-12'))
        f=replace_xs(full[sel],days,names,xs)
        f=f[f[ci.COLS].notna().mean(axis=1)>=.8]
        f.to_parquet(WIDE_CACHE/f'domain_{k:04}.parquet',index=False)
    r=ret.where((valid&~nm.to_numpy()))
    raw_z=(r.quantile(.75,axis=1)-r.quantile(.25,axis=1)).where(r.count(axis=1)>=100).rolling(20).mean()
    pd.DataFrame({'Z1_raw':raw_z,'Z1':pct_history(raw_z),'stocks':r.count(axis=1)}).rename_axis('signal_date').reset_index().to_parquet(OUT/'outside_state.parquet',index=False)
    build_scores(local,raw_week[raw_week.weekly_ok].sort_values(ci.KEY),days)

def build_scores(local,pooled,days):
    from inputs42 import EP40
    import importlib.util
    src=OUT800.parent/'scores.py'
    spec=importlib.util.spec_from_file_location('pooled_69_fit',src)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    source=ci.prepare().sort_values(ci.KEY)
    saved=pd.read_parquet(OUT800/'scores.parquet')
    keys=ci.KEY+['entry_idx']
    rows=[];audit=[]
    early=pd.concat(pd.read_parquet(f) for f in sorted(WIDE_CACHE.glob('early_*.parquet'))).sort_values(ci.KEY)
    for q,g in early.groupby(early.signal_date.dt.to_period('Q')):
        cut=q.start_time
        result=g[keys+['in300']].copy()
        for kind in ['transfer','refit']:
            training=(source[source.h10_mature<cut] if kind=='transfer' else pooled[pooled.exit_idx<days.searchsorted(cut)]).copy()
            if kind=='refit':
                group=training.groupby('signal_date').h10
                training['target_rank']=group.rank()/(group.transform('size')+1)-.5
            r=ci.ridge(training,ci.COLS,'target_rank')
            tree,med=mod.tree(training)
            result[kind+'_R']=ci.predict(g[ci.COLS],r)
            result[kind+'_T']=tree.predict(g[mod.C69].fillna(med),num_threads=2)
        rows.append(result)
    del early
    nm=pd.read_parquet(PRIVATE/'daily_members.parquet')
    ii=nm.index.get_indexer(saved.signal_date);jj=nm.columns.get_indexer(saved.instrument)
    saved['in300']=(jj>=0)&nm.to_numpy()[ii,jj]
    pd.concat([*rows,saved]).sort_values(ci.KEY).to_parquet(OUT/'wide_scores.parquet',index=False)
    rows=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        g=pd.concat(pd.read_parquet(f,filters=[('signal_date','>=',q.start_time),('signal_date','<=',q.end_time)]) for f in sorted(WIDE_CACHE.glob('domain_[0-9]*.parquet'))).sort_values(ci.KEY)
        proto=pooled[pooled.exit_idx<days.searchsorted(q.start_time)].copy()
        # This arm changes only the target ranking in pooled training.
        group=proto.groupby(['signal_date','in300']).h10
        proto['y']=group.rank()/(group.transform('size')+1)-.5
        bridge=ci.ridge(proto,ci.COLS,'y')
        original=pd.read_parquet(EP42/'events/results/features'/f'{q}.parquet')
        bridge_sc=original[keys].assign(label_only=ci.predict(original[ci.COLS],bridge))
        fold=[]
        for domain,gg in g.groupby('in300'):
            fit=local[local.in300.eq(domain)&local.exit_idx.lt(days.searchsorted(q.start_time))].copy()
            group=fit.groupby('signal_date').h10
            fit['y']=group.rank()/(group.transform('size')+1)-.5
            r=ci.ridge(fit,ci.COLS,'y')
            fold.append(gg[keys+['in300']].assign(domain_R=ci.predict(gg[ci.COLS],r)))
            audit.append(dict(quarter=str(q),inside=domain,training=len(fit),scored=len(gg),last_maturity=days[fit.exit_idx.max()]))
        rows.append(pd.concat(fold).merge(bridge_sc,on=keys,how='outer',validate='1:1'))
    pd.concat(rows).to_parquet(OUT/'domain_scores.parquet',index=False)
    pd.DataFrame(audit).to_csv(OUT/'domain_folds.csv',index=False)
    print('domain scores completed',flush=True)

if __name__=='__main__':main()

