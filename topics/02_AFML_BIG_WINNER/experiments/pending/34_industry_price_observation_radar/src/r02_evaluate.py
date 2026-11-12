"""Evaluate sealed R02 predictions with frozen R00 and paired uncertainty."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from matching_contract import Process,Alert,match_draft
from post_alert_evaluation import post_alert_result,label_neighborhood_known,registered_rules
from metric_accounting import summarize
from paired_time_blocks import paired_interval


def main():
    out=EP/'outputs/r02'
    if (out/'evaluation.json').exists():raise FileExistsError('R02 evaluation exists')
    seal=json.loads((out/'prediction_seal.json').read_text())
    for f,h in seal['source'].items():assert sha(Path(f))==h
    for f,h in seal['artifacts'].items():assert sha(out/f)==h
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    p=pd.read_parquet(pfile);pmap=p.set_index('process_id')
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile);asof=int(raw.day_i.max())
    groups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])}
    objects=[];byidentity={}
    for r in p.itertuples():
        x=Process(r.process_id,f'{r.era}|{r.industry_code}',int(r.start_day_i),int(r.end_day_i),int(r.start_day_i),int(r.start_day_i+60),int(r.start_day_i-5),int(r.start_day_i+10),left_origin_uncertain=bool(r.left_origin_uncertain))
        objects.append(x);byidentity.setdefault(x.identity,[]).append(x)
    predictions=pd.read_parquet(out/'predictions.parquet');weeks=pd.read_parquet(EP/'outputs/r00_metric_denominators/full_week_denominators.parquet')
    registry=p[['process_id','family_id','mature','left_origin_uncertain']].to_dict('records')
    eligible=p[p.mature & ~p.left_origin_uncertain].copy();eligible['week']=eligible.start_date.dt.to_period('W-SUN').astype(str)
    results={};records={};successsets={}
    for arm in ['A','B']:
        new=predictions[predictions.arm.eq(arm)];alerts=[];meta={}
        for r in new.itertuples():
            identity=f'{r.era}|{r.industry_code}';g=groups[(r.era,r.industry_code)]
            days=g.day_i.to_numpy();v=g.nav.to_numpy();blocks=g.block.to_numpy(float,na_value=np.nan)
            candidates=[x for x in byidentity.get(identity,[]) if x.window_start<=r.day_i<=x.window_end]
            chosen=min(candidates,key=lambda x:(abs(x.origin-r.day_i),x.origin,x.process_id)) if candidates else None
            kwargs={} if chosen is None else dict(process_end=chosen.end,process_end_observed=not pmap.loc[chosen.process_id].right_censored)
            assessed=post_alert_result(days,v,blocks,r.day_i,asof,**kwargs)
            coverage=label_neighborhood_known(days,v,blocks,r.day_i,asof)
            alerts.append(Alert(r.observation_id,identity,int(r.day_i),assessed['post_valid'],coverage,evaluation_status=assessed['status']))
            history=g.set_index('day_i').reindex(range(r.day_i-60,r.day_i+1)).nav
            weak=history.iloc[-1]/history.iloc[0]-1<=0 or history.iloc[-1]/history.max()-1<=-.1
            delta=None if chosen is None else int(r.day_i-chosen.origin)
            gain=None if delta is None or delta<0 else float(history.iloc[-1]/g.loc[g.day_i.eq(chosen.origin),'nav'].iloc[0]-1)
            meta[r.observation_id]=dict(era=r.era,industry_code=r.industry_code,date=r.date,r20=r.r20,delta20=r.delta20,
                                       hint_kind='WARMING' if weak else 'HEATING',label_coverage_known=coverage,
                                       delta_from_origin=delta,prior_gain_from_origin=gain,post_evaluation=assessed['status'])
        matched=match_draft(objects,alerts);f=pd.DataFrame([dict(**x,**meta[x['alert_id']]) for x in matched])
        f.to_parquet(out/f'{arm}_evaluated.parquet',index=False);records[arm]=f
        summary=summarize(registry,matched);successsets[arm]=set(f.loc[f.recall_credit,'process_id'])
        results[arm]=dict(summary={k:v for k,v in summary.items() if k!='family_counts'},
                          matched_timing=f.delta_from_origin.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict(),
                          matched_prior_gain=f.prior_gain_from_origin.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict())
        f['week']=f.date.dt.to_period('W-SUN').astype(str)
        wk=f.groupby(['era','week']).agg(ps=('recall_credit','sum'),pn=('new_observation_denominator','sum'))
        rk=eligible.assign(hit=eligible.process_id.isin(successsets[arm])).groupby(['era','week']).hit.sum()
        for col in ['ps','pn','rs','rn']:weeks[f'{arm}_{col}']=0
        for i,r in weeks.iterrows():
            key=(r.era,r.week)
            if key in wk.index:weeks.loc[i,[f'{arm}_ps',f'{arm}_pn']]=wk.loc[key].to_numpy()
            if key in rk.index:weeks.loc[i,f'{arm}_rs']=rk.loc[key]
            weeks.loc[i,f'{arm}_rn']=r.recall_denominator
        assert int(weeks[f'{arm}_pn'].sum())==summary['precision_denominator']
        assert int(weeks[f'{arm}_rs'].sum())==summary['recall_numerator']
    columns=[f'{arm}_{c}' for arm in ['A','B'] for c in ['ps','pn','rs','rn']]
    c=registered_rules();arrays=[g.sort_values('week')[columns].to_numpy(float) for _,g in weeks.groupby('era')]
    intervals=paired_interval(arrays,c['block_bootstrap_weeks'],c['bootstrap_repetitions'],c['bootstrap_seed'],c['confidence_level'])
    weeks.to_parquet(out/'paired_week_counts.parquet',index=False)
    a=results['A']['summary'];b=results['B']['summary']
    point_improvement=b['recall_lower']>a['recall_lower'] and b['precision']>=a['precision']
    verdict='STOP_CHANGE_RANKING_BRANCH' if not point_improvement else 'INCREMENT_UNCERTAIN' if intervals['B_minus_A_recall']['interval'][0]<=0 else 'POSITIVE_HISTORICAL_INCREMENT_REQUIRES_ALL_GATES'
    result=dict(status=verdict,arms=results,paired_intervals=intervals,
                paired_successes=dict(common=len(successsets['A']&successsets['B']),B_added=len(successsets['B']-successsets['A']),B_lost=len(successsets['A']-successsets['B'])),
                equal_weekly_new_counts=seal['equal_weekly_new_counts'],new_per_arm=seal['new_per_arm'],
                scope='Historical information diagnostic; no operational-pool or independent forward validation',
                pending=['strata and secondary market-relative paths','case and missing-process review'],
                inputs={str(x):sha(x) for x in [rawfile,pfile,out/'prediction_seal.json',Path(__file__),EP/'src/paired_time_blocks.py']})
    (out/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=verdict,arms={k:{x:v['summary'][x] for x in ['precision','precision_numerator','precision_denominator','recall_lower','outcomes']} for k,v in results.items()},paired_intervals=intervals,paired_successes=result['paired_successes']),ensure_ascii=False))


if __name__=='__main__':main()
