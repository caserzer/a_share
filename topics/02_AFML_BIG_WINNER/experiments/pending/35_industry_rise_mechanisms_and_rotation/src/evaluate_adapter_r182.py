"""Evaluate clock-filtered repaired sources without mutating observations."""
import pandas as pd
from common import *
from update_adapter_r181 import adapt
from versioned_observations import evaluate,verify_bundle


def validate_evaluation_sources(snapshot,daily,l1,market,cutoff):
    cutoff=pd.Timestamp(cutoff)
    if cutoff<pd.Timestamp(snapshot['identity']['asof']):raise ValueError('evaluation before observation')
    if not {'date','known_at'}<=set(daily) or daily.known_at.isna().any():raise ValueError('missing evaluation clock')
    if (daily.date>cutoff).any() or (daily.known_at>cutoff).any():raise ValueError('future evaluation source')
    if (l1.date>cutoff).any() or (market.index>cutoff).any():raise ValueError('future auxiliary source')
    if not market.index.is_unique or not market.index.is_monotonic_increasing:raise ValueError('invalid evaluation calendar')


def run():
    out=ROOT/'outputs/r182';store=ROOT/'data/update_store_r182';protocol=ROOT/'protocols/r182.json';cfg=json.loads(protocol.read_text())
    rp=ROOT/'outputs/r181/runs.json';obsruns=json.loads(rp.read_text());dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';ap=CACHE/'extension_v2/products/assignments.parquet';lp=ROOT/'data/l1_daily.parquet';mp=CACHE/'forecast_v5/CSI_ALL.parquet'
    d=pd.read_parquet(dp);a=pd.read_parquet(ap,columns=KEY+['month','date','security_id']);l1=pd.read_parquet(lp);market=pd.read_parquet(mp)
    sources={};reads={str(p):sha(p) for p in [rp,dp,ap,lp,mp,protocol,Path(__file__),ROOT/'src/update_adapter_r181.py',ROOT/'src/versioned_observations.py']}
    for cutoff in [cfg['evaluation_asof'],cfg['historical_regression']['asof']]:
        f=adapt(d,a,market.index,cutoff);x=l1[l1.date.le(cutoff)].copy();b=market.loc[:cutoff].copy()
        paths=[out/f'daily_{cutoff}.parquet',out/f'l1_{cutoff}.parquet',out/f'market_{cutoff}.parquet']
        f.to_parquet(paths[0],index=False);x.to_parquet(paths[1],index=False);b.to_parquet(paths[2])
        sources[cutoff]=(f,x,b,paths)
    jobs=[(r,cfg['evaluation_asof']) for r in obsruns]+[(next(r for r in obsruns if r['asof']==cfg['historical_regression']['origin']),cfg['historical_regression']['asof'])]
    runs=[];frames=[];sealed={}
    for row,cutoff in jobs:
        snapshot=Path(row['snapshot']);sm=verify_bundle(snapshot);before=sha(snapshot/'manifest.json');f,x,b,paths=sources[cutoff]
        validate_evaluation_sources(sm,f,x,b,cutoff)
        bundle=evaluate(store,snapshot,paths[:2],paths[2],cutoff);digest=sha(bundle/'manifest.json');m=verify_bundle(bundle)
        assert evaluate(store,snapshot,paths[:2],paths[2],cutoff)==bundle
        assert sha(snapshot/'manifest.json')==before and all(sha(p)==h for p,h in sealed.items())
        sealed[str(bundle/'manifest.json')]=digest
        frame=pd.read_parquet(bundle/'outcomes.parquet');frame['evaluation_asof']=cutoff;frames.append(frame)
        runs.append(dict(origin=row['asof'],evaluation_asof=cutoff,snapshot=str(snapshot),snapshot_sha256=before,evaluation=str(bundle),evaluation_sha256=digest,date_regression=cutoff!=cfg['evaluation_asof'],historical_price_prefix_changed_rows=m['historical_price_prefix_changed_rows']))
    result=pd.concat(frames,ignore_index=True);result.to_parquet(out/'outcomes.parquet',index=False)
    js(out/'runs.json',runs);js(out/'receipt.json',dict(reads=reads,source_paths={k:[str(p) for p in v[3]] for k,v in sources.items()},prospective_records=0))
    summary=result.groupby(['origin','evaluation_asof','horizon','status']).size().rename('rows').reset_index()
    summary.to_csv(out/'status_summary.csv',index=False);print(summary.to_string(index=False))


if __name__=='__main__':run()
