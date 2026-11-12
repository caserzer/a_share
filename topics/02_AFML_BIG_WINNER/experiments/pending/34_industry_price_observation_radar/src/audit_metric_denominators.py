"""Audit the complete truth registry with zero submitted signals; no method result."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP, sha
from metric_accounting import summarize
from post_alert_evaluation import registered_rules


def main():
    source=EP/'outputs/r00_price_process_v03/processes.parquet'
    coverage=EP/'outputs/r00_coverage/evaluation_coverage.parquet'
    p=pd.read_parquet(source);q=pd.read_parquet(coverage,columns=['era','date','day_i'])
    asof=int(q.day_i.max());delay=registered_rules()['uniform_process_recall_delay_sessions']
    p['mature']=asof-p.start_day_i>=delay
    p['recall_support_status']='MATURE_KNOWN_ORIGIN'
    p.loc[p.left_origin_uncertain,'recall_support_status']='MATURE_LEFT_UNKNOWN'
    p.loc[~p.mature,'recall_support_status']='IMMATURE'
    result=summarize(p[['process_id','family_id','mature','left_origin_uncertain']].to_dict('records'),[])
    counts=p.recall_support_status.value_counts().to_dict()
    assert result['process_catalog']==sum(counts.values())==len(p)
    eligible=p[p.mature&~p.left_origin_uncertain]
    assert result['mature_known_processes']==len(eligible)
    assert result['family_denominator']==eligible.family_id.nunique()
    weeks=q.assign(week=q.date.dt.to_period('W-SUN').astype(str))[['era','week']].drop_duplicates()
    actual=eligible.assign(week=eligible.start_date.dt.to_period('W-SUN').astype(str)).groupby(['era','week']).size().rename('recall_denominator')
    weeks=weeks.merge(actual.reset_index(),on=['era','week'],how='left')
    weeks.recall_denominator=weeks.recall_denominator.fillna(0).astype(int)
    assert weeks.recall_denominator.sum()==len(eligible)
    out=EP/'outputs/r00_metric_denominators';out.mkdir(exist_ok=True)
    p.to_parquet(out/'full_process_registry.parquet',index=False)
    weeks.to_parquet(out/'full_week_denominators.parquet',index=False)
    sources=[source,coverage,EP/'configs/evaluation_registration.json',EP/'src/metric_accounting.py',Path(__file__)]
    audit=dict(status='DENOMINATORS_ONLY_NO_METHOD_EVALUATED',asof_date=str(q.date.max().date()),
               process_catalog=len(p),support_status=counts,mature_known_families=int(eligible.family_id.nunique()),
               all_calendar_weeks=len(weeks),zero_process_weeks=int(weeks.recall_denominator.eq(0).sum()),
               tests='49 unit and semantic tests passed before this audit',
               inputs={str(f):sha(f) for f in sources},artifacts={f.name:sha(f) for f in sorted(out.glob('*.parquet'))})
    (out/'receipt.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:audit[k] for k in ['process_catalog','support_status','mature_known_families','all_calendar_weeks','zero_process_weeks']},ensure_ascii=False))


if __name__=='__main__':main()
