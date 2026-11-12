"""Omniscient interval scheduling bound, never a signal backtest."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def allocate(jobs, cap):
    used={};result=[]
    for job in sorted(jobs,key=lambda x:(x['weeks'][-1],x['weeks'][0],x['process_id'])):
        for week in job['weeks']:
            if used.get(week,0)<cap:
                used[week]=used.get(week,0)+1
                result.append({k:v for k,v in job.items() if k!='weeks'}|dict(cap=cap,week=week))
                break
    return result


def main():
    source=EP/'outputs/r00_price_process_v03/processes.parquet'
    p=pd.read_parquet(source);unknown=int(p.left_origin_uncertain.sum());p=p[~p.left_origin_uncertain]
    r=json.loads((PRIOR/'receipt.json').read_text());calendar=next(Path(x) for x in r['inputs'] if x.endswith('/calendar.parquet'))
    days=pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values();jobs=[]
    for x in p.itertuples():
        lo=max(x.start_day_i-5,x.start_day_i-x.start+60);hi=x.start_day_i+10
        weeks=sorted(set(days[lo:hi+1].to_period('W-SUN').astype(str)))
        jobs.append(dict(process_id=x.process_id,era=x.era,industry_code=x.industry_code,weeks=weeks))
    rows=[];results=[]
    for cap in [3,5,10]:
        f=pd.DataFrame(allocate(jobs,cap));rows.append(f)
        results.append(dict(cap=cap,known_origin_processes=len(p),unknown_origin_processes=unknown,
                            oracle_matched=len(f),optimistic_recall_ceiling=len(f)/len(p),
                            duplicate_industry_week_assignments=int(f.duplicated(['era','industry_code','week']).sum())))
    out=EP/'outputs/r00_v03_support'
    pd.concat(rows,ignore_index=True).to_parquet(out/'capacity_oracle_assignments.parquet',index=False)
    (out/'capacity_oracle.json').write_text(json.dumps(results,indent=2)+'\n')
    files=[source,calendar,Path(__file__),EP/'rounds/R00_capacity_feasibility.md']
    (out/'capacity_oracle_receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in files},
        note='Perfect information, no post-alert effectiveness filter; not an achievable forecast'),indent=2)+'\n')
    print(json.dumps(results))


if __name__=='__main__':main()
