"""Fixed inherited member-volume information experiment; historical causal features only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from v2_b06_replay import prepare as base_prepare

def prepare():
    c=base_prepare()
    vf=EP/'outputs/r04/volume_features.parquet'
    seal=json.loads((EP/'outputs/r04/prediction_seal.json').read_text())
    assert sha(vf)==seal["artifacts"]["volume_features.parquet"]
    for source,digest in seal["source"].items():
        assert sha(Path(source))==digest, source
    v=pd.read_parquet(vf);v['date']=pd.to_datetime(v.date)
    c=c.merge(v,on=['date','era','industry_code'],how='left',validate='one_to_one')
    c['original_eligible']=c.eligible
    c['eligible']=c.eligible & c.supported.eq(True) & np.isfinite(c.volume_ratio)
    c['adjusted_score']=np.nan
    for _,g in c[c.eligible].groupby('date'):
        c.loc[g.index,'adjusted_score']=.5*g.r20.rank(method='average',pct=True)+.5*g.volume_ratio.rank(method='average',pct=True)
    c['exclusion']=np.where(~c.original_eligible,'ORIGINAL_NOT_ELIGIBLE',np.where(c.eligible,'COMMON_ELIGIBLE','VOLUME_UNKNOWN'))
    return c

def pair(c,quota,delay,root):
    states={a:dict(pool={},exits={},events=[],catalog=[],burden=[],number=0) for a in ('A','B')}
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);now={(r.era,r.industry_code):r for r in g.itertuples()};lists={}
        def emit(arm,key,kind,row,reason):
            s=states[arm];s['number']+=1
            known=row is not None and np.isfinite(row.r5) and np.isfinite(row.r20) and np.isfinite(row.r40)
            s['events'].append(dict(event_id=f'B09-{quota}-{delay}-{arm}-{s["number"]:07d}',date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,
                block=None if row is None else row.block,r5=None if row is None else row.r5,r20=None if row is None else row.r20,
                score=None if row is None else row.r20 if arm=='A' else row.adjusted_score,
                positive_evidence=bool(known and row.r5>0),enhancement_evidence=bool(known and row.enhance)))
        for arm,s in states.items():
            s['new']=set();s['updated']=set();s['exited']=set()
            for key,p in list(s['pool'].items()):
                row=now.get(key);known=row is not None and np.isfinite(row.r40) and np.isfinite(row.r5) and row.block==p['block']
                p['weak']=p['weak']+1 if known and row.r20<=0 else 0
                reason=('IDENTITY_MISSING' if row is None else 'DATA_OR_CHAIN_UNAVAILABLE' if not known else
                        'TWO_WEAK_REVIEWS' if p['weak']>=2 else 'EIGHT_WEEK_LIMIT' if week-p['entry']>=8 else None)
                if reason:
                    emit(arm,key,'EXIT',row,reason);del s['pool'][key];s['exits'][key]=week;s['exited'].add(key)
                else:
                    emit(arm,key,'UPDATE',row,'LOCAL_IMPROVEMENT' if row.r5>0 else 'RISK_OR_NO_IMPROVEMENT');s['updated'].add(key)
            eligible=g[g.confirmed if delay else g.eligible]
            ranked=eligible.sort_values(['r20' if arm=='A' else 'adjusted_score','industry_code'],ascending=[False,True])
            lists[arm]=[r for r in ranked.itertuples() if (r.era,r.industry_code) not in s['pool'] and week-s['exits'].get((r.era,r.industry_code),-100)>=4]
        q=min(quota,*[20-len(s['pool']) for s in states.values()],*[len(v) for v in lists.values()])
        for arm,s in states.items():
            for row in lists[arm][:q]:
                key=(row.era,row.industry_code);s['pool'][key]={'entry':week,'block':row.block,'weak':0};s['new'].add(key)
                emit(arm,key,'NEW',row,'PAIRED_POSITIVE_PRICE_ADMISSION')
            for key,row in now.items():
                known=np.isfinite(row.r40) and np.isfinite(row.r5)
                status=('NEW' if key in s['new'] else 'TRACKING' if key in s['pool'] else 'EXIT' if key in s['exited'] else 'DATA_INSUFFICIENT' if not known else 'NOT_TRIGGERED')
                s['catalog'].append(dict(date=date,era=key[0],industry_code=key[1],industry_name=row.industry_name,state=status,r5=row.r5,r20=row.r20))
            s['burden'].append(dict(date=date,new=q,pool=len(s['pool']),updates=len(s['updated']),exits=len(s['exited'])))
            assert len(s['pool'])<=20 and len(s['new'])==q<=quota<=5
    summary={}
    for arm,s in states.items():
        dest=root/f'q{quota}_d{delay}'/arm;dest.mkdir(parents=True)
        ev=pd.DataFrame(s['events']);st=pd.DataFrame(s['catalog']);b=pd.DataFrame(s['burden'])
        assert len(st)==len(c) and not st.duplicated(['date','era','industry_code']).any()
        ev.to_parquet(dest/'events.parquet',index=False);st.to_parquet(dest/'catalog_states.parquet',index=False);b.to_csv(dest/'weekly_burden.csv',index=False)
        summary[arm]=dict(events=ev.kind.value_counts().to_dict(),max_pool=int(b.pool.max()),mean_pool=float(b.pool.mean()),mean_new=float(b.new.mean()))
    assert states['A']['burden'] and [r['new'] for r in states['A']['burden']]==[r['new'] for r in states['B']['burden']]
    return summary


def main():
    out=EP/'outputs/v2_b09'
    if out.exists():raise FileExistsError('Preserve B09')
    out.mkdir();paths=[PRIOR/'daily_industries.parquet',PRIOR/'receipt.json',EP/'outputs/r04/volume_features.parquet',EP/'outputs/r04/prediction_seal.json',EP/'configs/r04_volume.json',EP/'outputs/r01/weekly_catalog.parquet',EP/'src/v2_b06_replay.py',EP/'protocols/v2_b09/plan.md',Path(__file__)]
    c=prepare();c.to_parquet(out/'features.parquet',index=False);c.groupby(['era','exclusion']).size().rename('rows').to_csv(out/'admission_counts.csv')
    summary=pair(c,5,0,out);(out/'replay_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'replay_receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in paths},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
