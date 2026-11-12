"""Supplement R01 late coverage without changing any primary result."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from matching_contract import Process,Alert
from post_alert_evaluation import post_alert_result
from late_supplement import neighborhood_known,match_late


def main():
    out=EP/'outputs/s01';out.mkdir(exist_ok=True)
    if (out/'r01_result.json').exists():raise FileExistsError('supplement already evaluated')
    sealfile=EP/'protocols/s01_v1/seal.json';seal=json.loads(sealfile.read_text())
    for f,h in seal['files'].items():assert sha(Path(f))==h
    primaryfile=EP/'outputs/r01/evaluated_new_observations.parquet';primary=pd.read_parquet(primaryfile)
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';p=pd.read_parquet(pfile);pm=p.set_index('process_id')
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile);asof=int(raw.day_i.max())
    groups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])}
    objects=[];byidentity={}
    for r in p.itertuples():
        x=Process(r.process_id,f'{r.era}|{r.industry_code}',int(r.start_day_i),int(r.end_day_i),int(r.start_day_i),int(r.start_day_i+60),int(r.start_day_i-5),int(r.start_day_i+10),left_origin_uncertain=bool(r.left_origin_uncertain))
        objects.append(x);byidentity.setdefault(x.identity,[]).append(x)
    assigned=primary[primary.process_id.notna()].sort_values(['day','alert_id']).drop_duplicates('process_id')
    claims=dict(zip(assigned.process_id,assigned.alert_id));residual=primary[primary.process_id.isna()]
    alerts=[];meta={}
    for r in residual.itertuples():
        identity=f'{r.era}|{r.industry_code}';g=groups[(r.era,r.industry_code)]
        ds=g.day_i.to_numpy();v=g.nav.to_numpy();b=g.block.to_numpy(float,na_value=np.nan)
        candidates=[x for x in byidentity.get(identity,[]) if 11<=r.day-x.origin<=60]
        chosen=min(candidates,key=lambda x:(abs(r.day-x.origin),x.origin,x.process_id)) if candidates else None
        kwargs={} if chosen is None else dict(process_end=chosen.end,process_end_observed=not pm.loc[chosen.process_id].right_censored)
        assessed=post_alert_result(ds,v,b,r.day,asof,**kwargs);coverage=neighborhood_known(ds,v,b,r.day,asof)
        alerts.append(Alert(r.alert_id,identity,int(r.day),assessed['post_valid'],coverage,evaluation_status=assessed['status']))
        meta[r.alert_id]=dict(era=r.era,industry_code=r.industry_code,date=r.date,post_status=assessed['status'],neighborhood_known=coverage,
                             late_delta=None if chosen is None else r.day-chosen.origin)
    records=match_late(objects,alerts,claims);f=pd.DataFrame([dict(**r,**meta[r['alert_id']]) for r in records])
    f.to_parquet(out/'r01_late_records.parquet',index=False)
    primaryhits=set(primary.loc[primary.recall_credit,'process_id']);latehits=set(f.loc[f.late_credit,'process_id'])
    assert not primaryhits&latehits
    mature=p[(asof-p.start_day_i>=125)&~p.left_origin_uncertain].copy();knownids=set(mature.process_id)
    unresolved=set(primary.loc[primary.outcome.eq('UNKNOWN') & primary.process_id.notna(),'process_id'])|set(f.loc[f.outcome.eq('UNKNOWN') & f.process_id.notna(),'process_id'])
    unresolved&=knownids;unresolved-=primaryhits|latehits
    mature['primary_hit']=mature.process_id.isin(primaryhits);mature['late_hit']=mature.process_id.isin(latehits);mature['unresolved']=mature.process_id.isin(unresolved)
    mature.to_parquet(out/'r01_125day_process_coverage.parquet',index=False)
    eventfile=EP/'outputs/r01/events.parquet';events=pd.read_parquet(eventfile);new=events[events.event.eq('NEW')].sort_values(['day_i','observation_id'])
    reentered=new.duplicated(['era','industry_code']);linked=primary[['alert_id','process_id']].copy()
    linked=linked.set_index('alert_id');late_map=f.set_index('alert_id').process_id
    linked['process_id']=linked.process_id.fillna(late_map)
    new['is_reentry']=reentered;new['process_id']=new.observation_id.map(linked.process_id)
    new.to_parquet(out/'r01_reentry_attribution.parquet',index=False)
    n=len(mature);ph=int(mature.primary_hit.sum());lh=int(mature.late_hit.sum());den=int(f.denominator.sum())
    result=dict(scope='S01 post-result supplemental accounting; primary metrics unchanged',primary_alerts=len(primary),reserved_primary_assignments=int(primary.process_id.notna().sum()),
                residual_alerts=len(f),outcomes=f.outcome.value_counts().to_dict(),supplement_evaluable=den,late_success_alerts=int(f.late_credit.sum()),
                supplement_effectiveness=None if not den else float(f.late_credit.sum()/den),
                process_maturity_sessions=125,process_denominator=n,primary_success_on_125day_denominator=ph,unique_added_late_coverage=lh,
                late_coverage=lh/n,combined_coverage=(ph+lh)/n,unresolved_processes=len(unresolved),combined_coverage_upper=(ph+lh+len(unresolved))/n,
                not125mature=int((asof-p.start_day_i<125).sum()),left_origin_unknown125=int(((asof-p.start_day_i>=125)&p.left_origin_uncertain).sum()),
                repeat_known=int(f.outcome.eq('DUPLICATE').sum()),repeat_unknown=int(f.outcome.eq('UNKNOWN_DUPLICATE').sum()),
                operational=dict(updates=int(events.event.eq('UPDATE').sum()),unknown_suspended_updates=int(events.reason.eq('SUSPENDED_UNKNOWN').sum()),
                                 reentry_new_alerts=int(reentered.sum()),reentries_with_process_reference=int((reentered & new.process_id.notna()).sum())),
                timing_matched_late=f.late_delta.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict(),
                inputs={str(x):sha(x) for x in [sealfile,primaryfile,pfile,rawfile,eventfile,Path(__file__)]})
    assert result['reserved_primary_assignments']+len(f)==len(primary)
    (out/'r01_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':main()
