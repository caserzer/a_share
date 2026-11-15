"""L2/L3 cutoff reconstruction preserves EP32 precision and classification rules."""
import pandas as pd
from common import *
from cutoff_features_r102 import DAILY,regenerate

def matrices(stocks,days):
    month=days.to_period('M');anchors=pd.Series(np.arange(len(days)),index=month).groupby(level=0).max()
    prev=np.array([anchors.get(p-1,-1) for p in month]);safe=np.maximum(prev,0)
    ids=sorted(stocks);relative=np.full((len(days),len(ids)),np.nan,dtype=np.float64)
    breadth={h:np.full(relative.shape,np.nan,dtype=np.float32) for h in [21,63]}
    for j,sid in enumerate(ids):
        f=stocks[sid].set_index('date').reindex(days)
        price=pd.to_numeric(f.qfq_close).where(f.close_conflict.eq(False)&pd.to_numeric(f.qfq_close).gt(0)).to_numpy(float)
        chain=f.factor_chain_id.fillna('__MISSING__').to_numpy();ok=(prev>=0)&(chain==chain[safe])&(chain!='__MISSING__')
        with np.errstate(divide='ignore',invalid='ignore'):
            relative[:,j]=np.where(ok,price/price[safe]-1,np.nan)
            for h in breadth:
                change=price[h:]/price[:-h]-1;valid=np.isfinite(change)&(chain[h:]==chain[:-h])&(chain[h:]!='__MISSING__')
                breadth[h][h:,j]=np.where(valid,(change>0).astype(float),np.nan)
    return ids,relative,breadth


def rebuild(assignments,stocks,calendar,cutoff):
    cutoff=pd.Timestamp(cutoff);days=pd.DatetimeIndex(calendar[calendar<=cutoff]).sort_values()
    if not days.is_unique:raise ValueError('duplicate calendar')
    m=assignments[assignments.month.lt(cutoff.to_period('M'))].copy()
    if m.duplicated(KEY+['month','security_id']).any():raise ValueError('duplicate industry membership')
    members=set(m.security_id)
    stocks={s:f[f.date.le(cutoff)] for s,f in stocks.items() if s in members}
    for f in stocks.values():
        if f.date.duplicated().any():raise ValueError('duplicate stock date')
    ids,relative,breadth=matrices(stocks,days);sid_i={s:i for i,s in enumerate(ids)}
    month=days.to_period('M');anchors=pd.Series(np.arange(len(days)),index=month).groupby(level=0).max()
    records=[]
    for key,g in m.groupby(KEY):
        prior_end=None;prior_nav=np.nan;pieces=[]
        for mo,mg in g.groupby('month',sort=True):
            ix=np.flatnonzero(month==mo+1)
            if not len(ix):continue
            if (key[0]=='SW2014' and mo+1>pd.Period('2021-11')) or (key[0]=='SW2021' and mo+1<pd.Period('2022-01')):continue
            if mo not in anchors:raise ValueError('missing prior month anchor')
            ai=anchors[mo];si=[sid_i[s] for s in mg.security_id];n=len(si);den=n+int(mg.unresolved.max())
            x=relative[np.ix_(ix,si)];count=np.isfinite(x).sum(axis=1);coverage=count/den
            means=np.divide(np.nansum(x,axis=1),count,out=np.full(len(ix),np.nan),where=count>0)
            scale=prior_nav if prior_end==ai and np.isfinite(prior_nav) else 1.
            nav=scale*(1+means);nav[(coverage<.8)|(n<5)]=np.nan
            f=pd.DataFrame(dict(date=days[ix],nav=nav,coverage=coverage,members=n,day_i=ix))
            for h,values in breadth.items():
                v=values[np.ix_(ix,si)];cnt=np.isfinite(v).sum(axis=1)
                f[f'breadth{h}']=np.divide(np.nansum(v,axis=1),cnt,out=np.full(len(ix),np.nan),where=(cnt>=.8*den)&(n>=5))
            if prior_end!=ai or not np.isfinite(prior_nav):
                pieces.append(pd.DataFrame([dict(date=days[ai],nav=1.,coverage=np.nan,members=n,day_i=ai)]))
            pieces.append(f);prior_end=ix[-1];prior_nav=nav[-1]
        if not pieces:continue
        f=pd.concat(pieces,ignore_index=True).sort_values('date').drop_duplicates('date');f=f[f.nav.notna()].copy()
        f['block']=f.day_i.diff().ne(1).cumsum()
        for k,v in zip(KEY,key):f[k]=v
        records.append(f[DAILY])
    return pd.concat(records,ignore_index=True).sort_values(KEY+['date']).reset_index(drop=True)


