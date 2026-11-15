"""Six preregistered arms, identical per-week admissions, full directory states."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha

ARMS=['ORIGINAL20','BROAD20','RULE5','LR_BASE','LR_CHANGE','TREE_CHANGE']


def replay(c,quota,delay,out):
    states={a:dict(pool={},exits={},events=[],catalog=[],number=0) for a in ARMS}
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);now={(r.era,r.industry_code):r for r in g.itertuples()};lists={}
        def emit(a,key,kind,row,reason):
            s=states[a];s['number']+=1
            known=row is not None and np.isfinite(row.r40) and np.isfinite(row.r5)
            score=None if row is None else getattr(row,'score_'+a)
            s['events'].append(dict(event_id=f'M01-q{quota}d{delay}-{a}-{s["number"]:07d}',date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,
                block=None if row is None else row.block,r5=None if row is None else row.r5,r20=None if row is None else row.r20,score=score,
                positive_evidence=bool(known and row.r5>0),enhancement_evidence=bool(known and row.enhance)))
        for a,s in states.items():
            s['new']=set();s['exited']=set()
            for key,p in list(s['pool'].items()):
                row=now.get(key);known=row is not None and np.isfinite(row.r40) and np.isfinite(row.r5) and row.block==p['block']
                p['weak']=p['weak']+1 if known and row.r20<=0 else 0
                reason=('IDENTITY_MISSING' if row is None else 'DATA_OR_CHAIN_UNAVAILABLE' if not known else 'TWO_WEAK_REVIEWS' if p['weak']>=2 else 'EIGHT_WEEK_LIMIT' if week-p['entry']>=8 else None)
                if reason:
                    emit(a,key,'EXIT',row,reason);del s['pool'][key];s['exits'][key]=week;s['exited'].add(key)
                else:emit(a,key,'UPDATE',row,'LOCAL_IMPROVEMENT' if row.r5>0 else 'RISK_OR_NO_IMPROVEMENT')
            column=('confirmed_original' if delay else 'eligible_original') if a=='ORIGINAL20' else ('confirmed' if delay else 'eligible')
            ranked=g[g[column]].sort_values(['score_'+a,'industry_code'],ascending=[False,True])
            assert ranked['score_'+a].notna().all()
            lists[a]=[r for r in ranked.itertuples() if (r.era,r.industry_code) not in s['pool'] and week-s['exits'].get((r.era,r.industry_code),-100)>=4]
        q=min(quota,*[20-len(s['pool']) for s in states.values()],*[len(v) for v in lists.values()])
        for a,s in states.items():
            for row in lists[a][:q]:
                key=(row.era,row.industry_code);s['pool'][key]={'entry':week,'block':row.block,'weak':0};s['new'].add(key)
                emit(a,key,'NEW',row,'FIXED_SCORE_POSITIVE_LOCAL_PRICE')
            for key,row in now.items():
                known=np.isfinite(row.r40) and np.isfinite(row.r5)
                state='NEW' if key in s['new'] else 'TRACKING' if key in s['pool'] else 'EXIT' if key in s['exited'] else 'DATA_INSUFFICIENT' if not known else 'NOT_TRIGGERED'
                s['catalog'].append(dict(date=date,era=key[0],industry_code=key[1],industry_name=row.industry_name,state=state,score=getattr(row,'score_'+a),r5=row.r5,r20=row.r20))
            assert len(s['new'])==q<=quota<=5 and len(s['pool'])<=20
    admissions=[];summaries=[]
    for a,s in states.items():
        dest=out/f'q{quota}_d{delay}_{a}';dest.mkdir()
        ev=pd.DataFrame(s['events']);st=pd.DataFrame(s['catalog'])
        ev.to_parquet(dest/'events.parquet',index=False);st.to_parquet(dest/'catalog_states.parquet',index=False)
        assert len(st)==len(c) and not st.duplicated(['date','era','industry_code']).any()
        count=ev[ev.kind.eq('NEW')].groupby('date').size().reindex(sorted(c.date.unique()),fill_value=0)
        admissions.append(count.to_list());summaries.append(dict(run_id=dest.name,new=int(count.sum()),events=len(ev),catalog=len(st)))
    assert all(x==admissions[0] for x in admissions)
    return summaries


def main():
    source=EP/'outputs/v3_m01_models';out=EP/'outputs/v3_m01_replay'
    if out.exists():raise FileExistsError(out)
    rec=json.loads((source/'receipt.json').read_text())
    for rel,digest in rec['artifacts'].items():assert sha(source/rel)==digest,rel
    c=pd.read_parquet(source/'scored_catalog.parquet')
    # Explicit signal-only boundary: no training labels, reference IDs or maturity dates.
    keep=['date','era','industry_code','industry_name','block','r5','r20','r40','week','enhance','eligible','confirmed','eligible_original','confirmed_original']+['score_'+a for a in ARMS if a.startswith(('LR_','TREE_'))]
    c=c[keep].copy();c['score_ORIGINAL20']=c.r20;c['score_BROAD20']=c.r20;c['score_RULE5']=c.r5
    out.mkdir();summary=[]
    for q in [1,3,5]:
        for delay in [0,1]:
            summary.extend(replay(c,q,delay,out));print('Replay',q,delay,flush=True)
    pd.DataFrame(summary).to_csv(out/'run_inventory.csv',index=False)
    support=pd.read_csv(EP/'outputs/refresh/s02_chain_safe_v2_20261112/calendar_coverage.csv',parse_dates=['date'])
    support=support[support.date.between(c.date.min(),c.date.max())];support.to_csv(out/'calendar_coverage.csv',index=False)
    inputs=[source/'receipt.json',source/'scored_catalog.parquet',EP/'protocols/v3_r00/m01_plan.md',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
