"""Delay evaluation using the same frozen matching and accounting as capacity controls."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
OUT=EP/'outputs/r01_delay'

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
    for cap in seal['delays']:
        e=pd.read_parquet(OUT/f'delay{cap}_events.parquet');new=e[e.event.eq('NEW')];alerts=[]
        for r in new.itertuples():
            identity=f'{r.era}|{r.industry_code}';g=groups[(r.era,r.industry_code)]
            days=g.day_i.to_numpy();v=g.nav.to_numpy();b=g.block.to_numpy(float,na_value=np.nan)
            candidates=[x for x in byidentity.get(identity,[]) if x.window_start<=r.day_i<=x.window_end]
            chosen=min(candidates,key=lambda x:(abs(x.origin-r.day_i),x.origin,x.process_id)) if candidates else None
            kwargs={} if chosen is None else dict(process_end=chosen.end,process_end_observed=not pmap.loc[chosen.process_id].right_censored)
            result=post_alert_result(days,v,b,r.day_i,asof,**kwargs)
            alerts.append(Alert(r.observation_id,identity,int(r.day_i),result['post_valid'],label_neighborhood_known(days,v,b,r.day_i,asof),evaluation_status=result['status']))
        matched=match_draft(objects,alerts);summary=summarize(registry,matched)
        pd.DataFrame(matched).to_parquet(OUT/f'delay{cap}_matched.parquet',index=False)
        if cap==0:
            old=json.loads((EP/'outputs/r01/evaluation.json').read_text())['summary']
            assert summary==old,'main evaluation differs'
        weeks=pd.read_parquet(OUT/f'delay{cap}_weeks.parquet')
        compact={k:v for k,v in summary.items() if k!='family_counts'}
        output.append(dict(delay=cap,summary=compact,workload=weeks[['new_industries','in_pool']].describe(percentiles=[.5,.9,.95,.99]).to_dict()))
    result=dict(comparisons=output,prediction_seal_sha=sha(OUT/'prediction_seal.json'),scope='Historical confirmation-delay comparison; not equal-workload information comparison',
                inputs={str(x):sha(x) for x in [PRIOR/'daily_industries.parquet',EP/'outputs/r00_metric_denominators/full_process_registry.parquet']})
    (OUT/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([dict(delay=x['delay'],alerts=x['summary']['unique_new_alerts'],precision=x['summary']['precision'],recall=x['summary']['recall_lower'],outcomes=x['summary']['outcomes']) for x in output]))


if __name__=='__main__':evaluate()
