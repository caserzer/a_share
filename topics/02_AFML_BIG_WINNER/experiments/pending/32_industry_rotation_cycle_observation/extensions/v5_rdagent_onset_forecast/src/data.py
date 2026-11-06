"""Daily fixed-month baskets, using only the preceding month's membership."""
import json
import numpy as np
import pandas as pd
from common import CACHE, OUT, V4, V2, KEY, BENCHMARKS, sha, js, freeze_inputs


def frequency_dates(days):
    days = pd.DatetimeIndex(days)
    f = pd.DataFrame({'date':days})
    weeks = f.groupby(f.date.dt.to_period('W-FRI')).date.max()
    # A week may end Thursday because Friday is a holiday; require calendar Friday elapsed.
    weeks = weeks[[p.end_time.normalize() <= days.max() for p in weeks.index]]
    monthly = f.groupby(f.date.dt.to_period('M')).date.max()
    monthly = monthly[[p.end_time.normalize() <= days.max() for p in monthly.index]]
    anchor = pd.Timestamp('2017-01-06')
    bi = weeks[[((p.end_time.normalize()-anchor).days//7)%2 == 0 for p in weeks.index]]
    return {'W':pd.DatetimeIndex(weeks), 'BW':pd.DatetimeIndex(bi), 'M':pd.DatetimeIndex(monthly)}


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True); freeze_inputs()
    identity = json.loads((V4/'outputs/audits/inputs.json').read_text())
    release = __import__('pathlib').Path(identity['price_release'])
    old = CACHE.parent/'extension_v2/products'
    assignment_path = old/'assignments.parquet'
    joined = pd.read_parquet(assignment_path)
    days = pd.DatetimeIndex(pd.read_parquet(release/'inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    ids = sorted(joined.security_id.unique())
    sid_to_i = {s:i for i,s in enumerate(ids)}
    month = days.to_period('M')
    anchors = pd.Series(np.arange(len(days)), index=month).groupby(level=0).max()
    prev = np.array([anchors.get(m-1, -1) for m in month])
    daily_rel = np.full((len(days),len(ids)), np.nan)
    breadth = {w:np.full(daily_rel.shape,np.nan,dtype=np.float32) for w in [21,63]}
    vr = np.full(daily_rel.shape,np.nan,dtype=np.float32)
    reads = {str(assignment_path):sha(assignment_path)}
    assert reads[str(assignment_path)] == json.loads((V4/'../v3_screening_review/outputs/audits/input_identity.json').resolve().read_text())['assignment_sha256']
    for i,sid in enumerate(ids):
        rel = 'normalized/prices_qfq/'+sid+'.parquet'; p=release/rel
        h=sha(p); assert h == identity['daily_read_files'][rel]
        reads[str(p)]=h
        b=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id','volume']).set_index('date').reindex(days)
        price=pd.to_numeric(b.qfq_close).where(b.close_conflict.eq(False)&pd.to_numeric(b.qfq_close).gt(0)).to_numpy(float)
        chain=b.factor_chain_id.fillna('__MISSING__').to_numpy()
        safe=np.maximum(prev,0)
        ok=(prev>=0)&(chain==chain[safe])&(chain!='__MISSING__')
        with np.errstate(divide='ignore',invalid='ignore'):
            daily_rel[:,i]=np.where(ok,price/price[safe]-1,np.nan)
            for w in [21,63]:
                v=price[w:]/price[:-w]-1
                valid=np.isfinite(v)&(chain[w:]==chain[:-w])&(chain[w:]!='__MISSING__')
                breadth[w][w:,i]=np.where(valid,(v>0).astype(float),np.nan)
            vol=pd.to_numeric(b.volume).where(pd.to_numeric(b.volume).gt(0))
            vr[:,i]=(vol/vol.rolling(63,min_periods=42).mean()).clip(0,10).to_numpy()
        if (i+1)%1000==0: print('verified daily partitions',i+1,'/',len(ids),flush=True)
    records=[]; checks=[]
    for key,j in joined.groupby(KEY,sort=True):
        pieces=[]; prior_end=None; prior_nav=np.nan
        for m,g in j.groupby('month',sort=True):
            target=m+1
            if (key[0]=='SW2014' and target>pd.Period('2021-11')) or (key[0]=='SW2021' and target<pd.Period('2022-01')):
                continue
            ix=np.flatnonzero(month==target)
            if not len(ix): continue
            ai=anchors[m]; si=np.array([sid_to_i[s] for s in g.security_id]); members=len(si)
            unresolved=int(g.unresolved.max()); x=daily_rel[np.ix_(ix,si)]
            count=np.isfinite(x).sum(axis=1); cov=count/(members+unresolved)
            means=np.divide(np.nansum(x,axis=1),count,out=np.full(len(ix),np.nan),where=count>0)
            scale=prior_nav if prior_end==ai and np.isfinite(prior_nav) else 1.
            nav=scale*(1+means); nav[(members<5)|(cov<.8)]=np.nan
            def avg(mat):
                x=mat[np.ix_(ix,si)]; n=np.isfinite(x).sum(axis=1)
                return np.divide(np.nansum(x,axis=1),n,out=np.full(len(ix),np.nan),where=n>=.8*(members+unresolved))
            piece=pd.DataFrame(dict(date=days[ix],nav=nav,coverage=cov,members=members,
                membership_asof=days[ai],breadth21=avg(breadth[21]),breadth63=avg(breadth[63]),volume_ratio=avg(vr),day_i=ix))
            # Origin anchor exists at the prior month end, from that day's membership.
            if prior_end!=ai or not np.isfinite(prior_nav):
                pieces.append(pd.DataFrame([dict(date=days[ai],nav=1.,coverage=np.nan,members=members,
                    membership_asof=days[ai],day_i=ai)]))
            pieces.append(piece)
            if target < days.max().to_period('M'):
                checks.append(dict(era=key[0],level=key[1],industry_code=key[2],month=str(target),
                    observed_month_return=means[-1] if members>=5 and cov[-1]>=.8 else np.nan))
            prior_end=int(ix[-1]);prior_nav=nav[-1]
        if not pieces:continue
        f=pd.concat(pieces,ignore_index=True).sort_values('date').drop_duplicates('date',keep='first')
        f=f[f.nav.notna()].copy()
        f['block']=f.day_i.diff().ne(1).cumsum()
        for k,v in zip(KEY,key):f[k]=v
        f['industry_name']=j.industry_name.iloc[-1]
        records.append(f)
    daily=pd.concat(records,ignore_index=True).sort_values(KEY+['date'])
    compare=pd.DataFrame(checks).merge(pd.read_csv(V4/'outputs/details/industry_monthly_returns.csv.gz'),on=KEY+['month'],how='outer',validate='one_to_one',indicator=True)
    full=compare[compare.month.lt('2026-10')]
    assert full._merge.eq('both').all()
    assert np.allclose(full.observed_month_return,full.return_value,equal_nan=True,rtol=1e-10,atol=1e-10)
    daily.to_parquet(CACHE/'daily_industries.parquet',index=False)
    js(OUT/'daily_input_audit.json',dict(reads=reads,calendar_start=str(days.min().date()),calendar_end=str(days.max().date()),
        daily_industry_rows=len(daily),stock_partitions=len(ids),monthly_reconciliation_rows=len(full),monthly_reconciliation='PASS',
        daily_sha256=sha(CACHE/'daily_industries.parquet'),quality='Historical-proxy',strict_PIT='BLOCKED_DATA'))
    for name,code in BENCHMARKS.items():
        p=old.parent/'sources'/f'{code}.parquet'; b=pd.read_parquet(p).set_index('date').reindex(days)
        assert b.close.notna().all()
        b.to_parquet(CACHE/f'{name}.parquet')
    js(OUT/'schedule.json',{k:[str(t.date()) for t in v] for k,v in frequency_dates(days).items()})
    print('daily industry rows',len(daily),'monthly identity PASS',len(full),flush=True)


def features():
    d=pd.read_parquet(CACHE/'daily_industries.parquet')
    chunks=[]
    for _,g in d.groupby(KEY+['block'],sort=False):
        g=g.sort_values('date').copy(); p=g.nav
        for w in [5,21,63,126,252]:g[f'mom{w}']=p/p.shift(w)-1
        for w in [21,63,126,252]:g[f'dd{w}']=p/p.rolling(w,min_periods=w).max()-1
        ret=p.pct_change(fill_method=None)
        for w in [21,63]:g[f'vol{w}']=ret.rolling(w,min_periods=w).std()*np.sqrt(252)
        g['log_members']=np.log(g.members)
        chunks.append(g)
    d=pd.concat(chunks,ignore_index=True)
    schedule=json.loads((OUT/'schedule.json').read_text())
    snapshots=[]
    for freq,dates in schedule.items():
        f=d[d.date.isin(pd.to_datetime(dates))].copy();f['frequency']=freq
        snapshots.append(f)
    f=pd.concat(snapshots,ignore_index=True).reset_index(drop=True)
    f['row_id']=np.arange(len(f));f['features_ready']=f.mom63.notna()&f.coverage.ge(.8)
    assert (f.membership_asof<=f.date).all()
    f.to_parquet(CACHE/'features.parquet',index=False)
    js(OUT/'feature_audit.json',dict(rows=len(f),ready=int(f.features_ready.sum()),
        max_feature_date_equals_origin=True,features_sha256=sha(CACHE/'features.parquet'),
        frequency_rows=f.groupby('frequency').size().to_dict(),
        frequency_ready=f.groupby('frequency').features_ready.sum().astype(int).to_dict()))
    print('feature snapshots',len(f),'ready',int(f.features_ready.sum()),flush=True)


if __name__=='__main__':
    import sys
    if '--features-only' not in sys.argv:prepare()
    features()
