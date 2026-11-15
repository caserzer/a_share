"""Field-level revision evidence; historical rollback never selects current state."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle, evaluate

FIELDS=['nav','block','day_i','coverage','members','membership_asof','breadth21','breadth63']


def differences(old,new,cutoff):
    keys=KEY+['date']
    a=old[old.date<=pd.Timestamp(cutoff)][keys+FIELDS]
    b=new[new.date<=pd.Timestamp(cutoff)][keys+FIELDS]
    if a.duplicated(keys).any() or b.duplicated(keys).any(): raise ValueError('duplicate source identity/date')
    joined=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
    presence=joined.loc[joined._merge.ne('both'),keys+['_merge']].copy()
    presence['change']=presence.pop('_merge').astype(str).map({'left_only':'removed','right_only':'added'})
    cells=[]
    both=joined[joined._merge.eq('both')]
    for field in FIELDS:
        x=both[field+'_old'];y=both[field+'_new']
        same=x.eq(y)|(x.isna()&y.isna())
        changed=both.loc[~same,keys].copy()
        changed['field']=field
        changed['old_value']=x.loc[~same].map(lambda v:None if pd.isna(v) else str(v))
        changed['new_value']=y.loc[~same].map(lambda v:None if pd.isna(v) else str(v))
        cells.append(changed)
    return presence.reset_index(drop=True),pd.concat(cells,ignore_index=True)


def load_daily(manifest):
    return pd.concat([pd.read_parquet(v['path']) for k,v in manifest['sources'].items() if k.startswith('daily_')],ignore_index=True)


def historical_evaluate(store,snapshot,paths,market,asof,previous):
    sm=verify_bundle(snapshot);pm=verify_bundle(previous)
    if pm['identity']['snapshot']!=sm['bundle_id']:raise ValueError('previous evaluation belongs to another snapshot')
    if pd.Timestamp(asof)<pd.Timestamp(sm['identity']['asof']):raise ValueError('evaluation before observation origin')
    before=sha(Path(previous)/'manifest.json')
    result=evaluate(store,snapshot,paths,market,asof)
    assert sha(Path(previous)/'manifest.json')==before
    return result,dict(date_regression=pd.Timestamp(asof)<pd.Timestamp(pm['identity']['asof']),kind='explicit_historical_replay',previous_evaluation=str(previous),previous_sha256=before,current_pointer_changed=False)


def run():
    out=ROOT/'outputs/r180';rp=ROOT/'outputs/r179/runs.json';runs=json.loads(rp.read_text())
    presences=[];changes=[];reads={str(p):sha(p) for p in [rp,Path(__file__),ROOT/'protocols/r180.json']}
    summary=[];schemas=[]
    for run in runs:
        if run['version']!='source_revision':continue
        sp=Path(run['snapshot']);ep=Path(run['evaluation']);sm=verify_bundle(sp);em=verify_bundle(ep)
        for version,m in [('old',sm),('new',em)]:
            for key,v in m['sources'].items():
                if key.startswith('daily_'):
                    cols=pd.read_parquet(v['path']).columns
                    schemas.append(dict(asof=run['asof'],version=version,source_key=key,path=v['path'],sha256=v['sha256'],absent_fields=[f for f in FIELDS if f not in cols]))
        p,c=differences(load_daily(sm),load_daily(em),run['asof'])
        summary.append(dict(asof=run['asof'],row_changes=p.change.value_counts().to_dict(),cell_changes=c.field.value_counts().to_dict()))
        p['asof']=run['asof'];c['asof']=run['asof'];presences.append(p);changes.append(c)
        for q in [sp/'manifest.json',ep/'manifest.json']:reads[str(q)]=sha(q)
    pd.concat(presences,ignore_index=True).to_parquet(out/'row_changes.parquet',index=False)
    pd.concat(changes,ignore_index=True).to_parquet(out/'cell_changes.parquet',index=False)
    run=next(r for r in runs if r['version']=='repaired' and r['asof']=='2026-06-30')
    previous=Path(run['evaluation']);em=verify_bundle(previous);paths=[v['path'] for k,v in em['sources'].items() if k.startswith('daily_')];market=em['sources']['market']['path']
    store=ROOT/'data/update_store_r180';asof=json.loads((ROOT/'protocols/r180.json').read_text())['rollback_asof']
    result,rollback=historical_evaluate(store,run['snapshot'],paths,market,asof,previous)
    again,_=historical_evaluate(store,run['snapshot'],paths,market,asof,previous);assert again==result
    try:historical_evaluate(store,run['snapshot'],paths,market,'2026-06-29',previous)
    except ValueError as exc:assert str(exc)=='evaluation before observation origin'
    else:raise AssertionError('pre-origin evaluation accepted')
    frame=pd.read_parquet(result/'outcomes.parquet');assert frame.status.eq('pending_market_sessions').all() and frame.excess.isna().all()
    rollback.update(snapshot=run['snapshot'],evaluation=str(result),asof=asof,rows=len(frame),pending=len(frame),pre_origin_rejected=True,idempotent=True)
    js(out/'source_schemas.json',schemas)
    js(out/'rollback.json',rollback);js(out/'summary.json',dict(revisions=summary,rollback=rollback,prospective_records=0));js(out/'receipt.json',dict(reads=reads))
    print(summary);print('rollback',len(frame))


if __name__=='__main__':run()
