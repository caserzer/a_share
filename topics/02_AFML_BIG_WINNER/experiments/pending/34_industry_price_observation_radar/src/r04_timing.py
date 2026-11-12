"""S03 timing evidence for all existing alerts, never new signals."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from post_alert_evaluation import post_alert_result,registered_rules


def milestone(group,day,asof,end,rules,end_observed=True):
    horizon=rules['post_alert_peak_horizon'];threshold=rules['post_alert_peak_min_return']
    base=None;block=None;seen=[]
    for offset in range(horizon+1):
        t=day+offset
        if end is not None and t>end:return None,'PROCESS_ENDED' if end_observed else 'UNKNOWN_PROCESS_CENSORED',seen
        if t>asof:return None,'ASOF_INCOMPLETE',seen
        if t not in group.index:return None,'UNKNOWN_PATH',seen
        r=group.loc[t];v=r.nav;b=r.block
        if not np.isfinite(v) or v<=0 or pd.isna(b):return None,'UNKNOWN_PATH',seen
        if offset==0:base=v;block=b;continue
        if b!=block:return None,'UNKNOWN_PATH',seen
        gain=v/base-1;seen.append(float(gain))
        if gain>=threshold:return offset,'REACHED',seen
    return None,'NOT_REACHED_FULL_WINDOW',seen


def distribution(frame,column):
    v=frame[column].dropna()
    return dict(total=len(frame),computable=len(v),not_computable=len(frame)-len(v),
                quantiles={} if not len(v) else {str(k):float(x) for k,x in v.quantile([0,.1,.5,.9,.95,1]).items()})


def main():
    out=EP/'outputs/r04/timing';out.mkdir(exist_ok=True)
    if (out/'summary.json').exists():raise FileExistsError('already evaluated')
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile);asof=int(raw.day_i.max())
    groups={k:g.set_index('day_i').sort_index() for k,g in raw.groupby(['era','industry_code'])}
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';p=pd.read_parquet(pfile).set_index('process_id')
    plan=EP/'rounds/S03_timing_accounting_plan.md';config=EP/'configs/evaluation_registration.json'
    inputs={str(f):sha(f) for f in [rawfile,pfile,plan,config]};rules=registered_rules()
    specs=[('r04_'+arm,EP/'outputs/r04'/(arm+'_evaluated.parquet'),EP/'outputs/s01/variants'/('r04_'+arm)/'r01_late_records.parquet') for arm in ['A','B']]
    results={};tables={}
    for name,primaryfile,latefile in specs:
        primary=pd.read_parquet(primaryfile);late=pd.read_parquet(latefile).set_index('alert_id');records=[]
        for f in [primaryfile,latefile]:inputs[str(f)]=sha(f)
        for r in primary.itertuples():
            pid=r.process_id;source='TIMELY' if pd.notna(pid) else 'NONE';outcome=r.outcome
            if source=='NONE' and r.alert_id in late.index and pd.notna(late.loc[r.alert_id].process_id):
                pid=late.loc[r.alert_id].process_id;source='LATE';outcome=late.loc[r.alert_id].outcome
            proc=p.loc[pid] if pd.notna(pid) else None
            g=groups[(r.era,r.industry_code)];day=int(r.day)
            delta=None if proc is None else day-int(proc.start_day_i)
            gain=None;gainstatus='NO_REFERENCE' if proc is None else 'PRE_ORIGIN_NOT_APPLICABLE' if delta<0 else 'UNKNOWN_PATH'
            if delta is not None and delta>=0:
                t=g.loc[int(proc.start_day_i):day]
                if np.array_equal(t.index.to_numpy(),np.arange(int(proc.start_day_i),day+1)) and np.isfinite(t.nav).all() and t.nav.gt(0).all() and t.block.notna().all() and t.block.nunique()==1:
                    gain=float(t.nav.iloc[-1]/t.nav.iloc[0]-1);gainstatus='COMPUTABLE'
            end=None if proc is None else int(proc.end_day_i)
            hit,status,seen=milestone(g,day,asof,end,rules,proc is None or not proc.right_censored)
            if hit is not None:
                assert seen[-1]>=rules['post_alert_peak_min_return'] and all(x<rules['post_alert_peak_min_return'] for x in seen[:-1])
                assert end is None or day+hit<=end
            kw={} if proc is None else dict(process_end=end,process_end_observed=not proc.right_censored)
            assessed=post_alert_result(g.index.to_numpy(),g.nav.to_numpy(),g.block.to_numpy(float,na_value=np.nan),day,asof,**kw)
            records.append(dict(alert_id=r.alert_id,era=r.era,industry_code=r.industry_code,date=r.date,day=day,
                process_id=pid,reference=source,reference_outcome=outcome,primary_outcome=r.outcome,
                delta_from_origin=delta,prior_gain=gain,prior_gain_status=gainstatus,
                milestone_sessions=hit,milestone_status=status,post_status=assessed['status'],
                full_confirmation_sessions=rules['post_alert_horizon'] if assessed['status']=='POST_VALID' else None,
                registered_maturity_sessions=rules['uniform_alert_label_delay_sessions']))
        f=pd.DataFrame(records);assert len(f)==len(primary) and f.alert_id.is_unique
        folder=out/name;folder.mkdir(exist_ok=True);f.to_parquet(folder/'timing.parquet',index=False)
        parts={}
        for (ref,status),g in f.groupby(['reference','reference_outcome']):
            parts[ref+'|'+status]=dict(total=len(g),prior_gain_status=g.prior_gain_status.value_counts().to_dict(),
                milestone_status=g.milestone_status.value_counts().to_dict(),post_status=g.post_status.value_counts().to_dict(),
                distributions={k:distribution(g,k) for k in ['delta_from_origin','prior_gain','milestone_sessions','full_confirmation_sessions']})
        assert sum(x['total'] for x in parts.values())==len(f)
        results[name]=dict(total=len(f),groups=parts);tables[name]=f
        print(name,len(f),flush=True)
    receipt=dict(scope='S03 supplemental descriptive timing',inputs=inputs,source_sha256=sha(Path(__file__)),main_reproduction=None,results=results)
    (out/'summary.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
