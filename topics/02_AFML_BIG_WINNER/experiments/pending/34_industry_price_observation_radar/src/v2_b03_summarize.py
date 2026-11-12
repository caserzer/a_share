"""Prespecified paired uncertainty, discrete precision floor, delay costs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    root=EP/'outputs/v2_b03';out=root/'comparison'
    if out.exists():raise FileExistsError('Preserve comparison')
    out.mkdir();rows=[];procs={};quality={};burdens={};inputs={}
    for quota in (1,3,5):
        for delay in (0,1):
            for arm in ('A','B'):
                run=root/f'q{quota}_d{delay}'/arm
                files=[run/'evaluation/summary.json',run/'evaluation/process_coverage.parquet',run/'evaluation/event_quality.parquet',run/'weekly_burden.csv']
                inputs.update({str(f):sha(f) for f in files})
                s=json.loads(files[0].read_text());key=(quota,delay,arm)
                procs[key]=pd.read_parquet(files[1]);quality[key]=pd.read_parquet(files[2]);burdens[key]=pd.read_csv(files[3])
                rows.append(dict(quota=quota,delay=delay,arm=arm,new=s['new_total'],unknown=s['new_unknown'],evaluable=s['new_evaluable'],effective=s['new_effective'],
                    precision=s['new_effective_rate'],processes=s['known_processes'],covered=s['covered'],coverage=s['coverage'],timely=s['coverage_timing'].get('TIMELY',0),
                    mean_pool=burdens[key].pool.mean(),updates=burdens[key].updates.sum(),sample_support=s['new_evaluable']>=50))
            assert burdens[(quota,delay,'A')].new.equals(burdens[(quota,delay,'B')].new)
    table=pd.DataFrame(rows);table.to_csv(out/'all_comparisons.csv',index=False)
    first=burdens[(5,0,'A')].date.min();last=burdens[(5,0,'A')].date.max()
    weeks=pd.period_range(first,last,freq='W-SUN');wi={str(v):i for i,v in enumerate(weeks)};n=len(weeks)
    def vectors(arm):
        x=np.zeros((n,6));p=procs[(5,0,arm)];q=quality[(5,0,arm)]
        for r in p.itertuples():
            i=wi[str(pd.Period(r.start,freq='W-SUN'))];x[i,0]+=r.covered;x[i,1]+=1;x[i,2]+=r.timing=='TIMELY';x[i,3]+=1
        for r in q[q.kind.eq('NEW')&~q.status.eq('UNKNOWN')].itertuples():
            i=wi[str(pd.Period(r.date,freq='W-SUN'))];x[i,4]+=r.status in ('TIMELY','LATE');x[i,5]+=1
        return x
    a,b=vectors('A'),vectors('B');rng=np.random.default_rng(3403);diffs=[]
    for _ in range(2000):
        starts=rng.integers(0,n,size=(n+12)//13)
        ix=((starts[:,None]+np.arange(13))%n).ravel()[:n]
        aa=a[ix].sum(axis=0);bb=b[ix].sum(axis=0)
        diffs.append(bb[[0,2,4]]/bb[[1,3,5]]-aa[[0,2,4]]/aa[[1,3,5]])
    d=np.array(diffs);aa=a.sum(axis=0);bb=b.sum(axis=0);point=bb[[0,2,4]]/bb[[1,3,5]]-aa[[0,2,4]]/aa[[1,3,5]]
    uncertainty={name:dict(B_minus_A=float(point[k]),interval_95=np.quantile(d[:,k],[.025,.975]).tolist()) for k,name in enumerate(['coverage','timely_coverage','new_precision'])}
    floors=[]
    for delay in (0,1):
        for floor in (.30,.35,.40):
            row=dict(delay=delay,precision_floor=floor)
            for arm in ('A','B'):
                eligible=table[table.delay.eq(delay)&table.arm.eq(arm)&table.precision.ge(floor)]
                row[arm]=None if eligible.empty else eligible.sort_values(['coverage','quota'],ascending=[False,True]).iloc[0].to_dict()
            floors.append(row)
    calfile=Path(next(x for x in json.loads((PRIOR/'receipt.json').read_text())['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calfile).date);delay_cost=[]
    for quota in (1,3,5):
        for arm in ('A','B'):
            p0=procs[(quota,0,arm)].set_index('process');p1=procs[(quota,1,arm)].set_index('process')
            both=p0.covered&p1.covered
            dt=cal.get_indexer(pd.to_datetime(p1.loc[both,'first_date']))-cal.get_indexer(pd.to_datetime(p0.loc[both,'first_date']))
            delay_cost.append(dict(quota=quota,arm=arm,lost=int((p0.covered&~p1.covered).sum()),gained=int((~p0.covered&p1.covered).sum()),
                common=int(both.sum()),common_delay_quantiles={str(q):float(np.quantile(dt,q)) for q in (.1,.5,.9)},
                timely_change=int(p1.timing.eq('TIMELY').sum()-p0.timing.eq('TIMELY').sum())))
    result=dict(scope='Exploratory paired comparison; thresholds are research summaries, not user acceptance',
        bootstrap=dict(block_calendar_weeks=13,draws=2000,seed=3403,main=uncertainty),precision_floors=floors,confirmation_cost=delay_cost)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    inputs.update({str(calfile):sha(calfile),str(EP/'protocols/v2_b03/plan.md'):sha(EP/'protocols/v2_b03/plan.md'),str(Path(__file__)):sha(Path(__file__))})
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(table.to_string(index=False));print(json.dumps(uncertainty,indent=2));print(json.dumps(delay_cost,indent=2))


if __name__=='__main__':main()