def compare(actual,reference):
    keys=KEY+['date'];a=actual.set_index(keys).sort_index();b=reference.set_index(keys).sort_index()
    common=a.index.intersection(b.index);missing=b.loc[~b.index.isin(a.index)].reset_index();extra=a.loc[~a.index.isin(b.index)].reset_index()
    cols=[c for c in DAILY if c not in keys]
    av=a.loc[common,cols].to_numpy(float);bv=b.loc[common,cols].to_numpy(float)
    equal=np.isclose(av,bv,atol=1e-12,rtol=1e-12,equal_nan=True)
    bad=pd.DataFrame(common[~equal.all(axis=1)].tolist(),columns=keys)
    return dict(shared=len(common),missing=len(missing),extra=len(extra),different_shared_rows=len(bad)),missing,extra,bad


def run():
    out=ROOT/'outputs/r128';out.mkdir(exist_ok=True)
    ap=CACHE/'extension_v2/products/assignments.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
    audit=EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json';refp=CACHE/'forecast_v5/daily_industries.parquet'
    source=json.loads(audit.read_text());m=pd.read_parquet(ap);market=pd.read_parquet(bp).close
    assert sha(ap)==source['reads'][str(ap)]
    paths={Path(p).stem:Path(p) for p in source['reads'] if '/normalized/prices_qfq/' in p}
    reads={str(p):sha(p) for p in [ap,bp,audit,refp,Path(__file__),ROOT/'src/cutoff_features_r102.py',ROOT/'src/build_panel.py',ROOT/'protocols/r128.json']}
    stocks={}
    for sid in sorted(m.security_id.unique()):
        p=paths[sid];digest=sha(p);assert digest==source['reads'][str(p)];reads[str(p)]=digest
        stocks[sid]=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id'])
    print('VERIFIED',len(stocks),'stock partitions',flush=True)
    reference=pd.read_parquet(refp,columns=DAILY);results=[];previous=None;prior_cutoff=None
    for cutoff in json.loads((ROOT/'protocols/r128.json').read_text())['cutoffs']:
        f=rebuild(m,stocks,market.index,cutoff);fp=out/f'daily_{cutoff}.parquet';f.to_parquet(fp,index=False)
        ref=reference[reference.date.le(cutoff)];comparison,missing,extra,bad=compare(f,ref)
        for name,frame in [('missing',missing),('extra',extra),('different',bad)]:frame.to_parquet(out/f'{name}_{cutoff}.parquet',index=False)
        features=regenerate(f,market,cutoff);p=out/f'features_{cutoff}.parquet';features.to_parquet(p,index=False)
        transition=None
        if previous is not None:
            transition,inserted,deleted,changed=compare(previous,f[f.date.le(prior_cutoff)])
            for name,frame in [('inserted',inserted),('deleted',deleted),('changed',changed)]:frame.to_parquet(out/f'transition_{name}_{cutoff}.parquet',index=False)
        group=f.groupby(['era','level']).agg(rows=('date','size'),industries=('industry_code','nunique')).reset_index().to_dict('records')
        results.append(dict(cutoff=cutoff,rows=len(f),groups=group,feature_rows=len(features),comparison=comparison,transition=transition,sha256=sha(fp),feature_sha256=sha(p)))
        previous=f;prior_cutoff=cutoff;print(results[-1],flush=True)
    js(out/'receipt.json',dict(reads=reads,results=results,stock_partitions=len(stocks),quality='Historical-proxy',new_observations=0))

if __name__=='__main__':run()
