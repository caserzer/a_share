"""Connect sealed R01 observations to sealed R00; no signal modification."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from matching_contract import Process,Alert,match_draft
from post_alert_evaluation import post_alert_result,label_neighborhood_known,registered_rules
from metric_accounting import summarize,time_block_interval


def main():
    out=EP/'outputs/r01'
    if (out/'evaluation.json').exists():raise FileExistsError('R01 evaluation already exists')
    subprocess.run([sys.executable,str(EP/'src/seal_r00.py'),'verify'],check=True)
    pred=json.loads((out/'prediction_seal.json').read_text())
    for filename,h in pred['files'].items():
        if sha(Path(filename))!=h:raise ValueError('prediction drift')
    replay=json.loads((out/'replay_receipt.json').read_text())
    for filename,h in replay['artifacts'].items():
        if sha(out/filename)!=h:raise ValueError('replay drift')
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';p=pd.read_parquet(pfile)
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile)
    asof=int(raw.day_i.max());groups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])}
    objects=[];byidentity={};pmap=p.set_index('process_id')
    for r in p.itertuples():
        obj=Process(r.process_id,f'{r.era}|{r.industry_code}',int(r.start_day_i),int(r.end_day_i),int(r.start_day_i),int(r.start_day_i+60),int(r.start_day_i-5),int(r.start_day_i+10),left_origin_uncertain=bool(r.left_origin_uncertain))
        objects.append(obj);byidentity.setdefault(obj.identity,[]).append(obj)
    ev=pd.read_parquet(out/'events.parquet');new=ev[ev.event.eq('NEW')].sort_values(['day_i','observation_id'])
    alerts=[];meta={};c=registered_rules()
    for r in new.itertuples():
        identity=f'{r.era}|{r.industry_code}';g=groups[(r.era,r.industry_code)]
        indices=g.day_i.to_numpy();v=g.nav.to_numpy();blocks=g.block.to_numpy(float,na_value=np.nan)
        candidates=[x for x in byidentity.get(identity,[]) if x.window_start<=r.day_i<=x.window_end]
        chosen=min(candidates,key=lambda x:(abs(x.origin-r.day_i),x.origin,x.process_id)) if candidates else None
        if chosen:
            row=pmap.loc[chosen.process_id]
            assessed=post_alert_result(indices,v,blocks,r.day_i,asof,process_end=chosen.end,process_end_observed=not row.right_censored)
        else:assessed=post_alert_result(indices,v,blocks,r.day_i,asof)
        coverage=label_neighborhood_known(indices,v,blocks,r.day_i,asof)
        alerts.append(Alert(r.observation_id,identity,int(r.day_i),assessed['post_valid'],coverage,evaluation_status=assessed['status']))
        history=g.set_index('day_i').reindex(range(r.day_i-60,r.day_i+1)).nav
        assert history.notna().all()
        weak=history.iloc[-1]/history.iloc[0]-1<=0 or history.iloc[-1]/history.max()-1<=-.10
        meta[r.observation_id]=dict(date=r.date,era=r.era,industry_code=r.industry_code,hint_kind='WARMING' if weak else 'HEATING',
                                   label_coverage_known=coverage,post_evaluation=assessed['status'],
                                   delta_from_origin=None if chosen is None else int(r.day_i-chosen.origin))
    results=match_draft(objects,alerts)
    records=[dict(**r,**meta[r['alert_id']]) for r in results]
    f=pd.DataFrame(records);f.to_parquet(out/'evaluated_new_observations.parquet',index=False)
    registry=p[['process_id','family_id','mature','left_origin_uncertain']].to_dict('records')
    summary=summarize(registry,results)
    eligible=p[p.mature&~p.left_origin_uncertain].copy();hits=set(f.loc[f.recall_credit,'process_id'])
    eligible['hit']=eligible.process_id.isin(hits)
    annual=[]
    for year in sorted(set(p.start_date.dt.year)|set(f.date.dt.year)):
        a=f[f.date.dt.year.eq(year)];b=eligible[eligible.start_date.dt.year.eq(year)]
        den=int(a.new_observation_denominator.sum());num=int(a.recall_credit.sum())
        annual.append(dict(year=int(year),new_alerts=len(a),evaluable_alerts=den,successes=num,precision=None if not den else num/den,
                           known_processes=len(b),recalled=int(b.hit.sum()),recall_lower=None if not len(b) else float(b.hit.mean()),outcomes=a.outcome.value_counts().to_dict()))
    types=[]
    for kind in ['WARMING','HEATING']:
        a=f[f.hint_kind.eq(kind)];b=eligible[eligible.kind.eq(kind)];den=int(a.new_observation_denominator.sum())
        types.append(dict(kind=kind,new_alerts=len(a),evaluable_alerts=den,successes=int(a.recall_credit.sum()),
                          precision=None if not den else float(a.recall_credit.sum()/den),known_processes=len(b),recalled=int(b.hit.sum()),recall_lower=None if not len(b) else float(b.hit.mean())))
    weeks=pd.read_parquet(EP/'outputs/r00_metric_denominators/full_week_denominators.parquet')
    f['week']=f.date.dt.to_period('W-SUN').astype(str);eligible['week']=eligible.start_date.dt.to_period('W-SUN').astype(str)
    for name in ['precision_success','precision_n','recall_success']:weeks[name]=0
    wk=f.groupby(['era','week']).agg(precision_success=('recall_credit','sum'),precision_n=('new_observation_denominator','sum'))
    rk=eligible.groupby(['era','week']).hit.sum()
    for i,r in weeks.iterrows():
        key=(r.era,r.week)
        if key in wk.index:weeks.loc[i,['precision_success','precision_n']]=wk.loc[key].to_numpy()
        if key in rk.index:weeks.loc[i,'recall_success']=rk.loc[key]
    assert weeks.precision_n.sum()==summary['precision_denominator']
    assert weeks.recall_success.sum()==summary['recall_numerator']
    arrays=[g.sort_values('week')[['precision_success','precision_n','recall_success','recall_denominator']].to_numpy(float) for _,g in weeks.groupby('era')]
    interval=time_block_interval(arrays,c['block_bootstrap_weeks'],c['bootstrap_repetitions'],c['bootstrap_seed'],c['confidence_level'])
    weeks.to_parquet(out/'evaluation_week_counts.parquet',index=False)
    workload=pd.read_parquet(out/'weekly_workload.parquet')
    verdict='FAIL_MAIN_TARGET' if summary['precision'] is not None and (summary['precision']<c['precision_target'] or summary['recall_lower']<c['timely_process_recall_target']) else 'REQUIRES_ALL_REGISTERED_GATES'
    result=dict(status=verdict,scope='Historical simulation; no independent forward validation',summary=summary,interval=interval,annual=annual,types=types,
                workload=workload[['new_industries','in_pool']].describe(percentiles=[.5,.9,.95,.99]).to_dict(),
                matched_delta=f.delta_from_origin.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict(),
                hint_type_attribution='past-only weak/nonweak at alert; recall by true process kind',
                pending=['market and quality strata','failure and omission casebook','capacity and delay controls','equal-precision comparison'],
                inputs={str(x):sha(x) for x in [pfile,rawfile,out/'replay_receipt.json',out/'prediction_seal.json',EP/'rounds/R01_evaluation_attribution.md',Path(__file__)]})
    (out/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=verdict,precision=summary['precision'],recall_lower=summary['recall_lower'],recall_upper=summary['recall_upper'],outcomes=summary['outcomes'],interval=interval),ensure_ascii=False))


if __name__=='__main__':main()
