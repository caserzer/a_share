"""Paired online replay: identical weekly admissions, no label inputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def prepare():
    raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['date','day_i','era','industry_code','nav','block'])
    parts=[]
    for _,g in raw.groupby(['era','industry_code']):
        g=g.sort_values('day_i').copy()
        for h in (5,20,40):
            ok=g.nav.gt(0)&g.nav.shift(h).gt(0)&g.block.notna()&g.block.eq(g.block.shift(h))&g.day_i.sub(g.day_i.shift(h)).eq(h)
            g[f'r{h}']=(g.nav/g.nav.shift(h)-1).where(ok)
        g['accel']=g.r20-g.r20.shift(20);g.loc[g.r40.isna(),'accel']=np.nan
        parts.append(g)
    cat=pd.read_parquet(EP/'outputs/r01/weekly_catalog.parquet',columns=['date','era','industry_code','industry_name']);cat['date']=pd.to_datetime(cat.date)
    c=cat.merge(pd.concat(parts),on=['date','era','industry_code'],how='left',validate='one_to_one')
    c['week']=c.date.map({d:i for i,d in enumerate(sorted(c.date.unique()))})
    c=c.sort_values(['era','industry_code','week'])
    c['eligible']=c.r5.gt(0)&c.r20.gt(0)&c.r40.notna()
    previous=c.groupby(['era','industry_code'])[['week','block','r20','eligible']].shift(1)
    adjacent=c.week.sub(previous.week).eq(1)&c.block.eq(previous.block)
    c['enhance']=adjacent&c.r20.gt(previous.r20)
    c['confirmed']=c.eligible&adjacent&previous.eligible.fillna(False).astype(bool)
    return c


def pair(c,quota,delay,root):
    states={a:dict(pool={},exits={},events=[],catalog=[],burden=[],number=0) for a in ('A','B')}
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);now={(r.era,r.industry_code):r for r in g.itertuples()};lists={}
        def emit(arm,key,kind,row,reason):
            s=states[arm];s['number']+=1
            known=row is not None and np.isfinite(row.r5) and np.isfinite(row.r20) and np.isfinite(row.r40)
            s['events'].append(dict(event_id=f'B02-{quota}-{delay}-{arm}-{s["number"]:07d}',date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,
                block=None if row is None else row.block,r5=None if row is None else row.r5,r20=None if row is None else row.r20,
                score=None if row is None else row.r20 if arm=='A' else row.accel,
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
            ranked=eligible.sort_values(['r20' if arm=='A' else 'accel','industry_code'],ascending=[False,True])
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
    out=EP/'outputs/v2_b02'
    if out.exists():raise FileExistsError('Preserve paired replay')
    out.mkdir()
    paths=[PRIOR/'daily_industries.parquet',EP/'outputs/r01/weekly_catalog.parquet',EP/'protocols/v2_b02/plan.md',Path(__file__)]
    inputs={str(f):sha(f) for f in paths};(out/'started.json').write_text(json.dumps(inputs,indent=2))
    c=prepare();summary={}
    for quota in (1,3,5):
        for delay in (0,1):
            name=f'q{quota}_d{delay}';summary[name]=pair(c,quota,delay,out);print(name,json.dumps(summary[name]),flush=True)
    (out/'replay_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'replay_receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
