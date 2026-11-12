"""Online-only baseline replay. No reference process, window or label inputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/v2_b01'
    if out.exists():raise FileExistsError('Preserve replay')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet';catfile=EP/'outputs/r01/weekly_catalog.parquet'
    plan=EP/'protocols/v2_b01/plan.md'
    inputs={str(f):sha(f) for f in [source,catfile,plan,Path(__file__)]}
    (out/'started.json').write_text(json.dumps(inputs,indent=2))
    raw=pd.read_parquet(source,columns=['date','day_i','era','industry_code','nav','block'])
    features=[]
    for _,g in raw.groupby(['era','industry_code']):
        g=g.sort_values('day_i').copy()
        for h in [5,20]:
            ok=g.nav.gt(0)&g.nav.shift(h).gt(0)&g.block.notna()&g.block.eq(g.block.shift(h))&g.day_i.sub(g.day_i.shift(h)).eq(h)
            g[f'r{h}']=(g.nav/g.nav.shift(h)-1).where(ok)
        features.append(g)
    f=pd.concat(features,ignore_index=True)
    cat=pd.read_parquet(catfile,columns=['date','era','industry_code','industry_name'])
    cat['date']=pd.to_datetime(cat.date)
    c=cat.merge(f,on=['date','era','industry_code'],how='left',validate='one_to_one')
    events=[];states=[];burden=[];pool={};exit_week={};previous={};number=0
    for week,(date,g) in enumerate(c.groupby('date',sort=True)):
        now={(r.era,r.industry_code):r for r in g.itertuples()};exited=set();new=set();updated=set()
        def emit(key,kind,row,reason):
            nonlocal number
            number+=1
            known=row is not None and np.isfinite(row.r5) and np.isfinite(row.r20)
            prev=previous.get(key)
            enhance=bool(known and prev is not None and prev[0]==week-1 and prev[1]==row.block and row.r20>prev[2])
            events.append(dict(event_id=f'B01-{number:07d}',date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,
                block=row.block if row is not None else None,r5=row.r5 if row is not None else None,r20=row.r20 if row is not None else None,
                positive_evidence=bool(known and row.r5>0),enhancement_evidence=enhance))
        for key,s in list(pool.items()):
            row=now.get(key)
            known=row is not None and np.isfinite(row.r5) and np.isfinite(row.r20) and row.block==s['block']
            s['weak']=s['weak']+1 if known and row.r20<=0 else 0
            reason=('IDENTITY_MISSING' if row is None else 'DATA_OR_CHAIN_UNAVAILABLE' if not known else
                    'TWO_WEAK_REVIEWS' if s['weak']>=2 else 'EIGHT_WEEK_LIMIT' if week-s['entry']>=8 else None)
            if reason:
                emit(key,'EXIT',row,reason);del pool[key];exit_week[key]=week;exited.add(key)
            else:
                emit(key,'UPDATE',row,'LOCAL_IMPROVEMENT' if row.r5>0 else 'RISK_OR_NO_IMPROVEMENT');updated.add(key)
        eligible=g[g.r5.gt(0)&g.r20.gt(0)].sort_values(['r20','industry_code'],ascending=[False,True])
        for row in eligible.itertuples():
            key=(row.era,row.industry_code)
            if key in pool or key in exited or week-exit_week.get(key,-100)<4:continue
            if len(new)>=5 or len(pool)>=20:break
            pool[key]={'entry':week,'block':row.block,'weak':0};new.add(key)
            emit(key,'NEW',row,'POSITIVE_5D_AND_20D_RANKED_BY_20D')
        for key,row in now.items():
            known=np.isfinite(row.r5) and np.isfinite(row.r20)
            state=('NEW' if key in new else 'TRACKING' if key in pool else 'EXIT' if key in exited else 'DATA_INSUFFICIENT' if not known else 'NOT_TRIGGERED')
            states.append(dict(date=date,era=key[0],industry_code=key[1],industry_name=row.industry_name,state=state,r5=row.r5,r20=row.r20))
            if known:previous[key]=(week,row.block,row.r20)
        burden.append(dict(date=date,new=len(new),pool=len(pool),updates=len(updated),exits=len(exited)))
        assert len(new)<=5 and len(pool)<=20
    ev=pd.DataFrame(events); st=pd.DataFrame(states);b=pd.DataFrame(burden)
    assert len(st)==len(cat) and not st.duplicated(['date','era','industry_code']).any()
    assert not ev.duplicated(['date','era','industry_code','kind']).any()
    ev.to_parquet(out/'events.parquet',index=False);st.to_parquet(out/'catalog_states.parquet',index=False);b.to_csv(out/'weekly_burden.csv',index=False)
    summary=dict(scope='Online replay only, no labels read',weeks=len(b),catalog_rows=len(st),events=ev.kind.value_counts().to_dict(),
                 max_new=int(b.new.max()),max_pool=int(b.pool.max()),new_quantiles=b.new.quantile([.5,.9,1]).to_dict(),
                 pool_quantiles=b.pool.quantile([.5,.9,1]).to_dict(),states=st.state.value_counts().to_dict())
    (out/'replay_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'replay_receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
