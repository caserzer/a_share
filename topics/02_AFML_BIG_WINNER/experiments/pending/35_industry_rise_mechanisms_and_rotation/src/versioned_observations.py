"""Local immutable observations and separately matured outcomes. No network."""
import argparse, os, shutil, tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
from common import *
from build_panel import price_features

FEATURES=['mom20','mom60','vol20','dd60','breadth21','breadth63','coverage','members','membership_asof']

def digest_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()

def check_capture(asof,intent,now):
    local=now.astimezone(ZoneInfo('Asia/Shanghai'));day=pd.Timestamp(asof).date()
    if day>local.date():raise ValueError('future observation date')
    if intent=='forward' and (day!=local.date() or local.hour<15):
        raise ValueError('forward capture requires same local date after15:00; no backdating')
    return 'historical_replay' if intent=='historical' else 'forward_candidate'

def source_copy(source,store):
    source=Path(source);digest=sha(source);target=store/'sources'/f'{digest}{source.suffix}'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(target)!=digest:raise ValueError('immutable source corrupted')
    else:
        fd,name=tempfile.mkstemp(dir=target.parent);os.close(fd)
        try:
            shutil.copyfile(source,name)
            if sha(name)!=digest:raise ValueError('source changed during copy')
            os.replace(name,target)
        finally:
            if Path(name).exists():Path(name).unlink()
    return dict(original_path=str(source.resolve()),path=str(target.resolve()),sha256=digest)

def observations(daily,market,catalog,asof,era):
    asof=pd.Timestamp(asof)
    if asof not in market.index:raise ValueError('asof absent from exchange calendar')
    if daily.duplicated(KEY+['date']).any():raise ValueError('duplicate industry-date')
    prefix=daily[(daily.date<=asof)&daily.era.eq(era)]
    rows=[]
    for _,g in prefix.groupby(KEY+['block'],sort=False):
        f=price_features(g);rows.append(f[f.date.eq(asof)][KEY+['date']+FEATURES])
    observed=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=KEY+['date']+FEATURES)
    base=catalog[catalog.era.eq(era)][KEY+['industry_name']].copy()
    if base.duplicated(KEY).any():raise ValueError('duplicate catalog identity')
    identified=observed[KEY+['date']].merge(base[KEY],on=KEY,how='left',indicator=True)
    quarantined=identified.loc[identified._merge.eq('left_only'),KEY+['date']].copy()
    result=base.merge(observed,on=KEY,how='left',validate='one_to_one');result['asof']=asof
    ready=result[['mom20','mom60','vol20','dd60']].notna().all(axis=1)&result.coverage.ge(.8)&result.members.ge(5)
    result['price_ready']=ready;result['price_score']=np.nan;result['price_rank']=np.nan
    for _,g in result[ready].groupby(['era','level']):
        rank=g[['mom20','mom60','vol20','dd60']].apply(centered_rank)
        score=((rank.mom20+rank.mom60)/2-rank.vol20+rank.dd60)/3
        result.loc[g.index,'price_score']=score
        result.loc[g.index,'price_rank']=score.rank(ascending=False,method='min')
    result['status']=np.where(ready,'research_price_observation',np.where(result.date.isna(),'missing_basket_at_asof','insufficient_price_features'))
    for field in ['industry_mechanism','expectation_evidence','holdings_crowding','economic_stage']:
        result[field]='not_verified_in_this_snapshot'
    result=result.sort_values(KEY).reset_index(drop=True)
    result.attrs['quarantined']=quarantined.to_dict('records')
    return result

def verify_bundle(bundle):
    bundle=Path(bundle);m=json.loads((bundle/'manifest.json').read_text())
    check=dict(m);seal_hash=check.pop('seal_sha256',None)
    if digest_json(check)!=seal_hash:raise ValueError('manifest integrity mismatch')
    if m['identity']['sources']!={k:v['sha256'] for k,v in m['sources'].items()}:raise ValueError('source identity mismatch')
    for entry in m['sources'].values():
        if sha(entry['path'])!=entry['sha256']:raise ValueError('source integrity mismatch')
    for name,digest in m['outputs'].items():
        if sha(bundle/name)!=digest:raise ValueError('output integrity mismatch')
    if digest_json(m['identity'])!=m['bundle_id']:raise ValueError('manifest identity mismatch')
    return m

