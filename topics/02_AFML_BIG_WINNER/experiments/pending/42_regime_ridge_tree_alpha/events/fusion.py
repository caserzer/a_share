from event_account import *
from prepare_features import original
import json
from scipy.stats import rankdata
from scipy.linalg import lstsq
raw_names=['eps20','eps60','target20','coverage_delta','sue20']
def centered(v):
    out=np.zeros(len(v));mask=np.isfinite(v)
    if mask.any():out[mask]=rankdata(v[mask])/(mask.sum()+1)-.5
    return out
def residual(x,v):
    mask=np.isfinite(v);out=np.zeros(len(v))
    if mask.sum()>1 and np.ptp(v[mask])>0:
        z=x[mask]; y=v[mask]
        coef,_,rank,_=lstsq(z,y,cond=1e-10,lapack_driver='gelsd',check_finite=False)
        if rank<len(y):
            diff=y-z@coef
            if np.ptp(diff)>1e-9*max(np.ptp(y),1.):out[mask]=centered(diff)
    return out
def increments(g,model):
    vals=g[original.COLS].to_numpy(float)
    x=(np.where(np.isfinite(vals),vals,model['median'])-model['mean'])/model['sd'];x=np.column_stack([np.ones(len(g)),x])
    result={}; masks={}
    for n in raw_names:
        v=g[n].to_numpy(float);mask=np.isfinite(v);masks[n]=mask
        result[n]=residual(x,v)
        result[n+'_raw']=centered(v)
        result[n+'_flag']=centered(mask.astype(float))
    ma=masks['eps20'];mb=masks['sue20'];n=ma.astype(int)+mb
    result['mixed']=(result['eps20']+result['sue20'])/np.maximum(n,1)
    result['mixed_flag']=centered((n>0).astype(float))
    result['both_mixed']=np.where(n==2,result['mixed'],0.)
    result['both_eps']=np.where(n==2,result['eps20'],0.)
    result['both_sue']=np.where(n==2,result['sue20'],0.)
    result['coverage_current']=centered(g.coverage_current.to_numpy())
    result['target_momentum']=centered(g.mom20.where(masks['target20']).to_numpy())
    return result
def main():
    s=Study(False);m=s.m
    src=pd.read_parquet(OUT/'source_daily_signals.parquet')
    sig=src.set_index(['signal_date','instrument']).sort_index()
    assert sig.index.is_unique
    wide=pd.read_parquet(engine.LOCAL/'wide_features.parquet');weeks=pd.read_parquet(engine.PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    wide=wide[wide.weekly_ok & wide.signal_date.isin(weeks)&wide.h10.notna()].copy()
    wide['target_rank']=wide.groupby('signal_date').h10.transform(lambda x:x.rank()/(len(x)+1)-.5)
    wide=wide.join(sig,on=['signal_date','instrument'])
    fitdata=[];dates=[];qmetrics=[];plans={'ridge':s.top};cover=[];inc_records=[]
    for q,w in wide.groupby(wide.signal_date.dt.to_period('Q'),sort=True):
        cut=m.days.searchsorted(q.start_time);d=wide[wide.exit_idx<cut]
        if len(d)<800:continue
        path=original.OUT800/'models/refit'/str(q)/'ridge.json'
        model=json.loads(path.read_text()) if path.exists() else original.ridge(d,original.COLS,'target_rank')
        for date,g in w.groupby('signal_date'):
            inc=increments(g,model); r=original.predict(g[original.COLS],model);y=g.target_rank.to_numpy()-r
            for name,v in inc.items():
                # Maturity may differ for paused names; retain the exact label completion index.
                for exit_idx in np.unique(g.exit_idx):
                    valid=g.exit_idx.to_numpy()==exit_idx
                    fitdata.append((int(exit_idx),date,name,np.dot(v[valid],v[valid]),np.dot(v[valid],y[valid]),np.sum((v!=0)&valid)))
    train=pd.DataFrame(fitdata,columns='exit_idx signal_date arm xx xy nonzero'.split())
    folder=OUT/'fusion';folder.mkdir(exist_ok=True);train.to_parquet(folder/'calibration_oof.parquet',index=False)
    for file in sorted((OUT/'features').glob('*.parquet')):
        q=pd.Period(file.stem);cut=m.days.searchsorted(q.start_time)
        w=pd.read_parquet(file).join(sig,on=['signal_date','instrument'])
        model=json.loads((original.OUT800/'models/refit'/str(q)/'ridge.json').read_text())
        t=train[train.exit_idx<cut].groupby('arm').agg({'xx':'sum','xy':'sum','nonzero':'sum','exit_idx':'max'})
        gamma=(t.xy/t.xx.where(t.xx>0)).fillna(0).clip(0,1)
        for n,row in t.iterrows():qmetrics.append((str(q),n,gamma.at[n],int(row.nonzero),int(row.exit_idx),cut))
        for dt,g in w.groupby('signal_date'):
            e=int(g.entry_idx.iat[0]);ids=m.symbols.get_indexer(g.instrument)
            base=g.R.to_numpy();k=len(s.top[e]);inc=increments(g,model)
            for n,v in inc.items():
                score=base+gamma.get(n,0.)*v
                chosen=ids[np.lexsort((ids,score))[::-1][:k]]
                plans.setdefault(n,{})[e]=chosen
                cover.append((e,n,len(ids),int((v!=0).sum()),len(set(chosen)-set(s.top[e])),float(gamma.get(n,0.))))
            packed=g[['signal_date','instrument','R',*raw_names]].copy()
            for n in raw_names+['mixed']:packed['inc_'+n]=inc[n]
            inc_records.append(packed)
    pd.concat(inc_records).to_parquet(folder/'daily_sources_and_increments.parquet',compression='zstd',index=False)
    pd.DataFrame(qmetrics,columns='quarter arm gamma nonzero_training latest_mature_idx quarter_start_idx'.split()).to_csv(folder/'folds.csv',index=False)
    pd.DataFrame(cover,columns='entry_idx arm pool nonzero_increment changed_seats gamma'.split()).to_parquet(folder/'support.parquet',index=False)
    comp=[(n,'ridge') for n in plans if n!='ridge']+[(n,n+'_raw') for n in raw_names]+[(n,n+'_flag') for n in raw_names]+[('mixed','eps20'),('mixed','sue20'),('mixed','mixed_flag'),('both_mixed','both_eps'),('both_mixed','both_sue'),('target20','target_momentum'),('coverage_delta','coverage_current')]
    s.run('fusion',plans,comp)
if __name__=='__main__':main()
