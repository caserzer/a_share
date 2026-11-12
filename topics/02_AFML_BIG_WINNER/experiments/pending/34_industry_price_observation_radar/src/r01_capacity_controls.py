"""Predeclared capacity-only replay and separately invoked evaluation."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from r01_pool import ObservationPool

OUT=EP/'outputs/r01_capacity'


def predict():
    if (OUT/'prediction_seal.json').exists():raise FileExistsError('controls sealed')
    pred=json.loads((EP/'outputs/r01/prediction_seal.json').read_text())
    for filename,h in pred['files'].items():assert sha(Path(filename))==h
    wfile=EP/'outputs/r01/weekly_catalog.parquet'
    replay=json.loads((EP/'outputs/r01/replay_receipt.json').read_text())
    assert sha(wfile)==replay['artifacts'][wfile.name]
    w=pd.read_parquet(wfile,columns=['era','date','day_i','industry_code','eligible','score'])
    base=json.loads((EP/'configs/r01_baseline.json').read_text())
    OUT.mkdir(exist_ok=True)
    artifacts={}
    for cap in [3,5,10]:
        c=dict(base,weekly_new_cap=cap)
        pool=ObservationPool(c);events=[];weeks=[]
        for (era,date,day),g in w.groupby(['era','date','day_i'],sort=True):
            states,ev=pool.step(era,date,int(day),g[['industry_code','eligible','score']].to_dict('records'))
            events.extend(ev)
            weeks.append(dict(era=era,date=date,new_industries=sum(x['event']=='NEW' for x in ev),in_pool=len(pool.active)))
        events=pd.DataFrame(events);weeks=pd.DataFrame(weeks)
        if cap==5:
            original=pd.read_parquet(EP/'outputs/r01/events.parquet')
            # Boundary EXIT date is explicit in original; compare all other events.
            cols=['era','industry_code','date','day_i','event','reason','observation_id','entry_day','entry_date','missing_reviews']
            def canonical(x):return x[x.reason.ne('CLASSIFICATION_BOUNDARY')][cols].sort_values(['date','industry_code','event']).reset_index(drop=True)
            pd.testing.assert_frame_equal(canonical(original),canonical(events),check_dtype=False)
            oldweeks=pd.read_parquet(EP/'outputs/r01/weekly_workload.parquet')
            pd.testing.assert_frame_equal(oldweeks[weeks.columns],weeks,check_dtype=False)
        for name,frame in [(f'cap{cap}_events.parquet',events),(f'cap{cap}_weeks.parquet',weeks)]:
            frame.to_parquet(OUT/name,index=False);artifacts[name]=sha(OUT/name)
    inputs=[wfile,EP/'configs/r01_baseline.json',EP/'src/r01_pool.py',Path(__file__),EP/'rounds/R01_capacity_control_plan.md']
    seal=dict(caps=[3,5,10],concurrency=30,main_reproduction='all non-boundary events and weekly counts equal',
              boundary_note='Control boundary exits recorded at first next-era review; no new alerts at boundary; main uses explicit boundary date',
              inputs={str(x):sha(x) for x in inputs},artifacts=artifacts)
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print('Capacity predictions sealed; cap5 main events and workload reproduced')


def evaluate():
    from matching_contract import Process,Alert,match_draft
    from post_alert_evaluation import post_alert_result,label_neighborhood_known
    from metric_accounting import summarize
    if (OUT/'evaluation.json').exists():raise FileExistsError('already evaluated')
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for filename,h in seal['inputs'].items():assert sha(Path(filename))==h
    for filename,h in seal['artifacts'].items():assert sha(OUT/filename)==h
    p=pd.read_parquet(EP/'outputs/r00_metric_denominators/full_process_registry.parquet')
    raw=pd.read_parquet(PRIOR/'daily_industries.parquet');asof=int(raw.day_i.max())
    groups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])}
    pmap=p.set_index('process_id');objects=[];byidentity={}
    for r in p.itertuples():
        obj=Process(r.process_id,f'{r.era}|{r.industry_code}',int(r.start_day_i),int(r.end_day_i),int(r.start_day_i),int(r.start_day_i+60),int(r.start_day_i-5),int(r.start_day_i+10),left_origin_uncertain=bool(r.left_origin_uncertain))
        objects.append(obj);byidentity.setdefault(obj.identity,[]).append(obj)
    registry=p[['process_id','family_id','mature','left_origin_uncertain']].to_dict('records')
    output=[]
    for cap in seal['caps']:
        e=pd.read_parquet(OUT/f'cap{cap}_events.parquet');new=e[e.event.eq('NEW')];alerts=[]
        for r in new.itertuples():
            identity=f'{r.era}|{r.industry_code}';g=groups[(r.era,r.industry_code)]
            days=g.day_i.to_numpy();v=g.nav.to_numpy();b=g.block.to_numpy(float,na_value=np.nan)
            candidates=[x for x in byidentity.get(identity,[]) if x.window_start<=r.day_i<=x.window_end]
            chosen=min(candidates,key=lambda x:(abs(x.origin-r.day_i),x.origin,x.process_id)) if candidates else None
            kwargs={} if chosen is None else dict(process_end=chosen.end,process_end_observed=not pmap.loc[chosen.process_id].right_censored)
            result=post_alert_result(days,v,b,r.day_i,asof,**kwargs)
            alerts.append(Alert(r.observation_id,identity,int(r.day_i),result['post_valid'],label_neighborhood_known(days,v,b,r.day_i,asof),evaluation_status=result['status']))
        matched=match_draft(objects,alerts);summary=summarize(registry,matched)
        pd.DataFrame(matched).to_parquet(OUT/f'cap{cap}_matched.parquet',index=False)
        if cap==5:
            old=json.loads((EP/'outputs/r01/evaluation.json').read_text())['summary']
            assert summary==old,'main evaluation differs'
        weeks=pd.read_parquet(OUT/f'cap{cap}_weeks.parquet')
        compact={k:v for k,v in summary.items() if k!='family_counts'}
        output.append(dict(cap=cap,summary=compact,workload=weeks[['new_industries','in_pool']].describe(percentiles=[.5,.9,.95,.99]).to_dict()))
    result=dict(comparisons=output,prediction_seal_sha=sha(OUT/'prediction_seal.json'),scope='Historical workload curve; not equal-workload information comparison',
                inputs={str(x):sha(x) for x in [PRIOR/'daily_industries.parquet',EP/'outputs/r00_metric_denominators/full_process_registry.parquet']})
    (OUT/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([dict(cap=x['cap'],alerts=x['summary']['unique_new_alerts'],precision=x['summary']['precision'],recall=x['summary']['recall_lower'],outcomes=x['summary']['outcomes']) for x in output]))


if __name__=='__main__':
    {'predict':predict,'evaluate':evaluate}[sys.argv[1]]()