def seal(store,category,identity,sources,frames,metadata):
    parent=Path(store)/category;parent.mkdir(parents=True,exist_ok=True);bid=digest_json(identity);target=parent/bid
    if target.exists():verify_bundle(target);return target
    temp=Path(tempfile.mkdtemp(prefix='.pending-',dir=parent))
    try:
        hashes={}
        for name,frame in frames.items():
            if name.endswith('.parquet'):frame.to_parquet(temp/name,index=False)
            else:frame.to_csv(temp/name,index=False)
            hashes[name]=sha(temp/name)
        manifest=dict(bundle_id=bid,identity=identity,sources=sources,outputs=hashes,**metadata)
        manifest['seal_sha256']=digest_json(manifest)
        js(temp/'manifest.json',manifest)
        os.rename(temp,target)
    finally:
        if temp.exists():shutil.rmtree(temp)
    verify_bundle(target);return target

def capture(store,daily_paths,market_path,catalog_path,asof,era='SW2021',intent='historical'):
    now=datetime.now(timezone.utc);kind=check_capture(asof,intent,now);store=Path(store)
    sources={f'daily_{i}':source_copy(path,store) for i,path in enumerate(daily_paths)}
    for name,path in [('market',market_path),('catalog',catalog_path),('protocol',ROOT/'protocols/r18.json'),('code',Path(__file__)),('features_code',ROOT/'src/build_panel.py'),('common_code',ROOT/'src/common.py')]:
        sources[name]=source_copy(path,store)
    daily=pd.concat([pd.read_parquet(sources[f'daily_{i}']['path']) for i in range(len(daily_paths))],ignore_index=True)
    market=pd.read_parquet(sources['market']['path']).close
    today=now.astimezone(ZoneInfo('Asia/Shanghai')).date()
    if daily.date.max().date()>today or market.index.max().date()>today:raise ValueError('future source observations')
    frame=observations(daily,market,pd.read_csv(sources['catalog']['path']),asof,era)
    quarantine=pd.DataFrame(frame.attrs.pop('quarantined'),columns=KEY+['date'])
    identity=dict(asof=str(pd.Timestamp(asof).date()),era=era,intent=intent,sources={k:v['sha256'] for k,v in sources.items()})
    return seal(store,'observations',identity,sources,{'observations.parquet':frame,'observations.csv':frame,'quarantined.csv':quarantine},
        dict(created_at=now.isoformat(),capture_kind=kind,source_end=str(market.index.max().date()),rows=len(frame),price_ready=int(frame.price_ready.sum()),quarantined_rows=len(quarantine),
             quality='Historical-proxy; original release versions unverified',score_meaning='research observation rank, not validated signal',
             next_update='manual after new local sources; no scheduler installed'))

def evaluate_rows(observed,daily,market,asof):
    calendar=pd.DatetimeIndex(market.index);calendar=calendar[calendar<=pd.Timestamp(asof)]
    lookup={key:g.set_index('date').sort_index() for key,g in daily.groupby(KEY)};rows=[]
    for row in observed.itertuples():
        origin=pd.Timestamp(row.asof)
        for h in [20,60]:
            rec={k:getattr(row,k) for k in KEY}
            rec.update(origin=origin,horizon=h,price_ready=row.price_ready,price_score=row.price_score,entry_date=pd.NaT,maturity=pd.NaT,excess=np.nan,absolute_return=np.nan,status='pending_market_sessions')
            if origin not in calendar:rec['status']='origin_missing_from_calendar';rows.append(rec);continue
            i=calendar.get_loc(origin)
            if i+1<len(calendar):rec['entry_date']=calendar[i+1]
            if i+h+1>=len(calendar):rows.append(rec);continue
            dates=calendar[i+1:i+h+2];rec['maturity']=dates[-1];g=lookup.get(tuple(getattr(row,k) for k in KEY))
            if g is None:rec['status']='missing_identity';rows.append(rec);continue
            g=g.reindex(dates)
            if g.nav.isna().any() or g.block.nunique()!=1 or not g.nav.gt(0).all():
                rec['status']='missing_or_discontinuous_price_path';rows.append(rec);continue
            ret=g.nav.iloc[-1]/g.nav.iloc[0]-1;bm=market.loc[dates[-1]]/market.loc[dates[0]]-1
            rec.update(status='mature',absolute_return=ret,excess=ret-bm);rows.append(rec)
    return pd.DataFrame(rows)

