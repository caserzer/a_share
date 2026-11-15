"""Frozen-score pool competition. Signals contain no retrospective labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha

ARMS=[f'{score}_{wait}_COMPETE' for score in ['BALANCED','BROAD20'] for wait in ['NOW','WAIT']]

def priority(row,column,score):
    if getattr(row,column):
        value=getattr(row,score);assert np.isfinite(value)
        return (0,-value,row.industry_code)
    return (1,0,row.industry_code)

def choices(now,pool,exits,week,column,score,compete,entry_column=None):
    entry_column=entry_column or column
    candidates=[k for k,r in now.items() if getattr(r,column) and getattr(r,entry_column) and k not in pool and week-exits.get(k,-100)>=4]
    key=lambda k:priority(now[k],column,score)
    candidates.sort(key=key)
    incumbents=sorted(pool,key=key)
    if compete:
        top=set(sorted(incumbents+candidates,key=key)[:20])
        candidates=[k for k in candidates if k in top]
    return candidates,incumbents

def replay(c,arms,quota,out,prefix):
    states={a:dict(pool={},exits={},events=[],catalog=[],decisions=[],number=0) for a in arms}
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);now={(r.era,r.industry_code):r for r in g.itertuples()};offers={};caps={}
        def emit(a,key,kind,reason):
            s=states[a];r=now.get(key);s['number']+=1;sc='score_'+a.removesuffix('_COMPETE')
            known=r is not None and np.isfinite(r.r40) and np.isfinite(r.r5)
            s['events'].append(dict(event_id=f'M07-{prefix}-{a}-{s["number"]:07d}',date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,block=None if r is None else r.block,r5=None if r is None else r.r5,r20=None if r is None else r.r20,score=None if r is None else getattr(r,sc),positive_evidence=bool(known and r.r5>0),enhancement_evidence=bool(known and r.enhance)))
        for a,s in states.items():
            s['new']=set();s['exited']=set()
            for k,p in list(s['pool'].items()):
                r=now.get(k);known=r is not None and np.isfinite(r.r40) and np.isfinite(r.r5) and r.block==p['block']
                p['weak']=p['weak']+1 if known and r.r20<=0 else 0
                reason='IDENTITY_MISSING' if r is None else 'DATA_OR_CHAIN_UNAVAILABLE' if not known else 'TWO_WEAK_REVIEWS' if p['weak']>=2 else 'EIGHT_WEEK_LIMIT' if week-p['entry']>=8 else None
                if reason:
                    emit(a,k,'EXIT',reason);del s['pool'][k];s['exits'][k]=week;s['exited'].add(k)
            col='eligible_original' if a.startswith('ORIGINAL20') else 'eligible';sc='score_'+a.removesuffix('_COMPETE');compete=a.endswith('COMPETE')
            offers[a]=choices(now,s['pool'],s['exits'],week,col,sc,compete,'confirmed' if '_WAIT_' in a else col)
            caps[a]=min(quota,len(offers[a][0]),20 if compete else 20-len(s['pool']))
        q=min(caps.values())
        for a,s in states.items():
            candidates,incumbents=offers[a];before=set(s['pool']);free=20-len(before);replace=max(0,q-free)
            assert a.endswith('COMPETE') or replace==0
            removed=incumbents[-replace:] if replace else []
            for k in removed:
                emit(a,k,'EXIT','LOWER_CURRENT_PRIORITY');del s['pool'][k];s['exits'][k]=week;s['exited'].add(k)
            for k in s['pool']:
                emit(a,k,'UPDATE','LOCAL_IMPROVEMENT' if now[k].r5>0 else 'RISK_OR_NO_IMPROVEMENT')
            for k in candidates[:q]:
                assert k not in before and week-s['exits'].get(k,-100)>=4
                s['pool'][k]=dict(entry=week,block=now[k].block,weak=0);s['new'].add(k);emit(a,k,'NEW','FIXED_SCORE_POSITIVE_LOCAL_PRICE')
            for k,r in now.items():
                known=np.isfinite(r.r40) and np.isfinite(r.r5);sc='score_'+a.removesuffix('_COMPETE')
                state='NEW' if k in s['new'] else 'TRACKING' if k in s['pool'] else 'EXIT' if k in s['exited'] else 'DATA_INSUFFICIENT' if not known else 'NOT_TRIGGERED'
                s['catalog'].append(dict(date=date,era=k[0],industry_code=k[1],industry_name=r.industry_name,state=state,score=getattr(r,sc),r5=r.r5,r20=r.r20))
            s['decisions'].append(dict(date=date,pool_before=len(before),free_slots=free,own_capacity=caps[a],actual_new=q,competitive_exits=replace,pool_after=len(s['pool']),incumbents=[k[1] for k in incumbents],qualified_candidates=[k[1] for k in candidates],removed=[k[1] for k in removed],added=[k[1] for k in candidates[:q]]))
            assert len(s['pool'])<=20 and q<=quota<=5 and len(s['new'])==q
    summary=[]
    for a,s in states.items():
        dest=out/(prefix+'_'+a);dest.mkdir();ev=pd.DataFrame(s['events']);catalog=pd.DataFrame(s['catalog']);dec=pd.DataFrame(s['decisions'])
        assert len(catalog)==len(c) and not catalog.duplicated(['date','era','industry_code']).any()
        assert not ev.duplicated(['date','era','industry_code']).any()
        ev.to_parquet(dest/'events.parquet',index=False);catalog.to_parquet(dest/'catalog_states.parquet',index=False);dec.to_parquet(dest/'decisions.parquet',index=False)
        summary.append(dict(run_id=dest.name,arm=a,quota=quota,mode='solo' if prefix=='solo' else 'paired',new=int(ev.kind.eq('NEW').sum()),events=len(ev),catalog=len(catalog),replacements=int(dec.competitive_exits.sum())))
    return summary

def main():
    source=EP/'outputs/v3_m02_models';out=EP/'outputs/v3_m07_replay';assert not out.exists()
    rec=json.loads((source/'receipt.json').read_text())
    for f,h in rec['artifacts'].items():assert sha(source/f)==h
    cols=['date','era','industry_code','industry_name','block','r5','r20','r40','week','enhance','eligible','eligible_original','confirmed','score_BALANCED']
    c=pd.read_parquet(source/'scored_catalog.parquet',columns=cols);c['score_ORIGINAL20']=c.r20;c['score_BROAD20']=c.r20
    for arm in ARMS:c['score_'+arm.removesuffix('_COMPETE')]=c['score_BALANCED'] if arm.startswith('BALANCED') else c.r20
    out.mkdir();c.to_parquet(out/'signal_catalog.parquet',index=False);rows=[]
    for q in [1,3,5]:
        rows.extend(replay(c,ARMS,q,out,f'q{q}_d0'));print('M07 paired',q,flush=True)
    for arm in ARMS:
        rows.extend(replay(c,[arm],5,out,'solo'));print('M07 solo',arm,flush=True)
    pd.DataFrame(rows).to_csv(out/'run_inventory.csv',index=False)
    support=EP/'outputs/v3_m02_replay/calendar_coverage.csv';(out/'calendar_coverage.csv').write_bytes(support.read_bytes())
    inputs=[source/'receipt.json',source/'scored_catalog.parquet',support,EP/'protocols/v3_r00/m07_confirmation_cost_plan.md',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')

if __name__=='__main__':main()
