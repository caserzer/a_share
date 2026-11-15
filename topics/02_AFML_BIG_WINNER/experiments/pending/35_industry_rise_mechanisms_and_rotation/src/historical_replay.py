"""Explicit corrected local historical replay. No network or forward mode."""
import argparse
import tempfile
import pandas as pd
from common import *
from update_adapter_r181 import adapt
from evaluate_adapter_r182 import validate_evaluation_sources
from versioned_observations import source_copy,seal,verify_bundle,capture,evaluate

ROLES={'daily','assignments','l1','market','catalog'}


def checked_manifest(path,asof):
    m=json.loads(Path(path).read_text());date=pd.Timestamp(asof)
    if m.get('schema')!='ep35_repaired_historical_v1' or m.get('quality')!='Historical-proxy':raise ValueError('unsupported source contract')
    if pd.isna(date) or date.tz is not None or date!=date.normalize():raise ValueError('cutoff must be an explicit date')
    if date>pd.Timestamp(m['max_asof']):raise ValueError('cutoff exceeds source maximum')
    if set(m['sources'])!=ROLES:raise ValueError('source roles mismatch')
    for role,item in m['sources'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('source hash mismatch: '+role)
    return m,date


def verify_replay(envelope):
    m=verify_bundle(envelope)
    if m.get('replay_kind')!='historical_only':raise ValueError('not a corrected replay envelope')
    row=pd.read_parquet(Path(envelope)/'result.parquet').iloc[0]
    if sha(Path(row.bundle)/'manifest.json')!=row.manifest_sha256:raise ValueError('result manifest changed')
    bm=verify_bundle(row.bundle)
    if bm['bundle_id']!=row.bundle_id:raise ValueError('result identity mismatch')
    return m,row,bm


def replay(action,asof,manifest_path,store,snapshot=None):
    manifest,date=checked_manifest(manifest_path,asof);store=Path(store)
    if action not in ['capture','evaluate']:raise ValueError('unknown action')
    prior=None
    if action=='evaluate':
        if snapshot is None:raise ValueError('evaluation requires capture envelope')
        prior,row,sm=verify_replay(snapshot)
        if prior['identity']['action']!='capture':raise ValueError('evaluation requires capture envelope')
        if date<pd.Timestamp(sm['identity']['asof']):raise ValueError('evaluation before observation')
    sources={k:source_copy(v['path'],store) for k,v in manifest['sources'].items()}
    if any(sources[k]['sha256']!=manifest['sources'][k]['sha256'] for k in ROLES):raise ValueError('source changed during copy')
    codepaths={'source_manifest':Path(manifest_path),'driver':Path(__file__),'adapter':ROOT/'src/update_adapter_r181.py','guard':ROOT/'src/evaluate_adapter_r182.py','basket_rules':ROOT/'src/basket_repair_r129.py','versioning':ROOT/'src/versioned_observations.py','features':ROOT/'src/build_panel.py','common':ROOT/'src/common.py','protocol':ROOT/'protocols/r184.json'}
    sources.update({k:source_copy(p,store) for k,p in codepaths.items()})
    if json.loads(Path(sources['source_manifest']['path']).read_text())!=manifest:raise ValueError('source manifest changed during copy')
    daily=pd.read_parquet(sources['daily']['path']);a=pd.read_parquet(sources['assignments']['path'],columns=KEY+['month','date','security_id']);l1=pd.read_parquet(sources['l1']['path']);market=pd.read_parquet(sources['market']['path'])
    if date not in market.index:raise ValueError('cutoff absent from source calendar')
    corrected=adapt(daily,a,market.index,date);l1=l1[l1.date.le(date)];market=market.loc[:date]
    with tempfile.TemporaryDirectory(prefix='prepared-',dir=store) as tmp:
        tmp=Path(tmp);dp=tmp/'daily.parquet';lp=tmp/'l1.parquet';mp=tmp/'market.parquet'
        corrected.to_parquet(dp,index=False);l1.to_parquet(lp,index=False);market.to_parquet(mp)
        if action=='capture':
            bundle=capture(store,[dp,lp],mp,sources['catalog']['path'],str(date.date()))
        else:
            validate_evaluation_sources(sm,corrected,l1,market,date)
            bundle=evaluate(store,row.bundle,[dp,lp],mp,str(date.date()))
    bm=verify_bundle(bundle)
    sources['result_manifest']=source_copy(bundle/'manifest.json',store)
    if snapshot is not None:sources['capture_envelope']=source_copy(Path(snapshot)/'manifest.json',store)
    identity=dict(action=action,asof=str(date.date()),sources={k:v['sha256'] for k,v in sources.items()})
    frame=pd.DataFrame([dict(bundle=str(bundle),bundle_id=bm['bundle_id'],manifest_sha256=sha(bundle/'manifest.json'))])
    envelope=seal(store,'replay_receipts',identity,sources,{'result.parquet':frame},dict(replay_kind='historical_only',quality='Historical-proxy',prospective_records=0,current_pointer_changed=False))
    verify_replay(envelope)
    return envelope


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for name in ['capture','evaluate']:
        q=sub.add_parser(name);q.add_argument('--asof',required=True);q.add_argument('--sources',required=True);q.add_argument('--store',required=True)
        if name=='evaluate':q.add_argument('--snapshot',required=True,help='capture replay receipt directory')
    q=sub.add_parser('verify');q.add_argument('--receipt',required=True);args=p.parse_args()
    if args.action=='verify':
        m,row,bm=verify_replay(args.receipt);print(json.dumps(dict(status='PASS',action=m['identity']['action'],bundle=row.bundle,replay_kind=m['replay_kind'])));return
    receipt=replay(args.action,args.asof,args.sources,args.store,getattr(args,'snapshot',None))
    print(json.dumps(dict(receipt=str(receipt),replay_kind='historical_only',prospective_records=0)))


if __name__=='__main__':main()
