"""Read-only attribution of observed blocking gates; not counterfactual uplift."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/v2_b01/diagnosis'
    if out.exists():raise FileExistsError('Preserve diagnosis')
    out.mkdir()
    paths=[EP/'outputs/v2_b01/catalog_states.parquet',EP/'outputs/v2_b01/events.parquet',
           EP/'outputs/v2_b01/evaluation/process_coverage.parquet',
           EP/'outputs/r00_v2_window_recovery/windows.parquet',
           EP/'outputs/r00_v2_window_recovery/process_window_audit.parquet',
           PRIOR/'daily_industries.parquet',EP/'protocols/v2_b01_diagnosis/plan.md',Path(__file__)]
    inputs={str(f):sha(f) for f in paths}
    c=pd.read_parquet(paths[0]);ev=pd.read_parquet(paths[1]);pr=pd.read_parquet(paths[2]);w=pd.read_parquet(paths[3]);wa=pd.read_parquet(paths[4]).set_index('segment_id')
    raw=pd.read_parquet(paths[5],columns=['date','era','industry_code','block'])
    c=c.merge(raw,on=['date','era','industry_code'],how='left',validate='one_to_one')
    dates=sorted(c.date.unique());weekmap={pd.Timestamp(d):i for i,d in enumerate(dates)}
    c['week']=c.date.map(weekmap);c=c.sort_values(['era','industry_code','week'])
    group=c.groupby(['era','industry_code']);prev=group[['r20','week','block']].shift(1)
    c['enhance']=(c.r20>prev.r20)&c.week.sub(prev.week).eq(1)&c.block.eq(prev.block)
    last_exit={};facts=[]
    eg={d:g for d,g in ev.groupby('date')}
    for date,g in c.groupby('date',sort=True):
        events=eg.get(date,pd.DataFrame(columns=ev.columns));week=weekmap[date]
        exits=set(zip(events.loc[events.kind.eq('EXIT'),'era'],events.loc[events.kind.eq('EXIT'),'industry_code']))
        updates=set(zip(events.loc[events.kind.eq('UPDATE'),'era'],events.loc[events.kind.eq('UPDATE'),'industry_code']))
        for key in exits:last_exit[key]=week
        free=20-len(updates);slots=min(5,free)
        possible=[]
        for row in g.itertuples():
            key=(row.era,row.industry_code)
            if row.r5>0 and row.r20>0 and key not in updates and week-last_exit.get(key,-100)>=4:
                possible.append((key,row.r20))
        ranked=sorted(possible,key=lambda x:(-x[1],x[0][1]));ranks={key:i+1 for i,(key,_) in enumerate(ranked)}
        for row in g.itertuples():
            key=(row.era,row.industry_code)
            if not(np.isfinite(row.r5) and np.isfinite(row.r20)):reason='DATA_INSUFFICIENT'
            elif row.r5<=0:reason='NO_LOCAL_IMPROVEMENT'
            elif key in updates or row.state=='NEW':reason='ACTUAL_POSITIVE_EVENT'
            elif row.r20<=0:reason='POSITIVE_20D_GATE'
            elif week-last_exit.get(key,-100)<4:reason='EXIT_OR_REENTRY_LIMIT'
            elif free==0:reason='POOL_FULL'
            else:
                assert key in ranks and ranks[key]>slots,(date,key,ranks.get(key),slots)
                reason='RANKED_OUT'
            facts.append(dict(date=date.strftime('%Y-%m-%d'),era=row.era,industry_code=row.industry_code,
                reason=reason,enhance=bool(row.enhance),free_slots=free,candidate_rank=ranks.get(key),r5=row.r5,r20=row.r20))
    f=pd.DataFrame(facts);fg={k:g for k,g in f.groupby(['era','industry_code'])};wg={k:g for k,g in w.groupby('segment_id')}
    opportunities=[];processes=[]
    priority=['ACTUAL_POSITIVE_EVENT','RANKED_OUT','POOL_FULL','EXIT_OR_REENTRY_LIMIT','POSITIVE_20D_GATE',
              'NO_NEW_ENHANCEMENT_EVIDENCE','NO_LOCAL_IMPROVEMENT','DATA_INSUFFICIENT']
    def choose(g):
        return next((x for x in priority if g.reason.eq(x).any()),'NO_REVIEW_OPPORTUNITY')
    for row in pr.itertuples():
        g=fg[(row.era,row.industry_code)];spans=wg.get(row.process,pd.DataFrame(columns=['start','end']))
        mask=np.zeros(len(g),dtype=bool)
        for span in spans.itertuples():mask|=((g.date>=span.start)&(g.date<=span.end)).to_numpy()
        q=g[mask].copy();q['process']=row.process
        if row.kind=='HEATING':
            condition=q.reason.isin(['ACTUAL_POSITIVE_EVENT','RANKED_OUT','POOL_FULL','EXIT_OR_REENTRY_LIMIT','POSITIVE_20D_GATE'])&~q.enhance
            q.loc[condition,'reason']='NO_NEW_ENHANCEMENT_EVIDENCE'
        deadline=wa.loc[row.process,'timely_reference_end']
        q['timely']=q.date.le(deadline) if deadline is not None else False
        opportunities.append(q)
        whole=choose(q);early=choose(q[q.timely])
        assert (whole=='ACTUAL_POSITIVE_EVENT')==row.covered,(row.process,whole,row.covered)
        assert (early=='ACTUAL_POSITIVE_EVENT')==(row.timing=='TIMELY'),(row.process,early,row.timing)
        processes.append(dict(process=row.process,era=row.era,industry_code=row.industry_code,kind=row.kind,year=row.start[:4],
            covered=row.covered,timing=row.timing,all_window_reason=whole,timely_window_reason=early,
            opportunities=len(q),timely_opportunities=int(q.timely.sum())))
    details=pd.concat(opportunities,ignore_index=True);result=pd.DataFrame(processes)
    details.to_parquet(out/'opportunity_gates.parquet',index=False);result.to_parquet(out/'process_diagnosis.parquet',index=False)
    result.groupby(['era','year','kind','all_window_reason']).size().rename('count').reset_index().to_csv(out/'strata.csv',index=False)
    summary=dict(scope='Gate attribution, not causal uplift or a new strategy',processes=len(result),
        missed=int((~result.covered).sum()),missed_reasons=result.loc[~result.covered,'all_window_reason'].value_counts().to_dict(),
        late=int(result.timing.eq('LATE').sum()),late_timely_reasons=result.loc[result.timing.eq('LATE'),'timely_window_reason'].value_counts().to_dict(),
        all_timely_reasons=result.timely_window_reason.value_counts().to_dict(),opportunities=len(details))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
