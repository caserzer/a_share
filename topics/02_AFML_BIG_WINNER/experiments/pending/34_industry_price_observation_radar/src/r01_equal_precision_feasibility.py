"""Necessary support bounds only; never choose a threshold using future outcomes."""
import json
import math
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/r01_equal_precision';out.mkdir(exist_ok=True)
    if (out/'feasibility.json').exists():raise FileExistsError('feasibility already recorded')
    configfile=EP/'configs/evaluation_registration.json'
    c=json.loads(configfile.read_text())['researcher_registered_not_user_confirmed']
    minimum=c['minimum_mature_evaluable_unique_alerts'];target=c['equal_precision_reference']
    required=math.ceil(minimum*target)
    calendarfile=Path(next(x for x in json.loads((PRIOR/'receipt.json').read_text())['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.read_parquet(calendarfile).sort_values('date').reset_index(drop=True);cal['day_i']=cal.index
    configs=[('capacity3','r01_capacity','cap3'),('main5','r01_capacity','cap5'),('capacity10','r01_capacity','cap10'),('delay5','r01_delay','delay5'),('delay10','r01_delay','delay10')]
    totals=[];prefixes=[];inputs=[configfile,calendarfile,EP/'rounds/R01_equal_precision_plan.md',Path(__file__)]
    for name,folder,prefix in configs:
        root=EP/'outputs'/folder;mf=root/f'{prefix}_matched.parquet';ef=root/f'{prefix}_events.parquet'
        f=pd.read_parquet(mf);events=pd.read_parquet(ef);new=events[events.event.eq('NEW')]
        f=f.merge(new[['observation_id','era','date']],left_on='alert_id',right_on='observation_id',validate='one_to_one')
        assert not f.outcome.str.contains('DUPLICATE').any()
        assert not f.loc[f.process_id.notna(),'process_id'].duplicated().any()
        known=f[f.new_observation_denominator]
        successes=int(known.recall_credit.sum());n=len(known)
        totals.append(dict(version=name,mature_evaluable=n,successes=successes,necessary_successes=required,
                           ideal_subset_precision_upper=min(1.,successes/minimum),
                           unknown=int(f.outcome.eq('UNKNOWN').sum()),immature=int(f.outcome.eq('IMMATURE').sum()),
                           status='INFEASIBLE_ON_EXISTING_KNOWN_ALERTS' if successes<required else 'NECESSARY_BOUND_ONLY'))
        for era,g in f.groupby('era'):
            for year in range(int(g.date.dt.year.min())+1,int(g.date.dt.year.max())+1):
                cut=cal[cal.date.dt.year.eq(year)].iloc[0]
                eligible=g[(g.day+c['uniform_alert_label_delay_sessions']<cut.day_i)]
                z=eligible[eligible.new_observation_denominator]
                n=len(z);s=int(z.recall_credit.sum());weeks=z.date.dt.to_period('W-SUN').nunique()
                status='INSUFFICIENT_SUPPORT' if n<minimum or weeks<c['minimum_alert_weeks'] else 'INSUFFICIENT_SUCCESSES' if s<required else 'NECESSARY_BOUND_ONLY'
                prefixes.append(dict(version=name,era=era,decision_date=str(cut.date.date()),mature_evaluable=n,
                                     evaluable_weeks=int(weeks),successes=s,unknown=int(eligible.outcome.eq('UNKNOWN').sum()),
                                     ideal_subset_precision_upper=min(1.,s/minimum),status=status))
        inputs.extend([mf,ef])
    assert all(r['status']!='NECESSARY_BOUND_ONLY' for r in prefixes+totals)
    pd.DataFrame(prefixes).to_parquet(out/'annual_prefix_support.parquet',index=False)
    result=dict(reference_precision=target,minimum_evaluable_alerts=minimum,necessary_successes=required,
                scope='Fixed-sequence publication subsets only; unknown labels are not failures; no state-machine threshold rerun',
                versions=totals,prefix_checks=len(prefixes),prefix_status_counts=pd.Series([x['status'] for x in prefixes]).value_counts().to_dict(),
                status='TARGET_UNREACHABLE_FOR_REGISTERED_FIXED_VERSIONS_NO_EQUAL_PRECISION_RANKING',
                inputs={str(x):sha(x) for x in inputs})
    (out/'feasibility.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':main()