def evaluate(store,bundle,daily_paths,market_path,asof):
    now=datetime.now(timezone.utc);check_capture(asof,'historical',now);original=verify_bundle(bundle)
    obs=pd.read_parquet(Path(bundle)/'observations.parquet');store=Path(store)
    sources={f'daily_{i}':source_copy(path,store) for i,path in enumerate(daily_paths)}
    sources['market']=source_copy(market_path,store);sources['evaluation_code']=source_copy(Path(__file__),store)
    daily=pd.concat([pd.read_parquet(sources[f'daily_{i}']['path']) for i in range(len(daily_paths))],ignore_index=True)
    market=pd.read_parquet(sources['market']['path']).close
    if daily.duplicated(KEY+['date']).any() or not market.index.is_unique:raise ValueError('duplicate evaluation identity/date')
    old=pd.concat([pd.read_parquet(v['path']) for k,v in original['sources'].items() if k.startswith('daily_')],ignore_index=True)
    cutoff=pd.Timestamp(original['identity']['asof'])
    revisions=old[old.date<=cutoff][KEY+['date','nav']].merge(daily[daily.date<=cutoff][KEY+['date','nav']],on=KEY+['date'],how='outer',suffixes=('_old','_new'),indicator=True)
    changed=int((~np.isclose(revisions.nav_old,revisions.nav_new,equal_nan=True)|revisions._merge.ne('both')).sum())
    old_market=pd.read_parquet(original['sources']['market']['path']).close
    market_comparison=pd.concat([old_market.loc[:cutoff].rename('old'),market.loc[:cutoff].rename('new')],axis=1)
    market_changed=int((~np.isclose(market_comparison.old,market_comparison.new,equal_nan=True)).sum())
    result=evaluate_rows(obs,daily,market,asof);result['evaluation_kind']='historical_replay'
    if original['capture_kind']=='forward_candidate':
        captured=pd.Timestamp(original['created_at'])
        entry=pd.to_datetime(result.entry_date).dt.tz_localize('Asia/Shanghai')+pd.Timedelta(hours=15)
        result.loc[entry.notna()&(entry>captured),'evaluation_kind']='prospective_chronology_only'
    identity=dict(snapshot=original['bundle_id'],asof=str(pd.Timestamp(asof).date()),sources={k:v['sha256'] for k,v in sources.items()})
    return seal(store,'evaluations',identity,sources,{'outcomes.parquet':result,'outcomes.csv':result},
        dict(created_at=now.isoformat(),snapshot_path=str(Path(bundle).resolve()),historical_price_prefix_changed_rows=changed,market_prefix_changed_rows=market_changed,
             warning='chronology does not certify PIT inputs or investment validity; revisions recorded separately'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['capture','evaluate','verify'])
    parser.add_argument('--asof');parser.add_argument('--bundle');parser.add_argument('--intent',choices=['historical','forward'],default='historical');parser.add_argument('--era',default='SW2021')
    parser.add_argument('--store',default=str(ROOT/'data/update_store'))
    parser.add_argument('--daily',nargs='+',default=[str(CACHE/'forecast_v5/daily_industries.parquet'),str(ROOT/'data/l1_daily.parquet')])
    parser.add_argument('--market',default=str(CACHE/'forecast_v5/CSI_ALL.parquet'));parser.add_argument('--catalog',default=str(ROOT/'outputs/universe_current.csv'));args=parser.parse_args()
    if args.action=='verify':print(verify_bundle(args.bundle)['bundle_id']);return
    if not args.asof:parser.error('--asof required')
    result=capture(args.store,args.daily,args.market,args.catalog,args.asof,args.era,args.intent) if args.action=='capture' else evaluate(args.store,args.bundle,args.daily,args.market,args.asof)
    print(result)
if __name__=='__main__':main()
