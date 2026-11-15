"""Adapt repaired baskets with explicit clocks and frozen membership provenance."""
import pandas as pd
from common import *
from basket_repair_r129 import select_rows
from versioned_observations import capture, verify_bundle


def adapt(daily,assignments,calendar,cutoff):
    required=KEY+['date','known_at','source_kind','members']
    if not set(required)<=set(daily):raise ValueError('missing adapter fields')
    if daily.known_at.isna().any():raise ValueError('unknown availability clock')
    if daily.duplicated(KEY+['date']).any():raise ValueError('duplicate basket date')
    if not calendar.is_unique or not calendar.is_monotonic_increasing:raise ValueError('invalid calendar')
    d=daily[daily.date.le(pd.Timestamp(cutoff))&daily.known_at.le(pd.Timestamp(cutoff))].copy()
    if d.empty:raise ValueError('no available basket rows')
    ordinal=pd.Series(range(len(calendar)),index=calendar)
    d['day_i']=d.date.map(ordinal)
    if d.day_i.isna().any():raise ValueError('basket date absent from calendar')
    d['day_i']=d.day_i.astype('int64')
    d=pd.concat([select_rows(g,cutoff) for _,g in d.groupby(KEY)],ignore_index=True)
    d['membership_month']=d.date.dt.to_period('M')
    mask=d.source_kind.eq('observed');d.loc[mask,'membership_month']=d.loc[mask,'membership_month']-1
    a=assignments[KEY+['month','date','security_id']].copy()
    if a.duplicated(KEY+['month','security_id']).any():raise ValueError('duplicate membership')
    groups=a.groupby(KEY+['month'])
    if groups.date.nunique().ne(1).any():raise ValueError('ambiguous membership date')
    lineage=groups.agg(membership_asof=('date','first'),source_members=('security_id','size')).reset_index().rename(columns={'month':'membership_month'})
    d=d.merge(lineage,on=KEY+['membership_month'],how='left',validate='many_to_one')
    if d.membership_asof.isna().any() or d.members.ne(d.source_members).any():raise ValueError('membership provenance mismatch')
    if (d.membership_asof>d.date).any():raise ValueError('future membership date')
    return d.sort_values(KEY+['date']).reset_index(drop=True)


def run():
    out=ROOT/'outputs/r181';store=ROOT/'data/update_store_r181';protocol=ROOT/'protocols/r181.json'
    dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';ap=CACHE/'extension_v2/products/assignments.parquet';mp=CACHE/'forecast_v5/CSI_ALL.parquet';lp=ROOT/'data/l1_daily.parquet';cp=ROOT/'outputs/universe_current.csv'
    d=pd.read_parquet(dp);a=pd.read_parquet(ap,columns=KEY+['month','date','security_id']);calendar=pd.read_parquet(mp).index
    previous=json.loads((ROOT/'outputs/r179/runs.json').read_text());hashes={str(Path(x['snapshot'])/'manifest.json'):x['snapshot_sha256'] for x in previous}
    records=[];comparisons=[]
    for date in json.loads(protocol.read_text())['dates']:
        f=adapt(d,a,calendar,date);fp=out/f'daily_{date}.parquet';f.to_parquet(fp,index=False)
        bundle=capture(store,[fp,lp],mp,cp,date);m=verify_bundle(bundle);assert capture(store,[fp,lp],mp,cp,date)==bundle
        obs=pd.read_parquet(bundle/'observations.parquet');sub=obs[obs.level.isin(['L2','L3'])]
        excluded=int((d.date.le(date)&d.known_at.gt(date)).sum())
        records.append(dict(asof=date,daily_path=str(fp),daily_sha256=sha(fp),snapshot=str(bundle),snapshot_sha256=sha(bundle/'manifest.json'),rows=len(f),excluded_future_known=excluded,observations=len(obs),ready=int(obs.price_ready.sum()),observed_membership_dates=int(sub.membership_asof.notna().sum()),present_l2_l3=int(sub.date.notna().sum())))
        if date in {x['asof'] for x in previous}:
            old=next(x for x in previous if x['asof']==date and x['version']=='repaired')
            p=pd.read_parquet(Path(old['snapshot'])/'observations.parquet').merge(obs,on=KEY,suffixes=('_old','_new'),validate='one_to_one');p['asof']=date;comparisons.append(p)
    assert all(sha(p)==h for p,h in hashes.items())
    pd.concat(comparisons,ignore_index=True).to_parquet(out/'comparison.parquet',index=False)
    js(out/'runs.json',records);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in [dp,ap,mp,lp,cp,protocol,Path(__file__),ROOT/'src/basket_repair_r129.py',ROOT/'src/versioned_observations.py']},prior_snapshots=hashes,quality='Historical-proxy; membership_asof is source snapshot date, not release timestamp'))
    print(records,flush=True)


if __name__=='__main__':run()
