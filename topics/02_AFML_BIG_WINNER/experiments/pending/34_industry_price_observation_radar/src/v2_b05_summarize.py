"""Summarize all registered seeds; never pick the best seed."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    root=EP/'outputs/v2_b05';out=root/'comparison'
    if out.exists():raise FileExistsError('Preserve comparison')
    out.mkdir();rows=[];procs={};quality={};burdens={};inputs={};annual=[]
    for seed in range(34050,34058):
        for quota in (1,3,5):
            for delay in (0,1):
                for arm in ('A','B'):
                    run=root/f'seed{seed}/q{quota}_d{delay}'/arm;key=(seed,quota,delay,arm)
                    files=[run/'evaluation/summary.json',run/'evaluation/process_coverage.parquet',run/'evaluation/event_quality.parquet',run/'weekly_burden.csv']
                    inputs.update({str(f):sha(f) for f in files})
                    s=json.loads(files[0].read_text());procs[key]=pd.read_parquet(files[1]);quality[key]=pd.read_parquet(files[2]);burdens[key]=pd.read_csv(files[3])
                    rows.append(dict(seed=seed,quota=quota,delay=delay,arm=arm,new=s['new_total'],unknown=s['new_unknown'],evaluable=s['new_evaluable'],effective=s['new_effective'],
                        precision=s['new_effective_rate'],processes=s['known_processes'],covered=s['covered'],coverage=s['coverage'],timely=s['coverage_timing'].get('TIMELY',0),
                        mean_pool=burdens[key].pool.mean(),updates=burdens[key].updates.sum(),sample_support=s['new_evaluable']>=50))
                    if quota==5 and delay==0:
                        pr=procs[key].copy();pr['year']=pr.start.str[:4]
                        for y,g in pr.groupby('year'):annual.append(dict(seed=seed,arm=arm,year=y,n=len(g),covered=int(g.covered.sum()),timely=int(g.timing.eq('TIMELY').sum())))
                assert burdens[(seed,quota,delay,'A')].new.equals(burdens[(seed,quota,delay,'B')].new)
    table=pd.DataFrame(rows);table.to_csv(out/'all_seed_comparisons.csv',index=False)
    metrics=['new','unknown','evaluable','effective','precision','covered','coverage','timely','mean_pool','updates']
    means=table.groupby(['quota','delay','arm'])[metrics].mean().reset_index();means.to_csv(out/'mean_comparisons.csv',index=False)
    table.groupby(['quota','delay','arm'])[metrics].agg(['min','max']).to_csv(out/'seed_ranges.csv')
    pd.DataFrame(annual).to_csv(out/'main_annual_all_seeds.csv',index=False)
    first=burdens[(34050,5,0,'A')].date.min();last=burdens[(34050,5,0,'A')].date.max()
    weeks=pd.period_range(first,last,freq='W-SUN');wi={str(v):i for i,v in enumerate(weeks)};n=len(weeks)
    def vectors(seed,arm):
        x=np.zeros((n,6));p=procs[(seed,5,0,arm)];q=quality[(seed,5,0,arm)]
        for r in p.itertuples():
            i=wi[str(pd.Period(r.start,freq='W-SUN'))];x[i,0]+=r.covered;x[i,1]+=1;x[i,2]+=r.timing=='TIMELY';x[i,3]+=1
        for r in q[q.kind.eq('NEW')&~q.status.eq('UNKNOWN')].itertuples():
            i=wi[str(pd.Period(r.date,freq='W-SUN'))];x[i,4]+=r.status in ('TIMELY','LATE');x[i,5]+=1
        return x
    a=np.array([vectors(seed,'A') for seed in range(34050,34058)]);b=np.array([vectors(seed,'B') for seed in range(34050,34058)])
    def delta(aa,bb):return bb[:,[0,2,4]]/bb[:,[1,3,5]]-aa[:,[0,2,4]]/aa[:,[1,3,5]]
    rng=np.random.default_rng(3405);diffs=[]
    for _ in range(2000):
        starts=rng.integers(0,n,size=(n+12)//13);ix=((starts[:,None]+np.arange(13))%n).ravel()[:n]
        diffs.append(delta(a[:,ix,:].sum(axis=1),b[:,ix,:].sum(axis=1)).mean(axis=0))
    d=np.array(diffs);points=delta(a.sum(axis=1),b.sum(axis=1))
    uncertainty={name:dict(mean_B_minus_A=float(points[:,k].mean()),interval_95=np.quantile(d[:,k],[.025,.975]).tolist(),
        seed_difference_range=[float(points[:,k].min()),float(points[:,k].max())]) for k,name in enumerate(['coverage','timely_coverage','new_precision'])}
    floors=[]
    for delay in (0,1):
        for floor in (.30,.35,.40):
            row=dict(delay=delay,precision_floor=floor)
            for arm in ('A','B'):
                eligible=means[means.delay.eq(delay)&means.arm.eq(arm)&means.precision.ge(floor)]
                row[arm]=None if eligible.empty else eligible.sort_values(['coverage','quota'],ascending=[False,True]).iloc[0].to_dict()
            floors.append(row)
    calfile=Path(next(x for x in json.loads((PRIOR/'receipt.json').read_text())['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calfile).date);cost=[]
    for seed in range(34050,34058):
        for quota in (1,3,5):
            for arm in ('A','B'):
                p0=procs[(seed,quota,0,arm)].set_index('process');p1=procs[(seed,quota,1,arm)].set_index('process');both=p0.covered&p1.covered
                dt=cal.get_indexer(pd.to_datetime(p1.loc[both,'first_date']))-cal.get_indexer(pd.to_datetime(p0.loc[both,'first_date']))
                cost.append(dict(seed=seed,quota=quota,arm=arm,lost=int((p0.covered&~p1.covered).sum()),gained=int((~p0.covered&p1.covered).sum()),common=int(both.sum()),
                    delay_p10=float(np.quantile(dt,.1)),delay_p50=float(np.quantile(dt,.5)),delay_p90=float(np.quantile(dt,.9)),
                    timely_change=int(p1.timing.eq('TIMELY').sum()-p0.timing.eq('TIMELY').sum())))
    pd.DataFrame(cost).to_csv(out/'confirmation_cost_all_seeds.csv',index=False)
    result=dict(scope='Random ordering control, chronological historical simulation; no seed selection',seeds=list(range(34050,34058)),
        bootstrap=dict(block_weeks=13,draws=2000,seed=3405,main=uncertainty),precision_floors=floors,
        confirmation_means=pd.DataFrame(cost).groupby(['quota','arm'])[['lost','gained','common','delay_p10','delay_p50','delay_p90','timely_change']].mean().reset_index().to_dict('records'))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    inputs.update({str(calfile):sha(calfile),str(EP/'protocols/v2_b05/plan.md'):sha(EP/'protocols/v2_b05/plan.md'),str(Path(__file__)):sha(Path(__file__))})
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(means.to_string(index=False));print(json.dumps(uncertainty,indent=2))


if __name__=='__main__':main()
