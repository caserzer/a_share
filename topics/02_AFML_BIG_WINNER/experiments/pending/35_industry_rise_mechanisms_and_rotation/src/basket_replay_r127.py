"""Cutoff-bounded local L1 reconstruction; append rejects historical revisions."""
import pandas as pd
from common import *
from cutoff_features_r102 import DAILY,regenerate


def append_verified(old,new):
    old=old.copy();new=new.copy()
    old['date']=pd.to_datetime(old.date).astype('datetime64[ns]')
    new['date']=pd.to_datetime(new.date).astype('datetime64[ns]')
    keys=KEY+['date']
    for f in [old,new]:
        if f.duplicated(keys).any():raise ValueError('duplicate identity')
    a=old.set_index(keys).sort_index();b=new.set_index(keys).sort_index()
    common=a.index.intersection(b.index)
    try:pd.testing.assert_frame_equal(a.loc[common],b.loc[common],check_exact=True)
    except AssertionError as e:raise ValueError('historical revision requires new version') from e
    extra=b.loc[~b.index.isin(a.index)].reset_index()
    if len(old) and extra.date.le(old.date.max()).any():raise ValueError('historical insertion requires new version')
    return pd.concat([old,extra],ignore_index=True).sort_values(keys).reset_index(drop=True)


def matrices(stocks,days):
    month=days.to_period('M');anchors=pd.Series(np.arange(len(days)),index=month).groupby(level=0).max()
    prev=np.array([anchors.get(p-1,-1) for p in month]);safe=np.maximum(prev,0)
    ids=sorted(stocks);relative=np.full((len(days),len(ids)),np.nan,dtype=np.float32)
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
    if m.duplicated(['month','security_id']).any():raise ValueError('duplicate L1 membership')
    members=set(m.security_id)
    stocks={s:f[f.date.le(cutoff)] for s,f in stocks.items() if s in members}
    for f in stocks.values():
        if f.date.duplicated().any():raise ValueError('duplicate stock date')
    ids,relative,breadth=matrices(stocks,days);sid_i={s:i for i,s in enumerate(ids)}
    month=days.to_period('M');anchors=pd.Series(np.arange(len(days)),index=month).groupby(level=0).max()
    records=[]
    for code,g in m.groupby('industry_code'):
        prior_end=None;prior_nav=np.nan;pieces=[]
        for mo,mg in g.groupby('month',sort=True):
            ix=np.flatnonzero(month==mo+1)
            if not len(ix) or mo+1<pd.Period('2022-01'):continue
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
        f['block']=f.day_i.diff().ne(1).cumsum();f['era']='SW2021';f['level']='L1';f['industry_code']=code;records.append(f[DAILY])
    return pd.concat(records,ignore_index=True).sort_values(KEY+['date']).reset_index(drop=True)


def run():
    out=ROOT/'outputs/r127';out.mkdir(exist_ok=True)
    ap=ROOT/'data/l1_assignments.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
    audit=EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json'
    source=json.loads(audit.read_text());m=pd.read_parquet(ap);market=pd.read_parquet(bp).close
    paths={Path(p).stem:Path(p) for p in source['reads'] if '/normalized/prices_qfq/' in p}
    reads={str(p):sha(p) for p in [ap,bp,audit,Path(__file__),ROOT/'src/cutoff_features_r102.py',ROOT/'src/build_panel.py',ROOT/'protocols/r127.json']}
    stocks={}
    for sid in sorted(m.security_id.unique()):
        p=paths[sid];digest=sha(p);assert digest==source['reads'][str(p)];reads[str(p)]=digest
        stocks[sid]=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id'])
    print('VERIFIED',len(stocks),'stock partitions',flush=True)
    results=[];previous=None
    for cutoff in json.loads((ROOT/'protocols/r127.json').read_text())['cutoffs']:
        f=rebuild(m,stocks,market.index,cutoff);fp=out/f'daily_{cutoff}.parquet';f.to_parquet(fp,index=False)
        features=regenerate(f,market,cutoff);p=out/f'features_{cutoff}.parquet';features.to_parquet(p,index=False)
        if previous is not None:pd.testing.assert_frame_equal(append_verified(previous,f),f)
        results.append(dict(cutoff=cutoff,rows=len(f),industries=f.industry_code.nunique(),feature_rows=len(features),sha256=sha(fp),feature_sha256=sha(p),appended_rows=None if previous is None else len(f)-len(previous)))
        previous=f;print(results[-1],flush=True)
    js(out/'receipt.json',dict(reads=reads,results=results,stock_partitions=len(stocks),quality='Historical-proxy',new_observations=0,method='full-prefix rebuild with revision-rejecting append validation'))

if __name__=='__main__':run()
